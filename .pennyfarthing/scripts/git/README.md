# Git Scripts

Scripts for Git operations, branching, and worktree management.

## CLI Commands (preferred)

All git operations are available via the `pf git` CLI:

| Command | Purpose |
|---------|---------|
| `pf git status [--brief]` | Show git status across all repos |
| `pf git branches <name> [--repos all\|api\|ui]` | Create feature branches in repos |
| `pf git worktree create <name> <branch>` | Create worktrees for parallel work |
| `pf git worktree remove <name>` | Remove worktree and clean up |
| `pf git worktree list` | List all active worktrees |
| `pf git worktree status` | Show detailed worktree status |
| `pf git install-hooks` | Install git hooks with .d/ dispatcher |
| `pf git cleanup` | Organize changes into commits/branches |

## Legacy Scripts (deprecated shims)

These scripts now forward to `pf git` commands:

| Script | Forwards to |
|--------|-------------|
| `git-status-all.sh` | `pf git status` |
| `create-feature-branches.sh` | `pf git branches` |
| `worktree-manager.sh` | `pf git worktree` |
| `install-git-hooks.sh` | `pf git install-hooks` |
| `release.sh` | Release workflow (use `/pf-workflow start release`) |

## Ownership

- **Primary users:** SM agent, DevOps agent
- **Maintained by:** Core Pennyfarthing team
