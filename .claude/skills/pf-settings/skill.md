---
name: pf-settings
description: |
  View and manage .pennyfarthing/config.local.yaml settings.
  Get, set, and show configuration values using dot-path notation.
args: "[show|get|set] [key] [value]"
---

# /pf-settings - Configuration Settings

View and manage `.pennyfarthing/config.local.yaml` settings.

## Quick Reference

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-settings show` | `pf settings show` | Pretty-print all settings |
| `/pf-settings get <key>` | `pf settings get <key>` | Get value by dot-path |
| `/pf-settings set <key> <value>` | `pf settings set <key> <value>` | Set value by dot-path |

## Config Structure

Settings live in `.pennyfarthing/config.local.yaml`. Keys are nested — always use the full dot-path.

| Dot-Path | Type | Description |
|----------|------|-------------|
| `theme` | string | Active persona theme name |
| `last_panel` | string | Last viewed panel |
| `split.left` | string | Left split panel |
| `split.right` | string | Right split panel |
| `workflow.bell_mode` | bool | Bell mode (message injection) |
| `workflow.relay_mode` | bool | Auto-handoff between agents |
| `workflow.statusbar` | bool | Show status bar |
| `workflow.git_monitor` | bool | Git file watcher |
| `workflow.permission_mode` | string | Permission level (standard, accept) |
| `workflow.pr_mode` | string | PR creation mode (draft, ready) |
| `workflow.pr_merge` | string | PR merge strategy (auto, manual) |
| `display.colorPreset` | string | UI color theme |
| `display.fonts.uiFont` | string | UI font (system, custom) |
| `display.fonts.codeFont` | string | Code font (system, custom) |
| `display.fonts.customUiFont` | string | Custom UI font family |
| `display.fonts.customCodeFont` | string | Custom code font family |

**Keys that are NOT top-level** (common mistakes):
- `statusbar` → use `workflow.statusbar`
- `bell_mode` → use `workflow.bell_mode`
- `relay_mode` → use `workflow.relay_mode`
- `permission_mode` → use `workflow.permission_mode`
- `colorPreset` → use `display.colorPreset`

## Examples

```bash
# Show all interesting settings (theme, workflow, display, split, last_panel)
pf settings show

# Get a specific value
pf settings get theme                    # → mash
pf settings get workflow.relay_mode       # → True
pf settings get display.colorPreset      # → Midnight

# Set workflow flags (these are under workflow.*, not top-level)
pf settings set workflow.bell_mode false
pf settings set workflow.relay_mode true
pf settings set workflow.statusbar true

# Set display settings
pf settings set display.colorPreset monokai

# Set top-level values
pf settings set theme discworld
pf settings set last_panel diffs
```

## Notes

- Dot-path notation traverses nested keys: `workflow.relay_mode` → `workflow: { relay_mode: ... }`
- Value coercion: `true`/`false` → bool, numeric strings → int, else string
- `show` skips large blobs (layout, bikerack_layout, panels, theme_characters) for readability
- **Never set bare `statusbar`, `bell_mode`, or `relay_mode`** — these belong under `workflow.`
