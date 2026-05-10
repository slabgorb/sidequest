# Daemon Between-Session Music Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `music` tier to the daemon that executes per-track ACE-Step JSON params files, uploads OGG output to R2, and replaces the half-built `scripts/generate_music.py` GENRE_MOODS dict — restoring the audio stripped from the content repo.

**Architecture:** ACE-Step joins Flux/Z-Image as a daemon media tier, dispatched alongside `render` and `embed` over the existing Unix socket. Per-track `*_input_params.json` files in `sidequest-content/genre_packs/<pack>/audio/music/` are the canonical generation spec. The daemon reads JSON → runs ACE-Step → FFmpeg WAV→OGG → uploads to R2 at `genre_packs/<pack>/audio/music/<track>.ogg` → returns the R2 key. The script walks JSON files, skips ones already in R2 via HEAD, dispatches the rest. Orphaned `sidequest_daemon/audio/` (~1500 LOC) is deleted in the same change set.

**Tech Stack:** Python 3.11 (daemon, server, scripts), `acestep` package (PyTorch / diffusers), `boto3` (R2 / S3-compatible), FFmpeg subprocess, asyncio Unix socket IPC, pytest + pytest-asyncio, OpenTelemetry.

**Spec:** `docs/superpowers/specs/2026-05-09-daemon-between-session-music-generation-design.md`

---

## File Structure

### Created files

| Path | Responsibility |
|---|---|
| `sidequest-daemon/sidequest_daemon/media/music_pipeline.py` | `MusicPipeline` class — orchestrates one job: read params, derive R2 key, acquire lock, run ACE-Step, FFmpeg, upload, emit watcher events. |
| `sidequest-daemon/sidequest_daemon/media/ace_step_adapter.py` | Thin wrapper over the `acestep` package — strips output fields, overrides `audio_path`, requires `actual_seeds[0]`, returns wav path + seed. |
| `sidequest-daemon/sidequest_daemon/telemetry/__init__.py` | Re-exports `emit_watcher_event` (Task 0 — repairs the silent-ImportError audit finding). |
| `sidequest-daemon/sidequest_daemon/telemetry/watcher_bridge.py` | Cross-process watcher emit (writes to a known FIFO/socket the server reads, OR posts to a server REST endpoint). Implementation detail in Task 0. |
| `sidequest-daemon/tests/test_ace_step_adapter.py` | Adapter unit tests (mock the `acestep` import). |
| `sidequest-daemon/tests/test_music_pipeline.py` | Pipeline unit tests (mock adapter, R2, watcher). |
| `sidequest-daemon/tests/test_music_dispatch.py` | Wiring test — proves `tier=music` reaches `MusicPipeline` from a real socket request shape. |
| `sidequest-daemon/tests/test_music_pipeline_integration.py` | Integration — full pipeline with mock adapter writing real WAV → real FFmpeg → mock R2. |
| `tests/scripts/test_generate_music.py` | Refactored script tests (orchestrator repo). |
| `tests/scripts/__init__.py` | Marks the test package. |
| `docs/adr/0NN-daemon-music-tier-via-ace-step.md` | New ADR. Number assigned at write-time (next free in sequence). |

### Modified files

| Path | Change |
|---|---|
| `sidequest-daemon/sidequest_daemon/media/daemon.py` | Add `MUSIC_TIERS` constant; add `tier in MUSIC_TIERS` branch to dispatch (`~line 329-335`); construct `MusicPipeline` in `_run_daemon`. |
| `sidequest-daemon/sidequest_daemon/media/r2_writer.py` | Add `upload_pack_asset(*, pack, relative_path, content_bytes, content_type)` for genre-pack content (different path scheme than the existing `upload_artifact`). |
| `sidequest-daemon/sidequest_daemon/media/pipeline_factory.py` | Repurpose: delete `init_audio()` and orphaned-audio imports; add `init_music()` that constructs `MusicPipeline`. |
| `sidequest-daemon/pyproject.toml` | Add `ace_step` as a local sibling-path dependency (`{ path = "../ACE-Step", develop = true }`). |
| `scripts/generate_music.py` | Refactor: delete `GENRE_MOODS` / `VARIATION_SUFFIXES` / `compute_seed` / `wav_to_ogg`; add `discover_jobs`, `is_in_r2`; replace `--mood/--variation/--duration` with `--track/--force`. |
| `.claude/commands/sq-music.md` | Workflow update — JSON params authoring, no Python edits. |
| `.claude/agents/music-director.md` | Same workflow update. |
| `sidequest-content/CLAUDE.md` | "binary assets are tracked with Git LFS" → reference R2 + the new music workflow. |
| `CLAUDE.md` (orchestrator) | Soften "music is pre-rendered at build time" line; reference new ADR. |
| `sidequest-daemon/CLAUDE.md` | Same. |
| `docs/adr/046-gpu-memory-budget-coordinator.md` | Add a paragraph noting ACE-Step as a coordinator client (uses `render_lock` for v1). |
| `docs/adr/README.md` | Register the new ADR in the index. |

### Deleted files (Task 16, single commit)

| Path | Reason |
|---|---|
| `sidequest-daemon/sidequest_daemon/audio/__init__.py` | Module marker for orphaned tree |
| `sidequest-daemon/sidequest_daemon/audio/mixer.py` | Pygame mixer; daemon never plays audio |
| `sidequest-daemon/sidequest_daemon/audio/interpreter.py` | 306 LOC duplicate; server has its own |
| `sidequest-daemon/sidequest_daemon/audio/queue.py` | Async cue queue; nothing produces or consumes |
| `sidequest-daemon/sidequest_daemon/audio/library_backend.py` | Path resolver; server has its own |
| `sidequest-daemon/sidequest_daemon/audio/rotator.py` | Theme rotation; unused |
| `sidequest-daemon/sidequest_daemon/audio/protocol.py` | AudioBackend interface; no implementations called |
| `sidequest-daemon/sidequest_daemon/audio/models.py` | Data models; no consumers |

### Prerequisites

1. **Daemon → server watcher-event bridge** (Task 0). The audit found `sidequest_daemon.telemetry` does not exist; both import sites at `prompt_composer.py:43-48` and `daemon.py:719-734` swallow `ImportError`. Fixing this is a prerequisite for the OTEL coverage in §8 of the spec to be real. If a sibling story has already fixed this, skip Task 0 and use the existing module.
2. **ACE-Step package available** (Task 1). Lives at `~/Projects/ACE-Step` with `setup.py name="ace_step"`, but the importable package is lowercase `acestep`. Pip-installable as a local sibling-path dependency.

---

## Task 0: Repair daemon → server watcher-event bridge

The audit found two import sites in the daemon that try `from sidequest_daemon.telemetry import emit_watcher_event` against a module that doesn't exist; both swallow the `ImportError` silently. This violates "no silent fallbacks" and means OTEL emission from the daemon (including this plan's music events) goes to /dev/null.

**Decision needed before starting:** the simplest bridge is a server REST endpoint the daemon POSTs to. If the user prefers a different transport (Unix socket message, FIFO), substitute in step 3. The plan below uses HTTP POST.

**Skip this task if a sibling story has already created `sidequest_daemon/telemetry/__init__.py` exposing `emit_watcher_event`.**

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/telemetry/__init__.py`
- Create: `sidequest-daemon/sidequest_daemon/telemetry/watcher_bridge.py`
- Create: `sidequest-daemon/tests/test_watcher_bridge.py`
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py:43-48` (delete the `try/except ImportError` fallback — let the import succeed)
- Modify: `sidequest-daemon/sidequest_daemon/media/daemon.py:718-734` (delete the `try/except: pass` swallow — let the import succeed)

- [ ] **Step 1: Write the failing test for `watcher_bridge.emit_watcher_event`**

```python
# sidequest-daemon/tests/test_watcher_bridge.py
import pytest
from unittest.mock import patch, MagicMock
from sidequest_daemon.telemetry.watcher_bridge import emit_watcher_event


def test_emit_watcher_event_posts_to_server():
    with patch("sidequest_daemon.telemetry.watcher_bridge.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        emit_watcher_event("test.event", {"k": "v"})
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        body = mock_post.call_args[1]["json"]
        assert url.endswith("/internal/watcher/emit")
        assert body == {"event_type": "test.event", "fields": {"k": "v"}, "component": "daemon"}


def test_emit_watcher_event_swallows_network_error_with_log():
    """Daemon must never crash if the server is down. But the failure
    must log loudly — this is the inverse of the audit-flagged silent swallow."""
    import logging
    with patch("sidequest_daemon.telemetry.watcher_bridge.requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("server down")
        with patch("sidequest_daemon.telemetry.watcher_bridge.log") as mock_log:
            emit_watcher_event("test.event", {})
            mock_log.warning.assert_called_once()
            assert "watcher_bridge" in mock_log.warning.call_args[0][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_watcher_bridge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest_daemon.telemetry'`

- [ ] **Step 3: Implement `watcher_bridge.py` and `telemetry/__init__.py`**

```python
# sidequest-daemon/sidequest_daemon/telemetry/__init__.py
from sidequest_daemon.telemetry.watcher_bridge import emit_watcher_event

__all__ = ["emit_watcher_event"]
```

```python
# sidequest-daemon/sidequest_daemon/telemetry/watcher_bridge.py
"""Cross-process watcher event bridge — daemon → server.

The watcher hub lives in the server process (sidequest.telemetry.watcher_hub).
The daemon cannot import it, so this module POSTs each event to a server
HTTP endpoint that forwards to publish_event().

Per CLAUDE.md no-silent-fallbacks: network errors are LOGGED LOUDLY, not
swallowed. We never crash the calling path on telemetry failure (telemetry
must not break renders), but we make the failure visible.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

log = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://127.0.0.1:8765"


def _server_base_url() -> str:
    return os.environ.get("SIDEQUEST_SERVER_URL", _DEFAULT_SERVER_URL).rstrip("/")


def emit_watcher_event(event_type: str, fields: dict[str, Any], *, component: str = "daemon") -> None:
    """Forward a watcher event to the server's hub via HTTP.

    Failures are logged at WARNING — never raised. Telemetry must not
    break the calling path, but the failure must be visible (this is
    the fix for the silent ImportError pattern flagged in the wiring audit).
    """
    url = f"{_server_base_url()}/internal/watcher/emit"
    body = {"event_type": event_type, "fields": fields, "component": component}
    try:
        requests.post(url, json=body, timeout=2)
    except (requests.RequestException, ConnectionError) as exc:
        log.warning("watcher_bridge POST failed (%s): %s", type(exc).__name__, exc)
```

- [ ] **Step 4: Server-side endpoint to receive bridge events**

