# ADR-094 — Orrery Callout Strategy: Implementation Design

**Date:** 2026-05-04
**Author:** Architect (The Man in Black)
**ADR:** [docs/adr/094-orrery-label-placement-strategies.md](../../adr/094-orrery-label-placement-strategies.md)
**Status:** ready for implementation plan

---

## 1. Purpose

Implement ADR-094's three-strategy taxonomy (`textpath` / `radial` / `callout`)
for orrery body-label placement, including the new selection-rule pipeline,
the `callout_label` annotation kind, the gutter-zone flow-layout, the
leader-line geometry, and the two new OTEL spans (`chart.label_strategy`,
`chart.label_distribution`). Resolve all three failure modes documented in
ADR-094 §Context.

The ADR's design is locked. This document specifies *how* it lands in the
existing `sidequest-server` codebase, decomposed into two implementation
stories:

- **Story X — Renderer + selection rules + spans + schema.** Server-side,
  ~5pt. Lands the entire mechanism behind a synthetic test fixture. Does
  *not* alter coyote_star content, so the production campaign world
  continues to render exactly as it does today (no labeled
  companion-children means the new code path emits zero callouts).
- **Story Y — Content: label fields on companion habitats.** Content-side,
  ~1pt. Activates the new behavior on the production campaign world by
  adding `label:` fields to red_prospect's six habitats and the moons of
  far_landing / deep_root_world. Lands within hours of Story X merge.

## 2. Architectural Approach

### 2.1 Module shape

A new module `sidequest/orbital/label_strategy.py` holds the pure-logic
strategy selection and gutter-layout passes. `render.py` imports from it
and dispatches SVG emission per decision. The strategy module imports
from `models.py` and `palette.py` only — no `svgwrite`, no rendering.

```
sidequest/orbital/
├── render.py                ← modified at known cut points
├── models.py                ← +1 annotation kind, +1 optional field
├── palette.py               ← +text-width constants, +callout/leader/gutter constants
└── label_strategy.py        ← NEW (pure selection + flow-layout)

sidequest/telemetry/spans/
└── chart.py                 ← +emit_chart_label_strategy, +emit_chart_label_distribution

tests/orbital/
├── fixtures/world_callout_strategy/
│   ├── orbits.yaml
│   └── chart.yaml
├── snapshots/world_callout_strategy_t0.svg
└── test_render_callouts.py
```

**Why a sibling module rather than expanding `render.py`:** `render.py` is
already 1693 lines. The selection pass is pure (no SVG side effects), the
flow-layout is pure (no SVG side effects), and both have rich unit-test
surfaces independent of svgwrite. Extracting them keeps the new code
reviewable on its own and bounds `render.py`'s growth to the SVG emission
paths and the `_render_moon_band` carve-out.

**Module dependency direction:**
```
render.py  →  label_strategy.py  →  models.py + palette.py
              (no svgwrite anywhere in label_strategy)
```

### 2.2 Approach selected (and approaches rejected)

The implementation hoists strategy selection into a pre-emission pass and
keeps the existing two-strategy code paths intact. Rejected alternatives:

- **Refactor label rendering into a single dispatcher.** Extracting all
  label rendering into a new `_label_dispatcher.py` is a clean Boy Scout
  move but expands story scope. Filed as a deferred follow-up
  (`render.py` decomposition into `label_strategy/` + `layer_engraved/`
  + `layer_flavor/` modules); not in Story X scope.
- **Decision-tree inline in the per-body label loop.** Doesn't compose
  with the gutter flow-layout, which requires all callout decisions
  *before* any one is placed. Structurally rejected.

## 3. Components

### 3.1 `label_strategy.py` — public surface

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class LabelStrategy(StrEnum):
    TEXTPATH = "textpath"
    RADIAL = "radial"
    CALLOUT = "callout"


class SelectionReason(StrEnum):
    FORCED_MOON_BAND = "forced_moon_band"           # see §10 deviation note
    EXPLICIT_CALLOUT_LABEL = "explicit_callout_label"
    TEXTPATH_FITS = "textpath_fits"
    RADIAL_FITS = "radial_fits"
    FALLBACK_TEXTPATH_TOO_SHORT = "fallback_textpath_too_short"
    FALLBACK_ARC_TOO_SHORT = "fallback_arc_too_short"
    FALLBACK_TIER_CAPPED = "fallback_tier_capped"


