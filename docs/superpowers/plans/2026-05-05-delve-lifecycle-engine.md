# Delve Lifecycle Engine — Sünden Hub Item 4a (Server-Side)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the server-side delve lifecycle that makes hub worlds playable: hub-mode connect (no immediate rejection), recruit/dismiss REST, `DUNGEON_SELECT` WS to start a delve from a chosen roster, materialize hirelings into `GameSnapshot.characters`, `RETREAT_TO_HAMLET` WS (and `player_dead` auto-trigger) to end a delve and commit stress + status back to the roster, append the Wall ledger, set the drift / wound flags, and `init_session()` the delve state for the next descent.

**Architecture:** New `active_delve_dungeon: str | None` discriminator on `GameSnapshot` separates *hub mode* (None — connect emits a HUB_VIEW frame, narration is suppressed, REST hub mutations are allowed) from *delve mode* (a dungeon slug — connect proceeds today's path with the dungeon's cartography/openings, narration runs, hub mutations are rejected). Dungeon selection mutates `WorldSave` (append wall, drift flag) and `GameSnapshot` (init_session reinit, fresh snapshot built with materialized roster + active_delve_dungeon set, location and openings sourced from `World.dungeons[dungeon]`). Delve end is the inverse. The narrator is **not** the source of truth for delve outcome in this plan — `RETREAT_TO_HAMLET` carries an explicit `outcome` (party fate) AND `wounded_boss` (boss-floor flag), both client-asserted; `player_dead` auto-fires `outcome=defeat, wounded_boss=False` (narrator-side wound detection is a item-4-followon). Outcome and wound are deliberately orthogonal so a TPK-after-wounding-the-boss is recordable as `(defeat, wounded_boss=True)` — see Sünden spec §"Wounded Sins" line 81: *"a successful boss delve flips a permanent flag"*. Per-character commit-back from the in-delve `Character` to the roster `Hireling` is by **id** (a new `hireling_id` field on `Character`), never by name — namegen has finite culture-corpus entropy and two hirelings can share a display name; matching by name is a silent-misattribution bug magnet that would surface as "Volga's stress kept resetting" and take Keith hours to track. Stress is *declared* on `Hireling` by item 2 but *not read or written* by this plan — item 3 owns numeric stress accrual, and a CLAUDE.md "no silent fallbacks" reading of `getattr(ch, "stress", h.stress)` would silently no-op pre-item-3 in a way that masks real bugs post-item-3.

**Tech Stack:** Python 3.12, pydantic v2, FastAPI, websockets, pytest.

**Date:** 2026-05-05
**Status:** Draft
**Repo:** sidequest-server (everything; no content or UI changes)
**Spec parent:** `docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md` §"Engine Surface" item 4 (the engine half — UI is item 4b)
**Sibling plans:**
- `docs/superpowers/plans/completed/2026-05-04-genre-loader-dungeon-recursion.md` — item 1 (loader recursion). MERGED. Provides `World.dungeons` and the connect-handler hub guard this plan **replaces** with a hub-view-emission path.
- `docs/superpowers/plans/2026-05-05-world-save-persistence-hub.md` — item 2 (world save persistence). PEER. Provides the `WorldSave` storage layer this plan reads from and writes to. **This plan must land after item 2.**
- `docs/superpowers/plans/2026-05-05-stress-field-hireling.md` — item 3, *to be authored*. Adds numeric stress-accrual mechanics that mutate `Hireling.stress`. This plan calls `Hireling.stress` in commit-back but does not change it numerically.
- `docs/superpowers/plans/2026-05-05-sunden-hub-ui.md` — item 4b, *to be authored*. The UI plan that consumes the protocol surfaces this plan introduces.
- `docs/superpowers/plans/2026-05-05-narrator-zones-drift-wound-wall.md` — items 5/6/7, *to be authored*. Reads the drift_profile / wound_profile / Wall fields populated by this plan.
- `docs/superpowers/plans/2026-05-05-deleted-world-slug-test-sweep.md` — *to be authored*. The 44-test repair plan referenced by the loader-recursion plan. Becomes drafty after **this** plan ships, because the repair shape is `world="caverns_three_sins"` + `dungeon=X` via `DUNGEON_SELECT` — the API shape this plan defines.

---

## Why

Item 1 (loader) gave us a hub world that loads. Item 2 (world save) gave us a place to store roster / Wall / drift / wound. Neither plan wired a code path that *enters or exits* a delve. Today, connecting to `caverns_three_sins` returns a typed error (`hub_world_requires_dungeon_selection`) — by design, because letting it limp through with a missing cartography would mask the real failure. This plan replaces the typed error with a real entry path: the connect emits a `HUB_VIEW`, the client's hub UI (item 4b) lets the player recruit and pick a dungeon, and a `DUNGEON_SELECT` message starts the delve. Without this plan, none of the Sünden content can be played. With this plan plus item 4b's UI, Keith can run a full Hamlet → Grimvault → return loop end-to-end.

This plan is also the unblocker for the 44-test sweep referenced by the loader-recursion plan: those tests hardcode leaf world slugs (`grimvault`, `horden`, `mawdeep`, etc.) that no longer exist. The right replacement target is `caverns_three_sins` plus `DUNGEON_SELECT(grimvault, [...])` — an API shape only this plan can provide. The test-sweep plan can be drafted the moment this plan's protocol surface stabilizes.

## Scope

This plan ends when:
- A WS connect into a hub world (`caverns_three_sins`) **succeeds**, replaces today's typed error, and emits a single `HUB_VIEW` frame carrying the WorldSave + dungeon list.
- `POST /api/games/{slug}/hub/recruit` adds a `Hireling` to the roster using `archetype_funnels.yaml` to roll the archetype (and `sin_origin` when present), names the hireling via the existing namegen path, persists via `save_world_save()`. Returns the new Hireling JSON.
- `DELETE /api/games/{slug}/hub/roster/{hireling_id}` sets `Hireling.status = "dead"` when the hireling died on-delve, or removes the row when the player explicitly dismisses an alive one. Distinguishes the two via a query param `?reason=dismiss|died_offscreen` (default `dismiss`; `dismiss` is "alive but you're letting them go," `died_offscreen` is for legacy/cleanup edge cases — actual on-delve death goes through commit-back, not this endpoint).
- `DUNGEON_SELECT` WS message validates the chosen dungeon + party (1..6 hirelings, all `status=active`, all in the roster), materializes the party into `GameSnapshot.characters` with stress copied, sets `active_delve_dungeon` to the dungeon slug, loads the dungeon's `cartography` + `openings` + `rooms` (from `World.dungeons[dungeon]`), runs the same chargen-or-skip path leaf-world connects use today, emits the opening narration. Rejected if a delve is already active or any validation fails — typed error frame, no silent fallback.
- `RETREAT_TO_HAMLET` WS message accepts `outcome ∈ {retreat, victory}` AND `wounded_boss: bool` (orthogonal), runs commit-back (copy alive/dead status from `GameSnapshot.characters` to `WorldSave.roster` *by hireling_id, never by name*), appends a `WallEntry` carrying both fields, sets `latest_delve_sin = dungeon.config.sin` (the drift flag), sets `dungeon_wounds[dungeon] = True` whenever `wounded_boss=True` regardless of outcome, increments `delve_count`, calls `store.init_session(...)` to clear delve state, emits a `HUB_VIEW`.
- `GameSnapshot.player_dead` transitioning to True auto-triggers the same delve-end with `outcome="defeat", wounded_boss=False`. Auto-fired in the existing dispatch path immediately after the snapshot mutation that set the flag. Narrator-driven wound detection (so a TPK-after-wound automatically records `wounded_boss=True`) is item-4-followon — the honest gap is documented.
- Stress is declared on `Hireling` (item 2) but **not read or written** by this plan. Item 3 owns numeric stress accrual.
- `tests/server/test_delve_lifecycle.py` is green (the new file). `tests/handlers/test_connect.py` (existing) remains green for the leaf-world cases and gains coverage for the hub-view path.
- Leaf worlds are bit-identical: a connect to `space_opera/coyote_star` runs through today's code path. Verified by an existing-test rerun with the diff being a no-op.

**Explicitly NOT a goal:**
- Narrator-driven outcome detection (a `delve_outcome` sidecar on `NarrationTurnResult`). Manual via `RETREAT_TO_HAMLET.outcome`. Item 4-followon.
- Currency cost on recruit. Spec is silent. Recruit is free in this plan; pricing is gameplay tuning.
- Stress accrual numeric mechanics. Item 3. This plan reads/writes `Hireling.stress` in commit-back but does not change values.
- Stress-relief services (Confessional / Workhouse / Masquerade). Item 4-followon. Their REST endpoints can mirror the recruit/dismiss shape this plan establishes.
- The Sünden hub UI. Item 4b.
- Multi-character / multiplayer-shared roster delve. Solo-only in this plan. The roster is per-slug already (item 2), so multiplayer just inherits the storage; the *party-during-delve* coordination across multiple WS clients in one delve is item 4-followon if anyone asks.
- A "delve in progress, you can re-attach mid-delve" recovery flow distinct from today's resume. Today's resume already works for active delves (the snapshot has `active_delve_dungeon` set, so connect proceeds normally). No new resume code.

**Out of scope (separate, deliberately):**
- Save migration. Saves predating this plan have `active_delve_dungeon` absent → defaults to `None` → connect drops them into hub mode → user picks a dungeon to start a fresh delve. Their old per-delve snapshot state is *discarded* by the `init_session()` that fires on first DUNGEON_SELECT — same throwaway treatment as `feedback_legacy_saves`. Pre-Sünden saves of `caverns_and_claudes` already pointed at deleted leaf worlds (`grimvault`/`horden`/`mawdeep`) and are unloadable; new `caverns_three_sins` saves are the migration story.
- 44-test sweep. Becomes drafty once this plan ships; explicitly held back per the loader-recursion plan's follow-on note.

## Design

### 1. State machine

```
              ┌─────────────────┐
   connect    │   HUB MODE      │   DUNGEON_SELECT(d, party)
   (None) ──▶ │  active_delve_  │ ───────────────────────────▶  ┌────────────┐
              │  dungeon=None   │                              │ DELVE MODE │
              │  hub mutations  │ ◀──────────────────────────  │ active_d=d │
              │  allowed        │   RETREAT_TO_HAMLET(outcome) │ narration  │
              └─────────────────┘   or player_dead → defeat     │ runs       │
                                                               └────────────┘
```

`active_delve_dungeon` is the single discriminator. Every gate is `is_hub_world(genre_pack, world_slug) AND snapshot.active_delve_dungeon is None`.

### 2. New field on `GameSnapshot`

