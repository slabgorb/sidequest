# Beneath Sünden — Plan 7 Session-Integration DO-NOT-SHIP Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Genuinely close ADR-106 — make a real `caverns_and_claudes` / `beneath_sunden` session grow its dungeon, verified not asserted — by authoring the 4 missing genre-level tropes, driving the keystone with the real `GenrePack` (deleting the `_attach_pack` fabrication that masked the gap), and fixing the cross-session double-register residual in the seam we own.

**Architecture:** Spec §14 resolution. (A) Author 4 trope definitions in genre-level `sidequest-content/genre_packs/caverns_and_claudes/tropes.yaml` (the only file the materializer resolves `trope_id` against — verified by code-trace `connect.py:400 → pack_tropes → setpiece_attach.py:411-435`). (C) Rewrite the two session test files to drive the real `GenreLoader(DEFAULT_GENRE_PACK_SEARCH_PATHS).load("caverns_and_claudes")` pack. (D) Add a process-level save-keyed dedup guard inside `session_integration.py` (the hard constraint forbids touching `lookahead_worker.py` / `frontier_hook.py`). (E) Gated final adversarial review + ADR-106 CLOSED recording.

**Tech Stack:** Python 3.12, FastAPI, stdlib `sqlite3`, `uv` + `pytest` (`asyncio_mode="auto"`, `--timeout=30`), YAML genre packs (pydantic `TropeDefinition` is the schema gate). Two repos: `sidequest-content` (tropes) + `sidequest-server` (tests/guard).

**Spec:** `docs/superpowers/specs/2026-05-17-beneath-sunden-plan-7-session-integration-design.md` §14 (authoritative; commits `162d85b` / `52536df`). §14.B (visual_style port) is OUT — handled elsewhere.

**Repos / branches:**
- `sidequest-content`: **new** branch `feat/beneath-sunden-trope-gap-fix` off `develop` — Task 1 only. Per the subrepo-branch discipline, create it **before** dispatching any content implementer; content merges first/with the server branch (the server keystone reads the sibling content checkout at `parents[3]/sidequest-content`).
- `sidequest-server`: **existing** branch `feat/beneath-sunden-plan-7-session-integration` (tip `ffff55c6`, off merged develop `bcabbf6`) — Tasks 2–5.
- Plan/spec docs: oq-1 orchestrator branch `docs/beneath-sunden-plan-7-session-integration-spec`.

**Test runner facts:** From `/Users/slabgorb/Projects/oq-1/sidequest-server`: `uv run pytest <path> -v`. `asyncio_mode="auto"` — `async def test_*` needs **no** decorator. Per-test 30s timeout. The only mocked seam is the injected SDK curate fake (`_reflecting_sdk_client`); never a real `claude`/network call. Lint: `uv run ruff check .`. Type: `uv run pyright`. The real pack loads in tests via `from sidequest.genre.loader import GenreLoader, DEFAULT_GENRE_PACK_SEARCH_PATHS` (established pattern: `tests/server/test_encounter_lifecycle.py:12`).

---

## Verified blocker (the thing this plan fixes)

`connect.py:~400` → `genre_pack = GenreLoader().load(genre_slug)` (genre-level pack) → passed straight through as `pack_tropes`. `setpiece_attach.py:411-413`:

```python
pack_tropes_by_id: dict[str, Any] = {
    t.id: t for t in getattr(pack_tropes, "tropes", []) if t.id is not None
}
```

resolves against the genre-level `genre_packs/caverns_and_claudes/tropes.yaml`, which defines only `{the_keeper_stirs, extraction_panic, hireling_mutiny, the_deeper_dark}`. PASS-1 (`setpiece_attach.py:426-438`) raises `ValueError("trope_id {!r} not found in pack — content authoring bug (add it to tropes.yaml ...)")`. The 5 Plan-4 genre-level themes reference 4 trope_ids defined nowhere; `drowned_cavern` (the depth-0 entrance theme) is hit first by the bootstrap → connect aborts. The 7-task tests are false-green only because they inject `_attach_pack(*fabricated_ids)` (`tests/dungeon/test_materializer.py:1799` → `SimpleNamespace(tropes=[SimpleNamespace(id=t)…])`).

| trope_id | theme (set-piece) | set-piece params | depth_band |
|---|---|---|---|
| `the_thing_that_followed_you_down` | `drowned_cavern` (`the_siphon`) | `{from_region: surface}` | `{min: 0.0, max: 60.0}` — **entrance** |
| `the_keeper_notices_the_disturbance` | `bone_crypt` (`the_false_floor`) | `{patience: low}` | `{min: 30.0, max: 130.0}` |
| `priest_demands_a_sacrifice` | `sunless_temple` (`the_altar_that_waits`) | `{countdown_expansions: 2}` | `{min: 45.0, max: null}` |
| `the_resource_clock_you_can_see` | `labyrinth_trap` (`the_only_path`) | `{resource: light}` | `{min: 60.0, max: null}` |

`quest_components` (`deny_or_feed_the_altar`, `find_the_unlit_way_out`) need **no** authoring — re-verified: `setpiece_attach.py` (L488-489, L584) has no quest registry; quest_id is thread-provenance only.

