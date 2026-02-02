#!/usr/bin/env bash
#
# Watchdog Validator Script
# Purpose: Run compliance validator with hard timeout to prevent hangs
# Created: 2026-02-02
# Maps to: ChatGPT suggestion for watchdog timer
#
# Usage:
#   ./augment/watchdog_validator.sh [output_file]
#
# Exit codes:
#   0 - Validation passed
#   1 - Validation failed
#   124 - Validation timed out (hung)

set -euo pipefail

TIMEOUT_SECONDS=10
VALIDATOR_SCRIPT=".augment/validate_compliance.py"

echo "=== Watchdog Validator ==="
echo "Timeout: ${TIMEOUT_SECONDS}s"
echo

# Check if validator exists
if [ ! -f "$VALIDATOR_SCRIPT" ]; then
    echo "❌ Validator script not found: $VALIDATOR_SCRIPT"
    exit 1
fi

# Determine mode
if [ "${CI:-false}" = "true" ]; then
    echo "Mode: CI (structure validation only)"
    echo "Running: timeout ${TIMEOUT_SECONDS}s python3 $VALIDATOR_SCRIPT"
    echo
    
    if timeout ${TIMEOUT_SECONDS}s python3 "$VALIDATOR_SCRIPT"; then
        echo
        echo "✅ Validation passed (CI mode)"
        exit 0
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            echo
            echo "❌ Validation timed out after ${TIMEOUT_SECONDS}s (validator hung)"
            echo "This indicates a blocking code path (stdin read, infinite loop, etc.)"
            exit 124
        else
            echo
            echo "❌ Validation failed with exit code $EXIT_CODE"
            exit 1
        fi
    fi
else
    # Full mode: requires output file
    if [ $# -ne 1 ]; then
        echo "Usage: $0 <output_file>"
        echo "   or: CI=true $0"
        exit 1
    fi
    
    OUTPUT_FILE="$1"
    echo "Mode: Full (structure + output validation)"
    echo "Output file: $OUTPUT_FILE"
    echo "Running: timeout ${TIMEOUT_SECONDS}s python3 $VALIDATOR_SCRIPT $OUTPUT_FILE"
    echo
    
    if timeout ${TIMEOUT_SECONDS}s python3 "$VALIDATOR_SCRIPT" "$OUTPUT_FILE"; then
        echo
        echo "✅ Validation passed (full mode)"
        exit 0
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            echo
            echo "❌ Validation timed out after ${TIMEOUT_SECONDS}s (validator hung)"
            echo "This indicates a blocking code path (stdin read, infinite loop, etc.)"
            exit 124
        else
            echo
            echo "❌ Validation failed with exit code $EXIT_CODE"
            exit 1
        fi
    fi
fi

