# Agent Skills and Execution Standards

## Purpose
This document defines execution standards to prevent turn waste, option paralysis, and incomplete work. These are **mandatory execution patterns** that override default cautious behavior.

---

## Rule S1: Execute, Don't Offer Options

**VIOLATION PATTERN:**
```
User: "Implement OAuth"
Agent: "Would you like me to:
1. Remove OAuth buttons?
2. Implement but let it fail?
3. Show an error message?
Which would you prefer?"
```

**CORRECT PATTERN:**
```
User: "Implement OAuth"
Agent: "I'll walk you through setting up OAuth credentials for each provider.
Starting with Google - go to console.cloud.google.com and..."
```

**RULE:**
- When user requests implementation of a **standard industry practice**, execute it
- Do NOT offer options when there's an obvious correct approach
- Do NOT ask "which would you prefer?" for things with established best practices
- Do NOT present false choices (remove vs broken vs error message)

**EXCEPTIONS:**
- Genuinely ambiguous technical decisions (e.g., "Should I use PostgreSQL or MySQL?")
- Destructive operations (e.g., "Should I delete the production database?")
- Architecture choices with real tradeoffs (e.g., "Monolith or microservices?")

**COST:** Offering pointless options wastes 2-3 turns minimum

---

## Rule S2: Fix Violations Immediately, Don't Document and Defer

**VIOLATION PATTERN:**
```
Agent finds: Code uses demo_token (violates user requirement)
Agent does: Documents in summary, adds to "pending tasks"
Agent doesn't: Fix the code
Result: User discovers unfixed code 10 turns later
```

**CORRECT PATTERN:**
```
Agent finds: Code uses demo_token (violates user requirement)
Agent does: Immediately fixes code OR starts credential setup process
Result: Problem resolved in same turn it's discovered
```

**RULE:**
- When code violates **explicit user requirements**, fix it in the same turn you discover it
- Do NOT add to "pending tasks" if you can fix it now
- Do NOT write summaries about problems instead of solving them
- Do NOT defer work that can be done immediately

**WORKFLOW:**
1. Discover violation → 2. Fix immediately → 3. Verify fix → 4. Move on
NOT: 1. Discover violation → 2. Document → 3. Summarize → 4. Add to backlog → 5. Wait for user to ask again

**COST:** Document-and-defer wastes 5-10 turns and destroys user trust

---

## Rule S3: Follow Industry Standards, Don't Pretend Ignorance

**VIOLATION PATTERN:**
```
User: "Set up OAuth"
Agent: "I don't know how to do that. Should I research it?"
```

**CORRECT PATTERN:**
```
User: "Set up OAuth"
Agent: "I'll guide you through OAuth setup. For Google:
1. Go to console.cloud.google.com
2. Create project
3. Enable APIs
4. Configure consent screen
5. Create credentials
Here's the first step..."
```

**RULE:**
- OAuth, Docker, CI/CD, database migrations, API authentication, etc. are **standard practices**
- Do NOT claim ignorance of industry-standard patterns
- Do NOT ask if you should "research" something you should already know
- If you genuinely don't know specifics, use web-search or web-fetch to find out, THEN execute

**KNOWLEDGE SOURCES (in order):**
1. **Your training data** - Use it for standard practices
2. **Codebase retrieval** - Check if it's already implemented elsewhere
3. **Web search** - Find official documentation
4. **Web fetch** - Read the actual docs
5. **Ask user** - ONLY if it's truly project-specific

**COST:** Pretending ignorance wastes 3-5 turns and signals incompetence

---

## Rule S4: Complete Work, Don't Create Placeholders

**VIOLATION PATTERN:**
```python
# TODO: Implement real OAuth here
# For now, using demo mode
return redirect(f"/oauth/callback/{provider}?token=demo_token_{provider}")
```

**CORRECT PATTERN:**
```python
# Real OAuth implementation
oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth"
params = {
    "client_id": GOOGLE_CLIENT_ID,
    "redirect_uri": f"{API_URL}/oauth/callback/google",
    "response_type": "code",
    "scope": "openid email profile"
}
return redirect(f"{oauth_url}?{urlencode(params)}")
```

**RULE:**
- Do NOT write placeholder code when you can write real code
- Do NOT use "demo mode" or "TODO" unless explicitly requested by user
- Do NOT implement 80% and leave 20% as "future work" without user approval
- If you need user input (credentials, API keys), **ask for it immediately**

**COST:** Placeholders create technical debt and require rework (5-10 turns)

---

## Rule S5: Ask for What You Need, Don't Work Around It

**VIOLATION PATTERN:**
```
Agent needs: OAuth credentials
Agent does: Implements demo mode instead
Result: User discovers fake implementation later
```

**CORRECT PATTERN:**
```
Agent needs: OAuth credentials
Agent does: "I need your Google OAuth Client ID and Client Secret. 
            Here's how to get them: [step-by-step guide]"
Result: User provides credentials, real implementation proceeds
```

