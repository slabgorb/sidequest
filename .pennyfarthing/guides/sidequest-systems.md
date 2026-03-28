# SideQuest Systems Map

Reference for all agents working on the SideQuest Rust codebase. This is what's
built, where it lives, and what to NOT recreate.

<before-coding>
## Before Writing ANY Code

1. Read the CLAUDE.md in the crate you're modifying
2. Grep for the type/function you're about to create — if it exists, USE it
3. Check this guide for the system you're touching — it may already be wired

**The most common agent failure is recreating something that already exists.**
</before-coding>

<existing-systems>

## Complete Systems — Do Not Rewrite

<system name="combat" status="complete" crate="sidequest-game">
  <files>combat.rs, combatant.rs, hp.rs</files>
  <related>turn.rs, turn_mode.rs, barrier.rs (turn sequencing)</related>
  <entry-point>CombatState checked in dispatch_player_action(); IntentRouter routes to CreatureSmith when in_combat=true</entry-point>
  <wired>Yes — TurnContext.in_combat drives agent routing, CombatState in GameSnapshot</wired>
  <do-not>Do NOT stub CombatState. Do NOT create a new combat module. Do NOT add combat logic to the narrator — CreatureSmith handles it.</do-not>
</system>

<system name="inventory" status="complete" crate="sidequest-game">
  <files>inventory.rs (346 LOC)</files>
  <types>Item (with narrative_weight evolution), Inventory, InventoryError</types>
  <entry-point>Character.inventory field, populated at session load lib.rs:1288</entry-point>
  <wired>Yes — /inventory slash command reads it, state patches write it, narrator prompt includes it</wired>
  <do-not>Do NOT use Vec of String for items. Use the Item struct. Items evolve via narrative_weight (unnamed at 0.0, named at 0.5, evolved at 0.7 per ADR-021).</do-not>
</system>

<system name="slash-commands" status="complete" crate="sidequest-game">
  <files>slash_router.rs (106 LOC), commands.rs (316 LOC)</files>
  <commands>/status, /inventory, /map, /save, /help (built-in)</commands>
  <entry-point>dispatch_player_action() checks for slash prefix before sending to orchestrator</entry-point>
  <wired>Yes — all 5 commands registered, /help auto-generated from registry</wired>
  <do-not>Do NOT bypass SlashRouter. New commands implement CommandHandler trait and register via slash_router.register().</do-not>
</system>

<system name="trope-engine" status="complete" crate="sidequest-game">
  <files>trope.rs (225 LOC)</files>
  <related>engagement.rs, trope_alignment.rs (in sidequest-agents)</related>
  <entry-point>TropeEngine::tick() runs every turn at lib.rs:~2495</entry-point>
  <wired>Yes — passive progression + keyword modifiers + escalation beats</wired>
  <do-not>Do NOT confuse TropeEngine (mechanical progression, COMPLETE) with the Troper agent (LLM-driven trope activation, STUB). The engine ticks automatically; the agent would inject narrative beats.</do-not>
</system>

<system name="intent-classification" status="complete" crate="sidequest-agents">
  <files>intent_router.rs (251 LOC)</files>
  <entry-point>Orchestrator::process_action() calls IntentRouter first</entry-point>
  <wired>Yes — 2-tier: state override (in_combat->Combat) then keyword fallback. ADR-032.</wired>
  <do-not>Do NOT add a third classification tier without updating ADR-032. Do NOT call the LLM for intent classification — it's synchronous keywords only.</do-not>
</system>

<system name="persistence" status="complete" crate="sidequest-game">
  <files>persistence.rs (581 LOC)</files>
  <types>SqliteStore, PersistenceWorker, PersistenceHandle, SavedSession</types>
  <entry-point>PersistenceWorker runs as tokio task, receives commands via mpsc</entry-point>
  <wired>Yes — auto-save after every turn, one .db per genre/world session</wired>
  <do-not>Do NOT access SQLite directly — use PersistenceHandle (the mpsc sender). SqliteStore is !Send (single-threaded actor pattern).</do-not>
</system>

<system name="lore" status="complete" crate="sidequest-game">
  <files>lore.rs (2,746 LOC — the largest module)</files>
  <types>LoreStore, LoreFragment, LoreCategory, LoreSource</types>
  <entry-point>GameSnapshot.lore, seeded from char creation and genre pack</entry-point>
  <wired>Yes — category/keyword/semantic search, budget-aware prompt selection</wired>
  <do-not>Do NOT create a separate knowledge base. LoreStore IS the knowledge base. It has embedding-based similarity search built in.</do-not>
</system>

