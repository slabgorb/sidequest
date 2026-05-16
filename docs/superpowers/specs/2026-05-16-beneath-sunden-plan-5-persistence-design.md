# Beneath Sünden — Plan 5: Persistence Layer (Design)

- **Date:** 2026-05-16
- **Status:** Approved (design) — pending spec review, then implementation plan
- **Parent spec:** `docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md` (§7, §8, §11; §10 decomposition item 5)
- **Sub-plan:** 5 of 8 — *Persistence layer* (`dungeon_map`, `frontier`, mutation overlay, complication ledger; round-trip tests)
- **Predecessors (all merged):** Plan 1 maze-maker family port · Plan 2 region-graph + Jaquays · Plan 3 `depth_score` · Plan 4 theme palette + set-piece schema
- **Extends:** ADR-055 (room-graph), the existing `sidequest/game/persistence.py` `SqliteStore` save model
- **Does NOT:** introduce a migration framework, fork any `as_dict()` span contract, touch `caverns_sunden`, add dice/combat mechanics (ADR-074 reused untouched)

## 1. Problem & Intent

Plans 2–4 produced pure-compute, in-memory dungeon models (region graph, depth
scores, theme/set-piece schema). None of it survives a reload. Plan 5 makes the
megadungeon **persistent**: the four save-DB structures from parent spec §7, with
materialize → commit → reload → identical round-trip tests, per-region freeze
across generator-version bumps, and **no floor-indexed keys anywhere**.

Plan 5 is the *storage layer only*. It ships the module + a real save-DB
round-trip, with the runtime caller (the async materializer / frontier-crossing
session path) **honestly deferred to Plan 7** — the same discipline Plans 2–4
used for their deferred consumers (documented carry-forward, no stubs, no fake
wiring).

## 2. Decisions (locked during brainstorming)

| # | Decision |
|---|----------|
| 1 | **Module:** new `sidequest-server/sidequest/dungeon/persistence.py`, self-contained domain module (Plan 2–4 `sidequest/dungeon/` precedent). Split a `_serde.py` only if serialization adapters bloat the file — decided at implementation, not pre-optimized. |
| 2 | **Scope depth:** module + real save-DB round-trip; **no materializer/session caller** (Plan 7). Honest deferral + a Plan-7 wiring-test contract. |
| 3 | **Table home:** the four dungeon structures persist in the **same save DB**, on a **caller-supplied** SQLite connection (the store does not open its own), reusing `game/persistence.py`'s `_configure_connection` WAL + `foreign_keys` PRAGMA discipline. Plan 7's materializer later owns the single-transaction commit spanning game-save + dungeon-save (parent §7.5). |
| 4 | **Serialization (Approach A):** keyed-row + JSON `TEXT` payload built from the Plan 2–4 models' existing `as_dict()` serializers; Plan 5 adds the symmetric `from_dict()`. The few queried fields are promoted to real indexed columns. Masks ride as an in-DB `BLOB` (single-save-file invariant). |
| 5 | **No migration burden:** no `beneath_sunden` campaign exists yet, so there is no legacy dungeon data to migrate. Schema is additive `CREATE TABLE IF NOT EXISTS` (matches the existing `SqliteStore` pattern; no migration framework). |
| 6 | **No floors:** no table, column, or index may be keyed by or named for a floor (parent §5/§11 hard constraint), enforced by a schema-introspection test. |

## 3. Schema — Four Tables (additive `CREATE TABLE IF NOT EXISTS`)

All four use the keyed-row + JSON-payload shape (Approach A). Queried fields are
promoted out of the payload into real indexed columns; everything else lives in
the model-owned JSON so additive frozen-dataclass field growth never forces a
schema change.

### 3.1 `dungeon_map` — the single growing region graph
One row per region. **Keyed by `region_id`, never by floor.**

| Column | Type | Notes |
|---|---|---|
| `region_id` | `TEXT PRIMARY KEY` | natural domain id |
| `expansion_id` | `TEXT` | indexed; the materialization batch |
| `depth_score` | `REAL` | indexed; from Plan 3 (`RegionNode.depth_score`) |
| `generator_version` | `TEXT` | per-region freeze stamp (parent §7) |
| `payload` | `TEXT` | JSON `RegionNode.as_dict()` — includes typed edges (corridor/stairs/shaft/chute/secret), hidden/shortcut/conditional flags, set-piece component-state refs |
| `mask` | `BLOB NULL` | ADR-096 interior mask sidecar, kept in-DB for the single-save-file invariant |
| `created_at` | `TEXT` | ISO timestamp |

