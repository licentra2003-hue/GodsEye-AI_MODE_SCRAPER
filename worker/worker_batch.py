"""
GodsEye Batch Worker — worker_batch.py

ARCHITECTURE
============
  Main thread  → pika BlockingConnection.start_consuming()
                 Never blocked — just collects messages into batches.

  Batch thread → one daemon thread per batch (ThreadPoolExecutor).
                 Runs its own asyncio loop + Playwright browser.
                 N parallel tabs inside one browser context.

  ACK / NACK   → ALWAYS via connection.add_callback_threadsafe().
                 This schedules the call to run inside pika's own I/O thread,
                 eliminating the "IndexError: pop from an empty deque" /
                 "PRECONDITION_FAILED — unknown delivery tag" race condition
                 that occurs when multiple asyncio tasks ACK simultaneously
                 from a non-pika thread.

SCALING
=======
  Deploy multiple worker containers.  Each container processes one batch at a
  time (BATCH_SIZE tabs, one browser).  RabbitMQ distributes jobs automatically
  via prefetch_count.  For 100 concurrent queries: 20 workers × BATCH_SIZE=5.

DEDUPLICATION
=============
  Layer 1  — in-memory set per process          (fastest, same-worker guard)
  Layer 2  — DB unique insert to processed_jobs  (cross-worker / cross-restart)
  Layer 3  — upsert on job_id in product_analysis_google  (last-resort idempotency)

PREREQUISITES (one-time DB migration)
======================================
  ALTER TABLE product_analysis_google
      ADD COLUMN IF NOT EXISTS job_id VARCHAR(255) UNIQUE;

  CREATE TABLE IF NOT EXISTS processed_jobs (
      id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      job_id       VARCHAR(255) UNIQUE NOT NULL,
      worker_id    TEXT,
      engine       TEXT DEFAULT 'google_ai',
      claimed_at   TIMESTAMPTZ DEFAULT NOW(),
      expires_at   TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
  );

ENV VARS
========
  RABBITMQ_URL          amqp://admin:admin123@localhost:5672/
  WORKER_ID             auto (worker-<pid>)
  BATCH_SIZE            5
  BATCH_TIMEOUT_SECS    10     flush partial batch after this many seconds
  STORAGE_MODE_API      false  true -> POST to CALLBACK_API_URL
  CALLBACK_API_URL      http://gateway:8080/api/scrape-result
  CALLBACK_TIMEOUT      30
  SUPABASE_URL          ...
  SUPABASE_KEY          ...
  PROXY_SERVER          host:port  (optional)
  PROXY_USERNAME        ...
  PROXY_PASSWORD        ...
  HEADLESS              true
  DEBUG                 false
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set

import httpx
import pika
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("godseye.worker")

sys.path.append(str(Path(__file__).parent / "core"))
from core.scraper_working import AIModeResult, SourceLink      # noqa: E402
from core.profile_manager import ProfileManager                # noqa: E402
from core.scraper import LOCATION_CONFIG, GoogleAIModeScraper  # noqa: E402


# ---------------------------------------------------------------------------
# WorkerService
# ---------------------------------------------------------------------------

class WorkerService:
    """
    Batch scraping worker.

    One instance per process.  Multiple instances (Docker containers) share
    the same RabbitMQ queue and Supabase DB for horizontal scaling.
    """

    def __init__(self):
        # -- Identity ---------------------------------------------------------
        self.worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")

        # -- RabbitMQ ---------------------------------------------------------
        self.rabbitmq_url = os.getenv(
            "RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/"
        )
        # Set in start(), referenced by all threads for add_callback_threadsafe
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel = None

        # -- Supabase ---------------------------------------------------------
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Optional[Client] = None

        # -- Storage / callback -----------------------------------------------
        self.storage_mode_api = os.getenv("STORAGE_MODE_API", "false").lower() == "true"
        self.callback_api_url = os.getenv("CALLBACK_API_URL")
        self.callback_timeout = int(os.getenv("CALLBACK_TIMEOUT", "30"))

        # -- Proxy ------------------------------------------------------------
        self.proxy_server   = os.getenv("PROXY_SERVER")
        self.proxy_username = os.getenv("PROXY_USERNAME")
        self.proxy_password = os.getenv("PROXY_PASSWORD")

        # -- Batch config -----------------------------------------------------
        self.batch_size         = int(os.getenv("BATCH_SIZE", "5"))
        self.batch_timeout_secs = float(os.getenv("BATCH_TIMEOUT_SECS", "10"))

        # _batch_lock guards _current_batch and _flush_timer across threads.
        # _on_message_callback runs in the pika I/O (main) thread;
        # _flush_partial_batch runs in a threading.Timer thread.
        self._batch_lock: threading.Lock = threading.Lock()
        self._current_batch: List[dict] = []
        self._flush_timer: Optional[threading.Timer] = None

        # -- Deduplication ----------------------------------------------------
        # In-memory set: fastest guard, valid for the lifetime of this process.
        # Lock because batch threads may also call _claim_job concurrently.
        self._seen_job_ids: Set[str] = set()
        self._dedup_lock: threading.Lock = threading.Lock()

        # -- Thread pool for batch execution ----------------------------------
        # max_workers = how many batches can run in parallel per process.
        # Typically 1 (one browser at a time). Increase only if RAM allows.
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="batch"
        )

        # -- Misc -------------------------------------------------------------
        self.profile_manager = ProfileManager()
        self.debug = os.getenv("DEBUG", "false").lower() == "true"

        # -- Init external connections ----------------------------------------
        self._init_supabase()

        logger.info(
            f"Worker {self.worker_id} initialised | "
            f"batch_size={self.batch_size} | "
            f"batch_timeout={self.batch_timeout_secs}s | "
            f"storage={'API' if self.storage_mode_api else 'Supabase'} | "
            f"proxy={bool(self.proxy_server)} | debug={self.debug}"
        )

    # =========================================================================
    # Supabase
    # =========================================================================

    def _init_supabase(self):
        try:
            if self.supabase_url and self.supabase_key:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase client initialised")
            else:
                logger.warning("SUPABASE_URL / SUPABASE_KEY not set — DB dedup disabled")
        except Exception as exc:
            logger.error(f"Supabase init failed: {exc}")
            self.supabase = None

    # =========================================================================
    # Thread-safe pika ACK / NACK
    # =========================================================================
    #
    # THE FIX for "IndexError: pop from an empty deque" / PRECONDITION_FAILED:
    #
    # pika.BlockingConnection is NOT thread-safe.  Its internal write buffer
    # (a deque) is corrupted when multiple threads call basic_ack() at the same
    # time.  The only safe way to call channel operations from other threads is
    # connection.add_callback_threadsafe(), which enqueues a lambda to run on
    # the next iteration of pika's select-loop in the main thread — serialising
    # all socket writes with zero contention.

    def _ack(self, delivery_tag: int):
        """Schedule an ACK in pika's I/O thread. Safe to call from any thread."""
        try:
            self._connection.add_callback_threadsafe(
                lambda: self._do_ack(delivery_tag)
            )
        except Exception as exc:
            logger.error(f"Could not schedule ACK for tag {delivery_tag}: {exc}")

    def _nack(self, delivery_tag: int, requeue: bool = True):
        """Schedule a NACK in pika's I/O thread. Safe to call from any thread."""
        try:
            self._connection.add_callback_threadsafe(
                lambda: self._do_nack(delivery_tag, requeue)
            )
        except Exception as exc:
            logger.error(f"Could not schedule NACK for tag {delivery_tag}: {exc}")

    def _do_ack(self, delivery_tag: int):
        """Executes inside pika's I/O thread — no concurrency risk."""
        try:
            self._channel.basic_ack(delivery_tag=delivery_tag)
        except Exception as exc:
            logger.error(f"basic_ack failed for tag {delivery_tag}: {exc}")

    def _do_nack(self, delivery_tag: int, requeue: bool):
        """Executes inside pika's I/O thread — no concurrency risk."""
        try:
            self._channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
        except Exception as exc:
            logger.error(f"basic_nack failed for tag {delivery_tag}: {exc}")

    def _requeue_job_to_end(self, job_data: dict, delivery_tag: int):
        """Schedule a requeue in pika's I/O thread, publishing a new message so it goes to back."""
        try:
            self._connection.add_callback_threadsafe(
                lambda: self._do_requeue_to_end(job_data, delivery_tag)
            )
        except Exception as exc:
            logger.error(f"Could not schedule requeue for tag {delivery_tag}: {exc}")

    def _do_requeue_to_end(self, job_data: dict, delivery_tag: int):
        try:
            payload = dict(job_data)
            payload.pop('_delivery_tag', None)
            
            body = json.dumps(payload).encode("utf-8")
            
            self._channel.basic_publish(
                exchange='',
                routing_key="scrape_jobs",
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                )
            )
            # ACK the old one so it's fully processed/removed from front of queue
            self._channel.basic_ack(delivery_tag=delivery_tag)
        except Exception as exc:
            logger.error(f"basic_publish (requeue) failed for tag {delivery_tag}: {exc}")
            # Fallback
            try:
                self._channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
            except Exception as inner_exc:
                logger.error(f"fallback nack failed for tag {delivery_tag}: {inner_exc}")

    # =========================================================================
    # Job claiming (atomic deduplication)
    # =========================================================================

    def _claim_job(self, job_id: str) -> bool:
        """
        Atomically claim a job for this worker.

        Returns True  -> this worker owns it; proceed.
        Returns False -> already owned by another worker or run; skip.
        """
        with self._dedup_lock:
            # Layer 1: in-memory (instant, same process)
            if job_id in self._seen_job_ids:
                return False

            # Layer 2: database unique insert (cross-worker, cross-restart)
            if self.supabase:
                try:
                    self.supabase.table("processed_jobs").insert({
                        "job_id":    job_id,
                        "worker_id": self.worker_id,
                        "engine":    "google_ai",
                        "expires_at": (
                            datetime.now() + timedelta(hours=24)
                        ).isoformat(),
                    }).execute()
                    # Insert succeeded -> we own it
                except Exception as exc:
                    err = str(exc).lower()
                    if any(k in err for k in ("duplicate", "unique", "23505")):
                        logger.warning(
                            f"Job {job_id} already claimed by another worker — skipping"
                        )
                        return False
                    # Unexpected DB error — log but don't block
                    logger.warning(
                        f"processed_jobs insert error ({job_id}): {exc} — proceeding"
                    )

            self._seen_job_ids.add(job_id)
            return True

    def _unclaim_job(self, job_id: str):
        """
        Release a claim so another worker can retry the job.
        Only for browser-launch failures (pre-scrape). Never after a scrape runs.
        """
        with self._dedup_lock:
            self._seen_job_ids.discard(job_id)

        if self.supabase:
            try:
                self.supabase.table("processed_jobs")\
                    .delete().eq("job_id", job_id).execute()
            except Exception as exc:
                logger.warning(f"Could not unclaim job {job_id}: {exc}")

    # =========================================================================
    # RabbitMQ — start / message callback
    # =========================================================================

    def start(self):
        logger.info(f"Starting {self.worker_id}")

        params = pika.URLParameters(self.rabbitmq_url)
        params.heartbeat = 600           # 10 min — covers long browser sessions
        params.blocked_connection_timeout = 300

        self._connection = pika.BlockingConnection(params)
        self._channel    = self._connection.channel()
        self._channel.queue_declare(queue="scrape_jobs", durable=True)

        # prefetch_count = batch_size so RabbitMQ delivers exactly one batch
        # worth of messages before we start ACKing.
        self._channel.basic_qos(prefetch_count=self.batch_size)
        self._channel.basic_consume(
            queue="scrape_jobs",
            on_message_callback=self._on_message_callback,
            auto_ack=False,
        )

        logger.info(
            f"Connected to RabbitMQ — listening "
            f"(batch_size={self.batch_size}, timeout={self.batch_timeout_secs}s)"
        )

        # Blocks the main thread in pika's select loop.
        # ACKs/NACKs from batch threads arrive via add_callback_threadsafe
        # and are serialised here with no socket contention.
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Shutting down (KeyboardInterrupt)")
            self._connection.close()

    def _on_message_callback(self, channel, method, properties, body):
        """
        Runs in pika's I/O thread (main thread).
        Must return quickly — blocking here freezes pika's event loop.
        """
        try:
            job_data = json.loads(body.decode("utf-8"))
        except Exception as exc:
            logger.error(f"Could not parse message body: {exc} — discarding")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        job_data["_delivery_tag"] = method.delivery_tag

        with self._batch_lock:
            self._current_batch.append(job_data)
            count = len(self._current_batch)
            logger.info(
                f"Buffered {job_data.get('job_id')}  ({count}/{self.batch_size})"
            )

            if count >= self.batch_size:
                self._cancel_flush_timer()
                self._dispatch_batch()
            elif count == 1:
                self._start_flush_timer()

    # =========================================================================
    # Batch buffering helpers
    # =========================================================================

    def _start_flush_timer(self):
        self._flush_timer = threading.Timer(
            self.batch_timeout_secs, self._flush_partial_batch
        )
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _cancel_flush_timer(self):
        """Must be called while holding _batch_lock."""
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None

    def _flush_partial_batch(self):
        """Called by the Timer thread when the batch hasn't filled in time."""
        with self._batch_lock:
            if not self._current_batch:
                return
            logger.info(f"Partial-batch flush ({len(self._current_batch)} job(s))")
            self._flush_timer = None
            self._dispatch_batch()

    def _dispatch_batch(self):
        """
        Snapshot the current batch, reset state, hand to thread pool.
        Must be called while holding _batch_lock.
        """
        batch = self._current_batch.copy()
        self._current_batch = []
        if batch:
            self._executor.submit(self._execute_batch_in_thread, batch)

    # =========================================================================
    # Batch execution (runs in a ThreadPoolExecutor thread)
    # =========================================================================

    def _execute_batch_in_thread(self, batch: List[dict]):
        """
        Entry point for the batch thread.
        Each thread gets its own asyncio event loop and Playwright browser.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._process_batch(batch))
        except Exception as exc:
            logger.error(f"Unhandled batch-thread exception: {exc}")
            logger.error(traceback.format_exc())
            # Emergency NACK for any jobs not already handled
            for job in batch:
                job_id = job.get("job_id", "?")
                self._unclaim_job(job_id)
                self._nack(job["_delivery_tag"], requeue=True)
                logger.warning(f"Emergency NACK for {job_id}")
        finally:
            loop.close()

    async def _process_batch(self, batch: List[dict]):
        """Claim jobs, then run the browser session."""
        claimed: List[dict] = []

        for job in batch:
            job_id = job.get("job_id")
            if self._claim_job(job_id):
                claimed.append(job)
                logger.info(f"Claimed {job_id}")
            else:
                logger.warning(f"Duplicate {job_id} — ACKing and skipping")
                self._ack(job["_delivery_tag"])

        if not claimed:
            logger.info("All jobs in batch were duplicates — nothing to do")
            return

        logger.info(f"Launching browser for {len(claimed)} tab(s)")

        profile_path: Optional[str] = None
        try:
            batch_id     = f"batch_{self.worker_id}_{int(datetime.now().timestamp())}"
            profile_path = self.profile_manager.get_profile_path(batch_id)
            await self._run_browser_session(claimed, profile_path)

        except Exception as exc:
            # Browser never opened — safe to unclaim and NACK for retry
            logger.error(f"Browser-launch failure: {exc}")
            logger.error(traceback.format_exc())
            for job in claimed:
                job_id = job.get("job_id")
                self._unclaim_job(job_id)
                self._nack(job["_delivery_tag"], requeue=True)
                logger.warning(f"NACKed {job_id} (browser never opened)")

        finally:
            if profile_path:
                try:
                    self.profile_manager.cleanup_profile(profile_path)
                    logger.info(f"Burned profile: {profile_path}")
                except Exception as exc:
                    logger.warning(f"Profile cleanup error: {exc}")

    # =========================================================================
    # Browser session (single browser, N parallel tabs)
    # =========================================================================

    async def _run_browser_session(self, jobs: List[dict], profile_path: str):
        """Open one persistent context, run each job as an isolated tab."""
        location = jobs[0].get("location", "India")
        loc_cfg  = LOCATION_CONFIG.get(location, LOCATION_CONFIG["India"])

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-notifications",
            "--start-maximized",
            "--window-size=1920,1080",
        ]
        if os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes"):
            launch_args.append("--headless=new")

        proxy_config = None
        if self.proxy_server and self.proxy_username and self.proxy_password:
            proxy_config = {
                "server":   f"http://{self.proxy_server}",
                "username": self.proxy_username,
                "password": self.proxy_password,
            }
            logger.info(f"Using proxy: {self.proxy_server}")

        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=False,  # actual headless via --headless=new in launch_args
                args=launch_args,
                ignore_default_args=["--enable-automation"],
                locale=loc_cfg["locale"],
                timezone_id=loc_cfg["timezone_id"],
                geolocation=loc_cfg["geolocation"],
                permissions=loc_cfg["permissions"],
                no_viewport=True,  # prevents viewport vs window-size mismatch
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                proxy=proxy_config,
            )

            try:
                tasks = [
                    self._run_tab(context, job, idx)
                    for idx, job in enumerate(jobs)
                ]
                # return_exceptions=True: one tab crash does NOT kill siblings
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for idx, res in enumerate(results):
                    if isinstance(res, Exception):
                        # _run_tab never raises — this is a hard backstop
                        logger.error(
                            f"Tab {idx+1} leaked an unhandled exception "
                            f"(job {jobs[idx].get('job_id', '?')}): {res}"
                        )
            finally:
                try:
                    await context.close()
                except Exception as exc:
                    logger.warning(f"Context close error: {exc}")

    async def _run_tab(self, context, job_data: dict, idx: int):
        """
        One tab = one query.  Fully isolated.

        Contract: MUST NOT raise.  All exceptions are caught internally so
        sibling tabs are unaffected.  ACK fires in finally no matter what.
        """
        job_id  = job_data["job_id"]
        query   = job_data["query"]
        loc     = job_data.get("location", "India")
        prod_id = job_data.get("product_id")
        dtag    = job_data["_delivery_tag"]
        page: Optional[Page] = None
        should_ack = True

        try:
            # Stagger tabs to reduce simultaneous Google requests from one IP
            stagger = idx * 2.5
            if stagger:
                logger.info(f"Tab {idx+1}: staggering {stagger}s")
                await asyncio.sleep(stagger)

            page = await context.new_page()
            await self._apply_stealth_scripts(page)

            # Fresh GoogleAIModeScraper per tab — eliminates shared mutable
            # state corruption across concurrent coroutines (the original bug
            # that caused 4-5 silent drops per 25-query batch)
            scraper = GoogleAIModeScraper()

            logger.info(f"Tab {idx+1}: scraping '{query}' [{loc}]")
            result: AIModeResult = await scraper.scrape(page, query, loc, job_id)

            if result.success:
                logger.info(f"Tab {idx+1}: SUCCESS '{query}'")
                await self._save_result(job_id, prod_id, query, result)
            else:
                err_msg = (result.error_message or "").lower()
                if "bot detection" in err_msg or "captcha" in err_msg:
                    retry_count = job_data.get("_retry_count", 0)
                    if retry_count < 2:
                        logger.warning(
                            f"Tab {idx+1}: Bot detected. Re-queueing job {job_id} "
                            f"(Attempt {retry_count + 1}/2)"
                        )
                        # Increment retry count for the re-queued payload
                        job_data["_retry_count"] = retry_count + 1
                        self._unclaim_job(job_id)
                        
                        self._requeue_job_to_end(job_data, dtag)
                        should_ack = False
                    else:
                        logger.error(f"Tab {idx+1}: Max bot retries (2) reached for '{query}'")
                        logger.warning(
                            f"Tab {idx+1}: scraper returned failure for '{query}' "
                            f"— {result.error_message}"
                        )
                else:
                    logger.warning(
                        f"Tab {idx+1}: scraper returned failure for '{query}' "
                        f"— {result.error_message}"
                    )
                # ACK is handled in finally unless should_ack is False
                # Do NOT unclaim for non-bot failures or max retries

        except Exception as exc:
            # Log but do NOT re-raise — keeps sibling tabs alive
            logger.error(f"Tab {idx+1} exception for '{query}': {exc}")
            logger.error(traceback.format_exc())

        finally:
            # Close page first, then schedule ACK
            if page:
                try:
                    await page.close()
                except Exception as exc:
                    logger.warning(f"Page close error (tab {idx+1}): {exc}")

            # THE FIX: schedule ACK on pika's I/O thread via add_callback_threadsafe
            if should_ack:
                self._ack(dtag)
                logger.info(f"ACK scheduled for {job_id} (tab {idx+1})")
            else:
                logger.info(f"ACK skipped for {job_id} (re-queued to back of line)")

    # =========================================================================
    # Stealth scripts
    # =========================================================================

    async def _apply_stealth_scripts(self, page: Page):
        script = r"""
            Object.defineProperty(navigator, 'platform',           { get: () => 'Win32' });
            Object.defineProperty(navigator, 'webdriver',          { get: () => undefined });
            Object.defineProperty(navigator, 'hardwareConcurrency',{ get: () => 4 });
            Object.defineProperty(navigator, 'deviceMemory',       { get: () => 8 });

            const _gp = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Google Inc. (NVIDIA)';
                if (p === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return _gp.call(this, p);
            };
        """
        try:
            await page.add_init_script(script)
            await asyncio.sleep(random.uniform(0.05, 0.12))
        except Exception as exc:
            logger.warning(f"Stealth script error: {exc}")

    # =========================================================================
    # Persist result
    # =========================================================================

    async def _save_result(
        self,
        job_id: str,
        product_id: str,
        query: str,
        result: AIModeResult,
    ):
        """
        Persist the scrape result.

        Supabase: upsert on job_id — idempotent even on double-delivery.
                  Produces 0 extra rows instead of 1 duplicate.
        API:      POST to CALLBACK_API_URL (Go gateway stores in memory
                  for polling).
        """
        if self.debug:
            logger.info(
                f"save_result  job={job_id}  "
                f"mode={'API' if self.storage_mode_api else 'Supabase'}  "
                f"success={result.success}  ai_found={result.ai_mode_found}  "
                f"sources={len(result.source_links)}"
            )

        source_links = [
            {
                "url":           src.url,
                "text":          src.text,
                "snippet":       src.snippet,
                "position":      src.position,
                "related_to":    "General",
                "domain":        src.domain,
                "favicon_url":   src.favicon_url,
                "thumbnail_url": src.thumbnail_url,
                "date":          src.date,
            }
            for src in result.source_links
        ]

        try:
            if self.storage_mode_api:
                await self._post_to_api(job_id, {
                    "job_id":                       job_id,
                    "product_id":                   product_id,
                    "query":                        result.query,
                    "success":                      result.success,
                    "location":                     result.location,
                    "timestamp":                    result.timestamp,
                    "source_links":                 source_links,
                    "error_message":                result.error_message,
                    "original_query":               result.original_query,
                    "structure_type":               "structure_b",
                    "ai_overview_text":             result.ai_mode_text,
                    "ai_overview_found":            result.ai_mode_found,
                    "query_modifications_tried":    [result.query],
                    "did_query_popped_AI_overview": result.ai_mode_found,
                    "ai_mode_found":                result.ai_mode_found,
                    "ai_mode_text":                 "true" if result.ai_mode_found else "false",
                })

            else:
                if not self.supabase:
                    logger.error(f"Supabase unavailable — cannot save job {job_id}")
                    return

                response = (
                    self.supabase
                    .table("product_analysis_google")
                    .upsert(
                        {
                            "job_id":       job_id,      # unique -> idempotent
                            "product_id":   product_id,
                            "search_query": result.query,
                            "raw_serp_results": {
                                "query":                        result.query,
                                "success":                      result.success,
                                "location":                     result.location,
                                "timestamp":                    result.timestamp,
                                "source_links":                 source_links,
                                "error_message":                result.error_message,
                                "original_query":               result.original_query,
                                "structure_type":               "structure_b",
                                "ai_overview_text":             result.ai_mode_text,
                                "ai_overview_found":            result.ai_mode_found,
                                "query_modifications_tried":    [result.query],
                                "did_query_popped_AI_overview": result.ai_mode_found,
                                "ai_mode_found":                result.ai_mode_found,
                                "ai_mode_text":                 result.ai_mode_text,
                            },
                        },
                        on_conflict="job_id",
                    )
                    .execute()
                )

                if response.data:
                    row_id = response.data[0].get("id", "?")
                    logger.info(
                        f"Saved  id={row_id}  job={job_id}  "
                        f"text_len={len(result.ai_mode_text)}  "
                        f"sources={len(result.source_links)}"
                    )
                else:
                    logger.error(
                        f"Supabase upsert returned no data for job {job_id}: {response}"
                    )

        except Exception as exc:
            logger.error(f"Save error for job {job_id}: {exc}")
            if self.debug:
                logger.error(traceback.format_exc())
            # Do NOT unclaim or re-queue.  Scrape succeeded; a DB hiccup must
            # not trigger another scrape of the same query.

    # =========================================================================
    # API callback
    # =========================================================================

    async def _post_to_api(self, job_id: str, payload: dict):
        try:
            async with httpx.AsyncClient(timeout=self.callback_timeout) as client:
                resp = await client.post(
                    self.callback_api_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent":   "GodsEye-Worker/2.0",
                    },
                )
            if resp.status_code == 200:
                logger.info(f"API callback OK  job={job_id}")
            else:
                logger.error(
                    f"API callback {resp.status_code}  job={job_id}  "
                    f"body={resp.text[:200]}"
                )
        except Exception as exc:
            logger.error(f"API callback exception  job={job_id}: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    worker = WorkerService()
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as exc:
        logger.error(f"Worker crashed: {exc}")
        raise


if __name__ == "__main__":
    main()