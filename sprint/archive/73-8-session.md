---
story_id: "73-8"
jira_key: null
epic: "73"
workflow: "tdd"
---
# Story 73-8: hp_depletion beat-impact reads the HP channel, not nominal suppressed dial deltas

## Story Details
- **ID:** 73-8
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** 73-7 (opponent_last_beat_impact surface in confrontation payload)
- **Points:** 2

## Technical Context

### The Problem

Under `win_condition=hp_depletion` (SWN-style combat, ADR-114), the engine has two layers:

1. **Dial layer** (narrative pacing): the momentum/leverage/engagement_range metric dials and strike/brace/angle/push beats. These drive the fiction — *how the confrontation moves this round*.
2. **HP layer** (lethality substrate): ablative HP, the *concrete lethality track* underneath the dials.

The engine separates these by design:
- `apply_beat` **suppresses dial application** for hp_depletion encounters (lines 564–583 of beat_kinds.py).
- When `hp_depletion=True` and deltas are non-zero, the dial mutations do NOT fire; instead, the engine emits a `dial_suppressed_hp_depletion` watcher event so the GM panel sees the deltas were computed-then-suppressed.
- The **HP channel** (`edge_delta`, `target_edge_delta`, `damage_channel=strike`, plus `check_hp_depletion()`) is the authoritative resolution track.

### The Bug

Despite suppressing the dial application, `describe_beat_impact()` **still derives the impact from the nominal dial deltas**:

```python
impact = describe_beat_impact(deltas, kind=beat.kind, outcome=outcome)  # Line 549
```

This is the caveat at lines 541–548 of beat_kinds.py (documented 73-4):

> CAVEAT (hp_depletion): for win_condition="hp_depletion" the dial application below is suppressed (the dials are inert HP placeholders), so the descriptor can report effect="advance"/dial_moved=True for a beat whose dial never actually moved on-screen. That mode renders HP bars, not this dial-impact panel (out of scope for 73-4 / dial confrontations) — but a future story surfacing last_beat_impact under hp_depletion must read the HP channel, not these nominal dial deltas.

