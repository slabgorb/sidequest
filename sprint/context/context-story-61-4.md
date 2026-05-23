# Story 61-4 Context — Output-token-floor + input-bloat alarm + playtest preflight cost guard

## Summary

Two surfaces, one threat model. The 2026-05-23 $313 runaway burned silently
because (a) no per-call detector noticed a 60K-in/12-out signature being
hammered through 8 tool-loop iterations, and (b) the playtest driver
re-ran the same scenario YAML for hours without ever printing a
projected-cost number. 61-4 wedges both gaps shut.

- **Server surface** (`sidequest-server/sidequest/agents/anthropic_sdk_client.py`):
  per-call runtime alarm next to the existing `narrator.sdk.usage` log
  line. Two trigger conditions, single watcher event with a `trigger`
  field.
- **Orchestrator surface** (`scripts/playtest.py` + SDK-replay sidecar):
  preflight projected-cost print + refuse past `--max-projected-cost-usd`,
  and a `.meta.json` sibling for any `/tmp/real_req_*.json` dump.
  ~~AC5~~ (deferred — see Fix E in spec-fix phase; re-implement when
  SDK-replay capture path lands)

Steady-state target (AC1, load-bearing — every default in this story
derives from it): **~$0.03/turn** (60-4 post-fix Sonnet narrator turn,
healthy shape ~12K input / ~500 output, ratio ~24:1).

## Design decisions (locked in RED)

### A. Two parallel rolling baselines, not one
AC3 says "rolling baseline per-session, K=10 calls." The two AC2 triggers
operate on different quantities — `cost_usd > 5x baseline` needs a
**cost** baseline; `input_tokens > 2x baseline` needs an **input-token**
baseline. We carry both: `RollingBaseline(cost_usd)` and
`RollingBaseline(input_tokens)`, each a fixed-window deque of length
K=10, updated after every successful SDK call.

Rationale: cost and input-tokens diverge at runtime (cache-read hits
collapse cost while leaving input_tokens high), so one baseline cannot
serve both triggers without false positives in the cache-rebate regime.

