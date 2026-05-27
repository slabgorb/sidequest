# Epic 69: Gameboard & dice UX polish

## Overview

Playtest-3 surfaced two classes of gameboard friction (UX Designer + Keith, captured in `sq-playtest-pingpong.md`): the 3D dice roll doesn't read as a focal moment, and the opening gameboard buries both the action input and the party's mechanical state. This epic is pure player-facing UI polish in `sidequest-ui` — no server or protocol changes.

**Priority:** P2
**Repo:** orchestrator (work lands in `sidequest-ui` subrepo)
**Stories:** 2 (6 points)

- **69-1** (3pt) — 3D dice camera/scale pull-in + dice-lib wiring audit to real server rolls (ADR-074/075)
- **69-2** (3pt) — Opening gameboard: full-width action input under narrative + co-located high-contrast HP pip scale

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Playtest-3 ping-pong log** (`sq-playtest-pingpong.md`) | Gameboard friction findings (input placement, HP legibility), dice-roll legibility |
| **ADR-036** Multiplayer Turn Coordination | Submit-and-wait turn barrier; peer-action visibility during wait (2026-05-03 amendment) |
| **ADR-074** Dice Resolution Protocol | Player-facing rolls over WebSocket (69-1) |
| **ADR-075** 3D Dice Rendering | Three.js + Rapier overlay (69-1) |
| **ADR-079** Genre Theme System Unification | Theme tokens for high-contrast HP pips (69-2) |

## Background

SideQuest exists so a career GM (Keith) and the playgroup can *play*. Playtest-3 exposed two ways the gameboard undercuts that:

1. **Pacing & input prominence (serves Alex).** Alex is a slower reader/typist who freezes under time pressure. If the action input is small, side-docked, or visually secondary, it amplifies that pressure. A prominent, full-width input under the narrative reinforces the submit-and-wait doctrine (ADR-036): the turn doesn't advance until everyone submits, and the input should *look* like a generous, unhurried invitation.

2. **Mechanical legibility (serves Sebastien & Jade).** The group's two mechanics-first players want the numbers behind the narration visible in the **player-facing** UI. Today HP lives in a Dockview tab (CharacterPanel) the player must click into — it's not glanceable while typing an action. Co-locating a high-contrast HP scale with the input makes the stakes legible without a tab switch.

Both findings are player-UI concerns, **not** dev observability. Nothing in this epic touches OTEL, the GM panel, or watcher telemetry.

## Technical Architecture

All work is in `sidequest-ui` (React/TypeScript, Vite, Tailwind, Dockview-based workspace).

**Layout substrate (`components/GameBoard/GameBoard.tsx`):** flex-column — `BackgroundCanvas` → running header → Dockview tabbed workspace (flex-1; narrative left, character/inventory/map/etc. right tabs) → `TurnStatusPanel` → bottom input area (`shrink-0`, ~line 800) wrapping `PeerRevealList` → `MultiplayerTurnBanner` → optional `ConfrontationOverlay` → `InputBar`.

**Action input (`components/InputBar.tsx`):** already bottom-pinned and full-width; `forwardRef`, props `onSend(text, aside)`, `onReveal(call)` (ADR-036 peer visibility), `round`, `confrontationActive`. Submits via `useGameSocket().send()` from `App.tsx`.

**HP display (existing, reusable):** `CharacterPanel.tsx` renders `EdgeBadge` (text `HP {cur}/{max}`, danger ≤25%) and `FolioEdgeTicks` (diamond pip scale, gold fill / crimson danger). `GenericResourceBar.tsx` is a generic thresholded bar (used for edge/composure pools). **Reuse-first mandate:** 69-2 surfaces the existing pip pattern next to the input rather than authoring a new health widget.

**State flow:** `PARTY_STATUS` WS message → `useStateMirror` → `GameStateProvider` → `useGameState()` subscribers re-render. HP shape is `CharacterSummary { hp, hp_max }` (`types/party.ts`).

**Theme tokens (`hooks/useGenreTheme.ts`, ADR-079):** `--primary` (gold), `--accent`, `--destructive`, semantic `--card`/`--muted`/`--border`/`--foreground`. CharacterPanel's `FOLIO` map already binds these — any new co-located HP scale uses the same tokens for high contrast and genre consistency.

**Test substrate:** Vitest + React Testing Library. `src/test-setup.ts` mocks `matchMedia` (mobile default — override per test for desktop/tablet), `localStorage`, `ResizeObserver`, `fake-indexeddb`. MockWebSocket integration pattern in `src/__tests__/action-reveal-wiring.test.tsx`.

## Cross-Epic Dependencies

**Depends on:**
- ADR-036 (turn coordination) and ADR-079 (theme tokens) — both already live; this epic consumes, doesn't modify them.

**Depended on by:**
- None. Pure polish; no downstream story consumes its output.
