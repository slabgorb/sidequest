# WWN Dying Window + Solo-Actuator Gap — Design Spec

**Story:** 108-6 (WWN dying/down window + solo-actuator gap) · **Points:** 5 · **Workflow:** spdd
**Date:** 2026-06-14 · **Author:** Architect (Naomi Nagata, design mode)
**Status:** Approved (brainstorm 2026-06-14, all five sections nodded; Approach A)
**Refs:** ADR-114 (ablative HP), ADR-123 (LethalityArbiter), ADR-143 (WN binding replaces native combat — DO NOT balance), gm-decisions 2026-06-13/14, re-homes cancelled 106-5 (cancellation commit `e5ae1fc8`), server PR #846 (dual-status contradiction fix)

---

## Problem

Under a WWN binding, a PC dropped to 0 HP today goes **terminal-dead only**. There is
no live WWN dying window — the SRD's *mortally wounded → d6-round stabilize → dead*
progression. Server #846 fixed the *contradiction* (a downed PC no longer shows two
conflicting statuses at once — terminal-dead presents one coherent status), but it did
so by **superseding** the stabilizable window whenever a terminal verdict was already
stamped. In solo play the lethality path stamps terminal first, so the window never
opens.

Two distinct gaps, both must close:

1. **No window opens (state gap).** `resolve_downed` only mints the Mortal Injury
   "dies in N rounds" status when `superseded_by_terminal` is False. In solo the
   reprisal/lethality pass rules LETHAL and stamps the incapacitating terminal status
   *before* the downed seam runs, so `superseded=True` and no window is ever created.

2. **Nothing can drive the clock (actuator gap — the brainstorm-flagged open problem).**
   Even if a window opened, in solo play there is no second actor to advance rounds,
   and the turn-intake gate disables input the instant the PC carries an incapacitating
   status. A clock nothing can advance is worse than no clock. **A timer/auto-tick was
   rejected** — the chosen fix is to put the player's own hand back on the wheel: the
   downed soloist drives their own stabilize attempts, and each submission ticks the
   clock.

## Chosen approach — Approach A

A **player-driven last stand**, built entirely on existing infrastructure (the Mortal
Injury status, the `stabilize_mortal_injury` tool, the `created_turn` provenance #846
already plumbed). The states are made **sequential, never simultaneous**, so the #846
single-status coherence cannot be re-broken. The only genuinely new behavior is one
input-gate carve at a single auditable point.

**Doctrine fit (ADR-143 / SOUL "Bind the Ruleset, Don't Balance It"):** an ordinary
0-HP down resolving into the WWN dying window instead of instant-terminal is **plain
WWN SRD truth**, not a native-vs-WWN balance knob. Nothing here tunes, converts, or
gates a native beat mechanic. No native engine is layered under the WN path.

---

## Section 1 — The down-state machine (one coherent status, always)

**Invariant that must survive:** at any instant the PC carries exactly one death-state
status. Never the dual-status contradiction #846 killed. Approach A preserves this by
making the states sequential.

**Branch at the down event** — the `post_resolution_lethality ↔ resolve_downed` seam
(`sidequest/server/dispatch/downed_seam.py`, `run_cwn_wwn_downed_seam`), **under a WN
binding only**:

- **Live hostile can still act on the PC → terminal-dead immediately**, exactly as
  today. The enemy's initiative slot / coup-de-grace owns the outcome. #846 unchanged.
  No window — you don't get a last stand with a sword at your throat.
- **No live hostile (the scoped solo case) → emit the mortally-wounded / stabilizable
  window as the single status.** Terminal-dead is not applied yet.

