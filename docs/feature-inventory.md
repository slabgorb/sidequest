# SideQuest Feature Inventory

**Last updated:** 2026-04-30
**Sprint 3:** Playtest 3 closeout — MP correctness, state hygiene, post-port cleanup (active 2026-04-27 → 2026-05-10)
**Sprint 3 progress:** 24/37 stories done · 55/84 points
**Sprint 3 epic:** Epic 45 (single epic; rolls up Epic 37's open backlog plus port-drift residue)

> **Post-port snapshot.** This inventory describes the **Python** backend
> (`sidequest-server`) live since the ADR-082 cutover (2026-04-23). The
> language-level Rust → Python port is complete; subsystem-level drift is
> tracked separately. For the comprehensive non-parity inventory and
> verdicts, see:
>
> - `docs/port-drift-feature-audit-2026-04-24.md` — what landed in Python and what didn't
> - `docs/adr/087-post-port-subsystem-restoration-plan.md` — verdict + tier per non-parity subsystem
> - `docs/adr/README.md` — port-era reading guide and Rust → Python translation table

## Legend

- **Live & Wired** — Implemented in Python, reachable from real session traffic, OTEL-emitting
- **Live (partial)** — Wired but not fully exercised, or has a known gap flagged by ADR-087
- **Dark** — Concept ported to Python data model only; engine missing (per ADR-087 RESTORE roster)
- **Deferred** — Intentional phased scope; marker present or covered by Proposed ADR
- **Workshop only** — Genre content lives in `sidequest-content/genre_workshopping/` and is not selectable in the UI

**Wiring diagrams:** See [`docs/wiring-diagrams.md`](wiring-diagrams.md) for end-to-end signal traces (Mermaid) showing each feature's path from UI to storage.

---

## Live & Wired (Post-Port)

These features are wired end-to-end in the Python tree and exercise OTEL spans during real sessions.

### Core Game Loop

| Feature | Server module | UI | Notes |
|---------|---------------|----|-------|
| WebSocket transport | `sidequest.server.websocket` | `useGameSocket` | FastAPI WS upgrade, reader/writer task split (ADR-038) |
| REST genres endpoint | `sidequest.server.rest` | `ConnectScreen` | `/api/genres` — pack discovery |
| Session lifecycle | `sidequest.server.session_handler` | `ConnectScreen → GameLayout` | Connect → Create → Play, pydantic-validated |
| Multiplayer rooms | `sidequest.server.session_room` | shared-world state | `SessionRoom` keyed by `genre:world` (ADR-036/037) |
| Character creation | `sidequest.game.builder` + `character` | `CharacterCreation` | Genre-driven scene state machine, three modes (ADR-016) |
| Orchestrator turn loop | `sidequest.agents.orchestrator` | `NarrativeView` | Intent → Narrator → Patches → Broadcast |
| Intent classification | `sidequest.agents.orchestrator` (state-override) | — | `in_combat`/`in_chase`/default; no LLM call (ADR-067) |
| Unified narrator | `sidequest.agents.narrator` | — | Single persistent Opus session via `claude -p` (ADR-067 supersedes multi-agent ADR-010) |
| Auxiliary agents | `sidequest.agents.subsystems/` (resonator, troper, world_builder) | — | Off the live turn critical path |
| Sidecar tool patches | `sidequest.agents.orchestrator.assemble_turn` | — | Narrator emits prose; sidecar tools write JSONL for items/mood/intent/SFX (ADR-039 / ADR-057 / ADR-059) |
| State delta computation | `sidequest.game.delta` (`compute_delta`) | `useStateMirror` | Wire-efficient state diff per turn |
| Projection filter (per-player view) | `sidequest.game.projection_filter` + `projection/` | per-client `INITIAL_STATE`/deltas | Python-era extension; OTEL `projection_decide_span` |
| Narration delivery | `sidequest.protocol.messages.NARRATION` + `NARRATION_END` | `NarrativeView` (markdown, DOMPurify) | Two-message atomic state commit (ADR-076 retired the streaming chunk leg) |
| SQLite persistence | `sidequest.game.persistence` | — | `sqlite3` via `asyncio.to_thread`; one DB per save |
| Trope state | `sidequest.game.session.TropeState` | — | **Data ported; engine `apply_trope_engagement` is dark** (ADR-087 RESTORE P1) |
| Genre pack loading | `sidequest.genre.loader` + `models/` + `resolver` | `ThemeProvider` | YAML → pydantic; lazy bind on connect (ADR-004) |
| CORS | FastAPI middleware | Vite proxy | Dev + prod |

### Multiplayer & Pacing

| Feature | Module | Notes |
|---------|--------|-------|
| Turn barrier (sealed-letter window) | `sidequest.server.session_room.TurnBarrier` | Adaptive timeout (3s for 2-3, 5s for 4+); claim-election prevents duplicate narrator calls |
| Active-turn-takers vs lobby count | story 45-2 | Closed Sprint 3 (was 37-42); barrier no longer waits on phantom lobby peers |
| Shared-world delta handshake | `sidequest.game.shared_world_delta` | Closed Sprint 3 (story 45-1, re-scope of 37-37); seeds next player's turn with location/encounter/adjacency ground truth |
| Three turn modes | `sidequest.game.session.TurnMode` | FREE_PLAY, STRUCTURED, CINEMATIC (ADR-036) |
| Party action composition | `sidequest.agents.orchestrator` | Multi-character PARTY ACTIONS block in narrator prompt |
| Perception rewriter | `sidequest.agents.perception_rewriter` | Per-player narration variants based on status effects (ADR-028) |
| Two-tier turn counter | `sidequest.game.turn` | Interaction (monotonic) vs Round (narrative) — ADR-051 |
| TensionTracker | `sidequest.game.tension_tracker` | Dual-track model — gambler's ramp + HP stakes + event spikes |
| Drama-aware delivery | `sidequest.protocol.messages.NARRATION_END` consumers | INSTANT / SENTENCE / STREAMING (drama_weight thresholds) |
| Quiet turn detection | `sidequest.game.tension_tracker` | Escalation beat injection after sustained low drama |
| Genre-tunable thresholds | `pacing.yaml` per pack | Per-pack drama breakpoints |
| Momentum readout sync | story 45-3 | UI ConfrontationOverlay reads live momentum off state mirror |

### Knowledge & Lore

| Feature | Module | Notes |
|---------|--------|-------|
| KnownFact accumulation | `sidequest.game.character.KnownFact` | Tiered injection by relevance |
| Footnote protocol | `sidequest.protocol.messages.NarrationPayload.footnotes` | Discovery / callback styling, fact_id callbacks |
| Lore store | `sidequest.game.lore_store` | In-memory indexed collection, persisted via SQLite |
| Lore RAG (embedding cosine sim) | `sidequest.game.lore_embedding` (cross-process via daemon, ADR-048) | Ported intact |
| Lore seeding from packs | `sidequest.game.lore_seeding` | Bootstrap from genre/world YAML |

### NPC & World Systems

| Feature | Module | Notes |
|---------|--------|-------|
| OCEAN profiles (data) | `sidequest.genre.models.ocean` | Five floats 0.0–10.0 on every archetype |
| OCEAN behavioral summary | `sidequest.genre.models.ocean.OceanProfile.behavioral_summary()` | Scores → prompt text |
| Narrator reads OCEAN | `sidequest.agents.prompt_framework` | Voice/behavior adjustment per NPC |
| OCEAN shift proposals | — | **Dark** — model present, evolution pipeline not ported (ADR-087 RESTORE P2) |
| Disposition (scalar) | `sidequest.game.character.npc.disposition` | Reduced to scalar int with clamping; **Attitude enum + transitions are dark** (ADR-087 RESTORE P1) |
| Faction agendas | `sidequest.game.faction_agenda` (data ported), narrator injection live | Goals + urgency feed scene directives |
| Scene directives | `sidequest.agents.prompt_framework` (early-zone) | Mandatory weave |
| Trope ticks (data) | `sidequest.game.session.TropeState` progression | Progresses each turn; **engine that fires beats from progression is dark** (ADR-087 RESTORE P1) |
| World materialization | `sidequest.game.world_materialization` | Campaign maturity (fresh/early/mid/veteran) |
| Belief state (multi-source credibility) | `sidequest.game.belief_state` | Ported intact |
| Scenario / clue graph | `sidequest.game.scenario_state` | Bottle episodes, whodunit data |
| Room-graph navigation | `sidequest.game.room_movement` | Per-room topology for dungeon worlds (ADR-055) |
| Region init / validation | `sidequest.game.region_init`, `region_validation` | Seed `snap.current_region` from world `cartography.yaml` (ADR-019 supersession residual) |
| Resource pool | `sidequest.game.resource_pool` | Thresholds + decay; underpins genre-typed resources (humanity, heat, fuel, etc.) |

### Media Pipeline

| Feature | Module | Notes |
|---------|--------|-------|
| Image generation | `sidequest.daemon_client` → `sidequest-daemon` (Flux / Z-Image, MLX) | ADR-070 |
| Render tiers | per `visual_style.yaml` | scene_illustration, portrait, portrait_square, landscape, text_overlay, fog_of_war (cartography retired 2026-04-28; tactical_sketch retired under ADR-086) |
| Subject extraction | narrator `visual_scene` (preferred) + regex fallback | — |
| Image pacing throttle | `sidequest.media` | 30s solo, 60s multiplayer (ADR-050); DM override |
| Render queue with content dedup | `sidequest.media` (SHA256) | — |
| Speculative prerender | — | **Dark** — `prerender.rs` did not port (ADR-087 RESTORE P2 / ADR-044) |
| Beat filter (drama gate) | inline in orchestrator (no standalone module) | Standalone module dark (ADR-087 RESTORE P3) |
| Scene relevance validator | — | **Dark** — REDESIGN under ADR-086 image-composition taxonomy (ADR-087 P2) |
| Music director | `sidequest.audio` (mood classify + theme select) | Mood-indexed pre-rendered ACE-Step tracks |
| Audio cue messages | `sidequest.protocol.messages.AUDIO_CUE` | `useAudioCue` on client |
| 2-channel audio | `sidequest-daemon` (pygame mixer) | Music + SFX only (no voice/TTS — ADR-076) |
| Theme rotator (anti-repetition) | — | **Superseded** per ADR-087 (no evidence of value over TensionTracker + ADR-080 narrative-weight traits) |
| Mood-keyed tracks (string-keyed) | per `audio.yaml` | 7 core moods + per-pack `mood_aliases` |

### Observability

| Feature | Module | Notes |
|---------|--------|-------|
| OTEL span catalog | `sidequest.telemetry.spans` | 40+ named spans (vs. ~10 Rust-side); includes `local_dm_*`, `projection_*`, `mp_*` |
| OTEL leak audit | `sidequest.telemetry.leak_audit` | Python-era addition; verifies span hygiene |
| Validator pipeline | `sidequest.telemetry.validator` | `patch_legality_check`, `entity_reference_check`, etc. registered checks |
| Watcher endpoint | `/ws/watcher` | Streaming telemetry to GM Mode |
| GM Mode dashboard | UI `GMMode` component + `/dashboard` | **Restoration in progress** under ADR-090 |
| TurnRecord pipeline | telemetry validator | Async TurnRecord delivery to validator subscribers |
| Subsystem coverage tracker | partial — `sidequest.agents.subsystems/` framework only | `CoverageGap` watcher event **dark** (ADR-087 RESTORE P1) |

### Player UI

| Feature | Component | Notes |
|---------|-----------|-------|
| Party status panel | `PartyPanel` | Portraits, HP bars, status effects |
| Character sheet | `CharacterSheet` | Narrative-voiced per ADR-040 |
| Inventory panel | `InventoryPanel` | Items by type, equipped, gold |
| Map overlay | `MapOverlay` | Region nodes/connections (live world-map fog-of-war retired 2026-04-28) |
| Journal/handouts | `JournalView` | KnownFacts by category + handout thumbnails |
| Combat overlay | `CombatOverlay` | Enemy HP, turn order |
| Confrontation overlay | `ConfrontationOverlay` | Momentum, beats; reads live state mirror (story 45-3) |
| Slash commands | `useSlashCommands` | /inventory, /character, /quests, /journal, /help |
| Server-side slash router | `sidequest.game.commands` | /status, /inventory, /map, /save, /tone, /gm suite (Python-era home, was server dispatch in Rust) |
| Keyboard shortcuts | `GameLayout` | P/C/I/M/J toggles, Space, Escape |
| Responsive layout | `useBreakpoint` | Mobile/tablet/desktop |
| Genre theming | `ThemeProvider` + `useGenreTheme` | CSS vars from pack config (ADR-079) |
| Audio controls | `AudioStatus` | Per-channel volume/mute/now-playing |
| Auto-reconnect | `ConnectScreen` | localStorage session persistence |

### Input Handling & Safety

| Feature | Module | Notes |
|---------|--------|-------|
| Input sanitization | `sidequest.protocol.sanitize` + `sidequest.agents.prompt_redaction` | Strips injection attempts at protocol boundary (ADR-047) |
| Lethality arbiter | `sidequest.agents.lethality_arbiter` | Policy-driven verdict on lethality claims (Python-era addition; not in Rust) |
| LocalDM decomposer | `sidequest.agents.local_dm` (DORMANT on live path) | Six modules carry DORMANT marker docstrings; offline-only corpus extraction via `sidequest.corpus.miner` (decision dated 2026-04-28) |

---

## Dark / Partial (ADR-087 Restoration Roster)

Per `docs/port-drift-feature-audit-2026-04-24.md` §5 and ADR-087, the following had working Rust implementations and did not port. Each carries a verdict and tier.

### P0 — this sprint or next

| Subsystem | ADR-087 verdict |
|-----------|------------------|
| ADR-059 pregen dispatch (server invokes namegen/encountergen/loadoutgen) | RESTORE |
| `sidequest-namegen` rewire (entry point + dispatch integration) | REWIRE |
| `sidequest-encountergen` (currently empty stub) | RESTORE |
| `sidequest-loadoutgen` (currently empty stub) | RESTORE |
| Scene fixture hydrator (ADR-069) | RESTORE |
| Confrontation Engine / Epic 28 port-drift | VERIFY → likely RESTORE |

### P1 — within current epic window

Trope engine, NPC disposition Attitude transitions, sealed-letter dispatch handler, continuity validator, patch legality gate (currently *partial* in `telemetry/validator.py` — see audit §9.1), subsystem coverage tracker, `sidequest-promptpreview` CLI, inventory extractor (VERIFY first).

### P2 — design-ready, next-epic candidate

Gossip engine, accusation logic, genie wish consequence engine, OCEAN shift proposals, chase engine (ADR-017 — affects road_warrior and space_opera Ship Block), catch-up dispatch handler, lore filter, speculative prerendering, `sidequest-validate` CLI expansion, scene relevance validator (REDESIGN under ADR-086).

### P3 — flavor / low urgency

Conlang morpheme glossary, beat filter, test-support helpers (VERIFY).

### Deferred — markers confirmed

Affinity progression (P6-deferred at `game/character.py:55-64`), advancement/XP pipeline (ADR-081 Proposed), dogfight (ADR-077 Proposed), Edge/Composure rituals (ADR-078 Proposed), tactical grid engine (ADR-071 Proposed — protocol live), 3D dice (ADR-075 Proposed — protocol live), merchant system (no ADR; write one before porting).

### Superseded / collapsed

Theme rotator (no demonstrated value; SUPERSEDED), separate narrator/troper/resonator/world_builder agents (collapsed under ADR-067 Unified Narrator), 14-tool abstraction (collapsed under ADR-059 direct structured output), live world-map / fog-of-war runtime view (ADR-019 superseded 2026-04-28; cartography YAML lives on as chargen seed only), Kokoro TTS pipeline (retired Epic 27 / ADR-076).

---

## Sprint 3 (Active) — Epic 45 Snapshot

Single-epic sprint absorbing Epic 37's open backlog plus port-drift residue. Three lanes:

- **(A) MP correctness** — sealed-letter shared-world delta, turn-barrier fix, momentum sync
- **(B) State write-back hygiene** — bookkeeping counters and resolution handshakes that fire but never persist; each owns an OTEL span on the write path
- **(C) UI/cleanup tax + tuning + render observability** — the rest of 37's open work, prioritized below A/B

Stories landed (so far): 45-1 (sealed-letter delta), 45-2 (turn barrier active turn-takers), 45-3 (momentum readout sync). 21 more carried from Epic 37 reach into placeholder cleanup, content drift triage, and OTEL/tuning work; backlog of 13 remains as of 2026-04-30.

---

## Genre Pack Status (Pointer)

7 pack directories in `sidequest-content/genre_packs/` but only **5 are functionally loadable**: `caverns_and_claudes`, `elemental_harmony`, `mutant_wasteland`, `space_opera`, `victoria`. The `heavy_metal` and `spaghetti_western` production directories are empty shells; their YAMLs live in `genre_workshopping/`. Four other packs (`low_fantasy`, `neon_dystopia`, `pulp_noir`, `road_warrior`) are workshop-only.

Full pack-by-pack breakdown lives at [`docs/genre-pack-status.md`](genre-pack-status.md).

---

## Pre-Port Inventory (Historical)

Earlier revisions of this document tabulated Sprint 1/Sprint 2 work against Epics 1–26 of the **Rust** workspace (`sidequest-api`). That tracker context is preserved in the sprint archive (`sprint/archive/`) and in the Rust-tree commit history at <https://github.com/slabgorb/sidequest-api>. Subsystem-level mapping from those epics to the current Python tree lives in:

- `docs/adr/README.md` (Rust → Python translation table)
- `docs/port-drift-feature-audit-2026-04-24.md` (per-subsystem landing audit)
- `docs/adr/087-post-port-subsystem-restoration-plan.md` (verdict + tier for each non-parity row)

---

## What's Playtest-Ready Today (Post-Port)

The full game loop is wired end-to-end in Python: connect → create character → play → narrate → render images → play music. Multiplayer works with turn barriers, adaptive batching, party action composition, perception rewriting, and the post-Sprint-3 sealed-letter shared-world delta. The unified narrator (ADR-067) handles exploration, dialogue, combat narration, and chase narration through one persistent Opus session; auxiliary agents run off the critical path. Pacing engine shapes delivery speed and narrator length via TensionTracker. Lore RAG, OCEAN profiles, footnoted narration with journal callback, and projection-filtered per-player views are all live.

OTEL coverage is the strongest it has ever been — 40+ named spans, leak audit, validator pipeline. The GM Mode dashboard is being restored against the new span catalog under ADR-090.

The biggest known gaps for Keith-as-player and Sebastien (mechanics-first) are on the ADR-087 restoration roster: trope engine, disposition transitions, continuity validator, and pregen dispatch. Each of those is what makes the difference between a narrator that improvises convincingly and a narrator the GM panel can actually keep honest. CLAUDE.md says it plain: _"The GM panel is the lie detector."_ Sprint 3 is closing the playtest debt; the next sprint inherits ADR-087's P0 tier.

**Best playtest experience today:** Multiplayer session in `caverns_and_claudes` (most worlds), `elemental_harmony` (richest audio), or `victoria` (most distinctive mechanics + curated music). Full media pipeline. Faction-driven world. OCEAN-flavored NPCs. Footnoted narration with journal. Confrontation engine with genre-typed resource pools where wired.
