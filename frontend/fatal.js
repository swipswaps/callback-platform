/**
 * Production-safe fatal error screen for invariant violations.
 * 
 * When UX invariants are violated, this provides a clear, user-friendly
 * fatal state UI instead of a white screen or silent failure.
 * 
 * Users get:
 * - Clear explanation that something went wrong
 * - Actionable next step (reload)
 * - No technical jargon or stack traces
 * 
 * Developers still get:
 * - Hard failures in console
 * - Full error details for debugging
 * - Telemetry hooks for monitoring
 */

/**
 * Show a fatal error screen to the user.
 * This replaces the entire page with a clean, actionable error message.
 * 
 * @param {string} message - User-friendly error message
 * @param {Error} [error] - Optional error object for logging
 */
export function showFatalScreen(message, error = null) {
  // Log the error for developers
  if (error) {
    console.error('FATAL ERROR:', error);
    console.error('Stack trace:', error.stack);
  }

  // Replace entire page with fatal error UI
  document.body.innerHTML = `
    <main style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 2rem;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      text-align: center;
    ">
      <div style="
        background: rgba(255, 255, 255, 0.95);
        color: #333;
        padding: 3rem;
        border-radius: 12px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        max-width: 500px;
      ">
        <div style="font-size: 4rem; margin-bottom: 1rem;">⚠️</div>
        <h1 style="margin: 0 0 1rem 0; font-size: 1.75rem; font-weight: 600;">
          Something went wrong
        </h1>
        <p style="margin: 0 0 2rem 0; font-size: 1.1rem; line-height: 1.6; color: #666;">
          ${escapeHtml(message)}
        </p>
        <button 
          onclick="location.reload()" 
          style="
            background: #667eea;
            color: white;
            border: none;
            padding: 0.875rem 2rem;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
          "
          onmouseover="this.style.background='#5568d3'"
          onmouseout="this.style.background='#667eea'"
        >
          Reload Page
        </button>
        <p style="margin: 2rem 0 0 0; font-size: 0.875rem; color: #999;">
          If this problem persists, please contact support.
        </p>
      </div>
    </main>
  `;
}

/**
 * Escape HTML to prevent XSS in error messages
 * @param {string} text - Text to escape
 * @returns {string} - HTML-safe text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Assert UX invariants with production-safe error handling.
 * 
 * This wraps the invariant checks with a try/catch that shows
 * a user-friendly fatal screen instead of crashing silently.
 * 
 * @param {object} state - Application state to validate
 * @throws {Error} - Still throws for telemetry, but after showing UI
 */
export function assertUXInvariantsWithFallback(state) {
  try {
    // Check invariant: state must be defined
    if (!state.currentAppState) {
      throw new Error('UX invariant violated: currentState is undefined');
    }

    // Check invariant: state indicator must exist in DOM
    if (!document.getElementById('app-state-indicator')) {
      throw new Error('UX invariant violated: state indicator missing from DOM');
    }

    // Check invariant: state must be valid
    const validStates = [
      'initializing',
      'detecting_backend',
      'ready',
      'requesting_callback',
      'verifying',
      'calling',
      'connected',
      'error'
    ];
    
    if (!validStates.includes(state.currentAppState)) {
      throw new Error(`UX invariant violated: Invalid state "${state.currentAppState}"`);
    }

  } catch (err) {
    console.error('UX invariant failure:', err);
    
    // Show user-friendly fatal screen
    showFatalScreen(
      'The app encountered a fatal internal error. Please reload the page to continue.'
    , err);
    
    // Still throw for telemetry/monitoring
    throw err;
  }
}

