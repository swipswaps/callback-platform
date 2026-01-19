"""
Callback Service Backend - Flask API with Twilio Integration

Features:
- OAuth social login (Google, Facebook, Instagram, X, WhatsApp)
- Twilio-based callback system
- SQLite persistent storage
- Real-time status tracking
- SMS fallback for missed calls
- Comprehensive logging per Rule 25
- Security: CORS, rate limiting, input validation
"""

import os
import sys
import json
import base64
import sqlite3
import logging
import uuid
from datetime import datetime
from flask import Flask, request, redirect, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from oauth_providers import get_user_info
import phonenumbers
import pytz
from datetime import time as dt_time

# Configure comprehensive logging per Rule 25
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)
    
    file_handler = logging.FileHandler("/tmp/app.log", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(file_handler)

# Initialize Flask app
app = Flask(__name__)

# CORS configuration - restrict origins for security
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Rate limiting configuration - prevent abuse and control costs
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuration from environment variables
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER", "")
BUSINESS_NUMBER = os.environ.get("BUSINESS_NUMBER", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/tmp/callbacks.db")
RECAPTCHA_SECRET = os.environ.get("RECAPTCHA_SECRET", "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")  # Test key

# Business hours configuration
BUSINESS_HOURS_START = os.environ.get("BUSINESS_HOURS_START", "09:00")  # 9 AM
BUSINESS_HOURS_END = os.environ.get("BUSINESS_HOURS_END", "17:00")  # 5 PM
BUSINESS_TIMEZONE = os.environ.get("BUSINESS_TIMEZONE", "America/New_York")
BUSINESS_WEEKDAYS_ONLY = os.environ.get("BUSINESS_WEEKDAYS_ONLY", "true").lower() == "true"

# Initialize Twilio client
twilio_client = None
twilio_validator = None
if TWILIO_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        twilio_validator = RequestValidator(TWILIO_AUTH_TOKEN)
        logger.info("Twilio client and validator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Twilio client: {str(e)}")
else:
    logger.warning("Twilio credentials not configured - callback functionality will be limited")


def verify_recaptcha(token):
    """
    Verify Google reCAPTCHA v2 token.

    Args:
        token (str): reCAPTCHA response token from frontend

    Returns:
        bool: True if verification successful, False otherwise
    """
    if not token:
        logger.warning("reCAPTCHA token missing")
        return False

    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': RECAPTCHA_SECRET,
                'response': token
            },
            timeout=10
        )
        result = response.json()
        success = result.get('success', False)

        if success:
            logger.debug(f"reCAPTCHA verification successful")
        else:
            error_codes = result.get('error-codes', [])
            logger.warning(f"reCAPTCHA verification failed: {error_codes}")

        return success
    except requests.exceptions.RequestException as e:
        logger.error(f"reCAPTCHA verification request failed: {str(e)}")
        # Fail open in case of network issues (configurable)
        return False
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {str(e)}")
        return False


def is_business_hours():
    """
    Check if current time is within business hours.

    Returns:
        tuple: (is_open: bool, message: str) where message explains the status
    """
    try:
        tz = pytz.timezone(BUSINESS_TIMEZONE)
        now = datetime.now(tz)
        current_time = now.time()

        # Parse business hours
        start_hour, start_min = map(int, BUSINESS_HOURS_START.split(':'))
        end_hour, end_min = map(int, BUSINESS_HOURS_END.split(':'))
        start_time = dt_time(start_hour, start_min)
        end_time = dt_time(end_hour, end_min)

        # Check if weekend
        if BUSINESS_WEEKDAYS_ONLY and now.weekday() >= 5:  # Saturday=5, Sunday=6
            logger.debug(f"Outside business hours: Weekend (day {now.weekday()})")
            return False, "Outside business hours (weekend)"

        # Check if within time range
        if not (start_time <= current_time <= end_time):
            logger.debug(f"Outside business hours: {current_time} not in {start_time}-{end_time}")
            return False, f"Outside business hours ({BUSINESS_HOURS_START}-{BUSINESS_HOURS_END} {BUSINESS_TIMEZONE})"

        logger.debug(f"Within business hours: {current_time} in {start_time}-{end_time}")
        return True, "Within business hours"

    except Exception as e:
        logger.error(f"Error checking business hours: {str(e)}")
        # Fail open - allow calls if business hours check fails
        return True, "Business hours check unavailable"


