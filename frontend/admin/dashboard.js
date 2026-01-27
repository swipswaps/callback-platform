// Admin Dashboard JavaScript

const API_BASE_URL = 'https://api.swipswaps.com';

// State
let apiToken = '';
let currentOffset = 0;
let currentLimit = 50;
let currentFilters = {
  status: '',
  phone: ''
};

// DOM Elements
const authSection = document.getElementById('authSection');
const dashboardContent = document.getElementById('dashboardContent');
const apiTokenInput = document.getElementById('apiToken');
const loginBtn = document.getElementById('loginBtn');
const authError = document.getElementById('authError');
const refreshBtn = document.getElementById('refreshBtn');
const lastUpdated = document.getElementById('lastUpdated');

// Stats elements
const totalRequests = document.getElementById('totalRequests');
const successRate = document.getElementById('successRate');
const last24h = document.getElementById('last24h');
const pendingCount = document.getElementById('pendingCount');
const completedCount = document.getElementById('completedCount');
const failedCount = document.getElementById('failedCount');

// Filter elements
const statusFilter = document.getElementById('statusFilter');
const phoneFilter = document.getElementById('phoneFilter');
const limitFilter = document.getElementById('limitFilter');
const applyFiltersBtn = document.getElementById('applyFiltersBtn');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');

// Requests elements
const requestsLoading = document.getElementById('requestsLoading');
const requestsError = document.getElementById('requestsError');
const requestsTableContainer = document.getElementById('requestsTableContainer');
const requestsTableBody = document.getElementById('requestsTableBody');
const prevPageBtn = document.getElementById('prevPageBtn');
const nextPageBtn = document.getElementById('nextPageBtn');
const paginationInfo = document.getElementById('paginationInfo');

// Event Listeners
loginBtn.addEventListener('click', handleLogin);
apiTokenInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleLogin();
});
refreshBtn.addEventListener('click', refreshDashboard);
applyFiltersBtn.addEventListener('click', applyFilters);
clearFiltersBtn.addEventListener('click', clearFilters);
prevPageBtn.addEventListener('click', () => changePage(-1));
nextPageBtn.addEventListener('click', () => changePage(1));

// Check if token is stored in localStorage
window.addEventListener('DOMContentLoaded', () => {
  const storedToken = localStorage.getItem('adminApiToken');
  if (storedToken) {
    apiToken = storedToken;
    apiTokenInput.value = storedToken;
    handleLogin();
  }
});

// Auto-refresh every 30 seconds
setInterval(() => {
  if (apiToken && dashboardContent.style.display !== 'none') {
    refreshDashboard();
  }
}, 30000);

async function handleLogin() {
  const token = apiTokenInput.value.trim();
  
  if (!token) {
    showAuthError('Please enter an API token');
    return;
  }
  
  apiToken = token;
  
  // Test the token by fetching stats
  try {
    const response = await fetch(`${API_BASE_URL}/admin/api/stats`, {
      headers: {
        'Authorization': `Bearer ${apiToken}`
      }
    });
    
    if (response.ok) {
      // Token is valid
      localStorage.setItem('adminApiToken', apiToken);
      authSection.style.display = 'none';
      dashboardContent.style.display = 'block';
      authError.style.display = 'none';
      
      // Load dashboard data
      await refreshDashboard();
    } else {
      const data = await response.json();
      showAuthError(data.error || 'Invalid API token');
      apiToken = '';
      localStorage.removeItem('adminApiToken');
    }
  } catch (error) {
    showAuthError('Failed to connect to API: ' + error.message);
    apiToken = '';
    localStorage.removeItem('adminApiToken');
  }
}

function showAuthError(message) {
  authError.textContent = message;
  authError.style.display = 'block';
}

async function refreshDashboard() {
  await Promise.all([
    loadStats(),
    loadRequests(),
    loadHealthData()
  ]);

  lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
}

