---
story_id: "100-11"
jira_key: ""
epic: "100"
workflow: "tdd"
---
# Story 100-11: Phase 3 — React section components: POI, Cast, Timeline

## Story Details
- **ID:** 100-11
- **Title:** Phase 3 — React section components: POI, Cast, Timeline
- **Points:** 5
- **Priority:** p2
- **Jira Key:** (not used — SideQuest is Jira-free)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** sidequest-ui

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-09T07:15:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-09T07:15:00Z | - | - |

## Story Context

This story builds on merged stories:
- 100-3: Server Cast projection (is_projectable gate, R2 portrait resolved server-side)
- 100-4: Server POI projection (R2 landscape gate server-side)
- 100-5: Server Timeline projection (entries with temporal, sort_mode)
- 100-8: UI reference shell + NodeTree fallback + ReferenceDocument
- 100-9: Theme injector
- 100-10: Shared CartographyMap for the map section (JUST MERGED at b490dd2)

**Goal:** Build dedicated typed React components (POI, Cast, Timeline) that render the lore sections from the projection JSON. These are the rich sections that 100-8 deliberately left out of scope. Now each gets a purpose-built component with proper styling and functionality.

**Section dispatch:** The reference shell currently renders all sections generically. This story routes POI/Cast/Timeline section ids to their dedicated components and falls back to NodeTree for generic sections. Cast portraits and POI landscapes are R2 URLs resolved server-side — components just render them.

**Key files to study:**
- `src/types/reference.ts` — Projection shape (how server emits each section)
- `docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md` — Epic spec
- `sidequest-server/sidequest/lore/reference_projection.py` — Server projection logic

**Development setup:**
- Frontend tests: `just client-test`
- Lint: `just client-lint`
- Build: `just client-build` (tsc)
- NO database environment required (frontend-only story)

**Branch:** feat/100-11-react-section-components-poi-cast-timeline (off develop @ b490dd2)

## Known Develop Baseline Noise

These failures are NOT introduced by this story — they are pre-existing develop baseline noise:

1. **97-7/97-8 (ConfrontationOverlay.beatimpact.test.tsx — BeatEffect union):** client-build RED
2. **lobby-start-ws-open.test.tsx (flaky per 100-10 review):** May now be failing consistently

Capture baseline before starting TDD: run `just client-test` and `just client-build` to establish the known failures.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)

**Baseline (develop noise, NOT mine):**
- `src/__tests__/lobby-start-ws-open.test.tsx` — 1 timeout failure (documented flaky). Full suite at baseline: 1 failed / 1963 passed.
- client-build (tsc) RED on 97-7/97-8 ConfrontationOverlay (per session note). My new test files also fail tsc until GREEN (they import not-yet-created components/types) — that is expected RED, not new build noise.

