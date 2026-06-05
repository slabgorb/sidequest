# Story Context: 88-1 — AWN Plan 1 engine

**Story:** 88-1  
**Title:** AWN Plan 1 engine — thin awn ruleset module + binding seams + wiring/chargen tests  
**Type:** Feature  
**Points:** 5  
**Workflow:** tdd  
**Epic:** 88 (Ashes Without Number — mutant_wasteland ruleset port)  
**Repos:** sidequest-server  

---

## Story Summary

Implement the **foundation engine layer** for Ashes Without Number (AWN), a faithful port of the post-apocalyptic SRD by Kevin Crawford / Sine Nomine. AWN combat is mechanically identical to Cities Without Number (CWN) — the system is already built in the engine. Plan 1 binds and wires AWN:

1. Create a thin `AwnRulesetModule(CwnRulesetModule)` subclass with slug `"awn"`
2. Register it in the ruleset registry
3. Implement `AwnConfig(CwnConfig)` and add it to `RulesConfig`
4. Fix six slug-string binding sites so AWN characters get System Strain pools and combat resolution works
5. Add comprehensive wiring tests to verify the integration is live (using OTEL span assertions per server CLAUDE.md)

**Why:** `mutant_wasteland` currently runs the dial engine (no ablative HP, no crunch). Sebastien and Jade named this in the broken `coyote_star` session — a narrator improvising combat with nothing mechanical underneath. AWN fixes this by binding the existing CWN combat engine.

**Load-bearing:** This story gates every downstream Plan (Mutations, Radiation, Disease, Stress, Survival, hexcrawl, Creatures, Enclaves). Story 88-2 (content — mutant_wasteland pack binding) depends on the `_validate_awn` implemented here so the pack loads.

---

## Design Reference

**Authoritative spec:** `docs/superpowers/specs/2026-06-05-ashes-without-number-mutant-wasteland-design.md`

- **§6 Plan 1:** High-level design
- **§11 Architect Addendum:** Seam analysis + the two binding styles (capability vs. slug-string)
- **§11.2 MUST-change list:** The exact six items to fix (1–7)
- **§11.4 Test guidance:** Span-assertion strategy + mandatory tests

**Key precedents:** 
- `2026-05-28-neon-cwn-ruleset-design.md` — CWN module (CWN subclasses SWN)
- `2026-06-04-road-warrior-cwn-rig-combat-design.md` — genre pack binding to a sister module
- ADR-117 (Pluggable Ruleset Module System)
- ADR-114 (Ablative HP substrate)

---

## Acceptance Criteria (from spec §11.2 & §11.4)

### Engine Implementation (Items 1–7)

1. **New module:** `sidequest/game/ruleset/awn.py`
   - Class `AwnRulesetModule(CwnRulesetModule)`
   - `slug = "awn"`
   - No method overrides in Plan 1 (all inherited from CWN)
   - Docstring explains the inheritance and why the subclass exists

2. **Registry:** `sidequest/game/ruleset/registry.py`
   - Import `AwnRulesetModule`
   - Add to `_REGISTRY`: `AwnRulesetModule.slug: AwnRulesetModule()`
   - Verify unknown slug still fails (no silent default)

3. **Config model:** `sidequest/genre/models/rules.py`
   - New class `AwnConfig(CwnConfig)` (empty body; inherits system_strain/trauma/attribute_map; hacking stays None)
   - New field in `RulesConfig`: `awn: AwnConfig | None = None`
   - New validator `_validate_awn` (mirror `_validate_cwn`):
     - Return early if `ruleset != "awn"`
     - Initialize `awn` to `AwnConfig()` if None
     - Require complete six-key `attribute_map` (STRENGTH, CONSTITUTION, DEXTERITY, INTELLIGENCE, WISDOM, CHARISMA)
     - Validate all keys are in `ability_score_names`
     - Validate `system_strain.max_source` is a key in `attribute_map`
     - Validate `trauma.major_injury_save` is one of {physical, evasion, mental, luck}
   - Update `ruleset_config()` method to add `awn` branch