The branch predicate moves off "is an incapacitating terminal status already present"
(today's `superseded = any(... incapacitating ...)` at `downed_seam.py:168`) and onto
**"is there a live hostile that can still act on this PC."** The supersede mechanism
stays as the coherence guard, but the *decision to stamp terminal at all* for an
ordinary down becomes live-hostile-aware at this seam.

**The window status** is the existing Mortal Injury status minted by
`WithoutNumberRulesetModule.resolve_downed` (`sidequest/game/ruleset/without_number.py`,
~line 498–510), `text = "Mortal Injury — dies in {rounds} rounds unless stabilized"`,
`severity = StatusSeverity.Scar`, `rounds = cfg.trauma.mortal_injury_rounds`. It is
changed to carry **two** things it needs to be a live clock:

- **`stabilizable = True`** — a new structured flag on `Status` the input gate reads
  (Section 2). Do not key on status `text` (CLAUDE.md: no source/text-scrape wiring).
- **`incapacitating = True`** — so the PC cannot keep taking normal actions (no
  swinging while mortally wounded). **This is a change from today**, where the window
  status is created non-incapacitating. The window is incapacitating-for-normal-play
  but is *not* the terminal incapacitating-that-blocks-everything status — the gate
  tells them apart via `stabilizable` (Section 2).
- **Honest provenance** — `created_turn` / `created_in_encounter`, which #846 already
  plumbs through `resolve_downed`. The deadline is
  `created_turn + cfg.trauma.mortal_injury_rounds`; no separate counter to drift.

**Window resolution — still exactly one status at every step:**

- **Stabilize succeeds** → remove the window status, append a Frail Wound, restore to
  1 HP. (`stabilize_mortal_injury` already does precisely this — clears the Mortal
  Injury Scar, appends `"Frail — recovering at 1 HP"`, sets HP to 1.)
- **Clock expires** (`current_round ≥ created_turn + mortal_injury_rounds`, no success)
  → remove the window status, apply the terminal-dead status, block all input
  (Section 3's expiry edge).

Progression: **mortally-wounded → d6-round stabilize → dead**, exactly what the story
asks, with a singleton status set the whole way through.

**Open one-liner (spec-pinned):** an explicit overkill/instakill LethalityArbiter
verdict (vaporized, massive negative-threshold damage) **skips the window and goes
terminal immediately**. Window is for an *ordinary* down only. This is a one-line
predicate at the branch — the existing immediate-terminal path is preserved for true
instakills.

---

## Section 2 — The input-lane carve (the actual gap fix)

The one genuinely new behavior, confined to a single auditable point: the turn-intake
gate at `sidequest/handlers/player_action.py:534–589`.

**Today:** the gate calls `find_incapacitating_status(downed_core)`
(`sidequest/game/incapacitation.py`); if *anything* incapacitating is present it returns
the `CHARACTER_INCAPACITATED` banner before any turn dispatches — no narrator, no loop.
In solo that is the halt.

**The carve:** the gate stops treating "incapacitating" as one bucket. It distinguishes:

- **Terminal-dead status** (`incapacitating = True`, `stabilizable` falsy) → **block
  everything**, as today. The banner, zero turn consumed, no dispatch.
- **Stabilizable window status** (`incapacitating = True`, `stabilizable = True`) →
  **permit the submission and route it to the narrator.**

**The permitted lane is free-text, not a fixed verb menu.** The player types whatever
they would attempt while bleeding out — "press my hand to the wound," "crawl to my pack
for the potion," "tear my cloak into a bandage." The narrator adjudicates whether that
is a legitimate dying-window action and, when it is a stabilization attempt, calls
`stabilize_mortal_injury`. Deliberate per SOUL: the **Zork Problem** (never collapse the
player to keyword matching) and **the Guitar Solo** (give the downed soloist a real
part). The mechanical gate only decides whether input is allowed at all in this state —
it does not enumerate the actions.

**Genre-truth guard / abuse:** because the narrator adjudicates, "I stand up and attack
the door" from a mortally-wounded PC gets the monkey's-paw treatment — you can try, but
you are bleeding out; the attempt **costs a round on the clock and accomplishes nothing
useful**. The narrator enforces plausibility; the engine keeps the clock honest. This
stays out of "balancing native mechanics" and inside pure narration + WWN lethality.

**Why this is the whole fix:** permitting the submission re-supplies the loop driver
solo play lost. The player's stabilization turn fires the narrator → the narrator
resolves the attempt → the engine ticks the clock (Section 3). No timer, no auto-tick,
no parallel state machine — the player's own hand is back on the wheel.

The risk surface is now **one `if` in one gate**: terminal blocks, stabilizable permits.
That is where the wiring test plants its flag (Section 5).

---

## Section 3 — Clock advancement & expiry resolution (engine-owned)

The clock must be the engine's truth, not a number the narrator passes in — otherwise
the GM panel cannot tell a real countdown from improvised narration (lie-detector
principle).

**`rounds_elapsed` becomes derived, not supplied.** Today `stabilize_mortal_injury`
takes `rounds_elapsed` as a narrator argument (the narrator guesses it; difficulty =
`8 + rounds_elapsed`). Under this design the engine computes it from the provenance #846
stamped:

```
rounds_elapsed = current_round − created_turn        # created_turn = window open
deadline       = created_turn + cfg.trauma.mortal_injury_rounds
expired        = current_round ≥ deadline
```

The narrator-supplied `rounds_elapsed` is **kept only as a cross-check that raises if it
disagrees** with the computed value (fail-loud, No Silent Fallbacks — no silent drift).
The Heal-check difficulty `8 + rounds_elapsed` therefore rises automatically and honestly
as the window ages — the WWN SRD rule, driven by persisted state.

**Per dying-window turn, the engine does three things in order:**

1. **Resolve the attempt.** If the player's action was a stabilization, run the existing
   Heal check at the *computed* difficulty (success → window clears, Frail Wound, 1 HP).
   A non-stabilization action (the door-attack) resolves as narration and burns the round.
2. **Tick.** The round advances because the player submitted; `rounds_elapsed` recomputes
   from the new round number. Nothing to store — it falls out of
   `current_round − created_turn`.
3. **Check expiry.** If `current_round ≥ deadline` and still not stabilized → remove the
   window, apply terminal-dead, lock input.

**Where the expiry check lives:** it must fire even on a failed or non-stabilization
turn, so it sits in the **down/dying resolution path every dying-window turn passes
through** — the post-action lethality pass — **not** inside the success branch of the
stabilize tool. A wasted round still advances toward death.

**Stalling is impossible:** each submission burns a round, difficulty climbs, the
deadline is fixed. The only escapes are a successful Heal check or an external mend (a
potion is itself a stabilization-class action the narrator can honor). WWN-true; no
extra anti-abuse machinery.

---

## Section 4 — OTEL (the GM panel proves the clock is real)

Per the lie-detector principle, every subsystem decision emits a span. Three new events,
registered on the existing dynamic `{slug}.*` WN route pattern
(`sidequest/telemetry/spans/wn.py`, `WN_FAMILY_SLUGS` loop), so they namespace honestly
as `wwn.dying_window.*` (and `cwn`/`awn` when those bind):

- **`wn.dying_window.opened`** — fired at the down branch when the stabilizable window is
  chosen over terminal. Attributes: `actor`, `created_turn`, `mortal_injury_rounds`,
  `deadline_round`, `reason` (`no_live_hostile`). Proof the window path fired, not the
  terminal path.
- **`wn.dying_window.tick`** — fired each dying-window turn. Attributes: `actor`,
  `rounds_elapsed` (engine-derived), `difficulty` (`8 + rounds_elapsed`),
  `action_was_stabilization` (bool), `roll` / `success` when applicable. The per-round
  census — the panel watches the clock advance honestly and sees whether each turn was a
  real stabilization attempt or a burned round.
- **`wn.dying_window.resolved`** — fired once at exit. Attributes: `actor`, `outcome`
  (`stabilized` | `died`), `final_rounds_elapsed`, resulting status (`Frail` vs
  `terminal-dead`).

**Folded-in #846 thread:** `mortal_injury_declared_span` (`without_number.py`) already
*accepts* `superseded_by_terminal` but the span signature path that should record it as
an attribute was never completed — verify and complete so the supersede decision is
visible. Since this story re-touches that exact path, do not leave a known-dark span in a
subsystem we are hardening.

**Branch coverage is the point:** `opened`-with-reason on one side and the terminal path
on the other means the panel can always distinguish "entered the window" from "instantly
terminal (live hostile / overkill)." No decision in the down path is invisible.

---

## Section 5 — Test strategy

Workflow is **spdd** (TDD with superpowers attestation) — TEA (Amos) writes these
red-first. Coverage maps to the five seams; per the hard rule, **at least one test
proves the gap is wired end-to-end**, not just that units pass in isolation. Per the
server's "No Source-Text Wiring Tests" rule, wiring is asserted via OTEL spans and
fixture-driven behavior, never by grepping production source.

**State-machine tests (Section 1) — the singleton invariant:**
- Down with no live hostile → exactly one status, the stabilizable window; assert
  terminal-dead absent.
- Down with a live hostile present → terminal immediately, window absent (the #846
  contradiction stays fixed — regression guard).
- Window resolution success → window gone, Frail present, HP = 1, single status.
- Window expiry → window gone, terminal-dead present, single status. Assert the two
  never coexist at any step.
- Overkill/instakill verdict → skips window, terminal immediately (Section 1 predicate).

**Input-gate tests (Section 2) — the carve:**
- Terminal-dead status → submission blocked, `CHARACTER_INCAPACITATED`, zero turn.
- Stabilizable window status → submission permitted, routed to narrator (unit form of
  the gap fix).

**Clock tests (Section 3) — engine-owned `rounds_elapsed`:**
- `rounds_elapsed` derives from `current_round − created_turn`; difficulty climbs as the
  window ages.
- Narrator-supplied `rounds_elapsed` disagreeing with the computed value fails loud.
- A non-stabilization "stall" turn burns a round and advances expiry — does not pause it.
- Expiry fires on a failed/non-stabilization turn, not only inside the stabilize-success
  branch.

**OTEL tests (Section 4):**
- `opened` carries `reason`; `tick` carries derived `rounds_elapsed` +
  `action_was_stabilization`; `resolved` carries `outcome`. Assert the terminal side does
  not emit `opened`.
- Folded-in #846 fix: `mortal_injury_declared_span` records `superseded_by_terminal`.

**The wiring test (mandatory — proves the loop turns):**
A solo-play integration test driving the real path: solo PC drops to 0 HP with no live
hostile → assert the game loop is **not** halted (the bug today) → submit a free-text
stabilization action through the actual `player_action` entry → assert it reaches the
narrator and the engine ticks the clock → drive to both terminal outcomes
(stabilize-before-deadline lives; stall-past-deadline dies). Fails on `main` today (the
gate halts the loop); passes only when the carve is wired through to dispatch. No
half-wired credit.

---

## Files in scope

| File | Change |
|------|--------|
| `sidequest/game/status.py` | Add `stabilizable: bool = False` structured field to `Status`. |
| `sidequest/game/ruleset/without_number.py` (`resolve_downed`) | Window status carries `incapacitating=True` + `stabilizable=True`; mint it on the no-live-hostile branch (not gated only by `not superseded`); complete `superseded_by_terminal` span attribute. |
| `sidequest/server/dispatch/downed_seam.py` (`run_cwn_wwn_downed_seam`) | Branch predicate: live-hostile → terminal; no-live-hostile → window. Emit `dying_window.opened`. |
| `sidequest/handlers/player_action.py:534–589` | Gate carve: terminal blocks; stabilizable permits + routes to narrator. |
| `sidequest/agents/tools/stabilize_mortal_injury.py` | Derive `rounds_elapsed` from provenance; cross-check narrator arg, fail loud on mismatch. |
| post-action lethality pass (Section 3 expiry home) | Expiry check fires every dying-window turn; emit `dying_window.tick` / `dying_window.resolved`. |
| `sidequest/telemetry/spans/wn.py` | Register `dying_window.{opened,tick,resolved}` on the `{slug}.*` route pattern. |

## Out of scope

- Multiplayer dying windows (a downed PC with live allies who could stabilize them) —
  the existing multi-actor path already advances rounds; this story scopes the **solo**
  actuator gap. The branch (live-hostile vs not) is MP-safe but MP stabilize-by-ally is
  not designed here.
- Any native-engine tuning/conversion (ADR-143 forbids it).
- UI changes beyond rendering the permitted free-text input state (the window status is
  already a status the client renders; confirm the input box is not disabled client-side
  for the stabilizable state — if it is, that is a follow-up, not this story).
