# Reference Pages v2 — Panel Hyperlinks + Lobby Surface

**Date:** 2026-05-23
**Author:** Dev (Major Charles Emerson Winchester III)
**Status:** Design — awaiting approval
**Predecessor:** `2026-05-23-reference-pages-design.md` (v1, shipped)
**Brief:** `2026-05-23-reference-pages-v2-followup-brief.md`

## Problem

V1 shipped two server-rendered reference pages (`/reference/rules/<pack>`,
`/reference/lore/<pack>/<world>`) reachable from `NarrativeWidget` buttons. Every
`<h2>` / `<h3>` already has a stable slugified `id` attribute. Three pieces are
missing for the surface to do real work for the playgroup:

1. The in-game panels (character sheet, knowledge journal, location panel)
   don't hyperlink into the reference pages. Anchors exist; nothing links to
   them.
2. The lobby has no reference surface — players can't browse a pack before
   joining.
3. A user following a stale hyperlink lands on the page top with no signal
   that the anchor is gone.

## Scope

Three things ship together:

- **B.** Panel hyperlinks from structured surfaces (character sheet, knowledge
  journal, location panel) into the existing reference page anchors.
- **C.** Lobby reference surface on `ConnectScreen` (Rules + Lore buttons for
  the lobby's currently-selected pack/world).
- **Bad-anchor banner.** Loud failure when a hyperlink hash isn't found,
  satisfying brief hard-constraint #2.

## Out of scope (deferred / dropped)

- **Audience filter (player vs. GM view).** Dropped. At the table everyone is
  a player. The GM/maintenance view is a separate concern that lives in
  pack-authoring / world-creation tooling, not in the running game.
- **`public_description` schema work on `npcs.yaml`.** Moot — no player
  projection needed; v1 file exclusions stay in place.
- **Narration-prose reference callouts** (e.g. inline `<ReferenceAnchor>` in
  narrator output). Out of scope — v2 wires structured panels only.
- **Pack-themed stylesheet.** Defer to v3. v1's plain serif stylesheet stays.
- **`/reference/` landing page.** No global pack index. Lobby surface uses
  the lobby's selected pack/world.
- **`slug:` override field on classes / cultures / etc.** Iteration. v2 keeps
  v1's slug-from-name rule and documents the rename-breaks-link constraint.
- **Markdown rendering, cross-pack search, mobile layout.** Inherited from
  v1's out-of-scope list.

## Routing rule

The load-bearing architectural decision: **mechanics link to the genre/pack
page; content links to the world page.**

| Source kind | Anchor URL |
|---|---|
| Class | `/reference/rules/<pack>#class-<slug>` |
| Class signature ability | `/reference/rules/<pack>#class-<slug>-signature-<slug>` |
| Archetype | `/reference/rules/<pack>#archetype-<slug>` |
| Culture (world override) | `/reference/lore/<pack>/<world>#culture-<slug>` |
| Legend | `/reference/lore/<pack>/<world>#legend-<slug>` |
| Location (world) | `/reference/lore/<pack>/<world>#location-<slug>` |
| History entry | `/reference/lore/<pack>/<world>#history-<slug>` |

Server-side URL builders enforce this split. Panels don't choose where to
point — the server attaches the right URL based on the data's kind.

### Anchor id namespacing (v1 renderer change)

V1's renderer emits flat slugs for list-of-dict items
(`id="burglar"`, `id="thornberry"`). That allows cross-file collisions —
a class named "Knight" and a culture named "Knight" would both want
`id="knight"`. v2 needs unambiguous anchors, so the renderer is updated:
list-of-dict items get `id="<kind>-<slug>"` where `<kind>` is derived
from the containing file's stem (`classes.yaml` → `class`,
`archetypes.yaml` → `archetype`, `cultures.yaml` → `culture`,
`legends.yaml` → `legend`, `locations` → `location`, `history.yaml` →
`history`). The file-level wrapper section keeps its existing
`id="file-<stem>"`. Top-level scalar/dict keys keep flat slugs (those
already correspond to unique sections on a page).

