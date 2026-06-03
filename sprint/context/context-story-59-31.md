---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-31: Opponent-yield signal — record outcome opponent_yielded/player_victory when an opponent backs down (not abandoned)

## Business Context

**The label lies, and the GM panel can't tell a victory from a retreat.**

In the sq-playtest `wry_whimsy/oz` session (2026-06-02-oz-3, turn 7) the player stood
their ground against the Cowardly Lion. The Lion **yielded** — backed down, which is his
canon behavior. The confrontation resolved same-turn in prose with **zero beats** and **no
dial threshold met**. The engine recorded the outcome as `abandoned_on_location_change` —
a label that reads *"the player walked away from an unfinished fight."* The truth is the
exact opposite: **the opponent surrendered and the player prevailed.** The outcome label is
wrong, and because it is wrong, every downstream consumer keyed on it — XP/advancement
credit, the GM-panel resolution census, future narrator close-out — sees a non-event where
a victory happened.

This matters to the primary audience in two concrete ways. For **Keith-as-dev**, the GM
panel is the lie detector (CLAUDE.md OTEL principle): if the engine records `abandoned`
when the player won, the panel cannot distinguish "Claude narrated a win it didn't earn"
from "the engine genuinely resolved a win." For **Sebastien/Jade (mechanics-first
players)**, a yielded opponent that grants no advancement credit makes the crunch feel
broken — the same complaint that drove the SWN-crunch reintroduction. A win must *read* as
a win and *pay* like a win.

This is the residual that PR #576 (`feat/encounter-victory-on-location-change`)
**explicitly punted**. #576 fixed the higher-priority sibling — a location change at/after a
**met** dial threshold now resolves `player_victory`/`opponent_victory` via
`StructuredEncounter.dial_threshold_outcome()`. It left (a) the *no-threshold-met*
opponent-yield case and (b) the XP-on-victory question to this follow-up story. This story
closes both, standing on ADR-116 ("A Confrontation Requires an Other") and the #576
outcome-resolution seam — **no new ADR**.

## Technical Guardrails

**Single repo: `sidequest-server` only.** No UI, no content, no daemon. No new ADR.
Reuse-first discipline (epic 59 §"Critical reuse-first findings") and No-Silent-Fallbacks
(epic 59 §"fail loud") both apply with full force.

### The asymmetry invariant (load-bearing — never violate)

> A **player** yield is a withdrawal / **LOSS**. An **opponent** yield is a player
> **VICTORY**.

The existing yield infra is **player-side only**: `dispatch/yield_action.py:handle_yield`
sets `enc.outcome='yielded'` and emits `ResolutionSignal(outcome='yielded', ...)` when a
**PC** yields. There is **no path for the opponent to yield**. The opponent-yield outcome
**MUST map to a distinct label** — `opponent_yielded` (which *resolves as* `player_victory`)
— and **MUST NEVER reuse the player-side `'yielded'` label**. Conflating them would record
a player's victory as the player's loss.

### Reuse-first infra (do NOT invent new actor state)

The engine **already models a yielded opponent**:

