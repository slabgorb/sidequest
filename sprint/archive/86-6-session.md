---
story_id: "86-6"
jira_key: ""
epic: "86"
workflow: "tdd"
---
# Story 86-6: War Rig table-game core

## Story Details
- **ID:** 86-6
- **Jira Key:** (not in use)
- **Workflow:** tdd
- **Stack Parent:** 86-4 (not same-stack dependency; predecessor)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-09T07:32:09Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-09T00:00:00Z | 2026-06-09T06:24:43Z | 6h 24m |
| red | 2026-06-09T06:24:43Z | 2026-06-09T06:36:47Z | 12m 4s |
| green | 2026-06-09T06:36:47Z | 2026-06-09T07:05:32Z | 28m 45s |
| review | 2026-06-09T07:05:32Z | 2026-06-09T07:17:08Z | 11m 36s |
| green | 2026-06-09T07:17:08Z | 2026-06-09T07:25:45Z | 8m 37s |
| review | 2026-06-09T07:25:45Z | 2026-06-09T07:32:09Z | 6m 24s |
| finish | 2026-06-09T07:32:09Z | - | - |

## Sm Assessment

**Setup complete — routing to TEA (RED phase).**

- **Story:** 86-6 (8pts, tdd/phased), repos `sidequest-server` + `sidequest-content`, branch `feat/86-6-war-rig-crew-core` in both. No Jira (no-jira project).
- **Provenance:** Split from 86-4 (13pts) after an Architect design pass settled the open architectural fork. Sibling 86-7 (Command Points + Crisis table) follows this story.
- **Design spec (REQUIRED READ for TEA/Dev):** `docs/superpowers/specs/2026-06-09-road-warrior-war-rig-crew-spec.md`. The fork is settled: crewed War Rig combat reuses the **ADR-129 N-Seat Table Engine** (`resolution_mode: table_resolution`) as a new `war_rig_crew` kind bound via the `cwn` `RulesetModule.deal_table`/`resolve_table` seams. Rejected: ADR-077 dogfight sealed-letter (1v1-shaped), `beat_selection` (single-actor), and a `seat` field on `EncounterActor` (`TableSeat` already IS the seat primitive).
- **Scope (G1–G4):** register `war_rig_crew` + crew verbs; add a `custom_beat()` seam to the `TableGame` ABC (the one core-engine edit — `engine.py` currently `ValueError`s on unknown beats); vessel-scoped shared Hull pool reusing the `rig_pool.*` spans keyed by `vessel_id` (RigComposurePool is character-bound — cannot be the shared hull); Hull→0 crash cascade fanning 86-2's `resolve_crash_saves` out to each seated occupant. Plus a **mandatory OTEL wiring test** (rig_pool.* + table.* spans fire on a real crewed turn — GM panel is the lie detector).
- **Scope boundaries:** Command Points + d10 Crisis table are OUT (86-7). Solo-rig production combat STAYS on 86-2's two-pool path — the single-seat case rides the new engine for completeness/testing only, not as a replacement. Full vessel stat blocks/calibration are 86-5/Plan 5.
- **Predecessors 86-1 + 86-2 are DONE.** Merge gate clear (0 in-progress, 0 in-review).
- **Note for downstream:** the split tool set `depends_on: 86-4` on both children; the real 86-7→86-6 sequencing is captured in 86-7's title/spec (no CLI flag to edit `depends_on`; not hand-editing YAML). Harmless — `sidequest-server` is not a stacked repo.

**Decision:** Setup gate satisfied → hand off to TEA for RED.

## Tea Assessment

**RED complete — failing tests committed (`d6254357`), routing to Dev (GREEN).**

Tests follow the 86-2 precedent: proposed seams stated as TEA contract (open to Dev
refinement), assertions on **behaviour + telemetry** not internal names, imports inside test
bodies so a missing module fails the test, not collection. **RED verified:** `10 failed, 1
passed, 5 errored` — every failure is "feature not built", no collection breakage, the
fail-loud guard passes today.

### Acceptance Criteria (TEA-defined from spec §3–6)

