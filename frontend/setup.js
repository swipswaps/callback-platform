/**
 * Twilio Setup Wizard
 * Guides users through Twilio configuration step-by-step
 */

let currentStep = 1;
const totalSteps = 6;

// Configuration data
const config = {
  twilioSid: '',
  twilioAuthToken: '',
  twilioNumber: '',
  businessNumber: ''
};

// DOM Elements
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const steps = document.querySelectorAll('.wizard-step');
const stepItems = document.querySelectorAll('.step-item');

// Show/hide auth token
const showAuthTokenCheckbox = document.getElementById('showAuthToken');
if (showAuthTokenCheckbox) {
  showAuthTokenCheckbox.addEventListener('change', (e) => {
    const authTokenInput = document.getElementById('twilioAuthToken');
    authTokenInput.type = e.target.checked ? 'text' : 'password';
  });
}

// Navigation
prevBtn.addEventListener('click', () => {
  if (currentStep > 1) {
    goToStep(currentStep - 1);
  }
});

nextBtn.addEventListener('click', () => {
  if (validateCurrentStep()) {
    if (currentStep < totalSteps) {
      goToStep(currentStep + 1);
    } else {
      saveConfiguration();
    }
  }
});

function goToStep(step) {
  // Hide all steps
  steps.forEach(s => s.classList.remove('active'));
  stepItems.forEach(s => s.classList.remove('active'));
  
  // Show target step
  const targetStep = document.querySelector(`.wizard-step[data-step="${step}"]`);
  const targetStepItem = document.querySelector(`.step-item[data-step="${step}"]`);
  
  if (targetStep) targetStep.classList.add('active');
  if (targetStepItem) targetStepItem.classList.add('active');
  
  // Mark completed steps
  stepItems.forEach((item, index) => {
    if (index < step - 1) {
      item.classList.add('completed');
    } else {
      item.classList.remove('completed');
    }
  });
  
  currentStep = step;
  
  // Update buttons
  prevBtn.style.display = currentStep > 1 ? 'block' : 'none';
  nextBtn.textContent = currentStep === totalSteps ? 'Save Configuration' : 'Next →';
  
  // Update review on last step
  if (currentStep === totalSteps) {
    updateReview();
  }
}

function validateCurrentStep() {
  switch (currentStep) {
    case 1:
    case 2:
      return true; // No validation needed for welcome/account creation
      
    case 3:
      // Validate credentials
      const sid = document.getElementById('twilioSid').value.trim();
      const authToken = document.getElementById('twilioAuthToken').value.trim();
      
      if (!sid || !authToken) {
        alert('Please enter both Account SID and Auth Token');
        return false;
      }
      
      if (!sid.startsWith('AC') || sid.length !== 34) {
        alert('Account SID should start with "AC" and be 34 characters long');
        return false;
      }
      
      config.twilioSid = sid;
      config.twilioAuthToken = authToken;
      return true;
      
    case 4:
      // Validate Twilio number
      const twilioNumber = document.getElementById('twilioNumber').value.trim();
      
      if (!twilioNumber) {
        alert('Please enter your Twilio phone number');
        return false;
      }
      
      if (!twilioNumber.startsWith('+')) {
        alert('Phone number must include country code (e.g., +15551234567)');
        return false;
      }
      
      config.twilioNumber = twilioNumber;
      return true;
      
    case 5:
      // Validate business number
      const businessNumber = document.getElementById('businessNumber').value.trim();
      
      if (!businessNumber) {
        alert('Please enter your business phone number');
        return false;
      }
      
      if (!businessNumber.startsWith('+')) {
        alert('Phone number must include country code (e.g., +15557654321)');
        return false;
      }
      
      config.businessNumber = businessNumber;
      return true;
      
    case 6:
      return true; // Review step
      
    default:
      return true;
  }
}

function updateReview() {
  document.getElementById('reviewSid').textContent = config.twilioSid || '-';
  document.getElementById('reviewAuthToken').textContent = '••••••••' + (config.twilioAuthToken.slice(-4) || '');
  document.getElementById('reviewTwilioNumber').textContent = config.twilioNumber || '-';
  document.getElementById('reviewBusinessNumber').textContent = config.businessNumber || '-';
}

