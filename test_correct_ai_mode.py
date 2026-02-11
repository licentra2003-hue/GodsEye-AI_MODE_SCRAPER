#!/usr/bin/env python3
"""
Test Correct AI Mode Link Detection
Find the actual Google Search AI Mode link, not Google Workspace AI
"""
import asyncio
import random
from playwright.async_api import async_playwright, Page

async def find_correct_ai_mode_link(page: Page, query: str):
    """Find the CORRECT Google Search AI Mode link"""
    try:
        # Find search box
        search_box = page.locator('textarea[name="q"], input[name="q"]').first
        await search_box.wait_for(state="visible", timeout=20000)
        
        # Click and fill
        await search_box.click()
        await asyncio.sleep(random.uniform(0.2, 0.3))
        await search_box.fill(query)
        await asyncio.sleep(random.uniform(0.3, 0.5))
        
        # Press Enter first to get search results
        print("Pressing Enter to get search results...")
        await search_box.press("Enter")
        await asyncio.sleep(2)  # Wait for results to load
        
        # Now look for the CORRECT AI Mode link on search results page
        print("Looking for CORRECT Google Search AI Mode link...")
        
        # More specific selectors for Google Search AI Mode
        ai_mode_selectors = [
            # Try to find AI Mode specifically in search context
            'div[role="main"] a:has-text("AI Mode")',
            'div#search a:has-text("AI Mode")',
            'div#rso a:has-text("AI Mode")',
            'div[role="navigation"] a:has-text("AI Mode")',
            'div[role="banner"] a:has-text("AI Mode")',
            # Alternative approaches
            'a[href*="ai"] a:has-text("AI Mode")',
            'a[data-ved*="ai"] a:has-text("AI Mode")',
            'button[aria-label*="AI Mode"]',
            'div[role="button"]:has-text("AI Mode")',
            # Fallback - be more specific about context
            'a:has-text("AI Mode"):not([href*="workspace"])',
            'a:has-text("AI Mode"):not([href*="google.com/workspace"])',
        ]
        
        for selector in ai_mode_selectors:
            try:
                ai_mode_link = page.locator(selector).first
                if await ai_mode_link.is_visible(timeout=2000):
                    # Get the href to verify it's the right link
                    href = await ai_mode_link.get_attribute('href')
                    print(f"  Found AI Mode link with selector: {selector}")
                    print(f"  Link href: {href}")
                    
                    # Skip if it's Google Workspace link
                    if href and ('workspace.google.com' in href or 'google.com/workspace' in href):
                        print("  Skipping Google Workspace AI link (wrong one)")
                        continue
                    
                    # This should be the correct link
                    print("  Found potential Google Search AI Mode link!")
                    
                    # Scroll into view and click
                    await ai_mode_link.scroll_into_view_if_needed(timeout=3000)
                    await asyncio.sleep(random.uniform(0.2, 0.4))
                    await ai_mode_link.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    print("  Google Search AI Mode link clicked successfully")
                    return True
            except:
                continue
        
        print("  Could not find CORRECT Google Search AI Mode link")
        return False
        
    except Exception as e:
        print(f"  Error finding AI Mode link: {e}")
        return False

async def test_correct_ai_mode():
    """Test finding the correct Google Search AI Mode link"""
    
    print("=" * 80)
    print("CORRECT AI MODE LINK TEST")
    print("Finding Google Search AI Mode (not Google Workspace AI)")
    print("=" * 80)
    print()
    
    query = "what is artificial intelligence"
    
    print(f"Query: {query}")
    print("HEADLESS: false (GUI browser)")
    print()
    print("INSTRUCTIONS:")
    print("1. Watch the browser window open")
    print("2. Observe search results page")
    print("3. Look for the correct AI Mode link")
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
            print("SEARCHING FOR CORRECT AI MODE")
            print("=" * 80)
            print()
            
            result = await find_correct_ai_mode_link(page, query)
            
            print()
            print("=" * 80)
            print("TEST RESULTS")
            print("=" * 80)
            print()
            
            if result:
                print("SUCCESS: Correct Google Search AI Mode link found and clicked")
                print()
                print("What to observe:")
                print("  - Did AI Mode panel open on search results?")
                print("  - Did the query execute in AI Mode?")
                print("  - Did we stay on Google (not workspace.google.com)?")
                print()
                print("Wait 10 seconds to observe the result...")
                await asyncio.sleep(10)
            else:
                print("FAILED: Correct Google Search AI Mode link NOT found")
                print()
                print("What to observe:")
                print("  - Are there any AI Mode links on the page?")
                print("  - Do they all go to Google Workspace?")
                print("  - Is AI Mode not available right now?")
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
    print("Starting correct AI Mode link test...")
    print("This will find the Google Search AI Mode (not Workspace AI)")
    print()
    
    success = asyncio.run(test_correct_ai_mode())
    
    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("SUCCESS: Found and clicked the correct Google Search AI Mode")
    else:
        print("FAILED: Could not find the correct Google Search AI Mode link")
        print("The AI Mode might be in a different location or not available")
    
    print()
    print("Press Enter to exit...")
    input()
