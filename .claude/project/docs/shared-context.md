# SideQuest — Shared Context

## Project

- **Name:** SideQuest (Rust Rewrite)
- **Sprint Status:** `sprint/current-sprint.yaml`
- **Active Work:** `.session/{story-id}-session.md`
- **Agent Framework:** Pennyfarthing (pf CLI)

## Tech Stack

| Component | Language | Framework | Notes |
|-----------|----------|-----------|-------|
| API | Rust (2024 edition) | axum + tokio | WebSocket + REST, serde serialization |
| UI | TypeScript | React 19 + Vite | Tailwind CSS + shadcn/ui |
| Daemon | Python | Flux/SDXL, Kokoro, Piper | Image gen, TTS, audio mixing |
| Orchestrator | — | Pennyfarthing | Sprint tracking, genre packs, shared config |

## Repo Structure

```
orc-quest/                    # Orchestrator (this repo)
├── .claude/                  # Claude Code configuration
├── .pennyfarthing/           # Pennyfarthing framework
├── sprint/                   # Sprint tracking
├── .session/                 # Active work sessions
├── genre_packs/              # YAML genre data (shared across repos)
├── docs/                     # Architecture and design docs
├── repos.yaml                # Multi-repo topology
├── justfile                  # Cross-repo task runner
├── sidequest-api/            # API subrepo (gitignored, clone separately)
│   ├── Cargo.toml
│   ├── src/
│   └── tests/
├── sidequest-ui/             # UI subrepo (gitignored, clone separately)
│   ├── package.json
│   ├── src/
│   └── public/
└── sidequest-daemon/         # Daemon subrepo (gitignored, clone separately)
    ├── pyproject.toml
    ├── renderer/
    ├── tts/
    └── audio/
```

## Git Branch Strategy

- **Orchestrator:** trunk-based on `main`
- **API & UI:** gitflow — feature branches from `develop`
- **Branch naming:** `feat/{story}-{description}` or `fix/{issue}-{description}`
- **PRs target:** individual subrepos, not the orchestrator

## Testing Commands

### API (Rust)
```bash
cd sidequest-api && cargo test
# Or from orchestrator:
just api-test
```

### UI (React)
```bash
cd sidequest-ui && npx vitest run
# Or from orchestrator:
just ui-test
```

### All
```bash
just check-all
```

## Building

### API
```bash
just api-build          # Debug build
just api-release        # Release build
```

### UI
```bash
just ui-build           # Production build
just ui-dev             # Dev server
```

<critical>
## Velocity & Quality Standards

First commit: 2026-03-25. In 3.5 days: 528 commits, 125,163 LOC, 672/726 story points, 85 stories, 12 epics. A 5-crate Rust game engine, React client, Python media daemon, 7 genre packs, 30 ADRs, and a full WebSocket protocol.

Do not underestimate what we can do. There is no fix too ambitious, no refactor too large, no "we should do this later." If the right fix takes 20 minutes and the hack takes 5, do the right fix — because the hack will cost 2-3x MORE when we come back to it. The debugging cost of figuring out whether something is a stub or the real thing, whether a regex hack is the intended behavior or a placeholder, whether `if false {` was temporary or permanent — that confusion tax dwarfs the original implementation time by an order of magnitude.
</critical>

<critical>
## Rules — Non-Negotiable

- No stubs, no hacks, no "we'll fix it later" shortcuts.
- No skipping tests to save time.
- No half-wired features — connect the full pipeline or don't start.
- If something needs 5 connections, make 5 connections. Don't ship 3 and call it done.
- Never say "the right fix is X" and then do Y. Do X.
- Never downgrade to a "quick fix" because you think the context is "just a playtest." Every playtest is production tomorrow. Fix it right.
</critical>

<critical>
## No Stubs, No Incomplete Wiring

This is the #1 source of bugs in this project.

- `vec![]`, hardcoded `false`, and "empty for now" patterns are STUBS — even when the code compiles and tests pass.
- If you cannot wire something end-to-end right now, say so explicitly — do not ship a silent stub that looks like working code.
- Before writing new logic, trace existing code first. 90% of bugs in this codebase are disconnected wiring, not missing features. The function you need almost certainly already exists.

Session 5+6 playtests found `footnotes: vec![]` in 5 places, `inventory: vec![]` at save/load, `in_combat: false` hardcoded, slash router never instantiated, NPC registry not serialized, turn barrier not called, perception rewriter not connected, PARTY_STATUS never emitted — ALL written after the no-stubs rule was already in CLAUDE.md. Each stub cost 2-3x debugging time.
</critical>

<critical>
## Integration Wiring Is Part of the Story

TDD per-component creates stubs at integration seams. Each component passes its tests but nothing connects them. An unwired component is a stub. A stub is a bug.

- Definition of done for any component INCLUDES the call site that invokes it.
- If you build `barrier.rs`, the same story wires it into `dispatch_player_action()`.
- If you build a UI panel, the same story ensures the server emits the messages it needs.
- If you build an extraction pipeline, the same story connects its output to the consumer.
- Ship connected or don't ship.
</critical>

<critical>
## Debugging: Trace First, Wire Second, New Code Last

- Before implementing anything, search for the types, functions, and handlers that already exist.
- If you find yourself writing more than ~20 lines of new logic, STOP and ask: "Does this already exist somewhere?"
- When you hit a missing module/import: check `gh pr list` and `git branch -r` FIRST. If there's a PR for it, merge that PR — don't reinvent.
</critical>

<critical>
## Spoiler Protection

- Fully spoilable: `mutant_wasteland/flickering_reach` only
- Fully unspoiled: Everything else
</critical>

## Architecture Notes

- API communicates via WebSocket for real-time game events (narration, state updates)
- Small REST surface for save/load, character listing, genre pack metadata
- Claude CLI (`claude -p`) for all LLM calls — subprocess, not SDK
- Genre packs are YAML, loaded by the API from a configured path
- Media daemon (`sidequest-daemon`) is a Python sidecar for image/audio generation
