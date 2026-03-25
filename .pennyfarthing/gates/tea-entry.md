<gate name="tea-entry" model="haiku">

<purpose>
Entry gate for TEA phase. Forces a full audit of existing test files
before writing any new tests. Catches vacuous assertions, zero-assertion
tests, and missing edge cases that pre-date the current story.
</purpose>

<check name="test-audit">
Do not proceed with writing any new tests until you have read EVERY existing
test file and listed all issues found with file:line references.

For each test, check:

1. **Vacuous assertions** — assertions that always pass regardless of code behavior:
   - `assert!(x || true)` — the `|| true` makes it a no-op
   - `assert!(true)` or `assert_eq!(1, 1)` — proves nothing
   - Any assertion where the expected value is derived from the same code path as the actual

2. **Zero-assertion tests** — tests that run code but never assert anything:
   - `let _ = some_function()` with no subsequent assert
   - Tests that only check "doesn't panic" without verifying return values
   - Tests that call functions but discard results

3. **Missing edge cases** — error paths that lack test coverage:
   - Functions that return Result/Option but only happy-path is tested
   - Error variants that are never constructed in any test
   - Boundary conditions (empty input, max values, negative values)

4. **Tests that prove nothing** — setup without meaningful verification:
   - Tests that create objects but never exercise them
   - Tests where all assertions are on mock/fixture data, not on SUT output
</check>

<pass>
List every issue found, then return:

```yaml
GATE_RESULT:
  status: pass
  gate: tea-entry
  message: "Audit complete: {N} pre-existing test quality issues found"
  findings:
    - file: "{test_file}"
      line: {line}
      issue: "{description}"
      category: "vacuous-assertion | zero-assertion | missing-edge-case | proves-nothing"
```

Do not proceed with writing new tests until all findings above are addressed.
</pass>

<fail>
If no test files exist or tests cannot be read:

```yaml
GATE_RESULT:
  status: fail
  gate: tea-entry
  message: "Cannot audit: {reason}"
  recovery:
    - "{action to unblock}"
```
</fail>

</gate>
