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

// Backend detection state
let backendDetected = false;
let usingLocalBackend = false;

// DOM Elements
const statusEl = document.getElementById("status");
const form = document.getElementById("callbackForm");
const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const phoneInput = document.getElementById("phone");

// Logging utility
function log(level, message, data = {}) {
  const timestamp = new Date().toISOString();
  console[level](`[${timestamp}] ${message}`, data);
}

// Backend detection function
async function detectBackend() {
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
  statusEl.textContent = message;
  statusEl.style.display = 'block';
  
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

  log('info', 'Callback request submitted', { hasName: !!payload.name, hasEmail: !!payload.email, hasCaptcha: true });

  showStatus('info', '📞 Submitting callback request...');
  
  try {
    const res = await fetch(`${CONFIG.BACKEND_URL}/request_callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    const data = await res.json();
    
    if (data.success) {
      log('info', 'Callback request successful', { requestId: data.request_id });
      showStatus('success', '✓ Callback request received! Calling you now...');

      // Reset reCAPTCHA for next submission
      grecaptcha.reset();

      // Start polling for status updates
      if (data.request_id) {
        pollCallbackStatus(data.request_id);
      }
    } else {
      log('error', 'Callback request failed', { error: data.error });
      showStatus('error', data.error || 'Failed to submit callback request');

      // Reset reCAPTCHA on error so user can retry
      grecaptcha.reset();
    }
  } catch (err) {
    log('error', 'Network error during callback request', { error: err.message });
    showStatus('error', 'Network error. Please check your connection and try again.');

    // Reset reCAPTCHA on network error
    grecaptcha.reset();
  }
});

// Handle OAuth redirect with user data
const params = new URLSearchParams(window.location.search);
if (params.has("user")) {
  try {
    const userData = JSON.parse(atob(params.get("user")));
    autofill(userData);
    
    // Clean URL without reloading
    window.history.replaceState({}, document.title, window.location.pathname);
  } catch (error) {
    log('error', 'Failed to parse OAuth user data', { error: error.message });
  }
}

// Initialize backend detection on page load
(async function init() {
  log('info', 'Initializing callback form...');
  await detectBackend();
  log('info', 'Callback form initialized', {
    backendUrl: CONFIG.BACKEND_URL,
    backendDetected,
    usingLocalBackend
  });
})();

