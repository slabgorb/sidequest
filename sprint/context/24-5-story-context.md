# Story 24-5: Python Weather Generator in sidequest-server

**Story ID:** 24-5  
**Epic:** 24 (Procedural World-Grounding Systems)  
**Points:** 3  
**Priority:** p0  
**Workflow:** tdd  
**Repos:** sidequest-server  
**Status:** backlog

---

## Story Summary

Implement a Python weather generator in sidequest-server that reads climate YAML (authored in story 24-2 for tea_and_murder/glenross) and RNG seed, producing typed weather state. Follow the existing namegen module + CLI pattern. The generator will populate the free-form `SceneSetting.weather` field (currently a string) with structured weather state.

**Architectural note:** This is a Python implementation post-ADR-082. The Rust backend was ported back to Python per ADR-082 (accepted); read both ADR-082 and ADR-087 (successor pointer) for context on the Monster Manual pattern migration.

---

## Architecture & Patterns

### Monster Manual Pattern (ADR-059)

The weather generator follows ADR-059 Monster Manual pattern:
1. YAML content defines rules/baselines in genre packs (`tea_and_murder/climate.yaml`)
2. Python generator produces structured state from YAML + RNG seed
3. State injected into narrator prompt zones via dispatch pipeline
4. Narrator selects from proposed state, system reconciles
5. OTEL verifies proposed vs used (story 24-7)

### Reference Implementations

**Existing namegen pattern to follow:**
- CLI entry: `sidequest-server/sidequest/cli/namegen.py`
- Module layout: `sidequest-server/sidequest/corpus/` (name generation infrastructure)
- Markov-based naming: `sidequest-server/sidequest/corpus/markov.py`
- Generator pattern: Single entry point, typed return, RNG seed control

### Integration Seam

**File:** `sidequest-server/sidequest/genre/models/scenario.py:132`

Current definition:
```python
class SceneSetting(BaseModel):
    # ... other fields ...
    weather: str  # Currently free-form string
```

The new generator will populate this field with typed weather state (e.g., `WeatherState` pydantic model).

### Climate YAML Location

**File:** `sidequest-content/genre_packs/tea_and_murder/climate.yaml`

Authored in story 24-2 (now complete). Contains:
- Climate zones (coastal, inland, upland)
- Seasonal conditions (spring/summer/autumn/winter)
- Special weather events (storms, floods, frosts)
- Frequency tables for generation

### Pack Architecture

Per retired ADR-072: packs remain monolithic. Weather YAML lives in the pack root alongside other config files, NOT in a layered system/ folder.

---

## Acceptance Criteria

### AC1: WeatherState Pydantic Model

**File:** `sidequest-server/sidequest/game/weather.py` (new file)

Define typed weather state model:
```python
class WeatherState(BaseModel):
    condition: str  # e.g., "clear", "cloudy", "rainy", "stormy"
    temperature: str  # e.g., "cold", "cool", "mild", "warm"
    wind: str  # e.g., "calm", "breezy", "windy", "gale"
    special_event: Optional[str]  # e.g., "frost", "flood", "mist"
    intensity: float  # 0.0 to 1.0
    narrative_flourish: str  # 1-2 sentence flavor prose for narrator context
```

### AC2: WeatherGenerator Class

**File:** `sidequest-server/sidequest/game/weather.py`

Implement:
```python
class WeatherGenerator:
    def __init__(self, climate_yaml_path: str):
        """Load climate rules from YAML."""
        self.climate_rules = load_yaml(climate_yaml_path)
    
    def generate(
        self, 
        zone: str,  # e.g., "coastal"
        season: str,  # e.g., "winter"
        rng_seed: int
    ) -> WeatherState:
        """Generate weather state from climate rules, RNG seed."""
        # Implementation follows namegen pattern:
        # 1. Seed RNG
        # 2. Select from frequency table for zone+season
        # 3. Derive intensity from randomness
        # 4. Generate narrative flourish (optional — can be simple)
        # Returns WeatherState instance
```

**API design:** Single entry point, pure function (same seed = same output), no side effects.

### AC3: Climate YAML Schema Validation

**File:** `sidequest-server/sidequest/genre/models/scenario.py` (extend)

Define Pydantic model for climate YAML structure:
```python
class ClimateZone(BaseModel):
    conditions: List[str]
    seasonal_modifiers: Dict[str, Dict[str, float]]  # season -> condition -> frequency
    special_events: Optional[List[str]]

class ClimateRules(BaseModel):
    zones: Dict[str, ClimateZone]
    season_list: List[str]
```

Validate on load: `ClimateRules.model_validate(loaded_yaml)`.

### AC4: CLI Entry Point

**File:** `sidequest-server/sidequest/cli/weathergen.py` (new file, following namegen pattern)

Implement:
```bash
uv run sidequest cli weathergen \
    --pack tea_and_murder \
    --zone coastal \
    --season winter \
    --seed 12345
```

Output: JSON `WeatherState` instance. Primary tool for prompt preview loop testing.

### AC5: Wiring Test (Integration)

**File:** `sidequest-server/tests/game/test_weather_generator.py`

Test that generator is called from production code path, NOT just unit-tested in isolation:

1. **Unit tests (RED phase):**
   - `test_weather_generator_determinism` — same seed produces same output
   - `test_climate_yaml_validation` — rejects malformed climate YAML
   - `test_weather_state_schema` — WeatherState serializes/deserializes correctly

