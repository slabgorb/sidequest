---
story_id: "22-5"
epic: "22"
workflow: "tdd"
---

# Story 22-5: Engagement-triggered seed drops

## Story Details
- **ID:** 22-5
- **Epic:** 22 — Seed Tropes — Narrative Variety via Schrödinger's Gun
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Branch:** feat/22-5-engagement-triggered-seed-drops
- **Depends on:** 22-4 (story sequence, not blocking)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-25T08:14:04Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-25 | 2026-05-25T07:51:14Z | 7h 51m |
| red | 2026-05-25T07:51:14Z | 2026-05-25T07:59:28Z | 8m 14s |
| green | 2026-05-25T07:59:28Z | 2026-05-25T08:03:33Z | 4m 5s |
| spec-check | 2026-05-25T08:03:33Z | 2026-05-25T08:05:36Z | 2m 3s |
| verify | 2026-05-25T08:05:36Z | 2026-05-25T08:07:55Z | 2m 19s |
| review | 2026-05-25T08:07:55Z | 2026-05-25T08:13:01Z | 5m 6s |
| spec-reconcile | 2026-05-25T08:13:01Z | 2026-05-25T08:14:04Z | 1m 3s |
| finish | 2026-05-25T08:14:04Z | - | - |

## Story Charter

Add **mid-session seed injection** triggered by player engagement patterns. Today the seed engine draws an initial hand at session start (`ensure_initial_draw`) and ticks expiry every turn (`tick_seeds`). This story gates *mid-session draws* on engagement signals — when the system detects the players are actively engaged, deal new seeds from the deck into `snapshot.active_seeds`.

**Passive pacing loop:** The initial hand provides narrative scaffolding; as the players engage with the world (moving locations, investigating NPCs, triggering encounters), new seeds drop in to maintain narrative surprise and variety. This is the "player pacing" half of ADR-025 (Pacing Detection) manifested at the seed engine level.

## Why This Matters

**Session variety:** The initial 3 seeds constrain narrative exploration. Once exhausted, the world goes flat. Mid-session draws address this: seeds don't all have to be present at session start, they can emerge *in response* to player engagement. This is Schrödinger's Gun made dynamic — not just "the sealed letter is there or not," but "a new mystery appears when you're ready for one."

**Playgroup pacing:** Keith (the forever-GM now playing) and Sebastien (mechanics-first) engage deeply with the world. Passive seed injection prevents narrative exhaustion and maintains the surprise that makes a human DM feel real.

## Engagement Signals

The intent-router (ADR-113) already classifies player turns as mechanical or narrative engagement. This story taps that signal (available on dispatch context) to trigger mid-session draws.

**Specific signals (to be wired):**
- Player moves to a new location (location_change)
- Player initiates an NPC interaction (social engagement)
- Player triggers a confrontation or encounter beat (mechanical engagement)
- Post-encounter resolution (when encounter resolves, inject a seed to maintain momentum)

The exact threshold (e.g., "draw on every 3rd engagement" vs. "draw when deck is below N cards active") is TDD-determined: RED tests will establish the contract, GREEN will wire the mechanism.

## Architecture Overview

### Existing Infrastructure (from 22-1 through 22-4)

**Deck & Draws:**
- `sidequest/game/seed_deck.py:SeedDeck` — reproducible draw-without-replacement engine
- `sidequest/game/seed_tick.py:ensure_initial_draw()` — bootstrap hand at session start
- `sidequest/game/seed_tick.py:tick_seeds()` — expire seeds on turn tick

**Persistence & State:**
- `snapshot.active_seeds: list[SeedState]` — live seeds available to narrator
- `snapshot.seed_ghosts: list[SeedGhost]` — expired seeds for cross-session callback
- Deck state carried via `SeedState.activated_at_turn` tracking

