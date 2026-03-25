---
name: tmux
description: |
  Pane management for tmux sessions. Read TUI content, discover panes, run commands
  in worker panes, capture output, and manage pane lifecycle. Protects claude and tui
  panes from accidental targeting. Server auto-starts when needed — no manual setup
  required. Use when you need to see what the TUI shows, run shell commands in
  background panes, or manage worker panes.
args: "[read|tui|window|cli|list|run|create|send|close|register] [args...]"
---

# /tmux - Pane Management

Read TUI content, discover panes, and run commands in managed tmux panes.

The tmux server auto-starts on the `pf` socket when needed. No manual setup is required — `just start` is optional (it adds the full Claude Code + TUI layout). For the full tmux guide, see `guides/tmux.md`.

## Quick Reference

| Command | CLI | Purpose |
|---------|-----|---------|
| `pf tmux read tui` | | Capture what the TUI pane currently shows |
| `pf tmux read <ref>` | | Capture content from any pane by reference |
| `pf tmux tui` | | Find the TUI pane for this CLI session |
| `pf tmux window` | | Show all panes in this window |
| `pf tmux cli` | | Show the pane running this CLI session |
| `/tmux list` | `pf tmux list [--json]` | Show all panes with role, status, protection |
| `/tmux run "<cmd>"` | `pf tmux run "<cmd>" [--title NAME]` | Run command in idle worker (creates one if needed) |
| `/tmux create` | `pf tmux create [--role worker\|agent\|script] [--title NAME] [--owner NAME]` | Create a new pane |
| `/tmux send <ref> "<cmd>"` | `pf tmux send <ref> "<cmd>"` | Send keys to a pane by reference |
| `/tmux close <ref>` | `pf tmux close <ref>` | Close a pane |
| `/tmux register` | `pf tmux register` | Force full registry rebuild |

## Pane References

Target panes by any of:
- **role**: `tui`, `worker`, `agent`, `script`, `claude`
- **pane_id**: `%5` — tmux stable identifier
- **title**: `Worker 1`, `Dev Agent`

## Discovery

```bash
# What does the TUI show right now?
pf tmux read tui

# Which pane is the TUI for this session?
pf tmux tui

# What panes are in this window?
pf tmux window

# All panes across all sessions
pf tmux list
```

## Running Commands

```bash
# Run a command — finds idle worker or creates one
pf tmux run "npm test"

# Send to a specific pane
pf tmux send worker "git status"

# Create a dedicated pane
pf tmux create --role worker --title "Test Runner"

# Clean up
pf tmux close worker
```

## Full Environment

For the full Claude Code + TUI layout with status line, Frame server, and keybindings:

```bash
just start              # TUI on bottom (default)
just start right 35     # TUI sidebar on right, 35%
just start top 40       # TUI on top, 40%
just start left         # TUI sidebar on left
```

## Protection

`claude`, `tui`, and `saddle` panes are always protected. `send` and `close` refuse protected panes.

## Rules

1. **Always use `pf tmux read`** — never raw `tmux capture-pane`
2. **Always use `pf tmux run`** — never raw `tmux send-keys`
3. **Always use `pf tmux tui`** to find the TUI — never guess pane IDs
4. **Never target `claude` or `tui`** with send/close — they are protected
5. Idle = pane is at a shell prompt (zsh/bash/fish)
6. Max 5 panes by default — close idle workers to free slots
