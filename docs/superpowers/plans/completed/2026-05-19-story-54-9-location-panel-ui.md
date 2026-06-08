# Story 54-9: LocationPanel UI — new tab between Map and Knowledge

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the player-facing Location panel. Renders the base prose description for the current region/room, appends any active encounter overlay's `prose_suffix`, and shows a small "Overlay active" pip when one or more overlays are merged. The panel mounts as a new dockview tab between `map` and `knowledge`, mirrors `JournalView` / `KnowledgeJournal` / `InventoryPanel` patterns, and integrates with the existing state-mirror (ADR-026) via two new typed handlers: `LOCATION_DESCRIPTION` (snapshot, replaces `state.currentLocation`) and `LOCATION_OVERLAY_CHANGED` (delta, replaces `state.currentLocation.overlays`).

**Architecture (Zork-Problem reinforced):** Entity chips are **not** rendered. The manifest stays server-side contract data per spec §6.1 — surfacing it as clickable verbs would be a Zork violation. The panel renders only prose. The `entities` field on `LocationDescriptionPayload` arrives at the client (the type is shared with 54-2's payload), is mirrored into `state.currentLocation.entities` for completeness and for any future operator-side debug surfacing, but the component this story creates does not render it.

Five surfaces:

1. **`src/types/payloads.ts`** — already carries the `LocationDescriptionPayload`, `LocationOverlayChangedPayload`, `LocationEntity`, `LocationDescriptionOverlaySummary` types from 54-2 and 54-7. No new types here.
2. **`src/providers/GameStateProvider.tsx`** — extend `ClientGameState` with `currentLocation: LocationDescriptionPayload | null`. The persistence (sessionStorage / localStorage) path keeps it transparently.
3. **`src/hooks/useStateMirror.ts`** — two new branches that mirror `LOCATION_DESCRIPTION` (full replace) and `LOCATION_OVERLAY_CHANGED` (overlays-only replace). The delta-before-baseline case is the standard pattern: the delta is buffered as a pending overlays replacement that lands when the next `LOCATION_DESCRIPTION` arrives — spec §6.3 specifies this exact behavior.
4. **`src/components/LocationPanel.tsx`** — the React component: header (region/room name + terrain badge), base prose paragraphs, overlay prose paragraphs (visually distinct), "Overlay active" pip with tooltip when at least one overlay is merged. Empty/null `currentLocation` returns a graceful "No location yet." block per `sidequest-ui/CLAUDE.md`'s no-stubbing principle (this IS the expected absence shape, not a placeholder).
5. **`src/components/GameBoard/`** — widget plumbing: a new `LocationWidget.tsx` wrapper, a `"location"` entry in `WidgetId`/`WIDGET_REGISTRY` (with hotkey `l`), the `"location"` slot in `rightGroupOrder` between `map` and `knowledge`, render case in `renderWidgetContent`, and `available.add("location")` in `availableWidgets`. Tab visible only when `state.currentLocation` is non-null (`dataGated: true`) per spec §6.1.

**Tech Stack:** React, TypeScript (strict, `erasableSyntaxOnly`), Vitest + React Testing Library. CSS-custom-properties for genre-theme integration (ADR-079).

**Workflow:** tdd.

**Depends on:** 54-2 (`LocationDescriptionPayload` + `LOCATION_DESCRIPTION` MessageType + TS types), 54-7 (`LocationOverlayChangedPayload` + `LOCATION_OVERLAY_CHANGED` MessageType).

**Branch:** `feat/54-9-location-panel-ui` (off `develop`; subrepo `sidequest-ui`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `sidequest-ui/src/providers/GameStateProvider.tsx` | modify | Extend `ClientGameState` with `currentLocation: LocationDescriptionPayload \| null`. Extend `EMPTY_GAME_STATE`. Persistence already handles arbitrary fields. |
| `sidequest-ui/src/hooks/useStateMirror.ts` | modify | Two new handlers — `LOCATION_DESCRIPTION` replaces `current.currentLocation`; `LOCATION_OVERLAY_CHANGED` replaces `current.currentLocation.overlays` only. Delta-before-baseline buffering pattern: pending overlays carry forward until the next baseline arrives. |
| `sidequest-ui/src/components/LocationPanel.tsx` | create | Player-facing panel. Pure presentation; takes `data: LocationDescriptionPayload \| null` prop. No entity-chip rendering (Zork doctrine). |
| `sidequest-ui/src/components/GameBoard/widgets/LocationWidget.tsx` | create | Adapter — `LocationWidget({ data })` → `<LocationPanel data={data} />`. Mirrors `KnowledgeWidget` / `InventoryWidget`. |
| `sidequest-ui/src/components/GameBoard/widgetRegistry.ts` | modify | Add `"location"` to `WidgetId` union and `WIDGET_REGISTRY`. Hotkey `l`. `dataGated: true`. |
| `sidequest-ui/src/components/GameBoard/GameBoard.tsx` | modify | Add `currentLocation?: LocationDescriptionPayload \| null` to `GameBoardProps`. Wire to `availableWidgets`, `renderWidgetContent` (`case "location"`), and `rightGroupOrder` (between `map` and `knowledge`). |
| `sidequest-ui/src/App.tsx` | modify | Read `state.currentLocation` from the game-state provider and forward to `<GameBoard currentLocation={...} />`. |
| `sidequest-ui/src/components/__tests__/LocationPanel.test.tsx` | create | Component rendering tests. |
| `sidequest-ui/src/hooks/__tests__/useStateMirror-location.test.tsx` | create | State-mirror tests for both message types + delta-before-baseline buffering. |
| `sidequest-ui/src/components/GameBoard/__tests__/GameBoard-location-tab.test.tsx` | create | Wiring test — the `location` tab appears in the right group when `currentLocation` is non-null, and forwards the data into the rendered LocationPanel. |

---

### Task 1: Extend `ClientGameState` with `currentLocation`

**Files:**
- Modify: `sidequest-ui/src/providers/GameStateProvider.tsx`

- [ ] **Step 1: Add the field**

In `sidequest-ui/src/providers/GameStateProvider.tsx`, around line 65 (inside the `ClientGameState` interface, near `magicState`), add:

```typescript
  /**
   * Story 54-9 / ADR-109: persistent location description for the
   * currently rendered region/room. Mirrored from server's
   * LOCATION_DESCRIPTION (snapshot) and LOCATION_OVERLAY_CHANGED (delta).
   * Null when the player has not entered any room with a manifest yet —
   * legacy saves and pre-54 worlds remain valid in this shape.
   */
  currentLocation?: LocationDescriptionPayload | null;
```

Add the import at the top of the file (alongside the other `@/types/payloads` imports — check if a `LocationDescriptionPayload` import line already exists; if not, add it):

```typescript
import type { LocationDescriptionPayload } from '@/types/payloads';
```

If `@/types/payloads` is not imported here yet, use the relative path style the file already uses (`../types/payloads`) — keep file-local convention.

- [ ] **Step 2: Confirm the type compiles**

```bash
cd sidequest-ui && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add sidequest-ui/src/providers/GameStateProvider.tsx
git commit -m "feat(54-9): ClientGameState.currentLocation field

LocationDescriptionPayload-shaped slice mirrored from
LOCATION_DESCRIPTION / LOCATION_OVERLAY_CHANGED. Null when no manifest
has been delivered yet (legacy saves, pre-54 worlds, chargen scenes
without a room)."
```

---

### Task 2: Mirror `LOCATION_DESCRIPTION` and `LOCATION_OVERLAY_CHANGED` in `useStateMirror`

**Files:**
- Modify: `sidequest-ui/src/hooks/useStateMirror.ts`
- Test: `sidequest-ui/src/hooks/__tests__/useStateMirror-location.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/hooks/__tests__/useStateMirror-location.test.tsx`:

```typescript
import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import {
  GameStateProvider,
  useGameState,
} from "@/providers/GameStateProvider";
import { useStateMirror } from "@/hooks/useStateMirror";
import { MessageType, type GameMessage } from "@/types/protocol";
import type {
  LocationDescriptionPayload,
  LocationOverlayChangedPayload,
} from "@/types/payloads";

function wrap(children: ReactNode) {
  return <GameStateProvider>{children}</GameStateProvider>;
}

function mirror(messages: GameMessage[]) {
  const { result } = renderHook(
    () => {
      useStateMirror(messages);
      return useGameState();
    },
    {
      wrapper: ({ children }) => (
        <GameStateProvider>{children}</GameStateProvider>
      ),
    },
  );
  return result;
}

function descMsg(payload: LocationDescriptionPayload): GameMessage {
  return {
    type: MessageType.LOCATION_DESCRIPTION,
    payload: payload as unknown as Record<string, unknown>,
    player_id: "",
  };
}

function overlayMsg(payload: LocationOverlayChangedPayload): GameMessage {
  return {
    type: MessageType.LOCATION_OVERLAY_CHANGED,
    payload: payload as unknown as Record<string, unknown>,
    player_id: "",
  };
}

describe("useStateMirror — location (Story 54-9)", () => {
  it("starts with currentLocation null", () => {
    const result = mirror([]);
    expect(result.current.state.currentLocation ?? null).toBeNull();
  });

  it("LOCATION_DESCRIPTION populates currentLocation", () => {
    const payload: LocationDescriptionPayload = {
      region_id: "glenross_pub",
      prose: "The pub door is ajar.",
      terrain: "building",
      entities: [
        {
          id: "bar",
          label: "the bar",
          tier: "real_object",
          binding: { kind: "location_feature", ref: "glenross_arms_bar" },
          affordances: [],
          provenance: "authored",
          promoted_at_turn: null,
          promoted_canon: null,
        },
      ],
      overlays: [],
    };
    const result = mirror([descMsg(payload)]);
    const loc = result.current.state.currentLocation;
    expect(loc).not.toBeNull();
    expect(loc!.region_id).toBe("glenross_pub");
    expect(loc!.prose).toBe("The pub door is ajar.");
    expect(loc!.entities).toHaveLength(1);
  });

  it("a later LOCATION_DESCRIPTION fully replaces the prior one", () => {
    const first: LocationDescriptionPayload = {
      region_id: "glenross_pub",
      prose: "The pub door is ajar.",
      terrain: "building",
      entities: [],
      overlays: [],
    };
    const second: LocationDescriptionPayload = {
      region_id: "sunden_square",
      prose: "The square is quiet at dusk.",
      terrain: "settlement",
      entities: [],
      overlays: [],
    };
    const result = mirror([descMsg(first), descMsg(second)]);
    expect(result.current.state.currentLocation!.region_id).toBe(
      "sunden_square",
    );
    expect(result.current.state.currentLocation!.prose).toBe(
      "The square is quiet at dusk.",
    );
  });

  it("LOCATION_OVERLAY_CHANGED after baseline replaces only the overlays slice", () => {
    const base: LocationDescriptionPayload = {
      region_id: "glenross_pub",
      prose: "The pub door is ajar.",
      terrain: "building",
      entities: [],
      overlays: [],
    };
    const delta: LocationOverlayChangedPayload = {
      region_id: "glenross_pub",
      overlays: [
        {
          encounter_id: "tavern_brawl@glenross_pub",
          prose_suffix: "A chair lies in splinters by the door.",
          entity_delta_count: 1,
        },
      ],
    };
    const result = mirror([descMsg(base), overlayMsg(delta)]);
    const loc = result.current.state.currentLocation!;
    expect(loc.region_id).toBe("glenross_pub");
    // Base prose unchanged.
    expect(loc.prose).toBe("The pub door is ajar.");
    // Overlays replaced.
    expect(loc.overlays).toHaveLength(1);
    expect(loc.overlays[0].prose_suffix).toBe(
      "A chair lies in splinters by the door.",
    );
  });

  it("LOCATION_OVERLAY_CHANGED before baseline buffers and lands on next baseline", () => {
    /* Spec §6.3: server emits LOCATION_OVERLAY_CHANGED before baseline
     * (e.g. encounter activates the same frame a session resumes). The
     * UI buffers the delta and merges it when the next baseline arrives.
     */
    const delta: LocationOverlayChangedPayload = {
      region_id: "glenross_pub",
      overlays: [
        {
          encounter_id: "tavern_brawl@glenross_pub",
          prose_suffix: "A chair lies in splinters by the door.",
          entity_delta_count: 1,
        },
      ],
    };
    const baseline: LocationDescriptionPayload = {
      region_id: "glenross_pub",
      prose: "The pub door is ajar.",
      terrain: "building",
      entities: [],
      overlays: [],
    };
    const result = mirror([overlayMsg(delta), descMsg(baseline)]);
    const loc = result.current.state.currentLocation!;
    expect(loc.region_id).toBe("glenross_pub");
    expect(loc.prose).toBe("The pub door is ajar.");
    expect(loc.overlays).toHaveLength(1);
    expect(loc.overlays[0].prose_suffix).toBe(
      "A chair lies in splinters by the door.",
    );
  });

  it("LOCATION_OVERLAY_CHANGED with mismatched region_id is ignored", () => {
    const base: LocationDescriptionPayload = {
      region_id: "glenross_pub",
      prose: "The pub door is ajar.",
      terrain: "building",
      entities: [],
      overlays: [],
    };
    const delta: LocationOverlayChangedPayload = {
      region_id: "some_other_room",
      overlays: [
        {
          encounter_id: "x@some_other_room",
          prose_suffix: "Should not appear.",
          entity_delta_count: 0,
        },
      ],
    };
    const result = mirror([descMsg(base), overlayMsg(delta)]);
    const loc = result.current.state.currentLocation!;
    expect(loc.region_id).toBe("glenross_pub");
    expect(loc.overlays).toHaveLength(0);
  });

  it("LOCATION_OVERLAY_CHANGED with empty overlays clears the slice", () => {
    const base: LocationDescriptionPayload = {
      region_id: "glenross_pub",
      prose: "The pub door is ajar.",
      terrain: "building",
      entities: [],
      overlays: [
        {
          encounter_id: "old@glenross_pub",
          prose_suffix: "old suffix",
          entity_delta_count: 0,
        },
      ],
    };
    const delta: LocationOverlayChangedPayload = {
      region_id: "glenross_pub",
      overlays: [],
    };
    const result = mirror([descMsg(base), overlayMsg(delta)]);
    expect(result.current.state.currentLocation!.overlays).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-ui && npx vitest run src/hooks/__tests__/useStateMirror-location.test.tsx
```
Expected: FAIL — `currentLocation` is never populated.

- [ ] **Step 3: Wire the handlers**

Open `sidequest-ui/src/hooks/useStateMirror.ts`. Two changes:

(a) Inside the per-message replay loop, add `let currentLocation: LocationDescriptionPayload | null = null;` and `let pendingOverlays: LocationOverlayChangedPayload | null = null;` declared alongside `current`/`journal`/`knowledge` at the top of the loop body (around line 57).

(b) Add the two new branches just before the existing `if (msg.type !== MessageType.NARRATION && msg.type !== MessageType.TURN_STATUS)` early-return (around line 185):

```typescript
      // Story 54-9 / ADR-109: persistent location description snapshot.
      // Full replace of currentLocation. If a delta was buffered (delta-
      // before-baseline per spec §6.3) and its region_id matches this
      // baseline, merge it in by replacing the baseline's overlays slice.
      if (msg.type === MessageType.LOCATION_DESCRIPTION) {
        const payload = msg.payload as unknown as LocationDescriptionPayload;
        if (
          pendingOverlays !== null &&
          pendingOverlays.region_id === payload.region_id
        ) {
          currentLocation = {
            ...payload,
            overlays: [...pendingOverlays.overlays],
          };
          pendingOverlays = null;
        } else {
          currentLocation = payload;
          // Drop a buffered delta whose region_id no longer matches —
          // it belonged to a room we never received a baseline for and
          // the player has moved on.
          pendingOverlays = null;
        }
        continue;
      }

      // Story 54-9: per-encounter overlay delta. When a baseline exists
      // for the same region_id, replace its overlays slice. Otherwise
      // buffer the delta until the baseline arrives.
      if (msg.type === MessageType.LOCATION_OVERLAY_CHANGED) {
        const payload =
          msg.payload as unknown as LocationOverlayChangedPayload;
        if (
          currentLocation !== null &&
          currentLocation.region_id === payload.region_id
        ) {
          currentLocation = {
            ...currentLocation,
            overlays: [...payload.overlays],
          };
        } else if (currentLocation !== null) {
          // Baseline exists but is for a DIFFERENT region — ignore.
          // The delta is stale (room change happened mid-stream).
        } else {
          // Delta-before-baseline buffering (spec §6.3).
          pendingOverlays = payload;
        }
        continue;
      }
```

(c) Add the imports at the top of the file (alongside the existing `@/types/payloads` import):

```typescript
import type {
  FootnoteData,
  LocationDescriptionPayload,
  LocationOverlayChangedPayload,
  NarrationMessage,
} from '../types/payloads';
```

(d) After the replay loop completes, include `currentLocation` in the `setState` call. Find the existing call site (`grep -n "setState({" sidequest-ui/src/hooks/useStateMirror.ts`) and add `currentLocation` to the object:

```typescript
    setState({
      ...current,
      journal,
      knowledge,
      depletions,
      resourceAlerts,
      currentLocation,
    });
```

(Keep the rest of the object as-is — only `currentLocation` is added.)

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-ui && npx vitest run src/hooks/__tests__/useStateMirror-location.test.tsx
```
Expected: 7 passed.

- [ ] **Step 5: Confirm no regression in the existing state-mirror tests**

```bash
cd sidequest-ui && npx vitest run src/hooks/__tests__/
```
Expected: full mirror suite green.

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/hooks/useStateMirror.ts \
        sidequest-ui/src/hooks/__tests__/useStateMirror-location.test.tsx
git commit -m "feat(54-9): mirror LOCATION_DESCRIPTION + LOCATION_OVERLAY_CHANGED

LOCATION_DESCRIPTION is a full replace of state.currentLocation;
LOCATION_OVERLAY_CHANGED replaces the overlays slice only (when the
region_id matches the current baseline) or buffers until the next
baseline arrives (delta-before-baseline per spec §6.3). Mismatched-
region deltas after a room change are dropped silently — the
room-change render is the truth source."
```

---

### Task 3: `LocationPanel.tsx` component

**Files:**
- Create: `sidequest-ui/src/components/LocationPanel.tsx`
- Test: `sidequest-ui/src/components/__tests__/LocationPanel.test.tsx`

- [ ] **Step 1: Write failing component tests**

Create `sidequest-ui/src/components/__tests__/LocationPanel.test.tsx`:

```typescript
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LocationPanel } from "@/components/LocationPanel";
import type { LocationDescriptionPayload } from "@/types/payloads";

function payload(
  over: Partial<LocationDescriptionPayload> = {},
): LocationDescriptionPayload {
  return {
    region_id: "glenross_pub",
    prose: "The pub door is ajar.",
    terrain: "building",
    entities: [],
    overlays: [],
    ...over,
  };
}

describe("LocationPanel (Story 54-9)", () => {
  it("renders an empty-state message when data is null", () => {
    render(<LocationPanel data={null} />);
    expect(screen.getByTestId("location-empty")).toBeTruthy();
  });

  it("renders the region_id as a header", () => {
    render(<LocationPanel data={payload()} />);
    expect(screen.getByTestId("location-header")).toBeTruthy();
    expect(screen.getByTestId("location-header").textContent).toContain(
      "glenross_pub",
    );
  });

  it("renders the base prose paragraphs", () => {
    render(
      <LocationPanel
        data={payload({
          prose: "The pub door is ajar.\n\nA candle gutters on the bar.",
        })}
      />,
    );
    const paras = screen.getAllByTestId(/^location-prose-paragraph-/);
    expect(paras).toHaveLength(2);
    expect(paras[0].textContent).toBe("The pub door is ajar.");
    expect(paras[1].textContent).toBe("A candle gutters on the bar.");
  });

  it("renders a terrain badge when terrain is present", () => {
    render(<LocationPanel data={payload({ terrain: "settlement" })} />);
    const badge = screen.getByTestId("location-terrain-badge");
    expect(badge.textContent?.toLowerCase()).toContain("settlement");
  });

  it("omits the terrain badge when terrain is null", () => {
    render(<LocationPanel data={payload({ terrain: null })} />);
    expect(screen.queryByTestId("location-terrain-badge")).toBeNull();
  });

  it("renders the overlay-active pip when at least one overlay is merged", () => {
    render(
      <LocationPanel
        data={payload({
          overlays: [
            {
              encounter_id: "tavern_brawl@glenross_pub",
              prose_suffix: "A chair lies in splinters by the door.",
              entity_delta_count: 1,
            },
          ],
        })}
      />,
    );
    expect(screen.getByTestId("location-overlay-pip")).toBeTruthy();
  });

  it("omits the pip when no overlays are merged", () => {
    render(<LocationPanel data={payload({ overlays: [] })} />);
    expect(screen.queryByTestId("location-overlay-pip")).toBeNull();
  });

  it("renders overlay prose paragraphs visually separated from base", () => {
    render(
      <LocationPanel
        data={payload({
          overlays: [
            {
              encounter_id: "tavern_brawl@glenross_pub",
              prose_suffix: "A chair lies in splinters by the door.",
              entity_delta_count: 0,
            },
          ],
        })}
      />,
    );
    const overlaySection = screen.getByTestId("location-overlay-prose");
    expect(overlaySection).toBeTruthy();
    expect(overlaySection.textContent).toContain(
      "A chair lies in splinters by the door.",
    );
  });

  it("does NOT render entity chips (Zork doctrine — spec §6.1)", () => {
    render(
      <LocationPanel
        data={payload({
          entities: [
            {
              id: "bar",
              label: "the bar",
              tier: "real_object",
              binding: { kind: "location_feature", ref: "glenross_arms_bar" },
              affordances: [],
              provenance: "authored",
              promoted_at_turn: null,
              promoted_canon: null,
            },
            {
              id: "cobwebs",
              label: "cobwebs",
              tier: "flavor_only",
              binding: null,
              affordances: [],
              provenance: "authored",
              promoted_at_turn: null,
              promoted_canon: null,
            },
          ],
        })}
      />,
    );
    expect(screen.queryByTestId("location-entity-chip")).toBeNull();
    expect(screen.queryByTestId("location-entity-list")).toBeNull();
    // The manifest must not bleed into the prose either.
    expect(screen.queryByText(/the bar$/)).toBeNull();
  });

  it("aggregates overlay tooltip names when multiple overlays are merged", () => {
    render(
      <LocationPanel
        data={payload({
          overlays: [
            {
              encounter_id: "tavern_brawl@glenross_pub",
              prose_suffix: "A chair lies in splinters by the door.",
              entity_delta_count: 1,
            },
            {
              encounter_id: "rain_squall@glenross_pub",
              prose_suffix: "Rain hisses on the cobbles.",
              entity_delta_count: 0,
            },
          ],
        })}
      />,
    );
    const pip = screen.getByTestId("location-overlay-pip");
    const title = pip.getAttribute("title") ?? "";
    expect(title).toContain("tavern_brawl@glenross_pub");
    expect(title).toContain("rain_squall@glenross_pub");
  });
});
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-ui && npx vitest run src/components/__tests__/LocationPanel.test.tsx
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

Create `sidequest-ui/src/components/LocationPanel.tsx`:

```typescript
import type { CSSProperties } from "react";
import type {
  LocationDescriptionOverlaySummary,
  LocationDescriptionPayload,
} from "@/types/payloads";

export interface LocationPanelProps {
  data: LocationDescriptionPayload | null;
}

// Folio palette — mirrors CharacterPanel / InventoryPanel / KnowledgeJournal
// so all dock panels read as the same artifact. Resolved via CSS custom
// properties from useGenreTheme (ADR-079).
const FOLIO = {
  ink: "var(--card-foreground)",
  inkSoft: "var(--muted-foreground)",
  paper: "var(--card)",
  paper2: "var(--muted)",
  accent: "var(--accent)",
  primary: "var(--primary)",
  rule: "var(--border)",
} as const;

const FONT_DISPLAY = "'Pirata One', serif";
const FONT_BODY = "'EB Garamond', serif";

// Story 54-9: this component intentionally renders prose ONLY. The
// LocationEntity manifest arrives in `data.entities` and is mirrored
// into state.currentLocation.entities for server-side debugging and
// future operator surfaces, but rendering the manifest as clickable
// entries is a Zork-Problem violation (CLAUDE.md doctrine; spec §6.1
// "Reinforced exclusion"). Do not add entity chips here.

export function LocationPanel({ data }: LocationPanelProps) {
  if (!data) {
    return (
      <div
        data-testid="location-empty"
        className="p-6"
        style={{
          background: FOLIO.paper,
          color: FOLIO.inkSoft,
          fontFamily: FONT_BODY,
          minHeight: "100%",
        }}
      >
        <p>No location yet.</p>
      </div>
    );
  }

  const baseParagraphs = splitParagraphs(data.prose);
  const overlayParagraphs = data.overlays
    .map((o) => o.prose_suffix)
    .filter((s) => s.length > 0)
    .flatMap(splitParagraphs);

  const overlayTooltip = data.overlays.map((o) => o.encounter_id).join(", ");

  return (
    <div
      data-testid="location-panel"
      className="p-6"
      style={{
        background: FOLIO.paper,
        color: FOLIO.ink,
        fontFamily: FONT_BODY,
        minHeight: "100%",
      }}
    >
      <header
        data-testid="location-header"
        style={{
          fontFamily: FONT_DISPLAY,
          fontSize: "1.4rem",
          color: FOLIO.ink,
          borderBottom: `1px solid ${FOLIO.rule}`,
          paddingBottom: "0.5rem",
          marginBottom: "0.75rem",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          flexWrap: "wrap",
        }}
      >
        <span>{prettifyRegionId(data.region_id)}</span>
        {data.terrain ? (
          <span
            data-testid="location-terrain-badge"
            style={badgeStyle()}
          >
            {data.terrain}
          </span>
        ) : null}
        {data.overlays.length > 0 ? (
          <span
            data-testid="location-overlay-pip"
            title={`Overlay active — ${overlayTooltip}`}
            style={pipStyle()}
          >
            ● Overlay active
          </span>
        ) : null}
      </header>

      <section data-testid="location-base-prose">
        {baseParagraphs.map((p, i) => (
          <p
            key={`base-${i}`}
            data-testid={`location-prose-paragraph-${i}`}
            style={paragraphStyle()}
          >
            {p}
          </p>
        ))}
      </section>

      {overlayParagraphs.length > 0 ? (
        <section
          data-testid="location-overlay-prose"
          style={{
            marginTop: "0.75rem",
            paddingTop: "0.5rem",
            borderTop: `1px dashed ${FOLIO.rule}`,
          }}
        >
          {overlayParagraphs.map((p, i) => (
            <p
              key={`overlay-${i}`}
              style={{
                ...paragraphStyle(),
                fontStyle: "italic",
                color: FOLIO.accent,
              }}
            >
              {p}
            </p>
          ))}
        </section>
      ) : null}
    </div>
  );
}

function splitParagraphs(prose: string): string[] {
  if (!prose) return [];
  return prose
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}

function prettifyRegionId(id: string): string {
  // Region ids are snake_case. The Location header shows them as-is for
  // now; a server-supplied display_name field would be a future seam (54
  // out of scope). Show the id verbatim so the player + Keith always
  // know exactly which room key the panel is rendering.
  return id;
}

function badgeStyle(): CSSProperties {
  return {
    fontFamily: FONT_BODY,
    fontSize: "0.75rem",
    color: FOLIO.inkSoft,
    background: FOLIO.paper2,
    padding: "0.1rem 0.5rem",
    borderRadius: "999px",
    border: `1px solid ${FOLIO.rule}`,
    textTransform: "lowercase",
  };
}

function pipStyle(): CSSProperties {
  return {
    fontFamily: FONT_BODY,
    fontSize: "0.75rem",
    color: FOLIO.primary,
    background: FOLIO.paper2,
    padding: "0.1rem 0.5rem",
    borderRadius: "999px",
    border: `1px solid ${FOLIO.primary}`,
    cursor: "help",
  };
}

function paragraphStyle(): CSSProperties {
  return {
    margin: "0 0 0.6rem 0",
    lineHeight: 1.55,
    fontSize: "0.95rem",
  };
}
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-ui && npx vitest run src/components/__tests__/LocationPanel.test.tsx
```
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/LocationPanel.tsx \
        sidequest-ui/src/components/__tests__/LocationPanel.test.tsx
git commit -m "feat(54-9): LocationPanel — prose-only Location tab

Renders base prose paragraphs, overlay prose paragraphs visually
distinct (dashed separator + accent colour + italic), terrain badge,
'Overlay active' pip with tooltip listing contributing encounter ids.
Manifest NOT rendered as entity chips per Zork-Problem reinforcement
(spec §6.1). Empty state graceful when data is null."
```

---

### Task 4: `LocationWidget.tsx` adapter

**Files:**
- Create: `sidequest-ui/src/components/GameBoard/widgets/LocationWidget.tsx`

- [ ] **Step 1: Create the file**

Create `sidequest-ui/src/components/GameBoard/widgets/LocationWidget.tsx`:

```typescript
import { LocationPanel } from "@/components/LocationPanel";
import type { LocationDescriptionPayload } from "@/types/payloads";

interface LocationWidgetProps {
  data: LocationDescriptionPayload | null;
}

export function LocationWidget({ data }: LocationWidgetProps) {
  return <LocationPanel data={data} />;
}
```

- [ ] **Step 2: Type-check**

```bash
cd sidequest-ui && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add sidequest-ui/src/components/GameBoard/widgets/LocationWidget.tsx
git commit -m "feat(54-9): LocationWidget adapter

Thin wrapper around LocationPanel — matches the KnowledgeWidget /
InventoryWidget pattern so GameBoard's renderWidgetContent only
threads data, not styling."
```

---

### Task 5: Register `location` in `widgetRegistry.ts`

**Files:**
- Modify: `sidequest-ui/src/components/GameBoard/widgetRegistry.ts`

- [ ] **Step 1: Add to `WidgetId`**

In `sidequest-ui/src/components/GameBoard/widgetRegistry.ts`, extend the `WidgetId` type:

```typescript
export type WidgetId =
  | "narrative"
  | "character"
  | "inventory"
  | "map"
  | "ship"
  | "knowledge"
  | "gallery"
  | "audio"
  | "location";
```

- [ ] **Step 2: Add to `WIDGET_REGISTRY`**

Add the entry alphabetically between `knowledge` and `gallery` (or wherever the alphabetical-ish ordering puts it — `location` slots after `knowledge`):

```typescript
  location: {
    id: "location",
    label: "Location",
    hotkey: "l",
    minW: 3,
    minH: 3,
    defaultW: 4,
    defaultH: 5,
    closable: true,
    dataGated: true,
  },
```

- [ ] **Step 3: Type-check**

```bash
cd sidequest-ui && npx tsc --noEmit
```
Expected: any failures here will be in GameBoard.tsx where `WidgetId` is now incomplete in switch statements — Task 6 fixes them. If the immediate `tsc` reports only those downstream errors, proceed.

- [ ] **Step 4: Commit**

```bash
git add sidequest-ui/src/components/GameBoard/widgetRegistry.ts
git commit -m "feat(54-9): register 'location' widget — hotkey L, dataGated"
```

---

### Task 6: Wire `location` into `GameBoard.tsx`

**Files:**
- Modify: `sidequest-ui/src/components/GameBoard/GameBoard.tsx`
- Test: `sidequest-ui/src/components/GameBoard/__tests__/GameBoard-location-tab.test.tsx`

This is the **wiring test** required by CLAUDE.md — proves the panel reaches the live dockview workspace, not just lives in a file.

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-ui/src/components/GameBoard/__tests__/GameBoard-location-tab.test.tsx`:

```typescript
import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { GameBoard } from "@/components/GameBoard/GameBoard";
import type { LocationDescriptionPayload } from "@/types/payloads";

/* The full GameBoard pulls in dockview + many providers; the wiring
 * test here uses the same minimal shim as the existing
 * GameBoard.*.test.tsx files. If a shared test harness exists at
 * sidequest-ui/src/components/GameBoard/__tests__/_harness.ts, use
 * it; otherwise inline a `renderBoard({ currentLocation })` helper that
 * mounts GameBoard with the smallest set of required props.
 */

function renderBoard(currentLocation: LocationDescriptionPayload | null) {
  /* Minimal props — keep in sync with the existing GameBoard test files
   * (search for `<GameBoard ` in sidequest-ui/src/components/GameBoard/__tests__/).
   * The wiring test only needs the layout to mount; payload-specific
   * rendering is tested in LocationPanel.test.tsx. */
  return render(
    <GameBoard
      messages={[]}
      characters={[]}
      onSend={() => {}}
      disabled={false}
      currentLocation={currentLocation}
    />,
  );
}

describe("GameBoard — location tab wiring (Story 54-9)", () => {
  it("renders the LocationPanel when currentLocation is non-null", () => {
    renderBoard({
      region_id: "glenross_pub",
      prose: "The pub door is ajar.",
      terrain: "building",
      entities: [],
      overlays: [],
    });
    // The panel mounts as a dockview tab. Its testid is unique.
    expect(screen.getByTestId("location-panel")).toBeTruthy();
  });

  it("renders the empty-state when currentLocation is null", () => {
    renderBoard(null);
    // The location widget should still mount (dataGated=true means it
    // hides when no data; the panel itself handles null gracefully).
    // The dataGated tab disappears entirely when currentLocation is
    // null per spec §6.1 — assert that the panel is NOT in the DOM.
    expect(screen.queryByTestId("location-panel")).toBeNull();
    expect(screen.queryByTestId("location-empty")).toBeNull();
  });
});
```

(If the existing GameBoard test files use a different mount helper — `grep -n "<GameBoard " sidequest-ui/src/components/GameBoard/__tests__/*.tsx` — adopt that style instead. The two assertions stay the same.)

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-ui && npx vitest run src/components/GameBoard/__tests__/GameBoard-location-tab.test.tsx
```
Expected: FAIL — `currentLocation` is not a prop, panel doesn't mount.

- [ ] **Step 3: Add the prop to `GameBoardProps`**

In `sidequest-ui/src/components/GameBoard/GameBoard.tsx`, add inside `GameBoardProps` (near `mapData`):

```typescript
  /**
   * Story 54-9 / ADR-109: persistent location description for the
   * current room. Mirrored from state.currentLocation. Null when no
   * manifest has been delivered yet; the location tab is hidden in
   * that state (dataGated=true).
   */
  currentLocation?: LocationDescriptionPayload | null;
```

Add the import at the top:

```typescript
import type { LocationDescriptionPayload } from "@/types/payloads";
```

…and `LocationWidget`:

```typescript
import { LocationWidget } from "./widgets/LocationWidget";
```

- [ ] **Step 4: Destructure the new prop in the component function**

Find the `export function GameBoard({ ... }: GameBoardProps) {` destructure (around line 209). Add `currentLocation = null,` to the list (place it near `mapData`).

- [ ] **Step 5: Gate the tab on `currentLocation`**

In `availableWidgets` (around line 277), add the conditional:

```typescript
  const availableWidgets = useMemo(() => {
    const available = new Set<WidgetId>();
    available.add("narrative");
    available.add("character");
    available.add("inventory");
    available.add("map");
    available.add("knowledge");
    available.add("gallery");
    available.add("audio");
    if (worldSlug === "coyote_star") available.add("ship");
    // Story 54-9: Location tab appears only when a manifest has been
    // delivered. Hidden during chargen, on legacy saves with no manifest
    // yet, and in pre-54 worlds without authored entities.
    if (currentLocation) available.add("location");
    return available;
  }, [worldSlug, currentLocation]);
```

- [ ] **Step 6: Add the render case**

In `renderWidgetContent` (around line 413, the `switch (panelId)` block), add a new case between `case "knowledge":` and `case "audio":`:

```typescript
      case "location":
        return <LocationWidget data={currentLocation ?? null} />;
```

Also add `currentLocation` to the `useMemo` dependency array near the bottom of `renderWidgetContent` (around line 449):

```typescript
  }, [messages, thinking, characterSheet, inventoryData, mapData,
      knowledgeEntries, nowPlaying, volumes, muted, currentLocation,
      handleVolumeChange, handleMuteToggle, resources, companions, genreSlug, worldSlug,
      handleResourceThresholdCrossed, characters, currentPlayerId,
      activePlayerId, sealedPlayerIds, magicState, lastOrbitalChart, sendOrbitalIntent,
      sessionBoundEpoch]);
```

- [ ] **Step 7: Add `location` to `rightGroupOrder`**

In the `onDockviewReady` callback (around line 570), insert `"location"` between `"map"` and `"knowledge"`:

```typescript
    const rightGroupOrder: WidgetId[] = [
      "character",
      "inventory",
      "map",
      "location",
      "knowledge",
      "gallery",
      "audio",
    ];
```

- [ ] **Step 8: Confirm green**

```bash
cd sidequest-ui && npx vitest run src/components/GameBoard/__tests__/GameBoard-location-tab.test.tsx
```
Expected: 2 passed.

- [ ] **Step 9: Confirm no regression in other GameBoard tests**

```bash
cd sidequest-ui && npx vitest run src/components/GameBoard/__tests__/
```
Expected: green. If a snapshot test renders the full tab order, update it (the order grew by one). If a hotkey test asserts only 7 widgets, update it to 8.

- [ ] **Step 10: Commit**

```bash
git add sidequest-ui/src/components/GameBoard/GameBoard.tsx \
        sidequest-ui/src/components/GameBoard/__tests__/GameBoard-location-tab.test.tsx
git commit -m "feat(54-9): wire LocationWidget into GameBoard dock

New 'location' tab slots between 'map' and 'knowledge' in
rightGroupOrder. Tab is dataGated (currentLocation !== null) so it
disappears during chargen and on pre-54 worlds without authored
entities. Hotkey 'l' jumps to it."
```

---

### Task 7: Forward `currentLocation` from `App.tsx`

**Files:**
- Modify: `sidequest-ui/src/App.tsx`

- [ ] **Step 1: Read the existing GameBoard call site**

Run:
```bash
grep -n "<GameBoard" sidequest-ui/src/App.tsx
```
The render site is around line 1989 in `GameBoard.tsx`-reference territory; verify by reading 20 lines of context around the `<GameBoard` JSX in `App.tsx`. The prop order in App.tsx already passes `mapData`, `knowledgeEntries`, etc — find that block.

- [ ] **Step 2: Read `state.currentLocation` from the provider**

In `App.tsx`, find where `state` is read from `useGameState()` (`grep -n "useGameState\|state\.location\|state\.characters" sidequest-ui/src/App.tsx | head -5`). Reuse the existing `state` binding.

- [ ] **Step 3: Forward the prop**

Add to the `<GameBoard ...>` JSX (near `mapData={mapData}`):

```tsx
        currentLocation={state.currentLocation ?? null}
```

- [ ] **Step 4: Type-check + lint**

```bash
cd sidequest-ui && npx tsc --noEmit
just client-lint
```
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/App.tsx
git commit -m "feat(54-9): forward state.currentLocation to GameBoard

App.tsx reads currentLocation from the game-state provider (mirrored
by useStateMirror in Task 2) and forwards it as a GameBoard prop so
the dockview Location tab renders the live snapshot."
```

---

### Task 8: Full suite + smoke

- [ ] **Step 1: UI tests**

```bash
just client-test
```
Expected: green.

- [ ] **Step 2: UI lint**

```bash
just client-lint
```
Expected: green.

- [ ] **Step 3: TypeScript strict pass**

```bash
cd sidequest-ui && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 4: Aggregate gate**

```bash
just check-all
```
Expected: green.

- [ ] **Step 5: Manual UI sanity check**

Start the dev stack (`just up`), connect a client, advance to a region with a manifest (e.g. `caverns_and_claudes/caverns_sunden/sunden_square` from the 54-2 fixture), and confirm:

- The "Location" tab appears in the right tab strip between Map and Knowledge.
- Pressing `l` jumps to it.
- The base prose renders as paragraphs.
- When an encounter with `location_overlay` activates (this requires 54-7 server-side wiring being live), the "Overlay active" pip appears and the overlay prose renders in italic below a dashed rule.
- When the encounter resolves, the pip and overlay prose disappear.
- No entity chips render — only prose.

If the manifest content for `sunden_square` is too thin to verify visually, also drive `glenross_pub` (`tea_and_murder/glenross`) once the 54-4 backfill lands. Until then the sanity check is purely "panel renders the seeded fixture".

---

### Self-review checklist

- [ ] **Spec §6.1 coverage:** tab nav placement "between Map and Journal" ✓ (rightGroupOrder); header with region/room name + terrain badge ✓; base prose block ✓; overlay prose block visually distinct ✓; "Overlay active" pip with tooltip ✓; entity manifest UI **NOT rendered** ✓ (`test_does_not_render_entity_chips`); skeleton-loader / graceful absence ✓ (`location-empty` test).
- [ ] **Spec §6.2 coverage:** `LOCATION_DESCRIPTION` consumed as snapshot ✓; `LOCATION_OVERLAY_CHANGED` consumed as delta ✓; state mirror exposes `state.currentLocation: LocationDescription | null` ✓.
- [ ] **Spec §6.3 coverage:** server emits a `LOCATION_DESCRIPTION` for a region the client has never seen → UI accepts and renders (covered by the "later DESC fully replaces" test); server emits `LOCATION_OVERLAY_CHANGED` before baseline → UI buffers the delta until baseline arrives ✓ (delta-before-baseline test); overlay carries `entity_delta` but empty `prose_suffix` → pip shows but no extra prose ✓ (the pip test uses `prose_suffix` text content; need to verify the no-suffix-but-delta-count>0 case too).
- [ ] **Spec §6.3 entity_delta_count > 0 + empty suffix case** — covered implicitly: the pip renders whenever `overlays.length > 0`, regardless of suffix. The `it("renders the overlay-active pip when at least one overlay is merged")` test uses suffix-bearing overlays; add a one-liner if you want explicit coverage of the entity-delta-count-only path — the rendering logic already handles it but the test does not exercise it. Optional follow-up.
- [ ] **Zork-Problem reinforcement:** `test_does_not_render_entity_chips` asserts no `location-entity-chip` / `location-entity-list` testid, AND no raw entity labels in the rendered text. Component file has the inline comment "do not add entity chips here" referencing CLAUDE.md.
- [ ] **Placeholder scan:** no TBDs. Every code block complete. The `prettifyRegionId` snake-case-as-is decision is documented inline (not a TODO).
- [ ] **Type consistency:** `LocationDescriptionPayload` field names match what 54-2 ships (`region_id`, `prose`, `terrain`, `entities`, `overlays`); `LocationDescriptionOverlaySummary` fields match (`encounter_id`, `prose_suffix`, `entity_delta_count`). `state.currentLocation` is the same shape, optional/nullable, throughout.
- [ ] **No silent fallback:** mismatched-region delta after a room change is **dropped** (commented in the mirror); delta-before-baseline is **buffered** (also commented). Both behaviors are explicit, observable via test, and aligned with spec §6.3.
- [ ] **No stub:** every code path implemented. The "No location yet." empty state is the spec's "graceful absence" shape, not a stub.
- [ ] **Wiring test present:** `GameBoard-location-tab.test.tsx` proves the panel reaches the live dockview workspace via the new prop and the new `availableWidgets` gate.
- [ ] **ADR-026 compliance:** new state slice lives on `ClientGameState`, mirrored by `useStateMirror`, persisted by the existing `saveGameStateToStorage` (no new persistence path needed — the existing function serializes the whole state shape).

### Dependencies / handoff

- **Blocked by:** 54-2 (MessageType.LOCATION_DESCRIPTION + payload types in TS), 54-7 (MessageType.LOCATION_OVERLAY_CHANGED + payload types in TS).
- **Unblocks:** Nothing — this is the player-visible terminus.
- **Out of scope:**
  - Entity chips / clickable manifest (spec §2 out-of-scope, §6.1 reinforced exclusion).
  - Image generation bound to entities (POI/room image regeneration on overlay, spec §2 out-of-scope).
  - Per-PC perception filtering of the manifest (spec §9 open question — deferred).
  - Server-supplied display name distinct from `region_id` (would arrive as a payload field; v1 renders `region_id` verbatim).
  - Multi-language prose (spec §2 out-of-scope).
