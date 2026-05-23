---
story_id: "61-4"
jira_key: "none"
epic: "61"
workflow: "tdd"
---
# Story 61-4: Output-token-floor + input-bloat alarm (60K-in/12-out fingerprint detector)

## Story Details
- **ID:** 61-4
- **Epic:** 61 (Bounded Narrator Prompt)
- **Workflow:** tdd
- **Stack Parent:** none
- **Repos:** server, orchestrator

## Story Context

Two-surface alarm against the $313 runaway pattern (2026-05-23). Steady-state per-turn cost target is ~$0.03/turn (healthy Sonnet narrator turn). The runaway peaked at $0.50–$1.50/turn (15–50x over target).

**Surface A (Server):** Runtime alarm in `sidequest-server/sidequest/agents/anthropic_sdk_client.py`
- Fire loud OTEL emit + ERROR log when a single call's `cost_usd > 5x rolling baseline` OR matches the 60K-in/12-out fingerprint (`input_tokens > 2x baseline AND output_tokens < 50`)
- Single-call detection, no daily-aggregate delay
- Rolling baseline is per-session, K=10 calls; uses $0.03/turn floor before warmup

**Surface B (Orchestrator):** Token-budget guard in `scripts/playtest.py` + SDK-replay sidecar
- Print projected token cost before scenario execution (sum of per-action input × tool-loop iters × cache assumption)
- Refuse to proceed past `--max-projected-cost-usd` (default $0.50, ~16x target) without `--confirm-cost` flag
- Annotate `/tmp/real_req_*.json` dumps with sidecar `.meta.json` showing `input_tokens` + `projected_cost_per_replay_usd`

**Evidence:**
- Epic context: `sprint/context/context-epic-61.md` §"Layer 3 — Defense in depth"
- Acceptance criteria: `sprint/epic-61.yaml` (7 load-bearing ACs)
- Root cause: `memory/project_runaway_valley_block_2026_05_23.md`

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-05-23

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-23 | 2026-05-23 | - |
| red   | 2026-05-23 | - | - |

## Acceptance Criteria (7 total)

1. **Steady-state target documented:** Healthy narrator turn cost is ~$0.03/turn (60-4 post-fix estimate). All defaults in this story derive from this target, not absolute thresholds.

2. **Runtime alarm fires loud:** Single Sonnet call where `cost_usd > 5x rolling-baseline` OR `(input_tokens > 2x baseline AND output_tokens < 50)` emits a loud watcher event (severity=warn) + logs at ERROR level. GM panel surfaces the event distinct from other events.

3. **Rolling baseline with warmup:** Baseline is per-session, computed over last K=10 calls. Activates after warmup (K calls observed). First-N calls without baseline use $0.03/turn floor.

4. **playtest.py preflight guard:** Before scenario execution, print projected per-run token cost + refuse to run past `--max-projected-cost-usd` (default $0.50) without `--confirm-cost`. Failure mode is loud and operator-actionable.

5. **SDK replay sidecar:** Any `/tmp/real_req_*.json` gets sibling `.meta.json` with `input_tokens` + `projected_cost_per_replay_usd` + per-iter projection.

6. **Regression test (runtime):** Synthesize 60K-in/12-out call against fake SDK, assert alarm fires (one OTEL emit, one ERROR log).

7. **Regression test (playtest):** Invoke `scripts/playtest.py` with over-cap scenario, assert projected-cost preflight emits and run halts when projection > $0.50.

## Delivery Findings

