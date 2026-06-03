---
id: 130
title: "Orbital Story-Time Clock and Course Model — Beat-Driven Time Advance and Approximate Hohmann Transit"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [51, 94]
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-130: Orbital Story-Time Clock + Course Model

> **Documents a system already live in code.** The story-time `Clock`, the
> four-kind beat taxonomy, and the approximate course/conjunction model shipped
> across the `sidequest/orbital/` modules during the orbital-chart visual
> restoration work without a governing ADR. ADR-094 covered only *label
> placement* on the rendered orrery; the clock, beat taxonomy, and travel-cost
> model were never written down. This record closes that architecture-of-record
> gap and states what the decision *was*.

## Context

The `space_opera` orbital chart needs to answer three player-facing questions
that the orrery render (ADR-094) alone cannot: *what time is it in the fiction*,
*how long until two bodies align (the conjunction HUD countdown)*, and *how long
/ how much fuel to travel between bodies (the `<courses>` block)*. Those are
time-and-distance questions, and they sit beneath the SVG, not in it.

Two design tensions shaped the implementation:

1. **What advances story-time?** Wall-clock is wrong — a session paused
   overnight should not jump the fiction forward 8 hours. Turn-count is also
   wrong — fifty backstory questions are one story moment, not fifty hours of
   travel (the same conflation ADR-051 resolved for the *display* round
   counter). Story-time needs its own axis, advanced only by events that
   actually consume fictional time.
2. **How accurate must the orbital math be?** This is a tabletop space-opera
   chart read by players, not a mission planner. The ETA and Δv numbers exist to
   give mechanics-first players (Sebastien, Jade) *legible, consistent* numbers
   to reason about — "The Gate is 90 hours out, Tethys Watch is 12" — not to
   survive a physics audit. Calibrated, deterministic approximation beats a real
   ephemeris solver here.

## Decision

**Story-time is a third, independent time axis carried by a `Clock` that
advances *only* via typed beat events. Course ETA/Δv and conjunction timing are
computed by a deliberately-approximate, Hohmann-*flavored* model whose
calibration constants are tuned to feel right at the table, explicitly NOT real
orbital mechanics.**

### Beat-only time advance

`Clock` (`orbital/clock.py`) stores absolute story-hours from a world-defined
epoch (`epoch_days: 0`). It is a dataclass with a single mutator: `advance(hours)`
(`clock.py`), which is monotonic non-decreasing and **raises `ValueError` on
negative input** (`clock.py`). Zero is a legal no-op (`clock.py`) — the
engine still records the *attempt* so the OTEL trail is complete. `t_days` is a
derived 24h-per-day view (`clock.py`).

The clock is **never** advanced by wall-clock and **never** by turn count. The
only sanctioned mutation path is a beat — `advance_clock_via_beat`
(`orbital/beats.py`). The module docstring states the invariant directly:
"story-time advances *only* via beats" (`clock.py`).

### Beat taxonomy + durations

`StoryBeatKind` (`beats.py`) is a four-value enum: `ENCOUNTER`, `REST`,
`TRAVEL`, `DOWNTIME`. Each beat (`StoryBeat`, `beats.py`) carries a free-form
`trigger` string (scene id / route id / action id, captured in OTEL) and an
optional `duration_hours`. Duration resolution (`_resolve_duration`,
`beats.py`) is per-kind:

- **ENCOUNTER** — default **1h** (`DEFAULT_DURATIONS_HOURS`, `beats.py`),
  narrator-overridable per scene.
- **REST** — **fixed at 8h**; supplying any non-8.0 duration **raises
  `ValueError`** (`beats.py`). The override is rejected, not silently
  clamped.
- **TRAVEL** and **DOWNTIME** — no default; duration is **always supplied** (by
  the course model for TRAVEL, player-declared for DOWNTIME). Omitting it
  **raises `ValueError`** (`beats.py`).

Every advance emits a `clock.advance` OTEL span (`emit_clock_advance`,
`beats.py`, from `telemetry/spans/clock.py`) carrying beat kind, duration,
before/after hours, and trigger — the GM-panel lie-detector for time advance.

### Approximate course + conjunction model

`compute_eta_and_dv` (`orbital/course.py`) returns `(eta_hours,
delta_v_km_per_s)` for a party-body → destination-body pair. Its docstring is
explicit: **"Hohmann-flavored cost. NOT real orbital mechanics."**
(`course.py`). The model:

- Treats each body's `semi_major_au` as a flat distance proxy — even for moons,
  whose parent is not the system root (`course.py`).
- Builds a "chord" distance from a radial term (semi-major-axis difference) plus
  a small angular term derived from `chord_angular_distance_deg` over the epoch
  phases (`course.py`).
- Scales chord → hours and chord/radial → Δv via three **calibration
  constants** (`course.py`): `TRAVEL_HOURS_PER_AU = 30.0`,
  `DELTA_V_BASE = 0.7`, `DELTA_V_RADIAL_FACTOR = 0.4`. These are tuned so that
  Far Landing → Tethys Watch ≈ 12h and Far Landing → The Gate ≈ 90h — *feel*,
  not physics (`course.py`).
- Identical bodies cost `(0.0, 0.0)` (`course.py`).

