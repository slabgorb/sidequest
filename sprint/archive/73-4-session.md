---
story_id: "73-4"
jira_key: ""
epic: "73"
workflow: "tdd"
---
# Story 73-4: push/angle CritSuccess scores 0 — make beat-kind impact legible so a no-dial-move crit reads as intended, not broken (Sebastien/Jade)

## Story Details
- **ID:** 73-4
- **Jira Key:** (not configured)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 2
- **Type:** bug
- **Priority:** p3

## Story Summary

During the 2026-05-31 playtest of the Glenross / Tea&Murder 'Duel of Wits' (solo Inspector Pryce, during 67-10), a critical success on the 'Concede Gracefully' beat (beat-kind=push, stat=Humour, DC 10) resulted in zero dial movement for the player while the opponent's dial advanced +2 the same turn. From the player seat, this reads as broken: "I critically succeeded and my dial didn't move but theirs did."

Root cause: push/angle beat-kinds yield no barbs delta on CritSuccess. The crit outcome needs a legible non-zero (or explicitly-flagged) impact so players understand what a critical success on a non-scoring beat means.

**Scope:**
- **sidequest-server (scoring):** Determine how push/angle beat-kinds should resolve on CritSuccess. Either produce a measurable impact or explicitly surface why they don't (e.g., "This beat doesn't advance dials").
- **sidequest-ui (beat-result legibility):** Display beat-kind impact and crit resolution so players see what just happened — especially when a crit on a push/angle beat produces no dial delta.

**Blocking:** ADR-114 (Ablative HP substrate) + ADR-116 (Confrontation requires an Other — participant membership invariant). See epic-73 description for context on confrontation hardening follow-ups.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T18:06:13Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03 | 2026-06-03T15:39:39Z | 15h 39m |
| red | 2026-06-03T15:39:39Z | 2026-06-03T15:52:20Z | 12m 41s |
| green | 2026-06-03T15:52:20Z | 2026-06-03T15:58:48Z | 6m 28s |
| spec-check | 2026-06-03T15:58:48Z | 2026-06-03T16:07:01Z | 8m 13s |
| verify | 2026-06-03T16:07:01Z | 2026-06-03T16:11:29Z | 4m 28s |
| review | 2026-06-03T16:11:29Z | 2026-06-03T18:04:25Z | 1h 52m |
| spec-reconcile | 2026-06-03T18:04:25Z | 2026-06-03T18:06:13Z | 1m 48s |
| finish | 2026-06-03T18:06:13Z | - | - |

## Sm Assessment

**Routing:** Setup complete → handing to TEA (RED phase) for the `tdd` phased workflow.

**Why this story now:** Player-selected. It's a Confrontation Engine Hardening follow-up (epic 73) with a clean, reproduced repro from the 2026-05-31 Glenross playtest — a CritSuccess on a `push` beat-kind moved the player's dial by zero while the opponent advanced +2 the same turn. From the player seat that reads as flatly broken, which directly hits two primary-audience players: Sebastien and Jade, both mechanics-first, who need mechanical resolution **legible in the player-facing UI**.

**Shape for TEA:** Two-repo change, two distinct concerns the RED tests should cover separately:
1. **sidequest-server (scoring):** the substantive fix — a `push`/`angle` beat-kind on CritSuccess must yield either a non-zero, measurable impact OR an explicitly-flagged "no-dial-move-by-design" outcome. The bug is silent zero; the fix is legibility, not necessarily a bigger number. Decide and pin the intended behavior in the test.
2. **sidequest-ui (beat-result legibility):** surface beat-kind impact + crit outcome so the player sees *why* a crit produced the delta it did.

**Watch-outs for TEA/Dev:**
- This sits under the Confrontation Engine; OTEL watcher events on the scoring decision are mandatory per the project's lie-detector doctrine — the GM panel must be able to confirm the crit-on-push path fired and what it decided.
- "Legible" cuts both ways: a deliberate zero is acceptable *if* it's explicitly flagged. Don't invent a dial delta just to make the number move if the design intent is no-advance — pin the intent first.
- No Jira (not configured) — tracking is sprint YAML + session only.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Player-facing legibility behavior with a real engine + payload + UI contract. The engine math is already correct; the tests pin the *descriptor* contract so Dev can't "wing it."

**Status:** RED confirmed (verified via testing-runner, run_id `73-4-tea-red`) — all failures are for the right reason (missing symbols/fields, not unrelated errors).

