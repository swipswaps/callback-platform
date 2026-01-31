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
- Graceful shutdown handling (SIGINT/SIGTERM)
- Structured exit codes for automation
"""

import os
import sys
import json
import base64
import sqlite3
import logging
import uuid
import requests
import secrets
import time
import signal
import atexit
from enum import Enum
from datetime import datetime, timedelta
from flask import Flask, request, redirect, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from oauth_providers import get_user_info
import phonenumbers
import pytz
from datetime import time as dt_time
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from requests.exceptions import ConnectionError, Timeout
from urllib3.exceptions import NameResolutionError

# Structured exit codes for automation
class ExitCode(int, Enum):
    SUCCESS = 0
    USER_ERROR = 1
    CONFIG_ERROR = 2
    RUNTIME_ERROR = 3
    INTERRUPTED = 130  # Ctrl-C / SIGINT

# Application state tracking for crash reporting
class AppState(str, Enum):
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"

current_state = AppState.STARTING
last_action = "initializing"

def set_state(state: AppState):
    """Set application state with logging"""
    global current_state
    current_state = state
    if VERBOSE:
        logger.info(f"STATE → {state.value}")

def set_action(action: str):
    """Track last action for crash reporting"""
    global last_action
    last_action = action
    if VERBOSE:
        logger.debug(f"ACTION → {action}")

def assert_state(expected_state: AppState, action_description: str):
    """
    Assert that the application is in the expected state.
    Raises ValueError if state is invalid.
    This enforces the finite-state machine model.

    Args:
        expected_state: The required state
        action_description: Human-readable description of the action being attempted

    Raises:
        ValueError: If current state doesn't match expected state
    """
    if current_state != expected_state:
        error_msg = f"Cannot {action_description}: Invalid state. Expected {expected_state.value}, but current state is {current_state.value}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def error_response(error_message: str, status_code: int = 500, include_context: bool = True):
    """
    Create a standardized error response with optional context.
    Includes last_action for user-visible failure context.

    Args:
        error_message: The error message to display
        status_code: HTTP status code
        include_context: Whether to include last_action context

    Returns:
        tuple: (jsonify response, status_code)
    """
    response_data = {
        "success": False,
        "error": error_message
    }

    if include_context and last_action:
        # Make last_action human-readable
        action_phrases = {
            "initializing": "starting up",
            "detecting backend": "connecting to server",
            "requesting callback": "submitting your request",
            "verifying code": "verifying your code",
            "initiating callback": "starting your call"
        }
        human_action = action_phrases.get(last_action, last_action)
        response_data["context"] = f"Error occurred while {human_action}"
        response_data["next_step"] = "Please try again or contact support if the problem persists"

    return jsonify(response_data), status_code

# Configure comprehensive logging per Rule 25
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Support --verbose and --quiet flags
VERBOSE = "--verbose" in sys.argv
QUIET = "--quiet" in sys.argv

logger = logging.getLogger(__name__)

# Set log level based on flags
if QUIET:
    logger.setLevel(logging.WARNING)
elif VERBOSE:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if VERBOSE else logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler("/tmp/app.log", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(file_handler)

# Graceful shutdown handling (will be registered at end of file)
shutdown_requested = False

# Priority levels for queue prioritization
PRIORITY_HIGH = 'high'
PRIORITY_DEFAULT = 'default'
PRIORITY_LOW = 'low'

# Priority order mapping (lower number = higher priority)
PRIORITY_ORDER = {
    PRIORITY_HIGH: 1,
    PRIORITY_DEFAULT: 2,
    PRIORITY_LOW: 3
}

# Initialize Flask app
app = Flask(__name__)

# Trust X-Forwarded-* headers from Cloudflare Tunnel proxy
# This fixes Twilio signature validation when behind reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

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

# Prometheus metrics collectors
# Track callback requests by status
callback_requests_total = Counter(
    'callback_requests_total',
    'Total callback requests',
    ['status']
)

# Track currently active requests by status
callback_requests_active = Gauge(
    'callback_requests_active',
    'Currently active callback requests',
    ['status']
)

# Track callback duration
callback_duration_seconds = Histogram(
    'callback_duration_seconds',
    'Callback request duration in seconds',
    ['status']
)

# Track Twilio calls
twilio_calls_total = Counter(
    'twilio_calls_total',
    'Total Twilio calls initiated',
    ['status']
)

# Track Twilio SMS
twilio_sms_total = Counter(
    'twilio_sms_total',
    'Total Twilio SMS sent',
    ['type']
)

# Track verification codes
verification_codes_sent = Counter(
    'verification_codes_sent_total',
    'Total verification codes sent',
    ['channel']
)

# Track verification attempts
verification_attempts_total = Counter(
    'verification_attempts_total',
    'Total verification attempts',
    ['result']
)

# Track callback requests by priority
callback_requests_by_priority = Counter(
    'callback_requests_by_priority_total',
    'Total callback requests by priority level',
    ['priority']
)

# Track escalations
escalations_total = Counter(
    'escalations_total',
    'Total number of escalations',
    ['level']
)

escalation_success_total = Counter(
    'escalation_success_total',
    'Total successful escalations',
    ['level']
)

escalation_failures_total = Counter(
    'escalation_failures_total',
    'Total failed escalations',
    ['level']
)

# Track concurrency
concurrent_calls_gauge = Gauge(
    'concurrent_calls',
    'Current number of concurrent calls in progress'
)

concurrent_sms_gauge = Gauge(
    'concurrent_sms',
    'Current number of concurrent SMS sends in progress'
)

concurrency_limit_hits_total = Counter(
    'concurrency_limit_hits_total',
    'Total times concurrency limit was hit',
    ['type', 'action']  # type: calls/sms, action: queue/reject/delay
)

# Track commit mode transactions
commit_mode_transactions_total = Counter(
    'commit_mode_transactions_total',
    'Total transactions by commit mode',
    ['mode', 'operation']  # mode: on_db_commit/auto/request_finished, operation: verification/callback
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

# Escalation policy configuration
ESCALATION_ENABLED = os.environ.get("ESCALATION_ENABLED", "false").lower() == "true"
ESCALATION_TIMEOUT_MINUTES = int(os.environ.get("ESCALATION_TIMEOUT_MINUTES", "5"))  # Escalate after 5 minutes of no answer
ESCALATION_CHAIN = os.environ.get("ESCALATION_CHAIN", "")  # Comma-separated backup numbers: +1234567890,+0987654321
ESCALATION_MAX_LEVEL = int(os.environ.get("ESCALATION_MAX_LEVEL", "2"))  # Max escalation levels (0=primary, 1=first backup, 2=second backup)

# Concurrency control configuration
MAX_CONCURRENT_CALLS = int(os.environ.get("MAX_CONCURRENT_CALLS", "3"))  # Max simultaneous calls to business
MAX_CONCURRENT_SMS = int(os.environ.get("MAX_CONCURRENT_SMS", "10"))  # Max simultaneous SMS sends
CONCURRENCY_OVERFLOW_ACTION = os.environ.get("CONCURRENCY_OVERFLOW_ACTION", "queue")  # queue, reject, or delay

# Commit mode configuration (transactional integrity)
# on_db_commit: Ensure callback is only initiated after verification is committed to DB (default, safest)
# auto: Initiate callback immediately after verification (faster, but potential race condition)
# request_finished: Initiate callback after HTTP request completes (for async processing)
COMMIT_MODE = os.environ.get("COMMIT_MODE", "on_db_commit")  # on_db_commit, auto, or request_finished

# Cost protection limits
MAX_CALLS_PER_DAY = int(os.environ.get("MAX_CALLS_PER_DAY", "100"))
MAX_SMS_PER_DAY = int(os.environ.get("MAX_SMS_PER_DAY", "200"))
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")  # Email for cost alerts

# Admin dashboard authentication
ADMIN_API_TOKEN = os.environ.get("ADMIN_API_TOKEN", "")  # Bearer token for admin endpoints

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
        """Initiate Twilio call to business number with self-healing retry logic"""
        if not self.client:
            self.logger.error("Twilio client not initialized")
            return {'success': False, 'call_sid': None, 'message': 'Twilio not configured'}

        try:
            self.logger.info(f"Initiating Twilio call for request {request_id}: {from_number} -> {to_number}")

            # Wrap Twilio API call with exponential backoff retry
            call = retry_with_exponential_backoff(
                lambda: self.client.calls.create(
                    to=to_number,
                    from_=from_number,
                    url=f"http://twimlets.com/holdmusic?Bucket=com.twilio.music.classical",
                    status_callback=f"https://api.swipswaps.com/twilio/status_callback?request_id={request_id}",
                    status_callback_event=["completed", "no-answer", "busy", "failed"],
                    timeout=20
                ),
                max_retries=3,
                base_delay=1,
                max_delay=5
            )

            self.logger.info(f"Twilio call initiated successfully: {call.sid}")
            return {'success': True, 'call_sid': call.sid, 'message': 'Call initiated'}

        except (TwilioRestException, ConnectionError, Timeout, NameResolutionError) as e:
            self.logger.error(f"Twilio call failed after retries: {str(e)}")
            return {'success': False, 'call_sid': None, 'message': f"Call failed after retries: {str(e)}"}

    def send_sms(self, to_number, from_number, message):
        """Send SMS via Twilio with self-healing retry logic"""
        if not self.client:
            self.logger.error("Twilio client not initialized")
            return {'success': False, 'sms_sid': None, 'message': 'Twilio not configured'}

        try:
            self.logger.info(f"Sending Twilio SMS: {from_number} -> {to_number}")

            # Wrap Twilio API call with exponential backoff retry
            msg = retry_with_exponential_backoff(
                lambda: self.client.messages.create(
                    to=to_number,
                    from_=from_number,
                    body=message
                ),
                max_retries=3,
                base_delay=1,
                max_delay=5
            )

            self.logger.info(f"Twilio SMS sent successfully: {msg.sid}")
            return {'success': True, 'sms_sid': msg.sid, 'message': 'SMS sent'}

        except (TwilioRestException, ConnectionError, Timeout, NameResolutionError) as e:
            self.logger.error(f"Twilio SMS failed after retries: {str(e)}")
            return {'success': False, 'sms_sid': None, 'message': f"SMS failed after retries: {str(e)}"}

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


def cleanup_stuck_requests(timeout_minutes=5):
    """
    Auto-cleanup requests stuck in 'calling' status.

    If a request is in 'calling' status for more than timeout_minutes,
    mark it as 'failed' (likely Twilio callback was rejected/lost).

    Args:
        timeout_minutes (int): Minutes before marking stuck request as failed
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        cursor.execute("""
            UPDATE callbacks
            SET request_status = 'failed',
                status_message = 'Auto-cleared: stuck in calling status',
                updated_at = ?
            WHERE request_status = 'calling'
            AND created_at < ?
        """, (datetime.utcnow().isoformat(), cutoff_time.isoformat()))

        cleared_count = cursor.rowcount
        conn.commit()
        conn.close()

        if cleared_count > 0:
            logger.info(f"Auto-cleanup: cleared {cleared_count} stuck request(s)")

        return cleared_count

    except Exception as e:
        logger.error(f"Error in auto-cleanup: {str(e)}")
        return 0


