# Epic 22: Seed Tropes — Narrative Variety via Schrödinger's Gun

## Overview

Expand the trope engine with short-arc **seed tropes** — deliberately vague narrative
events (a sealed letter, a missing item, an uneasy innkeeper) randomly dealt each
session from a per-pack deck. Seeds inject as background context; the LLM narrator
retroactively connects them to macro-trope escalations, creating emergent
foreshadowing. Expired seeds linger as *ghosts* for cross-session callbacks. The player
experiences a world with narrative memory and variety.

**Priority:** P1
**Repos:** server, content, orchestrator
**Stories:** 5 (16 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-018 Trope Engine** (`docs/adr/adr-018-*.md`) | Existing `TropeDefinition` lifecycle, escalation, passive progression — the sibling that `SeedTrope` parallels |
| **ADR-009 Attention-Aware Prompt Zones** (`docs/adr/adr-009-*.md`) | VALLEY zone is the 22-3 injection target for active-seed context |
| **ADR-023 Session Persistence** (`docs/adr/adr-023-*.md`) | `game_state.snapshot_json` column — deck state, active seeds, and ghosts persist here |
| **ADR-082 Port to Python** (`docs/adr/adr-082-*.md`) | Backend is Python post-port — no Rust |

## Background

The trope engine (ADR-018) is live: `TropeDefinition` at
`sidequest-server/sidequest/genre/models/tropes.py:42` carries escalation,
passive_progression, and tags. These are **macro tropes** — long-lived narrative arcs
that escalate over many turns.

What the world lacks is *variety between sessions*. Two playthroughs of the same world
open the same way. Seed tropes solve this: a per-pack deck of short-arc, deliberately
underspecified narrative events is shuffled and dealt each session. A seed is a
"Schrödinger's Gun" — placed without a predetermined payoff, it stays ambiguous until
the narrator retroactively wires it to whatever macro-trope escalation actually
emerges. The sealed letter *becomes* a clue to the murder the players stumbled into,
because the narrator connected it after the fact, not because it was scripted.

Seeds have a different lifecycle from macro tropes (short-arc + deck draw + ghost
retention), so they want a **sibling `SeedTrope` type**, not field extension on
`TropeDefinition`. When a seed's lifespan elapses without being taken, it doesn't
vanish — it becomes a *ghost*, retained for cross-session callbacks ("the matter of
that sealed letter, weeks ago…"). This is the SOUL "untaken bait" doctrine made
mechanical: the hook stays in the water.

**Phasing:** Phase 1 dogfoods a single pack (`tea_and_murder`) to align with Epic 24's
grounding playtest. Other-pack seed authoring follows as separate stories once the loop
is proven end-to-end.

> **Doctrine note:** The "sealed letter" here is a *thematic seed example*, NOT the
> multiplayer submit-and-wait barrier. Seeds belong in the VALLEY (context) zone, not
> the Recency zone — so the deferred ADR-111/112 guardrail-prose migrations don't
> affect them.

## Technical Architecture

Seeds follow the existing trope-engine pattern but as a parallel type with its own
lifecycle and persistence.

**Component relationships:**

```
genre pack YAML (seeds)  ──load──▶  SeedDeck (per genre/world/session)
                                        │ draw() without replacement
                                        ▼
                                   active_seeds: list[SeedState]  ──lifespan elapses──▶  seed_ghosts: list[SeedGhost]
                                        │                                                    │
                                        └──────────────── persisted in GameSnapshot ◀────────┘
                                                          (game_state.snapshot_json, ADR-023)
                                                                    │
                                                       VALLEY-zone narrator injection (22-3)
                                                                    │
                                                          OTEL spans (22-4)
```

**Key files:**

| File | New/Existing | Role |
|------|--------------|------|
| `sidequest/genre/models/tropes.py` | existing (extend) | `TropeDefinition` lives at line 42; add `SeedTrope`, `SeedState`, `SeedGhost` siblings |
| `sidequest/game/seed_deck.py` | new | `SeedDeck` draw-without-replacement engine, seeded by `session_id` |
| `sidequest/game/session.py` | existing (extend) | `GameSnapshot` at line 515 gains `active_seeds` + `seed_ghosts` fields |
| `sidequest/game/persistence.py` | existing | `snapshot_json` column round-trips deck/seed/ghost state — no migration |
| genre pack YAML | new content (22-2) | per-pack seed deck for `tea_and_murder` |

**Lifecycle:** draw (without replacement, reproducible per session_id) → active (injected
as VALLEY context) → expire (lifespan_turns elapsed) → ghost (record-only retention) →
cross-session callback. Ghost is immutable in this epic — resolution mechanics are
explicitly out of scope until later stories.

## Cross-Epic Dependencies

**Depends on:**
- ADR-018 Trope Engine (live) — `TropeDefinition` is the sibling pattern `SeedTrope` parallels
- ADR-009 VALLEY prompt zone (live) — 22-3's injection target
- ADR-023 Session DB (live) — persistence substrate for deck/seed/ghost state

**Depended on by:**
- Epic 24 (Procedural World-Grounding) — Phase-1 dogfood on `tea_and_murder` is coordinated with Epic 24's grounding playtest; both inject structured variety into narrator context