---

## File Structure

| Path | Repo | Create/Modify | Responsibility |
|---|---|---|---|
| `genre_packs/caverns_and_claudes/tropes.yaml` | content | Modify (append 4) | The 4 missing genre-level trope definitions (Task 1). |
| `tests/dungeon/test_session_integration.py` | server | Modify | Drive the real `GenrePack`; delete `_pack()`/`_attach_pack`; add concurrent-same-save raise test (Tasks 2, 4). |
| `tests/dungeon/test_session_lifecycle_wiring.py` | server | Modify | Drive the real `GenrePack`; delete `_attach_pack`/`_ALL_REAL_TROPE_IDS`; add §10(f) assertions (Tasks 3, 4). |
| `sidequest/dungeon/session_integration.py` | server | Modify | Process-level save-keyed dedup guard (`_save_key`, `_ATTACHED_SAVES`); raise-loud on concurrent same-save attach; detach clears the key (Task 4). |
| parent megadungeon spec + this spec | oq-1 | Modify | Gated ADR-106 CLOSED recording (Task 5). |

**Untouched (hard constraint):** `sidequest/dungeon/lookahead_worker.py`, `sidequest/dungeon/frontier_hook.py`. `register_lookahead_worker` builds a new handle→new bound `_observer` each call; `frontier_hook.register_frontier_observer` dedups by `observer not in _OBSERVERS` (identity) → cross-session double-register. The fix is the save-keyed guard in the seam we own, not a worker change.

---

## Task 0: Branch setup (run once, before any implementer)

- [ ] **Step 1: Create the content feature branch off develop (BEFORE any content implementer)**

```bash
git -C /Users/slabgorb/Projects/oq-1/sidequest-content fetch origin --quiet
git -C /Users/slabgorb/Projects/oq-1/sidequest-content checkout develop
git -C /Users/slabgorb/Projects/oq-1/sidequest-content pull --ff-only origin develop
git -C /Users/slabgorb/Projects/oq-1/sidequest-content checkout -b feat/beneath-sunden-trope-gap-fix
git -C /Users/slabgorb/Projects/oq-1/sidequest-content log -1 --format='%h %s'
```

Expected: on branch `feat/beneath-sunden-trope-gap-fix`, a clean develop tip.

- [ ] **Step 2: Confirm the server branch is the built one**

```bash
git -C /Users/slabgorb/Projects/oq-1/sidequest-server rev-parse --abbrev-ref HEAD
git -C /Users/slabgorb/Projects/oq-1/sidequest-server log -1 --format='%h %s'
```

Expected: branch `feat/beneath-sunden-plan-7-session-integration`, HEAD `ffff55c6 test(dungeon): keystone session-lifecycle wiring …`. Do **not** branch or reset; Tasks 2–5 commit onto this branch.

---

## Task 1: Author the 4 missing genre-level tropes (`sidequest-content`)

**Files:**
- Modify: `genre_packs/caverns_and_claudes/tropes.yaml` (append 4 list items after the existing `the_deeper_dark`, end of file ~L213)

**Authoring discipline:** dispatch the **writer** agent (prose: `description`, `narrative_hints`, `escalation[].event`, voice) and the **scenario-designer** agent (mechanics: `category`, `triggers`, `tension_level`, `escalation[].at/stakes`, `passive_progression`, set-piece-param fidelity), two-stage reviewed (spec → code-quality). The YAML below is the **concrete faithful bar** — agents meet or improve it; they must NOT regress it to a stub. Match the existing house style exactly (folded `>-` scalars, 2-space indent, the field set used by `the_keeper_stirs` / `extraction_panic`: `id, name, description, category, triggers, narrative_hints, tension_level, resolution_hints, tags, escalation[at/event/npcs_involved/stakes], passive_progression{rate_per_turn,rate_per_day,accelerators}`). Tone: grave, lethal, Moria-as-tragedy, no winking (beneath_sunden `world.yaml`). Schema authority: `sidequest/genre/models/tropes.py::TropeDefinition` (`extra="forbid"` — no unknown keys). Each escalation array must be monotonic in `at` (0.0→1.0) and end in a terminal stake.

- [ ] **Step 1: Append the 4 tropes to `genre_packs/caverns_and_claudes/tropes.yaml`**

