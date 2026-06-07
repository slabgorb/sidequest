---
parent: context-epic-97.md
workflow: tdd
---

# Story 97-1: Pool-member relationship projection gap — engaged npc_pool members never get ADR-136 cards

## Business Context

The perseus repro is the sharpest player-facing failure of the relationship surface: Rifenna Muse — handshake, struck deal, three scenes, the party is *flying on her ship* — never appears on the Relationships tab, while a roster-promoted combat opponent got a card. The cause is structural, not behavioral: `build_relationship_entries` projects `snapshot.npcs` (the authored/promoted roster) only; `npc_pool` members are invisible to ADR-136 regardless of how many disposition beats they earn. Since most narrator-introduced NPCs (the ones players actually bond with in play) live in the pool, the relationship surface systematically misses the relationships the table formed at the table. This was FIXER residual (1) on server #742.

## Technical Guardrails

- **Design decision comes first** (this is why the story is 3 points and P1): pool→roster **promotion** on sustained engagement vs. direct **pool projection**. The Architect leans promotion-shaped because the machinery exists (Reuse-First): the ADR-128 development ladder in `sidequest/game/npc_development.py` already computes `acquaintance` at 3 interactions and `established` at 8, and #742 made tier escalation the only thing that writes milestone beats. A pool member crossing `acquaintance` is a natural promotion trigger. But evaluate both — direct projection avoids mutating the roster and may be the smaller change. Document the decision in the session file (or a short ADR if it changes the entity model).
- Projection seam: `sidequest/game/projection/relationships.py:51-66` (`build_relationship_entries`, `all_npcs = snapshot.npcs`).
- Pool model: `sidequest/game/npc_pool.py:27` (`NpcPoolMember`). Note `invented_from` (server #738) carries through pool→Npc promotion already — any promotion path must preserve it.
- **Do NOT spuriously mint `Npc` objects.** `test_disposition_does_not_drift_without_a_stateful_npc` pins the invariant that pool members without earned state don't become stateful NPCs. The seen-gate semantics of the existing projection (only "encountered" NPCs get cards) must extend to the pool, not be bypassed by it.
- #742's hostile-context gate applies: a pool member the party is actively fighting must not accrue development ticks; a resolved encounter releases the gate. Whatever promotion/projection logic lands must compose with `npc.development_skipped reason=hostile_context`.
- **97-5 interplay:** `_apply_npc_mentions` (the interaction counter feeding the ladder) currently double-fires on turn 1. If 97-5 hasn't landed, design the engagement threshold against deduped counts (`Npc.last_development_turn` seam at `narration_apply.py:2094` already dedupes the development tick) — don't calibrate against inflated raw mention counts.
- MP fan-out residual (2) from #742 (relationships emit is change-gated on a roster signature in `relationships_emit.py`, 1 emit/10 turns) is **adjacent but separate** — however, if pool members join the projection, verify the change-gate signature incorporates them, or new pool-derived cards will never emit.

## Scope Boundaries

**In scope:**
- The promotion-vs-projection design decision, documented
- Engaged pool members with relationship-relevant history appearing on the Relationships tab
- Seen-gate preservation for latent/unseen pool members
- OTEL span on every promotion/projection decision (fire and decline)

**Out of scope:**
- The MP emit fan-out defect (residual 2 of #742) — re-observe post-fix, file separately if still broken
- Fairfax presence-breadth (residual 3 — narrator listing off-scene NPCs in npcs_present)
- The upstream double-apply (97-5)
- Valence model changes — #742's milestone-only drift + narrator `update_npc_disposition` tool stands

## AC Context

1. **"An engaged npc_pool member with relationship-relevant history appears on the Relationships tab"** — Test: seed a pool member, drive ≥3 deduped interactions (or a narrator `update_npc_disposition` beat), build the projection → an entry exists for that member with its beat trail. The perseus shape (pool member seated as negotiation Other, deal resolved) is the canonical integration case.
2. **"A latent/unseen pool member does not (seen-gate semantics preserved)"** — Test: pool member exists (pregen-seeded, never referenced in play) → no card. Edge: a member referenced once in dialogue only (the 97-x blackthorn "Captain Hale" shape) should not card either.
3. **"OTEL span on the promotion/projection decision (lie-detector)"** — Test: span assertions on both branches — promoted/projected AND declined (with reason). Per house rule, the decline must emit; silence is indistinguishable from the current bug.

## Assumptions

- The ADR-128 ladder counts are trustworthy once 97-5 lands (or the threshold logic dedupes independently).
- `RelationshipEntry` protocol shape can represent a pool-derived entity without UI changes (the UI renders whatever entries arrive — verify with one look at the Relationships tab consumer before assuming).
- The perseus save (`2026-06-07-perseus_cloud-mp`, paused at turn 17) remains available as forensic reference but is NOT a migration target — already-mutated history stays as-is (legacy-saves doctrine).
