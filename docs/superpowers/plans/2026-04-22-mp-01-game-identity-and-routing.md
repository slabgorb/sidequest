# Multiplayer Plan 01 — Game Identity & Routing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current `(genre, world, player)` save key with a canonical game slug that encodes an explicit `solo|multiplayer` mode, and wire slug-based routing end-to-end (REST + WebSocket + UI URL namespace).

**Architecture:** A game is identified by `<YYYY-MM-DD>-<world-slug>`. Mode is picked at world-select, frozen at creation, and stored in the save file. Same-day + same-world = resume, not a new game. One slug → one `.db` file → one Claude resume session ID (stored in the DB so it survives restarts).

**Tech Stack:** Python 3.12 (FastAPI, pydantic, sqlite3), pytest, React 18 + TypeScript (react-router), vitest.

---

## File Structure

**Create:**
- `sidequest-server/sidequest/game/game_slug.py` — slug generation + parsing helpers.
- `sidequest-server/tests/game/test_game_slug.py`
- `sidequest-server/tests/server/test_games_endpoints.py`
- `sidequest-server/tests/server/test_slug_wiring.py` — integration/wiring test.
- `sidequest-ui/src/screens/lobby/ModePicker.tsx` — solo/multiplayer toggle.
- `sidequest-ui/src/screens/lobby/__tests__/ModePicker.test.tsx`
- `sidequest-ui/src/screens/GameScreen.tsx` — thin wrapper that reads slug+mode from URL.
- `sidequest-ui/src/__tests__/slug-routing-wiring.test.tsx`

**Modify:**
- `sidequest-server/sidequest/game/persistence.py` — add `GameMode` enum, `games` table, `db_path_for_slug()`, store `claude_session_id`.
- `sidequest-server/sidequest/server/rest.py` — add `POST /api/games`, `GET /api/games/{slug}`, keep legacy endpoints deprecated but functional.
- `sidequest-server/sidequest/server/session_handler.py` — accept `game_slug` + `mode` on SESSION_EVENT{connect}.
- `sidequest-server/sidequest/protocol/messages.py` — extend connect payload with `game_slug` and `mode` fields.
- `sidequest-ui/src/App.tsx` — react-router with `/solo/:slug` and `/play/:slug`.
- `sidequest-ui/src/screens/lobby/useSessions.ts` — call `POST /api/games` instead of legacy save-new.

---

### Task 1: Slug generation module

**Files:**
- Create: `sidequest-server/sidequest/game/game_slug.py`
- Test: `sidequest-server/tests/game/test_game_slug.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/game/test_game_slug.py
from datetime import date
import pytest
from sidequest.game.game_slug import generate_slug, parse_slug, InvalidSlugError


def test_generate_slug_uses_date_and_world():
    assert generate_slug(world_slug="moldharrow-keep", today=date(2026, 4, 22)) == "2026-04-22-moldharrow-keep"


def test_generate_slug_rejects_empty_world():
    with pytest.raises(ValueError):
        generate_slug(world_slug="", today=date(2026, 4, 22))


def test_parse_slug_roundtrip():
    parsed = parse_slug("2026-04-22-moldharrow-keep")
    assert parsed.date == date(2026, 4, 22)
    assert parsed.world_slug == "moldharrow-keep"


def test_parse_slug_world_with_dashes():
    parsed = parse_slug("2026-12-01-the-iron-city")
    assert parsed.world_slug == "the-iron-city"


def test_parse_slug_rejects_missing_date():
    with pytest.raises(InvalidSlugError):
        parse_slug("moldharrow-keep")


def test_parse_slug_rejects_malformed_date():
    with pytest.raises(InvalidSlugError):
        parse_slug("2026-13-40-moldharrow")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-server && uv run pytest tests/game/test_game_slug.py -v`
Expected: ImportError — module does not exist.

- [ ] **Step 3: Implement the module**