This is a small additive change in `reference_renderer.py` — the slug
function is reused, the namespacing happens in the list-walker call
site. v1 page consumers (the two existing buttons) are unaffected because
they don't follow specific anchors yet.

## Server architecture

### Shared slug helper

Extract `slugify` from `reference_renderer.py` into a small standalone module
so two surfaces never drift:

```
sidequest-server/sidequest/server/reference_slug.py
    def slugify(text: str) -> str  # lowercase, ASCII, hyphenated, max 64 chars
```

Both `reference_renderer.py` and the new `reference_anchors.py` import from
this module. This is the contract.

### Anchor URL builders

```
sidequest-server/sidequest/server/reference_anchors.py
    def build_rules_url(pack: str, kind: str, *keys: str) -> str
    def build_lore_url(pack: str, world: str, kind: str, *keys: str) -> str
```

`build_rules_url("tea_and_murder", "class", "burglar", "signature", "cosh")`
→ `"/reference/rules/tea_and_murder#class-burglar-signature-cosh"`

`build_lore_url("tea_and_murder", "glenross", "culture", "thornberry")`
→ `"/reference/lore/tea_and_murder/glenross#culture-thornberry"`

Both functions slugify each key segment via the shared helper, validate that
the pack (and for lore, the world) is known via the genre registry, and raise
loudly on unknown ids — no silent fallback per CLAUDE.md.

### Protocol additions

All new fields are `Optional[str]`. A `None` value means "no reference page
exists for this entity"; the UI renders plain text in that case.

| Type | New field | Populated when |
|---|---|---|
| `AbilityDefinition` | `reference_url` | `source == "Class"` and the class has a `classes.yaml` entry with this ability |
| `CharacterDefinition` | `class_reference_url` | character's class is a known `classes.yaml` entry |
| `CharacterDefinition` | `archetype_reference_url` | character's archetype is a known `archetypes.yaml` entry |
| `KnowledgeEntry` | `reference_url` | the entry's `FactCategory` maps to a renderable kind (see KnowledgeEntry mapping below) and the keyed entity exists in the YAML |
| `LocationDefinition` | `reference_url` | the location has a matching entry in the world's `world.yaml` / locations file |

Attachment happens server-side at the same point the protocol object is
constructed — not in a separate enrichment pass. The pack/world the session
is bound to is already in scope at that point.

### KnowledgeEntry category mapping

`FactCategory` (defined client-side in `GameStateProvider.tsx`) is:
`Lore | Place | Person | Quest | Ability`. v2 attaches `reference_url`
only when both the category maps to a renderable kind and the keyed
entity exists in the YAML:

| `FactCategory` | Target kind | Page | Notes |
|---|---|---|---|
| `Lore` | `legend` or `history` | Lore | Resolved by exact-match against `legends.yaml` first, then `history.yaml`; first hit wins. |
| `Place` | `location` | Lore | Matches against world locations file. |
| `Person` | — | — | **No `reference_url`.** `npcs.yaml` is excluded from rendering (v1 doctrine, preserved here). Person entries render as plain text. |
| `Quest` | — | — | No corresponding YAML file in v1's rendered set. Plain text. |
| `Ability` | `class-<slug>-signature-<slug>` or unmatched | Rules | If the ability matches a class signature in `classes.yaml`, link to the nested anchor; otherwise plain text. |

The mapping is implemented as a small dispatch table in
`reference_anchors.py`. Adding new categories or rerouting an existing
one is a single-table edit.

### Bad-anchor banner

The reference HTML routes gain two small additions:

1. A **JSON island** listing every valid anchor id rendered on the page:

   ```html
   <script id="ref-anchors" type="application/json">
   ["class-burglar","class-burglar-signature-cosh","archetype-aunt", ...]
   </script>
   ```