**Files:**
- Modify: `sidequest-server/sidequest/server/app.py` (add the route)
- Create: `sidequest-server/tests/server/test_watcher_bridge_endpoint.py`

```python
# sidequest-server/tests/server/test_watcher_bridge_endpoint.py
from fastapi.testclient import TestClient
from unittest.mock import patch
from sidequest.server.app import app


def test_watcher_emit_endpoint_publishes_to_hub():
    client = TestClient(app)
    with patch("sidequest.server.app.publish_event") as mock_publish:
        resp = client.post("/internal/watcher/emit", json={
            "event_type": "test.event",
            "fields": {"k": "v"},
            "component": "daemon",
        })
        assert resp.status_code == 204
        mock_publish.assert_called_once_with(
            event_type="test.event",
            fields={"k": "v"},
            component="daemon",
        )
```

Run: `cd sidequest-server && uv run pytest tests/server/test_watcher_bridge_endpoint.py -v`
Expected: FAIL — route doesn't exist.

Add to `sidequest-server/sidequest/server/app.py` (find the existing route declarations):

```python
from sidequest.telemetry.watcher_hub import publish_event  # if not already imported


@app.post("/internal/watcher/emit", status_code=204)
async def watcher_emit(payload: dict) -> None:
    publish_event(
        event_type=payload["event_type"],
        fields=payload["fields"],
        component=payload.get("component", "daemon"),
    )
```

Run: `cd sidequest-server && uv run pytest tests/server/test_watcher_bridge_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Remove the silent swallows now that the bridge exists**

In `sidequest-daemon/sidequest_daemon/media/prompt_composer.py:43-48`, change:

```python
try:
    from sidequest_daemon.telemetry import emit_watcher_event as _emit_watcher_event
except ImportError:
    # Stand-in when telemetry is not wired; the real module must exist in prod.
    def _emit_watcher_event(name: str, payload: dict) -> None:
        log.debug("otel (unwired): %s %s", name, payload)
```

to:

```python
from sidequest_daemon.telemetry import emit_watcher_event as _emit_watcher_event
```

In `sidequest-daemon/sidequest_daemon/media/daemon.py:718-734`, change:

```python
try:
    from sidequest_daemon.telemetry import (
        emit_watcher_event as _emit_compose_failure,
    )
    _emit_compose_failure(...)
except Exception:  # noqa: BLE001 — telemetry must never crash the error path
    pass
```

to (remove the `try/except`, keep the import + call):

```python
from sidequest_daemon.telemetry import emit_watcher_event as _emit_compose_failure
_emit_compose_failure(
    "daemon_compose_failed",
    {
        "tier": params.get("tier", ""),
        "error_type": type(e).__name__,
        "error_message": str(e)[:512],
        "world": params.get("world", ""),
        "genre": params.get("genre", ""),
        "render_id": params.get("render_id", ""),
    },
)
```

(`emit_watcher_event` itself never raises — failures are logged inside the bridge.)

- [ ] **Step 6: Run the full daemon + server test suites; commit**

Run: `cd sidequest-daemon && uv run pytest -v` and `cd sidequest-server && uv run pytest -v`
Expected: both pass (no new failures from removing the swallows).

```bash
git add sidequest-daemon/sidequest_daemon/telemetry sidequest-daemon/tests/test_watcher_bridge.py \
        sidequest-daemon/sidequest_daemon/media/prompt_composer.py sidequest-daemon/sidequest_daemon/media/daemon.py \
        sidequest-server/sidequest/server/app.py sidequest-server/tests/server/test_watcher_bridge_endpoint.py
git commit -m "fix(daemon): build watcher-event bridge; remove silent ImportError swallows"
```

---

## Task 1: Add `acestep` as a daemon dependency

Verify the local `acestep` package can be imported from the daemon's environment, then add it as a sibling-path dependency in the daemon's `pyproject.toml`.

**Files:**
- Modify: `sidequest-daemon/pyproject.toml`

- [ ] **Step 1: Verify the package imports**

Run: `cd /Users/slabgorb/Projects/ACE-Step && uv run python -c "from acestep.pipeline_ace_step import ACEStepPipeline; print('ok')"`
Expected: `ok` (no traceback). If ImportError: investigate before continuing — the package may need its own install step.

- [ ] **Step 2: Add to daemon's `pyproject.toml`**

In the daemon's `pyproject.toml`, find the `[project]` `dependencies` list. ACE-Step is not on PyPI; install as a local sibling path. Append (or add to `[tool.uv.sources]` section if the file uses uv source overrides):

```toml
# In [project] dependencies — add the package name only:
"ace-step",

# In [tool.uv.sources] — point uv at the sibling directory:
[tool.uv.sources]
ace-step = { path = "../../ACE-Step", editable = true }
```

(If the daemon already uses `[tool.uv.sources]` for other local deps, follow that pattern. If not, add the section.)

- [ ] **Step 3: Sync and verify import from inside the daemon's env**

Run: `cd sidequest-daemon && uv sync && uv run python -c "from acestep.pipeline_ace_step import ACEStepPipeline; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add sidequest-daemon/pyproject.toml sidequest-daemon/uv.lock
git commit -m "feat(daemon): add ace-step as a local sibling-path dependency"
```

---

## Task 2: ACE-Step adapter — strip output fields, override audio_path

Create `ace_step_adapter.py`. First behavior: read JSON params, strip output-only fields (`timecosts`, `actual_seeds[1:]`, `retake_seeds`), override `audio_path` to a daemon-controlled tempfile, force `format="wav"`.

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/ace_step_adapter.py`
- Create: `sidequest-daemon/tests/test_ace_step_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-daemon/tests/test_ace_step_adapter.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from sidequest_daemon.media.ace_step_adapter import (
    AceStepAdapter,
    prepare_inference_params,
)


def test_prepare_inference_params_strips_output_fields(tmp_path):
    raw = {
        "task": "text2music",
        "format": "ogg",  # daemon should force this to wav
        "prompt": "test prompt",
        "lyrics": "[inst]",
        "audio_duration": 60,
        "actual_seeds": [42, 100, 200],         # only [0] preserved
        "retake_seeds": [123],                  # stripped
        "timecosts": {"diffusion": 64.0},       # stripped
        "audio_path": "/Users/keithavery/stale/path.wav",  # overridden
    }
    json_path = tmp_path / "params.json"
    json_path.write_text(json.dumps(raw))
    output_wav = tmp_path / "out.wav"

    cleaned = prepare_inference_params(json_path, output_wav)

    assert cleaned["format"] == "wav"
    assert cleaned["audio_path"] == str(output_wav)
    assert cleaned["actual_seeds"] == [42]
    assert "retake_seeds" not in cleaned
    assert "timecosts" not in cleaned
    assert cleaned["prompt"] == "test prompt"
    assert cleaned["audio_duration"] == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_ace_step_adapter.py::test_prepare_inference_params_strips_output_fields -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest_daemon.media.ace_step_adapter'`.

- [ ] **Step 3: Implement `prepare_inference_params`**

```python
# sidequest-daemon/sidequest_daemon/media/ace_step_adapter.py
"""Thin wrapper over the ACE-Step package.

Isolates the daemon's only contact with the `acestep` API so the rest
of the codebase doesn't depend on it directly. Two responsibilities:

1. Sanitize JSON params (strip output fields, override audio_path,
   require a pinned seed) — see `prepare_inference_params`.
2. Run inference and return the WAV path + seed used — see `AceStepAdapter.run`.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Fields ACE-Step writes back into the JSON after a run; never used as input.
_OUTPUT_ONLY_FIELDS = frozenset({"timecosts", "retake_seeds"})


def prepare_inference_params(json_path: Path, output_wav: Path) -> dict[str, Any]:
    """Read JSON params, strip output fields, override audio_path, force wav.

    Raises ValueError if `actual_seeds[0]` is missing or non-integer
    (no implicit randomness — see spec §4.2 seed contract).
    """
    raw = json.loads(json_path.read_text())

    cleaned = {k: v for k, v in raw.items() if k not in _OUTPUT_ONLY_FIELDS}

    cleaned["format"] = "wav"
    cleaned["audio_path"] = str(output_wav)

    seeds = cleaned.get("actual_seeds")
    if not isinstance(seeds, list) or not seeds or not isinstance(seeds[0], int):
        raise ValueError(
            f"MISSING_SEED: {json_path} must have actual_seeds[0] as an integer "
            f"(got {seeds!r})"
        )
    cleaned["actual_seeds"] = [seeds[0]]

    return cleaned


@dataclass
class InferenceResult:
    wav_path: Path
    seed: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-daemon && uv run pytest tests/test_ace_step_adapter.py::test_prepare_inference_params_strips_output_fields -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/ace_step_adapter.py sidequest-daemon/tests/test_ace_step_adapter.py
git commit -m "feat(daemon): ace_step_adapter prepare_inference_params"
```

---

## Task 3: ACE-Step adapter — missing seed rejection

The seed contract from spec §4.2: missing or non-integer `actual_seeds[0]` raises a clear error.

**Files:**
- Modify: `sidequest-daemon/tests/test_ace_step_adapter.py` (add test)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ace_step_adapter.py`:

```python
def test_prepare_inference_params_rejects_missing_seed(tmp_path):
    raw = {"task": "text2music", "prompt": "x", "audio_duration": 60}  # no actual_seeds
    json_path = tmp_path / "params.json"
    json_path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="MISSING_SEED"):
        prepare_inference_params(json_path, tmp_path / "out.wav")


def test_prepare_inference_params_rejects_empty_seed_list(tmp_path):
    raw = {"task": "text2music", "actual_seeds": []}
    json_path = tmp_path / "params.json"
    json_path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="MISSING_SEED"):
        prepare_inference_params(json_path, tmp_path / "out.wav")


def test_prepare_inference_params_rejects_non_integer_seed(tmp_path):
    raw = {"task": "text2music", "actual_seeds": ["abc"]}
    json_path = tmp_path / "params.json"
    json_path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="MISSING_SEED"):
        prepare_inference_params(json_path, tmp_path / "out.wav")
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd sidequest-daemon && uv run pytest tests/test_ace_step_adapter.py -v`
Expected: PASS (the implementation in Task 2 already enforces this — these tests are regression coverage for the contract).

- [ ] **Step 3: Commit**

```bash
git add sidequest-daemon/tests/test_ace_step_adapter.py
git commit -m "test(daemon): ace_step_adapter rejects missing/invalid seed"
```

---

## Task 4: ACE-Step adapter — `AceStepAdapter.run()` invokes the pipeline

Add the actual inference call. The `acestep` package is mocked in tests; production loads the model lazily.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/ace_step_adapter.py`
- Modify: `sidequest-daemon/tests/test_ace_step_adapter.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ace_step_adapter.py`:

