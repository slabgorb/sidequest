---
parent: context-epic-72.md
workflow: trivial
---

# Story 72-10: observation_pending gate-ordering assert

## Business Context

The `observation_pending` ratification gate is the engine's defense against phantom
NPCs — people the narrator role-named or honorific-named in prose but the playgroup
never actually encountered (the 2026-05-11 Glenross turn-6 invented-Mother slip). Each
narration-apply turn, `_apply_npc_observation_gate` resolves *prior-turn* pending pool
members against *this* turn's `npcs_present`, then `_auto_mint_prose_only_npcs` scans
this turn's prose for *new* role/honorific mentions and mints them
`observation_pending=True` for the *next* turn's gate.

That ordering — **gate before mint** — is load-bearing. If a future refactor reorders
them, the gate would evaluate this turn's own freshly-minted entries against this turn's
(omitting) mentions and immediately self-purge them: the ratification gate silently
becomes a no-op and the phantom-NPC failure mode returns. Today the ordering is enforced
only by a comment (`narration_apply.py:2494–2502`) plus one behavioral order test. This
1-point chore adds a hard invariant so a reordering regression fails loudly at the call
site — and emits an OTEL span the GM panel (Keith's dev lie-detector, per epic 72's
"OTEL on every leg") can see — instead of degrading into convincing-but-baseless NPC
identity drift.

## Technical Guardrails

Real seams (verified):

- **Gate function:** `_apply_npc_observation_gate` — `sidequest/server/session_helpers.py:1912`.
  Iterates `snapshot.npc_pool`, promotes (`observation_pending=False`) or purges members
  with `observation_pending=True`, emitting `SPAN_NPC_OBSERVATION_GATE_PROMOTED` /
  `SPAN_NPC_OBSERVATION_GATE_PURGED`.
- **Mint function:** `_auto_mint_prose_only_npcs` — `sidequest/server/session_helpers.py:1728`.
  Appends `NpcPoolMember(drawn_from="dialogue_extraction", observation_pending=True)`.
- **Ordering call site:** `_apply_narration_result_to_snapshot` —
  `sidequest/server/narration_apply.py`: gate call at **~2503**, mint call at **~2518**,
  with the load-bearing-order comment at **2494–2502**. Both are imported at
  `narration_apply.py:67–68`.
- **Span catalog:** `sidequest/telemetry/spans/npc.py` (gate spans at lines 158–177,
  448–503). A violation span belongs here, defined and routed like its siblings.
- **Existing behavioral order test:** `tests/server/test_npc_observation_gate.py:941`
  (`test_apply_narration_result_runs_gate_before_auto_mint`) already proves correct order
  via observable outcomes (prior-turn Father purged, this-turn Mother stays pending). The
  new invariant is the *enforcement* layer that hard-fails on the wrong order rather than
  inferring it from downstream state.

Server rule — **NO source-text wiring test.** Per `sidequest-server/CLAUDE.md`
("No Source-Text Wiring Tests"), do NOT assert that `_apply_npc_observation_gate(`
appears before `_auto_mint_prose_only_npcs(` in `narration_apply.py` source, and do NOT
grep `narration_apply.read_text()`. The assert must be **behavioral/ordering**: drive the
real `_apply_narration_result_to_snapshot` flow and either (a) assert a runtime invariant
fires on reordering, or (b) assert an OTEL span records the violation. This mirrors the
71-9 migration, which converted a source-text wiring test into a behavioral/OTEL
assertion. Reflection-based runtime checks are also acceptable; source-string greps are not.

Implementation should be minimal: a runtime guard at (or just before) the mint call that
fails loud if any prior-turn `observation_pending` member that should already have been
gated is still unresolved when the minter runs, plus a single violation span on that
path. Reuse the existing `npc.py` span helpers and routing pattern — do not invent a new
telemetry mechanism.

## Scope Boundaries

In scope:
- One runtime invariant/assert guaranteeing the gate precedes the mint, wired into the
  real `_apply_narration_result_to_snapshot` path.
- One OTEL/log violation record (new span in `sidequest/telemetry/spans/npc.py`, defined +
  routed like the sibling gate spans) emitted when ordering is broken.
- Behavioral tests covering the pass and the violation case.

Out of scope (other epic-72 stories — do not touch):
- Gate/mint *logic* changes, new match strategies, or pool-cap/prune (72-6).
- Development pipeline, disposition drift, reconcile-on-load (72-1, 72-2).
- Namegen routing, born-hostile default, identity-drift overwrite (72-4, 72-5, 72-7).
- Any change to `_apply_npc_observation_gate` or `_auto_mint_prose_only_npcs` behavior
  beyond adding the ordering guard.

## AC Context

No explicit ACs existed; derived (regression-guard, behavioral only):

1. **Wrong order fails loud.** When the mint is reached without the gate having run first
   on this turn's apply (simulated reorder / direct invocation), the runtime
   invariant/assert raises (or the violation span fires) — driven through real production
   code, not a source-text grep.
2. **Correct order passes cleanly.** The normal gate→mint sequence through
   `_apply_narration_result_to_snapshot` completes with no violation: prior-turn pending
   members are resolved by the gate and this-turn auto-mints remain
   `observation_pending=True` (consistent with the existing
   `test_apply_narration_result_runs_gate_before_auto_mint` outcome), and no violation
   span is emitted.
3. **Violation is observable in OTEL.** A broken-ordering condition emits a dedicated
   `npc.*` span (severity=warning, mirroring `npc.observation_gate_purged`) so the GM
   panel surfaces the regression; the test asserts the span fired via the `otel_capture`
   fixture.

## Assumptions

- The guard lives at the `narration_apply.py:~2503/~2518` ordering site and/or at the head
  of `_auto_mint_prose_only_npcs`; either placement is acceptable as long as the assertion
  is behavioral and reachable from the real apply path.
- The violation span is a new constant + `SpanRoute` + helper added to
  `sidequest/telemetry/spans/npc.py` following the existing gate-span pattern (no new
  telemetry subsystem).
- Tests extend `tests/server/test_npc_observation_gate.py` and use the existing
  `otel_capture` fixture and `_pending_member` / `_mention` helpers already in that file.
- "Assert" may be a Python `assert`, an explicit raise of a named error, or an
  OTEL-span-backed runtime check — whichever fails loud per "No Silent Fallbacks." A bare
  `assert` is acceptable for a fail-loud dev invariant since these run server-side, not
  under `-O`.
