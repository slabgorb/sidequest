# Free-for-all N-seat Table Model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a general free-for-all N-seat confrontation resolution mode (poker as the proving instance, auction as the second) so the whole table can act each round, simultaneously, against each other — over real dealt hands with abstracted betting.

**Architecture:** Three additive changes behind the ADR-117 ruleset seam, mirroring the ADR-077 dogfight playbook. (1) `StructuredEncounter` gains one optional `table_state: TableState | None` field; the dual dials go unused for table types. (2) A new `ResolutionMode.table_resolution` + `WinCondition.table_showdown` + a `table_game` discriminator on `ConfrontationDef`. (3) A generic table engine (`game/table/`) dispatched per-`game_kind` through a small fail-loud registry, reached behind a `resolve_table`/`deal_table` seam on `RulesetModule`. A new **exclusive** branch in `narration_apply.py` (peer to the `sealed_letter_lookup` branch) routes per-seat commits to the engine and never falls through to `apply_beat` (double-apply guard). Per-seat hands stay secret until showdown via the existing perception firewall pointed at `table_state`.

**Tech Stack:** Python 3.12 / pydantic v2 / FastAPI server. Tests: pytest (`uv run pytest`, parallel `-n auto` by default; use `-n0` for serial debugging). Lint/format: `uv run ruff`. Type check: `uv run pyright`. All server commands run from `sidequest-server/`.

---

## Plan refinements over the spec (Architect notes)

Read these before starting; they are deliberate, spec-faithful refinements made during planning:

1. **Resolver home.** The spec says "`resolve_table(...)` method on `RulesetModule` (default in `native.py`)." Table resolution is genre-general and orthogonal to combat resolution, so to stay DRY (reuse-first) the real logic lives in free functions under `game/table/` (engine + per-kind modules), and `RulesetModule` **base** (`base.py`) gets two thin concrete methods (`deal_table`, `resolve_table`) that delegate to the engine. This gives every ruleset (native, swn, cwn) table support without duplication. native remains the reference binding (spaghetti_western poker + tea_and_murder auction both bind `ruleset: native`). This is a placement refinement, not a behavior change.
2. **Commit channel — `amount` slot.** The spec reuses `beat_selections` and notes "a params slot for raise amount." `BeatSelection` (`agents/orchestrator.py:257`) currently has no amount field; this plan adds an optional `amount: int | None = None`. The existing `target: str | None` field carries the Read/Accuse target seat.
3. **Barrier denominator.** The spec says folded seats "reuse the `effective_barrier_count` crash-release machinery." The crash-release set (`_crash_released`) is cleared **every interaction** (`session_room.py:776`), but a folded seat must stay out for the remaining decision points of the *hand* (multiple interactions). So this plan adds a **parallel** set `_table_folded_player_ids` that `effective_barrier_count` also subtracts, cleared at confrontation teardown — reusing the *pattern*, not the exact set.

---

## File Structure

**New files (server, `sidequest-server/sidequest/`):**

- `game/table/__init__.py` — package marker, re-exports public types.
- `game/table/types.py` — `TableSeat`, `TablePot`, `TableState` (pydantic models); `TableCommit`, `TableResolutionOutcome`, `CheatResult`, `ReadResult` (frozen dataclasses); `TableNeedsOthersError`. One responsibility: the data shapes shared by the engine and the kinds.
- `game/table/registry.py` — `TableGame` ABC + `register_table_game` / `get_table_game` + `UnknownTableGameError`. Fail-loud kind dispatch.
- `game/table/poker.py` — `PokerTableGame`: deal real 5-card hands, compute strength + band, Cheat, Read. Registered as `"poker"`.
- `game/table/auction.py` — `AuctionTableGame`: assign secret valuations, Read-the-Room. Registered as `"auction"`. Proves the model is the general free-for-all (zero model changes).
- `game/table/npc_policy.py` — `decide_npc_commit(...)`: NPC seat auto-commit over (strength_band, pot, OCEAN/disposition).
- `game/table/engine.py` — `deal_table(...)` and `resolve_table(...)`: the decision-point loop logic (fold/bet/raise/call pot mechanics, Cheat/Read/Accuse sub-loop, showdown). Emits spans. Genre-general; dispatches kind-specifics via the registry.
- `telemetry/spans/table.py` — the 8 `table.*` spans + `SpanRoute`s + `@contextmanager` factories.

**Modified files (server):**

- `game/encounter.py` — add `table_state` field to `StructuredEncounter`.
- `genre/models/rules.py` — `ResolutionMode.table_resolution`, `WinCondition.table_showdown`, `ConfrontationDef.table_game` + validators.
- `game/ruleset/base.py` — `deal_table` / `resolve_table` concrete methods.
- `telemetry/spans/__init__.py` — `from .table import *`.
- `agents/orchestrator.py` — `BeatSelection.amount` field + `from_dict` parse.
- `server/dispatch/encounter_lifecycle.py` — table instantiation/seat/deal branch.
- `server/narration_apply.py` — new exclusive `table_resolution` branch (~2685).
- `server/dispatch/confrontation.py` — per-seat private projection in the frame supplier.
- `server/session_room.py` — `_table_folded_player_ids` barrier integration.

**Modified files (content, `sidequest-content/genre_packs/`):**

- `spaghetti_western/rules.yaml` — poker confrontation → table_resolution.
- `tea_and_murder/rules.yaml` — auction confrontation → table_resolution.

**New test files (server, `sidequest-server/tests/`):**

- `game/table/test_types.py`, `game/table/test_poker.py`, `game/table/test_engine.py`, `game/table/test_cheat_read_accuse.py`, `game/table/test_npc_policy.py`, `game/table/test_auction.py`, `game/table/test_registry.py`
- `game/ruleset/test_resolve_table_seam.py`
- `game/test_encounter_table_state.py`
- `genre/test_table_resolution_schema.py`
- `telemetry/test_table_spans.py`
- `server/dispatch/test_table_instantiation.py`
- `server/dispatch/test_table_perception_firewall.py`
- `server/test_table_resolution_wiring.py` (the required end-to-end wiring test)
- `server/test_table_barrier_denominator.py`
- `genre/test_poker_table_content.py`, `genre/test_auction_table_content.py`

---

## Phase A — Data model & schema (no behavior)

### Task 1: Table state models + shared value types

**Files:**
- Create: `sidequest/game/table/__init__.py`
- Create: `sidequest/game/table/types.py`
- Test: `tests/game/table/__init__.py` (empty), `tests/game/table/test_types.py`

- [ ] **Step 1: Create the test package marker**

Create `tests/game/table/__init__.py` as an empty file (pytest package marker — mirrors `tests/server/dispatch/__init__.py`).

```python
```

- [ ] **Step 2: Write the failing test**

Create `tests/game/table/test_types.py`:

```python
import pytest
from pydantic import ValidationError

from sidequest.game.table.types import (
    TableNeedsOthersError,
    TablePot,
    TableResolutionOutcome,
    TableSeat,
    TableState,
)


def _seat(seat_id: str, party: str, *, is_pc: bool = True) -> TableSeat:
    return TableSeat(
        seat_id=seat_id,
        party_name=party,
        is_pc=is_pc,
        status="active",
        private_state={},
    )


def _state(n: int = 2) -> TableState:
    seats = [_seat(f"seat_{i}", f"P{i}") for i in range(1, n + 1)]
    return TableState(
        game_kind="poker",
        seats=seats,
        pot=TablePot(
            stake_kind="money",
            stake_descriptor="the pot",
            contributions={s.seat_id: 0 for s in seats},
        ),
        order=[s.seat_id for s in seats],
        dealer_seat=seats[0].seat_id,
        max_decision_points=3,
    )


def test_table_state_round_trips_and_defaults():
    st = _state(3)
    assert st.decision_point == 0
    assert st.resolved_winner is None
    # round-trip through pydantic serialization
    rebuilt = TableState.model_validate(st.model_dump())
    assert rebuilt == st


def test_extra_field_forbidden_on_seat():
    with pytest.raises(ValidationError):
        TableSeat(
            seat_id="seat_1",
            party_name="P1",
            is_pc=True,
            status="active",
            private_state={},
            bogus="x",
        )


def test_seat_status_literal_rejects_unknown():
    with pytest.raises(ValidationError):
        TableSeat(
            seat_id="seat_1",
            party_name="P1",
            is_pc=True,
            status="dancing",
            private_state={},
        )


def test_active_seat_ids_helper():
    st = _state(3)
    st.seats[1].status = "folded"
    assert st.active_seat_ids() == ["seat_1", "seat_3"]


def test_find_seat_helper():
    st = _state(2)
    assert st.find_seat("seat_2").party_name == "P2"
    assert st.find_seat("nope") is None


def test_table_needs_others_error_is_value_error():
    assert issubclass(TableNeedsOthersError, ValueError)


def test_resolution_outcome_holds_award():
    out = TableResolutionOutcome(
        showdown=True,
        resolved_winner="seat_1",
        pot_awarded_to="seat_1",
        stake_kind="money",
        stake_descriptor="the pot",
        narration_hint="seat_1 rakes the pot",
        forfeited_seats=["seat_2"],
    )
    assert out.showdown is True
    assert out.pot_awarded_to == "seat_1"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/game/table/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.table'`.

- [ ] **Step 4: Create the package marker**

Create `sidequest/game/table/__init__.py`:

```python
"""Free-for-all N-seat table resolution (poker / auction).

The general model (seats + pot + order) lives in ``types``; per-game-kind
behavior (deal, strength, cheat, read) is registered in ``registry`` and
implemented in ``poker`` / ``auction``; the decision-point loop is in
``engine``. See docs/superpowers/specs/2026-05-29-free-for-all-n-seat-table-design.md.
"""

from __future__ import annotations

from sidequest.game.table.types import (
    TableNeedsOthersError,
    TablePot,
    TableResolutionOutcome,
    TableSeat,
    TableState,
)

__all__ = [
    "TableNeedsOthersError",
    "TablePot",
    "TableResolutionOutcome",
    "TableSeat",
    "TableState",
]
```

- [ ] **Step 5: Write the models**

Create `sidequest/game/table/types.py`:

```python
"""Data shapes for the free-for-all N-seat table model.

The pydantic models are the *general* free-for-all: seats, a pot, and a
resolution order. ``private_state`` is an opaque dict the kind-specific
resolver interprets (poker hand vs auction valuation) — this is what lets
poker and auction share one model. Ephemeral: a TableState is a single
dramatic hand, never persisted across hands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field


class TableNeedsOthersError(ValueError):
    """Raised when a table would seat fewer than 2 parties (generalizes ADR-116).

    No solitaire table — fail loud rather than instantiate a one-seat hand.
    """


class TableSeat(BaseModel):
    model_config = {"extra": "forbid"}

    seat_id: str  # stable: "seat_1"…
    party_name: str  # maps to an EncounterActor (PC or NPC)
    is_pc: bool
    status: Literal["active", "folded", "out"]
    private_state: dict[str, Any]
    #   poker   → {"cards": [...], "strength": int, "strength_band": str, "cheat_trace": float}
    #   auction → {"valuation": int, "max_bid": int}


class TablePot(BaseModel):
    model_config = {"extra": "forbid"}

    stake_kind: str  # "money" | "item" | "information" | "favor" (content-declared)
    stake_descriptor: str  # "the deed to the Bar-T" — narration label
    contributions: dict[str, int]  # seat_id → abstract chips (money); current high bid (auction)


class TableState(BaseModel):
    model_config = {"extra": "forbid"}

    game_kind: str  # "poker" | "auction" — resolver dispatch
    seats: list[TableSeat]
    pot: TablePot
    order: list[str]  # seat_ids in resolution/narration order
    dealer_seat: str
    decision_point: int = 0
    max_decision_points: int  # abstracted betting — small (e.g. 3), content-declared
    resolved_winner: str | None = None
    # Accusations are recorded when committed but RESOLVED at showdown (rolled
    # against the FINAL cheat_trace) so a cheat in a later decision point is still
    # catchable. (accuser_seat_id, target_seat_id). See engine._showdown.
    pending_accusations: list[tuple[str, str]] = Field(default_factory=list)

    def find_seat(self, seat_id: str) -> TableSeat | None:
        for s in self.seats:
            if s.seat_id == seat_id:
                return s
        return None

    def active_seat_ids(self) -> list[str]:
        """Seat ids still in the hand, in resolution order."""
        active = {s.seat_id for s in self.seats if s.status == "active"}
        return [sid for sid in self.order if sid in active]


@dataclass(frozen=True)
class TableCommit:
    """One seat's sealed action for a decision point.

    Generalizes the dogfight sealed-letter commit from "keyed by role" to
    "keyed by seat". Rides the existing ``beat_selections`` channel: ``seat_id``
    is the actor's party→seat mapping, ``beat_id`` the authored action,
    ``amount`` the raise/bet chips, ``target_seat`` the Read/Accuse target.
    """

    seat_id: str
    beat_id: str  # "bet"|"raise"|"call"|"fold"|"bluff"|"cheat"|"read_table"|"accuse" (poker)
    amount: int = 0
    target_seat: str | None = None


@dataclass(frozen=True)
class CheatResult:
    strength_before: int
    strength_after: int
    new_trace: float


@dataclass(frozen=True)
class ReadResult:
    target_seat: str
    info: dict[str, Any]  # injected into the reader's next private frame


@dataclass
class TableResolutionOutcome:
    """Result of resolving ONE decision point (and showdown, when it triggers)."""

    showdown: bool
    resolved_winner: str | None
    pot_awarded_to: str | None
    stake_kind: str | None
    stake_descriptor: str | None
    narration_hint: str
    forfeited_seats: list[str] = field(default_factory=list)
    # Per-reader Read results to inject into the next private frame, keyed by seat_id.
    read_results: dict[str, ReadResult] = field(default_factory=dict)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/game/table/test_types.py -v`
Expected: PASS (7 tests).

- [ ] **Step 7: Lint + commit**

```bash
uv run ruff check sidequest/game/table/ tests/game/table/ && uv run ruff format sidequest/game/table/ tests/game/table/
git add sidequest/game/table/__init__.py sidequest/game/table/types.py tests/game/table/
git commit -m "feat(table): add free-for-all N-seat state models + value types"
```

---

### Task 2: Wire `table_state` onto StructuredEncounter

**Files:**
- Modify: `sidequest/game/encounter.py:155` (add field after `win_condition`) and the `win_condition` Literal
- Test: `tests/game/test_encounter_table_state.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/test_encounter_table_state.py`:

```python
from sidequest.game.encounter import EncounterMetric, StructuredEncounter
from sidequest.game.table.types import TablePot, TableSeat, TableState


def _enc(**kw) -> StructuredEncounter:
    base = dict(
        encounter_type="poker",
        player_metric=EncounterMetric(name="player", threshold=10),
        opponent_metric=EncounterMetric(name="opponent", threshold=10),
    )
    base.update(kw)
    return StructuredEncounter(**base)


def test_table_state_defaults_none():
    enc = _enc()
    assert enc.table_state is None


def test_table_state_round_trips():
    seats = [
        TableSeat(seat_id="seat_1", party_name="P1", is_pc=True, status="active", private_state={}),
        TableSeat(seat_id="seat_2", party_name="P2", is_pc=False, status="active", private_state={}),
    ]
    ts = TableState(
        game_kind="poker",
        seats=seats,
        pot=TablePot(stake_kind="money", stake_descriptor="pot", contributions={"seat_1": 0, "seat_2": 0}),
        order=["seat_1", "seat_2"],
        dealer_seat="seat_1",
        max_decision_points=3,
    )
    enc = _enc(win_condition="table_showdown", table_state=ts)
    rebuilt = StructuredEncounter.model_validate(enc.model_dump())
    assert rebuilt.table_state is not None
    assert rebuilt.table_state.game_kind == "poker"
    assert rebuilt.win_condition == "table_showdown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_encounter_table_state.py -v`
