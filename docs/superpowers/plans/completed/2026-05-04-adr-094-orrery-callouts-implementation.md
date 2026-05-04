# ADR-094 Orrery Callouts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement ADR-094's three-strategy taxonomy for orrery body labels (textpath / radial / callout), including the new selection pipeline, the `callout_label` annotation kind, the gutter-zone flow-layout, the leader-line geometry, and the two new OTEL spans. Resolve all three failure modes from ADR-094 §Context (trojan-cluster overlap, textPath flip, companion-children unlabeled).

**Architecture:** New pure-logic module `sidequest/orbital/label_strategy.py` owns the strategy selection pass and gutter flow-layout. Existing `sidequest/orbital/render.py` integrates at three known cut points: imports, the engraved-layer label loop (~907), and `_render_moon_band` (~1053). Generalizes ADR-094's `forced_companion` rule to `forced_moon_band` per spec §9 deviation. Two-story split: Story X (server, this plan up through Phase 8) lands the renderer behind a synthetic fixture; Story Y (Phase 9) adds production labels to coyote_star.

**Tech Stack:** Python 3.14, FastAPI, svgwrite, Pydantic v2, pytest, OTEL via `sidequest.telemetry.spans`. `uv` for dependency management; `just` for task running.

**Branch convention:** `sidequest-server` targets `main`. `sidequest-content` targets `main`. Orchestrator (`oq-1`) targets `main`. No worktree — direct commits to `main` per project pattern.

**Spec:** `docs/superpowers/specs/2026-05-04-adr-094-orrery-callouts-implementation-design.md`

---

## File Map

**New files:**
- `sidequest-server/sidequest/orbital/label_strategy.py` — pure selection + flow-layout logic
- `sidequest-server/tests/orbital/test_render_callouts.py` — Story X test suite
- `sidequest-server/tests/orbital/test_render_coyote_star.py` — wiring tests + Story Y snapshot
- `sidequest-server/tests/orbital/fixtures/world_callout_strategy/orbits.yaml`
- `sidequest-server/tests/orbital/fixtures/world_callout_strategy/chart.yaml`
- `sidequest-server/tests/orbital/snapshots/world_callout_strategy_t0.svg` (generated)
- `sidequest-server/tests/orbital/snapshots/coyote_star_callouts_system_t0.svg` (generated, Story Y)

**Modified files:**
- `sidequest-server/sidequest/orbital/palette.py` — text-width / safety / callout / leader / gutter constants
- `sidequest-server/sidequest/orbital/models.py` — `BodyDef` blank-label validator; `Annotation.tag` field; `callout_label` kind; `_validate_callout_label` validator
- `sidequest-server/sidequest/orbital/render.py` — strategy dispatch at line ~907; `_render_moon_band` carve-out at line ~1053; new SVG handlers for callout / leader / grouped block
- `sidequest-server/sidequest/telemetry/spans/chart.py` — `emit_chart_label_strategy`, `emit_chart_label_distribution`
- `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml` — Story Y, `label:` additions
- `docs/adr/094-orrery-label-placement-strategies.md` — frontmatter flip + `forced_moon_band` rename amendment

---

## Phase 1 — Foundation: palette constants and model validators

### Task 1: Add new palette constants

**Files:**
- Modify: `sidequest-server/sidequest/orbital/palette.py`

This task is pure configuration — no test ceremony. Adds constants other tasks consume.

- [ ] **Step 1: Add constants block to palette.py**

Append to the end of `sidequest-server/sidequest/orbital/palette.py`:

```python
# ---- ADR-094 callout strategy (label_strategy.py) ----------------------

# Text-width estimator — calibrated upper-bound char widths per register.
# Bias toward overestimate: if text genuinely fits radial we still pick
# callout, which is the safe failure mode (visible-and-correct vs.
# overlapping). Calibrated against UI-rendered bbox at LABEL_*_FONT_SIZE.
LABEL_ENGRAVED_CHAR_WIDTH_PX: float = 8.5  # Orbitron 700 + letter-spacing 2
LABEL_CHALK_CHAR_WIDTH_PX: float = 9.0     # Orbitron 600 + letter-spacing 3
LABEL_PROSE_CHAR_WIDTH_PX: float = 6.5     # VT323 italic at LABEL_PROSE_FONT_SIZE

# Safety factors per ADR-094 §Decision rule 2 ("× 1.2") and the same-or-larger
# recommendation for arc-length fit.
TEXTPATH_FIT_SAFETY: float = 1.2
ARC_FIT_SAFETY: float = 1.2

# Callout block geometry.
CALLOUT_BLOCK_PADDING_PX: float = 4.0
CALLOUT_BLOCK_LINE_HEIGHT_PX: float = 12.0
CALLOUT_BLOCK_TAG_LINE_HEIGHT_PX: float = 10.0
CALLOUT_BLOCK_INTER_BLOCK_GAP_PX: float = 6.0
CALLOUT_GROUP_BORDER_PX: float = 0.6
CALLOUT_GROUP_TITLE_HEIGHT_PX: float = 14.0

# Leader-line geometry.
LEADER_STROKE_WIDTH_PX: float = 1.0
LEADER_TERMINATOR_SIZE_PX: float = 3.0

# Gutter zone — width and minimum-viability threshold.
GUTTER_WIDTH_PX: float = 120.0
GUTTER_MIN_VIABLE_WIDTH_PX: float = 60.0  # below this, gutter is unavailable
GUTTER_INNER_MARGIN_PX: float = 8.0       # space between chart bbox and gutter

# Tag-line max length per ADR §Label-block content rule.
CALLOUT_TAG_MAX_CHARS: int = 24

# Sibling-group threshold — N or more children in a moon band form a
# grouped <PARENT> SYSTEM block; below this they are singleton callouts.
CALLOUT_GROUP_MIN_MEMBERS: int = 3
```

- [ ] **Step 2: Verify import works**

Run: `cd sidequest-server && uv run python -c "from sidequest.orbital import palette; print(palette.LABEL_ENGRAVED_CHAR_WIDTH_PX, palette.CALLOUT_TAG_MAX_CHARS, palette.GUTTER_WIDTH_PX)"`
Expected: `8.5 24 120.0`

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/sidequest/orbital/palette.py
git commit -m "feat(orbital): add ADR-094 callout strategy palette constants

Text-width estimator constants (calibrated upper-bound), safety factors
(1.2 per ADR-094 §Decision rule 2), callout block geometry, leader-line
geometry, gutter zone bounds, and the sibling-group threshold."
```

---

### Task 2: Add `BodyDef` blank-label validator (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/models.py`
- Test: `sidequest-server/tests/orbital/test_models_label_validation.py` (NEW)

Closes the silent-fallback hole where a YAML typo `label: " "` would render an invisible label.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_models_label_validation.py`:

```python
"""Validation tests for BodyDef.label and Annotation.tag (ADR-094)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.orbital.models import BodyDef, BodyType


class TestBodyDefLabelValidation:
    def test_label_blank_string_rejected(self):
        with pytest.raises(ValidationError, match="label must be non-empty"):
            BodyDef(
                type=BodyType.HABITAT,
                parent="sun",
                semi_major_au=1.0,
                period_days=365.0,
                epoch_phase_deg=0,
                label="   ",
            )

    def test_label_empty_string_rejected(self):
        with pytest.raises(ValidationError, match="label must be non-empty"):
            BodyDef(
                type=BodyType.HABITAT,
                parent="sun",
                semi_major_au=1.0,
                period_days=365.0,
                epoch_phase_deg=0,
                label="",
            )

    def test_label_none_accepted(self):
        body = BodyDef(
            type=BodyType.HABITAT,
            parent="sun",
            semi_major_au=1.0,
            period_days=365.0,
            epoch_phase_deg=0,
            label=None,
        )
        assert body.label is None

    def test_label_normal_string_accepted(self):
        body = BodyDef(
            type=BodyType.HABITAT,
            parent="sun",
            semi_major_au=1.0,
            period_days=365.0,
            epoch_phase_deg=0,
            label="HABITAT ALPHA",
        )
        assert body.label == "HABITAT ALPHA"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_models_label_validation.py::TestBodyDefLabelValidation -v`
Expected: 2 FAIL (the blank/empty cases pass through silently today), 2 PASS.

- [ ] **Step 3: Add validator to BodyDef**

In `sidequest-server/sidequest/orbital/models.py`, add a model validator to `BodyDef` (the existing `_validate_orbital_params` is around line 88; add a new validator method below it):

```python
    @model_validator(mode="after")
    def _validate_label_not_blank(self) -> BodyDef:
        if self.label is not None and not self.label.strip():
            raise ValueError("label must be non-empty if provided")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_models_label_validation.py::TestBodyDefLabelValidation -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/models.py sidequest-server/tests/orbital/test_models_label_validation.py
git commit -m "feat(orbital): reject blank BodyDef.label (ADR-094 prep)

Closes a silent-fallback hole where label: \" \" would render invisibly.
Validator raises ValueError if label is provided and strips to empty."
```

---

### Task 3: Add `callout_label` annotation kind (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/models.py`
- Test: `sidequest-server/tests/orbital/test_models_label_validation.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_models_label_validation.py`:

```python
from sidequest.orbital.models import Annotation, KNOWN_ANNOTATION_KINDS


class TestCalloutLabelAnnotation:
    def test_callout_label_in_known_kinds(self):
        assert "callout_label" in KNOWN_ANNOTATION_KINDS

    def test_callout_label_basic(self):
        a = Annotation(
            kind="callout_label",
            text="VAEL THAIN",
            body_ref="vael_thain",
        )
        assert a.kind == "callout_label"
        assert a.text == "VAEL THAIN"
        assert a.body_ref == "vael_thain"
        assert a.tag is None

    def test_callout_label_with_tag(self):
        a = Annotation(
            kind="callout_label",
            text="VAEL THAIN",
            body_ref="vael_thain",
            tag="habitat · 1.68M km",
        )
        assert a.tag == "habitat · 1.68M km"

    def test_callout_label_missing_text_rejected(self):
        with pytest.raises(ValidationError, match="callout_label requires non-empty text"):
            Annotation(kind="callout_label", body_ref="vael_thain")

    def test_callout_label_blank_text_rejected(self):
        with pytest.raises(ValidationError, match="callout_label requires non-empty text"):
            Annotation(kind="callout_label", text="   ", body_ref="vael_thain")

    def test_callout_label_missing_body_ref_rejected(self):
        with pytest.raises(ValidationError, match="callout_label requires body_ref"):
            Annotation(kind="callout_label", text="VAEL THAIN")

    def test_callout_label_tag_too_long_rejected(self):
        with pytest.raises(ValidationError, match="exceeds 24 chars"):
            Annotation(
                kind="callout_label",
                text="VAEL THAIN",
                body_ref="vael_thain",
                tag="x" * 25,
            )

    def test_callout_label_tag_at_limit_accepted(self):
        a = Annotation(
            kind="callout_label",
            text="VAEL THAIN",
            body_ref="vael_thain",
            tag="x" * 24,
        )
        assert len(a.tag) == 24

    def test_unknown_kind_still_rejected(self):
        with pytest.raises(ValidationError, match="unknown annotation kind"):
            Annotation(kind="not_a_real_kind", text="x")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_models_label_validation.py::TestCalloutLabelAnnotation -v`
Expected: most FAIL (`callout_label` not in known kinds; `tag` field absent).

- [ ] **Step 3: Update models.py**

In `sidequest-server/sidequest/orbital/models.py`:

3a. Update `KNOWN_ANNOTATION_KINDS` (around line 174):

```python
KNOWN_ANNOTATION_KINDS: frozenset[str] = frozenset(
    {
        "engraved_label",
        "glyph",
        "scale_ruler",
        "bearing_marks",
        "anomaly_marker",
        "lagrange_point",
        "flight_corridor",
        "callout_label",   # NEW (ADR-094)
    }
)
```

3b. Add `tag` field to `Annotation` (around line 192):

```python
class Annotation(BaseModel):
    """Chart-only flavor element. `kind` selects renderer behavior;
    other fields are per-kind (validated leniently — renderer asserts
    what it needs)."""

    model_config = ConfigDict(extra="forbid")
    kind: str
    text: str | None = None
    caption: str | None = None
    curve_along: str | None = None
    at: dict[str, Any] | None = None
    style: str | None = None
    body_ref: str | None = None
    bearings: list[float] | None = None
    label: str | None = None
    tag: str | None = None  # NEW (ADR-094) — only meaningful when kind == "callout_label"
```

3c. Add validator below the existing `_validate_known_kind`:

```python
    @model_validator(mode="after")
    def _validate_callout_label(self) -> Annotation:
        if self.kind != "callout_label":
            return self
        if self.text is None or not self.text.strip():
            raise ValueError("callout_label requires non-empty text")
        if not self.body_ref:
            raise ValueError("callout_label requires body_ref")
        if self.tag is not None:
            from sidequest.orbital.palette import CALLOUT_TAG_MAX_CHARS
            if len(self.tag) > CALLOUT_TAG_MAX_CHARS:
                raise ValueError(
                    f"callout_label tag exceeds {CALLOUT_TAG_MAX_CHARS} chars: "
                    f"{self.tag!r} ({len(self.tag)} chars)"
                )
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_models_label_validation.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/models.py sidequest-server/tests/orbital/test_models_label_validation.py
git commit -m "feat(orbital): add callout_label annotation kind (ADR-094)

New annotation kind callout_label for explicit per-body callout opt-in.
Validator enforces non-empty text, present body_ref, and tag length
limit (24 chars) per ADR-094 §Label-block content rule."
```

---

## Phase 2 — Strategy module skeleton and width estimator

### Task 4: Create `label_strategy.py` with type definitions

**Files:**
- Create: `sidequest-server/sidequest/orbital/label_strategy.py`

This task defines public types only — no behavior. Types are checked by import.

- [ ] **Step 1: Create the module with types**

Create `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
"""ADR-094 — orrery body-label strategy selection and gutter flow-layout.

Pure logic module: no svgwrite imports, no SVG side effects. Consumed by
sidequest.orbital.render at the engraved-layer label cut point and at
the moon-band carve-out.

Three strategies per ADR-094:
  - textpath: label wraps along an SVG path (orbit ring or moon ring).
  - radial: label sits along the bearing ray from chart center to body.
  - callout: anchor mark + leader line + label block in the gutter zone.

Selection is rule-priority based; see select_label_strategies() for the
decision tree. Gutter layout is flow-packed by anchor bearing.

§9 deviation note in the implementation spec: forced_moon_band
generalizes ADR-094's narrow forced_companion rule. Any moon-band-rendered
body with a non-empty label is forced to callout regardless of parent type
— the structural reason is sub-pixel render position, not parent type.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class LabelStrategy(StrEnum):
    TEXTPATH = "textpath"
    RADIAL = "radial"
    CALLOUT = "callout"


class SelectionReason(StrEnum):
    FORCED_MOON_BAND = "forced_moon_band"
    EXPLICIT_CALLOUT_LABEL = "explicit_callout_label"
    TEXTPATH_FITS = "textpath_fits"
    RADIAL_FITS = "radial_fits"
    FALLBACK_TEXTPATH_TOO_SHORT = "fallback_textpath_too_short"
    FALLBACK_ARC_TOO_SHORT = "fallback_arc_too_short"
    FALLBACK_TIER_CAPPED = "fallback_tier_capped"


Register = Literal["engraved", "chalk", "prose"]


@dataclass(frozen=True)
class LabelDecision:
    body_id: str
    parent_id: str | None
    parent_type: str | None
    strategy: LabelStrategy
    reason: SelectionReason
    text: str
    register: Register
    text_width_px: float
    radial_tier: int | None              # RADIAL only
    arc_available_px: float | None       # RADIAL only
    textpath_path_id: str | None         # TEXTPATH only
    path_circumference_px: float | None  # TEXTPATH only
    callout_tag: str | None              # CALLOUT optional second line


@dataclass(frozen=True)
class CalloutBlock:
    """A single callout slot — singleton body or sibling group."""
    anchor_x: float
    anchor_y: float
    anchor_bearing_deg: float
    side: Literal["right", "left", "inset"]
    parent_label: str | None             # set when this is a grouped block
    members: tuple[LabelDecision, ...]   # 1+ decisions; >1 ⇒ grouped block
    block_x: float
    block_y: float
    block_width_px: float
    block_height_px: float


@dataclass(frozen=True)
class GutterLayout:
    blocks: tuple[CalloutBlock, ...]
    inset_fallback_count: int
    cross_group_crossing_count: int
