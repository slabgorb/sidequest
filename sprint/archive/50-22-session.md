---
story_id: "50-22"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 50-22: Scene harness: hydrate magic_state + Character.abilities (ADR-092 follow-on)

## Story Details
- **ID:** 50-22
- **Jira Key:** (N/A — personal project, no Jira)
- **Workflow:** tdd (phased)
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-18T12:20:23Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-18 | 2026-05-18T11:42:13Z | 11h 42m |
| red | 2026-05-18T11:42:13Z | 2026-05-18T11:54:48Z | 12m 35s |
| green | 2026-05-18T11:54:48Z | 2026-05-18T12:01:10Z | 6m 22s |
| spec-check | 2026-05-18T12:01:10Z | 2026-05-18T12:03:28Z | 2m 18s |
| verify | 2026-05-18T12:03:28Z | 2026-05-18T12:12:06Z | 8m 38s |
| review | 2026-05-18T12:12:06Z | 2026-05-18T12:18:29Z | 6m 23s |
| spec-reconcile | 2026-05-18T12:18:29Z | 2026-05-18T12:20:23Z | 1m 54s |
| finish | 2026-05-18T12:20:23Z | - | - |

## Story Context

### Summary
Extend `hydrate_fixture` in `sidequest/game/scene_harness.py` to read and hydrate two new top-level fixture blocks:

1. **`magic_state:`** — project to `GameSnapshot.magic_state` (a `MagicState` instance per `sidequest/magic/state.py`)
2. **`abilities:` under `character:`** — project to `Character.abilities` (list of `AbilityDefinition` per `sidequest/protocol/models.py`)

This is a direct follow-on to story 50-21 (scene-harness StructuredEncounter hydration). The story unblocks Wave 2 magic fixtures: `magic_active_elemental` (mid-ritual), `magic_drained_elemental` (empty pool), and class-ability-active fixtures.

**Design references:**
- **ADR-092** (scene harness HTTP endpoint + fixture hydration contract)
- **ADR-095** (class mechanical surface — `AbilityDefinition` structure)
- **ADR-014** (Diamonds and Coal — magic state is Diamond, must be hydrated faithfully per spec)

### Acceptance Criteria

**AC-1: Character.abilities hydration**
- Fixture `character:` block may contain an optional `abilities:` list
- Each entry is a mapping with: `name`, `genre_description`, `mechanical_effect`, `source` (Race/Class/Item/Play), and optional `involuntary` (default false)
- All fields are validated as `AbilityDefinition` (pydantic constructor)
- Missing/malformed `abilities:` block raises `FixtureValidationError` (HTTP 422) per ADR-092 "Failure is loud"
- Empty or absent `abilities:` list projects to `Character.abilities=[]` (default)

**AC-2: MagicState hydration**
- Fixture may contain an optional top-level `magic_state:` block
- Block includes:
  - `config:` (WorldMagicConfig shape — genre pack binding, read at runtime)
  - Optional `ledger:` (dict of BarKey serialized → LedgerBar; defaults to empty)
  - Optional `confrontations:` (list of ConfrontationDefinition; defaults to empty)
  - Optional `control_tier:` (dict of actor_id → int; defaults to empty)
  - Optional `known_spells:`, `prepared_spells:`, `spent_spells:` (advanced — may be empty for basic fixtures)
- Missing/malformed `magic_state:` block raises `FixtureValidationError` (HTTP 422)
- Absence of `magic_state:` block leaves `GameSnapshot.magic_state=None` (current behavior, backward compat)

**AC-3: No silent defaults**
- If `magic_state:` is present but `config:` is missing or malformed, raise loudly (FixtureValidationError)
- If `config:` names a nonexistent genre/world, the genre loader will fail at save time (acceptable — fixture author has guidance)
- No fallback to empty MagicState or synthetic config

**AC-4: Integration with existing hydration**
- Both features coexist with existing hydration: `character:`, `characters:`, `scenario_state:`, `encounter:`, `npcs:`
- No breaking changes to prior hydration paths (stories 50-18 through 50-21 fixtures remain green)

**AC-5: Test coverage**
- Unit tests for `_hydrate_character()` validating `abilities:` field:
  - Valid abilities list with all AbilityDefinition fields
  - Empty abilities list
  - Missing abilities block (defaults to empty list)
  - Malformed field in an ability entry (e.g., missing `source`, bad `involuntary` type) → FixtureValidationError with field detail
- Unit tests for top-level `_hydrate_magic_state()` helper (if extracted as a function):
  - Valid `config:` block (minimal WorldMagicConfig)
  - Optional `ledger:` / `confrontations:` / `control_tier:` (sparse fixtures)
  - Missing `config:` in `magic_state:` block → FixtureValidationError
  - Malformed fields → FixtureValidationError with detail
  - Absence of `magic_state:` block → snapshot.magic_state=None (regression lock)

**AC-6: Wiring test**
- A fixture with `magic_state:` and `character: { ..., abilities: [...] }` hydrates end-to-end
- Persisted snapshot.magic_state is non-None; snapshot.characters[0].abilities is populated
- Both survive a round-trip through SqliteStore (save and load)

**AC-7: Canonical fixture expectations (blocked)**
- Currently blocked on elemental_harmony having no live worlds per the story description
- Once unblocked: author fixtures `magic_active_elemental`, `magic_drained_elemental` as Wave 2 test targets
- For now: the implementation is complete with no fixtures that use these fields; the tests exercise the hydration paths with synthetic YAML

### Technical Approach

1. **Extend `_hydrate_character()`** in `scene_harness.py` to read `character.abilities`:
   - Extract `data.get("abilities")` — if present and not None, validate as list of dicts
   - For each dict, construct `AbilityDefinition(**entry)` (pydantic validation catches missing/bad fields)
   - Pass `abilities=hydrated_list` to `Character()` constructor
   - If absent or empty, `Character.abilities` defaults to `[]` (via pydantic Field default)

