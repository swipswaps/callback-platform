#!/usr/bin/env bash
#
# Watchdog With Guaranteed Kill
# Purpose: Even if PTY dies, execution cannot hang indefinitely
# Created: 2026-02-02
# Maps to: ChatGPT suggestion for watchdog with guaranteed kill
#
# Usage:
#   ./.augment/watchdog.sh <command>
#   TIMEOUT=30 ./.augment/watchdog.sh <command>
#
# Exit codes:
#   Same as wrapped command
#   124 if timeout exceeded

set -euo pipefail

TIMEOUT="${TIMEOUT:-10}"

if ! timeout "$TIMEOUT" "$@"; then
  echo "[WATCHDOG] Timeout exceeded ($TIMEOUT s)" >&2
  exit 124
fi

