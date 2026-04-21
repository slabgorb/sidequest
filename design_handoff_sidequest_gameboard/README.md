# Handoff: Sidequest AI DM — GameBoard Surface

## Overview

A redesign of the main **GameBoard** for Sidequest (an AI-run tabletop RPG). The
player is in an ongoing narrative session; the DM generates prose, calls for
rolls, runs combat, tracks world state. This surface is where the player lives
for 90% of the session.

The design is pitched as a Victorian/gothic **parchment-and-ink** aesthetic:
aged paper backgrounds, oxblood accents, serif typography, hand-drawn feel.
Narration is the hero — everything else is chrome that recedes.

The handoff covers:

1. **Connect screen** — session picker / "answer the summons"
2. **Character creation** — guided Victorian dossier intake
3. **GameBoard** in five layout variants:
   - **Codex** — classic single-column manuscript
   - **Folio** — two-page spread (narration left, world right)
   - **Scriptorium** — tabbed panel system
   - **Margins** — narration center, collapsible edge rails
   - **DM Screen** — three-column dossier / narration / world + bottom status rail ★ default
5. **Combat side-drawer** — turn order, beats, dice integration
6. **3D dice overlay** — physical-feeling roll modal
7. **Tweaks panel** — live controls for layout, typography, density, combat HUD

## About the Design Files

The files in `prototype/` are a **design reference** — a standalone HTML +
React-via-Babel prototype showing intended look, layout, interaction, and
typographic hierarchy. They are **not** production code to copy directly.

Your job is to **recreate these designs in the Sidequest codebase's existing
environment** using its established component library, state management, and
build pipeline. Match the visual/interaction intent precisely; use the
codebase's patterns for structure.

## Fidelity

**High fidelity.** Colors, typography, spacing, interaction states, and
content are final. Recreate pixel-perfectly:

- Exact hex values provided (see **Design Tokens**)
- Exact font families (Google Fonts: *IM Fell English SC*, *IM Fell English*,
  *Libre Baskerville*, *Libre Caslon Text*, *JetBrains Mono*)
- Exact spacing, border styles (most dividers are `1px dashed var(--ink-ghost)`),
  and the specific "paper texture" feel documented below

Microcopy (status strings, tab labels, placeholder text) is intentional and
should ship as-is unless product gives new strings.

---

## Screens / Views

### 1. Connect screen

**Purpose:** Player arrives, picks an in-progress campaign or starts a new one.

**Layout:** Centered card on full-bleed parchment background.
- Card: max-width 540px, centered vertically
- Title plate: `font-display`, all caps, oxblood, letter-spacing 0.2em
- Body copy in Libre Baskerville
- Campaign list: each row = portrait + name + last-played date + resume button
- Primary CTA "Begin a new tale" as ornamented button

**Components:**
- `PaperBackground` — the textured paper base (used on every screen)
- `TitlePlate` — display-font heading with decorative rules above/below
- `CampaignRow` — thumbnail + meta + resume

### 2. Character Creation

**Purpose:** Build a PC. Guided, Victorian dossier-intake feel.

**Layout:** Two columns.
- **Left (360px):** Dossier preview that builds live as you answer — portrait
  placeholder, name, class, stats as they're filled
- **Right (fluid):** Step-by-step form. One question at a time, large serif
  input, advance via Enter or "Next" button at bottom

**Steps:** Name → Background → Class → Stat distribution → Starting gear →
Review.

### 3. GameBoard — DM Screen layout (default)

**Purpose:** The active-session surface. Default layout.

**Layout:** CSS grid, three columns + bottom rail.
```
grid-template-columns: 300px 1fr 340px;
grid-template-rows: 1fr 36px;
```
- **Dossier (left, 300px):** PC portrait, name/level/class, Vigor/Sanity bars,
  afflictions, purse, companions. Scrollable independently.
- **Narration (center, fluid):** Header with chapter title + scene meta;
  scrollable narration body. The **hero** of the surface.
- **World (right, 340px):** Tabbed panel — Map / Know(ledge) / Gear (inventory)
  / NPCs / Log (facts). Tabs can show a `pip` indicator when unread.
- **Bottom rail (full-width, 36px):** System status dots (Narrator · Audio ·
  Watcher) on the left; action buttons (Save, Recap, Scroll back) on the right.

**Components (with exact values):**

