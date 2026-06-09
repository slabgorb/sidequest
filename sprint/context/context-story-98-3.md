---
parent: context-epic-98.md
workflow: tdd
---

# Story 98-3: U1 UI — two-scale MapWidget (cartography graph default + orrery drill-down), retire orbital:bool whole-Map toggle

## Business Context

This story is where the two-scale model becomes **visible to the player**. After
98-1 restructures the content and 98-2 resolves per-system files, the UI must stop
treating `orbital: boolean` as a whole-Map toggle (the playtest-fix #748 wiring
that, correctly for single-system `coyote_star`, rendered the orrery *as the
entire Map tab* — and wrongly suppressed the galactic graph for a cluster). The
player should see a **legible campaign map** (cartography nodes-and-edges graph)
by default, and drill into a node to see **that system's orrery**.

This closes the loop on the ADR-141 core slice (C1 → S1 → U1): the cluster reads
as a cluster, the orrery reads as one system at a time. It does **not** rebuild
the renderer — #748's "orrery renders" behavior stays verified; this re-scopes
*when* it renders.

## Technical Guardrails

**Lane:** Dev. **Repo:** ui. **Depends on:** epic 100 / story 100-10.

**Key files:**
- `components/GameBoard/widgets/MapWidget.tsx` — `orbital?: boolean` at `:20`, `orbitalEnabled` at `:65`. This is the toggle being retired.
- `components/MapOverlay.tsx` — drives the graph; adopts the shared d3-dag component (per 100-10).

### Render-target dependency (the load-bearing constraint)

**U1 must NOT build against `sidequest-ui/src/lib/cartographyLayout.ts`.** Epic 100
/ story 100-10 (Phase 3) **deletes that SVG layout** and replaces it with a
**shared d3-dag cartography-layout module + Map component** consumed by both the
reference page and the in-game `MapOverlay`. Building against the SVG path is
doomed scaffolding — the work would be redone.