`compute_courses` (`course.py`) selects which bodies appear in the narrator's
`<courses>` block by union of in-scope / recently-mentioned / quest-anchor body
ids, with a priority-ordered hard cap of **12** (`COURSES_HARD_CAP`,
`course.py`) to bound prompt-token cost. `PlottedCourse` (`course.py`) is
the committed-course snapshot field, cleared on replace/cancel/arrival and
durable across save/load.

Conjunction timing (`orbital/conjunction.py`) finds the next angular-separation
minimum for the chart HUD countdown via a **two-stage** method: a coarse 1-day
grid scan (`_GRID_STEP_HOURS = 24.0`, `conjunction.py`) to bracket the first
significant local minimum, then **golden-section refinement** to ±0.1h
(`_golden_section_min`, `conjunction.py`). A `_MIN_SIGNIFICANCE_DEG = 0.5`
gate (`conjunction.py`) rejects floating-point-noise false minima from the
Kepler solver. The soonest event across all configured pairs wins
(`next_conjunction`, `conjunction.py`); `None` signals the HUD to hide the
countdown. This is, again, a coarse approximation — good enough to surface a
ticking number, not an ephemeris.

## Invariants / Contracts

- **Story-time advances only via beats.** `Clock.advance` is the sole mutator;
  the only sanctioned caller is `advance_clock_via_beat`. No wall-clock and no
  turn-count path mutates the clock.
- **Monotonic, never negative.** `advance(hours)` raises on negative input
  (`clock.py`); the clock is monotonic non-decreasing. Zero is a legal,
  OTEL-recorded no-op.
- **Per-kind duration rules are enforced loudly.** REST is fixed at 8h
  (non-8.0 override → `ValueError`); ENCOUNTER defaults to 1h but is
  narrator-overridable; TRAVEL and DOWNTIME require an explicit duration
  (`None` → `ValueError`). No silent clamping or defaulting — honors *No Silent
  Fallbacks*.
- **The course/conjunction math is calibrated approximation, not physics.** The
  three `course.py` constants and the conjunction grid step / refinement
  tolerance are tuning knobs, asserted-correct by *feel* against named
  campaign-world ETAs, not by physical correctness. Any contributor reading
  these numbers must treat them as game-feel constants.
- **Bounded prompt cost.** The `<courses>` block is hard-capped at 12 entries,
  dropped in reverse priority order (quest > recent > in-scope) so the
  highest-value courses survive the cap.
- **Every beat advance emits a `clock.advance` OTEL span** so the GM panel can
  verify time moved for a real reason.

## Consequences

**Positive**

- Story-time is decoupled from both real time and turn count — a paused session
  doesn't drift the fiction, and a flurry of zero-time questions doesn't burn
  fictional hours. Travel and rest cost time; chatter does not.
- Mechanics-first players get legible, deterministic ETA/Δv/countdown numbers in
  player-facing surfaces without the engine pretending to a physical fidelity it
  doesn't have.
- The approximate model is cheap, deterministic, and pure (no I/O, no global
  state — `course.py`), so it's trivially testable and stable across save/load.
- The calibration constants are a single, named, tunable surface.

**Negative / cost**

- The course/conjunction numbers will not survive a physics-literate player's
  scrutiny; the "NOT real orbital mechanics" caveat is load-bearing and must
  stay visible in the code and this ADR.
- Story-time advance depends on disciplined beat emission — a code path that
  consumes fictional time but forgets to emit a beat leaves the clock stale.
  The `clock.advance` OTEL span is the detection mechanism.
- Three distinct time axes now exist (interaction, round, story-time); see the
  reconciliation below so they aren't conflated.

## Alternatives considered

- **Wall-clock story-time.** Rejected: a session paused overnight would jump the
  fiction forward by real elapsed hours — the clock would track the table's life,
  not the story's.
- **Turn-count story-time.** Rejected: conflates mechanical exchanges with
  narrative progress, the exact failure ADR-051 documents for the display
  counter. Fifty backstory questions are one story moment, not fifty hours.
- **Real orbital mechanics (true Hohmann transfer / ephemeris solver).**
  Rejected: enormous accuracy for a tabletop chart that only needs consistent,
  believable numbers. The calibrated-constant approximation delivers the
  player-facing legibility at a fraction of the complexity and with full
  determinism.

## Reconciliation with ADR-051 and ADR-094

- **ADR-051 (Two-Tier Turn Counter — Interaction vs. Round):** ADR-051 governs
  two *turn* counters (`interaction`, `round`) that advance in lockstep on every
  player-narrator exchange. The orbital `Clock` is a **third, independent axis —
  story-time in hours** — and it is explicitly *not* coupled to either turn
  counter. A turn may advance the round counters while the story clock stays put
  (a question), or a single beat may advance the story clock by 90 hours within
  one turn (a long transit). They measure different things: turn counters measure
  *exchanges*, the orbital clock measures *fictional elapsed time*.
- **ADR-094 (Orrery Label Placement — Three-Strategy Taxonomy):** ADR-094 governs
  *only* how labels are placed on the rendered orbital SVG (textpath / radial /
  callout, collision tiers, upright-flip). It says nothing about the story-time
  clock, the beat taxonomy, or the course/conjunction cost model — those live
  below the renderer in `clock.py`, `beats.py`, `course.py`, and
  `conjunction.py`. `render.py` consumes `t_hours` to position bodies but does not
  own how that time advances. This ADR is the architecture-of-record for the
  time-and-distance model that ADR-094 left uncovered.
