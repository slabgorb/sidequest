---
id: 128
title: "Trope Temporal Governor, Seed-Trope Deck, and NPC Development Ladder — Pile-Up Prevention and Resume-Safe Randomness"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [14, 18, 25]
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-128: Trope Temporal Governor + Seed Deck

> **Documents systems already live in code.** The trope temporal governor
> (`trope_tuning.py`), its application across per-turn ticks and time skips
> (`trope_tick.py`, `trope_time_skip.py`), the deterministic resume-safe
> seed-trope deck (`seed_deck.py`, `seed_tick.py`), and the interest-driven
> NPC development ladder (`npc_development.py`) all shipped during the
> Epic-22 / 45-27 / 50-4 / 72-1 restoration work *after* ADR-018 was written
> and never had a governing record of their own. This ADR closes that
> architecture-of-record gap — exactly as ADR-117 did for the ruleset seam.

## Context

ADR-018 (Trope Engine) defines the *lifecycle*: dormant → progressing →
resolved, escalation beats firing at progression thresholds, beat
deduplication, and passive `rate_per_turn` / `rate_per_day` advancement so a
story keeps momentum even when players go quiet. What ADR-018 does **not**
describe is what stops the engine from over-firing. Its prose is permissive:
every progressing trope advances every turn, every crossed threshold can fire,
every dormant trope is a candidate to wake. Run that uncapped against a pack
with a dozen authored tropes and you get pile-up.

That is exactly what happened. **Playtest 3 (the Felix session, Sebastien
direct report)** surfaced mid-session pile-up of trope progressions — too many
threads advancing at once, beats firing on top of each other, blurring the
narrative threads a career-GM player expects to be able to follow. The diagnosis
was twofold: too many tropes *active* simultaneously, and the ones that were
active progressing *too fast* (`trope_tuning.py`).

Three distinct mechanisms address three distinct problems, and all three were
built without a governing ADR:

1. **A temporal governor** — calibrated constants that cap concurrency, brake
   progression rate, throttle new activations, and bound prompt-attention depth.
2. **A seed-trope deck** — short-arc seeds dealt at session start and on
   engagement, which must be *reproducible across reload* (Epic 22's
   resume contract) without a new persistence column.
3. **An NPC development ladder** — the dormant coal→diamond promotion path of
   ADR-014, revived as an *interest-driven* tier escalation rather than a
   mechanical-necessity-only one (Story 72-1).

## Decision

### 1. Trope temporal governor (`trope_tuning.py`)

Four playtest-tunable knobs live in a single module so one PR can retune tempo
without grepping the codebase (per ADR-068 magic-literal extraction and the
No-Silent-Fallbacks rule). They are a **multi-dimensional tradeoff** — no single
dial controls "how busy the world feels"; the four cut along different axes:

| Constant | Value | Axis it governs | `trope_tuning.py` |
|----------|-------|-----------------|-------------------|
| `MAX_SIMULTANEOUS_ACTIVE` | `3` | **Concurrency cap** — how many tropes may be `progressing` at once. The (N+1)th candidate stays dormant and emits `trope.cap_blocked`. | `:21` |
| `FIRE_COOLDOWN_TURNS` | `2` | **Activation throttle** — turns of suppression after any beat fires before a *new* `dormant → progressing` transition is allowed. Already-progressing tropes keep advancing during cooldown; the gate is on *new* activations only. | `:28` |
| `FOREGROUND_K` | `2` | **Attention depth** — how many progressing tropes reach the narrator prompt's Early zone as load-bearing beat directives. The rest (up to the cap) render as a Valley-zone summary. | `:35` |
| `PROGRESSION_RATE_MULTIPLIER` | `0.5` | **Rate brake** — a global multiplier on every trope's YAML `rate_per_turn`. Half the playtest-3 pile-up was simply too-fast progression; this halves it before any per-genre authoring change. | `:43` |

The cap and rate brake attack pile-up directly; the cooldown spaces activations
apart in time; `FOREGROUND_K` ensures that even at the cap of 3, the narrator's
attention is never diluted across every active thread. The values are
deliberately **conservative starting points** — playtest can pull them down if
pile-up returns or push them up if the world feels too quiet
(`trope_tuning.py`).