2. A **~10-line inline script** that checks `location.hash` against the JSON
   island and toggles a hidden banner element on mismatch:

   ```html
   <div id="ref-bad-anchor" hidden>Anchor '#<id>' not found on this page.</div>
   <script>
     (function () {
       var hash = location.hash.replace(/^#/, "");
       if (!hash) return;
       var anchors = JSON.parse(document.getElementById("ref-anchors").textContent);
       if (anchors.indexOf(hash) === -1) {
         var banner = document.getElementById("ref-bad-anchor");
         banner.textContent = "Anchor '#" + hash + "' not found on this page.";
         banner.hidden = false;
       }
     })();
   </script>
   ```

No external JS, no framework, no build step. The banner uses the same plain
stylesheet as the rest of the page.

## Client architecture

### Lobby surface (deliverable C)

`ConnectScreen.tsx` renders the existing `ReferenceLinks` component, bound to
the lobby's currently-selected pack and world:

- Rules button: enabled when a pack is selected.
- Lore button: enabled only when both pack and world are selected.
- Disabled state: button is visible but `aria-disabled` and not a clickable
  link. (Hidden is rejected: per memory, no flickering data-gated tabs — same
  principle applies to lobby controls. A button that pops in and out as the
  player picks a pack is the same UX anti-pattern.)

No `/reference/` index page. The lobby points at the user's actual selection.

### Panel hyperlinks (deliverable B)

Each affected panel renders an entity name as a hyperlink iff its
`reference_url` is non-null; otherwise plain text. All hyperlinks use
`target="_blank" rel="noopener"`.

- `CharacterSheet.tsx`
  - Ability list: when `ability.reference_url` is set, wrap the ability name
    in an `<a>`. The trailing source pill (e.g. "Class") stays plain text.
  - Class name in the header subtitle: hyperlink iff
    `data.class_reference_url` is set.
  - Archetype name: same pattern with `data.archetype_reference_url`.
- `KnowledgeJournal.tsx`
  - Entry title: hyperlink iff `entry.reference_url` is set.
- `LocationPanel.tsx`
  - Location heading: hyperlink iff `location.reference_url` is set.

No `onClick` handler is added to any of these anchors. No call to
`useGameSocket`, no `dispatch`, no state mutation. Pure HTML navigation.
Verified by wiring tests (see below).

### Component reuse

The lobby and `NarrativeWidget` both render `ReferenceLinks` — same
component, different props. Disabled-state logic moves into the component
itself so both call sites stay terse.

## Slug stability contract

v2 does not introduce a `slug:` override field. The slug is derived from the
entity's display name via the shared `slugify` helper.

Consequence: renaming a class, archetype, culture, legend, or location
without a matching content migration breaks every inbound link to its
anchor. This is acceptable for v2 because:

- The bad-anchor banner surfaces the break loudly to the player.
- Content-team renames are rare and reviewable.
- The override field is a clean v3 addition without protocol churn.

This constraint is documented in the v2 spec and surfaced in
`sidequest-content/CLAUDE.md` as a one-line authoring note.

## Testing

Per memory rule: **no content-coupled tests.** All assertions about the
genre pack registry live in fixture packs; live `genre_packs/*` validation
moves into a separate validator surfaced loudly at load time.

### Server unit tests (sidequest-server)

- `reference_slug.slugify` round-trip cases (ASCII, unicode, punctuation,
  length cap).
- `build_rules_url` / `build_lore_url`:
  - happy path for each kind in the routing-rule table
  - unknown pack raises `KeyError` (loud, no silent fallback)
  - unknown world raises `KeyError`
  - segments are slugified via the shared helper (assertion: monkeypatching
    `reference_slug.slugify` is observed by both surfaces)
- JSON-island content: `reference_renderer.assemble_rules_page` emits a
  `<script id="ref-anchors">` element whose JSON content equals the slug
  set of all `id`-bearing headings in the body. Fixture pack only.
