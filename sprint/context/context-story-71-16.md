---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-16: ADR-113 — per-dispatch confidence scoring + threshold gating in the intent router

## Business Context

ADR-113 (Intent Router — Mechanical-Engagement Spine) decided that each mechanical
dispatch engages its engine **only at or above a confidence threshold** (default
0.6, tunable per-subsystem in genre pack `rules.yaml`); below threshold, the
dispatch degrades to a `narrator_instruction` hint rather than firing an engine.
The router spine shipped and is live end-to-end — but the **confidence gate was
never built**. Today every dispatch the router emits fires its engine
unconditionally.

Why it matters: the gate is the router's safety valve. Without it, a low-confidence
guess from the Haiku decomposition pass engages a real mechanical subsystem
(instantiates a confrontation, consumes a clue, fires NPC agency) with the same
authority as a high-confidence read. That produces exactly the failure the OTEL
"lie-detector" is meant to catch — mechanical state changing on a weak inference —
except here the engine genuinely ran, so it's not narrator improvisation, it's the
router over-committing. For the mechanics-first players this is the difference
between "the system engaged because I clearly did X" and "the system lurched
because the router 55%-guessed I might have." This story makes engagement
*legible and earned* (SOUL: Cost Scales with Drama — don't fire an engine on a
coin-flip).

This is the deferred half of ADR-113, and it is the prerequisite the playtest
validation story **59-8** is waiting on (no green multi-turn validation exists yet;
2026-05-26 playtests showed router degradation + dispatch noise).

## Technical Guardrails

**Provenance — do NOT re-investigate.** Surfaced by the ADR-accuracy audit
(Architect, 2026-05-28) and confirmed in code. ADR-113 now carries a 2026-05-28
amendment stating the gate is DEFERRED; this story implements it. Coordinate with
59-8 (its validation depends on this landing).

### Root cause / current state (file:line pinned)

1. **`run_dispatch_bank` fires every dispatch unconditionally.**
   `sidequest/agents/subsystems/__init__.py:186` (`run_dispatch_bank`); the
   execution loop iterates dispatches (see the loop near `:181`) and engages each
   handler with **no confidence read and no threshold compare**.
2. **There is no per-dispatch confidence field to gate on.**
   `sidequest/protocol/dispatch.py:88` `SubsystemDispatch` carries **no**
   `confidence`. The only confidence floats in the protocol are
   `Referent.confidence` (`dispatch.py:78`) and the package-level
   `DispatchPackage.confidence_global` (`dispatch.py:207`) — neither is consulted
   as an engagement gate.
3. **Threshold config does not exist.** No per-subsystem threshold is read from
   `rules.yaml`; ADR-113's "default 0.6, tunable" is unrepresented.

### Fix direction

- Add `confidence: float` (0.0–1.0) to `SubsystemDispatch` (`protocol/dispatch.py`);
  have the `IntentRouter` (`sidequest/agents/intent_router.py`) populate it per
  dispatch from the decomposition pass.
- In `run_dispatch_bank`, gate each dispatch: engage the engine only if
  `confidence >= threshold`; below threshold, degrade to a `narrator_instruction`
  hint (do NOT engage the engine) per ADR-113's Decision.
- Source the threshold per-subsystem from genre pack `rules.yaml` with a 0.6
  default; fail loud on a malformed threshold (No Silent Fallbacks).
- Emit OTEL per dispatch: confidence value + gate decision (`engaged` vs
  `degraded_to_hint`) + threshold used. This is the lie-detector for the gate
  itself.

### Constraints

- **Do not regress the live spine.** The router → `run_dispatch_bank` → engines →
  narrator ordering must remain intact (`intent_router_pass.py` called from
  `websocket_session_handler.py` before the narrator). This story adds a gate inside
  the bank, not a re-architecture.
- **Below-threshold ≠ dropped.** A gated-out dispatch must still inform the narrator
  as a hint (degrade path), not vanish — otherwise the player's intent is silently
  ignored (SOUL: the player can attempt anything; the system must respond).
