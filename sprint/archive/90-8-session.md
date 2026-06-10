---
story_id: "90-8"
jira_key: ""
epic: "90"
workflow: "tdd"
---
# Story 90-8: Route hydration lie-detectors (wwn.magic_hydrated + magic.state_hydrated) into the typed GM-panel Subsystems feed — 90-7 fast-follow #1 (design-bearing)

## Story Details
- **ID:** 90-8
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none
- **Type:** chore
- **Points:** 3
- **Priority:** p3

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T18:26:18Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T18:03:15Z | 2026-06-10T18:05:07Z | 1m 52s |
| red | 2026-06-10T18:05:07Z | 2026-06-10T18:15:36Z | 10m 29s |
| green | 2026-06-10T18:15:36Z | 2026-06-10T18:20:19Z | 4m 43s |
| review | 2026-06-10T18:20:19Z | 2026-06-10T18:26:18Z | 5m 59s |
| finish | 2026-06-10T18:26:18Z | - | - |

## Story Context

### Problem
After story 90-7 (WWN scene-harness hydrator), two lie-detector OTEL events are emitted (wwn.magic_hydrated and magic.state_hydrated) but they don't appear in the typed GM-panel Subsystems feed. They reach only the dashboard RAW console because:

1. Event types are not in the UI WatcherEventType union (sidequest-ui/src/types/watcher.ts)
2. They are not in SPAN_ROUTES (sidequest-server/sidequest/telemetry/spans/)
3. As a result, they don't appear in the Subsystems tab like other subsystem events (wwn.spell.cast, wwn.effort.commit, etc.)

### Decision Required
Two viable paths exist:

**Path 1: Re-emit as routed OTEL spans**
- Use Span.open + SpanRoute with event_type=state_transition, component=magic
- Mirrors the pattern used by wwn.py helpers
- No UI changes required
- Changes 90-7's emit mechanism and test contract (tests monkeypatch _hub.publish_event)

**Path 2: Add literal event_types to the UI union**
- Add wwn.magic_hydrated and magic.state_hydrated to the WatcherEventType union
- Add them to SPAN_ROUTES
- Simpler, more direct routing

**Requirement:** Apply the chosen pattern to BOTH sibling events (wwn.magic_hydrated and magic.state_hydrated) consistently.

### References
- 90-7 Reviewer delivery finding
- scene_harness.py:371-390 (current emit location in sidequest-server)
- ADR-031 (Game Watcher — Semantic Telemetry for AI Agent Observability)
- ADR-132 (WatcherHub Infrastructure)

## Repos
- sidequest-server

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (non-blocking): TEA pinned the story's open DECISION to Path 1 (routed OTEL spans) rather than Path 2 (UI union + SPAN_ROUTES literals); if Dev or Reviewer believes this needed an Architect ruling, the RED suite is the artifact to challenge. Affects `sidequest-server/sidequest/telemetry/spans/` (new constants + helpers) and `sidequest-server/sidequest/game/scene_harness.py` (emit-mechanism swap). *Found by TEA during test design.*
- **Improvement** (non-blocking): raw `watcher_hub.publish_event` string event_types have no completeness lint — the exact mechanism that let 90-7's events miss the typed feed; a future lint pass over publish_event call sites would catch the next one. Affects `sidequest-server/sidequest/telemetry/watcher_hub.py` (no change this story; candidate follow-up). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): the `**attrs` passthrough on `wwn_magic_hydrated_span` can clobber the reserved `effort_sources_json` attribute (dict-literal merge order), turning the extract into a loud validation_warning; a `attrs.pop("effort_sources_json", None)` guard or a docstring reservation note would close it. Affects `sidequest-server/sidequest/telemetry/spans/wwn.py` (helper attribute merge). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): no test drives the full `WatcherSpanProcessor.on_end` path for the two new span names (current tests assert through `SPAN_ROUTES[...].extract` directly); the processor is generic and covered for sibling routes, but the 90-3 live free-play OTEL proof should confirm these events land in the typed feed end-to-end. Affects `sidequest-server/tests/integration/` (candidate watcher_setup-style test). *Found by Reviewer during code review.*

