---
story_id: "37-31"
jira_key: null
epic: "SQ-37"
workflow: "trivial"
---
# Story 37-31: Region population on opening rooms

## Story Details
- **ID:** 37-31
- **Jira Key:** (not assigned)
- **Workflow:** trivial
- **Stack Parent:** none
- **Priority:** p1
- **Points:** 2

## Problem Statement

On turn 1, `state.current_region` is blank, causing `map_update_skipped` event. The Map tab requires a region to be load-bearing from game start. Solution: require region in world.yaml or inherit a default region so players always have map context.

## Acceptance Criteria

- Region is populated on game start (turn 1)
- Map tab shows meaningful region information from turn 1 onwards
- Works for all genre packs in content repo
- Fallback mechanism or validation prevents blank regions

## Repos Affected
- **sidequest-content** — world.yaml schema, genre pack defaults
- **sidequest-api** — world loader, region initialization logic

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-22T21:52:04Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-22T20:43:00Z | 2026-04-22T20:44:13Z | 1m 13s |
| implement | 2026-04-22T20:44:13Z | 2026-04-22T21:03:08Z | 18m 55s |
| review | 2026-04-22T21:03:08Z | 2026-04-22T21:26:04Z | 22m 56s |
| implement | 2026-04-22T21:26:04Z | 2026-04-22T21:49:35Z | 23m 31s |
| review | 2026-04-22T21:49:35Z | 2026-04-22T21:52:04Z | 2m 29s |
| finish | 2026-04-22T21:52:04Z | - | - |

## Sm Assessment

Trivial 2pt p1 fix. Root cause: `state.current_region` is empty on turn 1, which triggers a `map_update_skipped` OTEL event and leaves the Map tab useless from the opening scene. Map tab needs to be load-bearing from turn 1 — this is a "Tabletop First, Then Better" issue since a human DM would never open the session without saying where you are.

**Approach options for Dev:**
1. Require `region` on opening room in world.yaml (schema validation + fix existing packs), OR
2. Inherit a default region (e.g., world's first declared region) when current_region is blank, OR
3. Both — schema requires it, loader falls back to first region if somehow missing.

Prefer option 3 — validation is the primary fix (fail loud per No Silent Fallbacks), but the loader should also guarantee non-empty current_region at session start rather than silently skipping map_update. Add OTEL span on region resolution so GM panel can verify.

**Repos:** content (world.yaml schema/data fixes across genre packs), api (loader/state init + validation + OTEL).

**Scope notes:**
- Audit all existing `world.yaml` files to confirm they declare a region; fix any that don't.
- Ensure `sidequest-validate` catches missing region in opening room.
- Add integration/wiring test that loads a world, starts turn 1, and confirms `state.current_region` is non-blank AND a `map_update` (not `map_update_skipped`) event fires.

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): `sidequest-validate` has no explicit check that `cartography.starting_region` is both non-blank and a key in `cartography.regions`. All current packs happen to comply, but the rule is now only enforced at runtime (via `RegionInitError`). Affects `sidequest-server/sidequest/cli/validate*` (add a cartography integrity check to the validator). *Found by Dev during implementation.*
- **Question** (non-blocking): The `map_update_skipped` string from the story title does not appear anywhere in the codebase — no OTEL event, no log message by that name. The underlying bug was real (current_region blank on turn 1), but the narrator/UI plumbing that would have emitted a literal `map_update_skipped` event is not in the server yet. A future MAP_UPDATE emission path should guard on `current_region` being non-blank and emit a named skip event so the GM panel can still catch regressions there. Affects `sidequest-server/sidequest/server/session_handler.py` (MAP_UPDATE dispatch, when it lands). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): Pre-existing bug at `sidequest-server/sidequest/server/session_handler.py:1850` — narrator location-update result appends `result.location` to `snap.discovered_regions` without distinguishing room_graph mode (where `location` is a room id) from region mode. Now that region_init guarantees `current_region` is populated from turn 1, the room-id pollution of `discovered_regions` becomes more visible from turn 2 onward. Affects `sidequest-server/sidequest/server/session_handler.py` (location-update branch — guard on navigation_mode or use `discovered_rooms` for room_graph). *Found by Reviewer during code review; surfaced by silent-failure-hunter subagent.*
- **Improvement** (non-blocking): The project's OTEL pattern duplicates the event name as an `"event"` key inside the attributes dict on every `span.add_event(name, {...})` call site. Redundant with OpenTelemetry's own event-name storage; costs a few bytes per span attribute and makes attribute dicts noisier. Affects most `span.add_event(...)` sites across `session_handler.py` and peers. Codebase-wide cleanup candidate. *Found by Reviewer; surfaced by simplifier subagent.*
- **Improvement** (non-blocking): `RegionInitError` and `RoomGraphInitError` both subclass `Exception` directly with no shared `LocationInitError` base. As more init-error types are added, the dispatch site will grow parallel `except` clauses. Consider introducing a shared base when a third init type lands. Affects `sidequest-server/sidequest/game/region_init.py`, `sidequest-server/sidequest/game/room_movement.py`. *Found by Reviewer; surfaced by type-design subagent.*

