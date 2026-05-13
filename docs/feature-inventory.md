# SideQuest Feature Inventory

**Last updated:** 2026-05-11
**Purpose:** *Manual-testing index.* Each row names a shipped feature, where it lives in the code (so you know what to grep when it breaks), and a one-line "Manual test" describing what to look for in a real session. If a row has no Manual-test note, it's an engineering-internal seam not directly user-exercisable.
**Sprint 3:** Playtest 3 closeout — MP correctness, state hygiene, post-port cleanup (active 2026-04-27 → 2026-05-10). Progress: 299/339 points · 8 in backlog.

> **Post-port snapshot.** This inventory describes the **Python** backend
> (`sidequest-server`) live since the ADR-082 cutover (2026-04-23). The
> language-level Rust → Python port is complete; subsystem-level drift is
> tracked separately. For the comprehensive non-parity inventory and verdicts:
>
> - `docs/port-drift-feature-audit-2026-04-24.md` — what landed in Python and what didn't
> - `docs/adr/087-post-port-subsystem-restoration-plan.md` — verdict + tier per non-parity subsystem
> - `docs/adr/README.md` — port-era reading guide and Rust → Python translation table

## Legend

- **Live & Wired** — Implemented, reachable from real session traffic, OTEL-emitting
- **Live (partial)** — Wired but not fully exercised, or has a known gap flagged by ADR-087
- **Dark** — Data model present, engine missing (ADR-087 RESTORE roster)
- **Deferred** — Phased scope; marker or Proposed ADR
- **Workshop only** — Content lives in `sidequest-content/genre_workshopping/`, not selectable in UI

**Companion docs:** [`wiring-diagrams.md`](wiring-diagrams.md) (Mermaid signal traces), [`api-contract.md`](api-contract.md) (WebSocket + REST), [`gm-handbook.md`](gm-handbook.md) (GM panel guide), [`genre-pack-status.md`](genre-pack-status.md) (pack-by-pack content).

---

## How To Use This As A Testing Index

For each section, scan the **Manual test** column for what a human can verify in a live session. Sections labeled *Engineering* have no manual-test column — they exist for grep-ability when something downstream breaks.

A baseline smoke pass is:
1. Connect (single player + multi-tab MP) → see *Connection & Lobby*
2. Roll a character through chargen → see *Character Creation*
3. Take 5–10 turns including a confrontation → see *Core Game Loop*, *Confrontation Engine*, *Combat / Edge*
4. Trigger an image render and a music cue → see *Media Pipeline*
5. Open the GM Dashboard at `/dashboard` and confirm OTEL spans → see *Observability*

---

## Live & Wired (Post-Port)

