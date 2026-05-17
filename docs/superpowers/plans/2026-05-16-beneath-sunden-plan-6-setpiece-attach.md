# Beneath Sünden — Plan 6: Set-Piece Attach + Trope/Quest-at-Attach + Complication Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Plan 4's set-piece *templates* live. At attach (during materialization), roll each `SetPiece`'s component slots from the seed, **start** its trope components (resolved against the world's `tropes.yaml` — register into the live trope engine so escalation begins *before* the party reaches the room), **seed** its quest components (resolved against scenario state), and write every started-but-unresolved thread into the **open-complication ledger** with origin region + status. Then wire the resolution side: when players close/finish/fail/kill/seal/flee a thread, flip its ledger status and emit the resolution span. This is spec §6 + §7.1 — the *dramatic* half of the bursty feel and the Tomb-of-Horrors escalation spine. `setpieces.py`'s own module docstring names this plan as the owner: *"Plan 6 rolls set-pieces / starts trope+quest components / writes the ledger."*

**Architecture:** One new module `sidequest/dungeon/setpiece_attach.py` exposing a single deterministic public entry point that **Plan 7's attach stage invokes inside the `dungeon.materialize.attach` span** (Plan 7 owns the span + ordering; Plan 6 owns the thread logic and emits `setpiece.attach`/`trope.start`/`quest.seed`/`ledger.add` as children; `ledger.resolve` is emitted from the gameplay resolution path). Slot rolls are a **pure deterministic function** of `(campaign_seed, expansion_id, region_id, setpiece_id, slot_id)` — Plan 7's commit freezes the result into the save; the save is source of truth and rolls are never recomputed (spec §7). The number of set-pieces/components lit per expansion is bounded by `threads_lit_per_expansion` driven from `burst_magnitude` (spec §7.1 — the dramatic burst paired with Plan 2's structural `connection_burst`). Three bindings are **reconcile-at-execution seams** declared against their contracts, the established Plan 2/3/4 honest-deferral stance: (1) **Plan 5's complication-ledger storage** (in flight, oq-1 — spec §7.1 contract); (2) the **trope engine** (`snap.active_tropes` / `TropeState`, ADR-018, *live* — a real binding, low risk); (3) **scenario/quest seeding** (`ScenarioState`, **ADR-053 `partial`** — a stated dependency risk, handled like Plan 7's ADR-055 note: bind to the real surface, stop-and-report if incomplete, never stub).

## Execution Preamble (read before Task 0)

**This plan executes after Plan 5 (persistence/ledger storage) is merged. It does NOT depend on Plan 7** — Plan 7 depends on *this*. Critical-path position: Plan 5 (in flight, oq-1) → **Plan 6 (this — next executable)** → Plan 7 (keystone, gated on 5+6). Writing it now is an Architect design artifact in parallel with oq-1's Plan 5; it is not a directive to begin coding.

### Cross-workspace ownership

oq-2 authors/pushes/opens PRs; **oq-1 owns Plan 5, git-sync, merge, verify.** This plan's *design* is oq-2/Architect; *execution* is gated on Plan 5 and coordinated with oq-1. Do not begin Task 1 while Plan 5's ledger API is unmerged — designing the ledger writes against a moving target produces rot. The contract bound here is **spec §7.1's ledger description**, not in-flight Plan 5 code; bind to the real Plan 5 API at execution and reconcile (Self-Review).

### Scope boundaries (deliberate — NOT omissions; logged so review does not flag them)

- **No persistence schema authored here.** The complication-ledger *storage* (first-class persisted structure, spec §7) is Plan 5. This plan defines *what is added at attach* and *the resolve transition*; it calls Plan 5's ledger primitive. It does not define save tables.
- **No pipeline orchestration / no async worker / no frontier here.** That is Plan 7. This plan's entry point is *called by* Plan 7's attach stage; it does not run the pipeline.
- **No new trope engine and no new scenario engine.** Trope components register into the **existing** ADR-018 trope engine (`snap.active_tropes`); quest components seed into the **existing** ADR-053 `ScenarioState`. ⚠️ **SUPERSEDED — see "Architect Task-0 Reconciliation (2026-05-16)" below: the quest-component host is Plan 5's `ComplicationThread(kind="quest")`, NOT `ScenarioState`.** Plan 6 does cross-resolution (id → real trope/quest) and wiring, not a reimplementation. Reuse-first (ADR-106 / pragmatic-restraint).
- **Set-pieces ≠ cookbook special rooms.** `DungeonTheme.set_pieces` (Plan 4 templates) is this plan's source library. The manifest's `special_rooms` are *curated content rows* placed by Plan 7's curate/attach — a different axis. Slot options that reference creatures/loot resolve against the manifest's `wandering_table`/`loot_table` (the join point, Task 3). Do not conflate the two; this boundary is stated so review does not flag the absence of special-room handling here.
- **No CR→Edge translation here.** That seam is Plan 7 Task 4 (owned, end-to-end). Plan 6 consumes already-translated creature refs from the manifest.

## §6 / §7.1 / §12 decisions baked in here (tunable — reversible)

| Decision | Default | Knob | Rationale |
|----------|---------|------|-----------|
| Threads lit per expansion | derived from `burst_magnitude` (the dramatic half) | `threads_lit_per_expansion` | Spec §7.1 — paired with Plan 2's `connection_burst`; "how big a spike feels fun" is empirical, playtest-tuned. |
| Slot-roll seed | `(campaign_seed, expansion_id, region_id, setpiece_id, slot_id)` | — | Deterministic-given-inputs; frozen by Plan 7 commit (spec §7). Not a knob — a contract. |
| Trope start | append `TropeState` to `snap.active_tropes`, `status="progressing"` | — | Reuses ADR-018 escalation (`trope_tick.tick_tropes`) so a started trope counts down before room entry (spec §6 `priest_demands_a_sacrifice`). |
| Unresolved-thread persistence | every started trope/quest → one ledger entry (origin region + status) | — | Spec §7.1 — first-class, fully legible, no hidden math. |
| Resolution | ledger entry clears **only** on player resolution (close/finish/fail/kill/seal/flee) | — | Spec §7.1 — threads shrink only on resolution; detection lives in the existing trope/scenario systems, Plan 6 subscribes the ledger to them. |

## File Structure

### sidequest-server

| Path | Action | Responsibility |
|------|--------|----------------|
| `sidequest/dungeon/setpiece_attach.py` | Create | Slot roll + trope-start + quest-seed + ledger-add; `AttachReport.as_dict()` span contract; the public entry point Plan 7 calls |
| `sidequest/dungeon/__init__.py` | Edit | Export the Plan 6 public surface |
| the gameplay resolution path (trope-resolve / scenario-resolve sites) | Edit | Subscribe the ledger: thread resolved → `ledger.resolve` + status flip |
| `tests/dungeon/test_setpiece_attach.py` | Create | Roll determinism, trope-start, quest-seed, ledger-add, burst bounding |
| `tests/dungeon/test_setpiece_attach_wiring.py` | Create | **Mandatory wiring test** — entry point reachable from the real Plan-7-attach call shape; resolve subscription fires from the real trope/scenario resolution path |

### sidequest-content

None. Set-piece templates + theme libraries shipped in Plan 4; `tropes.yaml`/scenario content is existing world content.

## Task 0: Branch setup + dependency gate

- [x] **Hard gate:** confirm Plan 5 (persistence/ledger storage) is **merged**. If not, stop. Record merged-base SHA. → **MERGED. PR #303 `feat/beneath-sunden-persistence`, merged-base SHA `cfd4aa1`.**
- [x] Read the **real merged** Plan 5 ledger API. Every "spec §7.1 contract" seam below binds to it at execution; log divergence in Self-Review (do not silently adapt). → **Done — see reconciliation below.**
- [x] Read the live `tropes.yaml` shape (world content) and the real `ScenarioState` seeding surface. **If the scenario/quest-seeding surface is too partial (ADR-053 `partial`) to seed a quest component, stop and report it** as the stated dependency risk — do not stub a fake seed (No Stubbing / No Silent Fallbacks; `feedback_no_burying_bombs`). → **Probed. Reported below — seam redirected, not stubbed.**
- [x] Branch in `sidequest-server` per `repos.yaml` base. → **`feat/beneath-sunden-plan-6-setpiece-attach` off `develop` (server) + off `main` (orchestrator, for plan/spec docs).**

## Architect Task-0 Reconciliation (2026-05-16)

Task 0's three investigative checkboxes are discharged here against **merged** Plan 5 (`cfd4aa1`), not spec §7.1 prose. Dev: bind to these findings; do not re-derive. Log any further divergence in Self-Review per the plan's honest-deferral discipline.

**Seam (1) — Plan 5 complication-ledger storage → GREEN (one favorable divergence).**
Merged API in `sidequest/dungeon/persistence.py`:
- `ComplicationThread(thread_id, origin_region_id, kind, status, started_at_depth_score, payload)` — `kind ∈ {"trope","quest"}`. This is the dataclass Task 4 binds to. `to_dict`/`from_dict` present.
- `DungeonStore.open_thread(thread: ComplicationThread)` — the ledger-add primitive (Task 4). Raises loudly on duplicate `thread_id` (no silent fallback). **It already wraps `ledger_add_span` internally.**
- `DungeonStore.resolve_thread(thread_id)` — the resolve primitive (Task 5). Wraps `ledger_resolve_span`.
- `DungeonStore.get_thread(thread_id)` — raises `NotFoundError` if absent.
- Span constants `ledger.add` / `ledger.resolve` are **owned by Plan 5** in `sidequest/telemetry/spans/dungeon_persist.py`.

**Divergence to carry into Self-Review:** Plan 6 does **NOT** emit `ledger.add` / `ledger.resolve` itself — Plan 5 owns those spans inside `open_thread()` / `resolve_thread()`. The line-7 architecture statement ("Plan 6 ... emits `ledger.add` as children") is superseded: Plan 6 emits only `setpiece.attach` / `trope.start` / `quest.seed` and **calls** the Plan 5 primitive for the ledger row + its span. This is favorable — less surface for Plan 6 to own, span contract centralized.

**Seam (2) — ADR-018 trope engine → GREEN (as the plan predicted, low-risk).**
`snapshot.active_tropes: list[TropeState]` is live on the session snapshot (`sidequest/game/session.py:587`); `trope_tick.tick_tropes` mutates it in place. Trope-start = append a `TropeState(status="progressing")` to `snapshot.active_tropes` (Task 2/3). No new engine. Binding confirmed real.

**Seam (3) — quest-component host → REDIRECTED (the ADR-053 bomb, defused on paper).**
`ScenarioState` (`sidequest/game/scenario_state.py`) is a **whodunit** model: clue graph, `guilty_npc`, suspect roles, gossip adjacency, "binding surface only, between-turn processing deferred." It has **no surface to seed a dungeon quest thread and never will — that is not its axis.** Plan 6 scope bullet "quest components seed into ADR-053 `ScenarioState`" was written against spec prose *before Plan 5 merged* and is **stale**.

**Architect decision (supersedes scope line 21):** A dungeon quest component is a `ComplicationThread(kind="quest")` written via Plan 5's `open_thread()` and cleared via `resolve_thread()` — **the same primitive as a trope thread, different `kind`**. Plan 5 already shipped the quest-thread host. `ScenarioState` is explicitly **out of Plan 6's path** (different subsystem, ADR-053 murder-mystery axis; conflating it is exactly the line-22 axis error). This is a **seam redirect, not a descope and not a stub**: every quest component still produces a real, persisted, legible ledger thread — it just lands in the ledger where Plan 5 put the `kind="quest"` slot, not in a whodunit clue graph.

**Net:** all three seams resolved. Task 1 is unblocked. Branch `feat/beneath-sunden-plan-6-setpiece-attach` off `develop` in `sidequest-server` (empirical: every merged Sünden server PR #295–#303 used `feat/beneath-sunden-*` → `develop`).

## Task 1: Slot roll — pure deterministic component selection

**TDD intent:** for a `SetPiece`, roll each `ComponentSlot` to exactly one `SlotOption` using a `random.Random` seeded by `(campaign_seed, expansion_id, region_id, setpiece_id, slot_id)` (blake2b-mixed, **not** XOR — pre-empt the Plan 2 `seed ^ 0x5EED` fixed-point gotcha at this layer too). Pure function: identical inputs → identical rolled set-piece. No I/O, no engine mutation.

- [ ] Test: identical inputs → byte-identical rolled result across repeated calls and process restarts (frozen-into-save contract; spec §7).
- [ ] Test: distinct `(region_id|setpiece_id|slot_id)` tuples do not collude (different rolls — no accidental shared sub-stream).
- [ ] Test: a `ComponentSlot` with one option rolls that option; an empty options list was already rejected by Plan 4's validator — assert that guard holds, do not re-validate.

## Task 2: Trope-component start → live trope engine (ADR-018 seam)

**TDD intent:** for each `TropeComponent` on the rolled set-piece, resolve `trope_id` against the world's `tropes.yaml` (loud failure if the id is unknown — a content authoring bug, not a silent skip), and **start** it: append a `TropeState` (`status="progressing"`, origin region recorded, `params` carried) to `snap.active_tropes` so `trope_tick.tick_tropes` escalates it from the next tick — before the party reaches the room (spec §6). Emit `trope.start` per component.

- [ ] Test: a started trope appears in `snap.active_tropes` with `status="progressing"` and origin region; a subsequent `tick_tropes` advances its progress (proves it is *live*, not inert — lie detector).
- [ ] Test: unknown `trope_id` raises loudly (content bug surfaced, not swallowed); the failure path still emits a `trope.start` span carrying the failure.
- [ ] Test: `threads_lit_per_expansion` bounds the count — with burst N, at most N trope+quest components across the expansion are lit; the selection of *which* is deterministic from the seed.

## Task 3: Quest-component seed → ScenarioState (ADR-053 `partial` seam)

**TDD intent:** for each `QuestComponent`, resolve `quest_id` and **seed** it into the existing `ScenarioState` (clue graph / belief seeding per ADR-053). Slot options referencing creatures/loot resolve against the manifest's `wandering_table` / `loot_table` (the set-piece↔cookbook join point — set-pieces consume curated content, they do not author it). Emit `quest.seed` per component.

- [ ] Test: a seeded quest is present in `ScenarioState` and discoverable through the real scenario surface (proves wiring, not just a struct write).
- [ ] Test: a slot option referencing a creature id absent from the manifest's tables raises loudly (curation/authoring mismatch surfaced — No Silent Fallbacks), span records the failure.
- [ ] Test (ADR-053 risk): if the scenario seeding surface cannot accept a quest seed, the test asserts the loud stop-and-report path — **not** a stubbed success.

## Task 4: Ledger add — every started thread persisted (Plan 5 seam)

**TDD intent:** every started trope and seeded quest produces one open-complication-ledger entry: thread id, kind (trope|quest), origin region, status `open`, the `setpiece.attach` linkage. Written via **Plan 5's ledger primitive** (binds at execution to the real merged API; spec §7.1 contract here). Emit `ledger.add` per entry and one `setpiece.attach` per attached set-piece. The accumulation is emergent and fully legible (spec §7.1) — no hidden counters.

- [ ] Test: N started threads → N ledger entries, each with origin region + `open` status; the count equals the trope+quest spans emitted (cross-check, lie detector).
- [ ] Test: ledger add is part of the materialization transaction — if Plan 7's commit aborts, no orphan ledger rows (binds to Plan 5 transaction; assert no partial state).
- [ ] Test: `AttachReport.as_dict()` is a byte-pinned span contract (mirrors `GenerationReport.as_dict()` / `DepthReport.as_dict()` precedent) — key-set locked so Plan 7's `attach` span and the GM panel stay stable.

## Task 5: Resolution wiring — `ledger.resolve` from the real gameplay path

**TDD intent:** threads shrink **only** on player resolution (spec §7.1: close set-piece / finish/fail quest / kill / seal / flee). Resolution *detection* already lives in the trope engine (TropeState terminal status) and scenario state (quest finish/fail). Subscribe the ledger to those existing resolution events: on resolution, flip the ledger entry to `resolved` and emit `ledger.resolve`. Do not invent a new resolution mechanic — wire the existing ones (reuse-first).

- [ ] Test: driving a trope to a terminal status through the **real** trope path flips its ledger entry to `resolved` and emits `ledger.resolve` (origin region carried).
- [ ] Test: an unresolved thread stays `open` across subsequent expansions (accumulation spine — it does not silently age out; spec §7.1 "no arbitrary clock").
- [ ] **MANDATORY WIRING TEST** (`test_setpiece_attach_wiring.py`, CLAUDE.md): (a) the attach entry point is invoked with the real Plan-7 attach call shape; (b) the resolve subscription fires from the **real** trope/scenario resolution path, not a test-only call. If the existing resolution surface cannot host the subscription, stop and report it as the stated Task-5 dependency risk — do not stub.

## Task 6: Full-suite gate + honest-deferral / as-built docs

- [ ] Full server suite green; ruff + pyright clean on `setpiece_attach.py` and both test files.
- [ ] Module docstring states: this is the runtime owner `setpieces.py` deferred to; the three seams (Plan 5 ledger / ADR-018 trope engine / ADR-053 scenario) and their contracts; the `AttachReport.as_dict()` byte-pinned span contract; the deterministic-roll / save-is-truth / resolution-only-shrinks contracts.
- [ ] **Post-Implementation Corrections** appended (code authoritative): record divergence between the spec §7.1 contract written against and the real merged Plan 5 ledger + ADR-053 scenario APIs.
- [ ] Update spec §10 decomposition item 6 status (the live tracker — not ADR-106's body).

## Self-Review

- [ ] No silent fallback: unknown trope/quest id, missing manifest creature ref, scenario-seed-impossible, ledger-write-fail all raise loudly with an OTEL trail.
- [ ] No stub: if Plan 5 unmerged or the ADR-053 surface can't seed, the plan did not run / stopped-and-reported — not faked.
- [ ] Set-pieces vs cookbook special rooms boundary respected (Task 3 join point only).
- [ ] Determinism: slot rolls pure + seed-stable across restarts; Plan 7 commit freezes them; never recomputed.
- [ ] Threads shrink only on player resolution; no arbitrary clock; accumulation observable in ledger + spans.
- [ ] All five Plan-6 spans present (`setpiece.attach`/`trope.start`/`quest.seed`/`ledger.add`/`ledger.resolve`); the first four emit inside Plan 7's `attach` span, `ledger.resolve` from the gameplay path.

## Execution Handoff

Designed by Architect (oq-2) on 2026-05-16, in parallel with oq-1's in-flight Plan 5. **Executes after Plan 5 merge; does not depend on Plan 7** (Plan 7 depends on this). Next executable plan after Plan 5. Coordinated with oq-1 (Plan 5 + git-sync/merge/verify owner). Do not begin Task 1 before the Task 0 gate passes.

## Post-Implementation Corrections (as-built — CODE IS AUTHORITATIVE)

### Task 2 corrections (2026-05-16, implementer: Claude Opus 4.7)

**Decision A — origin_region & params do NOT go on `TropeState`.**
Spec §6 says "origin region recorded, params carried" on the TropeState append. But
`TropeState` has `model_config = {"extra": "ignore"}` — any extra kwargs passed to it
are silently dropped, which is exactly the silent fallback the GM panel exists to catch.
Therefore:
- `start_trope_components` appends a minimal `TropeState(id=<trope_id>, status="progressing", progress=0.0)` only.
- Origin region and `params` are carried in `TropeStartResult.pending` as
  `list[tuple[TropeComponent, str]]` (component, origin_region_id pairs) for Task 4 to
  write into the ledger (`ComplicationThread.origin_region_id` + payload). Task 2 does
  NOT attempt to stash them on `TropeState`.
- Code authority: `sidequest/dungeon/setpiece_attach.py::TropeStartResult` and
  `start_trope_components`.

**Decision B — `threads_lit_per_expansion` is an explicit required parameter, no config module.**
The plan references `threads_lit_per_expansion` derived from `burst_magnitude` (spec §7.1).
There is no `threads_lit_per_expansion` knob in the dungeon subsystem (only Plan 2's
`region_graph/config.py::connection_burst`, a distinct structural axis). Plan 6's File
Structure forbids creating a config module. Therefore:
- `start_trope_components` takes `threads_lit_per_expansion: int` and `threads_already_lit: int`
  as explicit required keyword arguments — no silent default.
- Plan 7's pipeline owns the value (derived from `burst_magnitude`, playtest-tuned, spec §7.1)
  and threads it across set-pieces.
- The budget is shared across trope AND quest components (Task 3 continues the same counter
  via the returned `TropeStartResult.tropes_started` value accumulated into `threads_already_lit`).
- When components exceed remaining budget, the selection is deterministic from the seed via
  the existing `_slot_seed` / blake2b family (no second seed scheme, no XOR).
- Code authority: `sidequest/dungeon/setpiece_attach.py::start_trope_components` signature.
