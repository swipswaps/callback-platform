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

// Toast Notification System
function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };

  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span class="toast-message">${message}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;

  container.appendChild(toast);

  // Auto-remove after duration
  if (duration > 0) {
    setTimeout(() => {
      toast.style.animation = 'slideIn 0.3s ease-out reverse';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  return toast;
}

// Copy to clipboard helper
async function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
  try {
    await navigator.clipboard.writeText(text);
    showToast(successMessage, 'success', 2000);
    return true;
  } catch (err) {
    console.error('Failed to copy:', err);
    showToast('Failed to copy to clipboard', 'error');
    return false;
  }
}

// DOM Elements
const authSection = document.getElementById('authSection');
const dashboardContent = document.getElementById('dashboardContent');
const apiTokenInput = document.getElementById('apiToken');
const pasteTokenBtn = document.getElementById('pasteTokenBtn');
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
const exportCsvBtn = document.getElementById('exportCsvBtn');
const bulkActionsBtn = document.getElementById('bulkActionsBtn');
const selectAllCheckbox = document.getElementById('selectAllCheckbox');
const bulkActionsBar = document.getElementById('bulkActionsBar');
const selectedCountSpan = document.getElementById('selectedCount');
const bulkRetryBtn = document.getElementById('bulkRetryBtn');
const bulkCancelBtn = document.getElementById('bulkCancelBtn');
const deselectAllBtn = document.getElementById('deselectAllBtn');

// Bulk selection state
let selectedRequests = new Set();

// Event Listeners
loginBtn.addEventListener('click', handleLogin);
apiTokenInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleLogin();
});

// Paste from clipboard button
pasteTokenBtn.addEventListener('click', async () => {
  try {
    const text = await navigator.clipboard.readText();
    apiTokenInput.value = text.trim();
    showToast('Token pasted from clipboard', 'success', 2000);
    // Trigger auto-login if token looks valid
    if (text.trim().length >= 20) {
      setTimeout(() => handleLogin(), 500);
    }
  } catch (err) {
    console.error('Failed to read clipboard:', err);
    showToast('Failed to read clipboard. Please paste manually.', 'error');
  }
});

// Auto-login when token is pasted or entered
apiTokenInput.addEventListener('input', async (e) => {
  const token = e.target.value.trim();
  // Auto-login if token looks valid (at least 20 chars, typical for API tokens)
  if (token.length >= 20) {
    // Small delay to allow user to finish pasting
    setTimeout(() => {
      if (apiTokenInput.value.trim() === token) {
        handleLogin();
      }
    }, 500);
  }
});

refreshBtn.addEventListener('click', refreshDashboard);
applyFiltersBtn.addEventListener('click', applyFilters);
clearFiltersBtn.addEventListener('click', clearFilters);
prevPageBtn.addEventListener('click', () => changePage(-1));
nextPageBtn.addEventListener('click', () => changePage(1));
exportCsvBtn.addEventListener('click', exportToCSV);

// Bulk actions event listeners
selectAllCheckbox.addEventListener('change', toggleSelectAll);
bulkRetryBtn.addEventListener('click', bulkRetry);
bulkCancelBtn.addEventListener('click', bulkCancel);
deselectAllBtn.addEventListener('click', clearSelection);

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
  // Ignore if user is typing in an input field
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
    // Allow Escape to clear filters even when in input
    if (e.key === 'Escape') {
      clearFilters();
      e.target.blur();
    }
    return;
  }

  // Ctrl/Cmd + R: Refresh
  if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
    e.preventDefault();
    refreshDashboard();
    showToast('Dashboard refreshed', 'info', 2000);
  }

  // Ctrl/Cmd + K: Focus search
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    phoneFilter.focus();
  }

  // ?: Show keyboard shortcuts
  if (e.key === '?' && !e.shiftKey) {
    showShortcutsModal();
  }

  // Escape: Clear filters
  if (e.key === 'Escape') {
    clearFilters();
  }
});

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
    loadRequests()
  ]);

  lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
}

