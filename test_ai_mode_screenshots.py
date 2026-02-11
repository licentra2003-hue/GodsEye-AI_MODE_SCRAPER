#!/usr/bin/env python3
"""
Test Correct AI Mode Link with Screenshots
Using page.get_by_role("link", name="AI Mode") approach with headless=true
"""
import asyncio
import random
from playwright.async_api import async_playwright, Page
import os

async def simple_search(page: Page, query: str, screenshot_dir: str):
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
        
        # Take screenshot BEFORE clicking AI Mode
        print("Taking screenshot BEFORE AI Mode click...")
        await page.screenshot(path=f"{screenshot_dir}/before_ai_mode_click.png", full_page=True)
        print(f"  Screenshot saved: {screenshot_dir}/before_ai_mode_click.png")
        
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
                
                # Take screenshot highlighting the AI Mode link
                print("Highlighting AI Mode link...")
                await ai_mode_link.highlight()
                await asyncio.sleep(1)
                await page.screenshot(path=f"{screenshot_dir}/ai_mode_highlighted.png", full_page=True)
                print(f"  Screenshot saved: {screenshot_dir}/ai_mode_highlighted.png")
                
                # Click the correct AI Mode link
                await ai_mode_link.click()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                print("  Google Search AI Mode link clicked successfully")
                
                # Take screenshot AFTER clicking AI Mode
                print("Taking screenshot AFTER AI Mode click...")
                await page.screenshot(path=f"{screenshot_dir}/after_ai_mode_click.png", full_page=True)
                print(f"  Screenshot saved: {screenshot_dir}/after_ai_mode_click.png")
                
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
    """Test the correct AI Mode approach with screenshots"""
    
    print("=" * 80)
    print("CORRECT AI MODE TEST WITH SCREENSHOTS")
    print("Using page.get_by_role('link', name='AI Mode') approach")
    print("HEADLESS: true (screenshots enabled)")
    print("=" * 80)
    print()
    
    query = "what is up"
    
    # Create screenshots directory
    screenshot_dir = "screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    print(f"Query: {query}")
    print(f"Screenshots will be saved to: {screenshot_dir}/")
    print()
    print("INSTRUCTIONS:")
    print("1. Test will run in headless mode")
    print("2. Screenshots will be taken at key moments")
    print("3. Check screenshots to verify AI Mode link detection")
    print()
    
    try:
        print("Starting browser...")
        
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="C:/temp/test_profile",
                headless=True,  # HEADLESS TRUE for screenshots
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
            
            # Execute the corrected approach with screenshots
            result = await simple_search(page, query, screenshot_dir)
            
            print()
            print("=" * 80)
            print("TEST RESULTS")
            print("=" * 80)
            print()
            
            if result:
                print("SUCCESS: Correct AI Mode link found and clicked")
                print()
                print("Screenshots taken:")
                print(f"  - {screenshot_dir}/before_ai_mode_click.png (before clicking)")
                print(f"  - {screenshot_dir}/ai_mode_highlighted.png (AI Mode highlighted)")
                print(f"  - {screenshot_dir}/after_ai_mode_click.png (after clicking)")
                print()
                print("Check the screenshots to verify:")
                print("  - AI Mode link is visible before click")
                print("  - AI Mode panel opens after click")
                print("  - Query executes in AI Mode")
                print()
                print("Wait 5 seconds for AI Mode to load...")
                await asyncio.sleep(5)
            else:
                print("FAILED: Correct AI Mode link NOT found")
                print()
                print("Screenshots taken:")
                print(f"  - {screenshot_dir}/before_ai_mode_click.png (page state)")
                print()
                print("Check the screenshot to see:")
                print("  - Page state before AI Mode click")
                print("  - Why AI Mode link wasn't found")
                print()
                print("Wait 2 seconds...")
                await asyncio.sleep(2)
            
            await context.close()
            return result
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    print("Starting correct AI Mode test with screenshots...")
    print("Using page.get_by_role approach with headless=true")
    print()
    
    success = asyncio.run(test_correct_ai_mode())
    
    print()
    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("SUCCESS: Found and clicked the correct Google Search AI Mode")
        print("Screenshots saved for verification")
    else:
        print("FAILED: Could not find the correct Google Search AI Mode link")
        print("Check screenshots to debug the issue")
    
    print()
    print("Screenshots saved in 'screenshots/' directory")
    print("Check the PNG files to see what happened")
    print()
