---
story_id: "64-8"
jira_key: "N/A"
epic: "64"
workflow: "trivial"
---
# Story 64-8: Repoint daemon preview-style test off the dead mawdeep world

## Story Details
- **ID:** 64-8
- **Jira Key:** N/A
- **Epic:** 64 (Content Schema Compliance — Close Pack Validator Gaps)
- **Workflow:** trivial
- **Stack Parent:** none
- **Branch:** feat/64-8-repoint-preview-style-test (sidequest-daemon)

## Story Context

The daemon test `sidequest-daemon/tests/test_preview_style.py::test_style_wires_into_real_caverns_and_claudes_pack` hardcodes `--world mawdeep` (lines 127 and 134) and carries a stale comment "mawdeep is a real C&C world" (line 127). mawdeep NO LONGER EXISTS — `sidequest-content/genre_packs/caverns_and_claudes/worlds/` contains only `beneath_sunden` on disk.

Per the no-content-coupled-tests rule, DO NOT author a `genre_packs/caverns_and_claudes/worlds/mawdeep/visual_style.yaml` to resurrect the dead world. The fix is to repoint the test onto the live world `beneath_sunden`.

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-27T01:48:12Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-26 | 2026-05-27T00:43:39Z | 24h 43m |
| implement | 2026-05-27T00:43:39Z | 2026-05-27T01:44:13Z | 1h |
| review | 2026-05-27T01:44:13Z | 2026-05-27T01:48:12Z | 3m 59s |
| finish | 2026-05-27T01:48:12Z | - | - |

## Sm Assessment

**Setup Complete:** Yes
**Story:** 64-8 — Repoint daemon preview-style test off the dead mawdeep world
**Repos:** sidequest-daemon (gitflow, base `develop`)
**Branch:** feat/64-8-repoint-preview-style-test (created off develop in sidequest-daemon)
**Workflow:** trivial (phased) → next phase `implement`, owned by Dev

**Re-scope origin:** Story was originally "author missing mawdeep/visual_style.yaml." Keith confirmed mawdeep no longer exists (caverns_and_claudes has only beneath_sunden on disk), so authoring that file would resurrect a dead world. Re-scoped in place to repoint the failing daemon test off mawdeep.

**Technical approach:** `sidequest-daemon/tests/test_preview_style.py::test_style_wires_into_real_caverns_and_claudes_pack` hardcoded `--world mawdeep` (lines 127, 134) with a stale "mawdeep is a real C&C world" comment. Repoint to live world `beneath_sunden`; correct the comment. Do NOT create any `genre_packs/caverns_and_claudes/worlds/mawdeep/` files.

**Implementation already landed during setup:** commit `92781a8` ("fix: repoint daemon preview-style test off dead mawdeep world") on the feat branch. Dev should verify the test passes and confirm no mawdeep files were created, then proceed to review.

**Out of scope:** broader server-test mawdeep coupling (~30 `test_61_*` / npc-in-scene tests) tracked separately at epic-61:218.

**Jira:** N/A — this project never uses Jira (per project rule).

**Handoff:** To Dev (Winchester) for the implement phase.

