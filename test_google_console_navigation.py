#!/usr/bin/env python3
"""
Navigate Google Cloud Console to find the correct OAuth setup path.
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def navigate_google_console():
    async with async_playwright() as p:
        # Use Firefox instead of Chromium
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("=" * 60)
        print("STEP 1: Open Google Cloud Console API Library")
        print("=" * 60)
        
        await page.goto("https://console.cloud.google.com/apis/library?project=gen-lang-client-0071742907")
        await page.wait_for_load_state("networkidle", timeout=30000)
        
        # Take screenshot
        await page.screenshot(path="/tmp/api_library.png")
        print("📸 Screenshot: /tmp/api_library.png")
        
        print("\n" + "=" * 60)
        print("STEP 2: Search for 'People API'")
        print("=" * 60)
        
        # Look for search box
        search_selectors = [
            'input[type="search"]',
            'input[placeholder*="Search"]',
            'input[aria-label*="Search"]',
            '#searchbox',
            '[role="searchbox"]'
        ]
        
        search_box = None
        for selector in search_selectors:
            try:
                search_box = await page.query_selector(selector)
                if search_box:
                    print(f"✅ Found search box: {selector}")
                    break
            except:
                continue
        
        if search_box:
            await search_box.fill("People API")
            await search_box.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=10000)
            await page.screenshot(path="/tmp/people_api_search.png")
            print("📸 Screenshot: /tmp/people_api_search.png")
            
            # Look for People API result
            await asyncio.sleep(2)
            content = await page.content()
            if "People API" in content:
                print("✅ Found 'People API' in results")
            else:
                print("❌ 'People API' not found in results")
                print("Trying 'Google+ API' instead...")
                
                await search_box.fill("Google+ API")
                await search_box.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=10000)
                await page.screenshot(path="/tmp/googleplus_api_search.png")
                print("📸 Screenshot: /tmp/googleplus_api_search.png")
        else:
            print("❌ Could not find search box")
            print("Available input elements:")
            inputs = await page.query_selector_all('input')
            for i, inp in enumerate(inputs[:5]):
                inp_type = await inp.get_attribute('type')
                inp_placeholder = await inp.get_attribute('placeholder')
                print(f"  Input {i}: type={inp_type}, placeholder={inp_placeholder}")
        
        print("\n" + "=" * 60)
        print("STEP 3: Navigate to OAuth Consent Screen")
        print("=" * 60)
        
        await page.goto("https://console.cloud.google.com/apis/credentials/consent?project=gen-lang-client-0071742907")
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.screenshot(path="/tmp/oauth_consent_screen.png")
        print("📸 Screenshot: /tmp/oauth_consent_screen.png")
        
        # Check what's on the page
        content = await page.content()
        if "OAuth consent screen" in content:
            print("✅ On OAuth consent screen page")
        if "CONFIGURE CONSENT SCREEN" in content:
            print("⚠️  Consent screen not configured yet")
        if "Edit app registration" in content:
            print("✅ Consent screen already configured")
        
        print("\n" + "=" * 60)
        print("STEP 4: Navigate to Credentials page")
        print("=" * 60)
        
        await page.goto("https://console.cloud.google.com/apis/credentials?project=gen-lang-client-0071742907")
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.screenshot(path="/tmp/credentials_page.png")
        print("📸 Screenshot: /tmp/credentials_page.png")
        
        # Look for "Create Credentials" button
        create_btn_selectors = [
            'button:has-text("CREATE CREDENTIALS")',
            'button:has-text("Create Credentials")',
            '[aria-label*="Create"]',
            'text=CREATE CREDENTIALS'
        ]
        
        for selector in create_btn_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    print(f"✅ Found 'Create Credentials' button: {selector}")
                    break
            except:
                continue
        
        print("\n" + "=" * 60)
        print("Keeping browser open for 60 seconds for manual inspection...")
        print("=" * 60)
        await asyncio.sleep(60)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(navigate_google_console())

