# Jira Scripts

Scripts for Jira integration, synchronization, and story management.

## Scripts

| Script | Purpose |
|--------|---------|
| `jira-lib.sh` | Shared Jira bash utilities (library) |
| `jira-claim-story.sh` | Claim a story (assign and move to In Progress) |
| `jira-reconcile.sh` | Reconcile Jira with sprint YAML |
| `jira-sync.sh` | Sync story to Jira (wrapper → Python) |
| `jira-sync-story.sh` | Sync individual story (wrapper → Python) |
| `create-jira-epic.sh` | Create Jira epic with stories |
| `create-jira-story.sh` | Create individual Jira story |
| `sync-epic-jira.sh` | Sync epic to Jira (wrapper → Python) |
| `sync-epic-to-jira.sh` | Sync epic to Jira (alternate) |

## Python Implementation

Core logic lives in `pf/jira/`:
- `sync.py` — Epic and story sync
- `bidirectional.py` — Two-way YAML ↔ Jira sync
- `story.py` — Story operations

## Usage

```bash
.pennyfarthing/scripts/jira/jira-claim-story.sh <PROJECT-KEY>
.pennyfarthing/scripts/jira/jira-reconcile.sh
```

## Ownership

- **Primary users:** SM agent, `/pf-jira` skill
- **Maintained by:** Core Pennyfarthing team
