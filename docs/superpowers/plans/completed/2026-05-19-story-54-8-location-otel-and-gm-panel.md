# Story 54-8: Location OTEL Spans + GM-Panel Surfacing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare OTEL attribute-setting (54-6) and bare `watcher_publish` events (54-7) with proper dedicated SPAN definitions for every location-resolver and location-overlay event. Surface them on the GM-panel dashboard so Keith/Sebastien can see the *exact* lie-detector signal (`narrator_proactive resolved=false` = yellow) and the *exact* positive-canon signal (`player_initiated minted` and `narrator_proactive promoted` = blue) when narration is running live.

**Architecture:** Two layers.

1. **Server — `sidequest/telemetry/spans/location.py`** (new): five `SPAN_*` constants and five matching `@contextmanager` helpers, modelled on `cavern_room.py`. Each helper opens a tracer span with typed attributes and registers an entry in `SPAN_ROUTES` so the watcher fan-out emits a `state_transition` event under `component="location"`. The 54-6 tool adapter (`agents/tools/resolve_location_entity.py`) and 54-7 emit helper (`_maybe_emit_location_overlay_changed`) are rewritten to wrap their bodies in the new context managers instead of calling `ctx.otel_span.set_attribute(...)` directly. The bare `_watcher_publish("location_overlay_changed.emitted", ...)` from 54-7 is removed — the dedicated span carries the same fields by definition.

2. **UI — Dashboard surfacing**: add `"location"` to `COMP_COLORS` in `src/components/Dashboard/shared/constants.ts`. Add a small `LocationLane` component on the SubsystemsTab (or wire into the existing component-summary grid) that renders the route-extracted fields and applies the lie-detector / positive-canon color rule. The base infra already routes by `component`; the new tab work is only the colour-rule readout.

The five spans:

| Span constant | Fires when | Severity rule | Key attrs |
|---|---|---|---|
| `SPAN_LOCATION_ENTITY_RESOLVE` | Every resolver call | `info` (default), `warning` if `mode=narrator_proactive AND resolved=false` | `region_id`, `label`, `mode`, `engagement_kind`, `resolved`, `mode_outcome`, `from_promotion`, `entity_id` (when resolved), `tier` (when resolved), `binding_kind` (when binding) |
| `SPAN_LOCATION_ENTITY_MINTED` | Player-initiated mint | `info` (positive canon) | `region_id`, `entity_id`, `label`, `canon`, `turn` |
| `SPAN_LOCATION_ENTITY_PROMOTED` | flavor_only → yes_and promotion | `info` (positive canon) | `region_id`, `entity_id`, `from_tier`, `to_tier`, `canon`, `turn` |
| `SPAN_LOCATION_OVERLAY_ACTIVATE` | Encounter overlay activates | `info` | `region_id`, `encounter_id`, `delta_count`, `suffix_chars` |
| `SPAN_LOCATION_OVERLAY_DEACTIVATE` | Encounter overlay deactivates | `info` | `region_id`, `encounter_id`, `delta_count`, `suffix_chars` |

The lie-detector colour rule (yellow warning on `resolve resolved=false mode=narrator_proactive`, blue positive on `minted` / `promoted`) is implemented in the SpanRoute `extract` callback by reading `mode_outcome` and emitting an explicit `is_lie_detector` field the UI looks for — that keeps colour logic in one place per ADR-031.

**Tech Stack:** Python 3.14, OpenTelemetry Python SDK, pytest. React/TypeScript for the dashboard side.

**Workflow:** tdd.

**Depends on:** 54-6 (resolver + bare attribute-setting to upgrade), 54-7 (overlay activate/deactivate emit sites to upgrade).

**Branch:** `feat/54-8-location-otel-spans` (off `develop`; touches both `sidequest-server` and `sidequest-ui` — coordinate one feat/ branch per subrepo).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/telemetry/spans/location.py` | create | Five `SPAN_*` constants + helpers; `SPAN_ROUTES` registration with extractors. |
| `sidequest-server/sidequest/telemetry/spans/__init__.py` | modify | Add `from .location import *` line in alphabetical position (between `local_dm` and `lore`). |
| `sidequest-server/sidequest/agents/tools/resolve_location_entity.py` | modify | Wrap the resolver call in `location_entity_resolve_span(...)`; emit `location_entity_minted_span` / `location_entity_promoted_span` on the corresponding mode_outcomes; drop the now-redundant `ctx.otel_span.set_attribute` calls. |
| `sidequest-server/sidequest/server/websocket_session_handler.py` | modify | Wrap `_maybe_emit_location_overlay_changed` body in `location_overlay_activate_span` / `location_overlay_deactivate_span`; remove the bare `_watcher_publish("location_overlay_changed.emitted", ...)` (the span route carries the same fields). |
| `sidequest-ui/src/components/Dashboard/shared/constants.ts` | modify | Add `"location"` to `COMP_COLORS`. |
| `sidequest-ui/src/components/Dashboard/tabs/SubsystemsTab.tsx` | modify | Map `is_lie_detector: true` → yellow severity treatment so resolver lies surface as warnings even though the span itself is info-severity. |
| `sidequest-server/tests/telemetry/spans/test_location_spans.py` | create | Helper context managers fire spans with the right attributes; routes extract correctly; lie-detector path sets `is_lie_detector=true`. |
| `sidequest-server/tests/telemetry/test_location_routing.py` | create | Routing-completeness check: every `SPAN_LOCATION_*` constant has a `SPAN_ROUTES` entry. |
| `sidequest-server/tests/agents/tools/test_resolve_location_entity_otel.py` | create | Resolver tool emits `location.entity.resolve` span (with lie-detector flag on proactive miss); `.minted` on player_initiated miss; `.promoted` on flavor_only mechanical. |
| `sidequest-server/tests/server/test_location_overlay_emit_otel.py` | create | Activate/deactivate emit fires `location.overlay.activate` / `location.overlay.deactivate` spans. |
| `sidequest-ui/src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx` | create | Wiring test — a watcher event with `component="location"` + `is_lie_detector=true` renders with the warning treatment. |

---

### Task 1: Create `spans/location.py`

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/location.py`
- Test: `sidequest-server/tests/telemetry/spans/test_location_spans.py`

- [ ] **Step 1: Inspect the closest analog**

Read `sidequest-server/sidequest/telemetry/spans/cavern_room.py` (60 lines) — the closest analog because it's a domain-level state-transition span with a SpanRoute extractor. Mirror its structure: module docstring, constant, `SPAN_ROUTES[...] = SpanRoute(...)`, `@contextmanager` helper.

Also skim `magic.py` (`grep -n "SPAN_ROUTES" sidequest-server/sidequest/telemetry/spans/magic.py`) — it has multiple spans in one module, the shape this story needs.

- [ ] **Step 2: Write failing tests**

Create `sidequest-server/tests/telemetry/spans/test_location_spans.py`:

```python
"""OTEL spans for the location subsystem (Story 54-8)."""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from sidequest.telemetry.spans import (
    FLAT_ONLY_SPANS,
    SPAN_LOCATION_ENTITY_MINTED,
    SPAN_LOCATION_ENTITY_PROMOTED,
    SPAN_LOCATION_ENTITY_RESOLVE,
    SPAN_LOCATION_OVERLAY_ACTIVATE,
    SPAN_LOCATION_OVERLAY_DEACTIVATE,
    SPAN_ROUTES,
    location_entity_minted_span,
    location_entity_promoted_span,
    location_entity_resolve_span,
    location_overlay_activate_span,
    location_overlay_deactivate_span,
)


@pytest.fixture
def exporter(monkeypatch) -> InMemorySpanExporter:
    """Install an in-memory exporter on a fresh tracer; route Span.open through it."""
    provider = TracerProvider()
    exp = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    tracer = provider.get_tracer("test")
    monkeypatch.setattr(
        "sidequest.telemetry.spans.tracer", lambda: tracer
    )
    return exp


# --- constants registered correctly --------------------------------------


def test_constants_have_canonical_names():
    assert SPAN_LOCATION_ENTITY_RESOLVE == "location.entity.resolve"
    assert SPAN_LOCATION_ENTITY_MINTED == "location.entity.minted"
    assert SPAN_LOCATION_ENTITY_PROMOTED == "location.entity.promoted"
    assert SPAN_LOCATION_OVERLAY_ACTIVATE == "location.overlay.activate"
    assert SPAN_LOCATION_OVERLAY_DEACTIVATE == "location.overlay.deactivate"


def test_every_location_span_is_routed():
    """No FLAT_ONLY_SPANS membership — all five are state-transition events."""
    for span_name in [
        SPAN_LOCATION_ENTITY_RESOLVE,
        SPAN_LOCATION_ENTITY_MINTED,
        SPAN_LOCATION_ENTITY_PROMOTED,
        SPAN_LOCATION_OVERLAY_ACTIVATE,
        SPAN_LOCATION_OVERLAY_DEACTIVATE,
    ]:
        assert span_name in SPAN_ROUTES, f"{span_name} missing from SPAN_ROUTES"
        assert span_name not in FLAT_ONLY_SPANS
        route = SPAN_ROUTES[span_name]
        assert route.component == "location"
        assert route.event_type == "state_transition"


# --- helper: resolve ------------------------------------------------------


def test_resolve_span_records_attributes(exporter):
    with location_entity_resolve_span(
        region_id="glenross_pub",
        label="the bar",
        mode="narrator_proactive",
        engagement_kind="mechanical",
        resolved=True,
        mode_outcome="matched",
        from_promotion=False,
        entity_id="bar",
        tier="real_object",
        binding_kind="location_feature",
    ):
        pass

    [span] = exporter.get_finished_spans()
    assert span.name == "location.entity.resolve"
    assert span.attributes["region_id"] == "glenross_pub"
    assert span.attributes["label"] == "the bar"
    assert span.attributes["mode"] == "narrator_proactive"
    assert span.attributes["engagement_kind"] == "mechanical"
    assert span.attributes["resolved"] is True
    assert span.attributes["mode_outcome"] == "matched"
    assert span.attributes["from_promotion"] is False
    assert span.attributes["entity_id"] == "bar"
    assert span.attributes["tier"] == "real_object"
    assert span.attributes["binding_kind"] == "location_feature"


def test_resolve_route_extracts_lie_detector_on_proactive_miss(exporter):
    with location_entity_resolve_span(
        region_id="glenross_pub",
        label="the dragon",
        mode="narrator_proactive",
        engagement_kind="mechanical",
        resolved=False,
        mode_outcome="no_match",
        from_promotion=False,
    ):
        pass
    span = exporter.get_finished_spans()[0]
    fields = SPAN_ROUTES["location.entity.resolve"].extract(span)
    assert fields["is_lie_detector"] is True
    assert fields["mode"] == "narrator_proactive"
    assert fields["resolved"] is False


def test_resolve_route_extracts_no_lie_detector_on_player_miss(exporter):
    """player_initiated resolved=false is a positive-canon mint, NOT a lie."""
    with location_entity_resolve_span(
        region_id="glenross_pub",
        label="the antique sextant",
        mode="player_initiated",
        engagement_kind="mention",
        resolved=False,
        mode_outcome="no_match",
        from_promotion=False,
    ):
        pass
    span = exporter.get_finished_spans()[0]
    fields = SPAN_ROUTES["location.entity.resolve"].extract(span)
    assert fields.get("is_lie_detector") is False


def test_resolve_route_extracts_no_lie_detector_on_proactive_match(exporter):
    with location_entity_resolve_span(
        region_id="glenross_pub",
        label="the bar",
        mode="narrator_proactive",
        engagement_kind="mention",
        resolved=True,
        mode_outcome="matched",
        from_promotion=False,
        entity_id="bar",
        tier="real_object",
    ):
        pass
    span = exporter.get_finished_spans()[0]
    fields = SPAN_ROUTES["location.entity.resolve"].extract(span)
    assert fields.get("is_lie_detector") is False


# --- helper: minted -------------------------------------------------------


def test_minted_span_records_attributes(exporter):
    with location_entity_minted_span(
        region_id="glenross_pub",
        entity_id="the_antique_sextant",
        label="the antique sextant",
        canon="A brass sextant on the bartop.",
        turn=7,
    ):
        pass
    [span] = exporter.get_finished_spans()
    assert span.name == "location.entity.minted"
    assert span.attributes["region_id"] == "glenross_pub"
    assert span.attributes["entity_id"] == "the_antique_sextant"
    assert span.attributes["label"] == "the antique sextant"
    assert span.attributes["canon"] == "A brass sextant on the bartop."
    assert span.attributes["turn"] == 7
    fields = SPAN_ROUTES["location.entity.minted"].extract(span)
    assert fields["op"] == "entity_minted"
    assert fields["is_positive_canon"] is True


# --- helper: promoted -----------------------------------------------------


def test_promoted_span_records_attributes(exporter):
    with location_entity_promoted_span(
        region_id="glenross_pub",
        entity_id="cobwebs",
        from_tier="flavor_only",
        to_tier="yes_and",
        canon="cobwebs",
        turn=11,
    ):
        pass
    [span] = exporter.get_finished_spans()
    assert span.name == "location.entity.promoted"
    assert span.attributes["region_id"] == "glenross_pub"
    assert span.attributes["entity_id"] == "cobwebs"
    assert span.attributes["from_tier"] == "flavor_only"
    assert span.attributes["to_tier"] == "yes_and"
    assert span.attributes["turn"] == 11
    fields = SPAN_ROUTES["location.entity.promoted"].extract(span)
    assert fields["op"] == "entity_promoted"
    assert fields["is_positive_canon"] is True


# --- helper: overlay ------------------------------------------------------


def test_overlay_activate_span_records_attributes(exporter):
    with location_overlay_activate_span(
        region_id="glenross_pub",
        encounter_id="tavern_brawl@glenross_pub",
        delta_count=1,
        suffix_chars=42,
    ):
        pass
    [span] = exporter.get_finished_spans()
    assert span.name == "location.overlay.activate"
    assert span.attributes["region_id"] == "glenross_pub"
    assert span.attributes["encounter_id"] == "tavern_brawl@glenross_pub"
    assert span.attributes["delta_count"] == 1
    assert span.attributes["suffix_chars"] == 42
    fields = SPAN_ROUTES["location.overlay.activate"].extract(span)
    assert fields["op"] == "overlay_activate"


def test_overlay_deactivate_span_records_attributes(exporter):
    with location_overlay_deactivate_span(
        region_id="glenross_pub",
        encounter_id="tavern_brawl@glenross_pub",
        delta_count=0,
        suffix_chars=0,
    ):
        pass
    [span] = exporter.get_finished_spans()
    assert span.name == "location.overlay.deactivate"
    fields = SPAN_ROUTES["location.overlay.deactivate"].extract(span)
    assert fields["op"] == "overlay_deactivate"
```

