---
story_id: "71-2"
jira_key: null
epic: "71"
workflow: "trivial"
---
# Story 71-2: Orrery ring label — apply ADR-094 upright-flip on far-arc tangent labels

## Story Details
- **ID:** 71-2
- **Jira Key:** None (personal project)
- **Workflow:** trivial
- **Repository:** sidequest-server (AUTHORITATIVE — orrery render is server-side `orbital/render.py::_engraved_label_textpath`; the UI's MapWidget only injects the SVG). epic-71.yaml records `sidequest-ui` but `pf sprint story update` has no `--repos` flag and manual YAML edits are disallowed — so this session is the authoritative repo of record. Branch + PR live in sidequest-server.
- **Branch:** feat/71-2-orrery-ring-label-adr094-upright-flip
- **Story Type:** Bug
- **Points:** 2
- **Priority:** p3

## Problem Statement

The Orrery (orbital/space-scene visualization) renders ring labels using SVG textPath elements that wrap around elliptical orbit paths. Per ADR-094 "Orrery Label Placement — Three-Strategy Taxonomy," the `textpath` strategy wraps label text along curves.

**Bug:** Tangent labels on the FAR arc (bottom half) of a ring render upside-down. The SVG textPath naturally follows the path direction clockwise, meaning text on the bottom of a ring ends up rotated 180° past readable orientation — literally backwards/inverted.

**Root cause:** `_engraved_label_textpath()` in `sidequest-server/sidequest/orbital/render.py` (lines 572-630) constructs the SVG textPath without applying the upright-flip correction specified in ADR-094 §4.4. When the label's midpoint falls on the far arc (roughly bearing 180° from chart center), the text needs a 180° rotation applied to the textPath element to stay readable.

## Architecture Context

### Where SVG is Rendered
- **Server:** `sidequest-server/sidequest/orbital/render.py`
  - `_engraved_label_textpath()` — creates textPath SVG element (line 572)
  - `_resolve_curve_along()` — resolves path references (line 460)
  - Paths are generated as SVG `<path>` elements, always clockwise from top
  
- **Client:** `sidequest-ui/src/components/OrbitalChart/OrbitalChartView.tsx`
  - Receives server-rendered SVG as a string
  - Injects into DOM at mount
  - Applies pan/zoom transform to viewport group
  - No post-render label manipulation currently

### Label Placement Strategies (ADR-094)
1. **textpath** — text wrapped along `curve_along` path (rings/arcs) ← **THIS IS THE BUG**
2. **radial** — text placed radially from body outward
3. **callout** — text in margin callout box with leader line

The textpath strategy is the only one where labels follow curves and can flip upside-down.

### SVG Path Direction
Per `_resolve_curve_along()` line 479-480:
> "The path starts at the top of the ring and sweeps clockwise (sweep-flag=1) so textPath letters stay upright in the player's reading direction."

This works for the upper arc (0°–180° from chart center), where clockwise travel naturally keeps text upright. But on the lower arc (180°–360°), the clockwise path direction causes text to read backwards/upside-down.

## Acceptance Criteria

1. **Identify far-arc labels:** Detect when a textPath label's position (midpoint of path per `startOffset="50%"`) falls on the far arc (bearing ~180° ± ~90°, i.e., y > 0 in the chart's coordinate system where y points down).

2. **Apply upright-flip:** Add a `rotate(180 transform-origin=center)` or equivalent SVG transform to the textPath element when the label is on the far arc. The rotation must:
   - Be applied to the `<text>` element wrapping the `<textPath>`, not the path itself
   - Use `transform-origin: center` so text rotates around its own center, not the chart center
   - Flip the text 180° so it reads top-to-bottom instead of inverted

3. **Preserve register-driven styling:** The fix must not interfere with font, weight, opacity, or letter-spacing set per the label's `register` (prose/chalk/engraved).

4. **No regressions:** All existing radial-out and callout labels remain unchanged. Only textPath labels on far-arc get the flip.

5. **Observability:** Per CLAUDE.md OTEL Observability Principle, add an OTEL span attribute to `chart.label_strategy` span (emitted per body in `_render_engraved_labels()`) to track which textPath labels received the upright-flip. New attribute:
   - `textpath_upright_flip: bool` — true if far-arc flip was applied, false otherwise

