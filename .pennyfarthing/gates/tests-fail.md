<gate name="tests-fail" model="haiku">

<purpose>
Verify tests are RED — failing tests exist that cover the acceptance
criteria. TEA has written tests but implementation hasn't started.
This gate runs after the TEA agent's red phase to confirm the codebase
has proper test coverage before Dev begins implementation.
</purpose>

<pass>
Run these checks and report results:

1. **Failing tests exist:** Run the project test suite for the repos listed in the session file.
   - For `pennyfarthing` repo: `cd pennyfarthing && python3 -m pytest` or `pnpm test`
   - Record: total tests, passed, failed, skipped
   - At least one test MUST be failing (RED state)

2. **Tests cover acceptance criteria:** Read the session file's Acceptance Criteria section.
   - Cross-reference test names/descriptions against each AC
   - Each AC should have at least one corresponding test

3. **Tests enforce project rules:** Read the TEA Assessment's `### Rule Coverage` section.
   - The section must exist and list applicable rules from the lang-review checklist
   - At least 3 rules should have corresponding tests (unless the story is too small for rule-relevant code)
   - If the section is missing or says "No rules applicable," verify by checking if the story creates types, enums, traits, or constructors — if it does, rules ARE applicable

4. **No vacuous tests:** Search test files for patterns that indicate vacuous assertions:
   - `let _ =` without a subsequent assertion on the same value
   - `assert!(true)` or `assert!(!false)`
   - `is_none()` assertions on values that are always None
   - Tests with no assertion macros at all

5. **Tests are committed:** Run `git status --porcelain` to check for uncommitted test files.
   - All test files should be committed to the branch
   - No uncommitted test files should exist

If ALL checks pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: tests-fail
  message: "{N} failing tests covering {M} acceptance criteria and {R} project rules. Tests committed."
  checks:
    - name: failing-tests
      status: pass
      detail: "{failed}/{total} tests failing (RED state confirmed)"
    - name: ac-coverage
      status: pass
      detail: "All {M} acceptance criteria have test coverage"
    - name: rule-coverage
      status: pass
      detail: "{R} project rules have test coverage per Rule Coverage section"
    - name: no-vacuous-tests
      status: pass
      detail: "No vacuous assertions found in test files"
    - name: tests-committed
      status: pass
      detail: "All test files committed to branch"
```
</pass>

<fail>
If ANY check fails, diagnose and report:

1. **No failing tests found:** TEA didn't write tests or tests are already passing.
   - This means implementation may have leaked into the red phase
   - Or tests are not properly asserting against unimplemented code

2. **Tests don't cover ACs:** Some acceptance criteria lack test coverage.
   - List which ACs are missing tests
   - TEA needs to add additional test cases

3. **Tests don't enforce project rules:** Rule Coverage section missing or insufficient.
   - If the story creates types/enums/traits/constructors, rules ARE applicable
   - TEA needs to add rule-enforcement tests

4. **Vacuous tests found:** Tests with no meaningful assertions.
   - List the specific vacuous patterns found (file:line)
   - TEA must fix or remove these before handoff

5. **Tests aren't committed:** Uncommitted test files exist.
   - List uncommitted test files
   - TEA needs to commit before handoff

Return with actionable recovery guidance:

```yaml
GATE_RESULT:
  status: fail
  gate: tests-fail
  message: "Gate failed: {summary of what's missing}"
  checks:
    - name: failing-tests
      status: pass | fail
      detail: "{description of test state}"
    - name: ac-coverage
      status: pass | fail
      detail: "{list of uncovered ACs}"
    - name: rule-coverage
      status: pass | fail
      detail: "{whether Rule Coverage section exists with applicable rules}"
    - name: no-vacuous-tests
      status: pass | fail
      detail: "{list of vacuous test patterns found}"
    - name: tests-committed
      status: pass | fail
      detail: "{list of uncommitted files}"
  recovery:
    - "Write failing tests for: {uncovered ACs}"
    - "Add Rule Coverage section to TEA Assessment listing applicable lang-review rules and their tests"
    - "Fix or remove vacuous tests: {file}:{line} — {pattern}"
    - "Commit test files: git add {files} && git commit"
```
</fail>

</gate>