**Narrator Integration:**
- `sidequest/agents/seed_context_builder.py:build_seed_context_block()` — VALLEY-zone context
- Spans: `SPAN_SEED_DRAWN`, `SPAN_SEED_EXPIRED`, `SPAN_SEED_FIRED`, `SPAN_SEED_PROMOTED` (22-4)

### What 22-5 Adds

1. **`draw_engaged_seed(snapshot, pack, *, engagement_signal)` function** in `seed_tick.py`
   - Checks if deck has remaining undrawn seeds
   - Pulls next seed via `SeedDeck.draw()` (reusing existing deck state)
   - Constructs `SeedState` and appends to `snapshot.active_seeds`
   - Emits `SPAN_SEED_DRAWN` with attribute `trigger="engagement"` (distinguishes from bootstrap draw)

2. **Wiring in orchestrator / websocket handler** (likely `websocket_session_handler.py` near the tick_seeds call)
   - Extract engagement signal from dispatch context or intent-router result
   - Call `draw_engaged_seed()` when threshold is met
   - Emit `SPAN_SEED_PROMOTED` when a seed moves from "available in deck" to "drawn via engagement"

3. **Test coverage (TDD):**
   - RED: test fixtures for `draw_engaged_seed()` contract
   - Integration test: full dispatch flow with engagement signal → new seed in snapshot
   - Regression: existing `ensure_initial_draw` and `tick_seeds` still work

### Call Sites to Wire

**Dispatch pipeline** (in websocket_session_handler.py, after tick_seeds, before narrator call):
```python
# Extract engagement signal from the turn's dispatch result
if should_draw_engaged_seed(snapshot, result):
    draw_engaged_seed(snapshot, sd.genre_pack, engagement_signal=result.intent_class)
```

**Engagement detection:**
- Intent router already emits engagement classification (ADR-113)
- Available on `result` object from narrator/agent dispatch
- Threshold logic: "draw when player's engagement changes from 'idle' to 'active'" OR "draw every N engaged turns"

## Technical Approach

### Phase 1: RED (Test Fixtures)

Create `tests/game/test_seed_draw_engagement.py`:
1. Test `draw_engaged_seed()` with an empty snapshot, full deck → new seed added
2. Test idempotence: calling `draw_engaged_seed()` twice on same engagement signal → only one draw
3. Test deck exhaustion: all seeds drawn → further calls are no-op (no error)
4. Test span emission: `SPAN_SEED_DRAWN` with `trigger="engagement"` attribute

Integration test in `tests/server/test_seed_engagement_wiring.py`:
- Fixture: session with some seeds already active (from initial draw)
- Dispatch a turn with engagement signal
- Assert: new seed appears in snapshot, span emitted, context builder sees it

### Phase 2: GREEN (Implementation)

1. **`seed_tick.py`:**
   - Add `draw_engaged_seed(snapshot, pack, *, engagement_signal, now_turn)` function
   - Reuse existing deck reconstruction logic from `ensure_initial_draw` (pull `drawn_ids` from actives + ghosts)
   - Emit `SPAN_SEED_DRAWN` with `trigger="engagement"` attribute

2. **`websocket_session_handler.py`:**
   - After `tick_seeds()` call (line ~3591), add engagement-draw logic
   - Tentative wiring: check if `result.intent_class` indicates engagement
   - Call `draw_engaged_seed()` on threshold met

3. **Threshold logic** (TDD-determined):
   - Option A: "Draw every Nth engaged turn" (e.g., every 5 engaged turns after bootstrap)
   - Option B: "Draw when active seeds fall below threshold" (e.g., < 2 active → draw one)
   - Option C: "Draw on first engagement of each type" (location change, NPC interaction, confrontation)
   - Start with Option B (simplest, least magic numbers)

### Phase 3: REFACTOR

- Clean up threshold constants (move to config or genre pack)
- Verify span attributes are minimal (no duplicate data)
- Consider whether engagement signal should live on context or be passed down

## Test Strategy

### RED Phase Deliverables