**Concrete example:** An SWN strike with `Success` outcome under hp_depletion:
- Nominal deltas: `own=base` (the base value of the actor's damage dice).
- Dial application: **suppressed** (inert 1e6 placeholder, no mutation).
- HP channel: the real damage flows through `apply_beat_hp_channel()` via `damage_channel=strike` and the `damage_resolver()`.
- Current `describe_beat_impact()` output: `effect="advance"`, `dial_moved=True` — **falsely reports a dial move** even though the dial never moved on-screen.
- GM panel sees: the beat readout claims the player's edge advanced, but the HP bar/watcher shows HP changed instead. Inconsistency = lying about the impact.

### The Fix

`describe_beat_impact()` receives two parameters:
1. `deltas: ResolvedDeltas` — the *nominal* deltas (computed regardless of win_condition).
2. `kind` and `outcome` (for summary text).

To make the impact truthful under hp_depletion, we need:

**Option A (Add a flag):** Extend the call site to pass a `suppressed: bool` flag when hp_depletion=True. `describe_beat_impact()` uses this to:
- If `suppressed=True` and no HP-layer effects (tags, resolution), return `effect="inert"` + `dial_moved=False` + summary like "HP channel active" or "Dial suppressed for HP resolution".
- Otherwise, derive normally from the nominal deltas.

**Option B (Recompute from HP):** Pass the `StructuredEncounter` and `edge_resolver` into `describe_beat_impact()` so it can recompute the impact from the actual HP delta (`before/after` HP values). This requires introspection of the HP state *after* `apply_beat_hp_channel()` runs, which means the HP application must happen *before* the impact derivation.

**Recommendation:** **Option A (flag-based)** is cleaner and preserves the current signature. The flag is low-cost, explicit, and documents the suppression in the code. Option B couples `describe_beat_impact()` too tightly to the encounter state and makes the order-of-operations fragile.

### Implementation Approach

1. **Extend `describe_beat_impact()` signature:**
   ```python
   def describe_beat_impact(
       deltas: ResolvedDeltas,
       *,
       kind: BeatKind,
       outcome: RollOutcome,
       hp_depletion_suppressed: bool = False,
   ) -> BeatImpact:
   ```

2. **Update the logic:** When `hp_depletion_suppressed=True`:
   - If the beat has no narrative effects (no tags, no resolution, no backfire), return `effect="inert"` with a summary like "Dial suppressed; HP channel active" or similar.
   - If the beat grants tags or resolves, those still report — only the dial motion is suppressed.

3. **Update all call sites:** Find every invocation of `describe_beat_impact()` and:
   - In `apply_beat()` (beat_kinds.py line 549): pass `hp_depletion_suppressed=(enc.win_condition == "hp_depletion")`.
   - In tests: pass the flag as appropriate to the scenario (most tests pass `False` since they test dial confrontations, not hp_depletion).

4. **OTEL truthfulness:** The stamped `last_beat_impacts` dict will now correctly reflect whether a dial moved or whether the impact was inert due to suppression. The GM panel will see consistent impact + HP deltas, not conflicting narratives.

### Files to Modify

- **sidequest/game/beat_kinds.py:**
  - Function `describe_beat_impact()` (line 97): add `hp_depletion_suppressed` param.
  - Logic (lines 116–171): adjust to handle suppressed dials.
  - Call site in `apply_beat()` (line 549): pass the flag.

- **Tests:** Find and update all `describe_beat_impact()` calls in `tests/`.

### Acceptance Criteria (TDD)

1. **Test: describe_beat_impact with hp_depletion_suppressed=True**
   - A strike Success with suppressed dials and no tags returns `effect="inert"` (or a dedicated "suppressed" effect), `dial_moved=False`, summary indicates suppression.
   - A strike Success with suppressed dials AND a granted tag still returns the tag effect (tags are not suppressed by hp_depletion).
   - A push beat with resolution=True and suppressed dials still returns `effect="resolution"` (resolution beats are never suppressed, per apply_beat line 1020).

2. **Test: describe_beat_impact with hp_depletion_suppressed=False (default)**
   - All existing tests pass unchanged. The default is `False` so the behavior is backwards-compatible.

3. **Integration test: apply_beat under hp_depletion**
   - Create an hp_depletion encounter fixture.
   - Fire a strike beat with Success outcome.
   - Assert `last_beat_impacts["player"]["dial_moved"] == False` (suppressed).
   - Assert `last_beat_impacts["player"]["effect"]` is `"inert"` (or explicitly marked as suppressed).
   - Verify the HP channel recorded the actual damage (via `state_patch_hp` OTEL span).

4. **Wiring test (OTEL):**
   - Fire a beat under hp_depletion.
   - Assert `dial_suppressed_hp_depletion` watcher event fired (existing, line 566).
   - Assert `state_patch_hp` span emitted if HP changed (existing, line 335).
   - Assert `last_beat_impacts` is truthful: `dial_moved=False` when dials were suppressed.
   - The GM panel can now cross-check: watcher says "dials suppressed", impact says "inert", and state_patch_hp shows "X damage applied" — all consistent.

5. **No regressions:**
   - All existing beat_kinds tests pass.
   - All apply_beat tests pass.
   - Dial-threshold confrontations (non-hp_depletion) see no behavior change.

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-06-04

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04 | - | - |

## Delivery Findings

No upstream findings at setup time. Dev/TEA will populate as work progresses.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap (non-blocking):** The standalone `sprint/context/context-story-73-8.md` the TEA gate expects does not exist — only this session file's Technical Context. Recovered by working from the session file (which carries full ACs + technical context). Recurring sm-setup gap; flagging, not halting.

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Zeroed `own`/`opponent` under suppression (TEA's non-pinned hardening, lead-endorsed).** Implemented Option A by zeroing the dial deltas at the top of `describe_beat_impact` when `hp_depletion_suppressed=True`. This is the mechanism for BOTH the truthful stamp (favorable/unfavorable branches naturally fall through to `inert`, `dial_moved=False`) AND the hardening note: the surfaced `own`/`opponent` are 0, so 73-7's UI readout never shows a phantom dial number beside `dial_moved=False`. Tag/resolution/backfire branches read from `deltas` (not the zeroed locals), so they still fire. No test forced nominal numbers; zeroing chosen.

### TEA (test design)
- **Contract pinned at the observable boundary, not the signature.** Per team-lead directive ("pin the truthful stamp, leave Dev room on HOW"), the RED tests assert `enc.last_beat_impacts[...]` after a real `apply_beat` under hp_depletion — NOT `describe_beat_impact(..., hp_depletion_suppressed=True)`. Either Option A (flag) or Option B (HP-recompute) satisfies them. This deviates from the session's Implementation Approach, which pre-picked the flag signature and flag-specific unit tests.
- **`effect="inert"` within the existing closed `BeatEffect` union**, not a new `"suppressed"` literal. TEA strong view (see TEA Assessment): a dedicated literal would force a coordinated server+UI `BeatEffect` union change for a surface the UI does not render under hp_depletion (HP bars, not the dial-impact panel). The two `effect == "inert"` assertions are the only seam if Dev disagrees; `dial_moved is False` is non-negotiable regardless.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Truthfulness/correctness bug — the stamped `last_beat_impacts` lies about dial motion under hp_depletion. Behavioral, server-only (UI renders HP bars here, not the dial-impact panel — no UI surface).

**Test File:**
- `sidequest-server/tests/game/test_hp_depletion_beat_impact_truthful.py` — 6 tests. Mirrors `tests/game/test_apply_beat_hp_depletion.py` fixture (CreatureCore/HpPool, edge_resolver, damage_resolver, `_StrikeBeat` damage_channel=strike). Asserts on the real `apply_beat` stamp — no source-text assertions.

**Tests Written:** 6 (covers ACs 1, 3, 5; AC4 cross-channel-consistency folded into test 1).
**Status:** RED (2 failing, 4 green guards — correct for a fix-a-lie story).

**RED evidence (`-n0`):**
- `test_hp_depletion_strike_success_stamps_no_false_dial_move` → FAILED: `assert impact["dial_moved"] is False` → `assert True is False`. (Current stamp: `effect=advance, dial_moved=True, "+2 to your edge", own=2` — the lie.)
- `test_hp_depletion_strike_critsuccess_reports_tag_not_advance` → FAILED: `assert impact["dial_moved"] is False` → `assert True is False`. (Current: `effect=advance` despite the Opening tag being the only real effect.)
- 4 PASS = green guards Dev must keep green: `strike_fail_is_inert`, `resolution_beat_still_resolves` (AC 1.c — resolution never suppressed), `dial_threshold_strike_success_still_advances` (regression: dial packs unchanged, metric==2), `describe_beat_impact_pure_dial_path_unchanged` (pure-fn regression, current signature).

**Truthful contract pinned (the Dev target):**
- Under `win_condition=="hp_depletion"`, a suppressed-dial beat (strike/brace) must stamp `dial_moved=False` and an effect that is NOT `advance`/`setback`. For a strike with no tag/resolution → `effect="inert"`.
- Tags survive suppression: a CritSuccess strike (grants "Opening") stamps `effect="tag"`, `tag="Opening"`, `dial_moved=False`.
- Resolution beats are never suppressed: push resolution stamps `effect="resolution"`, `dial_moved=False`.
- Non-hp_depletion path UNCHANGED: dial strike Success → `advance`/`dial_moved=True`, metric advances.
- Cross-channel consistency (the point): the move lands on HP (`Pirate.hp.current == 4` after 3 dmg) while the stamp says "no dial" — the GM-panel cross-check.

**Mechanism recommendation (TEA strong view, lead invited it):** **Option A (flag)**, not Option B (HP-recompute). The descriptor classifies *dial* motion; under hp_depletion there is no dial motion, so the honest dial-classification is `inert`. HP is a separate channel (HP bars), not a dial effect — recomputing a "dial effect" from HP would invent a different fiction and over-couple the pure function to encounter/HP state + order-of-operations. Add `hp_depletion_suppressed: bool = False` to `describe_beat_impact`, pass `enc.win_condition == "hp_depletion"` at the call site (line 549), and under suppression drop the dial-motion precedence (so tag/resolution still surface, strike/brace fall through to inert). Keep `inert` in the existing union.

**Self-check:** No vacuous assertions. `dial_moved is False` is identity-checked. The HP cross-check (`Pirate.hp.current == 4`) proves the fixture is real, not a stub. Summary anti-lie check (`"to your edge" not in summary`) ties to the specific false claim.

**OTEL note:** Existing `dial_suppressed_hp_depletion` + `state_patch_hp` spans already cover the watcher side (tested in `test_apply_beat_hp_depletion.py`). This fix only corrects the stamp — no new subsystem decision, so no new span required; the value is making the stamp consistent with those existing spans.

**Handoff:** To Dev for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Approach:** Option A (flag) — TEA-recommended, lead-endorsed.
**Files Changed:**
- `sidequest-server/sidequest/game/beat_kinds.py` — added keyword-only `hp_depletion_suppressed: bool = False` to `describe_beat_impact`; under suppression the dial deltas (`own`/`opponent`) are zeroed at the top, so favorable/unfavorable fall through to `inert`, `dial_moved=False`, and the surfaced numbers clear. Call site in `apply_beat` (~line 565) passes `hp_depletion_suppressed=enc.win_condition == "hp_depletion"`. Tag/resolution/backfire read from `deltas` and still fire.

**own/opponent zeroed under suppression:** Yes (TEA hardening note adopted — see Design Deviations > Dev).

**Tests:** GREEN — 77/77 (`-n0`)
- Target `test_hp_depletion_beat_impact_truthful.py`: 6/6 (2 prev-RED now pass + 4 guards stay green)
- `test_beat_impact.py` (pure classifier): 16/16 — no regression
- `test_apply_beat_hp_depletion.py`: 10/10 — no regression
- broader beat suite (filter/hp_channel/disposition/counter/wwn): 45/45 — no regression

**Lint:** clean (`ruff check sidequest/game/beat_kinds.py`)
**Branch:** feat/73-8-hp-depletion-beat-impact-hp-channel (committed, NOT pushed — PR handled by SM)
**Commit:** e8a16a9

**OTEL:** No new span — per TEA, this corrects an existing stamp to be consistent with the already-emitted `dial_suppressed_hp_depletion` + `state_patch_hp` spans; no new subsystem decision.

**Handoff:** To review phase.

### Dev follow-up (suppression-specific summary) — commit 1a10e2b
TEA verify passed the structured fix but flagged a residual: the suppressed-dial inert path reused the generic "No change — the beat landed but moved nothing" summary, yet under hp_depletion the beat DID resolve on the HP channel — "moved nothing" was a small lie. Fix: capture `suppressed_dial_move = hp_depletion_suppressed and (own != 0 or opponent != 0)` *before* zeroing; in the inert branch, that case stamps "Dial held — HP channel resolved this beat" while a genuine miss (no nominal delta) keeps "moved nothing". Did NOT touch the shared line-174 literal (it serves real Fails/misses correctly). Added TEA's pinned test `test_hp_depletion_suppressed_summary_does_not_claim_total_inertness`. Verified genuine-miss `strike_fail_is_inert` still reads "No change — the beat landed but moved nothing". Tests: 78/78 (`-n0`) — target 7/7, classifier 16/16, apply_beat hp_depletion 10/10, broader beat suite 45/45. Lint clean.

## TEA Verify Assessment (quality_pass)

**Verdict: PASS (quality_pass)** — the structured-truthfulness bug is fully fixed. One adjudicated minor finding on the summary prose (note #2), recommended as a quick follow-up, NOT blocking.

**1. Tests — GREEN, no regressions:**
- Target `test_hp_depletion_beat_impact_truthful.py` 6/6 (the 2 ex-RED now pass, 4 guards green).
- Cited regression: `test_beat_impact.py` 16/16, `test_apply_beat_hp_depletion.py` 10/10 (combined run 32/32).
- Broader beat/hp/beat_impact sweep: **112 passed, 0 failed** (superset of Dev's 77 — all green).

**2. Mechanism matches the pinned contract (verified by re-characterization on the new code):**
- Suppressed strike Success → `{effect:'inert', dial_moved:False, own:0, opponent:0}` — numbers zeroed (my hardening note adopted).
- Suppressed strike CritSuccess → `{effect:'tag', tag:'Opening', dial_moved:False, own:0}` — tags survive.
- Resolution/backfire read from `deltas`, still fire. Non-hp_depletion path unchanged (dial pack strike → advance/True, metric==2).
- Only one production call site (`apply_beat:565`), correctly passes `enc.win_condition == "hp_depletion"`. No missed sites.

**3. Lint:** `ruff check sidequest/game/beat_kinds.py` → All checks passed.

**4. ADJUDICATION — Architect note #2 (summary truthfulness), my lane:**
The suppressed-inert summary reuses the generic `"No change — the beat landed but moved nothing"` (line 174). Under hp_depletion the beat DID move HP (e.g. Pirate 7→4), so "moved nothing" is a small residual lie.

**Verdict: GENUINE but MINOR gap — recommend a one-line follow-up, does not block this gate.**
- *Why it's real:* the project's central thesis is "the engine must not be described as doing something it didn't / not doing something it did." A stamped readout saying "moved nothing" when the engine applied 3 HP is exactly that failure mode — ironic on a fix-the-lie story. 73-7 is actively expanding which stamp fields get surfaced, so "not rendered under hp_depletion today" is a fragile defense.
- *Why it's minor / non-blocking:* the load-bearing GM-panel truth is carried by the **structured** fields (now `inert`/`False`/`0`/`0`) plus the existing `dial_suppressed_hp_depletion` + `state_patch_hp` watcher spans — all now consistent. The `summary` is prose, not a field the GM panel cross-checks, and this surface isn't rendered under hp_depletion. The actual bug (structured lie) is fixed.
- *Proposed pinned assertion (for route-back; the fix must be a SUPPRESSION-SPECIFIC branch — do NOT edit the shared line-174 inert literal, which also serves genuine Fails):*
  ```python
  def test_hp_depletion_suppressed_summary_does_not_claim_total_inertness():
      enc = _enc("hp_depletion"); resolver, _ = _cores(pirate_hp=7)
      apply_beat(enc, enc.actors[0], _StrikeBeat(), RollOutcome.Success,
                 turn=1, edge_resolver=resolver, damage_resolver=lambda: 3)
      summary = enc.last_beat_impacts["player"]["summary"].lower()
      assert "moved nothing" not in summary   # HP DID move
      assert "no change" not in summary
      assert any(k in summary for k in ("hp", "held", "suppress"))  # point at the real channel
  ```
  Example wording (Dev's choice): "Dial held — HP channel resolved this beat."

**Recommendation:** route back to Dev for the one-line suppression-branch summary + the assertion above. If the lead prefers to ship now and fast-follow, the mechanical fix is sound and the verdict stands as PASS.

## Reviewer Assessment

**Verdict:** APPROVED (no Critical/High; verdicts accept/nit only). The summary gap TEA flagged was already closed by Dev follow-up 1a10e2b — verified present and correct.

**Scope reviewed:** Full branch diff vs develop — `beat_kinds.py` (34 lines prod) + the new 208-line test file. Two prod commits (e8a16a9 structured fix, 1a10e2b summary follow-up). Server-only, no UI surface (HP bars render under hp_depletion, not the dial-impact panel).

**Data flow traced:** `resolve_tier_deltas` → nominal `ResolvedDeltas` → `describe_beat_impact(deltas, …, hp_depletion_suppressed=enc.win_condition=="hp_depletion")` (single prod call site, `apply_beat:576`). Under suppression the function zeroes its **local** `own`/`opponent` (rebind, not mutation — `ResolvedDeltas` is `@dataclass(frozen=True)`), so the favorable/unfavorable branches fall through, `dial_moved=False`, surfaced numbers clear. The suppression-block span at `apply_beat` reads `deltas.own/.opponent` (untouched nominal values) → `dial_suppressed_hp_depletion` carries `suppressed_own`/`suppressed_opponent`. Stamp and span co-fire on the **same gate** (`hp_depletion and (own!=0 or opponent!=0)`).

**Tests (run by Reviewer, `-n0`, not trusted from handoff):** `test_hp_depletion_beat_impact_truthful.py` 7/7 + `test_apply_beat_hp_depletion.py` 10/10 = **17/17 PASS** (0.04s). Tests pin the observable boundary (`enc.last_beat_impacts[...]` after real `apply_beat`), assert `dial_moved is False` by identity, prove the fixture is real via the HP cross-check (`Pirate.hp.current == 4`), and use a non-hp_depletion regression guard. No vacuous assertions, no source-text wiring tests.

**Verdicts on adjudication notes 1–4:**
1. **Overloaded `effect="inert"` — ACCEPT (correct call).** `inert` is honest at the dial-classification axis: under hp_depletion no dial moved, full stop. The *other* axis (whiff vs HP-resolved) is a different question answered by (a) the dedicated `dial_suppressed_hp_depletion` + `state_patch_hp` watcher spans — the GM-panel lie-detector seam per the OTEL principle — and now (b) the distinct summary string. A new `"suppressed"` BeatEffect literal would force a coordinated server+UI closed-union change for a surface the UI does not render under hp_depletion → cost with no consumer. The watcher cross-check IS the intended/sufficient disambiguation seam. Non-blocking.
2. **`suppressed_dial_move` logic — TRACED, CORRECT.** Captured before zeroing; the branch is **unreachable for a genuine miss** (requires nominal `own!=0 or opponent!=0`), so "Dial held" never leaks onto a real whiff — confirmed by the still-green `strike_fail_is_inert` ("moved nothing"). Branch precedence (advance→setback→backfire→resolution→tag→suppressed-inert→inert) keeps tag/resolution/backfire winning, all reading original `deltas`, all truthful when they fire. *Minor observation (nit):* a suppressed strike that also grants a tag stamps `effect="tag"` (not the "Dial held" note) — still truthful (the tag genuinely fired), the HP-channel note simply yields to the more salient tag effect. No wrong-summary path found.
3. **Zeroing loses info? — NO.** Nominal deltas are preserved on the `dial_suppressed_hp_depletion` span (`suppressed_own`/`suppressed_opponent`); the real signal is the HP delta (`state_patch_hp`). Zeroing the stamp is precisely what prevents 73-7's `opponent_last_beat_impact` UI from rendering a phantom number beside `dial_moved=False`. Correct trade. ACCEPT.
4. **OTEL truthfulness end-to-end — SATISFIED.** Before: stamp said `advance/dial_moved=True` while the span said suppressed → self-contradiction (the lie). After: stamp (`inert`/`False`/`0`/"Dial held") ↔ `dial_suppressed_hp_depletion` (nominal deltas + rationale) ↔ HP channel `state_patch_hp` all agree, and the shared gate guarantees stamp+span co-fire (genuine miss emits neither false signal). The three observability surfaces now tell one consistent story.

**Deviation audit (3 documented, all ACCEPTED):**
- *Dev — zeroing own/opponent under suppression:* ACCEPTED. Doubles as the truthful-stamp mechanism and the 73-7 phantom-number guard; nominal values retained on the span. Sound.
- *TEA — contract pinned at observable boundary, not signature:* ACCEPTED. Survives either mechanism (flag or HP-recompute); aligns with the repo's "No Source-Text Wiring Tests" rule.
- *TEA — `inert` over a new `"suppressed"` literal:* ACCEPTED. Identical to verdict #1.

**Findings:** 0 critical / 0 high / 0 medium / 1 nit (#2 tag-precedence drops the HP-channel summary — truthful, cosmetic, leave as-is).

**Observations (5+):**
1. Single prod call site, correctly wired — no half-fix (grep-confirmed). ✓
2. `ResolvedDeltas` frozen → in-function zeroing cannot corrupt the span's nominal-delta read. ✓
3. Stamp ↔ suppression-span share one gate → guaranteed consistency, including the genuine-miss negative case. ✓
4. Summary follow-up (1a10e2b) closes TEA's residual "moved nothing" lie with a suppression-specific branch; the shared line-174 literal (genuine Fails) untouched + guarded by `strike_fail_is_inert`. ✓
5. Tag/resolution/backfire correctly read original `deltas`, not the zeroed locals — they survive suppression as designed. ✓
6. No new OTEL span needed (no new subsystem decision); the value is making the existing stamp consistent with the already-emitted spans — exactly the OTEL-integrity intent.

**Handoff:** To SM for finish-story.
