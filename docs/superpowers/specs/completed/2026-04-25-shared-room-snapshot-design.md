---
id: shared-room-snapshot
title: "Shared `Room.snapshot` for ADR-037 (Python port, properly)"
status: draft
date: 2026-04-25
deciders: [Keith Avery]
related: [ADR-037, ADR-036, ADR-082]
implementation-status: draft
---

# Shared `Room.snapshot` for ADR-037

## Context

Multiplayer in the Python port (post ADR-082) currently lets each WebSocket
session hold its own copy of `GameSnapshot`. Mutations from one session do
not propagate to peers' in-memory snapshots; persistence is per-session and
last-writer-wins. Earlier in this playtest cycle that produced two
already-fixed bugs (multi-PC characters vanishing on disconnect, Tab 2
seeing the wrong PC as "self") and a defensive band-aid:
`WebSocketSessionHandler._merge_peer_state_into_snapshot`, which loads the
persisted snapshot before each save and pulls in peer-only entries.

The band-aid is holding for `characters` and `player_seats`, but per-session
divergence still exists for every other shared-world field
(`lore_established`, `npc_registry`, `world_history`, region/room state,
discovery state, RAG store, scenario state). Those fields haven't surfaced
as user-visible blockers yet, but they are real bugs waiting to land.

ADR-037 specifies the right model: per `(genre, world)` slug, a single
`SharedGameSession` mutated by all sessions, with per-player concerns
resolved on read. The Rust implementation (now retired) used
`Arc<RwLock<SharedGameSession>>` plus a `PlayerState` overlay map. The
Python port has not yet implemented this.

**Constraint that simplifies scope:** no multiplayer saved games exist on
disk. Multiplayer has never worked end-to-end before this playtest cycle.
That removes the migration concern entirely.

## Decision

Replace per-session `sd.snapshot` ownership with a single `GameSnapshot`
held on `SessionRoom` and shared by every WebSocket session bound to that
slug. The `_SessionData.snapshot` attribute keeps its name; after slug-
connect binding it is a Python reference to the room's snapshot, so all
existing reads and mutations transparently hit the canonical object.

The `_merge_peer_state_into_snapshot` band-aid is deleted in the same
change — it has no purpose once divergence is gone, and there are no MP
saves on disk that would benefit from its merge logic.

## Detailed Design

### `SessionRoom` additions

`sidequest-server/sidequest/server/session_room.py`

Two new fields, both protected by the existing `_lock`:

```python
_snapshot: GameSnapshot | None = None
_store: SqliteStore | None = None
```

Three new methods:

```python
def bind_world(
    self,
    *,
    snapshot: GameSnapshot,
    store: SqliteStore,
) -> None:
    """Bind the canonical snapshot for this room.

    Idempotent: a second call when ``_snapshot`` is already populated is a
    no-op. The first slug-connect on a room loads the persisted snapshot
    (or constructs a fresh one) and calls ``bind_world``; later connects
    consume the existing binding via ``snapshot`` / ``store`` properties.
    """

@property
def snapshot(self) -> GameSnapshot | None: ...

@property
def store(self) -> SqliteStore | None: ...

def save(self) -> None:
    """Save the canonical snapshot through the canonical store.

    Acquires ``_lock`` for the duration. Replaces every per-session
    ``sd.store.save(sd.snapshot)`` call site. No-op when the room has
    no snapshot bound (legacy / pre-bind paths must not crash on save).
    """

def close_store(self) -> None:
    """Close the canonical store. Idempotent. Called by RoomRegistry on
    last-disconnect teardown so the SQLite handle isn't leaked."""
```

Two reasons we keep the room lock at the file level rather than introducing
a separate `_snapshot_lock`:

1. ADR-036 sealed-letter pacing + the new TURN_STATUS gate already
   serialize narration turns per slug at the application layer. Mutation
   contention on the snapshot is structurally near-zero.
