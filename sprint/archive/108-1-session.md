---
story_id: "108-1"
jira_key: ""
epic: "108"
workflow: "tdd"
---
# Story 108-1: Engine core cut — run_wn_round() resolves the player's WN action without native apply_beat() scaffolding

## Story Details
- **ID:** 108-1
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** server

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-14T10:33:34Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-14T07:51:32Z | 2026-06-14T07:53:16Z | 1m 44s |
| red | 2026-06-14T07:53:16Z | 2026-06-14T08:21:31Z | 28m 15s |
| green | 2026-06-14T08:21:31Z | 2026-06-14T10:22:08Z | 2h |
| review | 2026-06-14T10:22:08Z | 2026-06-14T10:33:34Z | 11m 26s |
| finish | 2026-06-14T10:33:34Z | - | - |

## SM Assessment

**Story:** 108-1 — Engine core cut: `run_wn_round()` resolves the player's committed WN action with pure WN math, no native `apply_beat()` scaffolding under a `WithoutNumberRulesetModule` binding.

**Doctrine context (load-bearing):** This is the implementation of Keith's emphatic 2026-06-14 standing ruling (ADR-143; SOUL "Bind the Ruleset, Don't Balance It"). We bind Without Number so we never have to balance combat. The native engine is *removed* from the WN path, not layered under it and tuned. Any instinct to convert/gate/tune a native mechanic to "make it work with" WN is the exact dead end the binding deletes — stop and cut it instead.

**Scope for RED (TEA / Fezzik):**
- Tests must pin that under a WN binding, `run_wn_round()` resolves attack/full-defense/move/item-use/cast via WN math (d20+hit vs AC, weapon dice, Shock, saves).
- Tests must assert the native riders do NOT fire: no fleeting-tag grant (Opening/Counter Stance), no dial-metric advance, no composure rider, no Brace-as-an-action.
- Assert OTEL span `wn.native_scaffolding_suppressed` is emitted (the GM-panel lie-detector that the native engine is OFF). Per project OTEL principle, this span is mandatory, not optional.
- A regression guard: the native module path for native (non-WN) packs is unchanged — native riders still fire there.

**Seam (for orientation, not prescription):** `dispatch/dice.py` ~671-676 + the `run_wn_round()` beat-resolution path; `isinstance(WithoutNumberRulesetModule)` gate.

**Repo:** sidequest-server only, branch `feat/108-1-wn-round-engine-core-cut` off `develop`. No Jira (personal project) — claim explicitly skipped.

**Watch for stale-tree traps:** WN module wiring has 3 touchpoints reviews keep catching (spans `__init__` re-export, `dice.py` downed-seam guard + `_physical_save_target_for` isinstance, OTEL span-assertion tests). Don't assume "still broken" on a measured failure — verify the running tree, not a stale one.

**Decision:** Ready for RED. Gate satisfied — session exists, fields set, context written (epic + story), branch created, Jira skip explicit. → Fezzik (TEA).

## TEA Assessment (RED)

**Suite:** `sidequest-server/tests/integration/test_108_1_wn_native_scaffolding_cut.py` (real-pack, heavy_metal=wwn; skips when sidequest-content absent). Committed `0fc4b31f`.

**RED verified:** `3 failed, 3 passed` (env `SIDEQUEST_DATABASE_URL` set; `-n0`). The 3 failures are the new behavior; the 3 passes are guards that must STAY green.

**The cut, in one observable:** a d20 face-20 strike → `RollOutcome.CritSuccess` → the native `strike` rule (`beat_kinds.DEFAULT_DELTAS[BeatKind.strike][CritSuccess]`) mints the **"Opening"** fleeting tag onto `encounter.tags`. That tag is the deterministic lie-detector for "native engine resolved this action." After the cut it must not appear, and `wwn.native_scaffolding_suppressed` must fire.

