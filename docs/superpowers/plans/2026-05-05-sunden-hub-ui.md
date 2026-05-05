# Sünden Hub UI — Item 4b (Client-Side)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the React/TypeScript hub UI that consumes item 4a's protocol surfaces. A new `hub` session phase routes hub-world connects to a `HubScreen` showing the Wall ledger, the recruitable roster, and a three-sin dungeon picker with party selection. Buttons fire `POST /api/games/{slug}/hub/recruit`, `DELETE /api/games/{slug}/hub/roster/{id}`, and the `DUNGEON_SELECT` WS frame; the existing GameBoard gains an in-delve "Retreat" affordance that sends `RETREAT_TO_HAMLET` and routes the user back to the hub on the resulting `HUB_VIEW`.

**Architecture:** New `SessionPhase` value (`"hub"`) joins the existing `connect → creation → game` machine. Phase transitions are message-driven: a server `HUB_VIEW` frame moves the user *into* `hub` (from `connect` after WS open, or from `game` after a successful retreat); a server `NARRATION` frame after a `DUNGEON_SELECT` moves the user from `hub` to `game` — but **only when a `pendingDungeonSelect` flag is set**, set on the client at DUNGEON_SELECT send-time and cleared on first NARRATION receipt. The flag closes the in-flight-NARRATION race (a stale narration frame from a prior delve cannot bounce the user out of `hub` into `game` against their will). The hub state itself is mirrored from the most recent `HUB_VIEW.payload` (no client-side mutation — server is source of truth; mutations refetch). The `available_dungeons` payload arrives **enriched** as `[{slug, sin, wounded}, ...]` from item 4a — the client deliberately has **no** local `SIN_BY_DUNGEON` map (the spec language for sin is server-side, not duplicated). New components are pure presentational with prop-drilled state from `App.tsx`; no new context provider, because the hub is short-lived screen-scoped state and the existing `GameStateProvider` is delve-scoped. Retreat is a button that surfaces only when `sessionPhase === "game"` AND `snapshot.active_delve_dungeon !== null`; the button opens a confirm dialog with **two** outcome buttons (`retreat`, `victory`) and a separate **"Wounded the boss"** checkbox (orthogonal — a TPK-after-wound is recordable; spec §"Wounded Sins" line 81). Defeat is server-driven (player_dead) and never user-selectable.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, React Testing Library, Tailwind, base-ui (existing dependencies — no new ones).

**Date:** 2026-05-05
**Status:** Draft
**Repo:** sidequest-ui (everything; no backend changes — depends on item 4a's PR being merged)
**Spec parent:** `docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md` §"Engine Surface" item 4 (the UI half — engine is item 4a)
**Sibling plans:**
- `docs/superpowers/plans/2026-05-05-delve-lifecycle-engine.md` — item 4a, **prerequisite**. This plan cannot ship until the protocol surfaces it consumes (`HUB_VIEW`, `DUNGEON_SELECT`, `RETREAT_TO_HAMLET`, `/api/games/{slug}/hub/*`) exist on a deployed server. Order on the merge train: 4a → 4b.
- `docs/superpowers/plans/2026-05-05-world-save-persistence-hub.md` — item 2, **transitive prerequisite** via 4a.
- `docs/superpowers/plans/2026-05-05-stress-field-hireling.md` — item 3, *to be authored*. Once stress accrues numerically, the RosterPanel grows a stress bar; this plan ships a stress *display* (read-only) so item 3 has nothing to wire.
- `docs/superpowers/plans/2026-05-05-narrator-zones-drift-wound-wall.md` — items 5/6/7. The Wall view in this plan is *display-only*; once the narrator consumes the Wall (item 7), no UI change is needed — the same data flows.

---

## Why

Item 4a made the engine playable through curl + websocat. To get Keith — and especially Alex (slower reader, freezes under time pressure) and James (narrative-first) — into a real Sünden session, there has to be a UI that shows them where they are, who's on the roster, what the Wall says, and how to start a delve. Without this plan, the hub can be tested but not played.

The Hamlet view also matters as a *narrative beat* between delves. The spec frames Sünden as the place where drift surfaces, where the Wall is read, where stress relief is paid for. Showing those things on a screen with weight and stillness — not just an inventory list — is what makes the loop feel like Darkest Dungeon's hub, not just a JSON dump. Visual polish of that "weight and stillness" is calibrated against playgroup feedback after the first playtest; this plan ships a *functional, legible* hub and explicitly defers the heavy art-direction polish to a follow-on. Sebastien (mechanics-first; OTEL-as-feature per CLAUDE.md) gets the GM-panel transparency: the OTEL spans from item 4a (`session.delve_started` / `session.delve_ended` etc.) already publish, and this plan does not change that — it just gives Sebastien a UI to drive the spans from.

## Scope

This plan ends when:
- A connect into a hub world (e.g. `caverns_and_claudes/caverns_three_sins`) routes to a new `HubScreen` instead of `CharacterCreation`. The screen renders the WorldSave's roster, the Wall ledger, a three-sin dungeon picker, and the genre/world identity at the top.
- The Recruit button calls `POST /api/games/{slug}/hub/recruit`, refetches the hub state on success, and shows the new hireling in the roster.
- The Dismiss button calls `DELETE /api/games/{slug}/hub/roster/{id}?reason=dismiss`, refetches.
- The dungeon picker shows N sin-cards (Pride / Greed / Gluttony for caverns_three_sins; data-driven for future packs) with the wound flag indicated when set; sin and wound state come from `AvailableDungeon` in the HUB_VIEW payload — no client-side mapping. Clicking a card opens a party-select panel; party-select gates the "Start Delve" button until 1..6 active hirelings are checked. Start Delve sends `DUNGEON_SELECT`, sets `pendingDungeonSelectRef.current=true`, and the phase transitions to `"game"` on the first NARRATION received while the flag is true.
- A new "Retreat" button in `GameBoard` opens a confirmation dialog with two outcome buttons (`retreat` | `victory`) and a separate "Wounded the boss" checkbox; the chosen `(outcome, wounded_boss)` pair is sent in the `RETREAT_TO_HAMLET` payload. The phase transitions back to `"hub"` on the resulting `HUB_VIEW`.
- The Retreat button is *only* visible when in delve mode (snapshot has `active_delve_dungeon !== null`); it is hidden in any non-hub world (where the snapshot field is always null) and during hub mode.
- A `player_dead` defeat (server-driven) routes back to `"hub"` automatically when `HUB_VIEW` arrives — the same code path; nothing client-specific for defeat.
- `npm test` is green; `npm run build` is green; `npm run lint` is clean.

**Explicitly NOT a goal:**
- Visual polish for the Sünden assets (background image of the Square, Wall imagery, NPC portraits in the hub). Spec describes these (§"Sünden — the Hamlet"), but the asset pipeline + portrait_manifest entries belong to a content/media plan, not this UI plan. UI ships with placeholders — flat panels, simple tags — and is wired so a follow-on can swap in art without touching component logic.
- Stress-relief services UI (Confessional / Workhouse / Masquerade panels). Item 4-followon (depends on item 3 stress mechanics + item 4-followon services REST).
- Drift-flag visual indicators ("the innkeeper's voice doesn't carry"). Drift is read by the narrator, not the UI; the UI shows `latest_delve_sin` as a simple badge ("Last delve: Pride") for legibility but doesn't dramatize it.
- Wound-flag dramatization beyond a small "Wounded" badge on the dungeon card. Spec says wounded dungeons get tone-overridden Keepers (item 6); the UI just needs to indicate "this dungeon has been wounded."
- A separate Sünden-only audio cue. The existing audio engine reads `audio.yaml` at world level; this plan doesn't touch audio routing. (If world-level audio plays automatically on hub-mode connect today, great; if not, that's a follow-on for the audio plan.)
- Recruit cost / currency UI. Item 4-followon.
- A way to *resume* the previous party in a fresh delve in one click. The party is selected per-delve in this plan; quick-resume is a follow-on convenience.
- Multiplayer-shared hub (two clients editing the roster simultaneously). The server allows it (item 4a §"Out of scope"); the UI in this plan does not optimistically update — every mutation refetches — so concurrent edits "just work" with last-write-wins. No optimistic-UI race fixes in this plan.
- An end-of-delve scrapbook / recap card. The existing scrapbook system surfaces during the delve; nothing post-delve is added.

**Out of scope (separate, deliberately):**
- New genre-theme assets for `caverns_and_claudes`. The hub uses the existing theme.
- Persistence of UI-side hub navigation (e.g. "remember which dungeon was hovered last"). The hub is stateless across sessions.

## Design

### 1. Phase machine extension

Today (`App.tsx:51`):

```ts
type SessionPhase = "connect" | "creation" | "game";
```

After this plan:

```ts
type SessionPhase = "connect" | "hub" | "creation" | "game";
```

