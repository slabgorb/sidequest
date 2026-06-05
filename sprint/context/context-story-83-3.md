# Story 83-3 Context

## Title
Ongoing-threat identity stability — reconcile a re-described threat instead of re-minting

## Metadata
- **Story ID:** 83-3
- **Type:** bug
- **Points:** 5
- **Priority:** p3
- **Workflow:** tdd
- **Repo:** server
- **Epic:** NPC Creature Identity & Naming Hardening

## Problem
Deferred from ping-pong #74. A single ongoing threat was re-minted under a NEW identity every turn because the narrator re-describes it each turn and each novel descriptor hits the Step-3 novel-mint branch: the forest threat became 'Clemence Coralfast' → 'The Unseen Watcher' → 'Keeper Goldbraid' across two turns, and NONE reconciled to the authored Cowardly Lion already in the npcs roster (disposition 5). The result is unstable opponent identity — the GM panel and the player see three monsters where there is one, and a hand-authored NPC is shadowed by phantom duplicates. Add a stability/reconciliation guard so a recurring threat resolves to its existing pool member or authored Npc instead of minting a fresh one. Likely levers: a narrator continuity signal (the mention points at an existing entity), appearance/role similarity reconciliation, and/or a 'one active unnamed threat' guard per scene. Coordinate with the existing comma-inversion match keys and the observation-gate ratification (49-6) so this doesn't fight them. Note interaction with 83-1: a creature with a stable creature_id is easier to reconcile across turns.

## Technical Approach
_Architect tandem observations (Houlihan, 2026-06-05, verified against code — full notes in `.session/83-3-tandem-architect.md`):_

**Where the bug lives.** `_apply_npc_mentions` (`narration_apply.py:1771`) runs the three-step lookup. Steps 1+2 match on **name only** (casefold exact, then `_npc_name_match_keys` comma-flip — lines ~1862-1879 / ~1966-1979); neither consults `npc.creature_id`, `npc.aliases`, or any descriptor→entity mapping. A re-described threat fails both and falls to the Step-3 novel-mint at line 2035, appending a fresh `NpcPoolMember(drawn_from="narrator_invented")` at ~2165 — once per re-description.

**Recommended seam (deterministic core + accretion):**
1. Add `NpcPoolMember.creature_id: str | None = None` (`npc_pool.py:27`; pydantic default, no save migration) and set it at Step-3 creature mint time from `creature_data` or the `_synthetic_creature_dict` slug (`narration_apply.py:1083-1100`). `Npc.creature_id` already exists (`session.py:216`, landed via 83-1 / PR #678 — **merged prerequisite, verify before relying on it**).
2. In Steps 1 and 2, add a tertiary check after comma-flip fails: slug-of-`mention.name` vs `npc.creature_id` / `member.creature_id`, plus an `npc.aliases` sweep in Step 1 (aliases exist at `session.py:188`, fed by `accrete_npc_aliases`, imported at `narration_apply.py:28`). Inline within the existing loop structure — don't add a separate function that breaks the `continue` flow.
3. **On reconciliation hit, accrete the new descriptor as an alias** onto the matched entity (84-2 pattern) so subsequent turns match cheaply by alias.
4. **Known gap the slug alone can't close:** a *different* descriptive name ("The Unseen Watcher" vs "Cowardly Lion") produces a different slug. The first re-description turn needs an additional signal — narrator continuity flag on the mention, and/or a conservative "one active unnamed creature-threat per scene" preference for `is_creature=True` pool members in the current confrontation context. This is the design decision TEA/Dev must make; keep it conservative (no false merges — AC4).

**Reuse, don't reinvent:** `creature_id` slug equality (deterministic, load-bearing key), `_npc_name_match_keys` comma-flip, `npc.aliases` + `accrete_npc_aliases`, `alias_resolution._phrase_matches` (`alias_resolution.py:29`, already imported) only where phrase-in-text matching is genuinely needed. No new fuzzy/substring matcher.

**OTEL:** reuse `npc_referenced_span` (`telemetry/spans/npc.py:370`) with a new `match_strategy="creature_id_reconciled"`, and add a dedicated `SPAN_NPC_CREATURE_RECONCILED` (`npc.creature_reconciled`, parallel to `npc.creature_preserved` at `npc.py:293`) carrying `descriptor`, `match_key`, `matched_to` — the GM-panel lie-detector row for AC3.

**Do NOT touch (danger zones):**
- Observation-gate ordering invariant (`narration_apply.py:3862-3882`; gate at `session_helpers.py:2075` runs the dialogue-extraction ratification path — orthogonal, upstream-protected by `_assert_observation_gate_preceded_mint`).
- The `is_creature=False` person-namer route and 83-2 culture self-match / unaffiliated-stranger shuffle.
- `world_authored` identity protection (`narration_apply.py:1989-1996`) — on reconcile, the EXISTING entity's identity wins; mimic the existing `apply_overwrite` logic.

**Regression band (must stay green):** `tests/server/test_npc_pool_narration_apply.py` (esp. `test_npc_lookup_shadows_pool_member_with_same_name`), `test_npc_comma_inversion_match.py`, `test_npc_culture_self_match.py` (12 tests), `test_npc_observation_gate.py`, `test_npc_identity_drift.py`, `tests/integration/test_creature_mm_identity_83_1.py` (AC-6 `test_creature_id_stable_across_promotions` is the explicit 83-3 prerequisite).

## Scope
- In scope: reconciliation guard inside `_apply_npc_mentions` (Steps 1/2 tertiary match + Step-3 gate), `NpcPoolMember.creature_id` field, alias accretion on reconcile, the new OTEL span, and tests.
- Out of scope: observation-gate changes, person-side (`is_creature=False`) naming changes, any rework of 83-1 bestiary materialization or 83-2 culture routing, new fuzzy-matching infrastructure.

## Acceptance Criteria
- A recurring threat the narrator re-describes across turns reconciles to a SINGLE persistent identity (existing pool member or authored Npc) instead of minting a new pool member each turn.
- An authored roster Npc (e.g. the Cowardly Lion, disposition 5) is matched and NOT shadowed by a freshly-minted phantom when the narrator references the same creature in prose.
- When reconciliation fires, an OTEL span records the match (incoming descriptor → reconciled identity + the signal used: continuity flag / similarity / scene-guard) so the GM panel can confirm the engine collapsed the duplicates.
- No false merges: two genuinely distinct threats in the same scene stay distinct — the guard is conservative and span-visible, never a silent identity collapse (mirror the comma-inversion match precedent).
- Existing NPC match/ratification behavior (comma-inversion keys, observation gate 49-6) is preserved; a regression test pins that two distinct named NPCs are not collapsed.

---
_Generated by `pf context create story 83-3` from the sprint YAML._
