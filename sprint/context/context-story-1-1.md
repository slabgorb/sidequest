---
parent: context-epic-1.md
---

# Story 1-1: Workspace Setup — Cargo.toml, 5 Crates, Shared Deps

## Business Context

This is the foundation story. Nothing else can start until the workspace compiles with
all 5 crates declared and shared dependencies available. The current state is a single
`Cargo.toml` with an invalid edition (`2024`, should be `2021`), no `[workspace]` section,
no dependencies, and only a placeholder `src/main.rs`.

## Technical Guardrails

- **Edition:** Use `2021` (not `2024` which doesn't exist)
- **Workspace root** `Cargo.toml` declares `[workspace]` with members pointing to all 5 crates
- **Shared dependencies** use `[workspace.dependencies]` so versions are declared once
- **Crate creation** via `cargo new --lib` for protocol/genre/game/agents, `cargo new` (binary) for server
- **Dependencies** per `docs/tech-stack.md`: tokio, axum, serde, serde_json, serde_yaml, thiserror, tracing, tracing-subscriber, clap, uuid, chrono, rusqlite, futures, tower-http
- **Tooling:** rustfmt.toml (`group_imports = "StdExternalCrate"`), clippy config (`-D warnings`, `unsafe_code = forbid`), rust-toolchain.toml (stable)
- **Each crate** should have a minimal `lib.rs` (or `main.rs` for server) that compiles

## Scope Boundaries

**In scope:**
- Fix Cargo.toml: edition, workspace, dependencies
- Create 5 crate directories with minimal source files
- Add rustfmt.toml, clippy config, rust-toolchain.toml
- Verify `cargo build`, `cargo test`, `cargo clippy`, `cargo fmt --check` all pass

**Out of scope:**
- Any actual game logic, types, or handlers — those are stories 1-2 through 1-5
- CI/CD pipeline
- Git hooks

## AC Context

| AC | Detail |
|----|--------|
| `cargo build` passes | All 5 crates compile with no errors |
| `cargo test` passes | Default tests pass (may be empty) |
| `cargo clippy` clean | No warnings with `-D warnings` |
| `cargo fmt --check` | All code formatted per rustfmt.toml |
| Dependencies declared | All crates from tech-stack.md present in workspace deps |
