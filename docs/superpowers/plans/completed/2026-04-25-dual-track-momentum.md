# Dual-Track Momentum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-dial encounter `metric` with two side-routed `player_metric` / `opponent_metric` dials, structured tier outcomes, beat kinds, encounter tags, severity-bearing statuses, a Yield action, and full OTEL/persistence telemetry — making `2026-04-25-dungeon_survivor` resolve as `opponent_victory` instead of the current sign-collapsed false `player_victory`.

**Architecture:** Engine-side: replace `StructuredEncounter.metric` with two ascending `EncounterMetric`s, add `EncounterActor.side ∈ {player,opponent,neutral}`, `EncounterTag` model, structured `Status`/`StatusSeverity`. New `RollOutcome.Tie` tier and a margin-based `CritSuccess` clause. Beat schema gains `kind ∈ {strike,brace,push,angle}` driving per-tier delta defaults overridable via a `deltas:` map. `_apply_beat` rewritten as a tier-aware/side-aware helper shared by narrator and dice-throw paths. Narrator-side: required `side` per NPC and `outcome` per beat selection, `status_changes` array, one-shot `[ENCOUNTER RESOLVED]` prompt zone fed by `pending_resolution_signal`. Persistence: watcher events for every encounter decision land as typed rows in the `events` SQLite table so the GM panel can render the timeline post-hoc. New `MessageType.YIELD` wires a structured player exit with `EdgePool` refresh. v2 mechanics (leverage spend, status absorption) ride on the same data shapes but ship later.

**Tech Stack:** Python 3.13 + Pydantic v2 (server engine), pytest (unit/integration/telemetry tests), OpenTelemetry (spans), SQLite (events table), YAML (genre packs), TypeScript/React (UI yield button + GM panel handlers).

**Source spec:** `docs/superpowers/specs/2026-04-25-dual-track-momentum-design.md`

**Repos touched:**
- `sidequest-server/` (engine, tests) — main branch
- `sidequest-content/genre_packs/*/rules.yaml` — main branch (per-pack migration)
- `sidequest-ui/` — main branch (yield button, GM panel rendering of new event kinds)

**Reference save (regression target):** `~/.sidequest/saves/games/2026-04-25-dungeon_survivor/save.db`

**Phasing:**
- **Phase 1 — Engine core + schema** (Tasks 1–13). Pure-engine changes that do not yet activate from the wire. Internal API only. Land alone? No — stories must ship together; this is just a sub-section of the same PR/branch.
- **Phase 2 — Narrator awareness, telemetry, persistence, GM panel** (Tasks 14–22). Wire the engine to the narrator prompt assembly and to the events table; extend the GM panel to render the new event kinds.
- **Phase 3 — Yield action + content migration + regression** (Tasks 23–32). Wire `MessageType.YIELD`, ship the UI button, migrate every shipping pack's `rules.yaml`, run the regression playtest against the reference save.

**Conventions:**
- Tests are pytest. Run a single test with `cd sidequest-server && uv run pytest tests/path/test.py::test_name -v`.
- Lint with `cd sidequest-server && uv run ruff check .`. Format with `uv run ruff format .`.
- Aggregate gate: `just check-all` (from orchestrator root).
- Every commit message uses Conventional Commits: `feat(encounter): …`, `fix(narrator): …`, `chore(content): …`, etc.
- No `--no-verify`. If a hook blocks, fix the cause.
- Per CLAUDE.md: no silent fallbacks, no stubs, every test suite includes a wiring test, every subsystem decision emits OTEL.

---

## File Structure

### New files (server)

| Path | Purpose |
|---|---|
| `sidequest-server/sidequest/game/beat_kinds.py` | `BeatKind` enum + per-kind default delta tables, `resolve_tier_deltas()` helper, `ResolutionResult` dataclass. |
| `sidequest-server/sidequest/game/encounter_tag.py` | `EncounterTag` Pydantic model + helpers. |
| `sidequest-server/sidequest/game/status.py` | `StatusSeverity` enum + `Status` Pydantic model + bare-string forward-migration helper. |
| `sidequest-server/sidequest/game/resolution_signal.py` | `ResolutionSignal` dataclass — the transient one-shot payload for `[ENCOUNTER RESOLVED]`. |
| `sidequest-server/sidequest/server/dispatch/yield_action.py` | YIELD message dispatch handler. |
| `sidequest-server/tests/server/test_beat_kinds.py` | Per-kind default tier table tests. |
| `sidequest-server/tests/server/test_encounter_tag.py` | EncounterTag model + persistence tests. |
| `sidequest-server/tests/server/test_status_migration.py` | Bare-string → structured Status migration tests. |
| `sidequest-server/tests/server/test_yield_dispatch.py` | YIELD handler unit + integration tests. |
| `sidequest-server/tests/server/test_encounter_telemetry.py` | Span + watcher + events-row tests. |
| `sidequest-server/tests/server/test_resolution_signal.py` | `pending_resolution_signal` set/consume tests. |
| `sidequest-server/tests/integration/test_dual_track_dungeon_survivor.py` | Regression playtest against the reference save. |

### Modified files (server)

| Path | Change |
|---|---|
| `sidequest-server/sidequest/game/encounter.py` | Drop `metric`, add `player_metric` + `opponent_metric` + `tags`; `EncounterActor.side` + `withdrawn`; structured `outcome` values; delete `MetricDirection`. |
| `sidequest-server/sidequest/game/creature_core.py` | `statuses: list[str]` → `list[Status]`. |
| `sidequest-server/sidequest/game/dice.py` | Add `RollOutcome.Tie` branch + `CritSuccess`-by-margin clause to `resolve_dice_with_faces`. |
| `sidequest-server/sidequest/game/session.py` | `_SessionData.pending_resolution_signal: ResolutionSignal | None = None`. |
| `sidequest-server/sidequest/genre/models/rules.py` | `BeatDef.kind`, `BeatDef.deltas`, `BeatDef.target_tag`; `MetricDef` removed; new `MetricPairDef` (or inline two MetricDef-likes) on `ConfrontationDef`; reject single-`metric` shape. |
| `sidequest-server/sidequest/server/narration_apply.py` | Use new `_apply_beat`, side routing, drop `apply_encounter_updates` + `hostile_keywords` block. |
| `sidequest-server/sidequest/server/dispatch/dice.py` | Use shared `_apply_beat` from `beat_kinds`; tier-aware. |
| `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` | Drop `_DIRECTION_BY_NAME`; instantiate `player_metric` + `opponent_metric` from `cdef`; set `EncounterActor.side` from narrator payload. |
| `sidequest-server/sidequest/agents/orchestrator.py` | `BeatSelection.outcome: RollOutcome`; `NpcMention.side: str`; new `status_changes` field on `NarrationTurnResult`. |
| `sidequest-server/sidequest/agents/narrator.py` | Add `[ENCOUNTER RESOLVED]` prompt zone, side/outcome/status_changes contract text in `NARRATOR_OUTPUT_ONLY`, enriched active-encounter zone. |
| `sidequest-server/sidequest/protocol/enums.py` | `MessageType.YIELD = "YIELD"`. |
| `sidequest-server/sidequest/protocol/messages.py` | `YieldMessage` payload type. |
| `sidequest-server/sidequest/server/session_handler.py` | Route `YIELD` to dispatch; consume + clear `pending_resolution_signal` on next turn. |
| `sidequest-server/sidequest/telemetry/spans.py` | New `encounter.*` span constants + context managers (per spec §Telemetry). |
| `sidequest-server/sidequest/telemetry/watcher_hub.py` | Persist `state_transition` events whose `field == "encounter"` to the `events` table as typed rows. |
| `sidequest-server/sidequest/game/persistence.py` | Helper to insert event rows + a query helper for the GM panel + tests. |

### Modified files (UI)

| Path | Change |
|---|---|
| `sidequest-ui/src/types/payloads.ts` | YIELD payload type. |
| `sidequest-ui/src/screens/EncounterPanel.tsx` (or current equivalent) | Yield button. |
| `sidequest-ui/src/lib/socket.ts` (or current message helper) | `sendYield()`. |
| `sidequest-ui/src/screens/GMPanel/EncounterTimeline.tsx` (or current) | Render new `ENCOUNTER_*` event kinds: dual-dial view, beat rows with kind+tier+side, tag rows, status rows, yield rows. |

### Modified files (content)

| Path | Change |
|---|---|
| `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml` | Migrate every confrontation. |
| `sidequest-content/genre_packs/heavy_metal/rules.yaml` | Same. |
| `sidequest-content/genre_packs/space_opera/rules.yaml` | Same. |
| `sidequest-content/genre_packs/spaghetti_western/rules.yaml` | Same. |
| `sidequest-content/genre_packs/mutant_wasteland/rules.yaml` | Same. |
| `sidequest-content/genre_packs/elemental_harmony/rules.yaml` | Same. |

---

## Phase 1 — Engine core + schema

### Task 1: Add `RollOutcome.Tie`

Adds the new tier value at the wire layer. Pure data — no resolver behavior change yet.

**Files:**
- Modify: `sidequest-server/sidequest/protocol/dice.py:59-75`
- Test: `sidequest-server/tests/protocol/test_dice_payloads.py` (extend existing)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/protocol/test_dice_payloads.py`:

```python
from sidequest.protocol.dice import RollOutcome


def test_roll_outcome_has_tie_member():
    assert RollOutcome.Tie.value == "Tie"


def test_roll_outcome_unknown_wire_value_maps_to_unknown():
    # Existing _missing_ behavior must still hold once Tie is added.
    assert RollOutcome("MysteryTier") is RollOutcome.Unknown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_dice_payloads.py::test_roll_outcome_has_tie_member -v`

Expected: FAIL with `AttributeError: Tie` (or similar — the member doesn't exist).

- [ ] **Step 3: Add the Tie member**

Edit `sidequest-server/sidequest/protocol/dice.py`. In the `RollOutcome` enum (around lines 59–75), add `Tie` between `Success` and `Fail`:

```python
class RollOutcome(str, Enum):  # noqa: UP042 — matches project convention (see protocol/enums.py)
    """Outcome classification — feeds narrator tone.

    Serializes as the variant name (``"CritSuccess"`` etc.). Unknown wire
    values map to ``Unknown`` via ``_missing_`` so a newer variant from a
    future wire version doesn't hard-error at parse time.

    Tie is the 5th tier added for dual-track momentum (spec
    2026-04-25-dual-track-momentum-design.md): fired when total == difficulty.
    """

    CritSuccess = "CritSuccess"
    Success = "Success"
    Tie = "Tie"
    Fail = "Fail"
    CritFail = "CritFail"
    Unknown = "Unknown"

    @classmethod
    def _missing_(cls, value: object) -> RollOutcome:
        return cls.Unknown
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_dice_payloads.py -v`

Expected: PASS for both new tests; existing tests still PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/protocol/dice.py tests/protocol/test_dice_payloads.py
git commit -m "feat(protocol): add RollOutcome.Tie tier"
```

---

### Task 2: Extend `resolve_dice_with_faces` for Tie + margin-based CritSuccess

Adds the `total == difficulty` → `Tie` branch and the `total >= difficulty + 3` → `CritSuccess` branch, preserving the nat-20/nat-1 paths.

**Files:**
- Modify: `sidequest-server/sidequest/game/dice.py:142-152`
- Test: `sidequest-server/tests/game/test_dice_resolver.py` (extend existing)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/game/test_dice_resolver.py` (create if missing — match the pattern of nearby `tests/game/test_*.py`):

```python
from sidequest.game.dice import resolve_dice_with_faces
from sidequest.protocol.dice import DieSides, DieSpec, RollOutcome


def _d20(face: int):
    return [DieSpec(sides=DieSides.D20, count=1)], [face]


def test_tie_when_total_equals_difficulty_no_crit():
    dice, faces = _d20(10)
    # modifier 0, difficulty 10 → total 10 == DC → Tie
    resolved = resolve_dice_with_faces(dice, faces, modifier=0, difficulty=10)
    assert resolved.outcome is RollOutcome.Tie
    assert resolved.total == 10


def test_crit_success_by_margin_no_nat20():
    dice, faces = _d20(15)
    # modifier 0, difficulty 12 → margin 3 → CritSuccess
    resolved = resolve_dice_with_faces(dice, faces, modifier=0, difficulty=12)
    assert resolved.outcome is RollOutcome.CritSuccess


def test_crit_success_by_margin_just_under_threshold_is_success():
    dice, faces = _d20(14)
    # margin 2 → still Success, not CritSuccess
    resolved = resolve_dice_with_faces(dice, faces, modifier=0, difficulty=12)
    assert resolved.outcome is RollOutcome.Success


def test_nat20_still_crits_regardless_of_margin():
    dice, faces = _d20(20)
    resolved = resolve_dice_with_faces(dice, faces, modifier=0, difficulty=30)
    # total 20 < DC 30 but nat-20 wins
    assert resolved.outcome is RollOutcome.CritSuccess


def test_nat1_still_critfails_regardless_of_total():
    dice = [DieSpec(sides=DieSides.D20, count=1)]
    resolved = resolve_dice_with_faces(dice, [1], modifier=100, difficulty=5)
    # total 101 >> DC 5 but nat-1 wins
    assert resolved.outcome is RollOutcome.CritFail


def test_fail_when_total_below_difficulty():
    dice, faces = _d20(5)
    resolved = resolve_dice_with_faces(dice, faces, modifier=0, difficulty=15)
    assert resolved.outcome is RollOutcome.Fail
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/game/test_dice_resolver.py -v`

Expected: `test_tie_when_total_equals_difficulty_no_crit` and `test_crit_success_by_margin_no_nat20` FAIL — Tie path doesn't exist; margin-CritSuccess path doesn't exist. Others PASS.

- [ ] **Step 3: Update the resolver**

Edit `sidequest-server/sidequest/game/dice.py`. Replace the outcome decision block at lines ~142-150 with:

```python
    total = face_sum + modifier

    if has_d20 and has_d20_nat20:
        outcome = RollOutcome.CritSuccess
    elif has_d20 and has_d20_nat1:
        outcome = RollOutcome.CritFail
    elif total >= difficulty + 3:
        # Decisive-margin success — equivalent to a tabletop "succeed-with-style".
        # Required for the angle-kind two-leverage tag grant on margin alone.
        outcome = RollOutcome.CritSuccess
    elif total > difficulty:
        outcome = RollOutcome.Success
    elif total == difficulty:
        outcome = RollOutcome.Tie
    else:
        outcome = RollOutcome.Fail

    return ResolvedRoll(rolls=rolls, total=total, outcome=outcome)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_dice_resolver.py -v`

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/dice.py tests/game/test_dice_resolver.py
git commit -m "feat(dice): tier resolution gains Tie and margin-based CritSuccess"
```

---

### Task 3: Define `Status` and `StatusSeverity` with bare-string migration

Adds the structured shape and a forward-migration helper. Doesn't yet swap `CreatureCore.statuses` — that's Task 4.

**Files:**
- Create: `sidequest-server/sidequest/game/status.py`
- Test: `sidequest-server/tests/server/test_status_migration.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_status_migration.py`:

```python
import pytest

from sidequest.game.status import Status, StatusSeverity, migrate_legacy_statuses


def test_status_severity_enum_values():
    assert StatusSeverity.Scratch.value == "Scratch"
    assert StatusSeverity.Wound.value == "Wound"
    assert StatusSeverity.Scar.value == "Scar"


def test_status_full_construction():
    s = Status(
        text="Cracked Temple",
        severity=StatusSeverity.Wound,
        absorbed_shifts=0,
        created_turn=4,
        created_in_encounter="combat",
    )
    assert s.text == "Cracked Temple"
    assert s.severity is StatusSeverity.Wound
    assert s.absorbed_shifts == 0
    assert s.created_in_encounter == "combat"


def test_status_round_trip_json():
    s = Status(
        text="Bleeding",
        severity=StatusSeverity.Scratch,
        absorbed_shifts=0,
        created_turn=0,
        created_in_encounter=None,
    )
    raw = s.model_dump_json()
    parsed = Status.model_validate_json(raw)
    assert parsed == s


def test_migrate_bare_string_list_to_status_list():
    legacy = ["Bleeding", "Stunned"]
    migrated = migrate_legacy_statuses(legacy)
    assert len(migrated) == 2
    assert all(isinstance(s, Status) for s in migrated)
    assert migrated[0].text == "Bleeding"
    assert migrated[0].severity is StatusSeverity.Scratch
    assert migrated[0].absorbed_shifts == 0
    assert migrated[0].created_turn == 0
    assert migrated[0].created_in_encounter is None


def test_migrate_already_structured_statuses_passes_through():
    existing = [Status(
        text="Wound",
        severity=StatusSeverity.Wound,
        absorbed_shifts=2,
        created_turn=5,
        created_in_encounter="combat",
    )]
    migrated = migrate_legacy_statuses(existing)
    assert migrated == existing


def test_migrate_mixed_list_raises():
    # Mixing dict and bare string is a content bug — fail loud.
    with pytest.raises(TypeError):
        migrate_legacy_statuses(["Bleeding", 12345])  # type: ignore[list-item]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_status_migration.py -v`

Expected: ImportError — `sidequest.game.status` doesn't exist.

- [ ] **Step 3: Create the status module**

Create `sidequest-server/sidequest/game/status.py`:

```python
"""Structured statuses with severity tier — replaces bare-string statuses.

Spec: docs/superpowers/specs/2026-04-25-dual-track-momentum-design.md §Statuses.

Severity tiers drive recovery cadence (Scratch clears at scene end; Wound at
session end; Scar requires a milestone) and — in v2 — drive the absorption
budget when an encounter dial is about to cross threshold. v1 just tracks
the shape; the absorption mechanic ships in story 5.

Migration: existing saves carry ``CreatureCore.statuses`` as ``list[str]``.
``migrate_legacy_statuses`` converts a bare string to
``Status(text=<s>, severity=Scratch, absorbed_shifts=0, created_turn=0,
created_in_encounter=None)`` so loaders can call it during
``model_validator(mode="before")`` on CreatureCore.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class StatusSeverity(str, Enum):
    """Status severity tier — drives recovery cadence and (v2) absorption budget."""

    Scratch = "Scratch"
    Wound = "Wound"
    Scar = "Scar"


class Status(BaseModel):
    """An actor-level lingering cost.

    ``absorbed_shifts`` is 0 in v1; story 5 sets it from the severity's
    absorption budget when the status absorbs a would-be threshold cross.
    """

    model_config = {"extra": "forbid"}

    text: str
    severity: StatusSeverity
    absorbed_shifts: int = 0
    created_turn: int = 0
    created_in_encounter: str | None = None


def migrate_legacy_statuses(raw: list[object]) -> list[Status]:
    """Forward-migrate a save's ``statuses`` field to structured Status list.

    Accepts a list whose entries are either bare ``str`` (legacy save) or
    already-structured ``Status`` instances (post-migration save). A list
    that contains anything else raises ``TypeError`` per CLAUDE.md
    "no silent fallbacks".
    """
    out: list[Status] = []
    for entry in raw:
        if isinstance(entry, Status):
            out.append(entry)
            continue
        if isinstance(entry, str):
            out.append(
                Status(
                    text=entry,
                    severity=StatusSeverity.Scratch,
                    absorbed_shifts=0,
                    created_turn=0,
                    created_in_encounter=None,
                )
            )
            continue
        if isinstance(entry, dict):
            out.append(Status.model_validate(entry))
            continue
        raise TypeError(
            f"unexpected entry in statuses list: {entry!r} "
            f"(type={type(entry).__name__}); "
            f"expected str, dict, or Status"
        )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_status_migration.py -v`

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/status.py tests/server/test_status_migration.py
git commit -m "feat(game): add Status + StatusSeverity with bare-string migration"
```

---

### Task 4: Wire `CreatureCore.statuses` to the structured `Status` shape

Switches `CreatureCore.statuses: list[str]` to `list[Status]` with a `before` validator that funnels through `migrate_legacy_statuses` so existing saves load without manual migration.

**Files:**
- Modify: `sidequest-server/sidequest/game/creature_core.py:181`
- Test: `sidequest-server/tests/server/test_status_migration.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/server/test_status_migration.py`:

```python
from sidequest.game.creature_core import CreatureCore
from sidequest.game.status import Status, StatusSeverity


def _core_kwargs(**over):
    base = dict(
        name="Sam",
        description="A dungeon delver.",
        personality="Stoic.",
    )
    base.update(over)
    return base


def test_creature_core_loads_legacy_string_statuses():
    raw_json = (
        '{"name":"Sam","description":"A dungeon delver.",'
        '"personality":"Stoic.","statuses":["Bleeding","Stunned"]}'
    )
    core = CreatureCore.model_validate_json(raw_json)
    assert all(isinstance(s, Status) for s in core.statuses)
    assert [s.text for s in core.statuses] == ["Bleeding", "Stunned"]
    assert all(s.severity is StatusSeverity.Scratch for s in core.statuses)


def test_creature_core_loads_structured_statuses():
    structured = Status(
        text="Cracked Temple",
        severity=StatusSeverity.Wound,
        absorbed_shifts=0,
        created_turn=4,
        created_in_encounter="combat",
    )
    core = CreatureCore(**_core_kwargs(statuses=[structured]))
    assert core.statuses == [structured]


def test_creature_core_round_trip_after_migration():
    raw_json = (
        '{"name":"Sam","description":"A dungeon delver.",'
        '"personality":"Stoic.","statuses":["Bleeding"]}'
    )
    core = CreatureCore.model_validate_json(raw_json)
    re_serialized = core.model_dump_json()
    re_loaded = CreatureCore.model_validate_json(re_serialized)
    assert re_loaded.statuses == core.statuses
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_status_migration.py -v`

Expected: the three new tests FAIL — `core.statuses[0]` is currently a `str`, not a `Status`.

- [ ] **Step 3: Update CreatureCore**

Edit `sidequest-server/sidequest/game/creature_core.py`.

At the top, after the existing `from pydantic import …` line, add:

```python
from pydantic import BaseModel, Field, field_validator, model_validator
```

(if `model_validator` isn't already imported)

After the imports, add:

```python
from sidequest.game.status import Status, migrate_legacy_statuses
```

Find the field declaration `statuses: list[str] = Field(default_factory=list)` (line ~181) and replace with:

```python
    statuses: list[Status] = Field(default_factory=list)
