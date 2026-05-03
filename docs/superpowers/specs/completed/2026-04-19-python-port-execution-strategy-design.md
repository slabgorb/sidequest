# Python Port Execution Strategy — Design Spec

**Date:** 2026-04-19
**Author:** Keith Avery (Bossmang), Naomi Nagata (Architect, design mode)
**Status:** Approved — ready for implementation plan (writing-plans)
**Related:** [ADR-082](../../adr/082-port-api-rust-to-python.md)

## Purpose

Define the execution strategy for porting `sidequest-api` (Rust) to `sidequest-server` (Python). ADR-082 decided *that* the port happens and *why*; this spec decides *how* — phasing, test discipline, Rust reference usage, the one authorized refactor, cut-over mechanics, sprint integration, and risks.

## 1. Strategy Frame and Anchors

The port targets **playable parity**: one full session on the Python server indistinguishable from one on Rust. The following anchoring decisions are locked (confirmed with Keith 2026-04-19):

- **Feature-freeze model: C** — Rust is feature-frozen, but receives critical playgroup-blocking fixes. This protects the 2026-04-26 Sunday playtest window.
- **Porting target: B (playable parity)** — the playgroup can run a session on Python indistinguishable from a session on Rust. Not full feature parity; not narrowed end-to-end protocol parity.
- **Composition: strict 1:1** across all 15 crates, **with one carve-out**: `sidequest-genre` is authorized to consolidate the `genre-layered-derive` per-type expansions into a single layered-resolution abstraction.
- **Porting order: B (thin vertical slice, widen breadth-first)** — narration end-to-end first, then widen feature bands.

The port proceeds as **eight phases** (0 through 7), a thin vertical slice first, widened breadth-first:

- **Phase 0 — Scaffold.** `sidequest-server` goes from empty to "pyproject + FastAPI skeleton + pytest configured + OTEL wired + 15 empty packages + one smoke test proves the skeleton starts." No game logic. Purely plumbing. DoD: `just server-test` runs and passes; `just server-dev` binds a WebSocket port.
- **Phase 1 — Narration vertical slice.** Connect → `PLAYER_ACTION` → narrator agent → `NARRATION` → session persists. Touches all packages at minimum depth. Includes the **genre consolidation** because the loader is load-bearing for the narrator.
- **Phase 2 — Dice.** Dice module + dice OTEL spans + dice broadcast messages.
- **Phase 3 — Combat.** `combat_models`, `combatant`, `engagement`, `encounter` + combat OTEL.
- **Phase 4 — Chase.** The 6 chase modules (future consolidation candidate, not scope for this port).
- **Phase 5 — Scenario engine.** `belief_state`, `gossip`, `clue_activation`, `accusation`, `faction_agenda`.
- **Phase 6 — Advancement + edges.** Edge/Composure, advancement trees, affinity tiers (Epic 39 material).
- **Phase 7 — CLIs + cleanup.** The 5 CLI packages, final polish, cut-over.

Phases 0 and 1 together are the Sunday-deadline path: if only Phases 0 and 1 are green by 2026-04-26, the playgroup can play a **narration-only session** on Python while dice/combat remain deferred — that is still a meaningful proof point. Everything after Phase 1 is widening, not blocking.

## 2. Test Porting Discipline

Per-module port follows a strict RED→GREEN loop, with the Rust test file as the behavioral contract.

**The mechanical translation rule.** Test porting is a translation, not a rewrite. Every Rust test becomes one pytest function. Every assertion becomes one assertion. Test names are preserved verbatim as Python function names (Rust `snake_case` already matches pytest convention). This is deliberate: it makes per-test cross-tree comparison trivial (`grep` for the same name in both trees) and prevents spec drift via "improvement" of the original tests. **Idiomatic Python rewrites of tests are not allowed during the port.** Post-port cleanup can refactor test style if desired; during the port, fidelity wins.

**Per-module loop.**