```python
# sidequest-server/sidequest/game/game_slug.py
"""Game slug generation and parsing.

A game slug is the canonical identifier for a game:
    <YYYY-MM-DD>-<world-slug>

Same-day + same-world collisions are the resume path — they are expected.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


SLUG_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-z0-9][a-z0-9-]*)$")


class InvalidSlugError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedSlug:
    date: date
    world_slug: str


def generate_slug(world_slug: str, today: date) -> str:
    if not world_slug:
        raise ValueError("world_slug must not be empty")
    return f"{today.isoformat()}-{world_slug}"


def parse_slug(slug: str) -> ParsedSlug:
    m = SLUG_RE.match(slug)
    if not m:
        raise InvalidSlugError(f"not a valid game slug: {slug!r}")
    y, mo, d, world = m.groups()
    try:
        parsed_date = date(int(y), int(mo), int(d))
    except ValueError as exc:
        raise InvalidSlugError(f"invalid date in slug {slug!r}: {exc}") from exc
    return ParsedSlug(date=parsed_date, world_slug=world)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_game_slug.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/game_slug.py sidequest-server/tests/game/test_game_slug.py
git commit -m "feat(game): slug generation + parsing for game identity"
```

---

### Task 2: GameMode enum + games table schema

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py`
- Test: `sidequest-server/tests/game/test_persistence_games_table.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/game/test_persistence_games_table.py
from pathlib import Path
import pytest
from sidequest.game.persistence import (
    SqliteStore,
    GameMode,
    db_path_for_slug,
    upsert_game,
    get_game,
)


def test_game_mode_enum_values():
    assert GameMode.SOLO.value == "solo"
    assert GameMode.MULTIPLAYER.value == "multiplayer"


def test_db_path_for_slug_places_db_under_slug_dir(tmp_path: Path):
    p = db_path_for_slug(tmp_path, "2026-04-22-moldharrow-keep")
    assert p == tmp_path / "games" / "2026-04-22-moldharrow-keep" / "save.db"