- Bad-anchor banner element is present in the rendered HTML with the
  `hidden` attribute set by default.
- **Renderer namespacing:** list-of-dict items inside a file section
  emit `id="<kind>-<slug>"` where `<kind>` derives from file stem
  (`classes.yaml` → `class`). Fixture cases cover singular conversion
  for each rendered file. Cross-file name collision (e.g. a class
  "Knight" and a culture "Knight") produces distinct ids
  (`class-knight` vs `culture-knight`).

### Server integration tests

- Against a **fixture pack** in `tests/fixtures/genre_packs/`:
  - `GET /reference/rules/fixture_pack` returns 200 with the JSON island,
    the banner element, and at least one expected `id`.
  - `GET /reference/lore/fixture_pack/fixture_world` returns 200 with the
    JSON island.
- Protocol round-trip: serializing a fixture `AbilityDefinition` with
  `source="Class"` from a fixture pack populates `reference_url`;
  `source="Item"` leaves it `None`.
- `KnowledgeEntry` with category mapping to a fixture lore entity
  populates `reference_url`; entries with unknown category leave it `None`.

### Live-content validator (separate from unit tests)

A small CLI / load-time check that walks every live pack and reports:

- Any class/archetype/culture/legend/location whose slug collides with
  another entity's slug on the same page.
- Any entity that has been renamed since the previous run (detected via a
  manifest comparison, optional follow-on).

Validator is invoked by `just content-validate` (new recipe) and runs in
CI on `sidequest-content` changes. Live-pack errors surface there, never
in the server unit suite.

### UI tests (sidequest-ui)

- `CharacterSheet`:
  - Renders ability as `<a target="_blank" rel="noopener">` when
    `reference_url` is set; renders plain text otherwise.
  - Clicking the ability anchor does NOT call any WebSocket send (wiring
    test — mock `useGameSocket`, assert no dispatch).
  - Same coverage for class name and archetype.
- `KnowledgeJournal`: anchor / plain-text / no-WS-send coverage.
- `LocationPanel`: anchor / plain-text / no-WS-send coverage.
- `ConnectScreen`:
  - Rules button is enabled when a pack is selected, `aria-disabled` when
    not.
  - Lore button is enabled only when both pack and world are selected.
  - Buttons carry correct hrefs for the current selection.
  - Clicking either button does not dispatch a WebSocket message.
- `ReferenceLinks` wiring test: still imported and rendered by
  `NarrativeWidget` (regression check on v1).

## OTEL coverage

Per CLAUDE.md observability principle, every backend fix that touches a
subsystem adds OTEL spans. v2 attaches `reference_url` fields inside the
existing protocol-building paths, so:

- `sidequest.reference.url_attached` watcher event emitted from each builder
  call site, with attributes `kind`, `pack`, `world` (lore only),
  `keys`. Lets the GM panel verify the attach is actually happening
  rather than silently `None`.
- `sidequest.reference.url_failed` for the loud failure path (unknown pack /
  world), severity ERROR.

No span on the route handler itself — v1 already covered HTTP-tier
observability via FastAPI's middleware.

## Error handling

- Unknown pack / world to the URL builder → raise loudly, ERROR span, no
  silent `None`.
- Unknown ability / class / culture during attach → leave `reference_url`
  as `None`; emit an INFO watcher event (`reference.url_skipped`) with the
  kind and key. This is the "the entity exists in the game state but not in
  the YAML" case and is recoverable (UI renders plain text).
- Bad anchor at the client → banner appears (no scroll-to-top fallback).

The contrast is intentional: builders fail loud (programmer error), attach
fails soft-but-observable (content drift), client failures surface in the
UI.

## Hard constraints (preserved from brief)

1. **No origin-side auth.** Cloudflare Zero Trust gates identity; v2 adds
   no `?audience=` param, no role check, no header read.
2. **No silent fallbacks.** Bad-anchor banner is the visible failure; URL
   builders raise on unknown pack/world; attach emits an INFO watcher event
   when an entity is missing from YAML.
