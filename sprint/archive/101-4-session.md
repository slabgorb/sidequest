---
story_id: "101-4"
jira_key: ""
epic: "101"
workflow: "trivial"
---
# Story 101-4: UI dead-code sweep — delete deprecated OverlayType (zero importers) and retire no-op groupPortraitSegments call sites

## Story Details
- **ID:** 101-4
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-10T10:33:18Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T00:00:00Z | 2026-06-10T10:23:45Z | 10h 23m |
| implement | 2026-06-10T10:23:45Z | 2026-06-10T10:29:22Z | 5m 37s |
| review | 2026-06-10T10:29:22Z | 2026-06-10T10:33:18Z | 3m 56s |
| finish | 2026-06-10T10:33:18Z | - | - |

## Story Context

### Type
Chore (dead-code cleanup / deprecation removal)

### Points
1

### Repos
- sidequest-ui

### Epic
101 — Split-Brain Remediation — Daemon Renderer Drift & Dead Twins

### Technical Approach
Two concrete tasks:
1. **Delete deprecated OverlayType** — Search for all importers of the `OverlayType` type/enum in sidequest-ui. If zero importers found, delete the definition and export.
2. **Retire groupPortraitSegments call sites** — Find all call sites of `groupPortraitSegments()` function. If all call sites are no-op (i.e., the return value is unused or the function has no side effects), remove the calls and optionally delete the function if it has no other purpose.

### Acceptance Criteria
- `OverlayType` enum/type deleted (or confirmed unused and left with a deprecation marker if it has external consumers)
- All `groupPortraitSegments` call sites removed or documented as necessary
- Codebase compiles without errors (TypeScript check)
- No new test failures

## Sm Assessment

Trivial 1-pt dead-code sweep in sidequest-ui — pure deletion, no behavior change. The title is the spec; epic-101 is the split-brain/dead-twins remediation epic this fits cleanly under. Two surgical tasks:

1. **OverlayType** — claimed zero importers. Dev MUST verify zero importers before deletion (grep the ui src), then remove the definition + export. If any importer surfaces, that's a finding, not a silent skip.
2. **groupPortraitSegments** — claimed no-op call sites. Dev confirms each call site's return is unused / side-effect-free, removes the calls, and deletes the function if nothing else uses it.