def test_upsert_game_inserts_new_row(tmp_path: Path):
    db = db_path_for_slug(tmp_path, "2026-04-22-moldharrow-keep")
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db)
    store.initialize()
    upsert_game(store, slug="2026-04-22-moldharrow-keep", mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")
    row = get_game(store, "2026-04-22-moldharrow-keep")
    assert row is not None
    assert row.mode == GameMode.MULTIPLAYER
    assert row.genre_slug == "low_fantasy"
    assert row.world_slug == "moldharrow-keep"
    assert row.claude_session_id is None


def test_upsert_game_does_not_overwrite_mode_on_resume(tmp_path: Path):
    db = db_path_for_slug(tmp_path, "2026-04-22-moldharrow-keep")
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db)
    store.initialize()
    upsert_game(store, slug="2026-04-22-moldharrow-keep", mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")
    # Second call with different mode must NOT change the stored mode
    upsert_game(store, slug="2026-04-22-moldharrow-keep", mode=GameMode.SOLO,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")
    row = get_game(store, "2026-04-22-moldharrow-keep")
    assert row.mode == GameMode.MULTIPLAYER  # frozen at creation


def test_set_claude_session_id_persists(tmp_path: Path):
    db = db_path_for_slug(tmp_path, "2026-04-22-moldharrow-keep")
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db)
    store.initialize()
    upsert_game(store, slug="2026-04-22-moldharrow-keep", mode=GameMode.SOLO,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")
    from sidequest.game.persistence import set_claude_session_id
    set_claude_session_id(store, "2026-04-22-moldharrow-keep", "claude-sess-abc123")
    row = get_game(store, "2026-04-22-moldharrow-keep")
    assert row.claude_session_id == "claude-sess-abc123"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-server && uv run pytest tests/game/test_persistence_games_table.py -v`
Expected: ImportError — `GameMode`, `db_path_for_slug`, `upsert_game`, `get_game` not defined.

- [ ] **Step 3: Extend persistence.py**

Add to top of `sidequest-server/sidequest/game/persistence.py`:

```python
from enum import Enum


class GameMode(str, Enum):
    SOLO = "solo"
    MULTIPLAYER = "multiplayer"


@dataclass
class GameRow:
    slug: str
    mode: GameMode
    genre_slug: str
    world_slug: str
    claude_session_id: Optional[str]
    created_at: str
```

Extend `SCHEMA_SQL` by appending:

```sql
CREATE TABLE IF NOT EXISTS games (
    slug TEXT PRIMARY KEY,
    mode TEXT NOT NULL CHECK (mode IN ('solo', 'multiplayer')),
    genre_slug TEXT NOT NULL,
    world_slug TEXT NOT NULL,
    claude_session_id TEXT,
    created_at TEXT NOT NULL
);
```

Add helpers at bottom of the file:

```python
def db_path_for_slug(save_dir: Path, slug: str) -> Path:
    """New slug-keyed DB path. One .db per game slug."""
    return save_dir / "games" / slug / "save.db"


def upsert_game(
    store: SqliteStore,
    *,
    slug: str,
    mode: GameMode,
    genre_slug: str,
    world_slug: str,
) -> None:
    """Insert a game row if absent. Mode is frozen at creation; later upserts do NOT change it."""
    with store._connect() as conn:
        conn.execute(
            """INSERT INTO games (slug, mode, genre_slug, world_slug, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(slug) DO NOTHING""",
            (slug, mode.value, genre_slug, world_slug, _now_rfc3339()),
        )


def get_game(store: SqliteStore, slug: str) -> Optional[GameRow]:
    with store._connect() as conn:
        row = conn.execute(
            "SELECT slug, mode, genre_slug, world_slug, claude_session_id, created_at FROM games WHERE slug = ?",
            (slug,),
        ).fetchone()
    if row is None:
        return None
    return GameRow(
        slug=row[0],
        mode=GameMode(row[1]),
        genre_slug=row[2],
        world_slug=row[3],
        claude_session_id=row[4],
        created_at=row[5],
    )


def set_claude_session_id(store: SqliteStore, slug: str, claude_session_id: str) -> None:
    with store._connect() as conn:
        conn.execute(
            "UPDATE games SET claude_session_id = ? WHERE slug = ?",
            (claude_session_id, slug),
        )
```

(If `SqliteStore._connect()` doesn't exist under that name, use whatever context-manager method the existing file provides — inspect the file for the pattern. Do **not** invent a new connection method.)

- [ ] **Step 4: Run tests to verify pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_persistence_games_table.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/persistence.py sidequest-server/tests/game/test_persistence_games_table.py
git commit -m "feat(persistence): games table with frozen-at-creation mode + claude_session_id"
```

---

### Task 3: REST — POST /api/games (create or resume)

**Files:**
- Modify: `sidequest-server/sidequest/server/rest.py`
- Test: `sidequest-server/tests/server/test_games_endpoints.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_games_endpoints.py
from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sidequest.server.rest import create_rest_router
from fastapi import FastAPI


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.save_dir = tmp_path
    app.state.genre_pack_search_paths = []
    app.state.today_fn = lambda: date(2026, 4, 22)  # injectable clock
    app.include_router(create_rest_router())
    return TestClient(app)


def test_post_games_creates_new_game(client: TestClient):
    r = client.post("/api/games", json={
        "genre_slug": "low_fantasy",
        "world_slug": "moldharrow-keep",
        "mode": "multiplayer",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "2026-04-22-moldharrow-keep"
    assert body["mode"] == "multiplayer"
    assert body["resumed"] is False


def test_post_games_same_day_same_world_resumes(client: TestClient):
    first = client.post("/api/games", json={
        "genre_slug": "low_fantasy", "world_slug": "moldharrow-keep", "mode": "multiplayer",
    })
    assert first.status_code == 201
    second = client.post("/api/games", json={
        "genre_slug": "low_fantasy", "world_slug": "moldharrow-keep", "mode": "solo",
    })
    assert second.status_code == 200  # resumed, not created
    body = second.json()
    assert body["slug"] == "2026-04-22-moldharrow-keep"
    assert body["mode"] == "multiplayer"  # frozen — ignores the new mode request
    assert body["resumed"] is True


def test_post_games_rejects_invalid_mode(client: TestClient):
    r = client.post("/api/games", json={
        "genre_slug": "low_fantasy", "world_slug": "moldharrow-keep", "mode": "coop",
    })
    assert r.status_code == 422


def test_get_games_slug_returns_metadata(client: TestClient):
    client.post("/api/games", json={
        "genre_slug": "low_fantasy", "world_slug": "moldharrow-keep", "mode": "solo",
    })
    r = client.get("/api/games/2026-04-22-moldharrow-keep")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "2026-04-22-moldharrow-keep"
    assert body["mode"] == "solo"
    assert body["genre_slug"] == "low_fantasy"
    assert body["world_slug"] == "moldharrow-keep"


def test_get_games_slug_404_for_unknown(client: TestClient):
    r = client.get("/api/games/2026-01-01-nowhere")
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_games_endpoints.py -v`
Expected: 404 or attribute errors — endpoints don't exist yet.

- [ ] **Step 3: Add the endpoints**

In `sidequest-server/sidequest/server/rest.py`, add after existing response models:

```python
from datetime import date as _date_cls
from sidequest.game.game_slug import generate_slug
from sidequest.game.persistence import (
    GameMode,
    SqliteStore,
    db_path_for_slug,
    get_game,
    upsert_game,
)


class CreateGameRequest(BaseModel):
    genre_slug: str
    world_slug: str
    mode: GameMode  # pydantic rejects unknown enum values with 422


class GameResponse(BaseModel):
    slug: str
    mode: GameMode
    genre_slug: str
    world_slug: str
    resumed: bool
```

Inside `create_rest_router()`, add:

```python
@router.post("/api/games", status_code=201)
async def create_or_resume_game(req: CreateGameRequest, request: Request) -> Any:
    save_dir: Path = request.app.state.save_dir
    today_fn = getattr(request.app.state, "today_fn", _date_cls.today)
    slug = generate_slug(world_slug=req.world_slug, today=today_fn())
    db = db_path_for_slug(save_dir, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db)
    store.initialize()

    existing = get_game(store, slug)
    if existing is not None:
        payload = GameResponse(
            slug=slug, mode=existing.mode,
            genre_slug=existing.genre_slug, world_slug=existing.world_slug,
            resumed=True,
        )
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=200, content=payload.model_dump())

    upsert_game(store, slug=slug, mode=req.mode,
                genre_slug=req.genre_slug, world_slug=req.world_slug)
    return GameResponse(
        slug=slug, mode=req.mode,
        genre_slug=req.genre_slug, world_slug=req.world_slug,
        resumed=False,
    )


@router.get("/api/games/{slug}")
async def get_game_endpoint(slug: str, request: Request) -> GameResponse:
    save_dir: Path = request.app.state.save_dir
    db = db_path_for_slug(save_dir, slug)
    if not db.exists():
        raise HTTPException(status_code=404, detail=f"no game with slug {slug}")
    store = SqliteStore(db)
    store.initialize()
    row = get_game(store, slug)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no game with slug {slug}")
    return GameResponse(
        slug=row.slug, mode=row.mode,
        genre_slug=row.genre_slug, world_slug=row.world_slug,
        resumed=True,
    )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_games_endpoints.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/rest.py sidequest-server/tests/server/test_games_endpoints.py
git commit -m "feat(rest): POST /api/games + GET /api/games/{slug} with frozen-mode resume"
```

---

### Task 4: WebSocket connect — accept game_slug + mode

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` (connect payload)
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_session_handler_slug_connect.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_session_handler_slug_connect.py
from datetime import date
from pathlib import Path
import pytest
from sidequest.server.session_handler import WebSocketSessionHandler
from sidequest.protocol.messages import SessionEventMessage, SessionEventPayload
from sidequest.game.persistence import GameMode, SqliteStore, db_path_for_slug, upsert_game


@pytest.fixture
def seeded_game(tmp_path: Path) -> Path:
    slug = "2026-04-22-moldharrow-keep"
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db)
    store.initialize()
    upsert_game(store, slug=slug, mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")
    return tmp_path


@pytest.mark.asyncio
async def test_connect_by_slug_loads_existing_game(seeded_game: Path):
    handler = WebSocketSessionHandler(save_dir=seeded_game)
    msg = SessionEventMessage(
        type="SESSION_EVENT",
        player_id="alice",
        payload=SessionEventPayload(
            event="connect",
            game_slug="2026-04-22-moldharrow-keep",
        ),
    )
    outbound = await handler.handle_message(msg)
    assert any(getattr(m, "type", None) == "SESSION_CONNECTED" for m in outbound)
    assert handler.session_data is not None
    assert handler.session_data.game_slug == "2026-04-22-moldharrow-keep"
    assert handler.session_data.mode == GameMode.MULTIPLAYER


@pytest.mark.asyncio
async def test_connect_by_unknown_slug_errors(seeded_game: Path):
    handler = WebSocketSessionHandler(save_dir=seeded_game)
    msg = SessionEventMessage(
        type="SESSION_EVENT",
        player_id="alice",
        payload=SessionEventPayload(
            event="connect",
            game_slug="2020-01-01-nowhere",
        ),
    )
    outbound = await handler.handle_message(msg)
    assert any(getattr(m, "type", None) == "ERROR" for m in outbound)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_handler_slug_connect.py -v`
Expected: `game_slug` not a valid field on `SessionEventPayload`.

- [ ] **Step 3: Extend protocol**

In `sidequest-server/sidequest/protocol/messages.py`, add `game_slug: str | None = None` to `SessionEventPayload` (whichever class models the connect payload — locate with `grep -n "class SessionEventPayload" sidequest-server/sidequest/protocol/messages.py`). Leave legacy `genre`/`world`/`player_id` fields in place for backwards compat during migration.

- [ ] **Step 4: Add slug-connect branch in session_handler**

In `sidequest-server/sidequest/server/session_handler.py`, locate `_handle_connect` (around line 237). Add at the top of that method, before the existing `genre_slug = payload.genre or ""` line:

```python
# New slug-based path (preferred). Legacy genre+world path below remains for now.
if getattr(payload, "game_slug", None):
    from sidequest.game.persistence import (
        GameMode, SqliteStore, db_path_for_slug, get_game,
    )
    slug = payload.game_slug
    db = db_path_for_slug(self._save_dir, slug)
    if not db.exists():
        return [self._error(f"unknown game slug: {slug}", reconnect_required=False)]
    store = SqliteStore(db)
    store.initialize()
    row = get_game(store, slug)
    if row is None:
        return [self._error(f"unknown game slug: {slug}", reconnect_required=False)]
    self._session_data = SessionData(
        genre_slug=row.genre_slug,
        world_slug=row.world_slug,
        player_id=player_id,
        game_slug=slug,
        mode=row.mode,
        # ... existing fields required by SessionData, populated from loaded store
    )
    # (reuse the same post-load logic as the legacy path — emit SESSION_CONNECTED, etc.)
    return self._emit_session_connected()
```

Extend `SessionData` (around line 100) with:

```python
game_slug: str | None = None
mode: "GameMode | None" = None
```

If `_error` / `_emit_session_connected` helpers don't exist by those names, replace them with the actual helper calls the existing legacy branch uses (locate by reading the legacy branch that follows this insertion point).

- [ ] **Step 5: Run tests to verify pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_handler_slug_connect.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_session_handler_slug_connect.py
git commit -m "feat(ws): accept game_slug on SESSION_EVENT{connect}"
```

---

### Task 5: UI — react-router with /solo/:slug and /play/:slug

**Files:**
- Modify: `sidequest-ui/src/App.tsx`
- Create: `sidequest-ui/src/screens/GameScreen.tsx`
- Test: `sidequest-ui/src/__tests__/slug-routing.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// sidequest-ui/src/__tests__/slug-routing.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

describe('slug routing', () => {
  it('renders GameScreen at /solo/:slug with mode=solo', () => {
    render(
      <MemoryRouter initialEntries={['/solo/2026-04-22-moldharrow-keep']}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('game-screen')).toHaveAttribute('data-mode', 'solo');
    expect(screen.getByTestId('game-screen')).toHaveAttribute('data-slug', '2026-04-22-moldharrow-keep');
  });

  it('renders GameScreen at /play/:slug with mode=multiplayer', () => {
    render(
      <MemoryRouter initialEntries={['/play/2026-04-22-moldharrow-keep']}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('game-screen')).toHaveAttribute('data-mode', 'multiplayer');
  });

  it('renders lobby at /', () => {
    render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>);
    expect(screen.getByTestId('lobby-root')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/__tests__/slug-routing.test.tsx`
Expected: FAIL — App has no router.

- [ ] **Step 3: Create GameScreen**

```tsx
// sidequest-ui/src/screens/GameScreen.tsx
import { useParams } from 'react-router-dom';

export function GameScreen({ mode }: { mode: 'solo' | 'multiplayer' }) {
  const { slug = '' } = useParams<{ slug: string }>();
  return <div data-testid="game-screen" data-mode={mode} data-slug={slug} />;
}
```

- [ ] **Step 4: Rewire App.tsx router**

Read `sidequest-ui/src/App.tsx`, then replace the render tree with:

```tsx
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { GameScreen } from './screens/GameScreen';
// ... keep existing Lobby import

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LobbyRoot />} />
      <Route path="/solo/:slug" element={<GameScreen mode="solo" />} />
      <Route path="/play/:slug" element={<GameScreen mode="multiplayer" />} />
    </Routes>
  );
}

export default function App() {
  // In tests we wrap with MemoryRouter, so only add BrowserRouter in production entry point
  return <AppRoutes />;
}
```

Where `LobbyRoot` is whatever the current App.tsx rendered at the root level; wrap that existing JSX in a `<div data-testid="lobby-root">`. Move the top-level `BrowserRouter` to `main.tsx` so tests' MemoryRouter works.

- [ ] **Step 5: Run tests to verify pass**

Run: `cd sidequest-ui && npm test -- --run src/__tests__/slug-routing.test.tsx`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/App.tsx sidequest-ui/src/screens/GameScreen.tsx sidequest-ui/src/main.tsx sidequest-ui/src/__tests__/slug-routing.test.tsx
git commit -m "feat(ui): /solo/:slug and /play/:slug routing"
```

---

### Task 6: UI — ModePicker in lobby world-select

**Files:**
- Create: `sidequest-ui/src/screens/lobby/ModePicker.tsx`
- Test: `sidequest-ui/src/screens/lobby/__tests__/ModePicker.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// sidequest-ui/src/screens/lobby/__tests__/ModePicker.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ModePicker } from '../ModePicker';

describe('ModePicker', () => {
  it('defaults to solo', () => {
    const onChange = vi.fn();
    render(<ModePicker value="solo" onChange={onChange} />);
    expect(screen.getByRole('radio', { name: /solo/i })).toBeChecked();
  });

  it('calls onChange("multiplayer") when user picks MP', () => {
    const onChange = vi.fn();
    render(<ModePicker value="solo" onChange={onChange} />);
    fireEvent.click(screen.getByRole('radio', { name: /multiplayer/i }));
    expect(onChange).toHaveBeenCalledWith('multiplayer');
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/screens/lobby/__tests__/ModePicker.test.tsx`
Expected: file-not-found.

- [ ] **Step 3: Implement ModePicker**

```tsx
// sidequest-ui/src/screens/lobby/ModePicker.tsx
export type GameMode = 'solo' | 'multiplayer';

export function ModePicker({
  value,
  onChange,
}: {
  value: GameMode;
  onChange: (m: GameMode) => void;
}) {
  return (
    <fieldset>
      <legend>Mode</legend>
      <label>
        <input
          type="radio"
          name="mode"
          value="solo"
          checked={value === 'solo'}
          onChange={() => onChange('solo')}
        />
        Solo
      </label>
      <label>
        <input
          type="radio"
          name="mode"
          value="multiplayer"
          checked={value === 'multiplayer'}
          onChange={() => onChange('multiplayer')}
        />
        Multiplayer
      </label>
    </fieldset>
  );
}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd sidequest-ui && npm test -- --run src/screens/lobby/__tests__/ModePicker.test.tsx`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/screens/lobby/ModePicker.tsx sidequest-ui/src/screens/lobby/__tests__/ModePicker.test.tsx
git commit -m "feat(ui): ModePicker radio for solo vs multiplayer"
```

---

### Task 7: Wire ModePicker → POST /api/games → navigate to /solo|/play/:slug

**Files:**
- Modify: `sidequest-ui/src/screens/lobby/useSessions.ts` (or the lobby "start game" handler — locate the current world-select submit)
- Test: `sidequest-ui/src/screens/lobby/__tests__/useStartGame.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// sidequest-ui/src/screens/lobby/__tests__/useStartGame.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useStartGame } from '../useStartGame';

describe('useStartGame', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });

  it('POSTs to /api/games and returns the mode-prefixed URL', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        slug: '2026-04-22-moldharrow-keep',
        mode: 'multiplayer',
        genre_slug: 'low_fantasy',
        world_slug: 'moldharrow-keep',
        resumed: false,
      }),
    });
    const { result } = renderHook(() => useStartGame());
    const url = await result.current.start({
      genreSlug: 'low_fantasy',
      worldSlug: 'moldharrow-keep',
      mode: 'multiplayer',
    });
    expect(fetchMock).toHaveBeenCalledWith('/api/games', expect.objectContaining({ method: 'POST' }));
    expect(url).toBe('/play/2026-04-22-moldharrow-keep');
  });

  it('uses /solo/:slug when mode is solo', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        slug: '2026-04-22-moldharrow-keep', mode: 'solo',
        genre_slug: 'low_fantasy', world_slug: 'moldharrow-keep', resumed: false,
      }),
    });
    const { result } = renderHook(() => useStartGame());
    const url = await result.current.start({
      genreSlug: 'low_fantasy', worldSlug: 'moldharrow-keep', mode: 'solo',
    });
    expect(url).toBe('/solo/2026-04-22-moldharrow-keep');
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/screens/lobby/__tests__/useStartGame.test.tsx`
Expected: file-not-found.

- [ ] **Step 3: Implement the hook**

```tsx
// sidequest-ui/src/screens/lobby/useStartGame.ts
import { useCallback } from 'react';

