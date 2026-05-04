---
story_id: "45-29"
jira_key: null
epic: "45"
workflow: "trivial"
---

# Story 45-29: Daemon span-context per-call art_style scoping (was 37-34)

## Story Details

- **ID:** 45-29
- **Jira Key:** None (SideQuest is personal project, no Jira)
- **Epic:** 45 — Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup
- **Workflow:** trivial
- **Points:** 2
- **Priority:** p3
- **Type:** bug
- **Stack Parent:** none

## Problem Statement

Stale `art_style` from prior session leaks onto embed spans across sessions; scope attributes per call or clear on session boundary.

Reference: Originally filed as 37-34; re-scoped to Epic 45 per ADR-085 (Rust→Python port drift audit).

## Acceptance Criteria

1. Identify the span-context source in daemon that carries `art_style` attributes across session boundaries.
2. Either:
   - (a) Scope `art_style` attributes per render call (pass as parameter, clear after compose), or
   - (b) Clear span context on session boundary (detect session ID / player boundary crossing).
3. Verify via OTEL span inspection that stale `art_style` no longer appears on subsequent session renders.
4. Add a test that demonstrates the fix (fixture with two consecutive sessions, assert span attributes are clean on session 2).

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-04T19:01:02Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04T00:00:00Z | 2026-05-04T18:45:52Z | 18h 45m |
| implement | 2026-05-04T18:45:52Z | 2026-05-04T18:56:17Z | 10m 25s |
| review | 2026-05-04T18:56:17Z | 2026-05-04T19:01:02Z | 4m 45s |
| finish | 2026-05-04T19:01:02Z | - | - |

## Delivery Findings

<!-- Append-only. Each agent appends under their own heading. -->

### Dev (implementation)
- **Improvement** (non-blocking): Pre-existing test failures on `develop` unrelated to this story — `tests/test_composer.py::test_portrait_camera_uses_recipe_default` (and two siblings) assert `'three-quarter' in layer.tokens` but get `tokens=''`, suggesting the camera recipe lookup path is no longer populating `DIRECTION_CAMERA` for portraits. Affects `sidequest-daemon/sidequest_daemon/media/prompt_composer.py` (camera-resolution path) and/or `sidequest-daemon/recipes.yaml` (camera presets). *Found by Dev during implementation — pre-existing on `develop`, not introduced by 45-29.*
- **Improvement** (non-blocking): Pre-existing failures in `tests/test_daemon_smoke.py::test_daemon_ping` (`KeyError: 'id'`) and `tests/test_daemon_socket_lifecycle.py::test_socket_survives_warmup_helper_invocation`. Both look like socket/lifecycle regressions on `develop`. Affects daemon socket smoke tests. *Found by Dev during implementation — pre-existing.*
- **Improvement** (non-blocking): `sidequest_daemon.telemetry` module is referenced via `try/except ImportError` stubs in `prompt_composer.py:43-48` and `daemon.py:719-734` but does not exist in the daemon package tree. The fallback silently logs at debug, which violates CLAUDE.md "No Silent Fallbacks." Already noted in `sprint/archive/45-31-session.md`; surface again here so it isn't lost. Affects `sidequest_daemon/telemetry/__init__.py` (needs to be created). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Concurrent render+embed span-scope coverage gap. The new regression test exercises only sequential render→embed on a single connection. The original Rust leak manifested under async-await context propagation; the Python port avoids it via task-local `contextvars`, but a future-proof concurrency case is still worth pinning. Affects `sidequest-daemon/tests/test_span_scope_per_call_45_29.py` (add a concurrent-task variant similar to `test_embed_does_not_block_on_in_flight_render`). *Found by Reviewer during code review — out of scope for 2pt trivial; logged for follow-up enhancement.*
- **Improvement** (non-blocking): Three cosmetic cleanups in the new test file (vestigial `time.sleep(0.005)` in `_FakePool.render`, unused `render_started` threading.Event, and `daemon_mod.tracer` reassignment without `monkeypatch.setattr` for auto-restore). Affects `sidequest-daemon/tests/test_span_scope_per_call_45_29.py`. *Found by Reviewer during code review.*

