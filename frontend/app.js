// Configuration
const CONFIG = {
  // Backend detection - tries localhost first, falls back to deployed backend
  BACKEND_URL: null, // Will be set after detection
  LOCAL_BACKEND: 'http://localhost:8501',
  DEPLOYED_BACKEND: 'https://api.swipswaps.com', // Hostname-based routing - separate subdomain
  POLL_INTERVAL: 2000, // Poll for status updates every 2 seconds
  MAX_POLLS: 30, // Stop polling after 60 seconds
  DETECTION_TIMEOUT: 3000 // 3 seconds to detect local backend
};

// Application state model (explicit state tracking for UX clarity)
const AppState = Object.freeze({
  INITIALIZING: 'initializing',
  DETECTING_BACKEND: 'detecting_backend',
  READY: 'ready',
  REQUESTING_CALLBACK: 'requesting_callback',
  VERIFYING: 'verifying',
  CALLING: 'calling',
  CONNECTED: 'connected',
  ERROR: 'error'
});

let currentAppState = AppState.INITIALIZING;
let lastAction = 'initializing';

// State management with logging and UI rendering (UX Directive #2)
function setState(state) {
  currentAppState = state;
  log('info', `STATE → ${state}`);

  // Render state visibly in UI
  renderStateIndicator(state);
}

function setAction(action) {
  lastAction = action;
  log('info', `ACTION → ${action}`);
}

// Assert expected state before allowing actions (UX Directive #1: Enforce FSM)
function assertState(expectedState, actionDescription) {
  if (currentAppState !== expectedState) {
    const errorMsg = `Cannot ${actionDescription}: Invalid state. Expected "${expectedState}", but current state is "${currentAppState}"`;
    log('error', errorMsg);
    showStatus('error', errorMsg);
    throw new Error(errorMsg);
  }
}

// Render state indicator in UI (UX Directive #2: Make state user-visible)
function renderStateIndicator(state) {
  const indicator = document.getElementById('app-state-indicator');
  const stateText = document.getElementById('app-state-text');

  if (!indicator || !stateText) return;

  // State descriptions for users
  const stateDescriptions = {
    [AppState.INITIALIZING]: '⏳ Initializing...',
    [AppState.DETECTING_BACKEND]: '🔍 Connecting to server...',
    [AppState.READY]: '✅ Ready',
    [AppState.REQUESTING_CALLBACK]: '📞 Submitting request...',
    [AppState.VERIFYING]: '🔐 Verifying...',
    [AppState.CALLING]: '📞 Calling you now...',
    [AppState.CONNECTED]: '✅ Connected',
    [AppState.ERROR]: '❌ Error'
  };

  stateText.textContent = stateDescriptions[state] || state;

  // Show indicator for non-ready states
  if (state === AppState.READY) {
    indicator.style.display = 'none';
  } else {
    indicator.style.display = 'block';

    // Color coding
    if (state === AppState.ERROR) {
      indicator.style.background = '#ffebee';
      indicator.style.borderLeftColor = '#f44336';
    } else if (state === AppState.CONNECTED) {
      indicator.style.background = '#e8f5e9';
      indicator.style.borderLeftColor = '#4caf50';
    } else {
      indicator.style.background = '#e7f3ff';
      indicator.style.borderLeftColor = '#2196F3';
    }
  }
}

// Backend detection state
let backendDetected = false;
let usingLocalBackend = false;

// User session state
let currentUser = null;

// DOM Elements
const statusEl = document.getElementById("status");
const form = document.getElementById("callbackForm");
const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const phoneInput = document.getElementById("phone");

// Verification elements
const verificationSection = document.getElementById("verification-section");
const verificationPhoneEl = document.getElementById("verification-phone");
const verificationCodeInput = document.getElementById("verification-code");
const verifyBtn = document.getElementById("verify-btn");
const resendBtn = document.getElementById("resend-btn");
const cancelVerificationBtn = document.getElementById("cancel-verification-btn");
const codeTimerEl = document.getElementById("code-timer");

// Verification state
let currentRequestId = null;
let verificationTimer = null;
let resendCooldown = null;
let isVerifying = false; // Prevent multiple simultaneous verification attempts