async function saveConfiguration() {
  const saveStatus = document.getElementById('saveStatus');
  saveStatus.innerHTML = '<p style="color: #007bff;">⏳ Saving configuration...</p>';
  nextBtn.disabled = true;

  try {
    // Detect backend URL
    const backendUrl = await detectBackend();

    if (!backendUrl) {
      throw new Error('Backend not available. Please start the backend server first.');
    }

    // Send configuration to backend
    const response = await fetch(`${backendUrl}/api/configure`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        TWILIO_SID: config.twilioSid,
        TWILIO_AUTH_TOKEN: config.twilioAuthToken,
        TWILIO_NUMBER: config.twilioNumber,
        BUSINESS_NUMBER: config.businessNumber,
        FRONTEND_URL: window.location.origin,
        RECAPTCHA_SECRET: '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe' // Test key
      })
    });

    const result = await response.json();

    if (result.success) {
      saveStatus.innerHTML = `
        <div style="background: #d4edda; border-left: 4px solid #28a745; padding: 16px; border-radius: 4px;">
          <h3 style="color: #155724; margin-top: 0;">✅ Configuration Saved Successfully!</h3>
          <p style="color: #155724;">Your Twilio credentials have been configured.</p>
          <p style="color: #155724;"><strong>Next steps:</strong></p>
          <ol style="color: #155724;">
            <li>Restart your backend server to apply changes</li>
            <li>Go to the <a href="index.html">callback form</a> to test</li>
            <li>Submit a test callback request</li>
          </ol>
          <a href="index.html" style="display: inline-block; margin-top: 10px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 4px;">
            Go to Callback Form →
          </a>
        </div>
      `;
    } else {
      throw new Error(result.error || 'Failed to save configuration');
    }
  } catch (error) {
    console.error('Configuration save error:', error);
    saveStatus.innerHTML = `
      <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 16px; border-radius: 4px;">
        <h3 style="color: #721c24; margin-top: 0;">❌ Configuration Failed</h3>
        <p style="color: #721c24;"><strong>Error:</strong> ${error.message}</p>
        <p style="color: #721c24;"><strong>Manual Setup:</strong></p>
        <ol style="color: #721c24;">
          <li>Create a file named <code>.env</code> in your project root</li>
          <li>Copy the contents from <code>.env.example</code></li>
          <li>Replace the placeholder values with your credentials</li>
          <li>Restart your backend server</li>
        </ol>
        <button onclick="downloadEnvFile()" style="margin-top: 10px; padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
          Download .env File
        </button>
      </div>
    `;
    nextBtn.disabled = false;
  }
}

async function detectBackend() {
  // Try local backend first
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch('http://localhost:8501/health', {
      method: 'HEAD',
      mode: 'no-cors',
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    return 'http://localhost:8501';
  } catch (error) {
    console.log('Local backend not available');
    return null;
  }
}

function downloadEnvFile() {
  const envContent = `# Callback Service Environment Configuration
# Generated by Twilio Setup Wizard

# ============================================================
# TWILIO CONFIGURATION
# ============================================================
TWILIO_SID=${config.twilioSid}
TWILIO_AUTH_TOKEN=${config.twilioAuthToken}
TWILIO_NUMBER=${config.twilioNumber}

# ============================================================
# BUSINESS CONFIGURATION
# ============================================================
BUSINESS_NUMBER=${config.businessNumber}

# ============================================================
# FRONTEND CONFIGURATION
# ============================================================
FRONTEND_URL=${window.location.origin}
ALLOWED_ORIGINS=${window.location.origin}

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
DATABASE_PATH=/tmp/callbacks.db

# ============================================================
# RECAPTCHA CONFIGURATION
# ============================================================
RECAPTCHA_SECRET=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe

# ============================================================
# BUSINESS HOURS CONFIGURATION
# ============================================================
BUSINESS_HOURS_START=09:00
BUSINESS_HOURS_END=17:00
BUSINESS_TIMEZONE=America/New_York
BUSINESS_WEEKDAYS_ONLY=true
`;

  const blob = new Blob([envContent], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = '.env';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  alert('.env file downloaded! Place it in your project root directory and restart the backend.');
}

// Initialize wizard
console.log('Twilio Setup Wizard initialized');
goToStep(1);

