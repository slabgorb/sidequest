# tmux Integration Guide

Pennyfarthing uses a dedicated tmux socket (`-L pf`) to run Claude Code and the TUI dashboard side-by-side. This guide covers the full stack: server lifecycle, session management, pane operations, terminal configuration, and troubleshooting.

## Architecture

```
┌─ tmux server (socket: pf) ─────────────────────┐
│                                                  │
│  Session: pf-pf-1-0                              │
│  ┌──────────────────────────────────────────┐    │
│  │  Pane 0: Claude Code  (protected)        │    │
│  ├──────────────────────────────────────────┤    │
│  │  Pane 1: TUI          (protected)        │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  Frame server (FastAPI) ←→ TUI (Textual)         │
│  Status line ←── .pennyfarthing/tmux-status-*    │
│  Activity    ←── .pennyfarthing/tmux-activity    │
│  Registry    ←── .pennyfarthing/tmux-panes.json  │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Why a dedicated socket?** Project-level isolation. `tmux -L pf` loads the project's `tmux.conf` instead of `~/.tmux.conf`, preventing config conflicts and namespace collisions between projects.

## Server Lifecycle

### Auto-start

The tmux server starts automatically. Any `pf tmux` command that needs a server will create one if none exists — no manual setup required.

When auto-starting, a "bare" session is created (`pf-bare-<project>`). This session has no Claude Code or TUI panes — it exists solely so pane commands work. If you later run `just start` for the full environment, it creates a proper session (`pf-<project>-N`) alongside the bare one. All `pf tmux` commands automatically prefer proper sessions over bare ones.

### Full environment: `just start`

The full development environment starts Frame server, Claude Code, and the TUI:

```bash
just start              # default: TUI on bottom, 50/50 split
just start right 35     # TUI sidebar on right, 35% width
just start top 40       # TUI on top, 40% height
just start left         # TUI sidebar on left, default 35%
```

**What it does (in order):**
1. Validates tmux is installed
2. Parses layout and split percentage
3. Finds the project tmux.conf (`tmux.conf.vert`, etc.)
4. Picks next available session number (`pf-pf-1-0`, `pf-pf-1-1`, ...)
5. Unsets `CLAUDECODE` env var (prevents nested-session detection)
6. Starts Frame server in background, waits up to 5s for `.frame-port`
7. Creates tmux session with layout-specific pane arrangement
8. Runs `pf tmux register` to populate the pane registry
9. Attaches to the session

**Layouts:**

```
bottom (default)         top                right              left
┌──────────┐       ┌──────────┐       ┌───────┬────┐    ┌────┬───────┐
│  claude  │       │   TUI    │       │claude │TUI │    │TUI │claude │
├──────────┤       ├──────────┤       │       │    │    │    │       │
│   TUI    │       │  claude  │       └───────┴────┘    └────┴───────┘
└──────────┘       └──────────┘
```

### Stopping

```bash
tmux -L pf kill-server    # Kill all sessions on the pf socket
pf launch stop            # Stop Frame server
```

### Multiple sessions

Multiple sessions can coexist on the same socket. The session numbering (`pf-pf-1-0`, `pf-pf-1-1`) increments automatically. Each session has independent panes.

## Pane Management (`pf tmux`)

All pane operations go through `pf tmux`. Never use raw `tmux send-keys` or `tmux split-window` — the CLI manages a registry with role-based targeting and protection.

### Commands

| Command | Purpose |
|---------|---------|
| `pf tmux list [--json]` | Show all panes with role, idle/busy status, protection |
| `pf tmux run "<cmd>" [--title NAME]` | Run command in idle worker (creates one if needed) |
| `pf tmux create [--role worker\|agent\|script] [--title NAME]` | Create a new pane |
| `pf tmux send <ref> "<cmd>"` | Send keys to a pane by reference |
| `pf tmux close <ref>` | Close a pane by reference |
| `pf tmux register` | Force full registry rebuild from live state |
| `pf tmux read [PANE_REF]` | Capture visible content (default: TUI) |
| `pf tmux tui` | Find the TUI pane for this CLI session |
| `pf tmux window` | Show all panes in this window |
| `pf tmux cli` | Show the pane running this CLI session |
| `pf tmux layout <name>` | Apply layout: `vertical`, `grid`, `horizontal`, `stacked` |

### Layout management

When team agents are spawned via `teammateMode: tmux`, the default horizontal splits produce narrow panes with ~1 line of output. Use `pf tmux layout` to rearrange:

```bash
pf tmux layout vertical       # CLI left, agents stacked right (recommended)
pf tmux layout vertical -w 60 # Same but CLI gets 60% width
pf tmux layout grid           # 2x2 tiled grid
pf tmux layout stacked        # All panes top-to-bottom
```

**Auto-layout:** Set `peloton.layout` in `config.local.yaml` (or via TUI settings panel) to automatically apply the layout when team agents are spawned:

```yaml
peloton:
  layout: vertical        # auto-applied after Agent/TeamCreate
  main_pane_width: 50     # main pane width % for vertical layout
