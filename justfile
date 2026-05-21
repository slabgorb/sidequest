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
    # Anthropic SDK narrator (ADR-101) hard-requires ANTHROPIC_API_KEY — the
    # SDK client raises without it. Don't depend on the launching shell having
    # sourced ~/.zshrc: resolve it here (env override wins; else pull the
    # canonical ~/.zshrc export). Fail loudly, never start silently keyless.
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      ANTHROPIC_API_KEY="$(sed -nE 's/^[[:space:]]*export[[:space:]]+ANTHROPIC_API_KEY=["'\'']?([^"'\'' ]+).*/\1/p' "$HOME/.zshrc" 2>/dev/null | tail -n1)"
    fi
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      echo "✗ ANTHROPIC_API_KEY not set and no 'export ANTHROPIC_API_KEY=' in ~/.zshrc — Anthropic SDK narrator (ADR-101) cannot start. Export it or add it to ~/.zshrc." >&2
      exit 1
    fi
    export ANTHROPIC_API_KEY
    SIDEQUEST_GENRE_PACKS={{content}} \
    SIDEQUEST_RENDER_ENABLED=1 \
    SIDEQUEST_NARRATOR_STREAMING="${SIDEQUEST_NARRATOR_STREAMING:-1}" \
    SIDEQUEST_ASSET_BASE_URL="${SIDEQUEST_ASSET_BASE_URL:-https://cdn.slabgorb.com}" \
    DEV_SCENES="${DEV_SCENES:-1}" \
    SIDEQUEST_FIXTURES_DIR="${SIDEQUEST_FIXTURES_DIR:-{{root}}/scenarios/fixtures}" \
        uv run uvicorn sidequest.server.app:create_app \
            --factory --reload --reload-dir sidequest \
            --host 127.0.0.1 --port 8765 {{flags}} 2>&1 \
        | tee "$log"

# Production-style serve for Cloudflare Tunnel: build UI, mount it on FastAPI,
# run without --reload. Pair with `cloudflared tunnel run sidequest`.
# Daemon must be running separately (`just daemon`) for image renders.
#
# - SIDEQUEST_ASSET_BASE_URL defaults to https://cdn.slabgorb.com — Phase A R2
#   sync is live, so genre_packs media is served directly from R2's CDN-fronted
#   bucket. Override with SIDEQUEST_ASSET_BASE_URL=local for offline/local-only
#   dev (serves from /genre and /renders mounts).
# - --proxy-headers: trust X-Forwarded-* from cloudflared on 127.0.0.1, so
#   request.url and client IP reflect the public hostname (https) instead of localhost.
serve *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    log={{logdir}}/sidequest-server.log
    : > "$log"
    echo "▶ building UI…"
    ( cd {{root}}/sidequest-ui && npm run build )
    cd {{root}}/sidequest-server
    # Anthropic SDK narrator (ADR-101) hard-requires ANTHROPIC_API_KEY — the
    # SDK client raises without it. Don't depend on the launching shell having
    # sourced ~/.zshrc: resolve it here (env override wins; else pull the
    # canonical ~/.zshrc export). Fail loudly, never start silently keyless.
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      ANTHROPIC_API_KEY="$(sed -nE 's/^[[:space:]]*export[[:space:]]+ANTHROPIC_API_KEY=["'\'']?([^"'\'' ]+).*/\1/p' "$HOME/.zshrc" 2>/dev/null | tail -n1)"
    fi
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      echo "✗ ANTHROPIC_API_KEY not set and no 'export ANTHROPIC_API_KEY=' in ~/.zshrc — Anthropic SDK narrator (ADR-101) cannot start. Export it or add it to ~/.zshrc." >&2
      exit 1
    fi
    export ANTHROPIC_API_KEY
    SIDEQUEST_GENRE_PACKS={{content}} \
    SIDEQUEST_RENDER_ENABLED=1 \
    SIDEQUEST_NARRATOR_STREAMING="${SIDEQUEST_NARRATOR_STREAMING:-1}" \
    SIDEQUEST_ASSET_BASE_URL="${SIDEQUEST_ASSET_BASE_URL:-https://cdn.slabgorb.com}" \
    SIDEQUEST_UI_DIST={{root}}/sidequest-ui/dist \
        uv run uvicorn sidequest.server.app:create_app \
            --factory --host 127.0.0.1 --port 8765 \
            --proxy-headers --forwarded-allow-ips 127.0.0.1 \
            {{flags}} 2>&1 \
        | tee "$log"

# Cloudflare Tunnel — exposes :8765 at https://sidequest.slabgorb.com.
# Tunnel config lives at ~/.cloudflared/config.yml. Access policy gates the
# hostname; only the playgroup email allowlist gets in.
tunnel:
    cloudflared tunnel run sidequest

# React client (Vite) — port 5173
client *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    log={{logdir}}/sidequest-client.log
    : > "$log"
    cd {{root}}/sidequest-ui
    npm run dev -- {{flags}} 2>&1 | tee "$log"

# Private: spawn the daemon (caller handles output redirection / flags).
# Extracted per Story 43-5 so `daemon` and `up` share one source of truth
# for the daemon invocation — a flag change updates both call sites.
_daemon-cmd *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${R2_S3_ENDPOINT:?R2_S3_ENDPOINT must be set in shell}"
    : "${R2_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID must be set in shell}"
    : "${R2_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY must be set in shell}"
    cd {{root}}/sidequest-daemon
    SIDEQUEST_GENRE_PACKS={{content}} \
        exec uv run sidequest-renderer --warmup {{flags}}

# Media daemon (Z-Image renderer) with warmup
daemon *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    log={{logdir}}/sidequest-daemon.log
    : > "$log"
    just _daemon-cmd {{flags}} 2>&1 | tee "$log"

# ---------------------------------------------------------------------------
# `just up` — boot all three in the background, tail the merged log stream.
# Ctrl-C tears them down.
# ---------------------------------------------------------------------------

up *flags:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${R2_S3_ENDPOINT:?R2_S3_ENDPOINT must be set in shell}"
    : "${R2_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID must be set in shell}"
    : "${R2_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY must be set in shell}"

    # Anthropic SDK narrator (ADR-101) hard-requires ANTHROPIC_API_KEY — the SDK
    # client raises at first WebSocket connect without it. `just server` resolves
    # this but `up` historically did not, so `up` failed late mid-session instead
    # of refusing at boot. Resolve it here (env override wins; else pull the
    # canonical ~/.zshrc export), export so the inline server subshell inherits
    # it, and fail loudly. Never start silently keyless.
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      ANTHROPIC_API_KEY="$(sed -nE 's/^[[:space:]]*export[[:space:]]+ANTHROPIC_API_KEY=["'\'']?([^"'\'' ]+).*/\1/p' "$HOME/.zshrc" 2>/dev/null | tail -n1)"
    fi
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
      echo "✗ ANTHROPIC_API_KEY not set and no 'export ANTHROPIC_API_KEY=' in ~/.zshrc — Anthropic SDK narrator (ADR-101) cannot start. Export it or add it to ~/.zshrc." >&2
      exit 1
    fi
    export ANTHROPIC_API_KEY

    srv={{logdir}}/sidequest-server.log
    cli={{logdir}}/sidequest-client.log
    dmn={{logdir}}/sidequest-daemon.log

    # ---- Machine-global singleton lock (spans every clone) ------------------
    # Prevents the 2026-05-21 duplicate-stack cost runaway: two `just up` from
    # oq-1 + oq-2 racing port 8765 with cold prompt caches burned 41.6M tokens.
    # macOS ships no flock(1), so use an atomic `mkdir` lock dir in /tmp guarded
    # by a PID liveness check — a crashed `just up` leaves a STALE (reclaimable)
    # lock, never a permanent one. Acquired BEFORE log truncation below so a
    # refusal can't clobber the running stack's logs.
    lockdir=/tmp/sidequest-stack.lock.d
    holder="$lockdir/holder"
    force=0
    [[ "{{flags}}" == *--force* || "{{flags}}" == *-f* ]] && force=1

    if ! mkdir "$lockdir" 2>/dev/null; then
        hpid=""; hroot="?"; hsince="?"
        [[ -f "$holder" ]] && source "$holder" 2>/dev/null || true
        hpid="${HOLDER_PID:-}"; hroot="${HOLDER_ROOT:-?}"; hsince="${HOLDER_SINCE:-?}"
        if [[ -n "$hpid" ]] && kill -0 "$hpid" 2>/dev/null; then
            if [[ "$force" -eq 1 ]]; then
                echo "▶ --force: tearing down existing stack (${hroot}, pid $hpid)…"
                kill "$hpid" 2>/dev/null || true   # victim's own EXIT trap reaps its services
                sleep 1
                rm -rf "$lockdir"
            else
                echo "ERROR: a sidequest stack is already running" >&2
                echo "  holder: ${hroot}  (just up, pid $hpid, since ${hsince})" >&2
                echo "  ports 8765 + 5173 are owned by that stack." >&2
                echo "  Run \`just down\` there first, or \`just up --force\` to take over." >&2
                echo "Aborting." >&2
                exit 1
            fi
        else
            echo "▶ clearing stale stack lock (holder pid ${hpid:-?} not running)"
            rm -rf "$lockdir"
        fi
        mkdir "$lockdir" 2>/dev/null || { echo "ERROR: could not claim stack lock at $lockdir" >&2; exit 1; }
    fi
    {
        echo "HOLDER_PID=$$"
        echo "HOLDER_ROOT={{root}}"
        echo "HOLDER_SINCE=\"$(date '+%Y-%m-%d %H:%M:%S')\""
    } > "$holder"

    : > "$srv"; : > "$cli"; : > "$dmn"

    # Kill any leftover services from a previous run.
    for svc in server client daemon; do
        pidfile={{logdir}}/sidequest-${svc}.pid
        if [[ -f "$pidfile" ]]; then
            kill "$(cat "$pidfile")" 2>/dev/null || true
            rm -f "$pidfile"
        fi
    done

    # Reap orphans listening on our ports — covers processes started outside
    # this shell (different terminal, prior session whose pidfile was lost,
    # crashed `just up` that never ran cleanup). Without this, `uvicorn`
    # silently fails to bind and the stack tails three logs while one
    # service is actually missing — which is how the 2026-05-09 chargen
    # playtest hit a stale-server schema-mismatch wall.
    for port in 8765 5173; do
        pids=$(lsof -ti tcp:$port 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            echo "▶ reaping orphan listener on :$port (pid(s) $pids)"
            kill $pids 2>/dev/null || true
            sleep 0.3
            # Force-kill anything that didn't exit on SIGTERM.
            stragglers=$(lsof -ti tcp:$port 2>/dev/null || true)
            if [[ -n "$stragglers" ]]; then
                kill -9 $stragglers 2>/dev/null || true
            fi
        fi
    done

    echo "▶ daemon  (warmup)  → $dmn"
    ( just _daemon-cmd >"$dmn" 2>&1 ) &
    echo $! > {{logdir}}/sidequest-daemon.pid

    echo "▶ server  (:8765)   → $srv"
    ( cd {{root}}/sidequest-server && \
        SIDEQUEST_GENRE_PACKS={{content}} \
        SIDEQUEST_RENDER_ENABLED=1 \
        SIDEQUEST_ASSET_BASE_URL="${SIDEQUEST_ASSET_BASE_URL:-https://cdn.slabgorb.com}" \
        DEV_SCENES="${DEV_SCENES:-1}" \
        SIDEQUEST_FIXTURES_DIR="${SIDEQUEST_FIXTURES_DIR:-{{root}}/scenarios/fixtures}" \
        uv run uvicorn sidequest.server.app:create_app \
            --factory --reload --reload-dir sidequest \
            --host 127.0.0.1 --port 8765 >"$srv" 2>&1 ) &
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
        # Release the singleton lock only if we still hold it. A `just up
        # --force` from another clone reassigns the holder to its own PID;
        # in that case we must NOT delete the lock out from under it.
        if [[ -f "$holder" ]] && grep -q "^HOLDER_PID=$$\$" "$holder" 2>/dev/null; then
            rm -rf "$lockdir"
        fi
    }
    trap cleanup EXIT INT TERM

    echo
    echo "All services up. Open http://localhost:5173"
    echo "Tailing logs (Ctrl-C to stop everything)…"
    echo
    tail -F "$dmn" "$srv" "$cli"

# Stop all background services started by `just up`.
#
# Reaps both pidfile-tracked processes AND any orphan listeners on our ports
# (server :8765, client :5173). The port sweep handles processes started
# outside this shell — prior sessions, crashed `just up` runs, services
# launched manually with `just server` / `just client`. Without it, the
# 2026-05-09 chargen playtest pattern repeats: `just down` looks clean but
# the next `just up` can't bind.
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

    for port in 8765 5173; do
        pids=$(lsof -ti tcp:$port 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            echo "stopped orphan listener on :$port (pid(s) $pids)"
            kill $pids 2>/dev/null || true
            sleep 0.3
            stragglers=$(lsof -ti tcp:$port 2>/dev/null || true)
            if [[ -n "$stragglers" ]]; then
                kill -9 $stragglers 2>/dev/null || true
            fi
        fi
    done

    # Release the machine-global singleton lock (see `up`). `just down` always
    # clears it so a crashed holder can't wedge the next `just up`.
    rm -rf /tmp/sidequest-stack.lock.d

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

# Strict type-check — catches drift that ESLint and Vite let through.
# tsc --noEmit (used by some IDEs) skips composite projects; tsc -b walks
# tsconfig.app.json + tsconfig.node.json the way `npm run build` does.
client-typecheck:
    cd {{root}}/sidequest-ui && npx tsc -b

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

# Style-only prompt preview — show GENRE/WORLD/CULTURE styling for a world
preview-style genre world:
    cd {{root}}/sidequest-daemon && \
        SIDEQUEST_GENRE_PACKS={{content}} \
        uv run sidequest-promptpreview style --genre {{genre}} --world {{world}}

# ---------------------------------------------------------------------------
# Cross-repo + utilities
# ---------------------------------------------------------------------------

check-all: server-check client-lint client-typecheck client-test daemon-lint

# OTEL dashboard — opens the browser-friendly /ws/watcher viewer
# served by sidequest-server itself. Server must already be running
# (e.g. via `just up` or `just server`).
otel:
    uv run python3 -m webbrowser http://localhost:8765/dashboard

# ---------------------------------------------------------------------------
# Jaeger v2 — local trace collector + query UI for raw OTLP spans.
#
# Sits alongside the WatcherHub / GM dashboard; the watcher feed is the
# in-game "lie detector" for players, Jaeger is post-hoc forensics for the
# dev box. Spans flow to both when SIDEQUEST_OTLP_ENDPOINT=localhost:4317.
# ---------------------------------------------------------------------------

# Start Jaeger v2 all-in-one in the background. Badger storage at
# /tmp/sidequest-jaeger/, 7-day TTL. UI: http://localhost:16686.
#
# Inherited OTEL_EXPORTER_OTLP_* env vars are scrubbed before launch.
# This shell typically has them set to BikeRack/PF Frame (port 53670) for
# Claude Code telemetry; without scrubbing, Jaeger's embedded OTel
# Collector inherits those vars and tries to export its own self-telemetry
# to BikeRack — BikeRack is HTTP, Jaeger speaks gRPC, the result is a
# 30-second drumbeat of "frame too large, looked like an HTTP/1.1 header"
# warnings in the log. Harmless but noisy enough to drown real signal.
jaeger:
    #!/usr/bin/env bash
    set -euo pipefail
    log={{logdir}}/sidequest-jaeger.log
    pidfile={{logdir}}/sidequest-jaeger.pid
    if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "Jaeger already running (pid $(cat "$pidfile")). UI: http://localhost:16686"
        exit 0
    fi
    if ! command -v jaeger >/dev/null 2>&1; then
        echo "ERROR: jaeger binary not on PATH. Install to ~/.local/bin/jaeger"
        echo "       (jaeger v2 binary from https://github.com/jaegertracing/jaeger/releases)"
        exit 1
    fi
    : > "$log"
    mkdir -p /tmp/sidequest-jaeger/keys /tmp/sidequest-jaeger/values
    unset OTEL_EXPORTER_OTLP_ENDPOINT OTEL_EXPORTER_OTLP_HEADERS \
          OTEL_EXPORTER_OTLP_PROTOCOL OTEL_EXPORTER_OTLP_TRACES_ENDPOINT \
          OTEL_EXPORTER_OTLP_METRICS_ENDPOINT OTEL_EXPORTER_OTLP_LOGS_ENDPOINT
    ( jaeger --config=file:{{root}}/infra/jaeger/config.yaml >"$log" 2>&1 ) &
    echo $! > "$pidfile"
    echo "▶ jaeger  (:4317 OTLP, :16686 UI)  → $log"
    echo "  Set SIDEQUEST_OTLP_ENDPOINT=localhost:4317 in the server env to export spans."

# Stop the background Jaeger started by `just jaeger`.
jaeger-stop:
    #!/usr/bin/env bash
    pidfile={{logdir}}/sidequest-jaeger.pid
    if [[ -f "$pidfile" ]]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" && echo "stopped jaeger (pid $pid)"
        fi
        rm -f "$pidfile"
    else
        echo "no jaeger pidfile; nothing to stop"
    fi

# Open the Jaeger UI.
jaeger-ui:
    uv run python3 -m webbrowser http://localhost:16686

# Boot all services with OTLP export wired to local Jaeger AND every
# watcher event mirrored as a synthetic OTEL span. Requires `just jaeger`
# already running. Without SIDEQUEST_WATCHER_AS_SPANS, Jaeger only sees
# spans from `tracer().start_as_current_span(...)`; with it, every
# `publish_event(...)` call becomes a child span too — full semantic stream.
up-traced:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! curl -sSf -o /dev/null --max-time 1 http://localhost:16686 2>/dev/null; then
        echo "ERROR: Jaeger UI not reachable at :16686. Run 'just jaeger' first."
        exit 1
    fi
    # Scrub inherited OTEL_EXPORTER_OTLP_* (typically pointing at
    # BikeRack/PF Frame for Claude Code telemetry). Only SIDEQUEST_*
    # vars should drive the server's OTEL setup.
    unset OTEL_EXPORTER_OTLP_ENDPOINT OTEL_EXPORTER_OTLP_HEADERS \
          OTEL_EXPORTER_OTLP_PROTOCOL OTEL_EXPORTER_OTLP_TRACES_ENDPOINT \
          OTEL_EXPORTER_OTLP_METRICS_ENDPOINT OTEL_EXPORTER_OTLP_LOGS_ENDPOINT
    SIDEQUEST_OTLP_ENDPOINT=localhost:4317 \
    SIDEQUEST_WATCHER_AS_SPANS=1 \
        just up

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
