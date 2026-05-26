# Player Portrait Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let character creation present a grid of pre-generated sample faces (set against world locations) for the player to pick as their PC avatar, persisted on the character.

**Architecture:** Pickers are `type: player_picker` entries in each world's existing `portrait_manifest.yaml` (no new file/catalog). The server adds a `portrait_ref` field to `Character`, a REST endpoint to list pickers, and a `pick_portrait` step interposed at the single `_next_message` chokepoint right before the chargen confirmation summary (the builder's Rust-parity phase machine is untouched). The daemon gains a montage-guarded `portrait_in_location` camera preset; portrait-against-a-location is otherwise already wired (`RenderTarget.background` + `_resolve_location`). The UI adds a `PortraitPanel` grid with soft-suggest. This is the **mechanism only** — no portraits are authored or rendered by this plan.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 (server), Python / Pydantic (daemon), React + TypeScript + Vitest (ui), pytest (server/daemon).

**Spec:** `docs/superpowers/specs/2026-05-26-player-portrait-selection-design.md` (Epic 66).

---

## Repo Topology & Branch Setup

This plan touches four repos. Per `repos.yaml`: orchestrator (`.`) → base `main`; `sidequest-server`, `sidequest-ui`, `sidequest-daemon` → base `develop`. **Create a feature branch in each repo before its first task** (subrepo branches are independent of the orchestrator — create them up front or commits land on `develop`).

- [ ] **Task 0: Create feature branches**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && git checkout develop && git pull && git checkout -b feat/portrait-selection
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon && git checkout develop && git pull && git checkout -b feat/portrait-in-location
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && git checkout develop && git pull && git checkout -b feat/portrait-picker
cd /Users/slabgorb/Projects/oq-1 && git checkout main && git pull && git checkout -b feat/portrait-gen-backdrop
```

Expected: four branches created, each tracking its repo's base.

---

## File Structure

**sidequest-server** (`feat/portrait-selection`)
- Modify `sidequest/game/character.py` — add `portrait_ref` field
- Modify `sidequest/genre/models/pack.py` — add picker fields to `PortraitManifestEntry`
- Modify `sidequest/server/rest.py` — add `GET /api/chargen/portraits/{genre}/{world}`
- Modify `sidequest/telemetry/spans/chargen.py` — add span constant
- Modify `sidequest/server/session_state.py` — add `_SessionData` portrait fields
- Modify `sidequest/server/websocket_session_handler.py` — interpose `pick_portrait`, apply `portrait_ref`
- Modify `sidequest/handlers/character_creation.py` — dispatch `portrait_confirm`
- Modify `sidequest/cli/validate/pack.py` — picker validation
- Tests under `tests/`

**sidequest-daemon** (`feat/portrait-in-location`)
- Modify `sidequest_daemon/media/recipes.py` — add `CameraPreset.portrait_in_location`
- Modify `cameras.yaml` — add preset prose
- Modify `sidequest_daemon/media/prompt_composer.py` — auto-select preset when portrait+background
- Modify `sidequest_daemon/media/workers/zimage_mlx_worker.py` — thread `background` into portrait `RenderTarget`
- Modify `sidequest_daemon/media/daemon.py` — read `background` param into the cue
- Test `tests/test_composer.py`

**orchestrator scripts** (`feat/portrait-gen-backdrop`)
- Modify `scripts/render_common.py` — `send_render` accepts `background`
- Modify `scripts/generate_portrait_images.py` — pass `backdrop_poi` as `where:` ref for pickers

**sidequest-ui** (`feat/portrait-picker`)
- Modify `src/types/payloads.ts` — picker payload fields
- Create `src/components/CharacterCreation/PortraitPanel.tsx`
- Modify `src/components/CharacterCreation/CharacterCreation.tsx` — `pick_portrait` branch
- Modify `src/App.tsx` — fetch pickers, pass genre/world
- Tests under `src/components/CharacterCreation/__tests__/`

---

## Task 1: Add `portrait_ref` to the Character model (server)

**Files:**
- Modify: `sidequest-server/sidequest/game/character.py` (after `current_room`, ~line 126)
- Test: `sidequest-server/tests/game/test_character.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/game/test_character.py`:

```python
def test_portrait_ref_roundtrip_and_defaults_none():
    """portrait_ref defaults to None and survives a JSON round-trip."""
    c = make_test_character()
    assert c.portrait_ref is None
    c2 = c.model_copy(update={"portrait_ref": "picker_hegemonic_officer_f01"})
    back = Character.model_validate_json(c2.model_dump_json())
    assert back.portrait_ref == "picker_hegemonic_officer_f01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_character.py::test_portrait_ref_roundtrip_and_defaults_none -v`
Expected: FAIL — `Character` has no attribute/field `portrait_ref` (or `model_copy` update rejected because `extra="forbid"`).

- [ ] **Step 3: Add the field**

In `character.py`, immediately after the `current_room: str | None = None` field (line 126) and before the `@field_validator("backstory")` block:

```python
    # Player-chosen avatar portrait slug (Epic 66), matching the picker
    # entry's `id` (e.g. "picker_hegemonic_officer_f01") and the rendered
    # PNG filename. None when the player skipped the picker or the world
    # ships no sample portraits. Cosmetic only.
    portrait_ref: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/test_character.py::test_portrait_ref_roundtrip_and_defaults_none -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && git add sidequest/game/character.py tests/game/test_character.py
git commit -m "feat(66): add Character.portrait_ref field"
```

---

## Task 2: Add picker fields to PortraitManifestEntry (server)

`PortraitManifestEntry` is `extra="ignore"`, so unknown keys are silently dropped — picker metadata the endpoint serves must be real fields.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/pack.py:97-116`
- Test: `sidequest-server/tests/genre/test_pack_models.py` (create if absent)

- [ ] **Step 1: Write the failing test**

Create/append `tests/genre/test_pack_models.py`:

```python
from sidequest.genre.models.pack import PortraitManifestEntry


