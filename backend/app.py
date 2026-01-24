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
import requests
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

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Facebook OAuth configuration
FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "")

# Business hours configuration
BUSINESS_HOURS_START = os.environ.get("BUSINESS_HOURS_START", "09:00")  # 9 AM
BUSINESS_HOURS_END = os.environ.get("BUSINESS_HOURS_END", "17:00")  # 5 PM
BUSINESS_TIMEZONE = os.environ.get("BUSINESS_TIMEZONE", "America/New_York")
BUSINESS_WEEKDAYS_ONLY = os.environ.get("BUSINESS_WEEKDAYS_ONLY", "true").lower() == "true"

# Cost protection limits
MAX_CALLS_PER_DAY = int(os.environ.get("MAX_CALLS_PER_DAY", "100"))
MAX_SMS_PER_DAY = int(os.environ.get("MAX_SMS_PER_DAY", "200"))
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")  # Email for cost alerts

# Provider selection configuration
CALLBACK_PROVIDER = os.environ.get("CALLBACK_PROVIDER", "twilio").lower()

# Asterisk configuration (for asterisk provider)
ASTERISK_HOST = os.environ.get("ASTERISK_HOST", "localhost")
ASTERISK_AMI_PORT = int(os.environ.get("ASTERISK_AMI_PORT", "5038"))
ASTERISK_AMI_USER = os.environ.get("ASTERISK_AMI_USER", "callback_manager")
ASTERISK_AMI_SECRET = os.environ.get("ASTERISK_AMI_SECRET", "callback_secret_2026")


# ============================================================================
# PROVIDER ABSTRACTION LAYER
# ============================================================================
# Per Rule 6 (Scope Containment): Add Asterisk as alternative without removing Twilio
# Per Rule 18 (Feature Removal Prohibition): Preserve all existing Twilio functionality
# Per Rule 25 (Comprehensive Application Logging): All providers have comprehensive logging

