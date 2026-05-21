---
story_id: "24-7"
jira_key: "none"
epic: "24"
workflow: "tdd"
---
# Story 24-7: OTEL Spans for Weather Generation and Demographics Injection

## Story Details
- **ID:** 24-7
- **Epic:** 24 — Procedural World-Grounding Systems
- **Workflow:** tdd (phased: red → green → review → finish)
- **Repos:** sidequest-server
- **Points:** 2
- **Priority:** p1

## Context

This story adds OTEL observability to the procedural world-grounding system implemented in stories 24-5 (Python weather generator) and 24-6 (narrator grounding tool call).

**Dependencies (DONE):**
- **24-5:** Python weather generator in sidequest-server/sidequest/game/weather.py — generates typed WeatherState from climate YAML
- **24-6:** Narrator tool call for weather + demographics + calendar grounding — extends narrator tool registry per ADR-102/103

**Purpose:** Emit OTEL spans for:
1. **weather_generation_proposed** — what the weather generator produces (condition, temperature, wind, intensity, etc.)
2. **weather_generation_used** — what the narrator actually references in narration (if it uses the grounding tool)
3. **demographics_injection** — when demographics context is injected into the narrator prompt/tool response

These spans feed the GM panel (ADR-031, ADR-103) so story 24-8 (playtest validation) can verify the grounding system is engaged and the narrator is using the structured context.

**Architectural notes:**
- Per ADR-031 (Game Watcher — Semantic Telemetry for AI Agent Observability), every subsystem decision gets an OTEL event
- Per ADR-103 (Native OTEL via Tool Registry), OTEL spans are free in the tool-use flow — just add them to the tool definitions
- The spans must be **observable in the GM dashboard** — if they don't show up there, they're not useful

## Workflow Tracking
**Workflow:** tdd  
**Phase:** finish  
**Phase Started:** 2026-05-21T11:06:37Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-21T06:15:00Z | 2026-05-21T10:13:57Z | 3h 58m |
| red | 2026-05-21T10:13:57Z | 2026-05-21T10:27:24Z | 13m 27s |
| green | 2026-05-21T10:27:24Z | 2026-05-21T10:56:43Z | 29m 19s |
| spec-check | 2026-05-21T10:56:43Z | 2026-05-21T10:58:02Z | 1m 19s |
| verify | 2026-05-21T10:58:02Z | 2026-05-21T11:00:11Z | 2m 9s |
| review | 2026-05-21T11:00:11Z | 2026-05-21T11:05:37Z | 5m 26s |
| spec-reconcile | 2026-05-21T11:05:37Z | 2026-05-21T11:06:37Z | 1m |
| finish | 2026-05-21T11:06:37Z | - | - |

## SM Assessment

**Scope:** Add OTEL instrumentation to two existing, shipped subsystems — the Python weather generator (24-5) and the narrator grounding tool call (24-6). Three spans required: `weather_generation_proposed`, `weather_generation_used`, `demographics_injection`. Both subsystems landed APPROVED yesterday and are unmodified by this story's surface — this is pure instrumentation overlay, not behavioral change.

**Risk:** Low. ADR-103 (Native OTEL via Tool Registry) makes the `used` and `demographics` spans nearly free in the tool-use flow. The `proposed` span sits at the weather generator's typed-return boundary. No data-model changes, no protocol changes, no client surface.

**Lie-detector framing (per project OTEL doctrine):** The whole point of this story is that 24-8 (playtest validation) cannot trust the grounding system without these spans. The narrator can write convincing prose about morning fog over the moors with zero connection to the generated WeatherState — only the `_used` span proves engagement. Without it, 24-8 has no signal to grade against. TEA should drive tests off that lie-detector value, not off the spans' mere existence.

**TDD posture:** Tests assert spans fire with expected attributes when the subsystem runs, and crucially do NOT fire when not invoked (negative case matters for `_used` — if narrator skips the tool, no span). The mandatory wiring test (per CLAUDE.md) must show the span is reachable from a real game-loop entry point, not just unit-mocked.

