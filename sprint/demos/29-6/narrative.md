# 29-6

## Problem

**Problem:** The dungeon/room map displayed to players was visually incoherent — rooms floated in space with no sense of physical connection, and their sizes bore no relationship to their actual in-game dimensions. **Why it matters:** Players couldn't orient themselves spatially. The map felt like a spreadsheet, not a place. Immersion broke the moment someone looked at it.

---

## What Changed

Imagine you're drawing a floor plan. Before this change, the app was placing each room like sticky notes dropped randomly on a table — they might overlap, they might be miles apart, and a "great hall" looked the same size as a broom closet.

Now, rooms are placed using a tree layout: the starting room anchors the center, and connected rooms branch outward from it. When two rooms share a wall, the app actually shares that wall — they snap together like puzzle pieces rather than floating near each other. On top of that, each room is drawn at a size proportional to its real in-game square footage. The great hall is visibly large. The secret passage is visibly narrow.

---

## Why This Approach

Tree topology is the natural shape of a dungeon — there's always an entrance, and everything branches from it. By building the layout algorithm around that structure, rooms fall into sensible positions without manual adjustment. Shared-wall snapping was layered on top because it's the cheapest way to communicate adjacency: if two rooms share a wall, showing them literally touching is unambiguous. Using real room dimensions meant no separate data transformation — the same numbers that drive game logic now drive visual scale directly.

---
