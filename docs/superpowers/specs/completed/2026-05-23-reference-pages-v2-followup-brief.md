# Reference Pages v2 — Lobby Surface + Panel Hyperlinks Brief

**Status:** Brief, awaiting brainstorming
**Date:** 2026-05-23
**Predecessor:** `2026-05-23-reference-pages-design.md` (v1, shipped)

## Prompt for the next session

> The reference-pages v1 surface is live: two server-rendered pages
> (`/reference/rules/<pack>`, `/reference/lore/<pack>/<world>`) plus two
> anchor buttons in `NarrativeWidget`. The v1 spec deferred three pieces to
> iteration 2 that must land together because they have a forced
> bundling. This brief is the kickoff — use the brainstorming skill to
> turn it into a v2 spec, then write a plan.

## What's already in place (don't rebuild)

- **Server:** `sidequest-server/sidequest/server/reference_renderer.py` and
  `reference_routes.py`. Routes `GET /reference/rules/{pack}` and
  `GET /reference/lore/{pack}/{world}` return HTML built by walking on-disk
  YAML. Every heading (`<h2>`, `<h3>`) already has a stable slugified
  `id` attribute — *anchors are already there, they just aren't linked from
  anywhere*.
- **Wired router:** `app.include_router(create_reference_router())` in
  `sidequest-server/sidequest/server/app.py`.
- **UI:** `sidequest-ui/src/components/ReferenceLinks.tsx` and wiring in
  `NarrativeWidget.tsx` + `GameBoard.tsx`. Currently the *only* UI entry
  points — and only when a session is active.
- **Stylesheet:** `sidequest-server/sidequest/server/static/reference/reference.css`.
- **Hard-excluded files (v1):** `npcs.yaml`, `seed_tropes.yaml`,
  `prompts.yaml`, and 10 system/metadata files. See `EXCLUDED_FILES` in
  `reference_renderer.py`.

## The forced bundle

The v1 spec explicitly states: when we wire game-UI panels to hyperlink
into reference pages, the audience widens from "Keith-only" to "the
playgroup." That triggers two things that **must ship in the same iteration:**

1. **Panel hyperlinks** (the visible feature)
2. **Spoiler filter** (the safety net that makes the visible feature OK)

A v2 that ships hyperlinks without a filter hands players the spoiler-laden
files we file-level-excluded in v1 — because anchors *into* sections
implicitly invite browsing the rest of the page, and the rest of the page
gets richer when iteration 2 re-includes `npcs.yaml` and `seed_tropes.yaml`
with public projections.

