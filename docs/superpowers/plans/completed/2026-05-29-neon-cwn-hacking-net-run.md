# Neon CWN Hacking-as-Confrontation (`net_run`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy `net_combat` dial confrontation with a CWN-faithful `net_run` hacking confrontation resolved as 2d6 + Program + INT vs a named security-tier DC, with a `cwn.hacking.security_check` OTEL span fired by a dispatch seam.

**Architecture:** This is plan 4 of 4 in the `neon_dystopia → CWN` binding and extends the **already-live** `CwnRulesetModule` (System Strain + Trauma/Shock/Mortal-Injury seams shipped in plans 2-3). `net_run` is a *dial-based* confrontation (`player_metric=data`, `opponent_metric=alert`); its beats resolve through the **2d6 check shape** instead of the d20 attack shape combat uses, by branching the existing `dispatch_dice_throw`. A new `CwnRulesetModule.resolve_hacking` is a thin record-and-compute method (effective DC = security DC + alert modifier) that emits the lie-detector span — mirroring `resolve_shock`/`resolve_trauma`. No new dice resolver, no cyberspace minigame.

**Tech Stack:** Python 3.12 / pydantic v2 / FastAPI engine (`sidequest-server`, uv-managed), OpenTelemetry spans, YAML genre content (`sidequest-content`). Tests: pytest (`-n auto` default, `-n0` for ordering-sensitive runs).

---

## Spec

Source spec: `docs/superpowers/specs/2026-05-29-neon-cwn-hacking-net-run-design.md` (approved). Parent design: `docs/superpowers/specs/2026-05-28-neon-cwn-ruleset-design.md` §Hacking. Precedent plan (seam + span shape this mirrors): `docs/superpowers/plans/2026-05-28-neon-cwn-combat-lethality.md`.

## Two-repo split + branch setup

Engine + tests land in **`sidequest-server`**; the `net_run` confrontation + `cwn.hacking` ladder land in **`sidequest-content`** (`genre_packs/neon_dystopia/rules.yaml`). The server's wiring/e2e tests load the real neon pack off disk via `SIDEQUEST_GENRE_PACKS`, so **content must be committed locally before the server wiring tests run**, and **the content PR must merge before the server PR** (server CI checks out content). Default branch for PRs is `develop` (gitflow).

Before Task 1, create the feature branches:

```bash
# In sidequest-server
git checkout develop && git pull && git checkout -b feat/neon-cwn-hacking-net-run
# In sidequest-content
git -C ../sidequest-content checkout develop && git -C ../sidequest-content pull && git -C ../sidequest-content checkout -b feat/neon-hacking-net-run
```

All server-repo paths below are relative to the `sidequest-server/` working directory unless stated. The two content-repo paths are called out explicitly.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `sidequest/genre/models/rules.py` | `HackingConfig` model; `CwnConfig.hacking` field; `"hacking"` added to `ConfrontationDef` valid categories; `RulesConfig._validate_cwn` hacking cross-check | 1 |
| `sidequest/telemetry/spans/cwn.py` | `SPAN_CWN_HACKING_SECURITY_CHECK` constant + `SPAN_ROUTES` entry + `cwn_hacking_security_check_span()` emitter | 2 |
| `sidequest/game/ruleset/base.py` | `RulesetModule.resolve_hacking` no-emit default (returns `base_dc + alert_modifier`) | 3 |
| `sidequest/game/ruleset/cwn.py` | `CwnRulesetModule.resolve_hacking` — compute effective DC, emit span | 3 |
| `sidequest/game/encounter.py` | `StructuredEncounter.security_tier: str \| None` field | 4 |
| `sidequest/server/dispatch/encounter_lifecycle.py` | Stamp `security_tier` at `net_run` instantiation (default-tier fallback in content; unknown tier fails loud) | 4 |
| `sidequest/agents/subsystems/confrontation.py` | Thread `dispatch.params["security_tier"]` into `instantiate_encounter_from_trigger` | 4 |
| `sidequest/server/dispatch/dice.py` | `net_run` branch: build a 2d6 check request (not d20 attack), fire `resolve_hacking` after resolution | 5 |
| `../sidequest-content/genre_packs/neon_dystopia/rules.yaml` | Delete `net_combat`; add `net_run` + `cwn.hacking` ladder | 6 |
| `tests/genre/models/test_hacking_config.py` | `HackingConfig` validation (empty ladder, default-not-in-ladder) | 1 |
| `tests/telemetry/test_cwn_hacking_span.py` | span name + attribute payload | 2 |
| `tests/game/ruleset/test_cwn_hacking.py` | `resolve_hacking` return value, span emission, alert modifier, base no-emit | 3 |
| `tests/server/test_net_run_lifecycle.py` | `security_tier` stamping: default-tier path + unknown-tier fail-loud | 4 |
| `tests/server/test_net_run_resolution.py` | 2d6 pool + difficulty==effective DC; controlled faces → outcome tier | 5 |
| `tests/genre/test_neon_net_run_wiring.py` | load real neon, drive `Run Program` through production dispatch, assert `cwn.hacking.security_check` + the player/opponent dial paths | 7 |

---

## Task 1: `HackingConfig` model + `CwnConfig.hacking` + `"hacking"` category

**Files:**
- Modify: `sidequest/genre/models/rules.py` (add `HackingConfig` after `TraumaConfig` ~line 831; add field to `CwnConfig` ~line 847; add `"hacking"` to `valid_categories` line 511; extend `_validate_cwn` ~line 1003)
- Test: `tests/genre/models/test_hacking_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/genre/models/test_hacking_config.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import CwnConfig, HackingConfig


def test_hacking_config_valid():
    cfg = HackingConfig(
        default_tier="office",
        security_tiers={"home": 7, "office": 9, "facility": 11, "black_site": 12},
    )
    assert cfg.security_tiers["black_site"] == 12
    assert cfg.default_tier == "office"


def test_hacking_config_rejects_empty_ladder():
    with pytest.raises(ValidationError, match="security_tiers must be non-empty"):
        HackingConfig(default_tier="office", security_tiers={})


def test_hacking_config_rejects_default_not_in_ladder():
    with pytest.raises(ValidationError, match="default_tier"):
        HackingConfig(default_tier="moon_base", security_tiers={"office": 9})


def test_hacking_config_rejects_unknown_field():
    with pytest.raises(ValidationError):
        HackingConfig(
            default_tier="office", security_tiers={"office": 9}, bogus=1
        )


def test_cwn_config_hacking_defaults_none():
    # hacking is optional on the model; a CWN pack that never runs net_run
    # need not author it. A net_run firing without it fails loud at dispatch
    # (Task 5), not at model load.
    cfg = CwnConfig(attribute_map={})
    assert cfg.hacking is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/models/test_hacking_config.py -n0 -q`
Expected: FAIL — `ImportError: cannot import name 'HackingConfig'`.

- [ ] **Step 3: Add `HackingConfig` after `TraumaConfig`**

In `sidequest/genre/models/rules.py`, immediately after the `TraumaConfig` class (it ends at line 830 with `major_injury_save: str = "physical"`), insert:

```python
class HackingConfig(BaseModel):
    """CWN cyberspace security tuning (genre-level, content-authorable).

    security_tiers: named security level -> 2d6 difficulty (CWN published
      ratings 7-12). A net_run resolves Program checks against the tier's DC.
    default_tier: the tier stamped on a net_run opened without a named tier.
      An AUTHORED fallback declared in content (honors No Silent Fallbacks) —
      NOT a silent code default; it must be a key of security_tiers.
    """

    model_config = {"extra": "forbid"}

    default_tier: str
    security_tiers: dict[str, int]

    @model_validator(mode="after")
    def _validate(self) -> "HackingConfig":
        if not self.security_tiers:
            raise ValueError("cwn.hacking.security_tiers must be non-empty")
        if self.default_tier not in self.security_tiers:
            raise ValueError(
                f"cwn.hacking.default_tier {self.default_tier!r} "
                f"not in security_tiers {sorted(self.security_tiers)}"
            )
        return self
```

- [ ] **Step 4: Add the `hacking` field to `CwnConfig`**

In `CwnConfig` (the block ending at line 848 with `trauma: TraumaConfig = Field(default_factory=TraumaConfig)`), add a third field directly below the `trauma` line:

```python
    system_strain: SystemStrainConfig = Field(default_factory=SystemStrainConfig)
    trauma: TraumaConfig = Field(default_factory=TraumaConfig)
    hacking: HackingConfig | None = None
```

Also extend the `CwnConfig` docstring's closing lines — after the `Trauma is configured via ``trauma`` ...` line add:

```python
    Hacking is configured via ``hacking`` (optional; a net_run requires it).
```

- [ ] **Step 5: Add `"hacking"` to the confrontation valid-category set**

In `ConfrontationDef`'s validator, change line 511:

```python
        valid_categories = {"combat", "social", "pre_combat", "movement"}
```

to:

```python
        valid_categories = {"combat", "social", "pre_combat", "movement", "hacking"}
```