```python
# Sünden engine plan item 4a — delve lifecycle discriminator.
# None ⇒ hub mode (connect emits HUB_VIEW, narration suppressed, hub
# REST mutations allowed). Non-None ⇒ delve mode (the dungeon slug
# being delved; connect proceeds with that dungeon's cartography/openings/
# rooms, narration runs, hub REST mutations are rejected).
# Always None on a non-hub world (loader item 1's `World.dungeons` is
# empty there). Lazy-initialized: legacy saves without this field
# default to None and drop into hub mode on next connect.
active_delve_dungeon: str | None = None
```

Add to `sidequest/game/session.py` `GameSnapshot` next to `player_dead`. `model_config = {"extra": "ignore"}` already handles legacy-save forward-compat.

### 3. Protocol — new wire types

#### 3.1 New `MessageType` values

In `sidequest/protocol/enums.py` `MessageType`:

```python
HUB_VIEW = "HUB_VIEW"                  # outbound; payload below
DUNGEON_SELECT = "DUNGEON_SELECT"      # inbound
RETREAT_TO_HAMLET = "RETREAT_TO_HAMLET"  # inbound
```

#### 3.2 Pydantic models in `sidequest/protocol/messages.py`

```python
class AvailableDungeon(BaseModel):
    """Enriched dungeon descriptor in HUB_VIEW.

    Shipping {slug, sin, wounded} together eliminates the need for a
    client-side SIN_BY_DUNGEON map. The sin is resolved server-side from
    Dungeon.config.sin (loader item 1); wounded is read from
    WorldSave.dungeon_wounds. Future hub-world genre packs (heavy_metal,
    mutant_wasteland, etc.) get sin-labeled UI for free.
    """
    model_config = {"extra": "ignore"}

    slug: str                          # dungeon slug ("grimvault" | ...)
    sin: str                           # ("pride" | "greed" | "gluttony" | future)
    wounded: bool


class HubViewPayload(BaseModel):
    """Outbound — sent on hub-mode connect and on every delve-end."""
    model_config = {"extra": "ignore"}

    slug: str
    genre_slug: str
    world_slug: str
    available_dungeons: list[AvailableDungeon]  # sorted by slug
    world_save: WorldSave              # full hub state — small enough; UI needs all of it


class HubViewMessage(BaseModel):
    type: Literal[MessageType.HUB_VIEW] = MessageType.HUB_VIEW
    payload: HubViewPayload


class DungeonSelectPayload(BaseModel):
    """Inbound — start a delve."""
    model_config = {"extra": "forbid"}  # tight contract, reject unknowns

    dungeon: str                       # slug; must be in World.dungeons
    party_hireling_ids: list[str]      # 1..6, all status=active, all in roster


class DungeonSelectMessage(BaseModel):
    type: Literal[MessageType.DUNGEON_SELECT] = MessageType.DUNGEON_SELECT
    payload: DungeonSelectPayload


# Party fate. Three orthogonal-to-wound outcomes. "defeat" is server-only
# (player_dead auto-trigger) — the inbound wire type intentionally
# excludes it so a client cannot claim defeat, and defeat-with-wound is
# only achievable via the auto-trigger path which writes wounded_boss=False
# until item-4-followon adds narrator-driven wound detection.
DelveOutcome = Literal["retreat", "victory"]


class RetreatToHamletPayload(BaseModel):
    """Inbound — end a delve voluntarily.

    ``outcome`` and ``wounded_boss`` are deliberately orthogonal so that
    "we wounded the boss but two of us died" is recordable as
    ``(retreat, wounded_boss=True)`` rather than being forced into a
    single conflated literal. Per spec §"Wounded Sins" line 81:
    *"A successful boss delve flips a permanent flag on that dungeon"* —
    the flag is the wound, separate from whether the party walked or
    died on the way out.
    """
    model_config = {"extra": "forbid"}
    outcome: DelveOutcome
    wounded_boss: bool = False


class RetreatToHamletMessage(BaseModel):
    type: Literal[MessageType.RETREAT_TO_HAMLET] = MessageType.RETREAT_TO_HAMLET
    payload: RetreatToHamletPayload
```

Register the new types in whatever dispatch table sits in `sidequest/protocol/dispatch.py` (verify in task 4).

### 4. New module — `sidequest/game/delve_lifecycle.py`

A pure-functions module. No I/O. Tests can hit it without spinning up a server.

```python
"""Delve lifecycle — start, end, materialize, commit-back.

Sünden engine plan item 4a. The verbs are the only public surface:

- `is_hub_world(world: World) -> bool` — single source of truth for the
  hub-vs-leaf check (encapsulates `bool(world.dungeons)`).
- `materialize_party(roster, party_ids, *, world_slug, dungeon) -> list[Character]`
  — copy identity into Character shapes (with ``hireling_id`` linkage);
  raise on missing/dead ids. Does NOT carry stress (item 3 owns stress).
- `commit_back(snapshot, world_save) -> WorldSave` — pure: takes the
  delve-end snapshot, returns the WorldSave with status updated.
  Match is by ``Character.hireling_id`` → ``Hireling.id``. Does NOT
  touch stress (item 3). Does not call save_world_save; caller does.
- `apply_delve_end(world_save, *, dungeon, dungeon_obj, outcome,
  wounded_boss, party_hireling_ids, snapshot) -> WorldSave` — the full
  delve-end business rules (commit-back + Wall append + drift flag +
  wound flag (when ``wounded_boss=True``) + delve_count++). Returns
  updated WorldSave; caller persists.
"""

def is_hub_world(world: World) -> bool:
    return bool(world.dungeons)


def build_available_dungeons(
    world: World, world_save: WorldSave,
) -> list[AvailableDungeon]:
    """Compose the enriched dungeon list shipped in HUB_VIEW.

    Server-side resolution of {slug, sin, wounded} so the client never
    needs a hardcoded SIN_BY_DUNGEON map. Sin comes from the dungeon's
    Dungeon.config.sin (loader item 1), wounded comes from world_save.
    Sorted by slug for deterministic UI order.
    """
    return [
        AvailableDungeon(
            slug=dungeon_slug,
            sin=world.dungeons[dungeon_slug].config.sin,
            wounded=world_save.dungeon_wounds.get(dungeon_slug, False),
        )
        for dungeon_slug in sorted(world.dungeons)
    ]


def materialize_party(
    roster: list[Hireling],
    party_ids: list[str],
    *,
    world_slug: str,
    dungeon: Dungeon,
) -> list[Character]:
    """Materialize a delve party from the roster. Raises ValueError on
    invalid input — caller turns that into a typed wire error.

    Validation order matters (test-checked):
      1. party non-empty (1..6)
      2. all ids exist in roster (collect the missing list, error names them all)
      3. all are status=active (collect the inactive list, error names them all)
      4. no duplicates in party_ids
    """
    if not (1 <= len(party_ids) <= 6):
        raise ValueError(f"party size must be 1..6, got {len(party_ids)}")
    if len(set(party_ids)) != len(party_ids):
        raise ValueError(f"party_hireling_ids contains duplicates: {party_ids}")
    by_id = {h.id: h for h in roster}
    missing = [pid for pid in party_ids if pid not in by_id]
    if missing:
        raise ValueError(f"hirelings not in roster: {missing}")
    inactive = [
        pid for pid in party_ids
        if by_id[pid].status != "active"
    ]
    if inactive:
        raise ValueError(f"hirelings not active: {inactive}")

    chars: list[Character] = []
    for pid in party_ids:
        h = by_id[pid]
        # Build a Character matching the unified character model (ADR-007).
        # The narrative-only fields (name, archetype, description) come
        # from the Hireling. Mechanical fields (chassis bindings, magic
        # state) start fresh per delve and are wired in chargen as today.
        chars.append(_character_from_hireling(h, world_slug=world_slug))
    return chars


def commit_back(
    snapshot: GameSnapshot,
    world_save: WorldSave,
) -> WorldSave:
    """Pure: copy alive/dead status from delve characters back to roster.

    Match is by ``Character.hireling_id`` → ``Hireling.id``, never by name.
    Namegen has finite culture-corpus entropy and two hirelings can share
    a display name; matching by id is the only correct attribution.
    Characters with no ``hireling_id`` (e.g. legacy chargen-spawned PCs
    from non-hub flows) are ignored.

    Stress is NOT touched here. The field is declared by item 2 for
    storage shape; item 3 owns numeric stress accrual (per-encounter
    deltas, threshold effects). Reading ``Character.stress`` here pre-
    item-3 would silent-no-op (CLAUDE.md "no silent fallbacks") and
    once item 3 lands the absence of a write here is a known unwiring
    point for that plan to fill.
    """
    by_id = {h.id: h for h in world_save.roster}
    new_roster = list(world_save.roster)
    for ch in snapshot.characters:
        hid = getattr(ch, "hireling_id", None)
        if hid is None:
            continue  # legacy PC, not roster-tracked
        h = by_id.get(hid)
        if h is None:
            # Hireling was dismissed mid-delve (impossible by current REST
            # gating, but defended here). Loud log, not silent skip.
            logger.warning(
                "commit_back: character %r references hireling_id=%r "
                "absent from roster; status update skipped",
                ch.core.name, hid,
            )
            continue
        idx = new_roster.index(h)
        new_status = "dead" if ch.is_dead else h.status
        new_roster[idx] = h.model_copy(update={"status": new_status})
    return world_save.model_copy(update={"roster": new_roster})


def apply_delve_end(
    world_save: WorldSave,
    *,
    dungeon_slug: str,
    dungeon_sin: str,                       # from Dungeon.config.sin
    outcome: Literal["retreat", "victory", "defeat"],
    wounded_boss: bool,
    party_hireling_ids: list[str],
    snapshot: GameSnapshot,
    timestamp: datetime,
) -> WorldSave:
    """Apply all delve-end mutations to WorldSave and return the new value.

    ``outcome`` is party fate; ``wounded_boss`` is the orthogonal flag
    (spec §"Wounded Sins"). A wound flips ``dungeon_wounds[slug]=True``
    regardless of outcome — TPK-after-wound is a real recordable event.
    Once a dungeon is wounded, it stays wounded (spec line 89: "A dungeon
    can only be wounded once in this design").
    """
    ws = commit_back(snapshot, world_save)
    new_count = ws.delve_count + 1
    new_wall = ws.wall + [WallEntry(
        delve_number=new_count,
        sin=dungeon_sin,
        dungeon=dungeon_slug,
        party_hireling_ids=party_hireling_ids,
        outcome=outcome,
        wounded_boss=wounded_boss,
        timestamp=timestamp,
    )]
    new_wounds = dict(ws.dungeon_wounds)
    if wounded_boss:
        new_wounds[dungeon_slug] = True
    return ws.model_copy(update={
        "wall": new_wall,
        "dungeon_wounds": new_wounds,
        "latest_delve_sin": dungeon_sin,
        "delve_count": new_count,
    })
```

**`Character.hireling_id` / `Character.is_dead`:**

This plan adds **two** fields to `Character`:

1. `hireling_id: str | None = None` — populated by `_character_from_hireling`; commit-back's only correct match key. Task 5 step 1 verifies the field's absence and adds it if missing. `None` for legacy chargen-spawned PCs from non-hub flows.
2. `is_dead: bool = False` (only if not already present on `Character`) — per-character death sibling to the existing party-level `GameSnapshot.player_dead`. Required so commit-back can attribute death correctly when one hireling dies but the party retreats. Task 5 step 1 verifies presence.

Item 3 (stress mechanics) will later add `Character.stress: int = 0`. This plan does NOT touch stress: not on `Character`, not in `materialize_party`, not in `commit_back`. The Hireling-side `stress` field stays exactly as item 2 left it for the duration of this plan. Item 3's plan will introduce the stress propagation at both ends in one coherent change.

### 5. `_character_from_hireling` — the actual materialization

This is the most uncertain piece because `Character` is the unified model (ADR-007) with chassis / magic_state / narrative fields. Hirelings are slim. Materialization must:
- Carry `name`, `archetype` from Hireling.
- Set `Character.hireling_id = hireling.id` so commit-back can attribute back.
- Default-initialize all the rest using the existing chargen path so the narrator gets a complete Character to work with.

**Implementation strategy:** verify via `grep -n 'class Character' sidequest-server/sidequest/game/character.py` before writing. The chargen `CharacterBuilder` is the existing way to build a Character; if its constructor accepts a "from this archetype + this name" shape, reuse it. If it only works through the player chargen scenes, write a thin `Character(core=CharacterCore(name=h.name, archetype=h.archetype, ...), hireling_id=h.id)` constructor and rely on `model_config = {"extra": "ignore"}` for whatever fields are missing.

Test-driven discovery: write the test first (`test_materialize_party_carries_hireling_id_and_name`), then implement to pass it. Edge cases that must be tested explicitly: missing id, dead hireling, duplicate id, party-size 0, party-size 7. All raise.

### 6. Connect handler — replace hub-rejection with hub-view emission

In `sidequest/handlers/connect.py:307-331` the existing hub-world guard returns a typed error. Replace it with:

```python
_world_obj = genre_pack.worlds.get(row.world_slug)
is_hub = _world_obj is not None and is_hub_world(_world_obj)

if is_hub and (
    saved is None or saved.snapshot.active_delve_dungeon is None
):
    # Hub mode. Don't load openings/cartography (they don't exist at
    # the world level on a hub world — loader item 1). Don't run
    # chargen. Don't start narration. Return a HUB_VIEW frame and
    # leave the room in hub-mode (the next inbound message must be
    # DUNGEON_SELECT or a hub REST mutation; the WS handler enforces
    # this).
    world_save = store.load_world_save()
    _watcher_publish(
        "session.hub_mode_entered",
        {
            "slug": slug,
            "genre": row.genre_slug,
            "world": row.world_slug,
            "roster_size": len(world_save.roster),
            "delve_count": world_save.delve_count,
        },
        component="session",
    )
    return [
        _hub_view_msg(
            slug=slug,
            genre_slug=row.genre_slug,
            world_slug=row.world_slug,
            available_dungeons=build_available_dungeons(_world_obj, world_save),
            world_save=world_save,
        ),
    ]
# else: leaf world OR mid-delve resume → fall through to existing path
```

The existing `saved` load (line 335) needs to move *above* this branch; restructure so the snapshot existence check feeds the hub-vs-resume decision. The `init_session()` call on the fresh-snapshot path stays where it is (line 527) — applies only to leaf-world fresh sessions and to delve-mode-fresh sessions (DUNGEON_SELECT triggers it explicitly).

**Test:** `tests/handlers/test_connect.py` — add a test that hub-mode connect emits exactly one HUB_VIEW, no NARRATION, no OPENING. Add a complementary test that mid-delve resume on a hub world (snapshot has `active_delve_dungeon="grimvault"`) skips the hub branch and proceeds normally.

### 7. New WS handler — `DUNGEON_SELECT`

In `sidequest/handlers/` add `dungeon_select.py`:

```python
"""DUNGEON_SELECT handler — start a delve from the hub.

Sünden engine plan item 4a. Inbound only. Pre-condition: snapshot is
in hub mode (active_delve_dungeon is None). Validates dungeon exists,
party is well-formed, materializes the party, sets active_delve_dungeon,
swaps cartography/openings to the dungeon's, then runs the same
opening-narration emission the leaf-world fresh-session path does.
"""

async def handle_dungeon_select(
    msg: DungeonSelectMessage,
    *,
    room: SessionRoom,
    session: ServerSession,
    slug: str,
) -> list[Message]:
    snapshot = room.snapshot
    if snapshot is None:
        return [_error_msg("no active session", code="no_session")]
    if snapshot.active_delve_dungeon is not None:
        return [_error_msg(
            f"already delving in {snapshot.active_delve_dungeon!r}; "
            "send RETREAT_TO_HAMLET first",
            code="delve_already_active",
        )]

    loader = GenreLoader(search_paths=session._search_paths)
    pack = loader.load(snapshot.genre_slug)
    world = pack.worlds.get(snapshot.world_slug)
    if world is None or not is_hub_world(world):
        return [_error_msg(
            f"world {snapshot.world_slug!r} is not a hub world",
            code="not_a_hub_world",
        )]

    dungeon = world.dungeons.get(msg.payload.dungeon)
    if dungeon is None:
        return [_error_msg(
            f"dungeon {msg.payload.dungeon!r} not in {sorted(world.dungeons)}",
            code="unknown_dungeon",
        )]

    store = room.store
    if store is None:
        return [_error_msg("no store bound", code="no_store")]
    world_save = store.load_world_save()

    try:
        party = materialize_party(
            roster=world_save.roster,
            party_ids=msg.payload.party_hireling_ids,
            world_slug=snapshot.world_slug,
            dungeon=dungeon,
        )
    except ValueError as exc:
        return [_error_msg(str(exc), code="invalid_party")]

    # Re-init the per-delve slot (clears narrative_log, events,
    # game_state, etc; world_save survives — see item 2 plan §3).
    store.init_session(snapshot.genre_slug, snapshot.world_slug)

    new_snapshot = GameSnapshot(
        genre_slug=snapshot.genre_slug,
        world_slug=snapshot.world_slug,
        active_delve_dungeon=msg.payload.dungeon,
        characters=party,
        location=_pick_opening_location(dungeon),  # from openings.yaml
    )
    room.bind_world(snapshot=new_snapshot, store=store, world_dir=...)

    _watcher_publish(
        "session.delve_started",
        {
            "slug": slug,
            "dungeon": msg.payload.dungeon,
            "party_size": len(party),
            "party_hireling_ids": msg.payload.party_hireling_ids,
        },
        component="session",
    )

    # Run the same opening-narration emission used by the fresh-session
    # leaf-world path. Factored out from connect.py during this plan
    # (task 6) so both call sites share one implementation.
    return await emit_opening_narration_for(new_snapshot, pack, dungeon, room=room)
```

Several names above (`_pick_opening_location`, `emit_opening_narration_for`, the `_search_paths` private) need verification against the actual codebase. Each task that uses one calls it out explicitly so the implementer doesn't paper over a missing dependency.

### 8. New WS handler — `RETREAT_TO_HAMLET`

```python
async def handle_retreat_to_hamlet(
    msg: RetreatToHamletMessage,
    *,
    room: SessionRoom,
    slug: str,
) -> list[Message]:
    snapshot = room.snapshot
    if snapshot is None or snapshot.active_delve_dungeon is None:
        return [_error_msg(
            "not currently in a delve",
            code="not_in_delve",
        )]
    return await _end_delve(
        room=room, slug=slug,
        outcome=msg.payload.outcome,
    )
```

Internal helper `_end_delve` is the shared entry point for both `RETREAT_TO_HAMLET` and the `player_dead` auto-trigger (§9). It computes the new WorldSave via `apply_delve_end`, persists it, calls `store.init_session(...)`, builds a fresh hub-mode snapshot, rebinds the room, and emits a HUB_VIEW.

### 9. `player_dead` auto-trigger — server-side

Find every place `snapshot.player_dead` transitions from False to True. The cleanest gate is `_apply_narration_result_to_snapshot` (`narration_apply.py:981`) which is the single funnel for snapshot mutations driven by narrator output. After it returns, the dispatch caller checks the `player_dead` transition; on a positive edge AND `active_delve_dungeon is not None`, fire the same `_end_delve(outcome="defeat")` path.

This is one new check in the dispatch caller (probably `websocket_session_handler.py` post-narration-apply), guarded by:

```python
if (
    not prev_player_dead
    and snapshot.player_dead
    and snapshot.active_delve_dungeon is not None
):
    msgs.extend(await _end_delve(room=room, slug=slug, outcome="defeat"))
```

