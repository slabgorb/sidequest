# Plan Mode Handoff Guide

Use plan mode to design multi-step work, then hand execution to a fully-loaded agent — not bare Claude.

## How It Works

The `plan-exit-reload` hook (`pf.hooks.plan_exit_reload`) fires on `PreToolUse:ExitPlanMode`. It resolves which agent should execute:

1. **Signal file** `.session/.plan-exit-agent` (explicit override, consumed on read)
2. **Phase owner** from active session (default fallback)
3. **No agent found** — silent no-op

The hook runs `pf agent start <agent> --tier refresh --quiet` and injects the output as `additionalContext`. The executing agent gets persona, workflow state, and session awareness automatically.

## Planning for Yourself

Enter plan mode normally. On exit the hook detects you as the phase owner and reloads your context. No signal file needed.

## Planning for Another Agent

Before entering plan mode:
```bash
echo "dev" > .session/.plan-exit-agent
```

Valid targets: `sm`, `tea`, `dev`, `reviewer`, `architect`, `pm`, `tech-writer`, `ux-designer`, `devops`, `orchestrator`, `ba`.

The signal file is one-shot — consumed when plan mode exits. Invalid agent names are rejected and fall through to the phase owner.

## Executing a Plan

No action required. If you see `AGENT RELOAD on plan exit` in your context, your persona is already loaded. Execute the plan.

If the inline prime fails (timeout, missing CLI), the hook falls back to instructing you to run `pf agent start <agent>` manually.

## Architecture

```
Agent enters plan mode
    │
    ▼
Agent writes .session/.plan-exit-agent (optional)
    │
    ▼
Agent designs plan in read-only mode
    │
    ▼
ExitPlanMode tool fires
    │
    ▼
PreToolUse hook chain
    │
    ├─ plan-exit-reload matches "ExitPlanMode"
    │   ├─ Signal file exists? → read agent, delete file
    │   └─ No signal? → detect phase owner from session
    │       │
    │       ▼
    │   pf agent start <agent> --tier refresh --quiet
    │       │
    │       ▼
    │   additionalContext injected with persona + state
    │
    ▼
Plan execution begins with full agent context
```

## Files

| File | Purpose |
|------|---------|
| `src/pf/hooks/plan_exit_reload.py` | Hook implementation |
| `src/pf/hooks/dispatch.py` | Registry entry (`PreToolUse:ExitPlanMode`) |
| `.session/.plan-exit-agent` | Signal file (ephemeral, one-shot) |

## Relationship to Other Systems

- **agent_reload.py** — same pattern for `SessionStart:compact|clear`. Plan-exit-reload reuses `_find_active_agent()` from it.
- **Handoff CLI** — formal phase transitions between agents. Plan mode handoff is lighter — same session, same phase, just reloads identity.
- **TirePump** — context clearing mid-session. Plan mode exit may or may not clear context depending on user choice; the hook fires either way.