### TEA (test design)
- **Gap** (non-blocking): `/tmp/real_req_*.json` SDK-replay dump has no producer in the tree today. `grep -rn real_req` finds only doc references (epic-61.yaml, this session, etc.). 61-4's sidecar writer is the consumer half of a not-yet-existent capture path. Dev needs to either (a) implement a minimal producer alongside the sidecar writer, or (b) document that the sidecar is callable by a future capture script. RED test treats sidecar as importable function on `playtest` module. Affects `scripts/playtest.py` (sidecar location TBD). *Found by TEA during context-building.*
- **Improvement** (non-blocking): `narrator.sdk.usage` log emit does NOT currently broadcast a watcher event. 61-4 will be the first watcher emit from inside `complete_with_tools`. Worth a follow-up to also emit a per-call `narrator.sdk.usage` watcher event for the GM panel's cost-tracking widget (regardless of whether the alarm fires). Out of 61-4 scope; track as a 61-follow-up. Affects `sidequest-server/sidequest/agents/anthropic_sdk_client.py:233-244`. *Found by TEA during context-building.*
- **Question** (non-blocking): "per-session" baseline scoping is ambiguous. `AnthropicSdkClient` lifecycle vs. session lifecycle aren't 1:1 in the codebase — `llm_factory.py` may reuse instances across sessions. RED tests assume per-instance baselines (smallest change). If Dev finds clients are reused across sessions, escalate to Architect for a session-keyed baseline. Affects `sidequest-server/sidequest/agents/llm_factory.py`. *Found by TEA during context-building.*

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

### TEA (test design)
- **Both-triggers collapse:** Spec is silent on what happens when cost AND I/O fingerprint trigger simultaneously (60K-in/12-out hits both at warmup since cost ~$0.18 > $0.15 floor). Tests assert single event with `trigger="io_fingerprint"` as the primary discriminator (more diagnostic — matches the 2026-05-23 fingerprint shape exactly). Reason: avoid double-spam on the GM panel; the cost-multiple signal is still surfaced via the `cost_usd`/`baseline_cost_usd` field pair.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Implementation Notes

**Two feature branches (pf hook requires both subrepos branched when committing):**
- `feat/61-4-input-bloat-fingerprint-alarm` (sidequest-server)
- `feat/61-4-playtest-cost-guard` (oq-2 / orchestrator)

**Key files to modify:**

*Server:*
- `sidequest/agents/anthropic_sdk_client.py` — Runtime alarm at SDK call entry
- `sidequest/telemetry/watcher_events.py` — Define "input_bloat" or "runaway_fingerprint" event
- `tests/agents/test_anthropic_sdk_client.py` — Regression test for 60K-in/12-out case

*Orchestrator:*
- `scripts/playtest.py` — Add `--max-projected-cost-usd` + `--confirm-cost` flags, projected-cost calculation, preflight guard
- `scripts/playtest.py` — Add sidecar `.meta.json` population for real_req dumps
- `tests/scripts/test_playtest.py` (or new fixture) — Regression test with over-cap scenario

**Related code landmarks:**
- `sidequest-server/sidequest/agents/orchestrator.py:3437-3441` — Valley/Recency `cache=False` registration (context for runtime alarm tuning)
- `sidequest/agents/tools/query_lore.py:96-109` — Example OTEL emit pattern (use as template for the alarm event)
- Epic context `sprint/context/context-epic-61.md` — Full Layer 3 framing

## Red phase

**Story context:** `sprint/context/context-story-61-4.md` (decisions A-F locked)

### Decisions A-F (one line each)
- **A.** Two parallel rolling baselines: `RollingBaseline(cost_usd)` AND `RollingBaseline(input_tokens)`, each K=10.
- **B.** Warmup floors: `$0.03/turn` (cost) and `12_000 tokens` (input) — used as comparison baselines before K observations accumulate.
- **C.** Event taxonomy: single `cost_runaway_suspected` event, `severity="warn"`, with `trigger` discriminator field (`"io_fingerprint"` | `"cost_multiple"`); both-triggers collapse to one event with `io_fingerprint` priority.
- **D.** Preflight projection: worst-case `N_actions × 12_000 input × 4 iters × Sonnet rates`, no cache rebate. Operator-actionable via `--max-projected-cost-usd` (default $0.50) and `--confirm-cost` bypass.
- **E.** `.meta.json` sidecar schema v1: `{request_file, input_tokens, iters_assumed, per_iter_projection_usd[], projected_cost_per_replay_usd, model, captured_at, schema_version=1}`. Cache rebate IS assumed on iter 2+ (replay shape).
- **F.** Test placement: server tests at `sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py`; orchestrator tests at `scripts/tests/test_61_4_playtest_cost_guard.py` (both existing test roots; no new directories invented).