export type StartGameInput = {
  genreSlug: string;
  worldSlug: string;
  mode: 'solo' | 'multiplayer';
};

export function useStartGame() {
  const start = useCallback(async (input: StartGameInput): Promise<string> => {
    const resp = await fetch('/api/games', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        genre_slug: input.genreSlug,
        world_slug: input.worldSlug,
        mode: input.mode,
      }),
    });
    if (!resp.ok) throw new Error(`start game failed: ${resp.status}`);
    const body = await resp.json();
    const prefix = body.mode === 'solo' ? '/solo' : '/play';
    return `${prefix}/${body.slug}`;
  }, []);
  return { start };
}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd sidequest-ui && npm test -- --run src/screens/lobby/__tests__/useStartGame.test.tsx`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/screens/lobby/useStartGame.ts sidequest-ui/src/screens/lobby/__tests__/useStartGame.test.tsx
git commit -m "feat(ui): useStartGame hook posts to /api/games + returns mode URL"
```

---

### Task 8: Wire ModePicker + useStartGame into the lobby world-select screen

**Files:**
- Modify: `sidequest-ui/src/screens/lobby/<current-world-select-component>.tsx` (locate with `grep -rn "worlds" sidequest-ui/src/screens/lobby`)

- [ ] **Step 1: Find the current submit path**

