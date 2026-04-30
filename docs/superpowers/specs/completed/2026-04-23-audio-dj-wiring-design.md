# Audio DJ Wiring — Design

**Date:** 2026-04-23
**Status:** Approved (brainstorming) — implementation plan pending
**Scope:** Python server (`sidequest-server`)
**Parity target:** `SessionHandler._maybe_dispatch_render` (image pipeline)

## Problem

`sidequest/audio/` (interpreter, library_backend, rotator, models, protocol) was
lifted into the server in the same pass that lifted the image-render client
utilities, but nothing calls it. Turns ship `NARRATION` without an accompanying
`AUDIO_CUE`; the UI's audio provider never receives mood changes or SFX
triggers. The protocol already reserves `MessageType.AUDIO_CUE` but lacks an
`AudioCuePayload` class and an emitter.

The image pipeline is already wired at the turn-end dispatch site in
`SessionHandler`. This spec brings audio up to the same level of discipline
(best-effort, OTEL-instrumented, fail-safe) without copying its two-phase async
shape — Ogg-file selection is a local filesystem lookup, not a 10-60 second
daemon round-trip, so the placeholder message pattern buys nothing.

## Design summary

One-phase synchronous cue emission. At turn end, `SessionHandler` calls a new
`_maybe_dispatch_audio(sd, result)` alongside the existing
`_maybe_dispatch_render(sd, result)`. The dispatcher runs `AudioInterpreter` on
the narration text, resolves each cue to a library track via `LibraryBackend`,
and returns an `AudioCueMessage` to be appended to the turn's outbound frames.

## Architecture

### Components (all already present in tree)

| Component | Location | Role |
|---|---|---|
| `AudioInterpreter` | `sidequest/audio/interpreter.py` | Narration text → `list[AudioCue]` (mood + sfx_triggers), constrained by genre `AudioConfig` |
| `LibraryBackend` | `sidequest/audio/library_backend.py` | `AudioCue` → file path under the genre's audio directory, using `ThemeRotator` for cooldown |
| `ThemeRotator` | `sidequest/audio/rotator.py` | Cooldown shuffle + intensity-weighted track selection |
| `build_audio_cue_payload` | `sidequest/server/audio_cue.py` | `list[AudioCue]` → wire payload dict |
| `AudioConfig` | `sidequest/genre/models/audio.py` | Per-genre allow-list of moods, SFX triggers, audio paths |

### New code

1. `AudioCuePayload` + `AudioCueMessage` in `sidequest/protocol/messages.py`.
2. `_maybe_dispatch_audio` method on `SessionHandler`.
3. Two slots on `_SessionData`: `audio_interpreter: AudioInterpreter | None`,
   `audio_backend: LibraryBackend | None`. Populated during the
   genre/world-bind phase (same place `_SessionData` fields are set today).
4. Refactor `build_audio_cue_payload` to return an `AudioCuePayload` instance
   instead of a `dict`.

### Data flow

```
PLAYER_ACTION
  → orchestrator → NarrationTurnResult (result.narration: str)
    → _emit_event(NARRATION, ...)
    → _maybe_dispatch_render(sd, result)   [existing]
    → _maybe_dispatch_audio(sd, result)    [new]
         ├─ sd.audio_interpreter.extract(result.narration) → list[AudioCue]
         ├─ build_audio_cue_payload(cues, audio_backend=sd.audio_backend)
         │    └─ sd.audio_backend.resolve(cue) → Path   (DJ picks the track)
         └─ returns AudioCueMessage | None
    → _watcher_publish("state_transition", field=audio, op=dispatched|skipped)
    → outbound frames ← [NARRATION, RENDER_QUEUED?, AUDIO_CUE?, ...]
```

## Protocol

### `AudioCuePayload`

```python
class AudioCuePayload(ProtocolBase):
    """Audio cue emitted alongside NARRATION. Tells the UI's audio provider
    which mood to crossfade to (if any) and which SFX to trigger this turn.
    Music persists across turns client-side; a turn with no mood change
    simply has ``mood=None``."""

    mood: str | None = None
    """MoodCategory.value if the interpreter detected a mood change, else None.
    None explicitly means 'no change' — the UI keeps the current track."""

    music_track: str | None = None
    """Library-relative path (relative to the genre pack's audio dir) for the
    music track LibraryBackend selected. None when mood is None."""

    sfx_triggers: list[str] = []
    """Zero or more SFX track paths (library-relative) to fire on this turn.
    Empty list = no SFX."""
```

### `AudioCueMessage`

```python
class AudioCueMessage(ProtocolBase):
    type: Literal[MessageType.AUDIO_CUE] = MessageType.AUDIO_CUE
    payload: AudioCuePayload
    player_id: str | None = None
    seq: int | None = None
```

`MessageType.AUDIO_CUE` already exists in `sidequest/protocol/enums.py`.

## Session bind — constructing per-genre components

At the same point session_handler populates `_SessionData` after a genre/world
connect (where `sd.genre_slug`, `sd.world_slug`, and the loaded `GenrePack` are
available), construct the audio components:

