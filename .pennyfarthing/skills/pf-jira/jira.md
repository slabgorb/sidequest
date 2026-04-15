---
name: jira
description: Jira CLI commands for sprint management. Use when viewing, assigning, or updating Jira issues from the command line.
args: "[view|check|claim|move|assign|create|sync|bidirectional|reconcile|link|search|sprint]"
---

# /pf-jira - Jira Issue Management

<critical>
Never fabricate or guess Jira IDs. Valid keys follow `<PROJECT-KEY>`. Old-style IDs like `31-18` are local sprint YAML placeholders.
</critical>

<run>
pf jira <command> [args]
</run>

<output>
Command-specific output. Most commands print status messages. Use `--dry-run` on mutating commands to preview changes.
</output>

## Quick Reference

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-jira view <key>` | `pf jira view <key>` | View issue details |
| `/pf-jira check <key>` | `pf jira check <key>` | Check availability |
| `/pf-jira claim <key>` | `pf jira claim <key> [--dry-run]` | Assign to self + In Progress |
| `/pf-jira move <key> <status>` | `pf jira move <key> "<status>" [--dry-run]` | Transition status |
| `/pf-jira assign <key> <user>` | `pf jira assign <key> <user> [--dry-run]` | Assign to user |
| `/pf-jira link <p> <c> [type]` | `pf jira link <parent> <child> [type] [--dry-run]` | Link two issues |
| `/pf-jira search "<jql>"` | `pf jira search "<jql>"` | Search by JQL |
| `/pf-jira create epic <id>` | `pf jira create epic <id> [--dry-run]` | Create epic + stories |
| `/pf-jira create story <ek> <sid>` | `pf jira create story <epic-key> <story-id> [--dry-run]` | Create single story |
| `/pf-jira create standalone` | `pf jira create standalone "<title>" [opts]` | Create standalone story |
| `/pf-jira sync <epic>` | `pf jira sync <epic> [--transition] [--points] [--all] [--dry-run]` | Sync epic to Jira |
| `/pf-jira bidirectional` | `pf jira bidirectional [opts]` | Bidirectional sync |
| `/pf-jira reconcile` | `pf jira reconcile [--fix]` | Reconciliation report |
| `/pf-jira sprint add <sid> <key>` | `pf jira sprint add <sprint-id> <issue-key> [--dry-run]` | Add issue to sprint |

### GitHub to Jira User Mapping

Configure in `.pennyfarthing/config.local.yaml`:

```yaml
jira:
  user_map:
    github-user: jira-email@your-org.com
```

The mapping is used by `pf jira assign` and `pf jira claim` to resolve GitHub usernames to Jira emails.

### Prerequisites

```bash
brew install ankitpokhrel/jira-cli/jira-cli
jira init
export JIRA_API_TOKEN='your-token'
```

---

**Detailed options and behavior:** [usage.md](usage.md)
**Practical examples:** [examples.md](examples.md)
