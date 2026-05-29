---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-14: Test-file pyright cleanup for 71-5 — +13 type-looseness in opening-POV test files + 2 visibility_sidecar alias false-positives (pyright-ignore)

## Business Context

Story 71-5 ("POV-swap the driving player's own MP opening card", done — commit
`22dbb25`) and its sibling 71-13 (`emit_event` opening fanout) closed two of the
highest-friction `coyote_star` MP playtest defects: the driving player's own
opening narration now POV-swaps to second person and routes through `emit_event`
for uniform per-recipient POV + perception fanout. Those fixes shipped with new
test files that carry pyright type-looseness — untyped fixtures, `SimpleNamespace`
stand-ins, and `Optional` member access on values pyright cannot narrow.

Per the epic's "type hygiene" track (71-8/71-9/71-14), the residue must be cleared
so `pyright` stays green and a real type regression in this subsystem is not lost
in pre-existing noise. This is a pure type-checker debt story: no behavior, no
production code, no playtest-facing change. It serves Keith-the-dev (clean
type-check gate), not any player-facing surface — there is no math to expose, no
narration to verify.

## Technical Guardrails

**Key files to modify (all test files in `sidequest-server`):**

- `tests/server/test_opening_pov_swap_71_5.py` — the primary 71-5 test file
  (15 pyright errors).
- `tests/server/test_opening_emit_event_71_13.py` — the 71-13 sibling that
  exercises the same opening fanout (multiple errors, incl. 6 `visibility_sidecar`).

The 71-5-era helper `tests/server/test_pov_swap_opening_helper_71_5.py` referenced
in early triage **no longer exists on disk** — do not recreate it. The "+13"
count is approximate; treat the live `pyright tests` output as authority.

**Error categories observed (live `uv run pyright tests`):**

1. **`reportOptionalMemberAccess`** — accessing `.mode`, `.player_id`,
   `.snapshot`, `.repository`, `._room`, `.builder`, `.broadcast` on values pyright
   types as `None` (e.g. `directive.player_id` where `directive` is `X | None`).
   Fix with a local assert/narrowing or precise annotation — not by loosening
   production types.
2. **`reportCallIssue` / `reportArgumentType`** — `CharacterCreationMessage`
   passed where `GameMessage` is expected in `handle_message`; `str` passed where
   psycopg `Template` query is expected on `.execute(...)`; `SimpleNamespace`
   fixtures passed for `_SessionData`/`GameSnapshot`/`GenrePack`. These are test
   fixture/type-looseness issues — narrow with `cast(...)` or properly typed
   fixtures local to the test.
3. **`add_span_processor` on `TracerProvider`** — OTEL provider attribute access
   pyright cannot resolve on the abstract type; narrow via `cast`.

**The 2 visibility_sidecar alias false-positives (`# pyright: ignore`):**

`NarrationPayload` (and siblings) in `sidequest/protocol/messages.py` declare
`visibility_sidecar: dict | None = Field(default=None, alias="_visibility")`.
Pyright reports `No parameter named "visibility_sidecar" (reportCallIssue)` at
every keyword construction because it binds to the wire alias `_visibility`. This
is a **genuine false positive** (the model is `populate_by_name`): suppress with
`# pyright: ignore[reportCallIssue]` at the two canonical sites — do **not** rewrite
calls to use `_visibility=` (that would couple tests to the wire name). Live count
of `visibility_sidecar=` call sites is higher than two across the opening tests;
apply the ignore at the construction sites that pyright flags, matching the AC's
"alias false-positive" intent.

**Patterns / what NOT to touch:**

- No edits to `sidequest/protocol/messages.py` or any production module — the
  alias is correct as authored; the false positive is pyright's, not the model's.
- No behavioral change to any test — assertions and what they verify stay
  identical. Type fixes only.
- Do not add a blanket file-level `# pyright: basic`/`ignore` to mute everything;
  target each error so a future real regression still surfaces.
- Do not touch the other type-hygiene stories' files (71-8
  `reference_presenters.py`, 71-9 dice-overlay wiring test).