2. The existing `_lock` already protects connect/disconnect/seat. Reusing
   it keeps the locking model singular.

### `WebSocketSessionHandler` changes

`sidequest-server/sidequest/server/session_handler.py`

**Slug-connect bind path** (inside the existing slug-connect branch,
after `_room_registry.get_or_create(slug, mode=...)` returns the room):

```python
if room.snapshot is None:
    # First connect — this handler loads from store and binds.
    saved = store.load()
    if saved is not None:
        snapshot = saved.snapshot
    else:
        snapshot = GameSnapshot(
            genre_slug=row.genre_slug,
            world_slug=row.world_slug,
            location="Unknown",
        )
        store.init_session(row.genre_slug, row.world_slug)
    room.bind_world(snapshot=snapshot, store=store)

# Every connect: bind sd to the canonical room state.
sd.snapshot = room.snapshot
sd.store = room.store
```

**Save sites** — every existing `sd.store.save(sd.snapshot)` (or
`sd.store.save(snapshot)` where `snapshot is sd.snapshot`) becomes a call
to `self._room.save()`. Sites:

- Disconnect / cleanup save (~line 993–1001).
- Chargen-commit persist (~line 2514).
- Turn-end persist in `_execute_narration_turn` (~line 2862).
- UUID-rename-on-resume save (~line 1323).

The chargen-commit second-commit path that does
`sd.snapshot = existing_saved.snapshot` is removed — `sd.snapshot` is
already the room's canonical snapshot, so the second committer just
appends their character to it.

**Removed:** `_merge_peer_state_into_snapshot` and its three call sites
inside `_handle_player_action` cleanup, `_execute_narration_turn`, and
disconnect-save. Also removed: the imports / helper guards introduced
for it.

### `_SessionData` changes

`_SessionData.snapshot` and `_SessionData.store` remain typed as
`GameSnapshot` and `SqliteStore`. After slug-connect bind, they are
references to the room-level objects. This keeps the dispatch pipeline
verbatim — every existing line that reads `sd.snapshot.characters` or
mutates `sd.snapshot.npc_registry` still works without modification.

For paths that don't go through slug-connect (legacy non-slug connect,
some unit tests that construct `_SessionData` directly), behavior is
unchanged: each session has its own snapshot and store. There is no MP
on those paths.

### Solo path

Solo always runs as a one-occupant room. The shared-snapshot model is
mathematically identical to the per-session model when there is exactly
one session. No solo behavior changes.

### Concurrency

- Turns are serialized per slug by ADR-036 sealed-letter pacing + the
  pause-gate at line 2712–2729 + the new TURN_STATUS broadcast in
  `_handle_player_action`. Two sockets cannot run narration concurrently
  on the same slug.
- Mutations during a turn are not lock-protected at the snapshot field
  level — they don't need to be (single-writer-at-a-time, GIL covers
  individual list/dict ops).
- The room `_lock` only wraps `bind_world`, `save`, and `close_store` —
  the operations where two sockets can race (first-connect, two-disconnect-saves-overlapping).

### Compatibility

- **No saved MP games exist** (per Keith). This is the constraint that
  lets us delete the band-aid wholesale.
- **Solo saves** unaffected: solo's `player_seats` is empty or
  single-player; nothing diverges in the first place.
- **Legacy non-slug connect** unaffected: never enters the bind path,
  keeps per-session `_SessionData`.
