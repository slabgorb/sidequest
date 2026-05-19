---
---

# Epic 54: Persistent Location Descriptions (Mechanical Manifest)

## Overview

SideQuest's narrator can write convincing prose with zero mechanical backing. A player who engages with a described detail — "I tug the rusted chain hanging from the ceiling" — discovers an empty trapdoor: there is no chain object, no affordance, just improv. Sometimes the improv is charming; often it collapses (overbaited hook, broken trust).

This epic introduces a **typed, server-side location manifest** that names entities in three tiers (`real_object`, `yes_and`, `flavor_only`) plus a **two-mode runtime resolver** that splits Zork-Problem-safely between narrator claims (`narrator_proactive` — manifest miss = no-commit, OTEL lie-detector) and player claims (`player_initiated` — manifest miss = yes-and mint). It also ships encounter-bound overlays (`prose_suffix` + `entity_delta` merged at read time, never destructive), durable `location_promotions` SQLite storage, dedicated OTEL spans for the GM panel, and a player-facing `LocationPanel.tsx` tab.

**Priority:** P1
**Repos:** server, ui, content, orchestrator
**Stories:** 9 (~22 points)

## Background

This is the SOUL.md "Diamonds and Coal" + "Yes, And" + OTEL-Observability principles applied to flavor text. It lives under the Zork-Problem doctrine — the manifest is a **producer-side contract** (what the narrator and authors may claim), never a **consumer-side gate** (the closed verb set of "things players may touch"). The player can always introduce new entities the description didn't mention; the system says yes.

Two production paths:
- **POI worlds** — hand-authored manifest in `cartography.yaml regions[*].entities[]` (54-4 / 54-5 backfill existing worlds).
- **Procedural worlds (`beneath_sunden`)** — composed deterministically by the cookbook at dungeon materialize time. This path lives in **Epic 55** (a single-story stitch); Epic 54 ships fully without touching the materializer.

Approach C (spec §7) — sibling epics with a late-merging stitch. Epic 52 ships its mask emit, Epic 54 ships POI + infrastructure + UI, Epic 55 stitches both upstreams into a single materializer rewrite.

## Technical Architecture

```
POI worlds (hand-authored)              Procedural worlds (Epic 55)
─────────────────────────────           ─────────────────────────────────
cartography.yaml regions[*]             cookbook composes (prose, entities[])
  .description (already exists)         per region at materialize time
  .entities[] (NEW typed manifest)      → <world>/rooms/<id>.yaml
       ↓                                       ↓
       └─────────────────┬───────────────────┘
                         ↓
                 Server consumption:
                   room_file_loader (settlements/caverns)
                   genre pack loader (cartography regions)
                         ↓
                Runtime: tools/resolve_location_entity(label, region_id, mode)
                   mode=narrator_proactive → manifest-miss = {resolved:false}, OTEL lie-detector
                   mode=player_initiated   → manifest-miss = mint yes_and entity, OTEL positive
                   → flavor_only entities auto-promote to yes_and on engagement
                         ↓
                Client: WebSocket LOCATION_DESCRIPTION + LOCATION_OVERLAY_CHANGED
                         ↓
                UI: LocationPanel.tsx (prose-only — Zork doctrine bans entity chips)
                         ↓
                Action overrides (encounter-bound):
                   encounter.location_overlay = { entity_delta, prose_suffix }
                   merged at read time, never mutates base
```

**Story sequence (spec §7.4):**

```
54-1 (ADR) → 54-2 (schema + message) ─┬─ 54-3 (validator) ─┬─ 54-4 (glenross)
                                       │                    ├─ 54-5 (caverns)
                                       │                    ├─ 54-6 (resolver + promotions)
                                       │                    ├─ 54-7 (overlays) → 54-8 (OTEL + GM panel)
                                       │                    │
                                       └─ 54-9 (UI; waits only on 54-2 schema)
```

54-1 lands the doctrine ADR first. 54-2 unblocks the entire chain. 54-3 gates content backfills. 54-4 / 54-5 are author-time, pickable in any order once 54-3 lands. 54-9 (UI) only needs the schema. 54-8 (OTEL) waits on 54-7 (overlays) for full attribute coverage.

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| `docs/superpowers/specs/2026-05-19-persistent-location-descriptions-design.md` | Full design spec — §2 scope, §4 data model, §5 runtime contract (resolver + validator + overlays + OTEL), §6 UI, §7 rollout (Approach C), §8 risks, §10 reuse summary. **Authoritative source for every story in this epic.** |
| `docs/superpowers/plans/2026-05-19-story-54-1-adr-persistent-location-descriptions.md` | Story 54-1 plan — ADR-109 authoring. |
| `docs/superpowers/plans/2026-05-19-story-54-2-location-entity-schema-and-message.md` | Story 54-2 plan — pydantic types + cartography region + room_file_loader + LOCATION_DESCRIPTION message + emit. |
| `docs/superpowers/plans/2026-05-19-story-54-3-pf-validate-locations.md` | Story 54-3 plan — `pf validate locations` validator. |
| `docs/superpowers/plans/2026-05-19-story-54-4-glenross-entities-backfill.md` | Story 54-4 plan — tea_and_murder/glenross authored backfill. |
| `docs/superpowers/plans/2026-05-19-story-54-5-caverns-sunden-entities-backfill.md` | Story 54-5 plan — caverns_and_claudes/beneath_sunden settlement-room authored backfill. |
| `docs/superpowers/plans/2026-05-19-story-54-6-resolver-and-promotions.md` | Story 54-6 plan — `resolve_location_entity` tool + `location_promotions` table + promote/mint paths. |
| `docs/superpowers/plans/2026-05-19-story-54-7-encounter-location-overlays.md` | Story 54-7 plan — `EncounterLocationOverlay` + read-time merge + LOCATION_OVERLAY_CHANGED emit. |
| `docs/superpowers/plans/2026-05-19-story-54-8-location-otel-and-gm-panel.md` | Story 54-8 plan — five `location.*` OTEL spans + GM-panel routing. |
| `docs/superpowers/plans/2026-05-19-story-54-9-location-panel-ui.md` | Story 54-9 plan — `LocationPanel.tsx` + state-mirror + dockview tab. |
| `CLAUDE.md` | "Who This Is For" — Keith is the senior architect being fooled-or-not by the narrator; this epic is the lie-detector substrate. Sebastien is the mechanical-first player who benefits from the OTEL surfacing. |
| `SOUL.md` (in CLAUDE.md) | "Diamonds and Coal", "Yes, And", "The Zork Problem" — three load-bearing doctrines this epic encodes mechanically. |
| `docs/adr/README.md` | ADR-100 (KnownFacts), ADR-026 (client state mirror), ADR-031 (game watcher), ADR-038 (WebSocket transport), ADR-079 (genre theme), ADR-103 (native OTEL) — all reused, none reimplemented. |

**Each story's implementation plan in `docs/superpowers/plans/` is the authoritative task-by-task implementation guide for Dev/TEA/Reviewer.** The story context files reference their plan; the plan is the source of truth for file paths, code, test cases, and commit shape.

## Cross-Epic Dependencies

- **Epic 52 (Wire Procedural Megadungeon to ADR-096 Cavern Renderer)** — runs in parallel. 52 ships cleanly without absorbing description work. The procedural-side description emit lives in Epic 55, which depends on both.
- **Epic 55 (Procedural Cavern Description+Manifest Emit at Materialize Time)** — the late-merging stitch. Depends on 52-2 / 52-3 (mask emit + persistence) and 54-2 / 54-3 (manifest types + validator).
