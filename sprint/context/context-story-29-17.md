---
parent: context-epic-29.md
---

# Story 29-17: Browser Grid Editor

## Business Context

While ASCII is the fastest review format, authoring complex non-rectangular rooms in
a text editor is error-prone. A browser-based grid editor lets content authors paint
cells visually, place features, adjust exits, and export valid ASCII grids. This is the
TacticalGridRenderer (29-4) running in edit mode.

## Technical Approach

### Step 1: Add edit mode to TacticalGridRenderer

Extend `TacticalGridRenderer.tsx` with an `editMode` prop:

```typescript
interface TacticalGridRendererProps {
  // ...existing props from 29-4...
  editMode?: boolean;
  onGridChange?: (grid: TacticalGridData) => void;
}
```

In edit mode:
- Click a cell to cycle through cell types (floor -> wall -> void -> water -> difficult terrain)
- Right-click to place a feature (opens feature picker)
- Drag to paint multiple cells
- Grid border shows exit gaps highlighted in yellow

### Step 2: Create GridEditor component

New file: `sidequest-ui/src/components/GridEditor.tsx`

Wraps TacticalGridRenderer in edit mode with a toolbar:
- **Cell type palette**: buttons for each cell type (visual icons)
- **Feature palette**: add legend entry (letter, type, label)
- **Dimensions**: resize grid (add/remove rows and columns)
- **Exit editor**: click border cells to toggle exit gaps
- **Validation**: live validation status (runs the 8 rules client-side)
- **Export**: copy ASCII text to clipboard, or save to file

### Step 3: ASCII import/export

- **Import**: paste ASCII text into a text area, parse into TacticalGridData
- **Export**: convert TacticalGridData back to ASCII string + legend YAML block

Round-trip fidelity: import(export(grid)) === grid.

### Step 4: Live validation

Run a client-side subset of validation rules while editing:
- Perimeter closure (rule 4)
- Flood fill connectivity (rule 5)
- Legend completeness (rule 6)
- Legend placement (rule 7)

Display validation errors as inline markers on the grid (red highlight on invalid cells).

### Step 5: Route and access

Add a route: `/editor/grid` that renders the GridEditor component. Accessible from
the GM dashboard or directly via URL. Not part of the game flow -- purely an
authoring tool.

## Acceptance Criteria

- AC-1: Click to paint cell types in edit mode
- AC-2: Right-click to place features with type and label
- AC-3: Drag to paint multiple cells
- AC-4: Grid resizable (add/remove rows and columns)
- AC-5: Exit gaps editable on grid border
- AC-6: ASCII export produces valid grid string + legend YAML
- AC-7: ASCII import parses grid string into visual editor
- AC-8: Round-trip fidelity: import(export(grid)) preserves all cells
- AC-9: Live validation highlights invalid cells
- AC-10: Editor accessible at `/editor/grid` route

## Key Files

| File | Action |
|------|--------|
| `sidequest-ui/src/components/GridEditor.tsx` | NEW: editor UI wrapping TacticalGridRenderer |
| `sidequest-ui/src/components/TacticalGridRenderer.tsx` | MODIFY: add editMode, onGridChange props |
| `sidequest-ui/src/App.tsx` | ADD: `/editor/grid` route |
