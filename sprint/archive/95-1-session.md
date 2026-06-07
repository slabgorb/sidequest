---
story_id: "95-1"
jira_key: ""
epic: "null"
workflow: "tdd"
---
# Story 95-1: Region→orbital-scope binding + perseus_cloud sector orrery content

## Story Details
- **ID:** 95-1
- **Jira Key:** (not in use)
- **Workflow:** tdd
- **Stack Parent:** none
- **Branch Strategy:** gitflow (feat/95-1-region-orbital-scope-binding)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-07T01:32:27Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-07T00:24:37Z | 2026-06-07T00:25:41Z | 1m 4s |
| red | 2026-06-07T00:25:41Z | 2026-06-07T00:42:19Z | 16m 38s |
| green | 2026-06-07T00:42:19Z | 2026-06-07T01:05:11Z | 22m 52s |
| review | 2026-06-07T01:05:11Z | 2026-06-07T01:13:19Z | 8m 8s |
| red | 2026-06-07T01:13:19Z | 2026-06-07T01:19:30Z | 6m 11s |
| green | 2026-06-07T01:19:30Z | 2026-06-07T01:24:16Z | 4m 46s |
| review | 2026-06-07T01:24:16Z | 2026-06-07T01:32:27Z | 8m 11s |
| finish | 2026-06-07T01:32:27Z | - | - |

## Sm Assessment

Story 95-1 set up for TDD (phased). 5pt, p2. Two-repo touch (sidequest-server primary, sidequest-content secondary). Content half (perseus_cloud orbits.yaml, 140 bodies) is ALREADY MERGED in sidequest-content#383 — remaining work is server-side: bind region→orbital scope so the per-location orrery auto-centers on the party's current system.

**Scope for TEA/Dev:**
- Identity join is the lever: star body-id == cartography region-id by construction (region 'yula' → star body 'yula').
- Region truth: `snapshot.pc_regions[player_name]`, mutated via `WorldStatePatch(pc_region=...)` at `agents/subsystems/movement.py:367` and `server/narration_apply.py:3164`.
- Scope state: `server/session.py` `orbital_scope` + `snapshot.party_body_id`; session-bind path `server/session_room.py` bind_world.
- v1 design decision: pc_regions is per-PC but party_body_id is singular → bind to the ACTING/seated PC's region on each pc_region change. Stricter MP cross-system co-location deferred.

**Out of scope:** 'set a course' travel mechanics; chart.yaml flavor layer.

**OTEL:** Per CLAUDE.md, the scope-bind decision MUST emit a watcher event so the GM panel can verify the chart re-centered — not just trust the narration. No-Silent-Fallbacks: unknown/missing region→body mapping must fail loud, not silently leave the chart un-centered.

**Refs:** ADR-094 (orrery), ADR-130 (orbital clock).

Routing to Amos (TEA) for RED phase.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (8/8 failing — verified via `uv run pytest -n0`, run id 95-1-tea-red)

**Test Files:**
- `sidequest-server/tests/orbital/test_scope_bind.py` — 7 unit tests on the binding MECHANISM (synthetic `world_sector_join` fixture, Session-level contract).
- `sidequest-server/tests/server/test_region_orbital_scope_wiring.py` — 1 integration/wiring test driving the real `_apply_narration_result_to_snapshot` (Site B) seam with OTEL span assertion.
- `sidequest-server/tests/orbital/fixtures/world_sector_join/orbits.yaml` — new synthetic hub→stars→planet fixture (loads cleanly; star ids `yula`/`vorn` = region ids, `ceron` deliberately star-less).

**Contract pinned for Dev (GREEN):**
`Session.bind_region_scope(region_id: str, *, trigger: str) -> bool`
- MATCH → set `snapshot.party_body_id` + `session.orbital_scope = Scope(center_body_id=body_id)`, emit `orbital.scope_bind{region_id, body_id, trigger}`, return True.
- NO MATCH + `trigger="init"` → raise `RegionScopeBindError` (No Silent Fallbacks; never silent system_root).
- NO MATCH + `trigger="relocation"` → no mutation, emit `orbital.scope_bind_skipped{region_id, reason}`, return False.
- `orbital_content is None` → no-op skip (return False), no crash (regression guard for non-orbital worlds).
- `RegionScopeBindError` home: prefer `sidequest/orbital/scope_bind.py`, fallback `sidequest/server/session.py` (test uses an import shim).

**AC coverage map:**
| AC | Covered by | Notes |
|----|-----------|-------|
| Content load + 34/34 join | synthetic mechanism test + Delivery Finding | perseus-specific count → content validator (deviation logged) |
| Bind-on-init (match + fail-loud no-match) | `test_bind_init_*` | init home = connect.py:665 (Delivery Finding) |
| Bind-on-relocation (re-center + loud skip) | `test_bind_relocation_*` + Site-B wiring test | Site A (movement) = blocking Delivery Finding |
| OTEL scope_bind / scope_bind_skipped | `test_bind_emits_*` + wiring span assert | dotted span names per `orbital.*` convention |
| Wiring (real relocation through handler) | `test_region_relocation_recenters_orrery_and_emits_span` | OTEL + behavior, no source-text grep |
| Scope guard (no travel/chart.yaml; coyote_star unchanged) | None-content no-op guard + existing byte-identical render tests | no new chart.yaml authored |

### Rule Coverage (python lang-review)
| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions (No Silent Fallbacks) | `test_bind_init_no_matching_star_fails_loud`, `test_bind_relocation_no_matching_star_leaves_scope_unchanged` | failing (RED) |
| #4 logging coverage (loud skip) | `test_bind_skip_emits_scope_bind_skipped_span` | failing (RED) |
| #6 test quality (no vacuous asserts) | self-check below; wiring test asserts `orbital_content is not None` guard against vacuous None-content pass | n/a |

**Rules checked:** 3 of 13 lang-review rules are materially applicable to this behavior (fail-loud, loud-skip logging, test quality); the rest (resource leaks, deserialization, async, deps) don't apply to a pure in-memory binding.
**Self-check:** No vacuous assertions. The wiring test includes an explicit `assert room.session.orbital_content is not None` so it cannot silently pass against a None-content no-op.

