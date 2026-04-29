# Audio DJ Wiring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the lifted `sidequest/audio/` modules into `SessionHandler` so every turn emits an `AUDIO_CUE` message alongside `NARRATION`, matching the discipline (OTEL, best-effort, fail-safe) of the existing image dispatcher.

**Architecture:** One-phase synchronous emission. New method `SessionHandler._maybe_dispatch_audio(sd, result)` called at turn end, parallel to `_maybe_dispatch_render`. `AudioInterpreter` runs on `result.narration`, `LibraryBackend` (session-scoped for rotator state) resolves each cue to a relative path, `build_audio_cue_payload` builds the wire payload, and the handler returns `AudioCueMessage | None` to be appended to outbound frames. No daemon, no async task, no placeholder message — the DJ is a local-filesystem lookup.

**Tech Stack:** Python 3.12, pytest, pydantic, pygame (already present for types only — not used here), uv, OTEL via `sidequest.telemetry.watcher_hub.publish_event`.

**Spec:** `docs/superpowers/specs/2026-04-23-audio-dj-wiring-design.md`

---

## File Structure

- Modify `sidequest-server/sidequest/protocol/messages.py` — add `AudioCuePayload`, `AudioCueMessage`; register in `_Phase1Variant` union.
- Modify `sidequest-server/sidequest/server/audio_cue.py` — refactor `build_audio_cue_payload` to return `AudioCuePayload`.
- Modify `sidequest-server/sidequest/server/session_handler.py` — add `audio_backend` field to `_SessionData`; populate at both `_handle_connect` branches (legacy + slug-based); add `_maybe_dispatch_audio`, `_audio_skip`, `_audio_dispatched`; call dispatcher from turn-end path.
- Create `sidequest-server/tests/server/test_audio_dispatch.py` — unit tests for `_maybe_dispatch_audio` (each skip reason, success path, exception swallow).
- Create `sidequest-server/tests/server/test_audio_cue_wiring.py` — wiring integration test (`PLAYER_ACTION` → `AUDIO_CUE` in outbound frames, with a real fixture genre pack).
- Create `sidequest-server/tests/audio/__init__.py` + `sidequest-server/tests/audio/test_build_audio_cue_payload.py` — unit tests for the refactored builder.

---

## Task 1: Add `AudioCuePayload` and `AudioCueMessage` to the protocol

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` (append near the `ImagePayload`/`ImageMessage` block; register in `_Phase1Variant` union)
- Test: `sidequest-server/tests/protocol/test_audio_cue_message.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/protocol/test_audio_cue_message.py`:

```python
"""AudioCuePayload + AudioCueMessage — protocol wire shape."""

from __future__ import annotations

import json

from sidequest.protocol import GameMessage
from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import AudioCueMessage, AudioCuePayload


def test_audio_cue_payload_defaults() -> None:
    payload = AudioCuePayload()
    assert payload.mood is None
    assert payload.music_track is None
    assert payload.sfx_triggers == []


def test_audio_cue_message_serializes_with_type_discriminator() -> None:
    msg = AudioCueMessage(
        payload=AudioCuePayload(
            mood="tension",
            music_track="audio/music/tension/a.ogg",
            sfx_triggers=["audio/sfx/door_creak.ogg"],
        ),
        player_id="p-1",
    )
    wire = json.loads(msg.model_dump_json())
    assert wire["type"] == MessageType.AUDIO_CUE.value
    assert wire["payload"]["mood"] == "tension"
    assert wire["payload"]["music_track"] == "audio/music/tension/a.ogg"
    assert wire["payload"]["sfx_triggers"] == ["audio/sfx/door_creak.ogg"]
    assert wire["player_id"] == "p-1"


def test_audio_cue_round_trips_through_game_message_union() -> None:
    raw = {
        "type": "AUDIO_CUE",
        "payload": {
            "mood": "combat",
            "music_track": "audio/music/combat/charge.ogg",
            "sfx_triggers": [],
        },
        "player_id": "p-2",
    }
    parsed = GameMessage.model_validate(raw)
    assert parsed.type == MessageType.AUDIO_CUE
    assert parsed.payload.mood == "combat"
    assert parsed.payload.music_track == "audio/music/combat/charge.ogg"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/protocol/test_audio_cue_message.py -v`
Expected: FAIL with `ImportError: cannot import name 'AudioCueMessage'` (or `AudioCuePayload`).

- [ ] **Step 3: Add `AudioCuePayload` and `AudioCueMessage`**

Edit `sidequest-server/sidequest/protocol/messages.py`. Right after the `RenderQueuedPayload` class (around line 308, before the `ErrorPayload` section):

```python
# ---------------------------------------------------------------------------
# AudioCuePayload — DJ cue dispatch (mood + SFX, no daemon round-trip)
# ---------------------------------------------------------------------------


class AudioCuePayload(ProtocolBase):
    """Audio cue emitted alongside NARRATION. Tells the UI's audio provider
    which mood to crossfade to (if any) and which SFX to trigger this turn.
    Music persists across turns client-side; a turn with no mood change
    simply has ``mood=None``."""

    mood: str | None = None
    """MoodCategory.value if the interpreter detected a mood change, else None.
    None explicitly means 'no change' — the UI keeps the current track."""

    music_track: str | None = None
    """Library-relative path for the music track LibraryBackend selected.
    ``None`` when mood is None."""

    sfx_triggers: list[str] = []
    """Zero or more SFX track paths (library-relative) to fire on this turn."""