**RED tests (must go green):**
1. `…grants_no_native_fleeting_tag` — no "Opening"/"Counter Stance" on `enc.tags` after a WN CritSuccess strike. (Fails today: native `apply_beat` mints "Opening".)
2. `…emits_native_scaffolding_suppressed_span` — `wwn.native_scaffolding_suppressed` fires, slug-honest (`wwn.*`, never `native.*`/`cwn.*`). (Fails today: span absent.)
3. `…suppresses_native_scaffolding_end_to_end` (WIRING) — both, driven through `WebSocketSessionHandler.handle_message(DICE_THROW)`. (Fails today: span absent; `encounter.tag_created` present in the wire span dump = "Opening" minted.)

**Green guards (must STAY green):**
4. `…strike_still_removes_opponent_hp` — WN weapon damage intact (opponent HP drops). Don't throw out the WN math with the native riders.
5. `…native_engine_apply_beat_still_grants_opening` — `beat_kinds.apply_beat` itself unchanged: the cut belongs at the **call site** in `run_wn_round`, NOT inside `beat_kinds` (editing the engine regresses every native pack).
6. `…native_module_is_not_a_without_number_module` — `isinstance(Native…, WithoutNumberRulesetModule)` is False, WWN is True: the gate Dev should use excludes native packs.

**Guidance for Dev (Inigo):**
- **Where:** the player-beat resolution inside `run_wn_round` (`dispatch/wn_round.py` ~381, the `_apply_committed_player_beat` call) is the only WN-reached path. The shared `_apply_committed_player_beat` is ALSO called by the legacy immediate path (`dispatch/dice.py:764`, native + SWN-no-initiative space_opera/71-21) — do **not** suppress there. Scope the cut to the WN path / `isinstance(WithoutNumberRulesetModule)`.
- **What "native scaffolding" is here:** `ruleset.apply_beat()` → `beat_kinds.apply_beat` (fleeting tags, dial advance via `encounter.metric_advance`, composure rider, Brace). Keep the WN math that already runs *before* `apply_beat` in `_apply_committed_player_beat` (strike damage 2d6→HP, Shock chip, downed seam, WWN cast spine, Killing Blow). The cut removes the `apply_beat` rider call, not the WN damage block.
- **Span name:** the story writes `wn.native_scaffolding_suppressed` as shorthand; the WN family span invariant (`telemetry/spans/wn_round.py`, `WN_FAMILY_SLUGS`, `_require_family_slug`) means the honest emission is `{slug}.native_scaffolding_suppressed` → `wwn.*` for heavy_metal. Register a `SPAN_ROUTES` entry per family slug like the sibling round spans. Tests pin `wwn.native_scaffolding_suppressed`.
- **Watch the 3 WN-wiring touchpoints** ([[project_without_number_module_wiring_checklist]]): spans `__init__` re-export, and OTEL span-assertion coverage.
- **Dials already inert under hp_depletion** ([[project_combat_family_resolution_model]]) — I did NOT add a "dial unchanged" test (it would be vacuously green); the fleeting tag is the live observable.

**Rule coverage:** No-Silent-Fallbacks (suppression is explicit + spanned, not a quiet skip); OTEL Observability Principle (new lie-detector span, asserted at dispatch AND wire level); Wiring test present (mandatory); no source-text/grep assertions (span + behavior only); no vacuous assertions (every test asserts a concrete tag/HP/span/type fact).

**Decision:** RED is real and minimal. → Inigo (Dev) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-server):**
- `sidequest/server/dispatch/dice.py` — added `_resolve_wn_committed_action` (WN-pure HP resolution: weapon dice → `apply_beat_hp_channel`, then `check_hp_depletion`, no native riders) and gated the `ruleset.apply_beat(...)` call in `_apply_committed_player_beat` behind `isinstance(ruleset, WithoutNumberRulesetModule) and cdef.win_condition == "hp_depletion"`. Imports: `ApplyResult`, `wn_native_scaffolding_suppressed_span`.
- `sidequest/telemetry/spans/wn_round.py` — new `wn_native_scaffolding_suppressed_span` + per-family-slug `SPAN_ROUTES["{slug}.native_scaffolding_suppressed"]` (re-exported via the existing `from .wn_round import *`).

**The cut (faithful to ADR-143):** the native beat engine is **not called** under a WN combat binding — not called-then-muted. The WN-pure path reuses the same public HP helpers the native engine used (`apply_beat_hp_channel`, `check_hp_depletion`), so WN damage + the hp_depletion win check are preserved while every native rider (fleeting tag, dial advance, composure/edge, Brace, taunt) is gone. `ApplyResult(deltas=None, …)` flows through the unchanged downstream (downed seam, WWN cast spine, beat_applied telemetry).