## Design Deviations

No design deviations at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **No validator update in this story**
  - Spec source: `.session/37-31-session.md` SM Assessment, bullet "Ensure `sidequest-validate` catches missing region in opening room."
  - Spec text: "Ensure `sidequest-validate` catches missing region in opening room."
  - Implementation: Added runtime validation in `init_region_location` (raises `RegionInitError` on blank or unknown starting_region), plus OTEL `region.init_failed`. Did not extend the `sidequest-validate` CLI with a cartography integrity check.
  - Rationale: Every current pack already declares a valid starting_region (audited all 12 cartography.yaml files), and the runtime check now fails loud on any regression. A CLI validator pass is a legitimate follow-up but would have expanded scope beyond the 2-pt p1 fix. Logged as an Improvement finding for a follow-up story.
  - Severity: minor
  - Forward impact: minor — authoring a new pack with a broken starting_region will surface via OTEL / log on first chargen confirmation rather than at `sidequest-validate` time. No runtime behavior difference for the playgroup.

### Reviewer (audit)
- **Dev's "No validator update in this story" deviation** → ✓ ACCEPTED by Reviewer: runtime validation via `RegionInitError` + OTEL `region.init_failed` is a legitimate substitute at the 2-pt scope; all 12 current cartographies already comply (Dev audited them); rule is now enforced at dispatch time which is sufficient fail-loud behavior. A `sidequest-validate` pass is properly logged as a Dev Improvement finding for follow-up. No other undocumented spec deviations discovered during review.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/game/region_init.py` (new) — `init_region_location` + `RegionInitError`. Mirrors `room_movement.init_room_graph_location` shape so the session handler can treat the two init paths symmetrically.
- `sidequest-server/sidequest/server/session_handler.py` — wires `init_region_location` into chargen confirmation for every world with cartography (both `region` and `room_graph` modes). Emits `region.initialized` on success, `region.init_failed` on authoring-bug errors, and logs at error level without hard-failing the confirmation frame.
- `sidequest-server/tests/server/test_region_init.py` (new) — 4 wiring tests that drive the real chargen path against real content packs (caverns_and_claudes/grimvault for room_graph, heavy_metal/evropi for region) and assert current_region lands on the starting_region with the right OTEL events.

**Tests:** 4/4 new tests passing (GREEN). Full server suite: 1557 passing, 5 pre-existing failures unrelated to this story (caplog-fixture issues in `test_orchestrator.py` + one `test_rest.py` genre-packs-dir check — none touch region/cartography code).

**Branch:** `feat/37-31-region-population-opening-rooms` on sidequest-server (pushed).

**Handoff:** To review phase (Merovingian).

