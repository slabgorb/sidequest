---
story_id: "71-8"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 71-8: Fix pre-existing pyright error in reference_presenters.py present_magic rows reassignment

## Sm Assessment

Trivial 1-pt chore: fix a pre-existing pyright error in `sidequest-server` `reference_presenters.py` — the `present_magic` rows reassignment. Scope is a single type/annotation fix in one file; no behavior change, no new wiring.

**Context for Dev (implement phase):**
- Locate the `present_magic` function in `reference_presenters.py` and the `rows` reassignment pyright flags. Likely a variable reassigned to an incompatible inferred type (e.g. list narrowed then reassigned). Fix the annotation or restructure the reassignment so pyright is satisfied without `# type: ignore`.
- Verify with the server type-check gate (pyright) before claiming done — confirm the specific error is gone and no new errors introduced.
- Branch base is clean `origin/develop` (server was parked on the unmerged `feat/61-17` branch; switched to develop before setup).

**Branch:** `feat/71-8-fix-pyright-reference-presenters-present-magic`
**Repos:** sidequest-server

## Story Details
- **ID:** 71-8
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-28T16:47:49Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T16:00:00Z | 2026-05-28T16:40:53Z | 40m 53s |
| implement | 2026-05-28T16:40:53Z | 2026-05-28T16:45:13Z | 4m 20s |
| review | 2026-05-28T16:45:13Z | 2026-05-28T16:47:49Z | 2m 36s |
| finish | 2026-05-28T16:47:49Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): `develop` carries two pre-existing test failures unrelated to 71-8 — `test_zones_carry_cache_boundary_flag` (the 61-17 fix lives on its unmerged branch `feat/61-17`, not develop) and `test_all_live_packs_pass_cross_reference_lint` (missing asset dirs in sidequest-content). Affects `sidequest-server/tests` (61-17 PR #499 needs to merge; content asset gate). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Story 61-17 is marked `done` in the sprint but its fix sits on the unmerged `feat/61-17` branch (draft PR #499), so `test_zones_carry_cache_boundary_flag` fails on `develop`. Affects `sidequest-server` (merge/close PR #499 or reopen 61-17). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Two pre-existing ruff issues exist in untouched test files — `tests/dungeon/conftest.py` (I001) and `tests/server/test_arc_embedding_durability.py` (UP037). Affects `sidequest-server/tests` (independent cleanup, not introduced here). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Ran `ruff format` normalized one adjacent pre-existing whitespace line**
  - Spec source: story scope (session) — "single type/annotation fix in one file"
  - Spec text: "Scope is a single type/annotation fix in one file; no behavior change, no new wiring."
  - Implementation: The required fix is the `rows`→`limit_rows` rename in `present_magic`. Running the mandatory project `ruff format` also re-wrapped one pre-existing ternary in `_class_panel_body` (line ~717) that was not yet conformant.
  - Rationale: Project gate requires `ruff format`; the file was not fully format-clean before. The extra hunk is pure whitespace, no behavior change.
  - Severity: trivial
  - Forward impact: none

### Reviewer (audit)
- **Dev's `ruff format` whitespace normalization in `_class_panel_body`** → ✓ ACCEPTED by Reviewer: the hunk is pure formatting (a multi-line ternary collapsed to one line), `escape(name)` and the `if name else ""` guard are byte-identical before/after. Running the mandatory project formatter is correct hygiene, not scope creep. No undocumented deviations found.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/reference_presenters.py` — renamed local str `rows`→`limit_rows` in `present_magic` to resolve the `reportAssignmentType` pyright error (str assigned to a scope that later declares `rows: list[str]`); plus an incidental `ruff format` whitespace normalization.

**Tests:** reference suite 39/39 direct + 425 (`-k reference`) passing (GREEN); pyright 0 errors on the file; ruff lint + format clean.
**Branch:** `feat/71-8-fix-pyright-reference-presenters-present-magic` (pushed)

**Handoff:** To review phase (Colonel Potter / reviewer).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A (disabled via settings) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A (disabled via settings) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A (disabled via settings) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A (disabled via settings) |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A (disabled via settings) |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A (disabled via settings) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A (disabled via settings) |

**All received:** Yes (2 enabled returned clean; 7 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

This is a trivial 1-point pyright type-fix. `present_magic()` bound the name `rows` to a `str` at line 924, while the same function later declares `rows: list[str]` at line 940 (the counters block) — pyright's single-scope inference treated the str assignment as `reportAssignmentType`. Dev renamed the str to `limit_rows` (referenced only at 924 and 930), eliminating the collision. I independently confirmed via `grep` that the four other `rows: list[str]` declarations (lines 350, 988, 1080, 1125) are in separate functions and untouched, so the rename is correct and complete.

**Data flow traced:** genre-pack `magic.hard_limits` dict → `_format_chip_label(str(k/v))` → `escape(...)` → `limit_rows` HTML string → `parts.append(...)`. Safe because every content-derived value still passes through `html.escape` (verified byte-identical to pre-change) — no injection surface introduced.
**Pattern observed:** local-variable rename to resolve scope-wide annotation collision at `sidequest/server/reference_presenters.py:924`. Correct, minimal, idiomatic.
**Error handling:** unchanged — the `isinstance(limits, dict) and limits` guard and the `elif list` branch are untouched.

**Subagent dispatch tags:**
- [EDGE] — disabled via settings; no boundary surface in a rename (assessed N/A by reviewer).
- [SILENT] — disabled; no error-handling paths changed (assessed N/A).
- [TEST] — disabled; no test changes in this diff (assessed N/A).
- [DOC] — disabled; the `# Hard limits:` comment remains accurate (assessed N/A).
- [TYPE] — disabled; the fix itself is a type-correctness improvement, pyright 0 errors (assessed N/A).
- [SEC] — reviewer-security returned **clean**: all `escape()` calls preserved, no new untrusted-input surface.
- [SIMPLE] — disabled; diff is already minimal, no dead code (assessed N/A).
- [RULE] — disabled; manual rule check below.

### Rule Compliance
- **No Silent Fallbacks** (CLAUDE.md/SOUL.md): compliant — no fallback paths added or changed; the dict/list branch structure is intact.
- **HTML escaping of genre-pack content**: compliant — `escape(_format_chip_label(str(k)))` / `escape(...str(v)...)` preserved verbatim; `escape(name)` in `_class_panel_body` preserved verbatim.
- **No Stubbing / No half-wired features**: compliant — the renamed variable is consumed immediately by `parts.append`; reachable production path (the existing reference-page render walk).
- **OTEL observability**: N/A — cosmetic/type change, explicitly exempt per CLAUDE.md ("Not needed for cosmetic changes").

### Devil's Advocate
Could this rename break rendering? Only if `limit_rows` were referenced elsewhere under the old name `rows` — but `grep` confirms the old `rows` at 924 was local to the `if isinstance(limits, dict)` block and used exactly once at line 930, now both renamed. Could a malicious genre-pack inject script through `hard_limits`? No — keys and values flow through `html.escape`, identical to before; the change touches the *variable name*, not the escaping. Could a confused author misread `limit_rows` vs the counters' `rows`? Unlikely — the new name is more descriptive, reducing confusion. Could the incidental `_class_panel_body` reformat alter output? No — it collapses a ternary onto one line; Python evaluates it identically, and `escape(name)` is unchanged. Could the pre-existing test failures hide a regression here? No — `test_zones_carry_cache_boundary_flag` (61-17, not on develop) and `test_all_live_packs_pass_cross_reference_lint` (content asset gate) are both demonstrably unrelated to reference-presenter rendering, and the 39 direct reference-presenter tests + 425 `-k reference` tests pass. No new failure surfaced. Nothing broken.

**Handoff:** To SM (Hawkeye Pierce) for finish-story.