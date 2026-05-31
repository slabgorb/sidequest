---
id: 22
title: "WorldBuilder Maturity"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [48, 51, 90, 103]
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-022: WorldBuilder Maturity

> Ported from sq-2. Language-agnostic campaign initialization.

## Context
Starting a new campaign "from zero" is slow. Players want to jump into an established world.

## Decision
WorldBuilder applies cumulative `HistoryChapter` snapshots from genre packs to seed GameState at different maturity levels.

### Maturity Levels
| Level | Description |
|-------|-------------|
| FRESH | Blank slate, world just created |
| EARLY | Basic NPCs and quests established |
| MID | Ongoing storylines, known factions |
| VETERAN | Rich history, complex relationships |

### History Chapters (YAML)
```yaml
history:
  - maturity: EARLY
    npcs_added: [...]
    quests_active: [...]
    lore_established: [...]
  - maturity: MID
    npcs_added: [...]
    tropes_active: [...]
```

Chapters are cumulative — MID includes everything from EARLY.

### API
```rust
pub struct WorldBuilder;

impl WorldBuilder {
    pub fn build(pack: &GenrePack, maturity: Maturity) -> GameState {
        let mut state = GameState::default();
        for chapter in pack.history.iter().filter(|c| c.maturity <= maturity) {
            chapter.apply(&mut state);
        }
        state
    }
}
```

## Consequences
- "In medias res" starts are easy — pick MID or VETERAN
- Genre packs define campaign depth without code
- Useful for testing: `WorldBuilder::build(&pack, Maturity::Veteran)` creates rich test state

## Amendment (2026-05-31): Live Arc System — Cadence, Beats Formula, Authored-NPC Preload

The body above (and its Rust sketch) describes the **one-shot chargen concept**: a `WorldBuilder` that applies cumulative `HistoryChapter`s once at a chosen maturity to seed an "in medias res" start. That is real and still live — but it is only the seeding half of what shipped. The production reality is a **continuously re-derived arc system** that the original ADR never captured. This amendment records the live decisions, all in `sidequest-server/sidequest/game/world_materialization.py` (the Rust crate API in the body is historical per ADR-082; the code below is the canonical implementation).

### Cumulative, idempotent materialization at a target maturity

`WorldBuilder` (`world_materialization.py:201`) is the fluent builder: `at_maturity` (`:215`), `with_chapters` (`:220`), `build` (`:225`). `build` filters chapters cumulatively — every chapter whose tier is **at or below** the target applies (`:239-244`, via `CampaignMaturity.from_chapter_id` at `:111` and the `__le__`/`_ordinal` ordering at `:126-139`) — applies each in order (`_apply_chapter`, `:256`), then stores the applied set on `snap.world_history` so saves round-trip it (`:249`). Maturity tiers are `Fresh`/`Early`/`Mid`/`Veteran` (`CampaignMaturity`, `:75`). Re-running is idempotent: `_apply_npc` upserts by name (`:479`), `_apply_trope` upserts by definition id (`:554`), lore dedups (`:281-283`), and tropes/NPCs already canonical are left untouched.

The chapter DTOs live in `sidequest/game/history_chapter.py` (`HistoryChapter`, `ChapterCharacter`, `ChapterNpc`, `ChapterNarrativeEntry`, `ChapterTrope`) — split out from `session.py` to break the materialization ⇄ snapshot circular import (`history_chapter.py:1-13`). They reject unresolved `{{ }}` template markers loudly (`history_chapter.py:22-39`) — a content-authoring tripwire, not a substitution engine.

### Effective-turn formula — beats accelerate maturity

Maturity is **not** a fixed authoring choice at runtime; it is derived from live play. `CampaignMaturity.from_snapshot` (`:90`) computes `effective = round + beats // 2` (`:102`) and bands it: `<=5` Fresh, `<=20` Early, `<=50` Mid, else Veteran (`:103-109`). The `beats // 2` term means a dramatic early game — many fired narrative beats — **matures the world faster** than turn count alone, so the arc reflects intensity, not just elapsed turns.

### Cadence recompute — the production reality the original ADR missed

The seed-once builder is only invoked at chargen. Nothing re-derived maturity as play continued, so a long session stayed frozen at whatever it was seeded with. The fix is a **cadence**:

