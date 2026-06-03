---
id: 134
title: "Per-Session API Cost Runaway Detector and Hard-Kill Ceiling — Rolling-Baseline Triggers and Terminal Refusal"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [31, 101, 122]
tags: [agent-system, observability]
implementation-status: live
implementation-pointer: null
---

# ADR-134: Per-Session Cost Runaway Detector + Hard-Kill Ceiling

> **Documents a system already live in code.** A multi-trigger cost-runaway
> detector and a per-session cumulative hard-kill ceiling shipped on the
> Anthropic SDK narrator backend across Story 61-4 and its follow-ups
> (61-followup-A through -D) during the 2026-05 SDK-migration cost work,
> without a governing ADR. The detector, the rolling baselines, the absolute
> floors, the `$10` cumulative ceiling, and the terminal `AnthropicSdkCostCeilingExceeded`
> refusal all live in `sidequest-server/sidequest/agents/anthropic_sdk_client.py`.
> This record closes that architecture-of-record gap and states what the
> decision *was* — exactly as ADR-117 did for the ruleset seam.

## Context

ADR-101 moved the narrator onto the Anthropic SDK to make per-turn cost fit a
Max-20× cap. Its cost reasoning is entirely *per-turn average*: it targets a
weighted-average $0.05-0.07/turn and reasons about a 250-turn session costing
$12-18 against the cap (101 §Decision, §Consequences). It mentions the Max-20×
cap only in passing and contains **no runaway-detection spec and no
cumulative-ceiling spec** — its inline implementation-pointer names the backend
modules but no safety machinery, and the 2026-05-20 cache amendment is about
cache layout, not billing protection.

That left a billing-catastrophe gap that production hit. The
`anthropic_sdk_client.py` comments record the forcing incidents:

- **2026-05-23** — a 60K-input / 12-output-token call fingerprint: a snapshot
  misroute or prompt-bloat regression that bills a fat input with almost no
  output. A single fat turn is cheap; *sustained* fat turns are a runaway.
- **The 60-7 `annees_folles` ramp** — 11 consecutive turns sustained at ~$0.165
  each with no per-call spike sharp enough to trip a naive 5× alarm.

A second structural pressure comes from ADR-122 (SessionRoom never-evict):
`RoomRegistry` (`session_room.py`) **never evicts a slug**, so the
`AnthropicSdkClient` instance backing a slug's orchestrator lives for the
**server process lifetime**, not per-session (`session_room.py`). A
long-lived client means (a) any per-session state must be keyed on session_id,
not instance-wide, and (b) a rolling baseline that adapts to observed traffic
can **self-train onto a sustained runaway** — if 10 turns all bill $0.12, the
mean is $0.12 and turn 11 at $0.18 is only 1.5× baseline, under any 5× alarm
(`anthropic_sdk_client.py`). The May-23 incident, run continuously, would
have calibrated its own alarm into silence within 10 calls.

So the engine needs two things ADR-101 never specified: (1) a *detector* that
cannot be trained into silence, and (2) a *hard ceiling* that terminally stops
billing when cumulative session spend crosses a catastrophe line — both keyed
per-session because the client outlives any one session.

## Decision

**The Anthropic SDK narrator client carries two layered billing-safety
mechanisms, both keyed on `session_id`: a multi-trigger cost-runaway *detector*
that fires `cost_runaway_suspected` watcher events, and a per-session cumulative
*hard-kill ceiling* (`$10` default, env-overridable) that raises
`AnthropicSdkCostCeilingExceeded` and terminally refuses all subsequent calls
for that session.** Both run inside `complete_with_tools`; calls with
`session_id=None` (non-narrator codepaths, e.g. the dungeon-materializer
one-shot curate) bypass both mechanisms entirely.

### 1. Multi-trigger runaway detector (`_maybe_emit_cost_runaway`)