- [ ] **Step 3: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/telemetry/spans/test_location_spans.py -v
```
Expected: ImportError on every symbol.

- [ ] **Step 4: Create the module**

Create `sidequest-server/sidequest/telemetry/spans/location.py`:

```python
"""OTEL spans for the location subsystem. ADR-109 / Story 54-8.

Five state-transition spans:

- ``location.entity.resolve`` — every resolver call. Lie-detector flag
  set when ``mode=narrator_proactive`` AND ``resolved=False`` — the
  narrator's prose claimed something the manifest can't back.
- ``location.entity.minted`` — player-initiated mint of a new
  ``yes_and`` entity. Positive-canon flag.
- ``location.entity.promoted`` — authored ``flavor_only`` engaged
  mechanically and promoted to ``yes_and``. Positive-canon flag.
- ``location.overlay.activate`` / ``deactivate`` — encounter
  ``location_overlay`` state transitions.

All five are routed as ``state_transition`` events under
``component="location"`` so the GM panel renders them on the location
lane. The route extractor sets explicit boolean ``is_lie_detector`` and
``is_positive_canon`` fields so the UI can apply the colour rule
without re-deriving the logic from raw attributes.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from ._core import SPAN_ROUTES, SpanRoute
from .span import Span

SPAN_LOCATION_ENTITY_RESOLVE = "location.entity.resolve"
SPAN_LOCATION_ENTITY_MINTED = "location.entity.minted"
SPAN_LOCATION_ENTITY_PROMOTED = "location.entity.promoted"
SPAN_LOCATION_OVERLAY_ACTIVATE = "location.overlay.activate"
SPAN_LOCATION_OVERLAY_DEACTIVATE = "location.overlay.deactivate"


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def _extract_resolve(span: Any) -> dict[str, Any]:
    attrs = span.attributes or {}
    mode = attrs.get("mode", "")
    resolved = attrs.get("resolved", False)
    is_lie_detector = (mode == "narrator_proactive") and (resolved is False)
    return {
        "field": "location_entity",
        "op": "entity_resolve",
        "region_id": attrs.get("region_id", ""),
        "label": attrs.get("label", ""),
        "mode": mode,
        "engagement_kind": attrs.get("engagement_kind", ""),
        "resolved": resolved,
        "mode_outcome": attrs.get("mode_outcome", ""),
        "from_promotion": attrs.get("from_promotion", False),
        "entity_id": attrs.get("entity_id", ""),
        "tier": attrs.get("tier", ""),
        "binding_kind": attrs.get("binding_kind", ""),
        "is_lie_detector": is_lie_detector,
    }


def _extract_minted(span: Any) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "location_entity",
        "op": "entity_minted",
        "region_id": attrs.get("region_id", ""),
        "entity_id": attrs.get("entity_id", ""),
        "label": attrs.get("label", ""),
        "canon": attrs.get("canon", ""),
        "turn": attrs.get("turn", 0),
        "is_positive_canon": True,
    }


def _extract_promoted(span: Any) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "location_entity",
        "op": "entity_promoted",
        "region_id": attrs.get("region_id", ""),
        "entity_id": attrs.get("entity_id", ""),
        "from_tier": attrs.get("from_tier", ""),
        "to_tier": attrs.get("to_tier", ""),
        "canon": attrs.get("canon", ""),
        "turn": attrs.get("turn", 0),
        "is_positive_canon": True,
    }


def _extract_overlay_activate(span: Any) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "location_overlay",
        "op": "overlay_activate",
        "region_id": attrs.get("region_id", ""),
        "encounter_id": attrs.get("encounter_id", ""),
        "delta_count": attrs.get("delta_count", 0),
        "suffix_chars": attrs.get("suffix_chars", 0),
    }


def _extract_overlay_deactivate(span: Any) -> dict[str, Any]:
    attrs = span.attributes or {}
    return {
        "field": "location_overlay",
        "op": "overlay_deactivate",
        "region_id": attrs.get("region_id", ""),
        "encounter_id": attrs.get("encounter_id", ""),
        "delta_count": attrs.get("delta_count", 0),
        "suffix_chars": attrs.get("suffix_chars", 0),
    }


SPAN_ROUTES[SPAN_LOCATION_ENTITY_RESOLVE] = SpanRoute(
    event_type="state_transition", component="location", extract=_extract_resolve
)
SPAN_ROUTES[SPAN_LOCATION_ENTITY_MINTED] = SpanRoute(
    event_type="state_transition", component="location", extract=_extract_minted
)
SPAN_ROUTES[SPAN_LOCATION_ENTITY_PROMOTED] = SpanRoute(
    event_type="state_transition", component="location", extract=_extract_promoted
)
SPAN_ROUTES[SPAN_LOCATION_OVERLAY_ACTIVATE] = SpanRoute(
    event_type="state_transition",
    component="location",
    extract=_extract_overlay_activate,
)
SPAN_ROUTES[SPAN_LOCATION_OVERLAY_DEACTIVATE] = SpanRoute(
    event_type="state_transition",
    component="location",
    extract=_extract_overlay_deactivate,
)


# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------


@contextmanager
def location_entity_resolve_span(
    *,
    region_id: str,
    label: str,
    mode: str,
    engagement_kind: str,
    resolved: bool,
    mode_outcome: str,
    from_promotion: bool,
    entity_id: str | None = None,
    tier: str | None = None,
    binding_kind: str | None = None,
    _tracer: trace.Tracer | None = None,
) -> Iterator[trace.Span]:
    """Fires on every ``resolve_location_entity`` call.

    ``mode=narrator_proactive`` with ``resolved=False`` is the lie-detector
    signal — the route extractor sets ``is_lie_detector=True`` so the GM
    panel can flag the row yellow.
    """
    attrs: dict[str, Any] = {
        "region_id": region_id,
        "label": label,
        "mode": mode,
        "engagement_kind": engagement_kind,
        "resolved": resolved,
        "mode_outcome": mode_outcome,
        "from_promotion": from_promotion,
    }
    if entity_id is not None:
        attrs["entity_id"] = entity_id
    if tier is not None:
        attrs["tier"] = tier
    if binding_kind is not None:
        attrs["binding_kind"] = binding_kind
    with Span.open(
        SPAN_LOCATION_ENTITY_RESOLVE, attrs, tracer_override=_tracer
    ) as span:
        yield span


@contextmanager
def location_entity_minted_span(
    *,
    region_id: str,
    entity_id: str,
    label: str,
    canon: str,
    turn: int,
    _tracer: trace.Tracer | None = None,
) -> Iterator[trace.Span]:
    """Fires when ``player_initiated`` mode mints a brand-new ``yes_and`` entity."""
    attrs: dict[str, Any] = {
        "region_id": region_id,
        "entity_id": entity_id,
        "label": label,
        "canon": canon,
        "turn": turn,
    }
    with Span.open(
        SPAN_LOCATION_ENTITY_MINTED, attrs, tracer_override=_tracer
    ) as span:
        yield span


@contextmanager
def location_entity_promoted_span(
    *,
    region_id: str,
    entity_id: str,
    from_tier: str,
    to_tier: str,
    canon: str,
    turn: int,
    _tracer: trace.Tracer | None = None,
) -> Iterator[trace.Span]:
    """Fires when an authored entity is promoted (flavor_only → yes_and)."""
    attrs: dict[str, Any] = {
        "region_id": region_id,
        "entity_id": entity_id,
        "from_tier": from_tier,
        "to_tier": to_tier,
        "canon": canon,
        "turn": turn,
    }
    with Span.open(
        SPAN_LOCATION_ENTITY_PROMOTED, attrs, tracer_override=_tracer
    ) as span:
        yield span


@contextmanager
def location_overlay_activate_span(
    *,
    region_id: str,
    encounter_id: str,
    delta_count: int,
    suffix_chars: int,
    _tracer: trace.Tracer | None = None,
) -> Iterator[trace.Span]:
    """Fires when an encounter ``location_overlay`` becomes live."""
    attrs: dict[str, Any] = {
        "region_id": region_id,
        "encounter_id": encounter_id,
        "delta_count": delta_count,
        "suffix_chars": suffix_chars,
    }
    with Span.open(
        SPAN_LOCATION_OVERLAY_ACTIVATE, attrs, tracer_override=_tracer
    ) as span:
        yield span


@contextmanager
def location_overlay_deactivate_span(
    *,
    region_id: str,
    encounter_id: str,
    delta_count: int,
    suffix_chars: int,
    _tracer: trace.Tracer | None = None,
) -> Iterator[trace.Span]:
    """Fires when an encounter ``location_overlay`` resolves/clears."""
    attrs: dict[str, Any] = {
        "region_id": region_id,
        "encounter_id": encounter_id,
        "delta_count": delta_count,
        "suffix_chars": suffix_chars,
    }
    with Span.open(
        SPAN_LOCATION_OVERLAY_DEACTIVATE, attrs, tracer_override=_tracer
    ) as span:
        yield span
```

- [ ] **Step 5: Register in the spans package**

In `sidequest-server/sidequest/telemetry/spans/__init__.py`, add the import in alphabetical position (between `.local_dm` and `.lore`):

```python
from .location import *  # noqa: F401, F403
```

- [ ] **Step 6: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/telemetry/spans/test_location_spans.py -v
```
Expected: 10 passed.

- [ ] **Step 7: Confirm the routing-completeness static lint stays green**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_routing_completeness.py -v
```
Expected: green. Every new `SPAN_LOCATION_*` is in `SPAN_ROUTES`; the static lint enforces this.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/location.py \
        sidequest-server/sidequest/telemetry/spans/__init__.py \
        sidequest-server/tests/telemetry/spans/test_location_spans.py
git commit -m "feat(54-8): location.* OTEL span family

Five state_transition spans under component=location:
  location.entity.resolve, .minted, .promoted, .overlay.activate, .overlay.deactivate
Route extractors set explicit is_lie_detector / is_positive_canon
booleans so the GM panel can colour the row without re-deriving the
rule from raw attributes."
```

---

### Task 2: Routing-completeness focused test for `SPAN_LOCATION_*`

**Files:**
- Create: `sidequest-server/tests/telemetry/test_location_routing.py`

The repo-wide completeness test (`test_routing_completeness.py`) already covers the family. This adds a focused test so future engineers can run only the location spans during local dev.

- [ ] **Step 1: Write the test**

Create `sidequest-server/tests/telemetry/test_location_routing.py`:

```python
"""Focused routing check for the SPAN_LOCATION_* family (Story 54-8)."""

from __future__ import annotations

from sidequest.telemetry import spans
from sidequest.telemetry.spans import FLAT_ONLY_SPANS, SPAN_ROUTES


def test_all_span_location_constants_are_routed() -> None:
    constants = {
        v
        for name, v in vars(spans).items()
        if name.startswith("SPAN_LOCATION_") and isinstance(v, str)
    }
    assert constants, "expected SPAN_LOCATION_* constants to exist"
    missing = constants - set(SPAN_ROUTES) - set(FLAT_ONLY_SPANS)
    assert not missing, f"unrouted location spans: {sorted(missing)}"


def test_location_routes_target_state_transition() -> None:
    for name, route in SPAN_ROUTES.items():
        if not name.startswith("location."):
            continue
        assert route.event_type == "state_transition", (
            f"{name} routes to {route.event_type!r}; expected state_transition"
        )
        assert route.component == "location", (
            f"{name} routes to component={route.component!r}; expected 'location'"
        )
```

- [ ] **Step 2: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_location_routing.py -v
```
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/telemetry/test_location_routing.py
git commit -m "test(54-8): focused routing check for SPAN_LOCATION_* family"
```

---

### Task 3: Rewrite `resolve_location_entity` tool to use the span helpers

**Files:**
- Modify: `sidequest-server/sidequest/agents/tools/resolve_location_entity.py`
- Test: `sidequest-server/tests/agents/tools/test_resolve_location_entity_otel.py`

54-6 currently sets attributes on whatever span is in `ctx.otel_span`. That span is the tool-dispatch wrapper — it carries the resolve attributes but is not the dedicated `location.entity.resolve` span. This task wraps the resolver call in `location_entity_resolve_span(...)` and adds the dedicated `.minted` / `.promoted` spans on those mode outcomes.

The 54-6 attribute-setting on `ctx.otel_span` is **kept** as a side-channel — many existing tools also set attributes on the wrapper span for tool-dispatch-level introspection. The new dedicated spans coexist; the GM panel reads the dedicated spans.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/agents/tools/test_resolve_location_entity_otel.py`:

```python
"""Resolver tool emits dedicated location.* OTEL spans (Story 54-8)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from sidequest.agents.tool_registry import ToolContext
from sidequest.agents.tools.resolve_location_entity import (
    ResolveLocationEntityArgs,
    resolve_location_entity,
)
from sidequest.game.persistence import SqliteStore
from sidequest.protocol.models import LocationEntity, LocationEntityBinding


