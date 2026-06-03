---
parent: context-epic-77.md
workflow: trivial
---

# Story 77-6: Author wry_whimsy seed_tropes deck (ADR-128) — active_seeds carve-out

## Business Context

Epic 77 gives every session a **mechanical campaign spine** — a quest, an anchor,
current stakes — and a fourth field, `active_seeds`, that was empty in the
wry_whimsy/oz playtest (2026-06-02) alongside the others. ADR-137's code-grounded
root cause found **four fields, four distinct causes**. Three of them
(`quest_anchors`, `quest_log`, `active_stakes`) are *engine* gaps and are owned by
the implementation lane (77-1…77-5). The fourth, `active_seeds`, is **a content
gap, not an engine gap**:

> the ADR-128 seed-trope deck mechanism already works, and `tea_and_murder`
> already populates the identical `active_seeds` field through it. wry_whimsy
> simply authors no seed deck, so the deck deals nothing and `active_seeds`
> stays `[]`.

This story closes that half of the empty-spine failure **purely as content** —
authoring a `seed_tropes.yaml` deck for the wry_whimsy pack, following the
`tea_and_murder` precedent exactly. **No engine change.** The deck mechanism
(deal at session start, draw on engagement, expire to ghosts) is live and tested
under ADR-128; the only thing missing is authored seeds for this pack to deal.

This is a concrete instance of the project's authoring-surface theme (Jade, the
first non-Keith author): *a table should be able to add the short-arc hooks a
world wants by writing pack/world YAML, never by touching engine code.* If giving
wry_whimsy a seed deck required a server change, that would be a failure of the
content surface. It does not — and this story proves it by adding only YAML.

