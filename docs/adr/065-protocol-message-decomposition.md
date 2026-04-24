---
id: 65
title: "Protocol Message Decomposition — Split message.rs by Domain"
status: proposed
date: 2026-04-04
deciders: [Keith]
supersedes: []
superseded-by: null
related: [60]
tags: [codebase-decomposition]
implementation-status: deferred
implementation-pointer: null
---

# ADR-065: Protocol Message Decomposition — Split message.rs by Domain

## Context

`sidequest-protocol/src/message.rs` contains 1,111 lines with 47 struct/enum
definitions and a single large `GameMessage` enum. Every payload type for every
message category lives in this one file:

| Category | Types |
|----------|-------|
| **Core** | `GameMessage` (the top-level enum), `PlayerActionPayload`, `ErrorPayload` |
| **Narration** | `NarrationPayload`, `Footnote`, `FactCategory`, `NarrationChunkPayload`, `NarrationEndPayload`, `ThinkingPayload`, `ChapterMarkerPayload` |
| **Session** | `SessionEventPayload`, `TurnStatusPayload`, `ActionQueuePayload`, `ActionRevealPayload`, `PlayerActionEntry` |
| **Character** | `CharacterCreationPayload`, `CharacterSheetPayload`, `PartyStatusPayload`, `PartyMember`, `CharacterState`, `StatusEffectInfo` |
| **Combat** | `CombatEventPayload`, `CombatEnemy` |
| **World/Map** | `MapUpdatePayload`, `ExploredLocation`, `RoomExitInfo`, `FogBounds`, `InitialState` |
| **Economy** | `InventoryPayload`, `InventoryItem`, `ItemGained`, `StateDelta` |
| **Media** | `ImagePayload`, `AudioCuePayload`, `VoiceSignalPayload`, `VoiceTextPayload`, `TtsStartPayload`, `TtsChunkPayload` |
| **Scenario** | `ScenarioEventPayload`, `AchievementEarnedPayload` |
| **Journal** | `JournalSortOrder`, `JournalRequestPayload`, `JournalResponsePayload`, `JournalEntry` |
| **Narrator config** | `NarratorVerbosity`, `NarratorVocabulary` |

This mirrors the `models.rs` anti-pattern from `sidequest-genre` (ADR-060) — a
type dumping ground where every protocol addition means editing one file.

## Decision

**Split `message.rs` into a `message/` directory grouped by message domain.**

### Module Structure

```
sidequest-protocol/src/message/
├── mod.rs              # GameMessage enum + re-exports
├── narration.rs        # NarrationPayload, Footnote, FactCategory,
│                       #   NarrationChunkPayload, NarrationEndPayload,
│                       #   ThinkingPayload, ChapterMarkerPayload,
│                       #   NarratorVerbosity, NarratorVocabulary
├── session.rs          # SessionEventPayload, TurnStatusPayload,
│                       #   ActionQueuePayload, ActionRevealPayload,
│                       #   PlayerActionPayload, PlayerActionEntry
├── character.rs        # CharacterCreationPayload, CharacterSheetPayload,
│                       #   PartyStatusPayload, PartyMember, CharacterState,
│                       #   CreationChoice, StatusEffectInfo
├── combat.rs           # CombatEventPayload, CombatEnemy
├── world.rs            # MapUpdatePayload, ExploredLocation, RoomExitInfo,
│                       #   FogBounds, InitialState
├── economy.rs          # InventoryPayload, InventoryItem, ItemGained, StateDelta
├── media.rs            # ImagePayload, AudioCuePayload, VoiceSignalPayload,
│                       #   VoiceTextPayload, TtsStartPayload, TtsChunkPayload
├── scenario.rs         # ScenarioEventPayload, AchievementEarnedPayload
├── journal.rs          # JournalSortOrder, JournalRequestPayload,
│                       #   JournalResponsePayload, JournalEntry
└── error.rs            # ErrorPayload
```

### GameMessage Stays in mod.rs

The `GameMessage` enum references all payload types — it's the union type.
It belongs in the module root. Each variant imports its payload from the
appropriate submodule.

### API Preservation

`mod.rs` re-exports all types via `pub use`. Downstream crates continue to use
`use sidequest_protocol::message::NarrationPayload`. Zero-breakage migration.

## Alternatives Considered

### Keep single file, use type aliases
Doesn't reduce the file size or improve discoverability. Rejected.

### One file per payload type
47 files would be over-split. Many payloads are 10-15 lines. Domain grouping
keeps related types together at a manageable granularity. Rejected.

## Consequences

- **Positive:** Adding a new narration payload means editing `narration.rs`, not
  scrolling through 47 other types.
- **Positive:** Protocol reviews can focus on the affected domain module.
- **Positive:** Aligns with the UI's `types/` directory which already groups by
  domain — both sides of the protocol speak the same organizational language.
- **Negative:** `GameMessage` enum in `mod.rs` imports from all submodules.
  Acceptable — it's the point of convergence by definition.
- **Risk:** `combat.rs` may end up very small (2 types). Acceptable — combat
  payloads will grow as the combat system matures. If not, fold into `session.rs`.

## Post-port mapping (ADR-082)

Status in Python: **still unexecuted.** `sidequest-server/sidequest/protocol/messages.py`
remains a single file containing the pydantic discriminated union. The
decomposition plan from the Rust era is preserved here as design intent; when it
is acted on, the expected layout is `protocol/messages/` with domain submodules
(`session.py`, `narration.py`, `combat.py`, etc.) and re-exports through
`__init__.py`. Until then, `messages.py` is the canonical location.

Byte-identical JSON on the wire was a constraint of the port (ADR-082) — any
future decomposition must preserve the discriminator field name (`type`) and
the full payload shapes documented in `docs/api-contract.md`.