@pytest.fixture
def exporter(monkeypatch) -> InMemorySpanExporter:
    provider = TracerProvider()
    exp = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    tracer = provider.get_tracer("test")
    monkeypatch.setattr("sidequest.telemetry.spans.tracer", lambda: tracer)
    return exp


def _authored() -> list[LocationEntity]:
    return [
        LocationEntity(
            id="bar",
            label="the bar",
            tier="real_object",
            binding=LocationEntityBinding(kind="location_feature", ref="glenross_arms_bar"),
        ),
        LocationEntity(id="cobwebs", label="cobwebs", tier="flavor_only"),
    ]


def _ctx(tmp_path: Path, authored: list[LocationEntity]) -> ToolContext:
    store = SqliteStore.open(
        tmp_path / "save.db",
        genre_slug="tea_and_murder",
        world_slug="glenross",
    )
    region = MagicMock()
    region.entities = authored
    cartography = MagicMock()
    cartography.regions = {"the_glenross_arms": region}
    world = MagicMock()
    world.cartography = cartography
    pack = MagicMock()
    pack.worlds = {"glenross": world}
    return ToolContext(
        world_id="glenross",
        session_id="test-session",
        perspective_pc=None,
        turn_number=3,
        store=store,
        otel_span=MagicMock(),
        perception_filter=MagicMock(),
        genre_pack=pack,
    )


