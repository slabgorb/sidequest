# NPC Relationship Panel — Design Spec

- **Date:** 2026-06-01
- **Author:** Architect (Neo)
- **Status:** Approved (brainstorming) — ready for implementation plan
- **Origin:** Playtest 2026-06-01 (the_real_mccoy), ping-pong `[UX/GAP] Relationship state tracked server-side but invisible to the player; OCEAN/belief unpopulated on the ensemble`
- **Scope:** Single feature, phased implementation. Spans `sidequest-server` (engine) + `sidequest-ui` (panel). Content half (authored OCEAN) already landed in `sidequest-content #318`.

## Problem

NPC relationship state is tracked server-side but the player cannot see it. During the_real_mccoy playtest the disposition dial moved correctly (Dr. McCoy 19, Tabitha 24, Teague 10) yet **none of it reached the player**:

- The `Npc.disposition` integer (−100..+100), its trend, `last_seen_turn`, `last_seen_location`, and `non_transactional_interactions` are **server-only** — never serialized to player clients.
- The one `disposition` string the client receives (`ScrapbookEntryNpcRef.disposition`) is a **narrator prose tag** sourced from `npcs_present[].role`, not the mechanical `Disposition` object.
- Disposition **deltas** exist only as transient OTEL spans (`SPAN_DISPOSITION_SHIFT`) — there is no persisted history.
- `Npc.ocean` is `dict | None`, **P5-deferred and never runtime-populated** (authored OCEAN exists on `AuthoredNpc` content from #318 but is not materialized onto runtime NPCs).
- `Npc.belief_state` is live but only scenario-seeded; it contains spoiler-bearing `Fact`/`Suspicion` entries.

For a session whose point was *exploring relationships* (Keith's focus), the relationship state is invisible. Mechanics-first players (Sebastien/Jade) cannot see the relationship math; narrative players get no at-a-glance "where do I stand with these people."

## Goals

1. A player-facing **Relationships panel** showing, for each NPC the party has engaged: standing (band + on-demand number), trend, where/when last seen, the **history of why standing moved**, a **personality read**, and **what the NPC has told the party**.
2. Reuse existing infrastructure — disposition (ADR-020), OCEAN (ADR-042), belief_state (ADR-053), reactive per-domain messaging (ADR-026/027), the perception firewall (ADR-104/105), the dockview panel + `useGenreTheme` pattern (ADR-079).
3. Never leak mystery solutions (ADR-053 scenarios).

## Non-Goals (YAGNI)

- **Per-PC disposition.** `Disposition` is a single scalar on the `Npc` (NPC stance toward the party, global). Per-PC standing is a much larger engine change and is explicitly out of scope. The panel shows global standing.
- **Editing relationships from the panel.** Read-only surface.
- **NPCs in `npc_pool`.** The panel shows only the *promoted, stateful* roster (`snapshot.npcs`) — the people the party has actually engaged (ADR-014 coal→diamond). Transient pool mentions do not appear.
- **Changing the engine `Attitude` enum.** The 5-level display band is a *presentation* label computed at projection; the engine's 3-level `Attitude` (FRIENDLY/NEUTRAL/HOSTILE) is unchanged.

## Decisions (locked during brainstorming, 2026-06-01)

| Decision | Choice | Rationale |
|---|---|---|
| **Fidelity** | **Hybrid** — narrative band by default, raw integer + recent deltas on expand | Honors ADR-040 ("no raw stats") as the resting state; opts mechanics-first players into the math via progressive disclosure. |
| **Beat-log** | **Include** — persist a per-NPC disposition-event log | Makes it a relationship *story* (ADR-014), not a reputation bar. Captures the delta+reason the engine already computes. |
| **OCEAN + belief** | **Include both now** | Matches the relationship-driven play Keith wants and Sebastien/Jade's mechanics-first instincts. |
| **Belief firewall** | **Claims-to-party only** | Private `Fact`/`Suspicion` entries are the whodunit; only `Claim` entries (things the NPC said in-fiction) may be shown. Spoiler-safe by construction. |
| **Projection message** | **New dedicated `RELATIONSHIPS` reactive message** | Follows the existing per-domain message+panel pattern (KNOWLEDGE/LOCATION/MAP); honors Cost-Scales-with-Drama; isolates the firewall in one stage. |

## Architecture

### Message architecture (the core fork)

A new dedicated reactive `RELATIONSHIPS` message, **not** an extension of `PARTY_STATUS` or `SCRAPBOOK_ENTRY`.

- **Rejected — extend `PARTY_STATUS`:** that message is the *player's party*; relationships are a different domain with a different emission cadence and a heavy spoiler-firewall requirement that does not belong in party projection.
- **Rejected — extend `SCRAPBOOK_ENTRY`:** transient per-turn scene metadata (ImageBus/gallery), wrong home for durable relationship + beat history.
- **Chosen — dedicated message:** this is *pattern reuse*, not invention — KNOWLEDGE, LOCATION, MAP each already have their own reactive message + dockview panel. Emit reactively (ADR-027) when the relationship set changes (disposition shift, new NPC promoted into `snapshot.npcs`, a claim recorded), not every turn (Cost-Scales-with-Drama).

### Engine data seams (three, all reuse-first)

**1. Disposition beat-log (persistence of already-computed values).**

```python
class DispositionBeat(BaseModel):   # new, in game/disposition.py or session.py
    turn: int
    delta: int
    reason: str          # narrator-supplied via update_npc_disposition, or the
                         # interest-tick label from develop_npc_on_engagement
    location: str | None

# on Npc:
    disposition_log: list[DispositionBeat] = Field(default_factory=list)  # ring buffer, cap ~10
```

A single seam — `Npc.record_disposition_beat(turn, delta, reason, location)` — appends and trims to cap. It is called at the **existing** disposition-shift sites that already emit `SPAN_DISPOSITION_SHIFT`:
- `develop_npc_on_engagement` (interest tick → small drift; `narration_apply.py`)
- the `update_npc_disposition` tool (narrator-declared shift; already carries `reason`/`morale_event`)
- any morale-event path that mutates disposition

This persists the delta + reason the engine already computes — **no new mechanical computation**. Add an OTEL span (`relationship.beat_recorded`) confirming the append so the GM panel verifies the log is written, not improvised (CLAUDE.md OTEL principle). All disposition-mutation sites must call the seam ("if it needs 5 connections, make 5" — the plan enumerates them).

**Trend** is derived (not stored): sign of the summed deltas in the most recent scene-window (e.g. last turn, or last K beats).

**2. OCEAN seeding (wire the authored half to runtime).**

Extend the **authored-NPC materializer** (the seam `worlds/<world>/npcs.yaml` flows through to `snapshot.npcs`, the path #318 populated) to copy `AuthoredNpc.ocean` → `Npc.ocean`, normalizing the authored **0..1** scale to the runtime `OceanProfile` **0..10** scale. Mirror the seeding shape that 72-9 already uses for narrator-invented NPCs (single seeding helper if one exists; otherwise factor one). NPCs with no authored OCEAN keep `ocean=None` and the panel shows no personality read for them (graceful, no fabricated personality — No Silent Fallbacks: absence is shown as absence).

**3. Belief filter (claims-only) — a firewall rule, not a data change.**

At projection, `belief_state.beliefs` is filtered to `Claim` entries only (+ a coarse `credibility_hint` derived from `credibility_scores`). **All `Fact` and `Suspicion` entries are dropped.** This is enforced in the projection stage (below) and guarded by a test asserting a planted `Fact`/`Suspicion` never crosses the firewall.

### Projection + firewall stage

A new `RelationshipProjectionStage`, composing with the existing ADR-104/105 firewall chain, builds one entry per NPC in `snapshot.npcs`:

```
RelationshipEntry {
  name: str
  portrait_url: str | None
  band: str               # 5-level DISPLAY label: Hostile | Cool | Neutral | Warm | Devoted
                          #   computed at projection from disposition.value thresholds.
                          #   Distinct from the engine 3-level Attitude enum (unchanged).
  disposition: int        # raw value — the "reveal" detail
  trend: "up" | "flat" | "down"
  last_seen_turn: int
  last_seen_location: str | None
  beats: list[DispositionBeat]      # from disposition_log, capped
  personality_read: str | None      # narrative OCEAN descriptors (default view), or None
  ocean: OceanProfile | None        # numeric 0..10 — the "reveal" detail
  claims: list[{ text: str, credibility_hint: str }]   # claims-to-party only
}
```

- **Disposition + OCEAN are global** (single scalar / single profile; no per-PC divergence) — the firewall does not need to fork these per PC.
- The firewall's load-bearing job here is the **claims-only belief filter** and ensuring nothing spoiler-bearing leaks.
- `band` thresholds and the `personality_read` descriptor mapping are defined in the projection stage (presentation logic), keeping the engine `Attitude` enum and `OceanProfile` untouched.
- Emitted reactively when an NPC's `disposition` / `disposition_log` / claims change, or a new NPC enters `snapshot.npcs`. Sorted by `last_seen_turn` desc at the client.

### UI panel

A new `relationships` dockview widget via the documented 5-step registration:

1. add `"relationships"` to the `WidgetId` union (`widgetRegistry.ts`)
2. define its `WIDGET_REGISTRY` entry (min/default dims; `dataGated: true` — only available once ≥1 NPC is engaged)
3. add to `rightGroupOrder` (`GameBoard.tsx`) — position after `character`
4. add to `availableWidgets` (gated on relationship data present)
5. implement the render case in `renderWidgetContent`

Consumed by a thin `useRelationships` slice off the state mirror (matching `useStateMirror` / the KNOWLEDGE/LOCATION pattern). TypeScript payload mirrors `RelationshipEntry`.

**Hybrid display (the decision):**
- **Roster row (default):** portrait + name + **band** + trend arrow. Narrative, ADR-040-compliant.
- **Expand a row:** raw disposition int + recent deltas; last-seen turn/location; **beat history** ("warmed by your candor +3"); **personality read** (with a further expand to the numeric OCEAN profile for mechanics-first players); **claims-to-party** with credibility hints.

Theming via the FOLIO semantic-palette pattern + `useGenreTheme` (ADR-079) — no hardcoded colors; EB Garamond labels/body, display font for names only.

## Phasing (for the implementation plan)

Cohesive single feature, but the plan should sequence so each phase is independently verifiable:

- **Phase A — Visibility + beat-log:** `DispositionBeat` model + `record_disposition_beat` seam wired at all shift sites + OTEL span; `RELATIONSHIPS` message + `RelationshipProjectionStage` (band/int/trend/last-seen/beats; belief + OCEAN fields empty for now); UI panel skeleton (roster rows + expand showing disposition/beats). **Delivers the headline gap on its own.**
- **Phase B — OCEAN:** materializer seeding (`AuthoredNpc.ocean` → `Npc.ocean`, scale-normalized) + `personality_read` + numeric reveal in the panel.
- **Phase C — Claims:** claims-only belief filter in the projection stage + the spoiler-guard test + claims display in the expand view.

## Testing & wiring

**Engine:**
- Unit: `disposition_log` ring-buffer cap/trim; trend derivation; band-threshold mapping; OCEAN scale normalization (0..1 → 0..10).
- **Spoiler guard:** plant a `Fact` and a `Suspicion` in an NPC's `belief_state`, run the projection stage, assert neither crosses — only `Claim` entries appear. This is the load-bearing firewall test.
- **Wiring (behavior, not source-grep):** drive a real disposition shift through dispatch and assert (a) the beat is appended (`relationship.beat_recorded` OTEL span fires) and (b) a `RELATIONSHIPS` message is emitted carrying the new beat. OTEL-span assertion per the "No Source-Text Wiring Tests" rule.
- OCEAN seeding: materialize the_real_mccoy ensemble (#318) and assert `Npc.ocean` is populated on the runtime roster.

**UI:**
- Panel render test (roster + expand).
- **Mandatory integration test:** the `relationships` panel is mounted in GameBoard and renders a server `RELATIONSHIPS` payload end-to-end (server payload → state mirror → panel).

## ADR

Author a new ADR — **ADR-136: Player-Facing Relationship Surface — Reactive RELATIONSHIPS Projection, Disposition Beat-Log, and the Claims-Only Belief Firewall** — recording: the hybrid fidelity decision (reconciling ADR-040 with the mechanics-first directive), the dedicated-message choice, the beat-log persistence of OTEL-only deltas, the OCEAN materialization wiring, and the claims-only belief firewall as the spoiler boundary. Cross-reference ADR-020/040/042/053/104/105/026/027/079/014.

## Affected files (orientation, not exhaustive — plan refines)

**Server:** `game/disposition.py` (DispositionBeat, record seam), `game/session.py` (`Npc.disposition_log`), `game/belief_state.py` (claims filter helper), `server/narration_apply.py` + `agents/tools/update_npc_disposition.py` (call the beat seam), the authored-NPC materializer (OCEAN seeding), `game/projection/` (RelationshipProjectionStage), `protocol/messages.py` (`RELATIONSHIPS` + `RelationshipEntry`), `server/emitters.py` (reactive emit), `telemetry/spans/` (relationship spans).

**UI:** `components/GameBoard/widgetRegistry.ts`, `components/GameBoard/GameBoard.tsx`, a new `components/GameBoard/widgets/RelationshipsPanel.tsx`, `hooks/useRelationships.ts` (or extend state mirror), `types/payloads.ts` (`RelationshipEntryPayload`).
