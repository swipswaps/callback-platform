# 📞 Callback & Click-to-Call Platform

A secure, flat-rate-friendly callback system that lets customers request a call, automatically connects them to your business, and notifies you by SMS if the call is missed.

## 🎯 What This Does (Plain English)

1. **Visitor** visits your GitHub Pages site
2. **Optional**: They sign in using Google, Facebook, Instagram, X, or WhatsApp to auto-fill their details
3. They enter their phone number and click "Request Callback"
4. **System calls your business first** (to verify you're available)
5. **If you answer**: System calls the visitor and bridges both calls together
6. **If you don't answer**: System sends you an SMS with the visitor's details so you can call them back

### Why This Matters

- **No surprise billing**: Flat-rate compatible with Twilio pay-as-you-go
- **Privacy-first**: Calls not recorded by default, minimal data collection
- **Professional**: Visitors never hear busy signals or voicemail
- **Reliable**: SMS fallback ensures no missed opportunities

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (GitHub Pages)                                     │
│  https://contact.swipswaps.com                               │
│  - HTML/CSS/JavaScript                                       │
│  - OAuth-required UX (sign in before callback)               │
│  - Backend detection (localhost → deployed)                  │
│  - Real-time status updates                                  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ HTTPS/AJAX
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Cloudflare Tunnel (cloudflared)                             │
│  https://api.swipswaps.com → localhost:8501                  │
│  - Secure tunnel without port forwarding                     │
│  - Automatic HTTPS                                           │
│  - DDoS protection                                           │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend (Docker + Flask)                                    │
│  localhost:8501                                              │
│  - OAuth provider integration (⚠️ DEMO ONLY)                 │
│  - Twilio API for calls/SMS                                  │
│  - SQLite database (persistent storage)                      │
│  - Comprehensive logging                                     │
│  - Rate limiting & security (200/day, 50/hour per IP)        │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ Twilio API
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Twilio Services                                             │
│  - Programmable Voice (calls)                                │
│  - SMS (fallback notifications)                              │
│  - Status callbacks (real-time updates)                      │
└──────────────────────────────────────────────────────────────┘
```

### Current Deployment

- **Frontend**: GitHub Pages at `https://contact.swipswaps.com`
- **Backend**: Docker container on `localhost:8501`
- **Tunnel**: Cloudflare Tunnel routes `https://api.swipswaps.com` → `localhost:8501`
- **DNS**: Cloudflare manages DNS for `swipswaps.com`

---

## 🚀 Quick Start Guide

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Twilio Account** (free trial works): https://www.twilio.com/try-twilio
- **GitHub Account** (for hosting frontend on GitHub Pages)
- **Optional**: OAuth app credentials for social login

### ⚡ The Fastest Way (Fully Automated)

**Principle**: "If it can be typed, it MUST be scripted"

```bash
# Clone the repository
git clone <your-repo-url>
cd <repo-directory>

# ONE COMMAND to build, start, and test everything:
./scripts/quick-start.sh
```

**What this does automatically**:
- ✅ Checks prerequisites (Docker, curl, jq)
- ✅ Builds Docker image (~90 seconds)
- ✅ Starts services
- ✅ Waits for backend to be ready
- ✅ Runs health check
- ✅ Executes validation tests
- ✅ Shows next steps

**Time**: 2-3 minutes total

**Output**: Color-coded with progress bars and clear status messages

---

### 🎛️ Interactive Menu (Recommended for Daily Use)

```bash
./run.sh
```

**Features**:
- Interactive menu with 13 options
- One-key selection
- Service management (start/stop/restart)
- Live monitoring dashboard
- Automated testing
- Troubleshooting tools

**Menu Options**:
```
[1] Quick Start        - Build, start, test everything
[2] Monitor Dashboard  - Real-time monitoring
[3] Run Tests          - Full test suite
[4] Troubleshoot       - Automatic diagnosis
[5] Start Services     - docker compose up -d
[6] Stop Services      - docker compose down
[7] Restart Services   - docker compose restart
[8] View Logs          - docker logs -f
[9] Rebuild Image      - docker compose build --no-cache
[10] Clean Everything  - Remove all containers/images
[11] Health Check      - Quick test
[12] Show Status       - System information
[13] Documentation     - Open guides
[0] Exit
```

---

### 📊 Live Monitoring Dashboard

```bash
./scripts/monitor-dashboard.sh
```

**Features**:
- Real-time updates every 2 seconds
- Service status (health, container, uptime)
- Resource usage (CPU, memory)
- Request metrics (total requests, errors)
- Recent logs (last 5 lines, color-coded)
- Interactive controls (R=restart, L=logs, T=tests, Q=quit)

---

### 🔍 Automatic Troubleshooting

```bash
./scripts/troubleshoot.sh
```

**Performs 9 automated checks**:
1. Docker daemon status
2. Container status
3. Port availability
4. Health endpoint
5. Recent logs
6. Error detection
7. Environment config
8. Disk space
9. Summary with actionable fixes

**Output**: Full transparency with suggested fixes for each issue

---

### 📖 Manual Setup (Traditional Method)

If you prefer manual control:

### Step 1: Clone and Configure

```bash
# Clone the repository
git clone <your-repo-url>
cd <repo-directory>

# Copy environment template
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use your preferred editor
```

### Step 2: Configure Twilio

1. **Sign up** at https://www.twilio.com/try-twilio
2. **Get your credentials** from the Twilio Console:
   - Account SID
   - Auth Token
   - Phone Number (buy one or use trial number)
3. **Update `.env` file**:
   ```env
   TWILIO_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_NUMBER=+15551234567
   BUSINESS_NUMBER=+15557654321  # YOUR phone number
   ```

### Step 3: Start the Backend

```bash
# Build and start the Docker container
docker-compose up --build

# You should see:
# ✓ Database initialized
# ✓ Twilio client initialized
# ✓ Server running on 0.0.0.0:8501
```

### Step 4: Test Locally

```bash
# In a new terminal, test the health endpoint
curl http://localhost:8501/health

# Expected response:
# {"status":"healthy","timestamp":"2024-01-19T...","twilio_configured":true}
```

### Step 5: Deploy Frontend to GitHub Pages

```bash
# 1. Create a new GitHub repository
# 2. Push your code
git add .
git commit -m "Initial commit"
git push origin main

# 3. Enable GitHub Pages with GitHub Actions
# Go to: Settings → Pages → Source: GitHub Actions
# The workflow in .github/workflows/deploy.yml will automatically deploy

# 4. (Optional) Set up custom domain
# Go to: Settings → Pages → Custom domain
# Enter: contact.yourdomain.com
# Add CNAME file to frontend/:
echo "contact.yourdomain.com" > frontend/CNAME
git add frontend/CNAME
git commit -m "Add custom domain"
git push
```

### Step 6: Set Up Cloudflare Tunnel (Recommended)

Cloudflare Tunnel provides secure access to your backend without port forwarding:

```bash
# 1. Install cloudflared
# Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

# 2. Authenticate
cloudflared tunnel login

# 3. Create tunnel
cloudflared tunnel create callback-platform

# 4. Create config file at ~/.cloudflared/config.yml
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: <YOUR_TUNNEL_ID>
credentials-file: /home/owner/.cloudflared/<YOUR_TUNNEL_ID>.json

ingress:
  - hostname: api.yourdomain.com
    service: http://localhost:8501
  - service: http_status:404
EOF

# 5. Create DNS record
cloudflared tunnel route dns callback-platform api.yourdomain.com

# 6. Run tunnel
cloudflared tunnel run callback-platform
```

**Alternative**: Use ngrok for testing:
```bash
ngrok http 8501
# Update FRONTEND_URL in .env to ngrok URL
```

### Step 7: Update Backend Configuration

Edit `.env` file:

```env
# Set frontend URL (for OAuth redirects)
FRONTEND_URL=https://contact.yourdomain.com

# Backend will be accessible at:
# - Locally: http://localhost:8501
# - Via tunnel: https://api.yourdomain.com
```

**Frontend will automatically detect backend:**
1. Tries `http://localhost:8501` first (3-second timeout)
2. Falls back to `https://api.yourdomain.com` (4-second timeout)
3. Shows backend status indicator

---

## 📖 Detailed User Guide

### For Admin Users

The admin dashboard provides comprehensive management and monitoring of all callback requests.

**Access**: `https://contact.yourdomain.com/admin/dashboard.html`

#### Getting Started

1. **Login with API Token**:
   - Enter your API token (configured in backend `.env` as `ADMIN_API_TOKEN`)
   - Token is stored in browser session for convenience
   - Auto-login when pasting token (20+ characters)

2. **Dashboard Overview**:
   - Real-time statistics (total requests, success rate, 24h activity)
   - Clickable stat cards to filter by status
   - Live updates without page refresh
   - Version detection (shows when newer build exists on GitHub)

#### Key Features

**📊 Statistics Cards** (Clickable):
- **Total Requests**: Click to show all requests
- **Success Rate**: Shows % of successful callbacks (informational)
- **Last 24h**: Recent activity count (informational)
- **⏳ Pending**: Click to show pending requests (TAKE ACTION)
- **✅ Completed**: Click to show successful callbacks
- **❌ Failed**: Click to show failed requests (NEEDS RETRY)

**🔍 Filtering**:
- Filter by status (pending, verified, calling, connected, completed, failed, cancelled)
- Search by phone number
- Limit results (10, 25, 50, 100, 500 per page)
- Clear all filters with one click or press `Escape`

**📋 Request Management**:
- **View Details**: Click any request ID or phone number to see full details
- **Copy to Clipboard**: Click request ID or phone number to copy
- **Retry Failed Requests**: One-click retry for failed callbacks
- **Cancel Pending Requests**: Cancel requests that haven't been processed yet
- **Live Updates**: Actions update data without page refresh

**☑️ Bulk Actions**:
- Select multiple requests using checkboxes
- **Select All**: Checkbox in table header
- **Bulk Retry**: Retry multiple failed requests at once
- **Bulk Cancel**: Cancel multiple pending requests at once
- Progress feedback via toast notifications

**📊 Export to CSV**:
- Export filtered requests to CSV file
- Fetches up to 10,000 matching records
- Proper CSV escaping (commas, quotes, newlines)
- Filename includes timestamp and filter suffix
- Example: `callback_requests_failed_2024-01-27.csv`

**⌨️ Keyboard Shortcuts**:
- `Ctrl/Cmd + R`: Refresh dashboard
- `Ctrl/Cmd + K`: Focus search filter
- `Escape`: Clear all filters
- `?`: Show keyboard shortcuts help

**🔔 Toast Notifications**:
- Non-blocking, auto-dismiss notifications
- Color-coded: success (green), error (red), info (blue)
- Smooth slide-in animation
- No more blocking alert() dialogs

**🔄 Version Detection**:
- Automatic check on page load (no polling)
- Shows banner if newer build exists on GitHub
- Informational only (no claims about CDN propagation)
- Refresh or dismiss banner

#### Common Admin Tasks

**Monitor Pending Requests**:
1. Click "⏳ Pending" stat card
2. Review requests waiting for action
3. Cancel if needed or wait for automatic processing

**Retry Failed Callbacks**:
1. Click "❌ Failed" stat card
2. Review failure reasons in status message
3. Click "🔄 Retry" button for individual requests
4. Or select multiple and use "Bulk Retry"

**Export Data for Analysis**:
1. Apply filters (e.g., status=completed, last 24h)
2. Click "📊 Export CSV" button
3. Open in Excel/Google Sheets for analysis

**Search for Specific Customer**:
1. Enter phone number in search filter
2. Click "Apply Filters"
3. View all requests from that customer

**Bulk Operations**:
1. Select requests using checkboxes
2. Bulk actions bar appears automatically
3. Choose "Bulk Retry" or "Bulk Cancel"
4. Confirm action
5. Watch progress via toast notifications

#### Security Notes

- API token required for all operations
- Token transmitted via `Authorization: Bearer` header
- Session expires when browser closes
- No sensitive data stored in localStorage
- All actions logged in backend audit log

### For Business Owners

#### How to Receive Callbacks

1. **Keep your phone nearby** - The system calls YOU first
2. **Answer when you see your Twilio number** calling
3. **Wait 2-3 seconds** - System is connecting the visitor
4. **Start talking** - You're now connected to the visitor

#### If You Miss a Call

- You'll receive an **SMS** with visitor details
- **Call them back** using the number in the SMS
- The system logs all requests in the database

#### Viewing Callback History

```bash
# Access the SQLite database
docker exec -it callback-backend sqlite3 /app/data/callbacks.db

# View all callbacks
SELECT * FROM callbacks ORDER BY created_at DESC LIMIT 10;

# View audit log
SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 20;

# Exit
.quit
```

### For Visitors (Your Customers)

**⚠️ IMPORTANT: OAuth Sign-In Required**

To prevent abuse and ensure quality service, visitors must sign in before requesting a callback.

1. **Visit the callback page** (e.g., `https://contact.swipswaps.com`)
2. **Sign in** using one of the OAuth providers:
   - Google
   - Facebook
   - Instagram
   - X (Twitter)
3. **After sign-in**: Form appears with auto-filled details
4. **Enter your phone number** (required)
5. **Click "Request Callback Now"**
6. **Enter the 6-digit verification code** sent to your phone
   - **Auto-verify**: Code is automatically verified when you finish typing the 6th digit
   - No need to click "Verify" button - just type the code!
   - If you make a mistake, you can still click "Verify" manually or retype the code
7. **Answer your phone** when it rings (usually within 10-20 seconds)
8. **You'll be connected** to the business automatically

**Privacy**: Your OAuth data is only used to auto-fill the form. We never share your information.

#### Auto-Verify Feature

The platform includes an intelligent auto-verify feature that improves user experience:

- **Automatic verification**: When you type the 6th digit of your verification code, the system automatically verifies it without requiring you to click the "Verify" button
- **Race condition protection**: Built-in safeguards prevent duplicate verification attempts, ensuring smooth operation
- **Fallback options**: You can still use the "Verify" button or press Enter if you prefer manual verification
- **Error prevention**: The system prevents multiple simultaneous verification attempts that could cause confusion

**Technical Details** (for administrators):
- Uses `keyup` event listener for reliable cross-browser compatibility
- Implements `isVerifying` flag to prevent race conditions
- Comprehensive debug logging for troubleshooting (visible in browser console)
- Graceful error handling with user-friendly messages

---

## �️ Security Features

This platform includes **6 layers of security** to protect against abuse and fraud:

### 1. CORS Restriction
- Configured via `ALLOWED_ORIGINS` environment variable
- Prevents unauthorized domains from accessing the API
- Default: Restricts to your frontend domain only

### 2. Rate Limiting
- **5 requests per minute** per IP address
- **50 requests per hour** per IP address
- **200 requests per day** per IP address
- Prevents spam and DoS attacks

### 3. Phone Number Validation
- E.164 format validation using `phonenumbers` library
- Rejects invalid or malformed phone numbers
- Prevents toll fraud and abuse

### 4. Twilio Webhook Signature Verification
- Validates all Twilio callbacks using HMAC-SHA1
- Prevents spoofed webhook attacks
- Returns 403 Forbidden for invalid signatures

### 5. Google reCAPTCHA v2
- Prevents bot abuse and automated attacks
- Required for all callback requests
- Configurable via `RECAPTCHA_SECRET_KEY` and `RECAPTCHA_SITE_KEY`

### 6. Business Hours Check
- Timezone-aware time checking
- Configurable business hours (default: 9 AM - 5 PM)
- Weekend detection (optional)
- Sends SMS instead of calling outside business hours
- Prevents annoying 2 AM calls to your business

**Configuration** (`.env` file):
```env
# Business Hours
BUSINESS_HOURS_START=09:00
BUSINESS_HOURS_END=17:00
BUSINESS_TIMEZONE=America/New_York
BUSINESS_WEEKDAYS_ONLY=true

# reCAPTCHA
RECAPTCHA_SECRET_KEY=your_secret_key_here
RECAPTCHA_SITE_KEY=your_site_key_here
```

**Get reCAPTCHA keys**: https://www.google.com/recaptcha/admin

---

## 🎨 Automation Features

This platform follows the principle: **"If it can be typed, it MUST be scripted"**

### Available Automation Scripts

**1. Master Control** - `./run.sh`
- Interactive menu system
- 13 one-key operations
- Zero complexity, full automation

**2. Quick Start** - `./scripts/quick-start.sh`
- One-command setup
- Automatic prerequisite checking
- Build, start, test in 2-3 minutes

**3. Test Runner** - `./scripts/test-runner.sh`
- Automated testing (Levels 3-5)
- Color-coded output
- Automatic log saving to `/tmp/callback-tests/`

**4. Live Monitor** - `./scripts/monitor-dashboard.sh`
- Real-time dashboard
- Updates every 2 seconds
- Interactive controls

**5. Troubleshooter** - `./scripts/troubleshoot.sh`
- 9 automated diagnostic checks
- Error detection with explanations
- Actionable fixes

### UX Features

**Color Coding**:
- 🔵 Blue - Information
- ✅ Green - Success
- ⚠️ Yellow - Warnings
- ❌ Red - Errors
- 🔷 Cyan - Section headers
- 🔶 Magenta - Step headers

**Progress Indicators**:
```
[████████████████████████████████████████████████] 100% - Waiting for service...
```

**Automatic Log Saving**:
- All operations save logs to `/tmp/callback-tests/`
- Persistent for troubleshooting
- Timestamped filenames

**Full Transparency**:
- All terminal output visible
- No hidden operations
- Clear error messages with fixes

**See `AUTOMATION_GUIDE.md` for complete documentation**

---

## 🔐 OAuth Setup (REQUIRED)

### ⚠️ CRITICAL: OAuth Implementation Status

**Current Status**: ⚠️ **DEMO ONLY - NOT PRODUCTION READY**

The OAuth implementation in this repository uses **demo tokens** and does NOT perform actual OAuth authentication.

**Current behavior**:
- OAuth buttons redirect to backend `/oauth/login/<provider>`
- Backend returns `demo_token_{provider}` instead of real OAuth flow
- Frontend receives fake user data
- **This violates security best practices and MUST be replaced before production use**

### Why OAuth is Required

The frontend enforces OAuth sign-in before allowing callback requests. This:
- ✅ Prevents spam and abuse
- ✅ Reduces callback costs (no anonymous requests)
- ✅ Provides user accountability
- ✅ Auto-fills user details for better UX

**You MUST implement real OAuth before deploying to production.**

### Implementing Real OAuth (Required Steps)

**To use OAuth in production, you must**:
1. Register apps with each provider (Google Cloud Console, Meta Developers, Twitter Developer Portal)
2. Replace demo endpoints in `backend/app.py` with proper authorization code flow
3. Add OAuth credentials (Client ID, Client Secret) to `.env`
4. Implement state parameter for CSRF protection
5. Configure redirect URIs: `https://api.yourdomain.com/oauth/callback/{provider}`
6. Test thoroughly before deployment

**Alternative (NOT RECOMMENDED)**: Remove OAuth requirement and add reCAPTCHA v3 for spam protection.

---

### OAuth Provider Setup Guide

Social login makes it easier for visitors to request callbacks. Here's how to set up each provider:

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Add authorized redirect URI: `http://localhost:8501/oauth/callback/google`
6. Copy **Client ID** and **Client Secret**
7. Update `backend/oauth_providers.py` with your credentials

### Facebook/Instagram OAuth

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app
3. Add **Facebook Login** product
4. Configure OAuth redirect URI: `http://localhost:8501/oauth/callback/facebook`
5. For Instagram: Add **Instagram Basic Display** product
6. Copy **App ID** and **App Secret**

### X.com (Twitter) OAuth

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app
3. Enable **OAuth 2.0**
4. Add callback URL: `http://localhost:8501/oauth/callback/x`
5. Copy **Client ID** and **Client Secret**

### WhatsApp Business API

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Set up **WhatsApp Business API** (requires business verification)
3. This is the most complex setup - consider skipping unless you need it

**Note**: OAuth is optional. Visitors can always manually enter their details.

---

## 🛠️ Troubleshooting Guide

This section addresses **every common pain point** to save you hours of debugging.

### Problem: "Twilio client not initialized"

**Symptoms**:
- Backend logs show: `Twilio credentials not configured`
- Callbacks don't work

**Solutions**:
1. Check your `.env` file exists and has correct values
2. Verify environment variables are loaded:
   ```bash
   docker-compose config  # Shows resolved configuration
   ```
3. Check for typos in variable names (case-sensitive!)
4. Restart the container after changing `.env`:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

### Problem: "Network error contacting callback service"

**Symptoms**:
- Frontend shows: "Network error. Please check your connection"
- Browser console shows CORS errors or connection refused

**Solutions**:
1. **Check backend is running**:
   ```bash
   docker ps  # Should show callback-backend container
   curl http://localhost:8501/health  # Should return JSON
   ```

2. **CORS issues** (if frontend is on different domain):
   - Update `backend/app.py` CORS configuration:
   ```python
   CORS(app, resources={r"/*": {"origins": ["https://yourusername.github.io"]}})
   ```

3. **Frontend URL mismatch**:
   - Check `frontend/app.js` has correct `BACKEND_URL`
   - For local testing: `http://localhost:8501`
   - For production: Your deployed backend URL

### Problem: "Callback request submitted but no call received"

**Symptoms**:
- Frontend shows success message
- No phone call received
- No SMS received

**Solutions**:
1. **Check Twilio account status**:
   - Trial accounts can only call **verified numbers**
   - Go to Twilio Console → Phone Numbers → Verified Caller IDs
   - Add your phone number if using trial account

2. **Check phone number format**:
   - Must include country code: `+1` for US/Canada
   - Example: `+15551234567` (not `555-123-4567`)
   - Update `BUSINESS_NUMBER` in `.env` with correct format

3. **Check Twilio balance**:
   - Trial accounts have limited credits
   - Upgrade to paid account if credits exhausted

4. **Review logs**:
   ```bash
   # Check backend logs
   docker logs callback-backend

   # Check for Twilio errors
   docker logs callback-backend | grep -i "twilio"

   # Check application logs
   docker exec callback-backend cat /tmp/app.log
   ```

5. **Verify Twilio webhook configuration**:
   - Your backend must be publicly accessible for status callbacks
   - Use ngrok for local testing:
   ```bash
   ngrok http 8501
   # Update FRONTEND_URL in .env to ngrok URL
   ```

### Problem: "OAuth redirect fails" or "oauth_failed error"

**Symptoms**:
- After clicking social login, redirected back with error
- URL shows `?error=oauth_failed`

**Solutions**:
1. **Redirect URI mismatch**:
   - OAuth provider redirect URI must **exactly match** your backend URL
   - Check provider dashboard settings
   - Common mistake: `http://` vs `https://` or trailing slash

2. **OAuth app not approved**:
   - Some providers require app review before public use
   - Use test users during development

3. **Token exchange failed**:
   - Check backend logs for API errors
   - Verify OAuth credentials are correct
   - Check API rate limits

4. **For demo/testing without OAuth**:
   - Just skip social login and manually enter details
   - OAuth is optional, not required

### Problem: "Database locked" or SQLite errors

**Symptoms**:
- Backend logs show: `database is locked`
- Callbacks fail to save

**Solutions**:
1. **Multiple processes accessing database**:
   - Ensure only one backend instance is running
   - Check for zombie processes:
   ```bash
   docker ps -a  # Look for multiple callback-backend containers
   docker-compose down  # Stop all
   docker-compose up  # Start fresh
   ```

2. **Permissions issue**:
   ```bash
   # Fix permissions on data volume
   docker-compose down
   docker volume rm callback-data
   docker-compose up --build
   ```

3. **Database corruption**:
   ```bash
   # Backup and recreate database
   docker exec callback-backend cp /app/data/callbacks.db /app/data/callbacks.db.backup
   docker exec callback-backend rm /app/data/callbacks.db
   docker-compose restart backend
   ```

### Problem: "Port 8501 already in use"

**Symptoms**:
- Docker fails to start: `bind: address already in use`

**Solutions**:
1. **Find what's using the port**:
   ```bash
   # Linux/Mac
   lsof -i :8501

   # Windows
   netstat -ano | findstr :8501
   ```

2. **Kill the process** or **change the port**:
   ```yaml
   # In docker-compose.yml, change:
   ports:
     - "8502:8501"  # Use 8502 on host instead
   ```

3. **Stop conflicting service**:
   ```bash
   # If it's another Docker container
   docker ps
   docker stop <container-id>
   ```

### Problem: "SMS not received by business"

**Symptoms**:
- Call fails but no SMS notification
- Logs show SMS sent but nothing received

**Solutions**:
1. **Check SMS-capable number**:
   - Not all Twilio numbers support SMS
   - Verify in Twilio Console → Phone Numbers → Capabilities
   - Buy an SMS-capable number if needed

2. **Check carrier filtering**:
   - Some carriers block automated SMS
   - Try from a different phone number
   - Add your number to Twilio's verified list

3. **Check message content**:
   - Some carriers block messages with URLs or certain keywords
   - Review `backend/app.py` SMS message template

### Problem: "Frontend shows old data after OAuth"

**Symptoms**:
- Social login completes but form not auto-filled
- URL has `?user=...` but fields are empty

**Solutions**:
1. **Check browser console** for JavaScript errors
2. **Clear browser cache** and try again
3. **Verify base64 encoding**:
   ```javascript
   // In browser console:
   const params = new URLSearchParams(window.location.search);
   console.log(atob(params.get("user")));  // Should show user data
   ```

### Problem: "Docker build fails"

**Symptoms**:
- `docker-compose up --build` shows errors
- Dependencies fail to install

**Solutions**:
1. **Network issues**:
   ```bash
   # Test internet connectivity
   docker run --rm python:3.11-slim ping -c 3 google.com
   ```

2. **Disk space**:
   ```bash
   df -h  # Check available space
   docker system prune -a  # Clean up old images
   ```

3. **Corrupted cache**:
   ```bash
   docker-compose build --no-cache
   ```

### Problem: "Calls connect but no audio"

**Symptoms**:
- Both parties answer but can't hear each other
- One-way audio (only one person can hear)

**Solutions**:
1. **Firewall blocking RTP**:
   - Twilio uses UDP ports 10000-20000 for audio
   - Check firewall rules on both ends

2. **NAT traversal issues**:
   - Common with VPNs or corporate networks
   - Try from different network

3. **TwiML configuration**:
   - Check the TwiML URL in `backend/app.py`
   - Verify it returns valid TwiML XML

---

## 🔒 Security Best Practices

### For Production Deployment

1. **Use HTTPS everywhere**:
   - Frontend: GitHub Pages provides HTTPS automatically
   - Backend: Use reverse proxy (nginx) with Let's Encrypt SSL

2. **Restrict CORS**:
   ```python
   # In backend/app.py
   CORS(app, resources={r"/*": {"origins": ["https://yourdomain.com"]}})
   ```

3. **Add rate limiting**:
   ```bash
   pip install flask-limiter
   ```
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=lambda: request.remote_addr)

   @app.route("/request_callback", methods=["POST"])
   @limiter.limit("5 per minute")  # Max 5 requests per minute
   def request_callback():
       # ...
   ```

4. **Add CAPTCHA** (prevent abuse):
   - Use Google reCAPTCHA v3
   - Add to frontend form
   - Verify token in backend

5. **Secure environment variables**:
   - Never commit `.env` to git
   - Use secrets management in production (AWS Secrets Manager, etc.)

6. **Enable Twilio geographic permissions**:
   - Restrict calls to specific countries
   - Prevent international toll fraud

7. **Monitor usage**:
   - Set up Twilio usage alerts
   - Monitor logs for suspicious patterns

8. **Database backups**:
   ```bash
   # Automated backup script
   docker exec callback-backend sqlite3 /app/data/callbacks.db ".backup /app/data/backup-$(date +%Y%m%d).db"
   ```

---

## 📊 Monitoring and Logs

### View Real-Time Logs

```bash
# Follow backend logs
docker logs -f callback-backend