async function loadHealthData() {
  // Load worker health
  try {
    const response = await fetch(`${API_BASE_URL}/health/workers`, {
      headers: { 'Authorization': `Bearer ${apiToken}` }
    });
    const data = await response.json();

    let html = '';
    if (data.workers) {
      for (const [name, status] of Object.entries(data.workers)) {
        const healthyClass = status.healthy ? 'status-healthy' : 'status-unhealthy';
        const healthyText = status.healthy ? 'Healthy' : 'Unhealthy';
        html += `<div class="health-metric">
          <span class="health-metric-label">${name}:</span>
          <span class="status-badge ${healthyClass}">${healthyText}</span>
        </div>`;
      }
    }
    if (data.twilio_api) {
      const healthyClass = data.twilio_api.healthy ? 'status-healthy' : 'status-unhealthy';
      const healthyText = data.twilio_api.healthy ? 'Healthy' : 'Unhealthy';
      html += `<div class="health-metric">
        <span class="health-metric-label">Twilio API:</span>
        <span class="status-badge ${healthyClass}">${healthyText}</span>
      </div>`;
    }
    document.getElementById('workerHealth').innerHTML = html || 'No data';
  } catch (e) {
    document.getElementById('workerHealth').innerHTML = 'Error loading';
  }

  // Load concurrency
  try {
    const response = await fetch(`${API_BASE_URL}/health/concurrency`, {
      headers: { 'Authorization': `Bearer ${apiToken}` }
    });
    const data = await response.json();

    const html = `
      <div class="health-metric">
        <span class="health-metric-label">Active Calls:</span>
        <span class="health-metric-value">${data.calls.current} / ${data.calls.limit}</span>
      </div>
      <div class="health-metric">
        <span class="health-metric-label">Active SMS:</span>
        <span class="health-metric-value">${data.sms.current} / ${data.sms.limit}</span>
      </div>
      <div class="health-metric">
        <span class="health-metric-label">Call Utilization:</span>
        <span class="health-metric-value">${data.calls.utilization_percent.toFixed(1)}%</span>
      </div>
    `;
    document.getElementById('concurrencyHealth').innerHTML = html;
  } catch (e) {
    document.getElementById('concurrencyHealth').innerHTML = 'Error loading';
  }

  // Load commit mode
  try {
    const response = await fetch(`${API_BASE_URL}/health/commit_mode`, {
      headers: { 'Authorization': `Bearer ${apiToken}` }
    });
    const data = await response.json();

    const html = `
      <div class="health-metric">
        <span class="health-metric-label">Mode:</span>
        <span class="health-metric-value">${data.commit_mode}</span>
      </div>
      <div class="health-metric">
        <span class="health-metric-label">Transactional:</span>
        <span class="status-badge ${data.transactional_integrity ? 'status-healthy' : 'status-unhealthy'}">
          ${data.transactional_integrity ? 'Yes' : 'No'}
        </span>
      </div>
      <div class="health-metric">
        <span class="health-metric-label">Description:</span>
        <span class="health-metric-value" style="font-size: 12px;">${data.current_mode_description}</span>
      </div>
    `;
    document.getElementById('commitModeHealth').innerHTML = html;
  } catch (e) {
    document.getElementById('commitModeHealth').innerHTML = 'Error loading';
  }
}

async function loadStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/admin/api/stats`, {
      headers: {
        'Authorization': `Bearer ${apiToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to load stats');
    }
    
    const data = await response.json();
    const stats = data.stats;
    
    // Update stat cards
    totalRequests.textContent = stats.total_requests.toLocaleString();
    successRate.textContent = `${stats.success_rate}%`;
    last24h.textContent = stats.last_24h.total.toLocaleString();
    pendingCount.textContent = (stats.by_status.pending || 0).toLocaleString();
    completedCount.textContent = (stats.by_status.completed || 0).toLocaleString();
    failedCount.textContent = (stats.by_status.failed || 0).toLocaleString();
    
  } catch (error) {
    console.error('Error loading stats:', error);
  }
}