// Logging utility
function log(level, message, data = {}) {
  const timestamp = new Date().toISOString();
  console[level](`[${timestamp}] ${message}`, data);
}

// Backend detection function
async function detectBackend() {
  setState(AppState.DETECTING_BACKEND);
  setAction('detecting backend');
  log('info', 'Starting backend detection...');
  log('info', 'Current hostname:', { hostname: window.location.hostname });
  showBackendStatus('checking');

  // ALWAYS try localhost backend first (matches receipts-ocr pattern)
  log('info', 'Trying local backend first:', { url: CONFIG.LOCAL_BACKEND });
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.DETECTION_TIMEOUT);

    const response = await fetch(`${CONFIG.LOCAL_BACKEND}/health`, {
      method: 'GET',
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      if (data.status === 'healthy') {
        CONFIG.BACKEND_URL = CONFIG.LOCAL_BACKEND;
        usingLocalBackend = true;
        backendDetected = true;
        log('info', '✅ Local backend detected', { url: CONFIG.LOCAL_BACKEND });
        showBackendStatus('local');
        await checkTwilioConfiguration();
        setState(AppState.READY); // UX Directive #1: Set state to READY after successful detection
        return true;
      }
    }
  } catch (error) {
    log('warn', 'Local backend not available', { error: error.message });
  }

  // Fall back to deployed backend
  log('info', 'Trying deployed backend:', { url: CONFIG.DEPLOYED_BACKEND });
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000); // Longer timeout for production

    const response = await fetch(`${CONFIG.DEPLOYED_BACKEND}/health`, {
      method: 'GET',
      signal: controller.signal,
      headers: { 'Accept': 'application/json' },
      cache: 'no-store'
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      if (data.status === 'healthy') {
        CONFIG.BACKEND_URL = CONFIG.DEPLOYED_BACKEND;
        usingLocalBackend = false;
        backendDetected = true;
        log('info', '✅ Deployed backend detected', { url: CONFIG.DEPLOYED_BACKEND, data });
        showBackendStatus('deployed');
        setState(AppState.READY); // UX Directive #1: Set state to READY after successful detection
        return true;
      } else {
        throw new Error(`Backend unhealthy: ${data.status}`);
      }
    } else {
      throw new Error(`Backend returned ${response.status}`);
    }
  } catch (error) {
    log('error', 'Deployed backend not available', { error: error.message });
  }

  // No backend available
  CONFIG.BACKEND_URL = null;
  backendDetected = false;
  log('error', '❌ No backend detected');
  showBackendStatus('none');
  setState(AppState.ERROR); // UX Directive #1: Set state to ERROR if no backend detected
  return false;
}

// Check if Twilio is configured
async function checkTwilioConfiguration() {
  try {
    const response = await fetch(`${CONFIG.BACKEND_URL}/health`);
    const data = await response.json();

    const setupNotice = document.getElementById('setup-wizard-notice');
    if (setupNotice) {
      if (data.twilio_configured === false) {
        setupNotice.style.display = 'block';
        log('warn', 'Twilio not configured - showing setup wizard notice');
      } else {
        setupNotice.style.display = 'none';
        log('info', 'Twilio is configured');
      }
    }
  } catch (error) {
    log('warn', 'Could not check Twilio configuration', { error: error.message });
  }
}

// Show backend status in UI
function showBackendStatus(status) {
  const statusContainer = document.getElementById('backend-status');
  if (!statusContainer) return;

  const statusMessages = {
    'checking': {
      icon: '🔄',
      text: 'Checking backend connection...',
      class: 'status-checking'
    },
    'local': {
      icon: '🟢',
      text: 'Connected to local backend (http://localhost:8501)',
      class: 'status-success'
    },
    'deployed': {
      icon: '🌐',
      text: 'Connected to deployed backend',
      class: 'status-success'
    },
    'none': {
      icon: '🔴',
      text: 'Backend not available - Form submissions will fail',
      class: 'status-error'
    }
  };

  const msg = statusMessages[status];
  statusContainer.innerHTML = `
    <div class="backend-status ${msg.class}">
      <span class="status-icon">${msg.icon}</span>
      <span class="status-text">${msg.text}</span>
      ${status === 'none' ? '<button onclick="window.detectBackend()" class="retry-btn">Retry Connection</button>' : ''}
    </div>
  `;
  statusContainer.style.display = 'block';
}