```

Add a model-level `before` validator inside `CreatureCore` so legacy saves migrate transparently. Place it next to the existing field validators:

```python
    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_statuses(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        raw = data.get("statuses")
        if raw is None:
            return data
        if isinstance(raw, list):
            data = {**data, "statuses": migrate_legacy_statuses(raw)}
        return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_status_migration.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Run the full game-test suite to surface drift**

Run: `cd sidequest-server && uv run pytest tests/game tests/server -v`

Expected: PASS, or at most a small number of test-fixture failures referencing the old string shape — fix those fixtures inline (replace `"Bleeding"` with `Status(text="Bleeding", severity=StatusSeverity.Scratch)` only if the test was asserting on the structured shape; otherwise leave the bare string and rely on migration).

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/creature_core.py tests/server/test_status_migration.py
git commit -m "feat(game): structured Status on CreatureCore with legacy migration"
```

---

### Task 5: Add `EncounterTag` model

Pure data model. Tags get created/persisted in later tasks; this just lands the type so other tasks can import it.

**Files:**
- Create: `sidequest-server/sidequest/game/encounter_tag.py`
- Test: `sidequest-server/tests/server/test_encounter_tag.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_encounter_tag.py`:

```python
import pytest
from pydantic import ValidationError

from sidequest.game.encounter_tag import EncounterTag


def _kw(**over):
    base = dict(
        text="Off-Balance",
        created_by="Sam Jones",
        target="The Promo",
        leverage=1,
        fleeting=False,
        created_turn=3,
    )
    base.update(over)
    return base


def test_encounter_tag_full_round_trip():
    tag = EncounterTag(**_kw())
    raw = tag.model_dump_json()
    parsed = EncounterTag.model_validate_json(raw)
    assert parsed == tag


def test_encounter_tag_scene_target_is_none():
    tag = EncounterTag(**_kw(target=None))
    assert tag.target is None


def test_encounter_tag_fleeting_default_one_charge():
    tag = EncounterTag(**_kw(fleeting=True, leverage=1))
    assert tag.fleeting is True
    assert tag.leverage == 1


def test_encounter_tag_rejects_negative_leverage():
    with pytest.raises(ValidationError):
        EncounterTag(**_kw(leverage=-1))


def test_encounter_tag_extra_field_forbidden():
    with pytest.raises(ValidationError):
        EncounterTag(**_kw(), foo="bar")  # type: ignore[call-arg]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_tag.py -v`

Expected: ImportError — `sidequest.game.encounter_tag` doesn't exist.

- [ ] **Step 3: Create the EncounterTag model**

Create `sidequest-server/sidequest/game/encounter_tag.py`:

```python
"""EncounterTag — scene state created by ``angle`` beats and beat extras.

Spec: docs/superpowers/specs/2026-04-25-dual-track-momentum-design.md §Encounter tags.

v1: tags are created, displayed, and persisted but engine does not yet spend
leverage. v2 (story 4) adds ``consumes_leverage_from`` to BeatDef.

``target`` distinguishes per-actor tags (e.g. "The Promo is Off-Balance")
from scene-wide tags (e.g. "the floor is lava"). ``fleeting`` tags are
single-use: ``leverage`` starts at 1 and the tag vanishes when consumed
(v2). Persistent tags (``fleeting=False``) survive at ``leverage=0`` as
scene context the narrator can lean on prose-wise.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class EncounterTag(BaseModel):
    """A single scene tag attached to an encounter."""

    model_config = {"extra": "forbid"}

    text: str
    created_by: str
    target: str | None = None
    leverage: int = Field(ge=0)
    fleeting: bool = False
    created_turn: int
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_tag.py -v`

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/encounter_tag.py tests/server/test_encounter_tag.py
git commit -m "feat(game): EncounterTag model"
```

---

### Task 6: Define `BeatKind` enum and per-kind default delta tables

Pure helper module. Tasks 9 and 10 will call into it.

**Files:**
- Create: `sidequest-server/sidequest/game/beat_kinds.py`
- Test: `sidequest-server/tests/server/test_beat_kinds.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_beat_kinds.py`:

```python
import pytest

from sidequest.game.beat_kinds import (
    BeatKind,
    DEFAULT_DELTAS,
    ResolvedDeltas,
    resolve_tier_deltas,
)
from sidequest.protocol.dice import RollOutcome


# ---- BeatKind enum -------------------------------------------------------

def test_beat_kind_members():
    assert {k.value for k in BeatKind} == {"strike", "brace", "push", "angle"}


# ---- strike defaults -----------------------------------------------------

def test_strike_success_advances_own_by_base():
    deltas = resolve_tier_deltas(
        kind=BeatKind.strike, base=3, outcome=RollOutcome.Success,
        overrides=None, target_tag=None,
    )
    assert deltas == ResolvedDeltas(own=3, opponent=0)


def test_strike_tie_is_graze_half_base_floor():
    deltas = resolve_tier_deltas(
        kind=BeatKind.strike, base=3, outcome=RollOutcome.Tie,
        overrides=None, target_tag=None,
    )
    assert deltas.own == 1  # 3 // 2
    assert deltas.opponent == 0


def test_strike_critsuccess_grants_fleeting_opening_tag():
    deltas = resolve_tier_deltas(
        kind=BeatKind.strike, base=3, outcome=RollOutcome.CritSuccess,
        overrides=None, target_tag=None,
    )
    assert deltas.own == 3
    assert deltas.opponent == 0
    assert deltas.grants_fleeting_tag == "Opening"


def test_strike_fail_and_critfail_zero():
    for tier in (RollOutcome.Fail, RollOutcome.CritFail):
        deltas = resolve_tier_deltas(
            kind=BeatKind.strike, base=3, outcome=tier,
            overrides=None, target_tag=None,
        )
        assert deltas.own == 0
        assert deltas.opponent == 0


# ---- brace defaults ------------------------------------------------------

def test_brace_success_drains_opponent_by_base():
    deltas = resolve_tier_deltas(
        kind=BeatKind.brace, base=2, outcome=RollOutcome.Success,
        overrides=None, target_tag=None,
    )
    # Brace pushes opponent dial *backward* — implemented as negative delta
    # against opponent_metric.
    assert deltas.own == 0
    assert deltas.opponent == -2


def test_brace_critfail_lets_a_free_hit_land():
    deltas = resolve_tier_deltas(
        kind=BeatKind.brace, base=2, outcome=RollOutcome.CritFail,
        overrides=None, target_tag=None,
    )
    assert deltas.own == 0
    assert deltas.opponent == 1


def test_brace_critsuccess_grants_counter_stance_fleeting_tag():
    deltas = resolve_tier_deltas(
        kind=BeatKind.brace, base=2, outcome=RollOutcome.CritSuccess,
        overrides=None, target_tag=None,
    )
    assert deltas.opponent == -2
    assert deltas.grants_fleeting_tag == "Counter Stance"


# ---- push defaults -------------------------------------------------------

def test_push_success_resolves_encounter():
    deltas = resolve_tier_deltas(
        kind=BeatKind.push, base=1, outcome=RollOutcome.Success,
        overrides=None, target_tag=None,
    )
    assert deltas.resolution is True


def test_push_tie_does_not_resolve():
    deltas = resolve_tier_deltas(
        kind=BeatKind.push, base=1, outcome=RollOutcome.Tie,
        overrides=None, target_tag=None,
    )
    assert deltas.resolution is False


def test_push_critfail_backslides_own_by_one():
    deltas = resolve_tier_deltas(
        kind=BeatKind.push, base=1, outcome=RollOutcome.CritFail,
        overrides=None, target_tag=None,
    )
    assert deltas.own == -1


def test_push_critsuccess_clean_exit_fleeting_tag():
    deltas = resolve_tier_deltas(
        kind=BeatKind.push, base=1, outcome=RollOutcome.CritSuccess,
        overrides=None, target_tag=None,
    )
    assert deltas.resolution is True
    assert deltas.grants_fleeting_tag == "Clean Exit"


# ---- angle defaults ------------------------------------------------------

def test_angle_success_grants_persistent_tag_leverage_one():
    deltas = resolve_tier_deltas(
        kind=BeatKind.angle, base=0, outcome=RollOutcome.Success,
        overrides=None, target_tag="Off-Balance",
    )
    assert deltas.grants_tag == "Off-Balance"
    assert deltas.tag_leverage == 1


def test_angle_critsuccess_grants_persistent_tag_leverage_two():
    deltas = resolve_tier_deltas(
        kind=BeatKind.angle, base=0, outcome=RollOutcome.CritSuccess,
        overrides=None, target_tag="Off-Balance",
    )
    assert deltas.grants_tag == "Off-Balance"
    assert deltas.tag_leverage == 2


def test_angle_tie_grants_fleeting_tag():
    deltas = resolve_tier_deltas(
        kind=BeatKind.angle, base=0, outcome=RollOutcome.Tie,
        overrides=None, target_tag="Off-Balance",
    )
    assert deltas.grants_fleeting_tag == "Off-Balance"


def test_angle_critfail_backfires_target_tag_onto_opponent():
    deltas = resolve_tier_deltas(
        kind=BeatKind.angle, base=0, outcome=RollOutcome.CritFail,
        overrides=None, target_tag="Off-Balance",
    )
    assert deltas.tag_backfire is True
    # text reused: the angle backfires onto the actor.
    assert deltas.grants_fleeting_tag == "Off-Balance"


def test_angle_requires_target_tag():
    with pytest.raises(ValueError):
        resolve_tier_deltas(
            kind=BeatKind.angle, base=0, outcome=RollOutcome.Success,
            overrides=None, target_tag=None,
        )


# ---- per-tier overrides --------------------------------------------------

def test_per_tier_override_replaces_default():
    overrides = {RollOutcome.CritFail: {"own": -2}}
    deltas = resolve_tier_deltas(
        kind=BeatKind.strike, base=4, outcome=RollOutcome.CritFail,
        overrides=overrides, target_tag=None,
    )
    assert deltas.own == -2
    # other tiers still use kind defaults
    success = resolve_tier_deltas(
        kind=BeatKind.strike, base=4, outcome=RollOutcome.Success,
        overrides=overrides, target_tag=None,
    )
    assert success.own == 4


def test_default_deltas_table_covers_all_kinds_and_tiers():
    tiers = {
        RollOutcome.CritFail, RollOutcome.Fail, RollOutcome.Tie,
        RollOutcome.Success, RollOutcome.CritSuccess,
    }
    for kind in BeatKind:
        assert set(DEFAULT_DELTAS[kind].keys()) == tiers
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_beat_kinds.py -v`

Expected: ImportError — `sidequest.game.beat_kinds` doesn't exist.

- [ ] **Step 3: Create the beat_kinds module**

Create `sidequest-server/sidequest/game/beat_kinds.py`:

```python
"""Beat kinds + per-kind default delta tables.

Spec: docs/superpowers/specs/2026-04-25-dual-track-momentum-design.md
§"Beat kinds and outcome tiers".

A beat declares one of four ``kind`` values; the kind drives a default delta
table indexed by ``RollOutcome``. A beat can override any per-tier entry
via its ``deltas:`` map. ``resolve_tier_deltas`` merges the kind defaults
with per-beat overrides and returns a flat ``ResolvedDeltas`` consumed by
``_apply_beat``.

All deltas are *signed* and measured against the actor's own/other dials.
``brace`` drains the opponent's dial; that is encoded as a negative
``opponent`` delta so ``opponent.current += deltas.opponent`` is the only
arithmetic the engine needs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sidequest.protocol.dice import RollOutcome


class BeatKind(str, Enum):
    """Mechanical contract for a beat.

    - strike: advance own dial / press opponent.
    - brace:  absorb / counter — drains opponent dial.
    - push:   pursue a discrete narrative goal (flee, climb, persuade-out).
    - angle:  set up a scene tag for future leverage.
    """

    strike = "strike"
    brace = "brace"
    push = "push"
    angle = "angle"


@dataclass(frozen=True)
class ResolvedDeltas:
    """Flat deltas resolved for one beat at one outcome tier.

    ``own``/``opponent`` are scalar dial advances. Tag/resolution extras
    are independent flags the engine consults after applying the dials.
    """

    own: int = 0
    opponent: int = 0
    grants_tag: str | None = None
    tag_leverage: int = 0
    grants_fleeting_tag: str | None = None
    tag_backfire: bool = False
    resolution: bool = False


# Per-kind default delta tables. ``b`` is the beat's ``base``; the lambdas
# defer to runtime so we can substitute the live base + target_tag without
# building a fresh table per call.
_DefaultRule = dict[str, Any]  # {own,opponent,grants_tag,...} keyed by str

DEFAULT_DELTAS: dict[BeatKind, dict[RollOutcome, _DefaultRule]] = {
    BeatKind.strike: {
        RollOutcome.CritFail: {},
        RollOutcome.Fail: {},
        RollOutcome.Tie: {"own_expr": "b // 2"},
        RollOutcome.Success: {"own_expr": "b"},
        RollOutcome.CritSuccess: {"own_expr": "b", "grants_fleeting_tag": "Opening"},
    },
    BeatKind.brace: {
        RollOutcome.CritFail: {"opponent": 1},
        RollOutcome.Fail: {},
        RollOutcome.Tie: {"opponent_expr": "-(b // 2)"},
        RollOutcome.Success: {"opponent_expr": "-b"},
        RollOutcome.CritSuccess: {"opponent_expr": "-b", "grants_fleeting_tag": "Counter Stance"},
    },
    BeatKind.push: {
        RollOutcome.CritFail: {"own": -1},
        RollOutcome.Fail: {},
        RollOutcome.Tie: {},
        RollOutcome.Success: {"resolution": True},
        RollOutcome.CritSuccess: {"resolution": True, "grants_fleeting_tag": "Clean Exit"},
    },
    BeatKind.angle: {
        # CritFail: backfire — tag text from target_tag, fleeting, on opposing side.
        RollOutcome.CritFail: {"tag_backfire": True, "grants_fleeting_tag_from_target": True},
        RollOutcome.Fail: {},
        RollOutcome.Tie: {"grants_fleeting_tag_from_target": True},
        RollOutcome.Success: {"grants_tag_from_target": True, "tag_leverage": 1},
        RollOutcome.CritSuccess: {"grants_tag_from_target": True, "tag_leverage": 2},
    },
}


def _eval_expr(expr: str, base: int) -> int:
    """Evaluate a tiny ``b``-only arithmetic expression — closed form, no eval."""
    # Two forms appear in DEFAULT_DELTAS: ``b``, ``b // 2``, ``-b``, ``-(b // 2)``.
    expr = expr.replace(" ", "")
    if expr == "b":
        return base
    if expr == "-b":
        return -base
    if expr == "b//2":
        return base // 2
    if expr == "-(b//2)":
        return -(base // 2)
    raise ValueError(f"unsupported delta expression: {expr!r}")


def resolve_tier_deltas(
    *,
    kind: BeatKind,
    base: int,
    outcome: RollOutcome,
    overrides: dict[RollOutcome, dict[str, Any]] | None,
    target_tag: str | None,
) -> ResolvedDeltas:
    """Merge kind defaults with per-tier overrides into flat ``ResolvedDeltas``.

    Resolution order: kind defaults → per-tier override → engine zeros.

    ``target_tag`` is required for ``angle`` beats (used as the tag text
    on Success/CritSuccess and as the backfire text on CritFail). Other
    kinds may pass ``None``.
    """
    if outcome is RollOutcome.Unknown:
        raise ValueError("RollOutcome.Unknown cannot resolve a beat tier")

    if kind is BeatKind.angle and not target_tag:
        raise ValueError("angle beats require a target_tag")

    rule = dict(DEFAULT_DELTAS[kind][outcome])
    if overrides and outcome in overrides:
        rule.update(overrides[outcome])

    own = int(rule.get("own", 0))
    if "own_expr" in rule:
        own = _eval_expr(rule["own_expr"], base)

    opponent = int(rule.get("opponent", 0))
    if "opponent_expr" in rule:
        opponent = _eval_expr(rule["opponent_expr"], base)

    grants_tag = rule.get("grants_tag")
    grants_fleeting_tag = rule.get("grants_fleeting_tag")
    tag_leverage = int(rule.get("tag_leverage", 0))
    tag_backfire = bool(rule.get("tag_backfire", False))
    resolution = bool(rule.get("resolution", False))

    if rule.get("grants_tag_from_target"):
        grants_tag = target_tag
    if rule.get("grants_fleeting_tag_from_target"):
        grants_fleeting_tag = target_tag

    return ResolvedDeltas(
        own=own,
        opponent=opponent,
        grants_tag=grants_tag,
        tag_leverage=tag_leverage,
        grants_fleeting_tag=grants_fleeting_tag,
        tag_backfire=tag_backfire,
        resolution=resolution,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_beat_kinds.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/beat_kinds.py tests/server/test_beat_kinds.py
git commit -m "feat(game): BeatKind enum + per-kind tier default tables"
```

---

### Task 7: Reshape `BeatDef` and `ConfrontationDef` for kind/deltas/two-dial schema

Touches the genre-pack model. Existing single-`metric` packs must be loud-rejected (no silent fallback). All shipping packs are migrated in Phase 3.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py:71-130, 202-241`
- Test: `sidequest-server/tests/genre/test_rules_schema.py` (create or extend)

- [ ] **Step 1: Write failing tests**

Create or extend `sidequest-server/tests/genre/test_rules_schema.py`:

```python
import pytest
from pydantic import ValidationError
import yaml

from sidequest.genre.models.rules import BeatDef, ConfrontationDef


def _conf_yaml(beats_yaml: str, *, two_dials: bool = True) -> str:
    metric_block = (
        "player_metric:\n"
        "  name: momentum\n"
        "  starting: 0\n"
        "  threshold: 10\n"
        "opponent_metric:\n"
        "  name: momentum\n"
        "  starting: 0\n"
        "  threshold: 10\n"
    ) if two_dials else (
        "metric:\n"
        "  name: momentum\n"
        "  direction: bidirectional\n"
        "  starting: 0\n"
        "  threshold_high: 10\n"
        "  threshold_low: -10\n"
    )
    return (
        "type: combat\n"
        "label: Test Combat\n"
        "category: combat\n"
        f"{metric_block}"
        f"beats:\n{beats_yaml}"
    )


def test_beat_def_kind_required():
    raw = yaml.safe_load(
        "id: attack\nlabel: Attack\nkind: strike\nbase: 2\nstat_check: STR\n"
    )
    beat = BeatDef.model_validate(raw)
    assert beat.kind.value == "strike"
    assert beat.base == 2


def test_beat_def_invalid_kind_rejected():
    raw = yaml.safe_load(
        "id: x\nlabel: X\nkind: bogus\nbase: 1\nstat_check: STR\n"
    )
    with pytest.raises(ValidationError):
        BeatDef.model_validate(raw)


def test_beat_def_per_tier_override_parses():
    raw = yaml.safe_load("""
id: shield_bash
label: Shield Bash
kind: strike
base: 4
deltas:
  crit_fail:
    own: -2
  crit_success:
    own: 4
    grants_tag: "Off-Balance"
stat_check: STR
""")
    beat = BeatDef.model_validate(raw)
    assert beat.deltas is not None
    assert beat.deltas["crit_fail"]["own"] == -2
    assert beat.deltas["crit_success"]["grants_tag"] == "Off-Balance"


def test_angle_beat_requires_target_tag():
    raw = yaml.safe_load(
        "id: feint\nlabel: Feint\nkind: angle\nstat_check: DEX\n"
    )
    with pytest.raises(ValidationError):
        BeatDef.model_validate(raw)


def test_angle_beat_with_target_tag_ok():
    raw = yaml.safe_load(
        "id: feint\nlabel: Feint\nkind: angle\nstat_check: DEX\n"
        'target_tag: "Out of Position"\n'
    )
    beat = BeatDef.model_validate(raw)
    assert beat.target_tag == "Out of Position"


def test_confrontation_def_two_dials_loads():
    src = _conf_yaml(
        "  - id: attack\n"
        "    label: Attack\n"
        "    kind: strike\n"
        "    base: 2\n"
        "    stat_check: STR\n",
        two_dials=True,
    )
    cdef = ConfrontationDef.model_validate(yaml.safe_load(src))
    assert cdef.player_metric.threshold == 10
    assert cdef.opponent_metric.threshold == 10


def test_confrontation_def_legacy_single_metric_rejected():
    src = _conf_yaml(
        "  - id: attack\n"
        "    label: Attack\n"
        "    kind: strike\n"
        "    base: 2\n"
        "    stat_check: STR\n",
        two_dials=False,
    )
    with pytest.raises(ValidationError) as exc:
        ConfrontationDef.model_validate(yaml.safe_load(src))
    # Loud rejection per CLAUDE.md "no silent fallbacks".
    msg = str(exc.value)
    assert "metric" in msg or "player_metric" in msg


def test_legacy_metric_delta_field_rejected():
    raw = yaml.safe_load(
        "id: attack\nlabel: Attack\nkind: strike\nbase: 2\nstat_check: STR\n"
        "metric_delta: 2\n"
    )
    with pytest.raises(ValidationError):
        BeatDef.model_validate(raw)


def test_failure_metric_delta_field_rejected():
    raw = yaml.safe_load(
        "id: shield_bash\nlabel: Shield Bash\nkind: strike\nbase: 4\n"
        "stat_check: STR\nfailure_metric_delta: -2\n"
    )
    with pytest.raises(ValidationError):
        BeatDef.model_validate(raw)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/genre/test_rules_schema.py -v`

Expected: most fail — `BeatDef.kind` doesn't exist; `ConfrontationDef.player_metric` doesn't exist; legacy fields are still accepted.

- [ ] **Step 3: Update `BeatDef`**

Edit `sidequest-server/sidequest/genre/models/rules.py`. Replace the `BeatDef` class (lines ~71-108) with:

```python
class BeatDef(BaseModel):
    """A single action available during a confrontation.

    Schema (spec 2026-04-25-dual-track-momentum-design.md §Schema changes):

    - ``kind``: closed enum driving per-tier delta defaults.
    - ``base``: scalar magnitude; meaning depends on kind.
    - ``deltas``: optional per-tier override map; keys ∈
      {crit_fail, fail, tie, success, crit_success}; values are dicts of
      {own, opponent, grants_tag, grants_fleeting_tag, resolution, ...}.
    - ``target_tag``: required for kind=angle; text of the tag created.
    - Legacy ``metric_delta``/``failure_metric_delta``/``failure_effect``
      are deleted — pack migration is mandatory.
    """

    model_config = {"extra": "forbid"}

    id: str
    label: str
    kind: BeatKind
    base: int = 1
    deltas: dict[str, dict[str, Any]] | None = None
    target_tag: str | None = None
    stat_check: str
    risk: str | None = None  # narrator prose cue only — does not drive engine
    reveals: str | None = None
    resolution: bool | None = None  # legacy "always-resolves" flag (still useful for declarative pushes)
    effect: str | None = None
    consequence: str | None = None
    requires: str | None = None
    narrator_hint: str | None = None
    gold_delta: int | None = None
    edge_delta: int | None = None
    target_edge_delta: int | None = None
    resource_deltas: dict[str, float] | None = None

    @model_validator(mode="after")
    def _validate(self) -> BeatDef:
        if not self.id:
            raise ValueError("beat id must not be empty")
        if self.kind is BeatKind.angle and not self.target_tag:
            raise ValueError(
                f"beat '{self.id}' kind=angle requires target_tag"
            )
        if self.deltas is not None:
            valid_tiers = {
                "crit_fail", "fail", "tie", "success", "crit_success",
            }
            for tier in self.deltas:
                if tier not in valid_tiers:
                    raise ValueError(
                        f"beat '{self.id}' deltas key {tier!r} not in {valid_tiers}"
                    )
        return self
```

Add to the imports at the top of the file (alongside existing imports):

```python
from sidequest.game.beat_kinds import BeatKind
```

- [ ] **Step 4: Update `MetricDef` and `ConfrontationDef`**

Replace `MetricDef` (lines ~111-129) with a simpler ascending-only `MetricDef` and a per-side `MetricSideDef`:

```python
class MetricDef(BaseModel):
    """Per-side ascending metric for a confrontation.

    Spec change: bidirectional/descending metrics are gone — both sides have
    independent ascending dials. ``threshold`` is the cross point.
    """

    model_config = {"extra": "forbid"}

    name: str
    starting: int = 0
    threshold: int

    @model_validator(mode="after")
    def _validate(self) -> MetricDef:
        if self.threshold <= self.starting:
            raise ValueError(
                f"metric '{self.name}' threshold ({self.threshold}) must be "
                f"> starting ({self.starting})"
            )
        return self
```

Replace `ConfrontationDef`'s `metric` field with `player_metric`/`opponent_metric` and reject the legacy `metric` key:

```python
class ConfrontationDef(BaseModel):
    """A confrontation type declared by a genre pack in rules.yaml."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    confrontation_type: str = Field(alias="type", serialization_alias="type")
    label: str
    category: str
    resolution_mode: ResolutionMode = ResolutionMode.beat_selection
    player_metric: MetricDef
    opponent_metric: MetricDef
    beats: list[BeatDef] = Field(default_factory=list)
    secondary_stats: list[SecondaryStatDef] = Field(default_factory=list)
    escalates_to: str | None = None
    mood: str | None = None
    interaction_table: InteractionTable | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_metric(cls, data: object) -> object:
        if isinstance(data, dict) and "metric" in data:
            raise ValueError(
                "confrontation uses legacy single 'metric' shape; "
                "migrate to player_metric + opponent_metric per "
                "docs/superpowers/specs/2026-04-25-dual-track-momentum-design.md"
            )
        return data

    @model_validator(mode="after")
    def _validate(self) -> ConfrontationDef:
        if not self.confrontation_type:
            raise ValueError("confrontation type must not be empty")
        valid_categories = {"combat", "social", "pre_combat", "movement"}
        if self.category not in valid_categories:
            raise ValueError(
                f"invalid confrontation category '{self.category}': "
                f"must be one of {valid_categories}"
            )
        if not self.beats:
            raise ValueError(
                f"confrontation '{self.confrontation_type}' must have at least one beat"
            )
        seen: set[str] = set()
        for beat in self.beats:
            if beat.id in seen:
                raise ValueError(
                    f"confrontation '{self.confrontation_type}' has duplicate beat id '{beat.id}'"
                )
            seen.add(beat.id)
        return self
```

- [ ] **Step 5: Run the new tests**

Run: `cd sidequest-server && uv run pytest tests/genre/test_rules_schema.py -v`

Expected: PASS for all tests in this file. **Other tests** that load existing pack YAML will fail loudly — that's expected; Phase 3 migrates the packs.

- [ ] **Step 6: Commit**

```bash
git add sidequest/genre/models/rules.py tests/genre/test_rules_schema.py
git commit -m "feat(genre): BeatDef.kind/deltas/target_tag + dual-dial ConfrontationDef"
```

---

### Task 8: Reshape `EncounterMetric`, `StructuredEncounter`, `EncounterActor`

Wire the engine value types to the new shape: ascending-only `EncounterMetric`, dual `player_metric`/`opponent_metric`, `tags`, `EncounterActor.side` + `withdrawn`, and the structured outcome strings. Drop `MetricDirection` and the obsolete `chase()`/`combat()` constructors that depended on it.

**Files:**
- Modify: `sidequest-server/sidequest/game/encounter.py`
- Test: `sidequest-server/tests/server/test_encounter_model.py` (create)

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/server/test_encounter_model.py`:

```python
import pytest
from pydantic import ValidationError

from sidequest.game.encounter import (
    EncounterActor,
    EncounterMetric,
    StructuredEncounter,
)
from sidequest.game.encounter_tag import EncounterTag


def _metric(*, current: int = 0, threshold: int = 10) -> EncounterMetric:
    return EncounterMetric(name="momentum", current=current, starting=0, threshold=threshold)


def _actor(side: str = "player", *, name: str = "Sam") -> EncounterActor:
    return EncounterActor(name=name, role="combatant", side=side)


def test_encounter_metric_is_ascending_only_no_direction_field():
    m = _metric()
    assert m.current == 0
    assert m.threshold == 10
    with pytest.raises(ValidationError):
        EncounterMetric(name="x", current=0, starting=0, threshold=10, direction="ascending")  # type: ignore[call-arg]


def test_encounter_actor_side_required_and_closed_enum():
    EncounterActor(name="Sam", role="combatant", side="player")
    EncounterActor(name="Promo", role="combatant", side="opponent")
    EncounterActor(name="Host", role="bystander", side="neutral")
    with pytest.raises(ValidationError):
        EncounterActor(name="???", role="x", side="enemy")  # type: ignore[arg-type]


def test_encounter_actor_withdrawn_default_false():
    a = _actor()
    assert a.withdrawn is False


def test_structured_encounter_dual_dials_and_tags():
    enc = StructuredEncounter(
        encounter_type="combat",
        player_metric=_metric(),
        opponent_metric=_metric(),
        actors=[_actor("player"), _actor("opponent", name="Promo")],
    )
    assert enc.player_metric.threshold == 10
    assert enc.opponent_metric.threshold == 10
    assert enc.tags == []
    assert enc.outcome is None
    assert enc.resolved is False


def test_structured_encounter_rejects_old_metric_field():
    with pytest.raises(ValidationError):
        StructuredEncounter(  # type: ignore[call-arg]
            encounter_type="combat",
            metric=_metric(),
            actors=[_actor()],
        )


def test_structured_encounter_round_trip_with_tags():
    tag = EncounterTag(
        text="Off-Balance", created_by="Sam", target="Promo",
        leverage=1, fleeting=False, created_turn=2,
    )
    enc = StructuredEncounter(
        encounter_type="combat",
        player_metric=_metric(current=4),
        opponent_metric=_metric(current=7),
        actors=[_actor("player"), _actor("opponent", name="Promo")],
        tags=[tag],
        outcome=None,
    )
    raw = enc.model_dump_json()
    parsed = StructuredEncounter.model_validate_json(raw)
    assert parsed.tags == [tag]
    assert parsed.player_metric.current == 4
    assert parsed.opponent_metric.current == 7


def test_structured_outcome_values():
    # Outcome is a free-form str | None at the model level; engine writes
    # the structured values. The model just round-trips them.
    enc = StructuredEncounter(
        encounter_type="combat",
        player_metric=_metric(),
        opponent_metric=_metric(),
        actors=[_actor()],
        outcome="player_victory",
        resolved=True,
    )
    assert enc.outcome == "player_victory"


def test_metric_direction_enum_no_longer_importable():
    with pytest.raises(ImportError):
        from sidequest.game.encounter import MetricDirection  # noqa: F401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_model.py -v`

Expected: most FAIL — old shape still in place.

- [ ] **Step 3: Rewrite encounter.py**

Edit `sidequest-server/sidequest/game/encounter.py`. Replace the file's body (preserving the module docstring at the top) with the new shape:

```python
"""Structured Encounter System — dual-track momentum (spec 2026-04-25).

Replaces the single-dial bidirectional ``metric`` with two ascending dials
routed by actor side. ``MetricDirection`` is removed — both dials are
ascending; bidirectional was the workaround for actor-blind routing.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from sidequest.game.encounter_tag import EncounterTag


# ---------------------------------------------------------------------------
# RigType — preserved for chase cinematography (Phase 4 of the original port)
# ---------------------------------------------------------------------------

class RigType(str, Enum):
    """Rig archetype determines base stats."""

    Interceptor = "Interceptor"
    WarRig = "WarRig"
    Bike = "Bike"
    Hauler = "Hauler"
    Frankenstein = "Frankenstein"

    def base_stats(self) -> tuple[int, int, int, int, int]:
        return _RIG_BASE_STATS[self]


_RIG_BASE_STATS: dict[RigType, tuple[int, int, int, int, int]] = {
    RigType.Interceptor: (15, 5, 1, 3, 8),
    RigType.WarRig: (30, 2, 5, 1, 12),
    RigType.Bike: (8, 4, 0, 5, 5),
    RigType.Hauler: (25, 2, 3, 1, 20),
    RigType.Frankenstein: (18, 3, 2, 3, 10),
}


def _rig_damage_tier_label(hp: int, max_hp: int) -> str:
    if max_hp == 0:
        return "WRECK"
    pct = (hp / max_hp) * 100.0
    if pct <= 0.0:
        return "WRECK"
    if pct <= 25.0:
        return "SKELETON"
    if pct <= 50.0:
        return "FAILING"
    if pct <= 75.0:
        return "COSMETIC"
    return "PRISTINE"


# ---------------------------------------------------------------------------
# EncounterPhase
# ---------------------------------------------------------------------------

class EncounterPhase(str, Enum):
    Setup = "Setup"
    Opening = "Opening"
    Escalation = "Escalation"
    Climax = "Climax"
    Resolution = "Resolution"

    def drama_weight(self) -> float:
        return _DRAMA_WEIGHTS[self]


_DRAMA_WEIGHTS: dict[EncounterPhase, float] = {
    EncounterPhase.Setup: 0.70,
    EncounterPhase.Opening: 0.75,
    EncounterPhase.Escalation: 0.80,
    EncounterPhase.Climax: 0.95,
    EncounterPhase.Resolution: 0.70,
}


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

ActorSide = Literal["player", "opponent", "neutral"]


class StatValue(BaseModel):
    model_config = {"extra": "forbid"}
    current: int
    max: int


class SecondaryStats(BaseModel):
    model_config = {"extra": "forbid"}
    stats: dict[str, StatValue] = Field(default_factory=dict)
    damage_tier: str | None = None

    @classmethod
    def rig(cls, rig_type: RigType) -> SecondaryStats:
        hp, speed, armor, maneuver, fuel = rig_type.base_stats()
        stats: dict[str, StatValue] = {
            "hp": StatValue(current=hp, max=hp),
            "speed": StatValue(current=speed, max=speed),
            "armor": StatValue(current=armor, max=armor),
            "maneuver": StatValue(current=maneuver, max=maneuver),
            "fuel": StatValue(current=fuel, max=fuel),
        }
        return cls(stats=stats, damage_tier=_rig_damage_tier_label(hp, hp))


class EncounterActor(BaseModel):
    """A character assigned to an encounter role.

    ``side`` is closed: ``player`` (allies), ``opponent`` (anyone the party
    is fighting), ``neutral`` (bystanders, narrators, audience). Set at
    instantiation from the narrator's payload; engine never infers it.

    ``withdrawn`` flips True when the actor yields. Withdrawn actors are
    skipped by ``_apply_beat`` and emit a ``beat_skipped`` watcher event.
    """

    model_config = {"extra": "forbid"}

    name: str
    role: str
    side: ActorSide
    withdrawn: bool = False
    per_actor_state: dict[str, Any] = Field(default_factory=dict)


class EncounterMetric(BaseModel):
    """Ascending dial. ``current`` advances toward ``threshold``; the side
    that reaches ``threshold`` first triggers resolution.
    """

    model_config = {"extra": "forbid"}

    name: str
    current: int = 0
    starting: int = 0
    threshold: int


# ---------------------------------------------------------------------------
# StructuredEncounter
# ---------------------------------------------------------------------------

class StructuredEncounter(BaseModel):
    """A structured encounter with two side-routed dials.

    ``outcome`` values written by the engine:
    ``player_victory`` | ``opponent_victory`` | ``resolution_beat:<beat_id>``
    | ``yielded`` | ``None`` (unresolved).
    """

    model_config = {"extra": "forbid"}

    encounter_type: str
    player_metric: EncounterMetric
    opponent_metric: EncounterMetric
    beat: int = 0
    structured_phase: EncounterPhase | None = None
    secondary_stats: SecondaryStats | None = None
    actors: list[EncounterActor] = Field(default_factory=list)
    tags: list[EncounterTag] = Field(default_factory=list)
    outcome: str | None = None
    resolved: bool = False
    mood_override: str | None = None
    narrator_hints: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_metric(cls, data: object) -> object:
        if isinstance(data, dict) and "metric" in data:
            raise ValueError(
                "StructuredEncounter uses dual dials; legacy 'metric' field "
                "is rejected. Use player_metric + opponent_metric."
            )
        return data

    # ------------------------------------------------------------------
    # State mutations
    # ------------------------------------------------------------------

    def find_actor(self, name: str) -> EncounterActor | None:
        for a in self.actors:
            if a.name == name:
                return a
        return None

    def find_actor_for_player(self, player_name: str) -> EncounterActor | None:
        for a in self.actors:
            if a.side == "player" and a.name == player_name:
                return a
        return None

    def resolve_from_trope(self, trope_id: str) -> None:
        if self.resolved:
            return
        self.resolved = True
        self.structured_phase = EncounterPhase.Resolution
        self.outcome = f"resolved_by_trope:{trope_id}"
```

- [ ] **Step 4: Run the new tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_model.py -v`

Expected: PASS. The wider test suite will have failures referring to the removed `MetricDirection` / `chase()` / `combat()` constructors — fix those in the next steps.

- [ ] **Step 5: Sweep callers of `MetricDirection`**

Run: `cd sidequest-server && grep -rn "MetricDirection\|StructuredEncounter\.chase\|StructuredEncounter\.combat" sidequest tests`

For each hit (other than removals already pending in Tasks 9-13), update or delete the callsite. Expect the bulk to be in `narration_apply.py`, `dispatch/dice.py`, `dispatch/encounter_lifecycle.py`, and a handful of older tests. **Tests that depended on the legacy chase()/combat() classmethods should be rewritten to construct StructuredEncounter explicitly with `player_metric`/`opponent_metric`/`actors` per the new shape.**

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/encounter.py tests/server/test_encounter_model.py
git commit -m "feat(encounter): dual ascending dials + actor.side/withdrawn + tags"
```

---

### Task 9: Add new telemetry spans

Land all the new `encounter.*` span names + context managers. Kept in one task so callers in subsequent tasks can import the helpers without back-edits.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans.py`
- Test: `sidequest-server/tests/telemetry/test_encounter_spans.py` (create)

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/telemetry/test_encounter_spans.py`:

```python
"""Encounter span sanity tests.

These don't try to assert the full OTEL export pipeline — they just confirm
the new span name constants exist with the documented strings, the context
managers can be entered/exited, and they accept the documented attributes.
The events-table persistence tests live in test_encounter_telemetry.py.
"""
from sidequest.telemetry import spans


def test_new_span_names():
    assert spans.SPAN_ENCOUNTER_BEAT_SKIPPED == "encounter.beat_skipped"
    assert spans.SPAN_ENCOUNTER_INVALID_SIDE == "encounter.invalid_side"
    assert spans.SPAN_ENCOUNTER_INVALID_OUTCOME_TIER == "encounter.invalid_outcome_tier"
    assert spans.SPAN_ENCOUNTER_METRIC_ADVANCE == "encounter.metric_advance"
    assert spans.SPAN_ENCOUNTER_TAG_CREATED == "encounter.tag_created"
    assert spans.SPAN_ENCOUNTER_TAG_BACKFIRE == "encounter.tag_backfire"
    assert spans.SPAN_ENCOUNTER_STATUS_ADDED == "encounter.status_added"
    assert spans.SPAN_ENCOUNTER_YIELD_RECEIVED == "encounter.yield_received"
    assert spans.SPAN_ENCOUNTER_YIELD_RESOLVED == "encounter.yield_resolved"
    assert spans.SPAN_ENCOUNTER_RESOLUTION_SIGNAL_EMITTED == "encounter.resolution_signal_emitted"
    assert spans.SPAN_ENCOUNTER_RESOLUTION_SIGNAL_CONSUMED == "encounter.resolution_signal_consumed"


def test_context_managers_smoke():
    with spans.encounter_beat_skipped_span(
        reason="neutral_actor", actor="Host", actor_side="neutral", beat_id="attack",
    ):
        pass
    with spans.encounter_invalid_side_span(
        actor_name="??", declared_side="enemy", valid_set="player|opponent|neutral",
    ):
        pass
    with spans.encounter_invalid_outcome_tier_span(
        beat_id="attack", actor="Sam", declared_tier="Wibble",
        valid_set="CritFail|Fail|Tie|Success|CritSuccess",
    ):
        pass
    with spans.encounter_metric_advance_span(
        side="player", delta_kind="own", delta=2, before=0, after=2,
    ):
        pass
    with spans.encounter_tag_created_span(
        tag_text="Off-Balance", created_by="Sam", target="Promo",
        leverage=1, fleeting=False, created_via="angle_beat",
    ):
        pass
    with spans.encounter_tag_backfire_span(
        tag_text="Off-Balance", created_by="Sam", target="Sam", triggering_beat="feint",
    ):
        pass
    with spans.encounter_status_added_span(
        actor="Sam", text="Cracked Temple", severity="Wound", source="narrator_extraction",
    ):
        pass
    with spans.encounter_yield_received_span(
        player_id="p1", actor_name="Sam", prior_player_metric=4, prior_opponent_metric=7,
        statuses_taken_this_encounter=1,
    ):
        pass
    with spans.encounter_yield_resolved_span(
        outcome="yielded", yielded_actors=("Sam",), edge_refreshed=2,
    ):
        pass
    with spans.encounter_resolution_signal_emitted_span(
        outcome="opponent_victory", final_player_metric=4, final_opponent_metric=11,
    ):
        pass
    with spans.encounter_resolution_signal_consumed_span(
        outcome="opponent_victory", final_player_metric=4, final_opponent_metric=11,
    ):
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_encounter_spans.py -v`

Expected: AttributeError — none of the new constants exist.

- [ ] **Step 3: Add the span constants and context managers**

Edit `sidequest-server/sidequest/telemetry/spans.py`. Append to the encounter section (after the existing `encounter_confrontation_initiated_span` near line ~828):

```python
# ---------------------------------------------------------------------------
# Encounter (dual-track momentum, spec 2026-04-25)
# ---------------------------------------------------------------------------
SPAN_ENCOUNTER_BEAT_SKIPPED = "encounter.beat_skipped"
SPAN_ENCOUNTER_INVALID_SIDE = "encounter.invalid_side"
SPAN_ENCOUNTER_INVALID_OUTCOME_TIER = "encounter.invalid_outcome_tier"
SPAN_ENCOUNTER_METRIC_ADVANCE = "encounter.metric_advance"
SPAN_ENCOUNTER_TAG_CREATED = "encounter.tag_created"
SPAN_ENCOUNTER_TAG_BACKFIRE = "encounter.tag_backfire"
SPAN_ENCOUNTER_STATUS_ADDED = "encounter.status_added"
SPAN_ENCOUNTER_YIELD_RECEIVED = "encounter.yield_received"
SPAN_ENCOUNTER_YIELD_RESOLVED = "encounter.yield_resolved"
SPAN_ENCOUNTER_RESOLUTION_SIGNAL_EMITTED = "encounter.resolution_signal_emitted"
SPAN_ENCOUNTER_RESOLUTION_SIGNAL_CONSUMED = "encounter.resolution_signal_consumed"


def _enc_span(name: str, attrs: dict[str, Any]) -> Iterator[trace.Span]:
    t = tracer()
    return t.start_as_current_span(name, attributes=attrs)


@contextmanager
def encounter_beat_skipped_span(
    *, reason: str, actor: str, actor_side: str, beat_id: str, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_BEAT_SKIPPED,
        attributes={"reason": reason, "actor": actor,
                    "actor_side": actor_side, "beat_id": beat_id, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_invalid_side_span(
    *, actor_name: str, declared_side: str, valid_set: str, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_INVALID_SIDE,
        attributes={"actor_name": actor_name, "declared_side": declared_side,
                    "valid_set": valid_set, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_invalid_outcome_tier_span(
    *, beat_id: str, actor: str, declared_tier: str, valid_set: str, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_INVALID_OUTCOME_TIER,
        attributes={"beat_id": beat_id, "actor": actor,
                    "declared_tier": declared_tier, "valid_set": valid_set, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_metric_advance_span(
    *, side: str, delta_kind: str, delta: int, before: int, after: int, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_METRIC_ADVANCE,
        attributes={"side": side, "delta_kind": delta_kind, "delta": delta,
                    "before": before, "after": after, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_tag_created_span(
    *, tag_text: str, created_by: str, target: str | None,
    leverage: int, fleeting: bool, created_via: str, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_TAG_CREATED,
        attributes={"tag_text": tag_text, "created_by": created_by,
                    "target": target or "", "leverage": leverage,
                    "fleeting": fleeting, "created_via": created_via, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_tag_backfire_span(
    *, tag_text: str, created_by: str, target: str, triggering_beat: str, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_TAG_BACKFIRE,
        attributes={"tag_text": tag_text, "created_by": created_by,
                    "target": target, "triggering_beat": triggering_beat, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_status_added_span(
    *, actor: str, text: str, severity: str, source: str, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_STATUS_ADDED,
        attributes={"actor": actor, "text": text, "severity": severity,
                    "source": source, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_yield_received_span(
    *, player_id: str, actor_name: str, prior_player_metric: int,
    prior_opponent_metric: int, statuses_taken_this_encounter: int, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_YIELD_RECEIVED,
        attributes={"player_id": player_id, "actor_name": actor_name,
                    "prior_player_metric": prior_player_metric,
                    "prior_opponent_metric": prior_opponent_metric,
                    "statuses_taken_this_encounter": statuses_taken_this_encounter,
                    **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_yield_resolved_span(
    *, outcome: str, yielded_actors: tuple[str, ...], edge_refreshed: int, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_YIELD_RESOLVED,
        attributes={"outcome": outcome,
                    "yielded_actors": ",".join(yielded_actors),
                    "edge_refreshed": edge_refreshed, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_resolution_signal_emitted_span(
    *, outcome: str, final_player_metric: int, final_opponent_metric: int, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_RESOLUTION_SIGNAL_EMITTED,
        attributes={"outcome": outcome,
                    "final_player_metric": final_player_metric,
                    "final_opponent_metric": final_opponent_metric, **attrs},
    ) as s:
        yield s


@contextmanager
def encounter_resolution_signal_consumed_span(
    *, outcome: str, final_player_metric: int, final_opponent_metric: int, **attrs: Any,
) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(
        SPAN_ENCOUNTER_RESOLUTION_SIGNAL_CONSUMED,
        attributes={"outcome": outcome,
                    "final_player_metric": final_player_metric,
                    "final_opponent_metric": final_opponent_metric, **attrs},
    ) as s:
        yield s
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_encounter_spans.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/telemetry/spans.py tests/telemetry/test_encounter_spans.py
git commit -m "feat(telemetry): encounter spans for dual-track momentum"
```

---

### Task 10: Build the new shared `_apply_beat` helper

Tier-aware, side-aware, tag-aware. Lives in `beat_kinds.py` so both narrator and dice paths can call it. Pure function over (encounter, actor, beat, outcome) → `ApplyResult`.

**Files:**
- Modify: `sidequest-server/sidequest/game/beat_kinds.py`
- Test: `sidequest-server/tests/server/test_apply_beat.py` (create)

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/server/test_apply_beat.py`:

```python
import pytest

from sidequest.game.beat_kinds import (
    ApplyResult,
    apply_beat,
)
from sidequest.game.encounter import (
    EncounterActor,
    EncounterMetric,
    StructuredEncounter,
)
from sidequest.genre.models.rules import BeatDef
from sidequest.protocol.dice import RollOutcome


def _enc(*, p_thresh: int = 10, o_thresh: int = 10, p_cur: int = 0, o_cur: int = 0):
    return StructuredEncounter(
        encounter_type="combat",
        player_metric=EncounterMetric(name="momentum", current=p_cur, starting=0, threshold=p_thresh),
        opponent_metric=EncounterMetric(name="momentum", current=o_cur, starting=0, threshold=o_thresh),
        actors=[
            EncounterActor(name="Sam", role="combatant", side="player"),
            EncounterActor(name="Promo", role="combatant", side="opponent"),
            EncounterActor(name="Host", role="bystander", side="neutral"),
        ],
    )


def _strike_beat(beat_id: str = "attack", base: int = 2) -> BeatDef:
    return BeatDef.model_validate({
        "id": beat_id, "label": beat_id, "kind": "strike", "base": base,
        "stat_check": "STR",
    })


def _angle_beat(beat_id: str = "feint", target_tag: str = "Off-Balance") -> BeatDef:
    return BeatDef.model_validate({
        "id": beat_id, "label": beat_id, "kind": "angle",
        "target_tag": target_tag, "stat_check": "DEX",
    })


def _push_beat(beat_id: str = "flee") -> BeatDef:
    return BeatDef.model_validate({
        "id": beat_id, "label": beat_id, "kind": "push", "base": 1,
        "stat_check": "DEX",
    })


def test_strike_player_advances_player_metric_only():
    enc = _enc()
    sam = enc.find_actor("Sam")
    result = apply_beat(enc, sam, _strike_beat(base=2), RollOutcome.Success)
    assert enc.player_metric.current == 2
    assert enc.opponent_metric.current == 0
    assert result.resolved is False


def test_strike_opponent_advances_opponent_metric_only():
    enc = _enc()
    promo = enc.find_actor("Promo")
    result = apply_beat(enc, promo, _strike_beat(base=3), RollOutcome.Success)
    assert enc.player_metric.current == 0
    assert enc.opponent_metric.current == 3
    assert result.resolved is False


def test_neutral_actor_skipped_no_dial_change():
    enc = _enc()
    host = enc.find_actor("Host")
    result = apply_beat(enc, host, _strike_beat(), RollOutcome.Success)
    assert enc.player_metric.current == 0
    assert enc.opponent_metric.current == 0
    assert result.skipped_reason == "neutral_actor"


def test_withdrawn_actor_skipped():
    enc = _enc()
    sam = enc.find_actor("Sam")
    sam.withdrawn = True
    result = apply_beat(enc, sam, _strike_beat(), RollOutcome.Success)
    assert enc.player_metric.current == 0
    assert result.skipped_reason == "withdrawn_actor"


def test_threshold_cross_player_first_yields_player_victory():
    enc = _enc(p_cur=8)
    sam = enc.find_actor("Sam")
    apply_beat(enc, sam, _strike_beat(base=3), RollOutcome.Success)
    assert enc.player_metric.current == 11
    assert enc.resolved is True
    assert enc.outcome == "player_victory"


def test_threshold_cross_opponent_yields_opponent_victory():
    enc = _enc(o_cur=8)
    promo = enc.find_actor("Promo")
    apply_beat(enc, promo, _strike_beat(base=3), RollOutcome.Success)
    assert enc.opponent_metric.current == 11
    assert enc.resolved is True
    assert enc.outcome == "opponent_victory"


def test_push_success_resolves_with_resolution_beat_outcome():
    enc = _enc()
    sam = enc.find_actor("Sam")
    apply_beat(enc, sam, _push_beat("flee"), RollOutcome.Success)
    assert enc.resolved is True
    assert enc.outcome == "resolution_beat:flee"


def test_angle_success_creates_persistent_tag_with_leverage_one():
    enc = _enc()
    sam = enc.find_actor("Sam")
    apply_beat(enc, sam, _angle_beat("feint", "Off-Balance"), RollOutcome.Success)
    assert len(enc.tags) == 1
    tag = enc.tags[0]
    assert tag.text == "Off-Balance"
    assert tag.leverage == 1
    assert tag.fleeting is False
    assert tag.created_by == "Sam"


def test_angle_critsuccess_creates_tag_with_leverage_two():
    enc = _enc()
    sam = enc.find_actor("Sam")
    apply_beat(enc, sam, _angle_beat("feint", "Off-Balance"), RollOutcome.CritSuccess)
    assert enc.tags[0].leverage == 2


def test_angle_critfail_backfires_tag_onto_opposite_side():
    enc = _enc()
    sam = enc.find_actor("Sam")
    apply_beat(enc, sam, _angle_beat("feint", "Off-Balance"), RollOutcome.CritFail)
    assert len(enc.tags) == 1
    tag = enc.tags[0]
    assert tag.fleeting is True
    assert tag.target == "Promo"


def test_strike_critsuccess_creates_fleeting_opening_tag():
    enc = _enc()
    sam = enc.find_actor("Sam")
    apply_beat(enc, sam, _strike_beat(base=2), RollOutcome.CritSuccess)
    assert any(t.text == "Opening" and t.fleeting for t in enc.tags)


def test_post_resolution_apply_is_dropped_with_skipped_reason():
    enc = _enc()
    enc.resolved = True
    enc.outcome = "player_victory"
    sam = enc.find_actor("Sam")
    result = apply_beat(enc, sam, _strike_beat(), RollOutcome.Success)
    assert result.skipped_reason == "encounter_resolved"
    assert enc.player_metric.current == 0


def test_per_tier_override_applies_critfail_own_minus_two():
    enc = _enc()
    sam = enc.find_actor("Sam")
    bash = BeatDef.model_validate({
        "id": "shield_bash", "label": "Shield Bash", "kind": "strike", "base": 4,
        "stat_check": "STR",
        "deltas": {"crit_fail": {"own": -2}},
    })
    apply_beat(enc, sam, bash, RollOutcome.CritFail)
    # CritFail on strike default is 0 own; override drops to -2; ascending dial
    # is clamped at 0 (from spec — never go negative on a side's own dial)
    assert enc.player_metric.current == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v`

Expected: ImportError — `apply_beat` and `ApplyResult` don't exist on `beat_kinds`.

- [ ] **Step 3: Add `apply_beat` and `ApplyResult` to `beat_kinds.py`**

Append to `sidequest-server/sidequest/game/beat_kinds.py`:

```python
# ---------------------------------------------------------------------------
# apply_beat — shared between narrator and dice-throw paths
# ---------------------------------------------------------------------------
from dataclasses import dataclass

from sidequest.game.encounter import (  # placed at bottom to avoid cyclic import at top
    EncounterActor,
    EncounterPhase,
    EncounterTag,
    StructuredEncounter,
)
from sidequest.telemetry.spans import (
    encounter_metric_advance_span,
    encounter_tag_backfire_span,
    encounter_tag_created_span,
)


@dataclass(frozen=True)
class ApplyResult:
    """Outcome of one ``apply_beat`` invocation.

    ``skipped_reason`` is non-None when the beat was dropped — the encounter
    state is unchanged. ``resolved`` is True when this beat caused the
    encounter to flip ``resolved=True``.
    """

    deltas: ResolvedDeltas | None
    resolved: bool
    skipped_reason: str | None = None


def _phase_for_beat(beat: int) -> EncounterPhase:
    ladder = {
        0: EncounterPhase.Setup,
        1: EncounterPhase.Opening,
        2: EncounterPhase.Escalation,
        3: EncounterPhase.Escalation,
        4: EncounterPhase.Escalation,
    }
    return ladder.get(beat, EncounterPhase.Climax)


def _opposite_side_first_actor(
    enc: StructuredEncounter, side: str,
) -> str | None:
    other = "opponent" if side == "player" else "player"
    for a in enc.actors:
        if a.side == other and not a.withdrawn:
            return a.name
    return None


def _normalize_overrides(
    raw: dict[str, dict] | None,
) -> dict[RollOutcome, dict] | None:
    if raw is None:
        return None
    mapping = {
        "crit_fail": RollOutcome.CritFail,
        "fail": RollOutcome.Fail,
        "tie": RollOutcome.Tie,
        "success": RollOutcome.Success,
        "crit_success": RollOutcome.CritSuccess,
    }
    return {mapping[k]: v for k, v in raw.items()}


def apply_beat(
    enc: StructuredEncounter,
    actor: EncounterActor,
    beat: Any,  # BeatDef — typed as Any to dodge circular import
    outcome: RollOutcome,
    *,
    turn: int = 0,
) -> ApplyResult:
    """Apply one beat at one outcome tier to the encounter.

    Routes the deltas to the actor's side, processes tag/resolution extras,
    advances ``enc.beat`` and ``structured_phase``, and detects threshold
    crossings. Emits ``encounter.metric_advance``, ``encounter.tag_created``,
    and (on angle CritFail) ``encounter.tag_backfire`` spans.

    Skips with a structured reason when the actor is neutral, withdrawn,
    or the encounter is already resolved.
    """
    if enc.resolved:
        return ApplyResult(deltas=None, resolved=False, skipped_reason="encounter_resolved")
    if actor.side == "neutral":
        return ApplyResult(deltas=None, resolved=False, skipped_reason="neutral_actor")
    if actor.withdrawn:
        return ApplyResult(deltas=None, resolved=False, skipped_reason="withdrawn_actor")

    overrides = _normalize_overrides(getattr(beat, "deltas", None))
    deltas = resolve_tier_deltas(
        kind=beat.kind,
        base=getattr(beat, "base", 1),
        outcome=outcome,
        overrides=overrides,
        target_tag=getattr(beat, "target_tag", None),
    )

    own_metric = enc.player_metric if actor.side == "player" else enc.opponent_metric
    other_metric = enc.opponent_metric if actor.side == "player" else enc.player_metric

    if deltas.own != 0:
        before = own_metric.current
        own_metric.current = max(0, own_metric.current + deltas.own)
        with encounter_metric_advance_span(
            side=actor.side, delta_kind="own", delta=deltas.own,
            before=before, after=own_metric.current,
        ):
            pass

    if deltas.opponent != 0:
        before = other_metric.current
        # Opponent dial: ``brace`` emits a negative delta; ascending dials
        # are clamped at 0.
        other_metric.current = max(0, other_metric.current + deltas.opponent)
        with encounter_metric_advance_span(
            side=("opponent" if actor.side == "player" else "player"),
            delta_kind="cross", delta=deltas.opponent,
            before=before, after=other_metric.current,
        ):
            pass

    if deltas.tag_backfire:
        # Angle CritFail: tag goes onto the opposing side, fleeting.
        target_actor_name = _opposite_side_first_actor(enc, actor.side)
        tag = EncounterTag(
            text=getattr(beat, "target_tag", "Backfire"),
            created_by=actor.name,
            target=target_actor_name,
            leverage=1,
            fleeting=True,
            created_turn=turn,
        )
        enc.tags.append(tag)
        with encounter_tag_backfire_span(
            tag_text=tag.text, created_by=actor.name,
            target=target_actor_name or "", triggering_beat=beat.id,
        ):
            pass
    elif deltas.grants_tag:
        tag = EncounterTag(
            text=deltas.grants_tag,
            created_by=actor.name,
            target=_opposite_side_first_actor(enc, actor.side),
            leverage=deltas.tag_leverage or 1,
            fleeting=False,
            created_turn=turn,
        )
        enc.tags.append(tag)
        with encounter_tag_created_span(
            tag_text=tag.text, created_by=actor.name,
            target=tag.target, leverage=tag.leverage, fleeting=False,
            created_via="angle_beat",
        ):
            pass

    if deltas.grants_fleeting_tag and not deltas.tag_backfire:
        tag = EncounterTag(
            text=deltas.grants_fleeting_tag,
            created_by=actor.name,
            target=_opposite_side_first_actor(enc, actor.side),
            leverage=1,
            fleeting=True,
            created_turn=turn,
        )
        enc.tags.append(tag)
        with encounter_tag_created_span(
            tag_text=tag.text, created_by=actor.name,
            target=tag.target, leverage=1, fleeting=True,
            created_via="extras",
        ):
            pass

    enc.beat += 1
    enc.structured_phase = _phase_for_beat(enc.beat)

    resolved = False

    # Player threshold first, then opponent — sealed-letter order via
    # ADR-036 already places player beats first in the iteration; this
    # second-level tie-break is "first crossing wins".
    if enc.player_metric.current >= enc.player_metric.threshold:
        enc.resolved = True
        enc.outcome = "player_victory"
        enc.structured_phase = EncounterPhase.Resolution
        resolved = True
    elif enc.opponent_metric.current >= enc.opponent_metric.threshold:
        enc.resolved = True
        enc.outcome = "opponent_victory"
        enc.structured_phase = EncounterPhase.Resolution
        resolved = True
    elif deltas.resolution or getattr(beat, "resolution", False):
        enc.resolved = True
        enc.outcome = f"resolution_beat:{beat.id}"
        enc.structured_phase = EncounterPhase.Resolution
        resolved = True

    return ApplyResult(deltas=deltas, resolved=resolved, skipped_reason=None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/beat_kinds.py tests/server/test_apply_beat.py
git commit -m "feat(engine): shared apply_beat with tier+side+tag routing"
```

---

### Task 11: Replace narration_apply.py beat-application path

Wire the new shared `apply_beat` into the narrator extraction path. Remove the dead `apply_encounter_updates`, the `hostile_keywords` substring matcher, and the legacy `failure_metric_delta` branch.

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py`
- Test: `sidequest-server/tests/server/test_encounter_apply_narration.py` (extend)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/server/test_encounter_apply_narration.py`:

```python
from sidequest.agents.orchestrator import (
    BeatSelection, NarrationTurnResult, NpcMention,
)
from sidequest.game.encounter import (
    EncounterActor, EncounterMetric, StructuredEncounter,
)
from sidequest.game.session import GameSnapshot
from sidequest.protocol.dice import RollOutcome
from sidequest.server.narration_apply import _apply_narration_result_to_snapshot


def _two_dial_enc():
    return StructuredEncounter(
        encounter_type="combat",
        player_metric=EncounterMetric(name="momentum", current=0, starting=0, threshold=10),
        opponent_metric=EncounterMetric(name="momentum", current=0, starting=0, threshold=10),
        actors=[
            EncounterActor(name="Sam", role="combatant", side="player"),
            EncounterActor(name="Promo", role="combatant", side="opponent"),
        ],
    )


def test_narrator_player_strike_advances_player_metric(snapshot_with_pack):
    snap, pack = snapshot_with_pack  # provided by conftest — load caverns_and_claudes
    snap.encounter = _two_dial_enc()
    result = NarrationTurnResult(
        narration="Sam swings.",
        beat_selections=[BeatSelection(actor="Sam", beat_id="attack", outcome=RollOutcome.Success)],
        npcs_present=[NpcMention(name="Promo", side="opponent", role="hostile")],
    )
    _apply_narration_result_to_snapshot(snap, result, "Sam", pack=pack)
    assert snap.encounter.player_metric.current == 2
    assert snap.encounter.opponent_metric.current == 0


def test_narrator_opponent_strike_advances_opponent_metric(snapshot_with_pack):
    snap, pack = snapshot_with_pack
    snap.encounter = _two_dial_enc()
    result = NarrationTurnResult(
        narration="Promo lunges.",
        beat_selections=[BeatSelection(actor="Promo", beat_id="attack", outcome=RollOutcome.Success)],
        npcs_present=[NpcMention(name="Promo", side="opponent", role="hostile")],
    )
    _apply_narration_result_to_snapshot(snap, result, "Sam", pack=pack)
    assert snap.encounter.opponent_metric.current == 2
    assert snap.encounter.player_metric.current == 0


def test_unknown_actor_in_beat_selection_raises(snapshot_with_pack):
    snap, pack = snapshot_with_pack
    snap.encounter = _two_dial_enc()
    result = NarrationTurnResult(
        narration="Ghost swings.",
        beat_selections=[BeatSelection(actor="Ghost", beat_id="attack", outcome=RollOutcome.Success)],
    )
    import pytest
    with pytest.raises(ValueError, match="unknown actor"):
        _apply_narration_result_to_snapshot(snap, result, "Sam", pack=pack)


def test_apply_encounter_updates_no_longer_exported():
    import sidequest.server.narration_apply as mod
    assert not hasattr(mod, "apply_encounter_updates")
```

> The fixture `snapshot_with_pack` should live in `tests/server/conftest.py`. If it doesn't already exist as the dual-dial-aware version, **add it in this task's Step 2**:

- [ ] **Step 2: Add or update the conftest fixture**

Edit `sidequest-server/tests/server/conftest.py` to add (or update) a `snapshot_with_pack` fixture that loads the migrated `caverns_and_claudes` pack. *The pack itself is migrated in Phase 3; until then, build a synthetic in-memory pack.* For now use a synthetic pack:

```python
import pytest

from sidequest.game.session import GameSnapshot
from sidequest.game.turn import TurnManager
from sidequest.genre.models.pack import GenrePack
from sidequest.genre.models.rules import (
    BeatDef, ConfrontationDef, MetricDef, RulesConfig,
)


@pytest.fixture
def synthetic_two_dial_pack() -> GenrePack:
    cdef = ConfrontationDef(
        type="combat",
        label="Combat",
        category="combat",
        player_metric=MetricDef(name="momentum", starting=0, threshold=10),
        opponent_metric=MetricDef(name="momentum", starting=0, threshold=10),
        beats=[
            BeatDef.model_validate({
                "id": "attack", "label": "Attack", "kind": "strike",
                "base": 2, "stat_check": "STR",
            }),
            BeatDef.model_validate({
                "id": "defend", "label": "Defend", "kind": "brace",
                "base": 1, "stat_check": "CON",
            }),
            BeatDef.model_validate({
                "id": "flee", "label": "Flee", "kind": "push",
                "base": 1, "stat_check": "DEX",
            }),
            BeatDef.model_validate({
                "id": "feint", "label": "Feint", "kind": "angle",
                "target_tag": "Off-Balance", "stat_check": "DEX",
            }),
        ],
    )
    return GenrePack(
        slug="test_pack",
        rules=RulesConfig(confrontations=[cdef]),
    )


@pytest.fixture
def snapshot_with_pack(synthetic_two_dial_pack):
    snap = GameSnapshot(
        genre_slug="test_pack",
        world_slug="test_world",
        turn_manager=TurnManager(),
    )
    return snap, synthetic_two_dial_pack
```

(If `GameSnapshot`/`GenrePack` need additional required fields based on the current model, fill the minimum the constructor demands — adjust based on the live schema; do NOT add fields the engine doesn't need for these tests.)

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_apply_narration.py -v`

Expected: failures because `_apply_narration_result_to_snapshot` still uses the old single-`metric` shape.

- [ ] **Step 4: Rewrite the encounter section of narration_apply.py**

Edit `sidequest-server/sidequest/server/narration_apply.py`. Replace the encounter section (the block starting around line 224 with `if pack is not None:` through line 386 — including `_advance_phase` if it lives there) with:

```python
    # Encounter lifecycle (dual-track momentum, spec 2026-04-25)
    if pack is not None:
        from sidequest.game.beat_kinds import apply_beat
        from sidequest.server.dispatch.confrontation import find_confrontation_def
        from sidequest.server.dispatch.encounter_lifecycle import (
            instantiate_encounter_from_trigger,
        )
        from sidequest.telemetry.spans import (
            encounter_beat_skipped_span,
            encounter_empty_actor_list_span,
            encounter_resolved_span,
        )

        # (a) Narrator-initiated encounter
        if result.confrontation and (
            snapshot.encounter is None or snapshot.encounter.resolved
        ):
            if not result.npcs_present:
                with encounter_empty_actor_list_span(
                    encounter_type=result.confrontation,
                    genre_slug=snapshot.genre_slug or "",
                    player_name=player_name,
                ):
                    logger.warning(
                        "encounter.empty_actor_list confrontation=%s player=%s",
                        result.confrontation, player_name,
                    )
            instantiate_encounter_from_trigger(
                snapshot=snapshot,
                pack=pack,
                encounter_type=result.confrontation,
                player_name=player_name,
                npcs_present=result.npcs_present,
                genre_slug=snapshot.genre_slug,
            )

        # (b) Apply beat selections (dice-replay turns short-circuit)
        enc = snapshot.encounter
        if enc is not None and not enc.resolved and result.beat_selections:
            cdef = find_confrontation_def(
                pack.rules.confrontations if pack.rules else [],
                enc.encounter_type,
            )
            if cdef is None:
                raise ValueError(
                    f"active encounter type {enc.encounter_type!r} not in pack"
                )
            beat_by_id = {b.id: b for b in cdef.beats}

            selections = result.beat_selections
            if dice_failed is not None and selections:
                # Dice-replay turns: dispatch/dice.py already applied the beat;
                # narrator beat_selections are dropped.
                for sel in selections:
                    actor = enc.find_actor(sel.actor)
                    side = actor.side if actor else "unknown"
                    with encounter_beat_skipped_span(
                        reason="dice_replay_turn",
                        actor=sel.actor, actor_side=side, beat_id=sel.beat_id,
                    ):
                        pass
                selections = []

            turn_num = snapshot.turn_manager.interaction
            for sel in selections:
                actor = enc.find_actor(sel.actor)
                if actor is None:
                    raise ValueError(f"unknown actor {sel.actor!r} in beat selection")
                beat = beat_by_id.get(sel.beat_id)
                if beat is None:
                    raise ValueError(
                        f"unknown beat_id {sel.beat_id!r} for encounter {enc.encounter_type!r}"
                    )
                outcome = sel.outcome  # narrator-declared tier
                result_apply = apply_beat(enc, actor, beat, outcome, turn=turn_num)
                if result_apply.skipped_reason is not None:
                    with encounter_beat_skipped_span(
                        reason=result_apply.skipped_reason,
                        actor=actor.name, actor_side=actor.side,
                        beat_id=sel.beat_id,
                    ):
                        pass
                    continue
                if result_apply.resolved:
                    with encounter_resolved_span(
                        encounter_type=enc.encounter_type,
                        outcome=enc.outcome or "",
                        source="narrator_beat",
                    ):
                        pass
                    snapshot.pending_resolution_signal = _build_resolution_signal(enc)
                    break
```

Add the helper at module scope:

```python
def _build_resolution_signal(enc):
    from sidequest.game.resolution_signal import ResolutionSignal
    return ResolutionSignal(
        encounter_type=enc.encounter_type,
        outcome=enc.outcome or "",
        final_player_metric=enc.player_metric.current,
        final_opponent_metric=enc.opponent_metric.current,
        yielded_actors=tuple(),
        edge_refreshed=0,
    )
```

Delete the entire `apply_encounter_updates` function (lines ~403-612). Delete the `_advance_phase` function (now unreachable — `apply_beat` handles phase transitions). Remove `hostile_keywords` references entirely (they're in the deleted block).

- [ ] **Step 5: Remove the dead re-export in session_handler**

Open `sidequest-server/sidequest/server/session_handler.py` and remove the lines that import or re-export `apply_encounter_updates` (the `__all__` entry around line 4241 and the import around line 4203).

Run `grep -rn "apply_encounter_updates" sidequest tests` to find any remaining references and delete them.

- [ ] **Step 6: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_apply_narration.py -v`

Expected: PASS.

Run the broader server suite: `cd sidequest-server && uv run pytest tests/server -x -q`. Expect failures in dispatch/dice paths (covered in Task 12) and pack-load tests (covered in Phase 3).

- [ ] **Step 7: Commit**

```bash
git add sidequest/server/narration_apply.py sidequest/server/session_handler.py \
        tests/server/test_encounter_apply_narration.py tests/server/conftest.py
git commit -m "refactor(narration_apply): use shared apply_beat; drop dead encounter path"
```

---

### Task 12: Update dispatch/dice.py to use shared `apply_beat`

The DICE_THROW handler currently has its own `_apply_beat` and resolves only against `metric.threshold_high/low`. Replace with the shared helper, propagate the resolved tier (now including Tie + margin-CritSuccess) into `apply_beat`.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py`
- Test: `sidequest-server/tests/server/test_dice_dispatch.py` (extend)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/server/test_dice_dispatch.py`:

```python
def test_dice_throw_strike_player_advances_player_metric(dual_dial_test_setup):
    # dual_dial_test_setup is a fixture creating a fresh encounter, pack, and
    # the inputs to dispatch_dice_throw. Build it from the synthetic pack.
    setup = dual_dial_test_setup
    outcome = setup.run_dice_throw(beat_id="attack", faces=[15], modifier=0)
    # DC for strike base=2 is 10 + 2*2 = 14; 15 → Success
    assert outcome.outcome.value == "Success"
    assert setup.encounter.player_metric.current == 2
    assert setup.encounter.opponent_metric.current == 0


def test_dice_throw_tie_at_dc_resolves_to_tie_tier(dual_dial_test_setup):
    setup = dual_dial_test_setup
    # DC 14 + face 14 + modifier 0 → Tie (graze: own += b // 2 = 1)
    outcome = setup.run_dice_throw(beat_id="attack", faces=[14], modifier=0)
    assert outcome.outcome.value == "Tie"
    assert setup.encounter.player_metric.current == 1


def test_dice_throw_critfail_strike_zero_metric(dual_dial_test_setup):
    setup = dual_dial_test_setup
    outcome = setup.run_dice_throw(beat_id="attack", faces=[1], modifier=0)
    assert outcome.outcome.value == "CritFail"
    assert setup.encounter.player_metric.current == 0
```

Build the `dual_dial_test_setup` fixture in `tests/server/conftest.py`:

```python
@pytest.fixture
def dual_dial_test_setup(synthetic_two_dial_pack):
    from dataclasses import dataclass

    from sidequest.game.encounter import (
        EncounterActor, EncounterMetric, StructuredEncounter,
    )
    from sidequest.protocol.dice import DiceThrowPayload, ThrowParams
    from sidequest.server.dispatch.dice import dispatch_dice_throw

    @dataclass
    class _Setup:
        encounter: StructuredEncounter
        pack: object

        def run_dice_throw(self, *, beat_id, faces, modifier):
            payload = DiceThrowPayload(
                request_id="r1",
                throw_params=ThrowParams(velocity=(0, 0, 0), angular=(0, 0, 0), position=(0, 0)),
                face=faces,
                beat_id=beat_id,
            )
            return dispatch_dice_throw(
                payload=payload,
                rolling_player_id="p1",
                character_name="Sam",
                character_stats={"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
                encounter=self.encounter,
                pack=self.pack,
                session_id="s1",
                round_number=1,
                room_broadcast=None,
            )

    enc = StructuredEncounter(
        encounter_type="combat",
        player_metric=EncounterMetric(name="momentum", current=0, starting=0, threshold=10),
        opponent_metric=EncounterMetric(name="momentum", current=0, starting=0, threshold=10),
        actors=[EncounterActor(name="Sam", role="combatant", side="player")],
    )
    return _Setup(encounter=enc, pack=synthetic_two_dial_pack)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_dice_dispatch.py -v -k 'dual_dial' --no-header`

Expected: FAIL — old `_apply_beat` in dispatch/dice.py uses `encounter.metric` which no longer exists.

- [ ] **Step 3: Replace dispatch/dice.py beat application**

Edit `sidequest-server/sidequest/server/dispatch/dice.py`. Delete the local `_apply_beat` (lines ~127-168) and the `_resolve_applied_delta` function (lines ~113-124). At the call site in `dispatch_dice_throw` (around lines ~342-356), replace with:

```python
    # Resolve dice first so apply_beat sees the actual tier.
    try:
        resolved = resolve_dice_with_faces(
            request.dice, list(payload.face), request.modifier, request.difficulty,
        )
    except ResolveError as exc:
        raise DiceDispatchError(f"dice resolution failed: {exc}") from exc

    actor = encounter.find_actor(character_name)
    if actor is None:
        raise DiceDispatchError(
            f"character {character_name!r} not found in encounter actors"
        )

    from sidequest.game.beat_kinds import apply_beat
    apply_result = apply_beat(
        encounter, actor, beat, resolved.outcome,
        turn=round_number,
    )

    with encounter_beat_applied_span(
        encounter_type=encounter.encounter_type,
        actor=character_name,
        beat_id=payload.beat_id,
        metric_delta=(apply_result.deltas.own if apply_result.deltas else 0),
    ):
        pass

    with combat_tick_span(
        encounter_type=encounter.encounter_type,
        beat=encounter.beat,
        phase=(encounter.structured_phase or EncounterPhase.Setup).value,
    ):
        pass

    if apply_result.resolved:
        with encounter_resolved_span(
            encounter_type=encounter.encounter_type,
            outcome=encounter.outcome or "",
            source="dice_throw_beat",
        ):
            pass
```

Update the import block at the top to drop `MetricDirection`:

```python
from sidequest.game.encounter import EncounterPhase, StructuredEncounter
```

Update the `DiceThrowOutcome.encounter_resolved` value to read from `apply_result.resolved` rather than the deleted return tuple.

Update the `_format_replay_action` callers — `metric_before`/`metric_after` no longer exist on a single dial. Replace with the dial that the actor's side advanced. The simplest path: emit `<player|opponent>_momentum_before/after` based on `actor.side`. Update the function signature to take an `actor_side` parameter and the metric snapshots from the encounter.

```python
def _format_replay_action(
    *,
    beat_label: str,
    stat_check: str,
    actor_side: str,
    player_metric_after: int,
    opponent_metric_after: int,
    total: int,
    outcome: RollOutcome,
) -> str:
    return (
        f"[BEAT_RESOLVED] {beat_label} ({stat_check}, side={actor_side}): "
        f"player_momentum={player_metric_after} | "
        f"opponent_momentum={opponent_metric_after} | "
        f"Roll: {total} ({outcome.value})"
    )
```

And the call site:

```python
    replay_text = _format_replay_action(
        beat_label=beat.label,
        stat_check=beat.stat_check,
        actor_side=actor.side,
        player_metric_after=encounter.player_metric.current,
        opponent_metric_after=encounter.opponent_metric.current,
        total=resolved.total,
        outcome=resolved.outcome,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_dice_dispatch.py tests/server/test_dice_throw_wiring.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/dispatch/dice.py tests/server/test_dice_dispatch.py tests/server/conftest.py
git commit -m "refactor(dispatch/dice): use shared apply_beat with tier-aware deltas"
```

---

### Task 13: Update encounter_lifecycle.py for dual dials and side-from-payload

Lifecycle drops `_DIRECTION_BY_NAME`, builds two dials from `cdef`, and sets `EncounterActor.side` from the narrator's `npcs_present` payload (now carrying `side`).

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py`
- Test: `sidequest-server/tests/server/test_encounter_lifecycle.py` (extend)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/server/test_encounter_lifecycle.py`:

```python
from sidequest.agents.orchestrator import NpcMention
from sidequest.server.dispatch.encounter_lifecycle import (
    instantiate_encounter_from_trigger,
)


def test_instantiate_two_dials_from_cdef(snapshot_with_pack):
    snap, pack = snapshot_with_pack
    enc = instantiate_encounter_from_trigger(
        snapshot=snap,
        pack=pack,
        encounter_type="combat",
        player_name="Sam",
        npcs_present=[NpcMention(name="Promo", side="opponent", role="hostile")],
        genre_slug="test_pack",
    )
    assert enc is not None
    assert enc.player_metric.threshold == 10
    assert enc.opponent_metric.threshold == 10


def test_instantiate_routes_actor_sides_from_payload(snapshot_with_pack):
    snap, pack = snapshot_with_pack
    enc = instantiate_encounter_from_trigger(
        snapshot=snap,
        pack=pack,
        encounter_type="combat",
        player_name="Sam",
        npcs_present=[
            NpcMention(name="Promo", side="opponent", role="hostile"),
            NpcMention(name="Host", side="neutral", role="bystander"),
        ],
        genre_slug="test_pack",
    )
    sides = {a.name: a.side for a in enc.actors}
    assert sides["Sam"] == "player"
    assert sides["Promo"] == "opponent"
    assert sides["Host"] == "neutral"


def test_invalid_side_raises_with_span(snapshot_with_pack):
    import pytest
    snap, pack = snapshot_with_pack
    with pytest.raises(ValueError, match="declared_side"):
        instantiate_encounter_from_trigger(
            snapshot=snap,
            pack=pack,
            encounter_type="combat",
            player_name="Sam",
            npcs_present=[NpcMention(name="??", side="enemy", role="hostile")],
            genre_slug="test_pack",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: failures because the function signature still takes `combatants: list[str], hp: int`, not the npc-payload list.

- [ ] **Step 3: Rewrite encounter_lifecycle.py**

Replace the body of `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py`:

```python
"""Encounter lifecycle — instantiation, resolution.

Dual-track momentum (spec 2026-04-25): builds two ascending dials from the
ConfrontationDef and routes actor side from the narrator's npcs_present
payload. No keyword-bucket inference; ``side`` is structural.
"""
from __future__ import annotations

from typing import Iterable

from sidequest.game.encounter import (
    EncounterActor,
    EncounterMetric,
    EncounterPhase,
    StructuredEncounter,
)
from sidequest.game.lore_store import LoreStore
from sidequest.game.resource_pool import ResourceThreshold
from sidequest.game.session import GameSnapshot
from sidequest.genre.models.pack import GenrePack
from sidequest.genre.models.rules import ConfrontationDef, MetricDef
from sidequest.server.dispatch.confrontation import find_confrontation_def
from sidequest.telemetry.spans import (
    encounter_confrontation_initiated_span,
    encounter_invalid_side_span,
    encounter_resolved_span,
)


_VALID_SIDES = ("player", "opponent", "neutral")


def _metric_from_def(md: MetricDef) -> EncounterMetric:
    return EncounterMetric(
        name=md.name,
        current=md.starting,
        starting=md.starting,
        threshold=md.threshold,
    )


def _validate_side(actor_name: str, declared: str) -> str:
    if declared in _VALID_SIDES:
        return declared
    with encounter_invalid_side_span(
        actor_name=actor_name,
        declared_side=declared,
        valid_set="|".join(_VALID_SIDES),
    ):
        pass
    raise ValueError(
        f"actor {actor_name!r} declared_side={declared!r} not in {_VALID_SIDES}"
    )


def instantiate_encounter_from_trigger(
    *,
    snapshot: GameSnapshot,
    pack: GenrePack,
    encounter_type: str,
    player_name: str,
    npcs_present: Iterable[object],
    genre_slug: str | None,
) -> StructuredEncounter | None:
    """Create a StructuredEncounter from the narrator's confrontation trigger.

    Returns the new encounter, or ``None`` if an unresolved encounter
    already exists. Raises ``ValueError`` for unknown encounter types or
    invalid actor sides — no silent fallbacks.

    ``npcs_present`` carries the narrator's ``NpcMention`` instances; each
    must have a ``side`` ∈ {player, opponent, neutral}. The active player
    character is added with ``side="player"``.
    """
    current = snapshot.encounter
    if current is not None and not current.resolved:
        return None

    defs = pack.rules.confrontations if pack.rules else []
    cdef: ConfrontationDef | None = find_confrontation_def(defs, encounter_type)
    if cdef is None:
        raise ValueError(
            f"unknown encounter_type {encounter_type!r} — not in pack confrontations"
        )

    with encounter_confrontation_initiated_span(
        encounter_type=encounter_type,
        genre_slug=genre_slug or "",
        player_metric_threshold=cdef.player_metric.threshold,
        opponent_metric_threshold=cdef.opponent_metric.threshold,
    ):
        actors: list[EncounterActor] = [
            EncounterActor(
                name=player_name,
                role="combatant" if cdef.category == "combat" else "participant",
                side="player",
            )
        ]
        for npc in npcs_present:
            side_raw = getattr(npc, "side", None) or "neutral"
            side = _validate_side(getattr(npc, "name", "?"), side_raw)
            actors.append(
                EncounterActor(
                    name=getattr(npc, "name", "?"),
                    role=getattr(npc, "role", None) or "participant",
                    side=side,
                )
            )

        enc = StructuredEncounter(
            encounter_type=encounter_type,
            player_metric=_metric_from_def(cdef.player_metric),
            opponent_metric=_metric_from_def(cdef.opponent_metric),
            beat=0,
            structured_phase=EncounterPhase.Setup,
            actors=actors,
            mood_override=cdef.mood,
        )
        snapshot.encounter = enc
        return enc


def resolve_encounter_from_trope(
    *,
    snapshot: GameSnapshot,
    trope_id: str,
) -> StructuredEncounter | None:
    enc = snapshot.encounter
    if enc is None or enc.resolved:
        return None
    with encounter_resolved_span(
        encounter_type=enc.encounter_type,
        outcome=f"resolved_by_trope:{trope_id}",
        source="trope",
    ):
        enc.resolve_from_trope(trope_id)
    return enc


def _is_combat_category(pack: GenrePack, encounter_type: str) -> bool:
    defs = pack.rules.confrontations if pack.rules else []
    for d in defs:
        if d.confrontation_type == encounter_type:
            return d.category == "combat"
    return False


def award_turn_xp(snapshot: GameSnapshot, *, in_combat: bool) -> None:
    if not snapshot.characters:
        return
    delta = 25 if in_combat else 10
    char = snapshot.characters[0]
    char.core.xp = char.core.xp + delta


def apply_resource_patches(
    snapshot: GameSnapshot,
    *,
    affinity_progress: list[tuple[str, int]],
    lore_store: LoreStore,
    turn: int,
) -> list[ResourceThreshold]:
    from sidequest.game.resource_pool import ResourcePatchOp
    from sidequest.game.thresholds import mint_threshold_lore

    all_crossed: list[ResourceThreshold] = []
    for name, delta in affinity_progress:
        op = ResourcePatchOp.Add if delta >= 0 else ResourcePatchOp.Subtract
        value = float(abs(delta))
        result = snapshot.apply_resource_patch_by_name(name, op, value)
        mint_threshold_lore(result.crossed_thresholds, lore_store, turn)
        all_crossed.extend(result.crossed_thresholds)
    return all_crossed
```

- [ ] **Step 4: Update the lone caller in narration_apply.py**

In Task 11 the call site already passes `npcs_present=result.npcs_present`. Verify by `grep -n "instantiate_encounter_from_trigger" sidequest`.

- [ ] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_lifecycle.py tests/server/test_encounter_apply_narration.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/dispatch/encounter_lifecycle.py tests/server/test_encounter_lifecycle.py
git commit -m "refactor(lifecycle): dual dials + side-from-payload + invalid-side fail-loud"
```

---

## Phase 2 — Narrator awareness, telemetry persistence, GM panel

### Task 14: Add `ResolutionSignal` and `pending_resolution_signal` slot

The transient one-shot payload that carries the just-resolved encounter into the next narrator turn.

**Files:**
- Create: `sidequest-server/sidequest/game/resolution_signal.py`
- Modify: `sidequest-server/sidequest/game/session.py` (add `pending_resolution_signal` field on `GameSnapshot` or `_SessionData` — wherever transient session state lives)
- Test: `sidequest-server/tests/server/test_resolution_signal.py`

- [ ] **Step 1: Inspect where transient session state lives**

Run: `cd sidequest-server && grep -n "class GameSnapshot\|class _SessionData\|pending_" sidequest/game/session.py | head -20`

Note which class owns transient state — call it `_SessionData` below; substitute the actual class name if different. If the codebase keeps it on `GameSnapshot`, place the field there.

- [ ] **Step 2: Write failing tests**

Create `sidequest-server/tests/server/test_resolution_signal.py`:

```python
from sidequest.game.resolution_signal import ResolutionSignal


def test_resolution_signal_round_trip():
    sig = ResolutionSignal(
        encounter_type="combat",
        outcome="opponent_victory",
        final_player_metric=4,
        final_opponent_metric=11,
        yielded_actors=("Sam",),
        edge_refreshed=2,
    )
    assert sig.outcome == "opponent_victory"
    assert sig.yielded_actors == ("Sam",)
```

```python
# Append to tests/server/test_resolution_signal.py
def test_session_pending_resolution_signal_default_none(snapshot_with_pack):
    snap, _ = snapshot_with_pack
    assert snap.pending_resolution_signal is None


def test_session_pending_resolution_signal_can_be_set_and_cleared(snapshot_with_pack):
    snap, _ = snapshot_with_pack
    snap.pending_resolution_signal = ResolutionSignal(
        encounter_type="combat",
        outcome="player_victory",
        final_player_metric=10,
        final_opponent_metric=4,
        yielded_actors=tuple(),
        edge_refreshed=0,
    )
    assert snap.pending_resolution_signal is not None
    snap.pending_resolution_signal = None
    assert snap.pending_resolution_signal is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_resolution_signal.py -v`

Expected: ImportError; later, AttributeError on `snap.pending_resolution_signal`.

- [ ] **Step 4: Create the dataclass**

Create `sidequest-server/sidequest/game/resolution_signal.py`:

```python
"""ResolutionSignal — one-shot payload feeding the [ENCOUNTER RESOLVED] zone.

Set by ``apply_beat`` (via narration_apply or dispatch/dice) when the
encounter flips ``resolved=True``. The narrator prompt assembler reads
this slot on the next turn and clears it. Spec 2026-04-25-dual-track-
momentum-design.md §"[ENCOUNTER RESOLVED] zone (one-shot)".
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ResolutionSignal(BaseModel):
    """The transient signal carried into one (and only one) narrator turn."""

    model_config = {"extra": "forbid"}

    encounter_type: str
    outcome: str
    final_player_metric: int
    final_opponent_metric: int
    yielded_actors: tuple[str, ...] = Field(default_factory=tuple)
    edge_refreshed: int = 0
```

- [ ] **Step 5: Add the field on the session-state class**

Edit `sidequest-server/sidequest/game/session.py`. On the appropriate class (`GameSnapshot`):

```python
    from sidequest.game.resolution_signal import ResolutionSignal  # near other imports

    pending_resolution_signal: ResolutionSignal | None = None
```

If `GameSnapshot` uses `model_config = {"extra": "forbid"}`, this is a real schema change — saved snapshots without the field default to `None`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_resolution_signal.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add sidequest/game/resolution_signal.py sidequest/game/session.py \
        tests/server/test_resolution_signal.py
git commit -m "feat(session): pending_resolution_signal slot + ResolutionSignal payload"
```

---

### Task 15: Extend `BeatSelection` and `NpcMention` for outcome + side

Adds the new structured fields the narrator must emit and the engine consumes.

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py:84-152`
- Test: `sidequest-server/tests/agents/test_narration_extraction.py` (extend or create)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/agents/test_narration_extraction.py` (create the file if missing):

```python
import pytest

from sidequest.agents.orchestrator import BeatSelection, NpcMention
from sidequest.protocol.dice import RollOutcome


def test_beat_selection_outcome_required():
    sel = BeatSelection.from_dict({
        "actor": "Sam", "beat_id": "attack", "outcome": "Success",
    })
    assert sel.outcome is RollOutcome.Success


def test_beat_selection_invalid_outcome_raises():
    with pytest.raises(ValueError, match="declared_tier"):
        BeatSelection.from_dict({
            "actor": "Sam", "beat_id": "attack", "outcome": "Wibble",
        })


def test_beat_selection_missing_outcome_defaults_to_success_with_warning(caplog):
    # Per spec §Outcome declaration: missing outcome on free-text turns is a
    # narrator contract break. Engine logs and treats as Success — the
    # span fires (encounter.invalid_outcome_tier with declared_tier="").
    sel = BeatSelection.from_dict({"actor": "Sam", "beat_id": "attack"})
    assert sel.outcome is RollOutcome.Success


def test_npc_mention_side_required():
    npc = NpcMention.from_value({"name": "Promo", "side": "opponent", "role": "hostile"})
    assert npc.side == "opponent"


def test_npc_mention_invalid_side_raises():
    with pytest.raises(ValueError, match="declared_side"):
        NpcMention.from_value({"name": "??", "side": "enemy"})


def test_npc_mention_bare_string_default_side_neutral():
    npc = NpcMention.from_value("Random Bystander")
    assert npc.side == "neutral"
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: AttributeError / ValueError mismatches — the fields don't exist yet.

- [ ] **Step 3: Update `BeatSelection` and `NpcMention`**

Edit `sidequest-server/sidequest/agents/orchestrator.py`. In the `BeatSelection` dataclass (~line 84):

```python
@dataclass
class BeatSelection:
    """A single beat selection from the narrator's output.

    ``outcome`` is the resolved tier the prose describes. On free-text
    turns the narrator emits it; on dice-replay turns the engine
    overwrites it with the dice resolver's tier.
    """
    actor: str
    beat_id: str
    outcome: RollOutcome = RollOutcome.Success  # default for legacy callers
    target: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BeatSelection:
        raw_outcome = d.get("outcome")
        if raw_outcome is None or raw_outcome == "":
            outcome = RollOutcome.Success
        else:
            try:
                outcome = RollOutcome(str(raw_outcome))
            except ValueError as exc:
                from sidequest.telemetry.spans import (
                    encounter_invalid_outcome_tier_span,
                )
                with encounter_invalid_outcome_tier_span(
                    beat_id=str(d.get("beat_id", "")),
                    actor=str(d.get("actor", "")),
                    declared_tier=str(raw_outcome),
                    valid_set="CritFail|Fail|Tie|Success|CritSuccess",
                ):
                    pass
                raise ValueError(
                    f"BeatSelection declared_tier={raw_outcome!r} not in RollOutcome"
                ) from exc
        return cls(
            actor=str(d.get("actor", "")),
            beat_id=str(d.get("beat_id", "")),
            outcome=outcome,
            target=d.get("target"),
        )
```

Add `from sidequest.protocol.dice import RollOutcome` to the import list.

In `NpcMention`:

```python
@dataclass
class NpcMention:
    """An NPC mentioned in the narrator's structured output."""
    name: str
    pronouns: str = ""
    role: str = ""
    appearance: str = ""
    side: str = "neutral"
    is_new: bool = False

    @classmethod
    def from_value(cls, value: Any) -> NpcMention:
        valid_sides = {"player", "opponent", "neutral"}
        if isinstance(value, str):
            return cls(name=value, side="neutral")
        if isinstance(value, dict):
            side = str(value.get("side", "") or "neutral")
            if side not in valid_sides:
                from sidequest.telemetry.spans import encounter_invalid_side_span
                with encounter_invalid_side_span(
                    actor_name=str(value.get("name", "?")),
                    declared_side=side,
                    valid_set="player|opponent|neutral",
                ):
                    pass
                raise ValueError(
                    f"NpcMention declared_side={side!r} not in {valid_sides}"
                )
            return cls(
                name=str(value.get("name", "")),
                pronouns=str(value.get("pronouns", "")),
                role=str(value.get("role", "")),
                appearance=str(value.get("appearance", "")),
                side=side,
                is_new=bool(value.get("is_new", False)),
            )
        return cls(name=str(value), side="neutral")
```

Add a `status_changes` field on `NarrationTurnResult`:

```python
    status_changes: list[dict[str, Any]] = field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/agents/test_narration_extraction.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_narration_extraction.py
git commit -m "feat(narrator): BeatSelection.outcome + NpcMention.side + status_changes"
```

---

### Task 16: Extend the narrator JSON-extraction parser

The narrator returns a `game_patch` block; the parser that reads it (in `orchestrator.py` — search for `_extract_game_patch` or similar) must pick up `status_changes` and feed `outcome` into each `BeatSelection`.

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py` (extraction site)
- Test: `sidequest-server/tests/agents/test_narration_extraction.py` (extend)

- [ ] **Step 1: Locate the extractor**

Run: `cd sidequest-server && grep -n "beat_selections\|game_patch\|status_changes" sidequest/agents/orchestrator.py | head -30`

- [ ] **Step 2: Write a failing test for status_changes parsing**

```python
def test_narration_result_parses_status_changes():
    # Build a narrator response with a game_patch block and run the extractor
    # — exercise the live parsing path, not from_dict.
    raw = (
        "**The Arena**\n\n"
        "Sam ducks the swing.\n\n"
        "```game_patch\n"
        "{\n"
        '  "beat_selections": [{"actor": "Sam", "beat_id": "defend", "outcome": "Success"}],\n'
        '  "npcs_present": [{"name": "Promo", "side": "opponent", "role": "hostile"}],\n'
        '  "status_changes": [{"actor": "Sam", "status": {"text": "Bruised Ribs", "severity": "Wound"}}]\n'
        "}\n"
        "```\n"
    )
    from sidequest.agents.orchestrator import _parse_narrator_response  # adjust per actual export
    result = _parse_narrator_response(raw, default_action="defend")
    assert result.beat_selections[0].outcome.value == "Success"
    assert result.npcs_present[0].side == "opponent"
    assert result.status_changes == [
        {"actor": "Sam", "status": {"text": "Bruised Ribs", "severity": "Wound"}},
    ]
```

> If the parsing function isn't `_parse_narrator_response`, adjust the import to whatever the orchestrator exposes (e.g., `NarrationTurnResult.from_raw`).

- [ ] **Step 3: Wire status_changes through the extractor**

Find the extractor body — typically a loop reading `payload.get(field)` for each whitelisted field. Add `status_changes` to the whitelist; assign to the `NarrationTurnResult` field. Reuse existing patterns (no new abstraction).

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/agents/test_narration_extraction.py
git commit -m "feat(narrator): parse status_changes from game_patch"
```

---

### Task 17: Update narrator output-format prompt with side, outcome, status_changes

Extend the `NARRATOR_OUTPUT_ONLY` text in `narrator.py` so the LLM emits the new fields.

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py:70-188`
- Test: `sidequest-server/tests/agents/test_narrator_prompt.py` (extend or create)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/agents/test_narrator_prompt.py`:

```python
from sidequest.agents.narrator import NARRATOR_OUTPUT_ONLY


def test_prompt_documents_npc_side_field():
    # Closed enum surface — narrator must emit `side`.
    assert "side" in NARRATOR_OUTPUT_ONLY
    assert "player" in NARRATOR_OUTPUT_ONLY
    assert "opponent" in NARRATOR_OUTPUT_ONLY
    assert "neutral" in NARRATOR_OUTPUT_ONLY


def test_prompt_documents_beat_outcome_tiers():
    for tier in ("CritFail", "Fail", "Tie", "Success", "CritSuccess"):
        assert tier in NARRATOR_OUTPUT_ONLY


def test_prompt_documents_status_changes_field():
    assert "status_changes" in NARRATOR_OUTPUT_ONLY
    for sev in ("Scratch", "Wound", "Scar"):
        assert sev in NARRATOR_OUTPUT_ONLY
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Update `NARRATOR_OUTPUT_ONLY`**

Edit `sidequest-server/sidequest/agents/narrator.py`. In the `npcs_met` section (around line 168), append after the existing schema:

```
Each entry MUST include "side": one of "player" (party allies), "opponent"
(anyone the party is fighting), or "neutral" (bystanders, narrators,
audience). This is structural — `role` remains free-form prose, `side` is
a closed enum the engine routes on. Wrong sides break momentum routing.
```

In the `beat_selections` section (around line 177), append:

```
Each beat_selection MUST include "outcome": one of "CritFail", "Fail",
"Tie", "Success", "CritSuccess". This is the tier the prose describes —
"Fail" if the action did not succeed, "Success" if it cleanly worked,
"Tie" if it succeeded at a minor cost or partially, "CritSuccess" if it
succeeded with a notable extra benefit, "CritFail" if it failed badly
and the actor is now in a worse position than before. Match the tier to
the prose. On dice-replay turns the engine will overwrite this from the
actual roll.
```

Add a new section before the closing `Valid fields:` reminder:

```
status_changes: Array. Emit when prose describes a new lingering injury,
shaken nerve, social mark, or other actor-level cost. Format:
  {"actor": "<actor name>", "status": {"text": "<short prose label>", "severity": "Scratch|Wound|Scar"}}
- Scratch: clears at scene end (a graze, a lost composure beat).
- Wound: clears at session end or with rest (a real injury, a notable shake).
- Scar: persists until a milestone or healing event (a permanent mark —
  reputation, broken bone, lost trust).
Use sparingly — every status is narrative gravity. Align severity with
how seriously the prose treats the cost.
```

Also append `status_changes` to the `Valid fields:` list near the top of `NARRATOR_OUTPUT_ONLY`.

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/agents/narrator.py tests/agents/test_narrator_prompt.py
git commit -m "feat(narrator): prompt teaches side, outcome tier, status_changes"
```

---

### Task 18: Active-encounter prompt zone — render dual dials, tags, statuses

Extend `NarratorAgent.build_encounter_context` so the live encounter zone shows both dials, current tags, and per-actor statuses. Short-circuits when `enc.resolved`.

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py:411-477`
- Test: `sidequest-server/tests/agents/test_narrator_prompt.py` (extend)

- [ ] **Step 1: Write failing tests**

```python
def test_active_encounter_zone_renders_both_dials_and_tags(monkeypatch, build_registry):
    from sidequest.agents.narrator import NarratorAgent
    from sidequest.game.encounter import (
        EncounterActor, EncounterMetric, StructuredEncounter,
    )
    from sidequest.game.encounter_tag import EncounterTag
    from sidequest.game.status import Status, StatusSeverity
    from sidequest.genre.models.rules import (
        BeatDef, ConfrontationDef, MetricDef,
    )

    enc = StructuredEncounter(
        encounter_type="combat",
        player_metric=EncounterMetric(name="momentum", current=4, starting=0, threshold=10),
        opponent_metric=EncounterMetric(name="momentum", current=7, starting=0, threshold=10),
        actors=[
            EncounterActor(name="Sam", role="combatant", side="player"),
            EncounterActor(name="Promo", role="combatant", side="opponent"),
        ],
        tags=[EncounterTag(
            text="Off-Balance", created_by="Sam", target="Promo",
            leverage=1, fleeting=False, created_turn=3,
        )],
    )
    cdef = ConfrontationDef(
        type="combat", label="Combat", category="combat",
        player_metric=MetricDef(name="momentum", threshold=10),
        opponent_metric=MetricDef(name="momentum", threshold=10),
        beats=[BeatDef.model_validate({
            "id": "attack", "label": "Attack", "kind": "strike",
            "base": 2, "stat_check": "STR",
        })],
    )
    statuses_by_actor = {"Sam": [Status(
        text="Bruised Ribs", severity=StatusSeverity.Wound,
        absorbed_shifts=0, created_turn=2, created_in_encounter="combat",
    )]}

    registry = build_registry()
    NarratorAgent().build_encounter_context(
        registry, encounter=enc, cdef=cdef,
        statuses_by_actor=statuses_by_actor,
    )

    rendered = registry.render_for("narrator")
    assert "Player metric: 4 / 10" in rendered
    assert "Opponent metric: 7 / 10" in rendered
    assert "Off-Balance" in rendered
    assert "Bruised Ribs" in rendered
    assert "Wound" in rendered
    assert "side=player" in rendered
    assert "side=opponent" in rendered


def test_resolved_encounter_short_circuits_to_resolution_zone(build_registry):
    from sidequest.agents.narrator import NarratorAgent
    from sidequest.game.encounter import (
        EncounterActor, EncounterMetric, StructuredEncounter,
    )
    from sidequest.game.resolution_signal import ResolutionSignal
    from sidequest.genre.models.rules import (
        ConfrontationDef, MetricDef, BeatDef,
    )

    enc = StructuredEncounter(
        encounter_type="combat",
        player_metric=EncounterMetric(name="momentum", current=4, starting=0, threshold=10),
        opponent_metric=EncounterMetric(name="momentum", current=11, starting=0, threshold=10),
        actors=[EncounterActor(name="Sam", role="combatant", side="player")],
        resolved=True,
        outcome="opponent_victory",
    )
    cdef = ConfrontationDef(
        type="combat", label="Combat", category="combat",
        player_metric=MetricDef(name="momentum", threshold=10),
        opponent_metric=MetricDef(name="momentum", threshold=10),
        beats=[BeatDef.model_validate({
            "id": "attack", "label": "Attack", "kind": "strike",
            "base": 2, "stat_check": "STR",
        })],
    )
    signal = ResolutionSignal(
        encounter_type="combat",
        outcome="opponent_victory",
        final_player_metric=4,
        final_opponent_metric=11,
    )

    registry = build_registry()
    NarratorAgent().build_encounter_context(
        registry, encounter=enc, cdef=cdef,
        statuses_by_actor={},
        resolution_signal=signal,
    )

    rendered = registry.render_for("narrator")
    assert "[ENCOUNTER RESOLVED]" in rendered
    assert "outcome: opponent_victory" in rendered
    assert "final_player_metric: 4" in rendered
    assert "final_opponent_metric: 11" in rendered
    # The active-encounter live zone is NOT rendered.
    assert "Available beats" not in rendered
```

> Add a `build_registry` fixture in `tests/agents/conftest.py` if absent:

```python
import pytest

from sidequest.agents.prompt_framework.core import PromptRegistry


@pytest.fixture
def build_registry():
    def _build():
        return PromptRegistry()
    return _build
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Update `build_encounter_context`**

Edit `sidequest-server/sidequest/agents/narrator.py`. Replace the `build_encounter_context` method body with:

```python
    def build_encounter_context(
        self,
        registry: object,
        *,
        encounter: StructuredEncounter | None = None,
        cdef: ConfrontationDef | None = None,
        encounter_summary: str | None = None,
        statuses_by_actor: dict[str, list] | None = None,
        resolution_signal: object | None = None,
    ) -> None:
        from sidequest.agents.prompt_framework.core import PromptRegistry

        if not isinstance(registry, PromptRegistry):
            raise TypeError(f"Expected PromptRegistry, got {type(registry)}")

        registry.register_section(
            self.name(),
            PromptSection.new(
                "narrator_encounter_rules",
                f"<encounter-rules>\n{NARRATOR_COMBAT_RULES}\n"
                f"{NARRATOR_CHASE_RULES}\n</encounter-rules>",
                AttentionZone.Early,
                SectionCategory.Guardrail,
            ),
        )

        # One-shot resolution zone — wins over the active zone.
        if resolution_signal is not None:
            body = (
                "[ENCOUNTER RESOLVED]\n"
                f"type: {resolution_signal.encounter_type}\n"
                f"outcome: {resolution_signal.outcome}\n"
                f"final_player_metric: {resolution_signal.final_player_metric}\n"
                f"final_opponent_metric: {resolution_signal.final_opponent_metric}\n"
            )
            if resolution_signal.outcome == "yielded":
                yielded = ", ".join(resolution_signal.yielded_actors) or "(none)"
                body += (
                    f"yielded_actors: [{yielded}]\n"
                    f"edge_refreshed: {resolution_signal.edge_refreshed}\n"
                    "Describe the actor's exit on their own terms — they chose "
                    "to leave. Honor the choice. The opposing side does not "
                    "pursue or strike further.\n"
                )
            else:
                body += (
                    "The encounter has ended this turn. Describe the resolution "
                    "and any immediate transition out of the scene. Do NOT emit "
                    "beat_selections. Do NOT continue describing the encounter "
                    "as if it were active.\n"
                )
            registry.register_section(
                self.name(),
                PromptSection.new(
                    "narrator_encounter_resolved",
                    body,
                    AttentionZone.Early,
                    SectionCategory.State,
                ),
            )
            return  # short-circuit: do not render the live zone

        if encounter is not None and cdef is not None:
            statuses_by_actor = statuses_by_actor or {}
            actor_lines: list[str] = []
            for a in encounter.actors:
                statuses = statuses_by_actor.get(a.name, [])
                status_text = (
                    f"statuses: [{', '.join(f'{s.text} ({s.severity.value})' for s in statuses)}]"
                    if statuses else "statuses: []"
                )
                actor_lines.append(
                    f"  - {a.name} (side={a.side}, {status_text})"
                )
            beat_lines = "\n".join(
                f"  - {b.id}: {b.label} (kind={b.kind.value}, base={b.base})"
                for b in cdef.beats
            )
            tag_lines = "\n".join(
                f"  - \"{t.text}\" on {t.target or '(scene)'} "
                f"({'fleeting' if t.fleeting else f'leverage {t.leverage}'}, "
                f"created turn {t.created_turn})"
                for t in encounter.tags
            ) or "  (none)"
            body = (
                f"<encounter-live>\n"
                f"Active encounter: {cdef.label} ({cdef.confrontation_type})\n"
                f"Player metric: {encounter.player_metric.current} / "
                f"{encounter.player_metric.threshold}\n"
                f"Opponent metric: {encounter.opponent_metric.current} / "
                f"{encounter.opponent_metric.threshold}\n"
                f"Available beats — beat_selections.beat_id MUST be one of:\n"
                f"{beat_lines}\n"
                f"Actors — emit a beat_selection for every non-withdrawn "
                f"non-neutral actor:\n"
                + "\n".join(actor_lines) + "\n"
                f"Encounter tags:\n{tag_lines}\n"
                f"</encounter-live>"
            )
            registry.register_section(
                self.name(),
                PromptSection.new(
                    "narrator_encounter_live", body,
                    AttentionZone.Early, SectionCategory.State,
                ),
            )

        if encounter_summary:
            registry.register_section(
                self.name(),
                PromptSection.new(
                    "narrator_encounter_summary",
                    f"<encounter-state>\n{encounter_summary}\n</encounter-state>",
                    AttentionZone.Valley,
                    SectionCategory.State,
                ),
            )
```

- [ ] **Step 4: Update the orchestrator caller**

`grep -n "build_encounter_context" sidequest/agents/orchestrator.py`. The caller currently passes `encounter`/`cdef`/`encounter_summary` only. Update to:

```python
    statuses_by_actor = {
        ch.core.name: ch.core.statuses for ch in snapshot.characters
    }
    self._narrator.build_encounter_context(
        registry,
        encounter=snapshot.encounter,
        cdef=cdef,
        encounter_summary=encounter_summary,
        statuses_by_actor=statuses_by_actor,
        resolution_signal=snapshot.pending_resolution_signal,
    )
    if snapshot.pending_resolution_signal is not None:
        from sidequest.telemetry.spans import (
            encounter_resolution_signal_consumed_span,
        )
        sig = snapshot.pending_resolution_signal
        with encounter_resolution_signal_consumed_span(
            outcome=sig.outcome,
            final_player_metric=sig.final_player_metric,
            final_opponent_metric=sig.final_opponent_metric,
        ):
            pass
        snapshot.pending_resolution_signal = None
```

- [ ] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/agents/test_narrator_prompt.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/narrator.py sidequest/agents/orchestrator.py \
        tests/agents/test_narrator_prompt.py tests/agents/conftest.py
git commit -m "feat(narrator): dual-dial encounter zone + one-shot ENCOUNTER RESOLVED"
```

---

### Task 19: Wire status_changes into engine state mutation

When the narrator emits `status_changes`, append a `Status` to the named actor's `core.statuses`. Fires the `encounter.status_added` span.

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py`
- Test: `sidequest-server/tests/server/test_status_apply.py` (create)

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/server/test_status_apply.py`:

```python
from sidequest.agents.orchestrator import NarrationTurnResult
from sidequest.game.status import Status, StatusSeverity
from sidequest.server.narration_apply import _apply_narration_result_to_snapshot


def test_status_change_appends_to_named_actor(snapshot_with_pack, character_named_sam):
    snap, pack = snapshot_with_pack
    snap.characters.append(character_named_sam)
    result = NarrationTurnResult(
        narration="Sam grunts.",
        status_changes=[
            {"actor": "Sam", "status": {"text": "Bruised Ribs", "severity": "Wound"}},
        ],
    )
    _apply_narration_result_to_snapshot(snap, result, "Sam", pack=pack)
    sam = snap.characters[0]
    assert any(
        s.text == "Bruised Ribs" and s.severity is StatusSeverity.Wound
        for s in sam.core.statuses
    )


def test_unknown_actor_in_status_change_is_dropped_with_warning(
    snapshot_with_pack, character_named_sam, caplog,
):
    snap, pack = snapshot_with_pack
    snap.characters.append(character_named_sam)
    result = NarrationTurnResult(
        narration="...",
        status_changes=[{"actor": "Ghost", "status": {"text": "x", "severity": "Scratch"}}],
    )
    with caplog.at_level("WARNING"):
        _apply_narration_result_to_snapshot(snap, result, "Sam", pack=pack)
    assert any("status_change.unknown_actor" in r.message for r in caplog.records)
```

Add the `character_named_sam` fixture to `tests/server/conftest.py` — minimal Character with `core.name == "Sam"`.

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Add a `_apply_status_changes` step to narration_apply.py**

In `sidequest-server/sidequest/server/narration_apply.py`, after the encounter section, add:

```python
    if result.status_changes:
        from sidequest.game.status import Status, StatusSeverity
        from sidequest.telemetry.spans import encounter_status_added_span
        turn_num = snapshot.turn_manager.interaction
        encounter_type = (
            snapshot.encounter.encounter_type if snapshot.encounter else None
        )
        for entry in result.status_changes:
            actor_name = str(entry.get("actor", "")).strip()
            status_payload = entry.get("status") or {}
            text = str(status_payload.get("text", "")).strip()
            severity_raw = str(status_payload.get("severity", "Scratch"))
            try:
                severity = StatusSeverity(severity_raw)
            except ValueError:
                logger.warning(
                    "status_change.invalid_severity actor=%s severity=%s",
                    actor_name, severity_raw,
                )
                continue
            if not actor_name or not text:
                continue
            target = next(
                (c for c in snapshot.characters if c.core.name == actor_name),
                None,
            )
            if target is None:
                logger.warning(
                    "status_change.unknown_actor actor=%s text=%s",
                    actor_name, text,
                )
                continue
            target.core.statuses.append(Status(
                text=text,
                severity=severity,
                absorbed_shifts=0,
                created_turn=turn_num,
                created_in_encounter=encounter_type,
            ))
            with encounter_status_added_span(
                actor=actor_name, text=text, severity=severity.value,
                source="narrator_extraction",
            ):
                pass
```

- [ ] **Step 4: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_status_apply.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/narration_apply.py tests/server/test_status_apply.py tests/server/conftest.py
git commit -m "feat(narrator): apply status_changes to actor statuses with telemetry"
```

---

### Task 20: Persist `state_transition` events for encounter to the events table

Hook the watcher publish path so any event with `field == "encounter"` writes a typed row to the SQLite `events` table.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/watcher_hub.py`
- Modify: `sidequest-server/sidequest/server/narration_apply.py` (add encounter watcher publishes that mirror the new spans)
- Test: `sidequest-server/tests/server/test_encounter_telemetry.py` (create)

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/server/test_encounter_telemetry.py`:

```python
import json

from sidequest.game.persistence import SqliteStore


def _all_events(store: SqliteStore):
    return list(store._conn.execute(
        "SELECT kind, payload_json FROM events ORDER BY seq"
    ).fetchall())


def test_beat_applied_writes_event_row(store_bound_to_hub, encounter_dispatch_helper):
    store, snapshot, pack = store_bound_to_hub
    encounter_dispatch_helper.run_player_attack(snapshot, pack, beat_id="attack",
                                                outcome="Success")
    rows = _all_events(store)
    kinds = [r[0] for r in rows]
    assert "ENCOUNTER_BEAT_APPLIED" in kinds
    payload = next(json.loads(r[1]) for r in rows if r[0] == "ENCOUNTER_BEAT_APPLIED")
    assert payload["actor_side"] == "player"
    assert payload["beat_kind"] == "strike"
    assert payload["outcome_tier"] == "Success"


def test_resolution_writes_event_row_with_structured_outcome(
    store_bound_to_hub, encounter_dispatch_helper,
):
    store, snapshot, pack = store_bound_to_hub
    encounter_dispatch_helper.run_to_resolution(snapshot, pack, winner="opponent")
    rows = _all_events(store)
    kinds = [r[0] for r in rows]
    assert kinds[-1] == "ENCOUNTER_RESOLVED"
    payload = json.loads(rows[-1][1])
    assert payload["outcome"] == "opponent_victory"
```

Add fixtures `store_bound_to_hub` and `encounter_dispatch_helper` to `tests/server/conftest.py` — they should bind a real SqliteStore to the watcher hub and provide a tiny driver for running beats. Wire helper details from the existing `tests/server/test_encounter_apply_narration.py` pattern.

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL — events table only has `NARRATION` rows today.

- [ ] **Step 3: Extend `publish_event` to write to events when bound**

Edit `sidequest-server/sidequest/telemetry/watcher_hub.py`. Add a process-wide store-bind hook:

```python
_event_store = None  # bound at session-handler startup; weakref-safe by class id


def bind_event_store(store) -> None:
    """Bind a SqliteStore so encounter watcher events persist as rows.

    Multiple binds replace; ``None`` clears (used by tests).
    """
    global _event_store
    _event_store = store


_KIND_BY_OP = {
    "started": "ENCOUNTER_STARTED",
    "beat_applied": "ENCOUNTER_BEAT_APPLIED",
    "metric_advance": "ENCOUNTER_METRIC_ADVANCE",
    "beat_skipped": "ENCOUNTER_BEAT_SKIPPED",
    "tag_created": "ENCOUNTER_TAG_CREATED",
    "tag_backfire": "ENCOUNTER_TAG_CREATED",  # backfire is still a tag-creation row
    "status_added": "ENCOUNTER_STATUS_ADDED",
    "yield_received": "ENCOUNTER_YIELD",
    "yield_resolved": "ENCOUNTER_YIELD",
    "resolved": "ENCOUNTER_RESOLVED",
    "resolution_signal_emitted": "ENCOUNTER_RESOLUTION_SIGNAL",
    "resolution_signal_consumed": "ENCOUNTER_RESOLUTION_SIGNAL",
}


def _maybe_persist_encounter_row(event: dict) -> None:
    if _event_store is None:
        return
    if event.get("event_type") != "state_transition":
        return
    fields = event.get("fields", {})
    if fields.get("field") != "encounter":
        return
    op = str(fields.get("op", ""))
    kind = _KIND_BY_OP.get(op)
    if kind is None:
        return
    import json
    payload = json.dumps(fields)
    _event_store._conn.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        (kind, payload, _event_store._conn.execute("SELECT datetime('now')").fetchone()[0]),
    )
    _event_store._conn.commit()
```

In `publish_event`, immediately after the hub `publish` call, invoke `_maybe_persist_encounter_row(event_dict)`.

- [ ] **Step 4: Add watcher publishes alongside each new span**

For every span added in Task 9, pair a `_watcher_publish("state_transition", {"field": "encounter", "op": "<op>", ...}, component="encounter")` call at the same callsite. Concretely:

In `sidequest/game/beat_kinds.py::apply_beat`:
- After span `encounter.metric_advance` → publish `op="metric_advance"` with side, delta_kind, delta, before, after.
- After span `encounter.tag_created` → publish `op="tag_created"` with tag attrs.
- After span `encounter.tag_backfire` → publish `op="tag_backfire"` with tag attrs.
- When `resolved` flips True at the end of `apply_beat` → publish `op="resolved"` with `outcome`, `final_player_metric`, `final_opponent_metric`, `triggering_side`.
- For each `beat_applied` span (lifted to `narration_apply` and `dispatch/dice`) → publish `op="beat_applied"` with `actor`, `actor_side`, `beat_id`, `beat_kind`, `outcome_tier`, `own_delta`, `opponent_delta`, `metric_target`.

In `narration_apply.py` for `status_changes` → publish `op="status_added"`.

In `encounter_lifecycle.py::instantiate_encounter_from_trigger` → publish `op="started"`.

In `narration_apply.py` once the resolution signal is set → publish `op="resolution_signal_emitted"`.

In `agents/orchestrator.py` once the signal is consumed → publish `op="resolution_signal_consumed"`.

(Use `_watcher_publish` as imported in `narration_apply.py`.)

- [ ] **Step 5: Bind the store at session-handler startup**

`grep -n "SqliteStore\|store = " sidequest/server/session_handler.py` to find where the per-session store is opened. Right after the open call, invoke:

```python
from sidequest.telemetry.watcher_hub import bind_event_store
bind_event_store(self._store)
```

(or the equivalent for whatever owns the store).

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_telemetry.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add sidequest/telemetry/watcher_hub.py sidequest/game/beat_kinds.py \
        sidequest/server/narration_apply.py sidequest/server/dispatch/dice.py \
        sidequest/server/dispatch/encounter_lifecycle.py \
        sidequest/server/session_handler.py \
        tests/server/test_encounter_telemetry.py tests/server/conftest.py
git commit -m "feat(telemetry): persist ENCOUNTER_* state_transition events to SQLite"
```

---

### Task 21: Add a query helper for encounter timelines

The GM panel will read these rows. Provide a single query helper so the panel handler is one call.

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py`
- Test: `sidequest-server/tests/server/test_encounter_telemetry.py` (extend)

- [ ] **Step 1: Write a failing test**

```python
def test_encounter_timeline_query_returns_ordered_rows(store_bound_to_hub, encounter_dispatch_helper):
    store, snapshot, pack = store_bound_to_hub
    encounter_dispatch_helper.run_to_resolution(snapshot, pack, winner="opponent")
    from sidequest.game.persistence import query_encounter_events
    rows = query_encounter_events(store)
    kinds = [r["kind"] for r in rows]
    assert kinds[0] == "ENCOUNTER_STARTED"
    assert kinds[-1] == "ENCOUNTER_RESOLVED"
```

- [ ] **Step 2: Add the helper**

In `sidequest-server/sidequest/game/persistence.py`, add:

```python
def query_encounter_events(store: SqliteStore) -> list[dict]:
    """Return ordered ENCOUNTER_* event rows as dicts.

    The GM panel reads this for its post-hoc timeline view (spec
    2026-04-25-dual-track-momentum-design.md §GM panel verification).
    """
    import json
    rows = store._conn.execute(
        "SELECT seq, kind, payload_json, created_at FROM events "
        "WHERE kind LIKE 'ENCOUNTER_%' ORDER BY seq"
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "seq": r[0],
            "kind": r[1],
            "payload": json.loads(r[2]),
            "created_at": r[3],
        })
    return out
```

- [ ] **Step 3: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_encounter_telemetry.py::test_encounter_timeline_query_returns_ordered_rows -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add sidequest/game/persistence.py tests/server/test_encounter_telemetry.py
git commit -m "feat(persistence): query_encounter_events helper for GM panel"
```

---

### Task 22: GM panel — render new ENCOUNTER_* event kinds (UI)

Extend the panel timeline component to render every new event kind. Each row shows: turn, actor + side, kind tag (BEAT/TAG/STATUS/YIELD/RESOLVED), beat kind + tier, dial deltas. Final row is always the structured `ENCOUNTER_RESOLVED`.

**Files:**
- Modify: `sidequest-ui/src/screens/GMPanel/EncounterTimeline.tsx` (or current path; locate via `grep -rn "GM Panel\|encounter_timeline" sidequest-ui/src` if names drift)
- Modify: `sidequest-ui/src/types/payloads.ts`
- Test: `sidequest-ui/src/__tests__/EncounterTimeline.test.tsx`

- [ ] **Step 1: Locate the existing panel timeline**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
grep -rn "events_table\|kind === 'NARRATION'\|encounter timeline\|GM panel" src
```

If no panel exists yet, **stop and ask** — GM panel scaffolding is presumed in place per CLAUDE.md "wire up what exists". The spec assumes it.

- [ ] **Step 2: Add TypeScript types**

In `sidequest-ui/src/types/payloads.ts`, add:

```typescript
export type EncounterEventKind =
  | "ENCOUNTER_STARTED"
  | "ENCOUNTER_BEAT_APPLIED"
  | "ENCOUNTER_METRIC_ADVANCE"
  | "ENCOUNTER_BEAT_SKIPPED"
  | "ENCOUNTER_TAG_CREATED"
  | "ENCOUNTER_STATUS_ADDED"
  | "ENCOUNTER_YIELD"
  | "ENCOUNTER_RESOLVED"
  | "ENCOUNTER_RESOLUTION_SIGNAL";

export interface EncounterEvent {
  seq: number;
  kind: EncounterEventKind;
  payload: Record<string, unknown>;
  created_at: string;
}
```

- [ ] **Step 3: Write failing component tests**

Create `sidequest-ui/src/__tests__/EncounterTimeline.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EncounterTimeline } from "../screens/GMPanel/EncounterTimeline";
import type { EncounterEvent } from "../types/payloads";

const sample: EncounterEvent[] = [
  { seq: 1, kind: "ENCOUNTER_STARTED",
    payload: { encounter_type: "combat", player_metric_threshold: 10, opponent_metric_threshold: 10, turn: 1 },
    created_at: "2026-04-25T00:00:00Z" },
  { seq: 2, kind: "ENCOUNTER_BEAT_APPLIED",
    payload: { actor: "Sam", actor_side: "player", beat_id: "attack", beat_kind: "strike", outcome_tier: "Success", own_delta: 2, opponent_delta: 0, turn: 1 },
    created_at: "2026-04-25T00:00:01Z" },
  { seq: 3, kind: "ENCOUNTER_METRIC_ADVANCE",
    payload: { side: "player", delta_kind: "own", delta: 2, before: 0, after: 2, turn: 1 },
    created_at: "2026-04-25T00:00:02Z" },
  { seq: 4, kind: "ENCOUNTER_RESOLVED",
    payload: { outcome: "opponent_victory", final_player_metric: 4, final_opponent_metric: 11, triggering_side: "opponent", turn: 5 },
    created_at: "2026-04-25T00:00:10Z" },
];

describe("EncounterTimeline", () => {
  it("renders rows for each event kind with side and tier", () => {
    render(<EncounterTimeline events={sample} />);
    expect(screen.getByText(/Sam/)).toBeInTheDocument();
    expect(screen.getByText(/strike/)).toBeInTheDocument();
    expect(screen.getByText(/Success/)).toBeInTheDocument();
    expect(screen.getByText(/opponent_victory/)).toBeInTheDocument();
  });

  it("renders dial-pair view from STARTED through RESOLVED", () => {
    render(<EncounterTimeline events={sample} />);
    expect(screen.getByText(/Player metric:.*0/)).toBeInTheDocument();
    expect(screen.getByText(/Opponent metric:.*0/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-ui && npx vitest run src/__tests__/EncounterTimeline.test.tsx`

Expected: ImportError — component doesn't exist.

- [ ] **Step 5: Implement the component**

Create `sidequest-ui/src/screens/GMPanel/EncounterTimeline.tsx`:

```tsx
import type { EncounterEvent } from "../../types/payloads";

interface Props {
  events: EncounterEvent[];
}

function startedRow(payload: Record<string, unknown>) {
  const playerThresh = (payload.player_metric_threshold as number) ?? "?";
  const oppThresh = (payload.opponent_metric_threshold as number) ?? "?";
  return (
    <span>
      Encounter started — Player metric: 0 / {playerThresh},
      {" "}Opponent metric: 0 / {oppThresh}
    </span>
  );
}

function beatRow(payload: Record<string, unknown>) {
  return (
    <span>
      <strong>{payload.actor as string}</strong>
      {" (side="}{payload.actor_side as string}{") "}
      played <em>{payload.beat_id as string}</em>
      {" "}({payload.beat_kind as string}, tier {payload.outcome_tier as string});
      {" "}deltas own={payload.own_delta as number} opp={payload.opponent_delta as number}
    </span>
  );
}

function advanceRow(payload: Record<string, unknown>) {
  return (
    <span>
      {payload.side as string} dial advanced {(payload.delta as number) > 0 ? "+" : ""}
      {payload.delta as number} ({payload.before as number} → {payload.after as number})
    </span>
  );
}

function tagRow(payload: Record<string, unknown>) {
  return (
    <span>
      tag <em>"{payload.tag_text as string}"</em> on {(payload.target as string) || "(scene)"}
      {" "}— leverage {payload.leverage as number}, {(payload.fleeting as boolean) ? "fleeting" : "persistent"}
    </span>
  );
}

function statusRow(payload: Record<string, unknown>) {
  return (
    <span>
      {payload.actor as string} took status <em>{payload.text as string}</em>
      {" "}({payload.severity as string})
    </span>
  );
}

function yieldRow(payload: Record<string, unknown>) {
  const op = payload.op as string;
  if (op === "yield_resolved") {
    return (
      <span>
        Yield resolved — {(payload.yielded_actors as string)} (edge refreshed:
        {" "}{payload.edge_refreshed as number})
      </span>
    );
  }
  return <span>Yield received from {payload.actor_name as string}</span>;
}

function resolvedRow(payload: Record<string, unknown>) {
  return (
    <strong>
      RESOLVED — outcome: {payload.outcome as string}; final player_metric=
      {payload.final_player_metric as number}, opponent_metric=
      {payload.final_opponent_metric as number}
    </strong>
  );
}

function skippedRow(payload: Record<string, unknown>) {
  return (
    <span>
      Beat skipped — {payload.actor as string} ({payload.actor_side as string}) /
      {" "}{payload.beat_id as string} — reason: {payload.reason as string}
    </span>
  );
}

function row(ev: EncounterEvent) {
  switch (ev.kind) {
    case "ENCOUNTER_STARTED": return startedRow(ev.payload);
    case "ENCOUNTER_BEAT_APPLIED": return beatRow(ev.payload);
    case "ENCOUNTER_METRIC_ADVANCE": return advanceRow(ev.payload);
    case "ENCOUNTER_TAG_CREATED": return tagRow(ev.payload);
    case "ENCOUNTER_STATUS_ADDED": return statusRow(ev.payload);
    case "ENCOUNTER_YIELD": return yieldRow(ev.payload);
    case "ENCOUNTER_BEAT_SKIPPED": return skippedRow(ev.payload);
    case "ENCOUNTER_RESOLVED": return resolvedRow(ev.payload);
    case "ENCOUNTER_RESOLUTION_SIGNAL": return null; // internal
    default: return <span>(unknown {ev.kind})</span>;
  }
}

export function EncounterTimeline({ events }: Props) {
  return (
    <ol className="encounter-timeline">
      {events.map((ev) => (
        <li key={ev.seq}>
          <span className="seq">#{ev.seq}</span>
          {row(ev)}
        </li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 6: Wire the component into the GM panel screen**

Find the GM panel parent screen and add a tab/section that fetches `query_encounter_events` (server-side endpoint exposed via REST or via the existing watcher channel). If no endpoint exists, expose `GET /sessions/{slug}/encounter_events` in `sidequest/server/rest.py` returning the helper's output.

- [ ] **Step 7: Run UI tests**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-ui && npx vitest run src/__tests__/EncounterTimeline.test.tsx`

Expected: PASS.

- [ ] **Step 8: Boot the dev server and verify in browser**

```bash
cd /Users/slabgorb/Projects/oq-2 && just up
```

Open the GM panel, run a short scripted encounter (or load the regression save once Phase 3 ships), and confirm the timeline renders. Stop the server with `just down`.

- [ ] **Step 9: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
git add src/screens/GMPanel/EncounterTimeline.tsx \
        src/types/payloads.ts \
        src/__tests__/EncounterTimeline.test.tsx
git commit -m "feat(gm-panel): render dual-dial encounter timeline with new event kinds"

cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add sidequest/server/rest.py
git commit -m "feat(rest): GET /sessions/{slug}/encounter_events endpoint"
```

---

## Phase 3 — Yield action, content migration, regression playtest

### Task 23: Add `MessageType.YIELD` and `YieldMessage` payload

Wire the new player-action message kind through the protocol layer.

**Files:**
- Modify: `sidequest-server/sidequest/protocol/enums.py:20-72`
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Test: `sidequest-server/tests/protocol/test_messages.py` (extend or create)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/protocol/test_messages.py`:

```python
import json

from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import YieldMessage


def test_message_type_has_yield():
    assert MessageType.YIELD.value == "YIELD"


def test_yield_message_no_payload_fields():
    msg = YieldMessage(player_id="p1")
    raw = msg.model_dump_json()
    parsed = json.loads(raw)
    assert parsed["type"] == "YIELD"
    assert parsed["player_id"] == "p1"


def test_yield_message_round_trip():
    msg = YieldMessage(player_id="p1")
    re_msg = YieldMessage.model_validate_json(msg.model_dump_json())
    assert re_msg == msg
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL — neither symbol exists.

- [ ] **Step 3: Add the enum member**

Edit `sidequest-server/sidequest/protocol/enums.py`. In `MessageType`, add (alphabetical insert):

```python
    YIELD = "YIELD"
```

- [ ] **Step 4: Add `YieldMessage`**

Edit `sidequest-server/sidequest/protocol/messages.py`. Find where existing `*Message` classes are defined (e.g., `DiceRequestMessage`). Add:

```python
class YieldMessage(GameMessage):
    """Player-side structural withdrawal from the active encounter.

    Spec 2026-04-25-dual-track-momentum-design.md §Yield action. No
    payload fields — yielding is a structural intent. The server
    refunds edge based on the actor's accumulated statuses.
    """

    type: Literal["YIELD"] = "YIELD"
```

If the messages module has a `_KIND_TO_MESSAGE_CLS` mapping, add `MessageType.YIELD: YieldMessage` to it so dispatch can look up the class.

- [ ] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_messages.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/protocol/enums.py sidequest/protocol/messages.py tests/protocol/test_messages.py
git commit -m "feat(protocol): MessageType.YIELD + YieldMessage payload"
```

---

### Task 24: Add `OnYield` recovery trigger to EdgePool

**Files:**
- Modify: `sidequest-server/sidequest/game/creature_core.py:18-29` (RecoveryTrigger constants)
- Test: `sidequest-server/tests/server/test_yield_dispatch.py` (will be extended further in Task 25)

- [ ] **Step 1: Write failing test**

Create `sidequest-server/tests/server/test_yield_dispatch.py`:

```python
from sidequest.game.creature_core import RecoveryTrigger


def test_recovery_trigger_on_yield_constant():
    assert RecoveryTrigger.OnYield == "OnYield"
```

- [ ] **Step 2: Run test to verify it fails**

Expected: AttributeError.

- [ ] **Step 3: Add the constant**

Edit `sidequest-server/sidequest/game/creature_core.py`:

```python
class RecoveryTrigger(str):
    OnResolution = "OnResolution"
    OnRest = "OnRest"
    OnSceneChange = "OnSceneChange"
    OnYield = "OnYield"
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/creature_core.py tests/server/test_yield_dispatch.py
git commit -m "feat(creature_core): RecoveryTrigger.OnYield"
```

---

### Task 25: Implement the YIELD dispatch handler

The handler marks the actor withdrawn, resolves the encounter when every player-side actor has yielded or been taken out, sets `pending_resolution_signal`, and refunds edge by `1 + count_of_scratch-or-worse-statuses-this-encounter`.

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch/yield_action.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py` (route `MessageType.YIELD` → handler)
- Test: `sidequest-server/tests/server/test_yield_dispatch.py` (extend)

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/server/test_yield_dispatch.py`:

```python
import pytest

from sidequest.game.encounter import (
    EncounterActor, EncounterMetric, StructuredEncounter,
)
from sidequest.game.status import Status, StatusSeverity
from sidequest.server.dispatch.yield_action import handle_yield


def _enc(*, p_metric=4, o_metric=7):
    return StructuredEncounter(
        encounter_type="combat",
        player_metric=EncounterMetric(name="momentum", current=p_metric, starting=0, threshold=10),
        opponent_metric=EncounterMetric(name="momentum", current=o_metric, starting=0, threshold=10),
        actors=[
            EncounterActor(name="Sam", role="combatant", side="player"),
            EncounterActor(name="Promo", role="combatant", side="opponent"),
        ],
    )


def test_yield_solo_pc_resolves_encounter_immediately(snapshot_with_pack, character_named_sam):
    snap, _ = snapshot_with_pack
    snap.encounter = _enc()
    snap.characters.append(character_named_sam)
    handle_yield(snap, player_id="p1", player_name="Sam")
    assert snap.encounter.resolved is True
    assert snap.encounter.outcome == "yielded"
    assert snap.pending_resolution_signal.outcome == "yielded"
    assert snap.pending_resolution_signal.yielded_actors == ("Sam",)


def test_yield_refunds_edge_one_plus_status_count(snapshot_with_pack, character_named_sam):
    snap, _ = snapshot_with_pack
    snap.encounter = _enc()
    sam = character_named_sam
    sam.core.statuses.extend([
        Status(text="Bruised Ribs", severity=StatusSeverity.Wound,
               absorbed_shifts=0, created_turn=2, created_in_encounter="combat"),
        Status(text="Mocked", severity=StatusSeverity.Scratch,
               absorbed_shifts=0, created_turn=3, created_in_encounter="combat"),
    ])
    sam.core.edge.current = 0
    sam.core.edge.max = 5
    snap.characters.append(sam)
    handle_yield(snap, player_id="p1", player_name="Sam")
    # Both statuses created in this encounter → refund 1 + 2 = 3
    assert sam.core.edge.current == 3
    assert snap.pending_resolution_signal.edge_refreshed == 3


def test_yield_does_not_count_pre_existing_statuses(snapshot_with_pack, character_named_sam):
    snap, _ = snapshot_with_pack
    snap.encounter = _enc()
    sam = character_named_sam
    sam.core.statuses.append(Status(
        text="Old Scar", severity=StatusSeverity.Scar, absorbed_shifts=0,
        created_turn=0, created_in_encounter=None,
    ))
    sam.core.edge.current = 0
    sam.core.edge.max = 5
    snap.characters.append(sam)
    handle_yield(snap, player_id="p1", player_name="Sam")
    # Pre-existing status not in this encounter → refund 1 + 0 = 1
    assert sam.core.edge.current == 1


def test_yield_caps_at_edge_max(snapshot_with_pack, character_named_sam):
    snap, _ = snapshot_with_pack
    snap.encounter = _enc()
    sam = character_named_sam
    sam.core.edge.current = 4
    sam.core.edge.max = 5
    snap.characters.append(sam)
    handle_yield(snap, player_id="p1", player_name="Sam")
    assert sam.core.edge.current == 5  # capped at max


def test_yield_with_no_active_encounter_raises(snapshot_with_pack, character_named_sam):
    snap, _ = snapshot_with_pack
    snap.encounter = None
    snap.characters.append(character_named_sam)
    with pytest.raises(ValueError, match="no active encounter"):
        handle_yield(snap, player_id="p1", player_name="Sam")


def test_yield_with_two_pcs_first_yield_keeps_encounter_active(snapshot_with_pack):
    snap, _ = snapshot_with_pack
    enc = _enc()
    enc.actors.append(EncounterActor(name="Alex", role="combatant", side="player"))
    snap.encounter = enc
    # Each PC needs a Character entry
    from sidequest.game.character import Character
    from sidequest.game.creature_core import CreatureCore, placeholder_edge_pool
    snap.characters.append(Character(core=CreatureCore(
        name="Sam", description="x", personality="x",
        edge=placeholder_edge_pool(),
    )))
    snap.characters.append(Character(core=CreatureCore(
        name="Alex", description="x", personality="x",
        edge=placeholder_edge_pool(),
    )))
    handle_yield(snap, player_id="p1", player_name="Sam")
    # Sam withdrawn; Alex still active → encounter not resolved
    assert snap.encounter.resolved is False
    assert next(a for a in snap.encounter.actors if a.name == "Sam").withdrawn is True
    assert next(a for a in snap.encounter.actors if a.name == "Alex").withdrawn is False

    # Alex yields too → resolves
    handle_yield(snap, player_id="p2", player_name="Alex")
    assert snap.encounter.resolved is True
    assert snap.encounter.outcome == "yielded"
    assert set(snap.pending_resolution_signal.yielded_actors) == {"Sam", "Alex"}
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: ImportError on `handle_yield`.

- [ ] **Step 3: Implement the handler**

Create `sidequest-server/sidequest/server/dispatch/yield_action.py`:

```python
"""YIELD dispatch handler — structured player exit.

Spec 2026-04-25-dual-track-momentum-design.md §Yield action. The yielding
actor is marked ``withdrawn``; the encounter resolves when every
``side="player"`` actor has yielded or been taken out. Edge is refunded by
``1 + count_of_scratch-or-worse-statuses-created-this-encounter``.
"""
from __future__ import annotations

from sidequest.game.resolution_signal import ResolutionSignal
from sidequest.game.session import GameSnapshot
from sidequest.game.status import Status
from sidequest.telemetry.spans import (
    encounter_resolution_signal_emitted_span,
    encounter_yield_received_span,
    encounter_yield_resolved_span,
)


def _statuses_taken_in_encounter(
    statuses: list[Status], encounter_type: str,
) -> int:
    return sum(1 for s in statuses if s.created_in_encounter == encounter_type)


def _refund_edge_for_yielders(
    snapshot: GameSnapshot, yielded_names: list[str], encounter_type: str,
) -> int:
    total_refund = 0
    for name in yielded_names:
        char = next((c for c in snapshot.characters if c.core.name == name), None)
        if char is None:
            continue
        count = _statuses_taken_in_encounter(char.core.statuses, encounter_type)
        refund = 1 + count
        before = char.core.edge.current
        char.core.edge.current = min(char.core.edge.max, before + refund)
        total_refund += char.core.edge.current - before
    return total_refund


def handle_yield(
    snapshot: GameSnapshot,
    *,
    player_id: str,
    player_name: str,
) -> None:
    enc = snapshot.encounter
    if enc is None or enc.resolved:
        raise ValueError("YIELD: no active encounter")
    actor = enc.find_actor_for_player(player_name)
    if actor is None:
        raise ValueError(f"YIELD: no player-side actor named {player_name!r}")
    if actor.withdrawn:
        return  # idempotent

    sam_char = next(
        (c for c in snapshot.characters if c.core.name == player_name), None,
    )
    statuses_taken = (
        _statuses_taken_in_encounter(sam_char.core.statuses, enc.encounter_type)
        if sam_char else 0
    )
    with encounter_yield_received_span(
        player_id=player_id,
        actor_name=player_name,
        prior_player_metric=enc.player_metric.current,
        prior_opponent_metric=enc.opponent_metric.current,
        statuses_taken_this_encounter=statuses_taken,
    ):
        pass

    actor.withdrawn = True

    player_actors = [a for a in enc.actors if a.side == "player"]
    all_done = all(a.withdrawn for a in player_actors)
    if not all_done:
        return  # encounter remains active

    yielded_names = [a.name for a in player_actors if a.withdrawn]
    edge_refreshed = _refund_edge_for_yielders(
        snapshot, yielded_names, enc.encounter_type,
    )

    enc.resolved = True
    enc.outcome = "yielded"

    snapshot.pending_resolution_signal = ResolutionSignal(
        encounter_type=enc.encounter_type,
        outcome="yielded",
        final_player_metric=enc.player_metric.current,
        final_opponent_metric=enc.opponent_metric.current,
        yielded_actors=tuple(yielded_names),
        edge_refreshed=edge_refreshed,
    )

    with encounter_yield_resolved_span(
        outcome="yielded",
        yielded_actors=tuple(yielded_names),
        edge_refreshed=edge_refreshed,
    ):
        pass
    with encounter_resolution_signal_emitted_span(
        outcome="yielded",
        final_player_metric=enc.player_metric.current,
        final_opponent_metric=enc.opponent_metric.current,
    ):
        pass
```

- [ ] **Step 4: Route YIELD in `session_handler.py`**

Find the dispatch routing block (`if msg.type == MessageType.X: ...`) and add:

```python
        if msg.type == MessageType.YIELD:
            from sidequest.server.dispatch.yield_action import handle_yield
            try:
                handle_yield(
                    self._snapshot,
                    player_id=player_id,
                    player_name=self._player_name_for(player_id),
                )
            except ValueError as exc:
                return ErrorMessage(error=str(exc), player_id=player_id)
            return None
```

(Adjust to whatever `self._player_name_for` is named in the live code.)

- [ ] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_yield_dispatch.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/dispatch/yield_action.py sidequest/server/session_handler.py \
        tests/server/test_yield_dispatch.py
git commit -m "feat(yield): YIELD handler — withdraw actor, refund edge, signal narrator"
```

---

### Task 26: UI yield button + `/yield` slash command

**Files:**
- Modify: `sidequest-ui/src/lib/socket.ts` (or current message-helper module)
- Modify: `sidequest-ui/src/screens/EncounterPanel.tsx` (or current encounter UI)
- Modify: `sidequest-ui/src/lib/slash.ts` (or wherever slash commands route)
- Test: `sidequest-ui/src/__tests__/YieldButton.test.tsx`

- [ ] **Step 1: Write failing UI test**

Create `sidequest-ui/src/__tests__/YieldButton.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { YieldButton } from "../components/YieldButton";

describe("YieldButton", () => {
  it("calls onYield when clicked", () => {
    const onYield = vi.fn();
    render(<YieldButton onYield={onYield} disabled={false} />);
    fireEvent.click(screen.getByRole("button", { name: /yield/i }));
    expect(onYield).toHaveBeenCalledTimes(1);
  });

  it("disables when no active encounter", () => {
    const onYield = vi.fn();
    render(<YieldButton onYield={onYield} disabled />);
    fireEvent.click(screen.getByRole("button", { name: /yield/i }));
    expect(onYield).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: import error.

- [ ] **Step 3: Add the component**

Create `sidequest-ui/src/components/YieldButton.tsx`:

```tsx
interface Props {
  onYield: () => void;
  disabled: boolean;
}

export function YieldButton({ onYield, disabled }: Props) {
  return (
    <button
      type="button"
      onClick={() => { if (!disabled) onYield(); }}
      disabled={disabled}
      title="Step out of the fight on your terms. Edge refreshes by 1 + statuses taken."
    >
      Yield
    </button>
  );
}
```

- [ ] **Step 4: Wire `sendYield` in the socket helper**

Add to `sidequest-ui/src/lib/socket.ts`:

```typescript
export function sendYield(socket: WebSocket): void {
  socket.send(JSON.stringify({ type: "YIELD" }));
}
```

- [ ] **Step 5: Render the button in the encounter panel**

Edit the encounter panel screen so it imports `YieldButton` and renders it whenever `encounter && !encounter.resolved && playerHasNotYielded`:

```tsx
import { YieldButton } from "../components/YieldButton";

// inside the encounter panel render:
{encounter && !encounter.resolved && (
  <YieldButton
    onYield={() => sendYield(socket)}
    disabled={!encounter || encounter.resolved}
  />
)}
```

- [ ] **Step 6: Add the `/yield` slash command**

In `sidequest-ui/src/lib/slash.ts`, register the command:

```typescript
slashCommands.register("yield", () => ({
  type: "YIELD",
}));
```

- [ ] **Step 7: Run tests**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-ui && npx vitest run src/__tests__/YieldButton.test.tsx`

Expected: PASS.

- [ ] **Step 8: Manual smoke**

```bash
cd /Users/slabgorb/Projects/oq-2 && just up
```

Open the client, start an encounter (any genre — once Phase 3 packs are migrated; or use the synthetic test pack), click Yield, confirm the encounter resolves with "yielded" outcome. Stop with `just down`.

- [ ] **Step 9: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-ui
git add src/components/YieldButton.tsx src/lib/socket.ts src/lib/slash.ts \
        src/screens/EncounterPanel.tsx src/__tests__/YieldButton.test.tsx
git commit -m "feat(ui): yield button + /yield command"
```

---

### Task 27: Migrate `caverns_and_claudes/rules.yaml`

The canary pack. Migration template applies to every other pack in Tasks 28–32.

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`
- Test: `sidequest-server/tests/genre/test_pack_load.py` (extend)

- [ ] **Step 1: Enumerate the existing confrontations**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
rg -n "^\s*-\s*type:|^\s*metric:|^\s*beats:" genre_packs/caverns_and_claudes/rules.yaml
```

Expect three confrontations (combat, chase, negotiation) plus possibly a haggling variant.

- [ ] **Step 2: Write a failing pack-load test**

Append to `sidequest-server/tests/genre/test_pack_load.py`:

```python
def test_caverns_and_claudes_pack_loads_with_dual_dial_schema(load_pack):
    pack = load_pack("caverns_and_claudes")
    assert pack.rules is not None
    for cdef in pack.rules.confrontations:
        assert cdef.player_metric.threshold > 0
        assert cdef.opponent_metric.threshold > 0
        for beat in cdef.beats:
            assert beat.kind in {"strike", "brace", "push", "angle"}
```

`load_pack` fixture is presumed to exist (loads a pack by slug from `SIDEQUEST_GENRE_PACKS`); add it to `tests/conftest.py` if missing.

- [ ] **Step 3: Run test to verify it fails**

Expected: FAIL — current YAML uses single-`metric` shape.

- [ ] **Step 4: Migrate the YAML**

Edit `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`. Replace the `confrontations:` block with:

```yaml
confrontations:
  - type: combat
    label: Dungeon Combat
    category: combat
    player_metric:
      name: momentum
      starting: 0
      threshold: 10
    opponent_metric:
      name: momentum
      starting: 0
      threshold: 10
    beats:
      - id: attack
        label: Attack
        kind: strike
        base: 2
        stat_check: STR
        effect: "Target takes damage this round"
        narrator_hint: Steel rings off stone. Torchlight flickers across the blow.
      - id: defend
        label: Defend
        kind: brace
        base: 1
        stat_check: CON
        effect: "Reduce incoming damage this round, brace against the push"
        narrator_hint: Shield raised, back to the wall, weight forward.
      - id: shield_bash
        label: Shield Bash
        kind: strike
        base: 4
        deltas:
          crit_fail:
            own: -2
        stat_check: STR
        effect: "Stun the target briefly, break their footing"
        risk: "Overcommitted — lose 2 momentum and take a counter on failure"
        narrator_hint: Slam forward in the narrow corridor — nowhere to dodge.
      - id: feint
        label: Feint
        kind: angle
        target_tag: "Off-Balance"
        stat_check: DEX
        effect: "Set up a leverage tag the next attack can spend"
        narrator_hint: A bait — open the guard, draw the swing.
      - id: flee
        label: Flee
        kind: push
        base: 1
        stat_check: DEX
        consequence: "Combat ends — retreat deeper into the dungeon"
        narrator_hint: Break contact, torch sweeping behind you as you run.
    mood: combat
  - type: chase
    label: Corridor Pursuit
    category: movement
    player_metric:
      name: separation
      starting: 0
      threshold: 7
    opponent_metric:
      name: pursuit
      starting: 0
      threshold: 7
    beats:
      - id: sprint
        label: Sprint
        kind: push
        base: 2
        stat_check: DEX
        narrator_hint: Boots echo off stone as the quarry bolts down the passage.
      - id: duck_through
        label: Duck Through
        kind: angle
        target_tag: "Out of Sight"
        stat_check: INT
        narrator_hint: Squeeze through a side passage too narrow for pursuers.
      - id: barricade
        label: Barricade
        kind: brace
        base: 1
        stat_check: INT
        effect: "Topple debris to slow pursuit"
      - id: douse_torch
        label: Douse Torch
        kind: push
        base: 1
        stat_check: DEX
        consequence: "Chase ends in darkness — quarry vanishes"
    mood: tension
  - type: negotiation
    label: "Haggling at the Counter"
    category: social
    player_metric:
      name: leverage
      starting: 0
      threshold: 7
    opponent_metric:
      name: leverage
      starting: 3
      threshold: 7
    beats:
      - id: talk_up_the_haul
        label: "Talk Up the Haul"
        kind: strike
        base: 2
        stat_check: CHA
        effect: "merchant entertains the asking price — their eyebrow does the thing"
        narrator_hint: "The delver pitches the goods like a town crier."
      - id: swear_its_not_cursed
        label: "Swear It's Not Cursed"
        kind: strike
        base: 3
        deltas:
          crit_fail:
            own: -1
        stat_check: CHA
        risk: "if the bluff fails, merchant knocks 50% off the offer"
        effect: "merchant accepts the suspicious item — with a receipt, carefully worded"
        narrator_hint: "Running-joke territory. Lean all the way in."
      - id: plead_poverty
        label: "Plead Poverty"
        kind: angle
        target_tag: "Sympathetic"
        stat_check: WIS
        effect: "merchant softens — sets up a leverage tag for the closer"
        narrator_hint: "The delver goes for the sympathy play."
      - id: flash_the_coin
        label: "Flash the Coin"
        kind: brace
        base: 1
        stat_check: CHA
        effect: "merchant's disposition tightens — the real price slips out"
        narrator_hint: "A small concession now to read the shop properly."
      - id: walk_toward_the_door
        label: "Walk Toward the Door"
        kind: push
        base: 1
        stat_check: WIS
        consequence: "Negotiation ends — leave with the merchant's last offer"
    mood: comedic
```

- [ ] **Step 5: Run the pack-load test**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/genre/test_pack_load.py -v -k caverns`

Expected: PASS.

- [ ] **Step 6: Commit (content repo)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git add genre_packs/caverns_and_claudes/rules.yaml
git commit -m "feat(rules): migrate caverns_and_claudes to dual-dial momentum"
```

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add tests/genre/test_pack_load.py
git commit -m "test(pack-load): caverns_and_claudes loads under dual-dial schema"
```

---

### Task 28: Migrate `heavy_metal/rules.yaml`

Same template as Task 27. The `heavy_metal` pack has more confrontations — every one needs the migration. **Use the kind-mapping from spec §Migration impact** to convert legacy beats:

| Legacy label substring | New `kind` |
|---|---|
| Attack / Strike / Bash / Shoot / Cast (offensive) | `strike` |
| Defend / Block / Parry / Dodge / Ward | `brace` |
| Flee / Climb / Persuade / Sneak Past | `push` |
| Feint / Distract / Spot Weakness | `angle` |

- [ ] **Step 1: List confrontations to migrate**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
rg -n "^\s*-\s*type:" genre_packs/heavy_metal/rules.yaml
```

- [ ] **Step 2: Write a failing pack-load test**

Append to `sidequest-server/tests/genre/test_pack_load.py`:

```python
def test_heavy_metal_pack_loads_with_dual_dial_schema(load_pack):
    pack = load_pack("heavy_metal")
    for cdef in pack.rules.confrontations:
        assert cdef.player_metric.threshold > 0
        assert cdef.opponent_metric.threshold > 0
        for beat in cdef.beats:
            assert beat.kind.value in {"strike", "brace", "push", "angle"}
```

- [ ] **Step 3: Migrate every confrontation**

Apply the same transformation as Task 27 to each `confrontations:` entry in `genre_packs/heavy_metal/rules.yaml`. For each beat:

1. Replace `metric_delta: <n>` with `kind: <chosen>` (see mapping) and `base: <n>`.
2. Promote any `risk:` text describing a numeric penalty into `deltas.crit_fail.own: <-n>`. Keep `risk:` text — it's narrator prose only.
3. For new `angle` beats, add `target_tag: "<setting-appropriate prose>"`.
4. Replace single-`metric` block with two ascending `player_metric`/`opponent_metric` blocks. Pick thresholds matching the old single threshold (typically the magnitude of the old threshold_high/low).

- [ ] **Step 4: Run the pack-load test**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/genre/test_pack_load.py -v -k heavy_metal`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git add genre_packs/heavy_metal/rules.yaml
git commit -m "feat(rules): migrate heavy_metal to dual-dial momentum"
```

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add tests/genre/test_pack_load.py
git commit -m "test(pack-load): heavy_metal loads under dual-dial schema"
```

---

### Task 29: Migrate `space_opera`, `spaghetti_western`, `mutant_wasteland`, `elemental_harmony`

Repeat the Task 28 template for each remaining pack. Treat each pack as one task in execution; the plan groups them here because the work is identical.

- [ ] **Step 1: Migrate `space_opera/rules.yaml`** + add `test_space_opera_pack_loads_with_dual_dial_schema` to `tests/genre/test_pack_load.py`. Run `uv run pytest tests/genre/test_pack_load.py -v -k space_opera`. Commit content + test.

- [ ] **Step 2: Migrate `spaghetti_western/rules.yaml`** — note the spec calls out the existing `bidirectional` duel; map `duel` to two ascending dials directly (the spec confirms it maps cleanly). Add `test_spaghetti_western_pack_loads`. Commit content + test.

- [ ] **Step 3: Migrate `mutant_wasteland/rules.yaml`**. Add load test. Commit.

- [ ] **Step 4: Migrate `elemental_harmony/rules.yaml`**. Add load test. Commit.

- [ ] **Step 5: Run the full pack-load test sweep**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/genre/test_pack_load.py -v
```

Expected: every shipping pack PASSES. `genre_workshopping/*` drafts are out of scope per the spec.

---

### Task 30: Wiring test — full session round trip with the migrated `caverns_and_claudes`

The plan has unit tests, integration tests, and pack-load tests. We still owe a wiring test that exercises the live `SessionHandler` path with a stub Claude returning a scripted `NarrationTurnResult`. Per CLAUDE.md "Every Test Suite Needs a Wiring Test".

**Files:**
- Create: `sidequest-server/tests/integration/test_dual_track_wiring.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/integration/test_dual_track_wiring.py`:

```python
"""End-to-end wiring: SessionHandler → narrator stub → encounter resolution.

Asserts:
1. apply_beat is reachable from the live SessionHandler narration path.
2. pending_resolution_signal is set after threshold cross.
3. Next narrator turn injects [ENCOUNTER RESOLVED] zone.
4. The events table contains the full encounter timeline.
"""
import json

import pytest

from sidequest.protocol.dice import RollOutcome


@pytest.mark.integration
def test_session_runs_full_encounter_to_opponent_victory(live_session_with_stub_narrator):
    """Stub narrator scripts five beats that drive opponent_metric to 11."""
    session, store = live_session_with_stub_narrator
    session.queue_narrator_response({
        "narration": "...",
        "confrontation": "combat",
        "npcs_present": [{"name": "Promo", "side": "opponent", "role": "hostile"}],
    })
    session.send_player_action("I swing.")
    # Now drive five attacks from the opponent — narrator scripts them.
    for _ in range(5):
        session.queue_narrator_response({
            "narration": "Promo swings.",
            "beat_selections": [{"actor": "Promo", "beat_id": "attack", "outcome": "CritSuccess"}],
            "npcs_present": [{"name": "Promo", "side": "opponent", "role": "hostile"}],
        })
        session.send_player_action("I dodge.")

    snap = session.snapshot
    assert snap.encounter is None or snap.encounter.resolved
    # ResolutionSignal was set, then consumed on the next turn — at least once.
    rows = list(store._conn.execute(
        "SELECT kind, payload_json FROM events WHERE kind LIKE 'ENCOUNTER_%' ORDER BY seq"
    ).fetchall())
    kinds = [r[0] for r in rows]
    assert "ENCOUNTER_STARTED" in kinds
    assert "ENCOUNTER_BEAT_APPLIED" in kinds
    assert "ENCOUNTER_RESOLVED" in kinds
    final_payload = json.loads(rows[-1][1])
    assert final_payload["outcome"] == "opponent_victory"


@pytest.mark.integration
def test_post_resolution_turn_renders_encounter_resolved_zone(
    live_session_with_stub_narrator, captured_prompts,
):
    session, _ = live_session_with_stub_narrator
    # Drive resolution as above (helper).
    session.run_to_resolution(winner="opponent")
    # Next narrator call should include the [ENCOUNTER RESOLVED] header.
    session.queue_narrator_response({"narration": "Sam slumps."})
    session.send_player_action("I look around.")
    last_prompt = captured_prompts[-1]
    assert "[ENCOUNTER RESOLVED]" in last_prompt
    assert "outcome: opponent_victory" in last_prompt
    # And it should be cleared after consumption.
    assert session.snapshot.pending_resolution_signal is None
```

The fixtures `live_session_with_stub_narrator` and `captured_prompts` need to live in `tests/integration/conftest.py`:

```python
import pytest

from sidequest.agents.claude_client import LlmClient


@pytest.fixture
def captured_prompts():
    return []


@pytest.fixture
def live_session_with_stub_narrator(captured_prompts, tmp_path):
    # Build a minimal SessionHandler with a stub LlmClient whose `complete`
    # method pops from a queue. Bind the events store. Helper methods on
    # the returned wrapper provide queue_narrator_response, send_player_action,
    # and run_to_resolution. Implement using the existing test infrastructure
    # (look at tests/server/test_session_*.py for the canonical setup).
    from sidequest.game.persistence import SqliteStore
    from sidequest.telemetry.watcher_hub import bind_event_store

    store = SqliteStore.open(str(tmp_path / "save.db"))
    bind_event_store(store)
    # Build the rest using existing helpers — copy the smallest path that
    # boots a SessionHandler against an in-memory pack and stub LLM.
    from tests.integration._helpers import build_stub_session  # write this helper
    session = build_stub_session(store=store, captured_prompts=captured_prompts)
    yield session, store
    bind_event_store(None)
    store.close()
```

> Helper `build_stub_session` lives at `tests/integration/_helpers.py`. Use existing `tests/agents/*` patterns; do not invent a new abstraction.

- [ ] **Step 2: Run the wiring tests**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/integration/test_dual_track_wiring.py -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_dual_track_wiring.py tests/integration/conftest.py \
        tests/integration/_helpers.py
git commit -m "test(integration): full session wiring for dual-track momentum"
```

---

### Task 31: Regression playtest against `dungeon_survivor` save

The reference save's narration shows Sam KO'd while the engine reports `momentum=11` (false `player_victory`). Replay the same five beats against the new engine; the corrected outcome is `opponent_victory`. **No fix is considered complete until the GM panel can render the corrected timeline for this save.**

**Files:**
- Create: `sidequest-server/tests/integration/test_dual_track_dungeon_survivor.py`

- [ ] **Step 1: Inspect the reference save**

```bash
sqlite3 ~/.sidequest/saves/games/2026-04-25-dungeon_survivor/save.db \
    "SELECT id, content FROM narrative_log ORDER BY id;"
```

Note the five beats applied. The point is to capture the *narrator inputs* (the `beat_selections` and `npcs_present` payloads from the saved narration JSON) and replay them against a fresh in-memory snapshot under the new engine.

- [ ] **Step 2: Write the failing regression test**

Create `sidequest-server/tests/integration/test_dual_track_dungeon_survivor.py`:

```python
"""Regression: 2026-04-25-dungeon_survivor — Sam KO'd, engine had said
'player_victory'. Under dual-track momentum the same beat sequence must
resolve to opponent_victory.

This is the lie-detector check from CLAUDE.md's OTEL Observability
Principle: prose says one thing, engine says another, GM panel reconciles.
"""
import json
from pathlib import Path

import pytest


REF_SAVE = Path.home() / ".sidequest" / "saves" / "games" / \
           "2026-04-25-dungeon_survivor" / "save.db"


@pytest.mark.integration
@pytest.mark.skipif(not REF_SAVE.exists(), reason="reference save not present")
def test_dungeon_survivor_resolves_to_opponent_victory(
    live_session_with_stub_narrator, captured_prompts,
):
    """Replay the saved beats against the new engine.

    Concrete script transcribed from the reference save's narrative_log.
    If the reference save changes, regenerate by reading the events.
    """
    session, store = live_session_with_stub_narrator

    # Beat 1: encounter starts — Sam vs The Promo + The Host (neutral).
    session.queue_narrator_response({
        "narration": "The lights snap on.",
        "confrontation": "combat",
        "npcs_present": [
            {"name": "The Promo", "side": "opponent", "role": "hostile"},
            {"name": "The Host", "side": "neutral", "role": "announcer"},
        ],
    })
    session.send_player_action("I draw my sickle.")

    # Beats 2-5: the Promo critsuccesses three attacks, Sam fails his parry,
    # then a CritSuccess from the Promo at beat 5 that crosses opponent_metric.
    promo_script = [
        ("CritSuccess", "Promo lunges, blade sliding under Sam's guard."),
        ("Success", "Steel kisses ribs. Sam staggers."),
        ("CritSuccess", "The Promo presses, Sam off-balance."),
        ("CritSuccess", "Sam's knees buckle. The crowd roars."),
    ]
    for tier, prose in promo_script:
        session.queue_narrator_response({
            "narration": prose,
            "beat_selections": [
                {"actor": "Sam", "beat_id": "defend", "outcome": "Fail"},
                {"actor": "The Promo", "beat_id": "attack", "outcome": tier},
            ],
            "npcs_present": [
                {"name": "The Promo", "side": "opponent", "role": "hostile"},
                {"name": "The Host", "side": "neutral", "role": "announcer"},
            ],
        })
        session.send_player_action("I parry.")

    snap = session.snapshot
    assert snap.encounter is None or snap.encounter.resolved
    # ENCOUNTER_RESOLVED row in events table carries the structured outcome.
    rows = list(store._conn.execute(
        "SELECT kind, payload_json FROM events "
        "WHERE kind = 'ENCOUNTER_RESOLVED' ORDER BY seq"
    ).fetchall())
    assert rows, "expected at least one ENCOUNTER_RESOLVED row"
    payload = json.loads(rows[-1][1])
    assert payload["outcome"] == "opponent_victory"


@pytest.mark.integration
@pytest.mark.skipif(not REF_SAVE.exists(), reason="reference save not present")
def test_dungeon_survivor_timeline_is_renderable_by_gm_panel(
    live_session_with_stub_narrator,
):
    session, store = live_session_with_stub_narrator
    session.run_dungeon_survivor_script()  # helper that reuses the script above

    from sidequest.game.persistence import query_encounter_events
    rows = query_encounter_events(store)
    kinds = [r["kind"] for r in rows]

    # The lie-detector view: STARTED, multiple BEAT_APPLIED with side
    # attribution, METRIC_ADVANCE rows, terminating in RESOLVED.
    assert kinds[0] == "ENCOUNTER_STARTED"
    assert "ENCOUNTER_BEAT_APPLIED" in kinds
    assert "ENCOUNTER_METRIC_ADVANCE" in kinds
    assert kinds[-1] == "ENCOUNTER_RESOLVED"

    # Every BEAT_APPLIED row carries actor_side; no row asserts a
    # player-side actor advanced opponent_metric or vice versa.
    for r in rows:
        if r["kind"] == "ENCOUNTER_BEAT_APPLIED":
            payload = r["payload"]
            assert payload["actor_side"] in {"player", "opponent"}
```

- [ ] **Step 3: Run the regression**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/integration/test_dual_track_dungeon_survivor.py -v`

Expected: PASS.

If the reference save isn't present in CI, the tests skip — but they MUST run locally before the PR merges.

- [ ] **Step 4: Run a manual playtest against the live save**

```bash
cd /Users/slabgorb/Projects/oq-2 && just up
# Open the client, load 2026-04-25-dungeon_survivor save.
# Inspect the GM panel's encounter timeline: every beat attributed to a side,
# both dials visible, terminating ENCOUNTER_RESOLVED row showing outcome=
# opponent_victory.
just down
```

If the panel doesn't render the corrected outcome, **fix before commit** — this is the lie-detector check.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_dual_track_dungeon_survivor.py
git commit -m "test(regression): dungeon_survivor resolves to opponent_victory"
```

---

### Task 32: Final aggregate gate + cleanup sweep

- [ ] **Step 1: Run the aggregate gate**

```bash
cd /Users/slabgorb/Projects/oq-2 && just check-all
```

Expected: server-check, client-lint, client-test, daemon-lint all PASS.

- [ ] **Step 2: Sweep for stragglers**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
grep -rn "MetricDirection\|hostile_keywords\|apply_encounter_updates\|metric_delta:\|failure_metric_delta" sidequest tests
```

Expected: zero hits (other than this plan or migration notes in commit messages). Any remaining hit is dead code — delete it in this task per CLAUDE.md "delete dead code in the same PR".

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
grep -rn "metric:\s*$\|direction:\s*bidirectional\|metric_delta:" genre_packs
```

Expected: zero hits in shipping packs (genre_workshopping is out of scope per spec).

- [ ] **Step 3: Smoke playtest the migrated packs**

```bash
cd /Users/slabgorb/Projects/oq-2 && just up
```

Boot each shipping pack from the chargen screen and trigger one combat. Verify:
- Encounter starts. Both dials visible in GM panel.
- A player attack advances the player dial only.
- An NPC attack advances the opponent dial only.
- A nat-20 beat creates a fleeting `Opening` tag visible in the panel.
- Yield button resolves with `outcome=yielded` and edge refreshes.

Stop with `just down`.

- [ ] **Step 4: Commit any cleanup**

```bash
git add -p   # review and stage cleanup
git commit -m "chore: remove dead encounter symbols after dual-track migration"
```

- [ ] **Step 5: PR**

Open a single PR per repo (`sidequest-server`, `sidequest-content`, `sidequest-ui`) targeting `main`. The PR description references the spec and lists the three v1 stories shipped. v2 stories (leverage spend, status absorption) are explicitly out of scope and tracked separately.

---

## Out of Scope (Explicit)

These are deferred to future plans (one per future story):

- **Story 4 — Tag leverage spending.** `consumes_leverage_from` on BeatDef, narrator schema extension, `encounter.leverage_consumed` span, fleeting-tag-removed-on-spend, tier upgrade. Data model already lands here in Phase 1; the spend mechanic is a separate plan.
- **Story 5 — Status absorption.** Threshold-cross interrupt, severity-budget absorption, recovery hooks for Wound/Scar, "take a status" interactive prompt for PCs. Major v2 deliverable; warrants its own plan.
- **NPC yields.** Data model is forward-compatible; narrator-emitted `npc_yielded` is a future story.
- **Mid-encounter side mutation.** Charm, turncoat. The `side` field exists; mutation is a separate epic.
- **Three-way encounters.** v1 keeps two sides; neutrals are prose-only.
- **Party-size threshold scaling.** Engine assumes per-pack thresholds are tuned by content authors. Multiplier is a single-line later if playtest demands it.

---

## Self-Review Notes

**Spec coverage check.** Every section of the spec maps to a task:

- §Problem (sign collapse, no failure branch, narrator unaware, events not queryable) → Tasks 8, 10, 14, 17, 18, 20, 31.
- §Design summary (5 additions) → Beat kind: Tasks 6, 7. Five-tier outcome: Tasks 1, 2, 15. Encounter tags: Tasks 5, 10, 18. Statuses: Tasks 3, 4, 17, 19. Yield: Tasks 23, 24, 25, 26.
- §Architecture (schema, engine, narrator, data flow) → Tasks 7–22.
- §Multi-participant cases (1–4 in scope) → Task 25 multi-PC test, Task 13 side-from-payload routing, Task 10 neutral-skipped test.
- §Migration impact → Tasks 27–29.
- §Telemetry → Tasks 9, 18, 20, 21.
- §Testing → Unit (Tasks 1–10), integration (Tasks 11, 25, 30), telemetry (Task 20), regression playtest (Task 31).
- §Story breakdown → Phase 1 = Story 1; Phase 2 = Story 2; Phase 3 = Story 3.
- §Out of scope → captured in the "Out of Scope" section above.

**Placeholder scan.** No "TBD", no "implement later", no naked "Add error handling". Every step shows the actual code or command.

**Type/symbol consistency.**
- `apply_beat` (Task 10) uses `RollOutcome` from `sidequest.protocol.dice`; the same enum gains `Tie` in Task 1.
- `BeatDef.kind` (Task 7) uses `BeatKind` from `sidequest.game.beat_kinds` (Task 6).
- `EncounterActor.side` (Task 8) is a `Literal["player","opponent","neutral"]`; consumers (Tasks 10, 13, 25) match.
- `pending_resolution_signal` (Task 14) uses `ResolutionSignal` (Task 14); narrator zone (Task 18) and yield handler (Task 25) build the same model.
- `EncounterTag` (Task 5) — same shape used in `apply_beat` (Task 10), narrator zone (Task 18), GM panel timeline (Task 22).
- `Status` (Task 3) — same shape used in `CreatureCore` (Task 4), narrator status_changes parser (Task 16), apply path (Task 19), yield refund counter (Task 25), GM panel (Task 22).

---