```yaml

- id: the_thing_that_followed_you_down
  name: The Thing That Followed You Down
  description: >-
    Something came down with you, or after you, and it is between you and
    the rope now. It does not hurry. It has the patience of a thing that
    knows the only way out is back past it.
  category: tension
  triggers:
    - descent from the surface or a shallower level
    - a set-piece that names what followed (the_siphon)
    - the party splits or a straggler falls behind
    - light fails at the rear of the column
  narrative_hints:
    - wet drag-marks in the dust that lead the way you came, then stop
    - the rearguard's torch keeps finding nothing, and keeps looking
    - a sound from behind that matches your pace exactly, then does not
  tension_level: 0.7
  resolution_hints:
    - turn and face it in light and numbers before it picks the ground
    - collapse the way behind you and accept there is no going back that way
    - give it the straggler it is pacing and live with having done so
  tags: [pursuit, surface, dark, tension, escalation]
  escalation:
    - at: 0.25
      event: >-
        The rear of the column finds sign that did not come from the party:
        a print half in a print, a smear still wet on stone the party passed
        dry. Nothing is there when the light turns. Nothing is ever there
        when the light turns.
      npcs_involved: []
      stakes: The party is being followed. The rearguard cannot be spared now.
    - at: 0.5
      event: >-
        It takes something at the edge of the light — a torch, a pack, a
        hireling who lagged one step too far. No struggle anyone sees. Just
        a gap in the column where someone was, and the dark closing it.
      npcs_involved: []
      stakes: A loss the party cannot replace this deep. The rope is now on the far side of it.
    - at: 1.0
      event: >-
        It stops pacing and waits in the only passage that goes up, in the
        place it chose, on the ground it chose. There is no route around
        that it has not already counted. It will be met, or the party will
        not surface.
      npcs_involved: []
      stakes: Confront it on its ground or do not leave the deep. There is no third door.
  passive_progression:
    rate_per_turn: 0.03
    rate_per_day: 0.0
    accelerators:
      - descent
      - dark
      - straggler
      - split

- id: the_keeper_notices_the_disturbance
  name: The Keeper Notices the Disturbance
  description: >-
    Not the slow, ambient waking of the whole deep — this is local, and it
    is about you specifically. Something registered what the party did here
    and has decided, with very little patience, to attend to it.
  category: tension
  triggers:
    - a sprung trap, forced floor, or broken seal in a guarded place
    - disturbing a marked grave, niche, or interred thing
    - loud work — digging, prying, breaking — in a still place
    - returning to a place the party already disturbed
  narrative_hints:
    - the dust the party raised has been smoothed flat again, recently
    - a thing left disturbed is found set right, and nothing did it
    - the next room is arranged as if it expected exactly this approach
  tension_level: 0.65
  resolution_hints:
    - leave the disturbed place and do not come back through it
    - move quiet and quick before the attention finishes orienting
    - meet what it sends here rather than carry it deeper
  tags: [keeper, attention, trap, tension, escalation]
  escalation:
    - at: 0.3
      event: >-
        What the party broke or sprung has been undone behind them —
        re-set, re-closed, re-laid, patiently and without witness. The
        message is not a threat. It is bookkeeping.
      npcs_involved: []
      stakes: The deep is correcting the party's work faster than the party can do it. Stealth is gone here.
    - at: 0.6
      event: >-
        The hazards in this place stop being incidental. A pit is where the
        party's own route would have put a foot. A fall of stone waits on
        the path back, not the path on. It is reading the party's habits.
      npcs_involved: []
      stakes: Traps now target the party's patterns specifically. Improvise the route or be where it expects.
    - at: 1.0
      event: >-
        The disturbed place commits to the party fully — every remaining
        seam, slab, and counterweight in it working at once, against these
        intruders, here, now, until the place is still again.
      npcs_involved: []
      stakes: The set-piece turns wholly hostile. Clear it or be cleared from it.
  passive_progression:
    rate_per_turn: 0.04
    rate_per_day: 0.0
    accelerators:
      - breach
      - loud
      - return
      - grave

- id: priest_demands_a_sacrifice
  name: The Priest Demands a Sacrifice
  description: >-
    The altar has been counting since long before the party arrived and it
    does not pause for deliberation. It does not want worship. It wants one
    of you, or one of what you carry that bleeds, and it has set a price
    that comes due whether or not the party agrees to pay it.
  category: conflict
  triggers:
    - entering a temple, altar, or offering-place that is kept ready
    - the altar set-piece begins its count (the_altar_that_waits)
    - refusing, defiling, or trying to leave the offering unmade
    - a death or grievous wound near the altar
  narrative_hints:
    - the offering-channels are dry, scrubbed, and recently made ready
    - the count is somewhere being kept, and it is not slowing for you
    - the acolytes do not bar the way out; they do not need to
  tension_level: 0.8
  resolution_hints:
    - feed the altar what it asks and carry what that costs the party out
    - deny it and survive the two expansions it takes to collect regardless
    - destroy the altar before the count completes, if it can be destroyed
  tags: [sacrifice, temple, dilemma, countdown, escalation]
  escalation:
    - at: 0.34
      event: >-
        The demand is made plain — not in words the party needs translated,
        but in the way the place arranges itself toward the stone. One
        offering. The party has perhaps two expansions of deep before it is
        no longer asking.
      npcs_involved: []
      stakes: The choice is named. Deny-or-feed is now a clock, not a question.
    - at: 0.67
      event: >-
        Unfed, the temple stops waiting politely. Ways close that were open.
        What the party needs is on the far side of the altar. The price has
        not changed; only the cost of refusing it has.
      npcs_involved: []
      stakes: Refusal is now actively expensive. The altar collects in passage tolls until it collects in full.
    - at: 1.0
      event: >-
        The count completes. The altar takes its offering — the one the
        party chose, or the one it chooses for them, and it does not choose
        kindly. What is fed is not given back. What is denied is taken
        anyway, and remembered.
      npcs_involved: []
      stakes: Terminal. A sacrifice is made by the party or by the temple; either way the deep keeps it.
  passive_progression:
    rate_per_turn: 0.05
    rate_per_day: 0.0
    accelerators:
      - refusal
      - defile
      - bloodshed
      - delay

- id: the_resource_clock_you_can_see
  name: The Resource Clock You Can See
  description: >-
    The cruelty of this place is that it shows you the math. There is no
    shortcut and there never was; the only path is exactly as long as it is,
    and the light the party is burning to walk it is visibly, countably,
    running out faster than the path is.
  category: tension
  triggers:
    - committing to a route with no branch and no return budgeted
    - a set-piece that makes the drain legible (the_only_path)
    - rationing the named resource (light, water, air, rope)
    - losing or spending a unit of that resource to a hazard
  narrative_hints:
    - tally-scratches on the wall climb into the hundreds, then stop unfinished
    - the party can count the torches left and count the turnings left
    - the two counts are not the same count, and everyone has done the sum
  tension_level: 0.8
  resolution_hints:
    - spend everything else to protect the one resource the clock measures
    - find the unlit way the maze hides rather than outlast the maze
    - accept a loss now to keep the clock from reaching zero in the dark
  tags: [resource, maze, light, attrition, escalation]
  escalation:
    - at: 0.3
      event: >-
        The path proves longer than it looked and does not branch. The
        party does the arithmetic without being asked: the resource will
        not reach the end at this rate. Everyone has now done it.
      npcs_involved: []
      stakes: The drain is legible and adverse. Rationing starts here or it starts too late.
    - at: 0.6
      event: >-
        Rationing fails the way rationing fails — not all at once, but in a
        skipped torch, a dry skin, a stretch walked darker than is safe to
        save what cannot be saved. The clock does not slow for thrift.
      npcs_involved: []
      stakes: Thrift is no longer enough. Only a different route or a hard loss changes the sum.
    - at: 1.0
      event: >-
        The resource reaches zero with path still ahead. The maze does not
        end because the light did. What happens here happens in the dark,
        on the party's hands, against the turnings, by feel and by count.
      npcs_involved: []
      stakes: Terminal attrition. Cross the rest blind and lessened, or do not cross it.
  passive_progression:
    rate_per_turn: 0.05
    rate_per_day: 0.0
    accelerators:
      - dark
      - lost
      - slow
      - waste
```

