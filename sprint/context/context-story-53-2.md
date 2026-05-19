---
parent: context-epic-53.md
workflow: tdd
---

# Story 53-2: Materializer — instantiate rig vessel item → bind RigComposurePool to character

## Business Context

Road Warrior characters select a rig (vessel) at chargen — the inventory carries a `vessel`-tagged item like `rig_tier_1_prospect` whose tags encode the mechanical state (`composure:4`, `composure_max:4`, `speed:3`, `armor:0`, `mount_slots:1`). Right now the materializer ignores those tags: the rig is a *narrative* prop with no runtime presence. The narrator can describe a crash, but nothing in the game state guards the rig — no Composure to deplete, no zero-crossing to fire, no GM-panel observability. This story closes that gap by hooking the materializer to instantiate a `RigComposurePool` (built in 53-1) and bind it to the character, so subsequent stories (53-3 crash handler, 53-4 OTEL, 53-5 UI) have something concrete to react to. Per the CLAUDE.md "Gaslight the narrator with game state" doctrine, the materialized pool *is* the lie detector — without it, every Road Warrior session is improvisation.

## Technical Guardrails

### Key files

- `sidequest-server/sidequest/game/world_materialization.py` — primary edit site. The character materialization paths (`_apply_npc`, the player materialization fork — currently three `Inventory()` construction sites around lines 352, 461, 768) build `CreatureCore` instances. Add a "scan inventory for vessel items, instantiate pool, bind" step at the end of those paths.
- `sidequest-server/sidequest/game/creature_core.py` — `CreatureCore` carries `EdgePool` today; extend its data shape to carry an optional `rig_pool: RigComposurePool | None`. Do not remove or alter `EdgePool` semantics.
- `sidequest-server/sidequest/game/rig_composure_pool.py` — read only. Use `RigComposurePool(character_id=…, chassis_id=…, composure=…, composure_max=…)` exactly as defined in 53-1.
- `sidequest-server/sidequest/telemetry/spans/rig.py` — wire the `rig_pool.created` span at instantiation site (53-4 will harden the GM-panel surface; 53-2 just emits).
- `sidequest-content/genre_packs/road_warrior/inventory.yaml` — source of truth for vessel tag encoding. Do not modify; this story is server-only.

### Patterns to follow

- **Tag parsing convention:** Tags are lowercase, colon-separated `key:value` strings (`composure:4`). Parse with `str.split(":", 1)`, coerce value to `int`. Define a small helper rather than inlining the parser at the instantiation site.
- **No silent fallbacks (CLAUDE.md):** If a `vessel`-tagged item is in inventory but is missing `composure:N` or `composure_max:N` tags, raise loudly. Do not default composure to 0 or skip pool creation — that masks content bugs.
- **HP→Edge translation seam (memory `[[hp_removed]]`):** This is the materializer; if vessel items ever sprout an `hp` field in content YAML, translate it here. Today the tags are the only mechanical surface, so nothing extra is needed — just be aware the seam is the right place if it shows up later.
- **One rig per character per session:** Inventory may technically contain more than one vessel item (salvage scenarios). For 53-2, pick the *first* `vessel`-tagged item; document the choice and flag a follow-up if multi-rig becomes a real use case. Do not invent ranking logic.
- **Binding model (53-1 contract):** `character_id` = the owning character's id; `chassis_id` = the inventory item's id. Both are strings; both required.

### Integration points

- The pool must end up serialized into the session snapshot. `CreatureCore` is already in the snapshot chain — adding an optional field to it is sufficient, *but* verify that the SQLite persistence path round-trips the new field (read snapshot → save → reload → assert pool present).
- Materializer call sites are reached during character creation *and* during snapshot reload. The "vessel → pool" step must be idempotent: reloading a snapshot that already contains a serialized `rig_pool` should not double-instantiate.

### What NOT to touch

- The `RigComposurePool` class itself (53-1 territory).
- The crash event handler — Composure→0 detection lives in the pool; the *handler* that injects an injury tag + Edge hit + dismount is **53-3's** scope.
- OTEL GM-panel surface — 53-2 emits `rig_pool.created`; **53-4** adds dashboards and dataset spans.
- UI — `CharacterSheet` does not change here; **53-5** owns that.
- `scripts/render_common.slugify` — that's **53-6**, even though it's in the same epic.

## Scope Boundaries

