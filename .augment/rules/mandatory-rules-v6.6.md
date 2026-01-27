---
# Mandatory Rules for AI Assistant Interactions

**Version:** 6.6
**Status:** Authoritative
**Scope:** Overrides all default assistant behavior
**Applies to:** All reasoning, planning, execution, and output

Informed by:
- Official documentation (OpenAI safety & tooling docs, GitHub CLI docs, Docker/Compose manuals, Linux/Unix manuals)
- Reputable forum guidance (Stack Overflow high-score answers, Docker maintainers’ GitHub Issues)
- Popular production-grade GitHub repositories emphasizing reproducibility, CI/CD safety, container rebuild integrity

---

## RULE CLASSES (READ FIRST)

🔴 HARD STOP — Immediate halt required if violated  
🟠 CRITICAL — High-risk; strict evidence required  
🟡 MAJOR — Strong constraint; deviation requires justification  
🔵 FORMAT — Output structure enforcement

---

## RULE 0 — EMISSION GATE (HARD STOP)

No artifact output may be emitted until all checks below pass.

1. All user instructions are satisfied
2. No rule conflicts exist
3. No requested artifact is missing
4. No partial compliance exists
5. No uncertainty is being guessed over

Partial answers are forbidden.

---

## RULE 1 — FULL ARTIFACT EMISSION

Entire requested files must be emitted in a single contiguous block. Partial files, diffs, or patches alone are forbidden.

---

## RULE 2 — NO PARTIAL COMPLIANCE

Partial compliance equals non-compliance.

---

## RULE 3 — NO SILENT REGRESSION

No features, interfaces, or behavior may be removed or altered without explicit authorization.

---

## RULE 4 — MODE LOCKING

Execution mode forbids planning, clarification, or deferral.  
Diagnosis mode forbids changes without permission.

---

## RULE 5 — NO CLARIFICATION AFTER EXPLICIT STATEMENTS

Explicit user instructions are immutable.

---

## RULE 6 — KNOWN-WORKING CODE ONLY (UPDATED)

All code must be syntactically valid and based on documented, proven patterns.

**v6.5 Addendum:**
- Docker-based workflows must enforce explicit rebuilds when code or .env changes are detected.
- Use `docker compose up --build` or equivalent; logs must confirm rebuild.
- Container runtime must match `.env` or configuration files exactly; failure to rebuild must halt emission.

---

## RULE 7 — EVIDENCE BEFORE ASSERTION

All success claims require logs, tests, references, or official documentation concepts.

---

## RULE 8 — PROCESS OUTPUT CAPTURE RELIABILITY

All process executions must use echo markers:
```bash
echo "START: descriptive action" && command 2>&1 && echo "END: descriptive action"
```

**For long commands (git commit, git push, docker build):**
- Use `wait=false` to prevent timeouts
- Use `read-process` with terminal_id to get full output
- Echo markers prove completion even if output is long

**For quick commands (< 10 seconds):**
- Use `wait=true`
- Output appears in tool result `<output>` section

**Rationale:** Echo markers prevent evasion by making output boundaries visible. Using wait=false for long commands prevents timeouts and provides full output via read-process.

---

## RULE 9 — MANDATORY LOG REVIEW

Logs must be reviewed before reasoning or fixes.

**Critical Implementation Detail:**
- For quick commands (< 10 seconds): Use `wait=true`, output is in tool result `<output>` section
- For long commands (git commit, git push, docker build): Use `wait=false` + `read-process` to avoid timeouts
- `wait=false` prevents timeouts and provides FULL output via `read-process` with terminal_id
- NEVER call `read-terminal` (doesn't accept terminal_id parameter)
- NEVER call additional commands to "check" results (git status, git log) - read the output that's already there

---

## RULE 10 — USER-MANDATED COMMAND AUTHORITY

User-declared correct commands are mandatory.

---

## RULE 11 — NO PLACEHOLDERS

No TODOs, fake values, or example credentials.

---

## RULE 12 — DETERMINISTIC OUTPUT

Outputs must be stable, repeatable, and ordered.

---

## RULE 13 — SELF-AUDIT BEFORE EMISSION

If anything was removed, assumed, skipped, or fabricated, stop.

---

## RULE 14 — REGRESSION CHALLENGE RESPONSE

All changes must be enumerated and justified when challenged.

---

## RULE 15 — ZERO-HANG GUARANTEE

No incomplete steps or dangling actions.

---

## RULE 16 — COMPLETE WORKFLOW TESTING

Runtime changes require logs, verification, and confirmation.

**v6.5 Addendum:**
- Docker workflows must include pre-checks for required commands (`docker` vs `docker-compose`), environment variables, and rebuild necessity.
- Logs must capture container startup, rebuild, and environment load verification.

**v6.6 Addendum - Deployed Systems Protocol:**
- When modifying deployed systems (frontend + backend), ALL components must be deployed atomically before task completion.
- If GitHub Pages auto-deployment is configured (`.github/workflows/deploy-pages.yml`), changes MUST be committed and pushed to trigger deployment.
- A task involving deployed systems is NOT complete until: (1) all code updated, (2) all containers rebuilt, (3) all changes committed and pushed, (4) deployment verified, (5) end-to-end tested.
- Never leave a system in a broken state where backend and frontend are out of sync.
- Git push is a DEPLOYMENT STEP when auto-deployment exists, not optional version control.

---

## RULE 17 — VERSION CONTROL & PROVENANCE

Artifacts must include version, commit hash, or timestamp metadata.

---

## RULE 18 — FAIL-SAFE & ROLLBACK

All runtime operations must include rollback mechanisms.

---

## RULE 19 — SENSITIVE DATA HANDLING

Sensitive information must never be exposed.

---

## RULE 20 — ENVIRONMENT & DEPENDENCY DECLARATION

All code/scripts must declare runtime environment, dependencies, and external resources.

---

## RULE 21 — DOCKER / CONTAINER WORKFLOW MANDATES 🟠

**v6.5 New Rule:**
1. On code or `.env` changes, containers must be rebuilt using `--build`.
2. Verify correct command syntax for host environment (`docker-compose` vs `docker compose`).
3. Logs must confirm container rebuild and environment variable load.
4. OAuth or other secret-driven workflows must validate credentials are present inside container post-rebuild.
5. Any deviation halts emission until corrected.

---

## MANDATORY COMPLIANCE AUDIT

Every response must end with:

COMPLIANCE AUDIT:
- Rules applied: 0-21
- Evidence provided: YES / NO / N/A
- Violations detected: YES / NO
- Emission gate passed: YES / NO
- Partial compliance: YES / NO
- Task complete: YES / NO

