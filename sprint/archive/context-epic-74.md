# Epic 74: Genre tier = mechanics only

## Overview

Genre packs must hold **mechanics only**. All *flavor* — lore, cultures, archetypes,
theme, visual_style, audio, weather, and tropes — moves to the **world** tier. The genre
defines *how the game plays*; the world defines *what it feels like*. This epic delivers
the server loader/consumer refactor that makes the move possible, the trope-engine change
to read world tropes, and the per-world content migration that follows.

**Priority:** P2
**Repo:** sidequest-server + sidequest-content
**Stories:** 1 seeded (74-1); trope-engine + per-world migration stories to follow.

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Genre-Pack Content Audit** (`docs/genre-pack-content-audit.md`) | Whole doc — loader semantics, per-file mechanics-vs-flavor taxonomy, decisions, Part 2 server-change table, sequencing |
| **ADR-003 Genre Pack Architecture** (`docs/adr/`) | Pack/world layering this epic revises |
| **ADR-004 Lazy Genre Binding** (`docs/adr/`) | Load path being refactored |
| **ADR-018 Trope Engine** (`docs/adr/`) | Trope consumer that must switch genre→world |
| **ADR-091 Culture-Corpus Markov Naming** (`docs/adr/`) | Cultures consumer (already world-preferring) |

## Background

**Why this epic exists.** Keith (2026-05-30): *"I do not want any flavor at the genre!
Flavor is in the world, not the genre — even shared weather, holidays, calendar."* The
trigger was concrete: spaghetti_western's genre-tier tropes are authored for the
Mexican border (dust_and_lead) but are applied unchanged to 1878 Pittsburgh
(the_real_mccoy) and 1850s NYC (five_points). Shared genre flavor isn't just redundant —
it's *actively wrong* across a genre's divergent worlds.

**Current state (from the audit).** A full loader trace + source grep established three
realities:

1. **Some genre-tier files are already dead** and were expunged in Part 1
   (sidequest-content PR #299): `places.yaml`, `spellbook.yaml`-superseded peers,
   genre-tier `openings.yaml`/`history.yaml`/`cartography.yaml`, and the 1,368-line
   spaghetti `calendar.yaml` — which was *intentional, valuable flavor misfiled at the
   genre tier* (a pack-tier loader from story 24-7 never shipped, so it sat inert). It
   was split + slimmed into `worlds/dust_and_lead/calendar.yaml` +
   `worlds/the_real_mccoy/calendar.yaml`, where the live `load_world_calendar` reads it.

2. **The remaining flavor files are MANDATORY genre-tier loads.** `load_genre_pack`
   (`sidequest-server/sidequest/genre/loader.py`) hard-requires `lore.yaml`, `theme.yaml`,
   `archetypes.yaml`, `cultures.yaml`, `visual_style.yaml`, `audio.yaml`, `tropes.yaml`,
   `prompts.yaml` via `_load_yaml(path / "X.yaml", …)` — deleting any raises
   `GenreLoadError`. **You cannot delete them without changing the loader first.** That is
   what blocks the mechanics-only end state and is the core of story 74-1.

3. **Consumer behavior already leans world-ward for some files but not others:**
   - `lore` — **MERGED** (genre + world both seeded into the LoreStore;
     `game/lore_seeding.py:220-230`). Genre lore reaches the narrator of every world.
   - `cultures`, `archetypes` — **FALLBACK** (world wins if present;
     `cli/namegen/namegen.py:267-281`, `server/dispatch/culture_context.py:53-66`,
     `genre/archetype/shim.py:117-158`). Every live world already authors its own, so the
     genre fallback is never taken in-session — *except* `space_opera/perseus_cloud`,
     which has no archetypes.
   - `theme`, `visual_style`, `audio` — **GENRE-ONLY** today; no world-tier loader exists.
   - `weather` — **GENRE-TIER read** (`game/world_grounding_loader.py:47`,
     `load_pack_weather(pack_dir)`).
   - `tropes` — the trope engine reads `genre_pack.tropes` directly
     (`server/session_helpers.py:1103`, `game/trope_tick.py:91`,
     `agents/tool_registry.py:115`); 8/10 packs author **zero** world tropes today.

## Technical Architecture

**Load path under change:** `sidequest-server/sidequest/genre/loader.py`
(`load_genre_pack` for genre tier, `_load_single_world` for world tier) plus the per-file
consumers listed above.

**Target end state — genre tier carries mechanics only:** `pack.yaml`, `rules.yaml`,
`progression.yaml`, `axes.yaml`, `power_tiers.yaml`, `lethality_policy.yaml`,
`visibility_baseline.yaml`, `classes.yaml`, `chassis_classes.yaml`, `inventory.yaml`,
`char_creation.yaml`, `archetype_constraints.yaml`, `projection.yaml`, `pacing.yaml`,
`achievements.yaml`, `backstory_tables.yaml`, `equipment_tables.yaml`, `seed_tropes.yaml`,
`magic.yaml`/`spells/`, `prompts.yaml` (scaffold; see boundary note), `beat_vocabulary.yaml`
(boundary). Everything flavor lives under `worlds/<world>/`.

**Required server changes (per file — full table in the audit doc):**

| File | Today | Change |
|---|---|---|
| `lore.yaml` | mandatory genre + mandatory world (merged) | make genre lore optional → stop seeding genre tier; world lore authoritative |
| `cultures.yaml` | mandatory genre (fallback) | make genre optional / world-only; drop genre fallback |
| `archetypes.yaml` | mandatory genre (fallback) | make genre optional / world-only; **author `perseus_cloud` archetypes first** |
| `theme.yaml` | mandatory genre, no world loader | add world-tier loader; world-authoritative |
| `visual_style.yaml` | mandatory genre, no world loader | add world-tier loader; render pipeline reads world |
| `audio.yaml` | mandatory genre, no world loader | add world-tier loader; `_resolve_audio_urls` + audio engine read world |
| `weather.yaml` | optional, pack-tier read | switch `load_pack_weather` → world tier |
| `tropes.yaml` | engine reads `genre_pack.tropes` | engine reads world tropes; per-world decks authored (own story) |

**Invariants / guardrails:**
- **No Silent Fallbacks** — a world missing a now-required flavor surface must fail *loud*
  at load, not silently degrade. Mirror the existing required-file pattern
  (`visibility_baseline`, `lethality_policy`).
- **OTEL** — every world-tier flavor load emits a watcher event (mirror the existing
  `world_items` / `genre_pack` `state_transition` spans in `loader.py`) so the GM panel
  can prove world-tier loading actually fired.
- **Wiring test** — at least one integration test per moved surface proving the world-tier
  load reaches its consumer (per CLAUDE.md "Every Test Suite Needs a Wiring Test").

**Boundary cases (need a ruling before they move):** `tropes.yaml` (Keith confirmed it's
the core problem — moves to worlds), `prompts.yaml` and `beat_vocabulary.yaml` (mechanical
skeleton vs flavor prose — pending ruling). The `validate pack` `extensions:` manifest is a
validation-only construct (not read at runtime) and must be updated alongside any file move.

## Cross-Epic Dependencies

**Depends on:**
- Part 1 (sidequest-content PR #299) — dead-file expunge + calendar world-tier move; ships first.

**Depended on by:**
- Per-world content migration (author flavor into each world) — blocked until 74-1 makes
  the genre-tier loads optional / world-tier.
- Trope per-world authoring — blocked until the trope-engine reads world tropes.
- Epic 64 (Content Schema Compliance) overlaps on the `extensions:` validator manifest.