// Make detectBackend available globally for retry button
window.detectBackend = detectBackend;

// Social login handlers
document.querySelectorAll(".social-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const provider = btn.dataset.provider;
    log('info', `Social login initiated: ${provider}`);

    try {
      // OAuth always uses deployed backend (requires consistent redirect URL)
      // Try local backend first, fall back to deployed
      const oauthBackend = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? CONFIG.LOCAL_BACKEND
        : CONFIG.DEPLOYED_BACKEND;

      log('info', `Using OAuth backend: ${oauthBackend}`);
      window.location.href = `${oauthBackend}/oauth/login/${provider}`;
    } catch (error) {
      log('error', 'Social login failed', { provider, error: error.message });
      showStatus('error', `Failed to connect to ${provider}. Please try again.`);
    }
  });
});

// Autofill function
function autofill(user) {
  log('info', 'Autofilling user data', { hasName: !!user.name, hasEmail: !!user.email, hasPhone: !!user.phone });
  
  if (user.name) {
    nameInput.value = user.name;
    nameInput.classList.add('autofilled');
  }
  if (user.email) {
    emailInput.value = user.email;
    emailInput.classList.add('autofilled');
  }
  if (user.phone) {
    phoneInput.value = user.phone;
    phoneInput.classList.add('autofilled');
  }
  
  // Show success message
  if (user.name || user.email || user.phone) {
    showStatus('success', '✓ Your details have been auto-filled. Please verify and submit.');
  }
}

// Status display function
function showStatus(type, message) {
  statusEl.className = `status-message ${type}`;
  statusEl.innerHTML = message;
  statusEl.style.display = 'block';

  // Enhanced logging with stack trace to identify source of mystery errors
  const timestamp = new Date().toISOString();
  const stack = new Error().stack;
  console.log(`[${timestamp}] Status shown: ${type} "${message}"`);

  // If it's an error message, log the full stack trace to identify the source
  if (type === 'error') {
    console.log('[STATUS ERROR TRACE] Full stack trace:', stack);
  }

  log('info', `Status shown: ${type}`, { message });
}

// Clear status
function clearStatus() {
  statusEl.style.display = 'none';
  statusEl.className = 'status-message';
  statusEl.textContent = '';
}

// Poll for callback status
async function pollCallbackStatus(requestId, pollCount = 0) {
  if (pollCount >= CONFIG.MAX_POLLS) {
    log('warn', 'Polling timeout reached', { requestId });
    showStatus('info', 'Your callback request is being processed. We\'ll contact you shortly.');
    return;
  }

  try {
    const res = await fetch(`${CONFIG.BACKEND_URL}/status/${requestId}`);
    const data = await res.json();
    
    log('info', 'Status poll result', { requestId, status: data.status, pollCount });
    
    if (data.status === 'completed') {
      showStatus('success', '✓ Callback completed! Check your phone.');
    } else if (data.status === 'failed') {
      showStatus('error', `Callback failed: ${data.message || 'Unknown error'}`);
    } else if (data.status === 'sms_sent') {
      showStatus('info', 'We missed you! Check your SMS for our contact details.');
    } else {
      // Continue polling
      setTimeout(() => pollCallbackStatus(requestId, pollCount + 1), CONFIG.POLL_INTERVAL);
    }
  } catch (error) {
    log('error', 'Status polling failed', { requestId, error: error.message });
    // Continue polling despite errors
    setTimeout(() => pollCallbackStatus(requestId, pollCount + 1), CONFIG.POLL_INTERVAL);
  }
}