def test_portrait_manifest_entry_picker_fields():
    """player_picker entries carry id/culture/archetype/sex/backdrop_poi."""
    e = PortraitManifestEntry.model_validate(
        {
            "name": "Hegemony Officer",
            "type": "player_picker",
            "id": "picker_hegemonic_officer_f01",
            "culture": "hegemonic",
            "archetype": "ruler",
            "sex": "female",
            "backdrop_poi": "customs_concourse",
            "appearance": "stern, silver-templed",
        }
    )
    assert e.character_type == "player_picker"
    assert e.id == "picker_hegemonic_officer_f01"
    assert e.culture == "hegemonic"
    assert e.archetype == "ruler"
    assert e.sex == "female"
    assert e.backdrop_poi == "customs_concourse"


def test_portrait_manifest_entry_defaults_blank():
    """Existing NPC entries without picker fields still parse, fields blank."""
    e = PortraitManifestEntry.model_validate({"name": "Rux", "type": "npc_major"})
    assert e.id == ""
    assert e.culture == ""
    assert e.archetype == ""
    assert e.sex == ""
    assert e.backdrop_poi == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_models.py -v`
Expected: FAIL — `e.id` etc. raise `AttributeError` (fields dropped by `extra="ignore"`).

- [ ] **Step 3: Add the fields**

In `pack.py`, extend the `PortraitManifestEntry` field block (after `element_visual: str = ""`):

```python
    # Picker metadata (Epic 66). Populated only on type=player_picker entries;
    # blank on canon NPC entries. `id` is the explicit slug (also the rendered
    # PNG filename and the catalog ref suffix); culture/archetype/sex drive the
    # UI soft-suggest; backdrop_poi names the history.yaml POI used as the
    # render backdrop (empty => plain portrait).
    id: str = ""
    culture: str = ""
    archetype: str = ""
    sex: str = ""
    backdrop_poi: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_models.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && git add sidequest/genre/models/pack.py tests/genre/test_pack_models.py
git commit -m "feat(66): add picker fields to PortraitManifestEntry"
```

---

## Task 3: REST endpoint to list pickers (server)

**Files:**
- Modify: `sidequest-server/sidequest/server/rest.py` (inside `create_rest_router()`, before `return router`)
- Test: `sidequest-server/tests/server/test_rest_portraits.py` (create)

The endpoint returns all `player_picker` entries for a world, with resolved URLs. Slug is `entry.id`; portrait path mirrors the generator's output:
`genre_packs/{genre}/worlds/{world}/images/portraits/{slug}.png`.

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_rest_portraits.py`. Mirror the existing REST test setup (find how other `tests/server/test_rest*.py` build the app + `app.state.genre_pack_search_paths`; reuse that fixture). The behavioral assertions:

```python
def test_list_pickers_filters_and_resolves(rest_client, tmp_pack_with_pickers):
    # tmp_pack_with_pickers: a genre pack fixture whose world ships two
    # player_picker entries (ids "picker_a", "picker_b") plus one npc_major.
    resp = rest_client.get("/api/chargen/portraits/testgenre/testworld")
    assert resp.status_code == 200
    body = resp.json()
    slugs = {p["slug"] for p in body["portraits"]}
    assert slugs == {"picker_a", "picker_b"}  # npc_major excluded
    a = next(p for p in body["portraits"] if p["slug"] == "picker_a")
    assert a["portrait_url"].endswith(
        "/genre_packs/testgenre/worlds/testworld/images/portraits/picker_a.png"
    )
    assert a["culture"] == "hegemonic"
    assert a["archetype"] == "ruler"


def test_list_pickers_empty_world_returns_empty_list(rest_client, tmp_pack_no_pickers):
    resp = rest_client.get("/api/chargen/portraits/testgenre/testworld")
    assert resp.status_code == 200
    assert resp.json() == {"portraits": []}
```

> If the existing REST test fixtures don't expose a pack-with-pickers builder, add `tmp_pack_with_pickers` / `tmp_pack_no_pickers` fixtures that write a minimal `worlds/testworld/portrait_manifest.yaml` under a temp genre-pack dir and point `app.state.genre_pack_search_paths` at it. Reuse the loader (`load_genre_pack_cached`) so the test exercises real parsing.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_rest_portraits.py -v`
Expected: FAIL — 404 (route not defined).

- [ ] **Step 3: Add the endpoint**

In `rest.py`, inside `create_rest_router()`, add (mirroring the existing `@router.get("/api/genres")` idiom and using `load_genre_pack_cached` + `resolve_asset_url`, both already imported/used in this module):

```python
    @router.get("/api/chargen/portraits/{genre}/{world}")
    async def list_chargen_portraits(genre: str, world: str, request: Request) -> dict[str, Any]:
        """List player-picker sample portraits for a world (Epic 66).

        Filters portrait_manifest entries to type=player_picker. Returns an
        empty list (not an error) for worlds that ship no pickers.
        """
        search_paths = request.app.state.genre_pack_search_paths
        genre_pack = load_genre_pack_cached(genre, search_paths)
        world_obj = genre_pack.worlds.get(world) if genre_pack else None
        portraits: list[dict[str, Any]] = []
        if world_obj is not None:
            for entry in world_obj.portrait_manifest:
                if entry.character_type != "player_picker":
                    continue
                slug = entry.id or entry.name
                portraits.append(
                    {
                        "slug": slug,
                        "culture": entry.culture,
                        "archetype": entry.archetype,
                        "sex": entry.sex,
                        "role": entry.role,
                        "portrait_url": resolve_asset_url(
                            f"genre_packs/{genre}/worlds/{world}"
                            f"/images/portraits/{slug}.png"
                        ),
                    }
                )
        return {"portraits": portraits}
```

> Verify the exact signature of `load_genre_pack_cached` at its existing call site (`rest.py:347`) and match it — it may take the search paths positionally or read them from app state itself. Adjust the call to match the real signature; do not invent arguments.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_rest_portraits.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && git add sidequest/server/rest.py tests/server/test_rest_portraits.py
git commit -m "feat(66): GET /api/chargen/portraits/{genre}/{world}"
```

---

## Task 4: OTEL span constant (server)

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/chargen.py`
- Test: covered by the wiring test in Task 5.

- [ ] **Step 1: Add the constant**

In `chargen.py`, after `SPAN_CHARGEN_BACKSTORY_COMPOSED` (line ~9):

```python
SPAN_CHARGEN_PORTRAIT_SELECT = "chargen.portrait_select"
```

