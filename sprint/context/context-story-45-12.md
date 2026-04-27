---
parent: sprint/epic-45.yaml
workflow: tdd
---

# Story 45-12: Chargen double-init dedup of starting kit

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session — Blutka):** the
starting kit shipped 24 items where the catalogue specifies 13. The 24
breaks down as: 11 items in stub form (`"Starting equipment (slot): X"`
descriptions, `category: weapon`, `value: 10`) followed by 13 items in
canonical catalogue form (rich descriptions, real categories, real
values). Across the 24 items: 6 torches, 4 rations, 2 waterskins, 2
chalk, 2 ten-foot poles. Both batches were appended to
`character.core.inventory.items` without dedup — once by the
`CharacterBuilder` (`builder.py:1383–1423`) emitting stub-form items
from `equipment_tables`, and again by the
`apply_starting_loadout()` post-build wiring
(`server/dispatch/chargen_loadout.py:119`) emitting catalogue-form
items from `pack.inventory.starting_equipment`.

This is the **canonical write-back-symmetry** failure of the epic
(see Epic 45 themes §4): two extractors, both legitimately wired,
both writing to the same applier, neither aware of the other. The bug
isn't that one of them is wrong — they're each correct in isolation.
The bug is that they overlap and the applier's append path has no
identity check.

For Sebastien (mechanical-first, watches the GM panel), 24 items
where 13 belong is a bookkeeping divergence visible at a glance — but
the GM panel today shows 24 items because that's what's in the
snapshot, with no flag that two extractors fired. For James
(narrative-first), the surfaced symptom is encumbrance disagreement
and inventory clutter. For Alex (slow-reader), it's a wall of items
to process when picking gear. ADR-014 (Diamonds and Coal) frames
this directly: each item batch is diamond, but both batches together
contain coal-formatted duplicates of true diamond catalogue entries.

ADR-085 (port-drift) applies: this is the symptom listed in
`docs/plans/phase-2-chargen-port.md` IOU — the chargen-port plan
explicitly noted the equipment-tables/starting-equipment overlap as a
known tension and deferred resolution.

## Technical Guardrails

### Outermost reachable seam

The seam is **`apply_starting_loadout()`** at
`sidequest/server/dispatch/chargen_loadout.py:119–184`, called from
`session_handler.py:2631`. By the time `apply_starting_loadout()`
runs, the builder has already populated
`character.core.inventory.items` with stub-form entries (lines
1366–1382 builder hint path AND 1407–1422 equipment-tables path).
`apply_starting_loadout()` then both:

- Calls `_upgrade_hint_items_from_catalog()` at
  `chargen_loadout.py:158` — which **does** upgrade builder-hint dicts
  in-place (preserving slot index) when the id is in the catalog.
- Then **appends** the full `starting_equipment[class]` list at
  `chargen_loadout.py:163–169` — without checking whether
  `_upgrade_hint_items_from_catalog` already covered any of those ids.

The double-init is exactly that: the upgrade path covers the
builder-hint subset, then the append path adds the
`starting_equipment[class]` superset, and the overlap (any id present
in both `equipment_tables` rolls AND
`starting_equipment[class]`) ships twice.

The TDD test must exercise the production seam — a stub class with a
known overlap (e.g., `"torch"` in both `equipment_tables.tables`
under some slot AND in `starting_equipment["Adventurer"]`), drive
`apply_starting_loadout()`, assert the post-state list deduplicates
to 13 (or whatever the spec count is). A unit test on a
`dedup_inventory()` helper alone fails the wire bar.

### Two-extractor problem (THIS IS THE BUG SURFACE)

Both extractors are legitimate; the canonical pattern picks one and
makes the other defer. The cleanest options:

1. **Identity-aware append.** `apply_starting_loadout()` builds a set
   of ids already present in `character.core.inventory.items` (after
   the upgrade pass). For each id in `starting_equipment[class]`,
   skip if id already present. Trade-off: relies on stable ids; the
   builder produces ids via `hint.lower().replace(" ", "_")`
   (`builder.py:1364`), which may or may not match catalog ids. Add
   a name-fallback (case-insensitive name match) for safety.