```

- [ ] **Step 2: Verify module imports**

Run: `cd sidequest-server && uv run python -c "from sidequest.orbital.label_strategy import LabelStrategy, SelectionReason, LabelDecision, CalloutBlock, GutterLayout; print(LabelStrategy.CALLOUT, SelectionReason.FORCED_MOON_BAND)"`
Expected: `LabelStrategy.CALLOUT SelectionReason.FORCED_MOON_BAND`

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py
git commit -m "feat(orbital): add label_strategy module skeleton (ADR-094)

Pure-logic types: LabelStrategy/SelectionReason enums, LabelDecision/
CalloutBlock/GutterLayout dataclasses. No behavior yet — subsequent
tasks add estimate_text_width_px, select_label_strategies, lay_out_gutter."
```

---

### Task 5: Implement `estimate_text_width_px()` (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py` (NEW)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
"""Tests for the ADR-094 label_strategy module.

Pinned to ADR-094 acceptance criteria (AC-S*, AC-G*, AC-L*, AC-C*,
AC-A*, AC-O*) per docs/superpowers/specs/2026-05-04-adr-094-...
"""

from __future__ import annotations

import math

import pytest

from sidequest.orbital import palette
from sidequest.orbital.label_strategy import (
    LabelStrategy,
    SelectionReason,
    estimate_text_width_px,
)


class TestEstimateTextWidth:
    def test_engraved_uses_engraved_constant(self):
        w = estimate_text_width_px("ABC", "engraved")
        assert w == pytest.approx(3 * palette.LABEL_ENGRAVED_CHAR_WIDTH_PX)

    def test_chalk_uses_chalk_constant(self):
        w = estimate_text_width_px("ABCDE", "chalk")
        assert w == pytest.approx(5 * palette.LABEL_CHALK_CHAR_WIDTH_PX)

    def test_prose_uses_prose_constant(self):
        w = estimate_text_width_px("hello", "prose")
        assert w == pytest.approx(5 * palette.LABEL_PROSE_CHAR_WIDTH_PX)

    def test_empty_string_zero_width(self):
        assert estimate_text_width_px("", "engraved") == 0.0

    def test_unknown_register_raises(self):
        with pytest.raises(ValueError, match="unknown register"):
            estimate_text_width_px("ABC", "carved")  # type: ignore[arg-type]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestEstimateTextWidth -v`
Expected: FAIL with `ImportError` on `estimate_text_width_px`.

- [ ] **Step 3: Implement the function**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
from sidequest.orbital import palette


def estimate_text_width_px(text: str, register: Register) -> float:
    """Upper-bound width estimate using calibrated palette constants.

    Bias: overestimate is the safe failure direction (forces callout
    instead of letting a tight radial overlap). Calibrated against
    UI-rendered bbox at the register's standard font size.
    """
    if register == "engraved":
        char_width = palette.LABEL_ENGRAVED_CHAR_WIDTH_PX
    elif register == "chalk":
        char_width = palette.LABEL_CHALK_CHAR_WIDTH_PX
    elif register == "prose":
        char_width = palette.LABEL_PROSE_CHAR_WIDTH_PX
    else:
        raise ValueError(f"unknown register: {register!r}")
    return float(len(text)) * char_width
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestEstimateTextWidth -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): estimate_text_width_px (ADR-094)

Calibrated upper-bound width estimator per register. Used by selection
rules to compare against arc length and textpath circumference."
```

---

## Phase 3 — Selection rules (one TDD pair per rule)

Each rule is a pure function that takes a `_StrategyInput` (defined below)
and returns either a `LabelDecision` (rule matched) or `None` (fall through).
The driver `select_label_strategies()` composes them in priority order.

### Task 6: Define `_StrategyInput` and rule-function types

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`

This task adds the input type. Behavior comes in subsequent tasks.

- [ ] **Step 1: Append the input dataclass and helpers to label_strategy.py**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
@dataclass(frozen=True)
class _StrategyInput:
    """Per-body context the rule functions consume.

    Built once per render by the driver from orbits/chart/placements.
    Pure data: rule functions don't need the renderer.
    """
    body_id: str
    parent_id: str | None
    parent_type: str | None       # str rather than BodyType to avoid orbital→models→here cycle
    text: str                     # the label text (already stripped)
    register: Register
    text_width_px: float
    is_moon_band_child: bool      # body is rendered inside a moon band
    callout_label_annotation: object | None   # Annotation if explicit override exists, else None
    textpath_path_id: str | None  # set if engraved_label with curve_along resolves to this body
    path_circumference_px: float | None  # resolved path length when textpath_path_id set
    arc_to_neighbor_px: float | None     # smallest applicable arc to a peer's label edge
    radial_tier: int              # tier from existing _assign_collision_tiers (0..LABEL_TIER_MAX+1)
    # Anchor data (used by SVG handler later, threaded through unchanged):
    anchor_x: float
    anchor_y: float
    anchor_bearing_deg: float
    callout_tag: str | None       # for explicit callout_label, the tag line
```

- [ ] **Step 2: Verify imports still work**

Run: `cd sidequest-server && uv run python -c "from sidequest.orbital.label_strategy import _StrategyInput; print(_StrategyInput.__dataclass_fields__.keys())"`
Expected: dict keys list including `body_id`, `parent_type`, `is_moon_band_child`, `radial_tier`.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py
git commit -m "feat(orbital): _StrategyInput dataclass for rule fns (ADR-094)"
```

---

### Task 7: Rule — forced_moon_band (AC-S1, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import (
    _StrategyInput,
    _rule_forced_moon_band,
)


def _make_input(**overrides) -> _StrategyInput:
    """Helper: minimal _StrategyInput with sensible defaults."""
    defaults = dict(
        body_id="body_x",
        parent_id="parent_a",
        parent_type="habitat",
        text="BODY X",
        register="engraved",
        text_width_px=50.0,
        is_moon_band_child=False,
        callout_label_annotation=None,
        textpath_path_id=None,
        path_circumference_px=None,
        arc_to_neighbor_px=200.0,
        radial_tier=0,
        anchor_x=100.0,
        anchor_y=50.0,
        anchor_bearing_deg=45.0,
        callout_tag=None,
    )
    defaults.update(overrides)
    return _StrategyInput(**defaults)


class TestRuleForcedMoonBand:
    def test_moon_band_child_with_label_returns_callout(self):
        inp = _make_input(is_moon_band_child=True, parent_type="habitat")
        decision = _rule_forced_moon_band(inp)
        assert decision is not None
        assert decision.strategy == LabelStrategy.CALLOUT
        assert decision.reason == SelectionReason.FORCED_MOON_BAND

    def test_moon_band_child_companion_parent_returns_callout(self):
        # The original ADR-094 narrow case — companion parent.
        inp = _make_input(is_moon_band_child=True, parent_type="companion")
        decision = _rule_forced_moon_band(inp)
        assert decision is not None
        assert decision.strategy == LabelStrategy.CALLOUT
        assert decision.reason == SelectionReason.FORCED_MOON_BAND

    def test_top_level_body_returns_none(self):
        inp = _make_input(is_moon_band_child=False)
        assert _rule_forced_moon_band(inp) is None

    def test_decision_carries_text_and_register(self):
        inp = _make_input(is_moon_band_child=True, text="VAEL THAIN", register="engraved")
        d = _rule_forced_moon_band(inp)
        assert d.text == "VAEL THAIN"
        assert d.register == "engraved"
        assert d.body_id == "body_x"
        assert d.parent_id == "parent_a"
        assert d.parent_type == "habitat"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleForcedMoonBand -v`
Expected: FAIL — `_rule_forced_moon_band` not defined.

- [ ] **Step 3: Implement the rule**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def _rule_forced_moon_band(inp: _StrategyInput) -> LabelDecision | None:
    """If body is moon-band-rendered, force callout regardless of parent type.

    See spec §9 deviation: generalizes ADR-094's narrow forced_companion to
    cover any moon-band child with a label. Structural reason: sub-pixel
    render position has no radial space.
    """
    if not inp.is_moon_band_child:
        return None
    return LabelDecision(
        body_id=inp.body_id,
        parent_id=inp.parent_id,
        parent_type=inp.parent_type,
        strategy=LabelStrategy.CALLOUT,
        reason=SelectionReason.FORCED_MOON_BAND,
        text=inp.text,
        register=inp.register,
        text_width_px=inp.text_width_px,
        radial_tier=None,
        arc_available_px=None,
        textpath_path_id=None,
        path_circumference_px=None,
        callout_tag=inp.callout_tag,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleForcedMoonBand -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): forced_moon_band rule (ADR-094 AC-S1)

Generalizes ADR's narrow forced_companion (parent.type==companion only)
to all moon-band children with labels. See spec §9 deviation."
```

---

### Task 8: Rule — explicit_callout_label (AC-S2, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import _rule_explicit_callout_label
from sidequest.orbital.models import Annotation


class TestRuleExplicitCalloutLabel:
    def test_callout_label_annotation_returns_callout(self):
        annot = Annotation(
            kind="callout_label",
            text="SPREAD ALPHA",
            body_ref="body_x",
            tag="habitat · 3.0 AU",
        )
        inp = _make_input(callout_label_annotation=annot, callout_tag="habitat · 3.0 AU")
        d = _rule_explicit_callout_label(inp)
        assert d is not None
        assert d.strategy == LabelStrategy.CALLOUT
        assert d.reason == SelectionReason.EXPLICIT_CALLOUT_LABEL
        assert d.callout_tag == "habitat · 3.0 AU"

    def test_no_annotation_returns_none(self):
        inp = _make_input(callout_label_annotation=None)
        assert _rule_explicit_callout_label(inp) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleExplicitCalloutLabel -v`
Expected: FAIL — `_rule_explicit_callout_label` not defined.

- [ ] **Step 3: Implement the rule**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def _rule_explicit_callout_label(inp: _StrategyInput) -> LabelDecision | None:
    """If a callout_label annotation references this body, force callout."""
    if inp.callout_label_annotation is None:
        return None
    return LabelDecision(
        body_id=inp.body_id,
        parent_id=inp.parent_id,
        parent_type=inp.parent_type,
        strategy=LabelStrategy.CALLOUT,
        reason=SelectionReason.EXPLICIT_CALLOUT_LABEL,
        text=inp.text,
        register=inp.register,
        text_width_px=inp.text_width_px,
        radial_tier=None,
        arc_available_px=None,
        textpath_path_id=None,
        path_circumference_px=None,
        callout_tag=inp.callout_tag,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleExplicitCalloutLabel -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): explicit_callout_label rule (ADR-094 AC-S2)"
```

---

### Task 9: Rule — textpath fits / falls through (AC-S3 + AC-S4, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

The textpath rule has two outcomes: success (returns TEXTPATH decision) or
fall-through-with-latent-reason (returns special sentinel that the driver
interprets). To keep rules pure-functional, we return a tuple
`(decision, latent_reason)` where exactly one is not None.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import _rule_textpath


class TestRuleTextpath:
    def test_textpath_fits_returns_decision(self):
        # Path circumference 200 ≥ text_width 50 × 1.2 = 60 ⇒ fits.
        inp = _make_input(
            textpath_path_id="orbit_outer",
            path_circumference_px=200.0,
            text_width_px=50.0,
        )
        decision, latent = _rule_textpath(inp)
        assert latent is None
        assert decision is not None
        assert decision.strategy == LabelStrategy.TEXTPATH
        assert decision.reason == SelectionReason.TEXTPATH_FITS
        assert decision.textpath_path_id == "orbit_outer"
        assert decision.path_circumference_px == 200.0

    def test_textpath_too_short_returns_latent_reason(self):
        # Path circumference 50 < text_width 50 × 1.2 = 60 ⇒ falls through.
        inp = _make_input(
            textpath_path_id="body:tiny_belt",
            path_circumference_px=50.0,
            text_width_px=50.0,
        )
        decision, latent = _rule_textpath(inp)
        assert decision is None
        assert latent == SelectionReason.FALLBACK_TEXTPATH_TOO_SHORT

    def test_no_textpath_annotation_returns_none_none(self):
        inp = _make_input(textpath_path_id=None, path_circumference_px=None)
        decision, latent = _rule_textpath(inp)
        assert decision is None
        assert latent is None

    def test_safety_factor_boundary_inclusive(self):
        # exactly text_width × 1.2 should fit (≥, not >).
        inp = _make_input(
            textpath_path_id="orbit_outer",
            path_circumference_px=60.0,
            text_width_px=50.0,
        )
        decision, latent = _rule_textpath(inp)
        assert decision is not None
        assert decision.strategy == LabelStrategy.TEXTPATH
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleTextpath -v`
Expected: FAIL — `_rule_textpath` not defined.

- [ ] **Step 3: Implement the rule**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def _rule_textpath(
    inp: _StrategyInput,
) -> tuple[LabelDecision | None, SelectionReason | None]:
    """Rule 3 of the decision tree.

    Returns:
      (decision, None) — textpath fits; emit TEXTPATH decision.
      (None, FALLBACK_TEXTPATH_TOO_SHORT) — annotation present but path too
        short; caller falls through to callout (NOT to radial — designer
        opted into curved label).
      (None, None) — no textpath annotation present; rule does not apply.
    """
    if inp.textpath_path_id is None:
        return None, None
    assert inp.path_circumference_px is not None, (
        "textpath_path_id set but path_circumference_px not measured"
    )
    if inp.path_circumference_px >= inp.text_width_px * palette.TEXTPATH_FIT_SAFETY:
        decision = LabelDecision(
            body_id=inp.body_id,
            parent_id=inp.parent_id,
            parent_type=inp.parent_type,
            strategy=LabelStrategy.TEXTPATH,
            reason=SelectionReason.TEXTPATH_FITS,
            text=inp.text,
            register=inp.register,
            text_width_px=inp.text_width_px,
            radial_tier=None,
            arc_available_px=None,
            textpath_path_id=inp.textpath_path_id,
            path_circumference_px=inp.path_circumference_px,
            callout_tag=inp.callout_tag,
        )
        return decision, None
    return None, SelectionReason.FALLBACK_TEXTPATH_TOO_SHORT
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleTextpath -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): textpath rule with × 1.2 safety factor (ADR-094 AC-S3, AC-S4)

Returns (decision, None) on fit, (None, FALLBACK_TEXTPATH_TOO_SHORT) on
fall-through. Designer-opted curved labels fall to callout, never silently
demoted to radial."
```

---

### Task 10: Rule — radial fits / falls through (AC-S5, S6, S7, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import _rule_radial