4. **Chargen strain-pool fix:** `sidequest/game/builder.py:82` `seed_system_strain`
   - **Current:** `if rules.ruleset != "cwn" or rules.cwn is None: return None`
   - **Issue:** AWN characters get no strain pool (silent fall-through on the string check)
   - **Recommended fix (capability form):**
     ```python
     cfg = rules.ruleset_config()
     if not isinstance(cfg, CwnConfig):  # Covers CWN + AWN + future subclasses
         return None
     con_flavor = cfg.attribute_map["CONSTITUTION"]
     ```
   - This auto-covers AWN and immunizes against the next sister module

5. **Mortal/Major Injury gate:** `sidequest/server/dispatch/downed_seam.py:128`
   - **Current:** `if not (pack and pack.rules and pack.rules.ruleset in ("cwn", "wwn")):`
   - **Fix:** Align to isinstance form already used at line 71:
     ```python
     if not (pack and pack.rules and isinstance(pack.rules.ruleset_config(), (CwnConfig, WwnConfig))):
     ```

6. **Stabilize tool guard:** `sidequest/agents/tools/stabilize_mortal_injury.py:101`
   - **Current:** `if pack is None or pack.rules is None or pack.rules.ruleset != "cwn":`
   - **Issue:** AWN has the stabilize-at-0 rule (SRD p.52) but is blocked
   - **Fix (preferred):** Change to `isinstance(module, CwnRulesetModule)` (the assert at :99 already passes for AWN)
   - Or (string alternative): Add `or pack.rules.ruleset == "awn"`

7. **Strain adjustment tool guard:** `sidequest/agents/tools/adjust_system_strain.py:89`
   - **Current:** `if pack is None or pack.rules is None or pack.rules.ruleset != "cwn":`
   - **Issue:** AWN uses System Strain but is blocked
   - **Fix:** Same as Item 6 (prefer isinstance form)

### Verification (Items 8–9)

8. **FREE sites (no edit, verify via test):**
   - `cwn.py:100/153/237` — inherited cfg asserts (isinstance already passes for AWN)
   - `downed_seam.py:71` — already uses isinstance form
   - `dice.py:341` — override probe for shock resolution
   - `dice.py:776` — opponent reprisal (method-override check)
   - Confirm with tests that these paths work for AWN

9. **Out-of-scope (DO NOT touch):**
   - Hacking gates (`dice.py:328`, `encounter_lifecycle.py:1324`) — AWN correctly has no hacking; AwnConfig.hacking stays None
   - WWN-only subsystems — no change
   - Dogfight (`dogfight_shot.py:324`) — AWN vehicles are a later plan

### Mandatory Wiring Tests (per §11.4)

**All tests use OTEL span assertions + fixture behavior tests, NO source-text regex matching.**

1. **Registry tests** (`tests/game/ruleset/test_registry.py`)
   - `test_get_ruleset_module_awn_resolves`: Call `get_ruleset_module("awn")` → returns `AwnRulesetModule`
   - `test_get_ruleset_module_unknown_fails_loud`: Unknown slug raises `UnknownRulesetError`

2. **Config load tests** (exercises `_validate_awn`)
   - `test_awn_config_loads_with_complete_attribute_map`: Fixture pack with valid six-key map → loads
   - `test_awn_config_fails_on_incomplete_attribute_map`: Missing key → validation error
   - `test_awn_config_fails_on_bad_major_injury_save`: Invalid save name → validation error

3. **Chargen smoke test** (regression guard for Item 4 gap)
   - `test_seed_system_strain_awn_character_gets_pool`: AWN chargen with CON=14 → system_strain pool with max=14
   - `test_seed_system_strain_non_awn_returns_none`: Other rulesets still return None

