---
story_id: "45-41"
jira_key: null
epic: "45"
workflow: "tdd"
---
# Story 45-41: OTEL exporter not flowing — Jaeger registered but receives 0 spans (ADR-090 partial)

## Sm Assessment

**Routing:** Bug fix in observability subsystem — TEA writes failing wiring test first (verifies span reaches Jaeger end-to-end), then Dev fixes the per-event emit path. The story is well-scoped: known-good state (service registered, schema known) plus known-bad state (zero traces in 3hr session) narrows the fault to the emit path or sampler/flush.

**Why TDD over trivial:** The wiring test IS the bug-detection mechanism per CLAUDE.md "Every Test Suite Needs a Wiring Test." Without it, a fix that touches the right file but doesn't actually restore span flow could pass review. The test must traverse emit → tracer → exporter → Jaeger HTTP API.

**Risk:** Possible the exporter config is correct and the issue is upstream in `sidequest/telemetry/` watcher hooks not invoking the tracer. TEA may discover the test surface during RED phase exploration.

## Story Details
- **ID:** 45-41
- **Jira Key:** (local-only, no Jira ticket)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-04T03:22:59Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-03T23:02:00Z | 2026-05-04T03:02:51Z | 4h |
| red | 2026-05-04T03:02:51Z | 2026-05-04T03:10:33Z | 7m 42s |
| green | 2026-05-04T03:10:33Z | 2026-05-04T03:14:52Z | 4m 19s |
| spec-check | 2026-05-04T03:14:52Z | 2026-05-04T03:15:58Z | 1m 6s |
| verify | 2026-05-04T03:15:58Z | 2026-05-04T03:18:19Z | 2m 21s |
| review | 2026-05-04T03:18:19Z | 2026-05-04T03:21:57Z | 3m 38s |
| spec-reconcile | 2026-05-04T03:21:57Z | 2026-05-04T03:22:59Z | 1m 2s |
| finish | 2026-05-04T03:22:59Z | - | - |

## Context from Playtest Pingpong

**Source:** `/Users/slabgorb/Projects/sq-playtest-pingpong.md` lines 80–114 (2026-05-03 playtest session notes)

### Symptom
After ~3 hours of gameplay (28 turns), zero traces persisted in Jaeger despite service registration and known operation schemas.

### Known State
- Service name `sidequest-server` **IS** registered with Jaeger ✓
- Operation schemas exist and are known:
  - `watcher.state_transition`
  - `watcher.turn_complete`
  - `smoke.jaeger_wiring` (test operation)
- Jaeger sidecar config: `oq-2/infra/jaeger/config.yaml`

### Hypothesis
Per-event emit path in `sidequest/telemetry/` either:
1. Does not actually invoke the tracer
2. Has sampler set to 0 (drop all spans)
3. Spans are created but never flushed to the exporter

### Verification Path
1. **Trigger one watcher event** (turn_complete easiest — occurs on every turn)
2. **Query Jaeger HTTP API:**
   ```bash
   curl 'http://localhost:16686/api/traces?service=sidequest-server&limit=10&lookback=5m'
   ```
3. **Expected:** At least one trace with `operationName=watcher.turn_complete` or similar
4. **Success criteria:** Response includes `traceID`, `duration`, and span list (non-empty)

### CLAUDE.md Context
**From CLAUDE.md OTEL Observability Principle:**
> Every backend fix that touches a subsystem MUST add OTEL watcher events so the GM panel can verify the fix is working. Claude is excellent at "winging it" — writing convincing narration with zero mechanical backing. The only way to catch this is OTEL logging on every subsystem decision. **The GM panel is the lie detector. If a subsystem isn't emitting OTEL spans, you can't tell whether it's engaged or whether Claude is just improvising.**

This story is a foundational fix for ADR-090 (OTEL dashboard restoration after Python port — accepted but partial). Without span flow to Jaeger, the entire observability layer is dark.

## Delivery Findings

### TEA (test design)

