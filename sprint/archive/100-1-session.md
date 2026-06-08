---
story_id: "100-1"
jira_key: ""
epic: "100"
workflow: "trivial"
---

# Story 100-1: Phase 0 — ADR-135 amendment: server-projection/React-render seam, public-firewall rule, no-session invariant

## Story Details

- **ID:** 100-1
- **Jira Key:** (none — Jira not configured)
- **Epic:** 100 (Reference pages → React SPA migration)
- **Workflow:** trivial (phased: setup → implement → review → finish)
- **Type:** chore
- **Points:** 2
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** trivial  
**Phase:** finish  
**Phase Started:** 2026-06-08T15:48:13Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-08T00:00:00Z | 2026-06-08T15:38:07Z | 15h 38m |
| implement | 2026-06-08T15:38:07Z | 2026-06-08T15:42:04Z | 3m 57s |
| review | 2026-06-08T15:42:04Z | 2026-06-08T15:48:13Z | 6m 9s |
| finish | 2026-06-08T15:48:13Z | - | - |

## Technical Summary

This is a documentation/amendment story. Epic 100 introduces a server-projection / React-render seam for the reference pages, replacing the server-rendered HTML model with a server-projected JSON API and React SPA rendering. The design is recorded in `docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md`.

**Story 100-1 records the architectural decision** by amending ADR-135 to document:

1. **The projection/render seam:** Server emits public-projected JSON; React renders it.
2. **C1 — The firewall is a data projection, not a CSS hide:** `reference_visibility.py` is reused verbatim as the server-side projection gate. Keeper fields never cross the JSON boundary.
3. **C2 — No-session invariant:** `/reference/*` SPA routes render with no WebSocket session, no auth, no character state.
4. **C3 — Theme without a session:** CSS-variable injection fed from projection JSON, not the WebSocket `theme_css` event.
5. **C4 — Determinism preserved:** d3-dag (Sugiyama layered layout) replaces SVG hand-layout; byte-deterministic.
6. **C5 — Public URL home:** SPA is canonical; FastAPI retires HTML routes but keeps `/reference/api/*`.

**The Architect amended the epic-100 spec on 2026-06-08** to reconcile the 98-3 / 100-10 map-stack overlap: the shared Map component must be drill-aware-ready for epic 98 / ADR-141 (scale/drill view-model) without forelosing that work.

## Acceptance Criteria

| AC | Detail |
|----|--------|
| ADR-135 amended | New section documents server-projection seam, constraints C1–C5, and public-URL home |
| Projection/render boundary clear | Explicit record of what crosses JSON boundary (public data + theme tokens) |
| C1 firewall documented | `reference_visibility.py` reuse as projection gate; keeper fields never in JSON |
| C2 no-session invariant stated | `/reference/*` routes render without WebSocket/session/auth |
| C3 theme-without-session pattern | Session-free CSS-var injector contract; reuses mechanism, feeds from JSON |
| C4 determinism & map details | d3-dag layout, byte-deterministic; test moves to Vitest |
| C5 public URL home | SPA canonical; FastAPI history-fallback or redirect; API routes kept |
| Epic 98 / 100-10 wiring | Shared Map component drill-aware-ready per Architect amendment (no assumption of `MapWidget` feed/toggle permanence) |

## Delivery Findings

No upstream findings at story setup.

<!-- dev findings below -->
### Dev (implementation)
- No upstream findings. The epic-100 spec + story context were a complete, internally-consistent source; the amendment is a faithful transcription. The downstream phases (100-2…100-12) are already enumerated in the epic YAML and need no new tracking from Phase 0.