If this module maintains a `FLAT_ONLY_SPANS` set (as referenced in the codebase), register it:

```python
FLAT_ONLY_SPANS.add(SPAN_CHARGEN_PORTRAIT_SELECT)
```

Ensure it is re-exported from `sidequest/telemetry/spans/__init__.py` alongside the other `SPAN_CHARGEN_*` constants (match the existing export pattern).

- [ ] **Step 2: Verify import resolves**

Run: `cd sidequest-server && uv run python -c "from sidequest.telemetry.spans import SPAN_CHARGEN_PORTRAIT_SELECT; print(SPAN_CHARGEN_PORTRAIT_SELECT)"`
Expected: prints `chargen.portrait_select`

- [ ] **Step 3: Commit**

```bash
cd sidequest-server && git add sidequest/telemetry/spans/chargen.py sidequest/telemetry/spans/__init__.py
git commit -m "feat(66): add chargen.portrait_select span constant"
```

---

## Task 5: Interpose the pick_portrait step + apply portrait_ref (server)

The portrait step is interposed at the single `_next_message` chokepoint: when the builder reaches confirmation, emit the `pick_portrait` scene once (instead of the confirmation summary); on `portrait_confirm`/`portrait_skip`, store the selection on `_SessionData`, fire the OTEL span, then emit the confirmation summary. At build time, `_chargen_confirmation` copies the stored ref onto the Character. The builder phase machine is untouched.

**Files:**
- Modify: `sidequest-server/sidequest/server/session_state.py:144-168` (`_SessionData`)
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py` (`_next_message` ~3344; new handler method; `_chargen_confirmation` ~2486)
- Modify: `sidequest-server/sidequest/handlers/character_creation.py:95-117` (dispatch)
- Modify: `sidequest-server/sidequest/protocol/messages.py:378-419` (`CharacterCreationPayload`)
- Test: `sidequest-server/tests/server/test_chargen_portrait_step.py` (create)

- [ ] **Step 1: Add protocol fields**

In `messages.py`, add to `CharacterCreationPayload` (after `action`):

```python
    selected_portrait_ref: str | None = None
    """Player's chosen portrait slug (client → server, phase=portrait_confirm)."""
    portraits_available: bool | None = None
    """Server → client: whether this world ships any picker portraits."""
    suggest_archetype: str | None = None
    """Server → client: in-progress build archetype, for UI soft-suggest."""
    suggest_culture: str | None = None
    """Server → client: in-progress build culture hint, for UI soft-suggest."""
```

- [ ] **Step 2: Add `_SessionData` fields**

In `session_state.py`, add to `_SessionData` after the `builder` field (all defaulted, so dataclass field-ordering is preserved):

```python
    # Epic 66 portrait picker. portrait_step_shown gates the one-time
    # interposition of the pick_portrait scene before the confirmation
    # summary; selected_portrait_ref holds the player's choice until the
    # confirmation commit copies it onto the built Character.
    portrait_step_shown: bool = False
    selected_portrait_ref: str | None = None
```

- [ ] **Step 3: Write the failing tests**

Create `tests/server/test_chargen_portrait_step.py`. Use the existing chargen handler test harness (find a `tests/server/test_*chargen*` or character-creation test and reuse its session/builder setup). Behavioral assertions:

```python
def test_next_message_emits_portrait_scene_before_confirmation(chargen_session_at_confirmation):
    # Session whose builder.is_confirmation() is True, world ships >=1 picker.
    session, sd, player_id, builder = chargen_session_at_confirmation
    out = session._next_message(builder, sd, player_id)
    msg = out[0]
    assert msg.payload.input_type == "pick_portrait"
    assert msg.payload.portraits_available is True
    assert sd.portrait_step_shown is True


def test_portrait_confirm_stores_ref_and_emits_confirmation(chargen_session_portrait_shown):
    session, sd, player_id, builder = chargen_session_portrait_shown
    payload = CharacterCreationPayload(
        phase="portrait_confirm",
        selected_portrait_ref="picker_a",
    )
    out = session._chargen_portrait_confirm(builder, payload, sd, player_id, _span())
    assert sd.selected_portrait_ref == "picker_a"
    # next frame is the confirmation summary, not another portrait scene
    assert getattr(out[0].payload, "input_type", None) != "pick_portrait"


def test_confirmation_applies_portrait_ref_to_character(chargen_session_ready_to_build):
    session, sd, player_id, builder = chargen_session_ready_to_build
    sd.selected_portrait_ref = "picker_a"
    import asyncio
    asyncio.run(session._chargen_confirmation(builder, sd, player_id, _span()))
    assert sd.snapshot.characters[-1].portrait_ref == "picker_a"


def test_portrait_select_emits_otel_span(chargen_session_portrait_shown, otel_capture):
    session, sd, player_id, builder = chargen_session_portrait_shown
    payload = CharacterCreationPayload(phase="portrait_confirm", selected_portrait_ref="picker_a")
    session._chargen_portrait_confirm(builder, payload, sd, player_id, _span())
    assert "chargen.portrait_select" in otel_capture.event_names()
```

> Reuse the project's OTEL capture helper (search `tests/` for existing span-assertion fixtures used with `Emitter.fire`; do not invent `otel_capture` — wire it to the real test util). `_span()` returns a no-op/recording span as the existing chargen tests do.

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_chargen_portrait_step.py -v`
Expected: FAIL — `_chargen_portrait_confirm` undefined; `_next_message` emits confirmation directly.

- [ ] **Step 5: Implement the interposition in `_next_message`**

In `websocket_session_handler.py`, replace the body of `_next_message` (currently `if builder.is_confirmation(): return [render_confirmation_summary(...)]; return [builder.to_scene_message(player_id)]`) with:

```python
        if builder.is_confirmation():
            if not sd.portrait_step_shown:
                sd.portrait_step_shown = True
                return [self._render_portrait_scene(builder, sd, player_id)]
            return [render_confirmation_summary(builder, sd.genre_pack, sd.player_name, player_id)]
        return [builder.to_scene_message(player_id)]
```

- [ ] **Step 6: Add `_render_portrait_scene`**

Add this method near `_chargen_story_confirm` in `websocket_session_handler.py`. It computes soft-suggest hints from `builder.accumulated()` and whether the world ships pickers:

```python
    def _render_portrait_scene(
        self,
        builder: CharacterBuilder,
        sd: _SessionData,
        player_id: str,
    ) -> CharacterCreationMessage:
        """Emit the pick_portrait scene (Epic 66). The UI fetches the actual
        portrait list from GET /api/chargen/portraits/{genre}/{world}; this
        payload carries only the soft-suggest hints + availability flag."""
        world_obj = sd.genre_pack.worlds.get(sd.world_slug)
        has_pickers = bool(
            world_obj
            and any(e.character_type == "player_picker" for e in world_obj.portrait_manifest)
        )
        acc = builder.accumulated()
        payload = CharacterCreationPayload(
            phase="scene",
            input_type="pick_portrait",
            prompt="Choose a portrait for your character.",
            portraits_available=has_pickers,
            suggest_archetype=acc.jungian_hint or acc.rpg_role_hint or acc.class_hint,
            suggest_culture=acc.race_hint,
        )
        return CharacterCreationMessage(payload=payload, player_id=player_id)
```

> `AccumulatedChoices` has no dedicated `culture` field; `race_hint` is the closest build-time proxy and soft-suggest is cosmetic best-effort. Do not add a culture hint to the builder for this — out of scope.

- [ ] **Step 7: Add `_chargen_portrait_confirm` + dispatch**

Add the handler method in `websocket_session_handler.py`:

```python
    def _chargen_portrait_confirm(
        self,
        builder: CharacterBuilder,
        payload: CharacterCreationPayload,
        sd: _SessionData,
        player_id: str,
        span: trace.Span,
    ) -> list[object]:
        """Store the player's portrait choice (or skip) and advance to the
        confirmation summary. Cosmetic — no builder mutation."""
        sd.selected_portrait_ref = payload.selected_portrait_ref or None
        from sidequest.telemetry.spans import SPAN_CHARGEN_PORTRAIT_SELECT, Emitter

        Emitter.fire(
            SPAN_CHARGEN_PORTRAIT_SELECT,
            {
                "genre": sd.genre_slug,
                "world": sd.world_slug,
                "selected_portrait_ref": sd.selected_portrait_ref or "",
                "skipped": sd.selected_portrait_ref is None,
                "was_suggested": bool(payload.suggest_archetype)
                and payload.selected_portrait_ref is not None,
                "player_id": player_id,
            },
        )
        return self._next_message(builder, sd, player_id)
```

In `handlers/character_creation.py`, add dispatch after the `story_confirm` branch (line 116):

```python
        if phase == "portrait_confirm":
            return session._chargen_portrait_confirm(builder, payload, sd, player_id, span)
```

> `portrait_skip` from the UI is sent as `phase=portrait_confirm` with `selected_portrait_ref=None`; no separate branch needed.

- [ ] **Step 8: Apply portrait_ref at confirmation**

In `_chargen_confirmation` (the method that calls `builder.build(char_name)` ~line 2486), immediately after `character = builder.build(char_name)` succeeds and before the character is placed on the snapshot:

```python
            character.portrait_ref = sd.selected_portrait_ref
```

> Verify the exact place where the built `Character` is appended to `sd.snapshot.characters`; set `portrait_ref` before that append so the saved snapshot includes it.

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_chargen_portrait_step.py -v`
Expected: PASS (all four)

- [ ] **Step 10: Run the chargen regression suite**

Run: `cd sidequest-server && uv run pytest tests/server -k "chargen or character_creation" -v`
Expected: PASS — no regression in existing chargen flow (the interposition only adds one frame before confirmation).

- [ ] **Step 11: Commit**

```bash
cd sidequest-server && git add sidequest/server/session_state.py sidequest/server/websocket_session_handler.py sidequest/handlers/character_creation.py sidequest/protocol/messages.py tests/server/test_chargen_portrait_step.py
git commit -m "feat(66): interpose pick_portrait step + apply portrait_ref, OTEL span"
```

---

## Task 6: Picker validation in the pack validator (server)

**Files:**
- Modify: `sidequest-server/sidequest/cli/validate/pack.py:238-263` (`_validate_portrait_manifest`)
- Test: `sidequest-server/tests/cli/test_validate_pack_pickers.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/cli/test_validate_pack_pickers.py`:

```python
from pathlib import Path
import yaml
from sidequest.cli.validate.pack import _validate_portrait_manifest


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "portrait_manifest.yaml"
    p.write_text(yaml.safe_dump({"characters": entries}))
    return p


def test_picker_missing_fields_warns(tmp_path):
    p = _write(tmp_path, [{"name": "Officer", "type": "player_picker"}])
    errs = _validate_portrait_manifest(p, "testworld")
    joined = " ".join(errs)
    assert "player_picker" in joined
    assert "id" in joined and "culture" in joined


def test_picker_dangling_backdrop_poi_warns(tmp_path):
    p = _write(
        tmp_path,
        [{"name": "Officer", "type": "player_picker", "id": "picker_a",
          "culture": "heg", "archetype": "ruler", "sex": "female",
          "backdrop_poi": "no_such_poi"}],
    )
    # known_poi_slugs is the set of POI slugs from the world's history.yaml
    errs = _validate_portrait_manifest(p, "testworld", known_poi_slugs={"customs_concourse"})
    assert any("no_such_poi" in e for e in errs)


def test_complete_picker_no_warning(tmp_path):
    p = _write(
        tmp_path,
        [{"name": "Officer", "type": "player_picker", "id": "picker_a",
          "culture": "heg", "archetype": "ruler", "sex": "female",
          "backdrop_poi": "customs_concourse"}],
    )
    errs = _validate_portrait_manifest(p, "testworld", known_poi_slugs={"customs_concourse"})
    assert errs == []


