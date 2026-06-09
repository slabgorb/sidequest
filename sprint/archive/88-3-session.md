---
story_id: "88-3"
jira_key: ""
epic: "88"
workflow: "tdd"
---
# Story 88-3: WN capability-gate consolidation sweep

> **Note:** This session file was reconstructed by Dev (2026-06-09) after the
> `testing-runner` subagent's session-cache write clobbered it (known hazard:
> `feedback_testing_runner_clobbers_session`). All assessments below are faithful
> restorations from the working transcript.

## Story Details
- **ID:** 88-3
- **Epic:** 88 (Ashes Without Number — mutant_wasteland ruleset port)
- **Type:** Refactor
- **Points:** 2
- **Workflow:** tdd
- **Repos:** sidequest-server (github-flow, develop branch)
- **Stack Parent:** 88-2 (completed 2026-06-05)

## Story Context

### Specification
ADR-117, §Amendments, "2026-06-05 — Capability gates, not slug strings (the fifth-module lesson)" (line 175+). Design docs: `docs/superpowers/specs/2026-06-05-ashes-without-number-mutant-wasteland-design.md` §11 (Architect Addendum).

### The Work (as originally scoped)
AC1: clarify three docstrings to "CWN-family (cwn/awn)". AC2: AWN capability-gate lock-in tests. AC3: no regressions. **Guardrail:** do NOT convert genuinely slug-specific gates (the hacking ladder `dice.py:344`, `confrontation.py:336` — CWN-only, correct as-is). Full original context preserved in git history of `sprint/context/context-story-88-3.md`.

## Sm Assessment

**Routing:** Standard TDD phased workflow, single repo (sidequest-server). Deps 88-1 + 88-2 both DONE; merge gate clear.

**Re-scope (user decision, 2026-06-09):** Measured the premise before handoff (epic-59/61 stale-premise lesson). The story as titled — "convert remaining slug-string sites to capability gates" — is **already done in code**. All four ADR-117 "Known debt" sites use `isinstance` today (`builder.py:96`, `stabilize_mortal_injury.py:116`, `adjust_system_strain.py:102`, `downed_seam.py` via `run_cwn_wwn_downed_seam`). The only live `ruleset == "cwn"` sites are the hacking ladder — genuinely slug-specific, **ADR says keep**. The ADR-117 "Known debt" paragraph is STALE (sweep landed inline in 88-1/88-2). Keith chose **"Re-scope & lock it in"**: deliver the residual — AWN lock-in tests (AC2) + docstring cleanup (AC1) + no-regress (AC3).

**Framing for TEA:** gates already `isinstance`, so AC2 tests pass on green code (lock-in, not expect-RED). Tells: (1) a *failing* AC2 test = real regression; (2) verify OTEL span names exist before asserting.

**ADR-117 close-out:** marking the "Known debt" paragraph RESOLVED is an ORCHESTRATOR-repo (main) docs edit — SM handles it as a docs chore at finish, keeping 88-3 server-only.

## TEA Assessment

**Phase:** finish (test design)
**Tests Required:** No — **chore bypass** (documentation update + refactoring with existing, verified-green coverage).

**Reason (measured):** The AWN lock-in coverage AC2 asks for **already exists, delivered by Story 88-1** (test docstrings cite "Story 88-1 Item 5/7"). Ran all four on develop — **all GREEN (0.74s)**:

| Seam | Existing test (node id) | Result |
|------|-------------------------|--------|
| 2 — Mortal Injury @0 HP | `tests/server/test_awn_combat_dispatch.py::test_awn_downed_target_gets_mortal_injury` | PASSED |
| 3 — System Strain chargen | `tests/game/test_builder_seeds_strain.py::TestSeedSystemStrainHelper::test_awn_returns_pool_maxed_at_con_score` (+max-1 floor, +swn-returns-none regression) | PASSED |
| 4 — `adjust_system_strain` tool | `tests/agents/tools/test_adjust_system_strain_tool.py::test_awn_pack_applies_strain` | PASSED |
| 5 — `stabilize_mortal_injury` tool | `tests/agents/tools/test_stabilize_mortal_injury_tool.py::test_awn_pack_can_stabilize` | PASSED |

Meaningful (real `cwn.*` spans + state/status mutation, persisted), not skipped. `cwn.shock.applied` awn path also covered. Writing duplicates = Don't-Reinvent violation. SM tell #1 did not trigger (all green).