```

### Pane references

Target panes by any of:
- **pane_id**: `%5` — tmux stable identifier
- **role**: `worker`, `claude`, `tui`
- **title**: `Worker 1`, `Dev Agent`

### Protection

`claude`, `tui`, and `saddle` panes are always protected. `pf tmux send` and `pf tmux close` refuse to target protected panes. This prevents agents from accidentally sending commands to the Claude Code or TUI pane.

### Idle detection

A pane is idle when its current command is a shell (`zsh`, `bash`, `fish`, `sh`). `pf tmux run` finds the first idle worker, or creates a new one if under the pane limit (default: 5).

### Registry

The pane registry at `.pennyfarthing/tmux-panes.json` tracks all panes with their role, title, protection status, and owner. It is reconciled against live tmux state on every command:
- Stale entries (panes that no longer exist) are removed
- Unknown panes (created outside `pf tmux`) are auto-classified by title
- Classification rules: title contains "Claude Code" → `claude`, "TUI" → `tui`, "Saddle" → `saddle`, otherwise → `worker`

## Session Naming

| Pattern | Source | Example |
|---------|--------|---------|
| `pf-<project>-N` | `just start` (full environment) | `pf-pf-1-0` |
| `pf-bare-<project>` | Auto-start (bare server) | `pf-bare-pf-1` |

When multiple sessions exist, `pf tmux` commands prefer real sessions over bare ones. The bare session is a fallback that exists only so `pf tmux create/run/list` work without requiring `just start` first.

## Terminal Configuration

The tmux config files (`tmux.conf.vert`, `tmux.conf.right`, `tmux.conf.left`) handle terminal integration. Key settings:

### Key passthrough (CSI u mode)
```
set -s extended-keys always
set -s extended-keys-format csi-u
```
Forces CSI u output so Shift+Enter, Ctrl+Enter, etc. are properly distinguished from plain Enter in Claude Code. Claude Code (Ink/React) never sends the mode-1 request sequence, so `always` is required instead of `on`.

### Clipboard (OSC 52)
```
set -g set-clipboard on
set -as terminal-overrides ",*:Ms=\\E]52;c;%p2%s\\7"
```
Claude Code uses OSC 52 for copy-to-clipboard. Without this, copy operations silently fail.

### Image passthrough
```
set -g allow-passthrough all
```
Allows inline image protocols (Kitty, iTerm2, Sixel) to pass through tmux for portraits and logos.

### Mouse copy
- **Kitty:** Shift+drag to select, auto-copies to clipboard
- **iTerm2:** Option+drag to select, auto-copies to clipboard
- **Manual:** Prefix+[ enters copy mode, Space to start, y/Enter to yank

### Keybindings

| Binding | Action |
|---------|--------|
| Prefix+\| or Prefix+\\ | Vertical split (within Claude Code pane) |
| Prefix+- | Horizontal split (within Claude Code pane) |
| Prefix+Space | Popup shell (80% × 75%, centered) |
| Prefix+a | Agent selection menu |

## Status Line

The tmux status bar displays agent context, updated by hooks:

```
 [story] dir          tool activity          context-bar │ 12:30PM
```

**Cache files** (written by hooks, read by tmux `#()` expressions):
- `.pennyfarthing/tmux-status-left` — story ID, project directory
- `.pennyfarthing/tmux-status-right` — context usage bar with color tiers
- `.pennyfarthing/tmux-activity` — current tool label (italicized, centered)

The status line refreshes every 5 seconds (`status-interval`). The `statusline.py` hook writes cache files on each invocation; `bell_mode.py` writes the activity label on PostToolUse.

## Agent Rules

<critical>
1. **Always use `pf tmux run`** to execute commands in worker panes
2. **Use `pf tmux list`** to discover available panes before targeting
3. **NEVER target `claude` or `tui` roles** — they are protected
4. **NEVER use raw `tmux send-keys`** — it bypasses protection and registry tracking
5. Pane limit is enforced (default 5) — close idle panes or wait
6. **Use `pf tmux read tui`** to see TUI content — never raw `tmux capture-pane`
</critical>

## Troubleshooting

### TUI shows raw escape sequences on startup
**Cause:** SGR mouse events and focus-in (`^[[I`) arrive before Textual initializes terminal modes.
**Fix:** The launcher prepends `clear &&` before `just tui`. If it happens mid-session, force a Textual redraw by resizing the pane:
```bash
tmux -L pf resize-pane -t %1 -y 24 && tmux -L pf resize-pane -t %1 -y 25
```

### TERM_PROGRAM not detected inside tmux
**Cause:** tmux sets `TERM_PROGRAM=tmux`, hiding the real terminal (Kitty, iTerm2).
**Fix:** The launcher passes `-e "TERM_PROGRAM=${TERM_PROGRAM:-}"` to preserve the original value. If lost, set manually: `export TERM_PROGRAM=Kitty`

### Copy doesn't work
**Cause:** Claude Code's mouse mode captures all mouse events.
**Fix:** Use Shift+drag (Kitty) or Option+drag (iTerm2) to bypass mouse capture. These terminal-level selection methods work regardless of what the app is doing.

### Panes not appearing in `pf tmux list`
**Cause:** Registry is stale or panes were created outside `pf tmux`.
**Fix:** `pf tmux register` forces a full rebuild from live tmux state.

### "At pane limit" error
**Cause:** 5 panes already exist (default `max_panes`).
**Fix:** Close idle workers with `pf tmux close worker`, or edit `.pennyfarthing/tmux-panes.json` to increase `max_panes`.

## Key Files

| File | Purpose |
|------|---------|
| `start-session` (project root) | Session launcher script |
| `tmux.conf.vert` | Config for top/bottom layouts |
| `tmux.conf.right` | Config for right sidebar layout |
| `tmux.conf.left` | Config for left sidebar layout |
| `.pennyfarthing/tmux-panes.json` | Pane registry (auto-managed) |
| `.pennyfarthing/tmux-status-left` | Status bar left segment (hook-written) |
| `.pennyfarthing/tmux-status-right` | Status bar right segment (hook-written) |
| `.pennyfarthing/tmux-activity` | Tool activity label (hook-written) |
| `pennyfarthing-dist/src/pf/tmux/` | Python CLI source (`cli.py`, `panes.py`, `registry.py`) |
| `pennyfarthing-dist/templates/tmux*.template` | Config templates (source of truth for samples) |
