---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-8: Fix pre-existing pyright error in reference_presenters.py present_magic rows reassignment

## Business Context

Epic 71 is the residue bucket for the 2026-05-27 `coyote_star` multiplayer
playtest findings that no other in-flight epic owns. Among the open work is a
band of pure type-hygiene cleanups (71-8, 71-9, 71-14) whose value is keeping the
`sidequest-server` pyright gate green so it stays a meaningful pre-commit/CI
signal rather than a wall of pre-existing noise that masks new regressions.

This story clears one such pre-existing error in
`reference_presenters.py::present_magic` — the player-facing renderer that turns
`magic.yaml` into reference cards/chips (added during the 2026-05-25 playtest fix
that stopped the generic renderer from dumping raw config). The error is a local
variable-name reuse that makes a single name carry two incompatible types in one
function. It is a real type-checker complaint with **no runtime symptom**: the
prose magic reference renders correctly today. The payoff is a clean type-check
surface, not a behavior change. No user (Sebastien/Jade's player-facing magic
reference included) sees any difference — this is dev-side correctness debt.

## Technical Guardrails

**File to modify (only one):**
`sidequest-server/sidequest/server/reference_presenters.py`, function
`present_magic(node: object, ctx: PresenterContext) -> str` (starts line 839).

**The exact error** (`uv run pyright sidequest/server/reference_presenters.py`):

```
reference_presenters.py:928:16 - error: Type "str" is not assignable to declared
type "list[str]"  "str" is not assignable to "list[str]" (reportAssignmentType)
```

**Root cause — variable-name reuse within one function scope.** Inside
`present_magic`, the name `rows` is bound twice:

- **Line ~928 (Hard Limits block):** `rows = "".join(... for k, v in limits.items())`
  — `rows` is a **`str`** (joined `<li>` HTML).
- **Line ~942 (Counters block):** `rows: list[str] = []` — an **annotated**
  declaration of `rows` as **`list[str]`**, then `.append(...)`-ed in a loop.

Pyright treats the annotated `list[str]` declaration as the variable's declared
type for the whole function, so the earlier `str` assignment at line 928 violates
it (`reportAssignmentType`). The two uses are unrelated logic (limits vs.
counters) that happen to share a name.

**Pattern to follow — rename, don't restructure.** The intended fix is to give
the two bindings distinct names (e.g. the Hard-Limits join → `limit_rows` /
`limits_html`, leaving the counters' `rows: list[str]` as-is, or vice versa).
Keep both blocks' logic, conditionals, and emitted HTML byte-for-byte identical;
only the local identifier(s) change. Update every in-scope reference to the
renamed local (the `parts.append(... {rows} ...)` line in the limits block).

**Constraints / what NOT to touch:**
- No behavioral change to magic-row rendering — the emitted HTML strings, the
  `escape()`/`_format_chip_label()`/`_chip_strip()` calls, and the suppression of
  dev-tuning keys all stay exactly as they are.
- Do not change the function signature, the wrapper-unwrap logic
  (`node.get("magic")`), or any other presenter in the file.
- This is a **cosmetic / type-only** change per the OTEL principle's "Not needed
  for" clause — **no OTEL span is required** (no subsystem decision changes).
- No new imports, no helper extraction, no refactor of the surrounding loops.

**Verification gate:** `cd sidequest-server && uv run pyright
sidequest/server/reference_presenters.py` must report `0 errors`; the full
`uv run pyright` count for this file drops by exactly one. `uv run ruff check .`
stays clean. Existing presenter tests still pass (`uv run pytest`).

## Scope Boundaries

**In scope:**
- The single pyright `reportAssignmentType` fix at
  `reference_presenters.py:928` inside `present_magic`, via renaming the reused
  `rows` local so the `str` binding and the `list[str]` binding no longer collide.

**Out of scope:**
- Any behavioral change to how magic rows (Hard Limits, Counters, Sources,
  Costs) render — output HTML must be byte-identical.
- The other type-hygiene stories (71-9 dice-overlay test migration, 71-14
  opening-POV test type-looseness + `visibility_sidecar` aliases).
- Any other pyright error elsewhere in the codebase or other presenters.
- New tests for the renderer (existing coverage suffices; this is a no-behavior
  rename).
- OTEL instrumentation (cosmetic change, explicitly exempt).

## AC Context

The terse story title expands to these testable conditions:

1. **The named error is gone.** `cd sidequest-server && uv run pyright
   sidequest/server/reference_presenters.py 2>&1` no longer reports
   `928:16 - error: ... reportAssignmentType` (or any error). Expected output:
   `0 errors, 0 warnings`.
   - *Edge case:* the fix must not introduce a *new* pyright error elsewhere in
     `present_magic` (e.g. a renamed local that is referenced under its old name).
     Verify by checking the whole-file count goes from 1 → 0, not 1 → 1.

2. **No behavioral change to magic-row rendering.** The Hard-Limits `<section
   class="ref-allowed"><h3>Hard Limits</h3><ul>...</ul></section>` and the
   Counters output are emitted with identical markup for the same `magic.yaml`
   input.
   - *How a test verifies:* run the existing reference-presenter test suite
     (`uv run pytest -k reference` / the presenter tests under `tests/server/`)
     and confirm they pass unchanged. A `git diff` of the function should show
     only identifier renames, no string-literal or control-flow edits.
   - *Edge cases the rename must preserve:* `hard_limits` as a populated `dict`
     (the line-928 path), `hard_limits` as a `list[str]` (the `elif` chip-strip
     path), and the unrelated `counter` `list[dict|str]` path that owns the
     `rows: list[str]` declaration — all three must behave exactly as before.

3. **Repo gates stay green.** `uv run ruff check .` reports no new findings;
   `uv run pyright` (whole repo) error count decreases by one with no new errors.

## Assumptions

- **Technical:** The error is a pure local-variable name collision; no callers of
  `present_magic` depend on internal variable names (they cannot — locals are not
  observable), so a rename is safe and self-contained.
- **Technical:** Pyright's reported line numbers (`928`, and the `rows: list[str]`
  declaration ~`942`) match the current `reference_presenters.py`; if the file
  has drifted, re-run `uv run pyright sidequest/server/reference_presenters.py`
  to relocate the exact lines before editing.
- **Dependency:** No other open epic-71 story (71-9, 71-14) touches this file, so
  this can land independently in any order.
- **Domain:** Existing presenter test coverage exercises the Hard-Limits and
  Counters paths sufficiently to catch an accidental behavior change from the
  rename; if it does not, the `git diff` identifier-only check is the backstop.

If any assumption proves wrong (e.g. the rename surfaces a second latent error,
or the line has moved to a different construct), log a Design Deviation and notify
the SM rather than expanding scope into a broader presenter refactor.
