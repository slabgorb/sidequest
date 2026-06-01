# Lore Reference Pages — Images + Public Table Projection (Design)

**Status:** Design — awaiting user review, then `writing-plans`
**Date:** 2026-06-01
**Author:** Architect (Neo)
**Epic:** 65 — Content Infrastructure (R2 asset tracking and audit)
**Predecessors:** epic 63 (reference pages v1 + chrome), stories 65-1/65-5/65-6 (manifest + R2 listing + portrait resolver, all done)
**Supersedes:** the audience-filter (`?audience=gm`) model in `2026-05-23-reference-pages-v2-followup-brief.md` — see §0.
**Related / out of scope:** epic 74-3 (world-tier lore authoring — content smoothing)

## 0. Framing — this is a TABLE TOOL, and it is unconditionally public

In SideQuest the **AI is the GM/narrator**; every human at the table is a **player**
(the project exists so the forever-GM can finally *play*). There is **no human GM seat at
the table**, so a "GM audience" on this surface is incoherent. The full, keeper-side view
of a world already exists in two other places: **the YAML files themselves**, and the
**future world-building/authoring tools**. Those are the GM/author surfaces.

The reference pages are therefore **the table tool**: a single, **unconditionally public**
projection. There is **no `?audience` parameter, no identity/role resolution, no GM mode
toggle.** The only distinction that exists anywhere is public-vs-keeper, and this surface
is *always* the public side (`public=1`, implicitly and unflippably). The v2 brief's
`?audience=gm` filter was built on the now-deprecated assumption that one player at the
table is "the GM"; that premise is false and this design drops it entirely. The spoiler
firewall remains — but as a **fixed projection nobody on this surface can flip**, not a
toggle.

---

## 1. Problem

The server-rendered lore page (`GET /reference/lore/{pack}/{world}`) is image-poor and
content-thin, despite the assets and the wiring already existing:

1. **POI images never appear, even though they are live in R2.** The POI `<img>`
   emitter (`_poi_image_html`, story 63-8) only runs inside `present_lore_geography`,
   which needs a **list of location dicts**. In the live worlds (glenross,
   blackthorn_moor) `lore.yaml:geography` is authored as a **prose string**, so no
   location cards render and the POI images — confirmed present in R2 at
   `genre_packs/tea_and_murder/worlds/glenross/assets/poi/the_glenross_arms.png` (HTTP
   200) — have nowhere to attach. The POI slug manifest (`load_poi_image_slugs` ←
   `history.yaml:points_of_interest[].slug`) is built correctly and then goes unused.

2. **Portraits are never surfaced.** `npcs.yaml` and `portrait_manifest.yaml` are in
   `EXCLUDED_FILES`, and the lore renderer never calls the portrait resolver that the
   live game already uses (`_resolve_npc_portrait_url`, story 65-6). Portraits are live
   in R2 for six worlds (blackthorn_moor, aureate_span, annees_folles, long_foundry,
   burning_peace, shattered_accord) — glenross is **not** among them (negative-test
   world).

3. **No existence gate.** Today the renderer would have to guess R2 paths and rely on a
   404 as the only signal. glenross has a `portrait_manifest.yaml` listing 13 characters
   but **zero portraits in R2** — naive rendering = 13 broken images.

4. **The contents rail is broken for `tea_and_murder`.** Both worlds collapse to a single
   TOC entry ("I. The House"); every other section (history, cosmology, factions, the
   ad-hoc lore keys) renders as **unmapped stems dumped after** the rail because
   `PACK_TOC`/`TOC_TO_FILES` is stale for this pack.

5. **(Content, not engine.)** The world lore itself is rough — authored before the
   corpus was smoothed. Ad-hoc `lore.yaml` keys (`economy`, `religion`, `transport`,
   `cosy_constraints`, `the_village_voice`) fall through the generic snake_case walk.
   **This is epic 74-3's lane, not this design's.**

---

## 2. What already exists (reuse inventory — do NOT rebuild)

