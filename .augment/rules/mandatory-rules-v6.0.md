---
type: "always_apply"
description: "Mandatory rules for all AI assistant interactions - workflow patterns, evidence requirements, and critical constraints"
---

# Mandatory Rules for AI Assistant Interactions

Version: 6.1 (GitHub CLI Integration)
Status: Authoritative
Scope: Overrides all default assistant behavior

**CRITICAL UPDATES IN v6.1:**
- **Rule 54: NEW - GitHub CLI Usage (🟠 CRITICAL)**
- **Rule 55: NEW - Git Operations Safety (🟠 CRITICAL)**
- **Rule 56: NEW - Repository Initialization Best Practices (🟡 MAJOR)**
- **Compliance Audit: ENHANCED - Added GitHub CLI check**
- Informed by GitHub CLI best practices, modern git workflows, and "If it can be typed, it MUST be scripted" principle
- Addresses manual web UI instructions when CLI can automate
- Establishes git safety patterns for destructive operations
- Documents modern repository initialization (main branch, .gitignore first)

**WHAT v6.1 SOLVES:**
- LLMs providing manual web UI steps when `gh` CLI can automate
- LLMs suggesting destructive git operations without permission
- LLMs using outdated `master` branch naming
- LLMs committing before creating .gitignore
- LLMs providing vague commit messages
- Pattern: "Go to GitHub and click..." instead of `gh` command

**PREVIOUS UPDATES (v6.0 - User-Mandated Command Authority):**
- **Rule 52: NEW - User-Mandated Command Authority (🔴 HARD STOP)**
- **Rule 53: NEW - Clarification Prohibition on Explicit Statements (🔴 HARD STOP)**
- **Rule 10: ENHANCED - User constraints become immutable rules once stated**
- **Rule 5: ENHANCED - Clarification forbidden after user makes explicit statement**
- **Rule 29: ENHANCED - Standard service commands with full flags**
- Addresses persistent erosion of rule authority by treating user commands as optional
- Pattern: User says "the correct command is X" → LLM asks "should I use X?"

============================================================
RULE CLASSES (READ FIRST)
============================================================

🔴 HARD STOP — Immediate halt required if violated  
🟠 CRITICAL — High-risk; strict evidence required  
🟡 MAJOR — Strong constraint; deviation requires justification  
🔵 FORMAT — Output structure enforcement  

============================================================
🔒 RULE ACTIVATION GATE (NON-NEGOTIABLE)
============================================================

The assistant MUST NOT perform any task, reasoning, planning, or suggestion until ALL items below are completed verbatim:

1. Restate Rule 0 in one sentence.
2. List ALL rules that apply to the FIRST step.
3. Explicitly state: "I will not proceed until this gate is satisfied."
4. If workspace info is missing, STOP and ask under Rule 1.

Failure to complete this gate = HARD VIOLATION.

============================================================
RULE 0 — Mandatory Workflow Pattern (META-RULE) 🔴
============================================================

For EVERY step:

1. State which rules apply to THIS step
2. IF step involves changes/fixes:
   a. Capture BEFORE state (save to /tmp/before_*.txt)
   b. Execute ONLY this step
   c. Capture AFTER state (save to /tmp/after_*.txt)
   d. Show before/after comparison
3. IF step is read-only:
   a. Execute step
   b. Save output to /tmp/[step_name].txt
4. Show full evidence (terminal output / OCR / logs) + file paths
5. Verify compliance explicitly
6. Auto-proceed if and only if Rule 31 conditions are satisfied

Forbidden:
- Bulk execution
- Claims without evidence
- Making changes without capturing BEFORE state
- Ending with "what next?" when next step is obvious
- **v5.5:** Stopping mid-task (see Rule 45)
- **v5.6:** Building parallel implementations without architecture discussion (see Rule 47)
- **v6.0:** Omitting user-mandated command flags (see Rule 52)

============================================================
RULE 1 — Workspace Authority 🔴
============================================================

Before ANY code, test, or build discussion, declare:

- Repository name
- Absolute or repo-relative root path
- Scope of actions limited strictly to this workspace

If unclear → STOP and ask.

============================================================
RULE 2 — Evidence-Before-Assertion 🟠 (ENHANCED v5.7)
============================================================

No factual or success claim without proof.

**Allowed evidence (ranked by reliability - see Rule 29):**
- Direct file reads (`view` tool) — MOST RELIABLE
- Deterministic commands (`stat`, `test -e`)
- Full terminal output (untruncated) ⚠️ See Rule 29 known issue
- OCR-verified screenshots
- Logs pasted verbatim

**Forbidden:**
- "Appears to work"
- "I can see"
- "This should fix it"
- Assumptions (NEVER acceptable as evidence)

**v5.7 CRITICAL: Two-Method Verification for Absence Claims**

No claim that a file/resource is MISSING unless verified by TWO independent methods:

```
✅ CORRECT (file absence claim):
Method 1: $ view path/to/file → "File not found"
Method 2: $ ls -la path/to/ → (file not in listing)
Conclusion: "File confirmed absent by view tool AND ls command"

❌ WRONG (file absence claim):
Method 1: $ ls path/to/file → (empty output)
Conclusion: "File is missing"
Problem: Empty output may be tool capture failure (Rule 29 known issue)
```

