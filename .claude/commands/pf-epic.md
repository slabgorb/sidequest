---
description: Epic lifecycle - start epics for development and close completed epics
args: "[start|close] <epic-id>"
---

# Epic Management

<purpose>
Manage epic lifecycle. Start an epic by moving it to the current sprint and generating tech context. Close an epic by verifying completion, updating status, and archiving context.
</purpose>

## Commands

### `/pf-epic start <epic-id>`

Start an epic — move to current sprint and generate technical context.

```bash
pf epic start 79
pf epic start epic-79
```

<workflow>
1. Parse epic ID (strip `epic-` prefix if present)
2. Check epic location (current sprint or backlog)
3. Move to current sprint if needed, set status to `in-progress`
4. Invoke SM agent for `epic-tech-context` task
5. Generate tech context to `sprint/context/context-epic-{N}.md`
</workflow>

### `/pf-epic close <epic-id>`

Close an epic — verify completion, update status, and archive context.

```bash
pf epic close 79
pf epic close epic-79
```

<workflow>
1. Parse epic ID
2. Verify all stories have `status: done`
3. Update epic: `status: done`, calculate `completed_points`
4. Recalculate sprint summary totals
5. Transition Jira epic to Done (if jira key exists)
6. Archive context file to `sprint/archive/`
7. Commit and push sprint changes
</workflow>

## Quick Reference

| Command | Description |
|---------|-------------|
| `/pf-epic start <id>` | Start epic for development |
| `/pf-epic close <id>` | Close completed epic |

## CLI Equivalent

```bash
pf epic start <epic-id>
pf epic close <epic-id>
```

## Related

- `/pf-sprint` — Sprint management
- `/sm` — Scrum Master for epic tech context
