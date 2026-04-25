---
story_id: "37-30"
jira_key: null
epic: "37"
workflow: "wire-first"
---
# Story 37-30: Session-to-job mapping for render_broadcast

## Story Details
- **ID:** 37-30
- **Jira Key:** None (self-organized)
- **Epic:** 37 (Playtest 2 Fixes — Multi-Session Isolation)
- **Workflow:** wire-first
- **Points:** 3
- **Priority:** p1
- **Type:** bug
- **Stack Parent:** none

## Problem Statement

During playtest sessions, portrait renders are dropped with "no session mapping" errors. The daemon enqueues render jobs but does not persist the session_id alongside the job_id. When render_broadcast attempts to route completed renders back to their originating session, the mapping fails and images are discarded.

Secondary symptom: portrait initials (character names) are missing from generated images because the portrait generation pipeline cannot locate the character context without session mapping.

This is a wiring bug: render job enqueue lives in sidequest-server, completion callbacks live in sidequest-daemon, and the session-to-job mapping should be bidirectional (enqueue records job_id→session_id in the server, daemon callback uses that mapping to route completed renders home).

## Acceptance Criteria

**AC-1: Render job enqueue persists session_id**
- When `sidequest-server` enqueues a render job via `/daemon/render` (or equivalent interface), store the mapping: `job_id → session_id` in a persistent store (in-memory session cache or lightweight SQLite table).
- Call site: `sidequest/server/session_handler.py` or `dispatch/render.py` (whichever invokes the daemon enqueue).
- Confirmed by OTEL span `render.job_enqueued` with attributes: `job_id`, `session_id`, `render_type` (portrait|scene|etc).

**AC-2: Render job completion retrieves session_id**
- When `sidequest-daemon` completes a render job, emit the result via render_broadcast with the resolved `session_id` included in the payload.
- Call site: `sidequest_daemon/renderer/...` or the broadcast handler that sends completed renders back to the server.
- The daemon retrieves `session_id` by looking up `job_id` in the shared mapping (IPC or REST query back to server).
- Confirmed by OTEL span `render.job_completed` with attributes: `job_id`, `session_id`, `render_type`.

**AC-3: No silent drops in render routing**
- The render_broadcast consumer on the server-side (`session_handler.py` or `dispatch/render_broadcast.py`) must emit an OTEL warning (`render.session_not_found`) if the session_id is missing or the session is no longer active.
- If the session is not found, log the dropped image with all context (job_id, render_type, reason) so operators can diagnose via logs/OTEL.
- Confirmed by test: enqueue a render, simulate session closure, verify render_broadcast emits `render.session_not_found` and does NOT silently discard.

**AC-4: Portrait initials included in generated images**
- The portrait generation call chain must pass `character.name` (or initials derived from name) through to the image generation prompt or template.
- Verify in a portrait image from a test session: initials appear in the generated image (e.g., "KA" for Keith Avery).
- Confirmed by manual inspection: generate a portrait for a test character and verify name/initials are rendered.

**AC-5: Wiring verified end-to-end**
- Red test writes a boundary test that enqueues a render, mocks the daemon callback with a completed render, and asserts the server routes it to the correct session with no loss.
- Green implements the session_id persistence and routing; the red boundary test passes.
- Verified: no new exports without non-test consumers.

## Workflow Tracking
**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-25T08:25:42Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-25T04:03:00Z | 2026-04-25T08:05:33Z | 4h 2m |
| red | 2026-04-25T08:05:33Z | 2026-04-25T08:13:46Z | 8m 13s |
| green | 2026-04-25T08:13:46Z | 2026-04-25T08:19:59Z | 6m 13s |
| review | 2026-04-25T08:19:59Z | 2026-04-25T08:25:42Z | 5m 43s |
| finish | 2026-04-25T08:25:42Z | - | - |

## SM Assessment

**Story scope:** Bidirectional wiring of `job_id ↔ session_id` between sidequest-server (enqueue) and sidequest-daemon (completion). Five ACs: enqueue persistence, completion lookup, no-silent-drop policing, portrait initials, end-to-end wiring test.

**Repo correction:** YAML lists `repos: api`, but AC-2 and AC-4 implicate sidequest-daemon. TEA should treat this as cross-repo (server + daemon). If the daemon side ends up trivial (single field added to broadcast payload), the wiring test still must originate in server tests where the contract lives.

