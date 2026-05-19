---
parent: context-epic-24.md
workflow: trivial
---

# Story 24-1: Define YAML schemas for weather, demographics, calendar, economy, establishments, quest shapes, NPC schedules

## Business Context

Epic 24 is the narrator's anti-mode-collapse infrastructure: typed, procedural
world-state that the narrator **curates** instead of **invents**. Before any
generator code exists, the schemas must. Without a stable schema, downstream
work fans out into incompatible YAML dialects per pack and the narrator
prompt-zone wiring has nothing to validate against.

This story is the gate for the entire epic. It does not ship player-visible
behavior. It produces the contract every subsequent story (24-2 .. 24-8)
fulfills: 24-2/3/4 author `tea_and_murder/glenross` content **against these
schemas**; 24-5 writes a Python weather generator that **emits values matching
this schema**; 24-6 injects schema-shaped state into the narrator prompt;
24-7 emits OTEL spans whose payload **fields are these schema fields**.

The PRD is `docs/prd/prd-procedural-world-grounding.md`. The seven schemas
have illustrative examples scattered through PRD §1.1 .. §3.1; this story
consolidates them into formal definitions and decides the open questions
the PRD left implicit (validation strategy, required vs optional fields,
file location convention, pack-level vs world-level placement).

## Technical Guardrails

**Single source of truth for content:** all schema-shaped YAML lives under
`sidequest-content/genre_packs/<pack>/` (pack-level rules) or
`.../worlds/<world>/` (world-level instance data). Per the epic description,
ADR-072 (system/milieu split) is retired — **do NOT introduce a `system/`
folder**. Schemas describe files that sit alongside existing top-level pack
files (e.g. next to `pack.yaml`, `cultures.yaml`).

**Pack vs world placement** (from PRD):

| File | Level | Rationale |
|------|-------|-----------|
| `weather.yaml` | pack | climate rules, not climate state |
| `demographics.yaml` | world | settlement-specific |
| `calendar.yaml` | world | month/day/festival names are setting-specific |
| `economy.yaml` | world | trade routes are world geography |
| `establishment_templates.yaml` | pack | shape templates; named establishments stay in existing world files |
| `quest_shapes.yaml` | pack | genre-typed narrative arcs |
| `npc_schedules` | pack | embedded inside existing `archetypes.yaml` per PRD §1.3, NOT a new top-level file |

**Validation seam:** the orchestrator already ships `pf validate locations`
(54-3, just merged). This story should land schemas in a form `pf validate`
can consume — either JSON Schema files under `docs/schemas/` or
`sidequest-content/schemas/`, or pydantic models under
`sidequest-server/sidequest/genre/` if the validator path runs server-side.
Pick **one** location and document it in the schema files' headers; do not
scatter.

**Existing patterns to follow:**
- `sidequest-content/genre_packs/<pack>/pack.yaml` — top-level frontmatter
  + sectioned body
- `sidequest-content/genre_packs/<pack>/cultures.yaml` — list-of-records
  with id/name keys; same shape works for `establishment_templates`
- `sidequest-server/sidequest/genre/models/` — pydantic models for loaded
  pack content (the canonical typed surface)
- ADR-059 (Monster Manual) — pattern reference for "YAML → typed state →
  prompt zone injection"

**Do NOT touch in this story:**
- Generator code (24-5 owns weather generator)
- Prompt zone wiring (24-6 owns it)
- OTEL spans (24-7 owns it)
- Actual world content (24-2/3/4 own glenross authoring)
- Existing `archetypes.yaml` files — only extend the **schema** to permit a
  `schedule:` field; authoring values is downstream

## Scope Boundaries

**In scope:**
- Formal schema definitions for the seven listed systems:
  1. weather
  2. demographics
  3. calendar
  4. economy
  5. establishments
  6. quest shapes
  7. NPC schedules
- One decision-of-record on where schemas live and how they are validated
  (JSON Schema vs pydantic; client-side vs server-side validator)
- A minimal example file per schema (commented stub or a single
  `_example.yaml` per schema) so 24-2/3/4 authors can copy-paste-edit
- A short header comment in each schema file pointing to the PRD section
  that motivates it and to ADR-059 for the broader pattern