**Scope correction (caught by the full suite):** my first gate was `isinstance(WithoutNumberRulesetModule)` alone — too broad. It suppressed the native dial engine for **CWN net-run** (neon_dystopia), breaking 3 `test_neon_net_run_wiring` tests ("move_nodes advances without resolving"). Net-run is a *dial* confrontation under a WN binding, and the epic scope is explicit: **"WN COMBAT only (hp_depletion); dial chase/negotiation confrontations keep the native dial engine."** Added `and cdef.win_condition == "hp_depletion"`. Neon trio green again.

**Tests:** 6/6 GREEN (`tests/integration/test_108_1_wn_native_scaffolding_cut.py`). No regression: serial (`-n0`, no xdist pollution) run of `tests/agents + tests/integration + tests/server/dispatch + tests/telemetry` = **3089 passed, 0 failed** — every WN/SWN/combat/dogfight/narrator-tool test green.

**Full-suite failures are all pre-existing (outside this diff):** `102_5_wn_tool_narrator_wiring` (passes isolated AND serially → xdist flakiness, not mine), 2× pack validators (`wry_whimsy` missing `seed_tropes.yaml` — content gap), `106_1_chargen_armor_wire` (chargen path), `beneath_sunden_room_binding_107_2` (Monster Manual binding, 107 open). None exercise `_apply_committed_player_beat`.

**Branch:** `feat/108-1-wn-round-engine-core-cut` (pushed). **No PR** (SM owns finish).

**Handoff:** To verify phase.

