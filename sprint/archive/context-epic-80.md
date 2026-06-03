# Epic 80: Lobby Experience — World Picker & Chrome Scoping

## Overview

The lobby (`ConnectScreen`) — the menu where a player picks a world and a mode
before entering a game — has no identity of its own and leaks scope three ways
from a single root cause. This epic gives the lobby a stable identity: a
genre-grouped world picker, scope-clear Rules/Lore reference links, and a
neutral "house" chrome that no longer inherits the last-entered world's genre
theme. All work is `sidequest-ui` only — no engine, content, or daemon changes.

**Priority:** P2
**Repo:** sidequest-ui
**Stories:** 1 (5 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Design spec** (`docs/superpowers/specs/2026-06-03-lobby-identity-grouped-picker-design.md`) | Problem (3 leaks), Decisions, Design §A grouped picker / §B link relocation / §C scoped theming, Accessibility, Out of Scope |
| **Implementation plan** (`docs/superpowers/plans/2026-06-03-lobby-identity-grouped-picker.md`) | File structure, locked type/API decisions, Phase 1 (Tasks 1–4) theming, Phase 2 (Tasks 5–9) picker |
| **ADR-079** (`docs/adr/`) | Genre Theme System Unification — archetype CSS variables, `[data-archetype]` selector model |

## Background

### The one root cause: scope leakage

The lobby never asserts "I am the lobby; treat me as the lobby." Three visible
symptoms share that disease:

1. **Flat world list, bad scroll.** `OptionList` renders all 20 worlds as a flat,
   alphabetically-sorted radiogroup with each world's genre buried as an italic
   `hint` suffix. No structure; the scroll column is cramped (top row clips above
   the fold); the genre — the *rule pack* a world rides — is an afterthought.

2. **Scope-mixed, orphaned reference links.** `ReferenceLinks` drops a **Rules**
   link (pack-scoped, `/reference/rules/{pack}`) and a **Lore** link (world-scoped,
   `/reference/lore/{pack}/{world}`) together at the bottom of the list with no cue
   to what they point at. They silently re-target every time the selection changes.

3. **Lobby chrome inherits the last world's theme.** `App.tsx` runs
   `useChromeArchetype(currentGenre)`, writing `data-archetype` + structural CSS
   variables onto `<html>`. `currentGenre` stays set to the **last world entered**,
   so the lobby renders under a stale genre archetype — the menu cosplays whatever
   world it last visited.

### Why this matters for the table

The lobby is the first surface every player sees — it sets the tone before a single
narration beat. A lobby that wears the last world's skin reads as a bug to a career
GM (Keith) and confuses the genre→world mental model the picker is supposed to
teach. Clean genre identity in the picker also serves the mechanics-first players
(Sebastien, Jade) who navigate by genre/rule-pack, and the grouped + keyboard-clean
list serves inclusive pacing (Alex) by making the full set legible without a
cramped scroll.

## Technical Architecture

### Three fixes, one principle: "house in the shell, genre in the card"

- **House chrome archetype.** A new neutral `house` member of `ChromeArchetype`
  (alongside `parchment`/`terminal`/`rugged`) — a distinct editorial identity
  (humanist serif body, neutral ink-on-cream, `3px` radius) so a themed
  world-preview card visibly stands apart from the shell. `getArchetypeForGenre`
  stays fail-loud for genre slugs; `house` is explicitly selected, never thrown.

- **Scoped theming seam.** The current `useChromeArchetype` only writes to
  `document.documentElement`. The work factors a pure `applyArchetypeToElement`
  helper, makes the root hook archetype-driven (`useChromeArchetype(archetype)`),
  and adds `useScopedChromeArchetype(ref, archetype)` to confine an archetype to a
  subtree. `App` drives `house` on `<html>` during the `connect` phase (via an
  exported pure `resolveRootArchetype(phase, currentGenre)` resolver) and the
  genre archetype during `creation`/`game`. The preview card adopts the selected
  world's genre archetype scoped to its own wrapper.

- **Genre-grouped picker.** `OptionList` gains an optional `groups: OptionGroup[]`
  mode (mutually exclusive with flat `items`): sticky `role="presentation"` genre
  headers over a single `role="radiogroup"` spanning all worlds, with roving
  tabindex and arrow/Home/End nav over world radios only (headers skipped), plus
  auto-scroll-the-selection-into-view. `ConnectScreen` builds `OptionGroup[]`
  instead of a flat list. **Rules** moves onto each genre header (pack-scoped);
  **Lore** moves into the `WorldPreview` card header (world-scoped); the standalone
  lobby `ReferenceLinks` block is removed.

### Key files

| File | Change |
|------|--------|
| `src/hooks/useChromeArchetype.ts` | Add `house`; `applyArchetypeToElement`; archetype-driven root hook; `useScopedChromeArchetype` |
| `src/styles/archetype-chrome.css` | Add neutral `[data-archetype="house"]` block |
| `src/App.tsx` | Exported `resolveRootArchetype`; drive `house` on `<html>` during connect phase |
| `src/screens/lobby/OptionList.tsx` | Optional grouped mode (sticky headers, single radiogroup, header Rules link, auto-scroll) |
| `src/screens/lobby/WorldPreview.tsx` | Scope selected world's archetype to card via ref; host world-scoped Lore link |
| `src/screens/ConnectScreen.tsx` | Build `OptionGroup[]`; remove standalone `ReferenceLinks`; wire `archetype`/`loreHref` to `WorldPreview` |
| `src/components/ReferenceLinks.tsx` | **RETAINED** — still consumed in-game by `GameBoard/widgets/NarrativeWidget.tsx`; only the lobby usage is removed |

### Locked type/API decisions

```ts
export type ChromeArchetype = "parchment" | "terminal" | "rugged" | "house";
export function applyArchetypeToElement(el: HTMLElement, archetype: ChromeArchetype | null, prevKeys: string[]): string[];
export function useChromeArchetype(archetype: ChromeArchetype | null): ChromeArchetype | null; // root
export function useScopedChromeArchetype(ref: RefObject<HTMLElement | null>, archetype: ChromeArchetype | null): void;
export function getArchetypeForGenre(genre: string): ChromeArchetype; // unchanged; throws on unknown
export interface OptionGroup { slug: string; label: string; rulesHref: string | null; items: OptionItem[]; }
```

### Out of scope (YAGNI)

No accordion/collapse; no per-genre color-coding; no search/filter; **no change to
in-game chrome** (genre archetype on `<html>` during actual play is correct —
only the `connect` phase changes). Per-card *palette* scoping (`useGenreTheme`) is
out of scope — the card adopts genre fonts/borders only.

## Cross-Epic Dependencies

**Depends on:**
- ADR-079 (Genre Theme System Unification) — the archetype/`[data-archetype]` CSS
  variable model this epic extends with a `house` member and a scoped applier.

**Depended on by:**
- None. Single-story epic, self-contained in `sidequest-ui`.
