---
id: 109
title: "Persistent Location Descriptions + Mechanical Manifest"
status: accepted
date: 2026-05-19
deciders: ["Keith Avery", "Oberon (Architect agent)"]
supersedes: []
superseded-by: null
related: [3, 14, 26, 31, 55, 88, 96, 100, 101, 103, 104, 106, 107]
tags: [game-systems, frontend-protocol, observability, room-graph]
implementation-status: live
implementation-pointer: "sidequest-server location two-mode resolver + PgPromotionStore + LOCATION_DESCRIPTION msg + sidequest-ui LocationPanel.tsx (54-1..54-9, 55-1)"
---

# ADR-109: Persistent Location Descriptions + Mechanical Manifest

## Status

Accepted. Design detail and per-story decomposition live in
`docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md`.
The per-task plans for Epic 54 and Epic 55 live in
`docs/superpowers/plans/2026-05-19-story-54-*.md` and
`docs/superpowers/plans/2026-05-19-story-55-*.md`. This ADR is the durable
decision record and scope boundary — it locks the contested calls and the
seams, it does not restate the spec.

## Context

The SideQuest narrator (Anthropic SDK per ADR-101) writes convincing prose
with zero mechanical backing. A player who tugs the "rusted chain hanging
from the ceiling" can discover the chain was improv — there is no chain
object, no affordance, just narrator flavor. Sometimes the improv lands;
often it collapses — an overbaited hook (SOUL.md Diamonds-and-Coal) that
the OTEL "lie detector" (CLAUDE.md OTEL Observability Principle) is
designed to catch.

The play table asked for **persistent room/area descriptions, mechanically
backed**. Anything the description names must either be a real game-state
thing with affordances, OR be trivial enough that yes-and promotion handles
player engagement without breaking trust.

This is also a Zork-Problem (SOUL.md) call: the manifest is a
**producer-side contract** (what the narrator and authors may claim), never
a **consumer-side gate** (the closed verb set of "things players may
touch"). The player can always introduce new entities the description
didn't mention; the system says yes.

## Decision

Introduce a typed, persistent `LocationEntity` manifest per location,
backed by a three-tier classification, a two-mode runtime resolver, and a
validator. Five locked calls follow.

### 1. Three-tier manifest

Every named entity in a location's description carries a tier:

- `real_object` — fully bound to a game-state subsystem
  (`location_feature` | `npc` | `item` | `clue` | `scenario_clue`).
  Narrator may mechanically engage it; resolver returns its binding.
- `yes_and` — canonical but mechanically minimal. Engagement is honored;
  promotion lifts a `flavor_only` entry to `yes_and` on first mechanical
  touch.
- `flavor_only` — described but mechanically inert. Engaging it promotes
  it to `yes_and` and writes to `location_promotions`.

### 2. Two-mode resolver

The new `resolve_location_entity(label, region_id, mode, engagement_kind)`
tool has two modes that encode the Zork-Problem-safe split:

- `narrator_proactive` — narrator-side prose claim. Manifest miss =
  contract violation. The narrator's pending mechanical action does NOT
  commit; OTEL fires the lie-detector span.
- `player_initiated` — player-side input. Manifest miss = canonization
  (Yes-And). A new `yes_and_minted` entity is written to
  `location_promotions` and the player's action proceeds.

Pure narration (descriptive prose without mechanical commitment) does
not require resolver calls. Every narrator-side mechanical claim
(damage, move, take, modify) MUST route through the resolver — there
is no "claim without resolve" code path. The implementer enforces this
in the agent tool harness.

### 3. Two production paths, single consumer shape

- **POI worlds** (e.g. `tea_and_murder/glenross`) — hand-authored
  manifest in `cartography.yaml regions[*].entities[]`. Replaces the
  untyped `landmarks[]` string array.
- **Procedural worlds** (`beneath_sunden`) — deterministically composed
  at materialize time by `cookbook/assemble.py` and persisted to
  `<world>/rooms/<id>.yaml` alongside the cavern mask.

Both shapes are consumed by the same loader path. No new top-level
entity competes with `regions[]` or `<world>/rooms/<id>.yaml`. ADR-106's
materializer-emits-region pattern extends naturally.

### 4. Authored content never mutates at runtime

Per-game runtime mutations (flavor_only → yes_and promotion and
player-initiated mints) accumulate in a new `location_promotions`
SQLite table keyed by `(save_id, region_id, entity_id)`. Read-time
merge layers promotions on top of authored. Promotions are **durable**
per the durable-retention principle (project memory); no GC.

### 5. Encounter overlays layer, never destroy

Encounter-bound action overrides contribute an `entity_delta` and a
`prose_suffix` merged at read time. Base description and base manifest
never mutate from overlays. Two overlays on the same room concatenate
in encounter-arrival order (deterministic).

## Consequences

### Positive

- Narrator improv against described entities becomes detectable
  (`location.entity.resolve { mode=narrator_proactive, resolved=false }`).
  GM panel surfaces the count per session; over time, drives prose
  revision work.
- Players can canonize entities (Yes-And, Diamonds-and-Coal). The
  manifest grows from play, not just authoring.
- POI and procedural worlds share one consumer path; the cookbook seam
  (ADR-106) extends naturally with `compose_room_prose()`.
- Action overlays earn their screen-time spike (SOUL.md "Cut the Dull
  Bits") with deterministic merge order and no destructive mutation
  of the base.

### Negative

- New table (`location_promotions`) and new validator (`pf validate
  locations`) — two new surfaces with their own CI footprint.
- Content-side cost: every existing world with a `landmarks[]` array
  needs backfill to typed `entities[]` (mitigated by per-pack
  `generic_allowlist[]` and a non-blocking coherence warning).
- Cookbook dressing pool needs to be authored at 8-12 lines per look
  to avoid procedural-prose repetition (Risks §8).

### Scope boundary (v1)

Out of scope, deferred to follow-up ADRs / stories:

- Player-facing entity chips / clickable manifest in the Location tab.
  **Reinforced exclusion** — surfacing the manifest as a UI verb set
  is itself a Zork violation.
- Multi-language prose, audio cues bound to entities, image
  regeneration on overlay.
- Cross-region entities (NPCs go via the NPC subsystem).
- Per-PC perception filtering on the manifest (ADR-104 / ADR-105).
  All entities universally visible to all seated players in v1.

## Implementation guidance for Dev

The spec at
`docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md`
is authoritative. Per-story plans:

- 54-1 (this ADR)
- 54-2 — Server schema + `LOCATION_DESCRIPTION` WebSocket message
- 54-3 — `pf validate locations`
- 54-4, 54-5 — Content backfills
- 54-6 — Resolver + `location_promotions` table
- 54-7 — Encounter overlays
- 54-8 — OTEL spans + GM-panel surfacing
- 54-9 — `LocationPanel.tsx` UI
- 55-1 — Procedural cookbook description+manifest emit (stitch)

Suggested rollout order (spec §7.4): 54-1 → 54-2 → {54-3, 54-9} → 54-6
→ 54-7 → 54-8 → {54-4, 54-5} → 55-1.

### Reference

- Spec: `docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md`
- Related ADRs: ADR-026 (client state mirror), ADR-031 (Game Watcher —
  semantic telemetry substrate behind the lie-detector span), ADR-100
  (KnownFacts), ADR-103 (native OTEL via tool registry), ADR-104/105
  (perception filtering — out of scope here), ADR-106 (procedural
  megadungeon).