After each billable SDK iteration, the just-observed call is checked against
**two parallel rolling baselines** — one for `cost_usd`, one for `input_tokens`
— each a per-session `deque(maxlen=K)` with **K=10** (`_BASELINE_WINDOW_K`,
`anthropic_sdk_client.py`, `231-232`). Pre-warmup (fewer than K observations)
the comparator uses fixed warmup floors (`_WARMUP_COST_USD_FLOOR=$0.03`,
`_WARMUP_INPUT_TOKENS_FLOOR=12_000`, lines 48-49); post-warmup it uses the
rolling mean, **clamped at a ceiling** (`_BASELINE_COST_CEILING=3×$0.03=$0.09`,
`_BASELINE_INPUT_CEILING=3×12_000=36_000`, lines 74-75) so a drifted baseline
cannot raise the trip threshold without bound (`anthropic_sdk_client.py`).

Four triggers, two relative and two absolute (lines 765-782):

| Trigger | Condition | Kind |
|---|---|---|
| `cost_multiple` | `cost_usd > 5 × baseline_cost` (`_COST_TRIGGER_MULTIPLE`, l.50) | rolling-baseline |
| `io_fingerprint` | `input_tokens > 2 × baseline_input` **and** `output_tokens < 50` (`_IO_FINGERPRINT_INPUT_MULTIPLE`/`_OUTPUT_CEILING`, l.51-52) | rolling-baseline + absolute output floor |
| `input_absolute` | `input_tokens > 40_000` — **always**, regardless of baseline or output (`_ABSOLUTE_INPUT_TOKENS_FLOOR`, l.83) | absolute floor |
| `cost_absolute` | `cost_usd > $0.30` — **always**, regardless of baseline (`_ABSOLUTE_COST_USD_FLOOR`, l.62) | absolute floor |

The **absolute floors are the safety net the rolling baselines cannot provide**:
they fire regardless of how high the rolling mean has self-trained, catching the
trained-into-silence case (`anthropic_sdk_client.py`, `775-779`). The
`input_absolute` floor specifically catches the high-output sibling of the
60K-in/12-out fingerprint — a 50K-in/800-out call that slips past
`io_fingerprint`'s `output<50` clause but is still a snapshot-bloat canary
(lines 77-83, 770-774).

The baseline windows are appended to **after** the check, so the comparator
always sees prior observations; a healthy call still seeds the window so the
next call has priors (`anthropic_sdk_client.py`).

### 2. Per-session cumulative hard-kill ceiling (`_check_cost_ceiling` / `_update_session_cumulative`)

A per-session_id cumulative-cost dict (`_session_cumulative_cost_usd`,
`anthropic_sdk_client.py`) accumulates every billable iter's cost. The
ceiling is `_SESSION_COST_CEILING_USD=$10.00` (l.92) — sized at ~333 healthy
$0.03 turns of headroom, tight enough that a 60-7-class regression at $0.165/turn
caps at ~60 turns / one playtest evening, not a weekend (lines 85-92). It is
**env-overridable** via `SIDEQUEST_SESSION_COST_CEILING_USD`, parsed at
construction with No-Silent-Fallbacks discipline: non-parseable, NaN, ±inf, or
non-positive values raise `AnthropicSdkConfigError` immediately (lines 240-262)
— because `float('nan')` would silently disable the entire kill (every
`cumulative >= nan` is False) and `inf` would make the ceiling unreachable.

Two enforcement points in `complete_with_tools`:

- **Pre-flight** (`_check_cost_ceiling`, l.872-884, called at l.299-300): at the
  *entry* of every call, if cumulative already `>= ceiling`, raise immediately
  **without touching the SDK**. This is the "no further billing" half of the
  contract.
- **Post-iter** (`_update_session_cumulative`, l.886-940, called at l.521-526):
  after each billable iter, add the cost; if it crosses the ceiling, emit the
  typed `session.cost_ceiling_exceeded` watcher event (once) and raise. The iter
  that crossed has **already billed Anthropic** — the kill is "no further
  calls," not "no further tokens for the call already in flight" (lines 893-899).

## Invariants / Contracts

- **Terminal refusal — no recovery.** Once a session crosses the ceiling, every
  subsequent `complete_with_tools` for that `session_id` re-raises
  `AnthropicSdkCostCeilingExceeded` at the pre-flight check without making an SDK
  call. There is no reset/recovery handle for the cumulative tracker within a
  session's life (`_check_cost_ceiling`, l.872-884; `reset_baselines` explicitly
  does **not** clear `_session_cumulative_cost_usd`, l.643-655).
