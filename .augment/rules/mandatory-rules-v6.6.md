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

**PROVEN FACT: launch-process with wait=true runs in user's visible terminal**

All process executions must use:
```bash
launch-process:
  command: echo "START: action" && command 2>&1 && echo "END: action"
  wait: true
  max_wait_seconds: 3
```

**For ALL commands:**
- AI ALWAYS runs commands using `wait=true`
- ALWAYS use `max_wait_seconds=3`
- Output is in tool result <output> section - READ IT
- NEVER use `wait=false` - creates hidden background terminals
- NEVER call read-process - AI-only hidden tool (user can't see output)
- NEVER call list-processes - AI-only hidden tool (user can't see output)
- NEVER ask user to run commands - increases error chance
- EXCEPTION: read-terminal for user's spontaneous terminal activity

**Rationale:** AI runs commands with wait=true in user's visible terminal. Output is in tool result <output> section. Asking user to run commands exponentially increases error chance.

---

## RULE 9 — MANDATORY OUTPUT READING (ZERO EXCEPTIONS)

Logs must be reviewed before reasoning or fixes.

**TRUTH: launch-process with wait=true writes to user's VISIBLE terminal**

**THE ONLY PATTERN:**

Call `launch-process` with `wait=true` → output in tool result <output> section → **MUST READ AND QUOTE IT**

**THAT'S IT. ONE STEP.**

**CRITICAL: Use wait=true AND READ OUTPUT EVERY TIME**

- AI ALWAYS runs commands using `wait=true` for launch-process
- Output appears in user's VISIBLE terminal (they can see it)
- Output is ALSO in tool result <output> section - **MUST READ IT EVERY TIME**
- NEVER use `wait=false` - creates HIDDEN terminals user can't see
- NEVER call `read-process` - AI-only hidden tool (user can't see output)
- NEVER call `list-processes` - AI-only hidden tool (user can't see output)
- NEVER ask user to run commands - exponentially increases error chance
- EXCEPTION: `read-terminal` for user's spontaneous terminal activity
- NEVER use tee - not needed, output already visible
- Set max_wait_seconds=3 for most commands (per instructions.md line 12)

**AFTER EVERY launch-process call, assistant MUST:**
1. Check if <output> section exists in tool result
2. If <output> exists and is non-empty:
   - Quote verbatim output in response (at least key lines)
   - Parse output for success/failure indicators (return codes, "END:" markers, error messages)
   - Report findings explicitly to user
3. If <output> is empty or missing:
   - State explicitly: "No output captured"
   - Explain why (e.g., command failed immediately before producing output)
4. If tool returns <error>Cancelled by user.</error> or timeout:
   - **STILL read <output> section** (partial output is there)
   - Quote what was captured before timeout
   - Report partial results

**FORBIDDEN (ZERO TOLERANCE):**
- ❌ Ignoring <output> section when it exists
- ❌ Saying "OK" without reading output
- ❌ Saying "the command timed out" without reading partial output
- ❌ Assuming failure without checking output
- ❌ Calling additional commands to check results (output already in tool result)

**VIOLATION PENALTY:**
- Immediate halt - user must manually show output that was already available
- Wastes user's turn and money
- Breach of contract - assistant's job is to read output, not make user do it

---

## RULE 9B — Tool Name Accuracy (ZERO TOLERANCE)

**Before calling ANY tool, assistant MUST:**
1. Verify tool name matches EXACTLY from system-provided tools list
2. Check character-by-character: hyphens (-) vs underscores (_)
3. Verify capitalization matches exactly
4. Confirm all required parameters are present

**Common errors:**
- ❌ `str_replace-editor` (underscore) → ✅ `str-replace-editor` (hyphen)
- ❌ `launch_process` (underscore) → ✅ `launch-process` (hyphen)
- ❌ `codebase_retrieval` (underscore) → ✅ `codebase-retrieval` (hyphen)
- ❌ `save_file` (underscore) → ✅ `save-file` (hyphen)
- ❌ `web_search` (underscore) → ✅ `web-search` (hyphen)

**Correct tool names (reference):**
- ✅ `str-replace-editor` - Edit existing files
- ✅ `save-file` - Create new files
- ✅ `view` - Read files/directories
- ✅ `launch-process` - Execute commands
- ✅ `codebase-retrieval` - Search codebase
- ✅ `web-search` - Search web
- ✅ `web-fetch` - Fetch web pages

**VIOLATION PENALTY:**
- Tool call fails immediately
- Wastes user's turn and money
- Must retry with correct tool name
- Reveals lack of attention to detail

**RATIONALE:**
Tool name typos (especially hyphen vs underscore) are common and preventable. Assistant must verify exact spelling before calling tools to avoid wasting user's time and money on failed tool calls.

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

**v6.7 Addendum - LOCAL VERIFICATION PRECEDENCE (HARD STOP):**

**RULE LV-1 — No Push Without Local Execution**
- Assistant MUST NOT commit or push any change unless local execution has occurred and observable results are reported.
- "Local execution" means: running the application, triggering the modified code path, producing stdout/stderr logs, or demonstrating the behavior change in runtime terms.
- Mocking, reasoning, or "this should work" does NOT qualify.

**RULE LV-2 — Evidence Before State Advancement**
- Before advancing state from: edited → committed → pushed → deployed
- Assistant MUST present evidence: verbatim console output, browser runtime observation, test runner output, or explicit failure logs.
- Assertions without evidence are INVALID.

**RULE LV-3 — Deployment ≠ Validation**
- Deployment is NOT validation.
- Testing after deployment does NOT satisfy correctness requirements if the code could have been executed locally, the failure would be detectable locally, or the change affects user interaction or control flow.

**RULE LV-4 — Ambiguity Resolution**
- If any rule appears to allow pushing before testing, that interpretation is INVALID by default.
- In conflicts between workflow speed and engineering safety, engineering safety ALWAYS wins.

**RULE LV-5 — No Retroactive Justification**
- Assistant MUST NOT take an action first, then search rules to justify it.
- All rule justification must occur BEFORE irreversible actions are proposed.

**v6.7 Addendum - Deployed Systems Protocol (CORRECTED):**
- When modifying deployed systems (frontend + backend), ALL components must be deployed atomically before task completion.
- If GitHub Pages auto-deployment is configured (`.github/workflows/deploy-pages.yml`), changes MUST be committed and pushed to trigger deployment.
- A task involving deployed systems is NOT complete until: (1) all code updated, (2) all containers rebuilt, **(3) TESTED LOCALLY with evidence**, (4) all changes committed and pushed, (5) deployment verified, (6) end-to-end tested in production.
- Never leave a system in a broken state where backend and frontend are out of sync.
- Git push is a DEPLOYMENT STEP when auto-deployment exists, not optional version control.
- **LOCAL TESTING ALWAYS comes before push. Never push untested code.**

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

