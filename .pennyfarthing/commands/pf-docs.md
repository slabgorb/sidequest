---
description: Domain documentation management
args: "[update]"
---

# Documentation Operations

<purpose>
Manage domain documentation files. Currently supports updating CLAUDE-*.md domain documentation files to reflect the current state of the codebase.
</purpose>

## Commands

### `/pf-docs update`

Update CLAUDE-*.md domain documentation files based on current codebase.

Scans the relevant files for each domain and updates documentation with:
- Service files and their main functions
- Handler files and their endpoints
- Model files and their structs
- Worker files (if applicable)
- Test files

## Related

- `/pf-help` — Context-aware help
- `/tech-writer` — Technical Writer agent
