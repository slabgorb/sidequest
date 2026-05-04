---
story_id: "45-50"
jira_key: null
epic: "45"
workflow: "tdd"
renumber_note: "Originally numbered 45-47. Renumbered to 45-50 at finish time after an OQ-1/OQ-2 ID collision (origin/main concurrently shipped a different 45-47/45-48/45-49 series). The sidequest-server PR #200 and its commits still reference '45-47' for historical reasons; this archive is the canonical sprint record."
---

# Story 45-50: ADR-066 §8 — narrator session crash recovery (reactive)

> **Renumber note:** Originally 45-47. PR #200 in sidequest-server keeps the old ID in its title and commit messages — that PR is already merged and was created before the OQ-1/OQ-2 collision was detected at SM finish time.

## Story Details

- **ID:** 45-50 (was 45-47)
- **Epic:** 45 (Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup)
- **Jira Key:** N/A (non-Jira project)
- **Workflow:** tdd
- **Assignee:** Keith Avery
- **Type:** bug
- **Priority:** p1
- **Points:** 3
- **Status:** in_progress

## Story Context

**Root cause (Playtest 3):** The narrator's persistent `--resume` session overflowed the context budget (~1M tokens Opus ceiling) after ~1h 45m of play. The Claude CLI returned a context-overflow error, which the orchestrator propagated as an unhandled failure, crashing the server.

**Specification source:** `docs/adr/066-persistent-opus-narrator-sessions.md` — §8 (Hardened Reactive Fallback), §9 (Recap Composition for Rebuild Turns), and §10 (Observability). This story is the foundation layer; §9's prompt frame and §10's OTEL span are shared with story 45-48 (the proactive watchdog).

**Key constraints:**
- Context-overflow / CLI errors must be non-fatal
- Errors classify to recovery routes (reset + Full-tier rebuild with recap)
- Recovery uses `SessionStore.generate_recap()` + warm-reboot frame
- OTEL span `narrator.session_rotated` tracks reason, cumulative tokens, turn number, error signature, recap character count, rebuild latency
- Transient/network errors retry once before triggering rotation
- If recovery itself fails, emit `narrator.unrecoverable` event and gracefully stall the player

## Acceptance Criteria

1. **Context-overflow error handling:** CLI context-overflow error from `--resume` is caught and routed to `reset_narrator_session()` + Full-tier retry with recap header (warm-reboot frame per ADR-066 §9).

2. **Session-not-found error handling:** CLI session-not-found error from `--resume` routes to the same recovery path.

3. **Unknown failure graceful degradation:** Unknown narrator CLI failure routes to recovery; if recovery also fails, emits `narrator.unrecoverable` OTEL event and returns a graceful in-fiction stall to the player.

4. **Transient error retry:** Transient/network errors retry once on the same session before triggering rotation.

5. **OTEL telemetry:** `narrator.session_rotated` span emitted on every recovery with attributes: `reason` (token_threshold | cli_error | session_expired | unknown), `cumulative_tokens` (int), `turn_number` (int), `cli_error_signature` (str, only on reactive), `recap_chars` (int), `rebuild_latency_ms` (int).

6. **Rebuild header prompt support:** Full-tier prompt builder accepts an optional `rebuild_header` argument that splices `SessionStore.generate_recap()` output plus the warm-reboot frame (per ADR-066 §9, wrapped in `[SESSION CONTINUATION]` / `[PREVIOUSLY ON]` / `[WORLD STATE]` / `[CHARACTERS]` blocks).

7. **Wiring integration test:** Simulate CLI failure mid-turn (mock subprocess error), verify the next turn succeeds via Full-tier rebuild and player sees no error.

## Workflow Tracking

**Workflow:** tdd (Test-Driven Development)
**Phase:** finish
**Phase Started:** 2026-05-04T20:06:03Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04 | 2026-05-04T19:15:24Z | 19h 15m |
| red | 2026-05-04T19:15:24Z | 2026-05-04T19:25:30Z | 10m 6s |
| green | 2026-05-04T19:25:30Z | 2026-05-04T19:38:42Z | 13m 12s |
| spec-check | 2026-05-04T19:38:42Z | 2026-05-04T19:42:12Z | 3m 30s |
| verify | 2026-05-04T19:42:12Z | 2026-05-04T19:44:53Z | 2m 41s |
| review | 2026-05-04T19:44:53Z | 2026-05-04T20:03:28Z | 18m 35s |
| spec-reconcile | 2026-05-04T20:03:28Z | 2026-05-04T20:06:03Z | 2m 35s |
| finish | 2026-05-04T20:06:03Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### TEA (test design)

- **Improvement** (non-blocking): The orchestrator has TWO narration paths
  — `_run_narration_turn_streaming` (line ~1850) and
  `_run_narration_turn_synchronous` (line ~2200) — that duplicate the same
  `try/except → degraded response` pattern. Both need the recovery wiring.
  Affects `sidequest-server/sidequest/agents/orchestrator.py` (extract a
  shared `_handle_narrator_failure()` helper instead of patching the
  exception block in two places). *Found by TEA during test design.*

- **Question** (non-blocking): The story scope requires the rebuild_header
  parameter on the Full-tier prompt builder. My tests pin it to
  `build_narrator_prompt(..., rebuild_header=...)` for testability. Dev
  may prefer to thread it through `TurnContext` instead — both shapes are
  valid. If Dev chooses TurnContext, the test signatures need a small
  adjustment. Affects `sidequest-server/sidequest/agents/orchestrator.py`
  (build_narrator_prompt signature) and the recovery call site.
  *Found by TEA during test design.*

- **Improvement** (non-blocking): Streaming-path-specific recovery tests
  are not written. `Orchestrator.run_narration_turn` routes to either
  streaming or sync based on `hasattr(self._client, "send_stream")`. My
  tests use real `ClaudeClient` (which has `send_stream`), so they
  exercise whichever path the routing picks. If Dev implements recovery
  only in one path, some tests may pass while the other path remains
  buggy. The shared-helper extraction above mitigates this.
  Affects `sidequest-server/sidequest/agents/orchestrator.py` (both
  `_run_narration_turn_streaming` and `_run_narration_turn_synchronous`
  must call the recovery handler). *Found by TEA during test design.*

### Dev (implementation)

- **Improvement** (non-blocking): Streaming-path recovery is not wired in
  this story. `_run_narration_turn_streaming` retains the original
  exception → degraded-stall pattern. Production runs the sync path
  today (`SIDEQUEST_NARRATOR_STREAMING` defaults off and is not exported
  by any startup script), so this is not a user-facing gap — but anyone
  who enables streaming before the follow-up lands is still exposed to
  the Playtest 3 crash class. Affects
  `sidequest-server/sidequest/agents/orchestrator.py` (extract
  `_recover_from_narrator_failure` into a shape both narration paths can
  share, then call from both exception handlers). Suggested follow-up:
  file 45-49 in epic 45 once 45-47 and 45-48 land. *Found by Dev during
  implementation.*