@dataclass(frozen=True)
class LabelDecision:
    body_id: str
    parent_id: str | None
    parent_type: str | None
    strategy: LabelStrategy
    reason: SelectionReason
    text: str
    register: Literal["engraved", "chalk", "prose"]
    text_width_px: float
    radial_tier: int | None              # RADIAL only
    arc_available_px: float | None       # RADIAL only
    textpath_path_id: str | None         # TEXTPATH only
    path_circumference_px: float | None  # TEXTPATH only
    callout_tag: str | None              # CALLOUT optional second line


@dataclass(frozen=True)
class CalloutBlock:
    """A single callout slot — a singleton body or a sibling group."""
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


def select_label_strategies(
    orbits: OrbitsConfig,
    chart: ChartConfig,
    placements: list[_BodyPlacement],
    forced_callout_placements: list[_BodyPlacement],
    viewport: _Viewport,
) -> list[LabelDecision]:
    """Apply the four-rule decision tree per body. Pure function."""


def lay_out_gutter(
    decisions: list[LabelDecision],
    placements_by_id: dict[str, _BodyPlacement],
    viewport: _Viewport,
) -> GutterLayout:
    """Group, side-assign, sort, and pack callout blocks. Pure function."""


def estimate_text_width_px(
    text: str,
    register: Literal["engraved", "chalk", "prose"],
) -> float:
    """Upper-bound width estimate using calibrated palette constants."""
```

### 3.2 `palette.py` — new constants

```python
# Text-width estimator (calibrated upper bounds per register at LABEL_*_FONT_SIZE).
LABEL_ENGRAVED_CHAR_WIDTH_PX: float = 8.5   # Orbitron 700 + letter-spacing 2
LABEL_CHALK_CHAR_WIDTH_PX:    float = 9.0   # Orbitron 600 + letter-spacing 3
LABEL_PROSE_CHAR_WIDTH_PX:    float = 6.5   # VT323 italic

# Safety factors (per ADR §Decision rule 2 / "same factor or larger").
TEXTPATH_FIT_SAFETY: float = 1.2
ARC_FIT_SAFETY:      float = 1.2

# Callout block geometry.
CALLOUT_BLOCK_PADDING_PX:         float = 4.0
CALLOUT_BLOCK_LINE_HEIGHT_PX:     float = 12.0
CALLOUT_BLOCK_TAG_LINE_HEIGHT_PX: float = 10.0
CALLOUT_BLOCK_INTER_BLOCK_GAP_PX: float = 6.0
CALLOUT_GROUP_BORDER_PX:          float = 0.6
CALLOUT_GROUP_TITLE_HEIGHT_PX:    float = 14.0

# Leader-line geometry.
LEADER_STROKE_WIDTH_PX:    float = 1.0
LEADER_TERMINATOR_SIZE_PX: float = 3.0

# Gutter zone bounds.
GUTTER_WIDTH_PX:           float = 120.0
GUTTER_MIN_VIABLE_WIDTH_PX:float = 60.0     # below this, gutter is unavailable

# Tag-line max length (ADR §Label-block content rule).
CALLOUT_TAG_MAX_CHARS: int = 24
```

`GUTTER_LEFT_X_PX` / `GUTTER_RIGHT_X_PX` / `GUTTER_TOP_Y_PX` /
`GUTTER_BOTTOM_Y_PX` are computed at render-time from the viewport, not
fixed in palette — they depend on the chart bounding box.

### 3.3 `models.py` — additions

```python
KNOWN_ANNOTATION_KINDS: frozenset[str] = frozenset({
    "engraved_label", "glyph", "scale_ruler", "bearing_marks",
    "anomaly_marker", "lagrange_point", "flight_corridor",
    "callout_label",   # NEW
})


class Annotation(BaseModel):
    ...
    tag: str | None = None    # NEW — only meaningful when kind == "callout_label"

    @model_validator(mode="after")
    def _validate_callout_label(self) -> Annotation:
        if self.kind != "callout_label":
            return self
        if not self.text or not self.text.strip():
            raise ValueError("callout_label requires non-empty text")
        if not self.body_ref:
            raise ValueError("callout_label requires body_ref")
        if self.tag is not None and len(self.tag) > CALLOUT_TAG_MAX_CHARS:
            raise ValueError(
                f"callout_label tag exceeds {CALLOUT_TAG_MAX_CHARS} chars: "
                f"{self.tag!r} ({len(self.tag)} chars)"
            )
        return self