`prev_player_dead` is captured before the apply call; the existing dispatch already does similar before/after diffing for other fields (verify in task 9; if it doesn't, add the capture inline — small change).

### 10. Hub REST — recruit + dismiss

Add to `sidequest/server/rest.py`:

```python
class RecruitRequest(BaseModel):
    model_config = {"extra": "forbid"}
    # Empty — recruit rolls archetype from archetype_funnels.yaml; if a
    # caller wants to choose, that's a future enhancement (gameplay
    # tuning, item 4-followon).


@router.post("/api/games/{slug}/hub/recruit")
async def recruit_hireling(
    slug: str, _req: RecruitRequest, request: Request,
) -> dict:
    """Roll a fresh hireling and add them to the roster.

    Hub-mode only — rejects with 409 ``not_in_hub_mode`` if a delve is
    active. Future work (item 4-followon) may add a currency cost; for
    now recruit is free.
    """
    save_dir: Path = request.app.state.save_dir
    db = db_path_for_slug(save_dir, slug)
    if not db.exists():
        raise HTTPException(status_code=404, detail=f"no game with slug {slug}")
    store = SqliteStore(db)
    store.initialize()
    row = get_game(store, slug)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no game with slug {slug}")

    search_paths = getattr(
        request.app.state, "genre_pack_search_paths",
        DEFAULT_GENRE_PACK_SEARCH_PATHS,
    )
    pack = load_genre_pack_cached(row.genre_slug, search_paths=search_paths)
    world = pack.worlds.get(row.world_slug)
    if world is None or not is_hub_world(world):
        raise HTTPException(status_code=409, detail={
            "code": "not_a_hub_world",
            "world_slug": row.world_slug,
        })

    # Refuse hub mutations during a live delve — read snapshot via store.
    saved = store.load()
    if saved is not None and saved.snapshot.active_delve_dungeon is not None:
        raise HTTPException(status_code=409, detail={
            "code": "delve_in_progress",
            "active_dungeon": saved.snapshot.active_delve_dungeon,
        })

    world_save = store.load_world_save()
    new_hireling = _roll_hireling_from_funnels(
        pack=pack, world=world, existing_ids={h.id for h in world_save.roster},
    )
    new_world_save = world_save.model_copy(update={
        "roster": world_save.roster + [new_hireling],
    })
    store.save_world_save(new_world_save)
    return new_hireling.model_dump(mode="json")


@router.delete("/api/games/{slug}/hub/roster/{hireling_id}")
async def dismiss_hireling(
    slug: str, hireling_id: str, request: Request,
    reason: str = "dismiss",
) -> dict:
    """Remove a hireling from the roster (default ``dismiss``).

    ``reason=dismiss`` removes the row entirely (player chooses to let
    them go). ``reason=died_offscreen`` flips ``status='dead'`` and
    keeps the row (Wall references remain valid). On-delve death is
    handled by commit-back and never goes through this endpoint.
    """
    if reason not in {"dismiss", "died_offscreen"}:
        raise HTTPException(status_code=400, detail={
            "code": "invalid_reason",
            "allowed": ["dismiss", "died_offscreen"],
        })
    # ... same hub-mode validation as recruit ...
    world_save = store.load_world_save()
    by_id = {h.id: h for h in world_save.roster}
    if hireling_id not in by_id:
        raise HTTPException(status_code=404, detail={
            "code": "hireling_not_found",
            "hireling_id": hireling_id,
        })
    if reason == "dismiss":
        new_roster = [h for h in world_save.roster if h.id != hireling_id]
    else:
        new_roster = [
            h.model_copy(update={"status": "dead"}) if h.id == hireling_id else h
            for h in world_save.roster
        ]
    new_world_save = world_save.model_copy(update={"roster": new_roster})
    store.save_world_save(new_world_save)
    return {"removed": hireling_id, "reason": reason}
```

`_roll_hireling_from_funnels` takes the pack + world + a set of existing ids (for collision avoidance) and returns a fresh `Hireling`. Implementation: read `world.archetype_funnels`, pick a row weighted by the funnel weights, generate a name via the existing namegen (task 11 verifies the entry point), construct a slug-shaped id like `f"{archetype}_{secrets.token_hex(4)}"` collision-checked against `existing_ids`. The id MUST satisfy `Hireling.id`'s pattern `^[a-z][a-z0-9_]+$` (item 2) — archetype slugs are lowercase per existing genre packs, and `secrets.token_hex(4)` produces lowercase hex, so the format `prig_a3f1c2d4` is conformant. A pydantic validation error from the constructor at this point is a code bug (archetype slug not lowercase) — fail loud, do not normalize. The `sin_origin` field on `ArchetypeFunnel` (added in the loader plan's Sünden merge) is propagated into `Hireling.notes` as `f"sin_origin: {sin}"` — narrator-readable but mechanically inert in this plan.

### 11. Telemetry

Per CLAUDE.md "Every backend fix that touches a subsystem MUST add OTEL watcher events": this plan adds five spans, one per state transition:

- `session.hub_mode_entered` — hub-mode connect (§6).
- `session.delve_started` — DUNGEON_SELECT success (§7).
- `session.delve_ended` — `_end_delve` invocation (§8/§9). Carries `{slug, dungeon, outcome, party_size, delve_count_after}`.
- `session.hireling_recruited` — recruit endpoint success (§10).
- `session.hireling_dismissed` — dismiss endpoint success (§10).

Span constants live in `sidequest/telemetry/spans/session.py` next to the existing `SPAN_SESSION_SLOT_REINITIALIZED`. The watcher events go through the existing `watcher_publish` so the GM panel sees them on the live timeline — that's how Sebastien (mechanics-first player; rules + OTEL are a feature per CLAUDE.md) verifies the engine actually engaged.

## Tasks

### Task 1: `active_delve_dungeon` field on `GameSnapshot`

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py`
- Test: `sidequest-server/tests/game/test_session.py` (existing; add a test)

- [ ] **Step 1: Write failing test**

```python
def test_game_snapshot_active_delve_dungeon_defaults_none():
    snap = GameSnapshot(genre_slug="caverns_and_claudes",
                        world_slug="caverns_three_sins")
    assert snap.active_delve_dungeon is None


def test_game_snapshot_active_delve_dungeon_round_trips():
    snap = GameSnapshot(
        genre_slug="caverns_and_claudes",
        world_slug="caverns_three_sins",
        active_delve_dungeon="grimvault",
    )
    raw = snap.model_dump_json()
    snap2 = GameSnapshot.model_validate_json(raw)
    assert snap2.active_delve_dungeon == "grimvault"


def test_game_snapshot_legacy_save_no_active_delve_field():
    """A pre-this-plan save JSON has no active_delve_dungeon. Loading
    must default it to None, not raise."""
    raw = '{"genre_slug": "x", "world_slug": "y"}'
    snap = GameSnapshot.model_validate_json(raw)
    assert snap.active_delve_dungeon is None
```

- [ ] **Step 2: Run; expect failure on the round-trip test (field doesn't exist)**

- [ ] **Step 3: Add the field**

In `sidequest/game/session.py` `GameSnapshot`, add the field next to `player_dead` exactly as specified in §2.

- [ ] **Step 4: Run; expect 3 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/session.py sidequest-server/tests/game/test_session.py
git commit -m "feat(snapshot): active_delve_dungeon field (Sünden engine plan item 4a)"
```

### Task 2: Protocol — `MessageType` enums

**Files:**
- Modify: `sidequest-server/sidequest/protocol/enums.py`
- Test: `sidequest-server/tests/protocol/test_enums.py` (existing or new)

- [ ] **Step 1: Write failing test**

```python
def test_new_message_types_present():
    assert MessageType.HUB_VIEW.value == "HUB_VIEW"
    assert MessageType.DUNGEON_SELECT.value == "DUNGEON_SELECT"
    assert MessageType.RETREAT_TO_HAMLET.value == "RETREAT_TO_HAMLET"
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Add the three enum values to `MessageType`**

Append after `ORBITAL_CHART` (end of the existing list).

- [ ] **Step 4: Run; expect pass**

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/protocol/enums.py sidequest-server/tests/protocol/test_enums.py
git commit -m "feat(protocol): HUB_VIEW / DUNGEON_SELECT / RETREAT_TO_HAMLET enums"
```

### Task 3: Protocol — payload models

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Test: `sidequest-server/tests/protocol/test_messages.py` (existing)

- [ ] **Step 1: Write failing tests**

```python
from sidequest.protocol.messages import (
    AvailableDungeon,
    DungeonSelectPayload,
    HubViewPayload,
    RetreatToHamletPayload,
)
from sidequest.game.world_save import WorldSave


def test_hub_view_payload_round_trips():
    p = HubViewPayload(
        slug="x", genre_slug="caverns_and_claudes",
        world_slug="caverns_three_sins",
        available_dungeons=[
            AvailableDungeon(slug="grimvault", sin="pride", wounded=False),
            AvailableDungeon(slug="horden", sin="greed", wounded=False),
            AvailableDungeon(slug="mawdeep", sin="gluttony", wounded=True),
        ],
        world_save=WorldSave(),
    )
    raw = p.model_dump_json()
    p2 = HubViewPayload.model_validate_json(raw)
    assert [d.slug for d in p2.available_dungeons] == \
        ["grimvault", "horden", "mawdeep"]
    assert {d.slug: d.sin for d in p2.available_dungeons} == \
        {"grimvault": "pride", "horden": "greed", "mawdeep": "gluttony"}
    assert p2.available_dungeons[2].wounded is True
    assert p2.world_save.delve_count == 0


def test_dungeon_select_payload_rejects_unknown_keys():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        DungeonSelectPayload(
            dungeon="grimvault",
            party_hireling_ids=["a"],
            extra_field="oops",  # type: ignore[call-arg]
        )


def test_retreat_outcome_validates_literal_and_excludes_defeat():
    """Defeat is server-only — never inbound from a client. The wire
    type's literal MUST exclude it so a malicious or buggy client
    cannot claim defeat (which would short-circuit player_dead's
    auto-trigger logic in Task 10)."""
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RetreatToHamletPayload(outcome="defeat")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        RetreatToHamletPayload(outcome="wounded_dungeon")  # old conflated literal — gone
    # Two valid outcomes accepted:
    for ok in ("retreat", "victory"):
        p = RetreatToHamletPayload(outcome=ok)  # type: ignore[arg-type]
        assert p.outcome == ok
        assert p.wounded_boss is False  # default


def test_retreat_wounded_boss_orthogonal_to_outcome():
    """All four (outcome, wounded_boss) inbound combinations construct.
    Client UI presents these as outcome buttons + a separate wound checkbox.
    """
    for outcome in ("retreat", "victory"):
        for wounded in (True, False):
            p = RetreatToHamletPayload(outcome=outcome, wounded_boss=wounded)  # type: ignore[arg-type]
            assert p.outcome == outcome
            assert p.wounded_boss is wounded
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Add the four payload models + their wrapper Message classes to `messages.py`**

`AvailableDungeon`, `HubViewPayload`, `DungeonSelectPayload`, `RetreatToHamletPayload` — exactly as specified in §3.2. Place them near the other inbound/outbound message classes (search for an existing message and insert nearby for cohesion).

- [ ] **Step 4: Run; expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py sidequest-server/tests/protocol/test_messages.py
git commit -m "feat(protocol): payload models for hub view + delve lifecycle"
```

### Task 4: Protocol dispatch — register new inbound types

**Files:**
- Modify: `sidequest-server/sidequest/protocol/dispatch.py`
- Test: `sidequest-server/tests/protocol/test_dispatch.py` (existing)

- [ ] **Step 1: Read current dispatch table**

```bash
grep -nE "DUNGEON_SELECT|RETREAT|_KIND_TO_MESSAGE_CLS|TYPE_MAP|register" sidequest-server/sidequest/protocol/dispatch.py | head -10
```
Identify the table that maps `MessageType` → pydantic class for inbound parsing.

- [ ] **Step 2: Write failing test**

```python
def test_dispatch_parses_dungeon_select():
    raw = {
        "type": "DUNGEON_SELECT",
        "payload": {"dungeon": "grimvault", "party_hireling_ids": ["a"]},
    }
    msg = parse_inbound(raw)  # whatever the dispatch entry point is named
    assert isinstance(msg, DungeonSelectMessage)
    assert msg.payload.dungeon == "grimvault"


def test_dispatch_parses_retreat():
    raw = {"type": "RETREAT_TO_HAMLET", "payload": {"outcome": "retreat"}}
    msg = parse_inbound(raw)
    assert isinstance(msg, RetreatToHamletMessage)


def test_dispatch_does_not_parse_hub_view_inbound():
    """HUB_VIEW is server→client only. Inbound HUB_VIEW must error."""
    import pytest
    raw = {"type": "HUB_VIEW", "payload": {}}
    with pytest.raises(Exception):  # narrow once the dispatch contract is read
        parse_inbound(raw)
```

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Add the two inbound types to the dispatch table**