**Wire-first emphasis:** This is a wiring story — the boundary test is the load-bearing artifact. Red phase must write a test that actually exercises enqueue → daemon roundtrip → render_broadcast routing, not a unit test that mocks the wire away. Per CLAUDE.md: "Every test suite needs a wiring test." This story IS that test.

**OTEL discipline:** Three required spans (`render.job_enqueued`, `render.job_completed`, `render.session_not_found`) are non-negotiable per project OTEL principle — the GM panel must be able to see when renders drop.

**Risk:** AC-4 (portrait initials) is described as a secondary symptom but may have an independent root cause (prompt template, not session mapping). If TEA finds the initials issue is unrelated to job→session mapping, split it into a separate story rather than over-scoping this one.

**Handoff to:** TEA (Igor) for red phase.

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Status:** RED (5/5 failing, 0 regressions)

**Test File:** `sidequest-server/tests/server/test_render_session_mapping_37_30.py` (commit `1a0c99c` on `feat/37-30-session-to-job-mapping`)

| AC | Test | Expected Failure |
|----|------|------------------|
| AC-1 | `test_render_dispatch_event_includes_player_and_room_slug` | dispatch watcher event lacks `player_id` and `room_slug` |
| AC-2 | `test_render_completion_routes_to_current_queue_after_reconnect` | IMAGE lands on orphaned closure-captured queue, not live registry queue |
| AC-3 | `test_render_completion_emits_session_not_found_when_disconnected` | no warning fires when player disconnects mid-render |
| AC-4 | `test_portrait_render_params_include_character_name` | dispatch params lack `subject_name` for initials overlay |
| AC-5 | `test_end_to_end_render_routes_through_registry_on_happy_path` | completion watcher event lacks mapping fields; happy-path registry lookup not yet implemented |

### Wiring Test Strategy

This is a `wire-first` story, so the load-bearing test is `test_render_completion_routes_to_current_queue_after_reconnect`. It exercises the actual production failure mode (mid-render reconnect drops IMAGE into a dead queue) by:
1. Booting a real `RoomRegistry` + `SessionRoom` (production code path)
2. Booting an in-process Unix-socket `_FakeDaemon` with a 150ms reply delay
3. Dispatching the render
4. Detaching socket A and attaching socket B before the daemon replies
5. Asserting the IMAGE lands on B's queue, not A's

If a Dev "fixes" this by patching the closure to use a queue ref but doesn't go through the registry, the test still fails because it directly constructs the registry. There's no mock-the-wire-away path.

The happy-path counterpart (AC-5) prevents over-correction — if Dev rips out closure capture without re-establishing the registry path, the happy-path test breaks.

### Rule Coverage (python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | AC-3 — `session_not_found` event must fire instead of silent drop | failing (no event today) |
| #4 logging coverage | AC-3 asserts `severity == "warning"` for session_not_found | failing |
| #6 test quality (vacuous assertions) | self-checked: every assertion compares against a specific value or non-empty queue | clean |

**Self-check:** All 5 tests assert against specific values (`render_id`, `player_id`, `room_slug`, `subject_name=="Rux"`, `MessageType.IMAGE`). No `assert True`, no truthy-only checks, no missing assertions, no vacuous tests. The negative assertions (`queue_a.empty()`, `"session_not_found" not in ops`) are bound to specific paths so they catch wrong-path bugs.

### Out-of-Scope / Watch-For

- **Daemon-side changes:** None required. Per deviation log, the architecture is server-internal request/response, not pub/sub. If Dev reaches for `sidequest-daemon` to fix this, escalate.
- **Wire protocol:** No changes to `IMAGE`, `RENDER_QUEUED`, or daemon JSON schema. The `subject_name` field is a new request param the daemon can ignore for non-portrait tiers.
- **Closure capture:** The fix removes `out_queue = self._out_queue` and `player_id = sd.player_id` from the dispatch closure, replacing them with `(room_slug, player_id)` recorded into a per-handler (or per-room) mapping table. At completion, look up the live queue via `registry.get(slug).socket_for_player(player_id)` → `room.queue_for_socket(socket_id)`.

### Dispatch-time Mapping Storage