Expected: FAIL — `StructuredEncounter` has no `table_state` field (`extra="forbid"` rejects it), and `win_condition` Literal rejects `"table_showdown"`.

- [ ] **Step 3: Add the field and extend the win_condition Literal**

In `sidequest/game/encounter.py`, add the import near the top (after line 17, the `from sidequest.protocol.models import ...` line):

```python
from sidequest.game.table.types import TableState
```

Then change the `win_condition` Literal (currently `encounter.py:155`):

```python
    win_condition: Literal["dial_threshold", "hp_depletion", "table_showdown"] = "dial_threshold"
```

Then add the field immediately after `win_condition` (before `player_metric` at line 156):

```python
    # Free-for-all N-seat table (poker / auction). None for every non-table
    # confrontation — the dual dials go unused for table types; the resolver
    # reads table_state, not the metrics. See
    # docs/superpowers/specs/2026-05-29-free-for-all-n-seat-table-design.md.
    table_state: TableState | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_encounter_table_state.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the encounter regression slice**

Run: `uv run pytest tests/game/ -k "encounter" -q`
Expected: PASS (no regression from the new optional field / widened Literal).

- [ ] **Step 6: Commit**

```bash
uv run ruff check sidequest/game/encounter.py
git add sidequest/game/encounter.py tests/game/test_encounter_table_state.py
git commit -m "feat(table): add optional table_state field + table_showdown win_condition to StructuredEncounter"
```

---

### Task 3: ConfrontationDef schema — table_resolution mode, table_showdown, table_game

**Files:**
- Modify: `sidequest/genre/models/rules.py:325` (`ResolutionMode`), `:306` (`WinCondition`), `:432` area (`ConfrontationDef` field + validator)
- Test: `tests/genre/test_table_resolution_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tests/genre/test_table_resolution_schema.py`:

```python
import pytest

from sidequest.genre.models.rules import (
    BeatDef,
    ConfrontationDef,
    ResolutionMode,
    WinCondition,
)


def _table_cdef(**kw) -> ConfrontationDef:
    base = dict(
        type="poker",
        label="Poker",
        category="social",
        resolution_mode=ResolutionMode.table_resolution,
        win_condition=WinCondition.table_showdown,
        table_game="poker",
        max_decision_points=3,
        beats=[BeatDef(id="fold", label="Fold", stat_check="WIS", base=0)],
    )
    base.update(kw)
    return ConfrontationDef(**base)


def test_table_resolution_mode_exists():
    assert ResolutionMode("table_resolution") is ResolutionMode.table_resolution


def test_table_showdown_win_condition_exists():
    assert WinCondition("table_showdown") is WinCondition.table_showdown


def test_table_confrontation_does_not_require_dials():
    # table_showdown must NOT trip the dial_threshold metric requirement
    cdef = _table_cdef()
    assert cdef.player_metric is None
    assert cdef.opponent_metric is None
    assert cdef.table_game == "poker"
    assert cdef.max_decision_points == 3


def test_table_resolution_requires_table_game():
    with pytest.raises(ValueError, match="table_game"):
        _table_cdef(table_game=None)


def test_table_resolution_requires_positive_decision_points():
    with pytest.raises(ValueError, match="max_decision_points"):
        _table_cdef(max_decision_points=0)


def test_non_table_confrontation_leaves_table_game_none():
    cdef = ConfrontationDef(
        type="brawl",
        label="Brawl",
        category="combat",
        win_condition=WinCondition.hp_depletion,
        opponent_default_stats={"hp": 8, "armor_class": 12},
    )
    assert cdef.table_game is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/test_table_resolution_schema.py -v`
Expected: FAIL — `ValueError: 'table_resolution' is not a valid ResolutionMode` (and the rest cascade).

- [ ] **Step 3: Add the enum members**

In `sidequest/genre/models/rules.py`, add to `WinCondition` (after `hp_depletion = "hp_depletion"`, line 306):

```python
    table_showdown = "table_showdown"
```

Add to `ResolutionMode` (after `opposed_check = "opposed_check"`, line 327):

```python
    table_resolution = "table_resolution"
```

- [ ] **Step 4: Add the fields to ConfrontationDef**

In `ConfrontationDef`, add after `geometry_modifiers` (line 435):

```python
    # Free-for-all N-seat table (table_resolution mode). ``table_game`` is the
    # resolver discriminator ("poker" | "auction"); ``max_decision_points``
    # bounds the abstracted betting loop. Both None/0 for non-table types.
    table_game: str | None = None
    max_decision_points: int = 0
```

- [ ] **Step 5: Extend the after-validator**

In `ConfrontationDef._validate` (line 454), add a `table_resolution` branch. Insert immediately after the `if not self.confrontation_type:` block (before the `dial_threshold` check at line 458):

```python
        if self.resolution_mode == ResolutionMode.table_resolution:
            if not self.table_game:
                raise ValueError(
                    f"confrontation '{self.confrontation_type}' uses "
                    "resolution_mode 'table_resolution' but declares no "
                    "table_game (e.g. 'poker' | 'auction')"
                )
            if self.win_condition != WinCondition.table_showdown:
                raise ValueError(
                    f"confrontation '{self.confrontation_type}' uses "
                    "resolution_mode 'table_resolution' but win_condition is "
                    f"{self.win_condition.value!r}; it must be 'table_showdown'"
                )
            if self.max_decision_points < 1:
                raise ValueError(
                    f"confrontation '{self.confrontation_type}' uses "
                    "table_resolution but max_decision_points="
                    f"{self.max_decision_points} (must be >= 1)"
                )
            # table_showdown reads table_state, never the dials — return before
            # the dial_threshold requirement below.
            return self
```

> **Note:** the existing `dial_threshold` check at line 458 only fires `if self.win_condition == WinCondition.dial_threshold`, so `table_showdown` already skips it. The early `return self` above is belt-and-suspenders and also short-circuits the combat/hp_depletion block. Keep it.

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/genre/test_table_resolution_schema.py -v`
Expected: PASS (6 tests).

- [ ] **Step 7: Run the genre schema regression slice**

Run: `uv run pytest tests/genre/ -q`
Expected: PASS (existing packs load; new optional fields default safely).

- [ ] **Step 8: Commit**

```bash
uv run ruff check sidequest/genre/models/rules.py
git add sidequest/genre/models/rules.py tests/genre/test_table_resolution_schema.py
git commit -m "feat(table): add table_resolution mode, table_showdown win_condition, table_game discriminator"
```

---

## Phase B — Telemetry

### Task 4: The 8 `table.*` OTEL spans

**Files:**
- Create: `sidequest/telemetry/spans/table.py`
- Modify: `sidequest/telemetry/spans/__init__.py`
- Test: `tests/telemetry/test_table_spans.py`

- [ ] **Step 1: Write the failing test**

Create `tests/telemetry/test_table_spans.py`:

```python
from sidequest.telemetry.spans import (
    table_accuse_span,
    table_cheat_span,
    table_commit_span,
    table_dealt_span,
    table_fold_span,
    table_npc_commit_span,
    table_read_span,
    table_showdown_span,
)
from sidequest.telemetry.spans._core import SPAN_ROUTES


def test_all_table_spans_registered_in_routes():
    for name in (
        "table.dealt",
        "table.commit",
        "table.npc_commit",
        "table.cheat",
        "table.read",
        "table.accuse",
        "table.fold",
        "table.showdown",
    ):
        assert name in SPAN_ROUTES, f"{name} missing from SPAN_ROUTES"
        assert SPAN_ROUTES[name].component == "table"


def test_dealt_span_opens_and_routes():
    with table_dealt_span(seat_count=3, game_kind="poker", stake_kind="money"):
        pass
    route = SPAN_ROUTES["table.dealt"]
    # extract() must read attributes without raising even on a bare span shape
    extracted = route.extract(type("S", (), {"attributes": {"seat_count": 3, "game_kind": "poker"}})())
    assert extracted["seat_count"] == 3
    assert extracted["op"] == "dealt"


def test_showdown_span_carries_winner():
    with table_showdown_span(winner="seat_1", forfeits=["seat_2"], pot_awarded="seat_1"):
        pass
    assert SPAN_ROUTES["table.showdown"].component == "table"


def test_commit_and_npc_commit_spans_open():
    with table_commit_span(seat="seat_1", beat_id="raise", amount=2, decision_point=0):
        pass
    with table_npc_commit_span(seat="seat_2", strength_band="strong", pot=4, chosen_beat="call"):
        pass


def test_cheat_read_accuse_spans_open():
    with table_cheat_span(seat="seat_1", strength_before=12, strength_after=20, new_trace=0.4):
        pass
    with table_read_span(reader="seat_1", target="seat_2", info_returned="strength_band=weak"):
        pass
    with table_accuse_span(accuser="seat_1", target="seat_2", accuser_total=18, dc=14, landed=True):
        pass


def test_fold_span_opens():
    with table_fold_span(seat="seat_3", decision_point=1):
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_table_spans.py -v`
Expected: FAIL — `ImportError: cannot import name 'table_dealt_span'`.

- [ ] **Step 3: Write the span module**