2. **Single-source-of-truth.** Designate
   `starting_equipment[class]` as authoritative; the builder no
   longer emits items at all (only `item_hints` as data — the apply
   pass resolves them). This is the larger refactor and a wire-first
   story; not this story's scope.

This story takes option 1 (identity-aware append) per the story title
("Dedup on append, OR prevent the double-init"). The follow-up
larger refactor is filed against the chargen-port IOU separately.

### Dedup logic

```python
existing_ids = {
    str(it.get("id", "")).strip().lower()
    for it in character.core.inventory.items
    if it.get("id")
}
existing_names = {
    str(it.get("name", "")).strip().lower()
    for it in character.core.inventory.items
    if it.get("name")
}

skipped: list[str] = []
for item_id in equipment_ids:
    catalog_item = catalog_by_id.get(item_id)
    if catalog_item is not None:
        candidate = _item_dict_from_catalog(catalog_item)
    else:
        candidate = _item_dict_minimal(item_id)
    cand_id = str(candidate["id"]).strip().lower()
    cand_name = str(candidate["name"]).strip().lower()
    if cand_id in existing_ids or cand_name in existing_names:
        skipped.append(cand_id or cand_name)
        continue
    character.core.inventory.items.append(candidate)
    existing_ids.add(cand_id)
    existing_names.add(cand_name)
    items_added += 1
```

The skipped list feeds the OTEL span (below) so the GM panel can
**see the dedup fire** — without that, "no duplicates" is
indistinguishable from "no overlap existed."

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md)

Define in `sidequest/telemetry/spans.py` and register routes. Existing
chargen spans live around `spans.py:239–242` (`SPAN_CHARGEN_STAT_ROLL`
etc.) — sibling-shape:

| Span | Attributes | Site |
|------|------------|------|
| `chargen.starting_kit_dedup_evaluated` | `class_name`, `pre_dedup_count` (items list length entering loadout), `equipment_ids_count`, `skipped_count`, `items_added`, `items_upgraded`, `final_count`, `genre`, `world`, `player_id` | every call to `apply_starting_loadout()` |
| `chargen.starting_kit_dedup_fired` | same + `skipped_ids` (list) | only when `skipped_count > 0` |

`chargen.starting_kit_dedup_evaluated` MUST fire on every
chargen-confirm path, including ones where no overlap exists.
Sebastien's lie-detector requires the negative confirmation that the
dedup pass ran cleanly.

### Reuse, don't reinvent

- `_item_dict_from_catalog()` at `chargen_loadout.py:40–60` and
  `_item_dict_minimal()` at lines 93–116 stay as the canonical
  shapes. Dedup wraps the append, doesn't replace the dict-build.
- `_upgrade_hint_items_from_catalog()` at lines 63–90 is the
  precedent for **mutating-existing-items in place**; the dedup
  treats those upgraded dicts as the "already present" set.
- The 45-9 sibling story (`total_beats_fired` increment + OTEL) lands
  the same shape of "always-fire-on-success-path" span. Coordinate
  with that story's PR if both are open simultaneously — both are
  Lane B "extractor fires but applier doesn't observe" cases.

### Test fixtures

- `session_handler_factory()` at
  `sidequest-server/tests/server/conftest.py:332` — for the wire-test.
- `_FakeClaudeClient` at `conftest.py:197` — chargen completes
  deterministically.
