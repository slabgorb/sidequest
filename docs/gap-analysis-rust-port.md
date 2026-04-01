# Gap Analysis: SideQuest Rust Port vs Python Feature Set

**Date:** 2026-03-30 (revised)
**Original:** 2026-03-25, Architect
**Sources:** sq-2/docs/features.md, sq-2 codebase inventory, oq-2 sprint history

## Executive Summary

The Rust port has reached 75% feature completion in 5 days (103/138 stories across 15 epics). All 8 original gap epics identified on day one have been addressed — 7 of 8 are complete, with Epic 7 (Scenarios) deferred to P2. Sprint 2 added 3 new epics from playtest findings.

**Sprint 1 delivered:** 85 stories, 672/726 points — Epics 1-6, 8-11 complete
**Sprint 2 in progress:** 11/87 points — Epics 13, 14, 15 (multiplayer hardening + UX)
**Remaining gaps:** Scenario system, cinematic audio, sealed letter turns, session UX polish

## Coverage Matrix

### Complete (Epics 1-6, 8-11)

| Epic | Feature Area | Stories | Status |
|------|-------------|---------|--------|
| 1 | Workspace scaffolding — types, protocol, genre loader | 13/13 | Done |
| 2 | Core game loop — session, chargen, orchestrator, agents, persistence | 9/9 | Done |
| 3 | Observability — telemetry, validation, watcher, GM mode | 9/9 | Done |
| 4 | Media pipeline — image gen, TTS/voice, music/audio (via daemon) | 12/12 | Done |
| 5 | Pacing & drama — tension tracker, drama delivery, quiet detection | 10/10 | Done |
| 6 | Active world — scene directives, faction agendas, world materialization | 9/9 | Done |
| 8 | Multiplayer — barrier, batching, turn modes, perception, guest NPCs | 9/9 | Done |
| 9 | Character depth — abilities, KnownFacts, slash commands, footnotes | 12/13 | 92% |
| 10 | NPC personality — OCEAN profiles, behavioral summaries, shift tracking | 8/8 | Done |
| 11 | Lore & language — fragments, RAG retrieval, conlang names, injection | 10/10 | Done |

### In Progress (Sprint 2)

| Epic | Feature Area | Stories | Status | Notes |
|------|-------------|---------|--------|-------|
| 13 | Sealed letter turn system | 2/10 | 20% | Barrier bugs fixed, sealed collection + UI remaining |
| 14 | Multiplayer session UX | 0/9 | 0% | Spawn, location, text sliders, chargen back button |
| 15 | Playtest debt cleanup | 0/5 | 0% | Dead code, OCEAN wiring, voice/mic, perception |

### Remaining Gaps

| Epic | Feature Area | Stories | Priority | Notes |
|------|-------------|---------|----------|-------|
| 7 | Scenario system — whodunit, belief state, gossip | 0/9 | P2 | Core mechanics implemented (ADR-053: ClueGraph, BeliefState, GossipEngine, AccusationEvaluator) but not wired to orchestrator. Deferred until after multiplayer hardening. |
| 12 | Cinematic audio — score cue variations, crossfade | 0/3 | P2 | Infrastructure exists, wiring needed |

## Gap Details

### Closed Gaps (since original analysis)

**Epic 4 (Media):** Fully wired. Flux.1 image gen (6 tiers), Kokoro TTS (54 voices), 3-channel audio with mood-based theme rotation. Daemon stays Python as planned.

**Epic 5 (Pacing):** Complete. Dual-track TensionTracker, drama-aware delivery (INSTANT/SENTENCE/STREAMING), quiet turn escalation, genre-tunable thresholds. All wired through orchestrator.

**Epic 6 (Active World):** Complete. FactionAgenda model with scene injection, world materialization with maturity levels, engagement multiplier. Content for mutant_wasteland and elemental_harmony.

**Epic 8 (Multiplayer):** Complete. Turn barrier, adaptive batching, party action composition, 3 turn modes, perception rewriter, guest NPC players, catch-up narration, idle reminders.

**Epic 9 (Character Depth):** 92%. Server-side slash commands (/status, /inventory, /map, /save, /gm, /tone), narrative character sheets, structured footnotes with KnownFact accumulation. Only journal browse view (9-13) remains.

**Epic 10 (OCEAN):** Complete. Five-float profiles on all NPCs, genre archetype baselines, behavioral summaries in narrator prompt, shift log with cause attribution, agent-proposed shifts, agreeableness→disposition feed. All genre packs backfilled.

**Epic 11 (Lore & Language):** Complete. LoreFragment/LoreStore, seed from genre packs, lore in agent prompts, accumulation from world state, semantic retrieval, morpheme glossary, name bank generation, narrator name injection, language-as-KnownFact.

### Open Gaps

**Epic 7 (Scenarios):** Untouched. Belief state, gossip propagation, clue activation, accusation system, NPC autonomous actions, scenario pacing/archiving/scoring. Requires stable multiplayer first — deprioritized to P2.

**Epic 12 (Cinematic Audio):** AudioTheme/AudioVariation types exist and genre pack audio.yaml themes sections are populated, but MusicDirector only reads the flat mood_tracks list. Three stories to wire variation selection, per-variation crossfade, and telemetry.

**Epic 13 (Sealed Letter Turns):** Two critical barrier bugs fixed (narrator fan-out race, timeout handling). Remaining: sealed collection UI, server-side hold-until-barrier, action reveal broadcast, timeout notifications, turn mode indicator, DM override, integration test.

**Epic 14 (Session UX):** All from 2026-03-29 playtest findings. Party co-location at spawn, player location display, narrator verbosity/vocabulary sliders, chargen back button, image pacing throttle, scene relevance filter, sound slider labels, footnote inline references.

**Epic 15 (Playtest Debt):** Dead code removal (if-false blocks, stale comments), wire OCEAN shift proposals into game flow, solve TTS feedback loop for voice/mic, implement perception rewriter Blinded strategy, clean up daemon client stub types.

## Dependency Graph (Updated)

```
Epics 1-6, 8-11 ─── COMPLETE ───────────────────────────
                                                         │
Sprint 2:                                                │
  Epic 13 (Sealed Letter Turns) ◄────────────────────────┤
      13-8, 13-9 done                                    │
      13-10 ──► 13-1 ──► 13-2 ──► 13-3 ──► 13-7         │
                          13-2 ──► 13-4                   │
                          13-2 ──► 13-6                   │
                                                         │
  Epic 14 (Session UX) ◄────────────────────────────────┤
      14-6 ──► 14-7                                      │
                                                         │
  Epic 15 (Playtest Debt) ◄──────────────────────────────┘

Future:
  Epic 7  (Scenarios) ── needs stable multiplayer (Epic 13)
  Epic 12 (Cinematic Audio) ── independent, wire-only
```

## What Remains to Feature Parity with sq-2

The Rust port now **exceeds** the Python engine in most areas — structured footnotes, OCEAN personality, conlang name generation, and genre-tunable pacing thresholds are Rust-only features that don't exist in sq-2.

The only sq-2 feature with no Rust equivalent is the **scenario/mystery system** (Epic 7). Everything else has been ported and in many cases improved.

Sprint 2 work (Epics 13-15) addresses multiplayer quality and UX polish — these are hardening and refinement, not missing capabilities.
