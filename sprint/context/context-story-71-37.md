---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-37: Classify person-vs-creature at the NPC invention seam — route beasts to the Monster Manual (ADR-059), not the culture-NPC namer

> Source: sq-playtest ping-pong BUG "Wild animals/monsters are routed through the
> culture-NPC namer (person-name + bogus culture) instead of the Monster Manual"
> (wry_whimsy/oz, session `2026-06-03-oz`). Found by Keith + DRIVER/GM.

## Business Context

When the narrator introduces a non-person threat, the invention path
(`npc.invented_name_routed`) mints a **human person-name** and assigns it a **culture**,
even when the subject is a wild animal that belongs to no faction. From the live server log:

- turn 1: `original='The Munchkins' → minted='Roric the Crimson' culture='Quadling'`
  (Munchkins are Munchkin/East, not Quadling)
- turn 8: `original='The Forest Lions' → minted='Clemence Coralfast of the South'
  culture='Quadling'` (a pack of wild lions given a Quadling courtier name)
- turn 9: `original='The Unseen Watcher' → minted='Keeper Goldbraid' culture='Emerald
  City'` (the SAME forest threat re-minted a second time, new name + new culture)

Two coupled defects (Keith's framing):

1. **Wrong subsystem for creatures.** There is no faction that owns random fauna, so the
   culture-NPC namer has nothing correct to return and falls back to a random culture +
   person-name. A wild animal/monster (forest lions, a beast in the dark) should be drawn
   from the **Monster Manual / bestiary (ADR-059, server-side creature pre-generation)** as
   a *creature* (species, threat profile) with **no culture and no person-name**.
2. **Culture mis-assignment even for people.** A named people-group resolves to the wrong
   corpus (Munchkins → `Quadling`; the forest threat → `Quadling` then `Emerald City`). The
   culture router picks the wrong culture even when a person-name *is* appropriate.

**Consequences:** nonsense identities for animals ("Keeper Goldbraid of the Emerald City"
for a lion) and **unstable opponent identity** — one ongoing forest threat was minted as
three different names across two turns (`Clemence Coralfast` → `The Unseen Watcher` →
`Keeper Goldbraid`), and **none** resolved to the authored **Cowardly Lion** sitting in the
`npcs` roster (disposition 5). For the player this reads as the world forgetting who it
just introduced — the inverse of a living world.

## Technical Guardrails

**Seam:** the narrator-invention naming path in
`sidequest-server/sidequest/server/narration_apply.py` —
`_seed_invented_npc_identity` / `_resolve_invented_naming_context` /
`_generate_invented_name`, which emit the `npc.invented_name_routed` span
(`sidequest/telemetry/spans/npc.py`). This is where an invented subject currently gets a
culture-bound person-name unconditionally.

**Reuse what exists — do NOT reimplement creature generation:**
- `sidequest/game/monster_manual.py` already exists (ADR-059, server-side creature
  pre-generation via game-state injection). The fix is **routing** the invention seam to
  it for creature subjects, not building a new bestiary.
- The culture-corpus namer (ADR-091 Markov, `sidequest/corpus/`) stays the path for actual
  **people**; this story does not change how people are named — it (a) stops sending
  *creatures* there and (b) fixes which culture a *people-group* resolves to.

**Three pieces of work:**
1. **Classify the subject at the invention seam** — person vs creature/beast/monster. The
   classifier should be observable (an OTEL attribute on the routing decision), and when
   uncertain must fail toward the safer branch rather than silently minting a person-name
   for a beast (No Silent Fallbacks). Consider: the IntentRouter/narrator already has
   signal about the subject; prefer an existing signal over a brittle keyword list, but a
   conservative noun/plurality heuristic is acceptable if observable.
2. **Route creatures to the Monster Manual** — a creature identity (species, threat
   profile) with **no culture and no person-name**; emit a creature-routed OTEL span (or a
   `routed_to=monster_manual` attribute on the existing span) so the GM panel can see the
   beast went to the bestiary.
3. **Fix culture selection for people** — a named people-group resolves to its OWN culture
   (Munchkin → Munchkin, not Quadling). Investigate the culture router's corpus pick; the
   bug is a wrong-corpus selection, not a naming failure.

**Stability guard:** a single ongoing threat must not be re-minted under a new name every
turn. Once a forest threat is introduced and seated, subsequent references should resolve
to the *existing* entity (and, where an authored roster NPC fits — the Cowardly Lion —
prefer the authored creature over inventing a new one). The OTEL span lines
(`npc.invented_name_routed`) are the evidence trail for both the bug and the fix.

**OTEL (mandatory):** every routing decision at this seam emits a span — at minimum the
person-vs-creature classification, the chosen route (culture-namer vs monster_manual), and
the resolved culture for people. The GM panel must be able to answer "why did this become
a person named X of culture Y, or a creature of species Z?"

## Scope Boundaries

**In scope:**
- Person-vs-creature classification at the narrator-invention seam, observable via OTEL.
- Routing creature subjects to `monster_manual.py` (ADR-059) with a creature identity and
  no culture/person-name.
- Fixing the culture-corpus selection so a named people-group resolves to its own culture.
- A re-mint stability guard so one ongoing threat keeps one identity across turns.
- Behavioral tests (fixture-driven + OTEL span assertions) for: a creature subject routes
  to the bestiary; a people-group resolves to the correct culture; a repeated threat keeps
  its identity.

**Out of scope:**
- Authoring new Monster Manual content / bestiary entries (content lane — flag separately
  if oz needs specific creatures authored).
- Changing the Markov person-name generator itself (ADR-091) — only what gets *sent* to it.
- The ally-seating GAP (story 59-35) — a creature opponent still seats as the Other via the
  existing opponent path; this story is about its *identity*, not its seating.
- Disposition/relationship modeling for creatures beyond what the Monster Manual provides.

## AC Context

1. **Creatures go to the bestiary.** A narrator-invented wild-animal/monster subject
   (e.g. "The Forest Lions", "a beast in the dark") is routed to `monster_manual.py` and
   gets a creature identity (species/threat profile) with **no culture and no
   person-name** — proven by an OTEL span showing `routed_to=monster_manual` (or
   equivalent) on that turn.
2. **People go to the namer with the right culture.** A named people-group (Munchkins)
   resolves to its OWN culture (Munchkin), not a random one — assert the resolved culture
   on the routing span.
3. **Stable identity.** A single ongoing threat referenced across consecutive turns keeps
   one identity (no re-mint to a new name/culture); where an authored roster creature fits
   the introduced threat, it resolves to that authored entity rather than a new invention.
4. **Fail-loud classification.** An ambiguous subject takes the safer branch observably (a
   span attribute records the uncertainty) — never a silent person-name for a beast.
5. **OTEL coverage.** The classification decision, the chosen route, and the resolved
   culture each emit/attribute a span the GM panel can read.
6. **Wiring test.** Fixture-driven behavioral tests (real invention path + span
   assertions), not source-text greps.
