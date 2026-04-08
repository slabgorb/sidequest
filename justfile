# SideQuest Orchestrator — Cross-repo task runner

root := justfile_directory()
content := root / "sidequest-content" / "genre_packs"

import '.pennyfarthing/justfile.pf'

# API (Rust backend)
api-test:
    cd sidequest-api && cargo test

api-build:
    cd sidequest-api && cargo build

api-release:
    cd sidequest-api && cargo build --release

api-run *flags:
    cd sidequest-api && cargo build -p sidequest-namegen -p sidequest-encountergen -p sidequest-loadoutgen 2>/dev/null; cargo run -p sidequest-server -- --genre-packs-path {{content}} {{flags}}

api-lint:
    cd sidequest-api && cargo clippy -- -D warnings

api-fmt:
    cd sidequest-api && cargo fmt

api-check:
    cd sidequest-api && cargo fmt --check && cargo clippy -- -D warnings && cargo test

# Preview narrator prompt (uses real Rust types — never drifts)
prompt-preview *flags:
    cd sidequest-api && cargo run -p sidequest-promptpreview -- {{flags}}

# UI (React frontend)
ui-dev:
    cd sidequest-ui && npm run dev

ui-test:
    cd sidequest-ui && npx vitest run

ui-build:
    cd sidequest-ui && npm run build

ui-lint:
    cd sidequest-ui && npm run lint

ui-install:
    cd sidequest-ui && npm install

# Daemon (Python media services)
daemon-run:
    cd sidequest-daemon && SIDEQUEST_GENRE_PACKS={{content}} uv run sidequest-renderer --warmup

daemon-status:
    cd sidequest-daemon && uv run sidequest-renderer --status

daemon-stop:
    cd sidequest-daemon && uv run sidequest-renderer --shutdown

daemon-test:
    cd sidequest-daemon && SIDEQUEST_GENRE_PACKS={{content}} pytest

daemon-lint:
    cd sidequest-daemon && ruff check .

daemon-install:
    cd sidequest-daemon && pip install -e ".[dev]"

# OTEL dashboard — proxies /ws/watcher to a browser-friendly web UI
otel port="9765":
    python3 scripts/playtest.py --dashboard-only --dashboard-port {{port}}

# Quick-start aliases
warmup: daemon-run
server *flags:
    just api-run {{flags}}
client: ui-dev

# tmuxinator dev session (server, otel, client, daemon in 4 panes)
tmux:
    tmuxinator start -p .tmuxinator.yml

# Cross-repo
check-all: api-check ui-lint ui-test

# First-time dev environment setup
setup:
    #!/usr/bin/env bash
    echo "=== SideQuest Dev Environment Setup ==="
    echo ""

    # API (Rust)
    if [ -d "sidequest-api" ]; then
        echo "--- Rust toolchain ---"
        rustup component add clippy
        echo "--- API dependencies ---"
        cd sidequest-api && cargo build
        cd ..
        echo "✓ API ready"
    else
        echo "⚠ sidequest-api not cloned. Run: git clone git@github.com:slabgorb/sidequest-api.git"
    fi

    echo ""

    # UI (React)
    if [ -d "sidequest-ui" ]; then
        echo "--- UI dependencies ---"
        cd sidequest-ui && npm install
        cd ..
        echo "✓ UI ready"
    else
        echo "⚠ sidequest-ui not cloned. Run: git clone git@github.com:slabgorb/sidequest-ui.git"
    fi

    echo ""

    # Daemon (Python)
    if [ -d "sidequest-daemon" ]; then
        echo "--- Daemon dependencies ---"
        cd sidequest-daemon && pip install -e ".[dev]"
        cd ..
        echo "✓ Daemon ready"
    else
        echo "⚠ sidequest-daemon not cloned. Run: git clone git@github.com:slabgorb/sidequest-daemon.git"
    fi

    echo ""
    echo "=== Setup complete ==="

# Headless playtest
playtest-server *flags:
    cd sidequest-api && cargo build -p sidequest-namegen -p sidequest-encountergen -p sidequest-loadoutgen 2>/dev/null; cargo run -p sidequest-server -- --genre-packs-path {{content}} --headless {{flags}}

playtest *flags:
    python3 scripts/playtest.py {{flags}}

playtest-scenario file:
    python3 scripts/playtest.py --scenario scenarios/{{file}}.yaml

status:
    @echo "=== API ===" && cd sidequest-api && git status --short
    @echo "=== UI ===" && cd sidequest-ui && git status --short
    @echo "=== Daemon ===" && cd sidequest-daemon && git status --short 2>/dev/null || echo "(not cloned)"
    @echo "=== Orchestrator ===" && git status --short

# Sync shared CLAUDE.md preamble to all subrepos
sync-claude-md:
    python3 scripts/sync-claude-preamble.py