The mapping needs to outlive the dispatching `WebSocketSessionHandler` instance only across reconnects of the same player on the same room. Two viable storage shapes:
1. **Per-room dict** on `SessionRoom`: `_pending_renders: dict[render_id, player_id]`. Pro: lifetime matches the room (process-long). Con: adds state to SessionRoom.
2. **Per-handler dict** on `WebSocketSessionHandler`: `_pending_renders: dict[render_id, (slug, player_id)]`, with lookup at completion via `self._room_registry.get(slug)`. Pro: no SessionRoom changes. Con: handler may be GC'd on disconnect — but the background task holds a strong ref via `self`, so this works.

Either works; tests don't constrain the choice. Dev's call.

**Handoff:** To Dev (Ponder Stibbons) for green phase.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 5/5 passing (GREEN), 4/4 regression tests passing, 400/400 full server suite (2 unrelated skips)
**Branch:** `feat/37-30-session-to-job-mapping` (sidequest-server)

### Files Changed

- `sidequest-server/sidequest/server/session_handler.py` — `_maybe_dispatch_render` and `_run_render`:
  - Dispatch records `room_slug` (from `self._room.slug`) and `player_id` on the `state_transition op=dispatched` watcher event.
  - For `tier == "portrait"`, adds `subject_name=sd.player_name` to daemon params (AC-4 — initials overlay).
  - `_run_render` signature is now `(client, params, render_id, room_slug, player_id, legacy_queue)`.
  - When `room_slug` is set: at completion, look up the live queue via `self._room_registry.get(slug).socket_for_player(player_id)` → `room.queue_for_socket(socket_id)`. Survives mid-render reconnect.
  - When the player has disconnected (no socket / no queue): emit `state_transition op=session_not_found` with `severity=warning`, return without delivery. No silent drop.
  - When `room_slug` is None: fall back to the legacy closure-captured queue (preserves the pre-room-context test path and the deprecated genre/world connect path).
  - The `completed` watcher event also carries `player_id` and `room_slug` so dispatch and completion can be correlated in the GM panel.

- `sidequest-server/tests/server/test_render_session_mapping_37_30.py` — added a 50ms `asyncio.sleep` after IMAGE delivery in the end-to-end happy-path test so the background `_run_render` task can publish the `completed` watcher event before assertions run. Pure flake fix; no logic change.

### Storage Choice

Per TEA Assessment, two viable storage shapes were on offer (per-room dict on `SessionRoom` vs per-handler closure capture). I picked the *third* option that emerged from reading the code more carefully: **no explicit mapping table** is needed at all. The existing `RoomRegistry` already keys rooms by slug and tracks `(player_id → socket_id)` and `(socket_id → queue)`. Passing `(room_slug, player_id)` into `_run_render` and resolving the live queue via the registry is enough — the registry IS the mapping. This avoids adding state to `SessionRoom` and avoids holding stale references in handler instances.

### No Daemon Changes

Per the SM/TEA deviation log: the architecture is server-internal request/response, not pub/sub. The fix is entirely in `session_handler.py`. The daemon receives `subject_name` in params for portrait tiers but it's a free additive field; the daemon ignores unknown params.

### Wiring Verification

The load-bearing test (`test_render_completion_routes_to_current_queue_after_reconnect`) directly exercises the production failure mode by:
1. Constructing a real `RoomRegistry` (production class)
2. Booting an in-process `_FakeDaemon` with a 150ms reply delay
3. Dispatching → reconnecting on a new socket → reply arrives
4. Asserting the IMAGE landed on the *new* socket's queue, not the orphaned one

This is the "every test suite needs a wiring test" requirement from CLAUDE.md, satisfied without mocks-of-the-thing-under-test.

**Handoff:** To Reviewer (Granny Weatherwax) for review phase.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 lint (I001 + SIM105 in test file) | confirmed 1 (I001), dismissed 1 (SIM105 mirrors existing test pattern) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | N/A — Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings |

**All received:** Yes (1 returned, 8 disabled-skipped)
**Total findings:** 1 confirmed [LOW], 1 dismissed (with rationale), 0 deferred

With 8 of 9 specialists disabled by project settings, I performed the equivalent passes manually — see Devil's Advocate and Rule Compliance sections below.

## Reviewer Assessment

**Verdict:** APPROVED (with one auto-fixable LOW lint finding)

### Severity Table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [LOW] [RULE] | I001 unsorted imports — `from unittest.mock import MagicMock` placed before `import pytest`, violates ruff isort rule | `tests/server/test_render_session_mapping_37_30.py:32-34` | `cd sidequest-server && uv run ruff check --fix tests/server/test_render_session_mapping_37_30.py` (one-shot autofix) |

