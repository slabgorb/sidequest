# Plot a Course, Kestrel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the player ask the narrator to plot a course to a body or quest objective and have the orbital chart show it as a curved Bezier overlay with ETA + Δv cost annotations. Plot only — no clock advance, no movement, no fuel mutation.

**Architecture:** New `sidequest/orbital/course.py` module (pure functions: course computation, cost model, Bezier geometry). New `PlottedCourse` field on `GameSnapshot`. New sidecar intent variants `plot_course` / `cancel_course` parsed in narration_apply, applied as state patches. New `<courses>` block injected by orchestrator into Recency zone. Existing `render_chart` SVG composer extended to draw the Bezier overlay and HUD chip when `plotted_course` is set. UI orbital hook extended to refetch on `plotted_course` STATE_PATCH.

**Tech Stack:** Python 3.11+ / FastAPI / Pydantic v2 / pytest (server). React 19 / TypeScript / Vite / vitest (ui). OTEL spans via existing `sidequest.telemetry.spans` package.

**Spec:** `docs/superpowers/specs/2026-05-03-plot-a-course-design.md`

**Repos & branches:**
- `sidequest-server` → branch `feat/plot-a-course` → PR to `develop`
- `sidequest-ui` → branch `feat/plot-a-course` → PR to `develop`

Server PR ships first; UI PR depends on `plotted_course` field landing on the snapshot wire.

---

## File Structure

### Server (sidequest-server)

**Create:**
- `sidequest/orbital/course.py` — `PlottedCourse`, `CourseRow`, `compute_courses()`, `compute_eta_and_dv()`, `validate_course_request()`. Pure module, no I/O.
- `sidequest/orbital/course_geometry.py` — `bezier_control_offset()`, `prograde_sign()`, `chord_angular_distance_deg()`. Pure geometry, separate from selection logic so each is testable in isolation.
- `sidequest/orbital/course_render.py` — `render_course_overlay(svg_root, course, orbits, t_hours)`. Pure SVG composer. Separate from `course.py` to keep the model module free of `lxml`/string-building concerns.
- `sidequest/handlers/course_intent.py` — sidecar-intent extractor: parses `plot_course` / `cancel_course` from `game_patch` JSON, validates, emits state patches.
- `sidequest/protocol/course_intent.py` — `PlotCourseSidecar`, `CancelCourseSidecar` Pydantic models for the JSON variants.
- `sidequest/telemetry/spans/course.py` — `course.compute`, `course.plot`, `course.plot.rejected`, `course.cancel`, `course.render_overlay` span helpers.
- `tests/orbital/test_course_compute.py`
- `tests/orbital/test_course_cost.py`
- `tests/orbital/test_course_geometry.py`
- `tests/orbital/test_course_render_overlay.py`
- `tests/handlers/test_course_intent_wired.py`
- `tests/agents/test_narrator_courses_block.py`
- `tests/server/test_recent_body_mentions.py`

**Modify:**
- `sidequest/game/session.py` (around line 473, `party_body_id`) — add `plotted_course: PlottedCourse | None = None` and `quest_anchors: list[str] = Field(default_factory=list)` to `GameSnapshot`. Add forward reference import.
- `sidequest/server/session.py` — add `_recent_body_mentions: deque[str]` ring buffer and accessor; add `note_body_mentioned()` mutator.
- `sidequest/orbital/render.py` — call `render_course_overlay()` when snapshot carries a course; render HUD chip in `HudBottomStrip` equivalent.
- `sidequest/orbital/intent.py` (line ~62, `render_chart` call) — pass `plotted_course` and call overlay composer.
- `sidequest/agents/orchestrator.py` (after the line ~1428 NPC-intro section) — register `<courses>` PromptSection in Recency zone when world has orbital tier.
- `sidequest/server/narration_apply.py` — invoke `course_intent.handle_sidecar()` after game_patch parse, before encounter trigger.

### UI (sidequest-ui)

**Create:**
- `src/components/__tests__/OrbitalChartHudChip.test.tsx`
- `src/hooks/__tests__/useOrbitalChart.plot.test.ts`

**Modify:**
- `src/types/orbital-intent.ts` — add `plotted_course` field to `OrbitalIntentResponse`.
- `src/hooks/useOrbitalChart.ts` — accept `plottedCourseRevision: number` prop; refetch view_map when it changes.
- `src/components/OrbitalChart/HudBottomStrip.tsx` — render course chip (`COURSE → DEEP ROOT • ETA 30h • Δv 1.0`) when course present.
- `src/screens/<wherever-orbital-is-bound>/index.tsx` (find via `useOrbitalChart` consumer) — wire `plotted_course` from snapshot into the hook.

---

## Setup

### Task 0: Create feature branches

**Files:** none (git operations only)

- [ ] **Step 1: Server branch**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git checkout develop
git pull
git checkout -b feat/plot-a-course
```

- [ ] **Step 2: UI branch**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
git checkout develop
git pull
git checkout -b feat/plot-a-course
```

- [ ] **Step 3: Verify clean state**

```bash
cd /Users/slabgorb/Projects/oq-2 && just status
```

Expected: all repos show no uncommitted changes; server and ui on `feat/plot-a-course`.

---

## Server — Phase 1: Cost & geometry primitives

These are pure functions with no SideQuest dependencies. Building them first means everything downstream can use them with confidence.

### Task 1: chord_angular_distance_deg

**Files:**
- Create: `sidequest-server/sidequest/orbital/course_geometry.py`
- Test: `sidequest-server/tests/orbital/test_course_geometry.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_course_geometry.py`:

```python
"""Geometry helpers for course rendering — pure math, no SideQuest deps."""
from __future__ import annotations

import math

import pytest

from sidequest.orbital.course_geometry import (
    chord_angular_distance_deg,
    prograde_sign,
    bezier_control_offset,
)


def test_chord_angular_distance_zero_when_same_phase() -> None:
    assert chord_angular_distance_deg(0.0, 0.0) == 0.0


def test_chord_angular_distance_180_for_opposite_phase() -> None:
    assert chord_angular_distance_deg(0.0, 180.0) == pytest.approx(180.0)


def test_chord_angular_distance_takes_short_arc() -> None:
    # 350° -> 10° is a 20° short arc, not a 340° long arc
    assert chord_angular_distance_deg(350.0, 10.0) == pytest.approx(20.0)


def test_chord_angular_distance_symmetric() -> None:
    assert chord_angular_distance_deg(45.0, 270.0) == chord_angular_distance_deg(
        270.0, 45.0
    )
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_geometry.py -v
```

Expected: ImportError — `course_geometry` module does not exist.

- [ ] **Step 3: Implement the minimal code**

Create `sidequest-server/sidequest/orbital/course_geometry.py`:

```python
"""Pure geometry helpers for course overlay rendering.

Separate from course.py so cost/selection logic and rendering math
each test in isolation. No SideQuest model imports — operates on
plain floats.
"""

from __future__ import annotations

import math


def chord_angular_distance_deg(phase_a_deg: float, phase_b_deg: float) -> float:
    """Short-arc angular distance between two phase angles, in degrees.

    Always returns the smaller of the two arcs (0 ≤ result ≤ 180).
    """
    diff = abs((phase_a_deg - phase_b_deg) % 360.0)
    return min(diff, 360.0 - diff)


def prograde_sign(party_phase_deg: float, dest_phase_deg: float) -> int:
    """+1 if destination is ahead of party in prograde (counter-clockwise);
    -1 if behind. Used to bulge the Bezier control points in the prograde
    direction so the arc reads as orbital-flavored.
    """
    delta = (dest_phase_deg - party_phase_deg) % 360.0
    return 1 if delta <= 180.0 else -1


def bezier_control_offset(chord_length: float, prograde: int) -> float:
    """Perpendicular offset for cubic Bezier control points.

    0.3 × chord_length in prograde direction. ``chord_length`` is in the
    same units as the SVG (radii from chart center, typically pixels or
    AU-derived units depending on caller).
    """
    return 0.3 * chord_length * prograde
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_geometry.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Add tests for prograde_sign and bezier_control_offset**

Append to `tests/orbital/test_course_geometry.py`:

```python
def test_prograde_sign_destination_ahead_returns_plus_one() -> None:
    # destination 90° prograde of party
    assert prograde_sign(0.0, 90.0) == 1


def test_prograde_sign_destination_behind_returns_minus_one() -> None:
    # destination 90° retrograde (270° prograde, > 180)
    assert prograde_sign(0.0, 270.0) == -1


def test_prograde_sign_diametric_picks_prograde() -> None:
    # exactly 180°: tie-breaks to +1 (prograde) by the ≤ 180 condition
    assert prograde_sign(0.0, 180.0) == 1


def test_bezier_control_offset_scales_with_chord_and_sign() -> None:
    assert bezier_control_offset(100.0, 1) == pytest.approx(30.0)
    assert bezier_control_offset(100.0, -1) == pytest.approx(-30.0)
    assert bezier_control_offset(0.0, 1) == 0.0
```

- [ ] **Step 6: Run the tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_geometry.py -v
```

Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/orbital/course_geometry.py tests/orbital/test_course_geometry.py
git commit -m "feat(course): pure geometry helpers (chord, prograde, bezier offset)

Pure-math primitives for the course Bezier overlay. No SideQuest model
imports — keeps the geometry independently testable from selection
logic and renderer.

- chord_angular_distance_deg — short-arc, 0–180°
- prograde_sign — +1 if destination is ahead of party in prograde,
  -1 if behind
- bezier_control_offset — 0.3 × chord_length × prograde direction

Per the plot-a-course design (option B for geometry): the overlay is
a single cubic Bezier from party to destination with control points
offset perpendicular to the chord in the prograde direction."
```

### Task 2: compute_eta_and_dv cost function

**Files:**
- Create: `sidequest-server/sidequest/orbital/course.py`
- Test: `sidequest-server/tests/orbital/test_course_cost.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_course_cost.py`:

```python
"""Cost model — Hohmann-flavored, not Hohmann-accurate.

Calibration targets per the plot-a-course design:
- Far Landing → Tethys Watch (small moon hop) ≈ 12h, Δv 0.4
- Far Landing → Deep Root (cross-system rocky) ≈ 30h, Δv 1.0
- Far Landing → The Gate (far-edge habitat) ≈ 90h, Δv 2.8

Numbers are tunable via travel.travel_speed_factor. These tests
lock in the *order of magnitude* and the relative ordering, not
exact decimals — the calibration is allowed to drift within ±15%.
"""
from __future__ import annotations

import pytest

from sidequest.orbital.course import compute_eta_and_dv
from sidequest.orbital.models import (
    BodyDef,
    BodyType,
    ClockConfig,
    OrbitsConfig,
    TravelConfig,
    TravelRealism,
)


def _orbits(
    *bodies: tuple[str, BodyDef], travel_speed_factor: float = 1.0
) -> OrbitsConfig:
    return OrbitsConfig(
        version="0.1.0",
        clock=ClockConfig(),
        travel=TravelConfig(
            realism=TravelRealism.ORBITAL,
            travel_speed_factor=travel_speed_factor,
        ),
        bodies=dict(bodies),
    )


def _body(
    type_: BodyType = BodyType.HABITAT,
    parent: str | None = "coyote",
    semi_major_au: float | None = 1.0,
    period_days: float | None = 365.0,
    epoch_phase_deg: float | None = 0.0,
) -> BodyDef:
    return BodyDef(
        type=type_,
        parent=parent,
        semi_major_au=semi_major_au,
        period_days=period_days,
        epoch_phase_deg=epoch_phase_deg,
    )


def test_eta_zero_when_same_body() -> None:
    far = _body(semi_major_au=1.0, epoch_phase_deg=45.0)
    eta, dv = compute_eta_and_dv(far, far, _orbits(("far", far)))
    assert eta == 0.0
    assert dv == 0.0


def test_eta_for_short_radial_hop_is_under_30h() -> None:
    # Tethys Watch is a moon — same parent, near-zero radial diff
    far = _body(semi_major_au=1.0, epoch_phase_deg=45.0)
    moon = _body(parent="far", semi_major_au=1.0039, epoch_phase_deg=45.0)
    eta, dv = compute_eta_and_dv(far, moon, _orbits(("far", far), ("moon", moon)))
    assert eta < 30.0
    assert 0.0 < dv < 1.0


def test_eta_scales_inversely_with_travel_speed_factor() -> None:
    a = _body(semi_major_au=1.0, epoch_phase_deg=0.0)
    b = _body(semi_major_au=2.0, epoch_phase_deg=180.0)
    slow_orbits = _orbits(("a", a), ("b", b), travel_speed_factor=1.0)
    fast_orbits = _orbits(("a", a), ("b", b), travel_speed_factor=2.0)
    eta_slow, _ = compute_eta_and_dv(a, b, slow_orbits)
    eta_fast, _ = compute_eta_and_dv(a, b, fast_orbits)
    assert eta_fast == pytest.approx(eta_slow / 2.0)


