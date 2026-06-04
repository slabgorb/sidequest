---
story_id: "59-33"
jira_key: ""
epic: "59"
workflow: "tdd"
---
# Story 59-33: ResolutionSignal yield_side field — distinguish opponent-yield from player-yield for the dormant 49-5 [ENCOUNTER RESOLVED] narration

## Story Details
- **ID:** 59-33
- **Jira Key:** (not applicable)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p3

## Context

This story is part of **Epic 59: Intent Router — Mechanical-Engagement Spine**, specifically the **opponent-yield outcome cluster** (stories 59-31 through 59-34).

### Recent Progress
- **Story 59-31** (DONE) — Opponent-yield signal: record outcome `opponent_yielded` / `player_victory` when an opponent backs down (not abandoned). Implemented the engine-checked confirmation path and outcome resolution.
- **Story 59-32** (DONE, PR #634) — Shared `is_player_victory()` classifier: opponent_yielded/surrender/rout inherit player_victory rewards. Provides a single source of truth for credit-victory outcomes.

### What This Story Adds

Story 59-33 adds a `yield_side` field to the `ResolutionSignal` protocol class to distinguish:
- **Player yield** (player withdraws from confrontation) → outcome='yielded' (loss)
- **Opponent yield** (opponent backs down) → outcome='opponent_yielded' (player victory)

This distinction is critical for the currently-**dormant [ENCOUNTER RESOLVED]** narrator zone (story 49-5). Once 49-5 revives the TurnContext.pending_resolution_signal threading, the narrator will read resolution_signal.outcome and narrate the encounter close appropriately. The `yield_side` field will allow the narrator to distinguish _why_ the encounter ended (player gave up vs. opponent surrendered) for precise, genre-appropriate narration.

### Technical Approach

**Location:** `sidequest/protocol/resolution.py` — the `ResolutionSignal` pydantic model

**Current state:** ResolutionSignal has these fields:
- `outcome: str` (e.g., 'player_victory', 'opponent_victory', 'yielded', 'opponent_yielded', etc.)
- `yielded_actors: list[str]` (names of actors who yielded)
- Other outcome-tracking fields

**What changes:**
1. Add a `yield_side: str | None` field to `ResolutionSignal` with literal values:
   - `'player'` — the player side yielded (PCs withdrew)
   - `'opponent'` — the opponent side yielded (NPCs backed down)
   - `None` — the resolution was not a yield (e.g., dial threshold met, mutual destruction, etc.)

2. Wire the field at the **production emission sites** where ResolutionSignal is created:
   - `dispatch/yield_action.py::handle_yield()` — when a player yields, set `yield_side='player'`
   - `narration_apply.py::_resolve_opponent_yield()` — when an opponent yields, set `yield_side='opponent'`
   - `narration_apply.py::_resolve_dial_threshold_and_phase()` — when a dial threshold resolves, set `yield_side=None`

3. Verify the field flows through to `snapshot.pending_resolution_signal` (the staging point for 49-5 narration), which already exists.

### Acceptance Criteria

1. **ResolutionSignal schema update:** Add `yield_side: str | None` field with documentation. Field is optional in the pydantic model (pydantic v2 default: `None`).

2. **Player-yield site (handle_yield):** When `dispatch/yield_action.py::handle_yield()` creates a ResolutionSignal on player yield, set `yield_side='player'`.

3. **Opponent-yield site (_resolve_opponent_yield):** When `narration_apply.py::_resolve_opponent_yield()` creates a ResolutionSignal on opponent yield (from story 59-31), set `yield_side='opponent'`.

4. **Dial-threshold site:** When `narration_apply.py::_resolve_dial_threshold_and_phase()` creates a ResolutionSignal on dial threshold (existing), set `yield_side=None` (or omit; default).

5. **Wiring test:** Drive a full turn cycle (via fixture) that:
   - Triggers an **opponent yield** → assert `resolution_signal.yield_side == 'opponent'` on the snapshot
   - Triggers a **player yield** → assert `resolution_signal.yield_side == 'player'` on the snapshot
   - Triggers a **dial threshold resolution** → assert `resolution_signal.yield_side is None` on the snapshot
   
   Extend existing test suite in `tests/server/test_confrontation_*.py` or create `test_resolution_signal_yield_side.py`. Use real engine paths, not mocks.

6. **No breaking changes:** The field is optional; all existing ResolutionSignal() calls that don't set `yield_side` continue to work with default `None`.

7. **Documentation:** Add a brief docstring to the field explaining the yield_side values and their narrative purpose (49-5 context).

### Design Notes

- This story **does NOT revive story 49-5** (narrator-zone threading). That is a separate, dormant story. This story only ensures the ResolutionSignal carries the information 49-5 will need.
- The field is **cheap and correct**: a simple string field on an existing schema, wired at the 2-3 existing emission sites.
- **No impact on current production**: the narrator-zone is dormant; this field will be ignored until 49-5 reactivates the TurnContext threading.
- **Single source of truth**: once 49-5 reactivates, the narrator will read `resolution_signal.yield_side` directly; no secondary role tracking required.

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-06-04T08:38:25Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T08:38:25Z | - | - |

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design — PREP, pre-RED)
- **Question/Improvement** (blocking — the No-Stubbing question SM flagged): **`yield_side` would be WRITE-ONLY today; its only structural consumer (49-5 [ENCOUNTER RESOLVED] narrator zone) is DORMANT.** Authoritative trace: emission sites set `snapshot.pending_resolution_signal`, but `TurnContext.pending_resolution_signal` (`orchestrator.py:836`) is **never populated from the snapshot** — the copy/clear code was deleted in story 49-5 (per the explicit comment at `orchestrator.py:821-835`: "never reaches this field; the [ENCOUNTER RESOLVED] zone is therefore dormant in production"). So the narrator consumer (`orchestrator.py:1940-1961` → `narrator.py:323-335`) and the `encounter_resolution_signal_consumed_span` never fire in prod. The ENTIRE ResolutionSignal payload on the snapshot is write-only today, not just `yield_side`. A consume-side wiring test would be **vacuous** (no production path reads it). *Found by TEA during prep.*
- **Improvement** (recommendation — makes the field non-vacuous TODAY): There IS a feasible LIVE consumer — the OTEL `encounter_resolution_signal_emitted` span (`telemetry/spans/encounter.py:1015`, already accepts `**attrs`). Adding `yield_side` to that span gives it a real consumer NOW (the GM-panel lie-detector — epic-59's whole ethos / OTEL Observability Principle), and the wiring test becomes a genuine end-to-end OTEL assertion (drive real engine path → assert the span carries `yield_side`). **Catch:** that span is currently emitted at only ONE of the three resolution sites — the player-yield site (`yield_action.py:210`). The opponent-yield site (`_resolve_opponent_yield`, `narration_apply.py:4612`) and the dial/generic builder (`_build_resolution_signal`, `narration_apply.py:4852`, used by dial + hp_depletion + dice + 5 call sites) do NOT emit it. To give `yield_side` a live consumer at all sites, Dev must add the span emit (carrying `yield_side`) to those sites too — modest scope beyond "add a field," but it dissolves the No-Stubbing smell and yields a non-vacuous wiring test. *Found by TEA during prep.*
- **Conflict** (non-blocking — doc/path): The story names the model location `sidequest/protocol/resolution.py` (AC §35) — that file does NOT exist. The model lives at **`sidequest/game/resolution_signal.py`** (`ResolutionSignal`, `model_config = {"extra": "forbid"}`). Adding `yield_side: ... = None` is non-breaking (existing constructors omit it). *Found by TEA during prep.*
- **Improvement** (non-blocking — site accuracy): The "three emission sites" are really **two explicit yield sites + one shared default builder**: player-yield inline (`yield_action.py:183`, →`'player'`), opponent-yield inline (`narration_apply.py:4612` in `_resolve_opponent_yield`, →`'opponent'`), and `_build_resolution_signal` (`narration_apply.py:4852`, →default `None`) which backs ALL non-yield resolutions (dial threshold via `_resolve_dial_threshold_and_phase:4499`, hp_depletion, dice, +5 call sites at 3970/4044/4339/4543/5158/dice_throw:202). So `yield_side=None` as the builder default correctly covers every non-yield path in one place. *Found by TEA during prep.*

### Architect (design — concurs with TEA; adds type ruling + surrender/rout catch + verdict)
TEA's prep and mine converge: `ResolutionSignal` is in `game/resolution_signal.py` (not `protocol/resolution.py`); the consumer (49-5 `[ENCOUNTER RESOLVED]`) is dormant so the whole payload is write-only today; the fix is to give `yield_side` a live OTEL consumer. I **endorse** TEA's OTEL recommendation (emit `yield_side` on the resolution span at all three builders so the wiring test is a real span assertion, not a shape test). Three additional rulings:

- **Type (SM Q1): typed Literal, not `str|None`.** `yield_side: Literal["player","opponent"] | None = None`. The model is `extra="forbid"` pydantic v2 — a Literal makes an invalid value **raise** (fail-loud, epic mechanical-truth ethos) instead of silently storing a typo. Default `None` keeps existing constructors valid; `None` is semantically "not a yield" (distinct from the two yield sides).

- **Derive, don't hand-set — this closes the surrender/rout gap TEA's "None default" leaves open.** `yield_side` is a **pure function of `outcome`**: `yielded`→`player`; `opponent_yielded`/`surrender`/`rout`→`opponent`; else `None`. Add one helper `yield_side_for(outcome)` (co-locate with 59-32's `is_player_victory` — same single-source pattern) and call it in **all three builders**, including the factory `_build_resolution_signal`. If the factory just defaults `None` (per TEA's note), then a `surrender`/`rout` outcome that flows through the factory (opponent morale-break, `narration_apply.py:540,546`) would be mislabeled `None` instead of `opponent`. Deriving from `outcome` makes that impossible and removes per-site drift. This is the one place I'd extend beyond TEA's framing.

- **Verdict (SM Q3 — No Stubbing):** sound ~2pt story **iff** it ships with the OTEL emission (live GM-panel consumer → not a stub → non-vacuous wiring test). TEA's catch stands: the span exists at only the player-yield site today, so Dev must add the emit (carrying `yield_side`) to the opponent-yield site and the factory too — modest scope beyond "add a field," and the part that earns the story. If Keith would rather not touch OTEL here, **fold `yield_side` into 49-5** (where the narrator consumer revives) rather than land a dormant write-only field now. Do not land a field nothing reads. The unit test (`yield_side_for` mapping table) + the OTEL-span wiring tests are TEA's to write once the OTEL-vs-defer call is made.

## Design Deviations

None logged at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Wiring test asserts the OTEL span (live consumer), not just the snapshot field**
  - Spec source: AC5 (original) — "assert `resolution_signal.yield_side` on the snapshot"; SM Option-C RED dispatch.
  - Spec text: AC5 says assert the field on `snapshot.pending_resolution_signal`; Option C says the live consumer is the `encounter.resolution_signal_emitted` OTEL span.
  - Implementation: wiring tests assert BOTH the snapshot signal field AND the emitted OTEL span's `yield_side` attribute (drive real resolution paths → assert span). The snapshot-only assertion alone is a producer-write test against a dormant consumer (vacuous per CLAUDE.md wiring rule); the OTEL-span assertion is the non-vacuous live-consumer wiring test Option C mandates.
  - Rationale: 49-5 consume side is dormant (TEA prep finding) — the OTEL span is the only live consumer. Aligns with the OTEL Observability Principle.
  - Severity: minor (strengthens AC5, doesn't drop it)
  - Forward impact: Dev must emit `yield_side` on `encounter_resolution_signal_emitted_span` at the opponent-yield and factory paths (currently only player-yield emits that span).
- **Player-yield span test is PG-gated (separate file)**
  - Spec source: AC5 (drive player-yield path).
  - Spec text: "Use real engine paths, not mocks."
  - Implementation: the player-yield path (`handle_yield` → `room.session.end_scene`) requires Postgres; its test lives in a separate file with the `_pg_isolation` harness (mirrors `test_yield_dispatch.py`) and SKIPS without `SIDEQUEST_TEST_DATABASE_URL` (runs RED in CI). Opponent/dial wiring + all unit/schema tests are PG-free and cover RED locally.
  - Rationale: matches the existing codebase convention for handle_yield tests; keeps the PG dependency off the opponent/dial tests.
  - Severity: trivial
  - Forward impact: none (CI provisions PG).

### Dev (implementation)
- No deviations from spec. Implemented exactly to the TEA/Architect contract:
  - `yield_side_for(outcome) -> Literal["player","opponent"] | None` co-located in `encounter_classifier.py` beside `is_player_victory`. Implemented as an INDEPENDENT axis (string→side mapping), NOT in terms of `is_player_victory` — `yielded`→"player" (a loss, `is_player_victory`=False), `opponent_yielded`/`surrender`/`rout`→"opponent". TEA's orthogonality guard (`test_yield_side_for_is_orthogonal_to_is_player_victory`) passes.
  - `ResolutionSignal.yield_side: Literal["player","opponent"] | None = None` (game/resolution_signal.py — the real path, not the story's stale `protocol/resolution.py`). Literal fails loud on bogus values under `extra="forbid"`.
  - DERIVED (never hand-set) at all 3 builders: player-yield (`yield_action.py` `yield_side_for("yielded")`), opponent-yield (`_resolve_opponent_yield` `yield_side_for(enc.outcome)`), and the factory `_build_resolution_signal` (`yield_side_for(enc.outcome)`) — so surrender/rout flowing through the factory get "opponent", never a mislabeled None (the White Queen's catch).
  - Emit `yield_side` on `encounter.resolution_signal_emitted` at all 3 sites: player-yield (added attr to the existing emit), opponent-yield (NEW span emit), and the factory (NEW span emit inside `_build_resolution_signal`, covering every dial/hp_depletion/dice resolution in one DRY point). Verified exactly ONE span per resolution on both PG-free wiring tests (no double-emit).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-server):**
- `sidequest/game/resolution_signal.py` — new `yield_side: Literal["player","opponent"] | None = None` field (derived at construction, never hand-set). `from typing import Literal`.
- `sidequest/game/encounter_classifier.py` — new `yield_side_for(outcome) -> Literal["player","opponent"] | None` co-located with `is_player_victory`; independent axis (orthogonal to victory credit).
- `sidequest/server/narration_apply.py` — import `yield_side_for`; `_resolve_opponent_yield` derives `yield_side` + emits the resolution-signal span carrying it; `_build_resolution_signal` factory derives `yield_side` + emits the span (one DRY point for all dial/hp_depletion/dice resolutions).
- `sidequest/server/dispatch/yield_action.py` — import `yield_side_for`; player-yield builder derives `yield_side="player"`, added the attr to the existing resolution-signal span emit.

**Tests:** The 20 PG-free TEA RED tests → GREEN; the 1 PG-gated player-yield span test skips locally (runs RED in CI — expected, `SIDEQUEST_TEST_DATABASE_URL` unset). 59-33 suites: 20 passed / 1 skipped. Regression: **79 passed / 0 failed / 11 skipped** across resolution_signal/yield/encounter/dial_threshold/dice + the 59-32 classifier suites (testing-runner) — zero regressions. Full suite: **20 failed / 8988 passed / 72 errors** — the 20 failures + 72 errors are **identical to the pre-existing clean-tree baseline** (DB/embedding/reference env failures; verified the full FAILED list has ZERO yield/resolution/encounter/dice tests). **Zero new failures.** Ruff clean.

**Branch:** `feat/59-33-resolution-signal-yield-side` (sidequest-server) — pushed.

**Handoff:** To review (The Queen of Hearts).
