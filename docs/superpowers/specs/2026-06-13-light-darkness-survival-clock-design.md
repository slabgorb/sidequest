# Light & Darkness — Generic Environmental Survival Clock

**Date:** 2026-06-13
**Author:** Architect (The Man in Black)
**Status:** Approved design, pre-implementation
**Repos:** server, content, ui
**Surfaced by:** 2026-06-13 single-player playtest of `caverns_and_claudes/beneath_sunden` (WWN port)

---

## 1. Problem (from the 2026-06-13 dive)

Beneath Sünden's single most-advertised killer is the dark. The world's own
fiction says so out loud: the winch-keeper, asked what kills the most delvers,
answers *"The dark itself. Not the creatures. Not the traps. Parties that stay
too long, run their lights down, can't find the rope back."* The Board of the
Unreturned is, in-fiction, a wall of people who ran their lights down.

That threat has **zero mechanical backing**. Verified live during the dive:

- `GameSnapshot.resources == {}` — empty. No light pool, no survival clock.
- No light/torch/darkness subsystem exists in the server. The only `torch`
  string hits are an alias-accretion comment and an audio-ambience cue — neither
  is a mechanic.
- The starting kit contains three `Torch` items tagged `[light, consumable,
  essential]`, but the `consumable`/`essential` tags gate **nothing** — torches
  are inert inventory flavor.
- `clock_t_hours == 0.0`, `days_elapsed == 0` after a full descent into the
  deep — the only time clock present is the **orbital** clock (ADR-130), which
  is gated to space worlds and does not tick in a dungeon.

The consequence: the narrator can say *"your torch gutters and the dark closes
in"* and **nothing answers**. The board's death is improvisation. This is the
exact "convincing narration, no mechanical backing" failure the OTEL principle
exists to catch — pointed at the most important mechanic in the world.

## 2. Goals

1. **Light is a tracked, depleting resource** with deterministic per-beat burn —
   not narrator-judged. The dark becomes a mechanism, not a mood.
2. **Reusable across worlds.** The primitive is a generic *environmental clock*;
   Beneath Sünden declares `light`, a future world declares `air` / `cold` /
   `warmth` the same way. Crunch-in-genre, declaration-in-content.
3. **Running out has ongoing, legible teeth** — a status penalty on all rolls
   that makes everything (including finding the rope back) harder, killing by
   degrees without a bespoke death timer.
4. **No micromanagement chore.** The burn is automatic; only deliberate
   torch-management is a player action, and that action is a *meaningful*
   resource decision, not busywork.
5. **Player-legible** (Sebastien/Jade see the math) and **OTEL-observable**
   (the GM panel can verify the subsystem fired).

## 3. Non-goals

- **Not** a light-*radius* / line-of-sight / tactical-illumination model. Light
  here is a survival clock, not a visibility geometry. (A future tactical-map
  feature could read the lit/dark flag, but that is out of scope.)
- **Not** a rework of the equipment `equipped` flag. The dive also found the
  Hemp Rope flagged `equipped=True` while the sword/armor were `equipped=False`
  after a climb. That is a separate finding; this design deliberately does **not**
  hang light state on the `equipped` flag (see §11).
- **Not** a generic weather/temperature system. We build exactly one resolver
  (`light`) on a generic substrate; future environmental clocks register, they
  do not re-architect.
- **No auto-relight.** Lighting a fresh torch is always a player intent (§6.2).

## 4. Reuse audit (what we are climbing, not rebuilding)

| Need | Existing infrastructure | Reused how |
|------|------------------------|------------|
| Depleting bounded value with thresholds | `ResourcePool` / `ResourceThreshold` (ADR-033, `game/resource_pool.py`); `GameSnapshot.resources: dict[str, ResourcePool]` (`session.py`); `init_resource_pools` upserts from the genre pack | `light` is a declared `ResourcePool`. No new pool type. |
| Per-turn mechanical dispatch before the narrator | Intent-router **dispatch bank** `run_dispatch_bank` (ADR-113/123, `agents/subsystems/__init__.py`) | Light burn registers as a dispatch-bank subsystem. |
| Fire a subsystem on context, not on player intent | **Precondition gate** (ADR-123, `agents/dispatch_precondition_gate.py`) | The burn tick is precondition-gated (dark region + exploration beat), not confidence-gated. |
| Ongoing modifier on all rolls | **Status effects** — `Boon` / `Penalty` (`game/status.py`); read by the resolution/dice layer and the LethalityArbiter | Darkness applies a `Penalty` status; the −N flows into every roll for free. |
| Threshold crossing → narration + telemetry | `detect_crossings` + `mint_threshold_lore` (`game/thresholds.py`) | Guttering/dark crossings mint lore and feed OTEL with no extra plumbing. |
| Player-facing gauge | HP diamond-pip pattern (PartyPanel / Character panel, ui) | The light gauge reuses the pip rendering. |

