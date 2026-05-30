---
story_id: "59-22"
jira_key: ""
epic: "59"
workflow: "tdd"
---
# Story 59-22: Extract shared _deliver_to_connected_recipients helper (dedupe emit_event supplier loop vs _deliver_fanout)

## Story Details
- **ID:** 59-22
- **Jira Key:** (none — SideQuest personal project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repo:** sidequest-server
- **Slug:** deliver-to-connected-recipients-helper
- **Branch:** feat/59-22-deliver-to-connected-recipients-helper (sidequest-server, off develop)

## Workflow Tracking
**Workflow:** tdd
**Phase:** green
**Phase Started:** 2026-05-30T09:34:52Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30T00:00:00Z | 2026-05-30T09:25:13Z | 9h 25m |
| red | 2026-05-30T09:25:13Z | 2026-05-30T09:34:52Z | 9m 39s |
| green | 2026-05-30T09:34:52Z | - | - |

## Sm Assessment

Refactor-only follow-up to 59-16 (simplify-reuse medium-confidence finding, not auto-applied).
`sidequest/server/emitters.py` has two recipient-delivery loops that independently re-implement the
same `socket_for_player → _emit_recipient_dropped("socket_gone") → queue_for_socket →
_emit_recipient_dropped("queue_detached") → put_nowait` dispatch:

- **`_deliver_fanout`** (`emitters.py:71–127`) — builds the payload inline from a filtered dict under the
  C3 `model_validate` rule (`_visibility` strip + `try/except` logging `fanout_failed`), gated by
  `decision.include`.
- **The `per_recipient_payload` supplier loop in `emit_event`** (`emitters.py:403–417`) — message already
  built by `_frame_for(pid)`; a `None` return means "send nothing"; also captures the emitter's own frame.

Extract `_deliver_to_connected_recipients(room, recipients, *, message_builder, kind)` with a
builder-callable abstraction (`message_builder(pid) -> message | None`, `None` ⇒ skip). Fold each loop's
skip rule into its builder. Keep the 59-20 emitter-fallback (cleared-frame return) in `emit_event`, outside
the helper. **Behavior must be identical** — the existing emitter/confrontation delivery suite is the safety net.

Full context with line-cited duplication analysis, proposed shape, and ACs in
`sprint/context/59-22-context.md`. Repo is github-flow off `develop`. No Jira (personal project).

**Decision:** Route to TEA for the RED phase. Because this is a pure refactor, the RED test is a
characterization test pinning the shared dispatch contract (happy path + both drop reasons) plus a wiring
assertion proving BOTH production call sites route through the one helper.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- **[SM / Gap, non-blocking]** The `sm-setup` subagent corrupted this session file on first write
  (appended the "append deviations below this line" comment ~2000×). SM rewrote it clean. Flag for
  pf tooling: sm-setup template-expansion runaway.

## TEA Assessment (RED → Dev) — Radar

**Test file:** `tests/server/test_deliver_to_connected_recipients_59_22.py` — 6 tests, committed `943862cf`.
**RED verified** (serial run, no false reasons): 4× `AttributeError` (helper absent) + 2× `AssertionError`
(both call sites still inline the loop → spy never fires). Collection clean.

**Run command** (server suite needs the DB env or it throws phantom `MissingDatabaseUrlError`):
```
cd sidequest-server && SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
  uv run pytest tests/server/test_deliver_to_connected_recipients_59_22.py -v
```

### The contract Dev must satisfy (GREEN)

Extract **`emitters._deliver_to_connected_recipients(room, recipients, *, message_builder, kind)`**:
```python
for pid in recipients:
    msg = message_builder(pid)        # None ⇒ skip (the single skip rule)
    if msg is None: continue
    socket_id = room.socket_for_player(pid)
    if socket_id is None: _emit_recipient_dropped(kind, pid, "socket_gone"); continue
    queue = room.queue_for_socket(socket_id)
    if queue is None: _emit_recipient_dropped(kind, pid, "queue_detached"); continue
    queue.put_nowait(msg)
```
Then route **BOTH** call sites through it:
- **`_deliver_fanout`** (`emitters.py:71`) — `recipients = [pid for (pid, _d, _f) in fanout]`; the
  builder folds in `decision.include` (False ⇒ return None), the C3 `payload_cls.model_validate({**filtered_data, "seq": seq})`,
  the `_visibility` strip, and the `try/except` that logs `fanout_failed` and returns None on failure.
- **`emit_event` supplier loop** (`emitters.py:403`) — `recipients = room.connected_player_ids()`;
  builder = the existing `_frame_for`. **Capture the emitter frame separately** — the helper returns
  nothing useful for that. Keep the Story 59-20 cleared-frame fallback (`emitters.py:~421`) in
  `emit_event`, OUTSIDE the helper. The two wiring tests spy the helper and let it return `None`, so
  the supplier path must still produce the emitter's return value from its own builder/fallback, not
  from the helper's result.

> The wiring tests assert the helper is *called* by both sites (spy records the call) — they do not
> assert on the helper's return. Behavior parity is enforced by the EXISTING suites below, which Dev
> MUST keep green.

### Behavior-parity safety net (must stay green — these are the real regression guards)

- `tests/server/test_emit_fanout_recipient_drop.py` (3) — socket_gone/queue_detached surfacing, live
  recipients still served, excluded≠drop.
- `tests/server/test_confrontation_single_delivery.py` (8, needs Postgres `migrated_db` fixture) — the
  supplier path's real behavior: per-recipient filtered delivery, union→EventLog-only, emitter frame,
  fail-loud span.
- Also run: `test_emitters.py`, `test_merged_mp_emitter_projection.py`, `test_opening_emit_event_71_13.py`,
  `test_emitters_broadcast_delta.py`.

### Rule Coverage (`.pennyfarthing/gates/lang-review/python.md`)

| # | Rule | How covered |
|---|------|-------------|
| 3 | Type annotations at boundaries | Helper is a new module-boundary fn — Dev MUST annotate all params + return (`-> None`). Tests don't enforce types; Reviewer/pyright will. **Flagged for Dev.** |
| 6 | Test quality | Self-checked: no `assert True`, no bare-truthy-on-always-None. Every assert checks concrete values (queue sizes, `(kind,pid,reason)` tuples, payload dicts) or the spy-call list. `monkeypatch.setattr(emitters, "_emit_recipient_dropped", …)` / `(emitters, "_deliver_to_connected_recipients", …, raising=False)` patch **where used** (the `emitters` module), not where defined — correct target. |
| 1 | Silent exception swallowing | The fan-out builder keeps `_deliver_fanout`'s existing `try/except … logger.error("fanout_failed")` — NOT a bare swallow (logs + skips one recipient). Dev must preserve that log, not drop it into the helper as a silent continue. **Flagged for Dev.** |
| — | No Source-Text Wiring Tests (repo CLAUDE.md) | Wiring proven by **spying the live helper symbol** and asserting it's invoked through the real `_deliver_fanout` / real `emit_event` supplier branch — behavioral, not `read_text()`/grep. Compliant. |

### Notes / risks for Dev
- The supplier wiring test drives the real `emit_event` via a minimal `_FakeHandler` (real `SessionRoom`
  + fake `_event_log` whose `repository.transaction()` yields incrementing seq) — no Postgres needed for
  *that* test. The fuller behavior is covered by the PG-backed `test_confrontation_single_delivery.py`.
- `emit_event`'s signature is `emit_event(handler, kind, payload_model, *, author_player_id=None,
  per_recipient_payload=None)` — positional handler/kind/payload. (My first draft mis-called it with
  `room=`/`event_log=` kwargs → spurious TypeError; fixed before commit. Don't reintroduce.)
- Helper lives in `emitters.py` (same module as both callers + `_emit_recipient_dropped`) — no new
  import cycle.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Supplier-path wiring test driven through a fake handler, not the PG handler factory**
  - Spec source: 59-22-context.md, Testing Strategy ("at least one assertion must prove BOTH production
    call sites go through the helper")
  - What the spec implied: a wiring assertion on the supplier path.
  - What I did: drove the real `emit_event` supplier branch via a minimal `_FakeHandler` (real
    `SessionRoom` + fake `_event_log`) instead of the heavyweight `session_handler_factory` +
    `migrated_db` Postgres fixture used by `test_confrontation_single_delivery.py`.
  - Why: the wiring assertion only needs the supplier branch to *reach* the delivery loop; standing up
    Postgres + a genre pack for a spy-the-helper check is unnecessary weight. Full PG-backed behavior
    parity remains covered by the existing `test_confrontation_single_delivery.py` suite, which Dev must
    keep green. No behavior is asserted in the fake-handler test beyond "helper was called."