def test_npc_entry_unaffected(tmp_path):
    p = _write(tmp_path, [{"name": "Rux", "type": "npc_major"}])
    assert _validate_portrait_manifest(p, "testworld", known_poi_slugs=set()) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/cli/test_validate_pack_pickers.py -v`
Expected: FAIL — `_validate_portrait_manifest` has no `known_poi_slugs` param and no picker checks.

- [ ] **Step 3: Extend the validator**

Modify `_validate_portrait_manifest` to accept the POI set and add picker checks. Replace its signature and append checks inside the entry loop:

```python
def _validate_portrait_manifest(
    path: Path, label: str, known_poi_slugs: set[str] | None = None
) -> list[str]:
```

After the existing `PortraitManifestEntry.model_validate(entry)` try/except inside the loop, add:

```python
        if isinstance(entry, dict) and entry.get("type") == "player_picker":
            missing = [f for f in ("id", "culture", "archetype", "sex") if not entry.get(f)]
            if missing:
                errors.append(
                    f"{label}: {path.name} entry [{idx}] (player_picker) missing "
                    f"required picker field(s): {', '.join(missing)}"
                )
            bpoi = entry.get("backdrop_poi")
            if bpoi and known_poi_slugs is not None and bpoi not in known_poi_slugs:
                errors.append(
                    f"{label}: {path.name} entry [{idx}] backdrop_poi '{bpoi}' "
                    f"not found in world history.yaml POIs"
                )
```

- [ ] **Step 4: Thread the POI set at the call site**

At the invocation (line 382), gather the world's POI slugs from `history.yaml` and pass them. Find how the validator already reads `history.yaml` (there is a locations/POI validator in the same package); reuse that slug extraction. If a helper exists, call it; otherwise read the world's history chapters' `points_of_interest[].slug` into a set:

```python
    known_poi_slugs = _collect_poi_slugs(world_dir / "history.yaml")
    content_errors.extend(
        _validate_portrait_manifest(
            world_dir / "portrait_manifest.yaml", label, known_poi_slugs=known_poi_slugs
        )
    )
```

Implement `_collect_poi_slugs(path) -> set[str]` near `_validate_portrait_manifest` if no equivalent exists:

```python
def _collect_poi_slugs(path: Path) -> set[str]:
    """Return the set of POI slugs declared in a world's history.yaml."""
    if not path.is_file():
        return set()
    data, _err = _read_yaml(path, "history")
    slugs: set[str] = set()
    if isinstance(data, dict):
        for chapter in data.get("chapters", []) or []:
            for poi in (chapter or {}).get("points_of_interest", []) or []:
                slug = (poi or {}).get("slug")
                if slug:
                    slugs.add(slug)
    return slugs
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/cli/test_validate_pack_pickers.py -v`
Expected: PASS (all four)

- [ ] **Step 6: Run the validator against a live pack (smoke)**

Run: `cd sidequest-server && uv run python -m sidequest.cli.validate pack ../sidequest-content/genre_packs/space_opera --verbose`
Expected: completes; any coyote_star pickers missing the new fields surface as warnings (this is the intended content-gap signal, not a failure of this task).

- [ ] **Step 7: Commit**

```bash
cd sidequest-server && git add sidequest/cli/validate/pack.py tests/cli/test_validate_pack_pickers.py
git commit -m "feat(66): validate player_picker fields + backdrop_poi refs"
```

---

## Task 7: `portrait_in_location` camera preset (daemon)

Portrait-against-a-location is already wired: `RenderTarget.background` (`recipes.py:73`) + `_resolve_location` portrait branch (`prompt_composer.py:382-394`). This task adds the montage-guarded camera preset and auto-selects it when a portrait has a background.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/recipes.py:37-60` (`CameraPreset` enum)
- Modify: `sidequest-daemon/cameras.yaml`
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py:472-487` (`_resolve_direction_camera`)
- Test: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_composer.py` (the `composer` fixture exists; the fixture world must have a place the portrait can use as background — reuse an existing fixture POI ref, e.g. whatever `test_*_poi` uses; substitute the real fixture place ref for `where:testworld/<slug>`):

```python
def test_portrait_in_location_uses_guarded_preset(composer: PromptComposer):
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux", background="where:testworld/<FIXTURE_POI_SLUG>",
    )
    result = composer.compose(t)
    p = result.positive_prompt
    # montage guard present
    assert "single continuous photograph" in p
    assert "telephoto" in p
    # location backdrop layer present (POI environment text bled in)
    cam = composer._resolve_direction_camera(t)
    assert cam.source == "portrait_in_location"


def test_portrait_without_background_keeps_default_camera(composer: PromptComposer):
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre", character="npc:rux",
    )
    cam = composer._resolve_direction_camera(t)
    assert cam.source == "portrait_3q"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-daemon && uv run pytest tests/test_composer.py -k portrait_in_location -v`
Expected: FAIL — `CameraPreset.portrait_in_location` does not exist; camera source is `portrait_3q`.

- [ ] **Step 3: Add the enum member**

In `recipes.py`, in the `CameraPreset` enum under the "Signature shots" group:

```python
    portrait_in_location = "portrait_in_location"
```

- [ ] **Step 4: Add the preset prose**

In `cameras.yaml`, add (Z-Image: no negative prompts; prose is positive framing direction; the guard language forces one cohesive frame to dodge the close-up/wide montage trap):

```yaml
portrait_in_location:
  prompt: >-
    single continuous photograph, long telephoto lens compression, the subject
    standing in the foreground occupying the frame, the surrounding location
    softly out of focus behind them through shallow depth of field, one cohesive
    cinematic frame, environmental portrait
```

- [ ] **Step 5: Auto-select the preset for portraits with a background**

In `prompt_composer.py`, modify `_resolve_direction_camera` so the dispatch becomes:

```python
    def _resolve_direction_camera(
        self, target: RenderTarget
    ) -> LayerContribution:
        recipe = self._recipes.get(target.kind)
        if recipe.direction_camera == "{camera}":
            assert target.camera is not None
            preset = target.camera
        elif target.kind == "portrait" and target.background:
            preset = CameraPreset.portrait_in_location
        else:
            preset = CameraPreset(recipe.direction_camera)
        spec = self._cameras.get(preset)
        return LayerContribution(
            slot="DIRECTION_CAMERA",
            source=preset.value,
            tokens=spec.prompt,
            estimated_tokens=_estimate_tokens(spec.prompt),
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd sidequest-daemon && uv run pytest tests/test_composer.py -k portrait -v`
Expected: PASS (new tests + existing portrait tests still green)

- [ ] **Step 7: Commit**