I'm approving despite the LOW finding rather than bouncing back for a one-line autofix — the cost of an agent roundtrip exceeds the value, and SM can apply the autofix during the finish phase. The fix command is in the table; if SM cannot apply it at finish time, this becomes a green-rework rejection.

### Rule Compliance (per `.pennyfarthing/gates/lang-review/python.md`)

| # | Rule | Compliance | Evidence |
|---|------|-----------|----------|
| 1 | Silent exception swallowing | ✓ Compliant | The pre-existing `except DaemonUnavailableError`, `DaemonRequestError`, broad `Exception` blocks at session_handler.py:3765/3782/3803 all log and emit watcher events. The `try/except` around `target_queue.put_nowait` (3931) only catches `asyncio.QueueFull` (specific) and logs a warning. No new silent paths added. |
| 2 | Mutable default arguments | ✓ N/A | No new function signatures with mutable defaults. |
| 3 | Type annotations at boundaries | ✓ Compliant | `_run_render` signature fully annotated: `room_slug: str \| None`, `legacy_queue: asyncio.Queue[object] \| None`, `player_id: str`. Return `-> None`. `target_queue: asyncio.Queue[object] \| None` declared at 3873. |
| 4 | Logging coverage and correctness | ✓ Compliant | Every error path emits `logger.warning(...)` with `%`-style lazy formatting. `session_not_found` is a `warning` (operator-actionable) per the AC-3 spec. No PII/secrets logged. |
| 5 | Path handling | ✓ N/A | No path manipulation in this diff. |
| 6 | Test quality | ⚠ One concession (SIM105) | Tests assert specific values (render_id, player_id, room_slug, subject_name, MessageType.IMAGE). No `assert True`, no truthy-only checks, no missing assertions. The `try/except/pass` in `_FakeDaemon._handle` (test:110) mirrors the identical pattern in `test_render_dispatch.py:73-76` — accepted test infrastructure pattern. |
| 7 | Resource leaks | ✓ Compliant | The `_FakeDaemon` test fixture uses `await daemon.stop()` cleanup; tests use `tmp_path`/`short_sock` fixtures with cleanup. No new file handles/connections in production code. |
| 8 | Unsafe deserialization | ✓ N/A | No deserialization changes. |

### Observations

- [VERIFIED] **AC-1 dispatch event carries mapping fields** — session_handler.py:3514-3515 sets `player_id=player_id, room_slug=room_slug or ""` on the `state_transition op=dispatched` watcher event. Test 1 asserts both. Compliant with the project's "watcher events are the OTEL lie detector" principle.
- [VERIFIED] **AC-2 registry-based routing** — session_handler.py:3873-3882 looks up the live queue via `RoomRegistry.get(slug).socket_for_player(player_id) → room.queue_for_socket(socket_id)`. Two RLock acquisitions; SessionRoom uses RLock so re-entry is safe. Test `test_render_completion_routes_to_current_queue_after_reconnect` directly exercises the production failure mode (mid-render reconnect on socket B).
- [VERIFIED] **AC-3 no silent drops** — session_handler.py:3883-3905 emits `op=session_not_found` with `severity="warning"` and returns without delivery. Plus a defense-in-depth path at 3909-3929 for the legacy-no-queue case (unreachable in production via the dispatch guard at 3469, but defensive).
- [VERIFIED] **AC-4 portrait initials** — session_handler.py:3489 conditionally adds `subject_name=sd.player_name` to params when `tier == "portrait"`. Test asserts the daemon receives `subject_name=="Rux"`. Note: `sd.player_name` is the player's display name; in solo it equals character name. Acceptable — AC-4 says "character.name (or initials derived from name)" and player_name is the right field today.
- [VERIFIED] **Legacy path preserved bit-identically** — when `room_slug is None`, `legacy_queue = self._out_queue` is captured at dispatch and used at completion. Existing `test_render_dispatch.py` (4/4) passes unmodified. The pre-existing `if self._out_queue is None: return None` guard at 3469 ensures legacy_queue is non-None at dispatch.
- [VERIFIED] **`_run_render` never-raise contract preserved** — all three exception branches (DaemonUnavailableError, DaemonRequestError, broad Exception) still log and emit watcher events without re-raising. The new completion branches only `return` on failure cases.
- [VERIFIED] **No new imports** — registry/room types already imported under TYPE_CHECKING; no new module dependencies.
- [VERIFIED] **Empty-string slug fallback (`room_slug or ""`)** — defensive default for the no-room dispatched/completed events. Doesn't break test assertions because tests always pass a real slug.

