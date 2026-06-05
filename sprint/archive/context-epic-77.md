# Epic 77: Quest & Stakes Substrate

## Overview

Give every session a **mechanical campaign spine** — a quest, an anchor, and
current stakes — that exists from turn 1 and is maintained in play, rather than
living only as narrator improvisation. The epic implements ADR-137 (Option C
engine core + Option D UI panel as a committed fast-follow): seed a quest spine
at character creation, add typed `record_quest`/`set_stakes` narrator tools as
the single create/evolve mechanism, promote `quest_anchors` to a first-class
writable field feeding the orbital course planner, retire the redundant legacy
write lanes, and render the spine in a player-facing panel.

**Priority:** P2
**Repo:** server, ui, content
**Stories:** 6 (21 points) — design story (ADR-137) DONE and archived; 77-1…77-6 are the implementation lane (all backlog)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-137 — Quest & Stakes Substrate** (`docs/adr/137-quest-stakes-substrate.md`) | §Decision (Option C-core + D-fast-follow), §One-mechanism consolidation (AC-3), §OTEL spans (AC-4), §Implementation Stories, §active_seeds carve-out (AC-6) — the authoritative design |
| **ADR-130 — Orbital Story-Time Clock and Course Model** (`docs/adr/130-*.md`) | The live consumer of `quest_anchors` — `orbital/course.py:125,157` plots Hohmann courses from anchor beat/location ids. Promote-don't-retire the field. |
| **ADR-102 — Tool-Use Protocol for Structured Output** (`docs/adr/102-*.md`) | Schema discipline for the new `record_quest`/`set_stakes` typed tools |
| **ADR-024 / ADR-025 — Dual-Track Tension / Pacing Detection** | The downstream readers that need `active_stakes` populated to drive escalation/pacing |
| **ADR-128 — Trope Temporal Governor / Seed-Trope Deck** | Governs `seed_tropes`/`active_seeds`; backs the 77-6 content carve-out |
| **Snapshot + patch path** (`sidequest-server/sidequest/game/session.py`) | `quest_anchors` field decl (l.735), `WorldStatePatch` (l.420), `quest_log`/`quest_updates` apply (l.1275/1278) — the seam being reworked |
| **Narrator apply + extraction** (`sidequest-server/sidequest/agents/narration_apply.py`, `orchestrator.py`) | Live `quest_log` write (`narration_apply.py:2872`), trope handshake (`:5805,5812`), `quest_updates` extraction (`orchestrator.py:472,1258,3219,3549`) being consolidated |

## Background

The wry_whimsy/oz playtest (2026-06-02) ran **13 turns** against a world whose
entire premise *is* a campaign spine — *"the traveler arrives by accident and
wants only to go home."* Yet the turn-13 snapshot showed `quest_log: {}`,
`quest_anchors: []`, `active_stakes: ""`, `active_seeds: []`. The player had no
objective surface and the engine had no stakes to drive pacing/escalation
against. The session ran on pure narrator improvisation — the exact "convincing
narration with zero mechanical backing" failure the OTEL Observability Principle
exists to catch. This is a **mechanical-scaffold** failure (the fields exist;
nothing fills them), not a narration-quality one.

ADR-137's code-grounded root cause (verified against `sidequest-server` HEAD,
not assumed) found **four fields, four distinct causes**:

- **`quest_anchors`** — a structurally dead read-only field. It is read into
  narrator context, shipped to the client, and **consumed by the orbital course
  planner** (a live consumer, ADR-130), but it is *not* a `WorldStatePatch`
  field and has **zero write paths**. A live reader and live consumer, no writer.
- **`quest_log`** — writable, but no *create affordance*. The narrator's
  `quest_updates` lane is framed as status updates to existing quests; nothing
  tells it to **mint** a structured quest (id + title + objective). The trope
  handshake that does write a structured entry needs a *resolved* trope, which
  never fires in a prose-only pack.
