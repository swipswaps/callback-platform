#!/usr/bin/env python3
"""
Selenium test for callback platform frontend.
Tests backend detection and UI visibility per Rule 22, 27, 35, 40, 42.
"""

import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options

def test_frontend(url="http://localhost:3000"):
    """Test frontend with Selenium per Rule 35 (Firefox priority)."""

    print("=" * 60)
    print("SELENIUM TEST - Callback Platform Frontend")
    print("=" * 60)
    print(f"Testing URL: {url}")

    # Setup Firefox with headless option
    options = Options()
    # Don't use headless - we want to see it
    # options.add_argument('--headless')

    driver = None
    try:
        print("\n[1/6] Starting Firefox browser...")
        driver = webdriver.Firefox(options=options)
        driver.set_window_size(1280, 1024)
        print("✓ Firefox started")

        print(f"\n[2/6] Loading {url}...")
        driver.get(url)
        time.sleep(3)  # Wait for page load and backend detection
        print("✓ Page loaded")
        
        print("\n[3/6] Checking for backend status indicator...")
        backend_status = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "backend-status"))
        )
        print(f"✓ Backend status element found")
        print(f"  Display: {backend_status.value_of_css_property('display')}")
        print(f"  Visibility: {backend_status.is_displayed()}")
        
        print("\n[4/6] Reading backend status text...")
        status_text_elem = driver.find_element(By.CLASS_NAME, "status-text")
        status_text = status_text_elem.text
        print(f"✓ Status text: '{status_text}'")
        
        print("\n[5/6] Checking status icon...")
        status_icon_elem = driver.find_element(By.CLASS_NAME, "status-icon")
        status_icon = status_icon_elem.text
        print(f"✓ Status icon: '{status_icon}'")
        
        print("\n[6/6] Taking screenshot for OCR verification...")
        # Use different filename for GitHub Pages test
        is_github_pages = "github.io" in url
        screenshot_path = "/tmp/selenium-github-pages.png" if is_github_pages else "/tmp/selenium-callback-test.png"
        driver.save_screenshot(screenshot_path)
        print(f"✓ Screenshot saved to {screenshot_path}")
        
        # Get page title
        print(f"\nPage title: {driver.title}")
        
        # Get console logs
        print("\n[CONSOLE LOGS]")
        try:
            logs = driver.get_log('browser')
            for log in logs[-10:]:  # Last 10 logs
                print(f"  {log['level']}: {log['message']}")
        except Exception as e:
            print(f"  Could not retrieve console logs: {e}")
        
        # Determine success
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        
        if backend_status.is_displayed():
            print("✅ Backend status indicator IS VISIBLE")
        else:
            print("❌ Backend status indicator NOT VISIBLE")
            return False
        
        if "Connected to local backend" in status_text:
            print("✅ Backend detection SUCCESS - Local backend detected")
            return True
        elif "Checking backend" in status_text:
            print("⚠️  Backend detection IN PROGRESS - Still checking")
            time.sleep(3)  # Wait for detection to complete
            status_text_elem = driver.find_element(By.CLASS_NAME, "status-text")
            status_text = status_text_elem.text
            print(f"   Updated status: '{status_text}'")
            if "Connected to local backend" in status_text:
                print("✅ Backend detection SUCCESS after wait")
                return True
        elif "Backend not available" in status_text:
            print("❌ Backend detection FAILED - No backend found")
            return False
        else:
            print(f"⚠️  Unknown status: '{status_text}'")
            return False
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if driver:
            print("\n[CLEANUP] Waiting 5 seconds before closing browser...")
            time.sleep(5)
            driver.quit()
            print("✓ Browser closed")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    success = test_frontend(url)
    sys.exit(0 if success else 1)