2. **Add `_hydrate_magic_state()` helper** (or inline in hydrate_fixture if simpler):
   - Extract `data.get("magic_state")` — if None, skip (leave GameSnapshot.magic_state=None)
   - If present, validate as dict
   - Extract required `config:` field; validate as WorldMagicConfig (pydantic ValidationError → FixtureValidationError wrap)
   - Extract optional fields: `ledger`, `confrontations`, `control_tier`, `known_spells`, `prepared_spells`, `spent_spells`
   - Construct `MagicState(**kwargs)` — pydantic validation
   - Return the hydrated MagicState; caller projects to GameSnapshot.magic_state

3. **Error handling** (matching 50-20, 50-21 pattern):
   - Wrap pydantic ValidationError as FixtureValidationError with field-level detail
   - Include fixture name in error message for fixture-author clarity
   - No silent fallback to defaults (ADR-092 "Failure is loud")

4. **Test fixture** (synthetic YAML for unit tests):
   ```yaml
   genre: mutant_wasteland
   world: flickering_reach
   
   magic_state:
     config:
       world_slug: flickering_reach
       ledger_bars: []
       confrontations_by_name: {}
   
   character:
     name: Mage-Test
     description: A practitioner
     personality: Focused
     level: 2
     hp: 15
     max_hp: 15
     backstory: Studied the arts
     char_class: Mage
     race: Human
     abilities:
       - name: Fireball
         genre_description: Hurl flames at enemies
         mechanical_effect: 2d6 damage, area effect
         source: Class
         involuntary: false
   ```

### Scope Guard
- Do NOT add elemental_harmony worlds or author magic fixtures in this story
  - Those are blocked pending content work
  - This story delivers the hydration implementation only
  - Wave 2 fixtures (`magic_active_elemental`, `magic_drained_elemental`) will be authored in a follow-on story when the worlds exist
- Do NOT change the MagicState API (add/remove/rename fields)
  - Hydration uses the existing shape from `sidequest/magic/state.py`
  - Any MagicState schema changes are separate architectural decisions

### Schema References
- `sidequest/magic/state.py:MagicState` — shape to hydrate into
- `sidequest/protocol/models.py:AbilityDefinition` — ability shape with `source` enum
- `sidequest/game/character.py:Character` — embedding `abilities: list[AbilityDefinition]`
- `sidequest/genre/models/magic.py:WorldMagicConfig` — genre pack magic config (validator catches bad shapes)

## Sm Assessment

**Story selected:** 50-22 — recommended over 50-9 (p3 polish), 48-3 (13pt off-theme local-LLM training), and 48-4 (no model to A/B against until 48-3 lands).

**Rationale:**
- **Continuity** — direct follow-on to the just-completed 50-21 (scene-harness StructuredEncounter hydration). Same `hydrate_fixture` seam, same pattern established across 50-18→50-21. Low cold-start cost for TEA/Dev.
- **On-theme** — Sprint 3 is "Playtest 3 closeout — MP correctness, state hygiene, post-port cleanup." Fixture-hydration fidelity is state hygiene; this is squarely in the ward.
- **Clean scope boundary** — the hydration *implementation* (this story) is unblocked. The downstream Wave 2 *fixtures* (`magic_active_elemental`, `magic_drained_elemental`) are blocked on elemental_harmony having no live worlds. AC-7 correctly fences that off as a follow-on. TEA must test hydration paths with synthetic YAML, NOT against a live elemental world.

**Setup verification:**
- Session file created (`.session/50-22-session.md`), context written with technical approach + 7 ACs.
- Branch `feat/50-22-scene-harness-magic-abilities` cut off `sidequest-server/develop` — confirmed correct base via `.pennyfarthing/repos.yaml` (server `default_branch: develop`; only orchestrator targets `main`).
- Sprint YAML: 50-22 → `in_progress`, assignee `slabgorb`, started 2026-05-18.
- Jira: **explicitly skipped** — SideQuest is a personal project, no Jira (standing doctrine). `jira_key` intentionally empty.

**Watch-outs for downstream agents:**
- ADR-014 (Diamonds and Coal): magic state is Diamond — hydrate faithfully, no synthetic/empty-MagicState fallback. AC-3 enforces this; reviewer should hold the line.
- ADR-092 "Failure is loud": malformed `magic_state:`/`abilities:` must raise `FixtureValidationError` (HTTP 422), never silent defaults. This is also a project-wide "No Silent Fallbacks" critical.
- Scope guard is real: do NOT touch the MagicState API or add elemental_harmony content in this story. Schema changes are separate architectural decisions.

**Handoff:** phased tdd workflow → RED phase → TEA (Radar O'Reilly).

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): The session Schema References cite `sidequest/genre/models/magic.py:WorldMagicConfig`, but `WorldMagicConfig` actually lives in `sidequest/magic/models.py:287` (and `MagicState` at `sidequest/magic/state.py:123` imports it from there). Affects the 50-22 implementation in `sidequest/sidequest/game/scene_harness.py` — Dev must import `WorldMagicConfig`/`MagicState` from `sidequest.magic.*`, not `sidequest.genre.models.magic`. *Found by TEA during test design.*
- **Gap** (non-blocking): The session Technical Approach's example config (`config: {world_slug, ledger_bars: [], confrontations_by_name: {}}`) is **invalid** against `WorldMagicConfig`, which is `model_config={"extra": "forbid"}` with **11 required fields** (world_slug, genre_slug, allowed_sources, active_plugins, intensity, world_knowledge, visibility, hard_limits, cost_types, ledger_bars, narrator_register) and **no** `confrontations_by_name` field. Affects Dev — follow the corrected minimal-valid config in `tests/game/test_scene_harness_hydrator.py::_MINIMAL_WORLD_MAGIC_CONFIG_YAML`, not the session example. *Found by TEA during test design.*
- **Improvement** (non-blocking): The TEA on-activation context gate command `pf validate context-story {story_id}` is broken — the `pf validate` Click group declares both a variadic `[NAMES]...` argument and subcommands, so `context-story` is parsed as a validator NAME and never dispatches to the subcommand (`[ERROR] Unknown validator(s): context-story`). Worked around via `pf validate context` (exit 0) + manual session inspection. Affects `.pennyfarthing` validate CLI / every future TEA activation on this project. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The session ## Story Context is stale on three independent counts that should be corrected at the source so future stories don't inherit them: (1) ### Schema References cites `sidequest/genre/models/magic.py:WorldMagicConfig` (real path `sidequest/magic/models.py:287`); (2) ### Technical Approach item 4's example `config:` is invalid against the `extra="forbid"` `WorldMagicConfig`; (3) ### Technical Approach item 2's step-wise "extract config / `MagicState(**kwargs)`" recipe is superseded by the cleaner whole-block `MagicState.model_validate`. Affects `.session/50-22-session.md` (and any context-doc generator that produced it) — Architect/SM should correct the Schema References + Technical Approach. Implementation followed TEA's tests (higher spec authority); all green. *Found by Dev during implementation.*
- No other upstream findings during implementation.