**Span-name tell resolved:** an `awn` pack emits `cwn.*` spans (no `awn.py` span module; `AwnRulesetModule(CwnRulesetModule)` overrides nothing). Tools enrich the dispatch-layer `tool.write.{adjust_system_strain,stabilize_mortal_injury}` span and delegate `cwn.system_strain.delta` to the engine.

**Rule Coverage:** python.md #6 (Test Quality) is the load-bearing check — and the reason for bypass: duplicate AWN tests = vacuous-by-redundancy. No new tests → no new vacuous assertions. 88-1 tests satisfy the wiring requirement (real dispatch/builder/tool drive + span/state asserts).

**Handoff:** To Dev (GREEN) for **AC1 only** (3 docstrings). AC2+AC3 already satisfied — Dev must NOT duplicate AWN tests.

## Dev Assessment

**Phase:** finish (implementation)
**Commit:** `613279be` — docs(88-3): clarify CWN-family (cwn/awn) scope in tool/seam docstring summaries (3 files, +3/-3, doc-only).

**What I did (AC1 only):** three summary/header-line clarifications, nothing else:
- `agents/tools/stabilize_mortal_injury.py:1` — "CWN Mortal Injury" → "CWN-family (cwn/awn) Mortal Injury"
- `agents/tools/adjust_system_strain.py:1` — "CWN System Strain" → "CWN-family (cwn/awn) System Strain"
- `server/dispatch/downed_seam.py:1` — "Shared CWN/WWN 0-HP downed seam" → "Shared CWN-family/WWN 0-HP downed seam — cwn, awn, wwn"

**Scope restraint (minimalist discipline):** Did NOT touch the guard docstrings (`stabilize` 23-26, `adjust` 15-18) or the `downed_seam` module-body/gate comment — 88-1 had already made all of those awn-accurate ("cwn or its awn subclass" / "covers cwn, wwn, AND awn"). Did NOT write/duplicate AWN tests (AC2 green). Changed NO code/logic/gate. Hacking-ladder slug-strings left intact per the guardrail.

**Verification (evidence before claims):**
- `ruff check` (3 files) → All checks passed. `ruff format --check` → already formatted. (line-length 100; E501 not selected, so pre-existing long docstring lines remain conformant.)
- `pytest -n0` over the three changed modules' suites → **21 passed, 0 failed, 0 skipped (0.99s)**. No regression.

**AC status:** AC1 ✅ (this commit) · AC2 ✅ (88-1 coverage, TEA-verified green) · AC3 ✅ (21 green).