Run: `grep -rn "selectWorld\|startGame\|beginSession\|/api/saves/new" sidequest-ui/src/screens/lobby`
Write down the filename + submit handler name.

- [ ] **Step 2: Write failing integration test**

```tsx
// sidequest-ui/src/screens/lobby/__tests__/world-select-mode-wiring.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../../../App';

describe('world-select mode wiring', () => {
  it('sends mode + world to POST /api/games and navigates to the returned URL', async () => {
    const fetchMock = vi.fn()
      // GET /api/genres
      .mockResolvedValueOnce({ ok: true, json: async () => ({
        low_fantasy: { name: 'Low Fantasy', description: '', worlds: [
          { slug: 'moldharrow-keep', name: 'Moldharrow Keep', description: '', axis_snapshot: {}, inspirations: [] },
        ]},
      })})
      // POST /api/games
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({
        slug: '2026-04-22-moldharrow-keep', mode: 'multiplayer',
        genre_slug: 'low_fantasy', world_slug: 'moldharrow-keep', resumed: false,
      })});
    vi.stubGlobal('fetch', fetchMock);

    render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>);

    await waitFor(() => screen.getByText(/Moldharrow Keep/));
    fireEvent.click(screen.getByText(/Moldharrow Keep/));
    fireEvent.click(screen.getByRole('radio', { name: /multiplayer/i }));
    fireEvent.click(screen.getByRole('button', { name: /start/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/games', expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"mode":"multiplayer"'),
      }));
    });
    await waitFor(() => {
      expect(screen.getByTestId('game-screen')).toHaveAttribute('data-mode', 'multiplayer');
    });
  });
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/screens/lobby/__tests__/world-select-mode-wiring.test.tsx`
Expected: FAIL (no mode radio, no navigation wiring).