**Out of scope:**
- Interior topology + world maps schemas (tier-3, deferred — they are
  intentionally NOT in this story's title)
- Authoring actual `tea_and_murder/glenross` content (that is 24-2/3/4)
- Any Python generator code (24-5)
- Prompt-zone injection (24-6)
- OTEL emission (24-7)
- Schema rollout to other genre packs beyond `tea_and_murder` (later epics)
- Migrating existing free-form `SceneSetting.weather: str` to the typed
  representation — the field stays free-form until 24-5/6 lands

## AC Context

The story landed in the sprint with empty `acceptance_criteria: []`. Expand to:

**AC-1: Schemas exist for all seven systems.**
Seven schema artifacts (file count may collapse — e.g. all under one
`docs/schemas/world_grounding.md` is fine) cover weather, demographics,
calendar, economy, establishments, quest shapes, NPC schedules. Each names
the file the schema applies to, its placement level (pack vs world), and
the required top-level keys.

**AC-2: Required vs optional fields are explicit.**
For every schema, fields are split into REQUIRED and OPTIONAL. No field is
left ambiguous. Where the PRD example is open-ended (e.g. `weather.special_events`
as a free-form list), state explicitly that the field is OPTIONAL and an
open enum.

**AC-3: One validation location is chosen and documented.**
The schemas either ship as JSON Schema files (consumable by `pf validate`)
or as pydantic models (consumable by `sidequest-server` at pack-load time).
The choice is stated once, in a header in the first schema file, with a
one-paragraph rationale. **No schema lives in two places** — pick one seam.

**AC-4: One copy-paste-able example per schema.**
A reader of 24-2/3/4 can open the schema for `weather` and find a minimal,
valid example block (inline in a comment OR a separate `_example.yaml`).
Same for the other six.

**AC-5: NPC schedules are schema-extended into `archetypes.yaml`.**
Per PRD §1.3, NPC schedules live as a `schedule:` field on archetype
records — not a new top-level YAML file. The schema-of-record for
`archetypes.yaml` is extended to permit and describe the `schedule:` field.
If `archetypes.yaml` has no formal schema today, the extension lands
alongside the new schemas under whatever location AC-3 picks.

**AC-6: No code paths consume the schemas yet.**
This is a chore, not a feature. After this story, running the server, the
client, or the validator should produce **the same observable behavior** as
before. Schemas are documentation + future-validation contracts; nothing
imports them yet. (24-5/6/7 wire them in.)

**AC-7: PRD cross-references in headers.**
Every schema file's header points to the PRD section that justifies it
(`docs/prd/prd-procedural-world-grounding.md` §1.1 for weather, §1.2 for
demographics, etc.) so an implementer in 24-5 or 24-6 finds the design
intent in one hop.

## Assumptions

- **No existing schemas to retrofit.** None of the seven target files
  (`weather.yaml`, `demographics.yaml`, …) currently exist in any genre
  pack. Confirmed by `ls sidequest-content/genre_packs/tea_and_murder/` at
  setup time. If a stale draft is discovered mid-implementation, flag it as
  a Design Deviation.
- **Validator seam stays open.** The orchestrator's `pf validate` family
  (just expanded by 54-3 for locations) is the natural home for a future
  `pf validate world-grounding` command. This story does NOT have to ship
  the validator — only the schema in a form that command can later read.
- **Pydantic-leaning if undecided.** The server already loads packs through
  pydantic models in `sidequest-server/sidequest/genre/models/`. If AC-3
  has no strong tiebreaker, prefer pydantic models there over JSON Schema
  files, because it gives server-side type safety at zero extra cost. JSON
  Schema is only better if `pf validate` is expected to run without the
  server runtime — confirm during dev which constraint dominates.
- **PRD is authoritative for field intent**, but its illustrative YAML
  blocks may be lossy (e.g. PRD weather example shows `season:` as a key
  but doesn't specify enum vs free-form). When the PRD is ambiguous,
  prefer **constrained / typed** over **free-form** to keep the narrator
  prompt zone stable. Document each such choice in the schema header so
  future stories know why.
- **Tea_and_murder/glenross is the proof-of-concept world** for Phase 1
  (per current-sprint.yaml epic 24 description). The schemas are written
  with that pack in mind, NOT the stale `low_fantasy/pinwheel_coast` plan
  in the epic context document. If a schema decision would block
  `tea_and_murder` content authoring (24-2/3/4), revise the schema, not
  the content — content authoring is downstream and adapts.
