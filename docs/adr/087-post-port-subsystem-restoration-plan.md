---
id: 87
title: "Post-Port Subsystem Restoration Plan"
status: accepted
date: 2026-04-24
deciders: ["Keith Avery (Bossmang)", "Leonard of Quirm (Architect, design mode)"]
supersedes: []
superseded-by: null
related: [17, 18, 20, 41, 42, 43, 44, 53, 55, 59, 67, 69, 71, 74, 75, 77, 78, 81, 82, 85, 86, 90, 92]
tags: [project-lifecycle]
implementation-status: live
implementation-pointer: null
---

# ADR-087: Post-Port Subsystem Restoration Plan

- **Input:** `docs/port-drift-feature-audit-2026-04-24.md` (audit that fed this ADR)
- **Governing:** ADR-082 (1:1 port mandate), ADR-085 (port-drift tracker hygiene)
- **Consolidation context:** ADR-067 (Unified Narrator Agent — explains why several agent helpers are intentionally gone)
- **Amended/acknowledged:** ADR-017, 018, 020, 041, 042, 044, 053, 059, 069 (their implementations are missing or partial in Python; this ADR schedules their restoration without reopening the original decisions). _ADR-043 was originally in this list; it has since been superseded by ADR-091 and dropped from the restoration scope._ _ADR-069 has since been superseded by ADR-092 (design pivot ratified 2026-05-02); the restoration work item remains scheduled here but is now scoped against ADR-092's HTTP-endpoint design rather than ADR-069's retired CLI design._
- **Explicit restraint:** ADR-071 (Proposed — not executed in Rust either; stay deferred). _ADR-074 (Dice Resolution Protocol) was originally on this list; it has since been promoted to accepted/live (audit 2026-05-02) — protocol payloads, server dispatch, and UI subsystem are all wired._ _ADR-075 (3D Dice Rendering) was also on this list; it has since been promoted to accepted/partial (audit 2026-05-02) — Three.js + R3F + Rapier stack is live, but the design pivoted from overlay to inline tray and from gesture-throw to click-and-auto-roll; per-genre `dice.yaml` theming remains unshipped._ _ADR-077 (Dogfight Subsystem) was also on this list; it has since been promoted to accepted/live (audit 2026-05-02) — content shipping in space_opera, `ResolutionMode.sealed_letter_lookup` dispatch branch live in `narration_apply.py:1176`._ _ADR-078 (Edge / Composure / Push-Currency) was also on this list; it has since been promoted to accepted/partial (audit 2026-05-02) — Edge primitive on CreatureCore is live with apply_edge_delta wired, BeatDef.edge_delta field exists, advancement-effect data shapes loaded; gaps remain at Epic 39 (per-class edge config wiring), missing `composure_break` OTEL span, and push-currency content stuck in workshopping rather than production._ _ADR-081 (Advancement Effect Variant Expansion v1) was also on this list; it has since been promoted to accepted/deferred (audit 2026-05-02) — upstream-blocked on ADR-078's Epic 39 wiring; bundles into the same P2 restoration item._

> This ADR is not a redesign. It is a **scheduling verdict** on every subsystem
> that did not land in the Python tree cleanly — both the ones we knew we were
> phasing out (§4 of the audit) and the ones that went quietly missing (§5).
> One verdict per subsystem, grouped by family, sorted into priority tiers.
> Post-verdict, each row becomes a story or epic handoff for PM/SM.

## Context

ADR-082 ported `sidequest-api` (Rust) to `sidequest-server` (Python) with a mandated 1:1 structural mapping and a Phase 1 vertical-slice focus on narration. The audit at `docs/port-drift-feature-audit-2026-04-24.md` found three non-parity categories:

- **§4 Intentional P1/P6 deferrals** — porter left markers, aligned with phased scope.
- **§5 Silent port-drift** — subsystems absent without markers, violating ADR-082 §Port Strategy.
- **§5.4 CLI/ADR-059 wiring drift** — accepted ADR-059 (server-side pregen) is dark; 4 of 5 CLI binaries are empty stubs.

The user (Bossmang) has asked for a single plan covering **all** non-parity items — not just the surprises. This ADR is that plan.

## Verdict Taxonomy

