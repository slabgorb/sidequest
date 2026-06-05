---
story_id: "86-1"
jira_key: null
epic: "86"
workflow: "tdd"
---
# Story 86-1: Plan 1 — CWN binding + ablative-HP driver combat

## Story Details
- **ID:** 86-1
- **Jira Key:** (none — SideQuest uses sprint YAML tracking only)
- **Workflow:** tdd
- **Epic:** 86 - road_warrior → Cities Without Number: Two-Tier Rig Combat
- **Points:** 5
- **Priority:** p2
- **Repos:** sidequest-server, sidequest-content
- **Stack Parent:** none

## Story Description
Add ruleset:cwn to road_warrior; adopt standard CWN six (STR/DEX/CON/INT/WIS/CHA), remap every flavor-name reference (injury_system, archetypes, classes, char_creation, power_tiers); remove edge_config/Driver Edge → ablative HP + Shock/Trauma/Mortal/Major-Injury; combat confrontation win_condition:hp_depletion with opponent_default_stats carrying ALL SIX abilities + hp + armor_class; classes→CWN class+foci; FIX the hp_depletion calibration migration (test_road_warrior_pack_loads_with_dual_dial_schema + COMBAT_PACKS, per space_opera precedent); apply the Without-Number wiring checklist; mandatory OTEL/integration wiring test (cwn spans fire on a real turn).