**Handoff:** To Reviewer. PR diff is intentionally tiny (3 doc lines) — the story's substance was subsumed by 88-1; see TEA Assessment + Delivery Findings for the measured rationale. ADR-117 "Known debt → resolved" close-out remains the SM docs chore at finish (orchestrator repo, out of this server PR's scope).

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-09T02:22:00Z | 2026-06-09T06:46:14Z | 4h 24m |
| red | 2026-06-09T06:46:14Z | 2026-06-09 (TEA chore-bypass) | — |
| green | 2026-06-09 | 2026-06-09T07:00:02Z | 7h |
| review | 2026-06-09T07:00:02Z | 2026-06-09T07:05:11Z | 5m 9s |
| finish | 2026-06-09T07:05:11Z | - | - |

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The story context's AC2 ("add RED tests proving AWN capability gates fire") is already satisfied — Story 88-1 shipped all four AWN gate tests and they pass green on develop. Affects the story scope itself (no `tests/` changes needed). The context was authored from the ADR's stale "Known debt" framing without checking that 88-1's RED tests already cover the awn paths. *Found by TEA during test design.*
- **Improvement** (non-blocking): ADR-117 §Amendments "Known debt" paragraph is stale — it describes the four slug-string sites as outstanding when the capability-gate conversion (and its awn test coverage) landed inline in 88-1/88-2. Affects `docs/adr/117-pluggable-ruleset-module-system.md` (orchestrator repo) — mark the debt RESOLVED, citing the isinstance sites + the four green awn tests. Tracked as the SM finish-time docs chore (out of this server story's repo scope). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): AC1 was narrower than the story context implied — the guard docstrings (stabilize 23-26, adjust 15-18) and the entire `downed_seam.py` module-body/gate comment were ALREADY awn-accurate from 88-1. Only the three top summary/header lines were stale. Affects nothing further (fixed in `613279be`); recorded so Reviewer understands why the diff is 3 lines, not the broader doc rewrite AC1 suggested. *Found by Dev during implementation.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **No new RED tests written (chore bypass) despite AC2 specifying "add RED tests"**
  - Spec source: context-story-88-3.md, AC2 ("RED tests prove AWN confrontations fire the capability gates")
  - Spec text: "Add test coverage proving the seams activate for AWN: Mortal Injury declaration on 0 HP, System Strain pool seeding at chargen, System Strain adjustments via tool, Stabilize Mortal Injury via tool."
  - Implementation: No tests authored. Verified the four named behaviors are already covered by green Story-88-1 tests (run logged in TEA Assessment, all PASSED) and bypassed per the TEA Chore-Bypass criteria (documentation update + refactoring with existing coverage).
  - Rationale: Authoring the specified tests would duplicate existing, passing coverage — a Don't-Reinvent / vacuous-redundancy violation. The genuine residual is AC1 (docstrings), doc-only, needs no test.
  - Severity: minor
  - Forward impact: Dev's GREEN phase is AC1 docstrings only; no new test suite to maintain. If a Reviewer expects net-new tests, this deviation is the rationale.

### Dev (implementation)
- **AC1 scope narrowed to three summary lines (guard/body docstrings were already awn-accurate)**
  - Spec source: context-story-88-3.md, AC1 ("Docstrings updated for CWN-family capability gates" — named lines 23-25 / 15-18 / 15-16 across the three files)
  - Spec text: "Update docstrings in three files to reflect that the capability gates cover CWN/AWN (not just CWN)."
  - Implementation: Edited only line 1 (the summary/header) of each of the three files. The guard descriptions (stabilize 23-26, adjust 15-18) and the `downed_seam` body + gate comment already explicitly named awn (delivered by 88-1), so editing them would be a no-op churn.
  - Rationale: Minimalist discipline — only change what is genuinely inaccurate. The stale-at-a-glance bits were the top summary lines, not the already-corrected guard/body docstrings.
  - Severity: minor
  - Forward impact: none — the docstrings are now consistently awn-accurate from summary through guards.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 30 tests green, ruff check+format pass, 0 code smells |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings (domain self-covered below — this is the doc-only diff's relevant lens) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict: APPROVE** (doc-only; no Critical/High findings)

Diff scope independently verified via `git diff develop...HEAD`: exactly three module-docstring summary lines, +1/-1 each, across `adjust_system_strain.py`, `stabilize_mortal_injury.py`, `downed_seam.py`. No code, logic, gate, or test changes. The story's code+test substance was legitimately subsumed by 88-1 (I confirmed this, not just trusted it — see observations).

### Observations
- [VERIFIED] Diff is doc-only — evidence: `git diff --numstat develop...HEAD` = `1 1` on each of the 3 files; every changed line is the module docstring's first line. No runtime surface touched.
- [VERIFIED] New docstrings are ACCURATE against the real gates — evidence: `adjust_system_strain.py:102` / `stabilize_mortal_injury.py:116` gate `isinstance(module, CwnRulesetModule)` (covers awn), and `downed_seam.py` gates `isinstance(pack.rules.ruleset_config(), (CwnConfig, WwnConfig))`. The new "CWN-family (cwn/awn)" and "CWN-family/WWN — cwn, awn, wwn" wording matches the code; the downed_seam phrasing correctly keeps wwn as a SEPARATE config family (it is `WwnConfig`, not a `CwnConfig` subclass), consistent with the already-accurate module body (lines 15-20).
- [VERIFIED] AC2 lock-in coverage genuinely exists and passes — evidence: I independently ran the four named AWN tests + the three changed-module suites via direct pytest → 22 passed; preflight independently ran 30 → 0 failed. Not a pencil-whipped claim.
- [VERIFIED] Guardrail respected (hacking-ladder slug-strings untouched) — evidence: diff contains no `dice.py` or `confrontation.py`; the CWN-only `ruleset == "cwn" and cdef.category == "hacking"` gates remain as-is per the ADR.
- [VERIFIED] No NEW staleness introduced (comment-analyzer lens, self-covered since disabled) — evidence: the three new summary lines are consistent with each file's own guard/body docstrings, which 88-1 had already made awn-accurate. No docstring now contradicts another or the code.
- [LOW] `downed_seam.py:1` is now 113 chars — over the 100 line-length config — but ruff E501 is not in the selected rule set (the pre-existing line was already long), so `ruff check` passes. Cosmetic only; not blocking.

### Rule Compliance
Applicable rules enumerated against the diff (doc-only → most code rules are N/A):
- python.md #4 (logging f-strings): N/A — no logging lines changed.
- python.md #6 (test quality / vacuous assertions): N/A — no tests changed; TEA's chore-bypass (no duplicate tests) is the correct anti-vacuous outcome, and existing 88-1 tests assert real spans+state.
- python.md #1,2,3,5,7,8,9,11,12 (exceptions/mutable-defaults/types/paths/resources/deser/async/input-validation/deps): N/A — no code changed.
- CLAUDE.md "No Source-Text Wiring Tests" / "No Silent Fallbacks" / "Don't Reinvent": COMPLIANT — the bypass explicitly avoided duplicating coverage (Don't Reinvent); the gates fail loud (the docstrings document the ValueError guards).
- SOUL.md: no player-facing or agency surface touched. N/A.

### Devil's Advocate
Could this 3-line doc change be hiding a problem, or could the whole story be a rubber-stamped no-op that should never have shipped? Three angles. (1) *Is the diff really doc-only, or did a code change sneak in under a "docs" label?* I didn't trust the label — I ran `git diff` myself and read every changed line; all three are the docstring first line, numstat 1/1, no hunks touch executable code. A malicious or careless author could have bundled a logic tweak; this one did not. (2) *Are the new docstrings actively WRONG — i.e., do the gates NOT actually cover awn, making the docstring a lie that misleads a future maintainer?* This is the real risk of a doc-accuracy story: replacing one inaccuracy with another. I checked the gate sites directly: `isinstance(module, CwnRulesetModule)` and `isinstance(cfg, (CwnConfig, WwnConfig))` — `AwnConfig`/`AwnRulesetModule` subclass the Cwn types, so the gates demonstrably fire for awn, and the four green AWN tests prove it at runtime. The docstrings now tell the truth. (3) *Is the story a no-op that wastes a slot — should the pipeline have closed it instead of shipping 3 lines?* The honest answer: the code and tests were already done by 88-1, and the user was explicitly told this and chose "lock it in." The residual — three skim-misleading summary lines — IS a genuine (if small) accuracy defect: a maintainer reading only the top line of `stabilize_mortal_injury.py` would have believed it cwn-only and might wrongly "fix" awn support that already works. Correcting that is legitimate. What a confused user could still misread: "CWN-family/WWN" might be parsed as "CWN family of WWN" — but the trailing "— cwn, awn, wwn" disambiguates. What's genuinely left undone: the ADR-117 "Known debt" paragraph still falsely lists this debt as OPEN; if SM forgets the finish-time close-out, the project's most authoritative doc stays wrong while the code docstrings are right — a half-finished accuracy story. That is the one thing I will hold SM's feet to (see below). Nothing here rises to Critical/High.

### Deviation Audit
- **TEA: No new RED tests (chore bypass)** → ✓ ACCEPTED by Reviewer: I independently confirmed the four AWN behaviors are covered by green 88-1 tests (22→30 passing across two runs); writing duplicates would be Don't-Reinvent churn. Sound.
- **Dev: AC1 scope narrowed to three summary lines** → ✓ ACCEPTED by Reviewer: I read the guard docstrings (stabilize 23-26, adjust 15-18) and the downed_seam body/gate comment — all already name awn explicitly. Editing them would be no-op churn. Minimalist restraint was correct.

### Finish-gate note for SM (non-blocking on this PR, but REQUIRED to actually close the story's intent)
This story's whole purpose is doc accuracy. The code docstrings are now correct, but the **ADR-117 §Amendments "Known debt" paragraph still lists the four slug-string sites as outstanding** — which is now the only remaining inaccuracy. SM committed (in the SM Assessment) to making that orchestrator-repo edit at finish. **Do not archive 88-3 without it**, or the story half-delivers (code docstrings fixed, authoritative ADR still wrong).

**Handoff:** To SM (Hawkeye) for finish — create+merge the server PR, then execute the ADR-117 "Known debt → resolved" close-out in the orchestrator repo before archiving.