| Verdict | Meaning |
|---------|---------|
| **RESTORE** | Port the Rust implementation forward as-designed. Original ADR (if any) stands; this is implementation work. |
| **REWIRE** | Code exists in Python but is not connected. Implementation is wiring, not new logic. |
| **REDESIGN** | Concern is real; the Rust approach was wrong for Python or for the current product direction. A new ADR is owed before implementation. |
| **SUPERSEDE** | Concern is no longer load-bearing, or is handled elsewhere. Retire the concept. |
| **DEFER** | Intentional phased scope. Marker exists (or is being added here). No action owed now; will be claimed by a named future epic. |
| **VERIFY** | Audit could not determine current state from static inspection. Needs targeted check before assigning one of the above. |

## Priority Tiers

- **P0 — this sprint / next sprint.** Load-bearing for current product promise; accepted ADRs are currently dark.
- **P1 — within current epic window.** Fails the Keith-as-player or Alex-inclusive test, or is load-bearing for OTEL lie-detection.
- **P2 — design-ready, next-epic candidate.** Feature value is clear, no blocker, but not currently load-bearing.
- **P3 — flavor / nice-to-have.** Real value, low urgency.
- **Deferred** — explicit phased scope; no action until the owning epic lights up.

## Subsystem Verdicts

### A. Narrative engine subsystems

| Subsystem | Prior ADR | Verdict | Tier | Notes |
|-----------|-----------|---------|------|-------|
| Trope engine (`apply_trope_engagement`, driver selection) | ADR-018 Accepted | **RESTORE** | P1 | `TropeState` already ported; this is wiring the engine back onto the existing data structure. Narrative pacing depends on it. |
| NPC disposition (Attitude enum + transitions) | ADR-020 Accepted | **RESTORE** | P1 | Currently reduced to scalar `npc.disposition: int`. Scalar-only is below tabletop-DM baseline — fails the Keith-as-player test per CLAUDE.md. |
| Continuity validator (contradiction detection) | — | **RESTORE** | P1 | Load-bearing for OTEL lie-detection per CLAUDE.md (_"The GM panel is the lie detector"_). Without it, Claude's improvisations go unflagged. |
| Patch legality gate | — | **RESTORE** | P1 | State mutations currently apply without systematic authorization. Small module; enables auditable patch pipeline. |
| Subsystem coverage tracker (`CoverageGap` events) | — | **RESTORE** | P1 | Partial — `agents/subsystems/` has dispatch framework; `CoverageGap` watcher emission is absent. Required to prove subsystems are *actually* engaged, not stubbed by silence. |
| Gossip engine (NPC info propagation) | ADR-053 Accepted | **RESTORE** | P2 | Concept referenced in `session.py`/`scenario_state.py`/`belief_state.py` but no engine. Required for multi-NPC mystery scenarios to feel alive. |
| Accusation logic (`evaluate_accusation`) | ADR-053 Accepted | **RESTORE** | P2 | Logic proof check for mystery scenarios. Bundled with gossip under ADR-053 wiring. |
| Genie wish consequence engine | ADR-041 Accepted | **RESTORE** | P2 | `GenieWish` tracking in `session.py` has no engine behind it. SOUL.md "Rule of Cool" explicitly requires the monkey's paw mechanism — currently absent. |
| OCEAN shift proposals (trope-driven personality) | ADR-042 Accepted | **RESTORE** | P2 | Depends on trope engine. Model in `genre/models/ocean.py`, pipeline missing. |
| Chase engine (`chase_depth`, terrain, rig, phase) | ADR-017 Accepted | **RESTORE** | P2 | Zero implementation; protocol hint in `encounter.py` only. Narrative-weight feature — ADR-014/080 promise a dramatic chase. |
| Conlang morpheme glossary | ADR-043 Superseded | **SUPERSEDE** (already) | — | Superseded by ADR-091 (culture-corpus + Markov naming, retrospective of live system). The original RESTORE verdict was written before the Python tree was audited at the naming layer; production has the Markov + culture-corpus approach in `sidequest/genre/names/` (~604 LOC, every genre pack ships `corpus/` + `cultures.yaml`). No restoration needed; bringing morphemes back would mean demoting a working system. |
| Beat filter (conditional narration gating) | — | **RESTORE** | P3 | Small utility module; restoration is one-for-one. |
| Scene relevance validator | — | **REDESIGN** | P2 | Belongs inside the ADR-086 image-composition taxonomy, not as a free-floating Rust module. Fold into image pipeline design rather than port. |
| Theme rotator | — | **SUPERSEDE** | — | Unclear value from static inspection; tension tracker + narrative-weight traits (ADR-080) likely cover the same pacing surface. If a pacing gap surfaces later, design fresh. |