### Round 2 — Review Response (post-REJECT)

Merovingian rejected for lint regression + test-quality improvements. All confirmed findings addressed:

**Blocking fix:**
- Two new `I001` ruff errors on `tests/server/test_region_init.py`: collapsed the conftest import to one line with combined `# noqa: E402, I001` and a rationale comment. Lint clean on all three changed files (`ruff check sidequest/game/region_init.py sidequest/server/session_handler.py tests/server/test_region_init.py` → only the 11 pre-existing develop errors remain; no new errors introduced).

**Test quality:**
- Added `TestRegionInitUnit.test_dedup_does_not_duplicate_already_discovered_region` — direct unit test for the `if starting not in snap.discovered_regions` branch, which no integration test previously exercised (integration tests always start with an empty discovered_regions list).
- Replaced vacuous `assert expected_region` in evropi test with a specific-value compare against `"egzami_frontier"` (anchors against the known content fixture).
- Added `assert _events(otel_capture, "region.init_failed") == []` to the evropi test — mirrors the grimvault happy-path assertion.
- Added `assert sd.snapshot.discovered_regions == []` to `test_unknown_starting_region_logs_and_continues` — matches the parallel invariant checked in the blank-region test.
- Annotated fixtures and helpers:
  - `handler_factory(tmp_path: Path) -> Callable[[], WebSocketSessionHandler]`
  - `otel_capture() -> Generator[InMemorySpanExporter, None, None]`
  - `_walk_and_confirm(...) -> list[Any]`
  - `_events(...) -> list[Any]`

**Docstring:**
- Dropped "or propagate" from `region_init.py` module docstring — the wired caller always log-and-continues. Replaced with a concrete sentence pointing to the `region.init_failed` OTEL contract.

**Tests:** 5/5 passing (4 integration + 1 new unit). Lint clean on all changed files.

**Handoff:** Back to review phase (Merovingian) for round-2 sign-off.

