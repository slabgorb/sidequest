# Workflow Scripts

Scripts for workflow mechanics, phase transitions, and quality gates.

## Scripts

| Script | Purpose |
|--------|---------|
| `finish-story.sh` | **DEPRECATED** — forwards to `pf sprint story finish` |
| `fix-session-phase.sh` | Repair session file phase state |
| `check.sh` | Quality gates runner (lint, type check, tests) |
| `list-workflows.sh` | List available workflows |
| `show-workflow.sh` | Show workflow details |
| `start-workflow.sh` | Start a stepped workflow |
| `resume-workflow.sh` | Resume from last completed step |
| `workflow-status.sh` | Show workflow progress |

## Usage

```bash
pf sprint story finish <PROJECT-KEY>
.pennyfarthing/scripts/workflow/start-workflow.sh prd --mode create
```

## Ownership

- **Primary users:** SM agent, `/pf-workflow` skill
- **Maintained by:** Core Pennyfarthing team
