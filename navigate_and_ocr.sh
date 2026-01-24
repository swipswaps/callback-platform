#!/bin/bash
# Navigate Firefox to Google Cloud Console and OCR the result

set -e

FIREFOX_WINDOW=$(xdotool search --class "firefox" | head -1)
echo "Firefox window: $FIREFOX_WINDOW"

# Click on Firefox window to ensure it's focused
xdotool windowactivate --sync $FIREFOX_WINDOW
sleep 2

# Open new tab
xdotool key --window $FIREFOX_WINDOW ctrl+t
sleep 2

# Type URL
xdotool type --window $FIREFOX_WINDOW "https://console.cloud.google.com/apis/credentials?project=gen-lang-client-0071742907"
sleep 1

# Press Enter
xdotool key --window $FIREFOX_WINDOW Return
echo "⏳ Waiting 10 seconds for page to load..."
sleep 10

# Take screenshot
scrot -u -o /tmp/gcloud_credentials.png
echo "📸 Screenshot: /tmp/gcloud_credentials.png"

# OCR
tesseract /tmp/gcloud_credentials.png stdout 2>&1 | tee /tmp/gcloud_credentials_ocr.txt