**Test Files:**
- `sidequest-server/tests/server/test_beat_impact.py` — `describe_beat_impact` semantic classifier (AC1 push resolution, AC2 angle tag-grant, AC4 strike advance/keep-tag, brace drain) + the three-zero-ish-cases distinction (resolution vs inert vs setback) + override-reads-resolved-deltas edge + `apply_beat` exposes `ApplyResult.impact` and stamps `enc.last_beat_impacts[side]` (per-side). Fails: `ImportError: cannot import name 'BeatImpact'`.
- `sidequest-server/tests/server/test_beat_impact_payload_wiring.py` — AC3 wiring: real `apply_beat` → `build_confrontation_payload` surfaces `last_beat_impact` (player side); absent on fresh encounter; player-side not opponent-side; dial-moving beat still advances metric + carries impact (AC4 no-regression). Fails: `KeyError: 'last_beat_impact'`. (1 back-compat guard passes now: omit-before-any-beat.)
- `sidequest-ui/src/components/__tests__/ConfrontationOverlay.beatimpact.test.tsx` — overlay renders `data-testid="beat-impact"` panel from `data.last_beat_impact`: resolution shows the explanation (not a bare 0) + `data-effect="resolution"`; absent → no panel (back-compat, passes now); advance still renders both dial bars (AC4); resolution vs inert read distinctly. Fails: `Unable to find [data-testid="beat-impact"]` + `last_beat_impact` not on `ConfrontationData`.

### Contract pinned for Dev (the White Rabbit)