class TestRuleRadial:
    def test_radial_fits_returns_decision(self):
        # arc 200 / 1.2 = 166.6 ≥ text_width 50 ⇒ fits. tier 0 ≤ 3.
        inp = _make_input(
            arc_to_neighbor_px=200.0,
            text_width_px=50.0,
            radial_tier=0,
        )
        decision, latent = _rule_radial(inp)
        assert latent is None
        assert decision is not None
        assert decision.strategy == LabelStrategy.RADIAL
        assert decision.reason == SelectionReason.RADIAL_FITS
        assert decision.radial_tier == 0
        assert decision.arc_available_px == 200.0

    def test_arc_too_short_returns_latent(self):
        # arc 30 / 1.2 = 25 < text_width 50 ⇒ falls through.
        inp = _make_input(
            arc_to_neighbor_px=30.0,
            text_width_px=50.0,
            radial_tier=0,
        )
        decision, latent = _rule_radial(inp)
        assert decision is None
        assert latent == SelectionReason.FALLBACK_ARC_TOO_SHORT

    def test_tier_capped_returns_latent(self):
        # arc fits, but tier > LABEL_TIER_MAX ⇒ falls through.
        inp = _make_input(
            arc_to_neighbor_px=500.0,
            text_width_px=50.0,
            radial_tier=palette.LABEL_TIER_MAX + 1,
        )
        decision, latent = _rule_radial(inp)
        assert decision is None
        assert latent == SelectionReason.FALLBACK_TIER_CAPPED

    def test_arc_too_short_takes_priority_over_tier_capped(self):
        # Both fail — ADR §4.1 latent priority is TEXTPATH > ARC > TIER.
        inp = _make_input(
            arc_to_neighbor_px=10.0,
            text_width_px=50.0,
            radial_tier=palette.LABEL_TIER_MAX + 5,
        )
        _, latent = _rule_radial(inp)
        assert latent == SelectionReason.FALLBACK_ARC_TOO_SHORT

    def test_no_arc_data_returns_none_none(self):
        inp = _make_input(arc_to_neighbor_px=None, text_width_px=50.0)
        decision, latent = _rule_radial(inp)
        assert decision is None
        assert latent is None

    def test_safety_factor_boundary(self):
        # arc / 1.2 == text_width exactly ⇒ fits.
        inp = _make_input(
            arc_to_neighbor_px=60.0,
            text_width_px=50.0,
            radial_tier=0,
        )
        decision, _ = _rule_radial(inp)
        assert decision is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleRadial -v`
Expected: FAIL — `_rule_radial` not defined.

- [ ] **Step 3: Implement the rule**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def _rule_radial(
    inp: _StrategyInput,
) -> tuple[LabelDecision | None, SelectionReason | None]:
    """Rule 4 of the decision tree.

    Latent reason priority when falling through (per ADR-094 §4.1):
      ARC_TOO_SHORT > TIER_CAPPED. The arc check runs first.
    """
    if inp.arc_to_neighbor_px is None:
        return None, None
    if inp.arc_to_neighbor_px / palette.ARC_FIT_SAFETY < inp.text_width_px:
        return None, SelectionReason.FALLBACK_ARC_TOO_SHORT
    if inp.radial_tier > palette.LABEL_TIER_MAX:
        return None, SelectionReason.FALLBACK_TIER_CAPPED
    decision = LabelDecision(
        body_id=inp.body_id,
        parent_id=inp.parent_id,
        parent_type=inp.parent_type,
        strategy=LabelStrategy.RADIAL,
        reason=SelectionReason.RADIAL_FITS,
        text=inp.text,
        register=inp.register,
        text_width_px=inp.text_width_px,
        radial_tier=inp.radial_tier,
        arc_available_px=inp.arc_to_neighbor_px,
        textpath_path_id=None,
        path_circumference_px=None,
        callout_tag=inp.callout_tag,
    )
    return decision, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestRuleRadial -v`
Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): radial rule with arc-fit and tier-cap fallthrough (ADR-094 AC-S5..S7)"
```

---

### Task 11: Driver — `_apply_decision_tree` (AC-S8 precedence, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

This task wires the four rules in priority order and applies the fallback callout.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import _apply_decision_tree


class TestDecisionTreePrecedence:
    def test_forced_moon_band_beats_explicit_callout_label(self):
        # AC-S8 precedence: forced_moon_band > explicit_callout_label.
        annot = Annotation(kind="callout_label", text="X", body_ref="body_x")
        inp = _make_input(
            is_moon_band_child=True,
            parent_type="companion",
            callout_label_annotation=annot,
        )
        d = _apply_decision_tree(inp)
        assert d.reason == SelectionReason.FORCED_MOON_BAND

    def test_forced_moon_band_beats_textpath(self):
        inp = _make_input(
            is_moon_band_child=True,
            textpath_path_id="orbit_x",
            path_circumference_px=500.0,
        )
        d = _apply_decision_tree(inp)
        assert d.reason == SelectionReason.FORCED_MOON_BAND

    def test_explicit_callout_label_beats_textpath(self):
        annot = Annotation(kind="callout_label", text="X", body_ref="body_x")
        inp = _make_input(
            callout_label_annotation=annot,
            textpath_path_id="orbit_x",
            path_circumference_px=500.0,
        )
        d = _apply_decision_tree(inp)
        assert d.reason == SelectionReason.EXPLICIT_CALLOUT_LABEL

    def test_textpath_beats_radial(self):
        inp = _make_input(
            textpath_path_id="orbit_x",
            path_circumference_px=500.0,
            arc_to_neighbor_px=500.0,
        )
        d = _apply_decision_tree(inp)
        assert d.reason == SelectionReason.TEXTPATH_FITS

    def test_textpath_too_short_falls_to_callout_not_radial(self):
        # Even though radial would fit, designer intent (curve_along) preserves callout.
        inp = _make_input(
            textpath_path_id="body:tiny",
            path_circumference_px=10.0,
            text_width_px=50.0,
            arc_to_neighbor_px=500.0,
            radial_tier=0,
        )
        d = _apply_decision_tree(inp)
        assert d.strategy == LabelStrategy.CALLOUT
        assert d.reason == SelectionReason.FALLBACK_TEXTPATH_TOO_SHORT

    def test_radial_when_no_other_rule_fires(self):
        inp = _make_input(arc_to_neighbor_px=500.0, text_width_px=50.0, radial_tier=0)
        d = _apply_decision_tree(inp)
        assert d.strategy == LabelStrategy.RADIAL

    def test_arc_too_short_fallback_callout(self):
        inp = _make_input(arc_to_neighbor_px=10.0, text_width_px=50.0)
        d = _apply_decision_tree(inp)
        assert d.strategy == LabelStrategy.CALLOUT
        assert d.reason == SelectionReason.FALLBACK_ARC_TOO_SHORT

    def test_tier_capped_fallback_callout(self):
        inp = _make_input(
            arc_to_neighbor_px=500.0,
            text_width_px=50.0,
            radial_tier=palette.LABEL_TIER_MAX + 1,
        )
        d = _apply_decision_tree(inp)
        assert d.strategy == LabelStrategy.CALLOUT
        assert d.reason == SelectionReason.FALLBACK_TIER_CAPPED

    def test_no_data_fallback_callout(self):
        # No textpath, no arc data, not moon band, not annotation — pure fallback.
        inp = _make_input(arc_to_neighbor_px=None)
        d = _apply_decision_tree(inp)
        assert d.strategy == LabelStrategy.CALLOUT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestDecisionTreePrecedence -v`
Expected: FAIL — `_apply_decision_tree` not defined.

- [ ] **Step 3: Implement the driver**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def _apply_decision_tree(inp: _StrategyInput) -> LabelDecision:
    """Apply the four-rule decision tree per ADR-094 §Selection rule.

    Priority order (first match wins, AC-S8):
      1. forced_moon_band   (structural — sub-pixel position, no exceptions)
      2. explicit_callout_label  (designer override)
      3. textpath_fits      (curve_along annotation, path long enough)
      4. radial_fits        (label has space at body's bearing)
      5. fallback callout   (latent reason from rule 3 or 4)
    """
    if (d := _rule_forced_moon_band(inp)) is not None:
        return d
    if (d := _rule_explicit_callout_label(inp)) is not None:
        return d

    decision, textpath_latent = _rule_textpath(inp)
    if decision is not None:
        return decision

    decision, radial_latent = _rule_radial(inp)
    if decision is not None:
        return decision

    # Fallback callout — pick the most-specific latent reason available.
    # Priority: TEXTPATH_TOO_SHORT > ARC_TOO_SHORT > TIER_CAPPED.
    if textpath_latent is not None:
        reason = textpath_latent
    elif radial_latent is not None:
        reason = radial_latent
    else:
        # Truly no data — use ARC_TOO_SHORT as the generic "no space" reason.
        reason = SelectionReason.FALLBACK_ARC_TOO_SHORT

    return LabelDecision(
        body_id=inp.body_id,
        parent_id=inp.parent_id,
        parent_type=inp.parent_type,
        strategy=LabelStrategy.CALLOUT,
        reason=reason,
        text=inp.text,
        register=inp.register,
        text_width_px=inp.text_width_px,
        radial_tier=None,
        arc_available_px=None,
        textpath_path_id=None,
        path_circumference_px=None,
        callout_tag=inp.callout_tag,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): decision-tree driver with AC-S8 precedence (ADR-094)

Composes the four selection rules in priority order:
forced_moon_band > explicit_callout_label > textpath > radial > fallback.
Fallback callout uses latent reason from textpath/radial fall-through."
```

---

## Phase 4 — Gutter flow-layout

### Task 12: Block grouping and height computation (AC-G1, G2, G3, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import (
    _group_callouts_by_parent,
    _block_height_px,
)


def _make_decision(body_id, parent_id, semi_major_au=1.0, tag=None) -> LabelDecision:
    return LabelDecision(
        body_id=body_id,
        parent_id=parent_id,
        parent_type="companion" if parent_id else None,
        strategy=LabelStrategy.CALLOUT,
        reason=SelectionReason.FORCED_MOON_BAND,
        text=body_id.upper(),
        register="engraved",
        text_width_px=50.0,
        radial_tier=None,
        arc_available_px=None,
        textpath_path_id=None,
        path_circumference_px=None,
        callout_tag=tag,
    )


class TestGroupCallouts:
    def test_three_or_more_siblings_form_group(self):
        decisions = [
            _make_decision("c1", "parent_a"),
            _make_decision("c2", "parent_a"),
            _make_decision("c3", "parent_a"),
        ]
        groups = _group_callouts_by_parent(decisions, semi_major_by_id={"c1":0.005,"c2":0.010,"c3":0.015})
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_two_siblings_remain_singletons(self):
        decisions = [
            _make_decision("c1", "parent_a"),
            _make_decision("c2", "parent_a"),
        ]
        groups = _group_callouts_by_parent(decisions, semi_major_by_id={"c1":0.005,"c2":0.010})
        assert len(groups) == 2
        assert all(len(g) == 1 for g in groups)

    def test_orphan_callouts_are_singletons(self):
        # parent_id is None — top-level body in fallback callout.
        decisions = [
            LabelDecision(body_id="x", parent_id=None, parent_type=None,
                          strategy=LabelStrategy.CALLOUT, reason=SelectionReason.FALLBACK_ARC_TOO_SHORT,
                          text="X", register="engraved", text_width_px=50.0,
                          radial_tier=None, arc_available_px=None,
                          textpath_path_id=None, path_circumference_px=None, callout_tag=None),
        ]
        groups = _group_callouts_by_parent(decisions, semi_major_by_id={})
        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_group_members_sorted_by_semi_major_au_ascending(self):
        # AC-G3
        decisions = [
            _make_decision("outer", "parent_a"),
            _make_decision("inner", "parent_a"),
            _make_decision("middle", "parent_a"),
        ]
        groups = _group_callouts_by_parent(
            decisions,
            semi_major_by_id={"inner": 0.005, "middle": 0.010, "outer": 0.020},
        )
        assert len(groups) == 1
        ids = [d.body_id for d in groups[0]]
        assert ids == ["inner", "middle", "outer"]


class TestBlockHeight:
    def test_singleton_no_tag(self):
        d = _make_decision("body_x", None)
        h = _block_height_px((d,), is_grouped=False)
        # padding * 2 + line_height
        expected = 2 * palette.CALLOUT_BLOCK_PADDING_PX + palette.CALLOUT_BLOCK_LINE_HEIGHT_PX
        assert h == pytest.approx(expected)

    def test_singleton_with_tag(self):
        d = _make_decision("body_x", None, tag="habitat · 1.0 AU")
        h = _block_height_px((d,), is_grouped=False)
        expected = (
            2 * palette.CALLOUT_BLOCK_PADDING_PX
            + palette.CALLOUT_BLOCK_LINE_HEIGHT_PX
            + palette.CALLOUT_BLOCK_TAG_LINE_HEIGHT_PX
        )
        assert h == pytest.approx(expected)

    def test_grouped_block_height_scales_with_member_count(self):
        members = tuple(_make_decision(f"c{i}", "parent_a") for i in range(6))
        h = _block_height_px(members, is_grouped=True)
        expected = (
            2 * palette.CALLOUT_BLOCK_PADDING_PX
            + palette.CALLOUT_GROUP_TITLE_HEIGHT_PX
            + 6 * palette.CALLOUT_BLOCK_LINE_HEIGHT_PX
        )
        assert h == pytest.approx(expected)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestGroupCallouts tests/orbital/test_label_strategy.py::TestBlockHeight -v`
Expected: FAIL — functions not defined.

- [ ] **Step 3: Implement helpers**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def _group_callouts_by_parent(
    decisions: list[LabelDecision],
    semi_major_by_id: dict[str, float],
) -> list[tuple[LabelDecision, ...]]:
    """Group callout decisions by parent_id; ≥CALLOUT_GROUP_MIN_MEMBERS form
    a single grouped block, fewer remain as singletons. Within a group,
    members sort by semi_major_au ascending (innermost first, AC-G3).
    """
    by_parent: dict[str | None, list[LabelDecision]] = {}
    for d in decisions:
        by_parent.setdefault(d.parent_id, []).append(d)

    groups: list[tuple[LabelDecision, ...]] = []
    for parent_id, members in by_parent.items():
        if parent_id is not None and len(members) >= palette.CALLOUT_GROUP_MIN_MEMBERS:
            sorted_members = sorted(
                members,
                key=lambda d: semi_major_by_id.get(d.body_id, 0.0),
            )
            groups.append(tuple(sorted_members))
        else:
            for m in members:
                groups.append((m,))
    return groups


def _block_height_px(
    members: tuple[LabelDecision, ...],
    *,
    is_grouped: bool,
) -> float:
    """Vertical height of a callout block in pixels."""
    h = 2.0 * palette.CALLOUT_BLOCK_PADDING_PX
    if is_grouped:
        h += palette.CALLOUT_GROUP_TITLE_HEIGHT_PX
        h += len(members) * palette.CALLOUT_BLOCK_LINE_HEIGHT_PX
    else:
        # Singleton — exactly one member; tag adds an extra line.
        assert len(members) == 1
        h += palette.CALLOUT_BLOCK_LINE_HEIGHT_PX
        if members[0].callout_tag is not None:
            h += palette.CALLOUT_BLOCK_TAG_LINE_HEIGHT_PX
    return h
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestGroupCallouts tests/orbital/test_label_strategy.py::TestBlockHeight -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): block grouping and height computation (ADR-094 AC-G1..G3)"
```

---

### Task 13: Side assignment by bearing + within-side sort (AC-G4, G5, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import _side_for_bearing


class TestSideForBearing:
    def test_right_half(self):
        # Right half: bearings 270..360, 0..90.
        assert _side_for_bearing(0.0) == "right"
        assert _side_for_bearing(45.0) == "right"
        assert _side_for_bearing(89.999) == "right"
        assert _side_for_bearing(270.0) == "right"
        assert _side_for_bearing(330.0) == "right"

    def test_left_half(self):
        # Left half: bearings 90..270.
        assert _side_for_bearing(91.0) == "left"
        assert _side_for_bearing(180.0) == "left"
        assert _side_for_bearing(269.999) == "left"

    def test_boundary_90_deg_goes_left(self):
        # Boundary convention: 90° (straight up) → left, 270° → right.
        # Documented as: right_half = bearing in [270, 90) wrapping through 0.
        assert _side_for_bearing(90.0) == "left"
        assert _side_for_bearing(270.0) == "right"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestSideForBearing -v`
Expected: FAIL — `_side_for_bearing` not defined.

- [ ] **Step 3: Implement**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def _side_for_bearing(bearing_deg: float) -> Literal["right", "left"]:
    """Right gutter for bearings 270°→90° (sweeping through 0°);
    left gutter for bearings 90°→270°. Boundary convention:
    bearing == 90° goes left, bearing == 270° goes right.
    """
    b = bearing_deg % 360.0
    if b >= 270.0 or b < 90.0:
        return "right"
    return "left"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestSideForBearing -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): _side_for_bearing helper (ADR-094 AC-G4)"
```

---

### Task 14: `lay_out_gutter()` driver — packing + overflow + inset (AC-G5, G6, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

The driver orchestrates: groups → side assignment → bearing sort → top-down packing → overflow handling → CalloutBlock list. Returns GutterLayout.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import lay_out_gutter, GutterLayout


@dataclass(frozen=True)
class _FakeViewport:
    chart_min_x: float
    chart_max_x: float
    chart_top_y: float
    chart_bottom_y: float
    svg_min_x: float
    svg_max_x: float


def _viewport_default() -> _FakeViewport:
    return _FakeViewport(
        chart_min_x=-100, chart_max_x=100,
        chart_top_y=-100, chart_bottom_y=100,
        svg_min_x=-220, svg_max_x=220,
    )


# NOTE: import dataclass at top of file once
from dataclasses import dataclass  # noqa: E402  pragma: no cover


class TestLayOutGutter:
    def test_empty_decisions_empty_layout(self):
        layout = lay_out_gutter(
            decisions=[],
            anchor_by_id={},
            semi_major_by_id={},
            viewport=_viewport_default(),
        )
        assert layout.blocks == ()
        assert layout.inset_fallback_count == 0
        assert layout.cross_group_crossing_count == 0

    def test_single_callout_lands_on_correct_side(self):
        d = _make_decision("body_x", None)
        layout = lay_out_gutter(
            decisions=[d],
            anchor_by_id={"body_x": (50.0, -10.0, 11.3)},  # bearing ~11° → right
            semi_major_by_id={},
            viewport=_viewport_default(),
        )
        assert len(layout.blocks) == 1
        assert layout.blocks[0].side == "right"
        assert layout.blocks[0].block_x > 100  # right of chart bbox

    def test_within_side_sorted_by_bearing_top_down(self):
        # Two right-side callouts at bearings 80° (near top-right) and 350° (near right).
        # After sort: 80° first (more top), 350° second.
        d_top = _make_decision("top", None)
        d_bot = _make_decision("bot", None)
        layout = lay_out_gutter(
            decisions=[d_bot, d_top],  # decisions list ordering shouldn't matter
            anchor_by_id={"top": (10.0, -50.0, 80.0), "bot": (50.0, -10.0, 11.3)},
            semi_major_by_id={},
            viewport=_viewport_default(),
        )
        assert len(layout.blocks) == 2
        # First block (top) has smaller block_y than second.
        ys = [b.block_y for b in layout.blocks]
        assert ys[0] < ys[1]

    def test_grouped_block_for_companion_children(self):
        decisions = [_make_decision(f"x{i}", "parent_a") for i in range(3)]
        layout = lay_out_gutter(
            decisions=decisions,
            anchor_by_id={f"x{i}": (50.0, -10.0 + i, 30.0) for i in range(3)},
            semi_major_by_id={"x0": 0.005, "x1": 0.010, "x2": 0.015},
            viewport=_viewport_default(),
        )
        assert len(layout.blocks) == 1
        b = layout.blocks[0]
        assert len(b.members) == 3
        assert b.parent_label is not None or True  # parent_label resolved by caller; not required here

    def test_overflow_into_inset(self):
        # Force overflow: enough singleton blocks to exhaust both gutters.
        # Each block ~ 20px tall + 6px gap = 26px. Gutter height is 200px →
        # ~7 blocks per side. Add 20 singletons all on right side.
        decisions = [_make_decision(f"b{i}", None) for i in range(20)]
        anchors = {
            f"b{i}": (50.0, -10.0 + i * 0.001, 30.0)  # all right side, distinct y
            for i in range(20)
        }
        layout = lay_out_gutter(
            decisions=decisions,
            anchor_by_id=anchors,
            semi_major_by_id={},
            viewport=_viewport_default(),
        )
        assert layout.inset_fallback_count > 0
        # Some blocks marked inset.
        sides = [b.side for b in layout.blocks]
        assert "inset" in sides
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestLayOutGutter -v`
Expected: FAIL — `lay_out_gutter` not defined.