def validate_phone_number(number):
    """
    Validate and format phone number to E.164 format.

    Args:
        number (str): Phone number to validate

    Returns:
        tuple: (is_valid: bool, result: str) where result is formatted number or error message
    """
    try:
        parsed = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(parsed):
            return False, "Invalid phone number"
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        logger.debug(f"Phone number validated: {number} -> {formatted}")
        return True, formatted
    except phonenumbers.NumberParseException as e:
        logger.warning(f"Phone number parse error: {number} - {str(e)}")
        return False, f"Invalid phone number format: {str(e)}"


def init_database():
    """Initialize SQLite database with proper schema per Rule 11."""
    logger.info(f"Initializing database at {DATABASE_PATH}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create callbacks table - avoid SQL reserved keywords per Rule 11
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS callbacks (
            request_id TEXT PRIMARY KEY,
            visitor_name TEXT,
            visitor_email TEXT,
            visitor_phone TEXT NOT NULL,
            request_status TEXT NOT NULL,
            status_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            call_sid TEXT,
            sms_sid TEXT
        )
    """)
    
    # Create audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            event_type TEXT NOT NULL,
            event_data TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")


def log_audit_event(request_id, event_type, event_data=None):
    """Log audit events to database."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_log (request_id, event_type, event_data, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            request_id,
            event_type,
            json.dumps(event_data) if event_data else None,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Audit event logged: {event_type} for request {request_id}")
    except Exception as e:
        logger.error(f"Failed to log audit event: {str(e)}")


def update_callback_status(request_id, status, message=None, call_sid=None, sms_sid=None):
    """Update callback status in database."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE callbacks
            SET request_status = ?, status_message = ?, updated_at = ?, call_sid = ?, sms_sid = ?
            WHERE request_id = ?
        """, (
            status,
            message,
            datetime.utcnow().isoformat(),
            call_sid,
            sms_sid,
            request_id
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Callback status updated: {request_id} -> {status}")
        log_audit_event(request_id, "status_update", {"status": status, "message": message})
    except Exception as e:
        logger.error(f"Failed to update callback status: {str(e)}")


# Initialize database on startup
init_database()


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "twilio_configured": twilio_client is not None
    })


@app.route("/oauth/login/<provider>", methods=["GET"])
def oauth_login(provider):
    """
    Initiate OAuth login flow for specified provider.
    In production, this would redirect to the actual OAuth provider.
    For demo purposes, we simulate the flow.
    """
    logger.info(f"OAuth login initiated for provider: {provider}")
    log_audit_event(None, "oauth_login_initiated", {"provider": provider})

    # In production, redirect to actual OAuth provider
    # For now, simulate with a dummy token
    return redirect(f"/oauth/callback/{provider}?token=demo_token_{provider}")


@app.route("/oauth/callback/<provider>", methods=["GET"])
def oauth_callback(provider):
    """
    Handle OAuth callback and fetch user information.
    Redirects back to frontend with user data.
    """
    logger.info(f"OAuth callback received for provider: {provider}")

    token = request.args.get("token")
    if not token:
        logger.error(f"No token received in OAuth callback for {provider}")
        return redirect(f"{FRONTEND_URL}?error=oauth_failed")

    # Fetch user info from provider
    user_info = get_user_info(provider, token)

    if not user_info:
        logger.error(f"Failed to fetch user info from {provider}")
        return redirect(f"{FRONTEND_URL}?error=oauth_failed")

    # Encode user info and redirect to frontend
    encoded_user = base64.b64encode(json.dumps(user_info).encode()).decode()
    logger.info(f"OAuth successful for {provider}, redirecting to frontend")

    log_audit_event(None, "oauth_completed", {"provider": provider, "has_email": bool(user_info.get("email"))})

    return redirect(f"{FRONTEND_URL}?user={encoded_user}")


