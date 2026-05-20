---
story_id: "24-5"
jira_key: null
epic: "24"
workflow: "tdd"
---
# Story 24-5: Python weather generator in sidequest-server

## Story Details
- **ID:** 24-5
- **Epic:** 24 (Procedural World-Grounding Systems)
- **Workflow:** tdd
- **Stack Parent:** none

## Context
Implement Python weather generator in sidequest-server that reads climate YAML (authored in 24-2 for tea_and_murder/glenross) + RNG seed and produces typed weather state. Follow the namegen module + CLI pattern in:
- `sidequest-server/sidequest/cli/namegen.py` (CLI entry)
- `sidequest-server/sidequest/corpus/` (module layout reference)

Architectural pointers:
- Backend is Python post-ADR-082 (no Rust)
- ADR-059 Monster Manual pattern (read both drift + ADR-087 successor pointer)
- Existing seam: `sidequest-server/sidequest/genre/models/scenario.py:132` — `SceneSetting.weather` is currently free-form str; the new generator populates it from typed state
- Packs remain monolithic per retired-ADR-072: weather YAML lives in `sidequest-content/genre_packs/<pack>/` alongside existing top-level pack files
- Climate YAML location: `sidequest-content/genre_packs/tea_and_murder/` (24-2 shipped)

Critical workflow rules:
- No silent fallbacks, no stubbing, no half-wired features
- Every test suite needs a wiring test (verify generator is called from production code path, not just unit-tested in isolation)
- This is server-only repo work; orchestrator commit is for sprint YAML only
- Branch sidequest-server off develop (gitflow per repos.yaml)

## Sm Assessment

**Selected from p0 surface.** Epic 24 (Procedural World-Grounding) has two p0s remaining after 24-1/2/3 shipped: 24-4 (calendar content, 2pt trivial) and 24-5 (this — weather generator, 3pt tdd, server). Chose 24-5 because:
- Fresh /clear has full context budget; spend it on the meatier TDD module + CLI work.
- 24-2 already shipped climate YAML for `tea_and_murder/glenross` — the generator has its input ready.
- 24-4 is a clean content warm-down for after this lands; nothing in 24-5 blocks on it.
- Downstream (24-6 prompt injection, 24-7 OTEL, 24-8 playtest) all depend on the typed `WeatherState` produced here, so 24-5 unblocks the rest of the epic.

**Pattern reference.** Follow the existing `namegen` shape — `sidequest-server/sidequest/cli/namegen.py` for CLI, `sidequest-server/sidequest/corpus/` for module layout. ADR-059 (Monster Manual) is the architectural template; read its DRIFT entry and ADR-087 successor pointer before designing.

**Seam to populate.** `genre/models/scenario.py:132` — `SceneSetting.weather: str` is the field the generator's output ultimately fills. Don't ship a generator without an integration test that proves it's wired into the path that populates that field (or, if the wiring lives in 24-6, document the seam clearly so 24-6 doesn't drift).

**No-Jira project.** Skipped `pf jira claim` per `feedback_playtest_no_jira`. Sprint YAML is the source of truth.

**Branch state.** `sidequest-server` is on `feat/24-5-weather-generator` off develop (gitflow). Orchestrator stays on `main`; only sprint YAML changes commit there.

**Risk flags for TEA/Dev:**
- Don't unit-test the generator in isolation and call it done — the wiring test is mandatory. If the generator is callable from no production path yet, write the failing wiring test that *would* be green once 24-6 hooks it up, and leave a clearly-named xfail with a stated removal condition. Better: wire it now into whatever calls `SceneSetting.weather` and prove the typed value flows through.
- No silent fallbacks on missing climate YAML — fail loudly per project doctrine. If climate.yaml is absent, raise; don't synthesize a default.
- Don't stub or leave skeleton subsystems (precipitation/wind/temperature etc.) — implement the minimum the typed state model needs, no half-built fields.
- RNG seeding must be deterministic and exposed via CLI for reproducibility.

**Handoff target.** TEA / Radar O'Reilly for RED phase — write failing tests against the acceptance criteria captured in `sprint/context/24-5-story-context.md`.

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD workflow on a new module + CLI with seven explicit ACs and SOUL principles (no silent fallbacks, no stubbing, wiring required) that need enforcement.

**Test Files:**
- `sidequest-server/tests/game/test_weather_generator.py` — 30 tests covering AC1–AC7 + Python lang-rule checklist + CLI wiring against the real `tea_and_murder/weather.yaml`.

**Tests Written:** 30 tests covering 7 ACs
**Status:** RED — `ModuleNotFoundError: No module named 'sidequest.game.weather'` blocks all 30 tests at collection. No accidental passes, no test-code typos.

### Test Coverage by AC

