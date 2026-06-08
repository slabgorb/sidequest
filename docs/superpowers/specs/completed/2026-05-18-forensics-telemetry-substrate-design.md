# Durable Telemetry Substrate for Save Forensics — Design Spec

**Status:** approved design (brainstorming complete) → next: writing-plans for Phase 1.
**Scope of this spec:** Phase 1 only (the substrate + sink + read path + minimal
forensics lane). Phases 2–3 are named as follow-on sub-projects, each its own
spec→plan cycle.
**Owning repo:** `sidequest-server` (branch off `develop`). The forensics UI
touch is `sidequest/server/static/forensics.html` in the same repo.

---

## Problem

Save Forensics is the post-mortem counterpart to the live OTEL `/dashboard`.
It is **data-starved by the recording layer, not the UI**. Verified
2026-05-18 across all real saves: the `events` table holds only `NARRATION`
and `SCRAPBOOK_ENTRY`; `game_state` is a singleton row
(`INSERT OR REPLACE id=1`) overwritten every save, so there is no per-round
history; there is no per-event `state_delta`. Meanwhile a rich per-turn
telemetry stream is computed every turn via `_watcher_publish(...)` (intent
classification, beat selection, `state_transition` fields, projection/
perception decisions — the live "lie-detector" stream, ADR-031/103) and
sent only to OTEL/Jaeger. **None of it is persisted to the save.** The
autopsy cannot show what the live dashboard showed, because the save never
kept it.

This is the same root cause behind the `state_delta` / per-round-location
findings already fixed this session (see
`2026-05-18-save-forensics-ux-tufte.md`, and the KnownFacts fold): the
forensic value the tool needs was never written down.

## Goal & non-goals

**Goal (Phase 1):** every `_watcher_publish` payload is persisted verbatim,
append-only, into the save itself, atomically with the turn that produced
it, and surfaced per-round in the forensics page via a read-time fold.

**Non-goals (Phase 1):** no curation/normalization at write time (raw,
explicitly chosen); no macro-strip changes; no new watcher *instrumentation*
(Phases 2–3 audit/extend subsystem emission — Phase 1 persists whatever is
emitted today); no backfill of existing saves (impossible — the telemetry
was never captured).

## Decisions locked (from brainstorming)

1. One durable substrate; all three richness layers (lie-detector
   telemetry / mechanical-state history / living-world evolution) layer on
   it; phased.
2. **Raw** watcher payloads, append-only; curation happens at **read time**
   in the fold layer (mirrors `fold_known_facts`).
3. Write path = **synchronous append inside the turn's existing C2
   transaction** (Approach A). Async/buffered (B) and sidecar-DB (C)
   rejected — B loses the crash-turn telemetry you most want; C makes the
   save non-self-contained, the exact multi-file fragility the
   save-preservation memories flag.

## Architecture

```
turn pipeline ──> _watcher_publish(event_type, fields, *, component)
                        │
                        ├─(existing)─> OTEL watcher ─> gRPC ─> Jaeger   (live /dashboard)
                        └─(NEW sink)─> turn_telemetry append (same save.db,
                                        shared turn transaction)         (durable autopsy)

forensics page ──> /api/debug/save/{slug}/turn/{round}
                        └─ forensic_query (read-only ?mode=ro)
                              └─ fold_turn_telemetry(rows)  # pure, read-time curation
                                    └─ bundle["telemetry"] ─> "decision telemetry" lane
```

Self-contained: `turn_telemetry` lives in `save.db`, so the existing
db+wal+shm preservation trio already covers it; no new file.

## Components

### 1. Schema — `turn_telemetry` (append-only)

Added to the existing `CREATE TABLE IF NOT EXISTS` schema-init list in
`sidequest/game/persistence.py`.

| column        | type                | meaning |
|---------------|---------------------|---------|
| `seq`         | INTEGER PK AUTOINCREMENT | monotonic telemetry row id |
| `event_seq`   | INTEGER NULL        | `events.seq` of the turn frame this fired within; NULL if telemetry fired outside an event append |
| `round`       | INTEGER NULL        | best-effort from `turn_manager.round` at publish time; NULL if unavailable |
| `ts`          | TEXT                | `datetime.now(UTC).isoformat()` |
| `component`   | TEXT                | `_watcher_publish` `component=` (e.g. `projection`, `inventory`, `trope`) |
| `event_type`  | TEXT                | `_watcher_publish` first positional (e.g. `state_transition`) |
| `payload_json`| TEXT                | the fields dict, `json.dumps` verbatim — raw, no curation |

Never `UPDATE`d or `DELETE`d. No TTL, no reaping (durable-retention is
law). Indexed on `round` and `event_seq` for the read path.

### 2. Write sink — in `_watcher_publish` (`sidequest/server/session_handler.py`)

`_watcher_publish` already runs every turn and callers already wrap it so
"telemetry must never crash a turn." Add a sink that:

- resolves the active session's `SqliteStore` (the same `_conn`
  `event_log` uses for this slug);
- appends one `turn_telemetry` row using that connection — **inside the
  open turn transaction** when one is active (so it commits atomically
  with the `events`/`projection_cache` C2 block), else its own short
  `with conn:` transaction;
- derives `event_seq` from the turn's current event row when available,
  `round` from `turn_manager` best-effort;
- is **fully wrapped**: on *any* failure → `logger.warning(
  "turn_telemetry.sink_failed ...")` loudly and return; never raise,
  never stall the turn, never silently write to a different DB
  (No-Silent-Fallbacks).

The OTEL emission path is unchanged and independent — one failing sink
never affects the other.

### 3. Read path — `forensic_query` (`sidequest/game/forensic_query.py`)