class CallbackProvider:
    """
    Base class for callback providers.
    Defines the interface that all providers must implement.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def make_call(self, to_number, from_number, request_id):
        """
        Initiate a callback call.

        Args:
            to_number: Phone number to call (E.164 format)
            from_number: Caller ID number (E.164 format)
            request_id: Unique request ID for tracking

        Returns:
            dict: {
                'success': bool,
                'call_sid': str (provider-specific call ID),
                'message': str (status message)
            }
        """
        raise NotImplementedError("Subclasses must implement make_call()")

    def send_sms(self, to_number, from_number, message):
        """
        Send SMS message.

        Args:
            to_number: Phone number to send to (E.164 format)
            from_number: Sender phone number (E.164 format)
            message: SMS message text

        Returns:
            dict: {
                'success': bool,
                'sms_sid': str (provider-specific message ID),
                'message': str (status message)
            }
        """
        raise NotImplementedError("Subclasses must implement send_sms()")

    def is_configured(self):
        """
        Check if provider is properly configured.

        Returns:
            bool: True if configured, False otherwise
        """
        raise NotImplementedError("Subclasses must implement is_configured()")


class TwilioProvider(CallbackProvider):
    """
    Twilio callback provider.
    Wraps existing Twilio functionality with provider interface.
    Per Rule 18: Preserves all existing Twilio features.
    """

    def __init__(self, sid, auth_token, twilio_number):
        super().__init__()
        self.sid = sid
        self.auth_token = auth_token
        self.twilio_number = twilio_number
        self.client = None
        self.validator = None

        if sid and auth_token:
            try:
                self.client = Client(sid, auth_token)
                self.validator = RequestValidator(auth_token)
                self.logger.info("Twilio provider initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Twilio provider: {str(e)}")
        else:
            self.logger.warning("Twilio credentials not configured")

    def make_call(self, to_number, from_number, request_id):
        """Initiate Twilio call to business number"""
        if not self.client:
            self.logger.error("Twilio client not initialized")
            return {'success': False, 'call_sid': None, 'message': 'Twilio not configured'}

        try:
            self.logger.info(f"Initiating Twilio call for request {request_id}: {from_number} -> {to_number}")

            call = self.client.calls.create(
                to=to_number,
                from_=from_number,
                url=f"http://twimlets.com/holdmusic?Bucket=com.twilio.music.classical",
                status_callback=f"http://localhost:8501/twilio/status_callback?request_id={request_id}",
                status_callback_event=["completed", "no-answer", "busy", "failed"],
                timeout=20
            )

            self.logger.info(f"Twilio call initiated successfully: {call.sid}")
            return {'success': True, 'call_sid': call.sid, 'message': 'Call initiated'}

        except TwilioRestException as e:
            self.logger.error(f"Twilio call failed: {str(e)}")
            return {'success': False, 'call_sid': None, 'message': str(e)}

    def send_sms(self, to_number, from_number, message):
        """Send SMS via Twilio"""
        if not self.client:
            self.logger.error("Twilio client not initialized")
            return {'success': False, 'sms_sid': None, 'message': 'Twilio not configured'}

        try:
            self.logger.info(f"Sending Twilio SMS: {from_number} -> {to_number}")

            msg = self.client.messages.create(
                to=to_number,
                from_=from_number,
                body=message
            )

            self.logger.info(f"Twilio SMS sent successfully: {msg.sid}")
            return {'success': True, 'sms_sid': msg.sid, 'message': 'SMS sent'}

        except TwilioRestException as e:
            self.logger.error(f"Twilio SMS failed: {str(e)}")
            return {'success': False, 'sms_sid': None, 'message': str(e)}

    def is_configured(self):
        """Check if Twilio is configured"""
        return self.client is not None


class AsteriskProvider(CallbackProvider):
    """
    Asterisk PBX callback provider.
    Uses Asterisk Manager Interface (AMI) to originate calls.
    Per Rule 25: Comprehensive logging for troubleshooting.
    """

    def __init__(self, host, port, username, secret):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.secret = secret
        self._test_connection()

    def _test_connection(self):
        """Test AMI connection on initialization"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            sock.close()
            self.logger.info(f"Asterisk AMI connection test successful: {self.host}:{self.port}")
        except Exception as e:
            self.logger.warning(f"Asterisk AMI connection test failed: {str(e)}")

    def _ami_connect(self):
        """
        Connect to Asterisk Manager Interface.
        Returns socket connection or None on failure.
        """
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.host, self.port))

            # Read welcome message
            welcome = sock.recv(1024).decode('utf-8')
            self.logger.debug(f"AMI welcome: {welcome.strip()}")

            # Login
            login_cmd = (
                f"Action: Login\r\n"
                f"Username: {self.username}\r\n"
                f"Secret: {self.secret}\r\n"
                f"\r\n"
            )
            sock.send(login_cmd.encode('utf-8'))

            # Read login response
            response = sock.recv(1024).decode('utf-8')
            self.logger.debug(f"AMI login response: {response.strip()}")

            if "Success" in response:
                self.logger.info("AMI login successful")
                return sock
            else:
                self.logger.error(f"AMI login failed: {response}")
                sock.close()
                return None

        except Exception as e:
            self.logger.error(f"AMI connection failed: {str(e)}")
            return None

    def _ami_disconnect(self, sock):
        """Disconnect from AMI"""
        try:
            logoff_cmd = "Action: Logoff\r\n\r\n"
            sock.send(logoff_cmd.encode('utf-8'))
            sock.close()
            self.logger.debug("AMI disconnected")
        except Exception as e:
            self.logger.error(f"AMI disconnect error: {str(e)}")

    def make_call(self, to_number, from_number, request_id):
        """
        Initiate call via Asterisk AMI Originate command.

        This originates a call to the business number, and when answered,
        connects to the AGI script which handles the callback logic.
        """
        sock = self._ami_connect()
        if not sock:
            return {'success': False, 'call_sid': None, 'message': 'AMI connection failed'}

        try:
            self.logger.info(f"Originating Asterisk call for request {request_id}: {from_number} -> {to_number}")

            # Generate unique action ID for tracking
            action_id = f"callback_{request_id}"

            # Originate call via AMI using Twilio SIP trunk (PJSIP)
            # This calls the business number (to_number) via Twilio SIP trunk
            # and then connects to the customer (from_number)
            originate_cmd = (
                f"Action: Originate\r\n"
                f"ActionID: {action_id}\r\n"
                f"Channel: PJSIP/{to_number}@twilio-trunk\r\n"
                f"Context: callback-outbound\r\n"
                f"Exten: {from_number}\r\n"
                f"Priority: 1\r\n"
                f"CallerID: {from_number}\r\n"
                f"Timeout: 30000\r\n"
                f"Async: yes\r\n"
                f"\r\n"
            )

            sock.send(originate_cmd.encode('utf-8'))

            # Read response
            response = sock.recv(2048).decode('utf-8')
            self.logger.debug(f"AMI originate response: {response.strip()}")

            self._ami_disconnect(sock)

            if "Success" in response:
                self.logger.info(f"Asterisk call originated successfully: {action_id}")
                return {'success': True, 'call_sid': action_id, 'message': 'Call originated'}
            else:
                self.logger.error(f"Asterisk call originate failed: {response}")
                return {'success': False, 'call_sid': None, 'message': response}

        except Exception as e:
            self.logger.error(f"Asterisk call failed: {str(e)}")
            self._ami_disconnect(sock)
            return {'success': False, 'call_sid': None, 'message': str(e)}

    def send_sms(self, to_number, from_number, message):
        """
        Asterisk does not support SMS natively.
        This would require integration with an SMS gateway.
        For now, log and return not supported.
        """
        self.logger.warning("SMS not supported by Asterisk provider")
        return {
            'success': False,
            'sms_sid': None,
            'message': 'SMS not supported by Asterisk provider'
        }

    def is_configured(self):
        """Check if Asterisk is configured"""
        return bool(self.host and self.port and self.username and self.secret)


