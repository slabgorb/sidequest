# Lobby Identity — Genre-Grouped World Picker + Scoped Theming

**Date:** 2026-06-03
**Author:** UX Designer (Adora Belle Dearheart)
**Repo:** `sidequest-ui`
**Status:** Design — pending implementation plan

## Problem

The lobby (`ConnectScreen`) — the menu where a player picks a world and a mode
before entering a game — suffers three issues that share **one root cause:
scope leakage**. The lobby has no identity and no scope discipline.

1. **Flat world list, bad scroll.** `OptionList` renders all 20 worlds as a flat,
   alphabetically-sorted, scrollable radiogroup, with each world's genre buried as
   an italic `hint` suffix. There is no structure; the scroll column is cramped
   (the top row clips above the fold); the genre — the *rule pack* a world rides —
   is an afterthought.

2. **Scope-mixed, orphaned reference links.** `ReferenceLinks` drops a **Rules**
   and a **Lore** link at the bottom of the list. They are different scopes —
   Rules is **pack-scoped** (`/reference/rules/{pack}`), Lore is **world-scoped**
   (`/reference/lore/{pack}/{world}`) — yet they sit together with no indication of
   what they point at. They silently re-target every time the selection changes.
   A player cannot tell that "Rules" means "rules for the world currently
   highlighted."

