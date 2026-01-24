#!/bin/bash
# Navigate Google Cloud Console using existing Firefox session

echo "============================================================"
echo "Finding Firefox window..."
echo "============================================================"

# Find Firefox window ID
FIREFOX_WINDOW=$(xdotool search --class "firefox" | head -1)

if [ -z "$FIREFOX_WINDOW" ]; then
    echo "❌ No Firefox window found"
    exit 1
fi

echo "✅ Found Firefox window: $FIREFOX_WINDOW"

# Focus Firefox window
xdotool windowactivate $FIREFOX_WINDOW
sleep 1

echo ""
echo "============================================================"
echo "STEP 1: Navigate to API Library"
echo "============================================================"

# Open new tab with Ctrl+T
xdotool key ctrl+t
sleep 1

# Type URL
xdotool type "https://console.cloud.google.com/apis/library?project=gen-lang-client-0071742907"
xdotool key Return
sleep 5

# Take screenshot using scrot instead of import
scrot -u -o /tmp/firefox_api_library.png
echo "📸 Screenshot: /tmp/firefox_api_library.png"

echo ""
echo "============================================================"
echo "STEP 2: Navigate to OAuth Consent Screen"
echo "============================================================"

# Select URL bar with Ctrl+L
xdotool key ctrl+l
sleep 1

# Type new URL
xdotool type "https://console.cloud.google.com/apis/credentials/consent?project=gen-lang-client-0071742907"
xdotool key Return
sleep 5

# Take screenshot using scrot
scrot -u -o /tmp/firefox_oauth_consent.png
echo "📸 Screenshot: /tmp/firefox_oauth_consent.png"

echo ""
echo "============================================================"
echo "STEP 3: Navigate to Credentials page"
echo "============================================================"

# Select URL bar
xdotool key ctrl+l
sleep 1

# Type credentials URL
xdotool type "https://console.cloud.google.com/apis/credentials?project=gen-lang-client-0071742907"
xdotool key Return
sleep 5

# Take screenshot using scrot
scrot -u -o /tmp/firefox_credentials.png
echo "📸 Screenshot: /tmp/firefox_credentials.png"

echo ""
echo "============================================================"
echo "Screenshots saved. Running OCR..."
echo "============================================================"

tesseract /tmp/firefox_api_library.png /tmp/firefox_api_library_text
tesseract /tmp/firefox_oauth_consent.png /tmp/firefox_oauth_consent_text
tesseract /tmp/firefox_credentials.png /tmp/firefox_credentials_text

echo ""
echo "✅ OCR complete. Text files:"
echo "  - /tmp/firefox_api_library_text.txt"
echo "  - /tmp/firefox_oauth_consent_text.txt"
echo "  - /tmp/firefox_credentials_text.txt"