- [ ] **Step 2: Validate the real loader resolves all 4 ids (schema gate)**

Run:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run python -c "
from sidequest.genre.loader import GenreLoader, DEFAULT_GENRE_PACK_SEARCH_PATHS as D
gp = GenreLoader(D).load('caverns_and_claudes')
ids = {t.id for t in gp.tropes}
need = {'the_thing_that_followed_you_down','the_keeper_notices_the_disturbance','priest_demands_a_sacrifice','the_resource_clock_you_can_see'}
missing = need - ids
assert not missing, f'still missing: {sorted(missing)}'
print('OK genre tropes:', sorted(ids))
"
```

Expected: `OK genre tropes: [...]` listing 8 ids (the original 4 + the new 4). A pydantic `ValidationError` here means a field violates `TropeDefinition` (`extra="forbid"`) — fix the YAML, do not relax the schema.

- [ ] **Step 3: Regression — existing trope + dungeon suites still green**

Run:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/ -k "trope or genre_loader" -q
```

Expected: green. If a test asserts an exact genre trope **count/snapshot** for `caverns_and_claudes`, that snapshot is now stale — fix it forward to the new set (per `feedback_dont_revert_features`: fit the test to the intended new shape; never delete the 4 tropes to make a stale count pass).

- [ ] **Step 4: Commit (content branch)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git add genre_packs/caverns_and_claudes/tropes.yaml
git commit -m "feat(caverns_and_claudes): author 4 genre-level set-piece tropes (Plan 7 §14.A)

the_thing_that_followed_you_down / the_keeper_notices_the_disturbance /
priest_demands_a_sacrifice / the_resource_clock_you_can_see — referenced by
the Plan-4 genre-level themes' set-pieces, defined nowhere until now (the
verified DO-NOT-SHIP content gap). Faithful to TropeDefinition schema +
the_keeper_stirs voice + beneath_sunden Moria-as-tragedy tone."
git log -1 --format='%h %s'
```

---

## Task 2: Real-pack rewrite — `test_session_integration.py`

**Files:**
- Modify: `tests/dungeon/test_session_integration.py` (replace `_pack()` ~L42-55; repoint its two call sites L95, L127)

Deletes the `_attach_pack` fabrication (the No-Stubbing violation, spec §14.C) and drives the real loaded pack. Depends on Task 1 content being present in the sibling checkout `/Users/slabgorb/Projects/oq-1/sidequest-content` (working tree — it need not be merged for local green).

- [ ] **Step 1: Replace `_pack()` with the real loader**

In `tests/dungeon/test_session_integration.py`, delete the entire `_pack()` function (L42-55) and replace with:

```python
def _real_pack() -> Any:
    """The REAL loaded caverns_and_claudes GenrePack — NOT _attach_pack.

    Spec §14.C: the keystone must prove a real session grows the dungeon.
    The materializer resolves set-piece trope_id against this pack's
    genre-level .tropes (verified: connect.py:400 -> pack_tropes ->
    setpiece_attach.py:411-413). After Plan 7 §14.A the 4 set-piece tropes
    are authored in genre_packs/caverns_and_claudes/tropes.yaml, so the
    real pack resolves them with no fabrication.
    """
    from sidequest.genre.loader import (
        DEFAULT_GENRE_PACK_SEARCH_PATHS,
        GenreLoader,
    )

    return GenreLoader(DEFAULT_GENRE_PACK_SEARCH_PATHS).load("caverns_and_claudes")
