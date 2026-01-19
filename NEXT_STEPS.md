# Next Steps - Prioritized Action Plan

## 🚀 Immediate Actions (Before First Test)

### 1. Configure Environment Variables
```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or vim, code, etc.
```

**Required values**:
- `TWILIO_SID` - From https://console.twilio.com/
- `TWILIO_AUTH_TOKEN` - From Twilio Console
- `TWILIO_NUMBER` - Your Twilio phone number (format: +15551234567)
- `BUSINESS_NUMBER` - Your phone number (format: +15551234567)

### 2. Start the Backend
```bash
docker-compose up --build
```

**Expected output**:
```
✓ Database initialized successfully
✓ Twilio client initialized successfully
✓ Starting Callback Service Backend
✓ Serving on http://0.0.0.0:8501
```

### 3. Verify Health Check
```bash
# In a new terminal
curl http://localhost:8501/health

# Expected response:
# {"status":"healthy","timestamp":"2024-01-19T...","twilio_configured":true}
```

### 4. Test Frontend Locally
```bash
# Option 1: Python simple server
cd frontend
python3 -m http.server 3000

# Option 2: Node.js http-server
npx http-server frontend -p 3000

# Open browser: http://localhost:3000
```

### 5. Test Callback Flow
1. Open http://localhost:3000 in browser
2. Enter your phone number (must be verified in Twilio if using trial account)
3. Click "Request Callback Now"
4. Your phone should ring within 10-20 seconds
5. Answer and wait for connection

---

## ⚠️ Critical Fixes (Before Production)

### Fix 1: Restrict CORS Origins
**Priority**: HIGH
**Time**: 5 minutes

**Edit `backend/app.py` line 48**:
```python
# Change from:
CORS(app, resources={r"/*": {"origins": "*"}})

# Change to:
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
CORS(app, resources={r"/*": {"origins": allowed_origins}})
```

**Add to `.env`**:
```env
ALLOWED_ORIGINS=http://localhost:3000,https://yourusername.github.io
```

### Fix 2: Add Rate Limiting
**Priority**: HIGH
**Time**: 10 minutes

**Add to `backend/requirements.txt`**:
```
flask-limiter==3.5.0
```

**Add to `backend/app.py` after line 48**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
```

**Modify `/request_callback` endpoint (line 200)**:
```python
@app.route("/request_callback", methods=["POST"])
@limiter.limit("5 per minute")  # Add this decorator
def request_callback():
    # ... existing code
```

**Rebuild**:
```bash
docker-compose down
docker-compose up --build
```

### Fix 3: Add OAuth Status Warning
**Priority**: MEDIUM
**Time**: 2 minutes

**Add to `README.md` after line 150 (OAuth Setup section)**:
```markdown
### ⚠️ IMPORTANT: OAuth Implementation Status

**Current Status**: DEMO ONLY

The OAuth implementation is a **placeholder**. It does NOT perform real authentication.

**Options**:
1. **Remove social login buttons** from `frontend/index.html` (recommended for MVP)
2. **Implement real OAuth** by registering apps with each provider
3. **Keep as-is** for demo purposes only (not for production)
```

### Fix 4: Add Phone Number Validation
**Priority**: MEDIUM
**Time**: 15 minutes

**Add to `backend/requirements.txt`**:
```
phonenumbers==8.13.26
```

**Add to `backend/app.py` after imports**:
```python
import phonenumbers

def validate_phone_number(number):
    """Validate and format phone number to E.164."""
    try:
        parsed = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(parsed):
            return False, "Invalid phone number"
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        return True, formatted
    except phonenumbers.NumberParseException as e:
        return False, f"Invalid format: {str(e)}"
```

**In `request_callback` function, add after line 210**:
```python
# Validate phone number
is_valid, result = validate_phone_number(visitor_phone)
if not is_valid:
    logger.warning(f"Invalid phone: {visitor_phone} - {result}")
    return jsonify(success=False, error=result), 400
visitor_phone = result  # Use E.164 format
```

---

## 📦 Deployment Steps

### Deploy Backend (Choose One)

#### Option A: Heroku
```bash
# Install Heroku CLI
# Login
heroku login

