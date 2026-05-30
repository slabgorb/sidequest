---
parent: context-epic-72.md
workflow: trivial
---

# Story 72-5: Fix born-hostile disposition default

**Epic:** 72 (NPC Identity Hardening) · **Points:** 2 · **Type:** bug · **Repo:** sidequest-server

## Business Context

An NPC the narrator invents should walk on stage *neutral*, not spitting hostility.
Today the materialization seam stamps a `-20` disposition default — which ADR-020's
band table reads as **hostile** (`< -10`). That default was written for Monster Manual
creatures (encountergen output, ADR-059), where born-hostile is correct: a goblin
ambush *should* spawn at -20. But the same code path also materializes ordinary
narrator-invented people, so a shopkeeper or a passerby the narrator names can spawn
pre-loaded for a fight.

This violates SOUL "Living World": NPCs act on goals and earn their dispositions
through interaction (the ADR-014/020 model the epic's development pipeline revives in
72-1) — they are not *born* hostile by default. For the playgroup this is the
difference between a world that reacts to them and one that arbitrarily snarls. For
the mechanics-first players (Sebastien, Jade), a disposition that materializes from
nowhere is exactly the kind of unexplained number the GM panel exists to expose — so
the corrected spawn must emit a span, not silently flip.

This is the narrowest of the epic's identity-correctness fixes: **change the DEFAULT
only.** Explicit hostility stays intact.

## Technical Guardrails

**Real bug site (line numbers verified — epic context cites stale ~1500 figures from a
pre-edit revision, but they happen to still land correctly):**

- `sidequest-server/sidequest/game/session.py` — `Session._npc_from_patch` at
  **line 1501**. The born-hostile default is **line 1533**:
  ```python
  # Creatures default to hostile (-20), matching encountergen output.
  disposition=-20 if is_creature else 0,
  ```
  `is_creature` (line 1505) is `True` only when the patch carries a creature-shape
  field (`creature_id`, `threat_level`, or `hp`) — i.e. a Monster Manual / encountergen
  patch (ADR-059). A narrator-invented *person* carries none of those, so it *already*
  falls to the `else 0` branch in this exact function.

**Therefore the fix is about provenance, not a blind flip of -20.** Do NOT change the
`-20` for genuine creatures — that default is correct (it matches
`cli/encountergen/encountergen.py:312`). The story is: ensure a narrator-invented,
non-creature NPC reaches `_npc_from_patch` (or whatever seam materializes it) with
`is_creature == False` so it spawns neutral (0), and confirm no path injects a stray
creature-shape field onto an invented person that would mis-flag it as a creature and
drag it to -20.

- ADR-020 band: `> 10` friendly · `-10..10` neutral · `< -10` hostile. Neutral spawn = `0`.
- Disposition lives as `Npc.disposition: int` (clamp ±100) on `session.py`; qualitative
  derivation helper `_disposition_attitude` is in `server/dispatch/opening.py`.
- Narrator-invented NPCs mint as a disposition-free `NpcPoolMember`
  (`narration_apply.py:1293`, `drawn_from="narrator_invented"`) and only acquire a
  numeric disposition at materialization — this seam is where the default applies.

**OTEL (required — server CLAUDE.md OTEL principle):** emit a span recording the spawn
disposition and whether it was the default or an explicit value, so the GM panel can
verify the corrected default fired. NPC spans live in
`sidequest/telemetry/spans/npc.py` (e.g. `SPAN_NPC_REFERENCED`); the existing
disposition-shift span route is the parallel reference. The span is the lie-detector
for "did this NPC spawn neutral or did Claude improvise hostility?"

**Testing — behavioral assertions only (server rule "No Source-Text Wiring Tests"):**
drive `_npc_from_patch` (or the materialization entry point) with real patch fixtures
and assert on the resulting `Npc.disposition` and the emitted span. Do **not** grep
source for the `-20` literal. The wiring test is an OTEL span assertion on the spawn,
per the epic's 72-5 span point.

## Scope Boundaries

**In scope:**
- The DEFAULT disposition a narrator-invented, non-creature NPC receives at
  materialization (neutral `0`, not hostile).
- Preserving born-hostile (`-20`) for genuine creatures (creature_id / threat_level / hp).
- Preserving an explicit narrator-supplied hostile disposition (fix is default-only).
- An OTEL span recording the spawn disposition.

**Out of scope (do NOT touch):**
- The disposition **drift** pipeline — interest increment, tier escalation, emergent
  disposition evolution. That is **72-1**.
- Disposition **preservation on promotion** + load-time `npcs`↔`npc_pool` **reconcile**.
  That is **72-2**.
- Routing invented names through ADR-091 namegen (72-4), pool growth caps (72-6),
  identity-drift overwrite (72-7), OCEAN/belief seeding (72-9).
- The encountergen `-20` creature default (`encountergen.py:312`) — correct, leave it.

## AC Context

No explicit ACs in the story — derived for a trivial-workflow bug fix:

1. **Default → neutral.** A narrator-invented NPC materialized with no explicit
   disposition and no creature-shape field (`creature_id`/`threat_level`/`hp` all
   absent) spawns at disposition `0` (neutral per ADR-020), not `-20`. Behavioral
   assertion on the resulting `Npc.disposition`.

2. **Explicit hostile still hostile.** An NPC whose patch explicitly marks hostility
   (or a genuine creature patch carrying a creature-shape field) still spawns hostile
   (`-20` / its explicit value). The fix changes the *default* branch only; it must not
   neutralize intentional hostility or break Monster Manual creature spawns.

3. **OTEL reflects spawn.** Materializing an NPC emits a span carrying the spawn
   disposition (and, ideally, whether it was the default or explicit), firing on the
   real production path so the GM panel can confirm the neutral default. This span
   assertion doubles as the wiring test.

**Edge — pre-existing saves:** this changes only the spawn-time default for *newly*
materialized NPCs. NPCs already persisted in a save keep their stored disposition; no
migration, no retroactive rewrite. Reconciliation of existing stores is 72-2's concern,
not this story's.

## Assumptions

- The materialization seam for narrator-invented NPCs is `_npc_from_patch`
  (`session.py:1501/1533`); if a narrator-invented person reaches a *different* seam
  (e.g. `_promote_pool_member_to_npc` in `narration_apply.py:916`) that injects its own
  disposition default, that seam's default must be neutral too. Verify the live path
  during implementation rather than assuming line 1533 is the only one.
- `is_creature` is the existing, correct discriminator between "born-hostile creature"
  and "neutral person." If a narrator-invented person is being mis-flagged as a creature
  (stray `hp`/`threat_level`), that mis-flag is the bug to fix — not the `-20` constant.
- Neutral = exactly `0` per ADR-020's `-10..10` band; `0` is the canonical neutral spawn.
- A `disposition` OTEL span (or extension of an existing NPC/disposition span) is the
  accepted wiring proof; no new dashboard work is in scope.
