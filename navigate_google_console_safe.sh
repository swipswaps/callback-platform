#!/bin/bash
# Navigate Google Cloud Console with SAFE window focus verification

set -e

echo "=== Finding Firefox window ==="
FIREFOX_WINDOW=$(xdotool search --class "firefox" | head -1)

if [ -z "$FIREFOX_WINDOW" ]; then
    echo "❌ No Firefox window found"
    exit 1
fi

echo "✅ Found Firefox window: $FIREFOX_WINDOW"

# Function to verify focus
verify_focus() {
    sleep 2  # Allow window manager to process
    ACTIVE=$(xdotool getactivewindow)
    if [ "$FIREFOX_WINDOW" != "$ACTIVE" ]; then
        echo "❌ FOCUS VERIFICATION FAILED"
        echo "Expected: $FIREFOX_WINDOW"
        echo "Got: $ACTIVE"
        exit 1
    fi
    echo "✅ Focus verified"
}

# Activate Firefox
echo "=== Activating Firefox ==="
xdotool windowactivate $FIREFOX_WINDOW
verify_focus

# Navigate to Credentials page
echo "=== Navigating to Credentials page ==="
xdotool key ctrl+l
sleep 1
verify_focus

xdotool type "https://console.cloud.google.com/apis/credentials?project=gen-lang-client-0071742907"
sleep 1
verify_focus

xdotool key Return
echo "⏳ Waiting for page to load..."
sleep 8

# Take screenshot
echo "=== Taking screenshot ==="
scrot -u -o /tmp/gcloud_credentials_page.png
echo "📸 Screenshot: /tmp/gcloud_credentials_page.png"

# OCR the screenshot
echo "=== Running OCR ==="
tesseract /tmp/gcloud_credentials_page.png /tmp/gcloud_credentials_text
echo "✅ OCR complete: /tmp/gcloud_credentials_text.txt"

# Display first 50 lines
echo ""
echo "=== First 50 lines of OCR output ==="
head -50 /tmp/gcloud_credentials_text.txt