The tests define a **5-connection** wiring (per CLAUDE.md "if it needs 5 connections, make 5"):
1. `BeatImpact` frozen dataclass + `describe_beat_impact(deltas, *, kind, outcome) -> BeatImpact` in `game/beat_kinds.py` — the **single source of truth** for kind+tier semantics (context-story §Assumptions: derive server-side, NOT a TS lookup table). Fields: `effect` (`"advance"|"setback"|"resolution"|"tag"|"backfire"|"inert"`), `dial_moved: bool`, `summary: str`, `own: int`, `opponent: int`, `resolution: bool`, `tag: str|None`. Classifier reads the **resolved** deltas (honors per-tier overrides).
2. `ApplyResult.impact: BeatImpact | None` (None only when skipped).
3. `apply_beat` stamps `enc.last_beat_impacts[actor.side] = <serialized dict>` (per-side so opposed_check's opponent beat can't clobber the player's readout).
4. `build_confrontation_payload` surfaces the **player-side** entry as `payload["last_beat_impact"]` (additive, absent when none — mirrors the `win_condition`/`player_hp` precedent in that builder).
5. UI `ConfrontationData.last_beat_impact?` + a `beat-impact` panel that renders `summary` with a `data-effect` attribute, never replacing the dial bars.

**Guardrail honored:** NO dial-math change (`DEFAULT_DELTAS` untouched). NO new dev-OTEL — the `beat_no_op`/`beat_applied` watcher emits already cover the dev side (audience boundary: this is a Sebastien/Jade *player-UI* feature, not an OTEL/GM-panel task).

**Effect precedence** the classifier must implement (a tier never has two, but pin the order): favorable dial move (`own>0` or `opponent<0`) → `advance`; unfavorable (`own<0` or `opponent>0`) → `setback`; else `tag_backfire` → `backfire`; else `resolution` → `resolution`; else tag granted → `tag`; else → `inert`.

### Rule Coverage (Python lang-review applicable subset)

| Rule | Test(s) | Status |
|------|---------|--------|
| Every suite needs a wiring test | `test_payload_surfaces_player_clean_exit_impact` (real builder), `test_apply_beat_stamps_player_side_impact_on_encounter` | RED |
| No source-text wiring tests | wiring proven by driving real `apply_beat` + `build_confrontation_payload`, asserting emitted dict (no `read_text()`/grep) | RED |
| Meaningful assertions (no vacuous) | every test asserts concrete `effect`/`dial_moved`/`tag`/`summary` values | RED |
| Additive/back-compat (no silent break) | `test_payload_omits_impact_before_any_beat_applied`, UI "absent → no panel" | PASS (back-compat guards) |
| Reads resolved deltas, not nominal | `test_override_that_adds_a_dial_move_is_described_as_moved` | RED |

**Self-check:** no vacuous assertions; the two currently-passing tests are intentional back-compat guards, not vacuous.

**Handoff:** To Dev (the White Rabbit) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes — all 5 pinned connections wired, exactly to the TEA contract.

**Files Changed:**
- `sidequest-server/sidequest/game/beat_kinds.py` — `BeatImpact` frozen dataclass + `describe_beat_impact()` classifier (effect precedence: advance/setback/backfire/resolution/tag/inert; reads resolved deltas); `ApplyResult.impact` field; `apply_beat` computes the impact and stamps `enc.last_beat_impacts[actor.side] = asdict(impact)`; added `asdict` import.
- `sidequest-server/sidequest/game/encounter.py` — `StructuredEncounter.last_beat_impacts: dict[str, dict[str, Any]]` (declared because the model is `extra="forbid"`).
- `sidequest-server/sidequest/server/dispatch/confrontation.py` — `build_confrontation_payload` surfaces the player-side entry as `payload["last_beat_impact"]` (additive; key omitted when none — mirrors the `win_condition`/`player_hp` precedent).
- `sidequest-ui/src/components/ConfrontationOverlay.tsx` — `BeatImpactView` interface + `ConfrontationData.last_beat_impact?`; `BeatImpactPanel` (`data-testid="beat-impact"`, `data-effect`, summary) rendered in the "what just resolved" zone, adjunct to the dial bars (never replacing them).

**Tests:** GREEN (verified via testing-runner, run_id `73-4-dev-green`):
- New: 20/20 (`test_beat_impact.py` + `test_beat_impact_payload_wiring.py`).
- Regression (beat_kinds / apply_beat ×3 / confrontation dispatch / per-pc projection): 89/89.
- UI overlay suites (beatimpact + existing + outcomereveal): 50/50.
- `ruff check` on the 3 changed server files: clean. `tsc --noEmit`: clean.

**Branch:** `feat/73-4-push-angle-crit-legibility` — pushed in `sidequest-server` and `sidequest-ui`.

**Guardrails honored:** `DEFAULT_DELTAS` untouched (no dial-math change); no new dev-OTEL span (audience boundary — this is a Sebastien/Jade player-UI feature, the existing `beat_no_op`/`beat_applied` emits cover the dev side).

### Spec-Check Fix (round 2 — the White Queen's catch)

The White Queen (spec-check) found a **Critical end-to-end wiring break** the GREEN tests missed: the server `ConfrontationPayload` protocol model is `extra="forbid"` and did NOT declare `last_beat_impact`, so the production broadcast site `ConfrontationPayload(**payload_dict)` (`websocket_session_handler.py` + `make_confrontation_frame_supplier`) would have raised `ValidationError` on every beat-resolution turn — crashing the confrontation broadcast (worse than the original bug). The GREEN tests missed it because the server wiring test asserted on the raw dict (pre-wrap) and the UI test used the permissive TS type.

**Fix (mirrors the `player_hp` precedent):**
- `sidequest-server/sidequest/protocol/messages.py` — declared `ConfrontationPayload.last_beat_impact: dict[str, Any] | None = None`.
- `sidequest-server/tests/server/test_beat_impact_payload_wiring.py` — added 2 boundary tests (`test_impact_survives_the_protocol_boundary`, `test_protocol_boundary_clean_when_no_impact`) that construct `ConfrontationPayload(**build_confrontation_payload(...))` and assert the descriptor round-trips — closing the exact gap.
- UI boundary verified clean: `App.tsx:1053` casts the whole wire payload to `ConfrontationData` (no field-picking), so the field passes through automatically — no UI change needed.

**Re-verified GREEN** (run_id `73-4-dev-green2`): server 364 passed / 41 skipped (impact suites now 22, protocol regression 73, full protocol 269); UI 46 passed; `ruff` + `tsc` clean; boundary repro returns OK. Pushed (`sidequest-server` HEAD `1a154c5d`).

**Handoff:** Back to the White Queen (architect) to re-verify spec alignment and complete spec-check.

### Review Rework (round 3 — the Queen of Hearts' REJECT)

Applied all 3 required fixes from the Reviewer Assessment:
1. **[TYPE/RULE]** `BeatImpactView.effect` → `BeatEffect` union (`ConfrontationOverlay.tsx`); also mirrored server-side as `BeatEffect = Literal[...]` on `BeatImpact.effect` (`beat_kinds.py`) for one SSoT — a renamed/typo'd category now fails type-check on both sides instead of producing a dead `beat-impact-${effect}` class.
2. **[DOC]** Rewrote the false comment at `beat_kinds.py` stamp site ("correct regardless of any dial-application suppression below") to state the hp_depletion caveat honestly + recorded a Delivery Finding; softened the `describe_beat_impact` "never carries two" docstring re per-tier overrides.
3. **[TEST/RULE]** `test_fail_tier_is_inert_with_nonempty_summary` now asserts summary content (`"no change" in ...`), not bare truthiness (python.md #6).

Deferred PY-6 truthy asserts (lines 105 / wiring:92) left as-is per the Reviewer's own ruling (content checks immediately follow — harmless). Coverage-gap suggestions remain non-blocking follow-ups.

**Re-verified GREEN** (run_id `73-4-dev-green3`): server 83 passed, ruff clean, **pyright 0 errors** (Literal type-checks); UI 46 passed, tsc clean. Pushed — server `435dd475`, UI `4009497`.

**Handoff:** Back to the Queen of Hearts (reviewer) to re-review.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected → resolved. Now aligned.
**Mismatches Found:** 1 Critical (fixed via Option B) + 2 deferred follow-ups (Option D).

**Gate (structural):** PASS — AC coverage present in Dev Assessment, implementation marked complete, TEA + Dev deviation subsections well-formed.

**Substance analysis (per AC):**
- AC1 (push CritSuccess explained, reads as good): MET — `describe_beat_impact` → `effect="resolution"` + summary "Clean Exit — resolves the confrontation (no dial change by design)"; UI `beat-impact` panel with `data-effect`.
- AC2 (angle tag-grant legible): MET — `effect="tag"`, summary names the tag.
- AC3 (server emits structured impact on the player-bound payload + wiring test): MET **after fix** — see Critical mismatch below.
- AC4 (dial-moving outcomes unchanged, no regression): MET — `effect="advance"`, dial bars still render, payload metric still advances; 89→ regression green.

**Mismatch 1 — `last_beat_impact` dropped at the protocol boundary** (Missing in code — Architectural, **Critical**, breaking)
  - Spec: AC3 requires the descriptor to reach the player-bound payload, proven wired (imported, sent, consumed).
  - Code (as handed to spec-check): `build_confrontation_payload` emitted `last_beat_impact`, but the server `ConfrontationPayload` model is `extra="forbid"` and did not declare it — so the production broadcast `ConfrontationPayload(**payload_dict)` would raise `ValidationError` every beat-resolution turn, crashing the confrontation broadcast. The GREEN tests missed it (server test asserted the pre-wrap dict; UI test used the permissive TS type).
  - Recommendation: **B — Fix code.** Resolved this round: Dev declared `ConfrontationPayload.last_beat_impact` (mirrors `player_hp`) + added 2 boundary tests (`ConfrontationPayload(**build_confrontation_payload(...))` round-trip). Re-verified GREEN (410 passed). UI boundary confirmed clean (`App.tsx:1053` forwards the whole payload). **Now MET.**

**Mismatch 2 — opponent-side impact not surfaced** (Extra/missing — Behavioral, Minor, non-breaking)
  - Spec: context-story §Assumptions implies a singular player-facing field; the repro confusion is "mine moved 0 but theirs moved +2."
  - Code: surfaces only the player side; engine records both sides (`enc.last_beat_impacts`), so opponent surfacing is free.
  - Recommendation: **D — Defer.** Already logged as a Delivery Finding (TEA + Dev). Outside AC scope; clean follow-up.

**Mismatch 3 — `describe_beat_impact` under hp_depletion reads nominal deltas** (Different behavior — Behavioral, Trivial, non-user-facing today)
  - Spec: story scopes social dial confrontations; HP combat renders HP bars, not the dial-impact panel.
  - Code: classifies from nominal resolved deltas even when dial application is suppressed for `hp_depletion`.
  - Recommendation: **D — Defer.** Logged as a Delivery Finding (Dev). Not user-visible in scope; a future HP-impact story should read the HP channel.

**Guardrails confirmed:** `DEFAULT_DELTAS` untouched (no dial-math change); no new dev-OTEL (audience boundary respected — player-UI feature for Sebastien/Jade, not a GM-panel/OTEL task). SSoT lives server-side in `beat_kinds.py`; UI renders the server string (no TS lookup table) — matches context §Assumptions.

**Decision:** Proceed to review (verify). The Critical mismatch is fixed and re-verified; the two remaining mismatches are correctly deferred follow-ups.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (no code changed since `73-4-dev-green2`: server 364 passed/41 skipped, UI 46 passed, ruff + tsc clean).

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8 (4 server prod + 1 UI prod + 3 tests)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication; descriptor threads classifier → encounter → payload → protocol → UI with no copy-paste. |
| simplify-quality | clean | Naming/architecture/error-handling/types all conformant; matches `win_condition`/`player_hp` precedent and per-side state pattern (taunt/morale). |
| simplify-efficiency | 1 finding (medium) | `BeatImpact.own`/`opponent` carried on the wire but only `summary` rendered today. (Line-124 "unreachable fallback" self-dismissed by the agent as harmless defensive code.) |

**Applied:** 0 high-confidence fixes.
**Flagged for Review:** 1 medium — `own`/`opponent` pass-through.
**Noted:** line-124 defensive fallback (harmless, left as-is).
**Reverted:** 0.

**Disposition of the medium finding (TEA judgment — NOT applied):** Keep `own`/`opponent`. They are (1) directly asserted in the unit-test contract (`test_beat_impact.py`: `impact.own == -1 / == 2 / == 3`, `impact.opponent == -2`) — removing them breaks the pinned classifier contract; and (2) the mechanical payload the deferred opponent-side surfacing and any numeric "+2 to your edge" readout will consume. Carrying resolved deltas on a *mechanical legibility* descriptor is intentional for the mechanics-first audience (Sebastien/Jade want the numbers visible), not redundancy. Recorded as a non-blocking note for the Reviewer.

**Overall:** simplify: clean (1 medium finding reviewed + dismissed with rationale)

**Quality Checks:** All passing (server pytest, UI vitest, ruff, tsc).
**Handoff:** To Reviewer (the Queen of Hearts) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (95 server + 46 UI green; ruff+tsc clean; 0 smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 11 | confirmed 2 (1 req, 1 def), deferred 9 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 1 (req), deferred 2 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 2 (1 req TS-2, 1 req PY-6 line230), deferred 2 |

**All received:** Yes (4 enabled returned, 5 disabled via settings)
**Total findings:** 3 confirmed-required, 13 deferred (non-blocking), 0 dismissed

## Reviewer Assessment

**Verdict:** REJECTED (bounded rework — 3 cheap fixes; coverage gaps deferred)

The core feature is correct and well-wired: AC1–AC4 met, 95 server + 46 UI tests green, the Critical protocol-boundary break was caught in spec-check and fixed + boundary-tested. But the review surfaced **two confirmed violations of stated project rules** (which the reviewer doctrine forbids dismissing) and **one provably-false comment** in shipped code. All three are ~15-minute fixes; rather than ship known rule-violations + a false statement, I bounce for a quick polish. The broader test-coverage gaps are real but **deferred as non-blocking** (Cut the Dull Bits — this is a 2-pt story; don't balloon the rework).

### Required fixes (blockers)

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM] [TYPE] [RULE] | `BeatImpactView.effect` typed as bare `string`, not the closed 6-value set. The JSDoc enumerates all six; the loose type defeats exhaustiveness AND lets a typo'd/mismatched effect silently produce a dead CSS class via `beat-impact-${impact.effect}` (latent mis-render, no compiler error). Matches typescript.md #2. | `sidequest-ui/src/components/ConfrontationOverlay.tsx:85` | Type as `'advance' \| 'setback' \| 'resolution' \| 'tag' \| 'backfire' \| 'inert'`. Recommended (not required): mirror server `BeatImpact.effect` as a `Literal[...]` for one SSoT. |
| [MEDIUM] [DOC] | Comment claims the impact is "correct regardless of any dial-application suppression below" — **false** under `win_condition="hp_depletion"`: a `strike` Success (`own>0`) reports `effect="advance"`/`dial_moved=True` while the dial is actually suppressed (the OTEL `dial_suppressed` span at the same site contradicts it). The Dev/architect already acknowledged this behavior as a deferred finding — but the comment asserts the opposite. | `sidequest-server/sidequest/game/beat_kinds.py:~531` | Reword to state the hp_depletion caveat (impact may not reflect the suppressed dial). While there, soften the `describe_beat_impact` docstring claim "a tier never carries two" — a per-tier override CAN carry both (precedence silently picks the dial move), so phrase it as "precedence resolves the case where an override carries two." |
| [LOW] [TEST] [RULE] | `test_fail_tier_is_inert_with_nonempty_summary` asserts only `assert impact.summary` (bare truthy) — the SOLE check on the inert summary; passes for any non-empty string incl. a wrong one. Matches python.md #6 ("assert result without checking specific value"). | `sidequest-server/tests/server/test_beat_impact.py:230` | Assert content, e.g. `assert "no change" in impact.summary.lower()` (or the actual inert phrasing), not just truthiness. |

### Confirmed findings by source (all 8 tags)

- **[TEST]** (reviewer-test-analyzer, reviewer-rule-checker PY-6): the inert sole-truthy assertion (REQUIRED above). Plus 9 deferred coverage gaps — see Delivery Findings.
- **[DOC]** (reviewer-comment-analyzer): the false hp_depletion "correct regardless of suppression" comment (REQUIRED above) + 2 deferred docstring-accuracy nits (the "never carries two" / "no dial change by design" claims under overrides).
- **[RULE]** (reviewer-rule-checker): 4 violations — TS-2 effect-union (REQUIRED), PY-6 ×3 truthy asserts (1 REQUIRED at line 230; lines 105 + wiring:92 DEFERRED — content checks immediately follow, so effectively harmless). 26 rules / 87 instances checked, all else compliant (No-Silent-Fallbacks ✓, No-Stubbing ✓, Verify-Wiring ✓ with real non-test consumers, No-Source-Text-Wiring-Tests ✓, type annotations ✓, mutable-defaults ✓, async/resource/deserialization N/A).
- **[TYPE]** (subagent disabled; reviewer manual check): the `effect: string` weakness is the one type-design issue (folded into REQUIRED via rule-checker). Server `BeatImpact` is a frozen dataclass with full annotations; `ApplyResult.impact: BeatImpact | None` and `ConfrontationPayload.last_beat_impact: dict[str, Any] | None` are correctly typed with shape comments. No other type-invariant issues.
- **[SEC]** (subagent disabled; reviewer manual check): no security surface — descriptor is server-derived from typed `ResolvedDeltas`+enums, not user input; `ConfrontationPayload` is `extra="forbid"` (declared field, validated); no injection/auth/secret/PII path. Clean.
- **[EDGE]** (subagent disabled; reviewer manual check): the three zero-ish cases (resolution/inert/setback) + override-reads-resolved-deltas are covered; the `opponent>0` setback summary path (brace CritFail) and the `encounter_resolved` skip path are UNtested — deferred (non-blocking; behavior is correct, only assertions missing).
- **[SILENT]** (subagent disabled; reviewer manual check): no swallowed errors — skip paths return `impact=None` explicitly via dataclass default; `build_confrontation_payload` omits the key on `None` (intentional additive absence, not a silent fallback). Clean.
- **[SIMPLE]** (subagent disabled; verify-phase simplify already ran clean): no over-engineering. The `own`/`opponent` pass-through (flagged by verify-phase simplify-efficiency, kept with rationale) stands — they are asserted in the classifier contract and feed deferred numeric/opponent readouts.

### Rule Compliance (enumerated)

- **python.md #6 (test quality):** 3 truthy-assert instances — line 230 (REQUIRED: sole check), lines 105 & wiring:92 (deferred: redundant, content check follows). All other 20 test functions assert specific values. No skips, no mock-target errors, no vacuous `assert True`.
- **python.md #3 (type annotations at boundaries):** `describe_beat_impact` params+return annotated; `BeatImpact` all fields annotated; `last_beat_impacts: dict[str, dict[str, Any]]` with shape comment — COMPLIANT.
- **python.md #1/#7/#8/#9 (exceptions/resources/deserialization/async):** N/A — no try/except, no resource open, `asdict()` on a known frozen dataclass (not untrusted), no async in new code.
- **typescript.md #2 (generic/interface):** `BeatImpactView.effect: string` — VIOLATION (REQUIRED). All other fields appropriately typed; no `Record<string,any>`/`Function`.
- **typescript.md #1/#4 (type escapes / null):** no `as any`/`@ts-ignore`/non-null-assert; the `data.last_beat_impact &&` render guard correctly handles null+undefined — COMPLIANT.
- **typescript.md #6 (React/JSX):** `BeatImpactPanel` is a pure display component, no hooks, no `dangerouslySetInnerHTML`, no list `key` — COMPLIANT.
- **CLAUDE.md wiring doctrine:** real non-test consumers confirmed (`apply_beat`→`describe_beat_impact`; `build_confrontation_payload`→`last_beat_impacts`; `App.tsx:1053`→`BeatImpactPanel`); protocol-boundary round-trip tested — COMPLIANT.

### Data flow traced
Player beat → `apply_beat` (`beat_kinds.py`) resolves deltas → `describe_beat_impact` classifies → `asdict` stamped to `enc.last_beat_impacts[side]` → `build_confrontation_payload` lifts `["player"]` → `ConfrontationPayload(**dict)` (extra="forbid", field now declared) → wire → `App.tsx:1053` casts whole payload → `BeatImpactPanel` renders `summary`+`data-effect`. End-to-end intact; the only break (protocol boundary) was fixed in spec-check.

### Devil's Advocate
Could this be broken? **(1) The string-typed `effect` is the real soft spot.** `beat-impact-${impact.effect}` builds a CSS class from an unvalidated string. If the server ever emits an `effect` the CSS doesn't style (a 7th category, a rename, a typo), the panel renders with a dead class and NO error anywhere — the mechanics-first player (Sebastien/Jade) silently gets an unstyled/ambiguous readout, the exact failure mode this story exists to prevent. A union type turns that into a compile error. This is why I elevated it to required despite "only Medium." **(2) The hp_depletion comment is a landmine:** the next dev who surfaces `last_beat_impact` for SWN combat will trust "correct regardless of suppression" and ship a readout that says "your edge advances" when the dial never moved — a regression of *this very story's goal* in a different mode. **(3) Confused-user angle:** an `inert` Fail and a `resolution` no-move both render `dial_moved=false`; the `data-effect` distinguishes them for CSS, but if a genre ships no `beat-impact-inert`/`beat-impact-resolution` CSS, they read identically — a content/CSS follow-up worth noting (deferred). **(4) Malicious input:** none — server-derived, `extra="forbid"`, no user string reaches the descriptor. **(5) Empty/huge:** summary is a bounded server string; no unbounded growth. Net: no crash/security/data-loss path, but the two required items are genuine latent-quality defects, not nitpicks.

**Handoff:** Back to Dev (the White Rabbit) for the 3 bounded fixes (review → green rework).

---

### Re-Review Verdict (round 2) — APPROVED

All 3 required fixes verified in the branch (not taken on faith):
- **[TYPE][RULE]** `BeatImpactView.effect: BeatEffect` union (`ConfrontationOverlay.tsx:90,99`) + server `BeatEffect = Literal[...]` on `BeatImpact.effect` (`beat_kinds.py:63,88`) — one SSoT; a typo/rename now fails type-check on both sides. The `beat-impact-${effect}` dead-class landmine is closed. **RESOLVED.**
- **[DOC]** The false "correct regardless of any dial-application suppression below" comment is gone, replaced by an honest `CAVEAT (hp_depletion)` (`beat_kinds.py:542`) + a Dev Delivery Finding; the "never carries two" docstring softened re overrides. **RESOLVED.**
- **[TEST][RULE]** inert test now asserts `"no change" in impact.summary.lower()` (`test_beat_impact.py:232`), not bare truthiness. **RESOLVED.**

Re-verified GREEN (run_id `73-4-dev-green3`): server 83 + UI 46 passing, ruff clean, **pyright 0 errors** (Literal type-checks), tsc clean. Commits `435dd475` (server) / `4009497` (ui) pushed.

The deferred coverage gaps (backfire field asserts, brace-CritFail setback summary, same-side overwrite, encounter_resolved skip, UI explicit-null/inert-text, redundant truthy asserts at 105/wiring:92) remain **non-blocking** follow-ups — recorded in Delivery Findings. No Critical/High. ACs AC1–AC4 met.

**Verdict:** APPROVED
**Handoff:** To SM (the Mad Hatter) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): context-story-73-4 cites `narration_apply.py:~3199` for the beat_applied emit, but that line is now inventory-consume code; the real emits are `~4070` (beat_selection) and `~5792` (opposed_check). Affects `sprint/context/context-story-73-4.md` (line ref is advisory/stale — Dev should grep, not trust the number). *Found by TEA during test design.*
- **Improvement** (non-blocking): "mine moved 0 but theirs moved +2" is the precise repro confusion; the pinned contract surfaces only the **player-side** `last_beat_impact`. Surfacing the **opponent-side** impact too (e.g. `payload["last_beat_impacts"]` or an opponent field) would let the overlay show "you: clean exit · them: +2 pressure" and fully dissolve the confusion. Affects `sidequest/server/dispatch/confrontation.py` + overlay (a clean follow-up; engine already records both sides per-side, so the data is free). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): the engine already records BOTH sides in `enc.last_beat_impacts`, but the payload surfaces only the player side, so the opponent-side legibility follow-up (the Caterpillar's finding) is truly free — `build_confrontation_payload` need only add an `opponent` entry; no engine change. Affects `sidequest/server/dispatch/confrontation.py` + overlay. *Found by Dev during implementation.*
- **Question** (non-blocking): under `win_condition="hp_depletion"`, `apply_beat` suppresses dial application but `describe_beat_impact` still classifies from the nominal resolved deltas. HP combat renders HP bars (not the dial-impact panel) and this story scopes social dial confrontations, so it is not user-visible today — but a future story surfacing `last_beat_impact` for HP combat should read the HP channel, not the inert dial deltas. Affects `sidequest/game/beat_kinds.py::apply_beat`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): a payload-builder wiring test that asserts on the raw `dict` misses the `extra="forbid"` protocol boundary (caught here by spec-check — `last_beat_impact` would have crashed the broadcast). Any new `build_confrontation_payload` key should ship a test that round-trips through `ConfrontationPayload(**...)`, not just the dict. Affects future confrontation-payload work / the wiring-test pattern. *Found by Dev during implementation (post spec-check).*

### TEA (verify)
- **Improvement** (non-blocking): simplify-efficiency flagged `BeatImpact.own`/`opponent` as wire-carried-but-unrendered (only `summary` shows today). Reviewed and intentionally kept — they are asserted in the classifier unit-test contract and are the data the deferred opponent-side / numeric-delta readouts will consume. If those follow-ups never land, a future cleanup could drop them. Affects `sidequest/game/beat_kinds.py::BeatImpact`. *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): test-coverage gaps to harden in a follow-up — backfire impact field asserts (only `effect` checked), `opponent>0` setback summary path (brace CritFail) untested, same-side overwrite invariant unproven, `encounter_resolved` skip path untested, UI explicit-`null` and inert-text-render assertions. Affects `tests/server/test_beat_impact.py` + `ConfrontationOverlay.beatimpact.test.tsx`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): two redundant bare-truthy `assert impact["summary"]` / `assert impact.summary` checks remain at `test_beat_impact.py:105` and `test_beat_impact_payload_wiring.py:92` (content checks immediately follow, so harmless — left per bounded-rework). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): genre CSS should ship distinct `beat-impact-{resolution,inert,setback,...}` styles so the three zero-ish cases read differently visually (today the `data-effect` discriminator exists but unstyled genres would render them alike). Affects genre theme CSS. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Invented the descriptor API surface (no architect phase)**
  - Spec source: context-story-73-4.md, §Scope Boundaries / §Assumptions
  - Spec text: "derive/expose a structured beat-kind impact descriptor … derived server-side … the UI renders a server-provided string/struct"
  - Implementation: TEA pinned concrete names/shapes the spec left open — `BeatImpact` dataclass + `describe_beat_impact()` in `beat_kinds.py`, an `effect` taxonomy (`advance/setback/resolution/tag/backfire/inert`), `ApplyResult.impact`, `enc.last_beat_impacts[side]`, and `payload["last_beat_impact"]`.
  - Rationale: the `tdd` workflow has no architect/design phase, so the RED tests must define the interface; choices follow the spec's stated direction and the existing `win_condition`/`player_hp` precedent in `build_confrontation_payload`.
  - Severity: minor
  - Forward impact: Dev/Reviewer may rename fields or restructure — if so, update all three test files in lockstep; the *behavior* (legible no-dial crit, distinct zero-ish cases, no dial-math change) is the real contract.
