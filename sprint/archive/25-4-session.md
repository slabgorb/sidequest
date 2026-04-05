---
story_id: "25-4"
epic: "25"
workflow: "tdd"
---
# Story 25-4: Rewire GameLayout — CharacterPanel integration, hotkeys, slash commands

## Story Details
- **ID:** 25-4
- **Epic:** 25 (UI Redesign — Character Panel, Layout Modes, Chrome Archetypes)
- **Workflow:** tdd
- **Repository:** sidequest-ui
- **Branch:** feat/25-4-rewire-gamelayout-charpanel
- **Points:** 5
- **Priority:** p1
- **Status:** in-progress
- **Stack Parent:** 25-2 (done)

## Context

Story 25-2 built the CharacterPanel as a persistent docked sidebar. Story 25-3 extracted SettingsOverlay from OverlayManager, making settings management independent.

Currently, game state overlays (character, inventory, map, journal, knowledge) are temporarily unreachable because OverlayManager is no longer wrapping GameLayout. This story rewires GameLayout to:

1. Integrate CharacterPanel as a persistent sidebar (single-player view)
2. Render game state overlays directly in GameLayout (character, inventory, map, journal, knowledge)
3. Wire hotkeys (C/I/M/J/K) directly in GameLayout for overlay toggling
4. Wire slash commands (/character, /inventory, /map, /journal, /knowledge) to overlay state
5. Delete OverlayManager.tsx after this story

**Key architectural principle:** OverlayManager's hotkey and slash-command logic moves into GameLayout. The component becomes a container that directly manages both persistent UI (CharacterPanel sidebar) and modal overlays (game state details).

## Acceptance Criteria

### AC-1: CharacterPanel integrated as persistent sidebar
- CharacterPanel visible in GameLayout (left side, desktop+tablet only)
- Takes `character` prop from characterSheet data
- Takes optional `inventory` prop
- Collapse/expand state persisted to localStorage
- Responsive: hidden on mobile, visible on desktop/tablet

### AC-2: Game state overlays rendered directly in GameLayout
- Character, inventory, map, journal, knowledge overlays render as modals
- Modal backdrop + close button
- No OverlayManager wrapper component
- Rendered directly as conditional JSX in GameLayout

### AC-3: Hotkeys (C/I/M/J/K) wired in GameLayout
- C key toggles character overlay (if characterSheet exists)
- I key toggles inventory overlay (if inventoryData exists)
- M key toggles map overlay (if mapData exists)
- J key toggles journal overlay (if journalEntries exists)
- K key toggles knowledge overlay (if knowledgeEntries exists)
- Escape key closes active overlay
- Hotkeys not triggered when focus is on input/textarea/contenteditable

### AC-4: Slash commands wired to overlay state
- /character toggles character overlay
- /inventory toggles inventory overlay
- /map toggles map overlay
- /journal toggles journal overlay
- /knowledge toggles knowledge overlay
- /settings toggles settings overlay (already wired via SettingsOverlay)
- Called from InputBar → InputEvent handler in GameStateProvider
- Overlay state updates reflect the command result

### AC-5: OverlayManager.tsx can be deleted
- No remaining references to OverlayManager in production code
- All hotkey + slash-command logic migrated to GameLayout
- GameStateProvider no longer wraps GameLayout with OverlayManager

## Implementation Strategy

**Phase 1 (RED):** Write acceptance tests for GameLayout overlay rewiring
- CharacterPanel sidebar integration
- Overlay modal rendering
- Hotkey handling (C/I/M/J/K/Escape)
- Slash command routing
- Integration test: hotkey + modal, slash command + modal

**Phase 2 (GREEN):** Implement GameLayout rewiring
- Move hotkey logic from OverlayManager into GameLayout
- Add game state overlay modal rendering
- Integrate CharacterPanel sidebar
- Wire slash commands via InputBar callback
- Verify OverlayManager has no remaining references

**Phase 3 (VERIFY):** Integration tests
- End-to-end hotkey toggling
- End-to-end slash command toggling
- CharacterPanel visibility logic (mobile/desktop/tablet)
- Escape key closes modals
- Multiple overlays don't stack (only one active)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-05T12:19:27Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05T11:17:14Z | — | — |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings yet.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- **OverlayManager not deleted yet**
  - Spec source: session file, AC-5
  - Spec text: "Delete OverlayManager.tsx after this story"
  - Implementation: OverlayManager.tsx left in place — GameLayout no longer imports it but the file still exists
  - Rationale: Deleting the file would break OverlayManager.test.tsx (22 tests). The old test file should be removed alongside the component in a cleanup commit. The AC-5 test verifies GameLayout loads without OverlayManager dependency.
  - Severity: minor
  - Forward impact: none — OverlayManager is dead code with no production consumers

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-point feature story — overlay rewiring, hotkeys, CharacterPanel integration