**Explicitly NOT reused:** `clock_t_hours` (orbital-only, ADR-130). Light is
beat-driven, not story-hour-driven.

## 5. The pool (content-declared)

Beneath Sünden's world (or the C&C genre pack) declares a resource pool:

```yaml
# resources declaration (genre/world tier, consumed by init_resource_pools)
resources:
  - name: light
    current: 0          # starts UNLIT — you descend into the dark on purpose
    max: 6              # one torch = 6 exploration beats (tunable, §9)
    min: 0
    voluntary: false    # players don't "spend" it directly; the tick burns it
    thresholds:
      - name: guttering
        value: 1
        direction: down   # fires when the last beat of light begins
      - name: dark
        value: 0
        direction: down   # fires when light runs out → apply darkness penalty
```

`light.max` is the per-torch budget; lighting a torch sets `current = max`.
`current == 0` is the dark state. The pool is **party-shared** for the delve
(one torch lights the room); per-PC light is deferred until a world needs split
parties (§9). For solo it is moot.

**Dark-region flag.** Burn only happens where it is dark. Cartography regions
carry a content flag, e.g. `lit: false` (default for deep/generated regions) vs
`lit: true` (surface camp, the kept fire at Ropefoot). `the_dropmouth` — "the
last lit place" — is `lit: true`; the generated deep (`entrance` and below) is
`lit: false`. This is authored content, not engine logic.

## 6. Router-loop integration (two touchpoints)

Both run inside the intent-router turn loop, before the narrator.

### 6.1 The deterministic burn tick (precondition-gated)

A new dispatch-bank subsystem `environment_clock`:

- **Precondition** (via `dispatch_precondition_gate`, **not** router confidence):
  `PC in a region where lit == false` **AND** the classified beat is a
  *time-advancing exploration beat* (room/region move, search, rest, force a
  door, **a combat round** — lingering and fighting both cost light). Pure
  social/dialogue beats, inventory inspection, and OOB asides do **not** burn.
- **Effect:** apply `ResourcePatch(Subtract, "light", 1)`, clamped at 0. Inspect
  the returned `ResourcePatchResult.crossed_thresholds`:
  - crossed `guttering` (down) → set a narration cue ("the torch is dying").
  - crossed `dark` (down) → apply the darkness `Penalty` status (§7).
- The tick **cannot be dodged by phrasing** — that is the whole point of making
  it precondition-gated rather than intent-classified.

### 6.2 Lighting a torch (intent / confidence-gated)

Deliberate light management — *"I light a torch," "I light another," "I snuff
it"* — is a classified player **intent**, handled as a confidence-gated dispatch
(or routed to an inventory action):

- Verify a `Torch` item (tag `light`) is present and `consumable` charges remain.
- Consume one torch charge; `ResourcePatch(Set, "light", max)`.
- The upward crossing of the `dark` threshold **clears** the darkness `Penalty`.
- If no torch remains: the action fails loudly ("nothing left to burn") — this
  is the genuine "ran their lights down" state. No silent fallback.

This is the meaningful decision point: spend a finite torch now, or push deeper
into the gathering −N. It is **not** the meaningless re-equip churn we reject —
it is OSR torch-management tension.

## 7. The consequence (status effect, not a death clock)

When `light.current` reaches the `dark` threshold, apply an ongoing `Penalty`
status (`game/status.py`):

- **−N on all rolls** (default **N = 2**, §9), ongoing while `light.current == 0`
  in a dark region.
- Cleared when a torch is lit (§6.2) or the PC reaches a `lit: true` region (the
  rope back to Ropefoot).

Because the dice/resolution layer **already reads status effects**, the −N flows
into *every* check with no new wiring: navigation/search rolls to find exits and
the seam back, combat attack/save rolls, skill checks, and the LethalityArbiter's
inputs. **The dark kills by making the find-the-rope-back rolls fail** — which is
exactly the board's death, and needs no separate death timer.

