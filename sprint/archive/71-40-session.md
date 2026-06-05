---
story_id: "71-40"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-40: Per-turn latency diagnosis — router decompose + narrator tool-loop p50/p95 + env-vs-code/iteration attribution

## Story Details
- **ID:** 71-40
- **Jira Key:** (local-only story, no Jira key)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repo:** sidequest-server (gitflow, targets develop)
- **Branch:** feat/71-40-per-turn-latency-diagnosis
- **Branch Strategy:** gitflow (standard feature branch off develop)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T12:35:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T12:01:40Z | 2026-06-05T12:04:39Z | 2m 59s |
| red | 2026-06-05T12:04:39Z | 2026-06-05T12:13:10Z | 8m 31s |
| green | 2026-06-05T12:13:10Z | 2026-06-05T12:24:30Z | 11m 20s |
| review | 2026-06-05T12:24:30Z | 2026-06-05T12:35:32Z | 11m 2s |
| finish | 2026-06-05T12:35:32Z | - | - |

## Sm Assessment

**Setup complete — ready for RED (TEA).**

71-40 is a merge of former 71-22 (router decompose pass) and 71-26 (narrator
tool-loop pass), combined at the user's request because both bracket the two LLM
passes per turn against the same 2026-05-27 `coyote_star`/Glenross playtest latency
finding. This is a **diagnosis story, not a fix** — instrument and attribute, do not
tune.

**For TEA (RED):** five ACs in `sprint/context/context-story-71-40.md`:
- AC1 — router `intent_router.decompose` p50/p95 (reuse `validator.py:_percentile`)
- AC2 — router env-vs-code split: raw SDK round-trip (inside `emit_tool`) vs.
  bookkeeping + serialized `state_summary` size
- AC3 — solo-turn p95 from `agent_duration_ms` / `complete_with_tools` summary
- AC4 — `iterations_used` exposure + iteration cap with OTEL cap-hit span, **without
  weakening** the existing `AnthropicSdkLoopExceeded` fail-loud ceiling
- AC5 — written diagnosis artifact (both passes)

**Two required wiring tests** (CLAUDE.md — no source-text wiring tests): one driving
the *real* `IntentRouter.decompose` (mocked `IntentRouterLLM`) asserting router
attributes land on the `intent_router.decompose` span; one driving the *real*
`complete_with_tools` (mocked SDK) asserting the cap span emits through the watcher
hub. Mocked-LLM tests assert instrumentation presence only — real env-vs-code numbers
come from a live/recorded run.

**Surfaces are distinct and must not bleed:** router work lives in
`intent_router.py` / `intent_router_pass.py` / `llm_factory.py`; narrator-loop work
in `anthropic_sdk_client.py`. Do NOT touch the confidence gate, retry contract
(`_MAX_TOTAL_ATTEMPTS=2`), streaming (71-23), or the cost-ceiling alarm (61-4).

**Branch:** `feat/71-40-per-turn-latency-diagnosis` in sidequest-server (off
develop; PR targets develop). Dual-clone hazard noted — orchestrator session here,
code branch in the subrepo.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (13 failing, 1 passing-by-design — ready for Dev)

**Test Files:**
- `tests/telemetry/test_latency_report.py` (AC1 + AC3) — the shared p50/p95
  harness. Pins a new module `sidequest/telemetry/latency_report.py` exposing
  `latency_percentiles(values) -> LatencyPercentiles(p50, p95, count)` that
  **delegates to `validator._percentile`** (behavioral reuse proof, not a source
  grep). Covers empty→0.0, equality-with-`_percentile`, and the load-bearing
  tail-inclusion edge case (a retry-/loop-inflated outlier must raise p95 — the
  harness never silently drops it).
- `tests/agents/test_intent_router_latency_attribution.py` (AC2 — **router wiring
  test**) — drives the *real* `IntentRouter.decompose` (mocked `IntentRouterLLM`)
  and asserts the `intent_router.decompose` span carries two NEW attributes:
  `sdk_latency_ms` (env: raw `emit_tool` round-trip) and `state_summary_bytes`
  (code: serialized prompt size). Invariant `sdk_latency_ms <= latency_ms`;
  `state_summary_bytes == len(summary.encode())` for a string summary; monotonic
  growth with summary size.