| Component | Notes |
|---|---|
| `.dm-screen` | `display: grid`, fills viewport minus top chrome |
| `.dm-dossier` | 1.2rem 1.1rem padding; right border `1px solid var(--paper-edge)`; gradient bg `rgba(255,250,235,0.4) → rgba(232,220,190,0.3)` |
| `.dm-narr` | radial gradient highlight at top; header 0.9rem 2rem padding, 1px border-bottom |
| `.dm-narr-head h1` | `font-display`, 1.15rem, uppercase, letter-spacing 0.14em, color `--accent-ink` |
| `.dm-narr-body` | 1.6rem 2.2rem padding, `overflow-y: auto` |
| `.dm-world` | mirror of dossier column, left border |
| `.dm-world-tabs button` | `font-display`, 0.66rem, uppercase, letter-spacing 0.14em; active state `color: var(--accent); background: rgba(255,250,235,0.5)` |
| `.dm-world-tabs .pip` | 6×6 absolute-positioned dot, `background: var(--accent)`, `box-shadow: 0 0 6px var(--accent-soft)`, top-right 6px |
| `.dm-bottom` | 36px height, gradient bg, `font-display` 0.68rem uppercase |
| `.dm-bottom .pip-ok::before` | `content: '◉'`, color verdigris |
| `.dm-bottom .pip-warn::before` | `content: '◉'`, color accent |
| `.dm-bar-row / .dm-bar-label` | resource bar with label row + bar |
| `.dm-section` | section header: `font-display` 0.62rem, uppercase, letter-spacing 0.2em, color `--ink-mute`, 1px ink-ghost underline |
| `.dm-status` | italicized affliction line, prefixed by `◈` in accent color, dashed bottom border |
| `.dm-fact` | world-fact row with title + muted caption, dashed bottom border, optional `new-badge` (0.6rem, accent bordered pill) |

### 4. GameBoard — Codex layout

Single column narration, max-width 780px, centered on page. Character/map/etc
live in an off-canvas right drawer invoked by edge tabs. Use when player wants
maximum text focus.

### 5. GameBoard — Folio layout

Two pages side-by-side like an open book. Left page: narration. Right page:
contextual — map when moving, confrontation when in combat, NPC portrait when
speaking to someone. Divider styled as a book's gutter.

### 6. GameBoard — Scriptorium layout

Closest to current Sidequest. Draggable/tabbed panels. Narration pinned
center-top; other surfaces dockable.

### 7. GameBoard — Margins layout

Narration center-stage (780px). Thin icon rails on both edges (~48px) that
expand on hover/click into full panels.

### 8. Combat side-drawer

**Trigger:** any message carrying `confrontation` state.

**Position:** slides in from the right, width 400px, overlays (not pushes)
main content. Dimmed background underneath at 30% opacity.

**Content:**
- **Header:** confrontation title ("Skirmish at Ashgate Study"), danger meter
  with threshold markers (low / med / high).
- **Turn order:** vertical list, each actor = portrait + name + HP pip +
  initiative number. Active actor has oxblood left-border + paper-deep bg.
- **Beats:** recent combat events as brief bulleted prose lines ("Mrs. Ives
  falters — her flask strikes the rug."), newest at top, fade-in animation.
- **Dice tray button:** at bottom, "Roll" with d20 glyph — opens 3D dice overlay.

### 9. 3D dice overlay

Full-screen modal, paper-bg backdrop at 85% opacity. Large d20 (or requested
die) with physical tumble animation (~800ms), settles showing result face.
Result number in `font-display`, then caption "DC 15 — success" below. Press
any key / click to dismiss.

### 10. Tweaks panel

Floating panel, bottom-right, title "Tweaks". Controls:
- **Layout:** Codex / Folio / Scriptorium / Margins / DM Screen (radio)
- **Narration style:** Turn cards / Continuous scroll / Focus mode (radio)
- **Typography:** Body font toggle Libre Baskerville ⇄ IM Fell English
- **Density:** slider 0.85 → 1.25 (scales `--density`)
- **Combat HUD variant:** (future — placeholder radio)

All tweaks persist via the editor's `__edit_mode_set_keys` message (pattern is
specific to the prototype host; in the real app, use standard localStorage).

---

## Interactions & Behavior

- **Tab switch** (world column): instant swap. If the tab had a `pip` (unread),
  the pip clears on view.
- **Narration auto-scroll:** when a new DM message arrives and the user is
  already near the bottom, auto-scroll smoothly. If the user has scrolled up,
  don't hijack — show a small "↓ new" chip instead.
- **Resource bars:** animate width changes with `transition: width 400ms ease`.
- **Sanity drops:** a damage flash briefly tints the dossier column with a
  desaturated red overlay at 12% opacity, 600ms.
- **Combat drawer open/close:** slide transform, 280ms, ease-out.
- **Dice overlay:** tumble 800ms, settle 200ms (scale 1.05 → 1.0).
- **Hover states on buttons:** color lightens to `--accent-ink` for `.dm-bottom
  button`; rest is subtle (no ornamental hover effects).

## State Management

The DM Screen needs:
- `currentLayout: 'dmscreen' | 'codex' | 'folio' | 'scriptorium' | 'margins'`
- `narrationMode: 'turncards' | 'scroll' | 'focus'`
- `worldTab: 'map' | 'knowledge' | 'inventory' | 'npcs' | 'log'`
- `unreadTabs: Set<WorldTabId>` — driven by server events (new fact logged →
  `knowledge.unread = true`)
