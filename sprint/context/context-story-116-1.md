# Context: 113-1 — F2a Fate Action Classifier

## Summary

The freeform-text counterpart to F1d's explicit `FATE_ACTION` channel. When a player types prose in a pack bound `ruleset: fate` with an active conflict, the existing Intent Router (Haiku, forced tool-use) classifies the action into a **new** `fate_action` subsystem dispatch, and the dispatch bank routes it — pre-narrator — to the **same** engine entry F1d uses, `dispatch_fate_action`. A new `fate.action.classified` OTEL span anchors the F2 lie-detector: the GM panel can confirm the Fate action was engaged *from language*, not improvised. Two entry channels (explicit message + freeform classification), one engine entry. No second classifier, no duplicate engine entry (CLAUDE.md "Don't Reinvent").

## Architecture Overview

F2a rides the existing pre-narrator spine (ADR-113) — nothing parallel is built.

**Classification path (freeform):**
1. Player types prose → `IntentRouter` (existing Haiku forced-tool-use call) sees a `fate` block in the per-turn state summary + the static `FATE_ROUTING_RULES` and emits a `SubsystemDispatch(subsystem="fate_action", params={action, skill, target, difficulty, invoke_aspect, aspect_text})`.
2. Precondition gate drops the dispatch (loud `intent_router.dispatch.gated`) if there is no active/unresolved encounter — `fate_action` is conflict-scoped.
3. Dispatch bank (confidence gate ≥ default) resolves `fate_action` → `run_fate_action_dispatch`.
4. Handler builds a `FateActionPayload`, emits `fate.action.classified`, calls `dispatch_fate_action` (F1d) on the canonical snapshot BEFORE the narrator runs.
5. The exchange seals/resolves; F2b/F2c later narrate already-real Fate state.

**Why pre-narrator:** mechanical engagement happens on the canonical snapshot first, so the narrator narrates already-real Fate state — the producer-side Illusionism counter the confrontation subsystem already delivers. The GM panel's `fate.action.classified` (emitted before dispatch) + the F1 exchange/engagement spans make the whole path auditable.

**Conditional vocabulary:** the `fate` state-summary block is gated on `pack.rules.ruleset == "fate"` (absent for native packs); `FATE_ROUTING_RULES` is behaviorally conditional ("emit `fate_action` ONLY when a `fate` block is present"), so it is safe in the static cached system prompt — non-Fate packs never carry a `fate` block and never emit a `fate_action`. Same discipline as `confrontation_types` / `witnessed_act_vocabulary`.

## Key Files

### Core Infrastructure (Already Exist — F1a–F1d, merged to develop)
- `sidequest/server/dispatch/fate_conflict.py` — `dispatch_fate_action`, `FateConflictError` (the one engine entry; conflict-scoped)
- `sidequest/protocol/fate.py` — `FateActionPayload` (action/skill/target/difficulty/invoke_aspect/aspect_text)
- `sidequest/game/ruleset/` — `get_ruleset_module("fate")` → `FateRulesetModule`
- `sidequest/game/fate_sheet.py` — `FateSheet`, `Aspect` (skills, fate points, aspects, stress, consequences)
- `sidequest/agents/intent_router.py` — the existing `IntentRouter` + `_SYSTEM_PROMPT`
- `sidequest/server/intent_router_pass.py` — `_build_state_summary` (per-turn router state)
- `sidequest/agents/subsystems/__init__.py` — `_register_defaults`, `get_registered`, `run_dispatch_bank`, `SubsystemOutput`
- `sidequest/agents/dispatch_precondition_gate.py` — `_INERT_PRECONDITIONS`, `_GATE_DISPATCHED_TYPE_KEY`, `run_dispatch_precondition_gate`
- `sidequest/telemetry/spans/fate.py` — the 12 live Fate spans + `SPAN_ROUTES`

### New in This Story
- `sidequest/agents/subsystems/fate_action.py` — `run_fate_action_dispatch` (the freeform→payload→engine bridge)
- `sidequest/telemetry/spans/fate.py` — `fate_action_classified_span` + `SPAN_ROUTES["fate.action.classified"]`
- `sidequest/agents/subsystems/__init__.py` — `("fate_action", run_fate_action_dispatch)` registry entry + docstring bullet
- `sidequest/server/intent_router_pass.py` — `_build_fate_summary` + the gated `fate`-block enrichment
- `sidequest/agents/intent_router.py` — `FATE_ROUTING_RULES` spliced into `_SYSTEM_PROMPT`
- `sidequest/agents/dispatch_precondition_gate.py` — `_fate_action_precondition_unmet` + map entries
- Tests: `tests/telemetry/test_fate_action_classified_span.py`, `tests/agents/subsystems/test_fate_action_dispatch.py`, `tests/server/test_fate_classifier_enrichment.py`, `tests/agents/test_fate_action_precondition_gate.py`, `tests/server/test_fate_classifier_wiring.py`

