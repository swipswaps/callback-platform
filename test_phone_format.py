#!/usr/bin/env python3
"""
Test phone number formatting with Selenium.
Tests that the form accepts (xxx) xxx-xxxx format and backend sanitizes it.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_phone_format():
    """Test phone number format (321) 704-7403 per user request."""
    
    print("=" * 60)
    print("PHONE FORMAT TEST - (xxx) xxx-xxxx")
    print("=" * 60)
    
    # Setup Firefox
    options = Options()
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1280, 1024)
    
    try:
        # Load page
        print("\n[1/5] Loading http://localhost:3000...")
        driver.get("http://localhost:3000")
        time.sleep(3)
        print("✓ Page loaded")
        
        # Wait for backend detection
        print("\n[2/5] Waiting for backend detection...")
        backend_status = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "backend-status"))
        )
        status_text = driver.find_element(By.CLASS_NAME, "status-text").text
        print(f"✓ Backend status: {status_text}")
        
        # Fill form with problematic phone format
        print("\n[3/5] Filling form with phone format: (321) 704-7403")
        name_input = driver.find_element(By.ID, "name")
        email_input = driver.find_element(By.ID, "email")
        phone_input = driver.find_element(By.ID, "phone")
        
        name_input.send_keys("Test User")
        email_input.send_keys("test@example.com")
        phone_input.send_keys("(321) 704-7403")
        print("✓ Form filled")
        
        # Take screenshot before submit
        driver.save_screenshot("/tmp/phone-test-before-submit.png")
        print("✓ Screenshot saved: /tmp/phone-test-before-submit.png")
        
        # Submit form
        print("\n[4/5] Submitting form...")
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for response
        time.sleep(3)
        
        # Check for success or error message
        print("\n[5/5] Checking response...")
        try:
            status_div = driver.find_element(By.ID, "status")
            status_text = status_div.text
            print(f"Status message: {status_text}")
            
            if "success" in status_text.lower() or "pending" in status_text.lower():
                print("✅ FORM SUBMISSION SUCCESSFUL!")
                result = True
            elif "error" in status_text.lower() or "invalid" in status_text.lower():
                print("❌ FORM SUBMISSION FAILED")
                print(f"Error: {status_text}")
                result = False
            else:
                print(f"⚠ Unknown status: {status_text}")
                result = False
        except Exception as e:
            print(f"⚠ Could not find status message: {e}")
            result = False
        
        # Take screenshot after submit
        driver.save_screenshot("/tmp/phone-test-after-submit.png")
        print("✓ Screenshot saved: /tmp/phone-test-after-submit.png")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
        return result
        
    finally:
        print("\n[CLEANUP] Closing browser...")
        time.sleep(2)
        driver.quit()
        print("✓ Browser closed")

if __name__ == "__main__":
    success = test_phone_format()
    exit(0 if success else 1)

