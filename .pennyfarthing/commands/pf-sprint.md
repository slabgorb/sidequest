---
description: Sprint status, backlog, and story management - check status, find work, archive completed stories
args: "[status|backlog|work|archive|new|future|promote] [args...]"
---

# Sprint Management

<purpose>
Manage sprint workflow: check status, view backlog, start work, archive completed stories, and promote future epics. This is the primary interface for sprint operations.
</purpose>

<critical>
Never manually edit `sprint/current-sprint.yaml`. Always use the provided scripts.
</critical>

## Commands

### `/pf-sprint` or `/pf-sprint status [filter]`

Show current sprint status with story counts and points.

```bash
pf sprint status [filter]
```

| Filter | Description |
|--------|-------------|
| (none) | All stories |
| `todo` | Backlog only |
| `in-progress` | Work in progress |
| `done` | Completed stories |

### `/pf-sprint backlog`

Show available stories ready for work, grouped by epic.

```bash
pf sprint backlog
```

### `/pf-sprint work [story-id|epic-id|next]`

Start work on a story. Primary entry point for development.

| Argument | Behavior |
|----------|----------|
| (none) | Interactive selection from backlog |
| `<PROJECT-KEY>` | Start specific story |
| `epic-XX` | Start first available story in epic |
| `next` | Auto-select highest priority story |

```bash
# MERGE GATE: Enforced by gates/merge-ready
# Blocks if non-draft PRs exist for stories NOT in in_review status.
# PRs for in_review stories are allowed — they're awaiting external review
# and can't be self-merged per repo rules.
# Draft PRs are always allowed.
pf handoff resolve-gate merge-ready

# Check if story is available
pf sprint check <story-id>

# Then load SM to begin work
```

<workflow>
When starting work, this command:
1. **Checks merge gate** - blocks if non-draft PRs exist for stories not in `in_review`
2. Validates story availability
3. Loads SM agent
4. SM creates context and claims Jira
5. Hands off to TEA (tdd) or Dev (trivial)
</workflow>

### `/pf-sprint archive <story-id> [pr-number] [--apply]`

Archive a completed story.

```bash
pf sprint archive <story-id> [pr-number] [--apply]
```

| Option | Description |
|--------|-------------|
| `--apply` | Also remove from current-sprint.yaml |

### `/pf-sprint new <yyww> <jira-id> <start> <end> "<goal>"`

Initialize a new sprint.

```bash
pf sprint new 2605 277 2026-02-03 2026-02-16 "Sprint goal"
```

### `/pf-sprint future [--epic EPIC_ID]`

Show future work available for promotion.

```bash
pf sprint future [--epic epic-XX]
```

### `/pf-sprint promote <epic-id>`

Move an epic from future.yaml to current sprint.

```bash
pf sprint epic promote epic-XX
```

## Quick Reference

| Command | Action |
|---------|--------|
| `/pf-sprint` | Show sprint status |
| `/pf-sprint status todo` | Show backlog |
| `/pf-sprint backlog` | Available stories |
| `/pf-sprint work` | Interactive start |
| `/pf-sprint work next` | Start highest priority |
| `/pf-sprint work <PROJECT-KEY>` | Start specific story |
| `/pf-sprint archive <PROJECT-KEY>` | Archive completed |
| `/pf-sprint future` | Show future work |
| `/pf-sprint promote epic-XX` | Promote to sprint |

## Aliases

- `/pf-new-work` is an alias for `/pf-sprint work`

## Related

| Skill | Purpose |
|-------|---------|
| `/pf-jira` | Jira operations (create, sync, claim) |
| `/pf-sprint story` | Story creation, sizing, finish (consolidated) |
| `/sm` | Scrum Master agent for coordination |

<reference>
- **Skill:** `.claude/skills/sprint/skill.md`
- **Scripts:** `.pennyfarthing/scripts/sprint/`
- **Data:** `sprint/current-sprint.yaml`
</reference>