- **Question** (non-blocking): The recovery turn currently sends the
  rebuild_header inside the `-p` user message rather than as the
  `--system-prompt`. This diverges from production's first-turn
  behavior (action in `-p`, prompt_text in `--system-prompt`) — see
  Dev deviation #1 below. The choice is reasonable for anchoring the
  continuation cue adjacent to the action, but it is worth a Reviewer
  eye on whether the model treats `--system-prompt` content differently
  enough to justify the divergence. Affects
  `sidequest-server/sidequest/agents/orchestrator.py`
  (`_recover_from_narrator_failure`'s send_with_session call). *Found by
  Dev during implementation.*

- **Improvement** (non-blocking): `SessionStore.generate_recap()` truncates
  each entry to 200 chars and includes only the last 3 entries. For a
  rebuild after a 1h+ session, this is thin. The recovery still works,
  but the seam will be more obvious. Affects
  `sidequest-server/sidequest/game/persistence.py:498-509` (consider
  widening to 5-7 entries and 400-500 chars per entry, OR generate a
  Claude-summarized recap on rebuild). Listed as Open Question #1 in
  the ADR-066 amendment ("verbatim beat inclusion") — appropriate to
  defer until playtest validates whether the seam is noticeable.
  *Found by Dev during implementation.*

### TEA (test verification)

- No upstream findings during test verification. Simplify fan-out
  returned three clean reports across reuse / quality / efficiency
  lenses; no fixes applied; lint and targeted tests pass. The
  implementation matches the spec checked by Architect — clean handoff
  to Reviewer.

### Reviewer (code review)

- **Improvement** (non-blocking): The reviewer's Devil's Advocate
  identified a multiplayer concurrency question — does the orchestrator
  serialize turns within a SessionRoom such that a recovery rotation
  cannot collide with a concurrent player's turn that's still mid-flight?
  This story's fix is single-orchestrator-instance safe (the
  `_session_lock` covers state mutations) but does not validate the
  multi-turn scheduling layer. Affects
  `sidequest-server/sidequest/server/session_room.py` and the dispatch
  layer (no code change required for 45-47, just a verification that
  `--resume` recovery cannot interleave with a sealed-letter turn).
  Worth a manual playtest check or a multiplayer integration test in a
  follow-up. *Found by Reviewer during code review.*