- `tests/server/test_chargen_loadout.py` is the existing unit-test
  file for `apply_starting_loadout()`; the TDD-natural unit tests
  belong there (extend, don't replace).

### Test files (where new tests should land)

- Extend: `tests/server/test_chargen_loadout.py` — add overlap
  fixtures (e.g., torch in both `equipment_tables` and
  `starting_equipment[class]`); assert dedup; assert spans.
- Extend: `tests/server/test_chargen_persist_and_play.py` — wire-test
  with the Blutka regression fixture (24-item input → 13-item
  post-state).

## Scope Boundaries

**In scope:**

- Identity-aware append in `apply_starting_loadout()`
  (`server/dispatch/chargen_loadout.py:119`).
- Dedup keys: `id` (case-insensitive) + `name` (case-insensitive)
  fallback.
- New OTEL spans `chargen.starting_kit_dedup_evaluated` and
  `chargen.starting_kit_dedup_fired`, registered in `SPAN_ROUTES`.
- TDD-first test: failing test with the Blutka 24-item regression
  fixture, then the dedup implementation that brings the count to 13.
- Unit tests for: pure-overlap (every starting_equipment id already
  present → all skipped); pure-disjoint (no overlap → no skips);
  partial overlap (the realistic path); name-only collision (id
  differs, name matches).

**Out of scope:**

- The larger refactor that designates one extractor as authoritative
  and silences the other (option 2 in Technical Guardrails). File a
  follow-up note pointing back to the chargen-port IOU.
- Changing the builder's item-hint emission (`builder.py:1366–1382`,
  `builder.py:1407–1422`). The builder's stub-form remains; dedup
  catches the overlap downstream.
- Multi-quantity dedup (e.g., 6 torches → 1 torch). The bug
  description names quantity duplicates as part of the symptom; the
  fix is to dedup *the second-batch additions*, leaving the
  builder's stack intact. If the builder produced 6 torches as
  separate items, the dedup will collapse the catalogue's 1 torch
  against any of them — net result is the catalogue copy is dropped.
  A separate follow-up could quantity-merge sibling items (stack
  consolidation), but that's a different shape of fix.
- Migrating existing saves. Players with a 24-item Blutka kit keep
  the kit; new chargens get the dedup.
- UI changes. The fix surfaces in the GM panel via the new spans;
  the inventory UI sees fewer items naturally.

## AC Context

1. **Overlap between `equipment_tables` rolls and
   `starting_equipment[class]` is deduplicated; final inventory
   reflects the union, not the sum.**
   - TDD-natural test (the Blutka regression): fixture pack with
     `equipment_tables` that produces 11 stub-form items (matching
     playtest evidence — torches, rations, waterskins, chalk, poles)
     and `starting_equipment["Adventurer"]` that produces 13
     catalogue items, with 11 ids overlapping. Drive
     `apply_starting_loadout()`. Assert
     `len(character.core.inventory.items) == 13` (the union, not
     24). Assert no two items share an id or a (case-insensitive)
     name.
   - This is the negative-to-positive transformation: the failing
     test ships the 24-item evidence; the fix lands the dedup.

2. **Pure-disjoint case behaves identically pre- and post-fix.**
   - Test: pack with `equipment_tables` and
     `starting_equipment[class]` whose ids are fully disjoint. Drive
     loadout. Assert the post-state count is the sum of both.
     Regression guard against an over-eager dedup eating legitimate
     items.

3. **Pure-overlap case skips everything in the second batch.**
   - Test: every id in `starting_equipment[class]` is already
     present from `equipment_tables`. Drive loadout. Assert
     `items_added == 0`, `skipped_count == len(equipment_ids)`. The
     `chargen.starting_kit_dedup_fired` span carries the full
     `skipped_ids` list.

4. **Name-fallback collision detection.**
   - Test: builder emits item with `id="torch_1"` and `name="Torch"`.
     Catalogue emits `id="torch"` and `name="Torch"`. Dedup detects
     the collision via name and skips the catalogue entry.

5. **OTEL `chargen.starting_kit_dedup_evaluated` fires on every
   chargen-confirm; `dedup_fired` fires only on overlap.**
   - Test: 3 chargen runs (disjoint, full-overlap, partial). Assert
     `chargen.starting_kit_dedup_evaluated` fires 3 times with
     correct counts; `chargen.starting_kit_dedup_fired` fires 2
     times (full + partial), 0 times on disjoint.
   - `SPAN_ROUTES` registration verified — Sebastien's GM panel sees
     the events.

6. **Wire-test: end-to-end chargen confirms produce a deduplicated
   inventory and persist the deduped result.**
   - Drive `_handle_connect` → `_chargen_confirmation()` with the
     overlap fixture; assert the saved snapshot
     (`SqliteStore.load()` post-confirm) has the deduped inventory,
     not the 24-item version. This catches the half-wired regression
     where dedup runs in-memory but the persisted snapshot still has
     stale items.
