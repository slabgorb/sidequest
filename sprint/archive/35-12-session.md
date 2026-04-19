---
story_id: "35-12"
jira_key: null
epic: "35"
workflow: "trivial"
---
# Story 35-12: Delete dead daemon export — is_discardable

## Story Details
- **ID:** 35-12
- **Epic:** 35 (Wiring Remediation II)
- **Workflow:** trivial
- **Repo:** sidequest-daemon
- **Points:** 1
- **Priority:** p2

## Technical Context

The daemon's `renderer/stale.py` module defines `is_discardable(result: RenderResult) -> bool` but this function has zero consumers anywhere in the codebase (daemon, API, UI, content).

**Search results:**
```
$ grep -r "is_discardable" . --include="*.py" --include="*.rs" | grep -v ".venv"
sidequest_daemon/renderer/stale.py:def is_discardable(result: RenderResult) -> bool:
```

**No imports, no calls, no exports.** Pure dead code.

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-11T13:09:07Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-11T00:00:00Z | 2026-04-11T00:00:00Z | <1min |
| implement | 2026-04-11T00:00:00Z | 2026-04-11T00:05:00Z | 5min |

## Work Summary

**Branch:** `feat/35-12-delete-dead-is-discardable-export`
**Commit:** 7764ea6 — chore(daemon): delete dead is_discardable export
**PR:** https://github.com/slabgorb/sidequest-daemon/pull/30

**Actions:**
1. Located `is_discardable()` in `sidequest_daemon/renderer/stale.py`
2. Verified zero consumers via grep across entire codebase
3. Deleted the unused module entirely (22 lines removed)
4. Ran `uv run pytest` — 95 passed, 1 pre-existing failure (unrelated)
5. Verified deletion with final grep (zero references)
6. Committed and pushed

**Epic 35 Complete:** 15/15 stories done. Wiring Remediation II finished.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (1 pre-existing failure unrelated; 0 code smells; lint pre-existing only) | N/A |
| 2 | reviewer-edge-hunter | Yes | clean | none | N/A |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | Yes | findings | 2 | dismissed 2 (no tests existed; out-of-scope wiring-test gap pre-dates PR) |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 | confirmed 4 → all routed to Delivery Findings (pre-existing, out of scope) |
| 6 | reviewer-type-design | Yes | findings | 3 | dismissed 1 (dead invariant per "no stubbing" rule); confirmed 2 → Delivery Findings (pre-existing) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 violations across 6 rules / 11 instances | N/A |

**All received:** Yes (7 returned, 2 disabled)
**Total findings:** 2 confirmed (both pre-existing → upstream), 7 dismissed (with rationale), 0 deferred

## Rule Compliance

Project rules checked against the diff (single-file deletion: `sidequest_daemon/renderer/stale.py`).

### CLAUDE.md (orchestrator) + sidequest-daemon/CLAUDE.md

1. **No Silent Fallbacks** — applies to: any caller of the deleted module.
   - `renderer/__init__.py` — empty file, no re-export. ✓ Compliant.
   - `media/daemon.py` — zero imports from `renderer.stale`. ✓ Compliant.
   - Test suite — zero references. ✓ Compliant.
   - **Verdict:** Compliant (deletion introduces no fallback path because there were no callers to fall back).

2. **No Stubbing — "Dead code is worse than no code."** — applies to: the deletion itself and any replacement.
   - Module fully deleted (22 → 0 lines). No empty shell, no placeholder. ✓ Compliant.
   - No replacement constant added in `models.py`. ✓ Compliant (would have been a new dead invariant — the rule actively *prohibits* relocating an unreferenced policy).
   - **Verdict:** Compliant. This rule is what justifies dismissing the type-design "migrate the invariant" finding.

