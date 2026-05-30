---
story_id: "71-33"
jira_key: null
epic: "71"
workflow: "trivial"
---
# Story 71-33: Migrate pulp_noir scenarios to world tier

**Story:** Migrate pulp_noir scenarios to world tier (`worlds/annees_folles/scenarios/`) — restore scenario binding after 71-32 made bind world-aware
**Jira:** None (SideQuest is personal — no Jira)
**Workflow:** trivial
**Phase:** finish
**Repos:** content
**Branch:** 71-33-migrate-pulp-noir-scenarios-world-tier
**Slug:** migrate-pulp-noir-scenarios-world-tier
**Points:** 3
**Priority:** p2
**Type:** bug (regression)
**Status:** in_progress

## Summary
71-32 made `bind_scenario` world-aware (binds only `pack.worlds[world_slug].scenarios`,
no pack-level fallback). pulp_noir's `annees_folles` world has no `scenarios/` dir, so
pulp_noir now binds nothing. Fix = `git mv` the two pack-tier scenario dirs
(`midnight_express`, `the_warehouse`) into `worlds/annees_folles/scenarios/`. Mechanism
already shipped in 71-32; this is content-only, mirroring 71-32's tea_and_murder move.

Full scope, ACs, verification plan, and scope deviation in
`sprint/context/71-33-context.md`.

## Repos
- **content** (sidequest-content) — branch `71-33-migrate-pulp-noir-scenarios-world-tier`, base `develop`.
  NOTE: epic YAML reads `repos: server,content` but this story is **content-only** (see
  Scope Deviation in context doc). At finish, PR content only.

## Phase Log
- **setup (SM, Hawkeye, 2026-05-30):** Vetted the premise — repro CONFIRMED real
  (annees_folles has no scenarios dir; 71-32 archive shows Architect explicitly
  recommended this follow-up). Re-scoped tdd→trivial + server,content→content per
  Operator no-real-content-tests directive (binding mechanism already shipped). Content
  branch created off develop. Context doc written. Routing to Dev for the git mv +
  live-load verification.

## Scope Deviation
- YAML: `repos: server,content`, `workflow: tdd` → actual: `content`, `trivial`.
  Rationale + finish handling documented in `sprint/context/71-33-context.md` (Scope Deviation).
  `pf sprint story update` has no `--repos` flag; session Repos line is authoritative.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-content):**
- `genre_packs/pulp_noir/scenarios/midnight_express/` → `genre_packs/pulp_noir/worlds/annees_folles/scenarios/midnight_express/` (5 files, `git mv` — rename, 0 content lines changed)
- `genre_packs/pulp_noir/scenarios/the_warehouse/` → `genre_packs/pulp_noir/worlds/annees_folles/scenarios/the_warehouse/` (5 files, `git mv`)
- Removed now-empty `genre_packs/pulp_noir/scenarios/` dir

**No code changes.** Pure content relocation — neither `scenario.yaml` carries a
`world:`/`world_specific:` key; the loader (`_load_single_world`, `loader.py:1018-1044`)
discovers world scenarios by directory location. Server repo untouched (mechanism shipped in 71-32).

**Acceptance Criteria:**
- AC1 ✅ both scenario dirs relocated via `git mv` (history preserved — `git show --stat` shows renames, 0 line deltas)
- AC2 ✅ pack-tier `scenarios/` removed; live load shows `pack.scenarios == []` (no orphans)
- AC3 ✅ **live-verified**: `pack.worlds["annees_folles"].scenarios == ['midnight_express', 'the_warehouse']`; `bind_scenario` (`scenario_bind.py:78-105`) now reaches the initialize path (`scenario.initialized`) instead of `scenario.bind_skipped`/`reason=no_world_scenario`
- AC4 ✅ both YAMLs parse and load cleanly (full pack load succeeded)

**Verification method:** Real-pack load via `SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run python` (one-off, not a committed test) — per the Operator no-real-content-tests directive. The 71-32 hermetic synthetic-pack fixtures already guard the mechanism.

**Tests:** No new tests (content-only move; mechanism tested in 71-32). Did not run the
server suite — no server code changed.

**Branch:** `71-33-migrate-pulp-noir-scenarios-world-tier` (content, pushed to origin, commit `bb17053`)

**Handoff:** To Reviewer.

## Design Deviations

### Dev (implementation)
- **No deviations from spec.** The context doc anticipated a possible `world_specific:`
  flag edit ("measure, don't assume"); I measured — neither scenario.yaml carries such a
  key and the loader keys on directory location, so a pure `git mv` was the correct and
  complete implementation, exactly as the context doc's default expectation stated.
  (The pre-existing tdd→trivial / server,content→content re-scope is an SM setup decision,
  already logged under `## Scope Deviation` above — not a Dev implementation deviation.)

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation. The migration mirrored 71-32's
  tea_and_murder/the_morning_train move exactly; the world-aware loader and bind path
  behaved as documented.

## Reviewer Assessment

**Verdict:** APPROVED

**Verification (independent, not trusted):**
- **Diff is pure renames** — `git diff develop...HEAD -M` = 10 files, 0 insertions / 0 deletions; git rename-detection confirms every file moved with byte-identical content. No smuggled edits.
- **Live re-load** (my own run, not Dev's): `pack.scenarios == []` (no pack-tier orphans); `pack.worlds["annees_folles"].scenarios == ['midnight_express', 'the_warehouse']`. Both scenario packs carry real content (`midnight_express`: 10 NPCs; `the_warehouse`: 6 NPCs) — not empty shells. This is the regression fixed: `bind_scenario` (`scenario_bind.py:78-105`) now reaches `next(iter(world_scenarios))` → `scenario.initialized`, not the `bind_skipped`/`no_world_scenario` path.
- **No stale references** — grep for `pulp_noir/scenarios` (old path) across content + server: 0 hits. Grep for hardcoded `midnight_express`/`the_warehouse` in server source: 0 hits. Nothing depended on the old location.
- **Old pack-tier `scenarios/` dir removed**; working tree clean (0 uncommitted).
- **Single-world correctness:** annees_folles is pulp_noir's only live world, so no sibling world is left scenario-less by this move.

**Scope / process:** SM's tdd→trivial + server,content→content re-scope is sound and well-documented (mechanism shipped in 71-32; Operator no-real-content-tests directive makes a server RED test inappropriate). Verification-by-live-load is the correct method here, matching the 71-32 precedent. Fixed one factual error in the Dev assessment (commit hash `4d8da7d` → actual `bb17053`).

**Findings:** None. No correctness, security, or wiring defects. A directory rename that restores a binding the parent story intentionally deferred — exactly the right shape.

**OTEL:** N/A for a content move — the observability (`scenario.initialized` / `scenario.bind_skipped`) already shipped in 71-32 and is what this change re-activates.

**Handoff:** To SM (Hawkeye) for finish — squash-merge the content PR to develop, archive, mark done.