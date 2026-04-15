---
description: Session lifecycle - start new work and resume checkpoints
args: "[new|continue] [args...]"
---

# Session Management

<purpose>
Manage work session lifecycle. Start new stories from the backlog or resume from saved checkpoints after context circuit breaker.
</purpose>

## Commands

### `/pf-session new`

Start the next available story from the sprint backlog.

```bash
pf session new
```

Equivalent to `pf sprint work next`. Auto-selects the highest priority story.

### `/pf-session continue [--list] [--story-id ID]`

Resume work from a saved checkpoint after context circuit breaker.

```bash
pf session continue            # Interactive checkpoint selection
pf session continue --list     # Show available checkpoints
pf session continue --story-id <PROJECT-KEY>  # Resume specific story
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `/pf-session new` | Start next available story |
| `/pf-session continue` | Resume from checkpoint |

## CLI Equivalent

```bash
pf session new
pf session continue [--list] [--story-id ID]
```

## Related

- `/pf-work` — Smart entry point (resumes or starts new)
- `/pf-sprint work` — Interactive story selection