4. **Integration/wiring test** (production dispatch path)
   - `test_awn_combat_turn_fires_cwn_spans_and_depletes_hp`:
     - Load awn-bound pack (fixture with `ruleset: awn`)
     - Seed game state with two AWN characters in combat
     - Run one player action through production dispatch (actual narrator + OTEL telemetry)
     - **Assertions:**
       - `get_ruleset_module("awn")` resolves (no UnknownRulesetError)
       - Inherited `cwn.*` spans fire: `cwn.shock.applied`, `cwn.trauma.roll`, `cwn.mortal_injury.declared`
       - `state_patch_hp` span shows HP depletion on ablative pool
       - Opponent reprisal fires (counter-attack narrated if opponent alive)

---

## Technical Implementation Notes

### The Two Binding Styles (§11.1 Load-Bearing Finding)

The engine binds ruleset behavior two ways, and `awn` is treated differently by each:

| Binding style | Pattern | Sites | Works for `awn`? |
|---|---|---|---|
| **Capability** | `isinstance(cfg, CwnConfig)`, `isinstance(module, CwnRulesetModule)`, method-override probes | `cwn.py:100/153/237`, `downed_seam.py:71`, `dice.py:341/776` | **Yes — free.** `AwnConfig`/`AwnRulesetModule` *are* their parents. |
| **Slug-string** | `rules.ruleset == "cwn"`, `ruleset in ("cwn","wwn")`, `ruleset != "cwn"` | `rules.py:ruleset_config()`, `builder.py:90`, `downed_seam.py:128`, tools | **No — silent fall-through.** Each must be taught `"awn"`. |

The capability style is the better pattern (see opponent reprisal at dice.py:776 — it just works for AWN). The slug-string style is fragile and breaks on every new sister module.

**This story's fix:** Items 4–7 refactor to capability form where possible, closing the gaps for AWN and future modules.

### Why No Method Overrides in Plan 1?

