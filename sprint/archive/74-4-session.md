---
story_id: "74-4"
jira_key: ""
epic: "74"
workflow: "tdd"
---
# Story 74-4: World-flavor hardening: isinstance shape-guard on raw world theme/audio, weather-absence OTEL span, remove dead seed_lore_from_genre_pack

## Story Details
- **ID:** 74-4
- **Jira Key:** (none — personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-server
- **Base Branch:** develop

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-03T23:25:34Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T22:47:26Z | 2026-06-03T22:51:21Z | 3m 55s |
| red | 2026-06-03T22:51:21Z | 2026-06-03T23:04:08Z | 12m 47s |
| green | 2026-06-03T23:04:08Z | 2026-06-03T23:13:24Z | 9m 16s |
| spec-check | 2026-06-03T23:13:24Z | 2026-06-03T23:15:03Z | 1m 39s |
| verify | 2026-06-03T23:15:03Z | 2026-06-03T23:19:32Z | 4m 29s |
| review | 2026-06-03T23:19:32Z | 2026-06-03T23:24:35Z | 5m 3s |
| spec-reconcile | 2026-06-03T23:24:35Z | 2026-06-03T23:25:34Z | 59s |
| finish | 2026-06-03T23:25:34Z | - | - |

## Acceptance Criteria

### AC1: isinstance shape-guard on raw world theme/audio
- Loader at `sidequest-server/sidequest/genre/loader.py:1077` loads `world_theme` and `world_audio` via `_load_yaml_raw_optional` returning `Any` with no shape validation
- Add isinstance(dict) shape-guards that fail loud (raise GenreLoadError / LoadError with clear message)
- Prevents silent flow-through of malformed (non-dict) world theme.yaml / audio.yaml
- Violates "No Silent Fallbacks" principle otherwise
- Wiring test: verify a malformed world.yaml triggers the guard

### AC2: weather-absence OTEL span
- Existing spans: `world_grounding.weather_proposed` / `weather_used` in `sidequest/telemetry/spans/world_grounding.py`
- Add companion span for when a world authors NO weather (`weather absent`)
- Allows GM panel to distinguish "no weather by design" from "weather subsystem broken"
- Honors OTEL Observability Principle: every backend fix must add watcher events
- Wiring test: verify span fires for a world without weather

### AC3: Remove dead seed_lore_from_genre_pack
- Function defined at `sidequest/game/lore_seeding.py:53`, exported at `:476`
- Dead for production after 74-3 deleted genre-tier lore
- CAUTION: one reference at `sidequest/server/websocket_handlers/chargen_mixin.py:1124` + tests in:
  - `tests/game/test_lore_seeding.py` (one test already xfails as "deleted in epic 74" at :232)
  - `tests/server/test_lore_seeding_dispatch.py`
  - `tests/server/test_lore_store_resume_reseed.py`
  - `tests/genre/test_genre_flavor_world_tier.py`
- Delete dead code + its now-orphaned tests in the SAME PR (house rule)
- Verify every caller is gone/dead BEFORE deleting

## Sm Assessment

**Setup complete — ready for RED (TEA/Igor).**

Story 74-4 is the hardening tail of epic 74 (genre=mechanics-only). 74-1 (loader refactor)
and 74-3 (world lore authored) are done; this story closes three loose ends, all in
`sidequest-server`, all grounded in real code:

1. **AC1 — shape guard** at `loader.py:1077`: `world_theme`/`world_audio` load as `Any` via
   `_load_yaml_raw_optional` with no validation. A non-dict flavor file flows through
   silently → violates No Silent Fallbacks. Guard must raise the loader's error type
   naming the file + bad type. Mirror the mandatory-file precedent.
2. **AC2 — weather-absence OTEL span**: companion to existing
   `world_grounding.weather_proposed`/`weather_used` in `telemetry/spans/world_grounding.py`.
   Distinguishes "no weather by design" from "subsystem broken" on the GM panel.
3. **AC3 — delete dead `seed_lore_from_genre_pack`** (`lore_seeding.py:53/:476`): dead after
   74-3. **CAUTION** — verify the live ref at `chargen_mixin.py:1124` is genuinely dead
   before deleting; remove orphaned genre-seed tests (4 files; one already xfails at
   `test_lore_seeding.py:232`) in the SAME PR. Keep `seed_lore_from_world` intact.

**Risk flag for TEA:** AC3 is the one with teeth — the chargen_mixin caller must be proven
dead, not assumed. Don't delete the symbol while any production path still imports it.

**Test env:** full suite with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set, else
phantom DB errors / skipped calibration tests. Record baseline failures before RED.

**No Jira** — personal project. Context: `sprint/context/context-story-74-4.md` (validated).

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (11 failing, ready for Dev) + 6 green guards

**Test Files:**
- `tests/genre/test_world_flavor_shape_guard_74_4.py` — AC1: non-dict world theme/audio → `GenreLoadError` (3 RED) + valid-dict / absent-file load guards (2 green)
- `tests/telemetry/spans/test_world_grounding_weather_absent_74_4.py` — AC2: `world_grounding.weather_absent` constant/route/helper/extract (5 RED)
- `tests/agents/tools/test_grounding_weather_absent_wiring_74_4.py` — AC2 wiring: absent span fires from real `get_world_grounding` when weather requested-but-unwired, mutually exclusive with `weather_used` (1 RED + 3 green negatives)
- `tests/game/test_seed_lore_genre_pack_removed_74_4.py` — AC3: dead `seed_lore_from_genre_pack` removed from module + `__all__` (2 RED) + survivor `seed_world_lore` seeds world lore / zero genre (1 green)

**Tests Written:** 17 tests (11 RED + 6 green guards) covering 3 ACs
**RED verified:** `uv run pytest -n0` with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_TEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set → 11 failed, 6 passed. All failures are for the right reason (missing behavior, not test bugs).

### What Dev must build to go GREEN
1. **AC1** — in `loader.py` at the `world_theme`/`world_audio` seam (~:1077), after the raw load, add a shape guard: `if value is not None and not isinstance(value, dict): raise GenreLoadError(path=world_path / "<file>.yaml", detail="expected a mapping, got <type>")`. Must accept `None` (absent) and dict; reject list/scalar. Mirror `_parse_char_creation_scenes` (loader.py:151).
2. **AC2** — add `SPAN_WORLD_GROUNDING_WEATHER_ABSENT = "world_grounding.weather_absent"`, register a `SPAN_ROUTES` entry (component `world_grounding`, event_type `state_transition`, extract `field=weather`/`op=absent`/`world_id`), add `emit_weather_absent_span(*, world_id, perspective_pc)` (encode `perspective_pc or ""`), re-export both from `telemetry/spans/__init__.py`, and call it in `get_world_grounding.py` in the `else` of the `weather_used` branch (`"weather" in args.include and ctx.weather_state is None`).
3. **AC3** — delete `seed_lore_from_genre_pack` (`lore_seeding.py:53`) + its `__all__` entry (:476). **Then delete the orphaned tests that import it** or the suite breaks at collection: `tests/game/test_lore_seeding.py` (import at :17, class `TestSeedFromGenrePack` ~:152, and `test_world_seed_does_not_collide_with_genre_seed` ~:237). Stale *comment* mentions (`chargen_mixin.py:1124`, `lore_seeding.py:10/:179`, `test_lore_seeding_dispatch.py:169`, `test_lore_store_resume_reseed.py:7`, `test_genre_flavor_world_tier.py:261`) are non-breaking but should be cleaned for honesty.

### Rule Coverage (python lang-review checklist)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions / fail-loud | AC1 `test_non_dict_world_theme/audio_raises_genre_load_error` (must raise, not swallow) | failing (RED) |
| #6 test quality (meaningful assertions) | self-check — all 17 tests assert specific values / message substrings / `== []` / `len()`; no vacuous, no `assert True`, no bare-truthy-on-None | pass |
| #8 unsafe deserialization | N/A — loader already uses `yaml.safe_load`; new code adds no deserialization | n/a |
| #3 type annotations at boundaries | architectural note: Dev's `emit_weather_absent_span` + shape guard must annotate params/return (enforced at Reviewer + ruff/pyright, not behaviorally testable) | deferred to Dev |

**Rules checked:** #1 and #6 have direct test coverage; #3 noted for Dev; #2/#4/#5/#7/#9-13 not applicable to this change set.
**Self-check:** 0 vacuous tests found (all assertions check specific values or exception identity + message).

**Handoff:** To Ponder Stibbons (Dev) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-server):**
- `sidequest/genre/loader.py` — AC1: isinstance shape-guard on raw world `theme.yaml`/`audio.yaml` in `_load_single_world`; non-mapping → world-scoped `GenreLoadError` naming the file; `None` (absent) and dict still load.
- `sidequest/telemetry/spans/world_grounding.py` — AC2: `SPAN_WORLD_GROUNDING_WEATHER_ABSENT` constant + `SPAN_ROUTES` extract (`field=weather`/`op=absent`/`world_id`/`perspective_pc`) + `emit_weather_absent_span(*, world_id, perspective_pc)` helper.
- `sidequest/telemetry/spans/__init__.py` — AC2: re-export `emit_weather_absent_span` (constant rides `import *`).
- `sidequest/agents/tools/get_world_grounding.py` — AC2: fire `emit_weather_absent_span` in the `elif` of the `weather_used` branch (weather requested but `ctx.weather_state is None`); mutually exclusive with `weather_used`.
- `sidequest/game/lore_seeding.py` — AC3: deleted dead `seed_lore_from_genre_pack` + its `__all__` entry; cleaned 2 stale comments.
- `sidequest/server/websocket_handlers/chargen_mixin.py` — AC3: rewrote the stale lore-seeding comment block to reflect world-only lore.
- `tests/game/test_lore_seeding.py` — AC3: removed the symbol import, the `TestSeedFromGenrePack` class, and `test_world_seed_does_not_collide_with_genre_seed` (kept shared `caverns_pack` fixture + world-seed tests); cleaned module docstring.

