# Automation Guide - "If it can be typed, it MUST be scripted"

**Date**: 2024-01-19
**Principle**: Zero manual typing, full automation, cutting-edge UX
**Status**: ✅ Complete automation suite ready

---

## 🎯 Philosophy

This platform follows the principle: **"If it can be typed, it MUST be scripted"**

**Benefits**:
- ✅ **Zero complexity** - Single commands for everything
- ✅ **Full transparency** - All logs visible, color-coded output
- ✅ **No rabbit holes** - Direct, focused solutions
- ✅ **Cutting-edge UX** - Progress bars, live monitoring, instant feedback
- ✅ **Troubleshooting built-in** - Automatic diagnosis and fixes

---

## 🚀 Quick Start (One Command)

### The Simplest Way

```bash
./run.sh
```

This opens an **interactive menu** with all options. Just type a number and press Enter.

### The Fastest Way

```bash
./scripts/quick-start.sh
```

This **automatically**:
1. ✅ Checks prerequisites (Docker, curl, jq)
2. ✅ Builds Docker image (~90 seconds)
3. ✅ Starts services
4. ✅ Waits for backend to be ready
5. ✅ Runs health check
6. ✅ Runs quick validation tests
7. ✅ Shows next steps

**Output**: Color-coded, progress bars, clear status messages

---

## 📊 Available Scripts

### 1. Master Control (`run.sh`)

**Purpose**: Interactive menu for all operations

**Usage**:
```bash
./run.sh
```

**Features**:
- Interactive menu with 13 options
- Color-coded categories (Quick Actions, Service Management, Development, Information)
- One-key selection
- Automatic script execution
- Returns to menu after each action

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

### 2. Quick Start (`scripts/quick-start.sh`)

**Purpose**: Zero-configuration startup

**Usage**:
```bash
./scripts/quick-start.sh
```

**What it does**:
```
STEP 1: Checking Prerequisites
  ✅ Docker installed: Docker version 29.1.5
  ✅ Docker Compose installed
  ✅ curl installed
  ⚠ jq not found (optional)

STEP 2: Building Docker Image
  ℹ Building backend image (this may take 1-2 minutes)...
  ✅ Docker image built successfully

STEP 3: Starting Services
  ℹ Starting Docker Compose services...
  ℹ Waiting for backend to be ready...
  ✅ Backend is ready!

STEP 4: Running Health Check
  ℹ Testing health endpoint...
  {
    "status": "healthy",
    "timestamp": "2024-01-19T..."
  }
  ✅ Health check PASSED

STEP 5: Running Quick Tests
  ℹ Test 1: Invalid phone number (should reject)
  ✅ Phone validation working ✓
  ℹ Test 2: Missing CAPTCHA (should reject)
  ✅ CAPTCHA validation working ✓

STEP 6: Next Steps
  🎉 Platform is running!
  
  Access Points:
    • Backend API:  http://localhost:8501
    • Health Check: http://localhost:8501/health
    • Frontend:     Open frontend/index.html in browser
```

**Time**: ~2-3 minutes total

---

### 3. Test Runner (`scripts/test-runner.sh`)

**Purpose**: Automated testing suite (Levels 3-5)

**Usage**:
```bash
./scripts/test-runner.sh
```

**Tests Executed**:

**Level 3: Service Startup**
- Starts Docker Compose
- Waits for service (max 30s with progress bar)
- Tests health endpoint
- Checks initialization logs
- Saves logs to `/tmp/callback-tests/level3_*.log`

**Level 4: CAPTCHA Integration**
- Test 1: Missing CAPTCHA token → 400 error
- Test 2: Invalid CAPTCHA token → 400 error
- Verifies error messages contain "CAPTCHA"
- Checks logs for CAPTCHA failures
- Saves logs to `/tmp/callback-tests/level4_*.log`

**Level 5: Phone Validation**
- Test 1: Invalid phone number → 400 error
- Verifies error message contains "phone"
- Checks logs for validation messages
- Saves logs to `/tmp/callback-tests/level5_*.log`

**Output**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEVEL 3: SERVICE STARTUP TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ Starting Docker Compose services...
ℹ Waiting for service at http://localhost:8501/health (max 30s)...
[████████████████████████████████████████████████] 100% - Waiting for service...
✅ Service is ready!
✅ Health check PASSED
✅ Level 3 COMPLETE - Logs: /tmp/callback-tests/level3_success_20240119_123456.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEVEL 4: CAPTCHA INTEGRATION TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ Test 1: Missing CAPTCHA token (should fail with 400)
Response: {"success":false,"error":"CAPTCHA verification failed"}
Status: 400
✅ Missing CAPTCHA test PASSED
...
```

**Time**: ~1-2 minutes

---

### 4. Monitor Dashboard (`scripts/monitor-dashboard.sh`)

**Purpose**: Real-time monitoring with live updates

**Usage**:
```bash
./scripts/monitor-dashboard.sh
```

**Features**:
- **Live updates** every 2 seconds
- **Color-coded status** (green=good, red=error, yellow=warning)
- **Resource metrics** (CPU, memory)
- **Request counters** (total requests, errors)
- **Recent logs** (last 5 lines, color-coded)
- **Interactive controls** (R=restart, L=logs, T=tests, Q=quit)

**Display**:
```
╔═══════════════════════════════════════════════════════════════════════╗
║  🚀 CALLBACK PLATFORM - LIVE MONITORING DASHBOARD                    ║
║  Updated: 2024-01-19 12:34:56                                        ║
╚═══════════════════════════════════════════════════════════════════════╝

SERVICE STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ● Health Status:    HEALTHY
  ● Container:        RUNNING
  ● Uptime:           5 minutes

RESOURCE USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ● CPU:              2.5%
  ● Memory:           45.2MiB / 7.8GiB