**Ownership boundary (settled, 2026-06-08 — both specs cross-reference this):**
- **100-10 owns the layout engine** — the d3-dag module that lays out the
  cartography graph deterministically. Per the epic-100 spec amendment, 100-10's
  component is built **drill-aware-ready**: self-contained (does not assume
  `MapWidget`'s `orbital` toggle or current feed shape is fixed), accepts a
  selected/active-node signal, and exposes a node-select callback.
- **98-3 (this story) owns the view-model** — *which scale renders when*, the
  drill-in/back affordances, and the single-system collapse. U1 drives the shared
  component via its active-node prop + node-select callback; it does **not** fork
  or re-layout the graph.

### The "overlay feed frozen" note is STALE — no contradiction

The story's YAML description warns that epic-100 spec lines 51-52 ("No change to
the in-game `MapOverlay`'s data source") contradict this story. **That note is
out of date.** The Architect amendment immediately following those lines
(2026-06-08, "epic-98 reconciliation") explicitly scopes that Non-Goal to epic
100's *own* work and states that **epic 98 / 98-3 deliberately reworks the feed**.
The two specs now cross-reference each other and agree. SM: the story-description
note can be pruned.

### Edge model (consistent across both specs — epic 98 §3 is authoritative)

The shared d3-dag component renders **topology from `adjacent:` only**. `routes:`
entries are mechanics annotations (98-4), **not** layout edges. Two invariants
U1's rendering relies on: (1) an `adjacent` pair with no matching `routes` entry
is a valid navigable edge (ruleset-default jump cost), not a dropped/dangling
edge; (2) only an adjacency to an *unknown* region is dropped (the existing
`sidequest.reference.map_dangling_edge` WARN span, server-side). U1 does not
implement edge mechanics — it just must not mis-render the topology.

**What NOT to touch:**
- Do **not** build on or revive `cartographyLayout.ts` (deleted by 100-10).
- Do **not** re-layout the graph (100-10's engine owns that).
- Do **not** regress #748's verified "orrery renders" behavior — only re-scope *when* it renders.

## Scope Boundaries

**In scope:**
- Cluster world (`perseus_cloud`) default Map = cartography graph via the shared d3-dag component.
- Drill into a node → that system's orrery; back affordance returns to the graph.
- Replace the `orbital: boolean` whole-Map toggle with a campaign↔local scale/drill state.
- Single-system world (`coyote_star`) → orrery-as-Map (scales collapse).
- Legible "no local chart" state for a node with no authored orrery.

**Out of scope:**
- The d3-dag layout engine itself (100-10).
- Content (98-1) and server resolution (98-2).
- Jump-mechanics rendering / edge annotations (98-4 / 98-5).

## AC Context

- **AC1 — cluster default Map is the cartography graph.** For `perseus_cloud`, the
  default Map renders the cartography nodes-and-edges graph via the **shared d3-dag
  component from 100-10** (regions = nodes, `adjacent` = connectivity edges) — NOT
  the orrery, and NOT the retired `cartographyLayout.ts` SVG. *Test (wiring,
  CLAUDE.md mandate):* assert the cartography graph mounts as the default Map for a
  cluster world, sourced from the shared component.
- **AC2 — drill-down to per-system orrery + back.** Selecting/entering a node
  drills into that system's orrery; a back affordance returns to the galactic
  graph. *Test:* simulate node-select → assert orrery view for that node renders;
  assert back returns to the graph. *Edge case:* selecting the currently-occupied
  node vs a remote node — confirm intended behavior (drill is by node, the orrery
  only loads where a system file exists, see AC5).
- **AC3 — `orbital: bool` retired → scale/drill state.** The whole-Map toggle is
  replaced by a campaign↔local scale/drill state. *Test:* assert `orbital` boolean
  no longer gates the whole Map; assert state transitions campaign ↔ local. Amends
  #748 — **do not regress** its verified orrery rendering.
- **AC4 — single-system world collapses to orrery-as-Map.** `coyote_star` (one
  graph node) shows the orrery as the Map (two scales collapse to one — derivable
  from node count, no new flag). *Test:* load `coyote_star`; assert Map = orrery,
  no cartography-graph scale presented.
- **AC5 — graceful "no local chart" on unauthored node.** Drilling into a node
  with no authored orrery (no `systems/<id>.yaml`) shows a legible "no local chart"
  state — not a crash or blank. *Test:* drill into an unauthored node → assert the
  empty-state UI renders. (Mirrors 98-2 AC3's server fail-loud: the graph still
  shows the node; only the orrery drill-down is unavailable.)

## Assumptions

- **100-10 is merged before this story starts** and ships the shared d3-dag component with the drill-aware contract the epic-100 amendment specifies: an active-node prop and a node-select callback. If 100-10 lands without exposing the node-select callback (or without being feed-agnostic), 98-3 is blocked — log a Design Deviation and route back rather than forking the layout. (100-10 is p2, this is p3, so the priority order already favors landing it first.)
- 98-2 (S1) is merged, so drilling into `yula` resolves `systems/yula.yaml` server-side and an unauthored node fails loud server-side — U1's AC5 empty-state is the client face of that fail-loud, not a client-side guess.
- The single-vs-cluster distinction is derivable client-side from the graph's node count (one node → collapse to orrery-as-Map). If the client cannot cheaply tell "single system" from the projection, a small explicit signal may be needed — flag it rather than inferring incorrectly.

## Interaction Patterns

- **Default (campaign scale):** cartography graph — systems as nodes, jump links as edges. This is the top-level Map tab for a cluster world.
- **Drill-in (local scale):** select/enter a node → that system's orrery (calendar-driven body positions). A clear **back** affordance returns to the campaign graph.
- **Single-system world:** no campaign scale to show — the orrery *is* the Map (no drill affordance needed).
- **Unauthored node:** drill shows a legible "no local chart for this system yet" empty state; the node remains a valid jump destination on the graph.

## Accessibility Requirements

- The scale/drill transition must be operable and discoverable without relying solely on the d3-dag graph's visual layout — the back affordance and node-select must be keyboard-reachable and labelled. Defer detailed a11y tokens to the shared component (100-10) where layout-level concerns live; this story owns the drill-control affordances.

## Visual Constraints

- Render strictly through the shared d3-dag component's visual contract (100-10 owns layout, node/edge styling, determinism). 98-3 adds only the scale/drill chrome (back affordance, empty-state panel) and must inherit the active theme tokens the same way the rest of the GameBoard does — do not introduce a parallel styling path for the Map.
