---
parent: context-epic-29.md
---

# Story 29-4: Single-Room SVG Tactical Renderer

## Business Context

The tactical grid needs a visual representation. SVG is chosen for DOM event handling,
resolution independence, and accessibility. This story builds the single-room renderer --
the foundation component that all higher-level views (multi-room map, grid editor) compose.

## Technical Approach

### Step 1: Create TacticalGridRenderer component

New file: `sidequest-ui/src/components/TacticalGridRenderer.tsx`

Props:
```typescript
interface TacticalGridRendererProps {
  grid: TacticalGridData;      // parsed grid from server
  cellSize?: number;           // px per cell (default 24)
  theme: TacticalThemeConfig;  // genre-themed palette
  onCellClick?: (pos: GridPos) => void;
  onCellHover?: (pos: GridPos | null) => void;
  entities?: TacticalEntity[];  // token overlay (story 29-10)
  zones?: EffectZone[];         // zone overlay (story 29-13)
}
```

### Step 2: SVG structure

Use `<defs>` with `<symbol>` elements for each cell type. Render cells via `<use>` for
efficient DOM. Structure:
```
<svg viewBox="0 0 {width*cellSize} {height*cellSize}">
  <defs>
    <symbol id="cell-floor">...</symbol>
    <symbol id="cell-wall">...</symbol>
    <symbol id="cell-water">...</symbol>
    ...per feature type...
  </defs>
  <g class="grid-layer">
    {cells.map -> <use href="#cell-{type}" x y />}
  </g>
  <g class="feature-layer">
    {legend features with labels}
  </g>
</svg>
```

Void cells render nothing (transparent). Wall cells render solid. Floor cells render
with subtle grid lines. Feature cells render with type-specific icons/colors.

### Step 3: Genre-themed palette

`TacticalThemeConfig` maps cell types to colors/styles. Derive from existing theme.yaml
`colors` section. For caverns_and_claudes:
- Floor: warm stone (#8B7355)
- Wall: dark stone (#3C3024)
- Water: deep blue (#1A3A5C)
- Difficult terrain: muted amber (#A08050)
- Cover features: lighter stone (#9E8B6E)
- Hazard features: warning red (#8B2500)

### Step 4: Integrate with Automapper

In `sidequest-ui/src/components/Automapper.tsx` (line 1), add a check: if the current
room has a `grid` field in its data, render `TacticalGridRenderer` instead of the
schematic view. The Automapper becomes a delegating component:
- Room has grid -> TacticalGridRenderer
- Room has no grid -> existing schematic renderer

### Step 5: Add TypeScript types

New file: `sidequest-ui/src/types/tactical.ts` with TypeScript equivalents of the
Rust types: `TacticalGridData`, `TacticalCell`, `GridPos`, `FeatureDef`, `FeatureType`,
`TacticalThemeConfig`.

## Acceptance Criteria

- AC-1: SVG renders all 8 cell types with visually distinct styles
- AC-2: Void cells render as transparent (no visual artifact)
- AC-3: Feature cells show type-appropriate visual marker and tooltip on hover
- AC-4: `cellSize` prop scales the entire grid proportionally
- AC-5: `onCellClick` fires with correct GridPos for any cell
- AC-6: Genre theme palette applies (not hardcoded colors)
- AC-7: Automapper delegates to TacticalGridRenderer when grid data is present
- AC-8: Automapper continues to render schematic view when grid data is absent
- AC-9: Component has vitest tests for: rendering, cell click, theme application
- AC-10: Wiring test: Automapper imports and conditionally renders TacticalGridRenderer

## Key Files

| File | Action |
|------|--------|
| `sidequest-ui/src/components/TacticalGridRenderer.tsx` | NEW: single-room SVG renderer |
| `sidequest-ui/src/types/tactical.ts` | NEW: TypeScript tactical types |
| `sidequest-ui/src/components/Automapper.tsx` | MODIFY: delegate to tactical renderer when grid present |