```python
def test_adapter_run_invokes_acestep_pipeline_with_cleaned_params(tmp_path):
    raw = {
        "task": "text2music",
        "prompt": "test",
        "audio_duration": 60,
        "actual_seeds": [42],
    }
    json_path = tmp_path / "params.json"
    json_path.write_text(json.dumps(raw))
    output_wav = tmp_path / "out.wav"

    fake_pipeline = MagicMock()
    fake_pipeline.return_value = None  # ACE-Step writes the file as a side effect

    adapter = AceStepAdapter(_pipeline=fake_pipeline)
    result = adapter.run(json_path, output_wav)

    assert result.wav_path == output_wav
    assert result.seed == 42
    fake_pipeline.assert_called_once()
    # The call kwargs are the cleaned params:
    call_kwargs = fake_pipeline.call_args.kwargs
    assert call_kwargs["audio_path"] == str(output_wav)
    assert call_kwargs["format"] == "wav"
    assert call_kwargs["actual_seeds"] == [42]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_ace_step_adapter.py::test_adapter_run_invokes_acestep_pipeline_with_cleaned_params -v`
Expected: FAIL — `AceStepAdapter` doesn't exist as a class with `run()`.

- [ ] **Step 3: Implement `AceStepAdapter`**

Append to `sidequest_daemon/media/ace_step_adapter.py`:

```python
class AceStepAdapter:
    """Lazy-loaded wrapper over `acestep.pipeline_ace_step.ACEStepPipeline`.

    Inject `_pipeline` in tests to avoid loading the real model. In prod,
    `_pipeline` is None on construction and lazy-loads on first `run()`.
    """

    def __init__(self, *, _pipeline: Any | None = None) -> None:
        self._pipeline = _pipeline

    def _ensure_loaded(self) -> Any:
        if self._pipeline is None:
            from acestep.pipeline_ace_step import ACEStepPipeline
            self._pipeline = ACEStepPipeline()
            log.info("ACE-Step pipeline loaded (cold start)")
        return self._pipeline

    def run(self, json_path: Path, output_wav: Path) -> InferenceResult:
        params = prepare_inference_params(json_path, output_wav)
        pipeline = self._ensure_loaded()
        pipeline(**params)
        return InferenceResult(wav_path=output_wav, seed=params["actual_seeds"][0])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-daemon && uv run pytest tests/test_ace_step_adapter.py -v`
Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/ace_step_adapter.py sidequest-daemon/tests/test_ace_step_adapter.py
git commit -m "feat(daemon): AceStepAdapter.run lazy-loads pipeline and inferes"
```

---

## Task 5: Music pipeline — R2 key derivation

Create `MusicPipeline.derive_r2_key()` — pure function, no I/O. Spec §5.4 rule.

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/music_pipeline.py`
- Create: `sidequest-daemon/tests/test_music_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-daemon/tests/test_music_pipeline.py
from pathlib import Path
import pytest

from sidequest_daemon.media.music_pipeline import MusicPipeline


def test_derive_r2_key_strips_input_params_suffix():
    json_path = Path("/abs/sidequest-content/genre_packs/cav/audio/music/combat_input_params.json")
    key = MusicPipeline.derive_r2_key(json_path)
    assert key == "genre_packs/cav/audio/music/combat.ogg"


def test_derive_r2_key_handles_world_subpacks():
    json_path = Path("/abs/sidequest-content/genre_packs/cav/worlds/sunden/audio/music/combat_input_params.json")
    key = MusicPipeline.derive_r2_key(json_path)
    assert key == "genre_packs/cav/worlds/sunden/audio/music/combat.ogg"


def test_derive_r2_key_rejects_path_outside_genre_packs():
    json_path = Path("/abs/elsewhere/audio/music/combat_input_params.json")
    with pytest.raises(ValueError, match="INVALID_PARAMS_LOCATION"):
        MusicPipeline.derive_r2_key(json_path)


def test_derive_r2_key_rejects_wrong_filename_suffix():
    json_path = Path("/abs/sidequest-content/genre_packs/cav/audio/music/combat.json")
    with pytest.raises(ValueError, match="INVALID_PARAMS_LOCATION"):
        MusicPipeline.derive_r2_key(json_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_pipeline.py::test_derive_r2_key_strips_input_params_suffix -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest_daemon.media.music_pipeline'`.

- [ ] **Step 3: Implement `derive_r2_key`**

```python
# sidequest-daemon/sidequest_daemon/media/music_pipeline.py
"""MusicPipeline — orchestrates one ACE-Step generation job end-to-end.

Reads a per-track JSON params file, derives the R2 destination key from
the file's path, runs the adapter, converts WAV → OGG, uploads to R2,
emits watcher events at every stage. Per spec
docs/superpowers/specs/2026-05-09-daemon-between-session-music-generation-design.md.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_GENRE_PACKS_RE = re.compile(r".*?(genre_packs/.*?)/audio/music/(.+?)_input_params\.json$")


@dataclass
class MusicResult:
    r2_key: str
    duration_ms: int
    seed: int
    elapsed_ms: int


class MusicPipeline:
    """Single-job orchestrator. Constructed once per daemon process,
    reused across requests."""

    def __init__(self, *, adapter, r2_uploader, watcher, render_lock):
        self._adapter = adapter
        self._r2_uploader = r2_uploader
        self._watcher = watcher
        self._render_lock = render_lock

    @staticmethod
    def derive_r2_key(json_path: Path) -> str:
        """Strip `_input_params.json`, append `.ogg`, anchor under
        `genre_packs/<pack>/`. Raises ValueError if path doesn't fit."""
        s = str(json_path)
        m = _GENRE_PACKS_RE.match(s)
        if not m:
            raise ValueError(
                f"INVALID_PARAMS_LOCATION: {json_path} is not under a "
                f"genre_packs/<pack>/audio/music/ directory or is missing "
                f"the _input_params.json suffix"
            )
        pack_path, name = m.group(1), m.group(2)
        return f"{pack_path}/audio/music/{name}.ogg"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_pipeline.py -v`
Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/music_pipeline.py sidequest-daemon/tests/test_music_pipeline.py
git commit -m "feat(daemon): MusicPipeline.derive_r2_key (pure derivation rule)"
```

---

## Task 6: Music pipeline — `generate()` happy path with mocks

Implement `MusicPipeline.generate()` calling adapter → FFmpeg → R2. Mock everything in tests; verify the orchestration shape.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/music_pipeline.py`
- Modify: `sidequest-daemon/tests/test_music_pipeline.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_music_pipeline.py`:

```python
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch


def _write_json(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "task": "text2music",
        "prompt": "x",
        "audio_duration": 60,
        "actual_seeds": [42],
    }))


def test_generate_happy_path_orchestrates_all_stages(tmp_path):
    pack_dir = tmp_path / "genre_packs/cav/audio/music"
    json_path = pack_dir / "combat_input_params.json"
    _write_json(json_path)

    # Mock adapter — pretends to write a wav at the requested path
    def fake_run(jp, output_wav):
        output_wav.write_bytes(b"fake wav bytes")
        from sidequest_daemon.media.ace_step_adapter import InferenceResult
        return InferenceResult(wav_path=output_wav, seed=42)
    adapter = MagicMock()
    adapter.run.side_effect = fake_run

    # Mock R2 uploader — records the call, returns the key
    r2_uploader = MagicMock(return_value="genre_packs/cav/audio/music/combat.ogg")

    # Mock watcher — records emits
    watcher = MagicMock()

    render_lock = asyncio.Lock()

    pipeline = MusicPipeline(
        adapter=adapter, r2_uploader=r2_uploader,
        watcher=watcher, render_lock=render_lock,
    )

    # Patch FFmpeg subprocess to just rename the wav to ogg
    with patch("sidequest_daemon.media.music_pipeline._run_ffmpeg") as mock_ffmpeg:
        def fake_ffmpeg(wav, ogg):
            ogg.write_bytes(b"fake ogg bytes")
        mock_ffmpeg.side_effect = fake_ffmpeg

        result = asyncio.run(pipeline.generate(json_path))

    assert result.r2_key == "genre_packs/cav/audio/music/combat.ogg"
    assert result.seed == 42
    adapter.run.assert_called_once()
    mock_ffmpeg.assert_called_once()
    r2_uploader.assert_called_once()
    # Watcher emitted start + complete:
    event_types = [c.args[0] for c in watcher.call_args_list]
    assert "music.generation.start" in event_types
    assert "music.generation.complete" in event_types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_pipeline.py::test_generate_happy_path_orchestrates_all_stages -v`
Expected: FAIL — `generate` method and `_run_ffmpeg` helper don't exist.

- [ ] **Step 3: Implement `generate()` and `_run_ffmpeg`**

Append to `sidequest_daemon/media/music_pipeline.py`:

```python
import subprocess
import tempfile
import time
from contextlib import contextmanager


def _run_ffmpeg(wav_path: Path, ogg_path: Path) -> None:
    """Convert WAV → OGG (libvorbis q4). Raises CalledProcessError on failure."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path),
         "-c:a", "libvorbis", "-q:a", "4", str(ogg_path)],
        check=True, capture_output=True,
    )


@contextmanager
def _tempdir():
    """Yields a tempdir path; deletes everything on exit (success or failure)."""
    import shutil
    d = Path(tempfile.mkdtemp(prefix="music_pipeline_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


class MusicPipeline:  # extending the class from Task 5
    # ... (keep __init__ and derive_r2_key unchanged) ...

    async def generate(self, json_path: Path) -> MusicResult:
        r2_key = self.derive_r2_key(json_path)
        prompt_excerpt = ""
        try:
            params_for_log = json.loads(json_path.read_text())
            prompt_excerpt = str(params_for_log.get("prompt", ""))[:120]
            duration_s = int(params_for_log.get("audio_duration", 0))
        except Exception:
            duration_s = 0

        self._watcher("music.generation.start", {
            "r2_key": r2_key,
            "prompt_excerpt": prompt_excerpt,
            "duration_s": duration_s,
            "json_params_path": str(json_path),
        })

        t_start = time.perf_counter()
        async with self._render_lock:
            try:
                with _tempdir() as td:
                    wav_path = td / "out.wav"
                    ogg_path = td / "out.ogg"

                    # 1. ACE-Step inference (synchronous; runs under the lock)
                    t0 = time.perf_counter()
                    inference = self._adapter.run(json_path, wav_path)
                    inference_ms = int((time.perf_counter() - t0) * 1000)

                    # 2. WAV → OGG
                    t0 = time.perf_counter()
                    _run_ffmpeg(wav_path, ogg_path)
                    ffmpeg_ms = int((time.perf_counter() - t0) * 1000)

                    # 3. Upload to R2
                    t0 = time.perf_counter()
                    self._r2_uploader(
                        ogg_path.read_bytes(), r2_key, "audio/ogg",
                    )
                    upload_ms = int((time.perf_counter() - t0) * 1000)
                    file_size = ogg_path.stat().st_size

                elapsed_ms = int((time.perf_counter() - t_start) * 1000)
                self._watcher("music.generation.complete", {
                    "r2_key": r2_key,
                    "elapsed_ms": elapsed_ms,
                    "inference_ms": inference_ms,
                    "ffmpeg_ms": ffmpeg_ms,
                    "upload_ms": upload_ms,
                    "seed": inference.seed,
                    "file_size_bytes": file_size,
                })
                return MusicResult(
                    r2_key=r2_key, duration_ms=duration_s * 1000,
                    seed=inference.seed, elapsed_ms=elapsed_ms,
                )

            except Exception as exc:
                # Failure event includes stage attribution
                stage = self._classify_failure_stage(exc)
                self._watcher("music.generation.failed", {
                    "r2_key": r2_key,
                    "error_code": type(exc).__name__,
                    "stage": stage,
                    "detail": str(exc)[:512],
                })
                raise

    @staticmethod
    def _classify_failure_stage(exc: Exception) -> str:
        # Best-effort classification by exception type/message.
        msg = str(exc).lower()
        if "ffmpeg" in msg or isinstance(exc, subprocess.CalledProcessError):
            return "ffmpeg"
        if "missing_seed" in msg or "invalid_params" in msg:
            return "params"
        if "r2" in msg or "boto" in msg or "s3" in msg:
            return "upload"
        return "inference"
```

