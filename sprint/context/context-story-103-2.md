---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-2: Stock system — chargen stock step + stocks.yaml + generic stock application

## Business Context

Stocks deliver the Seaboard's six character-entry paths (Saint-Marked / Wild Mutant / Sleeper / Animal / Plant / Synthetic) — the Gamma World/Qud texture Keith asked for, locked into v1 scope 2026-06-10 including the non-human stocks. Per the addendum, AWN has **no native PC-stock system**, so this is the epic's one genuinely net-new engine surface — and the addendum's constraint is absolute: build from AWN primitives (attr mods, Move, AC, Trauma Target, granted mutations), extend AWN, never contradict it. This is also the first multi-path chargen in the pack — the UI branch must not rush slow readers (Alex) and must show the mechanical consequences of a stock pick legibly (Sebastien/Jade).

## Technical Guardrails

- **One generic application path.** `stocks.yaml` defines trait sets; the engine applies `{attr_mods, move, ac, trauma_target_mod, granted_mutations: [IDs], saint_affinity_allowed}` identically for every stock. **Zero per-stock special cases in engine code** — if Synthetic needs an `if stock == "synthetic"`, the schema is wrong; fix the schema.
- **Stock → expression mapping (addendum, locked):** Saint-Marked → 103-1's preset; Wild → existing freeform MP spend; Sleeper → no mutations, implants authored as **System-Strain item sources** (same pool slot as AWN cyberware/stims — reuse `system_strain.py` hooks, no parallel implant economy); Animal/Plant/Synthetic → stocks.yaml trait sets + optionally one Saint affinity bundle.
- **Chargen:** extend the live 5-step flow (`char_creation.yaml`: origins, pronouns, mutation, artifact, confirmation) — insert a stock step that branches the `mutation` step. Prior art to extend, not replace: ADR-015 (builder state machine), ADR-016 (three-mode creation). The dead 7-step `native` overhaul from the 2026-05-14 spec is NOT the design.
- **World-tier content (ADR-140):** `stocks.yaml` at `worlds/seaboard_of_saints/stocks.yaml`. flickering_reach has no stocks file → chargen shows no stock step there (absence = single-path, current behavior preserved).
- **Mutation-ID validation:** granted_mutations validate against the genre catalog at load, same loud-failure contract as 103-1 (reuse the same validation helper — don't duplicate it).
- **OTEL (D-D):** `awn.stock.applied` span with stock id + applied trait deltas.
- **UI (`sidequest-ui`):** stock pick + branch in the chargen screens; show the mechanical deltas of the chosen stock (attr mods, granted abilities) before confirmation. Natural-language entry stays open elsewhere — this is chargen, the one sanctioned menu surface.
- **Do not touch:** AWN combat math, MpEconomy pricing, 103-1's SaintRegistry contract.

## Scope Boundaries

**In scope:**
- `stocks.yaml` schema + loader + validation; generic stock application in chargen
- Stock chargen step (server flow + UI branch); per-stock branching of the mutation step
- Sleeper implant items as System-Strain sources (the 5 spec implants: subdermal weave, cortex booster, optic suite, dermal vox, blood-filter — as content entries)
- `awn.stock.applied` span; wiring + integration tests
- **Proof stocks only:** Sleeper + one Animal stock (with trait set + saint affinity), enough to prove every branch class of the schema

**Out of scope:**
- The full stock roster — all Animal/Plant/Synthetic variants (103-8)
- Implant install/uninstall mid-game mechanics (deferred in the world spec §13; narrative-only)
- Roll the Bones (103-3); Saint canon content (103-4)
- Subsystem progression trees for Synthetics (v2 per world spec §13)

## AC Context

1. **Stock step:** Seaboard chargen presents the stock choice; flickering_reach chargen is unchanged (no stocks.yaml → no step). Test: chargen flow integration test per world.
2. **Generic application:** a stocks.yaml fixture with arbitrary trait values applies correctly to the created character (attrs, move, AC, trauma target, granted mutations on sheet). Test: property-style fixture proving the engine reads schema, not stock names.
3. **Sleeper:** picking Sleeper yields zero mutations + chosen implant as a System-Strain item source whose use costs strain through the existing pool. Test: strain delta assertion on implant use.
4. **Animal + affinity:** the proof Animal stock applies its trait set AND can layer one Saint affinity bundle via 103-1's preset path without double-pricing. Test: combined application integration test.
5. **Validation:** bad granted_mutation ID fails world load loudly (same contract/helper as 103-1). Test: bad-fixture load assertion.
6. **Span:** `awn.stock.applied` emitted with stock id + deltas. Test: span capture.
7. **UI branch:** stock selection renders, branches correctly, and displays mechanical deltas pre-confirmation. Test: UI component/flow test (vitest) per existing chargen test conventions.

## Assumptions

- 103-1 is merged first (the affinity layering and the shared validation helper depend on it).
- The chargen state machine (ADR-015) supports inserting a step without protocol changes to the WebSocket contract; if a protocol payload change is needed, it's additive and documented in `docs/api-contract.md`.
- Trauma Target / Move / AC are already settable via existing creature/character fields from CWN substrate (verified for NPCs; assumed reachable for PC chargen — if not, the hook is added generically, logged as deviation).