**The lobby surface** is a third deliverable that doesn't strictly *need*
the filter (it's a static dump like v1), but it's natural to bundle
because:
- It lives in the same code path
- It expands the audience to "any browser the playgroup opens before play"
- Same hyperlink-anchor mechanics apply

## Goal of v2

Three deliverables, one iteration:

### A. Audience filter (the safety net)

- Add an `audience` parameter to `assemble_rules_page` and
  `assemble_lore_page`. Default: `player`. Other valid value: `gm`.
- Surfaced via URL: `/reference/rules/<pack>?audience=gm`. Default is
  `player` if the param is absent or invalid.
- **Player projection** of `npcs.yaml`: name + `public_description` only.
  Hide `hidden_agenda`, scenario beliefs (`belief_state` from ADR-053),
  clue-graph edges, secret_relations, etc.
- **Player projection** of `seed_tropes.yaml`: skip entirely (escalation
  structure is a spoiler even in summary).
- **GM mode**: show everything, including currently-excluded files.
- Identity source for audience: open question — see below.

### B. Panel hyperlinks (the visible feature)

- Class signature ability buttons (in `CharacterSheet.tsx`) should
  hyperlink to `/reference/rules/<pack>#class-<slug>-signature-<slug>`.
- Rule callouts (e.g. mention of an Edge cost in narration) — also
  hyperlinks. Probably needs a small `<ReferenceAnchor pack="..." section="..." />`
  React component that renders `<a target="_blank">` with the right URL.
- Anchor IDs are already stable (per v1's `slugify`). The work is the
  *reverse lookup*: from a piece of game data (class name, ability name,
  rule name), construct the URL+anchor.
- **Hard requirement:** clicking these links must NOT consume a turn,
  send a WebSocket message, or alter game state. Same constraint as v1.

### C. Lobby surface

- Add Rules + Lore buttons (or a small "Reference" panel) to
  `ConnectScreen.tsx` and/or the lobby card list, so players can browse
  *before* a session starts.
- Pack picker mechanics: probably default to the pack selected in
  ConnectScreen's pack dropdown; clicking a pack in the lobby grid could
  also expose its reference.
- Optional: an index page at `GET /reference/` listing all known packs
  with summary + links. Probably yes — gives a discoverable landing for
  bookmark-followers.

## Hard constraints (don't violate)

1. **No origin-side auth.** Cloudflare Zero Trust is the gate. The
   `?audience=gm` query param is an *application-level* role distinction
   for users who are already authenticated to the tunnel — not a security
   boundary. (See memory: `project_auth_cloudflare_zero_trust.md`.)
2. **No silent fallbacks.** If a hyperlink targets a section that doesn't
   exist (e.g. a class was renamed but the panel was cached), the route
   must 404 loudly or render with a clear "anchor not found" marker — not
   silently scroll to the page top.
3. **Hyperlinks must not consume turns.** Pure anchor navigation,
   `target="_blank"`, no JS handlers that touch game state.
4. **No content-coupled tests.** Per project rule: don't load live
   `genre_packs/*` and assert specific class names exist. Use fixture
   packs + a separate validator for live content.

## Open design questions (resolve at brainstorming)

1. **Who decides audience?** Options:
   - URL param only (`?audience=gm`) — trivially shareable, no auth needed,
     but a curious player can flip the URL to spoil themselves
   - Per-identity flag (Keith is GM, others are players) — requires reading
     `Cf-Access-Authenticated-User-Email` from Cloudflare and mapping it
     to a role
   - Session-bound (the player who is `is_gm=True` in the live session sees
     GM mode) — solid but ties reference auth to active session state,
     which breaks bookmark/pre-session use
   - Hybrid: default by identity, override by URL param (Keith can still
     "view as player" for testing)
2. **What goes in `public_description` for NPCs?** Authoring contract —
   probably needs a `public_description: str` field added to npcs.yaml
   schema, with a content-team backfill pass. Could fall back to `name`
   if missing.
3. **How are panel hyperlinks discovered by the panel components?**
   Options:
   - Hardcoded URL builders in each component (`/reference/rules/${pack}#class-${slugify(name)}-signature-${slugify(ability)}`) — DRY-ish if extracted to a `referenceUrl(pack, kind, ...args)` helper
   - Server-emitted hrefs in the data the panels render — e.g. each
     ability comes with a `reference_url` field
   - Slug-aware client helper that mirrors the server's slugify rules
     (risk: drift between client and server slug generation)
4. **Lobby pack picker:** does the lobby surface show ALL packs (browse
   anything before committing), or only the currently-selected pack?
5. **Should the lobby surface need a `world` for the Lore button?** Without
   a world selected, the Lore link is dead. Either gate the link on
   world-pick, or default to the first world in the pack.
6. **Pack-themed stylesheet integration** (was iteration 2 in v1 spec):
   bundle here or defer further? Probably defer — v1 stylesheet is fine,
   pack theme is polish.

## Out of scope for v2 (defer further)

- Markdown rendering inside YAML string values (would be a v3 polish)
- Search across packs ("find the rule that says X")
- Inline edit / authoring flow
- Comments / annotations from players
- Mobile-specific layout (the desktop layout is the playgroup's primary
  surface)

## Acceptance criteria (draft — brainstorming should refine)

1. `/reference/rules/tea_and_murder?audience=gm` returns content from
   `npcs.yaml` and `seed_tropes.yaml`; without the param, it does not.
2. The character sheet's class signature ability buttons hyperlink to
   the correct rules page anchor and open in a new tab.
3. Clicking any reference hyperlink during a session does NOT post a
   WebSocket message or alter game state.
4. A player at `ConnectScreen` can navigate to `/reference/rules/<pack>`
   for any pack visible in the lobby, without joining a session.
5. `/reference/` (root index, if implemented) returns 200 with a list
   of available packs.
6. Bad/unknown anchors render with an explicit "anchor not found" marker,
   not a silent scroll-to-top.
7. `just check-all` passes.
8. Spoiler invariant: with no `?audience=gm`, no playtester should be
   able to read `npcs.yaml` hidden fields or `seed_tropes.yaml` contents
   via any reference URL.

## How to start

1. Read this brief.
2. Read the v1 spec (`2026-05-23-reference-pages-design.md`) for the
   architecture context — especially the "Iteration 2" section, which
   this brief expands on.
3. Read the relevant code so you know the surface:
   - `sidequest-server/sidequest/server/reference_renderer.py` (in particular `EXCLUDED_FILES`, `assemble_rules_page`, `assemble_lore_page`)
   - `sidequest-server/sidequest/server/reference_routes.py`
   - `sidequest-ui/src/components/ReferenceLinks.tsx` and its wiring in
     `GameBoard/widgets/NarrativeWidget.tsx`
   - `sidequest-ui/src/screens/ConnectScreen.tsx` (lobby integration target)
   - `sidequest-ui/src/components/CharacterSheet.tsx` (panel hyperlink target)
4. Use the `superpowers:brainstorming` skill to turn this brief into a
   v2 spec. Resolve the open design questions with the user *before*
   committing to a plan.
5. Then `superpowers:writing-plans` for the implementation plan.

## Size estimate (rough)

v1 was 5 points. v2 is bigger because of the audience filter scoping
work and the per-component anchor wiring. Rough first guess: **8 points**.
Brainstorming will refine — if the identity-source question pushes us
toward reading Cloudflare headers, that's its own +2 points and probably
warrants splitting into two stories.
