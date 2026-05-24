---
parent: context-epic-61.md
workflow: tdd
---

# Story 61-11: Scene-gate `genre_chargen` / `genre_extraction` / `genre_keeper_monologue` (drop from STABLE_SECTION_NAMES)

## Business Context

ADR-112 / Story 57-3 promoted four genre-prose sections — `genre_extraction`,
`genre_keeper_monologue`, `genre_town`, `genre_chargen` — into
`STABLE_SECTION_NAMES` so they would land in the cache-marked `system_blocks[0]`
and survive the prefix-recomputation that the runaway-Valley incident exposed
(epic 61 §Overview; user memory `project_runaway_valley_block_2026_05_23`). The
trade was deliberate: three of the four sections are scene-typed (only relevant
during a specific moment of play) but the cache-thrash cost of conditional
registration was assumed to exceed the per-turn carry cost.

This story revisits that trade for three of the four. The ~150–200 token carry
per section adds up: on a neutral "you walk into the tavern" turn the prompt
ships `gp.chargen` (Brecca Half-Hand's loadout intake), `gp.extraction` (the
party hauling treasure toward the exit), and `gp.keeper_monologue` (the Keeper
announcing from the walls) into the cache root even though none of those
scenes is happening. The thrash argument ADR-112 used to defer
`genre_combat_voice` / `genre_chase_voice` (encounter-boundary churn) does
not symmetrically apply: `gp.chargen` fires **once per session** (opening
turn only — single cache miss, amortized by turn 5); `gp.extraction` and
`gp.keeper_monologue` fire on **rare scripted beats**.

Customer-facing impact: zero. Narrator output is unchanged on turns where the
scene predicate is true; on neutral turns the omitted prose was already
irrelevant. This is a cache-vs-relevance correction, not a feature.

## Technical Guardrails

