---
story_id: "58-3"
jira_key: null
epic: "58"
workflow: "trivial"
---
# Story 58-3: Generalize tone chip renderer: 'high {axis}' / 'low {axis}' for any axis name

## Story Details
- **ID:** 58-3
- **Jira Key:** None (no Jira in SideQuest)
- **Workflow:** trivial (3 phases: setup → implement → review → finish)
- **Stack Parent:** none
- **Priority:** p1
- **Points:** 2

## Acceptance Criteria
- [ ] toneAxes.ts removes hardcoded label/glyph lookup
- [ ] any axis with v≤0.33 renders as 'low {axis_name}'
- [ ] any axis with 0.33<v<0.67 renders as 'medium {axis_name}'
- [ ] any axis with v≥0.67 renders as 'high {axis_name}'
- [ ] all 6 live worlds render one chip per declared axis (verified in snapshot test or live lobby)

## Acceptance Criteria Background
Current toneAxes.ts (sidequest-ui/src/screens/lobby/toneAxes.ts) hardcodes a 5-axis lookup table with curated labels (serious/gritty/bleak/etc) and drops anything in the neutral band. Worlds whose axis_snapshot uses other names (cosy/gossip/swagger/chrome/weirdness/balance/etc.) get ZERO chips — implementation-order artifact.

Per Keith 2026-05-19: every authored axis gets a chip. Three buckets:
- v ≤ 0.33 → 'low {axis_name}'
- 0.33 < v < 0.67 → 'medium {axis_name}'
- v ≥ 0.67 → 'high {axis_name}'

Drop the hardcoded labels lookup table. Drop the per-axis glyphs (or use one generic chip glyph). Drop the 'neutral = no chip' rule — every authored axis surfaces as tagged info.

Verify all 6 live worlds render chips for every axis they declare:
- beneath_sunden (comedy/gravity/outlook) → 3 chips
- burning_peace (balance/mysticism/conflict) → 3 chips
- flickering_reach (hope/tech_level/weirdness) → 3 chips
- the_circuit (stakes/law/chrome) → 3 chips (all medium)
- coyote_star (scale/tone/swagger) → 3 chips
- glenross (cosy/puzzle/gossip/gothic) → 4 chips

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-19T23:24:29Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19 | 2026-05-19T22:58:13Z | 22h 58m |
| implement | 2026-05-19T22:58:13Z | 2026-05-19T23:00:53Z | 2m 40s |
| review | 2026-05-19T23:00:53Z | 2026-05-19T23:07:38Z | 6m 45s |
| finish | 2026-05-19T23:07:38Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### SM (setup)
- No upstream findings.

### Dev (implementation)
- No upstream findings during implementation.
- No upstream findings during Pass-2 rework.

### Reviewer (code review)
- No upstream findings (Pass 1).
- No upstream findings (Pass 2). One Pass-2 self-contradiction (lying error message claiming `[0, 1]` enforcement that the code did not deliver) caught and fixed in-place at `0ffb1f2`.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No design deviations recorded

## Sm Assessment

**Setup Complete:** Yes

**Story:** 58-3 — Generalize tone chip renderer: 'high {axis}' / 'low {axis}' for any axis name
**Workflow:** trivial (setup → implement → review → finish)
**Branch:** `feat/58-3-tone-chips-generalize` (sidequest-ui, off develop)
**Repos:** sidequest-ui only

**Scope summary:** ~10-line TypeScript change to `sidequest-ui/src/screens/lobby/toneAxes.ts`. Drop hardcoded `AXIS_LABELS` lookup + per-axis glyphs. Three buckets: v≤0.33 → `low {axis}`, 0.33<v<0.67 → `medium {axis}`, v≥0.67 → `high {axis}`. Drop the "neutral = no chip" filter — every authored axis surfaces as tagged info. Verify all 6 live worlds render chips for every axis they declare.

**Handoff:** To Dev (implement phase).

## Dev Assessment (Pass 2 — Reviewer rejection fixes)

**Implementation Complete:** Yes

