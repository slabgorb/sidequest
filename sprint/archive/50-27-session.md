---
story_id: "50-27"
jira_key: null
epic: "50"
workflow: "trivial"
---

# Story 50-27: Fix forensics wiring-test drift — test_forensics_route asserts stale honesty-contract copy vs rephrased forensics.html

## Story Details
- **ID:** 50-27
- **Jira Key:** null (Jira explicitly skipped — personal project per CLAUDE.md convention)
- **Workflow:** trivial
- **Stack Parent:** none

## Story Context

This is a pre-existing test/content drift on origin/develop (commit f43bd88, PR #332 / story 50-26). The forensics UI honesty-contract has been rephrased, causing the wiring test assertion to fail — this blocks story 48-4's merge until develop is green.

### Technical Context: Full Diagnosis

**Failure:**
`tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html` (line 154) asserts `"NOT a stored snapshot" in resp.text`

**Root cause:**
- Assertion introduced: commit a27d997 (old honesty contract wording)
- HTML rephrased: commit 66a8176 (new wording deployed)
- Both commits ≤ develop HEAD f43bd88
- Literal substring `"NOT a stored snapshot"` no longer appears in forensics.html

**Verification:**
- `git log f43bd88..HEAD -- sidequest/server/static/forensics.html tests/server/test_forensics_routes.py` returns empty — this is pre-existing drift, NOT a regression from 48-4 work
- Independently confirmed out-of-scope-for-48-4 by TEA, reviewer-preflight, and Reviewer
- Cross-story contamination risk identified: 50-27 must NOT fold into the 48-4 PR

### Current Forensics Copy (forensics.html:314)

The redesigned honesty-contract meta line reads:
```
'the ONLY stored snapshot — identical on every round, NOT this round's state'
```

This is the ground truth wording reflecting the actual behavior (one persistent snapshot vs. per-round derivations).

### Acceptance Criteria

1. **Test passes:** `test_forensics_route_is_wired_and_serves_html` passes by realigning the assertion to the current honesty-contract copy in forensics.html. The assertion must remain a genuine honesty-contract check (proving the "we do not store per-round snapshots" contract is served), not merely a route 200 check.

2. **Full suite green:** `uv run pytest -q` (sidequest-server) is green on the 50-27 branch, modulo unrelated pre-existing skips. This unblocks 48-4 finish.

3. **Scope: forensics files only:** Fix is strictly scoped to:
   - `tests/server/test_forensics_routes.py` (test assertion)
   - `sidequest/server/static/forensics.html` (if needed for honesty-contract wording adjustment)
   - Must NOT touch any ab_eval / 48-4 files
   - Must NOT be folded into the 48-4 PR (cross-story contamination gates)

## Workflow Tracking

**Workflow:** trivial (setup → implement → review → finish)
**Phase:** finish
**Phase Started:** 2026-05-18T18:29:02Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-18T18:15:24Z | 2026-05-18T18:18:05Z | 2m 41s |
| implement | 2026-05-18T18:18:05Z | 2026-05-18T18:23:30Z | 5m 25s |
| review | 2026-05-18T18:23:30Z | 2026-05-18T18:29:02Z | 5m 32s |
| finish | 2026-05-18T18:29:02Z | - | - |

## Delivery Findings

No upstream findings at setup time.

### Dev (implementation)
- No upstream findings during implementation. The fix was exactly as diagnosed in setup — a single stale literal in the wiring test vs the rephrased honesty-contract copy. No production code, no HTML, and no other test required change. (The orphan server PR #333 hygiene item is SM-owned and pre-flagged; not a 50-27 implementation finding.)

## Design Deviations

No design deviations recorded at setup time.

### Dev (implementation)
- No deviations from spec. Implemented AC1 exactly: realigned the test assertion to a stable substring of the current served honesty-contract copy (`"stores no per-round snapshot"` from `forensics.html:295`), kept it a genuine honesty-contract check, left `forensics.html` untouched as ground truth, and confined the change strictly to `tests/server/test_forensics_routes.py` per AC3. AC2 verified by full-suite run (0 failed).

### Reviewer (audit)
- **Dev: "No deviations from spec."** → ✓ ACCEPTED by Reviewer. Independently verified: `git diff origin/develop...HEAD` is exactly one line in one test file — the AC1 assertion realignment, nothing more. Dev correctly chose the AC1 *preferred* path (realign the drifted test, treat `forensics.html` as ground truth) over editing HTML, and correctly picked `forensics.html:295`'s straight-text phrase over line 314's `round's` (U+2019 curly apostrophe — a fragile assertion target Dev avoided). No undocumented deviation exists. The claim is accurate.

## SM Assessment

**Phase:** finish → implement | **Verdict:** READY FOR DEV

Story 50-27 is set up and ready for the implement phase. This is a 1-point, p1, trivial-workflow bug fix scoped strictly to forensics files in sidequest-server.

- **Session:** created at `.session/50-27-session.md` with full diagnosis (drift commits `a27d997` test-assertion vs `66a8176` HTML rephrase, both ≤ develop HEAD `f43bd88`) and 3 acceptance criteria.
- **Branch:** `feat/50-27-fix-forensics-wiring-test-drift` created in sidequest-server off `origin/develop` (gitflow base — PR targets `develop`, not main).
- **Status:** sprint YAML backlog → in_progress (via pf, no hand-edit).
- **Jira:** explicitly skipped — personal project; `pf jira *` forbidden by CLAUDE.md convention.

**Why this story exists / urgency:** 50-27 is the unblock for already-approved story 48-4. 48-4's finish was deferred by user decision (2026-05-18) because `origin/develop` is red from this pre-existing forensics drift (independently confirmed out-of-scope-for-48-4 by TEA, reviewer-preflight, and Reviewer). Develop must go green before 48-4 can merge. Resume path: 50-27 merges → develop green → re-run `/pf-sm` on 48-4.

**Hard scope guard for Dev:** Touch ONLY `tests/server/test_forensics_routes.py` and/or `sidequest/server/static/forensics.html`. Do NOT touch any ab_eval / 48-4 files. Do NOT fold this fix into the 48-4 PR — that is cross-story contamination into already-merged 50-26 / PR #332 territory. The realigned assertion must remain a genuine honesty-contract check (proves the "no per-round snapshot stored" contract is served), not a bare route-200 check. AC2 (full `uv run pytest -q` green on the branch) is the gate that unblocks 48-4 — it must actually be verified, not assumed.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for the implement phase.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/tests/server/test_forensics_routes.py` — one-line assertion realignment in `test_forensics_route_is_wired_and_serves_html`: stale literal `"NOT a stored snapshot"` → current served honesty-contract copy `"stores no per-round snapshot"` (literal text at `sidequest/server/static/forensics.html:295`). No production code, no HTML changed.

**Root cause confirmed:** Pre-existing test/content drift on `develop` (HEAD `f43bd88`, via PR #332 / story 50-26). Test assertion introduced in `a27d997`; honesty-contract HTML copy rephrased in `66a8176`; both ≤ `f43bd88`. The HTML is ground truth (reflects actual behavior — one persistent snapshot, no per-round persistence); the test drifted, so the test was realigned (AC1 preferred path).

**Tests (verified via testing-runner, RUN_ID 50-27-dev-green):**
- AC1 — `test_forensics_route_is_wired_and_serves_html`: **1 passed**
- `tests/server/test_forensics_routes.py` (full file): **11 passed**
- AC2 — full server suite (`uv run pytest -q`): **6338 passed, 0 failed, 400 skipped** → **GREEN**. (The ~21-test delta vs the 48-4 session's prior baseline is exactly 48-4's ab_eval suite, which is correctly absent on this clean-`develop` branch — not a regression.)
- `ruff check tests/server/test_forensics_routes.py`: clean

**ACs:** AC1 ✅ (assertion realigned, remains a genuine honesty-contract check) · AC2 ✅ (full suite green on branch — the gate that unblocks 48-4) · AC3 ✅ (scope strictly the one test file; no ab_eval/48-4 files touched; not folded into the 48-4 PR)

**Branch:** `feat/50-27-fix-forensics-wiring-test-drift` (sidequest-server, commit `f9f1ad1`, pushed, tracks origin). No PR — SM creates/merges in finish.

**Handoff:** To Reviewer (Colonel Sherman Potter) for the review phase.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (6338 passed / 0 failed / 400 skipped; ruff 0; diff 1 file +1/-1; 0 smells) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings (workflow.reviewer_subagents.edge_hunter=false) — domain assessed by Reviewer directly |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer directly |

**All received:** Yes (1 enabled subagent returned clean; 8 disabled via `workflow.reviewer_subagents`, pre-filled and domain-assessed directly)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred; 1 non-blocking ambient observation (pre-existing FastAPI deprecation warnings, NOT a 50-27 defect)

## Reviewer Assessment

**Verdict:** APPROVED

This is a one-line wiring-test assertion realignment. Decades of experience say the smallest changes are where people get lazy — so I traced it myself rather than trust the author or the preflight. It holds.

**Data flow traced:** HTTP `GET /forensics` → `forensics_router` (registered at `app.py:298` via `app.include_router(forensics_router)`) → `forensics()` handler (`forensics.py:19-22`) returns `FileResponse` over `files("sidequest.server").joinpath("static/forensics.html")` → the test's `resp.text` is therefore the **raw** static HTML file content (inline JS included) → `assert "stores no per-round snapshot" in resp.text`. The asserted literal exists verbatim at `forensics.html:295` inside the comparison-panel label `(SideQuest stores no per-round snapshot — see terminal snapshot below)`. The old literal `"NOT a stored snapshot"` appears **0 times** in the file (independently grep-verified by me and by preflight). The assertion is satisfiable, specific (exactly one occurrence in the file), and non-vacuous. Safe.

**Pattern observed:** AC1-preferred drift resolution — the test, not the ground-truth artifact, was realigned. `forensics.html` left untouched because it reflects actual runtime behavior (one persistent terminal snapshot, no per-round persistence). The honesty-contract intent of the assertion is preserved and arguably sharpened: the new phrase explicitly states SideQuest does *not* persist per-round snapshots, which is the exact contract the GM panel must surface so a career GM is not fooled into reading derived state as stored ground truth (SOUL.md "OTEL is the lie detector" spirit). The change does not weaken the wiring proof — lines 150-153 still independently assert status 200, `text/html`, `"Save Forensics"`, and `/api/debug/saves`; the honesty line is one of five orthogonal assertions, not the whole test.

**Error handling:** N/A to the diff (no control flow changed — a string literal in one assertion). The test's own failure mode is correct: if the honesty-contract copy drifts again, this assertion fails loudly (no silent fallback), which is the desired tripwire.

### Observations

1. `[VERIFIED]` Substring is real and unique — `forensics.html:295` contains `stores no per-round snapshot` exactly once; old literal `NOT a stored snapshot` count = 0. Evidence: my own `grep -n`/`grep -c` + preflight check #6 corroborate. Complies with python.md test-quality (assertion is specific, not a substring so generic it always passes).
2. `[VERIFIED]` Route genuinely serves the asserted bytes — `forensics.py:20-22` `FileResponse` of the static asset; `app.py:298` registers the router. The wiring test's premise ("proves app.py registered the router and the static asset resolves") remains true; the realigned line still rides that proof. Evidence: `app.py:28,297-298`, `forensics.py:16-22`.
3. `[VERIFIED]` AC2 gate satisfied — full server suite 6338 passed / **0 failed** / 400 skipped (preflight, RUN_ID corroborated by Dev's testing-runner run). This is the actual condition that unblocks story 48-4. Verified, not assumed.
4. `[VERIFIED]` AC3 scope clean — `git diff origin/develop...HEAD --stat` = 1 file, +1/-1, `tests/server/test_forensics_routes.py` only. Zero production code, zero HTML, zero ab_eval/48-4 files. No cross-story contamination into PR #332 / 50-26 territory. Working tree clean (only untracked `.claude/`, expected).
5. `[TEST]` `[VERIFIED]` (domain assessed directly — reviewer-test-analyzer disabled): the assertion is not vacuous or tautological. It checks a specific honesty-contract phrase that can fail; it does not collapse to a route-200 check (those assertions are separate lines). The `# honesty contract visible` comment is still accurate post-change — not stale.
6. `[DOC]` `[VERIFIED]` (domain assessed directly — reviewer-comment-analyzer disabled): inline comment `# honesty contract visible` correctly describes the new assertion. No stale/misleading comment introduced.
7. `[SIMPLE]` `[VERIFIED]` (domain assessed directly — reviewer-simplifier disabled): minimal change, no over-engineering, no dead code. The simplest correct fix for the drift.
8. `[EDGE]` `[SILENT]` `[TYPE]` `[SEC]` `[RULE]` (domains assessed directly — subagents disabled): no boundary conditions, swallowed errors, type-design surface, security surface, or project-rule surface is touched by a single string-literal change in a test assertion. No injection/auth/secret/tenant surface (offline read-only test). N/A across all five — no findings.
9. `[LOW]` `[non-blocking]` Pre-existing ambient noise (NOT a 50-27 defect): `DeprecationWarning: on_event is deprecated` from `sidequest/server/app.py:145,150,157,206,218` fires on every app-spinning test. Pre-exists on develop, unrelated to this diff, no AC covers it. Surfaced by preflight; logged as a non-blocking Delivery Finding for future hygiene, not a rework item.

### Rule Compliance (python.md / SOUL.md / CLAUDE.md — enumerated against the 1-line diff)

The diff changes exactly one assertion string in one test function. Enumerating every applicable rule against the single changed element (`test_forensics_route_is_wired_and_serves_html`'s honesty-contract assertion):

- **Test quality (no vacuous/tautological assertions, no `assert True`, no unconditional skip):** the assertion checks a specific, falsifiable substring with exactly one source occurrence — **Compliant**.
- **No silent fallbacks (CLAUDE.md / SOUL.md):** assertion fails loudly on future drift; no try/except, no default, no alternative path introduced — **Compliant**.
- **No stubbing / no half-wired (CLAUDE.md):** no stub, no skeleton; the wiring test remains a genuine end-to-end route+asset proof — **Compliant**.
- **Every test suite needs a wiring test (CLAUDE.md):** this *is* the forensics wiring test; the change strengthens, not removes, its honesty-contract leg — **Compliant**.
- **OTEL observability principle (CLAUDE.md):** N/A — explicitly exempt ("Not needed for: cosmetic changes (label rewording)"); this is a test-side string realignment, no subsystem decision path touched — **N/A, correctly**.
- **Personal-project / no-Jira (CLAUDE.md):** session `jira_key: null`, no Jira interaction — **Compliant**.
- **Gitflow base = develop (CLAUDE.md / repos.yaml):** branch cut off `origin/develop`; diff computed `origin/develop...HEAD` — **Compliant**.
- **Type-annotation / mutable-default / async / import-hygiene / deserialization / path-handling / resource-leak rules:** no code element of those kinds is added or modified by a string-literal swap in an assertion — **N/A, no surface**.

No rule is violated. No rule that applies was left unchecked.

### Devil's Advocate

Assume this fix is theater and the suite is green for the wrong reason. Attack vectors considered:

1. **"The assertion now always passes."** If `"stores no per-round snapshot"` were a string the framework injects regardless of the page (e.g., a default error body), the test would be vacuous. Refuted: the route returns `FileResponse` of a specific static asset (`forensics.py:20-22`); the literal occurs exactly once, only inside the page's comparison-panel label (`grep -c` = 1). Remove that label and the test fails. Genuinely coupled to the contract.

2. **"They weakened the honesty contract to make red go green."** The cynical read: pick any substring that happens to be present. Refuted: the chosen phrase is *more* explicit about the contract than the old one — it literally states SideQuest "stores no per-round snapshot," which is the precise claim the GM panel must make so a 40-year-GM isn't fooled by derived state. The old `"NOT a stored snapshot"` and the new `"stores no per-round snapshot"` assert the same invariant; the new one is the stronger phrasing. Not a weakening.

3. **"They asserted against fragile text."** There were two candidate honesty strings: line 295 (straight ASCII) and line 314 (`...NOT this round's state`, where `'` is U+2019). Asserting against line 314 would be brittle — any source re-encoding or smart-quote normalization flips the byte and the test fails spuriously. Dev chose line 295, the robust target. Correct judgment, not luck.

4. **"Green is masking a real regression."** Could the suite be green because the fix accidentally suppressed other failures? Refuted: diff is +1/-1 in a single test assertion — it is structurally impossible for a string literal in `test_forensics_route_is_wired_and_serves_html` to affect any other test. The 6338-vs-prior-6359 delta is fully explained (48-4's ab_eval suite absent on clean develop), independently reasoned, not a vanished-tests cover-up. Pre-fix this exact test was the sole red; post-fix 0 red.

5. **"Scope contamination."** Could 50-27 have smuggled forensics.html or 48-4 edits? Refuted: `git diff --stat` = 1 file, the test only. forensics.html untouched (correct — it's ground truth). No 48-4/ab_eval path in range. The cross-story firewall the prior reviewers demanded is intact.

6. **Stressed filesystem / confused operator:** the change adds no I/O, no parsing, no config surface. The only residual risk is the pre-existing `on_event` deprecation noise, which is develop-wide, unrelated, and explicitly out of scope. A future FastAPI major could turn those warnings into errors — flagged as a non-blocking finding so it is not lost, but it is emphatically not this story's defect and not a reason to block the gate that frees 48-4.

The devil gets nothing blocking. The fix is real, minimal, correctly scoped, and the honesty-contract assertion is preserved-to-strengthened. APPROVE is correct.

**Handoff:** To SM (Hawkeye Pierce) for finish-story. 50-27 is APPROVED. Merging this to `develop` makes the full server suite green, which clears the gate deferring story 48-4's finish — after 50-27 merges, re-run `/pf-sm` on 48-4 to complete its finish ceremony.

### Reviewer (code review)
- **Improvement** (non-blocking): pre-existing `DeprecationWarning: on_event is deprecated, use lifespan event handlers instead` fires from `sidequest/server/app.py` lines 145, 150, 157, 206, 218 on every app-spinning test. Develop-wide, unrelated to 50-27, no AC covers it; a future FastAPI major may promote these to errors. Affects `sidequest/server/app.py` (migrate `@app.on_event` startup/shutdown handlers to the `lifespan` context-manager API). Recommend a separate hygiene chore. *Found by Reviewer during code review.*