- **Per-side encounter storage instead of a single last-beat field**
  - Spec source: context-story-73-4.md, §Assumptions ("the dial-confrontation beat path needs its own player-facing impact field")
  - Spec text: implies a singular player-facing field.
  - Implementation: stored per-side (`enc.last_beat_impacts: dict[str, dict]`); payload surfaces only the player side.
  - Rationale: opposed_check applies a beat per side in one turn; a singular field would be clobbered by the opponent's beat in the non-resolving case (the exact repro is opposed_check). Per-side keeps the player's readout intact and makes the opponent-side follow-up (Delivery Finding) free.
  - Severity: minor
  - Forward impact: none for AC scope; enables the opponent-side legibility follow-up without an engine change.
- **Serialized dict on the encounter, not a nested pydantic model**
  - Spec source: ADR-023 / persistence (encounter rides the saved snapshot)
  - Spec text: encounter state is persisted via the snapshot.
  - Implementation: `last_beat_impacts` stores plain `dict[str, Any]` (wire-ready) rather than a nested `BeatImpact` pydantic field.
  - Rationale: avoids pydantic-model-nesting/serialization friction on `StructuredEncounter` and keeps the payload assembly a straight pass-through; `BeatImpact` stays a typed dataclass at the compute boundary.
  - Severity: minor
  - Forward impact: tests assert the serialized dict shape (`["effect"]`, `["dial_moved"]`, …); if Dev models it as pydantic instead, keep the same key names.