# Initialize provider based on configuration
callback_provider = None

if CALLBACK_PROVIDER == "asterisk":
    logger.info("Initializing Asterisk callback provider")
    callback_provider = AsteriskProvider(
        host=ASTERISK_HOST,
        port=ASTERISK_AMI_PORT,
        username=ASTERISK_AMI_USER,
        secret=ASTERISK_AMI_SECRET
    )
elif CALLBACK_PROVIDER == "twilio":
    logger.info("Initializing Twilio callback provider")
    callback_provider = TwilioProvider(
        sid=TWILIO_SID,
        auth_token=TWILIO_AUTH_TOKEN,
        twilio_number=TWILIO_NUMBER
    )
else:
    logger.error(f"Unknown callback provider: {CALLBACK_PROVIDER}")
    logger.info("Defaulting to Twilio provider")
    callback_provider = TwilioProvider(
        sid=TWILIO_SID,
        auth_token=TWILIO_AUTH_TOKEN,
        twilio_number=TWILIO_NUMBER
    )

logger.info(f"Callback provider initialized: {callback_provider.__class__.__name__}")
logger.info(f"Provider configured: {callback_provider.is_configured()}")


# Initialize Twilio client (legacy - for backward compatibility)
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


def generate_request_fingerprint(ip_address, user_agent, phone_number):
    """
    Generate unique fingerprint for spam detection.

    Combines IP, User-Agent, and phone number to detect suspicious patterns.

    Args:
        ip_address (str): Client IP address
        user_agent (str): Client User-Agent header
        phone_number (str): Submitted phone number

    Returns:
        str: SHA256 hash fingerprint
    """
    import hashlib

    fingerprint_data = f"{ip_address}|{user_agent}|{phone_number}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def check_duplicate_request(phone_number, time_window_minutes=60):
    """
    Check if phone number has recent pending/active callback request.

    Prevents spam by limiting one request per phone per time window.

    Args:
        phone_number (str): E.164 formatted phone number
        time_window_minutes (int): Time window in minutes (default: 60)

    Returns:
        tuple: (is_duplicate: bool, message: str, existing_request_id: str or None)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        # Check for recent requests from this phone number
        cursor.execute("""
            SELECT request_id, request_status, created_at
            FROM callbacks
            WHERE visitor_phone = ?
            AND created_at > ?
            AND request_status IN ('pending', 'calling', 'connected')
            ORDER BY created_at DESC
            LIMIT 1
        """, (phone_number, cutoff_time.isoformat()))

        result = cursor.fetchone()
        conn.close()

        if result:
            request_id, status, created_at = result
            logger.warning(f"Duplicate request detected for {phone_number}: existing {request_id} ({status})")
            return True, f"You already have a {status} callback request. Please wait.", request_id

        return False, "", None

    except Exception as e:
        logger.error(f"Error checking duplicate request: {str(e)}")
        # Fail open - allow request if check fails
        return False, "", None


def check_fingerprint_abuse(fingerprint, max_requests_per_day=5):
    """
    Check if request fingerprint shows abuse pattern.

    Detects if same IP+UserAgent+Phone combination is making too many requests.

    Args:
        fingerprint (str): Request fingerprint hash
        max_requests_per_day (int): Maximum requests allowed per day (default: 5)

    Returns:
        tuple: (is_abuse: bool, message: str, request_count: int)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Count requests with this fingerprint in last 24 hours
        cursor.execute("""
            SELECT COUNT(*)
            FROM callbacks
            WHERE fingerprint = ?
            AND created_at > ?
        """, (fingerprint, cutoff_time.isoformat()))

        count = cursor.fetchone()[0]
        conn.close()

        if count >= max_requests_per_day:
            logger.warning(f"Fingerprint abuse detected: {fingerprint} has {count} requests in 24h")
            return True, f"Too many requests. Please try again later.", count

        return False, "", count

    except Exception as e:
        logger.error(f"Error checking fingerprint abuse: {str(e)}")
        # Fail open - allow request if check fails
        return False, "", 0


