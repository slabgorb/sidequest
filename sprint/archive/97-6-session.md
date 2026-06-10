---
story_id: "97-6"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 97-6: test_chargen_name_rig_extraction xdist flake — pg-gated pair fails order-dependently in parallel full-suite runs

## Sm Assessment

**Story:** 97-6 — xdist isolation flake in `tests/server/test_chargen_name_rig_extraction.py::TestNameRigExtractionWiring`. The pair `extracted_name_and_renamed_rig` + `extraction_decisions_are_observable` fails order-dependently in full-suite parallel runs: the `chargen.names_extracted` span is absent from the `InMemorySpanExporter` capture. Passes in isolation, serially, and per-directory. These pg-gated tests only began running once `SIDEQUEST_TEST_DATABASE_URL` joined the standard env (previously silently skipped).

**Root-cause hypothesis (for TEA to confirm, not assume):** shared tracer-provider / span-exporter global state across tests within an xdist worker, or an extraction-path module global raced by a sibling test. The span isn't lost in production — it's the *test harness's* capture that's leaking across tests.

**Directive (load-bearing):** Fix the **isolation**, not the assertion. Do not weaken/skip/xfail the span check or mark the tests pg-only to dodge the race. The OTEL span IS the lie-detector for chargen name extraction (CLAUDE.md OTEL principle) — muting it defeats the test's purpose.

**Workflow:** tdd (phased) — Red first. TEA: reproduce the isolation failure deterministically if feasible (e.g. force the adverse ordering / shared-exporter condition), then Dev fixes isolation so the span is reliably captured.

**Repo:** server only. **Scope:** test-harness/fixture isolation + the named test module; no production extraction-path behavior change unless a genuine global is the culprit.

**ACs:** (1) pair passes 5 consecutive full-suite parallel runs; (2) root cause documented in the test docstring.

**Routing:** → TEA (The Architect), red phase, `tests_fail` gate.

## TEA Assessment (red)

**RED state:** achieved deterministically (single process, serial, 0.36s — no xdist or broken-env dependence).

**Root cause (confirmed by captured traceback, see Architect finding):** NOT OTEL. The pair fails at the first line `_connect`, because `tests/server/conftest.py::seed_slug_for_test` defaults to a FIXED slug `"test-slug"`. 18 server-test call sites share it; they seed different genres into the session-scoped, commit-based `migrated_db`; the `sessions` upsert (`ensure_session`, `ON CONFLICT DO UPDATE SET last_played`) never updates `genre_slug`, so the first seeder wins and a later same-slug seed silently keeps the stale genre. The chargen pair reads the real content tree where the leaked `test_genre` doesn't exist → genre-load ErrorMessage → both tests die before any span fires. "Span absent" was a symptom.

**Test added:** `TestSeedSlugIsolation::test_default_slug_does_not_collide_across_sibling_seeds` (in `tests/server/test_chargen_name_rig_extraction.py`). Encodes the isolation contract deterministically: two sibling `seed_slug_for_test` calls (default slug, different genres) against one pool must (1) return DISTINCT slugs and (2) each carry its own genre. Fails today on `assert 'test-slug' != 'test-slug'`. A thorough root-cause docstring on the class satisfies AC2 ("root cause documented in the test docstring").

**Fix for Dev (GREEN):** make `seed_slug_for_test`'s `slug` default a unique uuid-namespaced value (e.g. `f"test-{uuid4().hex[:8]}"`), mirroring `tests/dungeon/conftest.py`'s already-documented rule. No production change. Then grep-verify no test asserts on the literal `"test-slug"` on the read side (all 18 sites thread the *returned* slug; 0 pass an explicit `slug=`). Do NOT "fix" it by changing the production `ensure_session` upsert — that would clobber genre on real reconnects.

**AC verification plan (verify phase):** AC1 — run the full suite under `-n auto` 5× consecutively with the chargen pair green (and ideally re-run the historical dirty-env condition to confirm the collision is gone). AC2 — docstring present (done in RED).