- `tests/agents/test_anthropic_sdk_tool_loop_iterations.py` (AC4 — **narrator
  wiring test**) — drives the *real* `complete_with_tools` (fake SDK transport)
  and asserts a `narrator.tool_loop` summary span records `iterations_used`
  (2 for tool→text, 1 for one-shot), a new `iteration_cap` param fires a
  `narrator.tool_loop.cap_hit` span when crossed, and `AnthropicSdkLoopExceeded`
  **still raises** at the ceiling (fail-loud preserved). Plus a SPAN_ROUTES
  registration check (runtime registry interrogation) so the spans reach the GM
  hub via WatcherSpanProcessor.

**Tests Written:** 14 tests covering ACs 1–4. **RED verified** (`uv run pytest -n0`):
all instrumentation tests fail on missing module / missing span attrs / unknown
`iteration_cap` kwarg / unregistered span routes; the one green test
(`test_loop_ceiling_still_raises_without_cap`) guards the *existing* ceiling that
this story must not weaken.

### Rule Coverage

| python.md check | Test(s) | Status |
|------|---------|--------|
| #6 test quality (no vacuous asserts) | tail-inclusion + one-shot-vs-runaway + monotonic-bytes are differential, not truthy | passing-as-design |
| #3 type annotations at boundaries | `latency_percentiles(values) -> LatencyPercentiles`; `iteration_cap: int \| None` param pinned by call shape | failing (impl pending) |
| OTEL Observability Principle (CLAUDE.md) | every new subsystem decision emits a span: `sdk_latency_ms`/`state_summary_bytes` on decompose, `narrator.tool_loop` + `.cap_hit` | failing |
| No Source-Text Wiring Tests (CLAUDE.md) | wiring proven by driving real `decompose`/`complete_with_tools` + SPAN_ROUTES registry interrogation, never `read_text()` greps | passing-as-design |
| #1 silent exceptions / fail-loud | `AnthropicSdkLoopExceeded` ceiling preserved (explicit guard test) | passing |

**Rules checked:** 4 of 13 lang-review checks are materially applicable to this
diagnosis story (most #s — path handling, deserialization, async blocking, deps —
have no surface here). **Self-check:** 0 vacuous assertions; every test asserts a
specific value or a differential (with-tail > without-tail, large > small,
iterations 2 vs 1).

**Handoff:** To Dev (Naomi) for GREEN. Implementation surfaces (kept distinct, do
not bleed): router half in `intent_router.py` (time `emit_tool` separately from
the loop bookkeeping; record serialized state-summary size) + the decompose span;
narrator half in `anthropic_sdk_client.py` (`iteration_cap` param + new
`narrator.tool_loop[.cap_hit]` spans following the `intent_router.py` span-route
pattern in `telemetry/spans/`) ; harness in new `telemetry/latency_report.py`.

## Dev Assessment

**Implementation Complete:** Yes (AC1–AC4 instrumentation; AC5 prose artifact
deferred — see Delivery Findings)

**Files Changed:**
- `sidequest/telemetry/latency_report.py` (new) — `LatencyPercentiles` +
  `latency_percentiles()` p50/p95 harness, delegates to `validator._percentile`,
  no input filtering (tails move p95). **AC1 + AC3.**
- `sidequest/agents/intent_router.py` — extracted `_serialize_state_summary`
  (shared by the prompt builder + the new attr); `decompose` now times the
  successful `emit_tool` round-trip separately (`sdk_latency_ms`) and records the
  serialized state-summary byte size (`state_summary_bytes`) on the
  `intent_router.decompose` span, alongside the existing total `latency_ms`.
  Invariant `sdk_latency_ms <= latency_ms` holds by construction. **AC2.**
- `sidequest/telemetry/spans/intent_router.py` — added `sdk_latency_ms` +
  `state_summary_bytes` to the `intent_router.decompose` SPAN_ROUTES extract so
  the GM panel surfaces the env-vs-code split.