### B. Mechanical engine subsystems

| Subsystem | Prior ADR | Verdict | Tier | Notes |
|-----------|-----------|---------|------|-------|
| Pregen dispatch (server invokes namegen/encountergen/loadoutgen at turn-time) | ADR-059 Accepted | **RESTORE** | **P0** | Single biggest hot item. Accepted ADR is currently dark. Without this, NPC names/encounters/loadouts drift into Claude's improvisation — which is exactly what ADR-059 was written to prevent. |
| Confrontation engine / Combat Epic 28 port verification | ADR-033 Accepted | **VERIFIED** (Pillars 1 + 2 live; Pillar 3 partial) | P3 | Audit completed 2026-05-02. Pillars 1 (StructuredEncounter / ConfrontationDef / `apply_beat`) and 2 (ResourcePool + threshold→KnownFact via `mint_threshold_lore`) shipped intact through the port and are heavily wired across narrator, dispatch, and session paths. Remaining gap is Pillar 3's `mood_aliases` lookup table: declared on the Pydantic model (`genre/models/audio.py:120`) and in one content pack (`heavy_metal/audio.yaml`), but no consumer fires the alias chain. `mood_override` (the Pillar 3 step that actually moves narration) is live. Polish item, not port-casualty — drop from P0. |
| Speculative prerendering | ADR-044 Historical (re-labeled 2026-05-02) | **DO NOT RESTORE** | — | TTS is deprecated; this ADR's premise (use TTS playback window as free GPU render time) is moot. Image latency is now addressed by direct render-pipeline tuning, not speculation. If post-TTS speculative prerendering ever becomes interesting (predicting renders during narration-read gaps), write a fresh ADR — do not revive ADR-044. |
| Room graph navigation — per-transition mechanics + map wire message | ADR-055 Accepted (promoted from Proposed 2026-05-02) | **RESTORE** | P2 | Data layer + init runtime + 4 worlds' content shipping (`caverns_and_claudes/worlds/{dungeon_survivor,grimvault,horden,mawdeep}/rooms.yaml`). Three gaps: (1) `tick_on_room_transition` to fire trope `rate_per_turn` per transition in room_graph mode (Keeper-awareness escalation is currently dark); (2) `uses_remaining` decrement on transition for active light sources (torch-burn / extraction-pressure loop dark); (3) new wire message replacing the deleted MAP_UPDATE pipeline (UI carries dead consumer code at `App.tsx:781` — clean up in same pass). Spec drift in ADR-055's body (`size`, `RoomExit`, mode count) is documented; no action owed beyond the running models being source of truth. |
| Merchant / transactions | — | **DEFER** | — | No ADR, no current need. If economy becomes a feature, write an ADR first, then port. Add deferral marker to `game/__init__.py`. |
| Affinity progression | ADR-021, ADR-081 | **DEFER** | — | Porter's `P6-deferred` marker confirmed at `game/character.py:55-64`. Will land with the advancement epic. No action. |
| Advancement / XP pipeline | ADR-081 Proposed | **DEFER** | — | Partial `award_turn_xp` stub; marker aligned with ADR-081's Proposed status. |
| Dogfight subsystem | ADR-077 Accepted (promoted from Proposed 2026-05-02) | **VERIFIED live** | — | Sealed-letter cross-product resolution wired via `ResolutionMode.sealed_letter_lookup` dispatch branch at `sidequest-server/sidequest/server/narration_apply.py:1176`. Content shipping in `sidequest-content/genre_packs/space_opera/dogfight/`. SOUL gate exclusion in place. Test coverage at `tests/genre/test_dogfight_content_loading.py`. No restoration owed. |
| Edge/Composure push-currency rituals + Epic 39 wiring | ADR-078 Accepted (promoted from Proposed 2026-05-02) | **VERIFIED partial** | P2 | Edge primitive live: `EdgePool` on `CreatureCore`, `apply_edge_delta` called from `dispatch/yield_action.py:43` and `game/session.py:884, 888`; shared threshold helper at `game/thresholds.py`; `BeatDef.edge_delta` field at `genre/models/rules.py:105`; advancement-effect data shapes at `genre/models/advancement.py:89–106`. Gaps: (1) **Epic 39** — per-class edge config wiring; `world_materialization.py:325` placeholder explicit about it; (2) `composure_break` OTEL span (§4 of ADR) not emitted — engine-derived resolution at edge≤0 not wired; (3) push-currency content (`pact_working`/`commit_cost`) lives in `sidequest-content/genre_workshopping/heavy_metal/`, not shipped to production `genre_packs/`. Plus vestigial HP fields linger (`tension_tracker.py:340–350`, `history_chapter.py:64`) — stale-schema bugs per project memory `[HP removed per ADR-014]`. |
| Tactical grid engine | ADR-071 Proposed | **DEFER** | — | Protocol payload (`TacticalGridPayload`) is live and ported cleanly; engine awaits ADR-071 execution. Protocol = RESTORED (already). Engine = DEFERRED. |
| 3D dice rendering | ADR-075 Accepted (promoted from Proposed 2026-05-02) | **VERIFIED partial** | P3 | Three.js + R3F + Rapier stack landed per spec (`sidequest-ui/src/dice/DiceScene.tsx`, full dependency battery in `package.json`). Two architecture pivots from ADR-075 spec: (1) overlay→inline (`InlineDiceTray` mounted in `ConfrontationOverlay.tsx:325`; `DiceOverlay` retained but not active); (2) gesture-throw→click-and-auto-roll (per `InlineDiceTray.tsx:1–11` header). Remaining gap: per-genre `dice.yaml` theming (`material: bone\|chrome\|brass\|...`) — zero shipping packs declare it. Polish, not load-bearing. |

