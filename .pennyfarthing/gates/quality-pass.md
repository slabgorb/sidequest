<gate name="quality-pass" model="haiku">

<purpose>
Verify that all project quality gates pass locally — lint, type checks, and
tests — before handing off to the next phase. This gate wraps the check.py
quality runner to ensure the codebase is clean enough for Reviewer's time.
</purpose>

<pass>
Run the quality gate script for the repos listed in the session file:

```bash
source .venv/bin/activate && python3 .pennyfarthing/scripts/workflow/check.py
```

The script runs lint, type checks, and tests concurrently. Exit code 0 means
all checks passed.

If ALL checks pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: quality-pass
  message: "All quality gates passing — lint, typecheck, tests clean."
  checks:
    - name: lint
      status: pass
      detail: "Lint clean"
    - name: typecheck
      status: pass
      detail: "Type checks passing"
    - name: tests
      status: pass
      detail: "All tests passing"
```
</pass>

<fail>
If the script exits non-zero, parse its output to identify which checks failed.
The script prints `[PASS]` or `[FAIL]` for each check (Lint, Type Check, Tests).

Return with actionable recovery guidance:

```yaml
GATE_RESULT:
  status: fail
  gate: quality-pass
  message: "Quality gate failed: {summary of failures}"
  checks:
    - name: lint
      status: pass | fail
      detail: "{lint results or specific failures}"
    - name: typecheck
      status: pass | fail
      detail: "{typecheck results or specific errors}"
    - name: tests
      status: pass | fail
      detail: "{test results or failing test details}"
  recovery:
    - "Fix lint errors: run `npm run lint` to see details"
    - "Fix type errors: run `tsc --noEmit` to see details"
    - "Fix failing tests: run `pnpm test` to see details"
```
</fail>

</gate>