- `sidequest/agents/anthropic_sdk_client.py` — `complete_with_tools` gains an
  `iteration_cap: int | None` param; fires `narrator.tool_loop` (summary,
  `iterations_used` per converged turn) and `narrator.tool_loop.cap_hit` (once,
  when the soft cap is crossed). The `AnthropicSdkLoopExceeded` ceiling is
  unchanged (cap is observational, not a stop — see deviation). **AC4.**
- `sidequest/telemetry/spans/narrator.py` — two new routed spans + context-manager
  helpers (`narrator_tool_loop_span`, `narrator_tool_loop_cap_hit_span`),
  registered in SPAN_ROUTES for the WatcherSpanProcessor → GM hub.

**Tests:** 14/14 GREEN (`uv run pytest -n0` on the three story files). Lint
(ruff) + format + pyright clean on all changed files. No regressions: the two
`tests/agents/` failures (`test_output_only_prose_under_byte_budget`,
`test_active_stakes_path_applies`) fail identically on the stashed clean tree —
pre-existing. The flaky leak-audit test filters by a span name I never emit
(`make_canned_client` uses the CLI backend, not `complete_with_tools`) and is
order-dependent fixture pollution (logged as a non-blocking finding).

**Branch:** `feat/71-40-per-turn-latency-diagnosis` (pushed, `5791023`)

**Handoff:** To verify/review. Note the blocking AC5 finding — the diagnosis
report needs a live capture before the story is truly done.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): the narrator tool-loop has no turn-level
  iteration summary today — only a per-iteration `llm_request_span(iteration=N)`.
  Dev should add the `narrator.tool_loop` summary span on the success-return
  branch of `complete_with_tools`. Affects `sidequest/agents/anthropic_sdk_client.py`
  (~line 566-605 return path). *Found by TEA during test design.*