def _names(exporter):
    return [s.name for s in exporter.get_finished_spans()]


@pytest.mark.asyncio
async def test_proactive_match_emits_resolve_span(tmp_path, exporter):
    ctx = _ctx(tmp_path, _authored())
    args = ResolveLocationEntityArgs(
        label="the bar",
        region_id="the_glenross_arms",
        mode="narrator_proactive",
        engagement_kind="mention",
    )
    await resolve_location_entity(args, ctx)
    assert "location.entity.resolve" in _names(exporter)
    [span] = [s for s in exporter.get_finished_spans() if s.name == "location.entity.resolve"]
    assert span.attributes["resolved"] is True
    assert span.attributes["mode"] == "narrator_proactive"
    assert span.attributes["mode_outcome"] == "matched"
    assert span.attributes["entity_id"] == "bar"


@pytest.mark.asyncio
async def test_proactive_miss_emits_resolve_span_with_lie_detector(tmp_path, exporter):
    ctx = _ctx(tmp_path, _authored())
    args = ResolveLocationEntityArgs(
        label="the dragon",
        region_id="the_glenross_arms",
        mode="narrator_proactive",
        engagement_kind="mechanical",
    )
    await resolve_location_entity(args, ctx)
    [span] = [s for s in exporter.get_finished_spans() if s.name == "location.entity.resolve"]
    assert span.attributes["resolved"] is False
    assert span.attributes["mode"] == "narrator_proactive"
    # No .minted, no .promoted on a proactive miss.
    assert "location.entity.minted" not in _names(exporter)
    assert "location.entity.promoted" not in _names(exporter)


@pytest.mark.asyncio
async def test_player_initiated_miss_emits_resolve_and_minted(tmp_path, exporter):
    ctx = _ctx(tmp_path, _authored())
    args = ResolveLocationEntityArgs(
        label="the antique sextant",
        region_id="the_glenross_arms",
        mode="player_initiated",
        engagement_kind="mention",
    )
    await resolve_location_entity(args, ctx)
    names = _names(exporter)
    assert "location.entity.resolve" in names
    assert "location.entity.minted" in names
    [minted] = [s for s in exporter.get_finished_spans() if s.name == "location.entity.minted"]
    assert minted.attributes["region_id"] == "the_glenross_arms"
    assert minted.attributes["label"] == "the antique sextant"
    assert minted.attributes["turn"] == 3


@pytest.mark.asyncio
async def test_flavor_only_mechanical_emits_resolve_and_promoted(tmp_path, exporter):
    ctx = _ctx(tmp_path, _authored())
    args = ResolveLocationEntityArgs(
        label="cobwebs",
        region_id="the_glenross_arms",
        mode="narrator_proactive",
        engagement_kind="mechanical",
    )
    await resolve_location_entity(args, ctx)
    names = _names(exporter)
    assert "location.entity.resolve" in names
    assert "location.entity.promoted" in names
    [promoted] = [s for s in exporter.get_finished_spans() if s.name == "location.entity.promoted"]
    assert promoted.attributes["from_tier"] == "flavor_only"
    assert promoted.attributes["to_tier"] == "yes_and"
    assert promoted.attributes["entity_id"] == "cobwebs"


