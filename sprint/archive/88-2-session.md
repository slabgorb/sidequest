---
story_id: "88-2"
jira_key: ""
epic: "88"
workflow: "tdd"
---
# Story 88-2: AWN Plan 1 content — mutant_wasteland awn binding, standard-six sweep, hp_depletion combat confrontation

## Story Details
- **ID:** 88-2
- **Jira Key:** (none — SideQuest is a personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** 88-1 (merged, foundation)
- **Repos:** content, server  *(sprint YAML says `content` only; expanded by TEA — see Design Deviations. Design §6 is explicitly a two-repo story: content = mutant_wasteland YAML, server = the calibration migration + the §6.5 wiring tests. Content has no test runner of its own; every gate for this binding runs in sidequest-server.)*
- **Branches:**
  - content: `feat/88-2-awn-content-mutant-wasteland-binding`
  - server:  `feat/88-2-awn-content-mutant-wasteland-binding` (TEA-created; holds the RED tests + the calibration migration Dev must land)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T20:19:06Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T19:25:47Z | 2026-06-05T19:27:42Z | 1m 55s |
| red | 2026-06-05T19:27:42Z | 2026-06-05T19:43:24Z | 15m 42s |
| green | 2026-06-05T19:43:24Z | 2026-06-05T19:54:34Z | 11m 10s |
| review | 2026-06-05T19:54:34Z | 2026-06-05T20:03:44Z | 9m 10s |
| red | 2026-06-05T20:03:44Z | 2026-06-05T20:06:46Z | 3m 2s |
| green | 2026-06-05T20:06:46Z | 2026-06-05T20:10:36Z | 3m 50s |
| review | 2026-06-05T20:10:36Z | 2026-06-05T20:19:06Z | 8m 30s |
| finish | 2026-06-05T20:19:06Z | - | - |

## Context

### Story Purpose
Complete the content binding for AWN (Ashes Without Number) as the fourth sister Without-Number ruleset module. Story 88-1 (engine) merged via PR #682; this story binds `mutant_wasteland` genre pack to the new `awn` ruleset module with ablative-HP personal combat, replacing the momentum-dial "Wasteland Brawl" with a proper `hp_depletion` confrontation.

### Scope (from Design §6.2-6.5)
1. Add `ruleset: awn` to `genre_packs/mutant_wasteland/rules.yaml`
2. Configure `attribute_map` (standard six: STR/DEX/CON/INT/WIS/CHA) replacing flavor names (Brawn/Reflexes/Toughness/Wits/Instinct/Presence)
3. Add `awn:` config block with trauma and system_strain numbers from the AWN Free Edition SRD
4. Replace "Wasteland Brawl" (momentum dial) with `hp_depletion` combat confrontation; keep "Wasteland Parley" (negotiation) and "Wasteland Pursuit" (chase) as dial confrontations
5. Comprehensive content sweep (§6.3): update all stat_check references and ability-score names in `archetypes.yaml`, `char_creation.yaml`, `progression.yaml`, `power_tiers.yaml`, `axes.yaml`, `inventory.yaml`, `prompts.yaml`, and every confrontation
6. Retire `magic_level` flag per its own DRAFT note; mutations → Plan 2
7. Fix calibration tests (migrate dial_threshold filters and COMBAT_PACKS set per §6.4 precedent)
8. Integration tests proving the bound `awn` ruleset loads + fires `cwn.*` combat spans in production turn path

### Dependency
- **88-1** (AWN engine module) — MERGED via PR #682, complete. This story requires the module to exist in sidequest-server develop.

### Key Risks
- **Content remap breadth** — standard-six touches 8+ files; sweep must be exhaustive or narrator references dead stat names
- **Calibration test false alarms** — `hp_depletion` migration regresses dial/COMBAT_PACKS tests by design; baseline first
- **`magic.yaml` double-truth** — pack carries old mutation framing until Plan 2; flag clearly so no prompt implies unimplemented mechanics

## Sm Assessment

**Routing:** tdd / phased → next agent **tea** (RED phase). Content-only repo; branch `feat/88-2-awn-content-mutant-wasteland-binding` cut off freshly-FF'd `develop`. No Jira (personal project). Dependency 88-1 (engine module, PR #682) merged — module exists in server `develop`, so the content binding has a real consumer to load against.

**Known landmines for TEA/Dev (from prior Without-Number ports — do NOT relearn the hard way):**
- **Validator ≠ loader.** `validate pack` PASS 0/0 is not proof the pack loads. Only `load_genre_pack` catches enum/draft/opening-schema breaks. The wiring test must run the real loader against the bound `awn` pack and assert `cwn.*` combat spans fire in the production turn path — not a synthetic fixture.
- **hp_depletion migration regresses calibration tests BY DESIGN.** Binding combat to a Without-Number hp_depletion ruleset breaks `test_<pack>_pack_loads_with_dual_dial_schema` + the `COMBAT_PACKS` set. Follow the space_opera precedent (§6.4): filter the `dial_threshold` and drop the pack from `COMBAT_PACKS`. **Baseline the full suite first** so these expected failures aren't mislabeled as regressions.
- **Gate on the FULL suite with content env set** (`SIDEQUEST_GENRE_PACKS` + `SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test`). A scoped `tests/server/` run skips content-gated `tests/genre/` calibration tests and mislabels real regressions as pre-existing.
- **standard-six attribute_map must be COMPLETE** (canonical→abbrev, `max_source=canonical key`); `opponent_default_stats` needs all six ability scores for spell/physical saves. AWN combat == CWN, so the `awn` config extends the Cwn lineage — mind the isinstance/tuple seams the engine story already wired.
- **`magic_level`/mutation framing is double-truth until Plan 2** — flag, don't author mechanics for it.

**Stance:** Setup + routing only. The content sweep breadth and test gates are TEA's (RED) and Dev's (green) to own.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (12 failing + 1 intentional boundary-guard pass; ready for Dev) — verified via testing-runner, env set (`SIDEQUEST_GENRE_PACKS` + `SIDEQUEST_TEST_DATABASE_URL`). Zero import/collection/Type/Attribute errors — all 12 reds are clean `AssertionError`s.

**Test Files (server repo — see Design Deviations for why):**
- `tests/genre/test_mutant_wasteland_awn_binding.py` — 9 tests: real-pack load proves `ruleset: awn` binding + non-None AwnConfig; standard-six `ability_score_names`; complete `awn.attribute_map` (six canonical→abbrev, strain max_source in map); combat is `hp_depletion` (not `opposed_check`); combat `opponent_default_stats` carries all six ability scores + `hp` + `armor_class`; social/movement confrontations stay dial; every confrontation `stat_check` is standard-six; every archetype `stat_ranges` key is standard-six; `magic_level` retired from rules.yaml.
- `tests/server/test_mutant_wasteland_combat_dispatch.py` — 4 tests (the §6.5 mandatory wiring proof, mirrors `test_road_warrior_combat_dispatch.py`): `get_ruleset_module("awn")` resolves to `AwnRulesetModule` (∩ `CwnRulesetModule`) in the production registry; a real strike through `dispatch_dice_throw` emits `state_patch.hp` and depletes the ablative pool; a 0-HP strike runs the inherited CWN downed seam → `cwn.mortal_injury.declared` + Mortal Injury status; every personal weapon authors a `damage:` spec. OTEL-span / behavior assertions only — no source-text wiring tests (server CLAUDE.md).

**Tests Written:** 13 covering the design's content-side ACs (§6.2 binding + hp_depletion combat, §6.3 standard-six sweep, §6.5 production-path wiring + the GM-panel lie-detector spans).

### Rule Coverage

| Rule / Doctrine | Test(s) | Status |
|------|---------|--------|
| Validator≠loader — prove the pack LOADS (`_validate_awn` fires) | `test_mutant_wasteland_loads_and_binds_awn` | failing (native) |
| Standard-six sweep is exhaustive (no dead mechanical stat names) — §6.3/§10 | `..._ability_score_names_are_standard_six`, `..._all_confrontation_stat_checks_standard_six`, `..._archetype_stat_ranges_standard_six` | failing |
| attribute_map COMPLETE (six keys + strain source) — documented gotcha | `..._awn_attribute_map_complete_standard_six` | failing |
| hp_depletion combat with all six opponent saves + hp/ac — §6.2 | `..._combat_is_hp_depletion`, `..._combat_opponent_stats_have_all_six_plus_hp_ac` | failing |
| Keep Parley/Pursuit dial — no over-migration — §6.2 | `..._social_and_movement_stay_dial` | passing (boundary guard) |
| magic_level retired — §6.2 + DRAFT note | `..._magic_level_retired` | failing |
| Every test suite needs a wiring test (reachable from production path) | `..._binds_awn_module_in_production_registry` | failing (native) |
| OTEL lie-detector: HP actually depletes / downed seam fires on a REAL turn — §6.5 | `..._strike_depletes_ablative_hp_on_real_turn`, `..._downed_target_routes_through_cwn_seam` | failing |
| Content half wired: weapons author damage (no narration-without-mechanics) | `..._personal_weapons_carry_damage_specs` | failing |

**Rules checked:** 13 tests across 9 design-mapped gates. **Self-check:** the lone passing test is a non-vacuous boundary guard (`assert win_condition != "hp_depletion"` on real social/movement confrontations) — kept deliberately. No `let _ =`, no `assert True`, no always-None assertions.

**Calibration baseline (per §6.4 — record before the change):** `tests/genre/test_confrontation_calibration.py` is GREEN today; specifically `test_combat_pack_exposes_at_least_one_opposed_check_confrontation[mutant_wasteland]` PASSES. It WILL fail once GREEN lands combat as hp_depletion — that is the by-design migration, NOT a regression. Dev removes `mutant_wasteland` from `COMBAT_PACKS`.

**Handoff:** To Dev (Charles) for GREEN, across BOTH repos. Content: bind `ruleset: awn` + `awn:` block, standard-six sweep (rules.yaml stat_checks + opponent stats, archetypes.yaml stat_ranges, ability_score_names), migrate combat to `win_condition: hp_depletion` (set `damage_channel: strike` on the attack beat, all six opponent stats + hp + armor_class), author weapon `damage:` specs, retire `magic_level`. Server: drop `mutant_wasteland` from `COMBAT_PACKS` in the calibration test. Gate on the FULL suite with content env set.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 0 new (3 pre-existing lint, 0 smells) | confirmed 0, dismissed 0 (pre-existing I001 on unrelated lull-escalation files), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled returned; 8 disabled via `workflow.reviewer_subagents`)
**Total findings:** 1 confirmed (F1, HIGH — found by Reviewer's own manual pass, not a subagent), 0 dismissed, 0 deferred. Preflight: GREEN (34/34 story + 865 genre suite), 0 new lint/smells.

> Note: the adversarial diff-based specialists are all disabled for this project, so the manual review below (rule enumeration + data-flow trace + devil's advocate) carries the load. Preflight's GREEN was necessary but not sufficient — it had no test exercising a flickering_reach world-archetype NPC in combat, which is exactly where F1 lives.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Standard-six sweep is NOT exhaustive — the sole playable world's NPC archetypes still use retired flavor stat names, which crashes combat resolution (`_stat` raises `KeyError`, no neutral-10 fallback) | `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/archetypes.yaml` (12 `stat_ranges` keys) | Remap the 12 keys to standard-six (`Brawn`→STR, `Reflexes`→DEX, `Toughness`→CON, `Wits`→INT, `Instinct`→WIS, `Presence`→CHA) — the identical mapping already applied at genre tier. TEA: add a world-tier archetype sweep gate (the current test only checks genre `archetypes.yaml`). |

### Rule Compliance

- **§6.3 "Every flavor-name reference must move to the standard six … the sweep must be exhaustive"** — Genre tier: COMPLIANT (rules.yaml 13 stat_checks + opponent stats, genre archetypes.yaml 12 keys, ability_score_names, awn attribute_map all standard-six; verified by grep + passing tests). World tier: **VIOLATION** — `worlds/flickering_reach/archetypes.yaml` retains 12 flavor-named `stat_ranges` keys (Finding F1).
- **"No half-wired features … connect the full pipeline" (content CLAUDE.md)** — VIOLATION: genre tier swept, world tier (the only playable surface) not. The mapping rule may NOT be dismissed.
- **No Silent Fallbacks** — COMPLIANT: `magic_level` removal is behavior-neutral (not a magic gate; reference axiom strip filters absent keys, `reference_presenters.py:798`). Weapon DamageSpec fail-loud rules satisfied (no `shock` without `shock_ac`). The swn `_stat` fail-loud (`KeyError`, not neutral-10) is itself correct — it is what *surfaces* F1 rather than hiding it.
- **ADR-093 opponent-stat ceiling (≤10)** — COMPLIANT: all six combat opponent ability scores = 10; hp/armor_class/dexterity are reserved keys (exempt).
- **ConfrontationDef hp_depletion invariants (rules.py:539-574)** — COMPLIANT: hp:8≥1, armor_class:12≥1, dexterity:10≥3; pack loads.
- **"Crunch in the Genre, Flavor in the World" (SOUL)** — COMPLIANT: only the six attribute labels changed; classes/stocks keep flavor names; mutation framing left for Plan 2.

### Observations (manual review)

1. **[HIGH][RULE] F1 — world-archetype sweep omitted → combat-path crash.** `effective_archetypes` (pack.py:297) returns the WORLD archetype list when a world declares one (`return list(world_opt.archetypes), "world"`), so flickering_reach's archetypes REPLACE the genre ones in play; flickering_reach is mutant_wasteland's only world. NPC stats roll from `archetype.stat_ranges` (encountergen.py:608) → stat block keyed by `Instinct`/`Wits`/etc. AWN inherits SWN's `_stat` (swn.py:39-51), which **raises `KeyError`** on a missing key ("SWN module no longer falls back to a neutral 10"). When such an NPC's save/check resolves against the swept attribute_map (`WIS`/`STR`/…), `_stat` raises → combat crashes. Fix: 12-key remap in the world file + a TEA world-tier gate.
2. **[VERIFIED] `magic_level` removal is safe** — only consumers are the model field (rules.py:1005, default `""`) and a reference-page display label (reference_presenters.py:776); magic activation runs through `MAGIC_PLUGINS`/`magic_loader.py`, never `magic_level`. The axiom strip emits a card only `if key in node and node[key] not in (None, "")` (reference_presenters.py:798), so the absent key yields no blank chip. Behavior-neutral; complies with No Silent Fallbacks (no silent magic-on).
3. **[VERIFIED] hp_depletion combat shape correct** — `resolution_mode: beat_selection` + `win_condition: hp_depletion`, opponent_default_stats hp:8/armor_class:12/dexterity:10 + six scores ≤10, attack beat carries `damage_channel: strike` + attack_bonus/combat_skill. Matches the road_warrior precedent and passes `ConfrontationDef._validate`. The `dexterity` (initiative) vs `DEX` (ability) dual-key is the intended reserved-key pattern (OPPONENT_RESERVED_STAT_KEYS).
4. **[VERIFIED] genre sweep + weapon damage faithful/minimal** — 5 weapons author valid NdM DamageSpec (1d6/1d8/3d4); Trauma/Shock correctly deferred per §4; no shock-without-shock_ac. Calibration migration drops mutant_wasteland from COMBAT_PACKS with a precedent-matching comment; Parley/Pursuit still covered by SHIPPED_PACKS threshold tests.
5. **[LOW][Question] `mutant_ability` "Use Mutation" beat is mechanically inert** — `kind: strike, base: 4` but NO `damage_channel`, so in hp_depletion it deals no HP and momentum no longer wins; it is a narrative/decorative button until Plan 2 wires the MutationPlugin. Consistent with the design's mutation deferral and the magic.yaml double-truth flag, but confirm narration/UI does not imply a live combat power. Non-blocking.
6. **[LOW] sawed_off 3d4 (avg 7.5) one-shots the hp:8 default raider on an above-average roll** — genre-appropriate for "moderate"-lethality wastes (Genre Truth); noted, accepted.

### Data Flow Trace

Player picks "Attack" → `dispatch_dice_throw` → awn(=cwn=swn) `attack_params`: `stat_modifier(stats, "STR")` + attack_bonus 1 + combat_skill 1 vs opponent `armor_class` → on hit, weapon DamageSpec (resolved from catalog) rolls → opponent `HpPool` depletes → at 0 HP the inherited CWN downed seam fires `cwn.mortal_injury.declared`. **Safe** for a standard-six-keyed opponent (the wiring tests seed exactly that and pass: `state_patch.hp` + `cwn.mortal_injury.declared`). **Unsafe** for a flickering_reach-archetype NPC: its stat block is keyed by dead flavor names, so the first `_stat(stats, "STR"|"WIS"|…)` raises `KeyError` (swn.py:48-51) — the F1 crash path the green tests never exercise.

### Devil's Advocate

Assume this is broken. The headline break is F1: the story's entire reason to exist (give Sebastien and Jade *real* mechanics, lie-detectable via OTEL) is defeated in the only place mutant_wasteland is actually played. A GM boots flickering_reach, an encounter spawns a Scrapborn raider from the world archetype, the player swings — and instead of crunch, the turn throws `KeyError: stat 'STR' not in stat block ['Instinct','Wits']`. That is not "winging it with no backing"; it is worse — a hard fault in the combat spine. The green suite hid it because every wiring test hand-seeds a standard-six opponent; none draws from world content. That is the classic test-coverage blind spot the adversarial pass exists to catch. Second: legacy saves. Any in-flight mutant_wasteland character carries stats under the old flavor keys; after this flip, chargen and confrontation lookups expect STR/DEX/… — but per project doctrine legacy saves are throwaway, so I do not block on it (noted, not filed). Third: the "Use Mutation" beat now does nothing mechanical, yet its narrator_hint promises "the mutation manifests visibly … show the cost as well as the power" — a player could reasonably believe they spent something; confirm the prose doesn't sell an effect the engine no longer applies. Fourth: a confused author copies this pack as a template and inherits the half-swept world tier. Fifth: stressed input — an archetype with a stat_range like `[18,14]` (inverted) or a single-element list would roll oddly, but that is pre-existing content, not this diff. None of these unseat the verdict; F1 alone is a hard blocker, and it is a five-minute, already-proven mechanical fix.

**Handoff:** Back to TEA — F1 is testable (add a world-tier archetype standard-six gate mirroring the genre one), then Dev applies the 12-key remap to `worlds/flickering_reach/archetypes.yaml`.

---

## Subagent Results (Round-Trip 1 re-review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 new (2 pre-existing barsoom, 0 smells, lint/format clean) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled returned; 8 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred. F1 (the round-1 blocker) is RESOLVED.

## Reviewer Assessment (Round-Trip 1 re-review)

**Verdict:** APPROVED

**F1 resolution — verified three ways:**
1. **Diff** — `worlds/flickering_reach/archetypes.yaml` remaps exactly the 12 `stat_ranges` keys to standard-six across all six archetypes; `inventory_hints`, names, and lore are untouched (spoiler discipline honored). Stat-keys-only change.
2. **Exhaustiveness** — a pack-wide hunt for any flavor name used as a stat-block key (`^\s+(Brawn|Reflexes|Toughness|Wits|Instinct|Presence):\s*(\[|[0-9])`) across genre + every world returns **ZERO**. The §6.3 "must be exhaustive" mandate is now genuinely met; no second missed surface (world `creatures.yaml` uses HD-style SWN stat lines, not ability-score keys).
3. **Gate** — the new `test_mutant_wasteland_world_archetype_stat_ranges_standard_six` is well-formed (globs all worlds, **fails loud** on empty rather than silent-skip, checks both `RETIRED_FLAVOR_NAMES` and `not in STANDARD_SIX`) and PASSES; full suite GREEN (10930 passed; only the 2 pre-existing epic-87 barsoom validator failures remain), 0 new smells, lint/format clean.

**Data flow re-traced:** an NPC rolled from a flickering_reach archetype now produces a standard-six-keyed stat block → `_stat(stats, "STR"|"WIS"|…)` resolves → no `KeyError` → combat resolves with real modifiers. The round-1 crash path is closed.

**Pattern observed:** the world remap is byte-for-byte the same transform applied at genre tier; the new gate prevents any future world from regressing. Good, consistent, minimal.

**Carry-forward (non-blocking, already filed):** the mutant_ability "Use Mutation" beat remains mechanically inert in Plan 1 (Plan-2 mutation work); base-only weapon damage and point_buy faithfulness are accepted deferrals. None block.

**Handoff:** To SM (Hawkeye) for finish — create + merge the content PR AND the server PR (two-repo story; see TEA's scope deviation), both off branch `feat/88-2-awn-content-mutant-wasteland-binding`.

## Dev Assessment

**Implementation Complete:** Yes — GREEN across both repos.

**Files Changed:**
- *content* (`sidequest-content`, branch `feat/88-2-awn-content-mutant-wasteland-binding`, pushed):
  - `genre_packs/mutant_wasteland/rules.yaml` — `ruleset: awn` + `awn:` config block (identity attribute_map, system_strain CON, trauma 6/6/physical); `ability_score_names` → standard six; `magic_level` removed; "Wasteland Brawl" migrated to `resolution_mode: beat_selection` + `win_condition: hp_depletion` (six opponent ability scores + hp/armor_class/dexterity; `damage_channel: strike` + attack_bonus/combat_skill on the attack beat); 13 confrontation `stat_check`s → standard six. Parley + Pursuit untouched (stay dial).
  - `genre_packs/mutant_wasteland/archetypes.yaml` — 12 `stat_ranges` keys → standard six.
  - `genre_packs/mutant_wasteland/inventory.yaml` — base `damage` dice on the 5 personal weapons.
  - `genre_packs/mutant_wasteland/magic.yaml` — one stat-name comment fix (Plan-2 framing untouched).
  - **(round-trip 1, Reviewer F1)** `genre_packs/mutant_wasteland/worlds/flickering_reach/archetypes.yaml` — 12 world-archetype `stat_ranges` keys remapped to standard-six (same mapping as genre tier; stat keys only, names/lore untouched). Closes the combat-path `KeyError` in the only playable world.
- *server* (`sidequest-server`, branch `feat/88-2-awn-content-mutant-wasteland-binding`, pushed):
  - `tests/genre/test_confrontation_calibration.py` — dropped `mutant_wasteland` from `COMBAT_PACKS` (§6.4 by-design migration) with a why-comment mirroring the space_opera/elemental_harmony precedents.
  - `tests/genre/test_mutant_wasteland_awn_binding.py` + `tests/server/test_mutant_wasteland_combat_dispatch.py` — TEA's RED tests, trivial ruff line-length reflow only.

**Round-trip 1 (Reviewer F1):** applied the world-tier sweep to `flickering_reach/archetypes.yaml`; the new `test_mutant_wasteland_world_archetype_stat_ranges_standard_six` gate is GREEN; full suite **10932 passed, 344 skipped, 2 pre-existing barsoom failures**. No new regressions.

**Tests (initial green):** 13/13 story tests GREEN + calibration suite GREEN. Full suite: **10930 passed, 345 skipped, 2 failed** — the 2 failures are `heavy_metal/barsoom` content-validation (epic 87/89 in-progress world, assets pending), unrelated to this story (my diff touches only mutant_wasteland YAML + the calibration `COMBAT_PACKS` list; no causal path to a barsoom world-file check). Lint clean; `ruff format --check` clean.

**Branches:** both pushed (content + server), same branch name. **No PRs created** — SM creates+merges both at finish (see TEA's blocking Conflict finding re: the two-repo scope).

**Handoff:** To verify/review phase. The §6.5 OTEL lie-detector is satisfied — a real wasteland strike fires `state_patch.hp` + `cwn.mortal_injury.declared` and depletes the ablative pool; combat now has mechanical backing, not improvised prose.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (blocking): Sprint YAML scopes 88-2 `repos: content`, but design §6 makes this a two-repo
  story — the calibration migration and the mandatory §6.5 wiring tests must live in `sidequest-server`
  (content has no test runner). Affects `sprint/epic-88.yaml` (88-2 `repos:` should read `content,server`)
  and SM's finish ceremony (a server PR must be created+merged alongside the content PR). A server feature
  branch `feat/88-2-awn-content-mutant-wasteland-binding` already exists with the RED tests committed.
  *Found by TEA during test design.*
- **Gap** (non-blocking): NO mutant_wasteland personal weapon authors a `damage:` spec
  (sharpened_rebar, pipe_wrench, crossbow_salvage, sawed_off, power_glove). hp_depletion combat
  depletes nothing without them — the content half of §6.2. Affects
  `sidequest-content/genre_packs/mutant_wasteland/inventory.yaml` (add `damage:` to each personal
  weapon; base damage is enough for Plan 1 — Trauma/Shock refinement is a later plan per §4).
  *Found by TEA during test design.*
- **Gap** (non-blocking): `NpcArchetype` is `extra="allow"` and the loader does NOT cross-check
  `stat_ranges` keys against `ability_score_names`, so a half-finished standard-six sweep leaves dead
  flavor stat names in `archetypes.yaml` and the pack still loads clean (the silent failure §10 warns of).
  `test_mutant_wasteland_archetype_stat_ranges_standard_six` pins it. Affects
  `sidequest-content/genre_packs/mutant_wasteland/archetypes.yaml` (12 dead `stat_ranges` keys to migrate).
  *Found by TEA during test design.*
- **Question** (non-blocking): `magic.yaml` carries a flavor-name comment (`Instinct skill check`) and the
  whole mutation-as-magic framing — Plan-2 double-truth per §7. Not mechanically consumed, so the tests do
  not gate it, but flag for Dev: do NOT author live mutation mechanics here in Plan 1.
  Affects `sidequest-content/genre_packs/mutant_wasteland/magic.yaml`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): AWN-faithful chargen is 3d6-in-order / standard array, but the pack still
  declares `stat_generation: point_buy` (budget 27) — a faithfulness choice flagged by Architect §11.5, not a
  Plan-1 blocker. Affects `sidequest-content/genre_packs/mutant_wasteland/rules.yaml` (GM faithfulness pass may
  switch generation method; no engine change). *Found by Dev during implementation.*
- **Gap** (non-blocking): personal weapons carry base `damage` dice only — no per-weapon Trauma Die / Shock /
  AP yet (deferred to a later inventory plan per §4), so wasteland hits are non-traumatic until then. Affects
  `sidequest-content/genre_packs/mutant_wasteland/inventory.yaml`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (blocking): the standard-six sweep stopped at the genre tier — `worlds/flickering_reach/archetypes.yaml`
  retains 12 flavor-named `stat_ranges` keys. World archetypes REPLACE genre archetypes in play (pack.py:297
  `effective_archetypes`) and flickering_reach is the pack's only world, so an NPC rolled from a world archetype
  crashes combat resolution (`_stat` raises `KeyError`, swn.py:48-51 — no neutral-10 fallback). Violates §6.3's
  exhaustive-sweep mandate. Affects `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/archetypes.yaml`
  (remap the 12 keys, same mapping as the genre tier) and the server test suite (add a world-tier archetype gate).
  *Found by Reviewer during code review.* (Finding F1 — REJECT.)
- **Question** (non-blocking): the `mutant_ability` "Use Mutation" beat is mechanically inert in hp_depletion
  (no `damage_channel`; momentum no longer wins) but its narrator_hint promises a visible cost/power — confirm Plan-1
  narration/UI doesn't imply a live mutation mechanic. Affects `genre_packs/mutant_wasteland/rules.yaml` (and Plan 2).
  *Found by Reviewer during code review.*

### Reviewer (code review — round-trip 1 re-review)
- No new upstream findings. F1 resolved (world-tier sweep complete + gated; pack-wide hunt shows zero flavor stat keys). Verdict APPROVED. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **RED tests authored in sidequest-server, not the content repo**
  - Spec source: session Story Details `repos: content`; design §6 (`docs/superpowers/specs/2026-06-05-ashes-without-number-mutant-wasteland-design.md`)
  - Spec text: "Repos: `sidequest-server` (module + config + calibration) and `sidequest-content` (mutant_wasteland YAML)"
  - Implementation: created a `sidequest-server` feature branch and placed all 13 RED tests there (genre + server suites); session **Repos:** updated to `content, server`.
  - Rationale: sidequest-content has no test runner; `_validate_awn` and the OTEL wiring assertions only fire through the server's `load_genre_pack` / `dispatch_dice_throw`. The design itself is two-repo — the sprint YAML under-scoped it to `content`.
  - Severity: minor
  - Forward impact: SM must create+merge a server PR alongside the content PR at finish; Dev's GREEN spans both repos (content YAML + the COMBAT_PACKS calibration migration in `tests/genre/test_confrontation_calibration.py`).
- **Calibration migration left as GREEN work, not pre-written as a RED test**
  - Spec source: design §6.4
  - Spec text: "Binding to `hp_depletion` regresses the pack-load / dial-schema and `COMBAT_PACKS` calibration tests by design ... drop mutant_wasteland from the dial-`COMBAT_PACKS` set."
  - Implementation: I did NOT add a new test asserting "mutant_wasteland ∉ COMBAT_PACKS" (that would assert on a test constant). Instead the new `test_mutant_wasteland_combat_is_hp_depletion` pins the end-state; the existing `test_combat_pack_exposes_at_least_one_opposed_check_confrontation[mutant_wasteland]` will fail by-design once content lands, and Dev removes `mutant_wasteland` from `COMBAT_PACKS` (mirroring the space_opera + elemental_harmony comments already in that file).
  - Rationale: avoids a circular/vacuous test; matches how the prior sister-pack migrations were handled.
  - Severity: minor
  - Forward impact: Dev must edit `tests/genre/test_confrontation_calibration.py` `COMBAT_PACKS` (remove `mutant_wasteland` + add a why-comment). This is expected migration, NOT a regression — baseline captured below.

### Dev (implementation)
- **Weapon damage authored as base dice only (no Trauma Die / Shock)**
  - Spec source: design §6.2 + §4
  - Spec text: "Per-weapon Trauma Die/Rating and Shock live on weapon content (DamageSpec), authored in [a] Plan that fattens inventory.yaml."
  - Implementation: gave the 5 personal weapons `damage: {dice: "NdM"}` only (sharpened_rebar 1d6, pipe_wrench 1d6, crossbow_salvage 1d8, sawed_off 3d4, power_glove 1d8); no `trauma_die`/`shock`.
  - Rationale: §4 explicitly defers per-weapon Trauma/Shock to a later inventory plan. Base dice is all Plan 1's hp_depletion combat needs to deplete HP; `test_..._personal_weapons_carry_damage_specs` only requires `damage is not None`.
  - Severity: minor
  - Forward impact: a later AWN inventory plan adds Trauma Die / Shock / AP per weapon; until then wasteland weapons land non-traumatic hits.
- **`stat_generation: point_buy` left unchanged (AWN-native is 3d6-in-order / standard array)**
  - Spec source: Architect Addendum §11.5
  - Spec text: "AWN's native chargen is 3d6-in-order or the standard array (14/12/11/10/9/7), not point-buy ... Point-buy stays mechanically valid ... it's NOT a Plan-1 blocker — but flag it as a faithfulness/calibration choice for the GM."
  - Implementation: left `stat_generation: point_buy`, `point_buy_budget: 27` untouched.
  - Rationale: §11.5 explicitly rules it out of Plan 1; no test gates it; the builder seeds strain from final scores regardless of generation method. Changing it risks chargen-calibration tests for zero in-scope benefit.
  - Severity: minor
  - Forward impact: a GM faithfulness pass may switch to 3d6/array; no engine change needed.
- **`magic.yaml` comment touched (Instinct → WIS) despite Plan-2 double-truth flag**
  - Spec source: design §7 / TEA finding (Plan-2 reconciliation)
  - Spec text: "do NOT author live mutation mechanics here in Plan 1."
  - Implementation: changed ONE comment line ("Default is Instinct skill check" → "WIS skill check"); no mechanics, fields, or framing altered.
  - Rationale: leaving a retired flavor stat name in a comment would be a dead reference; a comment fix is not authoring mechanics.
  - Severity: trivial
  - Forward impact: none — Plan 2 still owns the mutation-as-magic reconciliation.

### TEA (test design — rework round-trip 1)
- **Added a world-tier archetype sweep gate in response to Reviewer F1**
  - Spec source: design §6.3; Reviewer Finding F1
  - Spec text: "Every flavor-name reference must move to the standard six … The sweep must be exhaustive."
  - Implementation: added `test_mutant_wasteland_world_archetype_stat_ranges_standard_six` (globs every `worlds/*/archetypes.yaml`, asserts standard-six `stat_ranges` keys, fails-loud if no world archetypes found). RED now (12 dead keys in flickering_reach), GREEN once Dev remaps. The original genre-tier gate only covered `<pack>/archetypes.yaml` — a coverage gap, correctly caught by the Reviewer.
  - Rationale: world archetypes REPLACE genre archetypes in play (`effective_archetypes`), so the sweep gate must cover the world tier or the only playable world ships dead stat references.
  - Severity: minor (test-coverage addition; the underlying fix is Dev's trivial remap)
  - Forward impact: Dev applies the same Brawn→STR… mapping to `worlds/flickering_reach/archetypes.yaml`; the gate prevents this regressing in any future world.

### Reviewer (audit)
- **TEA: RED tests in sidequest-server (two-repo split)** → ✓ ACCEPTED by Reviewer: content has no test runner; the design (§6) is explicitly two-repo. Session Repos line + SM finish-ceremony impact correctly flagged.
- **TEA: calibration migration left as GREEN work** → ✓ ACCEPTED by Reviewer: pre-writing "pack ∉ COMBAT_PACKS" would assert on a test constant; the end-state is pinned by `test_..._combat_is_hp_depletion`, and Dev's COMBAT_PACKS edit mirrors the space_opera/elemental_harmony precedent exactly.
- **Dev: weapon damage = base dice only** → ✓ ACCEPTED by Reviewer: §4 defers per-weapon Trauma/Shock; base NdM is all hp_depletion needs and all 5 specs validate (no shock without shock_ac).
- **Dev: point_buy left unchanged** → ✓ ACCEPTED by Reviewer: §11.5 explicitly rules it out of Plan 1; no test gates it; builder seeds strain from final scores regardless.
- **Dev: magic.yaml comment fix** → ✓ ACCEPTED by Reviewer: a one-line comment correction (Instinct→WIS) is not authoring mechanics; it removes a dead stat name and is accurate to the swept rules.yaml.
- **UNDOCUMENTED — World-tier archetype sweep omitted:** §6.3 mandates "**Every** flavor-name reference must move to the standard six ... The sweep **must be exhaustive**." Neither TEA (tests only gate the genre-tier `archetypes.yaml`) nor Dev swept `worlds/flickering_reach/archetypes.yaml`, which retains 12 flavor-named `stat_ranges` keys. Because `effective_archetypes` (pack.py:297) makes world archetypes REPLACE genre archetypes in play and flickering_reach is the ONLY playable world, this is in-scope-and-missed, not a deferral. Severity: **HIGH** (combat-path `KeyError`, see Finding F1). → ✗ FLAGGED. → ✓ RESOLVED (round-trip 1): world archetypes remapped to standard-six, new world-tier gate added + passing, pack-wide hunt confirms zero flavor stat keys remain.