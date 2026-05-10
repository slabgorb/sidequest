# Stateless Narrator Turns — Drop `--resume`, Bounded Per-Turn Prompts

**Status:** Draft (brainstorm output, pre-plan)
**Date:** 2026-05-10
**Author:** Architect (White Queen)
**Supersedes:** ADR-066 (Persistent Opus Narrator Sessions)
**Related:** ADR-067 §session-management text (rewrites), story 23-4 (location-scoped lore — separate follow-up)

## Problem

Narrator turns get slower and eventually crash with `context_window_full` over a long playtest. The proximate cause is `--resume`: Anthropic's session memory accumulates every turn's conversation, so each subsequent turn replays a growing history. Latency scales with turn count; failures compound.

Compounding this, the visible per-turn prompt (`prompt_assembled`) already grows turn-over-turn because state sections like `npc_roster`, `world_context`, `active_tropes`, and `retrieved_lore` project full state on every turn. Location scoping is a separate problem (story 23-4); this spec addresses only the **hidden** growth — Anthropic-side session history we cannot inspect, trim, or audit.

ADR-066 claimed `--resume` was load-bearing for latency (6s warm vs 22s rebuild). The claim was based on first-warm-cache measurements. As the session grows, the warm-cache hit gets progressively worse, and the `context_window_full` crash is the terminal state of that growth. The premise inverts: `--resume` is **causing** the latency problem, not solving it.

Every per-turn re-injection in `build_narrator_prompt` (NPC roster, chassis voices, party peers, game state, magic context, recency-zone guardrails) exists because we **already** don't trust the model's session memory — we re-assert ground truth every turn anyway. We pay for `--resume` (latency win, theoretically) and then pay again (per-turn injection) to undo its drawback (memory drift). The system fights itself.

## Decision

**Drop `--resume` entirely. Every narrator turn is a stateless, bounded, fully-scoped prompt.** No session id, no conversation history, no Full/Delta tier distinction. The model sees exactly what we send this turn, no more, no less.

Three properties follow by construction:

- **Bounded per-turn cost.** Prompt size is a function of current world scope, not turn count. Latency stays flat across long sessions.
- **No `context_window_full` crashes.** Structurally impossible. Worst case is a single oversized turn — a diagnosable bug, not a session collapse.
- **Complete OTEL audit.** `prompt_assembled` is the whole truth of what the model saw. The GM panel becomes a true lie-detector with no hidden state.

Migration is bigbang. No feature flag, no per-save fallback. The playgroup is in exploration mode; saves carrying `narrator_session_id` load with the field ignored.

## Architecture

### Request flow

```
process_action(action, context)
  └─ build_narrator_prompt(action, context)        # single composition pass
       └─ PromptRegistry → compose by zone, partition by category
  └─ ClaudeClient.send(system_prompt, user_message, model="opus", ...)
  └─ extract_structured_from_response → NarrationTurnResult
```

No `is_first_turn` branch. No session-id read/write. No recovery wrapper.

### Prompt composition

Build a single `PromptRegistry` by calling every section registrar. All sections previously gated by `is_full` now fire unconditionally. Sections gated by *turn position* keep that gate:

- `opening_scene_constraint` — only when `context.turn_number == 0` (a turn-1 constraint, not a session-establishment constraint)
- `backstory_capture` — only when the eventual intent classifier says so (unchanged from prior Phase 1 deferral)

Zones (`AttentionZone.Primacy/Early/Valley/Late/Recency`) and section categories are unchanged.

Compose into two strings using the existing zone-ordered emitter, partitioning by **operational stability** — i.e. whether the section's content is byte-identical across every turn of the same game given fixed operator settings:

- **`system_prompt`** receives the **stable scaffold**: narrator identity (`build_context`), dialogue rules (`build_dialogue_context`), SOUL principles, output format (`build_output_format`), genre identity, genre narrator voice, genre NPC voice, genre world-state voice, narrator vocabulary, transition hints. These are byte-identical for the entire session as long as genre + verbosity + vocabulary settings hold.

- **`user_message`** receives **turn-dynamic** content: NPC roster, party peers, game state, world context, retrieved lore, magic context, active tropes, encounter context (combat/chase/extraction voice fires here when active), opening_directive when set, trope_beat_directives, dispatch_bank directives, recency-zone guardrails (confrontation_trigger, npc_intro_visual, opening_scene_constraint), and finally `player_action`.

