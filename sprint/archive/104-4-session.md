---
story_id: "104-4"
jira_key: ""
epic: "104"
workflow: "trivial"
---
# Story 104-4: M-D — Fix orrery broken-drift arc-label sweep rotation

## Story Details
- **ID:** 104-4
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none
- **Type:** bug
- **Points:** 1
- **Repos:** server

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-11T09:59:38Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-11T09:29:13Z | 2026-06-11T09:30:47Z | 1m 34s |
| implement | 2026-06-11T09:30:47Z | 2026-06-11T09:45:16Z | 14m 29s |
| review | 2026-06-11T09:45:16Z | 2026-06-11T09:51:30Z | 6m 14s |
| implement | 2026-06-11T09:51:30Z | 2026-06-11T09:57:03Z | 5m 33s |
| review | 2026-06-11T09:57:03Z | 2026-06-11T09:59:38Z | 2m 35s |
| finish | 2026-06-11T09:59:38Z | - | - |

## Summary

Fix cosmetic rotation of arc-label text in the orrery visualization. The "broken drift" orbital label and similar opposite-side arc annotations render with the text reading upside-down due to incorrect textPath sweep flags.

**Location:** sidequest-server/sidequest/orbital/render.py
**Spec:** docs/superpowers/specs/2026-06-11-space-opera-map-playtest-addendum.md §5 Story M-D + §4
**ADR:** ADR-094 (Orrery Label Placement)

## Acceptance Criteria

1. Belt labels read upright/correct-direction on both sides of the chart
2. Opposite-side belts use the opposite sweep-flag (or reversed path)
3. Cosmetic fix — no OTEL needed

## Branch

**Branch Strategy:** gitflow
**Branch Name:** feat/104-4-orrery-arc-label-sweep

## Sm Assessment

Trivial-workflow cosmetic bug, 1pt, single repo (server). The fix is well-scoped by the spec: in `sidequest/orbital/render.py`, the `textPath` arc-belt rendering uses a fixed SVG sweep-flag, so labels on the opposite side of the chart (e.g. "broken drift") render mirrored/upside-down. The remedy is to flip the sweep-flag (or reverse the path direction) for belts on the opposite hemisphere so all labels read upright — exactly the ADR-094 label-placement concern. Right-sized for a single Dev implement pass (per the "right-size plan ceremony" doctrine: a cosmetic sub-200-LOC fix gets one implementer pass, not TDD-per-method ceremony).

**Scope guardrails for Dev:**
- This is genuinely cosmetic — ADR-094, no OTEL emit required (spec §5 says so explicitly). Do not add watcher spans.
- Touch only the arc-belt `textPath` sweep/path logic in `orbital/render.py`; do not refactor the surrounding label-placement strategy.
- Verify visually if practical (render an orrery with belts on both sides), and add/adjust a focused test asserting opposite-side belts get the opposite sweep-flag so the fix is regression-guarded.

