# Port-Drift Feature Audit — Rust → Python

**Date:** 2026-04-24 (initial pass) · **Last appended:** 2026-04-30 (§9 follow-up)
**Author:** Architect (Leonard of Quirm persona)
**Scope:** Subsystem-level comparison of `~/Projects/sidequest-api` (Rust reference, archived read-only) against `~/Projects/oq-2/sidequest-server` (live Python).
**Governing ADRs:** ADR-082 (port decision, 1:1 structural mapping mandate), ADR-085 (port-drift tracker hygiene, cutover+1 sprint audit window), **ADR-087 (post-port subsystem restoration plan — verdict and tier per non-parity row below)**.
**Status:** First pass + 2026-04-30 follow-up appended as §9. Verdicts now live in ADR-087; this audit remains the inventory of record.

---

## 1. Executive Summary

The Python port is a **narration-first vertical slice**. Protocol, genre loading, orchestration, persistence, OTEL telemetry, and the unified narrator (per ADR-067) are ported cleanly and in many cases improved. The game-engine surface is a different story: roughly **12 subsystems** that had working Rust implementations are absent or reduced to data-model stubs in Python, and **4 of the 5 CLI binaries** the Rust server invoked at runtime per ADR-059 are empty.

Three categories of finding:

| Category | Count | Meaning |
|----------|-------|---------|
| **Clean parity** | ~12 subsystems | Ported 1:1 or improved; no action. |
| **Intentional P1/P6 deferral** | ~8 subsystems | Porter left a deferral marker; matches phased-port scope. |
| **Silent port-drift** | ~12 subsystems | Gone from Python with no marker; violates ADR-082 §Port Strategy. |
| **CLI / wiring drift** | 4 binaries + pregen dispatch | ADR-059 wiring is dark. |

The intentional deferrals are not bugs — they are the port's declared Phase 1 boundary. The silent drift is where ADR-085 audits are owed.

## 2. Methodology

1. Parallel inventory of both trees by module/crate (two Explore agents).
2. Cross-check named entities against each side's files.
3. Targeted `grep` to distinguish "module gone" from "renamed" from "reduced to a field."
4. Deferral markers (`P1/P6-deferred`, `Phase 1 scope`, explicit TODOs) parsed as intent.
5. `pyproject.toml` `[project.scripts]` checked for CLI wiring.

Deliberately **not** covered: tracker reconciliation (PM owns), story-level AC verification (per ADR-085 §Audit procedure, that is story-by-story work), UI/content/daemon parity (out of ADR-082 scope).

## 3. Clean Parity — ported, no action

| Subsystem | Rust crate/module | Python module |
|-----------|-------------------|---------------|
| Wire protocol (discriminated union) | `sidequest-protocol::message` | `sidequest.protocol.messages` |
| Provenance / four-tier contribution | `sidequest-protocol::provenance` | `sidequest.protocol.provenance` |
| Input sanitization (prompt injection) | `sidequest-protocol::sanitize` | `sidequest.protocol.sanitize` + `agents.prompt_redaction` |
| Dice protocol (story 34) | `sidequest-protocol::dice` + `game::dice` | `sidequest.protocol.dice` + `game.dice` |
| Genre pack loader + layered merge | `sidequest-genre` + `layered-derive` | `sidequest.genre.loader`, `.resolver` |
| SOUL markdown prompt framework | `agents::prompt_framework` | `agents.prompt_framework` (core/soul/types) |
| OTEL span catalog | `sidequest-telemetry` | `sidequest.telemetry.spans` (**expanded** — 36K LOC) |
| Persistence (SQLite + narrative log) | `game::persistence` | `game.persistence` |
| Belief state (credibility, multi-source) | `game::belief_state` | `game.belief_state` |
| Lore RAG (embedding, cosine sim) | `game::lore` | `game.lore_store`, `.lore_embedding` |
| Tension tracker (drama weight, pacing) | `game::tension_tracker` | `game.tension_tracker` |
| Resource pool (thresholds, decay) | `game::resource_pool` | `game.resource_pool` |
| Scenario / clue graph | `game::scenario_state` | `game.scenario_state` |
| Room graph navigation | `game::room_movement` | `game.room_movement` |
| World materialization (campaign boot) | `game::world_materialization` | `game.world_materialization` |
| Character builder (template resolution) | `game::character` + builder | `game.character`, `game.builder` |