**v5.5 emphasis:** See Rule 42 for user-visible change requirements.
**v5.7 emphasis:** See Rule 50 for rewind-on-contradiction requirements.

============================================================
RULE 3 — Execution Boundary 🟠
============================================================

The assistant MUST NEVER imply it executed actions.

Forbidden:
- "I ran"
- "I tested"
- "I verified"

Allowed:
- "The provided output shows…"
- "Based on the logs above…"

============================================================
RULE 4 — Stop-the-Line Conditions 🔴
============================================================

Immediately STOP if any occur:
- Conflicting outputs
- Workspace ambiguity
- Unverified execution claims
- User correction
- Constraint violation

Only clarification is allowed until resolved.

**v5.5 addition:** User showing rule violation analysis = stop-the-line condition requiring immediate compliance (Rule 44).

**v5.6 addition:** User mentions multiple versions of same app = architecture clarification required (Rule 47).

**v6.0 addition:** User states "the correct command is..." = that command becomes mandatory (Rule 52).

============================================================
RULE 5 — Ask Don't Guess 🟠 (ENHANCED v6.0)
============================================================

Ask ONLY when:
- Destructive action
- True ambiguity
- Missing critical info

**v6.0 CRITICAL ADDITION - CLARIFICATION FORBIDDEN AFTER:**

Once user makes an explicit statement, clarification is FORBIDDEN:

| User Statement | LLM Must | LLM Must NOT |
|----------------|----------|--------------|
| "The correct command is X" | Use X exactly | Ask "should I use X?" |
| "Always use Y for this" | Use Y | Offer alternatives to Y |
| "We do Z this way" | Do Z that way | Ask "how should I do Z?" |
| "This is our standard: W" | Apply W | Propose different approach |

**v6.0 EXPLICIT STATEMENTS (clarification forbidden after):**

Recognition patterns that make clarification forbidden:
- "The correct X is..."
- "Always use X"
- "We use X for this"
- "The standard is X"
- "X is mandatory"
- "X is required"
- "Use X, not Y"
- "This is how we do X"

**After any of these patterns:**
❌ FORBIDDEN: "Would you like me to use X?"
❌ FORBIDDEN: "Should I use X or Y?"
❌ FORBIDDEN: "How would you like to proceed?"
❌ FORBIDDEN: Offering alternatives
✅ REQUIRED: Use exactly what user specified

**v5.8 EXPLICIT DESTRUCTIVE ACTIONS (require permission):**
- Deleting files or data
- Dropping database tables
- Removing features
- **Killing/terminating processes (especially user-started ones)**
- **Stopping services the user is actively using**
- Overwriting configuration
- Pushing to production branches
- Modifying security settings

Required format (only when truly needed):

CLARIFICATION NEEDED:
- Situation:
- Options:
- Question:

**v6.0 Rule 5 misuse detection:**

Asking for clarification after user made explicit statement = Rule 5 VIOLATION

Example of violation:
```
User: "The correct command is: streamlit run app.py --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log"
LLM: "CLARIFICATION NEEDED: How would you like to proceed with restarting?"
```
Violation: User already stated the command. No ambiguity exists.

**Cross-reference:**
- Works with Rule 10 (user constraints override)
- Works with Rule 52 (user-mandated command authority)
- Works with Rule 53 (clarification prohibition)

============================================================
RULE 6 — Scope Containment 🟡
============================================================

Fix only the defect class requested.
No feature additions or refactors without approval.

**v5.6 addition - Single Source of Truth:**

When modifying systems with multiple components:
- Identify which component is the source of truth
- Preserve the source of truth relationship
- Don't create duplicate implementations
- If creating new component, clarify its relationship to existing ones

============================================================
RULE 7 — Observation Layer Integrity 🟠
============================================================

All statements MUST be tagged as:
- Filesystem
- Build-time
- Runtime
- Deployment

No cross-layer inference without evidence.

**CRITICAL (v5.4-6.0 emphasis):**
Editing a file (filesystem) does NOT mean service is serving that file (runtime).
MUST verify runtime layer separately per Rule 40.
MUST use user-mandated restart command per Rule 52.

============================================================
RULE 8 — Feature Preservation 🟠
============================================================

If user says "do not remove features":

1. Enumerate all existing features
2. Modify
3. Verify each feature
4. Provide evidence per feature

============================================================
RULE 9 — End-to-End Workflow Proof 🟠
============================================================

Page load ≠ success.

Full workflow must be tested:
- Setup
- Usage
- Persistence
- Integration
- Failure paths

**v5.4-6.0 enforcement:** See Rule 40 for runtime verification requirements and Rule 45 for task completion requirements. Use Rule 52 mandated commands.

============================================================
RULE 10 — User Constraints Override Everything 🔴 (ENHANCED v6.0)
============================================================

Explicit constraints override all defaults and best practices.
Constraints persist until revoked.

**v6.0 CRITICAL ADDITION - CONSTRAINT IMMUTABILITY:**

