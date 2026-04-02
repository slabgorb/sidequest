---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-8: Automapper UI component — render room graph as dungeon floorplan

## Business Context

The automapper is the player-facing payoff for the room graph engine. It renders discovered rooms as a dungeon floorplan with fog of war, typed exits, and current room highlighting. This is a standalone UI component consuming MAP_UPDATE data — no backend changes needed. Largest story in the epic (8pt) because it involves graph layout, SVG rendering, and theme integration.

## Technical Guardrails

- New React component: `src/components/Automapper.tsx` in sidequest-ui.
- Consumes MAP_UPDATE messages from the WebSocket provider. The data format is defined in 19-4 (ExploredLocation with exits, room_type, size, is_current).
- **Graph layout:** Force-directed or grid-snapped layout from room exit directions. Rooms are rectangles, corridors are lines, doors/stairs/chutes are icons on connections.
- **Fog of war:** Undiscovered rooms not rendered. Exits to undiscovered rooms shown as faded/dashed lines with "?" markers.
- **Current room:** Highlighted with accent color from theme.
- **Theme integration:** Graph-paper aesthetic from Caverns & Claudes theme.yaml colors. Grid background, room fill from theme accent, corridor lines from theme secondary.
- Component must work in a sidebar panel — responsive within constrained width.
- No canvas — use SVG for accessibility and print support.

## Scope Boundaries

**In scope:**
- Automapper React component
- SVG rendering of room graph
- Fog of war (undiscovered rooms hidden)
- Current room highlighting
- Typed exit rendering (door, corridor, stairs, chute icons)
- Graph-paper aesthetic from theme
- Responsive sidebar layout

**Out of scope:**
- Room graph data generation (19-4 provides the data)
- Interactive features (clicking rooms to navigate — future)
- Minimap mode (future)
- Print stylesheet

## AC Context

1. Automapper component renders room graph from MAP_UPDATE data
2. Fog of war hides undiscovered rooms
3. Current room highlighted with accent color
4. Exits rendered as typed connections (door icon, corridor line, stairs)
5. Graph-paper aesthetic matching C&C theme
6. Responsive — works in sidebar panel
7. Test: render 5-room graph, verify SVG output matches expected structure
