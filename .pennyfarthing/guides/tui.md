# Frame

<info>
Terminal dashboard using Textual TUI panels. Frame runs Frame (Python FastAPI server), serving dashboard data via WebSocket while Claude Code runs in your terminal.
</info>

## Overview

Frame provides dashboard panels (sprint status, git diffs, workflow state, etc.) alongside Claude Code in your terminal using Textual TUI.

```
┌─────────────────┐       ┌──────────────────────┐
│  Claude CLI      │       │  Frame (Frame)  │
│  (your terminal) │──────▶│  Port 2898            │
│                  │ OTEL  │  WebSocket channels   │
│                  │ files │  REST API             │
└─────────────────┘       └──────────┬─────────────┘
                                     │ WS
                                     ▼
                          ┌──────────────────────┐
                          │  TUI (Textual)        │
                          │  Terminal panels       │
                          └──────────────────────┘
```

## Quick Start

```bash
# Launch Frame + Claude CLI together
pf frame start

# Or via just recipe
just frame

# With a specific project directory
just frame dir=/path/to/project

# Stop a running instance
pf frame stop

# Check status
pf frame status
```

Frame starts Frame in the background. Claude CLI runs in the foreground. When Claude exits, Frame shuts down automatically via `trap EXIT`.

## How It Works

1. **Launcher** (`pf frame start`) starts Frame with `IS_FRAME=1`
2. **Frame** listens on port 2898
3. **OTEL telemetry** flows from Claude CLI to Frame's OTLP receiver
4. **File watchers** detect changes to `.session/`, `sprint/`, and git state
5. **TUI panels** consume WebSocket data from Frame

### Port and PID Files

| File | Purpose |
|------|---------|
| `.frame-port` | Port number — readiness signal |
| `.frame-pid` | Frame PID — enables `pf frame stop` |

Both are deleted on shutdown.

## Layout Persistence

Save and restore Frame panel layouts:

```bash
pf bc save my-layout      # Save current layout
pf bc load my-layout      # Restore a saved layout
pf bc list                 # List saved layouts
```

## TUI Panels

### Prerequisites

- **Python** >= 3.11
- **uv** (recommended) or pip
- **just** >= 1.0

### Setup

```bash
# From the pennyfarthing repo root — create venv and install TUI deps
python3 -m venv .venv
uv pip install --python .venv/bin/python3 -e "pennyfarthing-dist"
```

Required packages:

| Package | Purpose |
|---------|---------|
| `textual` >= 1.0 | Terminal UI framework |
| `websockets` >= 12.0 | Frame WebSocket client |
| `rich` | Terminal rendering (textual dependency) |
| `click` >= 8.0 | CLI framework |
| `pyyaml` >= 6.0 | YAML parsing |
| `textual-image` >= 0.7.0 | Agent portrait images |

The justfile automatically uses `.venv/bin/python3` when `.venv/` exists.

### Launch

```bash
# Default — connects to Frame on localhost:1898
just tui

# Point at a specific project directory
just tui dir=/path/to/project

# Custom Frame port
just tui port=2898
```

### Navigation

| Key | Action |
|-----|--------|
| `Tab` / `]` | Next panel |
| `[` | Previous panel |
| `Shift+S` | Split view |
| `Ctrl+P` | Command palette |
| `q` | Quit |

Available panels: Sprint, Git, Diffs, Audit Log, Debug, Progress.

### Troubleshooting

**`ModuleNotFoundError: No module named 'textual'`**
```bash
# Deps not installed in venv — re-run setup
uv pip install --python .venv/bin/python3 -e "pennyfarthing-dist"
```

**`No module named 'pf'`**
The justfile sets `PYTHONPATH` automatically. If running manually:
```bash
PYTHONPATH=pennyfarthing-dist:$PYTHONPATH .venv/bin/python3 -m pf.frame.tui
```

**Portrait images not rendering**
`textual-image` is included in the base install. Requires a terminal with Sixel or Kitty graphics protocol support (iTerm2, WezTerm, Kitty). Falls back to text-only in unsupported terminals.

## Constraints

- **No MessagePanel** — Claude conversation stays in your terminal. This is intentional.
- **Single session** — one Claude CLI per Frame instance.

## Key Files

| File | Purpose |
|------|---------|
| `pf/frame/cli.py` | `pf frame` launcher CLI |
| `pf/frame/launcher.py` | Frame process management |
| `pf/frame/app.py` | FastAPI application |
| `pf/frame/tui.py` | Textual TUI application |

<info>
**ADR:** `docs/adr/0024-frame-mode.md`
</info>
