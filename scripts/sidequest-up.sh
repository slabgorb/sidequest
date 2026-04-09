#!/usr/bin/env bash
# sidequest-up — start all SideQuest services with logging to /tmp
#
# Usage: sidequest-up.sh [--kill]
#   --kill  Stop all running services
#
# Logs: /tmp/sidequest-api.log, /tmp/sidequest-ui.log, /tmp/sidequest-daemon.log
# PIDs: /tmp/sidequest-{service}.pid

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OQ_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTENT="$OQ_ROOT/sidequest-content/genre_packs"

stop_services() {
    local stopped=0
    for service in api ui daemon; do
        local pidfile="/tmp/sidequest-${service}.pid"
        if [[ -f "$pidfile" ]]; then
            local pid
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                echo "Stopped sidequest-${service} (pid $pid)"
                stopped=$((stopped + 1))
            fi
            rm -f "$pidfile"
        fi
    done
    if [[ $stopped -eq 0 ]]; then
        echo "No running services found."
    fi
}

if [[ "${1:-}" == "--kill" ]]; then
    stop_services
    exit 0
fi

# Stop any existing services first
stop_services 2>/dev/null

echo "Starting SideQuest services..."
echo "  Logs: /tmp/sidequest-{api,ui,daemon}.log"
echo "  Root: $OQ_ROOT"
echo ""

# 1. Daemon (Python media services)
(
    cd "$OQ_ROOT/sidequest-daemon"
    SIDEQUEST_GENRE_PACKS="$CONTENT" uv run sidequest-renderer --warmup \
        > /tmp/sidequest-daemon.log 2>&1 &
    echo $! > /tmp/sidequest-daemon.pid
)
echo "  daemon  started (pid $(cat /tmp/sidequest-daemon.pid))"

# 2. API server (Rust — build CLI tools first, then run)
(
    cd "$OQ_ROOT/sidequest-api"
    cargo build -p sidequest-namegen -p sidequest-encountergen -p sidequest-loadoutgen 2>/dev/null
    cargo run -p sidequest-server -- --genre-packs-path "$CONTENT" \
        > /tmp/sidequest-api.log 2>&1 &
    echo $! > /tmp/sidequest-api.pid
)
echo "  api     started (pid $(cat /tmp/sidequest-api.pid))"

# 3. UI dev server (React)
(
    cd "$OQ_ROOT/sidequest-ui"
    npm run dev > /tmp/sidequest-ui.log 2>&1 &
    echo $! > /tmp/sidequest-ui.pid
)
echo "  ui      started (pid $(cat /tmp/sidequest-ui.pid))"

echo ""
echo "All services running. Tail logs with:"
echo "  tail -f /tmp/sidequest-api.log"
echo "  tail -f /tmp/sidequest-ui.log"
echo "  tail -f /tmp/sidequest-daemon.log"
echo ""
echo "Stop with: $0 --kill"
