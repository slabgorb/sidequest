---
id: 137
title: "Quest & Stakes Substrate — Create/Anchor Lane, First-Class active_stakes Source, and One-Mechanism Consolidation"
status: proposed
date: 2026-06-02
deciders: ["Keith Avery", "Agent Smith (Dev)"]
supersedes: []
superseded-by: null
related: [11, 24, 25, 102, 128, 130]
tags: [game-systems, agent-system]
implementation-status: partial
implementation-pointer: "sidequest-server/sidequest/game/quest_seed.py (story 77-1 seed-at-creation live, quest.seeded_at_creation OTEL); 77-2..77-7 deferred"
---

# ADR-137: Quest & Stakes Substrate — Create/Anchor Lane, First-Class active_stakes Source, and One-Mechanism Consolidation

> **Design story (77-1).** Deliverable is this ADR plus the implementation-story
> breakdown in §Implementation Stories — **no production code lands in 77-1**. The
> engine work is scoped into stories 77-2…77-5 (server), 77-6 (UI), and the
> active_seeds carve-out 77-7 (content).

## Context

The wry_whimsy/oz playtest (2026-06-02) ran 13 turns against a world whose entire
premise is a campaign spine — *"the traveler arrives by accident and wants only to
go home."* The objective was captured as KnownFacts/footnotes, yet the snapshot at
turn 13 showed:

```
quest_log: {}
quest_anchors: []
active_stakes: ""
active_seeds: []
```

The player had **no quest/objective surface**, and the engine had **no stakes** to
drive pacing/escalation against (ADR-024 dual-track tension, ADR-025 pacing
detection). The session ran on pure narrator improvisation — exactly the "convincing
narration with zero mechanical backing" failure the OTEL Observability Principle
(CLAUDE.md) exists to catch. For a forever-GM-turned-player like Keith, a campaign
spine silently vanishing from state is a tell that no human DM would ever produce.

This is a **mechanical-scaffold** failure (SOUL §purpose), not a narration-quality
one. The fields exist; nothing fills them.

### Code-grounded root cause (verified, not assumed)

Four fields, four distinct causes. All claims below were verified against
`sidequest-server` at HEAD on 2026-06-02:

| Field | State | Evidence |
|-------|-------|----------|
| `quest_anchors` | **Structurally dead read-only field.** Defined on the snapshot (`game/session.py`), read into narrator context (`agents/orchestrator.py`), shipped to client (`server/session_helpers.py`), and **consumed by the orbital course planner** (`orbital/course.py,157` — ADR-130). But it is **not a `WorldStatePatch` field** (absent from `game/session.py`) and has **zero write paths** (grep for assignment/append/`setattr` returns nothing). A live reader, a live *consumer*, no writer. | `grep "quest_anchors"` — all reads, no writes |
| `quest_log` | **Writable, but no create *affordance*.** `WorldStatePatch.quest_log` replaces the whole dict (`session.py`) and `quest_updates` merges (`session.py`). The live narrator lane (`narration_apply.py`) does `snapshot.quest_log[quest_id] = status` — a status-string keyed by id. The narrator's `quest_updates` schema is framed as **status updates to existing quests**; nothing in the prompt/tool tells it to **mint** a structured quest (id + title + objective). Mechanical write capability ≠ a first-class create lane. The trope handshake (`narration_apply.py`) writes `quest_log["trope_{id}"]` but needs a *resolved* trope (`total_beats_fired:0` → never fired in a prose-only pack). | `narration_apply.py`, `:5805` |
| `active_stakes` | **Two writers, both off the normal-play path.** (1) The **deprecated** `apply_world_patch` escape hatch (`agents/tools/apply_world_patch.py` → `WorldStatePatch(active_stakes=...)`) — the narrator is explicitly told NOT to use it; its deprecation criterion is *zero uses*. (2) The trope-resolution handshake (`narration_apply.py`), which didn't fire. **No first-class "set the current stakes" affordance in ordinary play.** | `apply_world_patch.py`, `narration_apply.py` |
| `active_seeds` | **Content gap, not engine.** wry_whimsy authors no `seed_tropes`; only tea_and_murder does across live packs. The ADR-128 seed deck is simply unauthored. **Carved out — see §active_seeds carve-out.** | pack content audit |

### The core gap, stated once