Create `sidequest/telemetry/spans/table.py` (mirrors `dogfight.py`'s shape exactly):

```python
"""Free-for-all N-seat table resolution spans.

Eight spans cover the lifecycle: dealt, commit, npc_commit, cheat, read,
accuse, fold, showdown. Each subsystem decision emits one so the GM panel
(lie detector) can confirm the cheat fired / the read returned a real value /
the accuse checked an actual trace — narration claiming "you catch him palming
an ace" with no table.accuse/table.cheat span is a logged mismatch
(dispatch_engagement_watcher). See
docs/superpowers/specs/2026-05-29-free-for-all-n-seat-table-design.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from ._core import SPAN_ROUTES, SpanRoute
from .span import Span

SPAN_TABLE_DEALT = "table.dealt"
SPAN_ROUTES[SPAN_TABLE_DEALT] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "dealt",
        "seat_count": (span.attributes or {}).get("seat_count", 0),
        "game_kind": (span.attributes or {}).get("game_kind", ""),
        "stake_kind": (span.attributes or {}).get("stake_kind", ""),
    },
)
SPAN_TABLE_COMMIT = "table.commit"
SPAN_ROUTES[SPAN_TABLE_COMMIT] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "commit",
        "seat": (span.attributes or {}).get("seat", ""),
        "beat_id": (span.attributes or {}).get("beat_id", ""),
        "amount": (span.attributes or {}).get("amount", 0),
        "decision_point": (span.attributes or {}).get("decision_point", 0),
    },
)
SPAN_TABLE_NPC_COMMIT = "table.npc_commit"
SPAN_ROUTES[SPAN_TABLE_NPC_COMMIT] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "npc_commit",
        "seat": (span.attributes or {}).get("seat", ""),
        "strength_band": (span.attributes or {}).get("strength_band", ""),
        "pot": (span.attributes or {}).get("pot", 0),
        "chosen_beat": (span.attributes or {}).get("chosen_beat", ""),
    },
)
SPAN_TABLE_CHEAT = "table.cheat"
SPAN_ROUTES[SPAN_TABLE_CHEAT] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "cheat",
        "seat": (span.attributes or {}).get("seat", ""),
        "strength_before": (span.attributes or {}).get("strength_before", 0),
        "strength_after": (span.attributes or {}).get("strength_after", 0),
        "new_trace": (span.attributes or {}).get("new_trace", 0.0),
    },
)
SPAN_TABLE_READ = "table.read"
SPAN_ROUTES[SPAN_TABLE_READ] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "read",
        "reader": (span.attributes or {}).get("reader", ""),
        "target": (span.attributes or {}).get("target", ""),
        "info_returned": (span.attributes or {}).get("info_returned", ""),
    },
)
SPAN_TABLE_ACCUSE = "table.accuse"
SPAN_ROUTES[SPAN_TABLE_ACCUSE] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "accuse",
        "accuser": (span.attributes or {}).get("accuser", ""),
        "target": (span.attributes or {}).get("target", ""),
        "accuser_total": (span.attributes or {}).get("accuser_total", 0),
        "dc": (span.attributes or {}).get("dc", 0),
        "landed": (span.attributes or {}).get("landed", False),
    },
)
SPAN_TABLE_FOLD = "table.fold"
SPAN_ROUTES[SPAN_TABLE_FOLD] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "fold",
        "seat": (span.attributes or {}).get("seat", ""),
        "decision_point": (span.attributes or {}).get("decision_point", 0),
    },
)
SPAN_TABLE_SHOWDOWN = "table.showdown"
SPAN_ROUTES[SPAN_TABLE_SHOWDOWN] = SpanRoute(
    event_type="state_transition",
    component="table",
    extract=lambda span: {
        "field": "table",
        "op": "showdown",
        "winner": (span.attributes or {}).get("winner", ""),
        "forfeits": (span.attributes or {}).get("forfeits", ""),
        "pot_awarded": (span.attributes or {}).get("pot_awarded", ""),
    },
)


@contextmanager
def table_dealt_span(
    *, seat_count: int, game_kind: str, stake_kind: str,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_DEALT,
        {"seat_count": seat_count, "game_kind": game_kind, "stake_kind": stake_kind, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def table_commit_span(
    *, seat: str, beat_id: str, amount: int, decision_point: int,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_COMMIT,
        {"seat": seat, "beat_id": beat_id, "amount": amount, "decision_point": decision_point, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def table_npc_commit_span(
    *, seat: str, strength_band: str, pot: int, chosen_beat: str,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_NPC_COMMIT,
        {"seat": seat, "strength_band": strength_band, "pot": pot, "chosen_beat": chosen_beat, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def table_cheat_span(
    *, seat: str, strength_before: int, strength_after: int, new_trace: float,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_CHEAT,
        {"seat": seat, "strength_before": strength_before, "strength_after": strength_after,
         "new_trace": new_trace, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def table_read_span(
    *, reader: str, target: str, info_returned: str,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_READ,
        {"reader": reader, "target": target, "info_returned": info_returned, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def table_accuse_span(
    *, accuser: str, target: str, accuser_total: int, dc: int, landed: bool,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_ACCUSE,
        {"accuser": accuser, "target": target, "accuser_total": accuser_total, "dc": dc,
         "landed": landed, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def table_fold_span(
    *, seat: str, decision_point: int,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_FOLD,
        {"seat": seat, "decision_point": decision_point, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def table_showdown_span(
    *, winner: str | None, forfeits: list[str], pot_awarded: str | None,
    _tracer: trace.Tracer | None = None, **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_TABLE_SHOWDOWN,
        {"winner": winner or "", "forfeits": ",".join(forfeits), "pot_awarded": pot_awarded or "", **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span
```

- [ ] **Step 4: Export from the spans package**

In `sidequest/telemetry/spans/__init__.py`, add next to the other `from .X import *` lines (alphabetical neighborhood near `from .dogfight import *` on line 53):

```python
from .table import *  # noqa: F401, F403
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/telemetry/test_table_spans.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
uv run ruff check sidequest/telemetry/spans/table.py
git add sidequest/telemetry/spans/table.py sidequest/telemetry/spans/__init__.py tests/telemetry/test_table_spans.py
git commit -m "feat(table): add 8 table.* OTEL spans + routes"
```

---

## Phase C — Resolver engine

### Task 5: Table-game registry + `TableGame` ABC + fail-loud dispatch

**Files:**
- Create: `sidequest/game/table/registry.py`
- Test: `tests/game/table/test_registry.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/table/test_registry.py`:

```python
import random

import pytest

from sidequest.game.table.registry import (
    TableGame,
    UnknownTableGameError,
    get_table_game,
    register_table_game,
)
from sidequest.game.table.types import CheatResult, ReadResult, TablePot, TableSeat


def test_unknown_kind_fails_loud():
    with pytest.raises(UnknownTableGameError, match="frobnicate"):
        get_table_game("frobnicate")


def test_register_and_get_roundtrip():
    class _Dummy(TableGame):
        kind = "dummy_test_kind"

        def deal(self, seats, pot, rng):
            for s in seats:
                s.private_state["strength"] = 1
                s.private_state["strength_band"] = "weak"

        def strength(self, seat):
            return int(seat.private_state["strength"])

    register_table_game(_Dummy())
    game = get_table_game("dummy_test_kind")
    seat = TableSeat(seat_id="seat_1", party_name="P1", is_pc=True, status="active", private_state={})
    pot = TablePot(stake_kind="money", stake_descriptor="pot", contributions={"seat_1": 0})
    game.deal([seat], pot, random.Random(1))
    assert game.strength(seat) == 1


def test_default_cheat_and_read_raise_not_implemented():
    class _NoExtras(TableGame):
        kind = "no_extras_test_kind"

        def deal(self, seats, pot, rng):
            pass

        def strength(self, seat):
            return 0

    g = _NoExtras()
    seat = TableSeat(seat_id="seat_1", party_name="P1", is_pc=True, status="active", private_state={})
    with pytest.raises(NotImplementedError):
        g.cheat(seat, random.Random(0))
    with pytest.raises(NotImplementedError):
        g.read(seat, seat, reader_stat=0)


def test_double_register_same_kind_raises():
    class _A(TableGame):
        kind = "dup_kind_test"

        def deal(self, seats, pot, rng):
            pass

        def strength(self, seat):
            return 0

    register_table_game(_A())
    with pytest.raises(ValueError, match="already registered"):
        register_table_game(_A())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/table/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.table.registry'`.

- [ ] **Step 3: Write the registry**

Create `sidequest/game/table/registry.py`:

```python
"""Per-game-kind dispatch for the N-seat table model.

A TableGame implements the kind-specific bits the generic engine can't know:
how to deal, how strong a hand is, and (optionally) Cheat / Read. Kinds
register themselves at import time; an unknown game_kind fails loud
(UnknownTableGameError) — no silent default game.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from sidequest.game.table.types import CheatResult, ReadResult, TablePot, TableSeat


class UnknownTableGameError(ValueError):
    """Raised when a confrontation names a table_game with no registered resolver."""


class TableGame(ABC):
    """Authority for one game_kind's dealing, strength, and signature beats."""

    #: registry key, also the value authors write in rules.yaml `table_game:`
    kind: str

    @abstractmethod
    def deal(self, seats: list[TableSeat], pot: TablePot, rng: random.Random) -> None:
        """Populate each seat's private_state and seed pot antes (mutates in place)."""

    @abstractmethod
    def strength(self, seat: TableSeat) -> int:
        """Showdown comparison value for this seat (higher wins)."""

    def cheat(self, seat: TableSeat, rng: random.Random) -> CheatResult:
        """Manipulate the real hand + raise cheat_trace. Override per kind."""
        raise NotImplementedError(f"table_game {self.kind!r} does not support Cheat")

    def read(self, reader: TableSeat, target: TableSeat, *, reader_stat: int) -> ReadResult:
        """Return REAL info about a target into the reader's frame. Override per kind."""
        raise NotImplementedError(f"table_game {self.kind!r} does not support Read")


_REGISTRY: dict[str, TableGame] = {}


def register_table_game(game: TableGame) -> None:
    """Register a table-game kind. Fails loud on a duplicate kind."""
    if game.kind in _REGISTRY:
        raise ValueError(f"table_game {game.kind!r} already registered")
    _REGISTRY[game.kind] = game


def get_table_game(kind: str) -> TableGame:
    """Resolve a registered table-game kind. Fails loud — never a default."""
    game = _REGISTRY.get(kind)
    if game is None:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise UnknownTableGameError(f"Unknown table_game {kind!r}; registered: {known}")
    return game
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/table/test_registry.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
uv run ruff check sidequest/game/table/registry.py
git add sidequest/game/table/registry.py tests/game/table/test_registry.py
git commit -m "feat(table): add TableGame ABC + fail-loud kind registry"
```

---

### Task 6: Poker kind — deal, strength, strength band

**Files:**
- Create: `sidequest/game/table/poker.py`
- Test: `tests/game/table/test_poker.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/table/test_poker.py`:

```python
import random

from sidequest.game.table.poker import POKER_BANDS, PokerTableGame, _hand_strength
from sidequest.game.table.types import TablePot, TableSeat


def _seats(n: int) -> list[TableSeat]:
    return [
        TableSeat(seat_id=f"seat_{i}", party_name=f"P{i}", is_pc=True, status="active", private_state={})
        for i in range(1, n + 1)
    ]


def test_deal_populates_real_hands_and_strength():
    game = PokerTableGame()
    seats = _seats(3)
    pot = TablePot(stake_kind="money", stake_descriptor="pot", contributions={s.seat_id: 0 for s in seats})
    game.deal(seats, pot, random.Random(42))
    for s in seats:
        assert len(s.private_state["cards"]) == 5
        assert isinstance(s.private_state["strength"], int)
        assert s.private_state["strength_band"] in POKER_BANDS
        assert s.private_state["cheat_trace"] == 0.0
    # antes seeded the pot
    assert all(v > 0 for v in pot.contributions.values())


def test_deal_is_deterministic_under_seed():
    pot = TablePot(stake_kind="money", stake_descriptor="pot", contributions={"seat_1": 0})
    a = _seats(1)
    b = _seats(1)
    PokerTableGame().deal(a, pot, random.Random(7))
    pot2 = TablePot(stake_kind="money", stake_descriptor="pot", contributions={"seat_1": 0})
    PokerTableGame().deal(b, pot2, random.Random(7))
    assert a[0].private_state["cards"] == b[0].private_state["cards"]


def test_deal_no_duplicate_cards_across_seats():
    seats = _seats(4)
    pot = TablePot(stake_kind="money", stake_descriptor="pot", contributions={s.seat_id: 0 for s in seats})
    PokerTableGame().deal(seats, pot, random.Random(99))
    all_cards = [c for s in seats for c in s.private_state["cards"]]
    assert len(all_cards) == len(set(all_cards)), "dealt the same card twice"


def test_strength_reads_private_state():
    game = PokerTableGame()
    seat = _seats(1)[0]
    seat.private_state["strength"] = 1234
    assert game.strength(seat) == 1234


def test_hand_strength_orders_pair_above_high_card():
    pair = ["AS", "AH", "5C", "9D", "2S"]
    high = ["AS", "KH", "5C", "9D", "2S"]
    assert _hand_strength(pair) > _hand_strength(high)


def test_band_correctness_high_card_is_weak():
    high = ["AS", "KH", "9C", "5D", "2S"]  # ace-high, no pair → category 0
    assert _band_for(_hand_strength(high)) == "weak"


def test_band_correctness_quads_is_monster():
    quads = ["9S", "9H", "9C", "9D", "2S"]  # four of a kind → category 7
    assert _band_for(_hand_strength(quads)) == "monster"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/table/test_poker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.table.poker'`.

- [ ] **Step 3: Write the poker kind**

Create `sidequest/game/table/poker.py`:

```python
"""Poker table-game kind: real dealt 5-card hands, genuine strength.

Honest crunch where it's dramatic (Sebastien/Jade can see real card math).
A 52-card deck is dealt without replacement; strength is a coarse but real
hand ranking (high-card → pair → two-pair → trips → straight → flush →
full-house → quads → straight-flush) packed into a single comparable int.
Cheat/Read act on the REAL hand. Betting is abstracted by the engine.
"""

from __future__ import annotations

import random
from collections import Counter

from sidequest.game.table.registry import TableGame, register_table_game
from sidequest.game.table.types import CheatResult, ReadResult, TablePot, TableSeat

_RANKS = "23456789TJQKA"
_RANK_VALUE = {r: i for i, r in enumerate(_RANKS, start=2)}  # 2..14
_SUITS = "SHDC"
_FULL_DECK = [r + s for r in _RANKS for s in _SUITS]

_ANTE = 1  # abstract chips each seat antes at deal

# Coarse strength bands derived from the packed hand strength. Ordered low→high.
POKER_BANDS = ("weak", "marginal", "decent", "strong", "monster")

# Pack/unpack share these so the category always occupies a fixed leading slot
# and the two can't drift. (Corrected post-implementation: an earlier draft packed
# variable-length tiebreaks, which let a high-card hand outrank a pair, and recovered
# the category by reverse-division, which misclassified category-0 high-card hands.)
_PACK_BASE = 100  # each tiebreak (rank 2..14) is one base-100 digit
_TIEBREAK_SLOTS = 5  # a 5-card hand has at most 5 tiebreak values


def _categorize(cards: list[str]) -> tuple[int, list[int]]:
    """Return (category_rank, tiebreak_values_desc). Higher category wins."""
    values = sorted((_RANK_VALUE[c[0]] for c in cards), reverse=True)
    suits = [c[1] for c in cards]
    counts = Counter(values)
    # group by (count, value) so quads/trips/pairs sort to the front
    by_count = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    grouped_vals = [v for v, _ in by_count]
    count_shape = sorted(counts.values(), reverse=True)
    is_flush = len(set(suits)) == 1
    distinct = sorted(set(values))
    is_straight = len(distinct) == 5 and distinct[-1] - distinct[0] == 4
    # wheel straight A-2-3-4-5
    if set(values) == {14, 2, 3, 4, 5}:
        is_straight = True
        grouped_vals = [5, 4, 3, 2, 1]

    if is_straight and is_flush:
        return 8, grouped_vals
    if count_shape == [4, 1]:
        return 7, grouped_vals
    if count_shape == [3, 2]:
        return 6, grouped_vals
    if is_flush:
        return 5, grouped_vals
    if is_straight:
        return 4, grouped_vals
    if count_shape == [3, 1, 1]:
        return 3, grouped_vals
    if count_shape == [2, 2, 1]:
        return 2, grouped_vals
    if count_shape == [2, 1, 1, 1]:
        return 1, grouped_vals
    return 0, grouped_vals


def _hand_strength(cards: list[str]) -> int:
    """Pack (category, tiebreaks) into a single comparable int.

    Category occupies the fixed most-significant slot by padding tiebreaks to
    exactly _TIEBREAK_SLOTS — this guarantees any category-N hand beats any
    category-(N-1) hand regardless of kickers (pair always > high-card).
    """
    category, tiebreaks = _categorize(cards)
    padded = (tiebreaks + [0] * _TIEBREAK_SLOTS)[:_TIEBREAK_SLOTS]
    strength = category
    for v in padded:
        strength = strength * _PACK_BASE + v
    return strength


def _band_for(strength: int) -> str:
    # Recover the category from the fixed leading slot — NOT by reverse-division
    # (which can't distinguish category 0 from a tiebreak value).
    category = strength // (_PACK_BASE ** _TIEBREAK_SLOTS)
    # category 0..8 → 5 bands
    if category >= 7:
        return "monster"
    if category >= 4:
        return "strong"
    if category == 3:
        return "decent"
    if category in (1, 2):
        return "marginal"
    return "weak"


class PokerTableGame(TableGame):
    kind = "poker"

    def deal(self, seats: list[TableSeat], pot: TablePot, rng: random.Random) -> None:
        deck = list(_FULL_DECK)
        rng.shuffle(deck)
        for seat in seats:
            hand = [deck.pop() for _ in range(5)]
            strength = _hand_strength(hand)
            seat.private_state["cards"] = hand
            seat.private_state["strength"] = strength
            seat.private_state["strength_band"] = _band_for(strength)
            seat.private_state["cheat_trace"] = 0.0
            pot.contributions[seat.seat_id] = pot.contributions.get(seat.seat_id, 0) + _ANTE

    def strength(self, seat: TableSeat) -> int:
        return int(seat.private_state["strength"])

    def cheat(self, seat: TableSeat, rng: random.Random) -> CheatResult:
        """Swap the weakest card for a better one drawn fresh; raise cheat_trace.

        Real advantage (strength recomputed), real evidence (trace climbs and
        compounds with repeated cheats).
        """
        before = int(seat.private_state["strength"])
        hand: list[str] = list(seat.private_state["cards"])
        held = set(hand)
        # weakest card = lowest rank value
        weakest = min(hand, key=lambda c: _RANK_VALUE[c[0]])
        # draw the best available card not already on the table for this seat
        candidates = [c for c in _FULL_DECK if c not in held]
        replacement = max(candidates, key=lambda c: _RANK_VALUE[c[0]])
        swapped = list(hand)
        swapped[swapped.index(weakest)] = replacement
        after_swapped = _hand_strength(swapped)
        # A cheat must never sabotage the cheater: swapping into a made straight/
        # flush would break it. Keep the swap only if it genuinely helps; the
        # attempt still leaves a trace either way.
        if after_swapped > before:
            new_hand, after = swapped, after_swapped
        else:
            new_hand, after = hand, before
        seat.private_state["cards"] = new_hand
        seat.private_state["strength"] = after
        seat.private_state["strength_band"] = _band_for(after)
        # trace climbs; repeated cheats compound (0.3 base, +0.15 jitter, additive)
        prior = float(seat.private_state.get("cheat_trace", 0.0))
        new_trace = round(min(1.0, prior + 0.3 + rng.random() * 0.15), 4)
        seat.private_state["cheat_trace"] = new_trace
        return CheatResult(strength_before=before, strength_after=after, new_trace=new_trace)

    def read(self, reader: TableSeat, target: TableSeat, *, reader_stat: int) -> ReadResult:
        """Return the target's REAL strength_band; flag a suspicious trace when
        it exceeds a read threshold scaled by the reader's relevant stat.
        """
        trace_val = float(target.private_state.get("cheat_trace", 0.0))
        # higher reader_stat → lower threshold → easier to notice a cheat
        read_threshold = max(0.1, 0.6 - 0.03 * reader_stat)
        info = {
            "target_seat": target.seat_id,
            "strength_band": target.private_state.get("strength_band", "unknown"),
            "suspicious_trace": trace_val >= read_threshold,
        }
        return ReadResult(target_seat=target.seat_id, info=info)


register_table_game(PokerTableGame())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/table/test_poker.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
uv run ruff check sidequest/game/table/poker.py
git add sidequest/game/table/poker.py tests/game/table/test_poker.py
git commit -m "feat(table): add poker kind — real dealt hands, strength bands, cheat/read"
```

---

### Task 7: Engine — deal + decision-point resolution + showdown

**Files:**
- Create: `sidequest/game/table/engine.py`
- Test: `tests/game/table/test_engine.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/table/test_engine.py`:

```python
import random

import pytest

from sidequest.game.table.engine import deal_table, resolve_table
from sidequest.game.table.types import (
    TableCommit,
    TableNeedsOthersError,
    TablePot,
    TableSeat,
    TableState,
)

# poker kind must be imported so it registers
import sidequest.game.table.poker  # noqa: F401


def _state(n: int, max_dp: int = 3) -> TableState:
    seats = [
        TableSeat(seat_id=f"seat_{i}", party_name=f"P{i}", is_pc=True, status="active", private_state={})
        for i in range(1, n + 1)
    ]
    return TableState(
        game_kind="poker",
        seats=seats,
        pot=TablePot(
            stake_kind="money",
            stake_descriptor="the pot",
            contributions={s.seat_id: 0 for s in seats},
        ),
        order=[s.seat_id for s in seats],
        dealer_seat="seat_1",
        max_decision_points=max_dp,
    )


def test_deal_table_requires_two_seats():
    st = _state(1)
    with pytest.raises(TableNeedsOthersError):
        deal_table(st, rng=random.Random(0))


def test_deal_table_unknown_kind_fails_loud():
    from sidequest.game.table.registry import UnknownTableGameError

    st = _state(2)
    st.game_kind = "nonesuch"
    with pytest.raises(UnknownTableGameError):
        deal_table(st, rng=random.Random(0))


def test_fold_drops_seat_and_emits(monkeypatch):
    st = _state(3)
    deal_table(st, rng=random.Random(1))
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="fold"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call"),
        "seat_3": TableCommit(seat_id="seat_3", beat_id="call"),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(1))
    assert st.find_seat("seat_1").status == "folded"
    assert not out.showdown  # 2 active seats remain, decision_point advanced
    assert st.decision_point == 1


def test_bet_raise_adjusts_pot():
    st = _state(2)
    deal_table(st, rng=random.Random(2))
    before = st.pot.contributions["seat_1"]
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="raise", amount=5),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call", amount=5),
    }
    resolve_table(st, commits=commits, rng=random.Random(2))
    assert st.pot.contributions["seat_1"] == before + 5


def test_showdown_when_one_active_seat_left():
    st = _state(3)
    deal_table(st, rng=random.Random(3))
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="call"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="fold"),
        "seat_3": TableCommit(seat_id="seat_3", beat_id="fold"),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(3))
    assert out.showdown is True
    assert out.resolved_winner == "seat_1"
    assert out.pot_awarded_to == "seat_1"
    assert st.resolved_winner == "seat_1"


def test_showdown_at_max_decision_points_picks_highest_strength():
    st = _state(2, max_dp=1)
    deal_table(st, rng=random.Random(4))
    # force known strengths so the winner is deterministic
    st.find_seat("seat_1").private_state["strength"] = 999999
    st.find_seat("seat_2").private_state["strength"] = 1
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="call"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call"),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(4))
    assert out.showdown is True
    assert out.resolved_winner == "seat_1"


def test_showdown_requires_readable_strength():
    st = _state(2, max_dp=1)
    deal_table(st, rng=random.Random(5))
    del st.find_seat("seat_2").private_state["strength"]
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="call"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call"),
    }
    with pytest.raises(ValueError, match="strength"):
        resolve_table(st, commits=commits, rng=random.Random(5))


def test_commit_for_unknown_seat_fails_loud():
    st = _state(2)
    deal_table(st, rng=random.Random(6))
    commits = {"ghost": TableCommit(seat_id="ghost", beat_id="call")}
    with pytest.raises(ValueError, match="ghost"):
        resolve_table(st, commits=commits, rng=random.Random(6))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/table/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.table.engine'`.

- [ ] **Step 3: Write the engine (fold/bet/call/showdown; cheat/read/accuse added in Task 8)**

Create `sidequest/game/table/engine.py`:

```python
"""The generic N-seat decision-point loop.

resolve_table() resolves ONE decision point: it applies each seat's committed
action in resolution order, then decides whether the hand goes to showdown
(≤1 active seat, or max_decision_points reached) or advances to the next
decision point. Kind-specific bits (deal, strength, cheat, read) are dispatched
through the registry. Every seat action emits one OTEL span — the GM panel's
lie detector. The dual dials are never touched; this reads/writes table_state.
"""

from __future__ import annotations

import random

from sidequest.game.table.registry import get_table_game
from sidequest.game.table.types import (
    TableCommit,
    TableNeedsOthersError,
    TableResolutionOutcome,
    TableState,
)
from sidequest.telemetry.spans import (
    table_fold_span,
    table_showdown_span,
)

_POT_ACTIONS = {"bet", "raise", "call", "bluff", "raise_bid"}


def deal_table(state: TableState, *, rng: random.Random) -> None:
    """Seat-deal: enforce ≥2 seats, dispatch the kind's deal(). Mutates state."""
    if len(state.seats) < 2:
        raise TableNeedsOthersError(
            f"table {state.game_kind!r} needs >= 2 seats, got {len(state.seats)}"
        )
    game = get_table_game(state.game_kind)  # raises UnknownTableGameError if unregistered
    game.deal(state.seats, state.pot, rng)


def resolve_table(
    state: TableState,
    *,
    commits: dict[str, TableCommit],
    rng: random.Random,
) -> TableResolutionOutcome:
    """Resolve one decision point. See module docstring."""
    game = get_table_game(state.game_kind)

    # Apply each committed action in resolution order (folded/out seats ignored).
    for seat_id in state.order:
        commit = commits.get(seat_id)
        if commit is None:
            continue
        seat = state.find_seat(seat_id)
        if seat is None:
            raise ValueError(f"commit for unknown seat {seat_id!r}")
        if seat.status != "active":
            continue
        _apply_commit(state, seat_id, commit, game=game, rng=rng)

    # Reject commits naming seats that aren't on the table at all (fail loud).
    for seat_id in commits:
        if state.find_seat(seat_id) is None:
            raise ValueError(f"commit for unknown seat {seat_id!r}")

    active = state.active_seat_ids()
    is_showdown = len(active) <= 1 or state.decision_point >= state.max_decision_points - 1
    if not is_showdown:
        state.decision_point += 1
        return TableResolutionOutcome(
            showdown=False,
            resolved_winner=None,
            pot_awarded_to=None,
            stake_kind=None,
            stake_descriptor=None,
            narration_hint="",
        )
    return _showdown(state, game=game, rng=rng)


def _apply_commit(state, seat_id, commit, *, game, rng) -> None:
    seat = state.find_seat(seat_id)
    beat = commit.beat_id
    if beat == "fold":
        seat.status = "folded"
        with table_fold_span(seat=seat_id, decision_point=state.decision_point):
            pass
        return
    if beat in _POT_ACTIONS:
        state.pot.contributions[seat_id] = state.pot.contributions.get(seat_id, 0) + max(0, commit.amount)
        return
    # cheat / read_table / accuse handled in Task 8's _apply_signature_beat
    _apply_signature_beat(state, seat_id, commit, game=game, rng=rng)


def _apply_signature_beat(state, seat_id, commit, *, game, rng) -> None:
    # Filled in Task 8. Until then, an unauthored beat must fail loud.
    raise ValueError(
        f"unsupported table beat {commit.beat_id!r} for seat {seat_id!r} "
        f"(game_kind={state.game_kind!r})"
    )


def _showdown(state, *, game, rng) -> TableResolutionOutcome:
    """Compare strengths among non-folded seats; award the pot. Forfeit logic
    (exposed cheats) is layered in Task 8 — here, no forfeits yet."""
    forfeited: list[str] = []
    contenders = [s for s in state.seats if s.status == "active"]
    if not contenders:
        # everyone folded except possibly one already-out seat — shouldn't happen
        # because resolve_table triggers showdown at ≤1 active; guard anyway.
        raise ValueError("showdown with zero active seats — engine invariant broken")

    if len(contenders) == 1:
        winner = contenders[0]
    else:
        for s in contenders:
            if "strength" not in s.private_state:
                raise ValueError(
                    f"showdown: seat {s.seat_id!r} has no readable strength — "
                    "fail loud, never a coin-flip default"
                )
        winner = max(contenders, key=lambda s: game.strength(s))

    state.resolved_winner = winner.seat_id
    hint = f"{winner.party_name} takes {state.pot.stake_descriptor}"
    with table_showdown_span(
        winner=winner.seat_id, forfeits=forfeited, pot_awarded=winner.seat_id
    ):
        pass
    return TableResolutionOutcome(
        showdown=True,
        resolved_winner=winner.seat_id,
        pot_awarded_to=winner.seat_id,
        stake_kind=state.pot.stake_kind,
        stake_descriptor=state.pot.stake_descriptor,
        narration_hint=hint,
        forfeited_seats=forfeited,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/table/test_engine.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
uv run ruff check sidequest/game/table/engine.py
git add sidequest/game/table/engine.py tests/game/table/test_engine.py
git commit -m "feat(table): add engine decision-point loop — fold/bet/call/showdown"
```

---

### Task 8: Cheat / Read / Accuse sub-loop (the crunch)

> **CORRECTION (post-implementation, authoritative):** the code blocks below show an earlier design that resolved the accuse opposed-check *at apply time* using a `resolve_table`-local `accusations` list. That was a **bug**: an accusation made in a non-showdown decision point was silently discarded, and the roll used the apply-time `cheat_trace` (so a *later* cheat couldn't be caught). The shipped implementation instead **persists `pending_accusations: list[tuple[str,str]]` on `TableState`** (recorded at apply, no roll/span there) and **rolls the opposed check + emits `table.accuse` in `_showdown` against the FINAL `cheat_trace`**, clearing the list after. This satisfies the spec's "resolved at showdown so a late cheat is still catchable." Treat the committed `engine.py`/`types.py` as authoritative for the accuse path; the cheat/read branches below are accurate as written.

**Files:**
- Modify: `sidequest/game/table/engine.py` (replace `_apply_signature_beat`, add accuse resolution + forfeit-on-exposed-cheat to `_showdown`)
- Test: `tests/game/table/test_cheat_read_accuse.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/table/test_cheat_read_accuse.py`:

```python
import random

from sidequest.game.table.engine import deal_table, resolve_table
from sidequest.game.table.types import TableCommit, TablePot, TableSeat, TableState

import sidequest.game.table.poker  # noqa: F401  (registers poker)


def _state(n: int, max_dp: int = 3) -> TableState:
    seats = [
        TableSeat(
            seat_id=f"seat_{i}", party_name=f"P{i}", is_pc=True, status="active",
            private_state={"perception": 12, "concealment": 8},
        )
        for i in range(1, n + 1)
    ]
    return TableState(
        game_kind="poker",
        seats=seats,
        pot=TablePot(stake_kind="money", stake_descriptor="the pot",
                     contributions={s.seat_id: 0 for s in seats}),
        order=[s.seat_id for s in seats],
        dealer_seat="seat_1",
        max_decision_points=max_dp,
    )


def test_cheat_raises_trace_and_changes_strength():
    st = _state(2)
    deal_table(st, rng=random.Random(1))
    seat = st.find_seat("seat_1")
    # force a weak hand so the cheat can only help
    seat.private_state["cards"] = ["2S", "3H", "4C", "7D", "9S"]
    seat.private_state["strength"] = 0
    seat.private_state["cheat_trace"] = 0.0
    commits = {"seat_1": TableCommit(seat_id="seat_1", beat_id="cheat"),
               "seat_2": TableCommit(seat_id="seat_2", beat_id="call")}
    resolve_table(st, commits=commits, rng=random.Random(1))
    assert seat.private_state["cheat_trace"] > 0.0
    assert seat.private_state["strength"] >= 0


def test_read_injects_real_info_into_outcome():
    st = _state(2)
    deal_table(st, rng=random.Random(2))
    st.find_seat("seat_2").private_state["strength_band"] = "monster"
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="read_table", target_seat="seat_2"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call"),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(2))
    assert "seat_1" in out.read_results
    assert out.read_results["seat_1"].info["strength_band"] == "monster"


def test_accuse_lands_forfeits_cheater_at_showdown():
    st = _state(2, max_dp=1)
    deal_table(st, rng=random.Random(3))
    cheater = st.find_seat("seat_2")
    cheater.private_state["strength"] = 10 ** 9  # would win on raw strength
    cheater.private_state["cheat_trace"] = 1.0  # blatant
    accuser = st.find_seat("seat_1")
    accuser.private_state["strength"] = 1
    accuser.private_state["perception"] = 20  # near-certain catch
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="accuse", target_seat="seat_2"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call"),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(3))
    assert out.showdown is True
    assert "seat_2" in out.forfeited_seats
    assert out.resolved_winner == "seat_1"  # forfeit beats raw strength


def test_accuse_whiff_penalizes_accuser():
    st = _state(2, max_dp=1)
    deal_table(st, rng=random.Random(4))
    honest = st.find_seat("seat_2")
    honest.private_state["strength"] = 5
    honest.private_state["cheat_trace"] = 0.0  # nothing to find
    honest.private_state["concealment"] = 30
    accuser = st.find_seat("seat_1")
    accuser.private_state["strength"] = 10 ** 9  # would win on strength
    accuser.private_state["perception"] = 1
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="accuse", target_seat="seat_2"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call"),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(4))
    # whiff → accuser forfeits (slandered an honest man), honest seat wins
    assert "seat_1" in out.forfeited_seats
    assert out.resolved_winner == "seat_2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/table/test_cheat_read_accuse.py -v`
Expected: FAIL — `_apply_signature_beat` raises `ValueError: unsupported table beat 'cheat'`.

- [ ] **Step 3: Implement the sub-loop**

In `sidequest/game/table/engine.py`, add these imports to the existing telemetry import block:

```python
from sidequest.telemetry.spans import (
    table_accuse_span,
    table_cheat_span,
    table_fold_span,
    table_read_span,
    table_showdown_span,
)
```

Add a module-level constant near `_POT_ACTIONS`:

```python
# Accuse opposed-check tuning (content could later override via cdef).
_ACCUSE_BASE_DC = 10
_ACCUSE_TRACE_WEIGHT = 8  # cheat_trace (0..1) contributes 0..8 toward catchability
```

Replace the placeholder `_apply_signature_beat` with the real implementation, and thread a `pending_accusations` accumulator and `read_results` through resolution. The cleanest shape: collect signature side-effects on the state during apply, resolve accusations at showdown. Update `resolve_table` and `_showdown` as follows.

Replace `_apply_signature_beat` with:

```python
def _apply_signature_beat(state, seat_id, commit, *, game, rng, read_results, accusations) -> None:
    beat = commit.beat_id
    seat = state.find_seat(seat_id)
    if beat == "cheat":
        result = game.cheat(seat, rng)  # mutates seat.private_state
        with table_cheat_span(
            seat=seat_id,
            strength_before=result.strength_before,
            strength_after=result.strength_after,
            new_trace=result.new_trace,
        ):
            pass
        return
    if beat in ("read_table", "read_room"):
        target = _require_target(state, seat_id, commit)
        reader_stat = int(seat.private_state.get("perception", 0))
        read = game.read(seat, target, reader_stat=reader_stat)
        read_results[seat_id] = read
        with table_read_span(
            reader=seat_id,
            target=target.seat_id,
            info_returned=str(read.info.get("strength_band", "")),
        ):
            pass
        return
    if beat == "accuse":
        target = _require_target(state, seat_id, commit)
        # opposed check resolved AT SHOWDOWN (a late cheat is still catchable),
        # but record the roll now from a deterministic rng draw.
        accuser_stat = int(seat.private_state.get("perception", 0))
        concealment = int(target.private_state.get("concealment", 0))
        trace_val = float(target.private_state.get("cheat_trace", 0.0))
        accuser_total = rng.randint(1, 20) + accuser_stat
        dc = _ACCUSE_BASE_DC + concealment - round(trace_val * _ACCUSE_TRACE_WEIGHT)
        landed = accuser_total >= dc
        with table_accuse_span(
            accuser=seat_id, target=target.seat_id,
            accuser_total=accuser_total, dc=dc, landed=landed,
        ):
            pass
        accusations.append((seat_id, target.seat_id, landed))
        return
    raise ValueError(
        f"unsupported table beat {commit.beat_id!r} for seat {seat_id!r} "
        f"(game_kind={state.game_kind!r})"
    )


def _require_target(state, seat_id, commit):
    if commit.target_seat is None:
        raise ValueError(f"beat {commit.beat_id!r} from {seat_id!r} requires a target_seat")
    target = state.find_seat(commit.target_seat)
    if target is None:
        raise ValueError(f"beat {commit.beat_id!r} targets unknown seat {commit.target_seat!r}")
    return target
```

Now update `_apply_commit` to forward the two accumulators (change its signature and the signature-beat call):

```python
def _apply_commit(state, seat_id, commit, *, game, rng, read_results, accusations) -> None:
    seat = state.find_seat(seat_id)
    beat = commit.beat_id
    if beat == "fold":
        seat.status = "folded"
        with table_fold_span(seat=seat_id, decision_point=state.decision_point):
            pass
        return
    if beat in _POT_ACTIONS:
        state.pot.contributions[seat_id] = state.pot.contributions.get(seat_id, 0) + max(0, commit.amount)
        return
    _apply_signature_beat(
        state, seat_id, commit, game=game, rng=rng,
        read_results=read_results, accusations=accusations,
    )
```

Update `resolve_table` to create the accumulators, pass them in, attach `read_results` to the non-showdown outcome too, and hand `accusations` to `_showdown`:

```python
def resolve_table(state, *, commits, rng) -> TableResolutionOutcome:
    game = get_table_game(state.game_kind)
    read_results: dict = {}
    accusations: list[tuple[str, str, bool]] = []  # (accuser, target, landed)

    # Reject commits naming seats not on the table BEFORE applying anything —
    # fail loud before mutating, so a ghost commit can't leave a half-applied hand.
    for seat_id in commits:
        if state.find_seat(seat_id) is None:
            raise ValueError(f"commit for unknown seat {seat_id!r}")

    for seat_id in state.order:
        commit = commits.get(seat_id)
        if commit is None:
            continue
        seat = state.find_seat(seat_id)
        if seat is None:
            continue
        if seat.status != "active":
            continue
        _apply_commit(state, seat_id, commit, game=game, rng=rng,
                      read_results=read_results, accusations=accusations)

    active = state.active_seat_ids()
    is_showdown = len(active) <= 1 or state.decision_point >= state.max_decision_points - 1
    if not is_showdown:
        state.decision_point += 1
        return TableResolutionOutcome(
            showdown=False, resolved_winner=None, pot_awarded_to=None,
            stake_kind=None, stake_descriptor=None, narration_hint="",
            read_results=read_results,
        )
    return _showdown(state, game=game, rng=rng, accusations=accusations, read_results=read_results)
```

Update `_showdown` to resolve accusations FIRST (forfeit-on-exposed-cheat beats raw strength) and carry `read_results`:

```python
def _showdown(state, *, game, rng, accusations, read_results) -> TableResolutionOutcome:
    forfeited: list[str] = []
    for accuser, target, landed in accusations:
        if landed:
            # exposed cheat forfeits regardless of strength
            if target not in forfeited:
                forfeited.append(target)
        else:
            # slandered an honest man: the accuser eats the cost
            if accuser not in forfeited:
                forfeited.append(accuser)

    contenders = [
        s for s in state.seats if s.status == "active" and s.seat_id not in forfeited
    ]
    if not contenders:
        raise ValueError("showdown with zero eligible contenders — all seats folded/forfeited")

    # Uniform fail-loud strength guard (single- and multi-contender alike) — never a
    # coin-flip default, and never a bare KeyError from game.strength().
    for s in contenders:
        if "strength" not in s.private_state:
            raise ValueError(
                f"showdown: seat {s.seat_id!r} has no readable strength — "
                "fail loud, never a coin-flip default"
            )
    revealed = ",".join(f"{s.seat_id}:{game.strength(s)}" for s in contenders)
    winner = contenders[0] if len(contenders) == 1 else max(contenders, key=lambda s: game.strength(s))

    state.resolved_winner = winner.seat_id
    hint = f"{winner.party_name} takes {state.pot.stake_descriptor}"
    if forfeited:
        hint += f" (forfeits: {', '.join(forfeited)})"
    with table_showdown_span(
        winner=winner.seat_id, forfeits=forfeited, pot_awarded=winner.seat_id,
        revealed_strengths=revealed,
    ):
        pass
    return TableResolutionOutcome(
        showdown=True, resolved_winner=winner.seat_id, pot_awarded_to=winner.seat_id,
        stake_kind=state.pot.stake_kind, stake_descriptor=state.pot.stake_descriptor,
        narration_hint=hint, forfeited_seats=forfeited, read_results=read_results,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/table/test_cheat_read_accuse.py tests/game/table/test_engine.py -v`
Expected: PASS (both files — the engine tests still pass with the widened signatures).

- [ ] **Step 5: Commit**

```bash
uv run ruff check sidequest/game/table/engine.py
git add sidequest/game/table/engine.py tests/game/table/test_cheat_read_accuse.py
git commit -m "feat(table): add Cheat/Read/Accuse sub-loop + forfeit-on-exposed-cheat showdown"
```

---

### Task 9: NPC seat commit policy

**Files:**
- Create: `sidequest/game/table/npc_policy.py`
- Test: `tests/game/table/test_npc_policy.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/table/test_npc_policy.py`:

```python
import random

from sidequest.game.table.npc_policy import decide_npc_commit
from sidequest.game.table.types import TablePot, TableSeat, TableState


def _state() -> TableState:
    seats = [
        TableSeat(seat_id="seat_1", party_name="PC", is_pc=True, status="active", private_state={}),
        TableSeat(seat_id="seat_2", party_name="Gambler", is_pc=False, status="active",
                  private_state={"strength_band": "weak", "ocean": {"neuroticism": 0.9},
                                 "disposition": "neutral"}),
    ]
    return TableState(
        game_kind="poker", seats=seats,
        pot=TablePot(stake_kind="money", stake_descriptor="pot",
                     contributions={"seat_1": 5, "seat_2": 1}),
        order=["seat_1", "seat_2"], dealer_seat="seat_1", max_decision_points=3,
    )


def test_anxious_weak_npc_folds():
    st = _state()
    npc = st.find_seat("seat_2")
    commit = decide_npc_commit(st, npc, rng=random.Random(1))
    assert commit.beat_id == "fold"


def test_confident_strong_npc_does_not_fold():
    st = _state()
    npc = st.find_seat("seat_2")
    npc.private_state["strength_band"] = "monster"
    npc.private_state["ocean"] = {"neuroticism": 0.1}
    commit = decide_npc_commit(st, npc, rng=random.Random(1))
    assert commit.beat_id in ("raise", "call", "bluff")


def test_larcenous_disposition_can_cheat():
    st = _state()
    npc = st.find_seat("seat_2")
    npc.private_state["strength_band"] = "marginal"
    npc.private_state["ocean"] = {"neuroticism": 0.2}
    npc.private_state["disposition"] = "larcenous"
    # over many seeds, at least one cheat appears for a larcenous NPC
    beats = {decide_npc_commit(st, npc, rng=random.Random(s)).beat_id for s in range(40)}
    assert "cheat" in beats


def test_commit_seat_id_matches_npc():
    st = _state()
    npc = st.find_seat("seat_2")
    commit = decide_npc_commit(st, npc, rng=random.Random(0))
    assert commit.seat_id == "seat_2"


def test_deterministic_under_seed():
    st = _state()
    npc = st.find_seat("seat_2")
    a = decide_npc_commit(st, npc, rng=random.Random(123))
    b = decide_npc_commit(st, npc, rng=random.Random(123))
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/table/test_npc_policy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.table.npc_policy'`.

- [ ] **Step 3: Write the policy + emit the span**

Create `sidequest/game/table/npc_policy.py`:

```python
"""NPC seat auto-commit — a real basis, not narration whim.

A ruleset-module policy over (own strength_band, pot size, OCEAN/disposition)
returns a TableCommit. Confident/low-neuroticism → slow-play strong or bluff
weak; anxious → fold early; larcenous disposition → likelier to Cheat. Testable
in isolation, deterministic under a seeded rng. Emits table.npc_commit.
"""

from __future__ import annotations

import random

from sidequest.game.table.types import TableCommit, TableSeat, TableState
from sidequest.telemetry.spans import table_npc_commit_span

_BAND_RANK = {"weak": 0, "marginal": 1, "decent": 2, "strong": 3, "monster": 4}


def decide_npc_commit(state: TableState, npc: TableSeat, *, rng: random.Random) -> TableCommit:
    band = str(npc.private_state.get("strength_band", "weak"))
    rank = _BAND_RANK.get(band, 0)
    ocean = npc.private_state.get("ocean", {}) or {}
    neuroticism = float(ocean.get("neuroticism", 0.5))
    disposition = str(npc.private_state.get("disposition", "neutral"))
    pot = sum(state.pot.contributions.values())

    beat = _choose_beat(rank=rank, neuroticism=neuroticism, disposition=disposition, rng=rng)
    amount = _bet_amount(beat, rank=rank, rng=rng)
    target = None
    if beat in ("read_table", "accuse"):
        target = _pick_opponent(state, npc)
        if target is None:
            beat, amount = "call", 0

    with table_npc_commit_span(
        seat=npc.seat_id, strength_band=band, pot=pot, chosen_beat=beat
    ):
        pass
    return TableCommit(seat_id=npc.seat_id, beat_id=beat, amount=amount, target_seat=target)


def _choose_beat(*, rank: int, neuroticism: float, disposition: str, rng: random.Random) -> str:
    # larcenous NPCs reach for the deck when their hand is mediocre
    if disposition == "larcenous" and rank <= 2 and rng.random() < 0.35:
        return "cheat"
    # anxious + weak → fold
    if rank == 0 and neuroticism >= 0.6:
        return "fold"
    if rank == 0:
        # weak but calm → bluff sometimes, else fold
        return "bluff" if rng.random() < 0.4 else "fold"
    if rank >= 3:
        # strong + calm → slow-play (call) or press (raise)
        if neuroticism < 0.4 and rng.random() < 0.5:
            return "call"
        return "raise"
    # middling hand: mostly call, occasional raise
    return "raise" if rng.random() < 0.25 else "call"


def _bet_amount(beat: str, *, rank: int, rng: random.Random) -> int:
    if beat in ("raise", "bluff"):
        return 1 + rank + rng.randint(0, 2)
    if beat == "call":
        return 1
    return 0


def _pick_opponent(state: TableState, npc: TableSeat) -> str | None:
    for sid in state.order:
        s = state.find_seat(sid)
        if s is not None and s.seat_id != npc.seat_id and s.status == "active":
            return s.seat_id
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/table/test_npc_policy.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
uv run ruff check sidequest/game/table/npc_policy.py
git add sidequest/game/table/npc_policy.py tests/game/table/test_npc_policy.py
git commit -m "feat(table): add NPC seat commit policy over strength/pot/OCEAN/disposition"
```

---

### Task 10: RulesetModule seam — `deal_table` / `resolve_table`

**Files:**
- Modify: `sidequest/game/ruleset/base.py`
- Test: `tests/game/ruleset/test_resolve_table_seam.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/ruleset/test_resolve_table_seam.py`:

```python
import random

from sidequest.game.ruleset.registry import get_ruleset_module
from sidequest.game.table.types import TableCommit, TablePot, TableSeat, TableState

import sidequest.game.table.poker  # noqa: F401


def _state(n: int, max_dp: int = 1) -> TableState:
    seats = [
        TableSeat(seat_id=f"seat_{i}", party_name=f"P{i}", is_pc=True, status="active", private_state={})
        for i in range(1, n + 1)
    ]
    return TableState(
        game_kind="poker", seats=seats,
        pot=TablePot(stake_kind="money", stake_descriptor="the pot",
                     contributions={s.seat_id: 0 for s in seats}),
        order=[s.seat_id for s in seats], dealer_seat="seat_1", max_decision_points=max_dp,
    )


def test_native_module_deals_and_resolves_through_seam():
    module = get_ruleset_module("native")
    st = _state(2, max_dp=1)
    module.deal_table(st, rng=random.Random(1))
    st.find_seat("seat_1").private_state["strength"] = 999
    st.find_seat("seat_2").private_state["strength"] = 1
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="call"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="call"),
    }
    out = module.resolve_table(st, commits=commits, rng=random.Random(1))
    assert out.showdown is True
    assert out.resolved_winner == "seat_1"


def test_seam_is_available_on_every_module():
    # table resolution is genre-general — swn/cwn inherit it too
    for slug in ("native", "swn", "cwn"):
        module = get_ruleset_module(slug)
        assert hasattr(module, "deal_table")
        assert hasattr(module, "resolve_table")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_resolve_table_seam.py -v`
Expected: FAIL — `AttributeError: 'NativeRulesetModule' object has no attribute 'deal_table'`.

- [ ] **Step 3: Add the concrete delegating methods to the base module**

In `sidequest/game/ruleset/base.py`, add to the `TYPE_CHECKING` block (after line 21):

```python
    from sidequest.game.table.types import TableCommit, TableResolutionOutcome, TableState
```

Add a `random` import is already present (line 10). Then add two concrete methods to `RulesetModule` (place after `resolve_hacking`, the last method, ~line 140):

```python
    def deal_table(self, state: TableState, *, rng: random.Random) -> None:
        """Seat-deal an N-seat table (poker / auction). Genre-general; the
        per-kind deal is dispatched through the table-game registry. Concrete
        here (not abstract) because table resolution is orthogonal to combat
        resolution — every ruleset inherits it. See game/table/engine.py."""
        from sidequest.game.table.engine import deal_table as _deal

        _deal(state, rng=rng)

    def resolve_table(
        self,
        state: TableState,
        *,
        commits: dict[str, TableCommit],
        rng: random.Random,
    ) -> TableResolutionOutcome:
        """Resolve one decision point of an N-seat table. Delegates to the
        generic engine; kind-specifics dispatch through the registry."""
        from sidequest.game.table.engine import resolve_table as _resolve

        return _resolve(state, commits=commits, rng=rng)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_resolve_table_seam.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the ruleset regression slice**

Run: `uv run pytest tests/game/ruleset/ -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
uv run ruff check sidequest/game/ruleset/base.py
git add sidequest/game/ruleset/base.py tests/game/ruleset/test_resolve_table_seam.py
git commit -m "feat(table): add deal_table/resolve_table seam on RulesetModule (delegates to engine)"
```

---

## Phase D — Wiring into the live engine

### Task 11: Instantiation — seat N parties + deal + build table_state

**Files:**
- Modify: `sidequest/server/dispatch/encounter_lifecycle.py` (`instantiate_encounter_from_trigger`, ~line 766 where `StructuredEncounter(...)` is built)
- Test: `tests/server/dispatch/test_table_instantiation.py`

> **Context for the implementer:** read `instantiate_encounter_from_trigger` (`encounter_lifecycle.py:452`) end-to-end first. It resolves the `cdef`, sources NPCs (`npcs_present` or location fallback), builds the actor roster, then constructs `StructuredEncounter(...)` at ~line 766 stamping `win_condition=cdef.win_condition.value`. You will add an early branch: when `cdef.resolution_mode == ResolutionMode.table_resolution`, build the `TableState`, deal it, and construct the encounter with `table_state=` set (dials become inert placeholders, same as the hp_depletion path at line 727).

- [ ] **Step 1: Write the failing test**

Create `tests/server/dispatch/test_table_instantiation.py`:

```python
import pytest

from sidequest.game.table.types import TableNeedsOthersError
from sidequest.server.dispatch.encounter_lifecycle import instantiate_table_encounter
from sidequest.genre.models.rules import BeatDef, ConfrontationDef, ResolutionMode, WinCondition

import sidequest.game.table.poker  # noqa: F401


def _poker_cdef() -> ConfrontationDef:
    return ConfrontationDef(
        type="poker",
        label="Poker",
        category="social",
        resolution_mode=ResolutionMode.table_resolution,
        win_condition=WinCondition.table_showdown,
        table_game="poker",
        max_decision_points=3,
        beats=[
            BeatDef(id="fold", label="Fold", stat_check="WIS", base=0),
            BeatDef(id="call", label="Call", stat_check="WIS", base=0),
        ],
    )


def test_builds_table_state_with_seats_and_deals():
    cdef = _poker_cdef()
    enc = instantiate_table_encounter(
        cdef=cdef,
        player_names=["Doc"],
        npc_names=["Ringo", "Bart"],
        stake_kind="money",
        stake_descriptor="the pot",
        seed=7,
    )
    assert enc.table_state is not None
    assert enc.win_condition == "table_showdown"
    assert len(enc.table_state.seats) == 3
    # PCs and NPCs both seated; each has a dealt hand
    for seat in enc.table_state.seats:
        assert "strength" in seat.private_state
    # one EncounterActor per seat for barrier/perception plumbing
    assert len(enc.actors) == 3


def test_single_seat_fails_loud():
    cdef = _poker_cdef()
    with pytest.raises(TableNeedsOthersError):
        instantiate_table_encounter(
            cdef=cdef, player_names=["Doc"], npc_names=[],
            stake_kind="money", stake_descriptor="the pot", seed=7,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/dispatch/test_table_instantiation.py -v`
Expected: FAIL — `ImportError: cannot import name 'instantiate_table_encounter'`.

- [ ] **Step 3: Add the table-instantiation helper**

In `sidequest/server/dispatch/encounter_lifecycle.py`, add imports near the top (with the other `from sidequest.game...` imports):

```python
import random as _random

from sidequest.game.ruleset.registry import get_ruleset_module
from sidequest.game.table.types import TablePot, TableSeat, TableState
from sidequest.telemetry.spans import table_dealt_span
```

Add this module-level function (place it just above `instantiate_encounter_from_trigger`, ~line 451):

```python
def instantiate_table_encounter(
    *,
    cdef: ConfrontationDef,
    player_names: list[str],
    npc_names: list[str],
    stake_kind: str,
    stake_descriptor: str,
    seed: int,
    ruleset_slug: str = "native",
) -> StructuredEncounter:
    """Build + deal a table_resolution StructuredEncounter.

    Seats every PC then every NPC (≥2 total or TableNeedsOthersError via
    deal_table), populates each private_state via the kind's deal(), seeds the
    pot from antes, and stamps win_condition=table_showdown. The dual dials are
    inert placeholders (same as the hp_depletion path). Emits table.dealt.
    """
    from sidequest.game.encounter import EncounterActor, EncounterMetric

    parties = [(name, True) for name in player_names] + [(name, False) for name in npc_names]
    seats: list[TableSeat] = []
    actors: list[EncounterActor] = []
    for idx, (party_name, is_pc) in enumerate(parties, start=1):
        seat_id = f"seat_{idx}"
        seats.append(
            TableSeat(
                seat_id=seat_id, party_name=party_name, is_pc=is_pc,
                status="active", private_state={},
            )
        )
        # every seat is its own party; side is cosmetic for table types
        actors.append(EncounterActor(name=party_name, role=seat_id, side="player" if is_pc else "opponent"))

    table_state = TableState(
        game_kind=cdef.table_game or "",
        seats=seats,
        pot=TablePot(
            stake_kind=stake_kind, stake_descriptor=stake_descriptor,
            contributions={s.seat_id: 0 for s in seats},
        ),
        order=[s.seat_id for s in seats],
        dealer_seat=seats[0].seat_id if seats else "",
        max_decision_points=cdef.max_decision_points,
    )

    module = get_ruleset_module(ruleset_slug)
    # Span WRAPS the deal so it captures the work and still emits if the deal
    # raises (TableNeedsOthersError on <2 seats). All attrs are known pre-deal.
    with table_dealt_span(
        seat_count=len(seats), game_kind=table_state.game_kind, stake_kind=stake_kind
    ):
        module.deal_table(table_state, rng=_random.Random(seed))

    enc = StructuredEncounter(
        encounter_type=cdef.confrontation_type,
        win_condition=cdef.win_condition.value,
        player_metric=EncounterMetric(name="table_player_inert", threshold=1),
        opponent_metric=EncounterMetric(name="table_opponent_inert", threshold=1),
        actors=actors,
        table_state=table_state,
    )
    return enc
```

> **Wiring into the live trigger path:** in `instantiate_encounter_from_trigger`, after the `cdef` is resolved (line 510–512) and before the dial/actor construction, add a delegation branch:
>
> ```python
>     if cdef.resolution_mode == ResolutionMode.table_resolution:
>         current = snapshot.encounter
>         if current is not None and not current.resolved:
>             return None
>         additional = additional_player_names or []
>         npc_names = [n.name for n in npcs_present] if npcs_present else []
>         if not npc_names:
>             # location fallback for table seats — reuse the existing helper,
>             # adversary_only=False (gamblers need not be hostile).
>             fallback, _avail = _npc_fallback_at_location(
>                 snapshot, adversarial=False, acting_character_name=player_name,
>             )
>             npc_names = [n.name for n in fallback]
>         stake_kind = (cdef.player_default_stats or {}).get("stake_kind_marker", "money")
>         enc = instantiate_table_encounter(
>             cdef=cdef,
>             player_names=[player_name, *additional],
>             npc_names=npc_names,
>             stake_kind=str(stake_kind),
>             stake_descriptor=cdef.label,
>             seed=snapshot.turn_manager.interaction,
>             ruleset_slug=pack.rules.ruleset if pack.rules else "native",
>         )
>         snapshot.encounter = enc
>         return enc
> ```
>
> Place this branch immediately after the `if cdef is None: raise ...` block at line 512. (Stake metadata is read from content in Task 16; for now `cdef.label` is the descriptor and the stake_kind defaults to `"money"` — a content-declared `stake` block is added in the content tasks.)
>
> **Graceful no-mates decline (post-implementation refinement, authoritative):** before calling `instantiate_table_encounter`, the trigger branch counts total parties (PC + additional PCs + sourced NPCs). If `< 2`, it emits `encounter_no_opponent_available_span` and **returns `None`** — declining gracefully (the narrator continues; "nobody's at the table") rather than letting `TableNeedsOthersError` propagate uncaught and 500 the turn (`confrontation.py` catches only `NoOpponentAvailableError`). This mirrors the adversarial path's empty-fallback handling. The low-level helper `instantiate_table_encounter` still raises `TableNeedsOthersError` on `<2` for direct callers/tests — only the production trigger declines.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/dispatch/test_table_instantiation.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the lifecycle regression slice**

Run: `uv run pytest tests/server/dispatch/ -q`
Expected: PASS (existing dial/hp_depletion/sealed-letter instantiation untouched).

- [ ] **Step 6: Commit**

```bash
uv run ruff check sidequest/server/dispatch/encounter_lifecycle.py
git add sidequest/server/dispatch/encounter_lifecycle.py tests/server/dispatch/test_table_instantiation.py
git commit -m "feat(table): instantiate + deal table_resolution encounters in the trigger path"
```

---

### Task 12: narration_apply exclusive branch (peer to sealed_letter)

**Files:**
- Modify: `sidequest/agents/orchestrator.py` (`BeatSelection.amount` + `from_dict`)
- Modify: `sidequest/server/narration_apply.py` (new `elif` branch at ~2775, peer to the sealed_letter branch)
- Test: `tests/server/test_table_branch_unit.py`

- [ ] **Step 1: Write the failing test for the BeatSelection amount field**

Create `tests/server/test_table_branch_unit.py`:

```python
from sidequest.agents.orchestrator import BeatSelection


def test_beat_selection_parses_amount_and_target():
    bs = BeatSelection.from_dict(
        {"actor": "Doc", "beat_id": "raise", "amount": 5, "target": "seat_2"}
    )
    assert bs.amount == 5
    assert bs.target == "seat_2"


def test_beat_selection_amount_defaults_none():
    bs = BeatSelection.from_dict({"actor": "Doc", "beat_id": "fold"})
    assert bs.amount is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_table_branch_unit.py -v`
Expected: FAIL — `AttributeError: 'BeatSelection' object has no attribute 'amount'`.

- [ ] **Step 3: Add the `amount` field to BeatSelection**

In `sidequest/agents/orchestrator.py`, add to the `BeatSelection` dataclass (after `spell_id: str | None = None`, ~line 277):

```python
    # Table confrontations (poker/auction): raise/bet chips. None on every
    # non-table beat. The existing ``target`` field carries the Read/Accuse
    # target seat_id.
    amount: int | None = None
```

In `BeatSelection.from_dict`, add `amount` parsing (after the outcome parsing, before the `return cls(...)`). Locate the final `return cls(` in `from_dict` and add `amount=d.get("amount")` to its kwargs. The existing return already passes `actor`, `beat_id`, `outcome`, `target`, `spell_id`; append:

```python
            amount=d.get("amount"),
```

- [ ] **Step 4: Run the BeatSelection test**

Run: `uv run pytest tests/server/test_table_branch_unit.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Add the table_resolution branch to narration_apply**

In `sidequest/server/narration_apply.py`, add the branch as a new `elif` immediately after the `sealed_letter_lookup` branch closes (after line 2774's `_legacy_beat_path = False`, before the `elif cdef.resolution_mode == ResolutionMode.opposed_check:` at line 2775).

Add the necessary imports at the top of the function's module (with the other table imports):

```python
from sidequest.game.table.types import TableCommit
from sidequest.telemetry.spans import table_commit_span
```

The branch:

```python
            elif cdef.resolution_mode == ResolutionMode.table_resolution:
                # ---- Free-for-all N-seat table branch (poker / auction) ----
                # EXCLUSIVE of apply_beat: table beats (fold/bet/cheat/...) are
                # NOT dial beats; falling through would double-apply. Each seat's
                # sealed action rides beat_selections (actor→seat, beat_id, amount,
                # target). Folded/out seats are dropped from the barrier elsewhere
                # (session_room). One decision point resolves per barrier turn.
                if enc.table_state is None:
                    raise ValueError(
                        f"confrontation {enc.encounter_type!r} declares "
                        "resolution_mode=table_resolution but encounter has no "
                        "table_state — cannot dispatch table resolution"
                    )
                if pack is None or pack.rules is None:
                    raise ValueError(
                        f"table_resolution {enc.encounter_type!r} requires a pack "
                        "(ruleset binding) but pack/rules is None"
                    )
                # Map each selection (actor name) → seat_id via the actor roster.
                commits: dict[str, TableCommit] = {}
                for sel in gated_selections:
                    actor = enc.find_actor(sel.actor)
                    if actor is None:
                        raise ValueError(
                            f"beat_selection actor {sel.actor!r} not found on "
                            f"table encounter {enc.encounter_type!r}"
                        )
                    seat_id = actor.role  # role holds the seat_id for table encounters
                    commit = TableCommit(
                        seat_id=seat_id,
                        beat_id=sel.beat_id,
                        amount=int(sel.amount or 0),
                        target_seat=sel.target,
                    )
                    commits[seat_id] = commit
                    with table_commit_span(
                        seat=seat_id, beat_id=sel.beat_id,
                        amount=commit.amount, decision_point=enc.table_state.decision_point,
                    ):
                        pass

                # Auto-commit NPC seats that have no PC selection this turn.
                from sidequest.game.table.npc_policy import decide_npc_commit

                rng = _random.Random(
                    snapshot.turn_manager.interaction * 1000 + enc.table_state.decision_point
                )
                for seat in enc.table_state.seats:
                    if seat.is_pc or seat.status != "active" or seat.seat_id in commits:
                        continue
                    commits[seat.seat_id] = decide_npc_commit(enc.table_state, seat, rng=rng)

                module = get_ruleset_module(pack.rules.ruleset)
                table_outcome = module.resolve_table(
                    enc.table_state, commits=commits, rng=rng
                )
                if table_outcome.showdown:
                    enc.resolved = True
                    enc.outcome = f"table_winner:{table_outcome.resolved_winner}"
                    # Award the stake through the normal state-patch path so it's
                    # auditable. The winner's party_name → recipient.
                    winner_seat = enc.table_state.find_seat(table_outcome.pot_awarded_to)
                    if winner_seat is not None:
                        outcome.table_pot_award = {
                            "recipient": winner_seat.party_name,
                            "stake_kind": table_outcome.stake_kind,
                            "stake_descriptor": table_outcome.stake_descriptor,
                        }
                    snapshot.pending_resolution_signal = _build_resolution_signal(enc)
                if table_outcome.narration_hint:
                    enc.narrator_hints = [table_outcome.narration_hint]
                _legacy_beat_path = False
```

> **`_random` import:** add `import random as _random` to the top of `narration_apply.py` if not already present (check the existing imports first; if a `random` import exists under a different alias, reuse it).
>
> **`outcome.table_pot_award`:** add `table_pot_award: dict | None = None` to `NarrationApplyOutcome`.
>
> **As-built (post-implementation, authoritative):**
> - **Award is applied INLINE in the branch, not via a downstream consumer.** The existing `gold_change` path also mutates gold inline in `narration_apply` (there is no downstream reward-consumer pattern), so the table money award matches it: on a PC money winner, `winner_char.core.inventory.gold += pot_total`, with a `logger.info` and an `economy.table_pot_award` watcher event for parity. The event fires **unconditionally** for the money path (incl. NPC winners and zero-pot) so the GM panel never goes blind; the gold mutation only runs for a PC winner with `pot_total > 0`. A PC winner whose `party_name` doesn't resolve **fails loud**; an NPC winner is an intentional gold-ledger no-op (still observable). A `pot_awarded_to` not found in seats **raises** (engine/state mismatch).
> - **Money amount is an MVP proxy.** `pot_total = sum(pot.contributions.values())` (abstract chips) approximates the prize; the authoritative money value is the **content-declared stake** (Task 16). Marked with a `TODO(task-16)`.
> - **SOUL-gate exemption (load-bearing).** `_gate_applies_to_encounter` (narration_apply.py) MUST exempt `table_resolution` alongside `sealed_letter_lookup` — a player's classified "I raise"/"I fold" is their explicit consent frame, not narrator-inferred prose. Without the exemption, `_filter_inferred_pc_beats` silently drops every PC table commit on the live narrator path (`from_explicit_action=False`) and the table eats player actions in production. Locked by `test_soul_gate_exempts_table_resolution`.

- [ ] **Step 6: Run the branch test + a narration regression slice**

Run: `uv run pytest tests/server/test_table_branch_unit.py tests/server/ -k "narration_apply" -q`
Expected: PASS (BeatSelection tests pass; existing narration_apply tests unaffected — the new branch only fires for `table_resolution`).

- [ ] **Step 7: Commit**

```bash
uv run ruff check sidequest/agents/orchestrator.py sidequest/server/narration_apply.py
git add sidequest/agents/orchestrator.py sidequest/server/narration_apply.py tests/server/test_table_branch_unit.py
git commit -m "feat(table): route per-seat commits through exclusive table_resolution branch"
```

---

### Task 13: Perception firewall — per-seat private projection

**Files:**
- Modify: `sidequest/server/dispatch/confrontation.py` (`make_confrontation_frame_supplier` / `build_confrontation_payload`)
- Test: `tests/server/dispatch/test_table_perception_firewall.py`

> **Context:** the frame supplier (`confrontation.py:320`) already projects a per-recipient `ConfrontationPayload` keyed by the seated PC. For table encounters it must include **only that player's own seat private_state** plus public table state (pot, folds, bets, order) — never another seat's cards — until showdown, when the filter lifts and all hands broadcast. This is a behavior test (per No-Source-Text-Wiring), not a grep.

- [ ] **Step 1: Write the failing test**

Create `tests/server/dispatch/test_table_perception_firewall.py`:

```python
from sidequest.server.dispatch.confrontation import project_table_frame_for_seat
from sidequest.game.table.types import TablePot, TableSeat, TableState


def _state(resolved=False) -> TableState:
    seats = [
        TableSeat(seat_id="seat_1", party_name="A", is_pc=True, status="active",
                  private_state={"cards": ["AS", "AH"], "strength_band": "strong"}),
        TableSeat(seat_id="seat_2", party_name="B", is_pc=True, status="active",
                  private_state={"cards": ["2C", "7D"], "strength_band": "weak"}),
    ]
    st = TableState(
        game_kind="poker", seats=seats,
        pot=TablePot(stake_kind="money", stake_descriptor="pot",
                     contributions={"seat_1": 2, "seat_2": 2}),
        order=["seat_1", "seat_2"], dealer_seat="seat_1", max_decision_points=3,
        resolved_winner="seat_1" if resolved else None,
    )
    return st


def test_pre_showdown_frame_hides_other_seats_hand():
    st = _state(resolved=False)
    frame = project_table_frame_for_seat(st, seat_id="seat_1")
    own = next(s for s in frame["seats"] if s["seat_id"] == "seat_1")
    other = next(s for s in frame["seats"] if s["seat_id"] == "seat_2")
    assert own["private_state"]["cards"] == ["AS", "AH"]
    assert "cards" not in other.get("private_state", {})  # firewall
    # public table state always present
    assert frame["pot"]["contributions"] == {"seat_1": 2, "seat_2": 2}


def test_showdown_frame_reveals_all_hands():
    st = _state(resolved=True)
    frame = project_table_frame_for_seat(st, seat_id="seat_1")
    other = next(s for s in frame["seats"] if s["seat_id"] == "seat_2")
    assert other["private_state"]["cards"] == ["2C", "7D"]  # revealed


def test_unseated_socket_gets_public_only():
    st = _state(resolved=False)
    frame = project_table_frame_for_seat(st, seat_id=None)
    for s in frame["seats"]:
        assert "cards" not in s.get("private_state", {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/dispatch/test_table_perception_firewall.py -v`
Expected: FAIL — `ImportError: cannot import name 'project_table_frame_for_seat'`.

- [ ] **Step 3: Add the projection function**

In `sidequest/server/dispatch/confrontation.py`, add:

```python
def project_table_frame_for_seat(table_state, *, seat_id: str | None) -> dict:
    """Per-recipient table frame: own private_state only (+ public state) until
    showdown, when all hands reveal. ``seat_id=None`` (unseated/lobby socket)
    gets public-only. The perception firewall pointed at table_state — no new
    perception infra (ADR-104/105 reuse)."""
    revealed = table_state.resolved_winner is not None
    seats_out = []
    for seat in table_state.seats:
        show_private = revealed or (seat_id is not None and seat.seat_id == seat_id)
        seats_out.append(
            {
                "seat_id": seat.seat_id,
                "party_name": seat.party_name,
                "is_pc": seat.is_pc,
                "status": seat.status,
                # deepcopy (not shallow dict()) — privacy boundary: fully decouple
                # the per-recipient frame from canonical table_state (cards list,
                # ReadResult.info dict) regardless of engine mutation discipline.
                "private_state": copy.deepcopy(seat.private_state) if show_private else {},
            }
        )
    return {
        "game_kind": table_state.game_kind,
        "seats": seats_out,
        "pot": {
            "stake_kind": table_state.pot.stake_kind,
            "stake_descriptor": table_state.pot.stake_descriptor,
            "contributions": dict(table_state.pot.contributions),
        },
        "order": list(table_state.order),
        "dealer_seat": table_state.dealer_seat,
        "decision_point": table_state.decision_point,
        "max_decision_points": table_state.max_decision_points,
        "resolved_winner": table_state.resolved_winner,
    }
```

> **Wiring into the supplier:** in `make_confrontation_frame_supplier._frame_for` (line 352), when `encounter.table_state is not None`, resolve the recipient's seat (match `recipient_actor` name → `table_state` seat by `party_name`, or `None` for unseated) and attach `project_table_frame_for_seat(encounter.table_state, seat_id=resolved_seat_id)` to the payload. Read how `build_confrontation_payload` assembles `per_pc_dict` and add a `"table_state": <projection>` key to the returned `ConfrontationPayload` (add the field to `ConfrontationPayload` in `sidequest/protocol/messages.py` as `table_state: dict | None = None`). Pre-showdown, each socket sees only its own hand; at showdown the projection reveals all.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/dispatch/test_table_perception_firewall.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
uv run ruff check sidequest/server/dispatch/confrontation.py
git add sidequest/server/dispatch/confrontation.py sidequest/protocol/messages.py tests/server/dispatch/test_table_perception_firewall.py
git commit -m "feat(table): per-seat private projection in the confrontation frame supplier"
```

---

### Task 14: Barrier denominator — folded/out seats drop

**Files:**
- Modify: `sidequest/server/session_room.py` (add `_table_folded_player_ids`, `mark_table_folded`, `clear_table_folds`; subtract in `effective_barrier_count`)
- Test: `tests/server/test_table_barrier_denominator.py`

> **Context:** `effective_barrier_count` (`session_room.py:722`) returns PLAYING peers minus `_crash_released`. `_crash_released` clears every interaction (`drain_pending_actions`, line 776). Folded seats must persist across decision points (multiple interactions within one hand), so add a parallel set cleared only at table teardown.

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_table_barrier_denominator.py`:

```python
from sidequest.server.session_room import SessionRoom  # adjust import to the real class name


def _room_with_players(n: int):
    # Use the existing test helper/fixture for seating PLAYING peers. See
    # tests/server/ for the canonical SessionRoom construction helper and
    # reuse it here (e.g. a conftest fixture or a _seat_playing(room, id) util).
    room = SessionRoom(slug="table-test")  # adjust ctor to match real signature
    for i in range(1, n + 1):
        room._seat_playing(f"p{i}")  # replace with the real seating call
    return room


def test_folded_player_drops_from_denominator():
    room = _room_with_players(3)
    assert room.effective_barrier_count() == 3
    room.mark_table_folded("p2")
    assert room.effective_barrier_count() == 2


def test_table_fold_survives_interaction_drain():
    room = _room_with_players(3)
    room.mark_table_folded("p2")
    room.drain_pending_actions()  # clears crash-release, must NOT clear table folds
    assert room.effective_barrier_count() == 2


def test_clear_table_folds_restores_denominator():
    room = _room_with_players(3)
    room.mark_table_folded("p2")
    room.clear_table_folds()
    assert room.effective_barrier_count() == 3


def test_mark_table_folded_is_idempotent():
    room = _room_with_players(3)
    room.mark_table_folded("p2")
    room.mark_table_folded("p2")
    assert room.effective_barrier_count() == 2
```

> **Implementer note:** before writing, open `tests/server/` and find the canonical way a `SessionRoom` with PLAYING peers is constructed in existing barrier tests (e.g. `test_*barrier*`, `test_*crash*`). Replace the `_room_with_players` placeholders above with that real helper so the test matches production seating. Do not invent a new seating path.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_table_barrier_denominator.py -v`
Expected: FAIL — `AttributeError: 'SessionRoom' object has no attribute 'mark_table_folded'`.

- [ ] **Step 3: Add the parallel fold set**

In `sidequest/server/session_room.py`, add the field next to `_crash_released` (line 207):

```python
    # Table confrontations: seats that folded/went out drop from the barrier
    # denominator for the REST of the hand (multiple decision points), unlike
    # crash-release which is per-interaction. Cleared only at table teardown.
    _table_folded_player_ids: set[str] = field(default_factory=set)
```

Add the methods near `mark_crash_released` (line 713):

```python
    def mark_table_folded(self, player_id: str) -> None:
        """Drop a folded/out table seat from the barrier denominator until the
        hand ends. Idempotent."""
        with self._lock:
            self._table_folded_player_ids.add(player_id)

    def clear_table_folds(self) -> None:
        """Restore all folded seats to the denominator (call at table teardown)."""
        with self._lock:
            self._table_folded_player_ids.clear()
```

Update `effective_barrier_count` (line 735–737) to subtract both sets:

```python
        with self._lock:
            playing = sum(1 for seat in self._seated.values() if seat.state == LobbyState.PLAYING)
            released = self._crash_released | self._table_folded_player_ids
            raw = playing - len(released)
```

Update the underflow log (line 745–750) to reflect the combined release count (change `len(self._crash_released)` to `len(released)` in the warning args).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_table_barrier_denominator.py -v`
Expected: PASS (4 tests).

> **Wiring the fold-mark + teardown-clear:** in the table_resolution branch (Task 12), after a seat transitions to `folded`/`out`, call `room.mark_table_folded(<player_id>)` for PC seats (map seat→player_id via `snapshot.player_seats`); and at confrontation teardown (where `enc.resolved` is finalized for table types) call `room.clear_table_folds()`. Add a focused behavior test in `tests/server/test_table_resolution_wiring.py` (Task 15) that a folded PC seat lowers `effective_barrier_count` for the next decision point.

- [ ] **Step 5: Run the barrier regression slice**

Run: `uv run pytest tests/server/ -k "barrier or crash" -q`
Expected: PASS (crash-release behavior unchanged).

- [ ] **Step 6: Commit**

```bash
uv run ruff check sidequest/server/session_room.py
git add sidequest/server/session_room.py tests/server/test_table_barrier_denominator.py
git commit -m "feat(table): drop folded seats from the barrier denominator for the hand"
```

---

### Task 15: Required end-to-end wiring test

**Files:**
- Test: `tests/server/test_table_resolution_wiring.py`

> **Goal (spec §Testing, required):** drive a `table_resolution` confrontation through the **real** `_apply_narration_result_to_snapshot` with synthetic seat commits; assert `table.showdown` fired **AND** a state-patch awarded the pot — proving the new branch is reachable from the production narration path, not just callable in isolation.

- [ ] **Step 1: Study the canonical wiring-test shape**

Read `tests/server/dispatch/test_sealed_letter_dispatch_integration.py` and `tests/server/test_location_description_emit.py` (the CLAUDE.md canonical fixture-driven behavior test). Reuse their synthetic genre-pack + snapshot fixtures and the real `_apply_narration_result_to_snapshot` invocation. Capture spans via the existing OTEL test-capture fixture used in `tests/telemetry/` / `tests/server/` (find the fixture that records emitted spans — e.g. an in-memory span exporter conftest fixture).

- [ ] **Step 2: Write the wiring test**

Create `tests/server/test_table_resolution_wiring.py`:

```python
"""End-to-end wiring: a table_resolution turn through the REAL narration apply.

Asserts table.showdown fired and a state patch awarded the pot — the new branch
is reachable from the production path, not just unit-callable. OTEL span
assertion per CLAUDE.md "No Source-Text Wiring Tests".
"""

import random

import pytest

from sidequest.agents.orchestrator import BeatSelection
# Reuse the project's span-capture fixture + synthetic pack/snapshot builders.
# Import the real apply entrypoint:
from sidequest.server.narration_apply import _apply_narration_result_to_snapshot

import sidequest.game.table.poker  # noqa: F401


@pytest.fixture
def poker_table_snapshot(synthetic_table_pack, make_snapshot):
    """A snapshot carrying an active 2-seat poker table_resolution encounter,
    max_decision_points=1 so a single resolve goes straight to showdown.

    Build via the table-instantiation helper so the fixture matches production:
        from sidequest.server.dispatch.encounter_lifecycle import instantiate_table_encounter
        enc = instantiate_table_encounter(cdef=..., player_names=["Doc"],
            npc_names=["Ringo"], stake_kind="money", stake_descriptor="the pot", seed=1)
        snapshot = make_snapshot(pack=synthetic_table_pack, encounter=enc, characters=[...])
    """
    ...  # implement using the project's existing fixture builders


def test_table_turn_reaches_showdown_and_awards_pot(poker_table_snapshot, captured_spans, synthetic_table_pack):
    snapshot = poker_table_snapshot
    # force a deterministic winner
    snapshot.encounter.table_state.find_seat("seat_1").private_state["strength"] = 10 ** 9
    snapshot.encounter.table_state.find_seat("seat_2").private_state["strength"] = 1

    result = type("R", (), {})()
    result.beat_selections = [
        BeatSelection(actor="Doc", beat_id="call", amount=1),
        BeatSelection(actor="Ringo", beat_id="call", amount=1),
    ]
    # minimal result shape — mirror the other wiring tests' result stub fields

    outcome = _apply_narration_result_to_snapshot(
        snapshot=snapshot,
        result=result,
        pack=synthetic_table_pack,
        player_name="Doc",
        from_explicit_action=False,
        # ... remaining required kwargs per the real signature
    )

    # 1) showdown span fired
    assert any(s.name == "table.showdown" for s in captured_spans), \
        "table.showdown span did not fire — branch not reached"
    # 2) encounter resolved with a table winner
    assert snapshot.encounter.resolved is True
    assert snapshot.encounter.outcome == "table_winner:seat_1"
    # 3) pot award reached the outcome (state-patch path)
    assert outcome.table_pot_award is not None
    assert outcome.table_pot_award["recipient"] == "Doc"
```

> **Implementer:** fill the `...` fixtures using the project's real builders (search `tests/server/` and `tests/fixtures/` for `make_snapshot`, synthetic-pack factories, and the span-capture fixture). Match the exact `_apply_narration_result_to_snapshot` signature (read its `def`). The three assertions are the contract — keep them; flesh out the setup to match production.

- [ ] **Step 3: Run test to verify it fails, then passes**

Run: `uv run pytest tests/server/test_table_resolution_wiring.py -v`
Expected first run: FAIL (fixtures unimplemented). After wiring the fixtures to real builders: PASS.

- [ ] **Step 4: Commit**

```bash
uv run ruff check tests/server/test_table_resolution_wiring.py
git add tests/server/test_table_resolution_wiring.py
git commit -m "test(table): end-to-end wiring — table turn reaches showdown + awards pot via real apply path"
```

---

## Phase E — Content (poker, then auction)

### Task 16: spaghetti_western poker → table_resolution

**Files:**
- Modify: `sidequest-content/genre_packs/spaghetti_western/rules.yaml` (the `poker` confrontation)
- Test: `sidequest-server/tests/genre/test_poker_table_content.py`

> **Context:** the content repo is `sidequest-content` (single source of truth). The server loads it via `SIDEQUEST_GENRE_PACKS`. First read the current `poker` confrontation block in `spaghetti_western/rules.yaml` to preserve its label/category/beats.

- [ ] **Step 1: Write the failing test (in the server repo, which loads content)**

Create `sidequest-server/tests/genre/test_poker_table_content.py`:

```python
from sidequest.genre.loader import load_genre_pack  # adjust to the real loader entrypoint
from sidequest.genre.models.rules import ResolutionMode, WinCondition


def test_spaghetti_western_poker_is_table_resolution():
    pack = load_genre_pack("spaghetti_western")  # adjust signature to real loader
    poker = next(c for c in pack.rules.confrontations if c.confrontation_type == "poker")
    assert poker.resolution_mode == ResolutionMode.table_resolution
    assert poker.win_condition == WinCondition.table_showdown
    assert poker.table_game == "poker"
    assert poker.max_decision_points >= 1
    beat_ids = {b.id for b in poker.beats}
    assert {"fold", "call", "cheat", "accuse", "read_table"} <= beat_ids
```

> **Implementer:** confirm the real loader call from existing `tests/genre/` tests (e.g. `test_*content_loading.py`) and match it.

- [ ] **Step 2: Run test to verify it fails**

Run (from `sidequest-server/`): `uv run pytest tests/genre/test_poker_table_content.py -v`
Expected: FAIL — current `poker` confrontation is a dial/opposed shape, not `table_resolution`.

- [ ] **Step 3: Read the current poker block**

Read `sidequest-content/genre_packs/spaghetti_western/rules.yaml` and locate the `poker` entry under `confrontations:`.

- [ ] **Step 4: Rewrite the poker confrontation**

Replace the `poker` confrontation block's resolution fields. Set:

```yaml
  - type: poker
    label: "Poker"
    category: social
    resolution_mode: table_resolution
    win_condition: table_showdown
    table_game: poker
    max_decision_points: 3
    # dual dials dropped (table types read table_state, not metrics)
    beats:
      - { id: fold,       label: "Fold",            stat_check: WIS, base: 0 }
      - { id: call,       label: "Call",            stat_check: WIS, base: 0 }
      - { id: bet,        label: "Bet",             stat_check: CHA, base: 1 }
      - { id: raise,      label: "Raise",           stat_check: CHA, base: 2 }
      - { id: bluff,      label: "Bluff",           stat_check: CHA, base: 2 }
      - { id: read_table, label: "Read the Table",  stat_check: WIS, base: 1 }
      - { id: cheat,      label: "Cheat",           stat_check: DEX, base: 3 }
      - { id: accuse,     label: "Accuse of Cheating", stat_check: WIS, base: 2 }
```

> Preserve any existing `mood`/`escalates_to`/`intent_verbs` on the original block. Remove `player_metric`/`opponent_metric` (content SOUL: prefer removal for honesty; the loader accepts their absence for table types).

- [ ] **Step 5: Run test to verify it passes**

Run (from `sidequest-server/`): `uv run pytest tests/genre/test_poker_table_content.py -v`
Expected: PASS.

- [ ] **Step 6: Full pack-load regression**

Run (from `sidequest-server/`): `uv run pytest tests/genre/ -q`
Expected: PASS (spaghetti_western still loads clean).

- [ ] **Step 7: Commit (two repos)**

```bash
# content repo
cd sidequest-content && git add genre_packs/spaghetti_western/rules.yaml && \
  git commit -m "feat(spaghetti_western): poker → free-for-all table_resolution" && cd ..
# server repo
cd sidequest-server && git add tests/genre/test_poker_table_content.py && \
  git commit -m "test(table): assert spaghetti_western poker is table_resolution" && cd ..
```

---

### Task 17: Auction kind resolver + tea_and_murder auction content

**Files:**
- Create: `sidequest-server/sidequest/game/table/auction.py`
- Modify: `sidequest-server/sidequest/game/table/__init__.py` (import auction so it registers) — see note
- Modify: `sidequest-content/genre_packs/tea_and_murder/rules.yaml` (the `auction` confrontation)
- Test: `sidequest-server/tests/game/table/test_auction.py`, `sidequest-server/tests/genre/test_auction_table_content.py`

- [ ] **Step 1: Write the failing resolver test**

Create `tests/game/table/test_auction.py`:

```python
import random

from sidequest.game.table.auction import AuctionTableGame
from sidequest.game.table.engine import deal_table, resolve_table
from sidequest.game.table.types import TableCommit, TablePot, TableSeat, TableState

import sidequest.game.table.auction  # noqa: F401  (registers auction)


def _state(n=2, max_dp=1) -> TableState:
    seats = [
        TableSeat(seat_id=f"seat_{i}", party_name=f"P{i}", is_pc=True, status="active", private_state={})
        for i in range(1, n + 1)
    ]
    return TableState(
        game_kind="auction", seats=seats,
        pot=TablePot(stake_kind="item", stake_descriptor="the Ming vase",
                     contributions={s.seat_id: 0 for s in seats}),
        order=[s.seat_id for s in seats], dealer_seat="seat_1", max_decision_points=max_dp,
    )


def test_deal_assigns_secret_valuations():
    game = AuctionTableGame()
    seats = _state(3).seats
    pot = TablePot(stake_kind="item", stake_descriptor="vase", contributions={s.seat_id: 0 for s in seats})
    game.deal(seats, pot, random.Random(1))
    for s in seats:
        assert s.private_state["valuation"] > 0
        assert s.private_state["max_bid"] >= s.private_state["valuation"] // 2
        assert "strength_band" in s.private_state  # NPC policy reads this


def test_highest_standing_bid_wins_at_showdown():
    st = _state(2, max_dp=1)
    deal_table(st, rng=random.Random(2))
    # strength() for auction = current bid contribution
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="raise_bid", amount=10),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="raise_bid", amount=3),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(2))
    assert out.showdown is True
    assert out.resolved_winner == "seat_1"


def test_withdraw_folds_seat():
    st = _state(3, max_dp=3)
    deal_table(st, rng=random.Random(3))
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="raise_bid", amount=5),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="withdraw"),
        "seat_3": TableCommit(seat_id="seat_3", beat_id="raise_bid", amount=4),
    }
    resolve_table(st, commits=commits, rng=random.Random(3))
    assert st.find_seat("seat_2").status == "folded"


def test_read_room_returns_rival_valuation_band():
    st = _state(2, max_dp=3)
    deal_table(st, rng=random.Random(4))
    st.find_seat("seat_2").private_state["strength_band"] = "decent"
    commits = {
        "seat_1": TableCommit(seat_id="seat_1", beat_id="read_room", target_seat="seat_2"),
        "seat_2": TableCommit(seat_id="seat_2", beat_id="raise_bid", amount=1),
    }
    out = resolve_table(st, commits=commits, rng=random.Random(4))
    assert out.read_results["seat_1"].info["strength_band"] == "decent"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/table/test_auction.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.table.auction'`.

> **Engine note:** the auction beats `raise_bid` and `withdraw` must resolve. `raise_bid` is already in `_POT_ACTIONS` (Task 8). Add `withdraw` handling: in `engine._apply_commit`, treat `withdraw` like `fold` (status → folded, emit `table_fold_span`). Update the fold check to `if beat in ("fold", "withdraw"):`. For auction, `strength()` returns the seat's current bid (pot contribution), so the engine's `_showdown` strength comparison must read `game.strength(seat)` which the auction kind defines from the pot — pass the pot into strength. Simplest: auction `strength(seat)` reads `seat.private_state["_current_bid"]`, and `raise_bid` mirrors the amount into `private_state["_current_bid"]`. Add that mirror in `_apply_commit`'s pot branch only when `game_kind == "auction"` — OR (cleaner) have the auction kind's `strength` read from a closure. **Decision:** add to `_apply_commit` pot branch: after adjusting `pot.contributions`, also set `seat.private_state["_current_bid"] = pot.contributions[seat_id]`. This keeps strength kind-local. Document this one-line addition in Step 4.

- [ ] **Step 3: Write the auction kind**

Create `sidequest/game/table/auction.py`:

```python
"""Auction table-game kind — proves the model is the general free-for-all.

Zero TableState changes: same seats + pot + order. private_state holds a secret
valuation / max_bid (no cards). Beats: raise_bid / bluff / read_room / withdraw.
pot.contributions is the current high bid; strength() = the seat's standing bid
(mirrored into _current_bid by the engine pot branch). Cheat/Accuse are NOT
registered for auction (optional content — a rigged auction could add them).
"""

from __future__ import annotations

import random

from sidequest.game.table.registry import TableGame, register_table_game
from sidequest.game.table.types import ReadResult, TablePot, TableSeat

_BANDS = ("weak", "marginal", "decent", "strong", "monster")


def _band_for_valuation(valuation: int, ceiling: int) -> str:
    frac = valuation / ceiling
    idx = min(len(_BANDS) - 1, int(frac * len(_BANDS)))
    return _BANDS[idx]


class AuctionTableGame(TableGame):
    kind = "auction"
    _CEILING = 100

    def deal(self, seats: list[TableSeat], pot: TablePot, rng: random.Random) -> None:
        for seat in seats:
            valuation = rng.randint(10, self._CEILING)
            seat.private_state["valuation"] = valuation
            seat.private_state["max_bid"] = valuation  # won't bid above own valuation
            seat.private_state["strength_band"] = _band_for_valuation(valuation, self._CEILING)
            seat.private_state["_current_bid"] = 0

    def strength(self, seat: TableSeat) -> int:
        # showdown: highest standing bid (≤ own max_bid) wins
        bid = int(seat.private_state.get("_current_bid", 0))
        max_bid = int(seat.private_state.get("max_bid", 0))
        return bid if bid <= max_bid else -1  # an over-max bid is invalid → loses

    def read(self, reader: TableSeat, target: TableSeat, *, reader_stat: int) -> ReadResult:
        info = {
            "target_seat": target.seat_id,
            "strength_band": target.private_state.get("strength_band", "unknown"),
        }
        return ReadResult(target_seat=target.seat_id, info=info)


register_table_game(AuctionTableGame())
```

- [ ] **Step 4: Add `withdraw` + `_current_bid` mirror to the engine**

In `sidequest/game/table/engine.py`:

Change the fold check in `_apply_commit`:

```python
    if beat in ("fold", "withdraw"):
        seat.status = "folded"
        with table_fold_span(seat=seat_id, decision_point=state.decision_point):
            pass
        return
```

Add the bid mirror in the pot branch:

```python
    if beat in _POT_ACTIONS:
        state.pot.contributions[seat_id] = state.pot.contributions.get(seat_id, 0) + max(0, commit.amount)
        seat.private_state["_current_bid"] = state.pot.contributions[seat_id]
        return
```

Register `read_room` is already routed (Task 8 handles `read_table`/`read_room`). Ensure `register` of the auction kind happens: add to `game/table/__init__.py` re-export block a side-effect import so the kind registers when the package is used by the engine path:

```python
# Register built-in kinds on package import (side effects).
from sidequest.game.table import auction as _auction  # noqa: E402,F401
from sidequest.game.table import poker as _poker  # noqa: E402,F401
```

> Place these AFTER the `from .types import ...` block in `__init__.py`. (poker's import here also centralizes its registration; keep the explicit `import ...poker` in tests for clarity.)

- [ ] **Step 5: Run the auction resolver test + the engine/poker tests (registration regression)**

Run: `uv run pytest tests/game/table/ -v`
Expected: PASS (auction + all prior table tests; no double-registration error — the registry raises on dup, so confirm `poker`/`auction` register exactly once via the package import).

> If a double-registration error appears, it means a kind is imported twice through different paths. Fix by ensuring registration only happens at module top-level (it does) and the registry dedup is by kind — the test `test_double_register_same_kind_raises` guards this; the package-import + test-import both hit the same module object, so Python's import cache prevents re-execution. No action needed unless an error actually surfaces.

- [ ] **Step 6: Write + run the auction content test**

Create `sidequest-server/tests/genre/test_auction_table_content.py`:

```python
from sidequest.genre.loader import load_genre_pack  # adjust to real loader
from sidequest.genre.models.rules import ResolutionMode, WinCondition


def test_tea_and_murder_auction_is_table_resolution():
    pack = load_genre_pack("tea_and_murder")
    auction = next(c for c in pack.rules.confrontations if c.confrontation_type == "auction")
    assert auction.resolution_mode == ResolutionMode.table_resolution
    assert auction.win_condition == WinCondition.table_showdown
    assert auction.table_game == "auction"
    beat_ids = {b.id for b in auction.beats}
    assert {"raise_bid", "withdraw", "read_room"} <= beat_ids
```

Run (from `sidequest-server/`): `uv run pytest tests/genre/test_auction_table_content.py -v`
Expected: FAIL (auction is still a dial shape).

- [ ] **Step 7: Rewrite the tea_and_murder auction confrontation**

Read `sidequest-content/genre_packs/tea_and_murder/rules.yaml`, locate `auction` under `confrontations:`, and set:

```yaml
  - type: auction
    label: "The Auction"
    category: social
    resolution_mode: table_resolution
    win_condition: table_showdown
    table_game: auction
    max_decision_points: 3
    beats:
      - { id: raise_bid, label: "Raise the Bid",  stat_check: CHA, base: 1 }
      - { id: bluff,     label: "Bluff",          stat_check: CHA, base: 2 }
      - { id: read_room, label: "Read the Room",  stat_check: WIS, base: 1 }
      - { id: withdraw,  label: "Withdraw",       stat_check: WIS, base: 0 }
```

> Preserve original `mood`/`intent_verbs`. Remove `player_metric`/`opponent_metric`. No `cheat`/`accuse` beats — Glenross won't (per spec); a rigged auction could author them later.

- [ ] **Step 8: Run the content test + full pack regression**

Run (from `sidequest-server/`): `uv run pytest tests/genre/test_auction_table_content.py tests/genre/ -q`
Expected: PASS (tea_and_murder loads clean).

- [ ] **Step 9: Commit (two repos)**

```bash
cd sidequest-server && uv run ruff check sidequest/game/table/auction.py sidequest/game/table/engine.py && \
  git add sidequest/game/table/auction.py sidequest/game/table/engine.py sidequest/game/table/__init__.py \
          tests/game/table/test_auction.py tests/genre/test_auction_table_content.py && \
  git commit -m "feat(table): add auction kind (zero model changes) + withdraw/bid-mirror in engine" && cd ..
cd sidequest-content && git add genre_packs/tea_and_murder/rules.yaml && \
  git commit -m "feat(tea_and_murder): auction → free-for-all table_resolution" && cd ..
```

---

## Final verification

- [ ] **Step 1: Full server suite**

Run (from `sidequest-server/`): `uv run pytest -q`
Expected: PASS (all green).

- [ ] **Step 2: Lint + type check**

Run (from `sidequest-server/`): `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: clean.

- [ ] **Step 3: Cross-repo gate**

Run (from orchestrator root): `just check-all`
Expected: PASS.

---

## Self-Review (Architect, against the spec)

**Spec coverage map:**

| Spec section | Task(s) |
|---|---|
| `StructuredEncounter.table_state` additive field | 2 |
| `resolution_mode: table_resolution` + `win_condition: table_showdown` + `table_game` discriminator | 3 |
| State model (TableSeat/TablePot/TableState, opaque private_state, ephemeral) | 1 |
| Commit-channel reuse (beat_selections keyed by seat, +amount slot) | 12 |
| Resolver behind ADR-117 seam (`resolve_table`/`deal_table`) | 10 (+engine 7,8) |
| New exclusive narration_apply branch, double-apply guard | 12 |
| Round lifecycle: instantiate & deal (+ ≥2 invariant) | 11 (+engine 7) |
| Decision-point loop + showdown + teardown (pot via state-patch) | 7, 8, 12 |
| Cheat / Read / Accuse sub-loop (real hand, trace, opposed check, forfeit) | 8 |
| NPC seat commit policy (strength_band, pot, OCEAN/disposition) | 9 |
| Private-info delivery (perception firewall on table_state; reveal at showdown) | 13 |
| Folded/out seats drop from barrier denominator | 14 |
| OTEL span inventory (8 spans) | 4 (emitted across 7,8,9,11,12) |
| Invariants & fail-loud (≥2 seats, unknown kind, beat∈authored, exclusive, readable strength, no cross-seat leak) | 1,3,5,7,8,13,14 |
| Wiring test (real apply path → table.showdown + pot patch) | 15 |
| Auction (second instance, zero model changes) | 17 |
| Content changes (spaghetti_western poker, tea_and_murder auction) | 16, 17 |

**Type consistency check (names used across tasks):** `TableSeat`/`TablePot`/`TableState`/`TableCommit`/`TableResolutionOutcome`/`CheatResult`/`ReadResult`/`TableNeedsOthersError` (Task 1) — referenced identically in 5,6,7,8,9,10,11,13,17. `TableGame`/`register_table_game`/`get_table_game`/`UnknownTableGameError` (Task 5) — used in 6,7,10,17. `deal_table`/`resolve_table` engine functions (7) → seam methods of same name (10) → consumed in 11,12. Span factory names (Task 4) match emit sites in 7,8,9,11,12. `BeatSelection.amount` (12) consumed in the same branch. `project_table_frame_for_seat` (13). `mark_table_folded`/`clear_table_folds` (14). Beat ids: poker `{fold,call,bet,raise,bluff,read_table,cheat,accuse}` (Task 16 content ↔ Task 8 engine `read_table`); auction `{raise_bid,bluff,read_room,withdraw}` (Task 17 content ↔ engine `read_room`/`withdraw`/`_POT_ACTIONS`). Consistent.

**Known integration seams the implementer MUST resolve against live signatures (flagged inline, not placeholders):** (a) the exact `_apply_narration_result_to_snapshot` kwargs and `NarrationApplyOutcome` field set (Task 12, 15); (b) the real `SessionRoom` seating helper in tests (Task 14); (c) the genre loader entrypoint (Tasks 16, 17); (d) the downstream consumer that turns `outcome.table_pot_award` into the actual gold/item state patch (Task 12 — reuse the existing resolution-reward path; Task 15 asserts it lands). These are wiring-to-existing-code points where the plan gives the contract and points at the canonical pattern to copy, per the codebase's anti-stub / verify-wiring rules.
