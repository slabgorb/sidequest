# Epic 76: Universal Retrieval Follow-Ups — 75-6 Hardening + Source Coverage

## Overview

Harden the entity-card retrieval layer that landed in Story 75-6 (ADR-118 §D2
entity card sync/reproject), then make the "universal" retrieval index actually
universal. Today the index is **NPC-pool-only** (an ADR-118-permitted NPC-first
v1); this epic extends `sync_entity_cards` to stateful `snapshot.npcs`,
factions, and locations, and closes a set of non-blocking review findings carried
forward from 75-6's finish (untested dispatch gate, loose assertions, missing
dimension guard, log-leakage defense, entity-only-turn telemetry).

**Priority:** P2
**Repo:** server
**Stories:** 7 (14 points) — 76-1 DONE; 76-2…76-7 backlog

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-118 — Universal Retrieval Layer** (`docs/adr/118-*.md`) | §D2 entity card sync/reproject (the layer 75-6 built and this epic hardens); the NPC-first v1 carve-out that 76-6/76-7 close out to full source coverage |
| **Story 75-6 context** (`sprint/context/context-story-75-6.md`) | The parent implementation — entity card sync/reproject; its review surfaced every 76-x follow-up |
| **Epic 75 context** (`sprint/context/context-epic-75.md`) | The RAG retrieval layer epic this hardens; 76 blocks the full value of 75-7 (OTEL) and 75-8 (e2e) |
| **python.md #6 (project test rules)** | The assertion-tightening contract for 76-2 (exact-match over `>=`/over-broad guards) |
| **Lore embed worker** (`sidequest-server/.../lore_embedding.py`, `lore_embed` dispatch) | The expected_dim guard (76-3) and log pattern (76-4) being mirrored from lore→entity |

## Background

Story 75-6 implemented ADR-118 §D2 — entity card sync and reproject — and landed
with a clean review, but the reviewer (and finish) carried **non-blocking
follow-ups** rather than blocking the merge. This epic is that backlog, in two
threads:

**Thread 1 — Hardening (76-2…76-5).** Close the gaps 75-6 review flagged:
- **76-2** — tighten 3 loose test assertions (per python.md #6): `embedded >= 1`
  → `== 1`; an over-broad `failed_refs` guard → the exact `['   ']`; add an
  `op == 'synced'` assertion on the skipped-path watcher event.
- **76-3** — mirror the **lore worker's `expected_dim` guard** into the entity
  embed worker (`embed_pending_entity_cards` + `EntityStore.update_embedding`) so
  a mid-session daemon model-dim change cannot write a stale-dimension vector
  (today it self-heals one turn later via requeue — wasteful and briefly wrong).
- **76-4** — harden the embed text-too-large log against future content leakage:
  log `type(exc).__name__` instead of the `ValueError` object in both
  `entity_embedding.py` and `lore_embedding.py` (defense-in-depth — safe today,
  fragile if a content-bearing `ValueError` is ever introduced).
- **76-5** — entity-only-turn telemetry precision: surface `entity_pending` in
  the `lore_embed` dispatch `completed`/`dispatch_skipped` events so an
  entity-only turn no longer reports `pending_at_dispatch=0` with no
  entity-queue signal.

**Thread 2 — Source coverage (76-6, 76-7).** ADR-118 permitted an NPC-pool-only
v1; the index is not yet "universal." This thread extends it:
- **76-6** — sync stateful `snapshot.npcs` (not just `NpcPoolMember`s): add an
  `Npc` projector path (`project_npc_card` currently takes only pool members) and
  extend `sync_entity_cards` so **scene-stateful** NPCs are retrievable.
- **76-7** — sync **factions** (world lore) and **locations** (diffuse sources:
  room graph / `world_materialization` / PG promotions) through
  `project_faction_card`/`project_location_card`, so
  `entity_sync.{faction,location}_count` stop reading 0.

## Technical Architecture

All work lives in the server's **entity retrieval / embedding pipeline** —
`sync_entity_cards`, the entity projectors, the embed worker, the `EntityStore`,
and the `lore_embed` dispatch telemetry. The hardening thread mirrors patterns
the lore worker already proved; the coverage thread adds projector paths for new
source types.

```
sources                         projectors                index/embed
─────────────────────────────────────────────────────────────────────
NpcPoolMember (v1, live) ─────► project_npc_card ──────┐
snapshot.npcs (76-6, NEW) ─────► project_npc_card+Npc ──┤
factions     (76-7, NEW) ──────► project_faction_card ──┼─► sync_entity_cards
locations    (76-7, NEW) ──────► project_location_card ─┘        │
   (room graph / world_materialization / PG promotions)         ▼
                                              embed_pending_entity_cards
                                              + EntityStore.update_embedding
                                              [76-3: expected_dim guard mirrored from lore]
                                                              │
                                              lore_embed dispatch telemetry
                                              [76-5: surface entity_pending in completed/skipped]
```

**Key files (areas — verify exact paths at story start):**

| Area | Stories |
|------|---------|
| Entity sync (`sync_entity_cards`) + projectors (`project_npc_card`, `project_faction_card`, `project_location_card`) | 76-6 (npc/Npc path), 76-7 (faction/location paths) |
| Entity embed worker (`embed_pending_entity_cards`, `EntityStore.update_embedding`, `entity_embedding.py`) | 76-3 (dim guard), 76-4 (log hardening) |
| Lore embed worker (`lore_embedding.py`, `lore_embed` dispatch) | 76-3 (source pattern), 76-4 (log), 76-5 (telemetry) |
| 75-6 test suite | 76-2 (assertion tightening) |

**Guardrails:**
- **No source-text wiring tests** (project rule) — 76-x tests must assert on
  behavior/telemetry, not on source-text presence. (Sibling epic 72-14 exists
  specifically to replace a source-text wiring test; do not introduce new ones.)
- 76-3's dim guard must **fail/skip loudly** on a dimension mismatch (emit the
  guard signal), not silently write a stale vector — No Silent Fallbacks.
- Source coverage (76-6/76-7) is **wiring**, not new infrastructure: the index,
  embed worker, and store already exist; these stories add projector paths and
  extend the sync call. Verify each new source actually flows end-to-end
  (`entity_sync.{faction,location}_count > 0` in OTEL), not just that the
  projector function exists — the project's most expensive bug class.

## Cross-Epic Dependencies

**Depends on:**
- **Epic 75 (RAG Retrieval Layer) / Story 75-6** — the entity card sync/reproject
  layer this epic hardens and extends. 76-1 (done) guards 75-6's silent-revert
  risk with a regression test.
- **ADR-118** — the universal-retrieval design and its NPC-first v1 carve-out.

**Depended on by:**
- **Story 75-7 (OTEL retrieval.universal instrumentation)** — the GM-panel value
  is incomplete while the index is NPC-only; 76-6/76-7 make the universal counts
  meaningful.
- **Story 75-8 (end-to-end retrieval integration)** — full e2e value depends on
  factions/locations/stateful-NPCs being retrievable.
