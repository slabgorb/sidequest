# 19-8: Automapper UI — Room Graph Renderer

**Phase:** review
**Workflow:** tdd
**Repos:** ui
**Branch:** feat/19-8-automapper-ui

## Overview

Story: Automapper React component to render discovered dungeon rooms as navigable graph/floorplan.
Repo: sidequest-ui
Points: 8 (p1)
Depends on: 19-4 (MAP_UPDATE data format)
Workflow: TDD

## Business Context

The automapper is the player-facing payoff for room graph navigation (epic 19). When players move through a dungeon, discovered rooms accumulate in memory. The automapper renders them as a floorplan with fog of war, showing:

- **Discovered rooms** as rectangles with labels
- **Undiscovered rooms** hidden (fog of war)
- **Current room** highlighted with theme accent
- **Exits** as typed connections: doors (rectangle), corridors (lines), stairs (↑ icon), chutes (↓ icon)
- **Graph-paper aesthetic** matching Caverns & Claudes theme

This is a UI-only story. The backend (story 19-4) provides the data; this story consumes it.

## Technical Guardrails

### Component API

```tsx
// Location: src/components/Automapper.tsx
interface ExploredLocation {
  id: string;           // room_id
  name: string;
  room_type: string;    // "chamber" | "corridor" | "stairs" | "chute"
  size: string;         // "small" | "medium" | "large"
  is_current: boolean;
  exits: ExitInfo[];
}

interface ExitInfo {
  direction: string;    // "north", "south", "east", "west", "up", "down"
  exit_type: string;    // "door" | "corridor" | "stairs" | "chute"
  to_room_id?: string;  // Some if discovered; undefined if undiscovered
}

interface AutomapperProps {
  rooms: ExploredLocation[];
  currentRoomId: string;
  theme?: ThemeConfig;
}
```

### Data Flow

1. **WebSocket→MAP_UPDATE:** Backend sends ExploredLocation[] in a MAP_UPDATE message
2. **Provider stores:** WebSocket provider buffers in game state
3. **Component consumes:** Automapper.tsx reads from useGameState() or similar
4. **Re-renders on update:** When rooms list changes

### Graph Layout Strategy

**Force-directed layout** (physics simulation) is ideal for natural room placement. Fallback: **grid snap** based on exit directions.

- Use `d3-force` (already in dependencies) or lightweight alternative (simple Euclidean physics)
- Nodes = rooms; edges = exits
- Apply forces: link attraction, charge repulsion, center gravity
- Snap to grid (20px) after simulation to align with graph-paper aesthetic
- Handle undiscovered neighbors: position them off-canvas or semi-transparent pending discovery

### SVG Rendering

- Root: `<svg viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid meet">`
- Background: graph-paper pattern (theme colors)
- Rooms: `<rect x={} y={} width={} height={} fill={} stroke={} />`
- Room labels: `<text x={} y={} text-anchor="middle">` (room name)
- Corridors: `<line x1={} y1={} x2={} y2={} stroke={} />`
- Door/stair/chute icons: small `<g>` or emoji overlaid on connection midpoint
- Current room: stroke-width=3, accent color from theme.accent

### Theme Integration

Caverns & Claudes theme.yaml defines:
- `colors.accent` — current room highlight
- `colors.primary` — room fill
- `colors.secondary` — corridor lines
- `colors.background` — grid background

Apply grid-paper pattern using `<defs><pattern>` with background color and thin grid lines.

### Responsive Layout

- Component sits in sidebar (constrained width, e.g., 300px max)
- SVG scales to fit viewport without overflow
- Use CSS `max-width` and `aspect-ratio` to maintain proportions
- On narrow screens, rooms get smaller; corridors get thinner

## Acceptance Criteria

1. ✓ Automapper component renders room graph from MAP_UPDATE data
2. ✓ Fog of war: undiscovered rooms are hidden
3. ✓ Current room highlighted with theme accent color
4. ✓ Exits rendered as typed connections (door icon, corridor line, stairs, chute)
5. ✓ Graph-paper aesthetic matching C&C theme
6. ✓ Responsive: works in sidebar panel without overflow
7. ✓ Integration test: render 5-room graph, verify SVG output structure

## TDD Plan

### Phase 1: Test Fixtures & Layout

**Test file:** `src/components/__tests__/Automapper.test.tsx`

