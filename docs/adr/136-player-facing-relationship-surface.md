---
id: 136
title: "Player-Facing Relationship Surface — Reactive RELATIONSHIPS Projection, Disposition Beat-Log, and the Claims-Only Belief Firewall"
status: accepted
date: 2026-06-01
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [14, 20, 26, 27, 40, 42, 53, 79, 104, 105]
tags: [game-systems, frontend-protocol, npc-character, multiplayer]
implementation-status: deferred
implementation-pointer: "docs/superpowers/specs/2026-06-01-npc-relationship-panel-design.md"
---

# ADR-136: Player-Facing Relationship Surface — Reactive RELATIONSHIPS Projection, Disposition Beat-Log, and the Claims-Only Belief Firewall

> **Documents a decision governing upcoming work, not live code.** No
> relationship panel, `RELATIONSHIPS` message, disposition beat-log, OCEAN
> materialization, or claims filter exists yet. This ADR records the
> architecture agreed during brainstorming (2026-06-01); the implementation
> plan derives from the design spec at the implementation pointer above.

## Context

NPC relationship state is tracked server-side but is **invisible to the player**.
The the_real_mccoy playtest (2026-06-01) confirmed the disposition dial moves
correctly (Dr. McCoy 19, Tabitha 24, Teague 10) yet none of it reaches the table:

- `Npc.disposition` (the `Disposition` wrapper, −100..+100 + `.attitude()`, ADR-020),
  `last_seen_turn`, `last_seen_location`, and `non_transactional_interactions` are
  **server-only** — never serialized to player clients.
- The only `disposition` string the client receives (`ScrapbookEntryNpcRef`) is a
  **narrator prose tag** from `npcs_present[].role`, not the mechanical object.
- Disposition **deltas** exist only as transient OTEL spans
  (`SPAN_DISPOSITION_SHIFT`) — no persisted history of *why* a relationship moved.
- `Npc.ocean` (ADR-042) is `dict | None`, **P5-deferred and never runtime-populated**;
  authored OCEAN landed on `AuthoredNpc` content (`sidequest-content #318`) but is
  not materialized onto runtime NPCs.
- `Npc.belief_state` (ADR-053) is live but holds spoiler-bearing `Fact`/`Suspicion`
  entries (the whodunit, e.g. the_locked_study).