- **Question** (non-blocking): AC4's `iteration_cap` is specced as observability +
  "earlier recorded throttle," but the cap-vs-ceiling *stop semantics* are left to
  design — the tests only assert the cap-hit span fires and the ceiling still
  raises, NOT whether crossing the cap halts the loop. Dev/Architect should decide
  whether the cap is a soft warning threshold (loop continues to the hard ceiling)
  or a hard early stop, and document it. Affects
  `sidequest/agents/anthropic_sdk_client.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (blocking): AC5's prose diagnosis artifact (which cause dominates each
  pass, with captured numbers) is NOT delivered — it requires a live/recorded
  `coyote_star`/Glenross capture against a real `ANTHROPIC_API_KEY` to read real
  `sdk_latency_ms` / `state_summary_bytes` / `iterations_used`. GREEN delivered
  the full AC1–AC4 instrumentation that produces those numbers on the real
  decompose + `complete_with_tools` paths. Affects a new
  `sprint/` or `docs/` report artifact (must be written from a live capture
  before story-done). *Found by Dev during implementation.*
- **Improvement** (non-blocking): the `otel_capture` fixture in
  `tests/agents/conftest.py` adds a `SimpleSpanProcessor` to the live singleton
  `TracerProvider` and only `shutdown()`s it on teardown — it never *removes* the
  processor. Across a full `tests/agents/` run this leaks processors onto the
  shared provider and makes span-count tests order-dependent
  (`test_run_narration_turn_emits_leak_audit_span_with_zero_leaks` flips
  pass/fail by ordering, independent of this story — confirmed by stashing my
  changes). Affects `tests/agents/conftest.py` (teardown should pop the processor
  / use an isolated provider). Pre-existing; mirrors the documented server-suite
  OTEL deadlock. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): the `narrator.tool_loop` summary span fires on
  EVERY converged `complete_with_tools` call, including the non-narrator dungeon
  **curate** stage (`dungeon/materializer.py:1208`, default client is
  `AnthropicSdkClient` per line 2043). So dungeon-generation SDK loops emit a
  span named `narrator.tool_loop` (component=`narrator`), contaminating AC3's
  solo-turn p95 source and mislabeling curate calls on the GM panel. The span
  carries no caller discriminator, so the two cannot be separated post-hoc.
  Affects `sidequest/agents/anthropic_sdk_client.py` (rename to a caller-agnostic
  `sdk.tool_loop`, or add a caller/context tag attribute). The existing
  per-iteration `llm_request_span` has the same caller-agnostic behavior, so this
  follows precedent — but the `narrator.`-prefixed name newly implies otherwise.
  *Found by Reviewer during code review.*
- **Gap** (non-blocking): the `narrator.tool_loop` summary span fires ONLY on the
  converged path; a turn that exhausts `max_iterations` and raises
  `AnthropicSdkLoopExceeded` emits NO summary span — so the worst-latency turns
  (the ones the diagnosis most wants to see `iterations_used` for) are invisible
  to that metric. Affects `sidequest/agents/anthropic_sdk_client.py` (emit the
  summary span before the `raise`, e.g. with `loop_exceeded=True`). Not an AC
  violation (AC3's loop-exceeded tail is covered by the harness test), but a real
  diagnostic blind spot for the AC5 analysis. *Found by Reviewer during code review.*
- **Gap** (blocking-for-DONE, not blocking-for-merge): `latency_percentiles`
  (`sidequest/telemetry/latency_report.py`) and the `iteration_cap` knob have NO
  production caller — both are exercised only by tests. This is consistent with
  the ACs (the harness is an offline AC5 tool; the cap is a diagnostic kwarg "as
  diagnosis warrants"), so it does not block the green phase — but the wiring loop
  only closes when AC5 actually invokes the harness and the diagnostic run sets a
  cap. Affects the pending AC5 artifact + `sidequest/telemetry/latency_report.py`
  (add a module note that it is offline-diagnosis-only, or wire the AC5 consumer).
  *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC5 (diagnosis artifact) has no dedicated automated test**
  - Spec source: context-story-71-40.md, AC5
  - Spec text: "A diagnosis (committed as a session/report artifact, not engine code) stating which cause dominates for each pass, with the captured numbers. Testable precondition: the instrumentation from AC1-AC4 is present and emits on the real decompose and complete_with_tools paths."
  - Implementation: AC5 is covered transitively — the AC1-AC4 wiring tests verify the instrumentation precondition. The written report itself (env-vs-code numbers, iteration correlation) is a prose deliverable Dev produces from a live/recorded run; prose is not unit-testable.
  - Rationale: a markdown report's findings cannot be meaningfully asserted by pytest; the testable surface is the instrumentation that produces the numbers, which AC1-AC4 cover.
  - Severity: minor
  - Forward impact: Reviewer/SM must confirm the AC5 report artifact exists before finish — it is not gated by a test.
- **`latency_percentiles` module path chosen by TEA**
  - Spec source: context-story-71-40.md, AC1/AC3
  - Spec text: "reuse it [validator._percentile]" / "the measurement harness produces p50 and p95 numbers from a list of captured decompose spans"
  - Implementation: tests pin the harness at `sidequest/telemetry/latency_report.py::latency_percentiles`. The context names the helper to reuse but not the harness's home.
  - Rationale: a focused new module beside `validator.py` keeps the percentile reuse local and avoids bloating `validator.py`; Dev may relocate if a better home exists, but the contract (delegates to `_percentile`, returns p50/p95/count) is fixed.
  - Severity: minor
  - Forward impact: if Dev moves the module, the test import must move with it.
- **Real env-vs-code latency numbers are not asserted (mocked LLM)**
  - Spec source: context-story-71-40.md, Assumptions
  - Spec text: "Mocked-LLM tests cannot measure real network/env latency ... tests only assert the attribution instrumentation is present and correct."
  - Implementation: AC2/AC4 tests assert the *instrumentation* (attrs present, invariant holds, spans fire) with mocked transport; the actual 4-12s split comes from a live/recorded run in the AC5 report.
  - Rationale: explicitly sanctioned by the story's Assumptions section — no live ANTHROPIC_API_KEY in tests.
  - Severity: minor
  - Forward impact: the diagnosis's real numbers depend on Dev running a live/recorded Glenross capture for AC5.

### Dev (implementation)
- **`iteration_cap` is a SOFT warning threshold, not a hard early stop**
  - Spec source: context-story-71-40.md AC4 + TEA Delivery Finding (Question, "cap-vs-ceiling stop semantics left to design")
  - Spec text: "iteration cap with OTEL cap-hit span, without weakening the existing AnthropicSdkLoopExceeded fail-loud ceiling"
  - Implementation: crossing `iteration_cap` fires exactly one `narrator.tool_loop.cap_hit` span (recording the cap + iterations used) but does NOT halt the loop — it runs on to `max_iterations` and the existing `AnthropicSdkLoopExceeded` still raises. The cap is observability-only, a warning threshold strictly below the hard ceiling.
  - Rationale: this is the behavior TEA's own test pins (`test_iteration_cap_fires_cap_hit_span_and_ceiling_still_raises` sets cap=2, max=5 and asserts the loop STILL raises `AnthropicSdkLoopExceeded`). A hard early stop would have to either raise early or return a truncated result — both contradict that test. A diagnosis story instruments; it does not change control flow. The cap gives the GM panel an earlier "this turn is tool-heavy" signal without altering the turn's outcome.
  - Severity: minor
  - Forward impact: a future tuning story (not this diagnosis) can promote the cap to a hard stop if data shows runaway loops dominate p95 — the cap-hit span is already the hook for that decision.
- **AC5 prose diagnosis artifact not produced in GREEN (requires a live capture)**
  - Spec source: context-story-71-40.md, AC5
  - Spec text: "A diagnosis (committed as a session/report artifact) stating which cause dominates for each pass, with the captured numbers."
  - Implementation: GREEN delivers the full AC1–AC4 instrumentation (the testable precondition AC5 names) but does NOT write the diagnosis report. The report needs real `sdk_latency_ms`/`state_summary_bytes`/`iterations_used` numbers from a live or recorded `coyote_star`/Glenross run against a real `ANTHROPIC_API_KEY`, which the mocked test phase cannot produce.
  - Rationale: fabricating diagnosis numbers without a live capture would violate the OTEL "no winging it" / lie-detector ethos at the heart of this story. The honest deliverable is the instrumentation that produces the numbers; the prose pass belongs to a live-capture step. TEA already logged AC5 as having no automated gate.
  - Severity: minor
  - Forward impact: surfaced as a blocking Delivery Finding — SM/Reviewer must run (or schedule) a live capture and commit the AC5 report before the story is truly done. The instrumentation to produce it is now live on the real paths.

### Reviewer (audit)
- **TEA: AC5 has no dedicated automated test** → ✓ ACCEPTED by Reviewer: a prose markdown report's findings are not pytest-assertable; the testable surface (instrumentation emits on real paths) is covered by AC1–AC4. Agrees with author reasoning.
- **TEA: `latency_percentiles` module path chosen by TEA** → ✓ ACCEPTED by Reviewer: a focused module beside `validator.py` is a reasonable home and keeps the `_percentile` reuse local. Noted separately: because the module has no runtime consumer, its placement in the production `telemetry/` package reads as dead-code-in-waiting — see the Reviewer Delivery Finding asking AC5 to wire it or a docstring to mark it offline-only.
- **TEA: real env-vs-code numbers not asserted (mocked LLM)** → ✓ ACCEPTED by Reviewer: explicitly sanctioned by the story Assumptions ("Mocked-LLM tests cannot measure real network/env latency"); tests assert instrumentation presence, the AC5 live run supplies numbers.
- **Dev: `iteration_cap` is a SOFT warning threshold, not a hard stop** → ✓ ACCEPTED by Reviewer: this is exactly what AC4's test pins (cap-hit fires + `AnthropicSdkLoopExceeded` STILL raises). Independently verified by the silent-failure-hunter: the cap sets a flag and fires a span, then falls through to the unchanged `raise` — no path exits without convergence or the loud ceiling. A diagnosis story must not change control flow; correct call.
- **Dev: AC5 prose artifact not produced in GREEN** → ✓ ACCEPTED by Reviewer: AC5 is explicitly "a session/report artifact, not engine code" requiring a live/recorded capture; fabricating numbers would violate the OTEL lie-detector ethos. Correctly surfaced as blocking-for-DONE.
- **UNDOCUMENTED — `narrator.tool_loop` span fires for the non-narrator dungeon-curate caller:** Spec implied a narrator-scoped tool-loop signal; the code emits the `narrator.`-prefixed span for ANY `complete_with_tools` caller, including `dungeon/materializer.py`'s curate stage. Not logged by Dev. Severity: M (attribution fidelity, non-blocking — recorded as a Reviewer Delivery Finding). The existing `llm_request_span` shares this caller-agnostic property, so it follows precedent.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 MED (wiring gap), 4 LOW/INFO | confirmed 1, dismissed 0, deferred 0 (LOW/INFO folded into observations) |
| 2 | reviewer-edge-hunter | Yes | findings | 3 high-conf (cap≥max inert, no-summary-on-raise×2), several MED/LOW | confirmed 4, downgraded-not-dismissed 0, rest noted |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 LOW (max(0) clamp, sdk_latency init-to-0) | confirmed 2 as LOW; KEY: ceiling-not-weakened VERIFIED |
| 4 | reviewer-test-analyzer | Yes | findings | 3 "block-level"(reviewer-downgraded to MED), 6 MED/LOW | confirmed 4 MED, downgraded 3 high→med w/ rationale, 2 LOW noted |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([DOC] below) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([TYPE] below) |
| 7 | reviewer-security | Yes | clean | none | N/A — clean, no info leak; verified ints-only span attrs |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([SIMPLE] below) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([RULE] below) |

**All received:** Yes (5 enabled returned; 4 disabled pre-filled per settings)
**Total findings:** 11 confirmed (all MEDIUM/LOW, non-blocking), 0 dismissed, 0 deferred; 3 test-analyzer "block-level" findings downgraded high→medium with rationale (code is correct; the findings are test-strength/coverage gaps, not correctness defects)

## Reviewer Assessment

**Verdict:** APPROVED

**Summary:** A clean, well-scoped diagnosis story. The core instrumentation — the
`intent_router.decompose` env-vs-code attribution (`sdk_latency_ms`,
`state_summary_bytes`) and the `narrator.tool_loop` per-turn `iterations_used`
summary — is correct and genuinely wired onto the REAL production paths (both
wiring tests drive real `decompose` / real `complete_with_tools`, not isolated
units). The story's hard guardrail — preserve the `AnthropicSdkLoopExceeded`
fail-loud ceiling — is verified intact by an independent agent and by my own read.
Security is clean (span attributes are ints only; no state-summary content leaks).
14 story + 47 regression tests green; ruff/format/pyright clean. The findings below
are quality, coverage, and forward-diagnostic improvements — none break the
deliverable or violate a hard rule, so none are blocking.

**Data flow traced:** player action → `IntentRouter.decompose(action, state_summary)`
→ `_serialize_state_summary(state_summary)` measured as `state_summary_bytes` (int
byte-length only — content never enters the span) + `emit_tool` timed as
`sdk_latency_ms` → set on the `intent_router.decompose` span → SPAN_ROUTES extract
(ints only) → WatcherSpanProcessor → GM hub. Safe: no PII/prompt content reaches any
span attribute or log line (confirmed by reviewer-security across 4 span routes + 4
log calls).

**Observations (11):**
- [SILENT] **VERIFIED — fail-loud ceiling preserved.** `iteration_cap` sets
  `cap_hit_fired=True` and fires a span, then falls through; the loop still reaches
  `raise AnthropicSdkLoopExceeded` at `max_iterations`. Evidence:
  `anthropic_sdk_client.py:344-355` (cap block has no `return`/`break`) + `:642`
  (raise unchanged). No path exits without convergence or the loud raise.
- [SEC] **VERIFIED — no info leakage.** New span attrs are `sdk_latency_ms`,
  `state_summary_bytes`, `iterations_used`, `iteration_cap`, `max_iterations` (all
  int) + static `severity="warning"`. `state_summary` content is measured via
  `len(...encode())` and discarded — never stored. Evidence: `intent_router.py:411`,
  `narrator.py` extract lambdas. Complies with python.md #4 (never log sensitive data).
- [EDGE][MEDIUM] **`narrator.tool_loop` summary span is not emitted on the
  loop-exceeded raise path** (`anthropic_sdk_client.py:585` block is inside the
  `stop_reason != "tool_use"` convergence branch). The worst-latency turns produce
  no `iterations_used` summary. Non-blocking (AC3's loop-exceeded tail is covered by
  the harness test, and the raise itself is a loud signal) — recorded as a Delivery
  Finding to emit it before the raise.
- [EDGE][LOW] **`iteration_cap >= max_iterations` is silently inert** (cap-hit never
  fires when cap > max; loop exhausts first). No guard rejects a cap that isn't
  strictly below the ceiling. Internal kwarg, no production caller passes it — LOW.
- [TEST][MEDIUM] **`test_sdk_latency_never_exceeds_total_latency` is a weak
  invariant test** (python.md #6). Under `AsyncMock`, both timings floor to 0 ms, so
  the assertion is `0 <= 0` and cannot catch a swapped-window bug. The invariant IS
  structurally guaranteed (sdk window nested in total window), so the CODE is correct
  — but the test should mock `perf_counter_ns` or inject a real sleep. Confirmed, not
  dismissed; severity is MEDIUM because it weakens a test, it does not signal a code defect.
- [TEST][MEDIUM] **cap-hit "exactly once" is unasserted.** The new `cap_hit_fired`
  guard is the load-bearing once-per-turn invariant;
  `test_iteration_cap_fires_cap_hit_span...` only does `assert cap_hits` +
  `cap_hits[0]`, so a regression firing the span every iteration would pass. Add
  `assert len(cap_hits) == 1`.
- [TEST][MEDIUM] **dict→JSON `state_summary_bytes` byte-equality is unasserted.**
  Only the string path asserts exact bytes; the dict path asserts only presence/type.
- [TEST][MEDIUM] **No assertion that the summary span is ABSENT on the raise path**
  — pairs with the EDGE finding; would lock in the convergence-only contract.
- [DOC][LOW] (comment-analyzer disabled — assessed directly) `_serialize_state_summary`
  docstring calls itself "the single source of truth," but it is invoked twice per
  decompose (once for bytes at `:309`, once inside `_build_user_prompt`). Comment is
  slightly aspirational vs. the call pattern; otherwise comments are accurate and the
  dense `# Story 71-40:` rationale is appropriate for a diagnosis story.
