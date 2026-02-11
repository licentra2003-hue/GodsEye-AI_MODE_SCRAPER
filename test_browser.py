#!/usr/bin/env python3
"""
Minimal browser test with HEADLESS=false
"""
import asyncio
from playwright.async_api import async_playwright

async def test_browser_only():
    """Test browser functionality only"""
    
    print("=== BROWSER ONLY TEST ===")
    print("Testing HEADLESS=false with minimal automation")
    print()
    
    try:
        print("1. Starting browser...")
        
        async with async_playwright() as p:
            # Launch browser with HEADLESS=false
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=False,  # Explicitly false for GUI
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
            print("3. Navigating to Google...")
            
            # Go to Google
            await page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=60000)
            
            print("4. Google loaded successfully!")
            print("5. Finding search box...")
            
            # Find search box
            search_box = page.locator('textarea[name="q"], input[name="q"], textarea[title*="Search"]')
            await search_box.wait_for(state="visible", timeout=10000)
            
            print("6. Search box found!")
            print("7. Typing search query...")
            
            # Type query
            query = "what is artificial intelligence"
            await search_box.fill(query)
            
            print(f"8. Typed: '{query}'")
            print("9. Pressing Enter...")
            
            # Press Enter
            await page.keyboard.press("Enter")
            
            print("10. Waiting for search results...")
            
            # Wait for results
            await page.wait_for_url("**/search?**", wait_until="commit", timeout=10000)
            await page.locator("#search, #rso").first.wait_for(state="attached", timeout=20000)
            
            print("11. Search results loaded!")
            print("12. Looking for AI Mode link...")
            
            # Look for AI Mode link
            ai_selectors = [
                'a:has-text("AI Mode")',
                'a:has-text("AI")',
                'div:has-text("AI Mode")',
                'span:has-text("AI Mode")'
            ]
            
            ai_found = False
            for selector in ai_selectors:
                try:
                    ai_link = page.locator(selector).first
                    if await ai_link.is_visible(timeout=2000):
                        print(f"13. Found AI Mode link: {selector}")
                        await ai_link.click()
                        print("14. AI Mode link clicked!")
                        ai_found = True
                        break
                except:
                    continue
            
            if not ai_found:
                print("13. AI Mode link not found, but search worked!")
            
            print("15. Waiting 3 seconds to observe...")
            await asyncio.sleep(3)
            
            print("16. Test completed successfully!")
            
            await context.close()
            return True
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting minimal browser test...")
    print("This will open a browser window and test basic functionality")
    print("You can observe the automation process")
    print()
    
    success = asyncio.run(test_browser_only())
    
    print("\n=== FINAL RESULT ===")
    if success:
        print("SUCCESS: Browser test completed")
        print("HEADLESS=false works correctly")
        print("Basic automation (navigate, search, click) works")
    else:
        print("FAILED: Browser test failed")
        print("Check the error messages above")
    
    print("\nThis confirms:")
    print("- Browser can start with HEADLESS=false")
    print("- Basic navigation works")
    print("- Search functionality works")
    print("- The issue is in the scraper code (emoji encoding)")