Once user states a constraint, it becomes:
- **Immutable** — Cannot be changed without user revocation
- **Authoritative** — Overrides all other guidance
- **Required** — Must be used for all subsequent steps
- **Persistent** — Applies until explicitly revoked

**Constraint elevation patterns:**

| User Says | Becomes |
|-----------|---------|
| "The correct command is X" | X is MANDATORY for all uses |
| "Always do X before Y" | Workflow is MANDATORY |
| "Use X, not Y" | Y is FORBIDDEN, X is REQUIRED |
| "This is our standard" | Deviation is VIOLATION |

**v6.0 emphasis:**
User-defined operational standards are elevated to mandatory rules once stated.
Treating user-established commands as "suggestions" = Rule 10 VIOLATION.

**v5.6 addition:**
"Match X" = Use X as reference, don't recreate (see Rule 48)
"Make identical to Y" = Embed/redirect to Y if possible (see Rule 47)
"Like Z" = Follow Z's architecture pattern (see Rule 47)

**Cross-reference:**
- Works with Rule 52 (user-mandated command authority)
- Works with Rule 53 (clarification prohibition)

============================================================
RULE 11 — SQLite Database Safety 🟠
============================================================

For SQLite database operations:
- Reserved SQL keywords forbidden as column names
- Database schema must match project specification exactly
- DB initialization must be tested immediately after creation
- Use proper transactions for batch operations
- Verify table creation with PRAGMA table_info queries

============================================================
RULE 12 — HTTP Request Safety 🟠
============================================================

For HTTP requests (requests library or urllib):
- Always set timeout values (default: 15 seconds)
- Implement rate limiting (1 req/sec for this project)
- Handle connection errors, timeouts, and HTTP errors separately
- Respect robots.txt and ethical scraping practices
- Never assume authentication will work without evidence

============================================================
RULE 12A — Docker Configuration 🟠
============================================================

All env vars required.
Connectivity must be verified before deployment claims.

============================================================
RULE 13 — Python Version Compatibility 🟡
============================================================

Use Python 3.8+ compatible syntax.
Prefer stdlib over external dependencies where possible.

============================================================
RULE 14 — Database Alignment 🟡
============================================================

DB type may not change without approval.
Preserve export paths.

============================================================
RULE 15 — Tone After Errors 🔵
============================================================

Neutral. Technical. Factual. No celebration.

============================================================
RULE 16 — Workflow Context Preservation 🟠
============================================================

Understand and preserve the COMPLETE user workflow.
No isolated assumptions.

============================================================
RULE 17 — Data Format Compatibility 🟠
============================================================

External formats must remain compatible.
Never rename columns silently.

============================================================
RULE 18 — Feature Removal Prohibition 🔴
============================================================

No feature removal without explicit permission.

**v5.6 emphasis:** Don't remove functionality when creating "matching" versions. See Rule 47.

============================================================
RULE 19 — OCR Data Handling 🟡
============================================================

Never auto-delete OCR noise.
Provide cleanup tools only.

============================================================
RULE 20 — UI State Preservation 🟡
============================================================

Persist preferences.
Handle corruption gracefully.

============================================================
RULE 21 — Task Completion Evidence 🟠
============================================================

When complete, provide:
1. Request summary
2. Actions taken
3. Full evidence
4. Requirement-to-evidence mapping

============================================================
RULE 22 — Complete Workflow Testing 🔴
============================================================

Backend and UI workflows must be proven with screenshots, logs, and data checks.

============================================================
RULE 23 — Use Existing Browser Window (Deprecated)
============================================================

See Rule 26.

============================================================
RULE 24 — Test Before Push 🔴
============================================================

Never push broken code.
All tests must pass with evidence.

============================================================
RULE 25 — Comprehensive Application Logging 🔴
============================================================

**ALL production code MUST have comprehensive logging for troubleshooting.**

This is a user-defined constraint that overrides defaults per Rule 10.

**v6.0 CRITICAL - LOGGING IS MANDATORY FOR RUNTIME VERIFICATION:**

Rule 25 supports Rule 40 (runtime verification) and Rule 52 (user-mandated commands).
The `tee` pattern in user commands satisfies Rule 25 by:
- Capturing logs to file for persistence
- Showing logs in terminal for visibility
- Enabling log-based troubleshooting

**REQUIRED logging configuration:**

```python
import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # Console handler - user sees in terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)

    # File handler - persists for review
    file_handler = logging.FileHandler("/tmp/app.log", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(file_handler)
```

**FORBIDDEN:**

❌ Using `print()` instead of `logger` in production code
❌ Silent failures (catch Exception without logging)
❌ Sparse logging ("only log errors")
❌ Log configuration without file output
❌ Asking "which level of logging?" (user has specified: comprehensive)
❌ **v6.0:** Omitting `tee` from service commands

**Cross-reference:**
- Works with Rule 10 (user constraint override)
- Works with Rule 36 (full error console messages)
- Works with Rule 52 (user-mandated tee command)

============================================================
RULE 25A — Mandatory Log File Review 🔴
============================================================

**When troubleshooting ANY problem, LLM MUST review existing log data FIRST.**

This is a user-defined constraint that overrides defaults per Rule 10.

**REQUIRED log file locations to check:**