## Scope Boundaries

**In scope:**

- Resolve the ~13 type-looseness pyright errors in the 71-5/71-13 opening-POV test
  files (`tests/server/test_opening_pov_swap_71_5.py`,
  `tests/server/test_opening_emit_event_71_13.py`) via local narrowing, `cast`,
  precise fixture annotations, or asserts — test code only.
- Add `# pyright: ignore[reportCallIssue]` for the `visibility_sidecar` alias
  false-positives at the flagged construction sites.
- Leave `uv run pyright` clean of these specific errors with all tests still
  passing (`uv run pytest tests/server/test_opening_pov_swap_71_5.py
  tests/server/test_opening_emit_event_71_13.py`).

**Out of scope:**

- Any production-code type changes (no edits to `messages.py`, the opening
  resolver, websocket handlers, or telemetry spans).
- Any behavioral or assertion change to the tests.
- The unrelated pyright errors in other test files surfaced by the same run
  (`test_opening_loud_fail.py`, `test_chargen_dispatch.py`,
  `test_genre/test_models/*`, `test_adr105_b3_*`, `test_messages.py`,
  `test_merged_mp_emitter_projection.py`) — those belong to 71-8/71-9 or other
  epics, not 71-14.
- New OTEL spans — this is a test-only hygiene story touching no subsystem
  decision, so the OTEL-on-every-fix principle does not apply.

## AC Context

**AC1 — Type-looseness in the opening-POV test files is resolved.**
For each error pyright reports in `test_opening_pov_swap_71_5.py` and
`test_opening_emit_event_71_13.py` (categories: `reportOptionalMemberAccess`,
`reportCallIssue`, `reportArgumentType`), the error no longer appears.
Verification: `uv run pyright tests/server/test_opening_pov_swap_71_5.py
tests/server/test_opening_emit_event_71_13.py` reports `0 errors` (excluding the
two intentionally-ignored alias lines). Edge case: narrowing must not change which
branch the test exercises — e.g. an `assert directive is not None` must be true at
runtime, not mask a real `None`.

**AC2 — visibility_sidecar alias false-positives are suppressed, not rewritten.**
Each flagged `visibility_sidecar=` construction carries
`# pyright: ignore[reportCallIssue]` with the scoped rule name (not a bare
`# pyright: ignore`). Verification: grep the two files for `pyright: ignore` and
confirm each is rule-scoped and sits on a `visibility_sidecar=` line; pyright no
longer reports `No parameter named "visibility_sidecar"`. Edge case: do not
suppress a `visibility_sidecar` attribute-*access* error (e.g.
`test_merged_mp_emitter_projection.py:467`) under this story — that file is out of
scope.

**AC3 — No behavioral or production change.**
`git diff` touches only the two named test files; `git diff --stat -- sidequest/`
is empty. All tests in the two files still pass under `uv run pytest`. The
type-check gate (`just server-lint` / `uv run pyright`) is no noisier than before
for these files.

## Assumptions

- The "+13" count and "2 visibility_sidecar" framing are the triage-time
  estimate; the live `uv run pyright tests` output is authority. The actual
  `visibility_sidecar=` call-site count in the opening tests is higher than two —
  apply the ignore to every flagged site, matching the AC's "alias false-positive"
  intent rather than a literal count.
- The early-triage helper file `test_pov_swap_opening_helper_71_5.py` was folded
  into / superseded by `test_opening_pov_swap_71_5.py` and is gone; scope tracks
  the files that exist now.
- `visibility_sidecar` remains an aliased pydantic field (`alias="_visibility"`)
  in production; the false positive persists until a pyright/pydantic-plugin
  config change addresses aliases globally — out of scope here. If that config
  is added instead, the `# pyright: ignore` comments become removable (a future
  cleanup, not this story).
- If any "type-looseness" error turns out to flag a real bug in test logic (not
  just a missing annotation), stop and log a Design Deviation to SM rather than
  papering over it with a cast.
