#!/usr/bin/env python3
"""
Direct Scraper Test with HEADLESS=false
Uses the actual scraper code to debug AI Mode link detection
"""
import asyncio
import sys
import os

# Add worker directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'worker'))

from core.scraper import GoogleAIModeScraper, LOCATION_CONFIG
from playwright.async_api import async_playwright, Page

async def test_scraper_with_visual_debugging():
    """Test the actual scraper with HEADLESS=false for visual debugging"""
    
    print("=" * 80)
    print("SCRAPER VISUAL DEBUG TEST")
    print("Using actual scraper code with HEADLESS=false")
    print("=" * 80)
    print()
    
    # Test query
    query = "what is artificial intelligence"
    location = "USA"
    
    print(f"Query: {query}")
    print(f"Location: {location}")
    print(f"HEADLESS: false (GUI browser)")
    print()
    print("INSTRUCTIONS:")
    print("1. Watch the browser window open")
    print("2. Observe the search process")
    print("3. Look for the AI Mode link")
    print("4. Note if the link appears and if it's clicked")
    print()
    
    try:
        # Initialize the actual scraper
        scraper = GoogleAIModeScraper()
        
        # Get location settings
        if location not in LOCATION_CONFIG:
            raise ValueError(f"Invalid location: {location}")
        
        location_settings = LOCATION_CONFIG[location]
        
        print("Starting browser...")
        
        # Browser launch arguments (same as worker_main.py)
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
        
        # Launch browser with HEADLESS=false
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=False,  # GUI browser for visual debugging
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
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            print("Browser started successfully!")
            print("Starting scraper...")
            print()
            print("Watch the browser window to observe the process...")
            print()
            
            # Execute the actual scraper
            result = await scraper.scrape(page, query, location)
            
            print()
            print("=" * 80)
            print("SCRAPER RESULTS")
            print("=" * 80)
            print()
            print(f"Success: {result.success}")
            print(f"AI Mode Found: {result.ai_mode_found}")
            print(f"Error Message: {result.error_message}")
            print()
            
            if result.ai_mode_found:
                print(f"AI Mode Text Length: {len(result.ai_mode_text)}")
                print(f"AI Mode Text Preview: {result.ai_mode_text[:300]}...")
                print()
                print(f"Sources Count: {len(result.source_links)}")
                
                if result.source_links:
                    print()
                    print("First 5 sources:")
                    for i, source in enumerate(result.source_links[:5], 1):
                        print(f"  {i}. {source.text[:60]}... ({source.domain})")
            else:
                print("AI Mode was NOT found")
                print()
                print("This means the scraper failed to detect/click the AI Mode link")
                print("Watch the browser window to see what happened")
            
            await context.close()
            
            print()
            print("=" * 80)
            print("TEST COMPLETED")
            print("=" * 80)
            
            return result.success
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    print("Starting visual scraper test...")
    print("This will open a browser window so you can observe the process")
    print()
    
    success = asyncio.run(test_scraper_with_visual_debugging())
    
    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("SUCCESS: Scraper test completed")
        print("The scraper found AI Mode successfully")
    else:
        print("FAILED: Scraper test failed")
        print("The scraper did not find AI Mode")
        print("Observe the browser window to see what went wrong")
    
    print()
    print("Press Enter to exit...")
    input()
