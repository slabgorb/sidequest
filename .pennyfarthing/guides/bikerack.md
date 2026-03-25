# BikeRack

<info>
Terminal dashboard using Textual TUI panels. BikeRack runs WheelHub (Python FastAPI server), serving dashboard data via WebSocket while Claude Code runs in your terminal.
</info>

## Overview

BikeRack provides dashboard panels (sprint status, git diffs, workflow state, etc.) alongside Claude Code in your terminal using Textual TUI.

```
┌─────────────────┐       ┌──────────────────────┐
│  Claude CLI      │       │  WheelHub (BikeRack)  │
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
# Launch BikeRack + Claude CLI together
pf bikerack start

# Or via just recipe
just bikerack

# With a specific project directory
just bikerack dir=/path/to/project

# Stop a running instance
pf bikerack stop

# Check status
pf bikerack status
```

BikeRack starts WheelHub in the background. Claude CLI runs in the foreground. When Claude exits, BikeRack shuts down automatically via `trap EXIT`.

## How It Works

1. **Launcher** (`pf bikerack start`) starts WheelHub with `IS_BIKERACK=1`
2. **WheelHub** listens on port 2898
3. **OTEL telemetry** flows from Claude CLI to WheelHub's OTLP receiver
4. **File watchers** detect changes to `.session/`, `sprint/`, and git state
5. **TUI panels** consume WebSocket data from WheelHub

### Port and PID Files

| File | Purpose |
|------|---------|
| `.bikerack-port` | Port number — readiness signal |
| `.wheelhub-pid` | WheelHub PID — enables `pf bikerack stop` |

Both are deleted on shutdown.

## Layout Persistence

Save and restore BikeRack panel layouts:

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
| `websockets` >= 12.0 | WheelHub WebSocket client |
| `rich` | Terminal rendering (textual dependency) |
| `click` >= 8.0 | CLI framework |
| `pyyaml` >= 6.0 | YAML parsing |
| `textual-image` >= 0.7.0 | Agent portrait images |

The justfile automatically uses `.venv/bin/python3` when `.venv/` exists.

### Launch

```bash
# Default — connects to WheelHub on localhost:1898
just tui

# Point at a specific project directory
just tui dir=/path/to/project

# Custom WheelHub port
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
PYTHONPATH=pennyfarthing-dist:$PYTHONPATH .venv/bin/python3 -m pf.bikerack.tui
```

**Portrait images not rendering**
`textual-image` is included in the base install. Requires a terminal with Sixel or Kitty graphics protocol support (iTerm2, WezTerm, Kitty). Falls back to text-only in unsupported terminals.

## Constraints

- **No MessagePanel** — Claude conversation stays in your terminal. This is intentional.
- **Single session** — one Claude CLI per BikeRack instance.

## Key Files

| File | Purpose |
|------|---------|
| `pf/bikerack/cli.py` | `pf bikerack` launcher CLI |
| `pf/bikerack/launcher.py` | WheelHub process management |
| `pf/wheelhub/app.py` | FastAPI application |
| `pf/wheelhub/tui.py` | Textual TUI application |

<info>
**ADR:** `docs/adr/0024-bikerack-mode.md`
</info>
