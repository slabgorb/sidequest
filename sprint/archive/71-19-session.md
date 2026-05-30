---
story_id: "71-19"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-19: Author Glenross ADR-053 scenario — give the tea_and_murder flagship a solvable mystery

## Story Details
- **ID:** 71-19
- **Jira Key:** (Jira not configured; skipped)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-content (genre_packs/tea_and_murder/worlds/glenross/)
- **Points:** 8
- **Priority:** p2
- **Type:** feature

## Business Context

tea_and_murder IS a mystery engine, and ADR-053 (Scenario System: clue graph, belief state, gossip propagation) is the mechanical spine that makes a mystery *solvable by the engine* rather than improvised by the narrator. Glenross — the flagship tea_and_murder world, and a world Jade would author — ships a rich SETTING (archetypes, cartography, cultures, history, legends, lore, npcs, openings, tropes) but **zero** scenario/clue/belief content.

During the 2026-05-28 playtest (finding #G6 — the headline finding), every "clue" discovered during the doctor's body examination was narrator confabulation: a turn-4 exam invented a temple wound, a Perth rail ticket, and "he was not lying so when I left him" — all clue-shaped reveals with no mechanical provenance, non-canonical, non-reproducible. For mechanics-first players (Jade/Sebastien) the murder is unsolvable-by-system — the mystery equivalent of a combat pack with no confrontation engine. The OTEL lie-detector caught narrator improvisation where there should be engine mechanics.

## Technical Approach

**Provenance — the ENGINE is fine; the CONTENT is missing.** The router classifies investigation as `scenario_clue`; the handler runs; the Footnote-enum coercion is live (`scenario_clue.category_coerced raw='forensic' -> Lore`). The dispatch path is healthy. What's missing: `snapshot.scenario_state` is `None` because Glenross ships no scenario file.

**What will be authored:**

A Glenross ADR-053 scenario living under `genre_packs/tea_and_murder/worlds/glenross/scenarios/` (TBD scenario name). The scenario will be a complete whodunit with:

1. **Victim & Murder Setup** — A Glenross village figure who dies under suspicious circumstances, grounded in the village's social fabric (existing NPCs, relationships, history).
2. **Suspect Set** — ~4-6 suspects, each with explicit means (access, method), motive (what they had to gain), and opportunity (alibis/timeline). Each suspect is an NPC who appears in the Glenross `npcs.yaml` or is newly defined in the scenario's `npcs.yaml`.
3. **Canonical Solution** — A named suspect who committed the murder, with a rule-based justification (e.g., "Suspect X had means [poison from the manor], motive [inheritance dispute with victim's cousin], and opportunity [was alone in the study at 22:00]").
4. **Clue Graph** — A directed acyclic graph (DAG) of discoverable nodes, wired so investigation actions resolve real clue discoveries:
   - Physical clues (forensic evidence, documents, artifacts)
   - Testimonial clues (witness statements, overheard conversations)
   - Behavioral clues (observed actions, timeline contradictions)
   - Deduction clues (require prerequisites, e.g., "cross-referencing the letter with financial records")
   - Red herrings (plausible but false)
   - Discoveries are gated by prerequisites; e.g., a deduction clue requires two physical clues first.
5. **Belief States** — Suspects/witnesses carry `initial_beliefs` so interrogation reads have canonical knowledge behind them, not narrator improv. Beliefs seed the BeliefState data model (facts, suspicions, claims).
6. **Gossip Edges** — Information can propagate between NPCs so rumors spread and false beliefs form organically. These are social graph edges describing who talks to whom.
7. **At Least One Adversarial Suspect** — A suspect seatable as an adversarial Other so a social confrontation (cross-examine / social_duel / scandal) can instantiate, unblocking the 59-8 confrontation-lane validation.

**Reference Template** — The pulp_noir scenarios (`midnight_express`, `the_warehouse`) serve as schema templates. Both define:
- `scenario.yaml` (metadata, player roles, pacing, pressure events, escalation beats)
- `clue_graph.yaml` (nodes with discovery methods, visibility, locations, prerequisites, implicates)
- `npcs.yaml` (suspect/witness profiles with roles, beliefs, gossip connections)
- `assignment_matrix.yaml` (player role → NPC seating chart)
- `atmosphere_matrix.yaml` (pacing / tone tuning)

**Data Models** — The scenario must satisfy:
- `sidequest-server/sidequest/genre/models/scenario.py:Scenario` (top-level metadata)
- `sidequest-server/sidequest/genre/models/scenario.py:ClueGraph` (clue nodes, DAG structure)
- `sidequest-server/sidequest/game/scenario_state.py:ScenarioState` (runtime state: discovered_clues, tension, questioned_npcs)
- `sidequest-server/sidequest/game/belief_state.py:BeliefState` (per-NPC epistemic layer: facts, suspicions, claims)

## Acceptance Criteria

1. **Authored mystery** — Glenross ships a scenario (in `genre_packs/tea_and_murder/worlds/glenross/scenarios/<name>/`) with a victim, canonical solution, and suspect set each carrying explicit means/motive/opportunity.

2. **Clue graph resolves** — Investigation actions (examine body, interrogate, search) resolve real `scenario_clue` discoveries:
   - `discovered_clues` populates with real clue node IDs
   - `scenario_clue.resolved` / `SPAN_SCENARIO_ADVANCE` fires (OTEL visible in GM panel)
   - An irrelevant search resolves to "no clue" gracefully (no ERROR)
   - Clues gate on prerequisites; discovering clue X before clue Y is a prerequisite fails silently or errors appropriately

3. **Belief states seeded** — Suspects/witnesses carry `initial_beliefs` so interrogation reads have canonical knowledge behind them, not narrator improv. BeliefState data populates correctly at scenario load.

4. **Gossip edges defined** — NPCs have gossip connections so information can propagate across scenes per the world's social graph (ADR-053 gossip propagation reference).

5. **Adversarial suspect seatable** — At least one suspect is authorable as adversarial (has a `opponent_encounter` or equivalent field) so a social confrontation (cross-examine / social_duel / scandal) can instantiate against them.

6. **Validates & plays** — The scenario:
   - Loads through the live genre pack loader without errors
   - Passes ADR-053 schema validation (`pf validate`, no ERROR-level gaps)
   - A playtest investigation turn produces a real clue discovery with mechanical provenance (SPAN_SCENARIO_ADVANCE visible in GM panel, no silent no-op)
   - The clue discovery is reproducible across multiple turns (not narrator improv)

7. **Observability** — A `scenario_clue.resolved` / `SPAN_SCENARIO_ADVANCE` span fires on a clue discovery so the GM panel confirms the engine is engaged, not confabulating.

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-05-30

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30 | - | - |
| red | - | - | - |
| green | - | - | - |
| spec-check | - | - | - |
| verify | - | - | - |
| review | - | - | - |
| spec-reconcile | - | - | - |
| finish | - | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

- **Conflict (resolved by Operator decision):** Story prescribed world-level placement (`worlds/glenross/scenarios/`) and claimed "the engine is already wired." Reality: the loader auto-discovers scenarios ONLY at genre-pack root (`loader.py:1272` — `_load_subdirectories(path, "scenarios", ...)`), the `World` model has no scenario field, and `bind_scenario` (`scenario_bind.py:45-72`) is world-AGNOSTIC — it binds `next(iter(pack.scenarios.items()))`, the first scenario in the whole pack, regardless of world. A world-level scenario would silently never load. Operator chose: author genre-level now (playable today) + a follow-up Dev story to teach the loader world-level scenarios and make binding world-aware, then relocate. **Follow-up story to file (Operator-approved): "World-level scenario discovery + world-aware binding" (server).**
- **Gap (non-blocking):** AC#5 asks for an `opponent_encounter` "or equivalent field" on the adversarial suspect. No such field exists on `ScenarioNpc`, and `extra="forbid"` would reject one. Adversarial seating is implicit via the live confrontation engine — `social_duel` and `scandal` are real `category: social` confrontation types in tea_and_murder `rules.yaml`; the engine seats a present NPC opponent-side. Satisfied via the equivalent: each `can_be_guilty` suspect carries a rich `when_guilty.cover_story` + `breaking_evidence` triad (the substance a cross-examination breaks). A declarative opponent field would be a schema + engine change.
- **Gap (non-blocking):** The pack validator (`pf validate pack`) does NOT validate scenario schema or cross-references (dangling `requires`/`implicates`/`breaking_evidence`, suspect refs, guilty-pool completeness). Verified manually here via the live loader + `ScenarioState` engine (all clean). A scenario-validation pass in `pf validate` is a recommended follow-up so future authors (Jade) get the same guardrails automatically.
- **Improvement (non-blocking):** ADR-053's implementation-status section is stale on one point — it states `discover_clue` prerequisite enforcement is "dark," but the live code (`scenario_state.py:146-191`) DOES enforce the DAG (raises `PrerequisiteNotSatisfiedError` + emits `SPAN_SCENARIO_CLUE_PREREQUISITE_VIOLATION`). Worth updating the ADR. (Gossip + accusation engines do remain dark.)
- **Note (non-blocking, pre-existing):** `pf validate pack tea_and_murder` reports 4 ERROR-level asset-dir gaps (`assets/images/{portraits,poi}` for pack + glenross). These are R2-hosted-asset directories absent locally, pre-date this story, and are unrelated to the scenario. The scenario itself adds zero validator errors.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

- **Placement: genre-level, not world-level.** Spec said `worlds/glenross/scenarios/`; authored at `genre_packs/tea_and_murder/scenarios/the_morning_train/` instead. Why: the loader only discovers genre-level scenarios and binding is world-agnostic (see Delivery Findings Conflict). Operator-approved decision; follow-up loader story to converge on the architecturally-correct world-level home.
- **AC#5 adversarial field: not a field.** Spec asked for an `opponent_encounter`/equivalent field on the adversarial suspect; implemented via the live confrontation-engine seating path + rich `when_guilty` triad instead, because `ScenarioNpc` is `extra="forbid"` and would reject an unknown field. Equivalent outcome (a suspect is seatable as a `social_duel`/`scandal` Other), no schema break.