class BodyDef(BaseModel):
    ...
    @model_validator(mode="after")
    def _validate_label_not_blank(self) -> BodyDef:
        if self.label is not None and not self.label.strip():
            raise ValueError(f"label must be non-empty if provided")
        return self
```

### 3.4 `chart.py` (telemetry/spans) — additions

```python
SPAN_CHART_LABEL_STRATEGY     = "chart.label_strategy"
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
    tier: int | None = None,
    arc_available_px: float | None = None,
    text_width_px: float,
    path_circumference_px: float | None = None,
) -> None:
    """One span per labeled body per render."""
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
    """One span per render. Aggregates strategy attribution."""
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

### 3.5 `render.py` — modification points

| Region | Change |
|---|---|
| Top imports | Import from `label_strategy` |
| `_resolve_curve_along` (~450) | No code change. Existing flip-detection comment becomes the prelude to the new `path_circumference_px ≥ text_width × 1.2` check that lives in `select_label_strategies`. |
| Engraved-layer label rendering (after `_assign_collision_tiers`, ~907) | Replace direct `_resolve_anchor` + radial text emission with: invoke `select_label_strategies`, then dispatch by `LabelStrategy` to one of three SVG handlers (textpath / radial / callout). |
| `_render_moon_band` (~1053) | When `parent.type == COMPANION`, surface each child placement as a forced-callout candidate (returned alongside the existing moon-band group) instead of swallowing the children silently. |
| End of `render_chart` | Emit `chart.label_distribution` from the strategy distribution counts. The existing `emit_chart_render` call already accepts these counts as kwargs (extended by Story 45-42), and the same totals flow into both spans. |

## 4. Data Flow

```
render_chart(orbits, chart, scope, t_hours, party_at)
│
├── 1. Compute Kepler positions for all visible bodies          (existing)
├── 2. Build _BodyPlacement list for top-level bodies           (existing)
├── 3. Render moon-band groups for each top-level body
│      ├─ NORMAL parents: dashed ring + dots, no labels         (existing)
│      └─ COMPANION parents: dashed ring + dots,                (NEW)
│         children surfaced to forced_callout_placements
│
├── 4. Strategy selection pass    (label_strategy.select_label_strategies)
│      For each labeled body OR forced-callout candidate:
│         apply four-rule decision tree (forced > explicit
│         > textpath > radial > callout). Compute text_width_px
│         via estimate_text_width_px(). Record SelectionReason.
│         Emit chart.label_strategy span per body.
│
├── 5. Gutter layout pass         (label_strategy.lay_out_gutter)
│      Group callouts by parent_id → grouped block (≥3) vs
│      singletons. Side-assign by anchor bearing. Sort within
│      side by bearing. Pack top-down with padding. On overflow,
│      retry opposite side; on double-overflow, mark inset.
│      Compute pairwise leader-segment crossings; record count.
│
├── 6. SVG emission                (render.py)
│      For each LabelDecision in decisions:
│        ├─ TEXTPATH → emit <text><textPath href="#…">         (existing path)
│        ├─ RADIAL  → emit <text x=anchor_x y=anchor_y>          (existing path)
│        └─ CALLOUT → emit anchor mark (already there) +         (NEW)
│                     leader line (orthogonal, one bend) +
│                     label block (rect + text lines, or
│                     grouped block with title/border)
│
├── 7. Emit chart.label_distribution span                       (NEW)
└── 8. Emit chart.render span                                    (existing)
```

### 4.1 Decision tree (per body)