| AC | What it requires | Tests |
|----|------------------|-------|
| AC1 (WeatherState model) | typed pydantic model | `test_weather_state_round_trip_serialization`, `test_weather_state_rejects_extra_fields`, `test_weather_state_requires_seed_field` |
| AC2 (WeatherGenerator) | deterministic generator | `test_generator_determinism_same_seed_same_output`, `test_generator_different_seeds_eventually_diverge`, `test_generator_temperature_within_season_range`, `test_generator_condition_from_palette`, `test_generator_weights_respected_in_aggregate`, `test_generator_seed_round_trips_into_weather_state`, `test_generator_records_zone_and_season` |
| AC3 (Climate YAML schema validation) | pydantic models for the YAML | `test_climate_rules_loads_real_tea_and_murder_yaml`, `test_climate_rules_rejects_empty_climate_zones`, `test_climate_rules_rejects_mismatched_weights_and_conditions`, `test_climate_rules_rejects_unknown_top_level_field`, `test_climate_rules_rejects_empty_seasons`, `test_climate_rules_rejects_temp_range_with_three_values` |
| AC4 (CLI) | `python -m sidequest.cli.weathergen` entry point | `test_cli_wiring_real_pack_produces_valid_weather_state`, `test_cli_determinism_across_subprocess_invocations`, `test_weathergen_cli_module_is_importable` |
| AC5 (Wiring) | non-test consumer exercises the generator end-to-end | `test_cli_wiring_real_pack_produces_valid_weather_state` (CLI subprocess against real `tea_and_murder/weather.yaml`), `test_weathergen_cli_module_is_importable` (production import path). Narrator-dispatch wiring deferred to 24-6 — see Design Deviations. |
| AC6 (No silent fallbacks) | fail loud on missing/invalid inputs | `test_generator_raises_on_missing_yaml_path`, `test_generator_raises_on_unknown_zone`, `test_generator_raises_on_unknown_season`, `test_cli_unknown_zone_exits_nonzero_with_named_zone`, `test_cli_unknown_genre_exits_nonzero` |
| AC7 (No stubbing) | no half-implemented fields | Enforced via `extra='forbid'` on WeatherState (`test_weather_state_rejects_extra_fields` ensures unauthored fields can't sneak in) |

### Rule Coverage (Python lang-review checklist)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 Silent exception swallowing | `test_generator_does_not_swallow_yaml_parse_errors` | failing (RED) |
| #5 Path handling (encoding= on open) | `test_generator_reads_yaml_with_explicit_encoding` | failing (RED) |
| #6 Test quality (vacuous assertions) | self-check below | n/a (meta-rule) |
| #7 Resource leaks | covered transitively (Pydantic file-load patterns use `with` via the loader pattern; reviewer will verify in green) | deferred to Dev |
| #8 Unsafe deserialization | `test_generator_uses_yaml_safe_load_not_full_load` | failing (RED) |
| #11 Input validation at CLI boundary | `test_cli_unknown_zone_exits_nonzero_with_named_zone`, `test_cli_unknown_genre_exits_nonzero` | failing (RED) |

**Rules NOT applicable to this story:** #2 (no mutable defaults at risk in a pure-functional generator), #3 (covered by pyright in CI), #4 (no new logging surface — OTEL is 24-7), #9 (no async code), #10 (no star imports planned), #12 (no new dependencies), #13 (meta — re-applied after Dev fixes), #14 (no queue/buffer one-shot pattern).

**Rules checked:** 6 of 6 applicable lang-review rules have failing-test coverage. Reviewer should still execute the checklist at gate time — these tests catch the known classes but the checklist is broader.

**Self-check:** 0 vacuous tests detected. Every test has at least one assertion checking a specific value, not just truthiness. `assert result.returncode != 0` in the CLI failure tests is paired with a stdout/stderr content assertion to confirm the error is *named*, not just nonzero.

### Wiring Discipline

CLAUDE.md mandate: "Every set of tests must include at least one integration test that verifies the component is wired into the system — imported, called, and reachable from production code paths."

Satisfied by **two complementary tests**:
1. `test_cli_wiring_real_pack_produces_valid_weather_state` — invokes the real CLI binary against the real authored `tea_and_murder/weather.yaml` and validates the JSON output round-trips through `WeatherState`. This is end-to-end wiring through a real production consumer (the CLI is invoked by humans and by the narrator agent's tool-call path in the namegen/encountergen pattern).
2. `test_weathergen_cli_module_is_importable` — asserts a non-test consumer (`sidequest.cli.weathergen.weathergen.main`) exists. Without this the module is dead code.

Narrator-dispatch wiring is **not** in 24-5's scope — see Design Deviation #3 for rationale and the finding flagged for 24-6.

### Handoff

To Dev (Major Charles Emerson Winchester III) for GREEN phase. Files to create:
- `sidequest-server/sidequest/game/weather.py` — `WeatherState`, `ClimateRulesFile`, `ClimateZone`, `SeasonPalette`, `SpecialEvent`, `WeatherGenerator`
- `sidequest-server/sidequest/cli/weathergen/__init__.py`
- `sidequest-server/sidequest/cli/weathergen/__main__.py` — `sys.exit(main())`
- `sidequest-server/sidequest/cli/weathergen/weathergen.py` — argparse + `main()` returning int

Climate YAML lives at `sidequest-content/genre_packs/<pack>/weather.yaml` (pack-level, per the authored 24-2 deliverable). Real-data test uses the `content_dir` session fixture from `tests/conftest.py:23`.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — 30 / 30 tests passing on the story file, 6931 / 6931 passing on the full server suite, ruff clean, pyright 0 errors.

### Files Created

- `sidequest-server/sidequest/game/weather.py` (≈190 LOC) — runtime module:
  - `SpecialEvent`, `SeasonPalette`, `ClimateZone`, `ClimateRulesFile` — pydantic v2 models matching `docs/schemas/world-grounding/weather.schema.json`. `extra='forbid'` on every model. `SeasonPalette` carries a `@model_validator(mode='after')` that enforces `len(weights) == len(conditions)` and `weights >= 0`. `climate_zones` and `seasons` use `Field(min_length=1)` per the JSON Schema's `minProperties: 1`.
  - `WeatherState` — runtime DTO with the 8 fields TEA's deviation log realigned to: `zone, season, condition, temperature_c, precipitation, special_event, effects, seed`. `extra='forbid'` so the narrator can't sneak unauthored fields back in.
  - `WeatherGenerator` — constructor loads YAML with `read_text(encoding='utf-8')` (rule #5) and `yaml.safe_load` (rule #8), validates through `ClimateRulesFile.model_validate(raw)`. Generation algorithm: (1) roll eligible special events in declaration order — out-of-season events skip without consuming RNG state, keeping condition draws stable across seasons; (2) sample condition from weighted palette; (3) uniform temperature over `temp_range`; (4) Bernoulli precipitation vs `precipitation_chance` (treats missing as 0.0 — schema-permitted "infer from condition weights", minimal interpretation, no silent climate invention).

- `sidequest-server/sidequest/cli/weathergen/__init__.py` — package docstring
- `sidequest-server/sidequest/cli/weathergen/__main__.py` — `sys.exit(main())`
- `sidequest-server/sidequest/cli/weathergen/weathergen.py` — argparse + main():
  - Required: `--genre`, `--zone`, `--season`, `--seed`
  - Reads `SIDEQUEST_CONTENT_PATH` env var or `--genre-packs-path`
  - JSON to stdout (sorted, indented); errors to stderr
  - Exit codes: 0 success, 1 generic load failure, 2 named input error (no weather.yaml, unknown zone, unknown season). Unknown-zone error reuses the generator's `KeyError` message (which names the offending zone) — satisfies AC6 + lang-rule #11 (input validation at CLI boundary).

### How Each AC Passes

- **AC1 (WeatherState model):** Pydantic v2 model with `extra='forbid'` and 8 required fields. Round-trip + extra-rejection + required-seed tests green.
- **AC2 (WeatherGenerator):** `random.Random(seed)` per call; same arguments → same output. Determinism, divergence, palette membership, temperature range, weight distribution all asserted.
- **AC3 (Schema validation):** Real `tea_and_murder/weather.yaml` loads cleanly; mismatched weights/conditions, empty `climate_zones`, empty `seasons`, three-value `temp_range`, and unknown top-level fields all rejected with `ValidationError`.
- **AC4 (CLI):** `python -m sidequest.cli.weathergen --genre tea_and_murder --zone glen_floor --season winter --seed 12345` succeeds end-to-end, emits valid `WeatherState` JSON.
- **AC5 (Wiring):** CLI subprocess test runs against real content and parses the JSON back through `WeatherState.model_validate`. Production consumer is the CLI itself — narrator-dispatch wiring is 24-6's deliverable per the logged deviation.
- **AC6 (No silent fallbacks):** Missing file → `FileNotFoundError`. Unknown zone/season → `KeyError` with available options listed. Bad YAML → surfaces `yaml.YAMLError` / `ValidationError` — never caught-and-defaulted.
- **AC7 (No stubbing):** No empty methods, no half-implemented narrative-flourish field, no skeleton subsystems. `narrative_flourish` is absent from `WeatherState` entirely; the `extra='forbid'` test prevents reintroducing it as a stub.

### Lang-Rule Coverage (re-verified GREEN)

| Rule | Implementation choice | Verification |
|------|----------------------|--------------|
| #1 No silent exception swallowing | Generator catches nothing; CLI catches `FileNotFoundError` + `KeyError` and re-emits to stderr with exit code | `test_generator_does_not_swallow_yaml_parse_errors`, `test_cli_unknown_zone_exits_nonzero_with_named_zone` |
| #5 Path handling — explicit encoding | `Path.read_text(encoding="utf-8")` in `WeatherGenerator.__init__` | `test_generator_reads_yaml_with_explicit_encoding` |
| #7 Resource leaks | `read_text()` self-closes the file handle; no `open()` outside a context manager anywhere in the new code | static review |
| #8 Unsafe deserialization | `yaml.safe_load` only | `test_generator_uses_yaml_safe_load_not_full_load` |
| #11 Input validation at CLI boundary | argparse `required=True` + explicit `--seed type=int` + downstream `KeyError` surface with exit 2 | `test_cli_unknown_zone_exits_nonzero_with_named_zone`, `test_cli_unknown_genre_exits_nonzero` |

### Quality Gates

| Gate | Result |
|------|--------|
| `uv run pytest tests/game/test_weather_generator.py` | 30 passed, 0 failed, 1.60s |
| `uv run pytest` (full server suite) | 6931 passed, 396 skipped, 0 failed, 118.91s |
| `uv run ruff check sidequest/game/weather.py sidequest/cli/weathergen/ tests/game/test_weather_generator.py` | All checks passed |
| `uv run ruff format` | 2 files reformatted (auto-fixed), 3 unchanged |
| `uv run pyright sidequest/game/weather.py sidequest/cli/weathergen/` | 0 errors, 0 warnings |

### Wiring Discipline

Two real non-test consumers exercise `WeatherGenerator`:
1. `sidequest.cli.weathergen.weathergen.main` — invoked by `python -m sidequest.cli.weathergen`. Test `test_cli_wiring_real_pack_produces_valid_weather_state` runs it as a subprocess against the authored `sidequest-content/genre_packs/tea_and_murder/weather.yaml` and validates the JSON output round-trips through `WeatherState`.
2. `sidequest.cli.weathergen.__main__` — module entry point for `-m` invocation. Imports `main` from the implementation module.

Narrator-dispatch wiring (prompt-zone injection in `agents/orchestrator.py`) remains 24-6's deliverable per TEA's deviation log; the present finding `Gap: SceneSetting.weather seam does not exist` is carried forward in the Delivery Findings.

### Handoff

To TEA / Radar O'Reilly for VERIFY phase (simplify + quality-pass). Files changed in this branch:
- `sidequest-server/sidequest/game/weather.py` (new)
- `sidequest-server/sidequest/cli/weathergen/__init__.py` (new)
- `sidequest-server/sidequest/cli/weathergen/__main__.py` (new)
- `sidequest-server/sidequest/cli/weathergen/weathergen.py` (new)
- `sidequest-server/tests/game/test_weather_generator.py` (new — formatted)

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — all material drift is already logged in the TEA deviation manifest. One trivial spec-text inconsistency surfaced that wasn't deviation-logged; recommend Option A (update spec).
**Mismatches Found:** 4 (3 already deviation-logged by TEA, 1 trivial new)
**Gate:** spec-check passed — structural validation clean (AC coverage table present, implementation marked complete, both TEA and Dev deviation subsections properly formatted).

### Substance Check vs Story Context ACs

I cross-referenced `sprint/context/24-5-story-context.md` ACs against the committed code (`sidequest-server/sidequest/game/weather.py`, `sidequest-server/sidequest/cli/weathergen/*.py`) and the Dev Assessment.

| AC | Spec → Code Alignment | Verdict |
|----|----------------------|---------|
| AC1 (WeatherState model) | Spec proposed `(condition, temperature: str, wind, special_event, intensity: float, narrative_flourish: str)`; code ships `(zone, season, condition, temperature_c: float, precipitation: bool, special_event, effects, seed)`. | **Drift — deviation-logged** |
| AC2 (WeatherGenerator) | `WeatherGenerator(yaml_path)` + `.generate(zone, season, seed) -> WeatherState`; deterministic, pure-functional, RNG-seeded. | **Aligned** |
| AC3 (Climate YAML schema validation) | Spec proposed `ClimateRules(zones, season_list)` + `ClimateZone(conditions, seasonal_modifiers, special_events: List[str])` in `genre/models/scenario.py`; code ships `ClimateRulesFile(climate_zones)` + `ClimateZone(seasons, special_events: List[SpecialEvent])` + `SeasonPalette` + `SpecialEvent` in `game/weather.py`. | **Drift — deviation-logged** |
| AC4 (CLI) | Spec example `--pack tea_and_murder`; code ships `--genre tea_and_murder` (matches the explicitly-spec'd "follow namegen pattern" — namegen uses `--genre`). | **Minor inconsistency — new finding** |
| AC5 (Wiring) | Spec required dispatch-pipeline test populating `SceneSetting.weather`; code tests via CLI subprocess against real pack (no SceneSetting class exists; dispatch-wiring is 24-6's deliverable). | **Drift — deviation-logged** |
| AC6 (No silent fallbacks) | Missing YAML → `FileNotFoundError`; unknown zone/season → `KeyError` listing available; bad YAML → surfaces parse error. | **Aligned** |
| AC7 (No stubbing) | `narrative_flourish` absent entirely (didn't ship a half-implementation); `extra='forbid'` blocks re-introduction. | **Aligned** |

### Mismatch Resolution Recommendations

1. **WeatherState field set** (Behavioral, Moderate)
   - Spec: AC1 categorical-ladder shape with `narrative_flourish`.
   - Code: Schema-realigned shape (8 fields matching `weather.schema.json` + audit `seed`).
   - **Recommendation: A — Update spec.** Implementation correctly aligned with the authored YAML schema (sibling-story 24-1 + 24-2 deliverables that are now reality). Story-context AC1 was drafted before the schema was final and contradicts higher-authority sibling-story output. TEA's deviation log already captures this with full rationale.

2. **Climate-models placement + schema shape** (Architectural, Moderate)
   - Spec: AC3 + Touch Points table placed `ClimateRules` in `genre/models/scenario.py` with a `season_list` field and `seasonal_modifiers` dict.
   - Code: Climate models co-locate with the generator in `game/weather.py` and follow the authored YAML's `climate_zones / seasons / temp_range+conditions+weights / special_events` shape.
   - **Recommendation: A — Update spec.** Co-location matches the namegen pattern (story-context explicitly invokes it as the reference) and keeps the scenario authoring concern separate from runtime grounding. The proposed `season_list` doesn't exist in the schema and would have required silent invention. TEA's deviation log captures this.

3. **CLI argument name `--pack` vs `--genre`** (Cosmetic, Trivial — NEW)
   - Spec: AC4 example uses `--pack tea_and_murder`.
   - Code: CLI argument is `--genre tea_and_murder`.
   - **Recommendation: A — Update spec.** Story context simultaneously specifies "follow namegen pattern" — namegen's argument is `--genre`. Dev followed the higher-authority "follow pattern" instruction; the bash example was a drafting inconsistency. Not deviation-worthy on its own but worth a note for the eventual story-context refresh. No code change required.

4. **AC5 wiring scope: dispatch pipeline → CLI subprocess** (Behavioral, Moderate)
   - Spec: Trigger weather generation in the game dispatch pipeline; assert `SceneSetting.weather` populated.
   - Code: CLI subprocess test invokes `python -m sidequest.cli.weathergen` against real `tea_and_murder/weather.yaml`; asserts `WeatherState.model_validate(json.loads(stdout))`.
   - **Recommendation: A — Update spec for 24-5 + propagate to 24-6.** (a) `SceneSetting` class does not exist in the codebase — the only `weather: str` field is `AtmosphereVariant.weather` (authored scenario data, not runtime state). (b) Narrator-dispatch wiring is the explicit deliverable of story 24-6 per the Epic 24 plan. (c) Per ADR-059's Monster Manual pattern, CLI is a valid first-tier production consumer; the narrator-side wiring is the second-tier consumer that comes in the next story. (d) `test_weathergen_cli_module_is_importable` asserts a non-test consumer exists, satisfying the CLAUDE.md "every test suite needs a wiring test" rule for this story's surface. TEA's deviation log captures this; the matching upstream finding (`Gap: SceneSetting seam does not exist`) is appropriately tagged blocking-for-24-6.

### Cross-Cutting Observations

- **TEA's deviation rigor is exemplary.** All three logged deviations include the full 6-field format (Spec source, Spec text quoted, Implementation, Rationale, Severity, Forward impact). Dev's clean handoff confirms the deviations weren't aspirational — every drift call held up under implementation. No new architectural drift introduced.

- **Lang-rule coverage is genuine, not performative.** I checked the diff: `yaml.safe_load` (line 131), `read_text(encoding="utf-8")` (line 130), `extra='forbid'` on all 5 pydantic models (lines 35/47/70/79/102), CLI uses argparse `required=True` + `type=int`. The Python checklist tests aren't just present — the implementation choices that satisfy them are visible in the code.

- **No silent fallbacks confirmed.** `precipitation_chance` falls back to 0.0 when omitted, which Dev correctly flagged as schema-permitted ("may be inferred from condition weights") rather than silent. The fallback is documented inline in the generator. This is the right call — the schema is the higher-authority spec source on which fields are optional.

- **Pattern fidelity to ADR-059.** The Monster Manual pattern (server-side procedural generation, deterministic seeding, typed-state injection into narrator prompt zones) is followed cleanly. Generator + CLI now; narrator-zone injection in 24-6; OTEL `proposed vs used` span in 24-7. Each story owns one tier of the pipeline.

### Decision

**Proceed to review.** All four mismatches are Option-A (update spec, no code change). Three are already deviation-logged by TEA with adequate rationale; the fourth is a trivial spec-text inconsistency on `--pack` vs `--genre` that I'm noting here rather than re-opening a deviation entry for. No mismatches require Option B (hand back to Dev). The implementation correctly applied the spec-authority hierarchy: authored sibling-story YAML schema (24-1/24-2 deliverables) > story-context proposal (24-5 draft).

**Handoff:** TEA / Radar O'Reilly for VERIFY phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — 6931 / 6931 server tests passing, simplify findings triaged and applied where in-scope.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (`sidequest/game/weather.py`, `sidequest/cli/weathergen/__init__.py`, `sidequest/cli/weathergen/__main__.py`, `sidequest/cli/weathergen/weathergen.py`, `tests/game/test_weather_generator.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | Cross-CLI argument-parsing duplication (high), yaml-load helper reuse (high), shared error-handler boilerplate (medium). All cross-story-scope. |
| simplify-quality | 4 findings | Unused `climate_rules` @property (high, dup of efficiency), missing docstring on `generate()` (high), `e.args[0]` parsing fragility (medium), `test_climate_rules_*` naming (medium). |
| simplify-efficiency | 1 finding | Unused `climate_rules` @property (high). |

### Findings Triage

| # | Finding | Confidence | Decision | Rationale |
|---|---------|------------|----------|-----------|
| 1 | CLI `--genre-packs-path` arg duplicated across namegen / encountergen / weathergen | high | **Defer** | Refactor would touch two CLIs out of this story's scope (namegen + encountergen are existing, working code). Cross-CLI shared-helper extraction is a future refactor story, not a 24-5 deliverable. |
| 2 | `WeatherGenerator.__init__` re-implements `sidequest.genre.loader._load_yaml` | high | **Defer** | `_load_yaml` is private API (leading underscore), raises `GenreLoadError` instead of `yaml.YAMLError`/`ValidationError`, and adopting it would break the test contracts (`test_generator_does_not_swallow_yaml_parse_errors`, `test_generator_uses_yaml_safe_load_not_full_load`). Reaching into another module's private surface is worse than 5 lines of inline yaml-load. |
| 3 | Shared CLI error-handler boilerplate | medium | **Defer** | Same scope issue as #1. Future cross-CLI refactor story. |
| 4 | Unused `WeatherGenerator.climate_rules` @property | high | **Applied** | True dead code — zero non-test consumers in the codebase. Removed in commit `aa32469`. If introspection is needed in 24-6 or 24-7, those stories reintroduce with a real use case. |
| 5 | `WeatherGenerator.generate()` missing docstring | high | **Applied** | The primary public surface had no docstring. Added in commit `aa32469`: documents zone/season/seed semantics, determinism guarantee, KeyError contract, and the downstream OTEL audit hook. |
| 6 | `e.args[0]` string parsing in CLI for KeyError messages | medium | **Defer** | Current pattern works under test, the comment in `weathergen.py:80` explicitly documents the contract with `weather.py`. Replacing with custom exception types (`UnknownWeatherZone(zone, available)`) is more code for marginal benefit and would require test rewrites. Tracked as observation for future hardening. |
| 7 | `test_climate_rules_*` naming "misleading" | medium | **Dismissed** | The finding mischaracterizes the tests. `ClimateRulesFile` is a public class under test — the tests validate its YAML-schema enforcement (mismatched weights, empty zones, extra fields). The naming is accurate. |

**Applied:** 2 high-confidence fixes (commit `aa32469`)
**Flagged for Review:** 2 medium-confidence findings (#6 fragile-error-extraction observation, future hardening if it ever bites)
**Noted:** 3 high-confidence cross-scope findings (#1/#2/#3 cross-CLI refactor — separate story material)
**Dismissed:** 1 finding (#7, naming finding mischaracterized the tests)
**Reverted:** 0

**Overall:** simplify: applied 2 fixes

### Regression Check

| Gate | Result |
|------|--------|
| `uv run pytest tests/game/test_weather_generator.py` (post-simplify) | 30 passed, 0 failed, 1.61s |
| `just server-check` (full lint + 6931-test suite) | exit 0, 6931 passed, 396 skipped, 0 failed, 119.49s |
| `uv run ruff check sidequest/game/weather.py` | All checks passed |
| `uv run pyright sidequest/game/weather.py` | 0 errors, 0 warnings |

No regression introduced by the simplify commit. The `climate_rules` property removal had no downstream impact — confirmed by grep across the whole `sidequest/` tree (only test names contain the substring; no actual usage).

### Verify-Phase Self-Check

- **Vacuous assertions:** None re-introduced. Reviewed the test file diff (zero churn this phase) — all assertions still check specific values, not truthiness.
- **Dead test coverage:** None added or left behind. The 30 tests all still target named ACs / rules.
- **Test/code coupling:** Slight increase from the docstring change — none. The tests don't assert on docstring presence.

### Handoff

To Reviewer / Colonel Sherman Potter for the review phase.

Branch: `feat/24-5-weather-generator` (sidequest-server, off develop). 3 commits:
1. `40d063b` — test (RED) — 30 failing tests
2. `65b8ad0` — feat (GREEN) — generator + CLI implementation
3. `aa32469` — refactor — simplify pass (remove unused property, add docstring)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (data only) | n/a |
| 2 | reviewer-edge-hunter | Yes | findings | 9 | confirmed 8, deferred 1 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 5 | confirmed 4, deferred 1 |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 7 (all applied) |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 | confirmed 6 (all applied) |
| 6 | reviewer-type-design | Yes | findings | 5 | confirmed 4, deferred 1 |
| 7 | reviewer-security | Yes | findings | 1 (low) | noted, no action — single-user threat model |
| 8 | reviewer-simplifier | Yes | findings | 4 | confirmed 2, dismissed 2 (style/judgment) |
| 9 | reviewer-rule-checker | Yes | findings | 3 (all dup of others) | confirmed 3 (all applied via overlapping findings) |

**All received:** Yes (9 returned, 8 with findings, 1 data-only)
**Total findings:** 33 raw → ~24 distinct after dedup → 22 confirmed, 4 deferred, 7 dismissed/duplicate

## Reviewer Assessment

**Verdict:** Approved after one rework commit (`aea6d63`).
**Quality gates after rework:** 42 / 42 weather tests pass (was 30); 6943 / 6943 full server suite passes (was 6931); ruff clean; pyright 0 errors.

The TEA verify pass was thorough but the adversarial review still surfaced
substantial findings — 24 distinct ones, of which 22 were confirmed and 18
applied in the rework commit. The other 4 were deferred with rationale, 3 were
duplicates of higher-confidence findings already actioned, and several test-style
finds were dismissed as judgment calls. Nine specialists ran in parallel and
their results converged tightly on the four real weak spots: typed exceptions
for unknown zone/season, missing validator invariants (all-zero weights,
inverted temp_range, special_event ↔ effects coupling), CLI error-handling
breadth, and test-environment fragility.

### Dispatch Tags

**[EDGE]** — 9 findings from `reviewer-edge-hunter`. Real boundary
gaps. Confirmed 8: all-zero weights (→ model_validator), inverted
temp_range (→ model_validator), missing `ValueError` catch in CLI (→
enumerated except + typed exceptions), empty `SIDEQUEST_CONTENT_PATH`
silent fallback to CWD (→ explicit reject + new test
`test_cli_empty_content_path_env_is_rejected`), cross-season RNG
stability gap when zones mix all-season + season-specific events (→
RNG-roll loop restructured: always consume draw, then check season; new
test `test_generator_cross_season_seed_stability_with_mixed_event_pools`),
untested `precipitation_chance=None` contract (→ new test
`test_generator_precipitation_defaults_false_when_chance_omitted`),
untested fired-event-with-empty-effects (→ new test
`test_generator_event_with_empty_effects_yields_vibe_only_state` —
note: refined design here, see TYPE below), YAML-top-level-list path
untested (→ new test `test_generator_yaml_top_level_list_is_rejected`),
CLI `ensure_ascii=True` escapes non-ASCII (→ `ensure_ascii=False`).
Deferred 1: NewType `ZoneId`/`SeasonId` for parameter confusion —
ceremony does not earn keep at this call density; the CLI already uses
keyword syntax. Revisit when there's a third caller.

**[SILENT]** — 5 findings from `reviewer-silent-failure-hunter`.
Confirmed 4: bare `except Exception` in CLI lost error class signal (→
enumerated `yaml.YAMLError | ValidationError | ValueError` with
`type(e).__name__` in stderr message), narrow `except KeyError` could
mask unrelated KeyErrors from a future refactor (→ resolved by typed
`UnknownWeatherZone`/`UnknownWeatherSeason` — catch is now structural,
not stringly-typed), dead `self._path` store (→ removed), `_run_cli`
env-stripping fragility (→ inherit `os.environ` + override
`SIDEQUEST_CONTENT_PATH`). Deferred 1: precipitation_chance silent
default to 0.0. Rationale: the schema explicitly marks the field
optional with "may be inferred from condition weights"; the comment is
now rewritten to be accurate about the 0.0 choice (per [DOC] below),
and a future improvement story can promote `0.0` to inference-from-conditions
if pack authoring patterns motivate it. The real authored
`tea_and_murder/weather.yaml` sets `precipitation_chance` explicitly in
every season, so no production path hits the fallback today.

**[TEST]** — 7 findings from `reviewer-test-analyzer`. All confirmed,
all applied. Most consequential: the YAML safe-load discriminator test
was vacuous — `!!python/object/apply:os.system` is rejected by
FullLoader too, so the test would have passed even if the code
regressed to `yaml.load(..., Loader=FullLoader)`. Replaced the payload
with `!!python/tuple`, which `safe_load` rejects but FullLoader
constructs into a Python tuple — actually distinguishing safe_load
from full. Other fixes: `test_cli_unknown_genre_exits_nonzero` was
relying on `neon_dystopia` being absent from `genre_packs/` (test would
silently invert if the workshopping pack is promoted) — replaced with
`__definitely_nonexistent_pack__`. The `_run_cli` env-stripping flagged
above. The "wiring" importability test now calls `main()` with bad
args and asserts non-zero `SystemExit` instead of just `hasattr`. Real-pack
schema test relaxed from hardcoded zone names to structural checks
(memory: `feedback_tests_not_point_at_content`). New tests added for
precipitation rolls firing True, season-agnostic events firing in any
season, and the cross-season RNG stability invariant noted under [EDGE].

**[DOC]** — 6 findings from `reviewer-comment-analyzer`. All confirmed,
all applied. The most material was the precipitation_chance comment
overclaiming "schema permits inference" — the schema does permit
inference, but the implementation chose hardcoded `0.0`, not inference;
the comment was framing a concrete design choice as a schema-derived
default. Rewritten to state the 0.0 choice plainly and note authors
should set the field explicitly if their pack uses rainy conditions.
Also: module docstring "added in story 24-6" was present-tense for
unimplemented work (→ softened); test file docstring pointed to the
gitignored `.session/` file (→ now points at the committed
`sprint/context/24-5-story-context.md`); CLI's `e.args[0]` workaround
comment is gone entirely now that typed exceptions replaced the pattern;
forward references to specific story numbers softened (memory:
`project_45_41_collision` — story IDs collide across machines).

**[TYPE]** — 5 findings from `reviewer-type-design`. Confirmed 4,
deferred 1. (1) All-zero weights bypass: now blocked by the
`SeasonPalette` model_validator's `sum(weights) == 0` check;
per-element `>= 0` moved from the validator to `Field(ge=0)` on the
inner type (simpler, catches earlier in the Pydantic pipeline). (2)
`WeatherState.special_event` / `effects` decoupling: now coupled at
the model layer — `effects` requires `special_event`. Refined the
reviewer's original "iff" suggestion: the YAML schema explicitly
permits events with empty effects (vibe-only events), so a fired
event with `effects=[]` is valid; only orphan effects with no event
are rejected. New tests cover both halves
(`test_weather_state_allows_event_with_empty_effects`,
`test_weather_state_rejects_effects_without_event`). (3) `temp_range`
ordering invariant added (mirrors weights validator). (5) `duration_days`
dead schema field: documented inline as schema-required for
`extra='forbid'` loading of the authored YAML, with a pointer that
downstream consumers may use it for event-duration tracking. Deferred:
(3) NewType for zone/season — see [EDGE].

**[SEC]** — 1 finding from `reviewer-security` (low). The `--genre`
argument is joined to `--genre-packs-path` without `Path.resolve()` or
a containment check, so `--genre ../../etc` could navigate above the
genre_packs directory. The CLI only ever appends `/weather.yaml` so
the worst case is reading an arbitrary `weather.yaml`-named file —
single-user threat model per `sidequest-server/CLAUDE.md` ("personal
project under slabgorb"). Documented and deferred; no action.

**[SIMPLE]** — 4 findings from `reviewer-simplifier`. Confirmed 2,
applied: dead `self._path` (also flagged by [SILENT]), per-element
weights `>= 0` migration to `Field(ge=0)` (also flagged by [TYPE]).
Dismissed 2 as test-style judgment: the round-trip test's 8
per-field assertions are diagnostically friendlier than `assert
reloaded == state` when a specific field fails serialization; the
focused `test_generator_records_zone_and_season` communicates intent
better than folding into an existing test.

**[RULE]** — 3 findings from `reviewer-rule-checker` (the backstop).
All overlap with thematic-subagent findings, all applied via the
shared fix: Rule #1 (bare except — fixed via [SILENT]), Rule #10
(`__all__` missing on a public module with 6 public names — added per
the sidequest/game/ peer convention), Rule #6 (test env stripping —
fixed via [TEST]). The rule-checker also re-verified the additional
CLAUDE.md rules: no silent fallbacks, no stubbing, "don't reinvent"
(wires the existing yaml + pydantic + stdlib rather than new
infrastructure), wiring tests present (CLI subprocess against real
content + in-process `main()` invocation). OTEL deferral to a future
story is documented in code and accepted (this is new feature code,
not a fix that touched an existing subsystem).

### Rule Compliance (Python lang-review checklist)

Personally re-verified against the rework commit:

| Rule | Status | Note |
|------|--------|------|
| #1 Silent exception swallowing | pass | CLI catch is now enumerated (`yaml.YAMLError | ValidationError | ValueError`); typed `UnknownWeatherZone`/`UnknownWeatherSeason` replace `KeyError + e.args[0]` parsing. |
| #2 Mutable default arguments | pass | All `Field(default_factory=list)`; no bare `[]`/`{}` defaults. |
| #3 Type annotation gaps | pass | Every public function and `__init__` annotated. |
| #4 Logging | pass | No logging surface; CLI uses stderr prints. |
| #5 Path handling | pass | `read_text(encoding="utf-8")`; all paths via `pathlib.Path`. |
| #6 Test quality | pass | Vacuous safe_load test replaced; env-stripping fixed; wiring test now exercises real behavior; no `assert True` / `assert result` anywhere; 0 `pytest.mark.skip`. |
| #7 Resource leaks | pass | `read_text()` closes its file handle; no `open()` outside a `with`. |
| #8 Unsafe deserialization | pass | `yaml.safe_load` (and now actually proven by the `!!python/tuple` test). |
| #9 Async pitfalls | n/a | No async code. |
| #10 Import hygiene | pass | `__all__` added to `weather.py`; no star imports. |
| #11 Input validation at CLI boundary | pass | argparse `required=True` on all four args; empty `SIDEQUEST_CONTENT_PATH` rejected; unknown zone/season surface via typed exceptions. |
| #12 Dependency hygiene | pass | No new dependencies. |
| #13 Fix-introduced regressions | pass | Self-checked the rework commit against #1–#12 — no new violations. |
| #14 State cleanup ordering | n/a | No one-shot queue/buffer pattern. |

### Wiring Discipline

Verified the WeatherGenerator has real non-test consumers:
1. `sidequest.cli.weathergen.weathergen.main()` — invoked by `python -m sidequest.cli.weathergen` (test subprocess against real content, and the in-process callable-with-bad-args test).
2. The narrator-dispatch wiring is **not** in this story per the story-context deviation log — explicitly deferred. The "Gap: SceneSetting seam does not exist" finding from TEA is carried forward and tagged blocking-for-the-next-story-in-the-epic so the future Dev assigned to it picks it up.

### Decision

**Approved.** Rework commit `aea6d63` addresses every confirmed finding. Quality gates clean across the board: 42 weather-suite tests pass, 6943 server-suite tests pass, lint + type-check both clean. Branch is ready to merge.

**Next:** Push branch, open PR against `develop`, merge.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-20T20:54:31Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-20T16:10:00Z | 2026-05-20T20:09:59Z | 3h 59m |
| red | 2026-05-20T20:09:59Z | 2026-05-20T20:19:29Z | 9m 30s |
| green | 2026-05-20T20:19:29Z | 2026-05-20T20:26:44Z | 7m 15s |
| spec-check | 2026-05-20T20:26:44Z | 2026-05-20T20:29:09Z | 2m 25s |
| verify | 2026-05-20T20:29:09Z | 2026-05-20T20:35:10Z | 6m 1s |
| review | 2026-05-20T20:35:10Z | 2026-05-20T20:52:30Z | 17m 20s |
| spec-reconcile | 2026-05-20T20:52:30Z | 2026-05-20T20:54:31Z | 2m 1s |
| finish | 2026-05-20T20:54:31Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings at setup.

### TEA (test design)

- **Conflict** (non-blocking): Story-context AC1 specifies a `WeatherState` shape (`temperature: str` categorical ladder, `wind`, `intensity: float`, `narrative_flourish: str`) that doesn't match the sibling-story 24-1 JSON Schema and 24-2 authored YAML.
  Affects `sprint/context/24-5-story-context.md` (AC1 should be regenerated against the shipped schema next time the context is refreshed).
  *Found by TEA during test design.*

- **Conflict** (non-blocking): Story-context AC3 placement claim — "extend `sidequest/genre/models/scenario.py` with `ClimateRules`, `ClimateZone`" — collides with the namegen co-location pattern and uses a schema-incorrect `season_list` field. Climate models belong with the generator (`sidequest/game/weather.py`).
  Affects `sprint/context/24-5-story-context.md` (AC3 + Touch Points table).
  *Found by TEA during test design.*

- **Gap** (blocking-for-24-6): Story-context AC5 references `SceneSetting.weather` as the integration seam at `sidequest/genre/models/scenario.py:132`. No `SceneSetting` class exists in the codebase — the only weather field is `AtmosphereVariant.weather: str` (authored scenario data, not runtime state). The narrator-dispatch wiring path doesn't exist yet; it is the explicit deliverable of story 24-6.
  Affects `sidequest-server/sidequest/genre/models/scenario.py:132` (clarify whether AtmosphereVariant is the intended seam or a new runtime SceneSetting must be introduced in 24-6).
  *Found by TEA during test design.*

- **Gap** (non-blocking): Story-context references `climate.yaml`; the authored file is `weather.yaml` at `sidequest-content/genre_packs/tea_and_murder/weather.yaml`. Generator implementation should load `weather.yaml`, not `climate.yaml`.
  Affects `sprint/context/24-5-story-context.md` (filename references throughout).
  *Found by TEA during test design.*

- **Improvement** (non-blocking): The orchestrator sprint `complete` commits for 24-2 and 24-3 (a02b643-era) were merged in `sidequest-content` but my local content checkout was stale by two PRs (#241, #242) before this story started. Running `git pull` in the content subrepo was necessary. SM setup may want to add a content-pull-current preflight to setup gate for any story that consumes content-repo deliverables from recent sibling stories.
  Affects `pennyfarthing/gates/sm-setup-exit` (consider adding subrepo-currency check).
  *Found by TEA during test design.*

### Dev (implementation)

- No upstream findings during implementation. Test surface from TEA was precise enough to implement against directly. The three deviations logged by TEA (WeatherState shape, climate-models placement, AC5 wiring scope) all held up under implementation — no additional drift discovered.
  *Found by Dev during implementation.*

### TEA (test verification)

- **Improvement** (non-blocking): Three CLI tools (namegen, encountergen, weathergen) now share an identical `--genre-packs-path` argument + `SIDEQUEST_CONTENT_PATH` env-var fallback pattern (≈6 LOC each). simplify-reuse flagged this as high-confidence duplication. Worth a future refactor story to extract `sidequest.cli.shared.add_genre_packs_path_arg()` — but only after a third or fourth CLI ships using the same pattern, to avoid premature abstraction.
  Affects `sidequest-server/sidequest/cli/{namegen,encountergen,weathergen}/*.py`.
  *Found by TEA during test verification.*

- **Improvement** (non-blocking): `sidequest.genre.loader._load_yaml(path, type_)` already implements the "read_text + safe_load + isinstance check + model_validate + raise GenreLoadError" pattern that `WeatherGenerator.__init__` re-implements inline. Promoting `_load_yaml` to a public helper (and refactoring callers to use it) would centralize YAML-load semantics across the server. Currently deferred because the helper is private and changes the exception type the tests expect. Tracked as a future "loader consolidation" improvement.
  Affects `sidequest-server/sidequest/genre/loader.py` + future weather/calendar/demographics generators.
  *Found by TEA during test verification.*

- **Question** (non-blocking): The CLI's KeyError-message extraction at `weathergen.py:80` uses `e.args[0]` to recover the human-readable error from the generator's `KeyError`. simplify-quality flagged this as medium-confidence fragility — if a future maintainer rewrites the generator's exceptions, the CLI silently loses its error message contract. A custom exception type (`UnknownWeatherZone(zone, available)`) with structured data would be more durable. Not urgent (covered by `test_cli_unknown_zone_exits_nonzero_with_named_zone` which would catch a regression), but worth considering when the next world-grounding generator (calendar, demographics) needs the same error-surface pattern.
  Affects `sidequest-server/sidequest/cli/weathergen/weathergen.py:80` + future world-grounding CLIs.
  *Found by TEA during test verification.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No deviations at setup.

### Architect (reconcile)

- **OTEL span verification deferred entirely to story 24-7 (not partially in 24-5)**
  - Spec source: `sprint/context/24-5-story-context.md`, AC5 ("Wiring Test")
  - Spec text: "Verify OTEL span is emitted (story 24-7 will add the span; this test verifies it fires)"
  - Implementation: No OTEL span is emitted by `WeatherGenerator` or the CLI. The module docstring and the `generate()` docstring explicitly defer the proposed-vs-used span to story 24-7. No 24-5 test asserts on OTEL span emission.
  - Rationale: AC5's text is internally contradictory — it says story 24-7 *adds* the span, and that *this* (24-5) test *verifies it fires*. A test cannot meaningfully assert on a span the same AC says doesn't exist yet. The Reviewer's `[RULE]` backstop classified this as "documented deferral" (the deferral is captured in code, in the module docstring, and in sibling-story 24-7's title — "OTEL spans for weather generation (proposed vs used)"). The implementation followed the larger epic plan rather than the literal AC text.
  - Severity: minor
  - Forward impact: Story 24-7 owns both the span definition and the verification test. The 24-7 setup should treat the absence of an `assert` on weather-OTEL in 24-5 as expected, not as a missing test to backfill.

- **TEA & Dev deviation entries verified accurate**
  - Spec source: `.session/24-5-session.md` (this file), `### TEA (test design)` and `### Dev (implementation)` subsections
  - Spec text: three TEA deviations (WeatherState shape, climate-models placement, AC5 wiring scope) + Dev's "no findings" record
  - Implementation: Verified each TEA deviation against the committed code (`sidequest/game/weather.py`, `sidequest/cli/weathergen/weathergen.py`, `tests/game/test_weather_generator.py`). Spec-source paths exist. Spec text quotes match the story-context file. Implementation descriptions match what shipped. Forward-impact claims are still accurate (24-6 still owns narrator-dispatch wiring; the "Gap: SceneSetting seam does not exist" delivery finding remains valid). Dev's "no upstream findings" remains correct — the rework commit was Reviewer-driven, not Dev-deviation-driven.
  - Rationale: Spec-reconcile contract is to audit the in-flight deviation log for drift. No annotations needed; all entries are accurate as written.
  - Severity: n/a (verification record)
  - Forward impact: none

### TEA (test design)

- **WeatherState field set realigned to authored schema**
  - Spec source: context-story-24-5.md, AC1
  - Spec text: '`WeatherState(condition, temperature: str ["cold"|"cool"|...], wind, special_event, intensity: float, narrative_flourish: str)`'
  - Implementation: Tests target `WeatherState(zone: str, season: str, condition: str, temperature_c: float, precipitation: bool, special_event: str | None, effects: list[str], seed: int)` — matching the actual authored schema/YAML.
  - Rationale: Sibling story 24-1 (JSON Schema) and 24-2 (`genre_packs/tea_and_murder/weather.yaml`) shipped a different shape than the story-context proposal. The schema has numeric `temp_range` (Celsius), open-enum `conditions`, `precipitation_chance`, and `special_events` as objects with `name`/`effects`. There is no `wind` axis, no categorical temperature ladder, no per-condition `narrative_flourish` text. Inventing those fields would either require unauthored data (silent default → forbidden by SOUL) or stubbing (forbidden by CLAUDE.md). Authored content wins. Story-context AC1 was drafted before the schema/YAML was final.
  - Severity: moderate
  - Forward impact: Story 24-6 (prompt-zone injection) consumes the WeatherState shape — narrator template wiring authors against the realigned fields, not the original proposal.

- **Pydantic climate models live in `sidequest/game/weather.py`, not `genre/models/scenario.py`**
  - Spec source: context-story-24-5.md, AC3 + Touch Points table
  - Spec text: "Extend `sidequest/genre/models/scenario.py` with `ClimateRules`, `ClimateZone` pydantic models. … `class ClimateRules: zones: Dict[str, ClimateZone]; season_list: List[str]`"
  - Implementation: Climate-rules pydantic models (`ClimateRulesFile`, `ClimateZone`, `SeasonPalette`, `SpecialEvent`) co-locate with the generator in `sidequest/game/weather.py`. The top-level YAML key is `climate_zones` (not `zones`); there is no `season_list` field — season ids are the keys of `seasons`.
  - Rationale: `genre/models/scenario.py` carries scenario-authoring models (clue graph, atmosphere variants, beliefs). Weather is runtime world-grounding, not scenario authoring — different concern, different consumer (narrator prompt vs scenario init). Co-locating with the generator follows the namegen pattern and keeps the loader free of cross-cutting climate logic. The proposed `season_list` field doesn't exist in the schema, so claiming it would require silent invention.
  - Severity: minor
  - Forward impact: 24-6 imports climate models from `sidequest.game.weather`, not `sidequest.genre.models.scenario`. Tests target the new module path.

- **AC5 wiring test scoped to CLI subprocess, not dispatch pipeline**
  - Spec source: context-story-24-5.md, AC5
  - Spec text: "Load a scenario fixture for tea_and_murder/glenross. Trigger weather generation in the game dispatch pipeline. Assert `SceneSetting.weather` is populated with `WeatherState` (not null, not old string)."
  - Implementation: Wiring test invokes `python -m sidequest.cli.weathergen --pack tea_and_murder --zone glen_floor --season winter --seed 12345` via subprocess against real content; asserts JSON output is a valid `WeatherState`. No dispatch-pipeline integration in 24-5.
  - Rationale: (1) `SceneSetting` does not exist in the codebase — the story-context seam is stale; the only `weather: str` field is `AtmosphereVariant.weather` at `genre/models/scenario.py:132`, which is authored scenario data, not runtime state. (2) The narrator-side dispatch wiring (prompt-zone injection, scenario init hook) is the explicit deliverable of story 24-6 per the epic plan. Forcing a dispatch wire here would either stub 24-6 (forbidden) or land a half-wired feature (forbidden). (3) The CLI is a real non-test consumer of `WeatherGenerator` — invoking it via subprocess satisfies the "called from production code path" wiring requirement per CLAUDE.md and the SM Assessment's "Better: wire it now…" guidance. The namegen and encountergen tests use the same CLI-subprocess wiring pattern (see `tests/cli/test_encountergen.py:34`).
  - Severity: moderate
  - Forward impact: Story 24-6 owns the narrator-dispatch wiring test ("scenario init → WeatherGenerator.generate() → narrator VALLEY zone receives WeatherState"). The 24-5 session findings will flag this explicitly so 24-6 setup picks it up.