### Connection & Lobby

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| WebSocket transport | `server.websocket` + `websocket_session_handler` | `useGameSocket` / `useWebSocket` | Open client → see `WS upgrade` in network tab; messages flow both ways (ADR-038) |
| REST `/api/genres` | `server.rest` + `views` | `ConnectScreen` | Pack list appears on launch; new packs show up after server restart |
| Connect handshake | `handlers.connect` | `ConnectScreen` | New tab → name + genre → joins room without inline session_handler errors |
| Session lifecycle | `server.session_handler` + `session_helpers` | `ConnectScreen → GameLayout` | Connect → Create → Play; pydantic validation rejects malformed payloads (no silent fallback) |
| Lobby flat world picker | `server.session_handler` + `views` | `ConnectScreen` | Single flat list of worlds (not genre→world drill-down); each world tile carries its genre badge (ui PR #207) |
| Lobby hero image | `server.lobby` + `asset_urls` | `ConnectScreen` | World tiles show a hero image; image URL routes through `asset_urls` seam (R2 or local) |
| Multiplayer rooms | `server.session_room` | shared state | Two tabs with same `genre:world` land in one room (ADR-036/037); seat lights up |
| Player presence + seat | `handlers.player_seat` + `PLAYER_PRESENCE`/`PLAYER_SEAT`/`SEAT_CONFIRMED` | `MultiplayerSessionStatus` | Joining peer's avatar appears in seat strip; lobby paused-slot detection survives reconnect |
| Game pause/resume | `protocol.GAME_PAUSED`/`GAME_RESUMED` | `PausedBanner` | Disconnect last active player → server pauses → banner visible; rejoining resumes (`GAME_PAUSED` rollback hardened in ui `1da51bc`) |
| Auto-reconnect | `ConnectScreen` + `ReconnectBanner` + `OfflineBanner` | — | Kill server, restart → client reconnects from `localStorage`; transient drops do not lose seat |
| CORS + Vite proxy | FastAPI middleware | — | Dev hot-reload works; prod tunnel does not 404 on preflight |
| Production tunnel | `just serve` + `just tunnel` recipes | — | `player1.local`…`player4.local` reach the tunnel; per-origin cookie isolation holds (project memory) |

### Character Creation

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Three-mode chargen (ADR-016) | `game.builder` + `character` + `archetype_apply` | `CharacterCreation` | Lightning / Guided / Bespoke produce qualitatively different scene cadence |
| C&C visible-dice + arrange + story flow | `game.builder` + `dispatch.char_creation_resolve` | `CharacterCreation` (5–6 scenes) | In `caverns_and_claudes`, see *visible* d6 rolls per stat, an arrange step, and a story prompt (server PR #226 + ui PR #220, spec `2026-05-09-cnc-chargen-big-improvements-design.md`) |
| Four C&C classic classes | `genre.archetype.{resolved,shim}` + content `cc/classes/*` | `CharacterCreation` class-pick scene | Fighter / Mage / Cleric / Thief offered; class qualification filter hides ineligible classes (prime-requisite); each class produces distinct starting kit + gold + Edge seed (server feat sequence in `13db0ce` through `c3c5267`, content PR #182, spec `2026-05-06-cc-classic-classes-design.md`) |
| Class-themed equipment kits | `dispatch.chargen_loadout` + content `cc/equipment_kits.yaml` | inventory at chargen-end | Each class lands with a class kit (not a generic loadout); double-init dedup story 45-12 |
| CON-mod chargen Edge seed | `archetype_apply` + `game.session.starting_edge` | character sheet | Higher CON → higher starting Edge per ADR-078 amendment (server PR #247, story 39-10) |
| Per-class starting Edge | `edge_config` in `caverns_and_claudes/cc.yaml` | character sheet | Fighter starts with more Edge than Mage |
| Chargen dispatch package | `server.dispatch.{char_creation_resolve,chargen_loadout,chargen_summary}` | — | *Engineering* (split out of session_handler per ADR-063) |
| Chargen summary sentence | `dispatch.chargen_summary` | summary card | Prose sentence (not " \| "-joined fragment) shown at chargen-end; backstory paragraphs split on ` \| ` boundary (server `42558dd`) |
| Bootstrap character_locations | `chargen-complete` opening hook | — | After chargen, PC location seeded from opening scene (no null `character_locations` map in save) |
| Chargen OTEL surface | `telemetry.spans.chargen` | Dashboard `ConsoleTab` | Class subsystem events (qualifying classes, class-kit dispatch) visible in spans |

### Core Game Loop

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Orchestrator turn loop | `agents.orchestrator` | `NarrativeView` / `NarrationCards` | Type action → intent classified → narration arrives → state patches applied |
| Intent classification | `agents.orchestrator` (state-override) | — | `in_combat`/`in_chase`/default branches without an LLM hop (ADR-067) |
| Unified narrator (stateless turns, ADR-098) | `agents.narrator` + `claude_client.send_stateless` + `claude_stream_parser` + `stream_fence` | — | Each turn invokes `claude -p` as a fresh bounded prompt (no `--resume`, no `narrator_session_id`); per-turn prompt size stays bounded across 30-turn sessions (see `tests/agents/test_narrator_streaming.py`, ADR-098 supersedes ADR-066) |
| Stateless prompt split | `prompt.PromptRegistry.compose_split` + `STABLE_SECTION_NAMES` | — | *Engineering* — system + user pair built from registry buckets; every registered section has a deterministic bucket |
| Narrator retry-once | `orchestrator._invoke_with_retry_once` | — | Narrator failure once → silent retry; second failure → degraded turn with `is_degraded=True` (orchestrator `42ac13a`) |
| Oversized-prompt canary | `narrator` over-budget guard | Dashboard | If a single turn exceeds the budget, an OTEL canary fires but the turn still completes (ADR-098) |
| Sidecar tool patches | `orchestrator.assemble_turn` | — | Narrator prose arrives; items/mood/intent/SFX appear in JSONL sidecar; UI reflects state diff (ADR-039) |
| Auxiliary subsystem agents | `agents.subsystems/` (chassis_voice, distinctive_detail, npc_agency, reflect_absence) | — | Topologically-sorted dispatch off the live turn critical path; spans visible in `SubsystemsTab` |
| State delta computation | `game.delta.compute_delta` | `useStateMirror` | Wire-efficient state diff per turn; verify `STATE_DELTA` payloads contain only changed fields |
| Projection package | `game.projection/` + top-level `projection_filter.py` | per-client `INITIAL_STATE`/deltas | Run perception rewriter scenario; each player's view is filtered through `projection_decide_span`; invariants do not leak hidden facts |
| SQLite persistence | `game.persistence` + `migrations` | — | Save round-trip (`/character/save` → reconnect → state restored); one DB per save under `~/.sidequest/saves/` |
| Hub round-trip + REST hub endpoint | `game.world_save.hub` + `server.rest` | — | World hub state survives save/load (server feat `254257f`) |
| Genre pack loading | `genre.loader` + `models/` + `resolver` + `cache` + `genre_code` | `ThemeProvider` | Cold start loads pack YAML → pydantic → resolver; new world directories under `worlds/` appear on restart |
| Lethality policy loader | `genre.lethality_policy_loader` | — | Lethal claims arbitrated against per-genre policy YAML |
| Magic loader | `genre.magic_loader` | — | `magic.yaml` + plugin registry loaded into world config at boot |

### Narration & Streaming

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Narration delivery (two-message commit) | `protocol.messages.NARRATION` + `NARRATION_END` + `THINKING` | `NarrativeView`, `NarrationCards`, `NarrationFocus`, `NarrationScroll` (markdown via DOMPurify) | Each turn produces a `NARRATION` then `NARRATION_END`; UI applies atomically (ADR-076) |
| **Narrator streaming (default-on, 2026-05-11)** | `agents.narrator.stream_*` + `protocol.NarrationDelta` | `streamingNarration` reducer + `NarrationScroll` | Live token-by-token text renders inside the active turn card. Toggle off with `SIDEQUEST_NARRATOR_STREAMING=0` (commit `32bc0ff`) |
| Stalled-stream interstitial | client `lib/narrativeSegments` (5s no-content rule) | `NarrationScroll` | Cut narrator midstream → after 5s the UI shows a "still thinking" interstitial (ui `c979d3a`) |
| Narration Pane design pass | `NarrationCards` styling | `NarrationScroll` | Dark-Folio illuminated-manuscript visual applied to narration text (ui `5c5d573`) |
| Encounter render helper | `agents.encounter_render` | — | *Engineering* — renders encounter context for narrator |
| Drama-aware delivery | narration_apply consumers | UI delivery | INSTANT / SENTENCE / STREAMING modes triggered by `drama_weight`; quiet narration arrives instantly, climactic narration streams |
| Footnote protocol | `protocol.messages.NarrationPayload.footnotes` | `NarrationScroll` footnote chips | Click discovery footnote → opens journal at that fact; callback footnotes do not re-fire |

### Multiplayer & Pacing

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Turn barrier (submit-and-wait) | `server.session_room.TurnBarrier` | input lock + `MultiplayerTurnBanner` | Two players type; both must submit before narration; adaptive timeout 3s (2–3 players) / 5s (4+); claim-election prevents duplicate narrator calls. ADR-036 amendment 2026-05-03 — peer action text is *visible* during the window (collaborative default) |
| Active-turn-takers vs lobby count | story 45-2 | — | Spectator/observer peers do not stall the barrier |
| Shared-world delta handshake | `game.shared_world_delta` | — | After Player A's turn, Player B sees correct location/encounter/adjacency at hand-off (story 45-1) |
| Sealed-letter dispatch | `server.dispatch.sealed_letter` | — | PvP-style hidden moves (dogfight cross-product, magic outcomes) route through Phase-5 dispatch; multi-NPC arity-guard declines cleanly (server `f21cf52`) |
| Three turn modes | `game.session.TurnMode` | — | FREE_PLAY, STRUCTURED, CINEMATIC switchable via `/tone` family |
| Party action composition | `agents.orchestrator` | narrator prose | Three submitted actions reach narrator as a PARTY ACTIONS block; resolution mentions each PC |
| Perception rewriter | `agents.perception_rewriter` | per-player narration | Status-effect-bearing PC sees a different narration text than party (ADR-028) |
| **Live teammate typing (peer reveal)** | `handlers.action_reveal` + `protocol.ACTION_REVEAL`/`ACTION_QUEUE` + `InputBar` broadcast | `PeerRevealList` + `usePeerReveals` + `peerEventStore` | While Player B is typing, Player A sees B's draft text update live; on submit it locks into the queue (ui PR #205, spec `2026-05-03-live-teammate-typing-design.md`) |
| MP turn badges + new-turn auto-scroll | `MultiplayerTurnBanner` + `NarrationScroll` | turn cards | Per-turn badge identifies whose turn; new turn auto-scrolls into view (ui `74936ec`) |
| MP companion recruit | narrator `companions_added`/`companions_dismissed` apply seam + `PartyPanel` companion render | `PartyPanel` | Narrator adds an NPC to the party → companion appears in party strip with portrait + status; dismissal removes them (server `703ac05`, ui `890dc4b`) |
| Lockstep turn counter | `game.turn` | header / GM dashboard | `interaction` and `round` advance together via `record_interaction()` (ADR-051, collapse in story 45-11) |
| TensionTracker (dual-track) | `game.tension_tracker` | momentum readout | Gambler's ramp + Edge stakes + event spikes; quiet turns trigger escalation beats |
| Quiet turn detection | `game.tension_tracker` | narrator hint | Several sleepy turns → injected escalation beat in next narration |
| Genre-tunable thresholds | `pacing.yaml` per pack | — | Per-pack drama breakpoints; different packs cross thresholds at different counts |
| Momentum readout sync | story 45-3 | `ConfrontationOverlay` | Live momentum reads off state mirror; `encounter.momentum_broadcast` OTEL span visible |
| Yield action | `handlers.yield_action` + `dispatch.yield_action` | `YieldButton` | Click yield → narrator skips you this turn; Edge debit applied via `apply_edge_delta` |
| GAME_PAUSED input rollback | `GameStateProvider` | input | Input lock released on `GAME_PAUSED`; resume restores prior state (ui `1da51bc`) |
| `crypto.randomUUID` polyfill | `lib/uuid` shim | — | HTTP-only (non-localhost) tunnel sessions can join MP without crypto API errors (ui `1da51bc`) |

### Knowledge & Lore

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| KnownFact accumulation | `game.character.KnownFact` | `KnowledgeJournal` | Discover NPC/fact in narration → entry lands in journal under category |
| **Knowledge Journal keyword filter (live)** | server filter wire + `KnowledgeJournal.tsx` filter | journal search box | Type a multi-word query → token-AND match across fact contents (ui PR #204, story 45-22) |
| Footnote callback | `NarrationPayload.footnotes` | `NarrationScroll` | Click footnote → jumps to journal entry; same callback in a later turn reuses existing fact (no duplicate mint) |
| Lore store | `game.lore_store` | — | *Engineering* — persisted in SQLite |
| Lore RAG (embedding cosine) | `game.lore_embedding` (cross-process daemon, ADR-048) | — | Long-running session: narrator continues to reference earlier-session lore without total token blowup |
| Lore seeding from packs | `game.lore_seeding` | — | Boot loads pack legends/factions into lore store |
| Lore embedding dispatch | `server.dispatch.lore_embed` | — | Each turn emits a fan-out span in dashboard `LoreTab` |
| Belief state (multi-source credibility) | `game.belief_state` | — | Conflicting NPC accounts of the same fact → narrator weighs source credibility |
| Scenario / clue graph | `game.scenario_state` + `dispatch.scenario_bind` | — | Bottle-episode flows (e.g. whodunit) track clues and gates |

### NPC & World Systems

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| OCEAN profiles | `genre.models.ocean` | — | Every archetype carries five floats 0–10 |
| OCEAN behavioral summary | `OceanProfile.behavioral_summary()` | — | NPC voice differs across high-N vs low-N profiles |
| Narrator reads OCEAN | `agents.prompt_framework` | — | Same scene with two different NPCs reads differently |
| OCEAN shift proposals | — | — | **Dark** — evolution pipeline not ported (ADR-087 RESTORE P2) |
| Disposition (scalar) | `game.character.npc.disposition` | — | Scalar int with clamping; Attitude enum + transitions **dark** (ADR-087 RESTORE P1) |
| NPC pool / state split | `game.npc_pool` (Wave 2A) | — | NPCs split between session pool and party-bound state |
| Wave 2B per-character locations | `game.snap.character_locations` | — | Each PC carries its own location (no party-level `current_location`); story 45-48 |
| Recurring NPC presence detector | narrator `npcs_met` recurring tracker (story 45-53) | `KnowledgeJournal` recurrence badge | Same NPC encountered again across sessions → presence detector flags recurrence; OTEL span fires |
| Pool-only NPC promotion on `status_change` | narrator apply seam (`5492083`) | — | Narrator can promote a pool NPC to bound state when injuring them (no silent drop) |
| Faction agendas | `game.faction_agenda` | — | Goals + urgency feed scene directives; narrator weaves faction beats |
| Authored NPCs | `genre.models.authored_npc` | — | Pre-authored NPCs (Brecca, etc.) appear with their canonical traits |
| Scene directives | `agents.prompt_framework` (early-zone) | narration | Mandatory weave from `prompts.yaml`; absent weave → reflect_absence span fires |
| Trope ticks (data) | `game.session.TropeState` + `game.trope_tick` + `trope_tuning` | — | Progression cooldown + simultaneous-active cap (story 45-27); engine that fires beats remains **dark** (ADR-087 RESTORE P1) |
| Coyote Star trope wiring | content `coyote_star/chapters/*` | — | Chapter→trope blocks engage the trope engine when entered (content PR #209) |
| World materialization | `game.world_materialization` | — | Campaign maturity tier (fresh/early/mid/veteran) chosen at load |
| Region init / validation | `game.region_init`, `region_validation` | — | `snap.current_region` seeded from `cartography.yaml`; non-room entries rejected (45-16); slug-normalize at write (45-17) |
| Region state spans | `telemetry.spans.region_state` | Dashboard `StateTab` | Region transitions appear with `from`/`to` slug |
| Resource pool | `game.resource_pool` | `GenericResourceBar` | Thresholds + decay; visible in LedgerPanel for genre-typed pools (humanity, heat, fuel, voice/flesh/ledger) |
| Resolution signal | `game.resolution_signal` | momentum bar | Handshake plumbing for momentum/beat resolution |
| Scrapbook coverage | `game.scrapbook_coverage` | `ScrapbookGallery` | Renders backfilled when missing on save resume (story 45-10) |
| World history arcs | `game.history_chapter` | journal | Arc embeddings written back to narrative_log/lore (45-23); arcs run past turn 30 (45-19) |

### Confrontation Engine (ADR-033)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| StructuredEncounter + ConfrontationDef + `apply_beat` (Pillar 1) | `game.encounter`, `game.beat_kinds`, `game.opposed_check`, `server.dispatch.confrontation` | `ConfrontationOverlay` | Trigger a confrontation → beats apply → momentum + edge deltas land |
| ResourcePool + threshold→KnownFact mint (Pillar 2) | `game.resource_pool`, `game.thresholds`, `mint_threshold_lore` | journal | Crossing a threshold (e.g., humanity bar) mints a KnownFact visible in journal |
| Difficulty calibration v1 (ADR-093) | encounter difficulty math | momentum | Analytical-distribution + ship_combat correction live (story 45-42) |
| `mood_override` step | narration_apply | audio cue | Beat with `mood_override` flips audio track immediately |
| Confrontation outcome dispatch | `protocol.CONFRONTATION_OUTCOME` | `LedgerPanel` + Phase-5 reveal | Outcome message refreshes ledger bars (story 47-3) |
| Magic Phase 5 confrontation reveal | `ConfrontationOverlay` outcome panel | reveal UI | Magic confrontation result shown with revealed outcome card (ui PR #192, story 47-3) |
| Encounter lifecycle dispatch | `server.dispatch.encounter_lifecycle` | — | XP path partial (`award_turn_xp` stub); ADR-081 deferred |
| `mood_aliases` alias chain | `genre.models.audio.mood_aliases` | — | **Dark (polish)** — declared, one pack uses it; consumer not wired (ADR-087 P3) |

### Combat / Edge / Composure (ADR-078, ADR-014)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Edge primitive on CreatureCore | `game.creature_core.EdgePool`, `apply_edge_delta` | `CharacterPanel` Edge bar | Take a beat → Edge bar moves; yield → Edge debit; wired from `dispatch/yield_action.py:43`, `session.py:884,888` |
| Edge debits + composure break + numerical advantage (ADR-078 §3-4) | `combat.edge_apply` + numerical-advantage shift | Edge bar + narration | Surrounded PC sees numerical-advantage shift; Edge at ≤0 triggers composure-break narration (server feat `8fa2b3a`) |
| Shared threshold helper | `game.thresholds` | — | *Engineering* — covers crossings + threshold→KnownFact mint |
| `BeatDef.edge_delta` field | `genre.models.rules.BeatDef` | — | Beats with `edge_delta` move bars predictably |
| HP removal | story 45-35 | character sheet | No HP field on sheet; chargen does not roll HP; vestigial fields in `tension_tracker.py:340-350`, `history_chapter.py:64` flagged for cleanup |
| Combatant / opposed check | `game.combatant`, `opposed_check`, `combat_brackets` (dispatch) | — | *Engineering* — bracket math during combat ticks |
| Advancement-effect data shapes | `genre.models.advancement` | — | Shapes loaded; runtime upstream-blocked on Epic 39 per-class edge config |
| Gold-change narration apply | narrator gold seam | `InventoryPanel` purse | Narrator-reported gold change applies to acting PC's purse (no party-wide drift); OTEL span fires (server `a50c8c9`) |
| `composure_break` OTEL span | `telemetry.spans.combat` | Dashboard | **Dark** — span definition exists but resolution-at-edge≤0 not yet wired into critical path (ADR-078 §4) |
| Push-currency rituals (pact_working) | `genre_workshopping/heavy_metal/` | — | **Workshop only** |

### Saving Throws & B/X Class Beats

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| B/X B26 saving throws | `game.saving_throws` resolver + schema + OTEL (Tasks 1–8) | narration | C&C scene with poison/wand/death/breath/spell save → roll uses class-level B26 table; `save.throw` OTEL span emitted (server PR #224, spec `2026-05-09-cnc-bx-saving-throws-design.md`) |
| C&C B/X class beats + morale | `game.beat_filter`, `narration_apply.morale`, `resource_deltas` drain | narration | Enemy NPCs check morale and rout when broken; class-distinct beats (Fighter cleave, Mage memorization, Cleric turn, Thief backstab) trigger in matching contexts (server PR #220, content PR #193, spec `2026-05-08-cnc-bx-class-beats-morale-design.md`) |
| Class signature ability (one per class) | `game.class_moves` + abilities tab | `AbilitiesContent` (Lv1 Abilities tab) | Open Abilities tab → see Fighter Taunt / Cleric Turn Undead / Thief Backstab / Mage memorization (server PR #239, ui PR #223, content PR #200, ADR-095) |
| Fighter Taunt | `game.class_moves.taunt` | abilities tab | Taunt action moves enemy aggro one tier toward the fighter; resource_deltas drain `taunt_charges` |
| Cleric Turn Undead | content `cc/classes/cleric.yaml` | abilities tab | In undead encounter, Turn Undead resolves on B26 turn-undead table |
| Thief Backstab | content `cc/classes/thief.yaml` | abilities tab | Thief acting from concealment gets backstab multiplier |
| `class_moves` on character sheet | `protocol.CharacterSheetData.class_moves` | `CharacterSheet` | Sheet displays class moves block (ui `3a887f0` test fixture) |

### Magic System (Epic 47)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| MagicPlugin protocol | `magic.plugin.MagicPlugin` + `MAGIC_PLUGINS` registry | — | Plugins self-register at import (runtime-checkable Protocol) |
| Innate v1 plugin | `magic.plugins.innate_v1` (.py + .yaml) | — | coyote_star + heavy_metal references; ledger bars rise/fall on use |
| Item-legacy v1 plugin | `magic.plugins.item_legacy_v1` (.py + .yaml) | — | Item-bound magic costs route through item legacy bars |
| **Learned v1 plugin (Vancian memorization)** | `magic.plugins.learned_v1` | `LedgerPanel` slot bar + memorize action | C&C cleric/mage memorize spells at rest → slot bars fill; cast drains slots; `cost_type: spell_slots` matches bar id (server PR #221 + #223, content PR #195, story 47-10, spec `2026-05-06-magic-system-caverns-and-claudes-implementation-design.md`) |
| Class-aware spell-slot allocation | `magic.slot_allocator` | LedgerPanel | Mage gets 1/0/0 at L1, Cleric gets 1 divine slot at L2 etc. (server PR #219) |
| L1 spell catalogs (arcane 12 + divine 8) | content `caverns_and_claudes/spells/` | spell list at chargen | Mage offered 12 arcane L1; Cleric offered 8 divine L1 (content PR #194) |
| Starting known spells | content `cc/classes/mage.yaml` | sheet | Mage starts with 3 known spells (test contract `1a613d4`) |
| MagicState + LedgerBars | `magic.state` | `LedgerPanel` | Per-character bars with thresholds + crossing events |
| Magic context block | `magic.context_builder.build_magic_context_block` | narrator prose | Narrator references magic state (cost types, current bar) in-fiction |
| Plugin-aware proactive magic prompt | story 47-9 firing logic | narration | On `innate_v1` worlds, narrator force-fires innate magic in opening; `LedgerBar.value` (not `current`) read at prompt-assembly (server PR #215) |
| Magic validator + flag severity | `magic.validator` + `Flag`/`FlagSeverity`/`HardLimit`/`StatusPromotion` | narration counter-weight | Yellow/red/deep_red escalation; CRITICAL MAGIC NEGATIVE CASE counter-weight injected (server `a9db03c`) |
| Scope-aware cost routing | `magic.apply_working` | LedgerPanel | Innate cost debits character bar; item cost debits item bar (no cross-routing) — server `81f630a` |
| Surface valid cost types | `magic.context_builder.valid_cost_types` | narrator alignment | Narrator only proposes cost types the world actually supports (server `997c164`) |
| Magic confrontations (5 wired) | `magic.confrontations` | `ConfrontationOverlay` | `the_standoff`, `the_salvage`, `the_bleeding_through`, `the_quiet_word`, `the_long_resident` resolve via Phase-5 sealed-letter |
| Magic-init server hook | `server.magic_init` | — | Magic state booted at world load; MP-second-commit + OTEL spans + loud fallbacks (server PR #218) |
| MP joiner magic init | `magic_init` (MP joiner branch) | LedgerPanel | Player joining mid-session gets `character_class=` passed through (server `d5679eb`) |
| Magic warning watcher events (47-7) | promoted defensive warnings to watcher | Dashboard | Three uninit warnings fire as watcher events on the dashboard (server PR #229) |
| Tea ritual auto-fire | story 47-6 three-layer fix | narration + LedgerPanel | Entering a tea-ready room triggers tea ritual narration + bond bar increment |
| LedgerPanel UI | `LedgerPanel.tsx` + `MagicBlock` | LedgerPanel | Reacts to `CONFRONTATION_OUTCOME`; MagicBlock surfaces magic-specific bars (ui PR #215) |
| Sensitivities subsection | `SensitivitiesSection` on Abilities tab | abilities tab | coyote_star Sensitivities section visible (ui PR #193) |

### Rig System (sibling of Magic)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Rig framework decisions | project memory `project_rig_framework_decisions.md` | — | α / R / D3 / S2 / C3 locked; Coyote Star flagship |
| Tea brew confrontation | story 47-4 | `ConfrontationOverlay` | `the_tea_brew` resolves and adjusts bond tier |
| Cliché-judge hook #7 | rig validation hook | — | Validation flags chassis name-form vs bond tier mismatches |

### Orbital Chart / Course Plotting (ADR-094)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Body / orbits config | `orbital.models.BodyDef`, `OrbitsConfig` + `orbital.loader` | — | World loads `worlds/<world>/chart.yaml` |
| Position computation | `orbital.position` + `orbital.clock` | — | Bodies move with simulated time |
| Course plotting (eta + Δv) | `orbital.course` + `course_geometry.compute_eta_and_dv` | `useOrbitalChart` + `OrbitalChartView` | Plot a course → ETA + Δv numbers update; narrator references the trip |
| Course intent dispatch | `handlers.course_intent` + `protocol.course_intent` | OrbitalChart HUD | `ORBITAL_INTENT` inbound message accepted; replies with `OrbitalIntentResponse` |
| Plotted-course revision wire field | `OrbitalIntentResponse.plotted_course` | `useOrbitalChart` | Chart auto-refetches on `plotted_course` revision bump (ui PR #199, #194) |
| Server-rendered chart (ADR-094) | `orbital.render` + `orbital.course_render` | `OrbitalChartView` | Chart arrives as server SVG (not client orrery view); HUD strips on top/bottom (ui PR #189, #194) |
| Conjunction beats | `orbital.conjunction` + `orbital.beats` | narration | Conjunction event fires narrative beat in narrator prompt |
| Label placement (3 strategies) | `orbital.label_strategy` | callouts | Forced_moon_band etc. visible (ADR-094 amendment, story 45-43) |
| Chart-as-calendar HUD | `OrbitalChart/HudTopStrip`, `HudBottomStrip` | overlays | Imperative pan/zoom + calendar overlay (ui PR #194) |
| Orbital palette | `orbital.palette` | chart | Black ground, brass-amber phosphor; white reserved for party marker |
| Session-bound chart re-fetch | `useOrbitalChart` | chart | Mid-session bind re-fetches chart (no `AwaitingConnect` deadlock; ui `968cfe8`) |

### Interior / Ship (Kestrel)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Chassis interior SVG renderer | `interior.render` + `interior.loader` + `interior.dispatch` | `useChassisInteriorSVG` + `ShipWidget` | `voidborn_freighter` (Kestrel) renders 2×2 layout with rooms (ui PR #197); other chassis classes deferred |
| Ship tab in dock | `availableWidgets` registry | `ShipWidget` | Ship tab visible in widget dock (ui `f319fef`) |
| Asset routing for ship hero image | `asset_urls` seam (server `3c5578f`) | ShipWidget | Hero image URL resolves through asset_urls (R2 or local) |
| Chassis classes | `genre.models.chassis` + `chassis_classes.yaml` | — | Pack-defined chassis catalog |
| Chassis voice subsystem | `agents.subsystems.chassis_voice` | narration | Rig "speaks" with chassis voice between scenes |
| Chromed archetype | `useChromeArchetype` | character UI | Resolves player's chromed archetype for display |

### 3D Dice (ADR-074 / ADR-075)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Dice resolution protocol | `protocol.dice` + `DICE_REQUEST/THROW/RESULT` + `handlers.dice_throw` + `dispatch.dice` + `game.dice` | — | Confrontation rolls produce a DICE_REQUEST visible in dashboard `EncounterTab` |
| Three.js + R3F + Rapier scene | `sidequest-ui/src/dice/{DiceScene,DiceOverlay,DiceSpikePage,InlineDiceTray}` + `d4/d6/d10/d12/d20.ts` | Inline dice tray | Roll appears as 3D dice in the ConfrontationOverlay |
| Inline dice tray | `InlineDiceTray.tsx` (mounted in `ConfrontationOverlay.tsx:325`) | overlay | Tray auto-rolls on dice request (gesture pivot from explicit click) |
| Tie vs Fail rendering | dice outcome path | inline tray | Tie outcome renders distinctly from Fail; passing-face display correct (ui PR #211) |
| Dice theme | `diceTheme.ts` + `replayThrowParams.ts` | — | Default white-with-black for all genres |
| Per-genre `dice.yaml` theming | — | — | **Dark (polish)** — zero packs declare; default ships for all (ADR-087 P3) |

### Dogfight (ADR-077)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Sealed-letter cross-product resolution | `dispatch.sealed_letter` + `narration_apply.py:1176` `ResolutionMode.sealed_letter_lookup` | narration | Dogfight in space_opera resolves both pilots' moves simultaneously |
| Dogfight content | `genre_packs/space_opera/dogfight/` (descriptor_schema, interactions_mvp, interactions_tail_chase, maneuvers_mvp, pilot_skills) | — | Maneuver names visible in narration |
| SOUL gate exclusion | — | — | Dogfight beats not subject to lethality arbiter |

### Media Pipeline — Image

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Image generation backbone | `daemon_client` → `sidequest-daemon` (Z-Image MLX, Flux retired) | `ImageGalleryWidget`, `ScrapbookGallery` | Dramatic turn → portrait or POI image arrives within pacing window (ADR-070) |
| Daemon Z-Image MLX worker | `sidequest_daemon.media.workers.zimage_mlx_worker` | — | Single per-process singleton enforced (daemon `65f9841`) |
| Daemon Z-Image config | `sidequest_daemon.media.zimage_config` | — | Tier-driven config; high-fidelity tier (story 45-38) + worker swap on `SIDEQUEST_DAEMON_FIDELITY` (45-39) |
| Pipeline factory + recipe loader | `pipeline_factory` + `recipe_loader` + `recipes` | — | Recipe assembly validated at startup (daemon `b5cba3b`) |
| Prompt composer | `prompt_composer` + `subject_extractor` + `cameras.yaml` | — | Per-render prompt composed from camera spec + recipe; preserves ART_SENSIBILITY.WORLD under budget (daemon `222fff5`) |
| Catalog catalog injection | `prompt_composer` catalog-injected mode | — | Runtime PC registered into catalog from descriptor (daemon `949bd4d`) |
| GPU detection | `gpu_detect` | — | *Engineering* — hardware probe |
| Post-processor (crop + rotate) | `post_processor` + Pillow | — | Required render size respects pre-crop budget |
| Subject extraction | narrator `visual_scene` (preferred) + regex fallback | — | Narrator-supplied subject used; fallback only when absent |
| Image pacing throttle (ADR-050) | `server.image_pacing` | — | 30s solo, 60s MP; DM override available |
| Render trigger policy | `server.render_trigger` + `render_diagnostics` | Dashboard `render.trigger` span | Story 45-30 — explicit trigger reasons surfaced |
| Render mounts | `server.render_mounts` | — | FastAPI static mounts for render output |
| Asset URLs (local + R2) | `server.asset_urls` | hero/audio/portrait | Local renders served via static mount; R2 renders served via signed URL |
| **R2 writer + sha256-keyed upload** | `sidequest_daemon.media.r2_writer.upload_artifact` | — | Renders upload to R2; `r2_key` emitted alongside legacy `image_url` (daemon PR #69) |
| Image silent-fallback teardown | story 45-37 | Dashboard | `render.completed` is now a lie detector — every SF1-SF7 path killed |
| Render queue with content dedup | daemon pipeline | — | Identical prompts SHA256-dedup |
| Daemon worker heartbeat | story 45-31 | Dashboard `render.heartbeat` | Heartbeat frames published; client skips them when reading reply (orchestrator `ab8c0c0`) |
| Render-unavailable degradation | story 45-31 `WorkerState` | UI | Render outage → graceful "image unavailable" without crashing turn |
| `render_status` indicator | `ScrapbookGallery` | scrapbook | Visual indicator of in-flight vs completed renders (ui PR #196) |
| Daemon span-context per-call art_style | story 45-29 | Dashboard | Per-call scoping (not global), visible in render spans |
| Single-POI render flag | `scripts/generate_poi.py` | — | Daemon heartbeat lines tolerated when reading reply (orchestrator `941a7a3`) |
| Promptpreview CLI | `daemon.sidequest-promptpreview` (registered) | — | `sidequest-promptpreview style …` returns visual-style diagnostics (daemon `a74dfec`) |
| LoRA training pipeline | `sidequest_daemon.training.{cli,corpus_loader,format,trainer}` | — | *Engineering* — ADR-032/083/084 lineage |
| Composer recipes validated at startup | `recipes.yaml` + `cameras.yaml` validators | — | Bad recipe stops daemon at boot (no silent fallback) |

### Media Pipeline — Audio

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Music director | `audio.{interpreter,library_backend,protocol,rotator}` + `audio.models` | — | Pre-rendered ACE-Step tracks selected by mood |
| Audio cue messages | `protocol.messages.AUDIO_CUE` + `server.audio_cue` (asset_urls seam) | `useAudioCue`, `AudioStatus`, `AudioWidget` | Music + SFX flow over WS; URL resolved through `asset_urls` (server `cc17cd3`) |
| Client audio engine | `sidequest-ui/src/audio/{AudioEngine,AudioCache,Crossfader}` | AudioWidget | Cross-fade transitions between mood tracks (ADR-045) |
| Daemon audio pipeline | `sidequest_daemon.audio.{interpreter,library_backend,mixer,queue,protocol,rotator}` + `models` | — | 2-channel mixer (music + SFX), pygame |
| Daemon scene interpreter | `sidequest_daemon.scene_interpreter` | — | Maps narration → audio cues |
| 2-channel audio | — | — | Music + SFX only — no voice/TTS (ADR-076) |
| Mood-keyed tracks | per `audio.yaml` | — | 7 core moods + per-pack `mood_aliases` (consumer not yet wired — ADR-033 P3) |
| **ACE-Step daemon music tier (ADR-095)** | `sidequest_daemon.media.music_pipeline.py` + `r2_writer` | — | `python scripts/generate_music.py --genre <pack>` generates OGG → uploads to R2 at `genre_packs/<pack>/audio/music/<track>.ogg` (operator-triggered; daemon PR #73) |
| Audio assets live in R2 | content references | — | Audio files no longer in git LFS; pack `audio.yaml` references R2 keys (content PR #201, story 45-49) |
| Pack audio resolves R2-only | `audio.library_backend` (drop `Path.exists` guard) | — | Packs with only R2-key audio resolve without local file (server PR #248) |
| Theme rotator | — | — | **Superseded** (ADR-087 — no value over TensionTracker + ADR-080 narrative weight) |

### Player UI — Widgets & Panels

| Feature | Module(s) / Component | Manual test |
|---------|-----------------------|-------------|
| GameBoard widget shell | `GameBoard/GameBoard.tsx` + `widgetRegistry` + `WidgetWrapper` + `BackgroundCanvas` + `MobileTabView` | Open game → see modular widget dock (replaces fixed-panel layout) |
| Widgets | `GameBoard/widgets/`: `AudioWidget`, `CharacterWidget`, `ConfrontationWidget`, `ImageGalleryWidget`, `InventoryWidget`, `KnowledgeWidget`, `MapWidget`, `NarrativeWidget`, `ScrapbookGallery`, `ShipWidget` | Each panel toggleable from dock; layout persists |
| Hotkeys / layout | `useGameBoardHotkeys` + `useGameBoardLayout` + `useLayoutMode` | P / C / I / M / J toggles + Space + Escape work |
| Responsive layout | `useBreakpoint` + `useLayoutMode` | Resize browser → mobile/tablet/desktop layouts swap |
| Party panel | `PartyPanel` (`CharacterPanel`) | Portraits + status effects + Edge bars; recruited NPC companions render with badges (ui PR #212) |
| Character sheet | `CharacterSheet` | Narrative-voiced per ADR-040; Edge/Composure (no HP); class_moves block |
| **Abilities tab (Lv1)** | `AbilitiesContent` four-section | Class signature ability + Sensitivities + class_moves + magic block visible (ui PR #223) |
| Inventory panel | `InventoryPanel` + `InventoryWidget` | Items by type, equipped flag, gold purse |
| Map overlay | `MapOverlay` + `Automapper` + `DungeonMapRenderer` | Region nodes + connections (cavern image-mode renderer + Automapper settlement branch — ui PR #225) |
| Tactical grid renderer (cavern revival, ADR-096) | `TacticalGridRenderer` + `tacticalGridFromWire` + image-mode | Cavern scene renders as PNG-from-tile-set (not SVG); legacy SVG path still supported (ui PR #226) |
| Journal / handouts | `JournalView` + `KnowledgeJournal` | KnownFacts by category + handout thumbnails |
| **Dark-Folio illuminated-manuscript visual** | Knowledge Journal, Inventory, Character, Narration Pane | Dark parchment + illuminated drop-cap visual applied uniformly (ui PRs #216, #217, #218, #222) |
| **Folio font size bump (+2pt)** | every Folio text element | Body copy larger across panels (ui PR #219) |
| Confrontation overlay | `ConfrontationOverlay` + `InlineDiceTray` | Momentum + beats; mounts inline dice tray |
| Ledger panel | `LedgerPanel` + `MagicBlock` | Magic / Edge bars react to `CONFRONTATION_OUTCOME` |
| Generic resource bar | `GenericResourceBar` | Reused across magic, edge, faction pools |
| Sensitivities section | `SensitivitiesSection` | Player-facing content sensitivities |
| Slash commands (client) | `useSlashCommands` | `/inventory`, `/character`, `/quests`, `/journal`, `/help`, `/tone` |
| Server slash router | `game.commands` | `/status`, `/inventory`, `/map`, `/save`, `/tone`, `/gm` suite |
| Image bus | `providers/ImageBusProvider` | *Engineering* — image pub/sub for widgets |
| Game state provider | `providers/GameStateProvider` | *Engineering* — shared state mirror context |
| Local prefs | `useLocalPrefs` | Per-player persisted settings |
| Display name resolver | `useDisplayName` | Genre-aware formatting (e.g. "Sir/Dame" prefix in `tea_and_murder`) |
| Running header | `useRunningHeader` | Header reacts to state mirror |
| Error boundary | `ErrorBoundary` | UI errors caught at the boundary, not white-screen |
| Genre theming | `ThemeProvider` + `useGenreTheme` | CSS vars from pack config (ADR-079); per-pack `client_theme.css` honored |
| Story panel polish | `StoryPanel` | Optional badges shown; disabled-Confirm shows reason text (ui PR #221) |
| Border long-form on journal | journal entry styling | Border properties apply (ui PR #228) |
| Favicon / logo / window title | `index.html` | Tab shows SideQuest favicon + title (ui `5854b9e`) |
| Peer reveals | `PeerRevealList` + `usePeerReveals` + `usePeerEventCache` + `peerEventStore` | Other players' actions/observations visible in side stream |
| `aria-describedby` on Retry | error banner | Screen readers announce error context (ui PR #195) |

### Observability & GM Panel (ADR-058 / ADR-090)

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| OTEL span catalog | `telemetry.spans/` (50+ named spans across `agent`, `asset_url`, `audio`, `barrier`, `catch_up`, `chargen`, `chart`, `clock`, `combat`, `compose`, `content`, `continuity`, `course`, `dice`, `disposition`, `dogfight`, `emitter`, `encounter`, `interior`, `inventory`, `lobby`, `local_dm`, `lore`, `magic`, `merchant`, `monster_manual`, `mp`, `namegen`, `narrator`, `narrator_streaming`, `npc`, `opening`, `orchestrator`, `persistence`, `pregen`, `projection`, `rag`, `region_state`, `reminder`, `render`, `rig`, `room_state`, `scenario`, `scrapbook`, `script_tool`, `state_patch`, `trope`, `turn`, `world`) | Dashboard | Every subsystem decision emits a span |
| Phase timing | `telemetry.phase_timing` | Dashboard `TimingTab` | Per-phase timing decorators visible |
| OTEL leak audit | `telemetry.leak_audit` | — | *Engineering* — verifies span hygiene |
| OTEL setup + Jaeger exporter | `telemetry.setup` | Jaeger | Spans flow to Jaeger; exporter flow fix landed (story 45-41) |
| Validator pipeline | `telemetry.validator` | Dashboard `ConsoleTab` | `patch_legality_check`, `entity_reference_check` registered checks |
| TurnRecord pipeline | `telemetry.turn_record` | — | Async TurnRecord delivery to validator subscribers |
| Watcher endpoint | `/ws/watcher` + `server.watcher` + `server.emitters` + `telemetry.watcher_hub` | Dashboard | GM Mode streams telemetry over WS |
| **`/internal/watcher/emit` REST endpoint** | `server.watcher_emit` | Dashboard | Daemon → server bridge for OTEL emission (server PR #240) |
| Watcher replay buffer | `watcher_hub.replay` | Dashboard refresh | Refreshing dashboard shows prior watcher history (server PR #235) |
| GM Mode dashboard | UI `Dashboard/` (`DashboardApp`, `DashboardHeader`, `DashboardTabs`) + tabs (`ConsoleTab`, `EncounterTab`, `LoreTab`, `PromptTab`, `StateTab`, `SubsystemsTab`, `TimelineTab`, `TimingTab`) + charts (`DonutChart`, `FlameChart`, `Histogram`, `ScatterPlot`, `TokenBarChart`) | `/dashboard` | Open dashboard → all tabs populated during a session |
| **Prompt tab: system/user split + bounded marker** | `PromptTab` (ADR-098 view) | dashboard | Each turn shows system prompt + user prompt as separate panels with bounded marker (ui PR `ddc96ff`) |
| **Prompt tab: expandable section viewer** | `PromptTab` section content viewer | dashboard | Click a prompt section → expand to view full content (server PR #241) |
| Subsystem coverage tracker | partial — `agents/subsystems/` framework only | — | `CoverageGap` watcher event **dark** (ADR-087 RESTORE P1) |
| Watcher socket | `useWatcherSocket` | dashboard | Client subscribes to GM Mode telemetry |
| Six cold-subsystem OTEL spans wired | `telemetry.spans` (story 45-44) | dashboard | Subsystems that previously emitted nothing now produce spans (server PR #236) |

### Input Handling & Safety

| Feature | Module(s) | UI | Manual test |
|---------|-----------|----|-------------|
| Input sanitization | `protocol.sanitize` + `agents.prompt_redaction` | — | Adversarial input stripped at protocol boundary (ADR-047) |
| Lethality arbiter | `agents.lethality_arbiter` + `genre.lethality_policy_loader` | narration | Lethal claims arbitrated against per-genre policy (Python-era addition) |
| LocalDM decomposer (dormant) | `agents.local_dm` + `corpus.miner` | — | DORMANT marker docstrings; offline-only via corpus mining (2026-04-28 spec) |
| Corpus mining CLIs | `cli.corpusmine`, `cli.corpusdiff`, `cli.corpuslabel` + `corpus.{diff,going_forward,miner,negatives,save_reader,schema,writer}` | — | `python -m sidequest.cli.corpusmine` runs; reserved wire kinds (`DISPATCH_PACKAGE`, `NARRATOR_DIRECTIVE_USED`, `VERDICT_OVERRIDE`) ride along |
| Verdict override / directive used | `protocol.{VERDICT_OVERRIDE, NARRATOR_DIRECTIVE_USED, DISPATCH_PACKAGE}` | — | Reserved kinds — not yet emitter-reachable for all paths |

---

## Engineering Surfaces (No Manual Test)

These rows exist for grep-ability when a downstream user-facing feature breaks. They are the seams a Dev needs to trace through; they have no direct manual-test affordance.

### Genre Pack Modeling (Decomposed)

| Feature | Module(s) | Notes |
|---------|-----------|-------|
| Genre pack schema | `genre.models.pack` (`PackConfig`) | Top-level pack metadata |
| Rules / beats | `genre.models.rules` | Beats, edge_delta, target_edge_delta, resource_deltas |
| Axes / archetype axes | `genre.models.axes` + `archetype_axes` + `archetype_constraints` + `archetype_funnels` | Three-mode chargen + funnels |
| Archetypes | `genre.models.archetype` + `genre.archetype.{resolved,shim}` | Resolved archetype + shim for legacy callers |
| Character + chassis + inventory | `genre.models.{character,chassis,inventory}` | |
| Cultures | `genre.models.culture` + per-pack `cultures.yaml` + `corpus/` | ADR-091 culture-corpus + Markov |
| Names | `genre.names.{generator,markov,thresholds}` | Per-culture Markov; min-pool guard + thin-corpus audit (story 45-28) |
| Lethality | `genre.models.lethality` | |
| Audio | `genre.models.audio` | `mood_aliases` (P3 polish gap) |
| Visibility / projection | `genre.models.visibility` + `visibility_baseline.yaml` + `projection.yaml` | Per-player visibility config |
| Lore / legends | `genre.models.{lore,legends}` | |
| OCEAN / NPC traits | `genre.models.{ocean,npc_traits,authored_npc}` | |
| Theme | `genre.models.theme` + `theme.yaml` + `client_theme.css` | |
| Tropes | `genre.models.tropes` + `tropes.yaml` | |
| Progression / advancement | `genre.models.{progression,advancement}` | |
| Narrative axis / scenario | `genre.models.{narrative,scenario}` | |
| Rigs world | `genre.models.rigs_world` | Sibling-of-magic rig framework anchor |
| World | `genre.models.world` + per-world `world.yaml` | |
| Classes | `genre.models.classes` + pack `classes.yaml` | Four C&C classic classes ship in `caverns_and_claudes` |

### Server Dispatch Package (ADR-063)

| Handler | Module | Notes |
|---------|--------|-------|
| Char creation resolve | `dispatch.char_creation_resolve` | Final resolve step |
| Chargen loadout | `dispatch.chargen_loadout` | Double-init dedup story 45-12 |
| Chargen summary | `dispatch.chargen_summary` | Preserves prose; splits on ` \| ` |
| Combat brackets | `dispatch.combat_brackets` | |
| Confrontation | `dispatch.confrontation` | Pillar-1/2 ADR-033 |
| Culture context | `dispatch.culture_context` | Per-culture narrator context |
| Dice | `dispatch.dice` | ADR-074 |
| Encounter lifecycle | `dispatch.encounter_lifecycle` | XP partial stub |
| Lore embed | `dispatch.lore_embed` | Per-turn embedding fan-out |
| Opening | `dispatch.opening` | Session opener narration |
| Scenario bind | `dispatch.scenario_bind` | Bottle-episode binding |
| Sealed letter | `dispatch.sealed_letter` | Phase-5 sealed-letter |
| Yield action | `dispatch.yield_action` | Edge debit on yield |

### Top-Level Handlers

| Handler | Module | Notes |
|---------|--------|-------|
| Action reveal | `handlers.action_reveal` | Collaborative peer-action visibility (ADR-036 amendment 2026-05-03) |
| Character creation | `handlers.character_creation` | Replaces inline session_handler logic |
| Connect | `handlers.connect` | Connect handshake |
| Course intent | `handlers.course_intent` | Orbital chart inbound |
| Dice throw | `handlers.dice_throw` | `DICE_THROW` inbound |
| Orbital intent | `handlers.orbital_intent` | `ORBITAL_INTENT` inbound |
| Player action | `handlers.player_action` | `PLAYER_ACTION` — the live turn entry point |
| Player seat | `handlers.player_seat` | Lobby seat claim |
| Session event | `handlers.session_event` | Session event dispatch |
| Yield action | `handlers.yield_action` | `YIELD` inbound |

### CLIs (`pyproject.toml [project.scripts]`)

| CLI | Module | Status |
|-----|--------|--------|
| `sidequest-server` | `sidequest.server.app:main` | **Live** — the only registered entry point |
| `python -m sidequest.cli.namegen` | `cli/namegen/` + `__main__.py` | **Code present, runnable as module; not wired into server** (ADR-087 REWIRE P0) |
| `sidequest-encountergen` | `cli/encountergen/__init__.py` stub | **Empty** (ADR-087 RESTORE P0) |
| `sidequest-loadoutgen` | `cli/loadoutgen/__init__.py` stub | **Empty** (ADR-087 RESTORE P0) |
| `sidequest-validate` | `cli/validate/projection_check.py` | **Partial** — projection check shipped; broader validation owed (ADR-087 RESTORE P2) |
| `sidequest-promptpreview` (daemon-side) | `sidequest-daemon` entry point | **Live** — visual-style diagnostics (daemon `a74dfec`) |
| `sidequest-promptpreview` (server-side) | `cli/promptpreview/__init__.py` stub | **Empty** (ADR-087 RESTORE P1) — separate from daemon's preview |
| `python -m sidequest.cli.corpusmine` | `cli/corpusmine/` + `__main__.py` | **Live** (module-runnable; not in `[project.scripts]`) |
| `python -m sidequest.cli.corpusdiff` | `cli/corpusdiff/` + `__main__.py` | **Live** (module-runnable) |
| `python -m sidequest.cli.corpuslabel` | `cli/corpuslabel/` + `__main__.py` | **Live** (module-runnable) |

---

## Dark / Partial (ADR-087 Restoration Roster)

Verdicts and tiers per ADR-087 (last sweep 2026-05-02).

### P0 — this sprint or next

| Subsystem | ADR-087 verdict |
|-----------|------------------|
| ADR-059 pregen dispatch (server invokes namegen/encountergen/loadoutgen at turn-time) | RESTORE |
| `sidequest-namegen` rewire (entry point + dispatch integration) | REWIRE |
| `sidequest-encountergen` (currently empty stub) | RESTORE |
| `sidequest-loadoutgen` (currently empty stub) | RESTORE |
| ADR-092 scene fixture hydrator + `POST /dev/scene/{name}` (supersedes ADR-069) | RESTORE |

> Confrontation Engine port-drift VERIFY demoted from P0 to P3 polish on 2026-05-02 — Pillars 1+2 verified live; only `mood_aliases` consumer remains.

### P1 — within current epic window

Trope engine (ADR-018), NPC disposition Attitude transitions (ADR-020), sealed-letter broader scope (Phase-5 module landed; ADR-024/028 still partial), continuity validator, patch legality gate (currently *partial* in `telemetry/validator.py`), subsystem coverage tracker (`CoverageGap` events), `sidequest-promptpreview` server-side CLI, inventory extractor (VERIFY first).

### P2 — design-ready, next-epic candidate

Gossip engine (ADR-053), accusation logic (ADR-053), genie wish consequence engine (ADR-041), OCEAN shift proposals (ADR-042), chase engine (ADR-017 — affects road_warrior and space_opera Ship Block), catch-up dispatch handler, lore filter, `sidequest-validate` CLI expansion, scene relevance validator (REDESIGN under ADR-086), room graph per-transition mechanics + new map wire message (ADR-055), Edge/Composure Epic 39 per-class wiring + push-currency rituals (ADR-078).

### P3 — flavor / low urgency

Beat filter, test-support helpers (VERIFY), `mood_aliases` alias-chain consumer (ADR-033 Pillar 3), per-genre `dice.yaml` theming (ADR-075).

### Deferred — markers confirmed

Affinity progression (P6-deferred at `game/character.py:55-64`), advancement effect variants v1 (ADR-081 accepted/deferred — upstream-blocked on per-class edge config), Edge/Composure Epic 39 wiring residue (rides P2 item), tactical grid engine (ADR-071 Proposed — protocol live), 3D dice rendering polish (ADR-075 partial), merchant system (no ADR — write one first), combat mechanics detail beyond Epic 28 restoration.

### Superseded / collapsed

Theme rotator (SUPERSEDED — no demonstrated value), scrapbook standalone (collapse into daemon — pending VERIFY), separate narrator/troper/resonator/world_builder agents (collapsed under ADR-067), 14-tool abstraction (collapsed under ADR-059 — ADR-057 deprecated 2026-05-02 as infeasible under ADR-001), ADR-066 persistent narrator session (superseded by ADR-098 stateless turns).

### Do not restore

Speculative prerendering (ADR-044 historical 2026-05-02 — TTS-deprecated premise), conlang morpheme glossary (ADR-043 superseded by ADR-091 culture-corpus + Markov).

---

## Genre Pack Status (Pointer)

7 pack directories under `sidequest-content/genre_packs/`. Five packs (`caverns_and_claudes`, `elemental_harmony`, `mutant_wasteland`, `space_opera`, `tea_and_murder`) have full pack-level runtime; the lobby world picker currently shows **3 worlds** (caverns_sunden, flickering_reach, coyote_star) after the 2026-05 M2 reshuffle parked `aureate_span`, `burning_peace`, `shattered_accord`, and `blackthorn_moor` into workshopping. The `heavy_metal` and `spaghetti_western` production directories are empty shells; their YAMLs live in `genre_workshopping/`. Four other packs (`low_fantasy`, `neon_dystopia`, `pulp_noir`, `road_warrior`) are workshop-only.

**Highlights since the 2026-04-30 pack-status snapshot:**
- **caverns_and_claudes** — added Sünden hamlet world (`caverns_sunden`, formerly `caverns_three_sins`), authored Brecca + hamlet faction/lore/portraits, 6 hamlet music tracks (ACE-Step), Sünden-faith expansion, world-level visual_style; four classic B/X classes (fighter/mage/cleric/thief) + B/X B26 saving throws + memorization + morale; signature abilities (Taunt/Turn Undead/Backstab); silver currency
- **mutant_wasteland** — `flickering_reach` world-level `visual_style.yaml` authored (content PR #206)
- **space_opera** — `coyote_star` (renamed from `coyote_reach`) is the Magic + Rig MVP flagship; chapter→trope wiring engaged (content PR #209)

Pack-by-pack: [`docs/genre-pack-status.md`](genre-pack-status.md) (stale in places — Sünden world not yet listed there).

---

## Sprint 3 Snapshot (Closing)

Two epics open: **Epic 45** (Playtest 3 closeout) and **Epic 47** (Magic system + Rig MVP). Progress: 299/339 points, 8 in backlog as of 2026-05-11.

**Epic 39 closed (2026-05-10)** — Edge/Composure chargen seed (CON-mod) and per-class Edge config landed (stories 39-9, 39-10).

**Epic 45 — three lanes:**
- **(A) MP correctness** — sealed-letter shared-world delta, turn-barrier fix, momentum sync (45-1, 45-2, 45-3 done)
- **(B) State write-back hygiene** — 21 stories carrying placeholder cleanup, content-drift triage, OTEL/tuning work (45-4 through 45-23 done)
- **(C) UI/cleanup tax + tuning + render observability** — chargen polish, web-socket tuning, render trigger policy, image silent-fallback teardown, Z-Image high-fidelity tier, OTEL exporter fix (45-24 through 45-42 done)
- **Snapshot split-brain port-drift** — 45-45 (Wave 1: dedup+rename), 45-47 (Wave 2A: NPC pool/state split), 45-48 (Wave 2B: per-character locations) done; 45-46 (Wave 1 cleanup), 45-52 (Wave 2A cleanup) backlog
- **Orrery v2 visual restoration** (ADR-094) shipped via 45-43 + 45-40
- **ADR-066 §8 narrator session crash recovery superseded by ADR-098** — stateless narrator turns (PR #247 + linked); §7/§9/§10 proactive watchdog backlog now moot

**Epic 47 — Magic system landed in waves:** Phase 4 verification + smoke (47-1 done, 47-2 PARTIAL-PASS), Phase 5 confrontations wired (47-3 done — five confrontations live), Rig MVP Phase C tea-brew confrontation (47-4 done), Phase 6 multiplayer playtest (47-5 backlog), tea-ritual three-layer fix (47-6 done), magic state bars uninit warning (47-7 done), Coyote Object salvage hooks design (47-8 backlog), plugin-aware proactive prompt (47-9 done), C&C memorization wiring (47-10 done).

**Epic 48 — Local-LLM Workstream** — 4 stories, 24 pts; design + as-installed notes landed for local Qwen code editor MVP and built-in `ollama launch claude` integration.

---

## What's Playtest-Ready Today (Post-Port)

The full game loop is wired end-to-end in Python: connect → create character (now with C&C visible-dice flow + four classic classes) → play → narrate (now streaming by default, stateless per-turn) → render images → play music (ACE-Step tracks now serve from R2). Multiplayer works with turn barriers, adaptive batching, party action composition, perception rewriting, live teammate typing, MP companion recruit, and the sealed-letter shared-world delta. The unified narrator (ADR-067 + ADR-098) handles exploration, dialogue, combat narration, and chase narration as stateless per-turn invocations; auxiliary subsystem agents (chassis_voice, distinctive_detail, npc_agency, reflect_absence) run off the critical path. Pacing engine shapes delivery via TensionTracker. Lore RAG, OCEAN profiles, footnoted narration with journal callback, projection-filtered per-player views, and Knowledge-Journal keyword filter are all live.

**The big feature surfaces since the port:**
- **Stateless narrator (ADR-098)** — `claude -p` invoked fresh each turn; no `--resume`, no `narrator_session_id`, bounded per-turn prompt; warm-reboot/§8 recovery deleted
- **Narrator streaming on by default (2026-05-11)** — `NarrationDelta` renders live in `NarrationScroll`; stalled-stream interstitial after 5s
- **Magic system** — plugin protocol with three plugins live (`innate_v1`, `item_legacy_v1`, `learned_v1`/Vancian memorization for C&C); ledger bars; five wired confrontations; validator with severity-tiered flags
- **C&C B/X classic classes + B26 saving throws + class beats + morale + signature abilities** — Fighter Taunt, Cleric Turn Undead, Thief Backstab; class-aware spell slot allocation
- **Edge / Composure** — Edge primitive on `CreatureCore` replaces HP across the codebase (45-35); `apply_edge_delta` wired from yield + session paths; threshold helper extracted; advancement-effect data shapes loaded; CON-mod chargen Edge seed (ADR-078 amendment)
- **Orbital chart** — server-side SVG renderer, course plotting (eta + Δv), conjunction beats, three-strategy label placement (ADR-094); chart-as-calendar HUD overlays; session-bound chart re-fetch
- **Interior / Ship widget** — `voidborn_freighter` (Kestrel) 2x2 chassis interior SVG renderer; client `ShipWidget` mounted in dock
- **3D dice** — Three.js + R3F + Rapier inline tray; Tie outcome distinct from Fail
- **Dogfight** — sealed-letter cross-product resolution live; space_opera content shipping
- **Cavern renderer revival (ADR-096)** — image-mode `TacticalGridRenderer` + Automapper settlement branch
- **GameBoard widget architecture** — modular widget shell with registry; replaces fixed-panel layout
- **Dark-Folio illuminated-manuscript visual** — applied to Knowledge Journal, Inventory, Character, Narration Pane; +2pt body copy across panels
- **Live teammate typing** — InputBar draft text broadcasts to peers via `ACTION_REVEAL`
- **Dashboard restoration (ADR-090)** — eight tabs (Console, Encounter, Lore, Prompt, State, Subsystems, Timeline, Timing) plus five chart primitives; OTEL exporter to Jaeger flowing; Prompt tab now shows system/user split + bounded marker + expandable section viewer
- **Cloud media** — daemon R2 writer (renders + music + audio + hero images); `/internal/watcher/emit` daemon→server OTEL bridge; `asset_urls` seam routes media URLs end-to-end
- **Daemon music tier (ADR-095)** — ACE-Step pipeline, operator-triggered via `scripts/generate_music.py --genre <pack>`; OGG → R2
- **Decomposed projection** — eleven-module `game/projection/` package with predicate validators and invariants
- **Decomposed telemetry** — 50+ span modules in `telemetry/spans/`

OTEL coverage is the strongest it has ever been. The biggest known gaps for Keith-as-player and Sebastien (mechanics-first) remain on the ADR-087 restoration roster: trope engine beat firing, disposition Attitude transitions, continuity validator, and pregen dispatch. Each is what makes the difference between a narrator that improvises convincingly and a narrator the GM panel can actually keep honest. CLAUDE.md says it plain: _"The GM panel is the lie detector."_ Sprint 3 closes the playtest debt; the next sprint inherits ADR-087's P0 tier.

**Best playtest experience today:** Three lobby-selectable worlds post the 2026-05 M2 reshuffle —
- `caverns_and_claudes/caverns_sunden` (the Sünden hamlet hub, with grimvault/horden/mawdeep/primetime/dungeon_survivor as nested dungeons; reference pack carrying the four B/X classic classes, B26 saving throws, learned_v1 memorization, morale, and class signature abilities)
- `mutant_wasteland/flickering_reach` (the only fully spoilable world)
- `space_opera/coyote_star` (orbital chart + magic + rig MVP — flagship for Epic 47 work)

`elemental_harmony` and `tea_and_murder` retain their pack-level runtime but their worlds (`burning_peace`/`shattered_accord` and `blackthorn_moor`) are parked in workshopping pending the M2 completeness review — neither pack currently has a lobby-selectable world. The full media pipeline, faction-driven world, OCEAN-flavored NPCs, footnoted narration with journal, confrontation engine with genre-typed resource pools where wired, Edge/Composure replacing HP, magic ledger bars and five wired confrontations, live teammate typing, and streaming narration are all live across the three production worlds.