### TEA (verify)
- **Improvement** (non-blocking, resolved in-phase): The `magic.state_hydrated` OTEL event shipped from green untested *and* untestable — Dev's bound import (`from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish`) is inconsistent with the `scene_harness_router.py` sibling convention and cannot be intercepted by the standard `_capture_events` harness (it monkeypatches the module attribute). Fixed during verify: realigned to `import watcher_hub as _hub` + `_hub.publish_event(...)` and added `test_scene_harness_emits_magic_state_hydrated_span`. Affects `sidequest/game/scene_harness.py` + `tests/server/test_scene_harness.py` — already applied (`36e6c21`). Forward note: future subsystem-touching code in `sidequest/game/` should use the module-qualified `_hub.publish_event` form so OTEL events stay capturable. *Found by TEA (simplify-quality) during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): Abilities pydantic `ValidationError` is wrapped by `hydrate_fixture` at `characters[N] validation failed` granularity, not `characters[N].abilities[M] ...` — fixture-author ergonomics are marginally coarser. This mirrors the `known_facts` sibling exactly, so it is a *consistency* state, not a 50-22 regression. Affects `sidequest/game/scene_harness.py` (`_hydrate_character` / the singular+multi-PC wrap sites) — a future ergonomics pass should add the `.abilities[M]`/`.known_facts[M]` sub-index across both blocks together, not 50-22 alone. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `AbilityDefinition.name`/`genre_description`/`mechanical_effect` are plain `str` (not `NonBlankString`), so a fixture declaring `name: ""` hydrates a blank-named ability silently. This is the model's existing contract (out of 50-22 scope per the SM scope guard). Affects `sidequest/protocol/models.py:AbilityDefinition` — a model-hardening story could add non-blank validators if blank abilities ever cause downstream confusion. *Found by Reviewer during code review.*

## Design Deviations

No deviations from spec at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Corrected the spec's invalid example `magic_state.config` shape**
  - Spec source: `.session/50-22-session.md` → ## Story Context → ### Technical Approach, item 4 (Test fixture YAML)
  - Spec text: `config:\n  world_slug: flickering_reach\n  ledger_bars: []\n  confrontations_by_name: {}`
  - Implementation: Tests use a fully-valid 11-field `WorldMagicConfig` block (`_MINIMAL_WORLD_MAGIC_CONFIG_YAML`) mirroring `tests/magic/conftest.py::world_config`; the stale 3-field example is instead asserted *invalid* by `test_magic_state_config_extra_field_rejected`
  - Rationale: `WorldMagicConfig` is `extra="forbid"` with 11 required fields and no `confrontations_by_name` field; the spec example cannot construct and would have made every magic_state test un-writable
  - Severity: minor
  - Forward impact: Dev must follow the test fixtures, not the session Technical Approach example (see paired Delivery Finding); Architect may want to correct the session/context example text
- **AC-7 satisfied by synthetic YAML, no canonical elemental fixtures authored**
  - Spec source: `.session/50-22-session.md` → ### Acceptance Criteria → AC-7
  - Spec text: "Currently blocked on elemental_harmony having no live worlds … the tests exercise the hydration paths with synthetic YAML"
  - Implementation: All 50-22 tests build synthetic fixtures via `tmp_path`; `magic_active_elemental`/`magic_drained_elemental` were deliberately NOT authored
  - Rationale: This is the spec-mandated strategy, not a reduction — authoring blocked Wave 2 fixtures would violate the SM scope guard and ADR-014 (no fixtures against a non-existent world)
  - Severity: none (conformant — logged for traceability per "never assume simplification is acceptable")
  - Forward impact: a follow-on story authors Wave 2 fixtures once an elemental_harmony world exists

### Dev (implementation)
- **Whole-block `MagicState.model_validate(raw)` instead of step-wise config extraction**
  - Spec source: `.session/50-22-session.md` → ### Technical Approach, item 2 (`_hydrate_magic_state()`)
  - Spec text: "Extract required `config:` field; validate as WorldMagicConfig (pydantic ValidationError → FixtureValidationError wrap) … Construct `MagicState(**kwargs)`"
  - Implementation: `_hydrate_magic_state` validates the entire block in one call: `MagicState.model_validate(raw)`, delegating nested `config`→`WorldMagicConfig`, `ledger`→`LedgerBar`, etc. to pydantic. No manual field-by-field extraction.
  - Rationale: `MagicState` is `extra="forbid"` with a required `config`; `model_validate` of the raw block gives strictly stronger validation (the whole tree, including extra-field rejection at every level) with less code, and is exactly what TEA's tests assert (TEA explicitly directed `model_validate`, NOT `MagicState(**raw) or {}`). Tests are higher spec authority than the Technical Approach prose.
  - Severity: minor
  - Forward impact: none — behavior is a strict superset of the spec's intent; all 22 TEA tests + full suite green
- **Imports `MagicState`/`AbilityDefinition` from `sidequest.magic.state` / `sidequest.protocol.models`**
  - Spec source: `.session/50-22-session.md` → ### Schema References
  - Spec text: "`sidequest/genre/models/magic.py:WorldMagicConfig`"
  - Implementation: `from sidequest.magic.state import MagicState` (transitively pulls `WorldMagicConfig` from `sidequest.magic.models`) and `from sidequest.protocol.models import AbilityDefinition`
  - Rationale: `WorldMagicConfig` does not exist at the cited path; it lives at `sidequest/magic/models.py:287` (see TEA Delivery Finding). The chosen imports are the real module locations and introduce no import cycle (`game/session.py` already imports `MagicState`; `game/character.py` already imports `AbilityDefinition`).
  - Severity: minor
  - Forward impact: none — corrects a stale spec reference; Architect may want to fix the session/context Schema References text