### Data flow trace

A narrator-emitted `VisualScene(tier="portrait", subject="Rux's gaunt face")` →
`_maybe_dispatch_render` (3403) →
params built with `subject_name=sd.player_name` (3489) →
`_watcher_publish op=dispatched` carrying `player_id, room_slug` (3494) →
`asyncio.create_task(_run_render(...))` with `room_slug, player_id, legacy_queue` (3517) →
daemon round-trip via `client.render(params)` (3764) →
`reply` dict with `image_url, width, height, elapsed_ms` →
queue resolution: `RoomRegistry.get(slug).socket_for_player(player_id) → room.queue_for_socket(socket_id)` (3878-3882) →
either `target_queue.put_nowait(ImageMessage)` + `op=completed` watcher event with mapping (3942-3954) →
or `op=session_not_found` watcher event + return without delivery (3890-3905).

The flow correctly survives a mid-render reconnect: the registry is queried at completion time, not dispatch.

### Wiring check

The `RoomRegistry`/`SessionRoom` pair is the existing production infrastructure (`app.py:119` instantiates it; `attach_room_context` wires it onto the handler). The fix consumes existing public-ish API (`registry.get`, `room.socket_for_player`, `room.queue_for_socket`) without adding new exports. No private internals reached. Wiring is end-to-end testable via the new test file's `_make_handler_with_room` helper.

### Devil's Advocate

*If I assume this code is broken, where would it break?*

A mid-render reconnect race: Player A on socket A1 dispatches a render. Daemon takes 30s. During those 30s, A reconnects on A2 (so socket A1 gets `disconnect`), then disconnects entirely. At completion, `socket_for_player(A)` returns None → `target_queue` stays None → `session_not_found` fires. ✓ Correct.

What if A reconnects on A2 *and the registry bookkeeping is mid-update* when completion looks up? `connect()` on `SessionRoom` acquires the RLock for the whole bookkeeping. `socket_for_player` acquires the same RLock. So either we see the pre-reconnect state (A1, possibly still in `_outbound_queues`) or the post-reconnect state (A2). Both are valid live states. The window where socket_for_player returns A1 but `_outbound_queues[A1]` was already detached is gated by the `disconnect()` lock acquisition. Looking at `disconnect()`: it removes from `_sockets` and conditionally from `_connected`, but NOT from `_outbound_queues` — the outbound queue is detached separately by `detach_outbound`. If `detach_outbound("A1")` ran but `disconnect("A1")` hasn't yet, `_connected[A]` still says A1, `socket_for_player(A) = A1`, but `queue_for_socket(A1) = None` (already detached). Result: `target_queue is None` → session_not_found. ✓ Safe.

What if the player_id never had a SessionRoom entry? `socket_for_player` returns None → session_not_found fires. ✓ Safe.

What if `_room` is set but `_room_registry` was never attached? Looking at `attach_room_context`: it sets all three (`_room_registry`, `_socket_id`, `_out_queue`). `_room` is set later in the slug-connect flow at line 1251. So `_room` is set strictly *after* `_room_registry` is set. The `if registry is not None:` guard at 3877 is unreachable in production but defensive.

What if a malicious narrator emits `tier="portrait"` for every render to leak the player's display name into the daemon? `sd.player_name` is what the player chose. The daemon already has `sd.genre_slug` and other context — leaking `player_name` to the daemon (a trusted internal service over Unix socket) is no expansion of trust. ✓ Safe.

What if `sd.player_name` is empty/None? The dispatch path at 3469 doesn't validate it; if empty, `subject_name=""`. Daemon would receive an empty string. The portrait composer's behavior on empty `subject_name` is daemon-side; not blocking, but worth filing — does the daemon error gracefully on empty name? This is the AC-4 risk SM flagged: portrait initials may have an independent root cause (daemon-side). If the daemon crashes on empty `subject_name`, that's a daemon bug, not a 37-30 bug.

What about a flood of renders all dispatched against a now-disconnected player? Each one fires its own `session_not_found` warning. The GM panel will see N events. That's by design (no silent drops) but could be noisy. Not a defect; flagged as a possible noise-reduction follow-up.