## Acceptance Criteria

- **AC1:** `fate_action_classified_span` + `SPAN_ROUTES["fate.action.classified"]` (state_transition / fate; field=action_classified + actor/action/skill/target/confidence); routing-completeness lint stays green; added to `__all__`.
- **AC2:** `run_fate_action_dispatch` builds `FateActionPayload` from `dispatch.params`, emits the classified span, routes to `dispatch_fate_action`; registered in `_register_defaults`. Invalid action → `ValueError`; non-Fate ruleset / no conflict / unseated actor → `FateConflictError` caught → `data["error"]="fate_dispatch_error"` (no silent success).
- **AC3:** `_build_fate_summary` projection; `fate` block added to `_build_state_summary` ONLY for `pack.rules.ruleset == "fate"` (absent for native); `FATE_ROUTING_RULES` in `_SYSTEM_PROMPT`.
- **AC4:** `_fate_action_precondition_unmet` drops out-of-conflict `fate_action` (emits `intent_router.dispatch.gated`); registered in `_INERT_PRECONDITIONS` + `_GATE_DISPATCHED_TYPE_KEY`.
- **AC5:** end-to-end wiring test — runtime `get_registered()` membership + a freeform `fate_action` driven through the **real** `run_dispatch_bank` + **real** `get_ruleset_module("fate")` reaches `dispatch_fate_action`, resolves the exchange, fires `fate.action.classified` + `fate.exchange.resolved`.
- **AC6:** scoped lint/format/pyright clean on changed files; F2a + Fate + router suites green (incl. routing-completeness); non-Fate dispatch spine proven untouched.

## Doctrine & Constraints

- **ADR-144 / SOUL "Bind the Ruleset, Don't Balance It":** F2a binds the Fate SRD four-action core. There is no native engine on the Fate path to balance against — do NOT recreate, convert, or gate any native beat/dial mechanic to "make it work with" Fate.
- **No `full_defense` creep:** Fate's actions are overcome / create_advantage / attack / concede (+ reactive Defend). A "full/total defense +2 stance" is a d20-ism NOT in the Fate SRD — keep it out of the classifier and routing rules. (Keith caught this smuggled into F1c.)
- **OTEL lie-detector:** wiring proven via the new span + runtime `get_registered()` + real-bank drive — NEVER a source-text grep (server CLAUDE.md "No Source-Text Wiring Tests"). The classify span emits BEFORE dispatch so classify-without-engage is visible.
- **No Silent Fallbacks:** invalid action raises; non-Fate / no-conflict surface as `data["error"]`; precondition drop is loud.
- **In-conflict scope only:** out-of-conflict overcome (plain `resolve_action`) is epic §7.1's named follow-up — do NOT expand F2a to cover it. The gate flags the gap loudly.

## Dependencies

- **F1a–F1d** merged to server `develop` (`FateRulesetModule`, `FateActionPayload`, `dispatch_fate_action`, the 12 live Fate spans). Verified: no open PRs, no in-review stories, origin/develop HEAD `1e883844`.
- No shared mutable state with sibling slices F2b/F2c/F2d — F2a is purely additive and settles the shared contracts they build on.

## Implementation Plan

`docs/superpowers/plans/2026-06-14-f2a-fate-action-classifier.md` — 6 TDD tasks, each red-first with concrete test code, exact signatures, and a full self-review (zero placeholders). Epic context: `docs/superpowers/plans/2026-06-14-f2-narrator-intent-router-integration.md`.

**Implementer watch-points:**
1. Task 3 Step 5 — confirm the exact `_SYSTEM_PROMPT` assembly shape in `intent_router.py` (~line 103–263) before splicing `FATE_ROUTING_RULES`; constant text fully specified, only the splice site needs a look.
2. Scope in-conflict only — out-of-conflict overcome is §7.1 follow-up, not F2a.

**Test gotchas:** DB `postgresql://slabgorb@localhost:5432/sidequest_test` (both env vars); run new tests `uv run pytest -n0`; registry checks use runtime `get_registered()`.

## Refs

- ADR-144 — Fate Core binding replaces the native ruleset
- Design: `docs/superpowers/specs/2026-06-14-fate-core-binding-replaces-native-design.md` §4.5, §6
- Plan: `docs/superpowers/plans/2026-06-14-f2a-fate-action-classifier.md`
- Epic map: `docs/superpowers/plans/2026-06-14-f2-narrator-intent-router-integration.md`
