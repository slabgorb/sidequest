# Story Context: 100-6 — Rules page JSON projection API + firewall reuse

**Story ID:** 100-6  
**Epic:** 100  
**Title:** Phase 1 — Rules page JSON projection API + firewall reuse (/reference/api/rules/{pack})  
**Points:** 5  
**Priority:** p2  
**Workflow:** tdd  
**Type:** feature  
**Repos:** sidequest-server

## Story Description

Implement a JSON projection API endpoint `/reference/api/rules/{pack}` that:

1. Extracts the Rules section data from a genre pack
2. Applies the `reference_visibility.py` firewall to ensure keeper fields never cross the JSON boundary (matching the security pattern established in stories 100-2 through 100-5)
3. Returns a publicly-projected JSON payload

This story mirrors the projection pattern from the just-merged lore-section projections (100-2, 100-3, 100-4, 100-5). The key difference: Rules are per-pack (not per-world like the lore sections), so the endpoint is scoped to `/reference/api/rules/{pack}` not `/reference/api/rules/{pack}/{world}`.

## Key Context

- **Epic spec:** `docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md`
- **Lore projection pattern reference:** Stories 100-2 (generic-YAML section projection + classify() firewall), 100-3 (Cast), 100-4 (POI), 100-5 (Timeline)
- **Firewall pattern:** `reference_visibility.py` — keeper fields must never appear in the JSON output
- **Security constraint (C1):** No keeper field crosses the JSON boundary
- **Current reference Rules presenter:** Look for `reference_rules.py` or the rules reference route to understand the source data shape

## Acceptance Criteria

1. **API Endpoint:** `GET /reference/api/rules/{pack}` returns rules data as JSON
2. **Firewall reuse:** Rules data is projected through `reference_visibility.py` firewall (keeper-field scrubbing)
3. **Data shape:** Mirrors the live reference HTML Rules presenter (identify and match the shape)
4. **No session required:** Endpoint is public (no session/auth needed)
5. **Integration test:** Verify end-to-end against a live pack (e.g., space_opera) that the JSON projection has keeper fields removed

## Repos Affected

- **sidequest-server:** Main implementation (server/reference routes, projection logic)

## Workflow Type

**tdd** — Red/Green/Refactor cycle with unit + integration tests

## Related Stories

- **100-2:** Generic-YAML section projection + classify() firewall (reference implementation)
- **100-3:** Lore Cast section projection
- **100-4:** Lore POI section projection
- **100-5:** Lore Timeline section projection
- **100-7:** Theme tokens in projection JSON (dependent on projection infrastructure)
