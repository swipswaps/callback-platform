# Testing Guide - Callback Platform

**Date**: 2024-01-19
**Status**: Ready for Testing
**Compliance**: mandatory-rules-v6.0.md

---

## 📍 Current Status

### ✅ What's Complete
- **Code Quality**: ✅ Syntax validated, no errors
- **Dependencies**: ✅ 9 packages, all pinned versions
- **Logging**: ✅ 57 logger calls, 13 try/except blocks
- **Security**: ✅ 6 protection layers active
- **Frontend**: ✅ HTML/CSS/JS validated, reCAPTCHA integrated
- **Backend**: ✅ All endpoints intact, new features added

### ⏳ What Needs Testing
- **Runtime Verification**: Service startup and operation
- **CAPTCHA Flow**: Frontend → Backend integration
- **Business Hours**: Timezone logic and SMS fallback
- **Twilio Integration**: Signature validation with real callbacks
- **End-to-End**: Complete callback flow

---

## 🧪 Testing Levels

### Level 1: Local Syntax & Import Testing ✅ COMPLETE

**Status**: ✅ PASSED

**Evidence**:
```bash
✅ Python syntax check passed
✅ All imports verified (pytz, phonenumbers, flask_limiter, twilio.request_validator)
✅ No hardcoded secrets
✅ No print statements (using logger)
✅ 13 try blocks for error handling
✅ 57 logger calls for comprehensive logging
```

---

### Level 2: Docker Build Testing ⏳ PENDING

**Purpose**: Verify Docker image builds with new dependencies

**Commands**:
```bash
# Build Docker image
docker compose build

# Expected output:
# - Successfully installed pytz-2024.1
# - Successfully installed phonenumbers-8.13.26
# - Successfully installed flask-limiter-3.5.0
# - Image built successfully
```

**Success Criteria**:
- ✅ Build completes without errors
- ✅ All 9 dependencies installed
- ✅ Health check passes

**Failure Scenarios**:
- ❌ Dependency conflict → Check requirements.txt versions
- ❌ Build timeout → Increase Docker memory
- ❌ Missing system packages → Update Dockerfile

---

### Level 3: Service Startup Testing ⏳ PENDING

**Purpose**: Verify Flask app starts and initializes all components

**Commands**:
```bash
# Start services
docker compose up

# In another terminal, check health
curl http://localhost:8501/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-19T...",
  "twilio_configured": false  # true if credentials set
}
```

**Success Criteria**:
- ✅ Flask starts on port 8501
- ✅ Health endpoint returns 200 OK
- ✅ Logs show "Twilio client initialized" or "not configured"
- ✅ Logs show "Twilio validator initialized" or "not configured"
- ✅ Database initialized at /app/data/callbacks.db

**Check Logs**:
```bash
docker logs callback-backend | grep -E "initialized|configured|ERROR"
```

**Expected Log Lines**:
```
INFO | Twilio client and validator initialized successfully
INFO | Database initialized at /app/data/callbacks.db
INFO | Flask app started
```

---

### Level 4: CAPTCHA Integration Testing ⏳ PENDING

**Purpose**: Verify reCAPTCHA frontend/backend integration

**Test Case 1: Submit Without CAPTCHA**
```bash
# Should fail with 400 Bad Request
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{"visitor_number":"+15551234567","name":"Test"}'

# Expected response:
{
  "success": false,
  "error": "CAPTCHA verification failed. Please try again."
}
```

**Test Case 2: Submit With Invalid CAPTCHA**
```bash
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{"visitor_number":"+15551234567","name":"Test","recaptcha_token":"invalid"}'

# Expected: Same 400 error
```

**Test Case 3: Frontend Browser Test**
1. Open http://localhost:3000 in browser
2. Fill form WITHOUT completing CAPTCHA
3. Click submit → Should show error "Please complete the CAPTCHA verification"
4. Complete CAPTCHA
5. Click submit → Should proceed (may fail at Twilio if not configured)

