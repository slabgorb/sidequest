# Story 25-6: Chrome archetypes — genre-themed panel styling via CSS custom properties

**Status:** in_progress
**Phase:** finish
**Workflow:** tdd
**Repos:** ui,content
**Branch:** feature/25-6-chrome-archetypes
**Jira:** (none — personal project)

## Acceptance Criteria

1. Define a `ChromeArchetype` type that maps genre packs to one of three archetype families: `parchment`, `terminal`, `rugged`
2. Each archetype sets CSS custom properties (colors, fonts, borders, textures) based on genre pack `theme.yaml`
3. Genre pack `theme.yaml` values are loaded and applied as CSS custom properties on the game layout root
4. Switching genre packs dynamically updates the chrome without page reload
5. All three archetype mockups (parchment-low-fantasy, terminal-neon-dystopia, rugged-road-warrior) are representable via the custom property system
6. Wiring test: verify chrome is applied end-to-end from genre pack selection → WebSocket → UI theming

## Sm Assessment

**Ready for RED phase.** Dependencies satisfied (25-2, 25-4 both done). Genre pack theme.yaml files exist across all 11 packs with color palette and font data. Three HTML mockups define the target archetypes. Branch `feature/25-6-chrome-archetypes` created on sidequest-ui from develop.

**Routing:** → Fezzik (TEA) for red phase — write failing tests for chrome archetype type, CSS custom property injection, and genre→archetype mapping.

## Technical Approach

- Genre packs already have `theme.yaml` with color palette + `web_font_family`
- Three HTML mockups exist at `docs/mockups/` showing the target look per archetype
- Need to extract the CSS custom property pattern from mockups into a reusable archetype system
- Content repo: may need `chrome_archetype` field in `theme.yaml` to declare which family
- UI repo: `useTheme` or similar hook to consume genre theme data from WebSocket and set CSS vars on `:root`
- The character panel (25-2, done) and GameLayout (25-4, done) are the consumers

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

## Delivery Findings

### TEA (test design)
- **Improvement** (non-blocking): `useGenreTheme` currently injects raw CSS from server and bridges to Tailwind tokens. The chrome archetype system should layer *below* this — setting structural properties (fonts, borders, radii) that the genre color injection sits on top of. Dev should ensure `useChromeArchetype` runs before or alongside `useGenreTheme`, not after.
  Affects `src/hooks/useGenreTheme.ts` (ordering with new archetype hook).
  *Found by TEA during test design.*

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core type system and CSS injection hook need coverage

**Test Files:**
- `src/hooks/__tests__/useChromeArchetype.test.ts` — chrome archetype mapping, properties, hook, and wiring

**Tests Written:** 22 tests covering 6 ACs
**Status:** RED (failing — ready for Inigo Montoya)

### Test Strategy

| Area | Tests | What's Covered |
|------|-------|----------------|
| Genre→archetype mapping | 12 | All 11 genre packs + unknown slug throws |
| ARCHETYPE_PROPERTIES | 8 | All three archetypes have required CSS props, font family patterns match archetype identity, distinct border-radius values |
| useChromeArchetype hook | 7 | Sets data-archetype attr, injects CSS props, switches dynamically, cleans up old props, returns archetype value |
| Wiring | 2 | Archetype doesn't clobber genre colors, data-archetype enables CSS selector targeting |

### Rule Coverage

No lang-review rules file found for this project. Tests enforce:
- No silent fallbacks (unknown genre throws, not defaults)
- No stubs (all 11 genres mapped, all 3 archetypes defined)
- Wiring verification (archetype + genre colors coexist)

**Self-check:** 0 vacuous tests found. All assertions check specific values or patterns.

**Handoff:** To Inigo Montoya (Dev) for implementation

### Dev (implementation)
- No upstream findings during implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/hooks/useChromeArchetype.ts` — ChromeArchetype type, genre→archetype mapping, ARCHETYPE_PROPERTIES config, useChromeArchetype hook

**Tests:** 28/28 passing (GREEN)
**Branch:** feature/25-6-chrome-archetypes (pushed)

**Pre-existing failures:** 12 test files with 65 failures (PTT, voice signal, audio mixer) — all unrelated to this story.

**Handoff:** To next phase (verify/review)

### TEA (test verification)
- No upstream findings during test verification.

## TEA Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed — 28/28 tests passing

### Simplify Report

**Teammates:** inline (2 files, 76 LOC implementation — subagent fan-out not warranted)
**Files Analyzed:** 2

| Analysis | Status | Findings |
|----------|--------|----------|
| Reuse | clean | prevKeysRef cleanup pattern parallels ThemeProvider but operates on different property sets — no extraction needed |
| Quality | clean | Explicit error on unknown genre, React hook conventions followed, clean types |
| Efficiency | clean | No over-engineering — pure mapping, static config, single useEffect |

**Applied:** 0 fixes
**Flagged for Review:** 0 findings
**Noted:** 0 observations
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** 28/28 tests passing
**Handoff:** To Westley (Reviewer) for code review

### Reviewer (review)
- No deviations from spec.

### Reviewer (review)
- **Gap** (blocking): `useChromeArchetype` had zero non-test consumers — violated CLAUDE.md wiring principle. Fixed by wiring into `App.tsx` with `currentGenre` state tracking. Hook signature widened to `string | null` for pre-connection no-op.
  Affects `src/App.tsx` and `src/hooks/useChromeArchetype.ts`.
  *Found by Reviewer during review.*

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 28/28 tests pass, tsc clean | N/A |
| 2 | reviewer-edge-hunter | Yes | 1 finding | null genre slug path needs safe handling | Fixed: widened to `string \| null` |
| 3 | reviewer-type-design | Yes | clean | Types are tight — union type + Record mapping | N/A |
| 4 | reviewer-simplifier | Yes | clean | 76 LOC, no dead code, no over-engineering | N/A |
| 5 | reviewer-rule-checker | Yes | clean | No lang-review rules for this project, CLAUDE.md rules checked inline | N/A |
| 6 | reviewer-silent-failure-hunter | Yes | clean | No swallowed errors — unknown genre throws, null handled explicitly | N/A |

All received: Yes

## Reviewer Assessment

**Decision:** APPROVE (after wiring fix)

### Findings

| # | Severity | Category | Tag | Description | Resolution |
|---|----------|----------|-----|-------------|------------|
| 1 | **blocking** | wiring | [RULE] | `useChromeArchetype` not called from any production code — violates CLAUDE.md wiring principle | Fixed: wired into `App.tsx`, added `currentGenre` state |
| 2 | minor | react-hygiene | [TYPE] | useEffect missing cleanup for `data-archetype` attr on unmount | Accepted: root-level hook, app never unmounts |
| 3 | clean | silent-failure | [SILENT] | No swallowed errors — unknown genre throws, null handled with explicit early return | N/A |
| 4 | note | scope | [RULE] | No content repo changes despite `repos: ui,content` | Accepted: mapping hardcoded in TS is correct for 11 deterministic entries |

### Wiring Verification

- `useChromeArchetype` imported in `App.tsx:10` ✓
- Called at `App.tsx:257` with `currentGenre` state ✓
- `currentGenre` set in `handleConnect` ✓
- `currentGenre` initialized from `sessionStorage` for HMR recovery ✓
- Hook returns `null` when no genre selected (no silent fallback) ✓
- TypeScript compiles clean ✓
- 28/28 tests still GREEN ✓

**Handoff:** To Vizzini (SM) for finish