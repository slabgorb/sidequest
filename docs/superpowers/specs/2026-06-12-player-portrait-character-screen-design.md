# Player portrait on the character screen + rounded-rect framing

**Date:** 2026-06-12
**Status:** Design — approved, pending implementation plan
**Repos:** `sidequest-server`, `sidequest-ui`

## Problem

A player picks a portrait during character creation, but it never appears on
any character surface. The pipeline is wired *almost* end to end:

- Player picks a portrait → client sends `selected_portrait_ref: <slug>`
  (`PortraitPanel` → `CharacterCreation.tsx:169`).
- Server records it onto the built character:
  `character.portrait_ref = sd.selected_portrait_ref` (`chargen_mixin.py:1150`).
- The UI panels already know how to render `portrait_url` — `CharacterPanel`
  header, party rows, and `CharacterSheet`.

The single severed link: `party_member_from_character`
(`sidequest-server/sidequest/server/views.py:581`) hardcodes
**`portrait_url=None`**. The stored slug is never resolved into an R2 URL, so
every `PARTY_STATUS` frame reports "no portrait" and the panels fall back to
initials.

Separately, the existing portrait framing is inconsistent and not the desired
shape: the in-game avatars are circles (`rounded-full`) and the character sheet
is a barely-rounded square (`rounded`). The desired treatment is a **rounded
rectangle, square (1:1) aspect**, applied consistently across all character
surfaces.

This is **one server wiring fix + a UI restyle** — no new infrastructure.

## Goals

1. The portrait a player picks shows on every character surface: `CharacterPanel`
   header avatar, `CharacterPanel` party rows, and `CharacterSheet`.
2. All character portraits render as a rounded rectangle, 1:1 aspect, radius
   scaled to size (~6–12px). No cropping of square source art.
3. A character with no picked portrait (skipped, or a world with no picker art)
   keeps the initials monogram placeholder, reframed to match.

## Non-Goals

- No new portrait *generation* or content work — the picker PNGs already exist
  on R2 behind the asset gate.
- NPC / cast / scrapbook portraits (`ConfrontationOverlay`, `CastSection`,
  `ScrapbookGallery`, `CartographyMap`) are out of scope — different surfaces,
  different visual context, not the character screen.
- No portrait-aspect (3:4) reframing — square aspect only.
- No persisted/derived URL on the character (see Decision below).

## Design

### Server — resolve the slug at emit time, via a shared helper

A new pure helper lives next to `resolve_asset_url` in
`sidequest-server/sidequest/server/asset_urls.py`:

```python
def resolve_player_portrait_url(
    genre_slug: str, world_slug: str, portrait_ref: str | None
) -> str | None:
    """Resolve a picked player-portrait slug to its R2 URL.

    Returns None when portrait_ref is falsy (player skipped, or the world
    ships no picker art). Otherwise builds the canonical world-portrait path
    and delegates to resolve_asset_url.
    """
    if not portrait_ref:
        return None
    return resolve_asset_url(
        f"genre_packs/{genre_slug}/worlds/{world_slug}/assets/portraits/{portrait_ref}.png"
    )
```

Two call sites converge on it:

- `views.py:581` — replace `portrait_url=None` with
  `resolve_player_portrait_url(sd.genre_slug, sd.world_slug, character.portrait_ref)`.
  Both slugs are already in scope on `_SessionData` (`session_state.py:189–190`).
- `rest.py:964` (`list_chargen_portraits`) — switch the inline path string to
  the same helper so the `genre_packs/.../portraits/{slug}.png` convention lives
  in exactly one place and the picker list can never drift from the emit path.

**Why resolve at emit time (Approach A) rather than persist a URL (Approach B):**
`portrait_ref` stays the single stored truth. The URL is always computed against
current CDN config, so durable saves (ADR-115) can't carry a dead absolute URL
if the CDN host ever changes. Approach B (store resolved URL at chargen finalize)
was rejected for exactly that staleness risk plus a second source of truth.
Approach C (inline resolve, no helper) was rejected because it duplicates the
path convention `rest.py` already owns.

