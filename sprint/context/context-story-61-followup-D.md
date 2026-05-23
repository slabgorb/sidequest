# Story 61-followup-D Context — Trained-into-silence mitigation: baseline ceiling + absolute input floor + session-cumulative hard kill

## Summary

Three mitigations close the structural blind spot in 61-4's fingerprint
detector. The 2026-05-23 annees_folles session ran 11 turns at $0.165/turn
average (5.5× the ~$0.03/turn target) without firing 61-4's
`cost_runaway_suspected` alarm, because the rolling-K=10 baseline trained
upward into the new amplitude regime. 61-4 caught spikes; it did not catch
**ramps**. 61-followup-D adds three orthogonal backstops:

- **(A) Baseline ceiling.** Clamp the rolling baseline used in the
  comparator at a hard ceiling derived from the steady-state target so the
  ratio rule cannot self-train into silence.
- **(B) Absolute `input_tokens` alarm floor.** New trigger condition that
  fires on a single oversized call regardless of baseline AND regardless
  of `output_tokens` (the existing I/O fingerprint already requires
  `output<50`; (B) catches the long-output runaway shape that (A) and the
  I/O fingerprint both miss).
- **(C) Session-cumulative HARD KILL at $10.00.** New per-session
  cumulative cost tracker keyed on `session_id`. When cumulative >
  $10.00, the SDK client raises a typed `AnthropicSdkCostCeilingExceeded`
  exception; the orchestrator catches it, emits a typed
  `session.cost_ceiling_exceeded` watcher event + WebSocket message, and
  refuses subsequent narrator turns for that session. Terminal — no
  fallback, no degraded path. Operator unlock is explicitly **out of
  scope** (story body §C).

Steady-state target (load-bearing — every default below derives from it):
**~$0.03/turn** Sonnet, healthy 12K-in / 500-out shape, ratio ~24:1.
Source: `context-story-61-4.md` §B + `sprint/archive/60-4-session.md`.

## Design decisions (locked in RED)

### A. Baseline ceiling at 3× target ($0.09 / 36K)

`AnthropicSdkClient._maybe_emit_cost_runaway` already maintains two
rolling deques (length K=10) and uses warmup floors before K observations
accumulate. Today (post-warmup) the comparison baselines are
`mean(deque)` — unbounded above. Story decision:

```
baseline_cost  = min(mean(self._cost_baseline),         _BASELINE_COST_CEILING)
baseline_input = min(mean(self._input_tokens_baseline), _BASELINE_INPUT_CEILING)
```

with locked thresholds:

| Constant | Value | Derivation |
|---|---|---|
| `_BASELINE_COST_CEILING` | `0.09` | 3× `_WARMUP_COST_USD_FLOOR` ($0.03) — symmetric with warmup floor |
| `_BASELINE_INPUT_CEILING` | `36_000` | 3× `_WARMUP_INPUT_TOKENS_FLOOR` (12K) — same ratio |

After the clamp, the 5× cost trigger fires no higher than $0.45/call and
the 2× I/O trigger fires no higher than 72K tokens, regardless of how
high the rolling means have drifted. The annees_folles 11-turn ramp at
$0.165/turn would have averaged to $0.165 unclamped (then 5× = $0.825,
silent on $0.18 turn 12). Clamped: baseline_cost = $0.09, 5× = $0.45,
and call 12 at $0.20 trips on cost_multiple — within the trip envelope
the original 61-4 design implied. The 60-7 4×-sustained case is the
specific shape (A) is built to catch.

**Warmup interaction.** Warmup floor and ceiling are intentionally
**equal** today ($0.03 = warmup, $0.09 = 3× warmup ceiling, identical
shape for input). The clamp applies only post-warmup. The existing
`_ABSOLUTE_COST_USD_FLOOR` ($0.30 per-call) trigger added in 61-4
(decision "Architect spec-check A") remains unchanged — (A) is a
**baseline-side** clamp, not another per-call absolute. They compose:
absolute $0.30 catches the single spike, baseline ceiling ensures the
multiplicative rule keeps biting under sustained ramps.

### B. Absolute `input_tokens` alarm floor at 40_000 (new trigger)