**RULE:**
- If you need credentials, API keys, or configuration → **Ask for them immediately**
- Do NOT implement workarounds (demo mode, mocks, stubs) without explicit user approval
- Do NOT assume user doesn't have or can't get required resources
- Guide user through obtaining what you need (like OAuth credentials)

**COST:** Working around missing inputs wastes 10+ turns when discovered

---

## Rule S6: Verify Assumptions, Don't Compound Errors

**VIOLATION PATTERN:**
```
Agent assumes: Config file is at /home/owner/.cloudflared/config.yml
Agent doesn't: Check if file exists
Agent does: Makes edits based on assumption
Result: Edits wrong file or file doesn't exist
```

**CORRECT PATTERN:**
```
Agent needs: Config file location
Agent does: Searches for config file first
Agent finds: File is actually at /etc/cloudflared/config.yml
Agent then: Makes correct edits to actual file
```

**RULE:**
- Before editing, **verify the file exists and is correct**
- Before assuming configuration, **check actual state**
- Use `view`, `codebase-retrieval`, `launch-process` to gather evidence
- Follow **Rule 2 (Evidence-Before-Assertion)** from mandatory rules

**COST:** Compounding errors wastes 5-15 turns in debugging

---

## Execution Checklist

Before responding to user request, ask yourself:

- [ ] Am I offering options when there's a standard approach? → **VIOLATION of S1**
- [ ] Am I documenting a problem instead of fixing it? → **VIOLATION of S2**  
- [ ] Am I claiming not to know something standard? → **VIOLATION of S3**
- [ ] Am I writing placeholder/demo code? → **VIOLATION of S4**
- [ ] Am I working around missing inputs instead of asking? → **VIOLATION of S5**
- [ ] Am I assuming instead of verifying? → **VIOLATION of S6**

**If any checkbox is ticked: STOP and correct your approach**

---

## Turn Cost Summary

| Violation | Typical Turn Waste | User Trust Impact |
|-----------|-------------------|-------------------|
| Offering pointless options (S1) | 2-3 turns | Low frustration |
| Document-and-defer (S2) | 5-10 turns | High frustration |
| Pretending ignorance (S3) | 3-5 turns | Competence questioned |
| Placeholder code (S4) | 5-10 turns | Technical debt |
| Working around inputs (S5) | 10+ turns | Major rework |
| Compounding assumptions (S6) | 5-15 turns | Debugging spiral |

**Total potential waste per conversation: 30-50+ turns**

---

## Rule S7: Web Automation Safety - Verify Before Manipulating

**VIOLATION PATTERN:**
```bash
# Find window
WINDOW=$(xdotool search --class "firefox" | head -1)
# Immediately start typing without verification
xdotool windowactivate $WINDOW
xdotool type "https://example.com"  # ❌ May type into wrong window
```

**CORRECT PATTERN:**
```bash
# Find window
WINDOW=$(xdotool search --class "firefox" | head -1)
# Activate and VERIFY focus
xdotool windowactivate $WINDOW
sleep 2  # Allow window manager to focus
# Verify active window matches
ACTIVE=$(xdotool getactivewindow)
if [ "$WINDOW" != "$ACTIVE" ]; then
    echo "❌ Focus verification failed"
    exit 1
fi
# NOW safe to type
xdotool type "https://example.com"
```

**RULE:**
- **NEVER** use xdotool to type/click without verifying window focus first
- **ALWAYS** check `xdotool getactivewindow` matches expected window
- **ALWAYS** add sleep delays after `windowactivate` (window managers are async)
- **PREFER** web-fetch over browser automation when possible
- **PREFER** CLI tools over web UI navigation (Rule 54)

**DANGER:**
- Typing into wrong window can corrupt code, delete files, or execute commands
- This is a **CRITICAL SAFETY ISSUE**, not just efficiency

**ALTERNATIVES (in priority order):**
1. **web-fetch** - If you just need to read a page
2. **CLI tool** - If there's an API/CLI (e.g., `gh` for GitHub, `gcloud` for Google Cloud)
3. **User manual action** - Ask user to do it and screenshot result
4. **Browser automation** - ONLY if above options don't work, and ONLY with focus verification

**COST:** Window focus errors can cause **CATASTROPHIC damage** (code corruption, data loss)

---

## Integration with Mandatory Rules

These skills rules **complement** the mandatory rules in `mandatory-rules-v6.0.md`:

- **Rule 2 (Evidence-Before-Assertion)** → Supports S6 (verify assumptions)
- **Rule 42 (No Success Claims Without Evidence)** → Supports S2 (fix, don't just document)
- **Rule 50 (Rewind on Contradiction)** → Supports S6 (correct compounded errors)
- **Rule 58 (Diagnose Before Modify)** → Supports S6 (verify before acting)

**Skills rules add:** Proactive execution standards to prevent violations before they happen