## Branch Strategy
- **Repos:** sidequest-server (develop), sidequest-content (develop)
- **Branch Strategy:** gitflow
- **Feature Branch:** feature/86-1-cwn-binding-driver-combat

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T12:31:11Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T11:48:24Z | 2026-06-05T11:51:45Z | 3m 21s |
| red | 2026-06-05T11:51:45Z | 2026-06-05T12:02:55Z | 11m 10s |
| green | 2026-06-05T12:02:55Z | 2026-06-05T12:21:40Z | 18m 45s |
| review | 2026-06-05T12:21:40Z | 2026-06-05T12:31:11Z | 9m 31s |
| finish | 2026-06-05T12:31:11Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): The spec's calibration-migration premise is stale for road_warrior — `test_road_warrior_pack_loads_with_dual_dial_schema` does NOT exist, and road_warrior is in NEITHER `SHIPPED_PACKS` (lines 60-66) NOR `COMBAT_PACKS` (lines 93-95) of `tests/genre/test_confrontation_calibration.py`. Verified all pack-list calibration/chargen tests use explicit lists (no globs), so binding road_warrior to `hp_depletion` regresses ZERO existing calibration tests. Affects `sidequest-server/tests/genre/test_confrontation_calibration.py` (Dev should NOT chase a phantom `dial_threshold` migration; per the space_opera/elemental_harmony precedent, road_warrior should be ADDED to `SHIPPED_PACKS` so its `opponent_default_stats` get the ≤10 calibration ceiling + its surviving dial confrontations (negotiation/chase) are covered, and explicitly NOT added to `COMBAT_PACKS` since hp_depletion combat carries no opposed_check). *Found by TEA during test design.*
- **Improvement** (non-blocking): cwn is ALREADY a registered, fully-wired module (neon_dystopia proved the engine seams — downed-seam guard, spans, isinstance). So 86-1's engine work is mostly VERIFY, not build; the Without-Number wiring checklist's `dice.py` downed-seam slug guard already accepts cwn. The real surface area is the road_warrior content rewrite (both stat-name remap breadth across 7+ files) plus authoring damage on the combat strike beats (currently the ram/sideswipe beats have no damage source — the e2e test will stay RED until a strike actually depletes HP). Affects `sidequest-content/genre_packs/road_warrior/rules.yaml` (+ archetypes/classes/char_creation/powers/inventory/cultures/progression/worlds/the_circuit). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Confirmed TEA's calibration Gap — road_warrior should be ADDED to `SHIPPED_PACKS` in `tests/genre/test_confrontation_calibration.py` (NOT `COMBAT_PACKS`, per the space_opera/elemental_harmony hp_depletion precedent) so its calibrated opponent stats (≤10) and surviving dial confrontations (negotiation/chase) get coverage. Deferred to keep this PR content-scoped; the full suite passes today because road_warrior is in neither list. Affects `sidequest-server/tests/genre/test_confrontation_calibration.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): The class signature abilities (Wrecker "Push Through" / Ram beat, Grease Monkey "Field Repair", Chrome Saint "Body Sync", Strafe Run, Threading the Needle) are DORMANT Plan-2 rig mechanics — their `mechanical_effect` prose references Rig Composure / chase tiers that are not yet wired. Left as flagged dormant prose per spec §6.1; Plan 2/3 must wire or re-author them. Affects `sidequest-content/genre_packs/road_warrior/classes.yaml`. *Found by Dev during implementation.*
- **Gap** (non-blocking): Full server suite has 16 pre-existing failures unrelated to this story (none load road_warrior; all in engine modules untouched by a content-only change): `test_61_12_output_format_compaction` (NARRATOR_OUTPUT_ONLY byte budget 14416>13800), `test_enums::test_message_type_complete_count`, `test_npc_invented_namegen_routing` (6), `test_narration_clue_discovery_wiring` (5), `test_yield_handler_outbound::test_yield_multi_pc_partial_emits_active_confrontation`, `test_pertinence_wiring`, `test_retrieval_orchestration`. Recorded as the baseline failure list. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): The full server suite exhibits run-to-run flakiness under xdist on Python 3.14 — `psycopg_pool.ConnectionPool.__del__` raises `PythonFinalizationError: cannot join thread at interpreter shutdown` at interpreter teardown, intermittently marking infra-wiring tests FAILED that PASS in isolation (observed: `test_chargen_complete_log_uses_edge_not_hp` [caverns_and_claudes, not road_warrior], `test_connect_to_evropi...` [heavy_metal], `test_lore_rag_wiring`). This is environmental, not introduced by 86-1, but it makes the "16-failure baseline" non-deterministic and hampers regression detection. Affects `sidequest-server` test teardown / pool lifecycle. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **No calibration-migration test written (spec §6.2 premise stale)**
  - Spec source: 2026-06-04-road-warrior-cwn-rig-combat-design.md, §6.2 + §8 (Risks)
  - Spec text: "binding to hp_depletion regresses test_road_warrior_pack_loads_with_dual_dial_schema and the COMBAT_PACKS calibration set. Fix per the space_opera precedent — filter dial_threshold, drop road_warrior from COMBAT_PACKS."
  - Implementation: No such test was written or modified. Measured the actual suite: `test_road_warrior_pack_loads_with_dual_dial_schema` does not exist; road_warrior is absent from both SHIPPED_PACKS and COMBAT_PACKS; no glob test covers it. Binding regresses nothing here.
  - Rationale: Faithful to "measure, don't assert" — writing a test to "fix" a non-existent regression would be fiction. Logged as a Delivery Finding (Gap) for Dev: add road_warrior to SHIPPED_PACKS (not COMBAT_PACKS) per the space_opera precedent so its calibrated opponent stats get coverage.
  - Severity: minor
  - Forward impact: Dev's GREEN scope is lighter than the spec implies (no phantom migration); the calibration-coverage decision (add to SHIPPED_PACKS) is the actual follow-up.
