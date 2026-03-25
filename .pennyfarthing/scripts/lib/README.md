# Library Scripts

Shared bash libraries sourced by other scripts.

## Libraries

| Script | Purpose |
|--------|---------|
| `common.sh` | Common utilities (colors, logging basics) |
| `logging.sh` | Structured logging functions |
| `retry.sh` | Retry logic with exponential backoff |
| `checkpoint.sh` | Checkpointing for long-running operations |
| `file-lock.sh` | File locking utilities |
| `find-root.sh` | Project root finder |

## Usage

These are sourced by other scripts, not run directly:

```bash
source "$SCRIPTS_DIR/lib/common.sh"
source "$SCRIPTS_DIR/lib/logging.sh"
```

## Ownership

- **Primary users:** All scripts
- **Maintained by:** Core Pennyfarthing team
