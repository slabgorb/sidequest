---
story_id: "45-43"
jira_key: null
epic: null
workflow: "tdd"
---
# Story 45-43: Orrery v2 visual restoration — match design source

> **Tracker note:** This story was filed and built end-to-end as 45-42 in oq-2.
> A different 45-42 (confrontation calibration v1, itself renumbered from
> 45-41 on oq-1) merged to origin/main first while this work was in flight.
> Renumbered to 45-43 at finish-time. Subrepo branches and PRs (server #192,
> content #179, branch `feat/45-42-orrery-v2-visual-restoration`) keep the
> original 45-42 label — those references are immutable git history. All
> in-flight references below this header still say "45-42" because they
> were written during the live workflow; the story is the same regardless.

## Story Details
- **ID:** 45-43 (originally filed as 45-42)
- **Title:** Orrery v2 visual restoration — match design source
- **Workflow:** tdd
- **Stack Parent:** none

## Spec Reference

Spec at `docs/superpowers/specs/2026-05-04-orrery-v2-visual-restoration.md` — Architect-drafted, UX-amended (Adora Belle Dearheart 2026-05-04), both signed off.

## Story Context

Match server-side orrery base render to the Coyote Reach Orrery v2 design source (renamed Coyote Star post-PR #171). Predecessor 45-40 (course overlay aesthetic alignment) shipped at commit bd1041c — that work established the palette tokens and HUD strips infrastructure that this story builds on.

Three visible playtest bugs closed by this story:
1. **Label corruption from stacked engraved_label annotations** — two `engraved_label` entries for the outer system (`the Last Drift`, `broken drift`) both slot at same fixed position (top-center) instead of honoring their `curve_along` field, producing unreadable "tbrokendrift" smudge.
2. **Inner-cluster collision** — labels for bodies at au ≈ 1.0 (gravel_orchard, far_landing, dead_man_l5, deep_root_world, new_claim) stack at naive `(x+10, y-8)` offset with no radial awareness.
3. **Inconsistent label register** — `last_drift` stored as `"the Last Drift"` (lowercase italic hint) escapes register normalization and renders inconsistently vs caps siblings.

Also restores missing design elements:
- Bearing rose / longitude dial at chart center
- Star-as-reticle (red dashed ring + crosshair) replacing nested disks
- Chalk register for outer system (Grand Gate, Last Drift) — dashed orbits + chalk-class halo
- Moons rendered and labeled at system-root scope (Red Prospect's six moons: Ember, vael thain, Turning Hub, Whitedrift, Dead Lash, The Horn)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-04T13:00:16Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-04 | 2026-05-04T12:01:52Z | 12h 1m |
| red | 2026-05-04T12:01:52Z | 2026-05-04T12:13:40Z | 11m 48s |
| green | 2026-05-04T12:13:40Z | 2026-05-04T12:32:34Z | 18m 54s |
| spec-check | 2026-05-04T12:32:34Z | 2026-05-04T12:38:23Z | 5m 49s |
| green | 2026-05-04T12:38:23Z | 2026-05-04T12:42:55Z | 4m 32s |
| spec-check | 2026-05-04T12:42:55Z | 2026-05-04T12:44:26Z | 1m 31s |
| verify | 2026-05-04T12:44:26Z | 2026-05-04T12:49:07Z | 4m 41s |
| review | 2026-05-04T12:49:07Z | 2026-05-04T12:58:37Z | 9m 30s |
| spec-reconcile | 2026-05-04T12:58:37Z | 2026-05-04T13:00:16Z | 1m 39s |
| finish | 2026-05-04T13:00:16Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **Improvement** (non-blocking): Pydantic's `BaseModel` shadows attribute warnings for the field name `register` (BodyDef, ConfrontationDefinition, OpeningTone). Three classes already use this name across the codebase, so it's a project convention — but the warning noise during test runs is real. Future stories could rename to `cartographic_register` / similar across all three classes for consistency, or suppress the warning class-wide. Out of scope for 45-42. Affects `sidequest/orbital/models.py:54`, `sidequest/magic/confrontations.py:71`, `sidequest/genre/models/narrative.py:114`. *Found by Dev during green phase.*

- **Conflict** (non-blocking): Existing test `tests/orbital/test_render_scopes.py::test_system_scope_renders_drillable_cluster_for_red_prospect` asserts `data-action="drill_in:red_prospect"` is in the SVG at system_root. Spec §4.6 removes the legacy `+N` cluster glyph for parents-with-moons but says "Drill-in still works (click body → drill_in scope), but the affordance becomes 'click anywhere in the moon system' rather than 'click the +N chip.'" — implementation now wraps the body glyph + moon band in a group carrying `data-action="drill_in:<id>"` so both this test and AC #8 (moons render) pass. The actual `+N` text element does NOT appear (verified by `test_parent_with_moons_no_longer_emits_plus_n_cluster_glyph`); only the affordance attribute survives. *Found by Dev during green phase.*

- **Gap** (non-blocking): Pre-existing 45 server-test failures across `test_dice_throw_*`, `test_session_handler_localdm_offline`, `test_opening_turn_bootstrap`, `test_culture_context`, `test_multiplayer_party_status`, `test_turn_manager_round_invariant` — all in subsystems unrelated to orbital rendering. Failure root causes are in `sidequest/server/session_helpers.py` (`'NoneType' object is not callable` from `count_method`) and other server-handler paths. Not introduced by 45-42; likely in-flight stories of Sprint 3. Reviewer should not block 45-42 on these. Affects `sidequest/server/session_helpers.py` and various server handlers. *Found by Dev during green phase.*

### TEA (test design)

- **Question** (non-blocking): Where should `curve_along` validation raise — chart-load or render-time?
  Spec §4.1 says "Unknown curve_along value raises during chart-load (per CLAUDE.md no silent fallbacks)." But `curve_along: orbit_<body_id>` resolution requires the orbits config, and `load_orbital_content` already loads both files together — so chart-load IS the right time. However, `body:<body_id>` non-belt rejection (test_curve_along_body_ref_on_non_belt_raises) needs to know the body's `type`, also available at chart-load. Implementer choice between adding a post-load cross-validator on `OrbitalContent` vs. raising at first render. My tests use `_render_root` which exercises both paths — either implementation passes. Affects `sidequest/orbital/loader.py` or `sidequest/orbital/render.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): Spec §4.3 names two reticle radii (outer=28, inner=20) for the star, and `course_render.py` uses different radii (outer=13, inner=7) for course targets. AC #16's "shared reticle constants" probably means *vocabulary* (dash pattern, color, stroke widths, the `RETICLE_*` prefix) rather than literal radii. My test (`test_palette_exposes_reticle_constants`) accepts any name beginning with `RETICLE_` — implementer can choose whether to namespace as `STAR_RETICLE_OUTER_PX` + `COURSE_RETICLE_OUTER_PX` or share what's actually shareable (dash pattern). Affects `sidequest/orbital/palette.py`. *Found by TEA during test design.*
- **Gap** (non-blocking): The existing `test_render_emits_chart_render_span` in `tests/orbital/test_render.py:150` asserts `body_count == 3` for the world_minimal fixture. Adding 5 new attrs to `emit_chart_render` should not break that count, but the function signature change is breaking — every caller of `emit_chart_render` must pass the new kwargs. Currently the only caller is `render_chart` itself, but Dev should grep before touching the signature to confirm no test/CLI surface depends on it. Affects `sidequest/telemetry/spans/chart.py` and `sidequest/orbital/render.py`. *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)

- **Resolved scope-mismatch silently for `curve_along` annotations off-scope**
  - Spec source: spec §4.1; AC #14 / AC #19
  - Spec text: "Unknown curve_along value raises during chart-load (per CLAUDE.md no silent fallbacks)."
  - Implementation: Two distinct error types. Truly unknown body / wrong type → `ValueError` (raises, fails the render — matches AC #19). Body exists but isn't a direct child of the current centered body → `_CurveScopeMismatch` (caught in `_render_annotation` and the annotation is silently skipped at this scope).
  - Rationale: A chart.yaml authored for system_root scope (where `orbit_grand_gate` resolves to grand_gate's orbit around coyote) would crash on every drill-in render to red_prospect or any other body — grand_gate isn't a child of red_prospect. Skipping at off-scope is correct: the annotation literally has no orbit to attach to in that view, so silent skip is *not* hiding a config error, it's the right scope-respecting behavior. Truly bad data (unknown body, wrong type) still raises loud, which is what the no-silent-fallbacks rule actually cares about.
  - Severity: minor
  - Forward impact: Reviewer should evaluate by the AC-19 pattern: unknown bodies still raise, and the existing fixture's `test_curve_along_unknown_value_raises_at_load_or_render` test passes.

- **Drill-in affordance preserved on body+moon-band wrapper, not just the body glyph**
  - Spec source: spec §4.6
  - Spec text: "The drillable cluster glyph (+N) goes away for bodies that are now showing moons. Drill-in still works (click body → drill_in scope), but the affordance becomes 'click anywhere in the moon system' rather than 'click the +N chip.'"
  - Implementation: When a parent body renders with a moon band, the body glyph and the moon-band group are wrapped in a single `<g class="drillable" data-action="drill_in:<id>" data-body-id="<id>">`. The +N chip (text element) is not emitted. Click on the body OR any element in the moon band routes through the wrapper group's drill_in action.
  - Rationale: Existing `tests/orbital/test_render_scopes.py::test_system_scope_renders_drillable_cluster_for_red_prospect` asserts `data-action="drill_in:red_prospect"` is in the SVG at system_root. Without the wrapper, that test would break. Adding the wrapper preserves the affordance per spec while removing the visible +N glyph (also per spec). Both AC #8 (moons render) and the existing scope test pass.
  - Severity: minor
  - Forward impact: none — implements the spec's intent literally. The wrapper attribute names match the legacy +N cluster's so any client-side hover/drill handler keeps working.

- **Center body excluded from `body_count_<register>` OTEL counts**
  - Spec source: spec §7 AC #23
  - Spec text: "OTEL: `chart.render` span gains `body_count_chalk`, `body_count_engraved`, `body_count_prose`, ... attributes."
  - Implementation: `_RenderStats` accumulator counts only orbiting children + moons; the center body's register (always defaults to `engraved` for stars at root) is skipped.
  - Rationale: Register drives orbit + label styling — the center has no orbit at this scope, so its register attribute is meaningless to "how is the chart drawn?" The TEA test (`test_chart_render_span_has_register_body_counts`) explicitly expects 1/1/1 for a fixture with star + 3 typed children, which only makes sense if the star is excluded.
  - Severity: minor
  - Forward impact: GM panel's `body_count_*` totals describe the visible *orbiting field*, not the centered body. Documented in chart.py docstring.

- **(Resolved) textPath now inherits body's effective label_register; arc_belt body label suppressed when annotation matches** (Architect spec-check 2026-05-04, commit `0a8788d`)
  - Spec source: spec AC #6 + §4.1 last paragraph
  - Spec text: "Last Drift label reads 'Last Drift' along outer ring (textPath, prose register)" + "If both exist, prefer the annotation."
  - Implementation: Two narrow fixes per Architect's recommendations. `_resolve_curve_along` now returns the resolved body id; `_render_annotation` threads its `_effective_label_register` into `_engraved_label_textpath(register=...)`, which maps prose → VT323 italic + opacity 0.85, chalk → Orbitron weight-600, engraved → Orbitron weight-700. New helper `_arc_belt_bodies_with_textpath_annotation` collects arc_belt body ids whose orbit is referenced by a chart.yaml engraved_label and the Phase-5 label loop in `_render_engraved_layer` skips them. Restricted to arc_belt per spec; point-bodies still get both labels.
  - Rationale: Architect (Leonard of Quirm) flagged two visual drifts during spec-check that erode visual fidelity to the design source. Both fixes are mechanical and small (~30 LOC together); one snapshot re-record. Now last_drift textPath renders in VT323 prose register (matching design source lines 470/487/580-585) and the previously-duplicate "Last Drift" radial-out body label is suppressed.
  - Severity: minor (resolved)
  - Forward impact: none — implementation now matches spec literally.

- **`curve_along: orbit_outermost` resolves to outermost direct child, not outermost arc_belt globally**
  - Spec source: spec §4.1
  - Spec text: "`orbit_outermost` → the outermost arc_belt's orbit ellipse (Last Drift, ~10 AU)."
  - Implementation: Resolves to the direct child of the current center with the largest `semi_major_au`. For coyote_star at system_root that's `last_drift` (au=10) regardless of body type, which matches the spec's intent in practice (Last Drift is the outermost direct child *and* an arc_belt). For drill-in scopes, `orbit_outermost` resolves to that scope's outermost direct child instead.
  - Rationale: Spec phrasing implies arc_belt-only resolution but the *intent* is "the outermost ring" — at drill-in scopes there's no arc_belt, so an arc_belt-only resolver would crash drill-in renders that share a chart.yaml with system-root. "Outermost direct child" is the scope-respecting generalization that produces the same answer at root for coyote_star while keeping drill-in renders working.
  - Severity: minor
  - Forward impact: A chart that authors `curve_along: orbit_outermost` expecting a non-belt body wouldn't be wrong — it just gets that body's ellipse, which is the correct curve to follow.

### TEA (test design)

- **AC #19 chart-load fail vs render-time fail**
  - Spec source: spec §4.1, AC #19
  - Spec text: "Wire test: chart.yaml `engraved_label` with unknown `curve_along` value fails at chart-load."
  - Implementation: Test (`test_curve_along_unknown_value_raises_at_load_or_render`) accepts a raise from EITHER `load_orbital_content` OR `render_chart` — it calls `_render_root` which exercises both. The test catches `(ValueError, KeyError)` matching `(curve_along|nonexistent_body|orbit_)`.
  - Rationale: `chart.yaml` is parsed in isolation by pydantic (the `Annotation` model), but resolving `curve_along: orbit_<body_id>` to a real body requires the orbits config — that cross-validation must happen at `load_orbital_content` (which has both files) OR at first render. Either is acceptable per CLAUDE.md no-silent-fallbacks; the test pins the *behavior* (loud failure) without constraining *which file*.
  - Severity: minor
  - Forward impact: Reviewer should accept implementation in either site as long as the failure surfaces before any rendered output ships.

- **AC #18 / AC #24 snapshot tests use auto-record pattern, not pre-pinned bytes**
  - Spec source: spec §7 AC #18, AC #24
  - Spec text: "Snapshot test: Coyote Star at `t_hours=0`, scope=root — pinned canonical SVG, byte-identical across runs."
  - Implementation: AC #18/#24 use `_compare_or_record` (existing pattern in `test_render_snapshots.py`) which auto-records a snapshot on first run and compares thereafter. The fixture is `world_orrery_v2` (synthetic, not the real `coyote_star` content) to keep tests hermetic.
  - Rationale: Pre-pinning bytes requires knowing the renderer's exact output before it exists — impossible in RED phase. Auto-record-on-missing is the project's own established pattern (see existing `test_system_scope_t0_no_party`). Once Dev gets implementation green, `pytest --update-snapshots` records the canonical bytes, and from that point forward the test is byte-identical-pinned per the AC. Real `coyote_star/` content is large (24 bodies); a small synthetic fixture exercises every new register/moon/cluster path with less drift surface.
  - Severity: minor
  - Forward impact: Reviewer should expect Dev to commit the recorded `.svg` snapshots alongside implementation. The behavioral assertions in `test_render_orrery_v2.py` are the genuine RED gate; snapshots are the regression gate after green.

- **AC #16 reticle constants — name flexibility**
  - Spec source: spec §4.3, AC #16
  - Spec text: "Reticle constants (radii, dash pattern) extracted from `course_render.py` into `palette.py`; both renderers reference the shared constants."
  - Implementation: `test_palette_exposes_reticle_constants` accepts any palette attribute name containing `RETICLE` (e.g., `RETICLE_OUTER_RADIUS`, `STAR_RETICLE_OUTER_RADIUS`, `RETICLE_DASH_PATTERN`). The negative test (`test_course_render_imports_reticle_constants_from_palette`) asserts the literal `_RETICLE_OUTER_R = 13.0` is GONE from `course_render.py`.
  - Rationale: Star reticle (r=28/20) and course reticle (r=13/7) have different radii; only the *vocabulary* (dash pattern, naming, palette location) is shareable. Spec said "e.g." in its example names — flexibility intended.
  - Severity: minor
  - Forward impact: Reviewer should not require exact name matching against the spec; verify the *vocabulary share* (course_render imports from palette, no private literals).

### Architect (reconcile)

I drafted this spec on 2026-05-04 and reconcile it now against the shipped implementation. The TEA and Dev deviation entries above are accurate, well-formed (each carries the required 6 fields), and reflect what the code actually does. No corrections needed to existing entries.

One material deviation was missed during the in-flight phases — escalated from a Reviewer Delivery Finding to a documented spec-implementation reconciliation here, because the spec-gap is mine and any follow-up story will reference this entry:

- **`orbit_outermost` resolves to drill-in scope's outermost child, producing a textPath-on-a-moon at non-root scopes**
  - Spec source: spec §4.1, "Curve resolution" bullet — ships with this story
  - Spec text: "`orbit_outermost` → the outermost arc_belt's orbit ellipse (Last Drift, ~10 AU)."
  - Implementation: `_resolve_curve_along` (`render.py:469-507`) generalized this to "outermost direct child of the current centered body, ranked by `semi_major_au`." At root scope this resolves to `last_drift` for `coyote_star` (correct, matches spec example). At drill-in scope it resolves to whichever child of the drilled-into body has the largest `semi_major_au` — for `world_orrery_v2` drill-in to `giant`, that's `moon_hidden`; the textPath `<textPath>— the Outer Drift —</textPath>` therefore wraps `moon_hidden`'s tiny orbit. For `coyote_star` drill-in to `red_prospect`, it would wrap `the_horn`'s moon-band ring with "— Last Drift —". Verified in the recorded `orrery_v2_drill_in_giant.svg` snapshot (line 1).
  - Rationale: My spec phrasing assumed system-root scope (Last Drift is at au=10, "outermost" implicitly meant "outermost in the system"). I never wrote a resolution rule for non-root scopes. The Dev pragmatically chose "outermost direct child of the current center" which works at root and degrades cleanly without crashing at drill-in — but produces a visual oddity. Restricting to arc_belt-only would have crashed at every drill-in scope (no arc_belts among children at drill-in for any current world), so the Dev's choice was the safer one. Both Reviewer and I now agree the implementation is correct for what we asked but the spec was incomplete.
  - Severity: minor — affects the decorative chart-frame textPath at drill-in scopes; root-scope (the primary view of Coyote Star) is correct. The visual oddity is real but small audience: drill-in is a secondary interaction, and the misplaced textPath is at an obvious-it's-a-moon-band radius rather than overlaying load-bearing data.
  - Forward impact: Recommend a follow-up story (target Sprint 3 backlog or future) to either (a) restrict `orbit_outermost` to root-scope by raising `_CurveScopeMismatch` when `center_id` has a non-None parent, ~3 LOC in `_resolve_curve_along`, OR (b) add a `scope: Literal["any", "root"] = "any"` field to `Annotation` so chart authors can opt their decorative labels into root-only rendering, ~10 LOC in `models.py` + `render.py`. Option (a) is simpler and matches my original spec intent; option (b) is more flexible but requires a schema bump that ripples to chart.yaml. Suggest (a). No code in 45-42's diff blocks this future fix.

Reviewer also flagged a non-deviation observation (test-coverage gap on the round-2 fixes — they're snapshot-pinned but lack behavioral assertions). That's a test-discipline improvement, not a spec/code mismatch, so it stays in Delivery Findings rather than escalating here.

### AC deferral status

No ACs were deferred during this story — all 24 are addressed in the implementation per the AC coverage check in the Reviewer Assessment. AC accountability is therefore a no-op for spec-reconcile.

## Banned Patterns (from Project Memory)

- **NO `git stash`** — never stash work to "verify on prior commit" or for any other reason. Commit or discard.
- **NO running tests on prior commits to "prove pre-existing failure"** — run tests on current HEAD only. If something was already broken, the fix addresses the current code.

## Implementation Phasing (Six commits per spec §8)

1. **`curve_along` honored** (§4.1) — Fixes textPath rendering for engraved labels. ~50 LOC + 2 tests.
2. **Radial-out label anchor** (§5.1-§5.2) — Inner-cluster collision fixed via bearing-aware placement. ~25 LOC + 1 test.
3. **Moons rendered at system-root scope** (§4.6) — Replaces `+N` cluster glyph with moon band. ~80 LOC + snapshot + wire test.
4. **Bearing rose** (§4.2) — `_render_bearing_rose` + `palette.py` constants. ~70 LOC + snapshot test.
5. **Star reticle + shared reticle constants** (§4.3) — Replaces `_star_glyph`; lifts constants to `palette.py`. ~40 LOC change + ~10 LOC `palette.py`.
6. **Chalk register + label_register override** (§4.4 + §4.5) — Two new BodyDef fields, renderer plumbing. ~80 LOC + content updates to coyote_star orbits.

## Sm Assessment

**Story is well-scoped and ready for TDD.** The hard work was already done by Architect + UX in the spec, which carries 24 ACs broken into six tight commits (§8). Five points feels right: ~350 LOC, well-fenced surface (render.py + models.py + palette.py + two YAML files in coyote_star), no cross-repo plumbing changes.

**Predecessor in place.** 45-40 (course overlay aesthetic) shipped at bd1041c; palette tokens and HUD strip infrastructure already merged. This story builds on that, doesn't fight it.

**Why TDD fits here despite being mostly visual:**
- Snapshot tests (ACs 18, 24) are the right green-bar — byte-identical SVG output for Coyote Star at t=0 and drill-in.
- Wire tests (ACs 19-22) cover the BodyDef field plumbing — `register`, `label_register`, `curve_along` validation, peer-collision tier. These are real branching logic, not just rendering.
- OTEL attributes (AC23) are testable: `body_count_chalk`, `body_count_engraved`, `body_count_prose`, `body_count_moons_rendered`, `label_collision_tier_max`. Counts can be asserted without sniffing pixels.

**Routing:** Igor (TEA) writes the failing snapshot + wire tests for commit 1 (`curve_along` honored, §4.1). Six commits → six TDD cycles, smallest first. Igor decides whether to stack all reds up front or interleave with Ponder. Default to per-commit cycles to keep diff size honest.

**Risks flagged for downstream:**
- Snapshot tests on SVG can be brittle. If output is dependent on dict insertion order, lock the rendering loop's iteration explicitly (don't rely on Python 3.7+ dict ordering as a contract for a snapshot byte-comparison).
- AC23's OTEL attributes need to land on the *render* span, not a parent — verify the span-context plumbing is straight before asserting.
- Content changes in `sidequest-content/genre_packs/space_opera/worlds/coyote_star/` target `develop` per gitflow (per memory: feedback_gitflow_content.md). Reviewer must use `--base develop` for that PR.

**Banned patterns reminder for all downstream agents:** no `git stash`, no test runs on prior commits to prove "pre-existing" failures.

## Acceptance Criteria (24 total; see spec §7)

### Player-facing (ACs 1-11)
- AC1: Inner-cluster labels readable without collision
- AC2: "tbrokendrift" smudge gone; engraved labels follow their own arc curves
- AC3: Bearing rose visible with cardinal numerals 000/090/180/270 and intermediate 030..330
- AC4: Coyote (star) renders as red reticle + crosshair with `COYOTE` label inside
- AC5: Grand Gate orbit dashed (chalk), label CAPS chalk; Last Drift orbit dashed, label lowercase italic (prose)
- AC6: Last Drift label reads "Last Drift" along outer ring (textPath, prose register)
- AC7: Scale ruler reads cleanly
- AC8: Red Prospect's six moons all render and labeled at system-root scope
- AC9: Far Landing renders Tethys Watch as moon; Deep Root renders Lower Kerel only (kerel_eye elided)
- AC10: Inner-cluster labels don't collide with bearing rose
- AC11: Hazard bodies carry dashed outline glyph signal (+ red color for accessibility)

### Engineering (ACs 12-24)
- AC12-13: New BodyDef fields: `register` (Literal engraved|chalk|prose, default engraved), optional `label_register` override; `moon_display_radius_px` (int|None), `show_at_system_scope` (bool, default True)
- AC14: `_render_annotation` for engraved_label honors `curve_along`; raises on unknown values
- AC15-17: Constants in `palette.py` for bearing rose, reticle, label de-collision
- AC18: Snapshot test — Coyote Star t=0, scope=root, byte-identical SVG
- AC19-22: Wire tests — curve_along unknown value, chalk register, label_register override, peer-collision tier
- AC23: OTEL span attributes: `body_count_chalk`, `body_count_engraved`, `body_count_prose`, `body_count_moons_rendered`, `label_collision_tier_max`
- AC24: Snapshot test drill-in to Red Prospect — moons still render

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core feature work with 24 ACs and a detailed spec — every AC gets pinned coverage.

**Test Files:**
- `sidequest-server/tests/orbital/test_render_orrery_v2.py` (new) — 33 behavioral assertions covering ACs 1-23, organized by spec section in 8 test classes:
  - `TestBodyDefSchemaExtensions` (10 tests) — AC #12-13: register / label_register / moon_display_radius_px / show_at_system_scope field validation including Literal value enforcement.
  - `TestEngravedLabelCurveAlong` (7 tests) — AC #2, #14, #19: textPath emission, defs+href wiring, anti-regression for the 'tbrokendrift' overlap, body_ref non-belt rejection, backward-compat for unanchored labels.
  - `TestBearingRose` (5 tests) — AC #3, #15: cardinal + intermediate numerals, system-root-only rendering, palette constants exposed.
  - `TestStarReticle` (5 tests) — AC #4, #16: red dashed outer ring, no legacy corona, palette reticle constants, course_render no longer carries private literals.
  - `TestRegisterField` (5 tests) — AC #5, #20, #21: chalk = dashed orbit, engraved = solid orbit, label_register=prose decouples (VT323 italic) from chalk orbit, default-engraved is Orbitron CAPS.
  - `TestMoonsAtSystemScope` (7 tests) — AC #8, #9: moons render with own glyphs at system_root, show_at_system_scope=False elides at root but stays at drill-in, +N cluster glyph removed for parents now showing moons, prose register auto-applied to moon labels.
  - `TestLabelDeCollision` (4 tests) — AC #1, #10, #17, #22: palette constants exposed, three-body cluster gets distinct anchor positions, inner labels clear bearing rose by ≥ outer + clearance, peer-collision tier produces strictly increasing radial offset (tier 0/1/2).
  - `TestHazardNonColorSignal` (1 test) — AC #11: hazard body glyph carries stroke-dasharray non-color signal.
  - `TestOtelChartRenderAttributes` (4 tests) — AC #23: chart.render span has body_count_chalk/engraved/prose/moons_rendered/label_collision_tier_max with correct values for representative fixtures.
  - `TestOrreryV2FixtureWiring` (5 tests) — wiring: fixture loads, exercises every register, has the override + elision + OTEL attribute set.
- `sidequest-server/tests/orbital/test_render_snapshots.py` (extended) — 2 tests for AC #18 (system root) and AC #24 (drill-in to giant), using existing `_compare_or_record` pattern. Auto-records on first green run.
- `sidequest-server/tests/orbital/fixtures/world_orrery_v2/` (new fixture) — synthetic chart exercising every new code path: inner cluster (alpha/beta/gamma within 25° arc), hazard (trap), gas-giant moons including elided one, chalk register (outpost), chalk-orbit + prose-label override (drift). Used by snapshot tests; also asserted on directly for wiring.

**Tests Written:** 33 assertion-level + 2 snapshot tests covering 24 ACs.
**Status:** RED (33 failing on assertion + 14 fixture-load errors from pydantic correctly rejecting unknown BodyDef fields — these resolve once Dev adds the schema fields). 185 existing orbital tests still pass — no regression.

### Rule Coverage

Per `.pennyfarthing/gates/lang-review/python.md`. The rules apply to dev's implementation; for tests in RED phase the relevant ones are #6 (test quality) and #3 (type annotations at boundaries). Self-checked:

| Rule | Test(s) / Self-check | Status |
|------|----------------------|--------|
| #6 test-quality: vacuous assertions | All 33 tests assert specific values, structures, or attributes — no `assert True`, no truthy-only `assert result`, no missing-assertion bodies. | passing |
| #6 test-quality: implementation-coupling | Tests target SVG output structure and palette constant existence, not internal renderer call paths. Implementation can land in render.py / models.py / palette.py / loader.py in any combination. | passing |
| #6 test-quality: shared mutable state | All fixtures are per-test (function-scope `_orbits_with_bodies`); module-level state is read-only constants. | passing |
| #3 type annotations | Test helpers (`_orbits_with_bodies`, `_star_with`, `_render_root`) have full annotations. Test methods don't need return annotations per pytest convention. | passing |
| no-silent-fallbacks (CLAUDE.md) | Tests for AC #19 explicitly assert `pytest.raises` on unknown `curve_along` values; AC #14 same for non-belt body_ref. | passing |
| Wire tests (CLAUDE.md "Every Test Suite Needs a Wiring Test") | `TestOrreryV2FixtureWiring` (5 tests) drives the full fixture through render and asserts wiring. `test_course_render_imports_reticle_constants_from_palette` is a structural wiring test against the reticle-share refactor. | passing |
| OTEL discipline (CLAUDE.md) | AC #23 has 4 OTEL tests verifying the new span attributes are emitted with correct counts. | passing |

**Rules checked:** All 13 lang-review rules reviewed; rules #6 and #3 actively enforced. Other rules (logging, async, security, dependencies, resource leaks) don't apply to test code in RED phase but remain active for Dev's implementation.
**Self-check:** No vacuous assertions; no `let _ =` analogues; no `assert is_none()` on always-None values.

**Open question for Dev (logged as Delivery Finding):** AC #19 (`curve_along` unknown value fails loud) — spec §4.1 says "during chart-load" but the cross-file resolution requires both files. My test accepts a raise from either `load_orbital_content` or `render_chart`. Implementer's choice; either passes.

**Handoff:** To Dev (Ponder Stibbons) for implementation. Six-commit phasing per spec §8 is the recommended path. Smallest first (curve_along), most surface last (register/label_register/moon-band). Snapshot files will need to be recorded with `pytest --update-snapshots` once the renderer output stabilizes.

## Dev Assessment

**Implementation Approach:** Two commits in `sidequest-server` + one in `sidequest-content`. Followed the spec's six-section breakdown (§4.1 → §4.6 + §5) but bundled them into one renderer rewrite per the user's "right-size plan ceremony" memory — 350 LOC of cohesive renderer changes don't bisect well into six tiny commits, and each test class drives multiple sections at once. Content updates ride a separate commit so reviewers can scan the schema-bearing renderer change separately from the world-data adoption.

**Files Changed:**
- `sidequest-server/sidequest/orbital/models.py` (+38 LOC) — BodyDef gains `register`, `label_register`, `moon_display_radius_px`, `show_at_system_scope`. New `Register` Literal type.
- `sidequest-server/sidequest/orbital/palette.py` (+82 LOC, total 105) — bearing rose constants, reticle vocabulary (STAR_RETICLE_* + COURSE_RETICLE_* + RETICLE_DASH_PATTERN), register styling tokens, moon-band constants, label de-collision constants, hazard non-color signal.
- `sidequest-server/sidequest/orbital/render.py` — substantial rewrite (~870 LOC, was ~755). Added: `_star_reticle`, `_render_bearing_rose`, `_resolve_curve_along` (+ `_CurveScopeMismatch`), `_engraved_label_textpath`, `_render_moon_band`, `_BodyPlacement`, `_assign_collision_tiers`, `_resolve_anchor`, `_RenderStats`. Removed: `_star_glyph` (legacy corona), the auto-emitted star bearings (superseded by bearing rose).
- `sidequest-server/sidequest/orbital/course_render.py` — 4 lines: `_RETICLE_*` literals replaced by references to `palette.COURSE_RETICLE_*` per AC #16.
- `sidequest-server/sidequest/telemetry/spans/chart.py` — `emit_chart_render` gains 5 keyword args (defaults to 0 for legacy callers).
- `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml` — `last_drift` chalk/prose, `grand_gate` chalk, Red Prospect moons get `moon_display_radius_px`, `vael_thain` hazard=true, `kerel_eye` show_at_system_scope=false.
- `sidequest-content/genre_packs/space_opera/worlds/coyote_star/chart.yaml` — `"the Last Drift"` → `"Last Drift"` (renderer bakes em-dash decoration).
- 3 existing snapshot files re-recorded; 2 new orrery_v2 snapshots recorded.

**Test Status:** GREEN.
- `tests/orbital/test_render_orrery_v2.py`: 53/53 pass.
- `tests/orbital/` (full suite, 232 tests): 232/232 pass.
- Snapshot tests: 5/5 pass (3 re-recorded for the world_minimal fixture, 2 newly recorded for world_orrery_v2).
- 45 server-test failures elsewhere in the suite are pre-existing in subsystems unrelated to orbital (logged as a Delivery Finding); failure root causes are in `session_helpers.py` and other server-handler paths I did not touch.

**Smoke-tested against real coyote_star content:** Loads cleanly (21 bodies). At system_root scope with party at `far_landing`, the chart renders the bearing rose, star reticle, chalk-dashed orbits for Grand Gate + Last Drift, prose-styled "Last Drift" textPath label, all 6 Red Prospect moons (including hazard-flagged vael_thain with the dashed non-color signal), Tethys Watch around Far Landing, Lower Kerel only around Deep Root (kerel_eye elided), and BROKEN DRIFT engraved-label textPath. 66 KB of SVG; bisect-friendly fallback on `_CurveScopeMismatch` for drill-in renders.

**Open items for Reviewer:** Three Delivery Findings logged: (1) pydantic register-shadows-BaseModel warnings (project-wide convention, not my concern to fix), (2) drill-in affordance preserved via wrapper group not separate +N chip, (3) 45 pre-existing unrelated server-test failures.

**Handoff:** To Reviewer (Granny Weatherwax) for code review. PR base branches:
  - `sidequest-server` PR → `develop` (per repos.yaml)
  - `sidequest-content` PR → `develop` (per gitflow memory)

### Dev (implementation) — round 2 (post spec-check)

After Architect (Leonard of Quirm) flagged two visual drifts during spec-check, applied two narrow fixes (commit `0a8788d`, ~30 LOC). Both are documented in the Design Deviations log above as resolved. Phase: green→spec-check (2nd pass). 232 orbital tests pass; snapshots re-recorded.

Smoke-tested against real coyote_star content:
- "Last Drift" rendered exactly once (textPath only; body radial-out suppressed)
- last_drift textPath font: VT323 monospace (prose register, matches design source AC #6)
- broken_drift textPath font: Orbitron monospace (engraved register — its body has no register override)
- Two chalk dashed orbits: Last Drift (au=10) + Grand Gate (au=6.5)
- All 6 Red Prospect moons render at system scope; vael_thain hazard signal present.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (2 mismatches, both Minor / Behavioral)
**Mismatches Found:** 2

I drafted this spec myself on 2026-05-04, so I'm holding the implementation against my own intent. Implementation passes 53 new tests + 232 orbital tests + smoke-tested against real coyote_star content (21 bodies, 66KB SVG, all moons + chalk orbits + bearing rose visible). Two visual deviations remain — both narrow, both in the textPath path of §4.1, and both drift from the *visual fidelity to the design source* that this story is fundamentally about.

### Mismatch 1: textPath ignores body's label_register (AC #6)

(Behavioral — Minor)

- **Spec (AC #6):** "Last Drift label reads 'Last Drift' along outer ring (textPath, prose register)."
- **Spec (§4.4):** prose register = VT323 monospace, font-size 10, opacity 0.85, font-style italic.
- **Code (`render.py:545-575` `_engraved_label_textpath`):** textPath uses `palette.FONT_DISPLAY` (Orbitron) + font-size 12 + italic. Fixed styling regardless of which body the curve_along resolves to.
- **Verified:** Snapshot grep — textPath for `curve_orbit_drift` renders as Orbitron italic, while the body's own radial-out label renders correctly as `font-family="VT323, monospace" font-size="10" font-style="italic" opacity="0.85"`. The textPath is supposed to BE the prose-register label per AC #6; instead it's Orbitron and the body's separate radial-out label is the only thing in prose.
- **Recommendation:** **B (fix code)** — when `curve_along` resolves to a body's orbit (`orbit_<body_id>` or `orbit_outermost` resolving to a body), `_engraved_label_textpath` should inherit that body's effective `label_register` (via `_effective_label_register`) and pick font-family / font-size / opacity / font-style accordingly. ~15 LOC: thread the body's effective register through `_resolve_curve_along`'s return tuple (or a new helper) and have `_engraved_label_textpath` accept a `register` kwarg that maps to the right palette tokens.

### Mismatch 2: arc_belt body label not suppressed when chart.yaml engraved_label references the same body (§4.1 last paragraph)

(Behavioral — Minor)

- **Spec (§4.1, last paragraph):** "Also fix the broken_drift / arc_belt body's own `body.label` rendering: make ARC_BELT body labels follow the same textPath treatment when chart.yaml provides a matching `engraved_label` annotation. **If both exist, prefer the annotation.**"
- **Code:** Both render. Arc_belt bodies emit a body label at the radial-out anchor (Phase 5 of `_render_engraved_layer`) AND chart.yaml's `engraved_label` emits a textPath wrapping the orbit. No suppression logic.
- **Verified:** `grep -o "Outer Drift" tests/orbital/snapshots/orrery_v2_system_t0.svg | sort | uniq -c` → `2 Outer Drift`. Two visible labels for the same body in a snapshot whose stated job is to pin the v2 design.
- **Recommendation:** **B (fix code)** — before Phase 5 label rendering, walk `chart.annotations`: if any `engraved_label` has `curve_along` resolving to an arc_belt body's orbit (via `_resolve_curve_along`), record that body's id in a `suppressed_label_body_ids` set. Skip the body's own label render in Phase 5 if it's in that set. ~15 LOC. Restrict to `arc_belt` bodies per spec — point-bodies can legitimately have both a textPath (name on the ring) AND a radial-out label (name next to the planet), so the suppression rule is narrow.

### Substance items I checked and accept (no mismatch)

- AC #4 star label position — spec literally says `(x, y - 48)`; code uses `(0, -palette.STAR_RETICLE_OUTER_R - 8) = (0, -36)`. Cosmetic / Trivial — implementation reads better visually (label closer to the reticle than the spec's literal coordinate). Accept as-is, noted in passing.
- AC #18 / #24 use synthetic `world_orrery_v2` fixture instead of literal `coyote_star/` — TEA logged this with full rationale (hermetic tests, smaller drift surface). Accept as documented deviation.
- AC #19 chart-load vs render-time — TEA accepted either; Dev chose render-time with `_CurveScopeMismatch` for off-scope silent-skip. Sound design (raises loud on unknown bodies, scope-aware on legitimate cross-scope chart.yaml). Accept.
- AC #16 reticle constant naming flexibility — TEA accepted any RETICLE_*; Dev split into STAR_RETICLE_* + COURSE_RETICLE_* + RETICLE_DASH_PATTERN. Cleaner than my original spec text suggested. Accept.
- AC #23 center body excluded from register counts — Dev's deviation log explains. Sound: register drives orbit/label styling, the center has no orbit. Accept.

### Decision

**Hand back to Dev** for the two narrow textPath fixes. Both deviations specifically erode visual fidelity to the design source — the primary deliverable of this story. Combined fix is ~30 LOC and one snapshot re-record. The implementation is otherwise complete; this is the polish pass that makes the textPath actually be the "outer-ring prose register" label per AC #6 instead of a styled-incorrectly duplicate.

Phase routes back to **green** (Dev) until the two fixes land; then return to spec-check.

---

## Architect Assessment (spec-check, round 2)

**Spec Alignment:** Aligned
**Mismatches Found:** None (the two from round 1 are resolved)
**Decision:** Proceed to TEA verify.

Dev applied both recommendations in commit `0a8788d` (~125 lines changed in `render.py`, snapshots re-recorded). Spot-verified at the snapshot level:

1. **AC #6 textPath register inheritance — verified resolved.** `grep -oE 'font-family="[^"]+"[^>]*opacity="0.85"[^>]*>\s*<textPath[^>]*>— the Outer'` against `orrery_v2_system_t0.svg` returns: `font-family="VT323, monospace" font-size="10" font-style="italic" opacity="0.85" ...><textPath ...>— the Outer`. That's prose register exactly per `palette.LABEL_PROSE_*` — VT323 monospace, italic, opacity 0.85. AC #6 ("textPath, prose register") now satisfied for `last_drift`.

2. **§4.1 last paragraph (arc_belt body label suppression) — verified resolved.** `grep -c "Outer Drift" orrery_v2_system_t0.svg` returns `1` (was `2` prior to the fix). The arc_belt body's radial-out label is no longer rendered when chart.yaml has a matching engraved_label.

**Code review of the implementation:**
- `_resolve_curve_along` now returns a 3-tuple including the resolved body id. Return-type change is contained — only callers are `_render_annotation` and the new `_arc_belt_bodies_with_textpath_annotation` helper, both updated.
- `_engraved_label_textpath(register=...)` has three palette-driven branches (prose/chalk/engraved). Uses palette tokens consistently — no inline literals.
- `_arc_belt_bodies_with_textpath_annotation` correctly catches both `_CurveScopeMismatch` (off-scope, won't render) and `ValueError` (malformed, fails upstream in flavor-layer). Suppression set restricted to `BodyType.ARC_BELT` per spec — point-bodies retain both labels as designed.
- Suppression logic in `_render_engraved_layer` Phase 5 is a single-line skip with a small comment explaining why moon-band stats accounting still runs (defensive symmetry; no current arc_belt moons but keeps the bookkeeping consistent for future schemas).

**Smoke-tested against real coyote_star content** (per Dev's commit message): "Last Drift" renders once via VT323 textPath; broken_drift renders once via Orbitron textPath (correct — broken_drift body has no register override so default engraved); both chalk orbits render dashed; all 6 Red Prospect moons render at system scope.

The implementation now matches the spec literally where it was drifting before. Ship it.

## TEA Assessment (verify phase)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Cousin Igors:** reuse, quality, efficiency
**Files Analyzed:** 7 (5 production: render.py / models.py / palette.py / course_render.py / chart.py + 2 test files)

| Cousin Igor | Status | Findings |
|-------------|--------|----------|
| simplify-quality | clean | Strong typing, consistent naming, no dead code, no unused imports. Documented intentional patterns (course_render geometry mirror) recognized as design, not defect. |
| simplify-reuse | 3 findings | (high) cross-module geometry helpers duplicated by intentional design comment; (medium) register→font styling appears in both `_engraved_label_textpath` and `_label_text`; (low) haloed-text divergence between `render.py` (svgwrite) and `course_render.py` (raw SVG strings). |
| simplify-efficiency | 2 findings | (high) `_allocated_moon_radii` sorts `used` list inside the per-moon loop; (medium) two svgwrite validator monkey-patches duplicate the passthrough check. |

**Applied:** 1 high-confidence fix.
- `_allocated_moon_radii` (`render.py:1036-1049`): `used` was a sorted list with per-iteration `used.sort()`; only ever queried via `in`. Replaced with a `set[float]` — single membership-check data structure, dropping the in-loop sort entirely. Commit `56aa7f5`.

**Not applied (pre-existing / out of scope):**
- The cross-module geometry-helper duplication (reuse high) is pre-existing in `course_render.py` and explicitly documented at the file as intentional ("Mirror of `render._viewport_for_scope` scale computation"). Extraction to a shared `geometry.py` would be a real cleanup but is *not* in 45-42's diff and not in this story's scope. Logged as a forward-looking finding for future cleanup.

**Flagged for manual review (medium confidence):**
- (reuse #2) Register→style branching duplicated in `_engraved_label_textpath` and `_label_text`. ~60 LOC of three-branch conditionals that could be a single `_register_style_attrs(register) -> dict` helper. Both call sites are 45-42 code; the duplication was introduced (or expanded) in this story. Reviewer's call: keep as-is (each branch has slightly different defaults — e.g., engraved textPath font-size 12 vs body-label 10) or extract.
- (efficiency #2) Two svgwrite validator monkey-patches share the same passthrough check. Pre-existing pattern that 45-42 added two new entries to (`href`/`xlink:href`/`startOffset`/etc.). Pure cleanup; module-load cost only.

**Noted (low confidence):**
- Haloed-text divergence between `render.py` and `course_render.py`. Pre-existing. Recommend deferring — different rendering contexts (svgwrite Drawing vs. raw SVG fragments) make extraction non-trivial.

**Reverted:** 0 — no regression detected after applying the high-confidence fix.

**Overall:** simplify: applied 1 fix (high-confidence), 1 flagged for review (medium), 1 deferred (out of scope), 1 noted (low).

### Quality Checks

- `uv run ruff check` on all 7 changed files: **All checks passed**.
  - One pre-existing ruff error in `sidequest/orbital/render.py` (`dataclasses.field` unused — left over from initial scaffolding). Removed in commit `56aa7f5`.
  - One ruff F841 in `tests/orbital/test_render_orrery_v2.py` (unused `trap_segment` regex assignment from RED-phase exploration). Removed in commit `13d2e89`.
  - Four other ruff errors in `sidequest/orbital/course.py` and `sidequest/orbital/course_geometry.py` are **pre-existing**, not introduced by 45-42, and outside this story's scope. Logged as a Delivery Finding.
- `uv run pytest tests/orbital/`: **232 passed**, 0 failed, 0 errored.
  - All 53 new tests in `test_render_orrery_v2.py` pass.
  - All 5 snapshot tests pass.
  - All 174 pre-existing orbital tests still pass — no regression from the 45-42 work.
  - 3 warnings: pydantic `register`-shadows-BaseModel warnings on three classes (project-wide convention; logged as Delivery Finding by Dev).

**Banned-pattern check (per session-file):** No `git stash` operations were performed. No tests were run on prior commits to "prove pre-existing failure" — the 4 ruff errors in `course.py`/`course_geometry.py` were identified at current HEAD and noted as pre-existing without comparing to develop.

### Delivery Findings — TEA verify

- **Improvement** (non-blocking): `sidequest/orbital/course.py:225` has UP037 (quoted type annotations) and F821 (undefined `Scope` in annotation) lint errors. `sidequest/orbital/course_geometry.py:10` has an unused `math` import. All three pre-existing on develop, not introduced by 45-42. Future hygiene story could clean. *Found by TEA during test verification.*
- **Improvement** (non-blocking): Register→font-styling logic appears identically in `_engraved_label_textpath` (textPath) and `_label_text` (radial-out body label) — both switch on register (engraved/chalk/prose) to pick font_family / font_size / font_style / font_weight / letter_spacing / opacity. ~60 LOC across two functions. Extraction into a `_register_style_attrs(register) -> dict` helper is the obvious DRY win but would require unifying defaults (engraved textPath uses font_size 12, engraved body label uses 10). Flagged medium-confidence; Reviewer can decide. Affects `sidequest/orbital/render.py:571-616` and `sidequest/orbital/render.py:793-836`. *Found by TEA during test verification.*

**Handoff:** To Reviewer (Granny Weatherwax) for code review. Implementation is clean, tested, simplified. PR base branches: `sidequest-server` → `develop`, `sidequest-content` → `develop`.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 blocking; 1 cosmetic warning (Pydantic register-shadow on BodyDef — pre-existing project pattern) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (1 ran, 8 disabled per `workflow.reviewer_subagents` settings)
**Total findings:** 0 confirmed (preflight clean), 0 dismissed, 0 deferred from subagents. Reviewer's own diff-read found 2 non-blocking observations (logged below as Delivery Findings).

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** orbits.yaml + chart.yaml → loader → models (BodyDef carries register/label_register/moon_display_radius_px/show_at_system_scope) → `_arc_belt_bodies_with_textpath_annotation` (computes suppression set once) → `_render_engraved_layer` (bearing rose, body glyphs, moon band, register-driven orbit/label styling, label de-collision tier) → `_render_flavor_layer` (textPath via `_resolve_curve_along` returning resolved-body-id, register inherited via `_effective_label_register`) → svgwrite Drawing → `emit_chart_render` (5 new register/moon/tier OTEL attrs). Safe because: (a) the suppression set is computed once and threaded through; (b) `_CurveScopeMismatch` distinguishes "off-scope, silent skip" from "unknown body, raise loud"; (c) snapshot tests + 53 behavioral tests pin every visible output path.

**Pattern observed:** Three-phase rendering (collect placements → tier-assign → resolve anchors → render labels) at `render.py:1205-1396`. Cleaner than the prior interleaved single-loop, and necessary for cross-body collision-tier assignment which can't decide one body's tier without knowing all neighbors' bearings. Pattern is correctly mirrored across direct children, arc-belts, and moon-band placements via `all_placements = placements + arc_belt_placements + moon_band_placements`.

**Error handling:**
- `_resolve_curve_along` distinguishes truly unknown bodies (`ValueError`, raises) from off-scope bodies (`_CurveScopeMismatch`, caller-handled) — see `render.py:434-543`. AC #19 satisfied per the existing `test_curve_along_unknown_value_raises_at_load_or_render`.
- `_arc_belt_bodies_with_textpath_annotation` (`render.py:640-658`) catches both `_CurveScopeMismatch` and `ValueError` — broader than `_CurveScopeMismatch` alone, justified by the comment that the flavor-layer's own resolver still raises loudly on truly bad data. Best-effort suppression paired with strict flavor-layer rendering. Acceptable.
- `chart.py emit_chart_render` defaults all new params to 0 — backward compatible with any non-orbital callers (none today, but defensive).
- One genuine concern noted in Delivery Findings: at non-root scopes, `orbit_outermost` resolves to a child of the drilled-into body — at drill-in to giant in the orrery_v2 fixture, this produces a `<textPath>— the Outer Drift —</textPath>` wrapping `moon_hidden`'s tiny orbit. Not a crash; visual oddity at drill-in. Non-blocking; flagged as a follow-up.

**Spec/AC coverage check:**
- AC #1 (inner-cluster collision-free): covered by `TestLabelDeCollision::test_inner_cluster_labels_have_distinct_anchor_positions`. ✓
- AC #2 (tbrokendrift smudge gone): covered by `TestEngravedLabelCurveAlong::test_two_engraved_labels_with_curve_along_do_not_collide_at_top` + visual restoration. ✓
- AC #3, #15 (bearing rose + palette constants): `TestBearingRose` (5 tests). ✓
- AC #4, #16 (star reticle + palette extraction): `TestStarReticle` (5 tests, including `test_course_render_imports_reticle_constants_from_palette`). ✓
- AC #5, #20, #21 (chalk register, label_register override): `TestRegisterField` (5 tests). ✓
- AC #6 (Last Drift textPath in prose register): verified at the snapshot byte level after the round-2 fix; `font-family="VT323, monospace" opacity="0.85"` confirmed in `orrery_v2_system_t0.svg`. **Coverage gap noted in Delivery Findings**: no behavioral test asserts "textPath inherits the resolved body's effective_label_register"; only snapshot regression catches it.
- AC #7 (scale ruler): no regression — flavor layer untouched for scale_ruler.
- AC #8, #9 (moons at system-scope, kerel_eye elision): `TestMoonsAtSystemScope` (7 tests). ✓
- AC #10 (inner labels clear bearing rose): `TestLabelDeCollision::test_inner_cluster_labels_clear_bearing_rose`. ✓
- AC #11 (hazard non-color signal): `TestHazardNonColorSignal::test_hazard_body_glyph_has_dashed_outline`. ✓
- AC #12, #13 (BodyDef field additions): `TestBodyDefSchemaExtensions` (10 tests covering defaults, Literal validation, type coercion). ✓
- AC #14, #19 (curve_along honored, fail-loud on unknown): tests cover both, including the body-ref non-belt case. ✓
- AC #17, #22 (label de-collision constants + tier behavior): `TestLabelDeCollision` (4 tests). ✓
- AC #18, #24 (snapshot byte-pinning): `test_render_snapshots.py::test_orrery_v2_system_scope_t0` + `test_orrery_v2_drill_in_giant`. Recorded against `world_orrery_v2` synthetic fixture (not literal `coyote_star/`). TEA logged this as an explicit deviation with rationale (hermetic tests, smaller drift surface); Architect accepted at spec-check. Synthetic fixture exercises every new code path.
- AC #23 (5 new OTEL chart.render attrs): `TestOtelChartRenderAttributes` (4 tests). Center body excluded from register counts — Dev's deviation, accepted.

24 of 24 ACs covered. Round-2 spec-check fixes (textPath register inheritance + arc_belt body suppression) are correctly applied — verified via snapshot grep — but lack direct behavioral tests (gap noted, not blocking).

**Why approved despite Delivery Findings:**
1. Story scope is *visual restoration*; the visible playtest bugs ("tbrokendrift" smudge, inner-cluster collision, register confusion) are all closed.
2. 232 orbital tests pass; no regression in existing tests.
3. Architect (spec-check, two rounds) accepted the implementation after Dev applied two narrow fixes. The deviations that remain are documented and rationalized.
4. The drill-in `orbit_outermost` resolution oddity is real but narrow — affects the engraved_label decoration, not the core orrery render. Drill-in is the secondary view, not the primary chart frame the story restores.
5. Pre-existing 45 server-test failures in unrelated subsystems (dice_throw, session_handler, opening_turn, culture_context, etc.) are confirmed not caused by 45-42 — root cause in `session_helpers.py:247`, completely outside this diff.
6. Pydantic register-shadows-BaseModel warning is cosmetic, project-wide, and pre-existing in two other classes. No fix needed in this story.

**Handoff:** To SM for finish-story. PR base branches:
- `sidequest-server` → `develop`
- `sidequest-content` → `develop`

### Delivery Findings — Reviewer

- **Improvement** (non-blocking): At non-root scopes, `curve_along: orbit_outermost` resolves to the outermost direct child of the drilled-into body, producing a textPath that wraps a moon's orbit. Verified in the recorded `orrery_v2_drill_in_giant.svg` snapshot — `<textPath>— the Outer Drift —</textPath>` wraps `moon_hidden`'s tiny orbit. For coyote_star, drill-in to red_prospect would render Last Drift's textPath around The Horn's moon-band ring. Visually nonsensical at drill-in; doesn't affect root-scope which is the primary view. Recommend follow-up: either restrict `orbit_outermost` to root scope only (raise `_CurveScopeMismatch` at non-root, ~3 LOC fix in `_resolve_curve_along`), or add a `scope: Literal["any", "root"]` field to Annotation so chart authors can opt in. Affects `sidequest-server/sidequest/orbital/render.py:469-507`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The two round-2 fixes from Architect spec-check (textPath inherits body's `effective_label_register`; arc_belt body label suppressed when chart.yaml has matching engraved_label) are covered only by snapshot byte-comparison, not by behavioral assertions. A future maintainer who re-rolls the snapshot or refactors `_engraved_label_textpath` could pass the snapshot tests by accident. Recommend two ~10-LOC tests: (a) `test_engraved_label_textpath_inherits_body_label_register` — assert font-family of textPath when curve_along resolves to a body with `label_register=prose` is VT323. (b) `test_arc_belt_body_label_suppressed_when_engraved_label_matches` — assert body's radial-out label is absent from SVG when chart.yaml has matching engraved_label. Affects `sidequest-server/tests/orbital/test_render_orrery_v2.py`. *Found by Reviewer during code review.*