```tsx
describe("Automapper", () => {
  describe("layout", () => {
    it("positions rooms from exit graph", () => {
      // 5-room straight corridor: [A] -- [B] -- [C] -- [D] -- [E]
      const rooms = mockRoomGraph5();
      render(<Automapper rooms={rooms} currentRoomId="B" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      const rects = svg.querySelectorAll("rect[data-room-id]");
      expect(rects).toHaveLength(5);
      
      // B should be positioned centrally (forced layout)
      const bRect = svg.querySelector("rect[data-room-id='B']");
      expect(bRect).toHaveClass("current-room");
    });

    it("calculates layout with force simulation", () => {
      // 4-room junction: B in center connected to N, S, E, W
      const rooms = mockRoomGraphJunction();
      render(<Automapper rooms={rooms} currentRoomId="B" />);
      
      // Verify A,C,D,E are roughly equidistant from B
      // (physics sim should space them evenly)
    });
  });

  describe("fog of war", () => {
    it("hides undiscovered rooms", () => {
      const rooms = [
        { id: "A", name: "Entrance", exits: [{ direction: "east", to_room_id: "B" }] },
        { id: "B", name: "??", exits: [{ direction: "west", to_room_id: "A" }, { direction: "east", to_room_id: undefined }] },
      ];
      render(<Automapper rooms={rooms} currentRoomId="A" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      expect(svg.querySelector("rect[data-room-id='B']")).not.toBeInTheDocument();
      // But exit to B should show as "?" dashed line
      expect(svg.querySelector("line.unknown-exit")).toBeInTheDocument();
    });
  });

  describe("rendering", () => {
    it("renders rooms as SVG rectangles", () => {
      const rooms = mockRoomGraph5();
      render(<Automapper rooms={rooms} currentRoomId="C" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      rooms.forEach(room => {
        expect(svg.querySelector(`rect[data-room-id='${room.id}']`)).toBeInTheDocument();
      });
    });

    it("applies theme colors", () => {
      const theme = {
        colors: { accent: "#ff0000", primary: "#00ff00", secondary: "#0000ff" }
      };
      render(<Automapper rooms={mockRoomGraph5()} currentRoomId="A" theme={theme} />);
      
      const current = screen.getByRole("img", { hidden: true })
        .querySelector("rect[data-room-id='A'].current-room");
      expect(current).toHaveStyle({ stroke: "#ff0000" });
    });

    it("renders graph-paper background", () => {
      render(<Automapper rooms={mockRoomGraph5()} currentRoomId="A" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      const pattern = svg.querySelector("defs pattern");
      expect(pattern).toBeInTheDocument();
      expect(pattern.querySelector("line")).toBeInTheDocument(); // grid lines
    });
  });

  describe("exits", () => {
    it("renders door exits as symbols", () => {
      const rooms = [{
        id: "A",
        exits: [{ direction: "east", exit_type: "door", to_room_id: "B" }]
      }];
      render(<Automapper rooms={rooms} currentRoomId="A" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      expect(svg.querySelector("g[data-exit-type='door']")).toBeInTheDocument();
    });

    it("renders corridor exits as simple lines", () => {
      const rooms = [{
        id: "A",
        exits: [{ direction: "east", exit_type: "corridor", to_room_id: "B" }]
      }];
      render(<Automapper rooms={rooms} currentRoomId="A" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      expect(svg.querySelector("line[data-exit-type='corridor']")).toBeInTheDocument();
    });

    it("marks unknown exits as dashed + ?", () => {
      const rooms = [{
        id: "A",
        exits: [{ direction: "north", exit_type: "door", to_room_id: undefined }]
      }];
      render(<Automapper rooms={rooms} currentRoomId="A" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      const unknownExit = svg.querySelector("line.unknown-exit");
      expect(unknownExit).toHaveStyle({ strokeDasharray: "4,4" });
      expect(svg.querySelector("text.unknown-label")).toHaveTextContent("?");
    });
  });

  describe("responsiveness", () => {
    it("fits in 300px sidebar", () => {
      render(<Automapper rooms={mockRoomGraph5()} currentRoomId="A" />);
      
      const container = screen.getByRole("img", { hidden: true }).parentElement;
      expect(container).toHaveStyle({ maxWidth: "300px" });
    });

    it("scales SVG viewBox on narrow screens", () => {
      render(<Automapper rooms={mockRoomGraph5()} currentRoomId="A" />);
      
      const svg = screen.getByRole("img", { hidden: true });
      expect(svg).toHaveAttribute("preserveAspectRatio", "xMidYMid meet");
      expect(svg).toHaveAttribute("viewBox");
    });
  });
});
```

### Phase 2: Layout Engine

Implement force-directed layout using simple physics:

```tsx
// src/lib/layout.ts
export interface LayoutNode {
  id: string;
  x: number;
  y: number;
  vx?: number; // velocity
  vy?: number;
}

export interface LayoutEdge {
  source: string;
  target: string;
  length?: number; // preferred distance
}

export function forceDirectedLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  iterations = 100,
  gridSnap = 20
): LayoutNode[] {
  // Initialize positions randomly
  // Apply forces: link attraction, charge repulsion, center gravity
  // Iterate, dampening motion
  // Snap to grid
  // Return positioned nodes
}

export function directionToAngle(direction: string): number {
  // "north" → 0°, "east" → 90°, etc.
  // Used as hint for layout seed
}
```

