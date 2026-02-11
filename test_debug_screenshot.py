#!/usr/bin/env python3
"""
Test Debug Screenshot in Main Scraper
Tests the updated scraper with DEBUG=true screenshot functionality
"""
import asyncio
import os
from worker.core.scraper import GoogleAIModeScraper
from playwright.async_api import async_playwright

async def test_debug_screenshot():
    """Test the main scraper with debug screenshot enabled"""
    
    print("=" * 80)
    print("DEBUG SCREENSHOT TEST")
    print("Testing main scraper with DEBUG=true")
    print("=" * 80)
    print()
    
    # Verify DEBUG is enabled
    debug_enabled = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    print(f"DEBUG environment variable: {os.getenv('DEBUG')}")
    print(f"Debug screenshots enabled: {debug_enabled}")
    print()
    
    if not debug_enabled:
        print("ERROR: DEBUG=true is not set in environment")
        print("Set DEBUG=true in .env file to enable screenshots")
        return False
    
    query = "what is artificial intelligence"
    location = "USA"
    
    print(f"Query: {query}")
    print(f"Location: {location}")
    print()
    print("INSTRUCTIONS:")
    print("1. Test will run the main scraper code")
    print("2. Screenshot will be taken when AI Mode link is found")
    print("3. Check for debug_ai_mode_found_TIMESTAMP.png file")
    print()
    
    try:
        print("Starting browser...")
        
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=True,  # Use headless for automated testing
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
            
            print("Browser started successfully!")
            print("Creating scraper instance...")
            
            # Create scraper instance
            scraper = GoogleAIModeScraper()
            
            print("Executing scraper...")
            print()
            print("=" * 80)
            print("SCRAPER EXECUTION")
            print("=" * 80)
            print()
            
            # Execute the scraper
            result = await scraper.scrape(page, query, location)
            
            print()
            print("=" * 80)
            print("SCRAPER RESULTS")
            print("=" * 80)
            print()
            
            print(f"Success: {result.success}")
            print(f"AI Mode Found: {result.ai_mode_found}")
            print(f"Query: {result.query}")
            print(f"Location: {result.location}")
            
            if result.error_message:
                print(f"Error: {result.error_message}")
            
            if result.ai_mode_text:
                print(f"AI Text Length: {len(result.ai_mode_text)} characters")
                print(f"AI Text Preview: {result.ai_mode_text[:200]}...")
            
            if result.source_links:
                print(f"Sources Found: {len(result.source_links)}")
            
            await context.close()
            
            return result.success
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    print("Testing debug screenshot functionality in main scraper...")
    print()
    
    success = asyncio.run(test_debug_screenshot())
    
    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("SUCCESS: Scraper executed with debug screenshots")
        print("Check for debug_ai_mode_found_TIMESTAMP.png files")
    else:
        print("FAILED: Scraper execution failed")
        print("Check the error messages above")
    
    print()
    print("Look for debug screenshot files in current directory")
    print("Filename format: debug_ai_mode_found_YYYYMMDD_HHMMSS.png")
    print()