@app.route("/request_callback", methods=["POST"])
@limiter.limit("5 per minute")  # Prevent abuse - max 5 callback requests per minute
def request_callback():
    """
    Handle callback request from visitor.

    Flow:
    1. Validate input
    2. Store request in database
    3. Call business number via Twilio
    4. If business answers, bridge to visitor
    5. If business doesn't answer, send SMS to business
    """
    try:
        data = request.get_json()

        # Verify reCAPTCHA token
        recaptcha_token = data.get("recaptcha_token", "")
        if not verify_recaptcha(recaptcha_token):
            logger.warning(f"reCAPTCHA verification failed for request from {request.remote_addr}")
            log_audit_event(None, "captcha_failed", {
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'Unknown')
            })
            return jsonify(success=False, error="CAPTCHA verification failed. Please try again."), 400

        # Validate required fields
        visitor_phone = data.get("visitor_number", "").strip()
        if not visitor_phone:
            logger.warning("Callback request missing visitor phone number")
            return jsonify(success=False, error="Phone number is required"), 400

        # Validate and format phone number
        is_valid, result = validate_phone_number(visitor_phone)
        if not is_valid:
            logger.warning(f"Invalid phone number submitted: {visitor_phone} - {result}")
            return jsonify(success=False, error=result), 400
        visitor_phone = result  # Use E.164 formatted number

        visitor_name = data.get("name", "").strip()
        visitor_email = data.get("email", "").strip()

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        logger.info(f"Callback request received: {request_id} from {visitor_phone}")

        # Store in database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO callbacks (
                request_id, visitor_name, visitor_email, visitor_phone,
                request_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            visitor_name,
            visitor_email,
            visitor_phone,
            "pending",
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        log_audit_event(request_id, "callback_requested", {
            "visitor_phone": visitor_phone,
            "has_name": bool(visitor_name),
            "has_email": bool(visitor_email)
        })

        # Check business hours before initiating call
        is_open, hours_message = is_business_hours()

        # Initiate Twilio call if configured
        if twilio_client and BUSINESS_NUMBER and TWILIO_NUMBER:
            # If outside business hours, send SMS instead of calling
            if not is_open:
                logger.info(f"Outside business hours for request {request_id} - sending SMS only")
                try:
                    message = twilio_client.messages.create(
                        to=BUSINESS_NUMBER,
                        from_=TWILIO_NUMBER,
                        body=f"Callback request from {visitor_name or 'visitor'} at {visitor_phone}. Received outside business hours. Please call back during business hours."
                    )
                    update_callback_status(request_id, "sms_sent", f"SMS sent ({hours_message})", sms_sid=message.sid)
                    logger.info(f"SMS sent for outside-hours request: {message.sid}")
                    log_audit_event(request_id, "sms_sent_outside_hours", {"sms_sid": message.sid})

                    return jsonify(
                        success=True,
                        request_id=request_id,
                        message=f"Request received. {hours_message}. We'll call you back during business hours."
                    ), 200
                except Exception as sms_error:
                    logger.error(f"Failed to send outside-hours SMS: {str(sms_error)}")
                    update_callback_status(request_id, "failed", f"SMS failed: {str(sms_error)}")
                    return jsonify(
                        success=False,
                        error="Failed to process request. Please try again later."
                    ), 500

            try:
                # Call business first (within business hours)
                logger.info(f"Initiating Twilio call to business for request {request_id} ({hours_message})")

                call = twilio_client.calls.create(
                    to=BUSINESS_NUMBER,
                    from_=TWILIO_NUMBER,
                    url=f"http://twimlets.com/holdmusic?Bucket=com.twilio.music.classical",
                    status_callback=f"{request.host_url}twilio/status_callback?request_id={request_id}",
                    status_callback_event=["completed", "no-answer", "busy", "failed"],
                    timeout=20
                )

                update_callback_status(request_id, "calling", "Calling business", call_sid=call.sid)
                logger.info(f"Twilio call initiated: {call.sid}")

            except TwilioRestException as e:
                logger.error(f"Twilio call failed: {str(e)}")
                update_callback_status(request_id, "failed", f"Call failed: {str(e)}")

                # Send SMS fallback to business
                try:
                    message = twilio_client.messages.create(
                        to=BUSINESS_NUMBER,
                        from_=TWILIO_NUMBER,
                        body=f"Missed callback request from {visitor_name or 'visitor'} at {visitor_phone}. Please call them back."
                    )
                    update_callback_status(request_id, "sms_sent", "SMS sent to business", sms_sid=message.sid)
                    logger.info(f"SMS fallback sent: {message.sid}")
                except Exception as sms_error:
                    logger.error(f"SMS fallback failed: {str(sms_error)}")
        else:
            logger.warning("Twilio not configured - callback request stored but not processed")
            update_callback_status(request_id, "pending", "Twilio not configured")

        return jsonify(success=True, request_id=request_id)

    except Exception as e:
        logger.error(f"Error processing callback request: {str(e)}", exc_info=True)
        return jsonify(success=False, error="Internal server error"), 500


