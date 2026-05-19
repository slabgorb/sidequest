---
story_id: "52-1"
jira_key: "skip"
epic: "52"
workflow: "trivial"
---
# Story 52-1: ADR-096 subsume amendment + DRIFT/index regenerate (no supersedes-by; symmetric related)

## Story Details
- **ID:** 52-1
- **Epic:** 52
- **Title:** ADR-096 subsume amendment + DRIFT/index regenerate (no supersedes-by; symmetric related)
- **Workflow:** trivial
- **Type:** chore
- **Points:** 1
- **Repos:** orchestrator
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-19T09:29:01Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19T09:14:14Z | 2026-05-19T09:16:40Z | 2m 26s |
| implement | 2026-05-19T09:16:40Z | 2026-05-19T09:23:23Z | 6m 43s |
| review | 2026-05-19T09:23:23Z | 2026-05-19T09:29:01Z | 5m 38s |
| finish | 2026-05-19T09:29:01Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Gap** (non-blocking): ADR validator (`pf validate adr`) hasn't been updated to ADR-088's frontmatter-only convention. It demands prose-style `**Status:** / **Date:** / **Author:**` fields in the body and fails every modern ADR (349 errors corpus-wide; 3 on ADR-096 — all pre-existing, not introduced by this story). Affects `pf` source: `pf/validate/adapters/adr.py` (the `_validate_adr` body-field regex checks need to either read frontmatter instead, or skip files that have valid frontmatter per ADR-088). *Found by Dev during implementation.*
- **Improvement** (non-blocking): The ADR-index regen script's `IMPL_BADGES` dict in `scripts/regenerate_adr_indexes.py` only knows `live | drift | partial | deferred | not-applicable | retired` — same enum as ADR-088. If story-context authors keep proposing `amended` as a status (this story did), a schema-change ADR is needed before agents can honor the request. Affects `scripts/regenerate_adr_indexes.py` (IMPL_BADGES + DRIFT filter) and `docs/adr/088-adr-frontmatter-schema.md` (enum). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Story-context authoring (sm-setup / context-story templates) repeatedly proposes ADR `implementation-status` values that don't exist in the ADR-088 enum (`amended` here; "needs `amended`" appeared verbatim in the AC table). This generates avoidable spec deviations every time an ADR is amended without a successor. Affects `pf/templates/context-story.md` (or equivalent) and the prompt that produces AC for ADR-touch stories — the template should either cite ADR-088's enum explicitly or steer toward the body-banner convention for enum-illegal nuance. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Kept `implementation-status: partial`; did not switch to `amended`**
  - Spec source: sprint/context/context-story-52-1.md, AC table and Frontmatter Fields section
  - Spec text: "Update frontmatter: `implementation_status: amended` (change from `partial`)" and "frontmatter has `implementation_status: amended`"
  - Implementation: Left `implementation-status: partial`; expressed the amendment as a body banner + `implementation-pointer: 106`. Symmetric `related: [..., 106]` added; ADR-106 already lists 96.
  - Rationale: ADR-088 (line 56) hard-defines the enum as `live | partial | drift | deferred | not-applicable | retired`. `amended` is not a member. Saved project rule (`project_adr_schema_enforced_rules`) restates this: enum-illegal nuance goes in the body banner, not the enum. The regenerate_adr_indexes.py IMPL_BADGES dict also lacks `amended` — it would have rendered raw and dropped 096 out of DRIFT.md silently. Story context is higher authority than ADR-088 per spec-authority hierarchy, but the saved doctrine + tooling alignment make the body-banner expression the doctrinally correct way to honor the same intent. The banner is LOUD (top-of-file blockquote, dated) and the pointer threads 096→106 in both indexes.
  - Severity: minor
  - Forward impact: none on downstream epic 52 stories (52-2 through 52-5 target ADR-106's materializer seam, which the new `implementation-pointer: 106` makes machine-discoverable). If a future story needs `amended` as a first-class enum, that's an ADR-088 schema change, not a 52-1 concern.

- **Set `implementation-pointer: 106` (was `null`)**
  - Spec source: docs/adr/088-adr-frontmatter-schema.md, line 75
  - Spec text: "Required if `implementation-status` is `partial` or `drift`."
  - Implementation: Pointer was `null` despite `implementation-status: partial` — a pre-existing schema violation. Setting it to `106` resolves the violation and threads the index entries to the runtime owner.
  - Rationale: Free fix while we're already touching the frontmatter; honors ADR-088 schema; makes index regen render the link.
  - Severity: cleanup (pre-existing bug, in-scope side fix)
  - Forward impact: positive — DRIFT.md and README.md now point 096 readers at 106.

### Reviewer (audit)
- **Kept `implementation-status: partial`; did not switch to `amended`** → ✓ ACCEPTED by Reviewer: agrees with author reasoning. ADR-088 line 56 hard-defines the enum without `amended`; saved doctrine `project_adr_schema_enforced_rules` explicitly requires enum-illegal nuance to live in a body banner. The body banner is LOUD (top-of-file blockquote, dated 2026-05-19) and `implementation-pointer: 106` threads readers to the runtime owner. Story-context wanted a schema-illegal value; Dev correctly honored the higher-authority schema with the doctrinally-correct alternative.
- **Set `implementation-pointer: 106` (was `null`)** → ✓ ACCEPTED by Reviewer: pre-existing schema violation (088 line 75 requires pointer when status is `partial`) repaired in-scope. Free correct fix; renders the indexes properly.
- No undocumented spec deviations spotted.

## Sm Assessment

**Story:** ADR-096 subsume amendment + DRIFT/index regenerate. Gate story for epic 52 (procedural megadungeon runtime wiring).

**Scope (orchestrator-only, no code):**
- Amend ADR-096 to record the subsume relationship with ADR-106 (related, symmetric — NOT superseded-by per saved ADR schema rules).
- Update related ADR frontmatter on the partner ADR(s) so the symmetric `related:` field points back.
- Regenerate `docs/adr/README.md`, DRIFT.md, and SUPERSEDED.md indexes via `scripts/regenerate_adr_indexes.py`.
- Commit the regenerated indexes alongside the ADR frontmatter edits in a single PR.

**Acceptance gate (see sprint/context/context-story-52-1.md for full AC):**
- ADR-096 frontmatter carries the related-link to ADR-106 with rationale in the body banner.
- Symmetric: the related ADR's frontmatter points back to 096.
- No `superseded-by` introduced (subsume ≠ supersede — saved rule: `project_adr_schema_enforced_rules`).
- Regenerated indexes commit cleanly; pre-commit schema validation passes.

**Workflow:** trivial (setup → implement → review → finish). 1pt mechanical doc-touch, single-repo.

**Next agent:** Dev (Winchester) — execute the ADR amendment and index regen, then hand to Reviewer.

**No blockers.** Session, branch, epic context, story context all in place.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `docs/adr/096-cavern-renderer-revival.md` — added `106` to `related`, set `implementation-pointer: 106`, inserted top-of-file "AMENDED FOR RUNTIME GENERATION" body banner explaining what 096 still owns (format contract) vs what 106 subsumes (runtime path), amended `## Status` line
- `docs/adr/README.md` — regenerated (096 row now shows `*partial* → ADR-106`)
- `docs/adr/DRIFT.md` — regenerated (096 row now points at ADR-106 instead of `—`)
- `sprint/context/context-epic-52.md`, `sprint/context/context-story-52-1.md` — sm-setup artifacts, untracked
- `sprint/epic-52.yaml` — sm-setup updated (story in_progress, branch, assignee)

**ADR-106 symmetric link:** already present (ADR-106 frontmatter line 9: `related: [55, 74, 87, 96]`). No edit needed.

**Tests:** N/A — trivial workflow, single-repo ADR doc-touch, no test suite applies. Regen script ran cleanly; ADR validator was failing pre-edit and still fails identically (349 corpus errors, 3 on 096 — all pre-existing per ADR-088 schema vs validator drift, captured as Delivery Finding).

**Branch:** `feat/52-1-adr-096-subsume-amendment` (pushed below)

**AC verification:**
- ✓ ADR-096 records the subsume relationship with ADR-106 (body banner + `related` + `implementation-pointer`)
- ✓ Symmetric: ADR-096 → 106 (added) and ADR-106 → 96 (already present)
- ✓ No `superseded-by` introduced (`superseded-by: null` unchanged)
- ✓ Indexes regenerated and threaded
- ✗ Not `implementation-status: amended` — deviation logged; doctrinally correct alternative used (body banner + legal enum). See Dev (implementation) deviations.

**Handoff:** To Reviewer (Colonel Potter) for review phase.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — all 4 substantive checks pass: index regen idempotent, ADR-096 frontmatter parses, ADR-106 symmetric link confirmed, body banner + status line present |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A | Disabled via settings (workflow.reviewer_subagents.edge_hunter=false) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A | Disabled via settings — also N/A: trivial workflow, no test code in diff |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A | Disabled via settings — also N/A: doc-only diff, no types |
| 7 | reviewer-security | No | Skipped | disabled | N/A | Disabled via settings — also N/A: doc-only diff |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A | Disabled via settings — Reviewer performed ADR-088 rule enumeration directly (see Rule Compliance) |

**All received:** Yes (1 enabled subagent returned clean; 8 disabled per settings, pre-filled per protocol)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Scope sanity-check:** 23-line orchestrator-only doc change (ADR-096 body banner + frontmatter; index regen output). Trivial workflow. No code paths, no tests, no runtime impact. Reviewer ceremony right-sized per saved doctrine (`feedback_plan_ceremony`): enabled only `preflight` subagent; ran ADR-088 schema rule enumeration directly.

### Rule Compliance (ADR-088 schema + saved ADR doctrine)

Enumerated every rule that applies to this diff against every frontmatter field touched:

1. **ADR-088 `implementation-status` enum** (`live | partial | drift | deferred | not-applicable | retired`) — ADR-096 keeps `partial`. ✓ COMPLIANT. `amended` is not a legal value; Dev correctly used body banner instead (see Reviewer audit on deviation 1).
2. **ADR-088 `implementation-pointer` required when status is `partial`** (088 line 75) — Was `null`, now `106`. ✓ COMPLIANT (pre-existing schema violation repaired in-scope).
3. **ADR-088 `related` list type — ADR IDs** — Was `[55, 71, 86, 89]`, now `[55, 71, 86, 89, 106]`. All integers, all valid ADR IDs. ✓ COMPLIANT.
4. **ADR-088 `superseded-by` is `ADR-id or null`** — Remains `null`. ✓ COMPLIANT. Critical: subsume ≠ supersede; saved doctrine `project_adr_schema_enforced_rules` would have demanded `implementation-status: retired` had `superseded-by` been set. Dev correctly avoided it.
5. **Saved doctrine: "superseded ⇒ implementation-status: retired"** — N/A; this is not a supersession.
6. **Saved doctrine: "supersedes must be symmetric"** — N/A; no supersession. The analogous symmetry for `related` IS satisfied: 096→106 added by this diff; 106→96 already present (verified at docs/adr/106-runtime-procedural-jaquaysed-megadungeon.md:9 — `related: [55, 74, 87, 96]`).
7. **Saved doctrine: enum-illegal nuance ⇒ body banner, not enum** — Body banner at docs/adr/096-cavern-renderer-revival.md:14-26 carries the amendment; enum stays legal. ✓ COMPLIANT.
8. **Index regen idempotent (ADR-088 mandates auto-generation)** — Confirmed by preflight: `scripts/regenerate_adr_indexes.py` produces zero diff on README/DRIFT/SUPERSEDED/CLAUDE.md after this branch's regen. ✓ COMPLIANT.

### Observations

- [VERIFIED] ADR-096 frontmatter conforms to ADR-088 schema — docs/adr/096-cavern-renderer-revival.md:1-13. `related: [55, 71, 86, 89, 106]`, `implementation-pointer: 106`, `superseded-by: null`, `implementation-status: partial`. All fields conform to enum and type rules. Complies with all 088 rules enumerated above.
- [VERIFIED] Symmetric `related` link — ADR-106 already lists `96` (docs/adr/106-runtime-procedural-jaquaysed-megadungeon.md:9). No backfill needed; symmetry confirmed both directions.
- [VERIFIED] Body banner is LOUD per doctrine — docs/adr/096-cavern-renderer-revival.md:14-26 is a dated (2026-05-19) top-of-body blockquote that explicitly bisects ownership: format contract stays with 096, runtime path subsumed by 106. Matches saved-doctrine pattern for enum-illegal nuance.
- [VERIFIED] `## Status` amendment line — docs/adr/096-cavern-renderer-revival.md:32-34. Inline reminder that an amendment exists so readers skimming `Status` don't miss the banner.
- [VERIFIED] Index regen idempotent — confirmed by preflight; re-running `regenerate_adr_indexes.py` produces zero diff on README/DRIFT/SUPERSEDED/CLAUDE.md.
- [VERIFIED] No `superseded-by` introduced — `superseded-by: null` unchanged. This is the load-bearing distinction for this story (subsume vs supersede).
- [VERIFIED] Pre-existing schema violation repaired in-scope — `implementation-pointer` was `null` despite `partial` status; now `106`. Honors ADR-088 line 75. Bonus fix in same touch.
- [VERIFIED] Indexes thread the relationship — DRIFT.md row goes from `—` to ADR-106 link; README.md DRIFT-table row + ADR-Index row both show `*partial* → ADR-106`. Both are the canonical regen output.
- [LOW] [DOC] sprint/context/{context-epic-52.md,context-story-52-1.md} and sprint/epic-52.yaml are listed in the diff stat but are sm-setup artifacts. Not part of the substantive change. No issue.
- [VERIFIED] Preflight clean — index regen idempotent, frontmatter parses, symmetric link confirmed, body banner + status line present, script smoke OK. No new validator errors introduced (pre-existing 349-corpus / 3-on-096 failures are baseline noise per saved Dev finding, not regressions).

### Devil's Advocate

Could this amendment go wrong? A few angles:

**"Body banner gets stale."** ADR-088 prefers structured frontmatter exactly so indexes don't drift from prose. A free-form 2026-05-19 dated banner introduces a second source of truth that could disagree with the frontmatter if 106's relationship changes. Counter-argument: the banner is *narrative ownership prose*, not metadata. The frontmatter still carries the machine-readable `related` + `implementation-pointer`. The banner describes which parts each ADR owns — that's editorial, not enumerable, and ADR-088 has no field for it. If 096 is ever fully superseded by 106, the lifecycle change (`superseded-by: 106`, `implementation-status: retired`) updates both the frontmatter and demands rewriting the banner — they evolve together. Risk accepted.

**"`implementation-pointer: 106` overloads semantics."** The pointer field per ADR-088 line 75 is "Required if `implementation-status` is `partial` or `drift`." Its conventional use is to point at a restoration ADR (often ADR-087). Here it points at the ADR that subsumes the runtime path. Is this stretching the field? No — 096 is `partial`; the implementation that *would* complete it is 106 (different schedule, runtime not authoring-time, but still the closest live pointer). The field's purpose is "where is the implementation," and 106 is the most truthful answer available. ADR-088 doesn't forbid pointing at a different ADR; it explicitly allows ADR-id as a valid pointer.

**"Could someone reading just the frontmatter miss the amendment?"** With `implementation-status: partial` and pointer `106`, a frontmatter-only reader sees "implementation is partial, owned by 106" — which IS the truth. The banner adds *why* and *which parts*. Frontmatter-truth and banner-truth align.

**"What if a downstream tool keys on `implementation-status: amended`?"** No tool does, and no tool should — `amended` isn't a legal value. Saved doctrine explicitly steers nuance into the banner. Future-proof.

**"What if `pf validate adr` breaks on this diff?"** It does break, but identically — 3 errors on ADR-096 pre- and post-edit per Dev's finding; 349 corpus-wide. This is pre-existing validator drift against the ADR-088 schema, captured as a separate non-blocking Delivery Finding. Not introduced by this story.

**"What about the unstaged sprint/current-sprint.yaml drift?"** Preflight subagent flagged it but conflated working-tree `git diff` with branch `git diff main...HEAD`. Verified: that file is NOT in the branch diff, only in unstaged working tree. Separate concern — likely epic 54 promotion drift from another machine, not 52-1's scope. SM/finish phase will handle it.

Devil's Advocate finds no new findings.

**Data flow traced:** ADR-096 amendment (body banner + `related` += 106 + `implementation-pointer` = 106) → `scripts/regenerate_adr_indexes.py` reads frontmatter → emits README.md + DRIFT.md rows pointing 096 readers at 106. Idempotent: re-running the script produces zero diff. Symmetric backward: ADR-106 already carries 96 in its `related` list.

**Pattern observed:** Enum-illegal nuance expressed via dated body banner + legal enum value — the documented saved-doctrine pattern (`project_adr_schema_enforced_rules`). docs/adr/096-cavern-renderer-revival.md:14-26.

**Error handling:** N/A — no runtime; doc + index regen are static.

**Subagent-tag coverage:** `[EDGE]` N/A (subagent disabled; no boundary code) · `[SILENT]` N/A (disabled; no error paths) · `[TEST]` N/A (disabled; no tests) · `[DOC]` used above on sm-setup artifact observation · `[TYPE]` N/A (disabled; no types) · `[SEC]` N/A (disabled; no security surface) · `[SIMPLE]` N/A (disabled; 23-line doc diff) · `[RULE]` Rule Compliance section above enumerates ADR-088 schema + saved doctrine, all compliant.

**Handoff:** To SM (Hawkeye) for finish ceremony.