### C. Server dispatch handlers

| Handler | Prior ADR | Verdict | Tier | Notes |
|---------|-----------|---------|------|-------|
| Sealed-letter mechanic | ADR-024 / ADR-028 (related) | **RESTORE** | P1 | Two refs in encounter/rules; no dispatch. **Primary-audience feature per CLAUDE.md** — inclusive-pacing for Alex (_"sealed-letter turns, no fast-typist monopolies"_). Currently dark. |
| Catch-up / rapid turn replay | — | **RESTORE** | P2 | One telemetry span reference; no handler. Multiplayer latecomer flow. |

### D. Agent-layer helpers

| Helper | Verdict | Tier | Notes |
|--------|---------|------|-------|
| Lore filter (suitability filtering of LLM output) | **RESTORE** | P2 | Small module; prevents inappropriate lore mint during narration. |
| Inventory extractor (narrator → inventory patches) | **VERIFY** → likely **RESTORE** | P1 | Orchestrator does extract some structured output; confirm whether inventory specifically is covered before deciding. If not, restore. |
| Entity reference tracking | **DEFER** | — | Low load-bearing; restore if continuity validator proves insufficient alone. |
| Narrator/troper/resonator/world_builder/intent_router as separate agents | **SUPERSEDE** (already) | — | **Intentionally consolidated** under ADR-067 Unified Narrator Agent. This is not drift — it is ADR-067 being implemented. Documented here only to prevent false audit re-opens. |
| Tools abstraction (14 tool modules: assemble_turn, tactical_place, set_intent, etc.) | **DO NOT RESTORE** | — | These were the Rust-era surface for ADR-057's narrator-calls-tools design. **ADR-057 is deprecated as of 2026-05-02** — the design was infeasible under ADR-001 (`claude -p` is a one-shot subprocess; no reactive tool invocation during generation). What is actually running is the pre-ADR-057 default: narrator emits a fenced `game_patch` JSON block, server extracts mechanical state. No restoration owed; no successor ADR. Source of truth for the current narrator contract is `sidequest-server/sidequest/agents/narrator.py`. |

### E. CLI binaries and tooling

| Binary | Python state | Verdict | Tier | Notes |
|--------|--------------|---------|------|-------|
| `sidequest-namegen` | `cli/namegen/namegen.py` (22K LOC) exists; no `[project.scripts]` entry; server does not invoke | **REWIRE** | **P0** | Code is ported. Work is: register in `pyproject.toml`, add server-side dispatch to invoke as subprocess per ADR-059. |
| `sidequest-encountergen` | `__init__.py` stub only | **RESTORE** | **P0** | Port the Rust binary's logic; register entry point; wire into pregen dispatch. |
| `sidequest-loadoutgen` | `__init__.py` stub only | **RESTORE** | **P0** | Same shape as encountergen. |
| `sidequest-promptpreview` | `__init__.py` stub only | **RESTORE** | P1 | Dev iteration tool. Per ADR-082 §Context point 2 ("iteration speed is the product"), this is more load-bearing than its dev-tool label implies. |
| `sidequest-validate` | Only `projection_check.py` | **RESTORE** | P2 | Genre pack schema validation with batch error collection. Keeps content authors productive. |