# View last 100 lines
docker logs --tail 100 callback-backend

# Search for errors
docker logs callback-backend | grep -i error
```

### Access Application Logs

```bash
# Application log (comprehensive per Rule 25)
docker exec callback-backend cat /tmp/app.log

# OAuth provider log
docker exec callback-backend cat /tmp/oauth_providers.log

# Follow logs in real-time
docker exec callback-backend tail -f /tmp/app.log
```

### Database Queries

```bash
# Interactive SQLite session
docker exec -it callback-backend sqlite3 /app/data/callbacks.db

# Quick queries
docker exec callback-backend sqlite3 /app/data/callbacks.db "SELECT COUNT(*) FROM callbacks;"
docker exec callback-backend sqlite3 /app/data/callbacks.db "SELECT * FROM callbacks WHERE request_status='failed';"
```

---

## 🚀 Production Deployment Checklist

- [ ] Twilio account upgraded from trial (if needed)
- [ ] All phone numbers verified
- [ ] `.env` file configured with production values
- [ ] Backend deployed to cloud (AWS, GCP, Heroku, etc.)
- [ ] Backend URL is HTTPS
- [ ] Frontend deployed to GitHub Pages
- [ ] Frontend `BACKEND_URL` updated to production URL
- [ ] CORS configured for production domain
- [ ] Rate limiting enabled
- [ ] CAPTCHA added (if public-facing)
- [ ] Database backups configured
- [ ] Monitoring/alerting set up
- [ ] Twilio usage alerts configured
- [ ] OAuth apps approved (if using social login)
- [ ] Privacy policy added to frontend
- [ ] Terms of service added (if required)

---

## 💰 Cost Estimation

### Twilio Costs (Pay-as-you-go)

- **Voice calls**: ~$0.013/minute (US)
- **SMS**: ~$0.0075/message (US)
- **Phone number**: ~$1.15/month

### Example Monthly Cost

**Scenario**: 100 callbacks/month, 50% answer rate, 3-minute average call

- 100 calls to business × $0.013/min × 0.5 min (ring time) = **$0.65**
- 50 successful calls × $0.013/min × 3 min = **$1.95**
- 50 successful calls to visitor × $0.013/min × 3 min = **$1.95**
- 50 SMS fallbacks × $0.0075 = **$0.38**
- Phone number = **$1.15**

**Total**: ~$6.08/month for 100 callbacks

### Flat-Rate Alternative

For predictable costs, consider:
- Twilio Elastic SIP Trunking (flat monthly rate)
- Or use this system with your existing VoIP provider

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

MIT License - feel free to use for commercial or personal projects.

---

## 🆘 Support

### Getting Help

1. **Check this README** - especially the Troubleshooting section
2. **Review logs** - most issues show up in logs
3. **Check Twilio Console** - for call/SMS status
4. **Open an issue** - on GitHub with logs and error messages

### Common Questions

**Q: Can I use this without Twilio?**
A: The code is designed for Twilio, but you can adapt it for other providers (Vonage, Plivo, etc.) by modifying `backend/app.py`.

**Q: Does this work internationally?**
A: Yes, but costs vary by country. Check Twilio pricing for your region.

**Q: Can I customize the frontend design?**
A: Absolutely! Edit `frontend/styles.css` to match your brand.

**Q: Is this GDPR compliant?**
A: The system collects minimal data and includes privacy notices. You'll need to add a full privacy policy for GDPR compliance.

**Q: Can I record calls?**
A: Yes, but you must notify callers and get consent. Update the TwiML to include recording parameters.

---

## 🎉 Success Indicators

You'll know everything is working when:

✅ Backend health check returns `{"status":"healthy","twilio_configured":true}`
✅ Frontend loads without console errors
✅ Social login redirects work (or manual entry works)
✅ Submitting a callback shows "Callback request received"
✅ Your phone rings within 10-20 seconds
✅ After you answer, visitor's phone rings
✅ Both parties can hear each other clearly
✅ If you don't answer, you receive an SMS with visitor details
✅ Database shows the callback record

---

**Built with ❤️ for businesses that value customer connections**