**Unit tests** (`tests/game/test_seed_draw_engagement.py`):
- Empty snapshot, full deck → draw succeeds, snapshot has new seed
- Draw twice in one turn → only one seed added (idempotence check)
- Deck exhausted → further draws are no-op
- Span carries correct attributes (seed_id, trigger="engagement")

**Integration test** (`tests/server/test_seed_engagement_wiring.py`):
- Fixture: game session after initial draw (some seeds active, some ghosts)
- Dispatch turn with engagement signal
- Assert: new seed in snapshot, build_seed_context_block sees it
- Assert: `SPAN_SEED_DRAWN` emitted with trigger="engagement"

### GREEN Phase Deliverables

- `draw_engaged_seed()` function passes all RED tests
- Wiring in `websocket_session_handler.py` such that tests pass
- No new regressions in existing seed tests (22-1, 22-3, 22-4)

### Refactor Phase

- Move engagement threshold to a constant or config
- Verify call site doesn't emit redundant `SPAN_SEED_PROMOTED` spans (only on actual draw)
- Add docstring linking to ADR-025 (Pacing Detection) and ADR-113 (Intent Router)

## References

| Document | Relevance |
|----------|-----------|
| **ADR-018: Trope Engine** | Macro tropes escalate over time; seeds are the short-arc parallel — related pacing dynamics |
| **ADR-025: Pacing Detection** | Player engagement patterns drive narrative momentum; seed injection is the passive implementation |
| **ADR-113: Intent Router** | Classifies player intent as mechanical/narrative engagement; 22-5 uses this signal to trigger mid-session draws |
| **ADR-009: VALLEY Zone** | Seeds live in VALLEY context; new seeds immediately become part of the narrator's injection |
| **Epic 22 shard:** `sprint/epic-22.yaml` — full user story + AC |
| **22-4 reference:** Span definitions and subsystem routing — 22-5 reuses SPAN_SEED_DRAWN with new `trigger` attribute |

## Sm Assessment

**Story 22-5** is the fifth and final slice of Epic 22 (Seed Tropes). All four predecessors (22-1 schema+deck, 22-2 tea_and_murder content, 22-3 narrator injection, 22-4 OTEL spans) are merged and verified. The foundation is solid — this story extends the existing seed_tick/seed_deck infrastructure with an engagement-triggered draw path.

**Scope:** 3-point TDD, server only. New function `draw_engaged_seed()` reuses `SeedDeck` reconstruction pattern from 22-1, wired at the dispatch pipeline after `tick_seeds`. Engagement signal comes from `intent_class` (ADR-113 Intent Router). OTEL observability via existing `SPAN_SEED_DRAWN` with a new `trigger="engagement"` attribute distinguishing mid-session draws from bootstrap.

**Risk:** Low. No new persistence, no new models — extends existing snapshot state (`active_seeds`). The deck reconstruction pattern is proven (22-1). The main design decision (engagement threshold) has a recommended simple approach: draw when `intent_class ∈ ("mechanical", "social") AND active_seeds < 2`.

**Routing:** TDD phased workflow → Radar (TEA) for RED phase.

## Tea Assessment

### RED State Summary

**Commit:** `3d052f8` on `feat/22-5-engagement-triggered-seed-drops`
**Tests written:** 20 total (15 new for 22-5 + 5 existing regression)
**RED state:** 2 FAILED, 13 SKIPPED, 5 PASSED — clean RED

