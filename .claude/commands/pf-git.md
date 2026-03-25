---
description: Repository operations - status, cleanup, branches, snapshot, and release management
args: "[status|cleanup|branches|snapshot|release] [args...]"
---

# Git Operations

<purpose>
Manage git operations across all configured repos. Consolidates repository status, git cleanup, branch creation, snapshots, and release management into a single resource group.
</purpose>

## Commands

### `/pf-git snapshot`

Create safety branches and commit all dirty changes across all repos. Use before risky operations (rebases, branch switches) to ensure nothing is lost.

```bash
pf git snapshot [--label TEXT]
```

Creates a `snapshot/{repo}-{label}-{date}` branch in each dirty repo, stages everything, and commits. Clean repos are skipped.

**Examples:**
```bash
pf git snapshot                          # snapshot/orchestrator-2026-03-08
pf git snapshot --label benchmark-work   # snapshot/orchestrator-benchmark-work-2026-03-08
```

### `/pf-git status`

Check git status of all project repos.

```bash
pf git status [--brief]
```

Shows branch, uncommitted changes, and ahead/behind status for each configured repo.

### `/pf-git cleanup`

Organize uncommitted changes into proper commits and branches.

**When this subcommand is invoked, immediately start the stepped workflow:**

```bash
pf workflow start git-cleanup
```

Then follow each step's instructions. Use `pf workflow complete-step git-cleanup` to advance between steps. The workflow handles multi-repo analysis, change categorization, branch creation, commits, and push.

### `/pf-git branches <story-id>`

Create feature branches in both repos from a story.

```bash
pf git branches 86-3
```

### `/pf-git release`

Interactive release with verification gates.

```bash
pf git release
```

Starts the release stepped workflow — an 11-step process with gates at each stage.

## Quick Reference

| Command | Description |
|---------|-------------|
| `/pf-git status` | Check all repo status |
| `/pf-git snapshot` | Safety-branch + commit all dirty repos |
| `/pf-git cleanup` | Organize changes into commits/branches |
| `/pf-git branches <id>` | Create feature branches from story |
| `/pf-git release` | Interactive release workflow |

## CLI Equivalent

All commands are also available via `pf git`:

```bash
pf git status
pf git cleanup
pf git branches 86-3
pf git release
```

## Related

- `/pf-chore` — Quick commit for small changes
- `/pf-standalone` — Wrap changes into standalone story + PR
