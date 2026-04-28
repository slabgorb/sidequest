---
story_id: "45-9"
epic: "45"
workflow: "trivial"
---
# Story 45-9: total_beats_fired counter increments on every beat fire + OTEL

## Story Details
- **ID:** 45-9
- **Epic:** 45 — Playtest 3 Closeout
- **Workflow:** trivial
- **Type:** bug
- **Priority:** p1
- **Points:** 1
- **Repos:** server

## Description

Playtest 3: total_beats_fired frozen at 0 across 3 saves despite real beat fires (Orin had 5 fired beats including a Resolved extraction_panic trope). Counter is defined at session.py:400 but never incremented anywhere — confirmed via codebase audit 2026-04-27 (zero += matches). Increment in _apply_encounter_beats() on every beat fire; emit OTEL span with current counter value. Any beat-gated unlock perpetually blocks today.

**Source:** 37-38 sub-1

## Acceptance Criteria
- [ ] total_beats_fired increments on every beat fire in _apply_encounter_beats()
- [ ] OTEL span emitted with counter value on each increment
- [ ] Confirm zero += matches in codebase after fix (grep clean)
- [ ] No beat-gated unlock silently blocks

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-04-27T20:50:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T20:50:00Z | - | - |

## Delivery Findings

### Dev (implementation)
- **Gap** (non-blocking): There are actually THREE production beat-fire paths, not one. The story description called out `_apply_encounter_beats()` but the codebase has no such function — the actual fire path is `apply_beat()` in `sidequest/game/beat_kinds.py:236`, called from THREE call sites: (1) `narration_apply.py:613` legacy narrator beat path, (2) `narration_apply.py:959` opposed_check resolver, (3) `dispatch/dice.py:361` DICE_THROW path. All three now bump the counter. *Found by Dev during implementation.*
- **Improvement** (non-blocking): Repo's `ruff check` baseline has ~173 pre-existing lint errors (mostly UP037, I001 in session_handler.py and tooling). My touched files added zero new lint errors. `just server-check` lint stage fails on this baseline regardless of this story. Worth a separate cleanup pass. *Found by Dev during implementation.*

## Design Deviations

### Dev (implementation)
- **Helper placement:** Spec said "increment the counter inside `_apply_encounter_beats()`" — implemented as a `GameSnapshot.record_beat_fired()` helper method invoked from each of the three actual fire sites. Reason: the story description's path name doesn't exist; centralizing the bump+OTEL in one method keeps the three sites consistent and the OTEL emission identical (no drift between paths).
- **Test wire test path:** The story-level wire test exercises `_apply_narration_result_to_snapshot` (the most common production path used by Playtest 3's Orin trope fires); a second wire test exercises `dispatch_dice_throw` (the explicit-PC-consent path). The opposed-check path shares the helper and is covered transitively by `record_beat_fired`'s unit tests + the existing opposed-check wiring tests.

---

## Reviewer Assessment

**Verdict:** APPROVED
**Reviewer:** Westley
**Timestamp:** 2026-04-27
**PR:** https://github.com/slabgorb/sidequest-server/pull/91

**Data flow traced:** narrator-emitted `BeatSelection` → `_apply_narration_result_to_snapshot` → `apply_beat` (success) → `snapshot.record_beat_fired(...)` → `total_beats_fired += 1` → watcher event `state_transition/beat_fired` published. Counter is then read by `world_materialization.derive_maturity` (effective = round + beats // 2) which gates the campaign maturity ladder. End-to-end now connected; pre-fix the chain broke at the increment, leaving maturity frozen at Fresh forever.

**Wiring audit:** Grep `apply_beat(` in production returns exactly 3 sites (narration_apply.py:614, narration_apply.py:972, dispatch/dice.py:363). All 3 are followed by an unconditional `record_beat_fired` call after the `skipped_reason` early-`continue`. No production fire path missed. Tests in `test_total_beats_fired_counter.py` cover the legacy narrator path and the DICE_THROW path with real handlers, real snapshot, real `apply_beat`. Opposed-check path bumps inside the per-side for-loop (correct: 2 bumps per opposed exchange, one per side).

**Counter correctness:** Bump is gated on `apply_result.skipped_reason is None` at every site. Opposed-check `else` branch in dispatch/dice.py correctly defers (player tier unknown until narrator resolves) and the bump happens in narration_apply for both sides — no double-count, no count on a no-op.

**OTEL event shape:** `state_transition` + `op: "beat_fired"` matches the established pattern of sibling ops (`beat_applied`, `beat_skipped`, `resolved`). Payload carries `beat_id`, `encounter_type`, `turn`, `source` (`narrator_beat` / `opposed_check` / `dice_throw`), and the new `total_beats_fired` value — enough for the GM panel to verify each bump and attribute it to a fire path.

**Fail-loud:** `snapshot: GameSnapshot` is a required keyword (no default) on `dispatch_dice_throw` and `_resolve_opposed_check_branch`. Missing snapshot raises `TypeError` at the call site. Conforms to CLAUDE.md no-silent-fallbacks.

**Tests:** `tests/game/test_total_beats_fired_counter.py` (6) + `tests/server/test_dice_dispatch.py` (14) + `tests/server/test_opposed_check_wiring.py` (7 + 6 skipped pre-existing pack gates) — 27 passed, 6 skipped, 0 failed. Full suite per Dev: 2670/0/34.

**Severity table:**
| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [LOW] | `record_beat_fired` returns `int` but no caller uses it; could be `-> None`. | `session.py:569` | None — non-blocking |
| [LOW] | Opposed-check path increment not directly wire-tested (covered transitively via unit tests + existing opposed_check_wiring tests passing the new snapshot kwarg). | `tests/game/test_total_beats_fired_counter.py` | None — acceptable for trivial scope |

**Trivial scope:** 1pt budget respected. ~80 lines of helper + ~20 lines of fire-site bumps + 288 lines of tests. No drive-by refactors. Dev correctly identified that the story's named function (`_apply_encounter_beats`) doesn't exist and documented the actual 3-site reality in Delivery Findings — adversarial reading of the spec, well done.

**Observations (>= 5):**
1. Bump unconditional after `skipped_reason` check at all 3 sites — no double-count, no no-op count.
2. `state_transition` + `op` pattern matches sibling encounter events; GM panel will see it natively.
3. `snapshot` kwarg is required (no default), fails loud on missing — CLAUDE.md compliant.
4. Helper centralization (`record_beat_fired`) prevents OTEL emission drift between the 3 fire paths.
5. Tests exercise real production paths with real `apply_beat`, not just the helper in isolation — meets CLAUDE.md "every test suite needs a wiring test" rule.
6. `world_materialization.derive_maturity` is the live consumer; chain is now fully connected.

**Handoff:** To SM for finish-story.

---

**Session file created:** 2026-04-27
**Branch target:** sidequest-server (develop → feat/45-9-total-beats-fired-counter-otel)
