---
id: 129
title: "N-Seat Table Engine — Generalized Sealed-Commit Loop for Poker/Auction with Cheat/Accuse Mechanics"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [33, 77]
tags: [game-systems, genre-mechanics]
implementation-status: live
implementation-pointer: null
---

# ADR-129: N-Seat Table Engine

> **Documents a system already live in code.** The free-for-all N-seat table
> engine (`sidequest/game/table/`) — the generic decision-point loop, the
> poker and auction game kinds, the NPC auto-commit policy, and the
> cheat/read/accuse sub-game — shipped during the 2026-05-29 table work
> without a governing ADR. This record closes that architecture-of-record gap
> and states what the decision *was*. See
> `docs/superpowers/specs/2026-05-29-free-for-all-n-seat-table-design.md`.

## Context

SideQuest already ships two structured-encounter resolution shapes. ADR-033's
**Confrontation engine** (`ruleset/native.py`) advances a single shared metric
(tension, leverage, separation) toward a threshold via narrator-selected beats —
a *cooperative-or-adversarial-but-public* model with one dial. ADR-077's
**Dogfight** added a `sealed_letter_lookup` resolution mode: two pilots each
commit a maneuver privately, the engine looks up the cross-product cell, and
applies per-actor deltas. That commit-and-reveal protocol is the right shape for
hidden simultaneous decisions — but ADR-077 explicitly scoped it to **two
actors** with a **hand-authored 16-cell interaction table**, and called a
3-player table "impractical to hand-author" (8³ = 512 cells).

A poker hand or a sealed-bid auction is a *third* decision shape that neither
covers:

- **N seats, not 2.** A poker table seats 3–6; an auction can seat any number.
  The 077 cross-product table does not generalize to N.
- **Per-seat hidden private state, not a shared metric.** Each seat holds its
  own dealt hand / secret valuation. There is no single dial — the "metric" is
  each seat's own strength, compared only at showdown.
- **Multi-decision-point with attrition.** Seats fold across several betting
  rounds; the hand ends when ≤1 seat remains or a decision-point cap is hit.
- **A bluffing/forgery/detection sub-game.** Cheating manipulates the *real*
  hidden state and leaves *real* evidence; other seats can read the table and
  accuse a suspected cheat. This is honest crunch where it is dramatic —
  Sebastien and Jade can see real card math, real trace accumulation, and a
  real opposed catchability roll in the player-facing surface.

Folding this into ADR-033's single-dial confrontation would force per-seat
hidden hands and a deck through a stringly-typed shared-metric contortion — the
exact thing ADR-033 was built to avoid, in reverse. Folding it into ADR-077's
2-actor cross-product table does not scale past two players. The decision shape
is genuinely distinct, so the engine gets a distinct category.

## Decision

**Add a generic N-seat table engine as a distinct encounter category. It
generalizes ADR-077's sealed-letter commit from "keyed by role" (two pilots) to
"keyed by seat" (N players), resolves one decision point at a time against
per-seat private state, and dispatches kind-specific behavior (deal, strength,
cheat, read) through a fail-loud registry. Two concrete kinds ship: `poker` and
`auction`.**

### The N-seat loop

`engine.py::resolve_table` resolves **one** decision point
(`engine.py`). It applies each committed action in resolution `order`,
ignoring folded/out seats (`engine.py`), then decides whether the hand
goes to showdown — `len(active) <= 1 or decision_point >= max_decision_points - 1`
(`engine.py`) — or advances `decision_point` and returns
(`engine.py`). `deal_table` enforces **≥2 seats** before dealing
(`engine.py`); a one-seat table raises `TableNeedsOthersError`, which
"generalizes ADR-116" (`types.py`) — no solitaire table.

Pot/bid actions (`bet`, `raise`, `call`, `bluff`, `raise_bid`) accumulate into
`pot.contributions[seat_id]` and mirror the standing bid into
`private_state["_current_bid"]` so the auction kind can read it without knowing
the pot directly (`engine.py, 110-118`). The dual tension dials are never
touched — the engine reads/writes only `table_state` (module docstring,
`engine.py`).

### Sealed-commit generalization (from ADR-077)

`TableCommit` (`types.py`) is one seat's sealed action for a decision
point. Its docstring is explicit: it *"Generalizes the dogfight sealed-letter
commit from 'keyed by role' to 'keyed by seat'"* and *"Rides the existing
`beat_selections` channel"*. `seat_id` is the actor's party→seat mapping,
`beat_id` the authored action, `amount` the raise/bet chips, `target_seat` the
read/accuse target. `TableState` (`types.py`) is the *general*
free-for-all — `seats`, a `pot`, a resolution `order` — and is **ephemeral**: a
single dramatic hand, never persisted across hands (`types.py`). What lets
poker and auction share one model is `TableSeat.private_state`
(`types.py`): an opaque dict the kind-specific resolver interprets (poker
hand vs auction valuation). Auction proves the generalization with **zero
`TableState` changes** — same seats + pot + order, only different
`private_state` keys and beats (`auction.py`).