**Handoff:** To Dev (Naomi) for GREEN. Two blocking wiring decisions (movement Site-A Session access; init bind home at connect.py) are in Delivery Findings — Dev should resolve those, not just the unit-method, to fully satisfy the "both seams" AC.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (blocking): The movement seam (Site A, `agents/subsystems/movement.py:367` via `snapshot.apply_world_patch`) has NO `Session`/`orbital_content` reference — `run_movement_dispatch` receives only `snapshot`, `dispatch`, `dungeon_store`, `palette`, `lookahead_handle`, `pack`. It therefore cannot re-center `session.orbital_scope` (a Session attribute) on a procedural region move. The "both seams" AC (bind-on-relocation) cannot be met until Dev/Architect threads the Session (or `room`) into the movement dispatch context, or moves the bind to a layer that has it. Affects `sidequest/agents/subsystems/movement.py` + `sidequest/agents/subsystems/__init__.py` (`run_dispatch_bank` context). *Found by TEA during test design — Site A wiring test deferred to a Delivery Finding rather than a fabricated brittle test.*
- **Gap** (blocking): Bind-on-init has no existing home — `SessionRoom.bind_world` (`session_room.py:225`) does NOT receive cartography; its signature is `(snapshot, store, world_dir, ruleset)`. The starting_region lives on `genre_pack.worlds[world].cartography.starting_region`. The only production point where BOTH cartography and `room.session` are in scope is `handlers/connect.py:665` (immediately after `bind_world`). Dev must call the init bind there (or extend `bind_world` to take cartography). Affects `sidequest/handlers/connect.py` (post-bind init call). *Found by TEA during test design.*
- **Improvement** (non-blocking): AC-1's perseus_cloud-specific content assertion (one parent-less root + 34/34 star→region identity join, ceron excepted) is a CONTENT invariant, not engine behavior — per the project "no content in unit tests" rule it belongs in the sidequest-content pack validator, not server pytest. The binding MECHANISM (region id → matching star body re-centers scope) is covered here by the synthetic `world_sector_join` fixture. Affects `sidequest-content` pack validator (add an orbital-join check for region-mode worlds with orbital_content). *Found by TEA during test design.*
- **(Rework r1) Gap** (non-blocking): `CartographyConfig.starting_region` defaults to `str = ""` with no non-empty validation (`world.py:255`). The engine now fails loud at init bind for an orbital world with a blank starting_region (the new RED test), but the *content* layer never catches it earlier. The sidequest-content pack validator should reject an orbital-tier (orbital_content present), region-mode world whose `cartography.starting_region` is blank or not a body id — so authors get the error at validation time, not connect time. Affects `sidequest-content` pack validator. *Found by TEA during rework test design.*

### Dev (implementation)
- **Gap** (non-blocking): The content-validator orbital-join check TEA proposed (and the AC-1 wording) should validate region→**body** identity, not region→**star** specifically. coyote_star's `starting_region: far_landing` joins a `type: habitat` body, and the engine now matches any body type by id; a star-only validator check would false-flag every single-system orbital world. Affects `sidequest-content` pack validator. *Found by Dev — surfaced when the star-only match broke the coyote_star regression guard (`test_mp_new_player_connect_does_not_auto_seat`).*
- **Resolved (was TEA blocking — Site A)**: The movement.py Site-A bind is not needed. `run_movement_dispatch` early-returns with a `movement.region_mode` span (movement.py:143) for region-mode worlds BEFORE the `apply_world_patch(pc_region=...)` line (:367). All orbital worlds are region-mode, so Site A only mutates pc_region for room-graph/dungeon worlds, which have no orbital tier — a Site-A bind would be an unconditional no-op there. No Session threading was added; the "both seams" requirement collapses to Site B for every world this feature applies to. *Resolved by Dev via investigation, not wiring (see Design Deviations).*
- **Resolved (was TEA blocking — init home)**: Bind-on-init wired via `_bind_initial_orbital_scope(...)` after both `bind_world` sites in connect.py (fresh = starting_region/init fail-loud; resume = current_region/relocation loud-skip). `bind_world` was NOT extended to take cartography. *Resolved by Dev.*
- **Question** (non-blocking): No connect-level integration test exercises bind-on-init with an orbital world fixture (the orbital init path is covered indirectly by the coyote_star MP connect regression passing through it). A future fixture-driven connect test would lock in fresh-vs-resume re-centering semantics. Affects `tests/server/` (new orbital-connect fixture). *Found by Dev during implementation.*
- **(Rework r1) Resolved** (Reviewer HIGH): blank `starting_region` now fails loud — `_bind_initial_orbital_scope` fresh path is an unconditional `else` calling `bind_region_scope(starting_region or "", trigger="init")`, so a blank/foreign starting_region on an orbital world raises `RegionScopeBindError` instead of silently skipping. *Resolved by Dev in rework.*
- **(Rework r1) Resolved** (Reviewer MEDIUM): the fresh-connect init bind is wrapped in `try/except RegionScopeBindError` → typed `[_error_msg(code="orbital_scope_bind_failed")]` + `orbital_scope_bind_failed` watcher event, so a content-misconfigured orbital world returns an actionable connect error instead of an unhandled socket close. *Resolved by Dev in rework.*

### Reviewer (code review)
- **Gap** (blocking): `_bind_initial_orbital_scope` fresh-session path `elif starting_region:` silently skips the init bind when `starting_region` is blank (`CartographyConfig.starting_region` defaults to `str = ""`). An orbital world that omits `starting_region` gets a silently-uncentered chart with no raise/span/log — violates No Silent Fallbacks and the bind-on-init AC. Affects `sidequest/handlers/connect.py:307` (raise loud on blank starting_region for an orbital world). *Found by Reviewer during code review.*
- **Gap** (non-blocking): Fail-loud `RegionScopeBindError` from the fresh-connect init bind propagates unhandled — every other load failure in `ConnectHandler.handle` returns a typed `[_error_msg(...)]`; this one closes the socket with a raw traceback. Affects `sidequest/handlers/connect.py:763` (wrap the fresh init bind, return a typed error + watcher event). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `trigger: str` on `bind_region_scope` is an open extension point — an unknown trigger is silently treated as a relocation loud-skip. A `Literal["init", "relocation"]` or an explicit `ValueError` guard would catch call-site typos. Affects `sidequest/server/session.py:158`. *Found by Reviewer (corroborated by preflight + edge-hunter).*
- **(Rework r1, APPROVED) Improvement** (non-blocking): `test_init_bind_noop_for_non_orbital_world` asserts `party_body_id is None` — the default value (weak). Its load-bearing assertion (no-raise on blank starting_region for a non-orbital world) is genuine, but the mutation-absence check should pre-set a sentinel. Affects `tests/server/test_connect_orbital_init_bind.py`. *Found by Reviewer (test-analyzer) during re-review.*
- **(Rework r1, APPROVED) Gap** (non-blocking): the connect `except RegionScopeBindError` branch (logger + `orbital_scope_bind_failed` watcher event + typed `_error_msg`) has no automated test. The watcher-event half is testable without the Postgres handler harness; add a no-DB test asserting the `orbital_scope_bind_failed` span fires. Affects `tests/server/`. *Found by Reviewer (test-analyzer) during re-review.*
- **(Rework r1, APPROVED) Improvement** (non-blocking): `_bind_initial_orbital_scope`'s `cartography is None` early-return (connect.py:300) is non-reachable for loaded orbital worlds (`World.cartography` is a required field), but a defensive `raise` there would make the invariant explicit if the world model ever changes. Affects `sidequest/handlers/connect.py:300`. *Found by Reviewer (silent-failure-hunter) during re-review — non-reachable today.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC-1 perseus content-join not covered by a server pytest**
  - Spec source: context-story-95-1.md, AC-1
  - Spec text: "perseus_cloud orbits.yaml ... loads cleanly through load_orbital_content: exactly one parent-less root, and every type=star child of the root has a body-id matching a cartography region id (34/34 join, ceron excepted)."
  - Implementation: The join MECHANISM is tested with a synthetic `world_sector_join` fixture (hub→stars yula/vorn→planet) in `tests/orbital/test_scope_bind.py`; the perseus-specific 34/34 assertion is delegated to the content pack validator (Delivery Finding) instead of a server unit test.
  - Rationale: Project rule "content invariants go in the pack VALIDATOR, never unit tests." Hardcoding perseus body counts in pytest couples engine tests to shipped content and rots on every content edit.
  - Severity: minor
  - Forward impact: Content validator must gain an orbital-join check (logged as non-blocking Delivery Finding); engine behavior is fully covered.