// Form submission handler
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  // UX Directive #1: Assert state before allowing action
  try {
    assertState(AppState.READY, 'submit callback request');
  } catch (error) {
    return; // Error already shown to user
  }

  // Get reCAPTCHA response token
  const recaptchaResponse = grecaptcha.getResponse();

  if (!recaptchaResponse) {
    showStatus('error', 'Please complete the CAPTCHA verification');
    log('warn', 'CAPTCHA not completed');
    return;
  }

  // Get honeypot field value (should be empty for legitimate users)
  const websiteInput = document.getElementById('website');

  const payload = {
    name: nameInput.value.trim(),
    email: emailInput.value.trim(),
    visitor_number: phoneInput.value.trim(),
    recaptcha_token: recaptchaResponse,
    website: websiteInput ? websiteInput.value.trim() : ''  // Honeypot field
  };

  // Validation
  if (!payload.visitor_number) {
    showStatus('error', 'Please enter your phone number');
    phoneInput.focus();
    return;
  }

  setState(AppState.REQUESTING_CALLBACK);
  setAction('requesting callback');
  log('info', 'Callback request submitted', { hasName: !!payload.name, hasEmail: !!payload.email, hasCaptcha: true });

  showStatus('info', '📞 Submitting callback request...');

  try {
    // Step 1: Submit callback request (does NOT initiate call yet)
    const res = await fetch(`${CONFIG.BACKEND_URL}/request_callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.success) {
      log('info', 'Callback request successful', { requestId: data.request_id });
      currentRequestId = data.request_id;

      // Reset reCAPTCHA
      grecaptcha.reset();

      // Step 2: Send SMS verification code
      await sendVerificationCode(data.request_id, payload.visitor_number);
    } else {
      log('error', 'Callback request failed', { error: data.error });

      // UX Directive #3: Display last_action context from backend
      let errorMessage = data.error || 'Failed to submit callback request';
      if (data.context) {
        errorMessage = `${data.context}: ${errorMessage}`;
      }
      if (data.next_step) {
        errorMessage += ` ${data.next_step}`;
      }

      showStatus('error', errorMessage);
      setState(AppState.ERROR);

      // Reset reCAPTCHA on error so user can retry
      grecaptcha.reset();
    }
  } catch (err) {
    log('error', 'Network error during callback request', { error: err.message });
    showStatus('error', 'Network error. Please check your connection and try again.');
    setState(AppState.ERROR);

    // Reset reCAPTCHA on network error
    grecaptcha.reset();
  }
});

// Verification functions
async function sendVerificationCode(requestId, phone) {
  try {
    showStatus('info', '📱 Sending verification code to your phone...');

    const res = await fetch(`${CONFIG.BACKEND_URL}/send_verification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: requestId })
    });

    const data = await res.json();

    if (data.success) {
      log('info', 'Verification code sent', { requestId });
      showVerificationUI(phone);
      showStatus('success', '✓ Verification code sent! Check your phone.');
      startVerificationTimer();
    } else {
      log('error', 'Failed to send verification code', { error: data.error });
      showStatus('error', data.error || 'Failed to send verification code');
    }
  } catch (err) {
    log('error', 'Network error sending verification code', { error: err.message });
    showStatus('error', 'Network error. Please try again.');
  }
}

function showVerificationUI(phone) {
  // Hide form, show verification section
  form.style.display = 'none';
  verificationSection.style.display = 'block';
  verificationPhoneEl.textContent = phone;
  verificationCodeInput.value = '';
  verificationCodeInput.focus();
  isVerifying = false; // Reset verification flag for new verification flow
}

function hideVerificationUI() {
  // Show form, hide verification section
  form.style.display = 'block';
  verificationSection.style.display = 'none';
  currentRequestId = null;
  stopVerificationTimer();
  isVerifying = false; // Reset verification flag
}

function startVerificationTimer() {
  let timeLeft = 600; // 10 minutes in seconds

  function updateTimer() {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    codeTimerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    if (timeLeft <= 0) {
      clearInterval(verificationTimer);
      codeTimerEl.textContent = 'EXPIRED';
      codeTimerEl.style.color = 'var(--error-color)';
      verifyBtn.disabled = true;
    } else {
      timeLeft--;
    }
  }

  updateTimer();
  verificationTimer = setInterval(updateTimer, 1000);
}

function stopVerificationTimer() {
  if (verificationTimer) {
    clearInterval(verificationTimer);
    verificationTimer = null;
  }
  if (resendCooldown) {
    clearTimeout(resendCooldown);
    resendCooldown = null;
  }
}