# Create app
heroku create your-callback-backend

# Set environment variables
heroku config:set TWILIO_SID=ACxxxx
heroku config:set TWILIO_AUTH_TOKEN=xxxx
heroku config:set TWILIO_NUMBER=+15551234567
heroku config:set BUSINESS_NUMBER=+15557654321
heroku config:set FRONTEND_URL=https://yourusername.github.io/repo-name

# Deploy
git push heroku main

# Check logs
heroku logs --tail
```

#### Option B: AWS EC2
```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker
sudo apt update
sudo apt install docker.io docker-compose -y

# Clone repo
git clone your-repo-url
cd your-repo

# Configure .env
nano .env

# Start
sudo docker-compose up -d

# Check logs
sudo docker logs -f callback-backend
```

#### Option C: DigitalOcean App Platform
1. Connect GitHub repo
2. Select `backend` directory
3. Set environment variables in dashboard
4. Deploy

### Deploy Frontend (GitHub Pages)

```bash
# 1. Push code to GitHub
git add .
git commit -m "Initial commit"
git push origin main

# 2. Enable GitHub Pages
# Go to: Settings → Pages
# Source: main branch → /frontend folder
# Save

# 3. Update frontend config
# Edit frontend/app.js:
const CONFIG = {
  BACKEND_URL: 'https://your-backend-url.com',  // Your deployed backend
  // ...
};

# 4. Commit and push
git add frontend/app.js
git commit -m "Update backend URL for production"
git push origin main

# 5. Wait 1-2 minutes, then visit:
# https://yourusername.github.io/repo-name/
```

---

## 🧪 Testing Checklist

- [ ] Backend starts without errors
- [ ] Health endpoint returns `{"status":"healthy","twilio_configured":true}`
- [ ] Frontend loads at http://localhost:3000
- [ ] No console errors in browser
- [ ] Form validation works (try submitting empty form)
- [ ] Callback request shows success message
- [ ] Business phone rings within 20 seconds
- [ ] After answering, visitor phone rings
- [ ] Both parties can hear each other
- [ ] If business doesn't answer, SMS is received
- [ ] Database stores callback record:
  ```bash
  docker exec -it callback-backend sqlite3 /app/data/callbacks.db "SELECT * FROM callbacks;"
  ```
- [ ] Logs show all events:
  ```bash
  docker exec callback-backend cat /tmp/app.log
  ```

---

## 📊 Monitoring Setup (Optional but Recommended)

### 1. Set Up Twilio Usage Alerts
1. Go to Twilio Console → Usage → Triggers
2. Create trigger: "Alert when usage exceeds $10"
3. Add your email

### 2. Set Up Log Monitoring
```bash
# Create log monitoring script
cat > monitor_logs.sh << 'EOF'
#!/bin/bash
docker exec callback-backend tail -f /tmp/app.log | grep -i "error\|warning\|failed"
EOF

chmod +x monitor_logs.sh
./monitor_logs.sh
```

### 3. Database Backup Script
```bash
# Create backup script
cat > backup_db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec callback-backend sqlite3 /app/data/callbacks.db ".backup /app/data/backup_${DATE}.db"
echo "Backup created: backup_${DATE}.db"
EOF

chmod +x backup_db.sh

# Run daily with cron
crontab -e
# Add: 0 2 * * * /path/to/backup_db.sh
```

---

## 🎯 Success Criteria

You'll know everything is working when:

✅ Backend health check returns healthy
✅ Frontend loads without errors
✅ Callback request completes successfully
✅ Phone calls connect both parties
✅ SMS fallback works for missed calls
✅ Database records all callbacks
✅ Logs show comprehensive event trail
✅ No errors in production for 24 hours
✅ Cost stays within expected range

---

## 📞 Support Resources

- **Twilio Docs**: https://www.twilio.com/docs
- **Flask Docs**: https://flask.palletsprojects.com/
- **Docker Docs**: https://docs.docker.com/
- **This Project's README**: See `README.md` for troubleshooting

---

**Ready to start?** Begin with "Immediate Actions" section above! 🚀