async function cancelRequest(requestId) {
  if (!confirm('Are you sure you want to cancel this request?')) {
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

    if (data.success) {
      // Update live without page refresh
      await Promise.all([loadStats(), loadRequests()]);

      // Show success message briefly
      const row = document.querySelector(`[onclick*="${requestId}"]`)?.closest('tr');
      if (row) {
        row.style.backgroundColor = '#d1fae5';
        setTimeout(() => { row.style.backgroundColor = ''; }, 2000);
      }
    } else {
      showToast(`Failed to cancel request: ${data.error || 'Unknown error'}`, 'error');
    }
  } catch (error) {
    console.error('Error cancelling request:', error);
    showToast('Failed to cancel request. Please try again.', 'error');
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

    // Store requests data globally for viewDetails function
    window.currentRequestsData = data.requests;

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
    requestsTableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #6b7280;">No requests found</td></tr>';
    return;
  }

  requests.forEach(req => {
    const row = document.createElement('tr');

    const status = req.request_status.toLowerCase();

    // Build action buttons based on status
    let actionButtons = '';

    if (status === 'failed') {
      actionButtons += `<button class="btn btn-sm btn-primary" onclick="retryRequest('${req.request_id}')">🔄 Retry</button> `;
    }

    if (status === 'pending' || status === 'verified') {
      actionButtons += `<button class="btn btn-sm btn-warning" onclick="cancelRequest('${req.request_id}')">❌ Cancel</button> `;
    }

    // Always show view details button
    actionButtons += `<button class="btn btn-sm btn-secondary" onclick="viewDetails('${req.request_id}')">👁️ View</button>`;

    const isSelected = selectedRequests.has(req.request_id);

    row.innerHTML = `
      <td>
        <input type="checkbox"
               class="row-checkbox"
               data-request-id="${req.request_id}"
               ${isSelected ? 'checked' : ''}
               onchange="toggleRowSelection('${req.request_id}', this.checked)">
      </td>
      <td>
        <span class="request-id copyable"
              onclick="copyToClipboard('${req.request_id}', 'Request ID copied!')"
              title="Click to copy full ID">
          ${req.request_id.substring(0, 8)}...
        </span>
      </td>
      <td>${req.visitor_name || '-'}</td>
      <td>
        <span class="phone-number copyable"
              onclick="copyToClipboard('${req.visitor_phone}', 'Phone number copied!')"
              title="Click to copy phone number">
          ${req.visitor_phone}
        </span>
      </td>
      <td><span class="status-badge status-${status}">${formatStatusText(req.request_status)}</span></td>
      <td><span class="timestamp">${formatTimestamp(req.updated_at)}</span></td>
      <td>
        <div class="action-buttons">
          ${actionButtons}
        </div>
      </td>
    `;

    requestsTableBody.appendChild(row);
  });

  updateBulkActionsBar();
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

function filterByStatus(status) {
  // Update the filter dropdown
  statusFilter.value = status;

  // Apply the filter
  currentFilters.status = status;
  currentFilters.phone = '';
  phoneFilter.value = '';
  currentOffset = 0;

  loadRequests();
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

function viewDetails(requestId) {
  // Find the request in the current data
  const req = window.currentRequestsData?.find(r => r.request_id === requestId);

  if (!req) {
    showToast('Request details not found', 'error');
    return;
  }

  const details = `
Request ID: ${req.request_id}
Name: ${req.visitor_name || 'N/A'}
Email: ${req.visitor_email || 'N/A'}
Phone: ${req.visitor_phone}
Status: ${req.request_status}
Message: ${req.status_message || 'N/A'}
Created: ${formatTimestamp(req.created_at)}
Updated: ${formatTimestamp(req.updated_at)}
Call SID: ${req.call_sid || 'N/A'}
SMS SID: ${req.sms_sid || 'N/A'}
IP Address: ${req.ip_address || 'N/A'}
  `.trim();

  // Show in a better format using toast with longer duration
  showToast(details.replace(/\n/g, '<br>'), 'info', 10000);
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
      // Update live without page refresh
      await Promise.all([loadStats(), loadRequests()]);

      // Show success message briefly
      const row = document.querySelector(`[onclick*="${requestId}"]`)?.closest('tr');
      if (row) {
        row.style.backgroundColor = '#dbeafe';
        setTimeout(() => { row.style.backgroundColor = ''; }, 2000);
      }
    } else {
      showToast('Failed to retry: ' + (data.error || 'Unknown error'), 'error');
    }
  } catch (error) {
    showToast('Failed to retry: ' + error.message, 'error');
  }
}