REQUEST METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ● Total Requests:   12
  ● Errors:           0

RECENT LOGS (Last 5 lines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INFO | Health check requested
  INFO | Phone number validated: +15551234567
  WARNING | reCAPTCHA verification failed
  INFO | Request callback initiated
  INFO | Database updated

QUICK ACTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [R] Restart   [L] Full Logs   [T] Run Tests   [Q] Quit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Press Ctrl+C to exit
```

---

### 5. Troubleshooter (`scripts/troubleshoot.sh`)

**Purpose**: Automatic diagnosis with actionable fixes

**Usage**:
```bash
./scripts/troubleshoot.sh
```

**Checks Performed**:

1. **Docker Status** - Is Docker daemon running?
2. **Container Status** - Is backend container running?
3. **Port Availability** - Is port 8501 in use?
4. **Health Endpoint** - Is backend responding?
5. **Recent Logs** - Last 30 lines
6. **Error Detection** - Scans for errors/exceptions
7. **Environment Config** - Is .env configured?
8. **Disk Space** - Sufficient space available?

**Output**:
```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   🔍 TROUBLESHOOTING ASSISTANT                                       ║
║                                                                       ║
║   Automatic diagnosis with full transparency                         ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. DOCKER STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Docker daemon is running
Docker version 29.1.5, build 0e6fee6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. CONTAINER STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Backend container is running
callback-backend   Up 5 minutes   0.0.0.0:8501->8501/tcp

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. ERROR DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ No obvious errors found in logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. SUMMARY & RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quick Fixes:
  1. Restart everything:     docker compose restart
  2. Rebuild from scratch:   docker compose down && docker compose build --no-cache && docker compose up -d
  3. View live logs:         docker logs -f callback-backend
  4. Check all tests:        ./scripts/test-runner.sh
```

**Time**: ~5-10 seconds

---

## 🎨 UX Features

### Color Coding

- 🔵 **Blue** - Informational messages
- ✅ **Green** - Success messages
- ⚠️ **Yellow** - Warnings
- ❌ **Red** - Errors
- 🔷 **Cyan** - Section headers
- 🔶 **Magenta** - Step headers

### Progress Indicators

```
[████████████████████████████████████████████████] 100% - Waiting for service...
```

### Status Symbols

- `●` - Status indicator (colored)
- `✅` - Success
- `❌` - Failure
- `⚠` - Warning
- `ℹ` - Information
- `•` - List item

### Log Formatting

- Timestamps preserved
- Color-coded by severity (ERROR=red, WARNING=yellow, INFO=blue)
- Truncated to fit screen (70 chars)
- Saved to files for full details

---

## 📁 Log Files

All logs automatically saved to: `/tmp/callback-tests/`

**File naming**:
- `level3_success_20240119_123456.log` - Successful test
- `level4_captcha_missing_failed_20240119_123456.log` - Failed test
- `docker-compose-up.log` - Docker Compose output

**Retention**: Logs persist until `/tmp` is cleared (usually on reboot)

---

## 🔧 Common Workflows

### First Time Setup
```bash
./scripts/quick-start.sh
```

### Daily Development
```bash
./run.sh
# Select [2] Monitor Dashboard
```

### After Code Changes
```bash
./run.sh
# Select [7] Restart Services
# Select [3] Run Tests
```

### Debugging Issues
```bash
./scripts/troubleshoot.sh
```

### Production Deployment
```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with production keys

# 2. Test locally
./scripts/test-runner.sh

# 3. Deploy
docker compose up -d
```

---

## 🚨 Troubleshooting

### Script Permission Denied

**Problem**: `bash: ./run.sh: Permission denied`

**Fix**:
```bash
chmod +x run.sh scripts/*.sh
```

### Docker Not Running

**Problem**: `Cannot connect to the Docker daemon`

**Fix**:
```bash
# Start Docker Desktop (GUI)
# OR
sudo systemctl start docker
```

### Port Already in Use

**Problem**: `Port 8501 is already allocated`

**Fix**:
```bash
# Find process using port
lsof -i :8501
# Kill it or change port in docker-compose.yml
```

---

## 📊 Comparison: Before vs After

### Before (Manual)
```bash
# User types 15+ commands:
docker compose build
docker compose up -d
sleep 10
curl http://localhost:8501/health
curl -X POST http://localhost:8501/request_callback -H "Content-Type: application/json" -d '{"visitor_number":"invalid","name":"Test"}'
# ... check response manually
# ... check logs manually
docker logs callback-backend | grep error
# ... etc
```

### After (Automated)
```bash
# User types 1 command:
./scripts/quick-start.sh

# Everything happens automatically with:
# - Progress bars
# - Color-coded output
# - Automatic validation
# - Clear success/failure messages
# - Saved logs
# - Next steps guidance
```

---

## 🎯 Summary

**Principle Achieved**: ✅ "If it can be typed, it MUST be scripted"

**Scripts Created**: 5
- `run.sh` - Master control (7.6K)
- `scripts/quick-start.sh` - Zero-config startup (7.0K)
- `scripts/test-runner.sh` - Automated testing (6.9K)
- `scripts/monitor-dashboard.sh` - Live monitoring (7.1K)
- `scripts/troubleshoot.sh` - Auto-diagnosis (7.0K)

**Total Automation**: 35.6K of bash scripts

**User Experience**:
- ✅ Zero manual typing required
- ✅ Full transparency (all logs visible)
- ✅ Complexity abstracted (simple commands)
- ✅ No rabbit holes (direct solutions)
- ✅ Cutting-edge UX (colors, progress bars, live updates)

**Time Saved**: ~90% reduction in manual operations

---

**Next Step**: Run `./run.sh` to start! 🚀

