# Handoff: implement -> review
**Story:** 61-4  |  **Agent:** dev  |  **Timestamp:** 2026-05-23

## Summary

Made all 14 RED tests green across two repos with minimal implementation.
Server side: per-instance rolling-baseline cost-runaway fingerprint
detector in `AnthropicSdkClient.complete_with_tools` that emits a
`cost_runaway_suspected` watcher event + ERROR log when either trigger
fires (cost > 5x baseline OR input > 2x baseline AND output < 50).
Orchestrator side: `preflight_cost_check` (worst-case projection,
operator-actionable refusal) and `write_meta_sidecar` (SDK-replay
annotation, schema v1) on `scripts/playtest.py`, with the preflight
wired into `amain` so the production path is actually guarded.

## Deliverables

- `sidequest-server/sidequest/agents/anthropic_sdk_client.py` — added
  module-level constants (window K=10, warmup floors $0.03 / 12_000,
  trigger multiples), `deque` baselines on `__init__`, alarm check call
  in the per-iter usage path, and `_maybe_emit_cost_runaway` method.
  Commit `74fc4c9`.
- `scripts/playtest.py` — added preflight + sidecar functions,
  `--max-projected-cost-usd` (default 0.50) + `--confirm-cost` flags,
  preflight call in `amain` (skipped in fixture mode). Commit `8c4c841`.

## Key Decisions

- **Per-instance baseline scoping** — verified via `app.py:104` that
  `claude_client_factory` returns a fresh client per session; per-instance
  `deque` is per-session by construction. No session-id keying needed.
- **Sidecar is callable-only (no producer)** — RED test calls
  `write_meta_sidecar(dump_path)` directly with a synthesized fixture.
  Future capture paths invoke the writer.
- **Both-triggers collapse to `io_fingerprint`** — kept TEA's design
  deviation (sibling shape to 61-3's single-event taxonomy).
- **Component label = `narrator.sdk`** (not `orchestrator`) — alarm fires
  from inside the SDK client, distinguishing from 61-3's emit.
- **Preflight wired into `amain`** — returns exit 2 on refuse (matching
  existing `ScenarioError` exit code). Skipped in `--fixture` mode.

## Open Questions

None remaining. All four TEA-handoff questions are resolved in the
session file's `## Green phase > ### Open question resolutions`.

## Test Status

- Server: 8/8 passing (`tests/agents/test_61_4_cost_runaway_alarm.py`).
- Orchestrator: 6/6 passing (`scripts/tests/test_61_4_playtest_cost_guard.py`).
- Full server suite: 7275 passed, 400 skipped — no regressions.
- Pre-existing orchestrator-test failures (`test_claude_tab.py`,
  `test_playtest_split.py`) are function-name drift from prior refactors,
  unrelated to 61-4 — not touched.
- Lint: `ruff check` clean on both files; `just server-fmt` deliberately
  not run (PR #387 owns the format-drift wave).