### F. Test / iteration infrastructure

| Subsystem | Prior ADR | Verdict | Tier | Notes |
|-----------|-----------|---------|------|-------|
| Scene fixture hydrator + `POST /dev/scene/{name}` endpoint | ADR-092 (supersedes ADR-069) | **RESTORE** | **P0** | Design pivot resolved 2026-05-02 — ADR-092 ratifies the dev-gated HTTP-endpoint shape; ADR-069's CLI design is retired. Landed: UI scene-harness in `sidequest-ui/src/App.tsx:1183` + 4 fixture YAMLs in `scenarios/fixtures/`. Remaining gap: server endpoint (gated by `DEV_SCENES=1`) + YAML→`GameSnapshot` hydrator + OTEL spans (`scene_harness_load`, `hydrate.ok/error`, `persist.ok`). Still highest-leverage iteration-speed work outside ADR-059. |
| Scrapbook persistent image store | — | **COLLAPSE** into daemon, then **VERIFY** | P2 | One ref in `persistence.py`. Image persistence likely lives in `sidequest-daemon` now; if so, supersede the standalone concept and point at the daemon. |
| `sidequest-test-support` equivalent (MockClaudeClient, SpanCapture) | — | **VERIFY** | P3 | Not inventoried. Pytest fixtures may cover. If not, thin helper module. |

## Priority-Tier Rollup

### P0 — this sprint / next sprint (5 items)
1. ADR-059 pregen dispatch — server invokes pregen binaries at turn-time
2. `sidequest-namegen` rewire (entry point + dispatch integration)
3. `sidequest-encountergen` restore
4. `sidequest-loadoutgen` restore
5. ADR-092 scene fixture hydrator + `POST /dev/scene/{name}` endpoint (supersedes ADR-069)

> _Item 6 (Epic 28 / Confrontation Engine port-drift audit + restore) was originally P0 pending a VERIFY pass. Audit completed 2026-05-02: Pillars 1 + 2 of ADR-033 are live; only the `mood_aliases` alias-chain consumer remains as a polish gap. Moved to P3._

### P1 — within current epic window (7 items)
7. Trope engine (ADR-018)
8. NPC disposition Attitude transitions (ADR-020)
9. Sealed-letter dispatch handler
10. Continuity validator
11. Patch legality gate
12. Subsystem coverage tracker (`CoverageGap` watcher events)
13. `sidequest-promptpreview` CLI
14. Inventory extractor (**VERIFY** first)

### P2 — next-epic design-ready (11 items)
15. Gossip engine (ADR-053)
16. Accusation logic (ADR-053)
17. Genie wish consequence engine (ADR-041)
18. OCEAN shift proposals (ADR-042)
19. Chase engine (ADR-017)
20. Catch-up dispatch handler
21. Lore filter
22. `sidequest-validate` CLI expansion
23. Scene relevance validator (**REDESIGN** under ADR-086 taxonomy)
24. Room graph per-transition mechanics + new map wire message (ADR-055; promoted from Proposed 2026-05-02)
25. Edge/Composure Epic 39 wiring + push-currency rituals (ADR-078; promoted from Proposed 2026-05-02)

> _Speculative prerendering (ADR-044) was originally listed here at P2 RESTORE. Removed: ADR-044 has been re-labeled `historical` (2026-05-02) — TTS is deprecated and the ADR's "use TTS playback window as free GPU render time" premise no longer applies. No restoration owed._

### P3 — flavor / low urgency (4 items)
26. Beat filter
27. Test-support helpers (**VERIFY** first)
28. `mood_aliases` alias-chain consumer in MusicDirector track selection (ADR-033 Pillar 3 step 3) — Pydantic field + heavy_metal pack declaration exist; no consumer fires the chain. Polish, not port-casualty.
29. Per-genre `dice.yaml` theming (ADR-075 §Genre-pack theming) — `material`/`surface`/`glow`/`color_*`/`font` config feeding PBR textures. Zero packs declare it; default white-with-black dice ship for all genres. Polish, not load-bearing.

> _Conlang morpheme glossary (ADR-043) was originally listed here at P3 RESTORE. Removed: ADR-043 has been superseded by ADR-091 (culture-corpus + Markov naming, already live). No restoration owed._

