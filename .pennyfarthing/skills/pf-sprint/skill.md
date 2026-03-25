---
name: sprint
description: |
  Sprint status, backlog, and story management for Pennyfarthing. Use when checking current
  sprint status, finding available stories, reviewing backlog, or understanding story context
  and history.
  IMPORTANT: Always use `pf sprint` CLI commands - never manually edit sprint YAML.
args: "[status|backlog|work|story|epic|initiative|archive|new|future|info|metrics|validate|standalone]"
hooks:
  PostToolUse:
    - command: pf hooks sprint-yaml
      matcher: Edit|Write
---

# /pf-sprint - Sprint Management

<critical>
Never manually edit `sprint/current-sprint.yaml`. Use `pf sprint` CLI commands for deterministic, correct YAML formatting.
</critical>

## Quick Reference

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-sprint` | `pf sprint status` | Show sprint status |
| `/pf-sprint status [filter]` | `pf sprint status [filter]` | Filter: `backlog`, `todo`, `in-progress`, `review`, `done` |
| `/pf-sprint backlog` | `pf sprint backlog` | Available stories by epic |
| `/pf-sprint work [id]` | `pf sprint work [story-id] [--dry-run]` | Start work on a story |
| `/pf-sprint archive <id> [pr]` | `pf sprint archive <id> [pr] [--apply] [--dry-run]` | Archive completed story |
| `/pf-sprint new ...` | `pf sprint new <yyww> <jira-id> <start> <end> "<goal>" [--dry-run]` | Initialize new sprint |
| `/pf-sprint future [epic-id]` | `pf sprint future [epic-id]` | Show future initiatives |
| `/pf-sprint info` | `pf sprint info` | Sprint header as JSON |
| `/pf-sprint metrics` | `pf sprint metrics [--json]` | Sprint progress and velocity |
| `/pf-sprint validate` | `pf sprint validate [--fix] [--strict]` | Validate sprint YAML |

### Story Commands

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-sprint story show <id>` | `pf sprint story show <id> [--json]` | Show story details |
| `/pf-sprint story add ...` | `pf sprint story add <epic-id> "<title>" <pts> [opts]` | Add story to epic |
| `/pf-sprint story update <id>` | `pf sprint story update <id> [opts]` | Update story fields |
| `/pf-sprint story field <id> <f>` | `pf sprint story field <id> <field>` | Get single field value |
| `/pf-sprint story size [pts]` | `pf sprint story size [points]` | Sizing guidelines |
| `/pf-sprint story template [t]` | `pf sprint story template [type]` | Story templates |
| `/pf-sprint story finish <id>` | `pf sprint story finish <id> [--dry-run]` | Complete story workflow |
| `/pf-sprint story claim <id>` | `pf sprint story claim <id> [--claim/--unclaim] [--dry-run]` | Claim/unclaim in Jira |

### Epic Commands

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-sprint epic show <id>` | `pf sprint epic show <id> [--json]` | Show epic details |
| `/pf-sprint epic add <id> <title>` | `pf sprint epic add <id> <title> [opts]` | Add epic to sprint |
| `/pf-sprint epic update <id>` | `pf sprint epic update <id> [--status] [--priority] [--dry-run]` | Update epic fields |
| `/pf-sprint epic promote <id>` | `pf sprint epic promote <id> [--dry-run]` | Move from future to current |
| `/pf-sprint epic archive [id]` | `pf sprint epic archive [id] [--dry-run] [--jira]` | Archive completed epics |
| `/pf-sprint epic cancel <id>` | `pf sprint epic cancel <id> [--jira] [--dry-run]` | Cancel epic and stories |
| `/pf-sprint epic import <file>` | `pf sprint epic import <file> [init] [--marker] [--dry-run]` | Import BMAD epics |
| `/pf-sprint epic remove <id>` | `pf sprint epic remove <id> [--dry-run]` | Remove from future.yaml |
| `/pf-sprint epic field <id> <f>` | `pf sprint epic field <id> <field>` | Get single field value |

### Initiative Commands

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-sprint initiative show <n>` | `pf sprint initiative show <name> [--json]` | Show initiative details |
| `/pf-sprint initiative cancel <n>` | `pf sprint initiative cancel <name> [--jira] [--dry-run]` | Cancel initiative |

### Aliases

| Alias | Equivalent |
|-------|------------|
| `pf status` | `pf sprint status` |
| `pf backlog` | `pf sprint backlog` |
| `pf work` | `pf sprint work` |
| `pf story` | `pf sprint story` |
| `/pf-session new` | `/pf-sprint work` |

---

**Detailed options and behavior:** [usage.md](usage.md)
**Practical examples:** [examples.md](examples.md)

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/pf-jira` | Jira operations (create, sync, reconcile, claim, assign) |
