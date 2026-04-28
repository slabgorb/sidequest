---
id: 82
title: "Port `sidequest-api` from Rust back to Python"
status: accepted
date: 2026-04-19
deciders: [Keith Avery (Bossmang), Naomi Nagata (Architect, design mode)]
supersedes: [19]
superseded-by: null
related: [85]
tags: [project-lifecycle]
implementation-status: live
implementation-pointer: null
---

# ADR-082: Port `sidequest-api` from Rust back to Python

> Supersedes the implicit "Rust is the backend" decision baked in when the
> Python-to-Rust port landed (~2026-03-30). Cutover completed 2026-04-23.

> **Cutover note (2026-04-23):** The Rust tree (`sidequest-api/`) was removed
> from the working tree and archived read-only at
> <https://github.com/slabgorb/sidequest-api>. The Python tree (`sidequest-server/`)
> is the live backend. Per ADR-085, sprint-tracker reconciliation is the
> responsibility of Architect/PM for the remainder of the cutover-plus-one-sprint
> audit window.

## Context

The backend was ported from Python (`~/ArchivedProjects/sq-2`) to Rust (`sidequest-api`) around 2026-03-30, primarily as a learning exercise — Keith's day job uses Rust and the port doubled as a way to build fluency in a real codebase. That goal was achieved.

Rust has since proven to be the wrong tool for *this specific project* for three independent reasons:

1. **Mac security posture is non-negotiable.** Keith runs a hardened Mac configuration. The workaround most Rust developers use to get reasonable compile performance on macOS (granting Terminal full Developer Tools entitlement / disabling relevant TCC protections) would broaden the attack surface in ways that are unacceptable for a personal machine that also handles sensitive work. This is not a matter of preference — the floor is fixed, and Rust's compile loop pays a visible, recurring tax against it.

2. **Compile-before-run is the wrong model for this project.** Rust's "must compile to run any test" is valuable in enterprise codebases where correctness is life-or-death. SideQuest is a single-author creative project where *iteration speed is the product*. The narrator is only good if it can be tuned dozens of times an hour; game systems are only tunable if a shape change doesn't cost a multi-minute rebuild.

3. **Rust does not lend itself to TDD the way Python does.** The per-test cycle time, the type-surgery required when a shape evolves, and the friction of mocking/stubbing at boundaries all chafe against the RED→GREEN cadence the project uses. TDD in Python is frictionless; in Rust it is tolerable but expensive.

The learning dividend from the Rust port is already banked. The project has accumulated **1,829 commits across 5 repos in ~20 days** since the port — every one of those commits paid the compile-loop tax. The cost/benefit has inverted.

### Documented Infrastructure Hostility (supporting evidence)

The case against Rust is not theoretical. The project's own auto-memory (`~/.claude/projects/.../memory/`) is a dated trail of workarounds written to survive cargo's concurrency model fighting the developer's workflow. Each of the following is a load-bearing workaround — removing any of them reintroduces a concrete failure mode that has already been observed.

- **`feedback_cargo_env_contract.md` (2026-04-18) — recurring 26-minute cold rebuilds.** Cargo's `target/` incremental cache hashes environment variables into its fingerprint. Two entry points (`.envrc` for tmux/terminals, `.claude/hooks/cargo-env-inject.sh` for Claude's Bash tool) must export identical `CARGO_HOME` and `RUSTC_WRAPPER`, or every switch between entry points invalidates the cache and forces a cold build. The contract exists because cargo punishes heterogeneous invocation paths — which is exactly what a multi-agent development workflow produces.

- **Cross-clone cargo lock contention (upstream `rust-lang/cargo#9021`).** The two-clone workflow (`oq-1` and `oq-2`, required to keep Keith unblocked while long-running tasks execute in the other clone) hit the global advisory lock on `~/.cargo/.package-cache`. Fix: per-clone `CARGO_HOME` override so the two clones stop fighting each other. This is an upstream cargo bug with no resolution.

- **sccache daemon deadlock (rustc hangs indefinitely).** Cross-clone sccache daemon contention causes rustc to deadlock mid-compile. Mitigation: `RUSTC_WRAPPER=""` exported globally in the orchestrator justfile, in both `.envrc`s, and in the cargo-env hook. The memory notes that this mitigation has been reverted multiple times by agents who thought it was obsolete; each reversion reproduced the deadlock. **The phrase "hey is cargo deadlocked?" is literally documented behavior with a named fix**, not a one-off user complaint.

- **`feedback_no_duplicate_test_runs.md` — mutually-exclusive cargo invocations.** Explicit rule: never run `cargo test`/`cargo build` via Bash while the `testing-runner` subagent is running the same repo. Concurrent cargo invocations contend on the same lock. This forecloses the parallelization that any other toolchain would welcome.

- **`feedback_test_efficiency.md` — test suite is 90–300+ seconds.** Rule had to be written: do not re-run the suite; trust the build as the gate. This directly undermines TDD discipline — if the loop cost is 5 minutes, developers stop closing the loop.

