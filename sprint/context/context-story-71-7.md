---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-7: Authored chassis crew silently skipped when chapter seeds placeholder PC

## Business Context

This is a load-bearing SOUL failure for the playgroup. In the live `coyote_star`
session (session_id=76, 2026-05-27), the Kestrel's *authored* crew — Wainu, Hubo,
Kuna-Mikkaan, Kanga, plus matriarch Dura Mendes, all hand-authored in
`sidequest-content/genre_packs/space_opera/worlds/coyote_star/npcs.yaml` — never
hydrate into the live NPC roster at game start.

What the player gets instead:
- `npcs[]` holds only the 7 chapter-authored NPCs (Demiloslava Chop, Troy Goda,
  Cmdr. Yarya, Virki, Vesper, Ther Path, Deckonone) — the *wrong* cast.
- The real crew (Wainu, Kanga, Kestrel) lives as narrator-invented stubs in
  `npc_pool` with no disposition / OCEAN / `last_seen` tracking.
- ZERO `npc.authored_loaded` spans across 999 telemetry rows.

The downstream symptom is the one that hurts the table: the crew the player engages
with for hours has no persistent state backing it, so once the narration window rolls
past their last mention they simply evaporate — the "forget-the-NPCs" failure. This
violates SOUL "Living World" and "Diamonds and Coal." Jade and Sebastien (the
mechanics-first players) carried a 140-turn coyote_star game on relationship and NPC
strength alone; an authored crew that silently fails to persist is precisely the kind
of depth-erosion this group notices.

Compounding the visibility failure: the skip emits **nothing** — a silent fallback,
which CLAUDE.md forbids. The GM panel (the lie-detector) cannot tell whether the crew
loaded or whether the narrator is improvising stubs.

## Technical Guardrails

**Provenance — do NOT re-investigate.** Diagnosed by GM via live save audit, then
root-caused by Dev against a live PostgreSQL reproduction (session_id=76, world
coyote_star, 2026-05-27). The defect reproduces on HEAD; this is not a stale-save
artifact. The root cause is pinned to file:line below.

### Root Cause (file:line pinned)

Ordering / gate bug in the chargen first-commit path.

`sidequest-server/sidequest/websocket_handlers/chargen_mixin.py:728-789`
(the `is_first_commit` branch):
1. **~line 740:** `materialize_from_genre_pack(history_value, CampaignMaturity.Fresh, ...)`
   returns a snapshot that ALREADY contains a chapter-authored "Adventurer"
   placeholder *character* plus the 7 chapter NPCs (the wrong cast).
2. **~line 786:** `preload_authored_npcs(materialized, world.authored_npcs)` is called.
3. **~line 789:** The "Adventurer" placeholder is discarded — but AFTER the preload
   call, one line too late.

`sidequest-server/sidequest/game/world_materialization.py:785-866`
(`preload_authored_npcs`):
- **Gate logic (lines 807-812):** `is_fresh = not state.characters AND turn_manager.interaction == 0`.
- **Bug:** because `materialized.characters` is non-empty (it holds the placeholder
  seeded by `WorldBuilder._apply_chapter` at `world_materialization.py:335`:
  `name = char_data.name if char_data.name else "Adventurer"`), `is_fresh`
  evaluates to False.
- **Result:** silent early `return`. The crew never loads; **no span fires**.

### Fix direction (surgical, do not over-build)

Fix the ordering **or** the freshness gate so that a snapshot carrying only a
chapter-authored placeholder character is still recognized as fresh — e.g. gate on
`turn_manager.interaction == 0` plus absence of a real chargen/player character, or
discard the placeholder *before* the `preload_authored_npcs` call. Add the skip span
in `sidequest/telemetry/span_definitions.py`
(`SPAN_NPC_AUTHORED_LOAD_SKIPPED`, or reuse an existing skip span) so the skip path
is never silent.

### Constraints

- **No silent fallbacks (CLAUDE.md).** The current silent skip is exactly the
  forbidden anti-pattern; the skip path must emit a `reason`-carrying span.
- **OTEL observability mandate (CLAUDE.md).** Every subsystem decision on this seam
  must be visible on the GM panel — `npc.authored_loaded` on load, an explicit skip
  span on skip.
- **Do NOT regress resumed-session behavior.** Resumed sessions (characters present,
  `interaction > 0`) must still skip the preload — but now emit the skip span with a
  reason rather than no-op.
- **Do not drop the chapter NPCs and do not double-register the crew.** The
  chapter-authored cast and the authored crew must coexist correctly.
- **Wiring required (CLAUDE.md).** Prove the preload is reached and the span fires
  end-to-end through the production chargen path — not just a unit call to
  `preload_authored_npcs`. Prefer OTEL-span or fixture-driven behavior tests; no
  source-text grep wiring tests.