| Capability | Asset | State |
|---|---|---|
| POI `<img>` with theme accent + OTEL | `_poi_image_html`, `present_lore_geography` (`reference_presenters.py`) | Works; unfed |
| POI slug source | `load_poi_image_slugs` ← `history.yaml` | Works |
| Portrait URL resolution (name→slug→manifest→R2) + OTEL | `_resolve_npc_portrait_url`, `_world_portrait_slugs` (`emitters.py`, 65-6) | Live in game; unused by ref pages |
| **Checked-in R2 manifest** + YAML-derived key set | `scripts/r2_manifest.py` (`load_manifest`), `scripts/r2_audit.py` (`expected_keys`), `r2_sync_packs.py` writes `r2_manifest.json` (65-1) | **Code done; artifact never populated/committed** |
| Live R2 existence listing | generator skip-existing check (65-5) | Done |
| Per-pack chrome / TOC / theme | `PACK_TOC`, `TOC_TO_FILES`, `reference_theme` | Works; data stale for tea_and_murder |
| Single URL seam | `resolve_asset_url` | Works |

The net: **this is a wire-up, not a build.** The only genuinely new code is (a) two thin
presenters that feed existing renderers, (b) the public npcs projection, and (c) populating +
consuming the manifest the 65-1 code already knows how to write.

---

## 3. Decisions

### D1 — One fixed public projection (no audience parameter)

The reference pages render exactly one projection — the **public** one — and there is **no
parameter, header, or toggle** that exposes more. Keeper content is reachable only off this
surface (YAML + authoring tools, per §0). This is simpler and safer than a dual-audience
filter: there is no URL to flip, no identity to resolve, no allowlist to maintain, and no
`is_gm` concept to (re)entangle (`views.py:is_gm()` is a live-session seat and irrelevant
here; story 71-35 already deleted the projection-firewall `is_gm` axis — we do not
resurrect it).

**Public projection contract (per file) — fixed, not toggleable:**

- `npcs.yaml` → **name + role + appearance + portrait image** only. `public_description`
  (optional, see below) overrides `appearance` when present. **Never rendered:** `ocean`,
  `history_seeds`, `initial_disposition`, `distinguishing_features`, and any ADR-053
  `belief_state` / clue-graph / secret-relation data wherever it lives.
- `portrait_manifest.yaml` → image source only (subject prose is authoring config, not
  shown).
- `seed_tropes.yaml` / `tropes.yaml` → **omitted entirely** (escalation structure is a
  spoiler even in summary). These stay in `EXCLUDED_FILES` permanently — nobody reads them
  through this surface.

`npcs.yaml` and `portrait_manifest.yaml` move out of `EXCLUDED_FILES` into **public-
projected inclusion**: they are included, but only ever as the projection above — never
raw-dumped.

**`public_description` is an *optional override*, not a prerequisite.** `npcs.yaml` has no
such field today. Rather than block on a content backfill across every world, the public
view derives its text from already-authored safe fields (`name`, `role`, `appearance`).
Authors MAY add `public_description: str` later to curate; the renderer prefers it when
present. This keeps the engine slice unblocked and lets 74-3 curate at leisure.

### D2 — The existing `r2_manifest.json` is the existence oracle

Consume the **65-1 manifest**, do not invent a new one. The renderer emits an `<img>` iff
the asset's R2 key is present in the manifest. This makes the page structurally incapable
of lying about a picture it doesn't have — the asset-layer equivalent of the OTEL
lie-detector principle (and it kills the glenross "13 broken portraits" failure cleanly).

**The artifact must actually be populated and committed.** 65-1 shipped the *writer*; the
artifact is absent in-clone. Slice 65-7 runs `r2_sync_packs` / `r2_audit` to populate
`sidequest-content/r2_manifest.json` and commits it so `git pull local` syncs it between
OQ-1/OQ-2 (its original cross-clone purpose).

### D3 — POI gallery feeds the existing geography renderer from `history.yaml`

