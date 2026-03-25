<gate name="reviewer-preflight-check" model="haiku">

<purpose>
Composite gate for reviewer preflight. Extends tests-pass with code smell
detection and error boundary checks. The reviewer-preflight subagent runs
this gate before the Reviewer does critical analysis.
</purpose>

<ref gate="gates/tests-pass" />

<check name="no-debug-code">
No debug artifacts in changed files.
Search changed files (`git diff --name-only develop...HEAD`) for:
- `console.log` (not guarded by `process.env.NODE_ENV`)
- `dangerouslySetInnerHTML`
- `.skip(` (test skips)
- `TODO` / `FIXME`
Count by category. None found = pass.
</check>

<check name="error-boundaries">
UI components have error boundaries (UI repos only).
For React component files in diff, verify error boundary wrapping.
Skip for non-UI repos.
</check>

<pass>
Run all checks from `gates/tests-pass` (test-suite, working-tree, branch-status),
then run no-debug-code and error-boundaries.

If ALL pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: reviewer-preflight-check
  message: "Preflight clear: tests green, no smells, boundaries present"
  checks:
    - name: test-suite
      status: pass
      detail: "{passed}/{total} passing ({source: cached|fresh})"
    - name: working-tree
      status: pass
      detail: "No uncommitted changes"
    - name: branch-status
      status: pass
      detail: "On branch {branch}"
    - name: no-debug-code
      status: pass
      detail: "No debug patterns in {N} changed files"
    - name: error-boundaries
      status: pass
      detail: "Error boundaries present (or N/A for non-UI)"
```
</pass>

<fail>
If ANY check fails, report all results. Note: code smells are advisory (YELLOW)
rather than blocking (RED) — the Reviewer makes the final call.

```yaml
GATE_RESULT:
  status: fail
  gate: reviewer-preflight-check
  message: "Preflight issues: {summary}"
  checks:
    - name: test-suite
      status: pass | fail
      detail: "{test results or failure list}"
    - name: working-tree
      status: pass | fail
      detail: "{clean or list of uncommitted files}"
    - name: branch-status
      status: pass | fail
      detail: "{branch info}"
    - name: no-debug-code
      status: pass | fail
      detail: "{clean or smell counts by category}"
    - name: error-boundaries
      status: pass | fail
      detail: "{present, missing list, or N/A}"
  recovery:
    - "Fix failing tests before review"
    - "Commit or stash uncommitted changes"
    - "Remove debug code: {locations}"
    - "Add error boundaries to: {components}"
```
</fail>

</gate>
