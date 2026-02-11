#!/usr/bin/env python3
"""
Direct worker test with HEADLESS=false
"""
import asyncio
import sys
import os

# Add worker directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'worker'))

from core.scraper import GoogleAIModeScraper, LOCATION_CONFIG
from playwright.async_api import async_playwright, Page

async def test_worker_direct():
    """Test worker directly without RabbitMQ"""
    
    print("=== DIRECT WORKER TEST ===")
    print("Testing HEADLESS=false setup directly")
    print()
    
    # Test query
    query = "what is artificial intelligence"
    location = "USA"
    
    print(f"Query: {query}")
    print(f"Location: {location}")
    print(f"HEADLESS: {os.getenv('HEADLESS', 'false')}")
    print()
    
    try:
        # Initialize scraper
        scraper = GoogleAIModeScraper()
        
        # Get location settings
        if location not in LOCATION_CONFIG:
            raise ValueError(f"Invalid location: {location}")
        
        location_settings = LOCATION_CONFIG[location]
        
        print("1. Starting browser...")
        
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
        
        # Launch browser
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes"),
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
            
            print("2. Browser started successfully!")
            print("3. Starting scraping...")
            
            # Execute scrape
            result = await scraper.scrape(page, query, location)
            
            print("4. Scraping completed!")
            print()
            print("=== RESULTS ===")
            print(f"Success: {result.success}")
            print(f"AI Mode Found: {result.ai_mode_found}")
            print(f"AI Mode Text: {result.ai_mode_text}")
            print(f"Sources Count: {len(result.source_links)}")
            print(f"Error Message: {result.error_message}")
            print()
            
            if result.source_links:
                print("=== SOURCES ===")
                for i, source in enumerate(result.source_links[:3], 1):  # Show first 3
                    print(f"{i}. {source.text}")
                    print(f"   URL: {source.url}")
                    print(f"   Position: {source.position}")
                    print()
            
            return result.success
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Starting direct worker test...")
    print("This tests the scraper directly without RabbitMQ/API")
    print("You can observe the browser window with HEADLESS=false")
    print()
    
    success = asyncio.run(test_worker_direct())
    
    print("\n=== TEST RESULTS ===")
    if success:
        print("SUCCESS: Direct worker test completed")
        print("The scraper works with HEADLESS=false")
    else:
        print("FAILED: Direct worker test failed")
        print("Check the error messages above")
