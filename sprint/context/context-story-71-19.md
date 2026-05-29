---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-19: Author Glenross ADR-053 scenario — give the tea_and_murder flagship a solvable mystery

## Business Context

tea_and_murder IS a mystery engine, and ADR-053 (Scenario System: clue graph,
belief state, gossip propagation) is the mechanical spine that makes a mystery
*solvable by the engine* rather than improvised by the narrator. Glenross — the
flagship tea_and_murder world, and a world Jade would author — ships a rich
SETTING (archetypes, cartography, cultures, history, legends, lore, npcs,
openings, tropes) but **zero** scenario/clue/belief content. So during the
59-8 playtest (2026-05-28, finding #G6 — the headline finding), every "clue" the
doctor found was narrator confabulation: a turn-4 body exam invented a temple
wound, a Perth rail ticket, and "he was not lying so when I left him" — all
clue-shaped reveals with no mechanical provenance, non-canonical, non-reproducible.
For mechanics-first players (Jade/Sebastien) the murder is unsolvable-by-system —
the mystery equivalent of a combat pack with no confrontation engine.

This story authors the missing mystery so the flagship social pack finally has
real, solvable crunch behind its forensics — and gives the OTEL lie-detector
something true to point at.

## Technical Guardrails

**Provenance — the ENGINE is fine; the CONTENT is missing.** Confirmed during the
2026-05-28 FIXER pass. Do not "fix" this in engine code — it is an authoring job.

### What's wired vs what's missing

- **Wired (do not touch):** the router classifies investigation as `scenario_clue`;
  the handler runs; the Footnote-enum coercion is live (`scenario_clue.category_coerced
  raw='forensic' -> Lore`). The dispatch path (post the #G5 consolidation) is healthy.
- **Missing:** `snapshot.scenario_state` is `None` because Glenross ships no
  scenario file, so `consume_clue_footnotes` returns silently — no clue discovered,
  no belief update, no `SPAN_SCENARIO_ADVANCE`. `find worlds/glenross -iname
  '*scenario*' -o -iname '*clue*' -o -iname '*belief*'` → zero files.

### Where the content lives + the data model

- Author under `genre_packs/tea_and_murder/worlds/glenross/` (sidequest-content).
- The scenario must satisfy the ADR-053 schema and the server-side
  `scenario_state` / `BeliefState` / `discovered_clues` models (sidequest-server
  `game/` scenario modules). Reference an existing authored scenario in any pack
  as the schema template if one exists; otherwise ADR-053 is the spec.

### Constraints

- **Genre Truth + Diamonds and Coal:** the mystery must fit Glenross's cosy
  Edwardian Highland-village tone; clue detail scales with narrative weight.
- **No Silent Fallbacks:** authored clue nodes must wire into the graph such that
  investigation actions resolve real discoveries — a half-authored scenario that
  still no-ops is not done.
- **Engine already wired** — if a turn still no-ops with the scenario authored,
  that's a content-wiring bug in this story, not an engine gap.
- This is squarely the "Jade authors content" path (CLAUDE.md) — the authoring
  surface (world YAML, clue graph) is the user-facing deliverable.

## Scope Boundaries

**In scope:**
- A Glenross ADR-053 scenario: victim, canonical solution, suspect set (each with
  means/motive/opportunity), a discoverable clue graph, seeded NPC belief states,
  and gossip edges.
- At least one authorable-as-adversarial suspect so a social confrontation
  (cross-examine / social_duel / scandal) can instantiate against them.
- Schema validation + a playtest-verified clue discovery with mechanical
  provenance.

**Out of scope:**
- Engine changes to the scenario_clue handler / Footnote coercion / belief model
  (already working).
- Scenarios for other worlds (coyote_star also lacks one — that's a sibling, see
  Assumptions / promotion note).
- The social-confrontation *engine* (the suspect just needs to be seatable; the
  confrontation engine itself is not this story).
- Glenross setting content that already exists (NPCs, lore, cartography).

## AC Context

1. **Authored mystery:** Glenross ships a scenario with a victim, a canonical
   solution, and suspects each carrying explicit means/motive/opportunity.
2. **Clue graph resolves:** investigation actions (examine body, interrogate,
   search) resolve real `scenario_clue` discoveries — `discovered_clues` populates
   and `scenario_clue.resolved` / `SPAN_SCENARIO_ADVANCE` fires (no more silent
   no-op when `scenario_state is None`). *Edge:* an irrelevant search resolves to
   "no clue" gracefully, not an error.
3. **Belief states seeded:** suspects/witnesses carry `initial_beliefs` so
   interrogation reads have canonical knowledge behind them.
4. **Gossip edges:** information can propagate between NPCs across scenes per the
   world's social graph (ADR-053 gossip propagation).
5. **Adversarial suspect seatable:** at least one suspect is authorable as
   adversarial so a social confrontation can instantiate against them (unblocking
   the 59-8 confrontation-lane validation that #G6 also blocks).
6. **Validates + plays:** the scenario loads through the live loader and passes
   the ADR-053 schema (`pf validate`, no ERROR-level gaps); a playtest
   investigation turn produces a real clue discovery with provenance in the GM
   panel.
7. **Observability:** a `scenario_clue.resolved` / `SPAN_SCENARIO_ADVANCE` span
   fires on a clue discovery so the GM panel confirms the engine is engaged, not
   confabulating.

## Assumptions

- The ADR-053 schema and the server-side scenario models are stable and accept a
  newly authored world scenario without engine changes (the engine ran in the
  playtest — it just had no graph).
- A reference scenario exists somewhere to use as a schema template; if none does,
  authoring against ADR-053 + the model definitions is sufficient.
- This is a PATTERN, not a one-off: coyote_star also lacks an ADR-053 scenario.
  This story parks in epic 71 (playtest findings); if more investigation-worlds
  need scenarios, promote to a dedicated "ADR-053 scenario authoring" epic.
- 8 points reflects a full whodunit (victim + ~4-6 suspects with MMO + clue graph
  + belief states + gossip + canonical solution); may be sized down if the
  authored mystery is deliberately compact.
