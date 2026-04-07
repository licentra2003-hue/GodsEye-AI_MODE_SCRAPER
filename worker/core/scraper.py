"""
Google AI Mode Scraper Core Logic - worker\core\scraper.py
Extracted from main.py for microservices architecture
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, quote_plus
import re
import base64
import io

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error
from playwright.async_api import TimeoutError as PlaywrightTimeout
from pydantic import BaseModel, ConfigDict, Field
from supabase import create_client, Client

load_dotenv()

# ==================== SUPABASE STORAGE FOR SCREENSHOTS ====================

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase_client = None

if supabase_url and supabase_key:
    supabase_client = create_client(supabase_url, supabase_key)

async def upload_screenshot_to_supabase(page: Page, name: str, job_id: str = None):
    """Take screenshot and upload to Supabase storage"""
    screenshot_enabled = os.getenv("SCREENSHOT", "false").lower() in ("true", "1", "yes")
    print(f"  🔍 DEBUG: SCREENSHOT env var = {os.getenv('SCREENSHOT', 'NOT SET')}")
    print(f"  🔍 DEBUG: screenshot_enabled = {screenshot_enabled}")
    
    if not screenshot_enabled:
        print(f"  ⚠️ Screenshots disabled, skipping upload")
        return None
    
    if not supabase_client:
        print(f"  ⚠️ Supabase client not configured, skipping screenshot upload")
        return None
    
    try:
        print(f"  📸 Taking screenshot: {name}")
        # Take screenshot as bytes
        screenshot_bytes = await page.screenshot(full_page=False, timeout=40000)
        
        # Create filename with timestamp and job_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_prefix = f"{job_id}_" if job_id else ""
        filename = f"{job_prefix}{name}_{timestamp}.png"
        
        # Upload to Supabase storage
        bucket_name = "debug_screenshots"
        storage_path = f"{filename}"
        
        print(f"  📤 Uploading to bucket: {bucket_name}")
        print(f"  📤 File path: {storage_path}")
        
        # Upload to Supabase using bytes directly
        supabase_client.storage.from_(bucket_name).upload(
            path=storage_path,
            file=screenshot_bytes
        )
        
        # Get public URL
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"
        print(f"  ✅ Screenshot uploaded: {name} -> {public_url}")
        return public_url
        
    except Exception as e:
        print(f"  ❌ Failed to upload screenshot '{name}': {e}")
        import traceback
        traceback.print_exc()
        return None

# ==================== DEBUG SCREENSHOT FUNCTION ====================

async def take_debug_screenshot(page: Page, name: str):
    """Take screenshot only if DEBUG=true in environment"""
    if os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_{name}_{timestamp}.png"
            await page.screenshot(path=filename, full_page=True, timeout=40000)
            print(f"  Debug screenshot saved: {filename}")
        except Exception as e:
            print(f"  Failed to take debug screenshot: {e}")

# ==================== LOCATION CONFIGURATION ====================

LOCATION_CONFIG = {
    # --- North America ---
    'USA': {
        'locale': 'en-US',
        'timezone_id': 'America/New_York',
        'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-US,en;q=0.9'}
    },
    'Mexico': {
        'locale': 'es-MX',
        'timezone_id': 'America/Mexico_City',
        'geolocation': {'latitude': 19.4326, 'longitude': -99.1332},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'es-MX,es;q=0.9'}
    },
    'Canada': {
        'locale': 'en-CA',
        'timezone_id': 'America/Toronto',
        'geolocation': {'latitude': 43.6532, 'longitude': -79.3832},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8'}
    },

    # --- Asia ---
    'India': {
        'locale': 'en-IN',
        'timezone_id': 'Asia/Kolkata',
        'geolocation': {'latitude': 12.9716, 'longitude': 77.5946},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7'}
    },
    'Indonesia': {
        'locale': 'id-ID',
        'timezone_id': 'Asia/Jakarta',
        'geolocation': {'latitude': -6.2088, 'longitude': 106.8456},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'id-ID,id;q=0.9'}
    },
    'Japan': {
        'locale': 'ja-JP',
        'timezone_id': 'Asia/Tokyo',
        'geolocation': {'latitude': 35.6895, 'longitude': 139.6917},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8'}
    },
    'South Korea': {
        'locale': 'ko-KR',
        'timezone_id': 'Asia/Seoul',
        'geolocation': {'latitude': 37.5665, 'longitude': 126.9780},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'}
    },
    'Philippines': {
        'locale': 'en-PH',
        'timezone_id': 'Asia/Manila',
        'geolocation': {'latitude': 14.5995, 'longitude': 120.9842},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-PH,en;q=0.9'}
    },
    'Singapore': {
        'locale': 'en-SG',
        'timezone_id': 'Asia/Singapore',
        'geolocation': {'latitude': 1.3521, 'longitude': 103.8198},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-SG,en;q=0.9,zh-CN;q=0.8'}
    },
    'Thailand': {
        'locale': 'th-TH',
        'timezone_id': 'Asia/Bangkok',
        'geolocation': {'latitude': 13.7563, 'longitude': 100.5018},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'th-TH,th;q=0.9,en;q=0.8'}
    },
    'Vietnam': {
        'locale': 'vi-VN',
        'timezone_id': 'Asia/Ho_Chi_Minh',
        'geolocation': {'latitude': 10.8231, 'longitude': 106.6297},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8'}
    },

    # --- Europe ---
    'UK': {
        'locale': 'en-GB',
        'timezone_id': 'Europe/London',
        'geolocation': {'latitude': 51.5074, 'longitude': -0.1278},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-GB,en;q=0.9'}
    },
    'Germany': {
        'locale': 'de-DE',
        'timezone_id': 'Europe/Berlin',
        'geolocation': {'latitude': 52.5200, 'longitude': 13.4050},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'}
    },
    'France': {
        'locale': 'fr-FR',
        'timezone_id': 'Europe/Paris',
        'geolocation': {'latitude': 48.8566, 'longitude': 2.3522},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'}
    },
    'Spain': {
        'locale': 'es-ES',
        'timezone_id': 'Europe/Madrid',
        'geolocation': {'latitude': 40.4168, 'longitude': -3.7038},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'}
    },
    'Italy': {
        'locale': 'it-IT',
        'timezone_id': 'Europe/Rome',
        'geolocation': {'latitude': 41.9028, 'longitude': 12.4964},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8'}
    },
    'Netherlands': {
        'locale': 'nl-NL',
        'timezone_id': 'Europe/Amsterdam',
        'geolocation': {'latitude': 52.3676, 'longitude': 4.9041},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8'}
    },
    'Poland': {
        'locale': 'pl-PL',
        'timezone_id': 'Europe/Warsaw',
        'geolocation': {'latitude': 52.2297, 'longitude': 21.0122},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8'}
    },
    'Sweden': {
        'locale': 'sv-SE',
        'timezone_id': 'Europe/Stockholm',
        'geolocation': {'latitude': 59.3293, 'longitude': 18.0686},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8'}
    },
    'Serbia': {
        'locale': 'sr-RS',
        'timezone_id': 'Europe/Belgrade',
        'geolocation': {'latitude': 44.7866, 'longitude': 20.4489},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'sr-RS,sr;q=0.9,en;q=0.8'}
    },

    # --- Oceania ---
    'Australia': {
        'locale': 'en-AU',
        'timezone_id': 'Australia/Sydney',
        'geolocation': {'latitude': -33.8688, 'longitude': 151.2093},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-AU,en;q=0.9'}
    },
    'New Zealand': {
        'locale': 'en-NZ',
        'timezone_id': 'Pacific/Auckland',
        'geolocation': {'latitude': -36.8485, 'longitude': 174.7633},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-NZ,en;q=0.9'}
    },

    # --- Africa ---
    'South Africa': {
        'locale': 'en-ZA',
        'timezone_id': 'Africa/Johannesburg',
        'geolocation': {'latitude': -26.2041, 'longitude': 28.0473},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-ZA,en;q=0.9'}
    },
    'Kenya': {
        'locale': 'en-KE',
        'timezone_id': 'Africa/Nairobi',
        'geolocation': {'latitude': -1.2921, 'longitude': 36.8219},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'en-KE,en;q=0.9,sw;q=0.8'}
    },

    # --- South America ---
    'Brazil': {
        'locale': 'pt-BR',
        'timezone_id': 'America/Sao_Paulo',
        'geolocation': {'latitude': -23.5505, 'longitude': -46.6333},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8'}
    },
    'Argentina': {
        'locale': 'es-AR',
        'timezone_id': 'America/Argentina/Buenos_Aires',
        'geolocation': {'latitude': -34.6037, 'longitude': -58.3816},
        'permissions': ['geolocation'],
        'extra_http_headers': {'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8'}
    },
}

# ==================== DATA MODELS ====================

class SourceLink(BaseModel):
    text: str = ""
    url: str = ""
    snippet: str = ""
    domain: str = ""
    favicon_url: str = ""
    thumbnail_url: str = ""
    date: str = ""
    position: int = 0

class AIModeResult(BaseModel):
    query: str = ""
    original_query: str = ""
    ai_mode_found: bool = False
    ai_mode_text: str = ""
    source_links: List[SourceLink] = Field(default_factory=list)
    success: bool = False
    timestamp: str = ""
    location: str = ""
    error_message: Optional[str] = None

# ==================== GOOGLE AI MODE SCRAPER ====================

class GoogleAIModeScraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        ]

    # async def scrape(self, page: Page, query: str, location: str = "India", job_id: str = None) -> AIModeResult:
    #     timestamp = datetime.now().isoformat()
        
    #     print(f"\n{'='*80}")
    #     print(f"Starting Google AI Mode Scraper")
    #     print(f"Query: {query}")
    #     print(f"Location: {location}")
    #     print(f"Job ID: {job_id}")
    #     print(f"{'='*80}\n")
        
    #     # Properly encode the query for URL
    #     encoded_query = quote_plus(query)
        
    #     try:
    #         # Step 1: Navigate to Google AI Mode directly with query
    #         print("Navigating to Google AI Mode with query...")
    #         await page.goto(f"https://www.google.com/search?udm=50&sei=&q={encoded_query}", wait_until="domcontentloaded", timeout=60000)
    #         await self._random_wait(0.5, 1.0)

    #         # Step 2: Handle cookie consent
    #         await self._handle_cookie_consent(page)

    #         # Step 3: Perform search and click AI Mode directly
    #         print(f"Searching for: '{query}'")
    #         # ai_mode_clicked = await self._simple_search(page, query, job_id)
            
    #         # if not ai_mode_clicked:
    #         #     print("Could not find or click AI Mode link")
    #         #     # Screenshot when AI Mode link not found
    #         #     await upload_screenshot_to_supabase(page, "98_ai_mode_not_found", job_id)
    #         #     return AIModeResult(
    #         #         query=query,
    #         #         original_query=query,
    #         #         ai_mode_found=False,
    #         #         success=False,
    #         #         timestamp=timestamp,
    #         #         location=location,
    #         #         error_message="AI Mode link not found on search results"
    #         #     )

    #         # Step 5: Wait for AI Mode to load and complete
    #         print("\nWaiting for AI Mode response to complete...")
    #         await self._wait_for_ai_mode_complete(page)

    #         # Check for bot detection
    #         page_text = await page.locator("body").inner_text()
    #         if self._is_bot_detected(page_text):
    #             print("Bot detection triggered!")
    #             # Screenshot when bot detection occurs
    #             await upload_screenshot_to_supabase(page, "99_bot_detection", job_id)
    #             return AIModeResult(
    #                 query=query,
    #                 original_query=query,
    #                 ai_mode_found=False,
    #                 success=False,
    #                 timestamp=timestamp,
    #                 location=location,
    #                 error_message="Bot detection / CAPTCHA encountered"
    #             )

    #         # Step 6: Verify AI Mode is present
    #         ai_mode_present = await self._detect_ai_mode(page)
    #         if not ai_mode_present:
    #             print("No AI Mode content found")
    #             # Screenshot when AI Mode content not detected
    #             await upload_screenshot_to_supabase(page, "97_ai_mode_content_not_found", job_id)
    #             return AIModeResult(
    #                 query=query,
    #                 original_query=query,
    #                 ai_mode_found=False,
    #                 success=False,
    #                 timestamp=timestamp,
    #                 location=location,
    #                 error_message="No AI Mode content detected"
    #             )

    #         # Step 7: Expand content if needed
    #         await self._expand_content(page)

    #         # Step 8: Extract AI Mode text
    #         print("\nExtracting AI Mode text...")
    #         ai_text = await self._extract_ai_mode_text(page)
            
    #         if not ai_text:
    #             print("Could not extract AI Mode text")
    #             return AIModeResult(
    #                 query=query,
    #                 original_query=query,
    #                 ai_mode_found=False,
    #                 success=False,
    #                 timestamp=timestamp,
    #                 location=location,
    #                 error_message="Could not extract AI Mode text content"
    #             )

    #         # Step 9: Click "Show all related links"
    #         print("\nClicking 'Show all related links'...")
    #         await self._show_all_sources(page)

    #         # Step 10: Extract sources
    #         print("\nExtracting sources...")
    #         sources = await self._extract_sources(page)

    #         print(f"\nSuccessfully extracted AI Mode response")
    #         print(f"  - Text length: {len(ai_text)} characters")
    #         print(f"  - Sources found: {len(sources)}")

    #         return AIModeResult(
    #             query=query,
    #             original_query=query,
    #             ai_mode_found=True,
    #             ai_mode_text=ai_text,
    #             source_links=sources,
    #             success=True,
    #             timestamp=timestamp,
    #             location=location
    #         )

    #     except Exception as e:
    #         print(f"\nCritical error: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         return AIModeResult(
    #             query=query,
    #             original_query=query,
    #             ai_mode_found=False,
    #             success=False,
    #             timestamp=timestamp,
    #             location=location,
    #             error_message=str(e)
    #         )


    # # working one
    # async def scrape(self, page: Page, query: str, location: str = "India", job_id: str = None) -> AIModeResult:
    #     """
    #     Hybrid Scraper Strategy:
    #     1. Navigate to Homepage (sets cookies/trust)
    #     2. Type and Search like a Human (establishes behavioral patterns)
    #     3. Force AI Mode via URL parameter (bypasses UI variations/missing buttons)
    #     """
    #     timestamp = datetime.now().isoformat()
        
    #     print(f"\n{'='*80}", flush=True)
    #     print(f" Starting Hybrid Google Scraper", flush=True)
    #     print(f"Query: {query}", flush=True)
    #     print(f"Location: {location}", flush=True)
    #     print(f"Job ID: {job_id}", flush=True)
    #     print(f"{'='*80}\n", flush=True)
        
    #     try:
    #         # ==============================================================================
    #         # STEP 1: ESTABLISH TRUST (Navigate to Homepage)
    #         # ==============================================================================
    #         print(" Navigating to Google Homepage...", flush=True)
    #         await page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=60000)
    #         await self._random_wait(1.0, 2.0)

    #         # Handle cookies immediately
    #         await self._handle_cookie_consent(page)

    #         # ==============================================================================
    #         # STEP 2: PERFORM HUMAN SEARCH
    #         # ==============================================================================
    #         print(" Performing human search...", flush=True)
    #         try:
    #             # Find search box (works for both desktop and mobile views)
    #             search_box = page.locator('textarea[name="q"], input[name="q"]').first
    #             await search_box.wait_for(state="visible", timeout=10000)
                
    #             # Click and Type
    #             await search_box.click()
    #             await self._random_wait(0.2, 0.5)
    #             await search_box.type(query, delay=random.uniform(50, 120))  # Slower, human-like typing
    #             await self._random_wait(0.5, 1.0)
                
    #             # Press Enter
    #             await page.keyboard.press("Enter")
    #             print("   Search submitted via keyboard", flush=True)
                
    #             # Wait for initial standard results to ensure session is registered
    #             await page.wait_for_selector('#search, #rso', timeout=20000)
    #             print("   Initial search results loaded", flush=True)
                
    #         except Exception as e:
    #             print(f"   Search interaction issue: {e}", flush=True)
    #             # Fallback: If typing failed, try direct nav (less safe, but better than crashing)
    #             encoded = quote_plus(query)
    #             await page.goto(f"https://www.google.com/search?q={encoded}", wait_until="domcontentloaded")

    #         await self._random_wait(2.0, 4.0)

    #         # ==============================================================================
    #         # STEP 3: FORCE AI MODE (The "Trojan Horse")
    #         # ==============================================================================
    #         # Instead of looking for a button, we modify the URL of the *active trusted session*
    #         current_url = page.url
            
    #         # Check if AI mode is already active (sometimes auto-triggers)
    #         if "udm=50" in current_url:
    #             print("   AI Mode already active in URL", flush=True)
    #         else:
    #             print(" Forcing AI Mode via URL parameter (maintaining trusted session)...", flush=True)
                
    #             # Construct new URL properly handling existing parameters
    #             separator = "&" if "?" in current_url else "?"
    #             new_url = f"{current_url}{separator}udm=50"
                
    #             # Navigate to the forced AI view
    #             await page.goto(new_url, wait_until="domcontentloaded")
    #             await self._random_wait(2.0, 3.0)

    #         # ==============================================================================
    #         # STEP 4: BOT DETECTION CHECK
    #         # ==============================================================================
    #         page_text = await page.locator("body").inner_text()
    #         if self._is_bot_detected(page_text):
    #             print(" Bot detection triggered!", flush=True)
    #             await upload_screenshot_to_supabase(page, "99_bot_detection", job_id)
    #             return AIModeResult(
    #                 query=query,
    #                 original_query=query,
    #                 ai_mode_found=False,
    #                 success=False,
    #                 timestamp=timestamp,
    #                 location=location,
    #                 error_message="Bot detection / CAPTCHA encountered"
    #             )

    #         # ==============================================================================
    #         # STEP 5: WAIT FOR & DETECT CONTENT
    #         # ==============================================================================
    #         print(" Waiting for AI content...", flush=True)
    #         await self._wait_for_ai_mode_complete(page)

    #         # Verify AI content presence
    #         ai_mode_present = await self._detect_ai_mode(page)
    #         if not ai_mode_present:
    #             print(" AI Mode content still not found after forcing", flush=True)
    #             await upload_screenshot_to_supabase(page, "97_ai_content_missing", job_id)
    #             return AIModeResult(
    #                 query=query,
    #                 original_query=query,
    #                 ai_mode_found=False,
    #                 success=False,
    #                 timestamp=timestamp,
    #                 location=location,
    #                 error_message="No AI Mode content detected"
    #             )

    #         # ==============================================================================
    #         # STEP 6: EXTRACT DATA
    #         # ==============================================================================
    #         # Expand "Show more" buttons
    #         await self._expand_content(page)

    #         # Extract Text
    #         print("\n Extracting AI Mode text...", flush=True)
    #         ai_text = await self._extract_ai_mode_text(page)
            
    #         if not ai_text:
    #             print(" Could not extract AI Mode text", flush=True)
    #             return AIModeResult(
    #                 query=query,
    #                 original_query=query,
    #                 ai_mode_found=False,
    #                 success=False,
    #                 timestamp=timestamp,
    #                 location=location,
    #                 error_message="Could not extract AI Mode text content"
    #             )

    #         # Extract Sources
    #         print("\n Clicking 'Show all related links'...", flush=True)
    #         await self._show_all_sources(page)

    #         print("\n Extracting sources...", flush=True)
    #         sources = await self._extract_sources(page)

    #         print(f"\n Successfully extracted AI Mode response", flush=True)
    #         print(f"  - Text length: {len(ai_text)} characters")
    #         print(f"  - Sources found: {len(sources)}")

    #         return AIModeResult(
    #             query=query,
    #             original_query=query,
    #             ai_mode_found=True,
    #             ai_mode_text=ai_text,
    #             source_links=sources,
    #             success=True,
    #             timestamp=timestamp,
    #             location=location
    #         )

    #     except Exception as e:
    #         print(f"\n Critical error: {e}", flush=True)
    #         import traceback
    #         traceback.print_exc()
    #         return AIModeResult(
    #             query=query,
    #             original_query=query,
    #             ai_mode_found=False,
    #             success=False,
    #             timestamp=timestamp,
    #             location=location,
    #             error_message=str(e)
    #         )

    async def _click_ai_mode_link(self, page: Page) -> bool:
        """Click the 'AI Mode' link on search results"""
        try:
            # Try multiple selectors for the AI Mode link
            selectors = [
                'a:has-text("AI Mode")',
                'link[name="AI Mode"]',
                'a[aria-label*="AI Mode"]',
                'div:has-text("AI Mode")',
            ]

            for selector in selectors:
                try:
                    ai_mode_link = page.locator(selector).first
                    if await ai_mode_link.is_visible(timeout=3000):
                        print(f"  Found AI Mode link: {selector}")

                        # Click with human-like behavior
                        await ai_mode_link.scroll_into_view_if_needed(timeout=3000)
                        await self._random_wait(0.2, 0.4)
                        await ai_mode_link.click()
                        await self._random_wait(1.0, 2.0)

                        print("  AI Mode link clicked successfully")
                        return True
                except:
                    continue

            print("  AI Mode link not found")
            return False

        except Exception as e:
            print(f"  Error clicking AI Mode: {e}")
            return False


    async def scrape(self, page: Page, query: str, location: str = "India", job_id: str = None) -> AIModeResult:
        """
        Robust Hybrid Strategy with Fallback:
        1.  **Natural Search:** Go to Home -> Type Query -> Enter.
        2.  **Attempt 1 (UI Interaction):** Try to click "AI Mode" button naturally.
        3.  **Attempt 2 (URL Injection):** If button missing, force `&udm=50` on the *existing* trusted session.
        """
        timestamp = datetime.now().isoformat()
        
        print(f"\n{'='*80}", flush=True)
        print(f"🤖 Starting Robust Google Scraper", flush=True)
        print(f"Query: {query}", flush=True)
        print(f"Job ID: {job_id}", flush=True)
        print(f"{'='*80}\n", flush=True)
        
        try:
            # ==============================================================================
            # PHASE 1: ESTABLISH TRUST & PERFORM NATURAL SEARCH
            # ==============================================================================
            print("🌐 1. Navigating to Homepage...", flush=True)
            await page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=60000)
            await self._random_wait(1.0, 2.0)
            await self._handle_cookie_consent(page)

            print("🔍 2. Performing Human Search...", flush=True)
            try:
                # Find search box
                search_box = page.locator('textarea[name="q"], input[name="q"]').first
                await search_box.wait_for(state="visible", timeout=10000)
                
                # Type query naturally
                await search_box.click()
                await self._random_wait(0.2, 0.5)
                await search_box.type(query, delay=random.uniform(40, 100)) 
                await self._random_wait(0.3, 0.8)
                
                # Press Enter
                await page.keyboard.press("Enter")
                print("   Query submitted via keyboard", flush=True)
                
                # Wait for *any* results to load (establishing the session)
                await page.wait_for_selector('#search, #rso', timeout=15000)
                print("   Initial search results page loaded", flush=True)
                
            except Exception as e:
                print(f"   ⚠️ Natural search failed ({e}), falling back to direct navigation...", flush=True)
                encoded = quote_plus(query)
                await page.goto(f"https://www.google.com/search?q={encoded}", wait_until="domcontentloaded", timeout=40000)

            await self._random_wait(2.0, 3.0)

            # ==============================================================================
            # PHASE 2: ATTEMPT NATURAL "AI MODE" CLICK
            # ==============================================================================
            ai_content_found = False
            
            # NOTE: Auto-detection of "AI Overview" removed as requested. 
            # We strictly want to find the AI Mode tab/button or force it.

            print("🖱️ 3. Attempting to find 'AI Mode' button...", flush=True)
            button_clicked = await self._click_ai_mode_link(page)
            
            if button_clicked:
                print("   Button clicked, waiting for content...", flush=True)
                await self._wait_for_ai_mode_complete(page)
                # Verify if clicking actually worked
                if await self._detect_ai_mode(page):
                    print("✨ AI Content loaded via button click!", flush=True)
                    ai_content_found = True
                else:
                    print("   Button clicked but no AI content detected. Moving to fallback...", flush=True)
            else:
                print("   Button not found. Moving to fallback...", flush=True)
                await upload_screenshot_to_supabase(page, "90_No_Button_Found", job_id)

            # ==============================================================================
            # PHASE 3: FALLBACK TO URL INJECTION (Triggered if Phase 2 Failed)
            # ==============================================================================
            if not ai_content_found:
                print("\n⚡ 4. Fallback: Forcing AI Mode via URL Parameter...", flush=True)
                current_url = page.url
                
                # Avoid double-injecting if we are already there
                if "udm=50" not in current_url:
                    separator = "&" if "?" in current_url else "?"
                    new_url = f"{current_url}{separator}udm=50"
                    
                    # Navigate keeping current session cookies
                    await page.goto(new_url, wait_until="domcontentloaded", timeout=40000)
                    await self._random_wait(2.0, 4.0)
                    await self._wait_for_ai_mode_complete(page)
                    await upload_screenshot_to_supabase(page, "81_fallback_ai_mode_url_injection", job_id)
                else:
                    print("   Already on udm=50 URL, just waiting...", flush=True)
                    await self._wait_for_ai_mode_complete(page)
                    

            # ==============================================================================
            # PHASE 4: BOT DETECTION & EXTRACTION
            # ==============================================================================
            
            # Check for Bot Detection (CAPTCHA)
            page_text = await page.locator("body").inner_text()
            if self._is_bot_detected(page_text):
                print("⚠️ Bot detection triggered!", flush=True)
                await upload_screenshot_to_supabase(page, "99_bot_detection", job_id)
                return AIModeResult(
                    query=query, original_query=query, ai_mode_found=False, success=False,
                    timestamp=timestamp, location=location,
                    error_message="Bot detection / CAPTCHA encountered"
                )

            # Check for Content presence
            ai_mode_present = await self._detect_ai_mode(page)
            if not ai_mode_present:
                print("❌ AI Mode content still not found after all attempts", flush=True)
                await upload_screenshot_to_supabase(page, "97_ai_content_missing", job_id)
                return AIModeResult(
                    query=query, original_query=query, ai_mode_found=False, success=False,
                    timestamp=timestamp, location=location,
                    error_message="No AI Mode content detected"
                )

            # Extract Data
            await self._expand_content(page)

            print("\n📝 Extracting Text...", flush=True)
            ai_text = await self._extract_ai_mode_text(page)
            
            if not ai_text:
                return AIModeResult(
                    query=query, original_query=query, ai_mode_found=False, success=False,
                    timestamp=timestamp, location=location,
                    error_message="Could not extract text content"
                )

            print("\n🔗 Extracting Sources...", flush=True)
            await self._show_all_sources(page)
            sources = await self._extract_sources(page)

            print(f"\n✅ SUCCESS: {len(ai_text)} chars, {len(sources)} sources")

            return AIModeResult(
                query=query, original_query=query,
                ai_mode_found=True, ai_mode_text=ai_text, source_links=sources,
                success=True, timestamp=timestamp, location=location
            )

        except Exception as e:
            print(f"\n❌ Critical error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return AIModeResult(
                query=query, original_query=query, ai_mode_found=False, success=False,
                timestamp=timestamp, location=location, error_message=str(e)
            )

    async def _wait_for_ai_mode_complete(self, page: Page):
        """Wait for AI Mode streaming to complete"""
        print("  Waiting for AI response to finish...")
        
        # Strategy 1: Wait for loading indicators to disappear
        try:
            loading_indicators = [
                'div[role="progressbar"]',
                'div[aria-busy="true"]',
                'div.loading',
            ]
            
            for indicator in loading_indicators:
                try:
                    loader = page.locator(indicator).first
                    if await loader.count() > 0:
                        await loader.wait_for(state="hidden", timeout=30000)
                        print("    Loading indicator disappeared")
                except:
                    pass
        except:
            pass

        # Strategy 2: Wait for AI Mode container
        try:
            # Wait for main containers to appear
            ai_containers = page.locator('div[data-subtree="aimfl"], div.Y3BBE, ul.KsbFXc')
            await ai_containers.first.wait_for(state="attached", timeout=15000)
            print("    AI Mode container detected")
        except Exception as e:
            print(f"    Container wait failed: {e}")

        # Strategy 3: Wait for content stabilization
        try:
            previous_text = ""
            stable_count = 0
            
            for i in range(8):  # Max 8 checks (16 seconds)
                await self._random_wait(2, 2.5)
                
                try:
                    current_text = await page.locator('body').inner_text()
                    
                    if current_text == previous_text:
                        stable_count += 1
                        if stable_count >= 2:  # Stable for 2 consecutive checks
                            print("    Content appears stable")
                            break
                    else:
                        stable_count = 0
                        previous_text = current_text
                except:
                    break
        except:
            pass

        # Final safety wait
        await self._random_wait(1.5, 2.5)

    # async def _detect_ai_mode(self, page: Page) -> bool:
    #     """Detect if AI Mode response is present"""
    #     print("  Detecting AI Mode content...")
        
    #     # Check for AI Mode specific indicators
    #     selectors = [
    #         'div[data-subtree="aimfl"]',  # Intro text
    #         'div.Y3BBE',                   # Main container
    #         'div.otQkpb',                  # Section headings
    #         'ul.KsbFXc',                   # Lists
    #         'ul.bTFeG',                    # Sources list
    #         'table.NRefec',                # Tables,
    #     ]
        
    #     for selector in selectors:
    #         try:
    #             if await page.locator(selector).count() > 0:
    #                 print(f"    Found AI Mode indicator: {selector}")
    #                 return True
    #         except:
    #             pass
        
    #     print("    No AI Mode indicators found")
    #     return False


    async def _detect_ai_mode(self, page: Page) -> bool:
        """Detect if AI Mode response is present"""
        print("  Detecting AI Mode content...")

        # Check for AI Mode specific indicators (these are for CONTENT, not button)
        selectors = [
            'div[data-subtree="aimfl"]',  # Intro text
            'div.Y3BBE',                   # Main container
            'div.otQkpb',                  # Section headings
            'ul.KsbFXc',                   # Lists
            'ul.bTFeG',                    # Sources list
            'table.NRefec',                # Tables
        ]

        for selector in selectors:
            try:
                if await page.locator(selector).count() > 0:
                    print(f"    Found AI Mode indicator: {selector}")
                    return True
            except:
                pass

        print("    No AI Mode indicators found")
        return False

    async def _expand_content(self, page: Page):
        """Expand all collapsible content"""
        print("  Expanding content...")
        
        expand_buttons = [
            'button:has-text("Show more")',
            'button:has-text("Show all")',
            'div[role="button"]:has-text("Show more")',
        ]
        
        for selector in expand_buttons:
            try:
                buttons = page.locator(selector)
                count = await buttons.count()
                
                for i in range(count):
                    try:
                        btn = buttons.nth(i)
                        if await btn.is_visible(timeout=1000):
                            await btn.click()
                            await self._random_wait(0.3, 0.5)
                            print(f"    Clicked expand button {i+1}")
                    except:
                        pass
            except:
                pass

    async def _extract_ai_mode_text(self, page: Page) -> str:
        """Extract AI Mode response text using the specific HTML structure"""
        print("  Extracting structured text...")
        
        try:
            # JavaScript extraction matching the HTML structure
            ai_text = await page.evaluate("""() => {
                const clean = (text) => text ? text.replace(/\\s+/g, ' ').trim() : '';
                
                // Target the specific selectors from AI Mode structure
                const elements = document.querySelectorAll(
                    'div[data-subtree="aimfl"], div.Y3BBE, div.otQkpb[role="heading"], ul.KsbFXc, table.NRefec'
                );
                
                let textParts = [];
                let seenText = new Set();
                
                for (const el of elements) {
                    // Skip hidden elements
                    if (el.offsetParent === null) continue;
                    
                    // Skip sources list (we handle this separately)
                    if (el.closest('ul.bTFeG')) continue;
                    
                    // 1. Handle Section Headings (div.otQkpb)
                    if (el.classList.contains('otQkpb') && el.getAttribute('role') === 'heading') {
                        let heading = clean(el.innerText);
                        // Remove "View related links" button text
                        heading = heading.replace(/View related links/gi, '').trim();
                        
                        if (heading && !seenText.has(heading)) {
                            textParts.push('\\n### ' + heading + '\\n');
                            seenText.add(heading);
                        }
                    }
                    // 2. Handle Lists (ul.KsbFXc)
                    else if (el.tagName === 'UL' && el.classList.contains('KsbFXc')) {
                        const listItems = Array.from(el.querySelectorAll('li'));
                        listItems.forEach(item => {
                            // Extract text from span.T286Pc or full li text
                            let itemText = '';
                            const spanText = item.querySelector('span.T286Pc');
                            if (spanText) {
                                itemText = clean(spanText.innerText);
                            } else {
                                itemText = clean(item.innerText);
                            }
                            
                            itemText = itemText.replace(/View related links/gi, '').trim();
                            
                            if (itemText && itemText.length > 10) {
                                textParts.push('• ' + itemText);
                            }
                        });
                        textParts.push('');  // Spacing after list
                    }
                    // 3. Handle Tables (table.NRefec)
                    else if (el.tagName === 'TABLE') {
                        textParts.push('\\n');
                        const rows = Array.from(el.querySelectorAll('tr'));
                        rows.forEach((row, idx) => {
                            const cells = Array.from(row.querySelectorAll('th, td'));
                            const cellTexts = cells.map(c => clean(c.innerText));
                            textParts.push('| ' + cellTexts.join(' | ') + ' |');
                            
                            // Add separator after header row
                            if (idx === 0 && row.querySelector('th')) {
                                textParts.push('| ' + cells.map(() => '---').join(' | ') + ' |');
                            }
                        });
                        textParts.push('');
                    }
                    // 4. Handle Text Containers (div.Y3BBE, div[data-subtree])
                    else if (el.classList.contains('Y3BBE') || el.hasAttribute('data-subtree')) {
                        // Skip if it contains lists/tables (already processed)
                        if (el.querySelector('ul.KsbFXc, table.NRefec')) continue;
                        
                        let text = clean(el.innerText);
                        text = text.replace(/View related links/gi, '').trim();
                        
                        if (text && !seenText.has(text) && text.length > 15) {
                            textParts.push(text);
                            seenText.add(text);
                        }
                    }
                }
                
                return textParts.join('\\n');
            }""")
            
            ai_text = self._clean_text(ai_text)
            print(f"    Extracted {len(ai_text)} characters")
            
            if len(ai_text) < 50:
                print("    Text seems too short, might be incomplete")
            
            return ai_text
            
        except Exception as e:
            print(f"    Failed to extract text: {e}")
            import traceback
            traceback.print_exc()
            return ""

    async def _show_all_sources(self, page: Page):
        """Click 'Show all related links' button"""
        print("  Looking for 'Show all related links' button...")
        
        # Try multiple possible selectors
        selectors = [
            'button:has-text("Show all related links")',
            'button[aria-label*="sites"]',
            'button.iqGHOe',  # Specific class from HTML
            'button:has-text("Show all")',
            'div[role="button"]:has-text("Show all")',
        ]
        
        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    print(f"    Found button: {selector}")
                    
                    await btn.scroll_into_view_if_needed(timeout=3000)
                    await self._random_wait(0.3, 0.5)
                    await btn.click()
                    await self._random_wait(1.0, 1.5)
                    
                    print("    Button clicked successfully")
                    
                    # Wait for sources panel to appear
                    try:
                        sources_panel = page.locator('ul.bTFeG, div[data-type="hovc"]').first
                        await sources_panel.wait_for(state="visible", timeout=5000)
                        print("    Sources panel appeared")
                    except:
                        print("    Sources panel not detected (might already be visible)")
                    
                    return
            except:
                continue
        
        print("    No 'Show all' button found (sources might already be expanded)")

    # async def _extract_sources(self, page: Page) -> List[SourceLink]:
    #     """Extract sources from ul.bTFeG > li.CyMdWb"""
    #     print("  Extracting sources from list...")
        
    #     sources = []
        
    #     try:
    #         # Find the sources list (ul.bTFeG)
    #         sources_list = page.locator('ul.bTFeG').first
            
    #         if await sources_list.count() == 0:
    #             print("    Sources list (ul.bTFeG) not found")
    #             return sources
            
    #         # Get all source items (li.CyMdWb)
    #         source_items = sources_list.locator('li.CyMdWb')
    #         item_count = await source_items.count()
            
    #         print(f"    Found {item_count} source items")
            
    #         for idx in range(item_count):
    #             try:
    #                 item = source_items.nth(idx)
                    
    #                 # Extract URL (a.NDNGvf)
    #                 url = ""
    #                 try:
    #                     anchor = item.locator('a.NDNGvf').first
    #                     url = await anchor.get_attribute('href') or ""
    #                 except:
    #                     pass
                    
    #                 if not url:
    #                     print(f"      Item {idx+1}: No URL found, skipping")
    #                     continue
                    
    #                 # Extract Title (div.Nn35F)
    #                 title = ""
    #                 try:
    #                     title_elem = item.locator('div.Nn35F').first
    #                     title = await title_elem.inner_text()
    #                 except:
    #                     title = "Unknown Title"
                    
    #                 # Extract Snippet (span.vhJ6Pe)
    #                 snippet = ""
    #                 try:
    #                     snippet_elem = item.locator('span.vhJ6Pe').first
    #                     snippet = await snippet_elem.inner_text()
    #                 except:
    #                     pass
                    
    #                 # Extract Domain (span.R0r5R)
    #                 domain = ""
    #                 try:
    #                     domain_elem = item.locator('span.R0r5R').first
    #                     domain = await domain_elem.inner_text()
    #                 except:
    #                     # Fallback: extract from URL
    #                     from urllib.parse import urlparse
    #                     parsed = urlparse(url)
    #                     domain = parsed.netloc
                    
    #                 # Extract Favicon (img.sGgDgb or img.aWLPic)
    #                 favicon_url = ""
    #                 try:
    #                     favicon_img = item.locator('img.sGgDgb, img.aWLPic').first
    #                     favicon_url = await favicon_img.get_attribute('src') or ""
    #                 except:
    #                     pass
                    
    #                 # Extract Thumbnail (img.nHPWpc)
    #                 thumbnail_url = ""
    #                 try:
    #                     thumbnail_img = item.locator('img.nHPWpc').first
    #                     thumbnail_url = await thumbnail_img.get_attribute('src') or ""
    #                 except:
    #                     pass
                    
    #                 # Extract Date (usually in snippet like "15 Jan 2026 —")
    #                 date = ""
    #                 try:
    #                     date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', snippet)
    #                     if date_match:
    #                         date = date_match.group(1)
    #                 except:
    #                     pass
                    
    #                 # Create source object
    #                 source = SourceLink(
    #                     text=self._clean_text(title),
    #                     url=url,
    #                     snippet=self._clean_text(snippet),
    #                     domain=self._clean_text(domain),
    #                     favicon_url=favicon_url,
    #                     thumbnail_url=thumbnail_url,
    #                     date=date,
    #                     position=len(sources) + 1
    #                 )
                    
    #                 sources.append(source)
    #                 print(f"      Source {idx+1}: {title[:50]}... ({domain})")
                    
    #             except Exception as e:
    #                 print(f"      Source {idx+1} error: {str(e)[:60]}")
    #                 continue
            
    #         print(f"\n    Successfully extracted {len(sources)} sources")
    #         return sources
            
    #     except Exception as e:
    #         print(f"    Failed to extract sources: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         return sources


    async def _extract_sources(self, page: Page) -> List[SourceLink]:
        """Extract sources using multiple selector strategies"""
        print("  📚 Extracting sources...")
        sources = []
        
        try:
            # Strategy 1: Look for the standard list items (legacy)
            # Strategy 2: Look for any source card that contains a domain (span.R0r5R)
            # Strategy 3: Look for links with specific source attributes
            
            # We'll use a broad evaluation to find source blocks regardless of container
            found_items = await page.evaluate("""() => {
                const items = [];
                const seenUrls = new Set();
                
                // Helper to clean text
                const clean = (t) => t ? t.textContent.replace(/\\s+/g, ' ').trim() : '';
                
                // Potential selectors for Source Cards
                // 1. The standard list item
                // 2. Any element containing a domain span (R0r5R)
                // 3. Grid items in AI overviews
                const selectors = [
                    'li.CyMdWb',                    // Standard list item
                    'div.MjjYud a.NDNGvf',          // Standard link container
                    'div.hJDwNd',                   // Carousel item
                    'div[jsname="I3kE2c"]',         // Generic source container
                    '.OSrXXb'                       // Another common card container
                ];
                
                // Collect all potential elements
                let allElements = [];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => allElements.push(el));
                });
                
                // If no specific containers found, look for the "Domain" span pattern
                if (allElements.length === 0) {
                    document.querySelectorAll('span.R0r5R').forEach(span => {
                        // Go up to find the main link container
                        const card = span.closest('a') || span.closest('div.MjjYud') || span.closest('li');
                        if (card) allElements.push(card);
                    });
                }

                for (const el of allElements) {
                    // Find the anchor tag
                    const anchor = el.tagName === 'A' ? el : el.querySelector('a');
                    if (!anchor) continue;
                    
                    const url = anchor.getAttribute('href');
                    if (!url || !url.startsWith('http') || seenUrls.has(url)) continue;
                    
                    // Exclude google links
                    if (url.includes('google.com')) continue;

                    seenUrls.add(url);
                    
                    // Extract Details
                    let title = '';
                    let domain = '';
                    let date = '';
                    
                    // Title: usually in div.Nn35F or h3
                    const titleEl = el.querySelector('div.Nn35F') || el.querySelector('h3') || el.querySelector('.LC20lb');
                    if (titleEl) title = clean(titleEl);
                    
                    // Domain: usually in span.R0r5R or cite
                    const domainEl = el.querySelector('span.R0r5R') || el.querySelector('cite') || el.querySelector('.VuuXrf');
                    if (domainEl) domain = clean(domainEl);
                    
                    // Snippet: usually in span.vhJ6Pe
                    const snippetEl = el.querySelector('span.vhJ6Pe') || el.querySelector('.VwiC3b');
                    let snippet = snippetEl ? clean(snippetEl) : '';
                    
                    // Extract Date from snippet (Regex fallback in python)
                    
                    // Images
                    const faviconEl = el.querySelector('img.sGgDgb') || el.querySelector('img.XNo5Ab');
                    const thumbEl = el.querySelector('img.nHPWpc');
                    
                    items.push({
                        url: url,
                        text: title || domain || 'Source',
                        snippet: snippet,
                        domain: domain,
                        favicon_url: faviconEl ? faviconEl.src : '',
                        thumbnail_url: thumbEl ? thumbEl.src : ''
                    });
                }
                return items;
            }""")
            
            # Process results into Pydantic models
            print(f"    ✓ Found {len(found_items)} potential sources via JS evaluation")
            
            for idx, item in enumerate(found_items):
                # Extra cleanup or validation if needed
                date = ""
                # Try to extract date from snippet
                try:
                    date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})|(\d{4}-\d{2}-\d{2})', item['snippet'])
                    if date_match:
                        date = date_match.group(0)
                except:
                    pass

                source = SourceLink(
                    text=self._clean_text(item['text']),
                    url=item['url'],
                    snippet=self._clean_text(item['snippet']),
                    domain=self._clean_text(item['domain']),
                    favicon_url=item['favicon_url'],
                    thumbnail_url=item['thumbnail_url'],
                    date=date,
                    position=len(sources) + 1
                )
                sources.append(source)
                print(f"      ✓ Source {idx+1}: {source.text[:40]}... ({source.domain})")

            return sources

        except Exception as e:
            print(f"    ✗ Failed to extract sources: {e}")
            import traceback
            traceback.print_exc()
            return []
    # ==================== UTILITY METHODS ====================

    def _is_bot_detected(self, page_text: str) -> bool:
        """Check if bot detection was triggered"""
        detection_keywords = [
            "captcha", "verify you are human", "unusual traffic",
            "automated queries", "not a robot"
        ]
        return any(keyword in page_text.lower() for keyword in detection_keywords)

    async def _handle_cookie_consent(self, page: Page):
        """Handle Google cookie consent popup"""
        print("Checking for cookie consent...")
        try:
            consent_selectors = [
                'button:has-text("Reject all")',
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                '#L2AGLb',
            ]

            for selector in consent_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        await button.click()
                        await self._random_wait(0.3, 0.6)
                        print("  Cookie consent handled")
                        return
                except:
                    continue
        except:
            pass

    # async def _simple_search(self, page: Page, query: str, job_id: str = None):
    #     """Simple search using AI Mode directly"""
    #     try:
    #         # Screenshot: Page load
    #         await upload_screenshot_to_supabase(page, "01_page_load", job_id)
            
    #         # Find search box
    #         search_box = page.locator('textarea[name="q"], input[name="q"]').first
    #         await search_box.wait_for(state="visible", timeout=20000)
            
    #         # Screenshot: Before typing
    #         await upload_screenshot_to_supabase(page, "02_before_typing", job_id)
            
    #         # Click and type like human
    #         await search_box.click()
    #         await self._random_wait(0.3, 0.5)
    #         await search_box.type(query, delay=random.uniform(30, 80))
    #         await self._random_wait(0.3, 0.5)
            
    #         # Screenshot: After typing
    #         await upload_screenshot_to_supabase(page, "03_after_typing", job_id)
            
    #         print("Looking for AI Mode link using get_by_role...")
            
    #         try:
    #             ai_mode_link = page.get_by_role("link", name="AI Mode")
                
    #             # Check if it's visible
    #             if await ai_mode_link.is_visible(timeout=3000):
    #                 # Get href to verify it's not workspace link
    #                 href = await ai_mode_link.get_attribute('href')
    #                 print(f"  Found AI Mode link with href: {href}")
                    
    #                 # Skip if it's Google Workspace link
    #                 if href and ('workspace.google.com' in href or 'google.com/workspace' in href):
    #                     print("  Skipping Google Workspace AI link (wrong one)")
    #                     return False
                    
    #                 # Screenshot before clicking AI Mode
    #                 await upload_screenshot_to_supabase(page, "04_ai_mode_found", job_id)
                    
    #                 # Scroll into view and click
    #                 await ai_mode_link.scroll_into_view_if_needed(timeout=3000)
    #                 await self._random_wait(0.2, 0.4)
    #                 await ai_mode_link.click()
    #                 await self._random_wait(1.0, 2.0)
                    
    #                 # Screenshot after clicking AI Mode
    #                 await upload_screenshot_to_supabase(page, "05_ai_mode_clicked", job_id)
                    
    #                 print("  AI Mode link clicked successfully")
    #                 return True
    #             else:
    #                 print("  AI Mode link not visible with get_by_role approach")
    #                 return False
    #         except Exception as e:
    #             print(f"  Error with get_by_role approach: {e}")
    #             return False
            
    #     except Exception as e:
    #         print(f"  Error in simple search: {e}")
    #         return False

    async def _simple_search(self, page: Page, query: str, job_id: str = None):
        """Simple search using AI Mode directly"""
        print("  DEBUG: _simple_search called", flush=True)
        try:
            # Screenshot: Page load
            print("  DEBUG: Taking page load screenshot", flush=True)
            await upload_screenshot_to_supabase(page, "01_page_load", job_id)
            
            # Find AI Mode search box
            search_box = page.get_by_role("textbox", name="Ask anything")
            await search_box.wait_for(state="visible", timeout=20000)
            
            # Screenshot: Before typing
            await upload_screenshot_to_supabase(page, "02_before_typing", job_id)
            
            # Click and type like human
            await search_box.click()
            await self._random_wait(0.3, 0.5)
            await search_box.type(query, delay=random.uniform(30, 80))
            await self._random_wait(0.3, 0.5)
            
            # Screenshot: After typing
            await upload_screenshot_to_supabase(page, "03_after_typing", job_id)
            print("  DEBUG: About to look for Send button", flush=True)
            
            # Try to click Send button, otherwise press Enter
            send_clicked = False
            print("  Looking for Send button...", flush=True)
            try:
                send_button = page.get_by_role("button", name="Send")
                print(f"  Send button locator created", flush=True)
                if await send_button.is_visible(timeout=2000):
                    print("  Send button is visible, clicking...", flush=True)
                    await send_button.click()
                    await self._random_wait(1.0, 2.0)
                    print("Send button clicked successfully", flush=True)
                    send_clicked = True
                else:
                    print("  Send button not visible", flush=True)
            except Exception as e:
                print(f"  Send button click failed: {e}", flush=True)
            
            if not send_clicked:
                print("  Send button not found, pressing Enter instead", flush=True)
                # Try multiple methods to submit the form
                try:
                    # Method 1: Press Enter on search box
                    await search_box.click()
                    await self._random_wait(0.2, 0.3)
                    print("  Pressing Enter key...", flush=True)
                    await search_box.press("Enter")
                    await self._random_wait(1.0, 2.0)
                    print("  Enter key pressed", flush=True)
                except Exception as e:
                    print(f"  Enter key failed: {e}", flush=True)
                    # Method 2: Press Enter on page keyboard
                    try:
                        print("  Trying page keyboard Enter...", flush=True)
                        await page.keyboard.press("Enter")
                        await self._random_wait(1.0, 2.0)
                        print("  Page keyboard Enter pressed", flush=True)
                    except Exception as e2:
                        print(f"  Page keyboard Enter failed: {e2}", flush=True)
                        # Method 3: Submit form directly
                        try:
                            print("  Trying form submit...", flush=True)
                            await page.evaluate("document.querySelector('textarea[name=\"q\"], input[name=\"q\"]').form.submit()")
                            await self._random_wait(1.0, 2.0)
                            print("  Form submitted", flush=True)
                        except Exception as e3:
                            print(f"  Form submit failed: {e3}", flush=True)
            
            # Screenshot: After clicking Send/Enter
            await upload_screenshot_to_supabase(page, "04_send_clicked", job_id)
            
            # Wait for AI response to load
            print("Waiting for AI response...")
            await self._random_wait(3.0, 5.0)
            
            # Screenshot: AI response loaded
            await upload_screenshot_to_supabase(page, "05_ai_response_loaded", job_id)
            
            print("AI Mode interaction completed successfully")
            return True
            
        except Exception as e:
            print(f"  Error in simple search: {e}")
            return False

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove citation markers like [1], [2]
        text = re.sub(r'\[\d+\]', '', text)
        
        # Remove button text artifacts
        text = text.replace('View related links', '')
        text = text.replace('Show all related links', '')
        
        return text.strip()

    async def _random_wait(self, min_seconds: float, max_seconds: float):
        """Human-like random delay"""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))