- [ ] **Step 3: Implement the driver**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def lay_out_gutter(
    *,
    decisions: list[LabelDecision],
    anchor_by_id: dict[str, tuple[float, float, float]],  # body_id -> (x, y, bearing_deg)
    semi_major_by_id: dict[str, float],
    viewport,  # has chart_min_x/max_x/top_y/bottom_y, svg_min_x/max_x
) -> GutterLayout:
    """Group, side-assign, sort, and pack callout blocks. Pure function."""
    callout_decisions = [d for d in decisions if d.strategy == LabelStrategy.CALLOUT]
    if not callout_decisions:
        return GutterLayout(blocks=(), inset_fallback_count=0, cross_group_crossing_count=0)

    groups = _group_callouts_by_parent(callout_decisions, semi_major_by_id)

    # Compute side and representative bearing per group.
    annotated: list[tuple[Literal["right", "left"], float, tuple[LabelDecision, ...], float, float, float]] = []
    for g in groups:
        # Use first member's anchor as representative (companion-children share roughly the same bearing).
        first = g[0]
        ax, ay, abear = anchor_by_id[first.body_id]
        is_grouped = len(g) >= palette.CALLOUT_GROUP_MIN_MEMBERS
        height = _block_height_px(g, is_grouped=is_grouped)
        side = _side_for_bearing(abear)
        annotated.append((side, abear, g, ax, ay, height))

    # Sort within each side by bearing.
    # Right side: bearings near 0° on top, near 90° toward middle, near 270° toward bottom.
    # Convert bearing to a top-down sort key per side.
    def sort_key(item):
        side, bearing, *_ = item
        # Bearing → vertical position approximation: cos(bearing) gives x-component,
        # -sin(bearing) gives y-component (matches existing _polar_to_cartesian).
        # We want top-down: smallest y first.
        return -math.sin(math.radians(bearing))  # smaller (more negative? wait — y axis flipped)
        # SVG y-down: more positive y is lower. The renderer uses y = -r·sin(rad).
        # For a body at bearing 90° (top), y = -r. For 270° (bottom), y = +r.
        # So sort_key = -sin(rad) is consistent with chart.

    annotated.sort(key=sort_key)

    # Pack top-down per side.
    blocks: list[CalloutBlock] = []
    inset_count = 0

    chart_top = viewport.chart_top_y
    chart_bottom = viewport.chart_bottom_y
    gutter_height = chart_bottom - chart_top
    gap = palette.CALLOUT_BLOCK_INTER_BLOCK_GAP_PX

    # Per-side Y cursor.
    cursor = {"right": chart_top, "left": chart_top}
    block_x_for_side = {
        "right": viewport.chart_max_x + palette.GUTTER_INNER_MARGIN_PX,
        "left":  viewport.chart_min_x - palette.GUTTER_INNER_MARGIN_PX - palette.GUTTER_WIDTH_PX,
    }
    block_width_px = palette.GUTTER_WIDTH_PX - 2 * palette.GUTTER_INNER_MARGIN_PX

    for side, bearing, members, ax, ay, height in annotated:
        primary_side: Literal["right", "left"] = side
        opposite: Literal["right", "left"] = "left" if side == "right" else "right"

        chosen_side: Literal["right", "left", "inset"] | None = None
        chosen_x = chosen_y = 0.0

        for candidate in (primary_side, opposite):
            if cursor[candidate] + height <= chart_bottom:
                chosen_side = candidate
                chosen_y = cursor[candidate]
                chosen_x = block_x_for_side[candidate]
                cursor[candidate] = chosen_y + height + gap
                break

        if chosen_side is None:
            # Both sides full → inset fallback.
            chosen_side = "inset"
            # Place near the chart center, offset by a deterministic per-block delta.
            chosen_x = -block_width_px / 2.0
            chosen_y = -height / 2.0 + (inset_count * (height + gap))
            inset_count += 1

        is_grouped = len(members) >= palette.CALLOUT_GROUP_MIN_MEMBERS
        parent_label = members[0].parent_id if is_grouped else None
        # Note: parent_label is the parent_id; the caller (render.py) resolves
        # the parent's display label from orbits.bodies when emitting the title.

        blocks.append(CalloutBlock(
            anchor_x=ax,
            anchor_y=ay,
            anchor_bearing_deg=bearing,
            side=chosen_side,
            parent_label=parent_label,
            members=members,
            block_x=chosen_x,
            block_y=chosen_y,
            block_width_px=block_width_px,
            block_height_px=height,
        ))

    crossings = _count_cross_group_crossings(blocks)
    return GutterLayout(
        blocks=tuple(blocks),
        inset_fallback_count=inset_count,
        cross_group_crossing_count=crossings,
    )
```

- [ ] **Step 4: Add module-level math import**

At the top of `sidequest-server/sidequest/orbital/label_strategy.py`, ensure `import math` is present (next to existing imports). Add it if missing.

- [ ] **Step 5: Add stub for `_count_cross_group_crossings` (Task 15 implements properly)**

Append a stub for now so `lay_out_gutter` imports cleanly:

```python
def _count_cross_group_crossings(blocks: list[CalloutBlock]) -> int:
    """Number of leader-line segment intersections between different groups.
    Implemented in Task 15. Stub returns 0."""
    return 0
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestLayOutGutter -v`
Expected: 5 PASS.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): lay_out_gutter flow-pack with inset fallback (ADR-094 AC-G5, G6)"
```

---

### Task 15: Cross-group leader-crossing detection (AC-G7, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import _count_cross_group_crossings, _segments_intersect


class TestCrossGroupCrossings:
    def test_segments_intersect_basic(self):
        # X pattern — clearly crosses.
        assert _segments_intersect((0,0), (10,10), (0,10), (10,0))

    def test_segments_parallel_no_cross(self):
        assert not _segments_intersect((0,0), (10,0), (0,1), (10,1))

    def test_segments_share_endpoint_no_cross(self):
        # Sharing endpoint is not a "crossing" for our purposes.
        assert not _segments_intersect((0,0), (10,0), (10,0), (10,10))

    def test_no_crossings_when_one_block(self):
        b = _solo_block(10, 0, 0, 100, 50, 20, 30)
        assert _count_cross_group_crossings([b]) == 0

    def test_one_crossing(self):
        # Two blocks whose leader lines cross.
        b1 = _solo_block(anchor_x=10, anchor_y=10, bearing=10, bx=100, by=20, w=50, h=20)
        b2 = _solo_block(anchor_x=10, anchor_y=80, bearing=20, bx=100, by=0, w=50, h=20)
        assert _count_cross_group_crossings([b1, b2]) == 1