### Reviewer (code review)
- **Improvement** (non-blocking): A2's closing line cites "a *strengthening* of Decision §2/§4" but §4 is the identity/role-prohibition rule (no `Cf-Access`, no `is_gm()`); the firewall-at-JSON-boundary claim is a §2 matter and the §4 continuation already lives correctly in A3. Affects `docs/adr/135-reference-pages-public-table-tool.md` (A2 — change "§2/§4" to "§2"). *Found by Reviewer during code review.* [DOC]
- **Improvement** (non-blocking): A7's edge-semantics gloss ("`routes` = jump-mechanics annotations the layout must not treat as dangling") captures only one of the spec's two anomaly cases; the second — a `routes` entry with no backing `adjacent` pair → drop+WARN — is omitted. Mitigated because A7 explicitly defers to the epic-100 spec for full edge semantics. Affects `docs/adr/135-reference-pages-public-table-tool.md` (A7 — add the orphaned-`routes` anomaly to the parenthetical). *Found by Reviewer during code review.* [DOC]
- **Improvement** (non-blocking): The amendment's final subsection `### Implementation (epic 100)` does not follow ADR-118's `### A1…An` house style; should be `### A8 — Implementation (epic 100)`. Affects `docs/adr/135-reference-pages-public-table-tool.md` (rename heading). *Found by Reviewer during code review.* [RULE]
- These three are cheap doc fixes in the same file that **story 100-2 (Phase 1) touches**; fold them into that commit, or apply as a 1-minute chore. None block the Phase 0 deliverable.

## Design Deviations

No deviations at story setup.

### Dev (implementation)
- No deviations from spec. The amendment records exactly the C1–C5 constraint set, the public-URL home principle, and the epic-98/100-10 drill-aware-ready bridge from the story context / epic-100 spec, in the ADR-118 amendment house style (dated `## Amendment` section + `### A1…An` subsections + `implementation-pointer` frontmatter note). No constraints simplified, none added.

### Reviewer (audit)
- **Dev "No deviations from spec"** → ✓ ACCEPTED by Reviewer: verified. The amendment is a faithful transcription of the epic-100 spec's C1–C5 + the Architect's 2026-06-08 edge/ownership reconciliation; no constraint was simplified, dropped, or invented. The one house-style miss (`### Implementation` vs `### A8 —`) is captured as a non-blocking finding, not an undocumented deviation — Dev's claim of "house style followed" is substantially correct (8/9 subsections conform).
- No **undocumented** deviations found: the diff content matches the story scope (docs-only ADR amendment + regenerated indexes + sprint status flip); nothing diverged silently.

## SM Assessment

**Confidence: High.** This is a well-scoped 2-point chore — a docs-only ADR amendment with an authoritative design source already written and freshly Architect-reviewed.

**Why it's ready:**
- The authoritative design lives in `docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md` (the epic-100 spec, which explicitly declares itself as amending ADR-135). Dev has a complete source to transcribe from — no design work required at the implement phase.
- Constraints C1–C5 and the no-session invariant are enumerated in the Technical Summary and ACs above. The amendment is a faithful record, not a new decision.
- The Architect amended that same spec earlier today (2026-06-08) to reconcile the 98-3 / 100-10 map-stack overlap; AC8 captures the drill-aware-ready requirement so the ADR-135 amendment stays consistent with ADR-141.