### Test Coverage Map

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (engagement draw works) | `test_engagement_draw_appends_seed_to_actives`, `test_engagement_draw_sets_correct_seed_state_fields` | SKIP (awaiting impl) |
| AC2 (idempotent / no-redraw) | `test_engagement_draw_respects_already_drawn_seeds` | SKIP |
| AC3 (deck exhaustion no-op) | `test_engagement_draw_no_op_when_deck_exhausted`, `test_engagement_draw_no_op_when_pack_has_no_seeds`, `test_engagement_draw_no_op_when_pack_missing_seed_tropes` | SKIP |
| AC4 (OTEL trigger=engagement) | `test_engagement_draw_emits_seed_drawn_span`, `test_engagement_draw_span_carries_activated_at_turn`, `test_engagement_draw_no_span_when_deck_exhausted` | SKIP |
| AC5 (narrator sees new seed) | `test_narrator_sees_engagement_drawn_seed_in_valley_context` | SKIP |
| AC6 (no regressions) | `test_ensure_initial_draw_still_works_after_engagement_addition`, `test_tick_seeds_still_works_after_engagement_addition` | PASS |
| AC7 (reproducible deck) | `test_engagement_draw_is_reproducible_for_same_session` | SKIP |
| Wiring | `test_draw_engaged_seed_importable_from_seed_tick`, `test_engagement_draw_produces_span_through_real_otel_pipeline`, `test_seed_drawn_route_extracts_trigger_for_gm_panel` | 1 FAIL + 1 SKIP + 1 PASS |
| Threshold | `test_engagement_draw_respects_threshold_when_actives_at_capacity`, `test_engagement_draw_threshold_met_when_actives_below_capacity` | PASS |

### Rule Coverage (python-review-checklist)

| Rule | Test |
|------|------|
| #3 Type annotations | `test_draw_engaged_seed_has_type_annotations` |
| #6 Test quality | Self-check: all tests have meaningful assertions (specific values, not truthy checks) |

### Function Signature Contract

```python
def draw_engaged_seed(
    snapshot: GameSnapshot,
    pack: Any,
    *,
    session_id: str,
    engagement_signal: str,
    now_turn: int,
) -> None:
```