3. **Lobby chrome inherits the last world's theme.** `App.tsx:543` runs
   `useChromeArchetype(currentGenre)`, which writes `data-archetype` + structural
   CSS variables (fonts, border-radius) onto `document.documentElement` (`<html>`).
   `currentGenre` stays set to the **last world the player entered**, so the lobby
   renders under a stale genre archetype. The menu cosplays whatever world it last
   visited (e.g. Gulliver's `wry_whimsy → parchment` skin paints the whole lobby).

These are the same disease in three places: structure, link scope, and theme scope
all leak because the lobby never asserts "I am the lobby; treat me as the lobby."

## Decisions (confirmed with stakeholder)

- **Grouping model:** sticky genre section headers within a single radiogroup.
  (Not an accordion — half the genres ship only one world, so collapse is fiddly;
  not a two-step genre→world flow — keeps the see-all-worlds-at-once view.)
- **Lobby identity:** stable "house" chrome for the lobby shell; genre flavor is
  **contained to the world-preview card** on the right, scoped off `<html>`.
- **House style:** a **distinct editorial house archetype** — neutral, NOT any of
  the three genre archetypes — so a themed world-card visibly "lights up" against
  the shell (including for the ~5 parchment-genre worlds, which would otherwise be
  indistinguishable from a parchment house).

## Design

### A. Genre-grouped world picker

**Component:** `src/screens/lobby/OptionList.tsx` (extend), consumed by
`src/screens/ConnectScreen.tsx`.

- Add an optional **`groups`** prop to `OptionList`, mutually exclusive with the
  existing flat `items` prop:

  ```ts
  export interface OptionGroup {
    slug: string;        // genre slug
    label: string;       // genre display name (header text)
    rulesHref: string | null; // /reference/rules/{genreSlug}, null if unavailable
    items: OptionItem[]; // worlds in this genre
  }
  ```

  Flat `items` mode is unchanged — `ModePicker` and any genre-only picker caller
  are unaffected. (Consistency: extend the shared component, do not fork it.)

- **One** `role="radiogroup"` spans **all** worlds across all groups, so arrow-key
  navigation flows across genre boundaries exactly as today. Genre headers
  interleave as **non-focusable presentation rows** (`role="presentation"`,
  excluded from the roving-tabindex set). Arrow/Home/End traverse world radios
  only and skip headers. The existing keyboard model in `OptionList.handleKeyDown`
  operates over a flattened list of world items derived from `groups`.

- Each **genre header** is `position: sticky; top: 0` within the scroll container
  (orientation persists while scrolling) and carries the **Rules** link
  (see §B).

- **ConnectScreen** stops flattening. Currently (`:134-151`) it iterates `genres`
  and pushes every world into one array sorted by world label. Instead it builds
  `OptionGroup[]`: one group per genre, groups sorted by genre label, worlds sorted
  by world label within each group. The composite `genreSlug/worldSlug` slug and
  `worldPresence` annotation logic carry over unchanged into per-world items.

- **Auto-scroll the selected world into view** on mount and on selection change, so
  a restored/preselected world is never clipped above the fold.

### B. Rules / Lore relocation — retire the orphan block

- **Rules** (`/reference/rules/{genreSlug}`, pack-scoped) moves onto **each genre
  header**, right-aligned. Scope becomes self-evident: the link sits inside the
  "SPACE OPERA" header, so it is unmistakably Space Opera's rules.
- **Lore** (`/reference/lore/{genreSlug}/{worldSlug}`, world-scoped) moves into the
  **`WorldPreview` card header** (right panel), beside the world title — where the
  world actually lives.
- Remove the standalone `<ReferenceLinks pack world />` at `ConnectScreen:443`.
  **Retire `src/components/ReferenceLinks.tsx`** entirely if it has no other caller
  (dead-code rule); otherwise leave it for its remaining consumer and inline the
  two anchors in their new homes.
- Both remain real `<a target="_blank" rel="noopener noreferrer">` links. Because
  the visible text is just "Rules" / "Lore", each gets an explicit
  `aria-label` — e.g. `"Space Opera rules"`, `"The Aureate Span lore"`.
- Preserve the existing disabled treatment when an href is unavailable (no pack /
  no world selected) — render a non-interactive, dimmed label, as
  `ReferenceLinks` does today.

### C. Scoped theming — house shell, themed card

**Files:** `src/hooks/useChromeArchetype.ts`, `src/App.tsx`,
`src/screens/lobby/WorldPreview.tsx`.

- **Add a `house` archetype** to `ChromeArchetype` and `ARCHETYPE_PROPERTIES`: a
  neutral editorial identity, distinct from `parchment` / `terminal` / `rugged`.
  Proposed direction (final visual tuned in implementation): a humanist serif body
  with a restrained display face, neutral ink-on-cream, square-ish corners — a
  "library / card-catalog" feel that reads as *the menu*, not a world.
  `getArchetypeForGenre(genre)` stays **fail-loud** for genre slugs (unchanged);
  `house` is a separate, explicitly-selected identity and is never thrown.

- **Lobby root renders `house`.** While `ConnectScreen` is the active phase, the
  root `<html>` archetype must be `house`, not the stale `currentGenre`. The leak
  at `App.tsx:543` (`useChromeArchetype(currentGenre)`) must not paint a genre on
  the lobby. Implementation chooses the seam — e.g. drive the root archetype to
  `house` during the connect phase, reverting to `currentGenre` once a game is
  entered. (In-game chrome on `<html>` is correct and unchanged — see Out of
  Scope.)

- **Add a scoped applier.** Today `useChromeArchetype` writes to
  `document.documentElement` only. Add a variant that applies an archetype
  (`data-archetype` attribute + the `ARCHETYPE_PROPERTIES` CSS variables) to a
  **caller-supplied element ref** instead of the document root, with the same
  cleanup-on-change semantics (remove previously-set keys). The `[data-archetype]`
  CSS selectors already resolve against any ancestor element, so scoping the
  attribute to a subtree confines the genre fonts/treatment to that subtree.

- **WorldPreview card adopts the selected world's genre archetype**, scoped to the
  card's wrapper element via the new applier. The lobby shell stays `house`; the
  card becomes a contained, intentional "taste of the genre."

- **Net:** the lobby shell never inherits a world theme again; genre flavor lives
  only inside the preview card.

### Accessibility

- Single radiogroup; roving tabindex over world radios only; genre headers are
  `role="presentation"` and skipped by keyboard nav but remain visible.
- Sticky headers get a `z-index`; world radios get `scroll-margin-top` equal to the
  sticky-header height so auto-scroll-into-view clears the header and the
  focus-visible ring is never occluded by an overlapping header.
- Rules/Lore are tab-reachable `<a>` links with descriptive `aria-label`s.
- Color contrast of the house chrome and of header/link text meets WCAG 2.1 AA
  (4.5:1 body, 3:1 large text). Verify the house ink-on-cream pairing explicitly.

### Scrollbar / layout

- Give the list real vertical height. The current `min-h-0 overflow-y-auto` inside
  a cramped flex parent is why the top row clips; the scroll viewport needs enough
  height that the list breathes. Sticky headers + auto-scroll-to-selected do the
  real orientation work.
- Style the scrollbar to the house chrome (thin, house accent) rather than relying
  on the OS default. (`[scrollbar-width:thin]` is already present; add house-tuned
  thumb/track color via the established theming variables.)

## Out of Scope (YAGNI)

- No accordion / collapse behavior.
- No genre color-coding system or per-genre accent palette in the list.
- No search / filter (20 worlds with section headers does not need it).
- **No change to in-game chrome.** Applying the genre archetype to `<html>` *during
  actual play* is correct — the player is in the world then. Only the lobby phase
  changes.

## Components Touched

| File | Change |
|------|--------|
| `src/screens/lobby/OptionList.tsx` | Add optional `groups` mode (sticky genre headers, single radiogroup, header Rules link); flat mode unchanged |
| `src/screens/ConnectScreen.tsx` | Build `OptionGroup[]` instead of a flat sorted list; remove standalone `ReferenceLinks`; pass grouped data |
| `src/screens/lobby/WorldPreview.tsx` | Host the world-scoped **Lore** link in the card header; apply the selected world's genre archetype scoped to the card wrapper |
| `src/hooks/useChromeArchetype.ts` | Add `house` archetype; add a ref-scoped applier variant |
| `src/App.tsx` | Render `house` on `<html>` during the connect/lobby phase instead of stale `currentGenre` |
| `src/components/ReferenceLinks.tsx` | Retire if no remaining caller; else split its two links to their new homes |

## Testing

- **Grouped rendering:** worlds render under the correct genre headers, groups and
  worlds sorted as specified.
- **Keyboard nav:** a single radiogroup; arrow keys move across genre boundaries
  and skip headers; Home/End jump to first/last world; roving tabindex correct.
- **Link relocation:** Rules renders on each genre header with the pack href +
  `aria-label`; Lore renders in the preview card with the world href + `aria-label`;
  the old standalone `ReferenceLinks` block is gone.
- **Scoped theming (key assertion):** while the lobby is active,
  `document.documentElement` carries the **`house`** `data-archetype`, and the
  **selected world's** genre `data-archetype` is present on the **preview-card
  element** — NOT on `document.documentElement`.
- **No leak on return:** after entering a world and returning to the lobby, the
  root archetype is `house`, not the entered genre.
- **Auto-scroll:** a preselected/restored world is scrolled into view (not clipped).
- **Wiring test:** the grouped `OptionList` is actually rendered by `ConnectScreen`
  in production (not just unit-tested in isolation), per the project's
  every-suite-needs-a-wiring-test rule.

## Open Items / Notes

- Final visual tuning of the `house` archetype (exact typefaces, ink/cream values,
  scrollbar thumb color) is an implementation detail within the "distinct editorial"
  direction; it does not change the architecture above.
- `useGenreTheme(messages, connected)` (App.tsx:540) drives genre **palette** CSS
  from server `theme_css` events and is a separate path from `useChromeArchetype`
  (structural fonts/borders). This design scopes the **archetype**; if palette also
  leaks into the lobby shell, the same "house in lobby, genre in card" principle
  applies — flag for the implementer to verify during the theming work.