- [SIMPLE][LOW] (simplifier disabled — assessed directly) **Double serialization** of
  `state_summary` per decompose — `json.dumps` runs twice for a dict. Mild irony on
  the very hot path being diagnosed; reuse the string from `_build_user_prompt`. The
  `list(values)` copy in `latency_report.py` is also redundant (`_percentile` sorts a
  copy) but harmless. Both LOW.
- [TYPE][LOW] (type-design disabled — assessed directly) Types are clean:
  `iteration_cap: int | None`, `latency_percentiles(values: Sequence[float]) ->
  LatencyPercentiles`, frozen `LatencyPercentiles(p50: float, p95: float, count:
  int)`. Latent hole: `**extra: Any` on both new span helpers is an untyped escape
  hatch a future caller could use to push content into span attrs — unused at the sole
  call site today (security agent corroborated). Note for future call-site proliferation.

### Rule Compliance (python.md lang-review, exhaustive over the diff)
- **#1 silent exceptions / fail-loud:** PASS. No new `except`; the `AnthropicSdkLoopExceeded`
  ceiling is preserved (verified). `latency_percentiles([])→0.0/0.0` is documented with a
  discriminating `count=0`, not a silent mask.
- **#3 type annotations at boundaries:** PASS. All new public functions/dataclass fully
  annotated (`latency_percentiles`, `LatencyPercentiles`, both span helpers, `iteration_cap`).
