---
parent: context-epic-75.md
workflow: tdd
---

# Story 75-10: Wire player-NPC reference signal into the budgeted working-set brief tier (75-2 carryover, ADR-118)

## Business Context

Epic 75's budgeted NPC working-set (75-2) replaced the verbatim `npc_pool`
dump in the narrator prompt with a three-tier roster: **scene-present NPCs get
full profiles** (the deterministic floor, ADR-118 D4), **off-stage NPCs the
player just referenced get a brief name+role line**, and **everyone else
collapses to a compact name-only list**. The brief tier exists, is unit-tested,
and is reachable through the API — but it **never fires in production**, because
the production turn-build path passes `player_referenced_npcs=None`. The result:
when a player says "find the blacksmith Joran" and Joran is off-stage, Joran
renders as a bare name, stripped of the role context the narrator needs to keep
him consistent. This story closes that gap so the narrator gets the role tag for
the very NPCs the player is engaging — without re-inflating the prompt back to
the verbatim dump 75-2 removed. It directly serves Genre Truth / Living World:
off-stage NPCs the table cares about stay legible to the narrator.

This was explicitly deferred from 75-2 (logged as a Dev deviation + two TEA
findings) pending ADR-118's fill orchestration (75-5), which is now landed and
provides the natural per-turn signal source.

## Technical Guardrails

**Key files (sidequest-server):**
- `sidequest/agents/npc_context.py` — `build_npc_working_set(snapshot, *,
  current_turn, player_referenced_npcs=None, recency_window=2)`. **Do not change
  the tiering logic** — it is correct and tested. This story only changes what
  gets *passed in* for `player_referenced_npcs`.
- `sidequest/server/session_helpers.py` / `session_handler.py` — `_build_turn_context`
  is where `player_referenced_npcs=None` is hardcoded today. This is the seam to
  wire.
- `sidequest/telemetry/spans/npc.py` — `SPAN_NPC_WORKING_SET` ("npc.working_set")
  already emits `full_count` / `brief_count` / `compact_count` / `total_pool` /
  `references_present`. No span changes needed; the wiring just makes
  `references_present=true` reachable in prod.

**Signal-source rule (load-bearing):** The reference signal must derive from
**player input, pre-turn**. Do **not** reuse `_apply_npc_mentions`
(narration_apply.py) — it reads NARRATOR output *post-turn*, which is the wrong
phase and would tag NPCs the narrator invented, not ones the player referenced.

**Prefer reuse over a new extractor:** ADR-118's `retrieve_turn_context` (75-5)
is the per-turn fill orchestration and likely already computes a referenced-
entity set from player input. First check whether the player-reference signal
can be *sourced from 75-5's retrieval result* before building any new NPC-name
matcher. Don't reinvent — wire up what 75-5 already surfaces.

**Perception firewall (ADR-104/105):** unchanged. The brief tier emits no
disposition; the full tier emits only the coarsened attitude band. Do not let
the wiring leak raw disposition or any per-recipient-private field.

## Scope Boundaries

**In scope:**
- Replace the hardcoded `player_referenced_npcs=None` in the production
  `_build_turn_context` path with a real set derived from player input
  (sourced from 75-5's retrieval result where possible).
- Make the brief tier fire in production: referenced off-stage NPC → name+role.
- A wiring/integration test driving the **real** `_build_turn_context` path
  (not a direct `build_npc_working_set` unit call) proving the signal flows
  end-to-end, including the OTEL assertion.

**Out of scope:**
- **Per-entity reference *promotion*** (referenced off-stage NPC → *full*
  profile). Brief-vs-compact only. Promotion was logged as a separate concern in
  75-2 and is not this story.
- Changing the tiering thresholds, recency window, or the scene-present full
  floor.
- Any change to `SPAN_NPC_WORKING_SET` attributes or the working-set dataclass.

## AC Context

1. **`_build_turn_context` supplies a real `player_referenced_npcs` set from
   player input**, replacing the hardcoded `None`.
   - *Pass:* the production turn-build call to `build_npc_working_set` receives a
     non-`None` set whose contents trace to the player's submitted action for
     that turn.
   - *Edge:* a turn that references no NPC must pass an empty set (or the
     established no-reference sentinel), NOT `None` — and must still render
     scene-present NPCs full and off-stage compact.

2. **Referenced off-stage NPC renders in the BRIEF tier (name+role), not
   compact** — verified against the real turn-build path.
   - *Test:* drive `_build_turn_context` with a snapshot containing an off-stage
     NPC (last_seen_turn < current_turn - recency_window) and a player action
     referencing that NPC; assert the NPC lands in `brief_entries`, not
     `compact_names`.

3. **The scene-present FULL floor is unchanged (reference-independent).**
   - *Test:* a scene-present NPC stays in `full_profiles` whether or not the
     player references it; referencing must never demote, not-referencing must
     never demote.

4. **OTEL: `SPAN_NPC_WORKING_SET` emits `references_present=true` and
   `brief_count>0`** on a production-path turn where the player references an
   off-stage NPC. (OTEL Observability Principle — the GM panel must be able to
   prove the brief tier fired; today `references_present` is always false in
   prod.)

5. **Wiring test:** at least one integration test exercises the real
   `_build_turn_context` production path (not a synthetic direct unit call) to
   prove the signal flows action → turn-context → working-set → brief tier →
   span, end to end.

## Assumptions

- **75-5 (`retrieve_turn_context`) is merged and surfaces a per-turn referenced-
  entity set derived from player input.** If 75-5's result does *not* expose a
  usable player-reference signal, log a Design Deviation and notify SM before
  building a standalone extractor — the choice of signal source changes the test
  surface.
- The off-stage classification (`last_seen_turn >= current_turn -
  recency_window` → scene-present; else off-stage) is stable and correct as of
  75-2; this story does not retune it.
- A referenced NPC that is a `NpcPoolMember` (never full) correctly promotes
  compact→brief, same as a stateful off-stage `Npc`. Pool members never reach
  full regardless of reference.