**Files Changed (this pass — commit `46e2abf`):**
- `sidequest-ui/src/screens/lobby/toneAxes.ts` — Added `Number.isFinite` guard that throws on `NaN` / `±Infinity` (fail-loud per CLAUDE.md). Corrected JSDoc on `LOW_THRESHOLD` / `HIGH_THRESHOLD` to "At or below/above this threshold..." to match the `<=` / `>=` semantics.
- `sidequest-ui/src/screens/lobby/__tests__/toneAxes.test.ts` — Added 4 tests: tied-distance (both chips preserved when two axes share distance-from-neutral), and three throw assertions for `NaN`, `Infinity`, `-Infinity`.
- `sidequest-ui/src/screens/lobby/__tests__/WorldPreview.test.tsx` — Added wiring test: renders `<WorldPreview>` with a non-empty `axis_snapshot` and asserts `high gravity`, `low comedy`, `medium outlook` chips appear in the DOM end-to-end (previous suite only passed `{}` and never exercised the chip render branch at `WorldPreview.tsx:139`).
- `sidequest-ui/src/screens/lobby/WorldPreview.tsx` — Bounded boy-scout: stale comment "only rendered when axes are polarized enough" replaced with "one per authored axis; hidden only when the world declared none." Matches the post-58-3 semantics.

**Files Changed (cumulative across both Dev passes):**
- `sidequest-ui/src/screens/lobby/toneAxes.ts`
- `sidequest-ui/src/screens/lobby/__tests__/toneAxes.test.ts`
- `sidequest-ui/src/screens/lobby/__tests__/WorldPreview.test.tsx`
- `sidequest-ui/src/screens/lobby/WorldPreview.tsx`

**Reviewer findings disposition:**
| Finding | Severity | Resolved by |
|--------|----------|-------------|
| NaN/non-finite silent "medium" + corrupt sort key | HIGH | `Number.isFinite` throw in `toneAxes.ts:51-56`; tests at `toneAxes.test.ts` lines 73-83 |
| No wiring test — chip branch never exercised | HIGH | `WorldPreview.test.tsx` describe block "tone chips wiring" |
| JSDoc "Below/Above" contradicts `<=`/`>=` | MEDIUM | `toneAxes.ts:30,32` updated |
| Tied-distance untested | LOW | `toneAxes.test.ts` "keeps both chips when two axes share..." |

**Tests:** 1455/1455 passing across full sidequest-ui suite (137 test files); targeted lobby suite 63/63.
**Branch:** `feat/58-3-tone-chips-generalize` (pushed — `46e2abf`).

**Handoff:** To Reviewer (review phase).

### Dev (implementation)
- No deviations from spec.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — tests 17/17 green, type-check pass, scoped lint clean (pre-existing App.tsx warning unrelated to diff) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.edge_hunter=false |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.silent_failure_hunter=false |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (2 high, 1 medium, 2 low) | confirmed 3, dismissed 2 |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (both high) | confirmed 2 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.type_design=false |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.security=false |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via workflow.reviewer_subagents.simplifier=false |
| 9 | reviewer-rule-checker | Yes | findings | 3 (all high) | confirmed 3 — overlaps test-analyzer findings (same root causes) |

**All received:** Yes (4 returned + 5 disabled per settings)
**Total findings:** 6 confirmed (after dedup across overlapping sources), 2 dismissed, 0 deferred

### Finding Decisions