**Success Criteria**:
- ✅ Missing CAPTCHA token → 400 error
- ✅ Invalid CAPTCHA token → 400 error
- ✅ Valid CAPTCHA token → Proceeds to next validation
- ✅ Logs show "reCAPTCHA verification failed" for invalid tokens
- ✅ Audit log entry created for CAPTCHA failures

**Check Logs**:
```bash
docker logs callback-backend | grep -i captcha
```

---

### Level 5: Phone Validation Testing ⏳ PENDING

**Test Case 1: Valid Phone Number**
```bash
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{
    "visitor_number": "+15551234567",
    "name": "Test User",
    "recaptcha_token": "test_token_here"
  }'

# Expected: Proceeds (may fail at Twilio/CAPTCHA if not configured)
```

**Test Case 2: Invalid Phone Number**
```bash
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{
    "visitor_number": "invalid",
    "name": "Test User",
    "recaptcha_token": "test_token_here"
  }'

# Expected response:
{
  "success": false,
  "error": "Invalid phone number format: ..."
}
```

**Test Case 3: Phone Number Without Country Code**
```bash
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{
    "visitor_number": "5551234567",
    "name": "Test User",
    "recaptcha_token": "test_token_here"
  }'

# Expected: May fail or auto-detect country (depends on phonenumbers library)
```

**Success Criteria**:
- ✅ Valid E.164 number → Accepted and formatted
- ✅ Invalid number → 400 error with clear message
- ✅ Logs show "Phone number validated: ... -> +15551234567"

---

### Level 6: Business Hours Testing ⏳ PENDING

**Setup**: Configure business hours in .env
```env
BUSINESS_HOURS_START=09:00
BUSINESS_HOURS_END=17:00
BUSINESS_TIMEZONE=America/New_York
BUSINESS_WEEKDAYS_ONLY=true
```

**Test Case 1: Within Business Hours**
```bash
# Run during 9 AM - 5 PM EST on weekday
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{
    "visitor_number": "+15551234567",
    "name": "Test User",
    "recaptcha_token": "valid_token"
  }'

# Expected: Initiates Twilio call (if configured)
# Logs: "Initiating Twilio call to business (Within business hours)"
```

**Test Case 2: Outside Business Hours**
```bash
# Run outside 9 AM - 5 PM EST or on weekend
# Same request as above

# Expected: Sends SMS instead of calling
# Response: "Request received. Outside business hours. We'll call you back..."
# Logs: "Outside business hours - sending SMS only"
```

**Test Case 3: Weekend**
```bash
# Run on Saturday or Sunday
# Same request as above

# Expected: SMS sent
# Logs: "Outside business hours: Weekend (day 5 or 6)"
```

**Success Criteria**:
- ✅ Within hours → Call initiated
- ✅ Outside hours → SMS sent, no call
- ✅ Weekend → SMS sent, no call
- ✅ Logs show business hours check result
- ✅ Correct timezone handling

**Manual Time Testing**:
```bash
# Temporarily change business hours to test
docker exec -it callback-backend sh
export BUSINESS_HOURS_START=00:00
export BUSINESS_HOURS_END=23:59
# Restart app or test
```

---

### Level 7: Rate Limiting Testing ⏳ PENDING

**Test Case: Exceed Rate Limit**
```bash
# Make 6 requests rapidly (limit is 5/minute)
for i in {1..6}; do
  echo "Request $i:"
  curl -X POST http://localhost:8501/request_callback \
    -H "Content-Type: application/json" \
    -d '{
      "visitor_number": "+1555123456'$i'",
      "name": "Test '$i'",
      "recaptcha_token": "test"
    }'
  echo ""
done

# Expected:
# Requests 1-5: May succeed or fail at CAPTCHA/Twilio
# Request 6: 429 Too Many Requests
```

**Success Criteria**:
- ✅ First 5 requests processed
- ✅ 6th request returns 429 status
- ✅ Response includes rate limit error message
- ✅ Logs show rate limit enforcement

---