- **Session-id keying.** Both the rolling baselines (`dict[str, deque]`) and the
  cumulative tracker (`dict[str, float]`) are keyed on `session_id`, never
  instance-wide — required because one long-lived client (ADR-122 never-evict)
  backs many sessions over its lifetime, and deterministic-URL MP rejoins inherit
  the prior session's window correctly (`anthropic_sdk_client.py`,
  `215-232`). The canonical `session_id` is the room slug, flowing in as
  `session_id=sd.game_slug` (`session_room.py`).
- **Announced-once dedup.** The `session.cost_ceiling_exceeded` watcher event
  fires **exactly once per session** via the `_session_ceiling_announced` set
  (`anthropic_sdk_client.py`, `912-939`); subsequent refusals re-raise the
  exception but stay silent on the watcher. The announce-set `.add` happens
  **after** the side-effecting emit, so a failed emit cannot poison the set and
  permanently lose the GM-panel event on retry (lines 934-939).
- **Absolute floors vs baseline triggers.** The two absolute floors
  (`cost_absolute`, `input_absolute`) fire independent of any baseline; the two
  relative triggers (`cost_multiple`, `io_fingerprint`) fire against the
  K=10 rolling mean clamped at 3× the warmup floor. Exactly **one** event fires
  per call; on multi-trigger collision the priority is `io_fingerprint >
  input_absolute > cost_multiple > cost_absolute` (most-diagnostic first —
  `io_fingerprint` matches the 2026-05-23 shape exactly), with all four
  trigger conditions surfaced through the `cost_usd`/`baseline_cost_usd`/
  `input_tokens`/`baseline_input_tokens` field pairs regardless of which named
  the event (`anthropic_sdk_client.py`, `784-832`).
- **Typed exception carries actionable fields.** `AnthropicSdkCostCeilingExceeded`
  carries `session_id`, `cumulative_cost_usd`, and `ceiling_usd` so the WS
  handler / broadcast layer can build a typed `session.cost_ceiling_exceeded`
  client message without string-grovelling (lines 107-129); all three raise
  sites build it through `_build_ceiling_exceeded` (l.852-870) so wording and
  field shape cannot drift.
- **`session_id=None` is a hard bypass, not a synthesized key.** Non-narrator
  callers (one-shot curate, ad-hoc jobs) are detector- and ceiling-no-ops — no
  read, no append, no cumulative update. Per No Silent Fallbacks the contract is
  "off for None," not a magic `<no-session>` bucket (lines 727-731).

## Observability

Per the project OTEL principle and ADR-031 (the GM panel as lie detector), every
billing decision emits a watcher event via `_watcher_publish_event`
(component `narrator.sdk`):

- **`cost_runaway_suspected`** (severity `warn`) — the detector's alarm, with
  `trigger` discriminator, observed vs baseline cost and input, `warmup` flag,
  `model`, and `session_id` for interleaved multi-session attribution
  (`anthropic_sdk_client.py`).
- **`session.cost_ceiling_exceeded`** (severity `error`) — the hard-kill event,
  once per session, with `session_id`, `cumulative_cost_usd`, `ceiling_usd`,
  `model` (lines 915-933).
- **`session.cost_running_total`** (severity `info`) — per-turn live pulse with
  `fraction_used` (the "X / $10" denominator) for the GM-panel counter
  (`_emit_cost_running_total`, l.971-998).
- **`narrator.sdk.usage`** (severity `info`) — the per-call baseline pulse the
  warn alarm and the ceiling compare against (lines 448-460).

These give the GM panel a continuous, plottable cost baseline plus two distinct
alarm tiers (warn = "suspect," error = "killed"), so a runaway is visible *as it
ramps*, not only after the bill lands.

## Consequences

**Positive**

- A billing catastrophe is bounded at `$10`/session by default — a hard cap ADR-101
  never provided. The terminal refusal means a regression cannot run up an
  unbounded weekend bill on a never-evicted room.
