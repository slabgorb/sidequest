# Step 1: Analyze Current State

<purpose>
Gather the current git state across all configured repositories and build a complete picture of uncommitted changes across ALL repos.
</purpose>

<instructions>
1. Run the multi-repo git status script to show branch, staged/unstaged changes, and unpushed commits
2. For each repo with changes, gather detailed diffs and commit patterns
3. Check for active work sessions to understand context
4. Verify pre-flight checks (no merge conflicts, develop branches up to date, no secrets)
5. Present findings in structured format with analysis results by repo
</instructions>

<output>
Analysis results grouped by repo including:
- Current branch name
- Count of unpushed commits
- List of uncommitted changes with status (M/A/D/??)
- Any warnings or issues found
- Ready for user choice via switch prompt
</output>

## Objective

Build a complete picture of uncommitted changes across ALL repos defined in `.claude/project/pennyfarthing-settings.yaml`.

## Execution

### 1.1 Gather Git Status (All Repos)

**CRITICAL: Use the multi-repo script, not plain `git status`.**

```bash
pf git status
```

This shows branch, staged/unstaged changes, and unpushed commits for **all repos** defined in the project configuration.

### 1.2 For Each Repo with Changes

For repos with uncommitted changes, gather more detail:

```bash
# Show full diff for a specific repo
git -C {repo_path} diff

# Check the branch
git -C {repo_path} branch --show-current
```

### 1.3 Check Recent Commit Patterns

```bash
# In each repo with changes, check commit style
git -C {repo_path} log --oneline -5
```

### 1.4 Check Active Work Sessions

```bash
echo "=== Active Work Sessions ==="
ls -la .session/*.md 2>/dev/null || echo "No active sessions"
```

If sessions exist, read headers to understand what work is in progress.

## Pre-flight Checks

| Check | Status | Action if Failed |
|-------|--------|------------------|
| No merge conflicts | ☐ | Resolve conflicts first |
| Each repo's develop up to date | ☐ | `git -C {repo} pull origin develop` |
| No uncommitted secrets | ☐ | Add to .gitignore |

## Output Format

Present findings in this structure:

```
## Analysis Results

### Repo: {repo_name} (path: {repo_path})
Branch: {current_branch}
Unpushed: {count} commits

**Uncommitted Changes:**
- {file_path} ({status: M/A/D/??})
- ...

### Repo: {another_repo}
...

### Warnings
- {any issues found}
```

---


<switch tool="AskUserQuestion">
  <case value="analyze-a-specific-repo-in-more-detail" next="LOOP">
    Analyze a specific repo in more detail
  </case>
  <case value="continue-to-categorization" next="step-02-categorize">
    Continue to categorization
  </case>
</switch>