Telemetry is explicitly **better** in Python — OTEL-native spans with leak audit (`leak_audit.py`), a capability Rust did not have.

## 4. Intentional P1/P6 Deferrals — marker present, scope-aligned

These carry explicit "deferred" or "P1/P6 scope" markers in Python source. They match ADR-082's phased-port philosophy (narration vertical slice first, mechanical systems later). **No action owed** — they will be claimed as stories when lit up.

| Subsystem | Evidence | Intended story/epic |
|-----------|----------|---------------------|
| Affinity progression (PC-NPC tier unlocks) | `game/character.py:55-64` — `"P6-deferred: advancement/affinity progression, not needed for narration"` | ADR-021 progression, ADR-081 advancement variants |
| Combat mechanics (beyond encounter shell) | `game/encounter.py` shell present; tick/round logic thin | ADR-033 Confrontation Engine — Epic 28 landed on Rust side |
| Advancement / XP pipeline | `server/dispatch/encounter_lifecycle.py:award_turn_xp` is partially stubbed | ADR-081 |
| Dogfight subsystem | Referenced in encounter types; no engine | ADR-077 (Proposed) |
| Edge/Composure ritual | Pool types exist (`creature_core.EdgePool`, `EdgeThreshold`); no push-currency rituals | ADR-078 (Proposed) |
| Room/tactical grid protocol | Protocol payloads present (`TacticalGridPayload`), engine absent | ADR-071 (Proposed), ADR-074 |
| 3D dice rendering handshake | Protocol ported; client-side UI story | ADR-075 (Proposed) |
| OCEAN personality evolution | `genre/models/ocean.py` exists as model; no live evolution engine | ADR-042 |

Deferrals are **aligned with ADR-082 §Port Strategy** step 5: "Agents/server/telemetry in parallel once the core is green." These are downstream of core.

## 5. Silent Port-Drift — no marker, structural absence

These had working Rust implementations at cutover and were not carried forward in any form. None carry a P1/P6 deferral note. Per ADR-082 §Port Strategy ("No consolidation, no renaming, no 'while we're in here' refactors... Deviations from the 1:1 mapping during the port are deviations and must be logged as such") each of these owes a deviation entry and a tracker verdict.

### 5.1 — Game-engine subsystems

| Subsystem | Rust location | Python status | Design ADR |
|-----------|---------------|---------------|------------|
| **Chase engine** (terrain, rig physics, phase) | `crates/sidequest-game/src/chase_depth.rs` | Absent. Only string references in `game/encounter.py`. | ADR-017 |
| **Tactical grid** (ASCII map, entity placement, layout parser) | `crates/sidequest-game/src/tactical/{grid,entity,layout,parser}.rs` | No module. Only protocol payload passes through. | ADR-071 |
| **Trope engine** (story driver selection, engagement outcomes) | `crates/sidequest-game/src/trope.rs` | `TropeState` struct exists in `session.py`; no `apply_trope_engagement` / no engine. | ADR-018 |
| **Gossip engine** (information propagation between NPCs) | `crates/sidequest-game/src/gossip.rs` | Only string references in `session.py` / `scenario_state.py` / `belief_state.py`. No `GossipEngine`. | ADR-053 |
| **NPC disposition** (Attitude enum, systematic tracking) | `crates/sidequest-game/src/disposition.rs` | Reduced to scalar `npc.disposition: int` with clamping only. No attitude tiers, no transitions, no events. | ADR-020 |
| **Merchant / transactions** (buy/sell, price calc, ledger) | `crates/sidequest-game/src/merchant.rs` | No module. String refs only. | — |
| **Accusation logic** (`evaluate_accusation`, logic proof check) | `crates/sidequest-game/src/accusation.rs` | String refs in `session_handler.py` / `scenario_state.py`; no evaluator. | Scenario system (ADR-053) |
| **Genie / wish consequence engine** | `crates/sidequest-game/src/` — `WishConsequenceEngine` | `GenieWish` tracking in `session.py`; no engine. | ADR-041 |
| **OCEAN shift proposals** (trope-driven personality events) | `crates/sidequest-game/src/ocean_shift_proposals.rs` | Model present; proposal pipeline absent. | ADR-042 |
| **Conlang morpheme glossary** | `crates/sidequest-game/src/conlang.rs` (`MorphemeGlossary`) | Zero occurrences in `sidequest/`. | ADR-043 |
| **Speculative prerendering** | `crates/sidequest-game/src/prerender.rs` (`PrerenderScheduler`) | Zero occurrences in `sidequest/`. | ADR-044 |
| **Scrapbook persistent image store** | `crates/sidequest-game/src/scrapbook_store.rs` | One ref in `persistence.py`; no store. | (image pipeline) |
| **Scene relevance validator** | `crates/sidequest-game/src/scene_relevance.rs` | Zero occurrences. | (image pipeline) |
| **Theme rotator** | `crates/sidequest-game/src/theme_rotator.rs` | Zero occurrences. | (narrative pacing) |
| **Beat filter** (conditional narration gating) | `crates/sidequest-game/src/beat_filter.rs` | Zero occurrences. | — |