## Impact Summary

**Findings:** 3 non-blocking improvements logged (all addressed in implementation or deferred):
1. **Lint gap on raw `publish_event` calls** (TEA, non-blocking) — watcher_hub.publish_event string event_types lack completeness lint; this is how 90-7's events escaped the typed feed. Candidate for future lint pass, not this story.
2. **`**attrs` can clobber reserved `effort_sources_json` key** (Reviewer, non-blocking, CONFIRMED LOW) — helper attribute merge in wwn.py. Failure mode is loud (validation_warning); no production caller passes attrs; documented as improvement for follow-up.
3. **No full-processor test for new span names** (Reviewer, non-blocking) — tests assert through route extract directly; processor is generic over SPAN_ROUTES and covered by sibling routes; 90-3 live-proof can close incidentally.

**Blockers:** None. All findings non-blocking; Reviewer assessment APPROVED.

**Deviations Accepted:** 2 minor (effort_sources type boundary relaxed; span helpers split across wwn.py + magic.py per namespace placement convention). Both documented in Design Deviations section; both accepted by Reviewer.

**Working Tree:** Clean (server: 0 uncommitted; tests 163/163 green serially).

**Wiring Verified:** Production emit sites at scene_harness.py:388/669; span constants + routes registered at import; WatcherSpanProcessor registered at app.py:202; Subsystems tab already renders state_transition/magic events (test confirms known_event_types).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **effort_sources boundary type relaxed from strict list to JSON-array (list/tuple)**
  - Spec source: 90-7's prior AC-6 test contract (tests/game/test_scene_harness_hydrator.py, pre-90-8)
  - Spec text: `assert fields["effort_sources"] == []` (strict list equality on the publish_event payload)
  - Implementation: rewritten tests assert `not isinstance(sources, str)` + `list(sources) == [...]`, accepting list OR tuple from the SPAN_ROUTES extract
  - Rationale: OTEL span attributes return homogeneous sequences as tuples; pinning strict list would force a JSON-encode implementation when either encoding (JSON string per magic.py convention, or str-sequence attribute) yields a correct JSON array at the dashboard boundary — the contract that matters
  - Severity: minor
  - Forward impact: Dev may choose either attribute encoding; the extract must hand back a real array either way
- No other deviations from spec.

### Dev (implementation)
- **Module placement: span siblings split across wwn.py and magic.py rather than co-located**
  - Spec source: context-story-90-8.md, Technical Approach (Path 1)
  - Spec text: "re-emit as a routed OTEL span ... mirrors wwn.py helpers"
  - Implementation: `wwn.magic_hydrated` lives in `telemetry/spans/wwn.py`, `magic.state_hydrated` in `telemetry/spans/magic.py` — each beside its namespace family, both routed identically (state_transition/magic)
  - Rationale: TEA's tests import from the `sidequest.telemetry.spans` package namespace and left placement to Dev; per-namespace modules match the catalog's domain-submodule registration convention (`_core.py` docstring)
  - Severity: minor
  - Forward impact: none — package star-exports surface both; the routing pattern is identical for both siblings as the story requires
- No other deviations from spec.

### Reviewer (audit)
- **TEA: effort_sources boundary type relaxed from strict list to JSON-array (list/tuple)** → ✓ ACCEPTED by Reviewer: agrees with author reasoning — the dashboard-boundary contract (real JSON array) is what matters; Dev's JSON-encode implementation in fact yields a strict list, so the relaxation cost nothing.
- **Dev: module placement split across wwn.py and magic.py** → ✓ ACCEPTED by Reviewer: per-namespace placement matches the `_core.py` registration convention ("each domain submodule registers its routed spans near the constant declaration"); both routes verified identical (state_transition/magic).
- No undocumented deviations found: diff-vs-spec sweep covered the emit-condition semantics (unchanged per story scope), payload fields (field-identical to 90-7), and both-siblings requirement (verified in both modules).

