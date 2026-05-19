---
parent: context-epic-55.md
workflow: tdd
---

# Story 55-1: Procedural cavern description + manifest emit at materialize time

## Business Context

The **single materializer rewrite** that ties Epic 54 (typed manifest contract) to Epic 52 (megadungeon materializer + ADR-096 mask emit). The cookbook gains `compose_room_prose(rng, look_def, special_rooms, room_id)` that deterministically produces a `(prose, entities[])` tuple per region; `RegionContentManifest` gains `room_descriptions[]`; the materializer writes one `<world>/rooms/<region_id>.yaml` per newly-committed region in the same `_stage_commit` transaction, **after** the existing mask emit + `commit_expansion`. The 54-3 validator runs as a CI smoke check on the emitted YAMLs.

**Audience:** James and Sebastien (the live `beneath_sunden` campaign). Procedural rooms now carry the same manifest contract authored rooms have — narrator claims about anything below ground are governed by the same lie-detector as anything above ground. Keith-the-architect: this is the closing stitch of Approach C; one rewrite, one PR, no double-pass on `materializer.py`.

**Expected outcome:** A fresh megadungeon materialization deposits one validator-clean `<world>/rooms/<region_id>.yaml` per region alongside the ADR-096 mask sidecar. Re-materialization of a frozen region is a no-op on the YAML (freeze invariant). Every entity in those YAMLs carries `provenance="cookbook"`.

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-55-1-procedural-cavern-prose-and-manifest.md` — task-by-task TDD guide.

**Key files:**
- `sidequest-server/sidequest/game/cookbook/models.py` — `GeneratedRoomDescription` model; `RegionContentManifest.room_descriptions`.
- `sidequest-server/sidequest/game/cookbook/compose.py` (new) — `compose_room_prose(*, rng, look_def, special_rooms, room_id)` → `GeneratedRoomDescription`. Pure, deterministic. Samples 2-3 dressing lines per spec §8 ("Author 8-12 dressing lines per look minimum; assembler samples 2-3 per room").
- `sidequest-server/sidequest/game/cookbook/assemble.py` — `assemble_region` gains a required `room_id=` kwarg + per-room RNG seeded from `(campaign_seed, expansion_id, room_id)`; threads `composed` onto `manifest.room_descriptions[0]`.
- `sidequest-server/sidequest/dungeon/room_yaml_emit.py` (new) — `write_room_yaml(world_dir, room_id, description, entities, *, overwrite=False)`. Idempotent — refuses to overwrite by default.
- `sidequest-server/sidequest/dungeon/materializer.py` — new `_stage_emit_room_yamls` helper called from `_stage_commit` **after** `conn.commit()`. Existing YAMLs are skipped (freeze invariant).

**Patterns to follow:**
- All entities emitted by `compose_room_prose` carry `provenance="cookbook"` — the seam that distinguishes authored from procedurally composed content (consumed by 54-6 promotion logic + ADR-100 KnownFacts).
- Dressing lines → `flavor_only` entities with no binding.
- `SpecialRoom.telegraph` references → `real_object` entities with `binding.kind="location_feature"`, `binding.ref=special.id`, and `affordances=[special.mechanic]`.
- The YAML write runs **after** `conn.commit()` so a rolled-back expansion produces no orphan files on disk.
- "Every test suite needs a wiring test" (CLAUDE.md): an integration test asserts the helper has a non-test caller inside `_stage_commit`.

**What NOT to touch:**
- The 54-3 validator (just call it).
- Authored content for POI worlds (54-4 / 54-5 — independent).
- The resolver / overlay / OTEL / UI stack — this story emits content, downstream stories consume it unchanged.
- Multi-room-per-region — v1 is one region = one room per ADR-106; the seam is open at `room_id`, no speculation.

## Scope Boundaries

**In scope:**
- `GeneratedRoomDescription` + `RegionContentManifest.room_descriptions`.
- `compose_room_prose` pure function.
- `assemble_region` integration with required `room_id=`.
- `write_room_yaml` filesystem helper.
- `_stage_emit_room_yamls` + the single `_stage_commit` call site.
- Integration test: materialize → emit → `pf validate locations` clean.

**Out of scope:**
- Cookbook **content** authoring (thin dressing pools are author debt, not implementation bugs).
- Multi-room-per-region.
- Cookbook-driven `location.*` OTEL spans (54-8 handles the runtime-side spans; the materializer's own spans are existing Plan-7 work).
- Image generation bound to cookbook entities.
- Cross-region entities.

## AC Context

**AC-1:** `GeneratedRoomDescription` exists with fields `{room_id, description, entities: list[LocationEntity]}`, `model_config = {"extra": "forbid"}`, non-empty `room_id` required.

**AC-2:** `RegionContentManifest.room_descriptions` defaults to `[]`; existing manifest-construction sites remain valid.

**AC-3:** `compose_room_prose` is deterministic — identical `(rng, look_def, special_rooms, room_id)` inputs produce identical `(description, entities)` outputs.

**AC-4:** Dressing lines become `flavor_only` entities with `provenance="cookbook"` and no binding. Sample size is 2-3 per spec §8.

**AC-5:** Per-region `SpecialRoom`s become `real_object` entities with `binding.kind="location_feature"`, `binding.ref=special.id`, `affordances=[special.mechanic]`, `provenance="cookbook"`.

**AC-6:** `compose_room_prose` raises `ValueError` on empty dressing pool (No Silent Fallbacks — `validate_bundle` is the upstream guard, this is the runtime safety net).

**AC-7:** `assemble_region` requires `room_id=`; calls `compose_room_prose` with a per-room RNG seeded from `(campaign_seed, expansion_id, room_id)`; attaches the result to `manifest.room_descriptions[0]`.

**AC-8:** `write_room_yaml` round-trips through `room_file_loader.load_room_payload` (54-2's loader); `overwrite=False` refuses existing files with `FileExistsError`.

**AC-9:** `_stage_emit_room_yamls` runs inside `_stage_commit` **after** `conn.commit()`; writes one YAML per region in `expansion.new_nodes` that has a `RegionContentManifest.room_descriptions[0]`; skips regions whose YAML already exists (freeze invariant).

**AC-10:** Integration test: materialize a fresh expansion in a tmp world dir → at least one `<world>/rooms/<region_id>.yaml` exists per region → `validate_locations_in_world(world_dir)` returns zero hard errors.

**AC-11:** A wiring test asserts `_stage_emit_room_yamls` has a non-test caller inside `_stage_commit` (def + call = ≥2 mentions in `materializer.py`).

**AC-12:** Manual smoke (per the plan's Task 7): `just up`, start a fresh `beneath_sunden` session, materialize one expansion → inspect `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/` → each new YAML has non-empty `description` and a non-empty `entities[]` with `provenance: cookbook`. `pf validate locations caverns_and_claudes caverns_sunden` reports zero hard errors.
