# Forensics Telemetry Phase 2 — Mechanical-State Coverage — Design Spec

**Status:** approved design (brainstorming complete) → next: writing-plans for Phase 2.
**Scope of this spec:** Phase 2 only. Phase 1 (the substrate + sink + read path +
decision-telemetry lane) is MERGED & human-verified (sidequest-server PR #333,
develop `4482670`). Phase 3 (living-world coverage) remains a deferred follow-on,
its own spec→plan cycle.
**Owning repo:** `sidequest-server` (feature branch off `develop`; cut the subrepo
branch *before* dispatching implementers — gitflow). The forensics UI touch is
`sidequest/server/static/forensics.html` in the same repo. This design doc lives
in the orchestrator repo (`docs/superpowers/specs/`, targets `main`), mirroring
the Phase 1 spec's placement.
**Predecessor:** `2026-05-18-forensics-telemetry-substrate-design.md` (Phase 1).

---

## Problem

Phase 1 made the save *able* to remember the per-turn telemetry stream: a sink in
`watcher_hub.publish_event` persists every `_watcher_publish` payload into an
append-only `turn_telemetry` table, read back per-round and shown in the
`/forensics` "decision telemetry" lane. **Phase 1 added no instrumentation — it
persists whatever is emitted today.**

What is emitted today is uneven. A source-confirmed audit (2026-05-18, from
production call sites — not log-absence, per `feedback_log_absence_not_deadness`)
found:

- **Fully instrumented:** Encounter / Dice (30+ `state_transition` ops),
  Confrontation (9 ops — morale, flee, resolve, deactivate-on-move). No Phase 2
  work needed.
- **Partial / misleading:** Location (1 event — bare location change; no
  room-graph entry/exit, no multi-PC formation), Inventory (2 events — only
  *recipient resolution*, **not** item add/remove), XP (1 event — only
  post-encounter `award_turn_xp`; no tier crossings, no ability unlocks),
  Trope (1 event — tension round-classification only; no keyword/topic
  transitions).
- **Stone silent:** **HP / Edge / Composure.** Zero watcher events. OTEL spans
  exist (`encounter_edge_debit_span`) but nothing reaches the save.

Consequence: the GM panel — Keith's lie detector for "convincing narration with
zero mechanical backing" (CLAUDE.md OTEL principle) — cannot see whether a
narrated wound, a pocketed key, or a level-up actually moved any number. The
substrate is ready; the mechanical truth is simply never photographed.

## Goal & non-goals

**Goal (Phase 2):** every seated PC's mechanical state — location/room-graph/
formation, HP/Edge/Composure, inventory, XP/tier/advancements, trope progress —
is photographed once per round, persisted by Phase 1's existing sink, and
surfaced in the forensics page as a per-round per-PC mechanical **diff** plus a
macro-strip mechanical lane, so a narration-vs-mechanics discrepancy is *visually
obvious* to the GM.

**Non-goals (Phase 2), locked in brainstorming:**

- No narration-text parsing, no automated accusation, no discrepancy badging.
  The tool is **descriptive + passive contrast** — the GM reads the numbers and
  judges; the contrast does the work.
- No deterministic engine-invariant tripwires (the rejected "Approach C-flag"
  middle ground).
- **No Phase 1 code changed** — not the sink, not the `turn_telemetry` schema,
  not the transaction logic. Phase 2 is purely a new emitter + a new pure
  read-fold + a UI lane.
- Dice / confrontation instrumentation untouched (already covered).
- No event-sourcing of individual mutations (Approach A rejected — see Decisions).
- No backfill of pre-Phase-2 rounds (the state was never photographed —
  impossible, and never fabricated).

## Decisions locked (from brainstorming)

1. **Scope = all five gap areas:** HP/Edge, inventory, location/room-graph,
   XP/progression, trope. One spec→plan; the plan may sequence internally.
2. **Purpose = descriptive + passive contrast.** No NLP, no accusation, no
   deterministic tripwires.
3. **Emission model = B, per-round per-PC mechanical census.** One emission
   point; the read-fold diffs consecutive censuses.
   - *Rejected A (event-sourced transitions):* ~20 invasive call sites + ~20
     wiring tests, large regression surface, and it *propagates* the
     uneven-coverage disease forward (every future mutation path must remember
     to emit).
   - *Rejected C (census + bounded transitions) for initial scope:* deferred —
     added later *only if* a real census ambiguity bites in playtest, as its
     own small spec.
   - *B chosen because* it photographs **state**, not mutations: one call site,
     trivially wiring-tested, sealed-rounds-correct by construction, and
     structurally future-proof — a mutation path written next year is still
     captured because the census reads canonical state, not replayed emitters.

## Architecture

Phase 2 adds exactly three things — one emitter, one pure read-fold, one UI
lane — and changes nothing in Phase 1.