@pytest.mark.asyncio
async def test_matched_path_does_not_emit_minted_or_promoted(tmp_path, exporter):
    ctx = _ctx(tmp_path, _authored())
    args = ResolveLocationEntityArgs(
        label="the bar",
        region_id="the_glenross_arms",
        mode="player_initiated",
        engagement_kind="mechanical",
    )
    await resolve_location_entity(args, ctx)
    names = _names(exporter)
    assert "location.entity.resolve" in names
    assert "location.entity.minted" not in names
    assert "location.entity.promoted" not in names
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/agents/tools/test_resolve_location_entity_otel.py -v
```
Expected: FAIL — the dedicated spans aren't being emitted yet.

- [ ] **Step 3: Rewrite the tool adapter**

In `sidequest-server/sidequest/agents/tools/resolve_location_entity.py`, replace the body of `resolve_location_entity(args, ctx)` (keep the `_authored_entities_for` helper, the args model, and the `@tool` decorator unchanged). New body:

```python
@tool(
    name="resolve_location_entity",
    description=(
        "Resolve a named entity against the region's location manifest. "
        "Call this BEFORE any mechanical claim against a described "
        "entity (damage, move, take, search) and on every player input "
        "that names something in the location. narrator_proactive miss "
        "is a contract violation — the pending mechanical action does "
        "not commit. player_initiated miss canonizes the new entity "
        "(Yes-And). flavor_only entities promote to yes_and on "
        "mechanical engagement (Diamonds-and-Coal)."
    ),
    category=ToolCategory.WRITE,
)
async def resolve_location_entity(
    args: ResolveLocationEntityArgs, ctx: ToolContext
) -> ToolResult:
    from sidequest.telemetry.spans import (
        location_entity_minted_span,
        location_entity_promoted_span,
        location_entity_resolve_span,
    )

    authored = _authored_entities_for(ctx, args.region_id)
    if authored is None:
        return ToolResult.not_found(
            f"region {args.region_id!r} not found in world {ctx.world_id!r} "
            "cartography"
        )

    resolution = resolve(
        store=ctx.store,
        save_id="default",
        region_id=args.region_id,
        authored_entities=authored,
        label=args.label,
        mode=args.mode,
        engagement_kind=args.engagement_kind,
        turn_number=ctx.turn_number,
    )

    # Side-channel: keep the legacy ctx.otel_span attributes for
    # tool-dispatch introspection (matches other write tools).
    ctx.otel_span.set_attribute("location.region_id", args.region_id)
    ctx.otel_span.set_attribute("location.label", args.label)
    ctx.otel_span.set_attribute("location.mode", args.mode)
    ctx.otel_span.set_attribute("location.engagement_kind", args.engagement_kind)
    ctx.otel_span.set_attribute("location.resolved", resolution.resolved)
    ctx.otel_span.set_attribute("location.mode_outcome", resolution.mode_outcome)
    ctx.otel_span.set_attribute("location.from_promotion", resolution.from_promotion)
    if resolution.entity is not None:
        ctx.otel_span.set_attribute("location.entity_id", resolution.entity.id)
        ctx.otel_span.set_attribute("location.entity_tier", resolution.entity.tier)
        if resolution.entity.binding is not None:
            ctx.otel_span.set_attribute(
                "location.binding_kind", resolution.entity.binding.kind
            )

    # Dedicated GM-panel span (Story 54-8).
    entity_id = resolution.entity.id if resolution.entity is not None else None
    tier = resolution.entity.tier if resolution.entity is not None else None
    binding_kind = (
        resolution.entity.binding.kind
        if resolution.entity is not None and resolution.entity.binding is not None
        else None
    )
    with location_entity_resolve_span(
        region_id=args.region_id,
        label=args.label,
        mode=args.mode,
        engagement_kind=args.engagement_kind,
        resolved=resolution.resolved,
        mode_outcome=resolution.mode_outcome,
        from_promotion=resolution.from_promotion,
        entity_id=entity_id,
        tier=tier,
        binding_kind=binding_kind,
    ):
        pass

    # Mint / promotion side-effects each get their own dedicated span.
    if resolution.mode_outcome == "minted" and resolution.entity is not None:
        with location_entity_minted_span(
            region_id=args.region_id,
            entity_id=resolution.entity.id,
            label=resolution.entity.label,
            canon=resolution.entity.promoted_canon or resolution.entity.label,
            turn=ctx.turn_number,
        ):
            pass
    elif resolution.mode_outcome == "promoted" and resolution.entity is not None:
        with location_entity_promoted_span(
            region_id=args.region_id,
            entity_id=resolution.entity.id,
            from_tier="flavor_only",
            to_tier=resolution.entity.tier,
            canon=resolution.entity.promoted_canon or resolution.entity.label,
            turn=ctx.turn_number,
        ):
            pass

    if not resolution.resolved:
        return ToolResult.not_found(
            f"no entity matching {args.label!r} in region {args.region_id!r} "
            "(narrator_proactive contract violation)"
        )

    return ToolResult.ok(resolution.model_dump(mode="json"))
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/agents/tools/test_resolve_location_entity_otel.py \
                          tests/agents/tools/test_resolve_location_entity.py -v
```
Expected: all green. The 54-6 tests still pass (they only assert OK/NOT_FOUND + the side-channel `ctx.otel_span` attributes).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/agents/tools/resolve_location_entity.py \
        sidequest-server/tests/agents/tools/test_resolve_location_entity_otel.py
git commit -m "feat(54-8): dedicated OTEL spans in resolve_location_entity

Wraps the resolver call in location.entity.resolve and emits a
location.entity.minted span on player_initiated mint or
location.entity.promoted span on flavor_only mechanical promotion.
The 54-6 side-channel attribute-setting on ctx.otel_span is kept
for tool-dispatch introspection; the dedicated spans drive the
GM-panel routing."
```

---

### Task 4: Rewrite `_maybe_emit_location_overlay_changed` to fire dedicated spans

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py`
- Test: `sidequest-server/tests/server/test_location_overlay_emit_otel.py`

54-7 publishes a bare `_watcher_publish("location_overlay_changed.emitted", ...)` watcher event. The dedicated spans `location.overlay.activate` and `location.overlay.deactivate` carry the same information and route through the same fan-out — the bare publish is redundant.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_location_overlay_emit_otel.py`:

```python
"""Overlay activate/deactivate fires dedicated location.overlay spans (Story 54-8)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from sidequest.game.encounter import EncounterMetric, StructuredEncounter
from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
)
from sidequest.server.websocket_session_handler import (
    _maybe_emit_location_overlay_changed,
)


@pytest.fixture
def exporter(monkeypatch) -> InMemorySpanExporter:
    provider = TracerProvider()
    exp = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    tracer = provider.get_tracer("test")
    monkeypatch.setattr("sidequest.telemetry.spans.tracer", lambda: tracer)
    return exp


def _enc(*, resolved: bool) -> StructuredEncounter:
    return StructuredEncounter(
        encounter_type="tavern_brawl",
        player_metric=EncounterMetric(
            name="composure", current=10, starting=10, threshold=20
        ),
        opponent_metric=EncounterMetric(
            name="brawl_energy", current=10, starting=10, threshold=20
        ),
        resolved=resolved,
        location_overlay=EncounterLocationOverlay(
            bound_room_id="glenross_pub",
            entity_delta=[
                LocationEntity(
                    id="overturned_table",
                    label="an overturned table",
                    tier="yes_and",
                ),
            ],
            prose_suffix="A chair lies in splinters by the door.",
        ),
    )


def test_activate_fires_overlay_activate_span(exporter):
    emit_fn = MagicMock()
    sd = MagicMock()
    sd.genre_slug = "tea_and_murder"
    sd.world_slug = "glenross"
    sd.player_id = ""
    snapshot = MagicMock()
    snapshot.encounter = _enc(resolved=False)

    _maybe_emit_location_overlay_changed(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        transition="activate",
        emit_fn=emit_fn,
    )

    [span] = [s for s in exporter.get_finished_spans() if s.name == "location.overlay.activate"]
    assert span.attributes["region_id"] == "glenross_pub"
    assert span.attributes["encounter_id"] == "tavern_brawl@glenross_pub"
    assert span.attributes["delta_count"] == 1
    assert span.attributes["suffix_chars"] == len(
        "A chair lies in splinters by the door."
    )


def test_deactivate_fires_overlay_deactivate_span(exporter):
    emit_fn = MagicMock()
    sd = MagicMock()
    sd.player_id = ""
    snapshot = MagicMock()
    prior_overlay = EncounterLocationOverlay(
        bound_room_id="glenross_pub",
        entity_delta=[],
        prose_suffix="A chair lies in splinters by the door.",
    )

    _maybe_emit_location_overlay_changed(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        transition="deactivate",
        emit_fn=emit_fn,
        prior_overlay=prior_overlay,
    )

    [span] = [s for s in exporter.get_finished_spans() if s.name == "location.overlay.deactivate"]
    assert span.attributes["region_id"] == "glenross_pub"
    assert span.attributes["delta_count"] == 0
    assert span.attributes["suffix_chars"] == len(
        "A chair lies in splinters by the door."
    )
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_overlay_emit_otel.py -v
```
Expected: FAIL — overlay span constants exist but the emit helper doesn't open them.