@app.route("/status/<request_id>", methods=["GET"])
def get_status(request_id):
    """Get current status of a callback request."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT request_status, status_message, updated_at
            FROM callbacks
            WHERE request_id = ?
        """, (request_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.warning(f"Status requested for unknown request_id: {request_id}")
            return jsonify(success=False, error="Request not found"), 404

        status, message, updated_at = row

        return jsonify(
            success=True,
            status=status,
            message=message,
            updated_at=updated_at
        )

    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        return jsonify(success=False, error="Internal server error"), 500


@app.route("/twilio/status_callback", methods=["POST"])
def twilio_status_callback():
    """
    Handle Twilio status callbacks.
    Updates callback status based on call outcome.
    Verifies Twilio signature to prevent spoofing attacks.
    """
    try:
        request_id = request.args.get("request_id")

        # Verify Twilio signature to prevent spoofed callbacks
        if twilio_validator:
            signature = request.headers.get('X-Twilio-Signature', '')
            url = request.url
            params = request.form.to_dict()

            if not twilio_validator.validate(url, params, signature):
                logger.warning(f"Invalid Twilio signature - possible spoofing attempt for request {request_id}")
                log_audit_event(request_id, "invalid_signature", {
                    "url": url,
                    "signature_provided": bool(signature),
                    "remote_addr": request.remote_addr
                })
                return "", 403

            logger.debug(f"Twilio signature verified for request {request_id}")
        else:
            logger.warning("Twilio validator not configured - signature verification skipped")

        call_status = request.form.get("CallStatus")
        call_sid = request.form.get("CallSid")

        logger.info(f"Twilio status callback: {request_id} - {call_status}")

        if not request_id:
            logger.error("Status callback missing request_id")
            return "", 400

        # Update status based on call outcome
        if call_status == "completed":
            update_callback_status(request_id, "completed", "Call completed successfully")
        elif call_status in ["no-answer", "busy", "failed"]:
            update_callback_status(request_id, "failed", f"Call {call_status}")

            # Send SMS to business as fallback
            if twilio_client:
                try:
                    # Fetch visitor info
                    conn = sqlite3.connect(DATABASE_PATH)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT visitor_name, visitor_phone
                        FROM callbacks
                        WHERE request_id = ?
                    """, (request_id,))
                    row = cursor.fetchone()
                    conn.close()

                    if row:
                        visitor_name, visitor_phone = row
                        message = twilio_client.messages.create(
                            to=BUSINESS_NUMBER,
                            from_=TWILIO_NUMBER,
                            body=f"Missed callback from {visitor_name or 'visitor'} at {visitor_phone}. Please call back."
                        )
                        update_callback_status(request_id, "sms_sent", "SMS sent to business", sms_sid=message.sid)
                        logger.info(f"SMS fallback sent for missed call: {message.sid}")
                except Exception as e:
                    logger.error(f"Failed to send SMS fallback: {str(e)}")

        return "", 200

    except Exception as e:
        logger.error(f"Error in status callback: {str(e)}")
        return "", 500


if __name__ == "__main__":
    logger.info("Starting Callback Service Backend")
    logger.info(f"Frontend URL: {FRONTEND_URL}")
    logger.info(f"Database: {DATABASE_PATH}")
    logger.info(f"Twilio configured: {twilio_client is not None}")

    # Use waitress for production-ready WSGI server
    from waitress import serve
    serve(app, host="0.0.0.0", port=8501)