**Penalty shape:** binary — lit = 0, dark = −2. No ramp (per the "ongoing minus
on all rolls" decision). A world may tune N via the threshold metadata.

## 8. Data flow (one turn in the dark)

```
player action
  └─> intent router classifies beat + intent
        ├─ run_dispatch_bank (before narrator):
        │    ├─ environment_clock [precondition: dark region + exploration beat]
        │    │     └─ Subtract light 1 → ResourcePatchResult
        │    │           ├─ crossed guttering ↓ → narration cue
        │    │           └─ crossed dark ↓     → apply Penalty(-2) status
        │    └─ [if intent == "light torch", confidence-gated]
        │          └─ consume Torch → Set light=max → clear Penalty (dark ↑)
        ├─ resolution / dice for this turn READ the Penalty status → -2 on rolls
        └─ narrator runs LAST, gaslit via snapshot (light pool + status visible)
              └─ prose matches the gauge: guttering / dark / relit, truthfully
```

## 9. Tunable knobs (defaults set here)

| Knob | Default | Where tuned |
|------|---------|-------------|
| Penalty size **N** | −2 on all rolls | threshold metadata (world/genre) |
| Torch duration | 6 exploration beats (`light.max`) | resource declaration |
| Penalty shape | binary (lit 0 / dark −2), no ramp | design-fixed; ramp is a future option |
| Scope | party-shared light pool | per-PC deferred |
| Dark regions | `lit: false` default for generated/deep regions | cartography content |

## 10. Surfaces

### 10.1 UI — the light gauge

A light gauge in the player panel, reusing the HP diamond-pip rendering: pips
remaining = `light.current` of `light.max`, plus a torch-count readout (charges
left in inventory). Guttering = visually distinct (e.g. last pip pulsing/dim);
dark = empty + a "−2 in the dark" affordance so the penalty is legible (mechanics
-first players see the math). The gauge is reactive off the snapshot mirror like
HP.

### 10.2 OTEL — the lie detector for the new subsystem

The `environment_clock` tick emits a `light.tick` span each burn:
`light.current`, `light.max`, `region`, `beat_kind`, `crossed_threshold`,
`penalty_applied`. Lighting emits `light.relit` (torch consumed, charges
remaining). Per the OTEL principle, the GM panel can now verify the dark is
*engaged* rather than improvised.

### 10.3 Narrator gaslighting

The light pool and darkness status are materialized into the snapshot the
narrator sees, so guttering/dark/relit prose is *driven by* state, not invented.
The narrator must surface the stakes legibly (Diamonds and Coal) — entering the
dark unlit is never a silent gotcha; the winch-keeper's warning and the gauge
foreshadow it.

## 11. Related finding (out of scope, logged)

The dive also observed the **`equipped` flag** behaving oddly: after the climb,
Hemp Rope was `equipped=True` while Long Sword and Leather Armor were
`equipped=False`. This design intentionally does **not** model light via
`equipped` (a torch being "lit" is a pool/charge state, not an equip slot). The
equip-flag behavior — and whether `equipped` gates combat/AC at all — is a
separate finding to triage on its own; it is noted here only so the reader knows
it was seen and deliberately excluded.

## 12. Risks & watch-outs

- **Beat taxonomy precision.** "Exploration beat" must be defined against the
  router's existing beat-kind classification, not invented. If the precondition
  whitelist is too broad it over-burns (every social aside eats a torch); too
  narrow and lingering is free (understating the danger). Pin the whitelist to
  time-advancing beat kinds and OTEL every tick so calibration is observable.
- **Status-layer coupling.** Confirm the resolution/dice layer and the
  LethalityArbiter actually read the `Penalty` status for the WWN ruleset path
  (the dive is a WWN port). If a roll site bypasses status modifiers, the −2
  silently no-ops there — wire-and-verify, do not assume.
- **First-descent legibility.** Pool starts unlit; entering the dark without
  lighting applies −2 immediately. Ensure the narrator/gauge make this a choice,
  not a trap.
- **Save migration.** Old saves have `resources: {}`; the existing
  `resource_state` migration path must leave them empty and let
  `init_resource_pools` upsert the new `light` pool on load (legacy saves are
  throwaway per project policy — no back-compat heroics).

## 13. Out of this story / future

- Per-PC light for split parties.
- Tactical light-radius / line-of-sight (a different feature that may *read* the
  lit flag).
- Additional environmental clocks (`air`, `cold`) reusing this exact substrate —
  the proof the primitive generalizes.
- Penalty ramp (−1 guttering → −2 dark) if binary proves too coarse in play.
```