Edges are stored **in the region payload** (Plan 2's `RegionNode.as_dict()`
already emits them; a separate edge table would re-invent serialization the
Approach-A contract owns). Cross-region edges are reconciled on `load_map()`.

### 3.2 `dungeon_frontier` — unexpanded edges
One row per frontier edge.

| Column | Type | Notes |
|---|---|---|
| `frontier_edge_id` | `TEXT PRIMARY KEY` | |
| `from_region_id` | `TEXT` | indexed |
| `heading` | `TEXT` | direction/affinity hint |
| `spawn_depth_score` | `REAL` | `depth_score` an expansion here would spawn at |
| `payload` | `TEXT` | JSON |
| `created_at` | `TEXT` | |

### 3.3 `dungeon_mutation_overlay` — append-only mutation log
Sprung traps, looted rooms, collapses, resolved set-pieces. **Append-only** —
mutations are facts, never updated or deleted; load replays the overlay over the
base map.

| Column | Type | Notes |
|---|---|---|
| `mutation_id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | replay order |
| `region_id` | `TEXT` | indexed |
| `kind` | `TEXT` | `trap_sprung` / `looted` / `collapsed` / `setpiece_resolved` / … |
| `payload` | `TEXT` | JSON |
| `created_at` | `TEXT` | |

### 3.4 `dungeon_complication_ledger` — first-class open-thread ledger
Parent §7.1: the spine. Threads start at attach (Plan 6/7 produce them), persist
until player-resolved, clear only on resolution. Plan 5 owns the storage + status
transition API, **not the producers**.

| Column | Type | Notes |
|---|---|---|
| `thread_id` | `TEXT PRIMARY KEY` | |
| `origin_region_id` | `TEXT` | indexed |
| `kind` | `TEXT` | `trope` / `quest` |
| `status` | `TEXT` | **indexed** — the hot query: open threads for quest log / GM panel / §7.1 accumulation |
| `started_at_depth_score` | `REAL` | |
| `payload` | `TEXT` | JSON |
| `created_at` | `TEXT` | |
| `resolved_at` | `TEXT NULL` | set on resolution |

## 4. Serialization Contract (Approach A)

Plan 5 adds symmetric `from_dict()` classmethods **only to the models it
persists** — `RegionNode` (incl. its `depth_score` and nested typed-edge
structures) and the frontier/mutation/thread payload models. The transient
*report* classes (`GenerationReport`, `DepthReport`) are **not** persisted —
they are referenced here solely as the authoritative `as_dict()` *span-contract
shape* the persisted models' serialization must stay consistent with. Do **not**
add `from_dict()` to the report classes.

**`as_dict()` / `from_dict()` are an exact round-trip pair — the central
asserted invariant.** The `as_dict()` shapes *are already* the OTEL span
contracts (Plan 2 carry-forward: `GenerationReport.as_dict()` is Plan-7's
`dungeon.materialize.*` span contract; Plan 3: `DepthReport.as_dict()` is the
`attach` span contract). Plan 5 **reuses** these shapes and must **not** fork or
redefine them. If a model genuinely needs a field for round-trip fidelity that
`as_dict()` omits, that is a Plan 2/3 correction logged as a deviation — not a
Plan-5-local serialization fork.

## 5. Public API — the Deferred Plan-7 Caller Surface

```
DungeonStore(conn: sqlite3.Connection | Path)   # mirrors SqliteStore.__init__ shape;
                                                  # does NOT open its own connection
  .ensure_schema()                                # idempotent additive CREATE TABLE IF NOT EXISTS
  .commit_expansion(expansion)                    # one expansion's regions + frontier deltas
                                                  #   + lit threads, WITHIN the caller's txn
                                                  #   (Plan 7 owns the §7.5 one-txn boundary;
                                                  #    NO caller yet — honest deferral)
  .load_map() -> DungeonMap                       # base rows + replayed mutation overlay
  .record_mutation(region_id, kind, payload)      # append-only
  .open_thread(thread) / .resolve_thread(id)      # ledger transitions
  .open_threads() -> list[Thread]                 # status-indexed query
