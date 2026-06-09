# Story 88-3: WN capability-gate consolidation sweep

**Epic:** 88 (Ashes Without Number — mutant_wasteland ruleset port)
**Type:** Refactor
**Points:** 2
**Workflow:** tdd
**Repos:** sidequest-server
**Depends on:** 88-2 (completed)

## Acceptance Criteria

### AC1: Docstrings updated for CWN-family capability gates

Update docstrings in three files to reflect that the capability gates cover CWN/AWN (not just CWN):

1. **stabilize_mortal_injury.py** (lines 1-6, 23-25)
   - Summary: clarify "CWN-family ruleset (cwn/awn)" instead of "CWN Mortal Injury"
   - Line 23 guard description: update to "the tool requires a CWN-family ruleset — `cwn` or its `awn` subclass" (matching existing line 105-107 in code)

2. **adjust_system_strain.py** (lines 1-5, 15-18)
   - Summary: clarify "CWN-family ruleset (cwn/awn)" instead of "CWN character"
   - Line 15 guard description: update to "the tool requires a CWN-family ruleset — `cwn` or its `awn` subclass" (matching existing line 91-95 in code)

3. **downed_seam.py** (lines 1-2, 15-16)
   - Header: clarify "Shared CWN/WWN/AWN 0-HP downed seam" (or "CwnConfig/WwnConfig…")
   - Line 15-16: update module docstring to clarify the gate covers cwn, awn, AND wwn (all CwnConfig/WwnConfig subclasses)
   - Line 133-136 comment already correctly describes the capability gate; docstring should match

### AC2: RED tests prove AWN confrontations fire the capability gates

Add test coverage proving the seams activate for AWN (not just CWN/WWN):

1. **Test: AWN Mortal Injury declaration on 0 HP**
   - Use mutant_wasteland pack (awn binding)
   - Create AWN confrontation fixture with a downed actor
   - Assert `cwn.mortal_injury.declared` OTEL span fires (via `ruleset.resolve_downed`)
   - Verify Mortal Injury Status appears on the 0-HP character

2. **Test: AWN System Strain pool seeded at chargen**
   - Create AWN character (e.g. via CharacterBuilder)
   - Assert `system_strain` pool exists on the character core
   - Verify `max` is set to CONSTITUTION-flavor stat (Body for AWN)

3. **Test: AWN System Strain adjustment via narrator tool**
   - Create AWN character with active strain pool
   - Call `adjust_system_strain` tool (narrator-driven)
   - Assert strain pool deltas correctly (temporary/permanent/rest kinds)
   - Verify `tool.write.adjust_system_strain` OTEL span fires with correct attributes

4. **Test: AWN Mortal Injury stabilization via narrator tool**
   - Create AWN character with active Mortal Injury Status
   - Call `stabilize_mortal_injury` tool with successful Heal check
   - Assert Mortal Injury clears and Frail Wound appears
   - Verify `tool.write.stabilize_mortal_injury` OTEL span fires

**Wiring verification:** Every test must confirm the path runs end-to-end (dispatcher/narrator calls the seam, OTEL span is emitted, game state changes). Use existing test patterns from WWN/CWN variants as templates.

### AC3: No regressions on existing CWN/WWN/native tests

Existing unit + integration tests for CWN/WWN/native rulesets must pass. No slug-string logic was changed (only docstrings and new AWN tests added), so this is a smoke test.

## Technical Notes

### Files to modify (docstrings only)
- `/sidequest/agents/tools/stabilize_mortal_injury.py`
- `/sidequest/agents/tools/adjust_system_strain.py`
- `/sidequest/server/dispatch/downed_seam.py`

### Files with correct code (no changes needed)
- `/sidequest/game/builder.py` — `seed_system_strain` already uses `isinstance(cfg, CwnConfig)`
- `/sidequest/server/dispatch/downed_seam.py` — already uses `isinstance(..., (CwnConfig, WwnConfig))`
- `/sidequest/agents/tools/stabilize_mortal_injury.py` — already uses `isinstance(module, CwnRulesetModule)`
- `/sidequest/agents/tools/adjust_system_strain.py` — already uses `isinstance(module, CwnRulesetModule)`

All capability gates are live and correct. The docstrings lag the implementation.

### Guardrail: Do NOT convert slug-string gates for genuinely slug-specific behavior
The hacking ladder gates (`dice.py:344`, `confrontation.py:336`) use `rules.ruleset == "cwn"` because hacking is CWN-only. These are correct and should not be converted. Slug strings are correct for:
1. Registry lookup (`get_ruleset_module(pack.rules.ruleset)`)
2. Genuinely slug-specific behavior (e.g. hacking ladder)

Family-wide gates (System Strain, Mortal Injury, Shock) use capability checks and are already converted.

## Test Plan
- [ ] Update three docstrings to clarify CWN-family (cwn/awn) vs slug-specific behavior
- [ ] Add RED test: AWN Mortal Injury declaration (assert OTEL span fires)
- [ ] Add RED test: AWN System Strain chargen seeding
- [ ] Add RED test: AWN System Strain adjustment via tool
- [ ] Add RED test: AWN Mortal Injury stabilization via tool
- [ ] Verify all tests pass (local + CI)
- [ ] Confirm no regressions in CWN/WWN/native variants
- [ ] Code review: docstrings match capability-gate implementation

## References
- ADR-117, §Amendments (2026-06-05)
- Story 88-1 review findings (stale docstrings, code correct)
- mutant_wasteland pack (awn binding)
