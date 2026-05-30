---
story_id: "64-7"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 64-7: Expand 61 missing namegen corpus files flagged by audit

## Story Details
- **ID:** 64-7
- **Jira Key:** (none — this is a kanban story)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-30T20:10:16Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30T19:22:41Z | 2026-05-30T19:24:14Z | 1m 33s |
| red | 2026-05-30T19:24:14Z | 2026-05-30T19:36:14Z | 12m |
| green | 2026-05-30T19:36:14Z | 2026-05-30T19:40:18Z | 4m 4s |
| spec-check | 2026-05-30T19:40:18Z | 2026-05-30T19:42:16Z | 1m 58s |
| verify | 2026-05-30T19:42:16Z | 2026-05-30T19:45:27Z | 3m 11s |
| review | 2026-05-30T19:45:27Z | 2026-05-30T19:53:53Z | 8m 26s |
| green | 2026-05-30T19:53:53Z | 2026-05-30T19:58:24Z | 4m 31s |
| spec-check | 2026-05-30T19:58:24Z | 2026-05-30T19:59:27Z | 1m 3s |
| verify | 2026-05-30T19:59:27Z | 2026-05-30T20:03:14Z | 3m 47s |
| review | 2026-05-30T20:03:14Z | 2026-05-30T20:08:13Z | 4m 59s |
| spec-reconcile | 2026-05-30T20:08:13Z | 2026-05-30T20:10:16Z | 2m 3s |
| finish | 2026-05-30T20:10:16Z | - | - |

## Story Context

### Problem Statement

The audit script `scripts/audit_namegen_corpora.py` reports "61 MISSING" corpus files, but they actually exist and work at runtime.

**Root Cause:** The audit script resolves corpus references only as `pack_dir/corpus/<ref>`, but the runtime resolver (`sidequest/genre/names/generator.py:251`) also searches `sidequest-content/corpus/shared/` as a fallback. Four packs (space_opera, neon_dystopia, elemental_harmony, mutant_wasteland) have no per-pack corpus directory, so their references resolve from the shared fallback at runtime but fail in the audit.

**Verification (2026-05-30):**
- Running `uv run python scripts/audit_namegen_corpora.py` reports "0 FAIL, 61 MISSING, 0 THIN, 0 OK" with rc=0.
- The 61 MISSING rows collapse to just 22 distinct corpus files (pack × culture × slot deduplicated).
- All 22 files exist in `sidequest-content/corpus/shared/` with healthy word counts (georgian.txt 1004 words … russian.txt 566337 words).
- Zero files are absent or empty.
- Tests in `tests/scripts/test_audit_namegen_corpora.py` fail (4 tests, RED).

### Acceptance Criteria

1. **Audit script replicates the shared-corpus fallback** — `scripts/audit_namegen_corpora.py` now searches `sidequest-content/corpus/shared/` when a per-pack corpus file is missing, matching `generator.py:251(_resolve_corpus_file)`.
2. **Tests pass** — All 4 tests in `tests/scripts/test_audit_namegen_corpora.py` now pass; audit exits rc=0 on the live tree.
3. **No duplicate corpus files** — The 22 distinct files remain in `corpus/shared/` (single source of truth); no per-pack duplicate files are created.
4. **Parity test present** — The test suite verifies that the audit script and runtime generator resolve the same set of corpus files for the affected packs.

### Technical Details

**Audit Script (Current):**
- `scripts/audit_namegen_corpora.py:108` resolves corpus refs only from `pack_dir/corpus/<ref>`.
- Missing fallback causes false positives for packs without a per-pack corpus directory.

**Runtime Resolver (Reference):**
- `sidequest/genre/names/generator.py:251(_resolve_corpus_file)` searches fallback_dirs including `sidequest-content/corpus/shared/`.
- This is the ground truth for how the game actually resolves corpus files.

**Affected Packs:**
- space_opera, neon_dystopia, elemental_harmony, mutant_wasteland (no per-pack corpus dir).
- All four reference corpus files from shared/ at runtime.

**Test File:**
- `tests/scripts/test_audit_namegen_corpora.py` — 4 failing tests (RED).
- Tests should pass once audit mirrors the runtime fallback logic.

## Sm Assessment

**Routing decision:** Set up for the `tdd` workflow → hand off to TEA (red phase).

**Scope confirmed empirically (2026-05-30):** The story's original title premise ("expand 61 missing corpus files") is FALSE and must not be acted on. I re-verified today: `uv run python scripts/audit_namegen_corpora.py` reports "0 FAIL, 61 MISSING, 0 THIN, 0 OK" (rc=0). Those 61 are (pack × culture × slot × corpus-ref) table rows that collapse to **22 distinct files**, and **all 22 exist** in `corpus/shared/` with healthy word counts. Zero are absent, zero empty. This is a pure audit-script false-positive — the runtime resolver (`generator.py:251`) already searches the shared fallback the audit lacks.

**Repointed 5 → 2** to match the true size: a single-path fix (teach the audit the `corpus/shared/` fallback) plus making the 4 pre-existing failing tests green. Absorbs canceled story 64-9.

**Hard constraint for downstream agents:** DO NOT author any corpus files. The single source of truth is `corpus/shared/`; duplicating files there would be the wrong fix and would mask the real audit defect. The fix lives entirely in `scripts/audit_namegen_corpora.py` (resolution path) + its tests.

**Note for TEA:** The 4 RED tests already exist in `tests/scripts/test_audit_namegen_corpora.py`. Your red-phase job is to confirm they fail for the *right* reason (audit lacks the shared fallback), and that they assert the audit↔runtime resolution parity rather than coupling to implementation details.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Resolution-path defect in `scripts/audit_namegen_corpora.py`; not a chore-bypass category.

**Test File:** `sidequest-server/tests/scripts/test_audit_namegen_corpora.py`

**Tests Written:** 11 total (5 RED fix-drivers, 6 PASSING guards) covering ACs 1–4.
**Status:** RED (5 failing — ready for Dev). Verified by `testing-runner` (RUN_ID 64-7-tea-red): **5 failed / 6 passed**, every failure rooted in the absent `corpus/shared/` fallback (audit reports 61 MISSING → rc=1). No collection/import errors.