(Note for the implementer: do NOT add `"hacking"` to `_ADVERSARIAL_CATEGORIES` in `encounter_lifecycle.py`. A `net_run`'s "Other" is the network-alert dial, not a seated NPC; an adversarial category would trigger NPC opponent sourcing and a fail-loud `NoOpponentAvailableError` when no NPC is at the location. See ADR-116 — the dial *is* the Other.)

- [ ] **Step 6: Extend `_validate_cwn` to cross-check the hacking ladder**

In `RulesConfig._validate_cwn` (ends at line 1003 with `return self`), insert before the final `return self`:

```python
        if self.cwn.hacking is not None:
            # HackingConfig's own model_validator already enforces non-empty +
            # default-in-ladder. Cross-check tier DCs are sane 2d6 numbers so a
            # typo (e.g. 0 or 99) fails loud at pack load, not at dispatch.
            for tier, dc in self.cwn.hacking.security_tiers.items():
                if not (2 <= dc <= 12):
                    raise ValueError(
                        f"cwn.hacking.security_tiers[{tier!r}] = {dc} is not a "
                        "valid 2d6 difficulty (must be 2..12)"
                    )
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `uv run pytest tests/genre/models/test_hacking_config.py -n0 -q`
Expected: PASS (5 passed).

- [ ] **Step 8: Commit**

```bash
git add sidequest/genre/models/rules.py tests/genre/models/test_hacking_config.py
git commit -m "feat(cwn): HackingConfig model + hacking confrontation category"
```

---

## Task 2: `cwn.hacking.security_check` OTEL span

**Files:**
- Modify: `sidequest/telemetry/spans/cwn.py` (append after the major-injury span, ~line 207)
- Test: `tests/telemetry/test_cwn_hacking_span.py`

- [ ] **Step 1: Write the failing test**

Create `tests/telemetry/test_cwn_hacking_span.py`:

```python
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.telemetry.spans.cwn import (
    SPAN_CWN_HACKING_SECURITY_CHECK,
    cwn_hacking_security_check_span,
)


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_hacking_span_name_and_attributes():
    exporter, tracer = _exporter()
    cwn_hacking_security_check_span(
        actor="Rux",
        verb="Run Program",
        tier="black_site",
        base_dc=12,
        alert_modifier=2,
        effective_dc=14,
        result="Success",
        _tracer=tracer,
    )
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == SPAN_CWN_HACKING_SECURITY_CHECK == "cwn.hacking.security_check"
    attrs = dict(spans[0].attributes or {})
    assert attrs["actor"] == "Rux"
    assert attrs["verb"] == "Run Program"
    assert attrs["tier"] == "black_site"
    assert attrs["base_dc"] == 12
    assert attrs["alert_modifier"] == 2
    assert attrs["effective_dc"] == 14
    assert attrs["result"] == "Success"


def test_hacking_span_route_registered():
    from sidequest.telemetry.spans.cwn import SPAN_ROUTES

    route = SPAN_ROUTES[SPAN_CWN_HACKING_SECURITY_CHECK]
    assert route.event_type == "state_transition"
    assert route.component == "cwn"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_cwn_hacking_span.py -n0 -q`
Expected: FAIL — `ImportError: cannot import name 'SPAN_CWN_HACKING_SECURITY_CHECK'`.

- [ ] **Step 3: Add the span constant + route + emitter**

In `sidequest/telemetry/spans/cwn.py`, after the `SPAN_CWN_MAJOR_INJURY_ROLL` route block (ends ~line 112) add the constant + route:

```python
SPAN_CWN_HACKING_SECURITY_CHECK = "cwn.hacking.security_check"
SPAN_ROUTES[SPAN_CWN_HACKING_SECURITY_CHECK] = SpanRoute(
    event_type="state_transition",
    component="cwn",
    extract=lambda span: {
        "field": "hacking",
        "actor": (span.attributes or {}).get("actor", ""),
        "verb": (span.attributes or {}).get("verb", ""),
        "tier": (span.attributes or {}).get("tier", ""),
        "base_dc": (span.attributes or {}).get("base_dc", 0),
        "alert_modifier": (span.attributes or {}).get("alert_modifier", 0),
        "effective_dc": (span.attributes or {}).get("effective_dc", 0),
        "result": (span.attributes or {}).get("result", ""),
    },
)
```

Then, after the `cwn_major_injury_roll_span` function (ends ~line 206), append the emitter:

```python
def cwn_hacking_security_check_span(
    *,
    actor: str,
    verb: str,
    tier: str,
    base_dc: int,
    alert_modifier: int,
    effective_dc: int,
    result: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit a cwn.hacking.security_check span (lie-detector for CWN hacking).

    Fires on EVERY resolved net_run verb so the GM panel sees engaged and
    unengaged rolls alike. Point mutation, not a span of work — opens and
    immediately closes so WatcherSpanProcessor routes it to the state_transition
    feed.
    """
    attributes: dict[str, Any] = {
        "field": "hacking",
        "actor": actor,
        "verb": verb,
        "tier": tier,
        "base_dc": base_dc,
        "alert_modifier": alert_modifier,
        "effective_dc": effective_dc,
        "result": result,
        **attrs,
    }
    with Span.open(SPAN_CWN_HACKING_SECURITY_CHECK, attributes, tracer_override=_tracer):
        pass
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/telemetry/test_cwn_hacking_span.py -n0 -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add sidequest/telemetry/spans/cwn.py tests/telemetry/test_cwn_hacking_span.py
git commit -m "feat(cwn): cwn.hacking.security_check OTEL span + route"
```

---

## Task 3: `resolve_hacking` — base no-op + CWN emit

**Files:**
- Modify: `sidequest/game/ruleset/base.py` (add method after `resolve_downed`, ~line 132)
- Modify: `sidequest/game/ruleset/cwn.py` (add method + import the new span emitter)
- Test: `tests/game/ruleset/test_cwn_hacking.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/ruleset/test_cwn_hacking.py`:

```python
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.game.ruleset.swn import SwnRulesetModule

_CWN = CwnRulesetModule()
_SWN = SwnRulesetModule()


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_resolve_hacking_returns_base_plus_alert():
    dc = _CWN.resolve_hacking(
        verb="Run Program", tier="office", base_dc=9, alert_modifier=0, outcome="Success"
    )
    assert dc == 9


def test_alert_modifier_raises_effective_dc():
    # office=9, +2 alert escalation → effective DC 11.
    dc = _CWN.resolve_hacking(
        verb="Run Program", tier="office", base_dc=9, alert_modifier=2, outcome="Fail"
    )
    assert dc == 11


def test_resolve_hacking_emits_span_with_attrs():
    exporter, tracer = _exporter()
    _CWN.resolve_hacking(
        verb="Spoof",
        tier="black_site",
        base_dc=12,
        alert_modifier=1,
        outcome="CritSuccess",
        actor="Rux",
        _tracer=tracer,
    )
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "cwn.hacking.security_check"
    attrs = dict(spans[0].attributes or {})
    assert attrs["tier"] == "black_site"
    assert attrs["base_dc"] == 12
    assert attrs["alert_modifier"] == 1
    assert attrs["effective_dc"] == 13
    assert attrs["verb"] == "Spoof"
    assert attrs["result"] == "CritSuccess"


def test_base_swn_resolve_hacking_no_span():
    # native/swn inherit the base no-emit default: compute the DC, fire nothing.
    exporter, tracer = _exporter()
    dc = _SWN.resolve_hacking(
        verb="Run Program",
        tier="office",
        base_dc=9,
        alert_modifier=3,
        outcome="Success",
        actor="X",
        _tracer=tracer,
    )
    assert dc == 12
    assert exporter.get_finished_spans() == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_cwn_hacking.py -n0 -q`
Expected: FAIL — `AttributeError: 'CwnRulesetModule' object has no attribute 'resolve_hacking'`.

- [ ] **Step 3: Add the base no-op `resolve_hacking`**

In `sidequest/game/ruleset/base.py`, after `resolve_downed` (ends line 132 with `return None`), append a method to the `RulesetModule` class:

```python
    def resolve_hacking(
        self, *, verb, tier, base_dc, alert_modifier, outcome, actor="", _tracer=None
    ) -> int:
        """CWN cyberspace security check. Default: compute the effective DC,
        emit nothing (parallels resolve_shock returning 0). Only CWN overrides
        to emit cwn.hacking.security_check."""
        return int(base_dc) + int(alert_modifier)
```

- [ ] **Step 4: Add the CWN `resolve_hacking` override**

In `sidequest/game/ruleset/cwn.py`, first extend the span import block (lines 24-30) to include the new emitter:

```python
from sidequest.telemetry.spans.cwn import (
    cwn_hacking_security_check_span,
    cwn_major_injury_roll_span,
    cwn_mortal_injury_declared_span,
    cwn_shock_applied_span,
    cwn_system_strain_delta_span,
    cwn_trauma_roll_span,
)
```

Then, after `resolve_downed` (the class's last method, ends line 275 with the `DownedResult(...)` return), append:

```python
    def resolve_hacking(
        self,
        *,
        verb: str,
        tier: str,
        base_dc: int,
        alert_modifier: int,
        outcome: str,
        actor: str = "",
        _tracer: trace.Tracer | None = None,
    ) -> int:
        """Record a CWN cyberspace security check; return the effective DC.

        effective_dc = base_dc + alert_modifier (the CWN situational modifier:
        each network-alert escalation adds +1). Emits cwn.hacking.security_check
        — the GM lie-detector for the hacking subsystem; fires on EVERY net_run
        verb so the panel sees engaged + unengaged rolls alike. Does NOT mutate
        metrics or roll dice — the net_run dispatch seam builds the 2d6 check
        whose difficulty is this returned DC, the dice lib resolves the throw,
        and the confrontation engine applies the beat's tier deltas. Thin
        record-and-compute, consistent with resolve_shock/resolve_trauma."""
        effective_dc = int(base_dc) + int(alert_modifier)
        cwn_hacking_security_check_span(
            actor=actor,
            verb=verb,
            tier=tier,
            base_dc=int(base_dc),
            alert_modifier=int(alert_modifier),
            effective_dc=effective_dc,
            result=str(outcome),
            _tracer=_tracer,
        )
        return effective_dc
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_cwn_hacking.py -n0 -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/ruleset/base.py sidequest/game/ruleset/cwn.py tests/game/ruleset/test_cwn_hacking.py
git commit -m "feat(cwn): resolve_hacking — effective DC + security-check span (base no-op)"
```

---

## Task 4: `security_tier` on the encounter + stamping seam

**Files:**
- Modify: `sidequest/game/encounter.py` (add field to `StructuredEncounter`, ~line 199)
- Modify: `sidequest/server/dispatch/encounter_lifecycle.py` (add `security_tier` param to `instantiate_encounter_from_trigger`; compute + stamp in the dial branch ~line 742)
- Modify: `sidequest/agents/subsystems/confrontation.py` (read `dispatch.params["security_tier"]`, pass it through)
- Test: `tests/server/test_net_run_lifecycle.py`

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_net_run_lifecycle.py`. It builds a minimal synthetic CWN pack with a `net_run` confrontation and drives `instantiate_encounter_from_trigger` directly, asserting the stamped tier.

```python
from __future__ import annotations

import pytest

from sidequest.game.session import GameSnapshot
from sidequest.genre.models.pack import GenrePack
from sidequest.genre.models.rules import (
    BeatDef,
    ConfrontationDef,
    CwnConfig,
    HackingConfig,
    MetricDef,
    RulesConfig,
)
from sidequest.server.dispatch.encounter_lifecycle import (
    instantiate_encounter_from_trigger,
)


def _net_run_def() -> ConfrontationDef:
    return ConfrontationDef(
        type="net_run",
        label="Net Run",
        category="hacking",
        player_metric=MetricDef(name="data", starting=0, threshold=10),
        opponent_metric=MetricDef(name="alert", starting=0, threshold=10),
        beats=[
            BeatDef(id="run_program", label="Run Program", kind="strike", base=2, stat_check="Tech"),
        ],
        mood="tension",
    )


def _pack(hacking: HackingConfig | None) -> GenrePack:
    cwn = CwnConfig(
        attribute_map={
            "STRENGTH": "Brawn",
            "DEXTERITY": "Reflex",
            "CONSTITUTION": "Body",
            "INTELLIGENCE": "Tech",
            "WISDOM": "Instinct",
            "CHARISMA": "Cool",
        },
        hacking=hacking,
    )
    rules = RulesConfig(
        ruleset="cwn",
        ability_score_names=["Brawn", "Reflex", "Body", "Tech", "Instinct", "Cool"],
        cwn=cwn,
        confrontations=[_net_run_def()],
    )
    return GenrePack.model_construct(rules=rules)


def _ladder() -> HackingConfig:
    return HackingConfig(
        default_tier="office",
        security_tiers={"home": 7, "office": 9, "facility": 11, "black_site": 12},
    )


def _snapshot() -> GameSnapshot:
    snap = GameSnapshot()
    snap.genre_slug = "test_neon"
    return snap


def test_net_run_stamps_named_tier():
    snap = _snapshot()
    enc = instantiate_encounter_from_trigger(
        snapshot=snap,
        pack=_pack(_ladder()),
        encounter_type="net_run",
        player_name="Rux",
        npcs_present=[],
        genre_slug="test_neon",
        security_tier="black_site",
    )
    assert enc is not None
    assert enc.security_tier == "black_site"


def test_net_run_defaults_tier_when_omitted():
    snap = _snapshot()
    enc = instantiate_encounter_from_trigger(
        snapshot=snap,
        pack=_pack(_ladder()),
        encounter_type="net_run",
        player_name="Rux",
        npcs_present=[],
        genre_slug="test_neon",
        # no security_tier supplied → authored default
    )
    assert enc is not None
    assert enc.security_tier == "office"


def test_net_run_unknown_tier_fails_loud():
    snap = _snapshot()
    with pytest.raises(ValueError, match="security_tier"):
        instantiate_encounter_from_trigger(
            snapshot=snap,
            pack=_pack(_ladder()),
            encounter_type="net_run",
            player_name="Rux",
            npcs_present=[],
            genre_slug="test_neon",
            security_tier="moon_base",
        )


def test_net_run_without_ladder_fails_loud():
    snap = _snapshot()
    with pytest.raises(ValueError, match="cwn.hacking"):
        instantiate_encounter_from_trigger(
            snapshot=snap,
            pack=_pack(None),
            encounter_type="net_run",
            player_name="Rux",
            npcs_present=[],
            genre_slug="test_neon",
        )
```

> Implementer note: if `GenrePack.model_construct(...)` or `GameSnapshot()` don't accept these exact shapes, mirror the construction idiom from an existing lifecycle test (`grep -l instantiate_encounter_from_trigger tests/`) — the assertions on `enc.security_tier` and the fail-loud `pytest.raises` are the load-bearing parts; adapt only the fixture plumbing.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_net_run_lifecycle.py -n0 -q`
Expected: FAIL — `TypeError: instantiate_encounter_from_trigger() got an unexpected keyword argument 'security_tier'` (and `AttributeError` on `enc.security_tier`).

- [ ] **Step 3: Add the `security_tier` field to `StructuredEncounter`**

In `sidequest/game/encounter.py`, in `StructuredEncounter`, after the `location_overlay` field (line 199) add:

```python
    # net_run (CWN hacking) only — the named security tier this run targets,
    # stamped at instantiation from the dispatch param or the pack's
    # cwn.hacking.default_tier. The effective DC at resolution time is
    # cwn.hacking.security_tiers[security_tier] + alert escalation. None for
    # every non-hacking confrontation.
    security_tier: str | None = None
```

- [ ] **Step 4: Stamp `security_tier` in the lifecycle dial branch**

In `sidequest/server/dispatch/encounter_lifecycle.py`:

(a) Add the parameter to the signature (after `additional_player_names`, ~line 460):

```python
def instantiate_encounter_from_trigger(
    *,
    snapshot: GameSnapshot,
    pack: GenrePack,
    encounter_type: str,
    player_name: str,
    npcs_present: list,
    genre_slug: str | None,
    additional_player_names: list[str] | None = None,
    security_tier: str | None = None,
) -> StructuredEncounter | None:
```

(b) Compute the stamped tier just before the `enc = StructuredEncounter(` construction at line 742 (inside the dial branch, after the `pm`/`om` synthesis at line 741). Insert:

```python
        # net_run (CWN hacking, spec 2026-05-29): resolve the security tier the
        # run targets. The "Other" is the alert dial, not an NPC, so this is the
        # only adversary metadata net_run needs. Non-hacking confrontations
        # leave security_tier=None.
        stamped_security_tier: str | None = None
        if cdef.category == "hacking":
            from sidequest.genre.models.rules import CwnConfig

            cfg = pack.rules.ruleset_config() if pack and pack.rules else None
            if not isinstance(cfg, CwnConfig) or cfg.hacking is None:
                raise ValueError(
                    f"net_run confrontation {encounter_type!r} requires "
                    "cwn.hacking config on the pack; none authored (No Silent "
                    "Fallbacks)"
                )
            stamped_security_tier = security_tier or cfg.hacking.default_tier
            if stamped_security_tier not in cfg.hacking.security_tiers:
                raise ValueError(
                    f"net_run security_tier {stamped_security_tier!r} is not in "
                    f"cwn.hacking.security_tiers {sorted(cfg.hacking.security_tiers)}"
                )
```

(c) Add `security_tier=stamped_security_tier` to the `StructuredEncounter(...)` constructor call. After the `narrator_hints=[],` line (line 764) add:

```python
            narrator_hints=[],
            security_tier=stamped_security_tier,
        )
```

- [ ] **Step 5: Thread the dispatch param through `run_confrontation_dispatch`**

In `sidequest/agents/subsystems/confrontation.py`, in the `instantiate_encounter_from_trigger(...)` call (lines 125-133), add the param read from `dispatch.params`:

```python
        instantiate_encounter_from_trigger(
            snapshot=snapshot,
            pack=pack,
            encounter_type=enc_type,
            player_name=player_name,
            npcs_present=actor_list,
            genre_slug=snapshot.genre_slug,
            additional_player_names=additional_player_names,
            security_tier=dispatch.params.get("security_tier"),
        )
```

(`dispatch.params.get("security_tier")` returns `None` when the router/narrator didn't name a tier — the lifecycle then applies the pack's authored `default_tier`. This is the only enrichment net_run needs from the router; no IntentRouter prompt change is in scope for this plan.)

- [ ] **Step 6: Run the test to verify it passes**

Run: `uv run pytest tests/server/test_net_run_lifecycle.py -n0 -q`
Expected: PASS (4 passed).

- [ ] **Step 7: Commit**

```bash
git add sidequest/game/encounter.py sidequest/server/dispatch/encounter_lifecycle.py sidequest/agents/subsystems/confrontation.py tests/server/test_net_run_lifecycle.py
git commit -m "feat(cwn): stamp net_run security_tier at instantiation (default-tier + fail-loud)"
```

---

## Task 5: `net_run` resolution branch in `dispatch_dice_throw` (2d6 check + span)

**Files:**
- Modify: `sidequest/server/dispatch/dice.py` (add `_build_check_request_payload` helper; branch the request build at lines 289-314; fire `resolve_hacking` after dice resolution)
- Test: `tests/server/test_net_run_resolution.py`

This is the load-bearing wiring: combat hardcodes `attack_params` (d20 vs AC) at lines 297-304. `net_run` instead builds a **2d6** request with `modifier = INT mod + Program skill` and `difficulty = effective security DC`, resolves it through the same `resolve_dice_with_faces`, and fires `cwn.hacking.security_check`. The beat's dial deltas still apply via the existing `apply_beat` path (net_run is `dial_threshold`). The strike-damage / trauma / shock / downed seams are inert for net_run (its beats carry `damage_channel=none`, and there is no opponent core to drop), so no extra guards are needed there.

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_net_run_resolution.py`. It exercises the pure request-shape + resolution logic by driving `dispatch_dice_throw` against a synthetic net_run encounter, asserting (a) the broadcast `DiceRequest` carries a 2d6 pool, (b) `difficulty == base_dc + alert`, and (c) a controlled 2d6 face set resolves to the expected tier, and (d) `cwn.hacking.security_check` fired.

```python
from __future__ import annotations

import uuid

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.game.encounter import (
    EncounterActor,
    EncounterMetric,
    StructuredEncounter,
)
from sidequest.game.session import GameSnapshot
from sidequest.genre.models.pack import GenrePack
from sidequest.genre.models.rules import (
    BeatDef,
    ConfrontationDef,
    CwnConfig,
    HackingConfig,
    MetricDef,
    RulesConfig,
)
from sidequest.protocol.dice import DiceThrowPayload, DieSides, ThrowParams
from sidequest.protocol.messages import DiceRequestMessage
from sidequest.server.dispatch.dice import dispatch_dice_throw

_THROW = ThrowParams(velocity=(0, 0, 0), angular=(0, 0, 0), position=(0, 0))


def _pack() -> GenrePack:
    cwn = CwnConfig(
        attribute_map={
            "STRENGTH": "Brawn", "DEXTERITY": "Reflex", "CONSTITUTION": "Body",
            "INTELLIGENCE": "Tech", "WISDOM": "Instinct", "CHARISMA": "Cool",
        },
        hacking=HackingConfig(
            default_tier="office",
            security_tiers={"home": 7, "office": 9, "facility": 11, "black_site": 12},
        ),
    )
    rules = RulesConfig(
        ruleset="cwn",
        ability_score_names=["Brawn", "Reflex", "Body", "Tech", "Instinct", "Cool"],
        cwn=cwn,
        confrontations=[
            ConfrontationDef(
                type="net_run", label="Net Run", category="hacking",
                player_metric=MetricDef(name="data", starting=0, threshold=10),
                opponent_metric=MetricDef(name="alert", starting=0, threshold=10),
                beats=[
                    BeatDef(
                        id="run_program", label="Run Program", kind="strike",
                        base=2, stat_check="Tech", combat_skill=1,
                    ),
                ],
                mood="tension",
            )
        ],
    )
    return GenrePack.model_construct(rules=rules)


def _encounter(alert_current: int = 0) -> StructuredEncounter:
    return StructuredEncounter(
        encounter_type="net_run",
        player_metric=EncounterMetric(name="data", current=0, starting=0, threshold=10),
        opponent_metric=EncounterMetric(
            name="alert", current=alert_current, starting=0, threshold=10
        ),
        actors=[EncounterActor(name="Rux", role="runner", side="player")],
        security_tier="black_site",
    )


def _drive(*, faces, alert_current, tracer):
    captured: list = []
    snap = GameSnapshot()
    snap.genre_slug = "test_neon"
    payload = DiceThrowPayload(
        request_id=str(uuid.uuid4()),
        throw_params=_THROW,
        face=faces,
        beat_id="run_program",
    )
    return (
        dispatch_dice_throw(
            payload=payload,
            rolling_player_id="p1",
            character_name="Rux",
            character_stats={"Tech": 14},  # INT mod +1 at score 14 (SWN curve)
            encounter=_encounter(alert_current),
            pack=_pack(),
            genre_slug="test_neon",
            session_id="s1",
            round_number=1,
            room_broadcast=captured.append,
            snapshot=snap,
        ),
        captured,
    )


def test_net_run_builds_2d6_request_at_effective_dc():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    # black_site base 12, +2 alert escalation → effective DC 14.
    outcome, captured = _drive(faces=[6, 6], alert_current=2, tracer=tracer)
    req_msgs = [m for m in captured if isinstance(m, DiceRequestMessage)]
    assert req_msgs, "expected a DiceRequest broadcast"
    req = req_msgs[0].payload
    # 2d6 pool — NOT a d20 attack.
    assert len(req.dice) == 1
    assert req.dice[0].sides == DieSides.D6
    assert req.dice[0].count == 2
    assert req.difficulty == 14  # base_dc(12) + alert_modifier(2)


def test_net_run_controlled_faces_resolve_tier():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    # office=9, alert 0 → DC 9. Faces 2+3=5, +modifier(INT +1 + Program 1 = 2) → 7 < 9 → Fail.
    enc = _encounter(0)
    enc.security_tier = "office"
    captured: list = []
    snap = GameSnapshot()
    snap.genre_slug = "test_neon"
    payload = DiceThrowPayload(
        request_id=str(uuid.uuid4()), throw_params=_THROW, face=[2, 3], beat_id="run_program"
    )
    outcome = dispatch_dice_throw(
        payload=payload, rolling_player_id="p1", character_name="Rux",
        character_stats={"Tech": 14}, encounter=enc, pack=_pack(), genre_slug="test_neon",
        session_id="s1", round_number=1, room_broadcast=captured.append, snapshot=snap,
    )
    from sidequest.protocol.dice import RollOutcome

    assert outcome.outcome == RollOutcome.Fail


def test_net_run_fires_security_check_span():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Install as the global tracer so the seam's default-tracer span is captured.
    import opentelemetry.trace as ot

    ot.set_tracer_provider(provider)
    _drive(faces=[5, 5], alert_current=0, tracer=provider.get_tracer("test"))
    names = [s.name for s in exporter.get_finished_spans()]
    assert "cwn.hacking.security_check" in names
```

> Implementer note: the INT-modifier value at `Tech: 14` depends on `swn_attribute_modifier` (SWN's 3-18 → modifier curve). If +1 is wrong for score 14, read `sidequest/game/ruleset/swn.py::swn_attribute_modifier` and adjust the expected total in `test_net_run_controlled_faces_resolve_tier` — keep the chosen faces well clear of the DC so the *tier* (Fail) is unambiguous regardless of the exact mod. The span-capture test (`test_net_run_fires_security_check_span`) is the one that proves the seam fired; if installing a global tracer provider is flaky in the suite, instead assert via the watcher event the span routes to (mirror an existing `tests/server` dispatch test that reads `_watcher_publish` output).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_net_run_resolution.py -n0 -q`
Expected: FAIL — the request is built as a d20 attack (`req.dice[0].sides == DieSides.D20`, `difficulty == 10`), so the 2d6/effective-DC assertions fail; no `cwn.hacking.security_check` span.

- [ ] **Step 3: Add the 2d6 check-request helper**

In `sidequest/server/dispatch/dice.py`, after `_build_request_payload` (ends line 145), add:

```python
def _build_check_request_payload(
    *,
    request_id: str,
    rolling_player_id: str,
    character_name: str,
    stat: Stat,
    modifier: int,
    difficulty: int,
    context: str,
) -> DiceRequestPayload:
    """Shape a 2d6 skill-check DiceRequest (CWN net_run hacking path).

    Same envelope as _build_request_payload but a 2d6 pool instead of a single
    d20 — the CWN cyberspace Program check (Tech + Program vs the security DC).
    The physics overlay throws whatever pool the request names (ADR-074/075)."""
    return DiceRequestPayload(
        request_id=request_id,
        rolling_player_id=rolling_player_id,
        character_name=character_name,
        dice=[DieSpec(sides=DieSides.D6, count=2)],
        modifier=modifier,
        stat=stat,
        difficulty=difficulty,
        context=context,
    )
```

- [ ] **Step 4: Branch the request build for net_run**

In `dispatch_dice_throw`, replace the attack-setup block (lines 289-314 — from the `# Generalized attack setup:` comment through the `request = _build_request_payload(...)` call) with a fork. The net_run branch computes the security DC and builds a 2d6 request; the else branch is the unchanged d20 attack path. Insert just after `stat` is canonicalized (line 287) and a net_run detector:

```python
    is_net_run = bool(
        pack
        and pack.rules
        and pack.rules.ruleset == "cwn"
        and cdef.category == "hacking"
    )

    net_run_base_dc = 0
    net_run_alert_modifier = 0
    if is_net_run:
        # CWN net_run (spec 2026-05-29): resolve as 2d6 + INT mod + Program
        # skill vs the security DC, NOT d20 vs AC. The dice lib resolves any
        # pool; this selects the 2d6 shape — it does not build a new resolver.
        from sidequest.genre.models.rules import CwnConfig

        cfg = pack.rules.ruleset_config()
        if (
            not isinstance(cfg, CwnConfig)
            or cfg.hacking is None
            or encounter.security_tier is None
            or encounter.security_tier not in cfg.hacking.security_tiers
        ):
            raise DiceDispatchError(
                "net_run dispatch reached without a resolvable security tier "
                f"(tier={getattr(encounter, 'security_tier', None)!r}); the "
                "lifecycle seam should have stamped it (No Silent Fallbacks)"
            )
        net_run_base_dc = cfg.hacking.security_tiers[encounter.security_tier]
        # Alert escalation: each point of network alert (the opponent dial)
        # raises the effective DC by 1 (CWN situational modifier). The dial
        # climbs from the player's own failed verbs (`fail` opponent deltas —
        # a 2d6 Program check resolves under-DC as RollOutcome.Fail, never
        # CritFail, so the alert spike rides `fail`, not `crit_fail`).
        net_run_alert_modifier = int(encounter.opponent_metric.current)
        int_mod = ruleset.stat_modifier(character_stats, beat.stat_check)
        program_skill = int(beat.combat_skill)
        modifier = int_mod + program_skill
        difficulty = net_run_base_dc + net_run_alert_modifier
        request = _build_check_request_payload(
            request_id=payload.request_id,
            rolling_player_id=rolling_player_id,
            character_name=character_name,
            stat=stat,
            modifier=modifier,
            difficulty=difficulty,
            context=f"Program check vs {encounter.security_tier} — DC {difficulty}",
        )
    else:
        # Generalized attack setup: the module computes modifier + target number
        # with the target in hand, so SWN reads target AC. native ignores the
        # cores and reproduces stat_mod vs DC.
        target_core = None
        if encounter is not None:
            target_name = _opposite_side_first_actor(encounter, "player")
            if target_name is not None:
                target_core = snapshot.find_creature_core(target_name)
        attacker_core = snapshot.find_creature_core(character_name)
        attack = ruleset.attack_params(
            beat=beat,
            attacker_stats=character_stats,
            attacker_core=attacker_core,
            target_core=target_core,
        )
        modifier = attack.modifier
        difficulty = attack.target_number

        request = _build_request_payload(
            request_id=payload.request_id,
            rolling_player_id=rolling_player_id,
            character_name=character_name,
            stat=stat,
            modifier=modifier,
            difficulty=difficulty,
            context=f"{beat.label} — {beat.stat_check} check",
        )
```

- [ ] **Step 5: Fire `resolve_hacking` after dice resolution**

The dice resolve at lines 334-342 (`resolved = resolve_dice_with_faces(...)`) is unchanged. Immediately after that `try/except` block (after line 342), add the net_run span emit:

```python
    if is_net_run:
        # Lie-detector: record the resolved Program check. resolve_hacking
        # recomputes the same effective DC the request used and emits
        # cwn.hacking.security_check with the resolved tier. Fired here (after
        # resolve, before apply_beat) so the span carries the real outcome —
        # the dial deltas still land via apply_beat below.
        ruleset.resolve_hacking(
            verb=beat.label,
            tier=encounter.security_tier or "",
            base_dc=net_run_base_dc,
            alert_modifier=net_run_alert_modifier,
            outcome=resolved.outcome.value,
            actor=character_name,
        )
```

(No `_tracer` is passed — the seam uses the ambient global tracer, matching how the trauma/shock/downed seams in this same function call their `cwn_*` emitters without an explicit tracer.)

- [ ] **Step 6: Run the test to verify it passes**

Run: `uv run pytest tests/server/test_net_run_resolution.py -n0 -q`
Expected: PASS (3 passed).

- [ ] **Step 7: Run the broader dispatch suite for regressions**

Run: `uv run pytest tests/server/ -n0 -q -k "dice or confrontation or combat or net_run"`
Expected: no NEW failures — the d20 combat path is untouched (it's the `else` branch). Classify any failure as new-vs-pre-existing against the branch-point commit.

- [ ] **Step 8: Commit**

```bash
git add sidequest/server/dispatch/dice.py tests/server/test_net_run_resolution.py
git commit -m "feat(cwn): net_run dispatch branch — 2d6 Program check vs security DC + span"
```

---

## Task 6: Neon content — retire `net_combat`, add `net_run` + `cwn.hacking`

**Files:**
- Modify: `../sidequest-content/genre_packs/neon_dystopia/rules.yaml` (add `cwn.hacking` block; delete `net_combat` confrontation; add `net_run`)

Working directory for git: `../sidequest-content` (the content repo, on branch `feat/neon-hacking-net-run`).

- [ ] **Step 1: Add the `cwn.hacking` ladder**

In `genre_packs/neon_dystopia/rules.yaml`, in the `cwn:` block, after the `trauma:` sub-block (ends at line 29 `major_injury_save: physical`), add:

```yaml
  hacking:
    default_tier: office
    security_tiers:
      home: 7
      office: 9
      facility: 11
      black_site: 12
```

- [ ] **Step 2: Replace the `net_combat` confrontation with `net_run`**

Delete the entire `- type: net_combat` confrontation (lines 157-209, from `- type: net_combat` through its `mood: tension`) and replace it with the `net_run` confrontation below. `Jack In` is the act of opening the run (the confrontation start), so it is NOT a per-turn beat — the four beats are the in-run verbs:

```yaml
  - type: net_run
    label: "Net Run"
    category: hacking
    # CWN cyberspace as a dial confrontation. player_metric = objective
    # progress (data extracted); opponent_metric = network alert/trace.
    # Alert reaching threshold = CWN "Alert the Network x2" — the run is lost.
    # Each beat resolves as 2d6 + Program(combat_skill) + INT(Tech) vs the
    # security-tier DC; the cwn ruleset module fires cwn.hacking.security_check.
    player_metric:
      name: data
      starting: 0
      threshold: 10
    opponent_metric:
      name: alert
      starting: 0
      threshold: 10
    beats:
      - id: run_program
        label: "Run Program"
        kind: strike
        base: 2
        combat_skill: 1
        stat_check: Tech
        deltas:
          # `fail`, NOT `crit_fail`: a 2d6 Program check under the DC resolves to
          # RollOutcome.Fail (CritFail is a d20-nat-1 tier only), so the alert
          # spike must ride `fail` or the network can never win.
          fail:
            own: -1
            opponent: 2
        effect: "execute an offensive program — advance toward the objective"
        risk: "a botched call spikes the network alert"
        narrator_hint: "Describe the program tearing through the data architecture; failure trips an alarm."
      - id: spoof
        label: "Spoof / Unlock Barrier"
        kind: brace
        base: 1
        combat_skill: 1
        stat_check: Tech
        effect: "mask your signal or open a barrier — drop the network alert"
        narrator_hint: "Throw the trace off the scent. Buy room to breathe before the ICE closes in."
      - id: move_nodes
        label: "Move Nodes"
        # strike (advance the data dial by base on success), NOT push: a push
        # resolves the run on success — move_nodes is an incremental advance,
        # jack_out is the exit beat.
        kind: strike
        base: 2
        combat_skill: 1
        stat_check: Tech
        effect: "push deeper toward extraction"
        narrator_hint: "The runner traverses the lattice, closer to the prize."
      - id: jack_out
        label: "Jack Out"
        kind: push
        stat_check: Tech
        consequence: "exit the run — keep extracted data, end the confrontation"
        narrator_hint: "Yank the cable. Reality slams back. Did you get what you came for?"
    mood: tension
```

- [ ] **Step 3: Update the `net_combat` custom_rules prose note**

The `custom_rules.net_combat` prose block (lines 93-99) describes the retired confrontation. Rename the key and update the text so it documents `net_run`:

```yaml
  net_run: >-
    Cyberspace is a CWN net run: a dial confrontation, not a technical puzzle.
    When a runner jacks in, name a security tier (home/office/facility/
    black_site) — the engine sets the Program-check DC (7/9/11/12). Describe
    the virtual architecture as physical space — ICE walls, data streams,
    guardian programs as creatures. Each verb (Run Program, Spoof, Move Nodes,
    Jack Out) is a 2d6 + Program + Tech check vs that DC; the network fights
    back by raising the alert. Never narrate a breach the dice did not earn —
    the character is the expert, not the player.
```

- [ ] **Step 4: Validate the pack loads**

From the **orchestrator root** (`/Users/slabgorb/Projects/oq-3`), with `SIDEQUEST_GENRE_PACKS` pointing at the content repo:

Run: `cd sidequest-server && uv run python -c "from sidequest.genre.loader import load_pack; p = load_pack('neon_dystopia'); print('hacking', p.rules.cwn.hacking.security_tiers); print('net_run', [c.confrontation_type for c in p.rules.confrontations if c.confrontation_type in ('net_run','net_combat')])"`
Expected: prints the ladder dict and `['net_run']` (no `net_combat`). If `load_pack` import path differs, find it: `grep -rn "def load_pack" sidequest/genre/`.

- [ ] **Step 5: Commit (content repo)**

```bash
git -C ../sidequest-content add genre_packs/neon_dystopia/rules.yaml
git -C ../sidequest-content commit -m "feat(neon): replace net_combat with CWN net_run + cwn.hacking ladder"
```

---

## Task 7: End-to-end wiring test — neon drives `net_run` through dispatch

**Files:**
- Create: `tests/genre/test_neon_net_run_wiring.py`

Per CLAUDE.md testing doctrine (behavior/OTEL, **never** source-grep): load the **real** `neon_dystopia` pack, open a `net_run`, drive `Run Program` through the production `dispatch_dice_throw`, and assert `cwn.hacking.security_check` fired with the pack's ladder DC. This proves the pack→`CwnRulesetModule`→`cwn.hacking` config→dispatch seam chain end-to-end. Run **after Task 6 is committed locally** (content on disk via `SIDEQUEST_GENRE_PACKS`).

- [ ] **Step 1: Write the test**

Mirror the content-on-disk skip guard from an existing neon load test (`grep -l "load_pack(\"neon_dystopia\")" tests/`, e.g. `tests/genre/test_neon_loads_cwn.py`) and the dispatch-drive idiom from `tests/server/test_net_run_resolution.py` (Task 5). The test must:

1. `load_pack("neon_dystopia")`; assert `pack.rules.cwn.hacking.security_tiers["black_site"] == 12` and that `net_combat` is gone while `net_run` exists with `category == "hacking"` and `player_metric.name == "data"` / `opponent_metric.name == "alert"`.
2. Open a `net_run` via `instantiate_encounter_from_trigger(..., security_tier="black_site")`, seat a player actor, install an in-memory span exporter as the global tracer provider, and drive a `run_program` beat through `dispatch_dice_throw`.
3. Assert `cwn.hacking.security_check` fired and its `effective_dc` equals `12 + alert` (alert is 0 on the first verb, so 12), and `tier == "black_site"`.
4. Player-win path: drive `run_program` with winning faces repeatedly (or set `player_metric.current` near threshold) until `player_metric.current >= threshold`, assert `outcome.encounter_resolved` and the encounter `outcome` is a player victory.
5. Opponent-win path: set `opponent_metric.current` just below threshold, drive a FAILED `run_program` (faces `[1,1]` — total well under the DC → `RollOutcome.Fail`) so the `fail` opponent delta (`opponent: +2`) pushes alert to threshold; assert the run is lost (`opponent_metric.current >= threshold` and the encounter resolved to an opponent/loss outcome). (NOT `crit_fail`: a 2d6 pool never resolves to `CritFail` — that tier is d20-nat-1 only — so the spike rides `fail`.)

```python
from __future__ import annotations

import uuid

import pytest

try:
    from sidequest.genre.loader import load_pack

    _PACK = load_pack("neon_dystopia")
    _HAS_CONTENT = True
except Exception:  # content not on disk / load failure surfaced in the test
    _HAS_CONTENT = False


@pytest.mark.skipif(not _HAS_CONTENT, reason="sidequest-content not on disk")
def test_neon_net_run_config_and_confrontation():
    pack = load_pack("neon_dystopia")
    assert pack.rules.cwn.hacking.security_tiers["black_site"] == 12
    types = [c.confrontation_type for c in pack.rules.confrontations]
    assert "net_run" in types
    assert "net_combat" not in types
    nr = next(c for c in pack.rules.confrontations if c.confrontation_type == "net_run")
    assert nr.category == "hacking"
    assert nr.player_metric.name == "data"
    assert nr.opponent_metric.name == "alert"


@pytest.mark.skipif(not _HAS_CONTENT, reason="sidequest-content not on disk")
def test_neon_net_run_fires_security_check_through_dispatch():
    # ... open net_run (security_tier="black_site"), seat player actor,
    #     install global InMemorySpanExporter, drive run_program via
    #     dispatch_dice_throw, assert cwn.hacking.security_check fired with
    #     effective_dc == 12 and tier == "black_site". If it skips, load_pack
    #     raised — surface the exception (a real Task 6 pack-load failure)
    #     rather than accepting the skip.
    ...
```

Fill the `...` bodies using the Task 5 driver shape (real pack instead of the synthetic one). The two-direction win assertions (steps 4-5) go in two further `skipif`-guarded test functions.

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/genre/test_neon_net_run_wiring.py -n0 -q`
Expected: all PASS (NOT skipped). If it skips, `load_pack("neon_dystopia")` raised — surface and fix the underlying pack-load/validation failure from Task 6 rather than accepting the skip.

- [ ] **Step 3: Commit**

```bash
git add tests/genre/test_neon_net_run_wiring.py
git commit -m "test(cwn): wiring test — neon drives net_run through dispatch (OTEL security_check)"
```

---

## Task 8: Full gate — lint, types, full suite, PRs

**Files:** none (verification only). Server working directory unless noted.

- [ ] **Step 1: Lint + format**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors in this plan's files. If `ruff format --check` flags THIS plan's files, run `uv run ruff format` on them, re-stage, commit as `style:`. Do NOT touch pre-existing issues in untouched files.

- [ ] **Step 2: Type-check the touched modules**

Run: `uv run pyright sidequest/genre/models/rules.py sidequest/telemetry/spans/cwn.py sidequest/game/ruleset/base.py sidequest/game/ruleset/cwn.py sidequest/game/encounter.py sidequest/server/dispatch/encounter_lifecycle.py sidequest/agents/subsystems/confrontation.py sidequest/server/dispatch/dice.py`
Expected: 0 NEW errors. `dice.py` / `encounter_lifecycle.py` may carry pre-existing errors — compare against the branch-point commit and report new vs pre-existing.

- [ ] **Step 3: Full test suite**

Run: `uv run pytest -n auto -q`
Expected: no NEW failures. Pay attention to: the space_opera SWN combat e2e (base `resolve_hacking` is a no-op for swn — must still pass), native ruleset tests, the routing/telemetry tests, and any pack-load test. DB-gated tests skip without `SIDEQUEST_TEST_DATABASE_URL`. Classify any failure as new-vs-pre-existing against the branch-point base commit (the CWN combat-lethality plan handoff noted a stable count of pre-existing DB-infra/asset/corpus/lore-RAG failures — confirm the count is unchanged).

- [ ] **Step 4: Commit any fixups**

```bash
git add -A
git commit -m "chore(cwn): satisfy lint/type/test gate for net_run hacking"
```

(Stage only this plan's files; if `git add -A` would sweep unrelated changes, stage specifically.)

- [ ] **Step 5: Push both branches and open PRs (content first, then server)**

```bash
git -C ../sidequest-content push -u origin feat/neon-hacking-net-run
git push -u origin feat/neon-cwn-hacking-net-run
```

Open the content PR against `develop`, merge it, then open + merge the server PR against `develop` (server CI checks out content, so content must land first). Reconcile local `develop` to origin after each merge.

---

## Self-Review (completed during authoring)

**Spec coverage (decisions table, spec lines 40-49):**
- "Dial-based confrontation; player_metric = progress, opponent_metric = alert; opponent threshold = loss (reuse dial_threshold)" → Task 6 `net_run` def (`data`/`alert`, default `dial_threshold`) + the existing `apply_beat` dial path (no new win condition).
- "2d6 + Program + INT vs security DC via check shape, not d20 attack_params" → Task 5 net_run branch builds a 2d6 `_build_check_request_payload`; `else` keeps the d20 attack path.
- "Security DC narrator-set per scene; one net_run def" → Task 4 `security_tier` param + stamp; Task 6 single `net_run`.
- "Named ladder in content (home/office/facility/black_site → 7/9/11/12), narrator picks by name, engine maps tier→DC, tier+DC ride span + surface" → Task 1 `HackingConfig`, Task 6 ladder, Task 2/3 span carries tier + DCs, Task 5 `context=f"Program check vs {tier} — DC {dc}"` (player-facing legibility, spec §lines 219-226).
- "Each alert escalation adds +1 to effective DC" → Task 5 `net_run_alert_modifier = opponent_metric.current`.
- "resolve_hacking emits cwn.hacking.security_check per verb; dispatch seam fires it for net_run under cwn (Trauma/Shock precedent)" → Task 3 method + Task 5 seam call.
- "opposed_check not needed; static DC → beat_selection" → net_run def uses default `beat_selection` (no `resolution_mode` authored), Task 6.
- "net_combat replaced (rip-and-rebuild, no saves)" → Task 6 deletes `net_combat`, adds `net_run`.
- "Jack In is the confrontation open, not a beat" → Task 6 omits a Jack In beat; documented in the YAML comment.
- "Base RulesetModule.resolve_hacking is a no-emit default returning base_dc + alert_modifier; only cwn emits" → Task 3 base + override; `test_base_swn_resolve_hacking_no_span`.

**Testing & wiring coverage (spec lines 245-273):**
- Config validation (empty ladder / default-not-in-ladder) → Task 1 tests.
- Engine (`resolve_hacking` return, span, alert modifier, base no-emit) → Task 3 tests.
- Span (name + tier/DC attrs) → Task 2 tests.
- Resolution path (2d6 pool, difficulty == effective DC, controlled faces → tier) → Task 5 tests.
- Wiring test (real neon, drive Run Program, assert span — behavior/OTEL, never source-grep) → Task 7.
- End-to-end player-win + opponent-win ("Alert ×2" loss) → Task 7 steps 4-5.
- Default-tier path + unknown-tier fail-loud → Task 4 tests.

**Identified spec gaps resolved during authoring (not in the spec, surfaced from source):**
- `ConfrontationDef` validator's `valid_categories` did not include `"hacking"` (rules.py line 511) — Task 1 Step 5 adds it. Without this, Task 6's `category: hacking` fails pack load.
- A `net_run` must NOT be adversarial: `_ADVERSARIAL_CATEGORIES = {"combat","movement"}` (encounter_lifecycle.py). Leaving `hacking` out means no NPC opponent sourcing — the alert dial is the Other (ADR-116). Called out in Task 1 Step 5's implementer note.
- The "Program skill" term has no per-character skill store for confrontations; it rides the existing `BeatDef.combat_skill` field (the same term SWN combat uses via `attack_params`). Task 6 authors `combat_skill: 1` on the in-run verbs; Task 5 reads `beat.combat_skill`.

**Type/name consistency:** `resolve_hacking` signature (`verb, tier, base_dc, alert_modifier, outcome, actor, _tracer`) is identical in base.py (Task 3), cwn.py (Task 3), and the seam call (Task 5). `cwn_hacking_security_check_span` kwargs (`actor, verb, tier, base_dc, alert_modifier, effective_dc, result, _tracer`) match between Task 2 (def), Task 3 (call), and the Task 2 test. `HackingConfig` fields (`default_tier`, `security_tiers`) match across Task 1 (model), Task 4/5 (`cfg.hacking.security_tiers[...]`, `cfg.hacking.default_tier`), and Task 6 (YAML keys). `StructuredEncounter.security_tier` matches between Task 4 (field), Task 4 (stamp), and Task 5 (read).