## Round 2 — Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (round-1 lint regressions resolved; changed files ruff-clean; 5/5 tests pass; session_handler.py baseline unchanged at 11 pre-existing errors) | confirmed 0 (round-1 blocker cleared) |
| 2 | reviewer-edge-hunter | Yes | n/a | no new surface in round-2 delta (production code unchanged) | round-1 findings re-applied: all confirmed/dismissed/deferred rationales from round-1 still hold |
| 3 | reviewer-silent-failure-hunter | Yes | n/a | no new surface | round-1 dispositions stand |
| 4 | reviewer-test-analyzer | Yes | verified via diff read | 0 — all round-1 confirmed findings addressed in the test diff | confirmed 0: dedup test present, vacuous assert replaced, OTEL negative check mirrored, discovered_regions invariant added |
| 5 | reviewer-comment-analyzer | Yes | verified via diff read | 0 — round-1 "or propagate" docstring fix verified in region_init.py:13-16 | confirmed 0 (round-1 finding cleared) |
| 6 | reviewer-type-design | Yes | verified via diff read | 0 — 4 fixture/helper type annotations added (handler_factory, otel_capture, _walk_and_confirm, _events) | confirmed 0 (rule #3 violations cleared) |
| 7 | reviewer-security | Yes | n/a | no new surface; production code untouched | round-1 clean verdict stands |
| 8 | reviewer-simplifier | Yes | n/a | no new surface | round-1 dispositions stand (deferred `"event"` key cleanup and noqa-removal remain codebase-wide follow-ups) |
| 9 | reviewer-rule-checker | Yes | verified via diff read | 0 — all 5 round-1 violations resolved (rule 3 × 4 type annotations, rule 6 × 1 missing invariant) | confirmed 0 |

**All received:** Yes (round-2 preflight re-run; other 8 specialists verified via direct diff read — round-2 delta is scoped to test file + 5-line docstring, no new production surface)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment (Round 2)

**Verdict:** APPROVED

Dev (Agent Smith) came back with a tight, precise punch-list response. Every round-1 confirmed finding is addressed exactly as specified:

- [RULE] I001 lint on `tests/server/test_region_init.py`: resolved via single-line conftest import + `# noqa: E402, I001` with a one-line rationale comment. `ruff check` clean on all three changed files.
- [TEST] Dedup-append branch now has a direct unit test (`TestRegionInitUnit.test_dedup_does_not_duplicate_already_discovered_region`) that pre-seeds `snap.discovered_regions` with the starting region and asserts length and order preservation. Exercises the exact line the integration suite could never reach.
- [TEST] Vacuous `assert expected_region` in evropi test replaced with `assert world.cartography.starting_region == "egzami_frontier"` — anchors against the known fixture.
- [TEST] `assert _events(otel_capture, "region.init_failed") == []` added to the evropi test (symmetry with grimvault).
- [TEST] `assert sd.snapshot.discovered_regions == []` added to the unknown-region test (parallel invariant with blank-region test).
- [RULE] Fixture and helper annotations in place: `handler_factory -> Callable[[], WebSocketSessionHandler]`, `otel_capture -> Generator[InMemorySpanExporter, None, None]`, `_walk_and_confirm / _events -> list[Any]`.
- [DOC] "or propagate" removed from `region_init.py` docstring; replaced with a concrete OTEL-contract sentence pointing at `region.init_failed`.

**Tests:** 5/5 passing (`tests/server/test_region_init.py`). The OTEL teardown ValueError noted by preflight is a known pre-existing test-harness artifact on span-exporter shutdown, not a failure in this suite.

**Specialist coverage on round-2 delta:** [EDGE] no new boundary conditions introduced (production code untouched; round-1 dispositions stand). [SILENT] no new error-handling paths (test file only). [SIMPLE] no new complexity; delta is strictly corrective (resolves flagged items, no new abstractions). [TYPE] rule #3 compliance restored — all 4 fixture/helper annotations present (`Callable`, `Generator`, `list[Any]` × 2). [SEC] no new attack surface — test file adds a pydantic-constructed fixture only, no untrusted inputs. All round-1 tagged findings are resolved or remain deferred per the round-1 assessment.

**Branch:** `feat/37-31-region-population-opening-rooms` on sidequest-server, 2 commits (`6aa96f5` feat + `ba111e6` review-response).

**Production code** (session_handler.py region_init block + region_init.py): unchanged since round-1 approval on structural grounds. Round-1 Rule Compliance audit holds: 19 rules × 47 instances on production code, all compliant.

**Delivery findings from round 1 remain open for follow-up stories** (session_handler.py:1850 room-id/region conflation, `"event"` key redundancy across all span.add_event sites, shared `LocationInitError` base). None are blocking for 37-31.

**Handoff:** To SM (Morpheus) for finish phase — PR, merge, sprint archive.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 13 ruff errors (11 pre-existing on develop, 2 new I001 on test_region_init.py) | confirmed 2 new (blocking), 11 pre-existing dismissed (not this story's scope) |
| 2 | reviewer-edge-hunter | Yes | findings | 6 (2 high, 2 medium, 2 low) | confirmed 2 (test-analyzer corroborates dedup/resume gaps), dismissed 2 (cartography-None guard not needed — existing room_graph block at :1174 also assumes non-None; worlds.get()-returns-None is intentionally silent — matches room_graph), dismissed 2 low (race-condition is session-serial per ADR-066; key-stripping not needed — packs validated upstream) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 (both medium) | dismissed 1 (log-loud-and-continue is deliberate symmetry with room_graph path, OTEL + error-log satisfies fail-loud for pack-authoring bugs), deferred 1 (pre-existing bug at session_handler.py:1850 — room-id leaking into discovered_regions — not in this diff, logged as delivery finding for follow-up) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 (1 high, 3 medium, 2 low) | confirmed 3 (dedup gap, vacuous `assert expected_region`, asymmetric OTEL negative check), confirmed 1 (resume-flow untested — matches edge-hunter), dismissed 2 low (private-attr coupling is existing repo pattern; blank-region extra invariant is nice-to-have) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (1 medium, 2 low) | confirmed 1 ("or propagate" is misleading — the only caller always swallows), dismissed 2 low (module-docstring "real content packs" plural is technically accurate since grimvault+evropi exist; test comment wording is fine) |
| 6 | reviewer-type-design | Yes | findings | 3 (all low, all forward-looking) | deferred 3 (shared LocationInitError base, RegionId newtype, patch vs mutate nullability — all legitimate long-term improvements, none applicable to a 2pt trivial fix; production code fully type-compliant) |
| 7 | reviewer-security | Yes | clean | 0 | N/A (clean — no injection paths, no sensitive data in logs/OTEL, pack-authored input only) |
| 8 | reviewer-simplifier | Yes | findings | 3 (1 medium, 2 high) | confirmed 1 ("event" key in span.add_event attrs is redundant with the event name arg — but matches existing room_graph block; deferred as codebase-wide cleanup, not this story), confirmed 1 (conftest import noqa — but matches test_room_graph_init.py pattern exactly, deferred for parity), dismissed 1 medium (inline-region_init-into-handler: parity with room_movement.py module is the design; new module is justified for testability and future RegionInitError growth) |
| 9 | reviewer-rule-checker | Yes | findings | 5 (19 rules × 47 instances, production code clean on all 19; all 5 violations in test file) | confirmed 4 (missing fixture type annotations × 2 + bare-list return types × 2), confirmed 1 (missing discovered_regions invariant in unknown-region test — matches test-analyzer), dismissed 1 (asyncio.run pattern matches existing test_room_graph_init.py exactly — parity with established test harness takes precedence over rule 9) |

**All received:** Yes (9 returned, 7 with findings, 1 clean)
**Total findings:** 13 confirmed, 8 dismissed (with rationale), 4 deferred (forward-looking type improvements)

## Reviewer Assessment

**Verdict:** REJECTED

The core implementation is structurally sound — rule-checker found production code clean on all 19 rules (13 Python + 6 CLAUDE.md principles), security is clean, the OTEL contract is tested, and the pattern mirrors room_graph deliberately. However, the diff introduces two new ruff I001 lint errors and the test file has a handful of medium-severity quality gaps that three different subagents independently flagged. Bundle them into one tight Dev pass.

### Rule Compliance

Per rule-checker's exhaustive audit:
- **Production code (`region_init.py` + `session_handler.py` block):** compliant on all 19 rules (silent-exceptions, mutable-defaults, type-annotations, logging, path-handling, resource-leaks, unsafe-deserialization, async-pitfalls, import-hygiene, input-validation, dependency-hygiene, fix-regressions, no-silent-fallbacks, no-stubbing, don't-reinvent, verify-wiring, wiring-test, OTEL).
- **Test code (`test_region_init.py`):** 5 violations on rules 3 (type annotations) and 6 (test quality).

### Findings

| Severity | Tag | Issue | Location | Fix Required |
|----------|-----|-------|----------|--------------|
| [HIGH] | [RULE] | Two new `I001` lint errors introduced by the diff — `tests/server/test_region_init.py` import blocks at lines 16 and 42 are unsorted. Develop lint baseline is 11 errors, branch is 13. | `tests/server/test_region_init.py:16,42` | Run `uv run ruff check --fix tests/server/test_region_init.py` and commit. Leave pre-existing session_handler.py errors alone. |
| [MEDIUM] | [TEST][RULE] | Dedup-append contract is untested. `init_region_location`'s `if starting not in snap.discovered_regions` guard has no test that pre-seeds the list. A regression that drops the guard would be undetected. | `tests/server/test_region_init.py` (new test) | Add a test that pre-seeds `sd.snapshot.discovered_regions = [expected_region]` before running chargen confirmation, asserts `len == 1` afterwards. |
| [MEDIUM] | [TEST][RULE] | Vacuous `assert expected_region` at test_region_init.py:139 (the evropi test) violates python.md rule #6 — truthy check passes for any non-empty garbage string. Grimvault test got this right with a specific-value compare. | `tests/server/test_region_init.py:139` | Compare against a specific string (`assert expected_region == "egzami_frontier"`) or assert it matches the loaded cartography value explicitly. |
| [MEDIUM] | [TEST] | Asymmetric OTEL negative coverage — grimvault happy-path asserts `region.init_failed == []` but the evropi test does not. Regression where happy-path accidentally emits init_failed would slip through for region-mode worlds. | `tests/server/test_region_init.py` (evropi test body) | Add `assert _events(otel_capture, "region.init_failed") == []` to the evropi test, mirroring grimvault. |
| [MEDIUM] | [TEST][RULE] | `test_unknown_starting_region_logs_and_continues` omits the `discovered_regions == []` invariant that `test_blank_starting_region_logs_and_continues` explicitly checks. Parallel tests, asymmetric assertions. | `tests/server/test_region_init.py` (unknown-region test) | Add `assert sd.snapshot.discovered_regions == []` to the unknown-region test. |
| [MEDIUM] | [RULE] | Four test helpers / fixtures missing return type annotations: `handler_factory`, `otel_capture`, `_walk_and_confirm` (bare `list`), `_events` (bare `list`). python.md rule #3 treats fixtures as module boundaries. | `tests/server/test_region_init.py:46,61,94,123` | Annotate: `handler_factory -> Callable[[], WebSocketSessionHandler]`, `otel_capture -> Generator[InMemorySpanExporter, None, None]`, `_walk_and_confirm -> list[Any]` (with or without comment), `_events -> list[Any]`. |
| [LOW] | [DOC] | `region_init.py` module docstring says "log-and-continue (chargen must not hard-fail) or propagate" — only the log-and-continue branch is wired; "or propagate" is aspirational. | `sidequest/game/region_init.py:13-14` | Drop "or propagate" from the docstring — the wired caller always swallows. |

### Observations tagged by specialist

- [SEC] Security review clean — no injection, no sensitive data in logs/OTEL, pack-authored input validated at the init boundary. `sidequest-server/sidequest/game/region_init.py:35-58` strips input, checks membership against `cartography.regions`, raises on failure.
- [SILENT] Log-and-continue for `RegionInitError` at `sidequest-server/sidequest/server/session_handler.py:1204` is deliberate symmetry with the room_graph error path; OTEL `region.init_failed` + `logger.error` satisfy fail-loud for pack-authoring bugs. NOT a silent fallback.
- [EDGE] Edge-hunter's `world.cartography is None` guard concern: dismissed — existing room_graph block at `:1174` also reads `.cartography.navigation_mode` without a None guard, and pydantic `WorldConfig.cartography` is a required field. Parity with the neighbor pattern holds.
- [EDGE] Edge-hunter's resume-flow double-init concern: dismissed — `_chargen_confirmation` is only reached from `_state == Creating`; a reconnected session with `has_character=True` skips chargen entirely (session_handler.py:618), so region_init never re-runs.
- [SIMPLE] Simplifier's "inline region_init into handler" suggestion: dismissed — parity with `room_movement.py` module shape is the intended design, supports testability and future RegionInitError growth without bloating the handler.
- [SIMPLE] Simplifier's "`event` key in span.add_event attrs is redundant": confirmed but deferred — matches every other `span.add_event` call in session_handler.py; codebase-wide cleanup, not a story-scoped fix. Logged as Delivery Finding.
- [TYPE] All 3 type-design findings (shared `LocationInitError` base, `RegionId` newtype, mutation-vs-patch nullability): deferred — all low-confidence forward-looking improvements. Production code fully type-annotated per python.md rule #3.

### Dismissed / deferred (with rationale)

- **Cartography-None guard** (edge-hunter): The existing room_graph block at `session_handler.py:1174` reads `world.cartography.navigation_mode` without a None-guard — cartography is an assumed-non-None required field on WorldConfig. Adding the guard here would be an improvement but would also flag the existing code; out of scope for 2-pt trivial.
- **`worlds.get() is None` silent skip** (edge-hunter): Intentional and matches the existing room_graph block — an unresolvable world slug is already handled upstream with a load-level error; not a new silent failure.
- **`asyncio.run(body())` pattern** (rule-checker rule 9): Matches `test_room_graph_init.py` exactly — this is the established test harness in this repo. Changing it would be a codebase-wide refactor, not a story-scoped fix.
- **Conftest import `# noqa: E402`** (simplifier): Matches `test_room_graph_init.py` pattern exactly. Parity with neighbor file wins over noqa-removal.
- **`event` key duplicated in span.add_event dicts** (simplifier): Redundant but matches every other span.add_event in session_handler.py. Codebase-wide cleanup, not this story.
- **Inline `region_init` into handler** (simplifier): Rejected — parity with `room_movement.py` module structure is the intended design, supports future growth of RegionInitError subclasses, keeps testability clean.
- **Resume-flow test gap** (edge-hunter / test-analyzer): Dismissed. `_chargen_confirmation` is only reached when `_state == Creating`; resume with `has_character=True` skips to Playing, so region_init never re-runs on reconnect. Not a real regression risk.
- **Shared `LocationInitError` base / `RegionId` newtype** (type-design): All low-confidence, forward-looking — defer to a refactor story when a third init type lands.

### Devil's Advocate

Suppose a malicious or careless pack author writes `starting_region: "../etc/passwd"` or `starting_region: "<script>alert(1)</script>"`. Does this code care? The string passes through `strip()`, a dict-membership check, and lands on `snap.current_region`. Downstream, `current_region` is rendered in `commands.py` status output ("Location: X (Y)") and flows into narrator prompts. There is no sanitization for quotes, newlines, or path characters — but the narrator is Claude (string-tolerant, not shell-executed) and the UI is React (auto-escapes). Not a bug today, but worth noting that `current_region` is now guaranteed-populated, which means all downstream consumers that read it unchecked (commands.py:109 renders it into a template literal; delta.py:112 propagates it) will always show whatever the pack authored. If a pack author typos `starting_region` as `" ashgate_square "` with leading whitespace, `strip()` saves us on the `snap.current_region` value — but the dict-membership check uses the stripped value against raw dict keys (which may also have typos), so validation is strict (no silent match). This is correct behavior.

A confused user running `/gm teleport` to a region will work — `commands.py:361` sets `current_region` directly, overwriting the init value; discovered_regions accumulates correctly. No interaction bug.

The filesystem-stress angle: if YAML load produces a `starting_region` that's `None` rather than `""` (possible if the key is present with a null value in YAML), `.strip()` raises `AttributeError` — but the try/except catches `RegionInitError`, not `AttributeError`. The player would get a confirmation crash. **Edge-hunter flagged this at medium confidence.** However, pydantic's `CartographyConfig.starting_region: str = ""` coerces null YAML to the default `""`, not `None` — pydantic would actually reject a null value with a validation error at pack-load time before this code ever runs. So `AttributeError` cannot happen through the loader. Confirmed-not-a-bug via pydantic type guarantee.

What breaks on a resumed session mid-chargen? The player connects, walks 2 of 5 scenes, disconnects. On reconnect, `_state` is set to `Creating` if `not has_character` (line 618). The player then sends the 3rd scene message, eventually reaches confirmation. `_chargen_confirmation` runs once per completed chargen — region init runs exactly once. No double-append.

Nothing else emerges. The review holds.

### Delivery Findings

**Handoff:** Back to Dev (Agent Smith) for the punch list above.