### Reviewer (audit)

Every logged deviation stamped — nothing slips through undocumented.

- **TEA: Corrected the spec's invalid example `magic_state.config` shape** → ✓ ACCEPTED by Reviewer: independently verified `WorldMagicConfig` (`sidequest/magic/models.py:287`) is `extra="forbid"` with 11 required fields and no `confrontations_by_name`; the spec example genuinely cannot construct. Tests carry the correct shape and `test_magic_state_config_extra_field_rejected` actively asserts the stale shape invalid. Sound.
- **TEA: AC-7 satisfied by synthetic YAML, no canonical elemental fixtures authored** → ✓ ACCEPTED by Reviewer: matches the SM scope guard and ADR-014 (no fixtures against a non-existent world). Conformant, not a reduction.
- **Dev: Whole-block `MagicState.model_validate(raw)` instead of step-wise config extraction** → ✓ ACCEPTED by Reviewer: pattern-consistent with the merged `_hydrate_scenario_state` sibling's `ClueGraph.model_validate`; strictly stronger validation (full-tree `extra="forbid"`); Architect already endorsed (Option A). Agrees with author reasoning.
- **Dev: Imports `MagicState`/`AbilityDefinition` from real module paths** → ✓ ACCEPTED by Reviewer: cited `sidequest/genre/models/magic.py` does not exist; chosen imports are the real locations; no import cycle (verified `session.py`/`character.py` already import these); 6282-test suite green proves no cycle.

**Undocumented deviations found:** None. The verify-phase OTEL emitter realignment (bound→module import + added wiring test) is a code-quality correction, not a spec divergence, and is already documented in the TEA Simplify Report and the `### TEA (verify)` Delivery Finding — correctly NOT logged as a spec deviation.

### Architect (reconcile)

Definitive deviation manifest — every entry verified self-contained and accurate; the boss can audit 50-22 from this session file alone.

**Verification of existing entries (all 4 confirmed accurate, complete, 6-field):**

- *TEA — "Corrected the spec's invalid example `magic_state.config` shape"*: Spec source `.session/50-22-session.md → ### Technical Approach, item 4` **exists**; quoted spec text (`config:` with `world_slug: flickering_reach`, `ledger_bars: []`, `confrontations_by_name: {}`) **matches** the session Technical Approach verbatim. Implementation claim verified: `tests/game/test_scene_harness_hydrator.py::_MINIMAL_WORLD_MAGIC_CONFIG_YAML` carries an 11-field valid `WorldMagicConfig`; `test_magic_state_config_extra_field_rejected` actively asserts the stale `confrontations_by_name` shape invalid. `WorldMagicConfig` independently confirmed at `sidequest/magic/models.py:287`, `model_config={"extra":"forbid"}`, 11 required fields, no `confrontations_by_name`. All 6 fields present, forward impact accurate. **No correction needed.**
- *TEA — "AC-7 satisfied by synthetic YAML"*: Spec source AC-7 **exists**; spec text quoted accurately ("blocked on elemental_harmony having no live worlds … synthetic YAML"). Implementation verified: no `magic_active_elemental`/`magic_drained_elemental` fixtures authored; all tests use `tmp_path` synthetic YAML. Conformant-not-reduction classification correct. **No correction needed.**
- *Dev — "Whole-block `MagicState.model_validate(raw)` instead of step-wise config extraction"*: Spec source `### Technical Approach, item 2` **exists**; spec text ("Extract required `config:` field; validate as WorldMagicConfig … Construct `MagicState(**kwargs)`") quoted accurately. Implementation verified against `sidequest/game/scene_harness.py` `_hydrate_magic_state`: single `MagicState.model_validate(raw)` call, no manual field extraction. Pattern-consistent with the merged `_hydrate_scenario_state`'s `ClueGraph.model_validate`. Severity minor, forward impact "none — strict superset" accurate. **No correction needed.**
- *Dev — "Imports from real module paths"*: Spec source `### Schema References` **exists**; spec text (`sidequest/genre/models/magic.py:WorldMagicConfig`) quoted accurately. Implementation verified: `from sidequest.magic.state import MagicState`, `from sidequest.protocol.models import AbilityDefinition`. The cited `sidequest/genre/models/magic.py` path does not exist; real location `sidequest/magic/models.py:287`. No import cycle (6282-test suite green). **No correction needed.**

**Missed spec deviations:** None.

**Note for the auditor (self-contained, no external lookup required):** The verify-phase change to `sidequest/game/scene_harness.py` — replacing the bound import `from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish` with the module form `from sidequest.telemetry import watcher_hub as _hub` (call `_hub.publish_event(...)`), plus the new `test_scene_harness_emits_magic_state_hydrated_span` — is **deliberately NOT a spec deviation**. The written story spec (Technical Approach) is *silent* on OTEL; the OTEL emission requirement comes from a standing project rule (`sidequest-server/CLAUDE.md` OTEL observability principle: "Every backend fix that touches a subsystem MUST add OTEL watcher events"), surfaced as TEA RED-phase implementation guidance. Correcting *how* that rule-mandated event is wired (so it is consistent with the `scene_harness_router` sibling convention and capturable by the standard `_capture_events` harness) is a code-quality correction within rule-mandated scope, not a divergence from the written spec. It is fully recorded in the TEA Simplify Report and the `### TEA (verify)` Delivery Finding. Classification stands.

**AC deferral verification:** No-op — no ACs were deferred. AC-1 through AC-6 implemented and GREEN; AC-7 is explicitly out-of-scope-per-spec (synthetic-YAML strategy, blocked Wave 2 fixtures deferred to a future story when an elemental_harmony world exists), not a deferral of in-scope work. No AC accountability table was written by the ac-completion gate (none required — no deferrals). Reviewer verdict APPROVED with no AC gaps.

**Manifest status:** Complete. 4 deviations, all minor/none severity, all ACCEPTED by Reviewer, all verified accurate by Architect reconcile. Zero forward-impact risk to sibling stories (50-22 extends the shared hydrator seam additively; full suite confirms zero regression to 50-18..50-21).

## TEA Assessment

**Tests Required:** Yes
**Reason:** New behavior (two YAML→model hydration paths) on a tdd-tagged story — not a chore-bypass case.

