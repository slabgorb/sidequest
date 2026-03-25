#!/bin/bash
# otel-auto-config.sh - Auto-configure OTEL for Frame server (Story 20-1)
#
# This hook checks for a .frame-port file in the project directory.
# If found, it sets the OTEL environment variables to connect Claude Code
# telemetry to the running Frame server.
#
# Usage: Source this script early in Claude Code startup to enable auto-config.
#   source /path/to/otel-auto-config.sh
#
# Prerequisites:
#   - Frame server must be running (writes .frame-port file)
#   - CLAUDE_PROJECT_DIR must be set (standard in Claude Code environment)

# Determine project directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Read port from .frame-port (written by Frame server on startup)
PORT=""
PORT_FILE="$PROJECT_DIR/.frame-port"
if [[ -f "$PORT_FILE" ]]; then
  PORT=$(cat "$PORT_FILE" 2>/dev/null)
  # Validate port is a number
  if [[ ! "$PORT" =~ ^[0-9]+$ ]]; then
    PORT=""
  fi
fi

# Configure OTEL if a valid port was found
if [[ -n "$PORT" ]]; then
  export CLAUDE_CODE_ENABLE_TELEMETRY=1
  export OTEL_EXPORTER_OTLP_PROTOCOL="http/json"
  export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:$PORT"

  # Optional: Log for debugging (can be silenced by setting FRAME_QUIET=1)
  if [[ -z "$FRAME_QUIET" ]]; then
    echo "[otel-auto-config] Configured OTEL to http://localhost:$PORT (from $PORT_FILE)" >&2
  fi
fi
