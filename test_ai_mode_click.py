#!/usr/bin/env python3
"""
Test AI Mode Link Clicking
Uses the exact _simple_search code to test AI Mode button detection
"""
import asyncio
import random
from playwright.async_api import async_playwright, Page

async def simple_search(page: Page, query: str):
    """Simple search using AI Mode directly - EXACT CODE FROM USER"""
    try:
        # Find search box
        search_box = page.locator('textarea[name="q"], input[name="q"]').first
        await search_box.wait_for(state="visible", timeout=20000)
        
        # Click and fill
        await search_box.click()
        await asyncio.sleep(random.uniform(0.2, 0.3))
        await search_box.fill(query)
        await asyncio.sleep(random.uniform(0.3, 0.5))
        
        # Look for AI Mode link immediately (before pressing Enter)
        print("Looking for AI Mode link...")
        ai_mode_selectors = [
            'a:has-text("AI Mode")',
            'a:has-text("AI")',
            'span:has-text("AI Mode")',
            'div:has-text("AI") a',
            'button:has-text("AI Mode")',
            '[aria-label*="AI"]'
        ]
        
        for selector in ai_mode_selectors:
            try:
                ai_mode_link = page.locator(selector).first
                if await ai_mode_link.is_visible(timeout=2000):
                    print(f"  Found AI Mode link with selector: {selector}")
                    
                    # Scroll into view and click
                    await ai_mode_link.scroll_into_view_if_needed(timeout=3000)
                    await asyncio.sleep(random.uniform(0.2, 0.4))
                    await ai_mode_link.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    print("  AI Mode link clicked successfully")
                    return True
            except:
                continue
        
        print("  Could not find or click AI Mode link")
        return False
        
    except Exception as e:
        print(f"  Error in simple search: {e}")
        return False

async def test_ai_mode_click():
    """Test if AI Mode link is found and clicked"""
    
    print("=" * 80)
    print("AI MODE LINK CLICKING TEST")
    print("Testing exact _simple_search code")
    print("=" * 80)
    print()
    
    query = "what is artificial intelligence"
    
    print(f"Query: {query}")
    print("HEADLESS: false (GUI browser)")
    print()
    print("INSTRUCTIONS:")
    print("1. Watch the browser window open")
    print("2. Observe if AI Mode link is found")
    print("3. Observe if AI Mode link is clicked")
    print("4. Observe if query is executed in AI Mode")
    print()
    
    try:
        print("Starting browser...")
        
        async with async_playwright() as p:
            # Launch browser with HEADLESS=false
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=False,  # GUI browser for visual debugging
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
            print("Navigating to Google...")
            
            # Go to Google
            await page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(1)
            
            print("Google loaded successfully!")
            print()
            print("=" * 80)
            print("EXECUTING SIMPLE SEARCH")
            print("=" * 80)
            print()
            
            # Execute the exact _simple_search code
            result = await simple_search(page, query)
            
            print()
            print("=" * 80)
            print("TEST RESULTS")
            print("=" * 80)
            print()
            
            if result:
                print("SUCCESS: AI Mode link was found and clicked")
                print()
                print("What to observe:")
                print("  - Did the AI Mode panel open?")
                print("  - Did the query execute in AI Mode?")
                print("  - Did AI Mode content appear?")
                print()
                print("Wait 5 seconds to observe the result...")
                await asyncio.sleep(5)
            else:
                print("FAILED: AI Mode link was NOT found or clicked")
                print()
                print("What to observe:")
                print("  - Is the AI Mode link visible on the page?")
                print("  - Is it in a different location?")
                print("  - Does it appear after some action?")
                print()
                print("Wait 5 seconds to observe the page state...")
                await asyncio.sleep(5)
            
            await context.close()
            
            return result
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    print("Starting AI Mode link clicking test...")
    print("This will open a browser window to observe the process")
    print()
    
    success = asyncio.run(test_ai_mode_click())
    
    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("SUCCESS: AI Mode link was found and clicked")
        print("The exact _simple_search code works correctly")
    else:
        print("FAILED: AI Mode link was NOT found or clicked")
        print("The selectors or timing might need adjustment")
    
    print()
    print("Press Enter to exit...")
    input()