**Hand-off to TEA (Radar):** Write the red-phase tests against the production code paths in `sidequest-server/sidequest/game/weather.py` and the narrator tool registry. Reference ADR-031 (game watcher emit-event helper) and ADR-103 (tool-registry-driven spans) — don't roll a parallel span emitter. Include at least one integration test proving the span surfaces where the GM dashboard reads it.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (18 failing assertions, 7 negative-case guards green)

**Test Files:**
- `sidequest-server/tests/telemetry/spans/test_world_grounding_spans.py` — span constants exist + canonical names; all three routed as `state_transition` under `component="world_grounding"` (never `FLAT_ONLY_SPANS`); emit helpers round-trip attributes; route-extractor fields surface `field/op/zone/season/condition/seed/world_id/total_population/recurring_cast_count` for the GM dashboard.
- `sidequest-server/tests/game/test_weather_proposed_span.py` — wires the proposed span into `WeatherGenerator.generate()` on the live OTEL tracer (the same singleton the dashboard reads). Includes the "one span per call, not per construction" gate and the negative case (failed `generate()` MUST NOT emit).
- `sidequest-server/tests/agents/tools/test_grounding_otel_used_injection.py` — wires used + injection spans into `get_world_grounding` reached via `default_registry.dispatch()` (production code path). Negative cases: section excluded from `include`, session unwired (`weather_state=None` / `world_demographics=None`), and `include=[]`. Regression gate: existing 24-6 `tool.grounding.<section>_present` attrs MUST still fire on the dispatch span; new spans MUST be **separate** spans, not attrs on the dispatch span (the dashboard's typed channel routes by span name).

**Tests Written:** 25 (18 affirmative RED + 7 negative-case guards already passing)

### Design Decisions Locked by Tests

1. **Three SPAN_* constants**, all routed as `state_transition` / `component="world_grounding"`:
   - `world_grounding.weather_proposed`
   - `world_grounding.weather_used`
   - `world_grounding.demographics_injected`
2. **Three emit helpers** exposed from `sidequest.telemetry.spans` package: `emit_weather_proposed_span(state)`, `emit_weather_used_span(zone, season, condition, seed, world_id, perspective_pc)`, `emit_demographics_injected_span(world_id, demographics, perspective_pc)`.
3. **Span emit sites:** `proposed` inside `WeatherGenerator.generate()` after `WeatherState` construction (not in `__init__`, not in the CLI). `used` + `injected` inside the `get_world_grounding` tool handler, after the inclusion + non-None gate.
4. **No-silent-fallbacks encoding:** Absent `special_event` → empty string `""`, NOT omitted attr. Absent `perspective_pc` → empty string `""`. Absent population/cast → `0`. The dashboard tests for presence vs zero — never absence — so the contract must be explicit.
5. **Effects encoding:** Helper picks `tuple[str, ...]` or comma-joined string; tests accept either. Dev's call.
6. **No regression:** existing 24-6 `tool.grounding.<section>_present` dispatch-span attrs are explicitly re-asserted.

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|---|---|---|
| #3 Type annotations at boundaries | All test fns annotated; `_ctx` builder uses kwargs-only typed signature | green (lint-level) |
| #4 Log level / no sensitive data | No logging in tests (irrelevant for these spans) | n/a |
| #6 Test quality — meaningful assertions | Every test asserts on a named attribute/field, no `assert True` / `assert result` truthy-only checks; negative cases assert `[] == []` not just `is_none()` | green (self-checked) |
| #7 Resource leaks | All fixtures use `with`/yield/teardown via existing `otel_capture` + `exporter` fixtures | green |
| #9 Async/await pitfalls | Async test fns marked `@pytest.mark.asyncio`; no blocking calls; tool dispatch awaited correctly | green |
| #10 Import hygiene | No star imports in new code; new SPAN_* imported by name from `sidequest.telemetry.spans` package facade | green |
| ADR-031 OTEL doctrine (project-specific) | `test_used_and_injected_spans_are_distinct_from_dispatch_span` explicitly forbids collapsing to dispatch-span attrs; `test_existing_tool_grounding_present_attrs_still_fire` is the regression gate | green (RED-pending impl) |
| CLAUDE.md "no silent fallbacks" | `special_event == ""` and `perspective_pc == ""` explicit empty-string contract tests | green (RED-pending impl) |
| CLAUDE.md "every test suite needs a wiring test" | Two wiring files (`test_weather_proposed_span.py`, `test_grounding_otel_used_injection.py`) exercise production code paths via `WeatherGenerator.generate()` and `default_registry.dispatch()` | green |

**Rules checked:** 9 of 12 applicable python.md rules (rules #1 exception swallowing, #5 path handling, #8 unsafe deserialization, #11 boundary input validation, #12 dependency hygiene have no test surface for pure-instrumentation work).

**Self-check:** 0 vacuous tests found. Every test asserts on a named attribute, span-name string, or list length with rationale.

### Open Question for Dev

The `effects` attribute is a `list[str]` on `WeatherState`. OTEL allows `Sequence[str]` natively, but the watcher translator in this repo has historically preferred scalar attrs (the `namegen` extractor reads scalars). Dev to pick: native tuple/list OR comma-joined string. Tests accept either — both effect ids must round-trip.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for GREEN. Implementation surface is tightly bounded:
1. New module `sidequest/telemetry/spans/world_grounding.py` with three SPAN_* constants, three `SPAN_ROUTES` entries (state_transition / component=world_grounding), and three `emit_*` helpers.
2. Import in `sidequest/telemetry/spans/__init__.py` (alphabetical position, after `weather_*` if any, before re-exports).
3. One-line emit in `sidequest/game/weather.py:WeatherGenerator.generate()` (after state construction, before return).
4. Two-line emit in `sidequest/agents/tools/get_world_grounding.py` (after computing `weather_present` / `demographics_present` + the `include` gate).

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 89/89 passing on touched surface (25 new + 64 regression). Full sidequest-server suite was kicked off in the background but the focused gate is sufficient — blast radius is the three touched files plus the routing-completeness lint.
**Lint:** ruff clean.
**Branch:** `feat/24-7-otel-weather-demographics` (pushed to origin).

**Files Changed:**
- `sidequest/telemetry/spans/world_grounding.py` (new) — three SPAN_* constants (`world_grounding.weather_proposed`, `world_grounding.weather_used`, `world_grounding.demographics_injected`), three `SPAN_ROUTES` entries (`event_type="state_transition"`, `component="world_grounding"`), three `emit_*` helpers using the standard `Span.open()` pattern.
- `sidequest/telemetry/spans/__init__.py` — `from .world_grounding import *` plus an explicit re-export of the three `emit_*` symbols.
- `sidequest/game/weather.py:WeatherGenerator.generate()` — emits `weather_proposed` after `WeatherState` construction, before the return. Failed `generate()` raises before the emit (negative case already green pre-implementation, still green now).
- `sidequest/agents/tools/get_world_grounding.py` — emits `weather_used` and `demographics_injected` after the existing `tool.grounding.*_present` dispatch-span attrs, gated on `section in args.include AND ctx.<field> is not None`. The pre-existing dispatch-span attrs are preserved verbatim (regression test green).

**Design choices locked in:**
1. **Effects encoding:** comma-joined string (e.g. `"impair_visibility,ground_travel_halved"`, `""` for empty). Picked over native list because the existing watcher translator pattern (`namegen.py`) reads scalar attrs, and `""` matches the no-silent-fallbacks empty-marker convention used everywhere else in the module. Tests accepted either form.
2. **Lazy imports inside generate() and the tool handler:** the new emit functions are imported at call-site rather than module-top to avoid circular-import risk between `sidequest.game.weather` ↔ `sidequest.telemetry.spans.world_grounding` (which TYPE_CHECKING-imports `WeatherState`). Cheap — Python module cache makes the lookup ~zero cost after the first call.
3. **`emit_demographics_injected_span` tolerates `parish: None` and `recurring_cast: None`** (encoding both as `0`), matching the test that exercises a minimal dict. Per CLAUDE.md, this is contract-driven explicit absence — NOT a silent fallback for a missing required field.

**Handoff:** To Reviewer (Colonel Potter) for code review.

## Delivery Findings

### TEA (test design)

- No upstream findings during test design.

### Dev (implementation)

- No upstream findings during implementation.

### Architect (spec-check)

- No upstream findings during spec-check.

### TEA (test verification)

- No upstream findings during test verification.

### Reviewer (review)

- **Improvement** (non-blocking, already fixed): ruff I001 import-sort violation in `tests/agents/tools/test_grounding_otel_used_injection.py`. Slipped past the GREEN-phase lint pass because the targeted lint command excluded the test tree. *Found by Reviewer; autofixed inline as a one-line `ruff --fix` rather than rejecting back to Dev — right-size ceremony for a mechanical autofix.*
- **Improvement** (non-blocking, already fixed): stale docstrings in `sidequest/game/weather.py` (called the OTEL spans "a future epic-24 deliverable") and `sidequest/agents/tools/get_world_grounding.py` (called them "the story-24-7 follow-up"). 24-7 IS that story. Updated both to point at the live span sites and the lie-detector framing. *Found by Reviewer; refreshed inline.*
- No further upstream findings.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (ruff I001 in test_grounding_otel_used_injection.py) | confirmed 1 — autofixed inline (`adeaabd`) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter` |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.test_analyzer` |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.comment_analyzer` — gap covered by Reviewer's manual doc audit (two stale docstrings caught and fixed: `775b957`) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design` |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security` — no auth/secret surface in this diff (pure observability instrumentation) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier` — gap covered by TEA verify simplify fan-out (reuse/quality/efficiency all returned clean) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.rule_checker` — gap covered by Reviewer's manual Rule Compliance below |

**All received:** Yes (1 returned with one finding, 8 disabled via project settings)
**Total findings:** 3 confirmed (all non-blocking and fixed inline: 1 preflight lint, 2 Reviewer-found stale docstrings), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

### Diff Summary
4 commits since `develop`:
- `5c2321a` test(24-7): RED — three test files (1010 lines)
- `0ca4cf1` feat(24-7): GREEN — three emit sites + new span module (221 lines)
- `adeaabd` chore(24-7): ruff I001 autofix in test file (1 line)
- `775b957` docs(24-7): refresh stale docstrings (16 insertions / 10 deletions)

Net: ~1234 insertions, pure additive instrumentation. No protocol/wire/data-model changes. Tests outnumber implementation 4-to-1 — appropriate for a story whose entire deliverable is observability fidelity.

### Adversarial Findings

- **[VERIFIED] Span fires unconditionally from generate(), not from CLI entry only** — `sidequest/game/weather.py:309-313` calls `emit_weather_proposed_span(state)` immediately after `WeatherState` construction. Every consumer (CLI weathergen, future session bootstrap, future regen-on-day-roll) reaches the emit. Rule check (CLAUDE.md OTEL Observability Principle): emit on every subsystem decision — compliant.
- **[VERIFIED] Failed generate() does not emit** — `weather.py:245-256` raises `UnknownWeatherZone` / `UnknownWeatherSeason` before reaching the `state = WeatherState(...)` line and the subsequent emit. Negative test `test_generate_raises_does_not_emit_proposed_span` proves this. No false-positive proposals on the dashboard.
- **[VERIFIED] Conditional emits are correctly two-clause** — `get_world_grounding.py:124-146` gates each emit on `section in args.include AND ctx.<field> is not None`. The four-cell truth table (requested×wired) is covered: tests `test_weather_used_span_fires_when_weather_requested_and_wired` (1,1), `test_weather_used_span_does_not_fire_when_section_excluded` (0,1), `test_weather_used_span_does_not_fire_when_session_unwired` (1,0), `test_weather_used_span_does_not_fire_on_empty_include` (0,*). Symmetric coverage for demographics.
- **[VERIFIED] No-silent-fallbacks contract enforced in emitters** — `world_grounding.py:111` `state.special_event or ""`, `:139` `perspective_pc or ""`, `:171` `int(parish.get("total_population", 0) or 0)`, `:172` `len(cast)` over default `[]`. Every absent field has an explicit `0` or `""` encoding, not omission. Rule check (CLAUDE.md "No Silent Fallbacks"): compliant — absence is a first-class signal, not a hidden state.
- **[VERIFIED] No regression on 24-6 dispatch-span attrs** — `get_world_grounding.py:117-121` (`tool.grounding.*_present`) is preserved verbatim. Test `test_existing_tool_grounding_present_attrs_still_fire_on_dispatch_span` is the explicit regression gate. Distinct-spans guarantee (`test_used_and_injected_spans_are_distinct_from_dispatch_span`) enforces the spans live in their own state_transition channel, not as attrs on the dispatch span.
- **[VERIFIED] Routing-completeness lint covers new constants** — three new `SPAN_WORLD_GROUNDING_*` constants registered in `SPAN_ROUTES` at `world_grounding.py:54,71,86`, none in `FLAT_ONLY_SPANS`. Existing `tests/telemetry/test_routing_completeness.py` re-runs against the now-augmented `spans` package — green per testing-runner output.
- **[VERIFIED] Lazy imports inside hot paths are intentional and cheap** — `weather.py:311` and `get_world_grounding.py:128,140` import the emit helpers at call site to defuse a `sidequest.game.weather` ↔ `sidequest.telemetry.spans.world_grounding` (TYPE_CHECKING-only) circular-import risk. Python's module cache makes the cost effectively zero after first call. Acceptable.
- **[LOW] Effects encoding is a comma-joined string, not a list** — `world_grounding.py:114` `",".join(state.effects)`. An effect ID containing a literal comma (effect IDs are conventionally `snake_case`, so this is theoretical) would render ambiguously on the dashboard. Not a real-world concern given existing pack-author conventions. Acceptable.
- **[VERIFIED] `world_id` source-of-truth is `ctx.world_id`, not `demographics["world"]`** — `get_world_grounding.py:143` uses `ctx.world_id` for the demographics emit. ctx is session-authoritative; the demographics dict's own `world` field could be stale/cached/wrong-file. Correct choice.

### Rule Compliance (manual exhaustive pass, gap-fills disabled rule-checker subagent)

| Rule (CLAUDE.md / SOUL.md / python.md) | Applied to | Status |
|---|---|---|
| **No Silent Fallbacks** | All three emit helpers + tool-handler gates | ✓ Compliant — every absent field encodes explicitly (`""`/`0`), gates are explicit two-clause checks |
| **No Stubbing** | New `world_grounding.py` module | ✓ Compliant — three fully wired emit helpers + three route entries, zero placeholders |
| **Don't Reinvent — Wire Up What Exists** | OTEL infrastructure | ✓ Compliant — reuses `Span.open`, `SPAN_ROUTES`/`SpanRoute`, the existing `state_transition` event_type; no parallel span emitter |
| **Every Test Suite Needs a Wiring Test** | Three new test files | ✓ Compliant — `test_weather_proposed_span.py` exercises live `WeatherGenerator.generate()` on the singleton tracer; `test_grounding_otel_used_injection.py` exercises `default_registry.dispatch()` (production path) |
| **OTEL Observability Principle** | Every subsystem decision gets a span | ✓ Compliant — three lie-detector spans, all routed to GM dashboard, all carrying join keys |
| python.md #3 Type annotations at boundaries | `emit_*` signatures, route extractors | ✓ Compliant — keyword-only params with explicit types; route extractors use `_SpanLike` Protocol |
| python.md #6 Test quality | All 25 new tests | ✓ Compliant — every test asserts on a named attr / span name / span count; negative cases assert `[] == []` not just `is_none()` |
| python.md #7 Resource leaks | Span emitters | ✓ Compliant — `Span.open` is a context manager; all three emits use `with` correctly |
| python.md #9 Async pitfalls | Tool-handler emits inside async fn | ✓ Compliant — `Span.open` is synchronous and non-blocking; no `time.sleep`, no blocking I/O, no missing await |
| python.md #10 Import hygiene | `__init__.py` and lazy emits | ✓ Compliant — star imports are pre-existing pattern (registry-insertion order); lazy imports inside emit sites are intentional anti-cycle defense |
| python.md #11 Input validation | Demographics dict parsing | ✓ Compliant — `parish.get(..., 0) or 0` handles missing/None/0; `recurring_cast or []` handles missing/None |
| python.md #13 Fix-introduced regressions | Reviewer-applied lint + doc fixes | ✓ Verified — autofix + docstring edits both followed by re-run of lint + targeted tests (76 passed) |
| ADR-031 (Game Watcher semantic telemetry) | All three spans | ✓ Compliant — uses `Span.open` helper, attrs land on routed spans |
| ADR-102 (Tool-use protocol) | Tool-handler emit gates | ✓ Compliant — no change to tool dispatch contract; new emits are post-payload-build, pre-return |
| ADR-103 (Native OTEL via tool registry) | `weather_used` + `demographics_injected` | ✓ Compliant — the spans are nested under the existing tool dispatch span via natural OTEL parent-child |

### Devil's Advocate

Argue the code is broken — what would go wrong in production?

- **Span flood under heavy load:** `WeatherGenerator.generate()` is called once per scene-roll, not per turn. Even an aggressive playtest produces ~20 calls per session. OTEL backpressure is not a concern at this volume. If a future epic moves weather generation into a per-turn re-roll, the emit becomes per-turn — still fine for the in-memory exporter; would matter if we ship to an OTLP backend, but ADR-095 doesn't yet wire a production OTLP collector. **Acceptable.**
- **Misleading "used" signal when the narrator IGNORES the returned data:** The `weather_used` span fires when the tool *returns* weather to the narrator. The narrator could read the tool result and then write prose that contradicts it. The dashboard would record "weather_used" while the prose says sunny in a blizzard. **This is a known limitation of the lie-detector framing** — the only fix is downstream content-grading (a future story). 24-7's lie-detector catches "narrator wrote weather but never called the tool", which is the dominant failure mode. **Acceptable, with documented limit.**
- **Demographics injection signal when the data is empty/zero:** If a YAML has `parish: null` and `recurring_cast: null`, the span fires with `total_population=0`, `recurring_cast_count=0`. A reader could mistake "data wired but empty" for "data not wired". *But* the documented contract is that the span's *presence* means wired and the *counts* are informational — exactly what the helper's docstring states. Tests cover the minimal-dict case. **Acceptable.**
- **A future contributor adds a fourth section (e.g. `calendar`) to the tool and forgets to add a `calendar_injected` span:** There's no test or lint that catches the gap. The four section names live in three places: `_GroundingSection` Literal, the payload-build conditionals, and the emit-gate conditionals. Adding a section means updating all three. This is a minor maintenance hazard, not a 24-7 bug. **Acceptable; flag as future-epic concern.**
- **Race condition on dict mutation during emit:** `emit_demographics_injected_span` reads `parish` and `recurring_cast` non-atomically. In a hostile concurrent edit (which doesn't happen in this codebase — demographics is loaded once at session bootstrap), this could tear. Python GIL plus the fact that the dict is treated as immutable session config makes this impossible in practice. **Acceptable.**
- **Stale-comment recurrence:** The two docstrings I just fixed had been stale for ~2 hours (since Dev's GREEN landed). There's no automated check for "docstring references a story that has now shipped." This is a class of bug that recurs — would be worth a future tech-writer story. **Acceptable for 24-7; logged for future.**

No new findings from devil's advocate.

### Decisions

- Spec drift (Architect-flagged trivial naming evolution `weather_generation_*` → `world_grounding.weather_*`) — **✓ ACCEPTED**: the implemented names match the codebase convention and produce a coherent `component="world_grounding"` route group for the GM dashboard.
- Reviewer-applied trivial fixes (lint autofix + 2 stale docstrings) — **✓ ACCEPTED inline**: right-size ceremony for mechanical fixes that don't touch behavior.

**Verdict:** APPROVED

**Data flow traced:** `WeatherGenerator.generate(zone, season, seed)` → `WeatherState` constructed (`weather.py:296-305`) → `emit_weather_proposed_span(state)` fires on the live tracer (`weather.py:313`) → OTEL collector records `world_grounding.weather_proposed` with full state attrs → GM dashboard reads via `SPAN_ROUTES["world_grounding.weather_proposed"].extract()`. Separately, narrator tool call → `get_world_grounding` handler → conditional `emit_weather_used_span` (`get_world_grounding.py:128-136`) → same OTEL channel → dashboard joins proposed↔used on `seed`.

**Pattern observed:** Follows the established `clock.advance` / `namegen.*` / `location.*` emit pattern at `world_grounding.py:54-97` exactly — no new conventions introduced, full alignment with codebase telemetry style.

**Error handling:** Span emit is fire-and-forget by design (OTEL no-op tracer when unconfigured); failed `WeatherGenerator.generate()` raises before emit; tool handler errors are caught at the dispatch level. All boundary conditions tested with negative assertions.

**Handoff:** To SM (Hawkeye) for finish-story.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (89/89 on touched surface; lint clean)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7 (4 source + 3 test files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 — three emit helpers have legitimately distinct signatures; no duplicated logic to extract |
| simplify-quality | clean | 0 — strong convention adherence (ADR-102/103, CLAUDE.md no-silent-fallbacks, wiring tests present) |
| simplify-efficiency | clean | 0 high/medium; 1 low-confidence note re. explicit re-exports in `__init__.py` lines 97-101 being redundant with the preceding star-import, deemed intentional for documentation clarity |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 1 low-confidence (intentional explicit re-export for IDE/doc clarity — leave as-is)
**Reverted:** 0

**Overall:** simplify: clean

### Regression Detection

`pf check` from orchestrator root: lint PASS (server lint already validated during GREEN). Server pytest scan (89/89 GREEN on touched surface incl. routing-completeness, weather generator, grounding tool, span catalog) re-confirmed during the GREEN→spec-check transition. No new code added during verify; no regression risk introduced.

**Quality Checks:** All passing
**Handoff:** To Reviewer (Colonel Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with one cosmetic naming evolution worth logging)
**Mismatches Found:** 1 — trivial

### Mismatch: span-name prefix evolved during implementation (Cosmetic — Trivial)

- **Spec:** session file states the three spans as `weather_generation_proposed`, `weather_generation_used`, `demographics_injection`.
- **Code:** Dev implemented them as `world_grounding.weather_proposed`, `world_grounding.weather_used`, `world_grounding.demographics_injected`.
- **Recommendation:** A — update spec to match code. The implemented names follow the established subsystem-prefixed convention used everywhere else in `sidequest/telemetry/spans/` (`clock.advance`, `namegen.thin_corpus`, `location.entity.resolve`, `rig.pool_delta` etc.) and explicitly group the three spans under a single `component="world_grounding"` route — exactly what the GM dashboard needs to render a coherent "world grounding" tab. Reverting to the spec's flat prefix would create an inconsistency and lose the routing group. Logged as a Dev-noted naming evolution; no rework required.

### AC Coverage Verification

| AC (paraphrased from session) | Implementation | Status |
|---|---|---|
| Emit OTEL span when weather generator produces a WeatherState | `WeatherGenerator.generate()` → `emit_weather_proposed_span(state)` with full state attrs (zone/season/condition/temp/precip/special_event/effects/seed) | ✓ Covered; one span per `generate()` call; failed calls do not emit |
| Emit OTEL span when narrator actually references weather grounding | `get_world_grounding` tool → `emit_weather_used_span` gated on `"weather" in args.include AND ctx.weather_state is not None` | ✓ Covered; negative cases (section excluded / session unwired / empty include) tested and green |
| Emit OTEL span when demographics is injected into narrator context | `get_world_grounding` tool → `emit_demographics_injected_span` gated on `"demographics" in args.include AND ctx.world_demographics is not None` | ✓ Covered; carries world_id + total_population + recurring_cast_count |
| Spans observable in the GM dashboard | All three routed as `event_type="state_transition"` under `component="world_grounding"` in SPAN_ROUTES; routing-completeness lint passes; not in FLAT_ONLY_SPANS | ✓ Covered |
| Lie-detector framing (proposed vs used diff) | `weather_proposed` and `weather_used` carry the shared `seed` join key plus zone/season/condition for single-row rendering | ✓ Covered |
| No regression on existing 24-6 dispatch-span attrs | `tool.grounding.<section>_present` attrs preserved verbatim; explicit regression test green | ✓ Covered |

### Architectural Notes

- **ADR alignment:** Implementation follows ADR-031 (game watcher semantic telemetry) emit-event helper pattern via `Span.open()` and ADR-103 (native OTEL via tool registry) for the tool-side spans. No new ADR required — this is a faithful extension of established patterns. ADR-088 (frontmatter schema for ADRs) not invoked since no ADR change.
- **No new public surface:** the three `emit_*` helpers are package-internal to `sidequest.telemetry.spans`; the `ToolContext` schema is unchanged (24-7 reuses the 24-6 fields wholesale); no protocol/wire changes.
- **Forward impact for 24-8 (playtest validation):** the GM panel can now render proposed-vs-used coverage histograms and detect zero-`weather_used` turns where the narrator's prose talks about weather. 24-8 should script a scene that calls grounding once and a scene that does not, and assert the dashboard's counts match. Recommend adding that explicit acceptance to 24-8 when SM picks it up.
- **`heavy_metal` / `low_fantasy` packs lack `weather.yaml`:** that is fine — the proposed span only fires when `WeatherGenerator.generate()` runs, and absent climate config simply means no span. The dashboard will read "0 proposals" for those packs, which is the truthful signal.

**Decision:** Proceed to TEA verify. Spec drift is cosmetic naming only; the implementation matches both the intent and the codebase convention better than the original spec wording did.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### TEA (test verification)
- No deviations from spec.

### Architect (spec-check)
- **Span names use subsystem-prefixed dotted form** → ✓ ACCEPTED by Reviewer: agrees with author reasoning; the dotted form is the codebase convention and produces a coherent dashboard route group.
  - Spec source: `.session/24-7-session.md` (session context block, line 26-28)
  - Spec text: "weather_generation_proposed", "weather_generation_used", "demographics_injection"
  - Implementation: `world_grounding.weather_proposed`, `world_grounding.weather_used`, `world_grounding.demographics_injected`
  - Rationale: Matches the established convention across `sidequest/telemetry/spans/` (`clock.*`, `namegen.*`, `location.*`, `rig.*` etc.) and creates a coherent `component="world_grounding"` route group for the GM dashboard's tabbed view. Spec wording predated the SPAN_ROUTES component-grouping pattern.
  - Severity: trivial
  - Forward impact: none — sibling story 24-8 reads spans by component, not by literal name; dashboard tab gains a cleanly-grouped surface.

### Reviewer (audit)
- No undocumented deviations. TEA + Architect captured everything; Reviewer-applied changes (ruff autofix + 2 stale-docstring refreshes) are mechanical, non-behavioral, and noted in Delivery Findings.

### Architect (reconcile)
- **Audit of existing entries:**
  - TEA (test design): "No deviations from spec." ✓ Verified accurate — RED test files map 1:1 to the three spans named in the session context block; no scope cuts, no test omissions.
  - Dev (implementation): "No deviations from spec." ✓ Verified accurate — implementation hit every TEA-locked decision (three constants, three emit helpers, three emit sites, no-silent-fallbacks encoding, no regression on 24-6 dispatch-span attrs).
  - TEA (test verification): "No deviations from spec." ✓ Verified accurate — simplify fan-out returned `clean` on all three lenses; no rework applied; no spec evolution.
  - Architect (spec-check): "Span names use subsystem-prefixed dotted form" — entry has all 6 fields, accurately quotes the session-block spec text, accurately describes the implemented names, rationale is sound (matches codebase convention), severity (trivial) and forward impact (none) are correct. ✓ Verified.
  - Reviewer (audit): "No undocumented deviations" plus three inline mechanical fixes (ruff I001, two stale docstrings) noted in Delivery Findings. ✓ Verified — the three Reviewer-applied edits are non-behavioral and properly documented; they do not constitute spec deviations (they correct stale documentation and lint noise, both pre-existing micro-issues that surfaced during the review pass).

- **Additional deviations found:** None.

  Story 24-7 was a tightly-scoped instrumentation story with a sharp blast radius (3 emit sites, 1 new module, 0 protocol changes, 0 data-model changes). The single naming evolution (component-prefixed span names) was caught at spec-check and approved by Reviewer; no other drift surfaced through five gate passes.

- **AC deferral verification:** No ACs were deferred. Every signal point named in the session-block ACs (proposed, used, injection, dashboard observability, no-regression on 24-6) shipped with both production wiring and a test. Nothing remains for a follow-up story.

- **Forward impact for sibling 24-8 (playtest validation):** The three spans are routed to `state_transition` / `component="world_grounding"` and will appear on the GM dashboard. 24-8 should script (a) a turn where the narrator calls `get_world_grounding` with `include=["weather"]` and (b) a turn where it does not, then assert the proposed-vs-used coverage diff on the dashboard reflects exactly those two cases. Recommend the SM hand 24-8 to TEA with this explicit AC.
<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->