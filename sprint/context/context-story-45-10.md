---
parent: sprint/epic-45.yaml
workflow: tdd
---

# Story 45-10: Scrapbook backfill detection on save resume

## Business Context

**Playtest 3 evidence (2026-04-19):** Orin's session covered 29 rounds.
The `scrapbook_entries` table held entries for 10 of those rounds. The
other 19 rounds (rounds 11–29) had no scrapbook coverage — invisible to
the subsystem that injects "what happened in scene N" into the
narrator's recap and the GM-panel timeline. The cause is benign on its
face: the playtest carried Orin's save forward across a server restart
that predated the scrapbook subsystem being live, so older rounds were
never written. The damage is real: when the narrator queries scrapbook
context for round 17, it gets nothing, and silently invents continuity.

This is a **bookkeeping-fires-but-doesn't-persist** failure of the
exact shape Lane B is built around. The extractor (NARRATION turn →
`emit_scrapbook_entry`, `emitters.py:352`) fires; the applier
(scrapbook reader on save-resume) has no concept of "I should be
suspicious of round counts I don't cover." Tests exist that prove
write-side works (`test_emitters.py` has scrapbook coverage). What's
missing is the **read-side gap detection** on resume.

For Sebastien (mechanical-first), this is precisely the lie-detector
gap CLAUDE.md flags — the subsystem looks engaged, the GM panel
shows entries, but coverage is partial and nothing flags it. For James
(narrative-first), the symptom is the narrator subtly losing thread
on prior scenes. ADR-023 (Session Persistence) governs save resume —
the resume contract has to extend to "every per-turn subsystem either
backfilled or warned loudly when its coverage diverged from
`narrative_log.max_round`."

## Technical Guardrails

### Outermost reachable seam

The seam is the **save-resume entry path**. Two call sites:

1. **Slug-keyed resume** at `session_handler.py:1610–1647` (the
   `existing_session is not None` branch). After
   `room.bind_world(snapshot=snapshot, store=store)` succeeds and
   before the connect message is built.
2. **Legacy non-slug resume** at `session_handler.py:2138–2147`
   (the `saved is not None` branch). Same shape, same seam.

A new helper — `detect_scrapbook_coverage_gaps(store, snapshot) ->
ScrapbookCoverageReport` — is called from both sites. The TDD test
must drive a populated `.db` through one of these resume paths
end-to-end (a unit test on the helper alone fails the wire bar).

### Coverage definition

`narrative_log.max_round` is the upper bound:

```python
max_round = store._conn.execute(
    "SELECT MAX(round_number) FROM narrative_log"
).fetchone()[0] or 0
```

`scrapbook_entries` does NOT carry a round number — it carries
`turn_id` (interaction counter) per the schema at
`persistence.py:112–124`. The mapping `interaction → round` lives
on `narrative_log`. The gap detector joins:

```python
covered_rounds = store._conn.execute(
    "SELECT DISTINCT n.round_number "
    "FROM scrapbook_entries s "
    "JOIN narrative_log n ON n.round_number IS NOT NULL "
    "  AND n.id IN ("
    "    SELECT MIN(id) FROM narrative_log "
    "    WHERE round_number = n.round_number GROUP BY round_number"
    "  ) "
    "ORDER BY n.round_number"
).fetchall()
```

(Or simpler: derive round from `interaction` via the snapshot's
`narrative_log.entries` list which already pairs `round` with content.)

The report is `(max_round, covered_rounds_set, gap_rounds_list,
coverage_ratio)`.

### Two acceptable behaviors (story title says "either")

1. **Backfill** — synthesize a stub `scrapbook_entries` row per
   uncovered round using narrative_log content for that round
   (`narrative_excerpt` from the narrator-author entry, `location`
   from the snapshot's location at that turn — but the snapshot only
   has the *current* location; backfill location degrades to the
   snapshot's current `location` field with a `"backfilled"` tag).
2. **Warn loudly** — emit the OTEL span with `gap_count >= 1`,
   surface a watcher event `scrapbook.coverage_gap_detected`, and
   continue. Do NOT backfill.

The story description says "either backfill OR warn loudly"; pick
option 2 by default. Backfill is lossy (location is wrong, npcs
unknown, image_url null) and risks **fabricating diamond from coal**
(ADR-014 inverse). Warn-only is honest. If a future story wants to
backfill from a richer source (e.g., world_history chapters), it can
do so explicitly.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md)

Define in `sidequest/telemetry/spans.py` and register routes:

| Span | Attributes | Site |
|------|------------|------|
| `scrapbook.coverage_evaluated` | `max_round`, `covered_count`, `gap_count`, `coverage_ratio` (float 0–1), `genre`, `world`, `slug` | every save-resume — fires with `gap_count=0` on the no-op path |
| `scrapbook.coverage_gap_detected` | same + `gap_rounds` (list of int round numbers) | only when `gap_count > 0` |

`scrapbook.coverage_evaluated` MUST fire on every resume, including
fresh saves where `max_round=0`. Sebastien needs negative
confirmation. Pair the gap span with a `_watcher_publish(
"scrapbook_coverage_gap", {...}, component="scrapbook",
severity="warning")` so the GM panel surfaces it visibly — this
follows the pattern at `emitters.py:465–477`.

### Reuse, don't reinvent