3. **Don't Reinvent — Wire Up What Exists** — applies to: every "delete dead code" change in Epic 35.
   - Architectural slot check: render pipeline is fire-and-forget over Unix socket — `_write()`/`_respond()` returns synchronously, no in-flight queue, no result buffer, no eviction stage. No place exists where `is_discardable()` would be called even if wired.
   - ADR check: original ADR-044 (speculative prerendering) had a cancel/discard model that `stale.py` plausibly served. **ADR-076 superseded that model** — speculative renders now reconcile at turn boundaries, not by cancellation. The architectural justification for `stale.py` was removed by ADR-076.
   - Epic 35 backlog: no story tasking wire-up of `is_discardable`. The only remaining daemon-touching story (35-15) explicitly excludes the daemon side per its context doc.
   - **Verdict:** Compliant. The "wire it instead of delete it" alternative is dead because both the consumer architecture and the design rationale are gone.

4. **Verify Wiring, Not Just Existence** — applies to: every change claiming dead code removal.
   - Grep across all `.py` files in daemon, api, ui, content: zero matches for `is_discardable`, `_DISCARDABLE_TIERS`, `from .stale`, `from sidequest_daemon.renderer.stale`, `renderer.stale`. Confirmed by 3 independent subagents (silent-failure, edge-hunter, rule-checker).
   - **Verdict:** Compliant. Wiring verified absent.

5. **Every Test Suite Needs a Wiring Test** — applies to: surviving subpackages after deletion.
   - No `test_stale.py` ever existed. Deletion removes nothing from the test suite.
   - Broader observation: the renderer subpackage as a whole lacks a wiring test, but this **predates** the PR and is not introduced by it.
   - **Verdict:** Compliant for this PR. The renderer-wiring-test gap is logged as upstream finding.

6. **OTEL Observability Principle** — applies to: every backend fix touching a subsystem.
   - Deletion of code with zero call sites does not touch any subsystem decision path. There is no engaged subsystem to instrument.
   - **Verdict:** Not applicable (rule explicitly excludes "cosmetic" / no-decision-path changes).

### Drift Evidence (supporting deletion)

- `_DISCARDABLE_TIERS` covered 5 of 7 `RenderTier` variants.
- `FOG_OF_WAR` was **omitted without comment** — strong evidence the partition was never updated when the enum grew.
- A type invariant nobody updates when the underlying enum grows is not an invariant; it's a frozen comment. This is what makes the type-design agent's "preserve the invariant" finding wrong for this case.

## Devil's Advocate

Let me argue this PR is broken. Suppose the deletion is wrong. What's the mechanism by which it bites us?

**Argument 1: Hidden dynamic import.** Python's late binding means `importlib.import_module("sidequest_daemon.renderer.stale")` would have worked at runtime even if no static `import` statement referenced it. If somewhere in the daemon a string-driven plugin loader reflects on `renderer.stale`, deletion will surface as an `ImportError` at the moment that plugin loads — possibly far from the diff. **Refutation:** Grep across all `.py` files for the substring `renderer.stale` (not just `import`) returns zero matches. There is no string-keyed reflection in the daemon. The silent-failure-hunter and rule-checker independently confirmed this via complementary searches. The "dynamic import" attack surface is empty.

**Argument 2: External consumer outside the four repos.** Maybe the LoRA training scripts, the world-builder script, or one of the orchestrator playtest scripts imports it. **Refutation:** Search across the entire `oq-2` tree (daemon + api + ui + content + scripts + orchestrator) for `is_discardable` returns exactly one file: `sprint/epic-35.yaml` — and that's the story title text, not a code consumer. Cross-repo search complete; no external consumer exists.

**Argument 3: The sq-1 archive depended on it and there's a planned port back.** **Refutation:** Sq-1 is the `~/ArchivedProjects/sq-1` codebase, explicitly archived. Any port to the new architecture has to land in the new structure, and the new structure has no consumer slot. Even if a future port wanted this exact policy, it would get re-introduced in its own commit with a real consumer — not retained as a forgotten orphan.

**Argument 4: The architectural pivot in ADR-076 is incomplete and `stale.py` would have been brought back when prerendering is fully wired.** **Refutation:** ADR-076 explicitly says the prerender scheduler "queues against turn boundaries, not audio durations." Turn-boundary reconciliation does not need a per-result discard predicate — turns advance and stale results from prior turns are simply not consumed. The cancel/discard model is architecturally retired, not paused.

