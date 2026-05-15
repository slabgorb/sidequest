---
story_id: "50-17"
jira_key: ""
epic: ""
workflow: "tdd"
---

# Story 50-17: Journal: KnownFact.confidence enum promotion

## Story Details
- **ID:** 50-17
- **Jira Key:** N/A (SideQuest is personal — no Jira)
- **Workflow:** tdd
- **Points:** 1
- **Priority:** P3
- **Type:** refactor
- **Stack Parent:** none (independent refactor)

## Workflow Tracking

**Workflow:** tdd
**Phase:** dev
**Phase Started:** 2026-05-14T00:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-14T00:00:00Z | 2026-05-14T00:05:00Z | ~5min |
| dev | 2026-05-14T00:05:00Z | - | - |

## Technical Context

### Story Scope

Promote `KnownFact.confidence: str = "confirmed"` to `Literal["Certain", "Suspected", "Rumored", "Discovered"]` per ADR-100 J-4 spec. This is a type-safety refactor that aligns the server-side model with the accusation evaluator's already-typed confidence bands and the UI's Confidence enum.

### Rationale

ADR-100 "Journal Pipeline Coherence" defines four confidence levels for the journal system:
- **Certain** (weight 2.0) — direct, witnessed knowledge
- **Suspected** (weight 1.0) — uncertain, evidence-supported  
- **Rumored** (weight 0.5) — gossip, untrusted source
- **Discovered** (weight 1.5) — server-minted from a ScenarioClue footnote (ADR-100 seam B, story 50-5)

Current state:
- `KnownFact.confidence: str` with hardcoded default `"confirmed"` (line 28 of `game/character.py`)
- `EvidenceItem.confidence` already typed as `Literal["Certain", "Suspected", "Rumored", "Discovered"]` (line 104 of `game/accusation.py`)
- UI defines `Confidence = 'Certain' | 'Suspected' | 'Rumored'` (GameStateProvider.tsx:32)
- Story 50-5 writes `confidence="Discovered"` to KnownFact instances (scenario_clue_intake.py:77)

The mismatch creates silent type drift: KnownFact accepts any string, but only four values are semantically valid. OTEL confidence-weight lookup in AccusationEvaluator (accusation.py:71-76) requires exact string matches — any typo silently falls off the _CONFIDENCE_WEIGHTS dict.

### Call Sites

**Creation sites (KnownFact instances):**
- `scenario_clue_intake.py:73-81` — story 50-5, writes `confidence="Discovered"`
- Default initialization when not specified: uses `"confirmed"` (invalid; must be corrected during migration)

**Consumption sites:**
- `accusation.py:104` — EvidenceItem already typed; no change needed
- `accusation.py:71-76` — _CONFIDENCE_WEIGHTS dict lookup (will gain type safety with this change)
- `gossip_engine.py:251` — reads belief confidence (float, different field; not affected)

### Acceptance Criteria

1. **Type promotion:** `KnownFact.confidence` is `Literal["Certain", "Suspected", "Rumored", "Discovered"]`
2. **Default value:** corrected from hardcoded `"confirmed"` to a valid literal (likely `"Suspected"` as the cautious default per existing UI hardcode)
3. **Call site audit:** all existing KnownFact(...) constructor calls pass a valid literal
4. **Pydantic validation:** model enforces the literal at construction and deserialization
5. **OTEL safety:** _CONFIDENCE_WEIGHTS dict lookup can never return KeyError on a KnownFact.confidence field (type checker proves this)
6. **Test coverage:** unit test covers all four literals; integration test exercises the scenario_clue_intake path to ensure "Discovered" survives round-trip persistence

### Implementation Notes

- Use `from typing import Literal` (Python 3.8+, already in use across the codebase)
- Field definition: `confidence: Literal["Certain", "Suspected", "Rumored", "Discovered"] = "Suspected"`
- No migration needed — the default string value change is compatible with Pydantic v2 deserialization; old "confirmed" values are explicitly caught by the literal validator
- No schema change — SQLite stores confidence as TEXT, accepts any string; Pydantic validator gates it at model load time
- Verify story 50-5's scenario_clue_intake path still works post-refactor (that PR already landed with hardcoded `confidence="Discovered"`, so the integration test there validates the literal works)

## Implementation Summary

### Changes Made

1. **Type promotion in KnownFact** (`sidequest/game/character.py`):
   - Added `from typing import Literal` import
   - Changed `confidence: str = "confirmed"` to `confidence: Literal["Certain", "Suspected", "Rumored", "Discovered"] = "Suspected"`
   - Updated docstring to document the four confidence tiers and their weights

2. **Test suite updates**:
   - Added four new unit tests in `tests/game/test_character.py`:
     - `test_known_fact_confidence_default()` — verifies default is "Suspected"
     - `test_known_fact_confidence_all_literals()` — exercises all four literal values
     - `test_known_fact_confidence_invalid_rejected()` — validates Pydantic rejection of invalid values
     - `test_known_fact_confidence_roundtrip()` — confirms JSON serialization survives the type change
   - Fixed test fixtures in `tests/handlers/test_journal_request_handler.py`:
     - `_three_facts()` fixture updated from lowercase ("confirmed", "suspected", "rumored") to capitalized literals ("Certain", "Suspected", "Rumored")
     - `test_player_only_sees_own_journal_not_peers()` inline facts updated to "Certain"
   - Fixed test fixture in `tests/server/test_scenario_accusation_intake.py`:
     - Changed "confirmed" to "Certain" in known_facts

### Test Results

- All 68 related tests pass (accusation, journal, character, scenario clue intake)
- pyright type checking: 0 errors
- No silent regressions in broader test suite

### Verification

- Pydantic model now enforces literal values at construction and deserialization
- Type checker (pyright) confirms no type drift at call sites
- Story 50-5's scenario_clue_intake path (which writes `confidence="Discovered"`) verified to work with new type
- Default changed from invalid "confirmed" to valid "Suspected" (matches existing UI hardcode)

## Delivery Findings

No upstream findings.

## Design Deviations

No deviations from ADR-100 J-4 spec.
