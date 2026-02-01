# UX Regression Checklist (Mandatory)

Before merging any changes to the callback platform, **ALL** items below must be verified and checked.

This checklist enforces the UX contract defined in the README and prevents regressions that degrade user experience.

## State Model

- [ ] All state changes go through `transition_to()` (backend) / `transitionTo()` (frontend)
- [ ] `ALLOWED_TRANSITIONS` updated if any new state is added
- [ ] No direct state mutation exists (no `current_state = ...` or `currentAppState = ...`)
- [ ] All new states are documented in README.md state tables
- [ ] State transitions are logged when `--verbose` flag is used

## Errors

- [ ] All error responses include:
      - `error` (user-facing message)
      - `tier` (USER, SYSTEM, or OPERATOR)
      - `context` (what was happening when error occurred)
      - `next_step` (what user should do next)
- [ ] User errors (tier=USER) do not expose system internals
- [ ] System errors (tier=SYSTEM) suggest retry or reconnect
- [ ] Operator errors (tier=OPERATOR) direct user to contact admin
- [ ] Frontend renders errors with tier-appropriate prefixes (⚠️ / 🛠 / 🚨)

## Visibility

- [ ] Current state is visible in the UI at all times
- [ ] State indicator updates on every state transition
- [ ] Errors are visible without opening dev tools
- [ ] Status messages are clear and actionable
- [ ] Loading states are indicated (spinners, progress messages)

## Shutdown

- [ ] SIGINT/SIGTERM produces user-visible messaging in logs
- [ ] Backend transitions to `SHUTTING_DOWN` state on shutdown signal
- [ ] Shutdown is announced with visual separators and emojis (when not --quiet)
- [ ] Frontend reflects backend shutdown within one polling cycle
- [ ] No new requests are accepted after shutdown signal

## README

- [ ] State table updated if states changed
- [ ] Exit codes updated if new exit codes added
- [ ] UX guarantees remain true (no silent failures, no hanging, etc.)
- [ ] New features are documented with examples
- [ ] Error tiers are explained if error handling changed

## UX Invariants

- [ ] `assert_ux_invariants()` (backend) passes before every request
- [ ] `assertUXInvariants()` (frontend) passes after DOM load
- [ ] `assertUXInvariants()` (frontend) passes after every state transition
- [ ] `assertUXInvariants()` (frontend) passes after every error render
- [ ] No UX invariant violations in logs during testing

## Testing

- [ ] Manual testing performed with both local and deployed backend
- [ ] Error paths tested (invalid input, network errors, backend errors)
- [ ] State transitions tested (happy path and error recovery)
- [ ] Graceful shutdown tested (SIGINT/SIGTERM)
- [ ] Logs reviewed for UX invariant violations

---

## 🚫 Merge Policy

**If any box above is unchecked → no merge.**

UX regressions are not acceptable. This checklist is not optional.

---

## Rationale

This checklist exists because:

1. **State is law, not decoration** - Invalid state transitions break user trust
2. **Errors must be actionable** - Users need to know what went wrong and what to do
3. **Visibility prevents confusion** - Users should never wonder "what's happening?"
4. **Shutdown must be felt** - Users and operators need clear signals
5. **README is part of UX** - Documentation drift leads to broken expectations

If you're tempted to skip a checkbox, ask yourself:

- Would I want to use this product if this guarantee was violated?
- Would I trust this product if errors were unclear?
- Would I be frustrated if the UI didn't show me what's happening?

The answer is always **no**. That's why this checklist is mandatory.

