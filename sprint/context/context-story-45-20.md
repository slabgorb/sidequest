---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-20: Resolved tropes write quest_log entry + active_stakes update

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session — Orin):** at turn ~40,
Orin's snapshot held `active_tropes` containing `extraction_panic` with
`status="resolved"` and `hireling_mutiny` with `progress=0.255` (mid-arc).
Yet `snapshot.quest_log == {}` and `snapshot.active_stakes == ""`. The
narrator's state_summary advertised "no active stakes" three turns after
a major trope resolved — narrative continuity broke.

The trope-status field is the authoritative signal that something
narratively meaningful concluded; `quest_log` and `active_stakes` are the
durable records the narrator reads next turn to ground the prose. The
resolution pipeline has the extractor (a trope's `status` flips to
`"resolved"`, today only via chapter promotion at
`sidequest/game/world_materialization.py:429–458`) but no applier — no
caller takes the resolved trope and seeds the quest_log entry or updates
active_stakes. This is the canonical Lane B write-back failure: extractor
fires, applier never observes.

The Python-port helper `resolve_encounter_from_trope()` at
`sidequest/server/dispatch/encounter_lifecycle.py:183–221` exists for the
*encounter* side of trope resolution and is documented as having "no
Python caller as of this commit" (line 193) — the trope engine port is
deferred. This story is NOT the trope-engine port; it wires the durable
record path that ANY trope resolution (today: chapter promotion via
45-19's recompute; tomorrow: a future engine; or a narrator-extracted
status flip) must trigger.

**Audience tie:** James (narrative-first) is the one who feels the
broken continuity — the narrator stops referencing the resolved trope.
Sebastien (mechanical-first) needs the OTEL `trope.resolution_handshake`
span to confirm the path fired; without it the GM panel cannot tell
whether the trope "Resolved" indicator is real or whether the narrator
fabricated a closure beat that never wrote back.

**ADR linkage:**
- **ADR-014 (Diamonds and Coal):** the chapter-driven `_apply_trope` write
  is a diamond (canonical maturity-tier signal), but downstream consumers
  treat it as coal — quest_log and active_stakes never read it.
- **ADR-031 (Game Watcher / OTEL):** every Lane B fix emits a span on the
  write path. The handshake span fires on each Resolved trope detection,
  even when the trope was already-Resolved and the write is a no-op
  (idempotency confirmation).
- **ADR-067 (Unified Narrator Agent):** the narrator reads
  `snapshot.quest_log` and `snapshot.active_stakes` via the
  `state_summary` JSON at `session_helpers.py:226`. Writing the quest_log
  entry is what makes the resolution visible to next-turn prose.

This is **P2** — the durable-record loss is annoying for narrative texture
but does not break game correctness. Lane A (45-2/45-3) sprints first.

## Technical Guardrails

### Outermost reachable layer (wire-first seam)

The wire-first gate requires the test to exercise the actual handshake
seam, **not** a unit test on a pure helper. Two seams must be hit:

1. **Trope-state-change → resolution-handshake seam** — fire detection
   from inside `_execute_narration_turn()` at
   `sidequest/server/session_handler.py:3286–3490`, immediately after the
   snapshot mutation phase
   (`_apply_narration_result_to_snapshot` at `session_handler.py:3404`)
   and the `record_interaction()` call at `session_handler.py:3424`. That
   is the canonical post-mutation site where prior-turn state and
   current-turn state can be diff'd. (The chapter-promotion path that
   today is the only Resolved writer fires at `_apply_trope`,
   `world_materialization.py:444–449`, when 45-19's recompute runs — the
   handshake must observe both that path and any future status-flip
   pathway.)
2. **Handshake → state_summary seam** — the new `quest_log` entry and
   updated `active_stakes` must be on the snapshot *before*
   `state_summary_payload = json.loads(snapshot.model_dump_json())` at
   `sidequest/server/session_helpers.py:226`. The next narrator turn is
   what consumes the output; skipping this seam leaves the fix dead.