**Scope guardrails for Dev (Bicycle Repair Man):**
- **Docs only.** Touch `docs/adr/135-*.md`. No code, no `reference_*.py`, no UI. Phase 1+ stories (100-2…100-12) own the implementation.
- The amendment records the seam and constraints; it does NOT redesign the firewall or invent new contracts beyond what the epic-100 spec states.
- Orchestrator is trunk-based → work on `main`, no feature branch.
- Watch the pre-existing ADR-135 frontmatter conventions (run the frontmatter validator; ADR-141 currently carries a non-blocking title/H1 WARN — don't introduce a new one on 135).

**Risks:** Minimal. Only failure mode is scope creep into Phase 1 implementation, or an over-broad rewrite of ADR-135 instead of a surgical amendment. Keep it an amendment block, not a rewrite.

**Routing:** trivial/phased → next phase `implement`, owner `dev`.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `docs/adr/135-reference-pages-public-table-tool.md` — Added `## Amendment — Server-Projection / React-Render Seam (epic 100, 2026-06-08)` section (A1 seam, A2 C1 firewall-at-JSON-boundary, A3 C2 no-session, A4 C3 theme-without-session, A5 C4 d3-dag determinism, A6 C5 public-URL home, A7 epic-98/100-10 drill-aware-ready bridge, + phased implementation map). Updated `implementation-pointer` and added `141` to `related` in frontmatter.
- `docs/adr/README.md`, `docs/adr/DRIFT.md` — regenerated index pointer text for ADR-135 (`scripts/regenerate_adr_indexes.py`, per CLAUDE.md convention after a frontmatter edit). `CLAUDE.md` regenerated identically (no diff — 135's category membership unchanged).
- `sprint/epic-100.yaml` — story 100-1 `status: in_progress` + `started` (set by SM during setup; committed here to keep the working tree clean for the gate).

**Tests:** N/A — docs-only chore, no test suite in scope. ADR frontmatter validator passes (`0 errors`, no new title/H1 WARN on 135). ADR index regeneration clean (141 ADRs loaded).

**ACs:** 8/8 met — seam recorded; JSON boundary explicit (public data + theme tokens cross, keeper fields never); C1–C5 each documented with rationale; public-URL home stated (SPA canonical, API kept, HTML retired); epic-98/100-10 drill-aware-ready framing folded in with ownership boundary + sequencing.

**Branch:** `main` (orchestrator trunk-based, no feature branch) — to be pushed.

**Handoff:** To review phase (The Argument Professional).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — ADR-135 frontmatter PASS (0 err/0 warn on 135), index in sync, no test suite applies to docs |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | clean | none | N/A — docs-only, no test obligation; future test debts (C2 bare-router, C4 Vitest) belong to 100-8/100-10 |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | confirmed 2, dismissed 0, deferred 0 (both non-blocking medium) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 | confirmed 1, dismissed 0, deferred 0 (non-blocking low/style) |

**All received:** Yes (4 enabled returned, 5 disabled via settings)
**Total findings:** 3 confirmed (2 medium [DOC], 1 low [RULE]), 0 dismissed, 0 deferred — all non-blocking

## Reviewer Assessment

**Verdict:** APPROVED (with 3 confirmed non-blocking findings)

This is a docs-only Phase 0 chore: a single ADR-135 amendment recording the epic-100 server-projection/React-render seam, plus regenerated ADR indexes and a sprint status flip. The deliverable is prose, not code — so five code-specific subagents (edge, silent-failure, type-design, security, simplifier) are disabled by settings and N/A here; the meaningful review is documentation accuracy (comment-analyzer) and ADR convention compliance (rule-checker), both of which ran.

### Observations

- [VERIFIED] ADR-135 frontmatter is schema-valid and the title/H1 pair still matches — evidence: `validate_adr_frontmatter.py` reports 0 errors / 0 warnings on 135 specifically; the diff did not touch line 3 (title) or line 15 (H1). The pre-existing repo-wide title/H1 WARNs (ADRs 116–141) were **not** added by this change. Complies with ADR-088.
- [VERIFIED] Index regeneration is clean — evidence: re-running `regenerate_adr_indexes.py` against the committed tree produces zero diff in `README.md`, `DRIFT.md`, and `CLAUDE.md`. No index drift; CLAUDE.md compact entry unchanged (135's category membership did not move). Complies with the CLAUDE.md "rerun after frontmatter edit" convention.
- [VERIFIED] A7's cross-references resolve and are accurate — evidence (my own check): `docs/adr/141-*.md:173` carries the reciprocal 2026-06-08 amendment naming the d3-dag substitution + ownership + sequencing; the epic-100 spec error-handling section (lines 200–214) carries the `adjacent`=topology / `routes`=mechanics edge cross-reference A7 summarizes.
- [VERIFIED] Phase→story map is exact — evidence: amendment's Implementation subsection maps 100-1 (P0), 100-2…100-7 (P1), 100-8/100-9 (P2), 100-10/100-11 (P3), 100-12 (P4); matches `sprint/epic-100.yaml` story list one-to-one.
- [VERIFIED] A3 no-session invariant does not contradict ADR-135 §4 — evidence: §4 prohibits `Cf-Access-Authenticated-User-Email` / `views.py:is_gm()` / seat-role resurrection; A3 extends that prohibition into the client (no WS/auth/character), a faithful continuation, not a reversal. The amendment's self-claim that the firewall "moves earlier and strengthens" is correct: the projection moves from presenter to JSON wire.
- [DOC] **[MEDIUM, non-blocking]** A2 cites "strengthening of Decision §2/§4"; the §4 reference is imprecise (§4 is identity-prohibition; the firewall-move is a §2 matter, with the §4 continuation correctly in A3) at `docs/adr/135-reference-pages-public-table-tool.md` A2.
- [DOC] **[MEDIUM, non-blocking]** A7's edge-anomaly gloss omits the second spec anomaly case (orphaned `routes` with no backing `adjacent` → drop+WARN); mitigated by A7's explicit deferral to the spec, at A7.
- [RULE] **[LOW, non-blocking]** `### Implementation (epic 100)` deviates from ADR-118's `### A1…An` house style; should be `### A8 — Implementation (epic 100)`.
- [VERIFIED] No silent-fallback / stub doctrine violations — evidence (rule-checker, confirmed): A6's "history-fallback" is standard SPA deep-link routing and "redirect-to-SPA-host" is explicitly deferred to "confirmed at planning time", not silently tried; no TODO/placeholder/skeleton text. Complies with CLAUDE.md No Silent Fallbacks / No Stubbing.

### Dispatch tag coverage

[EDGE] disabled — N/A · [SILENT] disabled — N/A · [TEST] clean (docs-only, no test obligation) · [DOC] 2 confirmed non-blocking findings (A2 §4 cite, A7 edge gloss) · [TYPE] disabled — N/A · [SEC] disabled — N/A · [SIMPLE] disabled — N/A · [RULE] 1 confirmed non-blocking finding (A8 heading style).

### Rule Compliance

- **ADR-088 frontmatter schema** (1 instance: ADR-135): compliant — all required fields present/valid.
- **ADR-088 title↔H1 match** (1 instance): compliant — exact match, untouched by diff.
- **Index-regen-after-frontmatter-edit** (3 instances: README, DRIFT, CLAUDE): compliant — zero regen drift.
- **ADR-118 amendment house style** (9 subsections): 8/9 compliant; 1 deviation (`### Implementation` → should be `### A8`), recorded as [RULE] finding above.
- **No Silent Fallbacks / No Stubbing** (3 instances checked): compliant — no blessed fallback/stub.

### Devil's Advocate

Argue this amendment is broken. The strongest case: an accepted ADR is a binding reference, and **A7's compression is exactly where a downstream bug is born**. The implementer of story 100-10 builds the shared d3-dag layout; if they read only ADR-135's A7 — "`routes` … the layout must not treat as dangling" — they may conclude that *every* `routes` entry is benign and feed orphaned routes (endpoints absent from any `adjacent` list) into the layout as connectivity, silently inventing edges the topology never had. That is a real silent-acceptance failure mode, and it sits in the one subsystem (cartography) where two epics already collided. Counter-argument that holds: A7 does not stand alone — it explicitly says "see … the epic-100 spec for the `cartography.yaml` edge semantics," and the spec's error-handling section spells out both anomaly cases with a named WARN span (`sidequest.reference.map_dangling_edge`). The ADR is a pointer, not the authoritative edge spec, and it points correctly. So the failure mode requires an implementer to both ignore the explicit deferral and skip the spec — at which point the ADR's compression is not the proximate cause. Second attack: could the §2/§4 mis-cite mislead someone into thinking the JSON-boundary firewall has identity-coupling implications? Unlikely — A3 immediately and correctly frames the §4 (no-session) continuation, so the cross-leak is cosmetic. Third: does the amendment over-promise by saying the firewall "strengthens"? No — moving the projection from presenter (HTML) to wire (JSON) genuinely removes the in-browser-network-tab leak vector, which is a real strengthening, and C1 is the binding constraint for Phase 1's security tests. Conclusion: the findings are real but non-blocking; the deferral pointers and the authoritative spec backstop every compression. No new finding surfaced that rises above the three already recorded.

### Verdict rationale

No Critical/High findings. The three confirmed findings are non-blocking doc-accuracy/style nits, each mitigated (A2 is cosmetic; A7 defers to the authoritative spec; A8 is pure heading style) and each a sub-minute fix in a file that **story 100-2 already reopens**. Rejecting Phase 0 to ping-pong three trivial edits — and re-run the subagent panel — costs materially more than folding them into 100-2 or a quick chore. Findings recorded in Delivery Findings with exact fixes.

**Data flow traced:** N/A (no code path) — the "input" here is the epic-100 spec → ADR-135 amendment prose; traced for fidelity, confirmed faithful.
**Pattern observed:** ADR-118 dated-amendment house style, correctly applied at `docs/adr/135-reference-pages-public-table-tool.md:141` (8/9 subsections conform).
**Error handling:** N/A (docs) — but the amendment correctly documents downstream error behavior (dangling-edge WARN, planning-time deploy confirmation) without blessing any silent fallback.
**Handoff:** To SM (The Announcer) for finish-story.