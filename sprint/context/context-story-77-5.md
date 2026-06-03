---
parent: context-epic-77.md
workflow: tdd
---

# Story 77-5: Quest/objective panel — render quest_log + quest_anchors + active_stakes (quests payload)

> **Numbering note.** This is the **sprint** story 77-5. ADR-137 §Implementation
> Stories numbers it **77-6** ("Quest/objective panel"), because the ADR table was
> written when the design story was 77-1. Per the epic-context mapping, ADR 77-6 →
> sprint **77-5**. Wherever this doc cites "ADR-137 77-6," it means *this* story.

## Business Context

The wry_whimsy/oz playtest (2026-06-02, 13 turns) ran against a world whose entire
premise *is* a campaign spine — *"the traveler arrives by accident and wants only to
go home"* — yet the player had **no objective surface at all**. The turn-13 snapshot
showed `quest_log: {}`, `quest_anchors: []`, `active_stakes: ""`. The session ran on
pure narrator improvisation: the player could not see, anywhere in the UI, what they
were working toward or what was at stake. For a forever-GM-turned-player like Keith,
a campaign spine that lives only in the narrator's head (never on a visible sheet) is
exactly the tell a good human DM never produces.

This story is the **player-facing increment** of ADR-137 (Option D, committed as a
fast-follow). The server lane (sprint 77-1…77-4) seeds and maintains the spine and
emits OTEL spans so the GM panel can prove the substrate is engaged. **This story
makes the spine *visible to the player*.** It renders three things in one dockable
panel: the **quest log** (what am I doing), the **quest anchors** (where/when the
objective resolves — the beat/location bridge the orbital course planner already
consumes per ADR-130), and the **active stakes** (what's at risk right now).

Per CLAUDE.md, this is precisely the kind of surface the **mechanics-first players
(Sebastien, Jade)** want: mechanical campaign state made legible in a *player-facing*
surface. It is also Keith-as-player's objective tracker. This is a render-only
consumer of an already-projected server field — no game logic, no writes.

## Technical Guardrails

- **Render-only consumer. No write logic.** This panel reads projected state and
  displays it. It does **not** create, evolve, seed, or mutate quests/stakes — all of
  that is the server lane (77-1…77-4) via `record_quest`/`set_stakes`/the creation
  seed. Adding any client-side quest-write affordance is out of scope and a
  guardrail violation.

- **Gated on the server projection being OTEL-verified first (fast-follow).** ADR-137
  §"Why C-core + D-as-fast-follow" is explicit: the server fix must land and be
  **OTEL-verified independently** (the GM panel is the lie-detector for
  `quest.seeded_at_creation` / `quest.created` / `quest.anchor.added` / `stakes.set`)
  *before* this panel consumes the projection. Do not start the panel against an
  empty/improvised projection — confirm the spine is actually populated in a live
  session (or a real snapshot fixture) before treating it as the source of truth.
  This honors "Verify Wiring, Not Just Existence."

- **The rich `quests` projection does not exist yet — it is a blocking dependency.**
  Measured against `sidequest-ui` HEAD (2026-06-02): a `quests` field *does* exist,
  but it is **the wrong shape for this story**. It is declared as
  `quests?: Record<string, string>` on `StateDelta` (`src/types/payloads.ts:46`),
  carried into `ClientGameState` as `quests: Record<string, string>`
  (`src/providers/GameStateProvider.tsx:64,109`), and merged in the state mirror
  (`src/hooks/useStateMirror.ts:389-390`). That is the **legacy quest-title→status
  map** (e.g. `{ "Find the Amulet": "in_progress" }` — see
  `GameStateProvider.test.tsx`). It carries **only `quest_log`-as-status-strings**;
  it has **no `quest_anchors` and no `active_stakes`**. There is **no rich `quests`
  payload** (no `QuestsPayload` interface, no `QUESTS` message type, no projection
  carrying log+anchors+stakes together). **Before implementation, the Dev/TEA must
  confirm with the server lane whether 77-1…77-4 ship a richer `quests` projection
  (analogous to the `RELATIONSHIPS` snapshot / `RelationshipEntryPayload`). If it
  does not, this story is BLOCKED on a server projection field** — flag it, do not
  invent the panel against the thin `Record<string, string>` and call it done. The
  ADR's claim that "the `quests` field already exists in payloads.ts and renders
  nowhere" is *partially* true (a field exists) but **understates the gap**: the
  field present today cannot express anchors or stakes.

- **Mirror the established dock-panel pattern — do not invent a new one.** The
  reference implementation is the ADR-136 Relationships panel, which is structurally
  identical in intent (a player-facing, mechanics-legible, snapshot-fed dock tab):
  - **Presentational panel**: `src/components/RelationshipsPanel.tsx` — pure
    component taking a typed `data` prop, empty-state branch first, `data-testid`
    hooks, Folio palette via CSS custom properties (no color accessor).
  - **Thin widget adapter**: `src/components/GameBoard/widgets/RelationshipsWidget.tsx`
    — threads data only.
  - **Registry entry**: `src/components/GameBoard/widgetRegistry.ts` — add a
    `WidgetId` (e.g. `"quests"`), a `WIDGET_REGISTRY` entry (label "Quests" or
    "Objectives", a free hotkey — **avoid `q`/`k`/`r`/`l`/`m`/`i`/`c`/`s`/`g`
    which are taken**; verify against `buildHotkeyMap`), `dataGated: true`.
  - **GameBoard wiring**: `src/components/GameBoard/GameBoard.tsx` — add to the
    `renderWidgetContent` switch, the `useMemo` deps array, the `rightGroupOrder`
    tab order, and the `availableWidgets` data-gating `useMemo` (the relationships
    tab appears only when `relationshipsData.length > 0`; mirror that gating).
  - **Top-level threading**: `src/App.tsx` (see `relationshipsData={gameState.relationships ?? null}`
    at ~`:2199`) and `GameStateProvider` (`relationships?: ... | null`,
    default `null`).

- **Use the project theme system.** Read resolved CSS custom properties
  (`--card`, `--card-foreground`, `--muted-foreground`, `--accent`, `--border`,
  etc.) exactly as `RelationshipsPanel` does (ADR-079). `useGenreTheme` is a
  CSS-injection effect, **not** a color accessor — do not call it to fetch colors.
  Fonts via the same display/body family pattern.

- **TS/React + Vitest.** Hand-maintained TS payload types mirror the server
  (`src/types/payloads.ts` header). If a new rich `quests` payload type is added,
  it must mirror the server's projection shape and be documented with a pointer to
  the server source (the convention used by `magic.ts`, `RelationshipEntryPayload`).

## Scope Boundaries

**In scope:**
- A player-facing, dockable **Quests/Objectives panel** that renders, from the
  projected `quests` state: the **quest_log** (titles + status/objective per quest),
  the **quest_anchors** (anchor id, the quest it belongs to, and its beat/location
  resolution if any), and the **active_stakes** (the current stakes string).
- Empty/seeded/populated states: a clean empty state when the spine is unpopulated;
  a populated state once a seeded or narrator-minted quest arrives.
- **Reactive update** on state push — the panel reflects the latest projection as
  `record_quest`/`set_stakes`/the creation seed land server-side and the projection
  re-broadcasts (mirror how `RelationshipsPanel` updates from the `relationships`
  snapshot).
- Registry/widget/GameBoard/App/provider wiring so the tab actually mounts and is
  reachable from production code paths (not just a component that exists in
  isolation), including the data-gating so it appears once the spine is non-empty.
- Component tests + at least one **wiring test** (every test suite needs one): assert
  the panel renders each field, handles empty vs populated, updates reactively, and
  is reachable from GameBoard's render path.

**Out of scope:**
- All server-side work: seed-at-creation (77-1), `record_quest`/`set_stakes` typed
  tools (77-2), promoting `quest_anchors` to `WorldStatePatch` + orbital wiring
  (77-3), one-mechanism cleanup / `apply_world_patch` stripping (77-4). This panel
  consumes their output; it does not implement any of it.
- Defining/seeding the OTEL spans (`quest.*`, `stakes.set`) — those are server
  concerns; this panel is a cosmetic/render surface and does not emit subsystem OTEL
  (per the "Not needed for: cosmetic UI" carve-out in the UI CLAUDE.md). The panel's
  *correctness* is verified by component tests, not OTEL.
- The `active_seeds` content carve-out (sprint 77-6 / ADR 77-7, wry_whimsy
  `seed_tropes` deck) — unrelated content authoring.
- **The rich `quests` projection field itself** — *if* the server lane already ships
  a log+anchors+stakes projection, consume it; **if it does not exist yet, that field
  is a blocking dependency on the server lane, NOT something this UI story invents.**
  Confirm before building (see Technical Guardrails). Do not back-fill a fake shape
  into the thin `Record<string, string>` that exists today.
- Any quest *interaction* (clicking to pin, abandon, re-order, mark complete) — this
  is a read-only objective surface, not a control.

## AC Context

> The story carries **no stored acceptance_criteria or description** (both `null` in
> the sprint YAML, confirmed via `pf sprint story field`). The ACs below are derived
> from ADR-137 §Implementation Stories ("77-6 — Quest/objective panel: Render
> quest_log + quest_anchors + active_stakes from the existing `quests` payload field.
> Player-facing mechanical legibility.") and the epic context. **TEA/Dev should
> confirm these with the SM before RED**, and especially resolve the projection-shape
> dependency (below) first.

- **AC1 — Renders all three spine fields.** The panel displays the **quest_log**
  (each quest's title and its status/objective), the **quest_anchors** (each anchor's
  id, owning quest, and beat/location resolution where present), and the
  **active_stakes** string. *Test:* given a populated projection fixture, the panel
  renders a quest title, an anchor, and the stakes text; assert via `data-testid`
  hooks per the RelationshipsPanel convention.

- **AC2 — Empty and seeded states.** With an empty/unpopulated spine the panel shows
  a clean, theme-consistent empty state (mirror `relationships-empty`: "No objective
  yet…" or similar) and **does not white-screen or throw** on missing/undefined
  fields. With a seeded spine (a single creation-seeded quest + anchor + stakes, the
  minimum every session now starts with per 77-1) it renders that seed. *Test:*
  empty-state branch renders the placeholder and no quest rows; seeded fixture renders
  exactly the seeded entry.

- **AC3 — Reactive update on state push.** When the projected `quests` state changes
  (new quest minted, status updated, anchor added, stakes set/appended), the panel
  re-renders to reflect the latest value without a remount. *Test:* re-render the
  hosting state with an updated projection and assert the new quest/anchor/stakes
  appear and stale ones reconcile (mirror the `GameStateProvider`/`useStateMirror`
  merge tests for `quests`/`relationships`).

- **AC4 — Wired into the GameBoard dock as a data-gated tab.** The panel is reachable
  from production code: registered in `widgetRegistry.ts`, rendered via
  `renderWidgetContent` in `GameBoard.tsx`, threaded from `App.tsx`/`GameStateProvider`,
  and **data-gated** so the tab appears only once the spine is non-empty (mirroring
  relationships' `availableWidgets` gating). *Test (wiring):* the tab mounts and the
  panel is rendered from GameBoard's render path when projected quest data is present;
  it is absent when the spine is empty.

- **AC5 — Theme-consistent and accessible.** Styling reads resolved CSS custom
  properties (ADR-079) so the panel matches the active genre theme; the panel meets
  the Accessibility Requirements below. *Test:* panel root carries the expected
  ARIA role/label and renders within the Folio palette tokens (no hardcoded colors).

**Projection-shape dependency (resolve before RED).** AC1/AC3 cannot be satisfied by
the `Record<string, string>` `quests` field that exists today (it carries only
title→status, no anchors, no stakes). The blocking question for the SM/server lane:
*does 77-1…77-4 ship a richer `quests` projection (a typed payload with log + anchors
+ stakes, analogous to the `RELATIONSHIPS` snapshot)?* If yes, mirror its shape into
a new `payloads.ts` interface and consume it. If no, this story is blocked on that
server projection and should be re-sequenced behind it — do not fabricate the shape.

## Interaction Patterns

- **Where it lives.** A dockable tab in the right-side panel group of `GameBoard`,
  alongside Character / Relationships / Inventory / Map / Location / Knowledge. Add it
  to `rightGroupOrder` in a sensible slot (Objectives reads naturally near the top of
  the spine surfaces — e.g. just after Character, before Relationships — confirm with
  UX/SM). It has a hotkey (a free letter; `q` if available — verify against
  `buildHotkeyMap`, do not collide).
- **Data-gated appearance.** Like Relationships, the tab is `dataGated: true` and
  appears only once the spine is non-empty (a seeded quest arrives at session start,
  so in practice the tab appears almost immediately — but the gating prevents an empty
  tab during chargen / before any projection lands). No tab clutter when there's
  nothing to show.
- **Update on state push.** The panel is a pure render of the projected `quests`
  state; it updates whenever a new projection broadcast arrives (creation seed,
  `record_quest`, `set_stakes`). No polling, no local quest state, no optimistic UI.
- **Empty vs populated.** Empty: a single muted line ("No objective yet — your goal
  and stakes will appear here.") consistent with `relationships-empty`. Populated:
  stakes shown prominently (the "what's at risk right now" line), then the quest log
  as a list (title + status/objective), with anchors associated to their quest
  (anchor id + its beat/location resolution where present). Mechanics-first detail
  (raw anchor ids, beat ids) is legible but need not dominate — follow the ADR-136
  hybrid-disclosure spirit (band/summary by default, raw mechanical detail available)
  if the projection is rich enough to warrant it.
- **Read-only.** No buttons that mutate quests. Expand/collapse for detail is fine
  (RelationshipsPanel uses local `useState` toggles); anything that writes game state
  is out of scope.

## Accessibility Requirements

- **Panel landmark/role.** The panel root carries an appropriate ARIA role and an
  accessible name (e.g. `role="region"` / `aria-label="Quests and objectives"`), so
  it is announced as a distinct region — consistent with the dock-panel convention.
- **Keyboard reachability.** The tab is reachable and switchable via the existing
  hotkey mechanism (`buildHotkeyMap`); the chosen hotkey must not collide with an
  existing one. Expand/collapse controls (if any) are real `<button>` elements with
  `aria-expanded` reflecting state — exactly as `RelationshipsPanel` does its
  header/`Show traits` toggles — and are operable by keyboard.
- **Readable contrast within the genre theme.** All text uses the theme's
  foreground/muted/accent custom properties against the card/paper background
  (ADR-079); do not introduce hardcoded colors that could fail contrast in a dark or
  high-key genre theme. Status/stakes emphasis must not rely on color alone (pair
  color with text/weight) so it remains legible for color-vision-deficient players.
- **Empty state is announced, not silent.** The empty-state placeholder is real text
  content (like `relationships-empty`), so screen-reader users learn the surface
  exists and what it will hold, rather than encountering an empty region.