def check_honeypot(honeypot_value):
    """
    Check honeypot field to detect bots.

    Honeypot field should be empty for legitimate users (hidden via CSS).
    Bots typically fill all fields, triggering this check.

    Args:
        honeypot_value (str): Value of honeypot field

    Returns:
        bool: True if bot detected (honeypot filled), False if legitimate
    """
    if honeypot_value and honeypot_value.strip():
        logger.warning(f"Honeypot triggered: bot detected (value: {honeypot_value[:50]})")
        return True
    return False


def check_daily_limits():
    """
    Check if daily call/SMS limits have been reached.

    Prevents runaway costs from spam or misconfiguration.

    Returns:
        tuple: (within_limits: bool, message: str, stats: dict)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Count calls in last 24 hours
        cursor.execute("""
            SELECT COUNT(*)
            FROM callbacks
            WHERE created_at > ?
            AND request_status IN ('calling', 'connected', 'completed')
        """, (cutoff_time.isoformat(),))

        calls_24h = cursor.fetchone()[0]

        # Count SMS in last 24 hours (approximate - based on status)
        cursor.execute("""
            SELECT COUNT(*)
            FROM callbacks
            WHERE created_at > ?
            AND sms_sid IS NOT NULL
        """, (cutoff_time.isoformat(),))

        sms_24h = cursor.fetchone()[0]

        conn.close()

        stats = {
            'calls_24h': calls_24h,
            'sms_24h': sms_24h,
            'max_calls': MAX_CALLS_PER_DAY,
            'max_sms': MAX_SMS_PER_DAY
        }

        # Check limits
        if calls_24h >= MAX_CALLS_PER_DAY:
            logger.error(f"Daily call limit reached: {calls_24h}/{MAX_CALLS_PER_DAY}")
            return False, f"Daily call limit reached. Please try again tomorrow.", stats

        if sms_24h >= MAX_SMS_PER_DAY:
            logger.error(f"Daily SMS limit reached: {sms_24h}/{MAX_SMS_PER_DAY}")
            return False, f"Daily SMS limit reached. Please try again tomorrow.", stats

        # Warn at 80% threshold
        if calls_24h >= MAX_CALLS_PER_DAY * 0.8:
            logger.warning(f"Approaching daily call limit: {calls_24h}/{MAX_CALLS_PER_DAY}")

        if sms_24h >= MAX_SMS_PER_DAY * 0.8:
            logger.warning(f"Approaching daily SMS limit: {sms_24h}/{MAX_SMS_PER_DAY}")

        return True, "", stats

    except Exception as e:
        logger.error(f"Error checking daily limits: {str(e)}")
        # Fail open - allow request if check fails
        return True, "", {}


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

    Sanitizes input by removing common formatting characters and defaults to US region
    if no country code is provided.

    Args:
        number (str): Phone number to validate (e.g., "(321) 704-7403", "321-704-7403", "+13217047403")

    Returns:
        tuple: (is_valid: bool, result: str) where result is formatted number or error message
    """
    try:
        # Sanitize input: remove common formatting characters
        sanitized = number.strip()
        # Remove parentheses, spaces, dashes, dots
        sanitized = sanitized.replace('(', '').replace(')', '').replace(' ', '').replace('-', '').replace('.', '')

        # If number doesn't start with +, assume US and prepend +1
        if not sanitized.startswith('+'):
            # If it's 10 digits, it's likely a US number without country code
            if len(sanitized) == 10 and sanitized.isdigit():
                sanitized = '+1' + sanitized
            # If it's 11 digits starting with 1, add the +
            elif len(sanitized) == 11 and sanitized.startswith('1') and sanitized.isdigit():
                sanitized = '+' + sanitized

        # Parse with US as default region
        parsed = phonenumbers.parse(sanitized, "US")
        if not phonenumbers.is_valid_number(parsed):
            return False, "Invalid phone number"
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        logger.debug(f"Phone number validated: {number} -> {sanitized} -> {formatted}")
        return True, formatted
    except phonenumbers.NumberParseException as e:
        logger.warning(f"Phone number parse error: {number} - {str(e)}")
        return False, f"Invalid phone number format: {str(e)}"


