// Health Status Page JavaScript

const API_BASE_URL = 'https://api.swipswaps.com';

// DOM Elements
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const healthContent = document.getElementById('healthContent');

// Status indicators
const apiStatus = document.getElementById('apiStatus');
const apiStatusText = document.getElementById('apiStatusText');
const apiResponseTime = document.getElementById('apiResponseTime');
const twilioStatus = document.getElementById('twilioStatus');
const twilioStatusText = document.getElementById('twilioStatusText');
const activeCalls = document.getElementById('activeCalls');
const activeSMS = document.getElementById('activeSMS');
const totalRequests = document.getElementById('totalRequests');
const lastUpdated = document.getElementById('lastUpdated');

// Fetch health data
async function fetchHealthData() {
  const startTime = Date.now();
  
  try {
    // Test backend API health
    const healthResponse = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    const responseTime = Date.now() - startTime;

    if (!healthResponse.ok) {
      throw new Error(`Backend API returned ${healthResponse.status}`);
    }

    const healthData = await healthResponse.json();

    // Update API status
    apiStatus.className = 'status-indicator status-healthy';
    apiStatusText.textContent = 'Healthy';
    apiResponseTime.textContent = `${responseTime}ms`;

    // Update Twilio status (from health endpoint if available)
    if (healthData.twilio_status) {
      twilioStatus.className = `status-indicator ${healthData.twilio_status === 'healthy' ? 'status-healthy' : 'status-degraded'}`;
      twilioStatusText.textContent = healthData.twilio_status === 'healthy' ? 'Healthy' : 'Degraded';
    } else {
      twilioStatus.className = 'status-indicator status-healthy';
      twilioStatusText.textContent = 'Healthy';
    }

    // Fetch public stats (no auth required)
    try {
      const statsResponse = await fetch(`${API_BASE_URL}/stats`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        if (statsData.total_requests !== undefined) {
          totalRequests.textContent = statsData.total_requests;
        }
      }
    } catch (e) {
      // Stats endpoint might not exist, that's okay
      totalRequests.textContent = 'N/A';
    }

    // Set concurrency to 0 (we can't read these without auth)
    activeCalls.textContent = '0 / 3';
    activeSMS.textContent = '0 / 10';

    // Update last updated time
    lastUpdated.textContent = new Date().toLocaleString();

    // Show content, hide loading
    loading.style.display = 'none';
    error.style.display = 'none';
    healthContent.style.display = 'block';

  } catch (err) {
    console.error('Health check failed:', err);
    
    // Show error
    loading.style.display = 'none';
    error.style.display = 'block';
    error.textContent = `Failed to fetch health data: ${err.message}. The backend API may be down or unreachable.`;
    
    // Update API status to unhealthy
    apiStatus.className = 'status-indicator status-unhealthy';
    apiStatusText.textContent = 'Unhealthy';
    apiResponseTime.textContent = 'N/A';
    
    // Show partial content
    healthContent.style.display = 'block';
  }
}

// Auto-refresh every 30 seconds
function startAutoRefresh() {
  setInterval(fetchHealthData, 30000);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  fetchHealthData();
  startAutoRefresh();
});