**Rule Coverage:**
- *Meaningful assertions* (TEA discipline): both new assertions check concrete values (`slug_first != slug_second`, `genre_slug == "genre_beta"`) with diagnostic messages — no vacuous `is_not_none`-only checks.
- *Every suite needs a wiring/integration test* (CLAUDE.md): the existing `TestNameRigExtractionWiring` pair is the end-to-end integration test driving the real connect+walk path; the new test is the focused isolation unit. Both ship together.
- *No source-text wiring tests* (CLAUDE.md): the new test asserts runtime behavior (returned slugs + DB rows), not source-string greps.
- *Fix the isolation, not the assertion* (story directive): the OTEL span assertions in the pair are untouched; the fix targets the slug-isolation defect.

**Deviation from story hypothesis:** the SM/PR-741 OTEL hypothesis is falsified; logged under Design Deviations → TEA. The story's scope ("test-harness/fixture isolation, server only, no production change") still holds exactly.

## Dev Assessment (green)

**Implementation:** one-line-class fix in `tests/server/conftest.py::seed_slug_for_test` — `slug` now defaults to a unique uuid-namespaced value per call (`slug: str | None = None`; `if slug is None: slug = f"test-{uuid.uuid4().hex[:8]}"`). Added `import uuid`. No production code changed. Matches the recommended fix and `tests/dungeon/conftest.py`'s documented precedent.

**Collateral:** refreshed the now-stale shared-slug rationale in `tests/server/test_scenario_bind.py::_pg_isolation` docstring (it claimed dispatch tests "share a fixed slug" — no longer true; TRUNCATE kept as defence-in-depth).

**GREEN evidence:**
- New RED test `TestSeedSlugIsolation` now passes; full chargen file 3 passed serial.
- All 18 `seed_slug_for_test` consumer files (server + game): **89 passed, 0 failed** under clean env (`-n auto`).
- `test_scenario_bind` (which relied on the old shared default slug + TRUNCATE): 13 passed.
- Robustness: re-ran the full suite **8× under the *exact reproducing condition*** (dirty env, `SIDEQUEST_DATABASE_URL` unset, `-n auto`) — **chargen pair GREEN 8/8** (was ~1/7 fail before the fix). The 23-29 other failures each run are the pre-existing env-only set (`SIDEQUEST_DATABASE_URL` unset), unrelated to this story.

**Lint/types:** `ruff check` clean on all changed files. `pyright tests/server/conftest.py` shows 5 errors but all pre-existing (lines 235/236/241/923 — monkeypatch setitem + GenreLoader.load + psycopg execute overload), none on the changed lines.

**Env note (for Reviewer/CI):** the full pg-gated suite requires BOTH `SIDEQUEST_TEST_DATABASE_URL` and `SIDEQUEST_DATABASE_URL` set. With the latter unset, ~22 unrelated tests fail loudly (test_app/db_pool, forensics routes, culture_context, chargen_complete_no_hp_leak, lore_rag_wiring) — environmental, not from this change (verified: all pass with both vars set).

