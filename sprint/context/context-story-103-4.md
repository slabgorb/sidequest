---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-4: Saint canon (GM lane) — all ~25 Saints curated to AWN mutation IDs

## Business Context

The Saint canon is the world's identity: four traditions (literary, Catholic-immigrant, folk/place, wilderness/Sleeper) of real-history-anchored patron Saints whose mutation bundles players inherit at chargen. The world spec §6 defines all ~25 with bundles and drawbacks written as *flavor names*; this story translates every one into the live AWN mutation catalog — making each Saint a working chargen preset, not prose. The reference-stack depth (Melville's actual ship, Cabrini's actual shrine, Lizzie Bourne's actual cairn) is the cliché defense Keith demanded; preserve it.

## Technical Guardrails

- **Target:** `worlds/seaboard_of_saints/saints.yaml`, conforming exactly to the 103-1 schema (frozen before this story starts). One Saint = bundle of positive IDs + exactly one negative ID drawback + optional affinity list + iconography + veneration.
- **Curation, not invention:** map each spec-§6 flavor power to the **closest existing AWN catalog entry** (`genre_packs/mutant_wasteland/mutations.yaml`, namespace `category/snake_case`). The mapping won't be literal — "whale-bone density" lands on a structure-category analog; record non-obvious mappings in YAML comments.
- **Gap analysis → additive genre PR:** where no catalog analog exists, author an **additive genre-tier mutation** (mechanics live at genre tier). This means a **coordinated two-PR delivery** (world saints.yaml → content repo; genre mutations.yaml additions → same repo but flagged as genre-tier change in review). Additive only — never modify existing catalog entries (flickering_reach Wild Mutants roll on them).
- **Cliché bans (world spec §11):** no banned coinages in any Saint name/flavor; the roster's corrected names are final (Saint Folly of the Cove NOT Innsmouth, Saint Rebecca of Nurse NOT Marie of Salem, Saint Nikola of the Hotel NOT Niagara, Saint Lizzie of the Cairn NOT Lazarus).
- **Iconography fields** feed 103-9's portrait pipeline — write them as Z-Image-usable subject descriptions per `PROMPTING_Z_IMAGE.md`; style stays OUT of them (style lives only in visual_style positive_suffix — Keith, emphatic). No default facial scars.
- **Region binding is non-deterministic** (spec §6, "mutants migrate") — patron_regions is flavor weighting, not a constraint; don't encode region locks.

## Scope Boundaries

**In scope:**
- All ~25 Saints from spec §6 (7 literary, 7 Catholic-immigrant, 7 folk/place, 4 wilderness/Sleeper) fully curated, replacing/absorbing the 3 proof Saints from 103-1
- Mutation gap analysis + additive genre-tier entries where needed
- Per-Saint iconography + veneration flavor

**Out of scope:**
- Hagiographic long-form prose for lore RAG (Phase 3, post-MVP per world spec §12)
- The Phase-3 expansion Saints (Portuguese/Polish/Cape Verdean/Marcantonio etc. — spec §14 Q4 ships the listed roster only)
- Schema changes (if the schema can't express something, that's a 103-1 deviation conversation, not a silent fork)
- stocks.yaml content (103-8)

## AC Context

1. **Completeness:** every Saint in spec §6's four tables exists in saints.yaml with all required fields; count ≈25. Test: registry load + roster assertion.
2. **All IDs resolve:** world load passes 103-1's loud validation with zero misses. Test: full world-load integration run.
3. **Drawback fidelity:** each Saint's drawback maps to a negative whose mechanical effect plausibly carries the spec's flavor (e.g. a compulsion/phobia-class negative for Saint Herman's obsessive monologue); mapping rationale commented where non-obvious.
4. **Gap entries are additive:** genre mutations.yaml diff shows only additions; existing entries byte-identical. Test: regression on flickering_reach mutation rolls.
5. **Cliché audit:** §11 banned-name scan passes over the file (also re-verified epic-wide in 103-10).

## Assumptions

- 103-1 merged (schema + validation are the contract this story writes against).
- GM-lane authoring per Keith's directive (gm background agent / world-builder), with the engine-side validation suite as the acceptance harness.
- Spec §6's bundles of 3–4 positives fit AWN MP pricing via the drawback + affinity-purchase structure; where a bundle over-budgets MP, trim to the canonical 3 and move the rest to the affinity list (log as deviation, it's a content-fidelity call).
