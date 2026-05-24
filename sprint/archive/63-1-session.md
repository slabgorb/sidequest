---
story_id: "63-1"
jira_key: ""
epic: "63"
workflow: "tdd"
---
# Story 63-1: Anchor core — slug helper, namespaced ids, URL builders, JSON island, OTEL

## Story Details
- **ID:** 63-1
- **Jira Key:** (none — SideQuest has no Jira)
- **Epic:** 63 (Reference pages v3 — chrome + wiki-like anchor links)
- **Workflow:** tdd
- **Points:** 5
- **Priority:** p2
- **Repository:** sidequest-server
- **Base branch:** develop
- **Feature branch:** feat/63-1-reference-anchor-core
- **Stack Parent:** none (foundation story for 63-2 through 63-5)

## Story Scope

Tasks 1–5 of `docs/superpowers/plans/2026-05-23-reference-pages-v3.md`:

1. **Task 1:** Extract `slugify()` helper into `sidequest-server/sidequest/server/reference_slug.py` (refactor, no behaviour change)
2. **Task 2:** Namespace renderer anchor ids by file kind (`class-knight` vs `culture-knight`)
3. **Task 3:** Build URL builder module `sidequest-server/sidequest/server/reference_anchors.py` with six helper functions:
   - `build_rules_url(pack: str, kind: str, slug: str) -> str`
   - `build_lore_url(pack: str, world: str, slug: str) -> str`
   - `reference_url_for_ability(pack: str, ability_name: str) -> str | None`
   - `reference_url_for_class(pack: str, class_name: str) -> str | None`
   - `reference_url_for_journal_entry(pack: str, category: str, entry_title: str) -> str | None`
   - `reference_url_for_location_entity(pack: str, world: str, entity_name: str) -> str | None`
4. **Task 4:** Add JSON island + bad-anchor banner to rendered pages
5. **Task 5:** Add OTEL span helpers for reference URL attached/skipped/failed

All changes are server-only. This story is a foundation for stories 63-2 through 63-5.

## Workflow Tracking

**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-05-24T08:20:26Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24 | 2026-05-24T08:20:26Z | 8h 20m |
| red | 2026-05-24T08:20:26Z | - | - |

## Spec Sources (Priority Order)

1. Story scope (above)
2. `docs/superpowers/plans/2026-05-23-reference-pages-v3.md` (Tasks 1–5, lines 120–1114)
3. `docs/superpowers/specs/2026-05-23-reference-pages-v2-design.md` (anchor-link design contract)
4. `CLAUDE.md` (OTEL principle, no-silent-fallbacks, no-stubs, one-mechanism-per-problem)

## Project Conventions

- **No Jira:** SideQuest does not use Jira. The `jira_key` field remains empty.
- **TDD Phase Order:** setup → red → green → spec-check → verify → review → spec-reconcile → finish
- **No content-coupled tests:** Fixtures only for unit tests; never assert on live `genre_packs/*` in pytest.
- **No silent fallbacks:** Missing helpers fail LOUD with ERROR spans, never silently degrade.
- **No stubs:** Don't create placeholder modules or skeleton code.
- **One mechanism per problem:** Single emitter of anchor ids, not parallel systems.
- **OTEL observability:** Every backend subsystem decision must emit OTEL watcher events so the GM panel can verify the fix works.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (red)