**OTEL:** no new span. This surfaces already-stored data through the existing
`PARTY_STATUS` frame; `chargen.portrait_select` already fires at pick time. Per
both repos' CLAUDE.md OTEL carve-outs, cosmetic asset-URL resolution is not a
subsystem decision.

`portrait_ref` is validated against `picker_portrait_slugs(world_obj)` at confirm
time (`chargen_mixin.py`), so a non-null stored ref always names a real manifest
entry.

### UI — one shared `PortraitFrame`, rounded-rect everywhere

Today the img-or-initials pattern is hand-rolled three times with three shapes.
Extract a small `PortraitFrame` component so shape and fallback behave
identically across surfaces:

```
PortraitFrame({ url, name, sizeClass, radiusClass, bordered })
  - url present → <img aspect-square object-cover ...> with onError → initials
  - url absent  → initials monogram (toAvatarInitials), same frame
```

Consumers and shapes (square 1:1, radius scaled to size):

| Surface | Current | New |
|---|---|---|
| `CharacterPanel` header avatar | `w-12 h-12 rounded-full` | `PortraitFrame` 48px, `rounded-lg` (8px) |
| `CharacterPanel` party rows | `w-8 h-8 rounded-full` | `PortraitFrame` 32px, `rounded-md` (6px) |
| `CharacterSheet` portrait | `w-24 h-24 rounded` | `PortraitFrame` 96px, `rounded-xl` (12px) |

The existing FOLIO theming (gold border, paper background, `FONT_DISPLAY`
monogram) is preserved by threading the relevant style/border props through
`PortraitFrame`.

**Companions consistency:** the Companions rows in `CharacterPanel` (NPC
initials, currently `rounded-full`) sit directly beside the party rows. They
adopt the same `PortraitFrame` so the roster reads consistently; circles beside
rounded-rects would look broken. (Companions remain initials-only — they consume
no `portrait_url`.)

### Error handling

- `portrait_ref` null → helper returns `None` → `PortraitFrame` renders initials.
  Unchanged behavior.
- `portrait_ref` set but the R2 object is missing → URL still resolves (we never
  stat R2); `<img onError>` swaps to the initials monogram. Not a silent fallback
  — the server already logged the selection; the client degrades gracefully on a
  404 instead of showing a broken-image glyph.
- Unknown ref cannot occur for a stored ref (validated at confirm time); the
  helper is pure string-building and stays robust regardless.

## Testing

**Server (behavior-driven — no source-text wiring tests per CLAUDE.md):**

- `resolve_player_portrait_url`: returns the expected URL for a slug; returns
  `None` for a falsy ref.
- `party_member_from_character` fixture test: a character **with** `portrait_ref`
  → `PartyMember.portrait_url` is non-null and equals the helper output; a
  character **without** → `None`. Drives the real emit path (the wiring test).
- REST `list_chargen_portraits` returns the same URL for a given slug — guards
  helper convergence so REST and `PARTY_STATUS` can't drift.

**UI (Vitest):**

- `PortraitFrame`: renders `<img>` with the radius class when `url` set; renders
  initials when `url` null; `onError` swaps img → initials.
- Extend existing `CharacterPanel` / `CharacterSheet` tests: portrait renders
  when `portrait_url` present, initials when absent, and the frame carries the
  rounded-rect class (asserting it is not `rounded-full`).

## Repos touched

- `sidequest-server` — `resolve_player_portrait_url` helper + 2 call-site edits
  (`views.py`, `rest.py`).
- `sidequest-ui` — new `PortraitFrame` component + 3 (4 incl. Companions)
  consumer edits in `CharacterPanel.tsx` and `CharacterSheet.tsx`.
- No content or daemon changes.