- `ARC_RECOMPUTE_INTERVAL = 5` (`:602`) and `should_recompute_arc(interaction)` (`:605`) — fires every 5 interactions; interaction `<= 0` never ticks (`:615-617`), so the chargen materialization site doesn't double-fire.
- `recompute_arc_history(snapshot, chapters)` (`:620`) wraps the in-place `materialize_world` (`:721`), which re-derives maturity from the **current** snapshot (live `turn_manager.round` + `total_beats_fired`), re-filters chapters at-or-below the new tier, and promotes newly-applicable chapters into `snapshot.world_history` / `snapshot.campaign_maturity` (`:731-748`). It returns the diff of newly-promoted `HistoryChapter`s (`:693-713`) so the dispatch site can write their narrative log + lore into the durable store.

Wiring is end-to-end, not just present: `sidequest/server/websocket_session_handler.py:1012` calls `should_recompute_arc(snapshot.turn_manager.interaction)` after the interaction bump, then `:1013` calls `recompute_arc_history(...)`, then seeds promoted-chapter lore (`:1014-1029`).

### OTEL — the lie detector for the arc

Per CLAUDE.md's OTEL Observability Principle, the recompute emits spans defined in `sidequest/telemetry/spans/world.py:20-21`:

- `world_history.arc_tick` (`world_materialization.py:678-691`) — fires on **every** cadence call, carrying `from_maturity`/`to_maturity`, `chapters_before`/`chapters_after`, `tier_changed`, and `cadence_interval`. A stable-tier no-op is still observable, so the GM panel can confirm the tick ran rather than silently skipped.
- `world_history.arc_promoted` (`:702-711`) — fires **only** on an upward tier crossing, carrying `chapters_added` (the promoted ids). This is the filtered "something meaningful happened" signal (Fresh→Early, Early→Mid, Mid→Veteran).

`materialize_world` keeps its own `world.materialized` span (`:737`) so chargen-time seeding remains observable too.

### The motivating bug

The cadence exists because of a concrete playtest failure documented in-code (`:586-600`): a Playtest 3 (2026-04-19) session reached **turn 72 still reporting `campaign_maturity="Fresh"`** with only four chapters covering turns 1-30. The chargen path materialized exactly once and **no subsequent caller ever re-invoked `materialize_world`** — so the world's history was frozen at its seed state through 70+ turns of play. The diagnosis, recorded at `:592-593`, is blunt: *"the bug is the cadence, not the formula."* The formula was always correct; nothing was calling it again.

### Authored-NPC preload seam

`preload_authored_npcs(state, authored)` (`:785`) seeds a world's `AuthoredNpc`s into `state.npcs` as runtime `Npc`s on **fresh sessions only**, discriminated by the absence of a seated player character (`state.characters == []`, `:825`) — the chargen first-commit appends the PC *after* this runs. Resumed sessions skip and emit `npc.authored_load_skipped` with a `reason` (`:826-836`) rather than silently no-opping (No Silent Fallbacks); each loaded NPC emits `npc.authored_loaded` (`:877-888`). Story 71-7 deliberately removed the old `interaction == 0` gate (`:798-804`): a freshly materialized `TurnManager` baselines at `interaction == 1`, so that clause was unsatisfiable and silently skipped the authored crew on every real fresh session. Production caller: `sidequest/server/websocket_handlers/chargen_mixin.py:786`.

### Auto-description refresh and parse discipline

`_apply_character` (`:323`) refreshes an **auto-generated** `"A {race} {class}"` description (`_auto_description`, `:49`) when a chapter changes race or class without supplying a new description (`:398-424`), emitting `world_materialization.description_refreshed`; hand-authored descriptions (anything not matching the exact auto-template via `_is_auto_description`, `:59`) are left untouched. Parsing failures are loud: `parse_history_chapters` (`:166`) raises `HistoryParseError` (`:152`) on a non-mapping payload, a non-list `chapters`, or any chapter that fails `model_validate` — the dispatch layer decides whether to log-and-continue or propagate, rather than hiding a malformed history behind a silent empty list.

**Status note:** `implementation-status` remains `live` — the seeding concept the original ADR described is live, and the cadence/beats/OTEL/preload additions documented here are likewise live in production code paths (wired through `websocket_session_handler.py` and `chargen_mixin.py`). This amendment is a documentation catch-up, not a scope change.
