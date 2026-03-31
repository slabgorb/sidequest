<gate name="wiring-check" model="haiku">

<purpose>
Enforce CLAUDE.md's "no half-wired features" rule mechanically.
Every new public export must have at least one non-test consumer.
Functions that are only called from tests are stubs, not features.

This gate runs after TEA writes tests (red phase) and after Reviewer
assessment. TEA must write a test that verifies the call site exists.
Reviewer must verify the wiring is complete before approving.

**No deferrals.** "Story X will wire this later" is not a valid dismissal.
CLAUDE.md: "No half-wired features — connect the full pipeline or don't
start." If your story produces exports with no production consumers,
either wire them in this story or rescope the story before starting.
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
If ANY export is unwired, the gate FAILS. No exceptions, no deferrals.

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

<no-deferral>
## Deferral Is Not a Valid Dismissal

Agents CANNOT dismiss unwired exports by citing a future story. The
following dismissal patterns are explicitly prohibited:

- "Story X-Y will wire this"
- "The integration story handles wiring"
- "This is foundational — consumers come in later stories"
- "Correct scope for this story; wiring deferred to X-Y"
- Any variant of "we'll wire it later"

CLAUDE.md is absolute:

> No stubs, no hacks, no "we'll fix it later" shortcuts.
> No half-wired features — connect the full pipeline or don't start.
> If something needs 5 connections, make 5 connections.
> Don't ship 3 and call it done.

**Why no deferrals:** Epic 7 stories 7-1 through 7-5 all deferred wiring
to story 7-9. Each dismissal was individually reasonable. The result was
~1,500 LOC of dead code — five fully-implemented, fully-tested modules
with zero production consumers. The gate fired correctly every time.
Every agent dismissed it by pointing at 7-9. The "deferral" pattern is
the scope-scoped equivalent of "we'll fix it later."

**What to do instead when the gate fails:**

1. **Wire it in this story.** Add the consumer call site. If the story
   is "BeliefState model," the story isn't done until something in the
   pipeline reads or mutates BeliefState during gameplay. The model
   AND its first consumer ship together.

2. **Rescope the story before starting.** If the story is genuinely
   just a data model with no consumer yet, the story is scoped wrong.
   Combine it with the first consumer story, or add the consumer call
   site to the ACs.

3. **Split differently.** Instead of "model" → "integration," split by
   vertical slice: each story delivers one behavior end-to-end (type +
   logic + call site + protocol message + test). Thinner stories that
   each touch more layers, rather than thick stories that only touch one.

**The gate has no operator override for this rule.** Unwired exports
are a hard fail. Restructure the work, don't negotiate with the gate.
</no-deferral>

</gate>