### Deferred (marker confirmed or added) (8 items)
- Affinity progression (P6-deferred, existing marker)
- Advancement effect variants v1 (ADR-081 Accepted/deferred as of 2026-05-02 — `AllyEdgeIntercept` + `ConditionalEffectGating` upstream-blocked on ADR-078 Epic 39; rides P2 item 25)
- ~~Dogfight (ADR-077 Proposed)~~ — _promoted to accepted/live 2026-05-02; production sealed-letter dispatch wired_
- Edge/Composure Epic 39 wiring + push-currency rituals (ADR-078 Accepted/partial as of 2026-05-02 — Edge primitive live; per-class config + composure_break OTEL + production content owed)
- Tactical grid engine (ADR-071 Proposed — protocol already live)
- 3D dice rendering polish (ADR-075 Accepted/partial as of 2026-05-02 — stack live, per-genre `dice.yaml` theming gap remains)
- Merchant system (no ADR; write one first if needed)
- Combat mechanics detail beyond Epic 28 restoration (bundled into P0 item 6)

### Superseded / collapsed (4 items)
- Theme rotator — no evidence of value; reopen only on demonstrated pacing gap
- Scrapbook standalone — collapse into daemon (pending VERIFY)
- Separate narrator/troper/resonator agents — collapsed into unified narrator per ADR-067 (already)
- 14-tool abstraction — collapsed into direct structured output per ADR-059 (already)

## What this ADR does **not** do

- **Does not reconcile the sprint tracker.** That is PM/SM work per ADR-085 §Rule 1 and §4. This ADR gives them the verdict column they need to drive reconciliation; it does not re-open stories itself.
- **Does not redesign any accepted ADR.** ADR-017/018/020/041/042/044/053/059/069 all stand at the time of this write-up; the work scheduled here is implementation, not design. (ADR-043 was in this list at original write-time and has since been superseded by ADR-091, out of scope. ADR-069 has since been superseded by ADR-092, but the supersession was authored separately as a successor ADR — this restoration plan did not redesign ADR-069 in place; it scheduled the implementation that ADR-092 then resolved the design pivot for.)
- **Does not finalize Epic 28 scope.** Item P0-6 is explicitly `VERIFY` → likely `RESTORE`. The audit did not have time for a per-story Epic 28 port-drift pass; that is a follow-on from this ADR and from ADR-085 §Audit procedure.
- **Does not commit to the P3 tier landing.** P3 items are the first to be cut if any P0/P1 restoration exposes a deeper design problem.

## Consequences

