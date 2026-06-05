---
story_id: "87-2"
jira_key: "87-2"
epic: "87"
workflow: "tdd"
---
# Story 87-2: Story 2 — Classes & chargen

## Story Details
- **ID:** 87-2
- **Jira Key:** 87-2 (personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T10:50:42Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T09:56:47Z | 2026-06-05T09:56:47Z | 0m |
| red | 2026-06-05T09:56:47Z | 2026-06-05T10:18:19Z | 21m 32s |
| green | 2026-06-05T10:18:19Z | 2026-06-05T10:34:16Z | 15m 57s |
| review | 2026-06-05T10:34:16Z | 2026-06-05T10:41:29Z | 7m 13s |
| green | 2026-06-05T10:41:29Z | 2026-06-05T10:44:54Z | 3m 25s |
| review | 2026-06-05T10:44:54Z | 2026-06-05T10:50:42Z | 5m 48s |
| finish | 2026-06-05T10:50:42Z | - | - |

## Story Details

**Repos:** sidequest-server, sidequest-content

**Workflow:** tdd

**Design/Spec:** docs/superpowers/specs/2026-06-05-heavy-metal-wwn-classes-chargen-design.md

### Acceptance Criteria
> **REFRESHED 2026-06-05 (TEA) to the post-AMENDMENT real-magic scope** — supersedes the SM Assessment's "Casters are Effort-only / no spells (Story 3)" guardrail below, which predates Keith's scope change. Epic Story 3 is folded in.
- classes.yaml: 5 faithful-WWN classes (warrior, expert, necromancer, elementalist, pact_born) — correct chassis/role/prime per spec §3; warrior carries warrior:true; the three Mage traditions carry magic_access:wwn with FULL wwn_magic (effort_sources + casts_per_day_by_level + max_spell_level_by_level + prepared_by_level + starting_prepared resolving to real spells). Every class carries saving_throws (the spell-catalog load validator requires it once a catalog is present).
- spells_wwn.yaml authored as a faithful PORT of WWN High Magic spells (mechanics verbatim WWN; grim heavy_metal flavor reskin at most — where the retired pact/ledger doom-cost feeling re-homes). Loads into pack.wwn_spell_catalog (non-empty); every caster's starting_prepared resolves in the catalog; at least one caster starts with a damage spell.
- cast_spell beat added to the Blade-work combat with class_filter to [necromancer, elementalist, pact_born]; cast_spell EXCLUDED from non-caster encounter_beat_choices. wwn.magic config finalized.
- Each class has one signature ability (ADR-095) with grim dark-fantasy flavor; no separate Foci construct.
- rules.yaml: 5e allowed_classes/allowed_races/banned_spells/default_race removed; default_class→Warrior and class_label:Calling set; custom_rules (ledger_tracking/pact_cost_attribution) and the pact_working/debt_collection confrontations left UNTOUCHED (Story 4).
- 5e class names replaced everywhere: genre + evropi char_creation.yaml class_hints reference the 5 new ids; power_tiers.yaml re-keyed from 12 5e blocks to 5 WWN-display-name blocks; world typical_classes (evropi + long_foundry) updated.
- Cross-file consistency: no class_hint / typical_classes / power_tiers key references a class id/display-name absent from classes.yaml (test-enforced — protects reference-page anchors).
- Wiring: heavy_metal loads via load_genre_pack; chargen builds a character per class; each CASTER seeds a POPULATED SpellcastingState (prepared == starting_prepared[:capacity], NOT None) + an Effort pool; warrior/expert seed effort={}/spellcasting=None; cast_spell dispatch reachable for a caster (wwn.spell.cast span, cast spent, HP ablated); class_label shows 'Calling'. Full suite green vs recorded baseline.

## Branch Strategy

**Branch Strategy:** github-flow (feat/87-2-wwn-classes-chargen on develop for both sidequest-server and sidequest-content)

## Sm Assessment

**Setup complete.** Story 87-2 (heavy_metal → WWN, classes & chargen) is set up and ready for the RED phase.

- **Design is done and approved.** Leonard (Architect) brainstormed this with Keith and wrote the spec at `docs/superpowers/specs/2026-06-05-heavy-metal-wwn-classes-chargen-design.md` (committed on the orchestrator's `feat/87-2-wwn-classes-chargen` branch). **§4 is the file-by-file work order; §5 is the test contract.** Read the spec before writing tests — it is the source of truth, ahead of the story title.
- **Keith's directive (2026-06-05): "a port is a port — replace, don't remap."** Do not field-by-field translate the old 5e content. Author the faithful WWN port (template: `genre_packs/elemental_harmony/classes.yaml`) and replace the 5e scaffolding wholesale, genre tier AND the live `evropi` world.
- **Scope guardrails for the RED phase (Igor):**
  - This is **content + the wiring/consistency tests** — **no engine/Python changes**. The `wwn` module already exists (EH binding). Tests assert the *content* loads and chargen resolves; they do not drive new server behavior.
  - **Casters are Effort-only this story.** A test asserting a caster seeds an Effort pool with `SpellcastingState = None` (the EH "Vowed" `martial_artist` behavior) is correct. Do NOT write tests expecting castable spells / `cast_spell` beats — those are Story 3.
  - The cross-file **class-id consistency** test (AC5) is the highest-value new test — it protects reference-page anchors from id drift across `classes.yaml` / `char_creation.yaml` (×2) / `power_tiers.yaml` / world `typical_classes`.
  - **Record the full-suite baseline failure list FIRST** (`SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set), so a pre-existing failure isn't misread as a regression. Note: `test_heavy_metal_pack_loads_with_dual_dial_schema` was already migrated in Story 1 — no new calibration migration is expected here.
- **Repos:** `sidequest-content` (the heavy_metal YAML), `sidequest-server` (the tests). Both branched: `feat/87-2-wwn-classes-chargen` off `develop`.
- No Jira (personal project) — claim explicitly skipped.

**Handoff:** Igor (TEA) for the RED phase — author failing tests against the six ACs, anchored to spec §5.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (11 failing tests, ready for Dev) — verified `uv run pytest -n0` on the four files: 11 failed, 0 errored, 0 skipped, no collection/import errors.

> **SCOPE NOTE (read first):** mid-RED, Keith redirected — *"I want actual magic and shit … replaced with WWN."* Epic **Story 3 (magic content) is folded into 87-2** (now 13 pts; 87-3 canceled; Story 4 kept). The design spec carries a **2026-06-05 AMENDMENT banner** superseding the original Effort-only D3/§6. Story ACs were rewritten to match. The tests below assert **REAL WWN magic** (casters seed a populated `SpellcastingState`, a real ported spell catalog, `cast_spell` fires) — NOT the superseded Effort-only behavior.

**Test Files (all `sidequest-server`, branch `feat/87-2-wwn-classes-chargen`):**
- `tests/genre/test_heavy_metal_loads_wwn_classes.py` — pack-load + structure (4 tests): the 5 WWN classes with correct chassis markers (`warrior: true`; caster `magic_access: wwn` + FULL `wwn_magic`; `expert` no-magic), `saving_throws` on every class, a non-empty ported `wwn_spell_catalog` with every `starting_prepared` resolving, the Blade-work `cast_spell` beat `class_filter`ed to exactly the 3 casters, and a `rules.yaml` 5e-purge (`class_label: Calling`, `default_class`→Warrior, no 5e class/race/spell names, `default_race` dropped).
- `tests/integration/test_wwn_heavy_metal_chargen.py` — chargen seeding (5 parametrized): warrior/expert → `effort=={}`, `spellcasting is None`; each Mage tradition → Effort pool (formula-checked) + **populated** `SpellcastingState` (`prepared == starting_prepared[:capacity]`, `casts_remaining == casts_per_day`).
- `tests/integration/test_wwn_heavy_metal_dispatch.py` — cast e2e wiring (1 test, mirrors the mandated EH dispatch proof): real caster casts a **discovered** damage spell through the production `_apply_narration_result_to_snapshot` path → cast spent, opponent HP ablated, `wwn.spell.cast` span `refused=False`, B/X `magic.cast_spell_*` arm silent.
- `tests/genre/test_heavy_metal_class_id_consistency.py` — cross-file consistency (1 test): every `class_hint` (genre + evropi), `power_tiers.yaml` key, and world `typical_classes` resolves to a class in `classes.yaml` and no 5e class name survives. Reads YAML with `yaml.safe_load` (the files ARE the thing under test — not a source-grep).

**Tests Written:** 11 tests covering all 8 ACs.

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #6 test quality (meaningful assertions, no vacuous) | self-checked — every assert names a concrete value/identity; no `assert True`/bare-truthy | pass |
| #8 unsafe deserialization (`yaml.safe_load`) | `test_heavy_metal_class_id_consistency` uses `yaml.safe_load`, never `yaml.load` | failing (content) |
| #5 path handling (`pathlib`, `encoding=`) | consistency test uses `Path` + `open(encoding="utf-8")` | failing (content) |
| "No source-text wiring tests" (server CLAUDE.md) | wiring proven by the `wwn.spell.cast` / `state_patch.hp` OTEL spans + behavior, never by grepping source | n/a (satisfied by design) |

**Rules checked:** the content port has no new production `.py`; the applicable rules are test-hygiene (#6), safe-yaml (#8), path (#5) — all satisfied in the test code.
**Self-check:** 0 vacuous tests found.

**Guardrail for Dev (carried from SM):** record the FULL server-suite baseline failure list FIRST (`SIDEQUEST_DATABASE_URL` + on-disk content), so a pre-existing failure isn't misread as a regression. Once a spell catalog ships, the loader requires `saving_throws` on **every** class (`_validate_saving_throws_refs`, loader.py:656) — author it on all 5 or load fails. The cast e2e discovers the caster+damage-spell dynamically, so at least one caster's `starting_prepared` MUST include a damage spell (`damage_die` set), mirroring EH's `cinder_lance`.

**Handoff:** To Ponder (Dev) for GREEN — author the content per spec §3/§4 (AMENDED for real magic) to turn all 11 red.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed (sidequest-content, all under `genre_packs/heavy_metal/`):**
- `classes.yaml` (new) — 5 faithful-WWN Callings: warrior (`warrior: true`) + expert (no magic) + necromancer/elementalist/pact_born (Mage traditions, FULL `wwn_magic` + `starting_prepared`); `saving_throws` on every class; one signature ability each (Warrior carries the WWN pair).
- `spells_wwn.yaml` (new) — faithful WWN High Magic port (grim reskin); 8 spells; loads into `pack.wwn_spell_catalog`; every `starting_prepared` resolves; 3 prepared damage spells.
- `rules.yaml` — dropped 5e `allowed_classes`/`allowed_races`/`banned_spells`/`default_race`; `default_class: warrior`; `class_label: Calling`; added `cast_spell` beat to Blade-work combat with `class_filter: [Necromancer, Elementalist, Pact-born]`. Story-4 baggage (ledger/pact custom_rules + pact_working/debt_collection confrontations) left untouched.
- `char_creation.yaml` (genre) + `worlds/evropi/char_creation.yaml` — class_hints remapped to the 5 Calling display names.
- `power_tiers.yaml` — 12 5e blocks → 5 WWN-display-name blocks (fresh per-tier baroque-elegy prose).
- `worlds/evropi/archetypes.yaml` + `worlds/long_foundry/archetypes.yaml` — `typical_classes` remapped.

**Tests:** 11/11 story tests passing (GREEN). Full suite: 8 failed / 9349 passed / 1467 skipped — the 8 failures are the EXACT pre-existing baseline (test_61_12_output_format_compaction, test_enums message_type_count, 5× narration_clue_discovery_wiring, yield_handler_outbound); **0 regressions**.
**Branches (pushed):** `feat/87-2-wwn-classes-chargen` on sidequest-content (commit 37c8261) and sidequest-server (TEA's test commit b2b9b795). No server production code changed — pure content + the wiring/consistency tests.

**Handoff:** To next phase (verify/review).

### Dev Assessment — Rework R1 (post-review)

Granny (Reviewer) REJECTED with two findings; both fixed:
- **[HIGH] default_class wiring** — changed `genre_packs/heavy_metal/rules.yaml` `default_class: warrior` → `default_class: Warrior` (display name). The chargen builder resolves the default ClassDef by `display_name` only (builder.py:2286, no id fallback), so the lowercase id left a freeform-default character class-less. Empirically verified post-fix: `default_class: 'Warrior'` resolves to the warrior ClassDef with abilities `['Killing Blow', "Veteran's Luck"]` and `warrior: True`. No new test required (the existing rules-purge test already asserts `default_class.lower()=='warrior'`, which still passes); the fix makes the freeform-default path actually wire the class.
- **[LOW] ruff format** — `uv run ruff format` on the 4 story test files in `sidequest-server/tests/{genre,integration}/`. `ruff format --check` now clean; `ruff check` clean.

**Tests (post-rework):** 11/11 story tests GREEN; full suite 9349 passed / 8 failed / 1467 skipped — still the EXACT pre-existing baseline (0 regressions).
**Branches (pushed):** content `feat/87-2-wwn-classes-chargen` @ 7556563; server @ 2b2bbfac.
**Rework deviations:** none — the default_class fix aligns the content with the AC ("default_class→Warrior") and the EH/space_opera convention; it does not diverge from spec.

**Handoff:** Back to Granny (Reviewer) for re-review.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): epic Story 3 (magic content) was folded into 87-2 mid-flight per Keith; 87-3 is canceled and 87-4 (sweep/calibration/playtest) now follows 87-2 directly. Affects `sprint/current-sprint.yaml` (87-3 status) and `docs/superpowers/specs/2026-06-05-heavy-metal-wwn-classes-chargen-design.md` (AMENDMENT banner) — both already updated; Story 4's "exhaustive 5e-baggage sweep" should treat 87-2 as having already replaced class names + magic. *Found by TEA during test design.*
- **Gap** (non-blocking): `wwn.attribute_map` for heavy_metal maps `INTELLIGENCE: INT` / `CHARISMA: CHA`; the chargen test reads the caster's governing stat through that map, so if Dev sets a caster's `governing_attr` to a key not in the map the Effort-max assertion will KeyError loudly (intended). Affects `genre_packs/heavy_metal/classes.yaml` (caster `effort_sources.governing_attr` must be one of the 6 canonical keys). *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): the SM/TEA guardrail cited `_validate_saving_throws_refs` (loader.py:656) as the enforcer requiring `saving_throws` on every class once a catalog ships — but that validator gates on `has_spell_catalogs=(path / "spells").is_dir()` (the B/X `spells/` directory), so it is a **no-op for WWN packs** that ship `spells_wwn.yaml`. For heavy_metal the requirement is enforced only by the story tests, not by the loader. `saving_throws` was authored on all 5 classes anyway (test-driven), so behavior is correct; flagging that the loader does NOT fail loud if a future WWN caster class omits `saving_throws`. Affects `sidequest-server/sidequest/genre/loader.py:1466-1472` (could extend `has_spell_catalogs` to also detect `spells_wwn.yaml` for WWN packs). *Found by Dev during implementation.*
- **Improvement** (non-blocking): `worlds/evropi/archetype_funnels.yaml` and `worlds/long_foundry/archetype_funnels.yaml` carry NPC archetype display-names that contain 5e class words ("J\`rook Bard", "Coil and Brand Sorcerer") as flavor — these are NOT class references (funnels key off Jungian×rpg_role pairs, no `class_hint`/`typical_classes`), so they were left untouched per spec §4.7. Story 4's "exhaustive 5e-baggage sweep" may want to reskin these display-names for tone consistency. *Found by Dev during implementation.*
- **Improvement** (non-blocking, R1 rework): the builder silently skips class seeding when `default_class` doesn't resolve to a `display_name` (builder.py:2286 comment: "silently skips rather than raising"). Granny's HIGH finding was triggered by this. Fixed at the content layer for heavy_metal, but the engine could fail loud (or fall back to the first class) when `default_class` is set but unresolvable — a future-proofing for any pack author who fat-fingers the default. Affects `sidequest-server/sidequest/game/builder.py`. *Found by Dev during R1 rework.*

### Reviewer (code review) — Round 2
- **Improvement** (non-blocking): endorsing Dev's R1-rework finding — the builder's silent-skip on an unresolvable `default_class` (builder.py:2286) should fail loud or fall back to the first declared class, so a future pack author's typo can't ship a class-less default. This story's content is correct; the engine hardening is the durable fix. Affects `sidequest-server/sidequest/game/builder.py`. *Found by Reviewer during re-review.*

### Reviewer (code review)
- **Gap** (blocking): `default_class: warrior` (lowercase id) does not resolve through the builder's `display_name`-only class lookup (builder.py:2286), so a freeform-crucible character with no `class_hint` gets no ClassDef — no signature abilities, no `warrior:true`. Affects `genre_packs/heavy_metal/rules.yaml` (change to `default_class: Warrior`, matching the AC text and the EH/space_opera convention). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the 4 new test files in `sidequest-server/tests/{genre,integration}/` fail `ruff format --check` (pure reflow, lint is clean). Affects those 4 files (run `uv run ruff format`). Bundled into the same green-rework pass. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the Necromancer crucible choices ("A tithe you were born into" / "A Njörkte who paid…") retain `rpg_role_hint: healer` while the Necromancer class `rpg_role` is `control`. Out of scope here (spec only mandated `class_hint` replacement) and the hint feeds the archetype resolver independently, but Story 4 may want to reconcile the role hint with the new class identity. Affects `genre_packs/heavy_metal/char_creation.yaml` + `worlds/evropi/char_creation.yaml`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Tests assert REAL WWN magic, not the spec's original Effort-only caster design**
  - Spec source: `docs/superpowers/specs/2026-06-05-heavy-metal-wwn-classes-chargen-design.md`, original D3 + §6
  - Spec text: "Story-2 casters carry `effort_sources` only … no `casts_per_day_by_level` / … / `starting_prepared` … `SpellcastingState` seeds as `None`" and non-goal "No spells, no `cast_spell` wiring, no `spells_wwn.yaml` (Story 3). Casters are Effort-only."
  - Implementation: tests assert casters seed a POPULATED `SpellcastingState` (prepared spells, `casts_remaining`), a non-empty `wwn_spell_catalog`, and a working `cast_spell` dispatch — i.e. the EH Channeler shape, not the Effort-only Martial Artist shape.
  - Rationale: Keith overrode the original scope mid-RED ("I want actual magic and shit … replaced with WWN"); epic Story 3 folded into 87-2; the design spec was amended (2026-06-05 AMENDMENT banner) and the story ACs rewritten. Per spec-authority the session scope / story ACs (highest authority) govern over the original spec body.
  - Severity: major
  - Forward impact: 87-3 canceled (absorbed); Story 4's 5e/magic sweep should assume 87-2 already shipped class names + real spells; Dev (GREEN) must author `spells_wwn.yaml` + full caster `wwn_magic` + `saving_throws` on every class + the `cast_spell` beat, not just classes.

### Dev (implementation)
- **typical_classes 5e→WWN name mapping derived (spec gave an explicit table only for char_creation class_hints)**
  - Spec source: context-story-87-2 AC6 / spec §4.6
  - Spec text: "world typical_classes (evropi + long_foundry) updated" / "replace 5e class names in `typical_classes:` with the new ids/display names" — no per-name mapping table given (unlike §4.3/§4.4 which map the char_creation hints explicitly).
  - Implementation: applied a thematic many-to-one mapping — Fighter/Paladin→Warrior, Rogue/Bard/Ranger/Monk→Expert, Cleric→Necromancer, Druid/Wizard→Elementalist, Warlock/Sorcerer→Pact-born — and de-duplicated within each archetype's list.
  - Rationale: only the 5 Callings exist now; the mapping mirrors the chassis logic of §4.3/§4.4 (death-accounting→Necromancer, forge/craft→Elementalist, bargain/bloodline→Pact-born) and keeps each archetype's flavor intact.
  - Severity: minor
  - Forward impact: none — typical_classes is archetype flavor metadata; the consistency test (AC7) confirms every value resolves to a real class. Story 4 may re-tune if a world wants finer archetype/class pairing.
- **evropi "mis-copied Book" crucible choice mapped to Elementalist**
  - Spec source: spec §4.4
  - Spec text: "the mis-copied Book → `necromancer` or `elementalist` (writer's call)"
  - Implementation: chose Elementalist for the Wizard→? slot.
  - Rationale: explicitly writer's-call per spec; Elementalist is the guild-craft tradition, the closest fit for the scholar-copyist's "a craft that costs the craftsman" idiom.
  - Severity: minor
  - Forward impact: none.

### Reviewer (audit)
- **TEA: "tests assert REAL WWN magic"** → ✓ ACCEPTED by Reviewer: Keith's documented mid-RED scope change; spec carries the 2026-06-05 AMENDMENT banner and the ACs were rewritten. Higher-authority session scope governs. Sound.
- **Dev: "typical_classes 5e→WWN mapping derived"** → ✓ ACCEPTED by Reviewer: the spec gave an explicit table only for char_creation hints; Dev's thematic many-to-one mapping mirrors §4.3/§4.4 chassis logic and the AC7 consistency test confirms every value resolves. Verified the transform touched only `typical_classes` list items (surrounding `typical_races`/`stat_ranges` intact). Sound.
- **Dev: "mis-copied Book → Elementalist"** → ✓ ACCEPTED by Reviewer: spec §4.4 explicitly says "necromancer or elementalist (writer's call)". Within latitude.
- **UNDOCUMENTED (Reviewer-found): `default_class` uses the lowercase id `warrior`, not the display name `Warrior`.** Spec §4.2 body literally wrote `default_class: warrior` (the source of the error), BUT the AC text says "default_class→**Warrior**" and the engine resolves class only by `display_name` (builder.py:2286, no id fallback). Every other WWN/SWN pack uses the display name (`Wanderer`, `Smuggler`). Empirically confirmed: `next(c for c in pack.classes if c.display_name == 'warrior')` → None → no ClassDef, no abilities/`warrior:true` seeded on the freeform-default chargen path. The story test masks it (`default_class.lower() == 'warrior'`). Severity: HIGH (see assessment). Documented here as a Dev-undocumented divergence from the AC + convention. → **R1 rework RESOLVED:** Dev set `default_class: Warrior`; preflight verified it resolves to the warrior ClassDef with `warrior_flag: True`. Now AC- and convention-compliant. ✓ ACCEPTED.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (ruff format on 4 test files) + GREEN suite | confirmed 1, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled returned; 8 disabled via workflow.reviewer_subagents — Reviewer performed those domains manually, appropriate for a content-only change)
**Total findings:** 2 confirmed (1 blocking default_class wiring [HIGH], 1 non-blocking ruff format [LOW]), 0 dismissed, 1 deferred (rpg_role_hint reconciliation → Story 4)

Preflight verdict: full suite 9349 passed / 8 failed (EXACT pre-existing baseline — 0 regressions); 11/11 story tests GREEN; ruff lint clean; ruff format --check fails on all 4 test files (pure reflow); content loads end-to-end via load_genre_pack (5 classes, 8-spell catalog, label/default wired).

## Rule Compliance

Project rules checked against this content + tests diff (CLAUDE.md, content/CLAUDE.md, SOUL.md, server/CLAUDE.md):

- **No Silent Fallbacks** (CRITICAL) — VIOLATION found: `default_class: warrior` resolves to no ClassDef and the builder *silently* skips class seeding (builder.py:2286 comment: "silently skips rather than raising"). The unresolvable default triggers exactly the silent-fallback the rule forbids. → blocking finding.
- **No half-wired features** (CRITICAL) — VIOLATION: the freeform-default chargen path leaves the class system (the story's headline feature) unwired for defaulted characters. → blocking finding (same root cause as above).
- **Crunch in the Genre, Flavor in the World** (SOUL) — COMPLIANT: mechanics (classes, magic, cast beat, saving_throws) live in the genre tier (`genre_packs/heavy_metal/`); world files carry only flavor (`typical_classes`, crucible prose). Races correctly dropped from genre (world-tier).
- **No Source-Text Wiring Tests** (server CLAUDE.md) — COMPLIANT: the cast e2e proves wiring via the `wwn.spell.cast` OTEL span + HP ablation behavior, not by grepping source. The consistency test reads YAML with `yaml.safe_load` (the files ARE the unit under test) — not a source-grep.
- **Unsafe deserialization #8 (python.md)** — COMPLIANT: `test_heavy_metal_class_id_consistency.py` uses `yaml.safe_load`, never `yaml.load`.
- **Path handling #5 (python.md)** — COMPLIANT: consistency test uses `pathlib.Path` + `open(encoding="utf-8")`.
- **Test quality #6 (python.md)** — COMPLIANT: every story-test assertion names a concrete value/identity (class ids, spell ids, HP deltas, span attrs); no vacuous `assert True`.
- **ruff format (cleanliness)** — VIOLATION (LOW): 4 test files unformatted. Ungated by check-all but real; bundled into rework.
- **Reference-page anchor stability** (content CLAUDE.md) — COMPLIANT: AC7 consistency test enforces that every class reference (class_hint ×2, power_tiers keys, typical_classes ×2) resolves to a classes.yaml id/display_name, protecting anchors from drift.
- **OTEL Observability** — COMPLIANT (no new subsystem): the cast spine emits `wwn.spell.cast` (asserted refused=False); no new backend subsystem was added that would need new spans (content-only).

## Reviewer Observations

- [HIGH] `default_class: warrior` (lowercase id) does not resolve via the builder's `display_name`-only lookup — empirically `next(c for c in pack.classes if c.display_name=='warrior')` returns None — at `genre_packs/heavy_metal/rules.yaml`. Freeform-default characters get no class abilities / no `warrior:true`. Fix: `default_class: Warrior`.
- [LOW] 4 new test files fail `ruff format --check` (pure reflow, lint clean) at `tests/genre/`+`tests/integration/` [confirmed by preflight].
- [VERIFIED] `cast_spell` class_filter uses display names `[Necromancer, Elementalist, Pact-born]` — evidence: rules.yaml combat beat; loader validates class_filter against `display_name` (loader.py:628/634) and the pack loaded clean. Complies; gate fires only for casters.
- [VERIFIED] No class lists `cast_spell` in `encounter_beat_choices` — evidence: classes.yaml grep + `test_heavy_metal_classes_are_faithful_wwn_chassis` asserts absence per class. The beat is offered solely via the rules.yaml class_filter.
- [VERIFIED] Every caster `starting_prepared` resolves in the catalog and ≥1 caster prepares a damage spell — evidence: `_validate_wwn_starting_prepared_refs` (loader.py:721) ran clean at load; necromancer→wracking_bolt (damage_die 1d6) etc.; dispatch e2e ablated opponent HP.
- [VERIFIED] `saving_throws` authored on all 5 classes with values in the legal 2..20 d20 range — evidence: classes.yaml; `SavingThrowsTable._validate` (rules.py:285) would reject out-of-range and the pack loaded.
- [VERIFIED] typical_classes transform was surgical — evidence: archetypes diffs touch only `typical_classes` list items; `typical_races`/`stat_ranges` blocks unchanged; AC7 consistency test green.
- [VERIFIED] Story-4 baggage untouched — evidence: rules.yaml diff retains `ledger_tracking`/`pact_cost_attribution` custom_rules and the `pact_working`/`debt_collection` confrontations (D6 / spec §4.2).

## Devil's Advocate

Argue this is broken. Start with the default path, because that is where it actually is broken: heavy_metal's crucible scene sets `allows_freeform: true`. A player who types their own crucible answer instead of touching one of the canned tokens produces a `SceneResult` with `class_hint=None`. There is no later scene that forces a class. So `class_str` falls to `default_class`, which I set to the lowercase id `warrior`. The builder resolves classes ONLY by `display_name` (builder.py:2286) with no id fallback and no fail-loud — it "silently skips" — so that character is built with `char_class="warrior"` (lowercase, which will read wrong on the sheet) and, worse, with `_resolved_class_def=None`: no Killing Blow, no Veteran's Luck, no `warrior:true`. The headline feature of this very story — the class system — is dark for exactly the player who exercised the game's headline freedom (freeform input, the Zork-problem principle SOUL.md prizes). The test suite is complicit: it asserts `default_class.lower()=='warrior'`, which is true for both the broken id and the correct display name, so green tells us nothing here.

What else? Consider a malicious/contrarian player who freeform-answers EVERY scene: they reach confirmation with no class, no race hint either (race_str falls to `_default_race`, which I dropped — so it falls to the literal `"Human"` fallback in builder.py:2001; acceptable, races are world-tier). Consider a stressed loader: the pack has caster classes with `casts_per_day_by_level` set, so if a future edit deletes `spells_wwn.yaml` the loader fails loud (good, verified path). Consider the cast beat: `damage_channel: none` — if the WWN engine ever stopped special-casing cast_spell, casting would deal zero; but the dispatch e2e proves the engine routes damage today. Consider a confused author: power_tiers keys must equal class display_names exactly; a future rename of a class without updating power_tiers would bad-anchor — AC7's consistency test guards that, so it is caught. The one true wound is the default_class id/display mismatch. It is small in blast radius but it is a real silent-fallback wiring gap in the feature under test, contradicts the AC's own wording ("default_class→Warrior"), and breaks the universal pack convention. One character fixes it. Granny does not hold with shipping a known-dark fallback.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | `default_class: warrior` (lowercase id) doesn't resolve via the builder's `display_name`-only class lookup → freeform-default characters silently get no ClassDef (no abilities, no `warrior:true`). Violates No-Silent-Fallbacks + No-Half-Wired; contradicts the AC ("default_class→Warrior") and the EH/space_opera convention. | `genre_packs/heavy_metal/rules.yaml` (`default_class:`) | Change `default_class: warrior` → `default_class: Warrior`. Re-run the 4 story files + confirm full suite stays at the 8-failure baseline. |
| [LOW] | 4 new test files fail `ruff format --check` (pure reflow; lint clean). | `sidequest-server/tests/genre/test_heavy_metal_loads_wwn_classes.py`, `tests/genre/test_heavy_metal_class_id_consistency.py`, `tests/integration/test_wwn_heavy_metal_chargen.py`, `tests/integration/test_wwn_heavy_metal_dispatch.py` | `uv run ruff format` the 4 files. |

Findings are content + format (no test-logic change) → green rework lane (Dev). Tests stay green throughout; the default_class fix is masked by the existing test, so no new test is required — but Dev should eyeball that a freeform-default build now resolves to the Warrior ClassDef.

**Tags:** [EDGE] n/a (disabled — covered manually: freeform-default path is the edge that broke) · [SILENT] default_class silent-skip (HIGH, manual) · [TEST] story tests sound, but mask default_class via `.lower()` (manual) · [DOC] class/spell header comments accurate (manual, clean) · [TYPE] saving_throws/wwn_magic schema-valid (manual, clean) · [SEC] n/a content (no auth/secrets/injection surface) · [SIMPLE] no over-engineering; power_tiers is flavor-only (manual, clean) · [RULE] No-Silent-Fallbacks + No-Half-Wired violated by default_class (HIGH)

**Handoff:** Back to Ponder (Dev) for the green-rework fixes.
---

## Subagent Results — Re-Review (Round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (suite GREEN, ruff clean, fix verified) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled returned clean; 8 disabled via settings — covered manually)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred — both round-1 findings verified fixed.

## Reviewer Assessment — Re-Review (Round 2)

**Verdict:** APPROVED

Both round-1 rejection findings are resolved and independently verified:

- **[HIGH → FIXED] default_class wiring** — `genre_packs/heavy_metal/rules.yaml` now reads `default_class: Warrior` (display name) with an explanatory comment. Preflight verified the resolution live: `default_class Warrior -> resolves: warrior, warrior_flag: True` — a freeform-default character now wires the Warrior ClassDef (Killing Blow + Veteran's Luck + `warrior:true`). The fix matches the AC ("default_class→Warrior") and the EH/space_opera convention. No silent fallback remains.
- **[LOW → FIXED] ruff format** — the 4 story test files now pass both `ruff check` and `ruff format --check`. I independently audited the format commit (b2b9b795..2b2bbfac): every change is pure ruff reflow — set literals split one-per-line (identical members), redundant `(x or [])` parens removed, long asserts/defs wrapped — with byte-identical assertion conditions and messages. No semantic test change snuck in under the "format" label.

**Data flow traced:** chargen `class_hint`/freeform → `class_str` → builder resolves ClassDef by `display_name` → now resolves for the default path (Warrior) as well as the canned/caster paths. Safe.
**Pattern observed:** display-name-keyed class resolution is consistent across `default_class`, `class_hint` (×2 char_creation), `class_filter`, `power_tiers` keys, and `typical_classes` — all anchored to classes.yaml and guarded by the AC7 consistency test.
**Error handling:** the only silent-fallback risk (unresolvable default) is closed at the content layer; Dev filed a non-blocking engine improvement (fail-loud on unresolvable `default_class`) for future hardening.
**Regression status:** full suite 9349 passed / 8 failed (EXACT pre-existing baseline, 0 regressions); 11/11 story tests GREEN.

**Tags:** [EDGE] freeform-default path now resolves (the round-1 edge) — fixed · [SILENT] default_class silent-skip closed at content layer — fixed · [TEST] story tests sound; format reflow verified non-semantic · [DOC] new default_class comment is accurate and load-bearing · [TYPE] saving_throws/wwn_magic schema-valid (unchanged) · [SEC] n/a (content; no auth/secrets/injection surface) · [SIMPLE] no over-engineering introduced by the rework · [RULE] No-Silent-Fallbacks + No-Half-Wired now satisfied

**Handoff:** To Captain Carrot (SM) for finish-story.