This surface sits on a genuine doctrine fault line. **ADR-040 ("Narrative
Character Sheet — No Raw Stats")** and the perception firewall (ADR-104/105)
deliberately coarsen the disposition integer to an attitude band for player views.
But CLAUDE.md's "Who This Is For" requires that **mechanics-first players
(Sebastien/Jade) can see the math in player-facing surfaces.** A relationship
panel must serve both the narrative players (James/Alex) and the mechanics-first
players without leaking ADR-053 mystery solutions.

## Decision

Build a player-facing relationship surface on five decisions:

**1. Hybrid fidelity (reconciles ADR-040 with the mechanics-first directive).**
The resting display is a **narrative attitude band** with a trend arrow
(ADR-040-compliant). The **raw disposition integer and recent deltas are revealed
on demand** (progressive disclosure / expand). The math is opt-in, not the default
— narrative players see a band, mechanics-first players pop the number. The same
hybrid governs OCEAN: a narrative **personality read** by default, the numeric
`OceanProfile` (0..10) on a further expand.

**2. A dedicated reactive `RELATIONSHIPS` message — not an extension of
`PARTY_STATUS` or `SCRAPBOOK_ENTRY`.** This follows the existing per-domain
message+panel pattern (KNOWLEDGE, LOCATION, MAP each have their own reactive
message and dockview panel, ADR-026/027). It is emitted **when the relationship
set changes** (a disposition shift, a new NPC promoted into the stateful roster, a
claim recorded) — not every turn — honoring *Cost Scales with Drama* (SOUL.md). It
isolates the spoiler firewall in one projection stage rather than smearing it
across the party payload.

**3. A persistent per-NPC disposition beat-log.** Add `Npc.disposition_log` — a
bounded ring buffer of `DispositionBeat {turn, delta, reason, location}` — appended
via a single `Npc.record_disposition_beat(...)` seam at the **existing**
disposition-shift sites (the `develop_npc_on_engagement` interest tick and the
`update_npc_disposition` tool, which already carries the narrator's `reason`). This
**persists the delta + reason the engine already computes** — no new mechanical
computation; it rescues data that today lives only in transient OTEL spans. Every
append emits a `relationship.beat_recorded` span (the GM-panel lie-detector
confirms the history is written, not improvised — CLAUDE.md OTEL principle). This
is what makes the surface a relationship *story* (ADR-014 diamonds/coal), not a
reputation bar. Trend is **derived**, not stored (sign of summed deltas in the
recent scene-window).

**4. OCEAN materialization wires the authored half to runtime.** Extend the
authored-NPC materializer (the seam `worlds/<world>/npcs.yaml` flows through to
`snapshot.npcs`, the path #318 populated) to copy `AuthoredNpc.ocean` →
`Npc.ocean`, normalizing the authored 0..1 scale to the runtime `OceanProfile`
0..10 (mirroring the 72-9 seeding shape for narrator-invented NPCs). NPCs with no
authored OCEAN keep `ocean=None` and the panel shows no personality read —
**absence is shown as absence, never fabricated** (No Silent Fallbacks).

**5. The claims-to-party-only belief firewall is the spoiler boundary.** At
projection, `belief_state.beliefs` is filtered to **`Claim` entries only** (things
the NPC has openly expressed to the party) plus a coarse credibility hint. **All
`Fact` and `Suspicion` entries are dropped** — they are the mystery's solution. A
test plants a `Fact` and a `Suspicion` and asserts neither crosses the firewall.
This is the load-bearing rule that lets belief depth be shown at all in a mystery
world.

The projection runs as a new `RelationshipProjectionStage` composing with the
ADR-104/105 firewall chain, building one `RelationshipEntry` per NPC in
**`snapshot.npcs`** (the promoted, stateful roster — people the party has actually
engaged, ADR-014; **not** the transient `npc_pool`). Disposition and OCEAN are
**global** (a single scalar / single profile — the NPC's stance/personality toward
the party); per-PC standing is explicitly out of scope (YAGNI). The 5-level display
band (Hostile/Cool/Neutral/Warm/Devoted) is a **presentation label computed at
projection** and does not alter the engine's 3-level `Attitude` enum.

## Consequences

**Positive.**
- The relationship state the engine already computes becomes visible — closing the
  playtest gap and serving the relationship-driven play Keith wanted to explore.
- Both audiences are served from one surface: narrative band by default, math on
  expand (the hybrid).
- The beat-log gives durable, player-visible *why* behind each shift — and a second
  OTEL lie-detector (`relationship.beat_recorded`) on a subsystem that previously
  only emitted ephemeral spans.
- Mystery integrity is preserved by construction: the claims-only filter means
  private NPC knowledge can never reach the panel, even for the murderer.
- OCEAN authoring (#318) stops being dead data — it materializes onto runtime NPCs.

**Negative / costs.**
- Net-new engine surface: a model field + ring buffer, a materializer seam, a
  projection/firewall stage, a new typed message + reactive emitter, and a new
  dockview panel + client slice. Larger than the "pure-UI" framing the gap was
  first filed under (the relationship math was never on the wire).
- `record_disposition_beat` must be called at **every** disposition-mutation site;
  a missed site silently drops history. Mitigated by routing all mutations through
  the one seam and an OTEL/wiring test, but it is a standing coupling.
- The 5-level display band diverges from the engine's 3-level `Attitude`; two band
  vocabularies now coexist (engine semantics vs. presentation label). Kept
  deliberately separate so presentation tuning never touches engine thresholds.

**Neutral.**
- Disposition stays global. If per-PC standing is ever wanted (a PvP or split-party
  need), it is a separate, larger ADR — this design does not foreclose it but does
  not build for it.

## Alternatives considered

- **Extend `PARTY_STATUS` with an `npcs[]` array (sibling to companions).**
  Rejected: that message is the *player's party*; relationships are a different
  domain with a different emission cadence, and folding the spoiler firewall into
  party projection couples two concerns. The dedicated message follows the
  established per-domain pattern instead.
- **Extend `SCRAPBOOK_ENTRY` NPC refs.** Rejected: the scrapbook is transient,
  per-turn scene metadata (ImageBus/gallery) — the wrong home for durable
  relationship state and beat history.
- **Band-only (strict ADR-040), no number.** Rejected: withholds exactly the math
  Sebastien/Jade asked for; the panel would be prose, not mechanics.
- **Raw numbers always (no band).** Rejected: contradicts ADR-040 head-on and
  reduces every NPC to a reputation bar to grind.
- **Show full `belief_state`.** Rejected: leaks ADR-053 mystery solutions — the
  murderer's private guilt-knowledge would become a panel row.
- **Per-PC disposition.** Rejected (YAGNI): disposition is a single scalar today;
  per-PC standing is a much larger engine change with no current table need.

## Implementation pointer

`docs/superpowers/specs/2026-06-01-npc-relationship-panel-design.md` — full design
with the data shapes, the three engine seams, the projection stage, the dockview
panel registration, and A/B/C implementation phasing (Phase A: visibility +
beat-log; Phase B: OCEAN; Phase C: claims). Implementation-status is **deferred**
until the plan is executed.