### Dev (implementation)
- No deviations from spec. (The hp_depletion narrowing is not a deviation — the epic scope names "WN COMBAT only (hp_depletion)" explicitly; the story title's bare `isinstance` gate is satisfied as one conjunct.)

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- **Improvement** (non-blocking): the WN-combat cut is now live for ALL WN-family hp_depletion bindings, including **SWN** (space_opera) — not just WWN. Per the epic's WWN-first rollout this is the staged-doctrine direction (swn/cwn/awn "same doctrine, staged"), and the integration suite (incl. space_opera/dogfight SWN tests) stays green because SWN combat content already routes HP through the same channel. 108-3 (content de-nativize WWN combat defs) should confirm whether any SWN pack still authors `resolution_mode: beat_selection` combat that now leans on the cut. *Found by Dev during implementation.*
- **Gap** (non-blocking): `wry_whimsy` fails live content validation + crossref lint — `extension 'seed_tropes' requires missing file 'seed_tropes.yaml'`. Pre-existing, in **sidequest-content** (not this story's repo), but it red-bars `test_pack_validator` / `test_pack_validator_crossref` in the full server suite. Affects `sidequest-content/genre_packs/wry_whimsy/` (add `seed_tropes.yaml` or drop the extension declaration). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): native `apply_beat` advanced `enc.beat` + `enc.structured_phase` (the `_phase_for_beat` ladder) on every player commit, unconditionally — even under `hp_depletion`. The WN cut path (`_resolve_wn_committed_action`) does NOT, and the opponent reprisal never did, so a WN COMBAT encounter now stays frozen at `beat=0 / structured_phase=Setup` for its whole life. Consumed by the narrator scene render (`sidequest/agents/encounter_render.py:29`), the `query_encounter`/`query_scene_state` tools, and the phase→mood-weight map (`encounter.py:70`, Setup=0.70). No correctness break (HP-based resolution intact; nothing re-fires on `beat==0`), but the narrator's escalation/pacing cue is static across a multi-round WWN fight. This is the bookkeeping the epic's "WN combat owns the WN round" goal should grow natively. Affects `sidequest/server/dispatch/dice.py` (`_resolve_wn_committed_action`). *Found by Reviewer during code review.*
- **Gap** (non-blocking): native `apply_beat` stamped `enc.last_beat_impacts[actor.side]` (Story 73-4/73-7/73-8 — the player-facing beat-impact chip, re-stamped with `hp_removed` under hp_depletion so Sebastien/Jade "see the math"). The WN cut path does not stamp it, so the `last_beat_impact` broadcast key (`sidequest/server/dispatch/confrontation.py:489-499`) goes absent for WN combat. Authoritative `player_hp`/`opponent_hp` bars are unaffected — a supplementary-legibility degradation, not a correctness loss. Affects `sidequest/server/dispatch/dice.py` (`_resolve_wn_committed_action`). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Reviewer (audit)
- **Dev: "No deviations from spec" (the `hp_depletion` narrowing of the `isinstance` gate)** → ✓ ACCEPTED by Reviewer: not a deviation. The epic scope explicitly reads "WN COMBAT only (hp_depletion); dial chase/negotiation confrontations keep the native dial engine," and the neon CWN net-run trio (`test_neon_net_run_wiring`) proves the boundary is real — net-run is a *dial* confrontation under a WN binding and must keep `apply_beat`. The added `and cdef.win_condition == "hp_depletion"` conjunct is required correctness, not scope drift; the story title's bare `isinstance` is satisfied as one conjunct. Agrees with author reasoning.
- **UNDOCUMENTED (Reviewer audit): the cut drops `enc.beat`/`structured_phase` advance and the `last_beat_impacts` stamp under WN combat.** Spec said "remove the native riders (fleeting tag, dial-metric advance, composure, Brace)"; the code additionally removes the beat/phase ladder advance and the player-facing beat-impact chip, because both were emitted *inside* the now-uncalled `apply_beat`. Not logged by Dev. Severity: M (narrator pacing cue) / L (legibility chip) — both non-blocking. Arguably correct-per-doctrine (ADR-143: native scaffolding is removed, not preserved) and properly belongs to the epic's "WN owns the round" follow-up; captured as two Delivery Findings rather than rework.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; 5 informational notes | confirmed 0, dismissed 0, deferred 0 (notes folded into observations) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (test quality assessed by Reviewer directly) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (rules checked by Reviewer directly below) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed-from-subagent, 0 dismissed, 0 deferred. Reviewer-originated: 2 Medium/Low non-blocking gaps (beat/phase freeze, last_beat_impact chip), 3 Low observations. No Critical/High.

Preflight detail: story suite 6/6 GREEN; regression (`tests/integration tests/server/dispatch tests/telemetry`, -n0) 1065 passed / 34 skipped (pre-existing content-gated) / 0 failed; `ruff check` PASS; `ruff format --check` PASS (3 files clean). Preflight's 5 informational notes are addressed inline in the Rule Compliance / observations below (note 1 — the `str(...)=="strike"` compare — is parity with native `apply_beat` line 917, which does the identical thing, so it is consistent, not divergent).

## Reviewer Assessment

**Verdict:** APPROVED

### What this change is
Story 108-1 / ADR-143 "engine core cut": under a `WithoutNumberRulesetModule` binding with `win_condition=="hp_depletion"`, `_apply_committed_player_beat` no longer calls `ruleset.apply_beat`. Instead `_resolve_wn_committed_action` applies the WN math directly — weapon dice → `apply_beat_hp_channel`, then `check_hp_depletion` — and emits `{slug}.native_scaffolding_suppressed`. Every native rider (fleeting tag, dial-metric advance, composure/edge, Brace, taunt) is removed from the WN combat path, not muted. Native packs and WN *dial* confrontations (CWN net-run/chase/negotiation) are untouched.

### Data flow traced
Player `DICE_THROW` (face=20) → `WebSocketSessionHandler.handle_message` → sealed WN round (`run_wn_round`) → `_apply_committed_player_beat` → gate `isinstance(ruleset, WithoutNumberRulesetModule) and cdef.win_condition=="hp_depletion"` → `_resolve_wn_committed_action`: strike weapon-dice total (resolved pre-`apply_beat`, captured in `damage_resolver_fn`) lands on `_opposite_side_first_actor`'s `CreatureCore.hp` via `apply_beat_hp_channel` (armor mitigation parity preserved) → `check_hp_depletion` resolves the encounter at 0 HP → `wwn.native_scaffolding_suppressed` span → `ApplyResult(deltas=None, hp_removed=N)` flows through the unchanged downed seam, WWN cast spine, and `encounter_beat_applied` telemetry. Safe: HP resolution and the win check are preserved verbatim via the same public helpers the native engine used; `deltas=None` is consumed None-safely downstream (`apply_result.deltas.own if apply_result.deltas else 0`), and `encounter_resolved = apply_result.resolved or encounter.resolved` widens correctly.

### Findings (severity table — none blocking)
| Severity | Issue | Location | Disposition |
|----------|-------|----------|-------------|
| [MEDIUM] `[SIMPLE]`-adjacent | WN combat now freezes `enc.beat`/`structured_phase` at `0/Setup` (native `apply_beat` was the only advancer on the player path; opponent reprisal never advanced it). Narrator scene-render/mood cue goes static. No correctness break, nothing re-fires on `beat==0`. | `dice.py` `_resolve_wn_committed_action` | Non-blocking Delivery Finding (Gap) — belongs to epic's "WN owns the round" follow-up. |
| [LOW] | `last_beat_impacts` no longer stamped under WN combat → `last_beat_impact` broadcast key absent (player-facing "see the math" chip). Authoritative HP bars unaffected. | `dice.py` `_resolve_wn_committed_action` → `confrontation.py:489-499` | Non-blocking Delivery Finding (Gap). |
| [LOW] | Wiring test pins server rolls to min (`random.randint -> a`) and assumes Rux's 12-HP seed survives the reprisal — a fixture assumption, fragile under future damage tuning. | `test_108_1...py::test_ws_dice_throw_suppresses_native_scaffolding_end_to_end` | Accept — current behavior correct; note for future HP tuning. |
| [LOW] | This story's suite does not itself pin the `hp_depletion` scope boundary (that a WN *dial* confrontation keeps native scaffolding); relies on the pre-existing `test_neon_net_run_wiring` trio. | test suite | Accept — regression-guarded by existing suite; Dev verified green. |

### Observations (5+)
- [VERIFIED] HP/mitigation parity with native `apply_beat` strike channel — evidence: `dice.py` `_resolve_wn_committed_action` mirrors `beat_kinds.apply_beat` lines 917-953 (same `mitigation_override`→first-armor-item fallback, same `apply_beat_hp_channel(channel="strike", ...)`, same `_opposite_side_first_actor` target). Complies with No-Silent-Fallbacks (damage_spec_missing already spanned upstream).
- [VERIFIED] Win-condition resolution preserved — evidence: `_resolve_wn_committed_action` calls `check_hp_depletion(encounter, edge_resolver, beat_id=beat_id)`, identical to native's hp_depletion branch (`beat_kinds.py:1072-1075`); `hp_depletion.py:119-148` still sets `resolved`/`outcome`/`Resolution` phase and emits `encounter.resolved source="hp_depletion"`. ADR-139 liveness intact.
- [VERIFIED] Shock (miss) chip, downed seam, WWN cast spine, Killing Blow all preserved — evidence: they execute in `_apply_committed_player_beat` BEFORE/AFTER the gated call (`dice.py:1395-1622`, `1662-1700`), outside the replaced `apply_beat` call; the cut replaces only the rider call, not the surrounding WN math. Brace/full-defense are commit-driven via `_defensive_posture_for_reprisal`, not tag-driven, so they survive the tag removal. `[SILENT]` no swallowed paths.
- [VERIFIED] OTEL lie-detector present and slug-honest — evidence: `wn_native_scaffolding_suppressed_span` calls `_require_family_slug(slug)` and opens `{slug}.native_scaffolding_suppressed`; `SPAN_ROUTES` registers a per-family-slug route. Asserted at dispatch AND wire level. Satisfies the OTEL Observability Principle (mandatory span on a subsystem decision). `[DOC]` docstrings on both the helper and span accurately describe the cut and the `hp_removed` honesty field.
- [VERIFIED] Scope gate excludes native packs and WN dial confrontations — evidence: `isinstance(ruleset, WithoutNumberRulesetModule) and cdef.win_condition=="hp_depletion"`; guarded by `test_native_module_is_not_a_without_number_module` and the neon CWN net-run trio. The native engine path is byte-for-byte unchanged for everything else. `[TYPE]` `ApplyResult` reused (frozen dataclass), no stringly-typed leakage introduced; `[SEC]` no auth/tenant/input-trust surface in this diff (server-internal combat resolution).
- [SIMPLE] The cut is minimal and reuses public helpers (`apply_beat_hp_channel`, `check_hp_depletion`, `_opposite_side_first_actor`) rather than reimplementing — aligns with "Don't Reinvent." No dead code introduced; the old `apply_beat` call is preserved in the `else` branch for non-WN/dial paths.

### Rule Compliance
- **No Silent Fallbacks (CLAUDE.md/SOUL):** PASS. Suppression is explicit and spanned (`native_scaffolding_suppressed`), never a quiet skip; `damage_spec_missing` and `unarmed_strike_floor` remain loud upstream. The gate is an explicit `if/else`, not a fall-through.
- **No Stubbing / No half-wired:** PASS. `_resolve_wn_committed_action` is fully implemented and reached from production (`run_wn_round` → `_apply_committed_player_beat`), verified by the wiring test through `handle_message`.
- **Every Test Suite Needs a Wiring Test:** PASS. `test_ws_dice_throw_suppresses_native_scaffolding_end_to_end` drives the real `WebSocketSessionHandler`.
- **No Source-Text Wiring Tests:** PASS. Assertions are OTEL-span + behavior (tags/HP), no `read_text()`/grep-of-source.
- **OTEL Observability Principle:** PASS. New subsystem decision emits a span at dispatch and wire level; `hp_removed`/`suppressed` attributes make the decision auditable.
- **Bind the Ruleset, Don't Balance It (SOUL/ADR-143):** PASS — this change IS the doctrine: the native engine is removed from the WN combat path, not tuned to fit it. The `hp_depletion` narrowing keeps native dial confrontations on the native engine (correct boundary, not balancing).
- **Delete dead code in same PR:** N/A — no code became dead (the `apply_beat` call is still live for the `else` branch).

### Devil's Advocate
Argue this is broken. First attack: **double damage.** If the strike's weapon dice were applied both before `apply_beat` AND inside `_resolve_wn_committed_action`, the opponent would take 2× HP loss. Checked: the pre-`apply_beat` block (`dice.py:1395-1538`) only *rolls* the total and captures it in `damage_resolver_fn`; it never touches HP. The HP application happened *inside* `apply_beat` and now happens inside `_resolve_wn_committed_action` — one application, not two. The green guard `strike_still_removes_opponent_hp` would catch a zero, and an HP double would surface in `opponent_hp` regressions; none seen. Second attack: **the frozen `beat==0`.** Does any code treat `beat==0`/`Setup` as "encounter just started" and re-seed initiative, re-emit an opening, or re-run a once-per-fight hook every round? Enumerated consumers: `combat_tick_span` (telemetry attr only), `encounter_render` (display string), `query_*` tools (read-only), `encounter.py:70` mood weight (read-only), `narration_apply.py:6259-6305` (the narrator dial-advance path, gated to dial confrontations, never WN hp_depletion). No re-fire branch keys on `beat==0`/`Setup`. So the freeze is a degraded *signal*, not a *loop*. Third attack: **a confused author** writes a WWN combat beat that deals damage via `target_edge_delta` (the ADR-078 composure path) instead of `damage_channel=strike`. The cut drops the edge path entirely, so that beat would deal *no* HP under WN — a silent zero. But that is exactly the native composure rider ADR-143 says to remove, and 108-3 (content de-nativize) owns auditing WWN combat defs for `damage_channel=strike`; the `damage_spec_missing` span and `strike_still_removes_opponent_hp` guard bound the risk to authored content, not the engine. Fourth attack: **mutual-KO / no-Other.** `check_hp_depletion` and `_opposite_side_first_actor` both return None-safe; a strike with no seated Other applies no HP and resolves nothing — consistent with ADR-116. Conclusion: the failure modes are either guarded, telemetry-only, or correctly delegated to a follow-up content story. Nothing here justifies a block.

**Handoff:** To SM (Vizzini) for finish-story.