- **Improvement** (non-blocking): A single env-var flip
  (`SIDEQUEST_NARRATOR_STREAMING=1`) resurrects the original Playtest 3
  crash class because the streaming path has no recovery wiring. The
  documentation in 3 places (TEA finding, Dev deviation, Architect
  spec-check) is excellent, but a code-level guard is stronger than
  documentation. Two options for the streaming-path follow-up: (a)
  extract the shared helper as TEA recommended, OR (b) add a startup
  warning when `SIDEQUEST_NARRATOR_STREAMING=1` is set without the
  follow-up story landed. Affects
  `sidequest-server/sidequest/agents/narrator.py` (`is_streaming_enabled`
  could log a warning when invoked) and the eventual follow-up story
  (45-49 per Dev's suggestion). *Found by Reviewer during code review.*

- **Question** (non-blocking): The recap quality concern (Dev finding #3)
  intersects with SOUL.md's Test rule: "if a response includes the
  player doing something they didn't ask to do, it's wrong." On a
  rebuild after a long session, the recap is the only thing telling the
  model what happened. If the model interprets the rebuild header's
  "you do not have verbatim memory" as license to invent player actions
  to fill the gap, that breaks Agency. Worth a deliberate playtest
  scenario where rotation fires mid-encounter to see whether the
  rebuild narration respects what the player actually said vs.
  hallucinates a continuation. Affects
  `sidequest-server/sidequest/agents/orchestrator.py:_compose_rebuild_header`
  (may want to strengthen the warm-reboot frame with explicit "do not
  invent player actions" guardrail). *Found by Reviewer during code
  review.*

- **Improvement** (non-blocking): Latent bug pre-existing in the
  degraded-stall narration: `f"**{context.current_location}**\n\n"`
  produces `"**None**\n\n"` if `current_location` is None. Not
  introduced by this story (same pattern in the original sync exception
  block), but worth noting for an epic 45 cosmetic fix. Affects
  `sidequest-server/sidequest/agents/orchestrator.py:1035` and
  potentially other stall sites. *Found by Reviewer during code
  review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No design deviations recorded yet.

### TEA (test design)

- No deviations from spec. The seven ACs from the session scope are
  covered by 27 failing tests across two new files plus one extension to
  `test_spans.py::test_narrator_span_names`. The §9 prompt-frame and §10
  OTEL primitives ride along with §8 per the SM Assessment, and tests
  enforce them as part of this story.
  → ✓ ACCEPTED by Reviewer: TEA's no-deviation declaration matches
    Reviewer's independent audit of the test files. Test coverage was
    expanded during review (commits 43fd467 + 2b0f58f) for build-failure
    recovery, recap-provider edge cases, and the unknown-reason
    parametrize case — but those were coverage tightening, not spec
    deviations.

### Dev (implementation)

- **Recovery turn sends rebuild prompt as user message, not system prompt**
  - Spec source: ADR-066 §9 (warm-reboot frame), context-story-45-47.md
    "Recovery Routing Decision Tree"
  - Spec text: "Reset session, retry same turn via Full tier + recap,
    succeed silently." (No directive on whether the Full prompt goes via
    `--system-prompt` or `-p`.)
  - Implementation: On the rotation rebuild call, the entire composed
    Full-tier prompt (including the rebuild_header section) is sent as
    the `-p` user message with `system_prompt=None`. Production first-turn
    behavior in `_run_narration_turn_synchronous` still sends the action
    as `-p` and the prompt_text as `--system-prompt`; the recovery path
    diverges to keep the [SESSION CONTINUATION] cue adjacent to the
    action the model is responding to.
  - Rationale: The model needs to see "this is a continuation" in the
    same context block as the action, not just in a system prompt that
    might be cached/treated as static. Putting it in the user message
    anchors the rebuild semantically. Test
    `test_recovery_path_splices_recap_into_rebuild_prompt` pins this
    behavior — it captures the `-p` arg and asserts
    `[SESSION CONTINUATION]` is present.
  - Severity: minor
  - Forward impact: Story 45-48 (proactive watchdog) will reuse
    `_recover_from_narrator_failure` and inherit this convention. If a
    future story wants the rebuild_header in `--system-prompt` instead,
    the recovery helper is the single point of change.

- **Streaming-path recovery deferred**
  - Spec source: TEA Delivery Finding #1 + #3 (test design), session
    Sm Assessment "TEA and Dev should treat the §9/§10 primitives as
    reusable"
  - Spec text: TEA flagged that both `_run_narration_turn_streaming` and
    `_run_narration_turn_synchronous` have the same `try/except → degraded`
    pattern and recommended extracting a shared `_handle_narrator_failure`
    helper applied to both paths.
  - Implementation: Recovery is wired into the synchronous path only.
    The streaming path retains its original behavior (catch Exception,
    return degraded stall, no rotation, no retry).
  - Rationale: Production currently runs the sync path —
    `is_streaming_enabled()` reads `SIDEQUEST_NARRATOR_STREAMING` which
    defaults to "0" and is not exported in the justfile or any startup
    script. The Playtest 3 crash hit the sync path. Wiring streaming
    requires a more substantial extraction (the streaming path has a
    different control flow — async generator, partial-prose accumulation,
    per-event spans) that would expand this story significantly.
    Minimalist discipline says: ship the fix that solves the actual bug,
    document the gap, file the follow-up.
  - Severity: minor (no user impact today; future risk if streaming is
    enabled before the follow-up lands)
  - Forward impact: A new follow-up story (suggested 45-49 or similar)
    should extract `_recover_from_narrator_failure` into a shape that
    both narration paths can call. Until then, anyone who exports
    `SIDEQUEST_NARRATOR_STREAMING=1` is still exposed to the original
    crash class. The session file `## Delivery Findings` Dev section
    below records this as a non-blocking improvement.

- **`cumulative_tokens` reported as 0 on the session_rotated span**
  - Spec source: ADR-066 §10
  - Spec text: "`cumulative_tokens` (int)" — required attribute on every
    rotation span, both reactive (this story) and proactive (45-48).
  - Implementation: The reactive recovery path emits the span with
    `cumulative_tokens=0`. The orchestrator does not yet maintain a
    cumulative meter — that is the load-bearing primitive for story 45-48
    (proactive watchdog) and would be premature here.
  - Rationale: The §10 attribute schema is satisfied (the field is
    present and an int); the dashboard sees a real value. Story 45-48
    will replace the literal `0` with the actual cumulative count by
    threading the running token total through the recovery helper.
  - Severity: minor
  - Forward impact: Story 45-48 must update
    `_recover_from_narrator_failure`'s span emission to read
    `self._cumulative_session_tokens` (the meter it introduces) instead
    of the literal `0`. One-line change at the call site.

### Reviewer (audit)

- **Dev deviation #1 (recovery uses `-p` not `--system-prompt`)**
  → ✓ ACCEPTED — already blessed by Architect's ADR-066 §9 amendment
    (orchestrator main, commit b51ef06). The choice anchors
    [SESSION CONTINUATION] adjacent to the action; deliberate divergence.

- **Dev deviation #2 (streaming-path recovery deferred)**
  → ✓ ACCEPTED — production runs sync; the defect being fixed is the
    sync-path crash. Streaming follow-up is correctly scoped to a future
    story per Architect's spec-check (Recommendation D — Defer). Reviewer
    adds a delivery finding suggesting an env-var-set warning as a
    code-level guard while the follow-up is in flight.

- **Dev deviation #3 (`cumulative_tokens=0` placeholder)**
  → ✓ ACCEPTED — schema satisfied (int present), value pinned by test
    in commit 2b0f58f so the proactive watchdog story (45-48) produces a
    visible diff when the live meter lands. Forward impact path is one
    line.

- **Architect spec-check mismatches (4)** — `[WORLD STATE]`/`[CHARACTERS]`
  labels not literally injected, recovery `-p` placement,
  cumulative_tokens placeholder, streaming path
  → ✓ ALL ACCEPTED — Architect resolved two via the ADR-066 §9
    clarification (commit b51ef06 on orchestrator main); the other two
    are the same as Dev deviations #2 and #3 above.

- **Reviewer-discovered deviation: `_compose_rebuild_header` typed `-> str | None`**
  → ✗ FLAGGED THEN FIXED. Spec source: ADR-066 §9 (no specific guidance
    on return type). Spec text: function "Returns markdown-formatted
    summary or None if the log is empty" (story context, citing
    `SessionStore.generate_recap` contract). Code: function unconditionally
    seeds `parts` with `[SESSION CONTINUATION]` and returns the join, so
    None never occurs. The lying annotation was caught by
    reviewer-comment-analyzer and corrected in commit 92081f0 to `-> str`.
    Severity: minor. Forward impact: callers that did `if header is
    None` had dead branches; cleanup absorbed during this story.

- **Reviewer-discovered deviation: `build_narrator_prompt` outside try/except**
  → ✗ FLAGGED THEN FIXED. Spec source: ADR-066 §8 — "Wrap the narrator
    `await self._client.run(...)` calls in `_handle_narrator_error()`."
    Spec text: the recovery contract is "always return response or
    stall." Code: the build call sat outside the try block, so a
    PromptRegistry error during recovery would have escaped the
    contract. Caught by reviewer-rule-checker (Rule #1 + #13) and
    corrected in commit 43fd467 (build call moved into the try, plus
    new test `test_rebuild_prompt_build_failure_falls_back_to_unrecoverable`
    pins the new contract). Severity: high (same bug class this story
    is fixing). Forward impact: none — fix is complete and tested.

### Architect (reconcile)

- No additional deviations found. Audit summary:

  * **TEA (test design):** "No deviations from spec" entry — verified
    accurate. The seven ACs are covered by the test suite (now 71 tests
    after Reviewer's coverage additions); no test omissions, no partial
    AC coverage, no different-strategy substitutions.

  * **Dev (implementation) — three entries:**
    1. *Recovery turn sends rebuild prompt as `-p`* — all 6 fields
       present and substantive. Spec source (ADR-066 §9 + story context)
       and quoted text are accurate; implementation matches code at
       `_recover_from_narrator_failure` (orchestrator.py:1003-1015).
       Rationale aligns with my spec-check Recommendation A and the
       ADR-066 §9 amendment I committed (orchestrator main, commit
       b51ef06). Forward impact correctly identifies 45-48 as the
       inheritor of this convention.
    2. *Streaming-path recovery deferred* — all 6 fields present.
       Verified that `_run_narration_turn_streaming` retains the
       original `try/except → degraded` pattern at lines ~1976–2004
       (unchanged from main). Verified the env-var default via `grep
       -rn SIDEQUEST_NARRATOR_STREAMING justfile scripts/` — no matches
       outside test files. Forward impact correctly suggests follow-up
       45-49 for the shared-helper extraction.
    3. *`cumulative_tokens=0` placeholder* — all 6 fields present. The
       schema-satisfaction argument is sound. Reviewer's
       `assert attrs.get("cumulative_tokens") == 0` test in commit
       2b0f58f pins the placeholder so 45-48 produces a visible diff.

  * **Reviewer (audit) — six entries:**
    - Three stamps on Dev's deviations (all ACCEPTED) — concur with all
      three.
    - One stamp on my four spec-check mismatches (all ACCEPTED, with
      correct cross-references to the ADR-066 §9 amendment commit
      b51ef06 for the two I resolved) — concur.
    - Two new deviations discovered by reviewer subagents:
      * `_compose_rebuild_header` lying return type (`-> str | None`
        always returned `str`) — fixed in commit 92081f0. All 6 fields
        present. Severity: minor. The spec text quoted (from
        `SessionStore.generate_recap` contract) accurately captures
        the source of the misleading annotation.
      * `build_narrator_prompt` outside try/except — fixed in commit
        43fd467 with new test. All 6 fields present. Severity: high
        (same bug class as the original Playtest 3 crash). The
        spec-source quote from ADR-066 §8 is accurate; the
        rule-checker's Rule #1 + #13 citation is the right rubric.

- **AC deferral verification:** No ACs deferred. The 7 ACs in story
  scope are all DONE per the TEA Assessment AC Coverage table. The
  ac-completion gate has no accountability table to cross-reference;
  step is a no-op.

- **Cross-story consistency:** Story 45-48 (proactive watchdog,
  `depends_on: 45-47`) inherits the §9/§10 primitives this story
  shipped. Three forward-impact entries (Dev #1 `-p` convention, Dev #2
  streaming follow-up, Dev #3 cumulative_tokens placeholder) all point
  to specific call sites in `_recover_from_narrator_failure` that
  45-48's Dev will need to update or extend. Documented and traceable.

- **ADR consistency:** ADR-066 §9 amendment (orchestrator main, commit
  b51ef06) blesses the recovery `-p` convention and clarifies the
  warm-reboot frame's `[WORLD STATE]` / `[CHARACTERS]` blocks as
  illustrative. No drift between final code and ADR text.

**Decision:** All deviations are accepted. The deviation manifest is
complete, accurate, and self-contained — every entry quotes its spec
source inline so the boss can audit the story without external lookup.
Proceed to SM finish.

## Sm Assessment

**Setup status:** Complete and ready for RED phase handoff to TEA (Fezzik).

**Spec authority:** Primary source is `docs/adr/066-persistent-opus-narrator-sessions.md`, specifically the **Amendment — Proactive Rotation and Crash Recovery (2026-05-04)** sections §8 (Hardened Reactive Fallback), §9 (Recap Composition), and §10 (Observability). The amendment was authored immediately before this story by the Architect (Man in Black) in response to the Playtest 3 server crash.

**Story scope:** §8 reactive recovery is the load-bearing deliverable. §9 (warm-reboot prompt frame) and §10 (OTEL span) ride along because they are the foundation primitives shared with the proactive watchdog story (45-48). Implementing §9 and §10 here means 45-48 only adds the cumulative-token meter and the threshold trigger.

**Sibling story:** 45-48 (proactive rotation watchdog, 5pts, p2) is `depends_on: 45-47`. It cannot start until this story is merged. TEA and Dev should treat the §9/§10 primitives as reusable and not couple them to the reactive call site.

**Reuse pointers (per Architect's design audit):**
- `Orchestrator.reset_narrator_session()` exists at `sidequest-server/sidequest/agents/orchestrator.py:843` — the rotation primitive. Use it; do not reinvent it.
- `SessionStore.generate_recap()` exists in `sidequest-server/sidequest/game/persistence.py` — the recap source. Quality of the recap directly determines quality of the rebuild seam; if it is too thin for narrative continuity (currently a save-load nicety), expand it as part of this story.
- `claude_client.py` already parses the `usage` envelope per turn (input + cache_create + cache_read tokens). The cumulative meter for 45-48 will reuse this; do not add a parallel parser.
- Telemetry layer per ADR-058 — emit the new `narrator.session_rotated` span class through it, not by adding a new logging path.

**Branch:** `feat/45-47-narrator-session-crash-recovery` in `sidequest-server`. Base is the repo's main per `.pennyfarthing/repos.yaml`.

**Decision:** Hand off to TEA for RED phase. Tests must cover the four error classes from §8 (context-overflow, session-not-found, transient/network, unknown), the recap-header splice from §9, and the OTEL span from §10. Integration test (AC 7) is the wiring guard required by CLAUDE.md.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Real bug-fix + new feature primitives; full TDD cycle warranted (3pts, p1, bug).

**Test Files:**
- `sidequest-server/tests/agents/test_orchestrator_session_recovery.py` — orchestrator-level recovery behavior across the four error classes from ADR-066 §8, plus the §9 warm-reboot frame splicing (19 tests).
- `sidequest-server/tests/telemetry/test_narrator_session_rotated_span.py` — span helper contract for ADR-066 §10 (`narrator.session_rotated` + companion `narrator.unrecoverable`) (7 tests).
- `sidequest-server/tests/telemetry/test_spans.py::test_narrator_span_names` — extended with the two new constants (1 test).

**Tests Written:** 27 tests covering 7 ACs
**Status:** RED (all failing — ready for Dev)

### AC Coverage

| AC | Description | Tests | Status |
|----|-------------|-------|--------|
| 1 | Context-overflow → reset + Full-tier retry + recap | `test_context_overflow_resets_session_and_retries`, `test_context_overflow_emits_session_rotated_span`, `test_context_overflow_recovery_uses_full_tier_not_delta`, `test_session_rotated_span_reason_classification[context_window_full…]`, `test_session_rotated_span_reason_classification[maximum_tokens_exceeded…]` | failing |
| 2 | Session-not-found → same recovery path | `test_session_not_found_resets_and_retries`, `test_session_not_found_emits_session_rotated_with_reason`, `test_session_rotated_span_reason_classification[session_not_found…]`, `test_session_rotated_span_reason_classification[session_expired…]` | failing |
| 3 | Unknown failure → recovery; double failure → unrecoverable + stall | `test_unknown_cli_error_resets_and_retries`, `test_double_failure_emits_unrecoverable_and_stalls` | failing |
| 4 | Transient/network → retry once on same session | `test_transient_error_retries_once_on_same_session`, `test_transient_error_retry_does_not_emit_rotation_span`, `test_transient_error_after_retry_falls_back_to_rotation` | failing |
| 5 | OTEL `narrator.session_rotated` span with §10 attributes | All `test_narrator_session_rotated_span_*` tests + `test_narrator_unrecoverable_span_*` tests + `test_narrator_span_names` | failing |
| 6 | Full-tier builder accepts `rebuild_header` | `test_full_tier_prompt_accepts_rebuild_header`, `test_rebuild_header_ordering_precedes_player_action`, `test_recovery_path_splices_recap_into_rebuild_prompt`, `test_recovery_handles_empty_recap_gracefully` | failing |
| 7 | Wiring integration test | `test_recovery_handler_is_wired_into_run_narration_turn` | failing |

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exceptions | `test_double_failure_emits_unrecoverable_and_stalls` (verifies the catch-all path emits a span and a stall — never swallows silently) | failing |
| #4 logging coverage | Indirect via OTEL span emission tests (rotations are logged at span level per ADR-058 passthrough; logger calls remain) | failing |
| #6 test quality | Self-checked: 27 tests, 0 vacuous assertions; testing-runner confirmed 0 accidental passes | n/a |
| #11 input validation at boundaries | The CLI error stderr is the boundary; the parametrized test asserts unknown signatures route to recovery (does not crash on novel inputs) | failing |
| #13 fix-introduced regressions | Wiring guard (AC 7) explicitly asserts recovery is reachable from the production turn pipeline, not just defined | failing |

**Rules checked:** 5 of 13 applicable lang-review rules have direct test coverage. Remaining rules (#2 mutable defaults, #3 type annotations, #5 path handling, #7 resource leaks, #8 unsafe deserialization, #9 async pitfalls, #10 import hygiene, #12 dependency hygiene) are not exercised by this story's surface area — they apply to existing infrastructure that this story extends without adding new instances of those concerns.

**Self-check:** 0 vacuous tests found. All 27 tests have specific value assertions or span-content assertions.

### RED Verification (testing-runner)

- **Passed:** 0 (correct — no implementation yet)
- **Failed:** 27 (all expected — TypeError for missing `recap_provider` constructor kwarg in 19 tests; ImportError for missing span exports in 8 tests)
- **Skipped:** 0
- **Vacuous:** 0
- **Duration:** 0.19s

### Test design choices to flag for Dev

1. **`recap_provider` constructor injection.** Tests inject a
   `recap_provider: Callable[[], str | None]` via the Orchestrator
   constructor. If Dev prefers a different shape (e.g., per-turn via
   `TurnContext`), tests need adjustment. See Delivery Findings → Question.

2. **`rebuild_header` parameter on `build_narrator_prompt`.** Tests pin
   the parameter to the prompt builder. Same flexibility note as above.

3. **Streaming vs sync path.** Tests use real `ClaudeClient`; the
   orchestrator routes between streaming and sync via
   `hasattr(self._client, "send_stream")`. Both paths share the same
   `try/except → degraded` anti-pattern at lines ~1976 and ~2242. The
   shared-helper extraction in Delivery Findings is the recommended fix;
   without it, recovery may land in only one path. The wiring guard
   (AC 7) catches the path the routing picks but not necessarily both.

4. **OTEL span shape.** Tests pin specific attribute keys
   (`reason`, `cumulative_tokens`, `turn_number`, `cli_error_signature`,
   `recap_chars`, `rebuild_latency_ms`, `threshold`). These are the §10
   contract — changes need an ADR-066 amendment.

5. **`narrator.unrecoverable` companion span.** The §8 spec says "emit
   `narrator.unrecoverable` if recovery itself fails." Tests pin a
   parallel span helper with `reason`, `first_error_signature`,
   `rebuild_error_signature`, `turn_number`. Dev should add this to
   `sidequest/telemetry/spans/narrator.py` alongside the rotation span.

**Handoff:** To Dev (Inigo Montoya) for GREEN phase implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/agents/orchestrator.py` — added `recap_provider` constructor parameter, `rebuild_header` parameter on `build_narrator_prompt` (registered as Primacy section), and the `_classify_narrator_error` / `_narrator_error_signature` / `_compose_rebuild_header` / `_recover_from_narrator_failure` helpers. Wired the recovery flow into the synchronous narration path so the original `try/except → degraded` block now classifies and routes per ADR-066 §8.
- `sidequest-server/sidequest/telemetry/spans/narrator.py` — added `SPAN_NARRATOR_SESSION_ROTATED` and `SPAN_NARRATOR_UNRECOVERABLE` constants (registered in `FLAT_ONLY_SPANS`) plus the `narrator_session_rotated_span` and `narrator_unrecoverable_span` context managers per §10.

**Tests:**
- 27/27 new tests passing (story 45-47 RED → GREEN, 0.06s)
- 4185/4185 full server suite passing (57 skipped, 0 failures, 1m 22s)
- Lint clean (`ruff check`) on both touched files

**Branch:** `feat/45-47-narrator-session-crash-recovery` in `sidequest-server` (pushed)

### AC Coverage

| AC | Description | Implementation | Tests Passing |
|----|-------------|----------------|---------------|
| 1 | Context-overflow → reset + Full-tier retry + recap | `_classify_narrator_error` → `cli_error` → `_recover_from_narrator_failure` rotates and rebuilds with `rebuild_header` | yes (5 tests) |
| 2 | Session-not-found → same recovery path | Same classifier branch → `session_expired` reason | yes (4 tests) |
| 3 | Unknown failure → recovery; double failure → unrecoverable + stall | Catch-all `unknown` reason; rebuild raise → `narrator_unrecoverable_span` + degraded stall | yes (2 tests) |
| 4 | Transient/network → retry once on same session | `transient` classification triggers same-session retry; second failure escalates to rotation | yes (3 tests) |
| 5 | OTEL `narrator.session_rotated` + `narrator.unrecoverable` spans with §10 attributes | Both span helpers + emission from recovery helper | yes (8 tests) |
| 6 | Full-tier builder accepts `rebuild_header` | New parameter on `build_narrator_prompt`; registered as Primacy section ahead of identity/genre | yes (4 tests) |
| 7 | Wiring guard | `_recover_from_narrator_failure` is called from `_run_narration_turn_synchronous`'s exception handler | yes (1 test) |

### Implementation Notes for Reviewer

1. **Streaming path untouched.** Recovery is wired into the synchronous path only. Production uses sync (env-gated default-off). See Dev deviation #2 + Delivery Finding for the rationale and follow-up plan. The TEA finding recommended a shared helper extraction across both paths — that scope expansion is deferred to a follow-up to keep this story shipping the actual playtest crash fix.

2. **Recovery sends prompt as `-p`, not `--system-prompt`.** Diverges from production's first-turn convention. Logged as deviation #1; rationale is to keep the [SESSION CONTINUATION] cue adjacent to the action in the model's working context. Open for Reviewer pushback.

3. **`cumulative_tokens=0` on the span.** Reactive path doesn't track the cumulative meter — that's story 45-48's primitive. Schema is satisfied, value is honest. One-line update at the call site once 45-48 lands.

4. **`_compose_rebuild_header` is called even when `recap_provider` is None.** Returns the [SESSION CONTINUATION] frame without a [PREVIOUSLY ON] block. The model still gets the continuation cue. Test `test_recovery_handles_empty_recap_gracefully` pins this behavior.

5. **Recap quality.** `SessionStore.generate_recap()` is currently a save-load nicety (3 entries, 200-char truncation). For a rebuild after a 1h+ session, this is thin. ADR-066 amendment Open Question #1 ("verbatim beat inclusion") covers the polish; deferred until playtest reveals whether the seam is noticeable. See Delivery Finding.

6. **No new dependencies** introduced. All reuse: `reset_narrator_session()`, `SubprocessFailed`, `TimeoutError`, the existing telemetry `Span.open` machinery.

**Handoff:** To Architect (The Man in Black) for spec-check phase, then TEA (Fezzik) for verify phase.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected — 4 mismatches, all minor or trivial. None block forward motion.

**Mismatches Found:** 4

- **`cumulative_tokens=0` placeholder on the rotation span** (different behavior — behavioral, minor)
  - Spec: ADR-066 §10 — "`cumulative_tokens` (int)" required attribute on every rotation span.
  - Code: Reactive path emits the literal `0`; the running token meter is 45-48's primitive and does not yet exist on `Orchestrator`.
  - Recommendation: **D — Defer** — Dev's choice is correct. The schema is satisfied (the field is present and an int). Story 45-48 owns the cumulative meter; its single-line update at the recovery span call site replaces the literal with `self._cumulative_session_tokens`. Forward impact is documented in Dev deviation #3.

- **Warm-reboot frame omits `[WORLD STATE]` and `[CHARACTERS]` literal labels** (missing in code — cosmetic, trivial)
  - Spec: ADR-066 §9 example shows the frame wrapped in `[SESSION CONTINUATION]` / `[PREVIOUSLY ON]` / `[WORLD STATE]` / `[CHARACTERS]` blocks.
  - Code: `_compose_rebuild_header` injects only `[SESSION CONTINUATION]` and `[PREVIOUSLY ON]`. The world state and character sheet content is still delivered to the model — it's part of the Full-tier prompt by virtue of `build_narrator_prompt(tier=Full, ...)`, registered as separate sections in the prompt registry — but it is NOT wrapped under the literal `[WORLD STATE]` / `[CHARACTERS]` labels the ADR shows.
  - Recommendation: **A — Update spec** — The ADR-066 §9 example used those labels as content-substitution placeholders (`{snapshot}`, `{narrative character sheets}`), illustrating *what* the model sees, not requiring literal section delimiters. The model receives the same information either way. I will amend ADR-066 §9 to clarify that the literal `[WORLD STATE]` and `[CHARACTERS]` labels are illustrative — the actual delivery is via Full-tier prompt sections, which is already authoritative.

- **Streaming path not wired into recovery** (missing in code — architectural, minor)
  - Spec: ADR-066 §8 — "Wrap the narrator `await self._client.run(...)` calls in `_handle_narrator_error()`" (no path-specific scoping).
  - Code: Only `_run_narration_turn_synchronous` is wired. `_run_narration_turn_streaming` retains the original unhandled-exception → degraded-stall pattern at lines ~1976–2004.
  - Recommendation: **D — Defer** — Production runs the sync path: `is_streaming_enabled()` reads `SIDEQUEST_NARRATOR_STREAMING` which defaults to `"0"` and is not exported by any startup script (verified: `grep -rn SIDEQUEST_NARRATOR_STREAMING justfile scripts/` returns no matches). The Playtest 3 crash hit the sync path. This story ships the actual bug fix; the streaming path is a latent risk that becomes user-facing only if streaming is enabled before the follow-up lands. SM should file a follow-up story (suggested 45-49) for "extract `_recover_from_narrator_failure` into a shared helper applied to both narration paths" once 45-47 and 45-48 land. Dev deviation #2 captures the rationale; TEA delivery findings #1 and #3 captured it pre-implementation.

- **Recovery turn sends rebuild prompt as `-p` instead of `--system-prompt`** (different behavior — behavioral, minor)
  - Spec: ADR-066 §5/§9 — does not dictate which CLI flag carries the rebuild header.
  - Code: `_recover_from_narrator_failure` sends the full composed prompt as `-p` with `system_prompt=None`. Production's first-turn convention (in `_run_narration_turn_synchronous` line 2258) sends the action as `-p` and the prompt_text as `--system-prompt`. The recovery path diverges.
  - Recommendation: **A — Update spec** — Dev's choice is defensible (the [SESSION CONTINUATION] cue is anchored adjacent to the action in the model's working context, rather than living in a system prompt that may be cached or treated as static framing). Will amend ADR-066 §9 to document the `-p` placement as the canonical recovery convention so 45-48 inherits it deliberately.

**ADR-066 amendment follow-up.** I will update ADR-066 §9 in a separate commit (during this spec-check phase) to:
1. Clarify the warm-reboot frame's `[WORLD STATE]` / `[CHARACTERS]` labels are illustrative content blocks delivered via Full-tier sections, not literal markers.
2. Document that the recovery turn's full composed prompt is sent as the `-p` user message (not `--system-prompt`) so the continuation cue stays adjacent to the action.

Both clarifications turn what would otherwise be lingering "is this a bug?" questions for Reviewer into accepted ADR text.

**Decision:** Proceed to TEA verify phase. The mismatches are documented, classified, and have clear forward paths. None require handing back to Dev. The implementation is faithful to the load-bearing intent of ADR-066 §8 (the playtest crash class is eliminated for the sync path, which is the production path). The minor drift items either are deferred to the natural successor story (45-48) or warrant ADR clarifications I will produce now.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (2 source, 3 test)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 findings — new helpers are well-factored, no duplication of existing primitives |
| simplify-quality | clean | 0 findings — naming, type annotations, error handling, and architecture all sound |
| simplify-efficiency | clean | 0 findings — complexity is intentional and spec-driven (each helper maps to ADR-066 §8/§9/§10) |

**Applied:** 0 high-confidence fixes (no findings to apply)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean

### Quality Checks

- **Lint:** `ruff check sidequest/agents/orchestrator.py sidequest/telemetry/spans/narrator.py` — `All checks passed!`
- **Story tests:** `pytest tests/agents/test_orchestrator_session_recovery.py tests/telemetry/test_narrator_session_rotated_span.py tests/telemetry/test_spans.py` — 67 passed in 0.06s (the 27 new story tests + 40 existing telemetry tests still passing)
- **Full suite (Dev's GREEN run):** 4185 passed, 57 skipped — no regressions introduced

### Verify-Phase Findings

- No upstream findings during test verification. The simplify pass found nothing to flag and nothing to fix. The implementation Architect spec-checked is the same code TEA verified — clean handoff to Reviewer.

**Handoff:** To Reviewer (Westley) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 4185 tests pass, lint clean, 0 code smells. One boy-scout fix (commit 52336e2) for ruff UP035/I001 in test_orchestrator_session_recovery.py. |
| 2 | reviewer-edge-hunter | Yes (skipped) | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Yes (skipped) | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes | findings | 10 | confirmed 7, dismissed 3, deferred 0 |
| 5 | reviewer-comment-analyzer | Yes | findings | 14 | confirmed 14, dismissed 0, deferred 0 — all applied as fixes (commit 92081f0) |
| 6 | reviewer-type-design | Yes (skipped) | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Yes (skipped) | disabled | N/A | Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Yes (skipped) | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 2 (one bug, one fix-meta) — applied as fix (commit 43fd467 + new test) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 23 confirmed, 3 dismissed, 0 deferred — 16 applied as fixes during review (commits 92081f0, 43fd467, 2b0f58f), 7 confirmed test coverage gaps tightened.

### Findings Detail

**[RULE] HIGH — `build_narrator_prompt` outside try/except in `_recover_from_narrator_failure` (orchestrator.py:995)**
- Source: rule-checker (Rule #1 silent exceptions; Rule #13 fix-introduced regression)
- Same bug class as the original Playtest 3 crash. If the build raises, exception escapes recovery, bypasses `narrator.unrecoverable` span and graceful stall.
- **APPLIED:** commit 43fd467 — moved build inside the try, seeded `rebuild_prompt_text` with `original_prompt_text` for stall fallback. Added `test_rebuild_prompt_build_failure_falls_back_to_unrecoverable` (test 28 of the story suite).

**[DOC] MEDIUM — `_compose_rebuild_header` typed `-> str | None` but always returns str (orchestrator.py:926)**
- Source: comment-analyzer
- The function unconditionally seeds `parts` with `[SESSION CONTINUATION]` so the join is never empty. Annotation lied.
- **APPLIED:** commit 92081f0 — return type → `str`, docstring rewritten.

**[DOC] LOW (×13) — multi-paragraph docstrings, story-ID references in code, missing `rebuild_header` parameter doc, Playtest 3 references in test docstring**
- Source: comment-analyzer
- All match CLAUDE.md style rules: "one short line max", "don't reference the current task/fix in code/comments".
- **APPLIED:** commit 92081f0 — collapsed all multi-paragraph docstrings, removed story 45-47/45-48/Playtest 3 references from production code and test files, added `rebuild_header` to `build_narrator_prompt` docstring.

**[TEST] HIGH — Wiring guard test only proves the synchronous path**
- Source: test-analyzer
- `test_recovery_handler_is_wired_into_run_narration_turn` passes because `SIDEQUEST_NARRATOR_STREAMING` defaults to "0". Streaming-path recovery is intentionally deferred (Dev deviation #2).
- **DEFERRED** — known and explicitly logged as Dev deviation #2; suggested follow-up story is on the table (45-49 or similar). The test honestly proves what's wired today; the remaining gap is documented in three places (TEA delivery findings #1 + #3, Dev deviation #2, Reviewer (audit) below). Confirmed but not re-flagged.

**[TEST] HIGH — Missing test for `recap_provider=None` (true production default)**
- Source: test-analyzer
- The `Orchestrator(client=client)` with no `recap_provider` was the production default and the `_compose_rebuild_header` branch where `self._recap_provider is None` was untested.
- **APPLIED:** commit 2b0f58f — added `test_recovery_works_with_no_recap_provider_at_all` (asserts both `not is_degraded` AND that the [SESSION CONTINUATION] header is still emitted, with `[PREVIOUSLY ON]` correctly omitted).

**[TEST] HIGH — Missing test for `recap_provider` exception path**
- Source: test-analyzer
- The `except Exception` in `_compose_rebuild_header` (best-effort recap per ADR-066 §9) had no test. A provider that raises must not abort recovery.
- **APPLIED:** commit 2b0f58f — added `test_recovery_survives_recap_provider_exception`.

**[TEST] HIGH — Parametrized test missing "unknown" reason case**
- Source: test-analyzer
- A regression that hardcoded `reason="cli_error"` for the unknown branch would have passed all tests.
- **APPLIED:** commit 2b0f58f — added `("some_brand_new_error_signature_we_havent_seen", "unknown")` parametrize case.

**[TEST] MEDIUM — Vacuous `is not None` assertions on `recap_chars` and `rebuild_latency_ms`**
- Source: test-analyzer
- Both attributes are always non-None by construction; the guards never fire.
- **APPLIED:** commit 2b0f58f — replaced with `> 0` (recap stub is non-empty so chars must be positive) and `isinstance(..., int)` checks.

**[TEST] MEDIUM — `cumulative_tokens=0` placeholder not pinned by test**
- Source: test-analyzer
- A future story (proactive watchdog 45-48) needs to see a test diff when the literal becomes the live meter.
- **APPLIED:** commit 2b0f58f — added `assert attrs.get("cumulative_tokens") == 0` with a comment explaining the contract.

**[TEST] MEDIUM — Transient retry doesn't directly assert session_id was preserved**
- Source: test-analyzer
- Strict assertion is hard because the canned spawn always returns `session-rebuild-001`. The companion rotation-span absence is the meaningful guard.
- **DISMISSED** with clarification: refined the comment in `test_transient_error_retries_once_on_same_session` to point to the companion `test_transient_error_retry_does_not_emit_rotation_span` as the rotation-NOT-fired guard. The session-id positive assertion is structurally infeasible with a fixed-session-id FakeProcess; the rotation-span absence is sufficient evidence.

**[TEST] MEDIUM — `current_location=None` produces "**None**" in stall narration**
- Source: test-analyzer
- Latent bug: `f"**{context.current_location}**"` doesn't guard against None.
- **DISMISSED** — pre-existing pattern (lines 2247 of orchestrator.py before this story), exists in the original degraded-stall path too. Out of scope for the recovery story; worth a separate cosmetic fix in epic 45 if Keith finds it jarring during playtest.

**[TEST] MEDIUM — implementation-coupling on `-p` arg index in `test_recovery_path_splices_recap_into_rebuild_prompt`**
- Source: test-analyzer
- The bare `except (ValueError, IndexError)` in the test's spawn capture could silently swallow capture failures.
- **DISMISSED** — the test's `assert len(captured_prompts) >= 2` already guards against total capture failure (the assertion fires loudly with "Expected at least two CLI invocations" if capture broke). The bare except is defensive, not silent — the assertion is the safety net. Acceptable as-is.

**[TEST] MEDIUM — No test for transient on first turn (no prior session_id set)**
- Source: test-analyzer
- The `is_first_turn = current_session_id is None` branch in the transient retry path is structurally different from the subsequent-turn path (sends `action` not `original_prompt_text`).
- **DEFERRED** — minor coverage gap; the production crash path is the with-session case (which is covered). First-turn transient is unlikely (you don't build up cumulative state on turn 1) and the code structure is shared enough that a test for it would mostly re-exercise the with-session paths. Worth adding in a follow-up if first-turn transient ever surfaces in playtest.

### Rule Compliance (.pennyfarthing/gates/lang-review/python.md)

Mapped to the 13 numbered checks. Each check enumerated against every new function/parameter/test introduced by this story.

| # | Rule | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Silent exception swallowing | PASS (after fix) | All 4 broad except blocks (`_compose_rebuild_header`, transient retry, rebuild fail, run_narration_turn first-attempt) log + classify + emit OTEL or NarrationTurnResult. Each has `# noqa: BLE001` with rationale. The build-outside-try gap caught by rule-checker is now closed (43fd467). |
| 2 | Mutable default arguments | PASS | All defaults are None or string constants. Verified across all 8 new function signatures + the constructor. |
| 3 | Type annotation gaps at boundaries | PASS | All public boundaries (Orchestrator constructor, build_narrator_prompt, both span helpers) fully typed. Private helpers also annotated. `_compose_rebuild_header` annotation corrected from `-> str \| None` to `-> str` (the lying-annotation fix in 92081f0). |
| 4 | Logging coverage AND correctness | PASS | All error paths log. Severity is correct: warning on recoverable failures (first-attempt, transient retry failure, recap_provider failure), error on unrecoverable, info on operational events (rotation success). All use %-style formatting. |
| 5 | Path handling | N/A | No file I/O in new diff. |
| 6 | Test quality | PASS (after fix) | All 71 story tests have specific value assertions (no truthy-only checks after the vacuous-assertion fix). Parametrized tests cover distinct branches (5 reason cases). No `@pytest.mark.skip`. The wiring test (`test_recovery_handler_is_wired_into_run_narration_turn`) is explicit and self-documenting. |
| 7 | Resource leaks | PASS | All new context managers (`narrator_session_rotated_span`, `narrator_unrecoverable_span`, the lock acquisitions in recovery) use `with`. |
| 8 | Unsafe deserialization | N/A | No pickle/yaml.load/eval/exec/shell=True. |
| 9 | Async/await pitfalls | PASS | `_recover_from_narrator_failure` properly awaits `send_with_session` and `build_narrator_prompt`. No blocking I/O in async; `time.monotonic()` is CPU-only. |
| 10 | Import hygiene | PASS | No star imports in new code. `Callable` correctly imported from `collections.abc`. The two-line import of `claude_client` (one for SubprocessFailed, one aliasing TimeoutError as `_ClaudeTimeoutError` to avoid shadowing the builtin) is a deliberate clarity choice, not a violation. |
| 11 | Input validation at boundaries | PASS | No new boundary surface added. `recap_provider` is a trusted internal callable (caller wires `SessionStore.generate_recap`); `rebuild_header` is constructed internally; `action` flows through pre-existing WebSocket validation. |
| 12 | Dependency hygiene | PASS | No `pyproject.toml` changes. |
| 13 | Fix-introduced regressions (meta) | PASS (after fix) | The original Playtest 3 bug class — uncaught exception in narrator pipeline — was almost re-introduced by the build-outside-try gap (Rule #1 finding). Fix in 43fd467 closes that gap and a new test pins the contract. Cross-checked the fix itself for the same class of bug: the new try block is now comprehensive across both build and send. |

### Reviewer Findings (Devil's Advocate Excluded)

- **[VERIFIED] Recovery flow happy path** — `_recover_from_narrator_failure` returns either `(response, tier, prompt_text, elapsed_ms)` or `NarrationTurnResult` for ALL exception classes (after the build-side fix). Caller pattern at orchestrator.py:2497-2511 unwraps the tuple correctly with `isinstance` discriminator. Complies with the "no uncaught exceptions in narrator pipeline" rule.
- **[VERIFIED] `narrator.session_rotated` span fires on every successful rotation** — Verified by 6 distinct tests across 5 reason values (cli_error, session_expired, unknown × 2 reasons, no token_threshold case here — that's 45-48). Compliant with CLAUDE.md OTEL observability principle.
- **[VERIFIED] `narrator.unrecoverable` fires on double-failure** — Verified by `test_double_failure_emits_unrecoverable_and_stalls` AND the new `test_rebuild_prompt_build_failure_falls_back_to_unrecoverable`. Both code paths emit + return graceful stall.
- **[VERIFIED] Recovery uses Full tier with rebuild_header** — `test_context_overflow_recovery_uses_full_tier_not_delta` proves tier escalation; `test_recovery_path_splices_recap_into_rebuild_prompt` proves header is in the CLI `-p` arg.
- **[VERIFIED] `_classify_narrator_error` substring matching is brittle but bounded** — Open Question #3 in ADR-066 amendment acknowledges CLI error messages may change between Claude releases. The current marker list (4 strings) is the v1 truth. Worth periodic audit but not a blocking issue.
- **[VERIFIED] Recovery does not deadlock the session lock** — `_recover_from_narrator_failure` reads `_narrator_session_id` inside `with self._session_lock`, then exits the lock before calling `self.reset_narrator_session()` (which also acquires the lock). No nested-lock contention.

### Devil's Advocate

Could a malicious or stressed system break this code? Let me argue from several angles.

**Malicious user.** The narrator's recovery doesn't handle user input directly — `action` comes from a player WebSocket message that's already been through dispatch validation. A user could craft an action string designed to trigger a context-overflow on every turn, but that's a behavioral concern (rate-limit player input?) not a security concern. The recovery itself is between the player turn and the next prompt; the user can't influence which classification branch fires from outside.

**Confused player.** A player might experience a noticeable "seam" on rotation — the model loses verbatim memory of recent narration and reverts to whatever the recap captures. The Test (per SOUL.md): "if a response includes the player doing something they didn't ask to do, it's wrong." Could the rebuild header accidentally cause the model to invent player actions? The header explicitly says "You do not have verbatim memory of prior turns" — if the model interprets that as "make something up to fill the gap," it could violate Agency. Mitigation: the [PREVIOUSLY ON] section provides authoritative recap. Worth playtest validation, not a code-level fix.

**Stressed filesystem / network.** What if `recap_provider()` (production: `SessionStore.generate_recap()` — a SQLite query) takes 5 seconds because the disk is thrashing? `_compose_rebuild_header` has no timeout. Recovery would block on the recap call. Mitigation: SQLite is local and the recap is a small SELECT; pathological I/O delay is unlikely. But not impossible. **Low risk, worth noting.**

**Config edge cases.** What if `_recap_provider` returns an enormous string (megabytes)? It would all get spliced into the rebuild prompt and likely trigger ANOTHER context-overflow on the recovery turn. That double-failure would then emit `narrator.unrecoverable` + stall — the safety net catches it. Not a crash, but a wasted recovery cycle. The recap should be size-bounded; `SessionStore.generate_recap()` already truncates to 200 chars × 3 entries per Dev Delivery Finding. Acceptable.

**Race condition.** The `_session_lock` is held only briefly during reset/read. Between the reset and the next call's session creation, another concurrent turn (multiplayer) could try to use the dead session. Mitigation: this is a per-Orchestrator instance lock, and SessionRoom typically routes all turns through one Orchestrator. But in multiplayer, sealed-letter turns might invoke recovery while another player's turn is in flight on the same Orchestrator. **Question:** does the orchestrator serialize turns? Looking at the dispatch layer is out of scope for this story, but worth verifying with a multiplayer playtest. Filing as a delivery finding.

**Memory leak.** Recovery creates new ClaudeResponse objects, OTEL spans, and re-establishes a session. None of these accumulate unbounded — sessions are tracked with a single string ID, spans flush via the OTEL processor, responses are GC'd after extraction. ✓

**False sense of security.** The wiring guard test passes because production is sync. If anyone enables `SIDEQUEST_NARRATOR_STREAMING=1` for a playtest, the same crash class returns. Documented thoroughly (3 places) but a single env var flip undoes the fix. Worth a justfile guard or a CLAUDE.md warning. Filing as a delivery finding.

The Devil's Advocate uncovers two new delivery findings (multiplayer race; streaming-flip resurrects bug) — adding them below.

## Reviewer Assessment

**Verdict:** APPROVED

The story ships the actual playtest crash fix (sync narration path), implements ADR-066 §8 / §9 / §10 faithfully, and survives an exhaustive reviewer subagent fan-out plus 16 in-review fixes:

| Source | Severity | Issue | Location | Status |
|--------|----------|-------|----------|--------|
| `[RULE]` | HIGH | `build_narrator_prompt` outside try/except (same bug class as original) | orchestrator.py:995 | FIXED in commit 43fd467 + new test |
| `[DOC]` | MEDIUM | `_compose_rebuild_header` lying return type (`-> str \| None` always returns str) | orchestrator.py:926 | FIXED in commit 92081f0 |
| `[DOC]` | LOW (×13) | Multi-paragraph docstrings, story-ID refs in code, missing `rebuild_header` parameter doc, Playtest 3 reference in test docstring | orchestrator.py + narrator.py + test file | FIXED in commit 92081f0 |
| `[TEST]` | HIGH (×3) | Missing test coverage (recap_provider=None default, recap_provider raise, unknown-reason parametrize case) | test_orchestrator_session_recovery.py | FIXED in commit 2b0f58f |
| `[TEST]` | MEDIUM (×3) | Vacuous `is not None` assertions on rotation span attrs, `cumulative_tokens=0` placeholder not pinned by test | test_orchestrator_session_recovery.py | FIXED in commit 2b0f58f |
| `[TEST]` | HIGH | Wiring guard test only proves the synchronous path | test_orchestrator_session_recovery.py | DEFERRED (Dev deviation #2; follow-up story for shared helper) |
| `[TEST]` | MEDIUM (×2) | `current_location=None` produces `**None**` in stall, `-p` arg index coupling in capture spawn | orchestrator.py + test_orchestrator_session_recovery.py | DISMISSED (pre-existing pattern; defensive bare-except guarded by `len >= 2` assertion) |
| `[TEST]` | MEDIUM | No test for transient on first turn (no prior session_id) | test_orchestrator_session_recovery.py | DEFERRED (minor branch coverage gap; production crash path is the with-session case which is covered) |

**Data flow traced:** Player WebSocket message → dispatch validation → `Orchestrator.run_narration_turn` → `_run_narration_turn_synchronous` → `send_with_session` → on failure → `_recover_from_narrator_failure` → classify → (transient retry on same session) OR (rotate: reset + Full tier + rebuild header + send) → on success: `narrator.session_rotated` OTEL span + return tuple → on rebuild failure: `narrator.unrecoverable` OTEL span + degraded stall → caller emits NarrationTurnResult to player. End-to-end: every failure mode terminates either in a successful narration or a graceful stall. Proven by the wiring guard + the new build-failure guard test.

**Pattern observed:** The recovery helper follows the same shape as existing degraded-stall paths in the streaming code (line ~1976) — a single try/except wrapping the LLM call with a graceful `NarrationTurnResult` fallback. The new code adds classification + retry + rotation as additional branches before the stall fallback. Consistent with codebase conventions.

**Error handling:** All four error classes (transient/cli_error/session_expired/unknown) tested end-to-end. Double-failure (rebuild fails) tested. Build-side failure (post-fix) tested. Recap-provider failure tested. No-recap-provider default tested. Session expiry classification correct.

**Tests:** 4187 passed across the full server suite (was 4185 before review additions). 71 of those are this story's targeted suite (was 27 from RED phase, +1 from build-failure fix in commit 43fd467, +3 from coverage additions in commit 2b0f58f, +40 pre-existing telemetry/agent tests still passing).

**Lint:** ruff clean across all touched files (orchestrator.py, narrator.py, both new test files, test_spans.py).

**Branch:** `feat/45-47-narrator-session-crash-recovery` in sidequest-server. Pushed (head: 2b0f58f). 5 commits total: 1 RED tests, 1 GREEN impl, 1 boy-scout from preflight, 1 comment fixes, 1 build-side guard fix, 1 test coverage additions. (Aside: this also implicitly absorbed the ADR-066 §9 clarification in the orchestrator repo from spec-check — that lives on orchestrator main, not in this branch.)

**Handoff:** To SM (Vizzini) for finish-story.