```bash
cd sidequest-daemon && git add sidequest_daemon/media/recipes.py cameras.yaml sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(66): portrait_in_location montage-guarded camera preset"
```

---

## Task 8: Thread `background` through the render request (daemon + scripts)

The composer consumes `RenderTarget.background`, but nothing currently sends it. Thread a `background` request param: socket params → cue metadata → `build_target` → `RenderTarget.background`; and have the generator pass `where:<world>/<backdrop_poi>` for picker entries.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/daemon.py` (image-render param handling, ~line 226 / the StageCue build site)
- Modify: `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py:103-112` (portrait `RenderTarget`)
- Modify: `scripts/render_common.py:265-306` (`send_render`)
- Modify: `scripts/generate_portrait_images.py:44-98`
- Test: `sidequest-daemon/tests/test_composer.py` (build_target unit)

- [ ] **Step 1: Write the failing test (build_target threads background)**

Find the test module that exercises `build_target`/StageCue→RenderTarget (search `tests/` for `build_target` or `StageCue` portrait tests). Add:

```python
def test_build_target_portrait_threads_background():
    cue = StageCue(
        tier=RenderTier.PORTRAIT,
        subject="npc:rux",
        characters=["npc:rux"],
        metadata={"world": "w", "genre": "g", "background": "where:w/plaza"},
    )
    target = build_target(cue)   # use the real import path for build_target
    assert target.kind == "portrait"
    assert target.background == "where:w/plaza"
```

> Match the real `StageCue` constructor fields and the real name/import of the `build_target` function (it lives in `zimage_mlx_worker.py`). Adjust field names to the actual `StageCue` model.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/ -k build_target_portrait_threads_background -v`
Expected: FAIL — `target.background` is `None` (not threaded).

- [ ] **Step 3: Thread background in build_target**

In `zimage_mlx_worker.py`, the portrait branch (lines 105-112) becomes:

```python
        return RenderTarget(
            kind="portrait",
            world=world,
            genre=genre,
            character=character,
            background=cue.metadata.get("background") or None,
            camera=cue.camera,
            fidelity=fidelity,
        )
```

- [ ] **Step 4: Read the background param into the cue (daemon.py)**

In `daemon.py`, locate where the image-render StageCue is built from `params` for the catalog-composed path (where `params.get("subject")`, `params.get("world")`, `params.get("genre")` are read into the cue/metadata, near lines 226 / 585-633). Add `background` to the cue metadata alongside world/genre:

```python
                    # Epic 66: portrait backdrop ref (where:<world>/<slug>),
                    # passed straight through to RenderTarget.background.
                    cue.metadata["background"] = params.get("background", "")
```

> Set it on the same metadata dict that already carries `world`/`genre`/`fidelity`. If the cue is constructed in one literal, add `"background": params.get("background", "")` to that metadata dict instead.

- [ ] **Step 5: Run the daemon test to verify it passes**

Run: `cd sidequest-daemon && uv run pytest tests/ -k build_target_portrait_threads_background -v`
Expected: PASS

- [ ] **Step 6: Add `background` to `send_render` (scripts)**

In `scripts/render_common.py`, add a keyword param to `send_render` and forward it into `params` only when set (catalog path):

Signature — add after `variant: str = ""`:

```python
    background: str = "",
```

In the body, in the catalog-composed branch (`if subject and genre and world:`), after `params["world"] = world`:

```python
        if background:
            params["background"] = background
```

- [ ] **Step 7: Pass backdrop_poi from the generator (scripts)**

In `scripts/generate_portrait_images.py`, in `collect_characters` add `backdrop_poi` and `type` capture to each char dict (the loop ~line 57):

```python
                "backdrop_poi": char.get("backdrop_poi", ""),
```

(`type` is already captured.) Then, where `send_render` is invoked for the catalog path, compute and pass the background ref. The actual `send_render` call lives in `render_common.render_batch` (lines 532-541), which does not currently know about `backdrop_poi`. The minimal, DRY thread: in `render_batch`'s catalog branch, read it off the item and pass it:

In `render_common.py`, inside `render_batch`, in the `if use_catalog:` `send_render(...)` call (line 533), add:

```python
                    background=(
                        f"where:{item['world']}/{item['backdrop_poi']}"
                        if item.get("backdrop_poi")
                        else ""
                    ),
```

> Only picker entries set `backdrop_poi`; all other portrait items pass `background=""` and render plainly, unchanged. `collect_characters` already puts `world` and `backdrop_poi` on every item dict.

- [ ] **Step 8: Dry-run the generator to verify the ref is composed**

Run: `cd /Users/slabgorb/Projects/oq-1 && python3 scripts/generate_portrait_images.py --genre space_opera --world coyote_star --dry-run`
Expected: runs without error; catalog-composed mode is reported. (No render occurs; the daemon need not be running for `--dry-run`.)

- [ ] **Step 9: Commit (two repos)**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon && git add sidequest_daemon/media/daemon.py sidequest_daemon/media/workers/zimage_mlx_worker.py tests/
git commit -m "feat(66): thread background ref into portrait RenderTarget"
cd /Users/slabgorb/Projects/oq-1 && git add scripts/render_common.py scripts/generate_portrait_images.py
git commit -m "feat(66): generator passes backdrop_poi as where: background ref"
```

---

## Task 9: UI payload types (ui)

**Files:**
- Modify: `sidequest-ui/src/types/payloads.ts:119-134` (`CharacterCreationPayload`)

- [ ] **Step 1: Add server→client fields**

Add to `CharacterCreationPayload` (these arrive on the `pick_portrait` scene):

```typescript
  portraits_available?: boolean;
  suggest_archetype?: string;
  suggest_culture?: string;
```

- [ ] **Step 2: Verify the type compiles**

Run: `cd sidequest-ui && npx tsc --noEmit`
Expected: no new type errors.

- [ ] **Step 3: Commit**

```bash
cd sidequest-ui && git add src/types/payloads.ts
git commit -m "feat(66): portrait picker payload fields"
```

---

## Task 10: PortraitPanel component (ui)

**Files:**
- Create: `sidequest-ui/src/components/CharacterCreation/PortraitPanel.tsx`
- Test: `sidequest-ui/src/components/CharacterCreation/__tests__/PortraitPanel.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `__tests__/PortraitPanel.test.tsx` (mirror `StoryPanel.test.tsx` style):

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PortraitPanel } from "../PortraitPanel";