```

- [ ] **Step 2: Repoint the two call sites**

In `test_attach_seeds_and_registers_then_detach_unregisters` (was L95) and `test_attach_is_idempotent_reuses_persisted_seed` (was L127), change `genre_pack=_pack()` → `genre_pack=_real_pack()`.

- [ ] **Step 3: Run it — must pass for real**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_session_integration.py -v`
Expected: PASS (4 passed). The bootstrap now resolves `the_thing_that_followed_you_down` (drowned_cavern entrance) against the real pack. If it fails with `trope_id ... not found in pack`, Task 1 content is not on disk in the sibling checkout — fix Task 1, do not re-add `_attach_pack`.

- [ ] **Step 4: Lint + commit (server branch)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check tests/dungeon/test_session_integration.py
git add tests/dungeon/test_session_integration.py
git commit -m "test(dungeon): drive session_integration tests with the REAL GenrePack — delete _attach_pack fabrication (Plan 7 §14.C)"
```

---

## Task 3: Real-pack rewrite — `test_session_lifecycle_wiring.py` (keystone)

**Files:**
- Modify: `tests/dungeon/test_session_lifecycle_wiring.py` (delete `_ALL_REAL_TROPE_IDS` L22-27 + the comment block L10-21; replace the `_attach_pack(*_ALL_REAL_TROPE_IDS)` call L100 with the real pack)

- [ ] **Step 1: Delete the fabricated-id block and add the real loader**

In `tests/dungeon/test_session_lifecycle_wiring.py`, delete lines L10-27 (the `# The FULL set …` comment through the closing `)` of `_ALL_REAL_TROPE_IDS`). Add, after the imports (after `from sidequest.dungeon import frontier_hook`):

```python


def _real_pack() -> Any:
    """The REAL loaded caverns_and_claudes GenrePack (spec §14.C).

    No _attach_pack: the keystone genuinely proves a real session grows
    the dungeon. The 4 set-piece tropes are authored in the genre-level
    tropes.yaml (Plan 7 §14.A); the real pack resolves them.
    """
    from sidequest.genre.loader import (
        DEFAULT_GENRE_PACK_SEARCH_PATHS,
        GenreLoader,
    )

    return GenreLoader(DEFAULT_GENRE_PACK_SEARCH_PATHS).load("caverns_and_claudes")
```

- [ ] **Step 2: Repoint the keystone call site + drop the now-unused import**

In `test_session_lifecycle_registers_worker_and_dungeon_grows`, change the import line `from tests.dungeon.test_materializer import _attach_pack, _reflecting_sdk_client` → `from tests.dungeon.test_materializer import _reflecting_sdk_client`, and change `genre_pack=_attach_pack(*_ALL_REAL_TROPE_IDS)` → `genre_pack=_real_pack()`.

- [ ] **Step 3: Run the keystone — must pass for real**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_session_lifecycle_wiring.py -v`
Expected: PASS (1 passed) — bootstrap commits expansion 0+1, a real `snap.apply_world_patch` crossing materializes the next expansion, the `frontier.region_transition` span carries `observers>=1`. If `observers=0` or `trope_id not found`, the wiring/content is the bug — fix forward, never weaken the assertion (it IS the deliverable).

- [ ] **Step 4: Lint + commit (server branch)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check tests/dungeon/test_session_lifecycle_wiring.py
git add tests/dungeon/test_session_lifecycle_wiring.py
git commit -m "test(dungeon): keystone driven by the REAL GenrePack — delete _attach_pack fabrication, genuinely prove ADR-106 (Plan 7 §14.C)"
```

---

## Task 4: Save-keyed residual guard in `session_integration.py` (§14.D)

**Files:**
- Modify: `sidequest/dungeon/session_integration.py` (add `_save_key` + `_ATTACHED_SAVES`; guard in `attach_dungeon_to_session`; clear in `detach_dungeon_from_session`)
- Modify: `tests/dungeon/test_session_integration.py` (add concurrent-same-save raise test)
- Modify: `tests/dungeon/test_session_lifecycle_wiring.py` (add §10(f) assertions)

`lookahead_worker.py` / `frontier_hook.py` are **untouched** (hard constraint). The dedup lives in the seam we own.

