# sidequest-understudy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `sidequest-understudy` — an autonomous, *naive* simulated-player client that joins a real SideQuest session through the actual React UI in a browser, role-plays a seat in persona, and produces a graded affordance-findings report.

**Architecture:** A perceive→decide→act→observe loop per bot seat. Perception is Playwright's ARIA snapshot rendered as structured text (screen-reader model, no pixels). Decision is one LLM call behind a model-agnostic `ActionModel` seam (anthropic / ollama / claude_p / fake). Actuation resolves the bot's *named* target (role + accessible name) against the live page. Findings reconcile the bot's subjective `report_confusion` stream against objective stuck-signals into CONFIRMED / BEHAVIORAL / CLAIMED grades, written to a self-contained report directory alongside server-side `narration.turn` OTEL spans pulled from Jaeger.

**Tech Stack:** Python 3.12, uv, Playwright (chromium), pydantic v2, Typer, httpx, anthropic SDK, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-06-11-simulated-player-understudy-design.md`

**The naivety invariant (governs every task):** the only thing that ever reaches the brain is the rendered, semantic page. No step may inject privileged knowledge (server protocol models, pre-digested action menus, role-alias rescue maps). A bot asking for a control that isn't there is a *finding*, not a bug to paper over.

**Repo conventions:** new repo lives at `sidequest-understudy/` inside the orchestrator root (sibling of `sidequest-server/` etc.). Subrepos are github-flow with `develop` as the integration branch, and the pf branch-protection hook blocks commits while the shell cwd sits in a subrepo on `develop` — so **all work happens on `feature/understudy-bootstrap`**; the final task publishes the repo and PRs to `develop`.

---

### Task 1: Repo bootstrap

**Files:**
- Create: `sidequest-understudy/pyproject.toml`
- Create: `sidequest-understudy/.gitignore`
- Create: `sidequest-understudy/src/understudy/__init__.py` (and subpackage `__init__.py` files)
- Create: `sidequest-understudy/tests/__init__.py`

- [ ] **Step 1: Initialize the repo on a feature branch**

```bash
mkdir -p /Users/slabgorb/Projects/oq-2/sidequest-understudy
cd /Users/slabgorb/Projects/oq-2/sidequest-understudy
git init -b develop
git checkout -b feature/understudy-bootstrap
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "sidequest-understudy"
version = "0.1.0"
description = "Naive simulated-player playtest client for SideQuest — as naive as the user"
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.49",
    "httpx>=0.27",
    "pydantic>=2.7",
    "typer>=0.12",
    "pyyaml>=6.0",
    "anthropic>=0.40",
]

[project.scripts]
understudy = "understudy.cli:app"

