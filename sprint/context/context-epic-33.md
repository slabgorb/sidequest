# Epic 33: Composable GameBoard — Drag-and-Drop Dashboard Polish

## Overview

The structural GameBoard shipped via `feat/composable-gameboard`, replacing the fixed `GameLayout` with a Dockview-based tabbed panel system. Grid, widgets, image gallery, hotkeys, and layout persistence are all wired. This epic covers the visual polish layer: genre theming, per-archetype textures, preset tuning, character panel enrichment, inventory UX, mobile gestures, and edit-mode discoverability — the work that requires playtesting to get right.

**Priority:** P1
**Repo:** ui
**Stories:** 18 (2 done, 16 remaining)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| No dedicated PRD or ADR | Epic is polish on shipped infrastructure; design decisions are embedded in the codebase from the `feat/composable-gameboard` branch |

## Background

### Current State

The GameBoard (`sidequest-ui/src/components/GameBoard/GameBoard.tsx`) uses **Dockview** (not react-grid-layout — that was the original implementation, since replaced). Dockview provides a tab/split panel model with drag-and-drop between groups. The default layout is two-region: narrative on the left, supporting panels (character, inventory, map, knowledge, gallery, audio) tabbed on the right. Mobile falls back to `MobileTabView` with a bottom tab bar.

Genre theming operates on a **two-layer architecture**:

1. **Per-genre color layer** — `useGenreTheme` hook listens for `theme_css` WebSocket events from the server, injects genre-specific CSS custom properties (`--text`, `--background`, `--surface`, `--primary`, `--accent`), loads Google Fonts dynamically, and detects dark/light mode via WCAG 2.0 luminance calculation.

2. **Per-archetype structure layer** — `useChromeArchetype` maps genre slugs to one of three structural archetypes (`parchment`, `terminal`, `rugged`) and sets `data-archetype` on `<html>`. `archetype-chrome.css` (275 lines) uses attribute selectors to apply font families, border weights, corner treatments, overlay effects (vignettes, scanlines, dust), and pseudo-element decorations.

Story 33-1 (done) shipped the archetype chrome CSS. Story 33-11 (done) shipped tab notification badges for mobile.

### Why This Epic Exists

The structural grid works. But "works" and "feels like a genre-specific RPG dashboard" are different things. Players see a functional layout; they should see a space_opera command bridge, a low_fantasy parchment desk, or a road_warrior scrap-metal console. The polish stories in this epic transform the generic dashboard into genre-immersive chrome — the visual identity layer that makes each genre pack feel like a distinct product.

