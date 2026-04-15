# Workflow — Examples

## Listing & Viewing

```bash
# List all available workflows
pf workflow list

# Show TDD workflow details
pf workflow show tdd

# Show current session's workflow
pf workflow show

# Show trivial workflow
pf workflow show trivial
```

## Checking State

```bash
# Check current workflow state
pf workflow check
pf workflow check --json

# Who owns the "review" phase in TDD?
pf workflow phase-check tdd review
# Returns: reviewer

# Who owns the "implement" phase in trivial?
pf workflow phase-check trivial implement
# Returns: dev

# Get workflow type
pf workflow type tdd
# Returns: phased

pf workflow type architecture
# Returns: stepped

# Emit handoff marker for Frame GUI
pf workflow handoff reviewer
```

## Stepped Workflows (BikeLane)

```bash
# Start architecture workflow in create mode (default)
pf workflow start architecture

# Start in validate mode
pf workflow start architecture --mode validate

# Check progress
pf workflow status

# Resume after interruption
pf workflow resume
pf workflow resume architecture

# Complete current step and advance
pf workflow complete-step
pf workflow complete-step architecture --step 3
```

## Phase Repair

```bash
# Preview phase fix
pf workflow fix-phase 56-1 review --dry-run

# Fix phase to review (after Dev completed)
pf workflow fix-phase 56-1 review

# Fix phase to approved (after Reviewer approved)
pf workflow fix-phase 56-1 approved

# Using Jira key
pf workflow fix-phase <PROJECT-KEY> approved
```

## Switching Workflow Mid-Session

1. Verify the target workflow exists:
   ```bash
   pf workflow show trivial
   ```

2. Edit the session file:
   - Open `.session/{story-id}-session.md`
   - Change `**Workflow:**` line to new workflow name

3. Continue with the new workflow's agent sequence.

## Common Scenarios

### Story upgraded from trivial to TDD
```bash
# Check current state
pf workflow check --json
# Edit session to change workflow from trivial to tdd
# Fix phase to match where you are
pf workflow fix-phase 56-1 red
```

### Agent activated on wrong phase
```bash
# Check who owns the current phase
pf workflow phase-check tdd review
# Returns: reviewer — hand off if you're not the reviewer
pf workflow handoff reviewer
```