**Test Files Written (4, all RED — components don't exist yet):**
- `src/components/reference/sections/__tests__/PoiSection.test.tsx` (6 tests)
- `src/components/reference/sections/__tests__/CastSection.test.tsx` (6 tests)
- `src/components/reference/sections/__tests__/TimelineSection.test.tsx` (8 tests)
- `src/components/reference/sections/__tests__/SectionDispatch.test.tsx` (5 dispatch + 2 wiring tests)

**RED confirmation:** `npx vitest run src/components/reference/sections/__tests__` → 4 files fail with "Failed to resolve import" for the missing production components (`PoiSection`, `CastSection`, `TimelineSection`, `SectionDispatch`). Clean RED — failure is missing impl, not test typos. Type-only imports are erased by esbuild so they don't mask the runtime resolution failure.

### Pinned contracts for Dev (GREEN)

Component files (Dev creates):
- `src/components/reference/sections/PoiSection.tsx` → `export function PoiSection({ section }: { section: PoiSectionData })`
- `src/components/reference/sections/CastSection.tsx` → `export function CastSection({ section }: { section: CastSectionData })`
- `src/components/reference/sections/TimelineSection.tsx` → `export function TimelineSection({ section }: { section: TimelineSectionData })`
- `src/components/reference/sections/SectionDispatch.tsx` → `export function SectionDispatch({ section }: { section: ReferenceSection })`

Types to add to `src/types/reference.ts` (shapes pinned from `reference_projection.py`):
- `PoiEntry = { slug: string; name: string; region: string | null; description: string | null; image_url: string }` (image_url ALWAYS present — POI gated on R2, never emitted with null image)
- `PoiSectionData = { id: "poi"; label: string; entries: PoiEntry[] }`
- `CastMember = { slug: string; name: string; role: string | null; appearance: string | null; portrait_url: string | null }` (portrait_url IS nullable — render no `<img>` when null, but keep the member)
- `CastSectionData = { id: "cast"; label: string; members: CastMember[] }`
- `TimelineEntry = { slug: string; name: string; summary: string; temporal: string | null }`
- `TimelineSectionData = { id: "timeline"; label: string; sort_mode: "sorted" | "authored_order"; preamble: string | null; entries: TimelineEntry[] }`
- `ReferenceSection` = union of `GenericSection | PoiSectionData | CastSectionData | TimelineSectionData`

Dispatch mechanism: `SectionDispatch` switches on `section.id` → poi/cast/timeline to dedicated components, else NodeTree (generic node-bearing). Unknown node-less section (e.g. "map", deferred to a later story) → render nothing, never throw. `ReferenceDocument.sections` prop widens `GenericSection[]` → `ReferenceSection[]` and renders each via `SectionDispatch` (replaces the 100-8 `section.node`-only filter that silently dropped poi/cast/timeline).

Key behavioral contracts:
- a11y: every POI landscape + Cast portrait `<img>` carries alt text naming the entity (`getByRole("img", { name })`).
- Null discipline: null role/appearance/region/description render gracefully, never leak the literal "null".
- Timeline: client RENDERS server array order verbatim — never re-sorts (server owns sort via `sort_mode`); undated entries already trail in the array.

**Handoff:** To Dev for implementation (task #2).

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings. TEA's pinned contracts matched the live server projection exactly; the 100-8 shell widened cleanly with no surprises.

## Design Deviations

No deviations logged at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Widened `LoreProjection.sections` type in addition to the `ReferenceDocument` prop**
  - Spec source: .session/100-11-handoff-red.md, Open Questions
  - Spec text: "ReferenceDocument `sections` prop widens `GenericSection[]` → `ReferenceSection[]`" (named only the prop)
  - Implementation: also widened `LoreProjection.sections` from `GenericSection[]` → `ReferenceSection[]`
  - Rationale: the live lore projection emits poi/cast/timeline sections and `ReferenceLorePage` passes `data?.sections` straight into the widened prop. Without widening the projection type, the dedicated sections would be mistyped as `GenericSection` at the fetch boundary. Type-correctness only, no behavior change. `RulesProjection.sections` left as `GenericSection[]` (assignable to the union; rules tier carries no dedicated sections).
  - Severity: minor
  - Forward impact: none — additive widening; existing consumers unaffected.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/types/reference.ts` — added PoiEntry/PoiSectionData, CastMember/CastSectionData, TimelineEntry/TimelineSectionData, ReferenceSection union; widened LoreProjection.sections
- `src/components/reference/sections/PoiSection.tsx` — dedicated POI renderer (R2 landscape img + alt, null-safe region/description)
- `src/components/reference/sections/CastSection.tsx` — dedicated Cast renderer (nullable portrait → no img, null-safe role/appearance)
- `src/components/reference/sections/TimelineSection.tsx` — dedicated Timeline renderer (verbatim server order, null-safe preamble/temporal)
- `src/components/reference/sections/SectionDispatch.tsx` — routes by section.id; NodeTree fallback for generic; node-less unknown → nothing
- `src/screens/reference/ReferenceDocument.tsx` — widened prop to ReferenceSection[], renders each via SectionDispatch (removes 100-8 node-only filter)

**Tests:** 27/27 new section tests passing (GREEN). Full suite 1990 passed / 1 pre-existing flake (lobby-start-ws-open).
**Branch:** feat/100-11-react-section-components-poi-cast-timeline (pushed)

**Gate results:**
- client-test: 1 failed (lobby-start-ws-open.test.tsx — pre-existing 97-8/100-10 flake), 1990 passed. All 27 new tests pass.
- client-lint: 0 errors, 1 warning (pre-existing App.tsx exhaustive-deps).
- client-build (tsc): errors confined to ConfrontationOverlay.beatimpact.test.tsx (pre-existing 97-7/97-8 BeatEffect union). Zero errors in new files.

**Handoff:** To Reviewer (task #3).

## Reviewer Assessment

**Verdict:** APPROVED
**Reviewer:** reviewer (yellow), peloton-100-11
**Diff:** merge-base b490dd2 → HEAD 8a04b82 (10 files, +733/-17), sidequest-ui only

**Data flow traced:** server `build_{poi,cast,timeline}_section` dict → projection JSON → `ReferenceSection` typed union (`src/types/reference.ts`) → `ReferenceDocument.sections` → `SectionDispatch` (route by `id`) → dedicated component renders only allowlisted fields. Safe end-to-end.

**Shape fidelity (cross-checked vs reference_projection.py):** VERIFIED. PoiEntry/CastMember/TimelineEntry/section shapes match the server verbatim. Correctly distinguishes POI `entries` vs Cast `members` (a real confusion trap — dev got it right). `image_url` non-null; `portrait_url`/`temporal`/`preamble`/`region`/`description`/`role`/`appearance` nullable and handled. No field silently dropped.

**Section dispatch:** GENUINE. poi/cast/timeline → dedicated; node-bearing default → NodeTree (wrapped in the same labelled `<section>` the 100-8 shell emitted); node-less unknown (e.g. deferred "map") → `null`, never throws. The `as` casts are necessary because `GenericSection.id` is `string` (non-literal) so TS can't discriminate the union on `id` — acceptable, the only practical approach.

**Wiring:** VERIFIED. `ReferenceDocument` widened `GenericSection[]`→`ReferenceSection[]`, removed the 100-8 `.filter(section.node)` that silently dropped poi/cast/timeline. Genuine integration test renders the production `ReferenceDocument` with a mixed projection and asserts dedicated renderers fire AND a regression test proves the 100-8 drop is fixed. Satisfies the "every test suite needs a wiring test" rule.

**Keeper safety (defense-in-depth):** VERIFIED. Components read only named allowlist fields — no `{...spread}`, no `Object.keys/entries` enumeration over payloads. A `_`-prefixed/keeper field cannot surface because nothing iterates unknown keys. Generic path is server-firewalled (NodeTree).

**a11y / null contracts:** VERIFIED. Every `<img>` carries `alt` (entry/member name). Nullable fields gated `!== null` → literal "null" never renders. Null portrait → member shown, no `<img>`. Timeline renders server order verbatim (no client `.sort()`), honoring `sort_mode`.

**Observations (LOW, non-blocking, no action required):**
- Nullable handling uses `!== null` rather than truthiness — correct and more precise given the server contract is `string | null` (never `undefined`/`""` for these fields).
- POI `name` can be empty string server-side (`str(entry.get("name",""))`), yielding `alt=""` (decorative). Vanishingly unlikely for a real POI; not worth blocking.

**Gates (provenance via merge-base diff, no develop checkout):**
- client-test: 1990 passed / 1 failed. The failure (`lobby-start-ws-open.test.tsx`, 97-8) is NOT in this branch's diff — pre-existing develop noise. All 27 new section tests pass.
- client-lint: 0 errors (1 pre-existing `App.tsx` warning, untouched).
- client-build (tsc -b): errors ONLY in `ConfrontationOverlay.beatimpact.test.tsx` (last touched by 73-4 commit 78cd19b, not this branch) — pre-existing 97-7. Zero new build errors.
- **Net: ZERO new test/lint/build failures introduced by 100-11.**

**Deviation audit:** No deviations logged; none observed. Implementation matches TEA's pinned contracts exactly.

**Handoff:** Merging PR #362 to develop; to SM for finish-story.