- **Tests that mock `store` with `MagicMock`** — affected. The merge tests
  in `test_multiplayer_party_status.py` are deleted (5 tests). The
  resolver tests stay green (they don't touch save/store paths). New
  shared-room tests are added.

## Tests

Delete from `tests/server/test_multiplayer_party_status.py`:

- `test_merge_peer_state_pulls_peer_chars_and_seats_from_persisted`
- `test_merge_peer_state_local_wins_for_shared_character_names`
- `test_merge_peer_state_noop_for_solo`
- `test_merge_peer_state_noop_when_persisted_missing`
- `test_merge_peer_state_swallows_load_errors`
- `_saved_snapshot_with` helper (no other consumers)

Add to `tests/server/test_multiplayer_party_status.py`:

- `test_two_handlers_share_room_snapshot_after_bind` — handlerA and
  handlerB both bind to the same room; mutating
  `handlerA.session_data.snapshot.characters.append(...)` is observable
  via `handlerB.session_data.snapshot.characters`.
- `test_chargen_commit_visible_to_peer_handler_immediately` — handlerA
  has Laverne; handlerB does chargen-commit with Shirley; handlerA's
  `sd.snapshot.characters` and `sd.snapshot.player_seats` reflect both
  PCs without re-loading from store.
- `test_room_save_routes_through_canonical_store` — `room.save()`
  persists the canonical snapshot once; a fresh `room.snapshot` load on
  a new room produces the same data.
- `test_solo_path_unaffected_by_shared_room_model` — single-occupant
  room round-trips identically to the previous per-session behavior
  (regression guard).

Add to `tests/server/test_session_room.py` (new file or extend if it
exists):

- `test_bind_world_is_idempotent` — second `bind_world` call when
  snapshot is already bound is a no-op (same identity, no overwrite).
- `test_close_store_is_idempotent` — second close doesn't raise.
- `test_snapshot_property_returns_none_before_bind` — explicit
  guard so accessors return None before bind, never raise.

Existing wiring tests for `_resolve_self_character`, the chargen gate,
and TURN_STATUS broadcasts continue to pass unchanged.

## Files Touched

- `sidequest-server/sidequest/server/session_room.py` — fields +
  methods.
- `sidequest-server/sidequest/server/session_handler.py` — slug-connect
  bind, save site replacements, delete `_merge_peer_state_into_snapshot`.
- `sidequest-server/tests/server/test_multiplayer_party_status.py` —
  delete 5 merge tests, add 4 shared-room tests.
- `sidequest-server/tests/server/test_session_room.py` — extend or
  create with 3 binding tests.

No UI changes. No content changes. No daemon changes. Single subrepo,
single commit (or two if test deletion + new tests are split for
review clarity).

## Out of Scope

- **ADR-028 LLM rewrites** (charmed/blinded/deafened narration variants).
  Separate story.
- **Per-recipient narration filtering by region** (the deferred ping-pong
  entry that says "Each player's narrative pane shows the other player's
  narration too"). Separate story; the projection filter infrastructure
  already exists, the missing piece is wiring `_visibility.visible_to`
  on NarrationPayload at emit time.
- **`PlayerState` overlay struct** matching the retired Rust ADR-037
  shape. The Python `GameSnapshot` already mixes shared + per-player
  fields; per-player resolution happens by `player_id` on read via the
  existing `_resolve_self_character` helper. Adding a separate
  `PlayerState` is a refactor that doesn't earn its keep at current
  scale.

## Acceptance Criteria

1. Two `WebSocketSessionHandler` instances bound to the same room share
   a single `GameSnapshot` reference; mutations on one are observable on
   the other without any reload.
2. Every save site in `session_handler.py` routes through `room.save()`.
3. `_merge_peer_state_into_snapshot` and its 5 tests are deleted.
4. Solo behavior is unchanged. Existing solo / chargen / persistence
   tests stay green.
5. `tests/server/` + `tests/agents/` full sweep is green (current
   baseline: 736 passed, 2 skipped). Shared-room tests add ~7 net
   (delete 5, add 4 in party_status + 3 in session_room).
6. The two-tab playtest repro that produced "Multi-PC state does not
   survive disconnect" cannot reproduce: a fresh slug + Tab 1 commits
   Laverne + Tab 2 commits Shirley + close both tabs + reopen → both
   tabs resume their seated PC; neither re-enters chargen.