`SectionCategory` is **not** the partition key — categories were assigned for zone/layout reasons that don't track stability cleanly (e.g. `genre_npc_voice` is `Category.Genre` but is content-stable). Implementation introduces an explicit `bucket: Literal["system", "user"]` per registered section, defaulted by an explicit allowlist of stable section names. Adding a new section requires choosing its bucket; the `test_system_user_split_categories` test enforces the allowlist.

The split is semantic, not a caching trick. It matches Anthropic's API shape: "what the model is" vs "what's happening this turn." If `claude -p` ever exposes cache breakpoints, the system_prompt boundary is the natural place to put them — but the design does not depend on it.

### Components — what changes

**`sidequest/agents/orchestrator.py`** (load-bearing change)

*Delete:*
- `class NarratorPromptTier` (lines 83–94)
- `select_prompt_tier()` (1146–1172)
- `reset_narrator_session()`, `set_narrator_session_id()` (897–911)
- `_classify_narrator_error`, `_narrator_error_signature`, `_compose_rebuild_header`, `_recover_from_narrator_failure` (917–1105 — the full ADR-066 §8 recovery scaffolding)
- `_narrator_session_id`, `_session_genre`, `_session_lock` fields on `Orchestrator`
- `_recap_provider` (recap fed the warm-reboot frame; now dead)

*Simplify:*
- `build_narrator_prompt()` loses the `tier` and `rebuild_header` parameters. Every `if is_full:` gate is removed; inner bodies become unconditional. Function flattens to: register sections → compose → publish → return.
- `process_action()` (line 2479) loses `is_first_turn` branching, the `system_prompt_for_establish` / `send_prompt` swap, the session-id read/write block, the recovery wrapper. Becomes: build prompt → call client → parse response → return.

**`sidequest/agents/client.py`** (or wherever `ClaudeClient` lives)

The narrator's call site stops passing `session_id` and stops using the first-turn-vs-subsequent system_prompt swap — that's the load-bearing change. Whether to also rename/collapse the existing `send_with_session(prompt, model, session_id, system_prompt, ...)` API surface is a code-hygiene call the implementer makes after enumerating callers (`grep -rln "send_with_session" sidequest/`). If narrator is the only consumer, the cleaner shape is a new `send(system_prompt, user_message, model, allowed_tools, env_vars)`. If auxiliary callers exist, leaving the API intact and dropping `session_id` from the narrator's invocations is acceptable.

The underlying CLI invocation drops the `--resume <sid>` flag.

**`sidequest/server/session_helpers.py` and `sidequest/handlers/*`**

No structural change. They call `orchestrator.run_narration_turn(player_action, context)` which keeps the same signature.

**Saves (`sidequest/game/persistence.py`)**

`narrator_session_id` field removed from save schema. Old saves with the field set load with the field ignored. No migration script. Per the user decision: saves are exploratory; no preservation cost.

**ADRs**

- ADR-098 written (new — this design becomes its ADR)
- ADR-066 marked `superseded-by: 098`; entry added to `docs/adr/SUPERSEDED.md`
- ADR-067 §session-management text rewritten (unified-agent decision unaffected)
- `docs/adr/README.md` index updated

## Data flow

**Outbound to Claude CLI:**

```python
ClaudeClient.send(
    system_prompt=system_prompt,    # Identity | Soul | Format sections, zone-ordered
    user_message=user_message,      # Genre | State | Action | Guardrail sections, zone-ordered
    model="opus",
    allowed_tools=[],
    env_vars={},
)
```

No `session_id`, no `--resume`, no first-turn-vs-subsequent branching.

**Telemetry change to `prompt_assembled` event:**
- Add `system_len` and `user_len` fields (separate from `prompt_len` total)
- Add `bounded: true` as the design contract marker
- Remove `tier` field (no longer meaningful)

**Streaming.** Orthogonal. When `SIDEQUEST_NARRATOR_STREAMING=1`, the response read path is unchanged; only the request build/send changes.

**Response handling.** `ClaudeResponse.text` parsed by `extract_structured_from_response`. `ClaudeResponse.session_id` becomes vestigial — ignored. `narration_apply` consuming the game_patch is unchanged.