- **`feedback_build_verification.md` — two-clone workflow required explicit codification** of which clone does edits vs. verification, because the workflow Keith uses to stay unblocked during Rust builds was itself causing branches to land in the wrong place. The workaround-for-a-workaround problem.

- **`feedback_rust_python_split.md` (24 days old, written at port time).** The *original* guideline was already carving Rust out of the LLM-interfacing surface: "If it needs to operate LLMs, use Python." Even on day one of the port, we were conceding that Rust was not the universal answer.

**What this trail reveals structurally:** Keith's infrastructure is not *unusually* hostile to cargo — cargo is unusually hostile to the kind of infrastructure Keith runs. A two-clone workflow, parallel agent invocations, hardened macOS, and 20× pre-AI velocity are all things a modern developer workflow treats as normal. Cargo treats them as concurrency violations, and the memory trail is the receipt.

**None of these problems exist in Python.** Pytest does not care if two clones run at once. Python imports do not hash env into an incremental cache. There is no `pytest-wrapper` daemon to deadlock against itself. The ruff/pyright toolchain is designed for parallel invocation from the ground up. The port is not primarily a language change — it is the removal of an entire class of infrastructure tax.

## Decision

**Port `sidequest-api` back to Python.** Retain the design work from the Rust tree as the specification for the port. Treat the archived Python project (`sq-2`) as a layout reference, not a destination.

### Scope

| Repo | Action |
|------|--------|
| `sidequest-api` | **Becomes read-only reference** during the port. Remains present, untouched, as the canonical spec until the Python tree goes green and the cut-over happens. |
| `sidequest-server` | **New subrepo added inline** next to the existing four. Python port target. Created 2026-04-19 at `https://github.com/slabgorb/sidequest-server`, gitflow with `develop` as default. |
| `sidequest-ui` | **Probably untouched.** Risk is bounded to payload-shape compatibility (see Protocol section). |
| `sidequest-content` | **Untouched.** YAML shapes are language-agnostic. |
| `sidequest-daemon` | **Untouched.** Out of scope — daemon serves uses beyond SideQuest. |
| `orc-quest` (this repo) | **Tooling updates only.** justfile targets, `pf` integration, scripts, `repos.yaml` updated with the new inline repo. |

## What Survives the Port (Design Artifacts)

The expensive thinking of the last three weeks is not in the Rust code — it is in the *shape* of the Rust code. All of the following carry forward:

- **Crate boundaries → package boundaries.** The 15-crate decomposition (`protocol`, `genre`, `game`, `agents`, `server`, `telemetry`, `daemon-client`, CLIs) maps cleanly onto Python packages under `sidequest/`.
- **Typed protocol.** The discriminated-union message taxonomy in `sidequest-protocol` ports to pydantic v2 discriminated unions (`Annotated[Union[...], Field(discriminator='type')]`). This is a strict upgrade over sq-2's `payload: dict[str, Any]` — we retain Rust's wire-type rigor in Python form.
- **OTEL span catalog.** The span names, field conventions, and watcher emissions in `sidequest-telemetry` port verbatim to `opentelemetry-api`. The GM panel keeps working without UI changes.
- **Genre pack loader contract + layered inheritance.** YAML shapes are unchanged. The `sidequest-genre-layered-derive` proc-macro becomes a Python base class with `__init_subclass__` or a decorator — simpler in the target language.
- **Game subsystem designs.** `barrier`, `beat_filter`, `chase_depth`, `affinity`, `belief_state`, `engagement`, `faction_agenda`, `conlang`, `dice`, advancement trees, Edge/Composure — all of it carries as module designs, not Rust-specific constructs.
- **Tests as executable spec.** Every passing Rust test is a behavioral contract. The tests port alongside the code, and their assertions are the spec for each module.
- **Claude-as-subprocess.** Already a subprocess contract, not a library binding — trivial to re-home.
- **CLI tools.** Five CLI crates (`promptpreview`, `encountergen`, `loadoutgen`, `namegen`, `validate`) become Python entry points in `pyproject.toml`.

## What Changes (Implementation)