```
For each candidate body (labeled top-level body OR moon-band child with label):

   Is the body rendered inside a moon band AND does it have a `label:`?
      → CALLOUT, reason=FORCED_MOON_BAND
      (No exceptions. Covers companion-children AND habitat-moons —
      see §10 deviation note. Structural rule: sub-pixel render
      position has no radial space, period.)

   Is there a callout_label annotation referencing this body?
      → CALLOUT, reason=EXPLICIT_CALLOUT_LABEL

   Is there an engraved_label annotation with curve_along
   referencing this body?
      Resolve curve_along path; measure path_circumference_px.
      If path_circumference_px ≥ text_width_px × TEXTPATH_FIT_SAFETY:
         → TEXTPATH, reason=TEXTPATH_FITS
      Else: record FALLBACK_TEXTPATH_TOO_SHORT as latent reason
            and fall through to callout (NOT to radial — designer
            opted into curved label, preserve that intent).

   Does the body have a `label:` field?
      Compute neighbor_arc_at_radius (smallest applicable).
      If text_width_px ≤ neighbor_arc_px / ARC_FIT_SAFETY:
         Run _assign_collision_tiers.
         If tier ≤ LABEL_TIER_MAX:
            → RADIAL, reason=RADIAL_FITS
         Else: latent FALLBACK_TIER_CAPPED, fall through.
      Else: latent FALLBACK_ARC_TOO_SHORT, fall through.

   Fallback:
      → CALLOUT, with the latent fallback reason
        (priority order: TEXTPATH_TOO_SHORT > ARC_TOO_SHORT > TIER_CAPPED).
```

The "latent fallback reason" lets the OTEL span tell the GM panel
*why* a body got demoted to callout, not just *that* it did.

### 4.2 Moon-band-child surfacing (the structural fix for Failure 3)

`_render_moon_band` currently returns moon placements for downstream
de-collision, but those placements are unused (the moon-band emits no
labels — and a moon-band moon with a `label:` field today is a silent
fallback). The change:

1. Moon-band still draws the dashed ring and the moon dots — visual
   continuity preserved. The dot is the **anchor mark** the leader will
   originate from.
2. For *every* moon-band parent (companion OR habitat OR any other
   parent type that renders children inside a moon band), each child
   placement that has a non-empty `label:` field is added to a
   `forced_callout_placements` list returned alongside the moon-band
   group. Children without `label:` remain unlabeled (existing
   behavior — silent moon-band dots).
3. The strategy selection pass receives this list and emits one
   `LabelDecision(strategy=CALLOUT, reason=FORCED_MOON_BAND)` per child.
4. The gutter-layout pass groups them by `parent_id`. Parents with ≥3
   labeled moon-band children produce a grouped block titled
   `<PARENT_LABEL> SYSTEM`. Parents with 1-2 labeled children produce
   singleton callouts.

## 5. Error Handling

### 5.1 Hard errors (raise — no silent fallbacks)

| Condition | Behavior |
|---|---|
| `callout_label` annotation `body_ref` missing or refers to nonexistent body | `Annotation` validator raises `ValueError` at chart load. |
| `callout_label` `tag` longer than 24 chars | `Annotation` validator raises `ValueError` at chart load. |
| `callout_label` `text` empty/blank | `Annotation` validator raises `ValueError` at chart load. |
| `body.label` set but blank | `BodyDef` validator raises `ValueError`. |
| Internal: `LabelDecision(strategy=TEXTPATH)` with no `textpath_path_id` | Assertion in render dispatch — fail loud, never emit malformed SVG. |
| Body unrenderable at scope (e.g., `show_at_system_scope=False` at root) | Skipped from strategy pass. Not failure — does not contribute to `bodies_unlabeled`. |
| Unknown annotation kind | Existing validator raises (unchanged). |

### 5.2 Soft signals (OTEL only)

| Condition | Span attribute |
|---|---|
| Gutter overflow on natural side, succeeded on opposite | none — routine layout |
| Gutter overflow on both sides, fell to inset | `chart.label_distribution.gutter_inset_fallbacks += 1` |
| Cross-group leader crossings detected | `chart.label_distribution.cross_group_crossings += 1` |
| Strategy selected via fallback path | `chart.label_strategy.selection_reason = FALLBACK_*` |

### 5.3 Edge cases

1. **Body has both `engraved_label` annotation and `label:` field.** Existing
   behavior: annotation wins, `label:` suppressed. Preserved. If the
   annotation's textpath fails fit, fallback is callout (preserves
   designer intent), *not* radial.
2. **Body has both `callout_label` annotation and `label:` field.** Annotation
   wins (text + tag from annotation). If text strings differ, validator
   emits a warning span (`chart.annotation_label_text_mismatch`) but
   does not raise.
3. **Companion with no labeled children.** Forced-callout list is empty;
   moon-band renders normally; `bodies_callout` unchanged.
4. **Companion with 1-2 children.** Below grouping threshold; each child is
   a singleton callout, not a grouped block.