Transitions:
- `connect → hub`: WS opens, server sends `HUB_VIEW` (hub-world fresh connect or hub-world resume with no active delve).
- `connect → creation`: WS opens, server sends `CHARACTER_CREATION` (today's leaf-world fresh path).
- `connect → game`: WS opens, server sends `NARRATION` (today's leaf-world resume path; also a hub-world resume *mid-delve* — same path because `active_delve_dungeon` is set server-side and item 4a's connect handler resumes normally).
- `hub → game`: client sent `DUNGEON_SELECT`, set `pendingDungeonSelect = true`; server's first `NARRATION` after that arrives. Set `setSessionPhase("game")` and clear `pendingDungeonSelect` on the *first* NARRATION received **while phase is `"hub"` AND `pendingDungeonSelect` is true**. A NARRATION arriving in `hub` mode without `pendingDungeonSelect` is a stale frame from a previous delve and is ignored (logged as a console breadcrumb). The flag is the only thing standing between the user and a stale-narration bounce.
- `game → hub`: server sends `HUB_VIEW` (delve ended via `RETREAT_TO_HAMLET` or `player_dead`-auto-defeat). Set `setSessionPhase("hub")` on `HUB_VIEW` regardless of current phase. Reset all delve-scoped state (party, narration scroll, dice, etc.) — same reset path used today on disconnect/leave, factored into a `resetDelveState()` helper. **Concrete enumeration of state to reset is pinned in §6 below — derived from `App.tsx` `handleLeave` line 1229–1267 (current at plan time)** so the implementer doesn't have to rediscover the list.
- `hub → creation`: never. Hub players never see chargen — their characters are recruited Hirelings, not freshly-built PCs. (If chargen is somehow needed later, that's a different design.)

### 2. New protocol additions (TypeScript mirror)

In `src/types/protocol.ts` `MessageType` const-object, add:

```ts
HUB_VIEW: "HUB_VIEW",
DUNGEON_SELECT: "DUNGEON_SELECT",
RETREAT_TO_HAMLET: "RETREAT_TO_HAMLET",
```

In `src/types/payloads.ts` (or a new file `src/types/hub.ts` if payloads.ts is bursting — verify in task 2), add the typed payloads:

```ts
// "defeat" is server-only, never sent by the client. The inbound DelveOutcome
// type excludes it so a `RETREAT_TO_HAMLET.outcome="defeat"` from the UI is
// a compile error. Wound status lives on the orthogonal `wounded_boss` field.
export type DelveOutcome = "retreat" | "victory";

// The full set of outcomes that can appear in a Wall entry — includes
// "defeat" because the server's player_dead auto-trigger writes it.
export type WallOutcome = "retreat" | "victory" | "defeat";

export interface Hireling {
  id: string;
  name: string;
  archetype: string;
  stress: number;
  status: "active" | "dead" | "missing";
  recruited_at_delve: number;
  notes: string;
}

export interface WallEntry {
  delve_number: number;
  sin: string;        // ("pride" | "greed" | "gluttony" | future)
  dungeon: string;    // dungeon slug
  party_hireling_ids: string[];
  outcome: WallOutcome;
  wounded_boss: boolean;  // orthogonal to outcome (spec §"Wounded Sins")
  timestamp: string;  // ISO-8601
}

export interface WorldSaveView {
  roster: Hireling[];
  currency: number;
  wall: WallEntry[];
  dungeon_wounds: Record<string, boolean>;
  latest_delve_sin: string | null;
  delve_count: number;
  last_saved_at: string | null;
}

// Enriched dungeon descriptor — server resolves sin + wounded so the
// client never needs a hardcoded SIN_BY_DUNGEON map. Mirror of item 4a
// AvailableDungeon pydantic model.
export interface AvailableDungeon {
  slug: string;
  sin: string;
  wounded: boolean;
}

export interface HubViewPayload {
  slug: string;
  genre_slug: string;
  world_slug: string;
  available_dungeons: AvailableDungeon[];
  world_save: WorldSaveView;
}

export interface DungeonSelectPayload {
  dungeon: string;
  party_hireling_ids: string[];
}

export interface RetreatToHamletPayload {
  outcome: DelveOutcome;
  wounded_boss: boolean;  // orthogonal — sent independently of outcome
}
```

### 3. Hub state in `App.tsx`

A single `useState<HubViewPayload | null>(null)` holds the most recent hub view. It is set from any received `HUB_VIEW` and consumed by `HubScreen`. Refetch helper:

```ts
const fetchHubState = useCallback(async (slug: string) => {
  const res = await fetch(`/api/games/${slug}/hub`);
  if (!res.ok) {
    setTransientError(`Failed to load hub state: ${res.status}`);
    return;
  }
  const body = await res.json();
  setHubView(body as HubViewPayload);
}, []);
```

Used by Recruit and Dismiss after their REST calls succeed. Not used after `HUB_VIEW` WS frames — those carry the full state and update `hubView` directly.

### 4. New components

```
src/screens/HubScreen.tsx                — top-level screen, prop-drilled
src/components/Hub/RosterPanel.tsx       — hireling list + recruit + dismiss
src/components/Hub/HirelingCard.tsx      — one row in the roster
src/components/Hub/WallView.tsx          — read-only ledger of recent delves
src/components/Hub/DungeonPicker.tsx     — N sin-cards from server-enriched payload
src/components/Hub/SinCard.tsx           — one sin card with wound badge (data-driven)
src/components/Hub/PartySelectDialog.tsx — base-ui dialog with checkboxes
src/components/Hub/RetreatDialog.tsx     — outcome buttons + wounded-boss checkbox
src/components/Hub/__tests__/*.test.tsx  — RTL component tests
```

**No `sinMap.ts` / `SIN_BY_DUNGEON`** — sin labels arrive on `AvailableDungeon.sin` from item 4a's enriched HUB_VIEW payload. See "Sin labels — server-resolved" subsection below.

#### Component contracts (props)

```ts
// HubScreen — the page the user sees while sessionPhase === "hub"
interface HubScreenProps {
  hubView: HubViewPayload;
  onRecruit: () => Promise<void>;
  onDismiss: (hirelingId: string) => Promise<void>;
  onStartDelve: (dungeon: string, partyHirelingIds: string[]) => void;
  onLeave: () => void;  // back to lobby; reuses existing leave flow
}

// RosterPanel — the left side of HubScreen
interface RosterPanelProps {
  roster: Hireling[];
  delveCount: number;
  onRecruit: () => Promise<void>;
  onDismiss: (id: string) => Promise<void>;
  recruitDisabled?: boolean;  // true while a recruit POST is in-flight
}

// HirelingCard — one row
interface HirelingCardProps {
  hireling: Hireling;
  onDismiss: (id: string) => Promise<void>;
  selectable?: boolean;       // when used inside PartySelectDialog
  selected?: boolean;
  onToggleSelect?: () => void;
}

// WallView — the right side of HubScreen
interface WallViewProps {
  wall: WallEntry[];
  rosterById: Record<string, Hireling>;  // for resolving party_hireling_ids → names
  latestDelveSin: string | null;
}

// DungeonPicker — the bottom of HubScreen
interface DungeonPickerProps {
  // Enriched descriptors from the server (slug + sin + wounded).
  // Server is source of truth for sin; client never hardcodes the
  // sin→dungeon mapping.
  availableDungeons: AvailableDungeon[];
  roster: Hireling[];
  onStartDelve: (dungeon: string, partyHirelingIds: string[]) => void;
}

// SinCard — one of N (caverns_three_sins ships 3; future hub packs may differ)
interface SinCardProps {
  dungeon: AvailableDungeon;  // {slug, sin, wounded} from server
  onClick: () => void;
}

// PartySelectDialog — opens when a SinCard is clicked
interface PartySelectDialogProps {
  open: boolean;
  dungeon: string;
  sin: string;
  roster: Hireling[];
  onConfirm: (partyHirelingIds: string[]) => void;
  onCancel: () => void;
}

// RetreatDialog — opens when the in-game Retreat button is clicked
interface RetreatDialogProps {
  open: boolean;
  dungeon: string;
  onConfirm: (outcome: DelveOutcome, woundedBoss: boolean) => void;
  onCancel: () => void;
}
```

#### Sin labels — server-resolved, no client-side map

This plan deliberately ships **no** `SIN_BY_DUNGEON` map. The sin for each
dungeon arrives on `AvailableDungeon.sin` from item 4a's `HUB_VIEW`
payload, which the server resolves from `Dungeon.config.sin` (loader item
1's per-dungeon config). The `latest_delve_sin` field on `WorldSaveView`
likewise comes from the server. Future hub-world genre packs (heavy_metal,
mutant_wasteland, etc.) get sin-labeled UI for free with zero TS changes.

This was a load-bearing review-time decision: the prior draft had a
`src/components/Hub/sinMap.ts` with the three caverns dungeons hardcoded.
Eliminating it removes a duplicated source of truth and the maintenance
risk that comes with it.

### 5. Retreat affordance in `GameBoard`

A new `<RetreatButton>` placed in the GameBoard top bar (next to whatever existing controls live there — verify exact location in task 11). Visibility:

```ts
const showRetreat = sessionPhase === "game" && snapshot?.active_delve_dungeon != null;
```

Click opens `<RetreatDialog>` with two outcome buttons (Retreat / Victory) and a "Wounded the boss" checkbox. On confirm, sends:

```ts
sendMessage({
  type: MessageType.RETREAT_TO_HAMLET,
  payload: { outcome: chosenOutcome, wounded_boss: woundedBoss },
  player_id: playerId,
});
```

Fire-and-forget — the server responds with `HUB_VIEW`, which the existing message handler routes to the phase machine. No optimistic UI update.

The wound-checkbox is independent of outcome so a TPK-after-wound (player retreats with wounded_boss=True after one party member died offscreen) is recordable. Defeat is server-driven (player_dead) and never user-selectable; the auto-defeat path always sends wounded_boss=False (narrator-side wound detection is item-4-followon — a known gap).

### 6. Layered state-reset on `game → hub`

When `HUB_VIEW` arrives while `sessionPhase === "game"`:

1. `setSessionPhase("hub")`
2. `setHubView(payload)`
3. Call `resetDelveState()` — the factored helper.

The `resetDelveState()` helper is extracted from the existing `handleLeave`
block at `App.tsx:1229–1267` (current at plan time). The implementer must
verify this enumeration via `git grep` against the *current* `handleLeave`
at execution time — the plan was authored on 2026-05-05 and the file
evolves — but every setter listed here was present at plan-time. Missing
one of these on the `game → hub` path means leftover delve state visible
in the next hub render (e.g. dice still showing the last delve's roll,
the prior party still in `partyMembers`, narration still in `messages`).

**Concrete checklist — every setter to call from `resetDelveState()`:**

```ts
function resetDelveState() {
  // Narration & input
  setMessages([]);
  setCanType(true);
  setThinking(false);

  // Character & creation
  setCharacter(null);
  setCreationScene(null);

  // Side panels
  setCharacterSheet(null);
  setInventoryData(null);
  setMapData(null);

  // Confrontation
  setConfrontationData(null);
  setConfrontationOutcome(null);

  // Dice overlay
  setDiceRequest(null);
  setDiceResult(null);

  // Party & turn-state
  setPartyMembers([]);
  setActivePlayerName(null);
  setTurnStatusEntries([]);
  setCurrentRound(0);
  setPartyResources({});

  // Pause/turn-coordination
  setPaused(false);
  setPauseWaitingFor([]);

  // Dedup ledger for telemetry events
  seenEventKeysRef.current.clear();
}
```

**Setters from `handleLeave` that resetDelveState() does NOT call** (and why):

| Setter | Why it's omitted from resetDelveState |
|--------|---------------------------------------|
| `disconnect()` / `clearSession()` | We want the WS to stay open for the next delve. |
| `setConnected(false)` | WS stays open; connection state stays true. |
| `setSessionPhase("connect")` | We're going to `"hub"`, not `"connect"`. The caller sets phase. |
| `sessionPhaseRef.current = "connect"` | Same — caller sets to `"hub"`. |
| `autoReconnectAttempted.current = false` | Auto-reconnect already happened; don't reset. |
| `slugConnectFired.current = false` | We're staying on the same slug. |
| `justConnectedRef.current = false` | Connection-event ledger is already advanced past first connect. |
| `pendingConnectPayloadRef.current = null` | Connect handshake is done; this is in steady state. |
| `setGameMetaError(null)` / `setCurrentGenre/World(null)` | We're staying in the same game; identity persists. |
| `setSeatedPlayers({})` / `setConnectedPlayerName("")` | MP seating persists across delves (same campaign). |
| `setOffline(false)` | Offline state is connection-scoped, not delve-scoped. |
| `navigate("/")` | We're staying on the slug route. |

Call `resetDelveState()` from both:
- `handleLeave` (replaces the inline block — no behavior change).
- The `game → hub` transition in the message handler (new caller).

The Risks section flags this as the most fragile factoring; the §6 checklist
is the mitigation — the implementer reads it instead of rediscovering the
list against a moving target. Task 3 step 4 enforces a verification grep.

### 7. Wiring tests (per CLAUDE.md "every test suite needs a wiring test")

Component-level RTL tests prove each component renders and dispatches its callbacks correctly. The wiring test goes one level higher — `App.test.tsx` (existing file) gets a new test:

```ts
test("hub-mode connect routes to HubScreen", async () => {
  // Spin up a stub WS that emits HUB_VIEW on open.
  // Render <App />.
  // Wait for HubScreen to mount.
  // Assert at least one Hireling row from the stub renders.
});
```

This test proves the phase machine transitions correctly and that the screen actually mounts — the failure mode this guards against is "components compile, are unit-tested, but the App.tsx switch statement never hits the new case".

## Tasks

### Task 1: `MessageType` additions + payload types

**Files:**
- Modify: `sidequest-ui/src/types/protocol.ts`
- Create: `sidequest-ui/src/types/hub.ts`
- Test: `sidequest-ui/src/types/__tests__/hub.test.ts` (new — type-level test, just compile-time assertions)

- [ ] **Step 1: Write the failing test**

```ts
// hub.test.ts
import { describe, expect, test } from "vitest";
import { MessageType } from "@/types/protocol";
import type {
  DelveOutcome,
  HubViewPayload,
  WorldSaveView,
} from "@/types/hub";

describe("hub protocol types", () => {
  test("MessageType has hub additions", () => {
    expect(MessageType.HUB_VIEW).toBe("HUB_VIEW");
    expect(MessageType.DUNGEON_SELECT).toBe("DUNGEON_SELECT");
    expect(MessageType.RETREAT_TO_HAMLET).toBe("RETREAT_TO_HAMLET");
  });

  test("DelveOutcome is the inbound 2-literal (defeat is server-only)", () => {
    // The inbound DelveOutcome only allows what a CLIENT can send.
    // Defeat is server-only (player_dead auto-trigger), so it must be
    // a TS error to put it in a RetreatToHamletPayload.
    const ok: DelveOutcome[] = ["retreat", "victory"];
    expect(ok).toHaveLength(2);
    // @ts-expect-error — defeat is server-only
    const _no: DelveOutcome = "defeat";
    void _no;
    // @ts-expect-error — wounded_dungeon was removed during plan review
    const _no2: DelveOutcome = "wounded_dungeon";
    void _no2;
  });

  test("WallEntry outcome includes defeat (write-only on server)", () => {
    // The full Wall outcome union DOES include defeat — the server
    // writes it on player_dead auto-trigger, and the client must be
    // able to render it in WallView.
    const e: WallEntry = {
      delve_number: 1, sin: "pride", dungeon: "grimvault",
      party_hireling_ids: [], outcome: "defeat", wounded_boss: false,
      timestamp: "2026-05-05T00:00:00Z",
    };
    expect(e.outcome).toBe("defeat");
  });

  test("RetreatToHamletPayload requires both outcome and wounded_boss", () => {
    const p: RetreatToHamletPayload = {
      outcome: "victory",
      wounded_boss: true,  // orthogonal to outcome
    };
    expect(p.wounded_boss).toBe(true);
  });

  test("WorldSaveView has all required fields", () => {
    const ws: WorldSaveView = {
      roster: [],
      currency: 0,
      wall: [],
      dungeon_wounds: {},
      latest_delve_sin: null,
      delve_count: 0,
      last_saved_at: null,
    };
    expect(ws.roster).toEqual([]);
  });

  test("HubViewPayload composes AvailableDungeon[] + WorldSaveView", () => {
    const p: HubViewPayload = {
      slug: "x", genre_slug: "y", world_slug: "z",
      available_dungeons: [
        { slug: "grimvault", sin: "pride", wounded: false },
      ],
      world_save: {
        roster: [], currency: 0, wall: [], dungeon_wounds: {},
        latest_delve_sin: null, delve_count: 0, last_saved_at: null,
      },
    };
    expect(p.available_dungeons[0].sin).toBe("pride");
  });
});
```

- [ ] **Step 2: Run; expect failure (the imports don't exist)**

```bash
cd sidequest-ui && npx vitest run src/types/__tests__/hub.test.ts
```

- [ ] **Step 3: Add the three `MessageType` values to `src/types/protocol.ts`**

Append after `ORBITAL_CHART` exactly per §2.

- [ ] **Step 4: Create `src/types/hub.ts`**

Per §2 — `DelveOutcome`, `Hireling`, `WallEntry`, `WorldSaveView`, `HubViewPayload`, `DungeonSelectPayload`, `RetreatToHamletPayload`. Match the server-side pydantic field names exactly.

- [ ] **Step 5: Run; expect 6 passed**

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/types/protocol.ts sidequest-ui/src/types/hub.ts \
        sidequest-ui/src/types/__tests__/hub.test.ts
git commit -m "feat(hub): add HUB_VIEW / DUNGEON_SELECT / RETREAT_TO_HAMLET types"
```

### Task 2: `SessionPhase` extension + reducer-style transition map

**Files:**
- Modify: `sidequest-ui/src/App.tsx`
- Test: `sidequest-ui/src/__tests__/phase_transitions.test.ts` (new)

This is a pure-logic task — no rendering yet. Extract a small helper so the state machine is testable in isolation.

- [ ] **Step 1: Locate the existing phase-transition logic in App.tsx**

```bash
grep -n "setSessionPhase" sidequest-ui/src/App.tsx | head -20
```

- [ ] **Step 2: Write failing test**

```ts
// src/__tests__/phase_transitions.test.ts
import { describe, expect, test } from "vitest";
import { nextPhase } from "@/lib/phaseTransitions";
import { MessageType } from "@/types/protocol";

describe("phase transitions", () => {
  test("connect → hub on HUB_VIEW", () => {
    expect(nextPhase("connect", { type: MessageType.HUB_VIEW },
                     { pendingDungeonSelect: false })).toBe("hub");
  });

  test("connect → creation on CHARACTER_CREATION", () => {
    expect(nextPhase("connect", { type: MessageType.CHARACTER_CREATION },
                     { pendingDungeonSelect: false }))
      .toBe("creation");
  });

  test("hub → game on first NARRATION when DUNGEON_SELECT is pending", () => {
    expect(nextPhase("hub", { type: MessageType.NARRATION },
                     { pendingDungeonSelect: true })).toBe("game");
  });

  test("hub stays hub on NARRATION when no DUNGEON_SELECT pending", () => {
    // Stale narration frame from a prior delve must NOT bounce the user
    // into game mode against their will. The flag is the only thing
    // standing between the user and a stale-narration race.
    expect(nextPhase("hub", { type: MessageType.NARRATION },
                     { pendingDungeonSelect: false })).toBe("hub");
  });

  test("game → hub on HUB_VIEW", () => {
    expect(nextPhase("game", { type: MessageType.HUB_VIEW },
                     { pendingDungeonSelect: false })).toBe("hub");
  });

  test("hub stays hub on unrelated frames", () => {
    expect(nextPhase("hub", { type: MessageType.IMAGE },
                     { pendingDungeonSelect: false })).toBe("hub");
    expect(nextPhase("hub", { type: MessageType.AUDIO_CUE },
                     { pendingDungeonSelect: true })).toBe("hub");
  });

  test("game stays game on unrelated frames", () => {
    expect(nextPhase("game", { type: MessageType.NARRATION },
                     { pendingDungeonSelect: false })).toBe("game");
  });
});
```

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Create `src/lib/phaseTransitions.ts`**

```ts
import { MessageType } from "@/types/protocol";

export type SessionPhase = "connect" | "hub" | "creation" | "game";

export interface PhaseContext {
  /** Set to true on DUNGEON_SELECT send; cleared on first NARRATION
   * receipt while in hub mode. Closes the in-flight-NARRATION race —
   * a stale narration frame from a prior delve cannot bounce the user
   * out of hub against their will. */
  pendingDungeonSelect: boolean;
}

export function nextPhase(
  current: SessionPhase,
  msg: { type: string },
  ctx: PhaseContext,
): SessionPhase {
  if (msg.type === MessageType.HUB_VIEW) {
    return "hub";
  }
  if (current === "connect") {
    if (msg.type === MessageType.CHARACTER_CREATION) return "creation";
    if (msg.type === MessageType.NARRATION) return "game";
    return "connect";
  }
  if (current === "hub" && msg.type === MessageType.NARRATION) {
    if (ctx.pendingDungeonSelect) {
      return "game";
    }
    // Stale narration in hub mode without a pending DUNGEON_SELECT.
    // Console-log so it's visible during dev; do not transition.
    console.warn(
      "[phase] ignored stale NARRATION in hub mode (no pending DUNGEON_SELECT)",
    );
    return "hub";
  }
  return current;
}
```

Note that `HUB_VIEW → hub` is checked first regardless of current phase — that handles `game → hub` (delve end) and `connect → hub` (hub-mode fresh connect) with one rule. The `pendingDungeonSelect` guard on the `hub → game` rule is the only state-context the reducer takes; everything else stays pure.

- [ ] **Step 5: Run; expect 7 passed**

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/lib/phaseTransitions.ts \
        sidequest-ui/src/__tests__/phase_transitions.test.ts
git commit -m "feat(phase): nextPhase helper with hub transitions"
```

### Task 3: Wire `nextPhase` into `App.tsx` + extend `SessionPhase` union

**Files:**
- Modify: `sidequest-ui/src/App.tsx`
- Test: `sidequest-ui/src/App.test.tsx` (existing)

- [ ] **Step 1: Write failing test**

```tsx
// App.test.tsx — add a test
test("HUB_VIEW frame routes user into hub phase", async () => {
  // Render App with a stubbed WS that emits HUB_VIEW after open.
  // (Adapt to existing test fixtures — App.test.tsx already mocks
  // useGameSocket; reuse that mock.)
  const { findByTestId } = render(<App />);
  // Stub the WS message dispatch to deliver:
  await act(async () => {
    deliverMessage({
      type: "HUB_VIEW",
      payload: makeStubHubView(),
      player_id: "p1",
    });
  });
  expect(await findByTestId("hub-screen")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Wire `nextPhase` into the message handler in App.tsx**

Replace the existing scattered `setSessionPhase("game")` etc. calls with a single funnel that, on every received message, computes:

```ts
const newPhase = nextPhase(sessionPhase, msg, {
  pendingDungeonSelect: pendingDungeonSelectRef.current,
});
if (newPhase !== sessionPhase) {
  setSessionPhase(newPhase);
  if (sessionPhase === "game" && newPhase === "hub") {
    resetDelveState();
  }
  if (sessionPhase === "hub" && newPhase === "game") {
    // First narration after DUNGEON_SELECT consumed — clear the flag.
    pendingDungeonSelectRef.current = false;
  }
}
```

Add a `useRef<boolean>(false)` named `pendingDungeonSelectRef` (a ref, not state — the reducer reads it as input but the value never needs to drive a render). Set to `true` at DUNGEON_SELECT send-time (Task 10); the reducer clears it on first NARRATION-while-in-hub.

Verify in step 1 of this task that the existing phase-set call sites all funnel through one place; if they don't, restructure first (small refactor).

`SessionPhase` union extends `"hub"` per §1.

A `<HubScreen>` placeholder mount under the `sessionPhase === "hub"` branch is enough for now — full HubScreen lands in task 4. Use `<div data-testid="hub-screen">Hub</div>` to make the wiring test green.

- [ ] **Step 4: `resetDelveState()` helper — factor from handleLeave per §6 checklist**

Use the **concrete checklist in §6** as the authoritative list of setters. The existing `handleLeave` block at `App.tsx:1229–1267` is the source — verify alignment via `git grep` *at execution time* (the file evolves; the plan was authored 2026-05-05). For each setter in `handleLeave` that is NOT in §6's resetDelveState list, confirm it falls into the §6 "setters that resetDelveState does NOT call" table — if you find one that's neither in the helper nor in the omission table, stop and ask before guessing.

After factoring, `handleLeave` becomes:

```ts
const handleLeave = useCallback(() => {
  disconnect();
  clearSession();
  resetDelveState();             // shared with game→hub transition
  setConnected(false);
  setSessionPhase("connect");
  sessionPhaseRef.current = "connect";
  autoReconnectAttempted.current = false;
  slugConnectFired.current = false;
  justConnectedRef.current = false;
  pendingConnectPayloadRef.current = null;
  pendingDungeonSelectRef.current = false;  // NEW: also clear here
  setGameMetaError(null);
  setCurrentGenre(null);
  setCurrentWorld(null);
  setSeatedPlayers({});
  setConnectedPlayerName("");
  setOffline(false);
  navigate("/");
}, [disconnect, navigate]);
```

The diff should preserve handleLeave's exact behavior (no state goes uncleared that was cleared before). A regression test in Task 12 walks `connect → game → hub → game` and asserts `messages` is empty between delves.

- [ ] **Step 5: Run; expect pass**

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/App.tsx sidequest-ui/src/App.test.tsx
git commit -m "feat(app): wire nextPhase + hub phase + resetDelveState"
```

### Task 4: `HirelingCard` component

**Files:**
- Create: `sidequest-ui/src/components/Hub/HirelingCard.tsx`
- Test: `sidequest-ui/src/components/Hub/__tests__/HirelingCard.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { HirelingCard } from "@/components/Hub/HirelingCard";
import type { Hireling } from "@/types/hub";

const h: Hireling = {
  id: "h1", name: "Volga Stein", archetype: "prig",
  stress: 12, status: "active", recruited_at_delve: 0, notes: "",
};

describe("HirelingCard", () => {
  test("renders name + archetype + stress", () => {
    render(<HirelingCard hireling={h} onDismiss={vi.fn()} />);
    expect(screen.getByText("Volga Stein")).toBeInTheDocument();
    expect(screen.getByText(/prig/i)).toBeInTheDocument();
    expect(screen.getByText(/12/)).toBeInTheDocument();
  });

  test("dismiss button fires callback with id", async () => {
    const onDismiss = vi.fn().mockResolvedValue(undefined);
    render(<HirelingCard hireling={h} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalledWith("h1");
  });

  test("dead hireling renders status badge and no dismiss button", () => {
    const dead = { ...h, status: "dead" as const };
    render(<HirelingCard hireling={dead} onDismiss={vi.fn()} />);
    expect(screen.getByText(/dead/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dismiss/i })).toBeNull();
  });

  test("selectable mode renders checkbox; toggle fires onToggleSelect", () => {
    const onToggleSelect = vi.fn();
    render(<HirelingCard hireling={h} onDismiss={vi.fn()}
                         selectable selected={false}
                         onToggleSelect={onToggleSelect} />);
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onToggleSelect).toHaveBeenCalledOnce();
  });

  test("selectable + dead is unchecked and disabled", () => {
    const dead = { ...h, status: "dead" as const };
    render(<HirelingCard hireling={dead} onDismiss={vi.fn()}
                         selectable selected={false}
                         onToggleSelect={vi.fn()} />);
    expect(screen.getByRole("checkbox")).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `HirelingCard`**

```tsx
// HirelingCard.tsx — minimal Tailwind layout
import type { Hireling } from "@/types/hub";

export function HirelingCard({
  hireling, onDismiss, selectable, selected, onToggleSelect,
}: HirelingCardProps) {
  const isActive = hireling.status === "active";
  return (
    <div className="flex items-center gap-3 rounded border border-border p-3">
      {selectable && (
        <input type="checkbox" checked={!!selected} disabled={!isActive}
               onChange={onToggleSelect}
               aria-label={`Select ${hireling.name}`} />
      )}
      <div className="flex-1">
        <div className="font-medium">{hireling.name}</div>
        <div className="text-sm text-muted-foreground">
          {hireling.archetype} · stress {hireling.stress}
          {hireling.status !== "active" && (
            <span className="ml-2 rounded bg-red-100 px-1 text-xs uppercase">
              {hireling.status}
            </span>
          )}
        </div>
      </div>
      {isActive && !selectable && (
        <button onClick={() => onDismiss(hireling.id)}
                className="text-sm text-destructive">
          Dismiss
        </button>
      )}
    </div>
  );
}
```

Match the project's existing component patterns for class names / button styles — verify by looking at `CharacterPanel.tsx` or another existing card-shaped component.

- [ ] **Step 4: Run; expect 5 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/Hub/HirelingCard.tsx \
        sidequest-ui/src/components/Hub/__tests__/HirelingCard.test.tsx
git commit -m "feat(hub): HirelingCard component"
```

### Task 5: `RosterPanel` component

**Files:**
- Create: `sidequest-ui/src/components/Hub/RosterPanel.tsx`
- Test: `sidequest-ui/src/components/Hub/__tests__/RosterPanel.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
describe("RosterPanel", () => {
  test("renders empty state when roster is empty", () => {
    render(<RosterPanel roster={[]} delveCount={0}
                        onRecruit={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText(/no hirelings/i)).toBeInTheDocument();
  });

  test("renders one HirelingCard per roster entry", () => {
    const roster = [
      makeHireling("h1", "Volga"),
      makeHireling("h2", "Karl"),
    ];
    render(<RosterPanel roster={roster} delveCount={2}
                        onRecruit={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText("Volga")).toBeInTheDocument();
    expect(screen.getByText("Karl")).toBeInTheDocument();
  });

  test("recruit button fires callback", async () => {
    const onRecruit = vi.fn().mockResolvedValue(undefined);
    render(<RosterPanel roster={[]} delveCount={0}
                        onRecruit={onRecruit} onDismiss={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /recruit/i }));
    expect(onRecruit).toHaveBeenCalledOnce();
  });

  test("recruit button is disabled while in-flight", async () => {
    let resolve: () => void = () => {};
    const onRecruit = vi.fn(() => new Promise<void>(r => { resolve = r; }));
    render(<RosterPanel roster={[]} delveCount={0}
                        onRecruit={onRecruit} onDismiss={vi.fn()} />);
    const btn = screen.getByRole("button", { name: /recruit/i });
    fireEvent.click(btn);
    await waitFor(() => expect(btn).toBeDisabled());
    resolve();
    await waitFor(() => expect(btn).not.toBeDisabled());
  });
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `RosterPanel`**

Local `useState<boolean>(false)` for in-flight recruit lock. Layout: panel header with delve count ("Delve 3 — 2 hirelings"), `<HirelingCard>` list, recruit button at bottom.

- [ ] **Step 4: Run; expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/Hub/RosterPanel.tsx \
        sidequest-ui/src/components/Hub/__tests__/RosterPanel.test.tsx
git commit -m "feat(hub): RosterPanel component"
```

### Task 6: `WallView` component

**Files:**
- Create: `sidequest-ui/src/components/Hub/WallView.tsx`
- Test: `sidequest-ui/src/components/Hub/__tests__/WallView.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
describe("WallView", () => {
  test("renders empty state when wall is empty", () => {
    render(<WallView wall={[]} rosterById={{}} latestDelveSin={null} />);
    expect(screen.getByText(/the wall is empty/i)).toBeInTheDocument();
  });

  test("renders entries newest-first with sin and outcome", () => {
    const wall: WallEntry[] = [
      {
        delve_number: 1, sin: "pride", dungeon: "grimvault",
        party_hireling_ids: ["h1"],
        outcome: "victory", wounded_boss: false,
        timestamp: "2026-05-04T10:00:00Z",
      },
      {
        delve_number: 2, sin: "greed", dungeon: "horden",
        party_hireling_ids: ["h1"],
        outcome: "defeat", wounded_boss: false,
        timestamp: "2026-05-05T10:00:00Z",
      },
    ];
    render(<WallView wall={wall}
                     rosterById={{ h1: makeHireling("h1", "Volga") }}
                     latestDelveSin="greed" />);
    const entries = screen.getAllByTestId("wall-entry");
    expect(entries).toHaveLength(2);
    // Newest first
    expect(entries[0]).toHaveTextContent("2");
    expect(entries[0]).toHaveTextContent(/greed/i);
    expect(entries[0]).toHaveTextContent(/defeat/i);
  });

  test("resolves party_hireling_ids to names; falls back to id when missing", () => {
    const wall: WallEntry[] = [{
      delve_number: 1, sin: "pride", dungeon: "grimvault",
      party_hireling_ids: ["h1", "h_gone"],
      outcome: "retreat", wounded_boss: false,
      timestamp: "2026-05-04T10:00:00Z",
    }];
    render(<WallView wall={wall}
                     rosterById={{ h1: makeHireling("h1", "Volga") }}
                     latestDelveSin="pride" />);
    expect(screen.getByText(/Volga/)).toBeInTheDocument();
    expect(screen.getByText(/h_gone/)).toBeInTheDocument();
  });

  test("highlights the row matching latestDelveSin", () => {
    const wall: WallEntry[] = [
      { delve_number: 1, sin: "pride", dungeon: "grimvault",
        party_hireling_ids: [],
        outcome: "victory", wounded_boss: false,
        timestamp: "2026-05-04T10:00:00Z" },
      { delve_number: 2, sin: "greed", dungeon: "horden",
        party_hireling_ids: [],
        outcome: "retreat", wounded_boss: false,
        timestamp: "2026-05-05T10:00:00Z" },
    ];
    render(<WallView wall={wall} rosterById={{}} latestDelveSin="greed" />);
    const greed = screen.getByTestId("wall-entry-2");
    expect(greed).toHaveAttribute("data-latest", "true");
    const pride = screen.getByTestId("wall-entry-1");
    expect(pride).not.toHaveAttribute("data-latest", "true");
  });
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `WallView`**

Sort by `delve_number` descending. Resolve names via `rosterById[id]?.name ?? id`. Add `data-testid="wall-entry"` and `data-testid={`wall-entry-${delve_number}`}` and `data-latest="true"` when `entry.sin === latestDelveSin && entry === sortedFirstWithThatSin` (first occurrence; subsequent ones are not highlighted).

- [ ] **Step 4: Run; expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/Hub/WallView.tsx \
        sidequest-ui/src/components/Hub/__tests__/WallView.test.tsx
git commit -m "feat(hub): WallView component"
```

### Task 7: `SinCard` + `DungeonPicker` components

**Files:**
- Create: `sidequest-ui/src/components/Hub/SinCard.tsx`, `DungeonPicker.tsx`
- Test: `sidequest-ui/src/components/Hub/__tests__/SinCard.test.tsx`, `DungeonPicker.test.tsx`

**No `sinMap.ts`** — sin labels arrive on `AvailableDungeon.sin` from the server (item 4a's enriched HUB_VIEW payload). The client never duplicates the sin→dungeon mapping. Future hub-world genre packs (heavy_metal, etc.) get sin-labeled UI for free.

- [ ] **Step 1: Write failing tests**

```tsx
// SinCard.test.tsx
import type { AvailableDungeon } from "@/types/hub";

const grim: AvailableDungeon = { slug: "grimvault", sin: "pride", wounded: false };

describe("SinCard", () => {
  test("renders sin name and dungeon name from props", () => {
    render(<SinCard dungeon={grim} onClick={vi.fn()} />);
    expect(screen.getByText(/pride/i)).toBeInTheDocument();
    expect(screen.getByText(/grimvault/i)).toBeInTheDocument();
  });

  test("shows wounded badge when wounded", () => {
    render(<SinCard
      dungeon={{ ...grim, wounded: true }}
      onClick={vi.fn()} />);
    expect(screen.getByText(/wounded/i)).toBeInTheDocument();
  });

  test("click fires onClick", () => {
    const onClick = vi.fn();
    render(<SinCard dungeon={grim} onClick={onClick} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  test("future hub-world sin (e.g. metal pack) renders without changes", () => {
    // Defensive: this proves the component is data-driven, not tied to
    // the three caverns sins. A future heavy_metal hub world ships
    // {slug: "the_pit", sin: "wrath", wounded: false} and SinCard renders.
    const future: AvailableDungeon = { slug: "the_pit", sin: "wrath", wounded: false };
    render(<SinCard dungeon={future} onClick={vi.fn()} />);
    expect(screen.getByText(/wrath/i)).toBeInTheDocument();
    expect(screen.getByText(/the_pit/i)).toBeInTheDocument();
  });
});

// DungeonPicker.test.tsx
const threeSins: AvailableDungeon[] = [
  { slug: "grimvault", sin: "pride", wounded: false },
  { slug: "horden", sin: "greed", wounded: false },
  { slug: "mawdeep", sin: "gluttony", wounded: false },
];

describe("DungeonPicker", () => {
  test("renders one SinCard per available_dungeon", () => {
    render(<DungeonPicker
      availableDungeons={threeSins}
      roster={[]}
      onStartDelve={vi.fn()} />);
    expect(screen.getAllByRole("button", { name: /pride|greed|gluttony/i }))
      .toHaveLength(3);
  });

  test("clicking a card opens PartySelectDialog", () => {
    render(<DungeonPicker
      availableDungeons={[threeSins[0]]}
      roster={[makeHireling("h1", "Volga")]}
      onStartDelve={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /pride/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  test("wounded dungeon renders the wounded badge", () => {
    render(<DungeonPicker
      availableDungeons={[{ ...threeSins[0], wounded: true }]}
      roster={[]}
      onStartDelve={vi.fn()} />);
    expect(screen.getByText(/wounded/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `SinCard.tsx` + `DungeonPicker.tsx`**

Per §4. `DungeonPicker` holds `useState<AvailableDungeon | null>(null)` for the currently-open dungeon (party-select dialog target). Render `dungeon.sin` and `dungeon.slug` directly from props — no client-side sin lookup.

- [ ] **Step 4: Run; expect 7 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/Hub/SinCard.tsx \
        sidequest-ui/src/components/Hub/DungeonPicker.tsx \
        sidequest-ui/src/components/Hub/__tests__/SinCard.test.tsx \
        sidequest-ui/src/components/Hub/__tests__/DungeonPicker.test.tsx
git commit -m "feat(hub): SinCard + DungeonPicker (server-resolved sin labels)"
```

### Task 8: `PartySelectDialog`

**Files:**
- Create: `sidequest-ui/src/components/Hub/PartySelectDialog.tsx`
- Test: `sidequest-ui/src/components/Hub/__tests__/PartySelectDialog.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
describe("PartySelectDialog", () => {
  const roster = [
    makeHireling("h1", "Volga"),
    makeHireling("h2", "Karl"),
    makeHireling("h3", "Grete", "dead"),
  ];

  test("renders one row per roster member; dead disabled", () => {
    render(<PartySelectDialog open dungeon="grimvault" sin="pride"
                              roster={roster}
                              onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("Volga")).toBeInTheDocument();
    expect(screen.getByText("Karl")).toBeInTheDocument();
    // Grete renders but checkbox is disabled (HirelingCard handles it)
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes[2]).toBeDisabled();
  });

  test("start delve disabled when no party selected", () => {
    render(<PartySelectDialog open dungeon="grimvault" sin="pride"
                              roster={roster}
                              onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: /start delve/i }))
      .toBeDisabled();
  });

  test("start delve enabled with 1+ active selected; fires onConfirm with ids", () => {
    const onConfirm = vi.fn();
    render(<PartySelectDialog open dungeon="grimvault" sin="pride"
                              roster={roster}
                              onConfirm={onConfirm} onCancel={vi.fn()} />);
    fireEvent.click(screen.getAllByRole("checkbox")[0]);  // Volga
    const btn = screen.getByRole("button", { name: /start delve/i });
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(onConfirm).toHaveBeenCalledWith(["h1"]);
  });

  test("cap at 6 — selecting a 7th does nothing", () => {
    const big = Array.from({ length: 7 }, (_, i) =>
      makeHireling(`h${i}`, `Hireling${i}`));
    render(<PartySelectDialog open dungeon="grimvault" sin="pride"
                              roster={big}
                              onConfirm={vi.fn()} onCancel={vi.fn()} />);
    const checkboxes = screen.getAllByRole("checkbox");
    for (const c of checkboxes) fireEvent.click(c);
    // Only 6 should be checked.
    const checked = checkboxes.filter((c) => (c as HTMLInputElement).checked);
    expect(checked).toHaveLength(6);
  });

  test("cancel fires onCancel", () => {
    const onCancel = vi.fn();
    render(<PartySelectDialog open dungeon="grimvault" sin="pride"
                              roster={roster}
                              onConfirm={vi.fn()} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `PartySelectDialog` using base-ui Dialog primitives**

`useState<Set<string>>(new Set())` for selected ids. Toggling on a 7th when 6 are selected is a no-op (the 6-cap matches the server validation in materialize_party). Dialog uses `@base-ui/react`'s `Dialog.*` primitives — verify by looking at any existing dialog component in the codebase (e.g. `ConfrontationOverlay.tsx`).

- [ ] **Step 4: Run; expect 5 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/Hub/PartySelectDialog.tsx \
        sidequest-ui/src/components/Hub/__tests__/PartySelectDialog.test.tsx
git commit -m "feat(hub): PartySelectDialog"
```

### Task 9: `HubScreen` — composition

**Files:**
- Create: `sidequest-ui/src/screens/HubScreen.tsx`
- Test: `sidequest-ui/src/screens/__tests__/HubScreen.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
describe("HubScreen", () => {
  const stub: HubViewPayload = {
    slug: "test-1",
    genre_slug: "caverns_and_claudes",
    world_slug: "caverns_three_sins",
    available_dungeons: [
      { slug: "grimvault", sin: "pride", wounded: false },
      { slug: "horden", sin: "greed", wounded: true },
      { slug: "mawdeep", sin: "gluttony", wounded: false },
    ],
    world_save: {
      roster: [makeHireling("h1", "Volga")],
      currency: 0,
      wall: [],
      dungeon_wounds: { horden: true },
      latest_delve_sin: null,
      delve_count: 0,
      last_saved_at: null,
    },
  };

  test("renders all four sub-panels", () => {
    render(<HubScreen hubView={stub} onRecruit={vi.fn()}
                      onDismiss={vi.fn()} onStartDelve={vi.fn()}
                      onLeave={vi.fn()} />);
    expect(screen.getByTestId("hub-screen")).toBeInTheDocument();
    expect(screen.getByText("Volga")).toBeInTheDocument();        // RosterPanel
    expect(screen.getByText(/the wall is empty/i)).toBeInTheDocument();  // WallView
    expect(screen.getAllByText(/pride|greed|gluttony/i).length)
      .toBeGreaterThanOrEqual(3);                                // DungeonPicker
  });

  test("dungeon-pick → party-select → start-delve invokes onStartDelve", () => {
    const onStartDelve = vi.fn();
    render(<HubScreen hubView={stub} onRecruit={vi.fn()}
                      onDismiss={vi.fn()} onStartDelve={onStartDelve}
                      onLeave={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /pride/i }));
    fireEvent.click(screen.getAllByRole("checkbox")[0]);
    fireEvent.click(screen.getByRole("button", { name: /start delve/i }));
    expect(onStartDelve).toHaveBeenCalledWith("grimvault", ["h1"]);
  });

  test("displays world identity and delve count in header", () => {
    const withCount = { ...stub, world_save: { ...stub.world_save,
                                                delve_count: 5 } };
    render(<HubScreen hubView={withCount} onRecruit={vi.fn()}
                      onDismiss={vi.fn()} onStartDelve={vi.fn()}
                      onLeave={vi.fn()} />);
    expect(screen.getByText(/sünden|caverns_three_sins/i)).toBeInTheDocument();
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });

  test("Leave button fires onLeave", () => {
    const onLeave = vi.fn();
    render(<HubScreen hubView={stub} onRecruit={vi.fn()}
                      onDismiss={vi.fn()} onStartDelve={vi.fn()}
                      onLeave={onLeave} />);
    fireEvent.click(screen.getByRole("button", { name: /leave/i }));
    expect(onLeave).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `HubScreen.tsx`**

Layout: header (world_slug or "Sünden" hardcoded if `world_slug==="caverns_three_sins"`, plus delve count), three-column body (RosterPanel left, WallView middle, DungeonPicker right — or stack vertically on narrow viewports), footer with Leave button. `useMemo` to build `rosterById` for `WallView` from `hubView.world_save.roster`.

- [ ] **Step 4: Run; expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/screens/HubScreen.tsx \
        sidequest-ui/src/screens/__tests__/HubScreen.test.tsx
git commit -m "feat(hub): HubScreen composition"
```

### Task 10: Wire `HubScreen` into `App.tsx` with REST + WS handlers

**Files:**
- Modify: `sidequest-ui/src/App.tsx`
- Test: `sidequest-ui/src/App.test.tsx` (existing — extend)

- [ ] **Step 1: Write failing tests**

```tsx
test("Recruit button POSTs /api/games/:slug/hub/recruit and refetches state", async () => {
  // Mock fetch for both POST and the follow-up GET.
  const fetchMock = vi.spyOn(global, "fetch")
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: "h_new" }) } as Response)
    .mockResolvedValueOnce({ ok: true, json: async () => makeStubHubView({
      roster: [makeHireling("h_new", "Vox")],
    })} as Response);

  // Render App, deliver HUB_VIEW, click Recruit.
  // Assert fetchMock called with /api/games/<slug>/hub/recruit (POST)
  // and /api/games/<slug>/hub (GET).
});

test("Dismiss button DELETEs and refetches", async () => {
  // Same shape as above, against /api/games/<slug>/hub/roster/h1?reason=dismiss
});

test("Start Delve sends DUNGEON_SELECT WS frame", async () => {
  // Mock the WS sendMessage; assert DUNGEON_SELECT frame with
  // payload {dungeon, party_hireling_ids}.
});

test("HUB_VIEW after a delve clears messages and routes back to hub", async () => {
  // Set sessionPhase to "game", deliver HUB_VIEW, assert messages
  // is reset to [] and HubScreen is rendered.
});
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Wire the handlers in `App.tsx`**

In the `sessionPhase === "hub"` branch, mount:

```tsx
<HubScreen
  hubView={hubView!}
  onRecruit={async () => {
    const res = await fetch(`/api/games/${slug}/hub/recruit`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) {
      setTransientError(`Recruit failed: ${res.status}`);
      return;
    }
    await fetchHubState(slug!);  // refetch GET /api/games/.../hub
  }}
  onDismiss={async (id) => {
    const res = await fetch(
      `/api/games/${slug}/hub/roster/${id}?reason=dismiss`,
      { method: "DELETE" },
    );
    if (!res.ok) {
      setTransientError(`Dismiss failed: ${res.status}`);
      return;
    }
    await fetchHubState(slug!);
  }}
  onStartDelve={(dungeon, partyIds) => {
    // Arm the pendingDungeonSelect flag BEFORE sending. The reducer
    // reads this on the first NARRATION receipt — without it, a stale
    // narration frame would bounce the user out of hub mode.
    pendingDungeonSelectRef.current = true;
    sendMessage({
      type: MessageType.DUNGEON_SELECT,
      payload: { dungeon, party_hireling_ids: partyIds },
      player_id: playerId,
    });
  }}
  onLeave={handleLeave}
/>
```

`fetchHubState` is the helper from §3. Add it. Also: the `HUB_VIEW` message handler in the WS dispatch (already added in task 3 for phase) must also `setHubView(payload)` — extend the dispatch.

- [ ] **Step 4: Run; expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/App.tsx sidequest-ui/src/App.test.tsx
git commit -m "feat(app): wire HubScreen with recruit/dismiss/select-delve"
```

### Task 11: `RetreatDialog` + Retreat button in GameBoard

**Files:**
- Create: `sidequest-ui/src/components/Hub/RetreatDialog.tsx`
- Modify: `sidequest-ui/src/components/GameBoard/GameBoard.tsx` (or wherever the top bar lives — verify in step 1)
- Test: `sidequest-ui/src/components/Hub/__tests__/RetreatDialog.test.tsx`, plus an integration test in `App.test.tsx`

- [ ] **Step 1: Locate the GameBoard top bar**

```bash
grep -nE "RetreatButton|topbar|TopBar|header" sidequest-ui/src/components/GameBoard/*.tsx | head
```

- [ ] **Step 2: Write failing test**

```tsx
describe("RetreatDialog", () => {
  test("renders two outcome buttons + wounded-boss checkbox", () => {
    render(<RetreatDialog open dungeon="grimvault"
                          onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: /^retreat$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /victory/i })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /wounded the boss/i }))
      .toBeInTheDocument();
  });

  test("victory click fires onConfirm with outcome + woundedBoss=false by default", () => {
    const onConfirm = vi.fn();
    render(<RetreatDialog open dungeon="grimvault"
                          onConfirm={onConfirm} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /victory/i }));
    expect(onConfirm).toHaveBeenLastCalledWith("victory", false);
  });

  test("retreat click fires onConfirm with outcome + woundedBoss=false by default", () => {
    const onConfirm = vi.fn();
    render(<RetreatDialog open dungeon="grimvault"
                          onConfirm={onConfirm} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /^retreat$/i }));
    expect(onConfirm).toHaveBeenLastCalledWith("retreat", false);
  });

  test("checking wounded-boss + retreat fires (retreat, true) — TPK-after-wound case", () => {
    const onConfirm = vi.fn();
    render(<RetreatDialog open dungeon="grimvault"
                          onConfirm={onConfirm} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("checkbox", { name: /wounded the boss/i }));
    fireEvent.click(screen.getByRole("button", { name: /^retreat$/i }));
    expect(onConfirm).toHaveBeenLastCalledWith("retreat", true);
  });

  test("checking wounded-boss + victory fires (victory, true) — full success", () => {
    const onConfirm = vi.fn();
    render(<RetreatDialog open dungeon="grimvault"
                          onConfirm={onConfirm} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("checkbox", { name: /wounded the boss/i }));
    fireEvent.click(screen.getByRole("button", { name: /victory/i }));
    expect(onConfirm).toHaveBeenLastCalledWith("victory", true);
  });

  test("does NOT include defeat (server-only)", () => {
    render(<RetreatDialog open dungeon="grimvault"
                          onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /defeat/i })).toBeNull();
  });
});
```

For the GameBoard wiring, in `App.test.tsx`:

```tsx
test("Retreat button visible only during a delve", () => {
  // Render with snapshot.active_delve_dungeon = "grimvault"; expect button.
  // Render with snapshot.active_delve_dungeon = null; expect no button.
});

test("Retreat button → dialog → outcome → RETREAT_TO_HAMLET message sent", () => {
  // Click Retreat → dialog opens → check Wounded-the-Boss → click Victory →
  // assert sendMessage called with
  // {type: RETREAT_TO_HAMLET, payload: {outcome: "victory", wounded_boss: true}}.
});
```

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Implement `RetreatDialog` + GameBoard hookup**

`RetreatDialog` is a small base-ui Dialog with two buttons (Retreat / Victory) and a "Wounded the boss" checkbox. The dialog holds local `useState<boolean>(false)` for the wound flag; clicking either outcome button fires `onConfirm(outcome, woundedBoss)`. The GameBoard top-bar gets a button that opens the dialog when `snapshot?.active_delve_dungeon != null`. On dialog confirm, fire:

```ts
sendMessage({
  type: MessageType.RETREAT_TO_HAMLET,
  payload: { outcome, wounded_boss: woundedBoss },
  player_id: playerId,
});
```

Where the button lives in the GameBoard layout: place it next to whatever existing top-bar control matches its weight (e.g. the Yield button — search). If the GameBoard has no obvious top bar, place it inline in `App.tsx` *above* the GameBoard mount, gated on the same predicate.

- [ ] **Step 5: Run; expect 5 passed**

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/components/Hub/RetreatDialog.tsx \
        sidequest-ui/src/components/GameBoard/*.tsx \
        sidequest-ui/src/App.tsx \
        sidequest-ui/src/components/Hub/__tests__/RetreatDialog.test.tsx \
        sidequest-ui/src/App.test.tsx
git commit -m "feat(hub): RetreatDialog + in-game Retreat button"
```

### Task 12: Smoke + lint + build

- [ ] **Step 1: Run full test suite**

```bash
cd sidequest-ui && npx vitest run
```
Expected: all green.

- [ ] **Step 2: Lint**

```bash
cd sidequest-ui && npm run lint
```
Expected: clean.

- [ ] **Step 3: Production build**

```bash
cd sidequest-ui && npm run build
```
Expected: green.

- [ ] **Step 4: Manual playthrough**

```bash
just up   # boots server + UI + daemon
```

Walk the loop in a browser:
1. Lobby → New game → genre `caverns_and_claudes`, world `caverns_three_sins`.
2. Land on HubScreen — empty roster, empty Wall, three sin cards (Pride/Greed/Gluttony) — labels driven by server-side `AvailableDungeon.sin`.
3. Click Recruit twice — two hirelings appear.
4. Click Pride card → PartySelectDialog opens → check both → Start Delve.
5. Confirm phase transitions to game; opening narration fires.
6. Click Retreat → leave wounded-boss checkbox unchecked → click Victory.
7. HubScreen reappears; Wall has one entry (outcome=victory, wounded_boss=false); latest-delve-sin badge shows Pride; no dungeon shows wounded.
8. Recruit one more.
9. Click Greed card → PartySelectDialog → start a second delve.
10. Click Retreat → **check** wounded-boss checkbox → click Victory.
11. HubScreen reappears; Greed card now shows the Wounded badge; Wall has 2 entries; second entry has wounded_boss=true.
12. **Regression check:** confirm `messages` is empty (narration log cleared between delves — `resetDelveState()` working).

If any step fails, debug before proceeding to PR.

- [ ] **Step 5: Confirm the OTEL spans Sebastien gets**

In a separate browser tab, open `http://localhost:8765/dashboard`. The Console tab should show the spans from item 4a firing on each step: `session.hub_mode_entered`, `session.hireling_recruited` (×3 total), `session.delve_started` (×2), `session.delve_ended` (×2 — both with outcome `victory`; the second with `wounded_boss=true` flipping `dungeon_wounds.horden=true`). The span attributes must include `outcome` AND `wounded_boss` separately so Sebastien can see what was claimed. This is the GM-panel verification — *Sebastien-test*.

### Task 13: PR

- [ ] **Step 1: Push branch and open PR (gitflow → develop)**

```bash
cd sidequest-ui
git push -u origin feat/sunden-hub-ui
gh pr create --base develop --title "feat: Sünden hub UI (Sünden item 4b)" --body "$(cat <<'EOF'
## Summary
- New `hub` SessionPhase with `nextPhase(current, msg, ctx)` reducer in src/lib/phaseTransitions.ts. The `pendingDungeonSelect` flag in ctx closes the in-flight-NARRATION race so a stale narration cannot bounce the user out of hub.
- New `HubScreen` composing RosterPanel, WallView, DungeonPicker, and PartySelectDialog.
- DungeonPicker / SinCard render server-resolved sin labels from `AvailableDungeon.sin` — **no client-side `SIN_BY_DUNGEON` map**. Future hub-world packs get sin-labeled UI for free.
- Retreat button on GameBoard (visible only mid-delve) opens RetreatDialog with two outcome buttons (retreat / victory) and a separate "Wounded the boss" checkbox (orthogonal). Defeat is server-driven.
- `resetDelveState()` factored from `handleLeave` per the §6 concrete checklist.
- REST: POST /api/games/{slug}/hub/recruit; DELETE /api/games/{slug}/hub/roster/{id}.
- WS: outbound DUNGEON_SELECT + RETREAT_TO_HAMLET (`outcome` + `wounded_boss`); inbound HUB_VIEW (enriched `available_dungeons`).
- Component tests + App-level wiring tests; manual playthrough notes in plan §Task 12.

## Plan
docs/superpowers/plans/2026-05-05-sunden-hub-ui.md (orchestrator).

## Sequenced after
- sidequest-server item 2 PR (world save persistence)
- sidequest-server item 4a PR (delve lifecycle engine)

## Test plan
- [x] vitest run — all green
- [x] npm run lint — clean
- [x] npm run build — green
- [x] manual playthrough: recruit → delve → retreat → delve → wound (Task 12 step 4)
- [x] OTEL spans visible in /dashboard during the playthrough (Task 12 step 5)

## Unblocks
- Visual polish / asset pipeline for caverns_three_sins (separate plan)
- Stress UI growth path (item 3 lands a numeric stress; the existing display surfaces it)
- Stress-relief services UI (Confessional / Workhouse / Masquerade — item 4-followon)
EOF
)"
```

## Risks

- **Phase-machine sequencing under network latency.** `hub → game` transitions on the *first* NARRATION received while in `hub` mode AND `pendingDungeonSelectRef.current` is true. The flag is the in-flight-NARRATION race mitigation. *Mitigation:* `pendingDungeonSelectRef` is set on DUNGEON_SELECT send, cleared on first NARRATION-while-in-hub. A stale NARRATION arriving without the flag set is logged and ignored (Task 2 covers this in the reducer test). The flag also clears on `handleLeave`.
- **`resetDelveState()` factoring is invasive.** The existing `handleLeave` body at `App.tsx:1229–1267` is not a tidy reset block — state-clearing is scattered across several `useState` setters and refs. Extracting a clean helper requires reading every setter and being sure none has a side effect that should NOT fire on `game→hub` (e.g. closing the WS, navigating away, clearing slug-connect refs). *Mitigation:* §6 of this plan ships a **concrete checklist** of every setter resetDelveState() must call AND a table of setters it must NOT call (with rationale per omission). Task 3 step 4 enforces an execution-time grep against the current `handleLeave` to catch any drift since plan-authoring (2026-05-05). Task 12 includes a regression smoke that walks `connect → hub → game → hub → game` and asserts `messages` is empty between delves.
- **Recruit/dismiss race conditions across multiplayer.** Per spec, multiplayer-shared roster is allowed by the server but solo-only-tested in this plan. Two clients clicking Recruit simultaneously each get a hireling rolled — the server is fine (each call is its own POST), but the *first* client's refetch might race the *second* client's POST. *Mitigation:* not a defect — last-write-wins is acceptable per §"Out of scope". A future MP-aware UI would need WS-broadcast HUB_VIEW deltas; out of scope.
- **PartySelectDialog 6-cap UX.** If the player has 7+ active hirelings and tries to check a 7th, the test asserts the click is a no-op — but the user gets no feedback about *why*. *Mitigation:* add a small inline message ("Max 6 hirelings per delve") that appears when a 7th-click is silently rejected. Cheap to add.
- **Wounded-badge legibility colliding with theme colors.** caverns_and_claudes theme may already use red for hostility; the wounded badge needs to read distinctly. *Mitigation:* use a theme-neutral indicator (a small icon + the text "Wounded") rather than a colored pill. Verifies in Task 12 step 4 manual playthrough.
- **`sin` field on a future hub-world genre pack — eliminated risk.** The earlier draft hardcoded `SIN_BY_DUNGEON` in TS; this plan removed it during review. Sin labels now arrive on `AvailableDungeon.sin` from item 4a's enriched HUB_VIEW payload, resolved server-side from `Dungeon.config.sin`. A future hub world (heavy_metal, mutant_wasteland) gets sin-labeled UI for free with zero TS changes. The future-pack regression test is in `SinCard.test.tsx` (`future hub-world sin renders without changes`).
- **Defeat rendering.** When the server fires the `player_dead → defeat` auto-end, the UI receives a `HUB_VIEW` and routes back to hub. The user sees their just-killed party in the Wall as `outcome: "defeat"` — no specific "you died" panel. *Mitigation:* consider a transient toast / banner ("Your party fell in {dungeon}") that fires when the most-recent Wall entry's outcome is `"defeat"` AND the previous phase was `"game"`. Small UX polish; can be a follow-on if it adds task creep here.

## Definition of Done

- All 13 tasks complete.
- `npx vitest run` green; `npm run lint` clean; `npm run build` green.
- Manual playthrough (Task 12 step 4) succeeds end-to-end without console errors.
- The five OTEL spans from item 4a are visible in `/dashboard` during the playthrough (Task 12 step 5). Sebastien-test.
- A `caverns_and_claudes/caverns_three_sins` save can be created from the lobby, recruited into, delved twice (one Pride victory with wounded_boss=false, one Greed victory with wounded_boss=true), and the second hub-return shows: 2 Wall entries (both outcome=victory, second has wounded_boss=true), latest_delve_sin = "greed", dungeon_wounds.horden = true, the Greed card shows the Wounded badge.
- A `space_opera/coyote_star` save (leaf world) starts character creation and plays normally — regression guard from Task 3.
- PR open against `slabgorb/sidequest-ui` `develop`. Sequenced after sidequest-server items 2 and 4a.
- Items 3, 5–7, the test sweep, and any future stress-relief services UI plan can build on top of the protocol surfaces and components this plan introduces.
