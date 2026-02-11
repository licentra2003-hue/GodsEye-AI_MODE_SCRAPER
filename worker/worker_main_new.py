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

# Import LOCATION_CONFIG from working scraper
sys.path.append(str(Path(__file__).parent))
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
        
        # Force disable proxy configuration for Docker stability
        self.proxy_server = None
        self.proxy_username = None
        self.proxy_password = None
        
        # Initialize Supabase client
        self._init_supabase()
        
        logger.info(f"Worker {self.worker_id} initialized")
        logger.info(f"RabbitMQ URL: {self.rabbitmq_url}")
        logger.info(f"Supabase URL: {self.supabase_url}")
        logger.info(f"Proxy configured: {bool(self.proxy_server)}")
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            if self.supabase_url and self.supabase_key:
                # Create client without proxy - Supabase doesn't support proxy argument
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                
                logger.info("✅ Supabase client initialized")
            else:
                logger.warning("⚠ Supabase configuration missing")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
            # Continue without Supabase - worker can still process jobs
            self.supabase = None
    
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
        """Process a single scrape job"""
        job_data = json.loads(body.decode('utf-8'))
        job_id = job_data.get('job_id')
        query = job_data.get('query')
        location = job_data.get('location')
        product_id = job_data.get('product_id')
        
        logger.info(f"📋 Received job {job_id}: '{query}' in {location}")
        logger.info(f"   Product ID: {product_id}")
        
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
                channel.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.warning(f"⚠️ Job {job_id} failed: {result.error_message}")
                await self._handle_failure(job_id, result, channel, method)
                
        except Exception as e:
            logger.error(f"❌ Critical error processing job {job_id}: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        finally:
            # Clean up profile (Burn & Rotate strategy)
            if profile_path:
                self.profile_manager.cleanup_profile(profile_path)
                logger.info(f"🔥 Burned profile: {profile_path}")
    
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
        # Initialize stealth
        stealth = Stealth()
        
        # Get location settings
        if location not in LOCATION_CONFIG:
            raise ValueError(f"Invalid location: {location}")
        
        location_settings = LOCATION_CONFIG[location]
        
        async with stealth.use_async(async_playwright()) as p:
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
            proxy_url = None
            if self.proxy_server and self.proxy_username and self.proxy_password:
                proxy_url = f"http://{self.proxy_username}:{self.proxy_password}@{self.proxy_server}"
                logger.info(f"🌐 Using proxy: {self.proxy_server}")
            
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
                proxy={
                    "server": self.proxy_server,
                    "username": self.proxy_username,
                    "password": self.proxy_password
                } 
            )
            
            page = await context.new_page()
            
            # Add stealth scripts
            await self._add_stealth_scripts(page)
            
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
        """Save the scraping result to Supabase database"""
        try:
            # Prepare data for Supabase - matching API format with additional scraper data
            scrape_data = {
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
                "ai_mode_text": result.ai_mode_text
            }
            
            # Insert into Supabase
            response = self.supabase.table("product_analysis_google").insert(scrape_data).execute()
            
            if response.data:
                logger.info(f"✅ Saved to Supabase: {response.data[0].get('id')}")
                logger.info(f"   - Text length: {len(result.ai_mode_text)} chars")
                logger.info(f"   - Sources: {len(result.source_links)}")
            else:
                logger.error(f"❌ Failed to save to Supabase: {response}")
                
        except Exception as e:
            logger.error(f"❌ Database save error for job {job_id}: {e}")
            # Don't fail the job if database save fails
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
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped by user")
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}")
        raise

if __name__ == "__main__":
    main()