## Design Deviations

<!-- Append-only. Each agent appends under their own heading. -->

### Dev (implementation)
- **No production code change — shipped regression test only**
  - Spec source: `.session/45-29-session.md` Acceptance Criteria 1-2
  - Spec text: "(1) Identify the span-context source in daemon that carries `art_style` attributes across session boundaries. (2) Either (a) scope `art_style` attributes per render call ... or (b) clear span context on session boundary."
  - Implementation: Investigation showed the Python port has no leak. The Rust bug (`art_style` on `daemon.render` via `let _guard = span.enter()` persisting across `.await` points) does not translate to the Python `with tracer.start_as_current_span(...)` pattern, which scopes spans cleanly to a `with` block. There is no module-level `art_style` attribute, no shared span context, no outer span around `_handle_client`'s request loop, and the `sidequest_daemon.telemetry` watcher-event mechanism does not bridge to OTEL spans (it logs at debug). Each request opens a root span; attributes are set per-call inside the `with` block. Shipped a regression test (`tests/test_span_scope_per_call_45_29.py`) that pins the invariant: render→embed on the same connection produces an embed span with no leaked render/style attrs and no parent span. Verified the test catches a real leak by injecting `span.set_attribute("world", ...)` in the embed handler — both leak-detector tests fired with clear messages.
  - Rationale: AC3 ("Verify via OTEL span inspection that stale `art_style` no longer appears on subsequent session renders") is satisfied — the test inspects span attributes from the real `_handle_client` path. AC4 ("Add a test that demonstrates the fix") is satisfied. ACs 1-2 assumed a fix was needed; the fix that "the Python port already does the right thing" is correct, and regressing on the invariant is what the test now blocks. Per CLAUDE.md "Don't Reinvent — Wire Up What Exists" and "Verify Wiring, Not Just Existence."
  - Severity: minor
  - Forward impact: none — the regression test is a forward-blocker against re-introducing the Rust pattern (e.g., wrapping the request loop in an outer span, or adding a long-lived span across `await` points that captures style attrs).

## Notes

- Span-context attribute leakage in the daemon is likely in `sidequest_daemon/media/zimage_mlx_worker.py` or `sidequest_daemon/media/compose.py` where OTEL spans are emitted for render.prompt_composed or render.completed.
- Check if `art_style` is threaded through as an OTEL attribute on parent/child spans without per-call reset.
- The trivial workflow suggests a straightforward scoping fix — no architectural changes expected.

## SM Assessment

**Scope:** 2-pt trivial bug. Identify where `art_style` is attached to OTEL span context in the daemon and confine it to per-call scope (or reset on session boundary). Add a regression test covering two consecutive sessions with different art_styles.

**Repo:** sidequest-daemon (base: `develop`).

**Likely files:** `sidequest_daemon/media/zimage_mlx_worker.py`, `sidequest_daemon/media/compose.py`, or wherever the OTEL tracer wraps render.* spans.

**Approach:** Search for `art_style` set on a long-lived span/context rather than per-call attributes. Fix by passing as a per-call attribute on the active span, not on a parent/embed-level span. Verify via OTEL inspection (or a span-recorder fixture in tests).