The `history.yaml` POI entries already carry `name / slug / region / type / description /
environment` — the **exact shape `present_lore_geography` consumes**. Add a thin presenter
(a "Points of Interest" section) that feeds the existing card renderer from
`history.yaml:points_of_interest`, independent of the prose `geography` field. **No content
migration**, no new card markup. POI image emission stays gated on
`slug ∈ poi_image_slugs`, now additionally verified against the manifest (D2).

### D4 — Cross-repo seam: the oracle is a data artifact, never a code import

The renderer lives in **sidequest-server**; the manifest tooling lives in the
**orchestrator `scripts/`**. The server **cannot** import `r2_audit.py` across the repo
boundary, and must not grow a runtime dependency on orchestrator scripts. The server reads
`r2_manifest.json` from the content root it already mounts via `SIDEQUEST_GENRE_PACKS`.
Loading is cached per process (the manifest is static between deploys); the renderer
filters entries by `genre_packs/{pack}/worlds/{world}/...` prefix. Clean seam, no
cross-repo runtime coupling.

### D5 — Portrait/Cast surface (public projection only)

A "Cast" section renders NPCs under the single D1 public projection — name + role +
appearance + portrait, nothing else, for everyone. Portrait `<img>` reuses the 65-6
resolver's slug+path convention (`.../worlds/{world}/assets/portraits/{slug}.png`),
manifest-gated (D2).

### D6 — TOC/section-mapping repair

Correct `PACK_TOC`/`TOC_TO_FILES` for `tea_and_murder` and register the two new sections
(Points of Interest, Cast) so the contents rail reflects the page instead of dumping
unmapped stems after it. Scope-limited to the data + the two new section ids; the
generic-walk normalization of ad-hoc lore keys is **74-3 content work**, not here.

### D7 — Two-reader presentation principle (adopt now; costs nothing)

The page has **two simultaneous readers** and must serve both on one surface without
forcing either to scroll past the other's content:

- **The narrative reader** (James, Alex) — prose, portraits, legends, the watercolor of
  the place. Already the page's default register.
- **The mechanical reader** (Sebastien, Jade) — wants the gears *visible*: a faction's
  starting disposition, the world's survivability-pool label, axis snapshot
  (scale/tone/swagger), what kind of place a POI is. This is a **player-facing** surface,
  so per CLAUDE.md exposing the math here is correct and desired — it is the Sebastien/Jade
  player-UI consideration, **not** dev observability (no OTEL/GM-panel framing belongs in
  the rendered page).

**The principle:** wherever a section already carries a **public** mechanical fact, surface
it as a legible chip/badge *alongside* the flavor — never bury it in prose, never hide it
behind a toggle. This is already half-done and proves the pattern: faction cards emit a
`disposition` badge; `world.yaml` meta emits scale/tone/swagger cells. Extend the same
instinct to the new sections (POI `type` chip is already there; Cast cards show role).
**Spoiler-safe boundary:** only *public* mechanical facts — never hidden agendas, belief
state, or any cost/edge that would reveal scenario structure (those live behind the D1
projection). This is a presenter-design rule, not new sections; it shapes how D3/D5 and the
follow-on slices render, at no extra cost.

---

## 4. Data flow (lore page, post-design)

```
GET /reference/lore/{pack}/{world}              ← no params; always the public projection
        │
        ├─ load r2_manifest.json (cached) → set of live R2 keys, prefix-filtered to this world
        │
assemble_lore_page(pack, world, manifest_keys)
        ├─ hero (world_name)                         [existing]
        ├─ § Points of Interest  ← history.yaml POIs → present_lore_geography
        │        └─ <img> iff slug-key ∈ manifest_keys              [D2+D3]
        ├─ § Cast                ← npcs.yaml public projection      [D1+D5]
        │        └─ portrait <img> iff portrait-key ∈ manifest_keys [D2]
        ├─ § History / Cosmology / Factions / …      [existing presenters]
        └─ TOC wraps sections by corrected PACK_TOC  [D6]
```

---

