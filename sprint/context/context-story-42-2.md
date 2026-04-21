---
parent: context-epic-42.md
workflow: tdd
---

# Story 42-2: ResourcePool + threshold-lore minting

## Business Context

ADR-033 resource pools are the mechanism by which encounter-adjacent but session-persistent resources (ammunition, fuel, stamina, faction goodwill) decay across play. The **threshold-crossing lore mint** is the load-bearing design trick: when a pool crosses a tier threshold, an authored lore beat enters the narrator's `LoreStore` and shapes subsequent narration. This is how a pack authors a "your reputation is now `Wanted`" beat that the narrator will reliably reference — without hardcoded narration keywords.

Without ported resource pools, any pack feature that relies on pool tiers (spaghetti_western reputation, road_warrior fuel, mutant_wasteland radiation exposure) plays flat in the Python port.

## Technical Guardrails

**Port scope:**
- `sidequest-api/crates/sidequest-game/src/resource_pool.rs` (275 LOC)

**Target files (new):**
- `sidequest/game/resource_pool.py` — `ResourceThreshold`, `ResourcePool`, `ResourcePatchOp`, `ResourcePatch`, `ResourcePatchResult`, `ResourcePatchError`, `mint_threshold_lore(...)`

**Target files (modified):**
- `sidequest/game/session.py:313` — `resources` field type promotion (pull-forward from Phase 4 per Epic 42 recommendation)
- `sidequest/game/__init__.py` — export new types

**Dependencies:**
- `sidequest/game/lore_store.py` (existing — Story 2.3 Slice F) — `mint_threshold_lore` writes to this. Confirm `LoreStore.add_entry(...)` or equivalent exists with compatible signature.

**Translation key:**
- Rust `enum ResourcePatchError { ... }` → Python exception hierarchy: `ResourcePatchError(Exception)` as base, one subclass per variant (`InvalidPoolError`, `UnderflowError`, `OverflowError`, etc. — names track Rust verbatim)
- Rust `Result<T, E>` patch application → raise exception on failure, return `ResourcePatchResult` on success
- `#[non_exhaustive] enum ResourcePatchOp` → `StrEnum` subclass

**Patterns to follow:**
- **Atomic patch semantics:** a failed patch must leave the pool unchanged. Rust achieves this by computing the new value first and only mutating on success. Port the same pattern — do not mutate, then roll back on exception.
- **Threshold-crossing invariant:** a threshold fires exactly once per crossing direction. Hovering at the boundary does not re-fire. Pool state tracks `last_tier_crossed`; compare current tier to that on each patch. Test with the exact-hit and reversal edge cases.

**What NOT to touch:**
- `StructuredEncounter.secondary_stats` (42-1) — pools are session-persistent, `secondary_stats` is encounter-scoped. They are NOT aliases. Do not unify.
- Any narrator prompt assembly — 42-4 scope
- Rust source

## Scope Boundaries

**In scope:**
- `ResourceThreshold` (tier label + trigger point + lore beat template)
- `ResourcePool` (`name`, `current`, `max`, `decay_curve`, `thresholds: list[ResourceThreshold]`, `last_tier_crossed: str | None`)
- `ResourcePatchOp` enum (`Spend | Restore | SetMax | Invalidate` — names verbatim)
- `ResourcePatch` input DTO + `ResourcePatchResult` output DTO
- `ResourcePatchError` + typed subclasses
- `ResourcePool.apply_patch(patch) -> ResourcePatchResult` method
- `mint_threshold_lore(thresholds, store, turn)` free function
- `GameSnapshot.resources: list[ResourcePool]` (was pass-through `list`)
- Full Rust test suite ported (one pytest function per `#[test]`)

**Out of scope:**
- Any dispatch integration that drives `apply_patch(...)` from live encounter ticks — 42-4 scope
- UI-side resource display — Phase 3 is server-only
- Pool-to-encounter linkage (e.g., "combat consumes ammo pool") — content-authored in YAML, not wired in this story
- Decay curves beyond what Rust ships — port verbatim, no new shapes

## AC Context

**AC1: Patch-op semantics parity.**
All four `ResourcePatchOp` variants produce Rust-identical behaviour on fixture inputs. Fixture: pool at `current=10, max=20`; apply each op with a canned value; assert new `current`/`max` and returned `fired_thresholds` list.
*Edge case:* `Spend` when `current < amount` raises `UnderflowError` without mutating the pool.

**AC2: Atomic patch application.**
Any patch that would violate invariants (negative underflow, overflow past max, unknown pool reference) raises and leaves pool state unchanged. Test: read pool state before the failing call, assert identical state after catching the exception.

**AC3: Threshold fires exactly once per crossing.**
Pool with thresholds at `[25, 50, 75]` gets patched through values `[20, 30, 30, 40, 55, 55, 45, 30]`; the `fired_thresholds` across those patches are `[25, 50, None (repeat), None (reversed through 50), 25 (reversed)]` — i.e., one fire per directional crossing.
*Edge case:* exact-hit on a threshold (patch lands `current` exactly on `25`) counts as a crossing. Match Rust behaviour verbatim.

**AC4: `mint_threshold_lore` produces Rust-parity lore entries.**
Fixture: a threshold with `lore_beat_template = "Your reputation is now {tier}."` and `tier = "Wanted"` produces a `LoreEntry` with `text = "Your reputation is now Wanted."` and `category`/`keywords` matching the Rust output on the same inputs.
*Edge case:* empty thresholds list → no lore entries minted, no exception.

**AC5: `GameSnapshot.resources` loads legacy saves.**
A save file with `resources: [...]` in Rust-produced shape model-validates into `list[ResourcePool]`. Saves with unknown fields inside individual pool dicts fail loud (per CLAUDE.md). Saves with `resources: []` or missing `resources` key both validate to `[]`.

**AC6: Every Rust test ports 1:1.**
`grep '#\[test\]' sidequest-api/crates/sidequest-game/src/resource_pool.rs` → count N. Python test file has N `def test_*` functions with the same names (snake_case).

## Assumptions

- **`LoreStore.add_entry(...)` accepts the shape `mint_threshold_lore` needs.** Story 2.3 Slice F ported a minimal LoreStore; if its API differs from Rust's, add a thin adapter rather than reshaping LoreStore itself.
- **Pull-forward of `GameSnapshot.resources` does not break any Phase 1/2 save.** Most Phase 1/2 saves likely have `resources: []` (no pool use yet). Verify by loading the Sunday caverns_and_claudes save fixture as part of the test suite.
- **No narrator-prompt consumer of pools lands in Phase 3.** Pool data feeding narrator context is Phase 3+ work; 42-2 only mints into `LoreStore`, which narrator already consumes.
