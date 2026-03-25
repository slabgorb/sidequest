# BC (Panel Focus) — Detailed Usage

## Panel Focus Commands

### Set Focus

```bash
pf bc <panel> [--dry-run]
```

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `panel` | Yes | Panel name (see list below) |
| `--dry-run` | No | Preview without making changes |

Valid panels:

| Panel | Description |
|-------|-------------|
| `sprint` | Sprint status panel |
| `git` | Git operations panel |
| `diffs` | File diffs panel |
| `todo` | Todo/task panel |
| `workflow` | Workflow phase panel |
| `background` | Background tasks panel |
| `audit-log` | Audit log panel |
| `changed` | Changed files panel |
| `ac` | Acceptance Criteria panel |
| `debug` | Debug panel |
| `settings` | Settings panel |

The `message` panel (sacred center) is not focusable.

Output on success: `{"success": true, "panel": "<panel>"}`
Output on error: `{"success": false, "error": "Invalid panel..."}`

### Clear Focus

```bash
pf bc reset [--dry-run]
```

Removes the `focus` key from `.pennyfarthing/config.local.yaml`.

---

## Named Layout Commands

### Save Layout

```bash
pf bc save <NAME> [--dry-run]
```

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Layout name to save as |
| `--dry-run` | No | Preview without making changes |

Fetches the active layout from the running Frame server (reads `.frame-port`). Fails if no server is running.

Output: `{"success": true, "name": "<name>", "panels": <count>}`

### Load Layout

```bash
pf bc load <NAME> [--dry-run]
```

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Layout name to load |
| `--dry-run` | No | Preview without making changes |

Output: `{"success": true, "name": "<name>", "layout": {...}}`

### List Layouts

```bash
pf bc list
```

No arguments. Output: `{"success": true, "layouts": ["normal", "review", ...]}`

### Delete Layout

```bash
pf bc clear <NAME> [--dry-run]
```

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Layout name to delete |
| `--dry-run` | No | Preview without making changes |

### Delete All Layouts

```bash
pf bc clear-all [--dry-run]
```

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview without making changes |

---

## Storage

- Panel focus: `.pennyfarthing/config.local.yaml` under the `focus` key
- Named layouts: `.pennyfarthing/config.local.yaml` under the `named_layouts` key
- All other config keys (theme, layout, display, etc.) are preserved on write
- Config directory is created if it doesn't exist