def check_duplicate_request(phone_number, time_window_minutes=60):
    """
    Check if phone number has recent pending/active callback request.

    Prevents spam by limiting one request per phone per time window.

    Args:
        phone_number (str): E.164 formatted phone number
        time_window_minutes (int): Time window in minutes (default: 60)

    Returns:
        tuple: (is_duplicate: bool, message: str, existing_request_id: str or None, remaining_minutes: float)
    """
    try:
        # Auto-cleanup stuck requests before checking duplicates
        cleanup_stuck_requests(timeout_minutes=5)

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        # Check for recent requests from this phone number (exclude cancelled)
        cursor.execute("""
            SELECT request_id, request_status, created_at
            FROM callbacks
            WHERE visitor_phone = ?
            AND created_at > ?
            AND request_status IN ('pending', 'calling', 'connected', 'verified')
            ORDER BY created_at DESC
            LIMIT 1
        """, (phone_number, cutoff_time.isoformat()))

        result = cursor.fetchone()
        conn.close()

        if result:
            request_id, status, created_at_str = result
            logger.warning(f"Duplicate request detected for {phone_number}: existing {request_id} ({status})")

            # Calculate time remaining until user can retry
            created_at = datetime.fromisoformat(created_at_str)
            elapsed_minutes = (datetime.utcnow() - created_at).total_seconds() / 60
            remaining_minutes = max(0, time_window_minutes - elapsed_minutes)

            return True, f"You already have a {status} callback request. Please wait.", request_id, remaining_minutes

        return False, "", None, 0

    except Exception as e:
        logger.error(f"Error checking duplicate request: {str(e)}")
        # Fail open - allow request if check fails
        return False, "", None


def check_fingerprint_abuse(fingerprint, max_requests_per_day=20):
    """
    Check if request fingerprint shows abuse pattern.

    Detects if same IP+UserAgent+Phone combination is making too many requests.

    Args:
        fingerprint (str): Request fingerprint hash
        max_requests_per_day (int): Maximum requests allowed per day (default: 20, increased for testing)

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


def get_concurrent_calls_count():
    """
    Get current number of concurrent calls in progress.

    Returns:
        int: Number of requests currently in 'calling' or 'connected' status
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM callbacks
            WHERE request_status IN ('calling', 'connected')
        """)

        count = cursor.fetchone()[0]
        conn.close()

        # Update Prometheus gauge
        concurrent_calls_gauge.set(count)

        return count

    except Exception as e:
        logger.error(f"Error getting concurrent calls count: {str(e)}")
        return 0


def get_concurrent_sms_count():
    """
    Get current number of concurrent SMS sends in progress.

    Returns:
        int: Number of requests currently sending SMS (verified status within last 5 minutes)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Count recent SMS sends (within last 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)

        cursor.execute("""
            SELECT COUNT(*)
            FROM callbacks
            WHERE request_status = 'verified'
            AND updated_at > ?
        """, (cutoff_time.isoformat(),))

        count = cursor.fetchone()[0]
        conn.close()

        # Update Prometheus gauge
        concurrent_sms_gauge.set(count)

        return count

    except Exception as e:
        logger.error(f"Error getting concurrent SMS count: {str(e)}")
        return 0


def check_concurrency_limit(operation_type):
    """
    Check if concurrency limit is reached for given operation type.

    Args:
        operation_type (str): 'call' or 'sms'

    Returns:
        tuple: (can_proceed: bool, message: str, current_count: int, max_limit: int)
    """
    try:
        if operation_type == 'call':
            current_count = get_concurrent_calls_count()
            max_limit = MAX_CONCURRENT_CALLS

            if current_count >= max_limit:
                logger.warning(f"Concurrent call limit reached: {current_count}/{max_limit}")
                concurrency_limit_hits_total.labels(type='calls', action=CONCURRENCY_OVERFLOW_ACTION).inc()

                if CONCURRENCY_OVERFLOW_ACTION == 'reject':
                    return False, f"System is at capacity ({current_count} concurrent calls). Please try again later.", current_count, max_limit
                elif CONCURRENCY_OVERFLOW_ACTION == 'queue':
                    return True, f"Request queued due to high call volume ({current_count}/{max_limit} concurrent calls).", current_count, max_limit
                elif CONCURRENCY_OVERFLOW_ACTION == 'delay':
                    return True, f"Request will be delayed due to high call volume ({current_count}/{max_limit} concurrent calls).", current_count, max_limit

        elif operation_type == 'sms':
            current_count = get_concurrent_sms_count()
            max_limit = MAX_CONCURRENT_SMS

            if current_count >= max_limit:
                logger.warning(f"Concurrent SMS limit reached: {current_count}/{max_limit}")
                concurrency_limit_hits_total.labels(type='sms', action=CONCURRENCY_OVERFLOW_ACTION).inc()

                if CONCURRENCY_OVERFLOW_ACTION == 'reject':
                    return False, f"System is at capacity ({current_count} concurrent SMS). Please try again later.", current_count, max_limit
                elif CONCURRENCY_OVERFLOW_ACTION == 'queue':
                    return True, f"Request queued due to high SMS volume ({current_count}/{max_limit} concurrent SMS).", current_count, max_limit
                elif CONCURRENCY_OVERFLOW_ACTION == 'delay':
                    return True, f"Request will be delayed due to high SMS volume ({current_count}/{max_limit} concurrent SMS).", current_count, max_limit

        return True, "", current_count if operation_type in ['call', 'sms'] else 0, max_limit if operation_type in ['call', 'sms'] else 0

    except Exception as e:
        logger.error(f"Error checking concurrency limit: {str(e)}")
        # Fail open - allow request if check fails
        return True, "", 0, 0


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

        # Add retry columns if missing
        if 'retry_count' not in columns:
            logger.info("Adding retry_count column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN retry_count INTEGER DEFAULT 0")
            needs_migration = True

        if 'max_retries' not in columns:
            logger.info("Adding max_retries column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN max_retries INTEGER DEFAULT 3")
            needs_migration = True

        if 'retry_at' not in columns:
            logger.info("Adding retry_at column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN retry_at TEXT")
            needs_migration = True

        if 'last_retry_at' not in columns:
            logger.info("Adding last_retry_at column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN last_retry_at TEXT")
            needs_migration = True

        # Add priority column if missing
        if 'priority' not in columns:
            logger.info("Adding priority column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN priority TEXT DEFAULT 'default'")
            needs_migration = True

        # Add escalation columns if missing
        if 'escalation_level' not in columns:
            logger.info("Adding escalation_level column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN escalation_level INTEGER DEFAULT 0")
            needs_migration = True

        if 'escalation_at' not in columns:
            logger.info("Adding escalation_at column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN escalation_at TEXT")
            needs_migration = True

        if 'escalated_to' not in columns:
            logger.info("Adding escalated_to column to callbacks table")
            cursor.execute("ALTER TABLE callbacks ADD COLUMN escalated_to TEXT")
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

            # Create index on retry_at for efficient retry job queries
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_callbacks_retry_at
                    ON callbacks(retry_at)
                """)
                logger.info("Created retry_at index")
            except Exception as e:
                logger.warning(f"Could not create retry_at index: {e}")

            # Create index on priority and retry_at for efficient queue processing
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_callbacks_priority_retry
                    ON callbacks(priority, retry_at, request_status)
                """)
                logger.info("Created priority_retry index")
            except Exception as e:
                logger.warning(f"Could not create priority_retry index: {e}")
                logger.info("Created retry_at index")
            except Exception as e:
                logger.warning(f"Could not create retry_at index: {e}")

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
            fingerprint TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            retry_at TEXT,
            last_retry_at TEXT,
            priority TEXT DEFAULT 'default',
            escalation_level INTEGER DEFAULT 0,
            escalation_at TEXT,
            escalated_to TEXT
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

    # Create verification codes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            code TEXT NOT NULL,
            contact TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            verified BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (request_id) REFERENCES callbacks(request_id)
        )
    """)

    # Create index on request_id for verification lookup
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_verification_codes_request_id
        ON verification_codes(request_id)
    """)

    conn.commit()
    conn.close()

    logger.info("Database initialized successfully")


def retry_with_exponential_backoff(func, max_retries=3, base_delay=1, max_delay=10):
    """
    Retry a function with exponential backoff for network/DNS errors.

    Self-healing pattern for Twilio API calls that may fail due to:
    - DNS resolution errors
    - Network connectivity issues
    - Temporary API outages

    Args:
        func: Function to retry (should be a lambda or callable)
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1)
        max_delay: Maximum delay in seconds (default: 10)

    Returns:
        Result of func() if successful

    Raises:
        Last exception if all retries exhausted
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except (ConnectionError, Timeout, NameResolutionError, TwilioRestException) as e:
            if attempt == max_retries:
                # Last attempt failed - re-raise
                logger.error(f"All {max_retries} retry attempts exhausted: {str(e)}")
                raise

            # Calculate exponential backoff delay
            delay = min(base_delay * (2 ** attempt), max_delay)

            logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. Retrying in {delay}s...")
            time.sleep(delay)

    # Should never reach here, but just in case
    raise Exception("Retry logic error")


def generate_verification_code():
    """Generate a 6-digit verification code using cryptographically secure random."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def send_sms_verification(request_id, phone, visitor_name):
    """
    Send verification code via SMS using Twilio.

    Args:
        request_id (str): Request ID
        phone (str): Phone number
        visitor_name (str): Visitor's name

    Returns:
        tuple: (success: bool, code: str or None, error: str or None)
    """
    try:
        # Check concurrency limits for SMS
        can_proceed, concurrency_message, current_count, max_limit = check_concurrency_limit('sms')
        if not can_proceed:
            logger.warning(f"Concurrency limit reached for SMS: {current_count}/{max_limit}")
            return False, None, concurrency_message
        elif concurrency_message:
            # Queue or delay action - log the message but proceed
            logger.info(f"SMS concurrency handling: {concurrency_message}")

        # Check if code already exists and is still valid
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT code, expires_at
            FROM verification_codes
            WHERE request_id = ? AND channel = 'sms' AND verified = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        """, (request_id,))

        row = cursor.fetchone()
        now = datetime.utcnow()

        # Reuse existing code if still valid (within 10 minutes)
        if row:
            existing_code, expires_at_str = row
            expires_at = datetime.fromisoformat(expires_at_str)
            if now < expires_at:
                logger.info(f"Reusing existing SMS verification code for {request_id}")
                conn.close()
                # Still send the SMS again
                code = existing_code
            else:
                # Generate new code
                code = generate_verification_code()
        else:
            # Generate new code
            code = generate_verification_code()

        # Store code in database
        expires_at = now + timedelta(minutes=10)
        cursor.execute("""
            INSERT INTO verification_codes (request_id, channel, code, contact, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (request_id, 'sms', code, phone, now.isoformat(), expires_at.isoformat()))

        conn.commit()
        conn.close()

        # Send SMS via Twilio with retry logic (self-healing)
        if not twilio_client:
            logger.error("Twilio client not configured")
            return False, None, "SMS service not configured"

        # Keep message short to fit in 1 segment (including trial prefix)
        message = f"Your verification code is: {code}. Valid for 10 minutes."

        # Wrap Twilio API call with exponential backoff retry
        try:
            sms = retry_with_exponential_backoff(
                lambda: twilio_client.messages.create(
                    to=phone,
                    from_=TWILIO_NUMBER,
                    body=message
                ),
                max_retries=3,
                base_delay=1,
                max_delay=5
            )
        except Exception as retry_error:
            # All retries exhausted - return error
            logger.error(f"Failed to send SMS after retries: {str(retry_error)}")
            return False, None, f"SMS delivery failed after retries: {str(retry_error)}"

        # Increment Prometheus metrics
        verification_codes_sent.labels(channel='sms').inc()
        twilio_sms_total.labels(type='verification').inc()

        logger.info(f"SMS verification code sent to {phone} for request {request_id}: {sms.sid}")
        return True, code, None

    except Exception as e:
        logger.error(f"Failed to send SMS verification: {str(e)}")
        return False, None, str(e)


