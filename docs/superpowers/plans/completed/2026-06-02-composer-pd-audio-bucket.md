# Composer ↔ audio.yaml Shared PD Music Bucket — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a world's `audio.yaml` reference public-domain music from a single shared bucket (`genre_packs/assets/audio/classical_pd/`) that `sidequest-composer` renders into and the existing R2 sync uploads — turning the deferred-asset manifest into real, rights-free audio.

**Architecture:** Three thin layers, no new audio infrastructure. (1) A backward-compatible **server resolution rule**: an `audio.yaml` track `path` starting `assets/` resolves to `genre_packs/assets/…` instead of `genre_packs/<slug>/…`. (2) A tracked **`catalog.yaml`** (a composer manifest) in the shared bucket, carrying the `source_url`/composer/work that `MoodTrack` can't hold. (3) A cross-repo **reconciler** that joins demand (audio.yaml) ∩ supply (catalog) ∖ already-rendered (r2_manifest.json), invokes the **unchanged** composer, then the **existing** `r2_sync_packs` + `r2_manifest_from_bucket`. The composer is reused as a subprocess, never modified.

**Tech Stack:** Python 3.12 (server: FastAPI/pydantic v2; scripts: stdlib + `requests`), `uv`, pytest, ruff. `sidequest-composer` CLI (`composer render`). Cloudflare R2 via `scripts/r2_sync_packs.py`.

**Spec:** `docs/superpowers/specs/2026-06-02-composer-pd-audio-bucket-design.md`

**Repos & branches** (per `repos.yaml`): `sidequest-server` → `develop` (gitflow); `sidequest-content` → `develop` (gitflow); orchestrator (`scripts/`, `justfile`) → `main` (trunk). Commit each repo's changes on its own base branch.

---

## File Structure

**sidequest-server** (the only engine change):
- Modify `sidequest/server/asset_urls.py` — add optional `scope` param, forward to span.
- Modify `sidequest/telemetry/spans/asset_url.py` — record `asset.scope`.
- Create `sidequest/genre/audio_paths.py` — single helper `resolve_audio_relpath(rel, genre_slug)` encoding the `assets/`-vs-pack rule (DRY seam; both resolvers call it).
- Modify `sidequest/genre/loader.py` (`_resolve_audio_urls._fix`, ~1635-1642) — call the helper.
- Modify `sidequest/server/audio_cue.py` (`_maybe_prefix`, ~) — call the helper.
- Test `tests/genre/test_audio_url_resolution.py`, `tests/server/test_audio_cue.py`.

**sidequest-content**:
- Create `genre_packs/assets/audio/classical_pd/catalog.yaml` — the supply spec.
- Modify `genre_packs/wry_whimsy/audio.yaml`, `genre_packs/tea_and_murder/audio.yaml` — repoint `audio/classical_pd/…` → `assets/audio/classical_pd/…`.

**orchestrator**:
- Create `scripts/render_pd_audio.py` — the reconciler.
- Create `scripts/tests/test_render_pd_audio.py`.
- Modify `justfile` — `render-pd-audio` recipe.

---

## Phase 1 — Server: shared `assets/` audio path convention

This is the load-bearing unblock and the only engine change. Do it first; everything else is content/scripting.

### Task 1: OTEL span carries `asset.scope`

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/asset_url.py`
- Modify: `sidequest-server/sidequest/server/asset_urls.py`
- Test: `sidequest-server/tests/server/test_asset_urls.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/server/test_asset_urls.py` (create if absent):

```python
from sidequest.server.asset_urls import resolve_asset_url


