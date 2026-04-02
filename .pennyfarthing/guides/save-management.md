# Save File Management

Reference for managing SideQuest save files — cleanup, inspection, migration.

## Save File Location

```
~/.sidequest/saves/{genre}/{world}/{character}/save.db
```

Each character gets their own SQLite database. WAL journaling creates companion
`save.db-shm` and `save.db-wal` files (safe to leave; SQLite manages them).

## Schema (v1)

Three tables per save:

| Table | Type | Contents |
|-------|------|----------|
| `session_meta` | Singleton (id=1) | genre_slug, world_slug, created_at, last_played, schema_version |
| `game_state` | Singleton (id=1) | snapshot_json (full GameSnapshot as JSON), saved_at |
| `narrative_log` | Append-only | round_number, author, content, tags, created_at |

## Listing Saves

**Full inventory with sizes and dates:**
```bash
find ~/.sidequest/saves -name "save.db" -type f | while read f; do
  echo "$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$f")  $(du -h "$f" | cut -f1)  $f"
done | sort
```

**Quick count by genre:**
```bash
find ~/.sidequest/saves -name "save.db" | awk -F/ '{print $6}' | sort | uniq -c | sort -rn
```

## Identifying Real Sessions vs Empties

| Size | Meaning |
|------|---------|
| 4K | Empty or single-turn — character created but no gameplay |
| 20K-60K | Short session — a few turns of play |
| 60K-128K | Medium session — real gameplay history |
| 128K+ | Long session — extended play with narrative log |

## Inspecting a Save

```bash
# Schema version and session identity
sqlite3 save.db "SELECT * FROM session_meta"

# Character name and turn count from snapshot
sqlite3 save.db "SELECT json_extract(snapshot_json, '$.characters[0].core.name'), json_extract(snapshot_json, '$.turn_manager.interaction') FROM game_state"

# Narrative log entry count
sqlite3 save.db "SELECT COUNT(*) FROM narrative_log"

# Last 5 narrative entries
sqlite3 save.db "SELECT round_number, author, substr(content, 1, 80) FROM narrative_log ORDER BY id DESC LIMIT 5"

# Integrity check
sqlite3 save.db "PRAGMA integrity_check"
```

## Cleanup Procedure

1. **List everything** using the inventory command above
2. **Identify keepers** — saves with real gameplay you want to preserve
3. **Nuke by genre** (entire genre dirs): `rm -rf ~/.sidequest/saves/{genre}/`
4. **Selective nuke** (specific characters): `rm -rf ~/.sidequest/saves/{genre}/{world}/{character}/`
5. **Verify** what remains: `find ~/.sidequest/saves -name "save.db" | sort`

## Backup Before Surgery

```bash
# Back up specific saves before migration
mkdir -p ~/.sidequest/saves-backup
cp -r ~/.sidequest/saves/{genre}/{world}/{character} ~/.sidequest/saves-backup/
```

## Compatibility Notes

- **Backward compat** is built into GameSnapshot via `#[serde(default)]` on all fields
  and a `GameSnapshotRaw` migration layer. Old saves load with new fields defaulting.
- **No migration system yet** — schema_version exists but is always 1.
- **LoreStore is NOT persisted** — it's in-memory only, reconstructed from genre pack
  YAML on session resume. Game-accumulated lore (`lore_established: Vec<String>`)
  survives as text but not as searchable LoreFragments with embeddings.
- **Narrative log IS persisted** — append-only in the narrative_log table. Used for
  "Previously On..." recap generation on reconnect.