Boundary tests must drive both seams via the WS-driven dispatch path
using `session_handler_factory()` at `tests/server/conftest.py:332` and
the `_FakeClaudeClient` at `conftest.py:197`.

### Resolution diff predicate (THE FIX)

The handshake compares the prior-turn `active_tropes` snapshot to the
current `active_tropes` snapshot and emits a quest_log entry / updates
active_stakes for every trope whose `status` transitioned to `"resolved"`.

**Two stash candidates — pick `_SessionData`:**

- `_SessionData` already carries per-turn ephemera
  (`pending_roll_outcome` etc., session_handler.py:578). Add
  `prior_trope_status: dict[str, str]` populated at the END of each turn
  and consumed at the START of the next handshake. Survives across the
  turn boundary in-memory; not persisted (the trope engine reconstructs
  state from `snapshot.active_tropes` on reload, so the diff baseline
  on the very first post-reload turn is the persisted state itself —
  the baseline equals the current state, no false-positive resolution
  fires).
- Computing the baseline from `snapshot.active_tropes` *before* applying
  this turn's narration result is the simpler alternative. Capture the
  baseline at the top of `_execute_narration_turn()` before
  `_apply_narration_result_to_snapshot`, diff at the post-mutation site.
  No `_SessionData` field needed; survives reload cleanly because the
  baseline is always derived from the live snapshot.

**Recommend the second pattern** — fewer fields to track, no
post-reload edge case.

### Quest log entry schema

`snapshot.quest_log` is a `dict[str, str]` (`session.py:352`); each entry
is `quest_id → status_text`. The handshake writes:

- key: `f"trope_{trope_id}"` (namespaced so a future quest engine doesn't
  collide).
- value: a deterministic status text — `f"Resolved at turn {interaction}"`
  is the minimum; if the genre pack's trope definition declares a
  resolution_text it can be appended. Keep it short — the narrator reads
  this.

`snapshot.active_stakes` is a free-form string. On resolution, append
`f"\n[Resolved: {trope_id} on turn {interaction}]"` to the existing
value, trimming if the field length exceeds a guardrail (~512 chars —
the field is reflected in `state_summary` and runaway growth pollutes
the prompt). If `active_stakes` is empty and a trope resolves, set it to
the resolution marker alone.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md OTEL principle)