**Application.** `tick_tropes` (`trope_tick.py`) runs the governor every
turn in ordered passes:

- **Pass A** (`_advance_progress`, `trope_tick.py`) multiplies each
  progressing trope's `rate_per_turn` by `PROGRESSION_RATE_MULTIPLIER`
  (`:215`) and emits a per-trope `trope.tick` span.
- **Pass B** (`_fire_one_staggered_beat`, `:236`) fires **at most one beat per
  tick** — the single highest-progress eligible candidate, ties broken
  deterministically by id (`:279`). The fire kicks that trope's
  `fire_cooldown_until = now_turn + FIRE_COOLDOWN_TURNS` (`:283`).
- **Pass D** (`_gate_activations`, `:308`) gates dormant→progressing
  transitions: **cooldown first, then cap.** Cooldown extends through and
  including `cooldown_until` (a fire on turn N blocks N, N+1, N+2 and unblocks
  on N+3; `:326-331`); the cap blocks once `progressing_count >=
  MAX_SIMULTANEOUS_ACTIVE` (`:356`). Refusals emit `trope.cooldown_blocked` or
  `trope.cap_blocked` so the GM panel distinguishes "engine refused" from
  "engine never engaged."
- **Pass E** (`:150-169`) fires the wrapping `turn.tropes` aggregate span *every*
  call, even at zero active tropes — silence on the wire would lie about
  engagement.

`select_foreground_tropes` (`:172`) splits progressing tropes into the
`FOREGROUND_K` most-active (Early zone) and the remainder (Valley zone) for the
prompt-zone wiring.

**Time skips obey the same governor with a different stagger.** When the
narrator emits `days_advanced > 0`, `_pass_a2_time_skip`
(`trope_time_skip.py`) runs between Pass A and Pass B. It advances every
progressing trope by `rate_per_day * clamp(days_advanced, 0, DAY_TICK_CAP)`
where `DAY_TICK_CAP = 14` (`:29`) — a hard bound so a narrator over-emission
("a year passes") cannot resolve every trope in one turn. Unlike Pass B's
one-beat-per-tick stagger, a time skip **fires every crossed beat threshold**
(`:147-171`), because a multi-day jump implies multiple beats landing off-screen
between sessions. The clamp is visible in OTEL via `TropeTimeSkipFields.clamped`.

**Per-genre overrides are deliberately deferred.** A future story may let
`genre_packs/<g>/pack.yaml` override these constants; until then the values are
global (`trope_tuning.py`). `DAY_TICK_CAP` carries the same YAGNI deferral
(`trope_time_skip.py`).

### 2. Deterministic, resume-safe seed-trope deck (`seed_deck.py`, `seed_tick.py`)

Seeds are short-arc, deliberately-vague narrative events (Epic 22) — a sibling
of the long-lived macro tropes. `SeedDeck` (`seed_deck.py`) deals them
**without replacement** from a deck keyed by `(genre_id, world_id, session_id)`.

The reproducibility contract is the load-bearing part. The deck shuffle is
seeded by deriving a stable integer from the `session_id` via **SHA-256**
(`_seed_int`, `seed_deck.py`): the digest is hashed to a big-endian int.
This is justified in-code: a raw string seed fed to `random.seed()` is
**version-sensitive and PYTHONHASHSEED-dependent** via the builtin `hash()`;
SHA-256 is stable across processes and Python versions. The full seed list is
shuffled deterministically once (`random.Random(_seed_int(session_id))`,
`:53`), independent of what has already been dealt.

`draw()` (`:56`) walks the shuffled order and **skips IDs already in
`drawn_ids`**. On reload, `drawn_ids` is reconstructed from the persisted
snapshot — the union of active seeds and ghosts
(`seed_tick.py`) — so the deck re-instantiated after a load deals the same
remaining order it would have dealt mid-session. **No new persistence column**:
the resume contract rides the existing snapshot.

The engine has two draw paths and an expiry tick:

- `ensure_initial_draw` (`seed_tick.py`) deals the opening hand of 3
  (`_DEFAULT_INITIAL_HAND`, `:71`). It is **idempotent on a fresh session** —
  a no-op once any seed lives on `active_seeds` *or* `seed_ghosts`, so reload
  never re-bootstraps (`:96-97`).
- `draw_engaged_seed` (`seed_tick.py`) draws one mid-session seed on player
  engagement, reconstructing `drawn_ids` from the snapshot and emitting
  `SPAN_SEED_DRAWN` with `trigger="engagement"` to distinguish it from bootstrap
  draws.
- `tick_seeds` (`seed_tick.py`) migrates any seed past its `lifespan_turns`
  out of `active_seeds` and into `seed_ghosts` (record-only callbacks), firing
  `SPAN_SEED_EXPIRED`. The migration is idempotent on the same `now_turn`.

### 3. Interest-driven NPC development ladder (`npc_development.py`)

`develop_npc_on_engagement` (`npc_development.py`) revives the dormant
ADR-014 coal→diamond promotion path. On each **non-transactional** engagement —
a narrator cite that resolves to an existing stateful `Npc` (the `npcs_hit`
branch of `narration_apply._apply_npc_mentions`) — the NPC earns depth along a
monotonic, named tier ladder:

```
spawn → acquaintance → established
```

- `non_transactional_interactions` increments (the interest signal, `:89`).
- `resolution_tier` escalates via `tier_for_interactions` (`:47`) at fixed
  thresholds: `ACQUAINTANCE_AT = 3` (`:38`), `ESTABLISHED_AT = 8` (`:39`).
- `disposition` warms by `DISPOSITION_DRIFT_PER_ENGAGEMENT = 2` per engagement
  (`:44`), applied through the clamping `Disposition` constructor (`:91`) — so
  rapport deepens but never grows unbounded (±100 clamp).

The first threshold being `> 1` is the load-bearing invariant: **a single
engagement — or a lone combat hit — never promotes** (`:36-37`). Depth is
earned over several turns of genuine interest, not bought with one mechanical
touch. This is precisely ADR-014's "player shows genuine interest" promotion
trigger, expressed for NPCs rather than items, and it feeds ADR-020 disposition
evolution.

The function returns a frozen `DevelopmentTick` (`:56`) carrying before/after
tier, disposition, and attitude — the caller emits the development-tick and
`disposition.shift` OTEL spans from it. Thresholds and drift live here as named
constants, never as magic literals scattered through the apply branch (`:18-19`).

## Invariants / Contracts

- **Deterministic resume-safe shuffle.** Deck order is a pure function of
  `session_id` via SHA-256→int; identical across processes, Python versions, and
  reloads. Builtin `hash()` / raw string `random.seed()` is forbidden here for
  this reason (`seed_deck.py`).
- **Draw without replacement.** `draw()` never deals a seed whose id is in
  `drawn_ids`; on reload `drawn_ids` is reconstructed from active seeds + ghosts,
  guaranteeing no redeal (`seed_deck.py`, `seed_tick.py`).
- **Idempotent bootstrap / expiry.** `ensure_initial_draw` is a no-op once any
  seed exists; `tick_seeds` produces no duplicate ghost on a repeated `now_turn`.
- **One beat per tick (live play).** Pass B fires at most one beat per
  `tick_tropes` call; time skips are the deliberate exception (every crossed
  threshold).
- **Cooldown then cap.** New activations are gated cooldown-first, cap-second,
  each with a distinct OTEL refusal span. Cooldown is inclusive of
  `cooldown_until`.
- **Rate brake always applied.** Every passive progression delta is multiplied by
  `PROGRESSION_RATE_MULTIPLIER` before mutating `progress`.
- **Day clamp.** Time-skip days are clamped to `[0, DAY_TICK_CAP]`; the clamp is
  reported, not hidden.
- **Threshold > 1 for NPC promotion.** No single engagement promotes an NPC;
  the lowest earned tier (`acquaintance`) requires 3 interactions.
- **Every pass is observable.** `turn.tropes` fires every tick (even at zero
  active); seed draws/expiries and NPC dev ticks each fire their own spans —
  the GM panel can always distinguish "engine engaged, found nothing" from
  "engine never engaged" (CLAUDE.md OTEL Observability Principle).