No tests expected to change behavior; the gate is `npx vitest run` + `tsc` staying green (No Silent Fallbacks — fail loud if a "dead" symbol turns out live). Routing to Julia (dev) for the implement phase.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/hooks/useSlashCommands.ts` — deleted deprecated `OverlayType` type alias (zero importers; `WidgetId` import retained, still used by `SlashCommandResult`)
- `src/lib/narrativeSegments.ts` — deleted `@deprecated` no-op `groupPortraitSegments` passthrough
- `src/components/NarrationScroll.tsx` — unwrapped call site to `buildSegments(...)` directly; dropped import
- `src/components/NarrationCards.tsx` — unwrapped call site to `buildSegments(...).filter(...)`; dropped import

**Verification:**
- `npx tsc --noEmit` → exit 0 (clean)
- `grep OverlayType|groupPortraitSegments src/` → zero residual references
- Both targets were verified dead before deletion: `OverlayType` had only its own definition; `groupPortraitSegments` was a literal `return segments;` passthrough

**Tests:** 2029/2030 passing. The single failure (`lobby-start-ws-open.test.tsx` — "Leave + Start opens a new WebSocket" 5000ms timeout) is a **pre-existing WS-mock flake**, proven by `git stash` → same failure on the clean base branch. Unrelated to this story (touches no lobby/WebSocket code).
**Branch:** feat/101-4-ui-deadcode-overlaytype-portrait-segments (pushed)

**Handoff:** To review phase (The Thought Police).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (2029 pass, 1 pre-existing flake; 0 lint errors, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Yes | clean | none | N/A |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (3 enabled returned, all clean; 6 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

This is a textbook dead-code sweep: +4/−12, four files, pure deletion with two behavior-preserving call-site unwraps. All three enabled Surveillance specialists returned clean; the six disabled ones are pre-filled per settings.

**Data flow traced:** `messages`/`peerActionsByRound` props → `buildSegments(...)` → `.filter(...)` (NarrationCards) / direct (NarrationScroll) → render. Previously the chain passed through `groupPortraitSegments`, which was a literal `return segments;` identity passthrough — removing it yields the same array reference, so the data flow is byte-for-byte identical. DOMPurify sanitization lives *inside* `buildSegments` (narrativeSegments.ts:132) and is untouched — confirmed by [SEC].

**Observations (≥5):**
- [VERIFIED] Zero residual references to both deleted symbols repo-wide — evidence: `grep -rn "OverlayType\|groupPortraitSegments" --include=*.ts --include=*.tsx` returns empty across src + tests + barrels. Complies with No-Stubbing/dead-code-removal rule.
- [VERIFIED] `groupPortraitSegments` unwrap is behavior-identical — evidence: narrativeSegments.ts old body was `return segments;`; the array fed to `.filter()` is the same reference in both pipelines. Corroborated by [EDGE].
- [VERIFIED] `useMemo` dependency arrays unchanged (`[messages, peerActionsByRound]`) in both NarrationCards.tsx:62 and NarrationScroll.tsx:20 — no exhaustive-deps regression introduced. Complies with TS lang-review React hooks rules (lines 52-58).
- [VERIFIED] Import narrowing correct — `WidgetId` import retained in useSlashCommands.ts (still used by `SlashCommandResult`), `NarrativeSegment` type import retained in NarrationCards.tsx. No unused-import or `import type`-vs-value violations (TS rules 45-49).
- [SEC] No security-relevant behavior removed — both symbols were inert (type alias / identity fn); sanitization path intact at narrativeSegments.ts:132.
- [EDGE] No barrel re-export or type-only import propagates the deletion downstream; `useSlashCommands` hook itself remains wired (App.tsx).
- [VERIFIED] Tests GREEN — evidence: 2029/2030 pass; the single `lobby-start-ws-open.test.tsx` timeout reproduces on the clean base branch (Dev's `git stash` proof + [preflight] confirmation), so it is pre-existing and unrelated.

**Subagent tag coverage:** [EDGE] clean · [SEC] clean · [preflight] clean. Disabled (no findings possible): [SILENT] [TEST] [DOC] [TYPE] [SIMPLE] [RULE].

### Rule Compliance
- **No Silent Fallbacks** (CLAUDE.md): Both deletions remove genuinely dead symbols verified before removal — no consumer is silently left missing a reference (tsc exit 0 proves it). Compliant.
- **No Stubbing / dead code is worse than no code** (CLAUDE.md): This story *removes* dead code; directly aligned. Compliant.
- **TS lang-review — import hygiene (45-49):** narrowed imports are correct; no type-only value imports introduced. Compliant (2 files checked: NarrationCards.tsx, NarrationScroll.tsx).
- **TS lang-review — React hooks (52-58):** both `useMemo` calls retain correct deps; no literal-in-deps, no missing deps introduced. Compliant (2 instances checked).
- **No new test needed:** trivial pure-deletion; existing 2029-test suite is the regression net and stays green. The deleted symbols had zero test coverage (nothing to remove).

### Devil's Advocate
Could this deletion break something a grep can't see? Consider the failure modes. (1) *Dynamic/string references* — TS has no reflection here; nothing constructs `"groupPortraitSegments"` as a string or accesses it via index. A repo-wide grep including `.js`/`.d.ts` is therefore authoritative, and it's empty. (2) *Re-export through a barrel* — if `narrativeSegments` were re-exported via an `index.ts`, an external `import { groupPortraitSegments } from "@/lib"` could survive; edge-hunter checked and found no barrel re-export, and tsc would have failed regardless. (3) *Reference-identity dependence* — the subtlest risk: if any downstream code relied on `groupPortraitSegments` returning a *distinct* array from `buildSegments` to break a memo or trigger an effect, removing it would change identity. But the function was `return segments;` — it returned the *same* reference, so removing it is strictly identity-preserving; there is no scenario where a consumer got a different reference before vs after. (4) *The deprecated `OverlayType`* — a confused future dev might look for it; but it was `@deprecated` pointing at `WidgetId`, and the live `WidgetId` type remains the canonical replacement, so its removal reduces confusion rather than creating it. (5) *Test masking* — could the green suite be hiding a real break? The one red test is unrelated (lobby WebSocket) and pre-existing on base. No narration/segment test regressed. Nothing here is broken; the change is as safe as a deletion can be.

**Handoff:** To SM for finish-story.

## Design Deviations

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No spec deviations logged by Dev; none found during review. Nothing to stamp.

## Delivery Findings

### Dev (implementation)
- No upstream findings.

### Reviewer (code review)
- No upstream findings.