- [ ] **Step 4: Wire it into the world-select component**

In the component identified in step 1, add:

```tsx
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { ModePicker, type GameMode } from './ModePicker';
import { useStartGame } from './useStartGame';

// inside the component body:
const [mode, setMode] = useState<GameMode>('solo');
const { start } = useStartGame();
const navigate = useNavigate();

async function handleStart(genreSlug: string, worldSlug: string) {
  const url = await start({ genreSlug, worldSlug, mode });
  navigate(url);
}
```

Render `<ModePicker value={mode} onChange={setMode} />` in the selected-world panel, and wire the "Start" button to `() => handleStart(selectedGenre, selectedWorld)`.

- [ ] **Step 5: Run tests to verify pass**

Run: `cd sidequest-ui && npm test -- --run src/screens/lobby/__tests__/world-select-mode-wiring.test.tsx`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/screens/lobby/
git commit -m "feat(ui): wire ModePicker + useStartGame into lobby world-select"
```

---

### Task 9: End-to-end wiring test — UI → REST → WS

**Files:**
- Create: `sidequest-server/tests/server/test_slug_wiring.py`

- [ ] **Step 1: Write the wiring test**

```python
# sidequest-server/tests/server/test_slug_wiring.py
"""Integration: create a game via REST, then connect to it via WebSocket by slug."""
from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sidequest.server.app import create_app  # or wherever the app factory lives


