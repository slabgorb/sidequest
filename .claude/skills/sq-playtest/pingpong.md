# Ping-Pong File Protocol

Cross-workspace coordination between playtest driver and fix agent.

## File Locations

| Resource | Path |
|----------|------|
| Ping-pong file | `../Projects/sq-playtest-pingpong.md` |

These are siblings to `bugfix agent/` and `playtest/` under `Projects/`, accessible to both workspaces.

## Write Ownership

| Action | playtest (playtest) | bugfix agent (fixes) |
|--------|-----------------|---------------|
| Add new task | YES | NO |
| Set status → `in-progress` | NO | YES |
| Set status → `fixed` | NO | YES |
| Set status → `verified` | YES | NO |
| Add `ATTENTION` signal | YES | NO |
| Remove `ATTENTION` signal | NO | YES (when picking up) |
| Delete entries | NO | NO |

**Neither side deletes.** Status transitions only. This prevents edit conflicts.

## Status Flow

```
open → in-progress → fixed → verified
 │                      │
 └── (playtest adds)       └── (playtest verifies)
       (bugfix agent picks up)       (bugfix agent fixes)
```

## Task Tags

| Tag | Meaning | Typical Priority |
|-----|---------|-----------------|
| `[BUG]` | Functional bug, broken behavior | blocking or high |
| `[BUG-LOW]` | Cosmetic or minor visual bug | medium or low |
| `[UX]` | Usability improvement opportunity | medium or low |
| `[GAP]` | Expected feature or feedback missing | varies |

## Blocking Bug Signal

When playtest adds a blocking bug, it prepends this to the Tasks section:

```markdown
> **ATTENTION bugfix agent**: Blocking bug added — {brief description}. Please prioritize.
```

bugfix agent removes the attention line when it sets the task to `in-progress`.

## Server Restart Coordination

When bugfix agent fixes a bug that requires a server restart:
1. bugfix agent adds `- **Needs restart:** yes` to the task entry
2. bugfix agent sets status to `fixed`
3. playtest sees the `fixed` status and `Needs restart` flag
4. playtest pulls latest code and restarts the affected service
5. playtest re-tests and sets status to `verified`

## Task Entry Template

```markdown
### [{TAG}] {title}
- **Priority:** blocking | high | medium | low
- **Found by:** SM | UX Designer
- **Repro:** {step-by-step reproduction}
- **Status:** open | in-progress | fixed | verified
- **Notes:** {additional context}
- **Needs restart:** no (set by bugfix agent if fix requires service restart)
```
