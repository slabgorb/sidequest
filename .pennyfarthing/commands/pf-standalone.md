---
description: Wrap current changes into a standalone Jira story, branch, PR, and merge
---

# Standalone Story

Quickly wrap dirty changes into a tracked Jira story without the full sprint/workflow ceremony. Creates a Jira ticket, feature branch, commits, pushes, creates PR, and merges.

<purpose>
Fast path for shipping completed work that deserves tracking but doesn't need story setup upfront.
</purpose>

<when-to-use>
- You've done exploratory work that turned into something shippable
- A bug fix or feature emerged during other work
- Process improvements that should be tracked
- Any change worth a Jira ticket but not a full sprint story
</when-to-use>

<usage>
```bash
# Interactive: prompts for title and description
/standalone

# With title
/standalone "Add drift detection script"

# With title and points
/standalone "Add drift detection script" 2
```
</usage>

<workflow>
1. Verify dirty files exist (abort if clean)
2. Show changes and confirm with user
3. Create Jira story (prompts for title/description if not provided)
4. Add story to current sprint and mark Done
5. Create feature branch: `feat/<PROJECT-KEY>-{slug}`
6. Stage and commit changes
7. Push branch
8. Create PR with summary
9. Merge PR (squash) and delete branch
10. Return to develop
11. Add done story to `current-sprint.yaml` standalone_stories section
12. Write retroactive session file to `sprint/archive/{JIRA_KEY}-session.md`
</workflow>

## Execution

### Step 1: Pre-Flight

```bash
# Abort if clean
git diff --quiet && git diff --cached --quiet && {
  echo "ERROR: No changes to commit."
  exit 1
}

echo "=== Changes to Commit ==="
git status --short
git diff --stat
```

### Step 2: Gather Story Info

If title not provided, prompt:
- **Title:** Short summary (becomes Jira summary and commit message)
- **Description:** What was done (becomes Jira description and PR body)
- **Points:** Story points (default: 2)

```bash
# Defaults
TITLE="${1:-}"
POINTS="${2:-2}"

if [ -z "$TITLE" ]; then
  # Prompt user for title
  echo "Enter story title:"
  read TITLE
fi

# Generate description from changed files
CHANGED_FILES=$(git status --porcelain | awk '{print $2}')
DESCRIPTION="## Changes
$(git diff --stat)

## Files
$(echo "$CHANGED_FILES" | head -20)"
```

### Step 3: Create Jira Story

```bash
# Create Jira story
JIRA_OUTPUT=$(jira issue create \
  --project <PROJECT> \
  --type Story \
  --summary "$TITLE" \
  --body "$DESCRIPTION" \
  --label pennyfarthing \
  --custom story-points="$POINTS" \
  --no-input 2>&1)

JIRA_KEY=$(echo "$JIRA_OUTPUT" | grep -oE '<PROJECT>-[0-9]+' | head -1)

if [ -z "$JIRA_KEY" ]; then
  echo "ERROR: Failed to create Jira story"
  echo "$JIRA_OUTPUT"
  exit 1
fi

echo "Created: $JIRA_KEY"

# Read sprint ID from current-sprint.yaml (never hardcode)
SPRINT_ID=$(grep 'jira_sprint_id:' sprint/current-sprint.yaml | awk '{print $2}')
if [ -z "$SPRINT_ID" ]; then
  echo "WARNING: Could not read jira_sprint_id from sprint/current-sprint.yaml"
else
  jira sprint add "$SPRINT_ID" "$JIRA_KEY"
fi
jira issue move "$JIRA_KEY" "Done"
```

### Step 4: Create Branch and Commit

```bash
# Generate slug from title
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-' | cut -c1-30)

# Stash, update develop, create branch
git stash push -m "standalone-wip-$(date +%s)"
git checkout develop && git pull origin develop
BRANCH="feat/${JIRA_KEY}-${SLUG}"
git checkout -b "$BRANCH"
git stash pop

# Stage and commit
git add .
git commit -m "feat: ${TITLE} (${JIRA_KEY})

${DESCRIPTION}

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 5: Push and Create PR

Format the PR title using the project's `pr_title_format` setting:
```bash
PR_TITLE=$(source .venv/bin/activate && python -c "
from pf.git.repos import format_pr_title
print(format_pr_title(jira_key='${JIRA_KEY}', title='${TITLE}'))
")
```

```bash
git push -u origin "$BRANCH"

gh pr create \
  --title "$PR_TITLE" \
  --body "## Summary
${DESCRIPTION}

## Jira
[${JIRA_KEY}]($(pf settings get jira.url)/browse/${JIRA_KEY})

## Test plan
- [x] Changes verified locally

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

### Step 6: Merge and Cleanup

```bash
# Get PR number and merge
PR_URL=$(gh pr view --json url -q '.url')
gh pr merge --squash --delete-branch

# Return to develop
git checkout develop
git pull origin develop

echo "✅ Done: $JIRA_KEY merged"
echo "   Jira: $(pf settings get jira.url)/browse/$JIRA_KEY"
echo "   PR: $PR_URL"
```

### Step 7: Sprint Tracking & Session Archive

After merge, register the story in sprint YAML and write an archived session file.

**Add to `current-sprint.yaml` standalone_stories section:**

Append a new entry under `standalone_stories:` in `sprint/current-sprint.yaml` (create the section if it doesn't exist). Use the same field structure as `stories:` entries:

```yaml
standalone_stories:
  - id: ${JIRA_KEY}
    jira: ${JIRA_KEY}
    title: ${TITLE}
    points: ${POINTS}
    status: done
    repos: ${REPO}        # pennyfarthing or orchestrator (whichever has the changes)
    pr: ${PR_NUMBER}
    branch: ${BRANCH}
```

**Write retroactive session file** to `sprint/archive/${JIRA_KEY}-session.md`:

```markdown
# Standalone: ${TITLE}

**Jira:** ${JIRA_KEY}
**Points:** ${POINTS}
**Priority:** P2
**Workflow:** standalone
**Status:** done
**Repos:** ${REPO}
**Branch:** ${BRANCH}
**PR:** ${PR_NUMBER}
**Started:** ${TODAY}
**Completed:** ${TODAY}

---

## Description

${DESCRIPTION}

## Files Changed

| File | Change |
|------|--------|
${FILE_TABLE}
```

**Commit both tracking files** in the orchestrator repo:

```bash
# Return to orchestrator root
cd ${PROJECT_ROOT}
git add sprint/current-sprint.yaml sprint/archive/${JIRA_KEY}-session.md
git commit -m "chore(sprint): add standalone ${JIRA_KEY} to sprint tracking"
```

## Safety

- **NEVER commit directly to develop**
- **Never force push**
- **Never commit secrets** (.env, credentials)
- **Abort if working directory is clean**
- **Confirm changes before proceeding**

## Comparison

| Command | Tracking | Branch | PR | Use For |
|---------|----------|--------|-----|---------|
| `/chore` | None | chore/* | No | Quick maintenance |
| `/standalone` | Jira | feat/* | Yes | Trackable features |
| `/pf-sprint work` | Jira + Sprint | feat/* | Yes | Planned sprint work |

<related>
- `/chore` - Quick commits without Jira tracking
- `/pf-sprint work` - Full sprint workflow with story setup
- `/pf-git cleanup` - Organize multiple changes into groups
</related>
