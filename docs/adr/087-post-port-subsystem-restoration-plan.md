---
id: 87
title: "Post-Port Subsystem Restoration Plan"
status: proposed
date: 2026-04-24
deciders: ["Keith Avery (Bossmang)", "Leonard of Quirm (Architect, design mode)"]
supersedes: []
superseded-by: null
related: [17, 18, 20, 41, 42, 43, 44, 53, 59, 67, 69, 71, 74, 75, 77, 78, 81, 82, 85, 86]
tags: [project-lifecycle]
implementation-status: deferred
implementation-pointer: null
---

# ADR-087: Post-Port Subsystem Restoration Plan

- **Input:** `docs/port-drift-feature-audit-2026-04-24.md` (audit that fed this ADR)
- **Governing:** ADR-082 (1:1 port mandate), ADR-085 (port-drift tracker hygiene)
- **Consolidation context:** ADR-067 (Unified Narrator Agent — explains why several agent helpers are intentionally gone)
- **Amended/acknowledged:** ADR-017, 018, 020, 041, 042, 044, 053, 059, 069 (their implementations are missing or partial in Python; this ADR schedules their restoration without reopening the original decisions). _ADR-043 was originally in this list; it has since been superseded by ADR-091 and dropped from the restoration scope._
- **Explicit restraint:** ADR-071, 074, 075, 077, 078, 081 (Proposed — not executed in Rust either; stay deferred)

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
| Confrontation engine / Combat Epic 28 port verification | ADR-033 Accepted (Epic 28 landed Rust-side) | **VERIFY** → likely **RESTORE** | **P0** | Epic 28 was the biggest body of work immediately pre-port. Audit did not verify how much made it through. Dedicated port-drift audit on Epic 28 stories per ADR-085 §Audit procedure owed before a restoration plan can be finalized. |
| Speculative prerendering | ADR-044 Accepted | **RESTORE** | P2 | Zero occurrences. Performance feature; image latency is a primary-audience UX concern. |
| Merchant / transactions | — | **DEFER** | — | No ADR, no current need. If economy becomes a feature, write an ADR first, then port. Add deferral marker to `game/__init__.py`. |
| Affinity progression | ADR-021, ADR-081 | **DEFER** | — | Porter's `P6-deferred` marker confirmed at `game/character.py:55-64`. Will land with the advancement epic. No action. |
| Advancement / XP pipeline | ADR-081 Proposed | **DEFER** | — | Partial `award_turn_xp` stub; marker aligned with ADR-081's Proposed status. |
| Dogfight subsystem | ADR-077 Proposed | **DEFER** | — | Proposed ADR, never implemented in Rust either. Stays deferred. |
| Edge/Composure push-currency rituals | ADR-078 Proposed | **DEFER** | — | Pool types exist (`creature_core.EdgePool`); rituals await ADR-078 execution. |
| Tactical grid engine | ADR-071 Proposed | **DEFER** | — | Protocol payload (`TacticalGridPayload`) is live and ported cleanly; engine awaits ADR-071 execution. Protocol = RESTORED (already). Engine = DEFERRED. |
| 3D dice rendering | ADR-075 Proposed | **DEFER** | — | Protocol ported; client-side UI work out of server scope. |

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
| Tools abstraction (14 tool modules: assemble_turn, tactical_place, set_intent, etc.) | **SUPERSEDE** (already) | — | **Intentionally removed** per ADR-057 → ADR-059 progression: narrator emits structured output directly rather than calling tools. Not drift. |

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
| Scene fixture hydrator (`hydrate_fixture`, `load_fixture`, `Fixture` schema) | ADR-069 Accepted | **RESTORE** | **P0** | "Zero occurrences" was true at original write-time but is now stale. Landed since: UI scene-harness in `sidequest-ui/src/App.tsx:1183` + 4 fixture YAMLs in `scenarios/fixtures/`. Remaining gap: server `/dev/scene/{name}` endpoint + fixture→snapshot hydrator. **Design pivot unresolved:** ADR-069 specifies a CLI-driven flow (`sidequest-fixture load X` → save.db); the half-wired UI side targets an HTTP endpoint. Restoration must pick one — amend ADR-069 or write a successor — before building. Still highest-leverage iteration-speed work outside ADR-059. |
| Scrapbook persistent image store | — | **COLLAPSE** into daemon, then **VERIFY** | P2 | One ref in `persistence.py`. Image persistence likely lives in `sidequest-daemon` now; if so, supersede the standalone concept and point at the daemon. |
| `sidequest-test-support` equivalent (MockClaudeClient, SpanCapture) | — | **VERIFY** | P3 | Not inventoried. Pytest fixtures may cover. If not, thin helper module. |

## Priority-Tier Rollup

### P0 — this sprint / next sprint (6 items)
1. ADR-059 pregen dispatch — server invokes pregen binaries at turn-time
2. `sidequest-namegen` rewire (entry point + dispatch integration)
3. `sidequest-encountergen` restore
4. `sidequest-loadoutgen` restore
5. ADR-069 scene fixture hydrator
6. Epic 28 / Confrontation Engine port-drift audit + restore (**VERIFY** first)

