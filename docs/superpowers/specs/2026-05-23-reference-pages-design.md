# Reference Pages — Rules & Lore (v1)

**Date:** 2026-05-23
**Author:** PM (Major Margaret Houlihan)
**Status:** Design — awaiting approval

## Problem

Players want more background and something to do during downtime. The genre/world data
already exists on disk as YAML in `sidequest-content/genre_packs/<pack>/` and
`.../worlds/<world>/`. It has no surface in the running game; nobody sees it but the
narrator.

## Goal

Two server-rendered HTML reference pages that read the pack/world YAML on disk and
render it as a plain hypertext document. A "Rules" button and a "Lore" button in the
running game open them in a new browser tab.

## Non-Goals (v1)

- **Deep-link anchors from in-game panels.** Iteration 2.
- **Spoiler / audience filtering.** Iteration 2 — *must land at the same time as deep
  links*, because that moves the audience from "Keith" to "the playgroup."
- **Pack picker / browseable index of all packs.** v1 reads only the active session's
  pack/world.
- **Themed styling per pack** (`client_theme.css` integration). Plain default stylesheet
  in v1.
- **Lobby surface.** v1 buttons live only in NarrativeView. Lobby exposure is iteration.
- **Markdown / inline link rendering of YAML string values.** Plain text v1.

## Architecture

Server-rendered HTML, served by the existing FastAPI app.

```
React UI (NarrativeView header)
        │
        │  <a href="/reference/rules/<pack>" target="_blank">
        │  <a href="/reference/lore/<pack>/<world>" target="_blank">
        ▼
FastAPI route
        │
        │  walk sidequest-content/genre_packs/<pack>/<files>
        │  parse YAML → render <section>/<h2>/<dl> tree
        ▼
HTML document (one shot, no JS, default stylesheet linked)
```

No client state, no JSON layer, no React routing. The page is a plain HTML document
that opens in a new tab so it does not disturb a running session.

## Routes

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/reference/rules/{pack}` | Render pack-tier YAMLs |
| GET | `/reference/lore/{pack}/{world}` | Render world-tier YAMLs (+ pack flavor YAMLs) |
| GET | `/reference/static/reference.css` | Plain stylesheet |

Both content routes return `text/html`. 404 if pack or world is unknown.

Pack and world strings are validated against the loaded genre pack registry — no
filesystem traversal beyond the configured `SIDEQUEST_GENRE_PACKS` roots. **Fail loud**
on missing files (404 with a clear message; no silent empty section).

## File-to-Page Mapping

### `/reference/rules/{pack}` — pack-tier files

Renders, in this order, each file that exists in `genre_packs/<pack>/`:

1. `archetypes.yaml`
2. `classes.yaml` *(signature abilities are the future hyperlink targets)*
3. `rules.yaml`
4. `progression.yaml`
5. `magic.yaml` *(skipped if absent — not every pack has magic)*
6. `power_tiers.yaml`
7. `achievements.yaml`
8. `tropes.yaml`
9. `equipment_tables.yaml`
10. `inventory.yaml`
11. `beat_vocabulary.yaml`

**Explicitly excluded (v1):**
- `prompts.yaml` — LLM scaffolding, not player content
- `seed_tropes.yaml` — Schrödinger's gun escalation structure; spoiler
- `pack.yaml`, `theme.yaml`, `visual_style.yaml`, `audio.yaml`, `portrait_manifest.yaml`,
  `cartography.yaml`, `axes.yaml`, `lethality_policy.yaml`, `visibility_baseline.yaml`,
  `char_creation.yaml` — metadata, asset config, or system-tier
- `cultures.yaml` — *also rendered on the Lore page; suppressed here to keep Rules
  focused on mechanics*

### `/reference/lore/{pack}/{world}` — world-tier + pack flavor

Renders, in this order:

**World tier** (from `genre_packs/<pack>/worlds/<world>/`):
1. `world.yaml`
2. `cultures.yaml` (world overrides)
3. `history.yaml`
4. `calendar.yaml`
5. `demographics.yaml`
6. `legends.yaml`
7. `openings.yaml`
8. `lore.yaml`

**Pack flavor** (genre-level worldbuilding common to all worlds in the pack):
9. `cultures.yaml` (from pack root)
10. `lore.yaml` (from pack root)
11. `history.yaml` (from pack root, if present)

**Explicitly excluded (v1):**
- `npcs.yaml` — contains hidden agendas, scenario beliefs, ADR-053 clue graph. *Hard
  exclude even in v1.* Without a spoiler filter, dumping this hands players the answer
  key.
- `portrait_manifest.yaml`, `visual_style.yaml`, `cartography.yaml` — asset config
- `assets/`, `cultures/` subdirectories — opaque blobs / split corpus files

This is intentionally conservative on the "dump everything" instruction: the two files
that *will* burn you (`npcs.yaml`, `seed_tropes.yaml`) stay out even pre-filter, because
the cost of un-spoiling is infinite and the cost of adding them in iteration 2 is one
line.

### No pack/world override merging in v1

The world's `lore.yaml` and the pack's `lore.yaml` render as separate sections. The
narrator merges them at runtime; the reference page does not. This is simpler and more
honest — the reader sees what the author actually wrote in each file. Merging is a
plausible iteration if it confuses readers.

## Rendering Rules

A small recursive walker translates parsed YAML to HTML:

- Top-level dict → one `<section>` per key, `<h2>` for the key
- Nested dict → `<dl>`, each key as `<dt>`, value rendered recursively as `<dd>`
- List of dicts → `<section>` per item with an `<h3>` from item's `name` / `id` / `title`
  field if present, else `Item N`
- List of scalars → `<ul>`
- Scalar → escaped text in a `<p>` (HTML-escaped; no markdown parsing v1)
- Multiline string → preserved as a `<p>` with `white-space: pre-wrap` styling

Depth cap: 6. Beyond that, render as `<pre>` of the YAML re-dump to avoid runaway markup.

Every `<h2>` and `<h3>` gets a stable `id` derived from the key/name, slugified
(`lowercase-with-hyphens`, ASCII only). These ids are forward-compatible with the
iteration-2 deep-link work — they don't have to be exposed yet but they're already
there.

## UI Integration

Two new buttons in the `NarrativeView` header, next to the existing controls. Each is a
plain anchor with `target="_blank" rel="noopener"`:

```jsx
<a className="ref-link" href={`/reference/rules/${pack}`} target="_blank" rel="noopener">
  Rules