- **Conflict** (blocking): Story 63-1 scope (Plan Tasks 1–5) is already implemented on `sidequest-server/develop` via PR #395 (`feat/reference-v2`, merged 2026-05-23 20:26). Tasks 1–4 ship with 44 passing tests; Task 5 production helpers ship in `sidequest/telemetry/spans/reference.py` but `tests/server/test_reference_otel.py` is missing. The current branch `feat/63-1-reference-anchor-core` has zero diff vs develop. RED phase has no work to do — there are no failing tests to write because the code already passes. *Found by TEA before writing any tests.*
- **Conflict** (blocking): Same situation for story 63-2 (Tasks 6–14, 16). T6–T9 protocol fields, T10–T14 UI panel hyperlinks (except `LocationPanel.reference.test.tsx`), and T16 content CLAUDE.md note all already shipped in the same v2 PR. *Found by TEA while sanity-checking the epic.*
- **Conflict** (non-blocking): Story 63-3 (Tasks 15, 19) is half-done: T15 fixture-pack integration test ✅ merged; T19 `display_font_family` in `theme.yaml` ❌ not present in any pack. *Found by TEA while sanity-checking the epic.*
- **Gap** (non-blocking): Plan Task 5 (OTEL coverage for reference URL spans) — production helpers exist, test file does not. This is the only legitimate test gap inside the original 63-1 scope, but writing it now would not be a RED test (it'd pass GREEN immediately against existing code).
- **Gap** (non-blocking): Plan Task 14 (LocationPanel reference test) — production code present, test file missing.
- **Improvement** (non-blocking): Future plan-amendment passes (Architect and SM) must check repo state before assuming "not yet started." `git log --oneline -- <target-paths>` is the cheap probe. The v3 amendment header (line 11 of the plan) should be retroactively annotated to note PR #395 absorbed Tasks 1–16, so downstream stories can be re-scoped against the real delta.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations.

## Sm Assessment

**Setup Complete:** Yes
**Story:** 63-1 (Anchor core — slug helper, namespaced ids, URL builders, JSON island, OTEL)
**Branch:** feat/63-1-reference-anchor-core (sidequest-server, off develop)
**Workflow:** tdd (phased: setup → red → green → review → finish)
**Repos:** sidequest-server (single-repo story)

**Plan reference:** Tasks 1–5 of `docs/superpowers/plans/2026-05-23-reference-pages-v3.md`. The plan is the authoritative design doc for this story; TEA writes failing tests directly against the test specs already embedded in the plan (each Task has a "Step 1: Write the failing test" block with the full pytest code).

**Foundation story:** 63-1 is the dependency root for 63-2, 63-3, 63-4, 63-5. Get the slug helper, namespaced ids, URL builders, JSON island, and OTEL spans landed cleanly here — downstream stories assume they exist.

**No-Jira flag:** SideQuest convention; `jira_key` intentionally empty. Story finish will skip the Jira transition step.

**Handoff:** To Radar O'Reilly (TEA) for RED phase. Tests live in `sidequest-server/tests/server/test_reference_slug.py`, `test_reference_renderer_namespacing.py`, `test_reference_anchors.py`, `test_reference_renderer_bad_anchor.py`, and an OTEL test (path depends on which existing telemetry capture pattern is in use — Radar must grep first per plan Task 5 Step 1).

## Tea Assessment

**RED Complete:** No — story scope already implemented on develop, RED phase cannot proceed.

**Discovery:** Repo verification before writing any tests revealed that `sidequest-server` PR #395 (`feat/reference-v2`, merged 2026-05-23 20:26 — two hours after the plan was committed at 18:00) already ships Plan Tasks 1–9 + 15 + 16. 44 tests for Tasks 1–4 pass on `develop` today. Production helpers for Task 5 (OTEL reference spans) exist at `sidequest/telemetry/spans/reference.py`; only the test file `test_reference_otel.py` is missing.

**Current branch:** `feat/63-1-reference-anchor-core` has zero diff vs `sidequest-server/develop`.

**Tests written:** None. Writing RED tests against already-implemented code would be performative — every test would pass GREEN on first run.

**Handoff:** Back to Hawkeye Pierce (SM) for story re-scoping. Recommendation in Delivery Findings: shrink 63-1 to "Task 5 OTEL test only" OR close 63-1 as no-op (work was completed before story creation). Same triage needed for 63-2 (nearly done) and 63-3 (half done). Stories 63-4 (chrome rendering) and 63-5 (cleanup) are still real work and should survive the re-scope.

**Why not just close-phase as no-op:** Per project discipline (no silent fallbacks, fail loud), the right move is to surface a blocking finding and hand control back to coordination rather than advance the phase as if work happened. Keith should decide the re-scope.