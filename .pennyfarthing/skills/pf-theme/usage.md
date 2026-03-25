# Theme CLI — Detailed Usage

## Commands

### `pf.sh theme create`

Create a new custom theme from a base theme.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Name for the new theme (lowercase, hyphens allowed) |
| `--base` | No | Base theme to copy from (defaults to current theme) |
| `--user` | No | Create as user-level theme (~/.claude/pennyfarthing/themes/) |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh theme list`

Show all available themes with current theme highlighted.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `--json` | No | Output as JSON |

### `pf.sh theme set`

Set the active persona theme.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Theme name to activate |
| `--dry-run` | No | Show what would be done without making changes |

### `pf.sh theme show`

Show theme details including agent character mappings.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | No | Theme to show (defaults to current theme) |
| `--full` | No | Show full agent details (OCEAN, quirks, catchphrases, etc.) |
| `--json` | No | Output as JSON |