- Read `turn_telemetry` over the existing `_ro_connect` (`?mode=ro`,
  **never** `SqliteStore` — `project_sqlitestore_open_writes`).
- Rows for a round = those whose `event_seq` is within the round's
  event-seq range (same bucketing the bundle already computes), plus
  rows whose `round` column matches (covers NULL-`event_seq` rows).
- `build_turn_bundle` gains `telemetry` (list of rows for the round).

### 4. Read-time fold — `fold_turn_telemetry(rows)` (new, pure)

Mirrors `fold_known_facts`: pure, no I/O, defensive, never raises.
Groups rows by `component` then `event_type`; counts; keeps each row's
key fields for display. Unparseable `payload_json` is loud-skipped and
recorded (same `unparseable` contract as the footnote fold). This is the
read-time curation the raw-substrate decision deferred here.

### 5. Forensics UI — one evidence lane

`forensics.html` gains a single collapsed `<details>`: **"decision
telemetry (this round) — {n} signals"**, grouped by component, each row
`component · event_type · key fields` (defensive `esc()` on all values,
existing contract). No macro-strip change (Phase 2 territory). Absent →
honest *"— no decision telemetry (save predates the substrate)"*, never
fabricated.

## Data flow

1. Turn runs → subsystem calls `_watcher_publish(type, fields, component=)`.
2. Existing OTEL path emits to Jaeger (unchanged).
3. New sink appends one `turn_telemetry` row in the turn's transaction.
4. Turn commits → telemetry committed atomically with it (or rolled back
   with it — no orphan/partial).
5. Later: forensics opens the save read-only, buckets telemetry by round,
   folds it, renders the lane.

## Error handling

- Sink failure: loud `logger.warning`, continue; turn unaffected;
  telemetry for that publish is lost but visibly logged (acceptable —
  the alternative is risking a live table).
- Read path: `forensic_query` degrades to empty, never 500 (mirrors the
  existing forensics route tests). Unparseable payloads loud-skipped in
  the fold, recorded, never crash the page.
- Old saves (no `turn_telemetry` table or zero rows): honest empty lane,
  never fabricated.

## Testing (Phase 1)

- **Pure fold unit tests** (`test_forensic_fold`-style): grouping,
  counting, unparseable loud-skip, empty→empty.
- **`forensic_query` read test** over a seeded save with `turn_telemetry`
  rows: correct per-round bucketing incl. NULL-`event_seq` rows.
- **never-500 + read-only byte-identity**: a save with telemetry is not
  mutated by a forensics read (mirror existing forensics suite).
- **Mandatory wiring test** (CLAUDE.md "Every Test Suite Needs a Wiring
  Test"): a real production turn path actually writes `turn_telemetry`
  rows — not a unit stub. Proves the sink is reached from the live turn,
  not just importable.
- **Sink failure isolation test**: a forced sink error logs loudly and
  the turn still completes (telemetry never crashes a turn).

## Observability

The forensics page **is** the observability for this substrate (don't
recurse a watcher event about the telemetry sink into the telemetry
sink). Sink health = the loud `turn_telemetry.sink_failed` WARNING + the
row counts visible in the forensics lane. Note for the plan: a one-line
count ("N telemetry rows this save") in the macro header is a cheap
sink-health tell for the GM.

## Migration / back-compat

Forward-only. `CREATE TABLE IF NOT EXISTS` adds the table to any save on
next open by the live server (write path) — but **forensics is read-only
and must not create it**; the read path treats a missing table exactly
like zero rows (honest empty lane). Existing saves gain telemetry only
for turns played after the substrate ships; pre-substrate rounds honestly
show none.

## Open implementation question (plan's first task)

**Does `_watcher_publish` already have a handle to the per-slug
`SqliteStore`?** It lives in `session_handler.py` and is called as a
free function from `emitters.py`. If it does not carry the session's
store/handler, the sink cannot "resolve the active session's store"
without a session-registry lookup or threading the store through. The
plan's **first task** is to confirm the actual `_watcher_publish`
signature/scope and pick the wiring: (a) it already has the handler →
trivial; (b) thread the store in at call sites; (c) look up via the
session registry by slug. No silent global fallback — the chosen path
must be explicit. This is the load-bearing unknown; everything else is
mechanical.

## Risks & mitigations

- **Hot-path cost:** one small INSERT per `_watcher_publish` in the
  already-open turn transaction. A turn emitting many publishes = many
  inserts in one transaction (the C2 model already batches this). Plan
  must measure on a real turn; if pathological, coalesce per-turn.
- **Payload size / content:** payloads may embed narration snippets.
  Acceptable — the save is a local GM/dev artifact, not player-facing;
  noted, not gated.
- **Raw payload drift:** shape evolves over time (that's the point of
  raw). The read-fold is defensive by contract (esc, never-raise),
  same as the footnote fold.

## Phases (follow-on, each its own spec→plan)

- **Phase 2 — mechanical-state coverage.** Audit which subsystems emit
  `state_transition`/decision watcher events (CLAUDE.md OTEL principle
  says they should; coverage is uneven — `feedback_log_absence_not_
  deadness`). Fill gaps (per-PC location, HP, inventory, xp, trope
  progress, dice, confrontation outcomes). Phase 1's sink then persists
  them automatically; a read-fold derives the per-round mechanical diff
  and a macro-strip integrity/mechanical lane.
- **Phase 3 — living-world coverage.** Same pattern: NPC disposition/
  OCEAN shifts, gossip/relationship propagation, scenario clue-graph &
  belief state, coal→diamond world-fact promotions → a world-evolution
  lane.

## Handoff

Phase 1 → writing-plans skill → TDD implementation (the White Rabbit).
Branch `feat/forensics-telemetry-substrate` off `sidequest-server`
`develop`. Phases 2–3 deferred sub-projects.
