# Context: Story 45-47 — ADR-066 §8 Narrator Session Crash Recovery (Reactive)

**Status:** in setup phase
**Last updated:** 2026-05-04

## Primary Specification Source

- `docs/adr/066-persistent-opus-narrator-sessions.md` (2026-05-04 amendment)
  - §8: Hardened Reactive Fallback (lines 234–244)
  - §9: Recap Composition for Rebuild Turns (lines 250–283)
  - §10: Observability (lines 290–302)

## Playtest 3 Root Cause

Playtest 3 (2026-04-19) crashed ~1h 45m into a single narrator session when the persistent `--resume` session exceeded the Opus context ceiling (~1M tokens). The CLI returned:

```
OutOfContextError: "context_window_full" (or similar signature)
```

The orchestrator caught this as a generic subprocess failure and propagated it as an unhandled exception, bringing down the server. This is the event that prompted the 2026-05-04 amendment to ADR-066.

## Affected Code Areas

**sidequest-server (Python):**

1. **`sidequest/agents/orchestrator.py`** — `Orchestrator` class
   - `run_narration_turn()` — wraps the `--resume` call in error handler
   - `reset_narrator_session()` — resets `_narrator_session_id` and `_cumulative_session_tokens`
   - New `_handle_narrator_error()` method classifies error type and routes to recovery

2. **`sidequest/agents/claude_client.py`** — `ClaudeClient` class
   - `send_with_session()` — raises typed errors (SubprocessFailed, TimeoutError, EmptyResponse)
   - Error signatures must be queryable for classification (e.g., "context_window_full" in stderr)

3. **`sidequest/agents/prompt_framework/core.py`** (or relevant builder) — prompt tier assembly
   - Full-tier builder must accept optional `rebuild_header: str | None` parameter
   - When provided, injects `[SESSION CONTINUATION]` frame + recap before the player action

4. **`sidequest/game/persistence.py`** — `SessionStore` class
   - `generate_recap()` exists and is callable; generates "Previously On…" markdown
   - Used to compose the rebuild header

5. **`sidequest/telemetry/spans.py`** — span definitions
   - New span: `narrator_session_rotated_span()` with attributes per §10

## Error Classification Table (ADR-066 §8)

| Error Class | Detection | Action |
|---|---|---|
| Context-overflow / session-too-large | CLI stderr contains "context_window_full" or "maximum_tokens_exceeded" (signatures vary by Claude release) | Reset session, retry same turn via Full tier + recap, succeed silently |
| Session not found / expired by CLI | CLI stderr contains "session_not_found" or "session_expired" | Reset session, retry via Full tier + recap |
| Network / transient | timeout or subprocess I/O error | Retry once on same session before triggering rotation |
| Unknown narrator failure | Catch-all for unexpected errors | Reset session, retry via Full tier + recap; if recovery also fails, emit `narrator.unrecoverable` OTEL event + graceful in-fiction stall |

## Warm-Reboot Frame (ADR-066 §9)

When a session rebuild is triggered (proactive or reactive), splice this header into the Full-tier prompt:

```
[SESSION CONTINUATION]

The narration that follows is a continuation of an in-progress game.
You do not have verbatim memory of prior turns, but the world state
and recap below are authoritative. Resume narration in the established
tone and voice. Honor the hooks and NPC arcs in play.

[PREVIOUSLY ON]
{SessionStore.generate_recap() output}

[WORLD STATE]
{snapshot world state block — already in Full tier}

[CHARACTERS]
{narrative character sheets — already in Full tier}
```

Without this frame, the rebuilt session can revert to introductory prose and break continuity.

## OTEL Observability (ADR-066 §10)

Every rotation (proactive or reactive) emits:

```python
narrator_session_rotated_span(
    reason="cli_error" | "session_expired" | "token_threshold" | "unknown",
    cumulative_tokens=<int>,
    turn_number=<int>,
    threshold=<int> if reason == "token_threshold" else None,
    cli_error_signature="context_window_full" if reason == "cli_error" else None,
    recap_chars=<int>,
    rebuild_latency_ms=<int>,
)
```

The GM panel (Sebastien's mechanical-visibility lane) shows rotation events and can diagnose threshold tuning from the dashboard.

## SessionStore.generate_recap() Contract

```python
def generate_recap(self) -> str | None:
    """Generate a 'Previously On...' recap from recent entries.
    
    Returns markdown-formatted summary of the last 3 narrative_log entries,
    or None if the log is empty. Used as the [PREVIOUSLY ON] section of
    the warm-reboot frame on session rebuild.
    """
```

Current implementation in `sidequest/game/persistence.py:498–509` exists and works. This story validates that it's fit for purpose (prose quality sufficient for re-grounding); §9 implementation polish is deferred to story 45-48 or later if needed.

## Recovery Routing Decision Tree (ADR-066 §8)

```
narrator --resume fails
├── stderr contains context_window_full → ROUTE: reset + Full-tier retry + recap
├── stderr contains session_not_found → ROUTE: reset + Full-tier retry + recap
├── timeout or I/O error → ROUTE: retry once on same session
│   └── retry succeeds → ROUTE: continue turn normally
│   └── retry fails → ROUTE: reset + Full-tier retry + recap
└── unknown error → ROUTE: reset + Full-tier retry + recap
    └── recovery itself fails → EMIT: narrator.unrecoverable span
        └── RETURN: graceful in-fiction stall to player
```

## Dependencies

**Blocking on this story:** 45-48 (proactive watchdog) depends on this as its foundation. The rebuild path must be proven solid before 45-48 adds the proactive rotation trigger.

**Upstream:** None. This is a pure hardening layer.

## Testing Strategy

**RED phase (Tea):**
- Failing tests for each error class: context-overflow, session-not-found, network timeout, unknown error
- Fixture: mock `ClaudeClient.send_with_session()` to raise each error type
- Test: orchestrator catches, classifies, calls recovery path
- Test: recovery path succeeds and next turn completes without player error
- Test: OTEL span fires with correct attributes per error class

**GREEN phase (Dev):**
- Implement error handler in `run_narration_turn()`
- Extend `ClaudeClient` to expose error signatures (stderr/exception text)
- Extend Full-tier prompt builder to accept `rebuild_header` argument
- Implement `reset_narrator_session()` call and recap splicing
- Implement OTEL span emission
- All RED tests pass; lint clean

**Integration (Dev + TEA verify phase):**
- End-to-end: simulate CLI failure mid-turn → verify graceful recovery → next turn succeeds
- Snapshot test: verify `narrator.session_rotated` span attributes match §10 schema

## Open Questions (Deferred to Implementation)

1. Should rebuild header include the last 3–5 verbatim narration beats from `narrative_log` for tighter continuity? (Trade-off: token cost vs. seam smoothness. ADR defers; acceptable for §8 to leave generic.)

2. Should "baited but uneaten" hooks (per SOUL.md) be promoted from implicit-in-narrative to a structured field on `GameState`? (ADR defers; recap quality may argue for it in §9 phase.)

3. Error signature detection: are CLI error messages stable across Claude releases? (May need periodic audit; acceptable for v1 to use substring matching on known signatures.)

## Cross-story Coordination

- **45-48 (proactive watchdog):** Depends on this story's rebuild path. Once this lands and tests are green, 45-48 adds the proactive rotation trigger (token threshold check + preemptive reset call).
- **45-49 (future, if filed):** §9 recap quality improvements (verbatim beat inclusion, hook structuring) are deferred.

---

**Generated:** 2026-05-04 (setup phase)
**Story lifecycle:** setup → red → green → spec-check → verify → review → spec-reconcile → finish