## Technical Approach

### Phase 1: Detection
In `sidequest-server/sidequest/orbital/render.py`, modify `_engraved_label_textpath()` to:
1. Accept a new parameter `needs_upright_flip: bool` (passed from caller)
2. Add logic to detect far-arc based on the resolved path's center or the bearing to the path's midpoint

The caller context (`_render_annotation()` or the label strategy dispatch) must compute:
- The bearing from chart center to the path's center (e.g., for `orbit_<body_id>` the body's bearing; for `body:<belt_id>` the belt's position)
- Check if bearing is in the "far arc" range (180° ± 90°, i.e., bearing in (90°, 270°))

### Phase 2: SVG Transform
Apply the flip in the `<text>` element:
```python
# In _engraved_label_textpath, after creating elem = svgwrite.text.Text(...):
if needs_upright_flip:
    elem["transform"] = "rotate(180)"
    elem["transform-origin"] = "center"  # May require centering calculation
```

Or use svgwrite's API:
```python
if needs_upright_flip:
    # svgwrite does not directly support transform-origin in text elements.
    # Fallback: manually set via dict.
    elem["transform"] = f"rotate(180 {anchor_x} {anchor_y})"  # if anchor point known
```

**Note:** SVG's `transform-origin` is CSS-only; SVG uses `transform` with explicit rotation center coordinates. The rotation must be relative to the text's center position.

### Phase 3: OTEL Attribution
Modify the `chart.label_strategy` span emission (in `_render_engraved_labels()` or label decision dispatch) to add:
```python
span.set_attribute("textpath_upright_flip", needs_upright_flip)
```

## Story-Specific Findings

**Repo Mismatch:** The story record lists `sidequest-ui` as the target repo, but the actual bug fix lives in `sidequest-server/sidequest/orbital/render.py`. The UI (sidequest-ui) receives the SVG from the server and does not post-process labels. This appears to be a mislabeling in the epic-71.yaml story record — the true source-of-truth repo for this fix is **sidequest-server**, not sidequest-ui.

**Recommendation:** After implementing, file a follow-up chore to correct the story record to point to the correct repo, or clarify whether client-side post-processing was intended.

## Workflow Tracking

**Workflow:** trivial (quick fix, no TDD ceremony)  
**Phase:** implement (current)  
**Phase Started:** 2026-05-28T04:37:22Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28 | 2026-05-28T04:37:22Z | 4h 37m |
| implement | 2026-05-28T04:37:22Z | - | - |

## Sm Assessment

Setup verified for peloton handoff to Dev (Major Winchester) — trivial workflow (setup → implement → review → finish), so Dev owns implement and writes the test inline. Small, well-scoped SVG-geometry fix in `orbital/render.py::_engraved_label_textpath`: far-arc (bottom-half) tangent labels render upside-down because the textPath sweeps clockwise from the top; ADR-094 specifies a 180° upright-flip so far-arc labels stay readable.

**Routing notes:**
- ⚠️ REPO CORRECTED to sidequest-server (see Story Details) — branch relocated there; the YAML's `sidequest-ui` is a record artifact the CLI can't fix. Dev works in sidequest-server; PR targets server develop.
- Read ADR-094 (docs/adr/094*) for the upright-flip spec + the three-strategy taxonomy (this is the textpath strategy only — radial/callout unaffected).
- OTEL: setup proposed an OTEL span for the flip. JUDGMENT — this is DETERMINISTIC SVG geometry, not an engine/AI decision that could be "winged," so the OTEL-lie-detector doctrine doesn't strictly apply. A watcher event here is low-value; a light debug log or reusing existing render telemetry suffices. Dev: don't gold-plate a watcher event for a pure render-geometry flip unless trivially cheap. (Reviewer: don't block on a missing OTEL span for this one — it's geometry, not a subsystem decision.)
- AC focus / trap: the flip must rotate the label around ITS OWN center (`rotate(180 cx cy)`), not the chart origin (the open Question in Delivery Findings) — and must NOT regress upper-arc labels (only far-arc/inverted-angle labels flip). Reviewer holds both as the focus checks.
- Test: a unit test on `_engraved_label_textpath` (or its caller) asserting a far-arc label gets the flip transform and an upper-arc label does not — behavioral, not pixel-diff.