**Test Files:**
- `sidequest-server/tests/game/test_scene_harness_hydrator.py` — appended a "Story 50-22 (RED)" section: 20 unit tests + helpers/constants covering AC-1 (abilities, singular + multi-PC), AC-2 (magic_state config/ledger/control_tier/known_spells), AC-3 (loud failure / no silent default), AC-4 (canonical + tri-block coexistence regression locks).
- `sidequest-server/tests/server/test_scene_harness.py` — 2 endpoint wiring tests: AC-6 endpoint→`SqliteStore` round-trip (`test_scene_post_persists_magic_state_and_abilities_round_trip`) and FixtureValidationError→HTTP 422 boundary (`test_dev_scene_route_rejects_malformed_magic_config_with_422`).

**Tests Written:** 22 tests (incl. 4 parametrized source cases) covering ACs 1–4 + 6. AC-5 is the meta "test coverage exists" criterion — satisfied by this suite. AC-7 is intentionally out of scope (synthetic YAML only, per spec + scope guard — see Design Deviations).
**Status:** RED confirmed — 113 collected, 21 failed (all 50-22 RED drivers), 92 passed (incl. 4 backward-compat locks), **0 collection/import errors, 0 pre-existing regressions**.

### Rule Coverage

| Rule (lang-review/python.md) | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | test_ability_missing_required_field_raises, test_ability_invalid_source_value_raises, test_ability_extra_field_rejected_by_pydantic, test_abilities_not_a_list_raises, test_magic_state_missing_config_raises, test_magic_state_malformed_config_raises, test_magic_state_block_not_a_mapping_raises, test_present_but_empty_magic_state_does_not_silently_default | failing (RED) |
| #11 input validation at boundaries | (same raises-suite — the fixture parser is the boundary; config/abilities pydantic-validated before use) | failing (RED) |
| #6 test quality | Phase-C self-audit of all 22 new tests | pass |
| #8 unsafe deserialization | No new surface — magic_state reuses the already-`yaml.safe_load`ed dict + pydantic `model_validate`; covered by existing `test_hydrator_uses_yaml_safe_load_not_yaml_load` | pass (existing) |
| #3 type annotations at boundaries | New `_hydrate_magic_state` is a private helper (rule #3 exempt); `hydrate_fixture` public signature unchanged | n/a (noted) |

**Rules checked:** 4 of 14 lang-review rules are applicable to a pure YAML-block hydration extension. N/A (documented): #2 mutable-defaults, #4 logging, #5 path-handling, #7 resource-leaks, #9 async, #10 import-hygiene, #12 dependency-hygiene, #13 fix-regressions (no fixes yet), #14 state-cleanup-ordering (no one-shot queue touched).
**Self-check:** 0 vacuous tests found — every test asserts specific values or `pytest.raises` on a meaningful boundary; no `assert True`, no bare-truthy on always-None.

### Implementation guidance for Dev (Major Winchester)

Mirror the established 50-20 `scenario_state` branch exactly:
- **abilities:** extend `_hydrate_character()` — read `data.get("abilities")`; if not None and not a list → raise `FixtureValidationError` (the `known_facts` non-list precedent); else build `[AbilityDefinition(**e) for e in list]` and pass `abilities=` to the `Character(...)` constructor. Pydantic `ValidationError` propagates and is wrapped by the existing caller `try/except ValidationError` blocks (both singular `character:` and `characters:` list paths).
- **magic_state:** add a `_hydrate_magic_state(raw, *, fixture_name)` helper guarded by `if "magic_state" in data and data.get("magic_state") is not None:` (the scenario_state guard idiom). Non-dict → `FixtureValidationError`. Build `MagicState.model_validate(raw)` (NOT `MagicState(**raw) or {}`); wrap `ValidationError` as `FixtureValidationError`. Project to `snapshot_kwargs["magic_state"]`.
- **Imports:** `from sidequest.magic.state import MagicState` (it transitively pulls `WorldMagicConfig` from `sidequest.magic.models`) — NOT `sidequest.genre.models.magic` (see Delivery Finding).
- **The AC-3 lie-detector:** `test_present_but_empty_magic_state_does_not_silently_default` (`magic_state: {}`) — do NOT treat an empty dict as "absent" and do NOT swallow the resulting `ValidationError`. ADR-014 Diamond / "No Silent Fallbacks".
- **OTEL:** per `sidequest-server/CLAUDE.md` OTEL principle, the magic-state hydration decision touches the magic subsystem — emit a watcher event (e.g. `magic.state_hydrated` with config.world_slug / ledger size) so the GM panel can verify the fixture staged real magic state, not improvised. The hydrator is dev-gated but the fix-touches-subsystem rule still applies.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for the GREEN phase.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/game/scene_harness.py` (+89 lines, one file) —
  - 3 imports added: `MagicState` (sidequest.magic.state), `AbilityDefinition` (sidequest.protocol.models), `publish_event as _watcher_publish` (sidequest.telemetry.watcher_hub).
  - `_hydrate_character()`: reads optional `abilities:` list; non-list shape → `FixtureValidationError`; per-entry `AbilityDefinition(**entry)` (pydantic catches missing/bad `source`, extra-field typos); passes `abilities=` to `Character(...)`. Mirrors the `known_facts` precedent.
  - `_hydrate_magic_state(raw, *, fixture_name)` helper: non-dict guard → `FixtureValidationError`; `MagicState.model_validate(raw)` with `ValidationError`→`FixtureValidationError` wrap; emits `magic.state_hydrated` OTEL watcher event (component=`magic`, severity=`info`) on success.
  - `hydrate_fixture()`: added the `magic_state` branch after `scenario_state`, using the same `in data and ... is not None` guard idiom (lets empty `{}` through so missing-config raises, never silent-absent).

**Approach:** Minimal, pattern-faithful. No new abstractions, no scope creep. The implementation is strictly what the 22 TEA tests demand; mirrors the 50-20 `scenario_state` / 50-19 `known_facts` branches the Reviewer already blessed.

**Tests:** GREEN.
- Target files: **113/113** passed (`tests/game/test_scene_harness_hydrator.py` 89, `tests/server/test_scene_harness.py` 24) — all 22 Story 50-22 tests pass, zero pre-existing regressions in those files.
- Full server suite: **6281 passed, 0 failed, 400 skipped** — no cross-suite regression from the new imports/behavior.
- `ruff check sidequest/game/scene_harness.py`: **pass**.

**Branch:** `feat/50-22-scene-harness-magic-abilities` (commit `411a577`, pushed to `origin`, tracks remote). Base `develop` (server gitflow per repos.yaml). No PR created (SM owns PR at finish).

**Self-review (judgment checks):**
- Wired: `scene_harness.hydrate_fixture` is the production hydrator behind the dev-gated `/dev/scene/{name}` route; AC-6 endpoint→`SqliteStore` round-trip test proves the new fields are reachable and persist through the real HTTP path.
- Patterns: identical structure/idioms to the existing `scenario_state`/`known_facts` branches.
- ACs: AC-1, AC-2, AC-3, AC-4, AC-6 fully met; AC-5 (coverage exists) satisfied; AC-7 out of scope per spec + SM scope guard.
- Error handling: loud `FixtureValidationError` on every malformed shape (non-list abilities, non-dict magic_state, missing/extra config fields, empty `{}`); no silent fallback (ADR-014/ADR-092).
- OTEL: `magic.state_hydrated` watcher event added per CLAUDE.md observability principle.
- No debug code; working tree clean (only `.claude/` untracked, intentionally not staged).

**Handoff:** To verify phase — TEA (Radar O'Reilly) for simplify + quality-pass.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None substantive (2 Dev deviations pre-logged; both spec-update candidates already routed via Delivery Finding)

**Structural gate (Step 1):** `gates/spec-check` → `status: ready`. AC coverage present in Dev Assessment, implementation marked complete, both `### TEA (test design)` and `### Dev (implementation)` deviation subsections well-formed (6-field).