**Test Files:**
- `src/components/__tests__/GameLayout-overlays.test.tsx` - 23 tests across 6 describe blocks

**Tests Written:** 23 tests covering 5 ACs
**Status:** RED (17 failing, 6 passing — ready for Dev)

| AC | Tests | What's Covered |
|----|-------|---------------|
| AC-1 | 3 | CharacterPanel sidebar renders, null handling, prop passthrough |
| AC-2 | 8 | All 5 overlay types render, null case, backdrop, backdrop click |
| AC-3 | 9 | C/I/M/J/K/Escape hotkeys, toggle off, modifier ignore, input suppress, null data guard |
| AC-4 | 0 | Slash commands already wired via useSlashCommands → onOverlayChange prop chain |
| AC-5 | 1 | GameLayout module loads without OverlayManager dependency |
| Integration | 1 | Overlay switching (character → inventory via hotkey) |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Wiring test | AC-5 GameLayout import + AC-1 CharacterPanel testid | failing |
| No silent fallbacks | null characterSheet → no panel, null data → no hotkey fire | passing |
| Single overlay policy | Integration: overlay switching | failing |

**Self-check:** 0 vacuous tests. Every test has meaningful assertions.

**Handoff:** To Dev (Inigo Montoya) for implementation

### Delivery Findings
- No upstream findings during test design.

## TEA Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Files Analyzed:** 2 (GameLayout.tsx, GameLayout-overlays.test.tsx)

| Analysis | Status | Findings |
|----------|--------|----------|
| reuse | clean | No duplication |
| quality | clean | No dead imports |
| efficiency | clean | Flat conditional JSX |

**Applied:** 0 | **Flagged:** 0 | **Reverted:** 0
**Overall:** simplify: clean
**Quality Checks:** 41/41 tests passing

**Handoff:** To Westley (Reviewer) for code review

### TEA (test verification)
- No deviations from spec.

### Delivery Findings (verify)
- No upstream findings during test verification.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/components/GameLayout.tsx` — Added CharacterPanel sidebar, overlay modal rendering (character/inventory/map/journal/knowledge), hotkey handler (C/I/M/J/K/Escape)
- `src/components/__tests__/GameLayout-overlays.test.tsx` — Fixed mock data to match component interfaces

**Tests:** 23/23 passing (GREEN)
**Branch:** feat/25-4-rewire-gamelayout-charpanel (pushed)

### Delivery Findings
- **Improvement** (non-blocking): OverlayManager.tsx and its test file are now dead code — no production consumers. Affects `src/components/OverlayManager.tsx` and `src/components/__tests__/OverlayManager.test.tsx` (can be deleted). *Found by Dev during implementation.*

**Handoff:** To TEA (Fezzik) for verify phase

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | tsc clean, 41/41 tests pass, no debug code | N/A |
| 2 | reviewer-type-design | Yes | clean | Props interface unchanged, new value imports only | N/A |
| 3 | reviewer-security | Yes | clean | No auth, secrets, or injection surfaces | N/A |
| 4 | reviewer-simplifier | Yes | clean | No unnecessary complexity | N/A |
| 5 | reviewer-rule-checker | Yes | clean | Null guards on all overlays and hotkeys | N/A |
| 6 | reviewer-silent-failure-hunter | Yes | clean | No swallowed errors or silent fallbacks | N/A |

All received: Yes

## Reviewer Assessment

**Decision:** APPROVED
**PR:** slabgorb/sidequest-ui#60 (merged to develop)

**Findings:**
1. Escape handler correctly skips settings overlay (SettingsOverlay has its own handler)
2. CharacterPanel + PartyPanel coexist in multiplayer — by design (different data)
3. [RULE] Null data guards present on all overlays and hotkeys — no silent fallbacks
4. [SILENT] No swallowed errors, empty catches, or silent fallbacks
5. [TYPE] Props interface unchanged — no type design concerns

**Preflight:** TypeScript clean, 41/41 tests pass, no debug code
**Wiring:** CharacterPanel, all 5 overlay components, and hotkey handler are non-test consumers

### Delivery Findings (review)
- No upstream findings during code review.

### Reviewer (review)
- No deviations from spec.

**Handoff:** To Vizzini (SM) for finish ceremony

## Sm Assessment

5-point story continuing epic 25 UI redesign. 25-3 extracted SettingsOverlay — this story completes the migration by wiring game state overlays and CharacterPanel directly into GameLayout, removing the OverlayManager dependency. Branch `feat/25-4-rewire-gamelayout-charpanel` ready on UI develop. Handing off to TEA for RED phase.