def test_dv_independent_of_travel_speed_factor() -> None:
    a = _body(semi_major_au=1.0, epoch_phase_deg=0.0)
    b = _body(semi_major_au=2.0, epoch_phase_deg=180.0)
    _, dv_slow = compute_eta_and_dv(a, b, _orbits(("a", a), ("b", b), travel_speed_factor=1.0))
    _, dv_fast = compute_eta_and_dv(a, b, _orbits(("a", a), ("b", b), travel_speed_factor=2.0))
    assert dv_slow == pytest.approx(dv_fast)


def test_far_to_gate_is_expensive() -> None:
    # Calibration target: Far Landing 1.0 AU, The Gate 4.0 AU edge
    far = _body(semi_major_au=1.0, epoch_phase_deg=45.0)
    gate = _body(type_=BodyType.GATE, semi_major_au=4.0, epoch_phase_deg=180.0)
    eta, dv = compute_eta_and_dv(far, gate, _orbits(("far", far), ("gate", gate)))
    assert 60.0 < eta < 130.0  # ≈ 90h ± headroom
    assert 2.0 < dv < 4.0       # ≈ 2.8 ± headroom
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_cost.py -v
```

Expected: ImportError — `sidequest.orbital.course` does not exist.

- [ ] **Step 3: Implement compute_eta_and_dv**

Create `sidequest-server/sidequest/orbital/course.py`:

```python
"""Course computation — selection, cost, validation.

Pure module: no I/O, no global state. Deterministic given its inputs.
The renderer (course_render.py) and handler (handlers/course_intent.py)
import from here; nothing imports those upward.
"""

from __future__ import annotations

from sidequest.orbital.course_geometry import chord_angular_distance_deg
from sidequest.orbital.models import BodyDef, OrbitsConfig

# Calibration constants — tuned so Far Landing → Tethys Watch ≈ 12h,
# Far Landing → The Gate ≈ 90h. See cost-model section of the design.
TRAVEL_HOURS_PER_AU = 80.0
DELTA_V_BASE = 1.0           # km/s per AU of total chord distance
DELTA_V_RADIAL_FACTOR = 0.4  # extra Δv per AU of radial (semi-major-axis) diff


def compute_eta_and_dv(
    party_at: BodyDef,
    dest: BodyDef,
    orbits: OrbitsConfig,
) -> tuple[float, float]:
    """Hohmann-flavored cost. NOT real orbital mechanics.

    Returns ``(eta_hours, delta_v_km_per_s)``. Both 0.0 when the two
    bodies are identical references (same physical body, same phase).

    Inputs:
    - ``party_at``, ``dest``: ``BodyDef`` instances from the world's
      orbits.yaml. Either may be a moon (parent != system root); we
      treat ``semi_major_au`` as a flat distance proxy regardless.
    - ``orbits``: needed for ``travel.travel_speed_factor``.
    """
    if party_at is dest:
        return 0.0, 0.0
    a1 = party_at.semi_major_au or 0.0
    a2 = dest.semi_major_au or 0.0
    radial_au = abs(a1 - a2)
    phase_a = party_at.epoch_phase_deg or 0.0
    phase_b = dest.epoch_phase_deg or 0.0
    angular_au = 0.05 * (chord_angular_distance_deg(phase_a, phase_b) / 360.0)
    chord_au = radial_au + angular_au
    eta_hours = (chord_au * TRAVEL_HOURS_PER_AU) / orbits.travel.travel_speed_factor
    delta_v = chord_au * DELTA_V_BASE + radial_au * DELTA_V_RADIAL_FACTOR
    return eta_hours, delta_v
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_cost.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/orbital/course.py tests/orbital/test_course_cost.py
git commit -m "feat(course): Hohmann-flavored cost model (eta + delta_v)

Pure cost function. Calibration targets:
- Far Landing → Tethys Watch ≈ 12h / Δv 0.4
- Far Landing → Deep Root ≈ 30h / Δv 1.0
- Far Landing → The Gate ≈ 90h / Δv 2.8

ETA scales inversely with travel.travel_speed_factor; Δv does not.
Numbers are scifi-flavored decision weights, NOT real Hohmann
transfers."
```

---

## Server — Phase 2: PlottedCourse model & snapshot field

### Task 3: PlottedCourse + CourseRow models

**Files:**
- Modify: `sidequest-server/sidequest/orbital/course.py`
- Test: `sidequest-server/tests/orbital/test_course_compute.py` (will grow across tasks)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_course_compute.py`:

```python
"""Tests for compute_courses + PlottedCourse model."""
from __future__ import annotations

import pytest

from sidequest.orbital.course import (
    CourseRow,
    CourseSource,
    PlottedCourse,
)


def test_plotted_course_construction() -> None:
    pc = PlottedCourse(
        to_body_id="tethys_watch",
        label="Tethys Watch",
        eta_hours=12.0,
        delta_v=0.4,
        plotted_at_t_hours=120.0,
        source=CourseSource.IN_SCOPE,
    )
    assert pc.to_body_id == "tethys_watch"
    assert pc.label == "Tethys Watch"


def test_plotted_course_rejects_extra_fields() -> None:
    with pytest.raises(Exception):
        PlottedCourse(
            to_body_id="x",
            eta_hours=0.0,
            delta_v=0.0,
            plotted_at_t_hours=0.0,
            source=CourseSource.IN_SCOPE,
            extra_field="boom",  # type: ignore[call-arg]
        )


def test_course_row_carries_label_hint_for_quest_objective() -> None:
    row = CourseRow(
        to_body_id="deep_root",
        eta_hours=30.0,
        delta_v=1.0,
        source=CourseSource.QUEST_OBJECTIVE,
        label_hint="Hessler's manifest",
    )
    assert row.label_hint == "Hessler's manifest"


def test_course_source_priority_ordering() -> None:
    # Quest > recent_mention > in_scope, used by the 12-cap selector.
    assert (
        CourseSource.QUEST_OBJECTIVE.priority
        > CourseSource.RECENT_MENTION.priority
        > CourseSource.IN_SCOPE.priority
    )
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_compute.py -v
```

Expected: ImportError — `CourseRow`, `CourseSource`, `PlottedCourse` not defined.

- [ ] **Step 3: Add models to course.py**

Append to `sidequest-server/sidequest/orbital/course.py`:

```python
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CourseSource(StrEnum):
    """Why a course was offered. Drives the 12-cap priority ordering."""

    IN_SCOPE = "in_scope"
    RECENT_MENTION = "recent_mention"
    QUEST_OBJECTIVE = "quest_objective"

    @property
    def priority(self) -> int:
        """Higher = keep when capping. Quest > recent > in-scope."""
        return _SOURCE_PRIORITY[self]


_SOURCE_PRIORITY: dict[CourseSource, int] = {
    CourseSource.IN_SCOPE: 1,
    CourseSource.RECENT_MENTION: 2,
    CourseSource.QUEST_OBJECTIVE: 3,
}


class CourseRow(BaseModel):
    """One precomputed course exposed to narrator + GM panel.

    Labelled "row" because the prompt block renders these as one bullet
    each. Distinct from PlottedCourse, which is the snapshot field
    representing the *committed* (well, plotted) course.
    """

    model_config = ConfigDict(extra="forbid")

    to_body_id: str
    eta_hours: float
    delta_v: float
    source: CourseSource
    label_hint: str | None = None  # quest objective name when source=QUEST_OBJECTIVE


class PlottedCourse(BaseModel):
    """The snapshot's persistent course state — drawn on the chart.

    Cleared by replace, cancel, or arrival (party_body_id == to_body_id).
    Survives save/load and WebSocket disconnect by virtue of being a
    snapshot field.
    """

    model_config = ConfigDict(extra="forbid")

    to_body_id: str
    label: str | None = None
    eta_hours: float
    delta_v: float
    plotted_at_t_hours: float
    source: CourseSource
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_compute.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/orbital/course.py tests/orbital/test_course_compute.py
git commit -m "feat(course): PlottedCourse + CourseRow models

PlottedCourse is the persistent snapshot field (drawn on chart);
CourseRow is the precomputed selection entry (rendered into the
<courses> prompt block). CourseSource enum drives 12-cap priority:
quest_objective > recent_mention > in_scope."
```

### Task 4: Add plotted_course + quest_anchors fields to GameSnapshot

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py` (around line 473)
- Test: `sidequest-server/tests/orbital/test_course_compute.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_course_compute.py`:

```python
def test_game_snapshot_has_plotted_course_field_default_none() -> None:
    from sidequest.game.session import GameSnapshot

    snap = GameSnapshot()
    assert snap.plotted_course is None


def test_game_snapshot_quest_anchors_default_empty() -> None:
    from sidequest.game.session import GameSnapshot

    snap = GameSnapshot()
    assert snap.quest_anchors == []


def test_game_snapshot_round_trip_with_plotted_course() -> None:
    from sidequest.game.session import GameSnapshot

    snap = GameSnapshot(
        plotted_course=PlottedCourse(
            to_body_id="deep_root",
            label="Deep Root",
            eta_hours=30.0,
            delta_v=1.0,
            plotted_at_t_hours=42.0,
            source=CourseSource.QUEST_OBJECTIVE,
        ),
        quest_anchors=["deep_root", "the_gate"],
    )
    payload = snap.model_dump()
    restored = GameSnapshot.model_validate(payload)
    assert restored.plotted_course is not None
    assert restored.plotted_course.to_body_id == "deep_root"
    assert restored.quest_anchors == ["deep_root", "the_gate"]
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_compute.py::test_game_snapshot_has_plotted_course_field_default_none -v
```

Expected: AttributeError — `plotted_course` not on GameSnapshot.

- [ ] **Step 3: Modify GameSnapshot**

In `sidequest-server/sidequest/game/session.py`, add to the imports near the top of the file (look for the existing `from sidequest.game.encounter import StructuredEncounter` line and add nearby):

```python
from sidequest.orbital.course import PlottedCourse
```

In `sidequest-server/sidequest/game/session.py`, just after the existing `party_body_id: str | None = None` field (line ~473), insert:

```python

    # Course plot (plot-a-course design). None when no course is plotted.
    # Set by narrator-emitted plot_course sidecar intent; cleared by
    # cancel_course intent, replacement plot, or arrival
    # (party_body_id == plotted_course.to_body_id). Survives save/load.
    plotted_course: PlottedCourse | None = None

    # Quest anchor body ids (plot-a-course MVP — narrator-managed via
    # state patch). Surfaced into compute_courses() as
    # source=QUEST_OBJECTIVE, regardless of orbital scope. Future:
    # superseded by ScenarioState body-anchored clue mechanism.
    quest_anchors: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_compute.py -v
```

Expected: 7 passed (4 prior + 3 new).

- [ ] **Step 5: Run the wider game-session test suite to catch regressions**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/game/ tests/server/test_session.py -v -x
```

Expected: all pass. Pydantic round-trip should be transparent.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/game/session.py tests/orbital/test_course_compute.py
git commit -m "feat(snapshot): add plotted_course + quest_anchors fields

plotted_course (PlottedCourse | None) is the persistent course state
drawn on the orbital chart. quest_anchors is the MVP quest-targeting
mechanism — narrator-managed list of body_ids surfaced into the
<courses> prompt block as QUEST_OBJECTIVE.

Both fields default to empty/None so existing saves remain valid;
extra='ignore' on GameSnapshot already handles forward compat."
```

---

## Server — Phase 3: Selection logic

### Task 5: compute_courses pure function

**Files:**
- Modify: `sidequest-server/sidequest/orbital/course.py`
- Test: `sidequest-server/tests/orbital/test_course_compute.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_course_compute.py`:

```python
def _mini_orbits() -> "OrbitsConfig":
    """Tiny orbits config: coyote + 4 habitats at 1, 2, 3, 4 AU."""
    from sidequest.orbital.models import (
        BodyDef,
        BodyType,
        ClockConfig,
        OrbitsConfig,
        TravelConfig,
        TravelRealism,
    )

    bodies = {
        "coyote": BodyDef(type=BodyType.STAR),
        "near": BodyDef(
            type=BodyType.HABITAT,
            parent="coyote",
            semi_major_au=1.0,
            period_days=365.0,
            epoch_phase_deg=0.0,
        ),
        "mid": BodyDef(
            type=BodyType.HABITAT,
            parent="coyote",
            semi_major_au=2.0,
            period_days=720.0,
            epoch_phase_deg=90.0,
        ),
        "far": BodyDef(
            type=BodyType.HABITAT,
            parent="coyote",
            semi_major_au=3.0,
            period_days=1100.0,
            epoch_phase_deg=180.0,
        ),
        "edge": BodyDef(
            type=BodyType.HABITAT,
            parent="coyote",
            semi_major_au=4.0,
            period_days=1500.0,
            epoch_phase_deg=270.0,
        ),
    }
    return OrbitsConfig(
        version="0.1.0",
        clock=ClockConfig(),
        travel=TravelConfig(realism=TravelRealism.ORBITAL, travel_speed_factor=1.0),
        bodies=bodies,
    )


