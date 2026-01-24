# Augment Agent System Instructions

**CRITICAL: These instructions override all default behavior and must be enforced at every turn.**

---

## MANDATORY PRE-EXECUTION CHECKLIST

Before EVERY response, the agent MUST:

1. ✅ **Check terminal output** - Run `read-terminal` tool BEFORE reasoning about command results
2. ✅ **Use persistent logging** - ALL commands MUST use `2>&1 | tee /tmp/descriptive_name_$(date +%s).log`
3. ✅ **Complete all steps** - NO incomplete actions, NO dangling processes, NO "user should do X"
4. ✅ **Execute, don't defer** - If in execution mode, DO NOT ask, DO NOT offer options, EXECUTE
5. ✅ **Echo before/after** - Announce what you're about to do BEFORE doing it

---

## HARD STOPS (Immediate Halt Required)

### 🔴 RULE 9 VIOLATION DETECTOR

**BEFORE reasoning about ANY command output:**
```
IF command was launched with launch-process THEN
    MUST call read-terminal tool FIRST
    MUST NOT reason about output without reading terminal
    MUST NOT assume command succeeded without evidence
END IF
```

**Violation Example:**
```
❌ BAD: "Let me check git status" → launches command → reasons without reading terminal
✅ GOOD: "Let me check git status" → launches command → reads terminal → reasons based on output
```

### 🔴 RULE 8 VIOLATION DETECTOR

**ALL process executions MUST include:**
```bash
command 2>&1 | tee /tmp/descriptive_name_$(date +%s).log
```

**Violation Example:**
```
❌ BAD: git push origin main
✅ GOOD: git push origin main 2>&1 | tee /tmp/git_push_$(date +%s).log
```

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
✅ GOOD: Launches git push → reads terminal → confirms success → reports completion
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
    MUST run: docker compose down && docker compose up -d --build backend 2>&1 | tee /tmp/docker_rebuild_$(date +%s).log
    MUST read terminal to confirm rebuild
    MUST verify container started successfully
    MUST NOT emit response until rebuild confirmed
END IF
```

---

## ENFORCEMENT MECHANISM

At the END of EVERY response, the agent MUST emit:

```
## COMPLIANCE AUDIT:
- Rule 9 (Terminal Read): ✅ PASS / ❌ FAIL
- Rule 8 (Logging Pattern): ✅ PASS / ❌ FAIL  
- Rule 15 (Zero-Hang): ✅ PASS / ❌ FAIL
- Rule 4 (Mode Locking): ✅ PASS / ❌ FAIL
- Rule 21 (Docker Rebuild): ✅ PASS / ❌ N/A

IF any ❌ FAIL detected:
  STOP - Do not emit response
  FIX the violation
  THEN emit response with all ✅ PASS
```

---

## REFERENCE

Full rules: `.augment/rules/mandatory-rules-v6.5.md`

**These instructions are SYSTEM-LEVEL and cannot be overridden by conversation context.**