### Dev (implementation)
- No deviations from spec. Implemented the TEA-pinned 5-connection contract exactly (field names, `effect` taxonomy, per-side storage, additive payload key, adjunct UI panel). No dial-math change; no new dev-OTEL.

### Reviewer (audit)
- **TEA — Invented the descriptor API surface (no architect phase)** → ✓ ACCEPTED: sound; the `tdd` workflow has no design phase, choices follow the context's stated direction and the `win_condition`/`player_hp` precedent. Spec-check + review confirmed the shape.
- **TEA — Per-side encounter storage instead of a single field** → ✓ ACCEPTED: correct — opposed_check applies a beat per side per turn; per-side storage prevents the opponent beat clobbering the player readout (the exact repro). Enables the deferred opponent-side follow-up for free.
- **TEA — Serialized dict on the encounter, not a nested pydantic model** → ✓ ACCEPTED: avoids model-nesting friction; protocol field `ConfrontationPayload.last_beat_impact: dict[str, Any] | None` is declared + boundary-tested, so the wire contract is enforced where it matters.
- **Dev — No deviations from spec** → ✓ ACCEPTED: confirmed; implementation matched the pinned contract, and the review-round rework (BeatEffect Literal/union, honest comment, inert assertion) introduced no spec divergence.
- No undocumented deviations found by Reviewer.