New trigger `input_absolute`, fires when `input_tokens >
_ABSOLUTE_INPUT_TOKENS_FLOOR` regardless of baseline AND regardless of
output. Story body specifies "single Sonnet call where `input_tokens >
40000`".

| Constant | Value | Derivation |
|---|---|---|
| `_ABSOLUTE_INPUT_TOKENS_FLOOR` | `40_000` | Story body — "halfway between ~20K healthy steady-state and 60K runaway fingerprint" |

Why this is a **new** trigger and not a refinement of `io_fingerprint`:
the existing I/O fingerprint requires `output_tokens < 50` (the
hammered-with-no-response shape). A 40K-in / 800-out call would slip
past the I/O fingerprint but is still anomalous (3.3× healthy input,
likely indicates snapshot bloat or section misroute). (B) is the
single-call canary for input-side regression independent of output
shape.

Per the existing decision C (single event, `trigger` discriminator),
extend trigger priority order in `_maybe_emit_cost_runaway`:

```
io_fingerprint > input_absolute > cost_multiple > cost_absolute
```

Rationale: `io_fingerprint` is still most diagnostic (matches the
2026-05-23 incident exactly). `input_absolute` slots in next because it
shares the "input-side" diagnostic axis; the two cost triggers are
output-side amplifiers. Adding a fourth `trigger` value to the enum
requires the GM panel to learn it but the event shape (`severity="warn"`,
same field list) is unchanged.

### C. Session-cumulative HARD KILL at $10.00

The structurally new behavior. Three sub-decisions:

**C.1 — Keying on `session_id`, not `AnthropicSdkClient` instance.**
The story body and memory `project_session_id_dropin` are explicit:
cumulative cost lives on `session_id` so a deterministic rejoin
(`/play/{date}-{world}-mp` slug → same session_id → same cumulative
inheritance) does the right thing.

Today `complete_with_tools` has NO `session_id` parameter. Threading it
through is part of this story regardless of whether 61-followup-A
lands first. Architectural seam:

- `orchestrator.py:3663` already has `session_id` in local scope (set
  on the narration.turn span at line 3654). Pass it into
  `complete_with_tools(..., session_id=session_id)`.
- Update `ToolingLlmClient.complete_with_tools` protocol signature
  (`agents/tooling_protocol.py:96`) — add `session_id: str | None =
  None` so non-Anthropic backends (`claude_client.py`, Ollama) don't
  need to implement the tracker.
- Inside `AnthropicSdkClient`, a per-instance `dict[str, float]` maps
  `session_id → cumulative_cost_usd`. `None` session_id bypasses the
  tracker (non-narrator callsites, tests).

**Why not a process-global dict?** Memory `feedback_no_burying_bombs`
+ CLAUDE.md "No silent fallbacks": process-global cumulative leaks
across slugs after the rolling-baseline-pollution mode the
61-followup-A story addresses. Per-instance state stays consistent
with the comment at `anthropic_sdk_client.py:36-37` ("per-instance
state is per-session by construction" — true for the SDK client
because `llm_factory` builds one per slug).

**Why not on `SessionRoom`?** The cumulative is intrinsic to "how much
this client has billed for this session" — the natural home is the SDK
client. `SessionRoom` is the appropriate **consumer** (it'd
`get_cumulative_cost(session_id)` for the live counter UI), not the
owner. Dev may push back on this — see Open Question 1 below.

**C.2 — Hard-kill mechanism: typed exception, not return-value flag.**

```python
class AnthropicSdkCostCeilingExceeded(AnthropicSdkClientError):
    """Session-cumulative cost has exceeded the configured ceiling.
    Terminal: subsequent calls for the same session_id will continue to raise."""
    session_id: str
    cumulative_cost_usd: float
    ceiling_usd: float