### P1 — within current epic window (7 items)
7. Trope engine (ADR-018)
8. NPC disposition Attitude transitions (ADR-020)
9. Sealed-letter dispatch handler
10. Continuity validator
11. Patch legality gate
12. Subsystem coverage tracker (`CoverageGap` watcher events)
13. `sidequest-promptpreview` CLI
14. Inventory extractor (**VERIFY** first)

### P2 — next-epic design-ready (10 items)
15. Gossip engine (ADR-053)
16. Accusation logic (ADR-053)
17. Genie wish consequence engine (ADR-041)
18. OCEAN shift proposals (ADR-042)
19. Chase engine (ADR-017)
20. Catch-up dispatch handler
21. Lore filter
22. Speculative prerendering (ADR-044)
23. `sidequest-validate` CLI expansion
24. Scene relevance validator (**REDESIGN** under ADR-086 taxonomy)

### P3 — flavor / low urgency (2 items)
25. Beat filter
26. Test-support helpers (**VERIFY** first)

> _Conlang morpheme glossary (ADR-043) was originally listed here at P3 RESTORE. Removed: ADR-043 has been superseded by ADR-091 (culture-corpus + Markov naming, already live). No restoration owed._

### Deferred (marker confirmed or added) (8 items)
- Affinity progression (P6-deferred, existing marker)
- Advancement/XP pipeline (ADR-081 Proposed)
- Dogfight (ADR-077 Proposed)
- Edge/Composure rituals (ADR-078 Proposed)
- Tactical grid engine (ADR-071 Proposed — protocol already live)
- 3D dice rendering (ADR-075 Proposed — protocol already live)
- Merchant system (no ADR; write one first if needed)
- Combat mechanics detail beyond Epic 28 restoration (bundled into P0 item 6)

### Superseded / collapsed (4 items)
- Theme rotator — no evidence of value; reopen only on demonstrated pacing gap
- Scrapbook standalone — collapse into daemon (pending VERIFY)
- Separate narrator/troper/resonator agents — collapsed into unified narrator per ADR-067 (already)
- 14-tool abstraction — collapsed into direct structured output per ADR-059 (already)

## What this ADR does **not** do

- **Does not reconcile the sprint tracker.** That is PM/SM work per ADR-085 §Rule 1 and §4. This ADR gives them the verdict column they need to drive reconciliation; it does not re-open stories itself.
- **Does not redesign any accepted ADR.** ADR-017/018/020/041/042/044/053/059/069 all stand. The work scheduled here is implementation, not design. (ADR-043 was in this list at original write-time; it has since been superseded by ADR-091 and is no longer part of the restoration scope.)
- **Does not finalize Epic 28 scope.** Item P0-6 is explicitly `VERIFY` → likely `RESTORE`. The audit did not have time for a per-story Epic 28 port-drift pass; that is a follow-on from this ADR and from ADR-085 §Audit procedure.
- **Does not commit to the P3 tier landing.** P3 items are the first to be cut if any P0/P1 restoration exposes a deeper design problem.

## Consequences

### Positive
- Every non-parity subsystem now has a named verdict and a tier. Silent drift is no longer silent.
- ADR-059, ADR-069, and ADR-018 all have a path back from being effectively dark.
- Porter's intentional deferrals are distinguished from true drift, defending the port's phasing against false "restore everything" pressure.
- PM/SM can work sprint-planning against a prioritized list rather than a raw gap count.

### Negative
- P0 tier alone is ~6 items; realistically >1 sprint of Dev work. Scheduling will compete with new feature epics and with Epic 28's own closure.
- `VERIFY` items (Epic 28, inventory extractor, test-support, scrapbook) delay their verdicts until targeted checks run.
- Several restorations (trope engine, disposition, gossip, OCEAN shift) chain on each other — ordering matters, and ADR-087 intentionally does not hard-sequence the P1/P2 items because the chain depends on Epic 28 outcome.

### Neutral
- Prior ADRs' status is unchanged for the active set. Readers of ADR-017/018/020/041/042/044/053/059/069 should be directed here for implementation status via the ADR README cross-reference (pending update). ADR-043 has been superseded by ADR-091 and is out of scope.

## Follow-on tasks

1. **PM/SM:** Run ADR-085 §Audit procedure against each P0/P1/P2 row. Open/re-open stories with code-backed status.
2. **Architect (me, next pass):** Epic 28 port-drift audit — list Epic 28 stories, cross-check against Python `sidequest/game/encounter.py` + `server/dispatch/encounter_lifecycle.py` + `server/dispatch/confrontation.py`.
3. **Architect (me, next pass):** Update `docs/adr/README.md` so ADR-017/018/020/041/042/044/053/059/069 each reference ADR-087 for current implementation status. (ADR-043 was originally on this list; superseded by ADR-091, out of scope.)
4. **Dev (eventual):** Take the P0 list as a delivery queue; each row becomes a story.

---

*Modo pulls a weed the shape of a disused encoder. "This one yours, Mr. Leonard?" No, Modo, this one belonged to the Rust garden. Put it on the compost — we will grow it again from seed when the light is right.*