def migrate_database():
    """
    Migrate existing database to add new security columns.

    Adds ip_address, user_agent, and fingerprint columns if they don't exist.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if migration is needed
        cursor.execute("PRAGMA table_info(callbacks)")
        columns = [row[1] for row in cursor.fetchall()]

        needs_migration = False

        # Add ip_address column if missing
        if 'ip_address' not in columns:
            logger.info("Adding ip_address column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN ip_address TEXT")
            needs_migration = True

        # Add user_agent column if missing
        if 'user_agent' not in columns:
            logger.info("Adding user_agent column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN user_agent TEXT")
            needs_migration = True

        # Add fingerprint column if missing
        if 'fingerprint' not in columns:
            logger.info("Adding fingerprint column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN fingerprint TEXT")
            needs_migration = True

        if needs_migration:
            # Create indexes for new columns
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_callbacks_fingerprint
                    ON callbacks(fingerprint)
                """)
                logger.info("Created fingerprint index")
            except Exception as e:
                logger.warning(f"Could not create fingerprint index: {e}")

            conn.commit()
            logger.info("Database migration completed successfully")
        else:
            logger.info("Database schema is up to date")

        conn.close()

    except Exception as e:
        logger.error(f"Database migration failed: {str(e)}")
        raise


def init_database():
    """Initialize SQLite database with proper schema per Rule 11."""
    logger.info(f"Initializing database at {DATABASE_PATH}")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create callbacks table - avoid SQL reserved keywords per Rule 11
    # Note: New installs get all columns, existing DBs get migrated separately
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
            sms_sid TEXT,
            ip_address TEXT,
            user_agent TEXT,
            fingerprint TEXT
        )
    """)

    # Create index on phone number for duplicate detection
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_callbacks_phone
        ON callbacks(visitor_phone)
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


# Initialize database on startup (creates tables if they don't exist)
init_database()

# Run database migration AFTER init to add new columns to existing tables
try:
    migrate_database()
except Exception as e:
    logger.error(f"Migration failed, but continuing: {e}")


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "provider": callback_provider.__class__.__name__ if callback_provider else "None",
        "provider_configured": callback_provider.is_configured() if callback_provider else False,
        "twilio_configured": twilio_client is not None  # Legacy compatibility
    })


@app.route("/api/configure", methods=["POST"])
def configure_twilio():
    """
    Save Twilio configuration to .env file.
    This endpoint is called by the setup wizard.
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['TWILIO_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_NUMBER', 'BUSINESS_NUMBER']
        for field in required_fields:
            if not data.get(field):
                return jsonify(success=False, error=f"Missing required field: {field}"), 400

        # Validate Account SID format
        if not data['TWILIO_SID'].startswith('AC') or len(data['TWILIO_SID']) != 34:
            return jsonify(success=False, error="Invalid Account SID format"), 400

        # Validate phone number formats
        for field in ['TWILIO_NUMBER', 'BUSINESS_NUMBER']:
            if not data[field].startswith('+'):
                return jsonify(success=False, error=f"{field} must include country code (e.g., +15551234567)"), 400

        # Build .env content
        env_content = f"""# Callback Service Environment Configuration
# Generated by Twilio Setup Wizard on {datetime.utcnow().isoformat()}

# ============================================================
# TWILIO CONFIGURATION
# ============================================================
TWILIO_SID={data['TWILIO_SID']}
TWILIO_AUTH_TOKEN={data['TWILIO_AUTH_TOKEN']}
TWILIO_NUMBER={data['TWILIO_NUMBER']}

# ============================================================
# BUSINESS CONFIGURATION
# ============================================================
BUSINESS_NUMBER={data['BUSINESS_NUMBER']}

# ============================================================
# FRONTEND CONFIGURATION
# ============================================================
FRONTEND_URL={data.get('FRONTEND_URL', 'http://localhost:3000')}
ALLOWED_ORIGINS={data.get('FRONTEND_URL', 'http://localhost:3000')}

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
DATABASE_PATH=/tmp/callbacks.db

# ============================================================
# RECAPTCHA CONFIGURATION
# ============================================================
RECAPTCHA_SECRET={data.get('RECAPTCHA_SECRET', '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe')}

# ============================================================
# BUSINESS HOURS CONFIGURATION
# ============================================================
BUSINESS_HOURS_START=09:00
BUSINESS_HOURS_END=17:00
BUSINESS_TIMEZONE=America/New_York
BUSINESS_WEEKDAYS_ONLY=true
"""

        # Determine .env file path
        # Try to write to project root (one level up from backend/)
        import pathlib
        backend_dir = pathlib.Path(__file__).parent
        project_root = backend_dir.parent
        env_path = project_root / '.env'

        # Write .env file
        with open(env_path, 'w') as f:
            f.write(env_content)

        logger.info(f"Twilio configuration saved to {env_path}")
        logger.info(f"Account SID: {data['TWILIO_SID']}")
        logger.info(f"Twilio Number: {data['TWILIO_NUMBER']}")
        logger.info(f"Business Number: {data['BUSINESS_NUMBER']}")

        return jsonify({
            "success": True,
            "message": "Configuration saved successfully",
            "env_path": str(env_path),
            "restart_required": True
        })

    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        return jsonify(success=False, error=str(e)), 500


