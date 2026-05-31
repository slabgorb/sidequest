---
id: 124
title: "Save-Forensics Architecture — Read-Only Tiered Save Inspection, Loud-Skip Folds, and Per-Round Mechanical Census"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [14, 31, 100, 115]
tags: [observability, game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-124: Save-Forensics Architecture

> **Documents a system already live in code.** The save-forensics stack —
> strict read-only save opening (`forensic_query._ro_connect`), the per-round
> drill-down bundle, the three pure folds (`forensic_fold.py`), the per-round
> mechanical census (`mechanical_census.py`), and the Postgres reader
> (`pg/forensic.py` `PgForensicReader`) — shipped during the ADR-115 substrate
> work without a governing ADR. ADR-115 mentions `_ro_connect` only in passing.
> This record closes that architecture-of-record gap and states what the
> decision *was*.

## Context

SideQuest's GM panel is "the lie detector" (CLAUDE.md OTEL principle): the only
way to tell whether a subsystem actually fired — versus the narrator improvising
convincing prose with no mechanical backing — is to inspect what the engine
recorded. Live OTEL spans answer that for a *running* turn. But a finished save
is a different artifact: a static autopsy where the question is "what did the
engine establish, round by round, over the whole game, and does the narrative
match the mechanics?" That autopsy needs to read a saved game **without
disturbing it**, reconstruct the per-round picture, and present it honestly —
distinguishing what was *stored* from what is *derived*.

Three forces shaped the architecture:

1. **Inspecting a save must never mutate it (the WAL/save-clobber hazard).**
   Under the legacy SQLite-per-session store, `SqliteStore.open` *writes on
   construction* — schema init, migrations, a commit, and `journal_mode=WAL`
   (`forensic_query._ro_connect` docstring, `forensic_query.py:26-31`). Opening a
   live save through that path to "just look at it" would clobber bytes, flip the
   journal mode, and race a running session. Forensics had to open strictly
   read-only.
2. **A corrupt or partial save must never 500 the page.** Forensics exists
   precisely to inspect *broken* games. Every decode and every fold therefore
   degrades loudly-but-gracefully: a bad row is logged and skipped, never
   silently dropped and never allowed to crash the inspection
   (`forensic_query.py:350-364`, `forensic_fold.py:54-101`).
3. **Mechanics-first players (Sebastien, Jade) want legible crunch.** The
   narrative event log alone does not answer "what was each PC's HP/XP/inventory
   at round N, and what moved between rounds?" — that signal was never
   event-sourced. A dedicated per-round mechanical census fills it
   (`mechanical_census.py:125-191`).

The system is also a study in **three truth tiers**, which the UI must keep
visually distinct (the "amber-badge" doctrine, below).

## Decision

### RO inspection tiers — the per-round bundle

The forensics reader assembles, **per narrative round**, a bundle of panels that
deliberately separate *what the engine stored* from *what we reconstruct*
(`forensic_query.build_turn_bundle`, `forensic_query.py:367-488`; PG port
`pg/forensic.py:496-671`). The bundle keys are:

- `narrative` — verbatim `narrative_log` rows for the round
  (`forensic_query.py:379-392`).
- `events` — verbatim `events` rows in this round's seq window
  (`forensic_query.py:410-423`).
- `projection` — verbatim `projection_cache` rows (the per-player rendered lens)
  for the seq window (`forensic_query.py:444-457`).
- `scrapbook` — verbatim `scrapbook_entries` for the round
  (`forensic_query.py:459-476`).
- `derived` — the **reconstructed** KnownFacts ledger (see folds below),
  amber-badged by the UI as *derived, not stored* (`forensic_query.py:425-442`).
- `telemetry` — folded `turn_telemetry` rows for the round
  (`forensic_query.py:300-347`).
- `mechanical` — the folded per-PC mechanical census diff
  (`forensic_query.py:222-275`).

Rounds are bucketed by **narrative timestamp boundaries**: `events` rows carry no
round column, so each round's seq window `[seq_start, seq_end]` is derived from
the min `created_at` of consecutive narrative rounds (`_round_boundaries` →
`_events_for_round` → `build_timeline`, `forensic_query.py:118-188`). An unknown
round, or a round with no events, returns the **empty bundle** rather than
raising (`forensic_query.py:394-405`).

### The three pure folds (`forensic_fold.py`)

All three are pure (no I/O), accept rows in any order, sort internally, and
honor the **loud-skip, never-raise** contract:

1. **`fold_known_facts`** (`forensic_fold.py:54-101`) — folds the trusted event
   log into the derived KnownFacts ledger keyed by `fact_id`. **Footnotes, not
   `state_delta`:** recorded `events` are only `NARRATION` / `SCRAPBOOK_ENTRY`,
   and NARRATION payloads carry footnotes, not a `state_delta` key
   (`forensic_fold.py:1-19`); the footnote/KnownFacts stream (ADR-100) is the only
   genuinely *per-turn, derived-not-stored* signal in the log. `source_seqs`
   accumulates every asserting seq in order; `value` is the highest-seq
   assertion's `{summary, category}`. A non-dict payload or a footnote with no
   string `fact_id` is logged (`forensic_fold.unparseable_payload` /
   `malformed_footnote`) and skipped — well-formed siblings in the same event
   still fold.
2. **`fold_turn_telemetry`** (`forensic_fold.py:129-194`) — curates a round's
   `turn_telemetry` rows into `rows` (seq-ordered), `by_component` (component →
   event_type → count), `total`, and `unparseable_seqs`. A row with no usable int
   `seq` is logged and skipped but *not* recorded in `unparseable_seqs` (there is
   no seq to record).
3. **`fold_mechanical_census`** (`forensic_fold.py:321-409`) — folds this round's
   `component='mechanical'` census rows against the **previous census round's**
   rows into a per-PC typed consecutive diff (`PcMechanicalDiff`,
   `forensic_fold.py:200-213`). Per PC: no prior → `baseline`; prior == current →
   `static`; else `moved` with typed deltas computed by `_pc_deltas`
   (`forensic_fold.py:268-318`) over location, edge/HP, xp, level, inventory
   (name-aggregated set-diff), and acquired advancements. Session trope state is
   diffed separately (`forensic_fold.py:376-401`). The round's rolled-up `state`
   is `absent` / `static` / `moved`.

A fourth fold, `fold_mechanical_strip` (`forensic_fold.py:412-456`), computes a
whole-save per-round tri-state strip in one pass. It is **intentionally unwired
in production** — the macro strip is rendered client-side from the per-round
bundle cache; the strip fold and its caller `mechanical_strip`
(`forensic_query.py:278-297`) are retained as the forward (Phase-3) server-side
seam, exercised by tests only, not dead code.

### Mechanical census schema (`mechanical_census.py`)

The census is emitted at turn time, not reconstructed. `emit_mechanical_census`
(`mechanical_census.py:125-191`) writes, per **seated PC every round** (sealed
rounds, ADR-036 — keyed by `player_id`, no acting-player concept), one
`event_type='census'` row, plus one session-level `event_type='trope_census'`
row, all `component='mechanical'`. Per-PC fields (`build_pc_census`,
`mechanical_census.py:55-99`): `player_id`, `character_name`, `seat`, `round`,
`location`, `chassis_room`, `edge` (the ADR-114 `HpPool` `current`/`max`/
`base_max`), `down` (`is_broken()`), `statuses`, `inventory` (name-aggregated
digest via `inventory_digest`, `mechanical_census.py:18-35`), `inv_hash`, `gold`,
`xp`, `level`, `acquired_advancements`, `ability_count`. Session trope fields
(`build_trope_census`, `mechanical_census.py:102-122`): per-trope
`id`/`status`/`progress`/`beats_fired`/`last_fired_turn`, plus
`turns_since_meaningful` and `total_beats_fired`. The census must be called from
inside `emit_event`'s open turn transaction with that turn's `tx` and
`event_seq`, so each row rides the turn txn on the same connection (atomic with
`events`, event_seq attributed) — the `tx` is threaded explicitly, never sniffed
(ADR-115 D5).

### Two readers, one contract

`forensic_query.py` is the SQLite reader (`?mode=ro` opens, `sqlite_master`
table probes, timestamp normalization). `pg/forensic.py`'s `PgForensicReader`
(`pg/forensic.py:310-671`) is the Postgres reader: lock-free MVCC pooled reads
(`with pool.connection()`, no `session_tx`, no `FOR UPDATE`), no `sqlite_master`
probes (tables always exist under PG). **Both return byte-identical bundle
shapes** and reuse the same `forensic_fold` functions unchanged — the folds fold
plain dicts and are engine-agnostic (`pg/forensic.py:496-519`).

## Invariants / Contracts

1. **Strict `?mode=ro` — no WAL clobber.** `_ro_connect` opens
   `file:{db_path}?mode=ro` with no schema init, no migration, no journal flip
   (`forensic_query.py:26-37`). Opening a WAL-mode save read-only materializes
   only a harmless `save.db-shm` read-side index — *not* a main-db write — so
   `list_saves`' byte-identity contract holds. `open_save_readonly` probes with
   `SELECT 1` and returns `None` (logged) on a non-sqlite/corrupt file rather than
   raising (`forensic_query.py:491-510`). Under Postgres the equivalent invariant
   is "reads never lock and never write": plain MVCC pooled connections only
   (`pg/forensic.py:9-12, 310-318`).
2. **Loud-skip, never raise.** A corrupt save must never 500 the forensics page.
   Every JSON decode logs loudly and degrades — `_safe_json_list` →
   `[]` (`forensic_query.py:350-364`), `_safe_json` → `{"__unparseable__": raw}`
   sentinel (`forensic_query.py:198-204`) — and every fold records bad rows in
   `unparseable_seqs` rather than aborting (`forensic_fold.py:73-101, 144-194,
   228-258`). The PG reader adds `_safe_json_logged` so the snapshot/encounter
   reads log the sentinel too (`pg/forensic.py:67-99`). Census *emission* is
   likewise fully wrapped: any roster-resolution or per-PC build failure
   loud-logs and continues — telemetry never crashes a turn, and one bad PC never
   drops the others or the trope row (`mechanical_census.py:143-191`).
3. **Truth-tier separation / amber-badge.** Three tiers stay distinct and must
   not be conflated in the UI: **stored snapshot** (the single authoritative
   `game_state` blob), **projection lens** (`projection_cache`, the per-player
   rendered view), and **derived footnotes** (`fold_known_facts`' reconstructed
   KnownFacts ledger). `derived` is the narrator's accumulating working memory
   reconstructed from footnotes — *not* a stored fact — and the UI amber-badges
   it as distinct from the stored snapshot (`forensic_query.py:367-376`;
   `forensic_fold.py:1-19`). This is ADR-014's honesty doctrine applied to
   inspection: do not present a reconstruction as if it were ground truth.
4. **Census lockstep with rounds.** Exactly one census per seated PC per round,
   plus one trope census per round, attributed to that turn's `event_seq` inside
   the turn transaction (`mechanical_census.py:125-141`). Read-side, the per-round
   mechanical diff buckets rows by `event_seq ∈ [seq_start, seq_end]` *or*
   `round == round_number` (covering NULL-event_seq rows), and diffs against the
   most-recent *prior census round* — not merely round N−1 — via `MAX(round) …
   round < ?` (`forensic_query.py:222-275`; `pg/forensic.py:232-302`).
5. **Lexical-sort dependence on timestamp normalization.** Round bucketing is a
   lexical string comparison of `created_at`. Under SQLite the two tables use
   *different* formats — `events` is Python `.isoformat()` (`T` separator,
   microseconds, tz); `narrative_log` is `datetime('now')` (space, second
   precision, no tz) — so the event side is normalized with `_NORM_EV_TS`
   (`substr(replace(created_at,'T',' '),1,19)`) to make the bucket comparison
   correct (`forensic_query.py:127-153`). Under Postgres **both** columns are
   written by `datetime.now(tz=UTC).isoformat()` — identical format — so
   identically-shaped ISO-8601 strings sort as wall-clock time and `_NORM_EV_TS`
   is deliberately *not* applied (`pg/forensic.py:13-32, 134-172`).

## Observability

The census is itself an OTEL/telemetry sub-stream, not a side file. Each census
and trope-census row is published through the Phase-1 watcher sink as
`component='mechanical'` (`mechanical_census.py:181, 188` → `publish_event`,
`telemetry/watcher_hub.py:534`), so it lands in the same `turn_telemetry`
substrate as every other watcher event and is attributed to the turn's
`event_seq`. This makes the mechanical census a new sub-stream *under* ADR-031's
semantic telemetry: the GM panel can verify the census actually fired (rows
exist, PCs photographed) rather than trusting prose. `list_saves` surfaces both
`telemetry_rows` and `mechanical_rows` counts per save so an empty mechanical
stream is visible at the save-select level (`forensic_query.py:75-111`;
`pg/forensic.py:327-385`). The reader emits its own loud-log warnings on every
skipped/unparseable row (`forensic_query.unparseable_json_list`,
`forensic_fold.*`, `mechanical_census.*`), making degraded inspection observable
in the server log rather than silent.

## Consequences

**Positive**

- A finished save can be inspected, round by round, without any risk of mutating
  or racing it (RO discipline / MVCC reads).
- Corrupt and partial saves remain inspectable — the page degrades to honest
  empties and logged skips instead of crashing, which is exactly when forensics
  is most needed.
- The three truth tiers are kept honest: derived KnownFacts are visibly distinct
  from the stored snapshot and the projection lens (amber-badge), so an inspector
  cannot mistake reconstruction for ground truth.
- Mechanics-first players get a per-round, per-PC mechanical autopsy (HP, XP,
  level, inventory, advancements, location, tropes) that the narrative log alone
  never recorded.
- One fold layer serves both the SQLite and Postgres readers unchanged; the PG
  port swapped only the data source, not the bundle contract.

**Negative / cost**

- Round bucketing rests on timestamp lexical-sort correctness, which is
  engine-specific: SQLite needs `_NORM_EV_TS`, Postgres must not apply it. A
  future change to either table's timestamp format would silently misbucket rounds
  unless the normalization assumption is revisited.
- The census doubles per-turn telemetry volume (one row per seated PC per round,
  plus trope) — acceptable as a sub-stream, but it grows `turn_telemetry`.
- `fold_mechanical_strip` / `mechanical_strip` are carried but unwired (Phase-3
  seam); contributors must know the macro strip is rendered client-side today.

## Alternatives considered

- **Read-write inspection (open the save the normal way).** Rejected: the normal
  `SqliteStore.open` path writes on construction (schema, migrations, commit, WAL
  flip) — it would clobber the very bytes being inspected and could race a live
  session. The WAL/save-clobber hazard is the whole reason `_ro_connect` exists
  (`forensic_query.py:26-37`).
- **Event-source mechanical state instead of a census (backfill / derive from
  the event log).** Rejected: recorded `events` are only `NARRATION` /
  `SCRAPBOOK_ENTRY` and carry no `state_delta` (`forensic_fold.py:1-19`), so per-PC
  HP/XP/inventory at round N cannot be reconstructed from the log. There is
  nothing to backfill from; the census must be *captured* at turn time, which is
  why `emit_mechanical_census` projects canonical state into telemetry rather than
  the read path deriving it.
- **Raise on corrupt rows.** Rejected as hostile to the very use case — a 500 on
  a broken save defeats the inspector. Loud-skip preserves both visibility (logs,
  `unparseable_seqs`) and availability.

## Reconciliation with ADR-014 / 031 / 100 / 115

- **ADR-014 (Diamonds and Coal — Living World / honesty doctrine):** the source
  of the truth-tier/amber-badge discipline. ADR-014 governs how the *game*
  presents established detail honestly; it does not govern a save-inspection
  surface. This ADR applies its honesty principle to forensics: derived KnownFacts
  are presented as reconstruction, never as stored ground truth
  (`forensic_query.py:367-376`).
- **ADR-031 (Game Watcher — Semantic Telemetry):** defines the
  watcher/`turn_telemetry` substrate this reads from. The mechanical census is a
  **new `component='mechanical'` sub-stream** within that substrate
  (`mechanical_census.py:181, 188`); ADR-031 establishes *that* telemetry exists
  and how it is observed, but does not define the census schema, its census/round
  lockstep, or the read-side folds. Insufficient as governance for those.
- **ADR-100 (Journal Pipeline Coherence — Footnotes/KnownFacts):** owns the
  footnote → KnownFacts pipeline that `fold_known_facts` *reads*. ADR-100 governs
  how facts are produced and threaded at play time; it does not govern the
  read-only reconstruction of that ledger for inspection, nor its amber-badged
  presentation against the stored snapshot. The fold is a consumer of ADR-100's
  output (`forensic_fold.py:1-19, 54-101`).
- **ADR-115 (PostgreSQL Persistence Substrate):** the substrate migration that
  produced `PgForensicReader` and *mentions* `_ro_connect` and the MVCC read
  discipline in passing — but ADR-115 governs the persistence substrate, not the
  forensics architecture (the bundle tiers, the three folds, the census schema,
  the lexical-sort/`_NORM_EV_TS` invariant). This ADR is the architecture of
  record for the forensics stack that sits *on top of* ADR-115's substrate
  (`pg/forensic.py:9-32`).