- [ ] **Step 1: Add the failing concurrent-same-save test**

Append to `tests/dungeon/test_session_integration.py`:

```python
async def test_concurrent_attach_same_save_raises_loud_then_reattaches_after_detach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§14.D: a second attach for an already-attached save raises loud
    (concurrent sessions on one save would double-register — a contract
    violation, not an upsert). After detach, a fresh attach for that save
    succeeds (sequential reopen is unaffected)."""
    from sidequest.dungeon import session_integration
    from tests.dungeon.test_materializer import _reflecting_sdk_client

    monkeypatch.setattr(
        session_integration, "build_llm_client", _reflecting_sdk_client
    )
    store = _sqlite_store()
    kw = dict(
        store=store,
        snapshot=_snapshot(),
        genre_pack=_real_pack(),
        genre_slug="caverns_and_claudes",
        world_slug="beneath_sunden",
        world_dir=_beneath_sunden_world_dir(),
    )
    h1 = await session_integration.attach_dungeon_to_session(**kw)
    assert h1 is not None
    assert frontier_hook.registered_observer_count() == 1

    with pytest.raises(RuntimeError, match="already attached"):
        await session_integration.attach_dungeon_to_session(
            **dict(kw, snapshot=_snapshot())
        )
    # The violation path registered NOTHING extra.
    assert frontier_hook.registered_observer_count() == 1

    await session_integration.detach_dungeon_from_session(h1)
    assert frontier_hook.registered_observer_count() == 0

    # Sequential reopen of the same save still works (key was cleared).
    h2 = await session_integration.attach_dungeon_to_session(
        **dict(kw, snapshot=_snapshot())
    )
    assert h2 is not None
    assert frontier_hook.registered_observer_count() == 1
    await session_integration.detach_dungeon_from_session(h2)
    assert frontier_hook.registered_observer_count() == 0
```

- [ ] **Step 2: Run it — verify it fails (no guard yet)**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_session_integration.py::test_concurrent_attach_same_save_raises_loud_then_reattaches_after_detach -v`
Expected: FAIL — `DID NOT RAISE RuntimeError` (the second attach currently double-registers → `registered_observer_count() == 2`).

- [ ] **Step 3: Add the guard to `session_integration.py`**

In `sidequest/dungeon/session_integration.py`, add after the `_SEED_BITS = 63` line (after L44):

```python

# §14.D cross-session double-register guard. register_lookahead_worker
# builds a NEW handle -> NEW bound _observer each call, so frontier_hook's
# identity-dedup does NOT hold across sessions: two concurrent sessions on
# one save would double-register and double-materialize. The hard
# constraint forbids touching lookahead_worker.py/frontier_hook.py, so the
# guard lives here, in the seam we own — keyed by save identity. Concurrent
# attach for an already-attached save is a contract violation, not a silent
# upsert (No Silent Fallbacks). The real playgroup runs ONE shared session
# per save (submit-and-wait); sequential reopen clears the key in detach.
_ATTACHED_SAVES: dict[str, LookaheadWorkerHandle] = {}


def _save_key(conn: Any) -> str:
    """Stable per-save identity. Real saves: the sqlite main DB file path
    (two WS sessions on one save file open distinct connections to the
    SAME path -> same key -> guard fires). In-memory stores have no file
    -> fall back to the connection object's id (each in-memory store is a
    distinct connection, never sharing a file -> no false collision).
    """
    try:
        row = conn.execute("PRAGMA database_list").fetchone()
    except Exception as exc:  # pragma: no cover - sqlite always supports this
        raise RuntimeError(
            f"could not resolve save identity for the dungeon attach guard: {exc}"
        ) from exc
    # PRAGMA database_list row: (seq, name, file). file is '' for :memory:.
    db_file = row[2] if row is not None and len(row) >= 3 else ""
    return db_file if db_file else f"mem:{id(conn)}"
```

Then in `attach_dungeon_to_session`, replace the existing block:

```python
    conn = store.connection()
    persistence = DungeonStore(conn)
    persistence.ensure_schema()  # outside any txn (executescript implicit COMMIT)
```

with:

```python
    conn = store.connection()
    save_key = _save_key(conn)
    if save_key in _ATTACHED_SAVES:
        raise RuntimeError(
            f"a look-ahead worker is already attached for save {save_key!r} "
            "— concurrent sessions on one save would double-register and "
            "double-materialize the dungeon. This is a contract violation, "
            "not an upsert (No Silent Fallbacks); the playgroup runs one "
            "shared session per save. detach the prior session first."
        )
    persistence = DungeonStore(conn)
    persistence.ensure_schema()  # outside any txn (executescript implicit COMMIT)
```

And replace the final `return register_lookahead_worker(...)` block:

```python
    return register_lookahead_worker(
        persistence=persistence,
        bundle=bundle,
        palette=palette,
        pack_tropes=genre_pack,
        claude_client=claude_client,
        campaign_seed=campaign_seed,
    )
