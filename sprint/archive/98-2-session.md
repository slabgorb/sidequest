---
story_id: "98-2"
jira_key: ""
epic: "98"
workflow: "tdd"
---
# Story 98-2: S1 Server — per-region system-file resolution in orbital/loader.py (system_root() unchanged)

## Story Details
- **ID:** 98-2
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none
- **Branch:** feat/98-2-per-region-system-file-resolution
- **Branch Strategy:** gitflow (feat/{STORY_ID}-{SLUG})

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-09T21:35:15Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-09T00:00:00Z | 2026-06-09T20:44:08Z | 20h 44m |
| red | 2026-06-09T20:44:08Z | 2026-06-09T20:53:22Z | 9m 14s |
| green | 2026-06-09T20:53:22Z | 2026-06-09T21:05:34Z | 12m 12s |
| review | 2026-06-09T21:05:34Z | 2026-06-09T21:13:37Z | 8m 3s |
| red | 2026-06-09T21:13:37Z | 2026-06-09T21:17:55Z | 4m 18s |
| green | 2026-06-09T21:17:55Z | 2026-06-09T21:27:42Z | 9m 47s |
| review | 2026-06-09T21:27:42Z | 2026-06-09T21:35:15Z | 7m 33s |
| finish | 2026-06-09T21:35:15Z | - | - |

## Sm Assessment

**Story:** Server hinge of epic 98's critical path (ADR-141 two-scale spatial model). Replace the hard-coded `world_dir / "orbits.yaml"` in `orbital/loader.py:42` with per-region resolution of `worlds/<world>/systems/<region_id>.yaml`, keyed to the party's current region. `system_root()` (`render.py:132`) stays verbatim — the whole reuse argument rests on not touching it.

**Readiness:** Predecessor 98-1 is **done + approved** (perseus_cloud split into `systems/<id>.yaml`, fake root deleted, `yula` authored), so the files to resolve exist. Rich story context already authored at `sprint/context/context-story-98-2.md` with 5 ACs, scope boundaries, and assumptions. No blocking PRs. Branch off `develop` per gitflow.