Genre-fit matters: wry_whimsy is a portal-fairytale pack (Oz / Wonderland /
Gulliver-style Secondary Worlds, "the traveler arrives by accident and wants only
to go home"). The seeds are baited diamonds-and-coal hooks (ADR-014) — vague on
purpose — that the narrator later threads into whatever macro thread emerges. They
must read as genre-true whimsical-portal seeds, not cosy-crime ones.

## Technical Guardrails

**This is a content-only story. Do not modify any engine code.** The acceptance
gate is: author the deck, then prove the *existing* ADR-128 mechanism picks it up.

**Where the deck lives (verified):**
- Author a new file: `sidequest-content/genre_packs/wry_whimsy/seed_tropes.yaml`.
- The loader reads it at **pack (genre) tier**, unconditionally, via
  `_load_yaml_raw_optional(path / "seed_tropes.yaml")` and validates each entry as
  a `SeedTrope` model — `sidequest-server/sidequest/genre/loader.py:1289-1292`,
  surfaced on the pack as `pack.seed_tropes`
  (`sidequest-server/sidequest/genre/models/pack.py:230`).
- **Reference to copy from:**
  `sidequest-content/genre_packs/tea_and_murder/seed_tropes.yaml` (25 authored
  seeds — the canonical precedent; mirror its shape and authoring discipline, not
  its cosy-crime content).

**Pack-tier deck across multiple worlds — keep flavor genre-form-true.** The deck
is genre-tier, so the same seeds are dealt for **all three** wry_whimsy worlds
(`worlds/oz`, `worlds/wonderland`, `worlds/gulliver`). Per ADR-120's
genre-form-vs-world-flavor boundary and the genre `lore.yaml` note in this pack
("No Oz/Wonderland/Gulliver proper nouns as canon here"), the seeds must hook the
**portal-fairytale FORM** (a threshold, an unaccountable local custom, a road that
rearranges, a small wrongness in a vivid place) and must **not** name a specific
world's NPCs, factions, or geography. Concretely: avoid Dorothy/Alice/Lilliput
proper nouns; tea_and_murder's seeds can safely name Mrs. Cameron because that
pack ships a single Highland world — wry_whimsy cannot, because one deck serves
three worlds.

**`SeedTrope` schema (`extra="forbid"` — authoring typos fail loudly):**
- `id: str` (required) — stable slug.
- `name: str` (required).
- `description: str | None` — the seed prose; vague-on-purpose hook.
- `flavor_tags: list[str]` — used by the narrator/deck for retroactive threading.
- `lifespan_turns: int` (default 0) — turns before the seed expires to a ghost.
  tea_and_murder uses 4–8; match that band.
- `delivery_hints: list[str]` — three-ish ways the seed can surface in play.
- `narrative_hint: str` — how the narrator should thread the seed if engaged /
  if ignored.
- No other keys — `model_config = {"extra": "forbid"}` rejects unknown fields at
  load (`sidequest-server/sidequest/genre/models/tropes.py:63-81`).

**Hand size / deck depth.** `ensure_initial_draw` deals an opening hand of 3
(`_DEFAULT_INITIAL_HAND`, `seed_tick.py:74`) and `draw_engaged_seed` draws more
mid-session on player engagement, **without replacement**. tea_and_murder ships
25 seeds. Author enough that the deck does not exhaust in a normal session — aim
in the same ballpark (a dozen-plus; do not ship just 3).

**Optional manifest hygiene.** tea_and_murder lists `seed_tropes` under
`extensions:` in its `pack.yaml`. The loader does **not** gate file loading on
that list (it's a declarative manifest field, `pack.py:96`), so adding
`seed_tropes.yaml` is sufficient for the mechanism to fire. Adding
`- seed_tropes` to wry_whimsy `pack.yaml` `extensions:` is a consistency nicety
matching the precedent, not a functional requirement — if you add it, that is the
only `pack.yaml` edit; do not change loader behavior.

**Validation discipline (from project memory — load the real loader, not just the
validator).** `pf validate pack` returning PASS is **not** proof the pack loads;
the real gate is `load_genre_pack`. Run the loader against wry_whimsy and confirm
`pack.seed_tropes` is non-empty and well-typed. Then confirm runtime population:
in a fresh session, `ensure_initial_draw` (called from
`sidequest-server/sidequest/server/websocket_session_handler.py`) deals into
`snapshot.active_seeds` and emits a `SPAN_SEED_DRAWN` OTEL span per drawn seed
(`seed_tick.py:127`) — that span is the GM-panel lie detector confirming the deck
is engaged, not improvised. **No new OTEL spans to add** — the mechanism already
emits them; you are verifying they fire for wry_whimsy.

## Scope Boundaries

**In scope:**
- Author `sidequest-content/genre_packs/wry_whimsy/seed_tropes.yaml` — a deck of
  genre-form-true portal-fairytale seed tropes, following the
  `tea_and_murder/seed_tropes.yaml` shape and the `SeedTrope` schema.
- (Optional, precedent-matching) add `- seed_tropes` under `extensions:` in
  `wry_whimsy/pack.yaml`.
- Verify the pack still loads via the **real** `load_genre_pack` loader and that
  `pack.seed_tropes` is populated.
- Verify that in a fresh session the existing ADR-128 deck mechanism deals into
  `active_seeds` (and emits `SPAN_SEED_DRAWN`).

**Out of scope:**
- **All engine work.** No changes to `seed_deck.py`, `seed_tick.py`,
  `session.py`, the loader, or any server/UI code. The ADR-128 mechanism is live;
  this story does not touch it.
- The other three field gaps and their stories: 77-1 (seed quest spine at
  creation), 77-2 (`record_quest`/`set_stakes` typed tools), 77-3 (promote
  `quest_anchors`), 77-4 (write-lane cleanup), 77-5 (UI quest panel). This story
  is content, independent, runs in parallel.
- Authoring seed decks for any other pack (tea_and_murder already has one; others
  are not in scope here).
- Per-world seed decks or world-specific seed overrides — the deck is genre-tier
  by design; do not split it per Oz/Wonderland/Gulliver.
- Macro/long-arc `tropes.yaml` for wry_whimsy — that file already exists and is a
  **different engine** (long-lived macro tropes, not the short-arc seed deck).
  Seeds are a sibling, not an extension of it.

## AC Context

The story's `acceptance_criteria` and `description` fields are **null** in the
sprint YAML — there is no authored AC list to expand. Derive the acceptance gate
from the epic's 77-6 carve-out (ADR-137 §active_seeds carve-out, AC-6) and
ADR-128. The implicit ACs and their verification:

1. **A wry_whimsy seed deck exists and is genre-true.**
   `genre_packs/wry_whimsy/seed_tropes.yaml` contains a deck of portal-fairytale
   seed tropes (a dozen-plus), each a vague baited hook hooking the genre FORM
   (threshold, unaccountable custom, a small wrongness in a vivid place), with no
   world-specific proper nouns (no Oz/Wonderland/Gulliver canon names).
   *Verify:* read the file; sanity-check tone against the genre `lore.yaml`
   premise and the tea_and_murder precedent's authoring quality (vague-on-purpose,
   three delivery_hints, a narrative_hint covering engaged-vs-ignored).

2. **The pack still loads via the real loader and surfaces the deck.**
   *Verify:* `load_genre_pack(wry_whimsy)` succeeds (every entry validates against
   `SeedTrope`, `extra="forbid"` so a typo'd key fails loudly) and
   `pack.seed_tropes` is non-empty. `pf validate pack` PASS alone is insufficient
   — run the loader.

3. **The existing ADR-128 mechanism populates `active_seeds` from the deck.**
   *Verify:* a fresh wry_whimsy session's `ensure_initial_draw` deals an opening
   hand into `snapshot.active_seeds` (non-empty after turn 1) and emits a
   `SPAN_SEED_DRAWN` span per drawn seed — the GM-panel confirmation the deck is
   actually engaged. No engine change is required for this to happen; if it does
   *not* happen with the deck authored, the cause is the content (e.g. an
   unparsed file or empty list), not the engine.

**AC ambiguity to flag for TEA/Dev:** because the fields are null, there is no
authored deck-size target. Use the tea_and_murder precedent (25 seeds) as the
quality bar and ship a comparable-depth deck; do not ship a token 3-seed deck
that exhausts in one session. Confirm exact count expectation with the SM/Keith
if it becomes a review point.

## Assumptions

- wry_whimsy is a live, wired pack (`genre_packs/wry_whimsy/` with `oz`,
  `wonderland`, `gulliver` worlds) — confirmed present on disk; this story does
  not create the pack, only adds its seed deck.
- The ADR-128 seed mechanism is live and unchanged: `SeedDeck` (`seed_deck.py`),
  `ensure_initial_draw` / `draw_engaged_seed` / `tick_seeds` (`seed_tick.py`),
  wired from `websocket_session_handler.py`, with `active_seeds`/`seed_ghosts` on
  the snapshot (`session.py:690`) — confirmed in code.
- Verification runs against a current server + content tree. Per project memory,
  a content tree that lags develop won't reload the new deck without a server
  bounce; pull/restart before measuring "active_seeds is still empty."
