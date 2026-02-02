#!/usr/bin/env python3
"""
Machine-checkable compliance validator (deadlock-proof).

Enforces LLM compliance rubric with zero tolerance.
Fails hard when rubric is violated - no mercy, no partial success.

Design principles:
- No stdin reads
- No optional blocking paths
- No mode auto-detection
- One exit path per mode
- Guaranteed termination

Usage:
    # CI mode (structure validation only)
    CI=true python .augment/validate_compliance.py

    # Full mode (structure + output validation)
    python .augment/validate_compliance.py <output_file>

Exit codes:
    0 - Compliance validation passed
    1 - Compliance failure detected
    42 - Execution authority revoked (no evidence)
"""

import sys
import os
import yaml
import re
from pathlib import Path

# Import execution gate for authority checking
try:
    from execution_gate import check_execution_evidence
    EXECUTION_GATE_AVAILABLE = True
except ImportError:
    EXECUTION_GATE_AVAILABLE = False
from pathlib import Path

RUBRIC_PATH = Path(".augment/compliance_rubric.yaml")
REPO_ROOT = Path(".")


def fail(msg):
    """Fail hard with error message."""
    print(f"❌ COMPLIANCE FAILURE: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def warn(msg):
    """Warn about potential issue."""
    print(f"⚠️  WARNING: {msg}", file=sys.stderr, flush=True)


def load_rubric():
    """Load compliance rubric from YAML file (non-blocking)."""
    if not RUBRIC_PATH.exists():
        fail("Missing compliance rubric (.augment/compliance_rubric.yaml)")

    try:
        with RUBRIC_PATH.open() as f:
            return yaml.safe_load(f)
    except Exception as e:
        fail(f"Failed to load rubric: {e}")


def check_repo_grounding(output, rubric):
    """Verify all file references exist in repository."""
    patterns = rubric.get('file_reference_patterns', [])
    
    for pattern in patterns:
        file_refs = re.findall(pattern, output)
        for ref in file_refs:
            # Handle tuple results from regex groups
            file_path = ref[0] if isinstance(ref, tuple) else ref
            
            if not (REPO_ROOT / file_path).exists():
                fail(f"Referenced file does not exist: {file_path}")


def check_artifact_emission(output, rubric):
    """Verify full artifacts emitted, not just snippets."""
    if "```" not in output:
        fail("No code blocks found (snippets or artifacts missing)")

    forbidden_phrases = rubric.get('forbidden_phrases', [])
    for phrase in forbidden_phrases:
        if phrase in output.lower():
            fail(f"Forbidden advisory language detected: '{phrase}'")


def check_self_audit(output, rubric):
    """Verify self-audit section exists."""
    required_markers = rubric.get('required_markers', [])
    
    for marker in required_markers:
        if marker not in output:
            fail(f"Missing required self-audit section: {marker}")


def check_assumptions(output):
    """Verify explicit assumptions declared."""
    if "Assumption:" not in output and "Assumptions:" not in output:
        fail("No explicit assumptions declared")


def check_failure_modes(output):
    """Verify failure mode explanations exist."""
    if "Failure Mode" not in output and "Fails safely" not in output:
        fail("No failure mode / safe failure explanation found")


def validate_repository_structure():
    """Validate repository structure compliance (non-blocking)."""
    required_files = [
        ".augment/instructions.md",
        ".augment/rules/mandatory-rules-v6.6.md",
        ".augment/compliance_rubric.yaml",
        "README.md",
    ]

    for file_path in required_files:
        if not (REPO_ROOT / file_path).exists():
            fail(f"Required file missing: {file_path}")

    print("✅ Repository structure validation passed", flush=True)


def validate_repo_only():
    """CI mode: Validate repository structure only."""
    print("Running CI mode (structure validation only)", flush=True)
    validate_repository_structure()
    print("✅ CI compliance validation passed", flush=True)


def validate_output(output_file):
    """Full mode: Validate both structure and LLM output."""
    print(f"Running full mode (structure + output validation)", flush=True)

    # Load rubric
    rubric = load_rubric()

    # Load output file
    if not output_file.exists():
        fail(f"Output file not found: {output_file}")

    try:
        output = output_file.read_text(encoding="utf-8")
    except Exception as e:
        fail(f"Failed to read output file: {e}")

    # Validate structure first
    validate_repository_structure()

    # Validate output
    check_repo_grounding(output, rubric)
    check_artifact_emission(output, rubric)
    check_self_audit(output, rubric)
    check_assumptions(output)
    check_failure_modes(output)

    print("✅ Full compliance validation passed", flush=True)


def main():
    """Run compliance checks (deadlock-proof entry point)."""
    # Reconfigure stdout for line buffering (prevents buffer deadlock)
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    # HARD STOP: Check execution authority first (if gate is available)
    if EXECUTION_GATE_AVAILABLE:
        try:
            check_execution_evidence()
            print("[EXECUTION-GATE] Authority verified", flush=True)
        except SystemExit as e:
            if e.code == 42:
                print("[EXECUTION-GATE] Authority revoked - no execution evidence", file=sys.stderr, flush=True)
                sys.exit(42)
            raise

    # Determine mode (no auto-detection, explicit only)
    if os.environ.get("CI") == "true":
        # CI mode: structure validation only
        validate_repo_only()
        return

    # Full mode: requires output file argument
    if len(sys.argv) != 2:
        fail("Usage: python validate_compliance.py <output_file>\\n       CI=true python validate_compliance.py")

    output_file = Path(sys.argv[1])
    validate_output(output_file)


if __name__ == "__main__":
    main()