- **Site A (movement) relocation wiring test omitted**
  - Spec source: context-story-95-1.md, AC bind-on-relocation ("both the movement.py router seam and the narration_apply.py seam")
  - Spec text: "when a pc_region change lands for the acting PC (both the movement.py router seam and the narration_apply.py seam), party_body_id and orbital_scope re-center on the matching star body."
  - Implementation: Only the Site B (narration_apply) seam has a drivable wiring test (`tests/server/test_region_orbital_scope_wiring.py`). Site A is currently undrivable (no Session in the movement dispatch context) and is captured as a blocking Delivery Finding instead of a test.
  - Rationale: Writing a Site-A test today would require asserting against wiring that does not yet exist and whose shape is an open Architect decision; a fabricated test would be brittle and prescriptive. The RED contract is pinned at the Session-method + Site-B levels; Dev must add the Site-A wiring test once the Session-threading decision is made.
  - Severity: major
  - Forward impact: Dev/Architect must thread the Session into the movement path AND add the Site-A relocation wiring test in GREEN before AC bind-on-relocation is fully satisfied.
- **(Rework r1) Connect-graceful-error wrap (Reviewer MEDIUM #2) pinned at the helper level, not the full ConnectHandler**
  - Spec source: Reviewer Assessment (round-trip 1), MEDIUM finding — "wrap the fresh init bind, return a typed `_error_msg` + watcher event instead of an unhandled RegionScopeBindError socket close."
  - Spec text: "Fail-loud RegionScopeBindError from the fresh init bind propagates unhandled ... return a typed `[_error_msg(...)]`."
  - Implementation: The RED contract is pinned at `_bind_initial_orbital_scope` (it must RAISE on a blank/no-match starting_region — `test_init_bind_fresh_blank_starting_region_fails_loud`). No automated test drives the full `ConnectHandler.handle` typed-error response, because that path requires the Postgres-backed handler harness (`migrated_db` + real genre-pack load) and a deliberately-misconfigured orbital world fixture — disproportionate for a MEDIUM/non-blocking polish.
  - Rationale: The Reviewer sanctioned direct-call helper tests over the full handler. The HIGH defect (silent skip) is fully driven by the helper-raises test. The MEDIUM graceful-wrap is a connect-layer try/except around the documented raise; Dev should add it, verified by the helper-raise contract + a connect smoke. A brittle DB-backed handler test for a content-misconfig error path is not worth its maintenance cost.
  - Severity: minor
  - Forward impact: Dev should wrap the fresh-connect `_bind_initial_orbital_scope` call to catch `RegionScopeBindError` and return a typed error + watcher event. If the graceful wrap is skipped, the failure is still LOUD (unhandled raise), just less graceful — so this does not re-open the No-Silent-Fallbacks blocker.

### Dev (implementation)
- **Site A (movement.py) bind NOT wired — it is unreachable for orbital worlds, not merely deferred**
  - Spec source: context-story-95-1.md, AC bind-on-relocation ("both the movement.py router seam and the narration_apply.py seam"); TEA blocking Delivery Finding (Site A undrivable, needs Session threading)
  - Spec text: "when a pc_region change lands for the acting PC (both the movement.py router seam and the narration_apply.py seam), party_body_id and orbital_scope re-center on the matching star body."
  - Implementation: Wired the relocation bind ONLY at Site B (`narration_apply._apply_narration_result_to_snapshot`). Site A (`agents/subsystems/movement.py` `apply_world_patch`) was intentionally left unwired after investigation — `run_movement_dispatch` early-returns with a `movement.region_mode` span for region-mode worlds (movement.py:143, `_is_region_mode_world`) BEFORE reaching the `apply_world_patch(pc_region=...)` line at :367. All orbital worlds are region-mode (perseus_cloud + coyote_star both `navigation_mode: region`), so the Site-A pc_region mutation only ever fires for procedural room-graph/dungeon worlds, which by design have no orbital tier (`orbital_content is None`). A bind at Site A would therefore be an unconditional no-op for every world that has a chart to re-center. No Session threading into the movement context was needed; the "both seams" concern collapses to Site B for any world this feature applies to.
  - Rationale: Adding Session/orbital_content plumbing through `run_movement_dispatch` + `run_dispatch_bank` to call a method that provably can't do anything (no orbital world reaches that code path) would be dead wiring — worse than no code per the No-Stubbing principle. The region-mode early-return is the architectural fact that resolves TEA's blocking finding.
  - Severity: major
  - Forward impact: If a future world ever pairs room-graph navigation WITH an orbital tier (none exists today), Site A would need the bind. That world does not exist; documenting the precondition here so the assumption is visible if it ever changes.
- **Match criterion is region-id == any orbital body, not specifically a `type=star` body**
  - Spec source: context-story-95-1.md, AC bind-on-init / bind-on-relocation ("matching star body"); RED contract in TEA Assessment
  - Spec text: "re-center on the matching star body. A region with no matching star body (e.g. ceron) leaves scope unchanged."
  - Implementation: `bind_region_scope` matches when `region_id in orbital_content.orbits.bodies` (any `BodyType`), not when the body is specifically `type=star`. Both interpretations pass all 8 RED tests (the fixture's no-match region `ceron` has NO body entry at all; the only non-star body `yula_anchorage` is never exercised as a region). A star-only restriction was implemented first and broke the coyote_star regression guard: coyote_star's `starting_region: far_landing` resolves to a `type: habitat` body (orbits.yaml:33), so connect-time init binding raised `RegionScopeBindError` and failed `test_mp_new_player_connect_does_not_auto_seat`.
  - Rationale: The "star body" language describes perseus_cloud's authoring convention (sector stars are the region anchors), not the general mechanism. The orrery centers on the party's LOCATION body, which is a star in a sector world and a habitat/station/planet in a single-system world. The AC's explicit "existing coyote_star orrery behavior is unchanged (regression-safe)" guard takes precedence (spec-authority: an AC that breaks is higher signal than a descriptive phrase in a sibling AC).
  - Severity: minor
  - Forward impact: The content-validator orbital-join check (TEA non-blocking finding) should validate region→body identity, not strictly region→star, to match the engine. ceron-style star-less regions remain valid loud-skips.
- **Init bind threaded through `connect.py` (both resume and fresh paths), not `bind_world`**
  - Spec source: TEA blocking Delivery Finding (init bind home); AC bind-on-init
  - Spec text: "Bind-on-init: binding a region-mode world that has orbital_content initializes snapshot.party_body_id and session.orbital_scope from cartography.starting_region."
  - Implementation: Added `_bind_initial_orbital_scope(room, genre_pack, world_slug, is_resume)` called after both `bind_world` sites in `connect.py`. Fresh sessions bind from `cartography.starting_region` with `trigger="init"` (fail-loud). Resume binds from the party's persisted `current_region` (fallback `starting_region`) with `trigger="relocation"` (loud-skip) — re-centering on the party's ACTUAL location, since `orbital_scope` is transient session state that resets to system-root every connect. A single `trigger="init"` call from `starting_region` would have clobbered a resumed party's location and could fail-loud on a legitimately star-less current region.
  - Rationale: `bind_world` does not receive cartography (TEA finding); connect.py is the only point with both `room.session` and `genre_pack` in scope. Splitting init vs resume trigger semantics is required for correct resume behavior and is not covered by an automated test (no connect-level orbital fixture exists) — verified by the coyote_star MP connect test passing through the new code path without regression.
  - Severity: minor
  - Forward impact: A future connect-level integration test with an orbital world fixture would lock in resume re-centering; today it is covered indirectly by the coyote_star MP connect regression.
- **(Rework r1) Connect-graceful typed-error wrap implemented but not test-gated**
  - Spec source: Reviewer Assessment (round-trip 1) MEDIUM #2; TEA rework deviation (full-handler test omitted — DB harness disproportionate)
  - Spec text: "Wrap the fresh init bind; on RegionScopeBindError return a typed `[_error_msg(...)]` + watcher event."
  - Implementation: Wrapped the fresh-connect `_bind_initial_orbital_scope` call (connect.py) in `try/except RegionScopeBindError` → `logger.error` + `orbital_scope_bind_failed` watcher event + `return [_error_msg(..., code="orbital_scope_bind_failed")]`. The HIGH fix itself (helper fails loud on blank starting_region) IS test-gated by `test_init_bind_fresh_blank_starting_region_fails_loud`; the connect-level graceful wrap around it is NOT (TEA deviated on the full-handler test).
  - Rationale: Implemented the reviewer-requested graceful handling rather than leaving the raise to slam the socket. Mirrors the existing genre-pack / world-grounding load-failure pattern (`return [_error_msg(...)]`) directly above in the same handler, so it follows an established, reviewed shape. Skipping the DB-backed handler test matches TEA's logged deviation.
  - Severity: minor
  - Forward impact: The except branch (log + watcher + typed error) is exercised only manually / by the helper-raise unit test, not by an automated connect-handler test. If connect-error semantics are reworked later, add a handler-level test then.

### Reviewer (audit)
- **AC-1 perseus content-join → content validator** (TEA) → ✓ ACCEPTED by Reviewer: agrees — perseus body counts belong in the pack validator, not server pytest. No engine-behavior gap.
- **Site A (movement) relocation test omitted** (TEA) → ✓ ACCEPTED by Reviewer: superseded by Dev's investigation — Site A is unreachable for orbital worlds (region-mode early-return), so no Site-A test is owed.
- **Site A bind NOT wired — unreachable for orbital worlds** (Dev) → ✓ ACCEPTED by Reviewer: verified `run_movement_dispatch` early-returns at movement.py:143 for region-mode worlds before the `apply_world_patch` at :367; all orbital worlds are `navigation_mode: region`. A Site-A bind would be dead code. Sound call per No-Stubbing.
- **Match is region-id == any body, not type=star** (Dev) → ✓ ACCEPTED by Reviewer: verified coyote_star `starting_region: far_landing` is a `type: habitat` body (orbits.yaml:33). Region→body (not region→star) is correct and required by the regression-safe AC. NOTE: this body-type-agnostic behavior has NO unit test (test-analyzer [TEST] gap) — fix in rework.
- **Init bind threaded through connect.py, not bind_world** (Dev) → ✗ FLAGGED by Reviewer: the *location* of the bind is fine, but the *implementation* has a blocking hole — the `elif starting_region:` guard silently skips the fail-loud init bind when `starting_region` is blank (default `str = ""`). The deviation claims "fresh = starting_region/init (fail-loud)" but the code does NOT fail loud on a blank starting_region. See Reviewer Assessment HIGH finding. The resume-trigger split itself is sound and accepted; the blank-skip is the defect.

#### Reviewer (audit — round-trip 1 rework)
- **(Rework r1) Connect-graceful-error wrap pinned at helper level, not full ConnectHandler** (TEA) → ✓ ACCEPTED by Reviewer: the HIGH fix (helper raises on blank) IS test-gated; the connect-level typed-error wrap mirrors the existing genre-pack/world-grounding load-failure pattern and the full-handler test needs the Postgres harness — disproportionate for a MEDIUM. The graceful wrap is still a LOUD failure; skipping its automated test does not re-open the No-Silent-Fallbacks blocker. The watcher-event half is testable without Postgres → logged as a non-blocking delivery finding for future hardening.
- **(Rework r1) Connect-graceful typed-error wrap implemented but not test-gated** (Dev) → ✓ ACCEPTED by Reviewer: implementing the reviewer-requested graceful handling (vs. letting the raise slam the socket) is the right call; it follows the established `return [_error_msg(...)]` shape directly above it in the same handler. The untested except-branch is captured as a non-blocking delivery finding, not a blocker.

## Subagent Results (round-trip 0 — REJECTED, superseded)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 blockers (lint/format/type/tests all green; 3 architectural notes) | confirmed 0, dismissed 0, deferred 3 (notes) |
| 2 | reviewer-edge-hunter | Yes | findings | 6 | confirmed 2 (1 reinforces #1, 1 new MEDIUM), deferred 4 (2 medium, 2 low) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 1 (HIGH blocker), dismissed 1 (low — genre_pack never None at call sites) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 4 (3 high + 1 med coverage gaps), deferred 2 (low) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 0 | confirmed 0 — yaml.safe_load, `!r`-escaped strings, dict-key lookup, no dangerous sink |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 8 confirmed (1 HIGH blocker, 1 MEDIUM, 4 test-coverage, 2 corroborating), 1 dismissed (with rationale), 9 deferred (low/notes)

## Reviewer Analysis (round-trip 0 — REJECTED, superseded)

### Observations
- **[SILENT][EDGE][HIGH] Blank `starting_region` silently skips the fail-loud init bind** at `connect.py:307`. `CartographyConfig.starting_region` defaults to `str = ""` (`world.py:255`), with no non-empty validation. For an orbital world (orbital_content present) with cartography present but a blank starting_region, `elif starting_region:` is falsy → `bind_region_scope(..., trigger="init")` is never called → no raise, no span, no log → chart silently opens at system root. This is exactly the "silent system_root fallback" the bind-on-init AC forbids and the `<critical>` No Silent Fallbacks rule prohibits. Independently flagged by silent-failure-hunter (high) and edge-hunter (high).
- **[EDGE][MEDIUM] Fail-loud `RegionScopeBindError` propagates unhandled** from the fresh-connect init bind at `connect.py:763`. Verified: no try/except wraps the bind sites (handlers between :551 and :1044 do not cover them; `handle()` has no method-level try). A typo'd-but-non-blank starting_region raises and bubbles to the socket layer as a raw disconnect, unlike every other connect load failure which returns a typed `_error_msg`. Loud (satisfies the principle) but ungraceful for a content-authoring error.
- **[TEST][HIGH] No unit test for region→non-star-body match.** The fixture HAS `yula_anchorage` (habitat) but no test binds it. Dev specifically relaxed the match from star-only to any-body for coyote_star — the exact behavior with no direct unit lock. A regression to star-only would pass the entire unit suite (only the coyote_star MP connect test catches it, indirectly).
- **[TEST][HIGH] init-trigger span value unasserted + fail-loud span-absence unasserted.** `test_bind_emits_scope_bind_span` only checks `trigger="relocation"`; the init MATCH path makes no span assertion. The fail-loud test asserts no mutation but not that no `orbital.scope_bind` span fired. A hardcoded trigger or a span-before-raise would pass.
- **[TEST][HIGH] No connect-time integration test** for `_bind_initial_orbital_scope` (init/resume) — the production wiring that just shipped the HIGH bug. A connect-level fixture test would have caught the blank-starting_region skip.
- **[VERIFIED] OTEL spans registered + routed** — `orbital.scope_bind{,_skipped}` added to `FLAT_ONLY_SPANS` (scope_bind.py:24-29) and re-exported (`__init__.py:100`); `test_routing_completeness` passes. Complies with the OTEL Observability principle on the happy + loud-skip paths (the gap is the silent path above). Evidence: preflight OTEL ROUTING check green.
- **[VERIFIED] yaml.safe_load** in the orbital loader (security clean) — no unsafe deserialization introduced. Evidence: security subagent + loader.py.
- **[VERIFIED] Site B fires only on real region change** — bind is inside `if _is_region_mode_world and snapshot.current_region != known_region_id` (narration_apply.py:3169). No spurious binds. Evidence: wiring test green; diff read.
- **[LOW][EDGE] `<root>` sentinel on resume** — `current_region or starting_region` doesn't exclude `"<root>"`; a session saved at system-root emits a spurious `scope_bind_skipped` instead of falling back to starting_region. Non-blocking polish.
- **[LOW][EDGE] `room.session` race at narration_apply:3221** — unguarded deref raises RuntimeError if `close_store()` nulled `_session` mid-flight. Narrow, and consistent with the established unguarded pattern elsewhere; pre-existing class of race. Non-blocking.

### Rule Compliance
- **No Silent Fallbacks (`<critical>` CLAUDE.md + bind-on-init AC):** `Session.bind_region_scope` — COMPLIANT (init raises, relocation emits skip span, None-content is a documented no-op). `_bind_initial_orbital_scope` fresh path — **VIOLATION** at connect.py:307 (blank starting_region silently skipped). This is the blocking finding.
- **OTEL Observability (every subsystem decision emits a span):** happy bind + loud-skip — COMPLIANT (scope_bind / scope_bind_skipped). Fail-loud init raise — acceptable (the exception is the signal). Silent blank-skip — VIOLATION (no span). 
- **No Source-Text Wiring Tests:** wiring test asserts behavior + OTEL span, no source grep — COMPLIANT (test_region_orbital_scope_wiring.py).
- **Every test suite needs a wiring test:** present (Site B) — COMPLIANT for relocation; the connect-time init wiring is untested — GAP (non-blocking, rolled into rework).
- **No content in unit tests:** synthetic fixture used, perseus counts deferred to validator — COMPLIANT.
- **No Stubbing / dead code:** Site A correctly not wired (unreachable) — COMPLIANT. The `_bind_error_cls` fallback branch in the test is now dead (Dev chose the orbital home) but it is test-only import-shim scaffolding, harmless — LOW.
- **Type annotations at boundaries:** all new public functions annotated — COMPLIANT; `trigger: str` is loose but annotated (Literal would be stricter — LOW).

### Devil's Advocate
Assume this code is broken. The most damning path: a content author — say Jade, the first non-Keith author, exactly the load-bearing homebrew persona — builds a new sector world. She copies perseus_cloud's `orbits.yaml`, writes her `cartography.yaml`, and forgets (or typos the key of) `starting_region`. The pydantic model does not stop her: `starting_region: str = ""` happily defaults to empty. She boots the world. The orrery opens at the sector root — not her party's start system — and there is **nothing** anywhere to tell her why: no exception, no `scope_bind_skipped` span, no log line, no GM-panel event. She burns an evening diffing her YAML against perseus_cloud's, exactly the "why isn't this quite right" failure the No Silent Fallbacks rule was written to kill. The whole point of Story 95-1's bind-on-init was to make this fail loud; the `elif starting_region:` guard quietly defeats it for the single most likely authoring mistake. Worse, the implementation's own docstring *claims* it fails loud, so a future reader trusts a guarantee the code doesn't keep.

Now the confused-author's twin: she sets `starting_region: yula_landng` (a typo). This time the code DOES fail loud — but it raises `RegionScopeBindError` straight through the WebSocket with no typed error, so she sees a disconnect and a stack trace in the server log instead of "starting_region 'yula_landng' has no matching orbital body." Loud, yes; actionable, no. Two adjacent authoring mistakes, two bad outcomes: one silent, one a socket-slam.

What a stressed runtime produces: a player resumes an orbital save taken at session start (current_region still `<root>`); the orrery emits a spurious skip span every resume and never re-centers until they travel — cosmetic but it pollutes the lie-detector channel the GM panel trusts. And the tests would not catch a regression to star-only matching, so the coyote_star fix Dev made could silently rot. None of these are fatal to the happy path — perseus_cloud and coyote_star both ship a valid starting_region, so the demo works — but "the demo works" is precisely the trap the project rules name. The bug lives in the gap between shipped content and the next author's content, and that author is a named, load-bearing user.

## Reviewer Assessment (round-trip 0 — REJECTED, superseded)

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Blank `starting_region` (default `str=""`) silently skips the fail-loud init bind — violates No Silent Fallbacks + bind-on-init AC. `[SILENT]`/`[EDGE]` | `sidequest/handlers/connect.py:307` (`elif starting_region:`) | For an orbital world (orbital_content present), a blank/missing `starting_region` must fail loud. Replace the `elif starting_region:` truthiness gate with an explicit raise (`RegionScopeBindError`) on blank, or call `bind_region_scope(starting_region or "", trigger="init")` and let it raise. Add a test. |
| [MEDIUM] | Fail-loud `RegionScopeBindError` from the fresh init bind propagates unhandled — ungraceful socket close vs. the typed `_error_msg` pattern used by every other connect load failure. `[EDGE]` | `sidequest/handlers/connect.py:763` | Wrap the fresh-connect init bind; on `RegionScopeBindError` return a typed `[_error_msg(...)]` and emit a watcher event so the author gets an actionable message. |
| [MEDIUM] | No unit test locks region→non-star-body match (the coyote_star body-type-agnostic behavior); a star-only regression passes the unit suite. `[TEST]` | `tests/orbital/test_scope_bind.py` | Add a test binding `yula_anchorage` (habitat) and asserting it centers. |
| [MEDIUM] | init-trigger span value + fail-loud span-absence unasserted. `[TEST]` | `tests/orbital/test_scope_bind.py` | Assert `orbital.scope_bind` with `trigger="init"` on the init MATCH; assert NO span on the init fail-loud path. |
| [MEDIUM] | No connect-time integration test for `_bind_initial_orbital_scope` (the wiring that shipped the HIGH bug). `[TEST]` | `tests/server/` | Add a connect-level (or direct-call) test for init (fresh) and resume, including the blank-starting_region fail-loud. |
| [LOW] | `trigger: str` open extension point — unknown trigger silently treated as relocation. `[TYPE]`-adjacent (type_design disabled; flagged by preflight+edge) | `sidequest/server/session.py:158` | Use `Literal["init","relocation"]` or raise on unknown trigger. |
| [LOW] | `<root>` sentinel not excluded on resume → spurious skip span. `[EDGE]` | `sidequest/handlers/connect.py:304` | Exclude `"<root>"` before falling back to starting_region. |
| [LOW] | `room.session` unguarded deref (close_store race). `[EDGE]` | `sidequest/server/narration_apply.py:3221` | Optional: guard `_session is None` (pre-existing pattern; non-blocking). |

**Dispatch coverage:** `[EDGE]` (5), `[SILENT]` (1), `[TEST]` (3), `[SEC]` (clean — no findings), `[DOC]` (subagent disabled), `[TYPE]` (subagent disabled; LOW noted via preflight/edge), `[SIMPLE]` (subagent disabled), `[RULE]` (subagent disabled; rule compliance done manually in `### Rule Compliance`).

**Why REJECT:** The HIGH finding is a reachable silent fallback that contradicts both a `<critical>` project rule and this story's central acceptance criterion (bind-on-init *fails loud*). Per the reviewer rule, a finding matching a stated project rule cannot be dismissed. The happy path is correct and well-built — but the one thing this story existed to guarantee (fail-loud init) has a hole for the most likely authoring mistake, and the bind-on-init path has no test to catch it. Fix is small and localized.

**Handoff:** Back to Amos (TEA) for RED rework — the fixes are testable (a logic bug plus missing edge-case coverage). TEA should add: (1) blank `starting_region` on an orbital world fails loud; (2) region→non-star-body (habitat) match centers; (3) init-trigger span asserted + fail-loud emits no span; (4) a connect-time init/resume test. Then Dev makes them green (the connect.py:307 fix + the typed-error wrap).

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/orbital/scope_bind.py` (new) — `RegionScopeBindError` (fail-loud home on the orbital surface)
- `sidequest-server/sidequest/telemetry/spans/scope_bind.py` (new) — `orbital.scope_bind` / `orbital.scope_bind_skipped` emitters (FLAT_ONLY_SPANS)
- `sidequest-server/sidequest/telemetry/spans/__init__.py` — register the scope_bind span module
- `sidequest-server/sidequest/server/session.py` — `Session.bind_region_scope(region_id, *, trigger)` mechanism
- `sidequest-server/sidequest/server/narration_apply.py` — Site B: re-center on region-mode pc_region advance
- `sidequest-server/sidequest/handlers/connect.py` — `_bind_initial_orbital_scope` + calls after both `bind_world` sites (fresh init / resume relocation)

**Tests:** 8/8 story tests passing (GREEN) — 7 unit (`tests/orbital/test_scope_bind.py`) + 1 wiring (`tests/server/test_region_orbital_scope_wiring.py`). Routing-completeness lint passes (new spans registered). coyote_star regression guard (`test_mp_auto_seat_on_connect.py`) passes.

**Regression check:** Full `tests/orbital/` + `tests/server/` serial run = 18 pre-existing failures (combat/dogfight/chargen/reference domains), all confirmed identical on the base branch via stash-compare on the same file sets — **zero new failures introduced**. Pyright: 60 connect.py errors identical on base (pre-existing); new core files (session/scope_bind/spans) 0 errors. Ruff clean.

**Branch:** feat/95-1-region-orbital-scope-binding (pushed, sidequest-server commit 9406fd8)

**AC status:**
- Content load + identity join — covered by synthetic fixture mechanism test; perseus 34/34 → content validator (TEA deviation)
- Bind-on-init (match + fail-loud) — wired at connect.py; method tested
- Bind-on-relocation (re-center + loud skip) — Site B wired + tested; Site A proven unreachable for orbital worlds (deviation)
- OTEL scope_bind/scope_bind_skipped — emitters + span assertions green
- Wiring test (no source grep) — real narration-apply relocation + OTEL span assertion green
- Scope guard (coyote_star unchanged, no chart.yaml/travel) — regression-safe; match relaxed to region→body for coyote_star

**Handoff:** To verify/review phase.
## TEA Assessment (Rework — round-trip 1)

**Tests Required:** Yes
**Status:** RED (1 failing / 13 passing — verified via testing-runner, run id 95-1-tea-red-rework)

**New / changed test files:**
- `tests/server/test_connect_orbital_init_bind.py` (NEW) — direct-call tests for the connect wiring helper `_bind_initial_orbital_scope` (Reviewer sanctioned direct-call over the Postgres-backed handler harness):
  - `test_init_bind_fresh_blank_starting_region_fails_loud` — **the RED driver.** A fresh orbital world with a blank `starting_region` must raise `RegionScopeBindError`. Currently "DID NOT RAISE" → drives the connect.py:307 fix (Reviewer HIGH).
  - `test_init_bind_fresh_centers_on_starting_region` — fresh-valid centers (pass).
  - `test_resume_bind_centers_on_persisted_current_region` — resume centers on current_region, not starting_region (pass).
  - `test_init_bind_noop_for_non_orbital_world` — non-orbital world no-op, no raise even with blank starting_region (pass; regression guard).
- `tests/orbital/test_scope_bind.py` (3 added coverage locks):
  - `test_bind_relocation_match_non_star_body_centers` — region→habitat (`yula_anchorage`) match centers (locks coyote_star body-type-agnostic behavior; Reviewer MEDIUM [TEST]).
  - `test_bind_init_match_emits_span_with_init_trigger` — init MATCH emits `orbital.scope_bind` with `trigger="init"` (Reviewer MEDIUM [TEST]).
  - `test_bind_init_fail_loud_emits_no_scope_bind_span` — init fail-loud emits NO `orbital.scope_bind` span (no lie-detector false positive; Reviewer MEDIUM [TEST]).

**Reviewer-finding coverage:**
| Reviewer finding | Severity | Test | RED/lock |
|---|---|---|---|
| Blank starting_region silently skips init bind | HIGH | `test_init_bind_fresh_blank_starting_region_fails_loud` | **RED** |
| RegionScopeBindError propagates unhandled (graceful typed-error wrap) | MEDIUM | helper-raise contract; full-handler test deviated (DB harness disproportionate) | n/a (deviation logged) |
| No region→non-star-body unit test | MEDIUM | `test_bind_relocation_match_non_star_body_centers` | lock (green) |
| init-trigger span + fail-loud span-absence unasserted | MEDIUM | `test_bind_init_match_emits_span_with_init_trigger`, `test_bind_init_fail_loud_emits_no_scope_bind_span` | lock (green) |
| No connect-time init/resume test | MEDIUM | `test_connect_orbital_init_bind.py` (4 tests) | RED + locks |
| trigger: str open extension point | LOW | not pinned (Dev's call; LOW polish) | — |
| `<root>` sentinel not excluded on resume | LOW | not pinned (debatable semantics; LOW) | — |

### Rule Coverage (python lang-review)
| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions / No Silent Fallbacks | `test_init_bind_fresh_blank_starting_region_fails_loud` (blank → fail loud) | failing (RED) |
| #4 logging/observability coverage | `test_bind_init_match_emits_span_with_init_trigger`, `test_bind_init_fail_loud_emits_no_scope_bind_span` | passing (locks) |
| #6 test quality (no vacuous asserts) | self-check below | n/a |

**Rules checked:** same 3 of 13 materially-applicable rules as the original RED (fail-loud, observability, test quality).
**Self-check:** No vacuous assertions added. The non-orbital no-op test pre-asserts `orbital_content is None` so it can't pass vacuously; the fail-loud-no-span test asserts an empty span list after a real raise; the blank-starting_region test asserts both the raise AND no partial mutation.

**What Dev must do (GREEN):**
1. **(HIGH, blocking)** `connect.py:307` — replace the `elif starting_region:` truthiness gate so a fresh orbital world with a blank/missing `starting_region` FAILS LOUD (raise `RegionScopeBindError`), not a silent skip. Simplest: `else: session.bind_region_scope(starting_region or "", trigger="init")` (the method already raises on a no-match init), or an explicit `if not starting_region: raise RegionScopeBindError(...)`.
2. **(MEDIUM)** Wrap the fresh-connect `_bind_initial_orbital_scope` call to catch `RegionScopeBindError` and return a typed `[_error_msg(...)]` + watcher event (graceful loud failure). Not gated by an automated test (see deviation) but Reviewer-requested.
3. Keep the 13 coverage locks green.

**Handoff:** To Naomi (Dev) for GREEN.
## Dev Assessment (Rework — round-trip 1)

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/handlers/connect.py` — (1) `_bind_initial_orbital_scope` fresh path: `elif starting_region:` → unconditional `else: bind_region_scope(starting_region or "", trigger="init")` so a blank/missing starting_region on an orbital world fails loud (Reviewer HIGH); (2) wrapped the fresh-connect init bind in `try/except RegionScopeBindError` → `logger.error` + `orbital_scope_bind_failed` watcher event + typed `_error_msg` (Reviewer MEDIUM); (3) added top-level `from sidequest.orbital.scope_bind import RegionScopeBindError`.

**Reviewer findings addressed:**
| Finding | Severity | Resolution |
|---|---|---|
| Blank starting_region silently skips init bind | HIGH | Fixed — fresh path fails loud; gated by `test_init_bind_fresh_blank_starting_region_fails_loud` (now GREEN) |
| RegionScopeBindError propagates unhandled | MEDIUM | Fixed — typed `_error_msg` + watcher event (untested per TEA deviation; mirrors existing load-failure pattern) |
| No region→non-star-body unit test | MEDIUM | Covered by TEA lock `test_bind_relocation_match_non_star_body_centers` (GREEN) |
| init-trigger span + fail-loud span-absence | MEDIUM | Covered by TEA locks (GREEN) |
| No connect-time init/resume test | MEDIUM | Covered by TEA `test_connect_orbital_init_bind.py` (GREEN) |
| trigger: str open extension point | LOW | Not changed — LOW polish, not pinned by a test; left as-is per minimalist discipline |
| `<root>` sentinel on resume | LOW | Not changed — debatable semantics, not pinned; left as-is |
| room.session unguarded deref | LOW | Not changed — pre-existing pattern, non-blocking |

**Tests:** rework suite 22/22 GREEN (`tests/orbital/test_scope_bind.py` 11 + `test_connect_orbital_init_bind.py` 5 + `test_region_orbital_scope_wiring.py` 1 + routing-completeness + coyote_star MP regression). The round-trip-1 RED driver (`test_init_bind_fresh_blank_starting_region_fails_loud`) is now GREEN. Broader regression: 342 passed across `tests/orbital/` + connect/reconnect/narration-apply-wiring tests.

**Quality:** ruff clean (import re-sorted via --fix); pyright connect.py = 60 errors, identical to base (zero new); the 3 LOW findings consciously deferred per minimalist discipline (no test demands them).

**Branch:** feat/95-1-region-orbital-scope-binding (pushed, sidequest-server commit 4670901)

**Handoff:** To verify/review phase.
## Subagent Results (round-trip 1 — re-review of rework)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 blockers (22/22 green, lint/format pass, pyright unchanged at 60) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 3 | confirmed 0 blocking; dismissed 1 (narrow-except is correct design), deferred 2 (low: half-init state, None-getattr test) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 (+round-0 hole confirmed CLOSED) | dismissed 1 (cartography None non-reachable — World.cartography required) |
| 4 | reviewer-test-analyzer | Yes | findings | 3 | confirmed 0 blocking; deferred 3 (vacuous noop test [downgraded], foreign-region helper coverage, untested except-branch) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | 0 | confirmed 0 — error message + watcher payload carry only content-config identifiers, no leak |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 0 blocking; 2 dismissed (with rationale); 5 deferred (low/test-quality, captured as non-blocking delivery findings)

## Reviewer Analysis (round-trip 1 — re-review of rework)

### Observations
- **[VERIFIED] Round-0 HIGH (silent skip) is genuinely fixed** — `_bind_initial_orbital_scope` fresh path is now an unconditional `else: session.bind_region_scope(starting_region or "", trigger="init")` (connect.py:308-316). Both blank `""` and `None` collapse to `""`, which is never a body id → `RegionScopeBindError` raises. No truthiness gate remains. Confirmed by silent-failure-hunter + pinned by `test_init_bind_fresh_blank_starting_region_fails_loud` (the round-0 RED driver, now green). Evidence: connect.py:316 + session.py no-match-init raise.
- **[VERIFIED] Round-0 MEDIUM (graceful wrap) implemented** — fresh-connect bind wrapped in `try/except RegionScopeBindError` → `logger.error` + `orbital_scope_bind_failed` watcher event + typed `[_error_msg(code="orbital_scope_bind_failed")]` (connect.py:781-808). Mirrors the genre-pack/world-grounding load-failure pattern. The except `return` aborts the connect (no continue past it). Evidence: edge-hunter confirmed the return is reached before `has_character` and no state continues.
- **[SILENT] cartography-None silent return (connect.py:300)** — DISMISSED: `World.cartography` is a required non-Optional `CartographyConfig` field (pack.py:134), so a loaded orbital world always has a `CartographyConfig` (defaulting `starting_region=""` → reaches the `else` → fails loud). The `cartography is None` branch only fires for `world_obj is None` / `genre_pack is None`, both upstream-guarded. Non-reachable for the orbital-misconfig scenario. Pre-existing from round 0, not introduced by the rework.
- **[EDGE] Narrow `except RegionScopeBindError` (connect.py:789)** — DISMISSED: the only other raises from `bind_region_scope` are lazy `ImportError` (broken install → whole server down) or `AttributeError` on `orbital_content.orbits.bodies` (non-reachable — `load_orbital_content` returns a pydantic-validated `OrbitsConfig` whose `bodies` is always a dict). The narrow catch is *correct* — broadening to `except Exception` would swallow genuine bugs, violating fail-loud. Disagree with the broaden suggestion.
- **[TEST] `test_init_bind_noop_for_non_orbital_world` weak assertion (test_connect_orbital_init_bind.py:166)** — DEFERRED (non-blocking): the `assert party_body_id is None` line asserts the default value (weak), but the test's load-bearing assertion is genuine — it proves a non-orbital world does NOT raise even with a blank starting_region (the orbital_content-None early-return short-circuits before the new fail-loud), guarded by the `orbital_content is None` pre-assert. Not fully vacuous; the party_body_id line could be strengthened to a pre-set sentinel. Captured as a delivery finding.
- **[TEST] except-branch (watcher + _error_msg) untested** — DEFERRED (non-blocking): the round-0 TEA deviation. The watcher-event half is testable without Postgres; logged as a delivery finding for future hardening. Acceptable for a MEDIUM — the failure is still loud.
- **[VERIFIED] Resume path unaffected** — `if is_resume: ... else:` is exclusive; resume binds `trigger="relocation"` (loud-skip), never the init raise. Evidence: connect.py:303-316 + edge-hunter Q1.
- **[SEC] clean** — error message + watcher payload carry only content-config identifiers (world_slug, region_id repr); no secrets/PII/injection sink.
- **[DOC]/[TYPE]/[SIMPLE]/[RULE]** — subagents disabled via `workflow.reviewer_subagents`; rule compliance done manually below.

### Rule Compliance (round-trip 1)
- **No Silent Fallbacks (`<critical>`):** the round-0 violation is FIXED — blank/foreign starting_region on a fresh orbital world now fails loud. The remaining `cartography is None` return is non-reachable for loaded orbital worlds (type-system-guaranteed). COMPLIANT.
- **OTEL Observability:** the new error path emits `orbital_scope_bind_failed` watcher event (severity=error) — the GM-panel lie-detector for the content-misconfig failure. COMPLIANT.
- **Graceful degradation / typed errors:** the connect error now returns a typed `_error_msg(code=...)` matching the established load-failure pattern. COMPLIANT.
- **Test quality:** one weak (not fully vacuous) noop assertion deferred; the HIGH-fix RED driver is correctly structured (typed raise + no-partial-mutation + non-vacuous pre-assert). COMPLIANT enough to ship; nits deferred.

### Devil's Advocate
Try to break the rework. The blank-starting_region author footgun is now closed: a fresh orbital world with `starting_region: ""` raises `RegionScopeBindError`, the handler catches it, logs, emits a watcher event, and returns a typed error the author can read. Could the author still get a silent miss? Only via the `cartography is None` branch — but `World.cartography` is a required field, so a loaded orbital world always carries a `CartographyConfig`; an omitted cartography.yaml yields a default config with `starting_region=""`, which routes straight into the fail-loud `else`. So the silent path the round-0 review killed cannot resurrect through cartography omission. What about a genuinely unexpected exception (ImportError, malformed orbits) escaping the narrow except? Those are either install-level breakage or pre-validated-away by pydantic; catching them would be wrong (swallowing real bugs). The half-initialized PG-row-plus-bound-room state on the error path is the one rough edge — a content fix requires the session row cleared or the room reaped before a clean reconnect — but it's a repeating *loud* failure, not data corruption or a silent success, and the operator (Keith) sees the watcher event. The test debt is real but bounded: the except-branch's watcher/typed-error effects aren't pinned, and one noop test leans on a default value. Neither lets broken behavior ship silently — the production fail-loud is covered; what's uncovered is the *graceful-wrapping* of an already-loud failure. For a MEDIUM, that's an acceptable, documented gap. Nothing here rises to blocking.

## Reviewer Assessment

**Verdict:** APPROVED

**Round-0 blockers — resolution verified:**
- HIGH (blank starting_region silently skips fail-loud init bind) → **FIXED**: `else: bind_region_scope(starting_region or "", trigger="init")` raises on blank/None; pinned by `test_init_bind_fresh_blank_starting_region_fails_loud` (green). Confirmed closed by silent-failure-hunter.
- MEDIUM (RegionScopeBindError propagates unhandled) → **FIXED**: typed `_error_msg` + `orbital_scope_bind_failed` watcher event; aborts the connect cleanly.

**Data flow traced:** content `cartography.starting_region` → `_bind_initial_orbital_scope` (fresh/init) → `Session.bind_region_scope` → match sets `party_body_id` + `orbital_scope` + emits `orbital.scope_bind`; no-match raises `RegionScopeBindError` → caught at connect → typed error + watcher event. Relocation flows content region → narration_apply Site B → same bind (loud-skip on no-match). Safe: every branch either centers, loud-skips with a span, or fails loud with a typed error.

**Pattern observed:** the connect except-branch mirrors the existing genre-pack/world-grounding load-failure handling (`return [_error_msg(...)]`) at connect.py — consistent, reviewed shape.

**Error handling:** blank/foreign starting_region → `RegionScopeBindError` → typed connect error + OTEL watcher event (connect.py:789-808). Non-orbital worlds → clean no-op early-return (connect.py:296).

**Dispatch coverage:** `[EDGE]` (dismissed 1 narrow-except, deferred 2 low), `[SILENT]` (round-0 hole confirmed CLOSED; 1 dismissed non-reachable), `[TEST]` (3 deferred non-blocking), `[SEC]` (clean), `[DOC]` (disabled), `[TYPE]` (disabled), `[SIMPLE]` (disabled), `[RULE]` (manual — compliant).

**Non-blocking follow-ups** (delivery findings, not merge blockers): strengthen the non-orbital noop test to a pre-set sentinel; add a no-Postgres test for the `orbital_scope_bind_failed` watcher event; optionally a defensive raise on the (non-reachable) `cartography is None` path.

**Handoff:** To Camina (SM) for finish-story.