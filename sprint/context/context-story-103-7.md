---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-7: Cultures + factions (GM lane) — 15 cultures w/ corpus bindings + faction roster

## Business Context

Cultures drive naming (ADR-091 Markov generation) and social texture; factions drive the Living World — the Magisterium adjudicating inter-Saint disputes, the Saturday Club's courteous devastation, the Patroon Houses' faerie feudalism. The world spec's faction politics are doctrinal, not just territorial, which is what makes social confrontations first-class here. This story also plants the **Cryptic-Alliance faction tags** — the chargen faction-tie pick (opening NPC reactions + a starting-equipment slot) that becomes AWN Plan 7's Enclave retrofit hook.

## Technical Guardrails

- **Cultures:** the 15 from the world spec file plan (Brahmin/Saturday-Club, Federal-Hill-Italian, Down-East-Maine, Hudson-Valley-Patroon, Spanish-Harlem-Nuyorican, Bensonhurst-Italian, Arthur-Avenue-Bronx-Italian, Inwood-Dominican, Brookland-DC-Catholic, French-Canadian-Lowell, Mashpee-Aquinnah-Wampanoag, Penobscot-Down-East, Cape-Ann-Sodality, Sleeper, Lo'in). Follow flickering_reach's `cultures/` directory convention (per-culture YAML files).
- **ADR-091 corpus bindings:** every culture binds to corpus word lists (`sidequest-content/corpus/`). Existing corpora cover many source languages; cultures needing new corpora (e.g. Penobscot, Wampanoag, Joual-French-Canadian) get **new corpus files** — that's conlang-lane work (curate real-language word lists per ADR-091 conventions); names must feel phonetically right per culture.
- **Indigenous registers:** Mashpee-Aquinnah and Penobscot are real, extant sovereign polities in-world (spec §7 minor factions) — the spec's own framing ("not a flattening detail") is the bar; corpus sources from the actual languages, handled with the same reference-stack care as the Catholic material.
- **Factions:** 6 majors (Magisterium, Sisters of the Whitman Circle, Lo'in, Sleepers' Sodality, Saturday Club, Patroon Houses) + the ~10 regional minors (spec §7 list, renamed entries final: Atwells Avenue Society, Mashpee-Aquinnah Council, Red Hook Stevedores, etc.). Follow flickering_reach's faction file conventions; faction slugs coordinate with 103-6 region slugs.
- **Cryptic-Alliance tags:** each faction marked joinable-at-chargen or not, with opening-disposition and starting-equipment-slot hooks expressed in **existing content surfaces** (disposition system ADR-020, inventory) — no new engine. Flag in comments: `# AWN Plan 7 Enclave retrofit hook`.
- **No Enclave sim:** no settlement stats, no faction-turn mechanics — that's Plan 7. Factions here are narrative + disposition + retrieval (ADR-118) entities.

## Scope Boundaries

**In scope:**
- 15 culture files with corpus bindings (+ new corpus files where no source exists)
- 6 major + regional minor factions; Cryptic-Alliance chargen tags; doctrine-level inter-faction tensions (Ursuline wound, spectral-evidence doctrine, Anti-Rent precedent) as faction-relation content

**Out of scope:**
- Plan 7 Enclave mechanics; named-NPC rosters beyond faction leadership seeds (Diamonds and Coal — leaders are diamonds, the rest emerge in play); legends/ deep prose (103-8 carries tropes/openings; long-form legends can ride either or Phase 3)

## AC Context

1. **15 cultures load** with valid corpus bindings; namegen produces phonetically-distinct output per culture (the conlang smoke test: generate N names per culture, eyeball-distinct, no cross-culture bleed). Test: corpus binding validation + namegen run.
2. **Faction roster loads:** all majors + minors with relations expressing the spec's doctrinal tensions; retrievable via ADR-118 (faction index entries exist).
3. **Cryptic-Alliance tags:** joinable factions expose chargen tie hooks (disposition + equipment slot) consumable by the existing chargen; Unaligned is a valid choice. Test: chargen-with-faction-tie integration.
4. **Slug consistency** with 103-6 regions and 103-4 patron_regions at world load.
5. **Register fidelity:** Tituba's specifically-Barbadian creole framing (NOT "voodoo"), Baltimore-musical not Delta-gospel, founder-effect genetics not Innsmouth — the §11 coarse-granularity bans hold in culture/faction prose.

## Assumptions

- 103-5 merged. Corpus additions are additive files in the content repo (conlang lane), no server changes.
- The disposition + inventory surfaces suffice for faction-tie effects (if a hook is missing, engine deviation → Dev, scoped tiny).