```python
audio_cfg = getattr(genre_pack, "audio", None)
if audio_cfg is not None:
    audio_base = _resolve_genre_audio_base(genre_pack)
    sd.audio_interpreter = AudioInterpreter(audio_cfg)
    sd.audio_backend = LibraryBackend(audio_cfg, base_path=audio_base)
else:
    sd.audio_interpreter = None
    sd.audio_backend = None
    logger.info("audio.not_configured genre=%s", sd.genre_slug)
    _watcher_publish("state_transition",
        {"field": "audio", "op": "disabled", "reason": "no_audio_config",
         "genre": sd.genre_slug}, component="audio")
```

No silent fallback: a genre pack with no `audio` block means the session runs
without audio cues, logged loudly at bind time.

## Dispatcher logic

```python
def _maybe_dispatch_audio(
    self, sd: _SessionData, result: object,
) -> AudioCueMessage | None:
    from sidequest.agents.orchestrator import NarrationTurnResult

    if not isinstance(result, NarrationTurnResult):
        return None
    if sd.audio_interpreter is None or sd.audio_backend is None:
        self._audio_skip(sd, "no_audio_config")
        return None
    narration = (result.narration or "").strip()
    if not narration:
        self._audio_skip(sd, "no_narration")
        return None

    try:
        cues = sd.audio_interpreter.extract(narration)
        payload = build_audio_cue_payload(cues, audio_backend=sd.audio_backend)
    except Exception as exc:  # noqa: BLE001 — best-effort, must never crash a turn
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
```

Helper `_audio_skip` / `_audio_dispatched` centralize OTEL emission so every
branch goes through the same watcher-publish shape.

## OTEL discipline

`field=audio` state_transition events. Example shapes:

```
{ "field": "audio", "op": "dispatched",
  "turn_number": 42, "mood": "tension", "music_track": "tension/a.ogg",
  "sfx_count": 2 }

{ "field": "audio", "op": "skipped",
  "turn_number": 42, "reason": "empty_cues" }

{ "field": "audio", "op": "skipped",
  "turn_number": 42, "reason": "error", "error": "AttributeError" }
```

A tracer span `sidequest.audio.dispatch` wraps the
`interpreter.extract` + `build_audio_cue_payload` call for latency timing.

## Error handling

- Every failure mode of the interpreter or backend is caught at the dispatcher
  boundary; a turn never crashes because of audio.
- Missing genre-pack audio block: logged at bind time, dispatcher silently
  no-ops every turn with `reason=no_audio_config`.
- Missing files on disk: `LibraryBackend.resolve` returns `None`; that cue
  gets dropped from the payload; no skip event (caller sees the resulting
  mood or sfx_trigger list and decides).

## Testing

Per the "Every Test Suite Needs a Wiring Test" rule in `CLAUDE.md`.

1. **Unit — interpreter.** `tests/audio/test_interpreter.py` covers:
   mood extraction, SFX extraction, genre allow-list filtering, empty-narration
   short-circuit, multi-mood prioritization.
2. **Unit — library_backend + rotator.** `tests/audio/test_library_backend.py`
   covers: cue → path resolution across all lanes, missing-file behavior,
   rotator cooldown, intensity-weighted selection.
3. **Unit — dispatcher.** `tests/server/test_session_handler_audio_dispatch.py`
   covers: `_maybe_dispatch_audio` returns `None` for each skip reason,
   returns `AudioCueMessage` on success, OTEL event emitted for every branch,
   exceptions inside the interpreter are caught.
4. **Wiring integration.**
   `tests/server/test_audio_cue_end_to_end.py` — boots a `SessionHandler` with a
   real genre-pack fixture that has `audio` configured and a small set of
   stub Ogg files, runs a `PLAYER_ACTION`, asserts:
   - outbound frames include `NARRATION` and `AUDIO_CUE` in that order;
   - `AudioCuePayload.mood` is the interpreter's decision;
   - `AudioCuePayload.music_track` is library-relative and exists on disk;
   - a `state_transition field=audio op=dispatched` watcher event fired.
5. **Wiring integration — disabled genre.** Same as (4) but the genre pack has
   no `audio` block: assert `NARRATION` ships alone with no `AUDIO_CUE`, and
   `state_transition field=audio op=disabled` fired at connect time.

## Out of scope

- MusicDirector LLM agent (`MusicDirectorDecision` exists as a model in
  `sidequest/audio/protocol.py`; deferred upgrade path).
- Narrator prompt changes — the narrator does not emit audio hints in this
  spec. Mood/SFX decisions are made post-narration by the interpreter.
- UI-side audio provider changes.
- Between-session Ogg file generation.
- Voice/TTS lane (distinct subsystem, not part of the DJ).
- Per-player asymmetric audio (same AUDIO_CUE goes to every player this turn).

## Risks / open questions

- **Genre-pack audio path resolution.** The spec assumes a helper
  `_resolve_genre_audio_base(genre_pack)` that returns the absolute directory
  under which `LibraryBackend` looks for tracks. The current `GenrePack` model
  may or may not expose this cleanly; the implementation plan should either
  reuse an existing resolver or add one in `sidequest/genre/loader.py`.
- **`NarrationTurnResult.narration` shape.** The dispatcher assumes a single
  string `narration` field. If the current result uses a different name or a
  structured form, the implementation plan must adjust.
- **Rotator persistence across saves.** `ThemeRotator` carries cooldown state
  in memory. A session resume via `pf sprint` or a server restart loses it.
  Acceptable for v1 — rotator warm-up is one turn of potential repeat. A
  future spec can persist rotator state to the save file.
