# Unified Inspector — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the live OTEL/GM dashboard and the save-forensics tool into a single React surface (`#/dashboard`, "the Inspector") with a session picker, then delete the duplicate server-rendered HTML pages.

**Architecture:** One React shell over two data sources behind a capability model. `LiveSource` = today's WebSocket reducer (unchanged behavior). `ForensicSource` = REST reads of a saved session, round-scoped. Six event-array tabs (Console, Subsystems, Timing, Prompt, Lore, Encounters) become source-agnostic by feeding them `WatcherEvent[]` from either source via a single `telemetryRow → WatcherEvent` adapter. Two tabs (Timeline, State) swap renderer by source kind; one new tab (Mechanical) renders the per-round census. The two data pipes stay separate at the data layer per the spec — only the UX is unified.

**Tech Stack:** React 18 + TypeScript, Vite, Vitest + @testing-library/react (jsdom). Server: Python/FastAPI (deletions only).

**Spec:** `docs/superpowers/specs/2026-06-14-unified-inspector-design.md`

**Decisions locked at planning (override if wrong):**
- Route stays `#/dashboard` (hash-routed via `DashboardGate`; no router change).
- Forensic event-array tabs are **round-scoped** (show the selected round's telemetry), not whole-save — lazy, no new backend endpoint. Live tabs remain whole-session. This per-source difference is intentional and surfaced in the UI.
- Tool name "Inspector" is cosmetic (header text only).

**Repos & branches:**
- `sidequest-ui` (Parts A, B; stale tooltip fix) — branch `develop`.
- `sidequest-server` (Part C deletions, dead span constants) — branch `develop`.
- `orc-quest` (`.`, `just otel` recipe) — branch `main`.

Each task names its working directory. Run `git` from that directory.

---

## File Structure

**New (sidequest-ui):**
- `src/components/Dashboard/source/types.ts` — source/lens/forensic-bundle TypeScript contracts.
- `src/components/Dashboard/source/telemetryAdapter.ts` — `telemetryRowToWatcherEvent` + derivations.
- `src/components/Dashboard/source/useForensicSource.ts` — REST fetch hook (saves, timeline, bundle, snapshot).
- `src/components/Dashboard/source/useLiveSource.ts` — extracted live reducer/WS (behavior-preserving move).
- `src/components/Dashboard/SessionPicker.tsx` — source/session dropdown.
- `src/components/Dashboard/tabs/ForensicTimelineTab.tsx` — round-boundary timeline + macro strip.
- `src/components/Dashboard/tabs/ForensicStateTab.tsx` — snapshot + per-round drilldown (narrative/events/derived/projection/scrapbook), three truth-tier badging.
- `src/components/Dashboard/tabs/MechanicalTab.tsx` — per-round census diff + trope.

**Modified (sidequest-ui):**
- `src/components/Dashboard/DashboardApp.tsx` — becomes the shell holding source selection.
- `src/components/Dashboard/DashboardTabs.tsx` — add Mechanical tab; capability-gate.
- `src/components/Dashboard/DashboardHeader.tsx` — "Inspector" title; fix "Rust memory" tooltip.
- `src/types/watcher.ts` — (no change; reused).

**Deleted (sidequest-server):**
- `sidequest/server/static/dashboard.html`, `sidequest/server/dashboard.py`
- `sidequest/server/static/forensics.html`, `sidequest/server/forensics.py`
- `app.py` route registrations for both.
- Dead span constants in `telemetry/spans/audio.py`, `telemetry/spans/inventory.py`, `telemetry/spans/_core.py`.

**Modified (orc-quest):** `justfile` — `otel` recipe target.

---

# Part A — Source abstraction + session picker (foundation)

### Task A1: Source & forensic-bundle types

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/source/types.ts`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/source-types.test.ts`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```ts
// src/components/Dashboard/__tests__/source-types.test.ts
import { describe, expect, it } from "vitest";
import { ALL_LENSES, LIVE_CAPABILITIES, FORENSIC_CAPABILITIES } from "../source/types";

describe("source capability model", () => {
  it("declares all nine lenses", () => {
    expect(ALL_LENSES).toHaveLength(9);
    expect(ALL_LENSES).toContain("mechanical");
    expect(ALL_LENSES).toContain("encounters");
  });

  it("live supports everything except mechanical-diff is round-scoped only on forensic", () => {
    expect(LIVE_CAPABILITIES.has("timeline")).toBe(true);
    expect(LIVE_CAPABILITIES.has("encounters")).toBe(true);
  });

  it("forensic supports the full lens set (round-scoped)", () => {
    for (const lens of ALL_LENSES) {
      expect(FORENSIC_CAPABILITIES.has(lens)).toBe(true);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/source-types.test.ts`
Expected: FAIL — `Cannot find module '../source/types'`.

- [ ] **Step 3: Write the implementation**

```ts
// src/components/Dashboard/source/types.ts
import type { WatcherEvent } from "@/types/watcher";

/** The nine lenses the Inspector exposes (one per tab). */
export type Lens =
  | "timeline"
  | "state"
  | "subsystems"
  | "timing"
  | "console"
  | "prompt"
  | "lore"
  | "encounters"
  | "mechanical";

export const ALL_LENSES: Lens[] = [
  "timeline",
  "state",
  "subsystems",
  "timing",
  "console",
  "prompt",
  "lore",
  "encounters",
  "mechanical",
];

export type SourceKind = "live" | "forensic";

export const LIVE_CAPABILITIES: ReadonlySet<Lens> = new Set<Lens>([
  "timeline",
  "state",
  "subsystems",
  "timing",
  "console",
  "prompt",
  "lore",
  "encounters",
  "mechanical",
]);

export const FORENSIC_CAPABILITIES: ReadonlySet<Lens> = new Set<Lens>(ALL_LENSES);

// --- Forensic REST shapes (mirror PgForensicReader, sidequest-server) ---

/** GET /api/debug/saves — one entry per save. */
export interface ForensicSaveEntry {
  slug: string;
  genre: string;
  world: string;
  created_at: string;
  last_played: string;
  last_activity_ts: number;
  telemetry_rows: number;
  mechanical_rows: number;
}

/** GET /api/debug/save/{slug}/timeline — one entry per round. */
export interface ForensicTimelineRound {
  round: number;
  seq_start: number | null;
  seq_end: number | null;
  event_kind_counts: Record<string, number>;
  narrative_authors: string[];
  ts: string;
}

/** A persisted turn_telemetry row (inside the bundle's `telemetry.rows`). */
export interface TelemetryRow {
  seq: number;
  component: string;
  event_type: string;
  ts: string;
  fields: Record<string, unknown>;
}

export interface TelemetryFold {
  rows: TelemetryRow[];
  by_component: Record<string, Record<string, number>>;
  total: number;
  unparseable_seqs: number[];
}

export interface PcMechanicalDiff {
  player_id: string;
  character_name: string;
  seat: number;
  kind: "baseline" | "static" | "moved";
  deltas: Array<[string, string]>;
  absolute?: Record<string, unknown>;
}

export interface ForensicMechanical {
  state: "absent" | "static" | "moved";
  pcs: PcMechanicalDiff[];
  trope:
    | {
        summary: string;
        kind: string;
        turns_since_meaningful: number | null;
        total_beats_fired: number | null;
      }
    | null;
  unparseable_seqs: number[];
}

/** GET /api/debug/save/{slug}/turn/{round} — the full drilldown bundle. */
export interface ForensicBundle {
  round: number;
  narrative: Array<{
    round: number;
    author: string;
    content: string;
    tags: unknown;
    created_at: string;
  }>;
  events: Array<{
    seq: number;
    kind: string;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
  derived: Record<
    string,
    { value: { summary?: string; category?: string }; source_seqs: number[] }
  >;
  projection: Array<{
    event_seq: number;
    player_id: string;
    include: boolean;
    payload: Record<string, unknown>;
  }>;
  scrapbook: Array<Record<string, unknown>>;
  unparseable_seqs: number[];
  telemetry: TelemetryFold;
  mechanical: ForensicMechanical;
}

/** GET /api/debug/save/{slug}/snapshot — raw game_state.snapshot_json (shape varies). */
export type ForensicSnapshot = Record<string, unknown>;

/** What the shell passes to event-array tabs, regardless of source. */
export interface EventArrayView {
  turns: WatcherEvent[];
  allEvents: WatcherEvent[];
  componentMap: Record<string, WatcherEvent[]>;
  promptEvents: WatcherEvent[];
  loreEvents: WatcherEvent[];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/source-types.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/source/types.ts src/components/Dashboard/__tests__/source-types.test.ts
git commit -m "feat(inspector): source + forensic-bundle type contracts"
```

---

### Task A2: Telemetry → WatcherEvent adapter

The bridge that makes the event-array tabs source-agnostic. A persisted `TelemetryRow` becomes a `WatcherEvent`; derivations build the per-tab arrays.

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/source/telemetryAdapter.ts`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/telemetryAdapter.test.ts`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```ts
// src/components/Dashboard/__tests__/telemetryAdapter.test.ts
import { describe, expect, it } from "vitest";
import {
  telemetryRowToWatcherEvent,
  buildEventArrayView,
} from "../source/telemetryAdapter";
import type { TelemetryRow } from "../source/types";

const rows: TelemetryRow[] = [
  { seq: 1, component: "narrator", event_type: "prompt_assembled", ts: "2026-06-14T00:00:00Z", fields: { total_tokens: 100 } },
  { seq: 2, component: "lore", event_type: "lore_retrieval", ts: "2026-06-14T00:00:01Z", fields: { budget: 500 } },
  { seq: 3, component: "orchestrator", event_type: "turn_complete", ts: "2026-06-14T00:00:02Z", fields: { agent_duration_ms: 1200 } },
  { seq: 4, component: "encounter", event_type: "state_transition", ts: "2026-06-14T00:00:03Z", fields: { metric: 2 } },
];

describe("telemetryRowToWatcherEvent", () => {
  it("maps a row to a WatcherEvent with info severity", () => {
    const ev = telemetryRowToWatcherEvent(rows[0]);
    expect(ev.component).toBe("narrator");
    expect(ev.event_type).toBe("prompt_assembled");
    expect(ev.severity).toBe("info");
    expect(ev.timestamp).toBe("2026-06-14T00:00:00Z");
    expect(ev.fields.total_tokens).toBe(100);
  });
});

describe("buildEventArrayView", () => {
  it("partitions rows into the per-tab arrays the live tabs expect", () => {
    const view = buildEventArrayView(rows);
    expect(view.allEvents).toHaveLength(4);
    expect(view.promptEvents).toHaveLength(1);
    expect(view.loreEvents).toHaveLength(1);
    expect(view.turns).toHaveLength(1);
    expect(view.componentMap["encounter"]).toHaveLength(1);
    expect(view.componentMap["narrator"][0].event_type).toBe("prompt_assembled");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/telemetryAdapter.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

```ts
// src/components/Dashboard/source/telemetryAdapter.ts
import type { WatcherEvent, WatcherEventType } from "@/types/watcher";
import type { TelemetryRow, EventArrayView } from "./types";

/** A persisted telemetry row is structurally a WatcherEvent minus severity. */
export function telemetryRowToWatcherEvent(row: TelemetryRow): WatcherEvent {
  return {
    timestamp: row.ts,
    component: row.component,
    // Persisted event_type strings are a superset of WatcherEventType (e.g.
    // "census"); the consuming tabs treat unknown types as opaque strings.
    event_type: row.event_type as WatcherEventType,
    severity: "info",
    fields: row.fields,
  };
}

/** Build the per-tab WatcherEvent arrays the live tabs consume, from rows. */
export function buildEventArrayView(rows: TelemetryRow[]): EventArrayView {
  const allEvents = rows.map(telemetryRowToWatcherEvent);
  const componentMap: Record<string, WatcherEvent[]> = {};
  for (const ev of allEvents) {
    const comp = ev.component || "unknown";
    (componentMap[comp] ??= []).push(ev);
  }
  return {
    allEvents,
    componentMap,
    turns: allEvents.filter((e) => e.event_type === "turn_complete"),
    promptEvents: allEvents.filter((e) => e.event_type === "prompt_assembled"),
    loreEvents: allEvents.filter((e) => e.event_type === "lore_retrieval"),
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/telemetryAdapter.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/source/telemetryAdapter.ts src/components/Dashboard/__tests__/telemetryAdapter.test.ts
git commit -m "feat(inspector): telemetryRow→WatcherEvent adapter + per-tab derivations"
```

---

### Task A3: Forensic source hook

Fetches the saves list, the selected save's timeline, and the selected round's bundle + snapshot. Read-only REST; mirrors `EncounterTab`'s fetch idiom (cancel-on-unmount, throw on non-OK).

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/source/useForensicSource.ts`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/useForensicSource.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/useForensicSource.test.tsx
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useForensicSource } from "../source/useForensicSource";
import type { ForensicSaveEntry } from "../source/types";

const SAVES: ForensicSaveEntry[] = [
  { slug: "perseus_cloud", genre: "space_opera", world: "perseus_cloud", created_at: "x", last_played: "y", last_activity_ts: 2, telemetry_rows: 10, mechanical_rows: 4 },
];

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/api/debug/saves")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(SAVES) });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([{ round: 1, seq_start: 1, seq_end: 9, event_kind_counts: {}, narrative_authors: ["gm"], ts: "t" }]) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

describe("useForensicSource", () => {
  it("loads the saves list on mount", async () => {
    const { result } = renderHook(() => useForensicSource());
    await waitFor(() => expect(result.current.saves).toHaveLength(1));
    expect(result.current.saves[0].slug).toBe("perseus_cloud");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/useForensicSource.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

```ts
// src/components/Dashboard/source/useForensicSource.ts
import { useCallback, useEffect, useState } from "react";
import type {
  ForensicSaveEntry,
  ForensicTimelineRound,
  ForensicBundle,
  ForensicSnapshot,
} from "./types";

const API_BASE = (() => {
  const loc = window.location;
  const host = loc.hostname === "localhost" ? "localhost:8765" : loc.host;
  return `${loc.protocol}//${host}`;
})();

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export interface ForensicSourceState {
  saves: ForensicSaveEntry[];
  selectedSlug: string | null;
  rounds: ForensicTimelineRound[];
  selectedRound: number | null;
  bundle: ForensicBundle | null;
  snapshot: ForensicSnapshot | null;
  error: string | null;
  selectSave: (slug: string) => void;
  selectRound: (round: number) => void;
}

export function useForensicSource(): ForensicSourceState {
  const [saves, setSaves] = useState<ForensicSaveEntry[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [rounds, setRounds] = useState<ForensicTimelineRound[]>([]);
  const [selectedRound, setSelectedRound] = useState<number | null>(null);
  const [bundle, setBundle] = useState<ForensicBundle | null>(null);
  const [snapshot, setSnapshot] = useState<ForensicSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load saves once on mount.
  useEffect(() => {
    let cancelled = false;
    getJSON<ForensicSaveEntry[]>("/api/debug/saves")
      .then((data) => {
        if (!cancelled) setSaves(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load timeline when the selected save changes.
  useEffect(() => {
    if (!selectedSlug) return;
    let cancelled = false;
    setRounds([]);
    setSelectedRound(null);
    setBundle(null);
    setSnapshot(null);
    getJSON<ForensicTimelineRound[]>(
      `/api/debug/save/${selectedSlug}/timeline`,
    )
      .then((data) => {
        if (cancelled) return;
        setRounds(data);
        if (data.length > 0) setSelectedRound(data[data.length - 1].round);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedSlug]);

  // Load bundle + snapshot when the selected round changes.
  useEffect(() => {
    if (!selectedSlug || selectedRound === null) return;
    let cancelled = false;
    Promise.all([
      getJSON<ForensicBundle>(
        `/api/debug/save/${selectedSlug}/turn/${selectedRound}`,
      ),
      getJSON<ForensicSnapshot>(`/api/debug/save/${selectedSlug}/snapshot`),
    ])
      .then(([b, s]) => {
        if (cancelled) return;
        setBundle(b);
        setSnapshot(s);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedSlug, selectedRound]);

  const selectSave = useCallback((slug: string) => {
    setError(null);
    setSelectedSlug(slug);
  }, []);
  const selectRound = useCallback((round: number) => {
    setSelectedRound(round);
  }, []);

  return {
    saves,
    selectedSlug,
    rounds,
    selectedRound,
    bundle,
    snapshot,
    error,
    selectSave,
    selectRound,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/useForensicSource.test.tsx`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/source/useForensicSource.ts src/components/Dashboard/__tests__/useForensicSource.test.tsx
git commit -m "feat(inspector): forensic source hook (saves/timeline/bundle/snapshot, read-only)"
```

---

### Task A4: Session picker

A pure dropdown: "● Live: {slug}" plus each saved session with its row counts (empty mechanical stream flagged ⚠, mirroring forensics.html). Pure-renderer + props, testable.

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/SessionPicker.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/SessionPicker.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/SessionPicker.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SessionPicker } from "../SessionPicker";
import type { ForensicSaveEntry } from "../source/types";

const saves: ForensicSaveEntry[] = [
  { slug: "perseus_cloud", genre: "space_opera", world: "perseus_cloud", created_at: "x", last_played: "y", last_activity_ts: 2, telemetry_rows: 10, mechanical_rows: 4 },
  { slug: "coyote_star", genre: "space_opera", world: "coyote_star", created_at: "x", last_played: "y", last_activity_ts: 1, telemetry_rows: 5, mechanical_rows: 0 },
];

describe("SessionPicker", () => {
  it("renders live option and each save with counts, flags empty census", () => {
    render(
      <SessionPicker
        sourceKind="live"
        selectedSlug={null}
        liveSlug="active_session"
        saves={saves}
        onSelectLive={() => {}}
        onSelectSave={() => {}}
      />,
    );
    expect(screen.getByText(/Live: active_session/)).toBeInTheDocument();
    expect(screen.getByText(/perseus_cloud/)).toBeInTheDocument();
    expect(screen.getByText(/coyote_star/)).toBeInTheDocument();
    // coyote_star has 0 mechanical rows → warning glyph present in its row.
    expect(screen.getByText(/coyote_star.*⚠/)).toBeInTheDocument();
  });

  it("calls onSelectSave when a save is chosen", () => {
    const onSelectSave = vi.fn();
    render(
      <SessionPicker
        sourceKind="live"
        selectedSlug={null}
        liveSlug={null}
        saves={saves}
        onSelectLive={() => {}}
        onSelectSave={onSelectSave}
      />,
    );
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "save:perseus_cloud" } });
    expect(onSelectSave).toHaveBeenCalledWith("perseus_cloud");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/SessionPicker.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

```tsx
// src/components/Dashboard/SessionPicker.tsx
import type { ForensicSaveEntry, SourceKind } from "./source/types";
import { THEME } from "./shared/constants";

interface Props {
  sourceKind: SourceKind;
  selectedSlug: string | null;
  liveSlug: string | null;
  saves: ForensicSaveEntry[];
  onSelectLive: () => void;
  onSelectSave: (slug: string) => void;
}

export function SessionPicker({
  sourceKind,
  selectedSlug,
  liveSlug,
  saves,
  onSelectLive,
  onSelectSave,
}: Props) {
  const value =
    sourceKind === "live" ? "live" : `save:${selectedSlug ?? ""}`;

  return (
    <select
      role="combobox"
      aria-label="Session source"
      value={value}
      onChange={(e) => {
        const v = e.target.value;
        if (v === "live") onSelectLive();
        else if (v.startsWith("save:")) onSelectSave(v.slice("save:".length));
      }}
      style={{
        background: THEME.surface,
        color: THEME.text,
        border: `1px solid ${THEME.border}`,
        fontFamily: "inherit",
        fontSize: 12,
        padding: "4px 8px",
      }}
    >
      <option value="live">
        ● Live: {liveSlug ?? "(no active session)"}
      </option>
      <optgroup label="Saved sessions">
        {saves.map((s) => {
          const warn = s.mechanical_rows === 0 ? " ⚠" : "";
          return (
            <option key={s.slug} value={`save:${s.slug}`}>
              {s.slug} · {s.telemetry_rows} tel · {s.mechanical_rows} census{warn}
            </option>
          );
        })}
      </optgroup>
    </select>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/SessionPicker.test.tsx`
Expected: PASS (2 tests). Note: the `coyote_star.*⚠` matcher relies on the option text containing both; if jsdom splits text nodes, assert with `screen.getByRole("option", { name: /coyote_star.*⚠/ })` instead.

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/SessionPicker.tsx src/components/Dashboard/__tests__/SessionPicker.test.tsx
git commit -m "feat(inspector): session picker (live + saved sessions, empty-census flag)"
```

---

### Task A5: Extract `useLiveSource` (behavior-preserving)

Move the existing reducer + WebSocket + debug-state fetch out of `DashboardApp` into a hook, so the shell can hold either source. **No behavior change** — the existing `DashboardApp-event-parsing.test.tsx` must still pass.

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/source/useLiveSource.ts`
- Modify: `sidequest-ui/src/components/Dashboard/DashboardApp.tsx` (import from the hook; verified in A6)
- Test: existing `src/components/Dashboard/__tests__/DashboardApp-event-parsing.test.tsx` (regression guard)

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Create the hook by moving existing logic**

Move `DashboardState`, `PendingTurnContext`, `emptyPending`, `initialState`, `Action`, `extractTurnKey`, `synthesizeTurnComplete`, `reducer`, `API_BASE`, and `fetchDebugState` from `DashboardApp.tsx` into `useLiveSource.ts`. Wrap the `useReducer` + `useWatcherSocket` + debug-state effects into the hook. Return the live view plus controls.

```ts
// src/components/Dashboard/source/useLiveSource.ts
import { useReducer, useCallback, useEffect } from "react";
import { useWatcherSocket } from "@/hooks/useWatcherSocket";
import type { WatcherEvent, SessionStateView } from "@/types/watcher";

// ... (the moved DashboardState/Action/reducer/synthesizeTurnComplete/
//      extractTurnKey/API_BASE/fetchDebugState — verbatim from DashboardApp) ...

export interface LiveSourceState {
  turns: WatcherEvent[];
  allEvents: WatcherEvent[];
  componentMap: Record<string, WatcherEvent[]>;
  promptEvents: WatcherEvent[];
  loreEvents: WatcherEvent[];
  debugState: SessionStateView[] | null;
  selectedTurn: number | null;
  paused: boolean;
  connected: boolean;
  activeSlug: string | null;
  selectTurn: (i: number | null) => void;
  togglePause: () => void;
  clear: () => void;
  refreshState: () => void;
}

export function useLiveSource(): LiveSourceState {
  const [state, dispatch] = useReducer(reducer, initialState);

  const onEvent = useCallback((event: WatcherEvent) => {
    dispatch({ type: "EVENT", event });
  }, []);
  const { connected } = useWatcherSocket({ onEvent });

  const refreshState = useCallback(async () => {
    try {
      const data = await fetchDebugState();
      dispatch({ type: "SET_DEBUG_STATE", data });
    } catch {
      // Inspector is a dev tool — swallow fetch errors silently.
    }
  }, []);

  useEffect(() => {
    refreshState();
  }, [refreshState]);
  useEffect(() => {
    if (state.turns.length > 0) refreshState();
  }, [state.turns.length, refreshState]);

  const activeSlug: string | null = (() => {
    if (!state.debugState || state.debugState.length === 0) return null;
    const sorted = [...state.debugState].sort(
      (a, b) => (b.last_activity_ts ?? 0) - (a.last_activity_ts ?? 0),
    );
    return sorted[0].session_key;
  })();

  return {
    turns: state.turns,
    allEvents: state.allEvents,
    componentMap: state.componentMap,
    promptEvents: state.promptEvents,
    loreEvents: state.loreEvents,
    debugState: state.debugState,
    selectedTurn: state.selectedTurn,
    paused: state.paused,
    connected,
    activeSlug,
    selectTurn: (i) => dispatch({ type: "SELECT_TURN", index: i }),
    togglePause: () => dispatch({ type: "TOGGLE_PAUSE" }),
    clear: () => dispatch({ type: "CLEAR" }),
    refreshState,
  };
}
```

If `DashboardApp-event-parsing.test.tsx` imports the `reducer` directly, re-export it from `useLiveSource.ts` (`export { reducer }`) and update the test import path. Check the test's imports first:

Run: `grep -n "import" src/components/Dashboard/__tests__/DashboardApp-event-parsing.test.tsx`

- [ ] **Step 2: Run the regression test to verify it still passes**

Run: `npx vitest run src/components/Dashboard/__tests__/DashboardApp-event-parsing.test.tsx`
Expected: PASS (behavior unchanged). Fix import paths until green.

- [ ] **Step 3: Run full dashboard test suite for regressions**

Run: `npx vitest run src/components/Dashboard src/__tests__/EncounterTab.test.tsx`
Expected: PASS (no behavior change yet — `DashboardApp.tsx` still renders identically; the A6 refactor wires the shell).

- [ ] **Step 4: Commit**

```bash
git add src/components/Dashboard/source/useLiveSource.ts src/components/Dashboard/__tests__/DashboardApp-event-parsing.test.tsx
git commit -m "refactor(inspector): extract useLiveSource hook (behavior-preserving)"
```

---

# Part B — Forensic lenses + shell wiring

### Task B1: Forensic Timeline tab (round boundaries)

Pure renderer for the round timeline (`/timeline` data) with a round selector. Replaces the live flame chart when a save is selected.

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/tabs/ForensicTimelineTab.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/ForensicTimelineTab.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/ForensicTimelineTab.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ForensicTimelineTab } from "../tabs/ForensicTimelineTab";
import type { ForensicTimelineRound } from "../source/types";

const rounds: ForensicTimelineRound[] = [
  { round: 1, seq_start: 1, seq_end: 9, event_kind_counts: { NARRATION: 2 }, narrative_authors: ["gm"], ts: "t1" },
  { round: 2, seq_start: 10, seq_end: 18, event_kind_counts: { NARRATION: 3 }, narrative_authors: ["gm", "rux"], ts: "t2" },
];

describe("ForensicTimelineTab", () => {
  it("lists rounds and highlights the selected one", () => {
    render(<ForensicTimelineTab rounds={rounds} selectedRound={2} onSelectRound={() => {}} />);
    expect(screen.getByText(/Round 1/)).toBeInTheDocument();
    expect(screen.getByText(/Round 2/)).toBeInTheDocument();
  });

  it("fires onSelectRound on click", () => {
    const onSelectRound = vi.fn();
    render(<ForensicTimelineTab rounds={rounds} selectedRound={2} onSelectRound={onSelectRound} />);
    fireEvent.click(screen.getByText(/Round 1/));
    expect(onSelectRound).toHaveBeenCalledWith(1);
  });

  it("shows an empty state when there are no rounds", () => {
    render(<ForensicTimelineTab rounds={[]} selectedRound={null} onSelectRound={() => {}} />);
    expect(screen.getByText(/No rounds/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/ForensicTimelineTab.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

```tsx
// src/components/Dashboard/tabs/ForensicTimelineTab.tsx
import type { ForensicTimelineRound } from "../source/types";
import { THEME } from "../shared/constants";

interface Props {
  rounds: ForensicTimelineRound[];
  selectedRound: number | null;
  onSelectRound: (round: number) => void;
}

export function ForensicTimelineTab({ rounds, selectedRound, onSelectRound }: Props) {
  if (rounds.length === 0) {
    return (
      <div style={{ color: THEME.muted, textAlign: "center", padding: 32 }}>
        No rounds recorded for this save.
      </div>
    );
  }
  return (
    <div style={{ padding: 16 }}>
      <ol style={{ listStyle: "none", padding: 0, margin: 0, fontSize: 12 }}>
        {rounds.map((r) => {
          const kinds = Object.entries(r.event_kind_counts)
            .map(([k, n]) => `${k}:${n}`)
            .join("  ");
          const active = r.selectedMatch(selectedRound);
          return (
            <li
              key={r.round}
              onClick={() => onSelectRound(r.round)}
              style={{
                cursor: "pointer",
                padding: "6px 8px",
                borderBottom: `1px solid ${THEME.border}`,
                background: active ? THEME.surface : "transparent",
                color: active ? THEME.accent : THEME.text,
              }}
            >
              <strong>Round {r.round}</strong>{" "}
              <span style={{ color: THEME.muted }}>
                · {r.narrative_authors.join(", ") || "—"} · {kinds || "no events"}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
```

Note: replace `r.selectedMatch(selectedRound)` with `const active = r.round === selectedRound;` declared before the `return` (the inline pseudo-call above is illustrative — use the plain comparison). Corrected body:

```tsx
        {rounds.map((r) => {
          const kinds = Object.entries(r.event_kind_counts)
            .map(([k, n]) => `${k}:${n}`)
            .join("  ");
          const active = r.round === selectedRound;
          return (
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/ForensicTimelineTab.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/tabs/ForensicTimelineTab.tsx src/components/Dashboard/__tests__/ForensicTimelineTab.test.tsx
git commit -m "feat(inspector): forensic round-timeline tab"
```

---

### Task B2: Forensic State / drilldown tab (three truth tiers)

The heart of forensics.html in React: per-round narrative, events, derived KnownFacts (amber/derived), and the terminal snapshot (green/stored). Three-tier color coding via `THEME`.

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/tabs/ForensicStateTab.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/ForensicStateTab.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/ForensicStateTab.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ForensicStateTab } from "../tabs/ForensicStateTab";
import type { ForensicBundle, ForensicSnapshot } from "../source/types";

const bundle: ForensicBundle = {
  round: 1,
  narrative: [{ round: 1, author: "gm", content: "You enter the cave.", tags: [], created_at: "t" }],
  events: [{ seq: 1, kind: "NARRATION", payload: { foo: "bar" }, created_at: "t" }],
  derived: { "fn-cave": { value: { summary: "The cave is dark", category: "location" }, source_seqs: [1] } },
  projection: [],
  scrapbook: [],
  unparseable_seqs: [],
  telemetry: { rows: [], by_component: {}, total: 0, unparseable_seqs: [] },
  mechanical: { state: "absent", pcs: [], trope: null, unparseable_seqs: [] },
};
const snapshot: ForensicSnapshot = { current_region: "cave_mouth", player_dead: false };

describe("ForensicStateTab", () => {
  it("renders derived facts (amber tier) and stored snapshot (green tier)", () => {
    render(<ForensicStateTab bundle={bundle} snapshot={snapshot} />);
    expect(screen.getByText(/The cave is dark/)).toBeInTheDocument();
    expect(screen.getByText(/cave_mouth/)).toBeInTheDocument();
    expect(screen.getByText(/You enter the cave/)).toBeInTheDocument();
  });

  it("shows an empty state when no bundle is loaded", () => {
    render(<ForensicStateTab bundle={null} snapshot={null} />);
    expect(screen.getByText(/Select a round/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/ForensicStateTab.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

```tsx
// src/components/Dashboard/tabs/ForensicStateTab.tsx
import type { ForensicBundle, ForensicSnapshot } from "../source/types";
import { THEME } from "../shared/constants";

interface Props {
  bundle: ForensicBundle | null;
  snapshot: ForensicSnapshot | null;
}

function Section({ title, color, children }: { title: string; color: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ color, fontSize: 11, fontWeight: "bold", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

export function ForensicStateTab({ bundle, snapshot }: Props) {
  if (!bundle) {
    return (
      <div style={{ color: THEME.muted, textAlign: "center", padding: 32 }}>
        Select a round to inspect.
      </div>
    );
  }
  const derivedEntries = Object.entries(bundle.derived);
  return (
    <div style={{ padding: 16, fontSize: 12 }}>
      <Section title="Narrative (this round)" color={THEME.text}>
        {bundle.narrative.map((n, i) => (
          <p key={i} style={{ margin: "4px 0" }}>
            <span style={{ color: THEME.muted }}>{n.author}: </span>
            {n.content}
          </p>
        ))}
      </Section>

      <Section title="Derived — narrator believed (KnownFacts)" color={THEME.amber}>
        {derivedEntries.length === 0 ? (
          <div style={{ color: THEME.muted }}>No facts reconstructed.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              {derivedEntries.map(([id, f]) => (
                <tr key={id} style={{ borderBottom: `1px solid ${THEME.border}` }}>
                  <td style={{ color: THEME.amber, padding: "2px 8px" }}>{f.value.category ?? "—"}</td>
                  <td style={{ padding: "2px 8px" }}>{f.value.summary ?? id}</td>
                  <td style={{ color: THEME.muted, padding: "2px 8px" }}>seqs {f.source_seqs.join(",")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Stored — terminal snapshot (ground truth)" color={THEME.accent}>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", color: THEME.text }}>
          {snapshot && Object.keys(snapshot).length > 0
            ? JSON.stringify(snapshot, null, 2)
            : "(no snapshot stored)"}
        </pre>
      </Section>
    </div>
  );
}
```

(`THEME.amber` is used by the live tabs already; `THEME.accent` is the green/stored accent. If the green tier needs a distinct token, add `stored: "#3fb950"` to `shared/constants.ts` `THEME` and use it — matches forensics.html `--stored`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/ForensicStateTab.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/tabs/ForensicStateTab.tsx src/components/Dashboard/__tests__/ForensicStateTab.test.tsx
git commit -m "feat(inspector): forensic state drilldown (derived/stored truth tiers)"
```

---

### Task B3: Mechanical census tab

Per-PC census diff (baseline/static/moved) + trope summary, the ADR-124 mechanical fold. Forensic-rich; for live it renders the latest `component='mechanical'` rows if present, else a "select a save" note.

**Files:**
- Create: `sidequest-ui/src/components/Dashboard/tabs/MechanicalTab.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/MechanicalTab.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/MechanicalTab.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MechanicalCensus } from "../tabs/MechanicalTab";
import type { ForensicMechanical } from "../source/types";

const moved: ForensicMechanical = {
  state: "moved",
  pcs: [
    { player_id: "p1", character_name: "Rux", seat: 0, kind: "moved", deltas: [["edge", "5→3"], ["location", "cave→tunnel"]] },
  ],
  trope: { summary: "the_betrayal advanced", kind: "moved", turns_since_meaningful: 0, total_beats_fired: 4 },
  unparseable_seqs: [],
};

describe("MechanicalCensus", () => {
  it("renders per-PC deltas and trope summary", () => {
    render(<MechanicalCensus mechanical={moved} />);
    expect(screen.getByText(/Rux/)).toBeInTheDocument();
    expect(screen.getByText(/edge/)).toBeInTheDocument();
    expect(screen.getByText(/5→3/)).toBeInTheDocument();
    expect(screen.getByText(/the_betrayal advanced/)).toBeInTheDocument();
  });

  it("shows absent state", () => {
    render(<MechanicalCensus mechanical={{ state: "absent", pcs: [], trope: null, unparseable_seqs: [] }} />);
    expect(screen.getByText(/No mechanical census/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/MechanicalTab.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

```tsx
// src/components/Dashboard/tabs/MechanicalTab.tsx
import type { ForensicMechanical } from "../source/types";
import { THEME } from "../shared/constants";

export function MechanicalCensus({ mechanical }: { mechanical: ForensicMechanical }) {
  if (mechanical.state === "absent" || mechanical.pcs.length === 0) {
    return (
      <div style={{ color: THEME.muted, textAlign: "center", padding: 32 }}>
        No mechanical census for this round.
      </div>
    );
  }
  return (
    <div style={{ padding: 16, fontSize: 12 }}>
      {mechanical.pcs.map((pc) => (
        <div key={pc.player_id} style={{ marginBottom: 12, borderBottom: `1px solid ${THEME.border}`, paddingBottom: 8 }}>
          <div style={{ color: THEME.accent, fontWeight: "bold" }}>
            {pc.character_name} <span style={{ color: THEME.muted }}>(seat {pc.seat} · {pc.kind})</span>
          </div>
          {pc.deltas.length === 0 ? (
            <div style={{ color: THEME.muted }}>no change</div>
          ) : (
            <table style={{ borderCollapse: "collapse", marginTop: 4 }}>
              <tbody>
                {pc.deltas.map(([field, change], i) => (
                  <tr key={i}>
                    <td style={{ color: THEME.purple, padding: "1px 8px" }}>{field}</td>
                    <td style={{ padding: "1px 8px" }}>{change}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
      {mechanical.trope && (
        <div style={{ color: THEME.amber, marginTop: 8 }}>
          Tropes: {mechanical.trope.summary}
          {mechanical.trope.total_beats_fired !== null
            ? ` · ${mechanical.trope.total_beats_fired} beats fired`
            : ""}
        </div>
      )}
    </div>
  );
}

interface TabProps {
  mechanical: ForensicMechanical | null;
}

export function MechanicalTab({ mechanical }: TabProps) {
  if (!mechanical) {
    return (
      <div style={{ color: THEME.muted, textAlign: "center", padding: 32 }}>
        Select a saved session and round to see the mechanical census.
      </div>
    );
  }
  return <MechanicalCensus mechanical={mechanical} />;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/MechanicalTab.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/tabs/MechanicalTab.tsx src/components/Dashboard/__tests__/MechanicalTab.test.tsx
git commit -m "feat(inspector): mechanical census tab (per-PC diff + trope)"
```

---

### Task B4: Add Mechanical to the tab bar + capability gating

**Files:**
- Modify: `sidequest-ui/src/components/Dashboard/DashboardTabs.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/DashboardTabs-capability.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/DashboardTabs-capability.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardTabs } from "../DashboardTabs";

describe("DashboardTabs", () => {
  it("includes a Mechanical tab", () => {
    render(<DashboardTabs activeTab={0} onTabChange={() => {}} turnCount={0} errorCount={0} />);
    expect(screen.getByText(/Mechanical/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/DashboardTabs-capability.test.tsx`
Expected: FAIL — no "Mechanical" text (8 tabs only).

- [ ] **Step 3: Add the tab label**

In `DashboardTabs.tsx`, extend `TAB_LABELS` to include Mechanical as the 9th tab:

```tsx
const TAB_LABELS = [
  "① Timeline",
  "② State",
  "③ Subsystems",
  "④ Timing",
  "⑤ Console",
  "⑥ Prompt",
  "⑦ Lore",
  "⑧ Encounters",
  "⑨ Mechanical",
];
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/DashboardTabs-capability.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/DashboardTabs.tsx src/components/Dashboard/__tests__/DashboardTabs-capability.test.tsx
git commit -m "feat(inspector): add Mechanical tab to the bar"
```

---

### Task B5: Wire the shell — source selection + per-source tab rendering

Rebuild `DashboardApp` as the shell. It holds `sourceKind`/picker, calls `useLiveSource()` always (cheap, keeps the WS warm) and `useForensicSource()`, and renders each tab from the active source. Forensic event-array tabs are fed `buildEventArrayView(bundle.telemetry.rows)` (round-scoped).

**Files:**
- Modify: `sidequest-ui/src/components/Dashboard/DashboardApp.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/DashboardApp-source-switch.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/DashboardApp-source-switch.test.tsx
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DashboardApp } from "../DashboardApp";

// useWatcherSocket connects a real WS in jsdom; stub it to a no-op connected source.
vi.mock("@/hooks/useWatcherSocket", () => ({
  useWatcherSocket: () => ({ connected: false }),
}));

const SAVES = [
  { slug: "perseus_cloud", genre: "space_opera", world: "perseus_cloud", created_at: "x", last_played: "y", last_activity_ts: 2, telemetry_rows: 10, mechanical_rows: 4 },
];

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/api/debug/saves")) return Promise.resolve({ ok: true, json: () => Promise.resolve(SAVES) });
      if (url.endsWith("/api/debug/state")) return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      if (url.includes("/timeline")) return Promise.resolve({ ok: true, json: () => Promise.resolve([{ round: 1, seq_start: 1, seq_end: 9, event_kind_counts: {}, narrative_authors: ["gm"], ts: "t" }]) });
      if (url.includes("/turn/")) return Promise.resolve({ ok: true, json: () => Promise.resolve({ round: 1, narrative: [], events: [], derived: {}, projection: [], scrapbook: [], unparseable_seqs: [], telemetry: { rows: [], by_component: {}, total: 0, unparseable_seqs: [] }, mechanical: { state: "absent", pcs: [], trope: null, unparseable_seqs: [] } }) });
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

describe("DashboardApp source switch", () => {
  it("renders the picker and switches to a saved session", async () => {
    render(<DashboardApp />);
    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "save:perseus_cloud" } });
    // Selecting a save loads its timeline; the forensic Timeline tab shows the round.
    await waitFor(() => expect(screen.getByText(/Round 1/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/DashboardApp-source-switch.test.tsx`
Expected: FAIL — no combobox / no source switching yet.

- [ ] **Step 3: Rewrite `DashboardApp` as the shell**

```tsx
// src/components/Dashboard/DashboardApp.tsx
import { useState, useMemo } from "react";
import type { TurnCompleteFields } from "@/types/watcher";
import { DashboardHeader } from "./DashboardHeader";
import { DashboardTabs } from "./DashboardTabs";
import { SessionPicker } from "./SessionPicker";
import { TimelineTab } from "./tabs/TimelineTab";
import { StateTab } from "./tabs/StateTab";
import { SubsystemsTab } from "./tabs/SubsystemsTab";
import { TimingTab } from "./tabs/TimingTab";
import { ConsoleTab } from "./tabs/ConsoleTab";
import { PromptTab } from "./tabs/PromptTab";
import { LoreTab } from "./tabs/LoreTab";
import { EncounterTab } from "./tabs/EncounterTab";
import { ForensicTimelineTab } from "./tabs/ForensicTimelineTab";
import { ForensicStateTab } from "./tabs/ForensicStateTab";
import { MechanicalTab } from "./tabs/MechanicalTab";
import { useLiveSource } from "./source/useLiveSource";
import { useForensicSource } from "./source/useForensicSource";
import { buildEventArrayView } from "./source/telemetryAdapter";
import type { SourceKind, EventArrayView } from "./source/types";
import { THEME } from "./shared/constants";

const EMPTY_VIEW: EventArrayView = {
  turns: [],
  allEvents: [],
  componentMap: {},
  promptEvents: [],
  loreEvents: [],
};

export function DashboardApp() {
  const [activeTab, setActiveTab] = useState(0);
  const [sourceKind, setSourceKind] = useState<SourceKind>("live");

  const live = useLiveSource();
  const forensic = useForensicSource();

  // Forensic event-array tabs are round-scoped: derived from the loaded bundle.
  const forensicView: EventArrayView = useMemo(
    () => (forensic.bundle ? buildEventArrayView(forensic.bundle.telemetry.rows) : EMPTY_VIEW),
    [forensic.bundle],
  );

  const isLive = sourceKind === "live";
  const view: EventArrayView = isLive
    ? {
        turns: live.turns,
        allEvents: live.allEvents,
        componentMap: live.componentMap,
        promptEvents: live.promptEvents,
        loreEvents: live.loreEvents,
      }
    : forensicView;

  const slug = isLive ? live.activeSlug : forensic.selectedSlug;

  const errorCount = view.allEvents.filter((e) => e.severity === "error").length;
  const durations = view.turns
    .map((t) => (t.fields as TurnCompleteFields).agent_duration_ms ?? 0)
    .filter((d) => d > 0)
    .sort((a, b) => a - b);
  const p95 =
    durations.length > 0
      ? (durations[Math.floor(durations.length * 0.95)] / 1000).toFixed(1) + "s"
      : "—";

  return (
    <div
      style={{
        background: THEME.bg,
        color: THEME.text,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        fontSize: 13,
        minHeight: "100vh",
      }}
    >
      <DashboardHeader
        connected={isLive ? live.connected : true}
        turnCount={view.turns.length}
        errorCount={errorCount}
        p95={p95}
        paused={live.paused}
        onTogglePause={live.togglePause}
        onClear={live.clear}
        onRefreshState={live.refreshState}
      />
      <div style={{ padding: "6px 12px", background: THEME.surface, borderBottom: `1px solid ${THEME.border}` }}>
        <SessionPicker
          sourceKind={sourceKind}
          selectedSlug={forensic.selectedSlug}
          liveSlug={live.activeSlug}
          saves={forensic.saves}
          onSelectLive={() => setSourceKind("live")}
          onSelectSave={(s) => {
            setSourceKind("forensic");
            forensic.selectSave(s);
          }}
        />
      </div>
      <DashboardTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        turnCount={view.turns.length}
        errorCount={errorCount}
      />
      <div style={{ height: "calc(100vh - 116px)", overflowY: "auto" }}>
        {activeTab === 0 &&
          (isLive ? (
            <TimelineTab
              turns={live.turns}
              selectedTurn={live.selectedTurn}
              onSelectTurn={live.selectTurn}
            />
          ) : (
            <ForensicTimelineTab
              rounds={forensic.rounds}
              selectedRound={forensic.selectedRound}
              onSelectRound={forensic.selectRound}
            />
          ))}
        {activeTab === 1 &&
          (isLive ? (
            <StateTab debugState={live.debugState} onRefresh={live.refreshState} />
          ) : (
            <ForensicStateTab bundle={forensic.bundle} snapshot={forensic.snapshot} />
          ))}
        {activeTab === 2 && (
          <SubsystemsTab
            allEvents={view.allEvents}
            componentMap={view.componentMap}
            turnCount={view.turns.length}
          />
        )}
        {activeTab === 3 && <TimingTab turns={view.turns} />}
        {activeTab === 4 && <ConsoleTab allEvents={view.allEvents} />}
        {activeTab === 5 && <PromptTab promptEvents={view.promptEvents} />}
        {activeTab === 6 && <LoreTab loreEvents={view.loreEvents} />}
        {activeTab === 7 && <EncounterTab slug={slug} />}
        {activeTab === 8 && (
          <MechanicalTab mechanical={isLive ? null : forensic.bundle?.mechanical ?? null} />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the new test + full dashboard suite**

Run: `npx vitest run src/components/Dashboard src/__tests__/EncounterTab.test.tsx src/__tests__/app-dashboard-toggle-rehandshake-67-9.test.tsx`
Expected: PASS (new source-switch test green; all prior dashboard tests still green).

- [ ] **Step 5: Typecheck + lint**

Run: `npx tsc --noEmit && npm run lint`
Expected: clean. Fix any type drift (e.g. `MechanicalTab` prop nullability).

- [ ] **Step 6: Commit**

```bash
git add src/components/Dashboard/DashboardApp.tsx src/components/Dashboard/__tests__/DashboardApp-source-switch.test.tsx
git commit -m "feat(inspector): unify shell — source picker + per-source tab rendering"
```

---

### Task B6: Manual verification (live + forensic)

**Working dir:** orchestrator root.

- [ ] **Step 1: Start the stack**

Run: `just server` (terminal 1), `just daemon` (terminal 2), `just client` (terminal 3). Ensure a save exists in Postgres (`just pg-up`; play a short session or import one).

- [ ] **Step 2: Verify live**

Open `http://localhost:5173/#/dashboard`. Confirm the picker shows "● Live: …", the live tabs behave exactly as before, and the WS connects (header dot).

- [ ] **Step 3: Verify forensic**

Pick a saved session. Confirm: Timeline lists rounds; clicking a round updates State (derived amber + stored green), Mechanical (census diff), Console/Subsystems/Prompt/Lore (round-scoped telemetry), Encounters (full timeline). Confirm no writes hit the DB (read-only): `psql` row counts unchanged before/after scrubbing.

- [ ] **Step 4: No commit** (verification only). Record findings in the session notes.

---

# Part C — Teardown + stale fixes

> Run Part C only after Part B is merged/verified — the React forensics must exist before deleting the server HTML.

### Task C1: Delete server-rendered dashboard + forensics pages

**Files (delete):**
- `sidequest-server/sidequest/server/static/dashboard.html`
- `sidequest-server/sidequest/server/dashboard.py`
- `sidequest-server/sidequest/server/static/forensics.html`
- `sidequest-server/sidequest/server/forensics.py`
- Modify: `sidequest-server/sidequest/server/app.py` (remove both router imports + `include_router` calls, ~lines 322-326)

**Working dir:** `sidequest-server`

- [ ] **Step 1: Write the failing test (routes are gone)**

```python
# tests/server/test_legacy_html_routes_removed.py
from fastapi.testclient import TestClient
from sidequest.server.app import create_app


def test_legacy_dashboard_and_forensics_html_routes_removed():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/dashboard" not in paths
    assert "/forensics" not in paths
```

(If `create_app` has a different name/signature, match the existing `tests/server/test_forensics_routes.py` app-construction idiom.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_legacy_html_routes_removed.py -v`
Expected: FAIL — `/dashboard` and `/forensics` still registered.

- [ ] **Step 3: Delete the files and route registrations**

```bash
git rm sidequest/server/static/dashboard.html sidequest/server/dashboard.py
git rm sidequest/server/static/forensics.html sidequest/server/forensics.py
```

In `sidequest/server/app.py`, remove:
```python
from sidequest.server.dashboard import dashboard_router
app.include_router(dashboard_router)
from sidequest.server.forensics import forensics_router
app.include_router(forensics_router)
```
Leave every `/api/debug/*` and `/api/sessions/*` route untouched — those are the data API.

- [ ] **Step 4: Run test + the forensic REST suite**

Run: `uv run pytest tests/server/test_legacy_html_routes_removed.py tests/server/test_forensics_routes.py -v -n0`
Expected: PASS — HTML routes gone, REST data routes intact.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(inspector): delete server-rendered dashboard + forensics HTML (React is canonical)"
```

---

### Task C2: Remove dead Rust-port span constants

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/audio.py` (remove `SPAN_MUSIC_EVALUATE`, `SPAN_MUSIC_CLASSIFY_MOOD`)
- Modify: `sidequest-server/sidequest/telemetry/spans/inventory.py` (remove `SPAN_INVENTORY_EXTRACTION`)
- Modify: `sidequest-server/sidequest/telemetry/spans/_core.py` (remove the three from `FLAT_ONLY_SPANS`)

**Working dir:** `sidequest-server`

- [ ] **Step 1: Confirm no production emitters reference them**

Run:
```bash
grep -rn "SPAN_MUSIC_EVALUATE\|SPAN_MUSIC_CLASSIFY_MOOD\|SPAN_INVENTORY_EXTRACTION" sidequest/ tests/
```
Expected: only the definition sites + `FLAT_ONLY_SPANS` membership (no call sites). If a call site exists, STOP — it is not dead; leave it.

- [ ] **Step 2: Delete the constants and their `FLAT_ONLY_SPANS` entries**

Remove the three constant definitions and their references in `_core.py`'s `FLAT_ONLY_SPANS` set.

- [ ] **Step 3: Run the telemetry suite**

Run: `uv run pytest tests/telemetry -v -n0`
Expected: PASS. If a span-count test asserts the size of `FLAT_ONLY_SPANS`, update its expected count by −3 (this is the legitimate place — a count assertion, not a source-text wiring test).

- [ ] **Step 4: Lint**

Run: `uv run ruff check sidequest/telemetry`
Expected: clean (no unused-import fallout).

- [ ] **Step 5: Commit**

```bash
git add sidequest/telemetry/spans/audio.py sidequest/telemetry/spans/inventory.py sidequest/telemetry/spans/_core.py tests/telemetry
git commit -m "chore(telemetry): drop dead Rust-port span constants (music_evaluate/classify_mood, inventory_extraction)"
```

---

### Task C3: Fix the "Rust memory" tooltip + Inspector title

**Files:**
- Modify: `sidequest-ui/src/components/Dashboard/DashboardHeader.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/DashboardHeader-tooltip.test.tsx`

**Working dir:** `sidequest-ui`

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/Dashboard/__tests__/DashboardHeader-tooltip.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardHeader } from "../DashboardHeader";

describe("DashboardHeader", () => {
  it("uses a non-stale refresh tooltip (no 'Rust')", () => {
    render(
      <DashboardHeader
        connected
        turnCount={0}
        errorCount={0}
        p95="—"
        paused={false}
        onTogglePause={() => {}}
        onClear={() => {}}
        onRefreshState={() => {}}
      />,
    );
    const btn = screen.getByTitle(/Refresh game state from server/i);
    expect(btn).toBeInTheDocument();
    expect(screen.queryByTitle(/Rust/i)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/Dashboard/__tests__/DashboardHeader-tooltip.test.tsx`
Expected: FAIL — current title is "Refresh game state from Rust memory".

- [ ] **Step 3: Fix the tooltip**

In `DashboardHeader.tsx`, change `title="Refresh game state from Rust memory"` to `title="Refresh game state from server"`. (Optional: update the header label text to "Inspector" if a title element exists.)

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/Dashboard/__tests__/DashboardHeader-tooltip.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/Dashboard/DashboardHeader.tsx src/components/Dashboard/__tests__/DashboardHeader-tooltip.test.tsx
git commit -m "chore(inspector): drop stale 'Rust memory' tooltip"
```

---

### Task C4: Repoint `just otel`

**Files:**
- Modify: `orc-quest/justfile` (the `otel` recipe)

**Working dir:** orchestrator root (`.`)

- [ ] **Step 1: Read the current recipe**

Run: `grep -n -A4 '^otel' justfile`
Expected: a recipe opening the server `/dashboard` page (`http://localhost:8765/dashboard`).

- [ ] **Step 2: Repoint to the React Inspector**

Change the opened URL to the React app's hash route: `http://localhost:5173/#/dashboard` (dev). Add a comment noting that in a built/prod deploy the Inspector is served wherever the UI bundle is hosted, at `#/dashboard`.

- [ ] **Step 3: Verify**

Run: `just otel` (with `just client` running)
Expected: opens the React Inspector at `#/dashboard`.

- [ ] **Step 4: Commit**

```bash
git add justfile
git commit -m "chore(inspector): repoint 'just otel' to the React Inspector (#/dashboard)"
```

---

## Self-Review

**Spec coverage:**
- Single React stack / delete server HTML → Tasks C1 (delete), B-series (React forensics). ✓
- `SessionSource` abstraction → A1 (types/capabilities), A5 (`useLiveSource`), A3 (`useForensicSource`), B5 (shell). ✓
- Session picker over `/api/debug/saves` with row counts + empty-census flag → A4. ✓
- Unified lens set, shared event-array tabs source-agnostic via adapter → A2 + B5. ✓
- Forensic Timeline / State drilldown / Mechanical (the no-React-twin forensics content) → B1, B2, B3. ✓
- Prompt/Lore forensic-capable (persist, not ephemeral) → fed via adapter in B5 (round-scoped). ✓
- Truth-tier badging → B2 (derived amber / stored green). ✓
- Encounters identical both sources → B5 (passes `slug`). ✓
- Delete 2 dead span constants → C2. ✓
- "Rust memory" tooltip → C3. ✓
- Access-path change / repoint `just otel` → C4. ✓
- Two pipes stay separate (no plumbing merge) → live and forensic remain distinct hooks; no shared data contract beyond the UX. ✓
- Non-goals respected: no lie-detector headline, no span-firehose prune, no ADR-103 work, no backend persistence change (forensic tabs round-scoped to avoid a new aggregate endpoint). ✓

**Known deviations from the "ideal" merge (documented, intentional):**
- Forensic event-array tabs are **round-scoped**, live tabs are **whole-session**. Justified: lazy fetch, no new backend endpoint (Phase-1 scope discipline). A future phase can add a save-aggregate endpoint if whole-save forensic Console is wanted.
- `MechanicalTab` for the **live** source renders a "select a saved session" placeholder rather than live census rows. Justified: the per-PC *diff* is forensic-native (needs a previous round to diff against); live census is already visible in Subsystems via `component='mechanical'`. Promote to live-diff in a later phase if wanted.

**Placeholder scan:** none — all steps carry real code/commands. (The B1 inline `r.selectedMatch(...)` is explicitly corrected to `r.round === selectedRound` in the same step.)

**Type consistency:** `EventArrayView`, `ForensicBundle`, `ForensicMechanical`, `TelemetryRow`, `ForensicSaveEntry`, `ForensicTimelineRound` defined in A1 and used consistently in A2/A3/B1/B2/B3/B5. Hook return types (`LiveSourceState`, `ForensicSourceState`) match their consumers in B5. `SessionPicker` value protocol (`live` / `save:<slug>`) consistent between A4 and B5.

---

## Out of scope — Phase 2 (separate spec/plan)

Per the spec's non-goals, the following are deliberately **not** in this plan and should be brainstormed separately once the unified Inspector is standing:
- Lie-detector verdict as the headline (ADR-031 Layer 3 surfaced front-and-center).
- Pruning the 280+ routed / 51 flat-only span set down to "what you actually read."
- Whole-save forensic aggregation (server aggregate endpoint) for non-round-scoped Console/Timing.
- Live mechanical-diff (per-round census diff in the live source).
