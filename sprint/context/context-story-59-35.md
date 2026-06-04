# Story 59-35 Context

## Title
Seat present FRIENDLY companions as side=player combatants in confrontations (ADR-116 / Guitar Solo)

## Metadata
- **Story ID:** 59-35
- **Type:** story
- **Points:** 5
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** Intent Router — Mechanical-Engagement Spine

## Problem
GOAL: an allied NPC at the player's side FIGHTS on side=player, not as a silent spectator. Completes ADR-116 (A Confrontation Requires an Other — the friendly side of seating) and enacts the SOUL Guitar Solo principle ('others get a concurrent meaningful part, never a silent audience'). This is the FIRST non-PC side=player actor in the system.

REUSE MAP (Explore 2026-06-04, develop): the opponent-seater is a SINGLE chokepoint to mirror — instantiate_encounter_from_trigger (server/dispatch/encounter_lifecycle.py:724) with _npc_fallback_at_location (464-537) seats opponents (side='opponent'/'neutral'); PCs seat side='player' (1040-1047). EncounterActor.side ALREADY accepts 'player' (game/encounter.py:105-127). Disposition Attitude.FRIENDLY lives at game/disposition.py:95-189. Scene-presence predicate is_npc_in_scene(npc, encounter, current_room) at game/npc_scene.py:99-150. Friendly NPCs ALREADY carry mechanical state: Npc.core HpPool + armor_class (ADR-114 ablative HP, game/creature_core.py), armed by the SAME _seed_combat_hp_depletion_to_npcs / _publish_combat_edge_to_npcs paths that arm opponents. participant.joined span (telemetry/spans/encounter.py:105-115) carries a 'source' attr. Per-recipient CONFRONTATION delivery (server/dispatch/confrontation.py make_confrontation_frame_supplier) is seat-agnostic — a seated ally gets its filtered beats automatically. MISSING: nothing queries 'present-AND-friendly' NPCs, and no path seats side='player' beyond PCs.

DESIGN (Architect / White Queen — reuse-first, symmetric to the opponent-seater, NO new ADR — completes ADR-116): (1) SEAM — in instantiate_encounter_from_trigger, AFTER opponent fallback (~925) and BEFORE the no-opponent guard (946), add a symmetric _friendly_fallback_at_location (parallel to _npc_fallback_at_location) that scans snapshot.npcs for scene-present (is_npc_in_scene / last_seen_location == acting actor's party_location) AND disposition.attitude()==Attitude.FRIENDLY AND not withdrawn, seating each as EncounterActor(side='player'). (2) ARM via EXISTING channels — reuse the opponent HP/edge seeding (_seed_combat_hp_depletion_to_npcs / _publish_combat_edge_to_npcs) so a seated ally has a real ADR-114 stat block; NO new data model, NO placeholder HP. (3) OTEL — reuse participant.joined with source='friendly_fallback', side='player' (+ disposition_attitude, last_seen_turn): the lie detector proving the engine seated the ally, not the narrator. (4) DELIVERY — no change; the per-recipient frame already serializes all actors + filters beats per seat, so the ally is legible to the table.

DECISIONS / SCOPE: FRIENDLY = disposition Attitude.FRIENDLY AND scene-present AND not withdrawn (hostile/neutral are NOT auto-seated to player). The 'requires an Other' invariant is UNCHANGED — it gates on side=opponent; a confrontation with only friendly side=player actors and no opponent still raises NoOpponentAvailableError / ends-on-no-Other exactly as today (friendly seating never satisfies the opponent requirement). Apply on the adversarial/opponent-seating (combat-category) path where side=player combatants resolve mechanically. DEFER: roster-only Companions (game/session.py Companion — no HpPool) are NOT seated as combatants (need promotion to Npc/Character first); social/audience-trial friendly seating (ADR-116 §3 social extension is itself still deferred); ally-seating balance tuning (belongs to ADR-093 confrontation calibration — flag if it skews the dial/HP math, do not solve here). Re-homed note: filed under epic 59 (intent-router/confrontation spine).

## Technical Approach
_Approach hints to be refined by TEA/Dev. The story title above defines the
intended behavior._

## Scope
- In scope: the behavior described by the story title.
- Out of scope: unrelated changes.

## Acceptance Criteria
- Symmetric friendly-seater: add _friendly_fallback_at_location (parallel to _npc_fallback_at_location, encounter_lifecycle.py:464-537), invoked in instantiate_encounter_from_trigger after opponent fallback (~925) and before the no-opponent guard (946). It seats snapshot.npcs that are scene-present (is_npc_in_scene) AND disposition.attitude()==Attitude.FRIENDLY AND not withdrawn as EncounterActor(side='player'). Test: present friendly NPC → appears in encounter.actors with side='player'; present HOSTILE NPC → not friendly-seated; absent friendly NPC → not seated.
- Armed via EXISTING channels: a friendly-seated NPC gets a real stat block through the SAME paths opponents use (_seed_combat_hp_depletion_to_npcs / _publish_combat_edge_to_npcs; ADR-114 ablative HP on Npc.core) — no new data model, no placeholder HP. Test: a friendly-seated NPC in an hp_depletion confrontation has core.hp/armor_class seeded like an opponent.
- Invariant preserved: friendly side=player seating does NOT satisfy 'a confrontation requires an Other'. PC + friendly ally with NO side=opponent still hits the no-opponent path (NoOpponentAvailableError / graceful prose) and ends-on-no-Other exactly as today. Test: PC + present friendly ally, zero opponents → unchanged no-opponent behavior.
- OTEL (lie detector): each friendly seat emits participant.joined with source='friendly_fallback', side='player' (+ disposition_attitude, last_seen_turn), so the GM panel confirms the engine seated the ally rather than the narrator inventing it. Test: span asserted per friendly seat with correct source/side (OTEL span assertion, not source-grep).
- Guitar Solo delivery (wiring, behavioral): the seated ally appears in the per-recipient CONFRONTATION frame the players receive (actors roster) via the existing make_confrontation_frame_supplier — no silent audience. Wiring test: begin a confrontation with a present friendly NPC and assert the emitted CONFRONTATION payload's actors include the ally with side='player'.
- DEFER — explicit non-goals: roster-only Companions (no stat block) are not seated as combatants (need promotion first); social/audience-trial friendly seating (ADR-116 §3 social extension still deferred); ally-seating balance tuning (ADR-093). v1 = present friendly NPCs seated side=player on the combat-confrontation path.

---
_Generated by `pf context create story 59-35` from the sprint YAML._
