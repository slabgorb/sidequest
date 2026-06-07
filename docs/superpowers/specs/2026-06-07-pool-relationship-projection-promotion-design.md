# Pool-Member Relationship Projection + Promotion (Story 97-1) — Design

**Date:** 2026-06-07
**Story:** 97-1 — Pool-member relationship projection gap — engaged npc_pool members never get ADR-136 cards
**Status:** Approved (Keith, 2026-06-07)
**Repos:** sidequest-server
**Related:** ADR-136 (relationship surface), ADR-128 (development ladder), ADR-020 (disposition), server #742 (residual 1), server #738 (`invented_from`), epic 97 / `sprint/context/context-story-97-1.md`

## Problem

`build_relationship_entries` (`sidequest/game/projection/relationships.py:51-66`) projects `snapshot.npcs` only. Narrator-introduced NPCs live in `npc_pool` — so the NPCs players actually bond with in play never get ADR-136 relationship cards regardless of earned history. Measured repro (perseus MP 2026-06-07): Rifenna Muse — handshake, struck deal, three scenes, party flying on her ship — absent from the Relationships tab while a roster combat opponent got a card.

## Decisions (brainstorm 2026-06-07)

1. **Scope: Hybrid.** Project engaged pool members onto the Relationships tab immediately; promote to full `Npc` citizenship at a milestone. (Rejected: projection-only — pool NPCs stay second-class everywhere else; promotion-only — Relationships tab stays empty until the threshold.)
2. **Promotion trigger: tier escalation OR valence beat.** Promote when the ADR-128 ladder crosses `acquaintance` (3 deduped interactions, already computed in `sidequest/game/npc_development.py`) **or** when the narrator writes a valenced beat via the existing `update_npc_disposition` tool. Catches both the slow-burn regular and the one-scene deal-maker (the Rifenna case hit deal-struck before any count threshold).
3. **Projection seen-gate: scene-present + interacted.** A pool member projects only once it has been present in a scene AND has ≥1 deduped interaction tick (or any disposition beat). Dialogue-only mentions (the blackthorn "Captain Hale" mint — off-screen man in a photograph) and pregen-seeded latents never card. Mirrors the roster's existing "encountered" semantics and satisfies AC 2 as written.

## Design

### Leg 1 — Projection (immediate visibility)

`build_relationship_entries` gains a second source: after walking `snapshot.npcs`, walk `snapshot.npc_pool` and emit a `RelationshipEntry` per member passing the seen-gate. Entries render from the member's own fields (name, disposition, beat log). **No `Npc` object is minted to serve the projection** — `test_disposition_does_not_drift_without_a_stateful_npc` stays green.

### Leg 2 — Promotion (citizenship at milestone)

On either trigger, the member is promoted via the **existing** pool→Npc conversion path (the one #738 already threads `invented_from` through — reuse, don't rebuild), additionally carrying forward:

- accumulated deduped interaction count (the ladder must not reset),
- current `disposition` value,
- the disposition beat log.

After promotion the pool entry is removed. The relationship card re-sources from the roster under the same name key — exactly one card, one identity, before and after.

### Invariants preserved

- **Hostile-context gate (#742):** a member seated as a live opponent accrues no development ticks and cannot promote mid-fight; a *resolved* encounter releases the gate (beaten foe can become a contact). The "Unknown hostile — Warm ↗" failure cannot recur: projection requires interaction ticks the gate suppresses.
- **97-5 awareness:** all thresholds key on *deduped* counts (`Npc.last_development_turn` seam, `narration_apply.py:2094`) — the turn-1 double-apply cannot double-tick toward promotion. If 97-5 lands first, nothing changes here.
- **Emit change-gate:** the roster-signature gate in `relationships_emit.py` must incorporate projected pool members and promotion events, or new cards never fan out (#742 residual 2 — verify during implementation, don't assume).
- **`invented_from` alias continuity (#738):** promotion preserves the alias leg so re-mentions of the original name still reconcile to the promoted Npc.

### OTEL (lie-detector, AC 3)

One span per decision, **both branches**:

| Span | Attributes |
|------|-----------|
| `npc.pool_projected` | name, interactions, beats |
| `npc.pool_projection_skipped` | name, `reason=not_present\|no_interactions\|hostile_context` |
| `npc.promoted_from_pool` | name, `trigger=tier\|valence_beat`, carried counts |
| `npc.promotion_skipped` | name, reason (e.g. `hostile_context`) |

The GM panel must distinguish "deliberately not carded" from "projection didn't run."

## Testing

- **Unit:** seen-gate truth table — present+interacted ✓; dialogue-only mention ✗; pregen latent ✗; live-hostile ✗; resolved-hostile ✓ (gate released).
- **Unit:** both promotion triggers independently; carried state (count, disposition, beats, `invented_from`) survives promotion; pool entry removed; no duplicate card.
- **Integration (wiring test, mandatory):** the perseus shape end-to-end — pool member seated as negotiation Other, narrator valence beat → card appears, promotion fires, single identity — through the real projection + emit path, not a synthetic helper call.
- **Regression:** `test_disposition_does_not_drift_without_a_stateful_npc`; full suite at the known 2-failure epic-96 baseline (run with `SIDEQUEST_GENRE_PACKS` + `SIDEQUEST_TEST_DATABASE_URL`).

## Out of scope

- MP emit fan-out defect (#742 residual 2) beyond the change-gate signature check — re-observe post-fix, file separately if still broken.
- Fairfax presence-breadth (#742 residual 3 — narrator listing off-scene NPCs in `npcs_present`).
- The upstream double-apply (97-5).
- Valence model changes — #742's milestone-only drift + narrator tool stands.
- Retroactive repair of existing saves (legacy-saves doctrine; the paused perseus save is forensic reference only).
