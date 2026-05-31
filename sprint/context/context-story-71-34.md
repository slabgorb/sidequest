---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-34: Extract shared OTEL watcher-test harness (_setup/_Sock/_wait_for) into tests/integration/conftest — dedupe across combat + beat-advance wiring tests

## Business Context

The OTEL-observability principle means every subsystem wiring test drives a real
span through the watcher hub and asserts it broadcasts. To do that, each integration
wiring test stands up the same scaffolding: bind the watcher hub to the running loop,
clear subscribers, subscribe a fake socket that captures broadcast JSON, install a
local `TracerProvider` with a `WatcherSpanProcessor`, and monkeypatch the production
`tracer` to resolve to it — then poll the captured list for the expected event. This
`_setup` + `_Sock` + `_wait_for*` trio is **copy-pasted byte-for-byte** across at
least the combat and beat-advance wiring tests
(`test_encounter_beat_advance_otel_wiring.py` even carries the comment "mirrors
test_combat_otel_wiring.py::_setup"). As more wiring tests land (every Epic-59/71
subsystem needs one), the duplication compounds and any change to the hub-binding
ritual must be made in N places.

This is a pure refactor (no behavior change): lift the shared harness into
`tests/integration/conftest.py` so both tests — and future ones — import it. It pays
down test-debt without touching production code, and it makes the next subsystem
wiring test cheaper to write (which keeps the OTEL coverage bar enforceable).

## Technical Guardrails

**The two source files (identical `_setup`/`_Sock`):**
- `sidequest-server/tests/integration/test_combat_otel_wiring.py` — `_setup`
  (line ~73), inner `class _Sock` (line ~83), `_wait_for_event(captured,
  field_value, *, timeout_s=1.0)` (line ~97, matches a `state_transition` whose
  `fields.field == field_value`).
- `sidequest-server/tests/integration/test_encounter_beat_advance_otel_wiring.py` —
  `_setup` (line ~130, byte-identical to the combat one per its own comment), inner
  `class _Sock` (line ~137), `_wait_for_beat_event(captured, *, timeout_s=1.0)`
  (line ~151, matches on `fields` containing `beat_from`/`beat_to` rather than a
  `field` label).

**Key shape detail for the extraction:** `_setup` and `_Sock` are identical and lift
cleanly. The two wait helpers DIFFER in their match predicate — one matches a
`fields.field` value, the other matches presence of payload keys. Do NOT collapse
them into one signature that loses either behavior. Options (pick the smallest):
  1. Extract a single generic poller `_wait_for(captured, predicate, *,
     timeout_s=1.0)` taking a `predicate: Callable[[dict], bool]`, and keep the two
     call-site-specific matchers as thin local wrappers (or pass lambdas). OR
  2. Extract both `_wait_for_event` (field-value match) and a generic
     predicate-poller into conftest, and have the beat test pass its key-presence
     predicate. The beat helper's docstring deliberately matches on payload content
     "to stay decoupled from whatever discriminator the GREEN phase chooses" —
     preserve that intent.

**The conftest destination:**
- `sidequest-server/tests/integration/conftest.py` — already re-exports fixtures from
  `tests.server.conftest` (`otel_capture`, `session_fixture`, `store_bound_to_hub`,
  etc.). Add the harness helpers here. They are plain async functions / a small
  helper class, not pytest fixtures (the call sites invoke `await _setup(monkeypatch,
  label)` imperatively), so they can be module-level callables in conftest imported
  by name — OR converted to fixtures if that reads cleaner. Match the existing
  conftest's import/re-export style.

**Imports the harness needs** (already present in the two test files): `asyncio`,
`watcher_hub` (`sidequest.telemetry.watcher_hub`), `TracerProvider`,
`WatcherSpanProcessor`, and `spans_module` (the module whose `tracer` is
monkeypatched). Bring these into conftest with the helpers.

**Do NOT touch:** production code (`watcher_hub`, span definitions, any subsystem),
the actual assertions in either test, or the hub-binding/subscribe ritual's behavior.
The captured-event shape and the `tracer` monkeypatch target must remain identical.

## Scope Boundaries

**In scope:**
- Move `_setup` + `_Sock` (and a shared `_wait_for` poller) into
  `tests/integration/conftest.py`.
- Update `test_combat_otel_wiring.py` and `test_encounter_beat_advance_otel_wiring.py`
  to import the shared harness and delete their local copies.
- Preserve each test's distinct match predicate (field-value vs payload-key).

**Out of scope:**
- Migrating other wiring tests that happen to have similar (but not identical)
  helpers — only the combat + beat-advance pair named in the story.
- Converting the helpers to a published test-utils package or changing the broadcast
  capture mechanism.
- Any production change or any change to what the tests assert.

## AC Context

**AC1 — helpers live in conftest.** `_setup`, the `_Sock` fake socket, and a shared
`_wait_for` poller are defined once in `tests/integration/conftest.py`.

**AC2 — both tests import them; locals removed.** `test_combat_otel_wiring.py` and
`test_encounter_beat_advance_otel_wiring.py` no longer define their own
`_setup`/`_Sock`; they import the conftest versions. The beat test's key-presence
match and the combat test's `field`-value match are both still expressed (via
predicate argument or thin wrapper).

**AC3 — tests still pass, no behavior change.** Run
`uv run pytest tests/integration/test_combat_otel_wiring.py
tests/integration/test_encounter_beat_advance_otel_wiring.py -v` — all previously
passing cases pass unchanged. The captured events, the `state_transition` matches,
and the `component`/`field` assertions are identical to pre-refactor.

**Verification for TEA:** this is a refactor, so the "failing test first" is the
existing suite passing before and after. The meaningful check is a green run of both
files plus a grep confirming the local `def _setup` / `class _Sock` are gone from the
two test modules (a legitimate structural check here — it confirms the move
happened — but the load-bearing assertion is the green test run, not the grep).

## Assumptions

- The two `_setup`/`_Sock` definitions are byte-identical (confirmed by reading both;
  the beat-advance file's comment explicitly says it mirrors the combat one), so a
  single extracted copy serves both with no behavioral divergence.
- The differing wait predicates are intentional and must both survive; a single
  predicate-taking poller is the cleanest unification.
- conftest-level plain async helpers are importable by the test modules in this repo's
  pytest layout (the conftest already re-exports callables, so module-level functions
  are reachable). If pytest's conftest semantics make a plain helper hard to import by
  name, expose it as a fixture instead — same behavior, different access pattern.
- No other integration test currently imports a `_setup`/`_wait_for` from these two
  modules (they are module-local), so removing the locals breaks nothing outside the
  two files.

If a third test already silently depends on one of these locals via import, that is a
hidden coupling — log a Design Deviation and notify SM before deleting the local.
