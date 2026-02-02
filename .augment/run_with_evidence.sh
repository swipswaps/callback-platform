#!/usr/bin/env bash
#
# Evidence Capture Wrapper
# Purpose: All shell commands must leave verbatim artifacts or they don't count
# Created: 2026-02-02
# Maps to: ChatGPT suggestion for evidence capture wrapper
#
# Usage:
#   ./.augment/run_with_evidence.sh <command>
#
# Exit codes:
#   Same as wrapped command
#   Creates evidence files in .augment/evidence/

set -euo pipefail

mkdir -p .augment/evidence

CMD="$*"

{
  echo "COMMAND:"
  echo "$CMD"
  echo
  echo "OUTPUT:"
  eval "$CMD"
} > .augment/evidence/command_output.txt 2>&1

git status --short > .augment/evidence/git_status.txt 2>&1 || echo "git status failed" > .augment/evidence/git_status.txt