@pytest.fixture
def app_client(tmp_path: Path):
    app = create_app(save_dir=tmp_path)
    app.state.today_fn = lambda: date(2026, 4, 22)
    return TestClient(app)


def test_create_game_then_connect_by_slug(app_client: TestClient):
    r = app_client.post("/api/games", json={
        "genre_slug": "low_fantasy",
        "world_slug": "moldharrow-keep",
        "mode": "multiplayer",
    })
    assert r.status_code == 201
    slug = r.json()["slug"]

    with app_client.websocket_connect("/ws") as ws:
        ws.send_json({
            "type": "SESSION_EVENT",
            "player_id": "alice",
            "payload": {"event": "connect", "game_slug": slug},
        })
        msg = ws.receive_json()
        assert msg["type"] in ("SESSION_CONNECTED", "NARRATION", "STATE_UPDATE")
```

- [ ] **Step 2: Locate the app factory**

Run: `grep -rn "def create_app\|FastAPI()" sidequest-server/sidequest`
If no `create_app` factory exists, import the app instance directly from wherever it's constructed and skip the `create_app(save_dir=...)` arg — instead `app.state.save_dir = tmp_path` after import.

- [ ] **Step 3: Run the wiring test**

Run: `cd sidequest-server && uv run pytest tests/server/test_slug_wiring.py -v`
Expected: 1 passed. If it fails because SESSION_EVENT isn't returning anything recognizable, that's a real wiring bug — fix it in session_handler so the slug branch does emit SESSION_CONNECTED.

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/tests/server/test_slug_wiring.py
git commit -m "test(wiring): end-to-end — POST /api/games then WS connect by slug"
```