Do NOT register HUB_VIEW as inbound — it's outbound only.

- [ ] **Step 5: Run; expect pass**

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/protocol/dispatch.py sidequest-server/tests/protocol/test_dispatch.py
git commit -m "feat(protocol): register DUNGEON_SELECT + RETREAT_TO_HAMLET as inbound"
```

### Task 5: `delve_lifecycle.py` — `is_hub_world` + `materialize_party`

**Files:**
- Create: `sidequest-server/sidequest/game/delve_lifecycle.py`
- Test: `sidequest-server/tests/game/test_delve_lifecycle.py` (new)

- [ ] **Step 1: Verify `Character` death field AND add `hireling_id`**

Run: `grep -nE "is_dead|player_dead|hireling_id|class Character" sidequest-server/sidequest/game/character.py | head -10`

This task adds **two** fields to `Character` (or one, if `is_dead` is already present):

1. **`hireling_id: str | None = None`** — required for commit-back attribution. Match-by-name was rejected during plan review (namegen has finite culture-corpus entropy; two hirelings can share a display name; misattribution is silent). Match-by-id is the only correct path. `None` for legacy chargen-spawned PCs.

2. **`is_dead: bool = False`** — sibling to the existing party-level `GameSnapshot.player_dead`. Required so commit-back can flip exactly the right hireling's status when one dies but the party retreats.

Both get a covering test in `tests/game/test_character.py`:

```python
def test_character_hireling_id_defaults_none():
    ch = make_minimal_character(name="Anon")
    assert ch.hireling_id is None

def test_character_hireling_id_round_trips():
    ch = make_minimal_character(name="Volga", hireling_id="vol_1")
    raw = ch.model_dump_json()
    ch2 = Character.model_validate_json(raw)
    assert ch2.hireling_id == "vol_1"

def test_character_is_dead_defaults_false():
    ch = make_minimal_character(name="Anon")
    assert ch.is_dead is False
```

- [ ] **Step 2: Write failing tests for `is_hub_world` and `materialize_party`**

```python
# tests/game/test_delve_lifecycle.py
import pytest
from sidequest.game.delve_lifecycle import is_hub_world, materialize_party
from sidequest.game.world_save import Hireling


def _h(id_: str, status: str = "active") -> Hireling:
    return Hireling(id=id_, name=id_.title(), archetype="prig", status=status)


def test_is_hub_world_true_when_dungeons():
    # Use a stub: ``World(dungeons={"x": ...})`` shape isn't trivial to
    # build; cover via the loaded caverns_and_claudes pack instead.
    from sidequest.genre.loader import load_genre_pack_cached
    pack = load_genre_pack_cached("caverns_and_claudes")
    assert is_hub_world(pack.worlds["caverns_three_sins"]) is True


def test_is_hub_world_false_for_leaf():
    from sidequest.genre.loader import load_genre_pack_cached
    pack = load_genre_pack_cached("space_opera")
    assert is_hub_world(pack.worlds["coyote_star"]) is False


def test_materialize_party_validates_size_lower():
    with pytest.raises(ValueError, match="party size"):
        materialize_party([_h("a")], [], world_slug="x", dungeon=...)  # type: ignore[arg-type]


def test_materialize_party_validates_size_upper():
    roster = [_h(f"h{i}") for i in range(7)]
    with pytest.raises(ValueError, match="party size"):
        materialize_party(roster, [h.id for h in roster], world_slug="x", dungeon=...)  # type: ignore[arg-type]


def test_materialize_party_rejects_missing_id():
    with pytest.raises(ValueError, match="not in roster"):
        materialize_party([_h("a")], ["a", "b"], world_slug="x", dungeon=...)  # type: ignore[arg-type]


def test_materialize_party_rejects_dead_hireling():
    with pytest.raises(ValueError, match="not active"):
        materialize_party(
            [_h("a"), _h("b", status="dead")],
            ["a", "b"],
            world_slug="x", dungeon=...,  # type: ignore[arg-type]
        )


def test_materialize_party_rejects_duplicates():
    with pytest.raises(ValueError, match="duplicates"):
        materialize_party(
            [_h("a"), _h("b")],
            ["a", "a"],
            world_slug="x", dungeon=...,  # type: ignore[arg-type]
        )


def test_materialize_party_carries_hireling_id_and_name():
    from sidequest.genre.loader import load_genre_pack_cached
    pack = load_genre_pack_cached("caverns_and_claudes")
    dungeon = pack.worlds["caverns_three_sins"].dungeons["grimvault"]
    roster = [_h("vol_1"), _h("zin_1")]
    party = materialize_party(roster, ["vol_1", "zin_1"],
                              world_slug="caverns_three_sins",
                              dungeon=dungeon)
    assert len(party) == 2
    assert {ch.core.name for ch in party} == {"Vol_1", "Zin_1"}
    assert {ch.core.archetype for ch in party} == {"prig"}
    # Commit-back attribution match key — must round-trip.
    assert {ch.hireling_id for ch in party} == {"vol_1", "zin_1"}


def test_materialize_party_does_not_carry_stress():
    """Stress lives on Hireling but is item 3 territory; this plan does
    not propagate it to Character. Defensive test so a future change
    that adds stress propagation gets caught and routed to item 3."""
    from sidequest.genre.loader import load_genre_pack_cached
    pack = load_genre_pack_cached("caverns_and_claudes")
    dungeon = pack.worlds["caverns_three_sins"].dungeons["grimvault"]
    h = Hireling(id="stressed_1", name="X", archetype="prig", stress=42)
    [ch] = materialize_party([h], ["stressed_1"],
                             world_slug="caverns_three_sins",
                             dungeon=dungeon)
    # Item 3 will add Character.stress; until then, the field either
    # doesn't exist on Character or stays at default. Explicit absence
    # check via model_dump avoids accidental copy.
    assert "stress" not in ch.model_dump() or ch.model_dump().get("stress") == 0
```

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Implement `delve_lifecycle.py` with `is_hub_world` + `materialize_party` + `_character_from_hireling`**

Per §4 / §5. The `_character_from_hireling` implementation is test-driven: get `test_materialize_party_carries_name_and_archetype` passing with whatever shape `Character` actually has.

- [ ] **Step 5: Run; expect 8 passed**

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/delve_lifecycle.py sidequest-server/tests/game/test_delve_lifecycle.py
git commit -m "feat(delve_lifecycle): is_hub_world + materialize_party"
```

### Task 6: `delve_lifecycle.py` — `commit_back` + `apply_delve_end`

**Files:**
- Modify: `sidequest-server/sidequest/game/delve_lifecycle.py`
- Modify: `sidequest-server/tests/game/test_delve_lifecycle.py`

- [ ] **Step 1: Write failing tests**

```python
from datetime import UTC, datetime
from sidequest.game.delve_lifecycle import apply_delve_end, commit_back
from sidequest.game.session import GameSnapshot
from sidequest.game.world_save import Hireling, WorldSave


def test_commit_back_matches_by_id_not_name():
    """Two hirelings with the same display name — namegen collision is
    a real possibility on a small culture corpus. Commit-back MUST
    attribute death to the right id, not the first name match."""
    ws = WorldSave(roster=[
        _h("a"), _h("b"),  # default _h sets name = id.title()
        Hireling(id="dup_1", name="Volga", archetype="prig"),
        Hireling(id="dup_2", name="Volga", archetype="prig"),  # same name
    ])
    snap = GameSnapshot(genre_slug="x", world_slug="y")
    snap.characters = [
        _make_character(name="Volga", hireling_id="dup_1", is_dead=False),
        _make_character(name="Volga", hireling_id="dup_2", is_dead=True),
    ]
    new_ws = commit_back(snap, ws)
    by_id = {h.id: h for h in new_ws.roster}
    assert by_id["dup_1"].status == "active"
    assert by_id["dup_2"].status == "dead"


def test_commit_back_copies_dead_status():
    ws = WorldSave(roster=[_h("a"), _h("b")])
    snap = GameSnapshot(genre_slug="x", world_slug="y")
    snap.characters = [
        _make_character(name="A", hireling_id="a", is_dead=False),
        _make_character(name="B", hireling_id="b", is_dead=True),
    ]
    new_ws = commit_back(snap, ws)
    by_id = {h.id: h for h in new_ws.roster}
    assert by_id["a"].status == "active"
    assert by_id["b"].status == "dead"


def test_commit_back_ignores_character_without_hireling_id():
    """Legacy chargen-spawned PC has hireling_id=None — commit-back
    skips it (no roster row to write back to). Doesn't crash."""
    ws = WorldSave(roster=[_h("a")])
    snap = GameSnapshot(genre_slug="x", world_slug="y")
    snap.characters = [
        _make_character(name="LegacyPC", hireling_id=None, is_dead=True),
        _make_character(name="A", hireling_id="a", is_dead=True),
    ]
    new_ws = commit_back(snap, ws)
    assert {h.id: h.status for h in new_ws.roster} == {"a": "dead"}


def test_commit_back_does_not_touch_stress():
    """Stress is item 3 territory. commit_back must NOT propagate
    Character.stress to Hireling.stress in this plan — even if a
    future Character.stress field exists."""
    ws = WorldSave(roster=[
        Hireling(id="a", name="A", archetype="prig", stress=42),
    ])
    snap = GameSnapshot(genre_slug="x", world_slug="y")
    # _make_character may or may not have a stress field after item 3;
    # either way, commit_back leaves the Hireling stress untouched.
    snap.characters = [_make_character(name="A", hireling_id="a")]
    new_ws = commit_back(snap, ws)
    assert new_ws.roster[0].stress == 42


def test_apply_delve_end_increments_count_and_appends_wall():
    ws = WorldSave(
        roster=[_h("a"), _h("b")],
        delve_count=2,
    )
    snap = GameSnapshot(genre_slug="x", world_slug="y")
    snap.characters = [
        _make_character(name="A", hireling_id="a"),
        _make_character(name="B", hireling_id="b"),
    ]

    new_ws = apply_delve_end(
        ws,
        dungeon_slug="grimvault",
        dungeon_sin="pride",
        outcome="victory",
        wounded_boss=False,
        party_hireling_ids=["a", "b"],
        snapshot=snap,
        timestamp=datetime(2026, 5, 5, tzinfo=UTC),
    )
    assert new_ws.delve_count == 3
    assert new_ws.latest_delve_sin == "pride"
    assert len(new_ws.wall) == 1
    assert new_ws.wall[0].outcome == "victory"
    assert new_ws.wall[0].wounded_boss is False
    assert new_ws.wall[0].dungeon == "grimvault"
    assert new_ws.wall[0].delve_number == 3
    assert new_ws.dungeon_wounds == {}  # no wound flag on non-wounded delve


def test_apply_delve_end_wound_flag_orthogonal_to_outcome():
    """Spec §"Wounded Sins" line 81: "a successful boss delve flips a
    permanent flag." The flag flips when wounded_boss=True, regardless
    of outcome — so a TPK-after-wound is recordable correctly."""
    ws = WorldSave(roster=[_h("a")])
    snap = GameSnapshot(genre_slug="x", world_slug="y")
    snap.characters = [_make_character(name="A", hireling_id="a", is_dead=True)]
    new_ws = apply_delve_end(
        ws, dungeon_slug="grimvault", dungeon_sin="pride",
        outcome="defeat", wounded_boss=True,
        party_hireling_ids=["a"],
        snapshot=snap, timestamp=datetime.now(tz=UTC),
    )
    assert new_ws.dungeon_wounds == {"grimvault": True}
    assert new_ws.wall[0].outcome == "defeat"
    assert new_ws.wall[0].wounded_boss is True
    by_id = {h.id: h for h in new_ws.roster}
    assert by_id["a"].status == "dead"  # commit-back honored


def test_apply_delve_end_defeat_without_wound_does_not_wound():
    ws = WorldSave(roster=[_h("a")])
    snap = GameSnapshot(genre_slug="x", world_slug="y")
    snap.characters = [_make_character(name="A", hireling_id="a", is_dead=True)]
    new_ws = apply_delve_end(
        ws, dungeon_slug="grimvault", dungeon_sin="pride",
        outcome="defeat", wounded_boss=False,
        party_hireling_ids=["a"],
        snapshot=snap, timestamp=datetime.now(tz=UTC),
    )
    assert new_ws.dungeon_wounds == {}  # not wounded
    assert new_ws.wall[0].wounded_boss is False
```

