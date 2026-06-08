# WWN Magic Engine Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the server-side **faithful WWN magic engine** behind the `WwnRulesetModule` seam: per-character **Effort** (per-source commitment pools), **spell casting** (prepared list + daily casts + max level), the **cast spine** (`resolve_spellcast`), the Warrior's **Killing Blow** + **Veteran's Luck**, a real **scene/day reclaim**, chargen seeding, and the `wwn.*` magic OTEL spans — all **unit-tested against synthetic fixtures**. No content, no dispatch routing (Plan 3).

**Faithfulness is the whole point.** Mechanics are taken from the WWN SRD v1.0 (Crawford / Sine Nomine, CC0) and recorded in the spec's 2026-05-29 amendment (§A–§I). A career GM (Keith) and the two mechanics-first players (Sebastien, Jade) catch a fudge in one round; every mechanical decision emits an OTEL span because the GM panel is the lie detector.

**Architecture (decided — spec amendment §A):** WWN magic uses **bespoke per-`CreatureCore` pool models** (the SWN/CWN-family pattern, cf. `HpPool`/`SystemStrainPool`), seeded by the builder (cf. `seed_system_strain`), mutated by `WwnRulesetModule` methods that **emit `wwn.*` spans explicitly**. We reuse only the *interaction* plumbing the SWN/CWN ports proved (dice resolution, spans, beat dispatch, per-core pools, builder seeding) — **not** the session `ResourcePool` (session-scoped, unwired) nor the C&C `MagicState` ledger (wrong shape: per-level Vancian). The cwn↔wwn copy doctrine (spec §2.1) stands; WWN owns its magic outright.

**Tech Stack:** Python 3.12, pydantic v2, pytest (`-n0` for ordered runs), OpenTelemetry spans, `uv`. Run from `sidequest-server/`.

**Spec:** `docs/superpowers/specs/2026-05-29-wwn-ruleset-elemental-harmony-design.md` — **read the 2026-05-29 Amendment (§A–§I) first; it supersedes §3's ResourcePool language.**