- The detector cannot be trained into silence: the absolute floors and the
  baseline-ceiling clamp directly defeat the self-training failure mode that the
  long-lived (ADR-122) client makes possible.
- Two alarm tiers + a per-turn pulse make spend observable in the GM panel as it
  ramps, honoring ADR-031 / the OTEL principle.
- Env-override (validated fail-loud) lets the operator lower the ceiling to e.g.
  $0.50 to validate end-to-end termination in a manual playtest without a real
  bill (lines 88-91).

**Negative / cost**

- Terminal-with-no-recovery means a session that legitimately needs >$10 (a real
  marathon) is killed and must be reloaded as a fresh session — acceptable given
  the playgroup's session length, but a known sharp edge.
- Dual per-session state (`_session_cumulative_cost_usd`, `_session_ceiling_announced`,
  two baseline deques) accumulates one entry per distinct session_id for the
  process lifetime under ADR-122 never-evict. `reset_baselines(session_id)` from
  `SessionRoom.close_store()` evicts the baseline deques but **not** the
  cumulative/announce state — a flagged follow-up (`anthropic_sdk_client.py`):
  on a slug-recycle rejoin a stale announce-set entry would silently suppress the
  new session's first ceiling alarm, deferred so the decision and its OTEL
  plumbing land together.
- The `$10` ceiling and the trigger constants are calibrated to specific
  incidents (2026-05-23, 60-7); a different traffic shape may need retuning, for
  which the OTEL pulses provide the data.

## Alternatives considered

- **Global (process-wide) ceiling instead of per-session.** Rejected: the client
  outlives any one session (ADR-122 never-evict), and deterministic MP rejoins
  share a slug — a single global counter would conflate independent sessions,
  killing an innocent neighbor when one session ran hot, and could never reset.
  Per-session_id keying is the only correct grain (`anthropic_sdk_client.py`).
- **Soft warn only, no hard kill.** Rejected: the detector's `cost_runaway_suspected`
  warn already exists, but a warn does not stop billing. A sustained runaway on a
  never-evicted room with no human watching the GM panel is exactly the
  catastrophe a warn cannot prevent. The hard kill is the backstop the warn
  cannot be.
- **Rolling baseline alone (no absolute floors).** Rejected: a sustained runaway
  trains the rolling mean upward until the relative triggers go silent within
  ~10 calls — the documented self-training failure mode. The absolute floors and
  the baseline-ceiling clamp exist precisely because a self-adapting baseline is
  defeatable (lines 53-61).
- **Un-bill / abort the in-flight crossing iter.** Not possible: the iter that
  crosses has already billed Anthropic. The kill is correctly scoped to "no
  further calls," accepting the one already-landed crossing iter (lines 893-899).

## Reconciliation with ADR-101, ADR-122, ADR-031

- **ADR-101 (Anthropic SDK as narrator backend):** ADR-101 owns *per-turn* cost
  economics — caching, model routing, the $0.05-0.07/turn target, the Max-20×
  framing. It contains no runaway detector and no cumulative ceiling; its inline
  docs reference only the migration story IDs, not safety machinery. **ADR-134
  adds the cumulative-spend safety layer on top of 101's per-turn economics** —
  101 makes a turn cheap; 134 stops a *session* from going catastrophic. 101 is
  not superseded or amended; 134 is purely additive to the same client.
- **ADR-122 (SessionRoom never-evict):** the *reason* this machinery must be
  per-session-keyed and self-training-resistant. Because `RoomRegistry` never
  evicts, the `AnthropicSdkClient` lives for the process lifetime, so (a) all
  state is keyed on `session_id`, and (b) `SessionRoom.close_store()` calls
  `reset_baselines(session_id)` as the per-session eviction handle on the
  baseline windows (`session_room.py`). ADR-134 depends on 122's
  lifecycle but does not change it.
- **ADR-031 (Game Watcher — semantic telemetry):** the watcher transport and the
  "GM panel as lie detector" doctrine ADR-134's events ride on. The
  `cost_runaway_suspected` / `session.cost_ceiling_exceeded` /
  `session.cost_running_total` events are ADR-031-style semantic telemetry for
  the billing subsystem.
