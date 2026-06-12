# Story 105-1 Context

## Title
Restore the span-proof instrument — teach scripts/playtest.py to answer the Epic-66 pick_portrait frame (portrait_confirm skip) so scenarios/beneath_sunden_engagement.yaml (59-15) runs past chargen and captures movement/confrontation/magic spans instead of silently dying with WrongPhaseError; coordinate with 90-9 which also edits playtest.py chargen

## Metadata
- **Story ID:** 105-1
- **Type:** bug
- **Points:** 2
- **Priority:** p1
- **Workflow:** tdd
- **Repo:** orchestrator
- **Epic:** Beneath Sünden — make the procedural Deep reachable in live play (ADR-106 surface→deep crossing)

## Problem

The headless playtest driver `scripts/playtest.py` cannot answer the Epic-66 portrait-picker
frame, so `scenarios/beneath_sunden_engagement.yaml` (Story 59-15 — the purpose-built
span-proof scenario for the dungeon-crawl engagement spine) **silently dies in chargen
before testing a single engine subsystem**, and reports a false pass-by-early-death.

Measured on the 2026-06-12 dive (headless run): chargen proceeds through stat-arrange →
class → story → kit, reaches the `pick_portrait` frame ("Choose a portrait for your
character — or skip to continue."), and the driver — which only knows
`stat_arrange / story / text / select` — falls through to its generic
"no actionable fields → try a continue to nudge" branch and emits a bare `continue`. The
server routes that to `_chargen_continue → builder.apply_auto_advance()`, but the builder is
already in the `Confirmation` phase, raising:

```
WrongPhaseError(expected="InProgress", actual="Confirmation")
[ERROR] Cannot continue from current scene
Idle timeout while waiting for ERROR — giving up
scenario failed (rc=1); skipping span capture
```

This is a **driver-only** gap, NOT a player bug: the real UI handles the same frame
correctly (`sidequest-ui/src/components/CharacterCreation/CharacterCreation.tsx:163-170` —
`onSkip` sends `{ phase: "portrait_confirm", selected_portrait_ref: null }`, routing to the
server's `_chargen_portrait_confirm`). The driver just never learned the `pick_portrait`
message type.

## Technical Approach

- `scripts/playtest.py` (orchestrator repo): in the chargen phase dispatcher
  (~`playtest.py:407-459`, the `input_type` switch), add a `pick_portrait` case that emits
  the skip message the UI sends: `{ phase: "portrait_confirm", selected_portrait_ref: None }`
  (see `make_chargen_*` helpers / the existing `make_chargen_continue` for the message
  shape). Mirror the UI contract in `payloads.ts:191-192` (`selected_portrait_ref`).
- Do not change the bare-`continue` fallback for genuinely actionable-field-less scenes;
  only intercept `input_type == "pick_portrait"` ahead of it.
- **Coordinate with backlog 90-9**, which also edits `scripts/playtest.py` chargen (AC1:
  honor `scenario class:`). Prefer folding both chargen-driver gaps in one pass if 90-9 is
  picked up concurrently; at minimum avoid clobbering its branch.

## Scope

- **In scope:** `scripts/playtest.py` chargen-driver `pick_portrait` handling; a test that
  the driver, given a `pick_portrait` frame, emits a `portrait_confirm` skip; verification
  that `beneath_sunden_engagement.yaml` now runs past chargen into the action loop.
- **Out of scope:** any server-side chargen change (the server is correct); the
  surface→deep crossing itself (that is 105-2); 90-9's `scenario class:` honoring.

## Acceptance Criteria

1. Given a chargen frame with `input_type == "pick_portrait"`, `scripts/playtest.py` emits
   a `{ phase: "portrait_confirm", selected_portrait_ref: null }` message (skip) and chargen
   advances — no `WrongPhaseError`. Covered by a failing-then-passing test.
2. `scenarios/beneath_sunden_engagement.yaml` runs end-to-end past chargen into the scripted
   action loop (no chargen-phase abort), reaching the descent/confrontation/magic actions.
3. The run captures spans (e.g. via `--span-jsonl`): `intent_router.subsystem(...)` and the
   downstream subsystem spans are present for the action turns — i.e. the harness actually
   exercises the engine instead of dying early.
4. No regression to the existing `select / stat_arrange / story / text` driver paths.
