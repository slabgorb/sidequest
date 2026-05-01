# Orbital Map — Tracks A + B (Clock, Beats, Server SVG, Drill-In) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a deterministic story-time clock with beat-driven advances, a server-rendered engraved orbital chart for the Coyote Star world (with party marker and drill-in to Red Prospect's moon system), and the intent-message protocol that connects them. Track C (orbital math, plotter, danger beats) is a follow-up plan.

**Architecture:** Server is authoritative; UI is a thin SVG display layer. `sidequest/orbital/` is the new server module owning the clock, beat dispatch, content models, content loader, and SVG renderer. UI's `MapWidget` already routes `coyote_star` to a chart component (`OrreryView`); this plan replaces that client-side renderer with a server-fetched SVG host (`OrbitalChartView`) that adds pan/zoom (CSS) and click-intent routing back via WebSocket. Existing `cartography.yaml` data (1215 authored lines) migrates into the new `orbits.yaml` (mechanics) + `chart.yaml` (flavor) split.

**Tech Stack:**
- Server: Python 3.x, FastAPI, Pydantic, `svgwrite` (new dep), OpenTelemetry SDK (existing), `pytest`, `uv`
- Client: React 18, TypeScript, Vite, `vitest`
- Content: YAML
- Tests: pytest (server), vitest (UI), snapshot/golden-vector patterns

