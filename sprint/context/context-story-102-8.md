---
parent: context-epic-102.md
workflow: trivial
---

# Story 102-8: Doc-drift cleanup — retire stale "deferred"/"not wired" markers post-102

## Business Context

ADR-085's tracker-hygiene principle: docs that say "not wired" about things that ARE wired are worse than no docs — they send the next agent hunting for a gap that doesn't exist, or worse, "re-implementing" wired code (the exact failure CLAUDE.md's Don't Reinvent warns about). Concretely measured: `ruleset/wwn.py`, `swn.py`, `cwn.py` carry "not wired to dispatch (Plan 3)" / "deferred" markers while `apply_killing_blow` IS wired at `dispatch/dice.py:644`/`725` and `veterans_luck` has a narrator tool. After 102-1..7 land, `DRIFT.md` and the WN plan docs will be wrong in the other direction too — claiming deferrals this epic retired. This 2-point chore makes the written record match reality.

## Technical Guardrails

- **Sequencing: LAST in the epic.** This story reconciles docs against the post-102 state — run it after 102-1..7 merge (or explicitly note any story that didn't land, so "deferred" markers for it are *kept*, accurately).
- **Comment/docstring edits only in `sidequest-server`** — `ruleset/wwn.py`, `swn.py`, `cwn.py` headers and inline markers. Zero behavior changes; the test suite must be untouched and green.
- **Verify before deleting each marker** (per the Reviewer comment-analysis discipline): for every "deferred"/"not wired" line, confirm the wiring with a file:line citation in the PR description. A marker that's still TRUE stays — this is reconciliation, not bulk deletion.
- **DRIFT.md protocol:** `docs/adr/DRIFT.md` entries for ADR-114/117/139 (and any WN-adjacent partials) get updated status; if an ADR moves from *partial* to fully-live, update its frontmatter and rerun `scripts/regenerate_adr_indexes.py` (ADR-088 — the index is generated, never hand-edit the CLAUDE.md/README block).
- **Plan-doc disposition:** the completed specs (`2026-05-26-swn-module-design.md` etc.) get a short status addendum (phases P4/P5/P7 delivered by 102-4/5/6, AWN §6.5 discharged by 102-7) rather than rewrites — specs are historical records.
- **Repos:** server (comments) + orchestrator (DRIFT.md, specs). Orchestrator PRs target `main`, server targets `develop` (repos.yaml discipline).

## Scope Boundaries

**In scope:**
- Stale-marker retirement in `wwn.py`/`swn.py`/`cwn.py` (and `awn.py` if it carries any) with per-marker verification
- `docs/adr/DRIFT.md` reconciliation for WN-family ADRs; frontmatter + index regeneration if statuses change
- Status addenda on the WN plan/spec docs reflecting what 102 delivered

**Out of scope:**
- Any code behavior change, however small — if verification finds a marker that's true (something still unwired), that's a NEW story/backlog item, not a fix here
- Non-WN drift entries in DRIFT.md
- README/CLAUDE.md narrative rewrites beyond the generated ADR block

## AC Context

1. **No false "unwired" claims remain:** grep for `not wired`/`deferred`/`Plan 3` across `game/ruleset/*.py` returns only markers that are verifiably still true (each surviving marker justified in the PR).
2. **DRIFT.md matches reality:** WN-family entries reflect post-102 state; any ADR status changes flow through frontmatter + `regenerate_adr_indexes.py` (generated blocks regenerate cleanly, no hand edits).
3. **Specs annotated:** each retired plan phase has a dated addendum naming the delivering story.
4. **Zero behavior delta:** server test suite green with no test changes; diff is comments/docs only (reviewable by inspection).

## Assumptions

- 102-1 through 102-7 are merged (or their non-delivery is explicitly recorded so true deferrals keep their markers).
- `regenerate_adr_indexes.py` runs clean on the current tree (it did as of the last ADR landing).
- 2 points holds because verification is grep + citation, not investigation — the epic's seven preceding stories already established what's wired.