- [ ] **Step 3: Update `_maybe_emit_location_overlay_changed`**

Open `sidequest-server/sidequest/server/websocket_session_handler.py` and find `_maybe_emit_location_overlay_changed` (added by 54-7). Make three changes:

1. Add the span imports inside the function body (alongside the existing message/payload imports):

```python
    from sidequest.telemetry.spans import (
        location_overlay_activate_span,
        location_overlay_deactivate_span,
    )
```

2. In the `transition == "activate"` branch, after computing `encounter_id_str` and `overlay_summaries`, capture the suffix_chars and open the span around the emit. New activate branch:

```python
    if transition == "activate":
        enc = getattr(snapshot, "encounter", None)
        if enc is None or enc.resolved:
            return
        overlay = getattr(enc, "location_overlay", None)
        if overlay is None:
            return
        region_id = overlay.bound_room_id
        encounter_id_str = f"{enc.encounter_type}@{region_id}"
        overlay_summaries = [
            LocationDescriptionOverlaySummary(
                encounter_id=encounter_id_str,
                prose_suffix=overlay.prose_suffix,
                entity_delta_count=len(overlay.entity_delta),
            )
        ]
        span_cm = location_overlay_activate_span(
            region_id=region_id,
            encounter_id=encounter_id_str,
            delta_count=len(overlay.entity_delta),
            suffix_chars=len(overlay.prose_suffix),
        )
    elif transition == "deactivate":
        if prior_overlay is None:
            return
        region_id = prior_overlay.bound_room_id
        overlay_summaries = []
        encounter_id_str = ""  # caller cleared it
        span_cm = location_overlay_deactivate_span(
            region_id=region_id,
            encounter_id="",
            delta_count=0,
            suffix_chars=len(prior_overlay.prose_suffix),
        )
    else:
        raise ValueError(
            f"transition must be 'activate' or 'deactivate', got {transition!r}"
        )
```

3. Wrap the emit + logging in the `with span_cm:` block, and **remove** the bare `_watcher_publish("location_overlay_changed.emitted", ...)` block — the dedicated span carries the same fields through the fan-out:

```python
    payload = LocationOverlayChangedPayload(
        region_id=region_id,
        overlays=overlay_summaries,
    )
    msg = LocationOverlayChangedMessage(
        payload=payload,
        player_id=getattr(sd, "player_id", ""),
    )
    with span_cm:
        logger.info(
            "location_overlay_changed.emitted region=%s transition=%s overlays=%d",
            region_id,
            transition,
            len(overlay_summaries),
        )
        emit_fn(msg, "LOCATION_OVERLAY_CHANGED")  # type: ignore[operator]
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_overlay_emit_otel.py \
                          tests/server/test_location_overlay_emit.py -v
```
Expected: all green. The 54-7 wiring tests should still pass — the emit shape didn't change, only the surrounding span context.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/server/test_location_overlay_emit_otel.py
git commit -m "feat(54-8): dedicated overlay activate/deactivate OTEL spans

_maybe_emit_location_overlay_changed now opens location.overlay.activate
or location.overlay.deactivate around the WebSocket emit; the bare
_watcher_publish('location_overlay_changed.emitted', ...) is removed
because the dedicated span carries the same fields through the
SpanRoute fan-out (component='location', state_transition event)."
```

---

### Task 5: UI — add `location` to `COMP_COLORS`

**Files:**
- Modify: `sidequest-ui/src/components/Dashboard/shared/constants.ts`

- [ ] **Step 1: Read the existing entries**

The file lists colour hex codes per component. Find a free hue not already used by `trope` (#ffb74d amber), `combat` (#e57373 red), `music_director` (#f06292 pink), `multiplayer` (#ce93d8), `orchestrator` (#03dac6), `game` (#4fc3f7), `agent` (#bb86fc), `state` (#81c784). A muted cyan/blue-green works for "location".

- [ ] **Step 2: Add the entry**

In `sidequest-ui/src/components/Dashboard/shared/constants.ts`, add inside the `COMP_COLORS` map (preserve the existing alphabetical-ish order — between `combat` and `music_director`):

```typescript
  // Story 54-8 / ADR-109: location subsystem — entity resolver + overlay
  // activate/deactivate. Distinct hue so the GM panel can lane the rows.
  location: "#26c6da",
```

- [ ] **Step 3: Type-check + lint**

```bash
just client-lint
cd sidequest-ui && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add sidequest-ui/src/components/Dashboard/shared/constants.ts
git commit -m "feat(54-8): COMP_COLORS entry for 'location' subsystem"
```

---

### Task 6: UI — surface `is_lie_detector` as a warning treatment

**Files:**
- Modify: `sidequest-ui/src/components/Dashboard/tabs/SubsystemsTab.tsx`
- Test: `sidequest-ui/src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx`

The existing SubsystemsTab activity grid colours cells by `event.severity`. The location spans are all info-severity at emit time (the server doesn't decide UI colour). The route extractor sets `is_lie_detector: true` in `event.fields` on `narrator_proactive resolved=false` — the UI promotes those events to a warning treatment on display.

- [ ] **Step 1: Read the existing severity-driven cell colouring**

Look at `SubsystemsTab.tsx` lines 30–41 (the `gridData` `useMemo`). The cell is `"error"` / `"warn"` / `"ok"` based on `event.severity`. We add a fourth branch: any event with `fields.is_lie_detector === true` upgrades the cell to `"warn"`.

- [ ] **Step 2: Write the failing test**

Create `sidequest-ui/src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx`:

```typescript
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SubsystemsTab } from "../tabs/SubsystemsTab";
import type { WatcherEvent } from "@/types/watcher";

function makeEvent(over: Partial<WatcherEvent>): WatcherEvent {
  return {
    timestamp: "2026-05-19T00:00:00Z",
    component: "location",
    event_type: "state_transition",
    severity: "info",
    fields: {},
    ...over,
  };
}