```

Why exception, not flag: the story body says "server refuses
subsequent narrator turns" and "no fallback, no silent degraded path."
A return-value flag means every caller has to check it, and a missed
check is a silent fallback. A typed exception forces the orchestrator
to either catch-and-degrade-cleanly or let it propagate to the WS
handler. Sibling pattern: `AnthropicSdkLoopExceeded` at
`anthropic_sdk_client.py:64` (also a terminal "this call cannot
proceed" signal).

The check fires **before** the `messages.create` call (refuse the
billable round-trip), AND the cumulative update happens **after** the
call returns (so the tracker reflects actual billed cost, not
projected). The refusal IS terminal:
`AnthropicSdkClient._check_cost_ceiling(session_id)` simply re-raises
on every subsequent call for the same session_id once the threshold
has been crossed.

Two refusal paths per turn:
1. **At entry (before `messages.create`):** if `cumulative >= ceiling`,
   raise immediately. This is the steady-state refusal path after the
   first kill.
2. **At per-iter check (after each `messages.create` returns and cost
   is computed):** if updating `cumulative` crosses the ceiling, raise
   inside the tool-loop so any partial assistant text is discarded.
   This is the threshold-cross path. Important: the iter that crosses
   the ceiling has already billed Anthropic; we cannot un-bill it. The
   ceiling is a "no further calls" gate, not a "no further tokens"
   gate.

**C.3 — Typed WebSocket message + watcher event.**

Two emit surfaces:

(i) Watcher event `session.cost_ceiling_exceeded` (severity=`"error"`)
fires from the orchestrator catch site. Distinct from
`cost_runaway_suspected` (severity=`"warn"`) so the GM panel filter
chain can route differently — warn → yellow indicator, error → red
banner + audible cue.

```json
{
  "event_type": "session.cost_ceiling_exceeded",
  "severity": "error",
  "component": "narrator.orchestrator",
  "fields": {
    "session_id": "2026-05-23-glenross-mp",
    "cumulative_cost_usd": 10.04,
    "ceiling_usd": 10.0,
    "model": "claude-sonnet-4-6"
  }
}
```

(ii) Typed `SessionEventMessage` over the WS to clients (no new
discriminator if the existing `SESSION_EVENT` shape can carry a
`subtype="cost_ceiling_exceeded"` field — verify in
`protocol/messages.py:883`; if not, add a new typed message type per
ADR-038 convention). The UI side renders the operator-facing error in
the GM panel + on each player's screen ("This session has reached its
cost ceiling and cannot continue.").

(iii) Per-turn `session.cost_running_total` watcher event (severity=
`"info"`) emitted **on every successful narrator turn** so the GM
panel has continuous data for the live counter (running $X.XX /
$10.00). Story body specifies "ride 61-followup-B watcher event if
landed, otherwise emit dedicated `session.cost_running_total`." Since
B isn't landed, emit dedicated here. **Wiring test requirement (story
body §Testing):** this fires every turn, not just at threshold-cross
— the dual-lie-detector pairing with 60-7's
`narrator.cache.both_writes_fired`.

```json
{
  "event_type": "session.cost_running_total",
  "severity": "info",
  "component": "narrator.orchestrator",
  "fields": {
    "session_id": "...",
    "cumulative_cost_usd": 1.27,
    "ceiling_usd": 10.0,
    "fraction_used": 0.127,
    "model": "claude-sonnet-4-6"
  }
}
```

### D. Ceiling configuration knob

`_SESSION_COST_CEILING_USD: float = 10.0` module-level constant,
overridable via `SIDEQUEST_SESSION_COST_CEILING_USD` env var (mirrors
the `SIDEQUEST_ANTHROPIC_CACHE_TTL` pattern at
`anthropic_sdk_client.py:113`). The manual-playtest closure step
artificially lowers this to $0.50 to validate end-to-end termination
without running up a real bill — so the env var must work, not just
the constant.

| Constant | Value | Env var |
|---|---|---|
| `_SESSION_COST_CEILING_USD` | `10.0` | `SIDEQUEST_SESSION_COST_CEILING_USD` |

Validation: env var must parse as a positive float, else raise
`AnthropicSdkConfigError` at construction (same pattern as the cache
TTL validation at line 115). No silent fallback to default.

### E. Test placement

| Surface | Path | Sibling |
|---|---|---|
| Server unit | `sidequest-server/tests/agents/test_61_followup_D_*.py` | `test_61_4_cost_runaway_alarm.py` |
| Orchestrator wiring | `sidequest-server/tests/server/test_61_followup_D_orchestrator_kill_wiring.py` | `test_location_description_emit.py` (fixture-driven behavior, per CLAUDE.md "No Source-Text Wiring Tests") |
| WS message | `sidequest-server/tests/server/test_61_followup_D_session_cost_message.py` | (whichever 61-3 / 61-4 file dispatches typed messages) |
| Live integration | `sidequest-server/tests/server/test_61_followup_D_hard_kill_live.py` | 60-7 closure tests (whatever pattern they used — check `sprint/archive/60-7-session.md`) |

Splitting the suite this way lets the unit tests use the SDK-shape
fake (`_Sdk` / `_Resp` / `_FakeSocket` from
`test_61_4_cost_runaway_alarm.py:58-176`) for the cumulative arithmetic
and the orchestrator wiring tests use the real
`AnthropicSdkCostCeilingExceeded` propagation path — no kwargs-only
assertions per story body / 60-7 discipline.

## Acceptance criteria → test mapping

| AC | Surface | Test name (suggested) |
|----|---|---|
| (A) Baseline clamp prevents 60-7 trainable-silence | server unit | `test_baseline_ceiling_clamps_runaway_baseline` |
| (A) Clamp does not affect healthy steady state | server unit | `test_baseline_clamp_is_a_noop_for_healthy_baselines` |
| (B) `input_tokens > 40000` fires regardless of baseline | server unit | `test_absolute_input_floor_fires_with_baseline_at_60k` |
| (B) New `input_absolute` trigger appears in event | server unit | `test_input_absolute_trigger_value_and_priority_order` |
| (C.1) `session_id` threaded through, per-session keyed | server unit | `test_cumulative_cost_is_per_session_id` |
| (C.1) Rejoin (same session_id) inherits cumulative | server unit | `test_rejoin_same_session_id_inherits_cumulative` |
| (C.2) Crossing $10 raises typed exception | server unit | `test_crossing_ceiling_raises_cost_ceiling_exceeded` |
| (C.2) Subsequent calls keep raising | server unit | `test_after_ceiling_crossed_subsequent_calls_refuse` |
| (C.2) Single event at threshold-cross, not per-call | server unit | `test_cost_ceiling_event_fires_once_per_session` |
| (C.3) Typed watcher event shape + severity=error | server unit | `test_session_cost_ceiling_exceeded_event_shape` |
| (C.3) Per-turn `cost_running_total` fires every turn | server unit | `test_cost_running_total_fires_every_turn` |
| (C.3) Typed WS message reaches connected clients | server wiring | `test_cost_ceiling_websocket_message_broadcast` |
| (D) Env var override parses + validates | server unit | `test_env_var_override_and_invalid_parse` |
| Live integration (closure gate) | orchestrator | `test_lowered_ceiling_terminates_live_dispatch` |

## Open questions for Dev (RED phase deferrals)

1. **Tracker home: SDK client vs SessionRoom.** RED tests assume
   per-`AnthropicSdkClient` `dict[str, float]` because (a) it's the
   smallest change, (b) it composes cleanly with the existing
   per-instance baselines, (c) `llm_factory` builds the client
   per-slug. **Dev may discover** that some non-narrator codepaths
   (dungeon "curate" via `claude -p`, future Opus calls) also need to
   contribute to the cumulative, in which case a `SessionRoom`-owned
   counter that BOTH backends update may be the right design. If so,
   escalate before refactoring — there's a 60-followup story shape
   here that's larger than this followup.

2. **WS message subtype vs new discriminator.** RED tests for (C.3)
   assume `SessionEventMessage` (`protocol/messages.py:883`) can
   carry a `subtype` field. If `SessionEventMessage` is too narrow,
   add a new typed message per ADR-038 — `CostCeilingExceededMessage`
   with its own `MessageType` discriminator. Either is fine; Dev's
   call based on what `SessionEventMessage.payload` accepts today.

3. **Baseline reset semantics.** `reset_baselines()` (today dormant per
   `anthropic_sdk_client.py:363-385` docstring) clears the rolling
   deques. Story 61-followup-D **adds** the per-session cumulative
   dict — should `reset_baselines()` also clear cumulative for one
   session_id (signature change), or all sessions (existing
   signature)? RED tests assume `reset_baselines()` keeps its current
   "all sessions" signature and a new `reset_session_cost(session_id)`
   method handles per-session reset. 61-followup-C wires
   `SessionRoom.close_store()` into a real teardown — that's the call
   site for `reset_session_cost`.

4. **Cumulative double-count on rejoin.** When a rejoined session
   inherits cumulative (good), and then the in-process orchestrator
   for that slug is recycled (orchestrator dies, new
   `AnthropicSdkClient` constructed), the dict is empty — the rejoin
   would NOT inherit. This is acceptable for v1: the in-process
   orchestrator outlives WS reconnects per `session_room.py:174-181`,
   so the cumulative survives client-side reconnect but not
   server-process restart. Document this in the assessment;
   server-restart-resets-cumulative is an explicit not-in-scope.

## Surprises uncovered during context-building

- **The existing per-call absolute floor is $0.30.** Already landed in
  61-4 as `_ABSOLUTE_COST_USD_FLOOR` at line 53 — this is NOT what
  (A) does. (A) clamps the rolling **baseline**, (B) adds an absolute
  **input_tokens** floor. The $0.30 per-call cost floor remains the
  third (single-call) safety net. All three compose; none replace each
  other.

- **`narrator.sdk.usage` is still a plain `logger.info`, not a
  watcher event.** Same as 61-4's discovery. (C.3)'s per-turn
  `session.cost_running_total` watcher event is the first emit from
  the orchestrator narrator-turn path that carries cumulative cost as
  a GM-panel signal — sibling of 60-2's per-block prompt event but at
  the higher-level "what did this turn cost the session" axis.
  61-followup-B is the story that promotes `narrator.sdk.usage`
  proper; this story rides above it.

- **`session_id` is already in scope at the call site.** No new
  plumbing needed from handler to orchestrator — only from
  orchestrator to client (`anthropic_sdk_client.py:145`
  `complete_with_tools` signature). One protocol-layer signature
  change at `tooling_protocol.py:96`.

- **`SessionRoom.close_store` is dormant.** Per 61-4's note, no
  production caller. The hard-kill path does **not** depend on
  `close_store` firing; the typed exception propagates regardless.
  But the cumulative reset on session end would benefit from
  `close_store` becoming live — flag to 61-followup-C dependency.

## References

- Story body: `sprint/epic-61.yaml` `id: 61-followup-D`
- Epic context: `sprint/context/context-epic-61.md`
- Sibling: `sprint/context/context-story-61-4.md` (decisions A-F, the
  detector this story extends)
- Code: `sidequest-server/sidequest/agents/anthropic_sdk_client.py`
  (lines 28-53 for current constants, 387-485 for
  `_maybe_emit_cost_runaway`, 363-385 for `reset_baselines`)
- Code: `sidequest-server/sidequest/agents/orchestrator.py:3663` —
  `complete_with_tools` call site (session_id in scope at 3654)
- Code: `sidequest-server/sidequest/agents/tooling_protocol.py:96` —
  `complete_with_tools` protocol signature
- Code: `sidequest-server/sidequest/server/session_room.py:322-385` —
  `close_store` + `reset_baselines` (dormant teardown path)
- Code: `sidequest-server/sidequest/protocol/messages.py:883` —
  `SessionEventMessage` candidate for WS surface
- Test patterns: `tests/agents/test_61_4_cost_runaway_alarm.py:58-176`
  (SDK fake, `_FakeSocket`, watcher hub binding)
- Test patterns: `tests/server/test_location_description_emit.py`
  (fixture-driven wiring per CLAUDE.md "No Source-Text Wiring Tests")
- Incidents: `~/.claude/projects/-Users-slabgorb-Projects-oq-2/memory/project_runaway_valley_block_2026_05_23.md`
- Incidents: `~/.claude/projects/-Users-slabgorb-Projects-oq-2/memory/project_anthropic_key_compromise_2026_05_23.md`
- 60-7 evidence trail: `sprint/archive/60-7-session.md` (annees_folles
  ramp, closure discipline pattern to mirror)