### B. Warmup floor: $0.03/turn for cost, 12_000 tokens for input
Before K=10 calls have been observed, both triggers compare against a
**fixed floor** instead of an empty deque (no silent fallback to "no
baseline = no alarm").

- Cost trigger floor: **$0.03/turn** (AC1 steady-state target).
- Input-token trigger floor: **12_000 tokens** (~$0.036 at Sonnet input
  rate; the empirically healthy turn shape per 60-4 archive and the
  ~24:1 ratio in epic-61 context).

This means even the **first call** of a session is checked: if `cost_usd
> 5 × $0.03 = $0.15` OR (`input_tokens > 2 × 12_000 = 24_000 AND
output_tokens < 50`), the alarm fires.

### C. Event taxonomy — single `cost_runaway_suspected` event with `trigger` field
Mirroring 61-3's `prompt_oversized_hard` shape but at `severity="warn"`
(AC2 explicit — distinct from 61-3's `error`). One event type with a
`trigger` discriminator field so the GM panel can filter on event name
AND drill into trigger reason.

```json
{
  "event_type": "cost_runaway_suspected",
  "severity": "warn",
  "component": "anthropic_sdk_client",
  "fields": {
    "trigger": "cost_multiple" | "io_fingerprint",
    "input_tokens": int,
    "output_tokens": int,
    "cost_usd": float,
    "baseline_cost_usd": float,
    "baseline_input_tokens": float,
    "warmup": bool,                       // true if baseline is the floor
    "k_observed": int                     // calls observed so far (≤ K=10)
  }
}
```

Log line: `logger.error("narrator.cost_runaway_suspected trigger=%s
input=%d output=%d cost_usd=%.6f baseline_cost=%.6f
baseline_input=%.0f", …)` — `narrator.cost_runaway_suspected` prefix
chosen for grep-discoverability alongside existing
`narrator.sdk.usage` / `narrator.prompt_oversized` lines.

### D. Preflight projection math — worst-case (4 iters × no cache)
Operator-facing conservative projection:
`projected_cost_usd = N_actions × INPUT_TOKENS_PER_ACTION × ITERS_ASSUMED
× per-token-input-rate + small per-iter output budget`

Defaults:
- `INPUT_TOKENS_PER_ACTION = 12_000` (steady-state target, same as B).
- `ITERS_ASSUMED = 4` (between healthy 1-2 and pathological 8).
- `OUTPUT_TOKENS_PER_ITER = 200` (conservative ceiling for healthy turn).
- Model assumed **claude-sonnet-4-6** (production default; AC4 doesn't
  require per-scenario model detection in v1).
- **No cache rebate** assumed (worst-case projection — operator can
  opt-in via `--confirm-cost` if projection too high).

Operator override knobs: `--max-projected-cost-usd` (default $0.50,
~16x target), `--confirm-cost` bypass flag. Both surface in `--help`.

### E. `.meta.json` sidecar schema (locked)

~~AC5~~ (deferred — see Fix E in spec-fix phase; re-implement when SDK-replay capture path lands)
```json
{
  "request_file": "real_req_001.json",
  "input_tokens": 12345,
  "iters_assumed": 4,
  "per_iter_projection_usd": [0.037, 0.012, 0.012, 0.012],
  "projected_cost_per_replay_usd": 0.073,
  "model": "claude-sonnet-4-6",
  "captured_at": "2026-05-23T14:00:00+00:00",
  "schema_version": 1
}
```

- `per_iter_projection_usd[0]` = full input + small output (cold).
- `per_iter_projection_usd[1:]` = cache-read rate input (warm). Cache
  rebate IS assumed here (replay typically runs warm against the same
  prefix; this differs from preflight per D because replay is a tighter
  measurement, not a worst-case operator gate).
- `projected_cost_per_replay_usd = sum(per_iter_projection_usd)`.

### F. Cross-repo test placement
- **Server tests:** `sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py`
  (same convention as `test_61_3_hard_cap_oversized_canary.py`,
  `test_60_4_*.py`).
- **Orchestrator tests:** `scripts/tests/test_61_4_playtest_cost_guard.py`
  (same convention as `test_playtest_fixture_flag.py`, `test_playtest_split.py`).

Both directories exist with sibling tests for the same code areas — no
new test roots invented.

## Acceptance criteria → test mapping

| AC | Test surface |
|----|---|
| 1 (target documented) | This doc + epic-61 context |
| 2 (loud alarm: warn watcher + ERROR log, single emit) | Server tests 1, 2, 5 |
| 3 (rolling baseline K=10, warmup floor) | Server tests 3, 4 |
| 4 (playtest preflight, refuse + bypass) | Orchestrator tests 1, 2, 3 |
| ~~5 (.meta.json sidecar schema)~~ (deferred — see Fix E in spec-fix phase; re-implement when SDK-replay capture path lands) | Orchestrator test 4 |
| 6 (regression: 60K-in/12-out fingerprint) | Server test 1 |
| 7 (regression: playtest over-cap halts) | Orchestrator test 2 |

## Open questions for Dev (RED phase deferrals)

1. **Per-session baseline scoping.** Where does "per-session" live? The
   SDK client is currently process-wide singleton-ish via `llm_factory`.
   Options: (a) attach baseline state to the `AnthropicSdkClient`
   instance and rely on session-scoped client construction; (b) thread
   a session-id into `complete_with_tools`. RED tests assume (a) —
   per-instance state — because it's the smallest change. If Dev finds
   the client is reused across sessions, escalate.

2. **Where exactly the SDK-replay dump is written.** No producer for
   `/tmp/real_req_*.json` exists in the tree today (verified via
   `grep -rn real_req` — only doc references). RED tests treat the
   sidecar-writer as a callable function (`write_meta_sidecar`)
   ~~(deferred — see Fix E in spec-fix phase; re-implement when SDK-replay capture path lands)~~ on the
   playtest module, exercised with a synthetic dump file. Dev wires the
   real producer (which doesn't exist yet) to call this function. If
   the producer turns out to live in `scripts/playtest_otlp.py` or a new
   capture script, the function should be importable from there too.

3. **Whether to suppress alarm during the warmup window.** Spec says
   warmup uses the floor — implying alarm DOES fire during warmup if
   the floor is exceeded. RED tests assert this (warmup-window first
   call with 60K-in/12-out trips the alarm). If Dev/Architect decides
   warmup should be quiet, the `test_first_call_uses_floor_and_can_trip`
   test inverts.

## Surprises uncovered during context-building

- **`narrator.sdk.usage` does NOT currently emit a watcher event** — it
  only `logger.info`s. So the 61-4 alarm is the first watcher emit from
  inside `complete_with_tools`. The `publish_event` helper lives at
  `sidequest.telemetry.watcher_hub.publish_event`; the SDK client does
  not currently import it. New import needed.
- **`/tmp/real_req_*.json` has no producer today.** Doc-referenced
  artifact only. 61-4's sidecar function is the consumer side of a
  not-yet-existent producer (a Dev sequencing concern, not a TEA gap).
- **`scripts/playtest.py` already imports `httpx`** (per `import httpx`
  at line 74), so the import-shim guard in `test_playtest_fixture_flag.py`
  about `ImportError` is now stale for new tests — direct import should
  work.

## References

- Epic context: `sprint/context/context-epic-61.md` §"Layer 3 — Defense
  in depth (61-3, 61-4, 61-5)"
- Acceptance criteria: `sprint/epic-61.yaml` `id: 61-4` (7 ACs verbatim)
- Sibling pattern: `sidequest-server/tests/agents/test_61_3_hard_cap_oversized_canary.py`
- Cost incident: `~/.claude/projects/-Users-slabgorb-Projects-oq-2/memory/project_runaway_valley_block_2026_05_23.md`
- Healthy turn shape source: `sprint/archive/60-4-session.md`
- Fake SDK: `sidequest-server/tests/agents/fakes/fake_anthropic_sdk_client.py`
- SDK-shape fake (raw `sdk.messages.create`): `sidequest-server/tests/agents/test_60_4_continuation_cache_breakpoint.py`