```

**Fail-loud (No Silent Fallbacks — project critical):** unknown region/thread
ref, schema-version mismatch, or undecodable JSON raises — reusing/paralleling
the existing `SaveSchemaIncompatibleError` / `SerializationError` /
`NotFoundError` taxonomy from `game/persistence.py`. No silent default, no
alternate path.

`commit_expansion` does **not** autocommit — it writes within the caller's
transaction so Plan 7 can stitch game-save + dungeon-save into the single
parent-§7.5 transaction. Presented as API; **no caller exists yet** (Plan 7).

## 6. Freeze & OTEL

- **Freeze:** `generator_version` is stamped per region at commit. A round-trip
  test writes a region at version X, bumps the module version constant, reloads,
  and asserts the region payload is byte-identical and not rewritten (parent §7
  "frozen regions never regenerated"). Forward robustness — no legacy data exists
  per Decision 5.
- **OTEL (CLAUDE.md mandatory):** Plan 5 emits only spans it has *real callers*
  for — `dungeon.persist.commit`, `ledger.add`, `ledger.resolve` — emitted from
  the store methods and exercised by the store's own tests. Parent §8's
  `dungeon.materialize.*`, `frontier.expand`, `setpiece.attach`, `trope.start`,
  `quest.seed` belong to Plan 6/7 (the producers/materializer) and are **noted,
  not pre-emitted** — emitting spans with no runtime caller would be the exact
  Illusionism the GM panel exists to catch. Consistent with Plan 2–4
  honest-deferral.

## 7. Testing Strategy (parent §11)

- **Round-trip:** `model → commit → reload → assert equal` for all four
  structures, against real SQLite — both `:memory:` and a temp-file variant (the
  temp-file path exercises WAL, matching `_configure_connection`).
- **`as_dict()/from_dict()` exact-inverse property sweep** across a Plan 2/3 seed
  sweep, reusing the existing region-graph + depth generators as fixtures (no new
  fixtures invented).
- **Mutation overlay** survives reload; replay order is deterministic
  (`mutation_id` ascending).
- **Complication ledger:** open → resolve transitions persist; `open_threads()`
  reflects accumulation across multiple committed expansions (the §7.1
  accumulation-observable assertion).
- **Frozen region** untouched after a generator-version-constant bump.
- **No floor-indexed keys:** a schema-introspection test asserting no table,
  column, or index name matches `/floor/i` (parent §5/§11 hard constraint —
  the Plan-4-style deliberate completeness gate).
- **Wiring (deferred, per CLAUDE.md):** Plan 5 ships `DungeonStore` and a test
  proving it round-trips against a *real save-DB-shaped* connection (same
  `_configure_connection` PRAGMAs as `game/persistence.py`). The
  materializer/frontier-crossing **integration** wiring test is explicitly
  **Plan 7's** — documented carry-forward, Plan 2–4 precedent, not stubbed.

## 8. Scope Boundary

**In scope:** the four save-DB structures + schema, Approach-A serialization
(`from_dict()` additions), `DungeonStore` API, mutation-overlay replay,
complication-ledger storage + status transitions, per-region freeze stamp,
fail-loud taxonomy, store-owned OTEL spans, round-trip / property / freeze /
no-floor tests, deferred-wiring contract for Plan 7.

**Out / deferred:** async look-ahead materializer + frontier-crossing promotion
+ the single-transaction commit *caller* (Plan 7); set-piece roll &
trope/quest-at-attach *producers* (Plan 6); session integration & integration
wiring test (Plan 7); `beneath_sunden` world authoring + `caverns_sunden`
retirement (Plan 8); any dice/combat mechanics (ADR-074, reused untouched);
migration framework (none exists, none needed — Decision 5).

## 9. Carry-Forward to Plan 6 / 7

- **Plan 6** (set-piece attach + trope/quest-at-attach) produces the
  component-state and thread objects that Plan 5's `record_mutation` /
  `open_thread` persist. Plan 6 must serialize through the Approach-A
  `as_dict()/from_dict()` pair — not a parallel format.
- **Plan 7** (materializer) owns: `commit_expansion`'s *caller*, the parent-§7.5
  single transaction spanning game-save + dungeon-save, the
  `dungeon.materialize.*` / `frontier.expand` spans, and the **mandatory
  integration wiring test** proving the materializer is invoked from the real
  session / frontier-crossing path. Plan 5's `DungeonStore(conn)` deliberately
  takes the caller's connection so Plan 7 can wrap both stores in one txn.
- **Open parent §12 items unaffected by Plan 5:** look-ahead breadth, burst
  magnitudes, bucket coarseness, curation mechanism — all Plan 6/7/8.
