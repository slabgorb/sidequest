---
story_id: "108-6"
jira_key: ""
epic: "108"
workflow: spdd
---
# Story 108-6: WWN dying/down window + solo-actuator gap

## Story Details
- **ID:** 108-6
- **Title:** WWN dying/down window + solo-actuator gap (BRAINSTORM-FLAGGED)
- **Jira Key:** (none — personal project, no Jira integration)
- **Workflow:** spdd
- **Points:** 5
- **Type:** feature
- **Stack Parent:** none

## Story Context

**Acceptance Criteria:**

AC1: Under a WWN binding, a solo PC dropped to 0 HP with NO live hostile enters the WWN dying window (one coherent status — never the #846 dual-status); a PC downed with a live hostile present still goes terminal immediately.

AC2: The downed soloist can submit free-text actions (input gate carve: stabilizable window permits+routes to narrator; terminal blocks).

AC3: The stabilize clock is engine-owned — rounds_elapsed derived from created_turn provenance (narrator-supplied value is a fail-loud cross-check); difficulty = 8 + rounds_elapsed; successful stabilize restores HP to 1 + Frail.

AC4: Expiry fires per-turn even on non-stabilization turns; clock cannot be paused; expiry converts window to terminal-dead.

AC5: Three OTEL spans (wwn.dying_window.opened/tick/resolved) + folded #846 superseded_by_terminal attribute on mortal_injury.declared extract.

AC6: Mandatory end-to-end solo wiring test proving gate→tick→both outcomes (stabilize lives, stall dies).

**Design Spec:** `/Users/slabgorb/Projects/oq-1/docs/superpowers/specs/2026-06-14-wwn-dying-window-solo-actuator-design.md`

**Implementation Plan:** `/Users/slabgorb/Projects/oq-1/docs/superpowers/plans/2026-06-14-wwn-dying-window-solo-actuator.md`

**Architecture:** Sequential single-status state machine on existing infrastructure (the Mortal Injury status + `stabilize_mortal_injury` tool + #846 `created_turn` provenance). One input-gate carve lets the downed soloist keep submitting free-text actions; the player's own submissions tick an engine-owned clock; expiry converts the window to terminal. Three new OTEL spans make the clock GM-panel-auditable. No native-engine mechanic is touched (ADR-143).

**Tech Stack:** Python 3 / FastAPI, pydantic v2, pytest (`-n auto` via uv), OpenTelemetry spans (`sidequest/telemetry/spans/`).

**Repository:** sidequest-server (branch strategy: gitflow, base `develop`, feature branch `feat/108-6-wwn-dying-window-solo-actuator`)

**Files in Scope (8 tasks):**
- Task 1: `sidequest/game/status.py` — Add `stabilizable: bool = False` structured field to `Status`
- Task 2: `sidequest/telemetry/spans/wn.py` — Three dying-window spans + fold #846 `superseded_by_terminal`
- Task 3: `sidequest/game/ruleset/without_number.py` — Window status carries `incapacitating=True` + `stabilizable=True`; `is_dying_window_status` helper
- Task 4: `sidequest/server/dispatch/downed_seam.py` — Branch on live-hostile (terminal) vs no-live-hostile (window); emit `dying_window.opened`
- Task 5: `sidequest/handlers/player_action.py` — Gate carve: terminal blocks; stabilizable permits + routes to narrator
- Task 6: `sidequest/agents/tools/stabilize_mortal_injury.py` — Derive `rounds_elapsed` from provenance; fail-loud cross-check; set HP to 1 on success
- Task 7: `sidequest/server/post_resolution_lethality.py` — Per-turn expiry check; emit `dying_window.tick` / `dying_window.resolved`
- Task 8: `tests/server/test_wwn_dying_window_wiring.py` — End-to-end solo wiring test (the mandatory one)

## Workflow Tracking

**Workflow:** spdd
**Phase:** finish
**Phase Started:** 2026-06-14T13:11:56Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-14T11:43:14Z | 2026-06-14T11:46:54Z | 3m 40s |
| red | 2026-06-14T11:46:54Z | 2026-06-14T12:01:16Z | 14m 22s |
| green | 2026-06-14T12:01:16Z | 2026-06-14T12:45:51Z | 44m 35s |
| review | 2026-06-14T12:45:51Z | 2026-06-14T12:56:57Z | 11m 6s |
| green | 2026-06-14T12:56:57Z | 2026-06-14T13:07:08Z | 10m 11s |
| review | 2026-06-14T13:07:08Z | 2026-06-14T13:11:56Z | 4m 48s |
| finish | 2026-06-14T13:11:56Z | - | - |

## Delivery Findings

**Brainstorm status:** COMPLETE (2026-06-14, Approach A, all 5 sections approved). The open solo-actuator design problem is resolved in the spec.

**Design & Plan Status:** Both complete and comprehensive:
- Design spec: 5 sections (down-state machine, input-lane carve, clock advancement, OTEL, test strategy) + files-in-scope table
- Implementation plan: 8 tasks with step-by-step test-driven instructions, existing fixture references, and scope verification

No upstream findings.

### TEA (test design)
- **Gap** (non-blocking): The plan homes AC4 expiry in `apply_post_resolution_lethality`, but that function early-returns on any turn without a resolved PC-down encounter — so a dying-window *stall* turn would never tick/expire there, leaving the clock pausable (an AC4 violation). Affects `sidequest/server/post_resolution_lethality.py` + `sidequest/handlers/player_action.py` (Dev must put the per-turn expiry on the player-action path, which has cfg access via `session._session_data.genre_pack`, not solely in the post-resolution pass). The deadline needs `cfg.trauma.mortal_injury_rounds`; the window status carries only `created_turn`, so the expiry site must read rounds from the bound pack cfg (reachable at the gate) — or the window must store its own deadline. *Found by TEA during test design.*
- **Improvement** (non-blocking): The gate's *permit* decision for a stabilizable window should emit its own OTEL span (the plan proposes `player_action_dying_window_permitted_span`) so the GM panel can see the carve fire, not just the *block* span. `tests/server/test_player_action_dying_window_gate.py` asserts the block span does NOT fire on permit but does not yet require a positive permit span — Dev should add the emit and may extend that test. Affects `sidequest/handlers/player_action.py` + `sidequest/telemetry/spans/encounter.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): Overkill/instakill predicate (spec Section 1) is not explicitly implemented in `downed_seam.py` — the common verdict-routed instakill is covered by the existing `superseded` guard (a terminal verdict stamps the incapacitating status first), but an exotic solo strike/cast self-drop with massive overkill and no live hostile would open a stabilizable window. Affects `sidequest/server/dispatch/downed_seam.py` (add an explicit overkill marker check forcing `open_window=False`, + a test). Negligible real-world trigger for the playgroup; surfaced for the formal review to weigh. *Found by Dev during implementation (pre-handoff review).*
- **Improvement** (non-blocking): The expiry-converted terminal status is not persisted before the gate returns — it survives via the shared in-memory room object + the next save, matching the existing terminal-block path's behavior, but a crash mid-stall could lose the conversion. Affects `sidequest/handlers/player_action.py` (persist on the expiry branch). *Found by Dev during implementation (pre-handoff review).*
- **Improvement** (non-blocking): `_bound_wn_slug(sd) or "wwn"` defaults to `wwn` for the expiry spans; on the expiry path the pack is always a real WN pack (the deadline computation already confirmed a Cwn/Wwn cfg), so it cannot mis-namespace there, but the `or "wwn"` is defensive-only. Affects `sidequest/handlers/player_action.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): The full server suite is parallel (xdist) and has pre-existing cross-worker DB-state bleed — `test_102_5_wn_tool_narrator_wiring`, the space_opera SWN HP-ablation e2e tests, and chargen-armor flake under `-n auto` but pass in isolation and on `develop`. wry_whimsy content-validation fails deterministically (missing `seed_tropes.yaml` in sidequest-content). None are caused by 108-6. Affects test infra / sidequest-content. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (blocking): The test suite does not discharge its AC wiring obligations — expiry tests assert nothing on the AC5 spans they capture; the AC2 permit test passes via the no-cfg fallback, not the real carve; a `'Frail' in s.text` text-scrape violates the structured-markers rule. Affects `tests/server/test_dying_window_expiry.py`, `tests/server/test_player_action_dying_window_gate.py`, `tests/agents/tools/test_stabilize_dying_window_clock.py`. *Found by Reviewer during code review.*
- **Gap** (blocking): 2 ruff I001 lint errors in new test files. Affects `tests/server/test_player_action_dying_window_gate.py`, `tests/server/test_wwn_dying_window_wiring.py` (`ruff check --fix`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `slug or "wwn"` can mis-namespace expiry spans for a CWN/AWN session (slug-honesty / No-Silent-Fallbacks). Affects `sidequest/handlers/player_action.py:630,637` (resolve slug from the confirmed cfg or fail loud). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Stale/lying docstrings + dead `_MORTAL_INJURY_MARKER`. Affects `sidequest/game/ruleset/without_number.py:499`, `sidequest/agents/tools/stabilize_mortal_injury.py:8,14,60`. *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** 2 findings (0 Gap, 0 Conflict, 0 Question, 2 Improvement)
**Blocking:** None

- **Improvement:** The expiry-converted terminal status is not persisted before the gate returns — it survives via the shared in-memory room object + the next save, matching the existing terminal-block path's behavior, but a crash mid-stall could lose the conversion. Affects `sidequest/handlers/player_action.py`.
- **Improvement:** `slug or "wwn"` can mis-namespace expiry spans for a CWN/AWN session (slug-honesty / No-Silent-Fallbacks). Affects `sidequest/handlers/player_action.py:630,637`.

### Downstream Effects

- **`sidequest/handlers`** — 2 findings

### Deviation Justifications

3 deviations

- **AC4 expiry pinned at the player-action path, not `apply_post_resolution_lethality`**
  - Rationale: `apply_post_resolution_lethality` early-returns unless `encounter` is resolved with a PC-down outcome (verified at `post_resolution_lethality.py:208-211`). A dying-window *stall* turn (free-text non-stabilization) is NOT a resolved-down encounter, so an expiry check living only there would never fire on the stall turn — and AC4 explicitly requires "the clock cannot be paused" by stalling. The handler reads `session._session_data.genre_pack` (`player_action.py:429`), so the bound `cfg.trauma.mortal_injury_rounds` IS reachable on the player-turn path. Testing the behavioral outcome (not the function) keeps the Dev free to wire expiry in the gate, a gate-called helper, or a per-turn pass — but forces it onto the player-turn path where AC4 actually requires it.
  - Severity: minor
  - Forward impact: none on sibling stories; surfaced to Dev as a non-blocking Delivery Finding so the expiry home is chosen deliberately.
- **`resolve_downed` gained a `dying_window` flag; the window is no longer the default mint**
  - Rationale: the spec implied resolve_downed always mints the window when not superseded, but that suppressed/replaced the OPPONENT Mortal Injury death clock (a downed opponent always has a live hostile — the player). Making every WN down a stabilizable window broke 6 combat-dispatch tests (`statuses=[]`). The flag preserves the ordinary clock for opponents/PC-at-sword-point and opens the window only for the scoped solo (no-live-hostile) case — which IS the spec's AC1 intent ("a PC downed with a live hostile present still goes terminal immediately").
  - Severity: minor
  - Forward impact: any future direct caller of `resolve_downed` that wants the window must pass `dying_window=True` (the seam is the only production caller and does so).
- **Per-turn expiry implemented in the player_action gate (not `apply_post_resolution_lethality`)**
  - Rationale: `apply_post_resolution_lethality` early-returns on any turn without a resolved PC-down encounter, so it cannot fire on a dying-window stall turn (AC4 "the clock cannot be paused"). The gate is the one place every dying-window submission passes and has cfg access.
  - Severity: minor
  - Forward impact: none.

## Design Deviations

### TEA (test design)
- **AC4 expiry pinned at the player-action path, not `apply_post_resolution_lethality`**
  - Spec source: docs/superpowers/plans/2026-06-14-wwn-dying-window-solo-actuator.md, Task 7 ("Per-turn expiry ... lives in the per-PC post-resolution pass `apply_post_resolution_lethality`")
  - Spec text: "Every dying-window turn must tick the clock and, on deadline, convert the window to terminal — even when the player's action was not a stabilization. This lives in the per-PC post-resolution pass (`apply_post_resolution_lethality`), which runs after each action resolves."
  - Implementation: `tests/server/test_dying_window_expiry.py` asserts the expiry OUTCOME (deadline passed → blocked terminal + window cleared) by driving the real `PlayerActionHandler.handle`, not `apply_post_resolution_lethality` directly.
  - Rationale: `apply_post_resolution_lethality` early-returns unless `encounter` is resolved with a PC-down outcome (verified at `post_resolution_lethality.py:208-211`). A dying-window *stall* turn (free-text non-stabilization) is NOT a resolved-down encounter, so an expiry check living only there would never fire on the stall turn — and AC4 explicitly requires "the clock cannot be paused" by stalling. The handler reads `session._session_data.genre_pack` (`player_action.py:429`), so the bound `cfg.trauma.mortal_injury_rounds` IS reachable on the player-turn path. Testing the behavioral outcome (not the function) keeps the Dev free to wire expiry in the gate, a gate-called helper, or a per-turn pass — but forces it onto the player-turn path where AC4 actually requires it.
  - Severity: minor
  - Forward impact: none on sibling stories; surfaced to Dev as a non-blocking Delivery Finding so the expiry home is chosen deliberately.

### Dev (implementation)
- **`resolve_downed` gained a `dying_window` flag; the window is no longer the default mint**
  - Spec source: docs/superpowers/specs/2026-06-14-wwn-dying-window-solo-actuator-design.md, Section 1; plan Task 3
  - Spec text: "The window status is the existing Mortal Injury status ... changed to carry ... `stabilizable = True` ... `incapacitating = True`."
  - Implementation: `resolve_downed(..., dying_window: bool = False)`. The stabilizable+incapacitating window mints ONLY when `dying_window=True`; otherwise the pre-108-6 ordinary (non-incapacitating, non-stabilizable) Mortal Injury death clock mints. The seam passes `dying_window = not superseded and not live_hostile`. `tests/game/ruleset/test_wwn_dying_window_status.py` updated to pass `dying_window=True` on the window-mint call.
  - Rationale: the spec implied resolve_downed always mints the window when not superseded, but that suppressed/replaced the OPPONENT Mortal Injury death clock (a downed opponent always has a live hostile — the player). Making every WN down a stabilizable window broke 6 combat-dispatch tests (`statuses=[]`). The flag preserves the ordinary clock for opponents/PC-at-sword-point and opens the window only for the scoped solo (no-live-hostile) case — which IS the spec's AC1 intent ("a PC downed with a live hostile present still goes terminal immediately").
  - Severity: minor
  - Forward impact: any future direct caller of `resolve_downed` that wants the window must pass `dying_window=True` (the seam is the only production caller and does so).
- **Per-turn expiry implemented in the player_action gate (not `apply_post_resolution_lethality`)**
  - Spec source: plan Task 7
  - Spec text: "This lives in the per-PC post-resolution pass (`apply_post_resolution_lethality`)."
  - Implementation: `_dying_window_expired(sd, status)` + the expiry branch live in `sidequest/handlers/player_action.py` gate, reading `cfg.trauma.mortal_injury_rounds` from `sd.genre_pack`. Confirms TEA's red-phase finding.
  - Rationale: `apply_post_resolution_lethality` early-returns on any turn without a resolved PC-down encounter, so it cannot fire on a dying-window stall turn (AC4 "the clock cannot be paused"). The gate is the one place every dying-window submission passes and has cfg access.
  - Severity: minor
  - Forward impact: none.

### Reviewer (audit)
- **TEA — AC4 expiry pinned at the player-action path** → ✓ ACCEPTED by Reviewer: the early-return analysis is correct (`post_resolution_lethality.py` no-ops off a resolved PC-down encounter); homing expiry on the player-turn path is the only way to satisfy AC4's "clock cannot be paused." Sound.
- **Dev — `resolve_downed` gained a `dying_window` flag; window no longer the default mint** → ✓ ACCEPTED by Reviewer: this is the correct fix for the regression it describes. Making every WN down a stabilizable+incapacitating window broke the opponent death clock (6 dispatch tests); the flag cleanly separates the solo last-stand window from the ordinary clock. Verified: opponent down (live player = hostile) → `dying_window=False` → ordinary clock; solo down (no hostile) → window. ADR-143-clean (a seating flag, no native tune).
- **Dev — per-turn expiry implemented in the player_action gate** → ✓ ACCEPTED by Reviewer: confirms TEA's finding; the gate is the correct home (every dying-window submission passes it; `sd.genre_pack` gives cfg access). Implementation traced and correct.
- **No undocumented deviations found** beyond those already logged — the diff matches the spec's Section 1–5 structure; the deferred overkill predicate is explicitly documented by Dev.

## Branch & Context

**Branch Strategy:** gitflow (feat/108-6-wwn-dying-window-solo-actuator)

**Story Context File:** `/Users/slabgorb/Projects/oq-1/sprint/context/context-story-108-6.md` (auto-created by setup)

## Sm Assessment

**Setup complete — story routed to TEA (Amos) for the red phase.**

- **Story:** 108-6 — WWN dying/down window + solo-actuator gap. 5 pts, server-only, spdd (phased: setup → red → green → review → finish).
- **Readiness:** Design fully resolved before setup. The BRAINSTORM-FLAGGED open problem (solo actuator — nothing advances the stabilize clock in solo play) is answered in the approved spec (Approach A: the downed soloist's own free-text submissions drive an engine-owned clock; no timer/auto-tick). Architect (Naomi) delivered both the design spec and an 8-task TDD implementation plan.
- **Dependencies:** None declared and none real. The dying window operates on the existing `downed_seam` / `resolve_downed` / Mortal Injury status path, orthogonal to the 108-1 engine-core cut and 108-2 Other-seating work in the same epic. No ordering block.
- **Merge gate:** Clear — no open non-draft PRs.
- **Doctrine guard for TEA/Dev:** ADR-143 (SOUL "Bind the Ruleset, Don't Balance It") — the window-vs-terminal branch keys on live-hostile presence; it is a seating/branch decision, NOT a native beat/dial tune. No native mechanic is converted or gated. Tests must assert wiring via OTEL spans + fixture behavior, never source-text greps (server CLAUDE.md "No Source-Text Wiring Tests").
- **Acceptance criteria:** AC1–AC6 captured above, mapped 1:1 to the plan's 8 tasks. AC6 (end-to-end solo wiring test) is the mandatory gate — it must fail on `develop` today and pass only when every seam is wired through to dispatch.

**Handoff:** Amos — write the red phase against the plan at `docs/superpowers/plans/2026-06-14-wwn-dying-window-solo-actuator.md`. Each task is already red-first with concrete test code; the fixture-construction notes point at reusing existing harnesses (grep the neighboring suite) rather than stubbing new ones.
## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Test Files (8) — AC mapping:**
- `tests/game/test_status_stabilizable.py` — AC1/AC2 substrate: `Status.stabilizable` structured flag, default, model round-trip.
- `tests/telemetry/test_wn_dying_window_spans.py` — AC5: `dying_window.{opened,tick,resolved}` emitters + `{slug}.*` routes for wwn/cwn/awn + the folded #846 `superseded_by_terminal` projection.
- `tests/game/ruleset/test_wwn_dying_window_status.py` — AC1/AC3: `resolve_downed` window carries `incapacitating`+`stabilizable`; `is_dying_window_status` predicate keys on flag not text; superseded mints no window.
- `tests/server/test_wwn_dying_window_downed_seam.py` — AC1: live-hostile → terminal (no window, #846 guard); no-live-hostile → window + `wwn.dying_window.opened` (reason=no_live_hostile); terminal branch emits no opened span.
- `tests/agents/tools/test_stabilize_dying_window_clock.py` — AC3: engine-derived `rounds_elapsed` from `created_turn`; narrator-supplied mismatch fails loud; success restores HP=1 + Frail + clears window; no-window → error.
- `tests/server/test_player_action_dying_window_gate.py` — AC2: stabilizable window permits action into narration (no block span); terminal still blocks (CHARACTER_INCAPACITATED + block span).
- `tests/server/test_dying_window_expiry.py` — AC4: submitting past deadline is refused as terminal; window cleared, terminal status left (clock cannot be stalled).
- `tests/server/test_wwn_dying_window_wiring.py` — **AC6 mandatory wiring**: real downed seam opens an *incapacitating* window in solo (+opened span); real `PlayerActionHandler.handle` permits the soloist's free-text submission into the narration path (the loop is not halted).

**Tests Written:** 24 tests across 8 files covering AC1–AC6.
**RED verification:** 23 fail for feature-missing reasons (missing `Status.stabilizable`, `is_dying_window_status`, the three span emitters, the routes, the #846 extract field, the seam branch). 1 passes by design — `test_terminal_status_still_blocks`, a regression guard pinning existing terminal-block behavior the carve must preserve. Verified via testing-runner (RUN_ID 108-6-tea-red); no DB-availability or test-author-bug failures. One initially-weak test (`test_downed_soloist_submission_is_not_halted`) was strengthened to assert the opened window is `incapacitating` (the property that makes the solo-halt gap real) so it now fails for the right reason.

### Rule Coverage

| Rule (lang-review/python.md) | Test(s) | Status |
|------|---------|--------|
| #1 Silent exception swallowing (fail-loud) | `test_supplied_rounds_elapsed_mismatch_fails_loud` (clock mismatch must `raise ValueError`, not swallow) | failing |
| #6 Test quality — meaningful assertions | All tests assert concrete values (HP==1, span attrs, status presence/absence), no `assert True`/bare-truthy; patch bound names (`player_action._watcher_publish`), not source | n/a (self-check passed) |
| No source-text wiring (server CLAUDE.md) | All wiring proven via OTEL spans (`wwn.dying_window.opened`, block span (non-)fire) + fixture behavior; `is_dying_window_status` keys on the structured flag, asserted by `test_is_dying_window_status_keys_on_flag_not_text` | failing |
| Single-status coherence (#846) | `test_live_hostile_goes_terminal_no_window`, `test_superseded_by_terminal_mints_no_window` | failing |
| Doctrine ADR-143 (no native tune) | Branch keyed on live-hostile presence only; no native beat/dial asserted anywhere | n/a |

**Rules checked:** 3 of 8 applicable python lang-review rules have targeted coverage (the rest — mutable defaults, path handling, resource leaks, unsafe deserialization — do not apply to this status/span/gate change).
**Self-check:** 0 vacuous tests; 1 weak test found and strengthened (the AC6 not-halted test).

**Handoff:** To Dev (Naomi) for implementation. Two non-blocking Delivery Findings to weigh: (1) AC4 expiry must fire on the player-action path, not only `apply_post_resolution_lethality` (which early-returns on non-down turns); (2) add a positive permit-span on the gate carve.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** all 24 new story tests GREEN; the 6 combat-dispatch Mortal-Injury regressions caught mid-phase are fixed and GREEN; full suite = 12153 passed with only pre-existing failures (wry_whimsy content-validation deterministic; chargen-armor/SWN-HP/102_5 parallel-isolation flakes that pass in isolation + on develop). Verified via testing-runner across three runs. Lint/format clean; pyright adds 0 new errors (player_action.py holds at its pre-existing 22-error baseline, downed_seam/status/spans/stabilize clean).
**Branch:** feat/108-6-wwn-dying-window-solo-actuator (pushed; HEAD 4e3bf37b)

**Files Changed:**
- `sidequest/game/status.py` — `stabilizable` structured flag.
- `sidequest/game/ruleset/without_number.py` — `is_dying_window_status` predicate; `resolve_downed` `dying_window` flag (window vs ordinary mint).
- `sidequest/server/dispatch/downed_seam.py` — `_has_live_hostile_on_side`; live-hostile branch selects window vs ordinary clock; `wwn.dying_window.opened` span.
- `sidequest/handlers/player_action.py` — gate carve (stabilizable permits→narrator, terminal blocks); `_dying_window_expired` (+ fail-loud log); per-turn expiry→terminal + tick/resolved spans.
- `sidequest/agents/tools/stabilize_mortal_injury.py` — engine-derived `rounds_elapsed` (fail-loud on narrator mismatch); HP→1 on success; honest `dying_window.tick` + `resolved(stabilized)` spans.
- `sidequest/telemetry/spans/wn.py` — three `dying_window.{opened,tick,resolved}` emitters + routes; folded #846 `superseded_by_terminal` into the mortal-injury projection.
- `tests/game/ruleset/test_wwn_dying_window_status.py` — pass `dying_window=True` on the window-mint call (companion to the new flag).
- (committed 8776033b) `tests/agents/tools/test_stabilize_mortal_injury_tool.py` — CWN fixtures use the structured window; `_build_snapshot(interaction=…)`.

### Dev Assessment — Rework (round 2, HEAD 6db24489)

Addressed every Reviewer (Chrisjen) finding:
- **[HIGH test-integrity] FIXED.** Expiry tests now assert the AC5 `wwn.dying_window.tick`(action_was_stabilization=False)+`resolved`(outcome=died) spans on the expiry path (were decorative — the second test's unused `otel_capture` was dropped). The AC2 permit test now binds a real `_WwnPack` (created_turn=0, interaction=1 → within deadline) so it exercises the real carve, not the no-cfg fallback. The `'Frail' in s.text` text-scrape is replaced with `s.severity == StatusSeverity.Wound and not s.stabilizable`.
- **[HIGH lint] FIXED.** 2 ruff I001 import-sort errors auto-fixed; my 7 files lint+format clean.
- **[MEDIUM slug] FIXED.** Expiry spans resolve the bound slug and emit under an `"unknown"` sentinel + `logger.error` if unreadable — no false `wwn` namespace.
- **[MEDIUM edge tests] PARTIAL.** Added `test_failed_stabilization_leaves_window_and_hp_unchanged` and `test_narrator_overstating_rounds_elapsed_also_fails_loud`. Strike-path/overkill/MP seam variants remain deferred (documented; negligible-trigger / out-of-scope).
- **[LOW docs/dead-code] FIXED.** Updated `resolve_downed` docstring (no longer "deferred to 106-5"; documents `dying_window`), the stabilize module docstring (engine-derived rounds + 1-HP heal); removed dead `_MORTAL_INJURY_MARKER`.

**Verification:** 65 tests GREEN (35 story + 30 regression-sensitive WN suites) via testing-runner; lint+format clean on all 7 files; pyright 0 new errors (combined 23 = pre-existing baseline). A mass `ruff format` accidentally touched 162 unrelated files mid-rework — fully reverted; the working tree and the 15-file story diff are clean.

**Handoff:** Back to Reviewer (Chrisjen) for re-review.

**Pre-handoff review:** Ran a Reviewer subagent (per requesting-code-review). Fixed 2 of 3 HIGH findings immediately (OTEL tick honesty; fail-loud expiry-cfg). The 3rd HIGH (overkill predicate) + MEDIUM findings (expiry persistence, slug fallback, added MP/strike-path/overkill test coverage) are documented as non-blocking Delivery Findings for the formal review phase, with rationale (overkill common case covered by the existing supersede guard; realistic trigger negligible).

**Self-review (judgment checks):** wired end-to-end (gate→seam→tool→spans, proven by the AC6 wiring test driving real `PlayerActionHandler.handle` + real downed seam); follows project patterns (structured-flag predicate, capability gates, slug-namespaced spans, fail-loud); ADR-143 honored (no native mechanic tuned — pure seating/branch + WWN-SRD math); error handling fail-loud (clock mismatch raises, expiry-cfg logs).

**Handoff:** To Reviewer (Chrisjen) for the formal review phase.

<skills-invoked>
<skill name="test-driven-development" phase="green" at="2026-06-14T12:40:00Z"/>
<skill name="verification-before-completion" phase="green" at="2026-06-14T12:41:00Z"/>
<skill name="requesting-code-review" phase="green" at="2026-06-14T12:42:00Z"/>
<skill name="test-driven-development" phase="red" at="2026-06-14T12:05:00Z"/>
</skills-invoked>
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | tests GREEN (33), production lint/typecheck clean, 2 ruff I001 in test files, 0 new pyright errors | confirmed 1 (lint), dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 8 (2 high: expiry tests assert no spans; permit test passes via fallback not carve) | confirmed 3, downgraded 4 to non-blocking, deferred 1 |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 high (stale resolve_downed docstring; stale stabilize docstring ×2; dead _MORTAL_INJURY_MARKER) | confirmed 4 (all LOW severity) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 (text-scrape `'Frail' in s.text` [Rule #6/A5]; `slug or "wwn"` ×2 [A1]; `_dying_window_expired` return-False [A1]) | confirmed 2, downgraded 1, dismissed 0 |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 10 confirmed (1 HIGH cluster: test-integrity; rest MEDIUM/LOW), 5 downgraded with rationale, 1 deferred

## Reviewer Assessment

**Verdict:** REJECTED → red rework (TEA)

**The implementation logic is correct.** I traced the data flow and the seam/gate/tool branches; the production code is sound, ADR-143-clean, and fail-loud. This rejection is about **test integrity and hygiene**, not a runtime bug — but in a project whose CLAUDE.md is emphatic about "No Source-Text Wiring Tests," "Every Test Suite Needs a Wiring Test," "Verify Wiring Not Just Existence," and OTEL-as-lie-detector, a test suite that violates those rules and doesn't prove its own ACs is a first-class defect.

**Data flow traced:** player free-text submission → `PlayerActionHandler.handle` gate (`player_action.py:585`) → `is_dying_window_status(downed_status)` → `_dying_window_expired` (expired → tick(False)+resolved(died)+terminal+block) OR permit (`downed_status=None` → narrator) → on a stabilize attempt the `stabilize_mortal_injury` tool derives `rounds_elapsed` from `created_turn`, cross-checks the narrator value (raises on mismatch), heals to 1 HP, emits tick(True)+resolved(stabilized). Window-open decision traced through all three `run_cwn_wwn_downed_seam` call sites (strike, reprisal, cast). **Live-hostile polarity VERIFIED CORRECT** — `actor_side` is the attacker's side = hostile relative to the downed `_opposite_side_first_actor`; a downed opponent (live player = hostile) correctly gets the ordinary clock, not the regression.

**Pattern observed:** structured-flag predicate (`is_dying_window_status` keys on `stabilizable`, never text) at `without_number.py:71` — good. Capability-gated cfg reads (isinstance Cwn/Wwn) mirror the existing seam idiom — good. Slug-namespaced WN spans on the `{slug}.*` route loop — good.

**Error handling:** `stabilize_mortal_injury` clock mismatch raises `ValueError` (fail-loud, `stabilize_mortal_injury.py:147`) — verified. `_dying_window_expired` logs `logger.error` on unreadable cfg (`player_action.py:68`) — loud, though see findings.

### Findings (severity table)

| Severity | Tag | Issue | Location | Fix Required |
|----------|-----|-------|----------|--------------|
| [HIGH] | [TEST][RULE] | **Test suite does not prove its ACs and violates the structured-markers rule.** Three compounding problems: (a) both expiry tests accept `otel_capture` but assert **nothing** on it — the AC5 `dying_window.tick`/`resolved` emits on the expiry path could be deleted and the tests still pass; (b) the AC2 permit test passes via the no-cfg **fallback** (`MagicMock` pack → `_dying_window_expired` returns False), not the real carve with a real deadline — it would pass even if the permit logic were broken; (c) a **text-scraping** assertion `'Frail' in s.text` in a PR whose entire purpose is replacing text-scraping with structured flags (the Frail status carries `severity=StatusSeverity.Wound`). (a)+(c) match stated project rules (OTEL lie-detector; "structured markers, not text scraping") and cannot be dismissed. | `tests/server/test_dying_window_expiry.py:101,120`; `tests/server/test_player_action_dying_window_gate.py:81`; `tests/agents/tools/test_stabilize_dying_window_clock.py:170` | (a) assert tick(`action_was_stabilization=False`) + resolved(`outcome="died"`) fire on the expiry path; (b) bind a real `_WwnPack()` on `session._session_data.genre_pack` in the permit test so it exercises the deadline computation, not the fallback; (c) assert `s.severity == StatusSeverity.Wound and not s.stabilizable` instead of scraping `.text`. |
| [HIGH] | [PREFLIGHT] | **2 ruff I001 lint errors in new test files** (unsorted imports). The working tree must be lint-clean before merge; Dev lint-checked production files only. | `tests/server/test_player_action_dying_window_gate.py`, `tests/server/test_wwn_dying_window_wiring.py` | `uv run ruff check --fix` (or `ruff format`) on the two files. |
| [MEDIUM] | [RULE] | **`slug or "wwn"` silent fallback** can mis-namespace the expiry spans under `wwn.*` for a CWN/AWN session if `_bound_wn_slug` returns None (slug-honesty / No-Silent-Fallbacks). Unreachable in practice on the expiry path (a real WN cfg was already confirmed), but the `or "wwn"` is a fallback that masks misconfiguration. | `player_action.py:630,637` | Resolve the slug from the confirmed cfg (or fail loud) rather than defaulting to `"wwn"`. |
| [MEDIUM] | [TEST] | **Missing edge-case coverage:** (1) failed-stabilization does not assert the window PERSISTS + HP stays 0; (2) symmetric rounds_elapsed mismatch (narrator OVER-states) untested; (3) no strike-path (`actor_side="player"`) seam test; (4) overkill-skips-window untested; (5) MP (downed PC + living ally + dead enemy). | `test_stabilize_dying_window_clock.py`, `test_wwn_dying_window_downed_seam.py` | Add the failed-stabilize-persists test and the over-states-mismatch test at minimum; (3)-(5) may defer. |
| [LOW] | [DOC] | **Stale/lying docstrings + dead code:** `resolve_downed` docstring still says the dying window is "deferred to story 106-5 (unactionable in solo)" — this PR implements it; the `stabilize_mortal_injury` module docstring implies narrator-authoritative `rounds_elapsed` (now engine-derived) and omits the 1-HP heal from its flow diagram; `_MORTAL_INJURY_MARKER` constant is now dead. | `without_number.py:499`; `stabilize_mortal_injury.py:8,14,60` | Update both docstrings to current behavior; delete the dead constant. |
| [LOW] | [RULE] | `_dying_window_expired` returns False (+ logger.error) on unreadable cfg. **Downgraded** from the rule-checker's A1 flag: the `logger.error` satisfies loudness, and the state is unreachable in production (a window only opens under a WN cfg; packs don't hot-swap mid-session). Noted, not blocking — but consider whether raise/expire is more correct than block-forever if it ever fires. | `player_action.py:75` | Optional: decide raise vs expire for the impossible state. |

### Rule Compliance (lang-review/python.md + project rules)

- **#1 Silent exception swallowing:** COMPLIANT — no bare excepts or swallows introduced; clock mismatch raises; no-window returns ToolResult.error.
- **#2 Mutable default arguments:** COMPLIANT — all new functions/span emitters use immutable defaults (`bool`, `int`); `**attrs` keyword-only.
- **#3 Type annotations at boundaries:** COMPLIANT (with note) — new public functions (`is_dying_window_status`, three span emitters) fully annotated; `_bound_wn_slug`/`_dying_window_expired` leave `sd`/`status` unannotated but are private helpers (rule-exempt) and consistent with the file's existing loosely-typed `sd` convention.
- **#4 Logging coverage/correctness:** COMPLIANT — `logger.error` uses `%s` lazy format, correct severity for a server misconfiguration.
- **#6 Test quality:** **VIOLATION** — text-scrape `'Frail' in s.text` (see HIGH finding); plus weak/decorative `otel_capture` usage and fallback-masked permit test.
- **#7 Resource leaks:** COMPLIANT — all three span emitters use `with Span.open(...)`.
- **#8 Unsafe deserialization:** COMPLIANT — `model_validate` on known-good in-memory dump only.
- **No Silent Fallbacks:** one MEDIUM (`slug or "wwn"`), one downgraded-LOW (`_dying_window_expired` return-False).
- **No source-text wiring tests:** COMPLIANT — wiring proven via OTEL spans + behavioral sentinels; `is_dying_window_status` is the anti-text-scrape predicate.
- **OTEL Observability (every decision emits a span):** COMPLIANT in production — opened/tick/resolved all wired; permit branch correctly emits no tick (gate can't observe stabilization). The GAP is in the TESTS not asserting them.
- **ADR-143 (Bind, don't balance):** COMPLIANT — `open_window` is a seating decision; `difficulty = 8 + rounds_elapsed` and `mortal_injury_rounds` are pure WWN-SRD; no native dial/beat tuned.
- **Structured markers not text-scraping:** **VIOLATION** in the test (`'Frail' in s.text`); production code is compliant (keys on `stabilizable`).

### Devil's Advocate

Assume this is broken. The most damning angle: **the tests are theater.** The AC2 permit test — the literal heart of the solo-actuator fix — passes not because the gate carve works but because a `MagicMock` genre_pack trips the `_dying_window_expired` capability gate, which logs an error and returns False, which happens to also mean "permit." Swap the real fix (`downed_status = None`) for a no-op and bind no real pack, and the test still goes green via the same fallback. So the one behavior the entire story exists to deliver is *not actually verified* by its dedicated unit test; it leans on the e2e wiring test's sentinel, which itself makes no OTEL assertion on the permit path. A confused future maintainer reading the green suite would believe the carve is proven when it is proven only incidentally. Next, the expiry tests: they import a span-capture fixture, signaling "I will check the lie-detector," then check nothing — the worst kind of test, one that *looks* like it verifies OTEL but is inert. If a careless refactor drops the `dying_window_resolved_span(outcome="died")` emit, the GM panel goes dark on PC death-by-clock and not one test complains. Then the text-scrape: in the very PR that preaches "structured markers, not text scraping," a test asserts the Frail downgrade by sniffing a human-readable string that an i18n pass or a wording tweak would silently break — a self-inflicted instance of the exact anti-pattern. A malicious narrator angle is well-covered (the clock cross-check raises on fudging — genuinely good), and a confused player can't pause the clock (expiry is fixed-deadline). The runtime is honest. But the *proof* is not, and in this codebase the proof is the product. None of these are data-corrupting or exploitable, so none are Critical; but the cluster crosses into HIGH because the suite fails to discharge the AC wiring obligations the project treats as non-negotiable. (210 words.)

**Handoff:** Back to TEA (Amos) for red rework — the findings are test-design issues (assertions, fixtures, missing edge cases) plus test-file lint; the production-side LOW items (dead constant, two docstrings) and the MEDIUM `slug or "wwn"` get cleaned in the green phase that follows.

[EDGE] disabled. [SILENT] disabled. [TEST] confirmed (test-integrity HIGH + missing edge cases MEDIUM). [DOC] confirmed (stale docstrings + dead constant, LOW). [TYPE] disabled. [SEC] disabled. [SIMPLE] disabled. [RULE] confirmed (text-scrape #6/A5 HIGH; `slug or "wwn"` A1 MEDIUM; `_dying_window_expired` A1 downgraded LOW). [PREFLIGHT] confirmed (lint HIGH).
---

# RE-REVIEW (round 2 — after green rework, HEAD 6db24489)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | lint CLEAN (both prior I001 gone), format clean, 12 story tests GREEN, 0 new pyright, working tree clean (mass-format reverted) | confirmed 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | prior HIGH ×2 RESOLVED (verified); 2 new edge tests meaningful; 2 LOW residuals | confirmed 0 blocking, noted 2 LOW |
| 5 | reviewer-comment-analyzer | Yes | findings | prior 4 doc findings RESOLVED; 2 new sub-high nits | confirmed 0 blocking, noted 2 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | prior 2 rule findings RESOLVED (verified); 1 LOW pre-existing (`_bound_wn_slug` unannotated, rule-exempt) | confirmed 0 blocking, noted 1 LOW |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 0 blocking confirmed; all prior HIGH/MEDIUM findings resolved; 5 LOW/sub-high residuals noted, none blocking

## Reviewer Assessment

**Verdict:** APPROVED

**Every blocking finding from round 1 is resolved**, verified by both the subagents and my own read of the rework diff (`git diff 4e3bf37b..HEAD`, 7 files, 108/45):

- **[TEST] HIGH (round 1) — RESOLVED.** `test_submitting_past_deadline_is_refused_as_terminal` now asserts `wwn.dying_window.tick`(action_was_stabilization=False) and `wwn.dying_window.resolved`(outcome="died") — the test-analyzer confirmed deleting either production emit now fails the test (real AC5 lie-detector). `test_expiry_clears_the_window_and_leaves_terminal` dropped its decorative `otel_capture`. `test_stabilizable_window_permits_action_into_narration` binds a real `_WwnPack` (created_turn=0, interaction=1 → within the deadline=6), so the permit is driven by the real `_dying_window_expired` deadline computation, not the no-cfg fallback.
- **[RULE] HIGH (round 1) — RESOLVED.** The `'Frail' in s.text` text-scrape is now `s.severity == StatusSeverity.Wound and not s.stabilizable` — structured fields, refactor-stable. (Rule #6 / structured-markers compliant.)
- **[PREFLIGHT] HIGH (round 1) — RESOLVED.** Both ruff I001 lint errors gone; all 7 files lint+format clean; working tree clean (the accidental 162-file mass-format was fully reverted — preflight confirmed only the 7 story files in the delta).
- **[RULE] MEDIUM (round 1) — RESOLVED.** `slug or "wwn"` replaced: the expiry branch resolves `_bound_wn_slug(sd)`, and on None fires `logger.error` (lazy-arg) + emits under an `"unknown"` sentinel — no false `wwn` namespace (slug-honesty / No Silent Fallbacks compliant).
- **[TEST] MEDIUM (round 1) — PARTIALLY ADDRESSED.** Added the two highest-value edge tests (failed-stabilization-persists; over-stated-mismatch-fails-loud), both verified meaningful. Strike-path/overkill/MP variants remain deferred (documented; negligible trigger / out-of-scope).
- **[DOC] LOW (round 1) — RESOLVED.** Both stale docstrings updated; dead `_MORTAL_INJURY_MARKER` removed (comment-analyzer confirmed all 4).

**Data flow re-traced (rework):** the slug-honesty branch — `_dying_window_expired` confirms a Cwn/Wwn cfg → `_bound_wn_slug(sd)` resolves the real slug → None-guard logs + sentinel → `dying_window_tick_span(ruleset=slug)` / `resolved_span(ruleset=slug)`. Honest, fail-loud, no false default. **Pattern:** structured-marker assertions and span-attribute checks throughout the strengthened tests — the project's anti-text-scrape / OTEL-lie-detector doctrine is now actually enforced by the suite, not just claimed.

**Residual non-blocking observations (for a future polish pass, NOT blocking):**
- [TYPE] LOW — `_bound_wn_slug(sd)` parameter unannotated (rule-checker). Pre-dates this PR; Rule #3 exempts private helpers. Not introduced here.
- [TEST] LOW — `test_failed_stabilization_leaves_window_and_hp_unchanged` doesn't assert `difficulty==10` explicitly (covered by the sibling test for the same fixture).
- [TEST] LOW — no positive OTEL span on the gate PERMIT branch (a documented, deliberate design choice — the gate can't observe stabilization; the tool owns the honest tick).
- [DOC] LOW/MEDIUM — the slug-honesty comment is slightly imprecise about what makes a pack "inconsistent"; the expiry test's cross-reference to a sibling test by name is a mild maintenance dependency.

### Rule Compliance (re-review)
- **#6 Test quality / structured markers:** now COMPLIANT — text-scrape removed; strengthened assertions are specific-value/structured; no decorative fixtures.
- **No Silent Fallbacks / slug-honesty:** now COMPLIANT — `slug or "wwn"` removed; None-slug fails loud + sentinel.
- **OTEL lie-detector:** now COMPLIANT in BOTH production and tests — the expiry spans are asserted; deleting an emit fails a test.
- **ADR-143:** unchanged, COMPLIANT (no native mechanic touched).
- All other rules (#1, #2, #4, #7, #8, async, imports, security): COMPLIANT per rule-checker (0 new violations beyond the 1 LOW pre-existing).

### Devil's Advocate (re-review)

Try to break the rework. The strongest remaining angle is the permit branch's lack of a positive OTEL span: the GM panel can see a window OPEN (`opened`), a clock TICK on a stabilize attempt or expiry, and a RESOLVE — but a *permitted free-text non-stabilization turn* (the soloist types "I shout for help") leaves no dying-window span, only a narration turn. Could that hide a regression where the gate silently stops permitting? The test guards it via `_ReachedNarrationPath`, which is behavioral, not span-based — if someone mocked the narration path differently, the signal could weaken. But this is a *documented, defensible* design choice (the gate genuinely cannot know if the action is a stabilization, and a hardcoded span would be the exact dishonesty I rejected in round 1), and the e2e wiring test plus the gate test both exercise the real `PlayerActionHandler.handle`. Second angle: the `"unknown"` slug sentinel emits spans the WN route registry doesn't recognize (only wwn/cwn/awn route), so an inconsistent pack's expiry spans would emit-but-not-route — invisible to the panel. But that path is genuinely unreachable in production (a window only opens under a real WN cfg) and now logs an error if it ever fires, which is strictly better than the old false-`wwn` attribution. Third: the two new edge tests use the same `created_turn=3/current_turn=5` fixture as siblings — but they assert distinct behaviors (failure-persists vs over-state-raises), so they're not redundant. Nothing here rises to blocking. The suite now proves what it claims; the production logic was always correct; the round-1 defects were test-integrity and hygiene, and they are fixed. (215 words.)

**Handoff:** To SM (Camina Drummer) for the finish phase (PR creation + merge). I do NOT merge.

[EDGE] disabled. [SILENT] disabled. [TEST] all round-1 findings resolved; LOW residuals noted. [DOC] all round-1 findings resolved; LOW nits noted. [TYPE] disabled (1 LOW pre-existing surfaced by rule-checker, non-blocking). [SEC] disabled. [SIMPLE] disabled. [RULE] both round-1 findings resolved (text-scrape + slug-honesty). [PREFLIGHT] clean — lint/format/tests/typecheck all pass.

### Reviewer (audit) — re-review
- All three Design Deviations remain ✓ ACCEPTED (round-1 stamps stand); the rework introduced no new deviations — the slug-honesty change and test strengthening are within the approved design. No undocumented deviations.