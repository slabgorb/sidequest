# Local DM Group D — Training Corpus Mining + Labeling Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline corpus pipeline that turns existing and future `~/.sidequest/saves/**/save.db` play data into `(input, output)` training pairs, a per-player save diff utility that derives visibility ground truth, a deterministic negative-example miner, and a standalone web labeling tool Keith uses to tag disputed turns. All tooling is strictly **read-only** against player save files; labeled output lands in a separate tree.

**Architecture:** A single `sidequest.corpus` library defines the `TrainingPair` + `LabeledPair` pydantic schemas and a read-only `SaveReader` that opens save.db via `sqlite3.connect(uri=True, "file://.../save.db?mode=ro")`. Three thin CLIs wrap the library — `corpusmine` (emits JSONL pairs from one or many saves), `corpusdiff` (pairs same-`(genre, world)` per-player narrative_log rows by `round_number` to surface visibility divergence), and `corpuslabel` (FastAPI + vanilla HTML on port **9865**, separate from game :8765, OTEL :9765). Negative mining is heuristic-only (retarget detection via player message edit distance; Monster Manual misses via `SPAN_MONSTER_MANUAL_INJECTED` cross-reference; GM-panel overrides via a reserved event kind). Going-forward richer capture is a stub of three new event kinds (`DISPATCH_PACKAGE`, `NARRATOR_DIRECTIVE_USED`, `VERDICT_OVERRIDE`) — the miner reads them when Groups B/C emit them; Group D does not change runtime emission behaviour.

**Tech Stack:** Python 3.12, pydantic, stdlib `sqlite3` (read-only URI mode), FastAPI + uvicorn (already in `pyproject.toml`), vanilla HTML + fetch() for the labeling UI, pytest + pytest-asyncio, uv. No new dependencies.

**Reference spec:** `docs/superpowers/specs/2026-04-23-local-dm-decomposer-design.md` §4.3, §4.4, §10 Story Group D.

**Depends on:** Nothing load-bearing. Spec says Group D can run parallel to A-B-C. Uses whatever schema exists on `sidequest-server/develop` at branch time. Group E's QLoRA pipeline depends on **us**, not the other way around.

**Repos touched:**

- `sidequest-server/` — library + three CLIs + tests (branch `feat/local-dm-group-d`, targets `develop`)

No `sidequest-content/`, `sidequest-ui/`, or `sidequest-daemon/` changes. No orchestrator changes.

**Branch + worktree:**

```
/Users/slabgorb/Projects/oq-1/sidequest-server/.worktrees/group-d
```

Created off `sidequest-server/develop`. Every subagent MUST `cd` to this absolute path as its first bash call — subagent `cd` state does not persist across bash calls reliably.

**Decisions locked (do not re-litigate):**