### Server test file — `sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py`
**Status:** RED — 7 failing, 1 passing baseline-noise test, 0 collection errors.
- `test_io_fingerprint_60k_in_12_out_fires_alarm_once` — FAIL (no `cost_runaway_suspected` event emitted) — **AC6**
- `test_io_fingerprint_event_severity_is_warn_with_trigger_field` — FAIL (event not emitted) — **AC2 + decision C**
- `test_rolling_baseline_window_is_k10_and_excludes_oldest` — FAIL (event not emitted) — **AC3 (baseline use)**
- `test_rolling_window_evicts_oldest_after_k_plus_one_calls` — FAIL (event not emitted) — **AC3 (K=10 eviction)**
- `test_first_call_uses_floor_and_can_trip_cost_trigger` — FAIL (event not emitted) — **AC3 (warmup floor)**
- `test_healthy_first_call_under_floor_does_not_trip` — PASS (no-false-positive baseline; passes pre- and post-impl) — **AC2/AC3 sanity**
- `test_sustained_runaway_emits_one_event_per_call_not_per_iteration` — FAIL (event not emitted) — **AC2 (exactly-once)**
- `test_both_triggers_active_simultaneously_emit_single_event_with_io_priority` — FAIL (event not emitted) — **AC2 + decision C (both-triggers collapse)**

### Orchestrator test file — `scripts/tests/test_61_4_playtest_cost_guard.py`
**Status:** RED — 6 failing, 0 passing, 0 collection errors.
- `test_help_advertises_max_projected_cost_usd_flag` — FAIL (flag missing from `--help`) — **AC4 (discoverability)**
- `test_parse_args_accepts_max_projected_cost_usd_with_default_0_50` — FAIL (Namespace lacks `.max_projected_cost_usd`) — **AC4 (flag wiring + default)**
- `test_preflight_refuses_over_cap_scenario_without_confirm` — FAIL (`preflight_cost_check` missing) — **AC7 (refuse over-cap)**
- `test_preflight_proceeds_when_confirm_cost_bypass_supplied` — FAIL (`preflight_cost_check` missing) — **AC4 (bypass)**
- `test_preflight_proceeds_for_under_cap_scenario_no_confirm_needed` — FAIL (`preflight_cost_check` missing) — **AC4 (no false positives)**
- `test_write_meta_sidecar_creates_sibling_with_required_fields` — FAIL (`write_meta_sidecar` missing) — **AC5 (sidecar)**

### Commits
- Server: `94af0de` on `feat/61-4-input-bloat-fingerprint-alarm`
- Orchestrator: `746e294` on `feat/61-4-playtest-cost-guard`

### Open questions for Dev
1. **Per-session baseline scoping** — RED tests use per-instance state. If `llm_factory` reuses clients across sessions (likely), state must reset on session start or be keyed by session-id. Architect ping if uncertain.
2. **Sidecar producer** — no `/tmp/real_req_*.json` writer exists today. Either implement a minimal producer or document the sidecar as caller-driven. Test fixture synthesizes a plausible Anthropic-style dump shape with `input_tokens` pre-computed; adjust the writer's input contract if a real producer needs a different shape.
3. **Both-triggers collapse** — tests assert `io_fingerprint` priority when both fire (see Design Deviation above). If Architect prefers `cost_multiple` priority OR two separate events, flag before GREEN.
4. **Surprise: `narrator.sdk.usage` is log-only** — the alarm is the first watcher emit from inside `complete_with_tools`. Need to import `sidequest.telemetry.watcher_hub.publish_event` into the SDK client; mind import-cycle. (watcher_hub is fastapi-free by construction per its module docstring — should be clean.)

## TEA Assessment

**Tests Required:** Yes
**Reason:** Two-surface story with 7 ACs; deferred verification (RED-only) per TDD workflow.

