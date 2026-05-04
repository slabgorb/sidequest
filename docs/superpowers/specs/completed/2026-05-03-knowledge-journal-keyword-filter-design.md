# KnowledgeJournal — Keyword Filter

**Date:** 2026-05-03
**Author:** Dev (Inigo) via brainstorm with Keith
**Repo:** `sidequest-ui`
**Status:** Approved — ready for implementation plan
**Out of scope:** quoting, OR operator, field syntax, regex, source/category as searchable fields, persistence, match highlighting

## Problem

`KnowledgeJournal` (the live "Knowledge" widget at `sidequest-ui/src/components/KnowledgeJournal.tsx`) accumulates `KnowledgeEntry` records across a campaign — facts about people, places, quests, lore, abilities. After 20+ turns the list is long. Players who want to recall what they know about a specific subject (a named NPC, a ship, a substance) currently have to scroll the list and skim. Even with the existing **category** filter (Lore / Place / Person / Quest / Ability) and **sort** (chronological / categorical), narrow lookup is awkward.

The desired interaction: type one or more keywords and the list collapses to entries whose `content` mentions all of them.

## Audience

This serves **Sebastien** primarily (mechanics-first, wants to interrogate what the party "knows" before making a decision) and **Keith** secondarily (long-game continuity — three sessions ago, what did we hear about Pacheco?). Alex and the household would not be slowed down by it; the filter is opt-in via empty input.

## Behavior

### Parsing

- Split the input string on whitespace (any run of `\s+`) into **tokens**.
- Discard empty tokens.
- No quoting, no operators, no escaping.

### Match

- Empty token list → no filter applied; the existing category filter behaves as today.
- Otherwise: an entry passes the keyword filter iff `entry.content.toLowerCase()` contains **every** token (lowercased) as a substring.
- This is **AND across tokens** (intersection). `Bunjo Kestrel` matches entries about Bunjo *and* the Kestrel; entries that only mention one are filtered out.
- Per-token match is `String.prototype.includes` — substring, not word-boundary. `Kest` matches "Kestrel".

### Stacking with existing controls

- Keyword filter and category tab are **intersected**. On the "Person" tab, typing `Bunjo` shows only Person-category entries whose content matches. On "All", the same query searches across categories.
- Sort mode (chronological / categorical) is unaffected; it applies after both filters.

### UI

- Single text input rendered in the journal header, **above** the existing category tablist.
- Placeholder: `Filter by keyword`
- A clear button (×) appears inside the input when there's text; clicking it sets the value to empty.
- Live filter — no submit button, no Enter required. Filter applies on each keystroke via React state.
- The entry list re-renders as the user types.

### Empty-result state

- The existing empty-state (`Your journal is empty. Explore the world to fill its pages.`) shows when there are zero `KnowledgeEntry` records at all (current behavior).
- A new empty-result variant shows when the journal *has* entries but the active filters (category + keyword) leave zero matches: `No entries match "<keyword>"` (use the trimmed, joined token string).

## Non-functional

- **No new dependencies.** Pure React state + `Array.filter` on the existing entries prop. Entry counts in this game cap in the hundreds — no virtualization or memoization beyond the existing `useMemo`.
- **No persistence.** Reload clears the keyword. Adding `localStorage` retention is a future story; YAGNI for the "for now" version.
- **No backend changes.** Filtering is fully client-side; the entries prop is unchanged. No new WebSocket messages, no protocol changes, no server work.

## Implementation surface

Single file: `sidequest-ui/src/components/KnowledgeJournal.tsx`.

- Add `const [keyword, setKeyword] = useState('')` alongside the existing `activeCategory` and `sortMode` state.
- Extend the existing `filtered` derivation: after the category filter, apply the keyword AND-filter when `keyword.trim().length > 0`.
- Render the input in a new flex row above the existing `role="tablist"` row.
- Render the keyword empty-result variant inside the existing render branch where `sorted.length === 0` (does not currently exist as a distinct branch — the current empty-state guard fires only when `entries.length === 0`; add a new branch for "filters yield zero" downstream of the filter).

Estimated diff: ~30–40 lines in one file.

## Tests

Extend `sidequest-ui/src/components/__tests__/KnowledgeJournal.test.tsx`. New cases:

1. **Single keyword filters list.** Three entries about Bunjo, two about Pacheco. Type `Bunjo` → only Bunjo entries visible.
2. **Two tokens AND-narrow.** Type `Bunjo orange` → only entries mentioning both.
3. **Case-insensitive.** Type `BUNJO` → matches `bunjo` content.
4. **Substring, not word-boundary.** Type `Kest` → matches "Kestrel".
5. **Stacks with category tab.** On Person tab, type `Bunjo` → only Person-category entries matching.
6. **Empty input shows all.** Backspace to empty → list returns to category-filtered baseline.
7. **Whitespace-only input shows all.** Type only spaces → no filter applied.
8. **No matches → empty-result variant.** Type `xyznomatch` → renders `No entries match "xyznomatch"`.
9. **Clear button resets.** Click × → input empty, list returns to baseline.
10. **Wiring assertion.** Confirm the input is actually rendered inside the dock-mounted KnowledgeJournal (per CLAUDE.md "Every Test Suite Needs a Wiring Test").

## Risks / open questions

- **None blocking.** This is a pure client-side enhancement to a stable component with no protocol implications, no backend coupling, and no genre-pack dependencies.
- **Future:** if `source` or `learned_turn` later become useful filter dimensions, the parser can grow a `field:value` syntax. Out of scope today.