describe("SubsystemsTab — location lie-detector colour rule (Story 54-8)", () => {
  it("renders the 'location' component row when location events are present", () => {
    const events: WatcherEvent[] = [
      makeEvent({
        fields: {
          field: "location_entity",
          op: "entity_resolve",
          mode: "narrator_proactive",
          resolved: true,
          is_lie_detector: false,
        },
      }),
      // turn_complete delimiter so the row enters the activity grid.
      makeEvent({
        component: "game",
        event_type: "turn_complete",
        fields: {},
      }),
    ];
    render(
      <SubsystemsTab
        allEvents={events}
        componentMap={{ location: [events[0]] }}
        turnCount={1}
      />,
    );
    expect(screen.getByText(/location/i)).toBeTruthy();
  });

  it("upgrades a lie-detector event cell to warning severity in the grid", () => {
    const lieEvent = makeEvent({
      fields: {
        field: "location_entity",
        op: "entity_resolve",
        mode: "narrator_proactive",
        resolved: false,
        is_lie_detector: true,
      },
    });
    const events: WatcherEvent[] = [
      lieEvent,
      makeEvent({
        component: "game",
        event_type: "turn_complete",
        fields: {},
      }),
    ];
    const { container } = render(
      <SubsystemsTab
        allEvents={events}
        componentMap={{ location: [lieEvent] }}
        turnCount={1}
      />,
    );
    // The lie-detector cell renders with the amber (warn) background.
    // Search the rendered DOM for any element whose style includes the
    // amber theme value declared in constants.ts (#ff9800).
    const html = container.innerHTML.toLowerCase();
    expect(html).toContain("#ff9800");
  });
});
```

- [ ] **Step 3: Confirm fail**

```bash
cd sidequest-ui && npx vitest run src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx
```
Expected: FAIL — the lie-detector event renders with the default `info` (border) colour, not amber.

- [ ] **Step 4: Patch the grid logic**

In `sidequest-ui/src/components/Dashboard/tabs/SubsystemsTab.tsx`, find the `gridData` `useMemo` (around line 30). Update the cell classification:

```typescript
  const gridData = useMemo(() => {
    return components.map((comp) => {
      const cells = gridTurns.map((bucket) => {
        const compEvents = bucket.filter((e) => e.component === comp);
        if (compEvents.length === 0) return "empty";
        if (compEvents.some((e) => e.severity === "error")) return "error";
        // Story 54-8: a lie-detector event (e.g. narrator referenced an
        // unmanaged location entity) gets warn treatment even though the
        // span itself is info-severity. The is_lie_detector flag is set
        // by the route extractor in sidequest-server's
        // telemetry/spans/location.py.
        if (
          compEvents.some(
            (e) =>
              e.severity === "warning" ||
              (e.fields && (e.fields as Record<string, unknown>).is_lie_detector === true),
          )
        )
          return "warn";
        return "ok";
      });
      return { comp, cells };
    });
  }, [components, gridTurns]);
```

If the grid cell renderer separately applies the amber colour from `THEME.amber` (#ff9800), the change above is sufficient. If the renderer keys the colour off a different cell-class value, follow the data through to the render site and apply the same is_lie_detector check at the colour-mapping site instead.

- [ ] **Step 5: Confirm green**

```bash
cd sidequest-ui && npx vitest run src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx
```
Expected: 2 passed.

- [ ] **Step 6: Full UI suite**

```bash
just client-test
```
Expected: green.

- [ ] **Step 7: Commit**

```bash
git add sidequest-ui/src/components/Dashboard/tabs/SubsystemsTab.tsx \
        sidequest-ui/src/components/Dashboard/__tests__/SubsystemsTab-location.test.tsx
git commit -m "feat(54-8): GM-panel lie-detector treatment for location spans

is_lie_detector=true (set by the route extractor in
sidequest-server/sidequest/telemetry/spans/location.py for
narrator_proactive resolved=false) upgrades the activity-grid cell
to warn even when the underlying span is info-severity. Distinguishes
narrator-lying-about-the-world from player-canonizing-the-world
on the dashboard."
```

---

### Task 7: Full server + UI suites

- [ ] **Step 1: Server**

```bash
just server-test
```
Expected: green.

- [ ] **Step 2: UI**

```bash
just client-test
```
Expected: green.

- [ ] **Step 3: Aggregate gate**

```bash
just check-all
```
Expected: green.

---

### Self-review checklist

- [ ] **Spec §5.6 coverage:** every span in the spec's table has a constant + helper + SpanRoute. `location.entity.resolve`, `.minted`, `.promoted`, `.overlay.activate`, `.overlay.deactivate` — five total. ✓
- [ ] **GM-panel surfacing:** `narrator_proactive resolved=false` renders amber (lie-detector) per spec §5.6 bullet 1 ✓; `player_initiated resolved=false` paired with `.minted` renders as info+positive-canon ✓; `.promoted` renders as info+positive-canon ✓.
- [ ] **Placeholder scan:** no TBDs. Every helper is fully implemented.
- [ ] **Type consistency:** span attribute names match between (a) the route extractor, (b) the helper signature, (c) the resolver-tool emit, (d) the overlay-emit. `region_id`, `label`, `mode`, `engagement_kind`, `resolved`, `mode_outcome`, `from_promotion`, `entity_id`, `tier`, `binding_kind`, `encounter_id`, `delta_count`, `suffix_chars` — all consistent.
- [ ] **No silent fallback:** route extractor surfaces both true/false on the `is_lie_detector` field (not just true) so the UI never has to infer absence — explicit boolean both ways.
- [ ] **No stub:** every helper is a real `Span.open` call. The bare `_watcher_publish("location_overlay_changed.emitted", ...)` from 54-7 is removed — the dedicated span carries the same fields, so the dual emit was redundant.
- [ ] **54-6 / 54-7 contracts preserved:** the 54-6 side-channel attribute-setting on `ctx.otel_span` is kept (other tools rely on the same pattern for tool-dispatch introspection). The 54-7 message emit shape didn't change; only the surrounding span context did.
- [ ] **Routing-completeness static lint green:** `test_routing_completeness.py` (the repo-wide check) still passes because all five constants are routed.
- [ ] **Wiring tests present:** `SubsystemsTab-location.test.tsx` proves the colour rule is wired; `test_resolve_location_entity_otel.py` proves the resolver tool path emits the right spans; `test_location_overlay_emit_otel.py` proves the overlay emit fires the right spans.

### Dependencies / handoff

- **Blocked by:** 54-6 (resolver tool to upgrade), 54-7 (overlay-emit helper to upgrade).
- **Unblocks:** Nothing in Epic 54 — this is the OTEL terminus. 54-9 (UI Location panel) is independent.
- **Out of scope:** A dedicated EncounterTab-style detail panel for location events (the Subsystems grid + the existing ConsoleTab filter are sufficient for v1 — Keith can drill into rows on demand). UI rendering of the Location tab itself (54-9). Cookbook-driven span emit for procedural materialization (55-1).