| AC | Gap | Test(s) | RED reason |
|----|-----|---------|------------|
| **AC1** `war_rig_crew` table-game kind registered, resolvable like poker/auction | G1 | `test_war_rig_crew_kind_is_registered`, `test_unregistered_kind_still_fails_loud` | `sidequest.game.table.war_rig` absent |
| **AC2** deal assigns a station role (driver/gunner/wrench/spotter/road_boss) to every crew seat; single-seat == solo-rig degenerate | G1 | `test_deal_assigns_a_station_role_to_every_crew_seat`, `test_single_seat_crew_is_the_degenerate_solo_rig` | kind absent |
| **AC3** custom-beat dispatch seam: a war_rig station verb resolves through `resolve_table` WITHOUT the "unsupported beat" ValueError | G2 | `test_war_rig_station_verb_resolves_without_unsupported_beat_error` | seam + kind absent |
| **AC4** No Silent Fallbacks preserved: a kind that does NOT handle a beat STILL fails loud (poker + `shoot` raises) | G2 | `test_poker_unsupported_beat_still_fails_loud_after_seam` | **PASSES today** — regression guard, must stay green |
| **AC5** vessel-scoped shared Hull pool reuses `rig_pool.*` spans; sublethal hit → `delta`, kill → `delta`→`zero_crossing`→`crash_event`, armor-reduced | G3 | `test_sublethal_hull_hit_emits_rig_pool_delta`, `test_hull_destruction_fires_full_rig_chain` | `sidequest.game.war_rig_combat` absent |
| **AC6** Hull→0 fans CWN crash saves to EVERY occupant (HP loss + dismounted); passed saves spare the occupant | G4 | `test_hull_destruction_fans_crash_saves_to_every_occupant`, `test_passed_saves_spare_the_occupant` | module absent |
| **AC7** MANDATORY OTEL wiring: a crewed round drives `table.*` AND the hull drives `rig_pool.*` through the REAL `WatcherSpanProcessor` route | G2+G3 | `test_hull_destruction_fires_full_rig_chain` (rig half), `test_crewed_round_emits_table_spans_through_real_route` (table half) | modules/seam absent |
| **AC8** content: road_warrior declares a `war_rig` `table_resolution` / `war_rig_crew` confrontation with station beats, no dial metrics | content | `tests/genre/test_war_rig_crew_content.py` (6 tests) | `war_rig` confrontation not in `road_warrior/rules.yaml` |

### Rule Coverage (`.pennyfarthing/gates/lang-review/python.md` + CLAUDE.md)

- **#6 Test quality** — every test has a meaningful assertion; negative cases included
  (`test_passed_saves_spare_the_occupant`, `test_poker_unsupported_beat_still_fails_loud`). No
  vacuous `assert True` / bare-truthy / `let _ =`. Self-checked.
- **No Silent Fallbacks** (CLAUDE.md, critical) — AC4 directly enforces it: the custom-beat
  seam must not turn an unknown beat into a silent no-op; poker must still raise. This is the
  load-bearing rule test, green today, must stay green after Dev wires the seam.
- **No Source-Text Wiring Tests** (server CLAUDE.md) — the wiring tests assert OTEL spans
  through the real watcher route (`WatcherSpanProcessor` + `watcher_hub`) and behavioural HP
  deltas, never `read_text()`/grep of source. AC7 is the canonical "drive the flow, assert the
  spans" shape.
- **Every Test Suite Needs a Wiring Test** (CLAUDE.md) — AC7 (both halves) + AC8 (content
  reaches the kind) are the integration/wiring proofs; AC1–AC6 are the unit layer.
- **#3 Type annotations / #1 silent-exceptions** — Dev-side checks for the GREEN code; the
  proposed seams carry full signatures in the test docstrings to steer typed APIs.

### Notes for Bicycle Repair Man (Dev)

- **Proposed seams are a contract, not a cage** — names (`WarRigHull`,
  `apply_war_rig_hull_damage`, `custom_beat`) mirror 86-2's `apply_rig_damage`; refine if a
  cleaner shape emerges, but keep the **observable behaviour + span families** the tests pin.
- **The `rig_pool.*` extract lambdas key on `character_id`/`chassis_id`** (telemetry/spans/rig.py).
  For a vessel-scoped Hull you'll need the spans to carry the vessel identity — either route
  `vessel_id` into those attrs or extend the route. The tests assert the `op` fires (delta/
  zero_crossing/crash_event) and the armor-reduced magnitude, not the attr key — you have
  latitude on how `vessel_id` rides.
- **Cooperative vs competitive showdown** is real design surface: the table engine's `_showdown`
  picks max `strength()`. A war_rig is cooperative (crew vs external threat) — the win condition
  is Hull depletion, not a strength comparison. The unit tests deliberately stay at one
  decision point (no showdown) to avoid pinning this; settle it in GREEN and log a Design
  Deviation if it reshapes `_showdown`/win-condition handling.
