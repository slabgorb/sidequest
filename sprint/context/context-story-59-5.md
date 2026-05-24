---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-5: Magic_working dispatch handler + sidecar engagement retirement

## Business Context

Magic engagement currently relies on the narrator self-reporting a `result.magic_working` sidecar field in its JSON output — the same unreliable pattern that confrontation engagement suffered before 59-4's IntentRouter cutover. When the narrator omits or misreports the field, `apply_magic_working` never fires and the engine is bypassed entirely, with the narrator improvising magical outcomes that have no mechanical backing. This is the SOUL "Illusionism" failure mode applied to magic: convincing prose, zero crunch.

59-5 extends the IntentRouter spine (shipped in 59-2/59-4) to cover `magic_working`, following the same handler-dispatch pattern as the confrontation cutover. The router pre-classifies spellcasting intent via Haiku and engages `apply_magic_working` BEFORE the narrator runs, making magic mechanically real rather than narrator-optional.

## Technical Guardrails

**Key files to modify or extend:**
- `sidequest/agents/subsystems/magic_working.py` — NEW handler file, same shape as `subsystems/confrontation.py` (shipped in 59-4)
- `sidequest/agents/intent_router.py` — Add `magic_working` to dispatch vocabulary
- `sidequest/game/narration_apply.py:638` — RETIRE `result.magic_working` sidecar consumer path (currently calls `apply_magic_working` from narrator-emitted field)
- Narrator prompt (output_only_sdk.md or equivalent) — Remove magic engagement routing from narrator responsibility

**Patterns to follow:**
- Handler shape: mirror `subsystems/confrontation.py` — receives dispatch, calls existing engine entrypoint, emits OTEL spans
- Dispatch vocabulary: per ADR-113 §Decision §Dispatch vocabulary, `magic_working` is a named dispatch type
- OTEL: `intent_router.dispatch.magic_working` span on engagement (mirrors `intent_router.dispatch.confrontation`)
- No fallbacks (memory `feedback_no_fallbacks_hard`): handler failure = ERROR span + loud surface, never silent continuation

**Dependencies:**
- 59-4 (confrontation cutover) must be merged — the live IntentRouter pipeline and `run_dispatch_bank` call site are prerequisites
- `apply_magic_working` at `narration_apply.py:638` is the existing engine entrypoint — reuse it, don't rewrite it
- 59-3's lie-detector already covers `magic_working` dispatch mismatches (AC4 of 59-3)

**What NOT to touch:**
- `run_dispatch_bank` executor — already handles topo-sort and per-dispatch OTEL; just register the new handler
- `redact_dispatch_package` — visibility filtering already works for new dispatch types
- Other sidecar fields in `narration_apply.py` — only `result.magic_working` retires; sibling fields remain narrator-emitted

## Scope Boundaries

**In scope:**
- `subsystems/magic_working.py` handler routing dispatch to `apply_magic_working`
- `magic_working` added to IntentRouter dispatch vocabulary
- `result.magic_working` sidecar engagement path retired in `narration_apply.py`
- Narrator prompt updated: magic engagement is no longer narrator's signal
- Fixture tests (handler, retirement guard, pipeline wiring)
- ADR-013 drift note updated to reference ADR-113 for magic engagement

**Out of scope:**
- Scenario_clue dispatch (59-6)
- npc_agency / distinctive_detail / reflect_absence wiring (59-7)
- Playtest validation (59-8)
- Any changes to the IntentRouter core or `run_dispatch_bank` executor
- Magic system mechanics changes — this is a routing change, not a game design change

## AC Context

**AC1 — Fixture: spellcasting action dispatches magic_working before narrator:**
Router receives a spellcasting-shaped player action (e.g., "I cast a ward of protection"). IntentRouter.decompose classifies it as `magic_working` dispatch. Handler invokes `apply_magic_working` on the snapshot. Narrator runs AFTER, seeing the already-applied magical state. Verify via OTEL span ordering: `intent_router.decompose` → `intent_router.dispatch.magic_working` → `magic.applied` (or equivalent engine span), all before `narrator.turn`.

**AC2 — Retirement guard for result.magic_working sidecar path:**
Assert that `narration_apply.py` no longer calls `apply_magic_working` from `result.magic_working`. Two verification approaches (choose one or both): (a) search-based test on the function body confirming no `result.magic_working` consumer, (b) behavioral test: manually set `result.magic_working` on a turn result, assert no magic engagement fires from the sidecar path.

**AC3 — Lie-detector covers magic mismatches:**
Already shipped in 59-3 AC4. Verify the watcher emits `dispatch_engagement.magic_working.mismatch` when router dispatches magic but engine doesn't engage. This is a verification of existing coverage, not new implementation.

**AC4 — Wiring test through pipeline:**
Drive a full turn through the orchestrator pipeline (action → router → dispatch_bank → handler → narrator) with a magic-shaped input. Assert `apply_magic_working` was called and the snapshot reflects the magical outcome before narration. This tests the integration, not just the handler in isolation.

**AC5 — ADR-013 drift note update:**
ADR-013's drift note (updated in 59-2 for confrontation) gains a reference to magic_working engagement also being superseded by ADR-113 on the SDK path.

## Assumptions

- 59-4 (confrontation cutover) is merged to develop and the IntentRouter is live on the turn pipeline
- `apply_magic_working` at `narration_apply.py:638` is a stable entrypoint that can be called from the handler without modification
- The IntentRouter's Haiku prompt can classify spellcasting intent with sufficient confidence (threshold 0.6 per epic §Open Questions resolution)
- `run_dispatch_bank` already handles registration of new subsystem handlers via its existing plugin pattern