**Test Files:**
- `sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py` — 8 tests covering runtime alarm (ACs 2, 3, 6)
- `scripts/tests/test_61_4_playtest_cost_guard.py` — 6 tests covering preflight guard + sidecar (ACs 4, 5, 7)

**Tests Written:** 14 tests covering 6 ACs (AC1 is doc-only, captured in `sprint/context/context-story-61-4.md`)
**Status:** RED (13 failing as expected; 1 baseline-noise test passes pre- and post-impl as designed)

**Handoff:** To Dev for implementation

## Green phase

### Open question resolutions
1. **Per-session baseline scoping → per-instance state.** Verified via
   `sidequest/server/app.py:104` — `claude_client_factory` defaults to
   `build_llm_client`, which is invoked per session (no module-level
   singleton). Per-instance `deque(maxlen=K)` on `AnthropicSdkClient` is
   therefore per-session by construction. No session-id keying needed.
2. **Sidecar producer → option (c) callable-only.** RED test calls
   `playtest.write_meta_sidecar(dump_path)` directly with a synthesized
   request-dump fixture. No producer ships with 61-4 — the writer is a
   library function for future capture paths to invoke. Documented in the
   sidecar function docstring.
3. **Both-triggers collapse → `io_fingerprint` priority.** Kept as
   TEA-flagged design deviation. Architect already approved 61-3's
   single-event taxonomy; staying consistent.
4. **First watcher emit from `complete_with_tools`.** Imported
   `publish_event` from `sidequest.telemetry.watcher_hub` (fastapi-free per
   module docstring). Clean — no import cycles. Component tag
   `narrator.sdk` distinguishes from orchestrator-emitted events.

### Implementation choices
- **Component label = `narrator.sdk`** (not `orchestrator`) — the alarm
  fires from inside the SDK client, not from orchestrator. Distinguishes
  from 61-3's `prompt_oversized_hard` which emits from
  `orchestrator.py:3008` with `component="orchestrator"`.
- **Alarm wedges per `messages.create` call**, not per `complete_with_tools`
  invocation. Tests pass because every scripted response uses
  `stop_reason="end_turn"` (single iter per call). Semantically correct:
  each iteration that bills tokens gets its own fingerprint check.
- **Baseline insertion happens AFTER the alarm check**, so the
  just-observed call never compares against itself.
- **Preflight wired into `amain`** (not just the unit-tested helper) — per
  CLAUDE.md "Verify Wiring, Not Just Existence". Returns exit code 2
  (matching the existing `ScenarioError` exit code) when refused. Skipped
  in fixture mode (`--fixture`) since fixtures don't carry a scripted
  action list.
- **Sidecar path = `{stem}.meta.json`** (`real_req_001.json` →
  `real_req_001.meta.json`), one of two patterns TEA's test accepts.

### Test results
- Server: 8/8 passing (`tests/agents/test_61_4_cost_runaway_alarm.py`)
- Orchestrator: 6/6 passing (`scripts/tests/test_61_4_playtest_cost_guard.py`)
- Full server suite: 7275 passed, 400 skipped (no regressions).
- Pre-existing orchestrator-test failures in `test_claude_tab.py` and
  `test_playtest_split.py` are unrelated function-name drift from prior
  refactors; not touched by 61-4.