### 5.2 — Server dispatch handlers

Rust `sidequest-server::dispatch` had 27 handler modules. Python consolidates into one 192K-LOC `session_handler.py` plus a smaller `dispatch/` folder. Some consolidation is natural; three gaps are substantive:

| Handler | Rust | Python status |
|---------|------|---------------|
| **Sealed-letter mechanic** | `dispatch/sealed_letter.rs` | Two refs (encounter/rules), no dispatch handler. Alex-inclusive pacing feature. |
| **Catch-up / rapid turn replay** | `dispatch/catch_up.rs` | One telemetry span reference; no handler. Latecomer multiplayer feature. |
| **Pre-generation dispatch** (invokes namegen/encountergen/loadoutgen binaries) | `dispatch/pregen.rs` | No calls out to any CLI from server code. ADR-059 wiring absent. |

### 5.3 — Agent-layer helpers

Consolidation under ADR-067 (Unified Narrator Agent) is **intentional and correct** — the multi-agent routing of ADR-010 was explicitly superseded. The tools abstraction (14 tool modules in Rust) is also intentionally removed because the unified narrator emits structured output directly (per ADR-057→059 crunch-separation → monster-manual pregen). These are not drift.

What **is** drift:

| Helper | Rust | Python status |
|--------|------|---------------|
| **Continuity validator** (contradiction detection against state) | `agents::continuity_validator` | Two refs; no validator module. |
| **Lore filter** (suitability filtering of LLM output) | `agents::lore_filter` | Absent. |
| **Inventory extractor** (narrator output → inventory patches) | `agents::inventory_extractor` | Absent. |
| **Patch legality checking** | `agents::patch_legality` | Absent — patches are applied without systematic legality gate. |
| **Entity reference tracking** | `agents::entity_reference` | Absent. |
| **Exercise/subsystem coverage tracker** | `agents::exercise_tracker::SubsystemTracker` | Partial — subsystem dispatch framework exists in `agents/subsystems/`, but `CoverageGap` watcher event is not emitted from any code path visible in inventory. |

### 5.4 — CLI binaries (ADR-059 server-side pre-generation)

Rust had five wired binaries. Python has one entry point.

| CLI | Rust | Python `cli/` | `[project.scripts]` wired? |
|-----|------|---------------|----------------------------|
| `sidequest-namegen` | Full binary, invoked by narrator | `cli/namegen/namegen.py` (22.7K LOC) + `__main__.py` | **No** |
| `sidequest-encountergen` | Full binary, invoked by narrator | `cli/encountergen/__init__.py` (empty stub) | **No** |
| `sidequest-loadoutgen` | Full binary | `cli/loadoutgen/__init__.py` (empty stub) | **No** |
| `sidequest-promptpreview` | Dev tool — end-to-end prompt preview | `cli/promptpreview/__init__.py` (empty stub) | **No** |
| `sidequest-validate` | Genre pack schema validator | `cli/validate/projection_check.py` only | **No** |

Only `sidequest-server = "sidequest.server.app:main"` is registered. **Server does not call any of these subprocesses at turn-time.** The monster manual pregen flow of ADR-059 is dark.

### 5.5 — Test / fixture harness

| Tool | Rust | Python status |
|------|------|---------------|
| **Scene fixture hydrator** (`hydrate_fixture`, `load_fixture`, `Fixture` YAML schema) | `sidequest-fixture` crate | Zero occurrences. ADR-069 wiring absent. |
| **Test support (MockClaudeClient, SpanCapture)** | `sidequest-test-support` | Pytest fixtures in `tests/` presumably cover — not audited here. |