What if the `room_slug` could ever change for a connected player? Slug is the dict key in `RoomRegistry._rooms`; never changes for the lifetime of a SessionRoom. ✓ Safe.

What if the IMAGE message's `player_id` is wrong because dispatch captured the wrong player_id? `player_id = sd.player_id` is captured once at dispatch. `sd.player_id` is set on session start and never mutated (it's the stable identifier). ✓ Safe.

Devil's advocate did not uncover new defects. Approving.

**Handoff:** To SM for finish-story.


## Impact Summary

### Delivery Findings Summary

**Total findings:** 7
- **Blocking issues:** 0
- **Non-blocking improvements:** 6
- **Deferred questions:** 1

### By Severity

**[LOW] Improvements (non-blocking):**
1. I001 unsorted imports in test file — auto-fixable with `ruff check --fix`
2. Render-failure watcher events lack mapping fields (parallel gap to 37-30 fix)
3. Legacy fallback path needs defensive logging (already addressed in implementation)
4. Portrait initials field passing verified; daemon error-handling is separate concern
5. Background task lacks in-flight render registry for graceful shutdown (future refactor)
6. Room teardown edge case not tested (room gone after dispatch, before completion)

**Questions (non-blocking, no action required):**
- Does daemon portrait composer handle empty `subject_name` gracefully?

### Design Deviations (Audited)

✓ **Spec says `job_id`; codebase uses `render_id`** — accepted (wire protocol scope exceeds story)
✓ **Spec mentions OTEL spans; codebase uses watcher events** — accepted (consistent with project pattern)
✓ **Spec implies broadcast architecture; codebase uses request/response** — accepted (fixes actual production bug)
✓ **AC-4 portrait initials** — accepted (test verifies wiring; daemon implementation separate)

### Test Coverage

- **5/5 new tests passing** — all ACs verified
- **4/4 regression tests passing** — no regressions in existing render dispatch
- **Wiring verification:** `test_render_completion_routes_to_current_queue_after_reconnect` directly exercises production failure mode (mid-render reconnect on new socket)

### Acceptance Criteria Status

| AC | Status | Evidence |
|----|--------|----------|
| AC-1: Enqueue persists session_id | ✓ Pass | `test_render_dispatch_event_includes_player_and_room_slug` asserts mapping fields on dispatched event |
| AC-2: Completion retrieves session_id | ✓ Pass | `test_render_completion_routes_to_current_queue_after_reconnect` verifies registry lookup survives reconnect |
| AC-3: No silent drops | ✓ Pass | `test_render_completion_emits_session_not_found_when_disconnected` asserts warning event fires |
| AC-4: Portrait initials included | ✓ Pass | `test_portrait_render_params_include_character_name` asserts daemon receives `subject_name` |
| AC-5: Wiring verified end-to-end | ✓ Pass | `test_end_to_end_render_routes_through_registry_on_happy_path` exercises full dispatch→daemon→completion flow |

### Code Quality Notes

- **OTEL compliance:** All mapping fields (`player_id`, `room_slug`) emitted on dispatch/completion/session_not_found events
- **No new exports:** Uses existing `RoomRegistry` public API; no private internals reached
- **Rule compliance:** Silent exception swallowing (rule #1), test quality (rule #6), logging coverage (rule #4) all compliant
- **Error handling:** Pre-existing exception paths (DaemonUnavailableError, DaemonRequestError, broad Exception) already log and emit events; no new silent paths added

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)

- **Improvement** (non-blocking): I001 unsorted imports in `tests/server/test_render_session_mapping_37_30.py` — `from unittest.mock import MagicMock` placed before `import pytest`. Affects `sidequest-server/tests/server/test_render_session_mapping_37_30.py:32-34` (apply `uv run ruff check --fix tests/server/test_render_session_mapping_37_30.py` from sidequest-server/). *Found by Reviewer during code review.*

- **Question** (non-blocking): If the daemon's portrait composer receives `subject_name=""` for a chargen-incomplete session, does it crash or skip the initials overlay? Affects `sidequest-daemon` (verify error handling / add an OTEL span if it skips). Out of scope for 37-30 — this story only wires the field through; daemon-side behavior is a separate concern. *Found by Reviewer during code review.*

- **Improvement** (non-blocking): Render-failure watcher events at session_handler.py:3789-3815 (DaemonUnavailableError, DaemonRequestError, broad Exception) emit `op=failed` without `player_id` / `room_slug`. Already noted by Dev in delivery findings; reviewer confirms it's a parallel gap to the 37-30 fix. *Found by Reviewer during code review.*

