---
story_id: "93-3"
jira_key: ""
epic: "93"
workflow: "tdd"
---
# Story 93-3: Character-sheet History section — origin block

## Story Details
- **ID:** 93-3
- **Jira Key:** (not in use)
- **Workflow:** tdd
- **Stack Parent:** 93-2
- **Branch:** feat/93-3-character-sheet-history-origin-block
- **Branch Strategy:** gitflow (feat/{STORY_ID}-{SLUG})

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T21:26:43Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T21:05:26Z | 2026-06-10T21:07:14Z | 1m 48s |
| red | 2026-06-10T21:07:14Z | 2026-06-10T21:14:47Z | 7m 33s |
| green | 2026-06-10T21:14:47Z | 2026-06-10T21:18:59Z | 4m 12s |
| review | 2026-06-10T21:18:59Z | 2026-06-10T21:26:43Z | 7m 44s |
| finish | 2026-06-10T21:26:43Z | - | - |

## Sm Assessment

**Story:** Character-sheet History section — origin block. UI-only (sidequest-ui), 3pts, tdd/phased.

**Dependency:** Depends on 93-2, which is COMPLETE (commit 0ca19b51 — durable creation_answers provenance + snapshot exposure, server PR #808 merged). The `creation_answers` payload is now live on the character snapshot, so this story's data source exists. No blocking dependency remains.

**Scope (well-bounded):** Add a collapsible/labelled "History" section to `CharacterSheet.tsx` that reads `creation_answers` and lists, per scene, the prompt + the player's answer — verbatim words for freeform, chosen label for selections. Scenes flagged `archetype_inferred` get an "inferred from your words" badge. Type `creation_answers` in `payloads.ts` (CharacterSheetData). Graceful empty render on legacy saves missing the field.

**Key constraint for TEA/Dev:** Build the History *container/heading* to host more than the origin block (93-4 attaches lore there later) but render ONLY the origin block now — **no lore stubs or placeholder rows**. This is a structural-readiness requirement, not a "stub it out" license. Watch the No-Stubbing principle here.

**Audience:** Makes chargen provenance legible in the player UI (Sebastien/Jade, mechanics-first) and gives narrative-first players (James) their own words back. This is a player-facing surface — not GM/dev observability.

**Refs:** `sidequest-ui/CharacterSheet.tsx` (~101-242), `payloads.ts` CharacterSheetData (~22-88).

**Routing:** Phased tdd → hand off to TEA (Amos) for RED. Component test must assert History/Origin rows render from a `creation_answers` fixture including the inferred badge (AC6).

## TEA Assessment

**Tests Required:** Yes
**Reason:** Player-facing render + a wire→sheet mapping change. Both need coverage; no chore bypass.

**Test Files:**
- `sidequest-ui/src/components/__tests__/CharacterSheet.test.tsx` — added describe block "Story 93-3: History section (origin block)" (9 tests). Covers AC-1 (History+Origin render, per-scene prompt+answer), AC-2 (freeform verbatim vs preset label), AC-3 (inferred badge gated on `archetype_inferred`, incl. none-inferred and missing-flag cases), AC-4 (graceful — no History section when `creation_answers` absent/empty), AC-5 (origin-only — no premature lore section/stub rows), AC-6 (App-shaped wiring incl. badge).
- `sidequest-ui/src/lib/__tests__/partyStatusMapping.test.ts` — added describe block "creation_answers provenance (story 93-3)" (4 tests, 3 RED + 1 already-green guard). Proves `toCharacterSheetData` threads `sheetFacet.creation_answers` → `CharacterSheetData`, preserves per-entry `archetype_inferred`, is NOT identity-gated (carried in SP and MP — unlike `player_id`), and fabricates nothing on a legacy facet (no-fabrication guard already passes against undefined).

**Tests Written:** 13 tests covering 6 ACs (12 RED + 1 standing no-fabrication guard).
**Status:** RED (verified by testing-runner, run 93-3-tea-red): 12 new tests fail on clean assertions (`character-history` testid absent; `creation_answers` undefined on the mapper output); 40 pre-existing tests pass — no regression. No compile/collection errors — the `import type { CreationAnswer }` is stripped by esbuild as intended.

### Data shape (for Dev)
Server `CreationAnswer` (sidequest-server `protocol/models.py:403`): `{ scene_id: str, prompt: str, kind: "choice"|"freeform", value: str, archetype_inferred: bool = false }`. It rides `CharacterSheetDetails.creation_answers` (views.py:393), nested in the PARTY_STATUS member's `sheet` facet. `value` holds the chosen LABEL for `choice` and the verbatim text for `freeform` — the component renders `value` either way; the `kind` distinction is provenance, not a render branch.

### Implementation map (3 connections — wire it all)
1. `payloads.ts` — define `interface CreationAnswer` (AC-4 "typed in payloads.ts"). Tests import the type from `@/types/payloads`; the tsc/build gate enforces the location.
2. `CharacterSheet.tsx` — add `creation_answers?: CreationAnswer[]` to `CharacterSheetData`; render the History/Origin section (testids: `character-history`, `character-origin`, `origin-inferred-badge`). Render the section ONLY when `creation_answers` is present and non-empty. **No lore stub** (AC-5; No-Stubbing principle) — the container just needs to be structured to host more later.
3. `partyStatusMapping.ts` — `toCharacterSheetData` must read `sheetFacet.creation_answers` and set it on the returned object, UNGATED by `isMultiplayer`. Use `??`/`Array.isArray` guards (not `||`) per the TS lang-review null/undefined rule.

### Rule Coverage (TypeScript lang-review checklist)
| Rule | Test(s) | Status |
|------|---------|--------|
| #4 null/undefined — graceful optional field, no fabrication | `AC-4: ...absent`, `AC-4: ...empty array`, mapper `yields an empty (falsy) creation_answers...` | RED / standing-green guard |
| #6 React/JSX — list rendering of per-scene rows (stable, no index-key reorder hazard) | `AC-1: lists each chargen scene's prompt and the player's answer` | RED — note for Dev: key rows by `scene_id`, not array index |
| #8 test quality — meaningful assertions, no vacuous passes | self-check below | done |

**Rules checked:** 3 of the applicable lang-review rules have test coverage (the change is a narrow render+map; type-safety/async/security rules don't apply to this diff).
**Self-check:** Reviewed all 13 tests for vacuous assertions — every test asserts a concrete element/value or a counted badge set. The one standing-green mapper test (`yields an empty...`) is a no-fabrication guard, not vacuous: it fails if Dev defaults `creation_answers` to a non-empty value. 0 vacuous tests found.

**Handoff:** To Dev (Naomi) for GREEN.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The story's file refs are slightly stale — it cites `payloads.ts CharacterSheetData ~22-88`, but `CharacterSheetData` actually lives in `sidequest-ui/src/components/CharacterSheet.tsx:22-88`; `payloads.ts` is the home for the wire-level `CreationAnswer` type. Tests are written to that reality (type in `payloads.ts`, field on `CharacterSheetData` in `CharacterSheet.tsx`). Affects `sprint/context/context-story-93-3.md` (no action needed — noted so Dev isn't confused by the ref). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation. TEA's implementation map (3 connections: payloads.ts type, CharacterSheet.tsx field+render, partyStatusMapping.ts thread) matched the code exactly; all data shapes were as described.

### Reviewer (code review)
- **Improvement** (non-blocking): `payloads.ts:9` file-header JSDoc still reads "Mirrors sidequest-protocol (Rust) payload structs" — stale post-ADR-082 (backend is Python). Pre-existing (not introduced by 93-3), but the new `CreationAnswer` block sits directly under it and its own "Mirrors sidequest-server protocol" line is the correct framing. Affects `sidequest-ui/src/types/payloads.ts` (update the file header to "sidequest-server (Python)" in a future sweep). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): wire→sheet casts in `toCharacterSheetData` assert element types without runtime field validation (`as CreationAnswer[]`, matching the pre-existing `abilities`/`class_moves`/`injury_tags` casts). No Zod/runtime-schema layer exists in this mapper by design; if one is ever introduced, validate all sheet-facet arrays at the boundary together. Affects `sidequest-ui/src/lib/partyStatusMapping.ts` (boundary validation, whole-mapper concern — not a 93-3 regression). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **TEA: "No deviations from spec."** → ✓ ACCEPTED by Reviewer: the RED tests track the ACs literally (testids, badge gating, graceful absent/empty, no-lore-stub). No spec divergence.
- **Dev: "No deviations from spec."** → ✓ ACCEPTED by Reviewer: implementation matches the AC and TEA's 3-connection map exactly — verified each of payloads.ts type, CharacterSheet.tsx render, partyStatusMapping.ts thread against the spec. No undocumented divergence found.
- No undocumented deviations spotted during review.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/types/payloads.ts` — added the canonical `CreationAnswer` interface (`scene_id`, `prompt`, `kind: "choice"|"freeform"`, `value`, optional `archetype_inferred`), mirroring the server protocol type (AC-4 "typed in payloads.ts").
- `sidequest-ui/src/components/CharacterSheet.tsx` — imported `CreationAnswer`, added `creation_answers?: CreationAnswer[]` to `CharacterSheetData`, and rendered the History section (`character-history`) with the Origin block (`character-origin`). One row per scene, keyed by `scene_id` (not array index, per TEA rule #6); renders `value` for both kinds; `origin-inferred-badge` gated on `answer.archetype_inferred`. Section renders ONLY when `creation_answers` is present and non-empty (AC-4 graceful). No lore stub (AC-5).
- `sidequest-ui/src/lib/partyStatusMapping.ts` — `toCharacterSheetData` now threads `sheetFacet.creation_answers` (Array.isArray guard, no fabrication), UNGATED by `isMultiplayer` (provenance is the player's own, unlike `player_id`).

**Tests:** 52/52 passing (GREEN) — 13 new (9 CharacterSheet + 4 mapper), 39 pre-existing, no regression. `tsc --noEmit` clean. Lint clean.
**Branch:** feat/93-3-character-sheet-history-origin-block (pushed)

**Handoff:** To next phase (review).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (52 green, tsc clean, eslint clean, 0 smells, additions-only) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (4 low, 1 high-conf-but-benign) | confirmed 1 (LOW), dismissed 3, deferred 1 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (line 9 stale ×2, line 31 server-default) | confirmed 1 (LOW pre-existing), dismissed 2 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 (1 high boundary-cast, 1 med key, 1 high wiring-doctrine, 1 high test-form) | confirmed 1 (LOW), dismissed 3 |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 2 confirmed (both LOW, non-blocking), 8 dismissed (with rationale), 2 deferred (delivery findings for future polish)

### Finding dispositions

- **[RULE] `as CreationAnswer[]` boundary cast w/o element validation** (partyStatusMapping.ts:95, high conf) → CONFIRMED **[LOW]**. Identical to pre-existing `abilities`/`class_moves`/`injury_tags` casts (lines 73–74, 89); no runtime-schema layer exists in this mapper by design. Rendered as React text → no XSS. Not introduced by this diff (extends an established pattern). No project rule mandates runtime validation here. Non-blocking; recorded as a whole-mapper delivery finding.
- **[RULE] `key={answer.scene_id}` not type-enforced unique** (CharacterSheet.tsx:258, med conf) → DISMISSED. scene_id is the *correct* stable key — the rule forbids `key={index}`, and Dev did the opposite. Server records each scene once (`models.py:403` docstring: "Only ANSWERED scenes are recorded"), so uniqueness holds. Theoretical server-bug collision is out of scope for a read-only provenance list. `[VERIFIED]` good.
- **[RULE] no App.tsx-level integration test (wiring doctrine)** (high conf) → DISMISSED. `toCharacterSheetData` IS the wire→sheet seam, extracted from App.tsx precisely to be the testable wiring point; `partyStatusMapping.test.ts` exercises it directly (the same pattern used for `player_identity`/67-6 and `player_id`/56-1). App.tsx:1089 calls it and `setCharacterSheet(built)` — verified. "Every Test Suite Needs a Wiring Test" is satisfied by the mapper suite.
- **[RULE]/[TEST] redundant `as CreationAnswer` cast in test fixture** (CharacterSheet.test.tsx:487, high conf) → CONFIRMED **[LOW]**. Cast is vacuous (literal already satisfies the optional-field interface); harmless, slightly sloppy. Non-blocking style nit.
- **[TEST] `expect(built.creation_answers ?? []).toEqual([])` loose** (partyStatusMapping.test.ts:194, high conf) → DEFERRED **[LOW]**. `toBeUndefined()` would be tighter, but `[]` and `undefined` produce identical UI (component guards `&& length > 0`), so the impl is verified correct and the weakness is benign. Recorded for future polish.
- **[TEST] AC-2 split / no negative assertion that `kind`/`scene_id` don't render** (low) → DISMISSED. AC-2 asserts the `value` strings render; the kind-vs-value distinction is provenance, not a render branch. Acceptable coverage.
- **[TEST] AC-6 wiring test doesn't assert badge text** (low) → DISMISSED. AC-3 already locks the badge text; AC-6 asserts badge count from an App-shaped fixture. Adequate.
- **[TEST] SP test doesn't assert archetype_inferred preserved** (med) → DISMISSED. There is no SP/MP branch for `creation_answers` (single unconditional code path), so the flag cannot be stripped in SP but not MP. MP test (line 153) covers flag survival.
- **[DOC] `payloads.ts:9` "Mirrors sidequest-protocol (Rust)" stale** (high conf) → CONFIRMED **[LOW]** pre-existing. Not introduced by 93-3 (line 9 untouched); recorded as a delivery finding for a future header sweep.
- **[DOC] `payloads.ts:31` "server defaults it false" vs optional type** (high conf) → DISMISSED. I verified the server source: `protocol/models.py:403` declares `archetype_inferred: bool = False` with `extra: forbid` — the field is **always present** on the wire, so the comment is factually accurate. The UI's optional `?:` is defensive belt-and-suspenders, not a contradiction.
- **[DOC] `partyStatusMapping.ts` not-identity-gated comment** → `[VERIFIED]` accurate — code threads the field unconditionally; comment matches.

## Reviewer Assessment

**Verdict:** APPROVED

A small, clean, additive UI change (3 production files, +58 lines, 0 deletions) that wires the durable `creation_answers` provenance (story 93-2) onto a new player-facing History/Origin section. No Critical or High findings. The two confirmed findings are both LOW (a cosmetic redundant test cast and a pre-existing stale file header); the substantive subagent flags resolve to verified-correct or accepted established-pattern.

### Rule Compliance (TypeScript lang-review + project rules)

- **#1 Type-safety escapes** — VERIFIED clean. No `as any`, no `as unknown as T`, no `@ts-ignore`, no `!` non-null. Both new `import type` lines are type-only. The one test cast (line 487) is redundant-but-safe (LOW).
- **#4 Null/undefined** — VERIFIED. `data.creation_answers && data.creation_answers.length > 0` is the correct exists-and-non-empty guard; `{answer.archetype_inferred && …}` correctly treats `undefined`/`false` as no-badge (matches the verified server default). `Array.isArray(...) ? ... : undefined` is the right narrowing in the mapper. No `||`-on-falsy-valid bugs introduced.
- **#5 Module/declaration** — VERIFIED. `CreationAnswer` is a direct named `export interface` at its declaration site; all consumers use `import type`. No re-export-without-`export type`, no runtime-value type-import.
- **#6 React/JSX** — VERIFIED. List keyed by stable `scene_id` (not index — the correct call per TEA rule #6). No `useEffect`/dep hazards introduced. No `dangerouslySetInnerHTML`: `prompt`/`value` render as escaped React text children.
- **#10 Security / input validation** — `[SEC]` (subagent disabled — assessed manually). Player-authored freeform `value` and `prompt` render as React **text nodes**, auto-escaped → no XSS (CWE-79). The `as CreationAnswer[]` cast lacks element-level runtime validation, but this is the established mapper pattern (no Zod layer by design) and the rendered fields coerce safely; recorded as non-blocking delivery debt.
- **No Silent Fallbacks** — VERIFIED. The empty/absent → no-History behavior is the *documented, AC-required* graceful path (AC-4), not a masked misconfiguration. Returning `undefined` on a legacy facet is correct, not a silent substitution.
- **No Stubbing** — VERIFIED. AC-5 explicitly tested: no `history-lore` testid, no "lore"/"coming soon"/"placeholder" text. The container hosts only the Origin block; structural-readiness without skeleton code.
- **Wiring** — VERIFIED end-to-end: server `views.py:393` emits `creation_answers` on the sheet facet → `App.tsx:1089` `toCharacterSheetData(rawLocal, sheetFacet, …)` → `setCharacterSheet(built)` → component renders. `partyStatusMapping.test.ts` covers the wire→sheet seam (the "Every Test Suite Needs a Wiring Test" requirement).

### Subagent dispatch tags

- `[EDGE]` — subagent disabled; assessed manually: legacy-absent, empty-array, missing-flag, none-inferred, and App-shaped paths all covered by tests and verified. No unhandled boundary.
- `[SILENT]` — subagent disabled; assessed manually: no swallowed errors; the `undefined` return on absent facet is the AC-required graceful path, not a silent fallback (no try/catch introduced).
- `[TEST]` — test-analyzer: 1 LOW confirmed (redundant cast 487), 1 LOW deferred (`?? []` loosening, benign), 3 dismissed. Badge gating and no-stub guards are meaningfully asserted.
- `[DOC]` — comment-analyzer: 1 LOW confirmed pre-existing (stale Rust header, line 9), "server defaults false" dismissed as verified-accurate.
- `[TYPE]` — subagent disabled; assessed manually: `CreationAnswer` uses concrete fields + a `'choice'|'freeform'` string union (correct over enum); optional `archetype_inferred?` matches the defensive UI handling. Sound.
- `[SEC]` — subagent disabled; assessed manually: no XSS (text render), no secrets, no auth surface. Boundary-cast note is non-blocking accepted debt.
- `[SIMPLE]` — subagent disabled; assessed manually: minimal, no over-engineering, no dead code. The carried-but-unrendered `kind` field is wire-contract provenance, not dead code.
- `[RULE]` — rule-checker: 1 LOW confirmed (boundary cast, accepted pattern), key/wiring/test-form findings dismissed with evidence above.

### Devil's Advocate

Argue this is broken. **Malicious/garbage wire data:** the server is the only writer of `creation_answers`, but suppose it sends `{scene_id: null, prompt: 42, kind: "garbage", value: null}`. The `as CreationAnswer[]` cast won't catch it. What actually renders? `answer.prompt` (42) coerces to the text "42"; `null` value renders as nothing; `key={null}` would draw a React key warning. Ugly, but not a crash and not an injection — React escapes all of it, so there's no XSS even if `value` were `"<img onerror=…>"`. The blast radius is cosmetic, and the producer is trusted server code mirroring a Pydantic `extra: forbid` model. **Confused user:** a player with a long freeform answer — does it overflow? It renders in a `<p>` with narrative font; no truncation, but that's consistent with the Backstory block above it, so no new layout regression. **Duplicate scene_ids:** would collide React keys — but the server emits one answer per answered scene, so this needs a server bug to trigger, and the worst case is a reconciliation warning on a static, non-reordering list. **Empty vs absent:** could a save carry `creation_answers: []` and wrongly show an empty History shell? No — the `&& length > 0` guard suppresses it, and AC-4 tests both shapes. **The badge inverts?** `{archetype_inferred && …}` — if the server ever sent the string `"false"`, that's truthy and would wrongly badge; but the verified model types it `bool`, and the wire is JSON `true`/`false`, not strings. **Worst honest finding:** the boundary cast trusts the server's element shape. That is real but pervasive across the whole mapper and unchanged in risk by this diff — it belongs in a mapper-wide validation initiative, not a block on a 3-point provenance render. Nothing here rises to High.

**Data flow traced:** server `Character.creation_answers` → `views.py:393` sheet facet → WS PARTY_STATUS → `App.tsx:1089` `toCharacterSheetData` (Array.isArray-guarded thread, MP-ungated) → `setCharacterSheet` → `CharacterSheet` History/Origin render (per-scene rows, badge gated on `archetype_inferred`). Safe: player text is React-escaped; absent/empty degrades to no-section.
**Pattern observed:** wire→sheet mapping kept in the pure, unit-tested `toCharacterSheetData` seam (partyStatusMapping.ts:94-96) rather than inline in App.tsx — consistent with the 56-1/67-6 precedent.
**Error handling:** legacy/absent facet → `undefined` → graceful no-render (AC-4, tested). No throw paths introduced.

**Handoff:** To SM for finish-story (Camina Drummer).