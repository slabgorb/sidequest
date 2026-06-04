# Worktree Mode

Work on multiple stories in parallel using git worktrees.

## When to Use

- Working on a second story while waiting for PR review
- Urgent bug fix while feature work is in progress
- Comparing implementations side-by-side

## Quick Start

```
/pf-session parallel
```

This creates a worktree, sets up the session, and starts the TDD flow.

## How It Works

### Session Files

```
.session/
├── 5-2-session.md               # Story 5-2 (main checkout)
└── 5-3a-session.md              # Story 5-3a (worktree)
```

Naming convention: `{story-id}-session.md`
Worktree info is stored INSIDE the session file, not in the filename.

### Worktree Directory Structure

```
worktrees/
└── wt-5-3a/
    ├── Pennyfarthing-api/    # API repo worktree
    └── Pennyfarthing-ui/     # UI repo worktree
```

### Session File Format

Worktree sessions include a context section:

```yaml
## Worktree Context
worktree: wt-5-3a
path: /path/to/worktrees/wt-5-3a
api_port: 8082
ui_port: 5175
```

Agents read this to know:
- They're in a worktree
- Where the worktree lives
- Which ports to use

## Agent Detection

Agents detect worktree context from the session file:

```bash
# Check if worktree session
if grep -q "^worktree:" "$SESSION_FILE"; then
    WORKTREE_NAME=$(grep "^worktree:" "$SESSION_FILE" | cut -d' ' -f2)
    WORKTREE_PATH=$(grep "^path:" "$SESSION_FILE" | cut -d' ' -f2)
fi
```

No filename parsing needed.

## Port Management

Each worktree gets offset ports to avoid conflicts:

| Worktree | API Port | UI Port | WebSocket |
|----------|----------|---------|-----------|
| main     | 8080     | 5173    | 8081      |
| wt-1     | 8082     | 5175    | 8083      |
| wt-2     | 8084     | 5177    | 8085      |

Ports are stored in the session file and passed to agents.

## Commands

| Command | Purpose |
|---------|---------|
| `/pf-session parallel` | Start a new parallel work session |
| `pf git worktree list` | Show active worktrees |
| `pf git worktree remove <name>` | Clean up a worktree |

## TDD Flow in Worktrees

Same flow as main checkout:

```
/pf-session parallel → SM → TEA → Dev → Reviewer → SM (finish)
```

Agents use worktree paths from session file for all operations.

## Cleanup

When story is complete, SM archives the session and the worktree can be removed:

```bash
pf git worktree remove wt-5-3a
```

This removes:
- Git worktrees
- Session file
- Port allocations