**Substance analysis (Step 2) — per AC:**
- **AC-1 (abilities)** — Aligned. `_hydrate_character` non-list→`FixtureValidationError`; per-entry non-dict→`FixtureValidationError`; `AbilityDefinition(**entry)` pydantic errors (missing/bad `source`, `extra=forbid`) propagate and are wrapped on both the singular `character:` and multi-PC `characters:` caller paths; absent/empty→`[]`.
- **AC-2 (magic_state)** — Aligned. Guarded branch → `_hydrate_magic_state` → `MagicState.model_validate(raw)` delegates nested `config`→`WorldMagicConfig` (+ ledger/control_tier/spells) validation to pydantic. Architecturally consistent with the existing `_hydrate_scenario_state` precedent which uses `ClueGraph.model_validate` for nested validation — same philosophy, not a new pattern.
- **AC-3 (no silent default)** — Aligned. Empty `{}` intentionally passes the `is not None` guard so `model_validate({})` raises on missing `config`; no synthetic/empty fallback. Design intent documented inline; GREEN lie-detector test confirms.
- **AC-4 (integration)** — Aligned. Independent branch placed after `scenario_state`; `abilities` rides the shared `_hydrate_character` so both PC shapes benefit. Full server suite 6281 passed / 0 failed — zero regression.
- **AC-5 (coverage)** — Aligned. 22 TEA tests cover every enumerated case.
- **AC-6 (wiring)** — Aligned. Endpoint→`SqliteStore` round-trip test GREEN; hydrator wired behind the dev-gated `/dev/scene/{name}` route.
- **AC-7 (blocked)** — Aligned. No elemental fixtures authored (correct per SM scope guard + ADR-014); synthetic-YAML strategy per spec; deviation logged for traceability.

