# CWN System Strain Implementation Plan (2 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `neon_dystopia`'s narrator-driven 0–100 Humanity tracker with **System Strain** — a real, CON-bound, engine-tracked resource on `CreatureCore` (modeled on the ablative `HpPool`) that gates over-max actions, carries a permanent floor for installed cyberware, recovers on rest, and emits `cwn.system_strain.delta` OTEL on every change.

**Architecture:** A new `SystemStrainPool` (current/max/permanent) lives on `CreatureCore` beside `hp`, seeded at chargen with `max = the character's CONSTITUTION-flavor (Body) score`. All strain rules — gating (an add over max is refused), the permanent floor (cyberware), rest recovery, first-aid cost — live in one engine method `CwnRulesetModule.apply_system_strain(...)`, which emits the OTEL span. The narrator reaches that method through a thin SDK tool `adjust_system_strain` (the production caller). Neon's `humanity` resource block, `humanity_tracker` prose, and the scattered Humanity references are removed; a `system_strain` custom-rule tells the narrator when to spend strain. The generic session-global `ResourcePool` system is **untouched** — other packs (spaghetti_western, tea_and_murder) still use it; we only stop neon from using it.

**Tech Stack:** Python 3.12, pydantic v2, pytest (`uv run pytest`, `-n0` for ordered/isolated, `-n auto` for the suite), ruff, OpenTelemetry. Two repos: `sidequest-server` (engine, branch base = plan-1's `feat/neon-cwn-foundation`) and `sidequest-content` (YAML).

**This is the second of four plans.** Plan 1 (foundation) shipped `CwnConfig`, `CwnRulesetModule` (subclass of swn + Luck save), the `ruleset_config()` dispatch fix, the registry entry, and neon's CWN attribute remap. Plans 3 (combat lethality: Trauma/Shock + Major Injury, combat→HP) and 4 (hacking-as-confrontation) are **out of scope here**. See `docs/superpowers/specs/2026-05-28-neon-cwn-ruleset-design.md`.

**Branch note:** Plan 1 is not yet merged (open PRs #502 server / #280 content). This plan builds directly on plan-1's code (it extends `CwnConfig` and neon's `rules.yaml`), so execute it on a branch stacked on plan-1's branches: in `sidequest-server` branch off `feat/neon-cwn-foundation`; in `sidequest-content` branch off `feat/neon-cwn-binding`. The controller will create these before Task 1.

**Scope note — what this plan deliberately does NOT do:** No Trauma/Shock, no Major Injury, no HP/AC combat conversion (plan 3). No hacking confrontation (plan 4). The momentum `combat` confrontation stays in neon for now (plan 3 retires it). The **forced-over-max → unconscious** branch is NOT wired: every strain source in this plan (cyber install/activation, first-aid, rest) is gateable, so an *unavoidable* over-max push has no trigger yet; building that path now would be unreachable code (YAGNI). It lands when plan 3 adds an unavoidable strain source.

---

## File Structure

**`sidequest-server`:**
- Create `sidequest/game/system_strain.py` — `SystemStrainPool` (data model) + `StrainResult` (method outcome).
- Modify `sidequest/game/creature_core.py` — add `system_strain: SystemStrainPool | None = None` field on `CreatureCore`.
- Modify `sidequest/genre/models/rules.py` — add `SystemStrainConfig`, add `system_strain` field to `CwnConfig`, extend `_validate_cwn` to validate `max_source`.
- Create `sidequest/telemetry/spans/cwn.py` — `cwn.system_strain.delta` span + route.
- Modify `sidequest/telemetry/spans/__init__.py` — export the new span module.
- Modify `sidequest/game/ruleset/cwn.py` — add `apply_system_strain(...)` to `CwnRulesetModule`.
- Modify `sidequest/game/builder.py` — seed `SystemStrainPool` at chargen for cwn packs.
- Create `sidequest/agents/tools/adjust_system_strain.py` — narrator SDK tool wrapping the engine method (the production caller); register it like the existing tools.
- Tests: `tests/game/test_system_strain_pool.py`, `tests/genre/models/test_cwn_system_strain_config.py`, `tests/game/test_creature_core_strain_field.py`, `tests/telemetry/test_cwn_strain_span.py`, `tests/game/ruleset/test_cwn_system_strain.py`, `tests/game/test_builder_seeds_strain.py`, `tests/agents/tools/test_adjust_system_strain_tool.py`, `tests/genre/test_neon_system_strain_wiring.py`.

**`sidequest-content`:**
- Modify `genre_packs/neon_dystopia/rules.yaml` — remove `humanity` resource + `humanity_tracker`; add `cwn.system_strain` config + `system_strain` custom-rule prose.
- Modify `genre_packs/neon_dystopia/prompts.yaml`, `progression.yaml`, `inventory.yaml`, `lethality_policy.yaml` — reword Humanity references to System Strain.

---

## Task 1: `SystemStrainPool` + `StrainResult` data models

Mirror the ablative `HpPool` (`sidequest/game/creature_core.py:19-42`): a small, dumb pydantic model that holds the numbers. All *rules* live in the module method (Task 5), exactly as `HpPool` is dumb and `beat_kinds` holds the damage rules.

**Files:**
- Create: `sidequest-server/sidequest/game/system_strain.py`
- Test: `sidequest-server/tests/game/test_system_strain_pool.py`

Working directory for all server commands: `sidequest-server`.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_system_strain_pool.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.game.system_strain import StrainResult, SystemStrainPool


def test_pool_defaults_current_and_permanent_to_zero():
    pool = SystemStrainPool(max=12)
    assert pool.current == 0
    assert pool.permanent == 0
    assert pool.max == 12


def test_pool_requires_max():
    with pytest.raises(ValidationError):
        SystemStrainPool()  # type: ignore[call-arg]


def test_pool_forbids_extra_fields():
    with pytest.raises(ValidationError):
        SystemStrainPool(max=10, bogus=1)  # type: ignore[call-arg]


def test_strain_result_carries_outcome():
    r = StrainResult(applied=False, current=12, max=12, permanent=2, delta=0, reason="would exceed max")
    assert r.applied is False
    assert r.delta == 0
    assert r.reason == "would exceed max"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_system_strain_pool.py -n0 -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.game.system_strain'`.

- [ ] **Step 3: Create the module**

Create `sidequest-server/sidequest/game/system_strain.py`:

```python
"""System Strain — CWN's CON-bound chrome-cost resource.

A real engine-tracked pool on CreatureCore (mirrors the ablative HpPool):
- ``max`` == the character's CONSTITUTION-flavor (Body) score, seeded at chargen.
- ``current`` starts at 0 and rises as cyber is installed/activated, drugs are
  taken, and first aid is applied. An add that would push ``current`` past
  ``max`` is REFUSED by the rules layer (CwnRulesetModule.apply_system_strain).
- ``permanent`` is the floor set by installed cyberware: rest recovers
  ``current`` down to ``permanent``, never below.

This model is pure data. All rules (gating, permanent floor, rest recovery,
first-aid cost) live in CwnRulesetModule.apply_system_strain.
"""

from __future__ import annotations

from pydantic import BaseModel


class SystemStrainPool(BaseModel):
    model_config = {"extra": "forbid"}

    current: int = 0
    max: int
    permanent: int = 0


class StrainResult(BaseModel):
    """Outcome of an attempted strain change, for the narrator/tool to describe."""

    model_config = {"extra": "forbid"}

    applied: bool
    current: int
    max: int
    permanent: int
    delta: int
    reason: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_system_strain_pool.py -n0 -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/system_strain.py tests/game/test_system_strain_pool.py
git commit -m "feat(cwn): SystemStrainPool + StrainResult data models"
```

---

## Task 2: `SystemStrainConfig` on `CwnConfig` + validator

`SwnConfig` lives at `sidequest/genre/models/rules.py:759-793`; `CwnConfig` (subclass, currently field-less) at `796-809`; the `_validate_cwn` validator at `902-927`. Add a nested sub-config following the file's `field: SubModel = ...` convention.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py`
- Test: `sidequest-server/tests/genre/models/test_cwn_system_strain_config.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/models/test_cwn_system_strain_config.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import CwnConfig, RulesConfig, SystemStrainConfig

_FLAVOR = ["Brawn", "Reflex", "Body", "Tech", "Instinct", "Cool"]
_AMAP = {
    "STRENGTH": "Brawn",
    "DEXTERITY": "Reflex",
    "CONSTITUTION": "Body",
    "INTELLIGENCE": "Tech",
    "WISDOM": "Instinct",
    "CHARISMA": "Cool",
}


def test_system_strain_config_defaults():
    cfg = SystemStrainConfig()
    assert cfg.max_source == "CONSTITUTION"
    assert cfg.rest_recovery_per_night == 1
    assert cfg.first_aid_cost == 1


def test_cwn_config_has_system_strain_by_default():
    cfg = CwnConfig(attribute_map=_AMAP)
    assert isinstance(cfg.system_strain, SystemStrainConfig)
    assert cfg.system_strain.max_source == "CONSTITUTION"


def test_cwn_rejects_max_source_not_in_attribute_map():
    bad = CwnConfig(attribute_map=_AMAP, system_strain=SystemStrainConfig(max_source="LUCK"))
    with pytest.raises(ValidationError, match="max_source"):
        RulesConfig(ruleset="cwn", ability_score_names=_FLAVOR, cwn=bad)


def test_cwn_accepts_valid_max_source():
    rules = RulesConfig(
        ruleset="cwn",
        ability_score_names=_FLAVOR,
        cwn=CwnConfig(attribute_map=_AMAP, system_strain=SystemStrainConfig(max_source="CONSTITUTION")),
    )
    assert rules.cwn is not None
    assert rules.cwn.system_strain.max_source == "CONSTITUTION"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/models/test_cwn_system_strain_config.py -n0 -q`
Expected: FAIL with `ImportError: cannot import name 'SystemStrainConfig'`.

- [ ] **Step 3: Add `SystemStrainConfig` immediately before `CwnConfig`**

In `sidequest/genre/models/rules.py`, immediately before the `CwnConfig` class (currently at line 796), add:

```python
class SystemStrainConfig(BaseModel):
    """CWN System Strain tuning (genre-level, content-authorable).

    max_source: the CANONICAL attribute whose flavor-stat score caps strain
      (CWN: CONSTITUTION). Validated on RulesConfig to be a key of cwn.attribute_map.
    rest_recovery_per_night: strain removed per night of rest (down to the
      permanent floor).
    first_aid_cost: temporary strain added per first-aid application.
    """

    model_config = {"extra": "forbid"}

    max_source: str = "CONSTITUTION"
    rest_recovery_per_night: int = 1
    first_aid_cost: int = 1
```

- [ ] **Step 4: Add the `system_strain` field to `CwnConfig`**

In the `CwnConfig` class body (after its `model_config` line), add:

```python
    system_strain: SystemStrainConfig = Field(default_factory=SystemStrainConfig)
```

(`Field` is already imported in this file — it's used throughout, e.g. `SwnConfig.difficulties`.)

- [ ] **Step 5: Extend `_validate_cwn` to validate `max_source`**

In `_validate_cwn` (currently ending with `return self` at line 927), immediately before that final `return self`, add:

```python
        strain_source = self.cwn.system_strain.max_source
        if strain_source not in amap:
            raise ValueError(
                f"cwn.system_strain.max_source = {strain_source!r} is not a key of "
                f"cwn.attribute_map {sorted(amap.keys())}"
            )
```

(`amap` is already bound earlier in the validator as `self.cwn.attribute_map`.)

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/genre/models/test_cwn_system_strain_config.py -n0 -q`
Expected: 4 passed.

- [ ] **Step 7: Confirm plan-1's cwn tests still pass (the validator changed)**

Run: `uv run pytest tests/game/ruleset/test_cwn_module.py tests/genre/models/test_ruleset_config_accessor.py tests/genre/test_neon_loads_cwn.py -n0 -q`
Expected: all pass (the new validator branch is a no-op for the existing tests, which all use `max_source` defaulting to `CONSTITUTION`, present in their maps).

- [ ] **Step 8: Commit**

```bash
git add sidequest/genre/models/rules.py tests/genre/models/test_cwn_system_strain_config.py
git commit -m "feat(cwn): SystemStrainConfig on CwnConfig + max_source validation"
```

---

## Task 3: `system_strain` field on `CreatureCore`

`CreatureCore` is at `sidequest/game/creature_core.py:99-162` with `model_config = {"extra": "forbid"}` and an `hp: HpPool` field. Add `system_strain` beside it. Default `None` (non-cwn cores never have strain; cwn cores get it seeded at chargen in Task 6).

**Files:**
- Modify: `sidequest-server/sidequest/game/creature_core.py`
- Test: `sidequest-server/tests/game/test_creature_core_strain_field.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_creature_core_strain_field.py`:

```python
from __future__ import annotations

from sidequest.game.creature_core import CreatureCore
from sidequest.game.system_strain import SystemStrainPool


def _core(**kw) -> CreatureCore:
    return CreatureCore(name="Jax", description="runner", personality="cool", **kw)


def test_creature_core_strain_defaults_none():
    core = _core()
    assert core.system_strain is None


def test_creature_core_accepts_strain_pool():
    core = _core(system_strain=SystemStrainPool(current=0, max=14, permanent=0))
    assert core.system_strain is not None
    assert core.system_strain.max == 14
    assert core.system_strain.current == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_creature_core_strain_field.py -n0 -q`
Expected: FAIL — `CreatureCore` rejects the `system_strain` kwarg (`extra="forbid"`).

- [ ] **Step 3: Add the field**

In `sidequest/game/creature_core.py`, add the import near the other model imports at the top of the file:

```python
from sidequest.game.system_strain import SystemStrainPool
```

and add the field to `CreatureCore`, immediately after the `hp: HpPool = ...` line:

```python
    system_strain: SystemStrainPool | None = None
```

(Check for an import cycle: `system_strain.py` imports only `pydantic`, so importing it from `creature_core.py` is safe.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_creature_core_strain_field.py -n0 -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/creature_core.py tests/game/test_creature_core_strain_field.py
git commit -m "feat(cwn): system_strain pool field on CreatureCore"
```

---

## Task 4: `cwn.system_strain.delta` OTEL span

Mirror `state_patch_hp_span` (`sidequest/telemetry/spans/state_patch.py:74`). The routing-completeness test (`tests/telemetry/test_routing_completeness.py`) requires every `SPAN_*` constant to be registered in exactly one of `SPAN_ROUTES` / `FLAT_ONLY_SPANS`.

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/cwn.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py`
- Test: `sidequest-server/tests/telemetry/test_cwn_strain_span.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_cwn_strain_span.py`:

```python
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.telemetry.spans._core import SPAN_ROUTES
from sidequest.telemetry.spans.cwn import (
    SPAN_CWN_SYSTEM_STRAIN_DELTA,
    cwn_system_strain_delta_span,
)


def test_strain_span_is_routed():
    assert SPAN_CWN_SYSTEM_STRAIN_DELTA == "cwn.system_strain.delta"
    assert SPAN_CWN_SYSTEM_STRAIN_DELTA in SPAN_ROUTES
    route = SPAN_ROUTES[SPAN_CWN_SYSTEM_STRAIN_DELTA]
    assert route.component == "cwn"


def test_strain_span_emits_attributes():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    cwn_system_strain_delta_span(
        actor="Jax",
        source="cyberarm_install",
        amount=3,
        new_total=3,
        max=14,
        applied=True,
        _tracer=tracer,
    )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes or {})
    assert spans[0].name == "cwn.system_strain.delta"
    assert attrs["actor"] == "Jax"
    assert attrs["source"] == "cyberarm_install"
    assert attrs["amount"] == 3
    assert attrs["new_total"] == 3
    assert attrs["max"] == 14
    assert attrs["applied"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_cwn_strain_span.py -n0 -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.telemetry.spans.cwn'`.

- [ ] **Step 3: Create the span module**

Create `sidequest-server/sidequest/telemetry/spans/cwn.py`:

```python
"""CWN-specific OTEL spans. The GM panel is the lie detector for engine truth."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from ._core import SPAN_ROUTES, SpanRoute
from .span import Span

SPAN_CWN_SYSTEM_STRAIN_DELTA = "cwn.system_strain.delta"
SPAN_ROUTES[SPAN_CWN_SYSTEM_STRAIN_DELTA] = SpanRoute(
    event_type="state_transition",
    component="cwn",
    extract=lambda span: {
        "field": "system_strain",
        "actor": (span.attributes or {}).get("actor", ""),
        "source": (span.attributes or {}).get("source", ""),
        "amount": (span.attributes or {}).get("amount", 0),
        "new_total": (span.attributes or {}).get("new_total", 0),
        "max": (span.attributes or {}).get("max", 0),
        "applied": (span.attributes or {}).get("applied", True),
    },
)


def cwn_system_strain_delta_span(
    *,
    actor: str,
    source: str,
    amount: int,
    new_total: int,
    max: int,
    applied: bool,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "system_strain",
        "actor": actor,
        "source": source,
        "amount": amount,
        "new_total": new_total,
        "max": max,
        "applied": applied,
        **attrs,
    }
    with Span.open(SPAN_CWN_SYSTEM_STRAIN_DELTA, attributes, tracer_override=_tracer):
        pass
```

(Confirm `SpanRoute` is exported from `sidequest/telemetry/spans/_core.py` and `Span` from `sidequest/telemetry/spans/span.py` — they are, per `state_patch.py`'s imports. If the field set on `SpanRoute` differs from `event_type`/`component`/`extract`, match the actual dataclass.)

- [ ] **Step 4: Register the module on import**

In `sidequest/telemetry/spans/__init__.py`, add alongside the other `from .<module> import *` lines (e.g. next to `from .state_patch import *`):

```python
from .cwn import *  # noqa: F401, F403
```

If `__init__.py` does NOT use star-imports but instead imports each module explicitly for its side-effect registration, match that pattern instead (read the file and mirror how `state_patch` is wired).

- [ ] **Step 5: Run tests + the routing-completeness gate**

Run: `uv run pytest tests/telemetry/test_cwn_strain_span.py tests/telemetry/test_routing_completeness.py -n0 -q`
Expected: all pass (routing-completeness confirms the new span is registered).

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans/cwn.py sidequest/telemetry/spans/__init__.py tests/telemetry/test_cwn_strain_span.py
git commit -m "feat(cwn): cwn.system_strain.delta OTEL span + route"
```

---

## Task 5: `CwnRulesetModule.apply_system_strain` — the rules engine

The load-bearing task. All strain rules live here. `CwnRulesetModule` is at `sidequest/game/ruleset/cwn.py` (plan 1). The method takes the character's `CreatureCore`, a `kind`, an `amount`, and the `CwnConfig`; mutates `core.system_strain`; emits OTEL on every call (applied or refused); returns a `StrainResult`.

**Rules:**
- `core.system_strain is None` → fail loud (`ValueError`) — a cwn character must have strain seeded (No Silent Fallbacks).
- `kind == "temporary"`: new = current + amount. If new > max → **refused** (no change, `applied=False`). Else apply.
- `kind == "first_aid"`: same as temporary but `amount` is forced to `cfg.system_strain.first_aid_cost` (ignores the passed amount).
- `kind == "permanent"`: raise the floor. `permanent' = max(0, permanent + amount)`, `current' = current + amount`. If `amount > 0` and `current' > max` → **refused**. For `amount < 0` (cyber removal) clamp `current' = max(permanent', current')` and always apply.
- `kind == "rest"`: `amount` = nights (default 1 from the tool). `current' = max(permanent, current - cfg.system_strain.rest_recovery_per_night * amount)`. Always applies (never refused); `delta` is negative or 0.
- Any other `kind` → `ValueError` (fail loud).
- Emit `cwn.system_strain.delta` on every call: `amount`=requested signed amount, `new_total`=resulting current, `max`, `applied`, `source` (passed through).

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/cwn.py`
- Test: `sidequest-server/tests/game/ruleset/test_cwn_system_strain.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_cwn_system_strain.py`:

```python
from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.game.creature_core import CreatureCore
from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.game.system_strain import SystemStrainPool
from sidequest.genre.models.rules import CwnConfig

_AMAP = {
    "STRENGTH": "Brawn", "DEXTERITY": "Reflex", "CONSTITUTION": "Body",
    "INTELLIGENCE": "Tech", "WISDOM": "Instinct", "CHARISMA": "Cool",
}
_CFG = CwnConfig(attribute_map=_AMAP)
_MOD = CwnRulesetModule()


def _core(current=0, max=12, permanent=0) -> CreatureCore:
    return CreatureCore(
        name="Jax", description="runner", personality="cool",
        system_strain=SystemStrainPool(current=current, max=max, permanent=permanent),
    )


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_temporary_within_max_applies():
    core = _core(current=2, max=12)
    r = _MOD.apply_system_strain(core=core, kind="temporary", amount=3, source="adrenal_boost", cfg=_CFG)
    assert r.applied is True
    assert r.current == 5
    assert r.delta == 3
    assert core.system_strain.current == 5


def test_temporary_over_max_is_refused():
    core = _core(current=10, max=12)
    r = _MOD.apply_system_strain(core=core, kind="temporary", amount=5, source="overclock", cfg=_CFG)
    assert r.applied is False
    assert r.delta == 0
    assert r.current == 10
    assert core.system_strain.current == 10  # unchanged
    assert "max" in r.reason


def test_permanent_raises_floor_and_current():
    core = _core(current=1, max=12, permanent=0)
    r = _MOD.apply_system_strain(core=core, kind="permanent", amount=2, source="cyberarm", cfg=_CFG)
    assert r.applied is True
    assert core.system_strain.permanent == 2
    assert core.system_strain.current == 3


def test_permanent_install_over_max_is_refused():
    core = _core(current=11, max=12, permanent=4)
    r = _MOD.apply_system_strain(core=core, kind="permanent", amount=3, source="reflex_wires", cfg=_CFG)
    assert r.applied is False
    assert core.system_strain.permanent == 4  # unchanged
    assert core.system_strain.current == 11


def test_permanent_removal_lowers_floor_and_clamps_current():
    core = _core(current=5, max=12, permanent=5)
    r = _MOD.apply_system_strain(core=core, kind="permanent", amount=-2, source="explant", cfg=_CFG)
    assert r.applied is True
    assert core.system_strain.permanent == 3
    assert core.system_strain.current == 3  # clamped down to new floor


def test_rest_recovers_down_to_permanent_floor():
    core = _core(current=6, max=12, permanent=2)
    r = _MOD.apply_system_strain(core=core, kind="rest", amount=1, source="night_rest", cfg=_CFG)
    assert r.applied is True
    assert core.system_strain.current == 5  # 6 - 1
    r2 = _MOD.apply_system_strain(core=core, kind="rest", amount=10, source="long_rest", cfg=_CFG)
    assert core.system_strain.current == 2  # floored at permanent, never below


def test_first_aid_uses_config_cost():
    core = _core(current=0, max=12)
    r = _MOD.apply_system_strain(core=core, kind="first_aid", amount=99, source="medkit", cfg=_CFG)
    assert r.applied is True
    assert r.delta == 1  # cfg.system_strain.first_aid_cost, not the passed 99
    assert core.system_strain.current == 1


def test_missing_strain_pool_fails_loud():
    core = CreatureCore(name="Jax", description="x", personality="y")  # system_strain None
    with pytest.raises(ValueError, match="system_strain"):
        _MOD.apply_system_strain(core=core, kind="temporary", amount=1, source="x", cfg=_CFG)


def test_unknown_kind_fails_loud():
    core = _core()
    with pytest.raises(ValueError, match="kind"):
        _MOD.apply_system_strain(core=core, kind="bogus", amount=1, source="x", cfg=_CFG)


def test_emits_otel_on_apply_and_on_refusal():
    exporter, tracer = _exporter()
    core = _core(current=10, max=12)
    _MOD.apply_system_strain(core=core, kind="temporary", amount=1, source="ok", cfg=_CFG, _tracer=tracer)
    _MOD.apply_system_strain(core=core, kind="temporary", amount=9, source="too_much", cfg=_CFG, _tracer=tracer)
    spans = exporter.get_finished_spans()
    assert [s.name for s in spans] == ["cwn.system_strain.delta", "cwn.system_strain.delta"]
    applied_flags = [dict(s.attributes or {})["applied"] for s in spans]
    assert applied_flags == [True, False]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_cwn_system_strain.py -n0 -q`
Expected: FAIL — `CwnRulesetModule` has no attribute `apply_system_strain`.

- [ ] **Step 3: Implement the method**

In `sidequest/game/ruleset/cwn.py`, add these imports at the top (after the existing imports):

```python
from typing import cast

from opentelemetry import trace

from sidequest.game.creature_core import CreatureCore
from sidequest.game.system_strain import StrainResult
from sidequest.genre.models.rules import CwnConfig, SwnConfig
from sidequest.telemetry.spans.cwn import cwn_system_strain_delta_span
```

Add the method to the `CwnRulesetModule` class body:

```python
    def apply_system_strain(
        self,
        *,
        core: CreatureCore,
        kind: str,
        amount: int,
        source: str,
        cfg: SwnConfig | None,
        _tracer: "trace.Tracer | None" = None,
    ) -> StrainResult:
        """Apply a System Strain change under CWN rules; emit cwn.system_strain.delta.

        kind: "temporary" | "first_aid" | "permanent" | "rest".
        Over-max temporary/permanent-install adds are REFUSED (applied=False, no change).
        Rest recovers toward (never below) the permanent floor. Fails loud if the
        character has no strain pool or kind is unknown.
        """
        pool = core.system_strain
        if pool is None:
            raise ValueError(
                f"{core.name!r} has no system_strain pool; cwn characters must seed one at chargen"
            )
        scfg = cast(CwnConfig, cfg).system_strain

        before = pool.current
        applied = True
        reason = ""

        if kind == "first_aid":
            requested = scfg.first_aid_cost
            new_current = pool.current + requested
            if new_current > pool.max:
                applied, reason, new_current = False, f"would exceed max ({pool.max})", pool.current
        elif kind == "temporary":
            requested = amount
            new_current = pool.current + amount
            if new_current > pool.max:
                applied, reason, new_current = False, f"would exceed max ({pool.max})", pool.current
        elif kind == "permanent":
            requested = amount
            new_perm = max(0, pool.permanent + amount)
            new_current = pool.current + amount
            if amount > 0 and new_current > pool.max:
                applied, reason, new_current, new_perm = (
                    False, f"would exceed max ({pool.max})", pool.current, pool.permanent,
                )
            else:
                new_current = max(new_perm, new_current)
            if applied:
                pool.permanent = new_perm
        elif kind == "rest":
            requested = -scfg.rest_recovery_per_night * max(0, amount)
            new_current = max(pool.permanent, pool.current + requested)
        else:
            raise ValueError(f"unknown system_strain kind {kind!r}")

        if applied:
            pool.current = new_current
        delta = pool.current - before

        cwn_system_strain_delta_span(
            actor=core.name,
            source=source,
            amount=requested,
            new_total=pool.current,
            max=pool.max,
            applied=applied,
            _tracer=_tracer,
        )
        return StrainResult(
            applied=applied,
            current=pool.current,
            max=pool.max,
            permanent=pool.permanent,
            delta=delta,
            reason=reason,
        )
```

(Watch for an import cycle: `cwn.py` already imports from `sidequest.game.ruleset.swn` and `resolution`. Importing `CreatureCore`/`system_strain`/`rules`/the span here is fine — none of those import the ruleset package. If a cycle appears at import time, move the `CreatureCore`/`rules` imports under `TYPE_CHECKING` and keep them as string annotations; the span import and `StrainResult` are runtime-needed.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_cwn_system_strain.py -n0 -q`
Expected: all passed (10 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/cwn.py tests/game/ruleset/test_cwn_system_strain.py
git commit -m "feat(cwn): apply_system_strain engine method (gating, permanent floor, rest, OTEL)"
```

---

## Task 6: Seed `SystemStrainPool` at chargen for cwn packs

HP is seeded in `builder.py` around lines 2166-2202; the character is assembled at 2221-2253; `self._edge_config` is set from `rules.edge_config` at builder construction (~line 787). Seed strain right after HP, gated on `ruleset == "cwn"`, with `max = the CONSTITUTION-flavor (Body) score`.

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py`
- Test: `sidequest-server/tests/game/test_builder_seeds_strain.py`

- [ ] **Step 1: Read the builder regions first**

Read `sidequest/game/builder.py` lines ~780-800 (how `rules` / `edge_config` are stored on the builder — find the attribute holding the `RulesConfig`, e.g. `self._rules`), lines ~2166-2202 (HP seeding; note the `stats` dict and `class_str` in scope), and lines ~2221-2253 (the `Character(core=CreatureCore(...))` assembly). You will mirror the `edge_config` access pattern to reach `rules.ruleset` and `rules.cwn`.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/game/test_builder_seeds_strain.py`. This drives a real chargen through the public builder API for the neon pack. Mirror the construction used by an existing builder test — find one with: `grep -rln "CharacterBuilder\|build_character\|Builder(" tests/game | head`, read it, and copy its setup (pack load + builder instantiation + the calls that finalize a character). Then assert:

```python
# Pseudocode shape — adapt the builder setup to the existing test's idiom.
def test_cwn_character_gets_strain_pool_maxed_at_body_score():
    character = _build_finished_neon_character()  # via the existing builder idiom
    core = character.core
    assert core.system_strain is not None
    body_score = character.stats["Body"]
    assert core.system_strain.max == max(1, body_score)
    assert core.system_strain.current == 0
    assert core.system_strain.permanent == 0


def test_non_cwn_character_has_no_strain_pool():
    character = _build_finished_swn_or_native_character()  # e.g. space_opera (swn) or a native pack
    assert character.core.system_strain is None
```

If a full builder drive is impractical in a unit test, instead unit-test a small extracted helper `seed_system_strain(rules, stats)` (see Step 3) directly with a synthetic `RulesConfig` + `stats` dict, AND keep `test_non_cwn_character_has_no_strain_pool` as the integration check. Prefer the real builder drive if the existing tests show an easy idiom.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/game/test_builder_seeds_strain.py -n0 -q`
Expected: FAIL (`core.system_strain` is None for the cwn character).

- [ ] **Step 4: Implement the seeding**

Add a module-level helper near the top of `builder.py` (after imports) so it is unit-testable:

```python
def seed_system_strain(rules, stats: dict[str, int]):
    """Return a SystemStrainPool for a cwn pack (max = CONSTITUTION-flavor score), else None."""
    from sidequest.game.system_strain import SystemStrainPool

    if rules.ruleset != "cwn" or rules.cwn is None:
        return None
    con_flavor = rules.cwn.attribute_map["CONSTITUTION"]  # validated present by _validate_cwn
    body_score = int(stats.get(con_flavor, 10))
    return SystemStrainPool(current=0, max=max(1, body_score), permanent=0)
```

Then, in the chargen path immediately after the HP-seeding block (~line 2192, where `hp` and `stats` are in scope), compute:

```python
        system_strain = seed_system_strain(self._rules, stats)
```

(Replace `self._rules` with the actual attribute holding the `RulesConfig`, discovered in Step 1. If the builder stores only `edge_config`, also store the full rules config there — read how `edge_config` is captured at ~787 and add a sibling `self._rules = rules` if needed.)

In the `CreatureCore(...)` constructor call (~2221-2253), add the field beside `hp=hp`:

```python
            system_strain=system_strain,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/game/test_builder_seeds_strain.py -n0 -q`
Expected: passed.

- [ ] **Step 6: Run the broader builder/chargen suite for regressions**

Run: `uv run pytest tests/game -n auto -q -k "builder or chargen or character"`
Expected: all pass (non-cwn characters still get `system_strain is None`; cwn gets a seeded pool).

- [ ] **Step 7: Commit**

```bash
git add sidequest/game/builder.py tests/game/test_builder_seeds_strain.py
git commit -m "feat(cwn): seed SystemStrainPool at chargen (max = Body/CON score)"
```

---

## Task 7: `adjust_system_strain` narrator tool — the production caller

The narrator changes engine state through SDK tools (see the established pattern in `sidequest/agents/tools/update_resource_pool.py` and `sidequest/agents/tools/apply_damage.py`). Add a thin tool that resolves the actor's `CreatureCore` from the snapshot and calls `CwnRulesetModule.apply_system_strain`. This is the real production path the wiring test (Task 9) drives.

**Files:**
- Create: `sidequest-server/sidequest/agents/tools/adjust_system_strain.py`
- Modify: the tool registry (discover it — see Step 1)
- Test: `sidequest-server/tests/agents/tools/test_adjust_system_strain_tool.py`

- [ ] **Step 1: Read the tool pattern + registry**

Read `sidequest/agents/tools/update_resource_pool.py` and `sidequest/agents/tools/apply_damage.py` in full. Determine: (a) the tool function signature/decorator and how it receives the game context (the `ctx`/snapshot object), (b) how it looks up an actor's `CreatureCore` (cross-reference `GameSnapshot.find_creature_core(name)` at `session.py:1447`), (c) where tools are REGISTERED (grep: `grep -rn "update_resource_pool\|apply_damage" sidequest/agents | grep -iv test`) so the new tool is exposed to the narrator the same way. Mirror exactly.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/agents/tools/test_adjust_system_strain_tool.py`. Build a minimal `GameSnapshot` with one cwn character that has a seeded `SystemStrainPool`, then invoke the tool function directly (tools are plain callables) and assert: a temporary add within max applies and returns the new total; an add over max is refused; and a `cwn.system_strain.delta` span fires (use the `InMemorySpanExporter` setup from Task 5's test). Match the snapshot/ctx construction to whatever `update_resource_pool`'s own test uses — read `tests/` for that tool's existing test and mirror its fixture.

The assertions (adapt the call shape to the real tool signature):

```python
def test_tool_applies_strain_and_returns_total(...):
    result = adjust_system_strain(ctx, actor="Jax", kind="temporary", amount=3, source="boost")
    assert "3" in result  # or structured: result.new_total == 3 — match the tool's return contract
    assert ctx.snapshot.find_creature_core("Jax").system_strain.current == 3


def test_tool_refuses_over_max(...):
    # actor seeded near max
    result = adjust_system_strain(ctx, actor="Jax", kind="temporary", amount=99, source="overclock")
    # the tool reports refusal; pool unchanged
    assert ctx.snapshot.find_creature_core("Jax").system_strain.current == <unchanged>
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/agents/tools/test_adjust_system_strain_tool.py -n0 -q`
Expected: FAIL (module/tool does not exist).

- [ ] **Step 4: Implement the tool**

Create `sidequest-server/sidequest/agents/tools/adjust_system_strain.py`, mirroring `update_resource_pool.py`'s structure. Core logic:

```python
# Imports + decorator/signature mirror update_resource_pool.py.
from sidequest.game.ruleset import get_ruleset_module
from sidequest.game.ruleset.cwn import CwnRulesetModule

def adjust_system_strain(ctx, *, actor: str, kind: str, amount: int, source: str) -> <return type used by sibling tools>:
    """Narrator tool: adjust a character's CWN System Strain.

    kind: "temporary" (cyber activation/drugs), "permanent" (cyber install/removal),
    "first_aid", or "rest". Over-max adds are refused by the engine.
    """
    snapshot = ctx.snapshot  # match the real ctx accessor
    pack = ctx.pack          # match the real ctx accessor for the loaded pack/rules
    if pack.rules.ruleset != "cwn":
        raise ValueError("adjust_system_strain is only valid for cwn packs")
    core = snapshot.find_creature_core(actor)
    if core is None:
        raise ValueError(f"no creature named {actor!r}")
    module = get_ruleset_module(pack.rules.ruleset)
    assert isinstance(module, CwnRulesetModule)
    cfg = pack.rules.ruleset_config()
    result = module.apply_system_strain(core=core, kind=kind, amount=amount, source=source, cfg=cfg)
    # Return a narrator-facing summary in the same shape sibling tools return
    # (e.g. a short string or a structured payload). Match update_resource_pool's contract.
    return <summary built from result.applied / result.current / result.max / result.reason>
```

Register the tool exactly as `update_resource_pool` is registered (Step 1 finding).

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/agents/tools/test_adjust_system_strain_tool.py -n0 -q`
Expected: passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/tools/adjust_system_strain.py tests/agents/tools/test_adjust_system_strain_tool.py <registry file>
git commit -m "feat(cwn): adjust_system_strain narrator tool (production caller for strain engine)"
```

---

## Task 8: Neon content — remove Humanity, add System Strain config + prose

Working directory: `sidequest-content`. All paths under `genre_packs/neon_dystopia/`. Line numbers are from the current file head — VERIFY by reading each file before editing.

- [ ] **Step 1: Edit `rules.yaml`**

1. **Remove** the `custom_rules.humanity_tracker` entry (the prose block at ~lines 59-67). Leave other `custom_rules` keys intact.
2. **Remove** the entire `humanity` entry from the `resources:` list (~lines 82-99). If `humanity` was the only resource, remove the now-empty `resources:` key entirely (the generic resource system tolerates zero resources).
3. **Add** a `system_strain` config under the existing `cwn:` block (added in plan 1), beside `attribute_map`:

```yaml
cwn:
  attribute_map:
    STRENGTH: Brawn
    DEXTERITY: Reflex
    CONSTITUTION: Body
    INTELLIGENCE: Tech
    WISDOM: Instinct
    CHARISMA: Cool
  system_strain:
    max_source: CONSTITUTION
    rest_recovery_per_night: 1
    first_aid_cost: 1
```

4. **Add** a `system_strain` custom-rule prose entry under `custom_rules:` telling the narrator when to spend strain via the tool:

```yaml
custom_rules:
  system_strain: >-
    Cyberware has a bodily cost: System Strain (capped by the Body attribute,
    starts at 0). Installing chrome adds PERMANENT strain; activating cyber,
    using combat drugs, or applying first aid adds TEMPORARY strain. Call the
    adjust_system_strain tool — kind "permanent" on install, "temporary" on
    activation/drugs, "first_aid" when patching wounds, "rest" for a night's
    recovery. An action that would push strain over max simply fails (no
    benefit, no install). A night's rest removes 1 strain down to the permanent
    floor. Never narrate strain you did not record with the tool.
```

- [ ] **Step 2: Reword the scattered Humanity references**

- `prompts.yaml` (~line 101): change the `world_state` directive `"Track Humanity for augmented characters."` → `"Track System Strain for augmented characters."`
- `progression.yaml` (~line 9): change the affinity trigger text `"maintaining humanity while heavily augmented"` → `"managing System Strain while heavily augmented"`.
- `inventory.yaml` (~line 78): change the item lore `"Costs humanity. Worth it when the bullet stops."` → `"Costs System Strain. Worth it when the bullet stops."`
- `lethality_policy.yaml` (~line 7): change `must_narrate` text so chrome rescue `"costs Humanity"` → `"increases System Strain"`.
- `tropes.yaml` (~line 144): **leave unchanged** — `"The relationship between humanity and machine intelligence."` is thematic prose about humanity-the-concept, not the retired tracker.

Verify no tracker references remain:

Run (from `sidequest-content`): `grep -rniE "\bhumanity\b" genre_packs/neon_dystopia/rules.yaml genre_packs/neon_dystopia/prompts.yaml genre_packs/neon_dystopia/progression.yaml genre_packs/neon_dystopia/inventory.yaml genre_packs/neon_dystopia/lethality_policy.yaml`
Expected: no output (the only remaining `humanity` mentions are the deliberately-kept tropes.yaml thematic line and any flavor prose in lore.yaml/pack.yaml, which are out of scope for this grep).

- [ ] **Step 3: Sanity-check YAML**

Run: `python -c "import yaml; yaml.safe_load(open('genre_packs/neon_dystopia/rules.yaml')); print('OK')"`
Expected: OK.

- [ ] **Step 4: Commit (content repo)**

```bash
git add genre_packs/neon_dystopia/rules.yaml genre_packs/neon_dystopia/prompts.yaml genre_packs/neon_dystopia/progression.yaml genre_packs/neon_dystopia/inventory.yaml genre_packs/neon_dystopia/lethality_policy.yaml
git commit -m "feat(neon): replace Humanity tracker with CWN System Strain (config + prose)"
```

---

## Task 9: Wiring test — neon loads, seeds, and drives System Strain through a production path

Per the spec's testing doctrine (behavior/OTEL, never source-grep): load the real `neon_dystopia` pack, build a character, drive a strain change through the **narrator tool** (the production caller), and assert the engine truth + OTEL. Mirror `tests/genre/test_neon_loads_cwn.py`'s content-on-disk guard idiom.

**Files:**
- Create: `sidequest-server/tests/genre/test_neon_system_strain_wiring.py`

Working directory: `sidequest-server`.

- [ ] **Step 1: Write the test**

Mirror the guard idiom from `tests/genre/test_neon_loads_cwn.py` (it imports `load_pack` from `tests.genre.test_resolution_mode` and skips when content is absent). The test must:

1. Load `neon_dystopia`; assert `pack.rules.cwn.system_strain.max_source == "CONSTITUTION"` and `rest_recovery_per_night`/`first_aid_cost` are present (config wiring).
2. Build a neon character through the same builder idiom Task 6 used; assert `core.system_strain is not None` and `core.system_strain.max == max(1, character.stats["Body"])` (chargen wiring).
3. Construct the tool's `ctx` (mirror Task 7's test fixture), set up an `InMemorySpanExporter`, and call `adjust_system_strain(ctx, actor=<name>, kind="permanent", amount=2, source="cyberarm")`. Assert: the pool's `current`/`permanent` updated, and a `cwn.system_strain.delta` span fired with `applied=True` (proves pack→tool→module→OTEL end to end).
4. Call it again with a temporary add that exceeds max; assert refusal (pool unchanged) and a span with `applied=False`.

```python
@pytest.mark.skipif(not _HAS_CONTENT, reason="sidequest-content not on disk")
def test_neon_system_strain_end_to_end():
    pack = load_pack("neon_dystopia")
    assert pack.rules.cwn.system_strain.max_source == "CONSTITUTION"
    # ... build character, drive tool, assert engine state + cwn.system_strain.delta spans ...
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/genre/test_neon_system_strain_wiring.py -n0 -q`
Expected: 1 passed (NOT skipped — content is on disk). If it skips, `load_pack("neon_dystopia")` raised during the guard — surface the exception (it means a real pack-load/validation failure from Task 8) rather than accepting the skip.

- [ ] **Step 3: Commit**

```bash
git add tests/genre/test_neon_system_strain_wiring.py
git commit -m "test(cwn): wiring test — neon seeds + drives System Strain through the narrator tool (OTEL)"
```

---

## Task 10: Full gate — lint, types, full suite

**Files:** none (verification only). Working directory: `sidequest-server` (and a YAML lint of the content pack).

- [ ] **Step 1: Lint and format**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors in this plan's files. If `ruff format --check` flags THIS plan's files, run `uv run ruff format <those files>`, re-stage, and commit as a `style:` commit. Do NOT fix pre-existing issues in untouched files — note them as out of scope.

- [ ] **Step 2: Type-check the touched modules**

Run: `uv run pyright sidequest/game/system_strain.py sidequest/game/creature_core.py sidequest/genre/models/rules.py sidequest/game/ruleset/cwn.py sidequest/telemetry/spans/cwn.py sidequest/game/builder.py sidequest/agents/tools/adjust_system_strain.py`
Expected: 0 NEW errors. `builder.py` may carry pre-existing errors — confirm against the pre-plan commit and report new vs pre-existing.

- [ ] **Step 3: Full test suite**

Run: `uv run pytest -n auto -q`
Expected: no NEW failures. Pay attention to: the generic resource tests (`tests/game/test_wire_genre_resources.py`, `tests/game/test_resource_threshold_lore.py`, `tests/server/test_resource_patch_wiring.py`) — they use synthetic fixtures, not the neon pack, so removing neon's humanity must NOT break them; the routing-completeness telemetry test; and any pack-load/validation tests. Classify any failure as new-vs-pre-existing (compare against the pre-plan base commit if unsure).

- [ ] **Step 4: Commit any fixups**

```bash
git add -A
git commit -m "chore(cwn): satisfy lint/type/test gate for system strain"
```

(Stage only this plan's files; if `git add -A` would sweep unrelated changes, stage specifically.)

---

## Self-Review (completed during authoring)

**Spec coverage (System Strain section, spec lines 94-109):**
- "Max = Body (CON) score, starts at 0" → Task 1 pool defaults + Task 6 chargen seeding (max = CONSTITUTION-flavor score).
- "Cyberware install → permanent strain; activation/drugs → temporary" → Task 5 `kind="permanent"` (raises floor) / `kind="temporary"`; Task 7 tool exposes both; Task 8 prose tells the narrator which kind.
- "Action over max fails; forced over → unconscious ≥1hr" → Task 5 gating (refused). Forced-over/unconscious explicitly deferred (no trigger in this plan — scope note).
- "First aid +1 strain" → Task 5 `kind="first_aid"` uses `cfg.first_aid_cost`.
- "−1 strain per night's rest" → Task 5 `kind="rest"` recovers to permanent floor.
- "humanity resource + humanity_tracker removed; tropes reframed/retired" → Task 8 (removal + reword; thematic tropes line kept by design).
- "OTEL cwn.system_strain.delta {source, amount, new_total, max}" → Task 4 span + Task 5 emits on every call (incl. an `applied` flag for the GM lie-detector to see refusals).
- "CON-bound, real resource not a 0-100 dial" → on CreatureCore, not the session-global ResourcePool (Tasks 1, 3, 6).

**Out of scope (correctly absent):** Trauma/Shock, Major Injury, HP/AC combat conversion, hacking confrontation, retiring the momentum `combat` confrontation — all plan 3/4.

**Placeholder scan:** Tasks 1-5 and 8-10 contain literal code and exact anchors. Tasks 6 and 7 intentionally instruct the implementer to read specific files (builder chargen idiom; the `update_resource_pool`/`apply_damage` tool + registry pattern) and mirror them, because the exact builder-finalization call shape and the tool-registration mechanism are pattern-bound and best matched against live code — the load-bearing logic (the engine method, Task 5) is fully concrete and exhaustively tested.

**Type/name consistency:** `SystemStrainPool` (current/max/permanent), `StrainResult` (applied/current/max/permanent/delta/reason), `SystemStrainConfig` (max_source/rest_recovery_per_night/first_aid_cost), `apply_system_strain(core, kind, amount, source, cfg, _tracer)`, span `cwn.system_strain.delta` with attrs {actor, source, amount, new_total, max, applied}, and the four `kind` values (temporary/first_aid/permanent/rest) are used identically across Tasks 1, 2, 4, 5, 7, 9. The OTEL helper name `cwn_system_strain_delta_span` matches between Task 4 (definition) and Task 5 (call).
```
