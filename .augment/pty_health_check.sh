#!/usr/bin/env bash
#
# PTY Health Check Script
# Purpose: Diagnose terminal/PTY issues that cause command timeouts
# Created: 2026-02-02
# Maps to: ChatGPT suggestion for PTY health checks
#
# Usage:
#   ./augment/pty_health_check.sh
#
# Exit codes:
#   0 - PTY is healthy
#   1 - PTY has issues

set -euo pipefail

echo "=== PTY Health Check ==="
echo

# Check 1: Verify we're in a terminal
echo "1. Checking if running in terminal..."
if tty -s; then
    echo "   ✅ Running in terminal: $(tty)"
else
    echo "   ❌ Not running in terminal (stdin is not a TTY)"
    exit 1
fi

# Check 2: Check terminal settings
echo
echo "2. Checking terminal settings..."
if stty -a > /dev/null 2>&1; then
    echo "   ✅ Terminal settings accessible"
    stty -a | head -n 3
else
    echo "   ❌ Cannot access terminal settings (PTY may be dead)"
    exit 1
fi

# Check 3: Check for stuck Python processes
echo
echo "3. Checking for stuck Python processes..."
STUCK_PYTHON=$(ps aux | grep -E 'python|validate_compliance' | grep -v grep || true)
if [ -z "$STUCK_PYTHON" ]; then
    echo "   ✅ No stuck Python processes"
else
    echo "   ⚠️  Found Python processes:"
    echo "$STUCK_PYTHON" | sed 's/^/      /'
fi

# Check 4: Check for zombie processes
echo
echo "4. Checking for zombie processes..."
ZOMBIES=$(ps aux | awk '$8 ~ /Z/ { print }' || true)
if [ -z "$ZOMBIES" ]; then
    echo "   ✅ No zombie processes"
else
    echo "   ⚠️  Found zombie processes:"
    echo "$ZOMBIES" | sed 's/^/      /'
fi

# Check 5: Test basic command execution
echo
echo "5. Testing basic command execution..."
if echo "test" > /dev/null 2>&1; then
    echo "   ✅ Basic commands work"
else
    echo "   ❌ Basic commands fail (PTY is broken)"
    exit 1
fi

# Check 6: Test command with timeout
echo
echo "6. Testing command with timeout..."
if timeout 2s echo "timeout test" > /dev/null 2>&1; then
    echo "   ✅ Timeout mechanism works"
else
    echo "   ❌ Timeout mechanism failed"
    exit 1
fi

echo
echo "=== PTY Health Check Complete ==="
echo "✅ All checks passed - PTY is healthy"
exit 0

