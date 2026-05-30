---
parent: context-epic-73.md
workflow: trivial
---

# Story 73-5: Suppress re-fired confrontation_initiated span

**ID:** 73-5 | **Epic:** 73 (Confrontation Engine Hardening) | **Points:** 1 |
**Workflow:** trivial | **Type:** chore | **Repo:** sidequest-server

## Business Context

The GM panel is SideQuest's lie-detector: it reads OTEL signals to verify the
confrontation engine actually engaged rather than Claude improvising. When a
player's final action *resolves* a confrontation, the narrator extraction still
reports `confrontation=<type>` for that turn, and the orchestrator re-emits the
`encounter.confrontation_initiated` log signal — even though no new encounter was
created. The panel then renders one confrontation as **two initiations**, making
a clean single duel look like a double-fire and undermining the very audit trail
the panel exists to provide.

This is dev-side observability hygiene (Keith's lie-detector, not a Sebastien/Jade
player-facing surface). It is the one place in this epic where touching a span is
the *point* of the story — the artifact being fixed IS the emitted signal, so the
OTEL-hygiene framing is appropriate here rather than a misapplication of the
"don't name dev tools after players" rule. The fix makes the panel honest: one
`confrontation_initiated` per confrontation, at genuine initiation only.

## Technical Guardrails

The genuine-initiation span is **already correctly single-fire** at the engine
seam — do not touch it:

- `sidequest/server/dispatch/encounter_lifecycle.py` — `instantiate_encounter_from_trigger`
  (def at line 680) emits the real `encounter_confrontation_initiated_span` at
  **line 904**, *inside* the active-unresolved guard. The early-return guard at
  **lines 735-736** (`if current is not None and not current.resolved: return None`)
  already prevents a second creation-time span when an encounter is live. On a
  resolution turn the router re-dispatches through `run_confrontation_dispatch`
  (`sidequest/agents/subsystems/confrontation.py:49`, calls into the lifecycle at
  line 147), which re-enters the helper and returns `None` at the guard — **no
  second span at line 904**. This path is correct; leave it alone.

- `sidequest/telemetry/spans/encounter.py` — `encounter_confrontation_initiated_span`
  (def at **line 424**), `SPAN_ENCOUNTER_CONFRONTATION_INITIATED` (line 66). The
  real span machinery is fine; this story does not modify the span definition.

The actual re-fire is the cosmetic INFO-level `logger.info` re-emit in the narrator
extraction path of the orchestrator (these are plain log strings, *not* calls to
`encounter_confrontation_initiated_span`):

- `sidequest/agents/orchestrator.py:3093-3097` (streaming path) — `if extraction["confrontation"]:`
  → `logger.info("encounter.confrontation_initiated confrontation_type=%s", ...)`.
- `sidequest/agents/orchestrator.py:3348-3352` (sync / non-SDK path) — the same
  guard and log line.

Both fire whenever `extraction["confrontation"]` is truthy, with **no check** for
whether this turn *initiates* versus *resolves* an already-active encounter of that
type. Gate the re-emit so the signal fires only at genuine initiation — e.g. skip
the log when an active unresolved encounter of that type already exists on
`snapshot.encounter` (the same condition the lifecycle guard at lines 735-736
uses), or when the turn resolves rather than initiates. Fix **both** sites
(streaming and sync) identically — they are duplicate code paths and a one-sided
fix leaves the other backend leaking the dup.

Do not change the dial math, the resolution detection, the lifecycle guard, or the
genuine-initiation span. This is a pure suppression of a redundant cosmetic emit.

## Scope Boundaries

**In scope:** Gate the `confrontation_initiated` re-emit at
`orchestrator.py:3093-3097` and `3348-3352` so it fires once per confrontation
(at initiation, not on the resolution turn). A behavioral / span-count assertion
proving exactly-once.

**Out of scope:** The other epic-73 stories — sibling opposed_check conversions
(73-1/73-2), the `advance_confrontation` lost-update (73-3), push-CritSuccess
legibility (73-4). No `rules.yaml` edits. No changes to the lifecycle guard, the
span definition, or `run_confrontation_dispatch` (its re-dispatch already
correctly no-ops via the guard). No new spans — this story *removes* noise, it
does not add observability.

## AC Context

Derived (no explicit ACs on this chore). Keep to 2-3 tight, testable assertions:

- **AC1 — exactly-once:** Across a confrontation's full lifecycle
  (initiate → advance → resolve), the `encounter.confrontation_initiated` signal
  is emitted **exactly once**, at genuine initiation. The resolution turn does
  **not** re-emit it. Assert on the count (caplog on the orchestrator logger,
  or span-count if routed through a span), not on source text.
- **AC2 — resolution turn carries its own signal:** The resolving turn still
  produces its proper resolution span (`encounter_resolved_span`,
  `encounter_lifecycle.py:1178`) — the suppression removes only the spurious
  *initiation* re-emit, it must not swallow the genuine resolution signal.
- **AC3 — genuine initiation unaffected:** A real first-time confrontation
  initiation still emits `confrontation_initiated` exactly as before (no
  regression to the line-904 span or the first-turn log emit).

**Edge cases to cover:** (a) a confrontation initiated *and* resolved in the same
turn — must still emit initiation once, not zero and not twice; (b) back-to-back
confrontations (one resolves, a genuinely new one of the same or different type
initiates on the next turn) — the new confrontation gets its own single
initiation signal; the suppression must key on the *active-encounter* condition,
not on a once-per-session latch that would starve the second confrontation.

## Assumptions

- The gating condition is reachable from the orchestrator extraction sites:
  `snapshot.encounter` (and its `.resolved` / type fields) is the same state the
  lifecycle guard at `encounter_lifecycle.py:735-736` reads. If the orchestrator
  context does not already carry the active-encounter state at lines 3093/3348,
  prefer reading it from the in-flight snapshot the turn already holds rather than
  re-loading — and fail loud rather than silently skipping if the state isn't
  reachable (No Silent Fallbacks).
- Both orchestrator emit sites are duplicate cosmetic logs (not the real span);
  the correct fix narrows the `if extraction["confrontation"]:` guard, not the
  span definition or the lifecycle path.
- "Fires once" is asserted behaviorally (log/span count over a driven lifecycle),
  per the repo's No Source-Text Wiring Tests rule — not by grepping
  `orchestrator.py`.
