---
parent: context-epic-103.md
workflow: trivial
---

# Story 103-8: Stocks + dramatic content (GM lane) — full stock roster, Penitent, tropes/openings/archetypes/bestiary/currency

## Business Context

This story fills the world with its playable variety: the complete non-human stock roster (the Penobscot/Wampanoag-named uplift stocks, plant-folk, the Synthetic docents and brass-bots), the Penitent flavor-focus, and the dramatic machinery — tropes, campaign openings, archetypes, bestiary — that the narrator runs the world on. It's the largest content story and the one that makes the Seaboard *playable* rather than merely loadable. Keith locked all-stocks-in-v1; this is where that scope lands.

## Technical Guardrails

- **stocks.yaml roster** conforms to the 103-2 schema (frozen): every stock = trait set from AWN primitives + granted mutation IDs + saint_affinity_allowed. Spec §5 roster: Animal stocks incl. **muwin-folk** (Penobscot, bear), **kiwhosis-folk** (muskrat), **ahtuhq-folk** (Wampanoag, deer), **paquanaog-folk** (clam-people), plus lobster/harbor-seal/cardinal/mountain-lion/fox/brook-trout-folk; Plant stocks (white-pine, sugar-maple, salt-marsh-cord-grass, mountain-laurel, oak, kelp, cattail-folk); Synthetic variants (MTA conductor, Smithsonian docent, band-stand brass-bot, NYPL librarian) as trait-set variants — **no subsystem progression trees** (v2).
- **Zero engine changes:** if a stock can't be expressed in the 103-2 schema, that's a schema deviation conversation with Dev, not a content hack and not an engine PR from this story.
- **Penitent** = flavor-focus/archetype over AWN classes (addendum C5): Magisterium-aligned archetype whose miracle-narration social beats resolve through existing confrontation primitives and whose vow-drawback uses System Strain or an existing penalty hook. Content-only.
- **Tropes (`tropes.yaml`):** ADR-018/ADR-128 conventions (temporal governor, seed-trope deck compatibility). Seaboard-specific: thaw-day at the resorts, Magisterium adjudication, Mayflower sighting, Anti-Rent dispute, Lo'in pilgrimage, Saturday-Club regret-in-due-form.
- **Openings (`openings.yaml`):** per existing world conventions; spec §12 Phase-3 adventure seeds are the menu (Folly Cove town meeting, Swan Point pilgrimage, Ursuline-anniversary tension, Smithsonian artifact dispute, Catskills thaw-day, Patroon dispute) — openings reference 103-6 region slugs and 103-7 faction slugs.
- **Bestiary/creatures:** follow flickering_reach's bestiary.yaml/creatures.yaml shape. Mutant whales, Dunderberg Imp, Hudson faerie-register fauna. **Weapon-bearing entries need `damage:` specs** (hp_depletion lesson: weapons without damage specs deal 0 HP — caught in 86-1).
- **Currency:** Mint-struck coins + regional scrips (spec §8) as inventory/economy flavor in existing item surfaces; NO bottlecaps/water-currency (banned).
- **Cliché bans (§11)** + no facial-scar defaults in any appearance text.

## Scope Boundaries

**In scope:**
- Full stocks.yaml roster (all Animal/Plant/Synthetic variants), Penitent archetype, tropes.yaml, openings.yaml, archetypes.yaml, bestiary/creatures, currency flavor entries

**Out of scope:**
- Engine/schema changes (103-2 owns the schema); Saint canon (103-4); hagiographies + deep one-page adventures (Phase 3); implant install mechanics (v2); Synthetic subsystem progression (v2)

## AC Context

1. **Roster completeness:** every spec-§5 stock present and loading through the 103-2 generic path; each Animal/Plant stock's granted mutations resolve against the catalog. Test: world load + per-stock chargen smoke.
2. **Indigenous-named stocks** carry their language anchors correctly (Penobscot/Wampanoag terms per spec, regions matching 103-6 territory) — register check.
3. **Penitent:** archetype loads; vow-drawback expresses via System Strain or existing penalty hook (no new economy fields). Test: archetype application assertion.
4. **Tropes/openings load** and reference only valid region/faction slugs; openings runnable (at least one exercised end-to-end in 103-10).
5. **Bestiary:** entries load; weapon-bearing creatures have damage specs; encounter tables (103-6) can resolve them.
6. **Currency:** coin denominations + regional scrips present as items; no banned currency types anywhere.

## Assumptions

- 103-2 (schema) and 103-6 (region slugs) merged; 103-7 faction slugs available (coordinate if in flight).
- The trait-expression range of the 103-2 schema (attr/Move/AC/Trauma/granted-mutations) is sufficient for all spec-§5 stocks at v1 fidelity — fidelity is a content-budget call (addendum Q3), erring toward fewer, sharper traits.
