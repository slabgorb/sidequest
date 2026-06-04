---
story_id: "73-7"
jira_key: ""
epic: "73"
workflow: "tdd"
---
# Story 73-7: Opponent-side beat-impact legibility + numeric delta readout

## Story Details
- **ID:** 73-7
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-06-04T05:40:19Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04T05:40:19Z | - | - |

## Technical Context

### Story Summary
Surface the opponent's `last_beat_impact` alongside the player's in the confrontation UI overlay, and render numeric delta readouts in BeatImpactPanel. This dissolves the 73-4 confusion where mechanics-first players (Sebastien/Jade) see their critical hit move zero dials while the opponent's damage was visible and moving their dials — creating the illusion of an unfair outcome.

Example target state: "you: clean exit · them: +2 pressure" appears in the overlay, and the BeatImpactPanel shows own and opponent numeric deltas legibly.

### Key Technical Facts
1. **No engine change required.** The server already records both sides in `enc.last_beat_impacts` (StructuredEncounter).
2. **Server change (payload):** `build_confrontation_payload` must include opponent's `last_beat_impact` alongside player's.
3. **UI change (rendering):** BeatImpactPanel (sidequest-ui/src/components/confrontation/BeatImpactPanel.tsx or similar) renders own/opponent numeric deltas legibly.
4. **Design principle:** This serves mechanics-first players per CLAUDE.md design intent — exposing the math in player-facing surfaces is correct. Sebastien/Jade want to know "what happened to the numbers."
5. **OTEL consideration:** Any subsystem touched should emit/retain watcher events so the GM panel can verify. This is largely a payload passthrough, so keep existing spans intact; add new spans only if new subsystem decisions are introduced.

### Repos and Files to Inspect
**sidequest-server:**
- `sidequest/game/encounter.py` — StructuredEncounter.last_beat_impacts (confirm field exists on both sides)
- `sidequest/handlers/payload_builders.py` or similar — `build_confrontation_payload` function
- Affected test suite: tests covering confrontation state serialization

**sidequest-ui:**
- `src/components/confrontation/BeatImpactPanel.tsx` (or location in current codebase)
- Types in `src/types/confrontation.ts` or game payload types
- Confrontation component tests

### Acceptance Criteria
1. **Payload wiring:** `build_confrontation_payload` includes both `player_last_beat_impact` and `opponent_last_beat_impact` fields (or similar naming) in the confrontation state.
2. **UI rendering:** BeatImpactPanel renders own and opponent numeric deltas (dial movement, resource cost, etc.) in a legible, distinct visual layout. Not styled yet (73-10 handles styling), but data must be present and readable.
3. **No engine change:** Encounter resolution, dial application, and beat mechanics remain unchanged. Only payload and UI change.
4. **Type safety:** TypeScript defs for the payload include the new opponent field.
5. **Test coverage:** At least one test verifies the payload includes both sides; at least one test verifies the UI renders both numeric values (mock data or integration test).

### Known Dependencies
- Depends on 73-4 (push/angle CritSuccess legibility) being merged, since 73-4 clarified what beat-impact even means.
- 73-8 notes a caveat: hp_depletion win_condition suppresses dial application but beat-impact still reports from nominal deltas. This story doesn't fix that, but be aware when testing confrontations with hp_depletion.

## Delivery Findings

No upstream findings.

## Design Deviations

### TEA (test design)
- **Opponent field naming:** AC1 said "both `player_last_beat_impact` and `opponent_last_beat_impact` fields (or similar naming)". Tests pin the **additive** choice: keep the existing 73-4 player key `last_beat_impact` UNCHANGED and add a sibling `opponent_last_beat_impact`. Reason: renaming `last_beat_impact` → `player_last_beat_impact` would break 73-4's live payload contract, its passing tests, and the UI consumer for zero benefit. AC1's "or similar naming" explicitly permits this. Applies to both the server payload dict, the `ConfrontationPayload` protocol model, and the UI `ConfrontationData` type.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New payload/UI contract (opponent-side beat-impact) — behavioral, not a chore.

**Test Files:**
- `sidequest-server/tests/server/test_opponent_beat_impact_payload.py` — 6 tests pinning `build_confrontation_payload` + `ConfrontationPayload` opponent-side wiring (mirrors `test_beat_impact_payload_wiring.py` conventions; drives real `apply_beat`, no source-text assertions).
- `sidequest-ui/src/components/__tests__/ConfrontationOverlay.opponentbeatimpact.test.tsx` — 4 tests pinning BeatImpactPanel own/opponent numeric readouts via the real `ConfrontationOverlay`.

