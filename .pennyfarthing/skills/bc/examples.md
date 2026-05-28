# BC (Panel Focus) — Examples

## Setting Focus

```bash
# Focus on Sprint panel
pf bc sprint

# Focus on Diffs panel
pf bc diffs

# Focus on Acceptance Criteria
pf bc ac

# Focus on Git panel
pf bc git

# Preview without changing
pf bc sprint --dry-run
```

## Clearing Focus

```bash
# Remove focus setting
pf bc reset

# Preview
pf bc reset --dry-run
```

## Named Layouts

```bash
# Save current layout as "normal"
pf bc save normal

# Save current layout as "review"
pf bc save review

# Save current layout as "debug"
pf bc save debug

# List all saved layouts
pf bc list

# Switch to review layout
pf bc load review

# Switch back to normal
pf bc load normal

# Delete a specific layout
pf bc clear review

# Delete all layouts
pf bc clear-all
```

## Common Workflows

### During code review
```bash
pf bc save normal          # Save current layout first
pf bc diffs                # Focus on diffs
# ... do review ...
pf bc load normal          # Restore normal layout
```

### Debugging session
```bash
pf bc save normal
pf bc debug                # Focus debug panel
# ... debug ...
pf bc reset                # Clear focus
```

### Sprint planning
```bash
pf bc sprint               # Focus sprint panel
# ... review backlog ...
pf bc reset
```
