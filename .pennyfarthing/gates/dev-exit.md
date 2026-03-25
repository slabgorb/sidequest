<gate name="dev-exit" model="haiku">

<purpose>
Composite gate for Dev handoff. Extends tests-pass with a debug code scan.
Runs after the Dev agent's implementation phase before review.
</purpose>

<ref gate="gates/tests-pass" />

<check name="no-debug-code">
No console.log, debugger statements, or .only() in changed files.
Search changed files (`git diff --name-only develop...HEAD`) for:
- `console.log` (not in DEV guard)
- `debugger`
- `.only(`
None found = pass.
</check>

<pass>
Run all checks from `gates/tests-pass` (test-suite, working-tree, branch-status),
then run the no-debug-code check.

If ALL pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: dev-exit
  message: "All {N} tests passing. Tree clean. No debug code. Branch: {branch}"
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
    - name: no-debug-code
      status: pass
      detail: "No debug patterns found in changed files"
```
</pass>

<fail>
If ANY check fails, run all remaining checks (don't short-circuit) and return:

```yaml
GATE_RESULT:
  status: fail
  gate: dev-exit
  message: "Gate failed: {summary of failures}"
  checks:
    - name: test-suite
      status: pass | fail
      detail: "{test results or failure list}"
    - name: working-tree
      status: pass | fail
      detail: "{clean or list of uncommitted files}"
    - name: branch-status
      status: pass | fail
      detail: "{branch match or mismatch details}"
    - name: no-debug-code
      status: pass | fail
      detail: "{clean or list of debug code locations}"
  recovery:
    - "Fix failing tests in: {file1}, {file2}"
    - "Commit or stash uncommitted changes"
    - "Remove debug code: {file:line patterns}"
    - "Switch to correct branch: git checkout {expected-branch}"
```
</fail>

</gate>