def verify_code(request_id, channel, code):
    """
    Verify a verification code.

    Args:
        request_id (str): Request ID
        channel (str): 'email' or 'sms'
        code (str): Code to verify

    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get the most recent unverified code for this request and channel
        cursor.execute("""
            SELECT id, code, expires_at, attempts
            FROM verification_codes
            WHERE request_id = ? AND channel = ? AND verified = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        """, (request_id, channel))

        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, "No verification code found"

        code_id, stored_code, expires_at_str, attempts = row
        expires_at = datetime.fromisoformat(expires_at_str)
        now = datetime.utcnow()

        # Check if code expired
        if now > expires_at:
            conn.close()
            return False, "Verification code expired"

        # Check if too many attempts
        if attempts >= 3:
            conn.close()
            return False, "Too many verification attempts"

        # Increment attempts
        cursor.execute("""
            UPDATE verification_codes
            SET attempts = attempts + 1
            WHERE id = ?
        """, (code_id,))

        # Check if code matches
        if code != stored_code:
            conn.commit()
            conn.close()
            # Increment failed verification metric
            verification_attempts_total.labels(result='failed').inc()
            return False, "Invalid verification code"

        # Mark as verified
        cursor.execute("""
            UPDATE verification_codes
            SET verified = TRUE
            WHERE id = ?
        """, (code_id,))

        conn.commit()
        conn.close()

        # Increment successful verification metric
        verification_attempts_total.labels(result='success').inc()

        logger.info(f"Verification code verified for {request_id} via {channel}")
        return True, None

    except Exception as e:
        logger.error(f"Failed to verify code: {str(e)}")
        return False, str(e)


def check_verification_status(request_id):
    """
    Check if request has been verified (either email OR SMS).

    Args:
        request_id (str): Request ID

    Returns:
        tuple: (verified: bool, channel: str or None)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT channel
            FROM verification_codes
            WHERE request_id = ? AND verified = TRUE
            LIMIT 1
        """, (request_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return True, row[0]
        return False, None

    except Exception as e:
        logger.error(f"Failed to check verification status: {str(e)}")
        return False, None


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


def determine_priority(visitor_phone, visitor_email=None):
    """
    Determine callback priority based on visitor information.

    Priority rules:
    - High: VIP phone numbers (configurable list)
    - Default: Regular customers
    - Low: Could be used for batch operations or non-urgent requests

    Args:
        visitor_phone: Visitor's phone number
        visitor_email: Visitor's email (optional, for future VIP detection)

    Returns:
        str: Priority level ('high', 'default', or 'low')
    """
    # VIP phone numbers (could be loaded from env var or database)
    vip_phones = os.environ.get("VIP_PHONE_NUMBERS", "").split(",")
    vip_phones = [p.strip() for p in vip_phones if p.strip()]

    # Check if visitor is VIP
    if visitor_phone in vip_phones:
        logger.info(f"VIP customer detected: {visitor_phone}")
        return PRIORITY_HIGH

    # Default priority for regular customers
    return PRIORITY_DEFAULT


def get_escalation_chain():
    """
    Parse escalation chain from environment variable.

    Returns:
        list: List of backup phone numbers in escalation order
    """
    if not ESCALATION_CHAIN:
        return []

    chain = [num.strip() for num in ESCALATION_CHAIN.split(",") if num.strip()]
    logger.debug(f"Escalation chain configured with {len(chain)} backup number(s)")
    return chain


def get_escalation_target(escalation_level):
    """
    Get the phone number to call for a given escalation level.

    Args:
        escalation_level (int): Current escalation level (0=primary, 1=first backup, etc.)

    Returns:
        str or None: Phone number to call, or None if no more escalation targets
    """
    if escalation_level == 0:
        # Level 0 = primary business number
        return BUSINESS_NUMBER

    # Level 1+ = backup numbers from escalation chain
    chain = get_escalation_chain()
    backup_index = escalation_level - 1

    if backup_index < len(chain):
        return chain[backup_index]

    # No more escalation targets
    return None


def should_escalate(request_id):
    """
    Check if a request should be escalated based on timeout.

    Args:
        request_id: The callback request ID

    Returns:
        tuple: (should_escalate: bool, current_level: int, next_target: str or None)
    """
    if not ESCALATION_ENABLED:
        return False, 0, None

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT request_status, created_at, escalation_level, escalation_at
            FROM callbacks
            WHERE request_id = ?
        """, (request_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, 0, None

        request_status, created_at, escalation_level, escalation_at = row

        # Only escalate if status is 'calling' (unanswered)
        if request_status != 'calling':
            return False, escalation_level or 0, None

        # Check if escalation timeout has passed
        reference_time = escalation_at if escalation_at else created_at
        reference_dt = datetime.fromisoformat(reference_time)
        timeout_dt = reference_dt + timedelta(minutes=ESCALATION_TIMEOUT_MINUTES)
        now = datetime.utcnow()

        if now < timeout_dt:
            # Not yet time to escalate
            return False, escalation_level or 0, None

        # Check if we've reached max escalation level
        current_level = escalation_level or 0
        next_level = current_level + 1

        if next_level > ESCALATION_MAX_LEVEL:
            logger.info(f"Request {request_id} has reached max escalation level ({ESCALATION_MAX_LEVEL})")
            return False, current_level, None

        # Get next escalation target
        next_target = get_escalation_target(next_level)

        if not next_target:
            logger.warning(f"No escalation target available for level {next_level}")
            return False, current_level, None

        logger.info(f"Request {request_id} should escalate from level {current_level} to {next_level} (target: {next_target})")
        return True, next_level, next_target

    except Exception as e:
        logger.error(f"Error checking escalation for {request_id}: {str(e)}")
        return False, 0, None


def escalate_request(request_id, new_level, target_number):
    """
    Escalate a callback request to the next level in the escalation chain.

    Args:
        request_id: The callback request ID
        new_level: The new escalation level
        target_number: The phone number to call

    Returns:
        dict: Result of escalation attempt
    """
    try:
        logger.info(f"Escalating request {request_id} to level {new_level} (calling {target_number})")

        # Update escalation tracking in database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE callbacks
            SET escalation_level = ?,
                escalation_at = ?,
                escalated_to = ?,
                updated_at = ?
            WHERE request_id = ?
        """, (
            new_level,
            datetime.utcnow().isoformat(),
            target_number,
            datetime.utcnow().isoformat(),
            request_id
        ))

        conn.commit()
        conn.close()

        # Get visitor info for the call
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT visitor_name, visitor_phone
            FROM callbacks
            WHERE request_id = ?
        """, (request_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": "Request not found"}

        visitor_name, visitor_phone = row

        # Initiate call to escalation target
        if callback_provider and callback_provider.is_configured():
            # Determine from_number based on provider
            if isinstance(callback_provider, TwilioProvider):
                from_number = TWILIO_NUMBER
            elif isinstance(callback_provider, AsteriskProvider):
                from_number = visitor_phone
            else:
                from_number = target_number

            call_result = callback_provider.make_call(
                to_number=target_number,
                from_number=from_number,
                request_id=request_id
            )

            if call_result['success']:
                update_callback_status(
                    request_id,
                    "calling",
                    f"Escalated to level {new_level} ({target_number})",
                    call_sid=call_result['call_sid']
                )

                log_audit_event(request_id, "escalated", {
                    "level": new_level,
                    "target": target_number,
                    "call_sid": call_result['call_sid']
                })

                logger.info(f"Escalation call initiated: {call_result['call_sid']}")
                return {"success": True, "call_sid": call_result['call_sid'], "level": new_level}
            else:
                logger.error(f"Escalation call failed: {call_result['message']}")
                return {"success": False, "error": call_result['message']}
        else:
            return {"success": False, "error": "Callback provider not configured"}

    except Exception as e:
        logger.error(f"Error escalating request {request_id}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


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


def calculate_retry_delay(retry_count):
    """
    Calculate exponential backoff delay for retries.

    Returns delay in seconds:
    - Retry 1: 60 seconds (1 minute)
    - Retry 2: 300 seconds (5 minutes)
    - Retry 3: 900 seconds (15 minutes)

    Formula: min(60 * (5 ** retry_count), 900)
    """
    # Exponential backoff: 1min, 5min, 15min
    delay = min(60 * (5 ** retry_count), 900)
    return delay


def schedule_retry(request_id, retry_count):
    """
    Schedule a retry for a failed callback request.

    Updates the database with:
    - retry_count incremented
    - retry_at set to current time + exponential backoff delay
    - last_retry_at set to current time
    - request_status set to 'retry_scheduled'
    """
    try:
        delay_seconds = calculate_retry_delay(retry_count)
        retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE callbacks
            SET retry_count = ?,
                retry_at = ?,
                last_retry_at = ?,
                request_status = 'retry_scheduled',
                status_message = ?,
                updated_at = ?
            WHERE request_id = ?
        """, (
            retry_count,
            retry_at.isoformat(),
            datetime.utcnow().isoformat(),
            f"Retry {retry_count} scheduled in {delay_seconds}s",
            datetime.utcnow().isoformat(),
            request_id
        ))

        conn.commit()
        conn.close()

        logger.info(f"Retry scheduled for {request_id}: attempt {retry_count} at {retry_at.isoformat()} (delay: {delay_seconds}s)")
        log_audit_event(request_id, "retry_scheduled", {
            "retry_count": retry_count,
            "retry_at": retry_at.isoformat(),
            "delay_seconds": delay_seconds
        })

        return True
    except Exception as e:
        logger.error(f"Failed to schedule retry for {request_id}: {str(e)}")
        return False


def mark_as_dead_letter(request_id, reason):
    """
    Mark a callback request as permanently failed (dead letter).

    This happens when max retries are exhausted.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE callbacks
            SET request_status = 'dead_letter',
                status_message = ?,
                updated_at = ?
            WHERE request_id = ?
        """, (
            reason,
            datetime.utcnow().isoformat(),
            request_id
        ))

        conn.commit()
        conn.close()

        logger.warning(f"Request {request_id} moved to dead letter queue: {reason}")
        log_audit_event(request_id, "dead_letter", {"reason": reason})

        return True
    except Exception as e:
        logger.error(f"Failed to mark {request_id} as dead letter: {str(e)}")
        return False


def process_retry_queue():
    """
    Process the retry queue - find requests that are due for retry and initiate callbacks.

    Processes requests in priority order:
    1. High priority first
    2. Default priority second
    3. Low priority last

    Within each priority level, processes oldest requests first (FIFO).

    This function should be called periodically (e.g., every minute) by a background job.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Find requests that are due for retry, ordered by priority then time
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            SELECT request_id, visitor_name, visitor_email, visitor_phone, retry_count, max_retries, priority
            FROM callbacks
            WHERE request_status = 'retry_scheduled'
            AND retry_at <= ?
            ORDER BY
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'default' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 2
                END ASC,
                retry_at ASC
            LIMIT 10
        """, (now,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            logger.debug("No retries due at this time")
            return

        logger.info(f"Processing {len(rows)} retry requests (priority-ordered)")

        for row in rows:
            request_id, visitor_name, visitor_email, visitor_phone, retry_count, max_retries, priority = row

            logger.info(f"Processing retry for {request_id} [priority={priority}]: attempt {retry_count}/{max_retries}")

            # Attempt the callback
            result = initiate_callback_internal(request_id, visitor_name, visitor_email, visitor_phone)

            # Note: initiate_callback_internal will update the status to 'calling' or 'failed'
            # The twilio_status_callback will handle the final outcome

    except Exception as e:
        logger.error(f"Error processing retry queue: {str(e)}", exc_info=True)


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


@app.route("/stats", methods=["GET"])
def public_stats():
    """
    Public statistics endpoint (no authentication required).
    Returns basic stats about the system.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get total requests
        cursor.execute("SELECT COUNT(*) FROM callbacks")
        total_requests = cursor.fetchone()[0]

        # Get requests by status
        cursor.execute("SELECT request_status, COUNT(*) FROM callbacks GROUP BY request_status")
        by_status = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            "success": True,
            "total_requests": total_requests,
            "by_status": by_status,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching public stats: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch stats"
        }), 500


@app.route("/health/workers", methods=["GET"])
def worker_health_endpoint():
    """
    Expose worker health status.
    Requires admin authentication.

    Returns:
        JSON with worker health status and Twilio API health
    """
    # Check admin authentication
    is_valid, error_response = check_admin_auth()
    if not is_valid:
        return error_response

    # Get worker health status
    health_report = check_worker_health()

    # Check Twilio API health
    twilio_healthy = check_twilio_api_health()

    return jsonify({
        "workers": health_report,
        "twilio_api": {
            "healthy": twilio_healthy,
            "timestamp": datetime.utcnow().isoformat()
        }
    })


@app.route("/health/concurrency", methods=["GET"])
def concurrency_health_endpoint():
    """
    Expose concurrency status.
    Requires admin authentication.

    Returns:
        JSON with current concurrency levels and limits
    """
    # Check admin authentication
    is_valid, error_response = check_admin_auth()
    if not is_valid:
        return error_response

    # Get current concurrency counts
    concurrent_calls = get_concurrent_calls_count()
    concurrent_sms = get_concurrent_sms_count()

    return jsonify({
        "calls": {
            "current": concurrent_calls,
            "limit": MAX_CONCURRENT_CALLS,
            "available": max(0, MAX_CONCURRENT_CALLS - concurrent_calls),
            "utilization_percent": round((concurrent_calls / MAX_CONCURRENT_CALLS * 100) if MAX_CONCURRENT_CALLS > 0 else 0, 2)
        },
        "sms": {
            "current": concurrent_sms,
            "limit": MAX_CONCURRENT_SMS,
            "available": max(0, MAX_CONCURRENT_SMS - concurrent_sms),
            "utilization_percent": round((concurrent_sms / MAX_CONCURRENT_SMS * 100) if MAX_CONCURRENT_SMS > 0 else 0, 2)
        },
        "overflow_action": CONCURRENCY_OVERFLOW_ACTION,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/health/commit_mode", methods=["GET"])
def commit_mode_health_endpoint():
    """
    Expose commit mode configuration and transaction statistics.
    Requires admin authentication.

    Returns:
        JSON with commit mode configuration and transaction counts
    """
    # Check admin authentication
    is_valid, error_response = check_admin_auth()
    if not is_valid:
        return error_response

    # Get transaction counts from Prometheus metrics
    # Note: We can't easily read Counter values, so we'll just show configuration
    return jsonify({
        "commit_mode": COMMIT_MODE,
        "description": {
            "on_db_commit": "Callback initiated only after verification is committed to DB (safest, default)",
            "auto": "Callback initiated immediately after verification (faster, potential race condition)",
            "request_finished": "Callback initiated after HTTP request completes (async pattern)"
        },
        "current_mode_description": (
            "Safest mode - ensures transactional integrity" if COMMIT_MODE == "on_db_commit"
            else "Fast mode - potential race condition" if COMMIT_MODE == "auto"
            else "Async mode - deferred processing"
        ),
        "transactional_integrity": COMMIT_MODE == "on_db_commit",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/metrics", methods=["GET"])
def metrics():
    """
    Prometheus metrics endpoint (requires authentication).
    Exposes metrics in Prometheus text format for monitoring and alerting.

    Authentication: Bearer token required (same as admin endpoints)
    Header: Authorization: Bearer <ADMIN_API_TOKEN>

    Metrics exposed:
    - callback_requests_total: Total callback requests by status
    - callback_requests_active: Currently active requests by status
    - twilio_calls_total: Total Twilio calls by status
    - twilio_sms_total: Total SMS sent by type
    - verification_codes_sent_total: Total verification codes sent by channel
    - verification_attempts_total: Total verification attempts by result
    """
    # Check authentication
    is_valid, error_response = check_admin_auth()
    if not is_valid:
        return error_response

    try:
        # Update gauge metrics from database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Reset all active gauges to 0 first
        for status in ['pending', 'verified', 'calling', 'connected', 'retry_scheduled']:
            callback_requests_active.labels(status=status).set(0)

        # Active requests by status
        cursor.execute("""
            SELECT request_status, COUNT(*)
            FROM callbacks
            WHERE request_status IN ('pending', 'verified', 'calling', 'connected', 'retry_scheduled')
            GROUP BY request_status
        """)
        for status, count in cursor.fetchall():
            callback_requests_active.labels(status=status).set(count)

        conn.close()
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")

    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


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


@app.route("/send_verification", methods=["POST"])
@limiter.limit("10 per minute")  # Allow more attempts for verification
def send_verification():
    """
    Send SMS verification code.

    This is step 1 of the new verification flow (SMS only).
    """
    try:
        data = request.get_json()

        # Validate required fields
        request_id = data.get("request_id", "").strip()

        if not request_id:
            return jsonify(success=False, error="Request ID is required"), 400

        # Get request details from database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT visitor_name, visitor_phone
            FROM callbacks
            WHERE request_id = ?
        """, (request_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify(success=False, error="Request not found"), 404

        visitor_name, visitor_phone = row

        if not visitor_phone:
            return jsonify(success=False, error="Phone number not provided"), 400

        # Send SMS verification code
        success, code, error = send_sms_verification(request_id, visitor_phone, visitor_name)
        if not success:
            return jsonify(success=False, error=f"Failed to send SMS: {error}"), 500

        log_audit_event(request_id, "sms_verification_sent", {"phone": visitor_phone})
        return jsonify(success=True, message="Verification code sent to your phone"), 200

    except Exception as e:
        logger.error(f"Error sending verification: {str(e)}")
        return jsonify(success=False, error="Internal server error"), 500


@app.route("/verify_code", methods=["POST"])
@limiter.limit("10 per minute")
def verify_code_endpoint():
    """
    Verify SMS verification code with transactional integrity.

    This is step 2 of the new verification flow (SMS only).

    Commit modes:
    - on_db_commit: Update status only after verification is committed (default, safest)
    - auto: Update status immediately after verification (faster)
    - request_finished: Update status after HTTP response (async)
    """
    try:
        set_action("verifying code")
        data = request.get_json()

        # Validate required fields
        request_id = data.get("request_id", "").strip()
        code = data.get("code", "").strip()

        if not request_id:
            return error_response("Request ID is required", 400)

        if not code:
            return error_response("Verification code is required", 400)

        # COMMIT MODE: on_db_commit (default)
        # Verify code first - this commits the verification to DB
        success, error = verify_code(request_id, 'sms', code)

        if not success:
            log_audit_event(request_id, "verification_failed", {"channel": "sms", "error": error})
            commit_mode_transactions_total.labels(mode=COMMIT_MODE, operation='verification_failed').inc()
            return error_response(error, 400)

        # Track successful verification
        commit_mode_transactions_total.labels(mode=COMMIT_MODE, operation='verification').inc()
        log_audit_event(request_id, "verification_success", {"channel": "sms"})

        # COMMIT MODE: on_db_commit
        # Only update status AFTER verification is committed to DB
        # This ensures transactional integrity - no race condition
        if COMMIT_MODE == "on_db_commit":
            # Verification is already committed (line 1407 in verify_code function)
            # Now safe to update callback status
            update_callback_status(request_id, "verified", "Verified via SMS")
            logger.debug(f"Commit mode: on_db_commit - Status updated after verification commit for {request_id}")

        elif COMMIT_MODE == "auto":
            # Update status immediately (potential race condition if verification commit fails)
            update_callback_status(request_id, "verified", "Verified via SMS")
            logger.debug(f"Commit mode: auto - Status updated immediately for {request_id}")

        elif COMMIT_MODE == "request_finished":
            # Update status after request completes (async pattern)
            # For now, we'll update immediately since Flask doesn't have built-in request_finished hook
            update_callback_status(request_id, "verified", "Verified via SMS")
            logger.debug(f"Commit mode: request_finished - Status updated for {request_id}")

        return jsonify(success=True, message="Verification successful"), 200

    except Exception as e:
        logger.error(f"Error verifying code: {str(e)}")
        commit_mode_transactions_total.labels(mode=COMMIT_MODE, operation='verification_error').inc()
        return jsonify(success=False, error="Internal server error"), 500


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
        # Auto-cancel old request if user submits a new one (better UX)
        is_duplicate, dup_message, existing_id, remaining_minutes = check_duplicate_request(visitor_phone, time_window_minutes=60)
        if is_duplicate:
            # Auto-cancel the old request
            try:
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE callbacks
                    SET request_status = 'cancelled',
                        status_message = 'Auto-cancelled: user submitted new request',
                        updated_at = ?
                    WHERE request_id = ?
                """, (datetime.utcnow().isoformat(), existing_id))

                conn.commit()
                conn.close()

                logger.info(f"Auto-cancelled old request {existing_id} for {visitor_phone} - user submitted new request")
                log_audit_event(existing_id, "auto_cancelled_on_new_request", {
                    "remote_addr": request.remote_addr,
                    "visitor_phone": visitor_phone
                })

                # Continue processing the new request (don't return error)

            except Exception as e:
                logger.error(f"Error auto-cancelling old request: {str(e)}")
                # If auto-cancel fails, still allow the new request (fail open for better UX)

        # SECURITY LAYER 5: Generate and check request fingerprint
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        fingerprint = generate_request_fingerprint(ip_address, user_agent, visitor_phone)

        is_abuse, abuse_message, abuse_count = check_fingerprint_abuse(fingerprint, max_requests_per_day=20)
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

        # Determine priority based on visitor information
        priority = determine_priority(visitor_phone, visitor_email)

        logger.info(f"Callback request received: {request_id} from {visitor_phone} [priority={priority}] (fingerprint: {fingerprint[:16]}...)")

        # Store in database with security metadata and priority
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO callbacks (
                request_id, visitor_name, visitor_email, visitor_phone,
                request_status, created_at, updated_at,
                ip_address, user_agent, fingerprint, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            fingerprint,
            priority
        ))

        conn.commit()
        conn.close()

        # Increment Prometheus metrics for pending requests and priority
        callback_requests_total.labels(status='pending').inc()
        callback_requests_by_priority.labels(priority=priority).inc()

        log_audit_event(request_id, "callback_requested", {
            "visitor_phone": visitor_phone,
            "has_name": bool(visitor_name),
            "has_email": bool(visitor_email),
            "priority": priority
        })

        # NEW FLOW: Return request_id and ask user to verify phone via SMS
        # The call will only be initiated after verification via /initiate_callback endpoint
        return jsonify(
            success=True,
            request_id=request_id,
            message="Please verify your phone number to proceed"
        ), 200

    except Exception as e:
        logger.error(f"Error processing callback request: {str(e)}", exc_info=True)
        return jsonify(success=False, error="Internal server error"), 500


@app.route("/initiate_callback", methods=["POST"])
@limiter.limit("5 per minute")
def initiate_callback():
    """
    Initiate the actual Twilio call AFTER verification is complete.

    This is step 3 of the new verification flow (after /send_verification and /verify_code).
    """
    try:
        set_action("initiating callback")
        data = request.get_json()

        # Validate required fields
        request_id = data.get("request_id", "").strip()

        if not request_id:
            return error_response("Request ID is required", 400)

        # Check if request exists and get details
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT visitor_name, visitor_email, visitor_phone, request_status
            FROM callbacks
            WHERE request_id = ?
        """, (request_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return error_response("Request not found", 404)

        visitor_name, visitor_email, visitor_phone, request_status = row

        # Check if verification is complete
        is_verified, verified_channel = check_verification_status(request_id)

        if not is_verified:
            return error_response("Verification required. Please verify your phone number first.", 403)

        logger.info(f"Initiating callback for verified request {request_id} (verified via {verified_channel})")

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
                    # Increment Prometheus metrics
                    callback_requests_total.labels(status='calling').inc()
                    twilio_calls_total.labels(status='initiated').inc()
                    logger.info(f"Call initiated via {callback_provider.__class__.__name__}: {call_result['call_sid']}")
                else:
                    raise Exception(call_result['message'])

            except Exception as e:
                logger.error(f"Callback failed: {str(e)}")
                update_callback_status(request_id, "failed", f"Call failed: {str(e)}")
                # Increment Prometheus metrics
                callback_requests_total.labels(status='failed').inc()
                twilio_calls_total.labels(status='failed').inc()

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


@app.route("/cancel_request", methods=["POST"])
@limiter.limit("10 per minute")
def cancel_request():
    """
    Cancel a pending callback request.

    Allows users to cancel their pending request so they can submit a new one.
    """
    try:
        data = request.get_json()
        request_id = data.get("request_id", "").strip()

        if not request_id:
            return jsonify(success=False, error="Request ID is required"), 400

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if request exists and is cancellable
        cursor.execute("""
            SELECT request_status, visitor_phone
            FROM callbacks
            WHERE request_id = ?
        """, (request_id,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify(success=False, error="Request not found"), 404

        status, visitor_phone = row

        # Only allow cancellation of pending/calling requests
        if status not in ['pending', 'calling', 'verified']:
            conn.close()
            return jsonify(success=False, error=f"Cannot cancel {status} request"), 400

        # Update status to cancelled
        cursor.execute("""
            UPDATE callbacks
            SET request_status = 'cancelled',
                status_message = 'Cancelled by user',
                updated_at = ?
            WHERE request_id = ?
        """, (datetime.utcnow().isoformat(), request_id))

        conn.commit()
        conn.close()

        logger.info(f"Request cancelled by user: {request_id} (phone: {visitor_phone})")
        log_audit_event(request_id, "request_cancelled", {"phone": visitor_phone})

        return jsonify(success=True, message="Request cancelled successfully"), 200

    except Exception as e:
        logger.error(f"Error cancelling request: {str(e)}")
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

            # DEBUG: Log URL details to diagnose signature validation issues
            logger.debug(f"Signature validation - URL: {url}")
            logger.debug(f"Signature validation - Scheme: {request.scheme}")
            logger.debug(f"Signature validation - Host: {request.host}")
            logger.debug(f"Signature validation - X-Forwarded-Proto: {request.headers.get('X-Forwarded-Proto')}")
            logger.debug(f"Signature validation - X-Forwarded-Host: {request.headers.get('X-Forwarded-Host')}")

            if not twilio_validator.validate(url, params, signature):
                logger.warning(f"Invalid Twilio signature - possible spoofing attempt for request {request_id}")
                logger.warning(f"URL used for validation: {url}")
                logger.warning(f"Params: {params}")
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
        call_duration = request.form.get("CallDuration", "0")

        logger.info(f"Twilio status callback: {request_id} - {call_status} (duration: {call_duration}s)")

        if not request_id:
            logger.error("Status callback missing request_id")
            return "", 400

        # Update status based on call outcome
        # Treat "completed" with short duration as "no-answer" (declined/voicemail)
        # Duration includes ring time, so threshold must be higher (20s = ~3 rings)
        try:
            duration_seconds = int(call_duration)
        except (ValueError, TypeError):
            duration_seconds = 0

        if call_status == "completed" and duration_seconds >= 20:
            # Real conversation happened (answered and talked for 20+ seconds)
            update_callback_status(request_id, "completed", "Call completed successfully")
            # Increment Prometheus metrics
            callback_requests_total.labels(status='completed').inc()
            twilio_calls_total.labels(status='completed').inc()
        elif call_status in ["no-answer", "busy", "failed"] or (call_status == "completed" and duration_seconds < 20):
            # Check retry count and decide whether to retry or mark as failed
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT retry_count, max_retries, visitor_name, visitor_phone
                FROM callbacks
                WHERE request_id = ?
            """, (request_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                retry_count, max_retries, visitor_name, visitor_phone = row

                # Increment retry count
                new_retry_count = retry_count + 1

                if new_retry_count <= max_retries:
                    # Schedule retry with exponential backoff
                    logger.info(f"Call failed for {request_id}, scheduling retry {new_retry_count}/{max_retries}")
                    schedule_retry(request_id, new_retry_count)
                    # Increment Prometheus metrics for retry scheduled
                    callback_requests_total.labels(status='retry_scheduled').inc()
                    twilio_calls_total.labels(status='failed').inc()
                else:
                    # Max retries exhausted - mark as dead letter
                    logger.warning(f"Max retries exhausted for {request_id}, moving to dead letter queue")
                    mark_as_dead_letter(request_id, f"Max retries ({max_retries}) exhausted after {call_status}")
                    # Increment Prometheus metrics
                    callback_requests_total.labels(status='dead_letter').inc()
                    twilio_calls_total.labels(status='failed').inc()

                    # Send SMS to BOTH business AND visitor as final fallback
                    if twilio_client:
                        try:
                            # SMS to business (existing behavior)
                            business_sms = twilio_client.messages.create(
                                to=BUSINESS_NUMBER,
                                from_=TWILIO_NUMBER,
                                body=f"Missed callback from {visitor_name or 'visitor'} at {visitor_phone}. Please call back."
                            )
                            twilio_sms_total.labels(type='missed_call_business').inc()
                            logger.info(f"SMS sent to business for missed call: {business_sms.sid}")

                            # SMS to visitor (NEW: inform them what happened)
                            # Keep message short to avoid carrier filtering (trial account adds ~40 char prefix)
                            visitor_sms = twilio_client.messages.create(
                                to=visitor_phone,
                                from_=TWILIO_NUMBER,
                                body=f"We missed you! Reply: VOICEMAIL to leave message, HELP for assistance, or CANCEL to stop."
                            )
                            twilio_sms_total.labels(type='missed_call_visitor').inc()
                            logger.info(f"SMS sent to visitor for missed call: {visitor_sms.sid}")
                        except Exception as e:
                            logger.error(f"Failed to send SMS fallback: {str(e)}")
            else:
                # Fallback if we can't find the request (shouldn't happen)
                update_callback_status(request_id, "failed", f"Call {call_status}")
                callback_requests_total.labels(status='failed').inc()
                twilio_calls_total.labels(status='failed').inc()

        return "", 200

    except Exception as e:
        logger.error(f"Error in status callback: {str(e)}")
        return "", 500


@app.route("/twilio/sms", methods=["POST"])
def twilio_incoming_sms():
    """
    Handle incoming SMS messages from visitors.
    Allows visitors to interact via text:
    - VOICEMAIL: Connect to business voicemail
    - HELP: Get assistance information
    - CANCEL: Cancel callback request
    """
    try:
        from twilio.twiml.messaging_response import MessagingResponse

        # Verify Twilio signature
        if twilio_validator:
            signature = request.headers.get('X-Twilio-Signature', '')
            url = request.url
            params = request.form.to_dict()

            if not twilio_validator.validate(url, params, signature):
                logger.warning(f"Invalid Twilio signature on incoming SMS")
                return "", 403

        from_number = request.form.get('From', '')
        body = request.form.get('Body', '').strip().upper()

        logger.info(f"Incoming SMS from {from_number}: {body}")

        resp = MessagingResponse()

        # Find most recent callback request from this number
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT request_id, visitor_name, request_status
            FROM callbacks
            WHERE visitor_phone = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (from_number,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            resp.message("We don't have a callback request from this number. Please visit our website to request a callback.")
            logger.info(f"No callback request found for {from_number}")
            return str(resp), 200

        request_id, visitor_name, request_status = row

        # Handle different commands
        if 'VOICEMAIL' in body:
            # Initiate call that connects visitor directly to business voicemail
            if twilio_client:
                try:
                    call = twilio_client.calls.create(
                        to=from_number,
                        from_=TWILIO_NUMBER,
                        url=f"https://api.swipswaps.com/twilio/voicemail_connect",
                        status_callback=f"https://api.swipswaps.com/twilio/status_callback?request_id={request_id}",
                        status_callback_event=["completed"]
                    )
                    resp.message(f"Calling you now to connect you to our voicemail. Please answer your phone.")
                    update_callback_status(request_id, "voicemail_requested", "Visitor requested voicemail", call_sid=call.sid)
                    logger.info(f"Voicemail call initiated for {from_number}: {call.sid}")
                except Exception as e:
                    logger.error(f"Failed to initiate voicemail call: {str(e)}")
                    resp.message(f"Sorry, we couldn't connect you to voicemail. Please call us directly at {BUSINESS_NUMBER}.")
            else:
                resp.message(f"Please call us directly at {BUSINESS_NUMBER} to leave a voicemail.")

        elif 'HELP' in body:
            resp.message(f"We'll call you back if and when feasible. For immediate assistance, call us at {BUSINESS_NUMBER}.\n\nReply VOICEMAIL to leave a message or CANCEL to cancel your request.")
            log_audit_event(request_id, "sms_help_requested", {"from": from_number})

        elif 'CANCEL' in body:
            update_callback_status(request_id, "cancelled", "Cancelled by visitor via SMS")
            resp.message("Your callback request has been cancelled. Thank you!")
            log_audit_event(request_id, "sms_cancelled", {"from": from_number})
            logger.info(f"Callback request {request_id} cancelled via SMS by {from_number}")

        else:
            # Unknown command
            resp.message(f"Reply:\nVOICEMAIL - Leave a message\nHELP - Get assistance\nCANCEL - Cancel request\n\nOr call us at {BUSINESS_NUMBER}")
            log_audit_event(request_id, "sms_unknown_command", {"from": from_number, "body": body[:100]})

        return str(resp), 200

    except Exception as e:
        logger.error(f"Error handling incoming SMS: {str(e)}")
        resp = MessagingResponse()
        resp.message(f"Sorry, we encountered an error. Please call us at {BUSINESS_NUMBER}.")
        return str(resp), 200


@app.route("/twilio/voicemail_connect", methods=["POST"])
def twilio_voicemail_connect():
    """
    TwiML endpoint that connects caller directly to business voicemail.
    When visitor replies VOICEMAIL via SMS, they get called and connected to business number.
    If business doesn't answer, visitor reaches voicemail naturally.
    """
    try:
        from twilio.twiml.voice_response import VoiceResponse, Dial

        resp = VoiceResponse()
        resp.say("Please wait while we connect you to our voicemail system.", voice='alice')

        # Dial business number - if no answer, caller reaches business voicemail
        dial = Dial(
            timeout=30,
            action=f"https://api.swipswaps.com/twilio/voicemail_status",
            method="POST"
        )
        dial.number(BUSINESS_NUMBER)
        resp.append(dial)

        logger.info(f"Voicemail TwiML generated - dialing {BUSINESS_NUMBER}")

        return str(resp), 200, {'Content-Type': 'text/xml'}

    except Exception as e:
        logger.error(f"Error generating voicemail TwiML: {str(e)}")
        resp = VoiceResponse()
        resp.say(f"Sorry, we encountered an error. Please call us directly at {BUSINESS_NUMBER}.", voice='alice')
        return str(resp), 200, {'Content-Type': 'text/xml'}


@app.route("/twilio/voicemail_status", methods=["POST"])
def twilio_voicemail_status():
    """
    Handle status after voicemail dial attempt.
    """
    try:
        from twilio.twiml.voice_response import VoiceResponse

        dial_call_status = request.form.get('DialCallStatus')
        logger.info(f"Voicemail dial status: {dial_call_status}")

        resp = VoiceResponse()

        if dial_call_status in ['no-answer', 'busy', 'failed']:
            resp.say("We're sorry, we couldn't connect you to voicemail. Please try calling us directly.", voice='alice')

        return str(resp), 200, {'Content-Type': 'text/xml'}

    except Exception as e:
        logger.error(f"Error in voicemail status: {str(e)}")
        return "", 200


@app.route("/logs", methods=["GET"])
@limiter.limit("10 per minute")
def get_logs():
    """
    Return recent application logs from /tmp/app.log.
    Query params:
    - lines: number of lines to return (default: 100, max: 1000)
    - filter: filter logs by keyword (e.g., 'twilio', 'oauth', 'error')
    """
    try:
        lines = min(int(request.args.get('lines', 100)), 1000)
        filter_keyword = request.args.get('filter', '').lower()

        # Read logs from file
        log_file = "/tmp/app.log"

        if not os.path.exists(log_file):
            return jsonify({
                'success': False,
                'error': 'Log file not found'
            }), 404

        # Read last N lines from log file
        with open(log_file, 'r') as f:
            all_lines = f.readlines()

        # Get last N lines
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # Apply filter if specified
        if filter_keyword:
            recent_lines = [line for line in recent_lines if filter_keyword in line.lower()]

        logs = ''.join(recent_lines)

        return jsonify({
            'success': True,
            'logs': logs,
            'lines_requested': lines,
            'lines_returned': len(recent_lines),
            'filter': filter_keyword or 'none',
            'total_lines_in_file': len(all_lines)
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving logs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# ADMIN DASHBOARD API ENDPOINTS
# ============================================================

def check_admin_auth():
    """
    Check if request has valid admin Bearer token.
    Returns (is_valid: bool, error_response: tuple or None)
    """
    if not ADMIN_API_TOKEN:
        logger.warning("Admin API token not configured - admin endpoints disabled")
        return False, (jsonify({"success": False, "error": "Admin API not configured"}), 503)

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return False, (jsonify({"success": False, "error": "Missing or invalid Authorization header"}), 401)

    token = auth_header[7:]  # Remove "Bearer " prefix

    if token != ADMIN_API_TOKEN:
        logger.warning(f"Invalid admin token attempt from {request.remote_addr}")
        return False, (jsonify({"success": False, "error": "Invalid admin token"}), 403)

    return True, None


@app.route("/admin/api/stats", methods=["GET"])
@limiter.limit("60 per minute")
def admin_get_stats():
    """
    Get callback system statistics.
    Requires Bearer token authentication.

    Returns:
    - total_requests: Total callback requests
    - by_status: Count of requests by status
    - success_rate: Percentage of successful callbacks
    - last_24h: Stats for last 24 hours
    """
    is_valid, error_response = check_admin_auth()
    if not is_valid:
        return error_response

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Total requests
        cursor.execute("SELECT COUNT(*) FROM callbacks")
        total_requests = cursor.fetchone()[0]

        # Requests by status
        cursor.execute("""
            SELECT request_status, COUNT(*) as count
            FROM callbacks
            GROUP BY request_status
        """)
        by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Success rate (completed / total calls attempted)
        completed = by_status.get('completed', 0)
        total_calls = sum(by_status.get(s, 0) for s in ['calling', 'connected', 'completed', 'failed'])
        success_rate = (completed / total_calls * 100) if total_calls > 0 else 0

        # Last 24 hours stats
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        cursor.execute("""
            SELECT COUNT(*) FROM callbacks
            WHERE created_at > ?
        """, (cutoff_time.isoformat(),))
        last_24h_total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT request_status, COUNT(*) as count
            FROM callbacks
            WHERE created_at > ?
            GROUP BY request_status
        """, (cutoff_time.isoformat(),))
        last_24h_by_status = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            "success": True,
            "stats": {
                "total_requests": total_requests,
                "by_status": by_status,
                "success_rate": round(success_rate, 2),
                "last_24h": {
                    "total": last_24h_total,
                    "by_status": last_24h_by_status
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/admin/api/requests", methods=["GET"])
@limiter.limit("60 per minute")
def admin_get_requests():
    """
    Get all callback requests with optional filtering.
    Requires Bearer token authentication.

    Query params:
    - status: Filter by status (pending, verified, calling, connected, completed, failed, cancelled)
    - phone: Filter by phone number (partial match)
    - limit: Max results (default: 100, max: 1000)
    - offset: Pagination offset (default: 0)
    - order: Sort order (asc or desc, default: desc)
    """
    is_valid, error_response = check_admin_auth()
    if not is_valid:
        return error_response

    try:
        # Parse query parameters
        status_filter = request.args.get('status', '').strip()
        phone_filter = request.args.get('phone', '').strip()
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        order = request.args.get('order', 'desc').lower()

        if order not in ['asc', 'desc']:
            order = 'desc'

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Build query with filters
        query = """
            SELECT request_id, visitor_name, visitor_email, visitor_phone,
                   request_status, status_message, created_at, updated_at,
                   call_sid, sms_sid, ip_address, user_agent, fingerprint, priority,
                   escalation_level, escalation_at, escalated_to
            FROM callbacks
            WHERE 1=1
        """
        params = []

        if status_filter:
            query += " AND request_status = ?"
            params.append(status_filter)

        if phone_filter:
            query += " AND visitor_phone LIKE ?"
            params.append(f"%{phone_filter}%")

        query += f" ORDER BY created_at {order.upper()} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)

        requests_list = []
        for row in cursor.fetchall():
            requests_list.append({
                "request_id": row[0],
                "visitor_name": row[1],
                "visitor_email": row[2],
                "visitor_phone": row[3],
                "request_status": row[4],
                "status_message": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "call_sid": row[8],
                "sms_sid": row[9],
                "ip_address": row[10],
                "user_agent": row[11],
                "fingerprint": row[12][:16] + "..." if row[12] else None,  # Truncate fingerprint
                "priority": row[13] if len(row) > 13 else 'default',
                "escalation_level": row[14] if len(row) > 14 else 0,
                "escalation_at": row[15] if len(row) > 15 else None,
                "escalated_to": row[16] if len(row) > 16 else None
            })

        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM callbacks WHERE 1=1"
        count_params = []

        if status_filter:
            count_query += " AND request_status = ?"
            count_params.append(status_filter)

        if phone_filter:
            count_query += " AND visitor_phone LIKE ?"
            count_params.append(f"%{phone_filter}%")

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            "success": True,
            "requests": requests_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting admin requests: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/admin/api/retry/<request_id>", methods=["POST"])
@limiter.limit("10 per minute")
def admin_retry_callback(request_id):
    """
    Retry a failed callback request.
    Requires Bearer token authentication.

    This will:
    1. Check if request exists and is in 'failed' status
    2. Reset status to 'verified'
    3. Initiate a new callback
    """
    is_valid, error_response = check_admin_auth()
    if not is_valid:
        return error_response

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if request exists
        cursor.execute("""
            SELECT visitor_name, visitor_email, visitor_phone, request_status
            FROM callbacks
            WHERE request_id = ?
        """, (request_id,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Request not found"}), 404

        visitor_name, visitor_email, visitor_phone, current_status = row

        # Only allow retry for failed requests
        if current_status not in ['failed', 'cancelled']:
            conn.close()
            return jsonify({
                "success": False,
                "error": f"Cannot retry request with status '{current_status}'. Only 'failed' or 'cancelled' requests can be retried."
            }), 400

        # Reset status to verified
        cursor.execute("""
            UPDATE callbacks
            SET request_status = ?, status_message = ?, updated_at = ?
            WHERE request_id = ?
        """, (
            'verified',
            'Retrying callback (admin action)',
            datetime.utcnow().isoformat(),
            request_id
        ))

        conn.commit()
        conn.close()

        logger.info(f"Admin retry initiated for request {request_id} from {request.remote_addr}")
        log_audit_event(request_id, "admin_retry", {"admin_ip": request.remote_addr})

        # Initiate callback using existing logic
        # We'll call the initiate_callback function directly
        try:
            result = initiate_callback_internal(request_id, visitor_name, visitor_email, visitor_phone)

            if result.get("success"):
                return jsonify({
                    "success": True,
                    "message": "Callback retry initiated successfully",
                    "request_id": request_id
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "Failed to initiate callback")
                }), 500

        except Exception as e:
            logger.error(f"Error initiating retry callback: {str(e)}", exc_info=True)
            return jsonify({"success": False, "error": "Failed to initiate callback"}), 500

    except Exception as e:
        logger.error(f"Error retrying callback: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


def initiate_callback_internal(request_id, visitor_name, visitor_email, visitor_phone):
    """
    Internal function to initiate callback (used by admin retry).
    Returns dict with success status and error message if applicable.
    """
    try:
        # Check if callback provider is configured
        if not callback_provider or not callback_provider.is_configured():
            logger.error("Callback provider not configured")
            update_callback_status(request_id, "failed", "Callback provider not configured")
            return {"success": False, "error": "Callback provider not configured"}

        # Check concurrency limits for calls
        can_proceed, concurrency_message, current_count, max_limit = check_concurrency_limit('call')
        if not can_proceed:
            logger.warning(f"Concurrency limit reached for calls: {current_count}/{max_limit}")
            update_callback_status(request_id, "failed", concurrency_message)
            return {"success": False, "error": concurrency_message}
        elif concurrency_message:
            # Queue or delay action - log the message but proceed
            logger.info(f"Concurrency limit handling: {concurrency_message}")

        # Check cost limits (disabled - function not implemented)
        # within_limits, limit_message, stats = check_cost_limits()
        # if not within_limits:
        #     logger.warning(f"Cost limits exceeded: {limit_message}")
        #     update_callback_status(request_id, "failed", limit_message)
        #     return {"success": False, "error": limit_message}

        # Determine from_number based on provider
        if isinstance(callback_provider, TwilioProvider):
            from_number = TWILIO_NUMBER
        elif isinstance(callback_provider, AsteriskProvider):
            from_number = visitor_phone
        else:
            from_number = BUSINESS_NUMBER

        # Initiate call
        logger.info(f"Initiating callback for request {request_id} (admin retry)")
        call_result = callback_provider.make_call(
            to_number=BUSINESS_NUMBER,
            from_number=from_number,
            request_id=request_id
        )

        if call_result['success']:
            update_callback_status(request_id, "calling", "Call initiated (admin retry)", call_sid=call_result['call_sid'])
            log_audit_event(request_id, "call_initiated_admin", {"call_sid": call_result['call_sid']})
            return {"success": True, "call_sid": call_result['call_sid']}
        else:
            update_callback_status(request_id, "failed", f"Call failed: {call_result['message']}")
            return {"success": False, "error": call_result['message']}

    except Exception as e:
        logger.error(f"Error in initiate_callback_internal: {str(e)}", exc_info=True)
        update_callback_status(request_id, "failed", f"Error: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================
# RECURRING TASKS SYSTEM
# ============================================================

def process_escalation_queue():
    """
    Check for callback requests that need escalation and escalate them.

    This function should be called periodically (e.g., every minute) by a background job.
    It checks for requests in 'calling' status that have exceeded the escalation timeout
    and escalates them to the next level in the escalation chain.

    Returns:
        int: Number of requests escalated
    """
    if not ESCALATION_ENABLED:
        logger.debug("Escalation disabled, skipping escalation queue processing")
        return 0

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Find requests in 'calling' status that might need escalation
        cursor.execute("""
            SELECT request_id
            FROM callbacks
            WHERE request_status = 'calling'
            AND (escalation_level IS NULL OR escalation_level < ?)
        """, (ESCALATION_MAX_LEVEL,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            logger.debug("No requests pending escalation")
            return 0

        escalated_count = 0

        for row in rows:
            request_id = row[0]

            # Check if this request should be escalated
            should_esc, next_level, next_target = should_escalate(request_id)

            if should_esc:
                logger.info(f"Escalating request {request_id} to level {next_level}")

                # Attempt escalation
                result = escalate_request(request_id, next_level, next_target)

                # Track metrics
                escalations_total.labels(level=str(next_level)).inc()

                if result['success']:
                    escalated_count += 1
                    escalation_success_total.labels(level=str(next_level)).inc()
                    logger.info(f"Successfully escalated {request_id} to level {next_level}")
                else:
                    escalation_failures_total.labels(level=str(next_level)).inc()
                    logger.error(f"Failed to escalate {request_id}: {result.get('error')}")

        if escalated_count > 0:
            logger.info(f"Escalation queue processed: {escalated_count} request(s) escalated")

        return escalated_count

    except Exception as e:
        logger.error(f"Error processing escalation queue: {str(e)}", exc_info=True)
        return 0


def cleanup_old_requests(max_age_days=90):
    """
    Delete callback requests older than max_age_days.

    Data retention compliance - removes old requests to comply with GDPR/privacy policies.

    Args:
        max_age_days (int): Maximum age of requests to keep (default: 90 days)

    Returns:
        int: Number of requests deleted
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        cursor.execute("""
            DELETE FROM callbacks
            WHERE created_at < ?
            AND request_status IN ('completed', 'failed', 'cancelled', 'dead_letter')
        """, (cutoff_date.isoformat(),))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(f"Cleanup: deleted {deleted_count} old request(s) older than {max_age_days} days")

        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old requests: {str(e)}")
        return 0


def cleanup_expired_verification_codes(max_age_hours=24):
    """
    Remove expired verification codes from database.

    Security compliance - ensures old codes cannot be used.

    Args:
        max_age_hours (int): Maximum age of codes to keep (default: 24 hours)

    Returns:
        int: Number of codes deleted
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        cursor.execute("""
            DELETE FROM verification_codes
            WHERE created_at < ?
        """, (cutoff_time.isoformat(),))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(f"Cleanup: deleted {deleted_count} expired verification code(s)")

        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up verification codes: {str(e)}")
        return 0


def cleanup_old_audit_logs(max_age_days=365):
    """
    Archive audit logs older than max_age_days.

    Storage compliance - prevents audit log table from growing indefinitely.

    Args:
        max_age_days (int): Maximum age of logs to keep (default: 365 days)

    Returns:
        int: Number of logs deleted
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        cursor.execute("""
            DELETE FROM audit_log
            WHERE timestamp < ?
        """, (cutoff_date.isoformat(),))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(f"Cleanup: deleted {deleted_count} old audit log(s) older than {max_age_days} days")

        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up audit logs: {str(e)}")
        return 0


def send_daily_compliance_report(recipients=None):
    """
    Send daily summary email with callback system statistics.

    Monitoring compliance - provides visibility into system health.

    Args:
        recipients (list): Email addresses to send report to (default: ALERT_EMAIL from env)

    Returns:
        bool: True if report sent successfully
    """
    try:
        if recipients is None or len(recipients) == 0:
            recipients = [ALERT_EMAIL] if ALERT_EMAIL else []

        if not recipients:
            logger.debug("No recipients configured for daily report")
            return False

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get stats for last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN request_status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN request_status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN request_status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM callbacks
            WHERE created_at >= ?
        """, (yesterday.isoformat(),))

        stats = cursor.fetchone()
        total, completed, failed, cancelled = stats

        # Get abuse blocks
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log
            WHERE event_type IN ('fingerprint_abuse_blocked', 'duplicate_request_blocked')
            AND timestamp >= ?
        """, (yesterday.isoformat(),))

        abuse_blocks = cursor.fetchone()[0]

        conn.close()

        # Format report
        report = f"""
Daily Callback System Report - {datetime.utcnow().strftime('%Y-%m-%d')}

Summary (Last 24 Hours):
- Total Requests: {total}
- Completed: {completed}
- Failed: {failed}
- Cancelled: {cancelled}
- Abuse Blocks: {abuse_blocks}

Success Rate: {(completed / total * 100) if total > 0 else 0:.1f}%
"""

        logger.info(f"Daily report generated: {total} requests, {completed} completed, {failed} failed")
        logger.info(f"Report would be sent to: {', '.join(recipients)}")

        # TODO: Implement actual email sending via SMTP or SendGrid
        # For now, just log the report
        logger.info(report)

        return True
    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}")
        return False


def analyze_fingerprint_abuse_patterns(threshold_multiplier=2.0):
    """
    Analyze fingerprint patterns to detect sophisticated abuse.

    Security compliance - detects distributed attacks and abuse patterns.

    Args:
        threshold_multiplier (float): Multiplier for normal request rate (default: 2.0)

    Returns:
        dict: Analysis results with suspicious fingerprints
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get fingerprints with unusually high request rates in last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)

        cursor.execute("""
            SELECT fingerprint, COUNT(*) as request_count
            FROM callbacks
            WHERE created_at >= ?
            GROUP BY fingerprint
            HAVING request_count > ?
            ORDER BY request_count DESC
        """, (yesterday.isoformat(), 20 * threshold_multiplier))

        suspicious = cursor.fetchall()
        conn.close()

        if suspicious:
            logger.warning(f"Abuse pattern detected: {len(suspicious)} suspicious fingerprint(s)")
            for fingerprint, count in suspicious:
                logger.warning(f"  Fingerprint {fingerprint[:16]}... made {count} requests in 24h")

        return {
            "suspicious_count": len(suspicious),
            "fingerprints": [{"fingerprint": fp[:16], "count": count} for fp, count in suspicious]
        }
    except Exception as e:
        logger.error(f"Error analyzing abuse patterns: {str(e)}")
        return {"suspicious_count": 0, "fingerprints": []}


def check_daily_cost_thresholds(warning_threshold=0.8):
    """
    Check if approaching daily call/SMS limits and send alerts.

    Budget compliance - prevents unexpected costs.

    Args:
        warning_threshold (float): Threshold to trigger warning (default: 0.8 = 80%)

    Returns:
        dict: Current usage stats and alert status
    """
    try:
        within_limits, message, stats = check_daily_limits()

        calls_24h = stats.get('calls_24h', 0)
        sms_24h = stats.get('sms_24h', 0)
        max_calls = stats.get('max_calls', MAX_CALLS_PER_DAY)
        max_sms = stats.get('max_sms', MAX_SMS_PER_DAY)

        calls_pct = (calls_24h / max_calls) if max_calls > 0 else 0
        sms_pct = (sms_24h / max_sms) if max_sms > 0 else 0

        alert_sent = False

        if calls_pct >= warning_threshold:
            logger.warning(f"Cost alert: {calls_pct*100:.1f}% of daily call limit used ({calls_24h}/{max_calls})")
            alert_sent = True

        if sms_pct >= warning_threshold:
            logger.warning(f"Cost alert: {sms_pct*100:.1f}% of daily SMS limit used ({sms_24h}/{max_sms})")
            alert_sent = True

        return {
            "calls_used": calls_24h,
            "calls_limit": max_calls,
            "calls_pct": calls_pct,
            "sms_used": sms_24h,
            "sms_limit": max_sms,
            "sms_pct": sms_pct,
            "alert_sent": alert_sent
        }
    except Exception as e:
        logger.error(f"Error checking cost thresholds: {str(e)}")
        return {}


# ============================================================
# RECURRING TASKS SCHEDULER (APScheduler)
# ============================================================

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import yaml

def load_recurring_tasks_config():
    """
    Load recurring tasks configuration from YAML file.

    Returns:
        dict: Tasks configuration dictionary
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'recurring_tasks.yml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded recurring tasks config from {config_path}")
        return config.get('tasks', {})
    except FileNotFoundError:
        logger.warning(f"Recurring tasks config not found at {config_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading recurring tasks config: {str(e)}")
        return {}


# Initialize APScheduler
scheduler = BackgroundScheduler(timezone=pytz.UTC)

# Map task function names to actual functions
task_functions = {
    'cleanup_old_requests': cleanup_old_requests,
    'cleanup_expired_verification_codes': cleanup_expired_verification_codes,
    'cleanup_old_audit_logs': cleanup_old_audit_logs,
    'send_daily_compliance_report': send_daily_compliance_report,
    'cleanup_stuck_requests': cleanup_stuck_requests,
    'analyze_fingerprint_abuse_patterns': analyze_fingerprint_abuse_patterns,
    'check_daily_cost_thresholds': check_daily_cost_thresholds,
    'process_escalation_queue': process_escalation_queue
}

# Load and register recurring tasks from YAML config
tasks_config = load_recurring_tasks_config()
registered_count = 0

for task_name, task_config in tasks_config.items():
    if not task_config.get('enabled', False):
        logger.debug(f"Skipping disabled task: {task_name}")
        continue

    function_name = task_config.get('function')
    schedule = task_config.get('schedule')
    params = task_config.get('params', {})
    description = task_config.get('description', task_name)

    if function_name not in task_functions:
        logger.warning(f"Task function '{function_name}' not found for task '{task_name}'")
        continue

    try:
        # Parse cron schedule (minute hour day month day_of_week)
        parts = schedule.split()
        if len(parts) != 5:
            logger.error(f"Invalid cron schedule for {task_name}: {schedule}")
            continue

        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone=pytz.UTC
        )

        scheduler.add_job(
            task_functions[function_name],
            trigger=trigger,
            kwargs=params,
            id=task_name,
            name=description,
            replace_existing=True
        )

        logger.info(f"Registered recurring task: {task_name} ({schedule}) - {description}")
        registered_count += 1

    except Exception as e:
        logger.error(f"Error registering task {task_name}: {str(e)}")

# Start scheduler
try:
    scheduler.start()
    logger.info(f"Recurring tasks scheduler started with {registered_count} task(s)")
except Exception as e:
    logger.error(f"Error starting scheduler: {str(e)}")


# ============================================================
# WORKER HEALTH MONITORING
# ============================================================

import signal
import atexit

# Worker heartbeat tracking
worker_heartbeats = {}
worker_start_times = {}
worker_failure_counts = {}

# Prometheus metrics for worker health
from prometheus_client import Gauge, Counter
worker_uptime_seconds = Gauge('worker_uptime_seconds', 'Worker uptime in seconds', ['worker'])
worker_failures_total = Counter('worker_failures_total', 'Total worker failures', ['worker'])
worker_last_heartbeat_timestamp = Gauge('worker_last_heartbeat_timestamp', 'Timestamp of last heartbeat', ['worker'])
worker_health_status = Gauge('worker_health_status', 'Worker health status (1=healthy, 0=unhealthy)', ['worker'])

# Twilio API health tracking
twilio_api_health_status = Gauge('twilio_api_health_status', 'Twilio API health (1=healthy, 0=unhealthy)')
twilio_api_failures_total = Counter('twilio_api_failures_total', 'Total Twilio API failures', ['error_type'])


def update_worker_heartbeat(worker_name):
    """Update heartbeat timestamp for a worker."""
    now = datetime.utcnow()
    worker_heartbeats[worker_name] = now
    worker_last_heartbeat_timestamp.labels(worker=worker_name).set(now.timestamp())
    worker_health_status.labels(worker=worker_name).set(1)  # Healthy


def check_worker_health():
    """
    Check if workers are alive based on heartbeat.

    Returns:
        dict: Worker health status
    """
    now = datetime.utcnow()
    health_report = {}

    for worker_name, last_heartbeat in worker_heartbeats.items():
        age_seconds = (now - last_heartbeat).total_seconds()
        is_healthy = age_seconds < 120  # 2 minutes without heartbeat = unhealthy

        health_report[worker_name] = {
            "healthy": is_healthy,
            "last_heartbeat": last_heartbeat.isoformat(),
            "age_seconds": age_seconds,
            "uptime_seconds": (now - worker_start_times.get(worker_name, now)).total_seconds(),
            "failure_count": worker_failure_counts.get(worker_name, 0)
        }

        # Update Prometheus metrics
        worker_health_status.labels(worker=worker_name).set(1 if is_healthy else 0)

        if not is_healthy:
            logger.error(f"Worker {worker_name} appears dead (no heartbeat for {age_seconds:.0f}s)")

    return health_report


def check_twilio_api_health():
    """
    Check Twilio API health by making a lightweight API call.

    Returns:
        bool: True if Twilio API is healthy
    """
    if not twilio_client:
        twilio_api_health_status.set(0)
        return False

    try:
        # Lightweight API call - fetch account info
        account = twilio_client.api.accounts(TWILIO_SID).fetch()
        if account.status == 'active':
            twilio_api_health_status.set(1)
            return True
        else:
            logger.warning(f"Twilio account status: {account.status}")
            twilio_api_health_status.set(0)
            twilio_api_failures_total.labels(error_type='account_inactive').inc()
            return False
    except Exception as e:
        logger.error(f"Twilio API health check failed: {str(e)}")
        twilio_api_health_status.set(0)
        twilio_api_failures_total.labels(error_type='api_error').inc()
        return False


def monitored_worker(worker_func, worker_name, restart_on_failure=True):
    """
    Wrapper for worker functions that adds health monitoring and auto-restart.

    Args:
        worker_func: The worker function to run
        worker_name: Name of the worker for logging/metrics
        restart_on_failure: Whether to restart worker on crash
    """
    import time

    worker_start_times[worker_name] = datetime.utcnow()
    worker_failure_counts[worker_name] = 0

    logger.info(f"Worker {worker_name} started with monitoring")

    while True:
        try:
            # Update heartbeat before running
            update_worker_heartbeat(worker_name)

            # Update uptime metric
            uptime = (datetime.utcnow() - worker_start_times[worker_name]).total_seconds()
            worker_uptime_seconds.labels(worker=worker_name).set(uptime)

            # Run the worker function
            worker_func()

        except Exception as e:
            worker_failure_counts[worker_name] = worker_failure_counts.get(worker_name, 0) + 1
            worker_failures_total.labels(worker=worker_name).inc()
            worker_health_status.labels(worker=worker_name).set(0)  # Mark unhealthy

            logger.error(f"Worker {worker_name} crashed: {str(e)}", exc_info=True)

            if not restart_on_failure:
                logger.error(f"Worker {worker_name} terminated (restart disabled)")
                break

            # Wait before restart to avoid rapid crash loops
            restart_delay = min(5 * worker_failure_counts[worker_name], 60)  # Max 60s
            logger.info(f"Restarting worker {worker_name} in {restart_delay}s...")
            time.sleep(restart_delay)

            # Reset start time on restart
            worker_start_times[worker_name] = datetime.utcnow()


# Background retry processor
def retry_processor_worker():
    """
    Background worker that processes the retry queue every 60 seconds.

    This runs in a separate thread and continuously checks for requests
    that are due for retry.
    """
    import time

    while True:
        try:
            process_retry_queue()
        except Exception as e:
            logger.error(f"Error in retry processor: {str(e)}", exc_info=True)
            raise  # Re-raise to trigger monitored_worker restart logic

        # Sleep for 60 seconds before next check
        time.sleep(60)


# Graceful shutdown handler
def graceful_shutdown(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    global shutdown_requested
    signal_name = signal.Signals(signum).name

    # UX Directive #6: Make shutdown felt, not just handled
    logger.warning("=" * 60)
    logger.warning(f"🛑 Received {signal_name}. Shutting down gracefully...")
    logger.warning("=" * 60)
    set_state(AppState.SHUTTING_DOWN)
    shutdown_requested = True

    # Stop scheduler
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("✓ Scheduler stopped")
    except Exception as e:
        logger.error(f"✗ Error stopping scheduler: {e}")

    # Log final worker health
    health_report = check_worker_health()
    logger.info(f"✓ Final worker health: {health_report}")

    # UX Directive #6: Confirm completion
    logger.warning("=" * 60)
    logger.warning("✅ Graceful shutdown complete")
    logger.warning("=" * 60)
    sys.exit(ExitCode.INTERRUPTED)


# Register signal handlers
signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

# Register cleanup on normal exit
atexit.register(lambda: logger.info("Application exiting"))


# Start background retry processor thread with monitoring
import threading
retry_thread = threading.Thread(
    target=lambda: monitored_worker(retry_processor_worker, "retry_processor", restart_on_failure=True),
    daemon=True
)
retry_thread.start()
if not QUIET:
    logger.info("Background retry processor thread started with health monitoring")


if __name__ == "__main__":
    try:
        set_state(AppState.STARTING)

        # UX Directive #5: --quiet suppresses startup banners
        if not QUIET:
            logger.info("=" * 60)
            logger.info("Starting Callback Service Backend")
            logger.info("=" * 60)
            logger.info(f"Frontend URL: {FRONTEND_URL}")
            logger.info(f"Database: {DATABASE_PATH}")
            logger.info(f"Twilio configured: {twilio_client is not None}")
            logger.info(f"Log level: {'DEBUG' if VERBOSE else 'WARNING' if QUIET else 'INFO'}")
            logger.info("=" * 60)

        set_state(AppState.READY)

        # UX Directive #6: Announce state transition explicitly
        if not QUIET:
            logger.info("✅ Application ready - listening on 0.0.0.0:8501")

        # Use waitress for production-ready WSGI server
        from waitress import serve
        serve(app, host="0.0.0.0", port=8501)
    except Exception as e:
        # UX Directive #3: Include last_action in crash reports
        logger.error(f"❌ Fatal error during {last_action}: {e}", exc_info=True)
        set_state(AppState.DEGRADED)
        sys.exit(ExitCode.RUNTIME_ERROR)