5. **Strategy is TEXTPATH but path is out-of-scope.** Existing
   `_CurveScopeMismatch` is caught; annotation skipped at this scope; body
   falls through rules 3/4 based on its own state.
6. **Gutter Y collision.** Flow-layout uses monotonic Y by construction; no
   collision possible within a side.
7. **Inset fallback would overlap a body or orbit ring.** Coarse grid scan
   of chart interior, score by distance to bodies and rings, pick highest
   scoring cell. Below minimum quality, place at chart center anyway and
   emit `chart.label_distribution.inset_quality_warning` (deferred — heuristic
   refinement, not a blocker).
8. **Drill-in scope where `GUTTER_WIDTH_PX < GUTTER_MIN_VIABLE_WIDTH_PX`.**
   Gutter treated as fully unavailable; all callouts go inset; the
   inset_fallback_count == bodies_callout signals to the GM panel that
   this scope can't accommodate callouts. Acceptable — drill-in scope is
   narrower-named anyway.
9. **Safety factor wrong for a real campaign.** Safety factors are
   `palette.py` constants. Tuning is a one-line content-side change in a
   follow-up PR; snapshot tests catch the regression.

### 5.4 Out of scope (Story X)

- Animated/interactive callouts (hover, click).
- Multi-language label rendering (constants are ASCII-Latin calibrated).
- Adaptive viewBox-sensitive gutter sizing.
- Inset-quality heuristic refinement (escape valve via OTEL).

## 6. Testing Strategy

### 6.1 Synthetic fixture — `world_callout_strategy`

`tests/orbital/fixtures/world_callout_strategy/orbits.yaml`:

```yaml
version: "0.1.0"
clock: { epoch_days: 0 }
travel: { realism: orbital }

bodies:
  primary_star:
    type: star
    label: "PRIMARY"

  outer_world:                # textpath_fits — long orbit ring
    type: habitat
    parent: primary_star
    semi_major_au: 8.0
    period_days: 8000
    epoch_phase_deg: 0
    label: "OUTER WORLD"

  tiny_belt:                  # textpath_too_short
    type: arc_belt
    parent: primary_star
    semi_major_au: 0.5
    period_days: 130
    arc_extent_deg: 30
    epoch_phase_deg: 270
    label: "TINY BELT"

  spread_alpha:               # explicit_callout_label override
    type: habitat
    parent: primary_star
    semi_major_au: 3.0
    period_days: 1900
    epoch_phase_deg: 90
    label: "SPREAD ALPHA"

  cluster_a:                  # arc_too_short trojan triple at 1AU
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
  cluster_d:                  # tier_capped — pushes counter past LABEL_TIER_MAX
    type: habitat
    parent: primary_star
    semi_major_au: 1.05
    period_days: 392
    epoch_phase_deg: 120
    label: "CLUSTER DELTA"

  companion_dwarf:            # forced_moon_band (3-member group, companion parent)
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

  lonely_companion:           # forced_moon_band singleton (1 child, companion parent)
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

  # Moon-of-habitat case (the latent ADR gap closed by the deviation in §10).
  # Exercises forced_moon_band on a non-companion parent.
  habitat_with_moons:
    type: habitat
    parent: primary_star
    semi_major_au: 2.2
    period_days: 1200
    epoch_phase_deg: 315
    label: "HABITAT WITH MOONS"
  moon_z1:                    # forced_moon_band, parent.type=habitat
    type: habitat
    parent: habitat_with_moons
    semi_major_au: 0.004
    period_days: 25
    epoch_phase_deg: 0
    label: "MOON Z-1"
  moon_z2:                    # forced_moon_band, parent.type=habitat
    type: habitat
    parent: habitat_with_moons
    semi_major_au: 0.008
    period_days: 50
    epoch_phase_deg: 180
    label: "MOON Z-2"

  spread_beta:                # radial_fits — solo body, clear bearing
    type: habitat
    parent: primary_star
    semi_major_au: 4.5
    period_days: 3500
    epoch_phase_deg: 220
    label: "SPREAD BETA"
```

`tests/orbital/fixtures/world_callout_strategy/chart.yaml`:

```yaml
version: "0.1.0"
annotations:
  - kind: engraved_label
    text: "OUTER WORLD"
    curve_along: orbit_outer_world

  - kind: engraved_label
    text: "TINY BELT"
    curve_along: body:tiny_belt          # too short — falls back to callout

  - kind: callout_label                  # explicit override (rule precedence)
    text: "SPREAD ALPHA"
    body_ref: spread_alpha
    tag: "habitat · 3.0 AU"
```