**AC → test mapping:**

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 audit resolves the shared fallback (mirror `generator.py:_resolve_corpus_file`) | `test_audit_synthetic_shared_fallback_resolves` | failing (RED) |
| AC2 0 MISSING, rc=0 on live tree | `test_audit_live_tree_reports_zero_missing`, `test_audit_live_tree_exits_zero_after_corpus_expansion` | failing (RED) |
| AC3 the 4 pre-existing failing tests pass | all four now pass post-fix (two rewritten to the real layout, two unchanged) | failing (RED) |
| AC4 no new corpus files; parity with runtime | `test_audit_synthetic_shared_fallback_resolves` (corpus only in `corpus/shared/`), `test_shared_corpora_clear_warn_threshold` | RED / passing |

**Key design choice — behavioral parity over implementation coupling:** `test_audit_synthetic_shared_fallback_resolves` builds a hermetic pack whose corpus lives ONLY in `<root>/corpus/shared/` (no per-pack copy) and asserts the audit resolves it exactly as the runtime resolver does. This pins audit↔runtime parity *behaviorally* (per the SM note) without grepping the audit's source or hardcoding the fallback path — refactor-stable, fails on real wiring breakage.

**No Silent Fallbacks guard:** `test_audit_synthetic_absent_corpus_still_missing` proves the shared fallback resolves *real* files only and does not blanket-silence the MISSING signal — a genuinely absent corpus still exits rc=1.

### Rule Coverage

This is a CLI/audit script (no pydantic models, tenants, or enums). Lang-review rules apply via these checks:

| Rule | Test(s) | Status |
|------|---------|--------|
| No Silent Fallbacks (fail loud on genuine absence) | `test_audit_synthetic_absent_corpus_still_missing` | passing (guard) |
| Exit-code contract integrity (FAIL/MISSING→1, OK/THIN→0) | `test_audit_synthetic_fail_corpus_exits_one`, `..._ample..._exits_zero`, `..._thin..._exits_zero_with_thin_marker` | passing (guard) |
| Wiring / behavior (live-tree, not source-text) | all `test_audit_live_tree_*` run the real script against real content | RED |
| Meaningful assertions (no vacuous tests) | self-checked — every test asserts rc and/or report content; no `assert True`/`let _ =` | n/a |

**Rules checked:** No Silent Fallbacks + exit-code contract + behavior-not-source-text wiring all have coverage.
**Self-check:** 0 vacuous tests found; the two rewritten tests removed obsolete-premise assertions.