```

with:

```python
    handle = register_lookahead_worker(
        persistence=persistence,
        bundle=bundle,
        palette=palette,
        pack_tropes=genre_pack,
        claude_client=claude_client,
        campaign_seed=campaign_seed,
    )
    # Claim the save AFTER a successful register: a bootstrap/register
    # failure must leave no key behind (a later retry must be able to
    # attach). save-is-truth.
    _ATTACHED_SAVES[save_key] = handle
    return handle
```

- [ ] **Step 4: Clear the key in `detach_dungeon_from_session`**

Replace the body of `detach_dungeon_from_session`:

```python
    if handle is None:
        return
    handle.unregister()
    await handle.drain()
```

with:

```python
    if handle is None:
        return
    # Clear the §14.D save claim (reverse-lookup by handle identity — the
    # registry holds exactly one entry per live save; detach takes only the
    # handle, and LookaheadWorkerHandle is untouchable per the hard
    # constraint, so we cannot stash the key on it).
    for key, claimed in list(_ATTACHED_SAVES.items()):
        if claimed is handle:
            del _ATTACHED_SAVES[key]
    handle.unregister()
    await handle.drain()
```

- [ ] **Step 5: Run the new test + the full session_integration file**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_session_integration.py -v`
Expected: PASS (5 passed — the 4 prior + the new concurrent-same-save test). The idempotency test still passes (sequential attach→detach→attach: detach clears the key).

- [ ] **Step 6: Add the §10(f) assertions to the keystone**

In `tests/dungeon/test_session_lifecycle_wiring.py`, inside `test_session_lifecycle_registers_worker_and_dungeon_grows`, immediately **after** the `observers>=1` span assertion block (after the `assert any(... "ADR-106 lie-detector signal ...")` closes, before the `finally:`), add:

```python

        # §10(f): a second attach for the SAME live save raises loud and
        # adds no second observer (the §14.D save-keyed dedup — the merged
        # worker's identity-dedup does NOT hold across sessions).
        with pytest.raises(RuntimeError, match="already attached"):
            await session_integration.attach_dungeon_to_session(
                store=store,
                snapshot=GameSnapshot(
                    genre_slug="caverns_and_claudes",
                    world_slug="beneath_sunden",
                ),
                genre_pack=_real_pack(),
                genre_slug="caverns_and_claudes",
                world_slug="beneath_sunden",
                world_dir=_beneath_sunden_world_dir(),
            )
        assert frontier_hook.registered_observer_count() == 1, (
            "the concurrent-same-save attempt double-registered — the "
            "§14.D save-keyed guard did not hold"
        )
```

- [ ] **Step 7: Run the keystone + full dungeon suite + lint + type**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/dungeon/test_session_lifecycle_wiring.py -v
uv run pytest tests/dungeon/ -q
uv run ruff check sidequest/dungeon/session_integration.py tests/dungeon/test_session_integration.py tests/dungeon/test_session_lifecycle_wiring.py
uv run pyright sidequest/dungeon/session_integration.py
```

Expected: keystone PASS (1 passed, now incl. §10(f)); full dungeon suite PASS; ruff clean; pyright 0 errors on `session_integration.py`. Confirm `lookahead_worker.py` / `frontier_hook.py` are unmodified: `git -C /Users/slabgorb/Projects/oq-1/sidequest-server status --short sidequest/dungeon/lookahead_worker.py sidequest/dungeon/frontier_hook.py` → empty.

- [ ] **Step 8: Commit (server branch)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/dungeon/session_integration.py tests/dungeon/test_session_integration.py tests/dungeon/test_session_lifecycle_wiring.py
git commit -m "feat(dungeon): save-keyed cross-session double-register guard in session_integration (Plan 7 §14.D)

register_lookahead_worker builds a new handle/observer per call so
frontier_hook identity-dedup does not hold across sessions; the seam we
own now refuses a concurrent attach for an already-attached save (raise
loud, No Silent Fallbacks). lookahead_worker.py/frontier_hook.py untouched."
```

---

## Task 5: Final adversarial review + gated ADR-106 closure (§14.E)

**Files:**
- Modify (gated): `docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md` (§10 item 7 + Post-Implementation Corrections) — oq-1 orchestrator
- Modify (gated): `docs/superpowers/specs/2026-05-17-beneath-sunden-plan-7-session-integration-design.md` (§14.E status) — oq-1 orchestrator