async function verifyCode() {
  console.log('[AUTO-VERIFY DEBUG] verifyCode() called!');

  // Prevent multiple simultaneous verification attempts
  if (isVerifying) {
    console.log('[AUTO-VERIFY DEBUG] Already verifying, skipping duplicate call');
    return;
  }

  // Set flag IMMEDIATELY to prevent race condition
  isVerifying = true;
  console.log('[AUTO-VERIFY DEBUG] isVerifying flag set to true');

  const code = verificationCodeInput.value.trim();
  console.log('[AUTO-VERIFY DEBUG] Code value:', code, 'length:', code.length);

  if (!code || code.length !== 6) {
    console.log('[AUTO-VERIFY DEBUG] Validation failed - code length not 6');
    showStatus('error', 'Please enter a 6-digit verification code');
    isVerifying = false; // Reset flag since we're not proceeding
    return;
  }

  console.log('[AUTO-VERIFY DEBUG] Validation passed, proceeding with verification...');

  setState(AppState.VERIFYING);
  setAction('verifying code');

  try {
    console.log('[AUTO-VERIFY DEBUG] Starting verification request...');
    showStatus('info', '🔍 Verifying code...');
    verifyBtn.disabled = true;

    const requestStartTime = Date.now();
    console.log('[AUTO-VERIFY DEBUG] Sending POST to /verify_code at', new Date().toISOString());

    const res = await fetch(`${CONFIG.BACKEND_URL}/verify_code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: currentRequestId,
        code: code
      })
    });

    const requestEndTime = Date.now();
    console.log('[AUTO-VERIFY DEBUG] Response received in', requestEndTime - requestStartTime, 'ms, status:', res.status);

    const data = await res.json();
    console.log('[AUTO-VERIFY DEBUG] Response data:', JSON.stringify(data));

    if (data.success) {
      console.log('[AUTO-VERIFY DEBUG] Verification SUCCESS!');
      log('info', 'Verification successful', { requestId: currentRequestId });
      showStatus('success', '✓ Verified! Initiating callback...');
      stopVerificationTimer();

      // Step 3: Initiate the actual callback
      console.log('[AUTO-VERIFY DEBUG] Calling initiateCallback()...');
      await initiateCallback(currentRequestId);
      console.log('[AUTO-VERIFY DEBUG] initiateCallback() completed');
      // Note: isVerifying flag is NOT reset here because we don't want duplicate verifications
      // It will be reset when the user starts a new callback request
    } else {
      console.log('[AUTO-VERIFY DEBUG] Verification FAILED! Error:', data.error);
      log('error', 'Verification failed', { error: data.error });

      // UX Directive #3: Display last_action context from backend
      let errorMessage = data.error || 'Invalid verification code';
      if (data.context) {
        errorMessage = `${data.context}: ${errorMessage}`;
      }
      if (data.next_step) {
        errorMessage += ` ${data.next_step}`;
      }

      showStatus('error', errorMessage);
      setState(AppState.ERROR);
      verifyBtn.disabled = false;
      isVerifying = false; // Reset flag on error so user can retry
    }
  } catch (err) {
    console.log('[AUTO-VERIFY DEBUG] Network error:', err.message);
    log('error', 'Network error during verification', { error: err.message });
    showStatus('error', 'Network error. Please try again.');
    verifyBtn.disabled = false;
    isVerifying = false; // Reset flag on error so user can retry
  }
}

async function initiateCallback(requestId) {
  setState(AppState.CALLING);
  setAction('initiating callback');

  try {
    showStatus('info', '📞 Calling you now...');

    const res = await fetch(`${CONFIG.BACKEND_URL}/initiate_callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: requestId })
    });

    const data = await res.json();

    if (data.success) {
      log('info', 'Callback initiated', { requestId });
      showStatus('success', '✓ Calling you now! Please answer your phone.');
      setState(AppState.CONNECTED);
      hideVerificationUI();

      // Start polling for status updates
      pollCallbackStatus(requestId);
    } else {
      log('error', 'Failed to initiate callback', { error: data.error });

      // UX Directive #3: Display last_action context from backend
      let errorMessage = data.error || 'Failed to initiate callback';
      if (data.context) {
        errorMessage = `${data.context}: ${errorMessage}`;
      }
      if (data.next_step) {
        errorMessage += ` ${data.next_step}`;
      }

      showStatus('error', errorMessage);
      setState(AppState.ERROR);
    }
  } catch (err) {
    log('error', 'Network error initiating callback', { error: err.message });
    showStatus('error', 'Network error. Please try again.');
    setState(AppState.ERROR);
  }
}

