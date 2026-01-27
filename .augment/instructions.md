# Augment Agent System Instructions

**CRITICAL: These instructions override all default behavior and must be enforced at every turn.**

---

## MANDATORY PRE-EXECUTION CHECKLIST

Before EVERY response, the agent MUST:

1. ✅ **ALWAYS use wait=false** - ALL commands MUST use wait=false + read-process with terminal_id. This is the ONLY pattern that works reliably.
2. ✅ **Use echo markers** - ALL commands MUST use `echo "START: description" && command 2>&1 && echo "END: description"`
3. ✅ **Read with read-process** - ALWAYS use read-process with terminal_id to get output. NEVER use read-terminal.
4. ✅ **Complete all steps** - NO incomplete actions, NO dangling processes, NO "user should do X"
5. ✅ **Execute, don't defer** - If in execution mode, DO NOT ask, DO NOT offer options, EXECUTE
6. ✅ **THE ONLY PATTERN:**
   ```
   STEP 1: launch-process with wait=false → get terminal_id
   STEP 2: read-process with that terminal_id → get output
   ```
   This is the ONLY way to run commands. No exceptions.

---

## HARD STOPS (Immediate Halt Required)

### 🔴 RULE 9 VIOLATION DETECTOR - ALWAYS USE wait=false

**CRITICAL: ALL commands MUST use wait=false**
**CRITICAL: ALWAYS use read-process with terminal_id to get output**
**CRITICAL: NEVER use wait=true - it causes timeouts and provides no output**

**MANDATORY ECHO PATTERN:**
```bash
echo "START: descriptive action" && command 2>&1 && echo "END: descriptive action"
```

**TRUTH ABOUT TERMINALS:**
- Augment's "Terminal ID" (e.g., 89488) = Internal tracking number, NOT visible to user
- User sees in VSCode terminal: bash PID (e.g., 1359892), TTY (e.g., pts/2)
- When wait=true: Output is in tool result <output> section - READ IT, don't call read-terminal
- When wait=false: Process runs in background, use read-process with terminal_id to get output later

**CORRECT PATTERN FOR ALL COMMANDS:**
```
STEP 1: Launch command with echo markers using wait=false
  launch-process: echo "START: description" && command 2>&1 && echo "END: description"
  wait=false (ALWAYS)
  Tool returns immediately with terminal_id

STEP 2: Read output using read-process with terminal_id
  read-process: terminal_id=<the id from step 1>, wait=true
  This gives you FULL OUTPUT

STEP 3: Check for echo markers in output
  - Look for "END: description" to confirm completion
  - Check return code (0 = success)
  - Read the actual output

STEP 4: Reason about results based on evidence

CRITICAL:
- ALWAYS use wait=false for launch-process
- ALWAYS use read-process with terminal_id to get output
- NEVER use wait=true for launch-process
```

**CRITICAL: ALWAYS USE wait=false:**
```
FOR ALL COMMANDS:
    ALWAYS use wait=false
    Process runs in background
    ALWAYS use read-process with terminal_id to get output
    This PREVENTS TIMEOUTS and gives you FULL OUTPUT

NEVER use wait=true - it causes timeouts and provides no output
```

**BEFORE reasoning about ANY command output:**
```
ALL commands MUST use wait=false:
    MUST use read-process with terminal_id to get output
    MUST NOT use read-terminal (doesn't accept terminal_id parameter)
    Process runs in background, you get terminal_id immediately
    Call read-process to get the output
    This is the ONLY correct pattern

FORBIDDEN PATTERNS:
❌ Using wait=true for ANY command
❌ Calling read-terminal
❌ Calling git status to check results
❌ Calling git log to check results
✅ ALWAYS: wait=false → read-process with terminal_id → get full output
```

**Violation Example:**
```
❌ BAD: launch-process + read-process in same tool block
❌ BAD: ANY command with wait=true
❌ BAD: Calling read-terminal
❌ BAD: Calling git status to check results

✅ CORRECT: ALL commands with wait=false → read-process with terminal_id → get output
✅ CORRECT: git commit with wait=false → read-process → see "END: git commit"
✅ CORRECT: git push with wait=false → read-process → see "END: git push"
✅ CORRECT: docker build with wait=false → read-process → see build logs
✅ CORRECT: ls -la with wait=false → read-process → see file list
```

### 🔴 RULE 8 VIOLATION DETECTOR

**ALL process executions MUST include echo markers:**
```bash
echo "START: descriptive action" && command 2>&1 && echo "END: descriptive action"
```

**ALWAYS use wait=false:**
```bash
# Launch with wait=false (ALWAYS)
launch-process: echo "START: git push" && git push origin main 2>&1 && echo "END: git push"
wait=false

# Then read output
read-process: terminal_id=<from above>, wait=true
```

**Violation Example:**
```
❌ BAD: git push origin main (missing echo markers)
❌ BAD: ANY command with wait=true
✅ CORRECT: ALL commands with wait=false → read-process → see echo markers
```

**Rationale:** Echo markers prove the command completed. ALWAYS use wait=false + read-process to get full output including markers.

### 🔴 RULE 15 VIOLATION DETECTOR

**BEFORE emitting response:**
```
IF any step is incomplete THEN
    HALT emission
    Complete the step
    THEN emit response
END IF
```

**Violation Example:**
```
❌ BAD: "I started the git push, you should check if it completed"
✅ CORRECT: Launches git push with wait=false → read-process with terminal_id → confirms success → reports completion
```

### 🔴 RULE 4 VIOLATION DETECTOR