// Modal functions
function showShortcutsModal() {
  document.getElementById('shortcutsModal').style.display = 'flex';
}

function closeShortcutsModal() {
  document.getElementById('shortcutsModal').style.display = 'none';
}

// Make modal functions global
window.showShortcutsModal = showShortcutsModal;
window.closeShortcutsModal = closeShortcutsModal;

// Export to CSV
async function exportToCSV() {
  try {
    // Fetch all requests with current filters (no pagination limit)
    const params = new URLSearchParams({
      limit: 10000, // Get all matching records
      offset: 0,
      order: 'desc'
    });

    if (currentFilters.status) {
      params.append('status', currentFilters.status);
    }

    if (currentFilters.phone) {
      params.append('phone', currentFilters.phone);
    }

    showToast('Preparing CSV export...', 'info', 2000);

    const response = await fetch(`${API_BASE_URL}/admin/api/requests?${params}`, {
      headers: {
        'Authorization': `Bearer ${apiToken}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch requests for export');
    }

    const data = await response.json();
    const requests = data.requests;

    if (requests.length === 0) {
      showToast('No requests to export', 'warning');
      return;
    }

    // Create CSV content
    const headers = ['Request ID', 'Name', 'Phone', 'Email', 'Status', 'Created', 'Updated', 'Call SID', 'SMS SID', 'IP Address'];
    const csvRows = [headers.join(',')];

    requests.forEach(req => {
      const row = [
        req.request_id,
        req.visitor_name || '',
        req.visitor_phone,
        req.visitor_email || '',
        req.request_status,
        req.created_at,
        req.updated_at,
        req.call_sid || '',
        req.sms_sid || '',
        req.ip_address || ''
      ];
      // Escape commas and quotes in CSV
      const escapedRow = row.map(field => {
        const str = String(field);
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      });
      csvRows.push(escapedRow.join(','));
    });

    const csvContent = csvRows.join('\n');

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Generate filename with timestamp and filter info
    const timestamp = new Date().toISOString().split('T')[0];
    const filterSuffix = currentFilters.status ? `_${currentFilters.status}` : '';
    link.download = `callback_requests${filterSuffix}_${timestamp}.csv`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    showToast(`Exported ${requests.length} requests to CSV`, 'success');

  } catch (error) {
    console.error('Export failed:', error);
    showToast('Failed to export CSV: ' + error.message, 'error');
  }
}

// Bulk Actions Functions
function toggleRowSelection(requestId, isChecked) {
  if (isChecked) {
    selectedRequests.add(requestId);
  } else {
    selectedRequests.delete(requestId);
  }
  updateBulkActionsBar();
}

function toggleSelectAll() {
  const checkboxes = document.querySelectorAll('.row-checkbox');
  checkboxes.forEach(cb => {
    const requestId = cb.dataset.requestId;
    if (selectAllCheckbox.checked) {
      selectedRequests.add(requestId);
      cb.checked = true;
    } else {
      selectedRequests.delete(requestId);
      cb.checked = false;
    }
  });
  updateBulkActionsBar();
}

function clearSelection() {
  selectedRequests.clear();
  document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = false);
  selectAllCheckbox.checked = false;
  updateBulkActionsBar();
}

function updateBulkActionsBar() {
  const count = selectedRequests.size;
  selectedCountSpan.textContent = count;

  if (count > 0) {
    bulkActionsBar.style.display = 'flex';
  } else {
    bulkActionsBar.style.display = 'none';
  }

  // Update select all checkbox state
  const checkboxes = document.querySelectorAll('.row-checkbox');
  const allChecked = checkboxes.length > 0 && Array.from(checkboxes).every(cb => cb.checked);
  selectAllCheckbox.checked = allChecked;
}

async function bulkRetry() {
  if (selectedRequests.size === 0) {
    showToast('No requests selected', 'warning');
    return;
  }

  if (!confirm(`Are you sure you want to retry ${selectedRequests.size} requests?`)) {
    return;
  }

  const requestIds = Array.from(selectedRequests);
  let successCount = 0;
  let failCount = 0;

  showToast(`Retrying ${requestIds.length} requests...`, 'info', 3000);

  for (const requestId of requestIds) {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/api/retry/${requestId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiToken}`
        }
      });

      if (response.ok) {
        successCount++;
      } else {
        failCount++;
      }
    } catch (error) {
      console.error(`Failed to retry ${requestId}:`, error);
      failCount++;
    }
  }

  clearSelection();
  await Promise.all([loadStats(), loadRequests()]);

  if (failCount === 0) {
    showToast(`✅ Successfully retried ${successCount} requests`, 'success');
  } else {
    showToast(`⚠️ Retried ${successCount} requests, ${failCount} failed`, 'warning');
  }
}