Secondary goals: mobile UX (swipe navigation, badges), edit-mode discoverability (users don't know they can rearrange panels), and character panel enrichment (the sidebar needs portrait, conditions, party status, stat context to be useful at a glance).

## Technical Architecture

### Component Structure

```
App.tsx
├── useGenreTheme(messages)              # Layer 1: per-genre CSS vars + fonts
├── useChromeArchetype(currentGenre)     # Layer 2: archetype structural props
├── useGameBoardLayout(genre, world)     # Widget visibility + preset persistence
└── GameBoard.tsx
    ├── BackgroundCanvas.tsx             # Fixed bg, reads --surface/--background
    ├── Running header                   # Genre-styled header bar
    ├── DockviewReact                    # Tab/split panel manager
    │   ├── PanelAdapter                 # Stable ref bridge for context updates
    │   └── Panels (tabbed groups)
    │       ├── NarrativeWidget
    │       ├── CharacterWidget          # 33-7/8/9/10/12 enrichment target
    │       ├── MapWidget
    │       ├── InventoryWidget          # 33-13/14/15/16 enrichment target
    │       ├── KnowledgeWidget
    │       ├── ImageGalleryWidget       # 33-17 metadata target
    │       ├── AudioWidget
    │       └── ConfrontationWidget      # Data-gated (encounter only)
    ├── Turn status indicator
    └── InputBar
```

### Theming Data Flow

```
Server (theme_css event)
  ↓
useGenreTheme → <style#genre-theme-css> → CSS vars (--surface, --primary, etc.)
  ↓                                          ↓
useChromeArchetype → data-archetype attr    Tailwind classes consume vars
  ↓
archetype-chrome.css → structural CSS (borders, fonts, overlays, pseudo-elements)
  ↓
BackgroundCanvas → reads --surface/--background from cascade (no props needed)
```

### Key Files

| File | Role |
|------|------|
| `src/components/GameBoard/GameBoard.tsx` | Dockview layout manager, widget registry, context bridge |
| `src/components/GameBoard/BackgroundCanvas.tsx` | Genre-themed background — 33-2 target |
| `src/components/GameBoard/MobileTabView.tsx` | Mobile tab view — 33-4 target |
| `src/components/GameBoard/presetLayouts.ts` | 4 responsive presets (classic, tactician, explorer, minimalist) — 33-3 target |
| `src/components/GameBoard/widgetRegistry.ts` | Widget metadata (labels, hotkeys, closable, data-gating) — 33-6 target |
| `src/components/CharacterPanel.tsx` | Character sidebar — 33-7/8/9/10/12 target |
| `src/hooks/useGenreTheme.ts` | Layer 1: genre CSS injection, font loading, dark/light detection |
| `src/hooks/useChromeArchetype.ts` | Layer 2: genre→archetype mapping, structural CSS vars |
| `src/styles/archetype-chrome.css` | Archetype structural CSS (parchment/terminal/rugged) |

### Archetype Families

| Archetype | Genres | Character |
|-----------|--------|-----------|
| `parchment` | low_fantasy, victoria, elemental_harmony, star_chamber | Serif fonts, soft borders, warm vignette, corner flourishes |
| `terminal` | neon_dystopia, space_opera | Monospace fonts, neon glow, CRT scanlines, accent borders |
| `rugged` | road_warrior, mutant_wasteland, spaghetti_western, pulp_noir, caverns_and_claudes | Sans-serif, heavy borders, dust vignette, metal brackets |

### Architecture Constraints

1. **Two-layer theming is load-bearing.** Colors are per-genre (11 unique palettes via `theme_css`). Structure is per-archetype (3 families via `data-archetype`). Do not collapse these layers or add a fourth. New genres slot into existing archetypes.

2. **BackgroundCanvas reads from the cascade.** It consumes `--surface` and `--background` without props. Do not make it genre-aware or prop-driven — that creates a second source of truth for colors.

3. **Dockview replaced react-grid-layout.** Stories referencing "grid coordinates" (33-3) or "edit mode toggle" (33-5) need interpretation in the Dockview tab/split model. There is no coordinate grid and no edit/view mode toggle — Dockview panels are always draggable.

4. **Character panel uses header-tabs-footer.** Portrait/name pinned at top, Stats/Abilities/Status/Journal as switchable tabs, party section pinned at bottom. New stories (33-7 through 33-10, 33-12) layer into this existing hierarchy — do not restructure.

5. **Z-index bands are fragile.** BackgroundCanvas sits at `z-index: -10`. Terminal scanline overlay sits at `z-index: 100`. New texture layers must respect these bands.

### UX Consultation Findings (Klinger)

**Theming:** The two-layer system is correct. 33-2 background textures should be CSS `background-image` patterns within archetype `::before` overlays, consuming existing CSS vars.

**Character panel hierarchy:** Conditions/wounds (33-10) must surface in the header zone between name and tab bar — not inside a tab. Players miss "Stunned" during combat if it's hidden in the Stats tab.

**Mobile:** Extend `MobileTabView` with horizontal swipe (50px threshold, 0.3px/ms velocity). Gate swipe detection to skip InputBar and map-pan conflicts. Lazy-mount panels on first visit, then keep mounted to preserve scroll state.

**Edit mode:** Dockview is always editable — no toggle needed. 33-5 becomes: first-run tooltip ("Drag tabs to rearrange") + Reset Layout button in header. Ship 33-6 (widget add/remove menu) alongside or before 33-5 as the recovery mechanism for accidentally closed panels.

**Cross-genre consistency:** Enforce contrast ratios (WCAG AA 4.5:1 body, 3:1 headers) at theme injection time. Terminal archetype's `--glow-primary`/`--glow-accent` are hardcoded — should derive from genre CSS vars for palette correctness.

## Cross-Epic Dependencies

**Depends on:**
- feat/composable-gameboard branch (merged) — shipped the Dockview layout, widget system, and persistence
- Epic 33-1 (done) — shipped archetype chrome CSS that all subsequent stories build on
- Genre pack theme_css generation (server-side) — provides the per-genre color palettes

**Depended on by:**
- Epic 34 stories 34-5/6/7 (dice UI) — the dice overlay renders inside the GameBoard; it must respect the z-index bands and archetype theming
- Future genre pack additions — new genres must map to one of the three archetypes