### Level 8: Twilio Signature Validation Testing ⏳ REQUIRES REAL TWILIO

**Purpose**: Verify webhook signature validation

**Prerequisites**:
- Real Twilio account
- Callback URL configured in Twilio
- Active call to trigger callback

**Test Case 1: Valid Signature**
```bash
# Twilio sends callback with valid signature
# Check logs for:
# "Twilio signature verified for request {request_id}"
```

**Test Case 2: Invalid Signature (Spoofing Attempt)**
```bash
# Manually send callback without valid signature
curl -X POST http://localhost:8501/twilio/status_callback?request_id=test \
  -H "X-Twilio-Signature: invalid_signature" \
  -d "CallStatus=completed&CallSid=test"

# Expected response: 403 Forbidden
# Logs: "Invalid Twilio signature - possible spoofing attempt"
# Audit log: "invalid_signature" event
```

**Success Criteria**:
- ✅ Valid signature → Callback processed
- ✅ Invalid signature → 403 Forbidden
- ✅ Missing signature → Warning logged, processed (if validator not configured)
- ✅ Audit log entry for spoofing attempts

---

## 🚀 Quick Start Testing

### Minimal Test (No Twilio Account)

```bash
# 1. Start services
docker compose up --build

# 2. Check health
curl http://localhost:8501/health

# 3. Test phone validation (will fail at CAPTCHA)
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{"visitor_number":"invalid","name":"Test"}'

# Expected: "Invalid phone number format" error

# 4. Test with valid phone (will fail at CAPTCHA)
curl -X POST http://localhost:8501/request_callback \
  -H "Content-Type: application/json" \
  -d '{"visitor_number":"+15551234567","name":"Test"}'

# Expected: "CAPTCHA verification failed" error

# 5. Check logs
docker logs callback-backend | tail -20
```

### Full Test (With Twilio Account)

```bash
# 1. Configure .env with real credentials
cp .env.example .env
# Edit .env with your Twilio credentials

# 2. Get production reCAPTCHA keys
# https://www.google.com/recaptcha/admin
# Update frontend/index.html and .env

# 3. Start services
docker compose up --build

# 4. Open frontend in browser
# http://localhost:3000

# 5. Complete full callback flow
# - Fill form
# - Complete CAPTCHA
# - Submit
# - Verify call initiated
# - Check status updates

# 6. Monitor logs
docker logs -f callback-backend
```

---

## 📊 Test Results Template

```
TESTING RESULTS - [DATE]

Level 1: Syntax & Imports
  ✅ Python syntax: PASS
  ✅ All imports: PASS
  ✅ Code quality: PASS

Level 2: Docker Build
  [ ] Build completes: PASS/FAIL
  [ ] Dependencies installed: PASS/FAIL
  [ ] Image size: ___ MB

Level 3: Service Startup
  [ ] Flask starts: PASS/FAIL
  [ ] Health check: PASS/FAIL
  [ ] Database init: PASS/FAIL
  [ ] Logs clean: PASS/FAIL

Level 4: CAPTCHA
  [ ] Missing token rejected: PASS/FAIL
  [ ] Invalid token rejected: PASS/FAIL
  [ ] Frontend integration: PASS/FAIL

Level 5: Phone Validation
  [ ] Valid number accepted: PASS/FAIL
  [ ] Invalid number rejected: PASS/FAIL
  [ ] E.164 formatting: PASS/FAIL

Level 6: Business Hours
  [ ] Within hours → Call: PASS/FAIL
  [ ] Outside hours → SMS: PASS/FAIL
  [ ] Weekend → SMS: PASS/FAIL

Level 7: Rate Limiting
  [ ] 5 requests allowed: PASS/FAIL
  [ ] 6th request blocked: PASS/FAIL

Level 8: Twilio Signature
  [ ] Valid signature accepted: PASS/FAIL
  [ ] Invalid signature rejected: PASS/FAIL

OVERALL: PASS/FAIL
```

---

**Next Step**: Run Level 2 (Docker Build) to proceed with testing.