`_make_character` is a test helper in the same file that constructs a `Character` with the unified-character-model fields filled in to safe defaults.

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `commit_back` + `apply_delve_end`**

Per §4.

- [ ] **Step 4: Run; expect pass (7 added, 15 total)**

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/delve_lifecycle.py sidequest-server/tests/game/test_delve_lifecycle.py
git commit -m "feat(delve_lifecycle): commit_back + apply_delve_end"
```

### Task 7: Connect handler — hub-mode emission replaces hub-rejection

**Files:**
- Modify: `sidequest-server/sidequest/handlers/connect.py`
- Test: `sidequest-server/tests/handlers/test_connect.py` (existing)

- [ ] **Step 1: Write failing tests**

```python
def test_connect_emits_hub_view_for_hub_world(temp_save_dir):
    """Hub-world fresh connect → exactly one HUB_VIEW frame, no NARRATION."""
    # Set up a fresh save against caverns_three_sins.
    # Drive connect; assert message stream:
    msgs = drive_connect(slug="hub-test",
                        genre="caverns_and_claudes",
                        world="caverns_three_sins")
    types = [m.type for m in msgs]
    assert MessageType.HUB_VIEW in types
    assert MessageType.NARRATION not in types
    assert MessageType.ERROR not in types
    hub_view = next(m for m in msgs if m.type == MessageType.HUB_VIEW)
    assert [d.slug for d in hub_view.payload.available_dungeons] == \
        ["grimvault", "horden", "mawdeep"]
    # Server resolves sin server-side — client doesn't need a hardcoded map.
    assert {d.slug: d.sin for d in hub_view.payload.available_dungeons} == {
        "grimvault": "pride", "horden": "greed", "mawdeep": "gluttony",
    }
    assert all(d.wounded is False for d in hub_view.payload.available_dungeons)


def test_connect_resumes_mid_delve_skipping_hub_view(temp_save_dir):
    """A snapshot with active_delve_dungeon set bypasses hub mode."""
    # Pre-seed a snapshot with active_delve_dungeon="grimvault" and
    # at least one character. Connect; expect leaf-world-style flow,
    # no HUB_VIEW.
    msgs = drive_connect_with_active_delve(...)
    types = [m.type for m in msgs]
    assert MessageType.HUB_VIEW not in types


def test_connect_leaf_world_unchanged(temp_save_dir):
    """Regression: a leaf world (e.g. space_opera/coyote_star) still
    works exactly as before."""
    msgs = drive_connect(slug="leaf-test",
                        genre="space_opera",
                        world="coyote_star")
    types = [m.type for m in msgs]
    assert MessageType.HUB_VIEW not in types
    # Whatever the existing leaf-world success markers are (NARRATION,
    # OPENING, CHARACTER_CREATION) — assert at least one of them.
    assert any(t in types for t in (
        MessageType.CHARACTER_CREATION, MessageType.NARRATION,
    ))
```

- [ ] **Step 2: Run; expect failures (hub_view test fails on the typed-error response from the existing rejection guard)**

- [ ] **Step 3: Replace the rejection block in `connect.py`**

Per §6. Move the `saved = store.load()` call up so its result feeds the hub-vs-resume decision. Keep the legacy hub-rejection error path *removed entirely* — the new behavior is correct and the old behavior is dead.

Per `feedback_dead_code` (memory): delete the dead rejection branch in the same commit; do not leave it as commented-out code or guarded-by-flag.

- [ ] **Step 4: Run; expect 3 passed (hub-view + resume + leaf-unchanged)**

- [ ] **Step 5: Run the full `tests/handlers/test_connect.py`; expect no regressions**

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/handlers/connect.py sidequest-server/tests/handlers/test_connect.py
git commit -m "feat(connect): replace hub-rejection with HUB_VIEW emission"
```

### Task 8: `DUNGEON_SELECT` handler

**Files:**
- Create: `sidequest-server/sidequest/handlers/dungeon_select.py`
- Modify: wherever the inbound dispatch routes by `MessageType` (verify in step 1)
- Test: `sidequest-server/tests/handlers/test_dungeon_select.py` (new)

- [ ] **Step 1: Locate the inbound dispatch routing**

Run: `grep -nE "PLAYER_ACTION|MessageType\.|handle_" sidequest-server/sidequest/server/websocket_session_handler.py | head -20`

Identify how inbound `PLAYER_ACTION` reaches its handler. New handler hooks into the same site.

- [ ] **Step 2: Write failing tests**

```python
async def test_dungeon_select_starts_delve(temp_save_dir):
    # Prime: connect to hub mode, recruit two hirelings.
    slug = "ds-test"
    drive_hub_connect(slug, "caverns_and_claudes", "caverns_three_sins")
    h1 = drive_recruit(slug)
    h2 = drive_recruit(slug)

    # Send DUNGEON_SELECT.
    msgs = await drive_dungeon_select(slug, "grimvault", [h1["id"], h2["id"]])
    types = [m.type for m in msgs]
    # Expect: NO error frame; expect opening narration + active_delve set.
    assert MessageType.ERROR not in types

    snapshot = read_snapshot(slug)
    assert snapshot.active_delve_dungeon == "grimvault"
    assert len(snapshot.characters) == 2


async def test_dungeon_select_rejects_when_already_delving(temp_save_dir):
    slug = "ds-2"
    drive_hub_connect(slug, ...)
    h1 = drive_recruit(slug)
    await drive_dungeon_select(slug, "grimvault", [h1["id"]])
    # Second call should fail.
    msgs = await drive_dungeon_select(slug, "horden", [h1["id"]])
    err = next(m for m in msgs if m.type == MessageType.ERROR)
    assert err.code == "delve_already_active"


async def test_dungeon_select_rejects_unknown_dungeon(temp_save_dir):
    slug = "ds-3"
    drive_hub_connect(slug, ...)
    h1 = drive_recruit(slug)
    msgs = await drive_dungeon_select(slug, "nonexistent", [h1["id"]])
    err = next(m for m in msgs if m.type == MessageType.ERROR)
    assert err.code == "unknown_dungeon"


async def test_dungeon_select_rejects_dead_hireling(temp_save_dir):
    slug = "ds-4"
    drive_hub_connect(slug, ...)
    h1 = drive_recruit(slug)
    drive_dismiss(slug, h1["id"], reason="died_offscreen")
    msgs = await drive_dungeon_select(slug, "grimvault", [h1["id"]])
    err = next(m for m in msgs if m.type == MessageType.ERROR)
    assert err.code == "invalid_party"
```

`drive_recruit` / `drive_dismiss` / `drive_dungeon_select` are test helpers that wrap the REST + WS calls. They live in a `tests/conftest.py` fixture that the next several test files share.

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Create the handler module + register it**

Per §7. Imports: `from sidequest.game.delve_lifecycle import is_hub_world, materialize_party`.

- [ ] **Step 5: Run; expect 4 passed**

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/handlers/dungeon_select.py \
        sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/handlers/test_dungeon_select.py \
        sidequest-server/tests/conftest.py
git commit -m "feat(handlers): DUNGEON_SELECT starts a delve"
```

### Task 9: `RETREAT_TO_HAMLET` handler + `_end_delve` helper

**Files:**
- Create: `sidequest-server/sidequest/handlers/retreat_to_hamlet.py`
- Test: `sidequest-server/tests/handlers/test_retreat_to_hamlet.py` (new)

- [ ] **Step 1: Write failing tests**

```python
async def test_retreat_appends_wall_and_emits_hub_view(temp_save_dir):
    slug = "r-1"
    drive_hub_connect(slug, ...)
    h1 = drive_recruit(slug)
    h2 = drive_recruit(slug)
    await drive_dungeon_select(slug, "grimvault", [h1["id"], h2["id"]])

    msgs = await drive_retreat(slug, outcome="retreat", wounded_boss=False)
    types = [m.type for m in msgs]
    assert MessageType.HUB_VIEW in types

    ws = read_world_save(slug)
    assert ws.delve_count == 1
    assert len(ws.wall) == 1
    assert ws.wall[0].sin == "pride"  # grimvault's sin
    assert ws.wall[0].dungeon == "grimvault"
    assert ws.wall[0].outcome == "retreat"
    assert ws.wall[0].wounded_boss is False
    assert ws.latest_delve_sin == "pride"
    assert ws.dungeon_wounds == {}


async def test_retreat_with_wounded_boss_sets_wound_flag(temp_save_dir):
    """Victory + wounded_boss=True flips the dungeon's wound flag."""
    slug = "r-2"
    drive_hub_connect(slug, ...); h1 = drive_recruit(slug)
    await drive_dungeon_select(slug, "grimvault", [h1["id"]])
    await drive_retreat(slug, outcome="victory", wounded_boss=True)
    ws = read_world_save(slug)
    assert ws.dungeon_wounds == {"grimvault": True}
    assert ws.wall[0].outcome == "victory"
    assert ws.wall[0].wounded_boss is True