**AC status:** AC2 (root cause in docstring) DONE. AC1 (pair passes 5 consecutive full-suite parallel runs) — **DONE: verified 5/5 chargen pair GREEN in consecutive clean-env (`-n auto`) full-suite runs** (SM finish, 2026-06-10). The 7 residual per-run failures are the separate out-of-scope clean-env flake class (encounter_actors / dogfight_player_throw / namegen-audit subprocess / api_contract_aside), not the chargen pair.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 real smells (3 pytest.skip are pre-existing content-guards) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | confirmed 0, dismissed 0, deferred 0 |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled specialists returned; 7 disabled via `workflow.reviewer_subagents` settings)
**Total findings:** 0 confirmed, 1 dismissed (Reviewer's own, non-blocking — see below), 0 deferred

## Reviewer Assessment

**Verdict: APPROVE.**

Scope is a 3-file, test-harness-only change (97 +/7 -); no production code touched. I read the full diff and the surrounding fixtures myself, ran the enabled specialist panel, and verified the fix matches the confirmed root cause.

- **[PRE] reviewer-preflight — clean.** 89 passed / 0 failed / 64 skipped across the changed files + all 16 `seed_slug_for_test` consumer files (with both DB env vars set). `ruff check` clean on all 3 files. 0 real smells; the 3 `pytest.skip()` are pre-existing content-guards on `develop`, not introduced here. The `PythonFinalizationError` at shutdown is the known psycopg-pool teardown noise, not a failure. VERIFIED — consistent with my own runs and Dev's evidence.
- **[SEC] reviewer-security — clean.** `uuid4().hex[:8]` is metacharacter-free (0-9a-f); the slug flows only into the parameterized `ensure_session` INSERT (`%s` tuple) and parameterized `get_game` lookup — no injection surface, no shell/template/header path, nothing sensitive logged. The `None`→uuid default is an explicit deterministic replacement, not a silent fallback. VERIFIED.
- **[EDGE] reviewer-edge-hunter — disabled via settings (not run).** My own edge pass: the sentinel `slug: str | None = None` is always resolved to a `str` before use (return type holds); `uuid4().hex[:8]` = 32 bits, birthday-collision over ~18 seeds/worker is negligible and matches `tests/dungeon/conftest.py`'s precedent; explicit-`slug=` callers (0 in tree) are unaffected. No edge gap.
- **[SILENT] reviewer-silent-failure-hunter — disabled via settings (not run).** My own pass: no swallowed errors, no empty excepts, no silent alternative path introduced. The change removes a silent failure mode (the stale-genre no-op), it doesn't add one.

**Dismissed (non-blocking, Reviewer's own):** the new `TestSeedSlugIsolation` seeds rows into the session-scoped committed `migrated_db` that are never explicitly cleaned. Dismissed because (a) slugs are now unique so no collision, and (b) this is identical to all 16 existing `seed_slug_for_test` callers — consistent existing practice, not a new defect.

**Rule Compliance:** No silent fallbacks ✓ (removes one). No stubbing ✓. No source-text wiring tests ✓ (new test asserts runtime behavior — returned slug + DB row). Meaningful assertions ✓ (concrete values + diagnostics). Wiring test present ✓ (the existing `TestNameRigExtractionWiring` integration pair). "Fix the isolation, not the assertion" ✓ (OTEL span assertions untouched; the slug-isolation defect is fixed).

**AC verification:** AC2 (root cause in docstring) — DONE, thorough class docstring. AC1 (pair passes 5 consecutive full-suite parallel runs) — Dev showed 8/8 green under the *harder* reproducing condition (dirty env, was ~1/7 fail before). I consider AC1 substantively met; recommend SM/TEA run the literal clean-env 5× during finish for the record.

**Decision:** Approve for merge. **PR:** https://github.com/slabgorb/sidequest-server/pull/798 (base `develop`).

## Story Details
- **ID:** 97-6
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T15:02:30Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T12:40:38Z | 2026-06-10T12:42:43Z | 2m 5s |
| red | 2026-06-10T12:42:43Z | 2026-06-10T14:35:01Z | 1h 52m |
| green | 2026-06-10T14:35:01Z | 2026-06-10T14:55:01Z | 20m |
| review | 2026-06-10T14:55:01Z | 2026-06-10T15:02:30Z | 7m 29s |
| finish | 2026-06-10T15:02:30Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Architect (root-cause investigation, 2026-06-10)

- **[CONFIRMED ROOT CAUSE — Conflict, blocking] The flake is a shared fixed-slug DB collision, NOT OTEL. The story's tracer-provider hypothesis is falsified by the captured traceback.**
  - **Captured traceback (dirty-env repro, attempt 1):** BOTH pair tests fail at the *first* line, `await _connect(...)`, with `ErrorMessage: "Failed to load genre... genre pack 'test_genre' not found; searched: .../sidequest-content/genre_packs"` and log `session.genre_load_failed genre=test_genre slug=test-slug`. The test asked for `genre="road_warrior"` but connect resolved `slug=test-slug / genre=test_genre`. The walk never runs, so `chargen.names_extracted` never fires — "span absent" (the PR-741 note + SM hypothesis) is a *downstream symptom*, not the cause. OTEL is exonerated.
  - **Mechanism:** `tests/server/conftest.py::seed_slug_for_test` defaults to a FIXED slug `"test-slug"` (line 56). **18 call sites across 19 server-test files use that default (0 explicit `slug=` overrides)**, each seeding a *different* genre into the **session-scoped, commit-based** `migrated_db` (no per-test rollback). The `sessions` upsert (`sidequest/game/pg/sessions.py:57`) is `ON CONFLICT (session_slug) DO UPDATE SET last_played = excluded.last_played` — it updates *only* `last_played`, **never `genre_slug`/`world_slug`**. So the FIRST seeder of `test-slug` in a worker wins the genre; every later re-seed of the same slug is a silent no-op for genre. When a sibling (e.g. `test_chargen_dispatch`, which uses the `test_genre` fixture pack) seeds `test-slug→test_genre` before the chargen name-rig test seeds `test-slug→road_warrior`, the chargen test's connect reads the stale `test_genre`. The chargen test alone reads against the REAL content tree (`genre_pack_search_paths=[CONTENT_ROOT]`), where `test_genre` does not exist → genre-load failure → ErrorMessage at `_connect`. Order-dependent on which test wins the `test-slug` row in a worker → xdist flake.
  - **Why the env correlated:** reproduced only with `SIDEQUEST_DATABASE_URL` unset (heavier worker/db_pool churn widened the collision window / shifted scheduling). Under both DB vars set it passed 8/8 — but that is luck of scheduling, not a fix; the latent collision remains.
  - **Recommended fix (test-harness isolation; server-only; NO production change; honors "fix the isolation, not the assertion"):** make `seed_slug_for_test` default to a unique uuid-namespaced slug (e.g. `f"test-{uuid4().hex[:8]}"`), exactly mirroring `tests/dungeon/conftest.py`'s already-established rationale ("slug is uuid-namespaced — REQUIRED because migrated_db is session-scoped and the pool COMMITS, so fixed slugs bleed across xdist workers"). Each call gets its own `sessions` row → no cross-test collision. The returned slug is already threaded into the connect envelope, so read-side callers (all use the return value; 0 hardcode the literal) are unaffected — Dev must still grep-verify no test asserts on the literal `"test-slug"`.
  - **RED test (deterministic):** in one test, call `seed_slug_for_test` twice (default slug) with two different genres against the same pool, then drive `_connect` for the second and assert it resolves the SECOND genre (today it reads the stale first genre → ErrorMessage → RED). Optionally also assert two default-slug calls return DISTINCT slugs. Deterministic; no xdist or env dependence needed.
  - **Out of scope but real (separate stories):** (a) ~7 clean-env full-suite flakes unrelated to 97-6 (`test_encounter_actors_all_combatants` source-grep, `test_dogfight_player_throw_roundtrip`, the `test_audit_namegen_corpora` subprocess tests, `test_api_contract_aside`); (b) a genuine but DIFFERENT latent OTEL isolation defect — unrestored `set_tracer_provider` swaps in `tests/telemetry/test_spans.py` (×2) and projection tests orphan import-cached `ProxyTracer`s (proven droppable via synthetic repro); they should adopt the dungeon capture/reset/restore pattern. Neither is the cause of THIS flake.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **RED test targets a DB slug-collision mechanism, not the OTEL span-exporter mechanism the story hypothesized**
  - Spec source: `.session/97-6-session.md`, SM Assessment, "Root-cause hypothesis" (line 13)
  - Spec text: "shared tracer-provider / span-exporter global state across tests within an xdist worker, or an extraction-path module global raced by a sibling test. The span isn't lost in production — it's the test harness's capture that's leaking across tests."
  - Implementation: The RED test (`TestSeedSlugIsolation`) reproduces a shared FIXED-slug collision in the session-scoped committed `migrated_db`, not an OTEL exporter race. The captured full-suite traceback shows both pair tests fail at `_connect` (`genre pack 'test_genre' not found`), before any span fires — OTEL is exonerated; "span absent" is a downstream symptom.
  - Rationale: The SM Assessment explicitly flagged the hypothesis as "for TEA to confirm, not assume." Confirmed via deterministic reproduction + traceback. The story's actual scope ("test-harness/fixture isolation, server only, no production change, fix the isolation not the assertion") is honored exactly — only the named mechanism changed.
  - Forward impact: Dev's GREEN fix is a one-line uuid-namespaced default in `seed_slug_for_test` (not an OTEL fixture change). Two genuinely-separate defects were spun out as out-of-scope notes (Architect finding): ~7 unrelated clean-env flakes, and a real-but-different OTEL ProxyTracer-orphan defect in `tests/telemetry/test_spans.py`. Neither blocks 97-6.
  - Severity: non-blocking (re-diagnosis within the same scope; no AC change)