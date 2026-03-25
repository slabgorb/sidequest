# Sprint Scripts

Sprint management is handled by the Python CLI: `pf sprint [COMMAND]`.

## Commands

| Command | Purpose |
|---------|---------|
| `pf sprint status` | Show current sprint status and metrics |
| `pf sprint backlog` | List available stories grouped by epic |
| `pf sprint info` | Sprint info as JSON (for Cyclist sidebar) |
| `pf sprint metrics` | Sprint velocity and progress metrics |
| `pf sprint check <id>` | Check story/epic availability (JSON) |
| `pf sprint future` | Show future initiatives and epics |
| `pf sprint new` | Initialize a new sprint |
| `pf sprint validate <file>` | Validate sprint YAML structure |
| `pf sprint archive <id>` | Archive a completed story |
| `pf sprint work <id>` | Start work on a story |
| `pf sprint story field <id> <field>` | Get a story field value |
| `pf sprint epic field <id> <field>` | Get an epic field value |
| `pf sprint epic promote <id>` | Move epic from future to current sprint |
| `pf sprint epic show <id>` | Show epic details |
| `pf sprint epic cancel <id>` | Cancel an epic |
| `pf sprint epic archive` | Archive completed epics |

## Usage

```bash
pf sprint status
pf sprint backlog
pf sprint future epic-55
pf sprint epic promote epic-41
```

## Ownership

- **Primary users:** SM agent, `/pf-sprint` skill
- **Maintained by:** Core Pennyfarthing team

## Migration Note

All bash scripts previously in this directory have been migrated to Python CLI
commands in `pf/sprint/cli.py`. See PR #716 and the follow-up
deprecation commit for details.