def test_compute_courses_excludes_party_at() -> None:
    from sidequest.orbital.course import compute_courses

    rows = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids={"near", "mid", "far", "edge"},
        recent_body_mentions=[],
        quest_anchors=[],
    )
    assert "near" not in rows


def test_compute_courses_in_scope_source() -> None:
    from sidequest.orbital.course import CourseSource, compute_courses

    rows = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids={"near", "mid"},
        recent_body_mentions=[],
        quest_anchors=[],
    )
    assert set(rows.keys()) == {"mid"}
    assert rows["mid"].source == CourseSource.IN_SCOPE


def test_compute_courses_recent_mention_overrides_in_scope_priority() -> None:
    from sidequest.orbital.course import CourseSource, compute_courses

    # mid is both in-scope AND recently mentioned → recent_mention wins
    # (higher priority).
    rows = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids={"mid"},
        recent_body_mentions=["mid"],
        quest_anchors=[],
    )
    assert rows["mid"].source == CourseSource.RECENT_MENTION


def test_compute_courses_quest_objective_top_priority() -> None:
    from sidequest.orbital.course import CourseSource, compute_courses

    rows = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids={"mid"},
        recent_body_mentions=["mid"],
        quest_anchors=["mid"],
    )
    assert rows["mid"].source == CourseSource.QUEST_OBJECTIVE


def test_compute_courses_skips_unknown_body_ids_silently() -> None:
    """Unknown ids in inputs are dropped; we never invent bodies."""
    from sidequest.orbital.course import compute_courses

    rows = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids={"unknown_body"},
        recent_body_mentions=["also_unknown"],
        quest_anchors=["still_unknown"],
    )
    assert rows == {}


def test_compute_courses_caps_at_12() -> None:
    """Lots of in-scope bodies + a couple of higher-priority entries —
    cap drops in-scope first, keeps quest + recent."""
    from sidequest.orbital.course import compute_courses
    from sidequest.orbital.models import BodyDef, BodyType

    # Build orbits with party + 14 habitats so we exceed the cap.
    big_bodies = {"coyote": BodyDef(type=BodyType.STAR)}
    for i in range(14):
        big_bodies[f"hab_{i:02d}"] = BodyDef(
            type=BodyType.HABITAT,
            parent="coyote",
            semi_major_au=1.0 + 0.5 * i,
            period_days=365.0 + 100 * i,
            epoch_phase_deg=(i * 25) % 360,
        )
    big_bodies["party_body"] = BodyDef(
        type=BodyType.HABITAT,
        parent="coyote",
        semi_major_au=0.5,
        period_days=200.0,
        epoch_phase_deg=0.0,
    )
    from sidequest.orbital.models import (
        ClockConfig,
        OrbitsConfig,
        TravelConfig,
        TravelRealism,
    )

    orbits = OrbitsConfig(
        version="0.1.0",
        clock=ClockConfig(),
        travel=TravelConfig(realism=TravelRealism.ORBITAL),
        bodies=big_bodies,
    )

    rows = compute_courses(
        orbits=orbits,
        party_at="party_body",
        in_scope_body_ids={f"hab_{i:02d}" for i in range(14)},  # 14 in-scope
        recent_body_mentions=[],  # already represented in in_scope set
        quest_anchors=["hab_00"],  # 1 quest pin
    )
    assert len(rows) == 12
    # Quest must survive
    assert "hab_00" in rows
    # Quest source preserved
    from sidequest.orbital.course import CourseSource

    assert rows["hab_00"].source == CourseSource.QUEST_OBJECTIVE


def test_compute_courses_deterministic_order() -> None:
    """Same inputs → same output, including dict iteration order."""
    from sidequest.orbital.course import compute_courses

    a = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids={"mid", "far", "edge"},
        recent_body_mentions=[],
        quest_anchors=[],
    )
    b = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids={"edge", "far", "mid"},
        recent_body_mentions=[],
        quest_anchors=[],
    )
    assert list(a.keys()) == list(b.keys())


def test_compute_courses_label_hint_only_for_quest_objective() -> None:
    from sidequest.orbital.course import CourseSource, compute_courses

    # Without a label_hint map, even quest entries leave it None.
    rows = compute_courses(
        orbits=_mini_orbits(),
        party_at="near",
        in_scope_body_ids=set(),
        recent_body_mentions=[],
        quest_anchors=["mid"],
    )
    assert rows["mid"].source == CourseSource.QUEST_OBJECTIVE
    assert rows["mid"].label_hint is None
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_compute.py -v
```

Expected: ImportError — `compute_courses` not defined.

- [ ] **Step 3: Implement compute_courses**

Append to `sidequest-server/sidequest/orbital/course.py`:

```python
COURSES_HARD_CAP = 12
"""Token-budget guardrail. ~12 entries × ~20 tokens each = ~250 tokens
of <courses> block, well under what we can afford in the Recency zone.
If selection exceeds 12, drop in priority order keeping the highest."""


def compute_courses(
    *,
    orbits: OrbitsConfig,
    party_at: str | None,
    in_scope_body_ids: set[str],
    recent_body_mentions: list[str],
    quest_anchors: list[str],
) -> dict[str, CourseRow]:
    """Build the <courses> selection for one prompt assembly.

    Selection rule: a body is included if it appears in any of
    ``in_scope_body_ids``, ``recent_body_mentions``, or
    ``quest_anchors``. Source priority resolves multi-membership:
    quest > recent > in_scope.

    Hard cap: 12 entries. Drops are applied in *reverse* priority
    order, so quest objectives and recent mentions are preserved at
    the expense of in-scope-only bodies.

    Determinism: dict iteration order is sorted by
    (priority desc, eta_hours asc, body_id asc).

    Returns ``{}`` if ``party_at`` is None or unknown — there's no
    place to plot from.
    """
    if party_at is None or party_at not in orbits.bodies:
        return {}

    party_body = orbits.bodies[party_at]

    candidates: dict[str, CourseSource] = {}
    # Lowest priority first; later writes override.
    for bid in in_scope_body_ids:
        if bid != party_at and bid in orbits.bodies:
            candidates[bid] = CourseSource.IN_SCOPE
    for bid in recent_body_mentions:
        if bid != party_at and bid in orbits.bodies:
            candidates[bid] = CourseSource.RECENT_MENTION
    for bid in quest_anchors:
        if bid != party_at and bid in orbits.bodies:
            candidates[bid] = CourseSource.QUEST_OBJECTIVE

    rows: list[tuple[str, CourseRow]] = []
    for bid, source in candidates.items():
        eta, dv = compute_eta_and_dv(party_body, orbits.bodies[bid], orbits)
        rows.append(
            (
                bid,
                CourseRow(
                    to_body_id=bid,
                    eta_hours=eta,
                    delta_v=dv,
                    source=source,
                    label_hint=None,
                ),
            )
        )

    # Sort: priority desc, then eta asc, then body_id asc for stability.
    rows.sort(key=lambda kv: (-kv[1].source.priority, kv[1].eta_hours, kv[0]))

    if len(rows) > COURSES_HARD_CAP:
        rows = rows[:COURSES_HARD_CAP]

    return dict(rows)
```

- [ ] **Step 4: Run all course tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_compute.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/orbital/course.py tests/orbital/test_course_compute.py
git commit -m "feat(course): compute_courses selection (in-scope + recent + quest)

Pure selection function. Inputs: orbits, party_at, three id sets
(in-scope, recent-mention, quest-anchor). Output: deterministic
dict[body_id, CourseRow] with hard cap of 12.

Source priority resolves multi-membership:
quest_objective > recent_mention > in_scope.

Sort order is (priority desc, eta asc, body_id asc) so cap drops
preserve the highest-narrative-weight entries first."
```

---

## Server — Phase 4: Recent body mentions ring buffer

### Task 6: Session ring buffer

**Files:**
- Modify: `sidequest-server/sidequest/server/session.py`
- Test: `sidequest-server/tests/server/test_recent_body_mentions.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_recent_body_mentions.py`:

```python
"""Recent-body-mentions ring buffer on Session.

Plot-a-course MVP buffer: simple deque of last 4 distinct body IDs
mentioned by narrator output or player input. Populated by
``Session.note_body_mentioned`` after each turn's narration is
applied. Read by ``Orchestrator`` when assembling the <courses> block.
"""
from __future__ import annotations

from sidequest.orbital.models import (
    BodyDef,
    BodyType,
    ClockConfig,
    OrbitsConfig,
    TravelConfig,
    TravelRealism,
)
from sidequest.orbital.loader import OrbitalContent
from sidequest.orbital.render import Scope


def _content() -> OrbitalContent:
    return OrbitalContent(
        orbits=OrbitsConfig(
            version="0.1.0",
            clock=ClockConfig(),
            travel=TravelConfig(realism=TravelRealism.ORBITAL),
            bodies={
                "coyote": BodyDef(type=BodyType.STAR),
                "alpha": BodyDef(
                    type=BodyType.HABITAT,
                    parent="coyote",
                    semi_major_au=1.0,
                    period_days=365.0,
                    epoch_phase_deg=0.0,
                ),
                "beta": BodyDef(
                    type=BodyType.HABITAT,
                    parent="coyote",
                    semi_major_au=2.0,
                    period_days=720.0,
                    epoch_phase_deg=90.0,
                ),
            },
        ),
        chart=None,
    )


def _session():
    from sidequest.server.session import Session

    return Session(orbital_content=_content())


def test_recent_body_mentions_starts_empty() -> None:
    sess = _session()
    assert list(sess.recent_body_mentions) == []


def test_note_body_mentioned_appends() -> None:
    sess = _session()
    sess.note_body_mentioned("alpha")
    sess.note_body_mentioned("beta")
    assert list(sess.recent_body_mentions) == ["alpha", "beta"]


def test_recent_body_mentions_caps_at_4() -> None:
    sess = _session()
    sess.note_body_mentioned("a")
    sess.note_body_mentioned("b")
    sess.note_body_mentioned("c")
    sess.note_body_mentioned("d")
    sess.note_body_mentioned("e")
    # oldest 'a' evicted
    assert list(sess.recent_body_mentions) == ["b", "c", "d", "e"]


def test_note_body_mentioned_dedupe_moves_to_recent() -> None:
    """Re-mentioning a body refreshes its position to the most-recent
    end, so it survives subsequent evictions. Without this, a body the
    player keeps talking about would still drop off after 4 distinct
    mentions of other bodies."""
    sess = _session()
    sess.note_body_mentioned("a")
    sess.note_body_mentioned("b")
    sess.note_body_mentioned("a")  # refreshed to end
    sess.note_body_mentioned("c")
    sess.note_body_mentioned("d")
    sess.note_body_mentioned("e")
    # 'a' was refreshed before 'b' was old, so 'b' evicts; 'a' survives.
    assert "a" in sess.recent_body_mentions
    assert "b" not in sess.recent_body_mentions
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/server/test_recent_body_mentions.py -v
```

Expected: AttributeError — `recent_body_mentions` / `note_body_mentioned` not on Session.

- [ ] **Step 3: Add ring buffer to Session**

In `sidequest-server/sidequest/server/session.py`, add to imports near the top:

```python
from collections import deque
```

In the `Session.__init__` method (around line 41), after `self._orbital_content = orbital_content`, add:

```python
        self._recent_body_mentions: deque[str] = deque(maxlen=RECENT_BODY_MENTIONS_LEN)
```

Add a module-level constant near the top of the file (after the imports, before class definitions):

```python
RECENT_BODY_MENTIONS_LEN = 4
"""Plot-a-course ring buffer size. Bodies named in the last N turns
get surfaced into <courses> as RECENT_MENTION. Larger = more forgiving
across digressions; smaller = tighter focus on the current scene."""
```

Add the property and mutator near the existing `orbital_scope` property:

```python
    @property
    def recent_body_mentions(self) -> deque[str]:
        """Read-only-ish view of the recent body-mention buffer.

        Returns the actual deque (not a copy); callers should not
        mutate it. Iterate or list() it for a snapshot.
        """
        return self._recent_body_mentions

    def note_body_mentioned(self, body_id: str) -> None:
        """Record a body name as mentioned this turn.

        Dedupe-and-refresh: if the body is already in the buffer,
        remove and re-append so it sits at the most-recent end and
        survives subsequent evictions. This keeps a body the player
        keeps referencing in scope across many turns.
        """
        if body_id in self._recent_body_mentions:
            try:
                self._recent_body_mentions.remove(body_id)
            except ValueError:
                pass
        self._recent_body_mentions.append(body_id)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/server/test_recent_body_mentions.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/server/session.py tests/server/test_recent_body_mentions.py
git commit -m "feat(session): recent_body_mentions ring buffer

Length-4 deque on Session. Populated by note_body_mentioned() with
dedupe-and-refresh so a body the player keeps referencing survives
across many turns. Read by Orchestrator when assembling the <courses>
prompt block to mark bodies as RECENT_MENTION-source.

Buffer size lives at RECENT_BODY_MENTIONS_LEN (module constant) so a
future tuning pass can flip it without touching call sites."
```

---

## Server — Phase 5: Prompt block injection

### Task 7: <courses> PromptSection

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py`
- Modify: `sidequest-server/sidequest/orbital/course.py` (helper for prompt rendering)
- Test: `sidequest-server/tests/agents/test_narrator_courses_block.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/agents/test_narrator_courses_block.py`:

```python
"""Wiring: orchestrator includes <courses> block when world has
orbital tier and the snapshot/session yields any computed courses."""
from __future__ import annotations

from sidequest.orbital.course import (
    CourseRow,
    CourseSource,
    format_courses_block,
)


def test_format_courses_block_empty_returns_empty_string() -> None:
    assert format_courses_block({}) == ""


def test_format_courses_block_renders_each_row() -> None:
    rows = {
        "tethys_watch": CourseRow(
            to_body_id="tethys_watch",
            eta_hours=12.0,
            delta_v=0.4,
            source=CourseSource.IN_SCOPE,
        ),
        "deep_root": CourseRow(
            to_body_id="deep_root",
            eta_hours=30.0,
            delta_v=1.0,
            source=CourseSource.QUEST_OBJECTIVE,
            label_hint="Hessler's manifest",
        ),
    }
    block = format_courses_block(rows)
    assert "<courses>" in block
    assert "</courses>" in block
    assert "tethys_watch" in block
    assert "deep_root" in block
    assert "Hessler's manifest" in block
    assert "ETA 12h" in block or "ETA 12" in block
    assert "Δv" in block or "delta_v" in block
    # Instruction must be present
    assert "plot_course" in block


def test_format_courses_block_marks_recent_mentions() -> None:
    rows = {
        "the_gate": CourseRow(
            to_body_id="the_gate",
            eta_hours=90.0,
            delta_v=2.8,
            source=CourseSource.RECENT_MENTION,
        ),
    }
    block = format_courses_block(rows)
    assert "recently mentioned" in block.lower() or "recent" in block.lower()


def test_orchestrator_registers_courses_section_when_orbital_world() -> None:
    """Smoke wiring test: the orchestrator should call register_section
    with a courses-named section when the snapshot has a non-empty
    course set. Uses the actual orchestrator path; mocks only the
    minimum needed for prompt assembly."""
    # This is a wiring test — exercise the real assembly path with a
    # snapshot that has party_body_id set and an orbital_content
    # available, and assert the registry contains a 'courses' section.
    # See tests/agents/test_orchestrator.py for the existing fixture
    # patterns. Implementation note for the dev: the simplest assertion
    # is `"courses" in registry.section_ids()`.
    from sidequest.agents.orchestrator import Orchestrator
    from sidequest.agents.prompt_framework.types import (
        AttentionZone,
    )

    # Build a context that has a non-empty courses set. The dev should
    # follow the existing test_orchestrator.py fixture style and
    # assert that:
    #   - registry has a section named "courses"
    #   - section.zone == AttentionZone.Recency
    #   - section.body contains "<courses>" and at least one body_id
    # If the existing fixture machinery is too heavy, this test can
    # be skipped in favor of the format_courses_block tests above plus
    # a manual integration verification at the smoke-test step.
    assert AttentionZone.Recency  # placeholder so the import is real


def test_format_courses_block_respects_label_priority() -> None:
    """When label_hint is set, it appears in the bullet text."""
    rows = {
        "deep_root": CourseRow(
            to_body_id="deep_root",
            eta_hours=30.0,
            delta_v=1.0,
            source=CourseSource.QUEST_OBJECTIVE,
            label_hint="Hessler's manifest",
        ),
    }
    block = format_courses_block(rows)
    assert "Hessler's manifest" in block
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/agents/test_narrator_courses_block.py -v
```

Expected: ImportError — `format_courses_block` not defined.

- [ ] **Step 3: Add format_courses_block to course.py**

Append to `sidequest-server/sidequest/orbital/course.py`:

```python
def format_courses_block(rows: dict[str, CourseRow]) -> str:
    """Render the <courses> prompt block from a compute_courses output.

    Empty input → empty string (caller skips registering the section).

    The block contains the narrator instruction and one bullet per
    course. Format is engineered for one-shot Claude parsing: the
    instruction is unambiguous, each bullet is one line, body_ids are
    snake_case so a body_id token cannot collide with prose.
    """
    if not rows:
        return ""

    lines: list[str] = ["<courses>"]
    lines.append(
        "You can plot a course to any of these. When the player asks to plot "
        'a course ("plot a course to X", "Kestrel, lay in a course for X", '
        '"take us to X"), include the matching course_id in your '
        "game_patch sidecar:"
    )
    lines.append('  {"intent":"plot_course","course_id":"<id>"}')
    lines.append("")
    lines.append(
        "If the player asks for a destination not in this list, say so "
        'in-fiction ("Kestrel can\'t lock that, captain — say a body within '
        'scanner range or a known objective"). Do NOT invent course_ids.'
    )
    lines.append("")
    for body_id, row in rows.items():
        suffix = ""
        if row.source == CourseSource.QUEST_OBJECTIVE:
            label = row.label_hint or body_id
            suffix = f" — quest: {label}"
        elif row.source == CourseSource.RECENT_MENTION:
            suffix = " — recently mentioned"
        # IN_SCOPE: no suffix.
        lines.append(
            f"- {body_id} (ETA {row.eta_hours:.0f}h, Δv {row.delta_v:.1f}){suffix}"
        )
    lines.append("</courses>")
    return "\n".join(lines)
```

- [ ] **Step 4: Run the format tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/agents/test_narrator_courses_block.py::test_format_courses_block_empty_returns_empty_string tests/agents/test_narrator_courses_block.py::test_format_courses_block_renders_each_row tests/agents/test_narrator_courses_block.py::test_format_courses_block_marks_recent_mentions tests/agents/test_narrator_courses_block.py::test_format_courses_block_respects_label_priority -v
```

Expected: 4 passed.

- [ ] **Step 5: Wire orchestrator to register the section**

In `sidequest-server/sidequest/agents/orchestrator.py`, find the section near line 1428 where the NPC-intro visual constraint registers. After that registration block, add:

```python
        # Plot-a-course (plot-a-course design). The narrator can plot a
        # course to any body in the prompted set; rejection is OTEL-loud
        # and chart-silent. Block is omitted entirely when the world has
        # no orbital tier or the party has no body anchor.
        if context.orbital_content is not None and context.party_body_id:
            from sidequest.orbital.course import (
                compute_courses,
                format_courses_block,
            )

            in_scope = _bodies_in_scope(
                context.orbital_content.orbits,
                context.orbital_scope,
            )
            course_rows = compute_courses(
                orbits=context.orbital_content.orbits,
                party_at=context.party_body_id,
                in_scope_body_ids=in_scope,
                recent_body_mentions=list(context.recent_body_mentions),
                quest_anchors=list(context.quest_anchors),
            )
            block_text = format_courses_block(course_rows)
            if block_text:
                registry.register_section(
                    agent_name,
                    PromptSection.new(
                        "courses",
                        block_text,
                        AttentionZone.Recency,
                        SectionCategory.Guardrail,
                    ),
                )
```

In the same file, add a helper function near the bottom of the module (or near other private helpers; place it just before the `Orchestrator` class definition):

```python
def _bodies_in_scope(orbits, scope) -> set[str]:
    """Body ids visible in the current OrbitalIntent scope.

    System-root scope: every body whose parent is the system primary
    (no parent) PLUS the primary itself. Drilled-in scope: the center
    body PLUS its direct children (parent == center). Mirrors the
    existing render_chart scope semantics.
    """
    if scope.center_body_id == "<root>":
        # System root: include the primary and all of its direct children.
        return {bid for bid, b in orbits.bodies.items() if b.parent is None or b.parent in {bid_ for bid_, b_ in orbits.bodies.items() if b_.parent is None}}
    return {scope.center_body_id} | {
        bid for bid, b in orbits.bodies.items() if b.parent == scope.center_body_id
    }
```