async function resendVerificationCode() {
  if (!currentRequestId) return;

  resendBtn.disabled = true;
  await sendVerificationCode(currentRequestId, verificationPhoneEl.textContent);

  // Cooldown before allowing resend again (30 seconds)
  let cooldown = 30;
  resendBtn.textContent = `🔄 Resend Code (${cooldown}s)`;

  resendCooldown = setInterval(() => {
    cooldown--;
    if (cooldown <= 0) {
      clearInterval(resendCooldown);
      resendBtn.disabled = false;
      resendBtn.textContent = '🔄 Resend Code';
    } else {
      resendBtn.textContent = `🔄 Resend Code (${cooldown}s)`;
    }
  }, 1000);
}

// Note: Duplicate request handling removed - backend now auto-cancels old requests

// Event listeners for verification
verifyBtn.addEventListener('click', verifyCode);
resendBtn.addEventListener('click', resendVerificationCode);
cancelVerificationBtn.addEventListener('click', hideVerificationUI);

// Allow Enter key to submit verification code
verificationCodeInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    verifyCode();
  }
});

// Auto-format verification code input (numeric only) and auto-verify when 6 digits entered
console.log('[AUTO-VERIFY DEBUG] Attaching keyup event listener to verificationCodeInput:', verificationCodeInput);
if (verificationCodeInput) {
  verificationCodeInput.addEventListener('keyup', (e) => {
    console.log('[AUTO-VERIFY DEBUG] Keyup event fired, value:', e.target.value);
    e.target.value = e.target.value.replace(/[^0-9]/g, '');
    console.log('[AUTO-VERIFY DEBUG] After sanitization, value:', e.target.value, 'length:', e.target.value.length);

    // Auto-verify when 6 digits are entered
    if (e.target.value.length === 6) {
      console.log('[AUTO-VERIFY DEBUG] 6 digits detected! Calling verifyCode()...');
      verifyCode();
    }
  });
  console.log('[AUTO-VERIFY DEBUG] Keyup event listener attached successfully!');
} else {
  console.error('[AUTO-VERIFY DEBUG] ERROR: verificationCodeInput is null! Cannot attach event listener.');
}

// Authentication functions
function saveUserSession(userData) {
  sessionStorage.setItem('user', JSON.stringify(userData));
  currentUser = userData;
  log('info', 'User session saved', { user: userData.name });
}

function loadUserSession() {
  const stored = sessionStorage.getItem('user');
  if (stored) {
    try {
      currentUser = JSON.parse(stored);
      log('info', 'User session loaded', { user: currentUser.name });
      return currentUser;
    } catch (error) {
      log('error', 'Failed to load user session', { error: error.message });
      sessionStorage.removeItem('user');
    }
  }
  return null;
}

function clearUserSession() {
  sessionStorage.removeItem('user');
  currentUser = null;
  log('info', 'User session cleared');
}

function showAuthenticatedUI() {
  document.getElementById('auth-required').style.display = 'none';
  document.getElementById('user-profile').style.display = 'block';
  document.getElementById('callbackForm').style.display = 'block';

  // Update profile display
  document.getElementById('profile-name').textContent = currentUser.name || 'User';
  document.getElementById('profile-email').textContent = currentUser.email || '';

  // Show authenticated instructions
  const authInstructions = document.getElementById('instructions-authenticated');
  const unauthInstructions = document.getElementById('instructions-unauthenticated');
  if (authInstructions) authInstructions.style.display = 'block';
  if (unauthInstructions) unauthInstructions.style.display = 'none';

  // Autofill form
  autofill(currentUser);

  log('info', '✅ Authenticated UI shown - user can now request callback');
  log('info', `👤 User: ${currentUser.name} <${currentUser.email}>`);
}