[dependency-groups]
dev = ["pytest>=8", "pytest-asyncio>=0.24", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/understudy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
reports/
.pytest_cache/
.ruff_cache/
dist/
```

- [ ] **Step 4: Create the package skeleton**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-understudy
mkdir -p src/understudy/{persona/archetypes,perception,brain/llm,actuation,findings,report,orchestrate}
mkdir -p tests/wiring runs
touch src/understudy/__init__.py src/understudy/persona/__init__.py \
      src/understudy/perception/__init__.py src/understudy/brain/__init__.py \
      src/understudy/brain/llm/__init__.py src/understudy/actuation/__init__.py \
      src/understudy/findings/__init__.py src/understudy/report/__init__.py \
      src/understudy/orchestrate/__init__.py tests/__init__.py tests/wiring/__init__.py
```

(Empty `__init__.py` files are package markers, not stubs — every module added later lands in an already-real package.)

- [ ] **Step 5: Sync and install the browser**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-understudy
uv sync
uv run playwright install chromium
```

Expected: `uv sync` resolves and creates `.venv`; chromium downloads (or reports already installed).

- [ ] **Step 6: Verify pytest runs (zero tests is fine)**

```bash
uv run pytest -q
```

Expected: `no tests ran` exit code 5 — acceptable at bootstrap.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "chore: bootstrap sidequest-understudy (uv, playwright, package skeleton)"
```

---

### Task 2: Core types

**Files:**
- Create: `sidequest-understudy/src/understudy/types.py`
- Test: `sidequest-understudy/tests/test_types.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_types.py
import pytest
from pydantic import ValidationError

from understudy.types import (
    Finding,
    FrictionSignal,
    Grade,
    Intent,
    IntentKind,
    SignalKind,
    TranscriptRow,
)


def test_act_intent_requires_target():
    with pytest.raises(ValidationError):
        Intent(kind=IntentKind.ACT)


def test_act_intent_with_target_validates():
    i = Intent(kind=IntentKind.ACT, target_role="button", target_name="Send")
    assert i.target_name == "Send"


def test_confusion_requires_reason():
    with pytest.raises(ValidationError):
        Intent(kind=IntentKind.REPORT_CONFUSION)


def test_wait_is_bare():
    i = Intent(kind=IntentKind.WAIT)
    assert i.kind is IntentKind.WAIT


def test_intent_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Intent(kind=IntentKind.WAIT, hitpoints=10)


def test_transcript_row_roundtrips_json():
    row = TranscriptRow(
        seat=2,
        turn=3,
        snapshot='- button "Send"',
        intent=Intent(kind=IntentKind.WAIT),
        resolution="n/a",
        narration_delta="",
        signals=[FrictionSignal(kind=SignalKind.DECIDE_TIMEOUT, seat=2, turn=3, detail="120s")],
    )
    again = TranscriptRow.model_validate_json(row.model_dump_json())
    assert again.signals[0].kind is SignalKind.DECIDE_TIMEOUT


def test_finding_grade_values():
    assert {g.value for g in Grade} == {"confirmed", "behavioral", "claimed"}
    f = Finding(
        grade=Grade.CLAIMED, seat=1, archetype="hesitant", turn=4,
        confusion_reason="cannot tell whose turn it is", signals=[], snapshot_excerpt="…",
    )
    assert f.grade is Grade.CLAIMED
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-understudy && uv run pytest tests/test_types.py -q
```

Expected: FAIL — `ModuleNotFoundError: understudy.types`.

- [ ] **Step 3: Write `src/understudy/types.py`**

```python
"""Core wire-free types shared by every understudy module.

The Intent is the ONLY thing the brain returns: a typed claim about what the
player does next, naming its target the way a player would say it aloud —
never a node id, never a coordinate.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class IntentKind(StrEnum):
    ACT = "act"
    REPORT_CONFUSION = "report_confusion"
    WAIT = "wait"


class Intent(BaseModel):
    """What the bot does this cycle. One interaction at a time:
    type into a field (text_input set) OR click a control (text_input None)."""

    model_config = ConfigDict(extra="forbid")

    kind: IntentKind
    target_role: str | None = None  # ARIA role as the bot perceives it ("button")
    target_name: str | None = None  # accessible name as the bot would say it ("Send")
    text_input: str | None = None   # text to type into the target, if any
    reason: str | None = None       # for report_confusion / wait

    @model_validator(mode="after")
    def _shape(self) -> "Intent":
        if self.kind is IntentKind.ACT and not (self.target_role and self.target_name):
            raise ValueError("act intent requires target_role and target_name")
        if self.kind is IntentKind.REPORT_CONFUSION and not self.reason:
            raise ValueError("report_confusion intent requires a reason")
        return self


class SignalKind(StrEnum):
    RESOLUTION_FAILED = "resolution_failed"
    RESOLUTION_AMBIGUOUS = "resolution_ambiguous"
    REPEATED_ACTION = "repeated_action"
    DECIDE_TIMEOUT = "decide_timeout"
    CONSOLE_ERROR = "console_error"
    NO_ACTIONABLE_ELEMENTS = "no_actionable_elements"
    MODEL_ERROR = "model_error"  # malformed model output — down-weighted in reconciliation


class FrictionSignal(BaseModel):
    """One objective stuck-signal observed by the harness (zero LLM judgment)."""

    kind: SignalKind
    seat: int
    turn: int
    detail: str


class TranscriptRow(BaseModel):
    """One perceive→decide→act→observe cycle for one seat."""

    seat: int
    turn: int
    snapshot: str            # the structured-text a11y snapshot the brain saw
    intent: Intent | None    # None when decide failed or timed out
    resolution: str          # "resolved" | "ambiguous" | "failed" | "n/a"
    narration_delta: str     # new text observed after acting
    signals: list[FrictionSignal] = []


class Grade(StrEnum):
    CONFIRMED = "confirmed"    # subjective + objective agree
    BEHAVIORAL = "behavioral"  # objective only — bot muddled through silently
    CLAIMED = "claimed"        # subjective only — wolf-cry candidate, kept but down-ranked


class Finding(BaseModel):
    grade: Grade
    seat: int
    archetype: str
    turn: int
    confusion_reason: str | None
    signals: list[FrictionSignal]
    snapshot_excerpt: str
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_types.py -q
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/understudy/types.py tests/test_types.py
git commit -m "feat: core types — Intent, FrictionSignal, TranscriptRow, Finding"
```

---

### Task 3: Personas and the run manifest

**Files:**
- Create: `sidequest-understudy/src/understudy/persona/archetypes/{narrative_first,mechanics_first,hesitant,engaged_generalist}.yaml`
- Create: `sidequest-understudy/src/understudy/persona/model.py`
- Create: `sidequest-understudy/src/understudy/persona/prompts.py`
- Create: `sidequest-understudy/src/understudy/manifest.py`
- Test: `sidequest-understudy/tests/test_persona.py`, `sidequest-understudy/tests/test_manifest.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_persona.py
import pytest

from understudy.persona.model import Archetype, load_archetype, load_all_archetypes
from understudy.persona.prompts import HISTORY_DEPTH, VERBOSITY_CHAR_CAP, build_system_prompt


def test_four_starting_archetypes_load():
    all_ = load_all_archetypes()
    assert set(all_) == {"narrative_first", "mechanics_first", "hesitant", "engaged_generalist"}


def test_axes_are_validated():
    a = load_archetype("mechanics_first")
    assert 0.0 <= a.narrative_vs_mechanical <= 1.0
    assert a.narrative_vs_mechanical > 0.5  # mechanics_first leans crunch
    assert a.verbosity in ("low", "medium", "high")


def test_unknown_archetype_fails_loud():
    with pytest.raises(FileNotFoundError):
        load_archetype("min_maxer_3000")


def test_system_prompt_is_game_agnostic_and_in_persona():
    a = load_archetype("hesitant")
    prompt = build_system_prompt(a)
    # game-agnostic frame: never teaches the game's rules or affordances
    for forbidden in ("SideQuest", "dice tray", "WebSocket", "chargen"):
        assert forbidden not in prompt
    # the archetype's voice is present
    assert a.prompt_fragment.strip().splitlines()[0] in prompt
    # the three intent kinds are explained
    for kind in ("act", "report_confusion", "wait"):
        assert kind in prompt


def test_mechanical_axis_maps_exist():
    assert set(HISTORY_DEPTH) == {"low", "medium", "high"}
    assert set(VERBOSITY_CHAR_CAP) == {"low", "medium", "high"}
    assert HISTORY_DEPTH["low"] < HISTORY_DEPTH["high"]
```

```python
# tests/test_manifest.py
import pytest

from understudy.manifest import ManifestError, RunManifest, load_manifest


def test_seats_coerce_bare_strings(tmp_path):
    p = tmp_path / "run.yaml"
    p.write_text(
        "name: t\ngenre: g\nworld: w\nsession_url: http://x/play/s\n"
        "seats:\n  - human\n  - mechanics_first\n  - {archetype: hesitant, model: ollama/qwen3:8b}\n"
        "turns: 5\n"
    )
    m = load_manifest(p)
    assert [s.archetype for s in m.seats] == ["human", "mechanics_first", "hesitant"]
    assert m.seats[2].model == "ollama/qwen3:8b"
    assert m.seats[1].model.startswith("anthropic/")  # default backend


def test_unknown_archetype_in_manifest_fails_loud(tmp_path):
    p = tmp_path / "run.yaml"
    p.write_text(
        "name: t\ngenre: g\nworld: w\nsession_url: http://x/p\nseats: [balrog]\nturns: 2\n"
    )
    with pytest.raises(ManifestError, match="balrog"):
        load_manifest(p)


def test_missing_session_url_fails_loud(tmp_path):
    p = tmp_path / "run.yaml"
    p.write_text("name: t\ngenre: g\nworld: w\nseats: [hesitant]\nturns: 2\n")
    with pytest.raises(ManifestError):
        load_manifest(p)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_persona.py tests/test_manifest.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the four archetype YAMLs**

`src/understudy/persona/archetypes/narrative_first.yaml`:

```yaml
id: narrative_first
narrative_vs_mechanical: 0.15   # 0 = pure narrative, 1 = pure crunch
verbosity: medium
decisiveness: medium
affordance_hunger: low
reading_tolerance: high
prompt_fragment: |
  You play for the story. You type what your character does and says as prose,
  and you mostly ignore buttons, numbers, and panels unless you need them.
  You read everything the game tells you, carefully.
```

`src/understudy/persona/archetypes/mechanics_first.yaml`:

```yaml
id: mechanics_first
narrative_vs_mechanical: 0.85
verbosity: low
decisiveness: high
affordance_hunger: high
reading_tolerance: medium
prompt_fragment: |
  You care how the game works. When something mechanical happens, you look
  for the numbers: the roll, the cost, the delta. You actively scan the
  screen for controls and panels that expose the system, and you try them.
```

`src/understudy/persona/archetypes/hesitant.yaml`:

```yaml
id: hesitant
narrative_vs_mechanical: 0.4
verbosity: low
decisiveness: low
affordance_hunger: low
reading_tolerance: medium
prompt_fragment: |
  You are unsure of yourself at the table. You type short, plain actions.
  When you cannot quickly tell what to do or whose turn it is, you wait,
  and if waiting does not help, you say you are confused rather than guess.
```

`src/understudy/persona/archetypes/engaged_generalist.yaml`:

```yaml
id: engaged_generalist
narrative_vs_mechanical: 0.5
verbosity: medium
decisiveness: high
affordance_hunger: medium
reading_tolerance: high
prompt_fragment: |
  You are an experienced player who enjoys both story and system. You read
  thoroughly, act deliberately, and probe the interface methodically when
  something new appears.
```

- [ ] **Step 4: Write `src/understudy/persona/model.py`**

```python
"""Play-style archetypes — the playgroup as test matrix.

An archetype shapes BEHAVIOR AND ATTENTION, not knowledge: a mechanics_first
bot does not know the dice tray exists — it wants it to exist and goes
looking. 'Looked and could not find' is the per-user-type finding the
instrument exists to produce.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

_ARCHETYPE_DIR = Path(__file__).parent / "archetypes"

Level = Literal["low", "medium", "high"]


class Archetype(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    narrative_vs_mechanical: float = Field(ge=0.0, le=1.0)  # 0 = narrative, 1 = crunch
    verbosity: Level
    decisiveness: Level
    affordance_hunger: Level
    reading_tolerance: Level
    prompt_fragment: str


def load_archetype(archetype_id: str) -> Archetype:
    path = _ARCHETYPE_DIR / f"{archetype_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no archetype {archetype_id!r} at {path}")
    return Archetype.model_validate(yaml.safe_load(path.read_text()))


def load_all_archetypes() -> dict[str, Archetype]:
    return {p.stem: load_archetype(p.stem) for p in sorted(_ARCHETYPE_DIR.glob("*.yaml"))}
```

- [ ] **Step 5: Write `src/understudy/persona/prompts.py`**

```python
"""System-prompt assembly + the mechanical axis maps.

The frame is deliberately GAME-AGNOSTIC: it never teaches the game's rules,
names its controls, or enumerates valid actions. Doing so would delete the
affordance test (the naivety invariant).
"""

from __future__ import annotations

from understudy.persona.model import Archetype

# reading_tolerance → how many transcript messages replay into context each turn
# (also the token-cost knob for local models)
HISTORY_DEPTH: dict[str, int] = {"low": 4, "medium": 8, "high": 16}

# verbosity → hard cap on typed-action length (the "playtest actions stay
# short" rule, enforced mechanically by truncation at the cap)
VERBOSITY_CHAR_CAP: dict[str, int] = {"low": 160, "medium": 300, "high": 450}

# decisiveness → seconds a waiting bot sleeps before re-perceiving
WAIT_POLL_SECONDS: dict[str, float] = {"low": 8.0, "medium": 5.0, "high": 2.0}

_FRAME = """\
You are a person playing an online multiplayer tabletop-style game you have
never seen before. Each turn you are shown what is currently on your screen,
described the way a screen reader would describe it. Decide what you, as a
player, do next.

You respond with exactly one intent:
- act: interact with ONE thing on the screen. Name it the way you would say
  it aloud (its role and its label, e.g. the "Send" button, the text box
  labeled "Action"). To type, include the text. One interaction at a time:
  type into a field, OR click a control — never both at once.
- report_confusion: if you cannot work out what to do, or the screen does
  not make sense to you, say why. This is always allowed and never wrong.
- wait: if you believe it is not your turn, or the game seems busy.

Stay in character as the player described below. Never narrate other
players' actions. Never invent controls you cannot see.
"""

_LEAN = {
    "low": "You lean heavily toward story and prose over rules and numbers.",
    "medium": "You balance story and mechanics evenly.",
    "high": "You lean heavily toward rules, numbers, and how the system works.",
}


def _lean_bucket(x: float) -> str:
    return "low" if x < 0.34 else ("high" if x > 0.66 else "medium")


def build_system_prompt(arch: Archetype) -> str:
    cap = VERBOSITY_CHAR_CAP[arch.verbosity]
    return "\n".join(
        [
            _FRAME,
            "## Who you are as a player",
            arch.prompt_fragment.strip(),
            _LEAN[_lean_bucket(arch.narrative_vs_mechanical)],
            f"Keep anything you type under {cap} characters — short, like a real "
            "player at a table, not an author.",
        ]
    )
```

- [ ] **Step 6: Write `src/understudy/manifest.py`**

```python
"""Run manifest — declares the table. Composition falls out: a seat is just
an independent client; 'human' seats are simply not driven by this process."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from understudy.persona.model import load_all_archetypes

DEFAULT_MODEL = "anthropic/claude-haiku-4-5-20251001"


class ManifestError(Exception):
    pass


class SeatSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archetype: str  # "human" or an archetype id
    model: str = DEFAULT_MODEL


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    genre: str
    world: str
    session_url: str  # explicit, never derived — no silent fallbacks
    seats: list[SeatSpec]
    turns: int = 12
    wall_clock_minutes: float = 30.0
    decide_timeout_s: float = 120.0
    settle_ms: int = 4000
    max_tokens_total: int | None = None
    capture_spans: bool = True
    jaeger_url: str = "http://localhost:16686"

    @field_validator("seats", mode="before")
    @classmethod
    def _coerce_seats(cls, v: object) -> object:
        if isinstance(v, list):
            return [{"archetype": s} if isinstance(s, str) else s for s in v]
        return v


def load_manifest(path: Path) -> RunManifest:
    if not path.exists():
        raise ManifestError(f"manifest not found: {path}")
    try:
        m = RunManifest.model_validate(yaml.safe_load(path.read_text()))
    except (ValidationError, yaml.YAMLError) as exc:
        raise ManifestError(f"invalid manifest {path}: {exc}") from exc
    known = set(load_all_archetypes())
    for seat in m.seats:
        if seat.archetype != "human" and seat.archetype not in known:
            raise ManifestError(
                f"unknown archetype {seat.archetype!r} (known: {sorted(known)})"
            )
    return m
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
uv run pytest tests/test_persona.py tests/test_manifest.py -q
```

Expected: 8 passed.

- [ ] **Step 8: Commit**

```bash
git add src/understudy/persona src/understudy/manifest.py tests/test_persona.py tests/test_manifest.py
git commit -m "feat: playgroup archetypes, game-agnostic prompt frame, run manifest"
```

---

### Task 4: Perception — the faithful a11y snapshot

**Files:**
- Create: `sidequest-understudy/src/understudy/perception/snapshot.py`
- Test: `sidequest-understudy/tests/test_perception.py`

- [ ] **Step 1: Write the failing tests** (pure functions on recorded snapshot strings — no browser)

```python
# tests/test_perception.py
from understudy.perception.snapshot import count_actionable, new_lines

ARIA_FIXTURE = """\
- banner:
  - heading "The Flickering Reach" [level=1]
- main:
  - log: You stand at the gate of the settlement.
  - textbox "Action"
  - button "Send"
  - button "Roll"
- contentinfo:
  - text: turn 3
"""

NO_CONTROLS = """\
- main:
  - heading "Loading" [level=2]
  - text: please wait
"""


def test_count_actionable_finds_controls():
    assert count_actionable(ARIA_FIXTURE) == 3  # textbox + 2 buttons


def test_count_actionable_zero_on_dead_screen():
    assert count_actionable(NO_CONTROLS) == 0


def test_new_lines_returns_only_fresh_content():
    after = ARIA_FIXTURE + '  - log: A guard approaches you.\n'
    delta = new_lines(ARIA_FIXTURE, after)
    assert "A guard approaches you." in delta
    assert "You stand at the gate" not in delta


def test_new_lines_empty_when_nothing_changed():
    assert new_lines(ARIA_FIXTURE, ARIA_FIXTURE) == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_perception.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/understudy/perception/snapshot.py`**

```python
"""Perception: render the page the way a screen reader presents it.

Playwright's aria_snapshot() yields a YAML-ish structured-text tree of roles,
accessible names, and text. We present it FAITHFULLY — including ambiguous or
unlabeled nodes. No post-processing into a clean menu of clickables:
spoon-feeding affordances would delete the affordance test.
"""

from __future__ import annotations

from playwright.async_api import Page

# Roles a user can operate. Used ONLY for the harness-side
# NO_ACTIONABLE_ELEMENTS stuck-signal — never shown to the brain.
ACTIONABLE_ROLES = frozenset(
    {
        "button", "textbox", "searchbox", "link", "combobox", "checkbox",
        "radio", "slider", "spinbutton", "switch", "tab", "menuitem", "option",
    }
)


def _node_role(line: str) -> str | None:
    s = line.strip()
    if not s.startswith("- "):
        return None
    head = s[2:].split(" ", 1)[0].rstrip(":")
    return head or None


def count_actionable(snapshot: str) -> int:
    """Count operable controls in a snapshot (harness-side signal input)."""
    return sum(1 for line in snapshot.splitlines() if _node_role(line) in ACTIONABLE_ROLES)


def new_lines(before: str, after: str) -> str:
    """Lines present in `after` but not `before` — the narration delta."""
    seen = set(before.splitlines())
    fresh = [ln for ln in after.splitlines() if ln.strip() and ln not in seen]
    return "\n".join(fresh)


async def perceive(page: Page) -> str:
    """The ONLY thing the brain ever receives about the game."""
    title = await page.title()
    tree = await page.locator("body").aria_snapshot()
    return f"# Page: {title}\n{tree}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_perception.py -q
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/understudy/perception/snapshot.py tests/test_perception.py
git commit -m "feat: perception — faithful aria-snapshot rendering + pure helpers"
```

---

### Task 5: Brain core — protocol, intent parsing, FakeActionModel

**Files:**
- Create: `sidequest-understudy/src/understudy/brain/core.py`
- Test: `sidequest-understudy/tests/test_brain_core.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_brain_core.py
import pytest

from understudy.brain.core import (
    DecideResult,
    FakeActionModel,
    Message,
    ModelError,
    parse_intent,
)
from understudy.types import Intent, IntentKind


def test_parse_intent_strict_json():
    raw = '{"kind": "act", "target_role": "button", "target_name": "Send"}'
    intent = parse_intent(raw)
    assert intent.kind is IntentKind.ACT


def test_parse_intent_tolerates_code_fence():
    raw = '```json\n{"kind": "wait"}\n```'
    assert parse_intent(raw).kind is IntentKind.WAIT


def test_parse_intent_raises_model_error_on_garbage():
    with pytest.raises(ModelError):
        parse_intent("I attack the goblin!")


def test_parse_intent_raises_model_error_on_bad_shape():
    with pytest.raises(ModelError):
        parse_intent('{"kind": "act"}')  # act without target


async def test_fake_model_plays_script_then_waits():
    script = [Intent(kind=IntentKind.ACT, target_role="button", target_name="Send")]
    fake = FakeActionModel(script)
    first = await fake.decide("sys", [Message(role="user", content="screen")])
    assert isinstance(first, DecideResult)
    assert first.intent.kind is IntentKind.ACT
    assert (first.input_tokens, first.output_tokens) == (0, 0)
    second = await fake.decide("sys", [])
    assert second.intent.kind is IntentKind.WAIT  # script exhausted → wait forever
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_brain_core.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/understudy/brain/core.py`**

```python
"""Brain seam: the ActionModel protocol every backend implements.

Spec note: the protocol returns DecideResult (Intent + token usage) rather
than a bare Intent so the run's token ledger can meter API backends; the
Intent remains the decision payload per the design spec.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import ValidationError

from understudy.types import Intent, IntentKind


class ModelError(Exception):
    """The model produced output that is not a valid Intent. Logged as a
    down-weighted friction signal (model failure, not UI failure)."""


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class DecideResult:
    intent: Intent
    input_tokens: int
    output_tokens: int


class ActionModel(Protocol):
    async def decide(self, system: str, transcript: list[Message]) -> DecideResult: ...


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_intent(raw: str) -> Intent:
    """Strict JSON → Intent. Anything else is a ModelError — never a guess."""
    cleaned = _FENCE.sub("", raw.strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ModelError(f"model output is not JSON: {raw[:200]!r}") from exc
    try:
        return Intent.model_validate(data)
    except ValidationError as exc:
        raise ModelError(f"model JSON is not a valid Intent: {exc}") from exc


class FakeActionModel:
    """Scripted brain for tests and the wiring lane. Zero tokens, zero LLM."""

    def __init__(self, script: list[Intent]):
        self._script = list(script)

    async def decide(self, system: str, transcript: list[Message]) -> DecideResult:
        intent = self._script.pop(0) if self._script else Intent(kind=IntentKind.WAIT)
        return DecideResult(intent=intent, input_tokens=0, output_tokens=0)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_brain_core.py -q
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/understudy/brain/core.py tests/test_brain_core.py
git commit -m "feat: brain core — ActionModel protocol, strict intent parsing, FakeActionModel"
```

---

### Task 6: LLM backends — anthropic, ollama, claude_p + factory

**Files:**
- Create: `sidequest-understudy/src/understudy/brain/llm/anthropic_model.py`
- Create: `sidequest-understudy/src/understudy/brain/llm/ollama_model.py`
- Create: `sidequest-understudy/src/understudy/brain/llm/claude_p_model.py`
- Create: `sidequest-understudy/src/understudy/brain/llm/factory.py`
- Test: `sidequest-understudy/tests/test_backends.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_backends.py
import json

import httpx
import pytest

from understudy.brain.core import Message, ModelError
from understudy.brain.llm.factory import make_model
from understudy.brain.llm.ollama_model import OllamaModel
from understudy.types import IntentKind


def test_factory_dispatches_by_prefix():
    assert type(make_model("ollama/qwen3:8b")).__name__ == "OllamaModel"
    assert type(make_model("claude_p/haiku")).__name__ == "ClaudePModel"
    assert type(make_model("fake")).__name__ == "FakeActionModel"


def test_factory_fails_loud_on_unknown_backend():
    with pytest.raises(ValueError, match="unknown model backend"):
        make_model("bard/gpt-1")


def _ollama_transport(reply: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["format"]["properties"]["kind"]  # Intent schema passed
        return httpx.Response(200, json=reply)

    return httpx.MockTransport(handler)


async def test_ollama_decides_and_meters_tokens():
    reply = {
        "message": {"role": "assistant", "content": '{"kind": "wait"}'},
        "prompt_eval_count": 100,
        "eval_count": 12,
    }
    model = OllamaModel(
        "qwen3:8b", client=httpx.AsyncClient(transport=_ollama_transport(reply))
    )
    result = await model.decide("sys", [Message(role="user", content="screen")])
    assert result.intent.kind is IntentKind.WAIT
    assert (result.input_tokens, result.output_tokens) == (100, 12)


async def test_ollama_garbage_raises_model_error():
    reply = {"message": {"role": "assistant", "content": "lol no"}}
    model = OllamaModel(
        "qwen3:8b", client=httpx.AsyncClient(transport=_ollama_transport(reply))
    )
    with pytest.raises(ModelError):
        await model.decide("sys", [Message(role="user", content="screen")])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_backends.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/understudy/brain/llm/anthropic_model.py`**

```python
"""Anthropic SDK backend. Intent is forced via a tool call so the shape is
validated at the API layer, not parsed out of prose."""

from __future__ import annotations

import anthropic
from pydantic import ValidationError

from understudy.brain.core import DecideResult, Message, ModelError
from understudy.types import Intent

INTENT_TOOL = {
    "name": "submit_intent",
    "description": "Submit what you, the player, do next.",
    "input_schema": Intent.model_json_schema(),
}


class AnthropicModel:
    def __init__(self, model: str, client: anthropic.AsyncAnthropic | None = None):
        self._model = model
        self._client = client or anthropic.AsyncAnthropic()

    async def decide(self, system: str, transcript: list[Message]) -> DecideResult:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in transcript],
            tools=[INTENT_TOOL],
            tool_choice={"type": "tool", "name": "submit_intent"},
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        if block is None:
            raise ModelError("anthropic response contained no tool_use block")
        try:
            intent = Intent.model_validate(block.input)
        except ValidationError as exc:
            raise ModelError(f"tool input is not a valid Intent: {exc}") from exc
        return DecideResult(
            intent=intent,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
```

- [ ] **Step 4: Write `src/understudy/brain/llm/ollama_model.py`**

```python
"""Ollama backend — the zero-cost local lane. Uses /api/chat with a JSON
schema `format` so structured output comes from the runtime, not regex."""

from __future__ import annotations

import httpx

from understudy.brain.core import DecideResult, Message, parse_intent
from understudy.types import Intent


class OllamaModel:
    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        client: httpx.AsyncClient | None = None,
    ):
        self._model = model
        self._host = host.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=300.0)

    async def decide(self, system: str, transcript: list[Message]) -> DecideResult:
        payload = {
            "model": self._model,
            "stream": False,
            "format": Intent.model_json_schema(),
            "messages": [
                {"role": "system", "content": system},
                *({"role": m.role, "content": m.content} for m in transcript),
            ],
        }
        resp = await self._client.post(f"{self._host}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        intent = parse_intent(data["message"]["content"])
        return DecideResult(
            intent=intent,
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
        )
```

- [ ] **Step 5: Write `src/understudy/brain/llm/claude_p_model.py`**

```python
"""`claude -p` subprocess backend. One-shot; no token metering available
(reported as zeros — the ledger guards API spend, and claude -p bills to the
operator's plan, not per-token)."""

from __future__ import annotations

import asyncio
import json

from understudy.brain.core import DecideResult, Message, ModelError, parse_intent


class ClaudePModel:
    def __init__(self, model: str = "haiku"):
        self._model = model

    async def decide(self, system: str, transcript: list[Message]) -> DecideResult:
        convo = "\n\n".join(f"[{m.role}]\n{m.content}" for m in transcript)
        prompt = (
            f"{system}\n\n{convo}\n\n"
            "Reply with ONLY a JSON object for your intent — no prose. Shape: "
            '{"kind": "act"|"report_confusion"|"wait", "target_role": str|null, '
            '"target_name": str|null, "text_input": str|null, "reason": str|null}'
        )
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", "-", "--output-format", "json", "--model", self._model,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(prompt.encode())
        if proc.returncode != 0:
            raise ModelError(f"claude -p exited {proc.returncode}: {stderr.decode()[:300]}")
        try:
            envelope = json.loads(stdout.decode())
        except json.JSONDecodeError as exc:
            raise ModelError(f"claude -p emitted non-JSON envelope: {exc}") from exc
        intent = parse_intent(str(envelope.get("result", "")))
        return DecideResult(intent=intent, input_tokens=0, output_tokens=0)
```

- [ ] **Step 6: Write `src/understudy/brain/llm/factory.py`**

```python
"""Per-seat model factory. Spec form: '<backend>/<model-id>' (e.g.
'anthropic/claude-haiku-4-5-20251001', 'ollama/qwen3:8b', 'claude_p/haiku',
or bare 'fake' for the scripted lane). Unknown backend = loud failure."""

from __future__ import annotations

from understudy.brain.core import ActionModel, FakeActionModel
from understudy.brain.llm.anthropic_model import AnthropicModel
from understudy.brain.llm.claude_p_model import ClaudePModel
from understudy.brain.llm.ollama_model import OllamaModel


def make_model(spec: str) -> ActionModel:
    backend, _, model_id = spec.partition("/")
    match backend:
        case "anthropic":
            return AnthropicModel(model_id)
        case "ollama":
            return OllamaModel(model_id)
        case "claude_p":
            return ClaudePModel(model_id or "haiku")
        case "fake":
            return FakeActionModel([])
        case _:
            raise ValueError(f"unknown model backend: {spec!r}")
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
uv run pytest tests/test_backends.py -q
```

Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add src/understudy/brain/llm tests/test_backends.py
git commit -m "feat: model-agnostic backends — anthropic tool-forced, ollama schema, claude -p"
```

---

### Task 7: Actuation — resolve named targets against the live page

**Files:**
- Create: `sidequest-understudy/src/understudy/actuation/act.py`
- Create: `sidequest-understudy/tests/conftest.py`
- Test: `sidequest-understudy/tests/test_actuation.py`

- [ ] **Step 1: Write the browser fixture in `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
from playwright.async_api import async_playwright


@pytest.fixture
async def page():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        pg = await browser.new_page()
        yield pg
        await browser.close()
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_actuation.py
from understudy.actuation.act import Resolution, perform_act
from understudy.types import Intent, IntentKind

FIXTURE = """
<main>
  <h1>Fixture Table</h1>
  <div id="narration" role="log">You stand at the gate.</div>
  <textarea aria-label="Action"></textarea>
  <button onclick="document.getElementById('narration').append(' You did: ' +
    document.querySelector('textarea').value)">Send</button>
  <button>Send</button>
</main>
"""


async def test_fill_resolves_textbox_by_name(page):
    await page.set_content(FIXTURE)
    intent = Intent(kind=IntentKind.ACT, target_role="textbox", target_name="Action",
                    text_input="I open the gate")
    outcome = await perform_act(page, intent, settle_ms=50)
    assert outcome.resolution is Resolution.RESOLVED
    assert await page.locator("textarea").input_value() == "I open the gate"


async def test_duplicate_buttons_are_ambiguous_but_still_clicked(page):
    await page.set_content(FIXTURE)
    intent = Intent(kind=IntentKind.ACT, target_role="button", target_name="Send")
    outcome = await perform_act(page, intent, settle_ms=50)
    assert outcome.resolution is Resolution.AMBIGUOUS  # two Send buttons — real friction


async def test_missing_target_fails_without_crashing(page):
    await page.set_content(FIXTURE)
    intent = Intent(kind=IntentKind.ACT, target_role="button", target_name="Dice Tray")
    outcome = await perform_act(page, intent, settle_ms=50)
    assert outcome.resolution is Resolution.FAILED
    assert "Dice Tray" in outcome.detail


async def test_invalid_role_is_failed_resolution_not_crash(page):
    await page.set_content(FIXTURE)
    intent = Intent(kind=IntentKind.ACT, target_role="clicky thing", target_name="Send")
    outcome = await perform_act(page, intent, settle_ms=50)
    assert outcome.resolution is Resolution.FAILED
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_actuation.py -q
```

Expected: FAIL — `ModuleNotFoundError: understudy.actuation.act`.

- [ ] **Step 4: Write `src/understudy/actuation/act.py`**

```python
"""Actuation: resolve the bot's NAMED target (role + accessible name, the way
a player refers to it) to a live locator, then do exactly one interaction.

Three outcomes, all meaningful:
- RESOLVED: clean single match — interaction performed.
- AMBIGUOUS: multiple matches — first is used, friction logged. Two controls
  with the same name is itself a legibility finding.
- FAILED: the bot asked for something that is not there. The bot's mental
  model diverged from the page. This is the gold the instrument mines —
  it is NEVER rescued with alias maps or fuzzy heroics (naivety invariant).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from playwright.async_api import Error as PlaywrightError, Page

from understudy.types import Intent


class Resolution(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    FAILED = "failed"


@dataclass(frozen=True)
class ActOutcome:
    resolution: Resolution
    detail: str = ""


async def perform_act(page: Page, intent: Intent, settle_ms: int) -> ActOutcome:
    assert intent.target_role and intent.target_name  # guaranteed by Intent validator
    try:
        loc = page.get_by_role(intent.target_role, name=intent.target_name, exact=False)
        count = await loc.count()
    except PlaywrightError as exc:
        # e.g. the bot invented a non-ARIA role — its mental model diverged
        return ActOutcome(Resolution.FAILED, f"unresolvable target: {exc}")
    if count == 0:
        return ActOutcome(
            Resolution.FAILED,
            f'nothing on the page matches {intent.target_role} "{intent.target_name}"',
        )
    resolution = Resolution.RESOLVED if count == 1 else Resolution.AMBIGUOUS
    target = loc.first
    try:
        if intent.text_input is not None:
            await target.fill(intent.text_input)
        else:
            await target.click()
    except PlaywrightError as exc:
        # found but not operable (disabled, covered, detached mid-action)
        return ActOutcome(Resolution.FAILED, f"target found but not operable: {exc}")
    await page.wait_for_timeout(settle_ms)
    detail = "" if resolution is Resolution.RESOLVED else f"{count} elements matched"
    return ActOutcome(resolution, detail)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_actuation.py -q
```

Expected: 4 passed (real headless chromium, no LLM).

- [ ] **Step 6: Commit**

```bash
git add src/understudy/actuation/act.py tests/conftest.py tests/test_actuation.py
git commit -m "feat: actuation — role+name target resolution, three-outcome act"
```

---

### Task 8: Findings — stuck detection helpers + the reconciler

**Files:**
- Create: `sidequest-understudy/src/understudy/findings/detect.py`
- Create: `sidequest-understudy/src/understudy/findings/reconcile.py`
- Test: `sidequest-understudy/tests/test_findings.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_findings.py
from understudy.findings.detect import repeated_action
from understudy.findings.reconcile import reconcile
from understudy.types import (
    FrictionSignal, Grade, Intent, IntentKind, SignalKind, TranscriptRow,
)


def _act(name="Send"):
    return Intent(kind=IntentKind.ACT, target_role="button", target_name=name)


def _row(seat, turn, intent=None, signals=(), snapshot="- main:"):
    return TranscriptRow(seat=seat, turn=turn, snapshot=snapshot, intent=intent,
                         resolution="n/a", narration_delta="", signals=list(signals))


def _sig(kind, seat, turn):
    return FrictionSignal(kind=kind, seat=seat, turn=turn, detail="x")


def test_repeated_action_detects_three_identical_acts():
    assert repeated_action([_act(), _act(), _act()], n=3)
    assert not repeated_action([_act(), _act("Roll"), _act()], n=3)
    assert not repeated_action([_act(), _act()], n=3)


def test_confirmed_when_confusion_meets_objective_signal_in_window():
    confusion = Intent(kind=IntentKind.REPORT_CONFUSION, reason="cannot find submit")
    rows = [
        _row(1, 4, _act(), [_sig(SignalKind.RESOLUTION_FAILED, 1, 4)]),
        _row(1, 5, confusion),
    ]
    findings = reconcile(rows, {1: "hesitant"})
    grades = {f.grade for f in findings}
    assert Grade.CONFIRMED in grades


def test_claimed_when_confusion_has_clean_behavior():
    confusion = Intent(kind=IntentKind.REPORT_CONFUSION, reason="this is weird")
    findings = reconcile([_row(1, 2, confusion)], {1: "narrative_first"})
    assert [f.grade for f in findings] == [Grade.CLAIMED]
    assert findings[0].confusion_reason == "this is weird"


def test_behavioral_when_friction_without_complaint():
    rows = [_row(2, 7, _act(), [_sig(SignalKind.REPEATED_ACTION, 2, 7)])]
    findings = reconcile(rows, {2: "mechanics_first"})
    assert [f.grade for f in findings] == [Grade.BEHAVIORAL]


def test_model_error_is_downweighted_never_confirms():
    confusion = Intent(kind=IntentKind.REPORT_CONFUSION, reason="huh")
    rows = [
        _row(3, 1, None, [_sig(SignalKind.MODEL_ERROR, 3, 1)]),
        _row(3, 2, confusion),
    ]
    findings = reconcile(rows, {3: "hesitant"})
    assert all(f.grade is not Grade.CONFIRMED for f in findings)


def test_signals_from_other_seats_never_cross():
    confusion = Intent(kind=IntentKind.REPORT_CONFUSION, reason="lost")
    rows = [
        _row(1, 3, _act(), [_sig(SignalKind.RESOLUTION_FAILED, 1, 3)]),
        _row(2, 3, confusion),
    ]
    findings = reconcile(rows, {1: "hesitant", 2: "narrative_first"})
    claimed = [f for f in findings if f.seat == 2]
    assert [f.grade for f in claimed] == [Grade.CLAIMED]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_findings.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/understudy/findings/detect.py`**

```python
"""Behavioral stuck-detection helpers — zero LLM judgment."""

from __future__ import annotations

from understudy.types import Intent, IntentKind


def repeated_action(intents: list[Intent | None], n: int = 3) -> bool:
    """True when the last `n` ACT intents are identical (target + text)."""
    acts = [i for i in intents if i is not None and i.kind is IntentKind.ACT]
    if len(acts) < n:
        return False
    tail = acts[-n:]
    first = (tail[0].target_role, tail[0].target_name, tail[0].text_input)
    return all((a.target_role, a.target_name, a.text_input) == first for a in tail)
```

- [ ] **Step 4: Write `src/understudy/findings/reconcile.py`**

```python
"""Reconciler: join the subjective stream (report_confusion intents) against
the objective stream (FrictionSignals) by seat + turn-window and grade:

CONFIRMED  — both agree (complaint + hard signal within ±1 turn, same seat)
BEHAVIORAL — objective only: the bot muddled through without complaining
CLAIMED    — subjective only: complaint with clean behavior (kept, down-ranked)

MODEL_ERROR signals are down-weighted: they are model failures, not UI
failures, and never promote a complaint to CONFIRMED.
"""

from __future__ import annotations

from understudy.types import (
    Finding, FrictionSignal, Grade, IntentKind, SignalKind, TranscriptRow,
)

_DOWNWEIGHTED = {SignalKind.MODEL_ERROR}
_WINDOW = 1  # turns either side of a complaint


def _hard_signals(rows: list[TranscriptRow]) -> list[FrictionSignal]:
    return [s for r in rows for s in r.signals if s.kind not in _DOWNWEIGHTED]


def reconcile(rows: list[TranscriptRow], archetype_by_seat: dict[int, str]) -> list[Finding]:
    findings: list[Finding] = []
    seats = sorted({r.seat for r in rows})
    for seat in seats:
        seat_rows = sorted((r for r in rows if r.seat == seat), key=lambda r: r.turn)
        hard = _hard_signals(seat_rows)
        archetype = archetype_by_seat.get(seat, "unknown")

        # Subjective pass: every complaint becomes CONFIRMED or CLAIMED.
        complaint_windows: set[int] = set()
        for row in seat_rows:
            if row.intent is None or row.intent.kind is not IntentKind.REPORT_CONFUSION:
                continue
            window = [s for s in hard if abs(s.turn - row.turn) <= _WINDOW]
            grade = Grade.CONFIRMED if window else Grade.CLAIMED
            complaint_windows.update(
                t for t in range(row.turn - _WINDOW, row.turn + _WINDOW + 1)
            )
            findings.append(
                Finding(
                    grade=grade,
                    seat=seat,
                    archetype=archetype,
                    turn=row.turn,
                    confusion_reason=row.intent.reason,
                    signals=window,
                    snapshot_excerpt=row.snapshot[:800],
                )
            )

        # Objective pass: hard friction with no nearby complaint → BEHAVIORAL.
        for row in seat_rows:
            row_hard = [s for s in row.signals if s.kind not in _DOWNWEIGHTED]
            if row_hard and row.turn not in complaint_windows:
                findings.append(
                    Finding(
                        grade=Grade.BEHAVIORAL,
                        seat=seat,
                        archetype=archetype,
                        turn=row.turn,
                        confusion_reason=None,
                        signals=row_hard,
                        snapshot_excerpt=row.snapshot[:800],
                    )
                )
    return findings
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_findings.py -q
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/understudy/findings tests/test_findings.py
git commit -m "feat: findings — stuck detection + CONFIRMED/BEHAVIORAL/CLAIMED reconciler"
```

---

### Task 9: Report writer + Jaeger span capture

**Files:**
- Create: `sidequest-understudy/src/understudy/report/spans.py`
- Create: `sidequest-understudy/src/understudy/report/write.py`
- Test: `sidequest-understudy/tests/test_report.py`
- Reference: `scripts/playtest.py:127-300` in the **orchestrator repo** (`/Users/slabgorb/Projects/oq-2/scripts/playtest.py`) — the Jaeger pull is a faithful port of that code; read it before writing `spans.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_report.py
import json

import pytest

from understudy.manifest import RunManifest, SeatSpec
from understudy.report.spans import (
    SpanCaptureEmpty, flatten_jaeger_tags, traces_to_jsonl_records, write_span_jsonl,
)
from understudy.report.write import write_report
from understudy.types import (
    Finding, FrictionSignal, Grade, Intent, IntentKind, SignalKind, TranscriptRow,
)

JAEGER_PAYLOAD = {
    "data": [
        {
            "spans": [
                {
                    "operationName": "narration.turn",
                    "spanID": "abc", "traceID": "t1",
                    "references": [{"refType": "CHILD_OF", "spanID": "root"}],
                    "startTime": 1000, "duration": 50,
                    "tags": [{"key": "narration.turn.model_chosen", "value": "haiku"}],
                }
            ]
        }
    ]
}


def test_flatten_tags_keeps_native_values():
    flat = flatten_jaeger_tags([{"key": "k", "value": 7}, {"key": "s", "value": "x"}])
    assert flat == {"k": 7, "s": "x"}


def test_traces_flatten_to_records_with_parent():
    recs = traces_to_jsonl_records(JAEGER_PAYLOAD)
    assert recs[0]["name"] == "narration.turn"
    assert recs[0]["parent_span_id"] == "root"


def test_empty_span_write_refuses(tmp_path):
    with pytest.raises(SpanCaptureEmpty):
        write_span_jsonl([], tmp_path / "spans.jsonl")


def _manifest():
    return RunManifest(
        name="t", genre="g", world="w", session_url="http://x/p",
        seats=[SeatSpec(archetype="hesitant")], turns=2, capture_spans=False,
    )


def test_write_report_produces_all_artifacts(tmp_path):
    rows = [
        TranscriptRow(
            seat=1, turn=1, snapshot="- main:", resolution="resolved",
            intent=Intent(kind=IntentKind.ACT, target_role="button", target_name="Send"),
            narration_delta="a guard approaches",
            signals=[],
        )
    ]
    findings = [
        Finding(grade=Grade.CLAIMED, seat=1, archetype="hesitant", turn=1,
                confusion_reason="lost", signals=[], snapshot_excerpt="- main:")
    ]
    out = write_report(tmp_path, _manifest(), rows, findings, spans=None, spans_error=None)
    assert (out / "report.md").exists()
    assert (out / "findings.json").exists()
    assert (out / "transcript" / "seat-1.jsonl").exists()
    loaded = json.loads((out / "findings.json").read_text())
    assert loaded[0]["grade"] == "claimed"
    md = (out / "report.md").read_text()
    assert "claimed" in md.lower() and "hesitant" in md


def test_spans_error_is_loud_in_report(tmp_path):
    out = write_report(tmp_path, _manifest(), [], [], spans=None,
                       spans_error="Jaeger unreachable at http://localhost:16686")
    md = (out / "report.md").read_text()
    assert "SPANS MISSING" in md
    assert not (out / "spans.jsonl").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_report.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/understudy/report/spans.py`** — faithful port of `scripts/playtest.py:141-300` (orchestrator repo). Port these symbols verbatim-with-imports-adjusted: `JAEGER_SERVICE = "sidequest-server"`, `NARRATION_TURN_SPAN = "narration.turn"`, `SpanCaptureEmpty`, `flatten_jaeger_tags`, `_parent_span_id`, `jaeger_span_to_record`, `traces_to_jsonl_records`, `write_span_jsonl`, `_query_jaeger_traces`, and `capture_run_spans` (the poll-until-settled wrapper — copy its `settle_attempts=8` / `settle_interval=1.5` defaults and its narration.turn presence check). Read the source file first; do not paraphrase it from memory. Keep the module docstring noting the provenance:

```python
"""Jaeger span capture — port of scripts/playtest.py's Phase-E capture
(orchestrator repo, lines 127-300). The server's narration.turn spans are the
engine-side lie detector: bot said X, harness saw Y, spans say Z."""
```

- [ ] **Step 4: Write `src/understudy/report/write.py`**

```python
"""Report artifact — one self-contained directory per run.

reports/<date>-<name>-rN/
├── report.md          human-readable summary + graded findings
├── findings.json      machine-readable (the deferred ping-pong seam reads this)
├── transcript/        per-seat per-turn JSONL
└── spans.jsonl        server-side narration.turn OTEL spans (when captured)
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from understudy.manifest import RunManifest
from understudy.report.spans import write_span_jsonl
from understudy.types import Finding, Grade, TranscriptRow


def _next_run_dir(root: Path, name: str) -> Path:
    today = datetime.date.today().isoformat()
    n = 1
    while (root / f"{today}-{name}-r{n}").exists():
        n += 1
    out = root / f"{today}-{name}-r{n}"
    out.mkdir(parents=True)
    return out


def _findings_table(findings: list[Finding]) -> str:
    if not findings:
        return "_No findings — clean run._\n"
    lines = ["| Grade | Seat | Archetype | Turn | Summary |", "|---|---|---|---|---|"]
    order = {Grade.CONFIRMED: 0, Grade.BEHAVIORAL: 1, Grade.CLAIMED: 2}
    for f in sorted(findings, key=lambda f: (order[f.grade], f.seat, f.turn)):
        summary = f.confusion_reason or "; ".join(s.kind.value for s in f.signals)
        lines.append(
            f"| {f.grade.value} | {f.seat} | {f.archetype} | {f.turn} | {summary} |"
        )
    return "\n".join(lines) + "\n"


def _seat_stats(rows: list[TranscriptRow]) -> str:
    lines = ["| Seat | Turns | Acts | Waits | Confusions | Failed resolves |", "|---|---|---|---|---|---|"]
    for seat in sorted({r.seat for r in rows}):
        sr = [r for r in rows if r.seat == seat]
        acts = sum(1 for r in sr if r.intent and r.intent.kind.value == "act")
        waits = sum(1 for r in sr if r.intent and r.intent.kind.value == "wait")
        conf = sum(1 for r in sr if r.intent and r.intent.kind.value == "report_confusion")
        failed = sum(1 for r in sr if r.resolution == "failed")
        lines.append(f"| {seat} | {len(sr)} | {acts} | {waits} | {conf} | {failed} |")
    return "\n".join(lines) + "\n"


def write_report(
    out_root: Path,
    manifest: RunManifest,
    rows: list[TranscriptRow],
    findings: list[Finding],
    spans: list[dict] | None,
    spans_error: str | None,
) -> Path:
    out = _next_run_dir(out_root, manifest.name)

    (out / "findings.json").write_text(
        json.dumps([f.model_dump(mode="json") for f in findings], indent=2) + "\n"
    )

    tdir = out / "transcript"
    tdir.mkdir()
    for seat in sorted({r.seat for r in rows}):
        seat_rows = [r for r in rows if r.seat == seat]
        (tdir / f"seat-{seat}.jsonl").write_text(
            "\n".join(r.model_dump_json() for r in seat_rows) + "\n"
        )

    spans_note = ""
    if spans:
        n = write_span_jsonl(spans, out / "spans.jsonl")
        spans_note = f"{n} server spans captured (spans.jsonl)."
    elif spans_error:
        spans_note = f"**SPANS MISSING** — {spans_error}"
    elif manifest.capture_spans:
        spans_note = "**SPANS MISSING** — zero narration.turn spans found for the run window."
    else:
        spans_note = "span capture disabled for this run (capture_spans: false)."

    counts = {g: sum(1 for f in findings if f.grade is g) for g in Grade}
    (out / "report.md").write_text(
        f"# Understudy run — {manifest.name}\n\n"
        f"- **Genre/world:** {manifest.genre} / {manifest.world}\n"
        f"- **Session:** {manifest.session_url}\n"
        f"- **Seats:** {', '.join(s.archetype for s in manifest.seats)}\n"
        f"- **Findings:** {counts[Grade.CONFIRMED]} confirmed, "
        f"{counts[Grade.BEHAVIORAL]} behavioral, {counts[Grade.CLAIMED]} claimed\n"
        f"- **OTEL:** {spans_note}\n\n"
        f"## Findings\n\n{_findings_table(findings)}\n"
        f"## Per-seat outcomes\n\n{_seat_stats(rows)}"
    )
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_report.py -q
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/understudy/report tests/test_report.py
git commit -m "feat: report artifact + Jaeger narration.turn span capture (playtest.py port)"
```

---

### Task 10: Orchestration — the seat loop and the table runner

**Files:**
- Create: `sidequest-understudy/src/understudy/orchestrate/seat.py`
- Create: `sidequest-understudy/src/understudy/orchestrate/run.py`
- Test: `sidequest-understudy/tests/test_seat_loop.py`

- [ ] **Step 1: Write the failing tests** (FakeActionModel + real browser on inline fixture content)

```python
# tests/test_seat_loop.py
from understudy.brain.core import FakeActionModel
from understudy.orchestrate.seat import SeatRunner, TokenLedger
from understudy.persona.model import load_archetype
from understudy.types import Intent, IntentKind, SignalKind

FIXTURE = """
<main>
  <div role="log">You stand at the gate.</div>
  <textarea aria-label="Action"></textarea>
  <button onclick="document.querySelector('[role=log]').append(' Done.')">Send</button>
</main>
"""


def _ledger():
    return TokenLedger(ceiling=None)


async def test_seat_runs_script_and_records_transcript(page):
    await page.set_content(FIXTURE)
    script = [
        Intent(kind=IntentKind.ACT, target_role="textbox", target_name="Action",
               text_input="I open the gate"),
        Intent(kind=IntentKind.ACT, target_role="button", target_name="Send"),
        Intent(kind=IntentKind.REPORT_CONFUSION, reason="cannot tell whose turn it is"),
    ]
    runner = SeatRunner(
        seat=1, archetype=load_archetype("narrative_first"),
        model=FakeActionModel(script), page=page,
        turns=3, decide_timeout_s=10.0, settle_ms=50, ledger=_ledger(),
        deadline=None,
    )
    rows = await runner.run()
    assert len(rows) == 3
    assert rows[0].resolution == "resolved"
    assert rows[1].resolution == "resolved"
    assert "Done." in rows[1].narration_delta
    assert rows[2].intent.kind is IntentKind.REPORT_CONFUSION


async def test_failed_resolution_emits_signal(page):
    await page.set_content(FIXTURE)
    script = [Intent(kind=IntentKind.ACT, target_role="button", target_name="Dice Tray")]
    runner = SeatRunner(
        seat=1, archetype=load_archetype("mechanics_first"),
        model=FakeActionModel(script), page=page,
        turns=1, decide_timeout_s=10.0, settle_ms=50, ledger=_ledger(),
        deadline=None,
    )
    rows = await runner.run()
    assert rows[0].resolution == "failed"
    assert any(s.kind is SignalKind.RESOLUTION_FAILED for s in rows[0].signals)


async def test_token_ledger_breach_stops_gracefully(page):
    await page.set_content(FIXTURE)

    class CostlyFake(FakeActionModel):
        async def decide(self, system, transcript):
            result = await super().decide(system, transcript)
            return type(result)(intent=result.intent, input_tokens=600, output_tokens=0)

    runner = SeatRunner(
        seat=1, archetype=load_archetype("hesitant"),
        model=CostlyFake([Intent(kind=IntentKind.WAIT)] * 10), page=page,
        turns=10, decide_timeout_s=10.0, settle_ms=10,
        ledger=TokenLedger(ceiling=1000), deadline=None,
    )
    rows = await runner.run()
    assert len(rows) < 10  # stopped at the ceiling, partial transcript kept
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_seat_loop.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/understudy/orchestrate/seat.py`**

```python
"""The per-seat perceive→decide→act→observe loop.

A turn = ONE interaction cycle (type OR click OR wait OR complain), the way a
screen-reader user operates. Guards (ADR-134's lesson, applied client-side):
turn cap, token ledger, per-decide timeout, wall-clock deadline. Every guard
ends in a graceful partial transcript, never a hung process.
"""

from __future__ import annotations

import asyncio
import time

from playwright.async_api import Page

from understudy.actuation.act import Resolution, perform_act
from understudy.brain.core import ActionModel, Message, ModelError
from understudy.findings.detect import repeated_action
from understudy.perception.snapshot import count_actionable, new_lines, perceive
from understudy.persona.model import Archetype
from understudy.persona.prompts import (
    HISTORY_DEPTH, VERBOSITY_CHAR_CAP, WAIT_POLL_SECONDS, build_system_prompt,
)
from understudy.types import FrictionSignal, Intent, IntentKind, SignalKind, TranscriptRow


class TokenLedger:
    """Shared across all seats in a run — the pool is per-run, not per-seat."""

    def __init__(self, ceiling: int | None):
        self.total = 0
        self.ceiling = ceiling

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.total += input_tokens + output_tokens

    @property
    def breached(self) -> bool:
        return self.ceiling is not None and self.total >= self.ceiling


class SeatRunner:
    def __init__(
        self,
        *,
        seat: int,
        archetype: Archetype,
        model: ActionModel,
        page: Page,
        turns: int,
        decide_timeout_s: float,
        settle_ms: int,
        ledger: TokenLedger,
        deadline: float | None,  # time.monotonic() deadline, None = no wall clock
    ):
        self.seat = seat
        self.archetype = archetype
        self.model = model
        self.page = page
        self.turns = turns
        self.decide_timeout_s = decide_timeout_s
        self.settle_ms = settle_ms
        self.ledger = ledger
        self.deadline = deadline
        self._system = build_system_prompt(archetype)
        self._history: list[Message] = []
        self._intents: list[Intent | None] = []
        self._console_errors: list[str] = []
        page.on("console", self._on_console)
        page.on("pageerror", lambda err: self._console_errors.append(str(err)))

    def _on_console(self, msg) -> None:
        if msg.type == "error":
            self._console_errors.append(msg.text)

    def _drain_console(self, turn: int) -> list[FrictionSignal]:
        sigs = [
            FrictionSignal(kind=SignalKind.CONSOLE_ERROR, seat=self.seat, turn=turn,
                           detail=text[:300])
            for text in self._console_errors
        ]
        self._console_errors.clear()
        return sigs

    async def run(self) -> list[TranscriptRow]:
        rows: list[TranscriptRow] = []
        depth = HISTORY_DEPTH[self.archetype.reading_tolerance]
        cap = VERBOSITY_CHAR_CAP[self.archetype.verbosity]
        wait_poll = WAIT_POLL_SECONDS[self.archetype.decisiveness]

        for turn in range(1, self.turns + 1):
            if self.deadline is not None and time.monotonic() > self.deadline:
                break
            if self.ledger.breached:
                break

            snapshot = await perceive(self.page)
            signals: list[FrictionSignal] = self._drain_console(turn)
            if count_actionable(snapshot) == 0:
                signals.append(FrictionSignal(
                    kind=SignalKind.NO_ACTIONABLE_ELEMENTS, seat=self.seat, turn=turn,
                    detail="no operable controls exposed to a semantic reader"))

            self._history.append(Message(role="user", content=snapshot))
            context = self._history[-depth:]

            intent: Intent | None = None
            try:
                result = await asyncio.wait_for(
                    self.model.decide(self._system, context),
                    timeout=self.decide_timeout_s,
                )
                self.ledger.add(result.input_tokens, result.output_tokens)
                intent = result.intent
            except TimeoutError:
                signals.append(FrictionSignal(
                    kind=SignalKind.DECIDE_TIMEOUT, seat=self.seat, turn=turn,
                    detail=f"model did not decide within {self.decide_timeout_s}s"))
            except ModelError as exc:
                signals.append(FrictionSignal(
                    kind=SignalKind.MODEL_ERROR, seat=self.seat, turn=turn,
                    detail=str(exc)[:300]))

            self._intents.append(intent)
            if repeated_action(self._intents):
                signals.append(FrictionSignal(
                    kind=SignalKind.REPEATED_ACTION, seat=self.seat, turn=turn,
                    detail="same act three times running"))

            resolution = "n/a"
            narration_delta = ""
            if intent is not None and intent.kind is IntentKind.ACT:
                if intent.text_input and len(intent.text_input) > cap:
                    intent = intent.model_copy(
                        update={"text_input": intent.text_input[:cap]})
                outcome = await perform_act(self.page, intent, self.settle_ms)
                resolution = outcome.resolution.value
                if outcome.resolution is Resolution.FAILED:
                    signals.append(FrictionSignal(
                        kind=SignalKind.RESOLUTION_FAILED, seat=self.seat, turn=turn,
                        detail=outcome.detail))
                elif outcome.resolution is Resolution.AMBIGUOUS:
                    signals.append(FrictionSignal(
                        kind=SignalKind.RESOLUTION_AMBIGUOUS, seat=self.seat, turn=turn,
                        detail=outcome.detail))
                after = await perceive(self.page)
                narration_delta = new_lines(snapshot, after)
            elif intent is not None and intent.kind is IntentKind.WAIT:
                await asyncio.sleep(wait_poll)

            if intent is not None:
                self._history.append(
                    Message(role="assistant", content=intent.model_dump_json()))

            rows.append(TranscriptRow(
                seat=self.seat, turn=turn, snapshot=snapshot, intent=intent,
                resolution=resolution, narration_delta=narration_delta,
                signals=signals))
        return rows
```

- [ ] **Step 4: Write `src/understudy/orchestrate/run.py`**

```python
"""Table runner: N isolated browser contexts, one per bot seat. Human seats
are simply not driven — the human joins the same session_url in their own
browser. Composition falls out; nothing here knows about '2 and 2'."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

from understudy.brain.llm.factory import make_model
from understudy.findings.reconcile import reconcile
from understudy.manifest import RunManifest
from understudy.orchestrate.seat import SeatRunner, TokenLedger
from understudy.persona.model import load_archetype
from understudy.report.spans import SpanCaptureEmpty, capture_run_spans
from understudy.report.write import write_report


async def run_table(
    manifest: RunManifest,
    *,
    headed: bool = False,
    out_root: Path = Path("reports"),
    model_factory=make_model,  # injection seam for the wiring test
) -> int:
    """Returns a process exit code: 0 ok, 1 span-capture failure (run report
    still written — the artifact is partial, and that is said loudly)."""
    bot_seats = [
        (idx, spec) for idx, spec in enumerate(manifest.seats, start=1)
        if spec.archetype != "human"
    ]
    for idx, spec in enumerate(manifest.seats, start=1):
        if spec.archetype == "human":
            print(f"seat {idx}: human — join {manifest.session_url} yourself")

    ledger = TokenLedger(ceiling=manifest.max_tokens_total)
    deadline = time.monotonic() + manifest.wall_clock_minutes * 60.0
    run_start_us = int(time.time() * 1_000_000)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not headed)
        runners: list[SeatRunner] = []
        for idx, spec in bot_seats:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(manifest.session_url)
            runners.append(SeatRunner(
                seat=idx,
                archetype=load_archetype(spec.archetype),
                model=model_factory(spec.model),
                page=page,
                turns=manifest.turns,
                decide_timeout_s=manifest.decide_timeout_s,
                settle_ms=manifest.settle_ms,
                ledger=ledger,
                deadline=deadline,
            ))
        all_rows_nested = await asyncio.gather(*(r.run() for r in runners))
        await browser.close()

    run_end_us = int(time.time() * 1_000_000)
    rows = [row for seat_rows in all_rows_nested for row in seat_rows]
    archetype_by_seat = {idx: spec.archetype for idx, spec in bot_seats}
    findings = reconcile(rows, archetype_by_seat)

    spans: list[dict] | None = None
    spans_error: str | None = None
    if manifest.capture_spans:
        try:
            spans = await capture_run_spans(
                manifest.jaeger_url, run_start_us=run_start_us, run_end_us=run_end_us)
        except (httpx.HTTPError, SpanCaptureEmpty) as exc:
            spans_error = str(exc)

    out = write_report(out_root, manifest, rows, findings, spans, spans_error)
    print(f"report: {out}")
    if manifest.capture_spans and not spans:
        print("SPAN CAPTURE FAILED — run was not traced or Jaeger unreachable")
        return 1
    return 0
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_seat_loop.py -q
```

Expected: 3 passed.

- [ ] **Step 6: Run the whole suite**

```bash
uv run pytest -q
```

Expected: all green (≈33 tests).

- [ ] **Step 7: Commit**

```bash
git add src/understudy/orchestrate tests/test_seat_loop.py
git commit -m "feat: orchestration — guarded seat loop + N-context table runner"
```

---

### Task 11: CLI + example manifest

**Files:**
- Create: `sidequest-understudy/src/understudy/cli.py`
- Create: `sidequest-understudy/runs/four_seat_demo.yaml`
- Test: `sidequest-understudy/tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py
from typer.testing import CliRunner

from understudy.cli import app

runner = CliRunner()


def test_invalid_manifest_exits_2(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: x\n")  # missing required fields
    result = runner.invoke(app, ["run", str(bad)])
    assert result.exit_code == 2
    assert "invalid manifest" in result.output


def test_missing_manifest_exits_2(tmp_path):
    result = runner.invoke(app, ["run", str(tmp_path / "ghost.yaml")])
    assert result.exit_code == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_cli.py -q
```

Expected: FAIL — `ModuleNotFoundError: understudy.cli`.

- [ ] **Step 3: Write `src/understudy/cli.py`**

```python
"""Understudy CLI.

Exit codes (mirrors scripts/playtest.py conventions):
  0 — run completed, report written, spans captured (or capture disabled)
  1 — run completed but span capture failed (partial artifact, said loudly)
  2 — manifest invalid or missing
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from understudy.manifest import ManifestError, load_manifest
from understudy.orchestrate.run import run_table

app = typer.Typer(add_completion=False)


@app.command()
def run(
    manifest: Path,
    headed: bool = typer.Option(False, "--headed", help="show the browser windows"),
    out: Path = typer.Option(Path("reports"), "--out", help="report output root"),
) -> None:
    """Run a table from a manifest: N naive bot seats join the session and play."""
    try:
        m = load_manifest(manifest)
    except ManifestError as exc:
        typer.echo(f"invalid manifest: {exc}")
        raise typer.Exit(2)
    code = asyncio.run(run_table(m, headed=headed, out_root=out))
    raise typer.Exit(code)
```

- [ ] **Step 4: Write `runs/four_seat_demo.yaml`**

```yaml
# Fully-autonomous four-seat table. To drive a seat yourself, change one
# entry to `human` and join session_url in your own browser.
name: four_seat_demo
genre: mutant_wasteland
world: flickering_reach
session_url: http://localhost:5173   # point at the lobby; bots navigate naively
seats:
  - engaged_generalist
  - mechanics_first
  - narrative_first
  - hesitant
turns: 12
wall_clock_minutes: 45
max_tokens_total: 400000      # graceful stop + partial report at the ceiling
capture_spans: true
jaeger_url: http://localhost:16686
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_cli.py -q
```

Expected: 2 passed.

- [ ] **Step 6: Smoke the entry point**

```bash
uv run understudy run --help
```

Expected: usage text with `--headed` and `--out` options.

- [ ] **Step 7: Commit**

```bash
git add src/understudy/cli.py runs/four_seat_demo.yaml tests/test_cli.py
git commit -m "feat: understudy CLI + example four-seat manifest"
```

---

### Task 12: Wiring test — full loop, real browser, zero LLM

**Files:**
- Create: `sidequest-understudy/tests/wiring/fixture_table.html`
- Test: `sidequest-understudy/tests/wiring/test_full_loop.py`

This is the house-rule wiring test: it proves perceive→decide→act→observe→reconcile→report is connected end-to-end through `run_table` (the production entry path), using a scripted brain and a static fixture page — no LLM, no SideQuest stack, no tokens.

- [ ] **Step 1: Write `tests/wiring/fixture_table.html`**

```html
<!DOCTYPE html>
<html>
<head><title>Fixture Table</title></head>
<body>
<main>
  <h1>Fixture Table</h1>
  <div id="narration" role="log">You stand at the gate of the settlement.</div>
  <label for="action">Action</label>
  <textarea id="action"></textarea>
  <button id="send">Send</button>
</main>
<script>
  document.getElementById("send").addEventListener("click", () => {
    const box = document.getElementById("action");
    document.getElementById("narration").append(" You did: " + box.value + ".");
    box.value = "";
  });
</script>
</body>
</html>
```

- [ ] **Step 2: Write the failing wiring test**

```python
# tests/wiring/test_full_loop.py
import json
import shutil
from pathlib import Path

from understudy.brain.core import FakeActionModel
from understudy.manifest import RunManifest, SeatSpec
from understudy.orchestrate.run import run_table
from understudy.types import Grade, Intent, IntentKind

FIXTURE = Path(__file__).parent / "fixture_table.html"


async def test_full_loop_produces_graded_report(tmp_path):
    page_copy = tmp_path / "table.html"
    shutil.copy(FIXTURE, page_copy)

    script = [
        Intent(kind=IntentKind.ACT, target_role="textbox", target_name="Action",
               text_input="I open the gate"),
        Intent(kind=IntentKind.ACT, target_role="button", target_name="Send"),
        Intent(kind=IntentKind.ACT, target_role="button", target_name="Dice Tray"),
        Intent(kind=IntentKind.REPORT_CONFUSION,
               reason="I expected a way to roll dice and cannot find one"),
    ]

    manifest = RunManifest(
        name="wiring", genre="fixture", world="fixture",
        session_url=page_copy.as_uri(),
        seats=[SeatSpec(archetype="mechanics_first", model="fake")],
        turns=4, settle_ms=50, capture_spans=False,
    )

    code = await run_table(
        manifest, out_root=tmp_path / "reports",
        model_factory=lambda spec: FakeActionModel(list(script)),
    )
    assert code == 0

    run_dirs = list((tmp_path / "reports").iterdir())
    assert len(run_dirs) == 1
    out = run_dirs[0]

    transcript = [
        json.loads(line)
        for line in (out / "transcript" / "seat-1.jsonl").read_text().splitlines()
    ]
    assert len(transcript) == 4
    assert transcript[0]["resolution"] == "resolved"   # typed into Action
    assert transcript[1]["resolution"] == "resolved"   # clicked Send
    assert "I open the gate" in transcript[1]["narration_delta"]
    assert transcript[2]["resolution"] == "failed"     # Dice Tray isn't there

    findings = json.loads((out / "findings.json").read_text())
    grades = {f["grade"] for f in findings}
    # confusion at turn 4 sits within ±1 of the failed resolve at turn 3 → CONFIRMED
    assert Grade.CONFIRMED.value in grades

    md = (out / "report.md").read_text()
    assert "mechanics_first" in md and "confirmed" in md.lower()
```

- [ ] **Step 3: Run the wiring test to verify it fails or passes**

```bash
uv run pytest tests/wiring/test_full_loop.py -q
```

Expected: PASS if Tasks 2-11 are correct — if it fails, the failure is a real wiring gap between modules; fix the integration (not the test) until green.

- [ ] **Step 4: Run the whole suite**

```bash
uv run pytest -q
```

Expected: all green.

- [ ] **Step 5: Lint**

```bash
uv run ruff check . && uv run ruff format --check .
```

Expected: clean (run `uv run ruff format .` first if needed).

- [ ] **Step 6: Commit**

```bash
git add tests/wiring
git commit -m "test: wiring test — full perceive→decide→act→report loop, no LLM"
```

---

### Task 13: Publish the repo + orchestrator wiring

**Files:**
- Create: `sidequest-understudy/README.md`
- Modify: `repos.yaml` (orchestrator root — read it first, mirror an existing subrepo entry's key style)
- Modify: `justfile` (orchestrator root — add the recipe near the existing `playtest` recipes, around line 573)

- [ ] **Step 1: Write `sidequest-understudy/README.md`**

```markdown
# sidequest-understudy

A naive simulated-player playtest client for SideQuest. Bots join a real
session through the actual React UI in a (headless) browser, perceive the
page the way a screen reader does, and role-play a seat in persona — one
LLM call per turn, model-agnostic (Anthropic / Ollama / claude -p).

**The naivety invariant:** the bot is handed only what a player is handed.
Interface confusion is a *finding*, not a failure.

## Run a table

    uv run understudy run runs/four_seat_demo.yaml          # headless
    uv run understudy run runs/four_seat_demo.yaml --headed # watch it play

To drive a seat yourself, set one seat to `human` in the manifest and join
the session_url in your own browser.

Reports land in `reports/<date>-<name>-rN/`: `report.md`, `findings.json`
(CONFIRMED / BEHAVIORAL / CLAIMED), per-seat transcripts, and the server's
`narration.turn` OTEL spans pulled from Jaeger.

Design: `oq-2/docs/superpowers/specs/2026-06-11-simulated-player-understudy-design.md`
```

- [ ] **Step 2: Commit the README, publish the repo, and PR to develop**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-understudy
git add README.md && git commit -m "docs: README"
env -u GITHUB_TOKEN gh repo create slabgorb/sidequest-understudy --private \
    --source . --push
git push -u origin develop feature/understudy-bootstrap
env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-understudy \
    --base develop --head feature/understudy-bootstrap \
    --title "Bootstrap sidequest-understudy" \
    --body "Naive simulated-player playtest client per the 2026-06-11 design spec."
env -u GITHUB_TOKEN gh pr merge -R slabgorb/sidequest-understudy --squash
```

(`env -u GITHUB_TOKEN` per the known gh-keyring shadow issue. If `gh repo create --source --push` complains because the current branch is the feature branch, push develop first: `git push -u origin develop`.)

- [ ] **Step 3: Register the repo in `repos.yaml`** (orchestrator)

Read `repos.yaml` first and mirror the existing entries' exact key style. Add:

```yaml
understudy:
  path: sidequest-understudy
  type: service
  description: Naive simulated-player playtest client — joins real sessions via the UI
```

Plus whatever base-branch key the sibling subrepo entries carry (`develop`, matching ui/content/daemon/server).

- [ ] **Step 4: Add the justfile recipe** (orchestrator, near the `playtest` recipes ~line 573)

```just
# Naive simulated-player table (sidequest-understudy)
understudy manifest *flags:
    cd {{root}}/sidequest-understudy && uv run understudy run runs/{{manifest}}.yaml {{flags}}
```

- [ ] **Step 5: Verify the recipe parses**

```bash
cd /Users/slabgorb/Projects/oq-2 && just --list | grep understudy
```

Expected: `understudy manifest *flags` listed.

- [ ] **Step 6: Commit the orchestrator wiring** (orchestrator commits go to `main`; run from the orchestrator root cwd)

```bash
cd /Users/slabgorb/Projects/oq-2
git add repos.yaml justfile
git commit -m "chore: wire sidequest-understudy — repos.yaml entry + just recipe"
```

---

## Deferred (designed, not built — do NOT implement in this plan)

- `understudy emit-pingpong <report-dir>` — opt-in CONFIRMED-only ping-pong emitter
- `--fast-chargen` (server auto-strategy reuse)
- Vision/pixel perception skin
- A gated live-stack smoke test (`UNDERSTUDY_LIVE=1` + real session URL) — add when the first real run happens, using whatever session the operator stands up
- An explicit barrier-stall signal (resolved act whose page never changes, N turns running). Today a stalled submit-and-wait barrier surfaces through `REPEATED_ACTION`, repeated `wait` rows, and the wall-clock cap; a dedicated `SignalKind` can be added once real runs show what the stall pattern actually looks like

## Verification after all tasks

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-understudy
uv run pytest -q          # full suite green
uv run ruff check .       # clean
uv run understudy run --help
cd /Users/slabgorb/Projects/oq-2 && just --list | grep understudy
```
