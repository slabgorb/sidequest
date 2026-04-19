#!/usr/bin/env bash
# PreToolUse(Bash) hook for cargo / just commands on this clone.
#
# Three jobs:
#
#   1. Inject env vars — every cargo/just invocation gets
#      `RUSTC_WRAPPER="" CARGO_HOME=<this-clone>/.cargo` prepended so this
#      clone has its own cargo registry and bypasses sccache (avoiding
#      cross-clone contention with other checkouts of the same project).
#      These env vars are harmless for just recipes that never touch
#      cargo and critical for recipes that do.
#
#   2. Deny `cargo nextest` (and bare `nextest`) — nextest's parallel
#      --list test-discovery deadlocks under macOS XProtectService's
#      single-threaded malware scanner (35+ freshly-linked test binaries
#      queue behind XProtect, never complete). `cargo test` is the only
#      safe runner on this workspace. See memory: feedback_use_nextest.md.
#      Hook returns a permissionDecision=deny so the agent cannot bypass
#      it and sees the reason.
#
#   3. Wrap all other cargo/just commands through cargo-guard.sh, which
#      adds an mkdir-based lock (serializes invocations so two concurrent
#      `cargo test` calls queue instead of racing), a 30s heartbeat to
#      defeat the 2-minute stream auto-background, and pipefail so
#      `cargo test | tail` can't mask cargo's real exit code.
#
# Why match `just` as well as `cargo`:
#   Most just recipes in this workspace invoke cargo as a subprocess
#   (api-build, api-test, api-check, api-run, api-lint, api-fmt). The
#   Claude Code PreToolUse hook only sees the top-level Bash tool_input;
#   children of `just` are invisible. Matching only `cargo` meant
#   `just api-build` bypassed the guard entirely — same deadlock risk as
#   raw cargo. Matching `just` closes that hole.
#
# Why the bypass list (BYPASS_JUST_RE):
#   Recipes that NEVER invoke cargo (ui-*, daemon-*, and a handful of
#   utility aliases) don't need env injection (no cargo to inherit it),
#   don't need the lock (no cargo contention), and emphatically don't
#   need the 30s heartbeat to stderr — that heartbeat interferes with
#   long-running services like `just daemon-run`, where stderr is a
#   live log stream the consumer is parsing. (Discovered 2026-04-19:
#   embed inference returned spurious BrokenPipe errors when the
#   daemon was launched under cargo-guard.) The bypass returns `{}`
#   so the command runs unmodified.
#
#   Default is GUARDED — new recipes that touch cargo get protected
#   automatically. Recipes confirmed not to touch cargo can be added
#   to BYPASS_JUST_RE.
#
# Reads the PreToolUse JSON payload from stdin. Emits a hookSpecificOutput
# JSON: permissionDecision=deny for nextest, updatedInput.command for
# guarded commands, or `{}` (no-op) otherwise.
#
# Relocatable: CARGO_HOME is <project-root>/.cargo where <project-root> is
# two levels up from this script (.claude/hooks/ → root). Drop this script
# plus cargo-guard.sh into any clone's .claude/hooks/ and register in
# settings.local.json.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CARGO_HOME_PATH="$PROJECT_ROOT/.cargo"
GUARD_SCRIPT="$PROJECT_ROOT/.claude/hooks/cargo-guard.sh"

# Word-boundary match for commands that must be guarded: `cargo` or `just`,
# starting the command or following a shell separator, followed by
# whitespace or end-of-string. Won't match `Cargo.toml`, `cargo-*`,
# `justfile`, or `adjust`.
GUARDED_RE='(^|[;&|[:space:]])(cargo|just)([[:space:]]|$)'
# `just` recipes that NEVER invoke cargo — bypass the guard entirely so
# their stderr is not polluted by the 30s heartbeat. Matched as
# `just <recipe>` where recipe is a known-non-cargo name. Anything not
# in this list defaults to GUARDED (safe fail). Update when adding new
# non-cargo recipes to justfile.
BYPASS_JUST_RE='(^|[;&|[:space:]])just[[:space:]]+(ui-[a-z-]+|daemon-[a-z-]+|warmup|client|tmux|otel|playtest|playtest-scenario|scene-list|status|sync-claude-md)([[:space:]]|$)'
# Nextest detection: matches `cargo nextest ...` and bare `nextest ...`
# in any shell-separator position. Banned regardless of entry point
# because the XProtect deadlock is architectural, not a cargo subcommand
# problem — running `nextest` directly would deadlock identically.
NEXTEST_RE='(^|[;&|[:space:]])(cargo[[:space:]]+)?nextest([[:space:]]|$)'

jq -c \
  --arg cargo_home "$CARGO_HOME_PATH" \
  --arg guard "$GUARD_SCRIPT" \
  --arg cargo_re "$GUARDED_RE" \
  --arg bypass_re "$BYPASS_JUST_RE" \
  --arg nextest_re "$NEXTEST_RE" '
  (.tool_input.command // "") as $cmd
  | if ($cmd | test($nextest_re)) then
      {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: (
            "cargo nextest is forbidden on this workspace.\n" +
            "Reason: macOS XProtectService (malware scanner) runs single-threaded " +
            "and scans every freshly-linked binary on exec. nextest'\''s parallel " +
            "--list test-discovery spawns 35+ binaries at once, all queue behind " +
            "XprotectService, and the resulting XPC contention deadlocks nextest " +
            "(parked in tokio condvar, zero CPU, never completes). Confirmed in " +
            "Nicholas Nethercote'\''s Sept 2025 analysis and nextest'\''s own macOS " +
            "docs. Serial `cargo test` avoids the deadlock (still slow per-binary " +
            "due to XProtect but progresses).\n" +
            "Use `cargo test`. Alias `cargo t` points at `cargo test`. Full suite: " +
            "`just api-test`. See memory feedback_use_nextest.md."
          )
        }
      }
    elif ($cmd | test($bypass_re)) then
      # Non-cargo just recipe (ui-*, daemon-*, etc.) — let it run unwrapped.
      # The 30s heartbeat would interfere with long-running services that
      # use stderr as a live log stream.
      {}
    elif ($cmd | test($cargo_re)) then
      {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          updatedInput: {
            command: (
              "export RUSTC_WRAPPER=\"\" CARGO_HOME=" + $cargo_home + "; " +
              "export CARGO_GUARD_CMD_B64=" +
              ($cmd | @base64 | @sh) + "; " +
              "bash " + ($guard | @sh)
            )
          }
        }
      }
    else
      {}
    end
'
