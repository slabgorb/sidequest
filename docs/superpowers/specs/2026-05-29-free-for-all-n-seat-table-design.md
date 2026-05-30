# Free-for-all N-seat Table Model — Design

**Date:** 2026-05-29
**Status:** design (approved in brainstorm; pending spec review → implementation plan)
**Umbrella:** [Spotlight Cardinality roadmap](2026-05-29-spotlight-cardinality-roadmap.md) — this is **Spec 3 of 3** (Specs 1 & 2 pending; see roadmap "do not drop").
**SOUL anchor:** **The Guitar Solo** (`SOUL.md` / `sidequest-content/SOUL.md`, 2026-05-29).

## Problem

A poker table is the one multiplayer scene where the *whole* group should act every round, simultaneously, against each other. The engine has **no model for it.** Today `spaghetti_western` **poker** and `tea_and_murder` **auction** are forced into a two-sided `StructuredEncounter` dual dial (`player_metric` vs `opponent_metric`) — an abstraction that physically cannot represent N independent seats, a shared pot, betting order, or private per-seat hands. With one human it limps; with multiple humans at the same table it is a lie.

This spec adds a **general free-for-all N-seat resolution mode**. Poker is the proving instance; auction is the second; the model is genre-general (a future council vote / derby is a new `game_kind`, not a new subsystem).

## Decisions (locked in brainstorm)

| # | Decision | Choice |
|---|---|---|
| Fidelity | how "real" the simulation is | **Real dealt hands + genuine strength, abstracted betting.** Honest crunch where it's dramatic (Sebastien/Jade can see real card math); smash-cut the betting grind (*Cut the Dull Bits*, Alex-safe). |
| Cadence | how a hand reconciles with the live submit-and-wait barrier | **Simultaneous sealed commit** — every active seat commits at once, revealed/resolved in seat order. Generalizes the dogfight `sealed_letter_lookup` to N seats; fits the existing all-peers barrier; protects the slow typist. Sequential *tension* is recovered in narration, not in turn order. |
| Scene shape | one hand or a session | **Single dramatic hand.** Ephemeral state, no cross-hand stacks. Pot holds one stake (money / item / information / favor, content-declared). Another hand = another confrontation. |
| Signature beats | how mechanical Cheat/Read/Accuse are | **Fully mechanical** — Cheat mutates the real hand + leaves a detectable trace; Read returns real info; Accuse is an opposed check against the trace. |
| Architecture | how the N-seat model seats into the engine | **Additive `StructuredEncounter` extension** behind the ADR-117 ruleset seam (mirrors the ADR-077 dogfight playbook). No new peer type. |

## Architecture & seam

Three additive changes — no new peer type (honors ADR-033/077 unification):

1. **`StructuredEncounter` gains one optional field:** `table_state: TableState | None = None`. Non-table confrontations leave it `None` (as non-dogfight ones leave per-pilot descriptors unused). The dual dials go **unused** for table types — the resolver reads `table_state`, not the metrics.
2. **New `resolution_mode: table_resolution`** + third `win_condition: "table_showdown"` (joins `dial_threshold`/`hp_depletion`). `ConfrontationDef` also declares `table_game: "poker" | "auction"` — the resolver discriminator.
3. **Resolver behind the ADR-117 ruleset seam** — a `resolve_table(...)` method on `RulesetModule` (default in `native.py`). `narration_apply` gets a **new exclusive branch** peer to the `sealed_letter_lookup` branch (`narration_apply.py:~2685`) that routes per-seat commits to it and **never** falls through to `apply_beat` (double-apply guard).

**Commit-channel reuse:** each seat's sealed action rides the existing `beat_selections` list — `actor` = the seat's party, `beat_id` = the authored action (Bet/Raise/Bluff/Call/Fold/Cheat/Read/Accuse) + a params slot for raise amount. Sealed-letter pattern generalized from "keyed by role" to "keyed by seat." Zero new transport.

## State model

```python
class TableSeat(BaseModel):
    model_config = {"extra": "forbid"}
    seat_id: str                    # stable: "seat_1"…
    party_name: str                 # maps to an EncounterActor (PC or NPC)
    is_pc: bool
    status: Literal["active", "folded", "out"]
    private_state: dict[str, Any]   # opaque to the model; read by the kind-specific resolver
    #   poker   → {"cards": [...], "strength": int, "strength_band": str, "cheat_trace": float}
    #   auction → {"valuation": int, "max_bid": int}

class TablePot(BaseModel):
    model_config = {"extra": "forbid"}
    stake_kind: str                 # "money" | "item" | "information" | "favor" (content-declared)
    stake_descriptor: str           # "the deed to the Bar-T" — narration label
    contributions: dict[str, int]   # seat_id → abstract chips (money); current high bid (auction)

class TableState(BaseModel):
    model_config = {"extra": "forbid"}
    game_kind: str                  # "poker" | "auction" — resolver dispatch
    seats: list[TableSeat]
    pot: TablePot
    order: list[str]                # seat_ids in resolution/narration order
    dealer_seat: str
    decision_point: int = 0
    max_decision_points: int        # abstracted betting — small (e.g. 3), content-declared
    resolved_winner: str | None = None
```