**Handoff:** To Dev (Puck) for GREEN — add the `corpus/shared/` fallback to `scripts/audit_namegen_corpora.py:_audit_pack` (compute `pack_dir.parent.parent / "corpus" / "shared"`, check it when `pack_dir/corpus/<ref>` is absent, before flagging MISSING). Mirror `generator.py:_resolve_corpus_file`. Do NOT author corpus files. Do NOT widen scope to the per-culture-directory walker (Delivery Finding #1).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/scripts/audit_namegen_corpora.py` (+35/−2) — added `_resolve_corpus_path()` (mirrors `generator.py:_resolve_corpus_file`: pack `corpus/` dir first, then the `corpus/shared/` fallback; returns `None` on a true miss so a genuine absence still records a MISSING row — No Silent Fallbacks). Wired `_audit_pack` to compute `fallback_dirs = [pack_dir.parent.parent / "corpus" / "shared"]` and resolve through the helper before flagging MISSING.

**Scope honored:** No corpus files authored. The per-culture-directory walker (TEA Gap finding) was deliberately left untouched — out of scope.

**Result:** Audit now reports `0 FAIL, 0 MISSING, 0 THIN, 61 OK` (rc=0); the 61 phantom-MISSING rows resolve to OK via the shared fallback.

**Tests:** 11/11 passing (GREEN). Verified by `testing-runner` (RUN_ID 64-7-dev-green): story file 11 passed / 0 failed, and the full `tests/scripts/` suite 11 passed / 0 failed — no regression. `ruff check` clean, `ruff format` applied, `pyright` 0 errors.

**Branch:** `feat/64-7-audit-corpus-shared-fallback` (pushed to origin, commit `6cf5cf33`).

**Handoff:** To Reviewer (Portia) for code review.

### Dev Rework — Round 1 (post-review)

Reviewer REJECTED on verification-integrity grounds (no production-logic defect). All three findings addressed (test/doc-only); commit `0a811aa7`:

- **[HIGH] vacuous `assert "OK"`** (`test_audit_synthetic_shared_fallback_resolves`) → replaced with a co-located OK-row assertion `any("shared_only.txt" in line and "OK" in line for line in result.stdout.splitlines())`, which actually pins that the corpus landed as a counted OK row; the overclaiming comment is rewritten to match. (The summary's "N OK" can no longer falsely satisfy it.)
- **[MEDIUM] non-co-located substring checks** (`test_audit_surfaces_consumption_by_culture`) → replaced the two independent `in out` asserts with a same-row check (`rows = [line for line in out.splitlines() if culture in line and corpus_name in line]; assert rows`), then assert those rows aren't MISSING. Guards against mis-attribution.
- **[LOW] stale module docstrings** → both `scripts/audit_namegen_corpora.py:1` and `tests/scripts/test_audit_namegen_corpora.py:1` now cite Story 64-7, the `corpus/shared/` fallback, and the MISSING band (exit-code text corrected to MISSING → rc=1).

**Result:** No production-logic change — audit still `0 MISSING, 61 OK` (rc=0). 11/11 pass (verified by `testing-runner` RUN_ID 64-7-dev-green-rework: story file + full `tests/scripts/` both 11/0, no regression). `ruff` + `pyright` clean.

**Branch:** pushed, commit `0a811aa7`.

**Handoff:** Re-enters the pipeline at spec-check → verify → review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None (one minor maintainability observation, no action required)

**AC-by-AC verification:**
- **AC1 — audit replicates the shared-corpus fallback:** ALIGNED. `_resolve_corpus_path()` searches the pack `corpus/` dir, then `pack_dir.parent.parent / "corpus" / "shared"`. Verified this is **genuine path parity**, not just behavioral: all three production call sites compute the same expression — `narration_apply.py:1392`, `namegen.py:544`, `encountergen.py:491` (`<pack source dir>.parent.parent / "corpus" / "shared"`). Both resolve to `sidequest-content/corpus/shared`.
- **AC2 — 0 MISSING, rc=0 on live tree:** ALIGNED. Audit reports `0 FAIL, 0 MISSING, 0 THIN, 61 OK` (rc=0).
- **AC3 — no duplicate corpus files:** ALIGNED. Zero corpus files authored; the fix is entirely in the resolution path. Single-source-of-truth (`corpus/shared/`) preserved.
- **AC4 — parity test present:** ALIGNED. `test_audit_synthetic_shared_fallback_resolves` builds a pack whose corpus lives ONLY in `corpus/shared/` and asserts the audit resolves it as the runtime does — behavioral parity that also guards against the two resolvers drifting on the shared-fallback case.

**Minor observation (no action — recommendation D / defer):** The audit re-implements a parallel `_resolve_corpus_path` rather than importing `generator._resolve_corpus_file`. This is *justified* — the runtime resolver raises `FileNotFoundError` on a miss, while the audit needs `None`-return semantics to record a MISSING row (No Silent Fallbacks). The shared-fallback path literal now appears in 4 sites (3 production + audit); a future refactor could centralize a `shared_corpus_dir(pack_dir)` helper if a second fallback tier is ever added, but that is out of scope here and is not spec drift. TEA's parity test mitigates the drift risk for the case that matters.

**Note:** This change deliberately does NOT address the per-culture-directory walker blindness (TEA Gap finding) — correctly scoped out. That remains a real, separate defect (the audit cannot see aureate_span / perseus_cloud world cultures, incl. the yulan corpus). Recommend it be promoted to a follow-up story.

**Decision:** Proceed to review (TEA verify → Reviewer). No hand-back to Dev.

### Architect Assessment (spec-check — round 2, post-rework)

**Spec Alignment:** Aligned (unchanged from round 1)
**Mismatches Found:** None

The review-rework (commit `0a811aa7`) is **test- and docstring-only**. Verified via `git diff 6cf5cf33 0a811aa7 -- scripts/audit_namegen_corpora.py`: the *only* script change is the module docstring; the executable code (`_resolve_corpus_path`, the `_audit_pack` `fallback_dirs` computation) is byte-identical to the round-1 implementation. All four ACs remain satisfied; the runtime parity verified in round 1 is untouched. The rework tightened two test assertions (vacuous `"OK"` → co-located OK-row; independent substrings → same-row attribution) and refreshed stale docstrings — this *increases* verification honesty without altering behavior or scope.

**Decision:** Proceed to review (TEA verify → Reviewer). No hand-back to Dev.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`scripts/audit_namegen_corpora.py`, `tests/scripts/test_audit_namegen_corpora.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | (1) medium: two synthetic-pack builders share a ~15-line `cultures.yaml` template — extractable to `_build_synthetic_cultures_yaml(name, corpus_ref)`. (2) low: `_resolve_corpus_path` near-duplicates `generator._resolve_corpus_file` — already accepted by Architect (None-return vs raise). |
| simplify-quality | clean | Naming/docstrings/dead-code all clean; rewritten tests' names + docstrings match behavior; no stale references to old test names. |
| simplify-efficiency | clean | `fallback_dirs: list[Path]` weighed and ruled intentional parity with the runtime resolver, not over-engineering (audit is not a hot path). |

**Applied:** 0 high-confidence fixes (none were high-confidence).
**Flagged for Review:** 1 medium-confidence finding — test-only YAML-template extraction. Deliberately NOT auto-applied per the verify protocol (medium = flag, don't apply); the two builders are distinct fixtures and the duplication is benign test boilerplate. Reviewer may weigh whether it's worth a follow-up tidy.
**Noted:** 1 low-confidence observation (accepted resolver near-duplicate).
**Reverted:** 0.

**Overall:** simplify: clean (no fixes applied; 1 medium flagged for reviewer judgment)

**Quality Checks:** All passing. Verified by `testing-runner` (RUN_ID 64-7-tea-verify): 11 passed / 0 failed; `ruff check` clean on both changed files.

**Handoff:** To Reviewer (Portia) for code review.

### TEA Verify — Round 2 (post-rework)

Re-ran the three simplify lenses on the reworked diff. **All three clean** (reuse/quality/efficiency — no findings, no fixes applied). simplify-quality explicitly confirmed the reworked assertions are sound: the co-located OK-row check (`any("shared_only.txt" in line and "OK" in line ...)`) and the same-row culture/corpus attribution check are semantically correct and read clearly; docstrings now match behavior (exit-code text correctly states MISSING→rc=1); no stale references remain. The previously-flagged medium (synthetic-builder YAML boilerplate) was re-confirmed as deliberately-accepted distinct fixtures — not re-flagged.

**Overall:** simplify: clean. **Quality Checks:** All passing — `testing-runner` RUN_ID 64-7-tea-verify-r2: 11 passed / 0 failed; ruff clean.

**Handoff:** To Reviewer (Portia) for the second code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A (11 passed, ruff+pyright clean, live audit rc=0 "0 MISSING, 61 OK") |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 3 | confirmed 2, deferred 1 (pre-existing, out-of-diff) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3 (1 dup of [TEST], 2 stale-docstrings) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 | confirmed 1 (rule #6, corroborates [TEST]) |

**All received:** Yes (4 enabled returned, 5 disabled via `workflow.reviewer_subagents`)
**Total findings:** 4 confirmed, 0 dismissed, 1 deferred

**Convergence:** Three independent specialists (test-analyzer, comment-analyzer, rule-checker) flagged the SAME issue at HIGH confidence — the vacuous `assert "OK" in result.stdout` at `tests/scripts/test_audit_namegen_corpora.py:428` with a comment that overclaims what it verifies. This is the load-bearing finding.

## Reviewer Assessment

**Verdict:** REJECTED

### Rule Compliance (Python lang-review checklist — exhaustive)

| # | Rule | Instances checked | Result |
|---|------|-------------------|--------|
| 1 | Silent exception swallowing | `_resolve_corpus_path` (no except), `_load_cultures` (catches `ValidationError` w/ comment) | PASS |
| 2 | Mutable default args | `_resolve_corpus_path`, `_build_synthetic_pack_shared_only`, 5 test fns | PASS |
| 3 | Type annotations at boundaries | `_resolve_corpus_path(str, Path, list[Path]) -> Path \| None`; `_build_synthetic_pack_shared_only(Path, *, int) -> Path`; all tests `-> None` | PASS |
| 4 | Logging coverage/correctness | resolution layer returns `None` signal; absence surfaced as MISSING row + rc=1 | PASS |
| 5 | Path handling | all `pathlib` `/`; every `read_text`/`write_text` has `encoding="utf-8"`; CLI `--path` validated `.is_dir()` | PASS |
| **6** | **Test quality** | 14 assertions enumerated | **FAIL — 1 violation** (`:428` `assert "OK"` vacuous; summary always contains " OK.") |
| 7 | Resource leaks | only `read_text`/`write_text` (no dangling handles) | PASS |
| 8 | Unsafe deserialization | `yaml.safe_load`; `subprocess.run([...])` list-form (no `shell=True`) | PASS |
| 9 | Async pitfalls | no async in diff | N/A |
| 10 | Import hygiene | no star imports; inline `from thresholds import` explicit | PASS |
| 11 | Input validation at boundaries | `main()` validates `--path`; corpus filename is Pydantic-validated `Culture` field, operator CLI not web boundary | PASS |
| 13 | Fix-introduced regressions | re-scan of `_resolve_corpus_path` + `fallback_dirs` against #1–#12 | PASS |
| + | **No Silent Fallbacks** (CLAUDE.md/SOUL.md) | `_resolve_corpus_path` returns `None` → caller records MISSING; `test_audit_synthetic_absent_corpus_still_missing` pins rc=1 | PASS — invariant upheld AND tested |

### Observations (≥5)

- **[HIGH][TEST][RULE][DOC] Vacuous assertion + lying comment** at `tests/scripts/test_audit_namegen_corpora.py:428`. `assert "OK" in result.stdout` passes unconditionally — `_format_report` line 211 emits `f"{len(by_status['OK'])} OK."` in the summary on EVERY run (even `0 OK`). The comment at :426 ("Positively confirm it landed as a real, counted row (OK band), not silently skipped") claims a guarantee the assertion does not provide. The honest assertion is `assert "## OK" in result.stdout` — the section header at script line 219 renders only when OK rows exist (`if not rows: continue`), exactly mirroring how the sibling `test_audit_live_tree_reports_zero_missing` correctly distinguishes `"## MISSING"` (header) from `"0 MISSING"` (summary). Matches stated Python rule #6 (cannot be dismissed); flagged HIGH by three independent specialists. Block driven by **verification integrity** — a test whose comment overstates what it proves is precisely the "convincing-but-hollow verification" the project's OTEL-lie-detector ethos exists to prevent.
- **[MEDIUM][TEST] Independent (non-co-located) substring checks** at `:147–154` in `test_audit_surfaces_consumption_by_culture`. `assert corpus_name in out` and `assert culture in out` are separate — both pass even if the culture and its corpus appear on different report rows (or in an error trace). A regression that mis-attributes a corpus to the wrong culture, or moves the name to a header, would slip through. Fix: assert co-location — `assert any(culture in line and corpus_name in line for line in out.splitlines())`. (The MISSING-line negative check on the following lines already uses the correct per-line pattern, so this is an inconsistency within the same test.)
- **[LOW][DOC] Stale module docstrings (×2).** `scripts/audit_namegen_corpora.py:1` still reads "(Story 45-28)" and describes resolution as single "disk paths"; `tests/scripts/test_audit_namegen_corpora.py:1` enumerates only OK/THIN/FAIL with no mention of MISSING or the shared fallback. Both predate this change. Update to cite 64-7 and the `corpus/shared/` fallback / MISSING band.
- **[VERIFIED] Genuine runtime parity** — `_audit_pack` computes `pack_dir.parent.parent / "corpus" / "shared"` (script :133), identical to the three production call sites (`narration_apply.py:1392`, `namegen.py:544`, `encountergen.py:491`). Both resolve to `sidequest-content/corpus/shared`. Evidence: live audit flips 61 MISSING → 61 OK, rc=0. Complies with the No-Silent-Fallbacks rule (verified below).
- **[VERIFIED] No Silent Fallbacks upheld** — `_resolve_corpus_path` returns `None` on a true miss (script :96); `_walk_cultures` then records a MISSING `CorpusEntry` and `main()`'s `has_fail` includes MISSING → rc=1. The hermetic `test_audit_synthetic_absent_corpus_still_missing` pins this (rc=1 + `## MISSING` present). The fallback resolves real files only; it does not suppress the signal. This is the project's load-bearing rule and it is both honored and tested.
- **[VERIFIED] No corpus files authored** — `git diff --name-only develop...HEAD` returns exactly the two code files; AC3 (single-source-of-truth, no per-pack duplicates) holds.
- **[VERIFIED] Data flow traced** — operator runs `audit_namegen_corpora.py` → `main()` validates `--path` is a dir → iterates pack dirs → `_audit_pack` walks `cultures.yaml` cultures → each `corpus_ref.corpus` (Pydantic-validated string) → `_resolve_corpus_path(filename, pack/corpus, [shared])` → `count_words` → `_classify` → report + rc. No untrusted input reaches a dangerous sink (no eval/shell/SQL); `--path` is an operator-supplied dir, not a web boundary.

### Devil's Advocate

Argue the code is broken. First, the test suite's green is partly theatre: `test_audit_synthetic_shared_fallback_resolves` ends on `assert "OK" in result.stdout`, which a malicious or careless future edit could lean on — delete the two strong assertions above it (rc==0 and `## MISSING` not in stdout) and the test would STILL pass even if the shared fallback were ripped out and every corpus reported MISSING, because the summary line "0 OK" satisfies the substring. The comment actively invites this rot by asserting the OK-band is pinned when it is not. That is the single most dangerous line in the diff: a guard that looks load-bearing but isn't, wearing a comment that says it is.

Second, consider a confused maintainer. The audit walks only a single `cultures.yaml` per world — but two live worlds (aureate_span, perseus_cloud) now use a `cultures/` DIRECTORY. The audit reports "0 MISSING, 61 OK" and exits 0, radiating false confidence: it is BLIND to the very corpora a teammate (Jade) is authoring in perseus_cloud, including the `yulan_*` files shipped this same session. A maintainer reading a green audit would reasonably conclude "all corpora are healthy" — a lie of omission. (TEA correctly scoped this out and filed it; it is not a regression, but the green report overstates coverage.)

Third, a stressed filesystem: `_resolve_corpus_path` uses `.exists()` then the caller `.read_text()`s — a TOCTOU window, and `.exists()` follows symlinks, so a corpus symlinked into `corpus/shared/` resolves silently with no `.resolve()` guard (rule #5's symlink note). In this operator-CLI context that is benign, but it is an assumption, not a guarantee.

Fourth, the co-location gap: `test_audit_surfaces_consumption_by_culture` would green even if Hegemonic and latin.txt landed in unrelated rows. The attribution it claims to protect is not actually pinned.

What survives the assault: the production fix itself is correct, minimal, and genuinely parity-matched to runtime; the No-Silent-Fallbacks invariant is real and tested; rc/`## MISSING` assertions do gate the live behavior today. The rejection is about closing the verification-integrity gaps before they rot — not about a functional defect in the fix.

### Verdict

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Vacuous `assert "OK"` + comment overclaiming it pins the OK band (rule #6; 3-specialist convergence) | `tests/scripts/test_audit_namegen_corpora.py:428` (comment :426) | Change to `assert "## OK" in result.stdout` (or assert `shared_only.txt` co-located with `OK` on one line); make the comment match what it checks |
| [MEDIUM] | Culture/corpus substring checks not co-located — can false-pass | `tests/scripts/test_audit_namegen_corpora.py:147–154` | Assert culture and corpus appear on the SAME line: `any(culture in line and corpus_name in line for line in out.splitlines())` |
| [LOW] | Stale module docstrings (Story 45-28; no MISSING/shared-fallback) | `scripts/audit_namegen_corpora.py:1`, `tests/scripts/test_audit_namegen_corpora.py:1` | Cite Story 64-7 + the `corpus/shared/` fallback and MISSING band |

The production fix is correct and the core ACs are genuinely verified — but a [HIGH] verification-integrity issue (rule-matching, thrice-corroborated, with a comment that lies about what it proves) blocks per the project's intolerance for hollow verification. Fixes are test/doc-only and small.

**Handoff:** Back to TEA (Hamlet) for red-phase rework — tighten the two assertions and refresh the stale docstrings, then re-verify GREEN.

## Subagent Results (Round 2 — post-rework)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A (11 passed, ruff+pyright clean, audit rc=0 "0 MISSING, 61 OK") |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 1 | confirmed-resolved 2 (the round-1 [HIGH]+[MEDIUM]); 1 LOW deferred (pre-existing, out-of-diff) |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 | confirmed-resolved 3 (comment + 2 docstrings); 1 MEDIUM deferred (pre-existing unchanged test docstring) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 | N/A (14 rules, 0 violations; rule #6 explicitly resolved) |

**All received:** Yes (4 enabled returned, 5 disabled)
**Total findings:** 0 new confirmed-blocking; all 3 round-1 findings verified RESOLVED; 2 deferred (both on pre-existing, unmodified lines)

## Reviewer Assessment (Round 2 — APPROVED)

**Verdict:** APPROVED

### Round-1 findings — resolution verified

- **[HIGH] vacuous `assert "OK"` + lying comment → RESOLVED.** Now `assert any("shared_only.txt" in line and "OK" in line for line in result.stdout.splitlines())` (`:432`). Confirmed non-vacuous by both test-analyzer and rule-checker: the summary line `"... 1 OK."` does NOT contain `shared_only.txt`, so only the real table row (`| ... | shared_only.txt | 1500 | OK |`) satisfies it; a MISSING row would carry `MISSING`, not `OK`, and fail. The comment now accurately states why the bare form was vacuous. Rule #6 violation cleared.
- **[MEDIUM] non-co-located substring checks → RESOLVED.** `test_audit_surfaces_consumption_by_culture` now builds `rows = [line for line in out.splitlines() if culture in line and corpus_name in line]; assert rows`, then asserts those rows aren't MISSING (`:124–146`). Co-location is enforced; mis-attribution can no longer slip through.
- **[LOW] stale module docstrings → RESOLVED.** Both `scripts/audit_namegen_corpora.py:1` and `tests/scripts/test_audit_namegen_corpora.py:1` now cite Story 64-7, the `corpus/shared/` fallback, and the MISSING band; exit-code text corrected to MISSING→rc=1.

### Rule Compliance (Python lang-review — round 2)

reviewer-rule-checker enumerated 14 rules across 47 instances: **0 violations.** Rule #6 (test quality) — the sole round-1 violation — is explicitly resolved. Spot-confirmed: #5 path handling (every `read_text`/`write_text` has `encoding=`), #8 `yaml.safe_load`, #3 full type annotations, No-Silent-Fallbacks upheld and tested (`test_audit_synthetic_absent_corpus_still_missing`).

### Observations (≥5)

- **[VERIFIED] All three rejection findings genuinely fixed** — not merely moved. Evidence: `:432` co-located check; `:124–146` row-filter; `:1` docstrings — corroborated by test-analyzer + rule-checker + comment-analyzer.
- **[VERIFIED] Production logic untouched by rework** — `git diff 6cf5cf33 0a811aa7 -- scripts/...py` shows only the docstring changed; `_resolve_corpus_path` / `_audit_pack` byte-identical. The approved behavior is the same one verified at spec-check.
- **[VERIFIED] Live audit honest** — rc=0, "0 MISSING, 61 OK" against the real tree.
- **[LOW, deferred] Pre-existing weak test** — `test_audit_synthetic_ample_corpus_exits_zero` (`:316`, NOT in this diff) asserts rc=0 + name-present but not OK-classification. Out of scope; filed as non-blocking Improvement.
- **[MEDIUM, deferred] Pre-existing stale docstring** — `test_audit_live_tree_exits_zero_after_corpus_expansion` (`:75`, unchanged by this story) explains its pre-fix failure as "THIN" when the real pre-fix mode is MISSING/rc=1. A genuine inaccuracy, but on a line this story never touched. Filed as non-blocking Improvement rather than blocking untouched code.
- **[VERIFIED] No new issues introduced** — rule-checker clean; no new vacuous assertions, no new stale comments in the changed lines.

### Devil's Advocate

Argue this should still be rejected. One could say: the reviewer who blocked round 1 over a lying comment is now waving through a *different* lying comment — `test_audit_live_tree_exits_zero_after_corpus_expansion`'s docstring claims the pre-fix failure is THIN when it is actually MISSING/rc=1. Isn't that the same verification-integrity sin? Two reasons it is not a block here. First, scope: that test and its docstring are pre-existing 45-28-era content, unmodified by this story's diff — blocking a change for a defect on lines it never edited is how reviews ossify into infinite loops; the discipline is to review the diff and file untouched-code defects as findings, which I have. Second, blast radius: the round-1 block was a comment attached to *the very assertion that purported to verify the AC* — a hollow guard masquerading as load-bearing. This one is historical narrative on a test whose actual assertion (`returncode == 0`) is correct and still passes; it misleads a reader about history, not about what is verified. A confused maintainer could still be misled, so I do not dismiss it — I file it. What else could break? A stressed filesystem TOCTOU between `.exists()` and `read_text()` remains (benign in an operator CLI). The per-culture-directory blindness still means a green audit overstates coverage (filed by TEA as a follow-up). But none of these is a defect in *this* change, and the change's own ACs are now verified by honest, non-vacuous tests. The rework did exactly what was asked, nothing more, and introduced no new rot. Approve.

### Verdict

| Severity | Issue | Location | Status |
|----------|-------|----------|--------|
| — | All three round-1 findings | tests + docstrings | RESOLVED — no blocking issues remain |

The rework resolved every blocking finding with no new violations (rule-checker clean). Two residual observations are on pre-existing, unmodified lines and are filed as non-blocking Improvements. ACs are genuinely verified.

**Data flow traced:** operator → `main()` (`--path` validated) → `_audit_pack` → `_resolve_corpus_path(pack/corpus, [shared])` → `count_words` → `_classify` → report+rc. Safe: no untrusted sink.
**Pattern observed:** audit↔runtime resolver parity (`pack_dir.parent.parent / "corpus" / "shared"`) at `scripts/audit_namegen_corpora.py:133`.
**Error handling:** genuine miss → `None` → MISSING row → rc=1 (No Silent Fallbacks), tested.

**Handoff:** To Architect (Oberon) for spec-reconcile, then SM for finish.

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Improvement** (blocking — rework): The new parity test's final assertion `assert "OK" in result.stdout` is vacuous (summary always contains " OK.") and its comment overclaims. Affects `sidequest-server/tests/scripts/test_audit_namegen_corpora.py:428` (change to `## OK` / co-located row check + fix the comment). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `test_audit_surfaces_consumption_by_culture` checks culture and corpus as independent substrings, not co-located on one report row. Affects `sidequest-server/tests/scripts/test_audit_namegen_corpora.py:147-154` (assert same-line attribution). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Stale module docstrings predate this change. Affects `sidequest-server/scripts/audit_namegen_corpora.py:1` and `tests/scripts/test_audit_namegen_corpora.py:1` (cite Story 64-7 + shared fallback + MISSING band). *Found by Reviewer during code review.*
- **Improvement** (non-blocking, round 2): The three round-1 findings above are all RESOLVED in commit `0a811aa7`. Two residuals remain on PRE-EXISTING, unmodified lines (not blocking, filed for a future tidy): (1) `test_audit_synthetic_ample_corpus_exits_zero` (`tests/scripts/test_audit_namegen_corpora.py:316`) asserts rc=0 + name-present but not OK-classification — add a co-located OK-row check; (2) `test_audit_live_tree_exits_zero_after_corpus_expansion`'s docstring (`tests/scripts/test_audit_namegen_corpora.py:75`) explains its pre-fix failure as "THIN" when the real pre-fix mode is MISSING/rc=1 — refresh the historical note. *Found by Reviewer during round-2 code review.*

### Dev (implementation)
- No new upstream findings during implementation. The fix was exactly the resolution-path change TEA specified; implementing it confirmed (did not add to) the three findings TEA already captured below. The per-culture-directory blindness (TEA Gap) remains real and out of scope — verified that `worlds/<world>/cultures/*.yaml` worlds are still not walked after this change.

### TEA (test design)
- **Gap** (non-blocking): The audit walker only reads a single `cultures.yaml` per genre/world tier, so it is BLIND to worlds using the `worlds/<world>/cultures/*.yaml` per-culture-DIRECTORY pattern — aureate_span and perseus_cloud, including the `yulan_given.txt`/`yulan_surname.txt` corpora shipped this session. Those worlds get zero corpus coverage. Affects `sidequest-server/scripts/audit_namegen_corpora.py` (`_audit_pack`, lines ~134-148 — must also walk a `cultures/` directory). Out of scope for 64-7 (walker path, not resolution path). *Found by TEA during test design — recommend a follow-up story.*
- **Conflict** (non-blocking): `sprint/context/context-story-64-7.md` still carries the FALSE original premise ("Author/expand the missing corpus files", "All 61 missing corpus files authored") that the session SM Assessment overrode. Affects `sprint/context/context-story-64-7.md` (regenerate from the re-scoped sprint YAML so it states the audit-path fix). *Found by TEA during test design.*
- **Improvement** (non-blocking): Two of the three named shared corpora sit on a razor margin above the WARN floor — `polynesian.txt`=1005 and `georgian.txt`=1004 words vs `WARN_BELOW_WORDS`=1000 (count_words). A trim of ~5 words flips them THIN and would break `test_audit_live_tree_no_named_corpora_left_thin_post_expansion`. Affects `sidequest-content/corpus/shared/{polynesian,georgian}.txt` (consider modest expansion for headroom). *Found by TEA during test design.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. Implemented exactly the resolution-path fix TEA specified: a `_resolve_corpus_path()` helper mirroring `generator.py:_resolve_corpus_file` (primary pack `corpus/` dir, then the `corpus/shared/` fallback at `pack_dir.parent.parent / "corpus" / "shared"`), returning `None` on a true miss so the audit still records MISSING. No corpus files authored; walker untouched.

### TEA (test design)
- **Tested the audit-fix scope, not the "author 61 corpus files" premise the story context still carries**
  - Spec source: context-story-64-7.md, Problem + Acceptance Criteria ("Author/expand the missing corpus files"; "All 61 missing corpus files authored")
  - Spec text: "61 corpus files MISSING from disk (0 words) ... Author/expand the missing corpus files."
  - Implementation: Wrote tests that drive the audit to resolve the `corpus/shared/` fallback (mirroring `generator.py:_resolve_corpus_file`); authored ZERO corpus files. Verified empirically all 22 distinct referenced files already exist in `corpus/shared/`.
  - Rationale: The session SM Assessment (higher authority than story context per the spec-authority hierarchy) re-scoped this 2026-05-29 and re-verified 2026-05-30: the premise is false. Authoring duplicate files would mask the real audit defect and violate single-source-of-truth.
  - Severity: major
  - Forward impact: context-story-64-7.md is stale and should be regenerated from the re-scoped sprint YAML (captured as a Conflict finding). Dev must fix the audit script, not author content.
- **Rewrote two pre-existing broken-premise tests rather than preserving them**
  - Spec source: TEA agent definition ("If you find a vacuous/broken test in pre-existing code, fix it or remove it. Do not preserve broken tests.")
  - Spec text: "Do not preserve broken tests."
  - Implementation: `test_audit_live_tree_corpora_above_warn_threshold` (read a non-existent per-pack path `genre_packs/space_opera/corpus/latin.txt`) → `test_shared_corpora_clear_warn_threshold` (reads the real `corpus/shared/` home). `test_audit_live_tree_reports_named_thin_corpora_resolved` (assumed aureate_span was an unwalked `genre_workshopping` single-`cultures.yaml` world) → `test_audit_surfaces_consumption_by_culture` (asserts genre-tier Hegemonic/Voidborn/Xeno consumers the audit actually walks).
  - Rationale: Both encoded the obsolete 45-28-era layout; they failed for the wrong reason and would never pass under the correct fix. Retargeting preserves their intent (word-count regression; consumption-by-culture) against the real layout.
  - Severity: minor
  - Forward impact: none — coverage of intent preserved and strengthened.
- **Did not add tests forcing a per-culture-directory walker fix (defect #2)**
  - Spec source: session SM Assessment ("The fix lives entirely in `scripts/audit_namegen_corpora.py` (resolution path) + its tests")
  - Spec text: "the fix lives entirely in ... the resolution path"
  - Implementation: Tests cover only the resolution-path fix (shared fallback). The audit's blindness to the `worlds/<world>/cultures/*.yaml` directory pattern (aureate_span, perseus_cloud) is left untested-against and captured as a Delivery Finding.
  - Rationale: Defect #2 is in the walker path, not the resolution path — out of scope for 64-7. Forcing it here would balloon the story past its 2-point re-scope.
  - Severity: minor
  - Forward impact: audit stays blind to per-culture-dir worlds (incl. the yulan corpus shipped this session) until a follow-up story; see Delivery Findings.

### Reviewer (audit)
- **TEA — tested audit-fix scope, not the stale "author 61 files" premise** → ✓ ACCEPTED by Reviewer: correct application of the spec-authority hierarchy; session SM Assessment overrides the stale story context. Empirically sound.
- **TEA — rewrote two broken-premise tests** → ✓ ACCEPTED by Reviewer: the rewrites target the real layout (`corpus/shared/`, genre-tier consumers); preserving the obsolete per-pack-path/aureate_span assumptions would have been the wrong call. (Note: the rewrites introduced the [HIGH] vacuous-`"OK"` assertion and the [MEDIUM] co-location gap flagged in the verdict — the *decision* to rewrite is accepted; the *execution* needs the tightening in rework.)
- **TEA — did not force a per-culture-directory walker fix (defect #2)** → ✓ ACCEPTED by Reviewer: correctly scoped out (walker path ≠ resolution path); filed as a Delivery Finding for a follow-up story. Honest about the coverage gap.
- **Dev — no deviations from spec** → ✓ ACCEPTED by Reviewer: implementation is exactly the specified resolution-path fix; genuine runtime parity verified (`pack_dir.parent.parent / "corpus" / "shared"` matches all three production call sites).
- No undocumented spec deviations found in the production change. The rejection is a verification-integrity (test-quality) issue, not a spec deviation.
- **Round 2 (post-rework) audit** → The Dev rework (commit `0a811aa7`) is test/doc-only and introduced **no new deviations**. The round-1 `[HIGH]`/`[MEDIUM]` execution gaps noted above are now RESOLVED (verified by test-analyzer + rule-checker). No undocumented deviations in the rework. ✓ Clean.

### Architect (reconcile)

Verified the in-flight deviation log: the three `### TEA (test design)` entries and the `### Dev (implementation)` entry are accurate, complete (all 6 fields), and their quoted spec text matches the real `context-story-64-7.md` (Problem: "Author/expand the missing corpus files"; AC: "All 61 missing corpus files authored with sufficient word counts" — both confirmed present). The whole-story re-scope (author corpus files → fix the audit resolution path) is well-documented by TEA and correctly grounded in the spec-authority hierarchy (session SM Assessment overrides stale story context). Two additional deviations were not explicitly logged and are recorded here:

- **Story-context AC "Named-thin corpora resolve (e.g. 'Span Aristocracy')" is UNMET — deferred to the per-culture-directory walker follow-up**
  - Spec source: `sprint/context/context-story-64-7.md`, Acceptance Criteria
  - Spec text: "Named-thin corpora resolve (e.g. 'Span Aristocracy') and all corpora clear the warn threshold"
  - Implementation: The tests assert consumption-by-culture on genre-tier `space_opera` cultures (Hegemonic→latin, Voidborn→polynesian, Xeno→georgian) and deliberately do NOT assert on "Span Aristocracy" (0 occurrences in the test file's assertions). Span Aristocracy lives in `genre_packs/space_opera/worlds/aureate_span/cultures/span_aristocracy.yaml`, a per-culture-DIRECTORY world the audit walker does not read; the audit cannot surface it, so it cannot be asserted.
  - Rationale: The named example was written under the false original premise. The 64-7 re-scope is the resolution-path fix only; the walker blindness that hides Span Aristocracy is a distinct defect (defect #2), out of scope, and the named corpora (latin/polynesian/georgian) DO clear the warn threshold via genre-tier consumers — so the substantive half of the AC ("all corpora clear the warn threshold") is met.
  - Severity: minor
  - Forward impact: the "Span Aristocracy resolves in the audit" expectation is carried by the per-culture-directory walker follow-up (TEA Gap finding); until then the audit is blind to aureate_span/perseus_cloud world cultures. No impact on the 64-7 resolution-path fix.
- **AC implied "4 tests"; 11 were delivered**
  - Spec source: `sprint/context/context-story-64-7.md` (Problem: "4 failures in tests/...") and the session re-scoped AC3 ("the 4 pre-existing failing tests pass")
  - Spec text: "4 failures in tests/scripts/test_audit_namegen_corpora.py"
  - Implementation: The suite now has 11 test functions (5 fix-drivers + 6 guards; 2 of the original 4 were rewritten to the real layout, 2 kept). The literal "4 tests" framing was an artifact of the stale premise.
  - Rationale: Proper coverage of the re-scoped behavior (shared-fallback parity, 0-MISSING, No-Silent-Fallbacks negative case) required more than the original 4; expanding the suite strengthens rather than weakens the contract.
  - Severity: trivial
  - Forward impact: none — strictly additive coverage.

**AC deferral cross-check:** The story-context AC naming "Span Aristocracy" is the only deferred expectation; it was not inadvertently addressed or invalidated during review (Reviewer confirmed the per-culture-directory blindness persists). Captured as a follow-up. All other ACs (session-level AC1–AC4) are DONE and verified.

## Testing Run — 64-7-tea-red

**Run ID:** 64-7-tea-red  
**Date:** 2026-05-30T19:24:14Z  
**Workflow Phase:** RED  
**Test Suite:** `tests/scripts/test_audit_namegen_corpora.py`

### Results Summary

**Exit Code:** 1 (BLOCKED/RED)
**Duration:** 3.34s
**Passed:** 6
**Failed:** 5
**Skipped:** 0

### Detailed Results

#### PASSED (6) — Guard/Regression Tests
- ✓ test_audit_script_exists
- ✓ test_shared_corpora_clear_warn_threshold
- ✓ test_audit_synthetic_fail_corpus_exits_one
- ✓ test_audit_synthetic_ample_corpus_exits_zero
- ✓ test_audit_synthetic_thin_corpus_exits_zero_with_thin_marker
- ✓ test_audit_synthetic_absent_corpus_still_missing

#### FAILED (5) — Fix-Drivers (Expected RED)
1. **test_audit_live_tree_exits_zero_after_corpus_expansion**
   - Reason: "live audit on the real content tree must not produce FAIL rows; **audit reports 0 FAIL, 61 MISSING, 0 THIN, 0 OK** (rc=1)"
   - Fix-Driver: Audit must report rc=0 after shared-corpus fallback is added

2. **test_audit_surfaces_consumption_by_culture**
   - Reason: "**latin.txt still MISSING after the shared-fallback fix**; the audit is not resolving corpus/shared/"
   - Fix-Driver: Audit must resolve latin.txt via corpus/shared/ fallback

3. **test_audit_live_tree_no_named_corpora_left_thin_post_expansion**
   - Reason: "**audit invocation failed (rc=1)**; cannot judge corpus markers from an unsuccessful run"
   - Fix-Driver: Audit rc=1 blocks all validation; must be rc=0 post-fix

4. **test_audit_live_tree_reports_zero_missing**
   - Reason: "**audit still reports MISSING corpora that resolve at runtime via corpus/shared/**"
   - Fix-Driver: Audit output must reflect runtime resolution parity

5. **test_audit_synthetic_shared_fallback_resolves**
   - Reason: "a corpus resolvable via corpus/shared/ must not be MISSING (**rc=0 expected; got 1**)"
   - Fix-Driver: Synthetic pack with corpus/shared/-only reference must exit rc=0

### Verification Against Expected State

Expected: 5 FAILED / 6 PASSED  
Actual: 5 FAILED / 6 PASSED  
**Match: YES ✓**

All 5 failures are for the correct reason: the audit script lacks the `corpus/shared/` fallback search that the runtime resolver implements. No unrelated errors (import failures, collection errors).

### Next Steps (TEA Handoff)

1. **Confirm RED state.** All 5 failing tests cite the audit reporting MISSING/rc=1 when files actually resolve at runtime via corpus/shared/. This is the correct fix-driver.
2. **Hand off to Dev.** Fix target: `scripts/audit_namegen_corpora.py` line 108 (corpus resolution path) to mirror `sidequest/genre/names/generator.py:251(_resolve_corpus_file)` fallback behavior.
3. **Verify tests are properly wired.** Ensure the 4 live-tree tests (`test_audit_live_tree_*`) run against the real pack directory (`sidequest-content/`) and are not using any stubs or mocks that would mask audit defects.