Add the `import json` at the top of the file if not already present.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_pipeline.py::test_generate_happy_path_orchestrates_all_stages -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/music_pipeline.py sidequest-daemon/tests/test_music_pipeline.py
git commit -m "feat(daemon): MusicPipeline.generate() happy path"
```

---

## Task 7: Music pipeline — failure path emits failed event with stage

Verify each error stage produces a `music.generation.failed` watcher event with the correct `stage`.

**Files:**
- Modify: `sidequest-daemon/tests/test_music_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_music_pipeline.py`:

```python
def test_generate_inference_failure_emits_failed_event_stage_inference(tmp_path):
    pack_dir = tmp_path / "genre_packs/cav/audio/music"
    json_path = pack_dir / "combat_input_params.json"
    _write_json(json_path)

    adapter = MagicMock()
    adapter.run.side_effect = RuntimeError("CUDA OOM")
    pipeline = MusicPipeline(
        adapter=adapter, r2_uploader=MagicMock(),
        watcher=MagicMock(), render_lock=asyncio.Lock(),
    )
    with pytest.raises(RuntimeError):
        asyncio.run(pipeline.generate(json_path))

    failed_calls = [c for c in pipeline._watcher.call_args_list
                    if c.args[0] == "music.generation.failed"]
    assert len(failed_calls) == 1
    assert failed_calls[0].args[1]["stage"] == "inference"


def test_generate_ffmpeg_failure_emits_failed_event_stage_ffmpeg(tmp_path):
    pack_dir = tmp_path / "genre_packs/cav/audio/music"
    json_path = pack_dir / "combat_input_params.json"
    _write_json(json_path)

    def fake_run(jp, output_wav):
        output_wav.write_bytes(b"fake")
        from sidequest_daemon.media.ace_step_adapter import InferenceResult
        return InferenceResult(wav_path=output_wav, seed=42)
    adapter = MagicMock()
    adapter.run.side_effect = fake_run

    pipeline = MusicPipeline(
        adapter=adapter, r2_uploader=MagicMock(),
        watcher=MagicMock(), render_lock=asyncio.Lock(),
    )
    with patch("sidequest_daemon.media.music_pipeline._run_ffmpeg") as mock_ffmpeg:
        import subprocess
        mock_ffmpeg.side_effect = subprocess.CalledProcessError(1, "ffmpeg")
        with pytest.raises(subprocess.CalledProcessError):
            asyncio.run(pipeline.generate(json_path))

    failed_calls = [c for c in pipeline._watcher.call_args_list
                    if c.args[0] == "music.generation.failed"]
    assert failed_calls[0].args[1]["stage"] == "ffmpeg"


def test_generate_params_failure_emits_failed_event_stage_params(tmp_path):
    # Path not under genre_packs → INVALID_PARAMS_LOCATION raised inside generate
    json_path = tmp_path / "elsewhere/combat_input_params.json"
    _write_json(json_path)

    pipeline = MusicPipeline(
        adapter=MagicMock(), r2_uploader=MagicMock(),
        watcher=MagicMock(), render_lock=asyncio.Lock(),
    )
    with pytest.raises(ValueError, match="INVALID_PARAMS_LOCATION"):
        asyncio.run(pipeline.generate(json_path))

    # No watcher event — derive_r2_key fails before the start event fires
    # (this is acceptable; the daemon dispatch reports the error in the reply).
    assert pipeline._watcher.call_count == 0
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_pipeline.py -v`
Expected: PASS for inference and ffmpeg cases. The params case may need a small adjustment if the third assertion is wrong — read the implementation to confirm; if `derive_r2_key` is called BEFORE the start watcher event, the test as written is correct.

- [ ] **Step 3: Commit**

```bash
git add sidequest-daemon/tests/test_music_pipeline.py
git commit -m "test(daemon): MusicPipeline failed-event stage classification"
```

---

## Task 8: Music pipeline — tempfile cleanup on failure

Verify the `_tempdir` context manager actually deletes the working directory on every exit path.

**Files:**
- Modify: `sidequest-daemon/tests/test_music_pipeline.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_generate_cleans_tempfiles_on_failure(tmp_path):
    pack_dir = tmp_path / "genre_packs/cav/audio/music"
    json_path = pack_dir / "combat_input_params.json"
    _write_json(json_path)

    captured_tempdirs = []
    def capturing_run(jp, output_wav):
        captured_tempdirs.append(output_wav.parent)
        raise RuntimeError("fail in inference")
    adapter = MagicMock()
    adapter.run.side_effect = capturing_run

    pipeline = MusicPipeline(
        adapter=adapter, r2_uploader=MagicMock(),
        watcher=MagicMock(), render_lock=asyncio.Lock(),
    )
    with pytest.raises(RuntimeError):
        asyncio.run(pipeline.generate(json_path))

    assert len(captured_tempdirs) == 1
    assert not captured_tempdirs[0].exists(), \
        f"tempdir {captured_tempdirs[0]} should have been cleaned up"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_pipeline.py::test_generate_cleans_tempfiles_on_failure -v`
Expected: PASS (the `_tempdir` context manager already handles this).

- [ ] **Step 3: Commit**

```bash
git add sidequest-daemon/tests/test_music_pipeline.py
git commit -m "test(daemon): MusicPipeline cleans tempdir on failure"
```

---

## Task 9: R2 uploader for genre-pack assets

The existing `r2_writer.upload_artifact()` writes to `artifacts/<world>/<session>/...`. Music tracks need `genre_packs/<pack>/audio/music/<file>.ogg` — different path scheme. Add a sibling `upload_pack_asset()`.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/r2_writer.py`
- Create: `sidequest-daemon/tests/test_r2_writer_pack_asset.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-daemon/tests/test_r2_writer_pack_asset.py
from unittest.mock import patch, MagicMock

from sidequest_daemon.media.r2_writer import upload_pack_asset


def test_upload_pack_asset_writes_to_provided_key():
    fake_client = MagicMock()
    with patch("sidequest_daemon.media.r2_writer._client", return_value=fake_client):
        key = upload_pack_asset(
            r2_key="genre_packs/cav/audio/music/combat.ogg",
            content_bytes=b"fake ogg bytes",
            content_type="audio/ogg",
        )
        assert key == "genre_packs/cav/audio/music/combat.ogg"
        fake_client.put_object.assert_called_once()
        call_kwargs = fake_client.put_object.call_args.kwargs
        assert call_kwargs["Key"] == "genre_packs/cav/audio/music/combat.ogg"
        assert call_kwargs["Body"] == b"fake ogg bytes"
        assert call_kwargs["ContentType"] == "audio/ogg"


def test_upload_pack_asset_rejects_key_outside_genre_packs():
    import pytest
    with pytest.raises(ValueError, match="must start with 'genre_packs/'"):
        upload_pack_asset(
            r2_key="artifacts/foo/bar.ogg",
            content_bytes=b"x",
            content_type="audio/ogg",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_r2_writer_pack_asset.py -v`
Expected: FAIL — `upload_pack_asset` doesn't exist.

- [ ] **Step 3: Implement `upload_pack_asset`**

Append to `sidequest_daemon/media/r2_writer.py`:

```python
def upload_pack_asset(
    *,
    r2_key: str,
    content_bytes: bytes,
    content_type: str,
) -> str:
    """Upload `content_bytes` to R2 at `r2_key` (must start with `genre_packs/`).

    Distinct from `upload_artifact`, which writes session-scoped ephemeral
    content under `artifacts/<world>/<session>/...`. Pack assets use the
    raw key the caller provides — the JSON params file's location IS the
    identity (see music_pipeline.derive_r2_key).

    Returns the key. Raises ValueError on invalid key. Propagates any
    boto3 error verbatim — caller surfaces failure (no silent fallback).
    """
    if not r2_key.startswith("genre_packs/"):
        raise ValueError(f"r2_key must start with 'genre_packs/', got {r2_key!r}")
    if content_type not in _EXT_FOR_CONTENT_TYPE:
        raise ValueError(
            f"content_type must be one of {sorted(_EXT_FOR_CONTENT_TYPE)}, "
            f"got {content_type!r}"
        )

    tracer = _get_tracer()
    size = len(content_bytes)
    t0 = time.perf_counter()

    with tracer.start_as_current_span("daemon.r2.upload.pack_asset") as span:
        span.set_attribute("upload.key", r2_key)
        span.set_attribute("upload.bytes", size)
        try:
            _client().put_object(
                Bucket=BUCKET,
                Key=r2_key,
                Body=content_bytes,
                ContentType=content_type,
                CacheControl=CACHE_CONTROL_ARTIFACTS,
            )
        except Exception as exc:
            span.set_attribute("upload.error_class", exc.__class__.__name__)
            span.set_attribute("upload.error_message", str(exc))
            raise
        dt_ms = int((time.perf_counter() - t0) * 1000)
        span.set_attribute("upload.ms", dt_ms)

    return r2_key
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-daemon && uv run pytest tests/test_r2_writer_pack_asset.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/r2_writer.py sidequest-daemon/tests/test_r2_writer_pack_asset.py
git commit -m "feat(daemon): r2_writer.upload_pack_asset for genre-pack-keyed content"
```

