# tmux Pane Management

<critical>
**Use `pf tmux run "<cmd>"` instead of raw `tmux send-keys`.** The pf tmux subsystem manages a pane registry with role-based targeting and protection. Raw tmux commands bypass all safety checks.
</critical>

For the full tmux guide (server lifecycle, terminal config, status line, troubleshooting), see `guides/tmux.md`.

## Server Auto-Start

The tmux server starts automatically when needed. Any `pf tmux` command creates a bare session on the `pf` socket if no server is running. No manual setup required — `just start` is optional (it adds the full Claude Code + TUI environment).

## Commands

| Command | Purpose |
|---------|---------|
| `pf tmux list [--json]` | Show all panes with role, idle/busy status, protection |
| `pf tmux run "<cmd>" [--title NAME]` | Run a command in an idle worker pane (creates one if needed) |
| `pf tmux create [--role worker\|agent\|script] [--title NAME] [--owner NAME]` | Create a new pane |
| `pf tmux send <ref> "<cmd>"` | Send keys to a pane by reference |
| `pf tmux close <ref>` | Close a pane by reference |
| `pf tmux register` | Force full registry rebuild from live tmux state |
| `pf tmux read [PANE_REF]` | Capture visible content (default: TUI) |
| `pf tmux tui` | Find the TUI pane for this CLI session |
| `pf tmux window` | Show all panes in this window |
| `pf tmux cli` | Show the pane running this CLI session |

## Pane References

Panes can be targeted by:
- **pane_id**: `%5` — the tmux stable identifier
- **role**: `worker`, `agent`, `script`, `claude`, `tui`
- **title**: `Worker 1`, `Dev Agent`

## Protection

`claude`, `tui`, and `saddle` panes are always protected. `pf tmux send` and `pf tmux close` refuse to target protected panes. This prevents agents from accidentally sending commands to the Claude Code or TUI pane.

## Idle Detection

A pane is considered idle when its current command is a shell (`zsh`, `bash`, `fish`, `sh`). `pf tmux run` automatically finds the first idle worker pane, or creates a new one if none are available and the pane limit hasn't been reached.

## Rules for Agents

1. **Always use `pf tmux run`** to execute commands in worker panes
2. **Use `pf tmux list`** to discover available panes before targeting
3. **NEVER target `claude` or `tui` roles** — they are protected
4. **NEVER use raw `tmux send-keys`** — it bypasses protection and registry tracking
5. Pane limit is enforced (default 5) — if at max, close idle panes or wait
6. **Use `pf tmux read tui`** to see TUI content — never raw `tmux capture-pane`

## Registry

The pane registry lives at `.pennyfarthing/tmux-panes.json`. It is automatically reconciled against live tmux state on every command — stale entries are removed, unknown panes are auto-classified by title.