- **Improvement** (non-blocking): Two env vars (`SIDEQUEST_OTLP_ENDPOINT` and `SIDEQUEST_WATCHER_AS_SPANS`) gate the entire Jaeger trail; both are unset by `just up` and only set by `just up-traced`. The playtest used `just up`, so the silent-default explains the 0-span observation. Affects `justfile:306-326` (`up-traced` recipe) and `sidequest-server/sidequest/telemetry/setup.py:48` + `sidequest-server/sidequest/telemetry/watcher_hub.py:54` (the two env gates). Dev should consider whether the right fix is "loud-fail at startup" (this story's RED tests) or also "default-on when Jaeger is reachable" (broader scope; would require a justfile change too). *Found by TEA during test design.*
- **Question** (non-blocking): The pingpong reports operations `watcher.state_transition`, `watcher.turn_complete`, and `smoke.jaeger_wiring` are KNOWN to Jaeger — meaning a prior process exported them. With Badger storage at /tmp/sidequest-jaeger/ persisting schema across runs, this is consistent with "earlier `just up-traced` run registered them, then `just up` produced no new traces." Worth confirming during GREEN that the registered-but-empty state isn't misleading. Affects `infra/jaeger/config.yaml` (Badger TTL behavior). *Found by TEA during test design.*

### TEA (test verification)

- No upstream findings during test verification.

### Dev (implementation)

- **Gap** (non-blocking): The full server test suite has 45 pre-existing failures (3822 pass) on develop, in unrelated subsystems — `_StubRoom` missing `session` attribute (`session_helpers.py:382`), `LocalDM.decompose(room=...)` signature mismatch, opening-turn double-emit, momentum/dice broadcast spans. None touch `sidequest/telemetry/setup.py`. Affects `tests/server/test_dice_throw_*.py`, `tests/server/test_opening_turn_bootstrap.py`, `tests/server/test_session_handler_localdm_offline.py`, `tests/server/test_turn_manager_round_invariant.py`, `tests/server/test_multiplayer_party_status.py`. Out of scope for 45-41 — likely needs its own bug story. *Found by Dev during GREEN phase.*
- **Improvement** (non-blocking): The right long-term fix per CLAUDE.md OTEL Observability Principle is probably for `just up` to default-on the OTLP env vars when Jaeger is reachable on `:4317` (auto-detect, not auto-default). The loud-fail warnings shipped here make the silent-failure visible, but the operator still has to remember to use `just up-traced` or set env vars manually. A justfile change probing `curl localhost:16686` and exporting the env vars when reachable would close the loop. Affects `justfile` `up` recipe and possibly a new `up-auto-traced` variant. *Found by Dev during GREEN phase — captured for future story.*

## Design Deviations

### Architect (reconcile)

- No additional deviations found.

**Verification of existing entries:**

- **TEA (test design) — "Wiring test substitutes InMemorySpanExporter for OTLPSpanExporter"** — All 6 fields present and substantive. Spec source path (`.session/45-41-session.md`, "Wiring Test (Critical)" section) exists at lines 109-126 of this same session file. Spec text quoted accurately. Implementation description matches the actual code in `tests/telemetry/test_otlp_export_wiring.py:188-217` (`test_publish_event_lands_in_span_processor_when_synth_enabled`). Rationale (Jaeger HTTP roundtrip would be flaky without sidecar) is sound. Severity (minor) appropriate. Forward impact ("Reviewer may want a follow-up gated integration test") accurately reflects the optional follow-up; Reviewer accepted the deviation without requesting the gated test. ✓ Entry stands as written.
- **TEA (test verification)** — "No deviations from spec" — Confirmed; the verify-phase only removed dead code (a helper from earlier fixture refactor) which is tracked in the assessment, not a spec deviation.
- **Dev (implementation)** — No subsection appears under Design Deviations. Verified by re-reading the diff (`git diff develop...HEAD`): the implementation matches the TEA "Where Dev Should Look" specification exactly (two `logger.warning` blocks at the specified locations, both naming the named env vars). No silent deviation slipped through.
- **Reviewer (audit)** — "No undocumented spec deviations found" — confirmed by my own diff re-read.

**AC deferral check:** No ACs were formally tracked as deferrable (this story is a bug fix from the playtest pingpong, not a feature with separate ACs). The "AC" is "loud-fail when OTLP is dormant or half-wired" and that ships in full.

**Boss-readable summary:** One deviation total, fully documented, accepted by Reviewer. No drift, no missed entries, no follow-up debt beyond the two non-blocking improvements already captured in Delivery Findings (justfile auto-detect + pre-existing 45 unrelated test failures).

### TEA (test verification)

- No deviations from spec.

### TEA (test design)

- **Wiring test substitutes InMemorySpanExporter for OTLPSpanExporter**
  - Spec source: `.session/45-41-session.md`, "Wiring Test (Critical)" section
  - Spec text: "Retrieve traces from Jaeger HTTP API with filter `service=sidequest-server&operationName=watcher.turn_complete`"
  - Implementation: `test_publish_event_lands_in_span_processor_when_synth_enabled` uses InMemorySpanExporter via the existing `test_watcher_event_spans.py` fixture pattern, not a live Jaeger HTTP curl
  - Rationale: The Jaeger HTTP roundtrip requires a running sidecar — the unit test would either be skipped most of the time or flaky. The OTLP exporter is verified separately by `test_init_tracer_registers_otlp_exporter_when_endpoint_set`, so we cover (a) "the OTLP wire is plugged in" and (b) "publish_event produces a span on the same provider," which together transitively prove end-to-end. A live-Jaeger curl test could be added later as a marker-gated integration test (`pytest -m jaeger_required`).
  - Severity: minor
  - Forward impact: Reviewer may want a follow-up gated integration test. Not blocking for GREEN.

## Test Plan (TDD)

### Wiring Test (Critical)
**Name:** `test_watcher_turn_complete_span_reaches_jaeger`

**Setup:**
1. Boot server with OTEL exporter + Jaeger sidecar running
2. Load a live session or fixture with >= 1 turn playable
3. Trigger a turn completion (advance turn via WebSocket command or direct game_state mutation)
4. Wait <= 500ms for span flush

**Assertions:**
1. Retrieve traces from Jaeger HTTP API with filter `service=sidequest-server&operationName=watcher.turn_complete`
2. Assert `traces[0]` exists (at least one trace returned)
3. Assert `traces[0].spans` is non-empty
4. Assert at least one span has `operationName='watcher.turn_complete'` or similar
5. Assert span carries expected attributes (e.g., `round`, `turn_id`)

**Why wiring test:** Verifies end-to-end from emit site → tracer → BatchSpanProcessor → gRPC exporter → Jaeger persistence. A unit test of the emit site alone would pass even if the exporter is dead.

### Unit Tests (Supporting)
1. **Exporter initialization:** Assert `TracerProvider` is created and exporter is configured
2. **Sampler not disabled:** Assert sampler decision is not `DROP` for all spans
3. **Spans created and batched:** Mock the gRPC transport and assert BatchSpanProcessor queues and flushes spans on configured intervals

## Implementation Notes

### Related ADRs
- **ADR-090** — OTEL dashboard restoration after Python port (accepted, partial)
- **ADR-058** — Claude subprocess OTEL passthrough
- **ADR-031** — Game watcher semantic telemetry

### Files to Check
- `sidequest/telemetry/exporter.py` — OTEL exporter setup and initialization
- `sidequest/telemetry/watcher.py` or equiv — Per-event span emission
- `sidequest/server/websocket_session_handler.py` — Turn completion event site
- `infra/jaeger/config.yaml` — Jaeger sidecar configuration
- `.session/archive/` — Prior playtest session records for trace history

### Key Questions
1. Is the exporter actually initialized during server startup?
2. Is the sampler filtering all spans?
3. Are spans created but the BatchSpanProcessor never flushed?
4. Is there a race condition between turn completion and span flush?

---

*Session file created 2026-05-03 for story 45-41 — local-only bug fix (no Jira). Ready for TDD phase execution.*

---

## TEA Assessment

**Tests Required:** Yes
**Reason:** Bug fix to silent-fallback in observability subsystem; CLAUDE.md "Every Test Suite Needs a Wiring Test" applies directly.

**Test Files:**
- `sidequest-server/tests/telemetry/test_otlp_export_wiring.py` — 6 tests (2 RED, 4 GREEN pins)

**Tests Written:** 6 tests across the OTLP/watcher-bridge surface

| Test | Purpose | Status |
|------|---------|--------|
| `test_init_tracer_warns_when_otlp_endpoint_unset` | Loud-fail when OTLP exporter dormant | **failing (RED)** |
| `test_init_tracer_warns_when_otlp_set_but_watcher_synth_unset` | Loud-fail on half-wired state | **failing (RED)** |
| `test_init_tracer_silent_dormant_notice_does_not_fire_when_fully_wired` | Negative: no false-positive warnings | passing |
| `test_publish_event_lands_in_span_processor_when_synth_enabled` | E2E wiring (publish → tracer → exporter) | passing |
| `test_publish_event_does_not_reach_exporter_when_synth_disabled` | Negative: bridge default behavior | passing |
| `test_init_tracer_registers_otlp_exporter_when_endpoint_set` | OTLPSpanExporter is on the provider | passing |

**Status:** RED (2 failing — Dev must add the loud-fail logging)

### Rule Coverage

| Rule (`.pennyfarthing/gates/lang-review/python.md`) | Test(s) | Status |
|-----------------------------------------------------|---------|--------|
| #1 Silent exception swallowing (no-silent-fallback) | `test_init_tracer_warns_when_otlp_endpoint_unset`, `test_init_tracer_warns_when_otlp_set_but_watcher_synth_unset` | failing (these enforce the rule on the OTLP setup path) |
| #4 Logging coverage and correctness | Both warning tests assert specific log content (env var name, dormant signal) | failing |

**Self-check:** No vacuous tests. Every test asserts on either log content, exporter type identity, or span attribute values. Negative tests assert empty-list invariants which are the meaningful inverse of their positive counterparts.

**Rules checked:** 2 of the python lang-review rules apply directly to this story (logging + silent-fallback). Other rules (mutable defaults, type annotations, etc.) don't apply because the change is a 5-10 line addition to an existing well-typed function.

### Where Dev Should Look

Two surfaces touched by this fix:

1. **`sidequest-server/sidequest/telemetry/setup.py`** — `init_tracer()` body. Add:
   - When `otlp_endpoint` is None: `logger.warning("otel.otlp_dormant — set SIDEQUEST_OTLP_ENDPOINT=host:port to flow spans to Jaeger; no traces will leave this process")`
   - When `otlp_endpoint` is set AND `os.environ.get("SIDEQUEST_WATCHER_AS_SPANS") != "1"`: warn that semantic events won't reach the exporter and name the env var.

2. **Optional follow-up** (non-blocking, captured in Delivery Findings): consider whether the right long-term fix is also a justfile change so `just up` defaults to the traced configuration when Jaeger is reachable.

**Handoff:** To Dev (Ponder Stibbons) for GREEN.

---

## Dev Assessment

**Phase:** finish
**Status:** complete

### Implementation

Single file change: `sidequest-server/sidequest/telemetry/setup.py` (+27 lines, no removals).

Added two `logger.warning` blocks inside `init_tracer()`:

1. **`otel.otlp_dormant`** — fires when `SIDEQUEST_OTLP_ENDPOINT` is unset. Tells the operator no spans will leave the process and names the env var with an example value (`localhost:4317`).
2. **`otel.watcher_bridge_disabled`** — fires when OTLP IS set but `SIDEQUEST_WATCHER_AS_SPANS` is not `"1"`. Tells the operator `publish_event` semantic events won't reach Jaeger and names the env var to fix it.

Both warnings name the env var so the fix is discoverable from `tail -f /tmp/sidequest-server.log` alone, no source-grep required. Each comment block explains *why* the warning exists (the silent-fallback failure mode and CLAUDE.md OTEL Observability Principle), not what it does.

### Test Results

- New tests (`tests/telemetry/test_otlp_export_wiring.py`): **6/6 passing** — both RED tests now GREEN.
- Telemetry suite (`tests/telemetry/`): **162/162 passing** — no regressions.
- Targeted regression scope (`tests/server/test_turn_span_wiring.py`, `tests/smoke/`): **passing**.
- Full suite: **3822 pass, 45 pre-existing failures** in unrelated subsystems (logged in Delivery Findings).

### Lint

`uv run ruff check sidequest/telemetry/setup.py` — clean.
`uv run ruff format sidequest/telemetry/setup.py` — no changes needed.

### Wiring Verification

The new warning logs ARE the wiring — they fire from `init_tracer()` which is called once at FastAPI startup (`sidequest/server/app.py:151`). So on the next `just up`, the server log will show one of the two warnings, proving the fix is live in production code, not just in tests.

### Handoff

To TEA (Igor) for the verify phase (simplify + quality-pass).

---

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

The Dev implementation matches the TEA "Where Dev Should Look" specification exactly:

1. **`otel.otlp_dormant`** — fires when `SIDEQUEST_OTLP_ENDPOINT` is unset, names the env var, gives an example value (`localhost:4317`), explicitly states "no spans will leave this process." ✓
2. **`otel.watcher_bridge_disabled`** — fires when OTLP is set but `SIDEQUEST_WATCHER_AS_SPANS != "1"`, names the env var, explains semantic events won't reach Jaeger. ✓

Both warnings live inside `init_tracer()` (called once at app startup from `app.py:151`), so the operator sees them on `tail -f /tmp/sidequest-server.log` immediately after `just up`. Log keys are stable, machine-grep-able identifiers (`otel.otlp_dormant`, `otel.watcher_bridge_disabled`) so future ops automation can assert on them.

### Architectural Notes (no decision required)

- **No ADR needed.** This is a +27 line bug fix to an existing well-bounded function, not a pattern shift. The setup.py module docstring already describes the env-gate model and remains accurate.
- **CLAUDE.md alignment.** The fix is the textbook application of the "No Silent Fallbacks" rule from the project Development Principles — when something isn't where it should be (the OTLP wire, the bridge), fail loudly. Both warnings name the misconfiguration AND the remediation, which is the standard the principle implies but does not spell out.
- **OTEL Observability Principle alignment.** The fix doesn't add OTEL spans (the bug is upstream of any subsystem that would emit one) — it makes the OBSERVABILITY layer itself self-observing. That's load-bearing: if the lie detector is dark, every other subsystem's spans are useless because they have no destination.
- **Forward design question (deferred per Dev finding):** Should `just up` auto-detect Jaeger on `:4317` and default-on the env vars when reachable? Architectural answer: yes, this is the right long-term shape per CLAUDE.md "GM panel is the lie detector" — observability should be on by default, not opt-in. But it belongs to a follow-up story (justfile change + smoke test for the auto-detect probe), not this fix. Captured in Dev's Delivery Findings.

**Decision:** Proceed to TEA verify. No code changes required.

---

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Approach:** Inline simplify pass (per "right-size plan ceremony" memory rule for sub-200-LOC mechanical changes — three parallel haiku subagents on 27 production lines + 1 test file would be ceremony tax). Manual eyeball + ruff.

**Files Analyzed:** 2 (`sidequest/telemetry/setup.py`, `tests/telemetry/test_otlp_export_wiring.py`)

**Findings:**

| Lens | Finding | Action |
|------|---------|--------|
| reuse | None — both files use existing patterns (existing fixture style from `test_watcher_event_spans.py`, existing logger from `setup.py`) | n/a |
| quality | Dead helper `_attach_in_memory_exporter` left over from earlier fixture refactor | **applied** — removed in commit a097f1a |
| efficiency | None — log calls are O(1), no nested loops, no allocations beyond the f-string | n/a |

**Applied:** 1 high-confidence fix (dead helper removal)
**Flagged for Review:** 0
**Noted:** 0
**Reverted:** 0

**Overall:** simplify: applied 1 fix

### Quality Checks

- **`uv run ruff check sidequest/telemetry/setup.py tests/telemetry/test_otlp_export_wiring.py`** — All checks passed.
- **`uv run pytest tests/telemetry/ tests/server/test_turn_span_wiring.py tests/smoke/`** — 169 passed, 0 failed.
- **Wider `pf check` / `just check-all`** — 17 pre-existing lint errors and 45 pre-existing test failures across 10 files I did not touch (orbital, course, narration_apply, session, dice_throw, opening_turn, session_handler, turn_manager, multiplayer_party — see Dev Delivery Findings). Confirmed by file-scoped `ruff check` on the changed files passing clean. No simplify revert needed.

### Verify-phase Wiring Check

The 6 tests in `test_otlp_export_wiring.py` traverse `init_tracer()` and `publish_event()` end-to-end. The new warnings are exercised by the two RED-now-GREEN tests directly. The OTLPSpanExporter registration and the publish_event→span bridge are exercised by the wiring tests. No mocks of the code under test — only of the global `set_tracer_provider` to dodge OTEL's set-once lock, which is captured in the `captured_provider` fixture's docstring.

**Handoff:** To Reviewer (Granny Weatherwax) for code review.

---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A — 169/169 tests pass on changed scope, 0 code smells, lint clean on both changed files |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings (`workflow.reviewer_subagents.edge_hunter=false`) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 returned, 8 skipped per project settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred (preflight observations are non-blocking; addressed inline below)

### Rule Compliance (Python lang-review checklist)

Rule-by-rule enumeration of every check applicable to the changed surface (`init_tracer()` in `setup.py`, 6 tests in `test_otlp_export_wiring.py`).

| # | Rule | Applies? | Compliance |
|---|------|----------|------------|
| 1 | Silent exception swallowing | Yes (this story IS the silent-fallback fix) | **Compliant** — both new branches add `logger.warning` calls naming the env var. No bare `except`, no swallowed errors. |
| 2 | Mutable default arguments | No new function signatures with mutable defaults | **N/A** |
| 3 | Type annotation gaps at boundaries | No new public functions; existing `init_tracer(service_name: str = ...) -> None` annotations untouched. Test fixtures have full annotations. | **Compliant** |
| 4 | Logging coverage AND correctness | This is the rule the fix enforces | **Compliant** — both new logs use `logger.warning`, neither logs sensitive data, both use simple string concatenation (no f-string interpolation needed since there's nothing to interpolate). The earlier `logger.info("otel.otlp_exporter_registered endpoint=%s", otlp_endpoint)` correctly uses `%s` lazy formatting. |
| 5 | Path handling | No path manipulation in this change | **N/A** |
| 6 | Test quality | 6 new tests | **Compliant** — verified by TEA self-check; every test asserts on log content, span attributes, or exporter type identity. Negative tests assert empty-list invariants which are the meaningful inverse of positives. No `assert True`, no truthy-only checks on non-trivial objects. |
| 7 | Resource leaks | No file/socket/lock acquisitions | **N/A** |
| 8 | Unsafe deserialization | No deserialization paths | **N/A** |
| 9 | Async/await pitfalls | `init_tracer` is sync; no async added | **N/A** |
| 10 | Import hygiene | Lazy `from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter` inside the OTLP branch (preserved from prior code, mirrored inside the test that needs it) — intentional, keeps gRPC dependency optional at module load | **Compliant** |
| 11 | Security: input validation at boundaries | No user input flows through this path; env vars are operator-controlled | **N/A** |
| 12 | Dependency hygiene | No dependency changes | **N/A** |
| 13 | Fix-introduced regressions | Re-scanned the diff against #1–#12 above | **Compliant** — the fix doesn't introduce new bare excepts, swallowed errors, or mutable-default patterns. |

**Result:** Compliant on all applicable rules. Zero violations.

### Review Observations (5+ required)

1. **[VERIFIED] Idempotency preserved — `setup.py:36-38`**: `init_tracer` retains the `_initialized` short-circuit at line 36-38, so the new warnings fire AT MOST ONCE per process. Confirmed by reading the function — no path bypasses the gate. Complies with the project Development Principle "no silent fallbacks" without flipping to "noisy on every call."
2. **[VERIFIED] Warnings name the remediation — `setup.py:79-83, 90-94`**: Both warning messages explicitly mention the env var the operator should set (`SIDEQUEST_OTLP_ENDPOINT`, `SIDEQUEST_WATCHER_AS_SPANS`) AND give an example value (`localhost:4317`, `1`). Operator can fix without grepping source. This is the load-bearing intent of the fix.
3. **[VERIFIED] Wiring at app startup — `setup.py:67-95` invoked from `app.py:151`**: The new warnings live inside `init_tracer()`, which is called once during `_wire_watcher` startup handler. So the operator sees the warnings on the first `tail -f /tmp/sidequest-server.log` after `just up`. Wiring is end-to-end production code, not just tests.
4. **[VERIFIED] Comment policy compliance — `setup.py:69-77, 86-89`**: Both comment blocks explain WHY the warning exists (the silent-fallback failure mode + reference to CLAUDE.md OTEL Observability Principle), not WHAT the code does. Complies with the project's "default to no comments; only explain non-obvious WHY" rule.
5. **[VERIFIED] Test isolation — `test_otlp_export_wiring.py:47-57`**: The `_reset_tracer_init` autouse fixture flips `telemetry_setup._initialized` False around each test so monkeypatched env vars take effect. Scoped to this file (not a `conftest.py` leak), so other test files are unaffected.
6. **[VERIFIED] Set-once-global workaround documented — `test_otlp_export_wiring.py:60-77`**: The `captured_provider` fixture intercepts `set_tracer_provider` to dodge OTEL's set-once global lock. The fixture docstring explains the mechanism (set-once log warning + noop). Future test authors will understand why the indirection exists. Acceptable use of monkeypatch on an internal API since OTEL exposes no test seam.
7. **[NOTE] [SIMPLE] Private SDK attribute walk — `test_otlp_export_wiring.py:283-285`**: `getattr(provider, "_active_span_processor", None)` and `_span_processors` reach into OTEL SDK internals to enumerate processors. Fragile if OTEL refactors, but mirrors the established pattern in `app.py:175-177` (which does the same walk for idempotency checking). Acceptable — same fragility as production code; OTEL has no public API for processor enumeration.
8. **[VERIFIED] [TEST] Wiring test substitutes InMemorySpanExporter for OTLPSpanExporter**: TEA logged this as a deviation. The substitution is appropriate — the OTLP exporter is verified separately (test #6 walks the processor chain), and end-to-end span flow is verified by the publish_event test on the same provider. A live-Jaeger curl test would be flaky without the sidecar running. Accept the deviation. Documented; future story can add a `pytest -m jaeger_required` marker-gated test.
9. **[VERIFIED] [DOC] Module-level docstring captures the bug context — `test_otlp_export_wiring.py:1-29`**: Future maintainers reading the test file get the full playtest-incident summary, the root cause (env-gate silent default), and the three behaviors the file pins. No risk of "what does this test even verify?" rot.
10. **[VERIFIED] [TYPE] Type annotations on new fixtures — `test_otlp_export_wiring.py:60`**: `captured_provider` returns `dict[str, TracerProvider | None]` — explicit mutable-state container with typed contents. Complies with rule #3 type annotations at boundaries.
11. **[NOTE] [EDGE] Empty-string env var edge case**: `os.environ.get("SIDEQUEST_OTLP_ENDPOINT")` returns `""` if explicitly set to empty. The code's `if otlp_endpoint:` correctly treats empty as off (Python's truthy semantics). The dormant warning fires, technically misreporting "is unset" when it's "set to empty." An operator who sets it to empty is signaling "I want it off," and the warning still tells them how to turn it on. Not worth a finding — behavior is correct, message is mostly correct.
12. **[NOTE] [SEC] No tenant/security surface**: This is observability infrastructure for a single-process, single-user dev tool (per CLAUDE.md "SideQuest is built for a specific, real-world gaming group"). No tenant isolation, no PII, no auth tokens in scope. Security audit N/A by inspection.
13. **[NOTE] [SILENT] Silent-fallback IS the bug being fixed**: The whole point of this story is to remove a silent fallback. The fix replaces silence with WARNING-level logs. The change is the antidote, not a new instance of the failure mode.
14. **[NOTE] [RULE] Lang-review compliance verified above** in the Rule Compliance table.

### Devil's Advocate

Let me try to break this code.

What if Jaeger is reachable but the operator deliberately wants traces OFF for a profiling run? Today they unset `SIDEQUEST_OTLP_ENDPOINT` and get silence. After this fix they unset it and get a WARNING in the log on every server start. Annoying but not broken — they can ignore it, set the log filter to ERROR-only, or set `SIDEQUEST_OTLP_ENDPOINT=` to empty (still triggers the warning, but operator's intent is now explicit). The warning is unconditionally emitted — there's no `SIDEQUEST_OTEL_DORMANT_OK=1` opt-out flag for the "I know it's off, leave me alone" case. In a production tool with hundreds of users this would be a finding. For SideQuest's single-developer playtest scope it's fine.

What about test pollution? The autouse `_reset_tracer_init` fixture flips `_initialized` for every test in this file. Suppose a future test added to this file expects `init_tracer` to be a one-shot. Today's tests don't, so no breakage now, but the fixture is invisible to the test author at first glance. Acceptable — the fixture has a docstring explaining the rationale and future authors will see it before adding tests below.

What if `SIDEQUEST_OTLP_ENDPOINT` is set to a malformed value like `not:a:port`? The OTLPSpanExporter constructor will accept the string and gRPC will fail at first export attempt — the failure goes to OTEL's internal log, not ours. But the dormant/half-wired warnings won't fire because both env vars look "set." The operator sees `otel.otlp_exporter_registered endpoint=not:a:port` in the log, then no traces in Jaeger, and re-enters the original silent-failure mode — except this time it's "exporter configured but failing" rather than "exporter not configured." This is OUT OF SCOPE for 45-41 (which is about the env-not-set case), but worth noting as a possible follow-up. Pre-existing weakness, not introduced here.

What if uvicorn `--reload` re-imports setup.py and `_initialized` resets to False? The warning fires again every reload. That's actually GOOD — every server-file edit reminds the operator the tracer is dormant. Not a bug.

What if the warnings flood the log because something else catches WARNING? Pre-existing logging config doesn't suppress WARNING. The warnings fire ONCE per process (via `_initialized`). One line per startup is the floor.

What if a sibling test in `tests/telemetry/` previously relied on `init_tracer` being silent? Check: existing tests in `test_watcher_event_spans.py`, `test_validator_otel_dashboard_restore.py`, `test_turn_span_wiring.py` — none of them assert on log absence. Confirmed by 169/169 pass on the broader telemetry+turn-span+smoke scope. Safe.

What if the fix shipped without changing `just up` to set the env vars? The operator now SEES the dormant warning every time they run `just up`. That's the entire intent: visibility, not auto-correction. The justfile change is captured as a follow-up improvement in Dev's Delivery Findings — separate story.

Verdict: I tried to find a flaw and the fix's tradeoffs are all correct for SideQuest's scope. Approve.

### Deviation Audit

- **TEA test design — Wiring test substitutes InMemorySpanExporter for OTLPSpanExporter** → ✓ ACCEPTED by Reviewer: The substitution is sound. Live Jaeger HTTP roundtrip would require sidecar running and would be flaky in CI. The OTLP exporter registration is verified separately by `test_init_tracer_registers_otlp_exporter_when_endpoint_set`, which together with the publish_event→exporter test transitively proves end-to-end.
- **TEA test verification — No deviations from spec** → ✓ ACCEPTED.

### Reviewer (audit)

- No undocumented spec deviations found. The Dev implementation matches the TEA "Where Dev Should Look" specification exactly (verified in Architect's spec-check).

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `just up` → uvicorn startup → `app.py:151 _wire_watcher` → `init_tracer()` → env-var probe → `logger.warning(...)` → server log file (`/tmp/sidequest-server.log`). Operator sees the dormant/half-wired warning on first `tail -f` after server start. Safe because: (1) warnings name the remediation env var, (2) idempotent via `_initialized`, (3) no PII/secrets in messages, (4) zero behavior change to span-emission paths.

**Pattern observed:** Operator-visible loud-fail at module init time — matches the existing `otel.otlp_exporter_registered` info log pattern (same logger, same `otel.*` key prefix). Tags `otel.otlp_dormant` and `otel.watcher_bridge_disabled` are stable, machine-grep-able identifiers suitable for ops automation.

**Error handling:** N/A — no exception paths added. The new logic is a pure observability injection: env probe + log call.

**Security analysis:** N/A. Observability infrastructure for a single-developer dev tool. No multi-tenant data, no auth tokens, no user input. CLAUDE.md project context is explicit: "SideQuest is built for a specific, real-world gaming group."

**Wiring proof:** The two RED tests (`test_init_tracer_warns_when_otlp_endpoint_unset`, `test_init_tracer_warns_when_otlp_set_but_watcher_synth_unset`) call the production `init_tracer()` and assert on caplog records. The function is called from production code (`app.py:151`). End-to-end wiring confirmed.

**Subagent dispatch tags:** [EDGE]✓ [SILENT]✓ [TEST]✓ [DOC]✓ [TYPE]✓ [SEC]✓ [SIMPLE]✓ [RULE]✓ — see Review Observations and Rule Compliance above.

**Handoff:** To SM (Captain Carrot) for finish-story.

### Reviewer (code review) — Delivery Findings

- No upstream findings during code review. The two follow-ups already captured by Dev (justfile auto-detect + the 45 pre-existing test failures) cover the natural next-step territory; nothing new emerged from the diff itself.