### Positive
- Every non-parity subsystem now has a named verdict and a tier. Silent drift is no longer silent.
- ADR-059, ADR-092 (the scene-harness restoration scoped against ADR-092's HTTP design, supersedes ADR-069), and ADR-018 all have a path back from being effectively dark.
- Porter's intentional deferrals are distinguished from true drift, defending the port's phasing against false "restore everything" pressure.
- PM/SM can work sprint-planning against a prioritized list rather than a raw gap count.

### Negative
- P0 tier alone is ~6 items; realistically >1 sprint of Dev work. Scheduling will compete with new feature epics and with Epic 28's own closure.
- `VERIFY` items (Epic 28, inventory extractor, test-support, scrapbook) delay their verdicts until targeted checks run.
- Several restorations (trope engine, disposition, gossip, OCEAN shift) chain on each other — ordering matters, and ADR-087 intentionally does not hard-sequence the P1/P2 items because the chain depends on Epic 28 outcome.

### Neutral
- Prior ADRs' status is unchanged for the active set. Readers of ADR-017/018/020/041/042/044/053/059 should be directed here for implementation status via the ADR README cross-reference (pending update). ADR-043 has been superseded by ADR-091 and is out of scope. ADR-069 has been superseded by ADR-092; readers of ADR-069 should follow the supersession pointer to ADR-092 for the current design and to this ADR for restoration status.

## Follow-on tasks

1. **PM/SM:** Run ADR-085 §Audit procedure against each P0/P1/P2 row. Open/re-open stories with code-backed status.
2. **Architect (me, next pass):** Epic 28 port-drift audit — list Epic 28 stories, cross-check against Python `sidequest/game/encounter.py` + `server/dispatch/encounter_lifecycle.py` + `server/dispatch/confrontation.py`.
3. **Architect (me, next pass):** Update `docs/adr/README.md` so ADR-017/018/020/041/042/044/053/059 each reference ADR-087 for current implementation status. (ADR-043 was originally on this list; superseded by ADR-091, out of scope. ADR-069 was originally on this list; superseded by ADR-092, out of scope — readers should follow the supersession pointer.)
4. **Dev (eventual):** Take the P0 list as a delivery queue; each row becomes a story.

---

*Modo pulls a weed the shape of a disused encoder. "This one yours, Mr. Leonard?" No, Modo, this one belonged to the Rust garden. Put it on the compost — we will grow it again from seed when the light is right.*

## Implementation status (2026-05-02)

Promoted from `proposed`/`deferred` to `accepted`/`live`. This ADR is a
*meta-tracker*: its implementation surface is the document itself,
which is read, edited, and cross-referenced as the canonical post-port
restoration plan. Nine other ADRs carry `implementation-pointer: 87`
treating this as the load-bearing scheduling document.

### Sweep changes through 2026-05-02

The deferred-/proposed-bucket sweep (2026-05-02) revised the priority
tier counts and resolved several open scheduling questions. Cumulative
state changes induced in this plan during that sweep:

- **P0 went from 6 → 5 items.** ADR-033 Confrontation Engine
  port-drift audit moved from P0 (pending VERIFY) to P3 polish (only
  `mood_aliases` consumer remains). ADR-069 P0 entry replaced by
  ADR-092 (HTTP-endpoint successor) following the design-pivot
  ratification.
- **P2 went from 10 → 11 items.** Added ADR-055 (room graph
  per-transition mechanics + new map wire message) and ADR-078 +
  ADR-081 (Edge/Composure Epic 39 wiring + push-currency rituals);
  removed ADR-044 (speculative prerendering — re-labeled `historical`,
  TTS-deprecated premise).
- **P3 went from 2 → 4 items.** Added `mood_aliases` chain consumer
  (ADR-033) and per-genre `dice.yaml` theming (ADR-075).
- **Explicit-restraint list went from `ADR-071, 074, 075, 077, 078,
  081` to `ADR-071`.** ADRs 074, 075, 077, 078, 081 all promoted out of
  `proposed`/`deferred` after audit confirmed substantial
  implementation. ADR-074 + ADR-077 → `accepted`/`live`. ADR-075 +
  ADR-078 → `accepted`/`partial`. ADR-081 → `accepted`/`deferred`
  (upstream-blocked on ADR-078 Epic 39).
- **Amended/acknowledged list:** ADR-069 noted as superseded by
  ADR-092. ADR-043 was previously removed when ADR-091 superseded it.
- **Status fixes outside this ADR's table** that surface in this plan:
  ADRs 029, 072, 083 → `historical`. ADR-030 → `superseded` by ADR-053.
  ADRs 013 + 039 un-superseded back to `accepted`/`live` after ADR-057
  was deprecated for being infeasible under ADR-001 (`claude -p`
  cannot call tools mid-generation). ADR-044 → `historical`
  (TTS-playback-window premise dead with TTS).
- **Promotions to `accepted`/`live` outside the table:** ADR-045
  (Client Audio Engine), ADR-058 (Claude OTEL passthrough), ADR-076
  (narration protocol collapse), ADR-086 (image-composition taxonomy),
  ADR-013, ADR-039.

### Sibling restoration ADR

[ADR-090 (OTEL Dashboard Restoration after Python Port)](090-otel-dashboard-restoration.md) —
`accepted`/`live`. Covers the dashboard-side counterpart to this ADR's
subsystem-side scheduling. The two are post-port restoration siblings.

### Maintenance pattern

When an ADR is promoted out of `proposed`/`deferred` based on audit
findings against the Python tree, three updates land here:

1. The "Explicit restraint" or "Amended/acknowledged" line gets an
   inline parenthetical noting the promotion.
2. The relevant table row gets re-written from `DEFER` / `RESTORE` to
   `VERIFIED live` / `VERIFIED partial`.
3. The Priority Rollup gets renumbered and re-counted as items move
   tiers.

Indexes are regenerated via `scripts/regenerate_adr_indexes.py` after
each frontmatter change. The four index files
(`docs/adr/README.md`, `docs/adr/DRIFT.md`, `docs/adr/SUPERSEDED.md`,
the compact ADR block in `CLAUDE.md`) are auto-generated and not
hand-edited.