function showUnauthenticatedUI() {
  document.getElementById('auth-required').style.display = 'block';
  document.getElementById('user-profile').style.display = 'none';
  document.getElementById('callbackForm').style.display = 'none';

  // Show unauthenticated instructions
  const authInstructions = document.getElementById('instructions-authenticated');
  const unauthInstructions = document.getElementById('instructions-unauthenticated');
  if (authInstructions) authInstructions.style.display = 'none';
  if (unauthInstructions) unauthInstructions.style.display = 'block';

  log('info', '🔒 Unauthenticated UI shown - OAuth required');
}

// Handle OAuth redirect with user data
const params = new URLSearchParams(window.location.search);
if (params.has("user")) {
  try {
    const userData = JSON.parse(atob(params.get("user")));
    saveUserSession(userData);
    showAuthenticatedUI();

    // Clean URL without reloading
    window.history.replaceState({}, document.title, window.location.pathname);
  } catch (error) {
    log('error', 'Failed to parse OAuth user data', { error: error.message });
  }
}

// Logout handler
const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    clearUserSession();
    showUnauthenticatedUI();
    showStatus('info', 'You have been signed out');
  });
}

// Initialize backend detection and auth state on page load
(async function init() {
  log('info', 'Initializing callback form...');
  await detectBackend();

  // Check for existing session
  const user = loadUserSession();
  if (user) {
    showAuthenticatedUI();
  } else {
    showUnauthenticatedUI();
  }

  log('info', 'Callback form initialized', {
    backendUrl: CONFIG.BACKEND_URL,
    backendDetected,
    usingLocalBackend,
    authenticated: !!currentUser
  });
})();

// Settings Modal and Log Viewer
(function initSettingsModal() {
  const settingsBtn = document.getElementById('settings-btn');
  const modal = document.getElementById('settings-modal');
  const closeBtn = document.getElementById('close-modal');
  const refreshBtn = document.getElementById('refresh-logs');
  const logOutput = document.getElementById('log-output');
  const logStatus = document.getElementById('log-status');
  const autoRefreshCheckbox = document.getElementById('auto-refresh-logs');

  let autoRefreshInterval = null;

  // Open modal
  settingsBtn.addEventListener('click', () => {
    modal.classList.add('show');
    fetchLogs();
  });

  // Close modal
  closeBtn.addEventListener('click', () => {
    modal.classList.remove('show');
    if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = null;
      autoRefreshCheckbox.checked = false;
    }
  });

  // Close on outside click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('show');
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        autoRefreshCheckbox.checked = false;
      }
    }
  });

  // Refresh logs
  refreshBtn.addEventListener('click', fetchLogs);

  // Auto-refresh toggle
  autoRefreshCheckbox.addEventListener('change', (e) => {
    if (e.target.checked) {
      autoRefreshInterval = setInterval(fetchLogs, 10000);
    } else {
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
      }
    }
  });

  // Fetch logs function
  async function fetchLogs() {
    const lines = document.getElementById('log-lines').value;
    const filter = document.getElementById('log-filter').value;

    refreshBtn.disabled = true;
    refreshBtn.textContent = '⏳ Loading...';

    try {
      const params = new URLSearchParams({ lines });
      if (filter) params.append('filter', filter);

      const response = await fetch(`${CONFIG.BACKEND_URL}/logs?${params}`);
      const data = await response.json();

      if (data.success) {
        logOutput.value = data.logs || 'No logs available';
        logStatus.className = 'success';
        logStatus.textContent = `✓ Loaded ${data.lines_returned} of ${data.total_lines_in_file} lines (filter: ${data.filter})`;
      } else {
        logOutput.value = `Error: ${data.error}`;
        logStatus.className = 'error';
        logStatus.textContent = `✗ Failed: ${data.error}`;
      }
    } catch (error) {
      logOutput.value = `Error fetching logs: ${error.message}`;
      logStatus.className = 'error';
      logStatus.textContent = `✗ Error: ${error.message}`;
    } finally {
      refreshBtn.disabled = false;
      refreshBtn.textContent = '🔄 Refresh';
    }
  }
})();