- **Language:** Rust → Python 3.12+.
- **Runtime:** **FastAPI + uvicorn** for HTTP/WebSocket. Chosen over aiohttp (sq-2's pattern) for typed-handler ergonomics, native pydantic integration, and WebSocket support that slots cleanly into the existing message dispatch shape.
- **Serialization:** serde → pydantic v2. Discriminator field: `type`.
- **Test runner:** `cargo test` → `pytest` + `pytest-asyncio`. RED→GREEN cycle time drops from minutes to seconds.
- **Observability:** `tracing`/`opentelemetry-rust` → `opentelemetry-api` + `opentelemetry-sdk`. Same span names.
- **Build system:** `Cargo.toml` workspace → `pyproject.toml` (hatchling, per sq-2 convention). No build step; `uv run` or direct import.
- **CI/tooling:** `cargo fmt`/`clippy` → `ruff format`/`ruff check`. `just api-check` recipe rewrites accordingly.

## Port Strategy

**Approach:** Translate the Rust tree **1:1 into Python packages**, using tests as the acceptance spec for each port.

The 15-crate composition is preserved as 15 packages under `sidequest/`. No consolidation, no renaming, no "while we're in here" refactors. This rule is load-bearing for the port itself: a 1:1 structural mapping means any feature, span, test, or behavior can be compared across the two trees by path, not by archaeology. If the Rust tree has `crates/sidequest-game/src/chase_depth.rs`, the Python tree has `sidequest/game/chase_depth.py`. Deviations from the 1:1 mapping during the port are *deviations* and must be logged as such. Post-port refactoring is a separate decision; during the port, structural fidelity wins every tie.

1. **Scaffold.** Bring up `sidequest-api/` as a Python project using sq-2's pyproject + package layout. Commit skeleton with empty modules matching the Rust crate-to-package mapping.
2. **Protocol first.** Port `sidequest-protocol` to `sidequest.protocol` with pydantic discriminated unions. Verify JSON round-trips match the Rust wire format against a captured sample (protocol snapshot test).
3. **Genre loader second.** Port `sidequest-genre` to `sidequest.genre` with layered inheritance via base class. Run loader against live genre packs; output must structurally match Rust's.
4. **Game crate third.** Port `sidequest-game` module-by-module. Each module's Rust tests port to pytest alongside; the module is "done" when its tests pass in Python.
5. **Agents / server / telemetry** in parallel once the core is green. Agents is mostly subprocess orchestration and prompt building — translates cleanly. Server is FastAPI over the ported protocol. Telemetry is a direct span-catalog translation.
6. **CLIs last.** Small, parallelizable, each its own entry point.
7. **UI compatibility pass.** Boot the Python server against the existing TypeScript UI. Triage any payload-shape mismatches. Most should be none.

Per-module port is a Dev task; this ADR does not prescribe Dev's ordering beyond the dependency graph above.

## Protocol Compatibility (UI Risk Section)

Message *types* (`PLAYER_ACTION`, `NARRATION`, `COMBAT_EVENT`, `DICE_*`, `CHARACTER_SHEET`, etc.) are shared between sq-2, the current Rust tree, and the UI — no type-level churn expected. The risk is **payload shape**: fields the UI now depends on that were tightened during the Rust port beyond what sq-2 had. Mitigation: pydantic models mirror the Rust structs field-for-field, so the JSON on the wire is byte-identical. UI only breaks if we skip that mirror step.

## Consequences

### Positive
- Iteration speed restored. RED→GREEN loop measured in seconds, not minutes.
- TDD discipline becomes pleasant again, which means it actually happens.
- Narrator/prompt tuning gets fast again — critical for the Keith-as-player goal.
- Security posture preserved. No TCC/SIP concessions.
- Daemon split becomes more natural (both sides Python, shared pydantic models possible if desired later).
- One less language in the stack (Python backend + Python daemon + TS UI, down from Rust + Python + TS).
- Tests gain a free 10×+ cycle-time improvement, which encourages more of them.

### Negative
- Throw-away work: 1,829 commits of Rust translated into Python. The *design* carries; the *typing-it-in* does not. At present velocity, this is calendar-short but not trivial.
- Lose Rust's compile-time guarantees. Pydantic catches most shape errors at boundaries; mypy catches more; but there is no equivalent to the borrow checker. For this project, that trade is acceptable — game logic is single-threaded per session, async is cooperative, and the cost of a runtime panic is a dropped WebSocket, not a corrupted database.
- Slightly slower hot-path performance (dice rolls, state updates). In practice, dominated by Claude-subprocess latency anyway.
- Rewriting CI, `just` recipes, and `pf` integration for Python toolchain.

### Neutral
- UI and content repos untouched (or nearly so).
- OTEL/GM-panel story is preserved.
- Typed-protocol story is preserved (pydantic instead of serde).

## Alternatives Considered

- **Stay on Rust, work around compile-time pain.** Rejected. Security floor is fixed; compile loop cannot be mitigated without lowering the floor.
- **Port to TypeScript/Node (or Bun).** Rejected. Keith does not want JavaScript on the backend. Preference is firm.
- **Port to Go.** Not seriously considered. Compile loop is fast, types are fine, but no prior art in this codebase and no advantage over Python for this problem's shape. Python is the default because the domain fits it and the original code exists as a reference.
- **Resurrect sq-2 directly and carry forward.** Rejected. sq-2 is missing the majority of the work (1,829 commits' worth of new systems); it's a layout reference, not a destination.

## Resolved Design Decisions (confirmed with Keith 2026-04-19)

- **Server runtime:** FastAPI + uvicorn. Locked.
- **Composition:** 1:1 crate-to-package mapping, no consolidation during the port. Locked.
- **Daemon:** Left untouched. `sidequest-daemon` serves uses beyond SideQuest and is out of scope for this ADR. No protocol changes, no in-process collapse, no refactor.
- **Cut-over strategy:** A new inline subrepo is added alongside the existing four (`sidequest-api`, `sidequest-ui`, `sidequest-content`, `sidequest-daemon`). The Python port is developed in parallel with the running Rust tree. The Rust tree remains a read-only reference until the Python tree goes green; swap when proven.
