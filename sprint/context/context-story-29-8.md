---
parent: context-epic-29.md
---

# Story 29-8: Multi-Room SVG Dungeon Map

## Business Context

The single-room renderer (29-4) shows one room at a time. Players need to see the whole
dungeon: discovered rooms, current room highlighted, fog of war on undiscovered areas,
and a zoom transition between dungeon overview and tactical detail. This is the full
map experience.

## Technical Approach

### Step 1: Create DungeonMapRenderer component

New file: `sidequest-ui/src/components/DungeonMapRenderer.tsx`

Props:
```typescript
interface DungeonMapRendererProps {
  layout: DungeonLayoutData;        // all rooms with global positions
  currentRoomId: string;
  discoveredRoomIds: string[];
  theme: TacticalThemeConfig;
  onRoomClick?: (roomId: string) => void;
  entities?: TacticalEntity[];
  zones?: EffectZone[];
}
```

### Step 2: Global grid rendering

Render each room as a `<g>` element positioned at its global offset from DungeonLayout.
Each `<g>` contains the room's cells rendered via `<use>` (same pattern as 29-4).
Shared walls between rooms render once (the layout engine already merged them).

### Step 3: Fog of war

Three visibility states per room:
- **Current**: full detail, full opacity, tokens visible
- **Discovered**: cells visible at 40% opacity, no tokens, room name label
- **Undiscovered**: completely hidden (render nothing)

Implement via CSS opacity on the room `<g>` elements plus conditional token rendering.

### Step 4: Zoom transition

Two zoom levels:
- **Overview**: entire dungeon fits in viewport. Rooms are shapes with labels. No
  individual cell grid lines. Tokens rendered as dots.
- **Tactical**: current room fills viewport. Full cell detail, tokens at full size,
  feature labels visible, grid lines.

Smooth SVG viewBox animation between levels. Click on a room in overview to zoom to it.
Use `transform` and `viewBox` transitions.

### Step 5: Current room highlight

The current room gets a pulsing highlight border (CSS animation on the room `<g>`).
In overview mode, the current room is brighter than other discovered rooms.

### Step 6: Integrate with Automapper

Replace the conditional check from 29-4 with a three-way delegation in Automapper.tsx:
- Multiple rooms have grids -> DungeonMapRenderer
- Single room has grid -> TacticalGridRenderer (29-4)
- No grids -> existing schematic renderer

## Acceptance Criteria

- AC-1: All discovered rooms render at correct global positions
- AC-2: Shared walls render once (no double-wall visual artifact)
- AC-3: Undiscovered rooms are completely invisible
- AC-4: Discovered-but-not-current rooms render at reduced opacity without tokens
- AC-5: Current room renders at full opacity with tokens
- AC-6: Zoom overview shows all discovered rooms as shapes with labels
- AC-7: Zoom tactical shows current room with full cell detail
- AC-8: Smooth viewBox transition between zoom levels
- AC-9: Click room in overview zooms to it and emits onRoomClick
- AC-10: Vitest tests for: fog of war states, zoom toggle, room click

## Key Files

| File | Action |
|------|--------|
| `sidequest-ui/src/components/DungeonMapRenderer.tsx` | NEW: multi-room SVG map with fog/zoom |
| `sidequest-ui/src/components/Automapper.tsx` | MODIFY: three-way delegation |
| `sidequest-ui/src/types/tactical.ts` | ADD: DungeonLayoutData type |
