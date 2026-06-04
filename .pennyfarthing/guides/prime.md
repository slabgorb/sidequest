# Prime

<info>
Unified agent activation system. Bootstraps agents with context before they start working. Single entry point for all agent initialization — assembles identity, workflow state, session context, and behavioral guides into one payload.
</info>

<critical>
Prime outputs context in **priority order** (highest attention first):
1. Workflow State (routing decision)
2. Agent Definition (who am I)
3. Persona (character voice)
4. Behavior Guide (shared protocols)
5. Sprint Context
6. Session Context (story state)
7. Sidecars (patterns/gotchas/decisions)
</critical>

## Tiered Context

Prime selects a context tier based on session state to manage token overhead:

| Tier | ~Tokens | When |
|------|---------|------|
| **FULL** | 4000 | First turn of new session (no lastAgent) |
| **REFRESH** | 600 | Resumed session, same agent, turns 0-3 |
| **HANDOFF** | 700 | Resumed session, different agent |
| **MINIMAL** | 200 | Deep conversation (turn > 3), same agent |

## Workflow State Detection

| State | Meaning |
|-------|---------|
| `NEW_WORK_STATE` | No active story, agent should start new work |
| `IN_PROGRESS_STATE` | Story in progress, agent should continue |
| `FINISH_STATE` | Story ready for completion/review |
| `EMPTY_BACKLOG_STATE` | No stories available |

## Key Files

| File | Purpose |
|------|---------|
| `packages/cyclist/src/prime.ts` | TypeScript module: `getPrimeContext()`, `getPrimeContextWithTier()`, `selectContextTier()` |
| `pf/prime/cli.py` | Python CLI entry point |
| `pf/prime/tiers.py` | Tiered context selection logic |
| `pf/prime/persona.py` | Persona loading from theme config |
| `pf/prime/session.py` | Session state reading and registration |
| `pf/prime/workflow.py` | Workflow state detection |
| `pf/prime/models.py` | Data structures (WorkflowStatus, ContextTier, PrimeResult) |
| `pennyfarthing-dist/scripts/core/prime.sh` | Shell wrapper |
| `pennyfarthing-dist/commands/prime.md` | User command docs |

## Invocation

```bash
# From agent commands (via pf CLI)
pf agent start "<agent>" --quiet

# TypeScript API (from Frame GUI)
getPrimeContext(agentName, projectDir)
getPrimeContextWithTier(agentName, projectDir, tier)
getPrimeContextJson(agentName, projectDir, tier)  # JSON for Frame GUI
```

## Integration Points

- **Agent commands** (`/pf-sm`, `/pf-dev`, `/pf-tea`) invoke prime on activation
- **TirePump** calls prime to reload agent context after clearing
- **Frame GUI** uses JSON output for context display and token tracking

<info>
**ADR:** `docs/adr/0015-prime-activation-system.md`
</info>
