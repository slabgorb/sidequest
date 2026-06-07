---
parent: context-epic-97.md
workflow: tdd
---

# Story 97-4: Scratch sweep fires on same-region drift — clear_scratch_on_scene_end keys on the raw location-string gate #739 fixed for encounters

## Business Context

Same root-cause family as server #739 (region-drift encounter abandonment), deliberately left out of its scope (named in #739's FIXER scope note: "the Scratch sweep … same raw-location-string gate … still fires on same-region drift — file separately"). In region-mode worlds the narrator routinely re-titles the scene within the same region (`narrator.location_drift_repaired` fires every turn there, per the carried-forward observations) — each cosmetic drift wipes scratch state that should survive, because the party never left the scene. #739 proved the pattern and built the harness; this story applies the identical gate to the one remaining consumer of the raw string comparison.

## Technical Guardrails

- **This is a mirror of #739, not a design exercise.** The `_same_region_drift` flag already exists in `_apply_narration_result_to_snapshot` (`sidequest/server/narration_apply.py:3108` init, set at :3275 and :3376 by both region-resolution branches, consumed by the encounter ladder at :3480). The scratch sweep call sits at :3431-3433 (`from sidequest.server.status_clear import clear_scratch_on_scene_end`) — **upstream of the flag's current consumer and gated only on the raw `old_loc != result.location` comparison**. The fix is to consult the same flag at the scratch-sweep gate.
- Check ordering carefully: the sweep call at :3431 executes before the encounter-ladder consumption at :3480 — confirm the flag is fully settled (both set-points :3275/:3376 are earlier) by the time the sweep gate reads it. It is, per the line numbers, but verify against the live code, not this document.
- Sweep implementation lives in `sidequest/server/status_clear.py` — prefer gating at the call site in `narration_apply.py` (where the flag is in scope) over threading region-awareness into `status_clear` itself, unless the call site is shared.
- Harness: `tests/server/test_region_drift_encounter_continue.py` — #739's fixture-driven behavior tests are the template. Reuse the fixtures; add the scratch-state assertions.
- A genuine region change must still sweep — #739 preserved the won/yield/mobile/abandon ladder and negotiation-walk-out (2026-04-30) semantics for real region changes; the scratch sweep keeps the same symmetry.
- Room-graph (non-region-mode) worlds are unaffected — the flag is region-mode gated; the sweep behaves as today there.

## Scope Boundaries

**In scope:**
- Scratch sweep skipped on same-region drift in region-mode worlds; still fires on a genuine region change
- OTEL/log evidence on the keep-vs-sweep decision (both branches — per house rule and #739's precedent `encounter.continued_same_region_drift` INFO + watcher event)

**Out of scope:**
- Any other consumer of the raw location-string gate (if implementation finds a third, file it — don't expand scope silently)
- The narrator-drifts-location-every-turn behavior itself (`narrator.location_drift_repaired` — carried-forward observation, prompt-side)
- Encounter-ladder behavior (#739, merged and verified territory)

## AC Context

1. **"Same-region drift does not clear scratch; a genuine region change still does"** — Test: region-mode fixture (reuse #739's), populate scratch state, narrate a same-region scene-title drift → scratch intact; narrate a real region change → scratch swept. Edge: drift and region change in consecutive turns (flag must reset per-turn — it's function-local, but the test should prove it); non-region-mode world → sweep behavior unchanged on any location change.
2. **"OTEL/log evidence on the keep-vs-sweep decision"** — Test: span/log assertions on both branches — a `scratch.kept_same_region_drift`-shaped emit (naming per existing `encounter.continued_same_region_drift` convention) when skipped, and the existing sweep path's evidence when fired. The GM panel must be able to distinguish "kept deliberately" from "sweep didn't run."

## Assumptions

- 2-point sizing assumes the mirror holds: flag exists, harness exists, one gate to add. If the sweep call site turns out to be shared with non-narration paths, log the deviation and rescope.
- Scratch state semantics ("survives within a scene, dies at scene end") are as the entry describes — `status_clear.py` docstrings should confirm; if scratch has consumers expecting per-location (not per-scene) lifetime, surface that before changing the gate.