## 5. Invariants & observability

- **Spoiler invariant.** There is **no parameter that exposes keeper content** — the page
  renders only the public projection, always. A test asserts the render of a keeper-bearing
  fixture (hidden npc fields, `seed_tropes.yaml`, belief/clue data) contains none of the
  hidden tokens, and that no query param changes that.
- **No silent fallbacks.** Manifest absent at render → **fail loud** (the page must not
  silently render imageless as if assets don't exist); a present-but-keyless world renders
  text-only, which is correct.
- **OTEL (per CLAUDE.md).** Emit spans for: manifest load (path, key count) and each
  POI/portrait image decision (resolved | not-in-manifest). Reuse the existing
  `reference_poi_image_*` and `scrapbook_npc_portrait_*` span families; add
  `reference_manifest_loaded`. (No audience span — there is no audience.)

---

## 6. Decomposition (hand to SM / Morpheus)

| Story | Title | Repos | Pts (rough) | Depends |
|---|---|---|---|---|
| **65-7** | Populate + commit `r2_manifest.json`; establish it as the synced existence oracle | content, orchestrator | 2 | — |
| **65-8** | Lore renderer reads manifest; POI gallery feeds geography renderer from `history.yaml`; manifest-gated `<img>` | server | 3 | 65-7 |
| **65-9** | Cast/portrait surface — public npcs projection + manifest-gated portraits (no audience machinery) | server | 3 | 65-7 |
| **65-10** | TOC/section-mapping repair for tea_and_murder + register new sections | server | 2 | 65-8, 65-9 |
| **65-11** | POI **map view** — static server-rendered SVG from `cartography.yaml`, POI portraits as manifest-gated pins, click-to-card | server | 5 | 65-8, 65-10 |
| **65-12** | Unified **world timeline** — merge legends (`era`) + history (`chapters.session_range`) + POI founding into one sorted spine | server | 3 | 65-8, 65-10 |
| *(74-3)* | World-tier lore authoring / smoothing (ad-hoc key normalization) | content | — | — |

**65-11 / 65-12 are follow-on slices** (party-mode 2026-06-01): high value, low *new
content* — both render data the worlds already author (`cartography.yaml` geometry +
`region` fields; `era` / `session_range`). Captured here so the first pass (65-7…65-10)
stays scoped to images + manifest + TOC; the map and timeline land after the spine works.
Both obey D2 (manifest gate) and D7 (two-reader). 65-11 needs an `/architect` pass against
`cartography.yaml`'s real shape before it's cut.

**Pilot/verify world:** `blackthorn_moor` (the only world with **both** a live POI image
and live portraits in R2 — proves both image paths end-to-end). `glenross` is the negative
test: POIs yes, portraits no → the manifest gate must suppress the missing portraits
cleanly with zero broken images.

---

## 7. Out of scope

- Panel hyperlinks + lobby surface from the v2 brief (separable; not needed for images).
- The v2 brief's `?audience=gm` filter — **explicitly rejected** (§0), not deferred.
- World-tier lore content rewriting / corpus smoothing (epic 74-3).
- Markdown-in-YAML rendering, cross-pack search, inline authoring (v2 brief "defer further").
- UI `useAssetPreload` mount (65-4, independent).
- **Delight backlog (party-mode 2026-06-01, parked):** ambient opt-in pack music
  (`<audio>` → existing R2 OGG); conlang pronounce buttons on culture/place names (reuse
  corpus + Markov namer); played-vs-coal POI glow driven by save history (asset_ledger /
  65-2). Revisit after the spine + map/timeline ship — not in epic 65's current cut.

---

## 8. Open items for user review

1. **Rules page parity** — extend the same image/manifest treatment and the public
   projection to `/reference/rules/{pack}` this pass, or lore-only? The rules page has
   little keeper content and no per-world images, so the only shared work is consuming the
   manifest. Recommendation: keep the renderer uniform (both routes apply the public
   projection), but the *image* work is lore-only since rules pages have no POIs/portraits.