### 6.2 Acceptance Criteria (Story X)

#### Selection rules

- **AC-S1** Any body rendered inside a moon band (any parent type)
  with a non-empty `label:` field always selects
  `strategy=callout, reason=forced_moon_band`, regardless of textpath
  or radial viability. Covers companion-children (e.g.,
  `red_prospect`'s 6 habitats) AND non-companion moon-band moons
  (e.g., `tethys_watch` parented to habitat `far_landing`). See §10.
- **AC-S2** A body with a `callout_label` annotation selects
  `strategy=callout, reason=explicit_callout_label` even when radial
  would have fit. (Does not override `forced_moon_band` — see AC-S8.)
- **AC-S3** A body with `engraved_label` annotation whose `curve_along`
  path circumference ≥ `text_width × 1.2` selects
  `strategy=textpath, reason=textpath_fits`.
- **AC-S4** A body with `engraved_label` annotation whose `curve_along`
  path circumference < `text_width × 1.2` falls through to
  `strategy=callout, reason=fallback_textpath_too_short` (designer
  intent preserved as callout, not silently demoted to radial).
- **AC-S5** A body with `label:` and clear angular space selects
  `strategy=radial, reason=radial_fits` with tier value populated.
- **AC-S6** A body whose nearest-neighbor arc-length ÷ `ARC_FIT_SAFETY`
  is less than `text_width` falls through to
  `strategy=callout, reason=fallback_arc_too_short`.
- **AC-S7** A body whose tier exceeds `LABEL_TIER_MAX` falls through to
  `strategy=callout, reason=fallback_tier_capped`.
- **AC-S8** Selection-rule precedence:
  `forced_moon_band > explicit_callout_label > textpath_fits >
  radial_fits > fallback_*`. A body matching multiple rules selects
  the highest-priority match. A companion-child with a `callout_label`
  annotation reports `reason=forced_moon_band` (the structural rule
  wins; the annotation is redundant for moon-band-rendered bodies).

#### Gutter layout

- **AC-G1** Moon-band siblings of the same parent (≥3 labeled children)
  form a single grouped `<PARENT LABEL> SYSTEM` block. Applies to
  companion-children (red_prospect) and habitat-moons alike.
- **AC-G2** Moon-band siblings below threshold (1 or 2 labeled children
  under a parent) render as individual singleton callouts. Applies to
  e.g., `far_landing` with 1 labeled moon (`tethys_watch`).
- **AC-G3** Within a grouped block, members sort by ascending
  `semi_major_au`; first line is the innermost child.
- **AC-G4** Block side assignment matches anchor bearing: bearings
  270°→90° (right half) → right gutter; bearings 90°→270° (left
  half) → left gutter.
- **AC-G5** Within a side, blocks are placed top-down sorted by
  bearing; flow-layout Y monotonically increases.
- **AC-G6** Gutter overflow on natural side retries opposite side;
  double-overflow falls to inset placement and increments
  `gutter_inset_fallbacks`.
- **AC-G7** Within-group leader lines do not cross (verified
  geometrically). Cross-group crossings are counted in
  `cross_group_crossings`.

#### Leader-line geometry

- **AC-L1** Leader is orthogonal with at most one bend.
- **AC-L2** Leader stroke color matches the body's `label_register`
  palette color (engraved → BRASS, chalk → PARTY/white, prose →
  DIM/italic-yellow).
- **AC-L3** Leader terminator is a 3×3px filled square at the
  label-block end.
- **AC-L4** Leader origin is the body's anchor center (existing body
  glyph; **no new anchor shape**).

#### Label-block content

- **AC-C1** Singleton callout block contains the title (`label:` value)
  on line 1, optionally a tag (≤24 chars) on line 2; nothing else.
- **AC-C2** Grouped block contains a title `"<PARENT LABEL> SYSTEM"`
  on line 1, then one line per member as `<LABEL> · <distance>`
  ordered innermost-first.
- **AC-C3** `callout_label` annotation `tag` longer than 24 characters
  fails YAML load with `ValidationError`.

#### Annotation schema

- **AC-A1** `callout_label` is a known annotation kind; an unknown
  kind still raises (no silent fallback).