**From epic 61 architecture:** every change to narrator prompt construction
must preserve ADR-098 §Decision ("prompt size is bounded by section
selection") and ADR-110 §Phase B (allowlist DROP discipline). 61-11 does
not touch snapshot fields or the dump-allowlist; the rules are referenced
only to confirm this story does NOT reopen them.

**From SOUL.md:** "Cost Scales with Drama." Spending ~450 tok/turn on
out-of-scope scene prose is exactly the anti-pattern the principle names —
quiet walk through town should be cheap.

**No new flags rule (SM scope lock):** "Predicates should be derived from
existing TurnContext / GameState fields — no new state flags introduced."
This rule is enforceable for `genre_chargen`. **It is NOT enforceable for
`genre_extraction` or `genre_keeper_monologue`.** See "Predicate Audit"
below — the design as-written depends on existing signals that simply do
not exist for two of the three sections. The architect-recommended resolution
is a **scope reduction** logged as a Design Deviation before TEA writes any
test.

### Files in scope (server repo, paths under `sidequest-server/`)

| File | Change |
|------|--------|
| `sidequest/agents/prompt_framework/bucket.py:50-53` | REMOVE three names from `STABLE_SECTION_NAMES` (see scope reduction below for which) |
| `sidequest/agents/orchestrator.py:1558-1604` | Add scene-predicate gating to existing `if gp.<field>:` blocks (extraction at 1558-1567, keeper_monologue at 1571-1580, chargen at 1595-1604). `genre_town` at 1583-1592 is OUT OF SCOPE (story body explicitly defers) |
| `tests/agents/test_prompt_framework/test_bucket.py` | Unit assertions: each demoted name maps to `SectionBucket.User`; `genre_town` stays on STABLE |
| `tests/agents/` (new file: `test_61_11_scene_gated_genre_sections.py` recommended) | Fixture-driven behavior tests: predicate-true `TurnContext` → section lands in `user_message`; predicate-false → section absent |
| `docs/adr/0112-genre-prose-stable-cache-promotion.md` (orchestrator repo, separate commit on `main`) | Amendment block recording partial reversal and predicate-gating decision. **Doc deliverable only — not a code AC; flag in review-phase Delivery Findings, do not block green on it.** |

### Predicate Audit (load-bearing — informs scope reduction)

The SM assessment names three predicates: `chargen_active`, `extraction_active`,
`keeper_speaking`. I audited `TurnContext` (defined at
`sidequest/agents/orchestrator.py:539-876`) and the populating function
`_build_turn_context` (`sidequest/server/session_helpers.py:737+`) plus the
session-room state machine (`sidequest/server/session_room.py:85-111`,
`LobbyState` enum + per-seat tracking). Findings:

#### `chargen_active` — predicate exists ✅

`TurnContext.opening_directive: str | None` (field at
`orchestrator.py:647`) is set by
`_populate_opening_directive_on_chargen_complete()`
(`websocket_session_handler.py:181-346`) at the chargen-confirmation site, and
consumed on the post-chargen opening turn (the FIRST narration turn after
chargen commits). The session handler clears it after the opening turn fires.

`gp.chargen` prose ("describe what the character is carrying — their weapon,
their pack contents, how much coin they have. The player should know their
loadout before they step into the dark") is **exactly the prose the opening
turn needs to render**. After the opening turn, the chargen scene is over;
the prose is wasted carry.

**Predicate (in `orchestrator.py` registration block):**
```python
if gp.chargen and context.opening_directive is not None:
    registry.register_section(...)
```

Alternative formulation: `context.turn_number == 0`. Both are valid (the
opening turn IS turn 0 by construction — `is_opening_turn=True` path at
`websocket_session_handler.py:3115`), but `opening_directive is not None`
is **semantically tighter** (it specifically marks "this is the post-chargen
handoff turn" rather than "this is the first turn for any reason"). TEA
should test against the `opening_directive` formulation; Dev implements
against it.

#### `extraction_active` — predicate does NOT exist ❌

There is no `TurnContext` field, `GameSnapshot` field, encounter type, or
session-room state that flips when "the party is heading for the exit with
treasure." Grep results from full server tree:

- `extraction_phase: "true"` in `caverns_and_claudes/rules.yaml:24` is a
  **static genre-config flag** (declares "this genre has extraction
  mechanics") — not a runtime activation signal.
- No `escape_attempt`, `exiting_dungeon`, `leaving_with_loot`,
  `extraction_active`, or similar field exists in any production module
  outside test fixtures.
- The dungeon module (`sidequest/dungeon/`) has no "approaching exit" state;
  movement is room-graph traversal without a "headed for the surface" flag.
- The confrontation taxonomy (`pack.rules.confrontations`) declares categories
  like `combat`/`movement`/`social` but no `extraction` category appears in
  any live `rules.yaml` (the genre says "extraction is a phase" in flavor,
  not in mechanics).

**Honest scope statement:** there is no existing signal to gate
`genre_extraction` on. The SM-forbidden alternative ("invent a flag") would
require populating a new `TurnContext.extraction_active` from new wiring at
the session handler — a multi-site change well outside a 2-pt story.

#### `keeper_speaking` — predicate does NOT exist ❌

Same finding. The Keeper is a pure narrative construct in
`caverns_and_claudes`: "The Keeper speaks. All other sound stops. The voice
comes from the walls..." Grep finds no `keeper_speaking`, `keeper_active`,
or any state field that flips when the Keeper announces. The `keeper_*`
custom rules in `rules.yaml` (`keeper_awareness: "true"`) are static config
flags, not runtime signals. There is no engine model of "the Keeper is
currently speaking on this turn"; the narrator decides whether the Keeper
speaks based on the scene, NOT the other way around.

#### Resolution: scope reduction

The story scope as written depends on three predicates; only one exists.
Three architect-considered options:

**(A) Scope-reduce to `genre_chargen` only — RECOMMENDED.** Demote
`genre_chargen` from STABLE, gate it on `opening_directive is not None`.
Leave `genre_extraction` and `genre_keeper_monologue` on STABLE. ADR-112
amendment notes the partial-reversal AND explicitly defers extraction +
keeper_monologue alongside `combat_voice`/`chase_voice`/`town` to a future
story that builds runtime signals (or to ADR-113's intent-router work, which
would attach scene prose to tools rather than to the prompt root).
Token savings: ~150 tok/turn after the opening turn. One cache miss at
turn 0.

**(B) Demote all three, register `chargen` conditionally, defer
`extraction` + `keeper_monologue` registration entirely.** This drops
`genre_extraction` and `genre_keeper_monologue` from EVERY turn (no
predicate fires them), losing the prose entirely. The genre author would
expect those sections to fire when the scene happens — silently dropping
them violates the genre-truth contract. Rejected.

**(C) Invent flags.** SM forbade this in the assessment.

**(D) Cancel and re-plan.** Send back to PM. Heaviest ceremony.

**Architect recommendation: (A).** It honors the no-new-flags rule, achieves
the cache-vs-relevance correction for the most-cacheable section
(`chargen` is once-per-session — perfect amortization), and keeps the
genre-truth contract intact for the other two. The ADR-112 amendment makes
the partial-reversal LOUD (per memory `feedback_adr_priority_current_over_history`)
and points the next architect at the runtime-signal gap that blocks the
remaining two demotions.

**TEA must log this as a Design Deviation BEFORE writing tests** (see
"Design Deviation pre-log" below), and SM/user should confirm option (A)
before TEA proceeds. If the user prefers a different option, the test
surface changes substantially.

### Patterns to follow

- **No silent fallbacks** (CLAUDE.md, memory `feedback_no_burying_bombs`).
  If the chargen predicate is true but `gp.chargen` is empty, do not
  silently substitute a default. Skip the section (zero-byte leak, matches
  the existing `if gp.chargen:` outer guard).
- **No source-text wiring tests** (server CLAUDE.md). Behavior tests must
  drive `build_narrator_prompt` against a synthetic `TurnContext` + genre
  pack and assert on the typed `user_message` / `system_prompt` output —
  NOT grep production source.
- **Wiring tests required** (server CLAUDE.md "Every Test Suite Needs a
  Wiring Test"). At least one test must call `build_narrator_prompt` end
  to end (real orchestrator function, not a unit on `bucket.py` in
  isolation) and assert that the predicate-gated registration block fires
  the way the bucket assignment expects. The bucket test alone would pass
  while the orchestrator stays broken — the wiring test catches that.
- **ADR-112 amendment authoring** is a doc deliverable (orchestrator
  `docs/adr/0112-*.md` on `main`, NOT on the server feature branch).
  Tech Writer surface; do not block green on it. Flag in review-phase
  Delivery Findings.

### Dependencies / sequencing

- **Independent of 61-9** (SDK narrator commitment, complete on `develop`)
  — different file surface.
- **Independent of 61-10** (six byte-static sections to System bucket) —
  61-10 also touches `prompt_framework/bucket.py:50-53` but in the opposite
  direction (adding names); merge order is irrelevant because the diffs
  don't conflict (different names) and the test surfaces don't overlap.
  If 61-10 lands first, this story's diff drops three names from a longer
  list. If 61-11 lands first, 61-10 adds to the shorter list.
- **Independent of 61-12** (50% prose compaction, sequenced after 61-9).
  No coordination.

## Scope Boundaries

**In scope (option A — RECOMMENDED):**

- Drop `genre_chargen` from `STABLE_SECTION_NAMES` at
  `sidequest/agents/prompt_framework/bucket.py:50-53`.
- Gate the `gp.chargen` registration block at
  `sidequest/agents/orchestrator.py:1595-1604` on
  `context.opening_directive is not None`.
- Add a unit test asserting `default_bucket_for_section("genre_chargen") ==
  SectionBucket.User` (and that `genre_extraction`, `genre_keeper_monologue`,
  `genre_town` still map to `SectionBucket.System` — preserve the STABLE
  invariant for the un-demoted three).
- Add fixture-driven behavior tests for `build_narrator_prompt`:
  predicate-true (turn 0, `opening_directive` set) → `genre_chargen` lands
  in `user_message`; predicate-false (turn 5, `opening_directive=None`) →
  section absent from BOTH `system_prompt` AND `user_message`.
- Verify the existing test suite still passes — particularly any test that
  was relying on `genre_chargen` always appearing in `system_prompt`.
- ADR-112 amendment in orchestrator (separate commit on `main`).

**Out of scope (option A):**

- `genre_extraction` and `genre_keeper_monologue` demotion. Deferred to a
  follow-up story that either (a) builds runtime signals (`extraction_active`,
  `keeper_speaking`) or (b) migrates the prose to tool-attached scope under
  ADR-113. Document this in the ADR-112 amendment so the deferral is
  visible to the next architect.
- `genre_town` demotion (story body explicitly defers; "frequent enough
  that profiling needed before moving").
- `genre_combat_voice` / `genre_chase_voice` — ADR-112 §Defer stands.
- Snapshot slimming (61-2..61-5 territory).
- RAG wiring (separate epic-61 stories).
- Recency guardrails (61-7 territory, complete).

## AC Context

**AC-1 (modified per option A): only `genre_chargen` removed from STABLE.**
The story's AC-1 says "all three names." Per the predicate audit and
recommended scope reduction, this becomes: `genre_chargen` is removed;
`genre_extraction` and `genre_keeper_monologue` remain on STABLE. TEA must
log this as a Design Deviation against the story body's AC-1 with the
"option A scope reduction" rationale.

Test surface: `tests/agents/test_prompt_framework/test_bucket.py` adds an
assertion that `"genre_chargen" not in STABLE_SECTION_NAMES` AND that the
other three (`genre_extraction`, `genre_keeper_monologue`, `genre_town`)
ARE still in STABLE. Pinning all four positions is intentional — the
deferral is load-bearing and a future drive-by edit shouldn't quietly
drop them without re-running this story's predicate audit.

**AC-2 (modified per option A): only `genre_chargen` is conditionally
registered.** Predicate: `context.opening_directive is not None`. Derived
from existing `TurnContext` field at `orchestrator.py:647` — no new flag
needed. AC-2's "no new state flags introduced" rule is satisfied by
construction.

Compile-time-style check: `inspect.signature(TurnContext.__init__)` (or
direct dataclass field introspection) confirms no new field was added.

**AC-3: unit test in `test_bucket.py`.** Per option A: assert
`default_bucket_for_section("genre_chargen") == SectionBucket.User`. Also
assert the three deferred sections (`genre_extraction`,
`genre_keeper_monologue`, `genre_town`) stay on `SectionBucket.System` —
this pins the deferral.

**AC-4: fixture-driven behavior test.** Per option A, one section
(`genre_chargen`) gets the predicate-true / predicate-false pair. Test
constructs a synthetic `GenrePack` with a non-empty `prompts.chargen`,
builds two `TurnContext` fixtures (one with `opening_directive="...",
turn_number=0`; one with `opening_directive=None, turn_number=5`), calls
`build_narrator_prompt`, and asserts:

- Predicate-true: `genre_chargen` content appears in `user_message` (NOT
  `system_prompt` — it was demoted from STABLE).
- Predicate-false: `genre_chargen` content appears in NEITHER
  `user_message` NOR `system_prompt`.

The behavior test is the wiring test (server CLAUDE.md requirement) — it
verifies the bucket assignment AND the orchestrator gating fire together,
not just the bucket in isolation.

**AC-5 (modified per option A): ADR-112 amendment scope.** The amendment
records:
1. `genre_chargen` demoted from STABLE; gated on
   `opening_directive is not None` at orchestrator.py:1595-1604.
2. `genre_extraction` / `genre_keeper_monologue` deferral: predicate audit
   found no existing runtime signal; reaffirmed deferral pending either
   (a) future runtime signal wiring or (b) ADR-113 tool-attached scope
   migration.
3. `genre_town` deferral stands as in the original ADR.
4. Reference 61-11's commit SHA (after green).

Per memory `feedback_adr_priority_current_over_history`, make the
amendment LOUD about the partial-reversal status — it should be
immediately visible at the top of the ADR that the original full-cache
promotion has been partially walked back.

## Design Deviation pre-log (TEA must transcribe before writing tests)

TEA: before writing any RED tests, append this to the session file under
`## Design Deviations → ### TEA (test design)`:

```markdown
### TEA (test design)
- **Scope reduced from three sections to one (option A — architect recommendation in context-story-61-11.md §Predicate Audit)**
  - Spec source: sprint/epic-61.yaml story 61-11, AC-1 and AC-2
  - Spec text: "remove these three names from STABLE_SECTION_NAMES" + "Each of the three sections is registered conditionally ... predicates derived from existing TurnContext / GameState fields, no new state flags introduced"
  - Implementation: Only `genre_chargen` is demoted and gated; `genre_extraction` and `genre_keeper_monologue` stay on STABLE
  - Rationale: Predicate audit found `chargen_active` IS expressible via existing `TurnContext.opening_directive` (set at `websocket_session_handler.py:181-346`, cleared after opening turn). `extraction_active` and `keeper_speaking` have NO existing runtime signal — neither `TurnContext`, `GameSnapshot`, encounter state, nor `LobbyState` carries them. The SM-forbidden alternative (inventing flags) would expand scope well beyond 2 points and require new session-handler wiring
  - Severity: major (changes the count of demoted sections from 3 to 1; ADR-112 amendment AC scope changes correspondingly)
  - Forward impact: ~150 tok/turn savings (chargen only) instead of ~450 tok/turn projected by the story body. Two follow-up stories implied: one to build extraction/keeper runtime signals (or migrate to ADR-113 tool-attached scope), one to demote `genre_town` after profiling
```

If user/SM rejects option A and selects option B (demote all three, no
gating for extraction/keeper) or option C (invent flags), this deviation
is dropped and a different test surface applies — TEA should pause and
re-request scope before writing tests.

## Assumptions

- The `genre_pack.prompts` model exposes `chargen`, `extraction`,
  `keeper_monologue`, `town`, and `transition_hints` as the four fields
  the orchestrator currently reads at lines 1558-1604. If the model has
  drifted, the registration blocks above are still the right surface but
  the field-access syntax may need adjustment.
- `_build_turn_context` continues to thread `opening_directive` onto the
  produced `TurnContext` unchanged. (Verified via grep; the field is set
  at `websocket_session_handler.py:346` and threaded through.)
- The test suite at `tests/agents/test_prompt_framework/test_bucket.py`
  exists (check before writing — may need to be created if epic 61's
  prompt-framework tests live elsewhere). Grep `STABLE_SECTION_NAMES`
  across the test tree to confirm the right file.
- ADR-112 lives at `docs/adr/0112-genre-prose-stable-cache-promotion.md`
  (or similar 0112-prefixed filename) in the orchestrator repo. TEA can
  ignore this for RED phase — Tech Writer / SM owns the amendment surface.
- The 2026-05-23 runaway-Valley remediation work (`project_runaway_valley_block_2026_05_23`)
  is complete enough that this story is a pure follow-on optimization,
  not a remediation surface. If the orchestrator at line 1491+ has been
  refactored since the story was written, re-grep for the registration
  block before editing.

If any assumption proves wrong during RED phase, log under
`## Design Deviations → ### TEA (test design)` in the session file with
the 6-field format.