- `SqliteStore` (`game/persistence.py:218`) is the access seam. Do
  not open new connections; thread through `store._conn`.
- `recent_narrative()` at `persistence.py:339–364` is the existing
  read pattern; the new `_max_narrative_round()` and
  `_scrapbook_round_coverage()` queries belong on `SqliteStore` as
  sibling methods (or in a sibling module
  `sidequest/game/scrapbook_coverage.py` if you want to keep
  persistence.py tight — Keith preference for the latter).
- `persist_scrapbook_entry()` at `emitters.py:23` is the existing
  write site; the gap detector reads from the same table. No
  new schema.
- Watcher publish pattern is established at
  `emitters.py:465–477` — re-use shape and severity conventions.

### Test harness

- `session_handler_factory()` at
  `sidequest-server/tests/server/conftest.py:332` for the wire test.
- For the TDD-natural unit tests, populate a `SqliteStore` directly
  with `append_narrative()` and `persist_scrapbook_entry()` — both
  are public API.

### Test files (where new tests should land)

- New: `tests/server/test_scrapbook_coverage.py` — unit tests for the
  gap detector against pre-populated stores.
- Extend: `tests/server/test_chargen_persist_and_play.py` (or new
  `test_scrapbook_resume_wire.py`) — wire-test driving a populated
  resume path and asserting the span fires.

## Scope Boundaries

**In scope:**

- New `detect_scrapbook_coverage_gaps(store, snapshot) ->
  ScrapbookCoverageReport` helper (module location: new
  `sidequest/game/scrapbook_coverage.py`).
- Wire the helper into both resume paths
  (`session_handler.py:1610` slug, `session_handler.py:2138` legacy)
  immediately after `saved/snapshot` is loaded and before
  `_session_data` is constructed.
- New OTEL spans `scrapbook.coverage_evaluated` (always) and
  `scrapbook.coverage_gap_detected` (when gaps exist), with
  `SPAN_ROUTES` entries.
- Watcher event `scrapbook_coverage_gap` for GM-panel surfacing on
  the gap path.
- TDD-first test: populate a slot with 29 rounds of `narrative_log`
  and 10 rounds of `scrapbook_entries`, drive resume, assert the
  span fires with `gap_count=19` and the correct `gap_rounds` list.
- Unit tests for the helper: empty store → `gap_count=0`; full
  coverage → `gap_count=0`; partial coverage → correct gap list.

**Out of scope:**

- Backfilling scrapbook rows. Warn-only is the chosen path; backfill
  is rejected upstream (see Technical Guardrails). A follow-up story
  can layer backfill on top, sourcing from world_history or RAG.
- Schema changes. `scrapbook_entries.turn_id` stays
  interaction-keyed; the round join goes through `narrative_log`.
- Reworking the scrapbook write path (`emitters.py:352`). This is a
  read-side hygiene story.
- UI work for the GM panel. The watcher event is the surfacing hook;
  rendering is Lane C.
- Reconciling `interaction` vs `round` semantically — the existing
  two-tier turn counter (ADR-051) governs that; this story consumes
  it as-is.

## AC Context

1. **Resume path with full scrapbook coverage emits
   `scrapbook.coverage_evaluated` with `gap_count=0`.**
   - Test: populate a store with 5 rounds of `narrative_log` and 5
     rounds of `scrapbook_entries`. Drive resume. Assert span fires
     with `max_round=5`, `covered_count=5`, `gap_count=0`,
     `coverage_ratio=1.0`. No gap span. No watcher event.

2. **Resume path with partial scrapbook coverage emits both spans
   and the watcher event.**
   - TDD-natural test (the Orin regression): populate a store with
     29 rounds of `narrative_log` and 10 rounds of
     `scrapbook_entries` covering rounds 1–10. Drive resume. Assert
     `scrapbook.coverage_evaluated` fires with `max_round=29`,
     `covered_count=10`, `gap_count=19`,
     `coverage_ratio≈0.345`; `scrapbook.coverage_gap_detected` fires
     with `gap_rounds == list(range(11, 30))`; watcher event
     `scrapbook_coverage_gap` published with severity `warning`.
   - This is the negative-to-positive transformation: the bug-evidence
     fixture (Orin partial coverage) becomes the failing test that
     drives the detector into existence.

3. **Resume path on a fresh save fires `scrapbook.coverage_evaluated`
   with `max_round=0`.**
   - Test: empty `narrative_log`, empty `scrapbook_entries`. Drive
     resume. Assert span fires once with `max_round=0`,
     `gap_count=0`, `coverage_ratio=1.0` (defined as 1.0 when no
     rounds exist — better than NaN for downstream
     dashboarding). No gap span, no watcher event.
   - Sebastien's negative-confirmation requirement: the span MUST
     fire on the no-op path so "scrapbook checked" is observable.

4. **Both resume paths (slug + legacy) wire the detector.**
   - Wire-test: drive a slug-keyed resume → span fires.
   - Wire-test: drive a legacy non-slug resume → span fires.
   - Negative regression: a half-wired fix that only patches the
     slug path leaves the legacy path silent — the test catches it.

5. **No write-side mutation occurs from the detector.**
   - Test: pre-resume `scrapbook_entries` row count == post-resume
     row count (warn-only, not backfill). Pre-resume `narrative_log`
     row count is unchanged. Idempotent across repeated resumes of
     the same slot.