**Watch points for TEA/Dev:**
- AC2 mandates a **wiring test** — loader must be reached from a production code path, not just a unit harness (CLAUDE.md "Every Test Suite Needs a Wiring Test").
- AC3/AC4: **fail loud** on missing system file (No Silent Fallbacks) + **OTEL span** on resolution (region → file → hit/miss). The GM panel is the lie detector.
- Key assumption to verify early: the **current region id must be reachable at the loader seam** (same region layer feeding `movement.py` / `dungeon/region_projection.py`). If it needs new plumbing, log a Design Deviation — that changes story size.
- Do **not** touch `system_root()`, the ADR-130 course model, or add jump adjudication (that's 98-5).

**Verdict:** Ready for RED. Handing to TEA (Mr. Praline).

## TEA Assessment

**Tests Required:** Yes
**Reason:** New runtime behavior (per-region file resolution) — not a chore.

**Test Files:**
- `tests/orbital/test_loader_per_region.py` — 12 tests covering all 5 ACs.
- `tests/orbital/fixtures/world_two_scale/` — two-scale fixture: `systems/{yula,vorn}.yaml`, no top-level orbits.yaml (mirrors 98-1's deletion).
- `tests/orbital/fixtures/world_two_scale_stub/` — `systems/yula.yaml` + a stray `orbits.yaml` retirement-stub (marker body `legacy_monolith_marker`) to prove non-fallback.
- (reuses existing `tests/orbital/fixtures/world_minimal/` for the single-system / coyote_star-shape regression.)

**Tests Written:** 12 tests covering 5 ACs
**Status:** RED confirmed (11 failing, 1 regression-guard green) — verified via testing-runner (`98-2-tea-red`), clean collection, no import errors.

**AC → test map:**
| AC | Tests | RED status |
|----|-------|-----------|
| AC1 per-region resolution replaces hard-coded path | `test_resolves_systems_file_for_current_region`, `test_resolves_distinct_file_for_a_different_region`, `test_does_not_read_top_level_orbits_monolith` | failing (no `region_id`) |
| AC2 system_root() unchanged + WIRING | `test_system_root_resolves_verbatim_against_resolved_file`, `test_resolved_file_has_exactly_one_parentless_primary`, `test_loader_reached_from_production_bind_path_for_yula` (wiring) | failing |
| AC3 fail loud on missing file (No Silent Fallbacks) | `test_missing_system_file_fails_loud_naming_path`, `test_missing_system_file_does_not_fall_back_to_stub_monolith` | failing |
| AC4 OTEL span on resolution (hit + miss) | `test_resolution_hit_emits_system_resolve_span`, `test_resolution_miss_emits_system_resolve_span_with_hit_false` | failing |
| AC5 coyote_star single-system regression | `test_single_system_world_loads_without_region_key` (green guard), `test_single_system_world_ignores_a_supplied_region_key` | 1 green / 1 failing |

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| §Exception handling — fail loud, no silent swallow | `test_missing_system_file_fails_loud_naming_path`, `..._does_not_fall_back_to_stub_monolith` | failing |
| §Path handling — `Path / file`, cross-platform | path regex `systems[/\\]amanta\.yaml` in AC3 tests | failing |
| §Error logging / observability — error path is observable | AC4 miss test (`hit=False` span before raise) | failing |
| §Test quality — meaningful assertions, no vacuous | self-checked (see below) | n/a |

**Rules checked:** 4 of the applicable python lang-review rules have test coverage (the loader is a narrow path-resolution seam — exception-handling, path-handling, observability, and test-quality are the live rules; async/security/resource rules are not engaged by a synchronous YAML read that already uses `with ...open()`).
**Self-check:** 0 vacuous assertions. Every test asserts a specific value (body membership, root id, exception+path, span attrs). The one green-at-RED test (`test_single_system_world_loads_without_region_key`) is an intentional regression guard, not a vacuous pass.

**Handoff:** To Dev (Bicycle Repair Man) for GREEN. **Read the two blocking Delivery Findings first** — the region-id reachability at the bind seam is the one thing that can resize this story.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/orbital/loader.py` — `load_orbital_content(world_dir, region_id=None)`: multi-system worlds (a `systems/` dir) resolve `systems/<region_id>.yaml` via new `_resolve_system_file`; single-system worlds (no `systems/` dir) load `orbits.yaml` and ignore the region key (collapse). Fail-loud on a blank region or missing per-system file, naming the path; never falls back to a stray top-level `orbits.yaml` stub.
- `sidequest/telemetry/spans/system_resolve.py` — **new** `orbital.system_resolve` span (`region_id`, `system_file`, `hit`), registered in `FLAT_ONLY_SPANS`. Mirrors `scope_bind.py`. Fires on hit AND miss (before the raise).
- `sidequest/telemetry/spans/__init__.py` — registers the new span module (star-import).
- `sidequest/server/session_room.py` — `bind_world` gains `region_id` param (defaults to `snapshot.current_region` for resume) and threads it to `load_orbital_content`.
- `sidequest/handlers/connect.py` — new `_starting_region_for(genre_pack, world_slug)` helper; the **fresh-connect** `bind_world` call passes `region_id=starting_region` because a fresh snapshot's `current_region` is blank at bind time (region_init runs later at chargen). The resume path uses the `bind_world` default (persisted `current_region`).

**Tests:** 12/12 new (GREEN) + full regression GREEN — **3813 passed / 0 failed / 154 skipped** across `tests/orbital`, `tests/telemetry`, `tests/server`. Lint clean (`ruff check` + `format`). Pyright: 0 new errors (63 baseline errors identical with/without my changes — pre-existing debt in `connect.py`/`session_room.py`, none in changed lines).
**Branch:** `feat/98-2-per-region-system-file-resolution` (pushed)

**Wiring (CLAUDE.md "No half-wired features"):** Full pipeline connected — loader → `bind_world` → both `connect.py` call sites. Production-reachable: the AC2 wiring test drives `SessionRoom.bind_world` (production path) and confirms `systems/yula.yaml` resolves with `yula` as system root. OTEL `orbital.system_resolve` span is the GM-panel lie-detector for resolution.

**Handoff:** To verify/review phase.

## TEA Assessment — Round-Trip 1 (rework)

**Tests Required:** Yes (driving the Reviewer's HIGH path-traversal finding test-first)
**New/changed tests:** `tests/orbital/test_loader_per_region.py` — 6 added, 1 hardened.

**RED drivers (3 — fail until Dev adds the path-segment guard):**
- `test_path_traversal_does_not_load_sibling_orbits_stub` — airtight escape proof: in `world_two_scale_stub` the sibling `orbits.yaml` stub EXISTS, so `region_id="../orbits"` resolves `systems/../orbits.yaml` to a real file outside `systems/`. A raise can ONLY come from a guard (not a missing file). Today the loader loads the stub → FAILS.
- `test_parent_ref_region_id_rejected_before_filesystem_probe` — `..` region must be rejected BEFORE any path is built/probed → asserts no `orbital.system_resolve` span fires. Today a miss span fires → FAILS.
- `test_separator_region_id_rejected_before_filesystem_probe` — bare `/` (no `..`) rejected before probing → no span. Today a miss span fires → FAILS.

**Green-at-write coverage closures (verified PASS now):**
- `test_explicit_region_id_kwarg_resolves_via_bind_world` — the untested production branch: fresh blank snapshot + explicit `region_id="vorn"` through `SessionRoom.bind_world` → resolves `systems/vorn.yaml`, root `vorn`. Closes test-analyzer #1 (the fresh-connect multi-system path).
- `test_blank_region_none_fails_loud_for_multi_system` / `..._empty_string_...` — pin the No-Silent-Fallbacks blank-region guard (test-analyzer #2).
- `test_single_system_world_emits_no_resolve_span` — single-system collapse emits no resolve span (test-analyzer #5).
- hardened `test_resolution_miss_emits_system_resolve_span_with_hit_false` — now asserts `system_file` contains `amanta.yaml` (test-analyzer #4).

**Status:** RED confirmed via testing-runner (`98-2-tea-red-rt1`): 3 traversal tests FAIL, 16 PASS. Clean collection.

**Guard contract for Dev (GREEN):** In `_resolve_system_file` (loader.py), reject a `region_id` containing a path separator (`/` or `\`), a `..` parent ref, or a NUL byte — **before** building the path or emitting the span — failing loud (a path-like region is invalid input; `ValueError` or `OrbitalContentMissingError` both satisfy the tests). The three RED tests pin: (a) no escaped-file load, (b)+(c) no span fires for a path-like region.

**Also for Dev (non-test, Reviewer LOW, recommended):** fix the stale comment at `session_room.py:269-271`; optionally add `encoding="utf-8"` to `loader.py:76,82` (pre-existing). The swallow-narrowing is a non-blocking deferral (98-3/98-5).

**Self-check:** 0 vacuous assertions — traversal tests assert raises + span-absence; coverage tests assert specific bodies/roots/messages.

**Handoff:** To Dev (Bicycle Repair Man) for GREEN — add the path-segment guard.

## Dev Assessment — Round-Trip 1 (green rework)

**Implementation Complete:** Yes
**Files Changed (this round):**
- `sidequest/orbital/loader.py` — **path-segment guard** in `_resolve_system_file`: rejects a `region_id` containing `/`, `\`, NUL, or `..` **before** building/probing a path or emitting the span, raising **`ValueError`** (a path-like region is invalid input). Chose `ValueError` over `OrbitalContentMissingError` deliberately — it is NOT caught by `bind_world`'s optional-tier `except OrbitalContentMissingError`, so a malicious/corrupt `current_region` surfaces loudly instead of silently yielding no chart (completes No Silent Fallbacks). Also added `encoding="utf-8"` to both `open()` calls (lang-review #5).
- `sidequest/server/session_room.py` — corrected the now-stale swallow comment (names both `OrbitalContentMissingError` cases; documents that the path-like `ValueError` is intentionally NOT caught; defers the case-(2) narrowing to 98-3/98-5).

**Reviewer findings resolution:**
- [HIGH/BLOCKING] Path traversal → **FIXED** (guard + 3 green tests).
- [MED] Untested explicit-`region_id` wiring + blank-region guard → **covered** (TEA's rt1 tests pass).
- [LOW] Stale comment + `encoding=` → **fixed**.
- [non-blocking] Overbroad swallow narrowing → **deferred** to 98-3/98-5 (documented in the comment + delivery findings); the path-like case now escapes the swallow loudly.

**Tests:** 19/19 story tests GREEN (incl. 3 traversal guards) + full regression GREEN — **3820 passed / 0 failed / 154 skipped** (`tests/orbital`, `tests/telemetry`, `tests/server`). Lint + format clean. Pyright: 0 errors on `loader.py`.
**Branch:** `feat/98-2-per-region-system-file-resolution` (pushed)

**Handoff:** Back to Reviewer (The Argument Professional) for re-review.

## Subagent Results

_(Current round = round-trip 1 re-review. Round-0 results preserved in the assessment below.)_

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A — 374 orbital tests green, ruff clean (1 pre-existing in unrelated file), pyright delta −17, 0 smells |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — traversal/blank-region edge cases assessed via rule-checker + test-analyzer |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — swallow + ValueError-propagation assessed via rule-checker #1 |
| 4 | reviewer-test-analyzer | Yes | findings | 1 | confirmed 1 MEDIUM non-blocking (stub test could add span-absence — already covered by companion tests); 0 blocking |
| 5 | reviewer-comment-analyzer | Yes | clean | 0 | N/A — both rewritten comments (loader guard, session_room swallow) verified accurate |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled — rule-checker #3 confirms all new signatures fully annotated |
| 7 | reviewer-security | No | Skipped | disabled | Disabled — CWE-22 traversal closure verified by rule-checker #5/#11 (every vector analyzed) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled — guard is minimal (one string-content check); no over-engineering |
| 9 | reviewer-rule-checker | Yes | findings | 1 | HIGH traversal RESOLVED + encoding RESOLVED verified; 1 informational (pre-existing star-import convention, not actionable) |

**All received:** Yes (4 enabled re-ran, 5 disabled pre-filled)
**Total findings:** 0 blocking — the round-0 HIGH path traversal is verified closed; 1 MEDIUM non-blocking test-hardening (optional, already covered three ways)

## Reviewer Assessment

**Verdict:** APPROVED (round-trip 1 re-review)

The round-0 REJECT (HIGH path traversal + untested production path + LOW doc/encoding) is fully resolved and verified by a fresh subagent pass.

- `[SEC]`/`[RULE]` **Path traversal CLOSED** — `_resolve_system_file` (loader.py:113) rejects `region_id` containing `/`, `\`, NUL, or `..` **before** path construction and span emission, raising `ValueError`. Rule-checker analyzed every bypass vector (absolute paths, both separators, NUL, parent refs, URL-encoded, Unicode lookalikes, symlinks) — all caught or proven non-traversing on the target POSIX platforms. `[VERIFIED]` — guard precedes `system_path = systems_dir / ...` (loader.py:120) and `emit_system_resolve` (loader.py:124); confirmed by `test_parent_ref_region_id_rejected_before_filesystem_probe` / `test_separator_..._before_filesystem_probe` (no span fires) + `test_path_traversal_does_not_load_sibling_orbits_stub` (no escaped-file load).
- `[SILENT]` **ValueError escapes the swallow** — `bind_world`'s `except OrbitalContentMissingError` does NOT catch the path-like `ValueError`, so invalid input fails loud rather than silently yielding no chart. `[VERIFIED]` — rule-checker #1 confirmed no broad `except` on the propagation path; the choice is documented in both comments.
- `[TEST]` **Production path + guards now covered** — `test_explicit_region_id_kwarg_resolves_via_bind_world` (fresh blank snapshot + explicit `region_id`), `test_blank_region_none/empty_..._fails_loud`, `test_single_system_world_emits_no_resolve_span`, hardened miss-span. Test-analyzer confirms all genuinely pin behavior; 1 MEDIUM non-blocking residual (add span-absence to the stub test) is optional — the guard-before-probe claim is already instrumented by the companion tests.
- `[DOC]` **Comments corrected** — comment-analyzer clean: the loader guard comment and the session_room swallow comment both accurately describe the two `OrbitalContentMissingError` cases + the `ValueError`-not-caught rationale.
- `[RULE]` **encoding= added** — both `loader.py` `open()` calls now carry `encoding="utf-8"` (lang-review #5 closed).
- `[TYPE]` (disabled) — rule-checker #3 confirms every new signature is fully annotated.
- `[SIMPLE]` (disabled) — the guard is a single string-content check; no over-engineering.
- `[EDGE]` (disabled) — boundary cases (blank/None region, path-like region, single-system collapse, distinct-region selection) all covered by the suite.

**Data flow traced (re-verified):** narrator patch → `WorldPatch.current_region` → persisted snapshot → `bind_world` `resolved_region` → `load_orbital_content` → `_resolve_system_file` → **guard rejects path-like input before the path is built** → safe. The previously-unsafe final hop is now guarded.

**Pattern observed (good):** the fix is minimal and defense-in-depth at the correct seam (innermost path-construction boundary), with the OTEL miss-span preserved for legitimate misses. **Mechanical gates:** 374 orbital tests green, full regression 3820 green, pyright −17 vs baseline, lint clean.

**Verdict rationale:** No Critical/High issues remain; the single residual is MEDIUM non-blocking test hardening already covered by companion tests. APPROVED.

**Handoff:** To SM (The Announcer) for finish-story.

### Reviewer Assessment — Round 0 (REJECTED — superseded by the re-review above)

**Verdict:** REJECTED

The five acceptance criteria are met and the happy path is solid (12 targeted tests + 3813 regression green, wiring proven at `bind_world`, OTEL fires on hit/miss). But this PR introduces a **new path-traversal surface** in production code, and the production-goal path (fresh multi-system connect) plus the No-Silent-Fallbacks blank-region guard are untested. The blocking issue is cheap to fix.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] `[SEC]`/`[RULE]` | **Path traversal (CWE-22).** `region_id` is interpolated raw into a filesystem path with no sanitization. Its runtime source is `snapshot.current_region` — a narrator-patchable world field (`WorldPatch.current_region`), i.e. LLM-influenced. A persisted `current_region` like `"../../game/pg/sessions"` escapes `systems/`. **NEW surface:** pre-98-2 the loader read a fixed `world_dir/"orbits.yaml"`; this PR makes a region string a path segment. Mitigations exist (`.yaml`-only, `OrbitsConfig(extra="forbid")` rejects non-orbit files → no exfiltration, region writes *may* be canonicalized) so impact is bounded — but the project's lang-review rule #5/#11 explicitly requires path-from-input validation, and the fix is ~3 lines. | `sidequest/orbital/loader.py:105` (`_resolve_system_file`) | In `_resolve_system_file`, reject a `region_id` containing a path separator, `..`, or NUL **before** building the path — fail loud as an invalid region (this also completes the No-Silent-Fallbacks story: a path-like region is invalid, not a silent traversal). Add a test (`region_id="../orbits"` → raises). |
| [MEDIUM] `[TEST]`/`[EDGE]` | **Untested production path.** The wiring test only exercises the `snapshot.current_region` fallback branch of `bind_world`; the **explicit `region_id=` kwarg branch** — the one the fresh-connect `connect.py` path uses for multi-system worlds — has no test. Existing `test_connect_orbital_init_bind` uses a single-system fixture, so multi-system fresh resolution would not fail any test if it broke. On a project whose CLAUDE.md says "tests passing means nothing if the endpoint isn't hit in production code," this is the exact gap the wiring doctrine guards. | `tests/orbital/test_loader_per_region.py` | Add a wiring test: blank snapshot (no `current_region`), `bind_world(..., region_id="yula")` → `orbital_content` resolved from `systems/yula.yaml`. |
| [MEDIUM] `[TEST]`/`[SILENT]` | **No-Silent-Fallbacks guard uncovered.** `_resolve_system_file`'s blank/`None` `region_id` fail-loud branch (loader.py:99-103) has zero test coverage. A refactor turning the guard into a silent fallback would pass the suite. | `tests/orbital/test_loader_per_region.py` | Add tests: `load_orbital_content(TWO_SCALE, region_id=None)` and `region_id=""` each raise `OrbitalContentMissingError` (match "blank region"). |
| [LOW] `[DOC]` | **Stale inline comment.** `session_room.py:269-271` says `OrbitalContentMissingError` means "caverns... have no orbits.yaml" — after 98-2 it can also signal a multi-system world with a missing/blank region file. The comment now misleads (implies the swallow is always the optional-tier case). | `sidequest/server/session_room.py:269-271` | Update the comment to name both cases; note the swallow is intentionally broad and may need narrowing (see below). |

**Non-blocking observations (bundle with the rework, not strictly required):**
- `[RULE]`/`[SILENT]` **Overbroad swallow** (`session_room.py:268`, confirmed by rule-checker #1/#14 + comment-analyzer): the `except OrbitalContentMissingError` now also swallows the multi-system blank-region loud-fail, conflating "no orbital tier" with "orbital world, no region." Pre-existing mechanism, already logged as a Gap by TEA and Dev; the normal path (authored `starting_region`) works. **Recommend** narrowing (distinguish the two via an `OrbitalContentMissingError` reason/subclass) OR an explicit deferral to 98-3/98-5 where bind-time multi-system reachability is exercised. Not blocking on its own.
- `[RULE]` **Pre-existing `open()` without `encoding=`** (loader.py:76, :82) — a real lang-review #5 item but **not introduced by this diff** (the `with ...open()` lines are unchanged context). Since Dev is already in this file, adding `encoding="utf-8"` is a 2-char cheap win — recommended, not required.
- `[TEST]` Miss-span doesn't assert `system_file`; single-system path doesn't assert span *absence* (test-analyzer #4/#5) — nice-to-have hardening.
- `[TYPE]` (subagent disabled) — manually verified: every new signature is fully annotated (rule-checker #3 confirms `_starting_region_for`, `load_orbital_content`, `_resolve_system_file`, `bind_world`, `emit_system_resolve`). No stringly-typed concern beyond the traversal (covered by SEC).
- `[SIMPLE]` (subagent disabled) — manually verified: the two-scale discriminator (`systems_dir.is_dir()`) and `_resolve_system_file` extraction are appropriately minimal; no over-engineering, no dead code.

**Data flow traced:** narrator JSON patch → `WorldPatch.current_region` → persisted `snapshot.current_region` → (resume) `bind_world` `resolved_region` → `load_orbital_content(region_id=...)` → `_resolve_system_file` → `systems_dir / f"{region_id}.yaml"`. **Unsafe at the final hop** (no path-segment validation). The authored fresh path (`cartography.starting_region`) is trusted; the persisted-resume path is the concern.

**Pattern observed (good):** OTEL `orbital.system_resolve` fires on hit AND miss before any raise (`loader.py:108`), registered in `FLAT_ONLY_SPANS` mirroring `scope_bind.py` — the GM-panel lie-detector is correctly wired (`[VERIFIED]` — `system_resolve.py:20`, miss-span proven by `test_resolution_miss_emits_system_resolve_span_with_hit_false`).

### Devil's Advocate

Argue the code is broken. A confused operator authoring a new system forgets to create `systems/<starting_region>.yaml`; at fresh connect the loader raises, but `bind_world` swallows it to `orbital_content=None` and the player gets a silently chart-less session with only a `debug`-level log — no warning, no GM-panel signal — exactly the "why isn't this quite right" debugging hole the No-Silent-Fallbacks rule exists to prevent. A malicious or simply hallucinating narrator writes `current_region: "../../../../etc/hostname"` into a world patch; on the next resume `_resolve_system_file` builds `systems/../../../../etc/hostname.yaml`, and `Path.exists()` happily probes outside the world tree — even though `OrbitsConfig` rejects the parse, the *existence* of arbitrary `.yaml` files is now observable, and the containment of a content loader has been broken by a string that should have been rejected on sight. A stressed filesystem on a non-UTF-8 host misreads a body label with an accented place name because `open()` carries no `encoding=`. A future refactorer "simplifies" the blank-region guard into a single-system fallback and ships it, because no test pins that branch and the suite stays green. None of these are exotic: each follows directly from an untested guard, an unsanitized path segment, or an overbroad catch. The happy path is genuinely good — but "good on the path the tests walk" is precisely the trap this project's wiring and No-Silent-Fallbacks doctrines are written to catch. The traversal surface is the line I will not wave through in new code; the rest is cheap hardening that belongs in the same pass.

**Handoff:** Back to TEA (Mr. Praline) for red rework — the fixes are test-first (traversal-rejection test → guard; blank-region tests; explicit-region wiring test).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation) — round-trip 1
- **Improvement** (non-blocking): The `bind_world` `except OrbitalContentMissingError` swallow still conflates "no orbital tier" with "multi-system world, region authored-but-missing" (Reviewer/rule-checker finding, now documented in the inline comment). Deferred: 98-3 (drill) / 98-5 (jump) exercise bind-time multi-system reachability and should decide whether a missing authored region warrants a typed connect error (mirroring `RegionScopeBindError`). The path-like *invalid* case is already handled (raises `ValueError`, escapes the swallow). Affects `sidequest/server/session_room.py:268-282`.

### Dev (implementation)
- **Resolved** (was TEA's blocking Question): The region id is **NOT** on the snapshot at fresh bind — confirmed in `connect.py`. Fresh path constructs `GameSnapshot(...)` with blank `current_region` and binds immediately; `region_init.init_region_location` runs later (chargen, `chargen_mixin.py:961`). Resume path loads a snapshot with `current_region` persisted. **Fix:** threaded `region_id` into `bind_world` (defaults to `snapshot.current_region` for resume) and made the fresh `connect.py` call pass `cartography.starting_region`. This stayed within the 5pt estimate (no new plumbing layer — reused the cartography lookup already done by `_bind_initial_orbital_scope`). No deviation/resize needed.
- **Gap** (non-blocking): `session_room.bind_world` still swallows `OrbitalContentMissingError` → `orbital_content=None`. For a **multi-system** world whose `starting_region` has no `systems/<id>.yaml` (a content authoring bug), this means a silently chart-less session rather than a loud failure. In practice the starting system is always authored, and the drill-into-unauthored case (AC3's real scenario) hits the loader directly and DOES fail loud — but a future story (98-3/98-5 drill/jump) should decide whether bind-time multi-system misses deserve a typed connect error like the existing `RegionScopeBindError` path. Affects `sidequest/server/session_room.py:257-266`.
- **Improvement** (non-blocking): `chart.yaml` remains world-level (cluster-wide), not per-system. Two-scale worlds currently share one flavor-annotation layer across all systems. If per-system charts are ever wanted, that's a loader + content follow-up. Out of scope for 98-2. Affects `sidequest/orbital/loader.py` (chart resolution).

### TEA (test design) — round-trip 1
- No upstream findings during rework. The Reviewer's findings were converted to tests: 3 RED guards (path traversal) + 4 coverage closures. Dev's remaining work is the path-segment guard in `_resolve_system_file` (loader.py) plus the LOW comment/encoding cleanups noted in the rework assessment.

### TEA (test design)
- **Question** (blocking): Is the party's region id reachable at the `bind_world` seam at FRESH-session bind time? My wiring test sets `snap.current_region = "yula"` and asserts `bind_world` resolves `systems/yula.yaml`. The context's own assumption flags this: if `current_region` is not yet populated at bind (chargen may set it later), Dev must thread the region from `cartography.starting_region` instead — and **log a Design Deviation, because that changes the story's size**. Affects `sidequest/server/session_room.py:259` (the `load_orbital_content(world_dir)` call) and the region source feeding it.
- **Gap** (non-blocking): The existing swallow point `except OrbitalContentMissingError: orbital_content = None` at `session_room.py:260-264` is correct for *non-orbital* worlds (no systems/ dir, no orbits.yaml) but must NOT swallow a **multi-system miss** (region with no `systems/<id>.yaml`) — AC3 requires that to fail loud. Dev must ensure the multi-system fail-loud error is distinct from / not caught by the "optional orbital tier" swallow. Affects `sidequest/server/session_room.py:259-264`.
- **Improvement** (non-blocking): The shipped-content `coyote_star` regression (AC5) is *already* exercised by `tests/orbital/test_render_coyote_star.py`, which calls `load_orbital_content(path)` with no region. My AC5 contract (single-system loads with no region key) is what keeps that existing test green — Dev should run it as part of GREEN to confirm the shipped single-system world still resolves. Affects `tests/orbital/test_render_coyote_star.py` (no change; run as regression).

### Reviewer (code review)
- **Gap** (blocking): `region_id` becomes a filesystem path segment with no validation; its runtime source (`snapshot.current_region`, a narrator-patchable `WorldPatch` field) is untrusted → CWE-22 path traversal. Affects `sidequest/orbital/loader.py:105` (`_resolve_system_file` — add a guard rejecting path separators / `..` / NUL before building the path, failing loud as an invalid region).
- **Gap** (blocking): The production-goal path (fresh multi-system connect resolving via the explicit `region_id=` kwarg) and the blank/`None` region fail-loud guard are untested. Affects `tests/orbital/test_loader_per_region.py` (add an explicit-`region_id` wiring test + blank/None region fail-loud tests).
- **Improvement** (non-blocking): The `bind_world` `except OrbitalContentMissingError` swallow is overbroad (conflates no-orbital-tier with multi-system missing/blank region) and its inline comment (`session_room.py:269-271`) is now stale. Recommend narrowing the catch (reason/subclass on the error) or an explicit deferral to 98-3/98-5; fix the comment now. Affects `sidequest/server/session_room.py:268-276`.
- **Improvement** (non-blocking): Pre-existing `open()` without `encoding="utf-8"` at `sidequest/orbital/loader.py:76,82` — a real lang-review #5 item, not introduced by this diff but cheap to close while Dev is in the file.

### Reviewer (code review) — round-trip 1
- **Improvement** (non-blocking): `test_path_traversal_does_not_load_sibling_orbits_stub` could add an `assert _spans_named(otel_capture, "orbital.system_resolve") == []` for full guard-before-probe discrimination on the stub fixture (the `..`/separator companion tests already assert this against `world_two_scale`). Optional hardening; not required — the guard is pinned three ways and is green. Affects `tests/orbital/test_loader_per_region.py`.
- **Resolved**: round-0 blocking findings (HIGH path traversal, [MED] untested production path/blank-region guard, [LOW] stale comment + `encoding=`) are all fixed and verified by the re-review subagent pass. The overbroad-swallow narrowing remains the only deferred item (→ 98-3/98-5), now documented in code + delivery findings; the path-like invalid case escapes the swallow loudly via `ValueError`.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Wired the region into the production bind path beyond loader.py**
  - Spec source: epic spec §2 / Story S1 ("principally a loader.py change"); context-story-98-2.md Files list (`loader.py`, `scope_bind.py`, `render.py`)
  - Spec text: "The per-system resolution change is principally a loader.py change (which file to load for the current region), not a render.py change."
  - Implementation: Also added a `region_id` param to `SessionRoom.bind_world` and a `_starting_region_for` helper + fresh-path call change in `handlers/connect.py`. loader.py is the core, but the region has to *reach* it.
  - Rationale: "Principally" loader, but the loader needs the region threaded from where it lives (snapshot on resume, cartography on fresh). Without the connect change, fresh perseus_cloud sessions would resolve `orbital_content=None` and never get a chart — a half-wired feature, which the server CLAUDE.md forbids. This is the wiring AC2 mandates, not scope creep.
  - Severity: minor
  - Forward impact: none for siblings — 98-3 (UI) and 98-5 (jump) consume the now-correct per-region `orbital_content`; the seam is more complete, not different.
- **`region_id` is a keyword on `load_orbital_content`, single-vs-multi discriminated by the `systems/` directory**
  - Spec source: context-story-98-2.md AC1 + AC5
  - Spec text: AC1 "resolves systems/<region_id>.yaml keyed to the party's current region"; AC5 "coyote_star … still loads as before … collapse the two scales cleanly"
  - Implementation: `load_orbital_content(world_dir, region_id=None)`; presence of a `systems/` dir selects multi-system (region-keyed, fail-loud) vs single-system (orbits.yaml, region ignored). Matches exactly the API TEA pinned in the RED tests.
  - Rationale: Lowest-friction extension of the production-wired function; the directory discriminator satisfies AC1 and AC5 without special-casing world names (per the context assumption to flag rather than special-case coyote_star).
  - Severity: minor
  - Forward impact: none.

### TEA (test design)
- **Pinned a concrete loader API the spec left open**
  - Spec source: context-story-98-2.md AC1; epic spec §2 / Story S1 AC1
  - Spec text: "loader.py resolves worlds/<world>/systems/<region_id>.yaml keyed to the party's current region"
  - Implementation: Tests commit to `load_orbital_content(world_dir, region_id: str | None = None)` — extending the existing production-wired function rather than introducing a new resolver. Single-system worlds (no `systems/` dir) load `orbits.yaml` and ignore the region key; multi-system worlds (with `systems/` dir) require the key and fail loud on a missing file.
  - Rationale: `load_orbital_content` is already the seam wired into production (`session_room.py:259`), so extending it keeps the wiring test honest and minimizes new surface. The single-vs-multi discriminator (presence of `systems/`) is the cleanest way to satisfy AC1 (per-region) and AC5 (coyote_star collapse) simultaneously without special-casing world names.
  - Severity: minor
  - Forward impact: If Dev chooses a different signature or discriminator, they must update `tests/orbital/test_loader_per_region.py` and log a matching deviation. The behavioral contract (right file per region, fail-loud-on-miss, single-system collapse, OTEL span) is non-negotiable; the exact API is the deviable part.
- **Pinned the OTEL span name and attribute keys**
  - Spec source: context-story-98-2.md AC4; epic spec Story S1 AC4
  - Spec text: "OTEL span on system-file resolution: which region, which file, hit/miss"
  - Implementation: Tests assert span name `orbital.system_resolve` with attrs `region_id`, `system_file`, `hit` (bool). Mirrors the `orbital.scope_bind` span pattern in `sidequest/telemetry/spans/scope_bind.py`.
  - Rationale: The spec names attributes but not the span id; a concrete name is needed for a verifiable assertion (house style — scope_bind tests hard-code names). Dev should add `sidequest/telemetry/spans/system_resolve.py` mirroring `scope_bind.py`.
  - Severity: minor
  - Forward impact: Renaming the span/attrs requires updating the two AC4 tests with a logged deviation.
- **Single-system regression uses a fixture, not shipped coyote_star**
  - Spec source: context-story-98-2.md AC5 ("coyote_star regression coverage")
  - Spec text: "load coyote_star; assert its orrery resolves and renders unchanged"
  - Implementation: AC5 unit tests use the synthetic `world_minimal` fixture (single `coyote` star, orbits.yaml, no systems/ dir) per the project's "no shipped content in unit tests" rule. Shipped-content coverage is delegated to the pre-existing `tests/orbital/test_render_coyote_star.py`.
  - Rationale: Honors the unit-test-isolation convention used by `test_scope_bind.py`; the shipped-content path is already a wiring/snapshot test.
  - Severity: minor
  - Forward impact: none (logged as a Delivery Finding so Dev runs the shipped-content regression at GREEN).

### Dev (implementation) — round-trip 1
- **Path-like region raises `ValueError`, not `OrbitalContentMissingError`**
  - Spec source: Reviewer Assessment rt1 (HIGH traversal); TEA rt1 guard contract
  - Spec text: "fail loud as an invalid region (ValueError or OrbitalContentMissingError both satisfy the tests)"
  - Implementation: `_resolve_system_file` raises `ValueError` for a path-like `region_id`.
  - Rationale: `OrbitalContentMissingError` is swallowed by `bind_world`'s optional-tier catch — using it would silently turn an attack/corruption into "no chart". `ValueError` propagates past that catch, so a path-like `current_region` fails loud at bind (the correct No-Silent-Fallbacks posture). The TEA tests accept either type.
  - Severity: minor
  - Forward impact: none — callers that legitimately pass clean slug region ids are unaffected; only invalid/path-like input raises.

### TEA (test design) — round-trip 1
- **Path-traversal test uses the stub fixture for an airtight RED**
  - Spec source: Reviewer Assessment (round-trip 1), HIGH path-traversal finding
  - Spec text: "reject a region_id containing a path separator, `..`, or NUL before building the path"
  - Implementation: The primary RED test resolves `region_id="../orbits"` against `world_two_scale_stub` (which has an EXISTING sibling `orbits.yaml`), so a raise can only originate from a guard — not from a missing file. Complemented by two span-absence tests (`..` and bare `/`) proving the guard fires before the filesystem probe.
  - Rationale: A naive "raises on `../x`" test would pass vacuously against `world_two_scale` (the escaped file doesn't exist → generic miss raise), failing to drive the guard. The stub world + span-absence assertions force a real pre-probe guard.
  - Severity: minor
  - Forward impact: none — the guard contract (reject path-like region before path construction) is pinned three ways.

### Reviewer (audit)
- **Dev: "Wired the region into the production bind path beyond loader.py"** → ✓ ACCEPTED by Reviewer: sound and required — the epic spec's "principally a loader.py change" does not preclude threading the region to the loader; without the `bind_world`/`connect.py` wiring the feature is half-wired (CLAUDE.md forbids). Agrees with author reasoning.
- **Dev: "`region_id` keyword, single-vs-multi discriminated by the `systems/` directory"** → ✓ ACCEPTED by Reviewer: the directory discriminator cleanly satisfies AC1 + AC5 without special-casing world names, matching the context's "flag rather than special-case" guidance. Sound.
- **TEA: "Pinned a concrete loader API the spec left open"** → ✓ ACCEPTED by Reviewer: extending the production-wired `load_orbital_content` is the minimal, honest seam. Agrees.
- **TEA: "Pinned the OTEL span name and attribute keys"** → ✓ ACCEPTED by Reviewer: concrete span id is necessary for a verifiable assertion; mirrors `scope_bind.py` house style. Sound.
- **TEA: "Single-system regression uses a fixture, not shipped coyote_star"** → ✓ ACCEPTED by Reviewer: honors the no-shipped-content-in-unit-tests convention; shipped coverage delegated to the existing render test (which the full regression confirmed green). Sound.
- **UNDOCUMENTED (Reviewer-spotted):** `region_id` is interpolated into a filesystem path (`_resolve_system_file`, loader.py:105) with no path-segment validation. Neither TEA nor Dev logged the security implication of making a (narrator-influenceable) region string a path component. Spec/SOUL implied (No Silent Fallbacks + lang-review #5/#11): a path-like region is invalid input and must fail loud, not silently traverse. Code does neither — it builds the path and probes `exists()`. Severity: **H**. This is the blocking finding above. → **RESOLVED in round-trip 1** (guard added; verified closed by re-review rule-checker).

### Reviewer (audit) — round-trip 1
- **Dev rt1: "Path-like region raises `ValueError`, not `OrbitalContentMissingError`"** → ✓ ACCEPTED by Reviewer: correct and load-bearing — `ValueError` propagates past `bind_world`'s `except OrbitalContentMissingError`, so invalid input fails loud (rule-checker #1 confirmed it is not swallowed). The right call.
- **TEA rt1: "Path-traversal test uses the stub fixture for an airtight RED"** → ✓ ACCEPTED by Reviewer: the stub world (existing sibling `orbits.yaml`) makes the escape provable and the RED non-vacuous; the companion span-absence tests instrument the guard-before-probe claim. Sound test design.