## Sm Assessment

Setup complete and verified. Story 90-8 (3pt, p3, tdd, server-only) claimed in sprint/epic-90.yaml; session file and standalone story context (sprint/context/context-story-90-8.md) both exist; feature branch `feat/90-8-hydration-lie-detectors-gm-feed` created in sidequest-server off develop. Jira explicitly skipped — story has no jira_key in YAML.

**Routing rationale:** TDD workflow → red phase → TEA. This story is design-bearing: the YAML poses an explicit DECISION (re-emit hydration lie-detectors as routed OTEL spans mirroring the wwn.py helpers vs adding literal event_types to the UI WatcherEventType union). The story context captures both paths and their test-contract implications (routed-span path changes 90-7's emit mechanism, whose tests monkeypatch _hub.publish_event). TEA should weigh in on the test contract for the chosen path; if the design call needs an Architect, TEA can flag it as a delivery finding. Whichever pattern wins must be applied to BOTH siblings (wwn.magic_hydrated and magic.state_hydrated).

**Risks noted for downstream agents:** (1) Repos field is server-only per YAML — if the UI-union path is chosen, scope expands to sidequest-ui and the session Repos field must be updated; (2) the OTEL span-count tests deadlock under parallel xdist — run affected files serially with -n0.

## TEA Assessment

**Tests Required:** Yes
**Design decision (the story's explicit "DECISION NEEDED"):** Path 1 — re-emit both hydration lie-detectors as ROUTED OTEL SPANS (`Span.open` + `SPAN_ROUTES` entry, `event_type=state_transition`, `component=magic`), retiring the raw `watcher_hub.publish_event` calls. Rationale: (a) story repos = server-only; Path 2 requires sidequest-ui changes; (b) `telemetry/spans/magic.py`'s docstring documents this exact route as how magic events reach the GM panel "without needing a new UI tab"; (c) `tests/telemetry/test_routing_completeness.py` lints SPAN_* constants at import time — raw publish_event strings get no such lint, which is precisely how the 90-7 gap shipped. Applied to BOTH siblings per the story requirement.

**Test Files:**
- `sidequest-server/tests/telemetry/test_hydration_lie_detector_spans_90_8.py` (NEW) — contract suite: span constants hold the literal 90-7 event names; both names registered in SPAN_ROUTES as state_transition/magic; helper emitters (`wwn_magic_hydrated_span`, `magic_state_hydrated_span`, keyword-only with `_tracer` override per wwn.py convention) round-trip the full 90-7 payload through the route extract; empty `effort_sources` survives the OTEL attribute boundary as a real array; extracts default safely on a bare span; helpers never call publish_event (no double emit).
- `sidequest-server/tests/game/test_scene_harness_hydrator.py` (REWRITTEN, AC-6 section) — the four 90-7 wiring tests migrate from publish_event capture to span capture via monkeypatched `spans.tracer` (the Span.open-documented seam) + assertion through `SPAN_ROUTES[...].extract` (the production typed-feed translation); positive cases also assert the raw emit is retired; the non-caster no-noise guard now checks both channels.
- `sidequest-server/tests/server/test_scene_harness.py` (REWRITTEN, one test) — the 50-22 `magic.state_hydrated` wiring test re-pinned to the same routed-span contract through the dev-scene HTTP endpoint (TestClient → hydrate → span → extract), with the raw-emit negative.

**Tests Written:** 8 new + 5 rewritten, covering: routing registration (the story's core AC), payload fidelity for both siblings, emit-mechanism swap at both scene_harness call sites, no-noise guard, no-double-emit, boundary-type safety.
**Status:** RED verified by testing-runner (run 90-8-tea-red): 4 failures exactly matching the intended RED set — 1 collection ImportError (new contract file; constants/helpers don't exist), 3 span-capture assertion failures (hydrator still raw-publishes). 148 surrounding tests pass — zero collateral damage. The non-caster guard passes by construction (asserts absence) — acceptable; its publish_event half would catch a regression.

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | extract-defaults-on-bare-span tests (extracts must not KeyError/except-pass their way to empty payloads) | failing (import) |
| #3 boundary type annotations | helper signature pinned keyword-only with typed payload via round-trip tests | failing (import) |
| #4 logging/telemetry correctness | no-double-emit test + raw-emit-retired negatives (event fires once, on the right channel) | failing |
| #6 test quality (no vacuous asserts) | self-checked: every test asserts field-level values with diagnostic messages; no `assert True` / bare truthy; the one absence-assert (non-caster) is the AC's explicit no-noise requirement | n/a |
| CLAUDE.md OTEL principle | all wiring tests assert through SPAN_ROUTES extract — the GM-panel lie-detector path itself | failing |
| CLAUDE.md wiring-test rule | hydrator + HTTP-endpoint tests exercise production call sites, not just the helpers | failing |

**Rules checked:** 5 of 6 applicable lang-review rules have test coverage (#2 mutable defaults and #5 path handling don't apply to a telemetry-emit story; hydrator path-handling already covered by 50-18 suite).
**Self-check:** 0 vacuous tests found.

**Notes for Dev (Julia):**
- New constants/helpers likely live in `telemetry/spans/wwn.py` (wwn.magic_hydrated) and `telemetry/spans/magic.py` (magic.state_hydrated) — but tests import from the `sidequest.telemetry.spans` package namespace, so module placement is your call (star-exports must surface them).
- `effort_sources` attribute encoding is your choice: JSON-encode per magic.py's structured-payload convention or a homogeneous str-sequence attribute — the extract just has to hand back a real array (tuple ok), including empty.
- `scene_harness.py` swap sites: ~line 388 (`wwn.magic_hydrated`) and ~line 672 (`magic.state_hydrated`). Delete the publish_event calls — the negatives enforce no double emit.
- Run the three affected files serially (`-n0`) — known OTEL xdist deadlock.
- `tests/telemetry/test_routing_completeness.py` will auto-cover the new SPAN_* constants; if you intentionally leave one unrouted it must go in FLAT_ONLY_SPANS (don't — routing is the story).

**Handoff:** To Dev for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/telemetry/spans/wwn.py` — `SPAN_WWN_MAGIC_HYDRATED` constant + `SPAN_ROUTES` registration (state_transition/magic) + `wwn_magic_hydrated_span` emitter; `effort_sources` JSON-encoded (`effort_sources_json` attribute, decoded in the extract) per the magic.py structured-payload convention so the empty list survives the OTEL attribute boundary.
- `sidequest-server/sidequest/telemetry/spans/magic.py` — `SPAN_MAGIC_STATE_HYDRATED` constant + route (state_transition/magic, `field=magic_state` / `op=state_hydrated` per the module's house style) + `magic_state_hydrated_span` emitter.
- `sidequest-server/sidequest/game/scene_harness.py` — both raw `_hub.publish_event` emits swapped for the span helpers; the now-unused `watcher_hub as _hub` import replaced by the helper imports. Emit conditions unchanged (non-casters stay silent).

**Tests:** 163/163 passing across the four affected files (GREEN — testing-runner run 90-8-dev-green, serial `-n0`): contract suite 9/9, hydrator 128/128, server scene-harness 24/24, routing-completeness lint 2/2 (accepts the new constants). Ruff clean on all changed files.
**Branch:** feat/90-8-hydration-lie-detectors-gm-feed (pushed, commits eff6ee07 test + 94661213 feat)

**Wiring note (CLAUDE.md "Verify Wiring"):** production consumers are the two scene_harness call sites (non-test), translated by the existing WatcherSpanProcessor → SPAN_ROUTES path the Subsystems tab already renders for wwn.spell.cast / magic.working — no UI change needed, which was the point of Path 1.

**Handoff:** To TEA for verify (simplify + quality-pass).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 (pre-existing lint in unrelated file) | dismissed 1 |
| 2 | reviewer-edge-hunter | Yes | findings | 8 | confirmed 1 (as LOW), dismissed 7 |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 3 (all low confidence) | confirmed 1 (as LOW, same as edge #2), dismissed 2 |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (3 enabled returned; 6 disabled via workflow.reviewer_subagents)
**Total findings:** 1 confirmed (LOW, non-blocking), 10 dismissed (with rationale), 0 deferred

### Finding Decisions (rationale per dismissal)

- **[EDGE] confirmed LOW — `**attrs` can clobber `effort_sources_json`** (wwn.py helper): a caller passing `effort_sources_json=...` via `**attrs` overrides the canonical `_json.dumps` encoding (dict-literal ordering: `**attrs` merges last). Worst case is LOUD, not silent — the extract raises and `WatcherSpanProcessor.on_end` catches it (`server/watcher.py:107-126`: `logger.exception` + `validation_warning` severity=error on the bus). No production caller passes attrs; pattern matches every other helper in the module. Non-blocking; improvement candidate.
- Dismissed [EDGE] "json.loads(None) TypeError crashes processor": the processor wraps `route.extract` in `try/except Exception` and publishes a `validation_warning` (`server/watcher.py:106-126`) — nothing crashes; additionally the OTEL SDK drops None attribute values, so `.get(..., "[]")` returns the default.
- Dismissed [EDGE] "malformed JSON silences telemetry": same line evidence — extract failures are surfaced loudly per the processor's explicit CLAUDE.md no-silent-fallbacks comment. The premise (silent drop) is false.
- Dismissed [EDGE] "valid JSON non-list payload": reachable only via the deliberate clobber above; same loud-failure ceiling; theoretical.
- Dismissed [EDGE] "empty effort dict {} emits no span": behavior identical to the 90-7 contract this story explicitly preserves (emit condition unchanged in the diff); an empty effort block seeds zero pools, so there is no staged crunch for the lie-detector to attest. Out of 90-8's routing-only scope.
- Dismissed [EDGE] "Span.open exception propagates to hydration": identical to every existing fire-and-forget helper (wwn.py house pattern); default no-provider path yields a NoOp tracer, not an exception.
- Dismissed [EDGE] "non-str effort_sources elements": the only production call site passes `sorted(core.effort)` where keys are `str(source)`-coerced at EffortPool construction (scene_harness.py effort hydration); helper signature pins `list[str]`.
- Dismissed [EDGE] "NoOp tracer silently discards spans": pre-existing operational property of ALL spans in the codebase; `init_tracer` is called at app startup (`server/app.py:168-174`) and warns loudly when unconfigured (`telemetry/setup.py` otel.otlp_dormant warning); WatcherSpanProcessor registered at `server/app.py:202`.
- Dismissed [SEC] "json.loads without try/except violates rule #1": rule #1 forbids *swallowing* exceptions — the extract swallows nothing; the explicit catch upstream logs `logger.exception` AND emits a bus event (`server/watcher.py:110-126`), which is precisely the loud handling the rule demands. Misapplied rule, challenged with line evidence.
- Dismissed [SEC] "fixture-key strings reach dashboard unescaped": identical data flowed through the retired `publish_event` path to the same dashboard — this diff changes the transport, not the exposure; rendering is the UI repo's concern and the surface is dev-gated (ADR-092).
- Dismissed [SEC] "**attrs passthrough unsanitized": pre-existing house style across every helper in the spans package; no caller passes attrs; covered by the confirmed LOW above.
- Dismissed [PREFLIGHT] ruff I001 in `tests/integration/test_dice_path_spell_cast_102_2.py`: pre-existing on develop, file untouched by this branch.

### Rule Compliance

Rules from `.pennyfarthing/gates/lang-review/python.md` + CLAUDE.md applied to every changed production unit (2 route extracts, 2 helpers, 2 call-site swaps, 1 import swap):

| Rule | Instance | Verdict |
|------|----------|---------|
| #1 no silent exception swallowing | wwn.py extract (json.loads) | compliant — no except clause exists; failures surface loudly via processor catch (watcher.py:110-126) |
| #1 | magic.py extract | compliant — pure .get() defaults, no decode step |
| #1 | scene_harness call sites | compliant — no new try/except; FixtureValidationError discipline untouched |
| #2 mutable default arguments | both helpers, keyword-only params | compliant — no mutable defaults (`_tracer=None`) |
| #3 boundary type annotations | `wwn_magic_hydrated_span`, `magic_state_hydrated_span` | compliant — full param + `-> None` annotations; `**attrs: Any` matches module house style |
| #4 logging correctness / no sensitive data | both span payloads | compliant — fixture/world/genre slugs, actor names, counts; no secrets/PII (security agent concurs) |
| #5 path handling | scene_harness | n/a to diff — existing `_FIXTURE_NAME_RE` + resolve() guards untouched |
| #6 test quality | 3 test files | compliant — every assertion value-level with diagnostic messages; the two absence-asserts are the AC's no-noise/no-double-emit requirements |
| #8 yaml.safe_load | scene_harness | unchanged, compliant (line 109) |
| CLAUDE.md No Silent Fallbacks | extract defaults (.get) | compliant — SPAN_ROUTES house style for translator-side defaults; emit-side failures loud |
| CLAUDE.md OTEL principle | both events | compliant — this story IS the principle's enforcement (typed feed visibility) |
| CLAUDE.md wiring rule | new helpers | compliant — non-test consumers at scene_harness.py:388/669; processor registered app.py:202 |

### Devil's Advocate

Suppose this is broken. The most damaging possibility: the typed events never actually render in the Subsystems tab — the story would be "complete" while the GM panel stays dark, the exact Illusionism this project exists to detect. The chain is: helper → Span.open → provider (app.py:202 registers WatcherSpanProcessor) → on_end → SPAN_ROUTES extract → `state_transition`/`magic` event. I verified each link in source, and `state_transition` is the same event_type the Subsystems tab already renders for `wwn.spell.cast` and `magic.working` — the UI explicitly handles it (`test_routes_target_known_event_types` pins the known set against watcher.ts). The weakest link is that no test drives the full processor (tests assert through `extract` directly); if `on_end` someday special-cased these names the tests would still pass. That's mitigated by the processor being generic over SPAN_ROUTES with no name-specific logic, and by existing integration tests covering the processor for sibling routes — but it is a real, if small, residual gap; I flag it as a non-blocking observation rather than a defect. Second angle: a saved GM dashboard filtering the RAW console on `event_type == "wwn.magic_hydrated"` breaks, because the raw event is now `agent_span_close` with `name=wwn.magic_hydrated`. That is the intended, documented behavior change (the story retires the raw emit), and the firehose still carries the name. Third angle: a malicious fixture author names an effort source `"<script>..."` — that string reached the dashboard identically before this change; transport swap adds no new exposure, and the surface is dev-gated. Fourth: two casters in one fixture emit two spans — matches the per-character semantics of the old emit. Nothing here rises to a defect.

### Observations (5+)

1. [VERIFIED] Extract-failure path is loud, not silent — `server/watcher.py:106-126` wraps `route.extract` in try/except, calls `logger.exception`, and publishes a `validation_warning` (severity=error) to the bus. Complies with CLAUDE.md No Silent Fallbacks; checked against rule #1 (no swallowing — the catch logs AND surfaces).
2. [VERIFIED] Production wiring end-to-end — emit sites `scene_harness.py:388/669` (non-test consumers); `init_tracer()` at `server/app.py:168-174`; `WatcherSpanProcessor` registered at `server/app.py:202`; routes registered at import via `spans/wwn.py:475` and `spans/magic.py:163`. Complies with CLAUDE.md Verify Wiring / wiring-test rules (wiring tests exercise hydrator + HTTP endpoint).
3. [VERIFIED] Severity parity with the retired emits — old calls passed `severity="info"`; the processor defaults typed severity to "info" unless span status is ERROR or a `severity` attribute opts in (`server/watcher.py:79-82, 131-140`); neither helper sets one. No dashboard severity regression.
4. [VERIFIED] Jaeger coverage improves — the retired `publish_event` events reached OTLP only with `SIDEQUEST_WATCHER_AS_SPANS=1` (`telemetry/setup.py:70-85` warns about exactly this gap); real spans hit the OTLP BatchSpanProcessor unconditionally when an endpoint is set. The swap strictly widens observability.
5. [VERIFIED] Data flow traced — fixture YAML `effort:` keys → `str(source)` coercion at EffortPool construction → `sorted(core.effort)` → `_json.dumps` → span attribute → `_json.loads` in extract → typed event fields → hub broadcast. Round-trip is injection-safe (json both ways, no eval/exec); identical strings flowed to the same dashboard pre-change.
6. [EDGE→LOW] `**attrs` can clobber the reserved `effort_sources_json` key (wwn.py helper tail) — failure ceiling is a loud validation_warning, no production caller exists; improvement candidate, not a blocker.
7. [LOW] No test drives the full WatcherSpanProcessor for these two names (tests assert through `extract` directly); processor is generic over SPAN_ROUTES and covered by sibling integration tests, so residual risk is small. Candidate for the 90-3 live-proof story to close incidentally.
8. [VERIFIED] Pattern fidelity — both helpers match the module house style exactly (keyword-only, `_tracer` override, `with Span.open(...): pass`, route beside constant per `_core.py` docstring convention; JSON-encode mirrors `magic_working_span`'s `*_json` precedent at `spans/magic.py:139-141`).

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** fixture YAML effort keys → str-coerced EffortPool keys → sorted → json.dumps → OTEL span attribute → json.loads in SPAN_ROUTES extract → state_transition/magic typed event → WatcherHub broadcast → GM-panel Subsystems tab (safe because both directions are json codecs over str-coerced keys on a dev-gated surface, failures in the translator are caught and surfaced as validation_warning events, and the identical payload flowed to the same dashboard before this change).
**Pattern observed:** routed-span lie-detector with JSON-encoded structured payload — exemplary fidelity to the established convention at `spans/magic.py:139-141` (magic_working_span `*_json` precedent) and `spans/wwn.py` fire-and-forget helpers; routing decision lint-enforced by `tests/telemetry/test_routing_completeness.py`.
**Error handling:** translator failures loud (`server/watcher.py:106-126` logger.exception + validation_warning); hydration validation discipline (FixtureValidationError → 422) untouched; emit conditions unchanged from the 90-7 contract.
**Test verdict:** 163/163 green serially (preflight), zero collateral damage, no debug leftovers, working tree clean.
**Specialist findings incorporated:**
- [EDGE] confirmed LOW: `**attrs` can clobber the reserved `effort_sources_json` key in `wwn_magic_hydrated_span` (spans/wwn.py helper tail) — failure ceiling is a loud validation_warning via the processor catch, no production caller passes attrs; non-blocking improvement logged in Delivery Findings. Seven other [EDGE] findings dismissed with line evidence (see Finding Decisions — the processor's try/except at server/watcher.py:106-126 defuses the crash/silence claims).
- [SEC] all three findings low-confidence and dismissed with evidence: the json.loads "rule #1 violation" misreads the rule (nothing is swallowed; the upstream catch logs AND surfaces), the fixture-string exposure predates this change (transport swap, same dashboard), and the `**attrs` concern is the same as the confirmed [EDGE] item. Security agent's rule sweep otherwise concurs: no sensitive data in payloads, yaml.safe_load intact, path guards untouched.
- Both LOW items (attrs clobber footgun; no full-processor test for these two names) are non-blocking and recorded as Delivery Findings for follow-up.
**Handoff:** To SM for finish-story