- **AC-A2** `callout_label` with `body_ref` referencing a non-existent
  body fails YAML load.
- **AC-A3** `callout_label` with empty `text` fails YAML load.
- **AC-A4** A body with both `label:` and a `callout_label` annotation
  referencing it: the annotation's text wins; no double rendering.

#### Observability (lie-detector wiring)

- **AC-O1** Per labeled body, exactly one `chart.label_strategy` span
  fires per render; attribute set matches ADR §Per-body span schema
  (8 fields, with strategy-specific fields populated/null
  appropriately).
- **AC-O2** Per render, exactly one `chart.label_distribution` span
  fires; counts sum correctly:
  `bodies_textpath + bodies_radial + bodies_callout + bodies_unlabeled
  == bodies_total`.
- **AC-O3** `selection_reason` enum value matches the rule that won,
  including which fallback reason for callouts.
- **AC-O4** `gutter_inset_fallbacks` increments when both gutters
  reject a block.
- **AC-O5** `cross_group_crossings` reflects post-layout pairwise
  leader-segment intersections.

#### Wiring (per CLAUDE.md "Every Test Suite Needs a Wiring Test")

- **AC-W1** `test_coyote_star_renders_without_crash`: invokes
  `render_chart` against the real campaign world fixture. Asserts
  non-empty SVG. Asserts `chart.label_distribution` span fired with
  `bodies_callout == 0` (Story X has not yet added labels to
  red_prospect's children, so nothing is callout-eligible).
  Validates the new pipeline is reachable from production code.

#### Snapshot regression

- **AC-X1** `world_callout_strategy` at the canonical render produces
  byte-identical output against
  `tests/orbital/snapshots/world_callout_strategy_t0.svg`.

### 6.3 Acceptance Criteria (Story Y)

- **AC-Y1** `red_prospect`'s six habitats (`turning_hub`, `whitedrift`,
  `ember_moon`, `the_horn`, `dead_lash`, `vael_thain`) gain `label:`
  fields matching their canonical names.
- **AC-Y2** `far_landing`'s moon (`tethys_watch`) and `deep_root_world`'s
  moons (`kerel_eye`, `lower_kerel`) gain `label:` fields.
- **AC-Y3** Rendering coyote_star at system-scope produces
  `bodies_callout >= 9` (6 red_prospect habitats via grouped block,
  1 tethys_watch singleton from far_landing, 2 from deep_root_world's
  moons). May be higher if existing top-level bodies fall through to
  `fallback_arc_too_short` (the trojan cluster failure mode the ADR
  was shaped around). Exact count is pinned by the snapshot test
  below; this AC asserts only the lower bound.
- **AC-Y4** `tests/orbital/snapshots/coyote_star_callouts_system_t0.svg`
  byte-identical regression test passes.
- **AC-Y5** ADR-094 frontmatter flips:
  `implementation-status: live` and `implementation-pointer` set to
  the Story X merge commit. (This change happens in oq-1's `docs/adr/`
  alongside Story Y's content YAML edit, since orchestrator owns the
  ADRs.)

## 7. Story Sequencing

```
Story X (sidequest-server, ~5pt)            Story Y (sidequest-content, ~1pt)
─────────────────────────────────           ─────────────────────────────────
Renderer + selection rules                  Add label: fields to:
+ label_strategy.py module                    - red_prospect's 6 habitats
+ palette.py constants                        - far_landing's moon
+ models.py annotation kind                   - deep_root_world's 2 moons
+ chart.py spans                            + new coyote_star snapshot test
+ synthetic fixture + tests                + ADR-094 frontmatter flip to live
+ coyote_star wiring test (no crash)
                                            depends on Story X merging first
                                            (renderer must exist for the
                                            labels to render anywhere
                                            meaningful)
```

Story Y is intentionally tiny — pure YAML edits and a snapshot baseline.
It can be committed and reviewed in under an hour once Story X is merged.

## 8. Risk and Mitigations