---

## Task 10: Daemon dispatch — `MUSIC_TIERS` constant + tier=music branch (THE WIRING TEST)

Add the dispatch branch in `daemon.py` that routes `tier=music` to a `MusicPipeline` instance. This is the wiring test that prevents the "feature exists but nothing reaches it" failure mode.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/daemon.py`
- Create: `sidequest-daemon/tests/test_music_dispatch.py`

- [ ] **Step 1: Write the failing wiring test**

```python
# sidequest-daemon/tests/test_music_dispatch.py
"""Wiring test — proves tier=music reaches MusicPipeline from a real
socket request shape. Prevents the deferral-cascade failure mode from
recurring (feature implemented, never reached)."""
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


@pytest.mark.asyncio
async def test_dispatch_routes_music_tier_to_music_pipeline(tmp_path):
    pack_dir = tmp_path / "genre_packs/cav/audio/music"
    pack_dir.mkdir(parents=True)
    json_path = pack_dir / "combat_input_params.json"
    json_path.write_text(json.dumps({
        "task": "text2music", "prompt": "x", "audio_duration": 60,
        "actual_seeds": [42],
    }))

    # The exact request shape the production script sends:
    request = {
        "id": "music-test-1",
        "method": "render",
        "params": {"tier": "music", "json_params_path": str(json_path)},
    }

    from sidequest_daemon.media.music_pipeline import MusicPipeline, MusicResult

    fake_pipeline = MagicMock(spec=MusicPipeline)
    fake_pipeline.generate = AsyncMock(return_value=MusicResult(
        r2_key="genre_packs/cav/audio/music/combat.ogg",
        duration_ms=60_000, seed=42, elapsed_ms=67_000,
    ))

    from sidequest_daemon.media.daemon import dispatch_request
    reply = await dispatch_request(request, music_pipeline=fake_pipeline)

    fake_pipeline.generate.assert_called_once_with(Path(json_path))
    assert reply["result"]["r2_key"] == "genre_packs/cav/audio/music/combat.ogg"
    assert reply["result"]["seed"] == 42


@pytest.mark.asyncio
async def test_dispatch_unknown_tier_still_raises_loudly():
    """Regression: tier=foo must still raise ValueError. No silent fallback."""
    from sidequest_daemon.media.daemon import dispatch_request
    request = {
        "id": "x",
        "method": "render",
        "params": {"tier": "foo"},
    }
    with pytest.raises(ValueError, match="Unknown tier"):
        await dispatch_request(request)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_dispatch.py -v`
Expected: FAIL — `dispatch_request` likely doesn't exist as a top-level function (the dispatch is inline inside `_handle_client`).

- [ ] **Step 3: Extract `dispatch_request` and add the music branch**

Read `sidequest-daemon/sidequest_daemon/media/daemon.py` around line 329 (the existing inline dispatch). Extract the routing logic into a new `dispatch_request` function that the test can call directly. Add a `MUSIC_TIERS = {"music"}` constant near `IMAGE_TIERS`. The branch:

```python
# Near IMAGE_TIERS definition, add:
MUSIC_TIERS: Final[frozenset[str]] = frozenset({"music"})


# Extract or refactor the dispatch into a top-level async function.
# Existing inline dispatch from `_handle_client` near line 329:
#
#   tier = params.get("tier", "")
#   if tier in IMAGE_TIERS:
#       ...
#   else:
#       raise ValueError(f"Unknown tier: {tier!r}")
#
# becomes:

async def dispatch_request(
    request: dict,
    *,
    music_pipeline: "MusicPipeline | None" = None,
    # ...other dependencies the existing inline logic needs (image worker,
    # embed worker, locks). Pass-through so the existing _handle_client
    # caller keeps working.
) -> dict:
    method = request.get("method")
    if method != "render":
        # Other methods (ping, status, warm_up, embed, shutdown) handled
        # elsewhere — leave them untouched for now.
        raise NotImplementedError(f"dispatch_request only handles 'render', got {method!r}")

    params = request.get("params", {})
    tier = params.get("tier", "")
    if tier in IMAGE_TIERS:
        # ... existing image branch (unchanged) ...
        raise NotImplementedError("test should not exercise image branch")
    elif tier in MUSIC_TIERS:
        if music_pipeline is None:
            raise RuntimeError("MusicPipeline not initialized")
        result = await music_pipeline.generate(Path(params["json_params_path"]))
        return {"id": request.get("id"), "result": {
            "r2_key": result.r2_key,
            "duration_ms": result.duration_ms,
            "seed": result.seed,
            "elapsed_ms": result.elapsed_ms,
        }}
    else:
        raise ValueError(f"Unknown tier: {tier!r}")
```

> **Implementer note:** the existing dispatch logic in `_handle_client` is large. The minimum-viable extraction for this task is to factor out *just* the routing decision into `dispatch_request`, leaving the heavy image-tier code in place via callbacks or moved verbatim. Choose the smaller diff. The wiring test only exercises the music branch and the unknown-tier regression — image dispatch behavior must remain unchanged but doesn't need to be tested by this task.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_dispatch.py -v`
Expected: PASS for both tests.

- [ ] **Step 5: Run the full daemon test suite to catch regressions**

Run: `cd sidequest-daemon && uv run pytest -v`
Expected: PASS (no image-dispatch tests broken by the extraction).

- [ ] **Step 6: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/daemon.py sidequest-daemon/tests/test_music_dispatch.py
git commit -m "feat(daemon): dispatch routes tier=music to MusicPipeline"
```

---

## Task 11: Pipeline factory — repurpose to construct MusicPipeline

Repurpose `MediaPipelineFactory` to construct the music pipeline and stop constructing the orphaned audio module.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/pipeline_factory.py`
- Create: `sidequest-daemon/tests/test_pipeline_factory_music.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-daemon/tests/test_pipeline_factory_music.py
import asyncio
from sidequest_daemon.media.pipeline_factory import MediaPipelineFactory
from sidequest_daemon.media.music_pipeline import MusicPipeline


def test_factory_constructs_music_pipeline():
    factory = MediaPipelineFactory()
    factory.init_music(render_lock=asyncio.Lock())
    assert isinstance(factory.music_pipeline, MusicPipeline)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_pipeline_factory_music.py -v`
Expected: FAIL — `init_music` doesn't exist; `music_pipeline` attribute doesn't exist.

- [ ] **Step 3: Implement `init_music`**

Replace the contents of `sidequest_daemon/media/pipeline_factory.py` with:

```python
"""MediaPipelineFactory — constructs the music pipeline at daemon startup.

Previously constructed an audio playback pipeline (mixer, queue, etc.)
that had no production consumers. That tree was deleted; this factory
now exists solely to wire the music generation pipeline. Image rendering
is constructed elsewhere; this file is music-only for now.
"""
from __future__ import annotations

import asyncio
import logging

from sidequest_daemon.media.ace_step_adapter import AceStepAdapter
from sidequest_daemon.media.music_pipeline import MusicPipeline
from sidequest_daemon.media.r2_writer import upload_pack_asset
from sidequest_daemon.telemetry import emit_watcher_event

log = logging.getLogger(__name__)


class MediaPipelineFactory:
    """Lazy constructor for the music generation pipeline."""

    def __init__(self) -> None:
        self.music_pipeline: MusicPipeline | None = None

    def init_music(self, *, render_lock: asyncio.Lock) -> None:
        """Construct the music pipeline. Called once at daemon startup."""
        adapter = AceStepAdapter()  # production: lazy-loads model on first run

        def _r2_uploader(content_bytes: bytes, r2_key: str, content_type: str) -> str:
            return upload_pack_asset(
                r2_key=r2_key,
                content_bytes=content_bytes,
                content_type=content_type,
            )

        def _watcher(event_type: str, fields: dict) -> None:
            emit_watcher_event(event_type, fields, component="daemon.music")

        self.music_pipeline = MusicPipeline(
            adapter=adapter,
            r2_uploader=_r2_uploader,
            watcher=_watcher,
            render_lock=render_lock,
        )
        log.info("MusicPipeline initialized")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-daemon && uv run pytest tests/test_pipeline_factory_music.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/pipeline_factory.py sidequest-daemon/tests/test_pipeline_factory_music.py
git commit -m "feat(daemon): MediaPipelineFactory.init_music constructs MusicPipeline"
```

---

## Task 12: Wire factory into `_run_daemon` and dispatch

Update `_run_daemon` (in `daemon.py` around line 1046) to call `init_music()` and pass the constructed `music_pipeline` to dispatch.

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/daemon.py`

- [ ] **Step 1: Read `_run_daemon` to understand its current shape**

Run: `grep -n "_run_daemon\|init_audio\|MediaPipelineFactory" sidequest-daemon/sidequest_daemon/media/daemon.py`
Find the existing `MediaPipelineFactory(...)` construction site (~line 1048).

- [ ] **Step 2: Update the construction site**

Replace:

```python
pipeline_factory = MediaPipelineFactory(
    genre_pack=...,           # whatever args were here
    audio_base_path=...,
)
pool.pipeline_factory = pipeline_factory
log.info("MediaPipelineFactory initialized (audio pipeline deferred until session)")
```

with:

```python
pipeline_factory = MediaPipelineFactory()
pipeline_factory.init_music(render_lock=render_lock)
pool.pipeline_factory = pipeline_factory
log.info("MediaPipelineFactory initialized (music pipeline ready)")
```

- [ ] **Step 3: Update the dispatch call site to pass `music_pipeline`**

In the `dispatch_request` invocation inside `_handle_client`, pass:

```python
reply = await dispatch_request(
    request,
    music_pipeline=pool.pipeline_factory.music_pipeline,
    # ... other existing pass-throughs ...
)
```

- [ ] **Step 4: Run the full daemon test suite to verify nothing broken**

Run: `cd sidequest-daemon && uv run pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-daemon/sidequest_daemon/media/daemon.py
git commit -m "feat(daemon): _run_daemon wires music_pipeline into dispatch"
```

---

## Task 13: Integration test — mocked adapter writing real WAV → real FFmpeg → mock R2

Bigger test that exercises the real FFmpeg subprocess against a known sine-wave WAV. Catches "the dispatch wires up but FFmpeg isn't installed" / "wrong codec" classes of bug.

**Files:**
- Create: `sidequest-daemon/tests/test_music_pipeline_integration.py`

- [ ] **Step 1: Write the integration test**

```python
# sidequest-daemon/tests/test_music_pipeline_integration.py
"""Integration test — exercises real FFmpeg subprocess but mocks
ACE-Step (no GPU) and R2 (no network). Catches plumbing issues that
unit tests miss: FFmpeg not installed, wrong codec, file handles, etc.
"""
import asyncio
import json
import math
import struct
import wave
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidequest_daemon.media.ace_step_adapter import InferenceResult
from sidequest_daemon.media.music_pipeline import MusicPipeline