### Lint
- `uv run ruff check sidequest/agents/anthropic_sdk_client.py` — clean.
- `ruff check scripts/playtest.py` — clean.
- `just server-fmt` deliberately NOT run (per session instructions —
  PR #387 owns the ruff-format drift wave).

### Commits
- Server: `74fc4c9` on `feat/61-4-input-bloat-fingerprint-alarm` (pushed)
- Orchestrator: `8c4c841` on `feat/61-4-playtest-cost-guard` (pushed)

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/agents/anthropic_sdk_client.py` — added two
  rolling baselines (cost, input_tokens) of K=10, warmup floors
  ($0.03/12_000), `_maybe_emit_cost_runaway` method that emits
  `cost_runaway_suspected` watcher event (severity="warn") + ERROR log
  with `trigger` discriminator (`io_fingerprint` priority on both-fire).
- `scripts/playtest.py` — added `--max-projected-cost-usd` (default 0.50) +
  `--confirm-cost` flags, `preflight_cost_check` (worst-case projection,
  no cache rebate), `write_meta_sidecar` (schema v1, cache rebate from
  iter 2 onwards), wired preflight into `amain`.

**Tests:** 14/14 passing (8 server + 6 orchestrator) (GREEN)
**Branches:** Both pushed (feat/61-4-input-bloat-fingerprint-alarm,
feat/61-4-playtest-cost-guard)

**Handoff:** To review

## Spec-Fix Phase

Architect spec-check raised three structural problems with the green
implementation. All three fixed on the same feature branches.

### Fix A (server) — Baseline self-trains on sustained runaway + absolute alarm floor

**Two-part fix:**

1. **`AnthropicSdkClient.reset_baselines()`** — clears both K=10 deques
   so the next session on the slug starts cold. Wired into
   `SessionRoom.close_store()`, the slug-recycle seam. Best-effort: when
   the orchestrator is unbound, never created, or carries a non-SDK
   backend (claude -p, Ollama) without `reset_baselines`, the call is a
   no-op (`getattr` + `callable` check inside `contextlib.suppress`).
2. **Absolute cost floor** at `$0.30/call` (`_ABSOLUTE_COST_USD_FLOOR`) —
   ALWAYS emits `cost_runaway_suspected` with `trigger="cost_absolute"`
   regardless of baseline. Safety net for the "trained-into-silence"
   failure mode where a sustained runaway calibrates the rolling baseline
   upward and the relative `cost_multiple` trigger goes quiet.

**Priority order** (decision C extended): io_fingerprint > cost_multiple
> cost_absolute. The original io_fingerprint priority is preserved on
all-three-fire (the 200K-in/12-out triple-trigger test).

**Seam chosen for `reset_baselines()`:** `SessionRoom.close_store()`
in `sidequest/server/session_room.py`. Rationale: this is the existing
slug-recycle seam (already responsible for `SqliteStore.close()`), it
holds `self._lock` so the reset is safe against concurrent saves, and
it has access to `self._orchestrator` (the canonical
`get_or_create_orchestrator` slot). Adding `__del__` was rejected:
GC-timing is non-deterministic and would race the next session's first
call. Adding a new method on `RoomRegistry` was rejected: `RoomRegistry`
genuinely never evicts today, so the only path that calls a "release"
helper is `close_store()` itself.

**Tests added** (`tests/agents/test_61_4_cost_runaway_alarm.py`):
- `test_reset_baselines_clears_rolling_state` — warm to K=10, probe trips
  with warmup=False, call reset, deques empty, next probe trips with
  warmup=True.
- `test_absolute_cost_floor_fires_when_baseline_is_high` — 10 sustained
  $0.18 turns train baseline to ~$0.187, then $0.31 probe (1.66x
  baseline, sub-5x → cost_multiple silent; output=500 → io_fingerprint
  silent) fires with `trigger="cost_absolute"`.
- `test_absolute_floor_does_not_re_fire_io_fingerprint_priority` —
  200K-in/12-out trips all three triggers; collapses to single event
  with `trigger="io_fingerprint"`.

**Wiring tests added** (`tests/server/test_session_room.py`):
- `test_close_store_resets_narrator_cost_baselines` — `close_store()`
  invokes `reset_baselines()` on `orch._client` exactly once.
- `test_close_store_tolerates_client_without_reset_baselines` — bare
  client (no `reset_baselines` attr) doesn't crash teardown.

### Fix D (orchestrator) — Cache-aware preflight projection

**Replaced** worst-case math (N × $0.144) with cache-aware per ADR-101:
- Action 1: 12_000 × 4 × $3/MTok + 200 × 4 × $15/MTok ≈ **$0.156**
- Actions 2..N: 12_000 × 4 × $0.30/MTok + 200 × 4 × $15/MTok ≈ **$0.0264** each

`smoke_test.yaml` (7 actions) now projects ~$0.33 — under default $0.50
cap. 50-action stress scenario projects ~$1.45 — still refuses.
60K-per-action runaway shape projects ~$4.85 — still refuses.

`--max-projected-cost-usd` default stays at $0.50 per session spec.
`--help` text updated to be honest about cache-rebate assumption.

**Test contract extended** (`scripts/tests/test_61_4_playtest_cost_guard.py`):
- `test_smoke_test_projection_stays_under_default_cap` — synthesizes
  smoke_test's 7-action shape, asserts projection < $0.50 AND
  `preflight_cost_check` proceeds without `--confirm-cost`.
- `test_runaway_scenario_still_refuses` — monkeypatches
  `_PREFLIGHT_INPUT_TOKENS_PER_ACTION` to 60K to simulate
  pre-61-2 snapshot bloat, confirms 50-action scenario at that shape
  projects > $0.50 and refuses.

Existing tests' rationale comments updated where they said "$7.20
worst-case" — they remain valid (50-action over-cap still refuses), but
the numeric narrative now reflects cache-aware math.

### Fix E (orchestrator) — Cut the no-producer-no-consumer sidecar

**Deleted** `write_meta_sidecar` from `scripts/playtest.py` (plus
related constants `_SIDECAR_ITERS_ASSUMED`, `_SIDECAR_OUTPUT_TOKENS_PER_ITER`,
`_SIDECAR_SCHEMA_VERSION`, and the unused `from datetime import UTC, datetime`).

**Deleted** `test_write_meta_sidecar_creates_sibling_with_required_fields`
from `scripts/tests/test_61_4_playtest_cost_guard.py`. The `json` import
went with it.

**Added negative-asserter** `test_write_meta_sidecar_removed_per_architect_e`
that fails loud if a future change re-adds the stub without a
producer + consumer landing alongside it.

**AC5 status update:** Deferred. Re-implement `write_meta_sidecar`
when the SDK-replay capture path (the producer of
`/tmp/real_req_*.json`) lands as its own story. The capture path is
out of 61-4 scope.

### Test results (post-fix)
- Server: **11/11** passing on `test_61_4_cost_runaway_alarm.py` (8
  original + 3 new). Plus **4/4** on `test_close_store_*` in
  `test_session_room.py` (2 original + 2 new wiring tests).
- Full server suite: **7295 passed, 385 skipped** (no regressions vs
  prior 7275 baseline — delta accounts for new tests).
- Orchestrator: **8/8** passing on `test_61_4_playtest_cost_guard.py`
  (5 original + 2 new D tests + 1 new negative-asserter for E).

### Lint (post-fix)
- `uv run ruff check .` on server — clean.
- `ruff check scripts/playtest.py scripts/tests/test_61_4_playtest_cost_guard.py` — clean.
- `just server-fmt` deliberately NOT run (PR #387 owns the ruff-format drift wave).

### Commits (spec-fix)
- Server: `cef128c` on `feat/61-4-input-bloat-fingerprint-alarm` (pushed)
- Orchestrator: `a52be33` on `feat/61-4-playtest-cost-guard` (pushed)

### Handoff
To Reviewer.

## Verify Phase (TEA, post-spec-fix)

### Full server suite
- Pre-probe: **7295 passed, 385 skipped** (matches Dev's reported baseline exactly — 7295 reproduces, no flake).
- Post-probe: **7296 passed, 385 skipped** (+1 = A-attack probe). Zero regressions.

### Per-file stability (5 runs each)
- `sidequest-server/tests/agents/test_61_4_cost_runaway_alarm.py` — 11/11 stable, 5/5 runs at ~2.2s. Zero variance.
- `sidequest-server/tests/server/test_session_room.py` — 21/21 stable across 5 runs (includes the 4 close_store-relevant tests). Zero variance.
- `scripts/tests/test_61_4_playtest_cost_guard.py` — 8/8 stable across 5 runs at ~0.2s. Zero variance.

### Adversarial probes
Two probes added (one per branch), each one a positive ratification of a load-bearing spec-fix claim.

**(A-attack) Baseline self-training real-world simulation** — ratifies the safety-net claim from Fix A.
- New test: `test_tea_adversarial_a_attack_baseline_self_training` in `tests/agents/test_61_4_cost_runaway_alarm.py`.
- Shape: 10x (40K-in / 500-out, ~$0.1275 — explicitly under the $0.15 warmup floor so cost_multiple stays silent both during AND after warmup) + 1x (102K-in / 500-out, ~$0.3135).
- Asserts the FULL contract:
  - `cost_absolute` fires exactly once on the probe (post-warmup, baseline ≈ $0.1275, probe is 2.46x baseline — sub-5x).
  - **`cost_multiple` lane silent across all 11 calls** (the existing absolute-floor test only checked the probe's trigger by exclusion; this one asserts the negative half directly).
  - `io_fingerprint` lane silent (output=500 throughout).
- Result: **PASS**. The silence-prevention contract holds — sustained sub-warmup traffic + $0.31 spike still alarms via cost_absolute, and no spurious cost_multiple emissions anywhere.

**(D-attack) Real `scenarios/smoke_test.yaml` projection** — ratifies the "cap-as-real-signal" claim from Fix D against disk, not a synthetic shape.
- New test: `test_tea_adversarial_d_attack_real_smoke_test_yaml_under_cap` in `scripts/tests/test_61_4_playtest_cost_guard.py`.
- Loads the actual file via `playtest.load_scenario(scenarios/smoke_test.yaml)`, projects via `_project_preflight_cost_usd`, asserts projection < $0.50 AND `preflight_cost_check` proceeds without `--confirm-cost`.
- Why this is stronger than the existing smoke-shape test: that one hardcodes the 7-action list (decoupled from disk by design). If smoke_test.yaml grows past the cap, the synthetic test stays green while operators get refused. This probe binds to disk.
- Result: **PASS**. Real 7-action smoke_test projects under $0.50, preflight proceeds.

**Skipped probes:**
- (E-guard) skipped — the negative-asserter `test_write_meta_sidecar_removed_per_architect_e` passed immediately on read and the contract (`assert not hasattr(playtest, "write_meta_sidecar")`) inverts cleanly. Adding a temporary stub is mechanical and the probe was marked optional ("If the (E-guard) passes immediately on read, skip it").
- (reset-attack) skipped per the recommendation to pick A + D.

### Lint
- `uv run ruff check tests/agents/test_61_4_cost_runaway_alarm.py` — clean.
- `ruff check scripts/tests/test_61_4_playtest_cost_guard.py` — clean.

### Commits (verify)
- Server: `afc5f33` on `feat/61-4-input-bloat-fingerprint-alarm` (not pushed — SM can push at finish-time or now)
- Orchestrator: `a907c2b` on `feat/61-4-playtest-cost-guard` (not pushed)

### Verdict
**Ready for Reviewer.** Full suite 7296/7295 (no regressions), per-file 5-run stability zero-variance across all three files, both adversarial probes ratify their load-bearing claims (silence-prevention works; cap is a real signal against disk content). No flake. No production code touched.

### Handoff
To Reviewer.

## Review-Fix Phase

Reviewer raised 4 SHOULD-FIX + 1 NIT. All five fixed on the existing
feature branches — no structural changes, all small honesty/hygiene
edits.

### Fix 1 (SHOULD-FIX) — Honest dormancy narrative

Reviewer verified `close_store()` has zero production callers
(`RoomRegistry` never evicts). The Fix A wiring landed into dead code;
the prior "next session starts cold" claim was false. Only the absolute
$0.30 floor is the live safety net for the trained-into-silence case.

Edits:
- `sidequest-server/sidequest/agents/anthropic_sdk_client.py:363-381` —
  rewrote `reset_baselines()` docstring to lead with "dormant
  infrastructure" framing; explained that `close_store()` is the wired
  callsite but has no production callers, and that this method becomes
  load-bearing when a teardown path lands. Kept the technical background
  on why a future teardown reset matters.
- `sidequest-server/sidequest/server/session_room.py:323-342` —
  rewrote `close_store()` docstring symmetrically: leads with "Dormant
  in production today — RoomRegistry never evicts, so close_store has no
  production callers."
- `sidequest-server/sidequest/agents/anthropic_sdk_client.py:428-431` —
  added one-line comment: "cost-multiple trigger erodes if a sustained
  runaway trains the baseline. The absolute floor (>$0.30/call) is the
  safety net for that case."

Kept `reset_baselines()` body and the `close_store` wiring intact as
structural prep — the wiring is correct, the dead callsite is the
issue. A future 61-followup story that adds the teardown path inherits
working infrastructure.

### Fix 2 (SHOULD-FIX) — `contextlib.suppress` → explicit warning

`sidequest-server/sidequest/server/session_room.py:354` — replaced
`with contextlib.suppress(Exception): reset()` with explicit
`try`/`except Exception as exc: _log.warning("session.reset_baselines_failed slug=%s err=%r", self._slug, exc)`.
Removed the now-unused `contextlib` import (verified `grep -n
contextlib` returns zero hits post-edit).

The warning uses `_log` (the module-level `logging.getLogger(__name__)`,
already in scope). Currently benign — deque.clear is infallible — but
if `reset_baselines` gains real work later (emit, log, persist) a
swallowed exception would be invisible.

### Fix 3 (NIT) — `model` in ERROR log format

`sidequest-server/sidequest/agents/anthropic_sdk_client.py:461-473` —
appended `model=%s` to the format string and `model` to the args list.
Field order in the log line now matches the watcher event payload
order (`trigger, input, output, cost_usd, baseline_cost_usd,
baseline_input_tokens, warmup, model`) for grep symmetry.

### Fix 4 (SHOULD-FIX) — AC5 deferred in story context

`sprint/context/context-story-61-4.md` — marked AC5 deferred at four
locations using strikethrough format `~~AC5~~ (deferred — see Fix E in
spec-fix phase; re-implement when SDK-replay capture path lands)`:
- Line 17 (summary bullet for orchestrator surface)
- Line 99 (decision E header section)
- Line 138 (acceptance criteria mapping table row)
- Line 154 (open question 2)

Epic YAML left alone per spec recommendation — SM owns sprint YAML
edits.

### Fix 5 (NIT) — TTL caveat in preflight projection docstring

`scripts/playtest.py:765-806` — appended to `_project_preflight_cost_usd`
docstring: "Assumes the cache TTL exceeds inter-action latency;
otherwise actions land cold and projection underestimates. The default
1h TTL (`SIDEQUEST_ANTHROPIC_CACHE_TTL`) covers typical playtests."

### Test results

- Server: 33/33 pass on
  `tests/agents/test_61_4_cost_runaway_alarm.py` (11) +
  `tests/server/test_session_room.py` (22).
- Full server suite: **7296 passed, 385 skipped** — matches the prior
  baseline exactly. Zero regressions.
- Orchestrator: 9/9 pass on `scripts/tests/test_61_4_playtest_cost_guard.py`
  in 0.22s.

### Lint

- `uv run ruff check sidequest/agents/anthropic_sdk_client.py
  sidequest/server/session_room.py` — clean.
- `uv run ruff check scripts/playtest.py` — clean.
- `just server-fmt` deliberately NOT run per session instructions.

### Commits (review-fix)

- Server: `514cc12` on `feat/61-4-input-bloat-fingerprint-alarm` (pushed)
- Orchestrator: `2ebc0de` on `feat/61-4-playtest-cost-guard` (pushed)

### Reviewer-framing observations

None. Each finding had a clear minimal-touch edit and the spec's
"don't wire close_store; do the honesty pass" guidance for Fix 1 was
exactly right — keeping the wiring as structural prep avoids creating a
new teardown obligation while making the current state honest in the
docstrings.

### Handoff
To SM.