**Tests:** Full server suite **9979 passed / 343 skipped / 0 failed** (with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_TEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set). All 11 RED tests now GREEN; 6 green-guards still pass; no regressions. `ruff check` + `ruff format --check` clean on all changed files.

**Branch:** `feat/74-4-world-flavor-hardening` (pushed to origin)

**Self-review:** AC1/AC2 emit loud errors / OTEL spans (No Silent Fallbacks + OTEL Observability honored); AC2 span wired into a real production handler (verified by the wiring test, not just the helper); AC3 deletion verified zero remaining consumers tree-wide. No stubs, no debug code.

**Handoff:** To Igor (TEA) for verify (simplify + quality-pass).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None requiring code change (2 minor notes, both already captured as findings)

Reviewed the production diff against all three ACs in `context-story-74-4.md`:

- **AC1 (shape guard):** Aligned. `loader.py` guards `theme.yaml`/`audio.yaml` with `value is not None and not isinstance(value, dict)` → world-scoped `GenreLoadError` naming the file. Correctly accepts `None` (absent → genre fallback) and dict. Mirrors the `_parse_char_creation_scenes` fail-loud precedent as the AC intended. Honors No Silent Fallbacks.
- **AC2 (weather-absent span):** Aligned. Constant + `SPAN_ROUTES` extract (`field=weather`/`op=absent`, routed as `state_transition`/`world_grounding`, not flat-only) + `emit_weather_absent_span` helper, wired as the `elif` of `weather_used` in `get_world_grounding.py`. Mutually exclusive with `weather_used`, verified by the wiring test against the real `default_registry.dispatch` path — not a helper-only assertion.
- **AC3 (dead-code removal):** Aligned. `seed_lore_from_genre_pack` + its `__all__` entry deleted; orphaned genre-seed tests removed; `seed_lore_from_world`/`seed_world_lore` intact. Full-suite green (9979/0) confirms zero remaining consumers — the SM/TEA risk flag (chargen_mixin caller) was correctly resolved as a stale *comment*, not a live call.

