# Jira CLI — Examples

## Viewing & Checking

```bash
# View issue details
pf jira view PROJ-123

# Check if story is available to claim
pf jira check PROJ-123

# Search by JQL
pf jira search "project=PROJ AND type=Epic"
pf jira search "project=PROJ AND parent=PROJ-100"
pf jira search "project=PROJ AND summary~'feedback rules'"
```

## Claiming & Assigning

```bash
# Claim story (assign to self + In Progress)
pf jira claim PROJ-123

# Assign to user by email
pf jira assign PROJ-12345 user@your-org.com

# Assign by GitHub username (auto-mapped via jira.user_map config)
pf jira assign PROJ-12345 github-user

# Preview
pf jira claim PROJ-123 --dry-run
pf jira assign PROJ-123 github-user --dry-run
```

## Transitions

```bash
# Move to In Progress
pf jira move PROJ-123 "In Progress"

# Move to Done
pf jira move PROJ-123 "Done"

# Move to In Review
pf jira move PROJ-123 "In Review"

# Move back to To Do
pf jira move PROJ-123 "To Do"

# Preview
pf jira move PROJ-123 "Done" --dry-run
```

## Creating Issues

```bash
# Create epic + all child stories from sprint YAML
pf jira create epic epic-63
pf jira create epic 63
pf jira create epic 63 --dry-run

# Create single story under an epic
pf jira create story PROJ-100 63-7
pf jira create story PROJ-100 63-7 --dry-run

# Create standalone story (create + sprint + Done)
pf jira create standalone "Fix sprint script shard support"
pf jira create standalone "Fix sprint script shard support" --points 3
pf jira create standalone "Add drift detection" -d "Detects YAML drift"
pf jira create standalone "Quick fix" --dry-run
```

## Linking Issues

```bash
# Block relationship
pf jira link PROJ-123 PROJ-456 "Blocks"

# Parent-child
pf jira link PROJ-123 PROJ-456 "Parent-Child"

# Related (default)
pf jira link PROJ-123 PROJ-456
pf jira link PROJ-123 PROJ-456 "Relates"

# Duplicate
pf jira link PROJ-123 PROJ-456 "Duplicate"
```

## Syncing

```bash
# Sync epic to Jira (all fields)
pf jira sync PROJ-200 --all

# Sync only status transitions
pf jira sync 63 --transition

# Sync only story points
pf jira sync 63 --points

# Preview
pf jira sync 63 --all --dry-run

# Bidirectional sync (Jira wins by default)
pf jira bidirectional --all
pf jira bidirectional --all --dry-run

# YAML wins on conflicts
pf jira bidirectional --status --yaml-wins

# Sync specific fields
pf jira bidirectional --status --points --assignee

# Target specific sprint
pf jira bidirectional --all --sprint 276
```

## Reconciliation

```bash
# Report mismatches
pf jira reconcile

# Auto-fix (add missing stories to sprint)
pf jira reconcile --fix
```

## Sprint Management

```bash
# Read sprint ID from current-sprint.yaml (never hardcode)
SPRINT_ID=$(grep 'jira_sprint_id:' sprint/current-sprint.yaml | awk '{print $2}')

# Add issue to sprint
pf jira sprint add "$SPRINT_ID" PROJ-300

# Preview
pf jira sprint add "$SPRINT_ID" PROJ-300 --dry-run
```

## Common Workflows

### New story from sprint YAML to Jira
```bash
# 1. Add story to sprint YAML
pf sprint story add 91 "New feature" 3

# 2. Create in Jira under existing epic
pf jira create story PROJ-200 91-5

# 3. Claim it
pf jira claim PROJ-301
```

### End-of-sprint reconciliation
```bash
# 1. Check for mismatches
pf jira reconcile

# 2. Sync all completed stories
pf jira bidirectional --all

# 3. Fix any remaining issues
pf jira reconcile --fix
```