Define in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES`. Note
that `SPAN_TROPE_RESOLVE = "trope_resolve"` already exists at
`sidequest/telemetry/spans.py:156` but is in `FLAT_ONLY_SPANS` and has no
`SPAN_ROUTES` registration (`spans.py:2235–2240`) — promote it.

| Span | Attributes | Site |
|------|------------|------|
| `trope.resolution_handshake` | `trope_id`, `prior_status`, `new_status` (always `"resolved"`), `interaction`, `quest_log_key`, `active_stakes_appended` (bool — false on idempotent re-detect), `source` (`"chapter_promotion"` / `"narrator_extraction"` / `"engine_tick"`) | every detection of a `status=="resolved"` trope at the handshake site, INCLUDING idempotent re-detects (no double-write but the span fires so the GM panel sees the path engaged) |
| `trope_resolve` (existing constant) | `trope_id`, `interaction`, `genre_slug` | promote out of `FLAT_ONLY_SPANS`; register `SPAN_ROUTES[SPAN_TROPE_RESOLVE]` so the existing span name surfaces in the GM panel |

The `trope.resolution_handshake` span MUST fire on every detection, not
only on the first write. The bug is that no path fires at all today; if
the new span only emits on the first write, the panel cannot distinguish
"handshake correctly idempotent" from "handshake never engaged after
turn N."

### Reuse, don't reinvent

- `quest_update_span()` at `sidequest/telemetry/spans.py:1974` already
  wraps quest_log writes and routes through `SPAN_QUEST_UPDATE`. Wrap
  the quest_log mutation in this existing helper — do NOT author a
  parallel quest-write span. The existing
  `SPAN_ROUTES[SPAN_QUEST_UPDATE]` registration at `spans.py:312` will
  surface the entry in the GM panel.
- `TropeState` at `sidequest/game/session.py:253–264` is the data
  carrier; `id`, `status`, `progress`, `beats_fired`. The `id` is the
  `trope_id` for the handshake key.
- The chapter-promotion path that writes `status="resolved"` is at
  `world_materialization.py:439–449` (`_apply_trope`). The "resolved"
  literal is the canonical status string — the four valid values
  enumerated at `world_materialization.py:440` are
  `{"dormant", "active", "progressing", "resolved"}`.

### Test files (where new tests should land)

- New: `tests/server/test_trope_resolution_handshake.py` — unit tests for
  the diff predicate (prior_status `progressing` → new_status `resolved`
  fires; prior_status `resolved` → new_status `resolved` is idempotent
  no-write; prior_status `active` → new_status `resolved` fires) and the
  quest_log key namespace.
- New or extend: `tests/server/test_narration_turn_dispatch.py` — wire-
  first boundary test driving a chapter-promotion across the WS path
  (e.g. via the 45-19 recompute crossing a maturity tier whose chapter
  declares a resolved trope) and asserting `quest_log` and
  `active_stakes` are populated AFTER the next narrator's `state_summary`
  is built.
- Extend: `tests/server/test_chargen_persist_and_play.py` — add a save/
  reload round-trip after a resolved trope, asserting the quest_log
  entry survives persistence (durability AC — the in-memory diff
  baseline must not lose state on reload).
- Extend: `tests/telemetry/test_spans.py` — assert
  `SPAN_TROPE_RESOLUTION_HANDSHAKE` registers and `SPAN_TROPE_RESOLVE`
  is now in `SPAN_ROUTES` rather than `FLAT_ONLY_SPANS`.

## Scope Boundaries

**In scope:**

- A diff-and-write helper (e.g. `_handshake_resolved_tropes(snapshot,
  baseline_status)` in a new module or in
  `sidequest/server/narration_apply.py` near the existing
  `_apply_narration_result_to_snapshot`) that:
  - Identifies tropes whose `status` is now `"resolved"` and whose
    baseline status was anything other than `"resolved"`.
  - Writes a `quest_log[f"trope_{id}"]` entry per resolved trope.
  - Appends/sets `active_stakes` per the schema above.
  - Emits one `trope.resolution_handshake` span per detected trope
    (firing even on idempotent re-detects so the path is observable).
- Wire the helper into `_execute_narration_turn()` at the post-
  `record_interaction` site (`session_handler.py:3424`), with the
  baseline captured at the top of the function before
  `_apply_narration_result_to_snapshot`.
- Promote `SPAN_TROPE_RESOLVE` out of `FLAT_ONLY_SPANS`; register a
  `SPAN_ROUTES` entry for it.
- New `trope.resolution_handshake` span + `SPAN_ROUTES` registration.
- Wire-first boundary test reproducing Orin's evropi scenario: drive the
  chapter-promotion (or stub a status flip) and assert the next narrator
  turn's `state_summary` JSON contains the quest_log entry and the
  resolution marker in active_stakes.
- Save/reload durability test (the entry must survive persistence —
  it's a `quest_log` mutation on the snapshot; persistence already
  round-trips this field per `session.py:352`, but the AC is still
  testable end-to-end).

**Out of scope:**

- **Trope engine port.** The full Phase 3 trope engine (passive
  progression, beat-firing → trope_progress, narrator-extracted trope
  state) is P2-deferred per `session.py:321` and is NOT this story.
  This story handles the durable-record path for whatever upstream
  writes `status="resolved"` — today only chapter promotion, tomorrow
  whatever the engine port wires up.
- **Encounter resolution from trope.** `resolve_encounter_from_trope()`
  at `dispatch/encounter_lifecycle.py:183` resolves the active
  *encounter* when a trope completes. That helper is its own IOU
  (line 193: "no Python caller as of this commit"); 45-20 must NOT
  call it. The two paths are different consumers of the same upstream
  signal — encounter lifecycle vs. quest_log durability. A future
  trope-engine port would call both.
- **45-19 (world_history arc recompute).** 45-19 is the upstream that
  fires the chapter-promotion → trope-status writes that 45-20
  observes. The two stories' boundary is the snapshot mutation:
  45-19 mutates `active_tropes`, 45-20 reads the mutation and writes
  the durable record. Crossing the boundary collapses two stories.
- **Schema migration.** `quest_log` is `dict[str, str]` already on
  `GameSnapshot`; the namespaced `trope_*` key is a string and
  round-trips cleanly through the existing save format.
- **Narrator prompt template changes.** Only the JSON the narrator sees
  changes (quest_log gains an entry, active_stakes gains a marker); no
  edits to the prompt scaffolding.
- **Trope removal / "unresolved" transitions.** The handshake fires
  ONLY on transitions INTO `"resolved"`. A trope going from `resolved`
  → `progressing` (re-activation) does NOT remove the quest_log entry;
  history matters and the durable record persists. A future story can
  layer trope-reactivation semantics on top.

## AC Context

The story description carries the contract; we expand it into testable ACs:

1. **Resolved trope writes a `quest_log` entry on the next turn boundary.**
   - Test: drive a session where a trope's status transitions from
     `progressing` (or `active`, or `dormant`) to `resolved` between two
     turns. Assert `snapshot.quest_log[f"trope_{trope_id}"]` is set
     after the post-mutation handshake fires, and the value contains
     the interaction number.
   - Wire-first: the assertion is on the JSON the orchestrator received
     in `state_summary`, not the raw snapshot — proves the
     post-mutation timing seam.

2. **Resolved trope updates `active_stakes` with a resolution marker.**
   - Test: prior `active_stakes=""` → after resolution, the field
     starts with the resolution marker. Prior `active_stakes="Find
     the courier"` → resolution appends a newline + marker, original
     content preserved.
   - Negative: a 600-char `active_stakes` triggers the trim guardrail;
     the resolution marker is included and total length stays under
     the cap.