**Argument 5: The deletion removes a partition that documented design intent useful to future developers reading `RenderTier`.** This is the type-design subagent's argument. **Refutation:** The partition was already drifting (`FOG_OF_WAR` missing without comment). A drifted invariant misleads more than it documents. Worse, retaining the partition by relocating it to `models.py` creates the very thing CLAUDE.md prohibits: "Dead code is worse than no code." The right way to preserve a design intent is to wire it to a consumer; the second-best way is to delete it and let a future architect introduce it deliberately when needed.

**Argument 6: A confused contributor will misread the deletion as license to delete other unwired modules without architectural review.** This is a process risk, not a code risk. **Refutation:** The session file documents the architectural reasoning explicitly (ADR-044 → ADR-076 pivot). Future contributors looking at this PR will see that "dead code" was justified through ADR analysis, not by grep alone.

**Conclusion of devil's advocacy:** Every argument I can construct against this deletion either fails on grep evidence or fails on the ADR-076 architectural pivot. The deletion is correct.

## Reviewer Assessment

**Verdict:** APPROVED

**Tag dispatch:**
- `[EDGE]` — Edge hunter clean: no in-flight result queue or eviction stage exists where `is_discardable()` would have a wiring slot. Render pipeline is synchronous fire-and-forget over Unix socket. No boundary case introduced by deletion.
- `[SILENT]` — Silent failure hunter clean: zero imports of `renderer.stale` across all four repos. Deletion does not silence any existing failure path.
- `[TEST]` — Test analyzer non-blocking: no `test_stale.py` ever existed; nothing removed from the suite. The broader renderer-subpackage wiring-test gap pre-dates this PR and is captured as a Delivery Finding for future scope.
- `[DOC]` — Comment analyzer: 4 findings, all pre-existing stale documentation in `sidequest-api/crates/sidequest-game/CLAUDE.md` (TTS-removed module references) and `docs/adr/044-speculative-prerendering.md` (Consequences section needs update post-ADR-076). All routed to Delivery Findings — none introduced by this PR.
- `[TYPE]` — Type design: 3 findings. **Dismissed:** "migrate the invariant to models.py" — moving an unreferenced frozenset would create dead code, which CLAUDE.md "No Stubbing" explicitly prohibits ("Dead code is worse than no code"). The partition was already drifting (FOG_OF_WAR uncategorized) — it was not a maintained invariant. **Confirmed (out of scope):** `daemon.py:335` silent-fallback to `SCENE_ILLUSTRATION` on unknown tier_str (CLAUDE.md "No Silent Fallbacks" violation, pre-existing) and `flux_config.py` `FLUX_TIER_CONFIGS` FOG_OF_WAR hole (pre-existing). Both routed to Delivery Findings.
- `[SEC]` — Security subagent disabled via `workflow.reviewer_subagents.security`. Self-assessment: deletion of a tier-classification predicate has no security surface. No auth, no input parsing, no tenant isolation, no secrets touched.
- `[SIMPLE]` — Simplifier subagent disabled via `workflow.reviewer_subagents.simplifier`. Self-assessment: deletion *is* the simplification — 22 lines removed, 0 added, no new abstraction.
- `[RULE]` — Rule checker clean: 6 CLAUDE.md rules checked across 11 instances, 0 violations. The exhaustive rule pass confirms the deletion is consistent with No Silent Fallbacks, No Stubbing, Don't Reinvent, Verify Wiring, Wiring Tests, and OTEL Observability.

**Data flow traced:** N/A — there is no data flow to trace because the deleted function had no callers. The "data flow" question is *whether there should have been a caller*; that question is answered by the ADR-076 architectural pivot (cancel/discard model superseded by turn-boundary reconciliation).

**Pattern observed:** Architecturally consistent dead code removal — `sidequest_daemon/renderer/stale.py` was the daemon-side residue of the original ADR-044 cancel/discard model, made obsolete by ADR-076's turn-boundary reconciliation. The deletion correctly removes vestigial code from a superseded design path. This is the correct close-out for Epic 35 (Wiring Remediation II): once you've wired everything that should be wired, the leftover orphans get deleted.