async function bulkCancel() {
  if (selectedRequests.size === 0) {
    showToast('No requests selected', 'warning');
    return;
  }

  if (!confirm(`Are you sure you want to cancel ${selectedRequests.size} requests?`)) {
    return;
  }

  const requestIds = Array.from(selectedRequests);
  let successCount = 0;
  let failCount = 0;

  showToast(`Cancelling ${requestIds.length} requests...`, 'info', 3000);

  for (const requestId of requestIds) {
    try {
      const response = await fetch(`${API_BASE_URL}/cancel_request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ request_id: requestId })
      });

      const data = await response.json();

      if (data.success) {
        successCount++;
      } else {
        failCount++;
      }
    } catch (error) {
      console.error(`Failed to cancel ${requestId}:`, error);
      failCount++;
    }
  }

  clearSelection();
  await Promise.all([loadStats(), loadRequests()]);

  if (failCount === 0) {
    showToast(`✅ Successfully cancelled ${successCount} requests`, 'success');
  } else {
    showToast(`⚠️ Cancelled ${successCount} requests, ${failCount} failed`, 'warning');
  }
}

// Make bulk functions global
window.toggleRowSelection = toggleRowSelection;

// Version Detection (one-shot, fail-silent)
(function checkDeploymentVersion() {
  try {
    const metaCommit = document.querySelector('meta[name="build-commit"]')?.content;
    const metaTime = document.querySelector('meta[name="build-time"]')?.content;

    if (!metaCommit) return; // No build info, skip

    fetch('https://api.github.com/repos/swipswaps/callback-platform/commits/main', {
      headers: { 'Accept': 'application/vnd.github.v3+json' },
      cache: 'no-store'
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data?.sha) return;

        const remoteCommit = data.sha.substring(0, 7);

        if (remoteCommit !== metaCommit) {
          showVersionBanner(metaCommit, remoteCommit, metaTime);
        }
      })
      .catch(() => {}); // Fail silently
  } catch (_) {}
})();

function showVersionBanner(local, remote, buildTime) {
  const banner = document.createElement('div');
  banner.id = 'versionBanner';
  banner.style.cssText = `
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #1e293b;
    color: #e2e8f0;
    font-size: 13px;
    padding: 10px 16px;
    z-index: 10000;
    border-top: 2px solid #3b82f6;
    display: flex;
    justify-content: space-between;
    align-items: center;
  `;

  const message = document.createElement('div');
  message.innerHTML = `
    ℹ️ You are viewing build <strong>${local}</strong>.
    A newer build (<strong>${remote}</strong>) exists on GitHub.
    Updates may take time to reach all users.
  `;

  const actions = document.createElement('div');
  actions.style.cssText = 'display: flex; gap: 10px;';

  const refreshBtn = document.createElement('button');
  refreshBtn.textContent = 'Refresh';
  refreshBtn.className = 'btn btn-sm btn-secondary';
  refreshBtn.onclick = () => location.reload();

  const dismissBtn = document.createElement('button');
  dismissBtn.textContent = 'Dismiss';
  dismissBtn.className = 'btn btn-sm btn-secondary';
  dismissBtn.onclick = () => banner.remove();

  actions.appendChild(refreshBtn);
  actions.appendChild(dismissBtn);

  banner.appendChild(message);
  banner.appendChild(actions);

  document.body.appendChild(banner);
}