3. **Quest log entry survives save/reload (durability).**
   - Test: drive resolution; persist via `sd.store.save(snapshot)` at
     `session_handler.py:3471`; reload via the persistence path; assert
     `quest_log[f"trope_{trope_id}"]` is intact on the loaded
     snapshot. Confirms the diff baseline does not produce false-
     positive duplicate writes on the post-reload first turn (the
     baseline is taken from the live snapshot, so the same `resolved`
     status looks unchanged on the next turn — the idempotency span
     fires but no second write occurs).

4. **OTEL `trope.resolution_handshake` span fires on every detection
   with prior + new status.**
   - Test: trigger a single resolution; assert the span fires once
     with `prior_status` (e.g. `"progressing"`), `new_status="resolved"`,
     `quest_log_key=f"trope_{id}"`, `active_stakes_appended=True`,
     `source="chapter_promotion"`.
   - Test: drive the SAME session through one more turn without
     further trope changes; assert the handshake span fires again
     for the still-resolved trope with `active_stakes_appended=False`
     (idempotent re-detect — the lie-detector signal Sebastien needs).
   - Verify `SPAN_ROUTES` registers the watcher mapping so events
     reach the GM panel.

5. **Existing `SPAN_TROPE_RESOLVE` span is now in `SPAN_ROUTES`.**
   - Test: assert `SPAN_TROPE_RESOLVE` (`"trope_resolve"`) is no
     longer in `FLAT_ONLY_SPANS` (`spans.py:2235–2240`) and has a
     `SpanRoute` entry routing it to `component="game"`,
     `event_type="state_transition"`. Closes the GM-panel coverage gap
     for the existing constant.

6. **Negative — non-resolved trope status changes do NOT fire the handshake.**
   - Regression test: `dormant` → `active`, `active` → `progressing`,
     `progressing` → `dormant` (downgrade) all leave `quest_log`
     untouched and emit NO `trope.resolution_handshake` span. Confirms
     the diff predicate is scoped strictly to transitions into
     `"resolved"`.
