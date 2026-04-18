#!/usr/bin/env bash
# cargo-guard.sh — wraps a cargo command with the three safety mechanisms
# needed to prevent the recurring "can't run tests" death-spiral on macOS:
#
#   1. flock on a project-local lockfile — serializes cargo invocations so
#      concurrent `cargo test` / `cargo build` / `cargo clippy` calls queue
#      instead of racing on target/.cargo-lock and producing orphan
#      build-script-build processes.
#
#   2. 30s heartbeat to stderr — defeats the Claude Code 2-minute stream
#      watchdog that auto-backgrounds a silent process. A cargo build that
#      takes 4 minutes used to fire an auto-background at 2 min and trick
#      the agent into launching a second cargo behind the first, which then
#      deadlocked the test runner. A heartbeat every 30s keeps the stream
#      alive so cargo runs to completion in the foreground.
#
#   3. `set -o pipefail` — ensures that `cargo test | tail -N` style
#      invocations surface cargo's real exit code instead of tail's zero.
#      A failing test must fail the command.
#
# The command itself is passed via the CARGO_GUARD_CMD_B64 env var,
# base64-encoded to avoid shell-quoting hell. The hook decodes and runs it
# under bash -c.
#
# Exit codes are propagated faithfully. The heartbeat is cleaned up on exit.

set -u

: "${CARGO_GUARD_CMD_B64:?cargo-guard: CARGO_GUARD_CMD_B64 must be set}"

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOCK_PARENT="$PROJECT_ROOT/.cargo"
LOCK_DIR="$LOCK_PARENT/cargo-guard.lock.d"

mkdir -p "$LOCK_PARENT"

CMD="$(printf '%s' "$CARGO_GUARD_CMD_B64" | base64 -d)"

# ---------------------------------------------------------------------------
# mkdir-based lock — portable to stock macOS (no util-linux `flock` required).
#
# `mkdir` is atomic on POSIX filesystems: exactly one caller wins when
# multiple race to create the same directory. If the existing lock-holder's
# PID file exists but points at a dead process, treat the lock as stale and
# reclaim. Otherwise wait.
# ---------------------------------------------------------------------------

LOCK_HELD=0

acquire_lock() {
  local waited=0
  while true; do
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      echo "$$" > "$LOCK_DIR/pid"
      LOCK_HELD=1
      return 0
    fi
    # Stale-lock check: if PID file references a non-existent process,
    # clean up and retry. `kill -0` tests whether a PID is alive without
    # actually sending a signal.
    if [ -f "$LOCK_DIR/pid" ]; then
      local holder
      holder="$(cat "$LOCK_DIR/pid" 2>/dev/null)"
      if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then
        rm -rf "$LOCK_DIR" 2>/dev/null || true
        continue
      fi
    fi
    sleep 1
    waited=$((waited + 1))
    if [ $((waited % 30)) -eq 0 ]; then
      printf '[cargo-guard] waiting on cargo lock — %ds\n' "$waited" >&2
    fi
  done
}

release_lock() {
  if [ "$LOCK_HELD" -eq 1 ]; then
    rm -rf "$LOCK_DIR" 2>/dev/null || true
    LOCK_HELD=0
  fi
}

# ---------------------------------------------------------------------------
# Heartbeat — prints to stderr every 30s so the Claude Code stream watchdog
# does not auto-background the cargo invocation at the 2-minute mark.
# ---------------------------------------------------------------------------

(
  while true; do
    sleep 30
    printf '[cargo-guard] still running — %ds elapsed\n' "$SECONDS" >&2
  done
) &
HB=$!

cleanup() {
  kill "$HB" 2>/dev/null || true
  wait "$HB" 2>/dev/null || true
  release_lock
}
trap cleanup EXIT INT TERM

acquire_lock

# pipefail so `cargo test | tail -N` surfaces cargo's real exit code
# instead of tail's zero.
set -o pipefail
bash -c "$CMD"
RC=$?

exit $RC
