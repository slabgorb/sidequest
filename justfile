# SideQuest Orchestrator — cross-repo task runner (post-ADR-082, Python)

root    := justfile_directory()
content := root / "sidequest-content" / "genre_packs"
logdir  := "/tmp"

import '.pennyfarthing/justfile.pf'

# Default: run everything the way I always run it.
default: up

# ---------------------------------------------------------------------------
# The three you actually use.
# Each recipe tees stdout+stderr to /tmp so you can re-tail it later with:
#   tail -f /tmp/sidequest-{server,client,daemon}.log
# Ctrl-C stops the service in the foreground.
# ---------------------------------------------------------------------------

# API server (FastAPI / uvicorn) — port 8765
server *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    log={{logdir}}/sidequest-server.log
    : > "$log"
    cd {{root}}/sidequest-server
    SIDEQUEST_GENRE_PACKS={{content}} \
    SIDEQUEST_RENDER_ENABLED=1 \
        uv run uvicorn sidequest.server.app:create_app \
            --factory --reload --host 127.0.0.1 --port 8765 {{flags}} 2>&1 \
        | tee "$log"

# React client (Vite) — port 5173
client *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    log={{logdir}}/sidequest-client.log
    : > "$log"
    cd {{root}}/sidequest-ui
    npm run dev -- {{flags}} 2>&1 | tee "$log"

# Media daemon (Flux/Z-Image renderer) with warmup
daemon *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    log={{logdir}}/sidequest-daemon.log
    : > "$log"
    cd {{root}}/sidequest-daemon
    SIDEQUEST_GENRE_PACKS={{content}} \
        uv run sidequest-renderer --warmup {{flags}} 2>&1 \
        | tee "$log"

# ---------------------------------------------------------------------------
# `just up` — boot all three in the background, tail the merged log stream.
# Ctrl-C tears them down.
# ---------------------------------------------------------------------------

up:
    #!/usr/bin/env bash
    set -euo pipefail
    srv={{logdir}}/sidequest-server.log
    cli={{logdir}}/sidequest-client.log
    dmn={{logdir}}/sidequest-daemon.log
    : > "$srv"; : > "$cli"; : > "$dmn"

    # Kill any leftover services from a previous run.
    for svc in server client daemon; do
        pidfile={{logdir}}/sidequest-${svc}.pid
        if [[ -f "$pidfile" ]]; then
            kill "$(cat "$pidfile")" 2>/dev/null || true
            rm -f "$pidfile"
        fi
    done

    echo "▶ daemon  (warmup)  → $dmn"
    ( cd {{root}}/sidequest-daemon && \
        SIDEQUEST_GENRE_PACKS={{content}} \
        uv run sidequest-renderer --warmup >"$dmn" 2>&1 ) &
    echo $! > {{logdir}}/sidequest-daemon.pid

    echo "▶ server  (:8765)   → $srv"
    ( cd {{root}}/sidequest-server && \
        SIDEQUEST_GENRE_PACKS={{content}} \
        SIDEQUEST_RENDER_ENABLED=1 \
        uv run uvicorn sidequest.server.app:create_app \
            --factory --reload --host 127.0.0.1 --port 8765 >"$srv" 2>&1 ) &
    echo $! > {{logdir}}/sidequest-server.pid

    echo "▶ client  (:5173)   → $cli"
    ( cd {{root}}/sidequest-ui && npm run dev >"$cli" 2>&1 ) &
    echo $! > {{logdir}}/sidequest-client.pid

    cleanup() {
        echo
        echo "Stopping services…"
        for svc in server client daemon; do
            pidfile={{logdir}}/sidequest-${svc}.pid
            if [[ -f "$pidfile" ]]; then
                kill "$(cat "$pidfile")" 2>/dev/null || true
                rm -f "$pidfile"
            fi
        done
    }
    trap cleanup EXIT INT TERM

    echo
    echo "All services up. Open http://localhost:5173"
    echo "Tailing logs (Ctrl-C to stop everything)…"
    echo
    tail -F "$dmn" "$srv" "$cli"

# Stop all background services started by `just up`.
down:
    #!/usr/bin/env bash
    for svc in server client daemon; do
        pidfile={{logdir}}/sidequest-${svc}.pid
        if [[ -f "$pidfile" ]]; then
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" && echo "stopped sidequest-$svc (pid $pid)"
            fi
            rm -f "$pidfile"
        fi
    done

# Tail one or all service logs.  `just logs`, `just logs server`, etc.
logs service="all":
    #!/usr/bin/env bash
    if [[ "{{service}}" == "all" ]]; then
        tail -F {{logdir}}/sidequest-server.log \
                {{logdir}}/sidequest-client.log \
                {{logdir}}/sidequest-daemon.log
    else
        tail -F {{logdir}}/sidequest-{{service}}.log
    fi

# ---------------------------------------------------------------------------
# Per-service tasks
# ---------------------------------------------------------------------------