Minor notes (no code change in this story):
- **`visual_style.yaml` lacks the same shape guard** (Missing in code — Behavioral, Trivial). It is loaded raw alongside theme/audio but AC1 scopes the guard to theme/audio only, so the code is faithful to the spec. **Recommendation: D (Defer)** — natural fold-in for a follow-up; already logged by both TEA and Dev.
- **AC2 fires on "requested-but-unwired", narrower than the AC's looser wording "world authors no weather"** (Ambiguous spec — Behavioral, Trivial). The implemented seam (narrator asked for weather, session has none) is the correct lie-detector point — firing every turn regardless of request would be noise. **Recommendation: C (Clarify)** — code is right; AC wording is just looser than the precise seam. Noted for traceability, no change needed.

**Decision:** Proceed to review (verify phase / TEA).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (17/17 story tests pass; full suite 9979/0 from green phase, tree unchanged since)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 11 (6 production + 5 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 — span attr-extraction + lore-fragment patterns already at minimal abstraction; story removes dup (dead code), adds none |
| simplify-quality | clean | 0 — fail-loud guard, span conventions followed, mutual-exclusivity correctly if/elif-guarded, no dangling refs after deletion |
| simplify-efficiency | clean | 0 — additive code mirrors existing patterns; the only removal is dead code (opposite of over-engineering) |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** All passing (ruff check + format clean from green phase; tree unchanged, 0 simplify edits → no regression run needed)
**Handoff:** To Granny Weatherwax (Reviewer) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | tests GREEN 9980/0 (342 skip); 0 smells; lint/format YELLOW (all pre-existing, none in diff) | confirmed 0, dismissed 0 (lint/format pre-existing & outside diff), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([EDGE] below) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([SILENT] below) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([TEST] below) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([DOC] below) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([TYPE] below) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([SEC] below) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([SIMPLE] below) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — covered by Reviewer ([RULE] below) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` and covered by my own analysis)
**Total findings:** 0 confirmed blocking, 2 LOW non-blocking (pre-existing, outside diff), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

A small, disciplined, three-AC diff. I verified each AC against the real code, not the assessment prose, and hunted the domains the disabled subagents would have covered.

**Observations (tagged):**
- `[VERIFIED]` **AC1 guard fails loud and early** — `loader.py:1080` runs `if _flavor_value is not None and not isinstance(_flavor_value, dict): raise GenreLoadError(...)` BEFORE the `_emit_world_flavor_loaded` loop (:1103) and `World(...)` (:1239), so a malformed flavor file never emits a spurious "loaded" span and never reaches the opaque pydantic path. Accepts `None` (absent) and dict. Complies with No Silent Fallbacks.
- `[VERIFIED][SEC]` **No new attack surface** — the absence span records `world_id`/`perspective_pc` (session-derived, not user free-text); the loader reads local YAML via `yaml.safe_load` (no `yaml.load`/`pickle`/`eval` added). Nothing user-controlled is interpolated. (lang-review #8, #11)
- `[VERIFIED][TYPE]` **Boundary annotated** — `emit_weather_absent_span(*, world_id: str, perspective_pc: str | None) -> None` is fully typed and keyword-only, matching its sibling `emit_weather_used_span`. (lang-review #3)
- `[VERIFIED][SILENT]` **Nothing swallowed** — the new code raises (guard) and emits (span); the `elif "weather" in args.include and ctx.weather_state is None` is the exhaustive complement of the `weather_used` `if` for the weather-requested case. No bare `except`, no silent fallback. (lang-review #1)
- `[VERIFIED][SIMPLE]` **Clean excision** — grep confirms ZERO production callers/imports of `seed_lore_from_genre_pack` remain; `seed_world_lore`/`seed_lore_from_world` intact; `GenrePack`/`LoreSource` imports still used (no orphaned imports). 73 lines of dead code gone.
- `[VERIFIED][TEST]` **No vacuous pass introduced** — `test_lore_seeding_dispatch.py` asserts `len(genre_pack_frags) == 0` *directly* (explicitly avoiding the empty-`all()` trap); the new AC3 removal test uses the CLAUDE.md-sanctioned reflection tripwire (`hasattr` + `__all__`); the AC2 wiring test drives the real `default_registry.dispatch` (not helper-only) across 4 mutual-exclusivity cases.
- `[VERIFIED][EDGE]` **Boundary cases covered** — empty file → `yaml.safe_load("")` → `None` → valid-absent (tested); list/scalar → raise (tested); `include=[]` and `include=["demographics"]` → no absent span (tested); single-player `perspective_pc=None` → encoded `""` (tested).
- `[LOW][DOC]` **Pre-existing stale comments** — `test_lore_seeding_dispatch.py:165-172` ("...PLUS the genre pack's lore corpus ... wired `seed_lore_from_genre_pack`") contradicts that same file's `genre_pack_frags == 0` assertion; `test_lore_store_resume_reseed.py:7` docstring lists the removed seeder. **Both are PRE-EXISTING and OUTSIDE this PR's 11-file diff** — Dev correctly did not expand scope to touch unrelated files. Non-blocking; flagged for a future doc-cleanup sweep (see Delivery Findings).
- `[VERIFIED][RULE]` Rule compliance enumerated below.

### Rule Compliance (python lang-review checklist)

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | silent exceptions | PASS | guard raises `GenreLoadError`; no `except` added |
| 2 | mutable defaults | PASS | no mutable defaults introduced |
| 3 | type annotations at boundaries | PASS | `emit_weather_absent_span` params+return annotated |
| 4 | logging coverage/level | N/A | observability is via OTEL span, not logging |
| 5 | path handling | PASS | `world_path / "theme.yaml"` uses `pathlib` `/` |
| 6 | test quality | PASS | direct `== 0` assertion; reflection tripwire (allowed); no vacuous |
| 7 | resource leaks | PASS | `Span.open(...)` used as `with` context manager |
| 8 | unsafe deserialization | PASS | `yaml.safe_load` only; no new pickle/eval |
| 9 | async pitfalls | PASS | sync emit in async handler, no blocking call / missing await |
| 10 | import hygiene | PASS | `__init__` explicit import alphabetized; local import mirrors sibling |
| 11 | input validation | PASS | the guard IS validation at the YAML boundary |
| 12 | dependency hygiene | N/A | no dependency changes |
| 13 | fix-introduced regressions | PASS | full suite 9980/0 |

### Devil's Advocate

Let me try to break it. **The guard:** what if a world authors `theme.yaml` as an empty mapping `{}`? `{}` is a dict → passes the guard → flows to `World.theme` as an empty dict. Is that a silent acceptance of garbage? No — an empty mapping is a structurally valid (if useless) theme; the guard's contract is *shape*, not *richness*, and `World.theme: dict | None` accepts it. Acceptable. What about a YAML file containing only a comment? → `safe_load` returns `None` → treated as absent → genre fallback. Correct. What about a dict with non-string keys (`{1: "x"}`)? pydantic coerces to `{"1": "x"}` at `World()` — the guard lets it through (it IS a dict), but that's the pre-existing `World.theme: dict[str, Any]` contract, not a regression this story introduces. **The span:** could `weather_absent` AND `weather_used` both fire? No — `if/elif` on the same `ctx.weather_state is None` predicate is mutually exclusive by construction; the wiring test proves it. Could the span fire on every turn and spam the dashboard? Only when the narrator *requests* weather and it's unwired — bounded by tool-call frequency, identical cadence to `weather_used`. **The deletion:** could a save-file or pickled state reference the removed symbol? No — `seed_lore_from_genre_pack` was a function, never serialized; saves hold lore *fragments*, not seeder references. Could a downstream genre pack with genre-tier `lore.yaml` now silently lose its lore? That lore was already not seeded post-74-3 (the function had zero callers); the deletion changes nothing at runtime. **Confused author:** someone copies a list-shaped `audio.yaml` from another tool → now gets a clear `GenreLoadError` naming the file instead of a 40-line pydantic traceback. That's the improvement. I cannot find a correctness break.

**Data flow traced:** world `theme.yaml`/`audio.yaml` on disk → `_load_yaml_raw_optional` → shape guard (raise if non-dict-non-None) → `World.theme`/`.audio` (safe because the guard guarantees dict|None before pydantic). And: narrator tool call `get_world_grounding(include=[weather])` + `ctx.weather_state is None` → `emit_weather_absent_span` → `SPAN_ROUTES` → GM panel (safe because mutually exclusive with `weather_used`).
**Pattern observed:** new span mirrors `emit_weather_used_span` exactly (`world_grounding.py`); guard mirrors `_parse_char_creation_scenes` fail-loud shape check.
**Error handling:** malformed flavor → loud world-scoped `GenreLoadError`; absent → valid fallback; no swallow.

**Handoff:** To Captain Carrot (SM) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): AC1's premise "silent flow-through" is inaccurate — a non-dict world `theme.yaml`/`audio.yaml` does NOT pass silently today; it raises an *opaque* `pydantic.ValidationError` deep at `World(...)` construction (`loader.py:1222`) that names neither the file nor the world. The real fix is converting that opaque error into a loud, world-scoped `GenreLoadError` at the load seam (~`loader.py:1077`). Affects `sidequest/genre/loader.py` (add isinstance(dict) guard before `effective_theme`/`World()`; mirror the existing `_parse_char_creation_scenes` fail-loud shape guard at `loader.py:151`). *Found by TEA during test design.*
- **Gap** (non-blocking): `visual_style` (`loader.py:1067`, `_load_yaml_raw_optional(... "visual_style.yaml")`) has the IDENTICAL raw-load-without-shape-guard as theme/audio, but AC1 names only theme/audio so it is out of this story's scope and untested here. A malformed world `visual_style.yaml` would surface the same opaque failure mode. Affects `sidequest/genre/loader.py` (candidate follow-up story, or fold into AC1 if Dev/Reviewer agree it is one guard). *Found by TEA during test design.*
- **Improvement** (non-blocking): `seed_world_lore` (`lore_seeding.py:209`) still returns a 2-tuple whose first element `genre_added` is hardcoded `0` (always), and `chargen_mixin.py:1178` unpacks `genre_lore_added, world_lore_added = seed_world_lore(...)` then emits `genre_fragments=%d`. Now that genre lore is provably dead (AC3), that always-0 channel is vestigial surface that could be collapsed to a single int in a later cleanup. Out of 74-4 scope. Affects `sidequest/game/lore_seeding.py` + `sidequest/server/websocket_handlers/chargen_mixin.py`. *Found by TEA during test design.*
- **Gap** (non-blocking): The AC2 wiring tests (`tests/agents/tools/test_grounding_weather_absent_wiring_74_4.py`) require `SIDEQUEST_TEST_DATABASE_URL` (the agents conftest gates the DB-backed `default_registry.dispatch` path and SKIPS without it). The full-suite gate sets it; a scoped run that omits it will silently skip these — do not read a skip as a pass. Affects test env only. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): Confirmed during implementation that `visual_style.yaml` (loader.py, loaded raw alongside theme/audio) has the identical missing shape-guard — the new AC1 guard loop could be extended to it with one tuple entry (`("visual_style.yaml", visual_style)`), but it is out of 74-4's AC scope (AC1 names theme/audio only). Affects `sidequest/genre/loader.py`. Natural fold-in for a follow-up or for Reviewer to rule on. *Found by Dev during implementation.*
- No other upstream findings during implementation. Full server suite green (9979 passed / 343 skipped / 0 failed); no consumers of the removed `seed_lore_from_genre_pack` remain anywhere in the tree.

### TEA (test verification)
- No upstream findings during test verification. Simplify pass clean across all three lenses (reuse/quality/efficiency, 0 findings); GREEN intact; no fixes applied.

### Reviewer (code review)
- **Improvement** (non-blocking): Two pre-existing stale comments reference the now-removed `seed_lore_from_genre_pack` as if current — `tests/server/test_lore_seeding_dispatch.py:165-172` (contradicts that file's own `genre_pack_frags == 0` assertion) and `tests/server/test_lore_store_resume_reseed.py:7` (docstring). Both are OUTSIDE this PR's 11-file diff, so correctly left untouched. Affects those two test files (doc-only cleanup in a future sweep). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `visual_style.yaml` (loader.py) shares theme/audio's raw-load pattern and lacks the same shape guard; out of AC1 scope (theme/audio only). Affects `sidequest/genre/loader.py` (one-line fold-in for a follow-up). Corroborates TEA + Dev findings. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Empty/null theme/audio NOT tested as a guard target**
  - Spec source: context-story-74-4.md, AC1 ("a non-mapping (e.g. a list, scalar, or empty/`null`)")
  - Spec text: lists "empty/`null`" among the malformed shapes the guard should reject
  - Implementation: tests assert only `list` and `scalar` raise `GenreLoadError`; an empty/`None` file is treated as VALID (absent → genre fallback) and the green-guard `test_absent_world_theme_audio_still_loads` asserts it loads
  - Rationale: `_load_yaml_raw_optional` returns `None` for both absent and empty files (`yaml.safe_load("") is None`), and `None` is the documented valid "world authors no theme/audio" case (loader.py:1085 `if value is not None`). Guarding `None` would break the transitional genre-fallback contract. The guard must target non-null non-dict values only.
  - Severity: minor
  - Forward impact: Dev's guard must accept `None` (absent) and reject only non-dict non-None values; Reviewer should confirm the guard is `value is not None and not isinstance(value, dict)`, not `not isinstance(value, dict)`.
- **AC3 survivor proof at the seed_world_lore seam, not the full chargen websocket handler**
  - Spec source: context-story-74-4.md, AC3 wiring proof ("world-lore seeding still reaches the LoreStore through the chargen path")
  - Spec text: asks for a test proving world-lore seeding survives "through the chargen path"
  - Implementation: `test_seed_world_lore_seeds_world_lore_and_zero_genre` drives `load_genre_pack` → `seed_world_lore` directly (the single source of truth the chargen handler calls at `chargen_mixin.py:1178`), not the full WebSocket chargen-confirm handler
  - Rationale: the chargen handler delegates verbatim to `seed_world_lore`; exercising that seam proves the survivor without standing up a full session/WS fixture (heavier, slower, and already covered by `tests/server/test_chargen_persist_and_play.py` for the handler wiring itself)
  - Severity: minor
  - Forward impact: none — the production call site is the same function under test

### Dev (implementation)
- No deviations from spec. All three ACs implemented exactly as TEA's tests demanded: AC1 guard is `value is not None and not isinstance(value, dict)` (accepts absent/dict, rejects list/scalar) raising world-scoped `GenreLoadError`; AC2 `weather_absent` span wired as the `elif` of the `weather_used` branch (mutual exclusivity per the tests); AC3 deleted the function + `__all__` entry + orphaned tests, keeping `seed_world_lore`/`seed_lore_from_world`. Stale-comment cleanup in `lore_seeding.py` + `chargen_mixin.py` is house-rule honesty (delete-dead-code-in-same-PR), not a spec change.

### Reviewer (audit)
- **TEA — "Empty/null theme/audio NOT tested as a guard target"** → ✓ ACCEPTED by Reviewer: correct — `safe_load("")` → `None` → valid-absent (genre fallback); the guard `is not None and not isinstance(...)` honors this exactly, and the implementation matches.
- **TEA — "AC3 survivor proof at the seed_world_lore seam, not the full chargen websocket handler"** → ✓ ACCEPTED by Reviewer: the chargen handler delegates verbatim to `seed_world_lore` (`chargen_mixin.py:1178`); testing that seam is sufficient, and `tests/server/test_chargen_persist_and_play.py` already covers the handler wiring.
- **Dev — "No deviations from spec"** → ✓ ACCEPTED by Reviewer: verified against the diff — implementation matches the ACs and TEA's tests with no divergence.
- No UNDOCUMENTED deviations found. AC1's theme/audio scope (not visual_style) is faithful to the AC wording, not a deviation; the two pre-existing stale comments are outside this PR's diff.

### Architect (reconcile)
- No additional deviations found. Verified the existing entries against the merged diff and `context-story-74-4.md`:
  - **TEA entry 1 (empty/null not a guard target):** accurate — spec source `context-story-74-4.md` AC1 exists; the quoted "list, scalar, or empty/`null`" is a real excerpt; implementation (`_flavor_value is not None and not isinstance(_flavor_value, dict)` at `loader.py:1080`) matches; forward impact (guard must accept `None`) is correct and was honored. All 6 fields present.
  - **TEA entry 2 (AC3 survivor at the seed_world_lore seam):** accurate — the chargen handler delegates to `seed_world_lore` (`chargen_mixin.py:1178`); the test exercises that exact function; forward impact "none" is correct. All 6 fields present.
  - **Dev entry (no deviations):** verified — the three ACs were implemented exactly as specified and as TEA's tests demanded; no divergence to document.
- **AC deferral check:** no-op — all three ACs are DONE (none deferred or descoped), so there are no deferral justifications to cross-reference against the Reviewer's findings.
- The two non-blocking Improvements (visual_style guard fold-in; pre-existing stale comments) are findings, not spec deviations — AC1 is scoped to theme/audio and the comments are outside this PR's diff.