@app.route("/oauth/login/<provider>", methods=["GET"])
def oauth_login(provider):
    """
    Initiate OAuth login flow for specified provider.
    Redirects to the OAuth provider's authorization page.
    """
    logger.info(f"🔐 OAuth login initiated for provider: {provider}")
    log_audit_event(None, "oauth_login_initiated", {"provider": provider})

    if provider == "google":
        if not GOOGLE_CLIENT_ID:
            logger.error("❌ Google OAuth not configured - missing GOOGLE_CLIENT_ID")
            return redirect(f"{FRONTEND_URL}?error=oauth_not_configured")

        # Determine redirect URI based on request origin
        if request.host.startswith("localhost"):
            redirect_uri = "http://localhost:8501/oauth/callback/google"
        else:
            redirect_uri = "https://api.swipswaps.com/oauth/callback/google"

        # Build Google OAuth authorization URL
        from urllib.parse import urlencode
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        logger.info(f"✅ Redirecting to Google OAuth: {auth_url}")
        return redirect(auth_url)

    elif provider == "facebook":
        if not FACEBOOK_APP_ID:
            logger.error("❌ Facebook OAuth not configured - missing FACEBOOK_APP_ID")
            return redirect(f"{FRONTEND_URL}?error=oauth_not_configured")

        # Determine redirect URI based on request origin
        if request.host.startswith("localhost"):
            redirect_uri = "http://localhost:8501/oauth/callback/facebook"
        else:
            redirect_uri = "https://api.swipswaps.com/oauth/callback/facebook"

        # Build Facebook OAuth authorization URL
        from urllib.parse import urlencode
        params = {
            "client_id": FACEBOOK_APP_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email public_profile"
        }
        auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
        logger.info(f"✅ Redirecting to Facebook OAuth: {auth_url}")
        return redirect(auth_url)

    else:
        logger.error(f"❌ Unsupported OAuth provider: {provider}")
        return redirect(f"{FRONTEND_URL}?error=unsupported_provider")