- [ ] **Step 1: Full server suite gate**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest -q`
Expected: green except known-unrelated pre-existing failures (verify any failure is NOT in `tests/dungeon/`, `tests/game/`, or a changed module; a dungeon/game failure is in scope — fix forward, never revert the feature or weaken the keystone).

- [ ] **Step 2: Final adversarial whole-impl review against the REAL pack**

Dispatch the `Reviewer` agent (adversarial, read-only) with the full diff of both branches (`sidequest-content feat/beneath-sunden-trope-gap-fix` + `sidequest-server feat/beneath-sunden-plan-7-session-integration` since `bcabbf6`) and spec §14. Reviewer must specifically verify, with evidence (not assertion): (a) the keystone drives the **real** `GenreLoader(...).load("caverns_and_claudes")` with **zero** `_attach_pack`; (b) a real `apply_world_patch` crossing materializes the next expansion and the `frontier.region_transition` span carries `observers>=1`; (c) `lookahead_worker.py`/`frontier_hook.py` are byte-unchanged; (d) the §14.D guard raises loud on concurrent same-save and detach clears it; (e) no stub/silent-fallback. Address every blocking finding (fix forward) and re-run the gate until the Reviewer returns SHIP.

- [ ] **Step 3: GATE — only proceed if the real-pack path genuinely grows the dungeon**

Confirm, from Step 1–2 evidence: keystone green with the real pack, `observers>=1` on a real `frontier.region_transition` span, `max(expansion_id)` grew on a real crossing, Reviewer SHIP. **If any is not genuinely true, STOP — do not record ADR-106 closed, do not push/merge.** Report the gap and await direction.

- [ ] **Step 4: Record ADR-106 CLOSED (only past the gate)**

On the oq-1 orchestrator branch `docs/beneath-sunden-plan-7-session-integration-spec`: in the parent spec `docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md` §10 decomposition item 7 (Plan 7) + that spec's Post-Implementation Corrections appendix, record ADR-106 **CLOSED** with the verifying evidence (the keystone test name + the observed `observers>=1` + the real-crossing expansion growth). Update this spec's §14.E status line to CLOSED. Commit:

```bash
cd /Users/slabgorb/Projects/oq-1
git add docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md docs/superpowers/specs/2026-05-17-beneath-sunden-plan-7-session-integration-design.md
git commit -m "docs(spec): ADR-106 CLOSED — verified real-pack session grows the dungeon (Plan 7 §14.E)"
```

- [ ] **Step 5: Finish the branches**

Announce: "I'm using the finishing-a-development-branch skill to complete this work." **REQUIRED SUB-SKILL:** `superpowers:finishing-a-development-branch`. Coordinate the merge order: `sidequest-content feat/beneath-sunden-trope-gap-fix` merges **first/with** the server branch (the server keystone reads the sibling content checkout). No push/merge before this gate passed. Update memory `[[project_beneath_sunden]]` with the closure + per-task SHAs.

---

## Self-Review

**1. Spec coverage:**
- §14.A author 4 genre-level tropes → Task 1 (full faithful YAML, schema-gated by the real loader). ✔
- §14.B visual_style → explicitly OUT (handled elsewhere); no task. ✔ (intentional, per spec §14.B / §11)
- §14.C real-pack keystone, delete `_attach_pack` → Task 2 (`test_session_integration.py`) + Task 3 (`test_session_lifecycle_wiring.py`). ✔
- §14.D save-keyed residual guard, `lookahead_worker.py`/`frontier_hook.py` untouched → Task 4 (guard + concurrent-same-save test + §10(f) keystone assertions + byte-unchanged check). ✔
- §14.E gated final review + ADR-106 CLOSED recording + finish → Task 5 (explicit GATE step before any closure claim). ✔
- §9 cross-session bullet / §10 (f) → Task 4 Steps 1,6. ✔
- §10 (a)–(e) keystone → already built; Task 3 keeps them, swaps to real pack. ✔
- Subrepo-branch discipline (content branch before content implementers) → Task 0 Step 1. ✔ (`feedback_subrepo_branches`)

**2. Placeholder scan:** No "TBD"/"TODO"/"similar to". Task 1 contains the complete 4-trope YAML (the faithful bar; writer/scenario-designer refine, not stub). Every command has an expected result. Task 5 Steps 3–4 are a hard GATE with explicit stop condition, not a placeholder.

**3. Type/name consistency:** `_real_pack()` defined in Task 2 (test_session_integration) and independently in Task 3 (test_session_lifecycle_wiring) — each file gets its own (test files don't cross-import helpers except via `tests.dungeon.test_materializer`); both use the identical `GenreLoader(DEFAULT_GENRE_PACK_SEARCH_PATHS).load("caverns_and_claudes")`. `_save_key`/`_ATTACHED_SAVES` defined Task 4 Step 3, cleared Step 4, asserted by Step 1 test + Step 6 keystone. `RuntimeError` match string `"already attached"` is consistent across the guard message (Step 3), the unit test (Step 1), and the keystone assertion (Step 6). `register_lookahead_worker` kwargs unchanged from the built code (read from `session_integration.py`). The 4 trope ids are identical in Task 1 YAML, Task 1 Step 2 validation set, and the verified-blocker table.

**Known residual to verify at execution (explicit in-task steps, not placeholders):** Task 2/3 depend on Task 1 content being on disk in the sibling `sidequest-content` checkout (stated; the failure mode and the no-`_attach_pack`-fallback rule are called out in Task 2 Step 3 / Task 3 Step 3). Task 1 Step 3 flags fix-forward for any stale genre-trope-count snapshot test.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-17-beneath-sunden-plan-7-session-integration-resolution.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage (spec → code-quality) review between tasks; Task 1 uses the writer + scenario-designer specialists; Task 5 Step 2 uses the Reviewer. This is the Plan 7 discipline the spec calls for.
2. **Inline Execution** — execute tasks in this session via executing-plans with checkpoints.

Which approach?