- `combatOpen: boolean` + `combatData: Confrontation | null`
- `diceOverlay: { die, result, dc, outcome } | null`
- Standard session state: `messages`, `player`, `party`, `map`, `inventory`,
  `knowledge`

Data fetching: messages should stream (the DM is generating token-by-token).
In prototype this is faked from `mock.js`.

## Design Tokens

All tokens live on `:root` in `prototype/styles.css`. Reproduced here:

### Paper / ink

```
--paper:          #efe6d2
--paper-warm:     #e8dcbe
--paper-deep:     #d9c9a4
--paper-edge:     #b59e73
--paper-shadow:   rgba(60, 38, 18, 0.14)

--ink:            #22160c
--ink-soft:       #3b2a1a
--ink-mute:       #6b5a43
--ink-faint:      #9a8a6e
--ink-ghost:      #b8a98b
```

### Accent (oxblood)

```
--accent:         #7a1f22
--accent-soft:    #9c3a3a
--accent-bright:  #b84a3a
--accent-ink:     #4a1014
```

### Secondary

```
--verdigris:      #3d6958
--brass:          #8a6a2a
--gold:           #b08433
```

### Sizing

```
--rail-w:         340px
--page-max:       780px
```

### Typography

```
--font-display:   'IM Fell English SC', 'Libre Caslon Text', 'Baskerville', serif
--font-serif:     'Libre Baskerville', 'Baskerville', Georgia, serif
--font-hand:      'IM Fell English', 'Libre Caslon Text', serif
--font-ui:        'Libre Caslon Text', 'Libre Baskerville', serif
--font-mono:      'JetBrains Mono', ui-monospace, monospace
```

Google Fonts import:
```
https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Libre+Caslon+Text:ital,wght@0,400;0,700;1,400&display=swap
```

### Dashed divider (used constantly)

```
border-bottom: 1px dashed var(--ink-ghost);
```

## Assets

The prototype uses **no external images** — portraits are SVG monograms drawn
in `Portrait` component (`components.jsx` line 7). The map is vector SVG
generated from data (`MapSvg`, line 264). Any ornament is CSS/SVG.

In production, when you have real art:

- **PC portraits:** AI-generated illustrative style, aged photograph feel
  (sepia wash, slight vignette). Render in a `.portrait-frame` with an aged
  gilt border — see prototype `.portrait-frame` CSS.
- **Map:** keep SVG — designer is generating per-scene tactical maps as SVG
  from room data. The `MapSvg` component contract (data shape: `rooms[]`,
  `edges[]`, `markers[]`) should be preserved.
- **Ornaments:** fleurons between sections. Use SVG; the prototype uses Unicode
  `◈` and `◉` as placeholders which are acceptable in shipping if an
  illustrator doesn't produce ornaments.

## Files

In `prototype/`:

| File | Purpose |
|---|---|
| `Sidequest GameBoard.html` | Entry point — loads React+Babel, styles, mock data, components, app |
| `styles.css` | All CSS — tokens, layouts, components. `.dm-*` classes are the DM Screen. |
| `mock.js` | `window.MOCK` — sample Gaslamp Hollow session (player, party, messages, map, inventory, knowledge, confrontation) |
| `components.jsx` | All reusable components: `Portrait`, `Bar`, `NarrationTurnCards/Scroll/Focus`, `CharacterCard`, `MapSvg`, `Inventory`, `Knowledge`, `CombatDrawer`, `DiceOverlay`, `InputBar` |
| `app.jsx` | Five layout components (`CodexLayout`, `FolioLayout`, `ScriptoriumLayout`, `MarginsLayout`, **`DMScreenLayout`**) + `GameBoard` + `App` + Tweaks wiring |

**Key source locations to reference:**

- `DMScreenLayout` — `app.jsx`, search for `function DMScreenLayout`
- DM Screen CSS — `styles.css`, search for `.dm-screen`
- Narration renderers — `components.jsx` lines 68, 126, 159
- Combat drawer — `components.jsx` line 413
- Dice overlay — `components.jsx` line 512
- Mock data shape — `mock.js`

## Implementation Order (suggested)

1. Port tokens to the codebase's theme system (first — everything depends on
   these).
2. Load the four Google Fonts families.
3. Build the `DMScreenLayout` grid scaffold with stub panels.
4. Wire narration column to real message stream.
5. Build dossier column bound to PC state.
6. Build world column tabs (each tab is an existing or new feature).
7. Bottom rail — system status + actions.
8. Combat drawer overlay.
9. Dice overlay.
10. Tweaks panel (can ship behind a dev flag initially).
11. Three remaining layouts (Codex, Folio, Scriptorium, Margins) as follow-up.