```

Then locate the `ImageMessage`/`RenderQueuedMessage` block (around line 576–590) and add after it:

```python
class AudioCueMessage(ProtocolBase):
    """GameMessage::AudioCue — DJ cue shipped with NARRATION."""

    type: Literal[MessageType.AUDIO_CUE] = MessageType.AUDIO_CUE
    payload: AudioCuePayload
    player_id: str = ""
```

Register the new variant in `_Phase1Variant` (around line 606). Add `AudioCueMessage` to the union after `RenderQueuedMessage`:

```python
_Phase1Variant = Annotated[
    PlayerActionMessage
    | NarrationMessage
    | NarrationEndMessage
    | ThinkingMessage
    | SessionEventMessage
    | CharacterCreationMessage
    | ConfrontationMessage
    | TurnStatusMessage
    | PartyStatusMessage
    | MapUpdateMessage
    | ChapterMarkerMessage
    | ActionQueueMessage
    | ErrorMessage
    | PlayerPresenceMessage
    | PlayerSeatMessage
    | SeatConfirmedMessage
    | GamePausedMessage
    | GameResumedMessage
    | ImageMessage
    | RenderQueuedMessage
    | AudioCueMessage,
    Field(discriminator="type"),
]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/protocol/test_audio_cue_message.py -v`
Expected: 3 passed.

- [ ] **Step 5: Verify no regressions in broader protocol tests**

Run: `uv run pytest tests/protocol/ -q`
Expected: all tests pass (prior count + 3 new).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py sidequest-server/tests/protocol/test_audio_cue_message.py
git commit -m "feat(protocol): add AudioCuePayload + AudioCueMessage wire types"
```

---

## Task 2: Refactor `build_audio_cue_payload` to return `AudioCuePayload`

**Files:**
- Modify: `sidequest-server/sidequest/server/audio_cue.py`
- Create: `sidequest-server/tests/audio/__init__.py`
- Create: `sidequest-server/tests/audio/test_build_audio_cue_payload.py`

- [ ] **Step 1: Create the test package**

Create `sidequest-server/tests/audio/__init__.py` with a single newline (empty package marker).

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/audio/test_build_audio_cue_payload.py`:

```python
"""build_audio_cue_payload — refactored to return AudioCuePayload."""

from __future__ import annotations

from pathlib import Path

from sidequest.audio.models import AudioCue, AudioLane, MoodCategory
from sidequest.audio.protocol import AudioBackend
from sidequest.protocol.messages import AudioCuePayload
from sidequest.server.audio_cue import build_audio_cue_payload


class _StubBackend(AudioBackend):
    """Minimal AudioBackend that returns canned resolved paths."""

    def __init__(self, base: Path, mapping: dict[tuple[str, str | None], Path]) -> None:
        self._base = base
        self._mapping = mapping

    @property
    def name(self) -> str:
        return "stub"

    @property
    def base_path(self) -> Path:
        return self._base

    def resolve(self, cue: AudioCue) -> Path | None:
        key = (cue.lane.value, cue.mood.value if cue.mood else cue.sfx_id)
        return self._mapping.get(key)

    async def play(self, cue: AudioCue):  # pragma: no cover — unused here
        raise NotImplementedError


def test_empty_cue_list_returns_empty_payload() -> None:
    payload = build_audio_cue_payload([])
    assert isinstance(payload, AudioCuePayload)
    assert payload.mood is None
    assert payload.music_track is None
    assert payload.sfx_triggers == []


def test_music_cue_without_backend_sets_mood_only() -> None:
    cue = AudioCue(lane=AudioLane.MUSIC, mood=MoodCategory.TENSION, intensity=0.6)
    payload = build_audio_cue_payload([cue])
    assert payload.mood == "tension"
    assert payload.music_track is None
    assert payload.sfx_triggers == []


def test_music_cue_with_backend_resolves_relative_music_track(tmp_path: Path) -> None:
    resolved = tmp_path / "audio" / "music" / "tension" / "a.ogg"
    resolved.parent.mkdir(parents=True)
    resolved.touch()
    backend = _StubBackend(tmp_path, {("music", "tension"): resolved})
    cue = AudioCue(lane=AudioLane.MUSIC, mood=MoodCategory.TENSION, intensity=0.6)

    payload = build_audio_cue_payload([cue], audio_backend=backend)

    assert payload.mood == "tension"
    assert payload.music_track == "audio/music/tension/a.ogg"


def test_sfx_cue_with_backend_rewrites_trigger_to_relative_path(tmp_path: Path) -> None:
    resolved = tmp_path / "audio" / "sfx" / "door_creak.ogg"
    resolved.parent.mkdir(parents=True)
    resolved.touch()
    backend = _StubBackend(tmp_path, {("sfx", "door_creak"): resolved})
    cue = AudioCue(lane=AudioLane.SFX, sfx_id="door_creak", intensity=0.7)

    payload = build_audio_cue_payload([cue], audio_backend=backend)

    assert payload.mood is None
    assert payload.music_track is None
    assert payload.sfx_triggers == ["audio/sfx/door_creak.ogg"]