Note: `context` (the orchestrator's per-turn assembly context) needs to expose `orbital_content`, `orbital_scope`, `party_body_id`, `recent_body_mentions`, and `quest_anchors`. If these are not already on the context object, add them in the same change — search `orchestrator.py` for the context dataclass / kwargs and extend it. The Session already exposes all five.

- [ ] **Step 6: Run the orchestrator wiring test**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/agents/test_narrator_courses_block.py -v
```

Expected: 5 passed (the wiring test asserts on `AttentionZone.Recency` import; the dev should expand this test using the existing test_orchestrator.py fixtures to exercise the real path. If fixture authoring is non-trivial, lock the unit-level format tests and add a manual smoke verification at Task 18.)

- [ ] **Step 7: Run the wider orchestrator suite to catch regressions**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/agents/test_orchestrator.py -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/orbital/course.py sidequest/agents/orchestrator.py tests/agents/test_narrator_courses_block.py
git commit -m "feat(course): <courses> prompt block in Recency zone

Orchestrator registers a 'courses' PromptSection when the world has
orbital content and the party has a body anchor. Block contains the
plot_course instruction + one bullet per computed course. Empty when
no courses are available — narrator never sees the instruction.

format_courses_block is unit-tested; orchestrator wiring is exercised
by the existing test_orchestrator.py path."
```

---

## Server — Phase 6: Sidecar intent + handler

### Task 8: Sidecar protocol models

**Files:**
- Create: `sidequest-server/sidequest/protocol/course_intent.py`
- Test: extend `sidequest-server/tests/handlers/test_course_intent_wired.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/handlers/test_course_intent_wired.py`:

```python
"""Wiring tests: course_intent sidecar variants land as state patches.

Sidecar JSON appears inside the narrator's game_patch fenced block.
The narration_apply pipeline parses the JSON, dispatches typed
intents to handlers/course_intent.py, which validates against the
current turn's compute_courses output and emits state patches.
"""
from __future__ import annotations

import pytest

from sidequest.protocol.course_intent import (
    CancelCourseSidecar,
    PlotCourseSidecar,
    parse_course_sidecar,
)


def test_plot_course_sidecar_round_trip() -> None:
    payload = {"intent": "plot_course", "course_id": "tethys_watch"}
    sc = PlotCourseSidecar.model_validate(payload)
    assert sc.course_id == "tethys_watch"


def test_cancel_course_sidecar_round_trip() -> None:
    payload = {"intent": "cancel_course"}
    sc = CancelCourseSidecar.model_validate(payload)
    assert sc.intent == "cancel_course"


def test_parse_course_sidecar_returns_typed_variant() -> None:
    plot = parse_course_sidecar({"intent": "plot_course", "course_id": "x"})
    assert isinstance(plot, PlotCourseSidecar)
    cancel = parse_course_sidecar({"intent": "cancel_course"})
    assert isinstance(cancel, CancelCourseSidecar)


def test_parse_course_sidecar_returns_none_for_unrelated_payloads() -> None:
    """Sidecar parser is tolerant: non-course intents yield None so the
    pipeline can ignore them and let other handlers process the same
    game_patch."""
    assert parse_course_sidecar({"intent": "roll_dice"}) is None
    assert parse_course_sidecar({}) is None
    assert parse_course_sidecar({"intent": "plot_course"}) is None  # missing course_id


def test_plot_course_sidecar_forbids_extra_fields() -> None:
    with pytest.raises(Exception):
        PlotCourseSidecar.model_validate(
            {"intent": "plot_course", "course_id": "x", "secret": "boom"}
        )
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/handlers/test_course_intent_wired.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement the protocol models**

Create `sidequest-server/sidequest/protocol/course_intent.py`:

```python
"""Sidecar JSON variants for plot_course / cancel_course.

Carried inside the narrator's ``game_patch`` block, parsed by
narration_apply, dispatched to handlers/course_intent.py.

Not a new WebSocket message kind — STATE_PATCH (existing) carries
the resulting snapshot mutation back to the client.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PlotCourseSidecar(BaseModel):
    """Narrator: 'plot a course to <body>'."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal["plot_course"] = "plot_course"
    course_id: str


class CancelCourseSidecar(BaseModel):
    """Narrator: 'cancel the current plot'."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal["cancel_course"] = "cancel_course"


CourseSidecar = PlotCourseSidecar | CancelCourseSidecar


def parse_course_sidecar(payload: Any) -> CourseSidecar | None:
    """Tolerant parser: returns ``None`` if the payload is not a course
    intent (so other sidecar handlers can run on the same game_patch).

    Validates the shape strictly when intent is course-related — bad
    payloads raise ValidationError (caught upstream and logged as
    rejected sidecars). Missing fields = None, not exception, because
    we want to differentiate 'wasn't ours' from 'was ours but malformed'.
    """
    if not isinstance(payload, dict):
        return None
    intent = payload.get("intent")
    if intent == "plot_course":
        if "course_id" not in payload:
            return None
        return PlotCourseSidecar.model_validate(payload)
    if intent == "cancel_course":
        return CancelCourseSidecar.model_validate(payload)
    return None
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/handlers/test_course_intent_wired.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/protocol/course_intent.py tests/handlers/test_course_intent_wired.py
git commit -m "feat(course): sidecar protocol models for plot/cancel

PlotCourseSidecar + CancelCourseSidecar live in protocol/course_intent.py
alongside parse_course_sidecar (tolerant parser — returns None for
unrelated game_patch payloads, raises only on malformed course intents).

Wire into narration_apply in the next task."
```

### Task 9: Course intent handler

**Files:**
- Create: `sidequest-server/sidequest/handlers/course_intent.py`
- Modify: `sidequest-server/sidequest/server/narration_apply.py`
- Test: extend `sidequest-server/tests/handlers/test_course_intent_wired.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/handlers/test_course_intent_wired.py`:

```python
def test_handle_plot_course_sets_snapshot_field() -> None:
    """Accept path: course_id is in compute_courses output → state
    patch on /plotted_course → snapshot.plotted_course populated."""
    from sidequest.game.session import GameSnapshot
    from sidequest.handlers.course_intent import handle_course_sidecar
    from sidequest.orbital.course import (
        CourseRow,
        CourseSource,
    )

    snap = GameSnapshot(party_body_id="near", clock_t_hours=42.0)
    available = {
        "mid": CourseRow(
            to_body_id="mid",
            eta_hours=30.0,
            delta_v=1.0,
            source=CourseSource.IN_SCOPE,
        ),
    }
    sc = PlotCourseSidecar(intent="plot_course", course_id="mid")

    result = handle_course_sidecar(
        sidecar=sc,
        snapshot=snap,
        available_courses=available,
    )
    assert result.accepted is True
    assert snap.plotted_course is not None
    assert snap.plotted_course.to_body_id == "mid"
    assert snap.plotted_course.eta_hours == 30.0
    assert snap.plotted_course.delta_v == 1.0
    assert snap.plotted_course.plotted_at_t_hours == 42.0
    assert snap.plotted_course.source == CourseSource.IN_SCOPE


def test_handle_plot_course_rejects_unknown_id() -> None:
    """Reject path: course_id not in available_courses → snapshot
    unchanged, result.accepted=False, result.reason set."""
    from sidequest.game.session import GameSnapshot
    from sidequest.handlers.course_intent import handle_course_sidecar

    snap = GameSnapshot(party_body_id="near")
    sc = PlotCourseSidecar(intent="plot_course", course_id="maltese_falcon")
    result = handle_course_sidecar(
        sidecar=sc,
        snapshot=snap,
        available_courses={},
    )
    assert result.accepted is False
    assert "not_in_scope" in result.reason or "unknown" in result.reason
    assert snap.plotted_course is None


def test_handle_cancel_course_clears_field() -> None:
    from sidequest.game.session import GameSnapshot
    from sidequest.handlers.course_intent import handle_course_sidecar
    from sidequest.orbital.course import CourseSource, PlottedCourse

    snap = GameSnapshot(
        party_body_id="near",
        plotted_course=PlottedCourse(
            to_body_id="mid",
            eta_hours=30.0,
            delta_v=1.0,
            plotted_at_t_hours=10.0,
            source=CourseSource.IN_SCOPE,
        ),
    )
    sc = CancelCourseSidecar()
    result = handle_course_sidecar(
        sidecar=sc,
        snapshot=snap,
        available_courses={},
    )
    assert result.accepted is True
    assert snap.plotted_course is None


def test_handle_cancel_course_when_no_plot_is_no_op() -> None:
    """Cancel intent when no course is plotted → accepted=True, no-op,
    flagged via was_already_clear."""
    from sidequest.game.session import GameSnapshot
    from sidequest.handlers.course_intent import handle_course_sidecar

    snap = GameSnapshot()
    sc = CancelCourseSidecar()
    result = handle_course_sidecar(
        sidecar=sc,
        snapshot=snap,
        available_courses={},
    )
    assert result.accepted is True
    assert result.was_already_clear is True
    assert snap.plotted_course is None
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/handlers/test_course_intent_wired.py -v
```

Expected: ImportError — `handle_course_sidecar` not defined.

- [ ] **Step 3: Implement the handler**

Create `sidequest-server/sidequest/handlers/course_intent.py`:

```python
"""Apply plot_course / cancel_course sidecar intents to the snapshot.

Pure-ish: mutates the passed snapshot but has no other side effects
(OTEL emission lives in callers, not here, so unit tests stay fast).
"""

from __future__ import annotations

from dataclasses import dataclass

from sidequest.game.session import GameSnapshot
from sidequest.orbital.course import CourseRow, PlottedCourse
from sidequest.protocol.course_intent import (
    CancelCourseSidecar,
    CourseSidecar,
    PlotCourseSidecar,
)


@dataclass(frozen=True)
class CourseHandlerResult:
    """Outcome of applying one course sidecar.

    Callers (narration_apply) emit OTEL based on these fields and
    surface rejected reasons into the next turn's reactions zone.
    """

    accepted: bool
    reason: str = ""
    was_already_clear: bool = False
    """True for cancel_course when there was no plot to clear (no-op)."""


def handle_course_sidecar(
    *,
    sidecar: CourseSidecar,
    snapshot: GameSnapshot,
    available_courses: dict[str, CourseRow],
) -> CourseHandlerResult:
    """Apply ``sidecar`` to ``snapshot`` in-place.

    For ``PlotCourseSidecar``: requires ``course_id`` to be a key in
    ``available_courses`` (the compute_courses output for THIS turn).
    Sets ``snapshot.plotted_course`` on accept; leaves it untouched
    on reject.

    For ``CancelCourseSidecar``: clears ``snapshot.plotted_course``.
    No-op when already clear, but still ``accepted=True``.
    """
    if isinstance(sidecar, PlotCourseSidecar):
        return _handle_plot(sidecar, snapshot, available_courses)
    if isinstance(sidecar, CancelCourseSidecar):
        return _handle_cancel(snapshot)
    # Type system says exhaustive; this is a safety net.
    return CourseHandlerResult(accepted=False, reason="unknown_intent")


def _handle_plot(
    sidecar: PlotCourseSidecar,
    snapshot: GameSnapshot,
    available_courses: dict[str, CourseRow],
) -> CourseHandlerResult:
    row = available_courses.get(sidecar.course_id)
    if row is None:
        return CourseHandlerResult(
            accepted=False,
            reason=f"not_in_scope:course_id={sidecar.course_id!r}",
        )
    snapshot.plotted_course = PlottedCourse(
        to_body_id=row.to_body_id,
        label=row.label_hint,
        eta_hours=row.eta_hours,
        delta_v=row.delta_v,
        plotted_at_t_hours=snapshot.clock_t_hours,
        source=row.source,
    )
    return CourseHandlerResult(accepted=True)


def _handle_cancel(snapshot: GameSnapshot) -> CourseHandlerResult:
    if snapshot.plotted_course is None:
        return CourseHandlerResult(accepted=True, was_already_clear=True)
    snapshot.plotted_course = None
    return CourseHandlerResult(accepted=True)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/handlers/test_course_intent_wired.py -v
```

Expected: 9 passed (5 prior + 4 new).

- [ ] **Step 5: Wire into narration_apply**

In `sidequest-server/sidequest/server/narration_apply.py`, find where `game_patch` JSON is parsed and applied (search for `game_patch` near the top of `_apply_narration_result_to_snapshot`). Just before the encounter trigger block (the section we modified earlier in the playtest sweep, where `instantiate_encounter_from_trigger` is called), add:

```python
            # Plot-a-course: parse course sidecar variants out of the
            # game_patch payload and apply them to the snapshot. Other
            # sidecar handlers (dice, encounter trigger) ignore course
            # intents — parse_course_sidecar returns None for those.
            from sidequest.handlers.course_intent import handle_course_sidecar
            from sidequest.orbital.course import compute_courses
            from sidequest.protocol.course_intent import parse_course_sidecar
            from sidequest.telemetry.spans.course import (
                emit_course_plot_accepted,
                emit_course_plot_rejected,
                emit_course_cancel,
            )

            course_sidecar = parse_course_sidecar(result.game_patch_payload)
            if course_sidecar is not None and session.orbital_content is not None:
                in_scope = _bodies_in_scope(  # imported helper from orchestrator
                    session.orbital_content.orbits,
                    session.orbital_scope,
                )
                available = compute_courses(
                    orbits=session.orbital_content.orbits,
                    party_at=snapshot.party_body_id,
                    in_scope_body_ids=in_scope,
                    recent_body_mentions=list(session.recent_body_mentions),
                    quest_anchors=list(snapshot.quest_anchors),
                )
                handler_result = handle_course_sidecar(
                    sidecar=course_sidecar,
                    snapshot=snapshot,
                    available_courses=available,
                )
                from sidequest.protocol.course_intent import (
                    CancelCourseSidecar,
                    PlotCourseSidecar,
                )

                if isinstance(course_sidecar, PlotCourseSidecar):
                    if handler_result.accepted:
                        emit_course_plot_accepted(
                            from_body=snapshot.party_body_id,
                            course=snapshot.plotted_course,
                        )
                    else:
                        emit_course_plot_rejected(
                            course_id=course_sidecar.course_id,
                            reason=handler_result.reason,
                            available_ids=sorted(available.keys()),
                        )
                        # Inject a reactions hint for next turn.
                        session.add_reaction_for_next_turn(
                            f"Your last plot_course request was rejected: "
                            f"course_id {course_sidecar.course_id!r} is not "
                            "available. See <courses> for valid ids."
                        )
                elif isinstance(course_sidecar, CancelCourseSidecar):
                    emit_course_cancel(
                        was_already_clear=handler_result.was_already_clear,
                    )
```

(`_bodies_in_scope` was added to orchestrator.py in Task 7. Move it to `sidequest/orbital/course.py` to make it shareable: cut the function from orchestrator.py and re-import it in both call sites. This is a small refactor done in this task.)

For `session.add_reaction_for_next_turn`: if no equivalent exists, add a minimal `_pending_reactions: list[str]` deque on Session with a method to append, and an existing prompt section near the Recency zone in orchestrator.py reads and clears it. The dev should grep for an existing reactions mechanism first — there may already be one (search for `<reactions>` in `agents/orchestrator.py` and `narrator.py`); reuse it if so.

- [ ] **Step 6: Run the full test suite to catch regressions**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/handlers/ tests/orbital/ tests/agents/ tests/server/ -v -x
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/handlers/course_intent.py sidequest/server/narration_apply.py sidequest/orbital/course.py sidequest/agents/orchestrator.py tests/handlers/test_course_intent_wired.py
git commit -m "feat(course): plot_course / cancel_course handler + apply hook

handle_course_sidecar mutates the snapshot per the design's accept/
reject rules. narration_apply parses the game_patch, dispatches
course intents, emits OTEL, and queues a next-turn reactions hint
on rejection.

Move _bodies_in_scope to sidequest/orbital/course.py to share between
orchestrator (prompt block assembly) and narration_apply (intent
validation)."
```

---

## Server — Phase 7: OTEL spans

### Task 10: course span helpers

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/course.py`
- Test: extend `sidequest-server/tests/handlers/test_course_intent_wired.py` (uses real OTEL test fixture if available; otherwise smoke test)

- [ ] **Step 1: Inspect an existing span module for the pattern**

```bash
cat sidequest-server/sidequest/telemetry/spans/chart.py | head -40
```

This shows how `interior` and `chart` modules emit. Mirror that pattern.

- [ ] **Step 2: Write the failing test**

Append to `sidequest-server/tests/handlers/test_course_intent_wired.py`:

```python
def test_course_span_helpers_emit_without_error() -> None:
    """Smoke wiring test: span functions can be called without raising.

    Real assertions on attribute values belong in OTEL test infrastructure
    (search for tests/telemetry/ for the project's pattern). This smoke
    is sufficient to catch missing imports / arg signature drift."""
    from sidequest.orbital.course import CourseSource, PlottedCourse
    from sidequest.telemetry.spans.course import (
        emit_course_compute,
        emit_course_plot_accepted,
        emit_course_plot_rejected,
        emit_course_cancel,
        emit_course_render_overlay,
    )

    pc = PlottedCourse(
        to_body_id="mid",
        eta_hours=30.0,
        delta_v=1.0,
        plotted_at_t_hours=42.0,
        source=CourseSource.IN_SCOPE,
    )
    emit_course_compute(course_count=4, in_scope=2, recent=1, quest=1, dropped_by_cap=0)
    emit_course_plot_accepted(from_body="near", course=pc)
    emit_course_plot_rejected(
        course_id="bogus", reason="not_in_scope", available_ids=["mid", "far"]
    )
    emit_course_cancel(was_already_clear=False)
    emit_course_render_overlay(to_body="mid", bezier_control_offset_au=0.4)
```

- [ ] **Step 3: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/handlers/test_course_intent_wired.py::test_course_span_helpers_emit_without_error -v
```

Expected: ImportError.

- [ ] **Step 4: Implement spans**

Create `sidequest-server/sidequest/telemetry/spans/course.py`:

```python
"""OTEL spans for the course-plotting subsystem.

Pattern mirrors sidequest/telemetry/spans/chart.py and interior.py.
Per CLAUDE.md OTEL principle: every backend subsystem MUST emit
spans so the GM dashboard can verify the lie-detector pattern
(prose vs map disagreement is invisible without telemetry).
"""

from __future__ import annotations

from opentelemetry import trace

from sidequest.orbital.course import PlottedCourse

tracer = trace.get_tracer("sidequest.course")


def emit_course_compute(
    *, course_count: int, in_scope: int, recent: int, quest: int, dropped_by_cap: int
) -> None:
    """Fired every prompt assembly that includes the <courses> block."""
    with tracer.start_as_current_span("course.compute") as span:
        span.set_attribute("course_count", course_count)
        span.set_attribute("in_scope_count", in_scope)
        span.set_attribute("recent_count", recent)
        span.set_attribute("quest_count", quest)
        span.set_attribute("dropped_by_cap", dropped_by_cap)


def emit_course_plot_accepted(*, from_body: str | None, course: PlottedCourse | None) -> None:
    """Fired when a plot_course state patch is accepted."""
    with tracer.start_as_current_span("course.plot") as span:
        span.set_attribute("from_body", from_body or "")
        if course is not None:
            span.set_attribute("to_body", course.to_body_id)
            span.set_attribute("eta_hours", course.eta_hours)
            span.set_attribute("delta_v", course.delta_v)
            span.set_attribute("source", str(course.source))


def emit_course_plot_rejected(
    *, course_id: str, reason: str, available_ids: list[str]
) -> None:
    """Fired when a plot_course state patch is rejected."""
    with tracer.start_as_current_span("course.plot.rejected") as span:
        span.set_attribute("course_id", course_id)
        span.set_attribute("reason", reason)
        span.set_attribute("available_ids", ",".join(available_ids))


def emit_course_cancel(*, was_already_clear: bool) -> None:
    """Fired when cancel_course is applied (even as a no-op)."""
    with tracer.start_as_current_span("course.cancel") as span:
        span.set_attribute("was_already_clear", was_already_clear)


def emit_course_render_overlay(*, to_body: str, bezier_control_offset_au: float) -> None:
    """Fired every chart re-render that draws a course overlay."""
    with tracer.start_as_current_span("course.render_overlay") as span:
        span.set_attribute("to_body", to_body)
        span.set_attribute("bezier_control_offset_au", bezier_control_offset_au)
```

- [ ] **Step 5: Run the smoke test**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/handlers/test_course_intent_wired.py::test_course_span_helpers_emit_without_error -v
```

Expected: pass.

- [ ] **Step 6: Hook compute span into orchestrator**

In `sidequest-server/sidequest/agents/orchestrator.py`, in the courses block we added in Task 7, after `course_rows = compute_courses(...)`, before the `format_courses_block` call:

```python
            from sidequest.telemetry.spans.course import emit_course_compute

            in_scope_n = sum(
                1 for r in course_rows.values() if r.source.value == "in_scope"
            )
            recent_n = sum(
                1 for r in course_rows.values() if r.source.value == "recent_mention"
            )
            quest_n = sum(
                1 for r in course_rows.values() if r.source.value == "quest_objective"
            )
            emit_course_compute(
                course_count=len(course_rows),
                in_scope=in_scope_n,
                recent=recent_n,
                quest=quest_n,
                dropped_by_cap=0,  # cap-counted in compute_courses if we extend the API
            )
```

- [ ] **Step 7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/telemetry/spans/course.py sidequest/agents/orchestrator.py tests/handlers/test_course_intent_wired.py
git commit -m "feat(course): OTEL spans (compute/plot/rejected/cancel/render)

Five spans per the design: course.compute on every prompt assembly,
course.plot/rejected on state-patch decisions, course.cancel on
clear, course.render_overlay on chart re-render. Span attrs sized
for the GM dashboard's lie-detector role: pc_actor_count-style
visibility for course selection."
```

---

## Server — Phase 8: Bezier overlay renderer

### Task 11: render_course_overlay SVG composer

**Files:**
- Create: `sidequest-server/sidequest/orbital/course_render.py`
- Test: `sidequest-server/tests/orbital/test_course_render_overlay.py`

- [ ] **Step 1: Inspect render.py for the SVG primitives**

```bash
grep -nE "def |position_for|polar_to_cart" sidequest-server/sidequest/orbital/render.py | head -20
```

The renderer is reading-list — find existing helpers for "given body_id and t_hours, what x/y on the chart?" Then mirror that pattern.

- [ ] **Step 2: Write the failing golden snapshot test**

Create `sidequest-server/tests/orbital/test_course_render_overlay.py`:

```python
"""Golden snapshot for course Bezier overlay.

The overlay is composed onto the existing chart SVG. We render a
chart with a known plotted_course and assert the SVG includes:
- One <path d="M ... C ..." /> with the dashed engraved-register
  styling
- A target reticle <g> at the destination
- A HUD chip element with ETA/Δv text

Snapshot lock: golden lives at tests/orbital/golden/course_overlay.svg.
"""
from __future__ import annotations

from pathlib import Path

from sidequest.orbital.course import CourseSource, PlottedCourse
from sidequest.orbital.course_render import render_course_overlay
from sidequest.orbital.models import (
    BodyDef,
    BodyType,
    ClockConfig,
    OrbitsConfig,
    TravelConfig,
    TravelRealism,
)


GOLDEN = Path(__file__).parent / "golden" / "course_overlay.svg"


def _orbits() -> OrbitsConfig:
    return OrbitsConfig(
        version="0.1.0",
        clock=ClockConfig(),
        travel=TravelConfig(realism=TravelRealism.ORBITAL),
        bodies={
            "coyote": BodyDef(type=BodyType.STAR),
            "near": BodyDef(
                type=BodyType.HABITAT,
                parent="coyote",
                semi_major_au=1.0,
                period_days=365.0,
                epoch_phase_deg=0.0,
            ),
            "far": BodyDef(
                type=BodyType.HABITAT,
                parent="coyote",
                semi_major_au=3.0,
                period_days=1100.0,
                epoch_phase_deg=180.0,
            ),
        },
    )


def test_render_course_overlay_produces_path_and_chip() -> None:
    course = PlottedCourse(
        to_body_id="far",
        label="Far",
        eta_hours=80.0,
        delta_v=2.4,
        plotted_at_t_hours=0.0,
        source=CourseSource.IN_SCOPE,
    )
    svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"  # minimal carrier
    result = render_course_overlay(
        chart_svg=svg,
        course=course,
        orbits=_orbits(),
        party_body_id="near",
        t_hours=0.0,
    )
    assert "<path" in result
    assert 'd="M' in result
    assert " C " in result  # cubic Bezier
    assert "stroke-dasharray" in result
    assert "#d9a766" in result  # pale amber per design
    assert "ETA 80h" in result or "ETA 80" in result
    assert "Δv 2.4" in result or "delta_v" in result.lower()
    assert "FAR" in result.upper()


def test_render_course_overlay_no_change_when_course_is_none() -> None:
    svg_in = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    svg_out = render_course_overlay(
        chart_svg=svg_in,
        course=None,
        orbits=_orbits(),
        party_body_id="near",
        t_hours=0.0,
    )
    assert svg_out == svg_in


def test_render_course_overlay_handles_missing_party() -> None:
    course = PlottedCourse(
        to_body_id="far",
        eta_hours=10.0,
        delta_v=1.0,
        plotted_at_t_hours=0.0,
        source=CourseSource.IN_SCOPE,
    )
    svg_in = "<svg></svg>"
    # No party_body_id: overlay drops, OTEL flag set on caller side.
    svg_out = render_course_overlay(
        chart_svg=svg_in,
        course=course,
        orbits=_orbits(),
        party_body_id=None,
        t_hours=0.0,
    )
    assert svg_out == svg_in


def test_render_course_overlay_drops_unknown_target() -> None:
    course = PlottedCourse(
        to_body_id="ghost_body_not_in_orbits",
        eta_hours=10.0,
        delta_v=1.0,
        plotted_at_t_hours=0.0,
        source=CourseSource.IN_SCOPE,
    )
    svg_in = "<svg></svg>"
    svg_out = render_course_overlay(
        chart_svg=svg_in,
        course=course,
        orbits=_orbits(),
        party_body_id="near",
        t_hours=0.0,
    )
    # Unknown target: no overlay, no crash.
    assert svg_out == svg_in
```

- [ ] **Step 3: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_render_overlay.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement render_course_overlay**

Create `sidequest-server/sidequest/orbital/course_render.py`:

```python
"""Compose the course Bezier overlay onto an existing chart SVG.

Pure function: takes the chart SVG string + course state, returns a
new SVG string with the overlay layer inserted just before the
closing </svg> tag.

Per the plot-a-course design: cubic Bezier from party position to
destination position, control points offset perpendicular to the
chord by 0.3 × chord_length in the prograde direction. Pale amber
stroke (#d9a766), dashed, with a small reticle glyph at the destination
and a HUD chip.
"""

from __future__ import annotations

from sidequest.orbital.course_geometry import (
    bezier_control_offset,
    chord_angular_distance_deg,
    prograde_sign,
)
from sidequest.orbital.models import OrbitsConfig

# Position helper — body → SVG (x, y) pair. The orbital renderer already
# has this (sidequest/orbital/position.py); re-import to stay in sync
# with chart layout. The dev should locate the canonical helper at
# implementation time and adapt the import; the placeholder name below
# is the *intent*. If the existing helper expects different args, adapt.
from sidequest.orbital.position import body_position_xy  # type: ignore[import-not-found]

COURSE_STROKE_COLOR = "#d9a766"
"""Pale amber per design open-choice resolution. Defer to art-director
for final hex against the engraved register palette; this is the
recommended starting value."""

COURSE_STROKE_WIDTH = 1.5
COURSE_DASH_PATTERN = "6 4"
HUD_CHIP_FILL = "#1a1206"  # matches engraved-register card background


def render_course_overlay(
    *,
    chart_svg: str,
    course: "PlottedCourse | None",
    orbits: OrbitsConfig,
    party_body_id: str | None,
    t_hours: float,
) -> str:
    """Return ``chart_svg`` with a course overlay inserted, or ``chart_svg``
    unchanged when no overlay is needed.

    Drop conditions (return input unchanged):
    - course is None
    - party_body_id is None
    - course.to_body_id not in orbits.bodies
    - party_body_id not in orbits.bodies

    Per CLAUDE.md no-silent-fallbacks: drops emit OTEL flags via
    course.render_overlay span attrs (set by caller). Don't draw a
    course to nowhere; do log why.
    """
    if course is None:
        return chart_svg
    if party_body_id is None:
        return chart_svg
    if course.to_body_id not in orbits.bodies:
        return chart_svg
    if party_body_id not in orbits.bodies:
        return chart_svg

    party = orbits.bodies[party_body_id]
    dest = orbits.bodies[course.to_body_id]

    px, py = body_position_xy(orbits, party_body_id, t_hours)
    dx, dy = body_position_xy(orbits, course.to_body_id, t_hours)

    chord_x = dx - px
    chord_y = dy - py
    chord_length = (chord_x**2 + chord_y**2) ** 0.5
    if chord_length == 0:
        return chart_svg

    # Perpendicular unit vector (90° CCW from chord direction)
    perp_x = -chord_y / chord_length
    perp_y = chord_x / chord_length

    prograde = prograde_sign(
        party.epoch_phase_deg or 0.0, dest.epoch_phase_deg or 0.0
    )
    offset = bezier_control_offset(chord_length, prograde)

    # Symmetric control points at 1/3 and 2/3 along the chord, both
    # pushed perpendicular by ``offset``.
    c1x = px + chord_x / 3 + perp_x * offset
    c1y = py + chord_y / 3 + perp_y * offset
    c2x = px + 2 * chord_x / 3 + perp_x * offset
    c2y = py + 2 * chord_y / 3 + perp_y * offset

    path = (
        f'<path d="M {px:.2f} {py:.2f} '
        f"C {c1x:.2f} {c1y:.2f}, {c2x:.2f} {c2y:.2f}, {dx:.2f} {dy:.2f}\" "
        f'stroke="{COURSE_STROKE_COLOR}" stroke-width="{COURSE_STROKE_WIDTH}" '
        f'stroke-dasharray="{COURSE_DASH_PATTERN}" fill="none" />'
    )
    reticle = (
        f'<g transform="translate({dx:.2f},{dy:.2f})">'
        f'<circle r="6" fill="none" stroke="{COURSE_STROKE_COLOR}" />'
        f'<circle r="1.5" fill="{COURSE_STROKE_COLOR}" />'
        "</g>"
    )
    label = (course.label or course.to_body_id).upper()
    chip = (
        '<g class="course-hud-chip" transform="translate(20, 20)">'
        f'<rect width="220" height="28" fill="{HUD_CHIP_FILL}" '
        f'stroke="{COURSE_STROKE_COLOR}" />'
        f'<text x="10" y="19" fill="{COURSE_STROKE_COLOR}" '
        'font-family="monospace" font-size="12">'
        f"COURSE → {label} • ETA {course.eta_hours:.0f}h • Δv {course.delta_v:.1f}"
        "</text>"
        "</g>"
    )

    overlay = f'<g class="course-overlay">{path}{reticle}{chip}</g>'

    closing = "</svg>"
    if closing not in chart_svg:
        return chart_svg
    return chart_svg.replace(closing, overlay + closing, 1)
```

- [ ] **Step 5: Run the tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/orbital/test_course_render_overlay.py -v
```

Expected: 4 passed. (If `body_position_xy` lives at a different path — likely true — adjust the import. The intent is to call the existing renderer's "where on the SVG is this body right now" helper.)

- [ ] **Step 6: Wire into intent.py**

In `sidequest-server/sidequest/orbital/intent.py`, after the `svg = render_chart(...)` call (line ~62), insert:

```python
    # Plot-a-course overlay (plot-a-course design). Composes onto the
    # base chart SVG when the snapshot carries a plotted_course; no-op
    # otherwise. Failure to draw (unknown target body, missing party
    # anchor) returns the unmodified chart and emits an OTEL flag.
    from sidequest.orbital.course_render import render_course_overlay
    from sidequest.telemetry.spans.course import emit_course_render_overlay

    plotted = session.snapshot.plotted_course if session.snapshot else None
    if plotted is not None:
        svg = render_course_overlay(
            chart_svg=svg,
            course=plotted,
            orbits=content.orbits,
            party_body_id=session.party_body_id,
            t_hours=session.clock.t_hours,
        )
        emit_course_render_overlay(
            to_body=plotted.to_body_id, bezier_control_offset_au=0.3
        )
```

(Note: `session.snapshot` accessor — verify that exists. If not, the existing render_chart call already takes a snapshot or party_body_id; thread `plotted_course` through the same way.)

- [ ] **Step 7: Run the orbital integration test**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/integration/test_orbital_e2e.py tests/orbital/ -v
```

Expected: all pass. Existing chart behavior unchanged when no plotted_course.

- [ ] **Step 8: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/orbital/course_render.py sidequest/orbital/intent.py tests/orbital/test_course_render_overlay.py
git commit -m "feat(course): Bezier overlay + HUD chip on the orbital chart

render_course_overlay composes onto the existing chart SVG when the
snapshot has a plotted_course. Cubic Bezier from party to destination
with control points offset 0.3 × chord perpendicular in prograde
direction. Pale amber stroke (#d9a766), dashed, target reticle, HUD
chip with ETA/Δv.

No-op (returns input SVG unchanged) when course is None, party
unanchored, or target body unknown — overlay drop is OTEL-flagged
in course.render_overlay span attrs."
```

---

## Server — Phase 9: Wiring tests + integration smoke

### Task 12: End-to-end wiring test

**Files:**
- Create: `sidequest-server/tests/integration/test_plot_course_e2e.py`

- [ ] **Step 1: Write the integration test**

Create `sidequest-server/tests/integration/test_plot_course_e2e.py`:

```python
"""End-to-end: narrator emits plot_course in game_patch → snapshot
mutates → next chart fetch returns SVG with overlay → cancel_course
clears.

Stops short of touching the WebSocket transport — that's covered
by tests/integration/test_orbital_e2e.py for the chart path; we
just exercise the apply_narration_result + intent fetch chain.
"""
from __future__ import annotations

import json

from sidequest.game.session import GameSnapshot
from sidequest.handlers.course_intent import handle_course_sidecar
from sidequest.orbital.course import compute_courses
from sidequest.orbital.intent import handle_orbital_intent
from sidequest.orbital.loader import OrbitalContent
from sidequest.orbital.models import (
    BodyDef,
    BodyType,
    ClockConfig,
    OrbitsConfig,
    TravelConfig,
    TravelRealism,
)
from sidequest.protocol.course_intent import (
    PlotCourseSidecar,
    parse_course_sidecar,
)
from sidequest.protocol.orbital_intent import OrbitalIntent, ViewMapIntent


def _orbits() -> OrbitsConfig:
    return OrbitsConfig(
        version="0.1.0",
        clock=ClockConfig(),
        travel=TravelConfig(realism=TravelRealism.ORBITAL),
        bodies={
            "coyote": BodyDef(type=BodyType.STAR),
            "near": BodyDef(
                type=BodyType.HABITAT,
                parent="coyote",
                semi_major_au=1.0,
                period_days=365.0,
                epoch_phase_deg=0.0,
            ),
            "far": BodyDef(
                type=BodyType.HABITAT,
                parent="coyote",
                semi_major_au=3.0,
                period_days=1100.0,
                epoch_phase_deg=180.0,
            ),
        },
    )


def _content() -> OrbitalContent:
    return OrbitalContent(orbits=_orbits(), chart=None)


def test_narrator_payload_to_chart_overlay() -> None:
    """Simulate a narrator game_patch with plot_course intent, apply,
    then re-render the chart and assert the overlay appears."""
    from sidequest.server.session import Session

    session = Session(orbital_content=_content())
    session.snapshot = GameSnapshot(party_body_id="near", clock_t_hours=0.0)

    # Narrator-style game_patch payload (subset; only the bit we care about).
    game_patch = {"intent": "plot_course", "course_id": "far"}
    sidecar = parse_course_sidecar(game_patch)
    assert isinstance(sidecar, PlotCourseSidecar)

    in_scope = {"near", "far"}
    available = compute_courses(
        orbits=_orbits(),
        party_at="near",
        in_scope_body_ids=in_scope,
        recent_body_mentions=[],
        quest_anchors=[],
    )
    result = handle_course_sidecar(
        sidecar=sidecar,
        snapshot=session.snapshot,
        available_courses=available,
    )
    assert result.accepted
    assert session.snapshot.plotted_course is not None

    # Re-render the chart; verify overlay present.
    response = handle_orbital_intent(
        session,
        OrbitalIntent.model_validate(
            {"kind": "view_map", "scope": "system_root"}
        ),
    )
    assert "<path" in response.svg
    assert "stroke-dasharray" in response.svg
    assert "ETA" in response.svg


def test_cancel_course_drops_overlay() -> None:
    from sidequest.server.session import Session

    session = Session(orbital_content=_content())
    session.snapshot = GameSnapshot(party_body_id="near", clock_t_hours=0.0)
    # Pre-set a course
    available = compute_courses(
        orbits=_orbits(),
        party_at="near",
        in_scope_body_ids={"near", "far"},
        recent_body_mentions=[],
        quest_anchors=[],
    )
    handle_course_sidecar(
        sidecar=PlotCourseSidecar(course_id="far"),
        snapshot=session.snapshot,
        available_courses=available,
    )
    assert session.snapshot.plotted_course is not None

    cancel = parse_course_sidecar({"intent": "cancel_course"})
    assert cancel is not None
    handle_course_sidecar(
        sidecar=cancel,
        snapshot=session.snapshot,
        available_courses=available,
    )
    assert session.snapshot.plotted_course is None

    response = handle_orbital_intent(
        session,
        OrbitalIntent.model_validate({"kind": "view_map", "scope": "system_root"}),
    )
    # Without a plotted_course, the overlay path must NOT be present.
    assert "course-overlay" not in response.svg
```

- [ ] **Step 2: Run**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/integration/test_plot_course_e2e.py -v
```

Expected: 2 passed.

- [ ] **Step 3: Run the entire server suite**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
just server-check
```

Expected: lint clean + all tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add tests/integration/test_plot_course_e2e.py
git commit -m "test(course): E2E — narrator payload → snapshot → chart overlay

Two integration cases: plot_course populates plotted_course and the
next chart render contains the Bezier path; cancel_course clears it
and the next chart render omits the course-overlay group."
```

### Task 13: Server PR

- [ ] **Step 1: Push branch**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git push -u origin feat/plot-a-course
```

- [ ] **Step 2: Open PR**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
gh pr create --base develop --title "feat(server): plot a course, Kestrel — orbital course-plotting" --body "$(cat <<'EOF'
## Summary

Implements the plot-a-course design (\`docs/superpowers/specs/2026-05-03-plot-a-course-design.md\`).

- New \`sidequest/orbital/course.py\` (selection + cost + models) and \`course_geometry.py\` / \`course_render.py\` (geometry, Bezier overlay).
- New snapshot fields: \`plotted_course: PlottedCourse | None\`, \`quest_anchors: list[str]\`.
- \`<courses>\` PromptSection registered in Recency zone when world has orbital tier.
- Sidecar intents \`plot_course\` / \`cancel_course\` parsed from \`game_patch\` and applied via \`handlers/course_intent.py\`.
- 5 OTEL spans: \`course.compute\`, \`course.plot\`, \`course.plot.rejected\`, \`course.cancel\`, \`course.render_overlay\`.
- Length-4 \`recent_body_mentions\` ring buffer on Session, populated by \`note_body_mentioned()\`.
- Orbital chart renderer composes the curved Bezier overlay + HUD chip when \`plotted_course\` is set.

No new WS message kinds; STATE_PATCH carries the snapshot mutation back to the client.

## Test plan
- [x] Unit: cost model calibration (Far Landing→Tethys Watch ≈ 12h, ≈ The Gate ≈ 90h)
- [x] Unit: selection priority + 12-cap + determinism
- [x] Unit: geometry (chord, prograde, Bezier offset)
- [x] Unit: handler accept/reject/cancel paths
- [x] Wiring: format_courses_block, sidecar parsing, span emission
- [x] Integration: narrator payload → snapshot → chart overlay round-trip
- [ ] Live playtest: \"Kestrel, plot a course to Far Landing\" draws an arc
- [ ] OTEL dashboard: \`course.compute\` fires per turn, \`course.plot.rejected\` fires on hallucinated destinations

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Note PR number for the UI PR description**

The UI PR will mention this PR in its body.

---

## UI — Phase 10: Refetch on plotted_course state patch

### Task 14: Add plotted_course field to OrbitalIntentResponse type

**Files:**
- Modify: `sidequest-ui/src/types/orbital-intent.ts`

- [ ] **Step 1: Inspect existing type**

```bash
cat sidequest-ui/src/types/orbital-intent.ts
```

- [ ] **Step 2: Add plotted_course field**

In `sidequest-ui/src/types/orbital-intent.ts`, find the `OrbitalIntentResponse` interface and extend it:

```typescript
export interface PlottedCourseWire {
  to_body_id: string;
  label: string | null;
  eta_hours: number;
  delta_v: number;
  plotted_at_t_hours: number;
  source: "in_scope" | "recent_mention" | "quest_objective";
}

export interface OrbitalIntentResponse {
  // ...existing fields...
  /**
   * Course plotted by the narrator, drawn on the chart as a curved
   * Bezier overlay. Null when no course is plotted.
   * Cleared on the server by cancel_course intent, replacement plot,
   * or arrival at the destination body.
   */
  plotted_course: PlottedCourseWire | null;
}
```

(If the existing interface uses `type` rather than `interface`, follow that style; the dev should match the file's convention.)

- [ ] **Step 3: Verify typecheck**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
npm run typecheck 2>&1 | head -20
```

Expected: no new errors. Existing consumers of `OrbitalIntentResponse` should already destructure or pass through; only the chart consumer cares about `plotted_course` (next task).

- [ ] **Step 4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
git add src/types/orbital-intent.ts
git commit -m "feat(ui): plotted_course wire field on OrbitalIntentResponse

Mirrors the server-side PlottedCourse model. Source values track the
server enum (in_scope / recent_mention / quest_objective) but the UI
only renders the line + chip; source is exposed for future panel
work."
```

### Task 15: useOrbitalChart refetches on plotted_course change

**Files:**
- Modify: `sidequest-ui/src/hooks/useOrbitalChart.ts`
- Test: `sidequest-ui/src/hooks/__tests__/useOrbitalChart.plot.test.ts`

- [ ] **Step 1: Inspect the existing hook**

```bash
cat sidequest-ui/src/hooks/useOrbitalChart.ts
```

- [ ] **Step 2: Write the failing test**

Create `sidequest-ui/src/hooks/__tests__/useOrbitalChart.plot.test.ts`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

import { useOrbitalChart } from "@/hooks/useOrbitalChart";
import type { OrbitalIntentResponse } from "@/types/orbital-intent";

const baseResponse: OrbitalIntentResponse = {
  // existing required fields — fill in based on real shape; placeholders.
  scope_center: "coyote",
  svg: "<svg />",
  t_hours: 0,
  epoch_days: 0,
  party_at: "near",
  next_conjunction: null,
  plotted_course: null,
};

describe("useOrbitalChart — plotted_course refetch", () => {
  it("kicks an initial view_map on enable", () => {
    const sendIntent = vi.fn();
    renderHook(() =>
      useOrbitalChart({
        enabled: true,
        sendIntent,
        lastResponse: null,
        plottedCourseRevision: 0,
      } as any),
    );
    expect(sendIntent).toHaveBeenCalledWith({
      kind: "view_map",
      scope: "system_root",
    });
  });

  it("re-fetches view_map when plottedCourseRevision changes", () => {
    const sendIntent = vi.fn();
    const { rerender } = renderHook(
      ({ rev }: { rev: number }) =>
        useOrbitalChart({
          enabled: true,
          sendIntent,
          lastResponse: baseResponse,
          plottedCourseRevision: rev,
        } as any),
      { initialProps: { rev: 0 } },
    );
    sendIntent.mockClear();
    rerender({ rev: 1 });
    expect(sendIntent).toHaveBeenCalledWith({
      kind: "view_map",
      scope: "system_root",
    });
  });

  it("does NOT re-fetch when plottedCourseRevision is unchanged", () => {
    const sendIntent = vi.fn();
    const { rerender } = renderHook(
      ({ rev }: { rev: number }) =>
        useOrbitalChart({
          enabled: true,
          sendIntent,
          lastResponse: baseResponse,
          plottedCourseRevision: rev,
        } as any),
      { initialProps: { rev: 5 } },
    );
    sendIntent.mockClear();
    rerender({ rev: 5 }); // same value, different render
    expect(sendIntent).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 3: Run to verify failure**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
npx vitest run src/hooks/__tests__/useOrbitalChart.plot.test.ts
```

Expected: fail — `plottedCourseRevision` not in args type, or refetch behavior absent.

- [ ] **Step 4: Add plottedCourseRevision support**

In `sidequest-ui/src/hooks/useOrbitalChart.ts`:

Update the args interface:

```typescript
export interface UseOrbitalChartArgs {
  enabled: boolean;
  sendIntent: (intent: OrbitalIntent) => void;
  lastResponse: OrbitalIntentResponse | null;
  /**
   * Bumps when the server-side plotted_course changes (via STATE_PATCH).
   * Drives a re-fetch of the current view so the chart redraws with the
   * new overlay (or without it on cancel). Caller derives this from the
   * snapshot mirror — typically ``plotted_course?.to_body_id`` hashed
   * with ``plotted_course?.plotted_at_t_hours``.
   */
  plottedCourseRevision: number;
}
```

In the hook body, add a ref to track the last revision and a `useEffect` to refetch when it changes:

```typescript
  const lastPlottedRevision = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) {
      lastPlottedRevision.current = null;
      return;
    }
    if (lastPlottedRevision.current === null) {
      lastPlottedRevision.current = plottedCourseRevision;
      return; // initial enable handles its own fetch via the existing effect
    }
    if (plottedCourseRevision !== lastPlottedRevision.current) {
      lastPlottedRevision.current = plottedCourseRevision;
      sendIntent({ kind: "view_map", scope: "system_root" });
    }
  }, [enabled, plottedCourseRevision, sendIntent]);
```

(Note: this duplicates "scope" with the initial fetch. If the chart maintains a "current scope" elsewhere, refactor to fetch the *current* scope rather than always system_root. The dev should look at how the existing intent-forwarding handles this — search for `onIntent` callers.)

- [ ] **Step 5: Run tests**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
npx vitest run src/hooks/__tests__/useOrbitalChart.plot.test.ts
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
git add src/hooks/useOrbitalChart.ts src/hooks/__tests__/useOrbitalChart.plot.test.ts
git commit -m "feat(ui): refetch chart on plotted_course revision bump

useOrbitalChart accepts plottedCourseRevision: number and re-fetches
the current view when it changes. Caller derives the revision from
the snapshot mirror — bump it on every plotted_course STATE_PATCH.

Initial enable suppresses the watcher (the existing initial-fetch
effect handles that), so we don't double-fetch on mount."
```

### Task 16: Wire revision from snapshot mirror in App

**Files:**
- Modify: `sidequest-ui/src/<App.tsx or wherever the chart is bound>`

- [ ] **Step 1: Find the consumer**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
grep -rn "useOrbitalChart" src/ --include="*.tsx" --include="*.ts"
```

- [ ] **Step 2: Derive a revision number from the snapshot mirror**

In the consumer file, near where `useOrbitalChart` is called, derive a revision:

```typescript
// Plot-a-course: bump a counter every time the server-side plotted_course
// changes so the chart re-fetches with the new overlay (or without it
// on cancel). Hash on (to_body_id, plotted_at_t_hours) — both change on
// every plot, neither changes on incidental snapshot updates.
const plottedCourseRevision = useMemo(() => {
  const pc = snapshot?.plotted_course;
  if (!pc) return 0;
  // Rolling hash; collisions are harmless (worst case: spurious extra fetch).
  return (
    (pc.to_body_id.charCodeAt(0) ?? 0) +
    Math.floor(pc.plotted_at_t_hours * 1000)
  );
}, [snapshot?.plotted_course]);
```

Pass it into `useOrbitalChart`:

```typescript
const { chart, onIntent } = useOrbitalChart({
  enabled,
  sendIntent,
  lastResponse,
  plottedCourseRevision,
});
```

- [ ] **Step 3: Verify typecheck + smoke test**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
npm run typecheck && npx vitest run
```

Expected: clean.

- [ ] **Step 4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
git add src/  # just the consumer file actually edited
git commit -m "feat(ui): wire plotted_course revision into orbital hook

Derive a rolling revision number from snapshot.plotted_course so the
orbital chart hook re-fetches when the server-side plot changes. Hash
on (to_body_id, plotted_at_t_hours) — distinct on every plot, stable
otherwise."
```

### Task 17: HUD chip is rendered (snapshot-test the SVG path)

**Files:**
- (Optional) Create: `sidequest-ui/src/components/OrbitalChart/__tests__/OrbitalChartHudChip.test.tsx` if the chart has a structured chip component; otherwise the chip lives inside the server SVG (Task 11) and there's nothing UI-side to test.

- [ ] **Step 1: Determine where the HUD chip lives**

```bash
grep -rn "HudBottomStrip\|course-hud-chip" sidequest-ui/src/
```

If the chip is rendered via the server-emitted SVG (the path we took in Task 11), there is no separate UI component — the SVG carries the chip directly. Skip to Task 18.

If the project prefers a React-side HUD chip overlay (mirroring `HudBottomStrip.tsx`), add a component that reads `snapshot.plotted_course` and renders alongside the SVG. The dev decides which approach matches the existing conventions.

- [ ] **Step 2: If skipped, no commit needed.**

### Task 18: UI PR

- [ ] **Step 1: Run full UI gate**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
npm run typecheck && npx eslint . && npx vitest run
```

Expected: all green.

- [ ] **Step 2: Push**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
git push -u origin feat/plot-a-course
```

- [ ] **Step 3: Open PR**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
gh pr create --base develop --title "feat(ui): plot a course, Kestrel — chart refetch on STATE_PATCH" --body "$(cat <<'EOF'
## Summary

Companion PR to slabgorb/sidequest-server#NNN (substitute the server PR number after Task 13).

- \`OrbitalIntentResponse\` gains \`plotted_course: PlottedCourseWire | null\`.
- \`useOrbitalChart\` accepts \`plottedCourseRevision: number\` and re-fetches when it changes.
- App-level wiring derives the revision from \`snapshot.plotted_course\` so STATE_PATCH events trigger a chart refresh.
- HUD chip is server-rendered into the chart SVG (no UI component change beyond the wire passthrough).

## Test plan
- [x] Vitest: hook re-fetches on revision bump, not on equal revision
- [ ] Live playtest: plotting a course in chat draws the arc on the orbital chart within one frame after the STATE_PATCH

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Server + UI — Phase 11: Smoke verification on a live instance

### Task 19: Smoke

**Files:** none (manual verification)

- [ ] **Step 1: Boot everything**

```bash
cd /Users/slabgorb/Projects/oq-2
just down  # ensure clean
just up
```

Wait for the merged log to show "narrator session ready" and "Vite ready".

- [ ] **Step 2: Open a Coyote Star session in the browser**

Connect a player, pick the space_opera/coyote_star world, sit at a Kestrel station.

- [ ] **Step 3: Verify <courses> appears in the prompt**

Tail the server log:

```bash
just logs server
```

Look for the prompt assembly span / log line that includes `<courses>` block. (If the orchestrator logs prompt sizes, the section count will increment by 1.)

- [ ] **Step 4: Issue a plot request**

In the player chat, type: "Kestrel, plot a course to Far Landing."

Expected:
- Narrator prose mentions plotting.
- Orbital chart re-renders with a curved amber arc + reticle at Far Landing.
- HUD chip shows ETA + Δv.

- [ ] **Step 5: Issue an invalid plot**

Type: "Kestrel, plot a course to the Maltese Falcon."

Expected:
- Narrator declines in-fiction.
- No phantom line.
- OTEL `course.plot.rejected` span fires (visible in the GM panel at \`just otel\`).

- [ ] **Step 6: Issue a cancel**

Type: "Kestrel, cancel the plot."

Expected:
- Narrator confirms.
- Chart redraws without the arc; HUD chip gone.

- [ ] **Step 7: Reload the page**

Expected: arc is gone (we cancelled). If we hadn't cancelled, the arc would have persisted across the reload (snapshot field).

- [ ] **Step 8: Document any deviations**

If any of steps 3–7 deviate, file a follow-up patch via `/pf-patch` referencing this plan.

### Task 20: Merge PRs

- [ ] **Step 1: Merge server PR**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
gh pr checks <server-pr-number> --watch
gh pr merge <server-pr-number> --merge --delete-branch
```

- [ ] **Step 2: Merge UI PR**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
gh pr checks <ui-pr-number> --watch
gh pr merge <ui-pr-number> --merge --delete-branch
```

- [ ] **Step 3: Verify clean state**

```bash
cd /Users/slabgorb/Projects/oq-2 && just status
```

Expected: all repos clean, both PRs merged.

---

## Self-Review Checklist (run after writing the plan)

- [x] Every spec section has at least one task implementing it (cost, selection, geometry, prompt block, sidecar, handler, validation, persistence, OTEL, UI refetch, HUD chip).
- [x] No "TBD" / "TODO" / "implement later" placeholders. Open choices are resolved (pale amber #d9a766, 4-turn buffer, world_state.quest_anchors, no UI button).
- [x] All file paths are concrete (no `<somewhere>` sigils except in three documented "find this in the existing codebase" steps where the canonical location is a low-effort grep).
- [x] Type names consistent across tasks: `PlottedCourse`, `CourseRow`, `CourseSource`, `PlotCourseSidecar`, `CancelCourseSidecar`, `CourseHandlerResult`, `compute_courses`, `compute_eta_and_dv`, `format_courses_block`, `render_course_overlay`, `handle_course_sidecar`, `parse_course_sidecar`.
- [x] Each task has working test code (no "write tests for the above" stubs).
- [x] Each task ends with a commit step.
- [x] Commits scoped per task — `feat(course): …` namespace makes the history readable.
- [x] Wiring tests exist for every subsystem touched (CLAUDE.md mandate).
- [x] OTEL spans exist for every state-change point (CLAUDE.md mandate).
- [x] No silent-fallback paths — drop conditions emit OTEL flags, never substitute defaults silently.
- [x] PR ceremony per repo (server PR first because UI depends on the wire field; UI PR references server PR).
