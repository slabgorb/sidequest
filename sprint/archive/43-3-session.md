---
story_id: "43-3"
jira_key: null
epic: "43"
workflow: "trivial"
---
# Story 43-3: Archive LoRA training scripts, specs, plans, and trained .safetensors artifacts — cancelled per ADR-070 supersession

## Story Details
- **ID:** 43-3
- **Jira Key:** (pending creation)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-27T17:01:26Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T00:00:00Z | 2026-04-27T16:55:04Z | 16h 55m |
| implement | 2026-04-27T16:55:04Z | 2026-04-27T16:57:58Z | 2m 54s |
| review | 2026-04-27T16:57:58Z | 2026-04-27T17:01:26Z | 3m 28s |
| finish | 2026-04-27T17:01:26Z | - | - |

## Sm Assessment

Trivial 1pt archival. Targets:
- `tests/lora/*` (4 files, 347 lines total) — orphaned: import `scripts.lora.remap_mlx_to_mflux` and `scripts.lora.train` which no longer exist on disk.
- `docs/superpowers/specs/2026-04-20-lora-pipeline-design.md`
- `docs/superpowers/plans/2026-04-20-lora-pipeline.md`
- No committed `.safetensors` under genre_packs (verified via `find`).

Approach: move docs to `docs/superpowers/{specs,plans}/superseded/` (new convention); `git rm` the orphaned tests since the modules they exercise are gone (cannot run, dead). Skip ADRs (032/083/084) — historical record convention. Skip `.claude/commands/sq-lora.md` — that's a slash command, not training infra.

Hand to Dev.

## Dev Assessment

**Phase:** finish
**Status:** Complete — 1 commit on orchestrator. 24 of 25 orchestrator tests pass; 1 pre-existing failure unrelated to this story.

**Implementation:**
- `git mv docs/superpowers/specs/2026-04-20-lora-pipeline-design.md → .../specs/superseded/`
- `git mv docs/superpowers/plans/2026-04-20-lora-pipeline.md → .../plans/superseded/`
- `git rm -r tests/lora/` (4 test files + `__init__.py`, 347 lines total — orphaned since `scripts/lora/` was deleted)
- `pyproject.toml`: removed dead `torch>=2.0` and `safetensors>=0.4` deps (no remaining importers in scripts/ or tests/), updated description to drop "LoRA pipeline" mention, tidied hatch-build docstring.
- `uv.lock`: regenerated, removes torch/sympy/triton/setuptools/typing-extensions chains.
- No committed `.safetensors` files exist under `sidequest-content/genre_packs/` (verified via `find`); nothing to delete there.
- `~/lora-runs/` is user-local per the story description; not in repo — out of scope.
- ADRs 032/083/084 left in place per ADR convention (historical record).
- `.claude/commands/sq-lora.md` left in place — slash command, not training infrastructure (and may still be referenced).

**Test verification:**
- `uv run pytest` → 24 passed, 1 failed (`test_resolve_lora_args_resolved_loras_used_directly` in `tests/test_render_common.py`). Verified pre-existing on develop via `git stash` round-trip.

**Branch:** `feat/43-3-archive-lora-pipeline-scripts-specs` (1 commit, orchestrator only).

**Handoff:** To Reviewer.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 pre-existing test failure (unchanged from main); 12 pre-existing lint (none in diff) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | clean | 0 — confirmed no orphaned conftest fixtures or remaining `scripts.lora.X` imports | N/A |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 (low: pyproject description underrepresents scripts/) | confirmed 1 (fixed) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 violations across 18 rules (47 instances) | N/A |

**All received:** Yes (4 active, 5 skipped per settings)
**Total findings:** 1 confirmed and fixed; 0 dismissed; 0 deferred

### Confirmed and fixed during review
- `[DOC]` `pyproject.toml` description "POI gen, music gen, etc." underrepresented what scripts/ actually contains (playtest, migrations, ADR tooling, multi-image-gen). Fixed in amended commit: now reads "image gen, playtest, migrations, ADR tooling, etc."

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** N/A — pure archival, no production code. Two .md files moved to `superseded/` subdirs (rename-only), 5 orphaned test files (`tests/lora/`) deleted (their target modules `scripts/lora/*` were removed in a prior story), 2 dead deps removed from pyproject.toml (`torch`, `safetensors` — verified no remaining importers), uv.lock regenerated. Net −815 lines.