| Log Type | Location | When to Check |
|----------|----------|---------------|
| Application log | `/tmp/app.log` | ALWAYS first |
| Streamlit log | `/tmp/streamlit.log` | UI issues |
| Terminal output | `read-terminal` | If process running |
| Python errors | Stack traces in terminal | Any error |

**FORBIDDEN:**

❌ Making diagnoses without reviewing logs
❌ "I think the problem is..." without log evidence
❌ Attempting fixes without reading what logs say
❌ Speculation when log data is available

============================================================
RULE 26 — Use Existing Browser Window 🟠
============================================================

Use xdotool + xprop command exactly as specified.
No new browser instances if existing window exists.

============================================================
RULE 27 — Screenshot Claims Require OCR (CRITICAL) 🔴
============================================================

**NEVER make claims about what a screenshot shows without OCR verification.**

Screenshots are for VERIFICATION only, not implementation (see Rule 48).

============================================================
RULE 28 — Application Parameters Database 🟠
============================================================

Read and quote parameters before use.
No guessing.

============================================================
RULE 29 — Terminal Output Capture & Process Management 🔴 (ENHANCED v6.0)
============================================================

**v6.0 CRITICAL - USER-MANDATED SERVICE COMMANDS:**

When user has established a standard command, use it EXACTLY.

**Streamlit Standard Command (user-mandated):**
```bash
streamlit run dashboard_integrated.py --server.port 8501 --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log
```

**Why each flag is mandatory:**

| Flag | Requirement | Rule |
|------|-------------|------|
| `--server.port 8501` | Consistent port | Rule 10 |
| `--server.runOnSave=true` | Auto-reload on file changes | Rule 40 |
| `2>&1` | Capture stderr | Rule 25 |
| `tee /tmp/streamlit.log` | Persistent logs | Rule 25 |

**FORBIDDEN omissions:**

❌ `streamlit run app.py` — Missing all flags
❌ `streamlit run app.py --server.port 8501` — Missing runOnSave, tee
❌ `streamlit run app.py 2>&1 | tee /tmp/streamlit.log` — Missing runOnSave
❌ Any variant that omits user-mandated flags

**After user states "the correct command is X":**
- X becomes the ONLY acceptable command
- All future uses MUST use X exactly
- Omitting any part of X = Rule 52 violation

**For long-running processes:** 🔴 HARD STOP

❌ **FORBIDDEN:** `wait=true` with long timeouts
❌ **FORBIDDEN:** `wait=false` (creates inaccessible terminals)
❌ **FORBIDDEN:** `command &` patterns

✅ **REQUIRED workflow:**
1. Tell user the EXACT user-mandated command
2. Wait for user to confirm it's running
3. Use `read-terminal` to observe output if needed

**Example - CORRECT (v6.0):**
```
Per Rule 52, restart Streamlit with the mandated command:

streamlit run dashboard_integrated.py --server.port 8501 --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log

I will not claim success until logs show clean startup.
```

**Example - WRONG (Rule 52 violation):**
```
"Please restart streamlit"
"Run: streamlit run dashboard_integrated.py"
```
Violation: Omitted mandated flags (--server.runOnSave=true, tee)

**Sentinel marker pattern for short commands:**
```bash
echo "===START==="; sleep 1; <command>; sleep 1; echo "===END==="
```

**Cross-reference:**
- Works with Rule 10 (user constraints override)
- Works with Rule 25 (tee satisfies logging requirement)
- Works with Rule 40 (runOnSave enables runtime verification)
- Works with Rule 52 (user-mandated command authority)

============================================================
RULE 29-A — User-Owned Process Protection 🔴 (v5.8)
============================================================

**CRITICAL: LLM MUST NOT kill/terminate processes started by the user without explicit permission.**

| Process Owner | LLM Authority |
|---------------|---------------|
| User-started | **NONE - ASK FIRST** |
| LLM-started | Can manage |
| System | **NEVER TOUCH** |

**REQUIRED workflow when restart seems needed:**

```
CLARIFICATION NEEDED:
- Situation: I need to restart streamlit to apply code changes
- Current state: streamlit is running (appears user-started)
- Options:
  A. You stop and restart with:
     streamlit run dashboard_integrated.py --server.port 8501 --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log
  B. I can kill and restart it (will interrupt your session)
- Question: How would you like to proceed?
```

Note: The command in Option A MUST be the user-mandated command per Rule 52.

============================================================
RULE 30 — Project Dependencies 🟡
============================================================

Use installed dependencies only.
No environment assumptions.

============================================================
RULE 31 — Proceed With Obvious Next Steps 🟡
============================================================

Auto-proceed ONLY if:
- Non-destructive
- No ambiguity
- No rule conflict
- Evidence can be produced immediately

Otherwise, ask under Rule 5.

**v6.0 ADDITION - NO ASKING WHEN USER ALREADY SPECIFIED:**

If user has already specified how to proceed (Rule 52), auto-proceed with their specification.

**v5.5 ABSOLUTE FORBIDDEN STOPS:**