There is a lane to **UPDATE** a quest but no first-class lane to **CREATE/anchor**
one, and stakes only flow from a trope handshake that never fires in prose-only
packs (or from a deprecated escape hatch the narrator must not touch). The campaign
spine has nowhere to be written at session start and no maintained affordance to be
written during play.

## Decision

Adopt **Option C (both server fixes) as the engine core, with Option D's UI panel
defined as a fast-follow implementation story** — not bundled into the engine ADR
scope, but committed and enumerated so the feature is wired end-to-end rather than
shipped half-visible.

Concretely:

1. **Seed-at-creation (Option A).** At session init, derive **one quest_anchor + a
   `quest_log` entry + `active_stakes`** from the PC's drive/calling. Every session
   starts with a non-empty mechanical spine from turn 1. This is the smallest,
   highest-certainty fix and it directly closes the "empty at turn 0" failure.

2. **Typed narrator tools (Option B, ADR-102).** Add first-class structured-output
   tools — **`record_quest`** (mint/evolve a quest: id, title, objective, status,
   optional anchor) and **`set_stakes`** (set/append the current stakes) — so the
   narrator originates and evolves quests *in play*. These tools become the **single
   mechanism** for quest/stakes writes (see §One-mechanism consolidation).

3. **Promote `quest_anchors` to first-class (AC-2).** Add `quest_anchors` to
   `WorldStatePatch` with a real write path, fed by both the creation seed (1) and
   `record_quest` (2). **Promote, do not retire** — `orbital/course.py` (ADR-130)
   already consumes anchors as beat/location ids for Hohmann course plotting, so the
   anchor is the bridge that makes "go home" actually *plot a course*. Retiring it
   would rip out a live consumer.

### Why C-core + D-as-fast-follow (rationale)

- **A alone** guarantees a spine at turn 0 but quests never evolve.
- **B alone** lets quests evolve and spawn in play, but a session can run several
  turns before the narrator decides to mint one — the turn-0 hole stays open.
- **C = A + B** closes the gap at both ends: seeded from the PC's drive at creation,
  evolved (and newly spawned) via the typed tool. C is also what makes the
  one-mechanism consolidation possible — the tool gives us something to migrate the
  two discouraged/dead lanes *onto*.
- **D (UI panel)** is required for the player to *see* the spine — Keith-as-player's
  campaign objective, and the mechanical legibility Sebastien/Jade expect in
  player-facing surfaces (CLAUDE.md). But it is a separable concern: the `quests`
  field already exists in `payloads.ts`/`GameStateProvider` and renders nowhere
  today. Splitting it into its own story (77-6) lets the server fix land and be
  **OTEL-verified independently** (the GM panel is the lie-detector), then the panel
  consumes a proven projection. This honors "Verify Wiring, Not Just Existence" —
  the server story is not "done" until 77-6 is enumerated and committed.

## One-mechanism consolidation (AC-3)

Per one-mechanism-per-problem, we do **not** leave the dead legacy lane, the
deprecated escape hatch, and the new tool all live. In the same epic:

- **Retire the `quest_updates` extraction lane.** `record_quest` supersedes it;
  status-only updates become an update-mode of `record_quest`. Remove
  `quest_updates` from the orchestrator extraction (`orchestrator.py,1258,3219,3549`)
  and the apply path (`narration_apply.py`, `session.py`) once migrated.
- **Strip quest/stakes paths from `apply_world_patch`.** Remove `/quest_log`,
  `/quest_updates`, and `/active_stakes` from the escape-hatch tool
  (`apply_world_patch.py,195`). Other paths (location, current_region) are out
  of scope and remain. The escape hatch keeps its non-quest paths; quest/stakes go
  exclusively through the typed tools.

End state: **one create/evolve lane** (`record_quest`/`set_stakes` + the creation
seed), zero structurally-dead fields, zero discouraged duplicate writers.

## OTEL spans (AC-4)

The GM panel must be able to prove the substrate is engaged, not improvised:

| Span | Emitted when | Attributes |
|------|--------------|------------|
| `quest.seeded_at_creation` | session init seeds the spine | `quest_id`, `anchor_id`, `source_drive`, `has_stakes` |
| `quest.created` | `record_quest` mints a new quest | `quest_id`, `title`, `source` (creation\|narrator), `anchor_count` |
| `quest.updated` | `record_quest` changes status | `quest_id`, `old_status`, `new_status` (replaces `SPAN_QUEST_UPDATE`) |
| `quest.anchor.added` | an anchor is written | `anchor_id`, `quest_id`, `resolved_to_beat` (bool) |
| `stakes.set` | `set_stakes` writes/appends | `length`, `source`, `is_fresh` (mirrors the existing `active_stakes_appended` flag) |

## Implementation Stories

Spawn under epic 77 (`pf sprint story add`, never hand-edit YAML):

| Story | Repo | Pts | Scope |
|-------|------|-----|-------|
| **77-2 — Seed-at-creation** | server | 3 | At session init, derive 1 `quest_anchor` + `quest_log` entry + `active_stakes` from the PC drive/calling. +`quest.seeded_at_creation`. (Option A) |
| **77-3 — Typed quest/stakes tools** | server | 5 | `record_quest` + `set_stakes` structured-output tools (ADR-102). Create/evolve quests, set stakes in play. +`quest.created`/`quest.updated`/`stakes.set`. (Option B) |
| **77-4 — Promote quest_anchors** | server | 3 | Add `quest_anchors` to `WorldStatePatch` + write path; wire anchors into `orbital/course.py` (ADR-130). +`quest.anchor.added`. (AC-2) |
| **77-5 — One-mechanism cleanup** | server | 2 | Retire `quest_updates` extraction lane; strip `/quest_log`+`/active_stakes` from `apply_world_patch`; migrate to typed tools. (AC-3) |
| **77-6 — Quest/objective panel** | ui | 5 | Render `quest_log` + `quest_anchors` + `active_stakes` from the existing `quests` payload field. Player-facing mechanical legibility. (Option D increment) |
| **77-7 — wry_whimsy seed_tropes deck** | content | 2 | Author the ADR-128 seed deck for wry_whimsy (active_seeds carve-out). **Delegate to a `gm` agent.** (AC-6) |

Suggested order: 77-2 → 77-3 → 77-4 → 77-5 (engine spine, then consolidation), with
77-6 as a fast-follow once the projection is OTEL-verified, and 77-7 in parallel
(content, independent).

## active_seeds carve-out (AC-6)

`active_seeds` is **out of scope for the engine ADR.** It is empty in wry_whimsy
because the pack authors no `seed_tropes` (ADR-128), not because any engine lane is
missing — tea_and_murder populates the same field through the existing seed-deck
mechanism. The fix is **content authoring**, tracked as story 77-7 and delegated to
a `gm` agent per the project's content-delegation practice. This ADR references it
for completeness; it is not solved here.

## Consequences

**Positive**
- Every session starts with a mechanical campaign spine; pacing/escalation
  (ADR-024/025) finally has stakes to read.
- `quest_anchors` becomes live, feeding the orbital course planner (ADR-130) so
  spine objectives plot real courses.
- One create/evolve mechanism; no dead fields, no discouraged duplicate writers.
- GM-panel-verifiable at every write (OTEL spans), per the Observability Principle.
- Player sees the spine (77-6) — Keith-as-player's objective, Sebastien/Jade's crunch.

**Negative / risks**
- `record_quest`/`set_stakes` add tool-call surface to every narrator turn; bound
  the schema tightly (ADR-102) and lean on prompt caching to keep cost proportional
  to drama (SOUL §Cost Scales with Drama) — a quiet town walk shouldn't mint quests.
- Seed-at-creation depends on the PC drive/calling being populated at chargen; if a
  genre lacks a drive field, the seed must degrade **loudly** (emit a span noting the
  empty seed), never silently skip (No Silent Fallbacks).
- Migration (77-5) must land in lockstep with 77-3 or saves could carry quests
  written by a retired lane; gate 77-5 on 77-3.

## Alternatives considered

- **Option A only** — rejected: leaves quests static, no in-play evolution.
- **Option B only** — rejected: turn-0 spine hole remains; a 13-turn session could
  still reach turn 5 before a quest exists.
- **Option D bundled into one story** — rejected: couples server + UI into a single
  large story, defeating independent OTEL verification of the server lane and
  violating the "verify the projection before consuming it" sequencing.
- **Retire `quest_anchors` entirely** — rejected: `orbital/course.py` (ADR-130) is a
  live consumer; retiring the field means deleting a working course-planning input.