async def test_retreat_with_tpk_after_wound(temp_save_dir):
    """The bittersweet TPK-after-wound case: party died but the boss
    was wounded. Spec line 81 says wound flag flips on the event,
    not on victory. Recordable as (defeat from player_dead auto, but
    here we test the (retreat, wounded_boss=True) variant — party
    chose to flee after wounding the boss but somebody died offscreen)."""
    slug = "r-2b"
    drive_hub_connect(slug, ...); h1 = drive_recruit(slug)
    await drive_dungeon_select(slug, "grimvault", [h1["id"]])
    await drive_retreat(slug, outcome="retreat", wounded_boss=True)
    ws = read_world_save(slug)
    assert ws.dungeon_wounds == {"grimvault": True}
    assert ws.wall[0].outcome == "retreat"
    assert ws.wall[0].wounded_boss is True


async def test_retreat_clears_active_delve(temp_save_dir):
    slug = "r-3"
    drive_hub_connect(slug, ...); h1 = drive_recruit(slug)
    await drive_dungeon_select(slug, "grimvault", [h1["id"]])
    await drive_retreat(slug, outcome="victory", wounded_boss=False)
    snap = read_snapshot(slug)
    assert snap.active_delve_dungeon is None


async def test_retreat_rejects_in_hub_mode(temp_save_dir):
    """RETREAT outside an active delve must error, not silently no-op."""
    slug = "r-4"
    drive_hub_connect(slug, ...)
    msgs = await drive_retreat(slug, outcome="retreat", wounded_boss=False)
    err = next(m for m in msgs if m.type == MessageType.ERROR)
    assert err.code == "not_in_delve"


async def test_retreat_does_not_clear_world_save(temp_save_dir):
    """The init_session() inside _end_delve must NOT touch world_save."""
    slug = "r-5"
    drive_hub_connect(slug, ...)
    h1 = drive_recruit(slug); h2 = drive_recruit(slug)
    await drive_dungeon_select(slug, "grimvault", [h1["id"], h2["id"]])
    await drive_retreat(slug, outcome="victory", wounded_boss=False)
    ws = read_world_save(slug)
    assert {h.id for h in ws.roster} == {h1["id"], h2["id"]}, \
        "roster must survive _end_delve's init_session call"
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Create `retreat_to_hamlet.py` and the shared `_end_delve` helper**

Per §8. The helper lives in a sibling private module or in `delve_lifecycle.py` as an impure async function — verify in step 1 of this task what the codebase prefers for handler-shared helpers. (If unclear, put it in `dungeon_select.py` as a `_shared_end_delve`-style function that both handlers import; the cross-import is acceptable.)

- [ ] **Step 4: Run; expect 6 passed**

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/handlers/retreat_to_hamlet.py \
        sidequest-server/sidequest/game/delve_lifecycle.py \
        sidequest-server/tests/handlers/test_retreat_to_hamlet.py
git commit -m "feat(handlers): RETREAT_TO_HAMLET ends delve, persists hub state"
```

### Task 10: `player_dead` auto-trigger

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py` (or wherever the post-narration-apply check lives)
- Test: `sidequest-server/tests/handlers/test_retreat_to_hamlet.py` (extend)

- [ ] **Step 1: Locate the post-narration-apply call site**

Run: `grep -nE "_apply_narration_result_to_snapshot|player_dead" sidequest-server/sidequest/server/websocket_session_handler.py`

- [ ] **Step 2: Write failing test**

```python
async def test_player_dead_auto_triggers_defeat(temp_save_dir):
    slug = "pd-1"
    drive_hub_connect(slug, ...)
    h1 = drive_recruit(slug)
    await drive_dungeon_select(slug, "grimvault", [h1["id"]])
    # Force player_dead via the test harness (bypass narrator).
    set_player_dead(slug, True)
    # Run one dispatch tick; expect HUB_VIEW emission and Wall append.
    msgs = await drive_dispatch_tick(slug)
    assert MessageType.HUB_VIEW in [m.type for m in msgs]
    ws = read_world_save(slug)
    assert ws.delve_count == 1
    assert ws.wall[0].outcome == "defeat"
    # Auto-trigger sets wounded_boss=False — narrator-driven wound
    # detection is item-4-followon. The honest gap is documented in
    # PR description so a missing wound after a wounded-then-killed
    # delve is a known limitation, not a bug.
    assert ws.wall[0].wounded_boss is False
    assert ws.dungeon_wounds == {}
```

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Add the positive-edge check in the dispatch caller**

Per §9. Capture `prev_player_dead` before the apply call. After the apply, if the edge is positive AND `active_delve_dungeon is not None`, fire `_end_delve(outcome="defeat")`.

