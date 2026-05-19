# World-Grounding Schemas

Schemas for Epic 24 (Procedural World-Grounding Systems). These describe the
shape of YAML files that future stories will author and consume. **Nothing
imports these schemas yet** — they are documentation + future-validation
contracts. See [Epic 24 PRD](../../prd/prd-procedural-world-grounding.md).

## Decision of Record: JSON Schema, not pydantic

Story 24-1 AC-3 required picking **one** seam for schemas. We picked
[JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) over
pydantic models for three reasons:

1. **Scope.** Story 24-1's repos are `sidequest-content` + `orchestrator`.
   Pydantic models live in `sidequest-server`. Authoring them there would
   pull the story out of its declared scope.
2. **AC-6 (no consumers yet).** The moment pydantic models exist in
   `sidequest-server/sidequest/genre/models/`, the pack loader can import
   them — producing observable behavior change from a "chore" story.
   JSON Schema files are inert by construction; nothing parses them
   unless explicitly told to.
3. **Validator alignment.** The `pf validate` family already validates
   YAML against JSON Schemas elsewhere in the project (`pf validate
   locations` shipped under story 54-3). A future `pf validate
   world-grounding` follows the established pattern with zero new
   infrastructure.

When 24-5 (Python weather generator) lands, it will mint pydantic models
*from* these JSON Schemas (or hand-author them in mirror). The schemas
remain authoritative; pydantic mirrors them at the runtime seam.

## Inventory

| Schema | File | Level | PRD §  | Story consumer |
|--------|------|-------|--------|----------------|
| Weather | `weather.schema.json` | pack | 1.1 | 24-2 (glenross rules), 24-5 (generator) |
| Demographics | `demographics.schema.json` | world | 1.2 | 24-3 (glenross profiles) |
| Calendar | `calendar.schema.json` | world | 2.3 | 24-4 (glenross calendar) |
| Economy | `economy.schema.json` | world | 2.1 | Phase 2 epic |
| Establishment templates | `establishment_templates.schema.json` | pack | 2.2 | Phase 2 epic |
| Quest shapes | `quest_shapes.schema.json` | pack | 3.1 | Phase 3 epic |
| NPC schedule (archetype extension) | `npc_schedule.schema.json` | pack (embedded in `archetypes.yaml`) | 1.3 | Phase 2 epic |

## File placement convention

| Level | Path on disk |
|-------|--------------|
| pack | `sidequest-content/genre_packs/<pack>/<file>.yaml` |
| world | `sidequest-content/genre_packs/<pack>/worlds/<world>/<file>.yaml` |

ADR-072 (system/milieu split) is **retired** — schemas live alongside
existing top-level pack files (next to `pack.yaml`, `cultures.yaml`), not
under any `system/` subdirectory.

The NPC schedule schema (`npc_schedule.schema.json`) is an **embedded
fragment** — it describes the `schedule_template:` field that future
authoring will add to records inside the existing `archetypes.yaml`. No
new top-level file is introduced for NPC schedules.

## Conventions

- All schemas use `$schema: "https://json-schema.org/draft/2020-12/schema"`.
- Every property carries a `description` field; the prose is what humans
  read when authoring YAML.
- Required vs optional is split with the JSON Schema `required` array.
- An `examples` array provides at least one copy-paste-ready instance
  per schema (AC-4).
- Open enums (e.g. weather `condition`) are typed as `string` with the
  primary palette in `description`. Closed enums use `enum`. The rule
  of thumb: closed when the narrator prompt zone needs a finite set;
  open when narrative flavor varies by genre.

## What this story explicitly does NOT do

- Author actual YAML content in any genre pack (24-2/3/4 own that).
- Wire any code to consume these schemas (24-5/6/7 own that).
- Define schemas for interior topology or world maps — those are tier-3
  and intentionally excluded from this story's title.
- Migrate `SceneSetting.weather: str` to a typed shape — that lives in
  `sidequest-server/sidequest/genre/models/scenario.py:132` and stays
  free-form until 24-5/6 wires the typed pipeline.