### Cheat / read / accuse sub-game

Signature beats dispatch through `_apply_signature_beat` (`engine.py`):

- **`cheat`** — `game.cheat()` mutates the seat's *real* private state. Poker
  swaps the weakest card for a better fresh draw, recomputes real strength, and
  *only keeps the swap if it genuinely helps* — a cheat must never sabotage the
  cheater (`poker.py`). Evidence is a scalar `cheat_trace` that climbs
  and **compounds** on repeated cheats (`prior + 0.3 + rng.random()*0.15`,
  clamped to 1.0, `poker.py`).
- **`read_table` / `read_room`** — `game.read()` returns the target's *real*
  `strength_band` and flags a suspicious trace when it exceeds a
  reader-stat-scaled threshold (`poker.py`). The intel is delivered into
  the **reader's own** `private_state["read_intel"]`, accumulating across reads,
  so the perception firewall routes it to the reader's private frame and hides
  it from everyone else (`engine.py`).
- **`accuse`** — RECORDED at commit time but **ROLLED at showdown**
  (`engine.py`, `_showdown` `engine.py`). The opposed check is
  `accuser_d20 + perception >= 10 + concealment - round(cheat_trace * 8)`
  (`engine.py, 197-199`). Because it rolls against the **final** trace, a
  cheat committed in a *later* decision point is still catchable. A landed
  accusation forfeits the exposed cheat regardless of hand strength; a **false
  accusation forfeits the accuser** — slandering an honest seat costs you the
  hand (`engine.py`).

### NPC policy

`npc_policy.py::decide_npc_commit` (`npc_policy.py`) gives NPC seats a
real decision basis, not narration whim: a policy over (own `strength_band`, pot
size, OCEAN/disposition) returns a `TableCommit`, deterministic under a seeded
rng. Confident/low-neuroticism seats slow-play strong hands or bluff weak ones;
anxious seats fold early; a **larcenous** disposition is likelier to cheat. The
policy is **kind-general**: it maps abstract intents (drop-out / aggressive /
passive / bluff / cheat) onto beats present in `available_beats`
(`npc_policy.py, 110-175`), so an auction NPC can *never* emit a poker-only
`cheat` beat the auction kind doesn't implement.

### Registry

`registry.py` holds per-kind `TableGame` resolvers (`deal`, `strength`, optional
`cheat`/`read`). Kinds register at import (`poker.py`, `auction.py`); an
unknown `game_kind` raises `UnknownTableGameError` — **no silent default game**
(`registry.py`). Cheat/read are `NotImplementedError` by default so a kind
opts in (`registry.py`); auction deliberately registers neither
(`auction.py`).

## Invariants / Contracts

- **Per-seat `private_state` isolation.** Each seat's hand/valuation and its
  accumulated `read_intel` live only in that seat's `private_state`
  (`types.py`, `engine.py`). Reads deposit intel into the
  *reader's* state; the perception firewall (`project_table_frame_for_seat`)
  routes each seat's private frame and hides it from the others. `ReadResult.info`
  must be treated read-only post-construction because the firewall depends on it
  (`types.py`).
- **Deferred accusation at showdown.** Accusations are appended to
  `pending_accusations` at commit and resolved only in `_showdown`, rolled
  against the **final** `cheat_trace` (`types.py`, `engine.py,
  187-214`). An accusation against a seat that has left the table lapses
  silently-by-design (the seat is gone, `engine.py`).
- **False-accusation forfeit.** Exactly one party eats the cost of every
  accusation: the target if the check lands, the accuser if it misses
  (`engine.py`).
- **Fail-loud strength.** `_showdown` calls `game.strength()` on every
  contender (single- and multi-contender alike) and propagates a missing-key
  error as a loud `ValueError` — *never a coin-flip default*
  (`engine.py`). A showdown with zero eligible contenders also raises
  (`engine.py`).
- **Commits validated before mutation.** A commit naming an off-table seat
  raises before anything is applied, so a ghost commit can't leave a
  half-applied hand (`engine.py`).
- **≥2 seats.** No solitaire table (`engine.py`, generalizing ADR-116).

## Observability

Per the OTEL Observability Principle (the GM panel is the lie detector), every
seat-level subsystem decision emits exactly one span, defined in
`sidequest/telemetry/spans/table.py` and routed for the GM panel:

- `table.dealt` — seat_count, game_kind, stake_kind (`table.py`)
- `table.seat_seeded` — seat_id, party_name, is_pc, keys_seeded
  (`table.py`)
- `table.commit` / `table.npc_commit` — seat, beat_id/chosen_beat, amount/pot,
  strength_band (`table.py`)
- `table.cheat` — seat, strength_before, strength_after, new_trace
  (`table.py`, fired at `engine.py`)
- `table.read` — reader, target, info_returned (`table.py`,
  `engine.py`)
- `table.accuse` — accuser, target, accuser_total, **dc**, **landed**
  (`table.py`, fired in `_showdown` at `engine.py`)
- `table.fold` — seat, decision_point (`table.py`, `engine.py`)
- `table.showdown` — winner, forfeits, pot_awarded, revealed_strengths
  (`table.py`, `engine.py`)

Narration claiming "you catch him palming an ace" with no `table.accuse` /
`table.cheat` span is a logged mismatch via `dispatch_engagement_watcher`
(`table.py`). The `table.cheat` span carries before/after strength and the
new trace so the GM panel can confirm a cheat *actually* changed the hand rather
than the narrator inventing one.

## Consequences

**Positive**

- Poker and auction (and future N-seat games) share one ephemeral model and one
  loop; a new kind is a `TableGame` registration, not a new encounter type.
- Mechanics-first players get genuine, legible crunch: a real 52-card deck dealt
  without replacement, a real packed hand ranking (`poker.py`), real trace
  accumulation, and a real opposed catchability roll.
- The cheat/accuse sub-game makes bluffing *mechanical*, not improvised — the
  deferred-at-showdown roll against the final trace gives "I'll catch you
  eventually" real teeth.
- Every seat decision is observable; the GM panel can distinguish an engaged
  engine from narrator improvisation.

**Negative / cost**

- A third structured-encounter category now exists alongside ADR-033 dials and
  ADR-077 sealed-letter lookup; contributors must know which shape an encounter
  uses.
- `private_state` is an opaque typed-dict escape hatch (the same trade-off
  ADR-077 made with `per_actor_state`); kind correctness rests on each
  resolver's discipline plus the fail-loud strength guard, not a static schema.
- The NPC policy's ultimate `next(iter(available_beats))` fallback is
  order-nondeterministic across process restarts; latent today because poker and
  auction both author a drop-out beat, but new kinds should author `fold` or
  `withdraw` (`npc_policy.py`).

## Alternatives considered

- **Fold into ADR-033's confrontation engine.** Rejected: a poker hand has no
  single shared dial — it has N hidden per-seat hands compared only at showdown,
  plus multi-round fold attrition. Expressing that as one metric would be the
  stringly-typed contortion ADR-033 exists to prevent, in reverse.
- **Fold into ADR-077's dogfight sealed-letter lookup.** Rejected: 077 is
  scoped to **two** actors and a hand-authored cross-product cell table; 077
  itself called N-player cross-products "impractical to hand-author" (8³ cells).
  Poker/auction need N seats resolved against per-seat private strength, not a
  2-actor lookup. The table engine *reuses 077's commit-and-reveal idea* and
  generalizes it, rather than living inside 077's table.
- **Pure-content (narrator resolves the hand from prose).** Rejected on SOUL
  grounds, same as ADR-077: an LLM cannot be trusted to deal a fair deck,
  accumulate trace honestly, or run an opposed catchability roll. The deck math,
  trace scalar, and accuse DC exist precisely so the engine — not the narrator —
  owns the truth.

## Reconciliation with ADR-033 and ADR-077

- **ADR-033 (Confrontation engine — `native.py`):** unaffected. The table engine
  does not touch the tension dials (`engine.py`) and is not a confrontation
  metric. It is a sibling encounter category, dispatched separately, that a
  confrontation definition can invoke via the table game registry. ADR-033's
  single-dial model survives intact for tension/leverage/separation encounters.
- **ADR-077 (Dogfight sealed-letter):** **generalized, not superseded.** ADR-077
  established the sealed-commit protocol for two actors with a cross-product
  lookup; the table engine takes the same commit-and-reveal contract — riding
  the same `beat_selections` channel (`types.py`) — and lifts it to N
  seats resolved against per-seat private state instead of a 2-actor cell table.
  Dogfight remains the right tool for 1v1 maneuver duels; the table engine is the
  right tool for N-seat hands. Both descend from the sealed-letter idea; neither
  replaces the other.
- **ADR-116 (Confrontation requires an Other):** honored and generalized — the
  ≥2-seat guard (`TableNeedsOthersError`) is the table-engine expression of
  "no encounter without an other" (`types.py`).