```
end-of-round (state settled, INSIDE the open C2 turn transaction)
  └─ for each SEATED pc:
        _watcher_publish("census", fields, component="mechanical")
          └─ (Phase 1 sink, UNCHANGED) → turn_telemetry row,
                committed atomically with the turn via the
                existing conn.in_transaction branch

forensics read ── ?mode=ro (never creates the table — Phase 1 discipline)
  └─ forensic_query: component="mechanical" rows, bucketed by round
       └─ fold_mechanical_census(rows)   # NEW, pure, consecutive-diff
            └─ build_turn_bundle["mechanical"]
                 ├─ per-round per-PC mechanical-diff <details> block
                 └─ macro-strip mechanical lane
```

A census row **is** a `turn_telemetry` row with `component="mechanical"`. No new
table, no schema change, no transaction logic — Phase 1's sink already does all
of that and its atomic-commit / rollback-with-the-turn guarantee is inherited
for free.

### The one load-bearing unknown (plan's first task)

The census must fire **after** all mechanical state for the round has settled
**and inside** the open C2 turn transaction — so Phase 1's `in_transaction`
sink branch persists it atomically. Out-of-transaction emission would lose the
crash-round census, the exact failure mode Phase 1 explicitly rejected. The
exact pipeline hook point is **the plan's first task to confirm from source**,
deliberately mirroring how the Phase 1 spec named the `_watcher_publish`-store
question as its load-bearing first task. Everything else is mechanical once
that point is pinned. No silent fallback — the chosen point must be explicit.

### State is read, never reconstructed (plan's second task)

The census reads the **canonical** game-model objects — the same ones the
engine treats as truth — not replayed emitter events. This is precisely why B
cures the uneven-coverage disease. The plan's second task confirms the exact
canonical accessors; the 2026-05-18 audit already located the modules
(`creature_core` / edge pool, inventory model, `resource_pool` for xp,
trope/tension engine, `state.location` + room graph).

## Components

### 1. Emitter — per-round per-PC mechanical census (new)