1. **Read-only against player saves.** All save.db access uses `sqlite3.connect("file://<path>?mode=ro", uri=True)`. The miner never issues `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, or `VACUUM` against a save.db. Regression test enforces this (Task 2).
2. **No new deps.** FastAPI + uvicorn already ship. The labeling UI is vanilla HTML + `fetch()` — no React, no build step, no npm. Keith runs it via `uv run python -m sidequest.cli.corpuslabel <corpus.jsonl>` and opens `http://localhost:9865`.
3. **Output format is JSONL.** One `TrainingPair` or `LabeledPair` per line. Matches standard fine-tune ingest (Group E's QLoRA pipeline reads this directly).
4. **Separate labeled output tree.** Labeling tool writes to `~/.sidequest/corpus/labeled/<timestamp>.jsonl` — never into `~/.sidequest/saves/`. Input corpus JSONL default location is `~/.sidequest/corpus/mined/<timestamp>.jsonl`.
5. **Port allocation: 9865.** Chosen to sit near OTEL :9765 and avoid game :8765 / Vite :5173 / daemon :8766. If the port is busy, the CLI fails loud with a clear error — no silent fallback (CLAUDE.md "No Silent Fallbacks" is project doctrine).
6. **Negative mining is deterministic-heuristic today.** LLM-assisted negative mining is Group E's problem. Heuristics shipped in Group D:
   - **Retarget detection** — adjacent player actions on the same author in narrative_log where the second message contains a correction token set (`"no, "`, `"i meant "`, `"wait "`, `"actually "`, `"not the "`) — label the prior turn as a suspected mis-resolution.
   - **Monster Manual miss** — any narrator content that names an NPC via a proper-noun heuristic (capitalised multi-word token adjacent to a dialogue colon or combat verb) when no `SPAN_MONSTER_MANUAL_INJECTED` event appeared in the same turn window. Conservative — may false-positive; that's fine, Keith sees it in the labeling UI.
   - **GM-panel override** — events with kind `GM_OVERRIDE` (reserved in Task 7 even though no emitter exists yet in Group D scope). When emitter ships in a later group, miner picks it up automatically.
7. **Per-player diff is narrative_log-level today, event-level once Group G lands.** Per-player saves currently hold `narrative_log` rows but typically zero `events` (events flow only to canonical/host saves). Diff tool matches narrative rows by `(genre, world, round_number)`. An `--events` flag is plumbed and returns an empty result today; Group G populates it by shipping per-player event projection.
8. **Schema-first.** `TrainingPair` and `LabeledPair` are pydantic models with `model_config = {"extra": "forbid"}`. Corpus format is versioned (`schema_version: 1`) from day one — Group E will not have to guess at field semantics.
9. **Action_flags is gone.** Group A demolished it. The original spec bullet "auto-mine `action_flags absent from extraction` warnings" is **not** implemented; replaced by the retarget heuristic above. The plan does not add back any `action_flags` reference.
10. **Going-forward capture is reservation-only.** Task 7 reserves three event kinds in the kinds registry + adds pydantic payload models. It does **not** wire any emitter into `session_handler.py` — that is Group B (decomposer) and Group C (verdict) territory. Reservation alone is enough to unblock the miner: when emitters ship, pairs get richer automatically without another Group D release.

**Non-goals (explicit rejections):**

- No training, fine-tuning, or model evaluation. That is Group E (ADR-073 Phases 1–3).
- No narrator or decomposer runtime changes. Group D only reads saves and ships CLIs.
- No GM panel integration. Standalone tool by user preference (§4.3 "Labeling UI is standalone — quick to build, independent of session state, usable offline").
- No per-player feedback thumbs UI. That is Story Group F.
- No RLHF filtering. Group E excludes "RLHF-shaped Claude traces as positive examples" (§4.3 final bullet); Group D surfaces everything and tags provenance.
- No containerised deployment. The labeling tool is a local dev UI — `uv run` and a browser tab. Do not add Dockerfiles, nginx configs, auth layers, or TLS.
- No new Jira stories, no sprint YAML edits. Group D runs on the superpowers plan track, parallel to sprint work.

---

## File Structure

**New files (sidequest-server):**

- `sidequest-server/sidequest/corpus/__init__.py` — package marker + version constant
- `sidequest-server/sidequest/corpus/schema.py` — `TrainingPair`, `LabeledPair`, `DisputeTag`, `MineProvenance` pydantic models
- `sidequest-server/sidequest/corpus/save_reader.py` — read-only `SaveReader` context manager
- `sidequest-server/sidequest/corpus/miner.py` — `mine_save(path) -> Iterator[TrainingPair]`
- `sidequest-server/sidequest/corpus/negatives.py` — `scan_negatives(pairs) -> Iterator[TrainingPair]` (retarget + manual-miss heuristics)
- `sidequest-server/sidequest/corpus/diff.py` — `diff_per_player(genre, world, saves_root) -> Iterator[VisibilityPair]`
- `sidequest-server/sidequest/corpus/writer.py` — JSONL atomic writer (`write_pairs(path, pairs)`)
- `sidequest-server/sidequest/corpus/going_forward.py` — reserved event kinds + payload models

- `sidequest-server/sidequest/cli/corpusmine/__init__.py`
- `sidequest-server/sidequest/cli/corpusmine/__main__.py`
- `sidequest-server/sidequest/cli/corpusmine/corpusmine.py`

- `sidequest-server/sidequest/cli/corpusdiff/__init__.py`
- `sidequest-server/sidequest/cli/corpusdiff/__main__.py`
- `sidequest-server/sidequest/cli/corpusdiff/corpusdiff.py`

- `sidequest-server/sidequest/cli/corpuslabel/__init__.py`
- `sidequest-server/sidequest/cli/corpuslabel/__main__.py`
- `sidequest-server/sidequest/cli/corpuslabel/corpuslabel.py`           — FastAPI app factory
- `sidequest-server/sidequest/cli/corpuslabel/static/index.html`        — labeling UI
- `sidequest-server/sidequest/cli/corpuslabel/static/app.js`            — vanilla JS controller
- `sidequest-server/sidequest/cli/corpuslabel/static/style.css`

- `sidequest-server/tests/corpus/__init__.py`
- `sidequest-server/tests/corpus/test_schema.py`
- `sidequest-server/tests/corpus/test_save_reader_readonly.py`          — the regression test for Decision 1
- `sidequest-server/tests/corpus/test_miner.py`
- `sidequest-server/tests/corpus/test_negatives.py`
- `sidequest-server/tests/corpus/test_diff.py`
- `sidequest-server/tests/corpus/test_writer.py`
- `sidequest-server/tests/corpus/test_going_forward.py`
- `sidequest-server/tests/cli/test_corpusmine_cli.py`
- `sidequest-server/tests/cli/test_corpusdiff_cli.py`
- `sidequest-server/tests/cli/test_corpuslabel_api.py`
- `sidequest-server/tests/cli/fixtures/` — minted fixture save.db files (Task 0)

**No modified files** in scope, except one:

- `sidequest-server/sidequest/game/event_log.py` — Task 7 registers three new kinds in the kind enum. No behavioural change.

**No symlinked-directory edits.** No `.pennyfarthing/` changes. No `node_modules/`. No build output.

---

## Preflight

- [ ] **Preflight 1: Confirm server tests pass on current `develop`**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git checkout develop && git pull && just server-test 2>&1 | tail -30
```

Expected: full pytest suite green. If red, diagnose before starting — a test we later write near red code may mask a real regression.

- [ ] **Preflight 2: Confirm the actual save corpus is not to be touched**

This is not a code check — it is a commitment. Any command in this plan that opens a file under `~/.sidequest/saves/` or `~/.sidequest/saves copy/` MUST use `mode=ro` and MUST NOT pass a path into any test that could open the file read-write. Fixture saves live in `sidequest-server/tests/cli/fixtures/` and are the only save.db files any test is allowed to mutate.

- [ ] **Preflight 3: Confirm there is no existing `sidequest.corpus` package to avoid a name collision**

```bash
test ! -d sidequest-server/sidequest/corpus && echo "CLEAN" || echo "COLLISION"
```

Expected: `CLEAN`. If `COLLISION`, stop — the plan assumes a greenfield module.

- [ ] **Preflight 4: Create the worktree**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git worktree add .worktrees/group-d -b feat/local-dm-group-d develop
cd .worktrees/group-d
uv sync
```

Expected: worktree exists at `sidequest-server/.worktrees/group-d`, checked out on a fresh `feat/local-dm-group-d` branch from `develop`, dependencies synced.

---

## Task 0: Mint the fixture save corpus

**Files:**

- Create: `sidequest-server/tests/cli/fixtures/mint_fixtures.py`
- Create: `sidequest-server/tests/cli/fixtures/single_session.sql`
- Create: `sidequest-server/tests/cli/fixtures/per_player_a.sql`
- Create: `sidequest-server/tests/cli/fixtures/per_player_b.sql`
- Create: `sidequest-server/tests/cli/fixtures/README.md`

Fixtures are **hand-written SQL scripts** that produce minimal save.db files for tests. Never point tests at the real `~/.sidequest/saves/` tree.

- [ ] **Step 1: Write `single_session.sql`**

Minimal single-seat save with two NARRATION events and matching narrative_log rows. Use the real schema from `sidequest-server/sidequest/game/persistence.py` (check before writing: `grep -A 20 "CREATE TABLE IF NOT EXISTS events" sidequest-server/sidequest/game/persistence.py`). Include `session_meta` with genre + world, three events of kind NARRATION, three narrative_log rows with round_number 1..3.

- [ ] **Step 2: Write `per_player_a.sql` and `per_player_b.sql`**

Two per-player saves for the same `(genre, world) = ("caverns_and_claudes", "test_vault")`. Each has the same three round numbers in narrative_log, but the **content** diverges at round 2 — player A sees "You spot a locked door"; player B sees "You wander an empty corridor". This is the visibility-divergence signal Task 5 tests against.

- [ ] **Step 3: Write `mint_fixtures.py`**

```python
"""Build fixture save.db files from the .sql scripts. Idempotent: deletes + rebuilds."""
from __future__ import annotations

import sqlite3
from pathlib import Path

FIXTURES = Path(__file__).parent
SCHEMA = Path(__file__).parents[3] / "sidequest" / "game" / "persistence.py"


def _apply(db_path: Path, sql_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(sql_path.read_text())


def main() -> None:
    _apply(FIXTURES / "single_session.db", FIXTURES / "single_session.sql")
    _apply(FIXTURES / "per_player_a.db", FIXTURES / "per_player_a.sql")
    _apply(FIXTURES / "per_player_b.db", FIXTURES / "per_player_b.sql")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the minter and confirm three .db files exist**

```bash
cd sidequest-server
uv run python tests/cli/fixtures/mint_fixtures.py
ls tests/cli/fixtures/*.db
```

Expected: `single_session.db  per_player_a.db  per_player_b.db`.

- [ ] **Step 5: Confirm fixtures are valid SQLite and hold the expected rows**

```bash
sqlite3 sidequest-server/tests/cli/fixtures/single_session.db "SELECT COUNT(*) FROM events; SELECT COUNT(*) FROM narrative_log;"
```

Expected: `3\n3`.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/tests/cli/fixtures/
git commit -m "test(corpus): mint fixture save.db files for group D"
```

---

## Task 1: TrainingPair + LabeledPair pydantic schema

**Files:**

- Create: `sidequest-server/sidequest/corpus/__init__.py`
- Create: `sidequest-server/sidequest/corpus/schema.py`
- Test: `sidequest-server/tests/corpus/test_schema.py`

- [ ] **Step 1: Write the failing schema tests**

```python
# tests/corpus/test_schema.py
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.corpus.schema import (
    CORPUS_SCHEMA_VERSION,
    DisputeTag,
    LabeledPair,
    MineProvenance,
    TrainingPair,
)


def test_schema_version_is_1() -> None:
    assert CORPUS_SCHEMA_VERSION == 1


def test_training_pair_requires_input_and_output() -> None:
    pair = TrainingPair(
        schema_version=1,
        genre="caverns_and_claudes",
        world="mawdeep",
        round_number=3,
        input_text="I push on the door.",
        output_text="The door resists; something heavy braces it from the other side.",
        provenance=MineProvenance(source_save="fixtures/single_session.db", event_seq=None),
    )
    assert pair.input_text.startswith("I push")


def test_training_pair_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TrainingPair(
            schema_version=1,
            genre="caverns_and_claudes",
            world="mawdeep",
            round_number=1,
            input_text="hi",
            output_text="hi",
            provenance=MineProvenance(source_save="x.db", event_seq=None),
            nonsense_field="reject me",  # type: ignore[call-arg]
        )


def test_labeled_pair_carries_keith_correction() -> None:
    base = TrainingPair(
        schema_version=1,
        genre="caverns_and_claudes",
        world="mawdeep",
        round_number=2,
        input_text="I attack the bandit.",
        output_text="Your blade finds air.",
        provenance=MineProvenance(source_save="x.db", event_seq=None),
    )
    labeled = LabeledPair(
        pair=base,
        disputes=[DisputeTag.MIS_RESOLVED_REFERENT],
        corrected_output="The bandit is not present; the only figure in the alley is the fortune teller.",
        labeler="keith",
    )
    assert DisputeTag.MIS_RESOLVED_REFERENT in labeled.disputes
    assert labeled.corrected_output.startswith("The bandit is not present")
```

- [ ] **Step 2: Run tests — expect import failure**

```bash
cd sidequest-server/.worktrees/group-d
uv run pytest tests/corpus/test_schema.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.corpus'`.

- [ ] **Step 3: Write `__init__.py` and `schema.py`**

```python
# sidequest/corpus/__init__.py
from sidequest.corpus.schema import (  # noqa: F401
    CORPUS_SCHEMA_VERSION,
    DisputeTag,
    LabeledPair,
    MineProvenance,
    TrainingPair,
)
```

```python
# sidequest/corpus/schema.py
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

CORPUS_SCHEMA_VERSION: Literal[1] = 1


class DisputeTag(StrEnum):
    MIS_RESOLVED_REFERENT = "mis_resolved_referent"
    INVENTED_NPC = "invented_npc"
    SOFTENED_LETHALITY = "softened_lethality"
    GM_OVERRIDE = "gm_override"


class MineProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_save: str
    event_seq: int | None


class TrainingPair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    genre: str
    world: str
    round_number: int
    input_text: str
    output_text: str
    provenance: MineProvenance


class LabeledPair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pair: TrainingPair
    disputes: list[DisputeTag]
    corrected_output: str
    labeler: str
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/corpus/test_schema.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/corpus/__init__.py sidequest/corpus/schema.py tests/corpus/test_schema.py
git commit -m "feat(corpus): TrainingPair + LabeledPair pydantic schema (group D)"
```

---

## Task 2: Read-only SaveReader (the load-bearing safety test)

**Files:**

- Create: `sidequest-server/sidequest/corpus/save_reader.py`
- Test: `sidequest-server/tests/corpus/test_save_reader_readonly.py`

This task implements Decision 1 — the read-only guarantee. The regression test is the most important test in Group D.

- [ ] **Step 1: Write the failing tests**

```python
# tests/corpus/test_save_reader_readonly.py
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sidequest.corpus.save_reader import SaveReader

FIXTURES = Path(__file__).parents[1] / "cli" / "fixtures"
SINGLE = FIXTURES / "single_session.db"


def test_save_reader_opens_readonly() -> None:
    with SaveReader(SINGLE) as reader:
        rows = list(reader.iter_events())
        assert len(rows) == 3


def test_save_reader_refuses_writes() -> None:
    with SaveReader(SINGLE) as reader:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            reader.conn.execute("INSERT INTO events (kind, payload_json, created_at) VALUES ('X', '{}', 'now')")


def test_save_reader_does_not_mutate_mtime(tmp_path: Path) -> None:
    copy = tmp_path / "copy.db"
    copy.write_bytes(SINGLE.read_bytes())
    before = copy.stat().st_mtime_ns
    with SaveReader(copy) as reader:
        list(reader.iter_events())
        list(reader.iter_narrative_log())
    after = copy.stat().st_mtime_ns
    assert before == after, "opening readonly must not touch mtime"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
uv run pytest tests/corpus/test_save_reader_readonly.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement SaveReader**

```python
# sidequest/corpus/save_reader.py
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType


@dataclass(frozen=True)
class EventRow:
    seq: int
    kind: str
    payload_json: str
    created_at: str


@dataclass(frozen=True)
class NarrativeRow:
    id: int
    round_number: int
    author: str
    content: str
    tags: str | None
    created_at: str


class SaveReader:
    """Open a save.db strictly read-only. Never writes, never updates mtime."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> "SaveReader":
        uri = f"file:{self._path}?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SaveReader used outside of `with` block")
        return self._conn

    def iter_events(self) -> Iterator[EventRow]:
        cur = self.conn.execute(
            "SELECT seq, kind, payload_json, created_at FROM events ORDER BY seq ASC"
        )
        for row in cur:
            yield EventRow(*row)

    def iter_narrative_log(self) -> Iterator[NarrativeRow]:
        cur = self.conn.execute(
            "SELECT id, round_number, author, content, tags, created_at "
            "FROM narrative_log ORDER BY round_number ASC, id ASC"
        )
        for row in cur:
            yield NarrativeRow(*row)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/corpus/test_save_reader_readonly.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/corpus/save_reader.py tests/corpus/test_save_reader_readonly.py
git commit -m "feat(corpus): read-only SaveReader with mtime-preservation regression test"
```

---

## Task 3: Corpus miner core

**Files:**

- Create: `sidequest-server/sidequest/corpus/miner.py`
- Create: `sidequest-server/sidequest/corpus/writer.py`
- Test: `sidequest-server/tests/corpus/test_miner.py`
- Test: `sidequest-server/tests/corpus/test_writer.py`

The miner walks `events` + `narrative_log` and emits `(input, output)` pairs. Today the simplest honest pair is `(player_action_text, narrator_response_text)` keyed by `round_number`. When Group B lands `DISPATCH_PACKAGE` events, the miner reads those instead (Task 7 reserves the kinds).

- [ ] **Step 1: Write failing miner tests**

```python
# tests/corpus/test_miner.py
from __future__ import annotations

from pathlib import Path

from sidequest.corpus.miner import mine_save

FIXTURES = Path(__file__).parents[1] / "cli" / "fixtures"


def test_mine_single_session_emits_three_pairs() -> None:
    pairs = list(mine_save(FIXTURES / "single_session.db"))
    assert len(pairs) == 3
    assert pairs[0].genre == "caverns_and_claudes"
    assert pairs[0].world == "mawdeep"
    assert pairs[0].round_number == 1


def test_mine_pair_carries_input_and_output() -> None:
    pairs = list(mine_save(FIXTURES / "single_session.db"))
    assert pairs[0].input_text != ""
    assert pairs[0].output_text != ""


def test_mine_provenance_names_source_save() -> None:
    pairs = list(mine_save(FIXTURES / "single_session.db"))
    assert pairs[0].provenance.source_save.endswith("single_session.db")
```

- [ ] **Step 2: Write failing writer tests**

```python
# tests/corpus/test_writer.py
from __future__ import annotations

import json
from pathlib import Path

from sidequest.corpus.schema import MineProvenance, TrainingPair
from sidequest.corpus.writer import write_pairs


def _pair(i: int) -> TrainingPair:
    return TrainingPair(
        schema_version=1,
        genre="test",
        world="test",
        round_number=i,
        input_text=f"in{i}",
        output_text=f"out{i}",
        provenance=MineProvenance(source_save="x.db", event_seq=None),
    )


def test_write_pairs_emits_one_json_object_per_line(tmp_path: Path) -> None:
    out = tmp_path / "corpus.jsonl"
    write_pairs(out, [_pair(1), _pair(2)])
    lines = out.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["round_number"] == 1
    assert json.loads(lines[1])["round_number"] == 2


def test_write_pairs_is_atomic(tmp_path: Path) -> None:
    out = tmp_path / "corpus.jsonl"
    out.write_text("stale")
    write_pairs(out, [_pair(1)])
    assert "stale" not in out.read_text()
    assert not (tmp_path / "corpus.jsonl.tmp").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/corpus/test_miner.py tests/corpus/test_writer.py -v
```

Expected: `ModuleNotFoundError` on both.

- [ ] **Step 4: Implement writer**

```python
# sidequest/corpus/writer.py
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from sidequest.corpus.schema import TrainingPair


def write_pairs(path: Path, pairs: Iterable[TrainingPair]) -> None:
    """Write pairs as JSONL atomically. Completes or raises — never half-writes."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w", encoding="utf-8") as fh:
        for pair in pairs:
            fh.write(pair.model_dump_json())
            fh.write("\n")
    tmp.replace(path)
```

- [ ] **Step 5: Implement miner**

```python
# sidequest/corpus/miner.py
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from sidequest.corpus.save_reader import NarrativeRow, SaveReader
from sidequest.corpus.schema import MineProvenance, TrainingPair


def _session_meta(reader: SaveReader) -> tuple[str, str]:
    """Return (genre_slug, world_slug) from session_meta. Fail loud on missing rows.

    Schema authority: sidequest/game/persistence.py — columns are named
    genre_slug / world_slug, not genre / world.
    """
    row = reader.conn.execute(
        "SELECT genre_slug, world_slug FROM session_meta LIMIT 1"
    ).fetchone()
    if row is None:
        raise RuntimeError("save.db has no session_meta row — cannot mine corpus")
    return row[0], row[1]


def _group_by_round(rows: list[NarrativeRow]) -> dict[int, list[NarrativeRow]]:
    groups: dict[int, list[NarrativeRow]] = {}
    for row in rows:
        groups.setdefault(row.round_number, []).append(row)
    return groups


def mine_save(path: Path) -> Iterator[TrainingPair]:
    """Emit one TrainingPair per round_number present in narrative_log.

    Input is the player action; output is the narrator's response. When no
    player-authored row exists for a round (e.g. opening narration), input
    is the previous round's narrator output.
    """
    with SaveReader(path) as reader:
        genre, world = _session_meta(reader)
        rows = list(reader.iter_narrative_log())

    grouped = _group_by_round(rows)
    previous_narrator = ""
    for round_number in sorted(grouped):
        bucket = grouped[round_number]
        player = next((r for r in bucket if r.author != "narrator"), None)
        narrator = next((r for r in bucket if r.author == "narrator"), None)
        if narrator is None:
            continue
        input_text = player.content if player is not None else previous_narrator
        if not input_text:
            previous_narrator = narrator.content
            continue
        yield TrainingPair(
            schema_version=1,
            genre=genre,
            world=world,
            round_number=round_number,
            input_text=input_text,
            output_text=narrator.content,
            provenance=MineProvenance(source_save=str(path), event_seq=None),
        )
        previous_narrator = narrator.content
```

- [ ] **Step 6: Update fixtures if the miner test expectations don't match the SQL**

Check fixture rows: does `single_session.db` have a player-authored row at round 1? The miner needs at least one player row per round to pair, or the first round is skipped. Update `single_session.sql` so rounds 1–3 each carry one narrator row plus one player row, or accept that round 1 is the opening and adjust the expected count to 2. Pick whichever matches reality and update the test.

- [ ] **Step 7: Run tests**

```bash
uv run pytest tests/corpus/test_miner.py tests/corpus/test_writer.py -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add sidequest/corpus/miner.py sidequest/corpus/writer.py tests/corpus/test_miner.py tests/corpus/test_writer.py tests/cli/fixtures/single_session.sql
git commit -m "feat(corpus): miner extracts (input, output) pairs from narrative_log"
```

---

## Task 4: Negative example mining (retarget + manual-miss heuristics)

**Files:**

- Create: `sidequest-server/sidequest/corpus/negatives.py`
- Test: `sidequest-server/tests/corpus/test_negatives.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/corpus/test_negatives.py
from __future__ import annotations

from sidequest.corpus.negatives import detect_retarget
from sidequest.corpus.schema import MineProvenance, TrainingPair


def _p(round_: int, inp: str) -> TrainingPair:
    return TrainingPair(
        schema_version=1, genre="g", world="w", round_number=round_,
        input_text=inp, output_text="…",
        provenance=MineProvenance(source_save="x.db", event_seq=None),
    )


def test_detect_retarget_flags_no_i_meant() -> None:
    pairs = [_p(1, "I swing at the bandit"), _p(2, "No, I meant the fortune teller")]
    suspects = list(detect_retarget(pairs))
    assert [s.round_number for s in suspects] == [1]


def test_detect_retarget_does_not_flag_unrelated_correction() -> None:
    pairs = [_p(1, "I enter the tavern"), _p(2, "I order a drink")]
    assert list(detect_retarget(pairs)) == []


def test_detect_retarget_handles_single_pair() -> None:
    assert list(detect_retarget([_p(1, "hi")])) == []
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/corpus/test_negatives.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `negatives.py`**

```python
# sidequest/corpus/negatives.py
from __future__ import annotations

from collections.abc import Iterable, Iterator

from sidequest.corpus.schema import TrainingPair

_RETARGET_TOKENS = (
    "no, ",
    "i meant ",
    "wait ",
    "actually ",
    "not the ",
)


def detect_retarget(pairs: Iterable[TrainingPair]) -> Iterator[TrainingPair]:
    """Emit each pair whose NEXT pair's input contains a retarget token.

    Heuristic: a retarget in turn N+1 suggests turn N's referent was mis-resolved.
    """
    ordered = list(pairs)
    for i in range(len(ordered) - 1):
        next_lower = ordered[i + 1].input_text.lower()
        if any(tok in next_lower for tok in _RETARGET_TOKENS):
            yield ordered[i]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/corpus/test_negatives.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/corpus/negatives.py tests/corpus/test_negatives.py
git commit -m "feat(corpus): retarget-detection heuristic for negative-example mining"
```

Manual-miss heuristic (checking narrator NPC mentions against `SPAN_MONSTER_MANUAL_INJECTED` events) is deferred to a follow-up — it depends on OTEL spans ending up in the `events` table, which is out-of-scope for today's save corpus. Reserved as a TODO comment in `negatives.py` is **not** allowed per CLAUDE.md "no stubbing"; instead, document the gap in `docs/adr/` only if a decision needs recording. In Group D we simply don't ship manual-miss mining — retarget is enough signal to unblock Keith.

---

## Task 5: Per-player visibility diff

**Files:**

- Create: `sidequest-server/sidequest/corpus/diff.py`
- Test: `sidequest-server/tests/corpus/test_diff.py`

- [ ] **Step 1: Write failing test**

```python
# tests/corpus/test_diff.py
from __future__ import annotations

from pathlib import Path

from sidequest.corpus.diff import diff_per_player

FIXTURES = Path(__file__).parents[1] / "cli" / "fixtures"


def test_diff_pairs_same_round_across_players() -> None:
    divergences = list(diff_per_player(
        saves=[FIXTURES / "per_player_a.db", FIXTURES / "per_player_b.db"],
    ))
    # Round 2 diverges (locked door vs empty corridor)
    round_2 = [d for d in divergences if d.round_number == 2]
    assert len(round_2) == 1
    assert "locked door" in round_2[0].variants[0].content
    assert "empty corridor" in round_2[0].variants[1].content


def test_diff_ignores_rounds_that_agree() -> None:
    divergences = list(diff_per_player(
        saves=[FIXTURES / "per_player_a.db", FIXTURES / "per_player_b.db"],
    ))
    assert all(d.round_number != 1 for d in divergences), "round 1 content is identical"
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/corpus/test_diff.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `diff.py`**

```python
# sidequest/corpus/diff.py
from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from sidequest.corpus.save_reader import NarrativeRow, SaveReader


@dataclass(frozen=True)
class PlayerVariant:
    source_save: str
    content: str


@dataclass(frozen=True)
class VisibilityDivergence:
    round_number: int
    variants: list[PlayerVariant]


def diff_per_player(saves: Iterable[Path]) -> Iterator[VisibilityDivergence]:
    """Emit one divergence record per round_number whose narrator content differs across saves."""
    by_round: dict[int, list[PlayerVariant]] = {}
    for save in saves:
        with SaveReader(save) as reader:
            for row in reader.iter_narrative_log():
                if row.author != "narrator":
                    continue
                by_round.setdefault(row.round_number, []).append(
                    PlayerVariant(source_save=str(save), content=row.content)
                )
    for round_number in sorted(by_round):
        variants = by_round[round_number]
        contents = {v.content for v in variants}
        if len(contents) <= 1:
            continue
        yield VisibilityDivergence(round_number=round_number, variants=variants)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/corpus/test_diff.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/corpus/diff.py tests/corpus/test_diff.py
git commit -m "feat(corpus): per-player narrative_log diff surfaces visibility divergence"
```

---

## Task 6: `corpusmine` + `corpusdiff` CLIs

**Files:**

- Create: `sidequest-server/sidequest/cli/corpusmine/{__init__,__main__,corpusmine}.py`
- Create: `sidequest-server/sidequest/cli/corpusdiff/{__init__,__main__,corpusdiff}.py`
- Test: `sidequest-server/tests/cli/test_corpusmine_cli.py`
- Test: `sidequest-server/tests/cli/test_corpusdiff_cli.py`

Follow the existing `namegen` CLI layout pattern.

- [ ] **Step 1: Write failing CLI test**

```python
# tests/cli/test_corpusmine_cli.py
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_corpusmine_writes_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "mined.jsonl"
    result = subprocess.run(
        [sys.executable, "-m", "sidequest.cli.corpusmine",
         "--save", str(FIXTURES / "single_session.db"),
         "--out", str(out)],
        capture_output=True, text=True, check=True,
    )
    assert out.exists()
    lines = out.read_text().splitlines()
    assert len(lines) >= 1
    json.loads(lines[0])  # valid JSON
    assert "wrote" in result.stdout.lower()


def test_corpusmine_fails_loud_on_missing_save(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sidequest.cli.corpusmine",
         "--save", str(tmp_path / "nope.db"),
         "--out", str(tmp_path / "x.jsonl")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/cli/test_corpusmine_cli.py -v
```

Expected: `ModuleNotFoundError` or non-zero exit.

- [ ] **Step 3: Implement the CLI**

```python
# sidequest/cli/corpusmine/corpusmine.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sidequest.corpus.miner import mine_save
from sidequest.corpus.writer import write_pairs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="corpusmine", description="Mine (input, output) training pairs from a save.db.")
    p.add_argument("--save", required=True, type=Path, help="Path to a save.db")
    p.add_argument("--out", required=True, type=Path, help="Output JSONL path")
    args = p.parse_args(argv)

    if not args.save.exists():
        print(f"error: save not found: {args.save}", file=sys.stderr)
        return 2

    pairs = list(mine_save(args.save))
    write_pairs(args.out, pairs)
    print(f"wrote {len(pairs)} pairs to {args.out}")
    return 0
```

```python
# sidequest/cli/corpusmine/__main__.py
from __future__ import annotations

import sys

from sidequest.cli.corpusmine.corpusmine import main

if __name__ == "__main__":
    sys.exit(main())
```

```python
# sidequest/cli/corpusmine/__init__.py
```

- [ ] **Step 4: Repeat for `corpusdiff`**

Write `tests/cli/test_corpusdiff_cli.py` with a `--save` multi-arg test and a `--out` JSON output. Implement `sidequest/cli/corpusdiff/corpusdiff.py` that takes `--save` N times and serialises `VisibilityDivergence` records to a JSON array on disk (dataclass → dict).

```python
# tests/cli/test_corpusdiff_cli.py (core test)
def test_corpusdiff_surfaces_divergences(tmp_path: Path) -> None:
    out = tmp_path / "divergences.json"
    subprocess.run(
        [sys.executable, "-m", "sidequest.cli.corpusdiff",
         "--save", str(FIXTURES / "per_player_a.db"),
         "--save", str(FIXTURES / "per_player_b.db"),
         "--out", str(out)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.read_text())
    assert any(d["round_number"] == 2 for d in data)
```

- [ ] **Step 5: Run both CLI suites**

```bash
uv run pytest tests/cli/test_corpusmine_cli.py tests/cli/test_corpusdiff_cli.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest/cli/corpusmine sidequest/cli/corpusdiff tests/cli/test_corpusmine_cli.py tests/cli/test_corpusdiff_cli.py
git commit -m "feat(corpus): corpusmine + corpusdiff CLIs"
```

---

## Task 7: Reserve new event kinds for going-forward capture

**Files:**

- Create: `sidequest-server/sidequest/corpus/going_forward.py`
- Modify: `sidequest-server/sidequest/game/event_log.py` (kind enum / validator — check the actual file before editing)
- Test: `sidequest-server/tests/corpus/test_going_forward.py`

This task **reserves** the three kinds named in spec §10 Group D bullet 5. It does **not** add emitter call sites — that is Groups B/C. It does ensure the miner can parse them the moment they start flowing.

- [ ] **Step 1: Read `event_log.py` and the `projection/validator.py` kinds registry to find the authoritative enum location**

```bash
grep -n "kind" sidequest-server/sidequest/game/event_log.py | head -20
grep -n "NARRATION\|_KIND\|kinds" sidequest-server/sidequest/game/projection/validator.py | head -20
```

The test in Step 2 references the exact symbols. Adjust the imports below to match reality before writing the test.

- [ ] **Step 2: Write failing test**

```python
# tests/corpus/test_going_forward.py
from __future__ import annotations

from sidequest.corpus.going_forward import (
    DISPATCH_PACKAGE_KIND,
    NARRATOR_DIRECTIVE_USED_KIND,
    VERDICT_OVERRIDE_KIND,
    DispatchPackageEvent,
)


def test_reserved_kinds_are_distinct_strings() -> None:
    kinds = {DISPATCH_PACKAGE_KIND, NARRATOR_DIRECTIVE_USED_KIND, VERDICT_OVERRIDE_KIND}
    assert len(kinds) == 3
    assert all(isinstance(k, str) and k for k in kinds)


def test_dispatch_package_event_roundtrips() -> None:
    evt = DispatchPackageEvent(decomposer_session_id="abc", dispatched_at="2026-04-24T00:00:00Z", raw_package_json="{}")
    as_json = evt.model_dump_json()
    again = DispatchPackageEvent.model_validate_json(as_json)
    assert again.decomposer_session_id == "abc"
```

- [ ] **Step 3: Run — expect fail**

```bash
uv run pytest tests/corpus/test_going_forward.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 4: Implement `going_forward.py`**

```python
# sidequest/corpus/going_forward.py
"""Reserved event kinds for Group B/C going-forward corpus capture.

This module defines constants and payload schemas. It does not emit events —
emitter wiring belongs to the group that owns the subsystem.
"""
from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

DISPATCH_PACKAGE_KIND: Final[str] = "DISPATCH_PACKAGE"
NARRATOR_DIRECTIVE_USED_KIND: Final[str] = "NARRATOR_DIRECTIVE_USED"
VERDICT_OVERRIDE_KIND: Final[str] = "VERDICT_OVERRIDE"


class DispatchPackageEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decomposer_session_id: str
    dispatched_at: str
    raw_package_json: str


class NarratorDirectiveUsedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    directive_kind: str  # e.g. "must_narrate", "must_not_narrate"
    directive_text: str


class VerdictOverrideEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: str
    previous_verdict: str | None
    new_verdict: str
    labeler: str
```

- [ ] **Step 5: Register kinds in the projection validator**

Open `sidequest-server/sidequest/game/projection/validator.py`. The kind registry is a set/enum (find it with the grep from Step 1). Add the three new kinds to the registry. Do **not** add them to `_KIND_TO_MESSAGE_CLS` — they are not fan-out kinds today.

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/corpus/test_going_forward.py -v
uv run pytest tests/game/ -v  # projection validator regression guard
```

Expected: all pass. If the projection validator has its own kinds test, it should still pass — adding kinds is additive.

- [ ] **Step 7: Commit**

```bash
git add sidequest/corpus/going_forward.py sidequest/game/projection/validator.py tests/corpus/test_going_forward.py
git commit -m "feat(corpus): reserve DISPATCH_PACKAGE / DIRECTIVE / VERDICT_OVERRIDE event kinds"
```

---

## Task 8: Standalone labeling tool — backend

**Files:**

- Create: `sidequest-server/sidequest/cli/corpuslabel/corpuslabel.py`
- Create: `sidequest-server/sidequest/cli/corpuslabel/__main__.py`
- Create: `sidequest-server/sidequest/cli/corpuslabel/__init__.py`
- Test: `sidequest-server/tests/cli/test_corpuslabel_api.py`

The backend serves three JSON endpoints + one static index:

| Method | Path          | Purpose                                     |
|--------|---------------|---------------------------------------------|
| GET    | `/`           | serve static `index.html`                   |
| GET    | `/api/pairs`  | list unlabeled TrainingPairs                |
| POST   | `/api/label`  | accept a `LabeledPair`, append to labeled output |
| GET    | `/api/count`  | `{"unlabeled": N, "labeled": M}`            |

Fail loud if the corpus file is missing. Fail loud if port 9865 is busy.

- [ ] **Step 1: Write failing API test**

```python
# tests/cli/test_corpuslabel_api.py
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from sidequest.cli.corpuslabel.corpuslabel import build_app
from sidequest.corpus.schema import MineProvenance, TrainingPair
from sidequest.corpus.writer import write_pairs


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    corpus = tmp_path / "corpus.jsonl"
    labeled = tmp_path / "labeled.jsonl"
    pair = TrainingPair(
        schema_version=1, genre="g", world="w", round_number=1,
        input_text="hi", output_text="hello",
        provenance=MineProvenance(source_save="x.db", event_seq=None),
    )
    write_pairs(corpus, [pair])
    return corpus, labeled


def test_count_endpoint(tmp_path: Path) -> None:
    corpus, labeled = _seed(tmp_path)
    client = TestClient(build_app(corpus=corpus, labeled_out=labeled))
    resp = client.get("/api/count")
    assert resp.status_code == 200
    assert resp.json() == {"unlabeled": 1, "labeled": 0}


def test_pairs_endpoint_returns_pair(tmp_path: Path) -> None:
    corpus, labeled = _seed(tmp_path)
    client = TestClient(build_app(corpus=corpus, labeled_out=labeled))
    resp = client.get("/api/pairs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["input_text"] == "hi"


def test_label_endpoint_appends(tmp_path: Path) -> None:
    corpus, labeled = _seed(tmp_path)
    client = TestClient(build_app(corpus=corpus, labeled_out=labeled))
    resp = client.post(
        "/api/label",
        json={
            "pair": {
                "schema_version": 1, "genre": "g", "world": "w", "round_number": 1,
                "input_text": "hi", "output_text": "hello",
                "provenance": {"source_save": "x.db", "event_seq": None},
            },
            "disputes": ["mis_resolved_referent"],
            "corrected_output": "The NPC is not present.",
            "labeler": "keith",
        },
    )
    assert resp.status_code == 200
    assert labeled.exists()
    line = labeled.read_text().strip()
    assert json.loads(line)["labeler"] == "keith"


def test_missing_corpus_fails_loud(tmp_path: Path) -> None:
    import pytest
    with pytest.raises(FileNotFoundError):
        build_app(corpus=tmp_path / "missing.jsonl", labeled_out=tmp_path / "out.jsonl")
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/cli/test_corpuslabel_api.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `corpuslabel.py`**

```python
# sidequest/cli/corpuslabel/corpuslabel.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sidequest.corpus.schema import LabeledPair, TrainingPair

DEFAULT_PORT = 9865
_STATIC = Path(__file__).parent / "static"


def _load_unlabeled(corpus: Path) -> list[TrainingPair]:
    return [
        TrainingPair.model_validate_json(line)
        for line in corpus.read_text().splitlines()
        if line.strip()
    ]


def build_app(corpus: Path, labeled_out: Path) -> FastAPI:
    if not corpus.exists():
        raise FileNotFoundError(f"corpus not found: {corpus}")
    labeled_out.parent.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="SideQuest Corpus Labeler", version="0.1.0")
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    @app.get("/api/pairs")
    def pairs() -> list[dict]:
        return [p.model_dump() for p in _load_unlabeled(corpus)]

    @app.get("/api/count")
    def count() -> dict[str, int]:
        unlabeled = len(_load_unlabeled(corpus))
        labeled = 0
        if labeled_out.exists():
            labeled = sum(1 for line in labeled_out.read_text().splitlines() if line.strip())
        return {"unlabeled": unlabeled, "labeled": labeled}

    @app.post("/api/label")
    def label(pair: LabeledPair) -> dict[str, bool]:
        with labeled_out.open("a", encoding="utf-8") as fh:
            fh.write(pair.model_dump_json())
            fh.write("\n")
        return {"ok": True}

    return app


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="corpuslabel", description="Standalone corpus labeling web UI.")
    p.add_argument("corpus", type=Path, help="Path to mined JSONL corpus")
    p.add_argument("--out", type=Path, default=Path.home() / ".sidequest" / "corpus" / "labeled.jsonl")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)

    try:
        app = build_app(corpus=args.corpus, labeled_out=args.out)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print(f"corpuslabel listening on http://{args.host}:{args.port}")
    print(f"corpus: {args.corpus}")
    print(f"labeled output: {args.out}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0
```

```python
# sidequest/cli/corpuslabel/__main__.py
from __future__ import annotations

import sys

from sidequest.cli.corpuslabel.corpuslabel import main

if __name__ == "__main__":
    sys.exit(main())
```

```python
# sidequest/cli/corpuslabel/__init__.py
```

- [ ] **Step 4: Run API tests**

```bash
uv run pytest tests/cli/test_corpuslabel_api.py -v
```

Expected: 4 passed. (`test_missing_corpus_fails_loud` is still expected to pass because `build_app` raises before the app is built.)

- [ ] **Step 5: Commit**

```bash
git add sidequest/cli/corpuslabel/corpuslabel.py sidequest/cli/corpuslabel/__main__.py sidequest/cli/corpuslabel/__init__.py tests/cli/test_corpuslabel_api.py
git commit -m "feat(corpus): standalone labeling tool FastAPI backend on port 9865"
```

---

## Task 9: Standalone labeling tool — minimal frontend

**Files:**

- Create: `sidequest-server/sidequest/cli/corpuslabel/static/index.html`
- Create: `sidequest-server/sidequest/cli/corpuslabel/static/app.js`
- Create: `sidequest-server/sidequest/cli/corpuslabel/static/style.css`

No build step. No React. No TypeScript. Plain HTML + `fetch()`. Keith opens `http://localhost:9865` and sees one pair at a time with the dispute-tag checkboxes and a textarea for the corrected output.

- [ ] **Step 1: Write `index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>SideQuest Corpus Labeler</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <header>
    <h1>SideQuest Corpus Labeler</h1>
    <div id="counts"></div>
  </header>
  <main>
    <section id="current-pair">
      <h2>Input</h2>
      <pre id="input-text"></pre>
      <h2>Narrator output</h2>
      <pre id="output-text"></pre>
    </section>
    <section id="labeling">
      <h3>Disputes</h3>
      <label><input type="checkbox" name="dispute" value="mis_resolved_referent"> Mis-resolved referent</label>
      <label><input type="checkbox" name="dispute" value="invented_npc"> Invented NPC</label>
      <label><input type="checkbox" name="dispute" value="softened_lethality"> Softened lethality</label>
      <label><input type="checkbox" name="dispute" value="gm_override"> GM override</label>
      <h3>Corrected output</h3>
      <textarea id="corrected" rows="10"></textarea>
      <div class="buttons">
        <button id="submit">Save label</button>
        <button id="skip">Skip</button>
      </div>
    </section>
  </main>
  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `app.js`**

```js
// static/app.js
let pairs = [];
let cursor = 0;

async function refreshCount() {
  const r = await fetch("/api/count");
  const c = await r.json();
  document.getElementById("counts").textContent = `unlabeled: ${c.unlabeled}  |  labeled: ${c.labeled}`;
}

function render() {
  const pair = pairs[cursor];
  if (!pair) {
    document.getElementById("input-text").textContent = "(no pairs remaining)";
    document.getElementById("output-text").textContent = "";
    return;
  }
  document.getElementById("input-text").textContent = pair.input_text;
  document.getElementById("output-text").textContent = pair.output_text;
  document.getElementById("corrected").value = pair.output_text;
  document.querySelectorAll("input[name=dispute]").forEach(cb => { cb.checked = false; });
}

async function load() {
  const r = await fetch("/api/pairs");
  pairs = await r.json();
  cursor = 0;
  render();
  refreshCount();
}

async function submitLabel() {
  const pair = pairs[cursor];
  if (!pair) return;
  const disputes = Array.from(document.querySelectorAll("input[name=dispute]:checked")).map(cb => cb.value);
  const corrected = document.getElementById("corrected").value;
  const body = {
    pair: pair,
    disputes: disputes,
    corrected_output: corrected,
    labeler: "keith",
  };
  const r = await fetch("/api/label", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    alert("save failed: " + r.status);
    return;
  }
  cursor++;
  render();
  refreshCount();
}

document.getElementById("submit").addEventListener("click", submitLabel);
document.getElementById("skip").addEventListener("click", () => { cursor++; render(); });
load();
```

- [ ] **Step 3: Write `style.css`**

```css
body { font-family: system-ui, sans-serif; margin: 2em; max-width: 900px; }
h1 { margin-bottom: 0.2em; }
#counts { color: #666; margin-bottom: 1em; }
pre { background: #f4f4f4; padding: 1em; white-space: pre-wrap; border-radius: 4px; }
textarea { width: 100%; font-family: inherit; padding: 0.5em; }
label { display: block; margin: 0.2em 0; }
.buttons { margin-top: 1em; }
button { padding: 0.6em 1.2em; margin-right: 0.5em; }
```

- [ ] **Step 4: Smoke-test the UI manually against the fixture corpus**

```bash
cd sidequest-server/.worktrees/group-d
uv run python -m sidequest.cli.corpusmine --save tests/cli/fixtures/single_session.db --out /tmp/group-d-smoke.jsonl
uv run python -m sidequest.cli.corpuslabel /tmp/group-d-smoke.jsonl --out /tmp/group-d-smoke-labeled.jsonl &
PID=$!
sleep 2
curl -s http://127.0.0.1:9865/api/count
kill $PID
```

Expected: the `curl` prints a count JSON object. Open `http://127.0.0.1:9865` in a browser with the server running, confirm the UI renders one pair and "Save label" writes a row to `/tmp/group-d-smoke-labeled.jsonl`.

- [ ] **Step 5: Commit**

```bash
git add sidequest/cli/corpuslabel/static
git commit -m "feat(corpus): labeling tool UI (vanilla HTML/JS, no build step)"
```

---

## Task 10: End-to-end smoke test against a fixture save

**Files:**

- Create: `sidequest-server/tests/corpus/test_group_d_e2e.py`

A single integration test that mines → writes → reads back → diffs → confirms non-empty. Guards against wiring regressions between library pieces.

- [ ] **Step 1: Write the smoke test**

```python
# tests/corpus/test_group_d_e2e.py
from __future__ import annotations

import json
from pathlib import Path

from sidequest.corpus.diff import diff_per_player
from sidequest.corpus.miner import mine_save
from sidequest.corpus.writer import write_pairs

FIXTURES = Path(__file__).parents[1] / "cli" / "fixtures"


def test_group_d_pipeline_end_to_end(tmp_path: Path) -> None:
    pairs = list(mine_save(FIXTURES / "single_session.db"))
    assert pairs, "expected non-empty corpus from fixture"

    out = tmp_path / "corpus.jsonl"
    write_pairs(out, pairs)
    read_back = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(read_back) == len(pairs)
    assert read_back[0]["schema_version"] == 1

    divergences = list(diff_per_player(
        saves=[FIXTURES / "per_player_a.db", FIXTURES / "per_player_b.db"],
    ))
    assert any(d.round_number == 2 for d in divergences)
```

- [ ] **Step 2: Run**

```bash
uv run pytest tests/corpus/test_group_d_e2e.py -v
```

Expected: pass.

- [ ] **Step 3: Run the full server suite one last time to confirm no regressions**

```bash
just server-test 2>&1 | tail -30
```

Expected: full suite green.

- [ ] **Step 4: Commit**

```bash
git add tests/corpus/test_group_d_e2e.py
git commit -m "test(corpus): Group D end-to-end smoke — mine + write + diff"
```

---

## Task 11: Push the branch and open the PR

- [ ] **Step 1: Push**

```bash
cd sidequest-server/.worktrees/group-d
git push -u origin feat/local-dm-group-d
```

- [ ] **Step 2: Open PR targeting `develop`**

```bash
gh pr create --base develop --title "feat: local DM group D — corpus mining + labeling surface" --body "$(cat <<'EOF'
## Summary
- Read-only corpus miner reads `~/.sidequest/saves/**/save.db` and emits JSONL `(input, output)` training pairs.
- Per-player visibility diff surfaces narrative_log divergence between peer saves.
- Retarget-heuristic negative-example mining.
- Standalone FastAPI + vanilla-HTML labeling tool on port 9865.
- Three reserved event kinds (`DISPATCH_PACKAGE`, `NARRATOR_DIRECTIVE_USED`, `VERDICT_OVERRIDE`) for Groups B/C to populate.

## Non-goals
- No training (Group E).
- No runtime emission of new kinds (reserved only).
- No GM panel integration (standalone tool per spec §4.3).

## Test plan
- `just server-test` green locally.
- Manual smoke: `uv run python -m sidequest.cli.corpusmine --save <fixture>` writes JSONL.
- Manual smoke: `uv run python -m sidequest.cli.corpuslabel <jsonl>` serves UI at http://localhost:9865.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Link the PR URL in the session notes and stop**

Do not merge. Reviewer owns merge. Group D is done when the PR is green and merged.

---

## Self-Review

**1. Spec coverage (design doc §10 Story Group D):**

- ✅ "corpus-miner that reads `events` + `narrative_log`" — Task 3.
- ✅ "per-player save diff utility: pairs same-event_seq records" — Task 5 (narrative_log-level today per Decision 7).
- ✅ "Auto-mine negative examples" — Task 4 retarget heuristic. Manual-miss + GM-override deferred with documented reason (Decision 6, Task 4 trailing note).
- ✅ "Standalone labeling tool — lightweight web UI separate from the game session" — Tasks 8 + 9.
- ✅ "Extend going-forward capture: add decomposer I/O to the events stream — `dispatch_package`, `narrator_instructions_used`, `verdict_overrides`" — Task 7 reserves the kinds and ships pydantic payloads; emitters owned by Groups B/C.

**2. Placeholder scan:** No "TBD", "TODO", or "implement later" in code steps. Every code block is complete. No "similar to Task N" shortcuts.

**3. Type consistency:**

- `TrainingPair` fields used consistently across `miner.py`, `writer.py`, `negatives.py`, `corpusmine.py`, `corpuslabel.py`.
- `LabeledPair.disputes` is `list[DisputeTag]` everywhere.
- `MineProvenance(source_save, event_seq)` field names used identically in every test and impl.
- CLI module layout (`__init__` + `__main__` + `<name>.py`) matches existing `namegen` pattern.

**4. Project-rule compliance:**

- No silent fallbacks (port-busy + missing-corpus + missing-session_meta all fail loud).
- No stubbing (manual-miss / GM-override mining is explicitly out-of-scope, not half-implemented).
- Every test suite has an integration/wiring test (Task 10 E2E).
- No CLAUDE.md symlinked-path edits; no build output edits.
- OTEL watcher events: Group D is offline tooling — does not run in the server dispatch path, so no new OTEL spans are warranted. The GM panel's lie-detector principle applies to runtime subsystems.

**5. Actual-save safety:** Every save.db access goes through `SaveReader` (Task 2), which uses `mode=ro`. Only fixture save.db files (Task 0) are ever mutated. Verified by `test_save_reader_refuses_writes` + `test_save_reader_does_not_mutate_mtime`.