## Scope Boundaries

**In scope:**
- Server: fix the chargen first-commit ordering / freshness gate so the authored
  chassis crew (kestrel_captain/engineer/doc/cook + Dura Mendes) materializes into
  the live `snapshot.npcs` roster on a fresh `coyote_star` chargen-confirm.
- Server: add `npc.authored_loaded` emission per crew member on fresh load.
- Server: add `npc.authored_load_skipped` (with `reason`) on the skip path so the
  skip is observable.
- Tests: fixture-driven behavior test through the real handler seam + a wiring test +
  a resumed-session regression guard.

**Out of scope:**
- Redesigning the chargen flow, the `WorldBuilder._apply_chapter` placeholder mechanism,
  or the authored-NPC YAML schema.
- Backfilling crew state into already-broken live saves (session_id=76 etc.) —
  this story fixes go-forward fresh-chargen behavior, not migration.
- npc_pool / narrator-invented-stub promotion logic beyond ensuring the authored crew
  no longer lands there.
- OCEAN / disposition *evolution* mechanics — only correct *initial* dispositions are
  in scope (60/55/50/60/0).

## AC Context

Acceptance criteria copied verbatim from `.session/71-7-session.md`:

1. **Fresh chargen crew materialization:** On a fresh `coyote_star` chargen-confirm
   (first commit), the authored chassis crew
   (kestrel_captain/engineer/doc/cook = Wainu/Hubo/Kuna-Mikkaan/Kanga) AND Dura
   Mendes are materialized into `snapshot.npcs` as runtime `Npc` instances carrying
   their authored `initial_disposition` (60/55/50/60/0 respectively) — NOT left as
   `npc_pool` narrator_invented stubs.

2. **Fix freshness gate:** `preload_authored_npcs` no longer false-negatives when the
   materialized snapshot carries only a chapter-authored placeholder character. Fix
   the ordering or the freshness gate (e.g., gate on `turn_manager.interaction == 0`
   and absence of a real chargen/player character, or discard the placeholder before
   the preload call) — do NOT regress resumed-session skip behavior (resumed sessions
   must still skip preload).

3. **Coexistence:** The chapter-authored NPCs and the authored crew must coexist
   correctly — the fix must not drop the chapter NPCs nor double-register the crew.

4. **OTEL observability (CLAUDE.md Observability Principle + No Silent Fallbacks):**
   - `npc.authored_loaded` (`SPAN_NPC_AUTHORED_LOADED`) fires once per crew member +
     Dura Mendes on fresh chargen.
   - When `preload_authored_npcs` skips (resumed session OR gate-not-fresh), emit
     `npc.authored_load_skipped` with a `reason` field so the GM panel never goes
     blind on a silent no-op.

### Test Guidance (TEA red phase)

**Fixture-driven behavior test:**
- Construct a fresh coyote_star-like genre pack + history with a Fresh-tier chapter
  that seeds a placeholder character.
- Drive the chargen first-commit seam through the real handler path.
- Assert: authored crew present in `snapshot.npcs` with correct dispositions.
- Assert: `npc.authored_loaded` spans fired (OTEL span assertion).
- Reference canonical shape: `tests/server/test_location_description_emit.py`.

**Wiring test:**
- Assert the preload is reached and the span fires end-to-end through the production
  chargen path — not just a unit call to `preload_authored_npcs`.

**Regression guard:**
- A resumed session (characters present, `interaction > 0`) still skips the preload
  AND now emits the skip span with `reason`.

### Files to Modify
- `sidequest/websocket_handlers/chargen_mixin.py` — chargen first-commit handler.
- `sidequest/game/world_materialization.py` — `preload_authored_npcs` freshness gate
  and skip span.
- `sidequest/telemetry/span_definitions.py` — add `SPAN_NPC_AUTHORED_LOAD_SKIPPED`
  definition (or reuse an existing skip span).

## Assumptions

- The authored crew's `initial_disposition` values (60/55/50/60/0 for
  kestrel_captain/engineer/doc/cook/Dura Mendes) are as authored in
  `coyote_star/npcs.yaml`; the fix surfaces them, it does not redefine them.
- The "Adventurer" placeholder is the *only* character present in a fresh-tier
  materialized snapshot prior to chargen confirm; if a fresh snapshot is found to
  carry a real player character before first commit, that widens scope — log a Design
  Deviation and notify SM rather than relaxing the gate blind.
- Epic 71 (coyote_star MP playtest bugfix) governs this story; this fix is a
  go-forward chargen-path correction and does not alter sibling-story turn/socket
  resilience work.
