#!/usr/bin/env bash
# PreToolUse(Bash) hook for cargo commands on this clone.
#
# Three jobs:
#
#   1. Inject env vars — every cargo invocation gets
#      `RUSTC_WRAPPER="" CARGO_HOME=<this-clone>/.cargo` prepended so this
#      clone has its own cargo registry and bypasses sccache (avoiding
#      cross-clone contention with other checkouts of the same project).
#
#   2. Deny `cargo nextest` — nextest's parallel --list test-discovery
#      deadlocks under macOS code-signing verification (amfid/syspolicyd
#      serialize parallel binary-verification XPC calls). `cargo test` is
#      the only safe runner on this workspace. See memory:
#      feedback_use_nextest.md. Hook returns a permissionDecision=deny so
#      the agent cannot bypass it and sees the reason.
#
#   3. Wrap all other cargo commands through cargo-guard.sh, which
#      adds a flock (serializes cargo invocations, so two concurrent
#      `cargo test` calls queue instead of racing), a 30s heartbeat to
#      defeat the 2-minute stream auto-background, and pipefail so
#      `cargo test | tail` can't mask cargo's real exit code.
#
# Reads the PreToolUse JSON payload from stdin. Emits a hookSpecificOutput
# JSON: permissionDecision=deny for nextest, updatedInput.command for
# other cargo commands, or `{}` (no-op) when not a cargo command.
#
# Relocatable: CARGO_HOME is <project-root>/.cargo where <project-root> is
# two levels up from this script (.claude/hooks/ → root). Drop this script
# plus cargo-guard.sh into any clone's .claude/hooks/ and register in
# settings.local.json.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CARGO_HOME_PATH="$PROJECT_ROOT/.cargo"
GUARD_SCRIPT="$PROJECT_ROOT/.claude/hooks/cargo-guard.sh"

# Word-boundary cargo match: must start the command or follow a shell
# separator, and be followed by whitespace or end-of-string. Won't match
# `Cargo.toml` or `cargo-related-tool`.
CARGO_RE='(^|[;&|[:space:]])cargo([[:space:]]|$)'
# Explicit nextest detection: `cargo nextest ...` in any shell-separator
# position. Matches `cargo nextest run` and `cargo nextest list` alike.
NEXTEST_RE='(^|[;&|[:space:]])cargo[[:space:]]+nextest([[:space:]]|$)'

jq -c \
  --arg cargo_home "$CARGO_HOME_PATH" \
  --arg guard "$GUARD_SCRIPT" \
  --arg cargo_re "$CARGO_RE" \
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
