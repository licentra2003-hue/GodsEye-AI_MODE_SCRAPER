"""
Updated worker that uses the working scraper approach
"""
import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import aiohttp
import pika
from dotenv import load_dotenv
from playwright.async_api import async_playwright, BrowserContext, Page
from playwright_stealth import Stealth
from pydantic import BaseModel, Field
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import working scraper components
sys.path.append(str(Path(__file__).parent / "core"))
from core.scraper_working import AIModeResult, SourceLink
from core.profile_manager import ProfileManager

# Import LOCATION_CONFIG and GoogleAIModeScraper from root scraper
sys.path.append(str(Path(__file__).parent.parent))
from scraper import LOCATION_CONFIG, GoogleAIModeScraper

class WorkerService:
    """Main worker service that consumes jobs and executes scraping"""
    
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/")
        self.worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
        self.profile_manager = ProfileManager()
        self.scraper = GoogleAIModeScraper()
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        
        # Supabase configuration
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = None
        
        # Proxy configuration
        self.proxy_server = os.getenv("PROXY_SERVER")
        self.proxy_username = os.getenv("PROXY_USERNAME")
        self.proxy_password = os.getenv("PROXY_PASSWORD")
        
        # Storage mode configuration
        self.storage_mode_api = os.getenv("STORAGE_MODE_API", "false").lower() == "true"
        self.callback_api_url = os.getenv("CALLBACK_API_URL")
        self.callback_timeout = int(os.getenv("CALLBACK_TIMEOUT", "30"))
        
        # Debug configuration
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Job deduplication cache (prevent processing same query multiple times)
        # self.processed_jobs = set()  # Store job_ids that have been processed - REPLACED with Supabase deduplication
        
        # Initialize Supabase client
        self._init_supabase()
        
        logger.info(f"Worker {self.worker_id} initialized")
        logger.info(f"RabbitMQ URL: {self.rabbitmq_url}")
        logger.info(f"Supabase URL: {self.supabase_url}")
        logger.info(f"Proxy configured: {bool(self.proxy_server)}")
        logger.info(f"Storage mode: {'API Callback' if self.storage_mode_api else 'Direct Supabase'}")
        if self.storage_mode_api:
            logger.info(f"Callback API URL: {self.callback_api_url}")
        logger.info(f"Debug mode: {self.debug}")
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            if self.supabase_url and self.supabase_key:
                # Create client without proxy - Supabase doesn't support proxy argument
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                
                logger.info("✅ Supabase client initialized")
                # Create processed_jobs table if it doesn't exist
                self._ensure_processed_jobs_table()
            else:
                logger.warning("⚠ Supabase configuration missing")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
            # Continue without Supabase - worker can still process jobs
            self.supabase = None
    
    def _ensure_processed_jobs_table(self):
        """Ensure processed_jobs table exists in Supabase"""
        try:
            # Create table using SQL via RPC call
            sql = """
            CREATE TABLE IF NOT EXISTS processed_jobs (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
            );
            
            CREATE INDEX IF NOT EXISTS idx_processed_jobs_job_id ON processed_jobs(job_id);
            """
            
            # Execute SQL using Supabase RPC
            response = self.supabase.rpc('exec_sql', {'sql': sql}).execute()
            logger.info("✅ Processed jobs table ensured")
            
        except Exception as e:
            logger.warning(f"⚠ Could not ensure processed_jobs table: {e}")
            # Continue anyway - table might already exist or we'll handle errors later
    
    async def is_job_processed(self, job_id: str) -> bool:
        """Check if job has already been processed using Supabase"""
        try:
            if not self.supabase:
                return False
                
            response = self.supabase.table("processed_jobs").select("job_id").eq("job_id", job_id).execute()
            return len(response.data) > 0
            
        except Exception as e:
            logger.warning(f"⚠ Error checking if job {job_id} is processed: {e}")
            return False  # Assume not processed on error
    
    async def mark_job_processed(self, job_id: str):
        """Mark job as processed in Supabase"""
        try:
            if not self.supabase:
                return
                
            # Calculate expires_at as 24 hours from now
            from datetime import datetime, timedelta
            expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
            
            self.supabase.table("processed_jobs").insert({
                "job_id": job_id,
                "expires_at": expires_at
            }).execute()
            
            logger.info(f"✅ Marked job {job_id} as processed")
            
        except Exception as e:
            logger.warning(f"⚠ Error marking job {job_id} as processed: {e}")
    
    async def cleanup_old_processed_jobs(self):
        """Clean up old processed jobs (older than 24 hours)"""
        try:
            if not self.supabase:
                return
                
            # Delete expired jobs
            response = self.supabase.table("processed_jobs").delete().lt("expires_at", "NOW()").execute()
            if response.data:
                logger.info(f"🧹 Cleaned up {len(response.data)} old processed jobs")
                
        except Exception as e:
            logger.warning(f"⚠ Error cleaning up old processed jobs: {e}")
    
    async def _remove_processed_job(self, job_id: str):
        """Remove job from processed jobs to allow retry"""
        try:
            if not self.supabase:
                return
                
            self.supabase.table("processed_jobs").delete().eq("job_id", job_id).execute()
            logger.info(f"🗑️ Removed job {job_id} from processed jobs (will allow retry)")
            
        except Exception as e:
            logger.warning(f"⚠ Error removing job {job_id} from processed jobs: {e}")
    
    def start(self):
        """Start worker service"""
        logger.info(f"🚀 Starting worker {self.worker_id}")
        
        # Connect to RabbitMQ
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            channel = connection.channel()
            
            # Declare queue
            channel.queue_declare(queue='scrape_jobs', durable=True)
            channel.basic_qos(prefetch_count=1)
            
            # Set up consumer
            channel.basic_consume(
                queue='scrape_jobs',
                on_message_callback=self._process_job_sync,
                auto_ack=False  # Manual acknowledgment
            )
            
            logger.info("✅ Connected to RabbitMQ, waiting for jobs...")
            
            # Start consuming
            channel.start_consuming()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            raise
    
    async def _process_job(self, channel, method, properties, body):
        """Process a single scrape job with early ACK and persistent deduplication"""
        job_data = json.loads(body.decode('utf-8'))
        job_id = job_data.get('job_id')
        query = job_data.get('query')
        location = job_data.get('location')
        product_id = job_data.get('product_id')
        
        # Override product_id with the specified value
        # product_id = "b36b116e-0c19-4fa0-b669-835bd76c820e"
        
        logger.info(f"📋 Received job {job_id}: '{query}' in {location}")
        logger.info(f"   Product ID: {product_id}")
        
        # EARLY ACK: Acknowledge immediately to prevent re-delivery
        try:
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"✅ Early ACK sent for job {job_id}")
        except Exception as ack_error:
            logger.warning(f"⚠️ Early ACK failed for job {job_id}: {ack_error}")
        
        # Check if this job was already processed (persistent deduplication)
        if await self.is_job_processed(job_id):
            logger.warning(f"🔄 Job {job_id} already processed, skipping...")
            return
        
        # Mark job as processed immediately to prevent race conditions
        await self.mark_job_processed(job_id)
        
        profile_path = None
        
        try:
            # Create unique profile for this job
            profile_path = self.profile_manager.get_profile_path(job_id)
            logger.info(f"📁 Created profile: {profile_path}")
            
            # Execute scraping
            result = await self._execute_scrape(job_id, query, location, profile_path)
            
            if result.success:
                logger.info(f"✅ Job {job_id} completed successfully")
                await self._save_result(job_id, product_id, query, result)
            else:
                logger.warning(f"⚠️ Job {job_id} failed: {result.error_message}")
                # Remove from processed jobs to allow retry
                await self._remove_processed_job(job_id)
                
        except Exception as e:
            logger.error(f"❌ Critical error processing job {job_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Remove from processed jobs to allow retry
            await self._remove_processed_job(job_id)
        finally:
            # Clean up profile (Burn & Rotate strategy)
            if profile_path:
                self.profile_manager.cleanup_profile(profile_path)
                logger.info(f"🔥 Burned profile: {profile_path}")
            
            # No acknowledgment needed here - we already did early ACK at the start
    
    def _process_job_sync(self, channel, method, properties, body):
        """Synchronous wrapper for async job processing"""
        import asyncio
        
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run async job processing
            loop.run_until_complete(self._process_job(channel, method, properties, body))
            
        except Exception as e:
            logger.error(f"❌ Error in job processing: {e}")
            raise
        finally:
            # Clean up the loop
            try:
                loop.close()
            except:
                pass
    
    async def _execute_scrape(self, job_id: str, query: str, location: str, profile_path: str) -> AIModeResult:
        """Execute scraping using the working scraper approach"""
        # Get location settings
        if location not in LOCATION_CONFIG:
            raise ValueError(f"Invalid location: {location}")
        
        location_settings = LOCATION_CONFIG[location]
        
        # Use stealth wrapper
        async with async_playwright() as p:
            # Browser launch arguments
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-infobars', 
                '--disable-notifications',
                '--start-maximized',
                '--disable-gpu', 
                '--window-size=1920,1080',
            ]
            
            # Add proxy configuration if available
            proxy_config = None
            if self.proxy_server and self.proxy_username and self.proxy_password:
                proxy_config = {
                    "server": f"http://{self.proxy_server}",
                    "username": self.proxy_username,
                    "password": self.proxy_password
                }
                logger.info(f"🌐 Using proxy: {self.proxy_server}")
                logger.info(f"🌐 Using proxy config: {proxy_config}")
            
            # Launch browser with stealth
            context = await p.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes"),
                args=launch_args,
                ignore_default_args=['--enable-automation'],
                locale=location_settings['locale'],
                timezone_id=location_settings['timezone_id'],
                geolocation=location_settings['geolocation'],
                permissions=location_settings['permissions'],
                extra_http_headers={
                    **location_settings['extra_http_headers'],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0'
                },
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                proxy=proxy_config
            )
            
            page = await context.new_page()
            
            try:
                # Execute scrape using working scraper
                result = await self.scraper.scrape(page, query, location)
                return result
            finally:
                await context.close()
    
    async def _add_stealth_scripts(self, page: Page):
        """Add stealth scripts from working scraper"""
        stealth_script = r"""
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Google Inc. (NVIDIA)';
                }
                if (parameter === 37446) {
                    return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)';
                }
                return getParameter(parameter);
            };
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        """
        
        try:
            await page.add_init_script(stealth_script)
            await asyncio.sleep(random.uniform(0.05, 0.12))
        except Exception as e:
            print(f"⚠ Error adding stealth scripts: {e}")
    
    async def _save_result(self, job_id: str, product_id: str, query: str, result: AIModeResult):
        """Save the scraping result to Supabase database or send to API"""
        try:
            if self.debug:
                logger.info(f"🐛 DEBUG: Starting save process for job {job_id}")
                logger.info(f"🐛 DEBUG: Storage mode: {'API' if self.storage_mode_api else 'Supabase'}")
                logger.info(f"🐛 DEBUG: Result success: {result.success}")
                logger.info(f"🐛 DEBUG: AI mode found: {result.ai_mode_found}")
                logger.info(f"🐛 DEBUG: Sources count: {len(result.source_links)}")
            
            # Prepare data for Supabase - nested under raw_serp_results column
            scrape_data = {
                "product_id": product_id,
                "search_query": result.query,
                "raw_serp_results": {
                    "query": result.query,
                    "success": result.success,
                    "location": result.location,
                    "timestamp": result.timestamp,
                    "source_links": [
                        {
                            "url": source.url,
                            "text": source.text,
                            "snippet": source.snippet,
                            "position": source.position,
                            "related_to": "General",  # Default value matching API response
                            "domain": source.domain,
                            "favicon_url": source.favicon_url,
                            "thumbnail_url": source.thumbnail_url,
                            "date": source.date
                        } for source in result.source_links
                    ],
                    "error_message": result.error_message,
                    "original_query": result.original_query,
                    "structure_type": "structure_b",  # Default structure type
                    "ai_overview_text": result.ai_mode_text,
                    "ai_overview_found": result.ai_mode_found,
                    "query_modifications_tried": [result.query],  # Array with the query
                    "did_query_popped_AI_overview": result.ai_mode_found,
                    "ai_mode_found": result.ai_mode_found,
                    "ai_mode_text": result.ai_mode_text
                }
            }
            
            # For API mode, send the exact format required (without nesting)
            api_data = {
                "product_id": product_id,
                "query": result.query,
                "success": result.success,
                "location": result.location,
                "timestamp": result.timestamp,
                "source_links": [
                    {
                        "url": source.url,
                        "text": source.text,
                        "snippet": source.snippet,
                        "position": source.position,
                        "related_to": "General",  # Default value matching API response
                        "domain": source.domain,
                        "favicon_url": source.favicon_url,
                        "thumbnail_url": source.thumbnail_url,
                        "date": source.date
                    } for source in result.source_links
                ],
                "error_message": result.error_message,
                "original_query": result.original_query,
                "structure_type": "structure_b",  # Default structure type
                "ai_overview_text": result.ai_mode_text,
                "ai_overview_found": result.ai_mode_found,
                "query_modifications_tried": [result.query],  # Array with the query
                "did_query_popped_AI_overview": result.ai_mode_found,
                "ai_mode_found": result.ai_mode_found,
                "ai_mode_text": "true" if result.ai_mode_found else "false"
            }
            
            if self.debug:
                logger.info(f"🐛 DEBUG: Prepared scrape_data with {len(scrape_data)} fields")
                logger.info(f"🐛 DEBUG: Scrape data keys: {list(scrape_data.keys())}")
                logger.info(f"🐛 DEBUG: Raw SERP results keys: {list(scrape_data['raw_serp_results'].keys())}")
            
            # Use storage mode switch
            if self.storage_mode_api:
                # Send to API callback
                if self.debug:
                    logger.info(f"🐛 DEBUG: Sending to API callback at {self.callback_api_url}")
                    logger.info(f"🐛 DEBUG: API data keys: {list(api_data.keys())}")
                await self._send_to_api(job_id, api_data)
            else:
                # Save to Supabase (existing logic)
                if self.debug:
                    logger.info(f"🐛 DEBUG: Saving to Supabase table: product_analysis_google")
                    logger.info(f"🐛 DEBUG: Supabase client available: {self.supabase is not None}")
                
                response = self.supabase.table("product_analysis_google").insert(scrape_data).execute()
                
                if self.debug:
                    logger.info(f"🐛 DEBUG: Supabase response: {response}")
                    logger.info(f"🐛 DEBUG: Response data: {response.data}")
                    logger.info(f"🐛 DEBUG: Response error: {getattr(response, 'error', None)}")
                
                if response.data:
                    logger.info(f"✅ Saved to Supabase: {response.data[0].get('id')}")
                    logger.info(f"   - Text length: {len(result.ai_mode_text)} chars")
                    logger.info(f"   - Sources: {len(result.source_links)}")
                    if self.debug:
                        logger.info(f"🐛 DEBUG: Successfully saved with ID: {response.data[0].get('id')}")
                else:
                    logger.error(f"❌ Failed to save to Supabase: {response}")
                    if self.debug:
                        logger.error(f"🐛 DEBUG: Save failure details: {response}")
                
        except Exception as e:
            logger.error(f"❌ Save error for job {job_id}: {e}")
            if self.debug:
                logger.error(f"🐛 DEBUG: Exception type: {type(e).__name__}")
                logger.error(f"🐛 DEBUG: Exception details: {str(e)}")
                import traceback
                logger.error(f"🐛 DEBUG: Traceback: {traceback.format_exc()}")
            # Don't fail the job if save fails
            # The scraping was successful, just log the error
    
    async def _send_to_api(self, job_id: str, result_data: dict):
        """Send scraping result to callback API"""
        try:
            import httpx
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "GodsEye-Scraper/1.0"
            }
            
            # Add job_id to the result data
            result_data["job_id"] = job_id
            
            async with httpx.AsyncClient(timeout=self.callback_timeout) as client:
                response = await client.post(
                    self.callback_api_url,
                    json=result_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Sent result to API: {job_id}")
                    logger.info(f"   - API Response: {response.text}")
                else:
                    logger.error(f"❌ Failed to send to API: {response.status_code}")
                    logger.error(f"   - Response: {response.text}")
                    
        except Exception as e:
            logger.error(f"❌ API callback error for job {job_id}: {e}")
            # Don't fail the job if API callback fails
            # The scraping was successful, just log the error
    
    async def _handle_failure(self, job_id: str, result: AIModeResult, channel, method):
        """Handle scraping failures with retry logic"""
        # Check if it's a bot detection (should retry)
        if "bot detection" in str(result.error_message).lower() or "captcha" in str(result.error_message).lower():
            logger.info(f"🔄 Bot detected for job {job_id}, will retry")
            # Re-queue job for retry
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            logger.error(f"❌ Permanent failure for job {job_id}: {result.error_message}")
            # Don't re-queue permanent failures
            channel.basic_ack(delivery_tag=method.delivery_tag)

def main():
    """Main entry point"""
    worker = WorkerService()
    
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped by user")
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}")
        raise

if __name__ == "__main__":
    main()
