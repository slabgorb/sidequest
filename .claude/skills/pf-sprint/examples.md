# Sprint CLI — Examples

## Status & Discovery

```bash
# Full sprint status
pf sprint status

# Only backlog stories
pf sprint status backlog

# Only in-progress work
pf sprint status in-progress

# Only completed stories
pf sprint status done

# Available stories grouped by epic
pf sprint backlog

# Sprint metrics and velocity
pf sprint metrics
pf sprint metrics --json

# Sprint header as JSON (for scripts)
pf sprint info

# Future initiatives overview
pf sprint future

# Future epic detail with stories
pf sprint future epic-55
```

## Starting Work

```bash
# Show available stories (interactive)
pf sprint work

# Start specific story
pf sprint work 91-3

# Auto-select highest priority
pf sprint work next

# Preview without starting
pf sprint work 91-3 --dry-run

# Check story availability (JSON output)
pf sprint check 91-3
pf sprint check PROJ-400
pf sprint check next
```

## Story Operations

```bash
# Show story details
pf sprint story show 91-3
pf sprint story show PROJ-400 --json

# Add story to epic
pf sprint story add 91 "Add error handling" 3
pf sprint story add 91 "Fix null pointer" 2 --type bug
pf sprint story add 91 "Refactor parser" 3 --workflow trivial --priority p0

# Add standalone story to initiative
pf sprint story add --initiative technical-debt "Fix flaky test" 2 --type bug

# Update story fields
pf sprint story update 91-3 --status in_progress
pf sprint story update 91-3 --status done
pf sprint story update 91-3 --points 5 --priority P0
pf sprint story update 91-3 --assigned-to user@example.com
pf sprint story update 91-3 --workflow tdd-team
pf sprint story update 91-3 --status done --dry-run

# Get single field
pf sprint story field 91-3 workflow    # tdd
pf sprint story field 91-3 jira        # PROJ-400
pf sprint story field 91-3 status      # in_progress

# Sizing guidelines
pf sprint story size
pf sprint story size 5

# Story templates
pf sprint story template
pf sprint story template feature
pf sprint story template bug

# Complete story (archive, merge, Jira transition)
pf sprint story finish 91-3
pf sprint story finish 91-3 --dry-run

# Claim/unclaim in Jira
pf sprint story claim PROJ-400
pf sprint story claim PROJ-400 --unclaim
```

## Epic Operations

```bash
# Show epic details
pf sprint epic show 91
pf sprint epic show PROJ-500
pf sprint epic show 91 --json

# Add new epic
pf sprint epic add epic-95 "New Feature Epic"
pf sprint epic add epic-95 "New Feature" --priority p0 --jira PROJ-501
pf sprint epic add epic-95 "New Feature" -d "Description of the epic"

# Update epic
pf sprint epic update 91 --status in_progress
pf sprint epic update PROJ-500 --priority P0
pf sprint epic update 91 --status done --dry-run

# Promote from future to current sprint
pf sprint epic promote epic-55
pf sprint epic promote 55
pf sprint epic promote epic-55 --dry-run

# Archive completed epics
pf sprint epic archive                     # Scan all completed
pf sprint epic archive --dry-run           # Preview
pf sprint epic archive 91                  # Specific epic
pf sprint epic archive 91 --jira           # Also update Jira

# Cancel epic and all stories
pf sprint epic cancel 91
pf sprint epic cancel 91 --jira            # Also cancel in Jira
pf sprint epic cancel 91 --dry-run

# Import BMAD epics
pf sprint epic import docs/planning/feature-epics.md
pf sprint epic import docs/planning/feature-epics.md "My Feature" --marker my-feature
pf sprint epic import docs/planning/feature-epics.md --dry-run

# Remove from future.yaml
pf sprint epic remove epic-41
pf sprint epic remove epic-41 --dry-run

# Get epic field
pf sprint epic field 91 jira               # PROJ-500
pf sprint epic field 91 title              # Epic title
```

## Initiative Operations

```bash
# Show initiative details
pf sprint initiative show benchmark-reliability
pf sprint initiative show technical-debt --json

# Cancel initiative
pf sprint initiative cancel technical-debt
pf sprint initiative cancel technical-debt --jira
pf sprint initiative cancel technical-debt --dry-run
```

## Sprint Lifecycle

```bash
# Initialize new sprint
pf sprint new 2607 278 2026-02-16 2026-03-01 "Performance and polish"
pf sprint new 2607 278 2026-02-16 2026-03-01 "Performance and polish" --dry-run

# Archive completed story
pf sprint archive 91-3 856
pf sprint archive 91-3 856 --apply          # Archive + remove atomically

# Validate sprint YAML
pf sprint validate                           # All validators
pf sprint validate sprint                    # Sprint YAML only
pf sprint validate --fix                     # Auto-fix issues
pf sprint validate --strict                  # Warnings as errors
```

## Sizing Quick Reference

| Points | Scale | Complexity | Examples |
|--------|-------|------------|----------|
| 1-2 | Trivial | Single file, minimal testing | Config, typo, simple fix |
| 3 | Small | Few files, some testing | Validation, single component |
| 5 | Medium | Multiple files, comprehensive testing | New page, API endpoint |
| 8 | Large | Significant scope, extensive testing | Integration, major refactor |
| 13+ | **SPLIT** | Too complex for single story | Break into smaller stories |
