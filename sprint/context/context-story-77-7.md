---
parent: context-epic-77.md
workflow: tdd
---

# Story 77-7: Engine lull-escalation — drive a Bang/complication when turns_since_meaningful climbs (ADR-024/025/128)

> Source: sq-playtest ping-pong GAP "Engine is passive — no Bang/complication injection
> during lulls ('had to prod to get the action going')" (wry_whimsy/gulliver, session
> 2697). Found by Keith + Dev (Naomi). The **content half** (the empty Bang catalog) is
> story 77-6 (author the `wry_whimsy` seed_tropes deck, ADR-128) — already PR'd as
> content #347. **This story is the engine half: making the engine PUSH.**

## Business Context

Keith's one craft note from a 36-turn gulliver session: *"had to prod a bit to get the
action going."* Both set-pieces — the social confrontation (rounds 7–11) and the
wade-out-and-take-the-fleet sequence (rounds 29–33) — were **player-initiated**. The
narrator reacted well but never *drove*. For a forever-GM who wants to be **surprised**,
this is the difference between "fun, but I had to prod" and "fun, and it kept coming at
me." A good human DM names a stake, lands a complication, or has an NPC act on its own goal
during a lull (Living World). The engine didn't.

This is distinct from the durable-memory and quest gaps — it's the **pacing / Bang-injection
spine** (ADR-024 dual-track tension, ADR-025 pacing detection, ADR-128 seed-trope deck).
Even once 77-6 fills the seed catalog, a deck the engine never *deals from* changes
nothing: the deck gives the push something to throw; this story is the throwing.

## Technical Guardrails

**This is a design-first engine story.** The exact escalation seam should be confirmed
against ADR-024/025/128 before implementation — if the design work reveals the need for a
new ADR or a material amendment, raise it as a Design Deviation and route to the Architect
(Neo) rather than forcing a patch. The context below is the *direction*, not a frozen spec.

**The lull signal already exists — wire the escalation onto it:**
- The validator already computes silence: a `coverage_gap` event fires when a subsystem
  hasn't been exercised in N turns (`sidequest/telemetry/validator.py`
  `subsystem_exercise_check`, threshold 10 turns). In session 2697 it fired at turn 29 with
  `subsystem: scenario, silent_turns: 10`. That's the lull, already detected — but it's
  only *reported*, nothing *acts* on it.
- The per-turn pacing/seed state is assembled around `seed_context_builder.py` and
  `session_helpers.py`; `mechanical_census.py` tracks per-round mechanical activity. The
  OTEL evidence shows `next_turn_directives: []`, `active_stakes: ""`, `active_seeds: []`
  during the lull — the machinery had nothing queued and injected nothing.

**Design direction (confirm against the ADRs):**
1. **Track "turns since something meaningful happened"** — a meaningful beat is a fired
   confrontation beat, a quest/stakes change, a witnessed_act, a discovery, etc. (reuse the
   mechanical-census signal rather than inventing a new counter).
2. **When that climbs past a threshold, ESCALATE** — deal from the seed-trope deck (ADR-128,
   now populated by 77-6), name a stake (ADR-137 `set_stakes`), fire a complication, or
   have a present NPC act on its own goal (Living World). The escalation should be a
   *directive the narrator must honor*, not a suggestion it can ignore — engine-first, the
   same doctrine as the IntentRouter (the narrator narrates an already-decided push).
3. **Respect the editor's-eye doctrine** — *Cut the Dull Bits* and *The Guitar Solo*: the
   escalation should raise stakes / force a decision, and in MP should give the table a
   concurrent verb, not drop a solo on a silent band. Don't over-fire (a complication every
   turn is as bad as none) — escalation cadence is part of the design.

**OTEL (mandatory — this is the whole point):** the escalation decision MUST emit a span:
the lull measure that triggered it, what was thrown (which seed / stake / NPC-goal), and
why. Today the scenario subsystem going silent is invisible-as-intent; the fix is only
verifiable if the GM panel can see "lull detected at turn N → injected complication X." A
passive engine and a working engine that happens to have a quiet scene must be
distinguishable on the panel.

**Dependency:** 77-6 (seed deck content) should land first so the engine has a non-empty
deck to deal from — but the escalation logic must degrade gracefully (and observably) when
a pack ships no seeds (name a stake / NPC-goal instead), not silently no-op.

## Scope Boundaries

**In scope:**
- A "turns since meaningful beat" measure (reusing existing mechanical-census/pacing
  signal where possible).
- A lull-escalation step that, past threshold, injects a Bang — seed-trope deal, named
  stake, complication, or NPC-acts-on-goal — as a narrator-honored directive.
- The escalation OTEL span (trigger measure + what was thrown + rationale).
- Cadence control so escalation doesn't over-fire.
- Behavioral tests (fixture-driven + OTEL span) proving: a synthetic lull past threshold
  fires an escalation directive + span; a freshly-active scene does NOT escalate.

**Out of scope:**
- Authoring seed-trope content (that's 77-6 / content lane per pack).
- The RAG/durable-memory gaps (story 75-15) and the quest panel (77-5).
- Re-tuning every genre's pacing constants — ship a working default + the seam; per-pack
  tuning is follow-up.
- Narrator prose quality — this story decides *that* a push happens and hands the narrator
  a real directive; how purple the prose is is separate.

## AC Context

1. **Lull is measured.** The engine tracks turns since the last meaningful beat (define
   "meaningful" against the mechanical census) and exposes it (span/state) per turn.
2. **Escalation fires past threshold.** A synthetic session driven past the lull threshold
   produces an escalation directive — a dealt seed-trope / named stake / complication /
   NPC-goal action — that the narrator is required to honor (engine-first).
3. **No false escalation.** A session with recent meaningful beats does NOT escalate
   (assert no directive + no escalation span on an active turn).
4. **Graceful empty-deck degrade.** With no authored seeds, escalation still fires via a
   stake/NPC-goal path and says so on OTEL — never a silent no-op.
5. **OTEL proves it.** The escalation span carries the trigger measure, what was thrown,
   and the rationale; the GM panel can distinguish "engine pushed" from "quiet scene."
6. **Cadence guard.** Escalation does not fire every turn during a sustained lull (a
   bounded cadence, tested).
7. **Wiring test.** Fixture-driven behavioral tests (real pacing path + span), not greps.