---

### Task 10: Deprecate legacy save-key endpoints

**Files:**
- Modify: `sidequest-server/sidequest/server/rest.py`

- [ ] **Step 1: Mark legacy endpoints**

In `rest.py`, add deprecation log warnings to `GET /api/saves`, `POST /api/saves/new`, `DELETE /api/saves/{genre}/{world}/{player}`:

```python
import warnings

@router.post("/api/saves/new", deprecated=True)
async def legacy_saves_new(...):
    logger.warning("legacy /api/saves/new called — prefer POST /api/games")
    # ... keep existing body unchanged
```

Do **not** delete these yet. Plans 02/03 depend on nothing here; we can schedule removal as a chore after Plan 03 is in.

- [ ] **Step 2: Commit**

```bash
git add sidequest-server/sidequest/server/rest.py
git commit -m "chore(rest): mark legacy /api/saves endpoints deprecated"
```

---

## Plan 01 Self-Review

Spec sections covered:
- Slug generation, auto from date + world → **Task 1**
- Same-day resume → **Task 3** (`test_post_games_same_day_same_world_resumes`)
- Mode frozen at creation → **Task 2** (`test_upsert_game_does_not_overwrite_mode_on_resume`), **Task 3**
- URL namespace `/solo/:slug` vs `/play/:slug` → **Task 5**
- Mode picked at world-select → **Tasks 6–8**
- 1:1 slug ↔ SQLite save → **Task 2** (`db_path_for_slug`), **Task 4**
- Claude session ID storage (1:1) → **Task 2** (`set_claude_session_id`)
- WebSocket connect by slug → **Task 4**
- End-to-end wiring → **Task 9**

**Not covered here, deferred to Plan 02:** identity/join semantics, solo-single-slot enforcement, drop-out pause.
**Not covered here, deferred to Plan 03:** per-player filtered event log, projection sync.