| Risk | Mitigation |
|---|---|
| Text-width estimator miscalibrated → labels overlap or unnecessary callouts. | Bias toward overestimate (safe failure mode). Calibrate against UI-rendered bbox readback once during implementation. Snapshot tests detect regressions. |
| `× 1.2` safety factor wrong for a real campaign. | Constants in `palette.py`; one-line tunable. |
| Inset-fallback overlaps body or ring on a dense chart. | OTEL `gutter_inset_fallbacks` and (deferred) `inset_quality_warning` make density visible to Keith without crashing the render. |
| Reviewer concern about `render.py` size growth. | New code lives in `label_strategy.py`. `render.py` grows by the SVG dispatch and the moon-band carve-out only — minimal LOC delta. |
| Snapshot churn on unrelated future changes. | Synthetic snapshot is deterministic by design; coyote_star snapshot is one file, easily re-baselined. Existing orrery-v2 already follows this pattern. |
| Story Y blocked behind Story X — content team idles. | Story X has its own synthetic fixture for development; Story Y is a 30-minute YAML edit when the merge lands. |

## 9. Deviation from ADR-094 — `forced_moon_band` generalization

### Spec source
ADR-094 §Decision §Selection rule, item 1:
> **Forced callout** — if `body.parent.type == "companion"`, strategy =
> `callout`. (No exceptions. The first-class-destination rule is what
> makes the chart navigable for habitat groups.)

### Spec text (ADR's narrow framing)
The forced-callout rule fires only when `parent.type == "companion"`.
Justification given: companion-children are the structural failure
mode (Failure 3 in §Context) where six named habitats collapse into
the unlabeled moon-band ring.

### Implementation (this spec's broader rule)
The forced-callout rule fires whenever a body is rendered inside a
moon band AND has a non-empty `label:` field, regardless of parent
type. Reason name changed from `forced_companion` to
`forced_moon_band` to reflect the structural cause (sub-pixel render
position) rather than the parent type.

### Why the deviation
ADR-094 §Implementation Pointer Story Y states:
> Adds `label:` to the six red_prospect habitats and the moons of
> far_landing / deep_root_world. Pure YAML.

But `tethys_watch` (parented to habitat `far_landing`), `kerel_eye`
and `lower_kerel` (parented to habitat `deep_root_world`) are not
companion-parented. Implementing the ADR's selection rule literally
would add `label:` fields to those moons that the renderer would
silently fail to display (CLAUDE.md violation: silent fallback).

The structural reason for forcing callout is that moon-band-rendered
bodies have effectively zero radial space at any chart scale that
shows their parent. This applies to ALL moon-band children, not just
companion children. The narrow rule is a special case of the broader
rule, and Story Y as written requires the broader rule to land
end-to-end.

### Forward impact
- All companion-children continue to receive callouts (ADR's
  Failure-3 case fully preserved).
- Habitat-moons with labels also receive callouts (Story Y now
  ships without silent fallbacks).
- Any future world that adds `label:` to a deep moon (e.g., a
  gate's moon, a wreck's moon) automatically gets a callout
  without requiring a parent-type retrofit.
- OTEL `selection_reason` enum gains `forced_moon_band` instead of
  `forced_companion`. The GM panel reads one consistent reason for
  all moon-band-forced callouts.

### Recommendation for ADR amendment
ADR-094 should be amended (post-merge of Story X) to replace
`forced_companion` with `forced_moon_band` in §Selection rule item 1
and §Per-body span enum. Filed as a follow-up alongside the
implementation flip from `deferred` to `live`.

## 10. References

- ADR-094 (this implementation's source of truth)
- ADR-088 (frontmatter convention)
- ADR-090 (OTEL dashboard restoration — span destination)
- ADR-086 (image-composition taxonomy — taxonomy-of-strategies precedent)
- `sidequest-server/sidequest/orbital/render.py` (lines ~450, ~840-927,
  ~1053-1078: known cut points)
- `sidequest-server/sidequest/orbital/models.py:174-189`
  (`KNOWN_ANNOTATION_KINDS`)
- `sidequest-server/sidequest/orbital/palette.py:33-104`
  (existing font/label constants)
- `sidequest-server/sidequest/telemetry/spans/chart.py`
  (existing `chart.render` pattern)
- `sidequest-server/tests/orbital/test_render_orrery_v2.py`
  (test pattern precedent)
- `sidequest-server/tests/orbital/fixtures/world_orrery_v2/`
  (fixture pattern precedent)
- `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml`
  (Story Y target)
- CLAUDE.md "GM panel is the lie detector" (observability requirement)
- CLAUDE.md "Every Test Suite Needs a Wiring Test" (AC-W1 requirement)
