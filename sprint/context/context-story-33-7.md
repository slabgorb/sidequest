---
parent: context-epic-33.md
workflow: trivial
---

# Story 33-7: Character panel header — portrait, level, archetype display

## Business Context

The character sidebar is the single most-visited panel during a session — it's where players look when they want to know who they are, what they can do, and how hurt they are. Today that header is plain text: a name and a "Level X Class" subtitle. There's no portrait slot in the layout, no level badge, and no genre/archetype anchor to ground the character in the world.

This story replaces the header with a proper three-column row: a circular portrait placeholder (filled by Story 33-2's portrait system when available), the name in accent color, an archetype + genre subtitle line, and a compact level badge. It's a polish story on a cosmetic surface — no backend, no protocol, no game-state changes — but it carries disproportionate weight for the playgroup's primary audience:

- **Keith (forever-GM who wants to play)** gets the character-identity fidelity he's used to seeing on paper character sheets.
- **Sebastien (mechanics-first)** gets the level badge as a constant at-a-glance reference instead of buried in a subtitle.
- **Alex (slower reader)** benefits from the portrait + shape cues that reduce text re-reading.

Before-state reference: playtest screenshot `011-turn1-result.png`. Mockup: `.playwright-mcp/mockups/epic-33-panel-improvements.html#s33-7`.

## Technical Guardrails

**Target file:** `sidequest-ui/src/components/CharacterPanel.tsx` — lines 96-116 contain the current header block inside the `data-testid="character-panel"` wrapper. Replace those lines; do not restructure the panel shell or the tabs below.

**Shape to land (from mockup `s33-7` After state):**

```
┌─────────────────────────────────────┐
│ [◈ 48px ] Sable Vostok       Lv 1   │
│           Grand Farseer ·           │
│           Mutant Wasteland          │
└─────────────────────────────────────┘
```

Three-column flex row: portrait (fixed 48px circle), meta column (name + subtitle, min-width flex-grow, text-truncate), level badge (right-aligned, compact chip).

**Use existing primitives, do not invent new ones:**
- Name color: `text-[var(--primary)]` — already in use at line 106.
- Muted subtitle color: `text-muted-foreground` — already in use at line 107.
- Portrait shape: `rounded-full` instead of current `rounded` square (line 102) — this is the only structural change.
- Portrait size: `w-12 h-12` (48px) replacing current `w-16 h-16` (64px, line 102). Smaller circle + level badge wins over bigger square.
- Level badge: compact chip with bordered pill shape — use Tailwind (`px-2 py-0.5 rounded-md text-xs border border-[var(--primary)]/40 text-[var(--primary)]`) — do not introduce a new UI kit component.

**Portrait placeholder:** When `character.portrait_url` is falsy, render a circular div at the same 48px footprint with a centered glyph (mockup uses `◈` / Lozenge U+25C8). Do NOT silently omit the portrait slot — layout must stay three-column whether the portrait exists or not (no layout shift when 33-2 later fills it).

**Genre/archetype subtitle:** The subtitle format is `{Class Display Name} · {Genre Display Name}`. Class is already available via `toDisplayName(character.class)` (line 108). Genre comes from the game state provider / theme context — check `GameStateProvider` or `useGenreTheme` for the current genre slug, and map to display name via the genre pack metadata that the UI already loads for `ConnectScreen`. **Do not fetch; do not add a prop — consume from whatever the panel can already reach.** If the only way to get genre is plumbing a new prop through three levels, stop and flag it back — that's scope creep for a trivial story.

**Do NOT touch:**
- The tabs below the header (lines 118+) — those belong to other 33-x stories.
- The per-character location block removed at lines 110-114 — it's dead; leave it dead.
- Party section at the bottom of the file — that's 33-12's target.
- `CharacterWidget.tsx` at `src/components/GameBoard/widgets/` — that's the Dockview adapter; the actual markup lives in `CharacterPanel.tsx`.

**Archetype constraint from epic context:** This story layers into the existing header-tabs-footer hierarchy — header stays pinned at the top of the panel, tabs stay where they are. Header-zone additions are reserved for 33-10 (conditions/wounds) which will surface in the same header band. Keep the markup flat enough that 33-10 can insert a wound/condition row below the name/level without fighting the layout.

## Scope Boundaries

**In scope:**
- Replace header markup in `CharacterPanel.tsx` (lines 96-116) with three-column row: portrait slot (48px circle), name + archetype·genre subtitle, level badge.
- Portrait placeholder when `character.portrait_url` is absent (keeps layout stable).
- Level badge as a styled chip using existing theme CSS vars.
- Subtitle line combining class display name and genre display name with `·` separator.
- Update existing `CharacterPanel.test.tsx` header assertions to match new DOM shape.
- Add one integration check that the header renders inside `data-testid="character-panel"` (wiring test — per project rule "Every Test Suite Needs a Wiring Test").

**Out of scope:**
- Actually generating or fetching portrait images (33-2's job; this story only reserves the slot).
- Conditions/wounds display (33-10).
- Stat highlighting / stat usage labels (33-8, 33-9).
- Party section (33-12).
- Inventory header (33-16).
- Any protocol / WebSocket / backend change — this is a pure markup-and-CSS story.
- New UI kit components (shadcn additions, icon libraries) — use Tailwind + existing CSS vars only.

## AC Context

Expanding the story description into testable criteria:

**AC1 — Three-column header layout renders for any character**
- Header row inside `[data-testid="character-panel"]` contains three children: portrait slot, meta column, level badge.
- Layout is a flex row, `items-center` (not `items-start` — badge needs vertical centering), with `gap-3` between the portrait and meta, and meta flex-grows to push the badge right.
- Test: render panel with a mock character, assert all three child regions are present in the DOM and in document order (portrait, meta, level).

**AC2 — Portrait slot is always present (placeholder when no URL)**
- If `character.portrait_url` is truthy, render `<img>` inside a `w-12 h-12 rounded-full` wrapper.
- If falsy, render a `w-12 h-12 rounded-full` div with a centered placeholder glyph and `bg-[var(--surface)]` fill.
- Both states are exactly 48px square, preventing layout shift when the portrait loads later.
- Test: render with `portrait_url = undefined`, assert placeholder div renders with the glyph and correct dimensions; render with `portrait_url = "http://..."`, assert `<img src>` and same dimensions.

**AC3 — Name renders in accent color and truncates gracefully**
- Character name renders as an `<h2>` with `text-[var(--primary)]` and `truncate` class.
- Test: render with a long name ("Aelindranoria Veshthalassar"), assert the `<h2>` has `truncate` class and `min-w-0` on its parent column (required for flexbox truncation to actually work).

**AC4 — Subtitle combines class + genre with separator**
- Subtitle renders as `<p className="text-xs text-muted-foreground">{classDisplayName} · {genreDisplayName}</p>`.
- When genre is unavailable for any reason, render just the class (no dangling ` · ` — this is cosmetic, not a silent fallback: the character class always resolves, and the genre is a display enrichment).
- Test: render with a known character class (e.g., `"grand_farseer"`) and assert subtitle text contains "Grand Farseer" and the current genre's display name.

**AC5 — Level badge renders as compact chip on the right**
- Badge renders as a chip showing `Lv {character.level}` (e.g., `Lv 1`).
- Styled as a bordered pill, right-aligned in the flex row (meta column flex-grows to push it).
- Test: assert the badge element contains the text `Lv 1` for a `level: 1` character, and assert its computed position is right of the meta column (can assert via class-based layout or via testing-library's `getByText` + parent structure).

**AC6 — No regression in tab/stats content below the header**
- The tabs row (`role="tablist"`), tab panels, and stats content below the header render identically to before.
- Test: existing `CharacterPanel.test.tsx` tab-switching assertions still pass.

**AC7 — Wiring test (required by project rule)**
- A test verifies that `CharacterPanel` is the component actually rendered inside the GameBoard's CharacterWidget — not just that the new header works in isolation.
- Test: either extend an existing `CharacterWidget` / `GameBoard` integration test, or add one that mounts `CharacterWidget` with a mock character and asserts the new header markup is present.

## Assumptions

- **Genre display name is reachable from within `CharacterPanel.tsx` without new prop plumbing.** Most likely via the game state context or theme provider that already sets `data-archetype` on `<html>`. If it turns out to require a new prop threaded from `GameBoard.tsx` through the widget registry, stop and flag back — that's a design deviation, not a trivial fix.
- **Character class strings round-trip through `toDisplayName(character.class)` for all genre packs.** This function is already imported at the top of the file; it's assumed to handle any class slug the server sends.
- **Portrait URL, when present, points to an already-sized image** — no responsive srcset needed for a 48px avatar.
- **Level is a small integer (1-99) and always present on the character payload.** If level is 0 or undefined in some edge case (e.g., the instant after chargen), the chip should still render as `Lv —` or `Lv 0` rather than crash; pick the minimal non-crashing behavior and move on.
- **The portrait-placeholder glyph `◈` renders in all genre font stacks.** Parchment/terminal/rugged archetypes use different font families (per epic context); if the glyph is missing in any stack, fall back to a CSS-drawn shape (e.g., a filled div with rounded corners) rather than emoji.

## Interaction Patterns

Not applicable — this story is static markup. No state transitions, no click handlers, no user input. The header is read-only.

## Accessibility Requirements

- The portrait `<img>` must have a meaningful `alt` attribute — reuse `alt={character.name}` pattern already in place at line 101.
- The placeholder div (when no portrait URL) should have `aria-hidden="true"` — it's purely decorative, and the name immediately to its right is the actual identity cue.
- The level badge should be plain text inside its chip — no ARIA needed, but do not wrap it in a `<button>` or make it interactive (that would promise affordance this story doesn't deliver).
- The header row must not introduce a tab stop — it's not focusable. Keyboard navigation should proceed directly from whatever precedes the panel to the existing tab bar below.
- Keep the name `<h2>` as the semantic heading — screen readers already use it as the panel landmark.

## Visual Constraints

- **Colors must come from CSS vars, not hardcoded hex or Tailwind palette colors.** Use `var(--primary)`, `var(--surface)`, `var(--background)`, `text-muted-foreground`. This is load-bearing: the two-layer theming system (per-epic-context) depends on every themed component reading from the cascade.
- **Portrait size is fixed at 48px (`w-12 h-12`).** Do not make it responsive or genre-variant — all three archetypes share the same portrait footprint. The epic context's "archetype chrome" layer will decorate the border/glow/treatment via `[data-archetype="..."]` selectors, which is scoped to a future polish pass, not this story.
- **No new z-index usage.** The header sits in the normal document flow. The epic's z-index bands (`BackgroundCanvas` at -10, terminal scanlines at 100) are preserved by doing nothing to disturb them.
- **Level badge must not overflow on narrow panels.** Character panel can be as narrow as 260px in the mobile `MobileTabView`. At that width, the header must still fit portrait (48px) + gap (12px) + truncated meta + badge (~48px) = ~170px of fixed width, leaving ~90px for name truncation. Verify at 260px and at the default desktop width.
- **The subtitle line wraps gracefully on narrow panels.** Use `leading-tight` and allow a second line if needed — do not force single-line with `truncate` on the subtitle (that hides genre info, which is the whole point of adding it).