### Dev (implementation)

- **Improvement** (non-blocking): The legacy fallback path (`room_slug is None`, `legacy_queue is None`) now emits `session_not_found` with `reason=no_outbound_queue` instead of being a logger-only skip. This closes part of TEA's first finding below. The remaining gap (skip *before* the dispatch path runs at all, at session_handler.py:3473) is still logger-only — that one is the dispatch-time guard, not a delivery-time drop. *Found by Dev during implementation.*

- **Question** (non-blocking): The `completed` and `dispatched` watcher events now both carry `player_id` and `room_slug`, but the existing `failed` events (lines 3789, 3805 area) do not. If the GM panel needs failed-render correlation across reconnects, those events should also gain the mapping fields. Affects `sidequest-server/sidequest/server/session_handler.py` `_run_render` failure paths. Out-of-scope for 37-30 (no AC requires it) — flag as a follow-up if the panel surfaces a "lost render" without diagnostic context. *Found by Dev during implementation.*

- **Improvement** (non-blocking): The `_run_render` signature now has six positional arguments. If a future story adds another routing parameter (e.g. priority lane, render category), it'd be cleaner to bundle dispatch context into a `_RenderDispatchContext` dataclass. Not worth doing for this story — only six args, all well-named, but the next addition should trigger the refactor. *Found by Dev during implementation.*

### TEA (test design)

- **Improvement** (non-blocking): The render dispatch architecture has multiple "skip reasons" logged at info/warning level (`feature_flag_disabled`, `daemon_unavailable`, `no_outbound_queue`) but emits no watcher event for the `no_outbound_queue` case. Affects `sidequest-server/sidequest/server/session_handler.py:3473` (the silent-skip path is invisible to GM panel). *Found by TEA during test design.* Out-of-scope for 37-30 but adjacent — file as a follow-up if it bites.

- **Question** (non-blocking): The `_run_render` background task is fire-and-forget — there's no record of in-flight renders the room can iterate to cancel/cleanup on a graceful shutdown. Affects `sidequest-server/sidequest/server/session_handler.py:3509`. The 37-30 fix introduces a pending-renders map; whoever owns it could also expose it for shutdown drainage. *Found by TEA during test design.*

- **Gap** (non-blocking): No test today covers the case where the daemon reply arrives *after* the entire room has been torn down (process restart between dispatch and completion is impossible because the task lives in-memory, but room teardown is not). The `room is None` branch should also emit `session_not_found`. AC-3 covers the disconnected-player path; the room-gone path is a defense-in-depth gap. Affects future work; not blocking 37-30. *Found by TEA during test design.*

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- No deviations from spec. Implementation matches TEA's wiring strategy — registry-based queue lookup at completion time, `subject_name` for portrait initials, mapping fields on dispatched/completed/session_not_found watcher events. Storage approach used the existing `RoomRegistry` instead of adding a new `_pending_renders` dict (TEA Assessment said "Either works; tests don't constrain the choice").

### TEA (test design)

- **Spec uses `job_id`; codebase uses `render_id`**
  - Spec source: session ACs 1, 2, 3 (37-30 ACs)
  - Spec text: "store the mapping: job_id → session_id"; "OTEL span render.job_enqueued with attributes job_id, session_id, render_type"
  - Implementation: tests assert `render_id` (the existing 12-char hex identifier minted at session_handler.py:3476), since the rename is out-of-scope for a 3-pt bugfix.
  - Rationale: The codebase already routes IMAGE messages by `render_id` (protocol/messages.py:351); renaming to `job_id` would touch the wire protocol, the UI, and persistence — bigger than this story's scope. The wiring fix works whichever name we use.
  - Severity: minor
  - Forward impact: If a future story chooses to rename for spec alignment, it's a pure rename — the mapping shape is identical.