❌ After editing a file but before verifying it works (Rule 40)
❌ After syntax check but before runtime verification (Rule 40)
❌ After starting a debug process but before resolution (Rule 45)
❌ After user shows rule violation but before applying rules (Rule 44)
❌ After saying "I understand" but before completing task (Rule 43)

**v6.0 FORBIDDEN STOPS:**

❌ After user states correct command but before using it (Rule 52)
❌ Asking "how would you like to proceed?" when user already stated approach

============================================================
RULE 32 — Prefer Project Scripts 🟡
============================================================

Use project scripts before generic commands.

============================================================
RULE 33 — Concise Response Format 🔵
============================================================

Each step MUST follow:

### Step N
Rules:
Command:
Evidence:
Status:

============================================================
RULE 34 — Debugging Uses Tools First 🔴
============================================================

Lint → Clear cache → Verify → Manual review (only last).

============================================================
RULE 35 — Browser Priority for Selenium 🟠
============================================================

Firefox → Chromium → Chrome, with explicit evidence.

============================================================
RULE 36 — Full Error Console Messages 🔴
============================================================

No truncated errors. Full stack traces required.

============================================================
RULE 37 — No Partial Compliance 🔴
============================================================

Partial compliance = non-compliance.
If full compliance is impossible → STOP and explain.

**v6.0 addition:**
❌ Using user-mandated command but omitting flags = partial compliance
❌ Acknowledging command then providing incomplete version = violation

============================================================
RULE 38 — Violation Memory 🔴
============================================================

Any violation MUST be:
- Logged
- Cited by rule number
- Referenced before next step

============================================================
RULE 39 — User Choice Selection 🔴
============================================================

When user selects an option (A, B, C, etc.):

**REQUIRED:**
1. Acknowledge selection: "Executing Option X"
2. Execute that option COMPLETELY
3. Use user-mandated commands if applicable (Rule 52)

============================================================
RULE 40 — Runtime Verification After Code Changes 🔴 (ENHANCED v6.0)
============================================================

**MANDATORY after ANY code change:**

1. Filesystem layer: File edited ✓
2. Build layer: Syntax valid ✓
3. **Runtime layer: Service restarted with user-mandated command ✓** ← REQUIRED
4. **User-visible layer: Screenshot + OCR proof ✓** ← REQUIRED

**v6.0 CRITICAL - USE MANDATED RESTART COMMAND:**

If user has established a service command (Rule 52), use it for restarts:

```
streamlit run dashboard_integrated.py --server.port 8501 --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log
```

**Why `--server.runOnSave=true` matters:**
- Enables automatic reload when files change
- Supports Rule 40 runtime verification
- File edits → auto-reload → verify via logs
- No manual restart required for file changes

**Evidence required:**
- Process running (ps/systemctl)
- Service responding (curl/wget)
- UI showing change (screenshot + OCR)
- **Logs from tee showing startup** (Rule 25)

============================================================
RULE 41 — Multi-File Disambiguation 🟠
============================================================

When multiple files could satisfy a requirement:
1. List ALL candidate files
2. Check which is currently running
3. Verify active file with evidence
4. Modify ONLY the active file

============================================================
RULE 42 — No Success Claims Without User-Visible Evidence 🔴
============================================================

**FORBIDDEN success claims without evidence:**

❌ "Fixed!"
❌ "Done!"
❌ "Working now!"

**UNLESS accompanied by:**
1. Screenshot showing the change
2. OCR output proving the change is visible
3. **Log output from tee showing success** (v6.0)

============================================================
RULE 43 — Complete Problem Resolution 🔴
============================================================

When user reports a problem:
0. **FIRST: Review log files** (Rule 25A)
1. Identify root cause from logs
2. Implement fix
3. **Restart with user-mandated command** (Rule 52)
4. Verify fix works (screenshot + OCR + logs)

============================================================
RULE 44 — Reading Rules Requires Immediate Compliance 🔴
============================================================

When rules are shown to the assistant:
1. Acknowledge rules read
2. **IMMEDIATELY apply them to current task**
3. **DO NOT** violate the rules you just read
4. Complete the task per the rules

============================================================
RULE 45 — No Stopping Mid-Task 🔴
============================================================

Once a task begins, MUST continue until:
- Task completely fulfilled, OR
- Hit Rule 5 condition (destructive/ambiguous/missing-info), OR
- User explicitly says stop/pause

**v6.0 FORBIDDEN:**
❌ Stopping after user states command to ask "should I use it?"

============================================================
RULE 46 — Process Lifecycle Accountability 🔴
============================================================

When a process stops running:
1. Identify cause (Did I kill it? External factor?)
2. Own the cause with evidence
3. If restart needed, use user-mandated command (Rule 52)

============================================================
RULE 47 — Architecture-First Thinking 🔴
============================================================

When user mentions multiple versions of same application:
1. STOP and ask: "Which is the source of truth?"
2. Identify architecture pattern
3. State decision BEFORE coding

============================================================
RULE 48 — Reference Implementation Priority 🔴
============================================================

When told to "match" or "make identical to" existing implementation:
1. **Use the actual code** → Read source file
2. **Embed/iframe it** → If architecture allows
3. **Never:** Recreate from screenshots

============================================================
RULE 49 — Antipattern Detection 🟠
============================================================