async function loadRequests() {
  requestsLoading.style.display = 'block';
  requestsError.style.display = 'none';
  requestsTableContainer.style.display = 'none';

  try {
    const params = new URLSearchParams({
      limit: currentLimit,
      offset: currentOffset,
      order: 'desc'
    });

    if (currentFilters.status) {
      params.append('status', currentFilters.status);
    }

    if (currentFilters.phone) {
      params.append('phone', currentFilters.phone);
    }

    const response = await fetch(`${API_BASE_URL}/admin/api/requests?${params}`, {
      headers: {
        'Authorization': `Bearer ${apiToken}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to load requests');
    }

    const data = await response.json();

    // Render requests table
    renderRequestsTable(data.requests);

    // Update pagination
    updatePagination(data.pagination);

    requestsLoading.style.display = 'none';
    requestsTableContainer.style.display = 'block';

  } catch (error) {
    console.error('Error loading requests:', error);
    requestsLoading.style.display = 'none';
    requestsError.textContent = 'Failed to load requests: ' + error.message;
    requestsError.style.display = 'block';
  }
}

function renderRequestsTable(requests) {
  requestsTableBody.innerHTML = '';

  if (requests.length === 0) {
    requestsTableBody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #6b7280;">No requests found</td></tr>';
    return;
  }

  requests.forEach(req => {
    const row = document.createElement('tr');

    // Format retry info with better UX
    let retryInfo = '';
    if (req.retry_count > 0 || req.max_retries > 0) {
      const count = req.retry_count || 0;
      const max = req.max_retries || 3;
      retryInfo = `<span class="retry-badge">${count}/${max}</span>`;
      if (req.retry_at) {
        retryInfo += `<br><small style="color: #6b7280;">Next: ${formatTimestamp(req.retry_at)}</small>`;
      }
    } else {
      retryInfo = '<span style="color: #9ca3af;">N/A</span>';
    }

    // Format escalation info with better UX
    const escalationInfo = req.escalation_level > 0
      ? `<span class="escalation-badge">L${req.escalation_level}</span>`
      : '<span style="color: #9ca3af;">None</span>';

    // Format priority with color coding
    let priorityBadge = '';
    if (req.priority === 'urgent') {
      priorityBadge = '<span class="priority-badge priority-urgent">🔴 Urgent</span>';
    } else if (req.priority === 'high') {
      priorityBadge = '<span class="priority-badge priority-high">🟡 High</span>';
    } else {
      priorityBadge = '<span class="priority-badge priority-default">⚪ Normal</span>';
    }

    // Retry button for failed requests
    const retryButton = req.request_status === 'failed'
      ? `<button class="btn btn-sm btn-primary" onclick="retryRequest('${req.request_id}')">🔄 Retry</button>`
      : '';

    row.innerHTML = `
      <td><span class="request-id">${req.request_id.substring(0, 8)}...</span></td>
      <td>${req.visitor_name || '-'}</td>
      <td><span class="phone-number">${req.visitor_phone}</span></td>
      <td><span class="status-badge status-${req.request_status}">${formatStatusText(req.request_status)}</span></td>
      <td>${priorityBadge}</td>
      <td>${retryInfo}</td>
      <td>${escalationInfo}</td>
      <td><span class="timestamp">${formatTimestamp(req.updated_at)}</span></td>
      <td>
        <div class="action-buttons">
          ${retryButton}
        </div>
      </td>
    `;

    requestsTableBody.appendChild(row);
  });
}

function formatTimestamp(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function formatStatusText(status) {
  const statusMap = {
    'pending': 'Pending',
    'verified': 'Verified',
    'calling': 'Calling',
    'completed': 'Completed',
    'failed': 'Failed',
    'cancelled': 'Cancelled',
    'sms_sent': 'SMS Sent',
    'retry_scheduled': '🔄 Retry Scheduled'
  };
  return statusMap[status] || status;
}

function updatePagination(pagination) {
  const currentPage = Math.floor(currentOffset / currentLimit) + 1;
  const totalPages = Math.ceil(pagination.total / currentLimit);

  paginationInfo.textContent = `Page ${currentPage} of ${totalPages} (${pagination.total} total)`;

  prevPageBtn.disabled = currentOffset === 0;
  nextPageBtn.disabled = !pagination.has_more;
}

function applyFilters() {
  currentFilters.status = statusFilter.value;
  currentFilters.phone = phoneFilter.value;
  currentOffset = 0; // Reset to first page
  currentLimit = parseInt(limitFilter.value);

  loadRequests();
}

function clearFilters() {
  statusFilter.value = '';
  phoneFilter.value = '';
  limitFilter.value = '50';
  currentFilters = { status: '', phone: '' };
  currentOffset = 0;
  currentLimit = 50;

  loadRequests();
}

function changePage(direction) {
  currentOffset += direction * currentLimit;
  if (currentOffset < 0) currentOffset = 0;

  loadRequests();
}

async function retryRequest(requestId) {
  if (!confirm('Are you sure you want to retry this callback request?')) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/admin/api/retry/${requestId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiToken}`
      }
    });

    const data = await response.json();

    if (response.ok) {
      alert('Callback retry initiated successfully!');
      await refreshDashboard();
    } else {
      alert('Failed to retry: ' + (data.error || 'Unknown error'));
    }
  } catch (error) {
    alert('Failed to retry: ' + error.message);
  }
}

async function cancelRequest(requestId) {
  if (!confirm('Are you sure you want to cancel this callback request?')) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/cancel_request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ request_id: requestId })
    });

    const data = await response.json();

    if (response.ok) {
      alert('Request cancelled successfully!');
      await refreshDashboard();
    } else {
      alert('Failed to cancel: ' + (data.error || 'Unknown error'));
    }
  } catch (error) {
    alert('Failed to cancel: ' + error.message);
  }
}