| Existing primitive | Location | Role in this story |
|--------------------|----------|--------------------|
| `EncounterActor.withdrawn: bool` | encounter actor model | Flips `True` when an actor yields; withdrawn actors are skipped by `_apply_beat`. The deterministic signal that an opponent has backed down. |
| `StructuredEncounter.opponents_disposition` | encounter model (`'surrendered'`\|`'routed'`) | Set by the B/X morale path `_apply_flee_consequence` (`narration_apply.py` ~502-540), which already sets `resolved=True` + outcome on surrender/rout. |
| `StructuredEncounter.dial_threshold_outcome()` | encounter model | #576's helper → `player_victory`/`opponent_victory`/`None`. The new `opponent_yield_outcome()` helper is its sibling. |
| `confrontation_resolved_on_location_change` span | watcher emit (added by #576) | Reuse this emit family for the OTEL span on opponent-yield resolution. |
| `award_turn_xp` | `dispatch/encounter_lifecycle.py:1256` | Flat per-turn tick (25 in_combat / 10 otherwise). **No** victory-XP bonus exists today. |

### The three seam sites

1. **Wrong-label site (the residual):** `narration_apply.py` ~2788-2860, the
   location-change scene-boundary handler. #576 added: `won_outcome =
   active_encounter.dial_threshold_outcome()`; threshold met → victory; **else-branch**
   (~2835) sets `outcome='abandoned_on_location_change'`. The Lion-yield has no threshold
   met (zero beats) so it falls to the else → `abandoned`. **Fix:** before falling to
   abandoned, check `opponent_yield_outcome()`.
2. **Same-turn sweep:** the post-turn `_resolve_dial_threshold_and_phase` sweep. Wire
   `opponent_yield_outcome()` here so a same-turn opponent yield resolves **without** a
   location change (the Lion yielded same-turn in prose — resolution must not depend on the
   party walking out).
3. **Outcome mapping helper:** new `opponent_yield_outcome()` alongside
   `dial_threshold_outcome()`, returning `'player_victory'` when **every** `side='opponent'`
   actor is `withdrawn` (or `opponents_disposition in {'surrendered','routed'}`) **AND no
   opposing actor remains active**, else `None`.

### Trigger seam — design-first decision for Dev (White Rabbit)

Prefer **deterministic engine-checked confirmation** over pure-LLM compliance (avoid the
59-27 / 59-15 LLM-under-firing risk family). The narrator marks the opponent yielded via an
**existing write-tool surface** — reuse `update_npc_disposition` (disposition
`'surrendered'`) **or** a thin opponent-yield flag on `advance_confrontation` (`axis='opponent'`
is already the opponent dial). **Do NOT add a brand-new tool** unless the dev's first
design pass shows neither fits. The narrator signal is the *trigger*; the engine state
(`withdrawn`/`disposition`) is the *proof*.

### What NOT to touch

- **Do not revive the dormant 49-5 `[ENCOUNTER RESOLVED]` narrator-zone threading.** This
  story stands alone. Stamping `snapshot.pending_resolution_signal` on opponent-yield
  resolution is **cheap and correct** (matches the dial-threshold sweep, which already calls
  `_build_resolution_signal`) and SHOULD be done so 49-5 inherits it — but narrator-zone
  *narration* is **NOT an acceptance gate** here.
- **Do not reuse or mutate the player-side `'yielded'` path** in `yield_action.py`.
- **Do not introduce a yield-specific XP bonus or penalty.** Parity only.

## Scope Boundaries

**In scope:**
- `opponent_yield_outcome()` helper on `StructuredEncounter` → `'player_victory'` | `None`,
  computed purely from `withdrawn` / `opponents_disposition` / remaining-active-opponent
  state.
- Same-turn resolution: wire `opponent_yield_outcome()` into the post-turn
  `_resolve_dial_threshold_and_phase` sweep (no location change required).
- Location-change boundary fix: `narration_apply.py` ~2835 else-branch checks
  `opponent_yield_outcome()` **before** falling to `abandoned_on_location_change`.
- Recorded `enc.outcome = 'opponent_yielded'`, resolving as `player_victory` for
  reward/credit — distinct from player-side `'yielded'` (loss) and
  `'abandoned_on_location_change'` (genuine walk-away).
- XP/advancement parity: `opponent_yielded` flows through the same `player_victory`-keyed
  path as any beat/dial victory — no yield-specific bonus or penalty.
- OTEL span (`component='confrontation'`) on opponent-yield resolution with
  `resolution_label='opponent_yielded'`, `trigger`, `yielded_opponents`,
  `opponents_disposition`.
- Stamp `snapshot.pending_resolution_signal` on opponent-yield resolution (for 49-5 to
  inherit later — not gated here).
- The narrator trigger seam (reuse `update_npc_disposition` OR `advance_confrontation`
  flag), decided in Dev's first design pass.

**Out of scope:**
- Reviving 49-5 `[ENCOUNTER RESOLVED]` narrator-zone threading / `_build_turn_context`
  copy of `pending_resolution_signal` into `TurnContext`. (Delivery finding cross-link if
  the signal shape needs a new field.)
- Any new victory-XP bonus mechanic (would key on `player_victory` and inherit this for
  free if introduced later).
- Any new ADR, content/YAML, or new dispatch tool (unless the seam review proves the two
  existing tools cannot carry the trigger).
- UI / GM-panel rendering changes (the span is emitted; consuming it visually is the
  panel's existing job).

## AC Context

### AC-1 — Opponent-yield records `opponent_yielded` / `player_victory`, NOT abandoned

**Must be true:** Given an encounter where **all** `side='opponent'` actors are
`withdrawn`/`surrendered`/`routed` and **no opposing (opponent-side) actor remains active**,
the engine records `enc.outcome == 'opponent_yielded'` which resolves as `player_victory`.
It must be **NOT** `abandoned_on_location_change` and **NOT** the player-side `'yielded'`.

**Edge cases:** (a) a *mix* — one opponent withdrawn, another still active → `None`
(unresolved, do not fire); (b) `opponents_disposition='surrendered'` set via the morale
path with no per-actor `withdrawn` flag → still resolves (disposition is sufficient);
(c) opponent withdrawn but a **player-side** actor also withdrawn → resolution keys on
opponent-side actors only, player withdrawal does not block the opponent-yield.

**Test verifies:** Build a `StructuredEncounter` with opponent actor(s) flipped
`withdrawn=True`; assert `opponent_yield_outcome() == 'player_victory'`; drive the
resolution path and assert `enc.outcome == 'opponent_yielded'`; assert it is never equal to
`'yielded'` or `'abandoned_on_location_change'`.

### AC-2 — Same-turn resolution via the post-turn sweep (no location change)

**Must be true:** The opponent-yield resolves through
`_resolve_dial_threshold_and_phase` (the post-turn sweep) **without** requiring a location
change. This is the literal Lion-yields-in-prose case — zero beats, no dial threshold,
party does not move.

**Edge cases:** sweep runs but no opponent has yielded → no resolution (encounter stays
active, see AC-4); sweep runs and a dial threshold *was* met → existing #576 path wins
(opponent-yield helper is checked but the dial outcome already resolved).

**Test verifies:** Set up the encounter, flip opponent `withdrawn`, invoke the post-turn
sweep directly (no location-change call), assert `enc.resolved` / `enc.outcome ==
'opponent_yielded'` afterward.

### AC-3 — Location-change boundary checks opponent-yield before abandoning

**Must be true:** In `narration_apply.py` ~2835 the else-branch checks
`opponent_yield_outcome()` **before** setting `abandoned_on_location_change`. If the
opponent has yielded, it resolves `player_victory` with `outcome='opponent_yielded'` and
emits the `confrontation_resolved_on_location_change` span (reuse #576's emit), NOT
abandoned.

**Test verifies:** Drive an encounter to a location-change boundary with no threshold met
but with opponents withdrawn; assert outcome is `opponent_yielded`/`player_victory`, not
`abandoned_on_location_change`.

### AC-4 — Genuinely-unfinished encounter STILL abandons (no over-firing)

**Must be true:** An encounter with **no threshold met AND no opponent yield** (opponents
still active, none withdrawn/surrendered) on a location change still records
`abandoned_on_location_change`. This is the over-firing guard — the deterministic engine
check must not fabricate a victory where none occurred. (Opposite failure family to the
59-27/59-15 LLM-under-firing risk; here the deterministic check is the protection.)

**Edge cases:** partial opponent withdrawal (some active) → still abandons; empty
opponent set / malformed actor list → must not crash and must not falsely resolve victory.

**Test verifies:** Location-change boundary with active, non-withdrawn opponents; assert
`enc.outcome == 'abandoned_on_location_change'` (unchanged behavior). This is the negative
test that proves the new branch is gated correctly.

### AC-5 — OTEL span fires on opponent-yield resolution

**Must be true:** A watcher span with `component='confrontation'` fires on opponent-yield
resolution carrying: `outcome='player_victory'`, `resolution_label='opponent_yielded'`,
`trigger` (`'opponent_yield_sweep'` | `'opponent_yield_on_location_change'`),
`yielded_opponents` (list of withdrawn/surrendered opponent actor names), and
`opponents_disposition`. (GM-panel lie-detector requirement — dev observability only, NOT a
Sebastien player-facing feature.)

**Test verifies:** Capture emitted watcher spans during both resolution paths (sweep and
location-change); assert a `component='confrontation'` span exists with each required attr
present and correctly valued; assert `trigger` differs between the two paths.

### AC-6 — XP/advancement parity with any other `player_victory`

**Must be true:** `opponent_yielded` resolving as `player_victory` flows through the
**same** `player_victory`-keyed reward/advancement path as a beat/dial victory — identical
treatment, **no yield-specific bonus or penalty**. (Today no victory-XP bonus exists; the
contract is parity so any future bonus keyed on `player_victory` inherits this for free.)

**Test verifies:** Assert that whatever consumes `outcome=='player_victory'` for credit
sees the opponent-yield resolution identically (e.g. the resolution maps to the same
victory key with no special-casing on the `opponent_yielded` label). Guard against a code
path that branches on the literal `'opponent_yielded'` string to award differently.

### Rule-enforcement coverage (beyond ACs)

- **No-Silent-Fallbacks:** the new branch must not swallow malformed encounter/actor state
  into a silent default — a test should confirm bad input fails loud or returns a clean
  `None`, never a fabricated victory.
- **Distinct-label invariant:** an explicit assertion that `opponent_yielded != 'yielded'`
  is never collapsed anywhere the player-side path could be reused.
- **Test-quality self-check:** every test asserts a *valued* outcome (the exact label /
  span attr), not merely `is_some`/`is not None`.

## Assumptions

- **`opponent_yield_outcome()` is engine-inferable** from existing `withdrawn` /
  `opponents_disposition` state the narrator already sets via existing tools — no new actor
  field required. *(If false → Design Deviation; a thin tool field on `advance_confrontation`
  is the sanctioned fallback per the story.)*
- **PR #576 is merged into `develop`** (`StructuredEncounter.dial_threshold_outcome()`, the
  `confrontation_resolved_on_location_change` span, and the ~2788-2860 location-change
  handler all exist at the branch base). The branch `feat/59-31-opponent-yield-signal` was
  cut off `develop` in `sidequest-server`.
- **No victory-XP bonus exists today**, so "parity" means "resolves `player_victory` and is
  treated identically" — there is no existing bonus to match beyond the flat per-turn tick.
- **`side='opponent'` is the authoritative actor-side discriminator** for identifying which
  actors' yield constitutes a player victory.
- **Jira is not configured** for this project — Jira steps skipped throughout.

> If any assumption proves wrong during implementation, log it as a Design Deviation and
> notify SM (The Mad Hatter) immediately. Wrong assumptions are the #1 source of rework.

> **Context provenance:** Created by TEA (The Caterpillar) via `/pf-context` to unblock the
> RED phase — the SM setup did not emit this file. Authored solo (no tandem backseat); the
> Architect (White Queen) design is already fully specified in the story description and
> epic-59 architecture section, so architect-tandem observations would be redundant. The
> design-first trigger-seam decision is correctly deferred to Dev's first GREEN pass.