## 6. Python Extensions — Post-Port Improvements

Positive drift (new capability, well-marked):

| Subsystem | Rationale |
|-----------|-----------|
| **Lethality arbiter** (`agents/lethality_arbiter.py`) | Policy-driven verdict on lethality claims; lethality policy loader in genre. New — not in Rust. |
| **Local DM decomposer** (`agents/local_dm.py` + `protocol/dispatch.py`) | `DispatchPackage`, per-player visibility/perception/fidelity baseline. Matches ADR-028 (Perception Rewriter) and ADR-037 (per-player state) more fully than Rust had. |
| **Subsystem dispatch bank** (`agents/subsystems/`) | Topologically-sorted registration of subsystems with dependency declaration. Cleaner extension point than Rust's agent list. |
| **StateDelta / compute_delta** (`game/delta.py`) | Explicit state-diff computation for wire efficiency. |
| **Projection filter** (`game/projection_filter.py` + telemetry `projection_decide_span`) | Per-player state projection. Enables multiplayer perception without re-deriving on every send. |
| **OTEL span expansion** | 40+ named spans vs. Rust's ~10. Includes `local_dm_*`, `projection_*`, `mp_*` spans that did not exist. |
| **Commands handler** (`game/commands.py`) | Slash command routing as a game-layer concern. Was in server dispatch in Rust. |

## 7. Recommendations

### 7.1 — Process (for SM / PM)

1. **Run the ADR-085 audit procedure** on each "silent drift" row in §5 against the sprint tracker. Most of these have stories in the Rust session archive; they owe re-opening per ADR-085 Rule 2 ("Port-drift is a bug, not a new story").

2. **Add deferral markers** to the §5.1 subsystems that *are* deferred on purpose but currently unmarked. If Architect+PM agree that (say) merchant is P7 and waiting on Confrontation Engine to stabilize, put a `# P7-deferred:` comment on the location where the subsystem would attach. Silent absence is indistinguishable from forgotten absence; an explicit marker converts drift into deferral and the audit trail heals.

3. **ADR-059 wiring is the single biggest hot item.** The monster-manual pregen flow was an accepted ADR and the Rust server invoked those binaries at turn time. Python has `namegen` code but no dispatcher, and `encountergen`/`loadoutgen` are empty. Either re-wire or supersede ADR-059 with an ADR that says "narrator emits the names/encounters/loadouts inline now." Right now we're in limbo.

### 7.2 — Architecture (for me, next pass)

1. **Draft a supersession-or-restoration ADR for each subsystem in §5.1.** Most have a design ADR already (ADR-017 chase, ADR-020 disposition, ADR-018 trope, ADR-041 genie, ADR-042 OCEAN, ADR-043 conlang, ADR-044 prerender, ADR-053 scenario+gossip, ADR-071 tactical, ADR-077 dogfight). The choice for each is **restore, redesign, or supersede**. I recommend doing this as a batched addendum, not 15 new ADRs.

2. **Protocol decomposition (ADR-065) is still proposed.** The `session_handler.py` monolith at 192K LOC suggests ADR-065 and ADR-063 (dispatch handler splitting) should be promoted from "proposed/unexecuted" to scheduled work. The port was the right time to decompose; the port didn't.

3. **Fixture story (ADR-069) is dark.** For a single-author creative project where iteration speed is the product (ADR-082 §Context point 2), losing the fixture hydrator is a bigger quality-of-life hit than it looks. This is almost certainly worth restoring before any of the §5.1 subsystems.

### 7.3 — Priority ordering (opinion)

If forced to rank the §5 items for restoration:

1. **ADR-059 pregen wiring** — accepted ADR, protocol+binaries partly there, biggest risk to narrator quality (names/encounters/loadouts drift into Claude's improvisation).
2. **Fixture hydrator (ADR-069)** — unblocks iteration velocity, which is the reason the port happened.
3. **Trope engine (ADR-018)** — narrative pacing depends on it; `TropeState` data without an engine is dead weight.
4. **Disposition → attitude transitions (ADR-020)** — scalar int is below tabletop-DM quality, which fails the Keith-as-player test.
5. **Continuity validator + patch legality** — OTEL lie-detection is load-bearing per CLAUDE.md; these are the actual checks behind it.
6. Everything else in §5.1 per its own ADR status (Proposed ones can wait).

## 8. Out-of-Scope Notes

- **Tests** were not inventoried — ADR-082 says tests port alongside code, so test drift should approximate code drift, but this audit does not verify that.
- **Protocol byte-wire fidelity** (ADR-082 §Protocol Compatibility risk) is not re-verified here. That belongs in a playtest or a captured-payload diff.
- **Daemon and UI** are out of ADR-082 scope per its Scope table and are not audited.

---

## 9. 2026-04-30 Follow-Up — Six Days On

The original audit (§§1–8 above) was written 2026-04-24. This follow-up is appended six days later to capture (a) verdicts assigned by ADR-087, (b) one factual correction, and (c) which silent-drift rows have moved.

### 9.1 — One factual correction to §5.3

The audit listed **patch legality checking** as absent from Python ("Absent — patches are applied without systematic legality gate"). That was wrong.

`patch_legality_check` exists in `sidequest-server/sidequest/telemetry/validator.py`, registered by `register_check(patch_legality_check)` and invoked on every `TurnRecord`. Implementation is partial — it's a telemetry-side gate, not the agent-layer module the Rust tree had — but the *concern* is not dark. Status should be **partial**, not absent. ADR-087's "RESTORE P1" verdict still applies because the check is not yet structurally aligned with the Rust agent-layer design, but the floor is higher than the audit implied.

### 9.2 — ADR-087 verdict assignment (the audit's main consumer)

ADR-087 (`docs/adr/087-post-port-subsystem-restoration-plan.md`, dated 2026-04-24, status Proposed) consumed every row in §§4–5 and assigned a verdict + tier. The mapping:

| Audit row | ADR-087 verdict | Tier |
|-----------|------------------|------|
| §5.4 ADR-059 pregen dispatch | RESTORE | **P0** |
| §5.4 sidequest-namegen | REWIRE | **P0** |
| §5.4 sidequest-encountergen | RESTORE | **P0** |
| §5.4 sidequest-loadoutgen | RESTORE | **P0** |
| §5.5 fixture hydrator (ADR-069) | RESTORE | **P0** |
| Confrontation Engine / Epic 28 (not in original audit; flagged in ADR-087) | VERIFY → likely RESTORE | **P0** |
| §5.1 Trope engine | RESTORE | P1 |
| §5.1 NPC disposition (Attitude) | RESTORE | P1 |
| §5.2 sealed-letter dispatch | RESTORE | P1 |
| §5.3 continuity validator | RESTORE | P1 |
| §5.3 patch legality (see §9.1 correction) | RESTORE | P1 |
| §5.3 subsystem coverage tracker | RESTORE | P1 |
| §5.4 sidequest-promptpreview | RESTORE | P1 |
| §5.3 inventory extractor | VERIFY → likely RESTORE | P1 |
| §5.1 gossip engine, accusation logic | RESTORE | P2 |
| §5.1 genie wish engine | RESTORE | P2 |
| §5.1 OCEAN shift proposals | RESTORE | P2 |
| §5.1 chase engine | RESTORE | P2 |
| §5.2 catch-up dispatch | RESTORE | P2 |
| §5.3 lore filter | RESTORE | P2 |
| §5.1 speculative prerendering | RESTORE | P2 |
| §5.4 sidequest-validate | RESTORE | P2 |
| §5.1 scene relevance validator | **REDESIGN** | P2 (under ADR-086 image-composition taxonomy) |
| §5.1 conlang morpheme glossary | RESTORE | P3 |
| §5.1 beat filter | RESTORE | P3 |
| §5.5 test-support helpers | VERIFY | P3 |
| §4 affinity progression, advancement/XP, dogfight, Edge/Composure rituals, tactical grid engine, 3D dice | DEFER (markers confirmed) | — |
| §5.1 merchant / transactions | DEFER (no ADR; write one first) | — |
| §5.1 theme rotator | **SUPERSEDE** | — |
| §5.1 scrapbook persistent store | COLLAPSE into daemon, then VERIFY | P2 |
| §5.3 separate narrator/troper/resonator/world_builder | SUPERSEDE (already, per ADR-067) | — |
| §5.3 14-tool abstraction | SUPERSEDE (already, per ADR-059) | — |

### 9.3 — Sprint movement against the audit

Sprint 3 opened 2026-04-27 (Epic 45: Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup). The first three completed stories landed in this window:

- **Story 45-1** — sealed-letter shared-world delta (re-scope of pre-port 37-37). Closes a slice of the §5.2 sealed-letter handler gap *for shared-world state*; the dispatch handler itself is still **dark**.
- **Story 45-2** — turn barrier counts active turn-takers, not lobby connections. Adjacent to but not the same as §5.2 sealed-letter restoration.
- **Story 45-3** — momentum readout state sync (UI subscribes to `BEAT_RESOLVED`). Surfaces engine-side momentum tracking from §6's Python-era extensions.

None of the §§5.1, 5.4, 5.5 rows are claimed yet. ADR-087's P0 tier (pregen dispatch, namegen rewire, encountergen, loadoutgen, fixture hydrator, Epic 28 verify) is the pending dispatch.

### 9.4 — Tree drift since 2026-04-24

A handful of additions to `sidequest-server/sidequest/` since the audit, not all named in §6:

| Module | Effect on audit |
|--------|-----------------|
| `cli/corpusdiff/`, `cli/corpuslabel/`, `cli/corpusmine/` | New CLI lane; corpus extraction tools added (likely tied to LocalDM dormancy decision per ADR-082-era spec). Independent of §5.4's pregen CLI gap. |
| `game/shared_world_delta.py` | Closes part of the §5.2 sealed-letter gap (story 45-1 wiring). |
| `game/region_init.py`, `game/region_validation.py` | Cartography-config-as-chargen-seed (the residual world.cartography.yaml load after ADR-019 supersession). Not on audit; counts as Python-era extension. |
| `game/resolution_signal.py` | Handshake plumbing for momentum/beat resolution (story 45-3 adjacent). Python-era extension. |
| `agents/encounter_render.py` | New agent helper. Not on audit. |
| `agents/lethality_arbiter.py` (was on audit) | Continues to live in §6 as a positive Python-era extension. |
| `handlers/`, `magic/`, `audio/`, `media/`, `renderer/` packages | Top-level package additions outside the original `agents/`-`game/`-`server/`-`telemetry/` quadrant. **Not yet inventoried** — flagged for the next audit pass; some may reflect ADR-086 image-taxonomy work and ADR-090 OTEL dashboard restoration. |

### 9.5 — Genre pack drift (out of original audit scope but consequential)

Five packs that appeared in the §1 implicit landscape have been moved into `sidequest-content/genre_workshopping/` (staging tree, not loaded by the server): `low_fantasy`, `neon_dystopia`, `pulp_noir`, `road_warrior`, plus duplicate workshop copies of `heavy_metal` and `spaghetti_western`. The latter two also have **empty production directories** (`genre_packs/heavy_metal/` and `genre_packs/spaghetti_western/`) — promotion stalled half-way. Loadable production packs are 5: caverns_and_claudes, elemental_harmony, mutant_wasteland, space_opera, victoria. See `docs/genre-pack-status.md` for the breakdown.

This is not port-drift in the ADR-082 sense — it's content-curation drift — but it affects how `road_warrior`'s missing chase engine (§5.1) lands in user terms: the pack itself is also not in production.

### 9.6 — Methodology delta (next pass)

Four things to add when this audit is re-run:

1. **Test-tree parity.** ADR-082 mandated test-along-with-code; original audit deferred. Owed before claiming RESTORE on §5.3 helpers.
2. **The five new packages** under `sidequest-server/sidequest/` (`audio/`, `handlers/`, `magic/`, `media/`, `renderer/`) need a Python-vs-pre-port comparison. Some may be new domains; some may absorb subsystems counted as drift in §5.
3. **OTEL span coverage** against the lie-detection promise in CLAUDE.md (_"The GM panel is the lie detector"_). ADR-090 is restoring the dashboard surface; pair the next audit with a span-by-subsystem check.
4. **Protocol byte-wire fidelity** against Rust captures, listed as out-of-scope in §8. Becomes load-bearing once ADR-082 §Protocol Compatibility risk gets retired or reaffirmed.

---

*Modo would say: "Mr. Leonard's been counting things, has he?" Yes, Modo. Twelve subsystems of counting on Friday, an addendum on the following Wednesday. The counting is iterative.*