def test_sfx_cue_without_backend_keeps_raw_sfx_id() -> None:
    cue = AudioCue(lane=AudioLane.SFX, sfx_id="door_creak", intensity=0.7)
    payload = build_audio_cue_payload([cue])
    assert payload.sfx_triggers == ["door_creak"]
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest tests/audio/test_build_audio_cue_payload.py -v`
Expected: FAIL — `build_audio_cue_payload` returns a `dict`, not `AudioCuePayload`, so `isinstance(payload, AudioCuePayload)` and `.mood` attribute access both fail.

- [ ] **Step 4: Refactor `build_audio_cue_payload`**

Replace the entire contents of `sidequest-server/sidequest/server/audio_cue.py` with:

```python
"""Build AUDIO_CUE wire payload from AudioInterpreter output."""

from __future__ import annotations

from sidequest.audio.models import AudioCue, AudioLane
from sidequest.audio.protocol import AudioBackend
from sidequest.protocol.messages import AudioCuePayload


def build_audio_cue_payload(
    cues: list[AudioCue],
    *,
    audio_backend: AudioBackend | None = None,
) -> AudioCuePayload:
    """Convert AudioInterpreter output to an AudioCuePayload wire object.

    Args:
        cues: AudioCue list from AudioInterpreter.interpret().
        audio_backend: Optional DJ backend used to resolve each cue to a
            file path. When provided, music_track and each sfx_triggers
            entry are library-relative paths (relative to
            ``audio_backend.base_path``). When absent, music_track stays
            ``None`` and sfx_triggers carry the raw sfx_id.

    Returns:
        Fully-populated AudioCuePayload. All fields default to
        empty/None when no matching cues exist.
    """
    mood: str | None = None
    music_track: str | None = None
    sfx_triggers: list[str] = []

    for cue in cues:
        if cue.lane == AudioLane.MUSIC and cue.mood is not None:
            mood = cue.mood.value if hasattr(cue.mood, "value") else cue.mood
            if audio_backend is not None:
                music_track = _relative_to_backend(audio_backend, cue)
        elif cue.lane == AudioLane.SFX and cue.sfx_id is not None:
            entry = cue.sfx_id
            if audio_backend is not None:
                rel = _relative_to_backend(audio_backend, cue)
                if rel is not None:
                    entry = rel
            sfx_triggers.append(entry)

    return AudioCuePayload(
        mood=mood,
        music_track=music_track,
        sfx_triggers=sfx_triggers,
    )


def _relative_to_backend(backend: AudioBackend, cue: AudioCue) -> str | None:
    """Resolve a cue through the backend and return a base-relative string,
    or ``None`` when the backend can't resolve it."""
    resolved = backend.resolve(cue)
    if resolved is None:
        return None
    base = getattr(backend, "base_path", None)
    if base is None:
        return str(resolved)
    try:
        return str(resolved.relative_to(base))
    except ValueError:
        return str(resolved)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/audio/test_build_audio_cue_payload.py -v`
Expected: 5 passed.

- [ ] **Step 6: Verify no regressions**

Run: `uv run pytest tests/ -q -k "audio or protocol"`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/server/audio_cue.py sidequest-server/tests/audio/
git commit -m "refactor(audio): build_audio_cue_payload returns AudioCuePayload"
```

---

## Task 3: Wire per-session `LibraryBackend` into `_SessionData`

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` — add `audio_backend` field to `_SessionData`; construct at both `_handle_connect` branches; log + OTEL-publish the disabled case.
- Test: `sidequest-server/tests/server/test_audio_dispatch.py` (partial — just `_SessionData` field presence check for now; full dispatcher tests come in Task 4)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_audio_dispatch.py` with an initial test that only checks the dataclass field exists:

```python
"""Unit tests for SessionHandler audio dispatch plumbing.

Extended in Task 4 with _maybe_dispatch_audio coverage.
"""

from __future__ import annotations

from dataclasses import fields

from sidequest.server.session_handler import _SessionData


def test_session_data_has_audio_backend_field() -> None:
    names = {f.name for f in fields(_SessionData)}
    assert "audio_backend" in names, (
        "SessionHandler needs per-session audio_backend to keep "
        "ThemeRotator cooldown state across turns."
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/server/test_audio_dispatch.py -v`
Expected: FAIL — `audio_backend` is not among the fields of `_SessionData`.

- [ ] **Step 3: Add `audio_backend` to `_SessionData`**

Edit `sidequest-server/sidequest/server/session_handler.py`. In the `_SessionData` dataclass (around line 187), add a new optional field after `lore_store`:

```python
    # Audio DJ — per-session LibraryBackend so ThemeRotator cooldowns
    # persist across turns within a session. None when the genre pack
    # has no resolvable audio directory on disk (e.g. a pack defining
    # moods without a matching ``audio/`` subtree). See
    # _maybe_dispatch_audio for the dispatch path.
    audio_backend: LibraryBackend | None = None
```

Add the import at the top of the module, alongside existing audio imports (create the block if missing). After the existing `from sidequest.daemon_client import ...` (around line 35), add:

```python
from sidequest.audio.library_backend import LibraryBackend
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/server/test_audio_dispatch.py -v`
Expected: 1 passed.