- **No silent fallbacks.** Missing/invalid per-subsystem threshold → fail loud or
  use the documented 0.6 default *explicitly logged*, never a silent guess.
- **OTEL mandate (CLAUDE.md).** Every gate decision is a subsystem decision and must
  emit a span; the existing `dispatch_engagement_watcher` mismatch spans stay.
- **Wiring required.** Prove gating end-to-end through the production turn path
  (fixture-driven: a low-confidence dispatch does NOT engage its engine; a
  high-confidence one does), plus OTEL-span assertions. No source-text grep tests.

## Scope Boundaries

**In scope:**
- Protocol: `SubsystemDispatch.confidence` field.
- Router: populate per-dispatch confidence in `IntentRouter`.
- `run_dispatch_bank`: per-dispatch threshold gate + degrade-to-hint path.
- Config: per-subsystem threshold in `rules.yaml` (default 0.6).
- OTEL: per-dispatch confidence + gate-decision span.
- Tests: gating behavior, tunable threshold, degrade-to-hint, wiring, no-spine-regression.

**Out of scope:**
- The 59-8 playtest validation itself (separate story; this unblocks it).
- Re-tuning what confidence values the Haiku pass assigns (calibration is a
  follow-up once the gate exists and OTEL shows real distributions).
- Changes to the dispatch vocabulary / subsystem set (confrontation, magic_working,
  scenario_clue, npc_agency, distinctive_detail_hint, reflect_absence, movement).
- The double-dispatch cleanup (owned by 59-11) — do not entangle.

## AC Context

1. **Per-dispatch confidence:** `SubsystemDispatch` carries a validated
   `confidence: float` (0.0–1.0), populated by the `IntentRouter` for every emitted
   dispatch.
2. **Threshold gate:** In `run_dispatch_bank`, a dispatch engages its engine only
   when `confidence >= threshold`; below threshold it does NOT engage and instead
   produces a `narrator_instruction` hint (ADR-113 degrade path).
3. **Per-subsystem tunable threshold:** Threshold is read per-subsystem from genre
   pack `rules.yaml`, defaulting to 0.6; malformed config fails loud.
4. **OTEL (CLAUDE.md):** Each dispatch emits a span with its confidence, the
   threshold applied, and the decision (`engaged` | `degraded_to_hint`). GM panel
   can audit every gate decision.
5. **Spine intact:** The live router→bank→engines→narrator ordering is unchanged;
   high-confidence dispatches behave exactly as today.

### Test Guidance (TEA red phase)

- **Gate behavior (fixture-driven):** a dispatch with confidence below the subsystem
  threshold does NOT engage its engine (assert no encounter/clue/etc. state change)
  and produces a narrator hint; a dispatch at/above threshold engages. Drive through
  the real `run_dispatch_bank` path.
- **Tunable threshold:** a pack `rules.yaml` override changes the gate boundary for
  that subsystem; default is 0.6 when unset.
- **OTEL span assertions:** the per-dispatch gate span fires with confidence +
  decision for both engaged and degraded cases.
- **Spine regression:** the end-to-end intent-router pass still runs before the
  narrator and high-confidence dispatches engage as before.

### Files to Modify
- `sidequest/protocol/dispatch.py` — add `SubsystemDispatch.confidence`.
- `sidequest/agents/intent_router.py` — populate per-dispatch confidence.
- `sidequest/agents/subsystems/__init__.py` — gate in `run_dispatch_bank`.
- `sidequest/genre/models/rules.py` — per-subsystem threshold config (default 0.6).
- `sidequest/telemetry/` — gate-decision span.

## Assumptions

- ADR-113's 0.6 default and per-subsystem tunability are authoritative; this story
  implements them verbatim and leaves value-calibration to a follow-up informed by
  OTEL data.
- The Haiku decomposition pass can produce a meaningful per-dispatch confidence; if
  it currently only yields `confidence_global`, deriving per-dispatch confidence is
  in scope (prompt/parse change inside `IntentRouter`), but redesigning the router
  prompt wholesale is not.
- 59-8 remains the validation owner; this story's Definition of Done is the gate +
  OTEL, not a 30-turn green session.