</a>
<a className="ref-link" href={`/reference/lore/${pack}/${world}`} target="_blank" rel="noopener">
  Lore
</a>
```

`pack` and `world` come from the current `GameStateProvider`. Buttons are not rendered
if a session is not active (so the lobby/ConnectScreen does not show them in v1).

The buttons must NOT consume turns, NOT post WebSocket messages, NOT trigger any state
change in the running game. Pure navigation.

## Styling

A single static stylesheet served at `/reference/static/reference.css`. Goals:

- Readable serif body type, sensible measure (~70ch), generous line-height
- Clear `<h2>` / `<h3>` hierarchy
- Definition lists styled as columns where width allows
- No JS, no theme dependency, no genre-pack styling in v1

This is intentionally generic. A pack-themed stylesheet is iteration.

## Error Handling

- Unknown pack → 404 with `Pack '<x>' not found.` and a list of valid pack ids.
- Unknown world → 404 with `World '<x>' not found in pack '<y>'.` and a list of valid
  worlds for that pack.
- Missing optional file (`magic.yaml`, etc.) → silently skipped (file is genuinely
  optional).
- Missing *required* file when a section is expected → render the section heading with a
  visible `(missing: classes.yaml)` line. **No silent fallback.** Surfaces content drift
  loudly per CLAUDE.md principle.
- Malformed YAML → 500 with the parse error visible. Better to fail loud than render
  half a doc.

## Testing

Unit tests (sidequest-server):
- YAML walker handles dict / list-of-dict / list-of-scalar / nested / scalar
- Slug generation is stable and ASCII-safe
- 404 on unknown pack / unknown world
- 500 on malformed YAML
- Excluded files (e.g. `npcs.yaml`, `seed_tropes.yaml`) are never rendered even if
  present

Integration test:
- Hit `/reference/rules/tea_and_murder` against the live tea_and_murder pack — assert
  200, content-type `text/html`, contains `archetypes` and `classes` section headings,
  does *not* contain `npcs` or `seed_tropes`.

UI test (sidequest-ui):
- NarrativeView renders Rules and Lore links when session has pack+world
- Links carry correct href; click does not dispatch any WebSocket message
- Links are absent on ConnectScreen / Lobby

Wiring test (per CLAUDE.md doctrine): a test that asserts `NarrativeView` imports and
renders the link component, not just that the component exists in isolation.

## Implementation Notes

**Repos touched:**
- `sidequest-server` — new route module, YAML walker, stylesheet, tests
- `sidequest-ui` — two `<a>` tags in NarrativeView header, tests

**Estimated size:** 5 points. Server is the bulk of it; UI is trivial.

**Workflow:** TDD. The walker has enough edge cases (depth cap, list-of-dicts vs
list-of-scalars, escape rules, optional file handling) that test-first will pay back.

**ADR:** No new ADR required. This is feature work that sits cleanly on existing
infrastructure (FastAPI app, genre pack loader). If iteration 2 introduces the spoiler
filter as a public-schema layer, *that* gets an ADR.

## Acceptance Criteria

1. `GET /reference/rules/tea_and_murder` returns 200 `text/html` and contains, in order,
   the file sections listed under the rules mapping (omitting `magic.yaml`).
2. `GET /reference/lore/tea_and_murder/glenross` returns 200 and contains world-tier
   sections and the pack flavor tail.
3. `GET /reference/lore/tea_and_murder/glenross` does **not** contain any content from
   `npcs.yaml` or `seed_tropes.yaml`.
4. Unknown pack or world returns 404 with the list of valid ids.
5. NarrativeView renders "Rules" and "Lore" links opening in a new tab with the active
   session's pack/world; they are absent before a session is active.
6. Clicking either link does not post any WebSocket message or alter game state.
7. All headings have stable slugified `id` attributes (forward compat for iteration 2).
8. `just check-all` passes.

## Iteration 2 (out of scope here, but flagged)

When we wire game-UI panels (class signature ability buttons, rule callouts) to
hyperlink into these pages:

- Audience widens from Keith-only to the playgroup. **Spoiler filter must ship in the
  same iteration.** Likely Option A from brainstorming: an allowlist of player-safe
  fields per YAML kind. Files like `npcs.yaml` re-enter with a public projection
  (name + public_description only).
- Anchor stability becomes a contract — renaming a class or culture must keep its slug
  or break inbound links. Probably need a `slug:` field on slugged entities.
- Pack-themed stylesheet picks up `client_theme.css`.
- Lobby surface (`/reference` index page) so players can browse before sessions.