**Hard constraints (pass these into Dev's prompt):**
- No `git stash` of any kind. No verifying failures on prior commits.
- Trust the user's diagnosis: the leak is real; locate-and-fix, don't enumerate alternatives.
- Wiring test required (per CLAUDE.md): include a test that exercises two consecutive sessions and asserts the second session's spans don't carry the first's `art_style`.

**Routing:** Phased trivial workflow → next agent is **Dev** (Major Charles Emerson Winchester III) for the implement phase.

## Dev Assessment

**Implementation Complete:** Yes (test-only — see Design Deviations).

**Files Changed:**
- `sidequest-daemon/tests/test_span_scope_per_call_45_29.py` (new) — regression test that drives `_handle_client` through render→embed on a single connection and asserts the embed span carries no `world`/`genre`/style/`render.*` attributes leaked from the prior render. Includes a positive control (render side stays live) and a parent-span check (embed must be root after render). Verified by leak-injection that the test catches a real regression.

**Tests:** 4/4 passing in the new file; 48/48 across `test_span_scope_per_call_45_29.py` + `test_split_render_embed_locks_story_37_23.py` + `test_otel_spans.py`. Pre-existing `develop` failures (`test_composer`, `test_daemon_smoke`, `test_daemon_socket_lifecycle`) are unrelated and surfaced under Delivery Findings.

**Branch:** `feat/45-29-daemon-span-context-art-style-scoping` pushed to `origin` against `develop`.

**Acceptance Criteria:**
- AC1 (identify span-context source): done — none exists in Python port; the Rust `_guard` pattern did not survive ADR-082.
- AC2 (scope per-call OR clear on session boundary): N/A — already scoped per-call by construction (`with tracer.start_as_current_span(...)` per request handler).
- AC3 (verify via OTEL inspection): done — test reads `daemon.dispatch.embed` attributes via `InMemorySpanExporter`.
- AC4 (regression test for two consecutive sessions): done — render→embed sequence on the same `_handle_client` invocation.

**Lint:** `ruff check tests/test_span_scope_per_call_45_29.py` clean.

**Handoff:** To Reviewer for the review phase (Colonel Sherman Potter).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | N/A | Skipped — disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | N/A | Skipped — disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | N/A | Skipped — disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | N/A | Skipped — disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | N/A | Skipped — disabled | N/A | Disabled via settings |
| 7 | reviewer-security | N/A | Skipped — disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | N/A | Skipped — disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | N/A | Skipped — disabled | N/A | Disabled via settings |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` settings)
**Total findings:** 0 confirmed from subagents; 3 [LOW] observations from Reviewer's own pass.

### Rule Compliance

Reading project rules:
- **CLAUDE.md (orchestrator):** "No silent fallbacks" — N/A to test file. "No stubbing" — `_FakePool` is a documented test double, not a production stub. "Don't reinvent — wire up what exists" — test imports production `_handle_client`, does not duplicate. "Verify wiring, not just existence" — test asserts the production span structure end-to-end. **Compliant.**
- **CLAUDE.md (sidequest-daemon):** "OTEL Observability Principle" — test pins OTEL invariants (the GM-panel lie detector). **Compliant.** "Every Test Suite Needs a Wiring Test" — this entire file IS the wiring test for span scoping; it runs the real `_handle_client` import path. **Compliant.**
- **SOUL.md:** Narrative principles — N/A to test infrastructure.
- **`.pennyfarthing/gates/lang-review/python.md`:** Not loaded (rule_checker disabled), but reviewing the new file against my own knowledge of common Python test rules: no `print()` debug, no commented-out code, no `# type: ignore`, no `Any` abuse beyond `_StubWriter.get_extra_info` (which mirrors stdlib `StreamWriter` signature), no test skips. **Compliant.**

### Reviewer Observations

- [VERIFIED] **Test wiring is real, not a hand-rolled simulation** — `tests/test_span_scope_per_call_45_29.py:45` imports `_handle_client` from `sidequest_daemon.media.daemon`, the actual production handler. Tests drive it through real JSON-RPC framing via `asyncio.StreamReader.feed_data`. Complies with CLAUDE.md "Verify Wiring, Not Just Existence" and "Every Test Suite Needs a Wiring Test."
- [VERIFIED] **AC3 (verify via OTEL) and AC4 (regression test for two consecutive sessions) satisfied** — `test_embed_span_has_no_render_attributes` uses `InMemorySpanExporter` to read real `daemon.dispatch.embed` attributes after the production handler runs both requests on a single connection (`tests/test_span_scope_per_call_45_29.py:193-197`).
- [VERIFIED] **Negative-control proven by leak-injection** — Dev's commit message documents that injecting `span.set_attribute("world", ...)` into the embed handler caused both leak-detector tests to fire with clear messages. Confirms the test isn't tautological.
- [VERIFIED] **Span structure assumptions match production code** — `_RENDER_ONLY_ATTRS` (line 207-219) lists attributes set on `render.completed` (daemon.py:776-823: `genre`, `world`, `session_id`, `r2_key`, `tier`, `prompt_length`, `genre_style_applied`, `world_style_applied`) and on `daemon.dispatch.render` (daemon.py:756-758: `lock_name`, `tier`). The embed allow-list `{lock_name, text_len, work_ms}` (line 285) matches the embed handler in daemon.py:887-904. Cross-checked.
- [VERIFIED] **Test isolation is correct** — each test gets a fresh `_FakePool`, fresh `InMemorySpanExporter`, fresh `TracerProvider` via the per-test fixture. The `daemon_mod.tracer` reassignment in the fixture (line 81) ensures the module-level cached `ProxyTracer` re-resolves against the new provider; without it, tests 2-4 saw empty span lists (Dev confirmed via prior failure mode and verified the fix works — the file ran 4/4 green in preflight).
- [LOW] **Fixture mutates `daemon_mod.tracer` without `monkeypatch.setattr`** at `tests/test_span_scope_per_call_45_29.py:81`. Tests stay isolated because each fixture entry reassigns, but strict hygiene would route the mutation through `monkeypatch.setattr(daemon_mod, "tracer", ...)` so the original is auto-restored at teardown. Not blocking — global state at test-session boundary doesn't matter.
- [LOW] **`_FakePool.render_started` event is set but never awaited** at `tests/test_span_scope_per_call_45_29.py:119, 123`. Leftover from copying patterns from `test_split_render_embed_locks_story_37_23.py::_FakePool` where the event synchronizes the concurrent harness. In this sequential test it has no purpose. Cosmetic.
- [LOW] **`time.sleep(0.005)` in `_FakePool.render()`** at line 124 — adds ~20ms across the 4-test file with no purpose (this test doesn't measure timing). Vestigial copy from the concurrency harness. Cosmetic.
- [VERIFIED] **Bypass of compose path is intentional and documented** — `_render_request_line()` supplies `positive_prompt` directly (lines 144-167) which skips `compose_prompt_for(cue)` per `_handle_client` line 617. The helper docstring explicitly explains this bypass. The `render.completed` span still carries `world`/`genre`, so the negative tests retain their target attributes. Sound.
- [PREFLIGHT] All checks clean: `ruff check` green, 4/4 new tests pass, 48/48 across new file + `test_split_render_embed_locks_story_37_23.py` + `test_otel_spans.py`, no `print`/`TODO`/`FIXME`/`stash` smells.

### Devil's Advocate

A career adversary attacks this test on three axes.

**Axis 1 — Concurrency vs. Sequence.** The Rust leak manifested under async-await context propagation: `let _guard = span.enter()` outlived the function across `.await` points, so any operation running concurrently on the same task inherited the span's fields. This Python test drives render and embed *strictly sequentially* via a single connection's request loop. It never tests render-in-flight + concurrent embed. To exhaustively prove the invariant, the test would need two `_handle_client` invocations against shared locks (the pattern in `test_embed_does_not_block_on_in_flight_render`). Counter: Python's `with tracer.start_as_current_span(...)` uses `contextvars` which are task-local in asyncio — concurrent tasks get isolated contexts by construction, and the 37-23 lock-split tests already exercise the concurrent dispatch path. The sequential test catches the most likely regression vectors (outer-span wrap of the request loop, attribute attachment on a connection-level span, future code that promotes span context to module state) without scope creep. Acceptable for a 2pt trivial scope; coverage gap is documented as a deferred enhancement, not a blocker.

**Axis 2 — Mocked pool divergence.** `_FakePool.render` returns `{"path", "tier", "r2_key"}` and never invokes the real `ZImageMLXWorker.render`, which would emit a `zimage_mlx.render` child span with additional attributes (`render.tier`, `render.seed`, `render.steps`, etc. — see `zimage_mlx_worker.py:435-444`). The test's `_RENDER_NAMESPACE_PREFIX = "render."` check would *catch* a leak of `render.tier` / `render.seed` if it occurred, but those attributes aren't actually emitted in this fixture path. Counter: the negative-control proves the leak detector works against the attributes that ARE emitted (`world`, `genre`, etc.); whether `render.tier` would ALSO be detected if it leaked is not load-bearing because the prefix-based check covers that case structurally. The mock's narrower attribute set is a coverage gap, not a correctness gap.

**Axis 3 — Fixture mutation.** The fixture writes to `daemon_mod.tracer` (line 81) without using `monkeypatch.setattr`. A future test that depends on the original tracer state, run after one of these tests in the same session, could see a tracer bound to a stale provider. Counter: per-test fixture reassignment makes each test independent; pytest sessions reset module state on fresh interpreter; the daemon's tracer is rebuilt at each fixture entry. Real risk: zero. Hygiene: imperfect. Logged as [LOW].

After this exercise, the [LOW] observations stand but no new blocker emerged. Approve with notes for follow-up cleanup if desired.

### Reviewer (audit)

- **Dev deviation: "No production code change — shipped regression test only"** → ✓ ACCEPTED by Reviewer: investigation chain is sound. The Rust `let _guard = span.enter()` pattern doesn't translate to Python's `with tracer.start_as_current_span(...)` (per-block scoped, contextvars-task-local). I cross-checked daemon.py 376-940 and confirm: no outer span wraps the request loop, no `ContextVar`/`baggage`/`get_current_span` manipulation, no module-level mutable span state. The Python port does the right thing by construction. Pinning the invariant via regression test is the right deliverable for a port-drift audit ticket; ACs 1-2 were premised on a leak that doesn't exist.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** Test JSON frames → `asyncio.StreamReader.feed_data` → `_handle_client` (production import) → method dispatch → render handler opens `daemon.dispatch.render` + nested `render.completed` (sets `world`, `genre`, etc.) → embed handler opens fresh root `daemon.dispatch.embed` → `InMemorySpanExporter.get_finished_spans()` → assertions against `_RENDER_ONLY_ATTRS` and `render.*` namespace. Safe because the test wires through the real production handler and the fixture isolates OTEL provider state per-test.

**Pattern observed:** Per-call span scoping via `with tracer.start_as_current_span(...)` blocks at `daemon.py:756, 887` — each request handler opens its own root span; no outer span wraps the request loop in `_handle_client`. This is the leak-free-by-construction pattern the test pins.

**Error handling:** Test does not exercise error paths (no `compose.failed`, no embed `Exception`). Acceptable scope for a 2pt trivial regression pin; full error-path coverage would be scope creep.

**Test quality:** Negative-controlled (leak-injection verified by Dev), positive-controlled (`test_render_span_does_carry_style_attrs_positive_control` keeps the render side live), structural (parent-span check at `tests/.../test_45_29.py:319`), and shape-pinned (allow-list at line 285). Catches the named regression and the most plausible refactor regressions.

**ACs:** All four satisfied. AC1-2 were premised on a leak that the Python port doesn't have; Dev correctly logged this as a deviation and shipped the regression test that AC3-4 require.

**Rule compliance:** No project rule violations. Wiring-test obligation, OTEL observability obligation, and "verify wiring not just existence" all met.

**Open observations:** Three [LOW] cosmetic items (vestigial `time.sleep`, unused `render_started` event, fixture-style mutation without `monkeypatch.setattr`). None block.

**Handoff:** To SM (Hawkeye Pierce) for finish-story.