**Pattern observed:** Honest archival. Files moved to a clear `superseded/` namespace (new convention but obvious; matches the project's `sprint/archive/` pattern). Orphaned tests deleted rather than left to fail at import time. Dead deps removed once they had no consumers.

**Error handling:** N/A — no logic introduced.

### Findings table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| `[LOW] [DOC]` | pyproject description underrepresented scripts/ contents (only mentioned POI + music). | `pyproject.toml:4` | **Fixed in-flight** — description widened to "image gen, playtest, migrations, ADR tooling, etc." |
| `[NOTE] [TEST]` | reviewer-test-analyzer returned clean: confirmed no orphaned conftest fixtures, no remaining `scripts.lora.X` imports anywhere. | `tests/lora/*` (deleted) + sibling test trees | None — verified by subagent. |
| `[NOTE] [RULE]` | reviewer-rule-checker returned clean across 18 rules (47 instances): pyproject dep hygiene, import hygiene, no silent fallbacks, no stubbing, no orphaned wiring tests. | `pyproject.toml`, deleted `tests/lora/*` | None — verified by subagent. |

### Rule Compliance

Rule-checker enumerated 18 rules across 47 instances; **zero violations**. Pure archival diff, no new code paths to evaluate. Pre-existing 12 ruff errors and 1 test failure (`test_resolve_lora_args_resolved_loras_used_directly`) confirmed unrelated to this branch — both existed on `main` before this work; the test failure is in `scripts/render_common.py`'s LoRA composition logic (Dev's flagged Improvement finding, future story candidate).

### Devil's Advocate

The biggest argument against this archival is that `scripts/render_common.py` *still* contains substantial LoRA composition logic (LORA_DIR, compose_lora_stack, _validate_lora_entry, resolve_lora_args), and `tests/test_render_common.py` has a failing test for it. By only archiving the `tests/lora/` tree and the training-pipeline docs, we're leaving the render-pipeline LoRA infrastructure in a broken-test state. Counter: 43-3's scope is explicitly *training scripts/specs/artifacts*, not render-pipeline composition. Dev correctly logged the render_common.py infrastructure as a non-blocking Improvement finding for Epic 43 follow-up. Pulling that into 43-3 would expand scope considerably (new function deletions, branching test cases, possibly cross-repo render pipeline updates). The 1pt archival is bounded; the render_common cleanup deserves its own story. Second argument: the moved superseded docs reference paths that no longer exist (`scripts/lora/remap_mlx_to_mflux.py`, etc.) and a wrong username/repo path inside the plan file. Counter: superseded documents are historical record by design — they describe what *was* planned, not what currently exists. Updating them in-place would defeat the purpose of archiving them. Third argument: `safetensors` and `torch` deps are gone but `numpy` remains, even though no script in the diff uses it for LoRA-tensor work. Counter: numpy is used by `scripts/render_common.py` (PIL alternatives, image diff helpers in render path) — out of scope to verify exhaustively, and the dep is widely-used enough to keep without strict justification. The diff does what its name says, no more.

**Handoff:** To Vizzini (SM) for finish.

## Delivery Findings

### Dev (implementation)
- **Improvement** (non-blocking): `scripts/render_common.py` contains substantial LoRA composition logic (LORA_DIR constant, `compose_lora_stack`, `_validate_lora_entry`, `resolve_lora_args` with branching). Affects `scripts/render_common.py` and the failing pre-existing test `tests/test_render_common.py::test_resolve_lora_args_resolved_loras_used_directly`. Adjacent to Epic 43 but out of 43-3's archive scope (which targets training scripts/specs, not render-pipeline infra). Would make a clean follow-up story under Epic 43 to remove the LoRA composition path from the orchestrator render scripts. *Found by Dev during 43-3 implementation.*
- **Improvement** (non-blocking): `.claude/commands/sq-lora.md` slash command (~19KB) likely needs review — if no LoRA pipeline exists to invoke, the command may be dead. Out of 43-3's scope (slash commands are framework infra, not training artifacts). *Found by Dev during 43-3 implementation.*

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

None logged.