- **Scope boundary (don't regress 86-2):** solo-rig combat stays on `apply_rig_damage` /
  `RigComposurePool`. Keep the full existing suite green. Command Points + Crisis table are
  **86-7**, not here.

**Decision:** RED gate satisfied → hand off to Dev for GREEN.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings. Every TEA-proposed seam (`custom_beat`, `WarRigHull`, `apply_war_rig_hull_damage`) implemented as specified; the spec's reuse mandate held — no engine reimplementation needed.

### Dev (rework — review round 1)
- No new upstream findings. The Reviewer's blocking finding (war_rig_crew unregistered in production) is fixed and now guarded by a pollution-proof subprocess wiring test that fails RED without the `__init__` import (verified by temporarily reverting it). All non-blocking findings addressed in the same pass.

### Reviewer (code review)
- **Gap** (non-blocking): `WarRigHull` / `apply_war_rig_hull_damage` (`sidequest-server/sidequest/game/war_rig_combat.py`) have NO production caller — invoked only by tests. The station-verb→Hull-damage integration (a `shoot` verb actually depleting the threat's Hull) and the `table_showdown`→Hull win-condition wiring are deferred. Affects `war_rig_combat.py` + `narration_apply.py`/`encounter_lifecycle.py` (a future story must call the Hull seam from the resolution loop). *Found by Reviewer during code review.* — must be tracked so the Hull primitive doesn't become permanently orphaned (likely 86-5/86-7 per spec §6).
- **Gap** (non-blocking): content `damage_model` block in `road_warrior/rules.yaml` (lines ~93-114) still reads "CRASH EVENT … Not yet mechanically fired (Plan 2, dormant)" without distinguishing the now-live crewed Hull crash (86-6). Affects `genre_packs/road_warrior/rules.yaml` (add a note that the crewed war_rig Hull crash is live while the solo Rig Composure pool remains dormant). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the four `rig_pool.*` crash_event spans fan out per-occupant but the SPAN_ROUTES extract lambda drops the `occupant` attr, so all per-occupant crash_events render with identical `character_id`/`chassis_id` (= vessel_id) — the GM panel can't tell which crew member crashed. Affects `telemetry/spans/rig.py` (add occupant to the crash_event route, or accept reduced granularity). *Found by Reviewer during code review.*

### Reviewer (re-review — round 2, all non-blocking LOW polish)
- **Improvement** (non-blocking): `test_war_rig_unknown_station_verb_fails_loud` could `pytest.raises(ValueError, match=r"war_rig_crew has no station verb")` to pin the message, so a future change to the ABC default's exception type can't make it pass vacuously. Affects `tests/game/table/test_war_rig.py`. *Found by Reviewer during code review.*
- **Gap** (non-blocking): no test for the armor-floor on a *killing* hit (e.g. `hull.current=1, amount=3, armor=9` → floored 1-point hit destroys the Hull → zero_crossing + crash). Affects `tests/integration/test_war_rig_crew_combat.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `_crash_occupant` docstring says "matching the solo handler's *unconditional* appends" but the impl uses idempotency guards. Affects `sidequest/game/war_rig_combat.py` (reword to "idempotently appends"). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `strength()` docstring "picks contenders[0] by position" is actually `max()` stability on equal keys, not a guaranteed first-seat rule. Affects `sidequest/game/table/war_rig.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **`vessel_id` rides the existing `rig_pool.*` `character_id`/`chassis_id` attr slots (no route change)**
  - Spec source: 2026-06-09-road-warrior-war-rig-crew-spec.md, §4 G3 / TEA note (session lines 86-90)
  - Spec text: "reuses the `rig_pool.*` span vocabulary … keyed by `vessel_id` instead of `character_id` … either route `vessel_id` into those attrs or extend the route"
  - Implementation: Routed `vessel_id` into BOTH `character_id` and `chassis_id` span attrs AND added an explicit `vessel_id` attr; did NOT extend the SpanRoute extract lambdas in `telemetry/spans/rig.py`.
  - Rationale: The extract lambdas already surface `character_id`/`chassis_id`, so the GM panel renders the crewed Hull with zero route changes; the explicit `vessel_id` attr is forward-room for a dedicated route later. TEA explicitly granted this latitude.
  - Severity: minor
  - Forward impact: minor — if a future story wants `vessel_id` as a first-class rendered field, add it to the four `rig_pool.*` extract lambdas; the attr is already emitted.
- **Cooperative `strength()` returns a uniform 0; `_showdown` left unchanged**
  - Spec source: TEA note (session lines 91-95)
  - Spec text: "settle [cooperative vs competitive showdown] in GREEN and log a Design Deviation if it reshapes `_showdown`/win-condition handling"
  - Implementation: `WarRigCrewTableGame.strength()` returns 0 uniformly (crew don't compete); `engine._showdown` and the win-condition machinery are untouched. Win condition is Hull depletion, modeled on the vessel side (`war_rig_combat.py`), not in the table showdown.
  - Rationale: A cooperative crew has no inter-crew strength comparison; reshaping `_showdown` was unnecessary for 86-6's scope and would have risked the poker/auction suites. A uniform 0 makes any accidental showdown a stable no-contest rather than a crash.
  - Severity: minor
  - Forward impact: minor — 86-7 (Command Points/Crisis) or 86-5 (calibration) may introduce a real cooperative win/lose evaluation on the table state; it should live on the Hull/vessel branch, not by overloading `strength()`.
- **road_warrior `war_rig` confrontation is `category: movement`, not `combat`**
  - Spec source: 2026-06-09 spec §6 (minimal content) — category unspecified
  - Spec text: "Ship a minimal playable `war_rig` confrontation def … (`resolution_mode: table_resolution`, `table_game: war_rig_crew`, beats, station roles) sufficient to prove wiring."
  - Implementation: Chose `category: movement` (the chase precedent) rather than `combat`.
  - Rationale: `category: combat` enlists a confrontation in road_warrior's 86-1 CWN assertions that pin "exactly one combat confrontation" and require opponent HP/AC/DEX seed keys (`test_road_warrior_loads_cwn.py::_combat_confrontation`). A `table_resolution` war_rig reads `table_state`, never the dial/HP combat seam, so `movement` (vehicular action) is both correct and collision-free.
  - Severity: minor
  - Forward impact: none expected — categories are pack-local; 86-5/86-7 can recategorize if a vehicular-combat category is later introduced to the closed set.

### Dev (rework — review round 1)
- No NEW spec deviations introduced by the rework. All changes are fixes to Reviewer findings (registration wiring, test strengthening, docstring/comment corrections). The three deviations above remain as logged and were stamped ACCEPTED by Reviewer. The docstring/comment caveats the Reviewer attached to deviations #1 and #2 (vessel_id "carried explicitly"; strength() "cooperative victory lives on the Hull") were corrected in this rework — the docstrings now state the actual span routing and the deferred win-condition state.

### Reviewer (audit)
- **`vessel_id` rides `character_id`/`chassis_id` slots** → ✓ ACCEPTED by Reviewer: the routing choice is sound and TEA-sanctioned; the GM panel renders the Hull via `character_id=vessel_id`. **Caveat (separate finding, non-blocking):** the docstrings claim `vessel_id` is "carried explicitly for downstream consumers," but no `rig_pool.*` SPAN_ROUTES extract lambda reads `vessel_id` — it only rides aliased into `character_id`/`chassis_id`. The *deviation* is accepted; the *docstring overclaim* should be corrected in rework.
- **Cooperative `strength()` returns 0; `_showdown` unchanged** → ✓ ACCEPTED by Reviewer: correct scope call — not reshaping `_showdown` protects poker/auction and matches the 86-6 boundary. **Caveat:** the strength() docstring says "cooperative victory check lives on the Hull," but the content's `win_condition: table_showdown` means the engine STILL declares a `contenders[0]` winner after `max_decision_points`; the Hull is not currently wired as a win condition. Doc wording should be tightened; the win-condition→Hull integration is legitimately deferred to 86-5/86-7 (logged as a Delivery Finding).
- **`category: movement` not `combat`** → ✓ ACCEPTED by Reviewer: well-reasoned; `movement` is the correct closed-set value for a `table_resolution` vehicular confrontation and dodges the 86-1 single-combat opponent-seed assertions. Verified the closed set `{combat, social, pre_combat, movement, hacking}` and that no "exactly one movement" assertion exists.
- **UNDOCUMENTED (Reviewer audit):** Dev did NOT register `war_rig_crew` in the production import chain (`table/__init__.py`) — this is a **defect**, not a deviation (see Reviewer Assessment, blocking finding R1). The Dev Assessment claimed "resolvable like poker/auction (G1)" and "Implementation Complete: Yes" — but poker/auction are registered via `__init__.py` side-effect imports and `war_rig` is not, so the claim is false in production. Flagged as blocking.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/game/table/war_rig.py` (new) — `WarRigCrewTableGame` kind: deals station roles, resolves station verbs via `custom_beat`, emits `table.seat_seeded` + `table.commit` spans (G1).
- `sidequest-server/sidequest/game/table/registry.py` — added `TableGame.custom_beat()` to the ABC; default fails loud with `ValueError` (preserves No Silent Fallbacks) (G2).
- `sidequest-server/sidequest/game/table/engine.py` — `_apply_signature_beat` now dispatches unknown beats to `game.custom_beat(...)` instead of a terminal raise; poker/auction unaffected (G2).
- `sidequest-server/sidequest/game/war_rig_combat.py` (new) — `WarRigHull` (vessel-scoped pool reusing `rig_pool.*` spans keyed by `vessel_id`) + `apply_war_rig_hull_damage` (armor-reduced delta → zero_crossing → crash fan-out across every occupant via 86-2's `resolve_crash_saves`) (G3 + G4).
- `sidequest-content/genre_packs/road_warrior/rules.yaml` — minimal playable `war_rig` `table_resolution` / `war_rig_crew` confrontation with steer/shoot/repair/scan station beats, no dial metrics, `category: movement` (AC8).

**Tests:** 16/16 new 86-6 tests passing (GREEN). Regression suites green: table + rig + crash + poker + auction = 279 passed, 3 skipped; the 3 road_warrior CWN tests I initially perturbed (category collision) now pass. Lint + format + pyright clean on all changed files.

**Full-suite caveat (environmental, not code):** `uv run pytest` in this shell shows ~24 failures + ~82 errors that ALL trace to `MissingDatabaseUrlError: SIDEQUEST_DATABASE_URL is not set` (no test Postgres provisioned in this environment — reference/forensics/lore_rag/app tests require it). None touch the table/rig/war_rig code paths. Confirmed via direct re-run: the only 86-6-attributable failures were the 3 road_warrior category collisions, now fixed.

**Branch:** `feat/86-6-war-rig-crew-core` (both `sidequest-server` and `sidequest-content`) — pushed.

**Handoff:** To next phase (verify/review).

### Dev Rework Addendum (review round 1 → green)

Addressed all Reviewer findings:
- **[CRITICAL fixed]** Registered `war_rig_crew` in production: added `from sidequest.game.table import war_rig as _war_rig` to `sidequest/game/table/__init__.py` (alongside poker/auction) + updated the package docstring. Verified RED→GREEN: a fresh interpreter importing only `sidequest.game.table` now resolves `war_rig_crew` (was `UnknownTableGameError`).
- **[HIGH fixed]** Strengthened `test_war_rig_crew_kind_is_registered` to import the PACKAGE (not the module) + added `test_war_rig_crew_registered_via_production_package_import`, a subprocess-isolated wiring test (mirrors `tests/magic/test_production_registration_wiring.py`). Proven to fail when the `__init__` import is reverted — it would have caught the original bug.
- **[MEDIUM fixed]** `war_rig.py` now declares `__all__`.
- **[MEDIUM fixed]** OTEL wiring assertions tightened: `crash_event` count == occupant count; `table.commit` spans pinned to 3 distinct station beat_ids (`steer`/`shoot`/`repair`), not a truthy "at least one."
- **[MEDIUM fixed]** Added `test_war_rig_unknown_station_verb_fails_loud` (the kind-level ValueError path for an unknown verb).
- **[LOW fixed]** Added armor-floor test (armor ≥ damage → 1-point scratch) and one-failed-save test (exactly half-max HP).
- **[LOW fixed]** Corrected docstring overclaims (`vessel_id` aliasing vs. "carried explicitly"; `strength()`/win-condition wording) and the `road_warrior/rules.yaml` `damage_model` "dormant crash" comment (now distinguishes the live crewed Hull from the dormant solo Rig Composure pool).

**Tests:** 20/20 86-6 tests passing (was 16; +4 new). Regression green: table + rig + table-dispatch + road_warrior CWN = 86 passed. Lint + format + pyright clean on all changed files. The Hull-has-no-production-caller and win-condition-not-wired items remain tracked Delivery Findings for 86-5/86-7 (legitimately deferred per spec §6) — NOT fixed here, by design.

**Branch:** `feat/86-6-war-rig-crew-core` (both repos) — rework pushed.

**Handoff:** Back to review.

## Subagent Results (Round 1 — archived)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 blocking + 1 secondary (tests 83/0/0 green, lint/fmt/pyright clean) | confirmed 2 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 8 | confirmed 5, deferred 3 |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 | confirmed 3, deferred 3 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 (both rule 10) | confirmed 2 |

**All received:** Yes (4 enabled returned; 5 disabled via settings)
**Total findings:** 8 confirmed (2 blocking), 6 non-blocking confirmed, 8 deferred/dismissed-with-rationale

### Disabled-subagent domains (assessed manually by Reviewer)
- **[EDGE]** edge_hunter disabled — manual pass: armor≥amount floor (`max(1, …)`) scratches for 1 (untested but correct); single-seat degenerate deal works (bypasses the ≥2 guard intentionally); **the cooperative showdown-after-`max_decision_points` picks `contenders[0]` by `strength()==0` tie — a meaningless "winner" for a crew, but harmless narration_hint and out of 86-6 scope (win-condition integration deferred).** No crashing edge found.
- **[SILENT]** silent_failure_hunter disabled — manual pass: no swallowed exceptions; every error path raises `ValueError` (vessel_id blank, negative amount/armor, unknown verb, unknown kind). The registration gap fails LOUD in prod (`UnknownTableGameError`) — not a silent fallback, but a hard break. Clean on silent-failure axis.
- **[TYPE]** type_design disabled — manual pass: pyright 0 errors; `strength()→int`, `WarRigHull` fully validated (pydantic `extra=forbid` + bounds), `TableGame.custom_beat` typed with `TYPE_CHECKING` guard. No new stringly-typed surface beyond the pre-existing `beat_id: str` on `TableCommit`.
- **[SEC]** security disabled — manual pass: no untrusted-input boundary in the diff; `rules.yaml` is static content validated by genre pydantic models at load; no injection/eval/deserialization surface. Clean.
- **[SIMPLE]** simplifier disabled — manual pass: no over-engineering; per-occupant `crash_event` emission is justified. One note: marking ALL occupants injured+dismounted (even fully-spared ones) mirrors the solo `handle_rig_crash` precedent — consistent, not redundant. The test-only Hull seam is staged scaffolding, not dead code (see Delivery Findings).

## Reviewer Assessment (Round 1 — REJECTED, superseded by Round 2 below)

**Verdict:** REJECTED

**Blocking rationale:** The feature does not work in production. `war_rig_crew` is never registered in any production code path — it self-registers at module import (`war_rig.py:101`) but nothing in production imports the module. `table/__init__.py` (lines 27-31) registers `poker` and `auction` via side-effect imports; `war_rig` is absent. The all-green test suite is a false positive: every test imports `sidequest.game.table.war_rig` *directly* inside the test body, which masks the gap. The first production turn that resolves a road_warrior `war_rig` confrontation (`instantiate_table_encounter` → `deal_table("war_rig_crew")` → `get_table_game`) will raise `UnknownTableGameError` and 500 the turn. This violates **AC1** ("registered, resolvable like poker/auction"), CLAUDE.md **"Verify Wiring, Not Just Existence,"** and **"Every Test Suite Needs a Wiring Test."** Found independently by `reviewer-preflight`, `reviewer-rule-checker`, and Reviewer's own grep.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [CRITICAL] | `war_rig_crew` kind never registered in production — `UnknownTableGameError` at runtime on any war_rig turn | `sidequest-server/sidequest/game/table/__init__.py:31` | Add `from sidequest.game.table import war_rig as _war_rig  # noqa: E402,F401` to the package side-effect import block |
| [HIGH] | The registration test imports the module directly, masking the wiring gap — it is not a true wiring test | `sidequest-server/tests/game/table/test_war_rig.py:88-97` | Strengthen `test_war_rig_crew_kind_is_registered` to import ONLY the package (`import sidequest.game.table`) and assert `get_table_game("war_rig_crew")` resolves — so it fails RED on the unregistered state and guards the regression |
| [MEDIUM] | OTEL wiring tests assert membership/truthy, not count — partial fan-out / silent verb no-ops pass undetected | `tests/integration/test_war_rig_crew_combat.py:170,295` | `crash_event` → assert count == len(occupants); `table_ops` → assert count == 3 (one per station verb) and the specific ops appear |
| [MEDIUM] | No negative test for an unknown war_rig station verb hitting `WarRigCrewTableGame.custom_beat` (distinct ValueError path from the ABC default) | `tests/game/table/test_war_rig.py` | Add a test committing `beat_id="fly"` to a war_rig_crew table and assert `pytest.raises(ValueError)` |
| [MEDIUM] | `war_rig.py` declares no `__all__` (companion `war_rig_combat.py` does) — unclear public API, rule-10 violation | `sidequest-server/sidequest/game/table/war_rig.py:1` | Add `__all__ = ["WarRigCrewTableGame", "WAR_RIG_STATIONS", "WAR_RIG_STATION_VERBS"]` |
| [LOW] | Missing armor≥amount floor test and mixed-save (one pass / one fail) crash test | `tests/integration/test_war_rig_crew_combat.py` | Add `apply_war_rig_hull_damage(hull, 3, armor=5, …)` → 1-point scratch; add `crash_save_outcomes=(True, False)` → exactly half-max HP loss |
| [LOW] | Docstring overclaims: `vessel_id` "carried explicitly for downstream consumers" (no SPAN_ROUTES lambda extracts it); `strength()` "cooperative victory lives on the Hull" (win_condition is `table_showdown`, Hull not wired as win condition) | `sidequest-server/sidequest/game/war_rig_combat.py:12,62`; `war_rig.py:64` | Tighten docstrings to match actual span routing and the deferred win-condition state |

**Findings by source (dispatch tags):**
- **[RULE]** (rule-checker, confirmed 2): R1 `war_rig` unregistered in `__init__.py` (rule 10) — CRITICAL; `war_rig.py` no `__all__` (rule 10) — MEDIUM. All other 13 checks + No-Silent-Fallbacks/No-Stubbing/OTEL additional rules: COMPLIANT (67 instances checked).
- **[TEST]** (test-analyzer, confirmed 5): masking registration test (HIGH, escalated to blocking), weak crash_event/table_ops assertions (MEDIUM×2), missing unknown-verb negative (MEDIUM), missing armor-floor/mixed-save (LOW×2). Deferred: `assert all(stations)` redundancy, asyncio.sleep flakiness (inherited from 86-2), malformed-rules fail-loud test (low value).
- **[DOC]** (comment-analyzer, confirmed 3): `vessel_id` overclaim (LOW), `strength()`/win-condition docstring (LOW), rules.yaml dormant-crash contradiction (MEDIUM, Delivery Finding). Deferred: module-docstring omits `strength()`, "half max HP" cross-module claim, custom_beat 86-6 reference (all LOW polish).
- **[EDGE]** (disabled; manual): cooperative showdown picks meaningless `contenders[0]` winner after max_decision_points — out of scope, noted. No crashing edge.
- **[SILENT]** (disabled; manual): clean — all error paths raise; no swallowed exceptions.
- **[TYPE]** (disabled; manual): clean — pyright 0 errors; validated models; TYPE_CHECKING guard correct.
- **[SEC]** (disabled; manual): clean — no untrusted-input boundary; static YAML validated at load.
- **[SIMPLE]** (disabled; manual): clean — no over-engineering; Hull seam is staged scaffolding (Delivery Finding), not dead code.

**Data flow traced:** road_warrior `war_rig` confrontation (`rules.yaml`, `table_game: war_rig_crew`) → `instantiate_table_encounter` (`encounter_lifecycle.py:840` reads `cdef.table_game`) → `deal_table` (`engine.py:858` → `get_table_game(state.game_kind)`). **Break point:** `get_table_game("war_rig_crew")` raises `UnknownTableGameError` because the kind was never registered in the production import chain. The flow is severed at the registry lookup — the feature is unreachable end-to-end.

**Pattern observed:** Side-effect registration via package `__init__.py` imports (`table/__init__.py:30-31`) is the established pattern for poker/auction; the new kind correctly self-registers but the registration *trigger* (the `__init__` import) was omitted — a classic "register-on-import but nobody imports" gap.

**Error handling:** Fail-loud discipline is otherwise excellent — `WarRigHull` validates bounds + blank vessel_id (`war_rig_combat.py:73`), `apply_war_rig_hull_damage` rejects negative amount/armor (`war_rig_combat.py:227`), `custom_beat` rejects unknown verbs (`war_rig.py:88`). The registration gap is itself fail-loud (raises, not silent) — but it raises at the worst time (live play) instead of being caught by a wiring test.

### Devil's Advocate

Suppose I am wrong and this should ship. The counter-case: the engine, the kind, and the Hull are all genuinely built and unit-true; the only missing piece is one import line; the content loads; 83 tests are green. Isn't this a "minor wiring nit" fixable in a follow-up? No — and here is why the devil loses. The single most load-bearing rule in this codebase is "Verify Wiring, Not Just Existence," written precisely because Claude is excellent at producing convincing green tests over code that never runs in production. This PR is the textbook instance: a content author (Jade, per CLAUDE.md) ships a `war_rig` world tomorrow, a player triggers the confrontation, and the turn 500s with `UnknownTableGameError` — the exact "why isn't this quite right" failure the No-Silent-Fallbacks/wiring doctrine exists to prevent. The fact that the *tests* go green while *production* breaks is not a mitigating detail; it is the aggravating one, because it means the test suite actively lies. A malicious or merely unlucky user does nothing exotic — they just play the feature as authored. A confused author reads `rules.yaml`, sees `table_game: war_rig_crew` wired and a docstring saying "resolvable like poker/auction," and trusts it. What would a stressed runtime produce? A hard crash mid-session, the worst possible place. Worse, the Hull combat — the dramatic payload of the whole story (crew sharing a Hull, crash fan-out) — has no production caller at all, so even after the import is fixed, "shoot" emits a `table.commit` span and does nothing to any Hull. That second gap is arguably in-scope-deferred per spec §6, and I accept it as a tracked Delivery Finding — but it compounds the picture: shipping now would put a feature in front of the playgroup that is, end to end, inert-to-broken. The honest call is REJECT, fix the registration + its guarding wiring test, tighten the OTEL/negative assertions so the next green is a *true* green, then re-review. Rejection here is not pedantry; it is the doctrine doing its job.

**Handoff:** Back to TEA (RED rework) — the fix requires a corrected wiring test (import the package, assert registration) plus the strengthened OTEL/negative assertions, which fail RED on current code; Dev then makes them green with the one-line `__init__` import + `__all__`.
---

## Subagent Results (Round 2 — re-review of rework)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (20/20 primary, 86/86 regression, lint/fmt/pyright clean; blocking fix CONFIRMED live) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 3 (all LOW; 5 scrutinized areas confirmed SOUND) | confirmed 0 blocking, 3 deferred (non-blocking) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 new LOW (all 4 round-1 docstring findings RESOLVED) | confirmed 0 blocking, 2 deferred (non-blocking) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 (both round-1 rule-10 violations FIXED; 13 rules / 47 instances clean) | N/A |

**All received:** Yes (4 enabled returned; 5 disabled via settings)
**Total findings:** 0 blocking, 5 non-blocking confirmed (all LOW polish), 0 dismissed

### Disabled-subagent domains (assessed manually by Reviewer, round 2)
- **[EDGE]** disabled — manual: the rework adds the armor-floor edge test; the one remaining gap (armor-floor on a *killing* hit) is captured as a LOW Delivery Finding. No crashing edge in the delta.
- **[SILENT]** disabled — manual: rework adds no exception handling; `subprocess.run` asserts returncode with full diagnostics, no swallow. Clean.
- **[TYPE]** disabled — manual: pyright 0 errors on the delta; no new stringly-typed surface.
- **[SEC]** disabled — manual: `subprocess.run` uses `shell=False` (list form) with a hardcoded literal script — no injection surface. Clean.
- **[SIMPLE]** disabled — manual: rework is minimal and targeted (1 import line, `__all__`, doc fixes, focused tests); no over-engineering.

## Design Deviations — Reviewer re-audit (Round 2)

### Reviewer (audit — round 2)
- All three Dev deviations remain **✓ ACCEPTED** (unchanged by the rework). The two docstring caveats I attached in round 1 (vessel_id "carried explicitly"; strength() "cooperative victory lives on the Hull") were **corrected** in the rework — comment-analyzer round 2 confirms both are now accurate. The category=movement deviation is unaffected.
- The round-1 UNDOCUMENTED defect (war_rig_crew unregistered in production) is now **FIXED and guarded** by a subprocess wiring test — no longer an open audit item.
- No new undocumented deviations in the rework.

## Reviewer Assessment (Round 2 — re-review of rework)

**Verdict:** APPROVED

**Rework verification:** The round-1 blocking defect is fixed and proven dead. `war_rig_crew` is now registered in production via `table/__init__.py` (side-effect import alongside poker/auction), and a fresh interpreter importing ONLY the package resolves the kind (`get_table_game('war_rig_crew') → war_rig_crew`, was `UnknownTableGameError`). Critically, the masking false-green is gone: the new subprocess-isolated `test_war_rig_crew_registered_via_production_package_import` imports only the package (never the module directly) and fails RED if the `__init__` import is removed — verified by Dev reverting it. Both round-1 rule-10 violations (registration, missing `__all__`) are confirmed fixed by the rule-checker. All four round-1 docstring/comment findings are confirmed RESOLVED by the comment-analyzer.

**Data flow re-traced:** road_warrior `war_rig` confrontation (`rules.yaml`, `table_game: war_rig_crew`) → `instantiate_table_encounter` → `deal_table` → `get_table_game("war_rig_crew")` → **resolves** (the registry is populated by the package `__init__` side-effect import on first production import). The flow is now intact end-to-end at the table-engine layer.

| Severity | Issue | Location | Disposition |
|----------|-------|----------|-------------|
| [LOW] | unknown-verb test doesn't pin the ValueError message (would pass vacuously only if the ABC default were changed to ValueError — current code is falsifiable) | `tests/game/table/test_war_rig.py` (test_war_rig_unknown_station_verb_fails_loud) | Non-blocking — optional `match=` hardening (Delivery Finding) |
| [LOW] | no test for armor-floor on a *killing* hit (floored 1-point hit that destroys the Hull) | `tests/integration/test_war_rig_crew_combat.py` | Non-blocking — coverage gap (Delivery Finding) |
| [LOW] | `_crash_occupant` docstring says "matching the solo handler's *unconditional* appends" but impl uses idempotency guards | `sidequest/game/war_rig_combat.py` | Non-blocking — doc precision (Delivery Finding) |
| [LOW] | `strength()` docstring "picks contenders[0] by position" — actually `max()` stability on equal keys | `sidequest/game/table/war_rig.py` | Non-blocking — doc precision (Delivery Finding) |

**Findings by source (dispatch tags):**
- **[RULE]** (rule-checker): CLEAN — both round-1 violations FIXED, 0 new across 13 rules / 47 instances. "Verify Wiring" + "Every Test Suite Needs a Wiring Test" + OTEL + No-Silent-Fallbacks + No-Stubbing all explicitly re-confirmed compliant.
- **[TEST]** (test-analyzer): 5 scrutinized areas SOUND (subprocess wiring test, package-import fix, unknown-verb path, OTEL count/beat_id assertions, armor-floor/one-save arithmetic). 3 LOW hardening findings, deferred.
- **[DOC]** (comment-analyzer): all 4 round-1 findings RESOLVED; 2 new LOW doc-precision nits, deferred.
- **[EDGE]/[SILENT]/[TYPE]/[SEC]/[SIMPLE]** (disabled; manual): clean — see disabled-domain notes above.

### Devil's Advocate

Could I be rubber-stamping a fix I requested? Let me argue the rework is still broken. First attack: "the subprocess test is theater — it passes now but doesn't really guard anything." Refuted: Dev empirically reverted the `__init__` import and the subprocess test failed RED; I re-verified the package-only import resolves the kind in a fresh interpreter myself. It is a real guard. Second attack: "the kind is registered but the feature still does nothing in production — the Hull has no caller, so a `war_rig` turn resolves station verbs as empty spans." Partially true, and I do not wave it away — but it is a *deliberate, documented scope boundary* (spec §6: full vessel stat blocks, mount_slot remap, and the verb→Hull and showdown→Hull integration are 86-5/86-7), now captured as tracked Delivery Findings rather than silent dead code. 86-6's contract was: register the kind, add the custom-beat seam, build the vessel Hull + crash fan-out, prove the spans fire through the real route. All four are now true and wired at the layer this story owns. Third attack: "two docstrings are still imprecise and the tests have coverage gaps — reject again." That is the inflation trap my own round-1 sidecar warns against: four LOW-severity polish items on a correct, end-to-end-wired (at its layer), rule-clean, green implementation do not meet the Critical/High bar, and a second rejection would be process waste that teaches nothing. The honest disposition is APPROVE and capture the LOW items as fast-follow. The blocking issue that mattered — a feature that 500s in production behind green tests — is fixed and can never silently regress again because the wiring test now lives in a subprocess. The doctrine has been satisfied, not gamed.

**Handoff:** To SM for finish-story.