# Step 3: Execute Commits

<purpose>
Execute the approved change groupings by creating branches, staging and committing files, and merging to develop in each affected repo. Process groups sequentially without stashing changes.
</purpose>

<instructions>
1. For each approved group, create branches in affected repos following naming conventions
2. Stage only the files belonging to the current group (never commit directly to develop)
3. Show diffs for verification before committing
4. Commit with proper message format including Co-Authored-By line
5. Merge branches to develop and delete local branches after merge
6. For tracked groups, create Jira story, update branch with story ID, push and create PR
7. Report progress after each group with status table
8. Handle errors appropriately (hook rejection, merge conflicts, test failures)
</instructions>

<output>
Execution progress report showing:
- Status table with Group | Repo | Status | Branch
- Commits created count
- Branches merged count
- List of repos updated
- Confirmation ready to verify and push
- User choices presented via switch prompt
</output>

## Objective

Execute the approved change groupings using a simple branch workflow. No stashing required.

## Approach: One Group at a Time

Process groups sequentially. For each group:
1. Create branch in each affected repo
2. Stage and commit the group's files
3. Merge to develop
4. Move to next group

## Critical Rules

- **NEVER commit directly to develop** - Branch protection hooks will reject it
- **NEVER force push** - Data loss is not recoverable
- **NEVER commit secrets** - Check for .env, credentials, API keys

## Execution

### For Each Group

#### 3.1 Create Branch (in each affected repo)

```bash
# For each repo that has changes in this group
git -C {repo_path} checkout develop
git -C {repo_path} pull origin develop
git -C {repo_path} checkout -b {branch_name}
```

**Branch naming:**
- `feat/description` for features
- `fix/description` for bug fixes
- `chore/description` for maintenance
- `docs/description` for documentation

#### 3.2 Stage Files for This Group

```bash
# Stage only files belonging to this group
git -C {repo_path} add {file1} {file2} ...
```

#### 3.3 Show Diff for Verification

```bash
# Show what will be committed
git -C {repo_path} diff --cached --stat
```

#### 3.4 Commit

```bash
git -C {repo_path} commit -m "$(cat <<'EOF'
{type}({scope}): {description}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

#### 3.5 Merge to Develop

```bash
# Switch to develop
git -C {repo_path} checkout develop

# Merge the branch (fast-forward)
git -C {repo_path} merge {branch_name}

# Delete local branch
git -C {repo_path} branch -d {branch_name}
```

#### 3.6 Repeat for Next Group

Move to the next group and repeat steps 3.1-3.5.

## Multi-Repo Groups

When a group spans multiple repos, execute steps 3.1-3.5 in **each repo** before moving to the next group:

```
Group: "Todos WebSocket"
  1. pennyfarthing: checkout -b feat/todos-websocket
  2. pennyfarthing: add main.ts websocket.ts useTodos.ts
  3. pennyfarthing: commit
  4. pennyfarthing: merge to develop

  (If orchestrator also had changes in this group, repeat there)

  ✓ Group complete, move to next group
```

## Tracked Groups (Jira + PR Path)

For groups marked for Jira tracking:

#### Create Jira Story

```bash
JIRA_KEY=$(jira issue create \
  --project <PROJECT> \
  --type Story \
  --summary "{title}" \
  --body "{description}" \
  --label pennyfarthing \
  --no-input 2>&1 | grep -oE '<PROJECT>-[0-9]+' | head -1)

echo "Created: $JIRA_KEY"
```

#### Use Jira Key in Branch

```bash
BRANCH="feat/${JIRA_KEY}-${slug}"
git -C {repo_path} checkout -b "$BRANCH"
```

#### Push and Create PR

Format the PR title using the project's `pr_title_format` setting:
```bash
PR_TITLE=$(source .venv/bin/activate && python -c "
from pf.git.repos import format_pr_title
print(format_pr_title(jira_key='${JIRA_KEY}', title='{title}'))
")
```

```bash
git -C {repo_path} push -u origin "$BRANCH"

gh pr create \
  --repo {repo_owner}/{repo_name} \
  --title "$PR_TITLE" \
  --body "## Summary
{description}

## Jira
[${JIRA_KEY}](https://your-jira.atlassian.net/browse/${JIRA_KEY})

## Test plan
- [x] Changes verified locally"
```

#### Merge PR

```bash
gh pr merge --squash --delete-branch
git -C {repo_path} checkout develop
git -C {repo_path} pull origin develop
```

## Progress Tracking

Report progress after each group:

```
## Execution Progress

| Group | Repo | Status | Branch |
|-------|------|--------|--------|
| Sprint cleanup | orchestrator | ✅ Done | chore/sprint-update |
| Todos WebSocket | pennyfarthing | ✅ Done | feat/todos-websocket |
| Config changes | both | ⏳ In Progress | chore/config-update |
```

## Error Handling

If a commit fails:
1. **Hook rejection**: Check commit message format, fix and retry
2. **Merge conflict**: Report to user, resolve manually
3. **Test failure**: Report which tests failed, decide whether to proceed

## Output

After all groups processed:

```
## Execution Complete

Commits created: {n}
Branches merged: {n}
Repos updated: {list}

Ready to verify and push?
```

---


<!-- GATE -->

<switch tool="AskUserQuestion">
  <case value="abort-current-group" next="EXIT">
    Abort current group (leave those changes uncommitted)
  </case>
  <case value="continue-to-verification" next="step-04-verify">
    Continue to verification
  </case>
</switch>
