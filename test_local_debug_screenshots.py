#!/usr/bin/env python3
"""
Local test to verify debug screenshots work
"""
import asyncio
import os
from worker.core.scraper import GoogleAIModeScraper
from playwright.async_api import async_playwright

async def test_local_debug():
    print("Testing debug screenshots locally (not Docker)...")
    
    # Verify DEBUG is enabled
    debug_enabled = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    print(f"DEBUG enabled: {debug_enabled}")
    
    if not debug_enabled:
        print("ERROR: DEBUG must be set to true")
        return
    
    query = "what is artificial intelligence"
    
    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile_local",
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            page = await context.new_page()
            scraper = GoogleAIModeScraper()
            
            print(f"Running scraper with query: {query}")
            result = await scraper.scrape(page, query, "USA")
            
            print(f"Result: {result.success}")
            print(f"AI Mode Found: {result.ai_mode_found}")
            
            await context.close()
            
            # Check for screenshots
            import glob
            screenshots = glob.glob("debug_*.png")
            print(f"Screenshots created: {len(screenshots)}")
            for screenshot in screenshots:
                print(f"  - {screenshot}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_local_debug())