@app.route("/oauth/callback/<provider>", methods=["GET"])
def oauth_callback(provider):
    """
    Handle OAuth callback and fetch user information.
    Exchanges authorization code for access token and fetches user data.
    """
    logger.info(f"🔄 OAuth callback received for provider: {provider}")

    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        logger.error(f"❌ OAuth error from {provider}: {error}")
        return redirect(f"{FRONTEND_URL}?error=oauth_failed")

    if not code:
        logger.error(f"❌ No authorization code received in OAuth callback for {provider}")
        return redirect(f"{FRONTEND_URL}?error=oauth_failed")

    if provider == "google":
        try:
            # Determine redirect URI (must match what was sent to Google)
            if request.host.startswith("localhost"):
                redirect_uri = "http://localhost:8501/oauth/callback/google"
            else:
                redirect_uri = "https://api.swipswaps.com/oauth/callback/google"

            # Exchange authorization code for access token
            logger.info(f"🔐 Exchanging authorization code for access token")
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }

            token_response = requests.post(token_url, data=token_data, timeout=15)

            if token_response.status_code != 200:
                logger.error(f"❌ Token exchange failed: {token_response.status_code} - {token_response.text}")
                return redirect(f"{FRONTEND_URL}?error=oauth_failed")

            token_json = token_response.json()
            access_token = token_json.get("access_token")

            if not access_token:
                logger.error(f"❌ No access token in response")
                return redirect(f"{FRONTEND_URL}?error=oauth_failed")

            logger.info(f"✅ Access token obtained successfully")

            # Fetch user info using access token
            user_info = get_user_info(provider, access_token)

            if not user_info:
                logger.error(f"❌ Failed to fetch user info from {provider}")
                return redirect(f"{FRONTEND_URL}?error=oauth_failed")

            # Encode user info and redirect to frontend
            encoded_user = base64.b64encode(json.dumps(user_info).encode()).decode()
            logger.info(f"✅ OAuth successful for {provider}, redirecting to frontend")
            logger.info(f"📤 User: {user_info.get('name')} <{user_info.get('email')}>")

            log_audit_event(None, "oauth_completed", {
                "provider": provider,
                "has_email": bool(user_info.get("email"))
            })

            return redirect(f"{FRONTEND_URL}?user={encoded_user}")

        except Exception as e:
            logger.error(f"❌ OAuth callback error: {str(e)}")
            return redirect(f"{FRONTEND_URL}?error=oauth_failed")

    elif provider == "facebook":
        try:
            # Determine redirect URI (must match what was sent to Facebook)
            if request.host.startswith("localhost"):
                redirect_uri = "http://localhost:8501/oauth/callback/facebook"
            else:
                redirect_uri = "https://api.swipswaps.com/oauth/callback/facebook"

            # Exchange authorization code for access token
            logger.info(f"🔐 Exchanging authorization code for access token")
            token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
            token_params = {
                "code": code,
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "redirect_uri": redirect_uri
            }

            token_response = requests.get(token_url, params=token_params, timeout=15)

            if token_response.status_code != 200:
                logger.error(f"❌ Token exchange failed: {token_response.status_code} - {token_response.text}")
                return redirect(f"{FRONTEND_URL}?error=oauth_failed")

            token_json = token_response.json()
            access_token = token_json.get("access_token")

            if not access_token:
                logger.error(f"❌ No access token in response")
                return redirect(f"{FRONTEND_URL}?error=oauth_failed")

            logger.info(f"✅ Access token obtained successfully")

            # Fetch user info using access token
            user_info = get_user_info(provider, access_token)

            if not user_info:
                logger.error(f"❌ Failed to fetch user info from {provider}")
                return redirect(f"{FRONTEND_URL}?error=oauth_failed")

            # Encode user info and redirect to frontend
            encoded_user = base64.b64encode(json.dumps(user_info).encode()).decode()
            logger.info(f"✅ OAuth successful for {provider}, redirecting to frontend")
            logger.info(f"📤 User: {user_info.get('name')} <{user_info.get('email')}>")

            log_audit_event(None, "oauth_completed", {
                "provider": provider,
                "has_email": bool(user_info.get("email"))
            })

            return redirect(f"{FRONTEND_URL}?user={encoded_user}")

        except Exception as e:
            logger.error(f"❌ OAuth callback error: {str(e)}")
            return redirect(f"{FRONTEND_URL}?error=oauth_failed")

    else:
        logger.error(f"❌ Unsupported OAuth provider: {provider}")
        return redirect(f"{FRONTEND_URL}?error=unsupported_provider")


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

        # SECURITY LAYER 1: Honeypot check (bot detection)
        honeypot = data.get("website", "").strip()  # Hidden field - should be empty
        if check_honeypot(honeypot):
            log_audit_event(None, "honeypot_triggered", {
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'Unknown'),
                "honeypot_value": honeypot[:100]
            })
            # Return success to bot (don't reveal detection)
            return jsonify(success=True, message="Request received"), 200

        # SECURITY LAYER 2: Verify reCAPTCHA token
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

        # SECURITY LAYER 3: Check daily cost limits
        within_limits, limit_message, limit_stats = check_daily_limits()
        if not within_limits:
            log_audit_event(None, "daily_limit_reached", {
                "remote_addr": request.remote_addr,
                "stats": limit_stats
            })
            return jsonify(success=False, error=limit_message), 503  # 503 Service Unavailable

        # SECURITY LAYER 4: Check for duplicate requests (same phone number)
        is_duplicate, dup_message, existing_id = check_duplicate_request(visitor_phone, time_window_minutes=60)
        if is_duplicate:
            log_audit_event(existing_id, "duplicate_request_blocked", {
                "remote_addr": request.remote_addr,
                "visitor_phone": visitor_phone
            })
            return jsonify(success=False, error=dup_message), 429  # 429 Too Many Requests

        # SECURITY LAYER 5: Generate and check request fingerprint
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        fingerprint = generate_request_fingerprint(ip_address, user_agent, visitor_phone)

        is_abuse, abuse_message, abuse_count = check_fingerprint_abuse(fingerprint, max_requests_per_day=5)
        if is_abuse:
            log_audit_event(None, "fingerprint_abuse_blocked", {
                "remote_addr": ip_address,
                "user_agent": user_agent,
                "fingerprint": fingerprint,
                "count_24h": abuse_count
            })
            return jsonify(success=False, error=abuse_message), 429  # 429 Too Many Requests

        visitor_name = data.get("name", "").strip()
        visitor_email = data.get("email", "").strip()

        # Generate unique request ID
        request_id = str(uuid.uuid4())

        logger.info(f"Callback request received: {request_id} from {visitor_phone} (fingerprint: {fingerprint[:16]}...)")

        # Store in database with security metadata
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO callbacks (
                request_id, visitor_name, visitor_email, visitor_phone,
                request_status, created_at, updated_at,
                ip_address, user_agent, fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            visitor_name,
            visitor_email,
            visitor_phone,
            "pending",
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            ip_address,
            user_agent,
            fingerprint
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

        # Initiate callback via configured provider
        if callback_provider and callback_provider.is_configured() and BUSINESS_NUMBER:
            # Determine from_number based on provider
            if isinstance(callback_provider, TwilioProvider):
                from_number = TWILIO_NUMBER
            elif isinstance(callback_provider, AsteriskProvider):
                from_number = visitor_phone  # Asterisk uses visitor number as caller ID
            else:
                from_number = BUSINESS_NUMBER

            # If outside business hours, send SMS instead of calling (Twilio only)
            if not is_open:
                logger.info(f"Outside business hours for request {request_id} - sending SMS only")

                if isinstance(callback_provider, TwilioProvider):
                    try:
                        sms_result = callback_provider.send_sms(
                            to_number=BUSINESS_NUMBER,
                            from_number=from_number,
                            message=f"Callback request from {visitor_name or 'visitor'} at {visitor_phone}. Received outside business hours. Please call back during business hours."
                        )

                        if sms_result['success']:
                            update_callback_status(request_id, "sms_sent", f"SMS sent ({hours_message})", sms_sid=sms_result['sms_sid'])
                            logger.info(f"SMS sent for outside-hours request: {sms_result['sms_sid']}")
                            log_audit_event(request_id, "sms_sent_outside_hours", {"sms_sid": sms_result['sms_sid']})

                            return jsonify(
                                success=True,
                                request_id=request_id,
                                message=f"Request received. {hours_message}. We'll call you back during business hours."
                            ), 200
                        else:
                            raise Exception(sms_result['message'])

                    except Exception as sms_error:
                        logger.error(f"Failed to send outside-hours SMS: {str(sms_error)}")
                        update_callback_status(request_id, "failed", f"SMS failed: {str(sms_error)}")
                        return jsonify(
                            success=False,
                            error="Failed to process request. Please try again later."
                        ), 500
                else:
                    # Non-Twilio providers: store request for manual follow-up
                    update_callback_status(request_id, "pending", f"Outside business hours ({hours_message})")
                    return jsonify(
                        success=True,
                        request_id=request_id,
                        message=f"Request received. {hours_message}. We'll call you back during business hours."
                    ), 200

            try:
                # Call business first (within business hours)
                logger.info(f"Initiating callback via {callback_provider.__class__.__name__} for request {request_id} ({hours_message})")

                call_result = callback_provider.make_call(
                    to_number=BUSINESS_NUMBER,
                    from_number=from_number,
                    request_id=request_id
                )

                if call_result['success']:
                    update_callback_status(request_id, "calling", "Calling business", call_sid=call_result['call_sid'])
                    logger.info(f"Call initiated via {callback_provider.__class__.__name__}: {call_result['call_sid']}")
                else:
                    raise Exception(call_result['message'])

            except Exception as e:
                logger.error(f"Callback failed: {str(e)}")
                update_callback_status(request_id, "failed", f"Call failed: {str(e)}")

                # Send SMS fallback to business (Twilio only)
                if isinstance(callback_provider, TwilioProvider):
                    try:
                        sms_result = callback_provider.send_sms(
                            to_number=BUSINESS_NUMBER,
                            from_number=from_number,
                            message=f"Missed callback request from {visitor_name or 'visitor'} at {visitor_phone}. Please call them back."
                        )

                        if sms_result['success']:
                            update_callback_status(request_id, "sms_sent", "SMS sent to business", sms_sid=sms_result['sms_sid'])
                            logger.info(f"SMS fallback sent: {sms_result['sms_sid']}")
                    except Exception as sms_error:
                        logger.error(f"SMS fallback failed: {str(sms_error)}")
        else:
            logger.warning("Callback provider not configured - callback request stored but not processed")
            update_callback_status(request_id, "pending", "Provider not configured")

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