1. **Read Rust module + its tests.** Identify imports, public surface, behaviors under test.
2. **Port tests first.** Translate every Rust test file under `sidequest-api/crates/<crate>/tests/` and every `#[cfg(test)] mod tests` to pytest under `sidequest-server/tests/<package>/`. Imports point at not-yet-existent Python symbols. Run: `pytest <path>` must fail with `ImportError` or `AttributeError` — that's the RED signal.
3. **Port production code.** Implement the Python module to satisfy the ported tests. No speculative features — only what the tests demand.
4. **Run: green.** All ported tests pass. No skipped tests. No xfailed tests. If a test genuinely cannot port (e.g., `#[should_panic]` on something that doesn't translate cleanly), it is documented as a deviation in the per-phase deviation log, not silently dropped.
5. **OTEL parity check** (for modules with span emission). Capture Rust OTEL output for a known input. Capture Python OTEL output for the same input. Assert span names, parent/child structure, and attribute keys match. Values may differ where they reflect runtime identity (PIDs, timestamps) but structure is byte-identical.

**What does *not* get ported.** Rust-specific scaffolding — `#[cfg(test)]` blocks that only exist to exercise proc-macro expansion, test-only feature flags, doctests that prove Rust syntax. These are annotated as "scaffolding — Rust-specific" in the source module and skipped. Everything that tests *behavior* ports.

**Coverage comparison as a gate.** At the end of each phase, `cargo test -p <crate> 2>&1 | grep "test result"` gives a Rust test count. `pytest tests/<package> --collect-only -q | tail -1` gives a Python test count. The Python count must be **≥** the Rust count for that crate (≥ because ported tests may split into parametrized variants). A shortfall blocks phase exit.

**Fresh tests are permitted but flagged.** If a Python-idiomatic test adds coverage the Rust suite didn't have (e.g., pydantic validation edge cases that serde didn't exercise), it lives in a `tests/<package>/extensions/` subfolder. This keeps the "what ported" and "what grew" separable for the coverage comparison.

## 3. Rust Reference Usage

The Rust tree has two simultaneous roles during the port: **frozen source spec** (the code you port from) and **live oracle** (a running server you can diff against).

**Frozen source spec — primary role.** For 13 of 15 crates, the Rust code + its tests are the spec. You read them on oq-1 in `sidequest-api/crates/<crate>/`, port module-by-module into `sidequest-server/sidequest/<package>/`, nothing else needed. No live process required.