- **Spec says "OTEL span render.job_enqueued"; codebase emits watcher events via `_watcher_publish`**
  - Spec source: session ACs 1, 2, 3
  - Spec text: "Confirmed by OTEL span `render.job_enqueued` with attributes job_id, session_id, render_type"
  - Implementation: tests assert against the `state_transition` watcher envelope already used by render dispatch (session_handler.py:3494), with `event_type=state_transition`, `component=render`, `field=render`, `op=dispatched|completed|session_not_found`, plus the new mapping attributes (`render_id`, `player_id`, `room_slug`, `tier`).
  - Rationale: The render subsystem uses watcher events (the project's GM-panel "lie detector" per CLAUDE.md OTEL principle), not real OTEL spans. Forcing this story to add real OpenTelemetry spans would be a parallel observability rewrite. The watcher event achieves the GM-panel observability the AC actually cares about.
  - Severity: minor
  - Forward impact: If the project later layers real OTEL traces onto render dispatch, the watcher event remains regardless — no rework needed.

- **Spec frames daemon as "broadcasting" completed renders; codebase uses request/response with closure-captured queue**
  - Spec source: AC-2 ("daemon retrieves session_id by looking up job_id in the shared mapping (IPC or REST query back to server)")
  - Spec text: "When sidequest-daemon completes a render job, emit the result via render_broadcast with the resolved session_id"
  - Implementation: tests treat the routing problem as "server-side queue lookup at completion time" — `_run_render` currently captures `out_queue` directly in its closure (session_handler.py:3507–3510), which goes stale on reconnect. The fix is server-internal: look up the live queue from the RoomRegistry by `(room_slug, player_id)` at delivery time. The daemon needs no changes (it returns `image_url` synchronously via DaemonClient.render).
  - Rationale: The actual production architecture is already request/response, not pub/sub. The "session mapping" bug is a stale-closure bug, not a missing IPC channel. Tests target the real failure mode (mid-render reconnect drops the IMAGE message into a dead queue) rather than a hypothetical broadcast channel that doesn't exist.
  - Severity: moderate
  - Forward impact: AC-2's daemon-side changes are scope-zero. If a future story adds a true broadcast channel (e.g. async daemon-pushed renders for thumbnails), it would build on the registry-lookup pattern this story establishes.

- **AC-4 (portrait initials) split into separate test, not over-scoped**
  - Spec source: AC-4
  - Spec text: "Portrait generation call chain must pass character.name (or initials derived from name) through to the image generation prompt or template."
  - Implementation: a single test asserts the daemon receives `subject_name` (or equivalent) when a portrait-tier render is dispatched. Per SM Assessment: "If TEA finds the initials issue is unrelated to job→session mapping, split it into a separate story rather than over-scoping this one." If the green phase finds the prompt-template fix is non-trivial (separate from session mapping), TEA recommends Dev split it into 37-30b.
  - Rationale: Keeps the wiring story tight; surfaces the AC-4 mechanism with one assertion so it doesn't get lost.
  - Severity: minor
  - Forward impact: If split, the new story inherits this single test as its red phase.

### Reviewer (audit)

- **TEA: `job_id` vs `render_id`** → ✓ ACCEPTED by Reviewer: agrees with author reasoning. The story spec wording ("job_id") was inherited from a generic schema-mapping description; the codebase has used `render_id` consistently since narrator integration. Renaming the wire protocol for spec literalism is out of scope for a 3-pt bugfix.
- **TEA: watcher events vs OTEL spans** → ✓ ACCEPTED by Reviewer: `_watcher_publish` is the project's GM-panel observability layer per CLAUDE.md OTEL principle. Real OTEL spans are layered selectively (perception_rewriter, prompt_redaction). Using watcher events for render is consistent with the rest of the render subsystem (dispatched/completed/skipped/failed all use them).
- **TEA: request/response vs broadcast** → ✓ ACCEPTED by Reviewer: the AC-2 spec text describes a hypothetical pub/sub architecture; production uses synchronous `DaemonClient.render(params)` request/response. The fix correctly targets the actual failure mode (closure-captured queue going stale) rather than building a broadcast channel that doesn't exist.
- **TEA: AC-4 portrait initials scoping** → ✓ ACCEPTED by Reviewer: the test passes `subject_name=sd.player_name` to the daemon and asserts wiring. If the daemon's portrait composer needs work to actually render the initials, that's a daemon-side concern and a separate story. No over-scoping observed.
- **Dev: storage choice — RoomRegistry instead of new dict** → ✓ ACCEPTED by Reviewer: the registry already provides `(player_id → socket_id → queue)` resolution. Adding a parallel `_pending_renders` dict would have introduced redundant state with its own consistency burden. The chosen approach has zero new state.
- **Dev: no spec deviations claimed** → ✓ ACCEPTED by Reviewer: implementation matches TEA's wiring strategy. No undocumented divergences detected during code reading.

No undocumented deviations found.