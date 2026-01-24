#!/usr/bin/env python3
"""
Test the OAuth page to verify:
1. Does contact.swipswaps.com load?
2. What does backend status show?
3. What happens when clicking OAuth button?
"""
import asyncio
from playwright.async_api import async_playwright
import sys

async def test_oauth_page():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("=" * 60)
        print("TEST 1: Load contact.swipswaps.com")
        print("=" * 60)
        
        try:
            # Navigate to the page
            response = await page.goto("https://contact.swipswaps.com", timeout=30000)
            print(f"✅ Page loaded: {response.status}")
            
            # Wait for page to be ready
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Take screenshot
            await page.screenshot(path="/tmp/oauth_page_loaded.png")
            print("📸 Screenshot saved: /tmp/oauth_page_loaded.png")
            
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            await browser.close()
            return
        
        print("\n" + "=" * 60)
        print("TEST 2: Check backend status")
        print("=" * 60)
        
        try:
            # Wait for backend status to appear
            await page.wait_for_selector("#backend-status", timeout=10000)
            
            # Get backend status text
            status_element = await page.query_selector("#backend-status")
            status_text = await status_element.inner_text()
            print(f"Backend status: {status_text}")
            
            # Check if it shows connected or not available
            if "Connected" in status_text:
                print("✅ Backend is connected")
            elif "not available" in status_text:
                print("❌ Backend not available")
            else:
                print(f"⚠️  Unknown status: {status_text}")
                
        except Exception as e:
            print(f"❌ Failed to get backend status: {e}")
        
        print("\n" + "=" * 60)
        print("TEST 3: Click Google OAuth button")
        print("=" * 60)
        
        try:
            # Find and click Google OAuth button
            google_btn = await page.query_selector('button[data-provider="google"]')
            if google_btn:
                print("Found Google OAuth button")
                
                # Get current URL
                current_url = page.url
                print(f"Current URL: {current_url}")
                
                # Click the button
                await google_btn.click()
                print("Clicked Google OAuth button")
                
                # Wait for navigation or timeout
                try:
                    await page.wait_for_url(lambda url: url != current_url, timeout=10000)
                    new_url = page.url
                    print(f"✅ Redirected to: {new_url}")
                    
                    # Check if it's an error URL
                    if "error=oauth_failed" in new_url:
                        print("❌ OAuth failed - redirected to error page")
                    elif "user=" in new_url:
                        print("✅ OAuth succeeded - user data in URL")
                    else:
                        print(f"⚠️  Unexpected redirect: {new_url}")
                    
                    # Take screenshot of result
                    await page.screenshot(path="/tmp/oauth_result.png")
                    print("📸 Screenshot saved: /tmp/oauth_result.png")
                    
                except Exception as e:
                    print(f"⚠️  No redirect after 10s: {e}")
                    print("Page may have hung or is processing")
                    
            else:
                print("❌ Google OAuth button not found")
                
        except Exception as e:
            print(f"❌ Failed to test OAuth button: {e}")
        
        print("\n" + "=" * 60)
        print("TEST 4: Check page HTML for demo mode")
        print("=" * 60)
        
        # Get page content
        content = await page.content()
        if "demo" in content.lower():
            print("⚠️  Found 'demo' in page content")
        if "demo_token" in content:
            print("❌ Found 'demo_token' in page content")
        
        print("\n" + "=" * 60)
        print("Keeping browser open for 30 seconds for manual inspection...")
        print("=" * 60)
        await asyncio.sleep(30)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_oauth_page())

