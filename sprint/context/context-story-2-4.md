---
parent: context-epic-2.md
---

# Story 2-4: SQLite Persistence — Rusqlite Schema, Save/Load GameSnapshot, Narrative Log, "Previously On" Recap

## Business Context

Python persists game state as JSON files and narrative log as JSONL. ADR-006 and ADR-023
upgrade this to SQLite — atomic writes, indexed queries, and crash recovery that loses at
most one turn. This story builds the persistence layer that story 2-2's session actor uses
to check for existing saves and that story 2-5's orchestrator uses to save after each turn.

**Python source:** `sq-2/sidequest/game/session.py` (SessionManager, 175 lines)
**Python source:** `sq-2/sidequest/game/state.py` lines 377-472 (save/load/backup methods)
**Python source:** `sq-2/sidequest/game/persistence.py` (NarrativeLog JSONL)
**ADRs:** ADR-006 (SQLite, not JSON files), ADR-023 (session persistence, "Previously On")
**Depends on:** Story 1-8 (GameSnapshot, state delta structs)

## Technical Approach

### What Python Does

```python
class SessionManager:
    def save(self, state: GameState):
        state.last_saved_at = datetime.now(tz=timezone.utc)
        # atomic write: temp file → rename
        tmp = self.session_dir / "state.json.tmp"
        tmp.write_text(state.model_dump_json(indent=2))
        tmp.rename(self.session_dir / "state.json")

    def load(self) -> SessionResult:
        state = GameState.model_validate_json(path.read_text())
        entries = NarrativeLog(path).load()
        recap = self._generate_recap(state, entries)
        return SessionResult(state, entries, recap)

class NarrativeLog:
    def append(self, entry: dict):
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")  # JSONL
```

The problems:
- JSON file writes can corrupt on crash (partial write before rename)
- No indexing — "find all entries from session 5" scans the whole file
- `_generate_recap()` loads ALL narrative entries to produce a summary
- Save/load are synchronous despite being in an async server
- No schema versioning — if GameState adds a field, old saves may fail
- Backup versioning is manual directory creation with metadata.json

### What Rust Does Differently

**SQLite via rusqlite — one .db file per save slot:**

```sql
-- Schema
CREATE TABLE session_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton row
    genre_slug TEXT NOT NULL,
    world_slug TEXT NOT NULL,
    created_at TEXT NOT NULL,               -- ISO 8601
    last_played TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE game_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton row
    snapshot_json TEXT NOT NULL,             -- serialized GameSnapshot
    saved_at TEXT NOT NULL
);

CREATE TABLE narrative_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_number INTEGER NOT NULL,
    author TEXT NOT NULL,                   -- "narrator", "combat", "player", etc.
    content TEXT NOT NULL,
    tags TEXT,                              -- JSON array of encounter tags
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_narrative_round ON narrative_log(round_number);
CREATE INDEX idx_narrative_author ON narrative_log(author);
```

**Why SQLite over JSON files:**
- **Atomic writes.** SQLite transactions are all-or-nothing — no partial file corruption.
- **Indexed queries.** "Give me the last 10 narrator entries" is an indexed query, not a full file scan.
- **Concurrent access.** SQLite handles WAL mode for reader/writer concurrency.
- **Schema versioning.** `schema_version` column enables migrations.
- **Single file.** One `.db` file instead of `state.json` + `narrative_log.jsonl` + `builders.json` + `backups/`.

**Type-system improvements:**
- Python's `SessionResult` is a dataclass with `state`, `entries`, `recap` all as separate fields that could be inconsistent. Rust loads everything in a single transaction — the state and entries are guaranteed to be from the same save point.
- Python's narrative entries are `dict[str, Any]`. Rust uses `NarrativeEntry` struct from sidequest-game (already defined in 1-7).
- Python's `_generate_recap` returns `str` and there's no type for "a recap exists or it doesn't." Rust returns `Option<String>` — no recap for fresh games.

### SessionStore Trait

```rust
/// Persistence contract — the server depends on this trait, not rusqlite directly.
pub trait SessionStore: Send + Sync {
    fn save(&self, snapshot: &GameSnapshot) -> Result<(), PersistError>;
    fn load(&self) -> Result<Option<SavedSession>, PersistError>;
    fn append_narrative(&self, entry: &NarrativeEntry) -> Result<(), PersistError>;
    fn recent_narrative(&self, limit: usize) -> Result<Vec<NarrativeEntry>, PersistError>;
    fn generate_recap(&self) -> Result<Option<String>, PersistError>;
    fn list_saves(root: &Path) -> Result<Vec<SaveInfo>, PersistError>;
}

pub struct SavedSession {
    pub meta: SessionMeta,
    pub snapshot: GameSnapshot,
    pub recap: Option<String>,
}

pub struct SessionMeta {
    pub genre_slug: String,
    pub world_slug: String,
    pub created_at: DateTime<Utc>,
    pub last_played: DateTime<Utc>,
}

pub struct SaveInfo {
    pub session_id: String,       // "genre/world"
    pub genre_slug: String,
    pub world_slug: String,
    pub characters: Vec<String>,  // character names
    pub last_played: Option<DateTime<Utc>>,
}
```

