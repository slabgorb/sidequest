---
parent: context-epic-54.md
workflow: tdd
---

# Story 54-9: `LocationPanel.tsx` — Location tab between Map and Knowledge

## Business Context

The player-facing terminus of Epic 54. A new dockview tab between `map` and `knowledge` renders the current region/room's prose, appends any active encounter overlay's `prose_suffix`, and shows a small "Overlay active" pip with tooltip when one or more overlays are merged.

**Zork-Problem reinforced** (spec §6.1): entity chips are **NOT** rendered. The manifest stays server-side contract data. Surfacing it as clickable verbs is itself a Zork violation. The `entities[]` field arrives at the client and is mirrored into `state.currentLocation.entities` for completeness, but the component does not render it.

**Audience:** Every seated PC in the playgroup. The panel is read-only chrome — useful when the prose scrolls off, when a returning player needs the room described again, or when an overlay landed mid-scene. Alex benefits most: re-reading the room without asking is free for him; rushing is costly.

**Expected outcome:** A new "Location" tab appears in the right tab strip between Map and Knowledge when the server has delivered a `LOCATION_DESCRIPTION`. Pressing `l` jumps to it. Base prose + (optionally) overlay prose render with the existing genre-theme typography tokens. No entity chips.

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-9-location-panel-ui.md` — task-by-task TDD guide.

**Key files:**
- `sidequest-ui/src/providers/GameStateProvider.tsx` — `ClientGameState.currentLocation: LocationDescriptionPayload | null`.
- `sidequest-ui/src/hooks/useStateMirror.ts` — two new handlers: `LOCATION_DESCRIPTION` (full replace), `LOCATION_OVERLAY_CHANGED` (overlays-only replace + delta-before-baseline buffering per spec §6.3).
- `sidequest-ui/src/components/LocationPanel.tsx` (new) — prose-only React component.
- `sidequest-ui/src/components/GameBoard/widgets/LocationWidget.tsx` (new) — adapter mirroring `KnowledgeWidget`.
- `sidequest-ui/src/components/GameBoard/widgetRegistry.ts` — `WidgetId` + `WIDGET_REGISTRY` entry; hotkey `l`; `dataGated: true`.
- `sidequest-ui/src/components/GameBoard/GameBoard.tsx` — `currentLocation` prop, `availableWidgets` conditional, `renderWidgetContent` case, `rightGroupOrder` slot between `map` and `knowledge`.
- `sidequest-ui/src/App.tsx` — forwards `state.currentLocation` to `<GameBoard currentLocation={...} />`.

**Patterns to follow:**
- Mirror `JournalView.tsx` / `KnowledgeJournal.tsx` / `InventoryPanel.tsx` (`FOLIO` palette via genre-theme CSS custom properties per ADR-079).
- `useStateMirror` idempotent-replay pattern — recompute everything from `messages[]` each call.
- Delta-before-baseline buffering per spec §6.3: a `LOCATION_OVERLAY_CHANGED` arriving before a `LOCATION_DESCRIPTION` is **buffered**, not dropped; merges into the next matching baseline.
- Mismatched-region delta after a room change is **dropped silently** (room change is the truth source).
- ADR-026 state-mirror integration — new slice on `ClientGameState`, same provider, same persistence.

**What NOT to touch:**
- The `entities[]` field is mirrored but not rendered (Zork doctrine — load-bearing).
- Snake-case `region_id` is rendered verbatim in v1 — server-supplied `display_name` is a future seam.
- Multi-language prose (out of scope per spec §2).
- Per-PC perception filtering (spec §9 open question).

## Scope Boundaries

**In scope:**
- `ClientGameState.currentLocation` field + EMPTY_GAME_STATE update.
- `useStateMirror` handlers for both new MessageTypes.
- `LocationPanel.tsx` component (header + base prose + overlay prose + pip + empty state).
- `LocationWidget.tsx` adapter.
- `widgetRegistry.ts` entry (`l` hotkey, `dataGated: true`).
- `GameBoard.tsx` wiring (prop, availability gate, render case, dock order).
- `App.tsx` prop forwarding.

**Out of scope:**
- Entity chips / clickable manifest (Zork doctrine).
- Image regeneration on overlay (spec §2 out-of-scope).
- Audio cues bound to entities (spec §2 out-of-scope).
- Per-PC perception filtering.
- Server-supplied display name distinct from `region_id`.

## AC Context

**AC-1:** `ClientGameState.currentLocation: LocationDescriptionPayload | null` exists; `EMPTY_GAME_STATE` defaults it to `null`.

**AC-2:** `useStateMirror` handles `LOCATION_DESCRIPTION` as a full replace of `currentLocation`; a later message replaces the prior one entirely.

**AC-3:** `LOCATION_OVERLAY_CHANGED` arriving **after** a matching baseline replaces only the `overlays` slice; a baseline for a different region drops a buffered delta; a delta for the wrong region after the baseline is dropped silently.

**AC-4:** `LOCATION_OVERLAY_CHANGED` arriving **before** any baseline is buffered as `pendingOverlays`; the next matching `LOCATION_DESCRIPTION` merges the buffered overlays into its payload.

**AC-5:** `LocationPanel` renders `region_id` in a header, terrain badge when present, base prose split on blank lines into paragraphs, overlay prose paragraphs visually distinct (dashed separator + accent colour + italic), and an "Overlay active" pip with tooltip listing contributing encounter ids when at least one overlay is merged.

**AC-6:** `LocationPanel` renders a graceful "No location yet." block when `data` is `null`.

**AC-7:** **(Zork doctrine — load-bearing AC.)** `LocationPanel` does NOT render any element with testid `location-entity-chip` or `location-entity-list`, and does NOT render raw entity labels in the rendered DOM. A test asserts the absence explicitly.

**AC-8:** `widgetRegistry.ts` lists `location` with `hotkey: "l"`, `dataGated: true`. `GameBoard.tsx` adds `location` to `availableWidgets` only when `currentLocation` is non-null. `rightGroupOrder` places `location` between `map` and `knowledge`.

**AC-9:** `App.tsx` reads `state.currentLocation` and forwards it to `<GameBoard currentLocation={...} />`.

**AC-10:** A wiring test mounts the full GameBoard with `currentLocation` non-null and asserts the `location-panel` testid is present in the DOM. The same test with `currentLocation={null}` asserts the panel is NOT rendered.

**AC-11:** `just check-all` green; `npx tsc --noEmit` clean.