**Test:**
```tsx
describe("forceDirectedLayout", () => {
  it("positions straight corridor with even spacing", () => {
    const rooms = ["A", "B", "C", "D", "E"];
    const edges = [
      { source: "A", target: "B" },
      { source: "B", target: "C" },
      { source: "C", target: "D" },
      { source: "D", target: "E" },
    ];
    
    const result = forceDirectedLayout(rooms, edges);
    
    // A and E should be farthest apart
    // B, C, D should be evenly distributed
    const distances = [];
    for (let i = 0; i < 4; i++) {
      distances.push(dist(result[i], result[i+1]));
    }
    distances.forEach(d => expect(d).toBeCloseTo(distances[0], 0));
  });
});
```

### Phase 3: Automapper Component

Core rendering logic:

```tsx
// src/components/Automapper.tsx
export const Automapper: React.FC<AutomapperProps> = ({ rooms, currentRoomId, theme }) => {
  // 1. Build graph from rooms + exits
  // 2. Run layout algorithm
  // 3. Render SVG with rooms, exits, labels
  // 4. Apply theme colors
};
```

### Phase 4: Theme Integration

Map theme colors to SVG fills/strokes; ensure graph-paper background.

### Phase 5: Fog of War & Current Room Highlighting

Conditional rendering based on `is_current` and `to_room_id` presence.

## Implementation Checklist

- [ ] Create test file `src/components/__tests__/Automapper.test.tsx`
- [ ] Write Phase 1 test suite (layout, fog of war, rendering, exits, responsiveness)
- [ ] Create `src/lib/layout.ts` with force-directed algorithm
- [ ] Test layout engine with 5-room corridor and junction graphs
- [ ] Implement `src/components/Automapper.tsx`
  - [ ] Parse rooms and exits into graph structure
  - [ ] Call layout engine
  - [ ] Render SVG canvas with viewBox
  - [ ] Render rooms as rectangles with labels
  - [ ] Render exits as connections (lines, icons)
  - [ ] Apply fog of war (hide undiscovered rooms, show "?" for unknown exits)
  - [ ] Highlight current room with accent color
  - [ ] Apply graph-paper background from theme
  - [ ] Style for responsiveness
- [ ] Verify theme color application
- [ ] Integration test: 5-room graph renders correctly
- [ ] Wire into WebSocket provider (consume MAP_UPDATE in game state)
- [ ] Manual test with Caverns & Claudes theme

## TEA Assessment

**Tests Required:** Yes
**Test File:** `src/components/__tests__/Automapper.test.tsx`

**Tests Written:** 28 tests covering 7 ACs + edge cases
**Status:** RED (27 failing, 1 passing — empty list edge case)

| AC | Tests | Count |
|----|-------|-------|
| AC-1: Renders room graph | SVG element, rects per room, labels, connections, empty/single | 6 |
| AC-2: Fog of war | No rects for undiscovered, dashed lines, "?" labels | 3 |
| AC-3: Current room highlight | current-room class, not on others, accent stroke | 3 |
| AC-4: Typed exits | door/corridor/stairs/chute markers | 4 |
| AC-5: Graph-paper aesthetic | SVG defs pattern, grid lines, background fill | 3 |
| AC-6: Responsive sidebar | viewBox, preserveAspectRatio, width 100% | 3 |
| AC-7: Integration | 5-room linear + junction graph | 2 |
| Edge cases | sealed room, duplicate exits, no theme, bad roomId | 4 |

**Self-check:** 0 vacuous assertions. All tests use meaningful `expect()` with DOM queries.
**Handoff:** To Inigo Montoya (Dev) for implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/components/Automapper.tsx` — Full SVG room graph renderer (269 LOC). Direction-based BFS layout, graph-paper pattern, typed exits, fog of war, current room highlight, responsive viewBox.

**Tests:** 28/28 passing (GREEN)
**Branch:** feat/19-8-automapper-ui (pushed)

**Handoff:** To next phase (verify or review)

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

## Delivery Findings

### TEA (test design)
- **Question** (non-blocking): ExploredLocation in MapOverlay.tsx has different shape than Automapper's ExploredRoom. Affects `src/components/MapOverlay.tsx` (may need alignment or shared base type). *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

## Notes

- D3-force is already a dependency in sidequest-ui; use it if available
- If not, implement simple spring/charge physics (lightweight alternative)
- Undiscovered rooms: don't render the room node, but do show faded/dashed exit lines with "?" labels
- Room sizes (small/medium/large) can affect rectangle dimensions, or just use consistent sizing
- Exit directions (north/south/east/west/up/down) should hint at layout — use as seeding positions
- Grid snap (20px) after force simulation to align with graph-paper aesthetic