def test_resolve_asset_url_defaults_scope_pack(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    url = resolve_asset_url("genre_packs/cav/audio/music/combat.ogg")
    assert url == "https://cdn.slabgorb.com/genre_packs/cav/audio/music/combat.ogg"


def test_resolve_asset_url_accepts_shared_scope(monkeypatch):
    # scope is forensic-only; it must not change the URL, only the span.
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    url = resolve_asset_url(
        "genre_packs/assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg",
        scope="shared",
    )
    assert url == (
        "https://cdn.slabgorb.com/genre_packs/assets/audio/classical_pd/"
        "Satie - Gymnopedie No.1.ogg"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_asset_urls.py -v`
Expected: FAIL — `resolve_asset_url() got an unexpected keyword argument 'scope'`.

- [ ] **Step 3: Add `scope` to the span**

In `sidequest/telemetry/spans/asset_url.py`, add `scope` to the attrs dict inside `asset_url_resolved_span`:

```python
@contextmanager
def asset_url_resolved_span(
    *,
    relative_path: str,
    base_url: str,
    mode: str,
    scope: str = "pack",
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_ASSET_URL_RESOLVED,
        {
            "asset.relative_path": relative_path,
            "asset.base_url": base_url,
            "asset.mode": mode,
            "asset.scope": scope,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span
```

- [ ] **Step 4: Thread `scope` through `resolve_asset_url`**

In `sidequest/server/asset_urls.py`, change the signature and the span call:

```python
def resolve_asset_url(relative_path: str, *, scope: str = "pack") -> str:
    """Convert a content-relative path to the URL the UI should fetch.

    ``scope`` is forensic-only (``pack`` | ``shared``): it records on the OTEL
    span whether the path resolved to a pack-local asset or the shared
    ``genre_packs/assets/`` bucket. It never changes the URL.
    """
    rel = relative_path.lstrip("/")
    base = os.environ.get("SIDEQUEST_ASSET_BASE_URL", _DEFAULT_BASE)
    if base in ("", "local"):
        url = _local_path_for(rel)
        mode = "local"
    else:
        url = f"{base.rstrip('/')}/{rel}"
        mode = "cdn"

    with asset_url_resolved_span(
        relative_path=rel, base_url=base or "", mode=mode, scope=scope
    ):
        pass
    return url
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_asset_urls.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/spans/asset_url.py sidequest/server/asset_urls.py tests/server/test_asset_urls.py
git commit -m "feat(audio): asset_url span records pack|shared scope"
```

---

### Task 2: shared-audio-path helper (the single rule)

**Files:**
- Create: `sidequest-server/sidequest/genre/audio_paths.py`
- Test: `sidequest-server/tests/genre/test_audio_paths.py`

- [ ] **Step 1: Write the failing test**

Create `tests/genre/test_audio_paths.py`:

```python
import pytest

from sidequest.genre.audio_paths import resolve_audio_relpath


def test_pack_relative_path_gets_slug(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    url = resolve_audio_relpath("audio/music/combat.ogg", genre_slug="cav")
    assert url == "https://cdn.slabgorb.com/genre_packs/cav/audio/music/combat.ogg"


def test_assets_prefix_resolves_to_shared_bucket_no_slug(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    url = resolve_audio_relpath(
        "assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg", genre_slug="cav"
    )
    assert url == (
        "https://cdn.slabgorb.com/genre_packs/assets/audio/classical_pd/"
        "Satie - Gymnopedie No.1.ogg"
    )


def test_already_absolute_passes_through(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    assert resolve_audio_relpath("https://x/y.ogg", genre_slug="cav") == "https://x/y.ogg"
    assert resolve_audio_relpath("/renders/x.ogg", genre_slug="cav") == "/renders/x.ogg"


def test_empty_passes_through(monkeypatch):
    assert resolve_audio_relpath("", genre_slug="cav") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_audio_paths.py -v`
Expected: FAIL — `ModuleNotFoundError: sidequest.genre.audio_paths`.

- [ ] **Step 3: Write the helper**

Create `sidequest/genre/audio_paths.py`:

```python
"""Single rule for turning an audio.yaml relative path into a served URL.

A track ``path`` whose first segment is ``assets/`` lives in the shared
``genre_packs/assets/`` bucket (the "bucket o' music", mirroring
``genre_packs/assets/fonts/``) and resolves WITHOUT a pack slug. Any other
relative path is pack-local and resolves under ``genre_packs/<slug>/``.

This is the one place the convention is defined; the genre loader's eager
resolution and the turn-time audio_cue prefixer both call it, so the rule
cannot drift between them (per the 2026-05-10 playtest that found audio was
the one media path bypassing the asset_urls seam).
"""

from __future__ import annotations

from sidequest.server.asset_urls import resolve_asset_url

SHARED_PREFIX = "assets/"


def resolve_audio_relpath(rel: str, *, genre_slug: str) -> str:
    """Resolve an audio.yaml relative path to a full asset URL.

    Absolute URLs and server-absolute paths pass through untouched.
    """
    if not rel:
        return rel
    if rel.startswith(("http://", "https://", "/")):
        return rel
    if rel.startswith(SHARED_PREFIX):
        return resolve_asset_url(f"genre_packs/{rel}", scope="shared")
    return resolve_asset_url(f"genre_packs/{genre_slug}/{rel}", scope="pack")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_audio_paths.py -v`
Expected: PASS (all four).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/genre/audio_paths.py tests/genre/test_audio_paths.py
git commit -m "feat(audio): resolve_audio_relpath — shared assets/ bucket rule"
```

---

### Task 3: loader eager-resolution honors the shared bucket

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py` (`_resolve_audio_urls._fix`, ~1635-1642)
- Test: `sidequest-server/tests/genre/test_audio_url_resolution.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/genre/test_audio_url_resolution.py`:

```python
def test_shared_assets_track_resolves_without_slug(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    from sidequest.genre.loader import _resolve_audio_urls
    from sidequest.genre.models.audio import AudioConfig, MixerConfig, MoodTrack

    cfg = AudioConfig(
        mood_tracks={
            "exploration": [
                MoodTrack(
                    path="assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg",
                    title="Gymnopédie No.1",
                    bpm=60,
                ),
                MoodTrack(path="audio/music/local.ogg", title="Local", bpm=90),
            ]
        },
        mixer=MixerConfig(music_volume=0.4, sfx_volume=0.7, crossfade_default_ms=3000),
    )
    _resolve_audio_urls(cfg, genre_slug="wry_whimsy")
    shared, local = cfg.mood_tracks["exploration"]
    assert shared.path == (
        "https://cdn.slabgorb.com/genre_packs/assets/audio/classical_pd/"
        "Satie - Gymnopedie No.1.ogg"
    )
    assert local.path == "https://cdn.slabgorb.com/genre_packs/wry_whimsy/audio/music/local.ogg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_audio_url_resolution.py::test_shared_assets_track_resolves_without_slug -v`
Expected: FAIL — `shared.path` is `…/genre_packs/wry_whimsy/assets/audio/…` (slug wrongly inserted).

- [ ] **Step 3: Route `_fix` through the helper**

In `sidequest/genre/loader.py`, replace the inner `_fix` of `_resolve_audio_urls`:

```python
    from sidequest.genre.audio_paths import resolve_audio_relpath

    def _fix(rel: str) -> str:
        return resolve_audio_relpath(rel, genre_slug=genre_slug)
```

(Delete the old `from sidequest.server.asset_urls import resolve_asset_url` import inside this function and the old body of `_fix`. Leave the loop bodies calling `_fix` unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/genre/test_audio_url_resolution.py -v`
Expected: PASS (the new test and all pre-existing ones — pack-relative behavior is unchanged).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/genre/loader.py tests/genre/test_audio_url_resolution.py
git commit -m "feat(audio): loader resolves shared assets/ tracks to the shared bucket"
```

---

### Task 4: turn-time `audio_cue` honors the same rule

**Files:**
- Modify: `sidequest-server/sidequest/server/audio_cue.py` (`_maybe_prefix`)
- Test: `sidequest-server/tests/server/test_audio_cue.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/server/test_audio_cue.py` (match the existing fixture style in that file for building `AudioCue`/`LibraryBackend`; if a helper exists, reuse it). Minimal direct check of the prefixer behavior via a music cue:

```python
def test_audio_cue_shared_assets_path_drops_slug():
    """A backend-relative shared path resolves to the shared bucket, no slug."""
    from sidequest.audio.models import AudioCue, AudioLane
    from sidequest.server import audio_cue as ac

    class _Backend:
        base_path = None
        def resolve_relpath(self, cue):  # noqa: D401 - test stub
            return "assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg"

    # _maybe_prefix is a closure; exercise it through build_audio_cue_payload
    # with genre_slug set. Use the project's existing AudioCue construction.
    cue = AudioCue(lane=AudioLane.MUSIC, mood="exploration")
    # NOTE: adapt to the real LibraryBackend test double already used in this
    # file; the assertion is the contract:
    #   resolved music_track URL contains "/genre_packs/assets/audio/classical_pd/"
    #   and NOT "/genre_packs/wry_whimsy/assets/"
```

> Implementation note for the engineer: this test file already has a `LibraryBackend` double and a `build_audio_cue_payload(...)` call pattern — reuse it. The behavioral assertion that must hold: when the resolved backend-relative path starts with `assets/`, the emitted `music_track` URL is `…/genre_packs/assets/audio/classical_pd/<file>` (no `genre_slug` segment). Keep the test concrete using the existing double rather than the stub sketch above.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_audio_cue.py -k shared -v`
Expected: FAIL — slug is inserted before `assets/`.

- [ ] **Step 3: Route `_maybe_prefix` through the helper**

In `sidequest/server/audio_cue.py`, replace the body of the inner `_maybe_prefix` so it defers to the shared rule (keeping the `genre_slug is None` passthrough for CLI/test callers):

```python
    def _maybe_prefix(relative: str) -> str:
        if not relative:
            return relative
        if relative.startswith(("http://", "https://", "/")):
            return relative
        if genre_slug is None:
            return relative
        from sidequest.genre.audio_paths import resolve_audio_relpath

        return resolve_audio_relpath(relative, genre_slug=genre_slug)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_audio_cue.py -v`
Expected: PASS (new shared-path test + all existing audio_cue tests unchanged).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/server/audio_cue.py tests/server/test_audio_cue.py
git commit -m "feat(audio): turn-time audio_cue honors shared assets/ bucket rule"
```

---

### Task 5: Phase-1 gate — lint + full audio test slice

**Files:** none (verification).

- [ ] **Step 1: Lint**

Run: `cd sidequest-server && uv run ruff check sidequest/genre/audio_paths.py sidequest/genre/loader.py sidequest/server/audio_cue.py sidequest/server/asset_urls.py sidequest/telemetry/spans/asset_url.py`
Expected: no errors.

- [ ] **Step 2: Run the audio + genre test slice serially**

Run: `cd sidequest-server && uv run pytest tests/genre/test_audio_url_resolution.py tests/genre/test_audio_paths.py tests/server/test_audio_cue.py tests/server/test_asset_urls.py -v -n0`

> `-n0` (serial) avoids the known OTEL span-count deadlock when the full suite runs in parallel.
Expected: all PASS.

- [ ] **Step 3: Open the PR (server → develop)**

```bash
cd sidequest-server
git push -u origin HEAD
gh pr create --base develop --title "feat(audio): shared assets/ music bucket resolution" \
  --body "Implements the server half of the composer PD-audio bucket. audio.yaml paths under assets/ resolve to genre_packs/assets/ (no pack slug). Spec: docs/superpowers/specs/2026-06-02-composer-pd-audio-bucket-design.md"
```

---

## Phase 2 — Content: shared bucket + catalog

### Task 6: create the shared PD catalog

**Files:**
- Create: `sidequest-content/genre_packs/assets/audio/classical_pd/catalog.yaml`

- [ ] **Step 1: List the full demand set**

Run (from orchestrator root):

```bash
grep -rh 'classical_pd' sidequest-content/genre_packs --include='audio.yaml' \
  | grep 'path:' | sed 's#.*classical_pd/##; s/\.ogg.*//' | sort -u
```

Expected: the ~50 piece filenames (Satie, Chopin, Saint-Saëns, Strauss, …). This is the exact `out_name` set the catalog must cover.

- [ ] **Step 2: Author `catalog.yaml`**

Create `sidequest-content/genre_packs/assets/audio/classical_pd/catalog.yaml`. It is a composer manifest. One entry per demanded filename; `out_name` MUST equal the filename from Step 1 (including spaces/case). Seed with the proven smoke track and follow the same shape for the rest:

```yaml
# Shared public-domain music bucket — supply spec for sidequest-composer.
# out_name == the exact filename a pack audio.yaml references under
# assets/audio/classical_pd/. source_url is a PD score (Mutopia/IMSLP).
# Rendered + uploaded to R2 by scripts/render_pd_audio.py.
loudness: -16
entries:
  - out_name: "Satie - Gymnopedie No.1.ogg"
    title: Gymnopédie No. 1
    composer: Erik Satie
    work: Trois Gymnopedies
    movement: No. 1
    source_url: https://www.mutopiaproject.org/ftp/SatieE/gymnopedie_1/gymnopedie_1.mid
  # … one entry per filename from Step 1. Find each score on
  # mutopiaproject.org (MIDI/MusicXML) or imslp.org; record the direct
  # download URL. Leave a track OUT only if no PD score exists — the
  # reconciler will then fail loud naming it, which is the signal to source it.
```

> Authoring note: completing all ~50 is data entry, not code. Each entry needs a real, fetchable PD `source_url`. Do them in batches; the reconciler validates coverage (Task 9) so you cannot silently miss one.

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/assets/audio/classical_pd/catalog.yaml
git commit -m "feat(audio): shared classical_pd catalog (composer supply spec)"
```

---

### Task 7: repoint pack audio.yaml to the shared bucket

**Files:**
- Modify: `sidequest-content/genre_packs/wry_whimsy/audio.yaml`
- Modify: `sidequest-content/genre_packs/tea_and_murder/audio.yaml`

- [ ] **Step 1: Rewrite the paths**

In both files, change every `mood_tracks` entry path from `audio/classical_pd/<file>.ogg` to `assets/audio/classical_pd/<file>.ogg`. Title/bpm/energy are untouched. Example diff (wry_whimsy):

```yaml
  exploration:
    - path: assets/audio/classical_pd/Grieg - Morning Mood (Peer Gynt).ogg
      title: "Morning Mood"
      bpm: 70
```

Apply with sed per file, then eyeball:

```bash
cd sidequest-content
sed -i '' 's#path: audio/classical_pd/#path: assets/audio/classical_pd/#' \
  genre_packs/wry_whimsy/audio.yaml genre_packs/tea_and_murder/audio.yaml
grep -n 'classical_pd' genre_packs/wry_whimsy/audio.yaml genre_packs/tea_and_murder/audio.yaml
```

Expected: every `classical_pd` path now starts `assets/audio/classical_pd/`.

- [ ] **Step 2: Validate packs still load**

Run: `cd sidequest-server && SIDEQUEST_GENRE_PACKS=$PWD/../sidequest-content/genre_packs uv run python -m sidequest.cli.validate audio $PWD/../sidequest-content/genre_packs/wry_whimsy $PWD/../sidequest-content/genre_packs/tea_and_murder`
Expected: validation passes (mood coverage intact; the validator checks mood→track wiring, not on-disk OGG existence, so deferred R2 assets are fine).

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/wry_whimsy/audio.yaml genre_packs/tea_and_murder/audio.yaml
git commit -m "feat(audio): point classical_pd tracks at the shared assets/ bucket"
```

---

## Phase 3 — Orchestrator: the reconciler

### Task 8: `render_pd_audio.py` — demand ∩ supply ∖ rendered

**Files:**
- Create: `scripts/render_pd_audio.py`
- Test: `scripts/tests/test_render_pd_audio.py`

- [ ] **Step 1: Write the failing tests (pure logic — set math + fail-loud)**

Create `scripts/tests/test_render_pd_audio.py`:

```python
import pytest

from scripts.render_pd_audio import (
    UncataloguedTrackError,
    collect_demand,
    plan_renders,
)

CATALOG = {
    "Satie - Gymnopedie No.1.ogg": {
        "out_name": "Satie - Gymnopedie No.1.ogg",
        "title": "Gymnopédie No. 1",
        "source_url": "https://example/g1.mid",
    },
    "Chopin - Nocturne Op.9 No.2 in E-flat major.ogg": {
        "out_name": "Chopin - Nocturne Op.9 No.2 in E-flat major.ogg",
        "title": "Nocturne",
        "source_url": "https://example/noc.mid",
    },
}


def test_collect_demand_extracts_shared_classical_pd_filenames():
    audio_yaml = {
        "mood_tracks": {
            "exploration": [
                {"path": "assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg",
                 "title": "x", "bpm": 60},
                {"path": "audio/music/local.ogg", "title": "y", "bpm": 90},  # pack-local: ignored
            ]
        }
    }
    assert collect_demand([audio_yaml]) == {"Satie - Gymnopedie No.1.ogg"}


def test_plan_renders_skips_already_in_r2():
    demand = {"Satie - Gymnopedie No.1.ogg", "Chopin - Nocturne Op.9 No.2 in E-flat major.ogg"}
    already = {"genre_packs/assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg"}
    todo = plan_renders(demand, CATALOG, already_keys=already)
    assert [e["out_name"] for e in todo] == ["Chopin - Nocturne Op.9 No.2 in E-flat major.ogg"]


def test_plan_renders_fails_loud_on_uncatalogued_demand():
    demand = {"Mystery - Unknown.ogg"}
    with pytest.raises(UncataloguedTrackError) as exc:
        plan_renders(demand, CATALOG, already_keys=set())
    assert "Mystery - Unknown.ogg" in str(exc.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/slabgorb/Projects/oq-3 && uv run pytest scripts/tests/test_render_pd_audio.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.render_pd_audio`.

- [ ] **Step 3: Implement the reconciler**

Create `scripts/render_pd_audio.py`:

```python
#!/usr/bin/env python3
"""Render the public-domain music a world's audio.yaml demands.

Demand  = every `assets/audio/classical_pd/<file>.ogg` referenced by pack
          audio.yaml files.
Supply  = genre_packs/assets/audio/classical_pd/catalog.yaml (a composer
          manifest: out_name + source_url + composer/work per track).
Already = keys in sidequest-content/r2_manifest.json.

For demand ∩ supply ∖ already: write a temp composer manifest, run
`composer render` into the shared bucket, upload the new OGGs via
r2_sync_packs.sync(files=...), then regenerate the whole r2_manifest.json
from the live bucket (r2_manifest_from_bucket). Fails loud on any demanded
track missing from the catalog (No Silent Fallbacks).

Usage:
    uv run python scripts/render_pd_audio.py                 # all packs
    uv run python scripts/render_pd_audio.py --pack wry_whimsy
    uv run python scripts/render_pd_audio.py --dry-run
    uv run python scripts/render_pd_audio.py --force         # re-render rendered
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

log = logging.getLogger("render_pd_audio")

_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = _ROOT / "sidequest-content"
GENRE_PACKS = CONTENT_ROOT / "genre_packs"
SHARED_REL = "genre_packs/assets/audio/classical_pd"
SHARED_DIR = CONTENT_ROOT / "genre_packs" / "assets" / "audio" / "classical_pd"
CATALOG_PATH = SHARED_DIR / "catalog.yaml"
R2_MANIFEST = CONTENT_ROOT / "r2_manifest.json"
SHARED_AUDIO_PREFIX = "assets/audio/classical_pd/"


class UncataloguedTrackError(RuntimeError):
    """A demanded track has no catalog entry — fail loud, never skip."""


def collect_demand(audio_configs: list[dict]) -> set[str]:
    """Return the set of shared classical_pd filenames referenced by the given
    parsed audio.yaml dicts."""
    demand: set[str] = set()
    for cfg in audio_configs:
        for tracks in (cfg.get("mood_tracks") or {}).values():
            for track in tracks:
                path = track.get("path", "")
                if path.startswith(SHARED_AUDIO_PREFIX):
                    demand.add(path[len(SHARED_AUDIO_PREFIX):])
    return demand


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {e["out_name"]: e for e in data.get("entries", [])}


def plan_renders(
    demand: set[str], catalog: dict[str, dict], *, already_keys: set[str]
) -> list[dict]:
    """demand ∩ supply ∖ already. Raises UncataloguedTrackError if any demanded
    track is absent from the catalog."""
    missing = sorted(d for d in demand if d not in catalog)
    if missing:
        raise UncataloguedTrackError(
            "audio.yaml references tracks with no catalog entry:\n  "
            + "\n  ".join(missing)
            + f"\nAdd them to {CATALOG_PATH.relative_to(_ROOT)} (with a PD source_url)."
        )
    todo = []
    for name in sorted(demand):
        key = f"{SHARED_REL}/{name}"
        if key not in already_keys:
            todo.append(catalog[name])
    return todo


def _audio_configs(pack: str | None) -> list[dict]:
    packs = [GENRE_PACKS / pack] if pack else sorted(GENRE_PACKS.iterdir())
    configs = []
    for pack_dir in packs:
        for audio_yaml in pack_dir.rglob("audio.yaml"):
            configs.append(yaml.safe_load(audio_yaml.read_text(encoding="utf-8")) or {})
    return configs


def _already_keys() -> set[str]:
    if not R2_MANIFEST.is_file():
        raise FileNotFoundError(f"r2_manifest.json not found at {R2_MANIFEST}")
    entries = yaml.safe_load(R2_MANIFEST.read_text(encoding="utf-8")) or []
    return {e["key"] for e in entries}


def _write_temp_manifest(entries: list[dict]) -> Path:
    fd = tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", prefix="pd_render_", delete=False, encoding="utf-8"
    )
    yaml.safe_dump({"loudness": -16, "entries": entries}, fd, allow_unicode=True)
    fd.close()
    return Path(fd.name)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", default=None, help="Limit demand to one pack")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-render already-in-R2 tracks")
    args = ap.parse_args(argv)

    catalog = load_catalog()
    demand = collect_demand(_audio_configs(args.pack))
    already = set() if args.force else _already_keys()
    todo = plan_renders(demand, catalog, already_keys=already)

    log.info(
        "demand=%d catalogued=%d already=%d to-render=%d",
        len(demand), len(catalog), len(demand) - len(todo), len(todo),
    )
    if not todo:
        log.info("Nothing to render — all demanded tracks already in R2.")
        return 0
    if args.dry_run:
        for e in todo:
            log.info("DRY would render: %s", e["out_name"])
        return 0

    # 1. Render via the composer (subprocess; composer stays pure).
    manifest = _write_temp_manifest(todo)
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["uv", "run", "composer", "render", str(manifest), "--out-dir", str(SHARED_DIR)],
        cwd=_ROOT / "sidequest-composer",
        check=True,
    )

    # 2. Upload only the new OGGs (no manifest arg → don't clobber the manifest).
    new_oggs = [SHARED_DIR / e["out_name"] for e in todo]
    sys.path.insert(0, str(_ROOT / "scripts"))
    import r2_sync_packs  # noqa: E402

    counts = r2_sync_packs.sync(content_root=CONTENT_ROOT, files=new_oggs)
    log.info("uploaded=%(uploaded)d skipped=%(skipped)d", counts)

    # 3. Regenerate the whole manifest from the live bucket (authoritative).
    subprocess.run(
        ["uv", "run", "--project", ".", "python", "scripts/r2_manifest_from_bucket.py"],
        cwd=_ROOT,
        check=True,
    )
    log.info("Done. Rendered %d track(s); r2_manifest.json refreshed.", len(todo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the logic tests to verify they pass**

Run: `cd /Users/slabgorb/Projects/oq-3 && uv run pytest scripts/tests/test_render_pd_audio.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Lint**

Run: `cd /Users/slabgorb/Projects/oq-3 && uv run ruff check scripts/render_pd_audio.py scripts/tests/test_render_pd_audio.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3
git add scripts/render_pd_audio.py scripts/tests/test_render_pd_audio.py
git commit -m "feat(audio): render_pd_audio reconciler — audio.yaml→composer→R2"
```

---

### Task 9: `just render-pd-audio` recipe + dry-run smoke

**Files:**
- Modify: `justfile` (after the `composer-*` recipes added earlier)

- [ ] **Step 1: Add the recipe**

In `justfile`, below `compose target *flags`:

```just
# Render the public-domain music a world's audio.yaml demands → shared bucket → R2
render-pd-audio *flags:
    cd {{root}} && uv run python scripts/render_pd_audio.py {{flags}}
```

- [ ] **Step 2: Dry-run smoke (proves wiring end-to-end without rendering)**

Run: `cd /Users/slabgorb/Projects/oq-3 && just render-pd-audio --pack wry_whimsy --dry-run`
Expected: prints a `demand=… catalogued=… already=… to-render=…` line and `DRY would render:` entries — OR fails loud listing any uncatalogued track (which means Task 6's catalog is incomplete; finish it, then re-run).

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3
git add justfile
git commit -m "chore(just): render-pd-audio recipe"
```

---

### Task 10: Backfill (operator-run, after catalog is complete)

**Files:** none (operation).

- [ ] **Step 1: Render + upload all demanded tracks**

Run: `cd /Users/slabgorb/Projects/oq-3 && just render-pd-audio`
Expected: composer renders each missing OGG, uploads to R2, refreshes `r2_manifest.json`. Requires MuseScore 4 (`mscore`) installed (FluidSynth fallback otherwise).

- [ ] **Step 2: Verify via R2 audit**

Run: `cd /Users/slabgorb/Projects/oq-3 && uv run --project . python scripts/r2_audit.py --prefix genre_packs/assets/audio/classical_pd/`
Expected: every catalogued track present on R2.

- [ ] **Step 3: Commit the refreshed manifest**

```bash
cd sidequest-content
git add r2_manifest.json
git commit -m "chore(audio): backfill shared classical_pd bucket in r2_manifest"
```

---

## Self-Review

**Spec coverage:**
- Shared bucket `genre_packs/assets/audio/classical_pd/` → Tasks 6, 8. ✔
- `catalog.yaml` as composer manifest carrying source_url → Task 6. ✔
- `assets/` resolution convention (no slug), centralized seam, OTEL scope → Tasks 1-4. ✔
- `MoodTrack` schema unchanged → confirmed (no model edits in any task). ✔
- Reconciler demand∩supply∖R2, fail-loud, idempotent → Task 8. ✔
- Reuse `r2_sync_packs` + regenerate manifest via bucket scan (no clobber) → Task 8 steps. ✔
- Composer unchanged / subprocess only → Task 8 (no composer files touched). ✔
- `just` entrypoint, operator-run backfill → Tasks 9, 10. ✔
- Phasing (convention → catalog → reconciler → backfill) → matches spec §8. ✔

**Placeholder scan:** Task 4's test is a sketch deliberately deferring to the file's existing `LibraryBackend` double — flagged inline with the exact behavioral contract to assert, not a silent TODO. All other steps carry complete code/commands.

**Type consistency:** `resolve_audio_relpath(rel, *, genre_slug)` used identically in Tasks 2-4. `resolve_asset_url(path, *, scope=...)` consistent Tasks 1-2. Reconciler `collect_demand` / `plan_renders` / `UncataloguedTrackError` / `load_catalog` signatures match between test (Task 8 Step 1) and impl (Step 3). Manifest key form `genre_packs/assets/audio/classical_pd/<out_name>` consistent across `plan_renders` and `_already_keys`.

**Known caveat carried from spec:** run server audio tests with `-n0` (Task 5) to avoid the pre-existing parallel-OTEL deadlock.
```