- **#4 logging — no sensitive data:** PASS. New log calls (`intent_router.py` warnings) carry
  reason + exception repr only; no state_summary/action content.
- **#6 test quality:** PARTIAL — one weak invariant test + three missing assertions (above).
  Not vacuous-true (`assert True`), but weaker than the suite claims. MEDIUM, non-blocking.
- **#8 unsafe deserialization:** PASS / N/A. `json.dumps(..., default=str)` is serialization
  (output), not a code-exec vector.
- **#10 import hygiene:** PASS. New module has `__all__`; `narrator.py`/`intent_router.py`
  imports are explicit (no new star imports; the `spans/__init__.py` star re-export is the
  established registry pattern). No circular import (anthropic_sdk_client → spans.narrator is
  one-directional).
- **#2/#5/#7/#9/#11/#12:** N/A — no mutable defaults, no path handling, no new resource
  acquisition, no new async blocking call (timing uses `perf_counter_ns`, not sleep), no new
  user-input boundary, no dependency change.
- **CLAUDE.md "Verify Wiring / Every Test Suite Needs a Wiring Test":** PARTIAL. The
  instrumentation (decompose attrs + summary span) has genuine wiring tests on real paths —
  PASS. `latency_percentiles` + `iteration_cap` have no production consumer — this MATCHES the
  wiring rule and is CONFIRMED (not dismissed); downgraded to non-blocking because AC1/AC3/AC4
  scope them as an offline harness + diagnostic kwarg whose consumer is the pending AC5 artifact.
  Recorded as a blocking-for-DONE Delivery Finding so the loop closes at story completion.
