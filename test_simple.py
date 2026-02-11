#!/usr/bin/env python3
"""
Simple direct worker test with HEADLESS=false
"""
import asyncio
import sys
import os

# Add worker directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'worker'))

from core.scraper import GoogleAIModeScraper, LOCATION_CONFIG
from playwright.async_api import async_playwright, Page

async def test_simple():
    """Simple test of the scraper"""
    
    print("=== SIMPLE SCRAPER TEST ===")
    print("Testing HEADLESS=false setup")
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
        
        print("1. Starting browser...")
        
        # Launch browser with minimal config
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes"),
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-infobars', 
                    '--disable-notifications',
                    '--start-maximized',
                    '--disable-gpu', 
                    '--window-size=1920,1080',
                ],
                ignore_default_args=['--enable-automation'],
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            print("2. Browser started successfully!")
            print("3. Starting scraping...")
            print("   You should see a browser window open")
            print("   Watch the automation process...")
            print()
            
            # Execute scrape
            result = await scraper.scrape(page, query, location)
            
            print("4. Scraping completed!")
            print()
            print("=== RESULTS ===")
            print(f"Success: {result.success}")
            print(f"AI Mode Found: {result.ai_mode_found}")
            print(f"Error: {result.error_message}")
            print()
            
            if result.ai_mode_found:
                print(f"AI Mode Text Length: {len(result.ai_mode_text)}")
                print(f"AI Mode Text Preview: {result.ai_mode_text[:200]}...")
                print()
                print(f"Sources Count: {len(result.source_links)}")
                
                if result.source_links:
                    print("First 3 sources:")
                    for i, source in enumerate(result.source_links[:3], 1):
                        print(f"  {i}. {source.text[:50]}... ({source.domain})")
            else:
                print("AI Mode was not found")
            
            await context.close()
            return result.success
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting simple scraper test...")
    print("This will open a browser window for HEADLESS=false testing")
    print()
    
    success = asyncio.run(test_simple())
    
    print("\n=== FINAL RESULT ===")
    if success:
        print("SUCCESS: Scraper test completed")
        print("The scraper works with HEADLESS=false")
        print("You can observe the browser automation")
    else:
        print("FAILED: Scraper test failed")
        print("Check the error messages above")
    
    input("\nPress Enter to exit...")