**Why a trait:** Testability. Unit tests use an in-memory SQLite database. Integration tests
use a temp directory. The server depends on the trait, not the concrete implementation.

### SqliteStore Implementation

```rust
pub struct SqliteStore {
    conn: Connection,  // rusqlite::Connection — NOT shared across threads
}

impl SqliteStore {
    pub fn open(path: &Path) -> Result<Self, PersistError> {
        let conn = Connection::open(path)?;
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")?;
        Self::migrate(&conn)?;
        Ok(Self { conn })
    }

    pub fn open_in_memory() -> Result<Self, PersistError> {
        let conn = Connection::open_in_memory()?;
        Self::migrate(&conn)?;
        Ok(Self { conn })
    }

    fn migrate(conn: &Connection) -> Result<(), PersistError> {
        // Create tables if not exist, check schema_version, apply migrations
    }
}
```

**Thread safety:** rusqlite's `Connection` is `!Send`. Each session's tokio task owns its
own `SqliteStore`. This avoids `Arc<Mutex<Connection>>` contention and matches the
session-as-actor pattern (ADR-003). If we need cross-session queries later (list saves),
those happen on a blocking thread via `tokio::task::spawn_blocking`.

### Save Flow

```rust
impl SessionStore for SqliteStore {
    fn save(&self, snapshot: &GameSnapshot) -> Result<(), PersistError> {
        let json = serde_json::to_string(snapshot)?;
        let now = Utc::now().to_rfc3339();
        self.conn.execute(
            "INSERT OR REPLACE INTO game_state (id, snapshot_json, saved_at) VALUES (1, ?1, ?2)",
            params![json, now],
        )?;
        self.conn.execute(
            "UPDATE session_meta SET last_played = ?1 WHERE id = 1",
            params![now],
        )?;
        Ok(())
    }
}
```

Atomic: both writes in a transaction. If the process crashes mid-save, SQLite rolls back.
Python's "write tmp → rename" is almost-atomic but can fail on some filesystems.

### "Previously On" Recap (ADR-023)

```rust
fn generate_recap(&self) -> Result<Option<String>, PersistError> {
    let entries: Vec<NarrativeEntry> = self.conn.prepare(
        "SELECT round_number, author, content FROM narrative_log ORDER BY id DESC LIMIT 20"
    )?.query_map([], |row| { ... })?.collect()?;

    if entries.is_empty() {
        return Ok(None);
    }

    // Build recap from recent entries:
    // "Previously On...\n\nThe party — {character names} — had been adventuring.\n\n"
    // + bullet points from recent narrative entries
    // + "The party now finds themselves at {location}."
    Ok(Some(recap))
}
```

Python loads ALL entries for recap. Rust queries only the last 20 — the recap is a summary,
not a transcript. The indexed query is O(1), not O(n).

### Save Directory Layout

```
~/.sidequest/saves/
├── mutant_wasteland/
│   └── flickering_reach/
│       └── save.db              ← single SQLite file
├── low_fantasy/
│   └── default/
│       └── save.db
```

Python has: `state.json` + `narrative_log.jsonl` + `builders.json` + `backups/v1/` + `backups/v2/` ...
Rust has: `save.db`. SQLite handles everything.

## Scope Boundaries

**In scope:**
- `SessionStore` trait with save/load/append_narrative/recent_narrative/generate_recap/list_saves
- `SqliteStore` implementation using rusqlite
- Schema creation and migration mechanism
- Atomic save (transaction for state + metadata)
- Narrative log append and indexed query
- "Previously On" recap generation from recent entries
- `SaveInfo` struct for save enumeration
- In-memory constructor for testing

**Out of scope:**
- Backup versioning (Python's backup system — SQLite's WAL provides crash recovery)
- Builder persistence (defer — restart creation on disconnect)
- Save file encryption or compression
- Cloud sync
- Multiplayer shared saves

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Create save | New session creates save.db with schema, writes initial state |
| Save state | GameSnapshot serialized to JSON, stored atomically in transaction |
| Load state | Existing save.db loads GameSnapshot, returns SavedSession |
| Narrative append | Entry appended to narrative_log table with round, author, content |
| Narrative query | `recent_narrative(10)` returns last 10 entries by insertion order |
| Recap generation | `generate_recap()` returns "Previously On..." text from recent entries |
| Empty recap | Fresh game with no entries → `generate_recap()` returns None |
| List saves | `list_saves(root)` scans directory tree, returns SaveInfo for each save.db |
| Crash recovery | Kill process mid-save → next load succeeds with last good state |
| In-memory tests | `SqliteStore::open_in_memory()` works for unit tests |
| Schema migration | Second open of same .db file is idempotent — no duplicate table errors |

## Type-System Wins Over Python

1. **`SessionStore` trait** — server depends on the contract, not rusqlite. Tests use in-memory. Python's SessionManager is concrete.
2. **`SavedSession` bundles state + meta + recap** — loaded in one transaction, guaranteed consistent. Python loads three separate things.
3. **`NarrativeEntry` is a struct** — not a dict. Missing fields are compile errors.
4. **`Option<String>` for recap** — no empty string ambiguity. Python returns `""` for no recap.
5. **`PersistError` enum** — typed errors for IO, SQL, serialization. Python catches `Exception`.