- **CLAUDE.md "No Source-Text Wiring Tests":** PASS. Wiring proven by driving real code +
  runtime SPAN_ROUTES registry interrogation (the documented legitimate exception), never
  `read_text()` greps.

### Devil's Advocate
Argue this code is broken. The strongest case: this is a *latency-diagnosis* story that
quietly *adds latency on the exact path it measures*. `_serialize_state_summary` now runs
twice per decompose — once to size the prompt, once to build it — so for a large
`state_summary` (precisely the "code suspect" the story is hunting) the router does its most
expensive serialization twice every turn, inflating the very `latency_ms` it reports. A
confused analyst reading the AC5 numbers could conclude the prompt-assembly cost is higher
than it "really" is, because the instrumentation itself doubled it. Second: the headline
metric is a lie by omission. `narrator.tool_loop` fires only on convergence, so every turn
that actually *blows the budget* — the runaway that burns all 8 iterations and raises — emits
no `iterations_used` at all. The p95 tail the story exists to explain is exactly the data the
summary span drops. Worse, the same span fires under the `narrator.` name for the dungeon
*curate* stage, so a Glenross p95 computed naively from `narrator.tool_loop` is silently
polluted by non-narrator SDK loops with no field to filter them out — a stressed operator
diffing two runs could chase a regression that is really just a dungeon being generated.
Third: the cap a stressed user reaches for can't be turned on. `iteration_cap` is a kwarg no
production caller sets and no env/config toggles, so "surfaces throttled turns on the GM
panel" never happens in a real session without a code edit — a feature that exists in the
signature and the tests but not in any reachable runtime. Fourth: a malicious/confused caller
could pass `iteration_cap=0` or `-1` and get a cap-hit on iteration 1 with no validation, or
pass `cap >= max` and get silence; there is no guard. **Verdict on the devil's case:** every
one of these is real but none is a *correctness* defect or a hard-rule violation — they are
fidelity/coverage gaps and by-design diagnostic knobs. The double-serialization is bounded and
the byte metric is still accurate; the missing-summary-on-raise and curate contamination are
recorded Delivery Findings; the unwired cap/harness match the ACs' "as diagnosis warrants" /
offline-tool framing. The devil sharpened the findings; it did not find a reason to reject.

**Error handling:** `latency_percentiles([])` returns `0.0/0.0/count=0` (documented, with a
discriminator) — `latency_report.py:38`. The decompose success span is correctly NOT emitted on
the `IntentRouterFailure` raise path, so failure turns don't get phantom attribution
(`intent_router.py:400`). The cap/summary spans use `with ...: pass` zero-body context managers,
so OTEL exceptions propagate rather than corrupting turn outcome.

**Pattern observed:** new spans registered in `SPAN_ROUTES` beside their constants following the
established `intent_router.py` span-route pattern — `narrator.py:73-95`. Refactor-stable wiring.

**Handoff:** To SM (Camina Drummer) for finish-story. NOTE for finish: AC5's live-capture
diagnosis report is a blocking-for-DONE Delivery Finding (Dev-flagged) — the green/review phases
deliver the instrumentation; the report itself needs a live/recorded Glenross run before the
story is truly complete.