**Tests Written:** 10 tests covering ACs 1, 2, 4, 5 (AC3 "no engine change" enforced by NOT touching engine; the payload tests source-of-truth-compare to `enc.last_beat_impacts`, proving no engine math is re-derived).
**Status:** RED (failing — ready for Dev)

**RED evidence:**
- Server: 4 failed, 2 passed (`-n0`). Failures:
  - `test_payload_surfaces_opponent_beat_impact_alongside_player` → `AssertionError: assert None is not None` (builder omits `opponent_last_beat_impact`).
  - `test_payload_keeps_player_and_opponent_impacts_distinct` → `KeyError: 'opponent_last_beat_impact'` (player-side asserts on the line above PASS — fixture is real).
  - `test_opponent_impact_survives_the_protocol_boundary` → `AttributeError: 'ConfrontationPayload' object has no attribute 'opponent_last_beat_impact'` (model field undeclared).
  - `test_protocol_boundary_opponent_none_when_opponent_has_not_acted` → same `AttributeError`.
  - 2 PASS are the additive-null guards (`omits_opponent_impact_before_opponent_acts`, `omits_both_impacts_on_fresh_encounter`) — already-correct behavior Dev must preserve.
- UI: 4 failed. All → `Unable to find an element by: [data-testid="beat-impact-own"]` (panel renders only `data-testid="beat-impact"` + summary, no numeric readouts).

**Contract pinned (the Dev target):**
- *Server payload:* `build_confrontation_payload` adds key `opponent_last_beat_impact = encounter.last_beat_impacts.get("opponent")` — additive, omitted/None when opponent hasn't acted. Same serialized-BeatImpact shape `{effect, dial_moved, summary, own, opponent, resolution, tag}`. `last_beat_impact` (player) unchanged.
- *Server protocol:* declare `opponent_last_beat_impact: dict[str, Any] | None = None` on `ConfrontationPayload` (`sidequest/protocol/messages.py`) — model is `extra="forbid"`, so undeclared key crashes the broadcast.
- *UI type:* add `opponent_last_beat_impact?: BeatImpactView | null` to `ConfrontationData`.
- *UI render:* `BeatImpactPanel` renders the player's own dial delta as a number under `data-testid="beat-impact-own"`, and (when present) the opponent's number under `data-testid="beat-impact-opponent"`. Container `data-testid="beat-impact"` and the summary stay (73-4 regression). Opponent readout omitted when `opponent_last_beat_impact` is absent or `null`.
- *No engine change:* `enc.last_beat_impacts` already carries both sides (stamped in `beat_kinds.apply_beat` via `enc.last_beat_impacts[actor.side] = asdict(impact)`).

**Self-check:** No vacuous assertions (`let _`, `assert True`, always-None `is_none`). Numeric assertions use digit-free summaries so they prove real number rendering, not summary echo. Every assertion ties to a behavior.

