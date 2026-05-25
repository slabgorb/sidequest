---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-7: Wire three LocalDM subsystems (npc_agency, distinctive_detail_hint, reflect_absence)

## Business Context

Three subsystem modules already exist in `sidequest/agents/subsystems/` from the 2026-04 LocalDM build:
- `npc_agency.py` — enables contextual NPC action and agency based on game state
- `distinctive_detail_hint.py` — generates distinctive environmental details that guide roleplay and discovery
- `reflect_absence.py` — acknowledges and narrates the absence of expected game elements

These subsystems had no live dispatch path when LocalDM was shelved on 2026-04-28 due to `claude -p` subprocess latency. Now that the IntentRouter is live (59-4) and Haiku via SDK is the pre-narrator routing pass, these three subsystems can finally wake up and engage through the Intent Router dispatch pipeline.

59-7 is a pure additive story: wire each subsystem through `run_dispatch_bank` with fixture tests mirroring the confrontation/magic shape. No engine retirement, no field removal — just making three existing engines live for the first time since dormancy.

## Technical Guardrails

**Key files to modify or extend:**
- `sidequest/agents/subsystems/npc_agency.py` — Wrapped in a dispatch handler function (same shape as subsystems/confrontation.py, subsystems/magic_working.py)
- `sidequest/agents/subsystems/distinctive_detail_hint.py` — Wrapped in a dispatch handler function
- `sidequest/agents/subsystems/reflect_absence.py` — Wrapped in a dispatch handler function
- `sidequest/agents/subsystems/__init__.py` — Register handlers in `run_dispatch_bank` consumer pattern (add to subsystem dispatch registry)
- `sidequest/agents/intent_router.py` — Add `npc_agency`, `distinctive_detail_hint`, `reflect_absence` to dispatch vocabulary (if not already present)

**Patterns to follow:**
- Handler wrapper shape: mirror `subsystems/confrontation.py` and `subsystems/magic_working.py` — receives dispatch object, calls existing subsystem logic, emits OTEL spans
- Dispatch vocabulary: per ADR-113 §Decision §Dispatch vocabulary, all three are named dispatch types
- OTEL: `intent_router.dispatch.{subsystem}` span on engagement (mirrors confrontation/magic pattern)
- No fallbacks (memory `feedback_no_fallbacks_hard`): handler failure = ERROR span + loud surface, never silent continuation
- Visibility filtering: redact_dispatch_package already honors visibility tags on these dispatch types (no new work needed)

**Dependencies:**
- 59-4 (confrontation cutover) must be merged — the live IntentRouter pipeline and `run_dispatch_bank` call site are prerequisites
- Subsystem modules already exist and can be called directly from handlers
- 59-3's lie-detector already covers all three subsystems (AC4 mentions "extends 59-3 watcher vocabulary")

**What NOT to touch:**
- `run_dispatch_bank` executor core — it already handles topo-sort, per-dispatch OTEL, error handling; just register the new handlers
- The subsystem modules themselves — they're existing, stable code; handlers only wrap them with dispatch logic
- Other narrator sidecar fields — only dispatch routing is the new path; narrator emission stays as-is for non-engagement fields

## Scope Boundaries

**In scope:**
- Handler wrappers for npc_agency, distinctive_detail_hint, reflect_absence
- Registration of handlers in `run_dispatch_bank` subsystem registry
- `npc_agency`, `distinctive_detail_hint`, `reflect_absence` added to IntentRouter dispatch vocabulary (if not already present)
- Fixture tests for each subsystem (handler invokes engine, OTEL span emitted, integration through pipeline)
- Verify redact_dispatch_package filters visibility-tagged dispatches before narrator sees them
- Lie-detector coverage test (extends 59-3 vocabulary)

**Out of scope:**
- Changes to the subsystem module logic itself — if a subsystem has bugs, that's a separate story
- Changes to `run_dispatch_bank` executor core
- Narrator prompt updates for these subsystems (they're not narrator-owned; router-driven only)
- Scenario_clue (59-6) or other dispatch types
- Playtest validation (59-8)

## AC Context

**AC1 — npc_agency dispatch engages handler:**
Router dispatches `npc_agency` with parameters (e.g., NPC state, contextual trigger). Handler is invoked. Existing `npc_agency.py` logic runs on the snapshot. Verify via OTEL span: `intent_router.dispatch.npc_agency` emitted and handler completes before narrator runs.

**AC2 — distinctive_detail_hint dispatch engages handler:**
Router dispatches `distinctive_detail_hint` with scene parameters. Handler invokes subsystem. Verify via OTEL: `intent_router.dispatch.distinctive_detail_hint` span and handler execution before narration.

**AC3 — reflect_absence dispatch engages handler:**
Router dispatches `reflect_absence` with absence parameters. Handler invokes subsystem. Verify via OTEL: `intent_router.dispatch.reflect_absence` span and handler execution before narration.

**AC4 — redact_dispatch_package honored:**
When dispatches carry visibility tags (e.g., "gm_only", "player_group_A"), redact_dispatch_package filters them before narrator_instructions are assembled. Verify that visibility-tagged dispatches do not leak into the narrator's perception of the game state. This is a verification of existing redaction covering these new subsystems, not new redaction logic.

**AC5 — Lie-detector watches all three subsystems:**
The watcher (59-3) already has vocabulary for `dispatch_engagement.{subsystem}.mismatch` spans. Verify that if router dispatches any of the three but the engine doesn't engage on the snapshot, a mismatch span fires. This is a verification of existing coverage, not new watcher logic.

## Assumptions

- 59-4 (confrontation cutover) is merged and IntentRouter is live on the turn pipeline
- `run_dispatch_bank` already has a plugin/registry pattern for subsystem handlers; just add the new ones
- Subsystem modules (npc_agency.py, distinctive_detail_hint.py, reflect_absence.py) are stable and callable as-is
- The IntentRouter's Haiku prompt can classify npc_agency, distinctive_detail_hint, and reflect_absence intents with sufficient confidence
- Visibility tag filtering in redact_dispatch_package already applies to these dispatch types
- These three subsystems are intended to be suppressed from narrator view when tagged (narrator doesn't generate these — router does)

## Key Differences from Confrontation / Magic Stories

- **Scope:** No retirement of narrator sidecar fields (unlike 59-4/59-5). These subsystems have no sidecar path — they're pure router-driven.
- **Engine state impact:** npc_agency may mutate NPC state; distinctive_detail_hint may generate ephemeral details; reflect_absence may synthesize narrative gaps. All are designed to run pre-narrator.
- **Narrator visibility:** All three should be visibility-filtered from narrator_instructions if tagged "gm_only" or similar. This is a verification of existing redaction, not new filtering.