**Error handling:** N/A — pure deletion, no new error paths introduced. The pre-existing silent-fallback at `media/daemon.py:335` is captured as an upstream Delivery Finding.

**Wiring verified absent:** Confirmed by 3 independent grep passes (silent-failure-hunter, edge-hunter, rule-checker) across daemon, api, ui, content. Only match in entire `oq-2` tree is the story title in `sprint/epic-35.yaml`.

**Epic Closure:** This is story 15/15 of Epic 35 (Wiring Remediation II). On merge, the epic closes.

**Handoff:** To SM (The Announcer) for finish-story.

## Delivery Findings

### Reviewer (code review)

- **Improvement** (non-blocking): Pre-existing silent fallback in daemon tier resolution — unknown `tier_str` silently defaults to `RenderTier.SCENE_ILLUSTRATION` instead of raising. Affects `sidequest-daemon/sidequest_daemon/media/daemon.py:335` (replace ternary fallback with `RenderTier(tier_str)` and let `ValueError` propagate, or add explicit `raise ValueError(f"Unknown render tier: {tier_str!r}")`). Direct violation of CLAUDE.md "No Silent Fallbacks" rule. *Found by Reviewer during code review (surfaced by reviewer-type-design).*

- **Improvement** (non-blocking): Pre-existing undocumented hole in `FLUX_TIER_CONFIGS` — `FOG_OF_WAR` variant of `RenderTier` has no entry, and `FLUX_SUPPORTED_TIERS` derives from dict keys, so a `FOG_OF_WAR` render request would `KeyError` at runtime. Affects `sidequest-daemon/sidequest_daemon/media/flux_config.py:25-70` (either add `FOG_OF_WAR` config or define explicit `UNSUPPORTED_TIERS = frozenset({RenderTier.FOG_OF_WAR})` with rationale comment). *Found by Reviewer during code review (surfaced by reviewer-type-design).*

- **Improvement** (non-blocking): Stale CLAUDE.md feature inventory in `sidequest-game` crate — entries for `tts_stream.rs` (file deleted), `AudioMixer.duck_for_tts()` / `restore_volume()` (methods deleted), and `PrerenderScheduler` "speculative rendering during TTS playback" description are all post-ADR-076 lies. Affects `sidequest-api/crates/sidequest-game/CLAUDE.md` lines 61-92 (delete TTS streaming entry; remove duck_for_tts description; rewrite PrerenderScheduler description to "queues against turn boundaries"). *Found by Reviewer during code review (surfaced by reviewer-comment-analyzer).*

- **Improvement** (non-blocking): ADR-044 (Speculative Prerendering) Consequences section is stale post-ADR-076 — describes the cancel/promote model that has been superseded by turn-boundary reconciliation. Affects `docs/adr/044-speculative-prerendering.md:52` (mark superseded by ADR-076 once 076 is Accepted, and update Consequences to reflect turn-boundary reconciliation; note that `stale.py` was removed as the unimplemented daemon-side residue of the original cancel/discard model). *Found by Reviewer during code review (surfaced by reviewer-comment-analyzer).*

- **Improvement** (non-blocking): The renderer subpackage in sidequest-daemon has no wiring test covering any of its modules — `tests/` does not exercise `models.py`, `base.py`, `beat_filter.py`, or `null.py` from a production entry point. Affects `sidequest-daemon/tests/` (add at least one integration test that imports a real production entry from `sidequest_daemon.renderer` and exercises it via the daemon's actual call path). Pre-dates this PR — not introduced by 35-12. *Found by Reviewer during code review (surfaced by reviewer-test-analyzer).*

## Design Deviations

### Reviewer (audit)
No design deviations were logged by upstream agents (sm-setup ran the trivial workflow without a design phase, and the implementation carried no spec deviation). Nothing to stamp ACCEPTED or FLAGGED.

## Implementation Steps

1. Delete the `is_discardable()` function from `sidequest_daemon/renderer/stale.py`
2. Run pytest to verify no test failures
3. Verify deletion with grep (should find nothing)
4. Commit with message about closing Epic 35

This completes Epic 35 (final story: 15/15 done).