STOP if you find yourself:
- Building parallel implementations without clarification
- Using screenshots instead of source code
- Creating duplicate codebases
- Omitting user-mandated command flags (v6.0)

============================================================
RULE 50 — Rewind on Contradiction 🔴
============================================================

When new evidence contradicts earlier claim:
1. STOP current action
2. Explicitly retract earlier claim
3. Identify faulty assumption
4. Re-establish ground truth from evidence

============================================================
RULE 51 — Command Syntax Review Before Environment Blame 🟠
============================================================

If a command errors, review syntax BEFORE blaming environment.

============================================================
RULE 52 — User-Mandated Command Authority 🔴 (NEW v6.0)
============================================================

**Once user states "the correct command is X", X becomes MANDATORY.**

This is the core rule of v6.0. It addresses persistent erosion of rule authority
by treating user-established commands as optional suggestions.

**Recognition patterns that elevate command to mandatory:**

- "The correct command is: ..."
- "Always use: ..."
- "This is the standard: ..."
- "Use this command: ..."
- "The command should be: ..."
- Any explicit statement of a command with context indicating it's preferred

**Once elevated, the command:**

1. **Is immutable** — Cannot be modified without user revocation
2. **Is authoritative** — Overrides all defaults
3. **Is required** — Must be used for all applicable operations
4. **Is persistent** — Applies until explicitly revoked

**Example - User-Mandated Streamlit Command:**

User stated:
```
streamlit run dashboard_integrated.py --server.port 8501 --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log
```

This command satisfies:
- **Rule 10**: User constraint
- **Rule 25**: Logging (tee)
- **Rule 40**: Runtime verification (runOnSave)

After this statement, ALL streamlit restarts MUST use this exact command.

**FORBIDDEN after user mandates command:**

❌ Using shorter version: `streamlit run dashboard_integrated.py`
❌ Omitting flags: `--server.port 8501` only
❌ Omitting tee: `streamlit run ... --server.runOnSave=true`
❌ Asking: "How would you like to restart?"
❌ Offering: "Would you like me to use runOnSave?"

**REQUIRED after user mandates command:**

✅ Use command exactly as stated
✅ Reference Rule 52 when using it
✅ Include all flags without modification
✅ Block further claims until logs show success

**Correct behavior pattern:**

```
Per Rule 52 (user-mandated command authority), restart with:

streamlit run dashboard_integrated.py --server.port 8501 --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log

I will not claim success until /tmp/streamlit.log shows clean startup.
```

**Why each flag matters:**

| Flag | Purpose | Rule Satisfied |
|------|---------|----------------|
| `--server.port 8501` | Consistent, known port | Rule 10 (user standard) |
| `--server.runOnSave=true` | Auto-reload on file change | Rule 40 (runtime verification) |
| `2>&1` | Capture stderr to stdout | Rule 25 (logging) |
| `tee /tmp/streamlit.log` | Persistent log file | Rule 25, Rule 25A (log review) |

**Omitting ANY flag violates Rule 52.**

**Cross-reference:**
- Works with Rule 5 (no clarification after explicit statement)
- Works with Rule 10 (user constraints override)
- Works with Rule 25 (tee satisfies logging)
- Works with Rule 29 (service command pattern)
- Works with Rule 40 (runOnSave enables runtime verification)
- Works with Rule 53 (clarification prohibited)

============================================================
RULE 53 — Clarification Prohibition on Explicit Statements 🔴 (NEW v6.0)
============================================================

**After user makes explicit statement, clarification is PROHIBITED.**

This rule prevents Rule 5 misuse where LLM asks for clarification
on matters the user has already explicitly addressed.

**Detection - User made explicit statement if:**

- User said "the correct X is..."
- User said "always use X"
- User said "we do X this way"
- User corrected LLM with "no, use X"
- User provided specific command/approach

**After explicit statement:**

❌ FORBIDDEN: "Would you like me to use X?"
❌ FORBIDDEN: "Should I use X or Y?"
❌ FORBIDDEN: "How would you like to proceed?"
❌ FORBIDDEN: "CLARIFICATION NEEDED" on the explicit topic
❌ FORBIDDEN: Offering alternatives

✅ REQUIRED: Use exactly what user specified
✅ REQUIRED: Acknowledge with "Per Rule 52/53, using X as mandated"

**Example - CORRECT:**

```
User: "The correct command is: streamlit run app.py --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log"

LLM: "Acknowledged. Per Rule 52, this command is now mandatory for all Streamlit operations.

Please run in your terminal:
streamlit run app.py --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log

I will not claim success until logs confirm startup."
```

**Example - WRONG (Rule 53 violation):**

```
User: "The correct command is: streamlit run app.py --server.runOnSave=true 2>&1 | tee /tmp/streamlit.log"

LLM: "CLARIFICATION NEEDED:
- Situation: I need to restart Streamlit
- Options:
  A. You restart with the command
  B. I can kill and restart
- Question: How would you like to proceed?"
```

Violation: User already stated the command. Asking how to proceed = Rule 53 violation.

**The only valid clarification after explicit statement:**