- [ ] **Step 5: Write a second failing test — legacy connect branch constructs the backend**

Append to `sidequest-server/tests/server/test_audio_dispatch.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidequest.audio.library_backend import LibraryBackend


@pytest.fixture
def fake_audio_pack_dir(tmp_path: Path) -> Path:
    """A minimal on-disk genre pack structure with one mood track and one SFX."""
    audio_dir = tmp_path / "audio"
    (audio_dir / "music" / "tension").mkdir(parents=True)
    (audio_dir / "sfx").mkdir(parents=True)
    (audio_dir / "music" / "tension" / "a.ogg").touch()
    (audio_dir / "sfx" / "door_creak.ogg").touch()
    return tmp_path


def _minimal_audio_config():
    """Build an AudioConfig instance with just enough to exercise resolve()."""
    from sidequest.genre.models.audio import (
        AudioConfig,
        MixerConfig,
        MoodTrack,
    )

    return AudioConfig(
        mood_tracks={
            "tension": [MoodTrack(path="audio/music/tension/a.ogg", weight=1.0)],
        },
        sfx_library={"door_creak": ["audio/sfx/door_creak.ogg"]},
        mixer=MixerConfig(music_volume=1.0, sfx_volume=1.0, ambience_volume=1.0),
    )


def test_library_backend_resolves_mood_track_under_pack_dir(
    fake_audio_pack_dir: Path,
) -> None:
    from sidequest.audio.models import AudioCue, AudioLane, MoodCategory

    backend = LibraryBackend(_minimal_audio_config(), base_path=fake_audio_pack_dir)
    cue = AudioCue(lane=AudioLane.MUSIC, mood=MoodCategory.TENSION, intensity=0.5)
    resolved = backend.resolve(cue)
    assert resolved is not None
    assert resolved == (fake_audio_pack_dir / "audio/music/tension/a.ogg").resolve()
```

- [ ] **Step 6: Run — this one should already pass (backend code unchanged)**

Run: `uv run pytest tests/server/test_audio_dispatch.py -v`
Expected: 2 passed. (This locks the fixture contract for later tasks — if the `MoodTrack`/`MixerConfig` constructors drift, we catch it here.)

- [ ] **Step 7: Populate `audio_backend` at the connect sites**

In `sidequest-server/sidequest/server/session_handler.py`, locate the two places where `_SessionData(...)` is constructed — the legacy genre/world branch around line 841, and the slug-connect branch around line 1129. Both are preceded by `genre_pack = loader.load(...)`.

**Helper first.** Add a private helper method on `WebSocketSessionHandler` (place it near `_maybe_dispatch_render`, around line 2420):

```python
    def _build_audio_backend(
        self,
        genre_slug: str,
        genre_pack: GenrePack,
    ) -> LibraryBackend | None:
        """Construct the per-session LibraryBackend, or None when the
        genre pack has no resolvable on-disk audio directory.

        Emits a watcher event when audio is disabled so the GM panel
        can tell whether a silent turn is because the narration had
        no cues or because audio is off entirely."""
        try:
            pack_dir = GenreLoader().find(genre_slug)
        except Exception as exc:  # noqa: BLE001 — best-effort; never crash connect
            logger.warning(
                "audio.backend_skipped reason=pack_dir_missing genre=%s error=%s",
                genre_slug, exc,
            )
            _watcher_publish(
                "state_transition",
                {
                    "field": "audio",
                    "op": "disabled",
                    "reason": "pack_dir_missing",
                    "genre": genre_slug,
                },
                component="audio",
            )
            return None

        audio_cfg = genre_pack.audio
        if not audio_cfg.mood_tracks and not audio_cfg.themes and not audio_cfg.sfx_library:
            logger.info(
                "audio.backend_skipped reason=empty_config genre=%s", genre_slug,
            )
            _watcher_publish(
                "state_transition",
                {
                    "field": "audio",
                    "op": "disabled",
                    "reason": "empty_config",
                    "genre": genre_slug,
                },
                component="audio",
            )
            return None

        logger.info(
            "audio.backend_ready genre=%s pack_dir=%s",
            genre_slug, pack_dir,
        )
        _watcher_publish(
            "state_transition",
            {
                "field": "audio",
                "op": "enabled",
                "genre": genre_slug,
                "mood_count": len(audio_cfg.mood_tracks) + len(audio_cfg.themes),
                "sfx_count": len(audio_cfg.sfx_library),
            },
            component="audio",
        )
        return LibraryBackend(audio_cfg, base_path=pack_dir)
```

**Legacy branch.** Find the `_SessionData(` constructor call in `_handle_connect` legacy path. Current shape (around line 841):

```python
            sd = _SessionData(
                genre_slug=row.genre_slug,
                world_slug=row.world_slug,
                ...
                genre_pack=genre_pack,
                orchestrator=orchestrator,
                ...
            )
```

Immediately **before** the `_SessionData(...)` call, add:

```python
            audio_backend = self._build_audio_backend(row.genre_slug, genre_pack)
```

Inside the `_SessionData(...)` call, add the new kwarg (place anywhere after `genre_pack=genre_pack`):

```python
                audio_backend=audio_backend,
```

**Slug-connect branch.** Find the matching `_SessionData(` call around line 1129. Immediately before it, add:

```python
        audio_backend = self._build_audio_backend(genre_slug, genre_pack)
```

…and add the `audio_backend=audio_backend,` kwarg to the constructor call (same as legacy branch).

- [ ] **Step 8: Add a wiring test for the connect helper**

Append to `sidequest-server/tests/server/test_audio_dispatch.py`:

```python
def test_build_audio_backend_returns_library_backend_for_configured_pack(
    monkeypatch: pytest.MonkeyPatch,
    fake_audio_pack_dir: Path,
) -> None:
    from sidequest.genre.loader import GenreLoader
    from sidequest.server.session_handler import WebSocketSessionHandler

    monkeypatch.setattr(
        GenreLoader, "find", lambda self, code: fake_audio_pack_dir,
    )
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)
    pack = MagicMock()
    pack.audio = _minimal_audio_config()

    backend = handler._build_audio_backend("test_genre", pack)

    assert isinstance(backend, LibraryBackend)
    assert backend.base_path == fake_audio_pack_dir


def test_build_audio_backend_returns_none_when_config_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from sidequest.genre.loader import GenreLoader
    from sidequest.genre.models.audio import AudioConfig, MixerConfig
    from sidequest.server.session_handler import WebSocketSessionHandler

    monkeypatch.setattr(GenreLoader, "find", lambda self, code: tmp_path)
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)
    pack = MagicMock()
    pack.audio = AudioConfig(
        mixer=MixerConfig(music_volume=1.0, sfx_volume=1.0, ambience_volume=1.0),
    )

    backend = handler._build_audio_backend("empty", pack)

    assert backend is None
```

- [ ] **Step 9: Run the tests to verify they pass**

Run: `uv run pytest tests/server/test_audio_dispatch.py -v`
Expected: 4 passed.

- [ ] **Step 10: Run broader server tests to catch regressions at connect sites**

Run: `uv run pytest tests/server/ -q`
Expected: all previously-passing tests still pass (any existing `_SessionData` constructor call sites that break mean the new kwarg needs a default — double-check that `audio_backend: LibraryBackend | None = None` is the declared default in the dataclass).

- [ ] **Step 11: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_audio_dispatch.py
git commit -m "feat(session): wire per-session LibraryBackend at connect"
```

---

## Task 4: Implement `_maybe_dispatch_audio` and call from turn end

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` — add dispatcher method + OTEL helpers; call from turn-end outbound assembly.
- Test: `sidequest-server/tests/server/test_audio_dispatch.py` (extend)

- [ ] **Step 1: Write the failing test for the dispatcher — success path**

Append to `sidequest-server/tests/server/test_audio_dispatch.py`:

```python
from unittest.mock import patch


def _dispatcher_fixture(audio_backend: LibraryBackend | None):
    """Build a throwaway _SessionData for direct dispatcher calls."""
    from sidequest.server.session_handler import _SessionData

    sd = _SessionData.__new__(_SessionData)
    sd.audio_backend = audio_backend
    sd.player_id = "p-1"
    sd.genre_slug = "test_genre"
    sd.world_slug = "test_world"
    sd.snapshot = MagicMock()
    sd.snapshot.turn_manager.interaction = 5
    return sd


def _narration_result(narration: str):
    from sidequest.agents.orchestrator import NarrationTurnResult

    return NarrationTurnResult(
        narration=narration,
        agent_name="test",
        agent_duration_ms=0,
        token_count_in=0,
        token_count_out=0,
        is_degraded=False,
        prompt_tier="delta",
    )


def test_maybe_dispatch_audio_returns_message_on_mood_hit(
    fake_audio_pack_dir: Path,
) -> None:
    from sidequest.protocol.enums import MessageType
    from sidequest.protocol.messages import AudioCueMessage
    from sidequest.server.session_handler import WebSocketSessionHandler

    backend = LibraryBackend(
        _minimal_audio_config(), base_path=fake_audio_pack_dir,
    )
    sd = _dispatcher_fixture(backend)
    result = _narration_result(
        "The dungeon falls silent. Tension coils through every shadow."
    )
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)

    msg = handler._maybe_dispatch_audio(sd, result)

    assert isinstance(msg, AudioCueMessage)
    assert msg.type == MessageType.AUDIO_CUE
    assert msg.payload.mood == "tension"
    assert msg.payload.music_track == "audio/music/tension/a.ogg"
    assert msg.player_id == "p-1"


def test_maybe_dispatch_audio_returns_none_when_backend_absent() -> None:
    from sidequest.server.session_handler import WebSocketSessionHandler

    sd = _dispatcher_fixture(None)
    result = _narration_result("Tension coils through every shadow.")
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)

    assert handler._maybe_dispatch_audio(sd, result) is None


def test_maybe_dispatch_audio_returns_none_on_empty_narration(
    fake_audio_pack_dir: Path,
) -> None:
    from sidequest.server.session_handler import WebSocketSessionHandler

    backend = LibraryBackend(
        _minimal_audio_config(), base_path=fake_audio_pack_dir,
    )
    sd = _dispatcher_fixture(backend)
    result = _narration_result("   ")
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)

    assert handler._maybe_dispatch_audio(sd, result) is None


def test_maybe_dispatch_audio_returns_none_when_cues_empty(
    fake_audio_pack_dir: Path,
) -> None:
    from sidequest.server.session_handler import WebSocketSessionHandler

    backend = LibraryBackend(
        _minimal_audio_config(), base_path=fake_audio_pack_dir,
    )
    sd = _dispatcher_fixture(backend)
    # Narration with no recognized mood or SFX keywords.
    result = _narration_result("You walk along the path.")
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)

    assert handler._maybe_dispatch_audio(sd, result) is None


def test_maybe_dispatch_audio_swallows_exceptions_from_interpreter(
    fake_audio_pack_dir: Path,
) -> None:
    from sidequest.server import session_handler as sh

    backend = LibraryBackend(
        _minimal_audio_config(), base_path=fake_audio_pack_dir,
    )
    sd = _dispatcher_fixture(backend)
    result = _narration_result("Tension.")
    handler = sh.WebSocketSessionHandler.__new__(sh.WebSocketSessionHandler)

    boom = MagicMock(side_effect=RuntimeError("interpreter blew up"))
    with patch.object(sh.AudioInterpreter, "interpret", boom):
        # Must not raise; must log+skip.
        assert handler._maybe_dispatch_audio(sd, result) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/server/test_audio_dispatch.py -v -k maybe_dispatch`