- **`active_stakes`** — two writers, both off the normal-play path: the
  **deprecated** `apply_world_patch` escape hatch (narrator told not to use it)
  and the trope handshake (didn't fire). No first-class "set the stakes"
  affordance in ordinary play.
- **`active_seeds`** — a **content gap, not engine**: wry_whimsy authors no
  `seed_tropes`; tea_and_murder populates the identical field through the
  existing ADR-128 deck mechanism. Carved out to story 77-6.

**The core gap, stated once:** there is a lane to UPDATE a quest but no
first-class lane to CREATE/anchor one, and stakes only flow from a trope
handshake that never fires in prose packs (or a deprecated escape hatch the
narrator must not touch). The campaign spine has nowhere to be written at
session start and no maintained affordance during play.

> **Numbering note for downstream agents.** ADR-137 §Implementation Stories was
> written when the design story was 77-1, so its internal table numbers the
> implementation stories 77-2…77-7. After the design story completed and was
> archived, the implementation stories were re-promoted as **77-1…77-6**. The
> mapping is: ADR 77-2→sprint **77-1** (seed), 77-3→**77-2** (typed tools),
> 77-4→**77-3** (promote anchors), 77-5→**77-4** (cleanup), 77-6→**77-5** (UI
> panel), 77-7→**77-6** (content seed deck). Use the **sprint** numbers below.

## Technical Architecture

The fix closes the gap at **both ends** of a session — seeded at creation,
evolved in play — and consolidates three competing write mechanisms into one.

**Write-path consolidation (the heart of the epic):**

```
BEFORE (3 mechanisms, 2 broken/discouraged):
  quest_updates extraction lane ──► narration_apply (status-only, no create)
  apply_world_patch escape hatch ──► active_stakes/quest_log (DEPRECATED, "don't use")
  trope handshake ──────────────────► quest_log["trope_{id}"] (needs resolved trope, never fires)
  quest_anchors ─────────────────► [no writer at all]

AFTER (1 create/evolve mechanism):
  creation seed ─────┐
                     ├──► quest_log + quest_anchors + active_stakes
  record_quest ──────┤    (quest_anchors now first-class WorldStatePatch field)
  set_stakes ────────┘         │
                               └──► orbital/course.py (ADR-130 consumer — UNCHANGED, now fed)
```

**Key files (new and existing):**

| File | Change |
|------|--------|
| `sidequest-server/.../game/session.py` | Add `quest_anchors` to `WorldStatePatch` (l.420) + real apply path (77-3); seed-at-creation hook (77-1) |
| `sidequest-server/.../agents/tools/` | New typed tools `record_quest` + `set_stakes` (ADR-102) (77-2) |
| `sidequest-server/.../agents/narration_apply.py` | Migrate `quest_log` writes onto `record_quest`; remove `quest_updates` merge after migration (77-4) |
| `sidequest-server/.../agents/orchestrator.py` | Remove `quest_updates` extraction (l.472,1258,3219,3549) (77-4) |
| `sidequest-server/.../agents/tools/apply_world_patch.py` | Strip `/quest_log`, `/quest_updates`, `/active_stakes` paths (keep location/current_region) (77-4) |
| `sidequest-server/.../orbital/course.py` | No change — existing consumer (l.125,157); validates the promoted anchor end-to-end |
| `sidequest-ui/.../` (`payloads.ts`, panel) | Render the already-shipped `quests` payload field — quest_log + anchors + stakes (77-5) |
| `sidequest-content/genre_packs/wry_whimsy/` | Author `seed_tropes` deck (ADR-128) for the `active_seeds` carve-out (77-6, delegate to `gm` agent) |

**OTEL spans (AC-4) — the GM-panel lie detector for this substrate:**
`quest.seeded_at_creation`, `quest.created`, `quest.updated` (replaces
`SPAN_QUEST_UPDATE`), `quest.anchor.added`, `stakes.set`. Per the Observability
Principle, the server lane (77-1…77-4) is not "done" until these spans prove the
substrate is engaged rather than improvised — and the UI panel (77-5) consumes a
projection only after it is OTEL-verified independently.

**Implementation sequencing & guardrails:**
- Order: **77-1 → 77-2 → 77-3 → 77-4** (engine spine then consolidation), with
  **77-5** as a fast-follow once the projection is OTEL-verified, and **77-6** in
  parallel (content, independent).
- **77-4 must land in lockstep with 77-2** (gate cleanup on the typed tools) or
  saves could carry quests written by a retired lane.
- Seed-at-creation depends on the PC drive/calling being populated at chargen; if
  a genre lacks a drive field, the seed must degrade **loudly** (emit a span
  noting the empty seed), never silently skip — **No Silent Fallbacks**.
- Bound the new tool schemas tightly and lean on prompt caching — a quiet town
  walk shouldn't mint a quest (SOUL §Cost Scales with Drama).

## Cross-Epic Dependencies

**Depends on:**
- **ADR-130 / orbital course model** — `quest_anchors` must remain the
  beat/location-id bridge the course planner consumes; promote, don't retire.
- **ADR-102 tool-use protocol** — the structured-output contract for
  `record_quest`/`set_stakes`.
- **ADR-128 seed-trope deck** — backs the 77-6 `active_seeds` content carve-out.
- **Chargen drive/calling** — the seed source; must exist for the genre being
  played or the seed degrades loudly.

**Depended on by:**
- **ADR-024 dual-track tension / ADR-025 pacing detection** — these readers
  finally get a populated `active_stakes` to escalate/pace against.
- **Future wry_whimsy playtests** — the political spine (epic 59/Plan 2b) and the
  quest spine together replace narrator improvisation with mechanical backing;
  this epic closes the "empty spine at turn 0" half.
