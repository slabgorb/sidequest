---
parent: context-epic-81.md
workflow: tdd
---

# Story 81-3: Feed PacingHint into TurnContext so the [PACING] injection fires (ADR-025)

## Business Context

ADR-025 promises that the narrator receives a pacing hint each turn — accelerate when things
have gone quiet, give room when stakes are high — derived from the dual-track tension signal.
The plumbing for this exists: `TurnContext` has a `pacing_hint` field and the orchestrator
already knows how to inject a `[PACING]` section from it. But the field is never set, so the
guard `if context.pacing_hint is not None` never passes and the narrator never sees a hint.
This story closes the last link: derive the hint from the live `TensionTracker` (81-2) at
`TurnContext` construction and pass it through, so the narrator's pacing is mechanically
grounded and the GM panel can see the hint that was computed — turning improvised pacing into
an observable, verifiable decision.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 line anchors may drift):**
- `sidequest/server/session_helpers.py:1158` — the sole `TurnContext(...)` construction site; today it omits `pacing_hint`. This is where the hint must be derived and passed.
- `sidequest/agents/orchestrator.py:728` — `pacing_hint: PacingHint | None = None` field on `TurnContext`.
- `sidequest/agents/orchestrator.py:2648-2653` — consumption: `if context.pacing_hint is not None: ... register_pacing_section(hint)` (the `[PACING]` injection that currently never fires).
- `sidequest/game/tension_tracker.py` — `pacing_hint(thresholds)` (the producer call) and `DramaThresholds`.
- Genre config — where `DramaThresholds` come from for the active pack (resolve from genre/config, not hardcoded).

**Patterns to follow:**
- This is the consumer/bridge half of the 81-2 producer. Read the tracker that 81-2 put on
  `_SessionData`; do not construct a new tracker here.
- OTEL lie-detector: emit a watcher/OTEL event recording the computed hint per turn, so the
  GM panel can confirm the hint is real and see what drove it.
- Honor the existing `if ... is not None` guard — passing a real hint is the whole fix; don't
  remove the guard.

**Integration points / what NOT to touch:**
- Do not change `register_pacing_section` or the `[PACING]` prompt format — they work once a
  hint arrives.
- Do not re-open quiet-turn detection or trope_tick accelerator/decelerator scanning (deferred).

## Scope Boundaries

**In scope:**
- Derive `pacing_hint` from the session `TensionTracker` + genre `DramaThresholds` at the
  `session_helpers.py:1158` construction and pass it into `TurnContext`.
- A watcher/OTEL event for the computed hint.
- An end-to-end wiring test: tracker → `TurnContext.pacing_hint` → `[PACING]` in the prompt.

**Out of scope:**
- Standing up / feeding the `TensionTracker` (81-2 — this story depends on it).
- ADR-025's original quiet-turn pre/post game-state diff.
- The accelerator/decelerator keyword scan stubbed at `trope_tick.py:226-230`.

## AC Context

1. **Hint is derived and set.** `TurnContext` construction derives `pacing_hint` from the
   session `TensionTracker` via `pacing_hint(thresholds)` using the active genre's
   `DramaThresholds`. On a turn where accumulated tension warrants it, `pacing_hint` is
   non-None. Edge case: when the tracker has no meaningful signal (fresh session / neutral
   state), the hint may legitimately be None — assert the system handles both without error.
2. **Injection fires.** With a non-None hint, the orchestrator's `register_pacing_section`
   runs and the assembled narrator prompt contains the `[PACING]` section. Test at the
   prompt-assembly layer: assert the section is present when a hint is set and absent when it
   is None (proving the guard still works).
3. **OTEL observable.** A watcher/OTEL event records the per-turn computed pacing hint so the
   GM panel can verify it. Assert the event is emitted with the hint value on a real turn.
4. **End-to-end wiring test.** A test ties `TensionTracker` state → `TurnContext.pacing_hint`
   → `[PACING]` section in the narrator prompt. It fails on current `develop` (hint always
   None, section never present) and passes after the fix. Full `just server-test` green;
   `just server-lint` clean.

## Assumptions

- **Depends on 81-2 being merged first** — this story reads the `TensionTracker` from
  `_SessionData`. If 81-2 is not yet merged, this is blocked (the dependency is recorded in
  the sprint YAML via `depends-on: 81-2`).
- `DramaThresholds` are resolvable from the active genre pack's config at the construction
  site; if they are not yet exposed there, surfacing them is a small in-scope addition — log a
  deviation if it turns out to be larger.
- The orchestrator's `[PACING]` section format is acceptable as-is; this story does not tune
  the hint's wording, only ensures it is produced and injected.