def _write_sine_wav(path: Path, duration_s: int = 1, freq: float = 440.0) -> None:
    """Write a 1-second 440Hz sine wave at 44.1kHz, 16-bit mono."""
    sample_rate = 44100
    n_samples = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for i in range(n_samples):
            value = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate))
            w.writeframes(struct.pack("<h", value))


@pytest.mark.asyncio
async def test_full_pipeline_with_real_ffmpeg(tmp_path):
    pack_dir = tmp_path / "genre_packs/cav/audio/music"
    json_path = pack_dir / "combat_input_params.json"
    pack_dir.mkdir(parents=True)
    json_path.write_text(json.dumps({
        "task": "text2music", "prompt": "x", "audio_duration": 1,
        "actual_seeds": [42],
    }))

    # Adapter writes a real sine WAV to the requested output path
    def fake_adapter_run(jp, output_wav):
        _write_sine_wav(output_wav, duration_s=1)
        return InferenceResult(wav_path=output_wav, seed=42)
    adapter = MagicMock()
    adapter.run.side_effect = fake_adapter_run

    # R2 uploader records the bytes it would upload
    uploaded_bytes = []
    def capture_upload(content_bytes, r2_key, content_type):
        uploaded_bytes.append((r2_key, content_type, len(content_bytes)))
        return r2_key

    pipeline = MusicPipeline(
        adapter=adapter,
        r2_uploader=capture_upload,
        watcher=MagicMock(),
        render_lock=asyncio.Lock(),
    )

    result = await pipeline.generate(json_path)

    assert result.r2_key == "genre_packs/cav/audio/music/combat.ogg"
    assert len(uploaded_bytes) == 1
    r2_key, content_type, byte_count = uploaded_bytes[0]
    assert r2_key == "genre_packs/cav/audio/music/combat.ogg"
    assert content_type == "audio/ogg"
    assert byte_count > 100  # OGG of 1s sine should be at least a few hundred bytes
```

- [ ] **Step 2: Run the integration test**

Run: `cd sidequest-daemon && uv run pytest tests/test_music_pipeline_integration.py -v`
Expected: PASS. If FFmpeg isn't installed, this fails with `FileNotFoundError` — install FFmpeg and rerun.

- [ ] **Step 3: Commit**

```bash
git add sidequest-daemon/tests/test_music_pipeline_integration.py
git commit -m "test(daemon): MusicPipeline integration with real FFmpeg"
```

---

## Task 14: Delete the orphaned `sidequest_daemon/audio/` module

The old playback pipeline (~1500 LOC, zero callers) is now safely removable: `MediaPipelineFactory` no longer imports from it (Task 11), nothing else does either (audit confirmed).

**Files (deletions):**
- `sidequest-daemon/sidequest_daemon/audio/__init__.py`
- `sidequest-daemon/sidequest_daemon/audio/mixer.py`
- `sidequest-daemon/sidequest_daemon/audio/interpreter.py`
- `sidequest-daemon/sidequest_daemon/audio/queue.py`
- `sidequest-daemon/sidequest_daemon/audio/library_backend.py`
- `sidequest-daemon/sidequest_daemon/audio/rotator.py`
- `sidequest-daemon/sidequest_daemon/audio/protocol.py`
- `sidequest-daemon/sidequest_daemon/audio/models.py`

Plus any tests under `sidequest-daemon/tests/` that exercise the deleted module — find them with `grep -rln "sidequest_daemon.audio" sidequest-daemon/tests/` and delete those test files too (they will fail to import after deletion).

- [ ] **Step 1: Confirm no production consumers**

Run: `grep -rn "sidequest_daemon.audio" sidequest-daemon/sidequest_daemon/ --include="*.py" | grep -v __pycache__`
Expected: zero hits (after Task 11's `pipeline_factory.py` rewrite).

If any non-test file still imports from `sidequest_daemon.audio`, STOP and investigate before deleting.

- [ ] **Step 2: Find associated tests**

Run: `grep -rln "sidequest_daemon.audio\|from sidequest_daemon import audio" sidequest-daemon/tests/`
Note the file list — these tests will be deleted alongside the module.

- [ ] **Step 3: Delete the module and its tests**

```bash
git rm -r sidequest-daemon/sidequest_daemon/audio/
# Then delete each test file from step 2:
git rm sidequest-daemon/tests/test_<orphaned_audio>.py  # repeat per file
```

- [ ] **Step 4: Run full daemon suite**

Run: `cd sidequest-daemon && uv run pytest -v`
Expected: PASS. If anything fails, the deletion missed a consumer — investigate.

- [ ] **Step 5: Commit**

```bash
git commit -m "chore(daemon): delete orphaned sidequest_daemon/audio/ module (~1500 LOC, 0 callers)"
```

---

## Task 15: Refactored `scripts/generate_music.py` — `discover_jobs`

Start the script refactor. New `discover_jobs` walks JSON params files and returns `(json_path, expected_r2_key)` pairs.

**Files:**
- Create: `tests/scripts/__init__.py` (empty)
- Create: `tests/scripts/test_generate_music.py`
- Modify: `scripts/generate_music.py` (start carving up the existing file)

- [ ] **Step 1: Write the failing test**

```python
# tests/scripts/test_generate_music.py
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from generate_music import discover_jobs


def test_discover_jobs_walks_pack_audio_music_dir(tmp_path):
    pack_dir = tmp_path / "genre_packs" / "cav"
    music_dir = pack_dir / "audio" / "music"
    music_dir.mkdir(parents=True)
    (music_dir / "combat_input_params.json").write_text("{}")
    (music_dir / "tension_input_params.json").write_text("{}")
    (music_dir / "ignore_me.json").write_text("{}")  # missing _input_params suffix

    jobs = discover_jobs(pack_dir)

    by_key = {key: path for path, key in jobs}
    assert "genre_packs/cav/audio/music/combat.ogg" in by_key
    assert "genre_packs/cav/audio/music/tension.ogg" in by_key
    assert len(jobs) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2 && uv run --project sidequest-server pytest tests/scripts/test_generate_music.py -v`
(Or install pytest standalone — pick whatever environment runs the orchestrator-level tests.)
Expected: FAIL — `discover_jobs` doesn't exist yet.

- [ ] **Step 3: Add `discover_jobs` to `scripts/generate_music.py`**

At the top of `scripts/generate_music.py`, add a new function (before main, leave the existing GENRE_MOODS dict in place for now — we'll delete it in Task 19):

```python
import re

_GENRE_PACKS_RE = re.compile(r".*?(genre_packs/.*?)/audio/music/(.+?)_input_params\.json$")


def discover_jobs(pack_dir: Path) -> list[tuple[Path, str]]:
    """Walk `<pack_dir>/audio/music/**` for *_input_params.json files.

    Returns list of (json_path, expected_r2_key) tuples. R2 key derivation
    matches the daemon's MusicPipeline.derive_r2_key — strip
    `_input_params.json`, append `.ogg`, anchor under `genre_packs/`.
    """
    jobs = []
    for json_path in pack_dir.glob("**/audio/music/*_input_params.json"):
        m = _GENRE_PACKS_RE.match(str(json_path))
        if not m:
            continue
        pack_path, name = m.group(1), m.group(2)
        r2_key = f"{pack_path}/audio/music/{name}.ogg"
        jobs.append((json_path, r2_key))
    return jobs
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command as step 2.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_music.py tests/scripts/__init__.py tests/scripts/test_generate_music.py
git commit -m "feat(scripts): generate_music.discover_jobs walks JSON params"
```

---

## Task 16: Script — `is_in_r2` HEAD check

Add the skip-if-present check using SIDEQUEST_ASSET_BASE_URL.

**Files:**
- Modify: `scripts/generate_music.py`
- Modify: `tests/scripts/test_generate_music.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_generate_music.py`:

```python
from unittest.mock import patch, MagicMock
import os
from generate_music import is_in_r2


def test_is_in_r2_returns_true_on_http_200():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SIDEQUEST_ASSET_BASE_URL", None)
        with patch("generate_music.requests.head") as mock_head:
            mock_head.return_value = MagicMock(status_code=200)
            assert is_in_r2("genre_packs/cav/audio/music/combat.ogg") is True
            mock_head.assert_called_once_with(
                "https://cdn.slabgorb.com/genre_packs/cav/audio/music/combat.ogg",
                timeout=5,
            )