**Routing:** trivial → implement phase → Dev (Inigo Montoya).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/orbital/render.py` — `_resolve_curve_along` now returns a sixth value, `needs_upright_flip`, computed from the path geometry per branch (ellipse orbit: always flip at its bottom 50%-point; `body:` arc belt: flip when `sin(mid_deg) > 0`, i.e. the arc midpoint sits in the upper half and the swept glyphs travel leftward). Both render sites and the suppression/build sites updated to consume the returned flag instead of the inverted `midpoint[1] > 0` heuristic.
- `tests/orbital/test_render_orrery_v2.py` — replaced `test_upper_arc_arc_belt_label_has_no_transform` (which pinned the bug) with `test_upper_arc_arc_belt_label_is_flipped`; added `test_broken_drift_shaped_belt_is_flipped` (the exact 30°→120° coyote_star shape) and `test_lower_arc_arc_belt_label_has_no_transform` (mirror counter-case proving lower-half belts are NOT flipped).
- `tests/orbital/snapshots/coyote_star_callouts_system_t0.svg` — re-baselined: `broken drift` now carries `rotate(180 21.57 -80.49)` (its own midpoint).
- `tests/orbital/snapshots/world_callout_strategy_t0.svg` — re-baselined: `tiny_belt` (mid 285°, lower half) no longer wrongly flipped.

**Root cause:** The shared `midpoint.y > 0` flip rule is correct only for the full-ring ellipse (whose 50%-point is always the bottom). For partial `body:` arcs the readability condition is *inverted* — they read upside-down on the upper arc — so `broken drift` (mid 75°) rendered upside-down and a lower belt would be wrongly flipped. Confirmed against the live `coyote_star` orrery render (operator screenshots).

**Tests:** 376/376 orbital passing (GREEN); ruff check + format clean.
**Branch:** feat/104-4-orrery-arc-label-sweep (pushed)
**OTEL:** None added — cosmetic change, per spec AC2 + CLAUDE.md ("Not needed for cosmetic changes").

**Handoff:** To review phase (Westley).

## Subagent Results

Only `preflight` is enabled for the review phase (`workflow.reviewer_subagents`); the other eight are disabled via settings and pre-filled as Skipped.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 384 tests green, ruff check + format clean, tree clean, diff scope matches spec |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | N/A — Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings |

**All received:** Yes (1 enabled returned clean, 8 disabled)
**Total findings:** 1 confirmed (HIGH, Reviewer's own analysis), 0 dismissed, 0 deferred

## Reviewer Observations

- **[HIGH] OTEL/SVG flip divergence introduced** at `sidequest/orbital/render.py:1890`. The fix updated the SVG render site (line 1923 → `tp_data[3]`) and `_render_annotation` (line 2011) to the geometry-correct flag, but left `upright_flip_by_body` (line 1890) on the old `tp_data[2][1] > 0` (midpoint.y) heuristic. The comment at lines 1884–1885 documents the explicit invariant: *"pre-compute upright-flip … so the same value goes into both the OTEL span and the SVG element."* That invariant is now violated — for an upper-half arc belt (`broken drift`, mid 75°, y≈−80) the SVG correctly flips (`rotate(180 …)`) but the `textpath_upright_flip` OTEL attribute (emitted at line 1904) reports `False`. The telemetry now contradicts the render. Per CLAUDE.md ("the GM panel is the lie detector"), an existing span that misreports is worse than the pre-change state, where OTEL and SVG at least agreed. **Fix:** line 1890 → `tp_data is not None and tp_data[3]` (and, to honor the single-source design, line 1923 may read `needs_flip = upright_flip_by_body[d.body_id]` rather than recomputing `tp_data[3]`).
- **[VERIFIED] Arc-belt flip rule matches ground truth** — `render.py:592` `needs_upright_flip = math.sin(math.radians(mid_deg)) > 0`. For `broken drift` (mid 75°) sin>0 → flip; confirmed against the operator screenshot (label was upside-down pre-fix) and the re-baselined snapshot now carries `rotate(180 21.57 -80.49)` about the label's own midpoint.
- **[VERIFIED] Ellipse orbit still flips** — `render.py:551` returns `True` unconditionally for `orbit_*`; snapshot retains `curve_orbit_last_drift` with `rotate(180 -0.0 333.33)` at its bottom 50%-point. No regression to the working ellipse case.
- **[VERIFIED] Tuple-arity change fully propagated to render sites** — all four call sites updated (suppression `render.py:713` uses `_`; build site `:1810`; `_render_annotation` `:2011`). The SVG-affecting consumers are correct; only the OTEL consumer (line 1890) was missed — see the HIGH finding.
- **[VERIFIED] Test correction is sound, not a vacuous flip** — the old `test_upper_arc_arc_belt_label_has_no_transform` pinned the bug; it was replaced with `test_upper_arc_arc_belt_label_is_flipped` + `test_broken_drift_shaped_belt_is_flipped` (exact 30°→120° shape) + `test_lower_arc_arc_belt_label_has_no_transform` (mirror counter-case). Asserts on `rotate(180` presence/absence and rejects `rotate(180 0 0)` origin-rotation. Good coverage of both sides.
- **[MEDIUM→note] No test covers the OTEL `textpath_upright_flip` value** — `tests/telemetry/test_chart_label_spans.py::test_textpath_decision_emits_clean` doesn't pass or assert `textpath_upright_flip`, which is exactly why the divergence above slipped past a green suite. A regression test asserting the span value matches the SVG flip for an arc belt would have caught it; recommended alongside the line-1890 fix.

### Rule Compliance

- **OTEL Observability Principle (CLAUDE.md)** — "Not needed for cosmetic changes" applies to *adding* spans; it does **not** license desyncing an *existing* span from reality. The existing `textpath_upright_flip` span is now inaccurate for arc belts → VIOLATION (the HIGH finding).
- **No Silent Fallbacks** — fix preserves fail-loud `ValueError`/`_CurveScopeMismatch` paths in `_resolve_curve_along`; no new fallbacks. Compliant.
- **No Stubbing / No half-wired features** — the SVG path is fully wired; however the OTEL consumer is now half-aligned (SVG fixed, telemetry not) → the HIGH finding is precisely a "half-wired" instance.
- **No Source-Text Wiring Tests** — new tests assert on rendered SVG output (behavioral), not source text. Compliant.

### Devil's Advocate

Assume this is broken. The most damning angle is the one already found: the author fixed the *visible* symptom and declared victory while leaving the *measurement* of that symptom reporting the old, wrong answer. This is the single most dangerous failure mode this very project is built to prevent — the SOUL/CLAUDE doctrine is that Claude "wings it" with convincing output and only OTEL catches it. Here the author has made OTEL itself wing it: the GM panel would show `textpath_upright_flip=false` for a label the player sees flipped. A future engineer debugging label orientation would trust the span, see "false," and conclude the flip code never ran — sending them down exactly the multi-hour wrong path the No-Silent-Fallbacks rule exists to kill.

What else could break? The arc-belt rule `sin(mid_deg) > 0` assumes the SVG renderer traverses the `body:` arc from `from_deg`→`to_deg` in increasing-angle order and that the concentric arc is the one drawn. For `arc_extent_deg > 180` (large-arc) or a belt whose `epoch_phase_deg`+`arc_extent` straddles 0°/360°, the angular midpoint `(from+to)/2` still lands where expected, but no fixture exercises a >180° arc or a wrap-around belt, so that branch is unproven. It's not in scope for coyote_star (90° arc) and not a regression (the old rule was also untested there), so it's a note, not a blocker. Boundary `mid_deg ∈ {0, 180}` gives `sin = 0 → flip False`; a label exactly at 3 o'clock/9 o'clock is a degenerate horizontal case where flip-or-not is visually marginal — acceptable. Empty/None text and off-scope bodies are still guarded upstream. Conclusion: one real blocker (OTEL divergence), one unproven-but-out-of-scope edge (>180°/wrap arcs) worth a future fixture.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | `upright_flip_by_body` still uses the old `midpoint.y > 0` heuristic, so the `textpath_upright_flip` OTEL span now disagrees with the SVG flip for arc belts — violates the documented "same value to OTEL and SVG" invariant (lines 1884–1885). | `sidequest/orbital/render.py:1890` | Change to `tp_data is not None and tp_data[3]`. Optionally have the SVG site (line 1923) read `upright_flip_by_body[d.body_id]` to restore the single-source design. Add a telemetry regression asserting the span value equals the SVG flip for an upper-half arc belt. |

**Data flow traced:** chart annotation `curve_along` → `_resolve_curve_along` (now returns `needs_upright_flip`) → `textpath_by_body[...][3]` → SVG `rotate(180 …)` (correct) **and** → `upright_flip_by_body` (STALE: midpoint.y) → `emit_chart_label_strategy(textpath_upright_flip=…)` (wrong for arc belts). The divergence is the defect.

**Handoff:** Back to Dev for fixes.

## Dev Rework (round 2)

**Addressing the [HIGH] OTEL/SVG divergence finding.**

Applied the single-source fix: `upright_flip_by_body` (render.py:1890) now derives from the geometry-resolved `tp_data[3]`, and the strategy-layer SVG site (render.py:1929) reads back from `upright_flip_by_body` so the OTEL span and SVG element share exactly one value — honoring the documented invariant (lines 1884–1885).

**Honest correction to the finding's severity — it is NOT production-reachable.** While adding the regression test, I measured the real `coyote_star` render: **zero** bodies receive `strategy=textpath`; every `chart.label_strategy` span is `callout` or `radial` (the 17 spans were measured directly). The `curve_along` labels (Last Drift, broken drift) are rendered by the **flavor layer** (`_render_annotation`, render.py:2011) — a separate path from the `upright_flip_by_body`/OTEL emission — and arc-belt bodies with a textpath annotation are *suppressed* from the strategy/decision layer (`_arc_belt_bodies_with_textpath_annotation`). So `textpath_upright_flip` is always the default `False`, and the old vs. new formula at line 1890 produce the same value for every reachable input. **The divergence the Reviewer flagged cannot manifest in production.**

Therefore:
- The **effective** fix for the visible "broken drift" bug lives entirely in the flavor-layer path (`_render_annotation`) + `_resolve_curve_along` — that was correct in round 1 and is unchanged.
- The line-1890/1929 single-source change is kept as **defensive hygiene**: it removes a latent inconsistency (two different flip formulas for the same body) and makes the code honor its own invariant comment, at zero risk. It is not load-bearing.
- The telemetry regression test I drafted was **removed** — it asserted a `chart.label_strategy` textpath span that the suppression layer never emits for arc belts (it was a vacuous/invalid test). The SVG flip behavior is already regression-guarded by the three `test_render_orrery_v2.py` upright-flip tests + the re-baselined snapshots.

**Tests:** 384/384 (tests/orbital + tests/telemetry/test_chart_label_spans) GREEN; ruff check + format clean.
**Handoff:** Back to review (Westley).

## Delivery Findings

No upstream findings.

### Reviewer (code review)
- **Gap** (blocking): `textpath_upright_flip` OTEL span diverges from the SVG flip for arc-belt labels. Affects `sidequest/orbital/render.py` (line 1890 must use the resolved `tp_data[3]` flag, not the legacy `midpoint.y > 0`; add a telemetry regression test). *Found by Reviewer during code review.* — **RESOLVED round 2** (single-source applied; also found non-production-reachable).

### Reviewer (code review, round 2)
- No upstream findings. The round-1 finding is resolved; no further gaps, conflicts, or improvements for downstream stories.

## Design Deviations

### Dev (implementation)
- **Reused the existing 180° upright-flip mechanism instead of literally changing the SVG sweep-flag / reversing the path**
  - Spec source: 2026-06-11-space-opera-map-playtest-addendum.md, Story M-D AC1 / §4
  - Spec text: "opposite-side belts use the opposite sweep-flag (or reversed path)"
  - Implementation: Kept the `body:` arc path construction (and its `sweep-flag=1`) unchanged; corrected the trigger for the existing ADR-094 `rotate(180 cx cy)` upright-flip so it fires on the correct side for arc belts.
  - Rationale: A 180° rotation of the glyphs about the label midpoint is visually identical to reversing the path direction, and reuses the already-tested flip machinery rather than adding a second path-construction branch. Satisfies AC1's outcome (labels read upright on both sides of the chart) with a smaller, lower-risk change.
  - Severity: minor
  - Forward impact: none — purely the label transform; arc geometry, suppression, and register styling are unchanged.

### Reviewer (audit)
- **Dev deviation (reuse rotate-180 flip vs. literal sweep-flag reversal)** → ✓ ACCEPTED by Reviewer: a 180° glyph rotation about the label midpoint is visually equivalent to reversing the path, reuses tested machinery, and satisfies AC1 (labels upright on both sides). Lower-risk than a second path-construction branch — agrees with author reasoning.
- **Undocumented divergence:** The deviation's claim of "Forward impact: none" is incomplete — the chosen flip-trigger correction was applied to the SVG consumers but NOT to the OTEL consumer (`upright_flip_by_body`, line 1890), creating a telemetry/render divergence. Logged as the HIGH finding above. Severity: HIGH (blocking).
- **Round-2 resolution** → ✓ RESOLVED: Dev applied the single-source fix (line 1890 → `tp_data[3]`, line 1929 reads `upright_flip_by_body[d.body_id]`) AND measured that the divergence was never production-reachable (no `curve_along` body reaches TEXTPATH strategy — arc belts are suppressed; the OTEL span attribute is always default-`False`). I independently confirmed: zero `midpoint.y` heuristics remain in code, the OTEL/SVG now share one value, and the effective fix (flavor layer) is intact. My round-1 HIGH was over-cautious — accurate as a latent-inconsistency flag, but not a live bug. The applied cleanup is correct, zero-risk hygiene.

## Reviewer Assessment (round 2)

**Verdict:** APPROVED

**Re-review of the rework:**
- **Subagent gate:** preflight = Yes/clean (384 tests green, ruff check + format clean, tree clean, diff exactly 4 files; telemetry test file correctly reverted to baseline). Other 8 subagents disabled via settings.
- **[RESOLVED] round-1 HIGH** — single-source applied; OTEL span and SVG element now derive from one geometry-resolved value (`render.py:1890`, `:1929`). `grep` confirms no `[2][1] > 0` / `midpoint[1] > 0` survives in code.
- **[VERIFIED] effective fix intact** — `broken drift` snapshot retains `rotate(180 21.5682537585434 -80.49381885742237)` (own midpoint); ellipse `last_drift` still flips at its bottom. The round-1 flavor-layer fix (`_render_annotation` + `_resolve_curve_along`) is unchanged.
- **[VERIFIED] false-positive correction is sound** — independently re-confirmed the suppression: arc-belt bodies with a textpath annotation never enter the strategy/decision layer, so the `upright_flip_by_body` OTEL path emits default-`False` for all reachable inputs and old/new formulas agreed there. No production divergence existed; the fix is hygiene, not load-bearing.
- **[VERIFIED] no invalid tests left behind** — the vacuous telemetry tests (asserting a textpath-strategy span the suppression layer never emits) were removed; SVG flip behavior remains guarded by the three `test_render_orrery_v2.py` upright tests + two re-baselined snapshots.

**Data flow traced:** `curve_along` → `_resolve_curve_along` (returns `needs_upright_flip`) → flavor layer `_render_annotation` (`:2018`) → SVG `rotate(180 …)` for `broken drift` (correct). Strategy-layer OTEL path now single-sourced but inert for `curve_along` labels (suppressed).

**AC check:** AC1 (labels upright both sides) ✓; AC2 (no OTEL needed) ✓ — no new spans, existing span untouched in behavior; AC3 (cosmetic) ✓.

**Handoff:** To SM for finish-story.