# Server (FastAPI)
server-test:
    cd {{root}}/sidequest-server && uv run pytest -v

server-lint:
    cd {{root}}/sidequest-server && uv run ruff check .

server-fmt:
    cd {{root}}/sidequest-server && uv run ruff format .

server-check: server-lint server-test

# Client (React)
client-test:
    cd {{root}}/sidequest-ui && npx vitest run

client-build:
    cd {{root}}/sidequest-ui && npm run build

client-lint:
    cd {{root}}/sidequest-ui && npm run lint

client-install:
    cd {{root}}/sidequest-ui && npm install

# Daemon (media services)
daemon-status:
    cd {{root}}/sidequest-daemon && uv run sidequest-renderer --status

daemon-stop:
    cd {{root}}/sidequest-daemon && uv run sidequest-renderer --shutdown

daemon-test:
    cd {{root}}/sidequest-daemon && SIDEQUEST_GENRE_PACKS={{content}} pytest

daemon-lint:
    cd {{root}}/sidequest-daemon && ruff check .

daemon-install:
    cd {{root}}/sidequest-daemon && pip install -e ".[dev]"

# ---------------------------------------------------------------------------
# Cross-repo + utilities
# ---------------------------------------------------------------------------

check-all: server-check client-lint client-test daemon-lint

# OTEL dashboard — browser-friendly /ws/watcher viewer
otel port="9765":
    uv run python3 {{root}}/scripts/playtest_dashboard.py --dashboard-port {{port}}

# Headless playtest driver (uses the running server)
playtest *flags:
    python3 {{root}}/scripts/playtest.py {{flags}}

playtest-scenario file:
    python3 {{root}}/scripts/playtest.py --scenario {{root}}/scenarios/{{file}}.yaml

# tmuxinator session — server, client, daemon, otel in four panes
tmux:
    tmuxinator start -p {{root}}/.tmuxinator.yml

# Git status across every repo
status:
    @echo "=== orchestrator ===" && git status --short
    @echo "=== server ==="        && cd {{root}}/sidequest-server  && git status --short
    @echo "=== client ==="        && cd {{root}}/sidequest-ui      && git status --short
    @echo "=== daemon ==="        && cd {{root}}/sidequest-daemon  && git status --short
    @echo "=== content ==="       && cd {{root}}/sidequest-content && git status --short

# Sync shared CLAUDE.md preamble to all subrepos
sync-claude-md:
    python3 {{root}}/scripts/sync-claude-preamble.py

# First-time setup — install deps for every subrepo
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== SideQuest setup ==="
    for dir in sidequest-server sidequest-daemon; do
        if [[ -d "{{root}}/$dir" ]]; then
            echo "--- $dir (uv sync) ---"
            ( cd {{root}}/$dir && uv sync --all-extras )
        else
            echo "⚠ $dir not cloned"
        fi
    done
    if [[ -d "{{root}}/sidequest-ui" ]]; then
        echo "--- sidequest-ui (npm install) ---"
        ( cd {{root}}/sidequest-ui && npm install )
    else
        echo "⚠ sidequest-ui not cloned"
    fi
    echo "--- git hooks (point to .githooks/) ---"
    git -C {{root}} config core.hooksPath .githooks
    echo "=== setup complete ==="

# Validate ADR frontmatter + report staleness of generated indexes.
adr-check:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "--- Validating ADR frontmatter ---"
    python3 {{root}}/scripts/validate_adr_frontmatter.py
    echo ""
    echo "--- Checking generated indexes are up to date ---"
    tmpdir=$(mktemp -d)
    trap "rm -rf $tmpdir" EXIT
    for f in docs/adr/README.md docs/adr/SUPERSEDED.md docs/adr/DRIFT.md CLAUDE.md; do
        cp "{{root}}/$f" "$tmpdir/$(basename "$f").before"
    done
    python3 {{root}}/scripts/regenerate_adr_indexes.py > /dev/null
    stale=0
    for f in docs/adr/README.md docs/adr/SUPERSEDED.md docs/adr/DRIFT.md CLAUDE.md; do
        if ! diff -q "$tmpdir/$(basename "$f").before" "{{root}}/$f" > /dev/null; then
            echo "  STALE: $f (regen produced changes)"
            stale=1
        fi
    done
    if [[ $stale -eq 1 ]]; then
        echo ""
        echo "ERROR: generated indexes are stale relative to frontmatter."
        echo "Run: just adr-regen   (then stage and commit the index files)"
        exit 1
    fi
    echo "  OK: generated indexes are up to date."

# Regenerate ADR indexes from frontmatter (README tag sections, SUPERSEDED.md, DRIFT.md, CLAUDE.md block).
adr-regen:
    #!/usr/bin/env bash
    set -euo pipefail
    python3 {{root}}/scripts/regenerate_adr_indexes.py