def test_is_in_r2_returns_false_on_http_404():
    with patch("generate_music.requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)
        assert is_in_r2("genre_packs/cav/audio/music/combat.ogg") is False


def test_is_in_r2_honors_asset_base_url_env(monkeypatch):
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "http://localhost:8765")
    with patch("generate_music.requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)
        is_in_r2("genre_packs/cav/audio/music/combat.ogg")
        url = mock_head.call_args[0][0]
        assert url.startswith("http://localhost:8765/")
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL — `is_in_r2` doesn't exist.

- [ ] **Step 3: Implement `is_in_r2`**

Add to `scripts/generate_music.py` (also add `import requests` and `import os` at the top if not already present):

```python
def _asset_base_url() -> str:
    return os.environ.get("SIDEQUEST_ASSET_BASE_URL", "https://cdn.slabgorb.com").rstrip("/")


def is_in_r2(r2_key: str) -> bool:
    """HTTP HEAD against the public CDN. Returns True if 200, False if 404.
    Other status codes (or network errors) propagate as exceptions —
    we don't silently treat 'unreachable' as 'not present'."""
    url = f"{_asset_base_url()}/{r2_key.lstrip('/')}"
    resp = requests.head(url, timeout=5)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False  # unreachable, but appease type checker
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_music.py tests/scripts/test_generate_music.py
git commit -m "feat(scripts): generate_music.is_in_r2 HEAD with SIDEQUEST_ASSET_BASE_URL"
```

---

## Task 17: Script — `--track` and `--force` flags

Add the two new CLI flags (replacing the deleted `--mood` and `--variation`).

**Files:**
- Modify: `scripts/generate_music.py`
- Modify: `tests/scripts/test_generate_music.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_generate_music.py`:

```python
def test_filter_jobs_by_track_returns_only_matching_stem():
    from generate_music import filter_jobs_by_track
    jobs = [
        (Path("/x/genre_packs/cav/audio/music/combat_input_params.json"),
         "genre_packs/cav/audio/music/combat.ogg"),
        (Path("/x/genre_packs/cav/audio/music/tension_input_params.json"),
         "genre_packs/cav/audio/music/tension.ogg"),
    ]
    filtered = filter_jobs_by_track(jobs, "combat")
    assert len(filtered) == 1
    assert filtered[0][1] == "genre_packs/cav/audio/music/combat.ogg"


def test_filter_jobs_by_track_returns_empty_when_no_match():
    from generate_music import filter_jobs_by_track
    jobs = [
        (Path("/x/genre_packs/cav/audio/music/combat_input_params.json"),
         "genre_packs/cav/audio/music/combat.ogg"),
    ]
    assert filter_jobs_by_track(jobs, "nonexistent") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL — `filter_jobs_by_track` doesn't exist.

- [ ] **Step 3: Implement `filter_jobs_by_track`**

Add to `scripts/generate_music.py`:

```python
def filter_jobs_by_track(jobs: list[tuple[Path, str]], track: str) -> list[tuple[Path, str]]:
    """Narrow the job list to entries whose JSON file is named
    `<track>_input_params.json`. Used by the --track CLI flag."""
    target = f"{track}_input_params.json"
    return [(jp, key) for jp, key in jobs if jp.name == target]
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_music.py tests/scripts/test_generate_music.py
git commit -m "feat(scripts): generate_music.filter_jobs_by_track for --track flag"
```

---

## Task 18: Script — refactored main loop, delete dict and companions

Now do the destructive refactor: delete `GENRE_MOODS`, `VARIATION_SUFFIXES`, `compute_seed`, `wav_to_ogg`, the `--mood/--variation/--duration` CLI args. Rewrite `main()` to use `discover_jobs` + `is_in_r2` + `filter_jobs_by_track` and a `--track`/`--force` flag.

**Files:**
- Modify: `scripts/generate_music.py`

- [ ] **Step 1: Write the failing test for the new request shape**

Append to `tests/scripts/test_generate_music.py`:

```python
@pytest.mark.asyncio
async def test_send_render_uses_json_params_path_payload(tmp_path):
    """The script's send_render must build the request shape the daemon expects."""
    import asyncio as aio
    from unittest.mock import AsyncMock, patch
    from generate_music import send_render

    json_path = tmp_path / "combat_input_params.json"
    json_path.write_text("{}")

    fake_reader = AsyncMock()
    fake_reader.readline = AsyncMock(return_value=b'{"id":"x","result":{"r2_key":"k","seed":42,"duration_ms":60000,"elapsed_ms":67000}}\n')
    fake_writer = MagicMock()
    fake_writer.drain = AsyncMock()
    fake_writer.wait_closed = AsyncMock()

    with patch("generate_music.asyncio.open_unix_connection", AsyncMock(return_value=(fake_reader, fake_writer))):
        result = await send_render(json_path)

    written = fake_writer.write.call_args[0][0].decode()
    payload = json.loads(written)
    assert payload["method"] == "render"
    assert payload["params"]["tier"] == "music"
    assert payload["params"]["json_params_path"] == str(json_path)
```

(Add `import json` and `import pytest` at the top of the test file if not already present.)

- [ ] **Step 2: Replace the entire script body**

Open `scripts/generate_music.py` and **replace its entire content** with this refactored version (the destructive change — `GENRE_MOODS`, `VARIATION_SUFFIXES`, `compute_seed`, `wav_to_ogg` all deleted):

```python
#!/usr/bin/env python3
"""Walk per-track JSON params files in a genre pack and dispatch each
to the daemon for ACE-Step generation.

Source of truth: `<pack>/audio/music/*_input_params.json` files.
Output: R2 at `genre_packs/<pack>/audio/music/<track>.ogg`.

Usage:
    python scripts/generate_music.py --genre <pack>           # all missing
    python scripts/generate_music.py --genre <pack> --track combat
    python scripts/generate_music.py --genre <pack> --force   # re-render existing
    python scripts/generate_music.py --genre <pack> --dry-run

See docs/superpowers/specs/2026-05-09-daemon-between-session-music-generation-design.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests

SOCKET_PATH = Path("/tmp/sidequest-renderer.sock")
_root = Path(__file__).resolve().parent.parent
GENRE_PACKS_DIR = _root / "sidequest-content" / "genre_packs"

log = logging.getLogger(__name__)

_GENRE_PACKS_RE = re.compile(r".*?(genre_packs/.*?)/audio/music/(.+?)_input_params\.json$")


def discover_jobs(pack_dir: Path) -> list[tuple[Path, str]]:
    jobs = []
    for json_path in pack_dir.glob("**/audio/music/*_input_params.json"):
        m = _GENRE_PACKS_RE.match(str(json_path))
        if not m:
            continue
        pack_path, name = m.group(1), m.group(2)
        r2_key = f"{pack_path}/audio/music/{name}.ogg"
        jobs.append((json_path, r2_key))
    return jobs


def filter_jobs_by_track(jobs: list[tuple[Path, str]], track: str) -> list[tuple[Path, str]]:
    target = f"{track}_input_params.json"
    return [(jp, key) for jp, key in jobs if jp.name == target]


def _asset_base_url() -> str:
    return os.environ.get("SIDEQUEST_ASSET_BASE_URL", "https://cdn.slabgorb.com").rstrip("/")


def is_in_r2(r2_key: str) -> bool:
    url = f"{_asset_base_url()}/{r2_key.lstrip('/')}"
    resp = requests.head(url, timeout=5)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False


async def send_render(json_path: Path) -> dict:
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
    req = {
        "id": f"music-{json_path.stem}-{int(time.time())}",
        "method": "render",
        "params": {"tier": "music", "json_params_path": str(json_path)},
    }
    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()
    response_line = await asyncio.wait_for(reader.readline(), timeout=900)
    writer.close()
    await writer.wait_closed()
    return json.loads(response_line.decode())


async def check_daemon() -> bool:
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
        req = {"id": "healthcheck", "method": "ping"}
        writer.write((json.dumps(req) + "\n").encode())
        await writer.drain()
        resp = await asyncio.wait_for(reader.readline(), timeout=5)
        writer.close()
        await writer.wait_closed()
        return json.loads(resp.decode()).get("result", {}).get("status") == "ok"
    except Exception:
        return False


async def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ACE-Step music tracks for a genre pack")
    parser.add_argument("--genre", required=True, help="Genre pack slug")
    parser.add_argument("--track", help="Only generate this track (file stem, e.g. 'combat')")
    parser.add_argument("--force", action="store_true", help="Re-render even if R2 already has the object")
    parser.add_argument("--dry-run", action="store_true", help="List jobs without sending to daemon")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    pack_dir = GENRE_PACKS_DIR / args.genre
    if not pack_dir.is_dir():
        log.error("Pack directory not found: %s", pack_dir)
        return 1

    jobs = discover_jobs(pack_dir)
    if args.track:
        jobs = filter_jobs_by_track(jobs, args.track)
        if not jobs:
            log.error("No JSON params file matched --track %r in %s", args.track, pack_dir)
            return 1

    if args.dry_run:
        for jp, key in jobs:
            print(f"  {jp.name}  →  {key}")
        print(f"\n{len(jobs)} job(s) discovered.")
        return 0

    if not await check_daemon():
        log.error("Daemon not running at %s — start with: just daemon", SOCKET_PATH)
        return 1

    generated = 0
    skipped = 0
    failed = 0
    t_start = time.monotonic()

    for jp, r2_key in jobs:
        if not args.force and is_in_r2(r2_key):
            log.info("SKIP %s (in R2)", r2_key)
            skipped += 1
            continue
        log.info("GEN  %s", r2_key)
        try:
            result = await send_render(jp)
            if "error" in result:
                log.error("  FAILED: %s", result["error"])
                failed += 1
                continue
            elapsed = result["result"].get("elapsed_ms", 0)
            log.info("  OK (%.1fs)", elapsed / 1000)
            generated += 1
        except Exception as exc:
            log.error("  FAILED: %s: %s", type(exc).__name__, exc)
            failed += 1

    total = time.monotonic() - t_start
    print(f"\n{'=' * 60}")
    print(f"generated: {generated}  skipped: {skipped}  failed: {failed}")
    print(f"total: {total:.1f}s")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 3: Run all script tests**

Run: `cd /Users/slabgorb/Projects/oq-2 && python -m pytest tests/scripts/ -v`
(or whatever environment runs orchestrator-level pytest)
Expected: PASS for all script tests.

- [ ] **Step 4: Smoke-test --dry-run against the actual content repo**

Run: `python scripts/generate_music.py --genre caverns_and_claudes --dry-run`
Expected: prints a list of `*.ogg` keys derived from existing `*_input_params.json` files. No daemon call. No errors.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_music.py tests/scripts/test_generate_music.py
git commit -m "refactor(scripts): generate_music.py — JSON params canonical, dict deleted"
```

---

## Task 19: Update sq-music command + music-director agent

Documentation update so the skill / agent know the new authoring workflow.

**Files:**
- Modify: `.claude/commands/sq-music.md`
- Modify: `.claude/agents/music-director.md`

- [ ] **Step 1: Read both files**

Run: `cat .claude/commands/sq-music.md .claude/agents/music-director.md`

- [ ] **Step 2: Rewrite the workflow sections**

Replace any references to editing `GENRE_MOODS` in `scripts/generate_music.py` with the new flow:

> **Authoring a new track**
>
> 1. Edit `sidequest-content/genre_packs/<pack>/audio.yaml` — add the entry under `mood_tracks.<mood>` with `path: audio/music/<track>.ogg`, `title:`, and `bpm:`.
> 2. Create `sidequest-content/genre_packs/<pack>/audio/music/<track>_input_params.json` — full ACE-Step config with at minimum: `task: "text2music"`, `prompt:`, `lyrics: "[inst]"` for instrumentals, `audio_duration:`, `actual_seeds: [<int>]` (pinned for reproducibility).
> 3. Run `python scripts/generate_music.py --genre <pack>` — the script discovers the JSON, sends it to the daemon, daemon uploads OGG to R2.
> 4. Iterate with `--track <stem>` for one-job runs, `--force` to overwrite an existing R2 object after editing the prompt.
>
> The daemon owns ACE-Step; you never edit Python.

Apply the equivalent text to both files (commands/ has user-facing docs; agents/ has the agent's instructions).

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/sq-music.md .claude/agents/music-director.md
git commit -m "docs(skills): sq-music + music-director workflow uses JSON params"
```

---

## Task 20: Update CLAUDE.md trio + ADR-046

Three CLAUDE.md files reference the old "music is pre-rendered at build time" doctrine; ADR-046 should mention ACE-Step as a coordinator client.

**Files:**
- Modify: `CLAUDE.md` (orchestrator)
- Modify: `sidequest-daemon/CLAUDE.md`
- Modify: `sidequest-content/CLAUDE.md`
- Modify: `docs/adr/046-gpu-memory-budget-coordinator.md`

- [ ] **Step 1: Update orchestrator `CLAUDE.md`**

Find any line that says "music is pre-rendered at build time" or "no runtime music inference lives here." Replace with:

> Music tracks are generated by the daemon's music pipeline on operator command (see ADR-0NN — Daemon Music Tier via ACE-Step). Per-track JSON params files in `sidequest-content/genre_packs/<pack>/audio/music/` are the canonical generation spec. Run `python scripts/generate_music.py --genre <pack>` to regenerate missing audio.

- [ ] **Step 2: Same edit in `sidequest-daemon/CLAUDE.md`**

Find the equivalent line in the daemon's CLAUDE.md and apply the same replacement.

- [ ] **Step 3: Update `sidequest-content/CLAUDE.md`**

Find the "Syncing Between Machines" section that talks about Git LFS. Add a note above it:

> **Audio assets are NOT in this repo.** They live in R2 (`cdn.slabgorb.com`). Per-track ACE-Step generation parameters (`*_input_params.json`) ARE in this repo and are the canonical regeneration spec — see ADR-0NN. Image assets that remain LFS-tracked are unaffected by this change; the LFS sync notes below apply only to images.

- [ ] **Step 4: Update ADR-046**

Append a paragraph to `docs/adr/046-gpu-memory-budget-coordinator.md`:

> **ACE-Step (music) client (added 2026-05).** Music generation joins Flux/Z-Image as a GPU-using daemon tier. For v1, music acquires `render_lock` (the existing image lock) — model swap between image and ACE-Step happens lazily on first request of the alternate type. A dedicated `music_lock` is intentionally not introduced; the simpler shared-lock design avoids deadlock complexity at the cost of cold-swap latency on workload alternation. See ADR-0NN (Daemon Music Tier via ACE-Step) for the music pipeline design.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md sidequest-daemon/CLAUDE.md sidequest-content/CLAUDE.md docs/adr/046-gpu-memory-budget-coordinator.md
git commit -m "docs: CLAUDE.md trio + ADR-046 reflect daemon music pipeline"
```

---

## Task 21: New ADR — Daemon music tier via ACE-Step

Write the ADR that formalizes this architectural shift.

**Files:**
- Create: `docs/adr/0NN-daemon-music-tier-via-ace-step.md` (assign next free number)
- Modify: `docs/adr/README.md` (register the new ADR)

- [ ] **Step 1: Find the next free ADR number**

Run: `ls docs/adr/ | grep -E "^[0-9]{3}-" | sed 's/-.*//' | sort -n | tail -5`
Pick the next integer above the highest result.

- [ ] **Step 2: Write the ADR**

Create `docs/adr/0NN-daemon-music-tier-via-ace-step.md` (replace `NN` with the chosen number):

```markdown
---
status: accepted
date: 2026-05-10
load_bearing: false
supersedes: []
---

# ADR-0NN: Daemon Music Tier via ACE-Step

## Status

Accepted — 2026-05-10

## Context

The original architecture (per CLAUDE.md and ADR-045) treated music as
"pre-rendered at build time" — files baked into the content repo, played
back from disk by either client (today) or daemon (the orphaned
`sidequest_daemon/audio/` mixer module that never had production callers).

Two events changed this:

1. **Sprint 45-49 (LFS strip)** removed binary audio from the content repo.
   What remains are per-track ACE-Step parameter JSON files.
2. **R2 migration** moved durable assets to Cloudflare R2 (`cdn.slabgorb.com`).
   The image render path already uploads daemon outputs to R2 and returns
   `r2_key`; music has no equivalent path.

The "daemon doesn't run music inference" doctrine was correct when ACE-Step
lived in a separate project and the daemon was image-only. Both conditions
have changed: ACE-Step is pip-installable (`acestep`), the daemon already
owns GPU lifecycle (ADR-046), and the R2 upload pattern is established.

## Decision

ACE-Step joins Flux/Z-Image as a daemon media tier. Routing keys off the
existing `tier` field in the dispatch protocol (`tier="music"`).

- **Source of truth:** `sidequest-content/genre_packs/<pack>/audio/music/<track>_input_params.json`
- **Trigger:** explicit operator command via `scripts/generate_music.py`
  (which the `sq-music` skill / music-director agent wrap). No idle
  detection, no scheduled cron, no GM-panel button.
- **Output:** R2 at `genre_packs/<pack>/audio/music/<track>.ogg` (libvorbis q4 OGG).
- **GPU coordination:** music acquires the existing `render_lock` (no
  separate music lock for v1).
- **Manifest:** `audio.yaml` remains the runtime catalog (titles, BPM, mood
  mappings) and is human-authored. The daemon never writes to it. R2 key
  derivation is deterministic from JSON file location, so manifest and R2
  layout align by convention.

## Consequences

**Positive:**
- LFS-stripped audio can be regenerated by re-running existing JSON params
- New tracks added by dropping a JSON file + audio.yaml entry — no Python edits
- R2 upload reuses the established image path
- Orphaned `sidequest_daemon/audio/` module (~1500 LOC) deleted

**Negative:**
- Daemon now juggles two model families; cold-swap latency (~10-15s) on
  workload alternation
- ACE-Step is a non-trivial dependency; daemon process needs more VRAM headroom
- v1 explicit-only trigger means operator must remember to run the script
  (mitigated by `sq-music` skill flow)

**Neutral / future:**
- A dedicated `music_lock` and an idle-detected trigger could come later
  if cold-swap or operator burden becomes painful

## Alternatives considered

- **Keep music separate (status quo):** rejected — leaves operator with a
  manual ACE-Step UI workflow, doesn't solve LFS-strip restoration, leaves
  orphaned audio module in place
- **`MediaPipeline` abstraction (image and music as parallel implementations):**
  rejected — premature decomposition; abstraction earns its keep at three+
  generative tiers, we have two
- **Separate music daemon process:** rejected — duplicates R2 plumbing and
  GPU coordination; ADR-046 specifically exists so we don't need this

## References

- Spec: `docs/superpowers/specs/2026-05-09-daemon-between-session-music-generation-design.md`
- Plan: `docs/superpowers/plans/2026-05-10-daemon-between-session-music-generation.md`
- ADR-035 — Unix Socket IPC for Python Sidecar
- ADR-046 — GPU Memory Budget Coordinator (this ADR adds ACE-Step as a client)
- ADR-082 — Port `sidequest-api` from Rust back to Python
- ADR-045 — Client Audio Engine (historical context)
```

- [ ] **Step 3: Register in ADR README**

Open `docs/adr/README.md` and add the new ADR to the appropriate category (Media or Project Lifecycle). Then run any auto-index script if one exists:

Run: `ls scripts/*adr* 2>/dev/null` — if `regenerate_adr_indexes.py` exists, run it: `python scripts/regenerate_adr_indexes.py`

- [ ] **Step 4: Commit**

```bash
git add docs/adr/0NN-daemon-music-tier-via-ace-step.md docs/adr/README.md CLAUDE.md
git commit -m "docs(adr): ADR-0NN — daemon music tier via ACE-Step"
```

---

## Task 22: Manual smoke — regenerate audio for one pack, verify in-game playback

This is the release checklist, not an automated test. It validates the whole pipeline against real R2.

**No file changes.** Document the steps for the implementer's verification.

- [ ] **Step 1: Boot the daemon**

```bash
just daemon
```

Watch for `MusicPipeline initialized` in the log.

- [ ] **Step 2: Dry-run discover**

```bash
python scripts/generate_music.py --genre caverns_and_claudes --dry-run
```

Expected: prints a list of `genre_packs/caverns_and_claudes/audio/music/<track>.ogg` keys for each `*_input_params.json` file in the pack. Confirm the count matches what's expected.

- [ ] **Step 3: Generate one track for fast feedback**

```bash
python scripts/generate_music.py --genre caverns_and_claudes --track combat
```

Expected: ~60-90s elapsed (cold-load ACE-Step on first request, then ~real-time generation). Watch the daemon log for `music.generation.start` and `music.generation.complete` watcher events. Final line: `generated: 1  skipped: 0  failed: 0`.

- [ ] **Step 4: Verify in R2**

```bash
curl -I https://cdn.slabgorb.com/genre_packs/caverns_and_claudes/audio/music/combat.ogg
```

Expected: `HTTP/1.1 200 OK` with `Content-Type: audio/ogg`.

- [ ] **Step 5: Verify in-game playback**

Start the server + UI (`just up`), join a session in `caverns_and_claudes`, take an action that triggers `combat` mood (attack an NPC). Listen for the music. Watch the GM panel for `AUDIO_CUE` events.

If audio plays: pipeline end-to-end works.

If audio does NOT play: check (in this order):
1. Browser console for `Audio fetch failed` — if present, R2 URL or CORS issue
2. Server log for `audio.skipped reason=empty_cues` — if present, `LibraryBackend.resolve()` not finding the path; check audio.yaml `path:` exactly matches the R2 key minus `genre_packs/<pack>/`
3. Daemon log for music generation — if missing, daemon isn't seeing the request

- [ ] **Step 6: Generate the rest of the pack**

```bash
python scripts/generate_music.py --genre caverns_and_claudes
```

Expected: skips `combat` (already in R2), generates the rest. Total time scales with track count; ~60s per track.

- [ ] **Step 7: Repeat for the other four packs with JSON params**

```bash
python scripts/generate_music.py --genre elemental_harmony
python scripts/generate_music.py --genre mutant_wasteland
python scripts/generate_music.py --genre space_opera
python scripts/generate_music.py --genre victoria
```

This restores the LFS-stripped audio for all five packs. Expected total wall-clock: depends on number of tracks per pack.

---

## Self-Review

Done in-line. Spec coverage check passed: every section in §3-§10 of the spec maps to at least one task. Placeholder scan: ADR number is `0NN` with explicit "assigned at write-time" guidance (Task 21 step 1) — not a hidden TBD. Type consistency: `MusicResult`, `InferenceResult`, `MusicPipeline.derive_r2_key`, `discover_jobs`, `is_in_r2`, `filter_jobs_by_track`, `upload_pack_asset` are used consistently across the tasks where they appear.

One scope decision documented inline (Task 0 prerequisite): the daemon→server watcher bridge fix is bundled into this plan because it's load-bearing for the OTEL section's promises. If a sibling story has already shipped the bridge, Task 0 is a no-op and the implementer skips it.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-10-daemon-between-session-music-generation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