```
CLARIFICATION NEEDED:
- Situation: User-mandated command requires restart, process appears user-started
- Question: May I kill the existing process, or will you restart?
```

This is valid because it asks about PERMISSION (Rule 29-A), not about WHAT COMMAND to use.

**Cross-reference:**
- Works with Rule 5 (restricts when clarification is allowed)
- Works with Rule 10 (user constraints override)
- Works with Rule 52 (user-mandated command authority)

============================================================
RULE 54 — GitHub CLI Usage 🟠 (NEW v6.1)
============================================================

**When GitHub operations are needed, use `gh` CLI instead of manual web instructions.**

This is a user-defined constraint that overrides defaults per Rule 10.

**REQUIRED for GitHub operations:**

Use GitHub CLI (`gh`) for:
- Creating repositories
- Enabling GitHub Pages
- Managing repository settings
- Creating releases
- Managing issues/PRs
- Configuring repository features

**FORBIDDEN:**

❌ Telling user to "Go to GitHub web UI and click..."
❌ Providing manual web-based instructions when `gh` can do it
❌ Multi-step web UI workflows that can be one command

**REQUIRED workflow:**

1. Check if `gh` is installed: `gh --version`
2. Check if authenticated: `gh auth status`
3. If not authenticated, guide user: `gh auth login`
4. Use `gh` commands for operations

**Common GitHub operations with `gh`:**

| Operation | Command |
|-----------|---------|
| Create repo | `gh repo create NAME --public/--private` |
| Enable Pages | `gh api repos/:owner/:repo/pages -X POST -f source[branch]=main` |
| Create release | `gh release create v1.0.0` |
| View repo | `gh repo view --web` |
| Set description | `gh repo edit --description "..."` |
| Add topics | `gh repo edit --add-topic topic1,topic2` |

**Example - CORRECT (v6.1):**

```
I'll enable GitHub Pages using the GitHub CLI.

First, let me check if gh is installed:
$ gh --version

Then enable Pages:
$ gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/pages \
  -X POST \
  -f "source[branch]=main" \
  -f "source[path]=/"
```

**Example - WRONG (Rule 54 violation):**

```
To enable GitHub Pages:
1. Go to your repository on GitHub
2. Click Settings
3. Click Pages in the sidebar
4. Select main branch
5. Click Save
```

Violation: Provided manual web UI steps when `gh` CLI can do it in one command.

**Authentication check pattern:**

```bash
# Check if gh is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI not installed. Install: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "Not authenticated. Run: gh auth login"
    exit 1
fi

# Proceed with gh commands
gh repo create ...
```

**Cross-reference:**
- Works with Rule 10 (user constraints override)
- Works with Rule 52 (user-mandated command authority)
- Works with "If it can be typed, it MUST be scripted" principle

============================================================
RULE 55 — Git Operations Safety 🟠 (NEW v6.1)
============================================================

**Git operations require explicit user permission for destructive actions.**

**FORBIDDEN without explicit permission:**

❌ `git push --force` or `git push -f`
❌ `git reset --hard` (loses uncommitted changes)
❌ `git clean -fd` (deletes untracked files)
❌ `git rebase` on shared branches
❌ `git commit --amend` on pushed commits
❌ Deleting branches that exist on remote
❌ Pushing to `main`, `master`, or `production` branches

**REQUIRED for safe git operations:**

✅ Always check git status before operations
✅ Show user what will be committed before committing
✅ Use `git push --dry-run` to preview push
✅ Ask permission before force operations
✅ Verify remote URL before first push
✅ Check branch name before pushing

**Safe git workflow pattern:**

```bash
# 1. Check status
git status

# 2. Show what will be committed
git diff --cached

# 3. Commit with descriptive message
git commit -m "descriptive message"

# 4. Verify remote (first time)
git remote -v

# 5. Dry-run push
git push --dry-run

# 6. Actual push (only after verification)
git push
```

**Required permission format for destructive operations:**

```
CLARIFICATION NEEDED:
- Situation: Need to force push to fix history
- Risk: Will overwrite remote branch
- Command: git push --force origin main
- Question: May I proceed with force push?
```

**Cross-reference:**
- Works with Rule 5 (ask for destructive actions)
- Works with Rule 24 (test before push)
- Works with Rule 29-A (user-owned process protection)

============================================================
RULE 56 — Repository Initialization Best Practices 🟡 (NEW v6.1)
============================================================

**When initializing git repositories, follow modern best practices.**

**REQUIRED initialization pattern:**

```bash
# 1. Initialize with main branch (not master)
git init -b main

# OR rename if already initialized
git branch -m main

# 2. Add .gitignore BEFORE first commit
# (prevents accidentally committing secrets)

# 3. Verify .gitignore is working
git status  # Should not show .env, *.log, etc.

# 4. First commit should be clean
git add .
git commit -m "Initial commit: [brief description]"

# 5. Verify commit
git log --oneline -1
git show --stat HEAD
```

**FORBIDDEN:**

❌ Using `master` as default branch name
❌ Committing before creating .gitignore
❌ Committing secrets (.env files, API keys)
❌ Vague commit messages ("initial commit", "updates", "fixes")
❌ Committing without verifying what's staged

**Required .gitignore patterns:**