**Properties:**
- `private_state` is an **opaque dict** — the model stays the *general* free-for-all (seats + pot + order); only the kind-specific resolver interprets a poker hand vs an auction valuation. This is what lets poker and auction share one model.
- Each seat keeps a normal `EncounterActor` (so perception/barrier plumbing works unchanged); `side` is cosmetic — every seat is its own party.
- **Ephemeral** (single-hand): no cross-hand persistence, no stack bookkeeping.
- **Folded/out seats drop from the barrier denominator** for remaining decision points — reuses the `effective_barrier_count` crash-release machinery (`session_room.py:722`) so a folded player never blocks the table.

## Round lifecycle (data flow)

1. **Instantiate & deal.** Ruleset seats N parties (PCs buying in + NPC gamblers from the location roster). **Invariant (generalizes ADR-116): ≥2 seats**, else `TableNeedsOthersError` (fail loud). Populate each `private_state` (poker → deal + compute strength; auction → assign valuation), seed `pot` from the content stake + antes. Emit `table.dealt`.
2. **Decision-point loop (≤ `max_decision_points`).** Each **active** seat sealed-commits one action this barrier turn. PC free text → narrator classifies → `beat_id` (+amount); NPC seats auto-commit (see NPC logic). Barrier collects all; folded/out seats are out of the denominator.
3. **Resolve a decision point** (new exclusive branch): apply each committed action in `order` — Fold → `status="folded"`; Bet/Raise/Call → adjust `pot.contributions`; Cheat/Read/Accuse → sub-loop. One OTEL span per seat action. Then: ≤1 active seat **or** `decision_point == max_decision_points` → showdown; else `decision_point += 1`, loop.
4. **Showdown.** Lift perception filter (hands reveal). **Resolve standing accusations first** — an exposed cheat forfeits regardless of strength. Among non-folded, non-forfeited seats, compare real `strength` (poker) / highest valid bid (auction). Award `pot.stake`; write `resolved_winner`, `outcome="table_winner:<seat>"`, `resolved=True`. Emit `table.showdown`.
5. **Teardown.** Standard confrontation teardown. The stake's consequence (money/item/information/favor changing hands) flows through the normal state-patch path so it's auditable.

## The Cheat / Read / Accuse sub-loop (the crunch)

All act on the **real** `private_state`:

- **Cheat** — manipulates the real hand (e.g. swap weakest card → `strength`/`strength_band` recomputed) **and** raises a hidden `cheat_trace` float (bigger/repeated cheats → higher). Real advantage, real evidence. Emits `table.cheat` (strength before/after, new trace).
- **Read the Table** — returns **real information** to the reading seat's *next* private frame: a target's `strength_band` and/or "their trace is suspicious" if `cheat_trace` exceeds a read threshold scaled by the reader's relevant stat. How a sharp player *earns* the basis to accuse. Emits `table.read`.
- **Accuse of Cheating** — **opposed check**: accuser's perception stat vs target's `cheat_trace` (+ cheater's concealment stat). Land → target forfeits + genre consequence; whiff → **accuser** eats the cost (slandered an honest man). Resolved at showdown so a late cheat is still catchable. Emits `table.accuse` (check math, landed/whiffed).

This loop is *why* real hands were worth paying for; every step emits a span, so the GM panel confirms the cheat fired / the read returned a real value / the accuse checked an actual trace.

## NPC seat commit logic

NPC seats auto-commit from a **real basis, not narration whim**: a ruleset-module policy over `(own strength_band, pot size, OCEAN/disposition)` returning a `beat_id` (+amount). Confident/low-neuroticism → slow-play strong or bluff weak; anxious → fold early; larcenous disposition → likelier to Cheat. Testable in isolation, genre-overridable. Emits `table.npc_commit` (inputs + chosen action).

## Private-info delivery (ADR-104/105 reuse)

Each seat's `private_state` is **secret until showdown** — the dogfight sealed-commit privacy generalized. The per-recipient CONFRONTATION frame supplier (the `make_confrontation_frame_supplier` seam from 59-16/59-20) projects, per socket, **only that player's own hand** + public table state (pot, folds, bets). Read-the-Table results inject into the requesting seat's next private frame only. At showdown the filter lifts and hands broadcast. No new perception infra — the existing firewall pointed at `table_state`.

**Scope boundary:** PCs *not seated at the table* are out of scope here — that's Specs 1/2 (ensemble weave / duel concurrent-thread). Spec 3 makes the **table itself** multi-seat.

## OTEL span inventory

| Span | Fires when | Payload |
|---|---|---|
| `table.dealt` | instantiate | seat count, game_kind, stake_kind, per-seat strength_band (dev-only) |
| `table.commit` | each PC sealed action classified | seat, beat_id, amount, decision_point |
| `table.npc_commit` | each NPC auto-action | seat, inputs (strength_band, pot, OCEAN), chosen beat |
| `table.cheat` | Cheat resolves | seat, strength before/after, new cheat_trace |
| `table.read` | Read resolves | reader seat, target, info returned |
| `table.accuse` | Accuse resolves | accuser, target, check math, landed/whiffed |
| `table.fold` | seat folds | seat, decision_point |
| `table.showdown` | resolution | revealed strengths, winner, forfeits, pot awarded |

These also drive `dispatch_engagement_watcher.py`: narration claiming "you catch him palming an ace" with no `table.accuse`/`table.cheat` span is a logged mismatch.

## Invariants & fail-loud

- **≥2 seats** or `TableNeedsOthersError` (no solitaire table; generalizes ADR-116).
- **`game_kind` resolves to a registered resolver** or `UnknownTableGameError` (no silent default game).
- A commit's **`beat_id` ∈ authored beats** and **`actor` ∈ seated parties** — reuses existing selection-validation.
- **`table_resolution` exclusive of `apply_beat`** — same guard as the sealed-letter branch; mechanics never double-apply.
- **Showdown requires every non-folded seat to have a readable `strength`/bid** — missing → fail loud, never a coin-flip default.
- A non-showdown frame **must not** contain another seat's `private_state` (asserted in test).

## Testing

- **Unit (resolver):** deal → strengths computed; each beat mutates state correctly; cheat raises trace + strength; accuse opposed-check both outcomes; showdown picks the right winner; forfeit-on-exposed-cheat beats raw strength.
- **NPC policy:** strong/confident → slow-play or bluff; weak/anxious → fold; deterministic given seeded inputs.
- **Perception firewall:** 3-seat table; render each socket's frame; assert seat A's frame never contains seat B's cards until showdown. (Behavior test, not source-grep — per No-Source-Text-Wiring.)
- **Invariants:** 1-seat → `TableNeedsOthersError`; unknown `game_kind` → raises; double-apply guard holds.
- **Wiring test (required):** drive a `table_resolution` confrontation through the **real** `_apply_narration_result_to_snapshot` with synthetic seat commits; assert `table.showdown` fired **and** a state-patch awarded the pot — proving the new branch is reachable from the production narration path, not just callable in isolation.

## Auction (second instance, zero model changes)

Same `TableState`, different `game_kind` + resolver: `private_state` holds a secret `valuation`/`max_bid` (no cards); beats are Raise-the-Bid / Bluff / Read-the-Room / Withdraw; `pot.contributions` is the current high bid; Read-the-Room = the Read mechanic returning a rival's valuation band; showdown = highest standing bid ≤ its own `max_bid` wins, lot changes hands via state-patch. Cheat/Accuse are **optional content** (a rigged auction could author them; Glenross won't). Proves the model is the general free-for-all, not a poker minigame.

## Content changes

- `spaghetti_western/rules.yaml` **poker**: add `resolution_mode: table_resolution`, `win_condition: table_showdown`, `table_game: poker`, `max_decision_points`, stake declaration; keep existing beats (Bet/Raise/Bluff/Call/Fold/Read-the-Table/Cheat/Accuse).
- `tea_and_murder/rules.yaml` **auction**: add `table_game: auction` + the same mode/win-condition + stake.
- Both drop their now-unused `player_metric`/`opponent_metric` (or leave inert — loader must accept either; prefer removal for honesty per content SOUL).

## Related ADRs / files

ADR-033 (confrontation engine) · ADR-077 (dogfight additive-extension precedent) · ADR-116 (participant membership → ≥2-seats invariant) · ADR-117 (pluggable ruleset seam) · ADR-104/105 (perception filtering) · ADR-074 (opposed_check, for cheat/accuse) · ADR-036 (turn barrier).
`sidequest-server/sidequest/game/encounter.py` · `.../server/narration_apply.py` (sealed-letter branch ~2685, apply loop ~2895) · `.../game/ruleset/` (native.py resolver home) · `.../server/dispatch/confrontation.py` (frame supplier) · `.../server/session_room.py` (barrier denominator).

## Out of scope (follow-ons — see roadmap)

- **Spec 1 — Ensemble weave** (narrator reliably seats/honors all willing actors; idle-in-room verb).
- **Spec 2 — Duel concurrent-thread** (linked confrontation / parallel ADR-053 investigation during an intended 1v1).
- Play-until-broke sessions, cross-hand stacks, re-buys (rejected: Scene-A is single-hand).
- Full street-by-street betting simulation (rejected: Cadence-A abstracts betting).