**Builds on:** Plan 1 (merged, PR #520) — `WwnConfig`, `WwnRulesetModule(SwnRulesetModule)`, `telemetry/spans/wwn.py`, registry binding, the copied lethality layer, and the `dice.py` downed-seam wiring.

**Repo / branch:** `sidequest-server` (gitflow; base `develop`). All commits land on `feat/wwn-magic-engine`.

**Deferred to Plan 3 (explicitly NOT here):** the `elemental_harmony` content binding (rules/inventory/classes/char-creation), the `cast_spell` dispatch-routing branch, the day/long-rest *trigger* wiring, and the end-to-end wiring tests against the real pack. **Known dead-until-content (flagged, as `resolve_downed` was in Plan 1):** `resolve_spellcast` and the scene/day reclaim methods are exercised by unit tests here but are not reachable from production dispatch until Plan 3 authors the `cast_spell` beat and a rest action.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `sidequest/genre/models/rules.py` | `MagicConfig` sub-model; `WwnConfig.magic` field; `_validate_wwn` extension | Modify |
| `sidequest/genre/models/character.py` | `WwnClassMagic` sub-model; `ClassDef.wwn_magic` field (copy-not-share with C&C's `ClassMagicConfig`) | Modify |
| `sidequest/game/wwn_magic.py` | Per-core data models: `EffortCommitment`, `EffortPool`, `SpellcastingState`; result types (`EffortResult`, `SpellcastResult`, `VeteransLuckResult`) | Create |
| `sidequest/game/creature_core.py` | Add `effort: dict[str, EffortPool]` + `spellcasting: SpellcastingState | None` fields | Modify |
| `sidequest/telemetry/spans/wwn.py` | Add 5 magic spans (`wwn.spell.cast`, `wwn.effort.commit`, `wwn.effort.reclaim`, `wwn.killing_blow`, `wwn.veterans_luck`) | Modify |
| `sidequest/game/ruleset/wwn.py` | New methods: `commit_effort`, `reclaim_effort`, `reclaim_scene_effort`, `reclaim_day_and_refresh`, `resolve_spellcast`, `apply_killing_blow`, `veterans_luck` | Modify |
| `sidequest/game/builder.py` | `seed_wwn_magic(...)` helper + call at the `build()` seam (after `seed_system_strain`) | Modify |
| `sidequest/server/session.py` | Wire scene-end Effort reclaim into `Session.end_scene` (ruleset-gated) | Modify |
| `tests/game/ruleset/test_wwn_magic_config.py` | `MagicConfig` + `_validate_wwn` magic-validator tests | Create |
| `tests/game/ruleset/test_wwn_effort.py` | Effort-max formula, commit/reclaim, maintained/scene/day semantics, span assertions | Create |
| `tests/game/ruleset/test_wwn_spellcast.py` | Cast spine: fail-loud refuse, spend, force defender save, damage + save-for-half, span | Create |
| `tests/game/ruleset/test_wwn_warrior.py` | Killing Blow rider, Veteran's Luck once/scene, span assertions | Create |
| `tests/game/test_wwn_chargen_seed.py` | `seed_wwn_magic` against a synthetic class fixture: pool maxes + spellcasting state | Create |
| `tests/server/test_wwn_scene_reclaim.py` | `Session.end_scene` reclaims scene Effort for a wwn core (ruleset-gated) | Create |

**Reference sources to read and mirror (the proven idioms):**
- `sidequest/game/system_strain.py` — the per-core pure-data pool model to mirror for `EffortPool`.
- `sidequest/game/ruleset/wwn.py` — Plan 1's `apply_system_strain`/`resolve_trauma`/`resolve_downed` (the cfg-guard + explicit-span + result-object idiom every new method follows).
- `sidequest/game/builder.py` — `seed_system_strain` (line ~80) and its call site in `build()` (line ~2250) — the seeding seam to mirror.
- `sidequest/telemetry/spans/wwn.py` — Plan 1's 5 lethality spans (the `SPAN_WWN_*` + `SpanRoute` + `wwn_*_span()` helper idiom). Already re-exported in `telemetry/spans/__init__.py` and covered by `test_routing_completeness` — new spans are auto-covered.
- `sidequest/game/ruleset/swn.py` — inherited `save_params` (defender save) and `resolve_damage` the cast spine reuses.
- `sidequest/server/session.py` — `Session.end_scene` (line ~71) and `clear_scratch_on_scene_end` (the scene-boundary precedent the reclaim hook mirrors).
- `sidequest/genre/models/character.py` — `ClassDef` + `ClassMagicConfig` (do NOT reuse the B/X `slots_by_class_level` shape; add a new `WwnClassMagic`).

---

## Task 0: Branch

- [ ] **Step 1: Create the feature branch off `develop`**

```bash
cd sidequest-server
git checkout develop && git pull --ff-only
git checkout -b feat/wwn-magic-engine
```

- [ ] **Step 2: Record the full-suite baseline** (per the gate discipline). Run the suite once on `develop` BEFORE any change, with both env vars, and save the failure/error list — only a NEW failure is a regression:

```bash
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
uv run pytest -q 2>&1 | tail -40
```
(As of Plan 1 merge the baseline was **9 failed / 17 errors**, all in content/audit/reference suites — none in `tests/game/ruleset/`. Re-confirm.)

---

## Task 1: `MagicConfig` + `WwnConfig.magic` + validator

Ruleset-level magic constants (NOT per-class — per-class tables live on the class def, Task 5). `MagicConfig` carries: the Effort-max formula shape, the Killing-Blow divisor, the comfort-gated day-reclaim flag, and the default spell save.

**Files:** Modify `sidequest/genre/models/rules.py`; create `tests/game/ruleset/test_wwn_magic_config.py`.

- [ ] **Step 1: Write the failing tests** — `tests/game/ruleset/test_wwn_magic_config.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import MagicConfig, RulesConfig, WwnConfig

_EH_AMAP = {
    "STRENGTH": "Strength", "DEXTERITY": "Agility", "CONSTITUTION": "Endurance",
    "INTELLIGENCE": "Insight", "WISDOM": "Spirit", "CHARISMA": "Harmony",
}
_EH_FLAVOR = ["Strength", "Agility", "Endurance", "Insight", "Spirit", "Harmony"]


def test_magic_config_defaults():
    m = MagicConfig()
    assert m.killing_blow_divisor == 2          # ceil(level/2)
    assert m.day_reclaim_requires_comfort is True
    assert m.default_spell_save == "mental"
    assert m.effort_base == 1                    # max = effort_base + skill + mod


def test_wwn_config_has_magic_default():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    assert cfg.magic.default_spell_save == "mental"   # default_factory


def test_magic_default_spell_save_must_be_valid():
    with pytest.raises(ValidationError, match="default_spell_save"):
        RulesConfig(
            ruleset="wwn", ability_score_names=_EH_FLAVOR,
            wwn=WwnConfig(attribute_map=_EH_AMAP, magic=MagicConfig(default_spell_save="luck_XYZ")),
        )


def test_wwn_accepts_valid_magic_block():
    rules = RulesConfig(
        ruleset="wwn", ability_score_names=_EH_FLAVOR,
        wwn=WwnConfig(attribute_map=_EH_AMAP, magic=MagicConfig(default_spell_save="evasion")),
    )
    assert rules.wwn.magic.default_spell_save == "evasion"
```

- [ ] **Step 2: Run, verify FAIL** (`ImportError: cannot import name 'MagicConfig'`):
`SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test uv run pytest tests/game/ruleset/test_wwn_magic_config.py -n0 -q`

- [ ] **Step 3: Add `MagicConfig`** in `rules.py`, immediately before `WwnConfig`:

```python
class MagicConfig(BaseModel):
    """WWN magic ruleset constants (Sine Nomine, CC0). Per-class tables (Effort
    sources, casts/day, max spell level) live on the class def (WwnClassMagic),
    NOT here — this holds engine-level constants only. Spells name their own save;
    default_spell_save is the fallback when a spell omits one."""

    model_config = {"extra": "forbid"}

    effort_base: int = 1                       # Effort max = effort_base + skill + attr mod
    killing_blow_divisor: int = 2              # Killing Blow adds ceil(level / divisor)
    day_reclaim_requires_comfort: bool = True  # day-Effort needs a comfortable rest
    default_spell_save: str = "mental"
```

- [ ] **Step 4: Add the `magic` field on `WwnConfig`** (after `trauma`):

```python
    magic: MagicConfig = Field(default_factory=MagicConfig)
```

- [ ] **Step 5: Extend `_validate_wwn`** — before the final `return self`, validate the spell save:

```python
        if self.wwn.magic.default_spell_save not in valid_saves:
            raise ValueError(
                f"wwn.magic.default_spell_save = {self.wwn.magic.default_spell_save!r} "
                f"is not one of {sorted(valid_saves)}"
            )
```
(`valid_saves` is the `{"physical","evasion","mental","luck"}` set already defined in `_validate_wwn` by Plan 1 — reuse it; do not redefine.)

- [ ] **Step 6: Run, verify PASS (4 passed).** Then **commit**:
```bash
git add sidequest/genre/models/rules.py tests/game/ruleset/test_wwn_magic_config.py
git commit -m "feat(ruleset): WWN MagicConfig + WwnConfig.magic + validator"
```

---

## Task 2: Per-core magic models + `CreatureCore` fields

Faithful WWN data (spec amendment §B, §C). Pure data; all rules live in `WwnRulesetModule` (Task 4/5), mirroring `system_strain.py`.

**Files:** Create `sidequest/game/wwn_magic.py`; modify `sidequest/game/creature_core.py`; tests are exercised via Tasks 4/5 (these are pure models — a small direct test is included).

- [ ] **Step 1: Create `sidequest/game/wwn_magic.py`:**

```python
"""WWN magic — per-CreatureCore data models (pure data; rules live in WwnRulesetModule).

Mirrors game/system_strain.py: the model is inert; gating, reclaim, and span
emission are owned by WwnRulesetModule. Faithful to WWN SRD §1.4.4 (Effort:
per-source commitment pools with maintained/scene/day durations) and §4.2
(spells: a prepared list + a daily 'casts' pool + a max castable level — NOT
per-level Vancian slots).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EffortDuration = Literal["maintained", "scene", "day"]


class EffortCommitment(BaseModel):
    model_config = {"extra": "forbid"}

    points: int
    duration: EffortDuration
    label: str = ""           # the Art/power the Effort fuels, for the GM panel


class EffortPool(BaseModel):
    """One Effort pool for ONE class-source (High Mage, Vowed, ...). Points from
    one source cannot fuel another (SRD §1.4.4), so a caster carries a dict of
    these keyed by source. ``max`` is seeded at chargen = effort_base + relevant
    skill level + governing attribute modifier (Partial class: -1, min 1)."""

    model_config = {"extra": "forbid"}

    source: str
    max: int
    commitments: list[EffortCommitment] = Field(default_factory=list)

    @property
    def committed(self) -> int:
        return sum(c.points for c in self.commitments)

    @property
    def available(self) -> int:
        return self.max - self.committed


class SpellcastingState(BaseModel):
    """WWN spell economy (SRD §4.2). A cast spends ONE from ``casts_remaining``
    on ANY prepared spell of level <= max_spell_level; refreshes to casts_per_day
    on a night's rest. ``prepared`` holds spell ids chosen at rest from the
    spellbook (content)."""

    model_config = {"extra": "forbid"}

    prepared: list[str] = Field(default_factory=list)
    casts_remaining: int = 0
    casts_per_day: int = 0
    max_spell_level: int = 0


class EffortResult(BaseModel):
    model_config = {"extra": "forbid"}
    applied: bool
    source: str
    available: int
    max: int
    reason: str = ""


class SpellcastResult(BaseModel):
    model_config = {"extra": "forbid"}
    cast: bool
    spell_id: str
    casts_remaining: int
    save_made: bool | None = None
    damage: int = 0
    reason: str = ""


class VeteransLuckResult(BaseModel):
    model_config = {"extra": "forbid"}
    applied: bool
    mode: str          # "force_hit" | "force_miss"
    reason: str = ""
```

- [ ] **Step 2: Add fields to `CreatureCore`** in `creature_core.py` (next to `system_strain` / `rig_pool`). Read the surrounding block first and match the import + field idiom:

```python
from sidequest.game.wwn_magic import EffortPool, SpellcastingState
# ...
    effort: dict[str, EffortPool] = Field(default_factory=dict)
    spellcasting: SpellcastingState | None = None
```
Defaults make this backward-compatible (legacy/non-wwn cores carry an empty dict + None).

- [ ] **Step 3: Quick model test** — append to `tests/game/ruleset/test_wwn_effort.py` is fine, OR inline here. Verify `available`/`committed` math:
```python
def test_effort_pool_available_math():
    from sidequest.game.wwn_magic import EffortCommitment, EffortPool
    p = EffortPool(source="vowed", max=3, commitments=[EffortCommitment(points=1, duration="scene")])
    assert p.committed == 1 and p.available == 2
```

- [ ] **Step 4: Verify import + commit:**
```bash
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
  uv run python -c "from sidequest.game.creature_core import CreatureCore; c=CreatureCore(name='x',description='y',personality='z'); print(c.effort, c.spellcasting)"
git add sidequest/game/wwn_magic.py sidequest/game/creature_core.py
git commit -m "feat(game): per-core WWN magic models (EffortPool, SpellcastingState) on CreatureCore"
```

---

## Task 3: `wwn.*` magic spans

Extend `telemetry/spans/wwn.py` with five magic spans, following Plan 1's exact `SPAN_WWN_* + SpanRoute + wwn_*_span()` idiom. Already re-exported via `telemetry/spans/__init__.py` (Plan 1) and covered by `test_routing_completeness` — new spans need no `__init__` change but DO ride the completeness gate.

**Files:** Modify `sidequest/telemetry/spans/wwn.py`. (Span emission asserted by Tasks 4/5/6 tests.)

- [ ] **Step 1: Add the five spans** — mirror the existing helpers in the file. Each gets a `SPAN_WWN_* = "wwn.<name>"` constant, a `SPAN_ROUTES[...] = SpanRoute(event_type="state_transition", component="wwn", extract=...)` registration, and a `wwn_*_span(*, ..., _tracer=None, **attrs)` helper that opens `Span.open(...)`. The five:

| Constant | Span name | Key attributes |
|---|---|---|
| `SPAN_WWN_SPELL_CAST` | `wwn.spell.cast` | actor, spell_id, level, refused, casts_remaining, save, save_made, damage |
| `SPAN_WWN_EFFORT_COMMIT` | `wwn.effort.commit` | actor, source, points, duration, available, applied |
| `SPAN_WWN_EFFORT_RECLAIM` | `wwn.effort.reclaim` | actor, source, points, trigger, available |
| `SPAN_WWN_KILLING_BLOW` | `wwn.killing_blow` | actor, level, bonus, base, total |
| `SPAN_WWN_VETERANS_LUCK` | `wwn.veterans_luck` | actor, mode, applied |

(Replicate the exact structure of `wwn_shock_applied_span`/`wwn_trauma_roll_span` from the file — same imports, same `Span.open` body. Do not invent new helpers/APIs.)

- [ ] **Step 2: Verify imports + namespace clean** (the docstring may mention cwn provenance — that's fine; functional code must be `wwn.*` only):
```bash
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
  uv run python -c "import sidequest.telemetry.spans.wwn as w; print(w.SPAN_WWN_SPELL_CAST, w.SPAN_WWN_EFFORT_COMMIT, w.SPAN_WWN_KILLING_BLOW)"
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
  uv run pytest tests/telemetry/test_routing_completeness.py -n0 -q   # must stay green; now covers the 5 new spans
```

- [ ] **Step 3: Commit:**
```bash
git add sidequest/telemetry/spans/wwn.py
git commit -m "feat(telemetry): wwn.* magic spans (spell.cast, effort.commit/reclaim, killing_blow, veterans_luck)"
```

---

## Task 4: Effort engine — `commit_effort` / `reclaim_effort` (+ scene/day reclaim)

Faithful Effort (spec §B). All rules in `WwnRulesetModule`; fail loud on over-commit; emit spans. Mirror Plan 1's `apply_system_strain` idiom (cfg-guard, result object, explicit span).

**Files:** Modify `sidequest/game/ruleset/wwn.py`; create `tests/game/ruleset/test_wwn_effort.py`.

- [ ] **Step 1: Write the failing tests** — `test_wwn_effort.py`. Cover: commit decrements `available` and emits `wwn.effort.commit`; over-commit is **refused** (`applied=False`, available unchanged) — fail-loud-but-recorded; `reclaim_effort(maintained)` returns points immediately; `reclaim_scene_effort` drops only `scene` commitments (leaves `day`/`maintained`); `reclaim_day_and_refresh` drops `day` (+ `scene`) commitments AND refreshes `spellcasting.casts_remaining` to `casts_per_day`; each reclaim emits `wwn.effort.reclaim`. Use the `InMemorySpanExporter` idiom from `tests/game/ruleset/test_cwn_shock.py`, passing `_tracer=tracer`. Build a `CreatureCore` with a seeded `EffortPool` directly (synthetic). Pin span names literally (`"wwn.effort.commit"`, `"wwn.effort.reclaim"`).

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement the methods** on `WwnRulesetModule`:

```python
def commit_effort(self, *, core, source, points=1, duration="scene", label="",
                  _tracer=None) -> EffortResult:
    """Commit Effort from one class-source pool (SRD §1.4.4). Over-commit is
    REFUSED (applied=False) — fail loud, never silently clamp. Emits
    wwn.effort.commit."""
    pool = core.effort.get(source)
    if pool is None:
        raise ValueError(f"{core.name!r} has no {source!r} Effort pool; seed it at chargen")
    applied = points <= pool.available
    reason = "" if applied else f"only {pool.available} of {points} Effort available"
    if applied:
        pool.commitments.append(EffortCommitment(points=points, duration=duration, label=label))
    wwn_effort_commit_span(actor=core.name, source=source, points=points, duration=duration,
                           available=pool.available, applied=applied, _tracer=_tracer)
    return EffortResult(applied=applied, source=source, available=pool.available, max=pool.max, reason=reason)
```
Plus `reclaim_effort(core, source, *, label/predicate, trigger="maintained")` (drop matching commitments, emit `wwn.effort.reclaim`), `reclaim_scene_effort(core, *, _tracer)` (drop all `duration=="scene"` across every pool; emit one reclaim span per pool touched), and `reclaim_day_and_refresh(core, *, comfortable=True, cfg, _tracer)` (drop `scene` + `day` commitments — but if `cfg.magic.day_reclaim_requires_comfort and not comfortable`, leave `day` committed; then refresh `core.spellcasting.casts_remaining = casts_per_day`). Import the new span helpers + `EffortCommitment`/`EffortResult` at the top of `wwn.py`.

- [ ] **Step 4: Run, verify PASS. Commit:**
```bash
git add sidequest/game/ruleset/wwn.py tests/game/ruleset/test_wwn_effort.py
git commit -m "feat(ruleset): WWN Effort engine — commit/reclaim with maintained/scene/day, spans"
```

---

## Task 5: Cast spine — `resolve_spellcast`

Faithful (spec §C/§D). Approach C: engine guarantees the economy + rolls; bespoke effect is narrator prose. Reuses inherited `save_params` (defender saves) and `resolve_damage`.

**Files:** Modify `sidequest/game/ruleset/wwn.py`; create `tests/game/ruleset/test_wwn_spellcast.py`.

- [ ] **Step 1: Write the failing tests.** A small `Spell`-like fixture (id, level, save category or None, damage die or None, damage_per_level: bool). Cover: **refuse — no cast left** (`casts_remaining=0` → `cast=False`, `reason` set, emits `wwn.spell.cast` with `refused=True`, casts unchanged) — fail loud; **refuse — not prepared**; **refuse — level > max_spell_level**; **success** decrements `casts_remaining`, emits `wwn.spell.cast`; **forces the defender save** (a save spell rolls the defender's `save_params` for the named category — assert `save_made` populated); **damage + save-for-half** (damage = caster_level × die; halved when the save is made). Pin `"wwn.spell.cast"` literally. Use a deterministic `rng` (pin via monkeypatch like `test_cwn_trauma.py`).

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement `resolve_spellcast`** on `WwnRulesetModule`:
```python
def resolve_spellcast(self, *, caster_core, spell, target_core=None, cfg, rng,
                      _tracer=None) -> SpellcastResult:
    """WWN cast spine (SRD §4.2). Validate (prepared, casts_remaining, level<=max)
    -> fail loud / refused, recorded on wwn.spell.cast. Spend one cast. Force the
    defender's own save (inherited save_params) when the spell offers one. Roll
    caster_level x die when it's a damage spell (save halves). Bespoke effect is
    narrator prose. Emits wwn.spell.cast."""
```
Validation refuses (does NOT raise) but records `refused=True` on the span and returns `cast=False` — refusing a cast is a normal mechanical outcome, but it must be **loud** (recorded), never a silent no-op. `isinstance(cfg, WwnConfig)` guard (raise) as in Plan 1's methods. The save uses the spell's named category or `cfg.magic.default_spell_save`; compute the **defender's** `save_params(stats=..., save=<cat>, level=<defender level>, label=..., cfg=cfg)` and roll 1d20 vs its difficulty. Damage reuses the inherited `resolve_damage`/`DamageSpec.roll` path; halve (round down) on a made save.

> **Executor note:** the `spell` object's shape (a content `Spell` model) is authored in Plan 3. For Plan 2, define the **minimal protocol the spine needs** (`.id`, `.level`, `.save: str | None`, `.damage_die: str | None`, `.damage_per_level: bool`) as a tiny typed structure in `wwn_magic.py` (e.g. `CastInput`) and have `resolve_spellcast` accept that. Do NOT model the full spell catalog (Plan 3). The test fixtures construct `CastInput`s.

- [ ] **Step 4: Run, verify PASS. Commit:**
```bash
git add sidequest/game/ruleset/wwn.py sidequest/game/wwn_magic.py tests/game/ruleset/test_wwn_spellcast.py
git commit -m "feat(ruleset): WWN cast spine — resolve_spellcast (economy + defender save + damage), span"
```

---

## Task 6: Warrior — Killing Blow + Veteran's Luck

Faithful (spec §E). Fray Die struck. Killing Blow is a passive damage rider; Veteran's Luck is a once/scene Instant action.

**Files:** Modify `sidequest/game/ruleset/wwn.py`; create `tests/game/ruleset/test_wwn_warrior.py`.

- [ ] **Step 1: Write the failing tests.** Killing Blow: `apply_killing_blow(base_total=5, level=3, cfg=...)` returns `5 + ceil(3/2) == 7`, emits `wwn.killing_blow` (assert `bonus==2`, `total==7`); the bonus also applies to Shock (assert via the returned/Shock path). Veteran's Luck: first call in a scene returns `applied=True` and sets a scene-scoped used-flag (a `Status` with a known marker, mirroring how scene-scoped flags are stored — read how `clear_scratch_on_scene_end` / Scratch statuses work and mirror); second call same scene returns `applied=False`; emits `wwn.veterans_luck`. Pin span names literally.

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement:**
```python
def apply_killing_blow(self, *, base_total, level, cfg, actor="", _tracer=None) -> int:
    """WWN Warrior Killing Blow (SRD §1.5.18): add ceil(level / divisor) to the
    damage of any attack/spell/ability (and to Shock). Returns the new total;
    emits wwn.killing_blow."""
    import math
    bonus = math.ceil(int(level) / cfg.magic.killing_blow_divisor)
    total = base_total + bonus
    wwn_killing_blow_span(actor=actor, level=level, bonus=bonus, base=base_total, total=total, _tracer=_tracer)
    return total
```
`veterans_luck(core, *, mode, _tracer=None) -> VeteransLuckResult` — `mode ∈ {"force_hit","force_miss"}`; once per scene (guarded by a scene-scoped used-marker `Status`, cleared by the scene-end sweep); emit `wwn.veterans_luck`.

> **Executor note (Killing Blow + Shock):** read Plan 1's `resolve_shock`/CWN's Killing-Blow-adds-to-Shock relationship before deciding whether Killing Blow folds into `resolve_damage` or stays a standalone rider. Keep it a standalone `apply_killing_blow` for Plan 2 (dispatch wiring is Plan 3); the test asserts the math + span, not the dispatch integration.

- [ ] **Step 4: Run, verify PASS. Commit:**
```bash
git add sidequest/game/ruleset/wwn.py tests/game/ruleset/test_wwn_warrior.py
git commit -m "feat(ruleset): WWN Warrior — Killing Blow + Veteran's Luck (faithful; Fray Die struck), spans"
```

---

## Task 7: Class-def magic model + chargen seeding

Per-class magic data on the class def (copy-not-share with C&C's `ClassMagicConfig`), consumed by a `seed_wwn_magic` builder helper that mirrors `seed_system_strain`.

**Files:** Modify `sidequest/genre/models/character.py`; modify `sidequest/game/builder.py`; create `tests/game/test_wwn_chargen_seed.py`.

- [ ] **Step 1: Add `WwnClassMagic`** on `ClassDef` (new optional field `wwn_magic: WwnClassMagic | None = None`). Read `ClassDef`/`ClassMagicConfig` first; do NOT reuse the B/X `slots_by_class_level` shape. `WwnClassMagic` carries the per-class faithful data:
```python
class WwnClassMagic(BaseModel):
    model_config = {"extra": "forbid"}
    effort_sources: list[WwnEffortSource] = Field(default_factory=list)   # one per class-source
    casts_per_day_by_level: dict[str, int] = Field(default_factory=dict)  # "1": 1 ... "10": 6
    max_spell_level_by_level: dict[str, int] = Field(default_factory=dict)
    prepared_by_level: dict[str, int] = Field(default_factory=dict)
    partial: bool = False                                                 # Partial class: Effort -1, min 1

class WwnEffortSource(BaseModel):
    model_config = {"extra": "forbid"}
    source: str                 # "high_mage" | "vowed" | "elementalist" ...
    governing_attr: str         # canonical WWN attr key, e.g. "WISDOM"
    relevant_skill: str         # e.g. "Magic"
    starting_skill_level: int   # chargen skill level for the Effort-max formula
```

- [ ] **Step 2: Write the failing chargen test** — `tests/game/test_wwn_chargen_seed.py`. Build a synthetic `WwnClassMagic` + `stats` and assert `seed_wwn_magic(...)` returns: an `EffortPool` per source with `max == effort_base + starting_skill_level + governing_attr_mod` (Partial: −1, min 1), and a `SpellcastingState` with `casts_per_day`/`max_spell_level`/prepared-capacity from the level tables. Mirror the construction idiom of an existing builder/seed test.

- [ ] **Step 3: Implement `seed_wwn_magic`** in `builder.py` as a module-level helper mirroring `seed_system_strain`:
```python
def seed_wwn_magic(rules, stats, class_str, class_def) -> tuple[dict[str, EffortPool], SpellcastingState | None]:
    """Seed WWN Effort pools + spellcasting state at chargen. Returns ({} , None)
    for non-wwn rulesets or non-magic classes (no silent partial state)."""
```
Effort-max uses `swn_attribute_modifier` (WWN shares the SWN curve) on the governing attr's flavor value; `max = rules.wwn.magic.effort_base + starting_skill_level + mod`, minus 1 (floor 1) when `partial`. Call it at the `build()` seam right after `system_strain = seed_system_strain(...)` (read the surrounding block; pass the resolved class def already in scope), and attach the results to the `CreatureCore`/`Character` constructor.

> **Executor note:** confirm where `effort`/`spellcasting` reach the `CreatureCore` — the builder constructs a `Character` then its core. Attach the seeded `effort` dict + `spellcasting` exactly as `system_strain` is attached. If `system_strain` is passed into the `Character(...)`/core constructor, do the same; mirror it precisely.

- [ ] **Step 4: Run, verify PASS. Commit:**
```bash
git add sidequest/genre/models/character.py sidequest/game/builder.py tests/game/test_wwn_chargen_seed.py
git commit -m "feat(chargen): WwnClassMagic + seed_wwn_magic (Effort pools + spellcasting state)"
```

---

## Task 8: Scene-end Effort reclaim hook

Wire the real scene-boundary reclaim (spec §H). Scene-end has a live seam (`Session.end_scene`, 3 production callsites). **Day/long-rest reclaim + casts refresh ships as a method (Task 4) but its lifecycle TRIGGER is deferred to Plan 3** (a rest action/beat doesn't fire in production yet — do NOT invent speculative rest infra here).

**Files:** Modify `sidequest/server/session.py`; create `tests/server/test_wwn_scene_reclaim.py`.

- [ ] **Step 1: Write the failing test.** Construct a session/snapshot whose bound ruleset is `wwn` and whose PC core has a `scene`-committed Effort point; call `Session.end_scene(...)`; assert the scene Effort was reclaimed (available restored) and a `day`/`maintained` commitment was left intact. Read how an existing `end_scene` test builds the session + how `clear_scratch_on_scene_end` is tested, and mirror that harness (do NOT fabricate a synthetic session shape).

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Wire the hook** in `Session.end_scene`, right after `clear_scratch_on_scene_end`: if the bound ruleset is `wwn`, for each PC core call `ruleset_module.reclaim_scene_effort(core, ...)`. Gate on the ruleset slug (mirror the `dice.py` `ruleset in (...)` gate Plan 1 added) so non-wwn sessions are untouched. Resolve the bound module via the registry (`get_ruleset_module(pack.rules.ruleset)`), as `dice.py` does.

- [ ] **Step 4: Run, verify PASS. Commit:**
```bash
git add sidequest/server/session.py tests/server/test_wwn_scene_reclaim.py
git commit -m "feat(session): reclaim scene-committed WWN Effort at end_scene (ruleset-gated)"
```

---

## Task 9: Full-suite gate + PR

- [ ] **Step 1: Lint/format/types**
```bash
uv run ruff format . && uv run ruff check . && \
uv run pyright sidequest/game/ruleset/wwn.py sidequest/game/wwn_magic.py \
  sidequest/genre/models/rules.py sidequest/genre/models/character.py \
  sidequest/game/creature_core.py sidequest/game/builder.py \
  sidequest/server/session.py sidequest/telemetry/spans/wwn.py
```
Expected clean (or only pre-existing findings unrelated to these files).

- [ ] **Step 2: Full suite vs baseline** (both env vars; Task 0 baseline is the yardstick — only a NEW failure is a regression):
```bash
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
uv run pytest -q
```
Expected: the new `test_wwn_*` tests pass; **no new failures** vs the Task 0 baseline.

- [ ] **Step 3: Open the PR**
```bash
env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-server -B develop \
  -t "feat(ruleset): WWN magic engine (Plan 2 of 3)" \
  -b "Plan 2 of 3 for WWN (docs/superpowers/plans/2026-05-29-wwn-magic-engine.md; spec amendment 2026-05-29 §A-§I). Faithful server-side WWN magic: per-source Effort commitment pools (maintained/scene/day), prepared-list + daily-casts spell economy, resolve_spellcast cast spine (defender save + caster-level damage, save-for-half), Killing Blow + Veteran's Luck (Fray Die struck as an SWN mis-import), chargen seeding, scene-end reclaim, and wwn.* magic spans. Unit-tested against synthetic fixtures. Content binding + cast_spell dispatch routing + day/rest trigger + end-to-end wiring = Plan 3 (cast spine is dead-in-dispatch until then, flagged like resolve_downed was in Plan 1)."
```

---

## Self-Review

**Spec coverage (this plan = amendment §B–§H, server lane):**
- §B Effort per-source commitment pools (maintained/scene/day, available=max−committed) → Tasks 2, 4 ✓
- §C/§D spell economy + cast spine (prepared/casts/max-level; defender save; caster-level damage save-for-half; Approach C) → Tasks 2, 5 ✓
- §E Killing Blow + Veteran's Luck (Fray Die struck) → Task 6 ✓
- §F/§skill-gap per-class magic data on the class def + chargen seeding (skill level authored on class) → Task 7 ✓
- §G `wwn.*` magic spans → Task 3 ✓ (auto-covered by routing-completeness via Plan 1's `__init__` re-export)
- §H scene reclaim wired (real seam); day/rest reclaim = method only, trigger deferred → Task 8 ✓ (deferral flagged)

**Correctly deferred to Plan 3 (absent here):** the `elemental_harmony` binding (rules/inventory/classes/char-creation), the `cast_spell` dispatch branch, the day/rest TRIGGER wiring, the full spell catalog, and end-to-end wiring tests against the real pack. **Dead-until-content (flagged):** `resolve_spellcast` + reclaim methods are unit-tested but unreachable from production dispatch until Plan 3 — same posture as `resolve_downed` in Plan 1.

**Wiring-test discipline:** Task 3 rides `test_routing_completeness`; Task 8 wires + tests a real lifecycle seam; chargen seeding (Task 7) has a unit test. Full end-to-end wiring (dispatch routing, chargen against the real pack) is the explicit Plan 3 mandate per spec §7.

**Type consistency:** `MagicConfig` (Task 1) ← `WwnConfig.magic`, read by `apply_killing_blow`/`reclaim_day_and_refresh`. `EffortPool`/`SpellcastingState`/`CastInput` (Task 2/5) ← `CreatureCore` fields, the module methods, and all tests. Span helper names `wwn_*_span` (Task 3) ← imports in `wwn.py` (Tasks 4–6). `WwnClassMagic` (Task 7) ← `seed_wwn_magic`.

**Known risks:** (1) per-character skill registry doesn't exist — Effort-max skill level is authored on the class (Task 7), full skill system deferred. (2) day/rest trigger infra doesn't exist — Plan 2 ships the method, Plan 3 fires it. Both are spec-amendment-acknowledged, not surprises.