**Deviation review:**
- *Whole-block `MagicState.model_validate` vs step-wise extraction* (Dev, logged): Category=Different behavior, Type=Architectural, Severity=Minor. Recommendation **A — Update spec**: `model_validate` is the superior, pattern-consistent approach (matches `scenario_state`'s nested-model delegation); behavior is a strict superset. Already captured as a Dev deviation + Delivery Finding routing the stale Technical Approach text for source correction.
- *Corrected import paths* (Dev, logged): Category=Different behavior, Type=Cosmetic, Severity=Trivial. Recommendation **A — Update spec**: cited `sidequest/genre/models/magic.py` path does not exist; real path `sidequest/magic/models.py`. Already routed via TEA + Dev Delivery Findings for Schema References correction.

**OTEL check:** `magic.state_hydrated` (component=`magic`, severity=`info`) follows the established magic-subsystem dotted-event convention (parallels the live `magic.unrouted_cost` in `magic/state.py`); satisfies the CLAUDE.md observability principle for a subsystem-touching change. `publish_event` is a safe no-op without subscribers — no test/prod risk. Sound.

**Decision:** Proceed to review (next phase: verify — TEA simplify + quality-pass). No hand-back to Dev. The two logged deviations are Option-A spec-updates already routed to source via Delivery Findings; the Architect (reconcile) phase will finalize the deviation manifest.

**Handoff:** To verify phase — TEA (Radar O'Reilly).

## TEA Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`sidequest/game/scene_harness.py`, `tests/game/test_scene_harness_hydrator.py`, `tests/server/test_scene_harness.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | The 3 list-validation loops + 4 test-helper builders are intentional pattern-consistency with the 50-19/50-20 sibling branches, not harmful duplication; known_facts' fact_id scrub is load-bearing and rightly absent from abilities. |
| simplify-quality | 1 finding (high) | `magic.state_hydrated` emitted but no test asserts it — CLAUDE.md "Every Test Suite Needs a Wiring Test" + OTEL lie-detector gap. **Applied.** |
| simplify-efficiency | clean | Manual per-entry type guards give indexed error messages (intentional); pydantic delegation via `model_validate` is deliberate and consistent with `_hydrate_scenario_state`'s `ClueGraph.model_validate`. Not over-engineered. |

**Applied:** 1 high-confidence fix.
- **Root cause (deeper than the finding):** Dev's `magic.state_hydrated` used a *bound import* (`from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish`), which is (a) inconsistent with the established `scene_harness_router.py` convention (`from sidequest.telemetry import watcher_hub as _hub` + `_hub.publish_event(...)`), and (b) **uncapturable** by the project-standard `_capture_events` harness, which `monkeypatch.setattr(_hub, "publish_event", ...)` — a bound reference can't be intercepted by patching the module attribute (lang-review #6 "patch where used, not where defined", inverted). The OTEL event was therefore both untested *and* untestable with standard tooling.
- **Fix:** realigned `scene_harness.py` to the sibling convention (`import watcher_hub as _hub`; `_hub.publish_event(...)`) and added `test_scene_harness_emits_magic_state_hydrated_span` (mirrors `test_scene_harness_emits_hydrate_ok_span`) asserting the event fires with real `world_slug`/`genre_slug`/`control_tier_actors` values and `component=magic`. Committed `36e6c21`, pushed.

**Flagged for Review:** 0 medium-confidence findings.
**Noted:** 0 low-confidence observations.
**Reverted:** 0.

**Overall:** simplify: applied 1 fix

### Regression Detection

`testing-runner` full re-run after the applied fix:
- Target files: **114/114** passed (`test_scene_harness_emits_magic_state_hydrated_span` PASSED; all prior 50-22 + pre-existing scene-harness tests still green).
- Full server suite: **6282 passed, 0 failed, 400 skipped** (baseline 6281 at `411a577` + the 1 new OTEL test). Zero regressions from the watcher-import realignment.
- `ruff check` on both changed files: **pass**.

**Quality Checks:** All passing.

### Delivery Findings

(see `### TEA (verify)` under ## Delivery Findings)

**Handoff:** To Reviewer (Colonel Sherman Potter) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 code smells; 1 mechanical note (abilities error-message granularity) | confirmed 0, dismissed 0, deferred 1 (note → LOW obs) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via `workflow.reviewer_subagents.edge_hunter=false` — domain assessed by Reviewer directly |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings; verify-phase simplify (reuse/quality/efficiency) already ran — see TEA Simplify Report |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — lang-review/python.md enumerated by Reviewer directly (see Rule Compliance) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` and pre-filled Skipped per the completion-gate rule — their domains assessed directly by the Reviewer below)
**Total findings:** 0 confirmed blocking, 0 dismissed, 3 deferred as LOW/non-blocking observations

## Reviewer Assessment

**Verdict:** APPROVED

Forty years of looking at other people's incisions, Doctor — this one is clean, sutured the way the last three were (50-19 `known_facts`, 50-20 `scenario_state`), and the field hospital already caught its own one bleeder in verify. I read every added line myself; I did not take the assessments on faith.

**Data flow traced:** fixture YAML → `/dev/scene/{name}` (dev-gated, `DEV_SCENES=1`) → `scene_harness_router` → `hydrate_fixture` → (`_hydrate_character` abilities branch | `_hydrate_magic_state`) → `GameSnapshot` → `SqliteStore.save` → `.load`. Safe because every untrusted shape is pydantic-validated before construction and every failure raises `FixtureValidationError` (HTTP 422), never a silent default. End-to-end persistence proven by `test_scene_post_persists_magic_state_and_abilities_round_trip` (GREEN).

**Pattern observed:** the two new branches mirror the blessed `_hydrate_scenario_state`/`known_facts` idioms exactly — guard-then-delegate-to-pydantic — at `scene_harness.py:233-248` (magic_state branch) and `:331-352` (abilities loop). Consistency confirmed against the sibling code, not assumed.

### Rule Compliance (lang-review/python.md, enumerated against the diff)

| Rule | Applies to | Verdict |
|------|-----------|---------|
| #1 silent exception swallowing | `_hydrate_magic_state` `except ValidationError → raise FixtureValidationError ... from exc`; abilities/magic_state guards `raise` | **Compliant** — no bare except, no swallow, exception chained with `from` |
| #2 mutable default args | `abilities: list[AbilityDefinition] = []` is a local, not a param default; `_hydrate_magic_state(raw, *, fixture_name)` no mutable defaults | **Compliant** |
| #3 type annotations at boundaries | `_hydrate_magic_state(raw: Any, *, fixture_name: str) -> MagicState`; `hydrate_fixture` public sig unchanged | **Compliant** (private helper annotated anyway) |
| #4 logging coverage/correctness | validation failures `raise` (→422), not log-and-continue; no misleveled logging introduced | **Compliant** |
| #5 path handling | no new path handling in the diff | **N/A** |
| #6 test quality | new `test_scene_harness_emits_magic_state_hydrated_span` asserts specific field values + component; 22 hydrator tests assert concrete values / `pytest.raises` on real boundaries | **Compliant** — no vacuous assertions, monkeypatch targets the module attr (the realigned `_hub.publish_event` is now the correct patch target) |
| #8 unsafe deserialization | `MagicState.model_validate(raw)` / `AbilityDefinition(**entry)` on the already-`yaml.safe_load`ed dict; no eval/pickle/yaml.load | **Compliant** |
| #11 input validation at boundaries | fixture parser is the boundary; abilities + magic_state pydantic-validated before use; `extra="forbid"` rejects unknown keys at every level | **Compliant** |
| #13 fix-introduced regressions | verify-phase import realignment re-scanned: no broad except, no bad annotation; 6282 suite green | **Compliant** |
| #14 state-cleanup ordering | no one-shot queue/buffer touched | **N/A** |

Enumeration is exhaustive over the diff: 2 new helpers/branches + 3 new imports + 1 new test checked against every applicable numbered rule. No violations.

### Observations (tagged by domain — disabled subagents assessed directly)

1. `[VERIFIED]` **Error handling fails loud, no silent fallback** — evidence: `scene_harness.py` `_hydrate_magic_state` raises `FixtureValidationError` on non-dict and wraps `ValidationError`; empty `{}` deliberately reaches `model_validate` and raises on missing `config`. Complies with CLAUDE.md "No Silent Fallbacks" + ADR-014 (magic state is Diamond) + ADR-092. Confirmed by GREEN `test_present_but_empty_magic_state_does_not_silently_default`.
2. `[SILENT]` (subagent disabled — Reviewer assessed) `[VERIFIED]` No swallowed errors: every `except` re-raises with `from exc`; no `except: pass`, no `contextlib.suppress`. Evidence: the only new `except` is `except ValidationError as exc: raise FixtureValidationError(...) from exc`.
3. `[EDGE]` (subagent disabled — Reviewer assessed) **[LOW]** A literal-null `magic_state:` (YAML key, no value) is treated as absent (`data.get("magic_state") is not None` is False) → `magic_state=None`. This is *identical* to the `scenario_state` sibling guard (`scene_harness.py:223`) — a deliberate, consistent whole-hydrator convention, not a 50-22 regression. The AC-3 case the spec actually targets (`magic_state: {}` — mapping, no config) **does** raise (verified GREEN). Non-blocking.
4. `[TEST]` (subagent disabled — Reviewer assessed) `[VERIFIED]` Test quality sound: 8.7:1 test/impl ratio; the OTEL wiring test asserts `world_slug`/`genre_slug`/`control_tier_actors`/`component` concrete values (not bare truthy); negative tests use `pytest.raises` on the real `FixtureValidationError` boundary. TEA self-audited + simplify-reuse/efficiency confirmed no vacuity.
5. `[DOC]` (subagent disabled — Reviewer assessed) `[VERIFIED]` Comments accurate and load-bearing: the `is not None` guard comment correctly explains the empty-`{}`-must-raise intent; the `_hub` module-import comment documents *why* (test-harness capturability). No stale/misleading docs introduced.
6. `[TYPE]` (subagent disabled — Reviewer assessed) `[VERIFIED]` Type design sound: hydrator delegates to pydantic models (`MagicState`/`AbilityDefinition`, both `extra="forbid"`) — no stringly-typed surface, no unsafe cast. `source` is the `AbilitySource` StrEnum, validated by pydantic.
7. `[SEC]` (subagent disabled — Reviewer assessed) `[VERIFIED]` No new attack surface: route is dev-gated (`DEV_SCENES=1`, fail-closed, covered by existing tests); input is `yaml.safe_load`ed upstream; no injection/secret/PII path. The OTEL event logs only slugs + counts (no sensitive data, lang-review #4).
8. `[SIMPLE]` Verify-phase simplify already ran (reuse/efficiency clean; quality found+fixed the OTEL gap). No residual over-engineering: `_hydrate_magic_state` is 47 lines incl. docstring; pydantic delegation avoids hand-rolled extraction. Confirmed.
9. `[RULE]` (rule-checker disabled — Reviewer enumerated) See Rule Compliance table above — zero violations across 9 applicable lang-review rules.
10. **[LOW]** `[from reviewer-preflight]` Abilities pydantic `ValidationError` propagates bare from `_hydrate_character`; the outer `hydrate_fixture` wraps at `characters[N] validation failed` granularity rather than `characters[N].abilities[M] ...`. *Identical to the known_facts sibling* — a consistency choice, not a defect. Deferred, non-blocking; a future ergonomics pass could add the `.abilities[M]` index across both blocks together.
11. **[LOW/informational]** `AbilityDefinition` (`name`/`genre_description`/`mechanical_effect` are plain `str`, not `NonBlankString`) accepts blank strings — so a fixture with `name: ""` hydrates silently. This is the *model's* existing contract, not 50-22's; tightening it is explicitly out of scope (SM scope guard: "Do NOT change the MagicState API"; same logic applies to AbilityDefinition). Deferred to a model-hardening story if ever desired.

### Devil's Advocate

Let me try to break this. A malicious or confused fixture author is the only threat model here — the route is dev-gated and the input is YAML the author controls. What can they do? Feed `magic_state:` a list → caught, `FixtureValidationError`, 422 (verified). Feed a config missing `narrator_register` → pydantic rejects, wrapped, 422 (verified). Feed `confrontations_by_name: {}` (the stale spec example) → `WorldMagicConfig` `extra="forbid"` rejects it (verified by `test_magic_state_config_extra_field_rejected`). Feed `abilities: {}` (mapping) → non-list guard, 422. Feed an ability with `source: Sorcery` → `AbilitySource` StrEnum rejects, 422. Feed a deeply nested bomb? `yaml.safe_load` upstream already neutralizes `!!python/object`; pydantic depth is bounded by the model tree. So the loud-failure surface is genuinely closed.

Where could it *silently* misbehave? The one gray zone is the literal-null `magic_state:` → treated as absent. A careless author who writes `magic_state:` then forgets the body gets `magic_state=None` with no error. Is that a silent fallback (ADR-014 violation)? I argue no: it is *byte-identical* behavior to the `scenario_state` sibling that the Reviewer (me) already blessed in 50-20, it is a whole-hydrator convention, and a YAML key with no value is semantically "I declared nothing here" — distinct from `{}` ("I declared an empty mapping") which *does* raise. Holding 50-22 to a stricter standard than its merged sibling would be inconsistent, and inconsistency is its own defect. If this is wrong, it is wrong across the entire hydrator and belongs in a separate cross-cutting story, not a 50-22 block.

Second angle: the OTEL event fires *after* `model_validate` succeeds but *before* `return`. If `_hub.publish_event` raised, hydration would fail. But it is documented no-op-safe ("drops silently … no subscribers"), and every existing emitter in `scene_harness_router` takes the same risk — the risk profile is unchanged, not newly introduced. Third angle: persistence. Does `MagicState` round-trip through `SqliteStore`? `pending_status_promotions` is `exclude=True` and re-inits empty on load — by design per the model docstring — and `test_scene_post_persists_magic_state_and_abilities_round_trip` proves config + control_tier survive. No data-loss path. I cannot manufacture a Critical or High here. The work is sound.

### Rule Compliance summary

9 applicable lang-review rules enumerated exhaustively over the diff (table above): **0 violations**. SOUL.md/CLAUDE.md: "No Silent Fallbacks" ✓, "No Stubbing" ✓ (real implementation, no shells), "Verify Wiring Not Just Existence" ✓ (endpoint→SqliteStore + OTEL-capture tests), "Every Test Suite Needs a Wiring Test" ✓ (two wiring tests), OTEL observability principle ✓ (`magic.state_hydrated` emitted *and* asserted).

**Error handling:** loud `FixtureValidationError`→HTTP 422 on every malformed shape; `scene_harness.py` `_hydrate_magic_state` + abilities guards. No null-deref risk (`magic_state.config` guaranteed by required-field validation before the OTEL access).

**Handoff:** To SM (Hawkeye Pierce) for finish-story.