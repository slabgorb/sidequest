---
---

# Epic 55: Procedural Cavern Description+Manifest Emit at Materialize Time

## Overview

The late-merging stitch between Epic 52 (megadungeon materializer + ADR-096 mask emit) and Epic 54 (typed location manifest + validator). One story, one materializer rewrite (spec §7.3 Approach C). Cookbook gains `compose_room_prose(rng, look_def, special_rooms, room_id)` that deterministically produces a `(prose, entities[])` tuple per region; `RegionContentManifest` gains `room_descriptions[]`; the materializer writes one `<world>/rooms/<region_id>.yaml` per newly-committed region after the existing mask emit + `commit_expansion`. The 54-3 validator runs as a post-materialize CI smoke check on the emitted YAMLs.

**Priority:** P1
**Repo:** server
**Stories:** 1 (5 points)

## Background

Approach C (spec §7) splits the procedural-side cavern description work out of Epic 54 so it can land **after** both upstream chains settle. Epic 52 ships its mask emit cleanly; Epic 54 ships POI + infrastructure + UI cleanly; this epic stitches them with a single materializer rewrite — no double-pass on `materializer.py`.

The cookbook already owns the corpora the composition needs:
- `LookDef.dressing: list[str]` — flavor lines that become `flavor_only` entities (provenance="cookbook").
- `SpecialRoom.telegraph` + `SpecialRoom.mechanic` — narrator hints + affordance seeds that become `real_object` entities with `binding.kind=location_feature` and an affordance derived from the mechanic id.

The deterministic seed `(campaign_seed, expansion_id, room_id)` guarantees that re-materializing the same region produces identical prose + manifest — matching the rest of the megadungeon's freeze invariant. The materializer never overwrites an existing `<world>/rooms/<id>.yaml`; a frozen region's content stays frozen on disk.

## Technical Architecture

```
materializer._stage_commit (one transaction)
  ├─ commit_expansion(expansion, graph)            ← Plan 7 existing
  ├─ record_mutation(setpiece_state)               ← Plan 7 existing
  ├─ put_frontier(new_frontier_edges)              ← Plan 7 existing
  ├─ ADR-096 mask emit (Epic 52)                   ← 52-2 / 52-3
  ├─ conn.commit()
  └─ _stage_emit_room_yamls(world_dir, composed)   ← NEW (this epic)
        for each region in expansion.new_nodes:
          if <world>/rooms/<id>.yaml exists:  skip (freeze invariant)
          else:                                write_room_yaml(...)

cookbook.assemble.assemble_region(...)
  ├─ resolve LookDef                              ← existing
  ├─ roll race + wandering + loot + specials      ← existing
  └─ compose_room_prose(                          ← NEW
       rng=Random((campaign_seed, expansion_id, room_id)),
       look_def, special_rooms, room_id
     ) → GeneratedRoomDescription → manifest.room_descriptions
```

`GeneratedRoomDescription` (new pydantic model in `cookbook/models.py`) carries `{room_id, description, entities: list[LocationEntity]}`. Every entity carries `provenance="cookbook"`. The on-disk YAML shape is the same one 54-2's `room_file_loader.load_room_payload` consumes — a top-level `description` + top-level `entities` list of `LocationEntity` model dumps. Producer/consumer share a contract.

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| `docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md` | §5.2 loader wiring (cookbook seam), §4.2 where it lives (procedural row), §7.3 Approach C rollout (this epic is the stitch). |
| `docs/superpowers/plans/2026-05-19-story-55-1-procedural-cavern-prose-and-manifest.md` | Story 55-1 plan — cookbook compose + manifest extension + materializer rewrite + validator post-check. **Authoritative implementation source.** |
| `docs/adr/README.md` | ADR-096 (cavern renderer revival) + ADR-106 (megadungeon — per-region = per-room in v1) — the substrate this epic stitches onto. ADR-109 (54-1) for the manifest contract. |

## Cross-Epic Dependencies

- **Epic 52 (52-2 / 52-3)** — materializer mask emit + persistence. This epic's room YAML write sits at the same `_stage_commit` seam, **after** the mask emit.
- **Epic 54 (54-2 / 54-3)** — `LocationEntity` types + `room_file_loader.load_room_payload` round-trip + `pf validate locations` programmatic entry for the CI smoke check.

This is the closing stitch — nothing depends on Epic 55.