## Acceptance Criteria
1. test_preview_style.py no longer references the dead world "mawdeep"; it targets the live world beneath_sunden
2. test_style_wires_into_real_caverns_and_claudes_pack passes without creating any genre_packs/caverns_and_claudes/worlds/mawdeep/ files
3. The stale "mawdeep is a real C&C world" comment at test_preview_style.py:127 is corrected

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-daemon/tests/test_preview_style.py` — **deleted** `test_style_wires_into_real_caverns_and_claudes_pack` and its now-unused `REPO_ROOT`/`REAL_PACKS` constants. This test loaded the live `sidequest-content` tree (`SIDEQUEST_GENRE_PACKS=<real packs>`) and asserted content-owned values (`Erol Otus`/`David Trampier`/`pen and ink`) — a unit test against production content.

**Tests:** 4/4 passing (GREEN) in `tests/test_preview_style.py`, all fixture-based.
**Branch:** feat/64-8-repoint-preview-style-test (commit `3b99253`, force-pushed to origin)

**Why the scope shifted from "repoint" to "delete" (Keith's call, mid-phase):**
The initial fix repointed `--world mawdeep` → `--world beneath_sunden`. Keith caught that both are *live worlds in the real pack*, so the repoint just relocated the content coupling rather than removing it — the same anti-pattern flagged at epic-61:218 and in the `no-content-coupled-tests` rule. The CLAUDE.md "every test suite needs a wiring test" mandate is satisfied by the four fixture-based tests, which call the real `main(["style", ...])` entry point against `tests/fixtures/.../genre_packs` — proving the code path is imported/called/reachable without coupling to generated content. So the correct fix was to delete the live-content test outright; it added zero wiring coverage the fixture tests don't already provide.

**Verification notes:**
- No `genre_packs/caverns_and_claudes/worlds/mawdeep/` files created (no dead-world resurrection).
- No remaining `mawdeep` references in `sidequest-daemon/tests/`.
- The commit also carries a concurrent `uv.lock` version bump (1.2.0→1.3.0) from other-repo work; per Doctor's direction, left as-is (out of scope).

**AC reconciliation:** AC-1 ("no longer references the dead world mawdeep") — met by deletion. AC-2 ("passes without creating mawdeep files") — met. AC-3 ("stale comment corrected") — met by deletion (the comment was part of the removed test).

**Handoff:** To review phase.
## Impact Summary

**Scope:** Pure test deletion (34 lines) + incidental `uv.lock` self-version bump.

**Changes:**
- Removes content-coupled test `test_style_wires_into_real_caverns_and_claudes_pack` that pinned to the deleted `mawdeep` world
- Retains four fixture-based wiring tests, all passing (4/4 GREEN)
- No production code paths modified (narrator, engine, media, protocol unaffected)

**Risk Surface:**
- **Content correctness coverage:** Live-pack style-token assertions (Erol Otus, pen-ink detection) no longer covered by pytest. Routed to pack validator per project rule. Non-blocking if validator story is paired in epic-64.
- **Server-side `mawdeep` coupling:** Broader test suite (~30 `test_61_*` tests) remains uncovered; tracked separately at epic-61:218. Out of scope.

**Blocking Issues:** None
**Warnings:** None
**Pattern:** Deletion resolves a project-rule violation (`no-content-coupled-tests`) rather than introducing new behavior.

## Delivery Findings

### Dev (implementation)
- **Improvement** (non-blocking): Content correctness for live packs (does `caverns_and_claudes` emit its signature style tokens) is no longer asserted anywhere now that the content-coupled test is gone. If that coverage is wanted, it belongs in the **pack validator** (epic-64's domain), reported loudly at load time — not in daemon pytest. *Found by Dev during implementation.*
- **Gap** (non-blocking): Broader server-side `mawdeep` test coupling (~30 `test_61_*` / npc-in-scene tests) remains, tracked at epic-61:218. Out of scope for 64-8. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): epic-64 is "Close Pack Validator Gaps" — the live-pack style-token coverage just deleted here (does `caverns_and_claudes` emit `Erol Otus`/`pen and ink` style tokens) is a natural pack-validator check. Recommend a sibling epic-64 story to add a `style`-layer assertion to the pack validator so the coverage isn't merely dropped. Affects the pack validator CLI/load-time path. *Found by Reviewer during code review.*

## Design Deviations

### Dev (implementation)
- **Deleted the content-coupled test instead of repointing it to a live world**
  - Spec source: 64-8 session AC-1 / epic-64.yaml
  - Spec text: "test_preview_style.py ... targets a live world (beneath_sunden) or a test-only fixture pack"
  - Implementation: Deleted `test_style_wires_into_real_caverns_and_claudes_pack` entirely rather than repointing it to `beneath_sunden`.
  - Rationale: Repointing to any live world perpetuates the content coupling the story aimed to resolve (Keith's mid-phase direction); the four fixture-based tests already satisfy the wiring mandate, so the live-content test was redundant coupling.
  - Severity: minor
  - Forward impact: none on siblings — net effect (no mawdeep reference, no content coupling) exceeds the AC's intent. Live-pack content correctness moves to the validator (see Delivery Findings).

### Reviewer (audit)
- **Deleted the content-coupled test instead of repointing it to a live world** → ✓ ACCEPTED by Reviewer: the AC's intent was "stop referencing the dead world / stop coupling to content," and deletion satisfies it more completely than a repoint would. The `no-content-coupled-tests` project rule explicitly directs content-shape assertions to the validator, not pytest — so deleting (rather than relocating) the live-pack test is the rule-compliant action, not a shortcut. AC text offered "a test-only fixture pack" as an alternative; deletion is sound because the four surviving fixture tests already exercise the same `main()` entry point, so a new fixture-pack test would be redundant. Deviation reasoning agrees with author.
- No undocumented deviations found.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — tests GREEN (4/4), ruff clean, 0 code smells, no dangling REAL_PACKS/REPO_ROOT/mawdeep refs |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A — uv.lock change is self-version bump only (no dep/hash change); deleted test carried no security coverage; no secrets |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (2 enabled subagents returned, both clean; 7 disabled via `workflow.reviewer_subagents` and pre-filled as Skipped)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

This is a pure test deletion (34 lines removed, 1 added) plus an incidental `uv.lock` self-version bump. No production code path changed; no narrator, engine, media, or protocol code is touched. The change *removes* a project-rule violation rather than adding behavior.

### Rule Compliance
- **`no-content-coupled-tests` (FIXTURES for unit tests, VALIDATORS for worlds):** The deleted `test_style_wires_into_real_caverns_and_claudes_pack` set `SIDEQUEST_GENRE_PACKS` to the live `sidequest-content` tree and asserted content-owned tokens (`Erol Otus`/`David Trampier`/`pen and ink`) — a textbook violation. Deletion brings the file into compliance. The four surviving tests are all fixture-based (`FIXTURE_ROOT`) or use `tmp_path`. COMPLIANT after change.
- **CLAUDE.md (daemon) "Every Test Suite Needs a Wiring Test" — imported, called, reachable from production code paths:** The remaining four tests all invoke the real `main(["style", ...])` entry point (`sidequest_daemon.media.preview.main`) — they ARE wiring tests; they exercise the production CLI path, just with fixture data instead of live content. The mandate requires the production path be reachable, not that the data be live. COMPLIANT — verified `_run` → `main(argv)` at test lines, e.g. `test_style_text_output_against_fixture`.
- **No silent fallbacks / fail loud:** The deleted test's `@pytest.mark.skipif(not REAL_PACKS.exists())` was itself a soft-skip (silently green when content absent). Removing it tightens CI behavior. COMPLIANT.
- **Genre-pack `extra="forbid"` model-pairing rule:** N/A — no YAML schema or model field changed.

### Observations
- [VERIFIED] Tests pass after deletion — evidence: reviewer-preflight ran `uv run pytest tests/test_preview_style.py -v`, 4/4 GREEN in 0.01s. Complies with the wiring-test rule (all four hit `main()`).
- [VERIFIED] No dangling symbols — evidence: grep across `tests/` shows zero `REAL_PACKS`/`mawdeep` hits in `test_preview_style.py`; the surviving `pytest` import is used by `pytest.raises` in `test_style_world_with_no_style_file_raises_loud`, and `Path` by `FIXTURE_ROOT:19`. `REPO_ROOT` in other test files is an independent, self-contained constant — not affected.
- [VERIFIED] `uv.lock` delta is benign — evidence: reviewer-security confirmed the only changed line is `sidequest-daemon` `version 1.2.0 → 1.3.0`; no transitive package entry, source URL, or sha256 hash altered. Per Doctor's direction this is concurrent other-repo work, left as-is.
- [LOW] The `uv.lock` version bump rides in the same commit as an unrelated story; it will carry to `develop` on merge. Acceptable (it's a legitimate self-version bump and Keith explicitly directed leaving it), but noted so it isn't mistaken later for part of the test change.
- [VERIFIED] AC satisfaction — AC-1 (no dead-world reference) met by deletion; AC-2 (no `mawdeep/` files created) met — `worlds/` still contains only `beneath_sunden`; AC-3 (stale comment corrected) met — the comment was inside the removed block.
- [SEC] reviewer-security returned clean — confirmed no secrets added/removed, `uv.lock` change is a self-version bump only (no dependency source/hash moved), and the deleted test carried zero security coverage (it asserted style tokens, not auth/path-traversal/credentials). No security gap created.
- [SIMPLE] Net complexity reduced: 34 lines and two module constants removed, nothing added. No over-engineering introduced.
- Subagent tags for the disabled specialists (coverage assessed by Reviewer directly given the deletion-only diff): [EDGE] no new branches/paths introduced — a deletion adds no boundary conditions. [SILENT] the only error-suppression construct (the skipif soft-skip) was removed, not added. [TEST] test-quality improved — a content-coupled assertion was removed; remaining tests are fixture-based with real assertions (`assert code == 0`, token presence against fixtures). [DOC] the deleted comment block went with its test; no stale doc remains (verified no `mawdeep` comment survives). [TYPE] no types/signatures changed. [RULE] the change resolves a `no-content-coupled-tests` violation; no new rule violation introduced.

### Devil's Advocate
Let me argue this change is broken. First claim: "you deleted the only test that proves the `style` subcommand works against the real `caverns_and_claudes` pack — now a genuine breakage in live content (a malformed `visual_style.yaml`, a renamed slug) ships undetected." This is the strongest objection, and it's real but misdirected: catching malformed *live content* is precisely what a pack validator is for, not a daemon unit test — coupling that detection to pytest is the very anti-pattern the project rule forbids, and it had already rotted (the test was pinned to the now-deleted `mawdeep` world and would have failed for the wrong reason). The coverage gap is acknowledged and routed to the validator via a Delivery Finding, which is the correct home. Second claim: "the fixture tests don't actually prove wiring because fixtures aren't production." But the wiring mandate is about the *code path* (is `main()` imported, called, reachable?), not the data — and the fixtures flow through `main(["style",...])` exactly as production does; the data being synthetic doesn't break the import/call/reach chain. Third claim: "the `uv.lock` bump could smuggle a dependency change." Checked — it's a one-line self-version string, no hashes or sources moved. Fourth: "a confused future dev sees a test suite with no live-pack test and re-adds one." Mitigated by the explicit Dev Assessment + this audit recording *why* it was removed, plus the new dev-gotchas sidecar entry. Nothing here rises to Medium, let alone blocking.

**Data flow traced:** `main(["style", "--genre", "testgenre", "--world", "testworld"])` → StyleCatalog load from `FIXTURE_ROOT` → rendered style tokens in stdout → asserted by the fixture tests. Safe: no live-content dependency, no external I/O beyond the fixture tree, deterministic.
**Pattern observed:** fixture-pack-through-real-entry-point wiring test — `tests/test_preview_style.py` (the correct SideQuest pattern) vs. the deleted live-content-coupled test (the anti-pattern).
**Error handling:** `test_style_world_with_no_style_file_raises_loud` confirms the subcommand raises `StyleMissError` (fail-loud) rather than soft-degrading — consistent with the no-silent-fallbacks rule.
**Handoff:** To SM (Hawkeye) for finish-story.