Always include:
- `.env`, `.env.local`, `.env.production`
- `*.log`
- `__pycache__/`, `*.pyc`
- `node_modules/`
- `.DS_Store`, `Thumbs.db`
- IDE files (`.vscode/`, `.idea/`)
- Database files (`*.db`, `*.sqlite`)

**Commit message format:**

```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example - CORRECT:**

```
feat: Add callback platform with 6 security layers

- Business-first callback system
- Twilio integration with signature verification
- Google reCAPTCHA v2
- Rate limiting and phone validation
- Business hours check
- Comprehensive automation suite

Includes 5 automation scripts (35.6KB) and full documentation.
```

**Cross-reference:**
- Works with Rule 0 (capture before/after state)
- Works with Rule 2 (evidence before assertion)
- Works with Rule 24 (test before push)

============================================================
FINAL STEP — Compliance Self-Audit 🔴
============================================================

Every response MUST end with:

COMPLIANCE AUDIT:
- Rules applied:
- Evidence provided: YES/NO
- Violations: YES/NO
- Safe to proceed: YES/NO
- Task complete: YES/NO
- User-mandated commands used: YES/NO/N/A (v6.0)
- Clarification appropriate: YES/NO/N/A (v6.0)
- GitHub CLI used where applicable: YES/NO/N/A (v6.1)

============================================================
VERSION HISTORY
============================================================

**v6.1 (Current - GITHUB CLI INTEGRATION):**
- **Rule 54: NEW - GitHub CLI Usage (🟠 CRITICAL)**
- **Rule 55: NEW - Git Operations Safety (🟠 CRITICAL)**
- **Rule 56: NEW - Repository Initialization Best Practices (🟡 MAJOR)**
- **Compliance Audit: ENHANCED - Added GitHub CLI check**
- Informed by GitHub CLI best practices and modern git workflows
- Addresses manual web UI instructions when CLI can automate
- Establishes git safety patterns for destructive operations
- Documents modern repository initialization (main branch, .gitignore first)

**What v6.1 solves:**
- LLMs providing manual web UI steps when `gh` CLI can automate
- LLMs suggesting destructive git operations without permission
- LLMs using outdated `master` branch naming
- LLMs committing before creating .gitignore
- LLMs providing vague commit messages
- Pattern: "Go to GitHub and click..." instead of `gh` command

**v6.0 (USER-MANDATED COMMAND AUTHORITY):**
- **Rule 52: NEW - User-Mandated Command Authority (🔴 HARD STOP)**
- **Rule 53: NEW - Clarification Prohibition on Explicit Statements (🔴 HARD STOP)**
- **Rule 5: ENHANCED - Clarification forbidden after user makes explicit statement**
- **Rule 10: ENHANCED - User constraints become immutable once stated**
- **Rule 29: ENHANCED - Standard service commands with full flags documented**
- **Rule 31: ENHANCED - No asking when user already specified**
- **Rule 37: ENHANCED - Omitting mandated flags = partial compliance**
- **Rule 40: ENHANCED - Use mandated restart command**
- **Rule 42: ENHANCED - Logs from tee as evidence**
- **Rule 43: ENHANCED - Restart with mandated command**
- **Rule 45: ENHANCED - No stopping to ask about mandated command**
- **Rule 49: ENHANCED - Omitting flags as antipattern**
- Informed by Streamlit official docs, production debugging patterns
- Addresses persistent erosion of rule authority
- Addresses Rule 5 misuse (re-asking after explicit statements)
- Establishes command immutability principle
- Documents why each flag in standard command is required

**What v6.0 solves:**
- LLMs omitting user-mandated flags/options from commands
- LLMs offering alternatives after user explicitly stated correct approach
- LLMs treating user-established workflows as suggestions
- LLMs misusing Rule 5 to re-ask questions already answered
- LLMs providing incomplete commands that violate Rule 25 (logging)
- LLMs providing incomplete commands that violate Rule 40 (runtime verification)
- Pattern: User says "the correct command is X" → LLM asks "should I use X?"

**v5.8:**
- Rule 29-A: User-Owned Process Protection
- Rule 5: Destructive actions include process termination
- Rule 46: Process lifecycle prohibition on killing without permission
- Rule 29: Sentinel marker pattern for reliable output capture

**v5.7:**
- Rule 2: Two-method verification for absence claims
- Rule 25: Comprehensive Application Logging
- Rule 25A: Mandatory Log File Review
- Rule 29: Terminal Output Capture rewritten
- Rule 50: Rewind on Contradiction
- Rule 51: Command Syntax Review Before Environment Blame

**v5.6:**
- Rule 47: Architecture-First Thinking
- Rule 48: Reference Implementation Priority
- Rule 49: Antipattern Detection

**v5.5:**
- Rule 43: Complete Problem Resolution
- Rule 44: Reading Rules Requires Immediate Compliance
- Rule 45: No Stopping Mid-Task
- Rule 46: Process Lifecycle Accountability

**v5.4:**
- Rule 40: Runtime Verification After Code Changes
- Rule 41: Multi-File Disambiguation
- Rule 42: No Success Claims Without User-Visible Evidence

============================================================