**MP merged turns.** No special handling. Same composition runs; `context.merged_player_actions` already drives `player_action` to render multi-PC declarations. System prompt is identical regardless of single-PC vs merged — it's the narrator's identity, not the turn's shape.

## Error handling

The error model collapses dramatically because most of ADR-066 §8 only existed to handle session-state failures.

**Deleted error paths:**
- `session_expired` classification — there is no session
- `context_window_full` classification — by construction, the prompt is bounded; if hit, it's a bug (a specific section grew unexpectedly), not a runtime condition
- Session rotation, rebuild_header composition, warm-reboot frame, `_recover_from_narrator_failure` (~155 lines)

**Three remaining failure modes:**

1. **Transient subprocess failure** (network blip, spawn failure, `_ClaudeTimeoutError`).
   One retry. Same prompt, fresh subprocess. If retry fails, fall through to mode 3.
   OTEL: `narrator.transient_retry` span with error type + first-attempt duration.

2. **Malformed response** (CLI returned 0 but response isn't parseable, or `extract_structured_from_response` raises).
   No retry — retrying the same prompt on the same model gives the same broken output. Fall through to mode 3.
   OTEL: `narrator.response_unparseable` with response prefix for postmortem.

3. **Unrecoverable** — return a degraded `NarrationTurnResult` with an in-fiction stall ("The world holds its breath..."), same shape as the current degraded fallback. Game state untouched, turn counter not advanced, player can retry.
   OTEL: `narrator.unrecoverable` with classification.

Retry-once is deliberately simple. No exponential backoff, no rotation, no fallback model. The current code's complexity around retry was driven by session statefulness; none of that applies anymore. If `claude -p` is flaky on a given turn, the next turn is independent — no compounding failure to engineer around.

### Bound canary

Before the subprocess call:

```python
total_bytes = len(system_prompt) + len(user_message)
if total_bytes > SOFT_PROMPT_BUDGET_BYTES:
    logger.warning("narrator.prompt_oversized total_bytes=%d", total_bytes)
    # publish OTEL prompt_oversized with per-section breakdown
    # DO NOT fail the turn — canary, not circuit breaker
```

`SOFT_PROMPT_BUDGET_BYTES ≈ 2_000_000` (~500K tokens), leaving 50% headroom on Opus 4.7's 1M-token window. The canary's purpose is to surface unbounded growth regressions in OTEL while there's still 500K+ tokens of headroom and the game is still playable — not to prevent context-window crashes (those are structurally impossible at normal play sizes). Without the canary, a bad regression hides under generous capacity until something else breaks.

## Testing

The wiring test is the central claim. This design lives or dies on "prompt size doesn't grow with turn count." A test that doesn't verify that is theatre.

**New tests:**

1. **`test_prompt_size_bounded_over_session`** (integration).
   Drive `Orchestrator.process_action` through 30 simulated turns against an in-memory `ClaudeClient` stub. Capture `len(system_prompt) + len(user_message)` per turn.
   Assert: no strict monotonic increase across consecutive turns (turn N+1 size > turn N size for every N is forbidden), **and** `max(sizes) / min(sizes) <= 1.5` (the largest turn is no more than 50% larger than the smallest). These two conditions catch monotonic growth pathologies without requiring statistical machinery.
   This is the wiring test that proves the central claim.

2. **`test_system_prompt_stable_within_session`**.
   Across N turns of the same game, `system_prompt` is byte-identical (or differs only on operator-changed verbosity/vocabulary settings). Documents the design contract.

3. **`test_system_user_split_categories`**.
   For a representative turn, assert every section ends up in the expected bucket: `Identity | Soul | Format` in system, `State | Action | Guardrail | Genre` in user. Catches accidental mis-tagging of a new section.

4. **`test_no_narrator_session_id_in_outbound_call`**.
   Mock `ClaudeClient.send`; assert calls never carry a `session_id`. Belt-and-braces for the bigbang.

5. **`test_oversized_prompt_canary`**.
   Inject a section that overflows `SOFT_PROMPT_BUDGET_BYTES`; assert OTEL `narrator.prompt_oversized` fires with per-section breakdown and the turn still executes (canary, not circuit breaker).

6. **`test_merged_player_actions_stateless`**.
   MP merged turn with multiple PCs declaring; assert one composition pass, no session state read/written, normal `NarrationTurnResult`.

7. **`test_transient_retry_once`**.
   Mock client raises `_ClaudeTimeoutError` on first call, succeeds on second; assert one retry, one OTEL `narrator.transient_retry` span. Then mock raises twice; assert degraded `NarrationTurnResult` with in-fiction stall and `narrator.unrecoverable` span.

**Tests to delete.** Anything in `tests/` matching:
```
grep -rln "PromptTier\|select_prompt_tier\|rebuild_header\|_recover_from_narrator_failure\|session_established\|session_expired\|warm_reboot" tests/
```
Triage each — most assert on machinery this design retires. Delete file or method per file.

**Tests preserved unchanged.** Anything testing `build_narrator_prompt` for *which sections fire given context state* stays valid; tier param simply goes away from call sites. Tests of `narration_apply`, dispatch, encounter context, NPC roster, magic context — all unaffected.

**Type checking.** `uv run pyright` must pass. Deletion of `NarratorPromptTier`, `select_prompt_tier`, and recovery scaffolding will flag stragglers more reliably than test compilation.

**Coverage.** Don't chase a number. The seven new tests above are the load-bearing ones; deletions are pure subtraction.

## Out of scope (explicitly)

- **Location-scoped lore retrieval** (story 23-4 / ADR-097-in-waiting). This spec addresses **hidden** growth (session history). Visible state-section growth (`npc_roster`, `world_context`, retrieved_lore not scoped to current location) is a separate problem with its own design. Both feed the same OTEL signal but the fixes are independent.
- **Prompt-cache breakpoints.** The system/user split is *compatible* with eventual cache_control passthrough but does not depend on it. If/when `claude -p` exposes cache flags, the system_prompt is the natural breakpoint — that's a future story, not a prerequisite.
- **Narrator model change.** Stays on Opus 4.7. Stateless turns work with any model; this isn't the place to relitigate ADR-001 / ADR-066's model selection.
- **Streaming behavior.** Orthogonal. `SIDEQUEST_NARRATOR_STREAMING` flag and its read path are unchanged.
- **Backstory intent classifier.** The `backstory_capture` section stays referenced but its activation gate (intent classification) remains deferred as in the current Phase 1 omission.

## Risks and mitigations

- **Risk:** Per-turn latency without session reuse is materially worse in practice than the bounded-prompt model predicts.
  **Mitigation:** The wiring test measures it. Turn-to-turn timing is also already in OTEL (`turn.agent_llm.inference` span duration). If post-deployment data shows a regression at small prompt sizes, the system_prompt boundary gives us a clean place to add cache_control later — a story, not a redesign.

- **Risk:** Removing session memory degrades narrative continuity (model "forgets" earlier flavor choices, descriptions, NPC speech tics).
  **Mitigation:** The continuity that matters is in re-injected ground truth (`npc_roster`, `chassis_voices`, `game_state`). Flavor variety from a stateless model is arguably a net positive (no "oak door" creeping into every description). Playtest validation required, but architectural risk is low — every continuity concern that surfaced in prior playtests was already addressed by per-turn re-injection, not by session memory.

- **Risk:** A section accidentally accumulates state across turns and the size canary misses it.
  **Mitigation:** `test_prompt_size_bounded_over_session` measures the actual outcome (variance across turns). The canary is a runtime safety net; the test is the design contract. Both fail loudly.

- **Risk:** Old saves with `narrator_session_id` set fail to load.
  **Mitigation:** Drop the field at deserialization. If saves use pydantic, the `extra="ignore"` policy or an explicit field removal in the model handles this; if a different serializer, equivalent treatment at load. Per user direction, no migration script needed (saves are exploratory).

## Implementation notes for the plan

- Grep `send_with_session` consumers in the server before deciding whether to rename or just change call sites.
- Run `grep -rln "PromptTier\|select_prompt_tier\|rebuild_header\|_recover_from_narrator_failure" tests/` first to enumerate test deletions before touching production code.
- Update `prompt_assembled` event consumers in the dashboard (`sidequest-ui`) at the same time the server side ships — `tier` field disappears, `system_len` / `user_len` / `bounded` appear. Coordinate the cross-repo PR.
- ADR-098 itself is part of the implementation deliverable, not a separate story. Same PR.
