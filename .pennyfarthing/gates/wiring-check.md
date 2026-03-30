<gate name="wiring-check" model="haiku">

<purpose>
Enforce CLAUDE.md's "no half-wired features" rule mechanically.
Every new public export must have at least one non-test consumer.
Functions that are only called from tests are stubs, not features.

This gate runs after TEA writes tests (red phase) and after Reviewer
assessment. TEA must write a test that verifies the call site exists.
Reviewer must verify the wiring is complete before approving.
</purpose>

<pass>
Run these checks on the diff (`git diff {base_branch}...HEAD`):

1. **Find new public exports:** Search the diff for newly added lines matching:
   - `pub fn ` (new public functions)
   - `pub use ` (new re-exports)
   - `pub struct ` (new public types)
   - `pub enum ` (new public enums)
   - `pub trait ` (new public traits)

   Extract the identifier name from each match.

2. **For each new export, find non-test consumers:**
   Search the entire codebase for each identifier:
   ```bash
   grep -r "{identifier}" --include="*.rs" --include="*.ts" --include="*.tsx" --include="*.py" \
     | grep -v "/tests/" | grep -v "_test.rs" | grep -v ".test." | grep -v "test_" | grep -v "spec."
   ```

   A "consumer" is any file that references the identifier AND is not:
   - A test file (in `/tests/`, `_test.rs`, `.test.ts`, `spec.`)
   - The definition file itself (where the export is declared)
   - A re-export file (e.g., `lib.rs` just doing `pub use`)

3. **Classify each export:**
   - **Wired:** Has at least one non-test, non-definition consumer → PASS
   - **Unwired:** Only referenced in tests and its own definition → FAIL
   - **Type-only:** Structs/enums used as parameters or return types of wired functions → PASS (transitive wiring)

4. **Story-level check:** Read the story title and description from the session file.
   If the title contains "wire", "connect", "integrate", "hook", or "plug in":
   - The session file's ACs MUST name a specific call site (file + function)
   - If no call site is named in ACs, emit a warning

If ALL exports are wired or type-only, return:

```yaml
GATE_RESULT:
  status: pass
  gate: wiring-check
  message: "All {N} new exports have non-test consumers"
  checks:
    - name: exports-wired
      status: pass
      detail: "{list of exports and their consumers}"
    - name: story-callsite
      status: pass | warn
      detail: "{whether wiring story names call site in ACs}"
```
</pass>

<fail>
If ANY export is unwired, report:

```yaml
GATE_RESULT:
  status: fail
  gate: wiring-check
  message: "Half-wired feature: {N} exports have no non-test consumers"
  checks:
    - name: exports-wired
      status: fail
      detail: "{list of unwired exports with zero consumers}"
    - name: story-callsite
      status: pass | fail
      detail: "{whether call site is named}"
  recovery:
    - "Wire {export} into {suggested_location based on story context}"
    - "Or: write a test that verifies {export} is called from the pipeline"
    - "CLAUDE.md rule: 'No half-wired features — connect the full pipeline or don't start.'"
```

**TEA application:** When this gate runs at TEA exit (red phase), TEA must
include at least one test that imports the function from the CONSUMER side
(e.g., sidequest-server), not just the PRODUCER side (e.g., sidequest-game).
If the function is supposed to be called from `dispatch_player_action()`,
a test should verify that call path exists.

**Reviewer application:** Reviewer must verify that new exports are actually
called from the pipeline described in the story. Library functions with no
consumers are stubs per CLAUDE.md rules.
</fail>

</gate>