3. **Hyperlinks must not consume turns.** No `onClick` handlers on any new
   anchor; pure HTML navigation. Verified by wiring tests.
4. **No content-coupled tests.** Server tests use fixture packs; live
   content runs through the validator.

## Acceptance criteria

1. `CharacterSheet` renders a class-source ability as a hyperlink to
   `/reference/rules/<pack>#class-<slug>-signature-<slug>` opening in a new
   tab when `reference_url` is present on the ability. Abilities without
   `reference_url` render as plain text.
2. `CharacterSheet` renders the character's class name and archetype name
   as hyperlinks when the corresponding `*_reference_url` is set.
3. `KnowledgeJournal` entries with a recognized category render as
   hyperlinks to `/reference/lore/<pack>/<world>#<kind>-<slug>`.
4. `LocationPanel` location headings hyperlink to the lore page anchor
   when `reference_url` is set.
5. `ConnectScreen` renders a Rules button (enabled when a pack is
   selected, `aria-disabled` otherwise) and a Lore button (enabled only
   when both pack and world are selected).
6. Clicking any reference hyperlink does NOT post a WebSocket message or
   alter game state. (Wiring tests cover CharacterSheet, KnowledgeJournal,
   LocationPanel, ConnectScreen.)
7. A reference page loaded with `location.hash` not present in the page's
   anchor set shows a visible `Anchor '#…' not found on this page.` banner.
8. `reference_slug.slugify` is imported by both `reference_renderer.py` and
   `reference_anchors.py`. Grep confirms no duplicate slug implementation.
8a. Rendered list-of-dict items carry namespaced anchor ids
    (`id="<kind>-<slug>"`); a fixture with same-named entries in different
    files produces distinct ids.
9. OTEL: `sidequest.reference.url_attached` spans fire when builders
   attach a URL; `url_failed` (ERROR) fires on unknown pack/world;
   `url_skipped` (INFO) fires when attach finds no matching YAML entity.
10. `just check-all` passes.

## Implementation notes

**Repos touched:**

- `sidequest-server` — new `reference_slug.py`, new `reference_anchors.py`,
  protocol additions to `AbilityDefinition` / `CharacterDefinition` /
  `KnowledgeEntry` / `LocationDefinition`, attach call sites, JSON island
  + banner in renderer, OTEL spans, tests.
- `sidequest-ui` — `ConnectScreen` integration, `ReferenceLinks` disabled
  state, anchor wrapping in `CharacterSheet` / `KnowledgeJournal` /
  `LocationPanel`, tests.
- `sidequest-content` — one-line authoring note in `CLAUDE.md` about the
  rename-breaks-link constraint. No YAML changes.

**Estimated size:** 6 points.

- Server: shared slug extract + builders + protocol additions + attach
  wiring + JSON island + tests ≈ 3.5 pts
- Client: ConnectScreen lobby + three panel surfaces + tests ≈ 2 pts
- OTEL + validator stub ≈ 0.5 pts

**Workflow:** TDD per project default. Tests-first pays back on the
attach-conditional-on-YAML-presence logic and the JSON-island assertion.

**ADRs:** No new ADR required. The slug contract and rename-link
constraint are documented in the spec and the content `CLAUDE.md` line.
If v3 introduces the `slug:` override field, that becomes a thin ADR on
the content authoring schema.

## Iteration 3 (out of scope here)

- `slug:` override field on classes, cultures, legends, locations — turns
  renames into a non-breaking content change.
- Pack-themed stylesheet (`client_theme.css` wired into the reference
  pages).
- `/reference/` global pack index.
- Narration-prose reference callouts (`<ReferenceAnchor>` component
  emitted by the narrator inline in turn text).
- Maintenance/Creation-mode GM view of the same pages, with `npcs.yaml` /
  `seed_tropes.yaml` re-included — separate surface, separate auth path,
  not in the running game.
