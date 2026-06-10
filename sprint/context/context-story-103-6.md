---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-6: All 17 regions (GM lane) — places/cartography + encounter tables

## Business Context

The full corridor, Penobscot Bay to the Potomac — Keith locked **all 17 regions detailed in v1** (overriding the spec's own 7-region recommendation). The Corridor rail line is the connective spine: movement along it is fast travel ("Cut the Dull Bits"); movement off it is the adventure. Region density is what makes the Seaboard a *functioning weird world* rather than a wasteland, and it's the substrate for POI landscapes (103-9) and openings (103-8).

## Technical Guardrails

- **Files:** `worlds/seaboard_of_saints/cartography.yaml` + `encounter_tables.yaml`, following flickering_reach conventions for structure and the existing loader's expectations. (flickering_reach has no separate places.yaml — locations live in cartography; match the convention, don't invent a parallel file.)
- **The 17 regions (world spec §3, names final):** Down East, the Whalecoast, the Cape Ann Sodality, Boston Common, Salem Country, the Merrimack Mills, Providence, the Hudson Valley, the Catskills, the Adirondacks, the White Mountains, Plymouth Stone, the Sunken Bight, Outer Boroughs & Italian Bronx, Philadelphia, Baltimore, D.C. Each carries its register and its "Works." status per the spec table.
- **The Corridor** is the explicit inter-region link structure — fast-travel edges between Corridor cities; off-Corridor regions (Adirondacks, White Mountains interior, Cape Ann) connect via slower, adventure-bearing routes.
- **Region IDs** must match what 103-4's `patron_regions` and 103-7's factions reference — agree the slug list with those stories early (slugs from the spec names, snake_case, no banned suffix words).
- **Encounter tables:** genre-truth registers per region (comic-dystopia encounters at the Catskills, faerie-register on the Hudson, weather-priest hostility on Mount Washington); no mechanics that presume AWN Plans 3–6 (no radiation zones, no survival attrition tables).
- **Cliché bans (spec §11 + the "What's NOT in the Seaboard" list §3):** no glass plains, Heaps, Hum, vaults, root-gods, dust country; no Reach/Veil/Spire/Hollow/Drift/Mire/Shroud/Sanctum/Bastion coinages (Sleepy Hollow is real and stays).

## Scope Boundaries

**In scope:**
- All 17 regions with landmarks per spec §3 (real-geography anchors: the Acushnet at New Bedford, the Tip-Top House, Lovecraft's grave at Swan Point, the Cabrini shrine at Fort Tryon, Brown's Hotel, etc.)
- Corridor link structure + off-Corridor route texture
- Region-keyed encounter tables

**Out of scope:**
- POI landscape images (103-9); openings/tropes that use the regions (103-8); faction definitions (103-7 — reference faction slugs only where a landmark is faction-owned, coordinate slug list)
- Megadungeon/interior content (ADR-106 surfaces — not in this epic)

## AC Context

1. **All 17 present:** cartography.yaml contains all 17 region entries with register-bearing descriptions and at least 3 landmarks each; the spec's "Works." status is reflected in tone. Test: load + count + slug-set assertion.
2. **Corridor connectivity:** every Corridor city reachable via Corridor edges; off-Corridor regions reachable via at least one described route. Test: graph-connectivity check on the loaded structure.
3. **Encounter tables load** and key to valid region slugs; entries respect genre truth and promise no unshipped mechanics. 
4. **Slug consistency:** region slugs match those referenced by saints.yaml (103-4) — cross-file validation passes at world load.
5. **Cliché audit:** banned-term scan clean (re-verified epic-wide in 103-10).

## Assumptions

- 103-5 merged (world loads; starting location names one of these regions).
- The cartography loader handles a world of this region count without schema extension (flickering_reach is smaller; if loader limits surface, that's an engine deviation routed to Dev, not a content workaround).
- 17-region detail at ~3+ landmarks each is the right v1 grain — deep per-region adventure content beyond encounter tables is Phase 3.