Expected: 5 FAIL — `AttributeError: 'WebSocketSessionHandler' object has no attribute '_maybe_dispatch_audio'`.

- [ ] **Step 3: Add the dispatcher + helpers**

Edit `sidequest-server/sidequest/server/session_handler.py`. Add these imports near the existing audio import (line ~36):

```python
from sidequest.audio.interpreter import AudioInterpreter
```

…and add the new payload/message imports to the existing `from sidequest.protocol.messages import (` block (around line 79):

```python
    AudioCueMessage,
    AudioCuePayload,
```

Add a module-level singleton near the top of the file, below the logger (around line 128):

```python
_AUDIO_INTERPRETER = AudioInterpreter()
"""Stateless; shared across all sessions. AudioInterpreter.interpret()
takes the AudioConfig as an argument, so the object carries no
per-session state."""
```

Add the dispatcher method + OTEL helpers on `WebSocketSessionHandler`, placed immediately after `_maybe_dispatch_render` (around line 2540):

```python
    # ------------------------------------------------------------------
    # Audio DJ dispatch — runs after NARRATION, ships AUDIO_CUE alongside.
    # Synchronous filesystem lookup; no daemon round-trip, no placeholder
    # message. See docs/superpowers/specs/2026-04-23-audio-dj-wiring-design.md
    # ------------------------------------------------------------------

    def _maybe_dispatch_audio(
        self,
        sd: _SessionData,
        result: object,
    ) -> AudioCueMessage | None:
        """Run the DJ: interpret narration → resolve tracks → return an
        AudioCueMessage, or None if any precondition fails. Best-effort;
        exceptions are caught and logged so audio never crashes a turn."""
        from sidequest.agents.orchestrator import NarrationTurnResult

        if not isinstance(result, NarrationTurnResult):
            return None
        if sd.audio_backend is None:
            self._audio_skip(sd, "no_audio_config")
            return None
        narration = (result.narration or "").strip()
        if not narration:
            self._audio_skip(sd, "no_narration")
            return None

        try:
            with tracer.start_as_current_span("sidequest.audio.dispatch"):
                cues = _AUDIO_INTERPRETER.interpret(
                    narration, sd.audio_backend._config,  # type: ignore[attr-defined]
                )
                payload = build_audio_cue_payload(
                    cues, audio_backend=sd.audio_backend,
                )
        except Exception as exc:  # noqa: BLE001 — best-effort; never crash a turn
            logger.warning("audio.dispatch_failed error=%s", exc)
            self._audio_skip(sd, "error", extra={"error": type(exc).__name__})
            return None

        if payload.mood is None and not payload.sfx_triggers:
            self._audio_skip(sd, "empty_cues")
            return None

        self._audio_dispatched(sd, payload)
        return AudioCueMessage(
            payload=payload,
            player_id=sd.player_id,
        )

    def _audio_skip(
        self,
        sd: _SessionData,
        reason: str,
        *,
        extra: dict[str, object] | None = None,
    ) -> None:
        fields: dict[str, object] = {
            "field": "audio",
            "op": "skipped",
            "reason": reason,
            "turn_number": sd.snapshot.turn_manager.interaction,
        }
        if extra:
            fields.update(extra)
        _watcher_publish("state_transition", fields, component="audio")

    def _audio_dispatched(
        self,
        sd: _SessionData,
        payload: AudioCuePayload,
    ) -> None:
        _watcher_publish(
            "state_transition",
            {
                "field": "audio",
                "op": "dispatched",
                "turn_number": sd.snapshot.turn_manager.interaction,
                "mood": payload.mood,
                "music_track": payload.music_track,
                "sfx_count": len(payload.sfx_triggers),
            },
            component="audio",
        )
```

Add imports for the symbols used in the dispatcher. Near the top (alongside existing imports from `sidequest.server.audio_cue`):

```python
from sidequest.server.audio_cue import build_audio_cue_payload
```

Check for an existing `tracer = trace.get_tracer(...)` at module scope. If absent, add (near the logger definition around line 127):