**Key design notes for Dev:**
- `session_id` is a required kwarg (not on the snapshot — matches `ensure_initial_draw` pattern)
- `engagement_signal` is passed through for OTEL attribution but does NOT gate the draw (the threshold check is the caller's responsibility)
- The function is unconditional: it draws if the deck has seeds. The `active_seeds < 2` threshold belongs in the websocket_session_handler wiring, not in this function
- Duck-typed `pack`: reads `pack.seed_tropes` via `getattr(pack, "seed_tropes", [])` — no-op if absent
- OTEL: emit `SPAN_SEED_DRAWN` with `trigger="engagement"` attribute (not `trigger="bootstrap"`)

### Findings

- The context doc mentions `intent_class` from ADR-113, but there's no literal `intent_class` field on `DispatchPackage`. Dev will need to derive the engagement signal from the dispatch package's subsystem dispatches or another signal. The tests are written signal-agnostic (they pass any string as `engagement_signal`).
- Existing `SPAN_ROUTES[SPAN_SEED_DRAWN].extract` does NOT include a `trigger` field — it extracts `field`, `seed_id`, `session_id`, `activated_at_turn`. Dev may want to extend the extract lambda to include `trigger` for full GM panel visibility. The route extraction test passes today (it checks seed_id is present), but Dev should consider adding trigger to the extract.

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA Finding: intent_class signal unavailability (INFORMATIONAL)

The context doc references `intent_class` from ADR-113, but `DispatchPackage` has no such field. The engagement signal for the wiring call site will need to be derived from the dispatch package structure (e.g., presence of subsystem dispatches with engagement-indicating subsystem names) or from another mechanism. Tests are written signal-agnostic — they accept any string as `engagement_signal`. Dev decides the extraction approach.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/seed_tick.py` — Added `draw_engaged_seed()` function (unconditional draw, OTEL span emission with trigger="engagement")
- `sidequest/server/websocket_session_handler.py` — Wired engagement draw after `tick_seeds()` at line ~3592, gated on dispatch_package presence + subsystem dispatches + active_seeds < 2

**Tests:** 20/20 passing (GREEN) — 63/63 across all seed-related test files
**Pre-existing failures:** 4 tests fail on develop too (confrontation trigger prompt, output format compaction, cache attribution OTEL) — unrelated to this story
**Branch:** `feat/22-5-engagement-triggered-seed-drops` (pushed)
**Lint:** ruff clean on both changed files

**Implementation notes:**
- `draw_engaged_seed` follows the exact same deck reconstruction pattern as `ensure_initial_draw` — no new abstractions
- The `trigger` span attribute is the literal `"engagement"` (not the engagement_signal param), matching the test contract
- Wiring uses `any(pd.dispatch for pd in _dispatch_package.per_player)` as the engagement signal — if the intent router produced subsystem dispatches for any player, the player is engaged
- The `seed_session_id` variable from the `ensure_initial_draw` block is reused for deck reproducibility

**Handoff:** To verify phase (TEA)

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 0

### AC-by-AC Verification

| AC | Spec | Code | Verdict |
|----|------|------|---------|
| AC1 (draw works) | Draw when engaged + active < threshold | `draw_engaged_seed()` + wiring gates on `active_seeds < 2` and dispatch presence | Aligned |
| AC2 (idempotent) | Same seed not redrawn | Deck reconstruction with `drawn_ids` from actives+ghosts; draw-without-replacement. Wiring is a single `if` (not a loop), so at most 1 draw per turn | Aligned |
| AC3 (drawn_ids) | Active/ghosted seeds never redrawn | `drawn_ids = {s.id for s in active_seeds} | {g.id for g in seed_ghosts}` passed to SeedDeck | Aligned |
| AC4 (OTEL) | SPAN_SEED_DRAWN with trigger="engagement" | Span emitted with seed_id, trigger="engagement", session_id, activated_at_turn | Aligned |
| AC5 (narrator sees) | build_seed_context_block sees new seed immediately | Seed appended to `snapshot.active_seeds` in-place; context builder reads that list. Draw fires post-narrator (correct — engagement signal comes from this turn's dispatch, reward appears next turn) | Aligned |
| AC6 (no regressions) | All existing seed tests pass | 63/63 across all seed test files; 4 pre-existing failures confirmed on develop | Aligned |
| AC7 (reproducible) | Same snapshot → same next card | Deck keyed by session_id; same drawn_ids → same shuffle → same next card. Tested explicitly | Aligned |

### Deviation Review

Dev logged one deviation (intent_class → dispatch_package subsystem check). Verified:
- Spec source is accurate (context doc line 110-111 literally references `intent_class`)
- `intent_class` genuinely does not exist on `DispatchPackage` or `NarrationTurnResult`
- The substitution (subsystem dispatch presence) is a reasonable proxy — subsystem dispatches fire when the intent router classifies a turn as mechanically actionable
- Severity correctly classified as minor; forward impact correctly assessed as none

**Decision:** Proceed to review

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (verify)

#### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | getattr pattern + SeedState construction duplicated |
| simplify-quality | 1 finding | engagement_signal param accepted but unused |
| simplify-efficiency | 1 finding | Same as reuse #2 (SeedState duplication) |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 3 findings (all medium from architectural perspective)
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Rationale for not auto-applying:**
- Finding #1 (getattr duplication): one-liner defensive access; extracting a helper is over-extraction per CLAUDE.md
- Finding #2 (SeedState construction duplication): 7 lines in two distinct lifecycle functions; intentional pattern-following, not accidental duplication
- Finding #4 (unused engagement_signal): parameter is part of the declared test contract and intentionally preserved for future ADR-113 refinement; removing would break tests and narrow the API

**Overall:** simplify: clean (0 applied fixes)

#### Quality Gate

- **Lint:** ruff clean
- **Format:** ruff format applied (committed as `a52053c`)
- **Tests:** 20/20 story tests GREEN, 63/63 seed suite GREEN
- **Pre-existing failures:** 4 on develop (unrelated)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 (import sort + format in test files) | confirmed 2 — fixed in dcf1926 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 4 | confirmed 1, dismissed 3 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 returned, 7 disabled)
**Total findings:** 3 confirmed (2 preflight fixed, 1 medium observation), 3 dismissed

### Security Finding Triage

1. **engagement_signal unused** (low confidence) — **Dismissed:** parameter exists for future API stability per Dev deviation log; only call site passes hardcoded literal "dispatch". Not user-controllable input.
2. **OTEL blind spot on no-op paths** (medium confidence) — **Confirmed as MEDIUM observation:** deck-exhausted and no-seeds paths emit no span. Existing `ensure_initial_draw` has the same pattern (returns silently on empty pack). Consistent but noted for future OTEL coverage story.
3. **Large dispatch package DoS** (low confidence) — **Dismissed:** dispatch package comes from LLM output pipeline, not user WebSocket input. Pydantic validates shape. Not exploitable without controlling the model backend.
4. **otel_capture fixture global state reset** (medium confidence) — **Dismissed:** pre-existing pattern used across 40+ test files (not introduced by this PR). Out of scope for story 22-5.

## Reviewer Assessment

### Observations

1. [VERIFIED] `draw_engaged_seed` follows identical pattern to `ensure_initial_draw` — `seed_tick.py:139-196` mirrors `seed_tick.py:74-136` in deck construction, SeedState creation, and span emission. Complies with CLAUDE.md "Don't Reinvent — Wire Up What Exists."
2. [VERIFIED] OTEL span emission with `trigger="engagement"` at `seed_tick.py:187-196` — SPAN_SEED_DRAWN carries seed_id, trigger, session_id, activated_at_turn. Complies with OTEL Observability Principle. Checked: no silent fallback on draw success.
3. [VERIFIED] Wiring guard at `websocket_session_handler.py:3598-3603` correctly gates on: dispatch_package not None, per_player dispatches present, active_seeds < 2, seed_tropes exist. All four conditions are necessary and sufficient. `_dispatch_package` and `seed_session_id` are both in scope (same indent block).
4. [VERIFIED] Type annotations complete at `seed_tick.py:139-146` — all parameters annotated, return type annotated. `Any` for `pack` matches existing duck-type pattern. Complies with Python review rule #3.
5. [SEC] [MEDIUM] No-op paths emit no OTEL signal — `seed_tick.py:159-160` (no seeds) and `seed_tick.py:173-174` (deck exhausted) return without a span. GM panel cannot distinguish "engine engaged, nothing to draw" from "engine not reached." Consistent with `ensure_initial_draw` behavior but noted for future observability improvement. (Security agent finding #2 confirmed at medium severity.)
6. [LOW] `engagement_signal` parameter at `seed_tick.py:144` is accepted but the span always emits `trigger="engagement"` (not the parameter value). This is a documented design choice (Dev deviation log), not dead code — the parameter preserves API surface for when ADR-113 adds real intent classification.
7. [LOW] Cross-player dispatches not checked — `websocket_session_handler.py:3600` only checks `per_player`, not `cross_player`. Cross-player actions are rare multi-player interactions; per-player engagement is the intended trigger. Not a bug, but noted.

### Rule Compliance

| Rule | Instances | Verdict |
|------|-----------|---------|
| #1 Silent exception swallowing | 0 try/except in diff | COMPLIANT |
| #2 Mutable default arguments | 0 mutable defaults | COMPLIANT |
| #3 Type annotations at boundaries | 1 function (draw_engaged_seed) | COMPLIANT — all params + return annotated |
| #6 Test quality | 20 tests | COMPLIANT — specific value assertions, no vacuous checks |
| #14 State cleanup ordering | 1 instance (append before span) | COMPLIANT — state mutated before side-effect |
| OTEL Observability | 1 span emission (SPAN_SEED_DRAWN) | COMPLIANT on success path; MEDIUM gap on no-op paths |
| No Silent Fallbacks | 2 early returns (no seeds, deck exhausted) | COMPLIANT — no-op is design intent, not a fallback |
| No Stubs | 0 placeholder code | COMPLIANT |
| Wiring Test Required | 1 wiring test file | COMPLIANT — OTEL span + functional assertions |
| No Source-Text Wiring Tests | 0 source-grep assertions | COMPLIANT |

### Devil's Advocate

What if this code is broken? Let me stress-test the assumptions.

**The threshold is wrong for small packs.** If a genre pack has only 2 seed_tropes and the initial hand is 3 (default), `ensure_initial_draw` will deal 2 (the deck only has 2), leaving 0 in the remaining deck. The engagement draw will try to draw, find the deck exhausted (both seeds already active), and no-op. This is correct — but what if all 2 seeds expire quickly (lifespan_turns=1)? They'd ghost, active_seeds drops to 0, threshold met, engagement draw fires, but drawn_ids includes both seed IDs from the ghosts, deck exhausted. The session runs out of narrative variety. This is a content limitation, not a code bug — the answer is "author more seeds for packs that need them."

**Multiplayer race on active_seeds.** Two players submit actions simultaneously. Each player's turn is processed by the async handler. Could both read `len(active_seeds) < 2 == True` and both draw? In theory, yes, if the handler processes two turns without awaiting between the threshold check and the append. But examining the handler: the turn processing is `await sd.orchestrator.run_narration_turn(...)` — the next player's turn waits for the previous one to complete. So `tick_seeds` → `draw_engaged_seed` → next-player-tick is sequential per-room. Not a race.

**What if seed_session_id is None?** The `seed_session_id` derivation at lines 3238-3243 has three branches: room slug, game_slug, or a composed fallback. None of these can produce None (they're string operations). If `self._room` is None AND `sd.game_slug` is None, the fallback constructs a string from genre_slug, world_slug, player_id — all strings (possibly empty, but still a valid session_id for hashing). SeedDeck's sha256 hashing handles empty strings deterministically. Not a bug.

**What if the formatter changed websocket_session_handler.py semantics?** The diff shows three hunks in the handler that are format-only changes (parenthesis rewrapping). I verified these are cosmetic — they change line breaks in existing expressions without altering logic. Lines 3266, 4785, and 5288 are all pre-existing code reformatted by `ruff format`.

No devil's advocate argument uncovered a real issue beyond the already-noted MEDIUM observation about OTEL coverage on no-op paths.

### Verdict

**APPROVED** — No Critical or High issues. One MEDIUM observation (OTEL coverage gap on no-op paths) noted for a future story. Two LOW observations documented. All 7 ACs verified by the Architect in spec-check. Tests are comprehensive (20 story + 63 total seed suite). Code follows existing patterns exactly.

### Dev (implementation)
- **Engagement signal derived from dispatch_package subsystem dispatches, not intent_class**
  - Spec source: sprint/context/22-5-context.md, Engagement Signal Detection
  - Spec text: "The intent-router (ADR-113) classifies player actions... intent_class in ('mechanical', 'social')"
  - Implementation: Used `any(pd.dispatch for pd in _dispatch_package.per_player)` — checks if the dispatch package has any subsystem dispatches, rather than a literal `intent_class` field
  - Rationale: `intent_class` does not exist as a field on `DispatchPackage` or `NarrationTurnResult`. The presence of subsystem dispatches is the closest available signal for mechanical/social engagement, and TEA's tests are signal-agnostic (they accept any string as `engagement_signal`)
  - Severity: minor
  - Forward impact: none — the engagement signal string is passed through for OTEL attribution only, not used as a gate. If ADR-113 adds a literal intent_class field later, the wiring can be refined to use it

### Architect (reconcile)
- No additional deviations found. Dev's single deviation (intent_class → dispatch_package subsystem check) is accurately documented with all 6 fields, verified against the source text in sprint/context/22-5-context.md lines 104-126. No ACs were deferred. Reviewer APPROVED with zero Critical/High findings.