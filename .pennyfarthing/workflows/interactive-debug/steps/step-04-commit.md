# Step 4: Commit Changes

<step-meta>
number: 4
name: commit
gate: false
</step-meta>

<purpose>
Roll up all fixes into a single chore commit using the `/chore` skill.
</purpose>

<instructions>
1. REVIEW all changes before committing
2. Present summary of all changes (issues fixed, files changed)
3. Show git status output to verify no unintended changes
4. Ask user to confirm ready to commit
5. USE `/chore` skill to execute the commit
6. VERIFY no unintended changes are staged
7. Confirm commit succeeded with hash and message
8. Offer options to push, debug more, or exit
</instructions>

<output>
Provide:
- Summary: Issues fixed count, files changed count
- Changes table: File path and what was changed
- Git status before commit
- Commit hash
- Commit message used
- Post-commit status
- Next steps offered to user
</output>

## Purpose

Roll up all fixes into a single chore commit using the `/chore` skill.

## Mandatory Execution Rules

- REVIEW all changes before committing
- USE `/chore` skill for the commit
- VERIFY no unintended changes are staged

## Pre-Commit Review

Present summary of all changes:

```
## Debug Session Summary

**Issues Fixed:** [count]
**Files Changed:** [count]

### Changes

| File | Change |
|------|--------|
| `path/to/file.css` | Fixed overflow on main panel |
| `path/to/file.tsx` | Added missing click handler |
...

### Git Status
[show git status output]
```

Ask user to confirm:

> Ready to commit these changes as a chore fix?

## Commit Execution

**Use the `/chore` skill to create the commit.**

The chore skill will:
1. Stage the relevant files
2. Create a commit with appropriate message format
3. Handle the Co-Authored-By trailer

Suggested commit message format:

```
fix(ui): resolve visual bugs from debug session

- Fixed [issue 1 brief description]
- Fixed [issue 2 brief description]
...

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## Post-Commit

After successful commit:

```
## Debug Session Complete

**Commit:** [hash]
**Message:** [commit message]
**Files:** [count] files changed

The fixes have been committed. You can:
- Push to remote when ready
- Continue with another debug session
- Exit the workflow
```

## Workflow Complete

This concludes the interactive-debug workflow.

<switch tool="AskUserQuestion">
  <case value="commit" next="CONTINUE">
    Commit — Bundle into chore commit
  </case>
  <case value="review" next="LOOP">
    Review — Show me the diffs first
  </case>
  <case value="split" next="LOOP">
    Split — These should be separate commits
  </case>
  <case value="cancel" next="EXIT">
    Cancel — Don't commit yet
  </case>
  <case value="push" next="LOOP">
    Push — Push to remote branch
  </case>
  <case value="debug-more" next="LOOP">
    Debug more — Start another debug session (back to step 1)
  </case>
</switch>