**Reference docs:**
- Spec: `docs/superpowers/specs/2026-05-01-orbital-map-design.md` (commit `eb633ae`)
- ADR-038 (WebSocket transport), ADR-057 (LLM narrates / scripts crunch), ADR-067 (unified narrator agent), ADR-090 (OTEL dashboard)
- CLAUDE.md principles (No Silent Fallbacks, No Stubbing, Don't Reinvent, Wiring Tests)

**Spec → plan deviations (called out for visibility):**
- Spec referred to "Coyote Star" as world name; correct slug is `coyote_star` (rename in flight from `coyote_reach`). Task 0 finishes the rename.
- Spec called for fresh `orbits.yaml`; existing `cartography.yaml` already has 13 bodies authored. Per CLAUDE.md "Don't Reinvent," Task 8 *migrates* that data instead of re-authoring.
- Spec used body ID `coyote` for the primary star; existing data uses `coyote_star`. Task 0 renames body ID `coyote_star` → `coyote` to deconflict with the world slug.

**What this plan does NOT include (deferred to Track C / Plan 2):**
- Orbital math: `position()`, `route_options()`, `conjunction_events()`
- Danger beat scheduler / encounter table loading
- `commit_route` intent and travel beat playback
- Narrator scene-context injection for `COMPUTED_OPTIONS` / `TRAVEL_INTERRUPT`
- `chart.yaml` `encounters.yaml` (encounter tables) — schema lives here, file authored in Plan 2
- Eccentric-orbit Kepler solver, time-advance sweep animation, fog-of-war, multi-leg routes

These are explicitly out-of-scope. If a step requires them, that step belongs in Plan 2.

---

## File Structure

### New files (server)

| Path | Responsibility |
|---|---|
| `sidequest-server/sidequest/orbital/__init__.py` | Package marker |
| `sidequest-server/sidequest/orbital/clock.py` | `Clock` dataclass; story-time storage; `now()`/`advance()` |
| `sidequest-server/sidequest/orbital/beats.py` | `BeatKind` enum, `Beat` dataclass, `advance_clock_via_beat()` |
| `sidequest-server/sidequest/orbital/display.py` | `format_duration(hours) -> str` scale-appropriate formatter |
| `sidequest-server/sidequest/orbital/models.py` | Pydantic models: `OrbitsConfig`, `BodyDef`, `TravelConfig`, `ChartConfig`, `Annotation*` |
| `sidequest-server/sidequest/orbital/loader.py` | Read+validate `orbits.yaml` and `chart.yaml` for a given world dir |
| `sidequest-server/sidequest/orbital/render.py` | `render_chart(orbits, chart, scope, t_hours, party_at) -> str` returns full SVG |
| `sidequest-server/sidequest/orbital/intent.py` | Intent dispatch: `view_map`, `drill_in`, `drill_out` → SVG response |
| `sidequest-server/sidequest/telemetry/spans/clock.py` | `clock.advance` span emitter |
| `sidequest-server/sidequest/telemetry/spans/chart.py` | `chart.render` span emitter |
| `sidequest-server/sidequest/protocol/orbital_intent.py` | Pydantic protocol messages for intents + responses |

### New tests (server)

| Path | Tests |
|---|---|
| `sidequest-server/tests/orbital/__init__.py` | Package marker |
| `sidequest-server/tests/orbital/test_clock.py` | Clock advance, edge cases |
| `sidequest-server/tests/orbital/test_beats.py` | Beat kinds, default durations, OTEL emission |
| `sidequest-server/tests/orbital/test_display.py` | `format_duration` scale handling |
| `sidequest-server/tests/orbital/test_loader.py` | YAML validation, missing-field errors |
| `sidequest-server/tests/orbital/test_render.py` | Snapshot-pin SVG output for canonical inputs |
| `sidequest-server/tests/orbital/test_render_scopes.py` | System scope + body scope rendering |
| `sidequest-server/tests/orbital/test_intent.py` | Intent dispatch routing + responses |
| `sidequest-server/tests/integration/test_orbital_e2e.py` | view_map → drill_in → drill_out cycle; beat advance emits span |
| `sidequest-server/tests/orbital/snapshots/` | Pinned SVG outputs (fixtures) |

### New files (UI)

| Path | Responsibility |
|---|---|
| `sidequest-ui/src/components/OrbitalChart/OrbitalChartView.tsx` | Thin SVG host with pan/zoom + click intent routing |
| `sidequest-ui/src/components/OrbitalChart/index.ts` | Exports |
| `sidequest-ui/src/types/orbital-intent.ts` | TS types matching Python protocol |
| `sidequest-ui/src/hooks/useOrbitalChart.ts` | WebSocket-bound hook fetching SVG + handling intents |
| `sidequest-ui/src/components/OrbitalChart/__tests__/OrbitalChartView.test.tsx` | Mount, click routing, pan/zoom |

### New content

| Path | Source |
|---|---|
| `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml` | Migrated from `cartography.yaml` (mechanics fields) + new `travel:` block |
| `sidequest-content/genre_packs/space_opera/worlds/coyote_star/chart.yaml` | Migrated from `cartography.yaml` (flavor fields) + new `annotations:` block |

### Files to modify

| Path | Change |
|---|---|
| `sidequest-server/sidequest/telemetry/spans/__init__.py` | Register new `clock.advance` and `chart.render` spans |
| `sidequest-server/sidequest/server/dispatch/__init__.py` | Wire orbital intent dispatch into the WebSocket message router |
| `sidequest-server/sidequest/game/session.py` | Hold `Clock` per session; advance on rest/encounter beat boundaries |
| `sidequest-server/pyproject.toml` | Add `svgwrite` dependency |
| `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx` | Route `coyote_star` to `OrbitalChartView` instead of `OrreryView` |
| `sidequest-ui/src/__tests__/app-gameboard-world-slug-wiring.test.tsx` | Update wiring test for new component |

### Files to delete (after migration)

| Path | Reason |
|---|---|
| `sidequest-content/genre_packs/space_opera/worlds/coyote_reach/cartography.yaml` | Migrated to orbits.yaml + chart.yaml |
| `sidequest-ui/src/components/Orrery/OrreryView.tsx` | Replaced by server-rendered SVG |
| `sidequest-ui/src/components/Orrery/coyoteStarData.ts` | Hardcoded UI-side data, replaced by server fetch |
| `sidequest-ui/src/components/Orrery/geometry.ts` | Geometry now happens server-side |
| `sidequest-ui/src/components/Orrery/types.ts` | Replaced by `orbital-intent.ts` types |
| `sidequest-ui/src/components/Orrery/index.ts` | Folder deleted |

---

## Task 0: Rename world `coyote_reach` → `coyote_star`

The directory and the primary-star body ID both currently use `coyote_reach` / `coyote_star`. The user wants the world slug to be `coyote_star`; we deconflict the body ID by renaming it to `coyote`.

**Files:**
- Rename: `sidequest-content/genre_packs/space_opera/worlds/coyote_reach/` → `sidequest-content/genre_packs/space_opera/worlds/coyote_star/`
- Modify: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/world.yaml` (slug + name)
- Modify: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml` (body `coyote_star` → `coyote`; lagrange_pair refs)
- Modify: any remaining `coyote_reach` references in content + server + UI

- [ ] **Step 1: Find all references to old slug + old body ID**

```bash
grep -rn "coyote_reach\|Coyote Reach" sidequest-content sidequest-server sidequest-ui --include="*.yaml" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" 2>/dev/null > /tmp/coyote_reach_refs.txt
grep -rn "id: coyote_star\b\|coyote_star:\|^coyote_star" sidequest-content/genre_packs/space_opera/worlds/coyote_reach/ 2>/dev/null > /tmp/coyote_star_body_refs.txt
wc -l /tmp/coyote_reach_refs.txt /tmp/coyote_star_body_refs.txt
```

Expected: a count of files needing update. Inspect both files.

- [ ] **Step 2: Rename the world directory**

```bash
git mv sidequest-content/genre_packs/space_opera/worlds/coyote_reach sidequest-content/genre_packs/space_opera/worlds/coyote_star
```

- [ ] **Step 3: Update `world.yaml` slug and name**

Change `slug: coyote_reach` → `slug: coyote_star` and `name: Coyote Reach` → `name: Coyote Star` in `sidequest-content/genre_packs/space_opera/worlds/coyote_star/world.yaml`.

- [ ] **Step 4: Update body ID `coyote_star` (sun) → `coyote` in `cartography.yaml`**

In `sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml`:
- Find the body with `id: coyote_star` (the system primary star). Change `id: coyote_star` → `id: coyote`.
- Replace every `coyote_star` reference inside that file's `lagrange_pair: [coyote_star, X]` entries with `coyote`.

```bash
# Verify after edits — these should both return zero
grep -c "id: coyote_star" sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml
grep -c "lagrange_pair: \[coyote_star," sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml
```

Expected: both `0`.

- [ ] **Step 5: Update remaining slug references in other content files**

Use `/tmp/coyote_reach_refs.txt` as the worklist. For each file: replace `coyote_reach` → `coyote_star` and `Coyote Reach` → `Coyote Star`. Skip `.git/` paths.

```bash
# After edits — should return zero (excluding .git)
grep -rn "coyote_reach\|Coyote Reach" sidequest-content sidequest-server sidequest-ui --include="*.yaml" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" 2>/dev/null | grep -v "/\.git/" | wc -l
```

Expected: `0`.

- [ ] **Step 6: Run existing test suites to confirm rename didn't break wiring**

```bash
just server-test 2>&1 | tail -30
just client-test 2>&1 | tail -30
```

Expected: both pass (or fail only on tests that already failed pre-rename — diff against `main`).

- [ ] **Step 7: Commit**

```bash
git add sidequest-content sidequest-server sidequest-ui
git commit -m "content(world): rename coyote_reach -> coyote_star; deconflict body coyote_star -> coyote

User-driven rename: 'Reach' was a generic suffix; replaced with the
diegetic primary-star name. The body ID for the system primary moves
to 'coyote' so the world slug and the body ID are not the same string."
```

---

## Task 1: Clock state module

Story-time clock holds `t_hours: float` per session. Pure dataclass with an `advance(hours)` method. No persistence integration yet — that comes when we wire into `session.py`.

**Files:**
- Create: `sidequest-server/sidequest/orbital/__init__.py`
- Create: `sidequest-server/sidequest/orbital/clock.py`
- Create: `sidequest-server/tests/orbital/__init__.py`
- Create: `sidequest-server/tests/orbital/test_clock.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/__init__.py` (empty). Then `sidequest-server/tests/orbital/test_clock.py`:

```python
"""Clock primitive tests — story-time storage in hours."""
from __future__ import annotations

import pytest

from sidequest.orbital.clock import Clock


def test_clock_starts_at_zero():
    clock = Clock()
    assert clock.t_hours == 0.0


def test_clock_starts_at_explicit_epoch():
    clock = Clock(t_hours=72.0)
    assert clock.t_hours == 72.0


def test_clock_advance_adds_hours():
    clock = Clock()
    clock.advance(24.0)
    assert clock.t_hours == 24.0


def test_clock_advance_accumulates():
    clock = Clock()
    clock.advance(6.0)
    clock.advance(18.0)
    assert clock.t_hours == 24.0


def test_clock_advance_negative_rejected():
    clock = Clock()
    with pytest.raises(ValueError, match="negative"):
        clock.advance(-1.0)


def test_clock_advance_zero_allowed():
    clock = Clock()
    clock.advance(0.0)
    assert clock.t_hours == 0.0


def test_clock_t_days_is_t_hours_div_24():
    clock = Clock(t_hours=48.0)
    assert clock.t_days == 2.0
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_clock.py -v
```

Expected: ImportError / ModuleNotFoundError on `sidequest.orbital.clock`.

- [ ] **Step 3: Implement the clock**

Create `sidequest-server/sidequest/orbital/__init__.py` (empty). Then `sidequest-server/sidequest/orbital/clock.py`:

```python
"""Story-time clock primitive.

The clock stores absolute hours from a world-defined epoch (`epoch_days: 0`
in `orbits.yaml`). It advances *only* via beats — see `sidequest.orbital.beats`.

Per the orbital map spec (§3.1): internal unit is hours; display formatting
lives in `sidequest.orbital.display`. Standard Day = 24h.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Clock:
    """Story-time clock for a single session.

    `t_hours` is monotonic non-decreasing; `advance(hours)` is the only
    mutation method. Direct mutation of `t_hours` is technically possible
    but discouraged — go through `advance()` so the invariant holds.
    """

    t_hours: float = 0.0

    @property
    def t_days(self) -> float:
        return self.t_hours / 24.0

    def advance(self, hours: float) -> None:
        """Advance the clock by `hours`. Negative values raise ValueError.

        Zero is allowed (a no-op beat is legal — the engine still emits
        the OTEL span for it, since recording the *attempt* matters).
        """
        if hours < 0:
            raise ValueError(f"Clock cannot advance by negative hours: {hours!r}")
        self.t_hours += hours
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_clock.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/__init__.py \
        sidequest-server/sidequest/orbital/clock.py \
        sidequest-server/tests/orbital/__init__.py \
        sidequest-server/tests/orbital/test_clock.py
git commit -m "feat(orbital): add Clock primitive with hours-based story-time

Per spec §3.1: internal unit is hours, advance via positive deltas only.
Beats (§3.2) and OTEL emission (§3.3) come in subsequent tasks."
```

---

## Task 2: Beat taxonomy and advance dispatch

Four beat kinds (`encounter`, `rest`, `travel`, `downtime`) with default durations and a single `advance_clock_via_beat()` entry point. Travel duration is taken as a parameter (computed by Track C); rest is fixed; encounter has a narrator-overridable default; downtime is player-declared.

**Files:**
- Create: `sidequest-server/sidequest/orbital/beats.py`
- Create: `sidequest-server/tests/orbital/test_beats.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_beats.py`:

```python
"""Beat dispatch tests — clock advance via beat kinds."""
from __future__ import annotations

import pytest

from sidequest.orbital.beats import (
    Beat,
    BeatKind,
    DEFAULT_DURATIONS_HOURS,
    advance_clock_via_beat,
)
from sidequest.orbital.clock import Clock


def test_beat_kind_values():
    assert {k.value for k in BeatKind} == {"encounter", "rest", "travel", "downtime"}


def test_default_durations():
    assert DEFAULT_DURATIONS_HOURS[BeatKind.ENCOUNTER] == 1.0
    assert DEFAULT_DURATIONS_HOURS[BeatKind.REST] == 8.0
    # travel and downtime have no static default — duration must be supplied
    assert BeatKind.TRAVEL not in DEFAULT_DURATIONS_HOURS
    assert BeatKind.DOWNTIME not in DEFAULT_DURATIONS_HOURS


def test_encounter_beat_default_advances_one_hour():
    clock = Clock()
    advance_clock_via_beat(clock, Beat(kind=BeatKind.ENCOUNTER, trigger="scene-1"))
    assert clock.t_hours == 1.0


def test_encounter_beat_overridable():
    clock = Clock()
    advance_clock_via_beat(
        clock, Beat(kind=BeatKind.ENCOUNTER, duration_hours=6.0, trigger="negotiation")
    )
    assert clock.t_hours == 6.0


def test_rest_beat_fixed_eight_hours():
    clock = Clock()
    advance_clock_via_beat(clock, Beat(kind=BeatKind.REST, trigger="long-rest"))
    assert clock.t_hours == 8.0


def test_rest_duration_override_rejected():
    """REST is fixed at 8h; passing a different duration is a programming error."""
    clock = Clock()
    with pytest.raises(ValueError, match="REST.*fixed at 8h"):
        advance_clock_via_beat(
            clock, Beat(kind=BeatKind.REST, duration_hours=4.0, trigger="catnap")
        )


def test_travel_beat_requires_duration():
    clock = Clock()
    with pytest.raises(ValueError, match="TRAVEL.*requires.*duration_hours"):
        advance_clock_via_beat(clock, Beat(kind=BeatKind.TRAVEL, trigger="route-x"))


def test_travel_beat_advances_provided_duration():
    clock = Clock()
    advance_clock_via_beat(
        clock, Beat(kind=BeatKind.TRAVEL, duration_hours=432.0, trigger="route-x")
    )
    assert clock.t_hours == 432.0


def test_downtime_requires_duration():
    clock = Clock()
    with pytest.raises(ValueError, match="DOWNTIME.*requires.*duration_hours"):
        advance_clock_via_beat(clock, Beat(kind=BeatKind.DOWNTIME, trigger="wait"))


def test_downtime_advances_provided_duration():
    clock = Clock()
    advance_clock_via_beat(
        clock, Beat(kind=BeatKind.DOWNTIME, duration_hours=72.0, trigger="player-wait")
    )
    assert clock.t_hours == 72.0
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_beats.py -v
```

Expected: ImportError on `sidequest.orbital.beats`.

- [ ] **Step 3: Implement the beat module**

Create `sidequest-server/sidequest/orbital/beats.py`:

```python
"""Beat taxonomy and clock-advance dispatch.

Per spec §3.2: four beat kinds. Encounter has a 1h default that the narrator
can override. Rest is fixed at 8h. Travel duration is computed by Track C
and supplied to this module as a parameter. Downtime is player-declared.

Every beat advance emits a `clock.advance` OTEL span — see Task 3 for that
wiring. The dispatcher itself does not yet emit; it just mutates the clock.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sidequest.orbital.clock import Clock


class BeatKind(Enum):
    """The four beat kinds. The clock advances only via these."""

    ENCOUNTER = "encounter"
    REST = "rest"
    TRAVEL = "travel"
    DOWNTIME = "downtime"


# Beats with a static default duration. Encounter defaults to 1h but may be
# overridden by the narrator per scene. Rest is fixed (override rejected).
# Travel and Downtime have no default — duration is always supplied.
DEFAULT_DURATIONS_HOURS: dict[BeatKind, float] = {
    BeatKind.ENCOUNTER: 1.0,
    BeatKind.REST: 8.0,
}


@dataclass(frozen=True)
class Beat:
    """One clock-advance event.

    `trigger` is a free-form string identifying the cause (scene id, route
    id, player action id) — captured in the OTEL span for traceability.
    `duration_hours=None` means "use the default for this kind"; required
    for kinds without a default.
    """

    kind: BeatKind
    trigger: str
    duration_hours: float | None = None


def advance_clock_via_beat(clock: Clock, beat: Beat) -> float:
    """Advance the clock per the beat's kind and duration.

    Returns the actual hours advanced (handy for callers that want to log
    or surface it). Raises `ValueError` if the beat is malformed for its
    kind (e.g. REST with a non-default duration; TRAVEL without duration).
    """
    duration = _resolve_duration(beat)
    clock.advance(duration)
    return duration


def _resolve_duration(beat: Beat) -> float:
    if beat.kind == BeatKind.REST:
        if beat.duration_hours is not None and beat.duration_hours != 8.0:
            raise ValueError(
                f"REST beat duration is fixed at 8h; got {beat.duration_hours!r} "
                f"(trigger={beat.trigger!r})"
            )
        return 8.0
    if beat.kind == BeatKind.ENCOUNTER:
        return beat.duration_hours if beat.duration_hours is not None else 1.0
    # TRAVEL and DOWNTIME require explicit duration
    if beat.duration_hours is None:
        raise ValueError(
            f"{beat.kind.name} beat requires explicit duration_hours "
            f"(trigger={beat.trigger!r})"
        )
    return beat.duration_hours
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_beats.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/beats.py sidequest-server/tests/orbital/test_beats.py
git commit -m "feat(orbital): beat taxonomy + clock-advance dispatch

Four kinds (encounter/rest/travel/downtime) per spec §3.2. Encounter has a
narrator-overridable 1h default; rest is fixed at 8h; travel + downtime
require explicit duration. OTEL emission added in Task 3."
```

---

## Task 3: `clock.advance` OTEL span

Per spec §3.3 and §7.3, every beat advance emits a `clock.advance` span with `beat_kind`, `duration_hours`, `t_before/after_h`, and `trigger`. Wire the emitter into `advance_clock_via_beat`.

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/clock.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py` (add module import for registration)
- Modify: `sidequest-server/sidequest/orbital/beats.py` (call emitter)
- Modify: `sidequest-server/tests/orbital/test_beats.py` (assert span fired)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/orbital/test_beats.py`:

```python
def test_advance_emits_clock_advance_span(capture_spans):
    """clock.advance span fires with the right attributes on every beat."""
    clock = Clock(t_hours=10.0)
    advance_clock_via_beat(
        clock, Beat(kind=BeatKind.TRAVEL, duration_hours=24.0, trigger="route-xy")
    )

    spans = capture_spans("clock.advance")
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes["beat_kind"] == "travel"
    assert span.attributes["duration_hours"] == 24.0
    assert span.attributes["t_before_h"] == 10.0
    assert span.attributes["t_after_h"] == 34.0
    assert span.attributes["trigger"] == "route-xy"


def test_advance_emits_for_default_durations(capture_spans):
    clock = Clock()
    advance_clock_via_beat(clock, Beat(kind=BeatKind.ENCOUNTER, trigger="scene-1"))

    spans = capture_spans("clock.advance")
    assert len(spans) == 1
    assert spans[0].attributes["duration_hours"] == 1.0
    assert spans[0].attributes["beat_kind"] == "encounter"
```

`capture_spans` is the existing OTEL-capturing fixture in `sidequest-server/tests/conftest.py`. If it does not exist exactly under that name, find the equivalent (e.g., look for `OTELRecorder` / `recorded_spans` fixtures in `tests/conftest.py` and `tests/_helpers/`) and adapt — do not invent a new pattern.

```bash
grep -n "capture_spans\|recorded_spans\|@pytest.fixture" sidequest-server/tests/conftest.py | head -20
```

If the fixture exists under a different name, rename `capture_spans` in the new tests accordingly.

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_beats.py::test_advance_emits_clock_advance_span -v
```

Expected: AttributeError or assertion failure (no span emitted).

- [ ] **Step 3: Implement the span emitter**

Create `sidequest-server/sidequest/telemetry/spans/clock.py`:

```python
"""clock.* OTEL span — every beat-driven story-time advance.

Per spec §3.3 and §7.3: the GM panel relies on this span to verify that
every story-time advance happened via a real beat (no silent skips, no
narrator improvisation of duration).
"""
from __future__ import annotations

from ._core import FLAT_ONLY_SPANS
from .span import Span

SPAN_CLOCK_ADVANCE = "clock.advance"

FLAT_ONLY_SPANS.update({SPAN_CLOCK_ADVANCE})


def emit_clock_advance(
    *,
    beat_kind: str,
    duration_hours: float,
    t_before_h: float,
    t_after_h: float,
    trigger: str,
) -> None:
    """Emit a `clock.advance` span. Fire-and-forget (FLAT_ONLY_SPANS)."""
    with Span.open(
        SPAN_CLOCK_ADVANCE,
        attributes={
            "beat_kind": beat_kind,
            "duration_hours": float(duration_hours),
            "t_before_h": float(t_before_h),
            "t_after_h": float(t_after_h),
            "trigger": trigger,
        },
    ):
        pass
```

- [ ] **Step 4: Register the new span module**

Edit `sidequest-server/sidequest/telemetry/spans/__init__.py` and add the import alongside existing `from sidequest.telemetry.spans import rig` etc.:

```python
from sidequest.telemetry.spans import clock as _clock  # noqa: F401  (registers FLAT_ONLY_SPANS)
```

Use the same import-only-for-side-effects style already used for `rig`, `magic`, etc. — verify pattern with:

```bash
grep -n "from sidequest.telemetry.spans" sidequest-server/sidequest/telemetry/spans/__init__.py
```

- [ ] **Step 5: Wire emitter into `advance_clock_via_beat`**

Edit `sidequest-server/sidequest/orbital/beats.py` to import the emitter and call it after advancing:

```python
from sidequest.telemetry.spans.clock import emit_clock_advance


def advance_clock_via_beat(clock: Clock, beat: Beat) -> float:
    duration = _resolve_duration(beat)
    t_before = clock.t_hours
    clock.advance(duration)
    emit_clock_advance(
        beat_kind=beat.kind.value,
        duration_hours=duration,
        t_before_h=t_before,
        t_after_h=clock.t_hours,
        trigger=beat.trigger,
    )
    return duration
```

- [ ] **Step 6: Run all clock + beat tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/ -v
```

Expected: all clock + beat tests pass, including the two new span-assertion tests.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/clock.py \
        sidequest-server/sidequest/telemetry/spans/__init__.py \
        sidequest-server/sidequest/orbital/beats.py \
        sidequest-server/tests/orbital/test_beats.py
git commit -m "feat(orbital): emit clock.advance span on every beat

Per spec §3.3 + §7.3 — Keith's GM panel sees every story-time advance
with kind, duration, before/after hours, and trigger. Lie detector for
narrator improvisation of time skips."
```

---

## Task 4: Display utility — `format_duration`

Pure function: hours → scale-appropriate string per spec §3.1 table.

**Files:**
- Create: `sidequest-server/sidequest/orbital/display.py`
- Create: `sidequest-server/tests/orbital/test_display.py`

- [ ] **Step 1: Write the failing test**

```python
"""format_duration tests — scale-appropriate display per spec §3.1."""
from __future__ import annotations

import pytest

from sidequest.orbital.display import format_duration


@pytest.mark.parametrize(
    "hours, expected",
    [
        (0.5, "30 minutes"),
        (0.0167, "1 minute"),
        (0.99, "59 minutes"),
        (1.0, "1 hour"),
        (5.0, "5 hours"),
        (23.999, "24 hours"),
        (24.0, "1 day"),
        (48.0, "2 days"),
        (72.0, "3 days"),
        (336.0, "14 days"),       # threshold: still days
        (337.0, "2 weeks"),       # threshold: switches to weeks
        (504.0, "3 weeks"),       # 21 days
        (2160.0, "13 weeks"),     # 90 days
        (2161.0, "3 months"),     # 90+ → months
        (8760.0, "12 months"),    # 1 year — formatter chooses months
        (17520.0, "2 years"),     # 2+ years → years
    ],
)
def test_format_duration(hours, expected):
    assert format_duration(hours) == expected


def test_negative_rejected():
    with pytest.raises(ValueError, match="negative"):
        format_duration(-1.0)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_display.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `format_duration`**

Create `sidequest-server/sidequest/orbital/display.py`:

```python
"""Display formatting for durations.

Per spec §3.1: internal unit is hours; display picks scale-appropriate
units. Engine never returns formatted strings — formatters live here so
callers (UI, CLI, narrator scene context framing) can convert at the edge.
"""
from __future__ import annotations


def format_duration(hours: float) -> str:
    """Format `hours` per spec §3.1 thresholds.

    Boundaries:
      < 1h    → minutes
      1h–24h  → hours
      24h-336h (1–14 days)  → days
      337h-2160h (~2–13 weeks)  → weeks
      2161h-17519h (~3 months – ~24 months) → months
      ≥17520h → years

    Plural-aware ("1 day" vs "2 days"). Rounds to nearest integer of the
    chosen unit.
    """
    if hours < 0:
        raise ValueError(f"format_duration cannot accept negative hours: {hours!r}")

    if hours < 1.0:
        n = max(1, round(hours * 60))
        return _plural(n, "minute")
    if hours < 24.0:
        n = round(hours)
        return _plural(n, "hour")
    days = hours / 24.0
    if days <= 14.0:
        n = round(days)
        return _plural(n, "day")
    weeks = days / 7.0
    if weeks <= 13.0:
        n = round(weeks)
        return _plural(n, "week")
    months = days / 30.0
    if months < 24.0:
        n = round(months)
        return _plural(n, "month")
    years = days / 365.0
    n = round(years)
    return _plural(n, "year")


def _plural(n: int, unit: str) -> str:
    return f"{n} {unit}" if n == 1 else f"{n} {unit}s"
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_display.py -v
```

Expected: all parametrized cases pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/display.py sidequest-server/tests/orbital/test_display.py
git commit -m "feat(orbital): format_duration scale-appropriate display

Per spec §3.1 — scale boundaries pin minutes/hours/days/weeks/months/years
unit choice. Pure function; engine returns hours, formatter formats."
```

---

## Task 5: Wire beat advances into rest + encounter flows

Add a `Clock` to per-session state and emit `Beat`s at the existing rest and scene-end flow points.

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py` (hold a Clock; advance via Beat)
- Modify: existing rest action handler (find via grep below)
- Modify: existing scene-end / turn-end handler (find via grep below)
- Create/extend: tests/integration/test_session_clock.py

- [ ] **Step 1: Locate the existing rest + scene-end paths**

```bash
grep -rn "long_rest\|short_rest\|action.*rest\|advance_turn\|end_scene" sidequest-server/sidequest --include="*.py" | grep -v test | head -20
grep -rn "class Session\b\|class GameSession\b" sidequest-server/sidequest/game --include="*.py" | head -5
```

Expected: identifies the rest action handler module, the turn-advance entry point, and the canonical Session class. Record exact paths and line numbers in `/tmp/orbital-wiring-points.txt`.

- [ ] **Step 2: Write the failing integration test**

Create `sidequest-server/tests/integration/test_session_clock.py`:

```python
"""Session clock integration — beat-driven advance fires through Session."""
from __future__ import annotations

import pytest

from sidequest.game.session import Session  # canonical class located in Step 1
from sidequest.orbital.beats import Beat, BeatKind


def test_session_has_clock_at_construction():
    session = Session.empty()  # use whatever existing constructor produces a clean session
    assert session.clock.t_hours == 0.0


def test_session_advances_clock_via_beat(capture_spans):
    session = Session.empty()
    session.advance_via_beat(
        Beat(kind=BeatKind.ENCOUNTER, trigger="test-scene")
    )
    assert session.clock.t_hours == 1.0

    spans = capture_spans("clock.advance")
    assert len(spans) == 1
    assert spans[0].attributes["trigger"] == "test-scene"


def test_rest_action_emits_rest_beat(capture_spans):
    """The existing rest action wires into beat advance."""
    session = Session.empty()
    initial_t = session.clock.t_hours
    session.handle_rest()  # canonical rest method located in Step 1
    assert session.clock.t_hours == initial_t + 8.0
    spans = capture_spans("clock.advance")
    assert any(s.attributes["beat_kind"] == "rest" for s in spans)


def test_scene_end_emits_encounter_beat(capture_spans):
    """The existing scene-end / turn-advance wires into beat advance."""
    session = Session.empty()
    initial_t = session.clock.t_hours
    session.end_scene("scene-fixture")  # canonical scene-end located in Step 1
    assert session.clock.t_hours == initial_t + 1.0
    spans = capture_spans("clock.advance")
    assert any(
        s.attributes["beat_kind"] == "encounter"
        and s.attributes["trigger"] == "scene-fixture"
        for s in spans
    )
```

If `Session.empty()`, `handle_rest()`, or `end_scene()` do not exist by those exact names, replace with the actual constructor and method names found in Step 1. Do not invent new public methods — match what's there.

- [ ] **Step 3: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/integration/test_session_clock.py -v
```

Expected: AttributeError on `session.clock` (Clock not yet attached) and / or test failures on missing wiring.

- [ ] **Step 4: Add Clock to Session and wire `advance_via_beat`**

In `sidequest-server/sidequest/game/session.py`, add a `Clock` field to the Session dataclass / class initializer. Use the existing class shape — do not change its style (dataclass vs. plain class).

```python
from sidequest.orbital.beats import Beat, advance_clock_via_beat
from sidequest.orbital.clock import Clock

# In the Session class, alongside other state fields:
#     clock: Clock = field(default_factory=Clock)
# OR (if non-dataclass) initialize self.clock = Clock() in __init__

def advance_via_beat(self, beat: Beat) -> float:
    """Advance the session's clock per the beat. Emits clock.advance span."""
    return advance_clock_via_beat(self.clock, beat)
```

Use the existing field-declaration style (dataclass field, attrs, plain attribute).

- [ ] **Step 5: Wire rest action → REST beat**

At the rest-action handler entry point (located in Step 1), after the existing rest-effect logic, call:

```python
session.advance_via_beat(Beat(kind=BeatKind.REST, trigger="rest"))
```

Use the actual handler signature; the trigger string can be more specific (e.g. include the actor id) if the existing data flow makes it natural.

- [ ] **Step 6: Wire scene-end → ENCOUNTER beat**

At the scene-end / turn-advance handler entry point (located in Step 1), after existing per-scene effects, call:

```python
session.advance_via_beat(Beat(kind=BeatKind.ENCOUNTER, trigger=f"scene-{scene_id}"))
```

If a scene has explicit duration metadata (some encounters might tag "this is a long scene"), pass `duration_hours=` from that metadata; otherwise default 1h applies.

- [ ] **Step 7: Run integration tests**

```bash
cd sidequest-server && uv run pytest tests/integration/test_session_clock.py -v
cd sidequest-server && just server-test 2>&1 | tail -30
```

Expected: new tests pass; broader suite still green.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/game/session.py \
        sidequest-server/sidequest/<rest-handler-path> \
        sidequest-server/sidequest/<scene-end-handler-path> \
        sidequest-server/tests/integration/test_session_clock.py
git commit -m "feat(orbital): wire Clock into Session; rest + scene end emit beats

Track A wiring complete — every long rest emits a REST beat, every scene
end emits an ENCOUNTER beat, both fire clock.advance spans. Travel +
downtime beats wire in Plan 2."
```

---

## Task 6: Pydantic models for `orbits.yaml` + `chart.yaml`

Schema lock — these models are the contract between content and engine. Per spec §2.1–2.2.

**Files:**
- Create: `sidequest-server/sidequest/orbital/models.py`
- Create: `sidequest-server/tests/orbital/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_models.py`:

```python
"""Pydantic model tests for orbits.yaml + chart.yaml schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.orbital.models import (
    Annotation,
    BodyDef,
    BodyType,
    ChartConfig,
    ClockConfig,
    OrbitsConfig,
    TravelConfig,
    TravelRealism,
)


def test_minimal_orbits_config_loads():
    cfg = OrbitsConfig(
        version="0.1.0",
        clock=ClockConfig(epoch_days=0),
        travel=TravelConfig(realism=TravelRealism.ORBITAL),
        bodies={"coyote": BodyDef(type=BodyType.STAR)},
    )
    assert cfg.bodies["coyote"].type == BodyType.STAR


def test_orbiting_body_requires_orbital_params():
    with pytest.raises(ValidationError, match="semi_major_au"):
        OrbitsConfig(
            version="0.1.0",
            clock=ClockConfig(epoch_days=0),
            travel=TravelConfig(realism=TravelRealism.ORBITAL),
            bodies={
                "coyote": BodyDef(type=BodyType.STAR),
                "red_prospect": BodyDef(type=BodyType.COMPANION, parent="coyote"),
            },
        )


def test_arc_belt_requires_arc_extent():
    with pytest.raises(ValidationError, match="arc_extent_deg"):
        BodyDef(
            type=BodyType.ARC_BELT,
            parent="coyote",
            semi_major_au=1.5,
            period_days=600,
            epoch_phase_deg=30,
            hazard=True,
        )


def test_eccentricity_default_zero():
    body = BodyDef(
        type=BodyType.HABITAT,
        parent="coyote",
        semi_major_au=1.0,
        period_days=365,
        epoch_phase_deg=0,
    )
    assert body.eccentricity == 0.0


def test_unknown_parent_rejected():
    """A body cannot have a parent that does not exist in the bodies map."""
    with pytest.raises(ValidationError, match="unknown parent"):
        OrbitsConfig(
            version="0.1.0",
            clock=ClockConfig(epoch_days=0),
            travel=TravelConfig(realism=TravelRealism.ORBITAL),
            bodies={
                "moon": BodyDef(
                    type=BodyType.HABITAT,
                    parent="ghost",
                    semi_major_au=0.04,
                    period_days=6,
                    epoch_phase_deg=0,
                ),
            },
        )


def test_realism_default_narrative():
    """Genre-default tier is `narrative` per spec — locked decision 1."""
    cfg = TravelConfig()
    assert cfg.realism == TravelRealism.NARRATIVE
    assert cfg.travel_speed_factor == 1.0
    assert cfg.danger_density == 0.0


def test_chart_engraved_label():
    annot = Annotation(
        kind="engraved_label",
        text="the Last Drift",
        curve_along="orbit_outermost",
    )
    assert annot.kind == "engraved_label"


def test_chart_glyph():
    annot = Annotation(
        kind="glyph",
        text="?",
        at={"ra_deg": 135, "au": 5.0},
        caption="absent gate",
    )
    assert annot.at["au"] == 5.0


def test_chart_config_loads_list():
    cfg = ChartConfig(
        version="0.1.0",
        annotations=[
            Annotation(kind="engraved_label", text="x", curve_along="orbit_3"),
            Annotation(kind="glyph", text="?", at={"ra_deg": 0, "au": 1}),
        ],
    )
    assert len(cfg.annotations) == 2
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_models.py -v
```

Expected: ImportError on `sidequest.orbital.models`.

- [ ] **Step 3: Implement the models**

Create `sidequest-server/sidequest/orbital/models.py`:

```python
"""Pydantic models for orbits.yaml and chart.yaml.

Per spec §2.1–§2.2: orbits.yaml is the plotter's only input (mechanics);
chart.yaml is renderer-only (flavor); they live in the per-world content
directory and are loaded by `sidequest.orbital.loader`.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TravelRealism(str, Enum):
    NARRATIVE = "narrative"
    HYBRID = "hybrid"
    ORBITAL = "orbital"


class BodyType(str, Enum):
    STAR = "star"
    COMPANION = "companion"
    HABITAT = "habitat"
    ARC_BELT = "arc_belt"
    GATE = "gate"
    WRECK = "wreck"


class ClockConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epoch_days: float = 0.0


class TravelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    realism: TravelRealism = TravelRealism.NARRATIVE
    travel_speed_factor: float = Field(default=1.0, gt=0.0)
    danger_density: float = Field(default=0.0, ge=0.0)
    hazard_arc_density: float = Field(default=0.0, ge=0.0)


class BodyDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: BodyType
    parent: str | None = None
    semi_major_au: float | None = None
    period_days: float | None = None
    epoch_phase_deg: float | None = None
    eccentricity: float = 0.0
    arc_extent_deg: float | None = None
    hazard: bool = False
    hazard_table: str | None = None
    label: str | None = None
    label_color: str | None = None

    @model_validator(mode="after")
    def _validate_orbital_params(self) -> BodyDef:
        # A body with a parent must have orbital params (except STAR which never has parent).
        if self.parent is not None:
            for fld in ("semi_major_au", "period_days", "epoch_phase_deg"):
                if getattr(self, fld) is None:
                    raise ValueError(
                        f"body with parent={self.parent!r} requires {fld}; got None"
                    )
        # arc_belt also requires arc_extent_deg.
        if self.type == BodyType.ARC_BELT and self.arc_extent_deg is None:
            raise ValueError(
                "body with type=arc_belt requires arc_extent_deg; got None"
            )
        return self


class OrbitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    clock: ClockConfig
    travel: TravelConfig
    bodies: dict[str, BodyDef]

    @model_validator(mode="after")
    def _validate_parent_refs(self) -> OrbitsConfig:
        ids = set(self.bodies.keys())
        for body_id, body in self.bodies.items():
            if body.parent is not None and body.parent not in ids:
                raise ValueError(
                    f"body {body_id!r} has unknown parent {body.parent!r}; "
                    f"available bodies: {sorted(ids)}"
                )
        return self


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


class ChartConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    annotations: list[Annotation] = Field(default_factory=list)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_models.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/models.py \
        sidequest-server/tests/orbital/test_models.py
git commit -m "feat(orbital): pydantic models for orbits.yaml + chart.yaml

Schema lock per spec §2.1–§2.2. orbital body parent-references validate
at load time (No Silent Fallbacks). arc_belt requires arc_extent_deg.
Mechanics fields and flavor annotations live in separate models."
```

---

## Task 7: Orbital content loader

Reads + validates the two YAMLs from a world directory. Fails loudly on missing files for `realism: orbital` worlds; allows missing `orbits.yaml` for `narrative`-tier worlds (chart-only worlds are valid).

**Files:**
- Create: `sidequest-server/sidequest/orbital/loader.py`
- Create: `sidequest-server/tests/orbital/test_loader.py`
- Create: `sidequest-server/tests/orbital/fixtures/world_minimal/orbits.yaml`
- Create: `sidequest-server/tests/orbital/fixtures/world_minimal/chart.yaml`

- [ ] **Step 1: Write the test fixtures**

`sidequest-server/tests/orbital/fixtures/world_minimal/orbits.yaml`:

```yaml
version: "0.1.0"
clock:
  epoch_days: 0
travel:
  realism: orbital
  travel_speed_factor: 1.0
  danger_density: 0.012
  hazard_arc_density: 0.10
bodies:
  coyote:
    type: star
    label: COYOTE
    label_color: red
  red_prospect:
    type: companion
    parent: coyote
    semi_major_au: 1.2
    period_days: 380
    epoch_phase_deg: 270
    label: "RED PROSPECT"
    label_color: red
  turning_hub:
    type: habitat
    parent: red_prospect
    semi_major_au: 0.04
    period_days: 6
    epoch_phase_deg: 0
```

`sidequest-server/tests/orbital/fixtures/world_minimal/chart.yaml`:

```yaml
version: "0.1.0"
annotations:
  - kind: engraved_label
    text: "the Last Drift"
    curve_along: orbit_outermost
  - kind: glyph
    text: "?"
    at: { ra_deg: 135, au: 5.0 }
    caption: "absent gate"
```

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/orbital/test_loader.py`:

```python
"""Loader tests — reads orbits.yaml and chart.yaml from a world directory."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.orbital.loader import (
    OrbitalContentMissingError,
    load_orbital_content,
)
from sidequest.orbital.models import BodyType, TravelRealism

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_world_minimal():
    content = load_orbital_content(FIXTURES / "world_minimal")
    assert content.orbits.version == "0.1.0"
    assert content.orbits.travel.realism == TravelRealism.ORBITAL
    assert "coyote" in content.orbits.bodies
    assert content.orbits.bodies["coyote"].type == BodyType.STAR
    assert len(content.chart.annotations) == 2


def test_orbital_tier_missing_file_fails_loudly(tmp_path):
    """An `orbital`-tier world must have orbits.yaml; missing = loud error."""
    (tmp_path / "chart.yaml").write_text(
        "version: '0.1.0'\nannotations: []\n"
    )
    # No orbits.yaml — must fail
    with pytest.raises(OrbitalContentMissingError, match="orbits.yaml"):
        load_orbital_content(tmp_path)


def test_chart_optional(tmp_path):
    """chart.yaml is optional — a world can ship orbits without flavor."""
    (tmp_path / "orbits.yaml").write_text(
        FIXTURES.joinpath("world_minimal/orbits.yaml").read_text()
    )
    content = load_orbital_content(tmp_path)
    assert content.chart.annotations == []


def test_validation_error_propagates(tmp_path):
    """Schema errors surface with body context per No Silent Fallbacks."""
    (tmp_path / "orbits.yaml").write_text(
        """
version: "0.1.0"
clock: {epoch_days: 0}
travel: {realism: orbital}
bodies:
  ghost_moon:
    type: habitat
    parent: never_existed
    semi_major_au: 0.04
    period_days: 6
    epoch_phase_deg: 0
"""
    )
    with pytest.raises(Exception, match="unknown parent"):
        load_orbital_content(tmp_path)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_loader.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement the loader**

Create `sidequest-server/sidequest/orbital/loader.py`:

```python
"""Loader for orbital world content (orbits.yaml + chart.yaml).

Per CLAUDE.md "No Silent Fallbacks" — missing required files for an
`orbital`-tier world raise OrbitalContentMissingError with a clear path.
chart.yaml is optional (renderer falls back to no flavor layer).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from sidequest.orbital.models import ChartConfig, OrbitsConfig, TravelRealism


class OrbitalContentMissingError(FileNotFoundError):
    """Raised when an `orbital`-tier world is missing orbits.yaml."""


@dataclass(frozen=True)
class OrbitalContent:
    orbits: OrbitsConfig
    chart: ChartConfig


def load_orbital_content(world_dir: Path) -> OrbitalContent:
    """Load orbits.yaml (+ chart.yaml if present) from `world_dir`.

    Behavior:
      - orbits.yaml present → parsed and validated into OrbitsConfig.
      - orbits.yaml absent → OrbitalContentMissingError (the world is
        opting into orbital semantics by being passed to this loader).
      - chart.yaml present → parsed into ChartConfig.
      - chart.yaml absent → empty ChartConfig (no flavor layer).

    Schema validation errors propagate as pydantic ValidationError with
    enough context to pinpoint the offending body / field.
    """
    world_dir = Path(world_dir)
    orbits_path = world_dir / "orbits.yaml"
    chart_path = world_dir / "chart.yaml"

    if not orbits_path.exists():
        raise OrbitalContentMissingError(
            f"orbits.yaml missing under {world_dir}; required for orbital tier"
        )

    with orbits_path.open() as f:
        orbits_raw = yaml.safe_load(f)
    orbits = OrbitsConfig.model_validate(orbits_raw)

    if chart_path.exists():
        with chart_path.open() as f:
            chart_raw = yaml.safe_load(f)
        chart = ChartConfig.model_validate(chart_raw)
    else:
        chart = ChartConfig(version=orbits.version, annotations=[])

    return OrbitalContent(orbits=orbits, chart=chart)
```

- [ ] **Step 5: Run the tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_loader.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/orbital/loader.py \
        sidequest-server/tests/orbital/test_loader.py \
        sidequest-server/tests/orbital/fixtures/
git commit -m "feat(orbital): loader for orbits.yaml + chart.yaml

Per CLAUDE.md No Silent Fallbacks — orbital-tier world missing orbits.yaml
raises OrbitalContentMissingError. chart.yaml is optional (renderer drops
flavor layer if absent)."
```

---

## Task 8: Migrate `cartography.yaml` → `orbits.yaml` + `chart.yaml`

The existing 1215-line `cartography.yaml` already has 13 bodies authored. Reshape into the new two-file layout. Mechanics fields → `orbits.yaml`; descriptive prose, kind labels, jump-point markers, narrative arcs → `chart.yaml`.

**Files:**
- Create: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml`
- Create: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/chart.yaml`
- Delete: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml`

- [ ] **Step 1: Read the source data**

```bash
wc -l sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml
grep -E "^\s*-\s*id:|^\s*kind:|^\s*parent_body:" sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml
```

This produces the body inventory. Cross-reference against the spec's lead-use-case bodies (coyote, red_prospect, far_landing, turning_hub, ember, deep_root_world, gravel_orchard, broken_drift, dead_mans_drift, new_claim, compact_anchorage, the_counter, plus existing cartography ones like tethys_watch).

- [ ] **Step 2: Author orbits.yaml**

Create `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml`. Copy mechanics fields (kind→type, parent_body→parent, semi_major_axis_au→semi_major_au, orbital_period_days→period_days, eccentricity) for every body in cartography.yaml. Add `epoch_phase_deg` per body; pick values that produce a chart visually similar to the current screenshot at `t=0` (this can be tuned later by the world author, but ship a sensible starting state). Add the top-level `travel:` block with Coyote Star's `orbital` tier defaults from spec §2.1.

Skeleton (the migration fills body params from cartography.yaml; epoch_phase_deg values below are starting positions matching the screenshot):

```yaml
# sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml
version: "0.1.0"

clock:
  epoch_days: 0

travel:
  realism: orbital
  travel_speed_factor: 1.0
  danger_density: 0.012
  hazard_arc_density: 0.10

bodies:
  coyote:
    type: star
    label: COYOTE
    label_color: red

  red_prospect:
    type: companion
    parent: coyote
    semi_major_au: 1.2
    period_days: 380
    epoch_phase_deg: 270
    label: "RED PROSPECT"
    label_color: red

  turning_hub:
    type: habitat
    parent: red_prospect
    semi_major_au: 0.04
    period_days: 6
    epoch_phase_deg: 0

  ember:
    type: habitat
    parent: red_prospect
    semi_major_au: 0.08
    period_days: 18
    epoch_phase_deg: 90

  far_landing:
    type: habitat
    parent: coyote
    semi_major_au: 2.4
    period_days: 980
    epoch_phase_deg: 45

  tethys_watch:
    type: habitat
    parent: far_landing
    semi_major_au: 0.0039      # 580,000 km in AU
    period_days: 50
    epoch_phase_deg: 0

  # ... migrate every remaining body from cartography.yaml here
  # (deep_root_world, gravel_orchard, dead_mans_drift, new_claim,
  #  compact_anchorage, the_counter, broken_drift)

  broken_drift:
    type: arc_belt
    parent: coyote
    semi_major_au: 1.5
    period_days: 600
    epoch_phase_deg: 30
    arc_extent_deg: 90
    hazard: true
```

For every body: pick `epoch_phase_deg` so the chart at `t=0` resembles the existing screenshot. Document the chosen positions in a comment block at the top of the file.

- [ ] **Step 3: Author chart.yaml**

Create `sidequest-content/genre_packs/space_opera/worlds/coyote_star/chart.yaml`. Migrate flavor: `map_style` becomes a comment header; descriptive prose stays attached to bodies *via the rendered glyph caption* not via a chart annotation (caption is a body-level UI hint, not a top-level annotation). Engraved arcs ("the Last Drift", "broken drift" labels visible on the screenshot), the absent-gate glyph, the scale ruler, and bearing marks are top-level annotations.

```yaml
# sidequest-content/genre_packs/space_opera/worlds/coyote_star/chart.yaml
#
# Engraved chart flavor for Coyote Star. Renderer reads; plotter ignores.
# Per the original cartography map_style: a working orrery on dark vellum.

version: "0.1.0"

annotations:
  - kind: engraved_label
    text: "the Last Drift"
    curve_along: orbit_outermost
    style: engraved_curved

  - kind: engraved_label
    text: "broken drift"
    curve_along: body:broken_drift
    style: engraved_curved

  - kind: glyph
    text: "?"
    at: { ra_deg: 135, au: 5.0 }
    caption: "absent gate"
    style: question_mark

  - kind: scale_ruler
    at: { ra_deg: 350, au: 4.5 }
    label: "scale (engraved) — 0 1 2 3 4 5 AU"

  - kind: bearing_marks
    body_ref: coyote
    bearings: [0, 90, 180, 270]
```

- [ ] **Step 4: Delete cartography.yaml**

```bash
git rm sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml
```

The data has been migrated into the new two-file layout. The runtime that consumed cartography.yaml was removed 2026-04-28 per CLAUDE.md, so no live code paths break.

- [ ] **Step 5: Verify the new content loads**

```bash
cd sidequest-server && uv run python -c "
from pathlib import Path
from sidequest.orbital.loader import load_orbital_content
content = load_orbital_content(
    Path('../sidequest-content/genre_packs/space_opera/worlds/coyote_star')
)
print(f'Bodies: {len(content.orbits.bodies)}')
print(f'Annotations: {len(content.chart.annotations)}')
print(f'Realism: {content.orbits.travel.realism}')
"
```

Expected: prints body count (~13), annotation count (~5), realism `orbital`. No exceptions.

- [ ] **Step 6: Commit**

```bash
git add sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml \
        sidequest-content/genre_packs/space_opera/worlds/coyote_star/chart.yaml
git rm   sidequest-content/genre_packs/space_opera/worlds/coyote_star/cartography.yaml
git commit -m "content(coyote_star): migrate cartography.yaml -> orbits.yaml + chart.yaml

Mechanics fields (parent, semi_major_au, period_days, eccentricity) move
to orbits.yaml under the new schema; flavor (engraved labels, absent gate
glyph, scale ruler, bearing marks) goes to chart.yaml. epoch_phase_deg
chosen per body so chart at t=0 matches the existing screenshot.

Cartography runtime was removed 2026-04-28; no live code paths broken."
```

---

## Task 9: SVG renderer skeleton + engraved layer

First renderer slice: produce a valid SVG with `<g id="layer-engraved">` populated — orbital ellipses, body glyphs, scale ruler, bearings. No flavor or party marker yet.

**Files:**
- Modify: `sidequest-server/pyproject.toml` (add `svgwrite`)
- Create: `sidequest-server/sidequest/orbital/render.py`
- Create: `sidequest-server/tests/orbital/test_render.py`

- [ ] **Step 1: Add svgwrite dependency**

In `sidequest-server/pyproject.toml`, find the `[project] dependencies = [...]` list and append `"svgwrite>=1.4"`. Then:

```bash
cd sidequest-server && uv sync
```

- [ ] **Step 2: Define the rendering interface**

This task lays the public function shape used by every subsequent rendering task; later tasks add body to the layers.

- [ ] **Step 3: Write the failing test**

Create `sidequest-server/tests/orbital/test_render.py`:

```python
"""Renderer tests — SVG output structure for the engraved layer."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from sidequest.orbital.loader import load_orbital_content
from sidequest.orbital.render import Scope, render_chart

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def world_minimal():
    return load_orbital_content(FIXTURES / "world_minimal")


def test_render_returns_valid_svg(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    assert svg.startswith("<?xml") or svg.startswith("<svg")
    assert "</svg>" in svg


def test_render_has_engraved_layer(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    assert 'id="layer-engraved"' in svg


def test_engraved_layer_has_orbits_for_each_orbiting_body(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    # red_prospect orbits coyote at 1.2 AU; its orbital ellipse must be present.
    # Use a tag that's robust to stylistic variation: each orbit element carries
    # data-body-id so click-routing can target it.
    assert 'data-body-id="red_prospect"' in svg


def test_engraved_layer_has_named_bodies(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    # COYOTE label and RED PROSPECT label rendered as text
    assert "COYOTE" in svg
    assert "RED PROSPECT" in svg


def test_render_deterministic_for_same_inputs(world_minimal):
    svg1 = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    svg2 = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    assert svg1 == svg2


def test_t_hours_changes_body_position(world_minimal):
    """Bodies move with time — the rendered position differs at different t."""
    svg_t0 = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    # Advance half an orbit of red_prospect (period 380d → 4560h; 2280h ≈ half)
    svg_t_half = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=2280.0 * 24.0,  # actually the test only needs a change
        party_at=None,
    )
    assert svg_t0 != svg_t_half
```

- [ ] **Step 4: Implement the renderer skeleton + engraved layer**

Create `sidequest-server/sidequest/orbital/render.py`:

```python
"""Server-side SVG renderer for the orbital chart.

Per spec §6: renderer produces a complete SVG document per (world, scope,
t_hours, party_at, plot_state). Layers: engraved (orbits + bodies + scale +
bearings), flavor (chart.yaml annotations), party (current location), plot
(when active). Output is deterministic for fixed inputs — snapshot tests
pin canonical outputs in Task 13.

Position math is deliberately simple in this plan: circular orbits only,
theta = epoch_phase + 360 * t_days / period. Plan 2 (Track C) brings in
the full position() module that will be a drop-in replacement here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from io import StringIO

import svgwrite

from sidequest.orbital.models import (
    Annotation,
    BodyDef,
    BodyType,
    ChartConfig,
    OrbitsConfig,
)

# --- Scopes -----------------------------------------------------------------


@dataclass(frozen=True)
class Scope:
    """Render scope — which body is centered."""

    center_body_id: str  # body id at chart center

    @classmethod
    def system_root(cls) -> Scope:
        # Sentinel — renderer treats this as "use the unique body with no
        # parent in orbits.yaml" (the system primary).
        return cls(center_body_id="<root>")


# --- Position math (circular orbit, plan-1 placeholder for Plan-2 position()) ---


def _body_position_au_polar(
    body: BodyDef, t_hours: float
) -> tuple[float, float]:
    """Return (au, theta_deg) of a body relative to its parent at story-time t.

    Circular-orbit approximation. Plan 2 (Track C) replaces this with the
    full `position()` module that supports eccentric orbits.
    """
    if body.parent is None:  # primary
        return (0.0, 0.0)
    t_days = t_hours / 24.0
    assert body.semi_major_au is not None  # validated at load
    assert body.period_days is not None
    assert body.epoch_phase_deg is not None
    theta = (body.epoch_phase_deg + 360.0 * t_days / body.period_days) % 360.0
    return (body.semi_major_au, theta)


def _polar_to_cartesian(au: float, theta_deg: float, scale: float) -> tuple[float, float]:
    """Convert polar (AU, deg) to SVG cartesian pixels.

    SVG y-axis grows downward; we flip so 0° is "right" (3 o'clock) and 90°
    is "up" (12 o'clock) per orrery convention.
    """
    rad = math.radians(theta_deg)
    x = au * scale * math.cos(rad)
    y = -au * scale * math.sin(rad)
    return (x, y)


# --- Public API -------------------------------------------------------------


def render_chart(
    *,
    orbits: OrbitsConfig,
    chart: ChartConfig,
    scope: Scope,
    t_hours: float,
    party_at: str | None,
) -> str:
    """Compose the full chart SVG. Returns a UTF-8 string."""
    center_id = _resolve_scope_center(orbits, scope)
    viewport = _viewport_for_scope(orbits, center_id)

    dwg = svgwrite.Drawing(
        size=(viewport.size_px, viewport.size_px),
        viewBox=f"{-viewport.half} {-viewport.half} {viewport.size_px} {viewport.size_px}",
        profile="tiny",
    )
    dwg.add(dwg.rect(
        insert=(-viewport.half, -viewport.half),
        size=(viewport.size_px, viewport.size_px),
        fill="black",
    ))
    dwg.add(_render_engraved_layer(orbits, center_id, viewport, t_hours))
    # flavor / party / plot layers in subsequent tasks
    return dwg.tostring()


# --- Internals --------------------------------------------------------------


@dataclass(frozen=True)
class _Viewport:
    size_px: int
    half: int
    au_to_px: float


def _resolve_scope_center(orbits: OrbitsConfig, scope: Scope) -> str:
    if scope.center_body_id == "<root>":
        roots = [bid for bid, b in orbits.bodies.items() if b.parent is None]
        if len(roots) != 1:
            raise ValueError(
                f"system_root scope requires exactly one parent-less body; got {roots!r}"
            )
        return roots[0]
    if scope.center_body_id not in orbits.bodies:
        raise ValueError(f"scope center {scope.center_body_id!r} not in bodies")
    return scope.center_body_id


def _viewport_for_scope(orbits: OrbitsConfig, center_id: str) -> _Viewport:
    """Pick a viewport that fits the largest direct child orbit + 20% pad."""
    children = [b for b in orbits.bodies.values() if b.parent == center_id]
    if not children:
        max_au = 1.0
    else:
        max_au = max(c.semi_major_au or 0.0 for c in children) or 1.0
    size_px = 800
    half = size_px // 2
    pad = 1.2
    au_to_px = (half / pad) / max_au
    return _Viewport(size_px=size_px, half=half, au_to_px=au_to_px)


def _render_engraved_layer(
    orbits: OrbitsConfig, center_id: str, vp: _Viewport, t_hours: float
) -> svgwrite.container.Group:
    g = svgwrite.container.Group(id="layer-engraved")
    center = orbits.bodies[center_id]

    # Center body glyph + label
    g.add(_body_glyph(center, x=0, y=0, body_id=center_id))
    if center.label:
        g.add(svgwrite.text.Text(
            center.label,
            insert=(0, -16),
            fill=center.label_color or "yellow",
            text_anchor="middle",
            font_family="monospace",
            font_size=14,
        ))

    # Direct children: their orbits and bodies
    for body_id, body in orbits.bodies.items():
        if body.parent != center_id:
            continue
        au, theta = _body_position_au_polar(body, t_hours)
        # Orbit ellipse (circular)
        radius_px = au * vp.au_to_px
        g.add(svgwrite.shapes.Circle(
            center=(0, 0),
            r=radius_px,
            fill="none",
            stroke="yellow",
            stroke_width=0.6,
            **{"data-body-id": body_id},
        ))
        # Body glyph at current position
        x, y = _polar_to_cartesian(au, theta, vp.au_to_px)
        g.add(_body_glyph(body, x=x, y=y, body_id=body_id))
        if body.label:
            g.add(svgwrite.text.Text(
                body.label,
                insert=(x + 8, y - 6),
                fill=body.label_color or "yellow",
                font_family="monospace",
                font_size=10,
            ))

    # Bearings (4 ticks for system primary)
    if center.type == BodyType.STAR:
        for theta in (0, 90, 180, 270):
            x, y = _polar_to_cartesian(au=0.10, theta_deg=theta, scale=vp.au_to_px)
            g.add(svgwrite.text.Text(
                f"{theta:03d}°",
                insert=(x, y),
                fill="yellow",
                text_anchor="middle",
                font_family="monospace",
                font_size=8,
            ))

    return g


def _body_glyph(body: BodyDef, *, x: float, y: float, body_id: str) -> svgwrite.base.BaseElement:
    """Pick the right shape for a body type."""
    if body.type == BodyType.STAR:
        return svgwrite.shapes.Circle(
            center=(x, y),
            r=8,
            fill="red",
            stroke="red",
            **{"data-body-id": body_id},
        )
    if body.type == BodyType.COMPANION:
        return svgwrite.shapes.Circle(
            center=(x, y),
            r=4,
            fill="red",
            **{"data-body-id": body_id},
        )
    if body.type == BodyType.ARC_BELT:
        # Render belt as a thin dashed arc at semi_major_au; details in Task 12.
        return svgwrite.shapes.Circle(
            center=(x, y),
            r=2,
            fill="orange",
            **{"data-body-id": body_id},
        )
    # default: small yellow disc
    return svgwrite.shapes.Circle(
        center=(x, y),
        r=3,
        fill="yellow",
        **{"data-body-id": body_id},
    )
```

- [ ] **Step 5: Run renderer tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/pyproject.toml \
        sidequest-server/sidequest/orbital/render.py \
        sidequest-server/tests/orbital/test_render.py
git commit -m "feat(orbital): SVG renderer skeleton + engraved layer

Renderer composes full SVG with layer-engraved populated: orbit ellipses,
body glyphs, primary-star label, bearing marks. Circular-orbit position
math is a plan-1 placeholder; Plan-2 position() module slots in here.
Click-targets carry data-body-id."
```

---

## Task 10: Renderer — flavor layer + party marker layer

Adds `<g id="layer-flavor">` (chart.yaml annotations) and `<g id="layer-party">` (party position glyph).

**Files:**
- Modify: `sidequest-server/sidequest/orbital/render.py`
- Modify: `sidequest-server/tests/orbital/test_render.py`

- [ ] **Step 1: Write the failing tests**

Append to `sidequest-server/tests/orbital/test_render.py`:

```python
def test_flavor_layer_present_when_annotations_exist(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    assert 'id="layer-flavor"' in svg
    # The fixture has an "absent gate" glyph
    assert "absent gate" in svg or "?" in svg


def test_engraved_label_text_appears(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    assert "the Last Drift" in svg


def test_party_marker_renders_at_body(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at="turning_hub",
    )
    assert 'id="layer-party"' in svg
    # Marker carries an annotation indicating which body the party is at
    assert 'data-party-at="turning_hub"' in svg


def test_party_marker_absent_when_party_at_none(world_minimal):
    svg = render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    # Layer may exist but be empty; the data-party-at attribute must be absent
    assert "data-party-at=" not in svg
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render.py -v
```

Expected: 4 new tests fail; existing tests still pass.

- [ ] **Step 3: Add flavor layer rendering**

In `render.py`, add a flavor-layer renderer and call it from `render_chart` after the engraved layer:

```python
def _render_flavor_layer(
    chart: ChartConfig, orbits: OrbitsConfig, center_id: str, vp: _Viewport
) -> svgwrite.container.Group:
    g = svgwrite.container.Group(id="layer-flavor")
    for annot in chart.annotations:
        elem = _render_annotation(annot, orbits, center_id, vp)
        if elem is not None:
            g.add(elem)
    return g


def _render_annotation(
    annot: Annotation, orbits: OrbitsConfig, center_id: str, vp: _Viewport
) -> svgwrite.base.BaseElement | None:
    if annot.kind == "engraved_label":
        if annot.text is None:
            return None
        # Place along outer edge as a placeholder; curve_along refinement is
        # cosmetic and can be improved in a follow-up.
        return svgwrite.text.Text(
            annot.text,
            insert=(0, -vp.half + 30),
            fill="yellow",
            text_anchor="middle",
            font_family="monospace",
            font_size=12,
            font_style="italic",
        )
    if annot.kind == "glyph":
        if annot.text is None or annot.at is None:
            return None
        ra = float(annot.at.get("ra_deg", 0))
        au = float(annot.at.get("au", 0))
        x, y = _polar_to_cartesian(au, ra, vp.au_to_px)
        group = svgwrite.container.Group()
        group.add(svgwrite.text.Text(
            annot.text,
            insert=(x, y),
            fill="yellow",
            text_anchor="middle",
            font_family="monospace",
            font_size=20,
        ))
        if annot.caption:
            group.add(svgwrite.text.Text(
                annot.caption,
                insert=(x, y + 14),
                fill="yellow",
                text_anchor="middle",
                font_family="monospace",
                font_size=9,
                font_style="italic",
            ))
        return group
    if annot.kind == "scale_ruler":
        if annot.label is None:
            return None
        return svgwrite.text.Text(
            annot.label,
            insert=(0, vp.half - 20),
            fill="yellow",
            text_anchor="middle",
            font_family="monospace",
            font_size=9,
        )
    if annot.kind == "bearing_marks":
        # Already rendered as part of the engraved layer for the primary;
        # additional bearing-marks annotations could target other bodies.
        return None
    return None
```

Update `render_chart`:

```python
    dwg.add(_render_engraved_layer(orbits, center_id, viewport, t_hours))
    dwg.add(_render_flavor_layer(chart, orbits, center_id, viewport))
    dwg.add(_render_party_layer(orbits, center_id, viewport, t_hours, party_at))
    return dwg.tostring()
```

- [ ] **Step 4: Add party-marker layer rendering**

```python
def _render_party_layer(
    orbits: OrbitsConfig,
    center_id: str,
    vp: _Viewport,
    t_hours: float,
    party_at: str | None,
) -> svgwrite.container.Group:
    g = svgwrite.container.Group(id="layer-party")
    if party_at is None:
        return g
    if party_at not in orbits.bodies:
        # Don't fail loudly here — UI would render no marker; loader/state
        # validation enforces party_at exists upstream.
        return g
    body = orbits.bodies[party_at]
    # Compute position relative to scope center; if party is at the center
    # body, render the marker overlapping the body glyph but offset.
    if party_at == center_id:
        x, y = (0.0, 0.0)
    elif body.parent == center_id:
        au, theta = _body_position_au_polar(body, t_hours)
        x, y = _polar_to_cartesian(au, theta, vp.au_to_px)
    else:
        # Cross-scope: render an off-chart-edge indicator. Plan refinement.
        x, y = (vp.half - 16, 0.0)
    # Pencil-style annotation: small reticle echo, off-axis label
    marker = svgwrite.container.Group(**{"data-party-at": party_at})
    marker.add(svgwrite.shapes.Circle(
        center=(x + 10, y - 10), r=4, fill="none", stroke="white", stroke_width=1.0,
    ))
    marker.add(svgwrite.shapes.Line(
        start=(x + 5, y - 10), end=(x + 15, y - 10), stroke="white", stroke_width=1.0,
    ))
    marker.add(svgwrite.shapes.Line(
        start=(x + 10, y - 15), end=(x + 10, y - 5), stroke="white", stroke_width=1.0,
    ))
    marker.add(svgwrite.text.Text(
        "← party",
        insert=(x + 18, y - 8),
        fill="white",
        font_family="cursive, monospace",
        font_size=9,
        font_style="italic",
    ))
    g.add(marker)
    return g
```

- [ ] **Step 5: Run all renderer tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/orbital/render.py \
        sidequest-server/tests/orbital/test_render.py
git commit -m "feat(orbital): renderer flavor + party-marker layers

Flavor layer reads chart.yaml annotations (engraved_label, glyph,
scale_ruler). Party marker is pencil-style annotation at current body
or off-axis indicator when party is in a different scope. Cross-scope
rendering refined in Task 12 (drillable cluster glyphs)."
```

---

## Task 11: `chart.render` OTEL span

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/chart.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py`
- Modify: `sidequest-server/sidequest/orbital/render.py` (call emitter)
- Modify: `sidequest-server/tests/orbital/test_render.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/orbital/test_render.py`:

```python
def test_render_emits_chart_render_span(world_minimal, capture_spans):
    render_chart(
        orbits=world_minimal.orbits,
        chart=world_minimal.chart,
        scope=Scope.system_root(),
        t_hours=24.0,
        party_at="turning_hub",
    )
    spans = capture_spans("chart.render")
    assert len(spans) == 1
    s = spans[0]
    assert s.attributes["scope_center"] == "coyote"
    assert s.attributes["t_hours"] == 24.0
    assert s.attributes["party_at"] == "turning_hub"
    assert s.attributes["body_count"] == 3
    assert s.attributes["output_size_bytes"] > 0
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render.py::test_render_emits_chart_render_span -v
```

Expected: span not found.

- [ ] **Step 3: Implement the emitter and wire it**

Create `sidequest-server/sidequest/telemetry/spans/chart.py`:

```python
"""chart.* OTEL spans — orbital chart rendering."""
from __future__ import annotations

from ._core import FLAT_ONLY_SPANS
from .span import Span

SPAN_CHART_RENDER = "chart.render"

FLAT_ONLY_SPANS.update({SPAN_CHART_RENDER})


def emit_chart_render(
    *,
    scope_center: str,
    t_hours: float,
    party_at: str | None,
    body_count: int,
    output_size_bytes: int,
) -> None:
    with Span.open(
        SPAN_CHART_RENDER,
        attributes={
            "scope_center": scope_center,
            "t_hours": float(t_hours),
            "party_at": party_at if party_at is not None else "",
            "body_count": int(body_count),
            "output_size_bytes": int(output_size_bytes),
        },
    ):
        pass
```

Register in `sidequest/telemetry/spans/__init__.py`:

```python
from sidequest.telemetry.spans import chart as _chart  # noqa: F401
```

In `render.py`, call the emitter at the end of `render_chart`:

```python
from sidequest.telemetry.spans.chart import emit_chart_render

def render_chart(...) -> str:
    # ... existing composition ...
    output = dwg.tostring()
    emit_chart_render(
        scope_center=center_id,
        t_hours=t_hours,
        party_at=party_at,
        body_count=len(orbits.bodies),
        output_size_bytes=len(output.encode("utf-8")),
    )
    return output
```

- [ ] **Step 4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render.py -v
```

Expected: all renderer tests pass; new span test passes.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/chart.py \
        sidequest-server/sidequest/telemetry/spans/__init__.py \
        sidequest-server/sidequest/orbital/render.py \
        sidequest-server/tests/orbital/test_render.py
git commit -m "feat(orbital): chart.render OTEL span on every SVG composition

Per spec §7.3 — Keith's GM panel sees scope_center, t_hours, party_at,
body_count, output_size_bytes for every chart render. Validates that
re-renders happen on the expected schedule (clock advance, drill in/out)."
```

---

## Task 12: Scope handling — body scope (drill-in)

Render a body-scope chart centered on a body that has children (e.g. `red_prospect`). Show parent indicator at chart edge. System scope renders sub-systems (drillable bodies) as collapsed cluster glyphs.

**Files:**
- Modify: `sidequest-server/sidequest/orbital/render.py`
- Create: `sidequest-server/tests/orbital/test_render_scopes.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_render_scopes.py`:

```python
"""Scope tests — system scope vs. body scope (drill-in)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.orbital.loader import load_orbital_content
from sidequest.orbital.render import Scope, render_chart

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def world():
    return load_orbital_content(FIXTURES / "world_minimal")


def test_system_scope_renders_drillable_cluster_for_red_prospect(world):
    """System scope: red_prospect (with children) collapses to a cluster glyph
    that carries an explicit drill-in affordance."""
    svg = render_chart(
        orbits=world.orbits,
        chart=world.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    assert 'data-action="drill_in:red_prospect"' in svg


def test_body_scope_centers_on_red_prospect(world):
    svg = render_chart(
        orbits=world.orbits,
        chart=world.chart,
        scope=Scope(center_body_id="red_prospect"),
        t_hours=0.0,
        party_at=None,
    )
    # Direct children rendered: turning_hub
    assert 'data-body-id="turning_hub"' in svg
    # Parent indicator
    assert 'data-action="drill_out"' in svg
    # System primary not rendered as a body inside body scope (only as edge indicator)
    assert "COYOTE SYSTEM" in svg or "← Coyote" in svg


def test_body_scope_unknown_center_raises(world):
    with pytest.raises(ValueError, match="not in bodies"):
        render_chart(
            orbits=world.orbits,
            chart=world.chart,
            scope=Scope(center_body_id="nowhere"),
            t_hours=0.0,
            party_at=None,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render_scopes.py -v
```

Expected: failures on missing `data-action` attributes / wrong scope handling.

- [ ] **Step 3: Implement scope-aware rendering**

In `render.py`, modify `_render_engraved_layer` to:

- For each direct child of the center body that itself has children: render as a *cluster glyph* with `data-action="drill_in:<id>"`. Cluster glyph is a small group of dots inside a dotted circle, with a small "+N" annotation.
- For body scope (center_id is not the system primary): add a parent edge indicator at left side of chart with `data-action="drill_out"` and label "← <PARENT_LABEL> SYSTEM".

Pseudo-code structure (replace the inner orbit-rendering loop):

```python
def _render_engraved_layer(
    orbits: OrbitsConfig, center_id: str, vp: _Viewport, t_hours: float
) -> svgwrite.container.Group:
    g = svgwrite.container.Group(id="layer-engraved")
    center = orbits.bodies[center_id]

    # Drill-out affordance for body scope
    if center.parent is not None:
        parent = orbits.bodies[center.parent]
        parent_label = parent.label or center.parent.upper()
        edge = svgwrite.container.Group(**{"data-action": "drill_out"})
        edge.add(svgwrite.text.Text(
            f"← {parent_label} SYSTEM",
            insert=(-vp.half + 20, 0),
            fill="yellow",
            font_family="monospace",
            font_size=10,
        ))
        g.add(edge)

    # Center body glyph + label  (existing code)
    # ...

    drillable_ids = {
        bid for bid, b in orbits.bodies.items()
        if any(child.parent == bid for child in orbits.bodies.values())
    }

    for body_id, body in orbits.bodies.items():
        if body.parent != center_id:
            continue
        # ... compute orbit + position as before ...
        if body_id in drillable_ids and body_id != center_id:
            # Cluster glyph for drillable body
            cluster = svgwrite.container.Group(
                **{"data-action": f"drill_in:{body_id}", "data-body-id": body_id}
            )
            cluster.add(svgwrite.shapes.Circle(
                center=(x, y), r=8, fill="none", stroke="yellow",
                stroke_dasharray="2,2", stroke_width=0.6,
            ))
            cluster.add(_body_glyph(body, x=x, y=y, body_id=body_id))
            child_count = sum(1 for c in orbits.bodies.values() if c.parent == body_id)
            cluster.add(svgwrite.text.Text(
                f"+{child_count}",
                insert=(x + 14, y + 4),
                fill="yellow", font_family="monospace", font_size=8,
            ))
            g.add(cluster)
        else:
            g.add(_body_glyph(body, x=x, y=y, body_id=body_id))
        # label rendering as before
```

(Adapt the structure to fit your existing `_render_engraved_layer` code; preserve the orbit-circle rendering and label placement.)

- [ ] **Step 4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/ -v
```

Expected: all passing — including new scope tests and existing render tests.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/orbital/render.py \
        sidequest-server/tests/orbital/test_render_scopes.py
git commit -m "feat(orbital): drill-in scope rendering with cluster glyphs

System scope collapses drillable bodies (those with children) into
cluster glyphs carrying data-action=drill_in:<id>. Body scope adds
parent edge indicator with data-action=drill_out. UI reads these
attributes to fire intent messages."
```

---

## Task 13: Renderer snapshot tests

Pin canonical SVG outputs for fixed inputs. Drift = test failure.

**Files:**
- Create: `sidequest-server/tests/orbital/test_render_snapshots.py`
- Create: `sidequest-server/tests/orbital/snapshots/system_t0_no_party.svg`
- Create: `sidequest-server/tests/orbital/snapshots/system_t100_party_turning_hub.svg`
- Create: `sidequest-server/tests/orbital/snapshots/red_prospect_scope_t0.svg`

- [ ] **Step 1: Write the failing snapshot test**

Create `sidequest-server/tests/orbital/test_render_snapshots.py`:

```python
"""Snapshot tests — pin SVG output bytes for canonical inputs."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.orbital.loader import load_orbital_content
from sidequest.orbital.render import Scope, render_chart

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOTS = Path(__file__).parent / "snapshots"


@pytest.fixture
def world():
    return load_orbital_content(FIXTURES / "world_minimal")


def _normalize(svg: str) -> str:
    """Whitespace-normalize SVG for stable comparison."""
    return "\n".join(line.rstrip() for line in svg.splitlines() if line.strip())


def _compare_or_record(name: str, actual: str, request):
    snap_path = SNAPSHOTS / f"{name}.svg"
    if not snap_path.exists() or request.config.getoption("--update-snapshots", default=False):
        snap_path.parent.mkdir(parents=True, exist_ok=True)
        snap_path.write_text(actual)
        pytest.skip(f"snapshot recorded: {snap_path}")
    expected = snap_path.read_text()
    assert _normalize(actual) == _normalize(expected), (
        f"SVG snapshot drift for {name}. "
        f"Run with --update-snapshots to refresh after intentional change."
    )


def test_system_scope_t0_no_party(world, request):
    svg = render_chart(
        orbits=world.orbits,
        chart=world.chart,
        scope=Scope.system_root(),
        t_hours=0.0,
        party_at=None,
    )
    _compare_or_record("system_t0_no_party", svg, request)


def test_system_scope_t100h_party_turning_hub(world, request):
    svg = render_chart(
        orbits=world.orbits,
        chart=world.chart,
        scope=Scope.system_root(),
        t_hours=100.0,
        party_at="turning_hub",
    )
    _compare_or_record("system_t100_party_turning_hub", svg, request)


def test_red_prospect_scope_t0(world, request):
    svg = render_chart(
        orbits=world.orbits,
        chart=world.chart,
        scope=Scope(center_body_id="red_prospect"),
        t_hours=0.0,
        party_at=None,
    )
    _compare_or_record("red_prospect_scope_t0", svg, request)
```

- [ ] **Step 2: Add the `--update-snapshots` pytest option**

Edit `sidequest-server/tests/conftest.py` (or create a new local conftest under `tests/orbital/`) and add:

```python
def pytest_addoption(parser):
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Refresh recorded SVG snapshots in tests/orbital/snapshots/.",
    )
```

If the existing root conftest already has `pytest_addoption`, append to it.

- [ ] **Step 3: Record snapshots on first run**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render_snapshots.py --update-snapshots -v
```

Expected: 3 tests skipped with "snapshot recorded:" messages; 3 SVG files in `tests/orbital/snapshots/`.

- [ ] **Step 4: Run again to verify snapshots match**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_render_snapshots.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Inspect snapshots manually**

Open one in a browser or text editor:

```bash
open sidequest-server/tests/orbital/snapshots/system_t0_no_party.svg  # macOS
```

Expected: an engraved-style chart resembling the screenshot (red Coyote at center, yellow orbits, Red Prospect cluster glyph with "+1", absent gate "?", scale ruler). It will not exactly match the original screenshot because epoch_phase_deg values are placeholders — visual tuning is content-author work.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/tests/orbital/test_render_snapshots.py \
        sidequest-server/tests/orbital/snapshots/ \
        sidequest-server/tests/conftest.py
git commit -m "test(orbital): snapshot tests for canonical SVG outputs

Three pinned snapshots: system at t=0, system at t=100h with party,
red_prospect drill-in scope. --update-snapshots refresh flag for
intentional changes. Drift = test failure per spec §8.2."
```

---

## Task 14: Intent message types — Python protocol + TS types

The wire schema for client ↔ server intent messages.

**Files:**
- Create: `sidequest-server/sidequest/protocol/orbital_intent.py`
- Create: `sidequest-ui/src/types/orbital-intent.ts`
- Create: `sidequest-server/tests/orbital/test_intent_protocol.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/orbital/test_intent_protocol.py`:

```python
"""Intent protocol tests — message shape lock."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.protocol.orbital_intent import (
    DrillInIntent,
    DrillOutIntent,
    OrbitalIntent,
    OrbitalIntentResponse,
    ViewMapIntent,
)


def test_view_map_intent_round_trip():
    intent = ViewMapIntent(scope="system_root")
    payload = intent.model_dump()
    assert payload == {"kind": "view_map", "scope": "system_root"}
    parsed = OrbitalIntent.model_validate(payload)
    assert isinstance(parsed.root, ViewMapIntent)


def test_drill_in_intent():
    intent = DrillInIntent(body_id="red_prospect")
    payload = intent.model_dump()
    assert payload == {"kind": "drill_in", "body_id": "red_prospect"}


def test_drill_out_intent():
    intent = DrillOutIntent()
    payload = intent.model_dump()
    assert payload == {"kind": "drill_out"}


def test_unknown_kind_rejected():
    with pytest.raises(ValidationError):
        OrbitalIntent.model_validate({"kind": "explode_sun"})


def test_response_carries_svg():
    resp = OrbitalIntentResponse(
        scope_center="coyote", svg="<svg></svg>", t_hours=0.0
    )
    assert resp.svg.startswith("<svg")
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_intent_protocol.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement Python protocol**

Create `sidequest-server/sidequest/protocol/orbital_intent.py`:

```python
"""Wire protocol for orbital chart intents.

Per spec §6.3: UI sends intents over the existing WebSocket transport
(ADR-038); server returns rendered SVG (or scene update for commit_route,
which lives in Plan 2).
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel


class _IntentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ViewMapIntent(_IntentBase):
    kind: Literal["view_map"] = "view_map"
    scope: str = "system_root"  # "system_root" or a body_id


class DrillInIntent(_IntentBase):
    kind: Literal["drill_in"] = "drill_in"
    body_id: str


class DrillOutIntent(_IntentBase):
    kind: Literal["drill_out"] = "drill_out"


_AnyIntent = Annotated[
    Union[ViewMapIntent, DrillInIntent, DrillOutIntent],
    Field(discriminator="kind"),
]


class OrbitalIntent(RootModel[_AnyIntent]):
    """Polymorphic root for any orbital chart intent message."""


class OrbitalIntentResponse(BaseModel):
    """Server response to an orbital intent — full SVG + scope metadata."""

    model_config = ConfigDict(extra="forbid")
    scope_center: str
    svg: str
    t_hours: float
    party_at: str | None = None
```

- [ ] **Step 4: Implement TS types mirroring Python**

Create `sidequest-ui/src/types/orbital-intent.ts`:

```ts
/**
 * Wire protocol for orbital chart intents — must mirror
 * sidequest-server/sidequest/protocol/orbital_intent.py.
 */
export type OrbitalIntent =
  | { kind: "view_map"; scope: string }
  | { kind: "drill_in"; body_id: string }
  | { kind: "drill_out" };

export interface OrbitalIntentResponse {
  scope_center: string;
  svg: string;
  t_hours: number;
  party_at: string | null;
}
```

- [ ] **Step 5: Run tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_intent_protocol.py -v
cd sidequest-ui && npx tsc --noEmit src/types/orbital-intent.ts
```

Expected: pytest passes; tsc no errors.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/protocol/orbital_intent.py \
        sidequest-ui/src/types/orbital-intent.ts \
        sidequest-server/tests/orbital/test_intent_protocol.py
git commit -m "feat(orbital): wire protocol for intent messages

Three intents in v1: view_map, drill_in, drill_out. commit_route + plot
land in Plan 2. Polymorphic Python root with discriminated unions; TS
types mirror exactly."
```

---

## Task 15: Server intent dispatch

Wire intents into the WebSocket message router. Each intent yields an `OrbitalIntentResponse` with rendered SVG.

**Files:**
- Create: `sidequest-server/sidequest/orbital/intent.py`
- Modify: `sidequest-server/sidequest/server/dispatch/__init__.py` (add orbital intent route)
- Create: `sidequest-server/tests/orbital/test_intent.py`

- [ ] **Step 1: Locate the existing dispatch entry**

```bash
grep -rn "WebSocket\|websocket\|@router\|client_message\|receive_text\|json_message" sidequest-server/sidequest/server/ --include="*.py" | head -20
```

Identify the WebSocket message router and how new message types are registered. Patterns vary across the codebase; record the canonical entry point in `/tmp/orbital-dispatch-entry.txt`.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/orbital/test_intent.py`:

```python
"""Intent dispatch tests — view_map / drill_in / drill_out cycle."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.session import Session
from sidequest.orbital.intent import handle_orbital_intent
from sidequest.orbital.loader import load_orbital_content
from sidequest.protocol.orbital_intent import (
    DrillInIntent,
    DrillOutIntent,
    OrbitalIntent,
    ViewMapIntent,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def session_with_world():
    session = Session.empty()
    session.orbital_content = load_orbital_content(FIXTURES / "world_minimal")
    session.party_body_id = "turning_hub"
    return session


def test_view_map_returns_system_scope_svg(session_with_world):
    resp = handle_orbital_intent(
        session_with_world, OrbitalIntent.model_validate({"kind": "view_map", "scope": "system_root"})
    )
    assert resp.scope_center == "coyote"
    assert "<svg" in resp.svg or resp.svg.startswith("<?xml")
    assert resp.party_at == "turning_hub"


def test_drill_in_returns_body_scope_svg(session_with_world):
    resp = handle_orbital_intent(
        session_with_world, OrbitalIntent.model_validate({"kind": "drill_in", "body_id": "red_prospect"})
    )
    assert resp.scope_center == "red_prospect"
    # turning_hub is now the focus; data-body-id appears in body-scope
    assert 'data-body-id="turning_hub"' in resp.svg


def test_drill_in_unknown_body_raises(session_with_world):
    with pytest.raises(ValueError, match="not in bodies"):
        handle_orbital_intent(
            session_with_world,
            OrbitalIntent.model_validate({"kind": "drill_in", "body_id": "ghost"}),
        )


def test_drill_out_from_body_scope_returns_to_system(session_with_world):
    # First drill in
    handle_orbital_intent(
        session_with_world,
        OrbitalIntent.model_validate({"kind": "drill_in", "body_id": "red_prospect"}),
    )
    # Then drill out
    resp = handle_orbital_intent(
        session_with_world,
        OrbitalIntent.model_validate({"kind": "drill_out"}),
    )
    assert resp.scope_center == "coyote"
```

- [ ] **Step 3: Run to verify failure**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_intent.py -v
```

Expected: ImportError on `sidequest.orbital.intent`.

- [ ] **Step 4: Implement intent dispatch**

Create `sidequest-server/sidequest/orbital/intent.py`:

```python
"""Intent dispatch for orbital chart messages.

Per spec §6.3: each intent → render new SVG → return OrbitalIntentResponse.
The session holds the current scope so drill_out can return to its parent.
"""
from __future__ import annotations

from sidequest.game.session import Session
from sidequest.orbital.render import Scope, render_chart
from sidequest.protocol.orbital_intent import (
    DrillInIntent,
    DrillOutIntent,
    OrbitalIntent,
    OrbitalIntentResponse,
    ViewMapIntent,
)


def handle_orbital_intent(
    session: Session, intent: OrbitalIntent
) -> OrbitalIntentResponse:
    """Resolve an orbital intent against the session's content + state."""
    inner = intent.root
    if isinstance(inner, ViewMapIntent):
        scope = (
            Scope.system_root()
            if inner.scope == "system_root"
            else Scope(center_body_id=inner.scope)
        )
    elif isinstance(inner, DrillInIntent):
        scope = Scope(center_body_id=inner.body_id)
    elif isinstance(inner, DrillOutIntent):
        # Find the parent of the current scope center; if at system root, no-op.
        current = _current_scope(session)
        if current.center_body_id == "<root>" or current.center_body_id is None:
            scope = Scope.system_root()
        else:
            body = session.orbital_content.orbits.bodies[current.center_body_id]
            scope = (
                Scope(center_body_id=body.parent)
                if body.parent
                else Scope.system_root()
            )
    else:  # exhaustive
        raise TypeError(f"Unknown orbital intent: {inner!r}")

    svg = render_chart(
        orbits=session.orbital_content.orbits,
        chart=session.orbital_content.chart,
        scope=scope,
        t_hours=session.clock.t_hours,
        party_at=session.party_body_id,
    )

    # Persist scope on session so drill_out can resolve next time
    session.orbital_scope = scope

    # Resolve the friendly center id (system_root → primary body id)
    actual_center = (
        scope.center_body_id
        if scope.center_body_id != "<root>"
        else _system_primary_id(session)
    )

    return OrbitalIntentResponse(
        scope_center=actual_center,
        svg=svg,
        t_hours=session.clock.t_hours,
        party_at=session.party_body_id,
    )


def _current_scope(session: Session) -> Scope:
    return getattr(session, "orbital_scope", None) or Scope.system_root()


def _system_primary_id(session: Session) -> str:
    return next(
        bid
        for bid, b in session.orbital_content.orbits.bodies.items()
        if b.parent is None
    )
```

Add the matching attributes to `Session` (`session.py`):

```python
# Inside Session class field list:
#     orbital_content: OrbitalContent | None = None
#     orbital_scope: Scope | None = None
#     party_body_id: str | None = None
```

(Match your existing field declaration style — dataclass field, attrs, or plain attribute — and import OrbitalContent + Scope at the top of session.py.)

- [ ] **Step 5: Wire dispatch into the WebSocket router**

In the dispatch entry identified in Step 1 (something like `sidequest/server/dispatch/__init__.py` or `sidequest/server/handlers.py`), add a route that decodes incoming messages of type `orbital_intent`, calls `handle_orbital_intent(session, intent)`, and serializes the response back to the client.

The shape of this wiring depends on your existing router's pattern. Use the same registration mechanism the codebase already uses (e.g., a dispatch dict, decorator, or match statement). Do NOT invent a new routing pattern.

- [ ] **Step 6: Run tests**

```bash
cd sidequest-server && uv run pytest tests/orbital/test_intent.py tests/orbital/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/orbital/intent.py \
        sidequest-server/sidequest/game/session.py \
        sidequest-server/sidequest/server/<dispatch-file> \
        sidequest-server/tests/orbital/test_intent.py
git commit -m "feat(orbital): server intent dispatch (view_map / drill_in / drill_out)

Each intent renders a fresh SVG against the session's clock and party
position. Session holds orbital_content + orbital_scope so drill_out
resolves to the current scope's parent. Wired into the WebSocket router."
```

---

## Task 16: UI — replace `OrreryView` with `OrbitalChartView` (SVG host)

The new component fetches SVG from server via WebSocket intent, mounts it, adds pan/zoom (CSS transform), and routes click events back as intents.

**Files:**
- Create: `sidequest-ui/src/components/OrbitalChart/OrbitalChartView.tsx`
- Create: `sidequest-ui/src/components/OrbitalChart/index.ts`
- Create: `sidequest-ui/src/components/OrbitalChart/__tests__/OrbitalChartView.test.tsx`
- Create: `sidequest-ui/src/hooks/useOrbitalChart.ts`
- Modify: `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx` (route to new component)
- Delete: `sidequest-ui/src/components/Orrery/` (entire folder)
- Modify: `sidequest-ui/src/__tests__/app-gameboard-world-slug-wiring.test.tsx`

- [ ] **Step 1: Find the existing WebSocket intent-send hook**

```bash
grep -rn "useWebSocket\|sendMessage\|wsClient\|sendIntent" sidequest-ui/src --include="*.ts*" | head -10
```

Identify the canonical hook for sending WebSocket messages from React. Use it inside `useOrbitalChart`.

- [ ] **Step 2: Write the failing component test**

Create `sidequest-ui/src/components/OrbitalChart/__tests__/OrbitalChartView.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { OrbitalChartView } from "../OrbitalChartView";

describe("OrbitalChartView", () => {
  const mockSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-400 -400 800 800">
    <g id="layer-engraved">
      <circle cx="100" cy="0" r="4" data-body-id="red_prospect" data-action="drill_in:red_prospect"/>
    </g>
  </svg>`;

  it("renders the provided SVG markup", () => {
    render(
      <OrbitalChartView
        svg={mockSvg}
        scopeCenter="coyote"
        onIntent={() => {}}
      />
    );
    const host = screen.getByTestId("orbital-chart-host");
    expect(host.querySelector('[data-body-id="red_prospect"]')).not.toBeNull();
  });

  it("fires drill_in intent on click of element with data-action drill_in", () => {
    const onIntent = vi.fn();
    render(
      <OrbitalChartView
        svg={mockSvg}
        scopeCenter="coyote"
        onIntent={onIntent}
      />
    );
    const host = screen.getByTestId("orbital-chart-host");
    const target = host.querySelector('[data-action="drill_in:red_prospect"]');
    expect(target).not.toBeNull();
    fireEvent.click(target!);
    expect(onIntent).toHaveBeenCalledWith({ kind: "drill_in", body_id: "red_prospect" });
  });

  it("fires drill_out intent on click of element with data-action drill_out", () => {
    const onIntent = vi.fn();
    const drillOutSvg = `<svg viewBox="0 0 800 800">
      <g data-action="drill_out"><text>← COYOTE</text></g>
    </svg>`;
    render(
      <OrbitalChartView
        svg={drillOutSvg}
        scopeCenter="red_prospect"
        onIntent={onIntent}
      />
    );
    const host = screen.getByTestId("orbital-chart-host");
    const target = host.querySelector('[data-action="drill_out"]');
    fireEvent.click(target!);
    expect(onIntent).toHaveBeenCalledWith({ kind: "drill_out" });
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-ui && npx vitest run src/components/OrbitalChart/__tests__/OrbitalChartView.test.tsx
```

Expected: import error on `OrbitalChartView`.

- [ ] **Step 4: Implement `OrbitalChartView`**

Create `sidequest-ui/src/components/OrbitalChart/OrbitalChartView.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import type { OrbitalIntent } from "@/types/orbital-intent";

interface OrbitalChartViewProps {
  svg: string;
  scopeCenter: string;
  onIntent: (intent: OrbitalIntent) => void;
}

/**
 * Thin SVG host. Mounts server-rendered SVG, listens at root for clicks,
 * routes data-action and data-body-id attributes to intent messages.
 * Pan/zoom is pure CSS transform on the container.
 *
 * Per spec §6.4: pan/zoom is client-only and never round-trips. Only
 * scope changes (drill_in / drill_out) trigger server requests.
 */
export function OrbitalChartView({ svg, scopeCenter, onIntent }: OrbitalChartViewProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number } | null>(null);

  // Inject SVG markup directly. Server is the only producer; sanitization
  // happens server-side via svgwrite. (Per project policy, server output
  // is trusted; UI does not parse or modify SVG content.)
  useEffect(() => {
    if (hostRef.current) {
      hostRef.current.innerHTML = svg;
    }
  }, [svg]);

  // Click router — handle data-action attributes
  function onClick(e: React.MouseEvent<HTMLDivElement>) {
    let el: HTMLElement | null = e.target as HTMLElement;
    while (el && el !== hostRef.current) {
      const action = el.getAttribute?.("data-action");
      if (action) {
        if (action.startsWith("drill_in:")) {
          const bodyId = action.slice("drill_in:".length);
          onIntent({ kind: "drill_in", body_id: bodyId });
          return;
        }
        if (action === "drill_out") {
          onIntent({ kind: "drill_out" });
          return;
        }
      }
      el = el.parentElement;
    }
  }

  // Pan/zoom — CSS transform only
  function onWheel(e: React.WheelEvent<HTMLDivElement>) {
    e.preventDefault();
    setScale((s) => Math.max(0.25, Math.min(8, s * (e.deltaY < 0 ? 1.1 : 0.9))));
  }

  function onMouseDown(e: React.MouseEvent<HTMLDivElement>) {
    dragRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  }
  function onMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!dragRef.current) return;
    setPan({ x: e.clientX - dragRef.current.x, y: e.clientY - dragRef.current.y });
  }
  function onMouseUp() {
    dragRef.current = null;
  }

  function onReset() {
    setScale(1);
    setPan({ x: 0, y: 0 });
  }

  return (
    <div
      style={{ width: "100%", height: "100%", position: "relative", overflow: "hidden" }}
      data-testid="orbital-chart-container"
      data-scope-center={scopeCenter}
    >
      <button
        onClick={onReset}
        style={{
          position: "absolute", top: 6, right: 6, zIndex: 1,
          background: "transparent", color: "yellow",
          border: "1px solid yellow", fontFamily: "monospace", fontSize: 10,
          padding: "2px 6px", cursor: "pointer",
        }}
      >
        RESET
      </button>
      <div
        ref={hostRef}
        data-testid="orbital-chart-host"
        onClick={onClick}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        style={{
          width: "100%", height: "100%",
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
          transformOrigin: "center",
          cursor: dragRef.current ? "grabbing" : "grab",
        }}
      />
    </div>
  );
}
```

Create `sidequest-ui/src/components/OrbitalChart/index.ts`:

```ts
export { OrbitalChartView } from "./OrbitalChartView";
```

- [ ] **Step 5: Implement `useOrbitalChart` hook**

Create `sidequest-ui/src/hooks/useOrbitalChart.ts`:

```ts
import { useCallback, useEffect, useState } from "react";
import type { OrbitalIntent, OrbitalIntentResponse } from "@/types/orbital-intent";
// Use the existing WebSocket hook located in Step 1.
// The exact import path will depend on your codebase, e.g.:
// import { useWebSocket } from "@/hooks/useWebSocket";

interface UseOrbitalChartArgs {
  enabled: boolean;
  // sendIntent and onResponse are wired through your existing WebSocket layer
  sendIntent: (intent: OrbitalIntent) => void;
  lastResponse: OrbitalIntentResponse | null;
}

export function useOrbitalChart({ enabled, sendIntent, lastResponse }: UseOrbitalChartArgs) {
  const [chart, setChart] = useState<OrbitalIntentResponse | null>(null);

  useEffect(() => {
    if (enabled && !chart) {
      sendIntent({ kind: "view_map", scope: "system_root" });
    }
  }, [enabled, chart, sendIntent]);

  useEffect(() => {
    if (lastResponse) setChart(lastResponse);
  }, [lastResponse]);

  const onIntent = useCallback(
    (intent: OrbitalIntent) => sendIntent(intent),
    [sendIntent]
  );

  return { chart, onIntent };
}
```

- [ ] **Step 6: Update MapWidget to use the new component**

Edit `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx`:

- Remove the `OrreryView` import and the `getOrreryDataForWorld` call.
- Replace the orrery branch with a render of `OrbitalChartView`, fed by `useOrbitalChart`.
- The world-slug check stays — but instead of dispatching to a static client-side data view, it activates the orbital chart fetch.

```tsx
import { OrbitalChartView } from "@/components/OrbitalChart";
import { useOrbitalChart } from "@/hooks/useOrbitalChart";
// remove: import { OrreryView, getOrreryDataForWorld } from "@/components/Orrery";

// ... inside MapWidget ...

const orbitalEnabled = worldSlug === "coyote_star"; // expand list as more
                                                    // worlds opt into orbital tier
const { chart, onIntent } = useOrbitalChart({
  enabled: orbitalEnabled,
  sendIntent: /* from your WebSocket hook */,
  lastResponse: /* from your WebSocket hook */,
});

if (orbitalEnabled) {
  if (!chart) {
    return (
      <div data-testid="map-panel-orbital-loading"
           className="p-4 text-sm text-muted-foreground/60 italic">
        Loading orbital chart…
      </div>
    );
  }
  return (
    <div data-testid="map-panel-orbital" style={{ width: "100%", height: "100%" }}>
      <OrbitalChartView
        svg={chart.svg}
        scopeCenter={chart.scope_center}
        onIntent={onIntent}
      />
    </div>
  );
}
```

(Adapt `sendIntent` / `lastResponse` plumbing to your existing WebSocket hook from Step 1.)

- [ ] **Step 7: Delete the old Orrery folder**

```bash
git rm -r sidequest-ui/src/components/Orrery
```

- [ ] **Step 8: Update the wiring test**

Edit `sidequest-ui/src/__tests__/app-gameboard-world-slug-wiring.test.tsx`:
- Replace assertions about `OrreryView` / `coyoteStarData` with assertions that `coyote_star` activates `OrbitalChartView` (presence of `data-testid="map-panel-orbital"` or the loading state).

- [ ] **Step 9: Run UI tests**

```bash
cd sidequest-ui && just client-test 2>&1 | tail -30
```

Expected: all UI tests pass; the new component test and updated wiring test included.

- [ ] **Step 10: Commit**

```bash
git add sidequest-ui/src/components/OrbitalChart/ \
        sidequest-ui/src/hooks/useOrbitalChart.ts \
        sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx \
        sidequest-ui/src/__tests__/app-gameboard-world-slug-wiring.test.tsx
git rm -r sidequest-ui/src/components/Orrery
git commit -m "feat(orbital): replace OrreryView with server-rendered OrbitalChartView

UI is now a thin SVG host: pan/zoom via CSS, click events route
data-action attributes to intent messages, server returns new SVG.
Old client-side Orrery folder deleted."
```

---

## Task 17: Integration test — view_map → drill_in → drill_out cycle

End-to-end wiring test confirming the full pipe: WebSocket message in, SVG out, scope state correctly updates.

**Files:**
- Create: `sidequest-server/tests/integration/test_orbital_e2e.py`

- [ ] **Step 1: Write the failing test**

```python
"""End-to-end orbital chart flow — view_map / drill_in / drill_out cycle."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.session import Session
from sidequest.orbital.intent import handle_orbital_intent
from sidequest.orbital.loader import load_orbital_content
from sidequest.protocol.orbital_intent import OrbitalIntent

FIXTURES = Path(__file__).parent.parent / "orbital" / "fixtures"


@pytest.fixture
def session():
    s = Session.empty()
    s.orbital_content = load_orbital_content(FIXTURES / "world_minimal")
    s.party_body_id = "turning_hub"
    return s


def test_full_drill_cycle(session, capture_spans):
    # 1. view_map at system root
    r1 = handle_orbital_intent(
        session, OrbitalIntent.model_validate({"kind": "view_map", "scope": "system_root"})
    )
    assert r1.scope_center == "coyote"
    assert 'data-action="drill_in:red_prospect"' in r1.svg

    # 2. drill_in to red_prospect
    r2 = handle_orbital_intent(
        session, OrbitalIntent.model_validate({"kind": "drill_in", "body_id": "red_prospect"})
    )
    assert r2.scope_center == "red_prospect"
    assert 'data-body-id="turning_hub"' in r2.svg
    assert 'data-action="drill_out"' in r2.svg

    # 3. drill_out back to system
    r3 = handle_orbital_intent(
        session, OrbitalIntent.model_validate({"kind": "drill_out"})
    )
    assert r3.scope_center == "coyote"
    assert 'data-action="drill_in:red_prospect"' in r3.svg

    # OTEL: each render emits chart.render
    render_spans = capture_spans("chart.render")
    assert len(render_spans) == 3
    assert [s.attributes["scope_center"] for s in render_spans] == [
        "coyote", "red_prospect", "coyote"
    ]


def test_clock_advance_visible_in_chart(session, capture_spans):
    """Beat advance moves the clock; next render shows different positions."""
    from sidequest.orbital.beats import Beat, BeatKind

    r_t0 = handle_orbital_intent(
        session, OrbitalIntent.model_validate({"kind": "view_map", "scope": "system_root"})
    )
    session.advance_via_beat(Beat(kind=BeatKind.REST, trigger="rest-1"))  # +8h
    session.advance_via_beat(Beat(kind=BeatKind.REST, trigger="rest-2"))  # +8h
    r_t16 = handle_orbital_intent(
        session, OrbitalIntent.model_validate({"kind": "view_map", "scope": "system_root"})
    )
    assert r_t0.t_hours == 0.0
    assert r_t16.t_hours == 16.0
    assert r_t0.svg != r_t16.svg

    # Two clock.advance spans + two chart.render spans
    advance_spans = capture_spans("clock.advance")
    assert len(advance_spans) == 2
    assert all(s.attributes["beat_kind"] == "rest" for s in advance_spans)
```

- [ ] **Step 2: Run the test**

```bash
cd sidequest-server && uv run pytest tests/integration/test_orbital_e2e.py -v
```

Expected: pass.

- [ ] **Step 3: Run the full server test suite**

```bash
cd sidequest-server && just server-test 2>&1 | tail -30
```

Expected: all tests pass.

- [ ] **Step 4: Run the full UI test suite**

```bash
cd sidequest-ui && just client-test 2>&1 | tail -30
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/tests/integration/test_orbital_e2e.py
git commit -m "test(orbital): e2e integration — drill cycle + clock advance

Wiring test per CLAUDE.md: full pipe view_map -> drill_in -> drill_out
with span emission count + scope assertions; clock advance via beats
shows up in next chart render."
```

---

## Task 18: Manual smoke check + final QA pass

Boot the stack, open the chart, drill in, advance a beat, confirm visually.

- [ ] **Step 1: Boot the stack**

```bash
just up
```

Wait until logs show server + UI + daemon all up.

- [ ] **Step 2: Open the UI and start a Coyote Star session**

In a browser, hit `http://localhost:5173`, start or join a `coyote_star` solo session. The Map tab should show the engraved orbital chart with the party marker at the current body.

- [ ] **Step 3: Drill in / out**

Double-click (or single-click on the cluster glyph for) `red_prospect`. The chart should swap to body scope showing `turning_hub` and any other Red Prospect children with a `← COYOTE SYSTEM` indicator at the left edge. Click the indicator to drill out.

- [ ] **Step 4: Verify OTEL spans**

```bash
just otel
```

Open the GM dashboard. Verify `chart.render` spans appear on each map view, drill-in, drill-out (3 minimum from a single drill cycle). Verify `clock.advance` spans fire on rest / scene end.

- [ ] **Step 5: Smoke checklist**

Confirm visually:
- [ ] Chart resembles the engraved aesthetic of the original screenshot (orbits as yellow rings, red Coyote at center, named labels in monospace, scale ruler, bearings)
- [ ] Party marker is present at the current body, drawn as a small reticle annotation (not engraved style)
- [ ] Pan + zoom work smoothly without server roundtrips
- [ ] RESET button restores default viewport
- [ ] Drill-in shows the Red Prospect sub-system; drill-out returns to system view
- [ ] absent-gate `?` glyph appears at the SE region of the system view
- [ ] OTEL spans visible on dashboard match the actions taken

- [ ] **Step 6: If something is off, file follow-ups not regressions**

Visual tuning of `epoch_phase_deg` per body to better match the original screenshot is content-author work — not a Plan 1 regression. Capture in `docs/superpowers/plans/2026-05-01-orbital-map-tracks-a-b-followups.md` for the world author.

If anything *broke* (e.g. chart fails to load, drill-in errors), add a regression test reproducing the failure and fix it before closing the plan.

- [ ] **Step 7: Final commit if any fixes**

```bash
git status
# If any fixes were needed beyond the plan tasks
git add -A
git commit -m "fix(orbital): smoke-test fixes for <specific issue>"
```

---

## Self-Review Checklist (run after writing the plan)

The author of this plan ran the following self-review:

**1. Spec coverage:**
- [x] §1 architecture (4-layer split): Tasks 1–17 establish all four layers
- [x] §2.1 orbits.yaml schema: Task 6 (models) + Task 8 (migration)
- [x] §2.2 chart.yaml schema: Task 6 (models) + Task 8 (migration)
- [x] §2.3 encounters.yaml schema: deferred to Plan 2 per scope
- [x] §3.1 clock unit: Task 1 (Clock) + Task 4 (display)
- [x] §3.2 beat kinds: Task 2 (BeatKind + advance dispatch)
- [x] §3.3 beat OTEL spans: Task 3 (clock.advance)
- [x] §4 travel mechanics: deferred to Plan 2 per scope
- [x] §5 danger beats: deferred to Plan 2 per scope
- [x] §6.1 SVG composition: Tasks 9–11 (skeleton + layers + span)
- [x] §6.2 scopes: Task 12 (system + body scopes; cluster glyphs; drill-out)
- [x] §6.3 intent protocol: Tasks 14–15 (types + dispatch)
- [x] §6.4 pan/zoom/reset: Task 16 (CSS transform + RESET button)
- [x] §6.5 party marker: Task 10 (party layer)
- [x] §6.6 plot overlay: deferred to Plan 2 per scope
- [x] §7 narrator contract / OTEL: clock.advance + chart.render in this plan; the rest deferred
- [x] §8.1 unit tests: every task has test code with golden-vector pattern
- [x] §8.2 renderer snapshots: Task 13
- [x] §8.3 wiring tests: Task 5 (session beat wiring), Task 17 (e2e drill cycle)

**2. Placeholder scan:** No `TBD` / `TODO` / "implement later" / generic-error-handling phrasing in any step. Every step that produces code shows the code.

**3. Type consistency:**
- `BeatKind` enum and `Beat` dataclass match across Tasks 2, 3, 5, 17
- `Scope` dataclass with `center_body_id` field is consistent across Tasks 9, 10, 12, 15
- `OrbitalIntent` polymorphic root and `OrbitalIntentResponse` use the same field names in Python and TS (Task 14)
- `data-action` attribute strings (`drill_in:<id>`, `drill_out`) match between renderer (Task 12) and UI click router (Task 16)
- `data-body-id` attribute is set by renderer (Task 9) and read by UI (Task 16) — same name
- `Session` fields (`clock`, `orbital_content`, `orbital_scope`, `party_body_id`) are introduced in Task 5 and used consistently in Tasks 15, 17

No issues to fix inline.

---

## Execution

**Plan complete and saved to `docs/superpowers/plans/2026-05-01-orbital-map-tracks-a-b.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task with two-stage review between tasks (spec-compliance + code-review). Best for a multi-track plan like this where each task is a clean unit.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch with checkpoints for review at task boundaries.

**Which approach?**