**Confirmed (must fix before approval):**
1. `[DOC]` `toneAxes.ts:30` LOW_THRESHOLD JSDoc says "Below this" but code uses `<=` — fix to "At or below this threshold". (comment-analyzer high)
2. `[DOC]` `toneAxes.ts:32` HIGH_THRESHOLD JSDoc says "Above this" but code uses `>=` — fix to "At or above this threshold". (comment-analyzer high)
3. `[TEST]` `[RULE]` `toneAxes.ts:46-70` No guard on `NaN` or non-finite values. `NaN <= 0.33` and `NaN >= 0.67` both false → silent "medium {axis}" with `Math.abs(NaN-0.5)=NaN` corrupting Array.sort. Violates CLAUDE.md no-silent-fallbacks. (test-analyzer high, rule-checker rule #11). Fix: `if (!Number.isFinite(value)) { throw new Error(...) }` (fail-loud per project rule).
4. `[TEST]` Add test for `NaN`, `Infinity`, negative, and >1.0 values to lock the fail-loud contract.
5. `[TEST]` `[RULE]` No wiring test — every getToneChips test exercises the function in isolation; `WorldPreview.test.tsx` always passes `axis_snapshot: {}` so the chip-render branch (`WorldPreview.tsx:139`) is never reached in any test. Violates CLAUDE.md "Every test suite needs a wiring test". (test-analyzer high, rule-checker rule #8/#16)
6. `[TEST]` `toneAxes.test.ts:48` "sorts chips by distance-from-neutral" test happens to have all-distinct distances; add one case with a tied distance to verify stable behavior. (test-analyzer medium)

**Dismissed:**
- `[TEST]` Axis names with spaces (test-analyzer low) — DISMISSED: axis names in world.yaml across all 6 live worlds follow snake_case convention (cosy, tech_level, mount_kasai-style); no realistic failure path. The string interpolation handles any value correctly regardless.
- `[TEST]` Live-world snapshot tests brittle to value drift (test-analyzer low) — DISMISSED: this is intentional canary behavior documented in the test file's comment block. World YAML retunes are a *design* event; the test failing on retune is the desired signal.

### Rule Compliance

TypeScript lang-review checklist (13 rules) + 3 CLAUDE.md additional rules, enumerated by rule-checker:

| Rule | Title | Instances | Violations | Notes |
|------|-------|-----------|------------|-------|
| 1 | Type safety escapes | 2 | 0 | No `as any`/`!`/`@ts-ignore` in diff |
| 2 | Generic/interface pitfalls | 3 | 0 | `Record<string, number>` is specific (not `any`); param not mutated |
| 3 | Enum anti-patterns | 0 | 0 | No enums |
| 4 | Null/undefined handling | 4 | 0 | No `||`/`??` issues; no optional chains |
| 5 | Module/declaration issues | 2 | 0 | Relative imports OK under bundler resolution |
| 6 | React/JSX | 0 | 0 | Neither file is `.tsx` |
| 7 | Async/Promise | 0 | 0 | No async |
| 8 | Test quality | 14 | 1 | **Missing wiring test** (CLAUDE.md additional rule) |
| 9 | Build/config | 0 | 0 | tsconfig not touched |
| 10 | Input validation | 1 | 0 | `getToneChips` not at API boundary — validation responsibility upstream |
| 11 | Error handling | 1 | 1 | **No NaN/non-finite guard** — silent failure mode |
| 12 | Performance/bundle | 2 | 0 | Standard ops only |
| 13 | Fix-introduced regressions | 1 | 0 | Removes prior `if (!labels) continue` silent skip — net win |
| 14 | No silent fallbacks (CLAUDE.md) | 1 | 0 | Old silent axis-skip removed; NaN-as-medium is rule-11 not rule-14 |
| 15 | No stubbing (CLAUDE.md) | 2 | 0 | Real implementation, real tests |
| 16 | Wiring test (CLAUDE.md) | 1 | 1 | **No production-path test** — duplicate of rule #8 finding |

## Reviewer Assessment

**Verdict:** REJECTED

| Tag | Severity | Issue | Location | Fix Required |
|-----|----------|-------|----------|--------------|
| [TEST] [RULE] | HIGH | `NaN` / non-finite axis values silently produce a "medium" chip and a `NaN` sort key, corrupting chip order. Violates CLAUDE.md no-silent-fallbacks and TypeScript lang-review rule #11. | `sidequest-ui/src/screens/lobby/toneAxes.ts:51-65` | Add `if (!Number.isFinite(value))` guard that throws loudly. Add test asserting the throw for `NaN`, `Infinity`, `-Infinity`. |
| [TEST] [RULE] | HIGH | No wiring test — every getToneChips test is in isolation, and all `WorldPreview.test.tsx` cases pass `axis_snapshot: {}` so the chip-rendering branch (`WorldPreview.tsx:139`) is never exercised end-to-end. Violates CLAUDE.md "Every test suite needs a wiring test" and TypeScript lang-review rule #8. | `sidequest-ui/src/screens/lobby/__tests__/WorldPreview.test.tsx` | Add one test that renders `<WorldPreview>` with a non-empty `axis_snapshot` (e.g. `{gravity: 0.9, comedy: 0.05}`) and asserts the chips appear in the DOM with the correct labels. |
| [DOC] | MEDIUM | JSDoc on `LOW_THRESHOLD` says "Below this" but code uses `<=`. JSDoc on `HIGH_THRESHOLD` says "Above this" but code uses `>=`. Contradicts the (correct) module-level docstring. | `sidequest-ui/src/screens/lobby/toneAxes.ts:30, 32` | Change both to "At or below/above this threshold...". |
| [TEST] | LOW | Sort-by-distance test has all-distinct distances; tied-distance behavior is untested. | `sidequest-ui/src/screens/lobby/__tests__/toneAxes.test.ts:48-54` | Add one case with two equal distances and assert via set membership that both chips appear (any order). |

**Data flow traced:** `world.yaml axis_snapshot → API /api/genres → WorldMeta.axis_snapshot (Record<string, number>) → WorldPreview.tsx:47 getToneChips(world.axis_snapshot) → ToneChip[] → rendered as <li> chips at WorldPreview.tsx:139`. The function is pure and downstream of validation-free deserialization, which makes the NaN concern realistic for any future world.yaml authoring mistake (missing axis value, typo).

**Pattern observed (good):** The fix correctly eliminates the prior `if (!labels) continue` silent fallback that dropped unrecognized axes. The new code processes every entry, matching CLAUDE.md's no-silent-fallbacks principle — except for the NaN case, which still falls through silently.

**Pattern observed (mixed):** The 6 live-world snapshot tests are an intentional drift canary — fragile by design. Documented adequately.

**Error handling:** Currently absent for non-numeric / non-finite values. The TypeScript type `Record<string, number>` does not guarantee finiteness at runtime; structural typing accepts `NaN` and `Infinity` as `number`. Project rule says fail loudly — throw instead of silently classifying as `medium`.

**Security analysis:** No security surface — pure transform over already-deserialized lobby metadata. No user input, no auth boundary.

**Hard questions:**
- Empty snapshot? ✓ tested, returns `[]`.
- Single axis? ✓ implicitly covered.
- All-tied distances? Untested (low-severity finding).
- Out-of-range numeric? Untested (high-severity finding).
- Non-numeric? Untested (high-severity finding).
- Huge snapshot (e.g. 50 axes)? Untested, but `Object.entries` + sort scales fine for realistic counts.

**Handoff:** Back to Dev for fixes.

## Reviewer Assessment (Pass 2)

**Verdict:** APPROVED

Pass-2 fixes (`46e2abf`) resolved all four Pass-1 findings: non-finite guard throws loudly with regex-matched error, wiring test renders `<WorldPreview>` with non-empty `axis_snapshot` and asserts chips in DOM, JSDoc on thresholds reads "At or below/above" matching `<=`/`>=`, tied-distance test asserts via set membership.

Subagent re-review surfaced one self-contradiction in the Pass-2 commit itself: the error message claimed `[0, 1]` range that the `Number.isFinite` guard does not enforce. Fixed in-place (`0ffb1f2`) — error message now matches the actual contract: "finite numbers."

**Subagent Results (Pass 2):**

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | 1455/1455 GREEN, type-check pass, lint clean |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | settings off |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | settings off |
| 4 | reviewer-test-analyzer | Yes | findings | 4 (2 high, 1 medium, 1 low) | 1 confirmed (lying error message — fixed in `0ffb1f2`); rest deferred as non-blocking |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (both high) | confirmed — same root cause as test-analyzer high; fixed in `0ffb1f2` |
| 6 | reviewer-type-design | Skipped | disabled | N/A | settings off |
| 7 | reviewer-security | Skipped | disabled | N/A | settings off |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | settings off |
| 9 | reviewer-rule-checker | Yes | findings | 2 (both pre-existing, not in diff) | dismissed — `WorldPreview.tsx:77` non-null assertion and `tsconfig.app.json:13 skipLibCheck` are pre-existing, not introduced by this story |

**All received:** Yes (4 returned + 5 disabled per settings)
**Total findings:** 1 confirmed and fixed in `0ffb1f2`; 3 deferred as out-of-scope follow-ups; 2 dismissed as pre-existing.

[TEST] [DOC] confirmed — lying error message resolved by `0ffb1f2`.
[EDGE] [SILENT] [TYPE] [SEC] [SIMPLE] [RULE] — covered by disabled subagents or rule-checker dismissal.

**Tests:** 1455/1455 passing post-fix.
**Branch:** `feat/58-3-tone-chips-generalize` HEAD `0ffb1f2`.

**Handoff:** To SM (Prospero) for finish phase.