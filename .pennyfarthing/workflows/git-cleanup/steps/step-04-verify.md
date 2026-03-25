# Step 4: Verify and Push

<purpose>
Verify that all changes have been properly committed across all repos, confirm no uncommitted changes remain (except intentionally skipped), review commit history, and push to remote.
</purpose>

<instructions>
1. Run multi-repo git status script to confirm clean working directories
2. Review commits in each repo that had changes using git log
3. Check for cleanup branches that should have been deleted (expected: none)
4. Generate summary report showing commits created by repo and final state
5. Verify any intentionally skipped files
6. Push develop to remote for each repo with new commits
7. Offer user choices to push, keep local, or review again
</instructions>

<output>
Git cleanup summary report including:
- Commits created table by repo with commit hashes and messages
- Final state for each repo (clean or files remaining)
- List of any remaining work or skipped files
- User choices presented via switch prompt
</output>

## Objective

1. Confirm all changes are properly committed across all repos
2. Verify no uncommitted changes remain (or only intentionally skipped)
3. Show commit history for review
4. Push to remote

## Verification

### 4.1 Final Git Status (All Repos)

```bash
pf git status
```

Expected: Clean working directory in all repos, or only intentionally skipped files.

### 4.2 Review Commits (Each Repo)

```bash
# For each repo that had changes
git -C {repo_path} log --oneline -5
```

### 4.3 Branch Cleanup Check

```bash
# For each repo
git -C {repo_path} branch | grep -v "develop\|main"
```

All cleanup branches should be deleted after merge.

## Summary Report

```
## Git Cleanup Summary

### Commits Created

**pennyfarthing:**
| Commit | Message |
|--------|---------|
| abc1234 | feat(core): replace todos REST polling with WebSocket |

**pennyfarthing-orchestrator:**
| Commit | Message |
|--------|---------|
| (none) | |

### Final State
- pennyfarthing: {clean / X files remaining}
- orchestrator: {clean / X files remaining}

### Remaining Work
{list any skipped files or deferred changes}
```

## Push

Push develop to remote for each repo with new commits:

```bash
git -C {repo_path} push origin develop
```

---

**[L]** Keep local (don't push yet)

<switch tool="AskUserQuestion">
  <case value="push-all-repos-to-remote" next="LOOP">
    Push all repos to remote
  </case>
  <case value="keep-local" next="LOOP">
    Keep local (don't push yet)
  </case>
  <case value="review-commits-again" next="LOOP">
    Review commits again
  </case>
</switch>
