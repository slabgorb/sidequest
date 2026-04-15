---
description: Interrupt-driven bug fix during active story work
---

# Patch Mode

Quick fix for blocking issues during active story work. Branches from your FEATURE branch (not develop), fixes the issue, and restores workflow state.

<purpose>
Enable rapid bug fixes without abandoning current story context. Preserves workflow state and returns to previous work after fix is merged.
</purpose>

<when-to-use>
- Blocking bug discovered during story implementation
- Script error preventing progress
- Path or config issue blocking development
- Urgent UI fix needed before continuing
- Any issue that blocks current work but isn't part of the story
</when-to-use>

<when-not-to-use>
- For planned feature work (use `/pf-sprint work`)
- For quick maintenance (use `/chore`)
- For standalone features (use `/standalone`)
- When not actively working on a story
</when-not-to-use>

<usage>
```bash
# Start a patch (prompts for description)
/patch

# With description
/patch "fix missing import in utils"

# Alternative trigger
/fix-blocker "script path not found"
```
</usage>

<key-differences>
| Aspect | `/patch` | `/trivial` | `/standalone` |
|--------|----------|------------|---------------|
| Branches from | Feature branch | develop | develop |
| Merges to | Feature branch | develop | develop |
| Preserves state | Yes (stack-based) | No | No |
| Workflow | Dev only | SM → Dev → finish | SM → finish |
| Use case | Mid-story fix | Quick new feature | Wrap dirty changes |
</key-differences>

<workflow>

## Flow: Dev Only (No TEA, No Review)

1. **Capture State** - Save current story/workflow to patch stack
2. **Create Branch** - `patch/{description}-{timestamp}` from current feature branch
3. **Fix Issue** - Dev implements minimal fix
4. **Commit** - `fix(patch): {description} [from:{story_id}]`
5. **Merge** - Merge patch branch back to feature branch
6. **Restore** - Pop state from patch stack, continue story work

</workflow>

## Execution

### Step 1: Capture Current State

```bash
# Verify we're on a feature branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ ! "$CURRENT_BRANCH" =~ ^feat/ ]]; then
  echo "ERROR: /patch requires active feature branch work"
  echo "Current branch: $CURRENT_BRANCH"
  echo "Use /standalone or /chore for fixes outside story work"
  exit 1
fi

# Find active session
SESSION_FILE=$(ls -t .session/*-session.md 2>/dev/null | head -1)
if [ -z "$SESSION_FILE" ]; then
  echo "ERROR: No active session found"
  exit 1
fi

# Extract current state
STORY_ID=$(grep -m1 "^**Story ID:**" "$SESSION_FILE" | sed 's/.*: //')
WORKFLOW=$(grep -m1 "^**Workflow:**" "$SESSION_FILE" | sed 's/.*: //')
PHASE=$(grep -m1 "^**Phase:**" "$SESSION_FILE" | sed 's/.*: //')
AGENT=$(grep -m1 "^**Agent:**" "$SESSION_FILE" | sed 's/.*: //')

echo "Saving state for $STORY_ID (phase: $PHASE)"
```

### Step 2: Push State to Patch Stack

```bash
# Create or append to patch stack
STACK_FILE=".session/patch-stack.yaml"

# Generate stack entry
cat >> "$STACK_FILE" << EOF
- story_id: "$STORY_ID"
  workflow: "$WORKFLOW"
  phase: "$PHASE"
  agent: "$AGENT"
  feature_branch: "$CURRENT_BRANCH"
  timestamp: "$(date -Iseconds)"
EOF

echo "State pushed to patch stack"
```

### Step 3: Create Patch Branch

```bash
# Get description from args or prompt
DESCRIPTION="${1:-}"
if [ -z "$DESCRIPTION" ]; then
  echo "Enter patch description:"
  read DESCRIPTION
fi

# Generate branch name
SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-' | cut -c1-30)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
PATCH_BRANCH="patch/${SLUG}-${TIMESTAMP}"

# Create branch from current position
git checkout -b "$PATCH_BRANCH"
echo "Created patch branch: $PATCH_BRANCH"
```

### Step 4: Dev Implements Fix

The developer implements the minimal fix needed. This is a single-agent phase with no TEA or review required.

### Step 5: Commit and Merge

```bash
# Stage and commit
git add .
git commit -m "fix(patch): ${DESCRIPTION} [from:${STORY_ID}]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Merge back to feature branch
git checkout "$CURRENT_BRANCH"
git merge "$PATCH_BRANCH" --no-ff -m "Merge patch: ${DESCRIPTION}"

# Delete patch branch
git branch -d "$PATCH_BRANCH"
```

### Step 6: Restore State

```bash
# Pop from patch stack
STACK_FILE=".session/patch-stack.yaml"

# Get last entry and remove it
# (In practice, use yq or Python script for proper YAML handling)

echo "Patch complete. Restored to $STORY_ID phase: $PHASE"
echo "Run /${AGENT} to continue story work"
```

## Nested Patches

Patches can be nested - if a patch uncovers another blocking issue, run `/patch` again. The stack preserves each level:

```yaml
# .session/patch-stack.yaml
- story_id: "75-3"
  workflow: "tdd"
  phase: "green"
  agent: "dev"
  feature_branch: "feat/<PROJECT-KEY>-add-feature"
  timestamp: "2026-02-03T10:30:00-05:00"

- story_id: "75-3"
  workflow: "patch"
  phase: "fix"
  agent: "dev"
  feature_branch: "patch/fix-import-20260203-103500"
  timestamp: "2026-02-03T10:45:00-05:00"
```

When patches complete, state is restored in LIFO order.

## Safety

- **Never patch on develop** - Patches branch from feature work
- **Minimal scope** - Fix only the blocking issue
- **No skip** - Can't skip patch; must complete or abort
- **Stack limit** - Max 5 nested patches to prevent confusion

## Comparison

| Command | Tracking | Branch From | Merge To | State |
|---------|----------|-------------|----------|-------|
| `/patch` | Implicit | Feature | Feature | Preserved |
| `/chore` | None | develop | develop | None |
| `/standalone` | Jira | develop | develop | None |
| `/pf-sprint work` | Jira + Sprint | develop | develop | Full session |

<related>
- `/chore` - Quick commits without tracking
- `/standalone` - Wrap changes into tracked Jira story
- `/pf-sprint work` - Start planned sprint story
</related>