**Live oracle — narrow role.** For **`sidequest-protocol` only**, we need byte-identical wire output. The Rust server runs on oq-2 under `just api-run`, bound to a non-default port (so it doesn't collide with the Python server). During Phase 1 protocol porting, captured WebSocket frames from scripted client interactions against the Rust server become pytest fixtures. The Python server's output is asserted byte-identical against those fixtures.

Concretely:

```
tests/protocol/fixtures/
├── connect_handshake.json          # captured from Rust
├── player_action_narration.json    # captured from Rust
├── dice_broadcast.json             # captured from Rust (Phase 2)
├── combat_event_chain.json         # captured from Rust (Phase 3)
└── ...
```

Each fixture is a sequence of `{sent: [...], received: [...]}` pairs, captured via a small harness script (`scripts/capture_wire_fixture.py`) that connects to the Rust server, runs a scripted scenario, and writes the exchange to a fixture file. The harness lives in the orchestrator, runs against oq-2's Rust binary, and outputs to `oq-1/sidequest-server/tests/protocol/fixtures/`.

**Why oq-2 for the oracle, not oq-1.** oq-2 is already Keith's playtest workspace (per `feedback_build_verification.md` — oq-2 is the sister checkout for verification). Keeping the Rust oracle there preserves the existing two-clone discipline: edits/ports happen on oq-1, verification runs on oq-2. No new workflow invented.

**Live oracle is read-only.** Once fixtures are captured, they're committed to `sidequest-server` and the Rust server doesn't need to run again for that fixture. The oracle is re-consulted only when a new protocol message type is added to a later phase, at which point we capture its fixture before porting.

**Fixtures are a deviation boundary.** If the Python output cannot match Rust byte-for-byte for a genuine reason (e.g., Python JSON numeric serialization differs from serde in an edge case), that is logged as a protocol deviation in the phase deviation log and the fixture is updated with a comment explaining the deviation. No silent drift.

## 4. Genre Consolidation (the only authorized refactor)

**What's being consolidated.** The Rust tree has an 86-line proc-macro at `sidequest-genre-layered-derive` that implements `#[derive(Layered)]`. Every struct with the derive gets a `LayeredMerge::merge(self, other) -> Self` impl, generated at compile time by walking the struct's named fields and emitting merge code per field according to its `#[layer(merge = "...")]` annotation. Four strategies exist: `replace` (default), `append`, `deep_merge`, `culture_final`. Every layered entity in the genre pack system (archetypes, traits, axes, lore, NPCs, items, tropes — everything that participates in the base → genre → world inheritance chain) carries this derive. Each derive produces a type-specific copy of nearly-identical merge logic. **This is the split-brain.** In Rust it's unavoidable because proc-macros expand per-type. In Python, it's one function.

**The Python abstraction.** A single `LayeredMerge` base class in `sidequest.genre.resolver`:

```python
class LayeredMerge(BaseModel):
    """Mixin for pydantic models participating in base → genre → world layering.

    Field merge behavior is declared via Field metadata:
        name: str = Field(default="", json_schema_extra={"merge": "replace"})
        tags: list[str] = Field(default_factory=list, json_schema_extra={"merge": "append"})
        stats: StatBlock = Field(default_factory=StatBlock, json_schema_extra={"merge": "deep_merge"})
    """

    def merge(self, other: Self) -> Self:
        merged = {}
        for field_name, field_info in self.model_fields.items():
            strategy = (field_info.json_schema_extra or {}).get("merge", "replace")
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            merged[field_name] = _apply_strategy(strategy, self_val, other_val)
        return type(self)(**merged)
```

Every layered type inherits from `LayeredMerge` and declares merge strategies via `Field(json_schema_extra={"merge": "..."})`. No per-type merge code. One implementation, field-declarative config.

**The four strategies port verbatim.** `replace` (default — take `other`'s value), `append` (list extension — `self + other`), `deep_merge` (recursive `LayeredMerge.merge` if the field is itself `LayeredMerge`), `culture_final` (genre-specific strategy — port the Rust semantics exactly, whatever they are; read `resolver/load.rs` for the Rust behavior).

**Correctness gate.** Tests from every type that currently carries `#[derive(Layered)]` port to pytest. Every one of them must pass against `LayeredMerge`. In the Rust tree each type's derive has an implicit compile-time test — the merge function is synthesized and called; if a field annotation is wrong, compilation fails. In the Python tree, we replace the compile-time check with a runtime validation test per type: a `test_<TypeName>_layered_merge_fields_declared()` that asserts every field of the type has a declared merge strategy (no silent defaults in production). This is the wiring test per CLAUDE.md: "Every test suite needs a wiring test."

**Deviation logging.** Section 4's consolidation is pre-authorized by this spec, so it does not need a per-finding deviation. But the *scope* of the consolidation is bounded: **only** the `LayeredMerge` derive expansion. If during Phase 1 we discover any other similar-looking duplication inside `sidequest-genre` (e.g., YAML loader patterns, validation patterns, resolver caching patterns), those are **not** in scope for this authorization. Surface them, log them in this spec as "Candidate consolidation, deferred," and leave the Rust-like 1:1 in the port. Post-port follow-up work can address them; the port stays focused.

**Fallback clause.** If `culture_final` or any other merge strategy has subtle Rust semantics that don't translate cleanly to the single-function `LayeredMerge`, fall back to 1:1 per-type merge in Python. Lose the LOC win, keep correctness.

**LOC estimate (for sanity, not commitment).** The proc-macro itself is 86 lines but its *expansions* — the per-type merge impls scattered through `sidequest-genre` — are where the duplication lives. Conservative estimate: 5-10 layered types × ~30 lines of synthesized merge code per type ≈ 150-300 LOC replaced by ~60 lines of Python `LayeredMerge`. Modest but real, and the bigger win is declarative: merge strategy lives next to the field it affects, not in a proc-macro annotation.

## 5. Cut-over Mechanics

The cut-over is a discrete, reversible swap. It is not a merge; it is a set of coordinated changes that redirect tooling and workflow from `sidequest-api` to `sidequest-server`.

**Trigger.** Cut-over happens when **Phase 1 is green and at least one full playtest on Python feels like Rust** — this is playable parity. Later phases can land post-cut-over as ordinary feature work; they don't block the swap. In practice, cut-over is likely between Phase 3 (combat) and Phase 5 (scenario) depending on the playgroup's next-session needs.

**Pre-cut-over checklist.**

1. Every Phase 1 ported test is green on the Python server.
2. OTEL span parity verified for Phase 1 modules (spans match the Rust catalog for narration, session, genre load, character fetch).
3. A full playtest has been run against the Python server on a branch, with the playgroup or a solo dry-run, and felt indistinguishable from Rust.
4. The Rust `develop` tip is tagged `rust-final-<YYYYMMDD>` for long-term reference.

**The cut-over PR** (single PR on the orchestrator, reviewed by Keith as architect):

- `.pennyfarthing/repos.yaml` — `api:` stanza renamed to `rust:` with note "archived reference — see ADR-082," `server:` becomes the primary API repo.
- `justfile` — top-level recipes repointed: `api-run`, `api-test`, `api-build`, `api-lint`, `api-check` all become aliases or are renamed to `server-*` equivalents. Old recipes kept as `rust-*` aliases for reference during the stabilization window.
- `.pennyfarthing/config.local.yaml` — no change needed; workflow definitions are language-agnostic.
- `CLAUDE.md` (root) — "sidequest-api (Rust)" descriptor updated to "sidequest-server (Python)," with a pointer to ADR-082. The `Rust vs Python Split` principle is rewritten to reflect the new topology: Python backend + Python daemon + TypeScript UI.
- `scripts/` — any script that shells to `cargo` or to `sidequest-api/` is updated to hit `sidequest-server/` via `uv run` or `python -m`.
- `.claude/hooks/cargo-env-inject.sh` — retained but noted in its header as "no longer hot-path; kept for the stabilization window."
- `.envrc` — `CARGO_HOME` and `RUSTC_WRAPPER` overrides retained through the stabilization window, removed after.

**What happens to `sidequest-api`.** The repo is **not deleted**. It is:

1. Tagged `rust-final-<YYYYMMDD>` at its current `develop` tip.
2. Renamed on GitHub from `sidequest-api` to `sidequest-api-rust` (reference tag in the name prevents confusion).
3. Marked as archived in its GitHub repo settings — no new issues, no new PRs.
4. Its local clones (`oq-1/sidequest-api/`, `oq-2/sidequest-api/`) remain checked out in-place for the stabilization window; after 30 days without reference, they can be removed from the gitignored inline subrepo list.
5. README on the archived repo gets a header: *"Archived — superseded by [sidequest-server](https://github.com/slabgorb/sidequest-server) on YYYY-MM-DD per [ADR-082](...). Kept as read-only reference."*

**Stabilization window (30 days post-cut-over).** During this window:

- Cross-tree diffs are sanctioned: if a Python-port bug is suspected, run the frozen Rust binary and compare. The oracle stays live.
- Any Python-only phase-5-or-6 work that lands during stabilization is reviewed with extra care because we no longer have Rust as a fresh comparison point for it.
- Retired recipes (`rust-*` aliases) stay in the justfile.

**Rollback.** If within 72 hours of cut-over we hit a show-stopper in the Python tree that can't be fixed within a playtest window, rollback is:

1. `git revert` the cut-over PR on the orchestrator.
2. Tooling points back at `sidequest-api`.
3. The Python tree continues development on a branch; a second cut-over attempt happens when the blocker is fixed.

This is a single-atomic rollback path — no data migrations, no state that needs to be reconciled between trees because **content and UI never changed**. Both servers read the same `sidequest-content` genre packs and speak the same protocol to the same `sidequest-ui` — the swap is tooling, not data.

**What triggers the end of the stabilization window.** Either (a) 30 days pass with no Rust reference consultations, or (b) Phase 7 (CLIs + cleanup) is complete and the port is considered done. At that point, the `rust-*` aliases are removed, `.envrc` drops the cargo overrides, the cargo-env-inject hook is deleted, and `sidequest-api-rust` becomes a pure archive read-only reference.

## 6. Sprint and Story Workflow Integration

The port is structured as **one epic with phased stories**, slotted into the existing pennyfarthing sprint/story flow. This keeps the port visible in `pf sprint status`, lets each per-module port use the standard review/finish discipline, and makes cut-over a discrete, trackable story rather than a surprise commit.

**Epic structure.**

- **Epic 41 — Python port (sidequest-api → sidequest-server, ADR-082).** Umbrella epic. Parent for all port stories. Epic context written at `sprint/context/context-epic-41.md` with ADR-082 as its primary reference. Remains open until Phase 7 completes and the stabilization window closes.

**Story granularity.** One story per package-port per phase. A package touched in multiple phases gets multiple stories (e.g., `sidequest.game` is touched in Phases 1, 2, 3, 4, 5, 6 — six stories, each porting the subset of modules that feature band needs).

**Phase 1 story breakdown** (the Sunday-deadline-relevant set):

| Story | Scope | Workflow | Repo |
|---|---|---|---|
| 41-0 | Scaffold `sidequest-server` (Phase 0: pyproject, FastAPI skeleton, pytest+OTEL wired, 15 empty packages, one smoke test). | trivial | sidequest-server |
| 41-1 | Port `sidequest.protocol` (pydantic discriminated unions, wire-fixture tests captured from oq-2 Rust oracle). | tdd | sidequest-server |
| 41-2 | Port `sidequest.genre` with LayeredMerge consolidation (the authorized refactor). | tdd | sidequest-server |
| 41-3 | Port `sidequest.game` minimal slice (Character, Session, GameState — only what narrator needs). | tdd | sidequest-server |
| 41-4 | Port `sidequest.telemetry` (OTEL span catalog for Phase 1 modules). | tdd | sidequest-server |
| 41-5 | Port `sidequest.agents.narrator` (Claude subprocess orchestration, prompt builder). | tdd | sidequest-server |
| 41-6 | Port `sidequest.server` (FastAPI app, WebSocket dispatch, session handler) — Phase 1 endpoints only. | tdd | sidequest-server |
| 41-7 | Phase 1 integration playtest + cut-over readiness assessment. | trivial | orchestrator |

Each numbered story follows the existing Dev / TEA / Reviewer / SM flow. `tdd` workflow is chosen because the Rust tests are the RED (TEA ports them into pytest; Dev ports the production code to GREEN). `trivial` workflow is chosen for 41-0 (scaffolding — no behavioral tests yet) and 41-7 (integration playtest — a verification report, not code).

**Phases 2–6 story template.** Each subsequent phase gets its own story block parallel to Phase 1's, with per-phase story numbering (41-8 through 41-N). Phases 2–4 (dice, combat, chase) are mostly `sidequest.game` expansions plus dispatch wiring; story counts per phase are smaller than Phase 1 because the foundational packages already exist. Rough estimate: Phase 2 ≈ 3 stories, Phase 3 ≈ 4 stories, Phase 4 ≈ 3 stories, Phase 5 ≈ 4 stories, Phase 6 ≈ 3 stories, Phase 7 ≈ 5 stories (one per CLI + final cleanup). Total epic: ~28–30 stories.

**Cut-over as a story.** Story 41-CO (named explicitly, not numbered in sequence to emphasize its gate role) is the single atomic cut-over PR on the orchestrator, per Section 5. Workflow: `trivial`. Gated on Phase 1 green + one successful smoke playtest. May be filed between any two widening phases; it's not locked to a specific phase boundary.

**Critical-fix protocol during the port.** When the playgroup hits a Rust blocker during the feature-freeze window, the fix is a normal story on `sidequest-api` with a distinguishing marker:

- Branch: `fix/rust-critical-<slug>` on `sidequest-api`.
- Story: prefixed `41-RC-<N>` (Rust Critical) and tracked under Epic 41 so it's visible in port context.
- Scope: the narrowest possible fix. No refactors. No new features. No OTEL additions unless the bug is an OTEL bug.
- After merge: the fix is also ported forward to the Python tree (if applicable to already-ported Phase 1 modules). The forward-port is tracked as a follow-up story `41-FP-<N>` under Epic 41.
- Every Rust Critical story increases port risk by widening the frozen-Rust spec. Limit: **three Rust Criticals total** across the port. If a fourth is needed, we stop and reassess — either cut-over faster, or accept that the port is going to slip past Sunday.

**Why three.** Arbitrary but bounded. One or two is noise; four or more means Rust is still actively being developed and the feature-freeze has become theater. The limit is a forcing function for decisiveness, not a strict engineering budget.

**Sprint slot.** Epic 41 lands in Sprint 2 (the current sprint, per context: "Sprint 2: Multiplayer Works For Real"). The port supersedes whatever non-critical Sprint 2 work remains; any 39-series advancement work or 38-series sealed-letter work that hasn't started is deferred until post-port. Work in flight (Story 39-5, currently IN_PROGRESS) is the one thing that needs a decision: finish it in Rust before freezing, or defer it and port its final state from the green Rust tree. **Recommendation: finish 39-5 in Rust** — it's already in green phase, completing it is faster than freezing it half-done. After 39-5 finish, Rust enters feature-freeze and Epic 41 begins.

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Phase 1 slips past 2026-04-26 Sunday | Medium | Low — playtest happens on frozen Rust; port continues | Feature-freeze-with-critical-fixes (Anchor C) was chosen exactly for this. No decision depends on Sunday readiness. |
| Genre consolidation turns out harder than expected (e.g., `culture_final` strategy has subtle Rust semantics that don't translate cleanly) | Medium | Medium | Fall back to 1:1 per-type merge in Python (lose the LOC win, keep correctness). Story 41-2 has an explicit fallback clause in its context. |
| OTEL parity impossible to verify byte-precisely (Python OTEL SDK emits attributes in different order, tracer IDs differ, etc.) | High | Low | Parity defined structurally, not bytewise: span names + parent/child relationships + attribute *keys* must match. Attribute *values* must match where they reflect domain state; runtime-identity values (PIDs, trace IDs, timestamps) may differ. |
| Python hot-path perf regression vs. Rust (dice rolls, state transitions under load) | Medium | Low | Session throughput is dominated by Claude subprocess latency (~1-5s per call); Python state-machine overhead is <10ms per turn. Not on the critical path. Revisit in stabilization window if playtest surfaces actual latency complaints. |
| Feature-freeze violation creep — more than 3 Rust Criticals land during the port | Medium | High | Budget limit in Section 6 is the forcing function. On the 4th Critical, Epic 41 pauses and Keith decides: cut over with Phase N, or accept slip. No "just one more." |
| UI payload shape regression (UI expects a field Rust provided but Python omits) | Medium | Medium | Protocol snapshot tests against oq-2 Rust oracle (Section 3) catch this at the pydantic level. UI smoke test in Phase 1 story 41-7 catches any that snuck through. |
| Claude subprocess behavior differs between `tokio::process::Command` and `asyncio.create_subprocess_exec` (env inheritance, stdin/stdout buffering, shutdown signals) | Low | High | Port the subprocess invocation exactly — same args, same env, same stdin/stdout/stderr wiring. The narrator agent test in Phase 1 exercises the full subprocess path; any divergence fails there. |
| LOC savings from genre consolidation turn out smaller than estimated (~150–300 LOC claimed in Section 4) | High | Zero | Not a real risk. The consolidation is for code clarity and declarative merge strategies, not LOC golf. LOC estimate is for sanity only. |
| `sidequest-ui` needs changes after all (payload shape tightened during Rust work that UI now expects) | Medium | Low | Story 41-7 explicitly tests against real UI. Any required UI patches are filed as follow-on stories under Epic 41 with the `41-UI-<N>` marker. |
| Stabilization window finds a bug that would have been caught by deeper Phase 5/6 porting | Medium | Medium | Acceptable. Playable parity is the bar, and "playable" is checked at cut-over. Stabilization is for drift, not for re-proving the port. |
| `sidequest-daemon` client contract changes force daemon-side changes (violating "daemon untouched") | Low | High | The daemon is out of scope. If the daemon client reveals a protocol mismatch that requires daemon changes, Epic 41 pauses and a separate daemon-scope decision is made — likely defer the affected Phase until post-port. |

## 8. Non-Goals

Explicit boundaries, for the record:

- **Not porting with perfect idiomatic Python.** Fidelity to the Rust behavior spec wins every tie over Python prettiness during the port. Post-port cleanup can refactor for idiom.
- **Not unifying packages beyond the genre carve-out.** Every other "looks similar" finding is a **Candidate consolidation, deferred** entry in this spec (see Section 9), not a port-time action.
- **Not changing the content schemas.** YAML shapes are frozen; if a schema issue is found during the port, it's a content repo issue handled separately.
- **Not migrating save files.** Save file format is defined by the content + protocol; as long as both are stable across the port, existing saves from Rust should load on Python. One of 41-7's smoke tests is "load a real save from the `~/.sidequest/saves/` directory." If it breaks, that's a port bug, not a migration task.
- **Not rebuilding the OTEL watcher infrastructure.** The GM panel and BikeRack stay as-is; the Python server emits spans at the same names and the panel doesn't know or care that the source language changed.

## 9. Candidate Consolidations, Deferred

Consolidations that were *not* authorized by this spec but may be addressed in post-port follow-up work. Recorded here so they're not lost:

- **The 6 `chase_*` modules** in `sidequest.game` (chase, chase_attrition, chase_cinematography, chase_pacing, chase_rig, chase_terrain, chase_depth). Likely shares pattern structure worth abstracting. Defer to post-port.
- **`sidequest-fixture` + `sidequest-test-support`** — both test-adjacent. Possibly collapse to one `sidequest.test_support` package.
- **Scenario engine modules** (`belief_state`, `gossip`, `clue_activation`, `accusation`, `faction_agenda`) were a single `scenario/` package in sq-2 archive. Rust split them across `game/`. Post-port, consider reuniting them under `sidequest.scenario`.
- Any *new* candidates surfaced during the port (e.g., YAML loader patterns inside `sidequest-genre` outside the LayeredMerge scope) are appended here during execution.

## 10. Validation

This spec is the authoritative source for Epic 41. Its decisions override any conflicting guidance from lower-authority sources during the port. Changes to this spec during execution are logged as deviations in the affected phase's story context and require explicit Keith approval.

Next step: writing-plans skill produces an implementation plan for Phase 0 + Phase 1 (Stories 41-0 through 41-7), the Sunday-deadline-relevant block.