- **Standard-six labels asserted as the exact abbreviations STR/DEX/CON/INT/WIS/CHA**
  - Spec source: 2026-06-04 spec, §3 decision D3
  - Spec text: "adopt the standard CWN six (STR/DEX/CON/INT/WIS/CHA) on the sheet; drop the flavor names"
  - Implementation: `test_road_warrior_uses_standard_cwn_six` asserts `ability_score_names == {STR,DEX,CON,INT,WIS,CHA}` exactly (the spec's literal abbreviations), not a looser "six non-flavor names" check.
  - Rationale: D3 names them explicitly; "a port is a port." If Dev prefers full names (STRENGTH...), that's a deviation Dev logs and this test is updated — RED-phase precision over leniency.
  - Severity: minor
  - Forward impact: Dev must use the abbreviations or renegotiate the label set.

### Dev (implementation)
- **Combat confrontation converted from rig (ram/sideswipe) to driver-on-foot personal combat**
  - Spec source: 2026-06-04 spec §2, §6.1, §7
  - Spec text: "Driver-on-foot combat becomes standard CWN personal combat (ablative HP)." / "No rig/vehicle confrontation wiring (Plan 2)."
  - Implementation: The single `category: combat` confrontation "Vehicular Combat" (rig ram/sideswipe/evasive, opposed_check) was REPLACED by "Roadside Firefight" — driver personal combat (shoot/melee/take_cover/disengage, beat_selection + hp_depletion). Updated classes.yaml `encounter_beat_choices` accordingly (ram→shoot, sideswipe→melee, evasive→take_cover).
  - Rationale: Plan 1 is driver-on-foot CWN combat; rig-vs-rig combat is Plan 2. My TEA tests assert exactly one combat confrontation, so the rig beats could not coexist. Rig combat mechanics survive as DORMANT prose in custom_rules (flagged not-live).
  - Severity: moderate
  - Forward impact: Plan 2 builds the rig confrontation fresh (net-new two-pool resolution per epic §5); the ram/sideswipe beats are intentionally gone, not lost — their mechanics live in custom_rules.rig_* prose.
- **Flavor→standard mapping settled: Nerve→CON, Road Sense→WIS**
  - Spec source: 2026-06-04 spec §6.3
  - Spec text: "Grip→DEX, Iron→STR, Nerve/Road-Sense vs WIS/CON assignment is a calibration detail to settle during remap. Road Sense→CON?, Swagger→CHA."
  - Implementation: Locked Grip→DEX, Iron→STR, Nerve→CON, Scrap→INT, Road Sense→WIS, Swagger→CHA. Chose Road Sense→WIS (perception/instinct) and Nerve→CON (grit/endurance) — cleaner thematic fit than the spec's tentative Road Sense→CON.
  - Rationale: Spec explicitly delegated this to remap-time judgment. WIS=perception maps to "reading the terrain / road sense"; CON=endurance maps to "Nerve" (holding together under fire).
  - Severity: minor
  - Forward impact: applied consistently across all structured stat refs; Plan 5 calibration can revisit if play disagrees.
- **Added CWN weapon damage specs to personal weapons (not explicitly in the spec)**
  - Spec source: 2026-06-04 spec §6.1 (combat hp_depletion) + §6.4 (HP must deplete)
  - Spec text: "Driver-on-foot combat becomes standard CWN personal combat (ablative HP)." / "assert ... HP depletes on the ablative pool."
  - Implementation: Added `damage:` (CWN dice + trauma/shock) to tire_iron, chain, sawed_off_shotgun, crossbow, pistol in inventory.yaml. The damage resolver has no unarmed fallback — strike damage comes from the equipped weapon, and these had NO damage field, so personal combat would deal zero.
  - Rationale: Required for the spec's "HP depletes" to be real in play (not just the e2e). Rig/mounted weapons + vessels stay damage-less (Plan 2).
  - Severity: moderate
  - Forward impact: Plan 5 calibration should sanity-check these damage values against road_warrior lethality.
- **Fixed a pre-existing dangling stat ref (associated_stat: Chrome → CON)**
  - Spec source: 2026-06-04 spec §6.3 (remap sweep)
  - Spec text: "Every flavor-name reference must move to the standard six."
  - Implementation: powers.yaml "Chrome Saint Interface" power had `associated_stat: Chrome` — never one of the six (pre-existing dangling ref). Mapped to CON (body-mod durability) while remapping the file.
  - Rationale: opportunistic coherence fix in a file I was already remapping; leaving a dangling stat ref would contradict the sweep.
  - Severity: minor
  - Forward impact: none.

### Reviewer (audit)
- **TEA: No calibration-migration test written (spec §6.2 premise stale)** → ✓ ACCEPTED by Reviewer: independently confirmed road_warrior is in neither SHIPPED_PACKS nor COMBAT_PACKS and the named test does not exist; writing a test to "fix" a non-existent regression would be fiction. "Measure, don't assert" was the correct call. Follow-up (add to SHIPPED_PACKS) is logged as a finding.
- **TEA: Standard-six labels asserted as exact abbreviations** → ✓ ACCEPTED by Reviewer: D3 names STR/DEX/CON/INT/WIS/CHA literally; Dev used exactly those, so no conflict materialized. Faithful-port precision.
- **Dev: Combat confrontation converted from rig (ram/sideswipe) to driver-on-foot personal combat** → ✓ ACCEPTED by Reviewer: directly mandated by spec §2/§6.1 ("Driver-on-foot combat becomes standard CWN personal combat") and §7 (rig combat is Plan 2). The rig mechanics survive as DORMANT prose in custom_rules, clearly flagged — no mechanical backing is implied. Sound.
- **Dev: Flavor→standard mapping settled Nerve→CON, Road Sense→WIS** → ✓ ACCEPTED by Reviewer: spec §6.3 explicitly delegated this to remap-time judgment; the WIS=perception / CON=grit assignment is thematically defensible and applied consistently across every structured ref (verified by grep: zero residual flavor stat refs).
- **Dev: Added CWN weapon damage specs to personal weapons** → ✓ ACCEPTED by Reviewer: required for the spec's "HP depletes on the ablative pool" to be real in play — the damage resolver has no unarmed fallback, so weaponless personal combat would deal zero. Confined to personal weapons; rig/mounted weapons + vessels correctly stay damage-less (Plan 2). Lethality calibration deferred to Plan 5 (flagged).
- **Dev: Fixed pre-existing dangling associated_stat: Chrome → CON** → ✓ ACCEPTED by Reviewer: "Chrome" was never one of the six (old or new); leaving it dangling would contradict the §6.3 sweep. Opportunistic, in-scope, correctly mapped to CON (Chrome Saint body-mod durability).

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish

**Test Files:**
- `sidequest-server/tests/genre/test_road_warrior_loads_cwn.py` — 7 content-binding tests (skip-if-content-absent), mirrors `test_neon_loads_cwn.py`.
- `sidequest-server/tests/server/test_road_warrior_cwn_combat_e2e.py` — 1 production-path OTEL wiring test (drives a real strike against the loaded pack), mirrors `test_awn_combat_dispatch.py` / `test_space_opera_swn_combat_e2e.py`.

**Tests Written:** 8 tests covering the Plan 1 ACs (§6.1/§6.2/§6.4 of the spec).
**Status:** RED — all 8 fail on the binding gap (`ruleset='native'`, `win_condition='dial_threshold'`, no `state_patch.hp`/no HP depletion), not setup errors. The e2e test's `combat.tick` + `watcher.state_transition` spans fire, proving the dispatcher engages the real pack — it just resolves on dials, not ablative HP.

### AC → Test map

| AC (spec §) | Test | Current RED reason |
|-------------|------|--------------------|
| Bind `ruleset: cwn`; resolves to CwnRulesetModule (§6.1/§6.2) | `test_road_warrior_binds_cwn` | ruleset='native' |
| Standard CWN six on sheet, flavor names gone (D3) | `test_road_warrior_uses_standard_cwn_six` | sheet still Grip/Iron/... |
| Complete identity-style attribute_map (D3) | `test_road_warrior_attribute_map_is_complete_identity_style` | no cwn block |
| edge_config removed → ablative HP (D2) | `test_road_warrior_drops_edge_config` | edge_config present |
| Combat is `win_condition: hp_depletion` (§6.1) | `test_road_warrior_combat_is_hp_depletion` | dial_threshold |
| opponent_default_stats: six + hp/armor_class/dexterity (§6.1) | `test_road_warrior_opponent_carries_all_six_plus_reserved_keys` | flavor keys, no reserved seeds |
| Structured stat remap sweep (§6.3) | `test_all_beat_stat_checks_use_standard_six` | stat_checks Grip/Iron/Road Sense |
| Production-path OTEL proof (§6.4, mandatory) | `test_road_warrior_strike_depletes_ablative_hp_and_fires_span` | no state_patch.hp; HP not depleted |

### Rule Coverage (CLAUDE.md / SOUL)

| Rule | Test(s) | Status |
|------|---------|--------|
| No Silent Fallbacks (fail-loud cwn binding) | `test_road_warrior_binds_cwn` (registry resolve) | failing |
| Every suite needs a wiring test (production consumer) | `test_road_warrior_strike_..._fires_span` (real dispatch_dice_throw) | failing |
| No Source-Text Wiring Tests (OTEL/behavior only) | e2e asserts spans + HP state, never `read_text()` grep | n/a (compliant) |
| OTEL Observability (subsystem decision emits span) | e2e asserts `state_patch.hp` | failing |
| Surgical remap (prose "grip" stays legal — SOUL Zork/flavor) | remap test keys on `stat_check`/`opponent_default_stats` keys, not raw text | failing |

**Self-check:** No vacuous assertions — every test compares real values; combat-confrontation and strike-beat helpers fail loudly on 0/multiple matches so downstream asserts can't pass vacuously. No `assert True`, no always-None checks.

**Handoff:** To Dev (Winchester) for GREEN — bind road_warrior to cwn per spec §6, and note the two Delivery Findings (the calibration premise is stale; combat strike beats need a damage source for the e2e to flip GREEN).

---
## Dev Assessment

**Implementation Complete:** Yes
**Engine changes:** NONE — cwn was already a registered, fully-wired ruleset module (neon_dystopia precedent). This story is content-only (+ test arming). Confirmed the loader binds road_warrior via `get_ruleset_module('cwn')` and a real strike depletes ablative HP + fires `state_patch.hp` on the production dispatch path.

**Files Changed:**

*sidequest-content/genre_packs/road_warrior/* (PR → develop):
- `rules.yaml` — ruleset: cwn + attribute_map/system_strain/trauma; ability_score_names → standard six; edge_config removed; combat "Vehicular Combat"→"Roadside Firefight" (personal CWN hp_depletion); negotiation/chase stat refs → standard six; injury/damage/dismounted/rig prose reframed Edge→ablative HP + flagged dormant.
- `inventory.yaml` — CWN damage specs on the five personal weapons.
- `archetypes.yaml`, `worlds/the_circuit/archetypes.yaml` — stat_ranges keys → standard six.
- `classes.yaml` — prime_requisite + encounter_beat_choices + prose mechanical refs → standard six / new beat ids.
- `powers.yaml` — associated_stat → standard six (incl. pre-existing Chrome→CON fix).
- `beat_vocabulary.yaml` — stat_check → standard six.
- `prompts.yaml` — narrator stat-check prose → standard six.

*sidequest-server/* (PR → develop):
- `tests/genre/test_road_warrior_loads_cwn.py` (7 tests) + `tests/server/test_road_warrior_cwn_combat_e2e.py` (1 test, arms attacker with real catalog weapon).

**Tests:** 8/8 new tests GREEN. Full server suite: 9593 passed, 16 pre-existing failures (baseline list in Delivery Findings — none touch road_warrior). Calibration suite passes (confirms road_warrior binding regressed nothing). ruff format + check clean on both test files.

**Branch:** feature/86-1-cwn-binding-driver-combat (pushed: content + server).

**Handoff:** To TEA (Radar) for verify phase (simplify + quality-pass).

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 8/8 new tests pass; ruff clean; pack loads ruleset=cwn; full suite 9594 pass / 19 fail (16 baseline + 3 xdist-teardown flakes) | confirmed 1 (flakiness finding), dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents`, domains covered manually below)
**Total findings:** 1 confirmed (flakiness, non-blocking), 0 dismissed, 0 deferred

Only `preflight` is enabled in `workflow.reviewer_subagents`. I covered the disabled specialists' domains manually (test quality, simplification, edge cases, types, comments, rules) — a content-YAML + new-test change with zero production engine code, so the type/security/silent-failure surfaces are minimal.

## Reviewer Observations

1. `[VERIFIED]` CWN binding is faithful to the neon_dystopia precedent — `rules.yaml:19-33` declares `ruleset: cwn` + a complete six-key identity `attribute_map` (STRENGTH→STR … CHARISMA→CHA), `system_strain.max_source: CONSTITUTION` (a map key, satisfying `RulesConfig._validate_cwn`), and `trauma.major_injury_save: physical` (valid enum). Pack loads `ruleset=cwn` (preflight). Complies with ADR-117 pluggable-ruleset + the "Don't Reinvent — Wire Up What Exists" rule (no engine code added).
2. `[VERIFIED]` The flavor→standard remap is exhaustive and surgical — a structured-ref grep across the whole pack returns ZERO residual `(stat_check|associated_stat|prime_requisite|max_source): <flavor>`. Genuine prose/names were correctly preserved (cultures "Scrapper"/"Ironside", progression `name: "Iron"` track, char_creation `race_hint: Scrapper`), honoring SOUL's Zork/flavor principle (narrator may still *say* "grip"). Evidence: `rules.yaml`, `archetypes.yaml`, `classes.yaml:28/64/95/128/162/198`, `powers.yaml:18-65`, `beat_vocabulary.yaml`, `prompts.yaml:126`.
3. `[VERIFIED]` The combat confrontation is correctly seeded for `hp_depletion` — `rules.yaml` "Roadside Firefight" carries `resolution_mode: beat_selection` + `win_condition: hp_depletion`, all six abilities AND the reserved `hp: 8 / armor_class: 13 / dexterity: 10` keys (satisfies `ConfrontationDef._validate` for category=combat hp_depletion). Strike beats `shoot`/`melee` use `damage_channel: strike` + `attack_bonus`/`combat_skill` exactly like neon's Street Combat.
4. `[VERIFIED]` Weapon damage makes the ablative path real — `inventory.yaml` adds `damage:` specs to all five personal weapons (3d4 shotgun, 1d6 chain/pistol/crossbow, 1d4 tire_iron) with trauma dice + Shock on melee. The damage resolver has no unarmed fallback, so without these, driver-on-foot combat would deal zero. The e2e proves it: a real strike against the loaded pack depletes ablative HP and fires `state_patch.hp` on the production dispatch path (no source-grep, per CLAUDE.md). Rig/mounted weapons + vessels correctly stay damage-less (Plan 2).
5. `[VERIFIED]` Dormant-prose honesty — `custom_rules` rig/Composure/chase blocks and the rig-flavored class signature abilities are retained but explicitly flagged "DORMANT — Plan 2", and the dead "Driver Edge"/"−1 Edge" terms were reframed to ablative HP. No prose implies mechanical backing that isn't wired. Satisfies the spec §6.1 honesty requirement + No-Stubbing.
6. `[TEST]` `[VERIFIED]` Test quality is strong, non-vacuous — `test_road_warrior_loads_cwn.py` helpers fail loudly on 0/>1 combat confrontations (no vacuous pass), every assertion compares concrete values with diagnostic messages, and the env-gated `pytest.skip` calls are fixture-level content guards (correct content-gated pattern, not suppressions). The e2e is a real production-path wiring test (drives `dispatch_dice_throw` against the loaded pack), satisfying the "Every Test Suite Needs a Wiring Test" + "No Source-Text Wiring Tests" rules.
7. `[LOW]` Weapon lethality may be hot for the gritty tier — a 3d4 (avg 7.5) shotgun reliably one-shots the seeded HP-8 scav mook. This is genre-true for "gritty" road_warrior and calibration is explicitly Plan 5, but worth a sanity pass then. Already captured in Dev findings. Non-blocking.
8. `[SIMPLE]` `[VERIFIED]` No over-engineering — the change is the minimal faithful port: content YAML + a 6-key identity map + weapon specs + two tests. No new abstractions, no engine code, no speculative Plan-2 scaffolding (rig stays dormant prose). Diff is 243/-219 content + 438 test lines.

## Rule Compliance

Applicable rules from CLAUDE.md / SOUL.md / sidequest-server lang-review, enumerated against the diff:

- **No Silent Fallbacks** — `ruleset: cwn` resolves through `get_ruleset_module` which fails loud on unknown slugs; `_validate_cwn` raises on an incomplete attribute_map. The pack loaded clean. ✓ Compliant. No new silent fallbacks introduced (content-only).
- **No Stubbing / No half-wired features** — Plan-1 scope (driver combat) is fully wired end-to-end (binding → dispatch → ablative HP → span, proven by e2e). The Plan-2 rig layer is NOT stubbed — it is retained as honest dormant prose, explicitly flagged not-live. ✓ Compliant.
- **Don't Reinvent — Wire Up What Exists** — Zero engine code; reuses the existing cwn module (neon precedent). ✓ Compliant.
- **Every Test Suite Needs a Wiring Test / No Source-Text Wiring Tests** — `test_road_warrior_cwn_combat_e2e` drives the real production dispatcher and asserts on OTEL spans + HP state, never on source text. ✓ Compliant.
- **OTEL Observability** — the wiring proof asserts `state_patch.hp` fires on a real strike (the GM-panel lie-detector). ✓ Compliant. (No new subsystem decision points added by a content change.)
- **Crunch in the Genre, Flavor in the World** — all mechanics (ruleset, combat, weapon damage, attribute_map) live in genre-tier `rules.yaml`/`inventory.yaml`; world `the_circuit/archetypes.yaml` only remaps stat ranges (flavor). ✓ Compliant.
- **ruff (Python lang-review: lint + format)** — preflight: `ruff check` PASS, `ruff format --check` PASS on both test files. ✓ Compliant.
- **Tests must not point at live content (anti-pattern)** — N/A inverted: these ARE legitimately content-gated genre tests for road_warrior (the pack under change), using the established skip-if-absent helper, exactly like `test_neon_loads_cwn.py`. Not the prod-rows-in-unit-tests anti-pattern. ✓ Compliant.

## Devil's Advocate

Let me argue this is broken. **First attack — the vestigial dial.** The hp_depletion combat still carries `player_metric`/`opponent_metric` (momentum, threshold 7). If any resolution path reads that dial, combat could "end" on momentum before HP reaches zero, silently overriding the ablative kill — a confused player would see a fight stop with the enemy still standing. *Rebuttal:* the AWN reprisal fixture (`test_awn_combat_dispatch._make_awn_reprisal_pack`) seeds win_condition=hp_depletion WITH momentum metrics and the production dispatcher resolves on HP; the e2e here drives the real pack and the kill resolves on the pool, not the dial. The metric is inert colour, matching precedent. Not broken — but I'd prefer a future cleanup to drop the dial from hp_depletion combats for clarity (noted, not blocking).

**Second attack — the weapon-damage one-shot.** A 3d4 shotgun averages 7.5 vs a seeded HP-8 mook; a confused GM might find every roadside fight is over in one trigger pull, making "combat" feel like an execution. *Rebuttal:* that is genre-true for the "gritty" lethality tier (road_warrior's own `lethality: gritty`), and the seeded mook is deliberately fragile ("drops in ~2-3 hits" per the AC comment, optimistic vs a shotgun but in-band for a glass-cannon scav). Calibration is explicitly Plan 5. Logged LOW.

**Third attack — a missed dead stat reference.** If even one structured stat field still named "Grip"/"Swagger", chargen or a beat resolution would reference a non-existent ability and silently misbehave. *Rebuttal:* I ran an exhaustive structured-ref grep (`(stat_check|associated_stat|prime_requisite|max_source): <flavor>`) over the entire pack — zero hits. The pack loads clean, which would have raised on an attribute_map value not in ability_score_names. The class `encounter_beat_choices` were also re-pointed (ram→shoot, sideswipe→melee, evasive→take_cover) — the loader validates these against the beat pool and the pack loaded, proving no dangling beat id.

**Fourth attack — a broken downstream consumer.** Renaming the combat confrontation label ("Vehicular Combat"→"Roadside Firefight") and beat ids could break a test or a save-anchor. *Rebuttal:* grep found NO test referencing the old label/beat ids, and the full suite's only failures are the 16 known-baseline + 3 xdist flakes (all confirmed to pass in isolation, none touching road_warrior). Reference-page anchors derive from `name`, and this is a new world with no shipped saves at risk. **Conclusion:** the change survives each line of attack; concerns reduce to non-blocking calibration/cleanup notes.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** player strike (DiceThrowPayload, beat `shoot`) → `dispatch_dice_throw` → `get_ruleset_module("cwn")` resolves CwnRulesetModule → `resolve_damage` pulls the equipped weapon's spec from `inventory.yaml` catalog → ablative `HpPool` depletes → `state_patch.hp` OTEL span fires. Safe and proven end-to-end by the e2e against the real loaded pack.

**Pattern observed:** faithful CWN content binding mirroring `neon_dystopia/rules.yaml` (cwn block shape, hp_depletion combat, weapon damage specs) — `rules.yaml:19-33` and the "Roadside Firefight" confrontation.

**Error handling:** fail-loud preserved — unknown ruleset raises (registry), incomplete attribute_map raises (`_validate_cwn`), hp_depletion combat missing reserved keys raises (`ConfrontationDef._validate`); the damage resolver skips loudly (warning span) rather than fabricating when no weapon/override exists.

**Tests:** 8/8 new GREEN; full suite 9594 pass; 19 fail = 16 known baseline (none touch road_warrior) + 3 xdist/psycopg_pool teardown flakes (pass in isolation, pre-existing, not introduced by this diff). ruff clean.

**Handoff:** To SM (Hawkeye) for finish-story.

---
## Sm Assessment

**Setup complete — ready for RED phase (tea).**

- Story 86-1 selected from backlog (p2, 5pts, tdd). Unblocked gate story for epic 86 (road_warrior CWN rig combat). No stale session or archive entry; status was `backlog` → now `in_progress`.
- Session file created at `.session/86-1-session.md`; epic + story context written (`sprint/context/context-epic-86.md`, `context-story-86-1.md`) and validated.
- Feature branches `feature/86-1-cwn-binding-driver-combat` created off `develop` in sidequest-server and sidequest-content. Orchestrator commit cca6176.
- Jira: skipped — project uses sprint YAML only (no Jira by policy).
- Spec: `docs/superpowers/specs/2026-06-04-road-warrior-cwn-rig-combat-design.md`. Known traps for tea/dev: hp_depletion calibration migration (space_opera precedent — filter dial_threshold, drop from COMBAT_PACKS), Without-Number wiring checklist (spans `__init__` re-export, dice.py downed-seam guard, OTEL span-assertion tests), opponent_default_stats needs ALL SIX ability scores.
- Next: tea writes failing tests per ACs in story context.