- [ ] **Step 5: Run; expect pass**

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/handlers/test_retreat_to_hamlet.py
git commit -m "feat(dispatch): player_dead auto-triggers defeat delve-end"
```

### Task 11: REST recruit + dismiss

**Files:**
- Modify: `sidequest-server/sidequest/server/rest.py`
- Test: `sidequest-server/tests/server/test_rest_hub_endpoint.py` (extend the file from item-2)

- [ ] **Step 1: Locate the existing namegen entry point**

Run: `grep -nE "from sidequest\..*namegen|generate_name|def generate_" sidequest-server/sidequest/cli/namegen/namegen.py sidequest-server/sidequest/game/*.py | head`

The recruit endpoint must use the project's existing namegen — not invent a new one. Also locate `archetype_funnels` access on a loaded `World` (the loader plan added it).

- [ ] **Step 2: Write failing tests**

```python
def test_recruit_adds_hireling_to_roster(client, tmp_path):
    _seed_game(tmp_path, "rec-1", "caverns_and_claudes", "caverns_three_sins")
    r = client.post("/api/games/rec-1/hub/recruit", json={})
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "name" in body
    assert body["status"] == "active"

    r2 = client.get("/api/games/rec-1/hub")
    assert len(r2.json()["world_save"]["roster"]) == 1


def test_recruit_rejects_during_delve(client, tmp_path):
    # Pre-seed a snapshot with active_delve_dungeon set.
    store = _seed_game(tmp_path, "rec-2", "caverns_and_claudes",
                      "caverns_three_sins")
    snap = GameSnapshot(genre_slug="caverns_and_claudes",
                        world_slug="caverns_three_sins",
                        active_delve_dungeon="grimvault")
    store.save(snap)
    store.close()
    r = client.post("/api/games/rec-2/hub/recruit", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "delve_in_progress"


def test_dismiss_removes_alive_hireling(client, tmp_path):
    store = _seed_game(tmp_path, "dis-1", "caverns_and_claudes",
                      "caverns_three_sins")
    store.save_world_save(WorldSave(roster=[
        Hireling(id="h1", name="X", archetype="prig"),
    ]))
    store.close()
    r = client.delete("/api/games/dis-1/hub/roster/h1?reason=dismiss")
    assert r.status_code == 200
    body = client.get("/api/games/dis-1/hub").json()
    assert body["world_save"]["roster"] == []


def test_dismiss_died_offscreen_keeps_row_marked_dead(client, tmp_path):
    store = _seed_game(tmp_path, "dis-2", "caverns_and_claudes",
                      "caverns_three_sins")
    store.save_world_save(WorldSave(roster=[
        Hireling(id="h2", name="Y", archetype="prig"),
    ]))
    store.close()
    r = client.delete("/api/games/dis-2/hub/roster/h2?reason=died_offscreen")
    assert r.status_code == 200
    body = client.get("/api/games/dis-2/hub").json()
    assert body["world_save"]["roster"][0]["status"] == "dead"


def test_dismiss_404_unknown_id(client, tmp_path):
    _seed_game(tmp_path, "dis-3", "caverns_and_claudes", "caverns_three_sins")
    r = client.delete("/api/games/dis-3/hub/roster/nope?reason=dismiss")
    assert r.status_code == 404
```

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Add the two endpoints to `rest.py`**

Per §10. The `_roll_hireling_from_funnels` helper goes in `sidequest/game/delve_lifecycle.py` (it's per-world business logic, not REST plumbing). Use the namegen entry point identified in step 1.

- [ ] **Step 5: Run; expect 5 passed**

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/rest.py \
        sidequest-server/sidequest/game/delve_lifecycle.py \
        sidequest-server/tests/server/test_rest_hub_endpoint.py
git commit -m "feat(rest): hub recruit + dismiss endpoints"
```

### Task 12: Telemetry spans

**Files:**
- Create or modify: `sidequest-server/sidequest/telemetry/spans/session.py`
- Modify: `sidequest-server/sidequest/handlers/connect.py`, `dungeon_select.py`, `retreat_to_hamlet.py`, `sidequest/server/rest.py`
- Test: `sidequest-server/tests/telemetry/test_session_spans.py` (existing or new)

- [ ] **Step 1: Find the existing spans pattern**

Run: `grep -nE "SPAN_SESSION|watcher_publish" sidequest-server/sidequest/telemetry/spans/persistence.py sidequest-server/sidequest/telemetry/spans/session.py`

- [ ] **Step 2: Write failing tests**

```python
def test_hub_mode_entered_span_fires_on_hub_connect(...):
    # Subscribe to the watcher hub; drive a hub connect; assert
    # exactly one session.hub_mode_entered event with the expected
    # roster_size + delve_count attributes.
    ...


def test_delve_started_span_fires(...):
    ...


def test_delve_ended_span_fires_with_outcome(...):
    ...


def test_hireling_recruited_span_fires(...):
    ...


def test_hireling_dismissed_span_fires(...):
    ...
```

- [ ] **Step 3: Run; expect failure**

- [ ] **Step 4: Add the five `_watcher_publish` calls to their respective sites**

Per §11. Reuse the existing `_watcher_publish` helper used by the loader-recursion plan and the existing connect-handler hub-block span (now removed). Span names are kebab/dot-cased per existing convention (e.g. `session.delve_started`).

- [ ] **Step 5: Run; expect pass**

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/session.py \
        sidequest-server/sidequest/handlers/connect.py \
        sidequest-server/sidequest/handlers/dungeon_select.py \
        sidequest-server/sidequest/handlers/retreat_to_hamlet.py \
        sidequest-server/sidequest/server/rest.py \
        sidequest-server/tests/telemetry/test_session_spans.py
git commit -m "feat(telemetry): five spans across hub + delve lifecycle"
```

### Task 13: End-to-end happy-path test

**Files:**
- Test: `sidequest-server/tests/integration/test_sunden_hub_e2e.py` (new)

The single most playtest-aligned test in the suite. Walks the full loop.

- [ ] **Step 1: Write the test**

```python
async def test_full_sunden_loop_recruit_delve_retreat_recruit_delve():
    """Full hub loop end-to-end. The 'Keith would actually do this' test.

    Flow:
      1. Hub-mode connect — assert HUB_VIEW with empty roster + 3
         enriched dungeon descriptors {grimvault/pride/wounded=False, ...}.
      2. Recruit two hirelings — assert roster grows.
      3. DUNGEON_SELECT(grimvault, [both]) — assert delve starts.
      4. RETREAT_TO_HAMLET(outcome=victory, wounded_boss=False) — assert
         HUB_VIEW emitted; Wall has one entry with outcome=victory,
         wounded_boss=False; latest_delve_sin == 'pride'; delve_count == 1;
         dungeon_wounds still empty.
      5. Recruit a third hireling.
      6. DUNGEON_SELECT(horden, [the new one]) — assert delve starts in
         a different dungeon, with a different sin's drift waiting in
         WorldSave (latest_delve_sin still 'pride' until this delve ends).
      7. RETREAT_TO_HAMLET(outcome=victory, wounded_boss=True) — assert
         dungeon_wounds == {'horden': True}; latest_delve_sin == 'greed';
         Wall has 2 entries; second entry has wounded_boss=True;
         next HUB_VIEW's available_dungeons shows horden.wounded=True.
    """
    ...
```

The test exercises every code path this plan touches end-to-end and is what the implementer should run last to convince themselves the loop works.

- [ ] **Step 2: Run; expect green at the end of all prior tasks**

If this test fails after the prior tasks pass, *something is wrong with the integration*, not the units. Diagnose before claiming the plan complete.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/integration/test_sunden_hub_e2e.py
git commit -m "test(sunden): full hub→delve→retreat→delve loop e2e"
```

### Task 14: Smoke + lint

- [ ] **Step 1: Run full server tests for affected scopes**

```bash
cd sidequest-server && uv run pytest tests/game/ tests/handlers/ \
    tests/server/test_rest_hub_endpoint.py tests/integration/test_sunden_hub_e2e.py \
    tests/protocol/ tests/telemetry/test_session_spans.py -v
```
Expected: all green.

- [ ] **Step 2: Lint**

```bash
cd sidequest-server && uv run ruff check sidequest/game/delve_lifecycle.py \
    sidequest/handlers/dungeon_select.py sidequest/handlers/retreat_to_hamlet.py \
    sidequest/handlers/connect.py sidequest/server/rest.py \
    sidequest/protocol/messages.py sidequest/protocol/enums.py \
    sidequest/telemetry/spans/session.py sidequest/server/websocket_session_handler.py
```
Expected: clean.

- [ ] **Step 3: Confirm broader test sweep is unchanged + flag what newly *passes***

```bash
cd sidequest-server && uv run pytest tests/server/ tests/integration/ 2>&1 | tail -20
```

The 44 pre-existing failures from the loader-recursion plan's follow-on may flip green individually as a side effect of `caverns_three_sins` being delvable. That's a *good* surprise. Note any tests that move from failing to passing — they reduce the test-sweep follow-on plan's scope. Don't delete them; just record which ones pass for the test-sweep plan author.

- [ ] **Step 4: Smoke — boot and walk through the loop manually**

```bash
just up
# In another shell, drive the loop with curl + websocat:
# 1. Create a game against caverns_three_sins
# 2. GET /api/games/<slug>/hub  → empty WorldSave
# 3. POST /api/games/<slug>/hub/recruit  → twice
# 4. WS connect → HUB_VIEW frame
# 5. WS send DUNGEON_SELECT  → narration starts
# 6. WS send RETREAT_TO_HAMLET(victory)  → HUB_VIEW frame
# 7. GET /api/games/<slug>/hub  → one Wall entry, delve_count=1
just down
```

### Task 15: PR

- [ ] **Step 1: Push branch and open PR (gitflow → develop)**

```bash
cd sidequest-server
git push -u origin feat/delve-lifecycle-engine
gh pr create --base develop --title "feat: delve lifecycle engine (Sünden item 4a)" --body "$(cat <<'EOF'
## Summary
- Hub-mode connect emits HUB_VIEW with enriched `available_dungeons: [{slug, sin, wounded}, ...]` so the client never needs a hardcoded sin map.
- New `active_delve_dungeon` discriminator on GameSnapshot.
- New `Character.hireling_id: str | None` — commit-back attribution match key (NOT name; namegen has finite culture-corpus entropy).
- New WS messages: `DUNGEON_SELECT` (start delve), `RETREAT_TO_HAMLET` (end delve; `outcome` ∈ {retreat, victory} + orthogonal `wounded_boss: bool`).
- New REST: `POST /api/games/{slug}/hub/recruit`, `DELETE /api/games/{slug}/hub/roster/{id}`.
- `player_dead` auto-triggers `outcome=defeat, wounded_boss=False` delve-end (narrator-driven wound detection is item-4-followon).
- `apply_delve_end` writes Wall entry, sets drift flag, sets `dungeon_wounds[slug]=True` whenever `wounded_boss=True` (regardless of outcome — TPK-after-wound is recordable).
- Stress is declared on Hireling by item 2 but NOT touched by this plan (item 3 owns stress accrual).
- 5 OTEL spans: hub_mode_entered, delve_started, delve_ended, hireling_recruited, hireling_dismissed.

## Plan
docs/superpowers/plans/2026-05-05-delve-lifecycle-engine.md (orchestrator).

## Sequenced after
- #190 (loader recursion, MERGED)
- WorldSave persistence (item 2 plan, must merge first)

## Test plan
- [x] tests/game/test_delve_lifecycle.py — units
- [x] tests/handlers/test_dungeon_select.py + test_retreat_to_hamlet.py — handlers
- [x] tests/server/test_rest_hub_endpoint.py — REST
- [x] tests/integration/test_sunden_hub_e2e.py — full loop
- [x] tests/telemetry/test_session_spans.py — 5 spans
- [x] ruff clean

## Unblocks
- Item 4b (Sünden hub UI plan, to be authored)
- Item 3 (stress mechanics plan, to be authored)
- Items 5/6/7 (narrator zones plan, to be authored)
- 44-test world-slug sweep plan (to be authored)
EOF
)"
```

## Risks

- **Connect handler restructure is invasive.** The existing connect.py is 600+ lines with several path branches (saved-resume, fresh-session, MP-join). Threading the hub-mode branch in cleanly without dropping a leaf-world case is the highest-risk change. *Mitigation:* Task 7 includes an explicit leaf-world regression test, run the full `tests/handlers/test_connect.py` after the change, and the hub-rejection branch deletes cleanly (it is dead code post-change per §6).
- **`_character_from_hireling` materialization may surface ADR-007 unified-character constraints.** A Character with empty chassis bindings / empty magic state may behave unexpectedly downstream (e.g. crash on a magic-state read). *Mitigation:* the Hireling materialization defaults to safe pydantic defaults; downstream code that reads chassis/magic must already null-guard since chargen-spawned Characters can have those fields empty for a turn or two. Surface any issue via Task 13's e2e test, which actually runs the dispatch loop.
- **`init_session()` clears the wrong tables.** This is the biggest "did item 2 land correctly" check. The retreat e2e test (Task 9 step 1, fifth test) explicitly asserts roster survives `init_session`. If that test fails, item 2 is broken, not this plan. *Mitigation:* the test is named explicitly so a failure points the implementer at the right spec.
- **Recruit naming collisions on a small culture corpus.** The default namegen path can produce duplicates after enough recruits. *Mitigation:* `_roll_hireling_from_funnels` retries up to N=20 with fresh namegen samples before raising. If even N=20 fails, the recruit endpoint returns 503 "namegen exhausted" rather than picking a colliding id silently. Bound the namegen call site with a clear error to keep the failure mode loud.
- **Solo-only assumption.** Multiplayer connects to the same slug share the snapshot. A second WS client connecting mid-delve sees the active_delve_dungeon and falls into the leaf-world resume branch; recruit/dismiss attempted from a client mid-delve gets the typed `delve_in_progress` rejection. Both are correct. The only MP-specific concern is "two clients pick different parties simultaneously"; the protocol's existing `state.Pre*` queueing in the room model serializes these. *Mitigation:* call out in PR description that MP-shared roster delve is solo-only-tested in this plan; a multi-client party-select test is item 4-followon.
- **`_search_paths` private leak.** Connect.py uses `session._search_paths`; the new dungeon_select handler reaches for the same name. The leading underscore is a code smell that this plan inherits, not introduces. *Mitigation:* don't refactor here; flag in PR as a follow-on cleanup. Refactoring `_search_paths` to a public attribute is its own one-line PR.
- **The narrator never receives `active_delve_dungeon` context.** During a delve, the narrator prompt zone gets the same data it gets today. The narrator does not know it is in `grimvault` specifically (vs the legacy single-world `grimvault`). For most prompts this is fine because the dungeon's openings/cartography/Keeper definition flow through the existing per-world prompt assembly. But if any prompt-zone author writes something keyed on `world_slug` expecting `grimvault`, it now reads `caverns_three_sins`. *Mitigation:* this is item 5/6/7 territory (narrator zones) — ensure the items-5/6/7 plan reads `dungeon` from `active_delve_dungeon` AND the dungeon model, not `world_slug`.
- **No narrator-driven outcome detection means players can lie about wounded_boss.** A player can send `RETREAT_TO_HAMLET(outcome="retreat", wounded_boss=True)` without ever fighting the Keeper, flipping `dungeon_wounds[slug]` to True. *Mitigation:* this is honest MVP — Keith DMs himself, so cheating is irrelevant for the playgroup audience. Item-4-followon adds narrator-side detection (sidecar field on `NarrationTurnResult` flagging boss-wound events), and the GM panel exposes the `outcome` AND `wounded_boss` attributes separately on `session.delve_ended` so Sebastien can see exactly what was claimed and verify it against the dashboard's narration log.

## Definition of Done

- All 15 tasks complete.
- `tests/game/test_delve_lifecycle.py` (~15 tests — added: match-by-id, ignore-no-hireling-id, no-stress-touch, wound-flag-orthogonal, defeat-without-wound), `tests/handlers/test_dungeon_select.py` (~4 tests), `tests/handlers/test_retreat_to_hamlet.py` (~6 tests — wounded_boss orthogonal coverage), `tests/server/test_rest_hub_endpoint.py` (item 2's 5 plus this plan's 5 = 10 tests), `tests/integration/test_sunden_hub_e2e.py` (1 test), `tests/telemetry/test_session_spans.py` (~5 tests), `tests/protocol/test_messages.py` (4 added) — all green.
- `tests/handlers/test_connect.py` — leaf-world regression tests still green; new hub-view + mid-delve-resume tests green.
- `just server-lint` clean on every touched file.
- The 44 pre-existing test-sweep failures: any that flip green incidentally (because `caverns_three_sins` is now delvable) are noted in the PR description for the test-sweep plan author. Any that *regress* (newly fail) is a release-blocker.
- `just up` boots; the curl + websocat smoke walk in Task 14 step 4 completes successfully end-to-end.
- PR open against `slabgorb/sidequest-server` `develop`. Sequenced after item 2's PR — this plan's PR description lists the dependency explicitly.
- Item 4b (UI plan), item 3 (stress), items 5–7 (narrator zones), and the 44-test sweep can all now be drafted on top of this engine surface.