**In scope:**
- A vessel-tag parser helper (with tests).
- Materializer scan for `vessel`-tagged inventory items at character-instantiation time (both new chargen and snapshot reload paths).
- `RigComposurePool` instantiation bound to `(character_id, chassis_id)` with composure/composure_max from tags.
- `CreatureCore.rig_pool: RigComposurePool | None` field + snapshot round-trip.
- `rig_pool.created` OTEL span emitted at instantiation.
- Wiring test: instantiate a character with a `rig_tier_1_prospect` inventory item, materialize, assert `creature_core.rig_pool` is present, bound correctly, and composure matches the tag.

**Out of scope:**
- Crash handler at Composure→0 (53-3).
- Full OTEL GM-panel surface beyond the single creation span (53-4).
- UI surface (53-5).
- Multi-rig ranking / vessel swap mid-session (deferred).
- Speed/armor/fuel/mount_slots tag parsing (composure is the only pool wired here; the rest are display/narrative data for now).
- Any change to `EdgePool` semantics.

## AC Context

### AC1 — Vessel-tag parser helper

A function (likely `parse_vessel_tags(item) -> VesselTags`) that returns a typed object with at least `composure: int` and `composure_max: int`. Edge cases:
- Item with no `vessel` tag → not a vessel; helper not called (caller pre-filters).
- Item with `vessel` tag but missing `composure:N` or `composure_max:N` → raise loudly (custom exception preferred; `ValueError` acceptable with a clear message naming the item id).
- `composure:N` present but non-integer (`composure:foo`) → raise loudly.
- `composure > composure_max` in tags → raise loudly (model already enforces, but failing early at parse time is friendlier).

Tests live in `sidequest-server/tests/game/test_world_materialization.py` (or a new `test_vessel_tags.py` if separation reads better).

### AC2 — Materializer instantiates and binds the pool

After the existing inventory build in each character-materialization path, scan inventory for vessel items, parse tags, instantiate `RigComposurePool(character_id=core.id, chassis_id=item.id, composure=tags.composure, composure_max=tags.composure_max)`, and assign to `core.rig_pool`.

Test verifies: given a character with `rig_tier_1_prospect` in inventory, after materialization `creature_core.rig_pool` is not None, `chassis_id == "rig_tier_1_prospect"`, `composure == 4`, `composure_max == 4`.

### AC3 — Snapshot round-trip

`CreatureCore` serialization includes `rig_pool` when present. Test: build a snapshot with a rig-bound character, save to SQLite (use the existing session-test helper), reload, assert pool is present and field-equal.

Idempotency: reload of a snapshot that already contains a serialized `rig_pool` does NOT re-run the vessel-tag scan (or, if it does, it produces an equivalent pool — but the simpler invariant is "if `core.rig_pool` is already populated, skip the scan").

### AC4 — OTEL `rig_pool.created` span emitted at instantiation

Span name: `rig_pool.created`. Attributes (suggested): `character_id`, `chassis_id`, `composure`, `composure_max`. Test asserts span fires once per pool instantiation (use the existing OTEL test fixture pattern in `sidequest-server/tests/telemetry/`).

### AC5 — Wiring test (mandatory per CLAUDE.md)

One integration test that exercises the production materializer path end-to-end — not a direct call to a parser helper, but a "character with inventory → materialize → assert pool present + bound + correct" test. This is the lie detector per CLAUDE.md "Every Test Suite Needs a Wiring Test".

### AC6 — No silent fallbacks

A negative test: character with `vessel`-tagged inventory item lacking `composure:N` tag → materializer raises (test asserts the exception type and that the item id appears in the message).

## Assumptions

- **CreatureCore is the right home for `rig_pool`.** It already carries `EdgePool`. If during implementation it turns out CreatureCore is the wrong layer (e.g., the snapshot uses a separate character-state container), log a Design Deviation and consult Architect before forking the design.
- **Tag format is stable.** `composure:N` / `composure_max:N` strings are how content encodes pool state. The content team has shipped Tiers 1–4 in this format. If a tier surfaces with a different encoding, fail loudly and flag content.
- **"First vessel-tagged item wins" is acceptable for now.** Content currently expects exactly one rig per character. If multi-rig becomes real, that's a separate story.
- **Snapshot persistence already handles new optional model fields.** Pydantic v2 + the existing SQLite serialization should round-trip a new `Optional[RigComposurePool]` field on `CreatureCore` without schema migration. If it doesn't, that's a Design Deviation — discuss with SM before changing the snapshot schema.
- **53-1 is correct.** This story does not re-validate 53-1's contract; it consumes it.

If any of these assumptions break, log a Design Deviation and notify SM. Wrong assumptions are the #1 source of scope creep.