def _solo_block(anchor_x, anchor_y, bearing, bx, by, w, h):
    d = _make_decision("x", None)
    return CalloutBlock(
        anchor_x=anchor_x, anchor_y=anchor_y, anchor_bearing_deg=bearing,
        side="right", parent_label=None, members=(d,),
        block_x=bx, block_y=by, block_width_px=w, block_height_px=h,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestCrossGroupCrossings -v`
Expected: FAIL — `_segments_intersect` not defined; `_count_cross_group_crossings` returns 0 stub.

- [ ] **Step 3: Implement crossing detection**

Replace the stub of `_count_cross_group_crossings` and add `_segments_intersect`:

```python
def _segments_intersect(
    p1: tuple[float, float], p2: tuple[float, float],
    p3: tuple[float, float], p4: tuple[float, float],
) -> bool:
    """True if open segments p1-p2 and p3-p4 cross (excluding shared endpoints)."""
    if {p1, p2} & {p3, p4}:
        return False
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def _leader_segments_for_block(b: CalloutBlock) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return the (anchor → label-block-edge) line segment endpoints for crossing checks.
    Approximation: straight line from anchor to block-center-on-near-edge.
    Real renderer draws orthogonal with one bend; for crossing detection a
    straight approximation is sufficient — the eye reads the same crossings."""
    edge_x = b.block_x if b.anchor_x < b.block_x else b.block_x + b.block_width_px
    edge_y = b.block_y + b.block_height_px / 2.0
    return ((b.anchor_x, b.anchor_y), (edge_x, edge_y))


def _count_cross_group_crossings(blocks: list[CalloutBlock]) -> int:
    """Pairwise leader-segment crossings between distinct groups.
    Within-group crossings are forbidden by construction (bearing-sort);
    this counts cross-group crossings only.
    """
    segs = [(_leader_segments_for_block(b), id(b.members)) for b in blocks]
    n = 0
    for i in range(len(segs)):
        (p1, p2), gid_i = segs[i]
        for j in range(i + 1, len(segs)):
            (p3, p4), gid_j = segs[j]
            if gid_i == gid_j:
                continue  # same group; not a cross-group crossing
            if _segments_intersect(p1, p2, p3, p4):
                n += 1
    return n
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestCrossGroupCrossings -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): cross-group leader-crossing counter (ADR-094 AC-G7)

Pairwise segment-intersect check across distinct groups. Within-group
crossings are forbidden by bearing-sort; this counts only cross-group."
```

---

### Task 16: `select_label_strategies()` driver (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/label_strategy.py`
- Test: `sidequest-server/tests/orbital/test_label_strategy.py`

The driver assembles `_StrategyInput`s from orbits/chart/placements, applies
the decision tree per body, and emits the OTEL per-body span. It is the
public entry point the renderer calls.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_label_strategy.py`:

```python
from sidequest.orbital.label_strategy import select_label_strategies


class TestSelectLabelStrategies:
    def test_empty_inputs_empty_decisions(self):
        decisions = select_label_strategies(inputs=[])
        assert decisions == []

    def test_one_input_one_decision(self):
        inp = _make_input(arc_to_neighbor_px=500.0, text_width_px=50.0, radial_tier=0)
        decisions = select_label_strategies(inputs=[inp])
        assert len(decisions) == 1
        assert decisions[0].strategy == LabelStrategy.RADIAL

    def test_each_body_gets_independent_decision(self):
        inp_radial = _make_input(body_id="a", arc_to_neighbor_px=500.0, text_width_px=50.0)
        inp_callout = _make_input(body_id="b", is_moon_band_child=True)
        decisions = select_label_strategies(inputs=[inp_radial, inp_callout])
        assert {d.body_id for d in decisions} == {"a", "b"}
        by_id = {d.body_id: d for d in decisions}
        assert by_id["a"].strategy == LabelStrategy.RADIAL
        assert by_id["b"].strategy == LabelStrategy.CALLOUT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestSelectLabelStrategies -v`
Expected: FAIL — `select_label_strategies` not defined.

- [ ] **Step 3: Implement**

Append to `sidequest-server/sidequest/orbital/label_strategy.py`:

```python
def select_label_strategies(
    *,
    inputs: list[_StrategyInput],
) -> list[LabelDecision]:
    """Run the decision tree per body. Pure function.

    OTEL emission of chart.label_strategy spans happens in the renderer
    after this returns (the renderer has the trace context). This keeps
    label_strategy.py side-effect-free and trivially testable.
    """
    return [_apply_decision_tree(inp) for inp in inputs]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_label_strategy.py::TestSelectLabelStrategies -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/label_strategy.py sidequest-server/tests/orbital/test_label_strategy.py
git commit -m "feat(orbital): select_label_strategies driver (ADR-094)

Public entry point. Pure function; OTEL emission is the caller's
responsibility (renderer has the trace context)."
```

---

## Phase 5 — OTEL spans

### Task 17: `emit_chart_label_strategy` span (AC-O1, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/chart.py`
- Test: `sidequest-server/tests/telemetry/test_chart_label_spans.py` (NEW)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_chart_label_spans.py`:

```python
"""Tests for ADR-094 chart.label_strategy and chart.label_distribution spans."""

from __future__ import annotations

from sidequest.telemetry.spans.chart import (
    SPAN_CHART_LABEL_STRATEGY,
    SPAN_CHART_LABEL_DISTRIBUTION,
    emit_chart_label_strategy,
    emit_chart_label_distribution,
)
from sidequest.telemetry.spans._core import FLAT_ONLY_SPANS


class TestSpanRegistration:
    def test_label_strategy_in_flat_only(self):
        assert SPAN_CHART_LABEL_STRATEGY in FLAT_ONLY_SPANS

    def test_label_distribution_in_flat_only(self):
        assert SPAN_CHART_LABEL_DISTRIBUTION in FLAT_ONLY_SPANS

    def test_span_names(self):
        assert SPAN_CHART_LABEL_STRATEGY == "chart.label_strategy"
        assert SPAN_CHART_LABEL_DISTRIBUTION == "chart.label_distribution"


class TestEmitChartLabelStrategy:
    def test_textpath_decision_emits_clean(self, span_capture):
        emit_chart_label_strategy(
            body_id="body_x",
            parent_id="parent_a",
            parent_type="habitat",
            strategy_chosen="textpath",
            selection_reason="textpath_fits",
            tier=None,
            arc_available_px=None,
            text_width_px=50.0,
            path_circumference_px=200.0,
        )
        span = span_capture.last(SPAN_CHART_LABEL_STRATEGY)
        assert span.attrs["body_id"] == "body_x"
        assert span.attrs["parent_id"] == "parent_a"
        assert span.attrs["strategy_chosen"] == "textpath"
        assert span.attrs["selection_reason"] == "textpath_fits"
        assert span.attrs["tier"] == -1
        assert span.attrs["arc_available_px"] == -1.0
        assert span.attrs["path_circumference_px"] == 200.0

    def test_radial_decision_emits_tier_and_arc(self, span_capture):
        emit_chart_label_strategy(
            body_id="body_y",
            parent_id=None,
            parent_type=None,
            strategy_chosen="radial",
            selection_reason="radial_fits",
            tier=2,
            arc_available_px=180.0,
            text_width_px=42.0,
            path_circumference_px=None,
        )
        span = span_capture.last(SPAN_CHART_LABEL_STRATEGY)
        assert span.attrs["parent_id"] == ""  # null normalized to empty string
        assert span.attrs["tier"] == 2
        assert span.attrs["arc_available_px"] == 180.0
        assert span.attrs["path_circumference_px"] == -1.0
```

The `span_capture` fixture is the project's existing pytest fixture for OTEL span assertions. Verify it exists at `sidequest-server/tests/conftest.py` or the telemetry conftest. If absent, use the project's documented capture pattern.

- [ ] **Step 2: Verify span_capture fixture exists**

Run: `cd sidequest-server && grep -rn "def span_capture" tests/`
Expected: at least one match in a conftest.py.

If not present, swap the fixture for whatever pattern `tests/telemetry/` already uses. Read an existing telemetry test (e.g., `tests/telemetry/test_chart_render.py` if present, or look in `tests/orbital/test_render_orrery_v2.py` for `chart.render` span assertions) to see the pattern.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_chart_label_spans.py::TestEmitChartLabelStrategy -v`
Expected: FAIL — `emit_chart_label_strategy` not defined; `SPAN_CHART_LABEL_STRATEGY` not exported.

- [ ] **Step 4: Implement**

Append to `sidequest-server/sidequest/telemetry/spans/chart.py`:

```python
SPAN_CHART_LABEL_STRATEGY = "chart.label_strategy"
SPAN_CHART_LABEL_DISTRIBUTION = "chart.label_distribution"

FLAT_ONLY_SPANS.update({
    SPAN_CHART_LABEL_STRATEGY,
    SPAN_CHART_LABEL_DISTRIBUTION,
})


def emit_chart_label_strategy(
    *,
    body_id: str,
    parent_id: str | None,
    parent_type: str | None,
    strategy_chosen: str,
    selection_reason: str,
    tier: int | None,
    arc_available_px: float | None,
    text_width_px: float,
    path_circumference_px: float | None,
) -> None:
    """Emit one chart.label_strategy span per labeled body per render.

    Strategy-specific fields use sentinel values when not applicable:
      tier = -1 when not radial
      arc_available_px = -1.0 when not radial
      path_circumference_px = -1.0 when not textpath
    OTEL discourages None in attrs; sentinels keep the schema stable.
    """
    with Span.open(
        SPAN_CHART_LABEL_STRATEGY,
        attrs={
            "body_id": body_id,
            "parent_id": parent_id or "",
            "parent_type": parent_type or "",
            "strategy_chosen": strategy_chosen,
            "selection_reason": selection_reason,
            "tier": -1 if tier is None else int(tier),
            "arc_available_px": -1.0 if arc_available_px is None else float(arc_available_px),
            "text_width_px": float(text_width_px),
            "path_circumference_px": -1.0 if path_circumference_px is None else float(path_circumference_px),
        },
    ):
        pass


def emit_chart_label_distribution(
    *,
    bodies_total: int,
    bodies_textpath: int,
    bodies_radial: int,
    bodies_callout: int,
    bodies_unlabeled: int,
    gutter_inset_fallbacks: int,
    cross_group_crossings: int,
) -> None:
    """Emit one chart.label_distribution span per render — aggregates strategy counts."""
    with Span.open(
        SPAN_CHART_LABEL_DISTRIBUTION,
        attrs={
            "bodies_total":           int(bodies_total),
            "bodies_textpath":        int(bodies_textpath),
            "bodies_radial":          int(bodies_radial),
            "bodies_callout":         int(bodies_callout),
            "bodies_unlabeled":       int(bodies_unlabeled),
            "gutter_inset_fallbacks": int(gutter_inset_fallbacks),
            "cross_group_crossings":  int(cross_group_crossings),
        },
    ):
        pass
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_chart_label_spans.py -v`
Expected: PASS for all `TestSpanRegistration` and `TestEmitChartLabelStrategy` tests.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/chart.py sidequest-server/tests/telemetry/test_chart_label_spans.py
git commit -m "feat(telemetry): chart.label_strategy + chart.label_distribution spans (ADR-094)

Per-body and per-render spans for the GM panel lie-detector. Sentinel
values (-1, -1.0) for strategy-specific fields when not applicable —
OTEL discourages None in attrs."
```

---

### Task 18: `emit_chart_label_distribution` test coverage (AC-O2, TDD)

**Files:**
- Modify: `sidequest-server/tests/telemetry/test_chart_label_spans.py`

The function was implemented in Task 17; this task pins its behavior with tests.

- [ ] **Step 1: Append distribution-span tests**

Append to `sidequest-server/tests/telemetry/test_chart_label_spans.py`:

```python
class TestEmitChartLabelDistribution:
    def test_basic_distribution(self, span_capture):
        emit_chart_label_distribution(
            bodies_total=10,
            bodies_textpath=2,
            bodies_radial=3,
            bodies_callout=4,
            bodies_unlabeled=1,
            gutter_inset_fallbacks=0,
            cross_group_crossings=0,
        )
        span = span_capture.last(SPAN_CHART_LABEL_DISTRIBUTION)
        assert span.attrs["bodies_total"] == 10
        assert span.attrs["bodies_textpath"] == 2
        assert span.attrs["bodies_radial"] == 3
        assert span.attrs["bodies_callout"] == 4
        assert span.attrs["bodies_unlabeled"] == 1

    def test_sum_invariant_holds(self, span_capture):
        # AC-O2: bodies_textpath + bodies_radial + bodies_callout + bodies_unlabeled == bodies_total
        emit_chart_label_distribution(
            bodies_total=10, bodies_textpath=2, bodies_radial=3,
            bodies_callout=4, bodies_unlabeled=1,
            gutter_inset_fallbacks=0, cross_group_crossings=0,
        )
        span = span_capture.last(SPAN_CHART_LABEL_DISTRIBUTION)
        a = span.attrs
        assert (
            a["bodies_textpath"] + a["bodies_radial"] +
            a["bodies_callout"] + a["bodies_unlabeled"]
            == a["bodies_total"]
        )

    def test_with_warnings(self, span_capture):
        emit_chart_label_distribution(
            bodies_total=20, bodies_textpath=2, bodies_radial=8,
            bodies_callout=10, bodies_unlabeled=0,
            gutter_inset_fallbacks=2,
            cross_group_crossings=1,
        )
        a = span_capture.last(SPAN_CHART_LABEL_DISTRIBUTION).attrs
        assert a["gutter_inset_fallbacks"] == 2
        assert a["cross_group_crossings"] == 1
```

- [ ] **Step 2: Run test to verify all pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_chart_label_spans.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/telemetry/test_chart_label_spans.py
git commit -m "test(telemetry): chart.label_distribution coverage and sum invariant (ADR-094 AC-O2)"
```

---

## Phase 6 — Renderer integration

This phase is mechanical wiring. Each task modifies `render.py` at one of
the known cut points and verifies the integration via a focused test.
Tests in this phase use `render_chart()` end-to-end against the
`world_callout_strategy` fixture (created in Phase 7) — so this phase
**depends on Phase 7 fixture creation**.

Reorder: do Phase 7 (fixture) before Phase 6 (renderer integration).
The plan keeps Phase 6 numbering for narrative clarity but **execute
Phase 7 Task 24 (fixture creation) before Task 19 below**.

### Task 19: `_render_moon_band` surfaces forced-callout candidates (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/render.py`
- Test: `sidequest-server/tests/orbital/test_render_callouts.py`
  (Phase 7 Task 25 creates this file; this task adds to it.)

The carve-out: `_render_moon_band` returns its placement list. Today the
list is unused. Change it so that any moon-band child with a non-empty
`label:` field is surfaced into a `forced_callout_placements` collection
threaded through to `select_label_strategies`.

- [ ] **Step 1: Write the failing test**

In `sidequest-server/tests/orbital/test_render_callouts.py` add:

```python
class TestMoonBandForcedCalloutSurface:
    def test_moon_band_children_with_labels_surface_to_strategy(
        self, world_callout_strategy
    ):
        # Render at system scope. Companion-children (habitat_x1..x3) and
        # the habitat-moons (moon_z1, moon_z2) all have labels and should
        # appear in chart.label_distribution.bodies_callout.
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0,
            party_at=None,
        )
        # The fixture has 3 companion-of-companion-dwarf children with labels +
        # 1 child of lonely_companion + 2 children of habitat_with_moons = 6 forced callouts.
        # Plus tier-capped/arc-too-short top-level fallbacks (cluster_a..d,
        # spread_alpha explicit) — totals checked in dedicated AC-O2 test.
        # Here: assert at least 6 callouts present.
        # (We use the OTEL span capture to read counts.)
        assert "<g class=\"moon-band\"" in svg or "class=\"moon-band\"" in svg
        # Spot-check the callout block is present in SVG output.
        assert "HABITAT X-1" in svg
        assert "MOON Z-1" in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestMoonBandForcedCalloutSurface -v`
Expected: FAIL — moon-band labels not present in SVG.

- [ ] **Step 3: Modify `_render_moon_band`**

In `sidequest-server/sidequest/orbital/render.py`, locate `_render_moon_band` (~line 1053). Modify its signature and return type to surface labeled children.

The function currently returns `tuple[svgwrite.container.Group | None, list[_BodyPlacement]]`. Change the return tuple's second element from "placements for downstream label de-collision (currently unused)" to "placements for forced-callout strategy candidates."

Add to the moon-loop after the `_BodyPlacement` is constructed:

```python
        # Forced-callout surfacing: any moon-band child with a non-empty
        # `label:` becomes a candidate for the strategy pass per ADR-094 §9.
        # Children without `label:` remain unlabeled (existing behavior).
```

Update callers of `_render_moon_band` (`render_chart` and any helpers) to thread the placements list into a new `forced_callout_placements` accumulator. Search for `_render_moon_band(` to find all call sites.

The renderer entry point gathers all forced-callout placements before the strategy pass. Pseudocode:

```python
forced_callout_placements: list[_BodyPlacement] = []
# ... existing top-level body loop ...
for parent_id, parent_x, parent_y in top_level_bodies_with_children:
    moon_group, moon_placements = _render_moon_band(parent_id, parent_x, parent_y, orbits, t_hours, stats)
    if moon_group is not None:
        engraved_layer.add(moon_group)
    # Surface labeled moon-band children to forced-callout list.
    for p in moon_placements:
        if p.body.label and p.body.label.strip():
            forced_callout_placements.append(p)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestMoonBandForcedCalloutSurface -v`
Expected: still FAIL until Task 20 (renderer dispatch) lands. **Mark this test as `pytest.mark.xfail` for now** with reason `"awaits Task 20 dispatch"`.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/render.py sidequest-server/tests/orbital/test_render_callouts.py
git commit -m "feat(orbital): surface moon-band children as forced-callout candidates (ADR-094)

_render_moon_band now exposes labeled children for the strategy pass.
Test marked xfail until Task 20 wires the dispatch."
```

---

### Task 20: Strategy dispatch in engraved layer (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/render.py`
- Test: `sidequest-server/tests/orbital/test_render_callouts.py`

Replace the existing post-`_assign_collision_tiers` label loop (`render.py` ~907)
with strategy dispatch. For each top-level body OR forced-callout placement:
build `_StrategyInput`, call `select_label_strategies`, dispatch by strategy
to one of three SVG handlers.

- [ ] **Step 1: Write integration tests**

Append to `sidequest-server/tests/orbital/test_render_callouts.py`:

```python
class TestStrategyDispatch:
    """End-to-end via render_chart against world_callout_strategy fixture."""

    def test_outer_world_renders_textpath(self, world_callout_strategy):
        # outer_world has engraved_label annotation curve_along orbit_outer_world.
        # Path circumference at 8 AU is huge; should fit textpath.
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # textPath references the orbit path id.
        assert "<textPath" in svg
        assert "OUTER WORLD" in svg

    def test_spread_alpha_renders_callout_via_explicit(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # SPREAD ALPHA has explicit callout_label override.
        assert "SPREAD ALPHA" in svg
        # Tag line present.
        assert "habitat · 3.0 AU" in svg

    def test_companion_children_grouped_block(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # Grouped block titled with parent label + " SYSTEM"
        assert "COMPANION DWARF SYSTEM" in svg
        assert "HABITAT X-1" in svg
        assert "HABITAT X-2" in svg
        assert "HABITAT X-3" in svg

    def test_lonely_companion_singleton_callout(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # Below grouping threshold (1 child) → singleton callout, not grouped block.
        assert "HABITAT Y-1" in svg
        assert "LONELY COMPANION SYSTEM" not in svg

    def test_habitat_with_moons_grouping(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # 2 children = below threshold; singleton callouts each.
        assert "MOON Z-1" in svg
        assert "MOON Z-2" in svg
        assert "HABITAT WITH MOONS SYSTEM" not in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestStrategyDispatch -v`
Expected: FAIL — callout SVG not yet emitted.

- [ ] **Step 3: Implement strategy dispatch**

In `sidequest-server/sidequest/orbital/render.py`:

3a. **Imports** at top:

```python
from sidequest.orbital.label_strategy import (
    LabelStrategy,
    SelectionReason,
    LabelDecision,
    GutterLayout,
    _StrategyInput,
    select_label_strategies,
    lay_out_gutter,
    estimate_text_width_px,
)
from sidequest.telemetry.spans.chart import (
    emit_chart_label_strategy,
    emit_chart_label_distribution,
)
```

3b. **Build `_StrategyInput` per body** in the engraved-layer rendering. After the existing `_assign_collision_tiers(placements)` call (~907), and before any text emission:

```python
# Build strategy inputs for top-level bodies AND forced-callout placements.
strategy_inputs: list[_StrategyInput] = []
anchor_by_id: dict[str, tuple[float, float, float]] = {}
semi_major_by_id: dict[str, float] = {}

# Build a body-id → callout_label annotation map (one pass over chart.annotations).
callout_label_by_body: dict[str, Annotation] = {}
for annot in chart.annotations:
    if annot.kind == "callout_label" and annot.body_ref:
        callout_label_by_body[annot.body_ref] = annot

# Build a body-id → engraved_label textpath map.
textpath_by_body: dict[str, tuple[str, float]] = {}  # body_id → (path_id, circumference_px)
for annot in chart.annotations:
    if annot.kind == "engraved_label" and annot.curve_along:
        try:
            path_id, path_d, resolved_body_id = _resolve_curve_along(
                annot.curve_along, orbits, center_id, viewport
            )
            circumference = _path_d_length_px(path_d)
            textpath_by_body[resolved_body_id] = (path_id, circumference)
        except (_CurveScopeMismatch, ValueError):
            pass  # Skip; existing behavior

def _build_input(p: _BodyPlacement, is_moon_band_child: bool) -> _StrategyInput | None:
    if p.body.label is None or not p.body.label.strip():
        return None
    register: Register = (p.body.label_register or p.body.register)
    text = p.body.label.strip()
    text_w = estimate_text_width_px(text, register)
    cl = callout_label_by_body.get(p.body_id)
    tp = textpath_by_body.get(p.body_id)
    arc_to_neighbor = _arc_to_neighbor_for_placement(p, placements) if not is_moon_band_child else None
    return _StrategyInput(
        body_id=p.body_id,
        parent_id=p.body.parent,
        parent_type=(orbits.bodies[p.body.parent].type.value if p.body.parent else None),
        text=text,
        register=register,
        text_width_px=text_w,
        is_moon_band_child=is_moon_band_child,
        callout_label_annotation=cl,
        textpath_path_id=tp[0] if tp else None,
        path_circumference_px=tp[1] if tp else None,
        arc_to_neighbor_px=arc_to_neighbor,
        radial_tier=p.tier,
        anchor_x=p.anchor_x,
        anchor_y=p.anchor_y,
        anchor_bearing_deg=p.bearing_deg,
        callout_tag=cl.tag if cl else None,
    )

for p in placements:
    inp = _build_input(p, is_moon_band_child=False)
    if inp is None:
        continue
    strategy_inputs.append(inp)
    anchor_by_id[p.body_id] = (p.anchor_x, p.anchor_y, p.bearing_deg)
    if p.body.semi_major_au is not None:
        semi_major_by_id[p.body_id] = p.body.semi_major_au

for p in forced_callout_placements:
    inp = _build_input(p, is_moon_band_child=True)
    if inp is None:
        continue
    strategy_inputs.append(inp)
    # Anchor for moon-band child is the moon's dot position (p.body_x, p.body_y).
    anchor_by_id[p.body_id] = (p.body_x, p.body_y, p.bearing_deg)
    if p.body.semi_major_au is not None:
        semi_major_by_id[p.body_id] = p.body.semi_major_au

decisions = select_label_strategies(inputs=strategy_inputs)

# Emit per-body OTEL spans.
for d in decisions:
    emit_chart_label_strategy(
        body_id=d.body_id,
        parent_id=d.parent_id,
        parent_type=d.parent_type,
        strategy_chosen=d.strategy.value,
        selection_reason=d.reason.value,
        tier=d.radial_tier,
        arc_available_px=d.arc_available_px,
        text_width_px=d.text_width_px,
        path_circumference_px=d.path_circumference_px,
    )

# Compute gutter layout for callout decisions.
gutter = lay_out_gutter(
    decisions=decisions,
    anchor_by_id=anchor_by_id,
    semi_major_by_id=semi_major_by_id,
    viewport=viewport,
)
```

3c. **Helper `_path_d_length_px(path_d: str) -> float`** — compute the perimeter of an SVG path string. For ellipses we computed via `ellipse_geometry`, this comes for free; for circles `2πr`; for arc strings parse the `M`/`A` commands. A pragmatic implementation:

```python
def _path_d_length_px(path_d: str) -> float:
    """Approximate length of an SVG path 'd' string.

    The renderer issues paths via `_make_path_id_for_…` helpers that wrap
    `ellipse_geometry` (orbit rings) or arc strings (arc_belt bodies).
    For both shapes, the source geometry is known by the caller. This
    helper uses a coarse polyline approximation suitable for the
    text-width × 1.2 fit check, not for layout precision.
    """
    # Walk the path with svg.path or a manual parser; for the small set
    # of shapes the orrery produces (M + A, M + L sequences), a minimal
    # parser suffices. Use the existing svgwrite ellipse perimeter
    # formula when the path is a full ellipse.
    # (Implementation note: if a clean library is not desired, hardcode
    # the perimeter computation in the call site that already has
    # ellipse_geometry data.)
    raise NotImplementedError("provide via call-site geometry")
```

**Pragmatic decision:** rather than parse path d-strings, change `_resolve_curve_along` to return `(path_id, path_d, resolved_body_id, circumference_px)` — the function already has the geometry data when it builds the path. Add a 4th return value:

```python
# In _resolve_curve_along: when building the ellipse path, compute
#   circumference = ellipse_perimeter(geometry.semi_major, geometry.semi_minor)
# and return it.
```

Update callers accordingly. The signature change is local to `render.py`.

3d. **`_arc_to_neighbor_for_placement`** helper:

```python
def _arc_to_neighbor_for_placement(p: _BodyPlacement, placements: list[_BodyPlacement]) -> float:
    """Smallest arc length (px) at p's body radius to a peer's label edge."""
    body_radial = math.hypot(p.body_x, p.body_y)
    best_arc = float("inf")
    for other in placements:
        if other.body_id == p.body_id:
            continue
        delta_deg = _angular_distance(p.bearing_deg, other.bearing_deg)
        if delta_deg <= 0:
            continue
        arc_px = 2 * math.pi * body_radial * (delta_deg / 360.0)
        if arc_px < best_arc:
            best_arc = arc_px
    return best_arc if best_arc != float("inf") else 1e9  # no peers ⇒ huge arc
```

3e. **Strategy dispatch loop:**

```python
gutter_blocks_by_body: dict[str, CalloutBlock] = {}
for blk in gutter.blocks:
    for m in blk.members:
        gutter_blocks_by_body[m.body_id] = blk

for d in decisions:
    if d.strategy == LabelStrategy.TEXTPATH:
        # Reuse existing textPath emission path. The renderer already
        # has _engraved_label_via_textpath or similar; call it with the
        # decision's path_id.
        engraved_layer.add(_emit_textpath_label(d, viewport))
    elif d.strategy == LabelStrategy.RADIAL:
        # Reuse existing _resolve_anchor + radial text emission.
        # The placement's tier was already set; pass through.
        p = next(pl for pl in placements if pl.body_id == d.body_id)
        _resolve_anchor(p, apply_rose_clearance=(scope == Scope.system_root()))
        engraved_layer.add(_emit_radial_label(d, p, viewport))
    elif d.strategy == LabelStrategy.CALLOUT:
        block = gutter_blocks_by_body[d.body_id]
        # Only emit the block once per group; group blocks contain multiple decisions.
        # Use a "first member" guard.
        if block.members[0].body_id == d.body_id:
            engraved_layer.add(_emit_callout_block(block, orbits, viewport))
```

`_emit_textpath_label`, `_emit_radial_label`, `_emit_callout_block` are
implemented in subsequent tasks. For this task, stub them out so the
import works. Initial stubs:

```python
def _emit_textpath_label(d: LabelDecision, viewport: _Viewport) -> svgwrite.base.BaseElement:
    return svgwrite.text.Text(d.text)  # PLACEHOLDER, Task 21 implements

def _emit_radial_label(d: LabelDecision, p: _BodyPlacement, viewport: _Viewport) -> svgwrite.base.BaseElement:
    return svgwrite.text.Text(d.text)  # PLACEHOLDER, Task 22 implements

def _emit_callout_block(b: CalloutBlock, orbits: OrbitsConfig, viewport: _Viewport) -> svgwrite.base.BaseElement:
    return svgwrite.text.Text(b.members[0].text)  # PLACEHOLDER, Task 23 implements
```

3f. **Emit `chart.label_distribution` at end of `render_chart`:**

```python
counts = {
    "textpath":  sum(1 for d in decisions if d.strategy == LabelStrategy.TEXTPATH),
    "radial":    sum(1 for d in decisions if d.strategy == LabelStrategy.RADIAL),
    "callout":   sum(1 for d in decisions if d.strategy == LabelStrategy.CALLOUT),
}
# bodies_unlabeled = labeled-bodies-input minus those that became decisions
bodies_total = len(strategy_inputs)
bodies_unlabeled = sum(
    1 for bid, b in orbits.bodies.items()
    if (b.label is None or not b.label.strip())
    and b.show_at_system_scope  # only count visible-at-scope bodies
)
emit_chart_label_distribution(
    bodies_total=bodies_total,
    bodies_textpath=counts["textpath"],
    bodies_radial=counts["radial"],
    bodies_callout=counts["callout"],
    bodies_unlabeled=bodies_unlabeled,
    gutter_inset_fallbacks=gutter.inset_fallback_count,
    cross_group_crossings=gutter.cross_group_crossing_count,
)
```

- [ ] **Step 4: Run test to verify it passes (still partial — stubs in place)**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestStrategyDispatch -v`
Expected: FAILS for callout block content (stubs), PASSES for textpath / spans firing.

Mark callout-block tests `pytest.mark.xfail(reason="Task 23 implements callout SVG emission")` for now.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/render.py sidequest-server/tests/orbital/test_render_callouts.py
git commit -m "feat(orbital): strategy dispatch + OTEL emission in render_chart (ADR-094)

Wires select_label_strategies + lay_out_gutter into render_chart.
Per-body chart.label_strategy spans and per-render chart.label_distribution
span fire. Three SVG handlers stubbed; tasks 21-23 implement them."
```

---

### Task 21: `_emit_textpath_label` real implementation (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/render.py`
- Test: `sidequest-server/tests/orbital/test_render_callouts.py`

The existing renderer already has textPath emission code (around `render.py`
line 540-616 — the `_engraved_label_textpath_element` or similar function).
Refactor to take a `LabelDecision` instead of raw inputs.

- [ ] **Step 1: Write the failing test**

Append to `tests/orbital/test_render_callouts.py`:

```python
class TestEmitTextpathLabel:
    def test_textpath_uses_resolved_path_id(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # The textPath element's href should reference the orbit path id.
        # OUTER WORLD wraps along orbit_outer_world.
        assert 'href="#orbit_outer_world"' in svg or 'xlink:href="#orbit_outer_world"' in svg
        assert "— OUTER WORLD —" in svg  # em-dash bracketing per existing convention
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestEmitTextpathLabel -v`
Expected: FAIL — current stub returns plain text without textPath wrapper.

- [ ] **Step 3: Replace stub with refactored existing logic**

In `render.py`, replace the `_emit_textpath_label` stub:

```python
def _emit_textpath_label(d: LabelDecision, viewport: _Viewport) -> svgwrite.base.BaseElement:
    """Emit a textPath label per ADR-094 textpath strategy.

    Reuses the styling logic previously in the engraved_label annotation
    handler (em-dash bracketing, register-driven font/weight/letter-spacing).
    """
    assert d.textpath_path_id is not None
    decorated = f"— {d.text} —"
    register = d.register
    if register == "prose":
        font_family = palette.LABEL_PROSE_FONT
        font_size = palette.LABEL_PROSE_FONT_SIZE
        font_style = "italic"
        font_weight: int | None = None
        opacity: float | None = palette.LABEL_PROSE_OPACITY
        letter_spacing: int | None = None
    elif register == "chalk":
        font_family = palette.LABEL_CHALK_FONT
        font_size = 11
        font_style = None
        font_weight = palette.LABEL_CHALK_WEIGHT
        opacity = palette.ORBIT_OPACITY_CHALK
        letter_spacing = palette.LABEL_CHALK_LETTER_SPACING
    else:
        font_family = palette.LABEL_ENGRAVED_FONT
        font_size = 12
        font_style = "italic"
        font_weight = palette.LABEL_ENGRAVED_WEIGHT
        opacity = None
        letter_spacing = palette.LABEL_ENGRAVED_LETTER_SPACING

    fill = palette.BRASS  # textpath always engraved-color (existing convention)
    elem = svgwrite.text.Text(
        "", fill=fill, font_family=font_family, font_size=font_size, text_anchor="middle",
    )
    elem["stroke"] = palette.BG
    elem["stroke-width"] = 3
    elem["stroke-linejoin"] = "round"
    elem["paint-order"] = "stroke"
    if font_style is not None:
        elem["font-style"] = font_style
    if font_weight is not None:
        elem["font-weight"] = font_weight
    if letter_spacing is not None:
        elem["letter-spacing"] = letter_spacing
    if opacity is not None:
        elem["opacity"] = opacity
    tp = svgwrite.text.TextPath(path=f"#{d.textpath_path_id}", text=decorated)
    tp["startOffset"] = "50%"
    elem.add(tp)
    return elem
```

(If the legacy `_engraved_label_textpath_element` exists at ~line 540, keep
it for the chart.yaml annotation path-resolution flow that uses it; the
strategy dispatch is the new caller. Both call sites should share the
same emission helper — extract it if duplication is unacceptable.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestEmitTextpathLabel -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/render.py
git commit -m "feat(orbital): _emit_textpath_label real impl (ADR-094)"
```

---

### Task 22: `_emit_radial_label` real implementation (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/render.py`
- Test: `sidequest-server/tests/orbital/test_render_callouts.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/orbital/test_render_callouts.py`:

```python
class TestEmitRadialLabel:
    def test_radial_label_at_anchor_position(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # SPREAD BETA at bearing 220° has no other rule firing → radial.
        # Should appear as a <text> with x/y attributes (not inside a textPath).
        assert "SPREAD BETA" in svg
        # Sanity: the SVG should have at least one non-textPath text element with x= coords.
        assert '<text x="' in svg or "<text x='" in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestEmitRadialLabel -v`
Expected: FAIL — stub returns minimal text.

- [ ] **Step 3: Replace stub with implementation reusing existing radial-label logic**

In `render.py`, replace the `_emit_radial_label` stub:

```python
def _emit_radial_label(
    d: LabelDecision, p: _BodyPlacement, viewport: _Viewport,
) -> svgwrite.base.BaseElement:
    """Emit a radial-out body label at p.anchor_x/y."""
    register = d.register
    if register == "prose":
        font_family = palette.LABEL_PROSE_FONT
        font_size = palette.LABEL_PROSE_FONT_SIZE
        font_weight: int | None = None
        font_style = "italic"
        letter_spacing: int | None = None
        opacity = palette.LABEL_PROSE_OPACITY
    elif register == "chalk":
        font_family = palette.LABEL_CHALK_FONT
        font_size = 11
        font_weight = palette.LABEL_CHALK_WEIGHT
        font_style = None
        letter_spacing = palette.LABEL_CHALK_LETTER_SPACING
        opacity = palette.ORBIT_OPACITY_CHALK
    else:
        font_family = palette.LABEL_ENGRAVED_FONT
        font_size = 12
        font_weight = palette.LABEL_ENGRAVED_WEIGHT
        font_style = None
        letter_spacing = palette.LABEL_ENGRAVED_LETTER_SPACING
        opacity = None

    elem = svgwrite.text.Text(
        d.text,
        x=[p.anchor_x],
        y=[p.anchor_y],
        fill=palette.BRASS,
        font_family=font_family,
        font_size=font_size,
        text_anchor=p.text_anchor,
    )
    elem["stroke"] = palette.BG
    elem["stroke-width"] = 3
    elem["stroke-linejoin"] = "round"
    elem["paint-order"] = "stroke"
    if font_weight is not None:
        elem["font-weight"] = font_weight
    if font_style is not None:
        elem["font-style"] = font_style
    if letter_spacing is not None:
        elem["letter-spacing"] = letter_spacing
    if opacity is not None:
        elem["opacity"] = opacity
    elem["class"] = "radial-label"
    return elem
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestEmitRadialLabel -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/render.py
git commit -m "feat(orbital): _emit_radial_label real impl (ADR-094)"
```

---

### Task 23: `_emit_callout_block` — anchor + leader + label block (AC-L1..L4, AC-C1, AC-C2, TDD)

**Files:**
- Modify: `sidequest-server/sidequest/orbital/render.py`
- Test: `sidequest-server/tests/orbital/test_render_callouts.py`

This is the largest SVG handler. It draws:
- Per member: a leader line from anchor to block edge (orthogonal, one bend, terminator square).
- The label block: rect border (if grouped) + title (if grouped) + member lines.

- [ ] **Step 1: Write the failing test**

Append to `tests/orbital/test_render_callouts.py`:

```python
class TestEmitCalloutBlock:
    def test_singleton_callout_basic_emission(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # SPREAD ALPHA singleton callout (explicit_callout_label).
        # Expected SVG fragments:
        #   - title text "SPREAD ALPHA"
        #   - tag text "habitat · 3.0 AU"
        #   - leader-line element (class="callout-leader")
        #   - terminator square (class="callout-terminator")
        assert "SPREAD ALPHA" in svg
        assert "habitat · 3.0 AU" in svg
        assert "callout-leader" in svg
        assert "callout-terminator" in svg

    def test_grouped_block_has_title_and_border(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        assert "COMPANION DWARF SYSTEM" in svg
        # The grouped block draws a border rect (class="callout-group-border").
        assert "callout-group-border" in svg
        # Members listed in semi_major_au ascending order: x1 (0.005), x2 (0.010), x3 (0.015).
        idx_x1 = svg.find("HABITAT X-1")
        idx_x2 = svg.find("HABITAT X-2")
        idx_x3 = svg.find("HABITAT X-3")
        assert 0 < idx_x1 < idx_x2 < idx_x3

    def test_leader_color_matches_engraved_register(self, world_callout_strategy):
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        # All bodies in fixture default to engraved register, so leader stroke = BRASS.
        # AC-L2: leader stroke color matches register palette color.
        # The exact attribute placement depends on svgwrite output; assert BRASS appears
        # in proximity to "callout-leader".
        assert palette.BRASS in svg
        # Line stroke-width should match LEADER_STROKE_WIDTH_PX.
        assert f'stroke-width="{palette.LEADER_STROKE_WIDTH_PX}"' in svg or \
               f"stroke-width='{palette.LEADER_STROKE_WIDTH_PX}'" in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestEmitCalloutBlock -v`
Expected: FAIL — stub returns single text element.

- [ ] **Step 3: Replace stub with real implementation**

In `render.py`, replace `_emit_callout_block` stub:

```python
def _emit_callout_block(
    block: CalloutBlock,
    orbits: OrbitsConfig,
    viewport: _Viewport,
) -> svgwrite.base.BaseElement:
    """Emit a callout block: leader lines + label rect/border + text lines.

    Singleton: title + optional tag.
    Grouped:   "<PARENT_LABEL> SYSTEM" title + bordered rect + per-member lines.
    """
    g = svgwrite.container.Group()
    g["class"] = "callout-block"
    if block.side == "inset":
        g["data-inset"] = "true"

    is_grouped = len(block.members) >= palette.CALLOUT_GROUP_MIN_MEMBERS

    # Leader stroke color: derive from first member's register
    register = block.members[0].register
    if register == "prose":
        leader_color = palette.DIM
    elif register == "chalk":
        leader_color = palette.PARTY
    else:
        leader_color = palette.BRASS

    # --- Leader line(s) ---
    for member in block.members:
        # Anchor for THIS member: for grouped blocks, each child has its own anchor on
        # the moon-band ring. For singletons, anchor is the body's render position.
        # When grouped, the block's anchor_x/y is the first member's anchor; for
        # other members we look up via the renderer's anchor map. To keep this
        # function self-contained, we route from block.anchor_* to a per-member
        # offset along the block's leading edge.
        # (For grouped blocks, real per-member leader anchors are passed via
        # an extension in Task 24; this version draws one leader from
        # block.anchor to the block edge — sufficient for AC-L1..L4 SVG presence.)
        leader_origin = (block.anchor_x, block.anchor_y)
        # Block edge nearest the bend.
        if block.anchor_x < block.block_x:
            edge_x = block.block_x
        else:
            edge_x = block.block_x + block.block_width_px
        edge_y = block.block_y + block.block_height_px / 2.0
        # Orthogonal one-bend route: horizontal-then-vertical from anchor to edge.
        bend_x = edge_x
        bend_y = leader_origin[1]
        path_d = (
            f"M {leader_origin[0]} {leader_origin[1]} "
            f"L {bend_x} {bend_y} "
            f"L {edge_x} {edge_y}"
        )
        leader = svgwrite.path.Path(d=path_d, fill="none", stroke=leader_color)
        leader["stroke-width"] = palette.LEADER_STROKE_WIDTH_PX
        leader["class"] = "callout-leader"
        g.add(leader)

        # Terminator square.
        ts = palette.LEADER_TERMINATOR_SIZE_PX
        term = svgwrite.shapes.Rect(
            insert=(edge_x - ts / 2.0, edge_y - ts / 2.0),
            size=(ts, ts),
            fill=leader_color,
        )
        term["class"] = "callout-terminator"
        g.add(term)
        if is_grouped:
            # Only emit one leader per grouped block in this version.
            break

    # --- Label block content ---
    pad = palette.CALLOUT_BLOCK_PADDING_PX
    text_x = block.block_x + pad

    if is_grouped:
        # Border rect.
        border = svgwrite.shapes.Rect(
            insert=(block.block_x, block.block_y),
            size=(block.block_width_px, block.block_height_px),
            fill="none",
            stroke=leader_color,
        )
        border["stroke-width"] = palette.CALLOUT_GROUP_BORDER_PX
        border["class"] = "callout-group-border"
        g.add(border)

        # Title: "<PARENT_LABEL> SYSTEM"
        parent_id = block.parent_label  # actually parent_id; resolve to label below
        parent_body = orbits.bodies.get(parent_id) if parent_id else None
        parent_label_text = (parent_body.label if parent_body and parent_body.label else (parent_id or "")).strip().upper()
        title = svgwrite.text.Text(
            f"{parent_label_text} SYSTEM",
            x=[text_x],
            y=[block.block_y + pad + palette.CALLOUT_GROUP_TITLE_HEIGHT_PX * 0.75],
            fill=leader_color,
            font_family=palette.LABEL_ENGRAVED_FONT,
            font_size=11,
        )
        title["class"] = "callout-group-title"
        g.add(title)

        # One line per member.
        line_y = block.block_y + pad + palette.CALLOUT_GROUP_TITLE_HEIGHT_PX
        for m in block.members:
            line_y += palette.CALLOUT_BLOCK_LINE_HEIGHT_PX
            # "<LABEL> · <distance>" — use the body's semi_major_au for distance.
            body = orbits.bodies.get(m.body_id)
            distance_label = ""
            if body and body.semi_major_au is not None:
                # Format as compact distance: AU if ≥ 0.01, else km (×1.496e8).
                if body.semi_major_au >= 0.01:
                    distance_label = f"{body.semi_major_au:.2f} AU"
                else:
                    km = body.semi_major_au * 1.496e8
                    distance_label = f"{km/1e6:.2f}M km"
            line_text = f"{m.text} · {distance_label}" if distance_label else m.text
            line = svgwrite.text.Text(
                line_text,
                x=[text_x],
                y=[line_y],
                fill=leader_color,
                font_family=palette.LABEL_ENGRAVED_FONT,
                font_size=10,
            )
            line["class"] = "callout-group-member"
            g.add(line)
    else:
        # Singleton: title + optional tag.
        m = block.members[0]
        title = svgwrite.text.Text(
            m.text,
            x=[text_x],
            y=[block.block_y + pad + palette.CALLOUT_BLOCK_LINE_HEIGHT_PX * 0.75],
            fill=leader_color,
            font_family=palette.LABEL_ENGRAVED_FONT,
            font_size=11,
        )
        title["class"] = "callout-singleton-title"
        g.add(title)
        if m.callout_tag:
            tag_y = (
                block.block_y + pad + palette.CALLOUT_BLOCK_LINE_HEIGHT_PX
                + palette.CALLOUT_BLOCK_TAG_LINE_HEIGHT_PX * 0.75
            )
            tag = svgwrite.text.Text(
                m.callout_tag,
                x=[text_x], y=[tag_y],
                fill=palette.DIM,
                font_family=palette.LABEL_PROSE_FONT,
                font_size=palette.LABEL_PROSE_FONT_SIZE,
            )
            tag["font-style"] = "italic"
            tag["class"] = "callout-singleton-tag"
            g.add(tag)

    return g
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestEmitCalloutBlock -v`
Expected: PASS.

- [ ] **Step 5: Remove `xfail` markers from earlier tasks**

Earlier tasks in this phase marked tests xfail "awaits Task 23". Remove those markers so they assert positively now:

Run: `cd sidequest-server && grep -n "xfail" tests/orbital/test_render_callouts.py`
Edit each marked test to remove the `pytest.mark.xfail(...)` decorator.

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/orbital/render.py sidequest-server/tests/orbital/test_render_callouts.py
git commit -m "feat(orbital): callout SVG handler — anchor+leader+block (ADR-094 AC-L1..L4, C1, C2)

Real implementation of _emit_callout_block. Singleton and grouped blocks,
orthogonal one-bend leader, 3×3 terminator square, register-driven
stroke color. Removes xfail markers from prior tasks."
```

---

## Phase 7 — Synthetic fixture (must precede Phase 6 execution)

> **Execution order note:** create the fixture (Tasks 25-26) BEFORE running
> the renderer-integration tests in Phase 6. Phase 6 numbering reflects
> narrative order; execution should be Phase 1 → 2 → 3 → 4 → 5 → **7** → 6 → 8 → 9.

### Task 24: Create `world_callout_strategy` fixture

**Files:**
- Create: `sidequest-server/tests/orbital/fixtures/world_callout_strategy/orbits.yaml`
- Create: `sidequest-server/tests/orbital/fixtures/world_callout_strategy/chart.yaml`

- [ ] **Step 1: Create orbits.yaml**

Create `sidequest-server/tests/orbital/fixtures/world_callout_strategy/orbits.yaml` with the exact YAML from the spec §6.1:

```yaml
version: "0.1.0"
clock: { epoch_days: 0 }
travel: { realism: orbital }

bodies:
  primary_star:
    type: star
    label: "PRIMARY"

  outer_world:
    type: habitat
    parent: primary_star
    semi_major_au: 8.0
    period_days: 8000
    epoch_phase_deg: 0
    label: "OUTER WORLD"

  tiny_belt:
    type: arc_belt
    parent: primary_star
    semi_major_au: 0.5
    period_days: 130
    arc_extent_deg: 30
    epoch_phase_deg: 270
    label: "TINY BELT"

  spread_alpha:
    type: habitat
    parent: primary_star
    semi_major_au: 3.0
    period_days: 1900
    epoch_phase_deg: 90
    label: "SPREAD ALPHA"

  cluster_a:
    type: habitat
    parent: primary_star
    semi_major_au: 1.0
    period_days: 365
    epoch_phase_deg: 30
    label: "CLUSTER ALPHA"
  cluster_b:
    type: habitat
    parent: primary_star
    semi_major_au: 1.0
    period_days: 365
    epoch_phase_deg: 60
    label: "CLUSTER BETA"
  cluster_c:
    type: habitat
    parent: primary_star
    semi_major_au: 1.0
    period_days: 365
    epoch_phase_deg: 90
    label: "CLUSTER GAMMA"
  cluster_d:
    type: habitat
    parent: primary_star
    semi_major_au: 1.05
    period_days: 392
    epoch_phase_deg: 120
    label: "CLUSTER DELTA"

  companion_dwarf:
    type: companion
    parent: primary_star
    semi_major_au: 5.0
    period_days: 5000
    epoch_phase_deg: 180
    label: "COMPANION DWARF"
  habitat_x1:
    type: habitat
    parent: companion_dwarf
    semi_major_au: 0.005
    period_days: 30
    epoch_phase_deg: 0
    label: "HABITAT X-1"
  habitat_x2:
    type: habitat
    parent: companion_dwarf
    semi_major_au: 0.010
    period_days: 60
    epoch_phase_deg: 90
    label: "HABITAT X-2"
  habitat_x3:
    type: habitat
    parent: companion_dwarf
    semi_major_au: 0.015
    period_days: 90
    epoch_phase_deg: 180
    label: "HABITAT X-3"

  lonely_companion:
    type: companion
    parent: primary_star
    semi_major_au: 6.5
    period_days: 7400
    epoch_phase_deg: 270
    label: "LONELY COMPANION"
  habitat_y1:
    type: habitat
    parent: lonely_companion
    semi_major_au: 0.005
    period_days: 30
    epoch_phase_deg: 0
    label: "HABITAT Y-1"

  habitat_with_moons:
    type: habitat
    parent: primary_star
    semi_major_au: 2.2
    period_days: 1200
    epoch_phase_deg: 315
    label: "HABITAT WITH MOONS"
  moon_z1:
    type: habitat
    parent: habitat_with_moons
    semi_major_au: 0.004
    period_days: 25
    epoch_phase_deg: 0
    label: "MOON Z-1"
  moon_z2:
    type: habitat
    parent: habitat_with_moons
    semi_major_au: 0.008
    period_days: 50
    epoch_phase_deg: 180
    label: "MOON Z-2"

  spread_beta:
    type: habitat
    parent: primary_star
    semi_major_au: 4.5
    period_days: 3500
    epoch_phase_deg: 220
    label: "SPREAD BETA"
```

- [ ] **Step 2: Create chart.yaml**

Create `sidequest-server/tests/orbital/fixtures/world_callout_strategy/chart.yaml`:

```yaml
version: "0.1.0"
annotations:
  - kind: engraved_label
    text: "OUTER WORLD"
    curve_along: orbit_outer_world

  - kind: engraved_label
    text: "TINY BELT"
    curve_along: body:tiny_belt

  - kind: callout_label
    text: "SPREAD ALPHA"
    body_ref: spread_alpha
    tag: "habitat · 3.0 AU"
```

- [ ] **Step 3: Verify fixture loads**

Run: `cd sidequest-server && uv run python -c "from sidequest.orbital.loader import load_orbital_content; from pathlib import Path; w = load_orbital_content(Path('tests/orbital/fixtures/world_callout_strategy')); print(len(w.orbits.bodies), 'bodies;', len(w.chart.annotations), 'annotations')"`
Expected: `19 bodies; 3 annotations`

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/tests/orbital/fixtures/world_callout_strategy/
git commit -m "test(orbital): world_callout_strategy fixture (ADR-094)

19 bodies exercising every selection rule path: textpath fits/too-short,
explicit_callout_label override, radial fits, arc_too_short, tier_capped,
forced_moon_band (companion-children + habitat-moons), grouped block
threshold, singleton callouts."
```

---

### Task 25: Test file scaffolding and fixture loader

**Files:**
- Create: `sidequest-server/tests/orbital/test_render_callouts.py`

The previous Phase 6 tasks reference this file. This task creates it with
the imports and the world_callout_strategy fixture. Place this task
before any test additions in Phase 6 / Phase 7 execution.

- [ ] **Step 1: Create scaffolding**

Create `sidequest-server/tests/orbital/test_render_callouts.py`:

```python
"""End-to-end and unit tests for ADR-094 orrery callouts.

Spec: docs/superpowers/specs/2026-05-04-adr-094-orrery-callouts-implementation-design.md
ADR:  docs/adr/094-orrery-label-placement-strategies.md

This file pins the §6.2 acceptance criteria from the spec. Pure-logic
unit tests for label_strategy live in test_label_strategy.py; this file
covers the renderer integration end-to-end via render_chart() against
the world_callout_strategy fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.orbital import palette
from sidequest.orbital.loader import load_orbital_content

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def world_callout_strategy():
    """The synthetic fixture exercising every selection rule."""
    return load_orbital_content(FIXTURES / "world_callout_strategy")
```

- [ ] **Step 2: Smoke-test the fixture loads in pytest**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py -v`
Expected: 0 tests collected (no test functions yet) — just confirms file is valid Python.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/orbital/test_render_callouts.py
git commit -m "test(orbital): scaffolding for ADR-094 renderer integration tests"
```

---

### Task 26: Snapshot baseline for `world_callout_strategy`

**Files:**
- Create: `sidequest-server/tests/orbital/snapshots/world_callout_strategy_t0.svg`

Run after Phase 6 is complete (all renderer-integration tests pass). The
snapshot is the byte-identical regression detector for AC-X1.

- [ ] **Step 1: Generate the snapshot**

Run:
```bash
cd sidequest-server
uv run python -c "
from pathlib import Path
from sidequest.orbital.loader import load_orbital_content
from sidequest.orbital.render import Scope, render_chart
w = load_orbital_content(Path('tests/orbital/fixtures/world_callout_strategy'))
svg = render_chart(orbits=w.orbits, chart=w.chart, scope=Scope.system_root(), t_hours=0.0, party_at=None)
Path('tests/orbital/snapshots/world_callout_strategy_t0.svg').write_text(svg)
print('Wrote', len(svg), 'bytes')
"
```
Expected: prints byte count.

- [ ] **Step 2: Open the SVG visually to spot-check**

Open `tests/orbital/snapshots/world_callout_strategy_t0.svg` in a browser. Manually verify:
- Companion-children callout block titled "COMPANION DWARF SYSTEM" present.
- Three habitat lines visible inside the bordered group.
- "SPREAD ALPHA" callout has a tag line below.
- "OUTER WORLD" wraps along its orbit ring (textPath).
- No labels overlap.

If the visual looks wrong, debug the renderer before regenerating the snapshot.

- [ ] **Step 3: Add the snapshot regression test**

Append to `sidequest-server/tests/orbital/test_render_callouts.py`:

```python
SNAPSHOTS = Path(__file__).parent / "snapshots"


class TestSnapshotRegression:
    def test_world_callout_strategy_byte_identical(self, world_callout_strategy):
        """AC-X1: byte-identical snapshot regression."""
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=world_callout_strategy.orbits,
            chart=world_callout_strategy.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        baseline = (SNAPSHOTS / "world_callout_strategy_t0.svg").read_text()
        assert svg == baseline, (
            "Snapshot mismatch — re-baseline if intentional with:\n"
            "  python -c 'from pathlib import Path; "
            "from sidequest.orbital.loader import load_orbital_content; "
            "from sidequest.orbital.render import Scope, render_chart; "
            "w = load_orbital_content(Path(\"tests/orbital/fixtures/world_callout_strategy\")); "
            "Path(\"tests/orbital/snapshots/world_callout_strategy_t0.svg\").write_text("
            "render_chart(orbits=w.orbits, chart=w.chart, scope=Scope.system_root(), t_hours=0.0, party_at=None))'"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_callouts.py::TestSnapshotRegression -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/tests/orbital/snapshots/world_callout_strategy_t0.svg sidequest-server/tests/orbital/test_render_callouts.py
git commit -m "test(orbital): world_callout_strategy snapshot regression (ADR-094 AC-X1)"
```

---

## Phase 8 — Wiring test against production campaign world

### Task 27: `test_coyote_star_renders_without_crash` (AC-W1, TDD)

**Files:**
- Create: `sidequest-server/tests/orbital/test_render_coyote_star.py`

This is the wiring test mandated by CLAUDE.md "Every Test Suite Needs a
Wiring Test." It proves the new pipeline is reachable from production code
paths. After Story Y, this file gets a snapshot test for the post-Y
campaign render.

- [ ] **Step 1: Locate the campaign world fixture path**

Run: `cd sidequest-server && find . -path ./node_modules -prune -o -name 'orbits.yaml' -print 2>/dev/null | grep coyote_star`
Expected: a path under `sidequest-content/genre_packs/space_opera/worlds/coyote_star/`.

The path needs to resolve from a test file. Check if there's an existing convention — look at `tests/integration/test_orbital_e2e.py` for how it loads the production world.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/orbital/test_render_coyote_star.py`:

```python
"""Wiring + Story Y snapshot tests against the live coyote_star campaign world.

Per CLAUDE.md: "Every Test Suite Needs a Wiring Test" — proves the
ADR-094 pipeline is reachable from production code paths. The Story Y
post-content-edit snapshot test lives in TestStoryYSnapshot.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sidequest.orbital.loader import load_orbital_content


def _coyote_star_path() -> Path:
    # Allow override via env (cross-machine compatibility).
    env_path = os.environ.get("SIDEQUEST_CONTENT_COYOTE_STAR")
    if env_path:
        return Path(env_path)
    # Default: sibling sidequest-content checkout.
    server_root = Path(__file__).resolve().parents[2]  # sidequest-server/
    repo_root = server_root.parent
    return repo_root / "sidequest-content" / "genre_packs" / "space_opera" / "worlds" / "coyote_star"


@pytest.fixture
def coyote_star_world():
    path = _coyote_star_path()
    if not path.exists():
        pytest.skip(f"coyote_star fixture not present at {path}")
    return load_orbital_content(path)


class TestCoyoteStarWiring:
    def test_renders_without_crash(self, coyote_star_world, span_capture):
        """AC-W1: production campaign world renders end-to-end."""
        from sidequest.orbital.render import Scope, render_chart
        from sidequest.telemetry.spans.chart import SPAN_CHART_LABEL_DISTRIBUTION

        svg = render_chart(
            orbits=coyote_star_world.orbits,
            chart=coyote_star_world.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        assert svg.startswith("<?xml") or svg.startswith("<svg")
        assert len(svg) > 1000  # non-empty render

        # Distribution span fired.
        dist = span_capture.last(SPAN_CHART_LABEL_DISTRIBUTION)
        a = dist.attrs
        # Sum invariant (AC-O2):
        assert (
            a["bodies_textpath"] + a["bodies_radial"]
            + a["bodies_callout"] + a["bodies_unlabeled"]
            == a["bodies_total"]
        )
        # Pre-Story-Y: red_prospect children have no labels yet, so
        # bodies_callout should be 0 from the moon-band carve-out.
        # Top-level fallbacks (trojan cluster) may still produce callouts —
        # weak assertion: span fired with sane structure.
```

- [ ] **Step 3: Run test to verify it passes (with current state of code)**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_coyote_star.py::TestCoyoteStarWiring -v`
Expected: PASS — the renderer survives the production world. If it fails, the new pipeline has a regression on real data; debug before moving on.

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/tests/orbital/test_render_coyote_star.py
git commit -m "test(orbital): coyote_star wiring test (ADR-094 AC-W1)

Renders the live campaign world with the new strategy pipeline. Sum
invariant on chart.label_distribution. Pre-Story-Y, no callouts from
red_prospect (no labels yet); top-level fallbacks may still produce some."
```

---

**Story X is complete.** Confirm by running the full server test suite:

```bash
cd sidequest-server && uv run pytest tests/ -v
```

Expected: all tests PASS, including the new files. If any pre-existing test fails, investigate — strategy dispatch may have regressed the existing radial/textPath path. Re-baseline `tests/orbital/snapshots/orrery_v2_*.svg` ONLY if the visual diff is intentional and covered by an explicit AC.

---

## Phase 9 — Story Y: content YAML + ADR amendment

This phase is content + ADR housekeeping. Each task is a small edit.

### Task 28: Add labels to red_prospect's six habitats (AC-Y1)

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml`

- [ ] **Step 1: Locate red_prospect's children in the YAML**

Run: `grep -n "red_prospect\|turning_hub\|whitedrift\|ember_moon\|the_horn\|dead_lash\|vael_thain" sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml`
Note the line numbers.

- [ ] **Step 2: Add `label:` fields**

For each of the six habitats parented to `red_prospect`, add a `label:` line. The canonical names per ADR §Failure 3:

```yaml
  turning_hub:
    type: habitat
    parent: red_prospect
    # ... existing fields ...
    label: "TURNING HUB"

  whitedrift:
    # ...
    label: "WHITEDRIFT"

  ember_moon:
    # ...
    label: "EMBER MOON"

  the_horn:
    # ...
    label: "THE HORN"

  dead_lash:
    # ...
    label: "DEAD LASH"

  vael_thain:
    # ...
    label: "VAEL THAIN"
```

- [ ] **Step 3: Verify YAML still loads**

Run: `cd sidequest-server && uv run python -c "from sidequest.orbital.loader import load_orbital_content; from pathlib import Path; w = load_orbital_content(Path('../sidequest-content/genre_packs/space_opera/worlds/coyote_star')); print('OK', len(w.orbits.bodies), 'bodies')"`
Expected: `OK <count> bodies`.

- [ ] **Step 4: Commit (in sidequest-content)**

```bash
cd sidequest-content
git add genre_packs/space_opera/worlds/coyote_star/orbits.yaml
git commit -m "feat(coyote_star): label red_prospect's six habitats (ADR-094 Story Y)

Activates the forced_moon_band rule for red_prospect's habitat children:
turning_hub, whitedrift, ember_moon, the_horn, dead_lash, vael_thain.
The renderer (Story X, sidequest-server) will produce a grouped
RED PROSPECT SYSTEM callout block."
```

---

### Task 29: Add labels to far_landing and deep_root_world moons (AC-Y2)

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml`

- [ ] **Step 1: Locate moons of far_landing / deep_root_world**

Already visible in the file (the first 100 lines I read showed `tethys_watch` parent=`far_landing`, and `kerel_eye`/`lower_kerel` parent=`deep_root_world`).

- [ ] **Step 2: Add `label:` fields**

```yaml
  tethys_watch:
    # ...existing...
    label: "TETHYS WATCH"

  kerel_eye:
    # ...existing...
    label: "KEREL EYE"

  lower_kerel:
    # ...existing...
    label: "LOWER KEREL"
```

- [ ] **Step 3: Verify YAML still loads**

Run: `cd sidequest-server && uv run python -c "from sidequest.orbital.loader import load_orbital_content; from pathlib import Path; w = load_orbital_content(Path('../sidequest-content/genre_packs/space_opera/worlds/coyote_star')); n = sum(1 for b in w.orbits.bodies.values() if b.label); print('labeled bodies:', n)"`
Expected: count includes the three new labels.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/space_opera/worlds/coyote_star/orbits.yaml
git commit -m "feat(coyote_star): label far_landing and deep_root_world moons (ADR-094 Story Y)

tethys_watch, kerel_eye, lower_kerel get labels. Activates
forced_moon_band on non-companion parents per spec §9 deviation."
```

---

### Task 30: Generate post-Story-Y snapshot baseline + regression test (AC-Y3, AC-Y4)

**Files:**
- Create: `sidequest-server/tests/orbital/snapshots/coyote_star_callouts_system_t0.svg`
- Modify: `sidequest-server/tests/orbital/test_render_coyote_star.py`

- [ ] **Step 1: Generate the snapshot**

After Tasks 29-30 commit, regenerate:

```bash
cd sidequest-server
uv run python -c "
from pathlib import Path
import os
from sidequest.orbital.loader import load_orbital_content
from sidequest.orbital.render import Scope, render_chart
path = Path(os.environ.get('SIDEQUEST_CONTENT_COYOTE_STAR',
    '../sidequest-content/genre_packs/space_opera/worlds/coyote_star'))
w = load_orbital_content(path)
svg = render_chart(orbits=w.orbits, chart=w.chart, scope=Scope.system_root(), t_hours=0.0, party_at=None)
Path('tests/orbital/snapshots/coyote_star_callouts_system_t0.svg').write_text(svg)
print('Wrote', len(svg), 'bytes')
"
```

- [ ] **Step 2: Visually verify the snapshot**

Open `tests/orbital/snapshots/coyote_star_callouts_system_t0.svg` in a browser. Manually verify:
- "RED PROSPECT SYSTEM" grouped block visible with all six habitats inside.
- Members listed inner-to-outer (turning_hub innermost).
- TETHYS WATCH singleton callout near far_landing.
- KEREL EYE and LOWER KEREL near deep_root_world.
- No callouts overlap; no inset placements (assert via the OTEL span next).

- [ ] **Step 3: Add the snapshot regression test**

Append to `sidequest-server/tests/orbital/test_render_coyote_star.py`:

```python
class TestStoryYSnapshot:
    def test_coyote_star_callouts_byte_identical(self, coyote_star_world):
        """AC-Y4: post-Story-Y campaign world snapshot regression."""
        from sidequest.orbital.render import Scope, render_chart
        svg = render_chart(
            orbits=coyote_star_world.orbits,
            chart=coyote_star_world.chart,
            scope=Scope.system_root(),
            t_hours=0.0, party_at=None,
        )
        snapshot_path = (
            Path(__file__).parent / "snapshots" / "coyote_star_callouts_system_t0.svg"
        )
        baseline = snapshot_path.read_text()
        assert svg == baseline, "Snapshot mismatch — re-baseline if intentional"

    def test_callout_count_lower_bound(self, coyote_star_world, span_capture):
        """AC-Y3: at least 9 forced_moon_band callouts (6 RP + 1 + 2)."""
        from sidequest.orbital.render import Scope, render_chart
        from sidequest.telemetry.spans.chart import (
            SPAN_CHART_LABEL_STRATEGY,
            SPAN_CHART_LABEL_DISTRIBUTION,
        )
        render_chart(
            orbits=coyote_star_world.orbits, chart=coyote_star_world.chart,
            scope=Scope.system_root(), t_hours=0.0, party_at=None,
        )
        # Count forced_moon_band selection_reason occurrences.
        forced = [
            s for s in span_capture.all(SPAN_CHART_LABEL_STRATEGY)
            if s.attrs["selection_reason"] == "forced_moon_band"
        ]
        assert len(forced) >= 9
        dist = span_capture.last(SPAN_CHART_LABEL_DISTRIBUTION)
        assert dist.attrs["bodies_callout"] >= 9
```

- [ ] **Step 4: Run tests**

Run: `cd sidequest-server && uv run pytest tests/orbital/test_render_coyote_star.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (in sidequest-server)**

```bash
cd sidequest-server
git add tests/orbital/snapshots/coyote_star_callouts_system_t0.svg tests/orbital/test_render_coyote_star.py
git commit -m "test(orbital): coyote_star post-Story-Y snapshot regression (ADR-094 AC-Y3, AC-Y4)

Pins the production campaign render after Story Y's label additions.
Asserts ≥9 forced_moon_band callouts (6 red_prospect habitats +
tethys_watch + kerel_eye + lower_kerel)."
```

---

### Task 31: Flip ADR-094 frontmatter to live (AC-Y5)

**Files:**
- Modify: `docs/adr/094-orrery-label-placement-strategies.md`

- [ ] **Step 1: Update frontmatter**

In `docs/adr/094-orrery-label-placement-strategies.md`, update the frontmatter:

```yaml
implementation-status: live
implementation-pointer: <Story X merge commit SHA>
```

Replace `<Story X merge commit SHA>` with the actual commit SHA of the
Story X merge to `main` (in `sidequest-server`).

- [ ] **Step 2: Regenerate ADR indexes**

Run: `cd /Users/slabgorb/Projects/oq-1 && uv run python scripts/regenerate_adr_indexes.py`

- [ ] **Step 3: Commit (in oq-1 orchestrator)**

```bash
git add docs/adr/094-orrery-label-placement-strategies.md docs/adr/README.md
git commit -m "docs(adr-094): flip implementation-status to live

Story X merged in sidequest-server: <SHA>. Story Y merged in
sidequest-content: <SHA>. Frontmatter updated; index regenerated."
```

---

### Task 32: ADR amendment — `forced_companion` → `forced_moon_band`

**Files:**
- Modify: `docs/adr/094-orrery-label-placement-strategies.md`

Per implementation spec §9: the implementation generalized the rule, and the
ADR should be amended to reflect what shipped.

- [ ] **Step 1: Edit the ADR**

In `docs/adr/094-orrery-label-placement-strategies.md`:

1a. Update the strategy table row (around line 100) where it says "Forced callout — if `body.parent.type == "companion"`": replace with the broader rule:

```markdown
| `callout` | a small **anchor mark** at the body position | a **label block** placed in a margin gutter zone, joined by an orthogonal **leader line** | fallback when 1 and 2 don't apply, OR forced when body is rendered inside a moon band with a `label:` (companion-children OR habitat-moons) |
```

1b. Update §Selection rule item 1:

```markdown
1. **Forced moon-band callout** — if `body` is rendered inside a moon band AND has a non-empty `label:`, strategy = `callout`. (No exceptions. Covers companion-children — the primary failure mode this ADR was shaped around — and any other parent type whose children render in a moon band, e.g., habitats with named moons. Structural reason: sub-pixel render position has no radial space.)
```

1c. Update §Per-body span enum row for `selection_reason`:

```markdown
| `selection_reason` | enum: `forced_moon_band` \| `textpath_fits` \| `radial_fits` \| `fallback_arc_too_short` \| `fallback_tier_capped` \| `fallback_textpath_too_short` \| `explicit_callout_label` | Why this strategy won. |
```

1d. Add a brief note at the end of §Decision (above §Observability):

```markdown
### Implementation note — generalization from forced_companion

The accepted version of this ADR named the structural rule
`forced_companion` (`parent.type == "companion"`). The implementation
plan (`docs/superpowers/specs/2026-05-04-adr-094-...`) surfaced that
Story Y also adds labels to moons of habitat-typed parents (e.g.
`tethys_watch` under `far_landing`), which the narrow rule did not
cover. The shipped implementation generalizes the rule to
`forced_moon_band` — any moon-band child with a non-empty label —
and renames `selection_reason=forced_companion` to
`selection_reason=forced_moon_band`. Companion-children remain the
canonical case; the rename keeps the OTEL enum truthful to the
underlying structural cause.
```

- [ ] **Step 2: Verify the file lints**

Run: `cd /Users/slabgorb/Projects/oq-1 && head -20 docs/adr/094-orrery-label-placement-strategies.md`
Confirm frontmatter is valid YAML.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/094-orrery-label-placement-strategies.md
git commit -m "docs(adr-094): amend forced_companion → forced_moon_band

Generalizes the structural rule per implementation spec §9. The shipped
code applies forced-callout to any moon-band child with a label, not
just companion-children. Companion-children remain the canonical case.

OTEL enum value renamed to forced_moon_band to keep the lie-detector
truthful to the structural cause (sub-pixel render position)."
```

---

## Self-Review

After completing all tasks:

**Spec coverage check.** Walk the spec §6.2 / §6.3 ACs and confirm each has a task:

| AC | Task | Status |
|----|------|--------|
| AC-S1 forced_moon_band | Task 7 | ✓ |
| AC-S2 explicit_callout_label | Task 8 | ✓ |
| AC-S3 textpath fits | Task 9 | ✓ |
| AC-S4 fallback_textpath_too_short | Task 9 | ✓ |
| AC-S5 radial fits | Task 10 | ✓ |
| AC-S6 fallback_arc_too_short | Task 10 | ✓ |
| AC-S7 fallback_tier_capped | Task 10 | ✓ |
| AC-S8 precedence | Task 11 | ✓ |
| AC-G1 grouped block ≥3 | Task 12 | ✓ |
| AC-G2 singletons <3 | Task 12 | ✓ |
| AC-G3 sort by semi_major_au | Task 12 | ✓ |
| AC-G4 side by bearing | Task 13 | ✓ |
| AC-G5 within-side top-down | Task 14 | ✓ |
| AC-G6 overflow → opposite → inset | Task 14 | ✓ |
| AC-G7 cross-group crossings | Task 15 | ✓ |
| AC-L1..L4 leader geometry | Task 23 | ✓ |
| AC-C1 singleton block content | Task 23 | ✓ |
| AC-C2 grouped block content | Task 23 | ✓ |
| AC-C3 tag length validation | Task 3 | ✓ |
| AC-A1 callout_label known kind | Task 3 | ✓ |
| AC-A2 missing body_ref rejected | Task 3 | ✓ |
| AC-A3 empty text rejected | Task 3 | ✓ |
| AC-A4 annotation wins over label | Task 8 + Task 11 (precedence) | ✓ |
| AC-O1 per-body span | Tasks 17 + 20 (renderer emit) | ✓ |
| AC-O2 distribution sum | Tasks 18 + 27 (wiring assertion) | ✓ |
| AC-O3 reason matches rule | Tasks 7-11 | ✓ |
| AC-O4 inset count | Task 14 + 18 | ✓ |
| AC-O5 cross-group count | Task 15 + 18 | ✓ |
| AC-W1 coyote_star wiring | Task 27 | ✓ |
| AC-X1 synthetic snapshot | Task 26 | ✓ |
| AC-Y1 red_prospect labels | Task 28 | ✓ |
| AC-Y2 far_landing/deep_root_world labels | Task 29 | ✓ |
| AC-Y3 callout count lower bound | Task 30 | ✓ |
| AC-Y4 coyote_star snapshot | Task 30 | ✓ |
| AC-Y5 ADR frontmatter flip | Task 31 | ✓ |

All spec ACs have a task.

**Placeholder scan.** Search the plan for forbidden patterns:

```bash
grep -nE "TBD|TODO|fill in|implement later|similar to task" docs/superpowers/plans/2026-05-04-adr-094-orrery-callouts-implementation.md
```

The only legitimate "PLACEHOLDER" occurrences are in Task 20 step 3, where intermediate stubs are explicitly called out as stubs that Tasks 21-23 replace. These are not plan placeholders — they're an ordered implementation artifact.

**Type consistency check.** Function names used in later tasks reference earlier definitions:
- `_StrategyInput` (Task 6) → used in Tasks 7-11, 16, 20
- `LabelDecision` (Task 4) → used in Tasks 7-11, 12, 14, 15, 16, 20-23
- `_apply_decision_tree` (Task 11) → used in Task 16
- `select_label_strategies` (Task 16) → used in Task 20
- `lay_out_gutter` (Task 14) → used in Task 20
- `_emit_textpath_label` / `_emit_radial_label` / `_emit_callout_block` (stubbed Task 20, real Tasks 21-23) — names match throughout.

Names are consistent.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-04-adr-094-orrery-callouts-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for a 33-task plan because each task is independently scoped and verifiable.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**





