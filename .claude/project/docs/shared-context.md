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

## Architecture Notes

- API communicates via WebSocket for real-time game events (narration, state updates)
- Small REST surface for save/load, character listing, genre pack metadata
- Claude CLI (`claude -p`) for all LLM calls — subprocess, not SDK
- Genre packs are YAML, loaded by the API from a configured path
- Media daemon (`sidequest-daemon`) is a Python sidecar for image/audio generation