**Handoff:** To Dev for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/server/dispatch/confrontation.py` — additive `opponent_last_beat_impact` key in `build_confrontation_payload` (omitted when opponent hasn't acted)
- `sidequest-server/sidequest/protocol/messages.py` — declared `opponent_last_beat_impact: dict[str, Any] | None = None` on `ConfrontationPayload` (extra="forbid")
- `sidequest-ui/src/components/ConfrontationOverlay.tsx` — `opponent_last_beat_impact?` on `ConfrontationData`; `BeatImpactPanel` renders each side's `own` delta as a number (`beat-impact-own` / `beat-impact-opponent`, opponent omitted when absent/null)

**Tests:** GREEN
- Server: 6/6 `test_opponent_beat_impact_payload.py`; 6/6 `test_beat_impact_payload_wiring.py` (73-4 regression) — `-n0`
- UI: 4/4 `ConfrontationOverlay.opponentbeatimpact.test.tsx`; 54/54 all ConfrontationOverlay suites (regression)

**Lint:** clean (ruff on touched server files; eslint clean on ConfrontationOverlay.tsx — 2 pre-existing App.tsx warnings unrelated)
**Branch:** feat/73-7-opponent-beat-impact-legibility (both repos, committed, NOT pushed — PR handled by SM)
**Commits:** server b7aa5ae · ui e98a88a

**No engine change.** Pure payload + render passthrough; existing OTEL spans untouched (no new subsystem decision introduced).

**Handoff:** To review phase.

## TEA Verify Assessment (quality_pass)

**Verdict: PASS (quality_pass)**

**1. RED files now GREEN:**
- Server: `test_opponent_beat_impact_payload.py` 6/6 PASS (`-n0`).
- UI: `ConfrontationOverlay.opponentbeatimpact.test.tsx` 4/4 PASS.

**2. Regression — no breakage:**
- Server 73-4 `test_beat_impact_payload_wiring.py` 6/6 PASS. Full confrontation+beat_impact sweep (13 files, `-n0`): **98 passed, 10 skipped, 0 failed** (11.3s).
- UI full ConfrontationOverlay suite (4 files): **54/54 PASS**.

**3. Omit-vs-null consistency — RESOLVED, unambiguous (the load-bearing check):**
The server produces exactly ONE opponent-absent wire behavior: **the key is OMITTED (→ JS `undefined`), never explicit `null`.** Verified empirically + by code trace:
- The payload *dict* omits the key (`if opponent_impact is not None`).
- `ConfrontationPayload` extends `ProtocolBase`, whose `@model_serializer` applies Rust `skip_serializing_if` semantics: **None → omitted from the wire JSON** (unless flagged `include_when_none`, which this field is not). Same mechanism 73-4's `last_beat_impact` already uses.
- Empirical wire dump (`model_dump_json(exclude={"seq"})`, the real `emitters.py:382` path):
  - Opponent-absent frame → `last_beat_impact` present, `opponent_last_beat_impact` **absent**.
  - Both-acted frame → `opponent_last_beat_impact` present, `own=2` (numeric delta rides through).
- UI guard `opponent != null` catches both `undefined` and `null`. Production only ever yields `undefined` — which the UI `absent (undefined)` test covers directly. So the real production path is tested. No server↔UI ambiguity.

**4. Lint — clean on touched files:**
- Server: `ruff check` on `confrontation.py`, `messages.py`, test file → All checks passed.
- UI: `npm run lint` → 2 warnings only, both pre-existing `react-hooks/exhaustive-deps` at App lines 1323/1925 — far from the touched panel region (~647-743) and not in the test file. Touched code introduces zero new lint.

**Quality-gap analysis (untested-but-should-be paths):** None blocking.
- *Observation (non-blocking):* The UI test asserts an explicit-`null` opponent case the server will never emit (wire omits → `undefined`). Defensive over-coverage — harmless, but a future reader could wrongly infer the server emits `null`. Leave as-is (belt-and-suspenders).
- *Observation (non-blocking):* No test asserts the wire-level omission for *this specific field*; it's centrally guaranteed by `ProtocolBase.@model_serializer` and shared with 73-4. Per-field assertion would test framework behavior — verified here empirically instead.
- *Observation (non-blocking):* The render gate `{data.last_beat_impact && <BeatImpactPanel …>}` drops the opponent readout if the player impact is absent but opponent present. Confirmed unreachable in production: the player drives every turn (acts before the opposed-check opponent reacts), and `last_beat_impacts` accumulates per-side within an encounter — so whenever `opponent` is set, `player` is too.

**Simplify:** Change is ~8 lines server / ~25 lines UI, additive, mirroring the existing 73-4 player block 1:1. No duplication worth extracting, no dead code, no over-engineering. Skipped fan-out (disproportionate to a pattern-mirroring passthrough).

**Handoff:** To Reviewer.

## Reviewer Assessment

**Verdict:** APPROVED (no Critical/High; one should-fix + two nits, all non-blocking)

**Data flow traced:** `enc.last_beat_impacts["opponent"]` (stamped in `beat_kinds.apply_beat:550`) → `build_confrontation_payload` additive key `opponent_last_beat_impact` (`confrontation.py:280-287`) → `ConfrontationPayload.opponent_last_beat_impact` (declared, `extra="forbid"` satisfied) → ProtocolBase `@model_serializer` omits-on-None → wire → UI `ConfrontationData.opponent_last_beat_impact` → `BeatImpactPanel opponent` prop → `data-testid="beat-impact-opponent"`. Safe: additive sibling, mirrors the live 73-4 player path 1:1.

**Pattern observed:** Symmetric mirror of the 73-4 player block at `confrontation.py:272-287` — same `.get(side)` source, same `if … is not None` omit guard. Correct reuse, no divergence.

**Error handling:** None-absent on both server (key omitted → JS `undefined`) and UI (`opponent != null` guard catches `undefined` + `null`). No crash path. `own ?? 0` renders `0` for a clean-exit CritSuccess (the `summary` still explains it — 73-4 behavior intact).

**Tests (run by Reviewer, not trusted from handoff):**
- Server `-n0`: `test_opponent_beat_impact_payload.py` (6) + `test_beat_impact_payload_wiring.py` 73-4 regression (6) → **12/12 PASS** (0.12s). Tests drive REAL `apply_beat` + REAL builder + protocol round-trip; no source-text assertions; digit-free summaries prove real number rendering.
- UI: opponent-beat-impact suite **4/4**, full ConfrontationOverlay sweep **54/54 PASS**.

**`extra="forbid"` boundary:** Confirmed — field declared on model; ProtocolBase serializer (`base.py:88-92`) omits None unless `include_when_none` (this field is not flagged), so wire only ever yields `undefined` or a real value, never explicit `null`. TEA's omit-vs-null analysis holds.

**Verdicts on carry-forward notes 1–4:**
1. **`.own`-per-side semantics — ACCEPT (correct for scope).** `own`/`opponent` are signed deltas measured against the actor's own/other edge (`beat_kinds.py:12,46`). Panel shows player→player-edge and opponent→opponent-edge, i.e. "what each actor did to advance themselves." Matches the story example literally ("them: +2 pressure" = opponent advanced own edge +2). *Documented limitation:* the cross-delta (`.opponent` — "what the enemy did to MY dial") is NOT surfaced by these two numbers; for the canonical 73-4 "why did my dial move" case that cross number is arguably more informative. Out of scope here; flagging for 73-10's richer readout.
2. **Bare integers, no labels/sign — ACCEPT as scoped.** AC2 explicitly defers styling to 73-10; data is present, structured, reachable. *Caveat:* two adjacent identical `<span class="text-xs">` are disambiguated only by DOM testid — a sighted user sees "32"/"02" with no "you"/"them". The "legible" half of AC2 is thin, but the story body and the team both deferred labels/signs to 73-10. Non-blocking.
3. **UI explicit-null over-coverage — ACCEPT (nit).** Harmless belt-and-suspenders; exercises the `opponent != null` guard. Minor doc risk a future reader infers the server emits `null` — a one-line test comment would neutralize it. Non-blocking.
4. **Render-gate reachability — CORRECTION + SHOULD-FIX (non-blocking).** TEA's "unreachable in production" is **overstated**. The opposed_check path (`narration_apply.py:5636` apply_targets, dice path) genuinely applies player-first, so combat holds. BUT the **legacy beat_selection path** (`narration_apply.py:4031-4055`) applies whatever beats the narrator emits, in narrator order, and *explicitly preserves opponent-side selections* (per the 2026-04-25 P0 playtest comment at :3990). `last_beat_impacts` accumulates and is never cleared, so the live window is "first beat of an encounter is an opponent beat" — reachable via enemy-acts-first / surprise round / player-takes-a-non-combat-action turn. In that case `opponent_last_beat_impact` is present while `last_beat_impact` (player) is absent, and the gate `{data.last_beat_impact && <BeatImpactPanel…>}` drops the **entire** panel, suppressing exactly the "the enemy hit you" readout the story wants. **NOT a regression** (pre-73-7 rendered no opponent half at all) and **not a crash** (safe no-render) — so non-blocking. Recommend tracking for 73-10: gate on `(data.last_beat_impact || data.opponent_last_beat_impact)` and let `BeatImpactPanel` tolerate an absent player impact.

**Deviation audit:** The one documented deviation (TEA — additive `opponent_last_beat_impact` sibling rather than renaming to `player_last_beat_impact`) is **ACCEPTED** — AC1's "or similar naming" permits it, and renaming would break the live 73-4 contract for zero benefit.

**OTEL:** No gap. Pure payload/render passthrough, no new subsystem decision; the underlying beat application already emits the `beat_applied` watcher event carrying `own_delta`/`opponent_delta` (dice.py ~:744). Existing spans intact.

**Observations (5+):**
1. Server change is a faithful 1:1 mirror of 73-4 (confrontation.py:280-287). ✓
2. Protocol None-omit semantics verified at base.py:88-92 — no explicit `null` on wire. ✓
3. Tests drive real engine + real builder, digit-free summaries — no vacuous/echo assertions. ✓
4. Render-gate edge (#4) is a reachable-but-safe legibility miss in the legacy path, not a regression. (should-fix → 73-10)
5. `.own`-per-side readout omits cross-deltas (#1) — correct for scope, noted for 73-10.
6. Bare-integer ambiguity (#2) and explicit-null over-coverage (#3) — both accepted as scoped/nit.

**Handoff:** To SM for finish-story.
