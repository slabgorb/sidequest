# Story 84-7 Context

## Story Identification
- **ID:** 84-7
- **Title:** WI-5 follow-up — epithet extractor POS hardening (replace -s verb heuristic) before §A4 faction/location alias reuse
- **Epic:** 84 (ADR-118 Amendment — Unified Pertinence Scorer & Tiered Forgetting)
- **Type:** refactor
- **Points:** 3
- **Priority:** p3
- **Status:** backlog
- **Repository:** sidequest-server
- **Workflow:** tdd

## Work Summary

Harden the intent router's epithet extractor POS handling and integrate the shared NFKD-fold normalization (from Story 101-8) into reference/alias matching.

### Context for Intent Router
The intent router (`sidequest/agents/intent_router.py`) performs reference and alias matching for factions, locations, and NPCs (ADR-118 §A4). Current alias resolution risks diacritic split-brain: entities with diacritical characters (e.g., "Evropi", "Coyote Star") won't match their aliases if one side normalizes and the other doesn't.

### Load-Bearing Requirement
Story 101-8 introduced a shared NFKD-fold normalization helper (`fold_to_ascii` in `sidequest/server/slug_fold.py`) for slug derivation. This story must REUSE that exact helper in the intent router's alias/epithet matching logic — NOT implement a duplicate normalization rule.

The shared helper:
- **Location:** `sidequest/server/slug_fold.py`
- **Function:** `fold_to_ascii(text: str) -> str`
- **Behavior:** Decomposes precomposed letters via NFKD and strips combining marks. Returns folded text; callers apply lowercasing/separator handling.

## Acceptance Criteria
1. Intent-router reference/alias matching (faction/location/NPC epithet + alias resolution, ADR-118 §A4) normalizes candidate names through the shared `fold_to_ascii` helper from Story 101-8.
2. A diacritic-named entity (e.g., "Evropi") resolves its alias regardless of accent.
3. Verified by a fixture/OTEL test with a diacritic entity (no source-text grep).
4. The normalization applied in the intent router is the shared 101-8 helper, NOT a re-implemented rule.

## Architecture Notes

### Intent Router Module Structure
- **Path:** `sidequest/agents/intent_router.py`
- **Role:** Pre-narrator Haiku-via-SDK pass that decomposes player actions into a `DispatchPackage`.
- **Call Site:** `sidequest/server/intent_router_pass.py` (function `execute_intent_router_pre_narrator_pass`)
- **Related ADR:** ADR-118 §A4 (Unified Retrieval Layer — alias + epithet matching)

### Fold Helper Usage Pattern
Example from slug derivation:
```python
from sidequest.server.slug_fold import fold_to_ascii

# Apply fold, then apply caller's separator/lowercasing rules
folded = fold_to_ascii("Evropi")  # → "Evropi" (no combining marks)
folded = fold_to_ascii("Coyote Star")  # → "Coyote Star" (no change)
slugified = folded.lower().replace(" ", "_")
```

## Testing Strategy

### Test Type
Fixture/OTEL test with a diacritic entity. Do NOT use source-text grep assertions.

### Test Shape
1. Construct a synthetic genre/world state with a diacritic-named NPC/faction/location (e.g., "Faërie Realm" or "Maelstrom").
2. Build an alias that matches after folding (e.g., "Faerie Realm" or "Maelstrom").
3. Invoke the intent router's alias-matching logic through the real handler.
4. Assert that the alias resolved to the entity.
5. Optionally assert an OTEL span was emitted showing the fold applied.

## Related ADRs

- **ADR-118:** Unified Retrieval Layer — alias + epithet matching (§A4)
- **ADR-101:** Anthropic SDK as narrator backend (intent router uses SDK)
- **ADR-113:** Intent Router — mechanical-engagement spine

## Related Stories

- **84-1:** WI-1 Unified pertinence scorer + present-scene invariant (foundation)
- **84-2:** WI-5 Alias resolution + accretion-fed aliases (parent work)
- **101-8:** Slug derivation unified onto shared NFKD fold (shared helper source)

## Dependencies

- None (story 101-8's helper is already merged and available)

## Implementation Notes

- The epithet extractor's POS hardening (replacing the -s verb heuristic) is secondary.
- The primary load-bearing work is integrating the shared fold helper into alias matching.
- Keep the fold-helper import and reuse path simple and non-invasive.
- OTEL span emission recommended for observability (per CLAUDE.md OTEL Observability Principle).
