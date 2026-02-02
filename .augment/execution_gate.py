#!/usr/bin/env python3
"""
Execution Authority Gate
------------------------
Blocks state advancement unless execution evidence is explicitly provided.

This module is intentionally dumb and strict.
If evidence is missing, execution HALTS.

Created: 2026-02-02
Purpose: Prevent narration drift after execution failure
Maps to: ChatGPT suggestion for hard execution authority gate
"""

import sys
from pathlib import Path

REQUIRED_EVIDENCE = [
    "git_status.txt",
    "command_output.txt",
]

EVIDENCE_DIR = Path(".augment/evidence")


def fail(msg: str) -> None:
    """Fail hard with error message."""
    print(f"[EXECUTION-GATE] FAIL: {msg}", file=sys.stderr, flush=True)
    sys.exit(42)


def check_execution_evidence() -> None:
    """Verify execution evidence exists before allowing state advancement."""
    if not EVIDENCE_DIR.exists():
        fail("Evidence directory missing")

    missing = []
    for file in REQUIRED_EVIDENCE:
        if not (EVIDENCE_DIR / file).exists():
            missing.append(file)

    if missing:
        fail(f"Missing execution evidence: {', '.join(missing)}")


if __name__ == "__main__":
    check_execution_evidence()
    print("[EXECUTION-GATE] PASS: Execution evidence verified", flush=True)

