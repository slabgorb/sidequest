---
story_id: "25-2"
epic: "25"
workflow: "tdd"
---
# Story 25-2: Character Panel Sidebar Redesign

## Story Details
- **ID:** 25-2
- **Epic:** 25 (UI Redesign)
- **Workflow:** tdd
- **Repository:** sidequest-ui
- **Stack Parent:** none

## Context

The original character panel used book-themed skeumorphism. This story replaces it with:
- **Persistent themed sidebar** — character stats/abilities always visible, themed per genre
- **Current-turn narrative focus** — main canvas shows active narrative turn, not character sheet
- **Reactive to combat state** — combat overlay shows when needed, sidebar adapts

No new mechanics. Pure UI/UX reorientation: mechanical state now backs the narrative, not the reverse.

## Workflow Tracking
**Workflow:** tdd
**Phase:** review
**Phase Started:** 2026-04-05T10:38:39Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05 | 2026-04-05T10:30:56Z | 10h 30m |
| red | 2026-04-05T10:30:56Z | 2026-04-05T10:34:47Z | 3m 51s |
| green | 2026-04-05T10:34:47Z | 2026-04-05T10:38:25Z | 3m 38s |
| spec-check | 2026-04-05T10:38:25Z | 2026-04-05T10:38:32Z | 7s |
| verify | 2026-04-05T10:38:32Z | 2026-04-05T10:38:39Z | 7s |
| review | 2026-04-05T10:38:39Z | - | - |

## Delivery Findings

No upstream findings at setup.

## Sm Assessment

**Story:** 25-2 — CharacterPanel persistent docked sidebar
**Setup:** Session created, branch `feat/25-2-character-panel-sidebar` in sidequest-ui off develop
**Workflow:** tdd (red → green → verify → review → finish)
**Handoff:** To Fezzik (TEA) for RED phase — write failing tests for CharacterPanel

## Tea Assessment

**Tests Required:** Yes
**Reason:** 5-point component story with tabbed UI, persistence, and layout integration

**Test Files:**
- `src/components/__tests__/CharacterPanel.test.tsx` — 28 tests

**Tests Written:** 28 tests covering 5 ACs
- AC-1: Persistent sidebar rendering (8 tests) — visible without interaction, no modal/backdrop
- AC-2: Tabbed sections (9 tests) — Stats/Abilities/Backstory tabs, optional Inventory tab, aria-selected
- AC-3: Tab persistence via useLocalPrefs (3 tests) — save/restore/corrupt-data fallback
- AC-4: Collapse/expand (6 tests) — toggle, content hidden, name visible, persistence
- AC-5: Edge cases (3 tests) — empty stats, empty abilities, no location
- Wiring (1 test) — module exports exist

**Status:** RED (failing — CharacterPanel module does not exist)

**Handoff:** To Inigo Montoya (Dev) for GREEN phase

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/components/CharacterPanel.tsx` — persistent docked sidebar with tabbed ARIA interface, useLocalPrefs persistence, collapse/expand

**Tests:** 29/29 passing (GREEN)
**Branch:** feat/25-2-character-panel-sidebar (pushed)

**Handoff:** To next phase (verify)