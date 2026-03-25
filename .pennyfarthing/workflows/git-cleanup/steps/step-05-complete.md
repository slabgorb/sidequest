# Step 5: Complete

<purpose>
Complete the cleanup workflow by providing final summary of work performed, guidance for post-cleanup tasks, and quick re-run instructions for future cleanup sessions.
</purpose>

<instructions>
1. Display summary showing groups committed, files organized, repos updated, and push status
2. List all commit hashes and messages by repo for reference
3. Provide guidance for handling any remaining changes (intentional skips, branch maintenance)
4. Show quick re-run commands for future cleanup sessions
5. Mark workflow as complete with confirmation message
</instructions>

<output>
Final summary showing:
- Groups committed count
- Files organized count
- Repos updated list
- Push status (yes/no)
- Complete list of commits by repo with hashes and messages
- Post-cleanup task recommendations
- Quick re-run instructions
- Completion confirmation message
</output>

## Summary

```
## Git Cleanup Complete ✅

### Session Summary
- Groups committed: {n}
- Files organized: {count}
- Repos updated: {list}
- Pushed to remote: {yes/no}

### Commits
{list of commit hashes and messages by repo}
```

## Post-Cleanup Tasks

### If Changes Remain

Intentionally skipped files can be:
- Committed in next cleanup session
- Added to .gitignore if generated
- Discarded with `git -C {repo} checkout -- {file}`

### Branch Maintenance

Run periodically to clean up merged branches:

```bash
# For each repo
git -C {repo_path} branch --merged develop | grep -v "develop\|main" | xargs -r git branch -d
```

## Quick Re-run

To run git-cleanup again:

```
/pf-git cleanup
```

Or for a quick status check across all repos:

```bash
pf git status
```

---

**Cleanup complete.** All repos are organized.
