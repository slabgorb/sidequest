# Handoff: red -> green
**Story:** 61-4  |  **Agent:** tea  |  **Timestamp:** 2026-05-23

## Summary

RED-phase tests landed on both repos for the two-surface 61-4 fingerprint-alarm + playtest-preflight story. Server side: 7 failing + 1 passing baseline test for the runtime alarm in `AnthropicSdkClient.complete_with_tools` (ACs 2, 3, 6). Orchestrator side: 6 failing tests for `scripts/playtest.py` preflight guard + SDK-replay `.meta.json` sidecar (ACs 4, 5, 7). AC1 is doc-only and lives in the story context.

## Deliverables

- `sprint/context/context-story-61-4.md` — decisions A-F locked + AC→test mapping + open questions
- `sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py` — 8 server tests, commit `94af0de` on `feat/61-4-input-bloat-fingerprint-alarm`
- `scripts/tests/test_61_4_playtest_cost_guard.py` — 6 orchestrator tests, commit `746e294` on `feat/61-4-playtest-cost-guard`
- `.session/61-4-session.md` — `## Red phase` section with full test inventory + decisions

## Key Decisions

- **A. Two parallel rolling baselines** (cost + input_tokens, K=10 each) — cost-baseline and input-token-baseline diverge under cache rebate; one baseline can't serve both AC2 triggers.
- **B. Warmup floors $0.03/cost and 12_000 input tokens** — locked from epic-61 AC1 steady-state target + 60-4 healthy turn shape.
- **C. Single `cost_runaway_suspected` event, `severity="warn"`, `trigger` discriminator field** — sibling shape to 61-3's `prompt_oversized_hard` but distinct severity. Both-triggers collapse to one event with `io_fingerprint` priority (decision flagged in Design Deviations).
- **D. Preflight = worst-case projection** — `N × 12_000 × 4 iters × Sonnet rates`, no cache rebate. $0.50 default cap = 16x target = ~3 actions headroom.
- **E. Sidecar schema v1** — cache rebate IS assumed on iter 2+ (replay-shape projection, distinct from preflight's worst-case).
- **F. Tests in existing roots** — `sidequest-server/tests/agents/` + `scripts/tests/`, no new directories.

## Open Questions

1. **Per-session baseline scoping** — RED tests use per-instance state on `AnthropicSdkClient`. If `llm_factory` reuses clients across sessions, Dev must reset on session start OR escalate to Architect for session-id keying.
2. **`/tmp/real_req_*.json` has no producer** — sidecar writer is the consumer half of a not-yet-existent capture path. Dev either ships a minimal producer alongside the writer or documents the sidecar as caller-driven.
3. **Both-triggers collapse priority** — tests assert `io_fingerprint` wins when both fire. If Architect prefers two separate events OR `cost_multiple` priority, flag before GREEN.
4. **First watcher emit from `complete_with_tools`** — `narrator.sdk.usage` is currently log-only. Need to import `sidequest.telemetry.watcher_hub.publish_event` into the SDK client. `watcher_hub` is fastapi-free per its module docstring; should be a clean import.

## Test Status

**Server (sidequest-server):** 7 failed, 1 passed, 0 errored
- `uv run pytest tests/agents/test_61_4_cost_runaway_alarm.py -v`

**Orchestrator (oq-2):** 6 failed, 0 passed, 0 errored
- `python3 -m pytest scripts/tests/test_61_4_playtest_cost_guard.py -v`

All failures are real `AssertionError` / `AttributeError` from missing implementation, not collection errors. RED state clean.
