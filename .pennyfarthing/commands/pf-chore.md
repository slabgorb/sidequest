---
description: Quick commit for small changes without full git-cleanup ceremony
---

# Quick Chore Commit

Quickly commit dirty changes without the full `/pf-git cleanup` ceremony. Checks **all repos** (orchestrator + subrepos), creates branches, commits, merges to develop, and pushes.

<purpose>
Fast path for committing small changes that don't warrant story tracking.
</purpose>

<usage>
```bash
# Default: chore commit (auto-generate message)
/chore

# Chore with custom message
/chore "update sprint tracking"

# Variants for different commit types
/chore doc                       # docs: prefix, docs/* branch
/chore doc "update README"       # docs: with custom message
/chore ux                        # style: prefix, ux/* branch
/chore ux "adjust button spacing"
```
</usage>

<variants>
| Command | Branch | Commit Prefix | Use For |
|---------|--------|---------------|---------|
| `/chore` | `chore/*` | `chore:` | Maintenance, config, scripts |
| `/chore doc` | `docs/*` | `docs:` | Documentation, README, guides |
| `/chore ux` | `ux/*` | `style:` | UI tweaks, CSS, styling |
</variants>

<workflow>
**CRITICAL: Never commit directly to develop. Branch protection hooks will reject direct commits.**

**CRITICAL: Never use git stash.** The stash/pull/pop pattern can silently revert changes when upstream modifies the same files during the pull.

**CRITICAL: Always check ALL repos, not just the orchestrator.** Most changes are in subrepos (e.g., `pennyfarthing/`). Use `git -C {repo_path}` for subrepo operations.

1. Check ALL repos for dirty files (orchestrator + subrepos from `repos.yaml`)
2. Abort if all repos are clean
3. Determine variant (chore/doc/ux) from first arg
4. For EACH dirty repo, independently:
   a. Create branch from current HEAD: `{variant}/{timestamp}`
   b. Stage and commit all changes
   c. Fetch origin and rebase onto latest develop
   d. Switch to develop, merge the branch
   e. Push develop
   f. Delete local branch
</workflow>

## Execution

### Step 1: Multi-Repo Pre-Flight

**ALWAYS check all repos.** Read `repos.yaml` for repo paths.

```bash
# Check ALL repos for dirty changes
# Orchestrator root (.)
git status --short

# Subrepos (e.g., pennyfarthing/)
git -C pennyfarthing status --short 2>/dev/null

# Or use the multi-repo status script:
pf git status --brief
```

Collect which repos have changes. If ALL repos are clean, abort with "No changes to commit."

**Common case:** Only the subrepo (`pennyfarthing/`) has changes. The orchestrator is clean. This is normal — framework development happens in the subrepo.

### Step 2: Parse Arguments

```bash
# Defaults
VARIANT="chore"
PREFIX="chore"
BRANCH_TYPE="chore"
MESSAGE=""

# Check first arg
case "$1" in
  doc|docs)
    VARIANT="docs"
    PREFIX="docs"
    BRANCH_TYPE="docs"
    shift
    ;;
  ux|style)
    VARIANT="ux"
    PREFIX="style"
    BRANCH_TYPE="ux"
    shift
    ;;
esac

# Remaining args are the message
MESSAGE="$*"
```

### Step 3: For Each Dirty Repo — Generate Message, Branch, Commit, Merge, Push

Repeat steps 3a–3d for each repo that has dirty changes. Use `git -C {repo_path}` for subrepo operations, or `cd` into the subrepo temporarily.

#### Step 3a: Generate Message (if user didn't provide one)

Generate a message based on the changed files **in that specific repo**.

```bash
if [ -z "$MESSAGE" ]; then
  CHANGED_FILES=$(git -C {repo_path} status --porcelain | awk '{print $2}')

  case "$VARIANT" in
    docs)
      if echo "$CHANGED_FILES" | grep -qi "readme"; then
        MESSAGE="update README"
      elif echo "$CHANGED_FILES" | grep -qi "changelog"; then
        MESSAGE="update changelog"
      else
        MESSAGE="update documentation"
      fi
      ;;
    ux)
      if echo "$CHANGED_FILES" | grep -qE "\.css|\.scss"; then
        MESSAGE="update styles"
      else
        MESSAGE="update styling"
      fi
      ;;
    chore)
      if echo "$CHANGED_FILES" | grep -q "sprint/"; then
        MESSAGE="update sprint tracking"
      elif echo "$CHANGED_FILES" | grep -q "\.claude/"; then
        MESSAGE="update pennyfarthing config"
      elif echo "$CHANGED_FILES" | grep -q "scripts/"; then
        MESSAGE="update scripts"
      else
        FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l | tr -d ' ')
        MESSAGE="minor updates to ${FILE_COUNT} files"
      fi
      ;;
  esac
fi
```

**For subrepos:** Also review the diff to generate a meaningful message. Prefer descriptive messages over generic ones (e.g., "migrate TTY panel to WebSocket" over "minor updates to 3 files").

#### Step 3b: Branch and Commit

**IMPORTANT: Do NOT use git stash.** Stash + pull + pop can silently revert changes when upstream modifies the same files.

```bash
# For subrepos, cd into the repo first (or use git -C throughout)
cd {repo_path}

# Create branch from current HEAD (preserves dirty changes)
BRANCH="${BRANCH_TYPE}/$(date +%Y%m%d-%H%M%S)"
git checkout -b "$BRANCH"

# Stage and commit on the branch
git add .
git commit -m "${PREFIX}: ${MESSAGE}

Co-Authored-By: Claude <noreply@anthropic.com>"

# Now fetch and rebase onto latest develop
git fetch origin develop
git rebase origin/develop

# Switch to develop, fast-forward merge, and push
git checkout develop
git pull origin develop
git merge "$BRANCH"
git branch -d "$BRANCH"
git push origin develop
```

#### Step 3c: Return to orchestrator root

```bash
cd {orchestrator_root}
```

### Step 4: Verify

After all repos are processed:
```bash
pf git status --brief
```

All repos should show clean.

## Safety

- **NEVER commit directly to develop** (use branches)
- **Never force push**
- **Never commit secrets** (.env, credentials)
- **Abort if ALL repos are clean**
- **ALWAYS use `git -C {repo_path}` for subrepo operations**

## When to Use

| Use /chore | Use /pf-git cleanup |
|------------|------------------|
| Single logical change | Multiple unrelated changes |
| Quick fix or tweak | Need to organize into groups |
| One type of change | Mixed types requiring separation |

<related>
- `/pf-git cleanup` - Full ceremony for organizing multiple changes
- `/pf-git status` - Check status across all repos
</related>