AWN and CWN are mechanically identical for personal combat:
- Attack roll: d20 + bonus + skill + attr-mod vs AC (identical)
- Skill check: 2d6 + skill + attr-mod vs difficulty ladder 6/8/10/12/14 (identical)
- Saves: Physical/Evasion/Mental/**Luck** with d20 ≥ 15−(level−1) (CWN added Luck; AWN uses it)
- Shock/Trauma/System Strain/Mortal Injury/Major Injury: all identical

Future Plans (Mutations, Radiation) may add AWN-specific mechanics, so the subclass exists as a home for them. For now, it inherits everything.

### No Hacking

AWN has the "Program" skill but no cyberspace net-run ladder. `AwnConfig.hacking` stays `None` (CwnConfig default). The hacking gates (`dice.py:328`, `encounter_lifecycle.py:1324`) correctly skip AWN; that's not a bug, it's correct behavior.

---

## Dependencies

**Upstream:** None (this is the foundation)

**Downstream:**
- **Story 88-2** (content — mutant_wasteland pack binding) depends on `_validate_awn` so the pack loads
- **Plans 2–7** (Mutations, Radiation, Disease, Stress, Survival, Creatures, Enclaves) depend on Plan 1's foundation

---

## Testing Strategy

Per server CLAUDE.md "No Source-Text Wiring Tests": never grep production code as a wiring assertion. Instead:

1. **OTEL span assertions** — every subsystem decision emits a span. Drive the flow, assert the span fired.
2. **Fixture-driven behavior tests** — construct synthetic state, fire real handlers, assert the message went out.
3. **Registry/decorator dispatch** — test that the wiring is reachable from production code paths.

**Integration test shape** (Item 4):
- Fixture: minimal awn-bound genre pack (rules.yaml with `ruleset: awn`, six-key attribute_map, one archetype)
- Setup: seed game state with two AWN characters in combat encounter
- Action: submit one player intent through the production dispatcher
- Assertions: OTEL spans + behavior outcomes (HP delta, narration content)

---

## Story Scope & Non-Goals

### In Scope (Plan 1)
- Ruleset module binding + config validation
- Chargen strain pool wiring fix
- Six slug-string guard fixes
- OTEL span assertions + wiring tests
- No new combat math (faithful CWN port)

### Out of Scope (Plans 2+)
- Mutations (Plan 2 — bespoke MutationPlugin + tables)
- Radiation/Disease/Poisons (Plan 3)
- Stress/Addiction (Plan 4)
- Survival hexcrawl (Plan 5)
- Creatures/Nemesis traits (Plan 6)
- Enclaves/faction sim (Plan 7)

### NOT Done (out of spec)
- Content sweep (standard-six attribute names, rules.yaml binding, combat confrontation definition, ability_score_names remap) — that's Story 88-2
- Calibration test migration (dial-schema regressions) — Story 88-2 handles this
- Image/portrait assets — content plan
- `magic.yaml` reconciliation with Mutations — Plan 2 decides this

---

## Known Risks

1. **Capability form refactoring (Item 4):** Switching `seed_system_strain` from string to isinstance *should* be safe (broadens the condition), but test thoroughly to confirm no edge cases break.
2. **isinstance on ruleset_config():** The method returns `SwnConfig | None`; checking `isinstance(cfg, CwnConfig)` works because CwnConfig is a SwnConfig subclass. Make sure this relationship holds.
3. **Chargen test regression:** The smoke test must verify that AWN characters get a strain pool *and* non-AWN characters don't. A botched fix could break other rulesets.
4. **Integration test scope:** Wiring tests require a full genre pack fixture + dispatcher + narrator. Mock the narrator (use `SIDEQUEST_LLM_BACKEND=mock` if available) to keep tests fast and deterministic.

---

## Glossary & Key Terms

- **AWN:** Ashes Without Number (Sine Nomine SRD, post-apocalyptic)
- **CWN:** Cities Without Number (Sine Nomine SRD, urban fantasy)
- **SWN:** Stars Without Number (Sine Nomine SRD, science fiction)
- **WWN:** Worlds Without Number (Sine Nomine SRD, fantasy)
- **ADR-117:** Pluggable Ruleset Module System
- **ADR-114:** Ablative HP substrate (HpPool: current/max/base_max)
- **System Strain:** CWN/AWN mechanic — damage pool that depletes over time (max = CONSTITUTION score)
- **Shock:** CWN/AWN chip damage on a miss vs low AC; shields negate first
- **Trauma:** CWN/AWN damage multiplier triggered on a d6 roll
- **Mortal Injury:** CWN/AWN — 0 HP → die in 6 rounds, stabilize at difficulty 8
- **Major Injury:** CWN/AWN — 0 HP + Traumatic Hit → d12 injury table (loses body part, etc.)
- **Slug-string binding:** Rules keyed on `ruleset == "cwn"` (fragile, breaks on every new module)
- **Capability binding:** Rules keyed on `isinstance(cfg, CwnConfig)` (robust, works for subclasses)
- **OTEL spans:** OpenTelemetry trace events emitted by subsystems (game watcher, intent router, dispatch)

---

## Session Navigation

- **Session file:** `.session/88-1-session.md` — detailed spec, test plans, branch info
- **Design spec:** `docs/superpowers/specs/2026-06-05-ashes-without-number-mutant-wasteland-design.md` (READ §6, §11, §11.2, §11.4)
- **Precedent (CWN):** `docs/superpowers/specs/2026-05-28-neon-cwn-ruleset-design.md`
- **Epic repo:** `sprint/epic-88.yaml` — story 88-2 (content) depends on 88-1
- **OTEL principle:** `sidequest-server/CLAUDE.md` — "OTEL Observability Principle"
- **Wiring tests:** `sidequest-server/CLAUDE.md` — "No Source-Text Wiring Tests" (must use spans + behavior tests)