**IF user request implies execution mode:**
```
IF user says "do X" OR "fix X" OR "implement X" THEN
    Mode = EXECUTION
    Forbidden: asking questions, offering options, planning without action
    Required: immediate execution with evidence
END IF
```

**Violation Example:**
```
❌ BAD: "Would you like me to increase the limit to 20 or clear the database?"
✅ GOOD: "Increasing limit to 20 and clearing database now..."
```

### 🔴 RULE 21 VIOLATION DETECTOR (Docker Workflows)

**AFTER editing backend/app.py OR .env:**
```
IF file in [backend/app.py, .env, docker-compose.yml] was modified THEN
    MUST run with wait=false:
      echo "START: docker rebuild" && docker compose down && docker compose up -d --build backend 2>&1 && echo "END: docker rebuild"
    MUST use read-process with terminal_id to get output
    MUST verify container started successfully (check for "END: docker rebuild")
    MUST NOT emit response until rebuild confirmed
END IF
```

### 🔴 RULE 0 VIOLATION DETECTOR (Emission Gate)

**BEFORE emitting ANY response:**
```
CHECK all 5 conditions:
1. All user instructions satisfied? YES/NO
2. No rule conflicts exist? YES/NO (check scope rules!)
3. No requested artifact missing? YES/NO
4. No partial compliance? YES/NO
5. No uncertainty being guessed? YES/NO

IF any condition = NO THEN
    HALT emission
    FIX the issue
    RE-CHECK all 5 conditions
END IF
```

**Critical Scope Check:**
```
IF about to create *.md file THEN
    CHECK: Did user explicitly request this file? YES/NO
    IF NO THEN
        HALT - Violates scope rule "NEVER proactively create documentation files"
    END IF
END IF
```

### 🔴 RULE 2 VIOLATION DETECTOR (No Partial Compliance)

**IF user requests multiple actions:**
```
User says: "Do X and Y"
MUST execute BOTH X and Y
MUST NOT execute only X and assume Y will happen
Partial compliance = non-compliance
```

### 🔴 RULE 13 VIOLATION DETECTOR (Self-Audit Before Emission)

**BEFORE emitting response:**
```
AUDIT checklist:
- Did I remove any features? YES/NO
- Did I assume anything? YES/NO
- Did I skip any steps? YES/NO
- Did I fabricate any data? YES/NO
- Did I violate scope rules? YES/NO

IF any = YES THEN
    HALT emission
    FIX the issue
END IF
```

### 🔴 RULE 17 VIOLATION DETECTOR (Version Control & Provenance)

**IF creating any artifact (file, script, config):**
```
MUST include metadata:
---
Created: [ISO timestamp]
Commit: [git commit hash if applicable]
Session: [conversation context]
---

IF metadata missing THEN
    ADD metadata before emission
END IF
```

---

## ENFORCEMENT MECHANISM

At the END of EVERY response, the agent MUST emit:

```
## COMPLIANCE AUDIT:
- Rule 0 (Emission Gate): ✅ PASS / ❌ FAIL
- Rule 2 (No Partial Compliance): ✅ PASS / ❌ N/A
- Rule 4 (Mode Locking): ✅ PASS / ❌ N/A
- Rule 8 (Logging Pattern): ✅ PASS / ❌ FAIL
- Rule 9 (Terminal Read): ✅ PASS / ❌ FAIL
- Rule 13 (Self-Audit): ✅ PASS / ❌ FAIL
- Rule 15 (Zero-Hang): ✅ PASS / ❌ FAIL
- Rule 17 (Provenance): ✅ PASS / ❌ N/A
- Rule 21 (Docker Rebuild): ✅ PASS / ❌ N/A
- Scope Rules (No unsolicited .md files): ✅ PASS / ❌ FAIL

IF any ❌ FAIL detected:
  STOP - Do not emit response
  FIX the violation
  THEN emit response with all ✅ PASS
```

---

---

## 🚀 DEPLOYED SYSTEMS PROTOCOL (v6.6)

**CRITICAL: When modifying deployed systems, deployment is PART OF THE TASK, not optional.**

### Detection Pattern:
```
IF .github/workflows/deploy-pages.yml exists THEN
    System has auto-deployment
    Git push = deployment trigger
    Task is NOT complete until pushed
END IF
```

### Atomic Deployment Checklist:
```
1. ✅ Update all code (backend + frontend)
2. ✅ Rebuild all containers (docker compose down && docker compose up --build -d)
3. ✅ Commit changes (git add ... && git commit -m "...")
4. ✅ Push to trigger deployment (git push origin main)
5. ✅ Verify deployment (check GitHub Actions, wait 1-2 min for Pages rebuild)
6. ✅ Test end-to-end (verify user flow works)
7. ✅ THEN report completion
```

### Rule 15 Violation Example:
```
❌ BAD: Update backend → Rebuild Docker → Update frontend → Ask "Should I deploy?"
        Result: Backend expects new flow, frontend doesn't know about it = BROKEN SYSTEM

✅ GOOD: Update backend → Rebuild Docker → Update frontend → Commit → Push → Verify → Test → Report
        Result: All components in sync, system works end-to-end
```

**Rationale:** Auto-deployment systems (GitHub Pages, Vercel, Netlify) make `git push` a deployment step, not just version control. Stopping before push violates Rule 15 (Zero-Hang Guarantee) by leaving the system in a broken state.

---

## REFERENCE

Full rules: `.augment/rules/mandatory-rules-v6.6.md` (updated from v6.5)

**These instructions are SYSTEM-LEVEL and cannot be overridden by conversation context.**