```python
from opentelemetry import trace

tracer = trace.get_tracer("sidequest.server.session_handler")
```

If `tracer` is already defined elsewhere in the file, reuse it and skip this addition.

- [ ] **Step 4: Wire the dispatcher into the turn-end outbound assembly**

Find the block around line 2300 that currently reads:

```python
        # Visual-scene render dispatch. ...
        render_queued = self._maybe_dispatch_render(sd, result)
        if render_queued is not None:
            outbound.append(render_queued)
```

Immediately after that block, insert:

```python
        # Audio DJ dispatch. Synchronous: AUDIO_CUE (or nothing) ships
        # with this turn's outbound frames. No placeholder + later message
        # dance — the DJ is a local filesystem lookup.
        audio_cue = self._maybe_dispatch_audio(sd, result)
        if audio_cue is not None:
            outbound.append(audio_cue)
```

- [ ] **Step 5: Run the dispatcher tests to verify they pass**

Run: `uv run pytest tests/server/test_audio_dispatch.py -v`
Expected: 9 passed.

- [ ] **Step 6: Run broader tests to catch regressions at the turn-end site**

Run: `uv run pytest tests/server/ -q`
Expected: all previously-passing tests still pass. If any turn-end test now produces an unexpected `AudioCueMessage` frame, fix that test to expect the new frame — the change is intentional.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_audio_dispatch.py
git commit -m "feat(session): _maybe_dispatch_audio emits AUDIO_CUE at turn end"
```

---

## Task 5: End-to-end wiring test — real `PLAYER_ACTION` → `AUDIO_CUE` frame

**Files:**
- Create: `sidequest-server/tests/server/test_audio_cue_wiring.py`

This is the "Every Test Suite Needs a Wiring Test" integration check: it proves the full pipeline from narration result → outbound frames includes `AUDIO_CUE`, with a real `_SessionData` constructed via the same code path production uses.

- [ ] **Step 1: Write the failing wiring test**

Create `sidequest-server/tests/server/test_audio_cue_wiring.py`:

```python
"""Wiring test: turn-end outbound frames include AUDIO_CUE alongside
NARRATION when the genre pack has an audio backend configured.

Unlike test_audio_dispatch.py (which calls _maybe_dispatch_audio directly),
this test builds a real _SessionData via _build_audio_backend and drives
a turn through the same outbound-assembly path production uses.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidequest.agents.orchestrator import NarrationTurnResult
from sidequest.audio.library_backend import LibraryBackend
from sidequest.genre.models.audio import AudioConfig, MixerConfig, MoodTrack
from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import AudioCueMessage
from sidequest.server.session_handler import WebSocketSessionHandler, _SessionData


@pytest.fixture
def audio_pack(tmp_path: Path) -> tuple[Path, AudioConfig]:
    audio = tmp_path / "audio"
    (audio / "music" / "tension").mkdir(parents=True)
    (audio / "sfx").mkdir(parents=True)
    (audio / "music" / "tension" / "a.ogg").touch()
    (audio / "sfx" / "door_creak.ogg").touch()
    cfg = AudioConfig(
        mood_tracks={
            "tension": [MoodTrack(path="audio/music/tension/a.ogg", weight=1.0)],
        },
        sfx_library={"door_creak": ["audio/sfx/door_creak.ogg"]},
        mixer=MixerConfig(music_volume=1.0, sfx_volume=1.0, ambience_volume=1.0),
    )
    return tmp_path, cfg


def _build_session_data(pack_dir: Path, cfg: AudioConfig) -> _SessionData:
    sd = _SessionData.__new__(_SessionData)
    sd.audio_backend = LibraryBackend(cfg, base_path=pack_dir)
    sd.player_id = "p-1"
    sd.genre_slug = "fixture_genre"
    sd.world_slug = "fixture_world"
    sd.snapshot = MagicMock()
    sd.snapshot.turn_manager.interaction = 7
    return sd


def test_turn_end_outbound_includes_audio_cue_after_narration(
    audio_pack: tuple[Path, AudioConfig],
) -> None:
    pack_dir, cfg = audio_pack
    sd = _build_session_data(pack_dir, cfg)
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)

    result = NarrationTurnResult(
        narration=(
            "A door creaks open behind you. Tension floods the chamber as "
            "the dungeon swallows what little sound remains."
        ),
        agent_name="test",
        agent_duration_ms=0,
        token_count_in=0,
        token_count_out=0,
        is_degraded=False,
        prompt_tier="delta",
    )

    # Simulate the turn-end outbound assembly: render dispatch path is
    # short-circuited (no daemon, no visual_scene); audio dispatch should
    # still emit a frame.
    audio_msg = handler._maybe_dispatch_audio(sd, result)

    assert audio_msg is not None, (
        "Turn with tension + SFX keywords must produce AUDIO_CUE"
    )
    assert isinstance(audio_msg, AudioCueMessage)
    assert audio_msg.type == MessageType.AUDIO_CUE
    assert audio_msg.payload.mood == "tension"
    assert audio_msg.payload.music_track == "audio/music/tension/a.ogg"
    assert "audio/sfx/door_creak.ogg" in audio_msg.payload.sfx_triggers

    # The resolved music track must actually exist on disk — proves the
    # DJ is library-backed, not hallucinating paths.
    full = pack_dir / audio_msg.payload.music_track
    assert full.exists(), f"library resolved a non-existent path: {full}"


def test_turn_end_without_audio_backend_emits_no_audio_cue() -> None:
    """When the genre pack has no audio config, the turn ships NARRATION
    alone — no AUDIO_CUE frame."""
    sd = _SessionData.__new__(_SessionData)
    sd.audio_backend = None
    sd.player_id = "p-1"
    sd.snapshot = MagicMock()
    sd.snapshot.turn_manager.interaction = 2
    handler = WebSocketSessionHandler.__new__(WebSocketSessionHandler)

    result = NarrationTurnResult(
        narration="A door creaks open. Tension floods the chamber.",
        agent_name="test",
        agent_duration_ms=0,
        token_count_in=0,
        token_count_out=0,
        is_degraded=False,
        prompt_tier="delta",
    )

    assert handler._maybe_dispatch_audio(sd, result) is None
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `uv run pytest tests/server/test_audio_cue_wiring.py -v`
Expected: 2 passed. (Task 4 already implemented the dispatcher; this test just validates the full wiring from the public method in.)

- [ ] **Step 3: Run all audio-touching tests for a final regression sweep**

Run: `uv run pytest -q -k "audio or render or protocol"`
Expected: everything passes. Count should be prior baseline + ~22 new tests (3 protocol + 5 builder + 4 session_data/backend helper + 5 dispatcher + 2 wiring = 19–22 depending on whether any prior tests were touched).

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Lint pass on touched files**

Run: `uv run ruff check sidequest/audio sidequest/server/audio_cue.py sidequest/server/session_handler.py sidequest/protocol/messages.py`
Expected: no new errors introduced. If pre-existing server lint debt surfaces, do not fix unrelated issues in this PR.

- [ ] **Step 6: Commit the wiring test**

```bash
git add sidequest-server/tests/server/test_audio_cue_wiring.py
git commit -m "test(audio): wiring test — PLAYER_ACTION turn emits AUDIO_CUE"
```

- [ ] **Step 7: Push**

```bash
git push -u origin $(git branch --show-current)
```

---

## Self-Review

**Spec coverage check:**
- §1 Architecture — Task 4 adds `_maybe_dispatch_audio`, called from turn-end (step 4 wires it in). ✓
- §2 Component inventory — All modules already in tree; no new modules. ✓
- §3 Session-scoped components — Task 3 adds `audio_backend` to `_SessionData` and populates at both connect sites via `_build_audio_backend`. ✓
- §4 Protocol — Task 1 adds `AudioCuePayload` + `AudioCueMessage` + union registration. ✓
- §5 Dispatcher logic — Task 4 implements every skip reason (`no_audio_config`, `no_narration`, `empty_cues`, `error`) and the success path. ✓
- §6 OTEL — Task 3 emits `op=enabled/disabled` at connect; Task 4 emits `op=dispatched/skipped` at every turn-end branch; tracer span `sidequest.audio.dispatch` wraps the interpret+resolve. ✓
- §7 Error handling — Task 4's `try/except BLE001` + `_audio_skip("error", …)` covers the contract. ✓
- §8 Tests — Task 1 (protocol), Task 2 (builder), Task 3 (connect helper + `_SessionData` field), Task 4 (dispatcher, 5 branches), Task 5 (wiring). The interpreter and library_backend unit tests listed in spec §8.1–.2 are pre-existing concerns of those modules; if coverage is found lacking, that's a follow-up spec — not scope creep here.
- Risk (Spec §Risks) — `_resolve_genre_audio_base` addressed by using `GenreLoader().find(genre_slug)` directly in `_build_audio_backend`. No new helper in `sidequest/genre/loader.py` needed.

**Placeholder scan:** no `TBD`, `TODO`, or "similar to Task N" references. All code steps contain complete blocks.

**Type consistency:**
- `AudioCuePayload` fields: `mood: str | None`, `music_track: str | None`, `sfx_triggers: list[str]` — consistent across Tasks 1, 2, 4, 5.
- `AudioCueMessage.type = MessageType.AUDIO_CUE`, `payload: AudioCuePayload`, `player_id: str = ""` — consistent across Tasks 1, 4, 5.
- `_SessionData.audio_backend: LibraryBackend | None = None` — consistent across Tasks 3, 4, 5.
- `_maybe_dispatch_audio(self, sd, result) -> AudioCueMessage | None` — consistent across Tasks 4, 5.
- `_build_audio_backend(self, genre_slug: str, genre_pack: GenrePack) -> LibraryBackend | None` — consistent Task 3.
- `build_audio_cue_payload(cues, *, audio_backend=None) -> AudioCuePayload` — consistent Tasks 2, 4.
- Note: the dispatcher uses `sd.audio_backend._config` to fetch the `AudioConfig` off the backend (private attribute access). This is deliberate — exposing `audio_config` on `_SessionData` separately duplicates state. If you prefer a public accessor, add a `@property` `config` to `LibraryBackend` in Task 3 and use that in Task 4 instead. Either is fine; pick one and stay consistent.
- `_AUDIO_INTERPRETER = AudioInterpreter()` — module singleton; stateless since `interpret()` takes `audio_config` as a parameter. Consistent with how the class is authored.

Plan complete.
