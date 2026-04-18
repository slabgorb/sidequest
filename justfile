# SideQuest Orchestrator — Cross-repo task runner

root := justfile_directory()
content := root / "sidequest-content" / "genre_packs"

# Disable sccache for every cargo invocation run through `just`.
#
# Why: sccache daemon contention between the OQ-1 and OQ-2 clones on this
# machine causes rustc to hang indefinitely — a cargo check that should take
# 30s has been observed sitting at 0% CPU for 19+ minutes while waiting on a
# sccache lock held by a zombie cargo test worker in the other clone. Setting
# RUSTC_WRAPPER="" bypasses sccache entirely and the build runs at normal
# speed (~3-4 min cold, seconds warm). This only applies to `just` recipes —
# raw shell `cargo ...` invocations still pick up sccache from the user env
# if they want it.
#
# Discovered during scene-harness work on 2026-04-15.
export RUSTC_WRAPPER := ""

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

# ---------------------------------------------------------------------------
# Scene Harness — drop directly into an encounter for fast iteration.
# Requires the UI dev server running on :5173 and nothing on :8765.
# ---------------------------------------------------------------------------

# Boot the API with DEV_SCENES=1, stage the named fixture save, open the UI.
scene name:
    #!/usr/bin/env bash
    set -euo pipefail
    pkill -f 'sidequest-server' 2>/dev/null || true
    sleep 1
    cd sidequest-api
    DEV_SCENES=1 SIDEQUEST_FIXTURES={{root}}/scenarios/fixtures \
        cargo run -p sidequest-server -- \
        --genre-packs-path {{content}} &
    SERVER_PID=$!
    trap "kill $SERVER_PID 2>/dev/null || true" EXIT
    # Wait for /api/genres to answer — the server is ready when this returns 200
    for i in $(seq 1 60); do
        if curl -sf http://localhost:8765/api/genres >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
    echo "Staging fixture '{{name}}'…"
    curl -sSf -X POST http://localhost:8765/dev/scene/{{name}}
    echo
    echo "Open http://localhost:5173?scene={{name}} in your browser."
    wait $SERVER_PID

# List available scene fixtures.
scene-list:
    @ls {{root}}/scenarios/fixtures/*.yaml 2>/dev/null \
        | xargs -n1 basename \
        | sed 's/\.yaml$//' \
        || echo "no fixtures"

# Stage a fixture save WITHOUT booting the server (uses the CLI binary).
scene-stage name:
    cd sidequest-api && cargo run -p sidequest-fixture -- \
        --content-root {{root}}/sidequest-content \
        --fixtures-root {{root}}/scenarios/fixtures \
        load {{name}}

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