One emission point. For each **seated** PC (ADR-036 sealed rounds — every
seated PC every round; there is no "acting player"), emit one
`_watcher_publish("census", fields, component="mechanical")`. Fully wrapped:
telemetry never crashes a turn (Phase 1's contract, inherited).

**Census schema — "mechanical state," precisely, per seated PC per round:**

| group | fields | canonical source (plan confirms exact accessor) |
|---|---|---|
| identity | `player_id`, `character_name`, `round`, `seat` | turn_manager / session roster |
| location | `location_id` + label, room-graph `node`, party `formation`/`adjacency` | `state.location` / room graph |
| vitals | `edge` (cur/max), `composure` (cur/max), `down`/threshold flags | `creature_core` / edge pool |
| inventory | digest `[{item, qty}]` + stable `inv_hash` (cheap diff key) | inventory model |
| progression | `xp_total`, `tier`/`level`, `pending_advancements`, unlocked-ability flags | `resource_pool` |
| trope | active tropes + `progress` / activation counters | trope engine / tension tracker |

Payload is a bounded fixed field-set × party size — tiny against the ~50
`turn_telemetry` rows/turn already measured in Phase 1. `round` is carried
explicitly in the payload (the read path buckets on it; covers NULL
`event_seq`).

### 2. Read path — `forensic_query.py`

`build_turn_bundle` gains a `mechanical` key alongside Phase 1's `telemetry`.
Census rows = `turn_telemetry` rows with `component="mechanical"` for the
round, keyed by the `round` column (plus `event_seq` for stable ordering).
Read strictly `?mode=ro`; the read path **never creates the table** (Phase 1
discipline, `project_sqlitestore_open_writes`).

### 3. Read-time fold — `fold_mechanical_census(rows)` (new, pure)

Mirrors `fold_turn_telemetry` / `fold_known_facts`: pure, no I/O, never raises,
defensive `esc`, unparseable rows loud-skipped **and recorded** (identical
contract to the two folds already in-tree). One job: group census rows by
`round` then `player_id`, and compute each PC's diff against **that PC's
previous-round census**:

- location: `Ropefoot → The Kept Fire` (or `·` if static)
- vitals: `Edge 10→7 (−3)`, `Composure 4→4`
- inventory: `+brass key, −torch×1`
- progression: `+15 xp`, `tier 2→3` (badged when a tier line is crossed)
- trope: `vengeance 2→3`

**Three honest states, three distinct renderings — never conflated:**

- **moved** — diff shown.
- **static** — `· no mechanical change` (the census fired; nothing changed).
- **absent** — `— no mechanical census (save predates Phase 2 coverage)`
  (the census never fired).

First round per PC = **baseline, not a spurious diff** (no prior census → show
absolute state, no deltas). It is a poor sort of forensics that shows the same
face for "nothing happened" and "we weren't watching."

### 4. Forensics UI — two additions, on the established Phase 1 idiom

1. **Per-round mechanical-diff block** — a collapsed `<details>`:
   *"mechanical state (this round) — {n} PCs"*, one sub-block per seated PC
   with the diff above. Discrepancy spotting is passive and visual: narration
   "the blade bites deep" against a row reading `Edge 12→12 ·` is GM-obvious
   with no badge or accusation.
2. **Macro-strip mechanical lane** — the strip row the Phase 1 spec explicitly
   reserved for Phase 2. Per round-column, a minimal marker: mechanical state
   *moved* vs. *static* vs. *absent*. Lets the GM scan a whole session and jump
   to the round where prose and numbers disagree.

Both follow `forensics.html`'s collapsed-`<details>` + macro-strip pattern,
defensive `esc()` on every value (existing contract).

## Data flow

1. Turn runs; mechanical state mutates through whatever paths exist.
2. End of round, state settled, inside the open C2 turn transaction → for each
   seated PC, emit one `component="mechanical"` census event.
3. Phase 1's sink (unchanged) appends one `turn_telemetry` row per census in
   the turn's transaction.
4. Turn commits → census committed atomically with it (or rolled back with it
   — no orphan/partial; inherited from Phase 1).
5. Later: forensics opens the save `?mode=ro`, buckets `mechanical` rows by
   round, folds them into per-PC consecutive diffs, renders the lane.

## Error handling

- **Per-PC failure isolation:** a census-build failure for one PC loud-logs
  `mechanical_census.build_failed pc=<id>` and continues; other PCs' rows and
  the turn are unaffected. A missing PC row reads as **absent**, never a zeroed
  body — no silent fallback, no fabricated state.
- **Emitter:** fully wrapped; telemetry never crashes a turn (Phase 1 contract).
- **Read/fold:** degrades to empty, never 500; unparseable payloads
  loud-skipped and recorded.
- **Transaction safety:** inherited free from Phase 1's unchanged sink — Phase 2
  adds zero transaction logic.

## Testing & verification (success criteria)

- **Per-subsystem accuracy:** seeded character → census payload carries correct
  location, Edge/Composure, inventory digest, xp/tier, trope progress read from
  the canonical model. One assertion family per gap subsystem — this is also
  the anti-log-absence proof: each gap closed against real state, not a hoped-for
  emitter.
- **Pure fold:** consecutive-diff correctness; first-round = baseline (no
  spurious diff); no-change = empty diff (the *static* rendering, not *absent*);
  unparseable loud-skip + recorded; honest-empty.
- **Mandatory wiring test** (CLAUDE.md "Every Test Suite Needs a Wiring Test"):
  a *real production turn* writes one `component="mechanical"` row per seated PC
  into `turn_telemetry` — not a unit stub. Proves emission from the live
  pipeline.
- **Sealed-rounds / MP:** 2+ seated PCs → exactly one census row per PC per
  round, no acting-player bias (ADR-036, `feedback_sealed_rounds_no_acting_player`).
- **Read-only byte-identity + never-500:** a save with census rows is not
  mutated by a forensics read (mirror Phase 1's forensics suite,
  `project_sqlitestore_open_writes`).
- **Acceptance gate (deferred human verification, mirrors the Phase 1
  verification run 2026-05-18):** a fresh playtest save's `/forensics` shows,
  for every round and every PC, the mechanical diff; a deliberately
  narrated-damage-with-no-Edge-move round is visually identifiable from the
  contrast alone.

## Observability

The forensics page **is** the observability for this layer (don't recurse a
watcher event about the census into the census). Health tells: the loud
`mechanical_census.build_failed` WARNING, and the per-round census row count
visible in the mechanical lane / macro strip (parallels Phase 1's
`turn_telemetry.sink_failed` + row-count tell).

## Migration / back-compat

Forward-only. **No schema change, no new table** — census rows are
`turn_telemetry` rows with `component="mechanical"`. Pre-Phase-2 rounds honestly
render the *absent* state. No backfill (the state was never photographed —
impossible, never fabricated). Phase 1's `CREATE TABLE IF NOT EXISTS` already
provisions the table on the live write path; the read path still must not
create it.

## Risks & mitigations

- **Emission-point placement** (the load-bearing unknown): wrong point = census
  reads pre-settle state or commits outside the turn txn. Mitigation: plan's
  first task confirms it from source, explicit, no silent fallback.
- **Canonical accessor drift:** the census must read true engine state.
  Mitigation: plan's second task pins exact accessors; per-subsystem accuracy
  tests assert payload == canonical model for a seeded character.
- **Payload size:** bounded fixed field-set × party size; tiny vs. the measured
  ~50 `turn_telemetry` rows/turn. Inventory carried as a digest + hash, not full
  item blobs. Noted, not gated.
- **No-change vs. predates conflation:** explicitly three distinct renderings;
  a fold test asserts the static and absent paths render differently.

## Phases (status)

- **Phase 1 — substrate + sink + decision-telemetry lane.** MERGED &
  human-verified (sidequest-server PR #333, develop `4482670`).
- **Phase 2 — mechanical-state coverage.** *This spec.*
- **Phase 3 — living-world coverage.** Deferred follow-on, its own spec→plan:
  NPC disposition/OCEAN shifts, gossip/relationship propagation, scenario
  clue-graph & belief state, coal→diamond world-fact promotions → a
  world-evolution lane (same census-style pattern is the likely shape).

## Handoff

Phase 2 → writing-plans skill → TDD implementation (the White Rabbit). Feature
branch off `sidequest-server` `develop`, cut before any implementer dispatch.
Plan's first two tasks are the named load-bearing unknowns (emission point;
canonical accessors); the rest is mechanical.
