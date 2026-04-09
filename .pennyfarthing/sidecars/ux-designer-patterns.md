## UX Designer Patterns

### How to work with Keith
- **Art background + 40 years of tabletop RPG + frontend/React expertise + full product perspective.** Keith is not a UX novice — he has deep domain conviction. When he gives UX feedback, it comes from someone who's designed physical character sheets, dungeon maps, and digital interfaces for decades. Trust the judgment. Don't explain basic UX principles to him.
- **Procedural world generation lineage (30+ years).** Visual design decisions on map rendering, character panels, and information density should respect the domain patterns he's iterated on before. SideQuest UI is the latest in a long line — not a blank-slate exploration.
- **Dictation artifacts** ("axiom" → "axum", "SERG" → "serde", "playlist" → "playtest", "dinkus" and "drop cap" are actual terms he uses precisely). Parse for intent.
- **Keith wants to be surprised by narrative content.** Don't show him spoilers in mockups or design reviews. Only `mutant_wasteland/flickering_reach` is fully spoilable. For every other genre, present "here's the panel structure" without revealing the lore content it will display.

### Core UX principles for SideQuest
- **Information scent over metaphor.** The book conceit failed because it forced the player to ask the narrator for their own stats — the information scent was wrong. Rule: if a player has to round-trip to the narrator to see persistent state (HP, inventory, conditions, location), the design has failed. Persistent state goes on persistent surfaces.
- **Current Turn Focus + Scrollable History.** Narrative renders as the current turn at full opacity + a scrollable dimmed history above. Not continuous scroll (too noisy). Not paginated storybook (book-conceit artifact). The current turn always lands at a predictable visual anchor.
- **Themed chrome, not themed interaction patterns.** Genre theming drives colors, fonts, border treatments, backgrounds — not the navigation model. The tab strip, panel layout, input bar, and interaction gestures are constant across genres. Players learn the app once, not per-genre.
- **Three chrome archetypes driven by `theme.yaml`:**
  - **`parchment`** — low_fantasy, victoria, spaghetti_western, caverns_and_claudes
  - **`terminal`** — neon_dystopia, space_opera, mutant_wasteland, star_chamber
  - **`rugged`** — road_warrior, pulp_noir, elemental_harmony
- **Existing infrastructure:** `theme.yaml` + `client_theme.css` per genre pack, injected via the `useGenreTheme` hook. CSS vars (`--primary`, `--surface`, `--accent`, etc.) bridge to Tailwind tokens automatically. Wire up existing hooks — don't rebuild the theming system.
- **Gap:** only narrative elements get genre CSS classes — panels use generic Tailwind. When adding genre-specific treatments, wire the existing CSS vars into panel chrome. Don't build a parallel theming system.

### Character panel structure (settled direction)
- **Persistent docked sidebar** (CharacterPanel) replaces the retired `OverlayManager` modal pattern. Always visible on desktop, expandable on tablet, bottom-sheet on mobile.
- **Four tabs on the character side:** Status (portrait, HP, stats, conditions, abilities) / Gear (inventory, equipped, gold) / Journal (merged knowledge + journal with category filters) / Map (automapper or location list).
- **Right-side dock order (matches `GameBoard.tsx::rightGroupOrder`):** Character → Inventory → Map → Knowledge → Journal → Gallery → Audio. Character is always the initial active tab on fresh session load, never Audio (that bug was real — `api.addPanel` activates the last-added panel by default).
- **Narrative panel is the left column**, focused on mount via `narrative.focus()`.

### Design references (what Keith has cited as right directions)
- **Mothership RPG** — dense single-page layout, stress track always visible, info density over whitespace.
- **Blades in the Dark** — clocks inline with prose, compact stress/trauma/harm strips, playbook-as-identity affordance.
- **Vaesen Revised (2025)** — four-tab sheet (Main/Actions/Inventory/Log), conditions rendered as glyphs, strong thematic treatment without skeumorphism.

### Responsive breakpoints
- **Desktop ≥1200px:** docked right sidebar ~300px wide, always visible. This is the primary target for playtests.
- **Tablet 768–1199px:** collapsed icon strip on the right, click to expand a drawer.
- **Mobile <768px:** bottom sheet, swipe up to reveal. De-prioritized target — playtests don't run on phones.

### Verification patterns
- **Screenshots in `/Users/keithavery/Projects/sq-playtest-screenshots/`** are the canonical visual evidence for UX feedback. When Keith references a screenshot by filename in the pingpong, fetch it and describe what's actually rendered before proposing changes.
- **Pingpong cadence during playtests: every 2-3 minutes.** New `open` bugs from OQ-1 often include UX observations filed by Alex Kamal (the OQ-1 UX persona). Read the pingpong before any design work mid-playtest.
- **Stale evidence check.** Screenshots from earlier sessions may predate recent UI changes. Before proposing a fix, verify the bug still reproduces on the current branch. Example from 2026-04-09: the Dockview tab-order drift screenshots predated the Lore → Knowledge collapse, so part of the reported drift was stale evidence rather than a real regression.

### Wiring patterns UX should enforce
- **"Wire X into Y" means the full data pipeline**, not "component accepts props." UX design specs for panel work should explicitly name the data source (WebSocket message type, provider hook, selector function), the intermediate layers it passes through, and the final rendered element. Spec ACs that stop at "component accepts props" cause half-wired features every time.
- **Persistent state must survive reconnect.** Any UX element that shows persistent state (stats, inventory, location, knowledge) needs a reconnect-replay path — when the player reopens the tab, the panel must repopulate. The 2026-04-09 "reconnect narrative is blank" bug was exactly this pattern at the narrative layer.
- **Every panel gets a non-empty empty state.** `MapWidget`'s "No map data yet — the world map will populate as you explore" is the reference. A blank panel is a UX failure.

### Git / process patterns
- **Gitflow on every subrepo.** `sidequest-ui` targets `develop`, not `main`. Check `repos.yaml` before any git op.
- **Branch before editing.** `git checkout -b feat/description` before touching files.
- **Screenshots are user-generated evidence.** When Keith uploads a screenshot path, use the Read tool to view it directly — don't try to infer what's in it from the filename.
