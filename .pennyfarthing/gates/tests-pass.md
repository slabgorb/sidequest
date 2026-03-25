<gate name="tests-pass" model="haiku">

<purpose>
Verify that all tests pass and the working tree is clean before handing off
to the reviewer. This gate runs after the Dev agent's implementation phase
to confirm the codebase is in a GREEN state.
</purpose>

<pass>
Run these checks and report results:

1. **Test suite:** Run the project test suite for the repos listed in the session file.
   - For `pennyfarthing` repo: `cd pennyfarthing && pnpm test`
   - For `orchestrator` repo: tests in the orchestrator root if applicable
   - Record: total tests, passed, failed, skipped

2. **Working tree:** Run `git status --porcelain` in each repo listed in session `**Repos:**`.
   - Verify no uncommitted or untracked files (empty output = clean)

3. **Branch status:** Run `git branch --show-current` and `git log --oneline -1`.
   - Confirm on the expected feature branch from session `**Branch:**`

If ALL checks pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: tests-pass
  message: "All {N} tests passing. Working tree clean. Branch: {branch}"
  checks:
    - name: test-suite
      status: pass
      detail: "{passed}/{total} tests passing ({skipped} skipped)"
    - name: working-tree
      status: pass
      detail: "No uncommitted changes"
    - name: branch-status
      status: pass
      detail: "On branch {branch}, HEAD at {short-sha}"
```
</pass>

<fail>
If ANY check fails, diagnose and report:

1. **Failing tests:** List each failing test file and line number.
   - Run tests with verbose output to capture failure details.
   - Group failures by file.

2. **Dirty working tree:** List uncommitted and untracked files.
   - Run `git status --porcelain` and report each file with its status code.

3. **Wrong branch:** Report actual vs expected branch name.

Return with actionable recovery guidance:

```yaml
GATE_RESULT:
  status: fail
  gate: tests-pass
  message: "Gate failed: {summary of failures}"
  checks:
    - name: test-suite
      status: pass | fail
      detail: "{description of test results or failures}"
    - name: working-tree
      status: pass | fail
      detail: "{list of uncommitted files, or 'clean'}"
    - name: branch-status
      status: pass | fail
      detail: "{branch info or mismatch details}"
  recovery:
    - "Fix failing tests in: {file1}, {file2}"
    - "Commit or stash uncommitted changes before handoff"
    - "Switch to correct branch: git checkout {expected-branch}"
```
</fail>

</gate>