### Architect (reconcile)

Existing TEA (×3), Dev, and Reviewer-audit entries reviewed: all spec sources resolve to real paths (`sprint/context/context-story-73-4.md`, `context-epic-73.md`), quoted spec text is accurate, implementation descriptions match the shipped code, and all 6 fields are present. No corrections needed. Two behavioral deviations were captured only as Delivery Findings during the run; promoted here to the deviation manifest for the audit, self-contained:

- **`describe_beat_impact` classifies from nominal deltas — over-reports a move under `hp_depletion`**
  - Spec source: `sprint/context/context-story-73-4.md`, §Scope Boundaries (In scope)
  - Spec text: "UI: render that descriptor so a no-dial-move CritSuccess reads as intended, covering `push` (resolution + Clean Exit tag) and `angle` (tag-grant) and any `{own=0, opponent=0}`-with-effect tier."
  - Implementation: `describe_beat_impact` reads the *nominal* resolved deltas. Under `win_condition="hp_depletion"`, `apply_beat` suppresses dial application (dials are inert HP placeholders) but still stamps the impact from nominal deltas — so a `strike` Success would report `effect="advance"`/`dial_moved=True` though no dial moved on-screen. A code comment (`beat_kinds.py:~542`) documents the caveat.
  - Rationale: story scope is dial (social) confrontations; `hp_depletion` renders HP bars, not the dial-impact panel, so the mismatch is not user-visible within scope. Fixing it would require threading the suppression flag / effective deltas — deferred to avoid scope creep on a 2-pt story.
  - Severity: minor
  - Forward impact: a future story surfacing `last_beat_impact` for `hp_depletion` combat MUST read the HP channel, not the nominal dial deltas (`beat_kinds.py::apply_beat`).

- **AC3 end-to-end wiring satisfied by composition, not a single cross-process e2e test**
  - Spec source: `sprint/context/context-story-73-4.md`, AC3
  - Spec text: "a wiring test proves the UI's render path actually receives it (imported, sent, consumed), not merely that a helper can compute it."
  - Implementation: proven by three composed checks over real production functions — server protocol-boundary test (`ConfrontationPayload(**build_confrontation_payload(...))` round-trips `last_beat_impact`), UI render test (overlay renders `data.last_beat_impact`), and `App.tsx:1053` forwarding the whole wire payload into `ConfrontationData` (verified by code read). No single test drives server→websocket→UI in one process.
  - Rationale: a cross-process e2e harness for one additive field is disproportionate for a 2-pt story; the composition covers each seam with real functions and honors "No Source-Text Wiring Tests." The architect's spec-check specifically closed the one seam (the `extra="forbid"` protocol boundary) that the original tests missed.
  - Severity: minor
  - Forward impact: none; if a cross-process e2e harness lands later, one test could subsume the three.