## Consequences

**Positive**

- Mid-session pile-up (the playtest-3 defect) is bounded on four independent
  axes; the narrative threads a career-GM player tracks stay legible.
- The four knobs are retunable in one PR, so calibration is a content/tuning
  decision, not an engine change.
- Reload is safe by construction: the seed deck deals an identical remaining
  order after a load, with no new persistence and no redeal.
- NPCs earn depth on genuine interest, matching ADR-014's intent and feeding
  ADR-020 disposition evolution — and the threshold>1 rule keeps drive-by
  combat hits from inflating the world's stateful-NPC roster.

**Negative / cost**

- The constants are **global, conservative, and hand-calibrated** from a single
  playtest. Per-genre overrides are deferred, so a pack that genuinely wants a
  busier or quieter tempo has no authoring lever yet.
- The one-beat-per-tick stagger means a backlog of eligible beats drains one per
  turn; a flurry of authored beats can feel rationed in fast play (the
  intended behavior, but a tuning surface to watch).
- The seed-deck resume contract depends on `active_seeds + seed_ghosts` being a
  complete record of dealt ids. A future "seed resolution" path that removes a
  seed from both lists would silently allow a redeal — out of scope for Epic 22
  (ghosts are immutable) but a constraint any follow-on must honor.

## Alternatives considered

- **`random.seed(session_id)` (raw string) vs SHA-256→int.** Rejected the raw
  string seed: `random.seed()` on a string routes through hashing that is
  PYTHONHASHSEED- and version-sensitive, breaking the cross-process / cross-load
  reproducibility the resume contract requires. SHA-256→big-endian-int is
  stable and explicit (`seed_deck.py`).
- **Eviction vs governor for concurrency.** Rejected evicting an in-flight trope
  to make room for a new one. The governor *refuses the new candidate* (it stays
  dormant, emits `trope.cap_blocked`) rather than tearing down a thread already
  in front of the players — dropping a progressing arc mid-beat would be exactly
  the narrative incoherence the governor exists to prevent. Refusal is observable;
  silent eviction would not be.
- **Per-trope rate authoring instead of a global brake.** Deferred, not
  rejected: halving every `rate_per_turn` globally fixed the playtest-3 pile-up
  immediately without touching any pack YAML. Per-genre override remains the
  planned follow-on.

## Reconciliation with ADR-014 / ADR-018 / ADR-025

- **ADR-018 (Trope Engine).** This ADR *updates* ADR-018's drift. ADR-018 owns
  the **lifecycle and beat-dedup** (dormant→progressing→resolved, beats firing at
  thresholds, `rate_per_turn`/`rate_per_day`, no beat fires twice). ADR-018's
  2026-05-13 amendment already records that 45-27 added "activation gating … a
  simultaneous-active cap and a post-fire cooldown window" and that 50-4 added the
  `rate_per_day` time-skip pass. **ADR-128 is the missing detailed record of
  those governor mechanisms** — the calibrated constants, their multi-axis
  tradeoff, the playtest-3 motivation, the one-beat-per-tick vs every-threshold
  stagger split, and the `DAY_TICK_CAP` — plus the seed deck, which ADR-018 never
  mentioned at all (seeds are a sibling engine, not part of the macro-trope
  lifecycle). ADR-018 remains the lifecycle authority; ADR-128 is the
  governor-and-deck authority.
- **ADR-014 (Diamonds and Coal).** `npc_development.py` *implements* the
  coal→diamond ladder for NPCs. ADR-014's promotion trigger — "player shows
  genuine interest" — becomes the `non_transactional_interactions` interest
  signal and the spawn→acquaintance→established tier ladder, with the threshold>1
  rule enforcing that interest must be *sustained* (the ADR-014 spirit: depth is
  earned, not free).
- **ADR-025 (Pacing Detection).** Complementary, not overlapping. ADR-025 detects
  *too little* momentum (quiet-turn counting) and prompts the engine to push.
  ADR-128's governor bounds *too much* momentum (pile-up). Together they form the
  two-sided pacing envelope: ADR-025 raises the floor, the governor lowers the
  ceiling.