2. **Wiring test (GREEN phase):**
   - Load a scenario fixture for tea_and_murder/glenross
   - Trigger weather generation in the game dispatch pipeline
   - Assert SceneSetting.weather is populated with WeatherState (not null, not old string)
   - Verify OTEL span is emitted (story 24-7 will add the span; this test verifies it fires)

**Critical rule:** The wiring test must verify the generator is **called from the production code path** — scenario initialization or on-tick (ADR-059 pattern), not just tested in isolation.

### AC6: No Silent Fallbacks

Per CLAUDE.md critical principles:

- If climate YAML is missing → fail loudly (raise exception, not silently use defaults)
- If zone not found in climate rules → fail loudly
- If RNG seed is invalid → fail loudly

Document these constraints in docstrings and error messages.

### AC7: No Stubbing

Do not create placeholder implementations or skeleton code. If a feature (e.g., narrative flourish prose generation) isn't implemented now, don't leave an empty method. Either implement it fully or omit the field.

---

## Testing Strategy

### 1. Prompt Preview Loop (Primary)

Use `scripts/preview-prompt.py` to iterate:
1. Generate weather for tea_and_murder/glenross (various seeds + seasons)
2. Wire into prompt zone
3. Preview narrator output
4. Iterate on YAML until variety + consistency is good

### 2. Unit Tests (RED Phase)

- Determinism (same seed → same output)
- Climate YAML validation
- WeatherState schema validation
- Edge cases (invalid zone, invalid season, boundary RNG values)

### 3. Integration Test (GREEN Phase)

- Full scenario load with weather generation
- Verify production code path (dispatcher calls generator on scenario init)
- OTEL span emitted (dry-run; story 24-7 adds the actual span)
- SceneSetting.weather populated, not null

### 4. Smoke Playtest (AC11, story 24-8)

Full playtest with narrator variety observed via GM panel.

---

## Related Stories & Dependencies

- **24-2** (DONE): Authored tea_and_murder/glenross climate.yaml — weather generator consumes this
- **24-3** (DONE): Authored glenross demographics — parallel work, no hard dependency
- **24-4** (BACKLOG): Author glenross calendar — parallel work, no hard dependency
- **24-6** (BACKLOG): Prompt zone injection — depends on this story; extends narrator template to include weather
- **24-7** (BACKLOG): OTEL spans — depends on this story; adds observability to weather generation decision

---

## Constraints & Assumptions

### Constraints
- Generator must be deterministic: same seed produces same output
- No live RNG calls outside the generator (all randomness sourced through RNG seed)
- WeatherState must be serializable (Pydantic BaseModel)
- Climate YAML must validate on load (Pydantic schema)
- Must not break existing SceneSetting schema (only populate the weather field)

### Assumptions
- climate.yaml (tea_and_murder/glenross) is correctly authored per story 24-2 (DONE)
- namegen module patterns are stable and can be safely copied
- Narrator will not be wired until story 24-6 (this story is backend-only, no UI changes)
- OTEL tooling is already in place (story 24-7 adds the span definitions)

---

## Touch Points (Code Locations)

### sidequest-server

| File | Change | AC |
|------|--------|----| 
| `sidequest/game/weather.py` | New file: WeatherState, WeatherGenerator classes | 1, 2 |
| `sidequest/genre/models/scenario.py` | Extend with ClimateRules, ClimateZone pydantic models | 3 |
| `sidequest/cli/weathergen.py` | New file: CLI entry point (following namegen pattern) | 4 |
| `tests/game/test_weather_generator.py` | New file: unit + wiring tests | 5 |

### sidequest-content

| File | Change | AC |
|------|--------|----| 
| `genre_packs/tea_and_murder/climate.yaml` | Already exists (story 24-2, DONE) — generator consumes | Input |

### sidequest-ui

| File | Change | AC |
|------|--------|----| 
| (None for this story) | UI wiring deferred to 24-6 (prompt injection) | - |

---

## Narrative Anchor

Per CLAUDE.md, this story serves:

- **Keith (forever-GM-now-player):** Structured weather state fed to narrator enables consistent world grounding — Scottish village weather drives scene framing, narrator can't improvise away season/climate mechanics.
- **James (narrative-first):** Weather context enriches narration variety — no longer generic "it's morning"; now "it's a cold March morning after last night's frost in the glenross hills" — more specific, more engaging.
- **Alex (slow typist, freeze-prone):** Weather is pure backend; no UI time pressure. Submit-and-wait turn barrier unchanged.
- **Sebastien (mechanics-first):** GM panel will show weather generation decisions as OTEL spans (story 24-7) — he can see the mechanical grounding, not improvisation.

---

## Related Documents

- **Epic context:** `sprint/context/context-epic-24.md`
- **ADR-059:** Monster Manual pattern (protocol for procedural generation)
- **ADR-082:** Rust→Python port (context on backend architecture)
- **ADR-087:** Post-Port Subsystem Restoration Plan (successor pointer)
- **Climate YAML:** `sidequest-content/genre_packs/tea_and_murder/climate.yaml` (story 24-2)
- **Scenario model:** `sidequest-server/sidequest/genre/models/scenario.py`
- **Namegen reference:** `sidequest-server/sidequest/cli/namegen.py` + `sidequest-server/sidequest/corpus/`
- **Preview tool:** `scripts/preview-prompt.py`
