#!/usr/bin/env python3
"""
Test Correct AI Mode Link
Using page.get_by_role("link", name="AI Mode") approach
"""
import asyncio
import random
from playwright.async_api import async_playwright, Page

async def simple_search(page: Page, query: str):
    """Simple search using AI Mode directly - CORRECTED APPROACH"""
    try:
        # Find search box
        search_box = page.locator('textarea[name="q"], input[name="q"]').first
        await search_box.wait_for(state="visible", timeout=20000)
        
        # Click and fill
        await search_box.click()
        await asyncio.sleep(random.uniform(0.2, 0.3))
        await search_box.fill(query)
        await asyncio.sleep(random.uniform(0.3, 0.5))
        
        # Use the exact Playwright approach - page.get_by_role("link", name="AI Mode")
        print("Looking for AI Mode link using get_by_role...")
        
        try:
            ai_mode_link = page.get_by_role("link", name="AI Mode")
            
            # Check if it's visible
            if await ai_mode_link.is_visible(timeout=3000):
                # Get href to verify it's not workspace link
                href = await ai_mode_link.get_attribute('href')
                print(f"  Found AI Mode link with href: {href}")
                
                # Skip if it's Google Workspace link
                if href and ('workspace.google.com' in href or 'google.com/workspace' in href):
                    print("  Skipping Google Workspace AI link (wrong one)")
                    return False
                
                # Click the correct AI Mode link
                await ai_mode_link.click()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                print("  Google Search AI Mode link clicked successfully")
                return True
            else:
                print("  AI Mode link not visible with get_by_role approach")
                return False
                
        except Exception as e:
            print(f"  Error with get_by_role approach: {e}")
            return False
        
    except Exception as e:
        print(f"  Error in simple search: {e}")
        return False

async def test_correct_ai_mode():
    """Test the correct AI Mode approach"""
    
    print("=" * 80)
    print("CORRECT AI MODE TEST")
    print("Using page.get_by_role('link', name='AI Mode') approach")
    print("=" * 80)
    print()
    
    query = "what is up"
    
    print(f"Query: {query}")
    print("HEADLESS: false (GUI browser)")
    print()
    print("INSTRUCTIONS:")
    print("1. Watch the browser window open")
    print("2. Observe search box being filled")
    print("3. Observe correct AI Mode link being clicked")
    print("4. Verify it doesn't go to workspace.google.com")
    print()
    
    try:
        print("Starting browser...")
        
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=False,
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
            
            await page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(1)
            
            print("Google loaded successfully!")
            print()
            print("=" * 80)
            print("EXECUTING CORRECT AI MODE SEARCH")
            print("=" * 80)
            print()
            
            # Execute the corrected approach
            result = await simple_search(page, query)
            
            print()
            print("=" * 80)
            print("TEST RESULTS")
            print("=" * 80)
            print()
            
            if result:
                print("SUCCESS: Correct AI Mode link found and clicked")
                print()
                print("What to observe:")
                print("  - Did AI Mode panel open?")
                print("  - Did query execute without pressing Enter?")
                print("  - Did we stay on Google (not workspace.google.com)?")
                print("  - Did we get AI Mode response for the query?")
                print()
                print("Wait 10 seconds to observe the result...")
                await asyncio.sleep(10)
            else:
                print("FAILED: Correct AI Mode link NOT found")
                print()
                print("What to observe:")
                print("  - Is there a different AI Mode link?")
                print("  - Does it appear after typing the query?")
                print("  - Is it in a different location on the page?")
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
    print("Starting correct AI Mode test...")
    print("Using page.get_by_role approach to avoid workspace links")
    print()
    
    success = asyncio.run(test_correct_ai_mode())
    
    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("SUCCESS: Found and clicked the correct Google Search AI Mode")
        print("The get_by_role approach works!")
    else:
        print("FAILED: Could not find the correct Google Search AI Mode link")
        print("May need to investigate the page structure further")
    
    print()
    print("Press Enter to exit...")
    input()