Branch `feat/71-2-orrery-ring-label-adr094-upright-flip` in sidequest-server off develop (includes 71-5's #485). Clear to hand to Dev.

## Dev Implement Plan (pre-handoff, no code written yet — fresh Dev picks up here)

Dev investigated then stopped at a clean boundary (context limit). Build to this:

**Fix locus:**
- `orbital/render.py::_engraved_label_textpath` (line 565) builds `<text>`+`<textPath>` — no path geometry today.
- Caller `_render_annotation` (1923): `_engraved_label_textpath(annot.text, path_id=path_id, register=register)`.
- `_resolve_curve_along` (460) returns `(path_id, path_d, resolved_body_id, circumference_px)` — geometry source.
- Span: `emit_chart_label_strategy(...)` at 1813 (from `orbital/label_strategy.py`) — AC5 attribute goes here.

**Steps:**
1. **Far-arc detection (caller side):** compute the resolved body's bearing from chart center (or path-midpoint at startOffset 50%); far arc = bearing ∈ (90°,270°), i.e. label-midpoint y>0 (SVG y-down). Pass `needs_upright_flip: bool` + label-midpoint center `(cx, cy)` into `_engraved_label_textpath`.
2. **TRAP #1 — rotate around the label's OWN center, EXPLICIT coords:** `elem["transform"] = f"rotate(180 {cx} {cy})"` on the `<text>`. Do NOT use `rotate(180)` + `transform-origin:center` (CSS-only; no effect on SVG `<text>`). The session's earlier Technical-Approach `transform-origin` suggestion is WRONG — use explicit `rotate(180 cx cy)`. **OPEN ITEM to resolve at implement:** exact source of `(cx,cy)` — parse the 50%-point from `path_d`, OR compute from body bearing+radius (ellipse top = path start, 50% offset ≈ bottom). Read the path-generation to pick the cleaner source.
3. **TRAP #2 — no upper-arc regression:** flip strictly gated on the far-arc test; upper-arc + radial (`_emit_radial_label`) + callout untouched.
4. **AC5 OTEL:** add `textpath_upright_flip: bool` to the EXISTING `chart.label_strategy` span via `emit_chart_label_strategy` (one kwarg) — NOT a separate watcher event.
5. **Inline unit test:** far-arc label → `<text>` carries `rotate(180 cx cy)` (assert transform present + center ≠ chart origin); upper-arc → no transform. Behavioral, not pixel-diff.
6. **Gates (scoped):** ruff on changed files; pyright prod delta; run new test + relevant orbital tests with exact commands.

## Delivery Findings

**Gap:** Repo assignment mismatch between story record and actual implementation location.
- **Type:** Gap
- **Urgency:** non-blocking
- **Description:** Story record says "sidequest-ui" but the orrery SVG rendering (and the bug) is entirely in sidequest-server. The UI only hosts/displays the server-rendered SVG.

**Question:** Upright-flip implementation detail.
- **Type:** Question
- **Urgency:** non-blocking
- **Description:** SVG transform syntax — should we use `rotate(180)` or `rotate(180 cx cy)` with explicit center? Need to verify svgwrite API and test that text rotates around its own center, not the chart origin.

## Design Deviations

None yet; will be recorded as implementation progresses.

## Next Steps

1. ✅ Claim story in sprint tracking (done)
2. ✅ Create feature branch (done: `feat/71-2-orrery-ring-label-adr094-upright-flip`)
3. ⏳ Implement in sidequest-server:
   - Modify `_engraved_label_textpath()` to accept `needs_upright_flip` parameter
   - Update call sites to detect and pass far-arc condition
   - Apply SVG transform when flipping
   - Add OTEL span attribute
4. ⏳ Test:
   - Snapshot test against `coyote_star` world (canonical test world per ADR-094)
   - Verify far-arc labels are now readable (visually)
   - Verify upper-arc labels unchanged
   - Verify OTEL span emits correctly
5. ⏳ Code review + merge to develop
6. ⏳ Update epic-71.yaml to mark 71-2 done

---

**Co-Authored-By:** Claude Opus 4.7 (1M context) <noreply@anthropic.com>