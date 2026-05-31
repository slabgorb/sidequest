# Narrative

## Problem Statement
**Problem:** The game engine's genre-pack loader was hard-wired to require shared flavor files (lore, cultures, archetypes, theme, visual style, audio) at the genre level — meaning every world within a genre inherited the same flavor, whether that made sense or not. A world set in 1878 Pittsburgh (`the_real_mccoy`) used the same cultural tropes, lore fragments, and atmosphere files as a world on the Mexican border, because both belong to the `spaghetti_western` genre pack. The loader crashed if those genre-level files were absent, making it impossible to delete them or move them closer to the individual worlds that actually needed them.

**Why it matters:** SideQuest's core promise is that every world feels distinct. That promise breaks if the engine demands all worlds in a genre share the same flavor DNA. Keith's 2026-05-30 architecture call made it official: genre packs should hold **mechanics only** (the dice system, resolution rules, encounter tables). Everything a player sees, hears, and reads — the flavor — belongs at the world level. This story removes the loader-level barrier that was preventing that migration.

---

## What Changed
Imagine a recipe binder where every recipe in the "Italian" section was forced to start with the same paragraph about tomatoes — even if you were making tiramisu. That's what the old loader did: every world in a genre had to carry the genre's flavor chapter, word for word.

After this change, the genre binder no longer includes a mandatory flavor chapter. Each recipe (world) can bring its own flavor introduction, or borrow from the genre's if it hasn't written one yet. The binder still refuses to print a recipe with no flavor at all — it just stops demanding that flavor come from the shared genre shelf.

Concretely:
- **Lore**: The narrator no longer seeds its memory with genre-level lore fragments. It reads only from the world's own lore files.
- **Theme, audio, visual style**: These now load from the world directory first. The genre file is a fallback during the transition period, not the source of truth.
- **Weather**: Moved from the genre pack root into each world's own folder.
- **Crash prevention**: The engine no longer crashes if a genre pack has no flavor files. It only crashes if a *world* ends up with no theme at all — which is the right invariant.
- **Observability**: Every time the engine reads world-tier flavor (theme, audio, visual style), it now emits a telemetry span so the GM dashboard can confirm it's reading the right source.

---

## Why This Approach
The refactor follows a "make genre optional, world authoritative" pattern rather than a big-bang migration. Here's why that's the right order:

1. **Deletion is irreversible.** The eventual goal is deleting flavor files from the genre tier entirely. But you can't safely delete files the loader requires. This story makes the loader tolerant of absence first — so the subsequent deletion (a later story) is a one-way door with the safety net already in place.

2. **Backward compatibility is non-negotiable.** All 10 live genre packs still load cleanly. The world-flavor loading is additive: if a world has its own theme, it wins; if it doesn't, the genre fallback keeps the lights on until the per-world migration writes real world themes. Zero crashes, zero regressions in 9,246 test cases.

3. **Raw loading over strict validation — for now.** The world-tier flavor files are hand-authored per world and don't always conform to the same schema as genre-tier files. (`spaghetti_western/worlds/five_points/audio.yaml` is a free-form urban-Irish palette that fails the genre audio schema on 48 fields.) Loading world flavor as raw data and letting typed consumers sort it out is the pragmatic call; locking it to genre schemas would crash real content today.

4. **Observability before migration.** Every moved surface emits a telemetry span before the migration stories run. That means the GM dashboard can flag any world that's still reading genre-tier flavor versus world-tier flavor — making the migration auditable rather than a leap of faith.

---

## Before/After
| Surface | Before (genre-tier mandatory) | After (world-tier authoritative) |
|---|---|---|
| **Lore seeding** | `seed_world_lore` seeded genre lore first (`genre_added == 3` for a 3-file pack) | `genre_added == 0`, always. Narrator memory is world-local only. |
| **Theme** | Loaded from `genre_packs/<pack>/theme.yaml` — required, crash on absence | Loaded from `worlds/<world>/theme.yaml` (world authoritative); genre theme is a transition-period fallback; missing both raises a world-scoped error naming the world |
| **Audio** | Loaded from `genre_packs/<pack>/audio.yaml` — required, crash on absence | Genre-tier load is optional (absent → `None`); world-tier raw load added; audio backend guards `None` gracefully |
| **Visual style** | Loaded from `genre_packs/<pack>/visual_style.yaml` — required | Genre-tier load is optional; world-tier raw load emits an OTEL span |
| **Weather** | Read from `genre_packs/<pack>/weather.yaml` (pack root) | Read from `genre_packs/<pack>/worlds/<world>/weather.yaml` (world directory) |
| **Cultures / archetypes** | Required at genre tier — crash on absence | Optional; absence returns `None` on `GenrePack`; world migration to follow |
| **Engine behavior on missing genre flavor** | `FileNotFoundError` / `GenreLoadError` at startup | Clean load — genre flavor absent means optional, not broken |
| **OTEL coverage** | No spans for world-tier flavor reads | `world_theme`, `world_audio`, `world_visual_style` `state_transition` spans per world load |
| **Type contract** | `GenrePack.lore`, `.theme`, `.audio` — non-optional typed fields | `Optional[...]` fields; `World.theme: GenreTheme \| dict[str, Any] \| None` (explicit dict-vs-model split for consumer `isinstance` branching) |
