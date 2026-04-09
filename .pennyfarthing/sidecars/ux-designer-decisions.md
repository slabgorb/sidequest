## UX Designer Decisions

### Major UI direction (settled 2026-04-05 — don't revisit)
- **Book conceit is retired.** The narrative-as-interface with modal overlays for character info created too much friction — having to ask the narrator for your own state is like asking the DM to see your character sheet every turn. Information-scent failure.
- **Persistent docked sidebar** (`CharacterPanel`) replaces the `OverlayManager` modal pattern.
- **Current Turn Focus + Scrollable History** for narrative — not continuous scroll, not paginated storybook.
- **Themed chrome, not themed interaction patterns.** Three archetypes driven by `theme.yaml`:
  - `parchment` — low_fantasy, victoria, spaghetti_western, caverns_and_claudes
  - `terminal` — neon_dystopia, space_opera, mutant_wasteland, star_chamber
  - `rugged` — road_warrior, pulp_noir, elemental_harmony

### Character panel structure (settled)
- **Four tabs:** Status (portrait, HP, stats, conditions, abilities) / Gear (inventory, equipped, gold) / Journal (merged knowledge + journal with category filters) / Map (automapper or location list).
- **Backstory is NOT under the Character tab** anymore — it's absorbed into Knowledge (commit `d10a2df`, later reverted to drop backstory there entirely and retire the Lore tab per commit `4b9dad4`). Lore tab is gone. Knowledge is the winner for "reference-y reading between turns."
- **Inventory is its own top-level tab**, not a Character subtab. Removed as part of the book-conceit retirement — was duplicating the top-level Inventory panel.

### Right-side dock layout (settled)
- **Order:** Character → Inventory → Map → Knowledge → Journal → Gallery → Audio
- **Initial active tab on mount:** Character (not Audio — that was a bug from `api.addPanel` auto-activating the last-added panel; fixed 2026-04-09 via explicit `api.setActivePanel(rightFirst)` + `narrative.focus()`)
- **`key={currentGenre}` on the GameBoard mount** forces React to remount dockview on genre switch, preventing tab-order drift from mid-session drag-and-drop.

### No skeumorphism (settled — do not revisit)
- No Roman numeral turn counters (book artifact)
- No scroll-to-ask-for-own-stats (book artifact)
- No paginated storybook (book artifact)
- No manuscript-page framing on panels
- No illuminated PNG drop caps (CSS-based now)
- No dinkus PNG scene breaks (CSS-based now)
- Usability over vibes, every time

### Responsive breakpoints (settled)
- **Desktop ≥1200px:** docked right sidebar ~300px wide, always visible. Primary playtest target.
- **Tablet 768–1199px:** collapsed icon strip, click to expand drawer.
- **Mobile <768px:** bottom sheet, swipe up. De-prioritized — playtests don't run on phones.

### Narrative rendering (settled)
- **Current turn at full opacity + scrollable history above at reduced opacity** (`opacity-40` with `border-b-2 border-border/50` separator).
- **NarrationScroll skips the trailing separator** when finding the history/current split, so a freshly-completed turn stays at full opacity until the NEXT turn begins. Fixed 2026-04-09 via PARTY_STATUS protocol refactor.
- **World facts strip** ("WORLD LEARNED THIS TURN") renders as an `<aside>` at the bottom of each turn with primary-color header and `border-t-2 border-[var(--primary)]/30` visual break. Uses `text-sm text-muted-foreground` body, not `text-xs`.

### Information density references (settled)
- **Mothership RPG** — dense single-page, stress track always visible
- **Blades in the Dark** — clocks inline with prose, compact stress/trauma/harm
- **Vaesen Revised (2025)** — four-tab sheet, conditions as glyphs, strong thematic treatment without skeumorphism

### Dockview technical decisions (settled 2026-04-09)
- **No layout persistence via localStorage.** GameBoard does not call `api.toJSON`/`fromJSON`. The canonical `rightGroupOrder` runs fresh on every mount. Keeps tab order deterministic across sessions without a stale-state escape hatch.
- **No "reset layout" control** — unnecessary because nothing persists. The first reload IS a reset.
- **No per-genre canonical layouts** — one global default for all genres. Revisit only if real drift shows up in a future playtest.

### Genre theming infrastructure (settled — wire it up, don't rebuild)
- **Per-genre `theme.yaml` + `client_theme.css`** in each genre pack, injected via `useGenreTheme` hook on session connect.
- **CSS vars bridge to Tailwind automatically:** `--primary`, `--surface`, `--accent`, `--muted-foreground`, etc. Tailwind tokens (`bg-background`, `text-primary`) resolve to these at runtime.
- **Gap to close:** panel chrome uses generic Tailwind classes, not genre CSS vars. When adding theming, wire existing vars — don't build a parallel system.

### Asset decisions (settled)
- **Screenshots canonical location:** `/Users/keithavery/Projects/sq-playtest-screenshots/`
- **Images load via `ImageBusProvider`** consuming `MessageType.IMAGE` from the messages array
- **Portraits NOT duplicated in CharacterState** — portrait URLs come from genre pack manifests, not from protocol state
- **Gallery thumbnails clickable** — clicking opens a lightbox overlay

### Product-level decisions that shape UX work
- **Narrative consistency is the #1 product goal.** Every UX decision should support the narrator's ability to tell a consistent story. Persistent visible state → fewer "what's my HP again" narrator interruptions → fewer consistency breaks.
- **Spoiler protection.** Only `mutant_wasteland/flickering_reach` is fully spoilable. For every other genre, Keith wants to discover content in play. Don't show him lore/faction/plot content in design reviews.
- **Keith owns mechanics/crunch. World Builder has creative freedom on flavor/lore/story/NPCs/plot hooks.** UX specs that constrain the narrator's creative range should be raised for his review; pure visual/interaction specs don't need his approval.

### Process decisions
- **Skip architect spec checks for SideQuest.** Personal project — streamlined RED → GREEN → VERIFY → REVIEW → FINISH. UX designer participates in design phases, not spec-check ceremony.
- **Pingpong file is canonical during playtests.** `/Users/keithavery/Projects/sq-playtest-pingpong.md` — read every 2-3 minutes. UX bugs filed by "Alex Kamal" (the OQ-1 UX persona) come through this channel.

### Reference locations
- **Original Python SideQuest UI:** `~/ArchivedProjects/sq-1` — source of truth when porting interaction patterns
- **Screenshots:** `/Users/keithavery/Projects/sq-playtest-screenshots/`
- **Ping-pong:** `/Users/keithavery/Projects/sq-playtest-pingpong.md`
- **Genre packs (theme.yaml source):** `sidequest-content/genre_packs/{genre}/theme.yaml` and `client_theme.css`
- **Dockview docs:** `node_modules/dockview-core/dist/esm/dockview/dockviewComponent.d.ts` — check the type definitions before writing new dockview code

### Hardware context
- **MacBook Pro M3 Max 128GB + external 27" P27h-20 (2560x1440).** The external monitor is the primary playtest display. Design for a 2560x1440 window, not a full 5120x1440 dual-monitor layout. Keith also uses the built-in 16" (3456x2234) as a secondary.