describe("PortraitPanel", () => {
  const portraits = [
    { slug: "picker_a", portrait_url: "/a.png", culture: "heg", archetype: "ruler", sex: "female", role: "Officer" },
    { slug: "picker_b", portrait_url: "/b.png", culture: "drift", archetype: "outlaw", sex: "male", role: "Miner" },
  ];

  it("renders a grid tile per portrait", () => {
    render(<PortraitPanel portraits={portraits} suggestArchetype={null} onConfirm={vi.fn()} onSkip={vi.fn()} />);
    expect(screen.getByTestId("portrait-tile-picker_a")).toBeInTheDocument();
    expect(screen.getByTestId("portrait-tile-picker_b")).toBeInTheDocument();
  });

  it("calls onConfirm with the chosen slug", () => {
    const onConfirm = vi.fn();
    render(<PortraitPanel portraits={portraits} suggestArchetype={null} onConfirm={onConfirm} onSkip={vi.fn()} />);
    fireEvent.click(screen.getByTestId("portrait-tile-picker_b"));
    fireEvent.click(screen.getByTestId("portrait-confirm"));
    expect(onConfirm).toHaveBeenCalledWith("picker_b");
  });

  it("calls onSkip when skip is clicked", () => {
    const onSkip = vi.fn();
    render(<PortraitPanel portraits={portraits} suggestArchetype={null} onConfirm={vi.fn()} onSkip={onSkip} />);
    fireEvent.click(screen.getByTestId("portrait-skip"));
    expect(onSkip).toHaveBeenCalled();
  });

  it("surfaces archetype-matching portraits first (soft-suggest)", () => {
    render(<PortraitPanel portraits={portraits} suggestArchetype={"outlaw"} onConfirm={vi.fn()} onSkip={vi.fn()} />);
    const tiles = screen.getAllByTestId(/^portrait-tile-/);
    expect(tiles[0].getAttribute("data-testid")).toBe("portrait-tile-picker_b");
  });

  it("shows an empty state when no portraits", () => {
    render(<PortraitPanel portraits={[]} suggestArchetype={null} onConfirm={vi.fn()} onSkip={vi.fn()} />);
    expect(screen.getByTestId("portrait-empty")).toBeInTheDocument();
    expect(screen.getByTestId("portrait-skip")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/CharacterCreation/__tests__/PortraitPanel.test.tsx`
Expected: FAIL — module `../PortraitPanel` not found.

- [ ] **Step 3: Implement PortraitPanel**

Create `PortraitPanel.tsx`:

```typescript
import { useState } from "react";

export interface PortraitOption {
  slug: string;
  portrait_url: string;
  culture: string;
  archetype: string;
  sex: string;
  role: string;
}

interface PortraitPanelProps {
  portraits: PortraitOption[];
  suggestArchetype: string | null;
  onConfirm: (slug: string) => void;
  onSkip: () => void;
}

export function PortraitPanel({ portraits, suggestArchetype, onConfirm, onSkip }: PortraitPanelProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const ordered = [...portraits].sort((a, b) => {
    if (!suggestArchetype) return 0;
    const am = a.archetype === suggestArchetype ? 0 : 1;
    const bm = b.archetype === suggestArchetype ? 0 : 1;
    return am - bm;
  });

  if (portraits.length === 0) {
    return (
      <div data-testid="character-creation" className="flex flex-col items-center px-6 py-10 gap-6 max-w-2xl mx-auto">
        <p data-testid="portrait-empty" className="text-foreground/70 italic">
          No sample portraits for this world yet.
        </p>
        <button data-testid="portrait-skip" className="px-4 py-2 rounded border" onClick={onSkip}>
          Continue without a portrait
        </button>
      </div>
    );
  }

  return (
    <div data-testid="character-creation" className="flex flex-col items-center px-6 py-10 gap-6 max-w-2xl mx-auto">
      <h2 className="text-lg font-semibold tracking-tight">Choose a Portrait</h2>
      <div className="grid grid-cols-3 gap-3" data-testid="portrait-grid">
        {ordered.map((p) => (
          <button
            key={p.slug}
            data-testid={`portrait-tile-${p.slug}`}
            className={`rounded overflow-hidden border-2 ${selected === p.slug ? "border-primary" : "border-transparent"}`}
            onClick={() => setSelected(p.slug)}
            title={`${p.role}`}
          >
            <img src={p.portrait_url} alt={p.role} className="w-full h-auto" />
          </button>
        ))}
      </div>
      <div className="flex gap-3">
        <button
          data-testid="portrait-confirm"
          className="px-4 py-2 rounded bg-primary text-primary-foreground disabled:opacity-50"
          disabled={selected === null}
          onClick={() => selected && onConfirm(selected)}
        >
          Use this portrait
        </button>
        <button data-testid="portrait-skip" className="px-4 py-2 rounded border" onClick={onSkip}>
          Skip
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/components/CharacterCreation/__tests__/PortraitPanel.test.tsx`
Expected: PASS (all five)

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui && git add src/components/CharacterCreation/PortraitPanel.tsx src/components/CharacterCreation/__tests__/PortraitPanel.test.tsx
git commit -m "feat(66): PortraitPanel grid with soft-suggest + skip"
```

---

## Task 11: Wire pick_portrait into CharacterCreation + App (ui)

**Files:**
- Modify: `sidequest-ui/src/components/CharacterCreation/CharacterCreation.tsx` (CreationScene interface ~17-45; render branches ~136-260)
- Modify: `sidequest-ui/src/App.tsx` (fetch pickers on entering pick_portrait; pass genre/world; ~1151, ~261)
- Test: `sidequest-ui/src/components/CharacterCreation/__tests__/CharacterCreation.test.tsx`

- [ ] **Step 1: Write the failing integration test**

Add to `__tests__/CharacterCreation.test.tsx` (mirror existing stat_arrange/story integration tests in that file):

```typescript
it("renders PortraitPanel when input_type is pick_portrait", () => {
  render(
    <CharacterCreation
      scene={{ phase: "scene", input_type: "pick_portrait", prompt: "Choose..." }}
      portraits={[{ slug: "p1", portrait_url: "/p1.png", culture: "c", archetype: "ruler", sex: "female", role: "Officer" }]}
      loading={false}
      onRespond={vi.fn()}
    />,
  );
  expect(screen.getByTestId("portrait-tile-p1")).toBeInTheDocument();
});

it("emits portrait_confirm with selected_portrait_ref", () => {
  const onRespond = vi.fn();
  render(
    <CharacterCreation
      scene={{ phase: "scene", input_type: "pick_portrait", prompt: "Choose..." }}
      portraits={[{ slug: "p1", portrait_url: "/p1.png", culture: "c", archetype: "ruler", sex: "female", role: "Officer" }]}
      loading={false}
      onRespond={onRespond}
    />,
  );
  fireEvent.click(screen.getByTestId("portrait-tile-p1"));
  fireEvent.click(screen.getByTestId("portrait-confirm"));
  expect(onRespond).toHaveBeenCalledWith({ phase: "portrait_confirm", selected_portrait_ref: "p1" });
});

it("emits portrait_confirm with null ref on skip", () => {
  const onRespond = vi.fn();
  render(
    <CharacterCreation
      scene={{ phase: "scene", input_type: "pick_portrait", prompt: "Choose..." }}
      portraits={[]}
      loading={false}
      onRespond={onRespond}
    />,
  );
  fireEvent.click(screen.getByTestId("portrait-skip"));
  expect(onRespond).toHaveBeenCalledWith({ phase: "portrait_confirm", selected_portrait_ref: null });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/CharacterCreation/__tests__/CharacterCreation.test.tsx -t pick_portrait`
Expected: FAIL — no pick_portrait branch; `portraits` prop unknown.

- [ ] **Step 3: Extend CharacterCreation props + add the branch**

In `CharacterCreation.tsx`, add to the `CreationScene` interface:

```typescript
  portraits_available?: boolean;
  suggest_archetype?: string;
  suggest_culture?: string;
```

Add a `portraits` prop to the component's props type (alongside `scene`, `loading`, `onRespond`):

```typescript
  portraits?: import("./PortraitPanel").PortraitOption[];
```

Add the render branch (before the `confirmation` branch so it takes precedence when active), importing `PortraitPanel` at the top:

```typescript
  if (scene.input_type === "pick_portrait") {
    return (
      <PortraitPanel
        portraits={portraits ?? []}
        suggestArchetype={scene.suggest_archetype ?? null}
        onConfirm={(slug) => onRespond({ phase: "portrait_confirm", selected_portrait_ref: slug })}
        onSkip={() => onRespond({ phase: "portrait_confirm", selected_portrait_ref: null })}
      />
    );
  }
```

- [ ] **Step 4: Run the component test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/components/CharacterCreation/__tests__/CharacterCreation.test.tsx -t pick_portrait`
Expected: PASS (all three)

- [ ] **Step 5: Fetch pickers in App.tsx and pass them down**

In `App.tsx`, add state near `currentGenre`/`currentWorld` (line 261):

```typescript
  const [creationPortraits, setCreationPortraits] = useState<
    import("./components/CharacterCreation/PortraitPanel").PortraitOption[]
  >([]);
```

When a `pick_portrait` scene arrives, fetch the list. In the handler that processes incoming `CHARACTER_CREATION` scenes (where `creationScene` state is set), add: when `payload.input_type === "pick_portrait"`, fetch and store:

```typescript
      if (payload.input_type === "pick_portrait" && currentGenre && currentWorld) {
        fetch(
          `/api/chargen/portraits/${encodeURIComponent(currentGenre)}/${encodeURIComponent(currentWorld)}`,
        )
          .then(async (resp) => {
            if (!resp.ok) throw new Error(`failed to load portraits: ${resp.status}`);
            return resp.json() as Promise<{ portraits: PortraitOption[] }>;
          })
          .then((body) => setCreationPortraits(body.portraits))
          .catch(() => setCreationPortraits([]));
      }
```

> Import `PortraitOption` from the PortraitPanel module. The `.catch(() => setCreationPortraits([]))` is the deliberate empty-state path (the panel shows "no portraits / skip"), not a silent fallback masking config — the endpoint legitimately returns `[]` for worlds with no pickers, and a fetch error degrades to the same skippable state rather than blocking chargen. Surface the error to the console for diagnosis.

Pass it into the component where `CharacterCreation` is rendered:

```typescript
        <CharacterCreation
          scene={creationScene}
          portraits={creationPortraits}
          loading={creationLoading}
          onRespond={handleCreationRespond}
        />
```

- [ ] **Step 6: Run the full UI test suite + typecheck**

Run: `cd sidequest-ui && npx tsc --noEmit && npx vitest run`
Expected: PASS, no type errors.

- [ ] **Step 7: Commit**

```bash
cd sidequest-ui && git add src/components/CharacterCreation/CharacterCreation.tsx src/App.tsx src/components/CharacterCreation/__tests__/CharacterCreation.test.tsx
git commit -m "feat(66): wire pick_portrait phase + fetch pickers"
```

---

## Final Verification

- [ ] **Server gate**

Run: `cd sidequest-server && uv run ruff check . && uv run pytest -q`
Expected: lint clean; suite green.

- [ ] **Daemon gate**

Run: `cd sidequest-daemon && uv run ruff check . && uv run pytest -q`
Expected: lint clean; suite green.

- [ ] **UI gate**

Run: `cd sidequest-ui && npx tsc --noEmit && npx vitest run && npm run lint`
Expected: clean.

- [ ] **End-to-end wiring confirmation (manual, no content authored)**

The mechanism is provable without authored portraits: a world with zero pickers must reach the pick_portrait step, show the empty/skip state, skip, and complete chargen with `portrait_ref == null`. The four-test wiring suite in Task 5 plus the Task 11 empty-state test cover this without a live render. (Actually rendering authored portraits is the downstream content fan-out, out of scope.)

---

## Out of Scope (do not implement)

- Authoring `player_picker` entries / the ~20 portraits per world.
- Rendering pilot portraits (daemon is committed elsewhere).
- Custom/player-uploaded portraits.
- Changing a portrait mid-game.