<system name="tension-pacing" status="complete" crate="sidequest-game">
  <files>tension_tracker.rs (780 LOC)</files>
  <types>TensionTracker, PacingHint, EventSpike</types>
  <entry-point>Dual-track: action_tension (gambler's ramp) + stakes_tension (HP-based)</entry-point>
  <wired>Yes — produces PacingHint injected into narrator prompt (drama_weight, target_sentences, delivery_mode)</wired>
  <do-not>Do NOT add separate pacing logic. TensionTracker drives all pacing decisions.</do-not>
</system>

<system name="render-pipeline" status="complete" crate="sidequest-game + sidequest-server">
  <files>subject.rs, render_queue.rs, beat_filter.rs, prerender.rs (game); render_integration.rs (server)</files>
  <flow>Narration -> SubjectExtractor -> BeatFilter -> RenderQueue -> Daemon -> IMAGE broadcast</flow>
  <wired>Yes — full pipeline from narration text to client image delivery</wired>
  <do-not>Do NOT create a new image pipeline. The existing one handles extraction, filtering, dedup (SHA256), async queuing, and speculative prerendering.</do-not>
</system>

<system name="tts-streaming" status="complete" crate="sidequest-game">
  <files>tts_stream.rs (211 LOC), segmenter.rs (274 LOC)</files>
  <types>TtsSegment, TtsSynthesizer trait, TtsStreamer, SentenceSegmenter</types>
  <flow>Narration -> SentenceSegmenter -> TtsSegments -> TtsStreamer (Start/Chunk*/End)</flow>
  <wired>Yes — pluggable via TtsSynthesizer trait for dependency injection</wired>
  <do-not>Do NOT split sentences manually. Use SentenceSegmenter — it handles abbreviations, ellipsis, multi-period patterns.</do-not>
</system>

<system name="music" status="complete" crate="sidequest-game">
  <files>music_director.rs (667 LOC), audio_mixer.rs (369 LOC), theme_rotator.rs (323 LOC)</files>
  <types>MusicDirector, AudioMixer, ThemeRotator, Mood, AudioCue</types>
  <wired>Yes — mood classification from narration, track selection from genre pack .ogg files, 3-channel ducking during TTS</wired>
  <do-not>Music tracks are pre-rendered .ogg files from genre_packs, NOT generated by daemon. Do NOT check daemon for music issues.</do-not>
</system>

<system name="multiplayer" status="complete" crate="sidequest-game + sidequest-server">
  <files>multiplayer.rs, barrier.rs, turn_mode.rs, turn_reminder.rs, guest_npc.rs (game); shared_session.rs (server)</files>
  <types>MultiplayerSession, TurnBarrier, TurnMode, SharedGameSession</types>
  <wired>Yes — session coordination, barrier sync, adaptive timeout, guest NPC roles</wired>
  <do-not>Do NOT create separate session tracking. SharedGameSession is keyed by "genre:world" and manages all per-world state.</do-not>
</system>

<system name="character-creation" status="complete" crate="sidequest-game">
  <files>builder.rs (903 LOC)</files>
  <types>CharacterBuilder (state machine: InProgress -> AwaitingFollowup -> Confirmation)</types>
  <wired>Yes — loads CharCreationScene from genre pack, produces Character with narrative hooks and lore anchors</wired>
  <do-not>Do NOT bypass CharacterBuilder. It handles scene sequencing, mechanical effects, and narrative hook extraction.</do-not>
</system>

<system name="protocol" status="complete" crate="sidequest-protocol">
  <files>message.rs (763 LOC), types.rs, sanitize.rs</files>
  <types>GameMessage (23 variants), NarrationPayload, StateDelta, NonBlankString</types>
  <wired>Yes — all WebSocket communication between server and client</wired>
  <do-not>NarrationPayload has 3 fields only (text, state_delta, footnotes). Adding fields requires updating BOTH server and client due to deny_unknown_fields.</do-not>
</system>

<system name="genre-loader" status="complete" crate="sidequest-genre">
  <files>loader.rs, models.rs (1,827 LOC), resolve.rs, validate.rs</files>
  <types>GenrePack, World, OceanProfile, DramaThresholds, VisualStyle</types>
  <wired>Yes — unified YAML loading with inheritance resolution and validation</wired>
  <do-not>Genre packs live at sidequest-content/genre_packs/, NOT oq-2/genre_packs/. OceanProfile is defined here (re-exported by sidequest-game).</do-not>
</system>

<system name="prompt-framework" status="complete" crate="sidequest-agents">
  <files>prompt_framework/ (1,484 LOC total — mod.rs, types.rs, soul.rs, tests.rs)</files>
  <types>PromptSection, AttentionZone (Primacy/Situational/Anchoring/Grounding), SectionCategory</types>
  <wired>Yes — zone-ordered prompt assembly with telemetry instrumentation (story 3-1)</wired>
  <do-not>Do NOT compose prompts manually. Use ContextBuilder with PromptSection and AttentionZone for proper ordering and telemetry.</do-not>
</system>

<system name="npc-model" status="complete" crate="sidequest-game">
  <files>npc.rs (297 LOC), disposition.rs (223 LOC), creature_core.rs (129 LOC)</files>
  <types>Npc, Disposition, Attitude, CreatureCore</types>
  <wired>Yes — identity-locked fields (pronouns, appearance), OCEAN personality, disposition->attitude derivation (ADR-020)</wired>
  <do-not>Do NOT overwrite identity-locked fields. merge_patch() protects them. Do NOT store disposition as a string — use the Disposition newtype.</do-not>
</system>

</existing-systems>

<stub-systems>

## Stubs — Exist but NOT Functional

These files exist and compile but have minimal/no real implementation.
Do NOT integrate with them as-is. They need full implementation.

<system name="resonator-agent" status="stub" crate="sidequest-agents">
  <files>resonator.rs (49 LOC — scaffolding only)</files>
  <python-original>sq-1: agents/hook_refiner.py (~150 LOC) + agents/perception_rewriter.py (~190 LOC)</python-original>
  <purpose>Two responsibilities: (1) polish player narrative hooks via LLM, (2) rewrite narration per-player based on perception effects</purpose>
</system>

<system name="troper-agent" status="stub" crate="sidequest-agents">
  <files>troper.rs (49 LOC — scaffolding only)</files>
  <python-original>No discrete class — logic split across sq-1: game/state.py + state_processor.py + prompt_composer.py</python-original>
  <purpose>LLM-driven trope activation and narrative beat injection. NOT mechanical progression (that's TropeEngine in sidequest-game, which IS complete).</purpose>
</system>

<system name="world-builder-agent" status="stub" crate="sidequest-agents">
  <files>world_builder.rs (49 LOC — scaffolding only)</files>
  <python-original>sq-1: game/world_builder.py (~500 LOC) — builder pattern for dense GameState</python-original>
  <purpose>Materialize world state at maturity levels. Note: world_materialization.rs in sidequest-game already handles the maturity model.</purpose>
</system>

<system name="perception-rewriting" status="stub" crate="sidequest-game">
  <files>perception.rs (169 LOC — types compile, methods unimplemented)</files>
  <types>PerceptionFilter, PerceptualEffect, RewriteStrategy trait, PerceptionRewriter</types>
  <purpose>Per-player narration rewriting (blinded, charmed, dominated). RED phase — story 8-6.</purpose>
</system>

<system name="ocean-shift-proposals" status="stub" crate="sidequest-game">
  <files>ocean_shift_proposals.rs (106 LOC — rules defined, not wired)</files>
  <purpose>Event-driven personality evolution. Mapping exists but not connected to story flow. Story 10-6.</purpose>
</system>

</stub-systems>

<not-started>

## Not Started

- **Scenario System** — Epic 7. BeliefState, gossip propagation, clue activation,
  accusations, NPC autonomous actions, scenario pacing, archiver, scoring,
  ScenarioEngine integration. Zero code exists.

</not-started>

<architecture-notes>

## Architecture Notes

### Cross-Cutting Concerns
- **Combat** spans 6+ files across 2 crates (game: combat.rs, combatant.rs, hp.rs,
  turn.rs, turn_mode.rs, barrier.rs; server: dispatch_player_action routing).
  Future refactoring should extract combat orchestration into its own module.
- **dispatch_player_action()** in sidequest-server/lib.rs is ~1,950 lines. Read the
  full function before modifying. Line numbers shift every PR.

### Crate Dependency Flow
```
sidequest-protocol  (types only, no logic dependencies)
       ↑
sidequest-genre     (YAML loading, models)
       ↑
sidequest-game      (state, mechanics, audio, persistence)
       ↑
sidequest-agents    (LLM orchestration, prompt framework)
       ↑
sidequest-server    (axum, WebSocket, wires everything together)
```

### Key Patterns
- Composition over inheritance (CreatureCore embedded in Character/Npc)
- Trait objects for pluggable strategies (Combatant, CommandHandler, TtsSynthesizer, RewriteStrategy)
- Typed patches (WorldStatePatch, NpcPatch) for composable state mutations
- Actor pattern for !Send resources (PersistenceWorker owns SQLite)
- Newtype pattern for semantic richness (Disposition, TropeStatus)

</architecture-notes>
