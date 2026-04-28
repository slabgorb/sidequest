---
story_id: "45-18"
epic: "45"
jira_key: null
workflow: "wire-first"
---
# Story 45-18: encounter.actors registers all combatants, not just player

## Story Details
- **ID:** 45-18
- **Epic:** 45 — Playtest 3 Closeout
- **Jira Key:** (none assigned)
- **Workflow:** wire-first
- **Type:** bug
- **Priority:** p1
- **Points:** 2
- **Repos:** server
- **Branch:** feat/45-18-encounter-actors-all-combatants
- **Stack Parent:** none (standard PR)

## Description

Playtest 3 Orin: encounter.actors=[Orin only] through 6 rounds of combat with Crawling Scavenger. Per-actor damage/momentum tracking impossible. Encounter-start handshake must register every combatant (NPC + player) in the actors array.

**Source:** 37-41 sub-4

## Acceptance Criteria

### AC1: Encounter-start handshake registers all combatants
- [ ] **Call site:** encounter initialization (likely game/encounter.py or server/session_handler.py) must populate `encounter.actors` with EncounterActor entries for EVERY combatant (player + each active NPC)
- [ ] **Current bug:** actors array contains only the player on encounter start
- [ ] **Required fix:** the handshake that builds the encounter from scenario data OR initializes from combat dispatch must register NPC combatants alongside the player

### AC2: Per-actor damage/momentum tracking becomes operational
- [ ] At least one integration test exercises damage tracking across multiple actors
- [ ] At least one integration test exercises momentum tracking across multiple actors
- [ ] Test verifies that separate damage values are recorded per actor (not co-mingled)

### AC3: OTEL observability on encounter init
- [ ] Encounter initialization emits OTEL span tracking `actor_count` (distinct actor names registered)
- [ ] Span includes `combatant_names` list or equivalent for GM panel verification

### AC4: Verification against Playtest 3 regression
- [ ] Integration test using Playtest 3 Orin save (or synthetic equivalent) demonstrates 6-round combat with Crawling Scavenger
- [ ] actors array explicitly includes Crawling Scavenger by name (not just [Orin])

### AC5: No half-wired exports
- [ ] No new `pub` exports without non-test consumers in the same PR
- [ ] All new code in encounter setup path has at least one production call site that exercises it
- [ ] Grep clean on encounter.actors assignment sites (no orphaned mutation points)

## Story Context

### Domain: Encounter Combat System
The encounter model (sidequest/game/encounter.py) maintains a list of EncounterActor objects representing all combatants in a fight. During Playtest 3 (2026-04-19), the actors array was observed containing only the player across 6 full rounds of combat with an NPC (Crawling Scavenger). This prevented per-actor damage and momentum tracking — both the narrator and the game state had no way to track separate HP/momentum deltas for each combatant.

### Root Cause
The encounter-start handshake (the code that initializes or deserializes an encounter from scenario data) must be registering the player but not the NPCs. The fix is likely in one of:
- encounter initialization from scenario (game/encounter.py or similar)
- combat dispatch / encounter start event handler (server/session_handler.py or similar)
- NPC registry population (game/npc_registry.py or similar)

### Integration Points
- **Narrator:** encounters beat on combat state; needs all actors registered for accurate damage narration
- **GM Panel:** OTEL spans should report actor_count and combatant names so Keith can verify the bug is fixed
- **UI:** ConfrontationOverlay reads encounter state; per-actor momentum display depends on all actors being present
- **Protocol:** GameMessage.encounter payload carries the actors array; if only player is wired to the client, UI sees same incomplete picture

### Testing Approach for TEA
The RED test must exercise the entire wire: scenario → encounter start → actors array populated → message sent to client → UI receives all actors. Not just "does the code run" but "does the wire carry the data."

## Workflow Tracking
**Workflow:** wire-first
**Phase:** review
**Phase Started:** 2026-04-28T16:17:03Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28T16:01:06Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->
- **TEA / RED:** Bug source localized — `instantiate_encounter_from_trigger` (sidequest/server/dispatch/encounter_lifecycle.py:49) only registers actors from the narrator's `npcs_present` list. When the JSON extraction drops the adversary (Playtest 3 shape: confrontation=combat with empty `npcs_present`), the encounter starts with `actors=[player only]`. Downstream, `narration_apply.py:688` raises `ValueError("unknown actor 'Crawling Scavenger'")` whenever the narrator's beat selections name an NPC that wasn't registered, OR opponent-side beats are silently dropped, leaving `opponent_metric` stuck at 0 for the entire encounter. Fix path: when `npcs_present` is empty/sparse, fall back to NPCs from `snapshot.npc_registry` whose `last_seen_location == snapshot.location`. Also add `actor_count` + `combatant_names` attributes to the existing `encounter.confrontation_initiated` span (AC3).

### Dev (implementation)
- No upstream findings during implementation. TEA's localization was correct; the registry-fallback fix landed exactly where predicted (`encounter_lifecycle.py`) and the `encounter.confrontation_initiated` span helper already accepted `**attrs`, so no upstream telemetry plumbing was needed.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` — Added `_registry_fallback_npcs` helper that synthesises `NpcMention` entries from `snapshot.npc_registry` filtered by `last_seen_location == snapshot.location`, defaulting to side="opponent" for combat encounters and "neutral" otherwise. Wired into `instantiate_encounter_from_trigger` so the fallback only fires when the explicit `npcs_present` list is empty AND the encounter is not sealed-letter (sealed-letter requires exactly-one explicit opponent and would be corrupted by registry leakage). Added `actor_count` and `combatant_names` (comma-joined string) attributes to the existing `encounter.confrontation_initiated` OTEL span for GM-panel verification (AC3).

**Tests:** 10/10 GREEN on `tests/server/test_encounter_actors_all_combatants.py`. Full server suite: 2685 passed, 44 skipped, 0 failures (50.32s). `ruff check` clean.

**Branch:** `feat/45-18-encounter-actors-all-combatants` (will be pushed)

**Wire verification:**
- AC1 — `_apply_narration_result_to_snapshot` (production caller, narration_apply.py:507) invokes `instantiate_encounter_from_trigger`, which now consults the registry fallback when `npcs_present=[]`. End-to-end test exercises this path.
- AC2 — Per-actor `per_actor_state` and per-side metric independence verified by integration tests that fire opponent-side beats through the same production path.
- AC3 — Span attributes set on the live span returned by the contextmanager; verified via `InMemorySpanExporter` in `test_encounter_init_span_carries_actor_count_and_combatant_names`.
- AC4 — 6-round Orin/Crawling-Scavenger regression test passes.
- AC5 — AST-based grep test confirms no production code outside `encounter_lifecycle.py` constructs `StructuredEncounter(..., actors=...)`.

**Handoff:** To Reviewer (Westley) — adversarial review of 45-18 fix.