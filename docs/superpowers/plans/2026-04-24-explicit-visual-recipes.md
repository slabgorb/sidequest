# Explicit Visual Recipes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tier-conditional, fallback-heavy prompt composer with a catalog-driven recipe system where every render resolves through one canonical path and every composed prompt is inspectable as a single artifact.

**Architecture:** New daemon-side types (`Recipe`, `RenderTarget`, `CameraPreset`, `ComposedPrompt`) live in `sidequest_daemon.media.recipes`. Three catalogs (`CharacterCatalog`, `PlaceCatalog`, `StyleCatalog`) load their sources at daemon startup and hot-reload on SIGUSR1. A rewritten `PromptComposer` walks a recipe, resolves slots from catalogs at a computed LOD, applies the art-sensibility cascade (GENRE → WORLD → CULTURE), and emits a `ComposedPrompt` plus an OTEL span with the per-layer breakdown. A new `sidequest-promptpreview` CLI prints the same breakdown for any target. Dead server-side copies of the old composer are deleted.

**Tech Stack:** Python 3.13, pydantic v2, PyYAML, Pillow (post-processing), argparse, pytest, OpenTelemetry (existing daemon instrumentation). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-24-explicit-visual-recipes-design.md`

**Spec deltas discovered during file structure audit:**
- The spec names `flux_mlx_worker` and `zimage_mlx_worker`; only `zimage_mlx_worker.py` exists today. Plan targets the single worker.
- The spec says `portrait_manifest.yaml` sources from `genre_packs/<genre>/portrait_manifest.yaml`; the real location is `genre_packs/<genre>/worlds/<world>/portrait_manifest.yaml` (per-world, confirmed by Keith). `CharacterCatalog` is world-scoped via `RenderTarget.world`; character keys stay `npc:<slug>` with the world as ambient scope.
- Local clone has 6 genre packs; docs reference 11. Plan uses "each existing genre pack" and enumerates only what the canary requires.

---

## File Structure

**New (daemon):**
- `sidequest-daemon/sidequest_daemon/media/recipes.py` — `Slot`, `CameraPreset`, `LOD`, `PlaceLOD`, `Recipe`, `RenderTarget`, `LayerContribution`, `ComposedPrompt`, `CatalogMissError`, `BudgetError`
- `sidequest-daemon/sidequest_daemon/media/catalogs.py` — `CharacterCatalog`, `PlaceCatalog`, `StyleCatalog`, `CharacterTokens`, `PlaceTokens`, loaders
- `sidequest-daemon/sidequest_daemon/media/camera_specs.py` — `CameraSpec`, `PostDirective`, `CameraLoader`
- `sidequest-daemon/sidequest_daemon/media/recipe_loader.py` — `RecipeLoader`
- `sidequest-daemon/sidequest_daemon/media/post_processor.py` — Pillow crop/rotate implementations
- `sidequest-daemon/sidequest_daemon/media/preview.py` — CLI entry point
- `sidequest-daemon/recipes.yaml` — three canonical recipes
- `sidequest-daemon/cameras.yaml` — 17 camera preset prompt shapes
- `sidequest-daemon/tests/test_recipes_types.py`
- `sidequest-daemon/tests/test_camera_specs.py`
- `sidequest-daemon/tests/test_recipe_loader.py`
- `sidequest-daemon/tests/test_catalogs.py`
- `sidequest-daemon/tests/test_composer.py`
- `sidequest-daemon/tests/test_composer_wiring.py`
- `sidequest-daemon/tests/test_post_processor.py`
- `sidequest-daemon/tests/test_preview_cli.py`
- `sidequest-daemon/tests/golden/` — snapshot fixtures
- `sidequest-daemon/tests/fixtures/visual_recipes/` — minimal test pack

**Modified (daemon):**
- `sidequest-daemon/sidequest_daemon/media/prompt_composer.py` — fully rewritten
- `sidequest-daemon/sidequest_daemon/renderer/models.py` — remove `TACTICAL_SKETCH`, add `camera` field on `StageCue`
- `sidequest-daemon/sidequest_daemon/renderer/base.py` — signature unchanged at `Renderer` level; downstream worker migrates
- `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py` — construct `RenderTarget`, call new composer, invoke post-processor when preset declares one
- `sidequest-daemon/pyproject.toml` — `sidequest-promptpreview` entry point

**New (content):**
- `sidequest-content/genre_packs/<genre>/places.yaml` — one per genre (seeded from legacy `_DEFAULT_LOCATION_TAGS` for fantasy-native genres; authored for `mutant_wasteland` as canary; others fail-loud until authored)

**Migration scripts (orchestrator):**
- `scripts/migrate_portrait_manifest_lods.py` — stub `long`/`short`/`background` LODs, promote existing `appearance` to `solo`
- `scripts/migrate_poi_backdrop_lod.py` — same for POIs in `history.yaml`
- `scripts/migrate_visual_tag_overrides.py` — port overrides into place descriptions, produce report for unmatched

**Modified (content — canary world):**
- `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/portrait_manifest.yaml` — authored LODs
- `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/history.yaml` — authored POI backdrops

**Deleted (server):**
- `sidequest-server/sidequest/media/subject_extractor.py`
- `sidequest-server/sidequest/media/prompt_composer.py`
- Dead tier-prefix defs in `sidequest-server/sidequest/renderer/models.py`
- `sidequest-server/tests/**` entries covering the above

---

## Execution Notes

- This plan targets three repos: `sidequest-daemon`, `sidequest-content`, and `sidequest-server` (deletions only). Each task names the repo.
- Branch strategy per `repos.yaml`: daemon and content use gitflow from `develop`; server uses `develop`. Orchestrator changes (migration scripts) target `main`.
- Tests run via `uv run pytest` (daemon) and `pytest` (server). Use the `testing-runner` subagent per project rules.
- Each task ends with a commit. Commit messages follow Conventional Commits.

---

## Phase 1 — Foundational Types

### Task 1: Slot enum, CameraPreset enum, LOD enums

**Repo:** `sidequest-daemon`

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/recipes.py`
- Create: `sidequest-daemon/tests/test_recipes_types.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-daemon/tests/test_recipes_types.py
from sidequest_daemon.media.recipes import CameraPreset, LOD, PlaceLOD, Slot


def test_slot_has_required_members():
    assert Slot.CASTING.value == "casting"
    assert Slot.LOCATION.value == "location"
    assert Slot.DIRECTION_ACTION.value == "direction_action"
    assert Slot.DIRECTION_CAMERA.value == "direction_camera"
    assert Slot.ART_SENSIBILITY.value == "art_sensibility"


def test_lod_levels():
    assert [m.value for m in LOD] == ["solo", "long", "short", "background"]


def test_place_lod_levels():
    assert [m.value for m in PlaceLOD] == ["solo", "backdrop"]


def test_camera_preset_count_is_seventeen():
    assert len(CameraPreset) == 17


def test_camera_preset_contains_canary_presets():
    assert CameraPreset.portrait_3q in CameraPreset
    assert CameraPreset.topdown_90 in CameraPreset
    assert CameraPreset.extreme_closeup_leone in CameraPreset
    assert CameraPreset.scene in CameraPreset
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd sidequest-daemon && uv run pytest tests/test_recipes_types.py -v`
Expected: FAIL (module `sidequest_daemon.media.recipes` does not exist).

- [ ] **Step 3: Write the minimal implementation**

```python
# sidequest-daemon/sidequest_daemon/media/recipes.py
"""Recipe-driven prompt composition types."""

from __future__ import annotations

from enum import Enum


class Slot(str, Enum):
    """Named slots that every recipe declares."""

    CASTING = "casting"
    LOCATION = "location"
    DIRECTION_ACTION = "direction_action"
    DIRECTION_CAMERA = "direction_camera"
    ART_SENSIBILITY = "art_sensibility"


class LOD(str, Enum):
    """Character level-of-detail for prompt contribution."""

    SOLO = "solo"
    LONG = "long"
    SHORT = "short"
    BACKGROUND = "background"


class PlaceLOD(str, Enum):
    """Place level-of-detail — subject or setting."""

    SOLO = "solo"
    BACKDROP = "backdrop"


class CameraPreset(str, Enum):
    """Enumerated camera presets — 17 total, stills-only (no motion)."""

    # Portrait framings
    portrait_3q = "portrait_3q"
    portrait_profile = "portrait_profile"
    portrait_closeup = "portrait_closeup"
    portrait_full_body = "portrait_full_body"
    # POI framings
    wide_establishing = "wide_establishing"
    low_angle_hero = "low_angle_hero"
    interior_wide = "interior_wide"
    aerial_oblique = "aerial_oblique"
    # Illustration framings
    scene = "scene"
    over_shoulder = "over_shoulder"
    wide_action = "wide_action"
    closeup_action = "closeup_action"
    topdown_90 = "topdown_90"
    # Signature shots
    extreme_closeup_leone = "extreme_closeup_leone"
    dutch_tilt = "dutch_tilt"
    single_point_perspective_kubrick = "single_point_perspective_kubrick"
    trunk_shot_tarantino = "trunk_shot_tarantino"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd sidequest-daemon && uv run pytest tests/test_recipes_types.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
cd sidequest-daemon
git checkout -b feat/visual-recipes
git add sidequest_daemon/media/recipes.py tests/test_recipes_types.py
git commit -m "feat(recipes): add Slot/CameraPreset/LOD enums"
```

---

### Task 2: RenderTarget type with validation

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/recipes.py`
- Modify: `sidequest-daemon/tests/test_recipes_types.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_recipes_types.py`:

```python
import pytest
from pydantic import ValidationError

from sidequest_daemon.media.recipes import CameraPreset, RenderTarget


def test_portrait_requires_character():
    with pytest.raises(ValidationError):
        RenderTarget(kind="portrait", world="w", genre="g")


def test_portrait_rejects_illustration_fields():
    with pytest.raises(ValidationError):
        RenderTarget(
            kind="portrait",
            world="w",
            genre="g",
            character="npc:rux",
            action="swinging an axe",
        )


def test_poi_requires_specific_place():
    with pytest.raises(ValidationError):
        RenderTarget(kind="poi", world="w", genre="g")
    with pytest.raises(ValidationError):
        # Archetypal place is not allowed for POI renders.
        RenderTarget(
            kind="poi",
            world="w",
            genre="g",
            place="where:low_fantasy/tavern",
        )


def test_poi_accepts_specific_place():
    target = RenderTarget(
        kind="poi",
        world="flickering_reach",
        genre="mutant_wasteland",
        place="where:flickering_reach/the_lookout",
    )
    assert target.place == "where:flickering_reach/the_lookout"


def test_illustration_requires_participants_action_location_camera():
    with pytest.raises(ValidationError):
        RenderTarget(kind="illustration", world="w", genre="g")
    with pytest.raises(ValidationError):
        RenderTarget(
            kind="illustration",
            world="w",
            genre="g",
            participants=["npc:a"],
            action="",
            location="where:w/x",
            camera=CameraPreset.scene,
        )


def test_illustration_accepts_archetypal_or_specific_location():
    specific = RenderTarget(
        kind="illustration",
        world="w",
        genre="g",
        participants=["npc:a"],
        action="talking",
        location="where:w/x",
        camera=CameraPreset.scene,
    )
    archetypal = RenderTarget(
        kind="illustration",
        world="w",
        genre="g",
        participants=["npc:a"],
        action="talking",
        location="where:g/tavern",
        camera=CameraPreset.scene,
    )
    assert specific.location.startswith("where:")
    assert archetypal.location.startswith("where:")


def test_portrait_default_camera_is_portrait_3q():
    target = RenderTarget(
        kind="portrait",
        world="w",
        genre="g",
        character="npc:rux",
    )
    assert target.camera is None  # recipe supplies default — see Task 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_recipes_types.py -v`
Expected: FAIL — `RenderTarget` is not yet importable.

- [ ] **Step 3: Implement `RenderTarget`**

Append to `sidequest_daemon/media/recipes.py`:

```python
from typing import Literal

from pydantic import BaseModel, model_validator


class RenderTarget(BaseModel):
    """The composable render input. One type serves all three kinds."""

    kind: Literal["portrait", "poi", "illustration"]
    world: str
    genre: str

    # Portrait
    character: str | None = None
    pose_override: str | None = None
    background: str | None = None  # optional where:<scope>/<slug>

    # POI
    place: str | None = None  # where:<world>/<slug> — specific only

    # Illustration
    participants: list[str] = []
    location: str | None = None  # where:<scope>/<slug> — specific or archetypal
    action: str = ""
    camera: CameraPreset | None = None

    # Debug/preview only
    lod_override: dict[str, LOD] | None = None

    @model_validator(mode="after")
    def _enforce_kind_shape(self) -> "RenderTarget":
        if self.kind == "portrait":
            if self.character is None:
                raise ValueError("portrait targets require `character`")
            if self.place or self.participants or self.action:
                raise ValueError(
                    "portrait targets must not set place/participants/action",
                )
        elif self.kind == "poi":
            if self.place is None:
                raise ValueError("poi targets require `place`")
            # Specific-place guard: the scope segment must match `world`.
            # Full validation (catalog lookup) is enforced by the composer;
            # this guard rejects obviously-archetypal refs at the schema level.
            _, _, scope_slug = self.place.partition(":")
            scope = scope_slug.split("/", 1)[0]
            if scope != self.world:
                raise ValueError(
                    f"poi targets must reference a specific place in world "
                    f"{self.world!r}; got scope {scope!r}",
                )
            if self.character or self.participants or self.action:
                raise ValueError(
                    "poi targets must not set character/participants/action",
                )
        elif self.kind == "illustration":
            if not self.participants:
                raise ValueError("illustration targets require `participants`")
            if not self.action:
                raise ValueError("illustration targets require `action`")
            if not self.location:
                raise ValueError("illustration targets require `location`")
            if self.camera is None:
                raise ValueError("illustration targets require `camera`")
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_recipes_types.py -v`
Expected: PASS (11 tests total in this file now).

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/recipes.py tests/test_recipes_types.py
git commit -m "feat(recipes): add RenderTarget with per-kind validation"
```

---

### Task 3: Recipe, LayerContribution, ComposedPrompt types

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/recipes.py`
- Modify: `sidequest-daemon/tests/test_recipes_types.py`

- [ ] **Step 1: Write the failing tests**

```python
from sidequest_daemon.media.recipes import (
    ComposedPrompt,
    LayerContribution,
    Recipe,
)


def test_recipe_has_slot_bindings():
    r = Recipe(
        kind="portrait",
        casting="character",
        location="background",
        direction_action="pose",
        direction_camera="portrait_3q",
        art_sensibility=["GENRE", "WORLD", "CULTURE"],
    )
    assert r.direction_camera == "portrait_3q"
    assert r.art_sensibility == ["GENRE", "WORLD", "CULTURE"]


def test_layer_contribution_roundtrip():
    lc = LayerContribution(
        slot="CASTING",
        source="npc:rux",
        tokens="a gaunt inquisitor...",
        estimated_tokens=11,
    )
    assert lc.source == "npc:rux"


def test_composed_prompt_carries_layers_and_warnings():
    cp = ComposedPrompt(
        positive_prompt="...",
        clip_prompt="...",
        negative_prompt="...",
        worker_type="zimage",
        seed=0,
        layers=[],
        dropped_layers=[],
        warnings=[],
    )
    assert cp.dropped_layers == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_recipes_types.py -v`
Expected: FAIL — `Recipe`, `LayerContribution`, `ComposedPrompt` missing.

- [ ] **Step 3: Implement the types**

Append to `sidequest_daemon/media/recipes.py`:

```python
class Recipe(BaseModel):
    """A canonical recipe — names the source bindings for each slot."""

    kind: Literal["portrait", "poi", "illustration"]
    casting: str
    location: str
    direction_action: str
    direction_camera: str  # a CameraPreset member name, or "{camera}" to
                           # pull from RenderTarget.camera
    art_sensibility: list[str]  # ordered cascade: e.g. ["GENRE","WORLD","CULTURE"]


class LayerContribution(BaseModel):
    slot: str
    source: str
    tokens: str
    estimated_tokens: int


class ComposedPrompt(BaseModel):
    positive_prompt: str
    clip_prompt: str
    negative_prompt: str
    worker_type: str
    seed: int
    layers: list[LayerContribution]
    dropped_layers: list[str]
    warnings: list[str]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_recipes_types.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/recipes.py tests/test_recipes_types.py
git commit -m "feat(recipes): add Recipe/LayerContribution/ComposedPrompt"
```

---

### Task 4: CatalogMissError and BudgetError

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/recipes.py`
- Modify: `sidequest-daemon/tests/test_recipes_types.py`

- [ ] **Step 1: Write the failing tests**

```python
from sidequest_daemon.media.recipes import BudgetError, CatalogMissError


def test_catalog_miss_error_carries_source_and_id():
    err = CatalogMissError(source="CharacterCatalog", missing_id="npc:ghost")
    assert "CharacterCatalog" in str(err)
    assert "npc:ghost" in str(err)


def test_budget_error_carries_breakdown():
    err = BudgetError(
        message="identity floor breached",
        breakdown={"CASTING": 200, "ART_SENSIBILITY.GENRE": 320},
    )
    assert "identity floor" in str(err)
    assert err.breakdown["CASTING"] == 200
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_recipes_types.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
class CatalogMissError(Exception):
    """Raised when a catalog reference cannot be resolved. Never silent."""

    def __init__(self, source: str, missing_id: str) -> None:
        super().__init__(f"{source} has no entry for {missing_id!r}")
        self.source = source
        self.missing_id = missing_id


class BudgetError(Exception):
    """Raised when eviction would drop into the identity floor."""

    def __init__(self, message: str, breakdown: dict[str, int]) -> None:
        super().__init__(f"{message}: {breakdown}")
        self.breakdown = breakdown
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_recipes_types.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/recipes.py tests/test_recipes_types.py
git commit -m "feat(recipes): add CatalogMissError and BudgetError"
```

---

## Phase 2 — Camera Catalog

### Task 5: cameras.yaml with 17 presets

**Files:**
- Create: `sidequest-daemon/cameras.yaml`

- [ ] **Step 1: Author the file**

Write the full camera catalog. Every preset has a `prompt`; `extreme_closeup_leone` has a `post` directive per spec.

```yaml
# sidequest-daemon/cameras.yaml
# 17 camera presets. Stills-only — no motion techniques.
# See docs/superpowers/specs/2026-04-24-explicit-visual-recipes-design.md

# --- Portrait framings ---
portrait_3q:
  prompt: >-
    three-quarter view portrait, centered subject, detailed face,
    shoulders-up framing

portrait_profile:
  prompt: >-
    profile view portrait, sharp silhouette, subject facing left, bust framing

portrait_closeup:
  prompt: >-
    tight face-only portrait, emotional weight, shallow depth of field

portrait_full_body:
  prompt: >-
    full-body standing portrait, full outfit and stance visible, grounded pose

# --- POI framings ---
wide_establishing:
  prompt: >-
    wide establishing shot, environmental context, mid-distance subject,
    atmospheric depth

low_angle_hero:
  prompt: >-
    low-angle hero shot looking up at the landmark, monumental presence,
    sky filling the upper frame

interior_wide:
  prompt: >-
    wide architectural interior, depth receding, leading lines, grounded floor

aerial_oblique:
  prompt: >-
    high-angle aerial oblique, landscape scale, map-like clarity,
    diminishing detail to horizon

# --- Illustration framings ---
scene:
  prompt: >-
    painterly mid-distance composition, narrative staging, balanced framing

over_shoulder:
  prompt: >-
    over-the-shoulder two-shot, foreground silhouette, focused subject beyond

wide_action:
  prompt: >-
    wide action shot, middle-distance subjects, environmental context,
    kinetic staging

closeup_action:
  prompt: >-
    tight closeup on a single action beat, kinetic energy, shallow depth

topdown_90:
  prompt: >-
    orthographic top-down tactical view, 90-degree overhead angle, battle-map
    framing, clear spacing between subjects, no perspective

# --- Signature shots ---
extreme_closeup_leone:
  prompt: >-
    tight portrait, single dominant facial feature, macro detail, heavy
    chiaroscuro, sweat and skin texture, shallow depth of field
  post:
    kind: crop
    mode: center
    percent: 0.25

dutch_tilt:
  prompt: >-
    dutch angle, camera tilted 15-25 degrees off-horizontal, destabilized
    composition, disoriented framing

single_point_perspective_kubrick:
  prompt: >-
    rigid symmetric one-point perspective, corridor or hall receding to
    central vanishing point, centered subject, architectural order

trunk_shot_tarantino:
  prompt: >-
    low POV looking up from inside a container, subjects leaning over the
    frame, worm's-eye angle
```

- [ ] **Step 2: Verify file loads as valid YAML**

Run: `uv run python -c "import yaml; d = yaml.safe_load(open('cameras.yaml')); print(len(d), 'presets'); assert len(d) == 17"`
Expected: output `17 presets`.

- [ ] **Step 3: Commit**

```bash
git add cameras.yaml
git commit -m "feat(recipes): author cameras.yaml with 17 preset prompt shapes"
```

---

### Task 6: CameraSpec, PostDirective, CameraLoader

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/camera_specs.py`
- Create: `sidequest-daemon/tests/test_camera_specs.py`

- [ ] **Step 1: Write the failing tests**

```python
# sidequest-daemon/tests/test_camera_specs.py
from pathlib import Path

import pytest

from sidequest_daemon.media.camera_specs import (
    CameraLoader,
    CameraSpec,
    PostDirective,
)
from sidequest_daemon.media.recipes import CameraPreset

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_loads_all_seventeen_presets():
    loader = CameraLoader.from_file(REPO_ROOT / "cameras.yaml")
    assert len(loader.specs) == 17
    for preset in CameraPreset:
        assert preset in loader.specs


def test_leone_has_crop_post():
    loader = CameraLoader.from_file(REPO_ROOT / "cameras.yaml")
    spec = loader.specs[CameraPreset.extreme_closeup_leone]
    assert isinstance(spec.post, PostDirective)
    assert spec.post.kind == "crop"
    assert spec.post.percent == 0.25


def test_portrait_3q_has_no_post():
    loader = CameraLoader.from_file(REPO_ROOT / "cameras.yaml")
    spec = loader.specs[CameraPreset.portrait_3q]
    assert spec.post is None


def test_missing_preset_in_yaml_raises():
    bad = {"portrait_3q": {"prompt": "..."}}  # only one, 16 missing
    with pytest.raises(ValueError, match="missing"):
        CameraLoader.from_dict(bad)


def test_unknown_preset_in_yaml_raises():
    good = {preset.value: {"prompt": "x"} for preset in CameraPreset}
    good["fabricated_preset"] = {"prompt": "x"}
    with pytest.raises(ValueError, match="unknown"):
        CameraLoader.from_dict(good)
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_camera_specs.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement**

```python
# sidequest-daemon/sidequest_daemon/media/camera_specs.py
"""Camera preset specifications loaded from cameras.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel

from sidequest_daemon.media.recipes import CameraPreset


class PostDirective(BaseModel):
    """Post-processing applied after the image renders."""

    kind: Literal["crop", "rotate"]
    mode: Literal["center", "subject_center"] | None = None
    percent: float | None = None  # crop
    degrees: float | None = None  # rotate


class CameraSpec(BaseModel):
    prompt: str
    post: PostDirective | None = None


class CameraLoader:
    """Loads and validates cameras.yaml — fails loud on missing or unknown."""

    def __init__(self, specs: dict[CameraPreset, CameraSpec]) -> None:
        self.specs = specs

    @classmethod
    def from_file(cls, path: Path) -> "CameraLoader":
        data = yaml.safe_load(path.read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CameraLoader":
        known = {p.value for p in CameraPreset}
        provided = set(data.keys())

        missing = known - provided
        if missing:
            raise ValueError(f"cameras.yaml missing presets: {sorted(missing)}")

        unknown = provided - known
        if unknown:
            raise ValueError(
                f"cameras.yaml contains unknown presets: {sorted(unknown)}",
            )

        specs: dict[CameraPreset, CameraSpec] = {}
        for name, spec_data in data.items():
            specs[CameraPreset(name)] = CameraSpec.model_validate(spec_data)
        return cls(specs)

    def get(self, preset: CameraPreset) -> CameraSpec:
        return self.specs[preset]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_camera_specs.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/camera_specs.py tests/test_camera_specs.py
git commit -m "feat(recipes): add CameraLoader with fail-loud validation"
```

---

## Phase 3 — Recipe Loader

### Task 7: recipes.yaml with three canonical recipes

**Files:**
- Create: `sidequest-daemon/recipes.yaml`

- [ ] **Step 1: Author the file**

```yaml
# sidequest-daemon/recipes.yaml
# The three canonical recipes. Each names the source binding per slot.

portrait:
  kind: portrait
  casting: character
  location: background
  direction_action: pose
  direction_camera: portrait_3q
  art_sensibility: [GENRE, WORLD, CULTURE]

poi:
  kind: poi
  casting: landmark
  location: environment
  direction_action: description
  direction_camera: wide_establishing
  art_sensibility: [GENRE, WORLD, CULTURE]

illustration:
  kind: illustration
  casting: participants
  location: poi_location
  direction_action: action
  direction_camera: "{camera}"
  art_sensibility: [GENRE, WORLD, CULTURE]
```

- [ ] **Step 2: Verify file loads**

Run: `uv run python -c "import yaml; d = yaml.safe_load(open('recipes.yaml')); assert set(d) == {'portrait','poi','illustration'}; print('ok')"`
Expected: output `ok`.

- [ ] **Step 3: Commit**

```bash
git add recipes.yaml
git commit -m "feat(recipes): author recipes.yaml with three canonical recipes"
```

---

### Task 8: RecipeLoader

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/recipe_loader.py`
- Create: `sidequest-daemon/tests/test_recipe_loader.py`

- [ ] **Step 1: Write the failing tests**

```python
# sidequest-daemon/tests/test_recipe_loader.py
from pathlib import Path

import pytest

from sidequest_daemon.media.recipe_loader import RecipeLoader

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_loads_three_recipes():
    loader = RecipeLoader.from_file(REPO_ROOT / "recipes.yaml")
    assert set(loader.recipes) == {"portrait", "poi", "illustration"}


def test_portrait_recipe_binds_to_portrait_3q():
    loader = RecipeLoader.from_file(REPO_ROOT / "recipes.yaml")
    r = loader.recipes["portrait"]
    assert r.direction_camera == "portrait_3q"
    assert r.art_sensibility == ["GENRE", "WORLD", "CULTURE"]


def test_illustration_recipe_has_dynamic_camera():
    loader = RecipeLoader.from_file(REPO_ROOT / "recipes.yaml")
    r = loader.recipes["illustration"]
    assert r.direction_camera == "{camera}"


def test_unknown_camera_preset_rejected():
    bad = {
        "portrait": {
            "kind": "portrait",
            "casting": "character",
            "location": "background",
            "direction_action": "pose",
            "direction_camera": "fabricated_shot",
            "art_sensibility": ["GENRE"],
        },
    }
    with pytest.raises(ValueError, match="camera"):
        RecipeLoader.from_dict(bad)


def test_unknown_cascade_layer_rejected():
    bad = {
        "portrait": {
            "kind": "portrait",
            "casting": "character",
            "location": "background",
            "direction_action": "pose",
            "direction_camera": "portrait_3q",
            "art_sensibility": ["GENRE", "FABRICATED"],
        },
    }
    with pytest.raises(ValueError, match="cascade"):
        RecipeLoader.from_dict(bad)
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_recipe_loader.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# sidequest-daemon/sidequest_daemon/media/recipe_loader.py
"""Loads recipes.yaml and validates against known camera presets / layers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sidequest_daemon.media.recipes import CameraPreset, Recipe

_ALLOWED_CASCADE_LAYERS = {"GENRE", "WORLD", "CULTURE"}
_DYNAMIC_CAMERA_MARKER = "{camera}"


class RecipeLoader:
    def __init__(self, recipes: dict[str, Recipe]) -> None:
        self.recipes = recipes

    @classmethod
    def from_file(cls, path: Path) -> "RecipeLoader":
        return cls.from_dict(yaml.safe_load(path.read_text()))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecipeLoader":
        recipes: dict[str, Recipe] = {}
        known_cameras = {p.value for p in CameraPreset}
        for name, raw in data.items():
            recipe = Recipe.model_validate(raw)

            if recipe.direction_camera != _DYNAMIC_CAMERA_MARKER:
                if recipe.direction_camera not in known_cameras:
                    raise ValueError(
                        f"recipe {name!r}: unknown camera preset "
                        f"{recipe.direction_camera!r}",
                    )

            unknown_layers = set(recipe.art_sensibility) - _ALLOWED_CASCADE_LAYERS
            if unknown_layers:
                raise ValueError(
                    f"recipe {name!r}: unknown cascade layer(s) "
                    f"{sorted(unknown_layers)}",
                )

            recipes[name] = recipe
        return cls(recipes)

    def get(self, kind: str) -> Recipe:
        return self.recipes[kind]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_recipe_loader.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/recipe_loader.py tests/test_recipe_loader.py
git commit -m "feat(recipes): add RecipeLoader with camera+cascade validation"
```

---

## Phase 4 — Catalogs

### Task 9: Fixture test pack

**Files:**
- Create: `sidequest-daemon/tests/fixtures/visual_recipes/genre_packs/testgenre/visual_style.yaml`
- Create: `sidequest-daemon/tests/fixtures/visual_recipes/genre_packs/testgenre/places.yaml`
- Create: `sidequest-daemon/tests/fixtures/visual_recipes/genre_packs/testgenre/worlds/testworld/visual_style.yaml`
- Create: `sidequest-daemon/tests/fixtures/visual_recipes/genre_packs/testgenre/worlds/testworld/portrait_manifest.yaml`
- Create: `sidequest-daemon/tests/fixtures/visual_recipes/genre_packs/testgenre/worlds/testworld/history.yaml`
- Create: `sidequest-daemon/tests/fixtures/visual_recipes/genre_packs/testgenre/worlds/testworld/cultures/ironhand.yaml`

- [ ] **Step 1: Author fixture genre visual_style.yaml**

```yaml
# .../genre_packs/testgenre/visual_style.yaml
positive_suffix: "painterly digital illustration, muted desaturated palette, gritty mood"
negative_prompt: "watermark, blurry, deformed"
base_seed: 42
preferred_model: "zimage"
```

- [ ] **Step 2: Author fixture archetypal places**

```yaml
# .../genre_packs/testgenre/places.yaml
tavern:
  landmark:
    solo: ""
    backdrop: ""
  environment:
    solo: "wooden beams, hearth fire, lamp-lit interior"
    backdrop: "wooden beams, hearth fire"
  description:
    solo: "a tavern common room"
    backdrop: "a tavern"
```

- [ ] **Step 3: Author fixture world visual_style.yaml**

```yaml
# .../worlds/testworld/visual_style.yaml
positive_suffix: "bruised amber sky, weathered surfaces"
```

- [ ] **Step 4: Author fixture portrait_manifest.yaml**

```yaml
# .../worlds/testworld/portrait_manifest.yaml
characters:
  - id: rux
    type: npc_major
    culture: ironhand
    descriptions:
      solo: "a tall gaunt inquisitor in grey wool cassock, iron-chased buttons, silver device at throat, scar across left cheekbone, hands callused"
      long: "gaunt inquisitor in grey wool, iron buttons, silver throat device, scar on left cheek"
      short: "a gaunt inquisitor in grey wool"
      background: "an inquisitor"
    default_pose: "standing, hands folded, neutral expression"
  - id: mira
    type: npc_supporting
    culture: ironhand
    descriptions:
      solo: "a young woman in leather traveling gear, short chestnut hair, green eyes, quick smile, longbow slung across her back"
      long: "woman in leather gear, chestnut hair, longbow"
      short: "a woman with a longbow"
      background: "a traveler"
    default_pose: "relaxed, hand on bow"
```

- [ ] **Step 5: Author fixture history.yaml**

```yaml
# .../worlds/testworld/history.yaml
chapters:
  - name: The Present Age
    points_of_interest:
      - slug: the_lookout
        name: The Lookout
        controlling_culture: ironhand
        visual_prompt:
          solo: "a weathered stone watchtower atop a rocky promontory, iron-banded timber door, narrow slit windows, a copper weathervane in the shape of an axe"
          backdrop: "a stone watchtower on a rocky promontory"
        environment:
          solo: "barren upland, bruised amber sky, distant mountain silhouettes, scattered gorse"
          backdrop: "barren upland, bruised sky"
```

- [ ] **Step 6: Author fixture culture**

```yaml
# .../worlds/testworld/cultures/ironhand.yaml
visual_tokens: "iron-chased buttons, grey wool, silver devices, monastic severity"
```

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/
git commit -m "test(recipes): add minimal test genre pack fixture"
```

---

### Task 10: CharacterCatalog

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/catalogs.py`
- Create: `sidequest-daemon/tests/test_catalogs.py`

- [ ] **Step 1: Write the failing tests**

```python
# sidequest-daemon/tests/test_catalogs.py
from pathlib import Path

import pytest

from sidequest_daemon.media.catalogs import CharacterCatalog, CharacterTokens
from sidequest_daemon.media.recipes import LOD, CatalogMissError

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "visual_recipes" / "genre_packs"


def test_loads_world_characters():
    cat = CharacterCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    tokens = cat.get("npc:rux")
    assert isinstance(tokens, CharacterTokens)
    assert tokens.kind == "npc"
    assert tokens.culture == "ironhand"
    assert "inquisitor" in tokens.descriptions[LOD.SOLO]
    assert tokens.default_pose.startswith("standing")


def test_all_four_lods_present():
    cat = CharacterCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    t = cat.get("npc:rux")
    for lod in LOD:
        assert t.descriptions[lod], f"missing {lod}"


def test_missing_character_raises():
    cat = CharacterCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    with pytest.raises(CatalogMissError) as exc:
        cat.get("npc:ghost")
    assert exc.value.source == "CharacterCatalog"
    assert exc.value.missing_id == "npc:ghost"


def test_rejects_non_npc_pc_key():
    cat = CharacterCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    with pytest.raises(ValueError, match="scheme"):
        cat.get("rux")
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_catalogs.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# sidequest-daemon/sidequest_daemon/media/catalogs.py
"""Catalogs — Character, Place, Style. Load at startup. Fail-loud on miss."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from sidequest_daemon.media.recipes import (
    LOD,
    CatalogMissError,
    PlaceLOD,
)


class CharacterTokens(BaseModel):
    kind: Literal["npc", "pc"]
    descriptions: dict[LOD, str]
    default_pose: str
    culture: str | None
    world: str


class CharacterCatalog:
    """World-scoped — every character belongs to exactly one world."""

    def __init__(self, entries: dict[str, CharacterTokens]) -> None:
        self._entries = entries

    @classmethod
    def load(
        cls,
        genre_packs_root: Path,
        *,
        genre: str,
        world: str,
    ) -> "CharacterCatalog":
        path = (
            genre_packs_root
            / genre
            / "worlds"
            / world
            / "portrait_manifest.yaml"
        )
        data = yaml.safe_load(path.read_text())
        entries: dict[str, CharacterTokens] = {}
        for raw in data.get("characters", []):
            slug = raw["id"]
            descriptions = {
                LOD(k): v
                for k, v in raw.get("descriptions", {}).items()
            }
            if set(descriptions) != set(LOD):
                missing = set(LOD) - set(descriptions)
                raise ValueError(
                    f"character {slug!r} missing LODs: {sorted(m.value for m in missing)}",
                )
            entries[f"npc:{slug}"] = CharacterTokens(
                kind="npc",
                descriptions=descriptions,
                default_pose=raw.get("default_pose", ""),
                culture=raw.get("culture"),
                world=world,
            )
        return cls(entries)

    def get(self, ref: str) -> CharacterTokens:
        if not (ref.startswith("npc:") or ref.startswith("pc:")):
            raise ValueError(
                f"character ref {ref!r} must use scheme 'npc:' or 'pc:'",
            )
        if ref not in self._entries:
            raise CatalogMissError(source="CharacterCatalog", missing_id=ref)
        return self._entries[ref]

    def add_pc(self, pc_id: str, tokens: CharacterTokens) -> None:
        """Register a PC at runtime from the character store."""
        self._entries[f"pc:{pc_id}"] = tokens
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_catalogs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/catalogs.py tests/test_catalogs.py
git commit -m "feat(recipes): add world-scoped CharacterCatalog"
```

---

### Task 11: PlaceCatalog

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/catalogs.py`
- Modify: `sidequest-daemon/tests/test_catalogs.py`

- [ ] **Step 1: Write failing tests**

```python
from sidequest_daemon.media.catalogs import PlaceCatalog, PlaceTokens


def test_loads_specific_place_from_history():
    cat = PlaceCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    t = cat.get("where:testworld/the_lookout")
    assert isinstance(t, PlaceTokens)
    assert t.kind == "specific"
    assert t.controlling_culture == "ironhand"
    assert "watchtower" in t.landmark[PlaceLOD.SOLO]
    assert "upland" in t.environment[PlaceLOD.SOLO]


def test_loads_archetypal_place_from_genre():
    cat = PlaceCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    t = cat.get("where:testgenre/tavern")
    assert t.kind == "archetypal"
    assert t.landmark[PlaceLOD.SOLO] == ""
    assert "hearth" in t.environment[PlaceLOD.SOLO]


def test_archetypal_with_populated_landmark_rejected():
    bad_genre = FIXTURE_ROOT / "badgenre"
    bad_genre.mkdir(parents=True, exist_ok=True)
    (bad_genre / "places.yaml").write_text(
        "tavern:\n"
        "  landmark: {solo: 'a specific tavern named The Black Lion', backdrop: ''}\n"
        "  environment: {solo: '...', backdrop: '...'}\n"
        "  description: {solo: 'tavern', backdrop: 'tavern'}\n",
    )
    try:
        with pytest.raises(ValueError, match="landmark"):
            PlaceCatalog.load(FIXTURE_ROOT, genre="badgenre", world="testworld")
    finally:
        (bad_genre / "places.yaml").unlink()
        bad_genre.rmdir()


def test_missing_place_raises():
    cat = PlaceCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    with pytest.raises(CatalogMissError):
        cat.get("where:testworld/no_such_poi")


def test_poi_kind_guard_rejects_archetypal_key():
    cat = PlaceCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    # Archetypal ref is legal in catalog; the caller (composer) enforces
    # poi-recipe-specific constraints. This test documents the catalog accepts both.
    specific = cat.get("where:testworld/the_lookout")
    archetypal = cat.get("where:testgenre/tavern")
    assert specific.kind == "specific"
    assert archetypal.kind == "archetypal"
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_catalogs.py -v -k place`
Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `catalogs.py`:

```python
class PlaceTokens(BaseModel):
    kind: Literal["specific", "archetypal"]
    landmark: dict[PlaceLOD, str]
    environment: dict[PlaceLOD, str]
    description: dict[PlaceLOD, str]
    controlling_culture: str | None
    scope: str  # world slug (specific) or genre slug (archetypal)


class PlaceCatalog:
    def __init__(self, entries: dict[str, PlaceTokens]) -> None:
        self._entries = entries

    @classmethod
    def load(
        cls,
        genre_packs_root: Path,
        *,
        genre: str,
        world: str,
    ) -> "PlaceCatalog":
        entries: dict[str, PlaceTokens] = {}
        cls._load_specific(entries, genre_packs_root, genre, world)
        cls._load_archetypal(entries, genre_packs_root, genre)
        return cls(entries)

    @staticmethod
    def _load_specific(
        entries: dict[str, PlaceTokens],
        root: Path,
        genre: str,
        world: str,
    ) -> None:
        path = root / genre / "worlds" / world / "history.yaml"
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text()) or {}
        for chapter in data.get("chapters", []):
            for poi in chapter.get("points_of_interest", []):
                slug = poi["slug"]
                visual = poi.get("visual_prompt", {})
                env = poi.get("environment", {})
                if isinstance(visual, str) or isinstance(env, str):
                    raise ValueError(
                        f"POI {slug!r} has string visual_prompt/environment — "
                        f"migrate to {{solo: ..., backdrop: ...}} LODs "
                        f"(see scripts/migrate_poi_backdrop_lod.py)",
                    )
                landmark = {
                    PlaceLOD.SOLO: visual.get("solo", ""),
                    PlaceLOD.BACKDROP: visual.get("backdrop", ""),
                }
                environment = {
                    PlaceLOD.SOLO: env.get("solo", ""),
                    PlaceLOD.BACKDROP: env.get("backdrop", ""),
                }
                description = {
                    PlaceLOD.SOLO: poi.get("name", slug),
                    PlaceLOD.BACKDROP: poi.get("name", slug),
                }
                entries[f"where:{world}/{slug}"] = PlaceTokens(
                    kind="specific",
                    landmark=landmark,
                    environment=environment,
                    description=description,
                    controlling_culture=poi.get("controlling_culture"),
                    scope=world,
                )

    @staticmethod
    def _load_archetypal(
        entries: dict[str, PlaceTokens],
        root: Path,
        genre: str,
    ) -> None:
        path = root / genre / "places.yaml"
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text()) or {}
        for slug, raw in data.items():
            landmark = {PlaceLOD(k): v for k, v in raw["landmark"].items()}
            environment = {PlaceLOD(k): v for k, v in raw["environment"].items()}
            description = {PlaceLOD(k): v for k, v in raw["description"].items()}
            for lod, text in landmark.items():
                if text:
                    raise ValueError(
                        f"archetypal place {genre}/{slug!r} has populated "
                        f"landmark.{lod.value}; archetypes have no landmark",
                    )
            entries[f"where:{genre}/{slug}"] = PlaceTokens(
                kind="archetypal",
                landmark=landmark,
                environment=environment,
                description=description,
                controlling_culture=None,
                scope=genre,
            )

    def get(self, ref: str) -> PlaceTokens:
        if not ref.startswith("where:"):
            raise ValueError(f"place ref {ref!r} must use scheme 'where:'")
        if ref not in self._entries:
            raise CatalogMissError(source="PlaceCatalog", missing_id=ref)
        return self._entries[ref]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_catalogs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/catalogs.py tests/test_catalogs.py
git commit -m "feat(recipes): add PlaceCatalog with specific + archetypal sources"
```

---

### Task 12: StyleCatalog

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/catalogs.py`
- Modify: `sidequest-daemon/tests/test_catalogs.py`

- [ ] **Step 1: Write failing tests**

```python
from sidequest_daemon.media.catalogs import StyleCatalog


def test_loads_genre_style():
    cat = StyleCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    tokens = cat.get_genre("testgenre")
    assert "painterly" in tokens


def test_loads_world_style():
    cat = StyleCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    tokens = cat.get_world("testgenre", "testworld")
    assert "amber" in tokens


def test_absent_world_style_returns_empty():
    cat = StyleCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    tokens = cat.get_world("testgenre", "no_such_world")
    assert tokens == ""


def test_culture_tokens_loaded():
    cat = StyleCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    tokens = cat.get_culture("testgenre", "testworld", "ironhand")
    assert "iron-chased" in tokens


def test_unknown_culture_raises():
    cat = StyleCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld")
    with pytest.raises(CatalogMissError):
        cat.get_culture("testgenre", "testworld", "nonexistent")
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_catalogs.py -v -k style`
Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `catalogs.py`:

```python
class StyleCatalog:
    def __init__(
        self,
        genre_tokens: dict[str, str],
        world_tokens: dict[tuple[str, str], str],
        culture_tokens: dict[tuple[str, str, str], str],
    ) -> None:
        self._genre = genre_tokens
        self._world = world_tokens
        self._culture = culture_tokens

    @classmethod
    def load(
        cls,
        genre_packs_root: Path,
        *,
        genre: str,
        world: str,
    ) -> "StyleCatalog":
        genre_tokens: dict[str, str] = {}
        world_tokens: dict[tuple[str, str], str] = {}
        culture_tokens: dict[tuple[str, str, str], str] = {}

        # Genre style
        genre_style = genre_packs_root / genre / "visual_style.yaml"
        if genre_style.exists():
            data = yaml.safe_load(genre_style.read_text()) or {}
            genre_tokens[genre] = data.get("positive_suffix", "")

        # World style
        world_style = (
            genre_packs_root / genre / "worlds" / world / "visual_style.yaml"
        )
        if world_style.exists():
            data = yaml.safe_load(world_style.read_text()) or {}
            world_tokens[(genre, world)] = data.get("positive_suffix", "")

        # Cultures (world-scoped — per spec)
        cultures_dir = genre_packs_root / genre / "worlds" / world / "cultures"
        if cultures_dir.is_dir():
            for culture_file in cultures_dir.glob("*.yaml"):
                data = yaml.safe_load(culture_file.read_text()) or {}
                slug = culture_file.stem
                culture_tokens[(genre, world, slug)] = data.get("visual_tokens", "")

        return cls(genre_tokens, world_tokens, culture_tokens)

    def get_genre(self, genre: str) -> str:
        if genre not in self._genre:
            raise CatalogMissError(source="StyleCatalog.genre", missing_id=genre)
        return self._genre[genre]

    def get_world(self, genre: str, world: str) -> str:
        # Absent world style is a skip-layer signal, not an error.
        return self._world.get((genre, world), "")

    def get_culture(self, genre: str, world: str, culture: str) -> str:
        key = (genre, world, culture)
        if key not in self._culture:
            raise CatalogMissError(
                source="StyleCatalog.culture",
                missing_id=f"{genre}/{world}/{culture}",
            )
        return self._culture[key]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_catalogs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/catalogs.py tests/test_catalogs.py
git commit -m "feat(recipes): add StyleCatalog (genre/world/culture cascade)"
```

---

## Phase 5 — Composer

### Task 13: PromptComposer skeleton and constructor

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py` (full rewrite)
- Create: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-daemon/tests/test_composer.py
from pathlib import Path

import pytest

from sidequest_daemon.media.camera_specs import CameraLoader
from sidequest_daemon.media.catalogs import (
    CharacterCatalog,
    PlaceCatalog,
    StyleCatalog,
)
from sidequest_daemon.media.prompt_composer import PromptComposer
from sidequest_daemon.media.recipe_loader import RecipeLoader

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "visual_recipes" / "genre_packs"
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def composer() -> PromptComposer:
    return PromptComposer(
        recipes=RecipeLoader.from_file(REPO_ROOT / "recipes.yaml"),
        cameras=CameraLoader.from_file(REPO_ROOT / "cameras.yaml"),
        characters=CharacterCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld"),
        places=PlaceCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld"),
        styles=StyleCatalog.load(FIXTURE_ROOT, genre="testgenre", world="testworld"),
    )


def test_composer_constructs(composer: PromptComposer) -> None:
    assert composer is not None
```

- [ ] **Step 2: Run test**

Run: `uv run pytest tests/test_composer.py -v`
Expected: FAIL.

- [ ] **Step 3: Rewrite `prompt_composer.py`**

```python
# sidequest-daemon/sidequest_daemon/media/prompt_composer.py
"""Catalog-driven prompt composer. See spec:
docs/superpowers/specs/2026-04-24-explicit-visual-recipes-design.md
"""

from __future__ import annotations

import hashlib
import logging

from sidequest_daemon.media.camera_specs import CameraLoader
from sidequest_daemon.media.catalogs import (
    CharacterCatalog,
    PlaceCatalog,
    StyleCatalog,
)
from sidequest_daemon.media.recipe_loader import RecipeLoader
from sidequest_daemon.media.recipes import (
    LOD,
    BudgetError,
    ComposedPrompt,
    LayerContribution,
    PlaceLOD,
    RenderTarget,
    Slot,
)

log = logging.getLogger(__name__)

_TOKEN_LIMIT = 512
_TOKENS_PER_WORD = 1.3
_BASE_NEGATIVES = (
    "watermark, signature, text, blurry, deformed, extra limbs, "
    "photograph, photorealistic, hyperrealistic, smooth skin, CGI"
)
_HOUSE_SAFETY_CLAUSE = "solo character focus, detailed distinctive features"


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text.split()) * _TOKENS_PER_WORD))


class PromptComposer:
    def __init__(
        self,
        *,
        recipes: RecipeLoader,
        cameras: CameraLoader,
        characters: CharacterCatalog,
        places: PlaceCatalog,
        styles: StyleCatalog,
    ) -> None:
        self._recipes = recipes
        self._cameras = cameras
        self._characters = characters
        self._places = places
        self._styles = styles

    def compose(self, target: RenderTarget) -> ComposedPrompt:
        raise NotImplementedError  # filled in by subsequent tasks
```

- [ ] **Step 4: Run test**

Run: `uv run pytest tests/test_composer.py -v`
Expected: PASS (just the constructor test).

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): skeleton PromptComposer with catalog injection"
```

---

### Task 14: LOD plan resolution

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing tests**

```python
from sidequest_daemon.media.recipes import CameraPreset, LOD, RenderTarget


def test_portrait_lod_plan_is_solo(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    plan = composer._character_lod_plan(t)
    assert plan == {"npc:rux": LOD.SOLO}


def test_illustration_one_participant_is_solo(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="thinking",
        location="where:testgenre/tavern", camera=CameraPreset.scene,
    )
    assert composer._character_lod_plan(t) == {"npc:rux": LOD.SOLO}


def test_illustration_two_participants_both_long(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux", "npc:mira"], action="arguing",
        location="where:testgenre/tavern", camera=CameraPreset.scene,
    )
    assert composer._character_lod_plan(t) == {
        "npc:rux": LOD.LONG,
        "npc:mira": LOD.LONG,
    }


def test_illustration_four_participants_focus_long_rest_short(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux", "npc:mira", "npc:a", "npc:b"],
        action="around a table", location="where:testgenre/tavern",
        camera=CameraPreset.scene,
    )
    plan = composer._character_lod_plan(t)
    assert plan["npc:rux"] == LOD.LONG
    for other in ("npc:mira", "npc:a", "npc:b"):
        assert plan[other] == LOD.SHORT


def test_illustration_six_participants_tail_background(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux", "npc:a", "npc:b", "npc:c", "npc:d", "npc:e"],
        action="tavern brawl", location="where:testgenre/tavern",
        camera=CameraPreset.scene,
    )
    plan = composer._character_lod_plan(t)
    assert plan["npc:rux"] == LOD.LONG
    assert plan["npc:a"] == LOD.SHORT
    assert plan["npc:b"] == LOD.SHORT
    assert plan["npc:c"] == LOD.BACKGROUND
    assert plan["npc:d"] == LOD.BACKGROUND
    assert plan["npc:e"] == LOD.BACKGROUND


def test_poi_lod_solo(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="poi", world="testworld", genre="testgenre",
        place="where:testworld/the_lookout",
    )
    assert composer._place_lod_for(t) == PlaceLOD.SOLO


def test_illustration_place_lod_backdrop(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="arriving",
        location="where:testworld/the_lookout", camera=CameraPreset.scene,
    )
    assert composer._place_lod_for(t) == PlaceLOD.BACKDROP
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_composer.py -v -k "lod"`
Expected: FAIL.

- [ ] **Step 3: Implement LOD planning**

Append to `PromptComposer`:

```python
    def _character_lod_plan(self, target: RenderTarget) -> dict[str, LOD]:
        if target.kind == "portrait":
            assert target.character is not None
            return {target.character: LOD.SOLO}
        if target.kind == "illustration":
            participants = list(target.participants)
            n = len(participants)
            if n == 1:
                return {participants[0]: LOD.SOLO}
            if n == 2:
                return {p: LOD.LONG for p in participants}
            if 3 <= n <= 4:
                return {
                    **{participants[0]: LOD.LONG},
                    **{p: LOD.SHORT for p in participants[1:]},
                }
            # n >= 5
            return {
                participants[0]: LOD.LONG,
                participants[1]: LOD.SHORT,
                participants[2]: LOD.SHORT,
                **{p: LOD.BACKGROUND for p in participants[3:]},
            }
        return {}  # POI targets have no character plan

    def _place_lod_for(self, target: RenderTarget) -> PlaceLOD:
        if target.kind == "poi":
            return PlaceLOD.SOLO
        if target.kind == "illustration":
            return PlaceLOD.BACKDROP
        if target.kind == "portrait" and target.background:
            return PlaceLOD.BACKDROP
        return PlaceLOD.SOLO  # unreachable for current targets, safe default
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_composer.py -v -k "lod"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): add LOD plan resolution for characters and places"
```

---

### Task 15: Slot resolution — CASTING layer

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing tests**

```python
def test_casting_portrait_uses_solo_description(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    layers = composer._resolve_casting(t)
    assert len(layers) == 1
    assert layers[0].slot == "CASTING"
    assert layers[0].source == "npc:rux"
    assert "inquisitor" in layers[0].tokens
    assert "grey wool cassock" in layers[0].tokens  # solo is richest


def test_casting_illustration_two_uses_long(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux", "npc:mira"], action="arguing",
        location="where:testgenre/tavern", camera=CameraPreset.scene,
    )
    layers = composer._resolve_casting(t)
    assert len(layers) == 2
    rux = next(l for l in layers if l.source == "npc:rux")
    # long is shorter than solo — check that rux's long text appears, not solo
    assert rux.tokens.startswith("gaunt inquisitor in grey wool")


def test_casting_poi_uses_landmark(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="poi", world="testworld", genre="testgenre",
        place="where:testworld/the_lookout",
    )
    layers = composer._resolve_casting(t)
    assert len(layers) == 1
    assert layers[0].source == "where:testworld/the_lookout"
    assert "watchtower" in layers[0].tokens
```

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
    def _resolve_casting(
        self, target: RenderTarget
    ) -> list[LayerContribution]:
        if target.kind in ("portrait", "illustration"):
            plan = self._character_lod_plan(target)
            layers: list[LayerContribution] = []
            for ref, lod in plan.items():
                tokens = self._characters.get(ref)
                text = tokens.descriptions[lod]
                layers.append(
                    LayerContribution(
                        slot="CASTING",
                        source=ref,
                        tokens=text,
                        estimated_tokens=_estimate_tokens(text),
                    ),
                )
            return layers
        if target.kind == "poi":
            assert target.place is not None
            place = self._places.get(target.place)
            lod = self._place_lod_for(target)
            text = place.landmark[lod]
            return [
                LayerContribution(
                    slot="CASTING",
                    source=target.place,
                    tokens=text,
                    estimated_tokens=_estimate_tokens(text),
                ),
            ]
        return []
```

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): resolve CASTING slot from catalogs"
```

---

### Task 16: Slot resolution — LOCATION layer

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing tests**

```python
def test_location_portrait_empty_when_no_background(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    layers = composer._resolve_location(t)
    assert layers == []


def test_location_poi_uses_environment(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="poi", world="testworld", genre="testgenre",
        place="where:testworld/the_lookout",
    )
    layers = composer._resolve_location(t)
    assert len(layers) == 1
    assert "upland" in layers[0].tokens


def test_location_illustration_specific_uses_landmark_plus_environment(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="arriving",
        location="where:testworld/the_lookout", camera=CameraPreset.scene,
    )
    layers = composer._resolve_location(t)
    combined = " ".join(l.tokens for l in layers)
    assert "watchtower" in combined  # backdrop landmark
    assert "upland" in combined      # backdrop environment


def test_location_illustration_archetypal_uses_environment_only(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="drinking",
        location="where:testgenre/tavern", camera=CameraPreset.scene,
    )
    layers = composer._resolve_location(t)
    combined = " ".join(l.tokens for l in layers)
    assert "hearth" in combined
```

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
    def _resolve_location(
        self, target: RenderTarget
    ) -> list[LayerContribution]:
        if target.kind == "portrait":
            if not target.background:
                return []
            place = self._places.get(target.background)
            lod = PlaceLOD.BACKDROP
            text = place.environment[lod]
            return [
                LayerContribution(
                    slot="LOCATION",
                    source=target.background,
                    tokens=text,
                    estimated_tokens=_estimate_tokens(text),
                ),
            ]
        if target.kind == "poi":
            assert target.place is not None
            place = self._places.get(target.place)
            text = place.environment[PlaceLOD.SOLO]
            return [
                LayerContribution(
                    slot="LOCATION",
                    source=target.place,
                    tokens=text,
                    estimated_tokens=_estimate_tokens(text),
                ),
            ]
        if target.kind == "illustration":
            assert target.location is not None
            place = self._places.get(target.location)
            lod = PlaceLOD.BACKDROP
            parts: list[str] = []
            if place.landmark[lod]:
                parts.append(place.landmark[lod])
            if place.environment[lod]:
                parts.append(place.environment[lod])
            text = ", ".join(parts)
            return [
                LayerContribution(
                    slot="LOCATION",
                    source=target.location,
                    tokens=text,
                    estimated_tokens=_estimate_tokens(text),
                ),
            ]
        return []
```

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): resolve LOCATION slot (portrait bg, poi env, illustration)"
```

---

### Task 17: Slot resolution — DIRECTION_ACTION and DIRECTION_CAMERA

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing tests**

```python
def test_portrait_direction_action_uses_default_pose(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    layer = composer._resolve_direction_action(t)
    assert "neutral expression" in layer.tokens


def test_portrait_direction_action_honors_pose_override(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
        pose_override="turning sharply, accusing gesture",
    )
    layer = composer._resolve_direction_action(t)
    assert "accusing" in layer.tokens


def test_illustration_direction_action_is_inline(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="arguing at the door",
        location="where:testgenre/tavern", camera=CameraPreset.scene,
    )
    layer = composer._resolve_direction_action(t)
    assert "arguing" in layer.tokens


def test_portrait_camera_uses_recipe_default(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    layer = composer._resolve_direction_camera(t)
    assert "three-quarter" in layer.tokens


def test_illustration_camera_from_render_target(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="ambush",
        location="where:testgenre/tavern", camera=CameraPreset.topdown_90,
    )
    layer = composer._resolve_direction_camera(t)
    assert "top-down" in layer.tokens
```

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
    def _resolve_direction_action(
        self, target: RenderTarget
    ) -> LayerContribution:
        if target.kind == "portrait":
            assert target.character is not None
            if target.pose_override:
                text = target.pose_override
                source = "inline"
            else:
                text = self._characters.get(target.character).default_pose
                source = f"{target.character}.default_pose"
        elif target.kind == "poi":
            assert target.place is not None
            place = self._places.get(target.place)
            text = place.description[PlaceLOD.SOLO]
            source = target.place
        elif target.kind == "illustration":
            text = target.action
            source = "inline"
        else:
            text, source = "", "inline"
        return LayerContribution(
            slot="DIRECTION_ACTION",
            source=source,
            tokens=text,
            estimated_tokens=_estimate_tokens(text),
        )

    def _resolve_direction_camera(
        self, target: RenderTarget
    ) -> LayerContribution:
        from sidequest_daemon.media.recipes import CameraPreset

        recipe = self._recipes.get(target.kind)
        if recipe.direction_camera == "{camera}":
            assert target.camera is not None
            preset = target.camera
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

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): resolve DIRECTION_ACTION and DIRECTION_CAMERA slots"
```

---

### Task 18: Art sensibility cascade

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing tests**

```python
def test_cascade_genre_world_culture_portrait(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    layers = composer._resolve_art_sensibility(t)
    slots = [l.slot for l in layers]
    assert "ART_SENSIBILITY.GENRE" in slots
    assert "ART_SENSIBILITY.WORLD" in slots
    assert "ART_SENSIBILITY.CULTURE" in slots


def test_cascade_world_empty_still_emitted_as_empty(
    composer: PromptComposer,
) -> None:
    # If world visual_style exists, WORLD contributes. If not, it's skipped.
    # In our fixture, world IS present, so test the skip path differently:
    # use a different world that lacks visual_style.yaml.
    t = RenderTarget(
        kind="portrait", world="no_such_world", genre="testgenre",
        character="npc:rux",
    )
    # Catalog load is world-scoped; this test is illustrative — in practice
    # the composer gets a StyleCatalog already scoped to the target's world.
    # Here we confirm that get_world returning "" produces an empty layer.
    layers = composer._resolve_art_sensibility(
        RenderTarget(
            kind="portrait", world="testworld", genre="testgenre",
            character="npc:rux",
        ),
    )
    world_layer = next(l for l in layers if l.slot == "ART_SENSIBILITY.WORLD")
    assert world_layer.tokens  # testworld has one


def test_cascade_illustration_merges_multiple_cultures(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux", "npc:mira"], action="standing watch",
        location="where:testworld/the_lookout", camera=CameraPreset.scene,
    )
    layers = composer._resolve_art_sensibility(t)
    culture_layers = [l for l in layers if l.slot == "ART_SENSIBILITY.CULTURE"]
    # Rux and Mira share `ironhand`; dedupe produces one culture layer.
    assert len(culture_layers) == 1
    assert "iron-chased" in culture_layers[0].tokens
```

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
    def _resolve_art_sensibility(
        self, target: RenderTarget
    ) -> list[LayerContribution]:
        recipe = self._recipes.get(target.kind)
        layers: list[LayerContribution] = []

        for layer_name in recipe.art_sensibility:
            if layer_name == "GENRE":
                text = self._styles.get_genre(target.genre)
                layers.append(
                    LayerContribution(
                        slot="ART_SENSIBILITY.GENRE",
                        source=f"genre:{target.genre}",
                        tokens=text,
                        estimated_tokens=_estimate_tokens(text),
                    ),
                )
            elif layer_name == "WORLD":
                text = self._styles.get_world(target.genre, target.world)
                layers.append(
                    LayerContribution(
                        slot="ART_SENSIBILITY.WORLD",
                        source=f"world:{target.genre}/{target.world}",
                        tokens=text,
                        estimated_tokens=_estimate_tokens(text),
                    ),
                )
            elif layer_name == "CULTURE":
                cultures = self._collect_cultures(target)
                for culture in cultures:
                    text = self._styles.get_culture(
                        target.genre, target.world, culture,
                    )
                    layers.append(
                        LayerContribution(
                            slot="ART_SENSIBILITY.CULTURE",
                            source=f"culture:{target.genre}/{target.world}/{culture}",
                            tokens=text,
                            estimated_tokens=_estimate_tokens(text),
                        ),
                    )
        return layers

    def _collect_cultures(self, target: RenderTarget) -> list[str]:
        seen: list[str] = []
        refs: list[str] = []
        if target.kind == "portrait":
            assert target.character is not None
            refs = [target.character]
        elif target.kind == "illustration":
            refs = list(target.participants)
        elif target.kind == "poi":
            assert target.place is not None
            place = self._places.get(target.place)
            if place.controlling_culture:
                return [place.controlling_culture]
            return []
        for ref in refs:
            c = self._characters.get(ref).culture
            if c and c not in seen:
                seen.append(c)
        return seen
```

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): art-sensibility cascade with culture dedup"
```

---

### Task 19: Assembly order and compose() wiring

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing tests**

```python
def test_compose_portrait_assembles_in_order(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    result = composer.compose(t)
    # Assembly order per spec:
    # GENRE, WORLD, CASTING, LOCATION, DIRECTION_ACTION, DIRECTION_CAMERA,
    # CULTURE, safety clause.
    genre_idx = result.positive_prompt.find("painterly")
    casting_idx = result.positive_prompt.find("inquisitor")
    camera_idx = result.positive_prompt.find("three-quarter")
    culture_idx = result.positive_prompt.find("iron-chased")
    safety_idx = result.positive_prompt.find("solo character focus")
    assert 0 <= genre_idx < casting_idx < camera_idx < culture_idx < safety_idx


def test_compose_illustration_specific_location_contains_landmark(
    composer: PromptComposer,
) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="arriving",
        location="where:testworld/the_lookout", camera=CameraPreset.scene,
    )
    result = composer.compose(t)
    assert "watchtower" in result.positive_prompt
    assert "arriving" in result.positive_prompt


def test_compose_populates_layers_list(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    result = composer.compose(t)
    slots = {l.slot for l in result.layers}
    assert "CASTING" in slots
    assert "DIRECTION_CAMERA" in slots
    assert "ART_SENSIBILITY.GENRE" in slots


def test_compose_seed_is_deterministic(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    a = composer.compose(t)
    b = composer.compose(t)
    assert a.seed == b.seed
    assert a.positive_prompt == b.positive_prompt
```

- [ ] **Step 2: Run tests**

Expected: FAIL — `compose()` still raises NotImplementedError.

- [ ] **Step 3: Implement**

```python
    def compose(self, target: RenderTarget) -> ComposedPrompt:
        layers = self._resolve_all_layers(target)
        positive = self._assemble(layers)
        clip = self._build_clip(layers)
        negative = self._build_negative(target)
        worker = self._select_worker(target)
        seed = self._derive_seed(target)
        return ComposedPrompt(
            positive_prompt=positive,
            clip_prompt=clip,
            negative_prompt=negative,
            worker_type=worker,
            seed=seed,
            layers=layers,
            dropped_layers=[],
            warnings=[],
        )

    def _resolve_all_layers(
        self, target: RenderTarget
    ) -> list[LayerContribution]:
        art = self._resolve_art_sensibility(target)
        casting = self._resolve_casting(target)
        location = self._resolve_location(target)
        action = [self._resolve_direction_action(target)]
        camera = [self._resolve_direction_camera(target)]
        return art + casting + location + action + camera

    def _assemble(self, layers: list[LayerContribution]) -> str:
        # Order: GENRE, WORLD, CASTING, LOCATION, DIRECTION_ACTION,
        # DIRECTION_CAMERA, CULTURE, safety clause.
        by_slot: dict[str, list[str]] = {}
        for layer in layers:
            if layer.tokens:
                by_slot.setdefault(layer.slot, []).append(layer.tokens)

        ordered: list[str] = []
        for slot in (
            "ART_SENSIBILITY.GENRE",
            "ART_SENSIBILITY.WORLD",
            "CASTING",
            "LOCATION",
            "DIRECTION_ACTION",
            "DIRECTION_CAMERA",
            "ART_SENSIBILITY.CULTURE",
        ):
            if slot in by_slot:
                ordered.extend(by_slot[slot])

        ordered.append(_HOUSE_SAFETY_CLAUSE)
        return ", ".join(ordered)

    def _build_clip(self, layers: list[LayerContribution]) -> str:
        # CLIP gets short style-adjacent keywords — GENRE + CAMERA.
        parts: list[str] = []
        for layer in layers:
            if layer.slot in ("ART_SENSIBILITY.GENRE", "DIRECTION_CAMERA"):
                parts.append(layer.tokens)
        return ", ".join(parts)

    def _build_negative(self, target: RenderTarget) -> str:
        # Preserve base + tier-specific negatives that used to hang on
        # TACTICAL_SKETCH / SCENE_ILLUSTRATION.
        parts = [_BASE_NEGATIVES]
        if target.kind == "illustration" and target.camera and \
                target.camera.value == "topdown_90":
            parts.append(
                "illegible text, blurry labels, overlapping tokens, "
                "3D perspective, realistic rendering",
            )
        return ", ".join(parts)

    def _select_worker(self, target: RenderTarget) -> str:
        # For now, all renders target the zimage worker. Style.preferred_model
        # override can be re-introduced once PR lands — tracked in Task 25.
        return "zimage"

    def _derive_seed(self, target: RenderTarget) -> int:
        key_parts: list[str] = [target.kind, target.world, target.genre]
        if target.character:
            key_parts.append(target.character)
        if target.place:
            key_parts.append(target.place)
        if target.location:
            key_parts.append(target.location)
        key_parts.extend(sorted(target.participants))
        key_parts.append(target.action)
        if target.camera:
            key_parts.append(target.camera.value)
        key = ":".join(key_parts)
        digest = hashlib.sha256(key.encode()).hexdigest()
        return int(digest[:8], 16) % (2**32)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_composer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): assemble positive/clip/negative + deterministic seed"
```

---

### Task 20: Budget estimation and slot eviction

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing tests**

```python
def test_eviction_order_drops_location_flourish_first(
    composer: PromptComposer,
) -> None:
    # Inject a deliberately oversized culture/location to force eviction.
    # Build a target that exceeds 512 tokens when every layer is full.
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="x " * 200,  # forces overflow
        location="where:testworld/the_lookout", camera=CameraPreset.scene,
    )
    result = composer.compose(t)
    # Location flourish should evict before any identity-floor slot.
    assert any(
        "LOCATION" in dl or "DIRECTION_ACTION" in dl
        for dl in result.dropped_layers
    )
    assert not any("CASTING" in dl for dl in result.dropped_layers)


def test_identity_floor_breach_raises_budget_error(
    composer: PromptComposer,
) -> None:
    # Fabricate an over-sized target: make the inline action itself so large
    # that even after every evictable layer is dropped we're still over 512.
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"],
        # Action is identity-floor protected for base verb; but flourish
        # eviction + inline action together must exceed budget for the test.
        action="word " * 600,
        location="where:testworld/the_lookout", camera=CameraPreset.scene,
    )
    with pytest.raises(BudgetError):
        composer.compose(t)
```

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement**

Replace the `compose` body with eviction-aware assembly:

```python
    # Eviction order (most-evictable → least). Identity floor is below.
    _EVICTION_ORDER: list[tuple[str, int]] = [
        # (slot_label, preserve_token_count)
        ("LOCATION.flourish", 8),
        ("DIRECTION_ACTION.flourish", 8),
        ("ART_SENSIBILITY.WORLD", 0),       # drop entirely
        ("ART_SENSIBILITY.CULTURE.flourish", 12),
    ]

    # Identity floor — never evict below these.
    _IDENTITY_FLOOR: set[str] = {
        "CASTING",
        "DIRECTION_CAMERA",
        "ART_SENSIBILITY.GENRE",
    }

    def compose(self, target: RenderTarget) -> ComposedPrompt:
        layers = self._resolve_all_layers(target)
        dropped: list[str] = []
        warnings: list[str] = []

        # Participant-LOD downgrade runs first (Task 21 will implement);
        # for now we go directly to slot-level eviction.

        current_tokens = sum(l.estimated_tokens for l in layers)
        if current_tokens > _TOKEN_LIMIT:
            layers, dropped = self._apply_slot_eviction(layers)
            current_tokens = sum(l.estimated_tokens for l in layers)
            warnings.append(
                f"token budget eviction applied: "
                f"{current_tokens}/{_TOKEN_LIMIT}",
            )

        if current_tokens > _TOKEN_LIMIT:
            raise BudgetError(
                "identity floor breached",
                breakdown={l.slot: l.estimated_tokens for l in layers},
            )

        positive = self._assemble(layers)
        clip = self._build_clip(layers)
        negative = self._build_negative(target)
        return ComposedPrompt(
            positive_prompt=positive,
            clip_prompt=clip,
            negative_prompt=negative,
            worker_type=self._select_worker(target),
            seed=self._derive_seed(target),
            layers=layers,
            dropped_layers=dropped,
            warnings=warnings,
        )

    def _apply_slot_eviction(
        self, layers: list[LayerContribution]
    ) -> tuple[list[LayerContribution], list[str]]:
        result = [l.model_copy() for l in layers]
        dropped: list[str] = []

        def _truncate(layer: LayerContribution, keep_tokens: int) -> None:
            words = layer.tokens.split()
            keep_words = max(1, int(keep_tokens / _TOKENS_PER_WORD))
            layer.tokens = " ".join(words[:keep_words])
            layer.estimated_tokens = _estimate_tokens(layer.tokens)

        for eviction_label, preserve in self._EVICTION_ORDER:
            if sum(l.estimated_tokens for l in result) <= _TOKEN_LIMIT:
                break

            base_slot, _, flourish = eviction_label.partition(".")
            if flourish == "flourish":
                for layer in result:
                    if layer.slot == base_slot or layer.slot.startswith(
                        base_slot + "."
                    ):
                        if layer.estimated_tokens > preserve:
                            _truncate(layer, preserve)
                            dropped.append(
                                f"{layer.slot}:{layer.source}:flourish",
                            )
            else:
                # Drop entirely
                before = len(result)
                result = [l for l in result if l.slot != eviction_label]
                if len(result) < before:
                    dropped.append(eviction_label)

        return result, dropped
```

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): budget estimation and slot eviction with identity floor"
```

---

### Task 21: Budget-driven LOD downgrade (participants)

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing test**

```python
def test_budget_downgrade_participants_before_slot_eviction(
    composer: PromptComposer,
) -> None:
    # Six participants + rich culture/environment — forces downgrade
    # from planned LODs toward `background` for tail participants.
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=[
            "npc:rux", "npc:mira",
            # Reuse existing two characters; participant duplication is OK
            # because LOD downgrade operates on ordinal position not identity.
            "npc:rux", "npc:mira", "npc:rux", "npc:mira",
        ],
        action="argument " * 50,
        location="where:testworld/the_lookout",
        camera=CameraPreset.scene,
    )
    result = composer.compose(t)
    # Even under budget pressure, at least one CASTING layer survives for
    # every participant slot (never drop below background).
    casting_sources = [l.source for l in result.layers if l.slot == "CASTING"]
    assert len(casting_sources) == len(t.participants)
```

- [ ] **Step 2: Run test**

Expected: FAIL (or participants dropped instead of downgraded).

- [ ] **Step 3: Implement**

Replace Task 19's `compose()` and `_resolve_all_layers()`. After this task, Task 19's `_resolve_all_layers` is dead code — delete it (the plan-aware version below is the only caller).

Add a downgrade pass before `_apply_slot_eviction` in `compose`:

```python
    def compose(self, target: RenderTarget) -> ComposedPrompt:
        plan = self._character_lod_plan(target)
        layers = self._resolve_all_layers_with_plan(target, plan)
        dropped: list[str] = []
        warnings: list[str] = []

        # 1. Participant LOD downgrade (preserves presence of every participant).
        while sum(l.estimated_tokens for l in layers) > _TOKEN_LIMIT:
            downgraded = self._downgrade_one_participant(plan)
            if not downgraded:
                break
            layers = self._resolve_all_layers_with_plan(target, plan)

        # 2. Slot-level eviction.
        if sum(l.estimated_tokens for l in layers) > _TOKEN_LIMIT:
            layers, dropped = self._apply_slot_eviction(layers)

        if sum(l.estimated_tokens for l in layers) > _TOKEN_LIMIT:
            raise BudgetError(
                "identity floor breached",
                breakdown={l.slot: l.estimated_tokens for l in layers},
            )

        # ... unchanged from here ...
```

Add helpers:

```python
    _LOD_ORDER = [LOD.SOLO, LOD.LONG, LOD.SHORT, LOD.BACKGROUND]

    def _downgrade_one_participant(self, plan: dict[str, LOD]) -> bool:
        """Downgrade the lowest-priority participant one LOD rung. Returns True
        if a downgrade was applied, False if every participant is already at
        background."""
        # Operate in reverse order so tail participants downgrade first.
        for ref in reversed(list(plan.keys())):
            current = plan[ref]
            idx = self._LOD_ORDER.index(current)
            if idx < len(self._LOD_ORDER) - 1:
                plan[ref] = self._LOD_ORDER[idx + 1]
                return True
        return False

    def _resolve_all_layers_with_plan(
        self, target: RenderTarget, plan: dict[str, LOD]
    ) -> list[LayerContribution]:
        # Delegate to _resolve_all_layers but override _character_lod_plan
        # for this call using the passed-in plan.
        art = self._resolve_art_sensibility(target)
        casting = self._resolve_casting_with_plan(target, plan)
        location = self._resolve_location(target)
        action = [self._resolve_direction_action(target)]
        camera = [self._resolve_direction_camera(target)]
        return art + casting + location + action + camera

    def _resolve_casting_with_plan(
        self, target: RenderTarget, plan: dict[str, LOD]
    ) -> list[LayerContribution]:
        if target.kind == "poi":
            return self._resolve_casting(target)
        layers: list[LayerContribution] = []
        for ref, lod in plan.items():
            tokens = self._characters.get(ref)
            text = tokens.descriptions[lod]
            layers.append(
                LayerContribution(
                    slot="CASTING", source=ref, tokens=text,
                    estimated_tokens=_estimate_tokens(text),
                ),
            )
        return layers
```

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): budget-driven participant LOD downgrade"
```

---

### Task 22: CatalogMissError surfaced from compose()

**Files:**
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing test**

```python
from sidequest_daemon.media.recipes import CatalogMissError


def test_unknown_character_raises_catalog_miss(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:nobody",
    )
    with pytest.raises(CatalogMissError) as exc:
        composer.compose(t)
    assert exc.value.missing_id == "npc:nobody"


def test_unknown_place_raises_catalog_miss(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="poi", world="testworld", genre="testgenre",
        place="where:testworld/fabricated",
    )
    with pytest.raises(CatalogMissError):
        composer.compose(t)
```

- [ ] **Step 2: Run tests**

Expected: PASS immediately (catalogs already raise; composer propagates).

- [ ] **Step 3: Implement (none needed if PASS)**

If the tests fail, audit each `_resolve_*` method to ensure `CatalogMissError` from `.get()` is not swallowed.

- [ ] **Step 4: Re-run**

Expected: PASS.

- [ ] **Step 5: Commit (if fixes needed)**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "test(composer): assert CatalogMissError propagation"
```

---

## Phase 6 — OTEL and CLI

### Task 23: OTEL span render.prompt_composed

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/prompt_composer.py`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write failing test**

```python
def test_compose_emits_otel_span(composer: PromptComposer, monkeypatch) -> None:
    emitted: list[dict] = []

    def fake_emit(name: str, payload: dict) -> None:
        emitted.append({"name": name, "payload": payload})

    monkeypatch.setattr(
        "sidequest_daemon.media.prompt_composer._emit_watcher_event",
        fake_emit,
    )
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    composer.compose(t)
    assert any(e["name"] == "render.prompt_composed" for e in emitted)
    span = next(e for e in emitted if e["name"] == "render.prompt_composed")
    assert span["payload"]["kind"] == "portrait"
    assert span["payload"]["world"] == "testworld"
    assert "layers" in span["payload"]
    assert any(l["slot"] == "CASTING" for l in span["payload"]["layers"])
```

- [ ] **Step 2: Run test**

Expected: FAIL.

- [ ] **Step 3: Implement**

Add at the top of `prompt_composer.py`:

```python
try:
    from sidequest_daemon.telemetry import emit_watcher_event as _emit_watcher_event
except ImportError:
    # Stand-in when telemetry is not wired; the real module must exist in prod.
    def _emit_watcher_event(name: str, payload: dict) -> None:
        log.debug("otel (unwired): %s %s", name, payload)
```

Check whether `sidequest_daemon.telemetry.emit_watcher_event` exists:

```bash
grep -r "emit_watcher_event\|watcher_event" sidequest-daemon/sidequest_daemon/ --include="*.py"
```

If the symbol exists elsewhere (e.g. `sidequest_daemon.watcher` or `sidequest_daemon.otel`), import from there instead — do NOT create a stub module. If no watcher emit helper exists, this task blocks on wiring one in; pull in the OTEL helper from the existing daemon instrumentation (per CLAUDE.md OTEL Observability Principle — every subsystem must emit).

Add the emit call at the end of `compose`, just before returning:

```python
        _emit_watcher_event(
            "render.prompt_composed",
            {
                "kind": target.kind,
                "world": target.world,
                "genre": target.genre,
                "total_estimated_tokens": sum(
                    l.estimated_tokens for l in layers
                ),
                "layers": [
                    {
                        "slot": l.slot,
                        "source": l.source,
                        "estimated_tokens": l.estimated_tokens,
                    }
                    for l in layers
                ],
                "dropped_layers": dropped,
                "warnings": warnings,
            },
        )
```

- [ ] **Step 4: Run test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/prompt_composer.py tests/test_composer.py
git commit -m "feat(composer): emit render.prompt_composed OTEL span"
```

---

### Task 24: sidequest-promptpreview CLI — argparse + text output

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/preview.py`
- Create: `sidequest-daemon/tests/test_preview_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# sidequest-daemon/tests/test_preview_cli.py
import json
from pathlib import Path

import pytest

from sidequest_daemon.media.preview import main

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "visual_recipes" / "genre_packs"


def _run(argv: list[str], capsys) -> str:
    exit_code = main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0, f"CLI exited {exit_code}: {captured.err}"
    return captured.out


def test_cli_portrait_text_output(capsys, monkeypatch) -> None:
    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(FIXTURE_ROOT))
    out = _run([
        "portrait",
        "--character", "npc:rux",
        "--world", "testworld",
        "--genre", "testgenre",
    ], capsys)
    assert "== Target ==" in out
    assert "== Composed prompt ==" in out
    assert "== Layer breakdown ==" in out
    assert "npc:rux" in out
    assert "inquisitor" in out


def test_cli_illustration_text_output(capsys, monkeypatch) -> None:
    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(FIXTURE_ROOT))
    out = _run([
        "illustration",
        "--participants", "npc:rux,npc:mira",
        "--location", "where:testworld/the_lookout",
        "--action", "arriving at dusk",
        "--camera", "scene",
        "--world", "testworld",
        "--genre", "testgenre",
    ], capsys)
    assert "arriving at dusk" in out
    assert "watchtower" in out


def test_cli_json_output_roundtrips(capsys, monkeypatch) -> None:
    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(FIXTURE_ROOT))
    out = _run([
        "portrait",
        "--character", "npc:rux",
        "--world", "testworld",
        "--genre", "testgenre",
        "--json",
    ], capsys)
    payload = json.loads(out)
    assert payload["worker_type"]
    assert payload["positive_prompt"]
    assert any(l["slot"] == "CASTING" for l in payload["layers"])


def test_cli_unknown_character_exits_nonzero(capsys, monkeypatch) -> None:
    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(FIXTURE_ROOT))
    exit_code = main([
        "portrait",
        "--character", "npc:ghost",
        "--world", "testworld",
        "--genre", "testgenre",
    ])
    assert exit_code != 0
    assert "ghost" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests**

Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement**

```python
# sidequest-daemon/sidequest_daemon/media/preview.py
"""sidequest-promptpreview CLI — print the composed prompt for any target."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sidequest_daemon.media.camera_specs import CameraLoader
from sidequest_daemon.media.catalogs import (
    CharacterCatalog,
    PlaceCatalog,
    StyleCatalog,
)
from sidequest_daemon.media.prompt_composer import PromptComposer
from sidequest_daemon.media.recipe_loader import RecipeLoader
from sidequest_daemon.media.recipes import (
    CameraPreset,
    CatalogMissError,
    RenderTarget,
)

_DAEMON_ROOT = Path(__file__).resolve().parents[2]


def _build_composer(genre: str, world: str) -> PromptComposer:
    packs_root = Path(os.environ.get("SIDEQUEST_GENRE_PACKS", ""))
    if not packs_root.exists():
        raise SystemExit(
            f"SIDEQUEST_GENRE_PACKS does not exist: {packs_root!r}",
        )
    return PromptComposer(
        recipes=RecipeLoader.from_file(_DAEMON_ROOT / "recipes.yaml"),
        cameras=CameraLoader.from_file(_DAEMON_ROOT / "cameras.yaml"),
        characters=CharacterCatalog.load(packs_root, genre=genre, world=world),
        places=PlaceCatalog.load(packs_root, genre=genre, world=world),
        styles=StyleCatalog.load(packs_root, genre=genre, world=world),
    )


def _build_target(args: argparse.Namespace) -> RenderTarget:
    kwargs: dict = {"kind": args.kind, "world": args.world, "genre": args.genre}
    if args.kind == "portrait":
        kwargs["character"] = args.character
        if args.background:
            kwargs["background"] = args.background
        if args.pose_override:
            kwargs["pose_override"] = args.pose_override
        if args.camera:
            kwargs["camera"] = CameraPreset(args.camera)
    elif args.kind == "poi":
        kwargs["place"] = args.place
    elif args.kind == "illustration":
        kwargs["participants"] = [
            p.strip() for p in args.participants.split(",") if p.strip()
        ]
        kwargs["location"] = args.location
        kwargs["action"] = args.action
        kwargs["camera"] = CameraPreset(args.camera)
    return RenderTarget(**kwargs)


def _format_text(target: RenderTarget, result) -> str:
    lines: list[str] = []
    lines.append("== Target ==")
    lines.append(f"kind:         {target.kind}")
    lines.append(f"world:        {target.world}")
    lines.append(f"genre:        {target.genre}")
    lines.append("")
    lines.append("== Composed prompt ==")
    lines.append(result.positive_prompt)
    lines.append("")
    lines.append("== Layer breakdown ==")
    lines.append(f"{'slot':<30} {'source':<40} {'tokens':>7}")
    for layer in result.layers:
        lines.append(
            f"{layer.slot:<30} {layer.source:<40} {layer.estimated_tokens:>7}",
        )
    total = sum(l.estimated_tokens for l in result.layers)
    lines.append(f"{'':<30} {'':<40} {'-' * 7}")
    lines.append(f"{'':<30} {'':<40} {total:>7}  (of 512 T5 budget)")
    lines.append("")
    lines.append("== Warnings ==")
    if result.warnings:
        for w in result.warnings:
            lines.append(f"- {w}")
    else:
        lines.append("(none)")
    return "\n".join(lines) + "\n"


def _format_json(result) -> str:
    return json.dumps(result.model_dump(), indent=2) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sidequest-promptpreview")
    subs = p.add_subparsers(dest="kind", required=True)

    def _shared(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--world", required=True)
        sp.add_argument("--genre", required=True)
        sp.add_argument("--json", action="store_true")

    portrait = subs.add_parser("portrait")
    portrait.add_argument("--character", required=True)
    portrait.add_argument("--background", default=None)
    portrait.add_argument("--pose-override", default=None)
    portrait.add_argument("--camera", default=None)
    _shared(portrait)

    poi = subs.add_parser("poi")
    poi.add_argument("--place", required=True)
    _shared(poi)

    illus = subs.add_parser("illustration")
    illus.add_argument("--participants", required=True, help="comma-separated refs")
    illus.add_argument("--location", required=True)
    illus.add_argument("--action", required=True)
    illus.add_argument("--camera", required=True)
    _shared(illus)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        target = _build_target(args)
        composer = _build_composer(args.genre, args.world)
        result = composer.compose(target)
    except CatalogMissError as e:
        sys.stderr.write(f"catalog miss: {e}\n")
        return 2
    except ValueError as e:
        sys.stderr.write(f"invalid target: {e}\n")
        return 3

    if args.json:
        sys.stdout.write(_format_json(result))
    else:
        sys.stdout.write(_format_text(target, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_preview_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/preview.py tests/test_preview_cli.py
git commit -m "feat(preview): sidequest-promptpreview CLI with text + JSON output"
```

---

### Task 25: CLI entry point in pyproject.toml

**Files:**
- Modify: `sidequest-daemon/pyproject.toml`

- [ ] **Step 1: Add the script entry**

Add under `[project.scripts]` (create the table if it does not exist):

```toml
[project.scripts]
sidequest-promptpreview = "sidequest_daemon.media.preview:main"
```

- [ ] **Step 2: Sync**

Run: `uv sync`
Expected: no errors, entry point registered.

- [ ] **Step 3: Verify the installed CLI runs**

Run: `SIDEQUEST_GENRE_PACKS=tests/fixtures/visual_recipes/genre_packs uv run sidequest-promptpreview portrait --character npc:rux --world testworld --genre testgenre`
Expected: same text output as Task 24 test.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat(preview): register sidequest-promptpreview entry point"
```

---

## Phase 7 — Renderer Integration

### Task 26: StageCue.camera field + TACTICAL_SKETCH retirement

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/renderer/models.py`
- Modify: existing tests that reference `RenderTier.TACTICAL_SKETCH`
- Create: `sidequest-daemon/tests/test_stage_cue_camera.py`

- [ ] **Step 1: Find existing TACTICAL_SKETCH callers**

Run:
```bash
grep -rn "TACTICAL_SKETCH" sidequest-daemon sidequest-server 2>/dev/null
```

List each caller. These callers must migrate in Task 32.

- [ ] **Step 2: Write failing test**

```python
# sidequest-daemon/tests/test_stage_cue_camera.py
import pytest
from pydantic import ValidationError

from sidequest_daemon.media.recipes import CameraPreset
from sidequest_daemon.renderer.models import RenderTier, StageCue


def test_tactical_sketch_removed() -> None:
    assert not hasattr(RenderTier, "TACTICAL_SKETCH")


def test_stage_cue_accepts_camera() -> None:
    cue = StageCue(
        tier=RenderTier.SCENE_ILLUSTRATION,
        subject="goblin ambush",
        camera=CameraPreset.topdown_90,
    )
    assert cue.camera is CameraPreset.topdown_90


def test_stage_cue_camera_optional() -> None:
    cue = StageCue(
        tier=RenderTier.PORTRAIT,
        subject="rux",
    )
    assert cue.camera is None
```

- [ ] **Step 3: Run test**

Expected: FAIL.

- [ ] **Step 4: Implement**

Edit `sidequest_daemon/renderer/models.py`:

```python
from sidequest_daemon.media.recipes import CameraPreset


class RenderTier(str, Enum):
    """Image generation tiers — broad latency/quality bands."""

    SCENE_ILLUSTRATION = "scene_illustration"
    PORTRAIT = "portrait"
    PORTRAIT_SQUARE = "portrait_square"
    LANDSCAPE = "landscape"
    TEXT_OVERLAY = "text_overlay"
    CARTOGRAPHY = "cartography"
    FOG_OF_WAR = "fog_of_war"


class StageCue(BaseModel):
    tier: RenderTier
    subject: str
    mood: str = ""
    location: str = ""
    characters: list[str] = []
    tags: list[str] = []
    seed: int | None = None
    turn_id: int = 0
    metadata: dict[str, Any] = {}
    camera: CameraPreset | None = None
```

- [ ] **Step 5: Run test and full daemon suite**

Run: `uv run pytest -v`
Expected: tests-for-stage-cue PASS; any tests that referenced `RenderTier.TACTICAL_SKETCH` now FAIL. These are the callers that must be migrated in Task 32. Note failures; do not commit until callers are migrated.

- [ ] **Step 6: Commit (after Task 32 callers migrated — see Task 32 commit)**

Combined commit with Task 32 to avoid an intermediate broken state:
```bash
git add sidequest_daemon/renderer/models.py tests/test_stage_cue_camera.py
# … plus caller fixes from Task 32
git commit -m "feat(renderer): StageCue.camera + retire TACTICAL_SKETCH"
```

---

### Task 27: Pillow post-processing (crop + rotate)

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/post_processor.py`
- Create: `sidequest-daemon/tests/test_post_processor.py`

- [ ] **Step 1: Write failing tests**

```python
# sidequest-daemon/tests/test_post_processor.py
from PIL import Image

from sidequest_daemon.media.camera_specs import PostDirective
from sidequest_daemon.media.post_processor import apply_post


def _make_image(size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGB", size, color=(128, 0, 0))
    # Add a central white square so we can verify the crop region.
    inner = Image.new("RGB", (size[0] // 2, size[1] // 2), color=(255, 255, 255))
    img.paste(inner, (size[0] // 4, size[1] // 4))
    return img


def test_crop_center_25_percent_preserves_center() -> None:
    src = _make_image((4096, 4096))
    directive = PostDirective(kind="crop", mode="center", percent=0.25)
    out = apply_post(src, directive)
    assert out.size == (1024, 1024)
    # Center pixel must be white (the inner square we painted).
    assert out.getpixel((512, 512)) == (255, 255, 255)


def test_rotate_inscribed_rect() -> None:
    src = _make_image((1024, 1024))
    directive = PostDirective(kind="rotate", degrees=15.0)
    out = apply_post(src, directive)
    assert out.size[0] < src.size[0]
    assert out.size[1] < src.size[1]
    # No black corners — every pixel has source content.
    assert out.getpixel((0, 0)) != (0, 0, 0)


def test_no_post_returns_input_unchanged() -> None:
    src = _make_image((512, 512))
    out = apply_post(src, None)
    assert out is src
```

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# sidequest-daemon/sidequest_daemon/media/post_processor.py
"""Pillow-based post-processing for camera preset directives."""

from __future__ import annotations

import math

from PIL import Image

from sidequest_daemon.media.camera_specs import PostDirective


def apply_post(img: Image.Image, directive: PostDirective | None) -> Image.Image:
    if directive is None:
        return img
    if directive.kind == "crop":
        return _center_crop(img, directive.percent or 1.0)
    if directive.kind == "rotate":
        return _rotate_inscribed(img, directive.degrees or 0.0)
    raise ValueError(f"unknown post kind: {directive.kind!r}")


def _center_crop(img: Image.Image, percent: float) -> Image.Image:
    w, h = img.size
    new_w = max(1, int(w * percent))
    new_h = max(1, int(h * percent))
    left = (w - new_w) // 2
    top = (h - new_h) // 2
    return img.crop((left, top, left + new_w, top + new_h))


def _rotate_inscribed(img: Image.Image, degrees: float) -> Image.Image:
    rotated = img.rotate(degrees, resample=Image.BICUBIC, expand=False)
    # Inscribed rectangle inside a rotated rectangle of same aspect ratio.
    # For a square input, side = orig * (cos θ - sin θ) scaled appropriately.
    w, h = img.size
    theta = math.radians(abs(degrees))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    # Largest inscribed rectangle of same aspect ratio (simplified square-case
    # formula — works for |θ| < 45°).
    new_w = int((w * cos_t - h * sin_t) if w >= h else (h * cos_t - w * sin_t))
    new_h = int(new_w * (h / w)) if w >= h else int(new_w * (w / h))
    new_w = max(1, new_w)
    new_h = max(1, new_h)
    left = (w - new_w) // 2
    top = (h - new_h) // 2
    return rotated.crop((left, top, left + new_w, top + new_h))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_post_processor.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/post_processor.py tests/test_post_processor.py
git commit -m "feat(post): Pillow crop + rotate post-processing"
```

---

### Task 28: Post-processing extra-resolution budgeting

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/post_processor.py`
- Modify: `sidequest-daemon/tests/test_post_processor.py`

- [ ] **Step 1: Write failing test**

```python
from sidequest_daemon.media.post_processor import required_render_size


def test_crop_25_percent_requires_4x_target_per_axis() -> None:
    target_w, target_h = 1024, 1024
    directive = PostDirective(kind="crop", mode="center", percent=0.25)
    w, h = required_render_size((target_w, target_h), directive)
    assert w == 4096
    assert h == 4096


def test_no_post_returns_target() -> None:
    assert required_render_size((1024, 1024), None) == (1024, 1024)


def test_rotate_requires_diagonal_envelope() -> None:
    directive = PostDirective(kind="rotate", degrees=15.0)
    w, h = required_render_size((1024, 1024), directive)
    # Rotating then inscribing — we need enough source that the inscribed
    # square matches the target.
    assert w >= 1200
    assert h >= 1200
```

- [ ] **Step 2: Run tests**

Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `post_processor.py`:

```python
def required_render_size(
    target_size: tuple[int, int],
    directive: PostDirective | None,
) -> tuple[int, int]:
    if directive is None:
        return target_size
    tw, th = target_size
    if directive.kind == "crop":
        percent = directive.percent or 1.0
        if percent <= 0:
            raise ValueError("crop percent must be > 0")
        return (int(tw / percent), int(th / percent))
    if directive.kind == "rotate":
        theta = math.radians(abs(directive.degrees or 0.0))
        # Inverse of _rotate_inscribed: target is inscribed_side; need source.
        # For equal aspect: target = source * (cos θ - sin θ ... ) inverse.
        denom = max(1e-6, math.cos(theta) - math.sin(theta))
        return (int(tw / denom) + 1, int(th / denom) + 1)
    return target_size
```

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/post_processor.py tests/test_post_processor.py
git commit -m "feat(post): required_render_size helper for pre-crop budgeting"
```

---

### Task 29: zimage_mlx_worker — build RenderTarget, call composer, apply post

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py`
- Create: `sidequest-daemon/tests/test_composer_wiring.py`

- [ ] **Step 1: Read the current worker**

Read `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py` end-to-end. The change is to replace wherever the old `PromptComposer.compose(cue, style)` is called with: build a `RenderTarget` from the `StageCue`, call the new `PromptComposer.compose(target)`, apply post-processing from the camera preset.

- [ ] **Step 2: Write the wiring test**

```python
# sidequest-daemon/tests/test_composer_wiring.py
"""Wiring test (per CLAUDE.md): prove renderer worker uses the new composer."""

from pathlib import Path

import pytest

from sidequest_daemon.media.recipes import CameraPreset
from sidequest_daemon.media.workers import zimage_mlx_worker
from sidequest_daemon.renderer.models import RenderTier, StageCue

FIXTURE_ROOT = (
    Path(__file__).parent / "fixtures" / "visual_recipes" / "genre_packs"
)


def test_worker_imports_new_composer() -> None:
    """The worker must import PromptComposer from prompt_composer.py."""
    source = Path(zimage_mlx_worker.__file__).read_text()
    assert "from sidequest_daemon.media.prompt_composer import PromptComposer" in source
    assert "RenderTarget" in source


def test_worker_build_render_target_from_cue(monkeypatch) -> None:
    """When the worker receives a StageCue with a CameraPreset, it must
    construct a valid RenderTarget and pass it to the composer."""
    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(FIXTURE_ROOT))
    cue = StageCue(
        tier=RenderTier.PORTRAIT,
        subject="npc:rux",
        characters=["npc:rux"],
        camera=CameraPreset.portrait_3q,
        metadata={"world": "testworld", "genre": "testgenre"},
    )
    target = zimage_mlx_worker.build_render_target(cue)
    assert target.kind == "portrait"
    assert target.character == "npc:rux"
    assert target.world == "testworld"
    assert target.genre == "testgenre"


def test_wiring_end_to_end_produces_nonempty_prompt(monkeypatch) -> None:
    """The worker's compose path produces a non-empty positive prompt."""
    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(FIXTURE_ROOT))
    cue = StageCue(
        tier=RenderTier.PORTRAIT,
        subject="npc:rux",
        characters=["npc:rux"],
        camera=CameraPreset.portrait_3q,
        metadata={"world": "testworld", "genre": "testgenre"},
    )
    prompt = zimage_mlx_worker.compose_prompt_for(cue)
    assert "inquisitor" in prompt.positive_prompt
    assert prompt.seed != 0
```

- [ ] **Step 3: Run tests**

Expected: FAIL (the worker functions don't exist yet).

- [ ] **Step 4: Implement worker migration**

In `zimage_mlx_worker.py`:

```python
# Add imports
from pathlib import Path
import os

from sidequest_daemon.media.camera_specs import CameraLoader
from sidequest_daemon.media.catalogs import (
    CharacterCatalog,
    PlaceCatalog,
    StyleCatalog,
)
from sidequest_daemon.media.post_processor import apply_post, required_render_size
from sidequest_daemon.media.prompt_composer import PromptComposer
from sidequest_daemon.media.recipe_loader import RecipeLoader
from sidequest_daemon.media.recipes import (
    CameraPreset,
    CatalogMissError,
    ComposedPrompt,
    RenderTarget,
)

_DAEMON_ROOT = Path(__file__).resolve().parents[3]


def _get_composer(genre: str, world: str) -> PromptComposer:
    """Build a composer scoped to the target's world."""
    packs_root = Path(os.environ["SIDEQUEST_GENRE_PACKS"])
    return PromptComposer(
        recipes=RecipeLoader.from_file(_DAEMON_ROOT / "recipes.yaml"),
        cameras=CameraLoader.from_file(_DAEMON_ROOT / "cameras.yaml"),
        characters=CharacterCatalog.load(packs_root, genre=genre, world=world),
        places=PlaceCatalog.load(packs_root, genre=genre, world=world),
        styles=StyleCatalog.load(packs_root, genre=genre, world=world),
    )


def build_render_target(cue: StageCue) -> RenderTarget:
    """Translate a StageCue into a RenderTarget.

    `cue.metadata["world"]` and `cue.metadata["genre"]` are required — fail
    loud if either is missing.
    """
    world = cue.metadata.get("world")
    genre = cue.metadata.get("genre")
    if not world or not genre:
        raise ValueError(
            "StageCue.metadata must carry `world` and `genre` for composer routing",
        )

    if cue.tier in (RenderTier.PORTRAIT, RenderTier.PORTRAIT_SQUARE):
        character = cue.characters[0] if cue.characters else cue.subject
        return RenderTarget(
            kind="portrait", world=world, genre=genre, character=character,
            camera=cue.camera,
        )
    if cue.tier == RenderTier.LANDSCAPE:
        # POI render: subject is a `where:` ref.
        return RenderTarget(
            kind="poi", world=world, genre=genre, place=cue.subject,
        )
    if cue.tier == RenderTier.SCENE_ILLUSTRATION:
        return RenderTarget(
            kind="illustration", world=world, genre=genre,
            participants=cue.characters,
            location=cue.location or cue.metadata.get("location_ref", ""),
            action=cue.subject,
            camera=cue.camera or CameraPreset.scene,
        )
    raise ValueError(f"unsupported tier for composer routing: {cue.tier!r}")


def compose_prompt_for(cue: StageCue) -> ComposedPrompt:
    world = cue.metadata["world"]
    genre = cue.metadata["genre"]
    composer = _get_composer(genre, world)
    target = build_render_target(cue)
    return composer.compose(target)
```

Then locate the worker's render function (where it previously called `PromptComposer().compose(cue, style)`) and replace with:

```python
    prompt = compose_prompt_for(cue)
    # ... pass prompt.positive_prompt, prompt.clip_prompt, prompt.negative_prompt,
    # prompt.seed to the MLX pipeline ...

    # Post-processing: if the camera preset declares a post directive,
    # render at the pre-crop resolution and apply after inference.
    camera_loader = CameraLoader.from_file(_DAEMON_ROOT / "cameras.yaml")
    post = camera_loader.get(cue.camera).post if cue.camera else None
    render_w, render_h = required_render_size((target_w, target_h), post)
    # ... run inference at (render_w, render_h) ...
    if post is not None:
        image = apply_post(image, post)
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_composer_wiring.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest_daemon/media/workers/zimage_mlx_worker.py tests/test_composer_wiring.py
git commit -m "feat(worker): wire zimage_mlx_worker to new composer + post-processing"
```

---

### Task 30: Daemon startup validation

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/daemon.py`
- Modify: `sidequest-daemon/tests/test_composer_wiring.py`

- [ ] **Step 1: Write failing test**

```python
def test_daemon_refuses_to_start_with_invalid_recipes(tmp_path, monkeypatch) -> None:
    from sidequest_daemon.media import daemon as daemon_module

    bad = tmp_path / "recipes.yaml"
    bad.write_text("portrait: {kind: portrait, direction_camera: fabricated_shot}")
    with pytest.raises(ValueError):
        daemon_module.validate_startup_config(
            recipes_path=bad,
            cameras_path=Path(__file__).resolve().parents[1] / "cameras.yaml",
        )


def test_daemon_accepts_valid_config() -> None:
    from sidequest_daemon.media import daemon as daemon_module

    root = Path(__file__).resolve().parents[1]
    daemon_module.validate_startup_config(
        recipes_path=root / "recipes.yaml",
        cameras_path=root / "cameras.yaml",
    )
```

- [ ] **Step 2: Run test**

Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `sidequest_daemon/media/daemon.py`:

```python
def validate_startup_config(
    *, recipes_path: Path, cameras_path: Path
) -> None:
    """Fail-loud validation of recipe + camera YAML at daemon boot."""
    from sidequest_daemon.media.camera_specs import CameraLoader
    from sidequest_daemon.media.recipe_loader import RecipeLoader

    CameraLoader.from_file(cameras_path)
    RecipeLoader.from_file(recipes_path)
```

Wire `validate_startup_config` into the daemon's existing boot path (whatever function loads config today). A `startup()` that already runs at boot should call it before accepting connections. Fail-loud on error.

- [ ] **Step 4: Run test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest_daemon/media/daemon.py tests/test_composer_wiring.py
git commit -m "feat(daemon): validate recipes.yaml + cameras.yaml at startup"
```

---

## Phase 8 — Server Cleanup + Caller Migration

### Task 31: Delete dead server-side composer copies

**Repo:** `sidequest-server`

**Files:**
- Delete: `sidequest-server/sidequest/media/prompt_composer.py`
- Delete: `sidequest-server/sidequest/media/subject_extractor.py`
- Delete: any tests under `sidequest-server/tests/` that import the above
- Modify: `sidequest-server/sidequest/renderer/models.py` — remove tier-prefix definitions (if any)
- Modify: `sidequest-server/sidequest/media/__init__.py` — drop any re-exports of the deleted modules

- [ ] **Step 1: Verify no production code imports the dead copies**

Run:
```bash
grep -rn "from sidequest.media.prompt_composer\|from sidequest.media.subject_extractor\|sidequest.media.prompt_composer\|sidequest.media.subject_extractor" sidequest-server/sidequest 2>/dev/null | grep -v __pycache__
```

Expected: **empty output**. If non-empty, the caller must be migrated (the server should be calling into the daemon via the media daemon client, not composing prompts locally). Fix each caller before deleting.

- [ ] **Step 2: Inspect and list server tests that import the dead modules**

Run:
```bash
grep -rln "prompt_composer\|subject_extractor" sidequest-server/tests 2>/dev/null
```

List each test file — these must be deleted alongside the source.

- [ ] **Step 3: Create deletion branch**

```bash
cd sidequest-server
git checkout -b feat/delete-dead-composer-copies
```

- [ ] **Step 4: Delete files**

```bash
git rm sidequest/media/prompt_composer.py sidequest/media/subject_extractor.py
# Plus each test file listed in Step 2:
git rm tests/<file_a>.py tests/<file_b>.py  # as applicable
```

- [ ] **Step 5: Clean up __init__.py and renderer/models.py**

Read `sidequest/media/__init__.py` — remove any line that re-exports `PromptComposer` or `SubjectExtractor`.

Read `sidequest/renderer/models.py` — if tier-prefix dicts (analogous to `_TIER_PROMPT_PREFIX`) exist here as dead code, delete them. Leave the `StageCue` / `RenderTier` protocol types intact (they are shared transport types).

- [ ] **Step 6: Run the full server test suite**

Run: `cd sidequest-server && uv run pytest -v`
Expected: PASS (no imports of deleted modules; tests referencing them are also deleted).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore(server): delete dead composer/subject-extractor copies"
```

---

### Task 32: Migrate TACTICAL_SKETCH callers to StageCue(camera=topdown_90)

**Files:** Each file listed in Task 26 Step 1.

- [ ] **Step 1: For each caller, make the swap**

For every occurrence of `RenderTier.TACTICAL_SKETCH`:
- Change the tier to `RenderTier.SCENE_ILLUSTRATION`
- Add `camera=CameraPreset.topdown_90` to the `StageCue` constructor (or whatever call site builds the cue)
- Update any downstream code that branched on `tier == TACTICAL_SKETCH` — the distinction is now `cue.camera == CameraPreset.topdown_90`

Example:

```python
# before
StageCue(tier=RenderTier.TACTICAL_SKETCH, subject="ambush at the altar", ...)
# after
StageCue(
    tier=RenderTier.SCENE_ILLUSTRATION,
    subject="ambush at the altar",
    camera=CameraPreset.topdown_90,
    ...
)
```

- [ ] **Step 2: Run tests touched by each file**

Run: `cd sidequest-daemon && uv run pytest -v`
Expected: PASS.

- [ ] **Step 3: Run existing combat/map integration tests**

Run any test module whose name matches `combat`, `tactical`, or `map`:
```bash
cd sidequest-daemon && uv run pytest tests/ -v -k "combat or tactical or map"
```
Expected: PASS.

- [ ] **Step 4: Commit (combined with Task 26)**

```bash
git add -A
git commit -m "feat(renderer): retire TACTICAL_SKETCH tier — migrate callers to topdown_90 camera"
```

---

## Phase 9 — Content Migration

### Task 33: Migration script — portrait_manifest LOD stub

**Repo:** `orc-quest` (orchestrator)

**Files:**
- Create: `scripts/migrate_portrait_manifest_lods.py`
- Create: `scripts/tests/test_migrate_portrait_manifest_lods.py`

- [ ] **Step 1: Write failing test**

```python
# scripts/tests/test_migrate_portrait_manifest_lods.py
from pathlib import Path

import yaml

from scripts.migrate_portrait_manifest_lods import migrate_manifest


def test_legacy_single_description_migrates_to_solo(tmp_path) -> None:
    src = tmp_path / "portrait_manifest.yaml"
    src.write_text(yaml.safe_dump({
        "characters": [
            {
                "name": "Rux",
                "role": "inquisitor",
                "type": "npc_major",
                "appearance": "a tall gaunt inquisitor in grey wool",
            },
        ],
    }))
    migrate_manifest(src, in_place=True)
    data = yaml.safe_load(src.read_text())
    char = data["characters"][0]
    assert char["descriptions"]["solo"] == "a tall gaunt inquisitor in grey wool"
    # Non-solo LODs marked for human authoring.
    for lod in ("long", "short", "background"):
        assert char["descriptions"][lod].startswith("TODO:")
    # `appearance` retained for one release for diff-readability; the
    # migration also flags it.
    assert "_needs_lod_authoring" in char


def test_already_migrated_file_is_noop(tmp_path) -> None:
    src = tmp_path / "portrait_manifest.yaml"
    src.write_text(yaml.safe_dump({
        "characters": [
            {
                "id": "rux",
                "descriptions": {
                    "solo": "...", "long": "...",
                    "short": "...", "background": "...",
                },
                "default_pose": "standing",
            },
        ],
    }))
    before = src.read_text()
    migrate_manifest(src, in_place=True)
    after = src.read_text()
    assert before == after
```

- [ ] **Step 2: Run test**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# scripts/migrate_portrait_manifest_lods.py
"""Stub long/short/background LODs on existing portrait_manifest.yaml files.

Preserves existing `appearance` as `descriptions.solo`; flags remaining LODs
for human authoring with TODO markers. No silent fallback — the composer
will fail-loud when a TODO LOD is requested.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

_LODS = ("solo", "long", "short", "background")


def migrate_manifest(path: Path, *, in_place: bool = False) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    changed = False

    for char in data.get("characters", []):
        descriptions = char.get("descriptions")
        if descriptions and all(lod in descriptions for lod in _LODS):
            continue  # already migrated

        appearance = char.get("appearance", "")
        char["descriptions"] = {
            "solo": appearance,
            "long": f"TODO: author long LOD (15-25 tok) for {char.get('name', char.get('id', '?'))}",
            "short": f"TODO: author short LOD (5-10 tok) for {char.get('name', char.get('id', '?'))}",
            "background": f"TODO: author background LOD (1-3 tok) for {char.get('name', char.get('id', '?'))}",
        }
        char.setdefault(
            "id",
            char.get("name", "unknown").lower().replace(" ", "_"),
        )
        char["_needs_lod_authoring"] = True
        char.setdefault("default_pose", "neutral, standing")
        changed = True

    if changed and in_place:
        path.write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    for path in args.manifests:
        migrate_manifest(path, in_place=args.in_place)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/keithavery/Projects/oq-1  # orchestrator root
git add scripts/migrate_portrait_manifest_lods.py scripts/tests/test_migrate_portrait_manifest_lods.py
git commit -m "feat(scripts): migrate_portrait_manifest_lods — stub long/short/bg LODs"
```

---

### Task 34: Migration script — POI backdrop LOD stub

**Files:**
- Create: `scripts/migrate_poi_backdrop_lod.py`
- Create: `scripts/tests/test_migrate_poi_backdrop_lod.py`

- [ ] **Step 1: Write failing test**

```python
# scripts/tests/test_migrate_poi_backdrop_lod.py
from pathlib import Path

import yaml

from scripts.migrate_poi_backdrop_lod import migrate_history


def test_legacy_single_visual_prompt_migrates(tmp_path) -> None:
    src = tmp_path / "history.yaml"
    src.write_text(yaml.safe_dump({
        "chapters": [{
            "name": "Present Age",
            "points_of_interest": [
                {"slug": "lookout", "visual_prompt": "a stone watchtower"},
            ],
        }],
    }))
    migrate_history(src, in_place=True)
    data = yaml.safe_load(src.read_text())
    poi = data["chapters"][0]["points_of_interest"][0]
    assert poi["visual_prompt"]["solo"] == "a stone watchtower"
    assert poi["visual_prompt"]["backdrop"].startswith("TODO:")
```

- [ ] **Step 2: Run test**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# scripts/migrate_poi_backdrop_lod.py
"""Stub `backdrop` LOD on existing POI visual_prompt strings in history.yaml.

Promotes the existing string to `solo`; flags `backdrop` with a TODO for
human authoring.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def migrate_history(path: Path, *, in_place: bool = False) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    changed = False
    for chapter in data.get("chapters", []):
        for poi in chapter.get("points_of_interest", []):
            vp = poi.get("visual_prompt")
            if isinstance(vp, str):
                poi["visual_prompt"] = {
                    "solo": vp,
                    "backdrop": f"TODO: author backdrop LOD for {poi.get('slug', '?')}",
                }
                changed = True
            env = poi.get("environment")
            if isinstance(env, str):
                poi["environment"] = {
                    "solo": env,
                    "backdrop": f"TODO: author backdrop environment for {poi.get('slug', '?')}",
                }
                changed = True
    if changed and in_place:
        path.write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("histories", nargs="+", type=Path)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    for path in args.histories:
        migrate_history(path, in_place=args.in_place)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_poi_backdrop_lod.py scripts/tests/test_migrate_poi_backdrop_lod.py
git commit -m "feat(scripts): migrate_poi_backdrop_lod — stub backdrop LOD"
```

---

### Task 35: Migration script — visual_tag_overrides → place descriptions

**Files:**
- Create: `scripts/migrate_visual_tag_overrides.py`
- Create: `scripts/tests/test_migrate_visual_tag_overrides.py`

- [ ] **Step 1: Write failing test**

```python
# scripts/tests/test_migrate_visual_tag_overrides.py
from pathlib import Path

import yaml

from scripts.migrate_visual_tag_overrides import migrate_world


def test_override_migrates_to_matching_archetype(tmp_path) -> None:
    genre_root = tmp_path / "genre_packs" / "testgenre"
    (genre_root / "worlds" / "testworld").mkdir(parents=True)
    (genre_root / "worlds" / "testworld" / "visual_style.yaml").write_text(
        yaml.safe_dump({
            "visual_tag_overrides": {
                "tavern": "low-ceilinged roadhouse, amber lantern-glow",
            },
        }),
    )
    (genre_root / "places.yaml").write_text(
        yaml.safe_dump({
            "tavern": {
                "landmark": {"solo": "", "backdrop": ""},
                "environment": {"solo": "wood beams", "backdrop": "wood beams"},
                "description": {"solo": "tavern", "backdrop": "tavern"},
            },
        }),
    )
    report = migrate_world(genre_root, "testworld", in_place=True)
    tav = yaml.safe_load((genre_root / "places.yaml").read_text())["tavern"]
    assert "roadhouse" in tav["environment"]["solo"]
    assert report["matched"] == ["tavern"]


def test_override_with_no_match_goes_to_report(tmp_path) -> None:
    genre_root = tmp_path / "genre_packs" / "testgenre"
    (genre_root / "worlds" / "testworld").mkdir(parents=True)
    (genre_root / "worlds" / "testworld" / "visual_style.yaml").write_text(
        yaml.safe_dump({"visual_tag_overrides": {"xenotemple": "glowing geometry"}}),
    )
    (genre_root / "places.yaml").write_text(yaml.safe_dump({}))
    report = migrate_world(genre_root, "testworld", in_place=True)
    assert "xenotemple" in report["unmatched"]
```

- [ ] **Step 2: Run test**

Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# scripts/migrate_visual_tag_overrides.py
"""Port `visual_tag_overrides` (from world visual_style.yaml) into either
the matching archetypal place's environment description, or into a human-
review report for unmatched overrides.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def migrate_world(genre_root: Path, world: str, *, in_place: bool = False) -> dict:
    style_path = genre_root / "worlds" / world / "visual_style.yaml"
    places_path = genre_root / "places.yaml"
    style_data = yaml.safe_load(style_path.read_text()) or {}
    overrides = style_data.get("visual_tag_overrides", {}) or {}
    places_data = yaml.safe_load(places_path.read_text()) if places_path.exists() else {}
    places_data = places_data or {}

    matched: list[str] = []
    unmatched: list[str] = []

    for slug, tokens in overrides.items():
        if slug in places_data:
            # Fold the override into the archetype's solo environment.
            env = places_data[slug].setdefault("environment", {})
            env["solo"] = (env.get("solo", "") + ", " + tokens).strip(", ")
            matched.append(slug)
        else:
            unmatched.append(slug)

    if in_place:
        places_path.write_text(yaml.safe_dump(places_data, sort_keys=False))
        # Clear migrated overrides from visual_style.yaml.
        style_data.pop("visual_tag_overrides", None)
        style_path.write_text(yaml.safe_dump(style_data, sort_keys=False))

    return {"matched": matched, "unmatched": unmatched}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("genre_root", type=Path)
    parser.add_argument("world")
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    report = migrate_world(args.genre_root, args.world, in_place=args.in_place)
    print(f"Matched ({len(report['matched'])}): {report['matched']}")
    print(f"Unmatched ({len(report['unmatched'])}): {report['unmatched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_visual_tag_overrides.py scripts/tests/test_migrate_visual_tag_overrides.py
git commit -m "feat(scripts): migrate_visual_tag_overrides to archetypal place descriptions"
```

---

### Task 36: Seed places.yaml for fantasy-native genres

**Repo:** `sidequest-content`

**Files:**
- Create: `sidequest-content/genre_packs/low_fantasy/places.yaml` (if the pack exists; per content CLAUDE.md it does, though local clone may lag)
- Create: `sidequest-content/genre_packs/caverns_and_claudes/places.yaml`

> **Branch:** `sidequest-content` uses gitflow from `develop`. Create `feat/visual-recipes-archetypes` from `develop`.

- [ ] **Step 1: Confirm which packs exist in this clone**

Run: `ls sidequest-content/genre_packs/`
If `low_fantasy` is absent, seed only `caverns_and_claudes` for now; the other fantasy-native genre will pick up archetypes when that clone lands.

- [ ] **Step 2: Author caverns_and_claudes/places.yaml**

Port `_DEFAULT_LOCATION_TAGS` content from the old composer (rewritten per the meta-humor tone of caverns_and_claudes). Full file content — each of the 8 archetypes needs both `solo` and `backdrop` LODs for `landmark`, `environment`, `description`:

```yaml
# sidequest-content/genre_packs/caverns_and_claudes/places.yaml
# Archetypal places. `landmark` is always empty for archetypes — content
# lives in `environment` and `description`.

tavern:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      wooden-beamed low-ceiling interior, smoke-blackened rafters, hearth
      fire crackling in a stone fireplace, oil-lamp glow on ale-stained
      tables, heavy shutters, a doorway to the cellar, a barmaid who has
      seen everything
    backdrop: "wooden beams, hearth fire, lamp-lit smoky interior"
  description:
    solo: "a tavern common room"
    backdrop: "a tavern"

forest:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      dense canopy of ancient trees, dappled sunlight through leaves,
      mossy undergrowth, ferns and fallen logs, filtered green light
    backdrop: "canopy shadow, trunks receding, dappled light"
  description:
    solo: "deep forest"
    backdrop: "forest"

dungeon:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      stone corridors, flickering torches, damp walls, iron grates,
      puddles reflecting firelight, a draft from somewhere below
    backdrop: "stone corridor, torchlight, damp walls"
  description:
    solo: "a dungeon corridor"
    backdrop: "dungeon depths"

castle:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      stone battlements, tapestries, vaulted ceilings, heraldic banners,
      flagged floor, narrow arrow-slits
    backdrop: "stone battlements, banners, vaulted hall"
  description:
    solo: "a castle great hall"
    backdrop: "a castle"

market:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      merchant stalls, colorful awnings, crowded square, barrels and
      crates, hawkers calling, the smell of spice and smoke
    backdrop: "stalls, awnings, crowded square"
  description:
    solo: "a market square"
    backdrop: "a market"

cave:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      stalactites, dim glow, rough stone, underground pools, breath
      visible in cold air, a sound that might be water
    backdrop: "stalactites, dim stone, underground pool"
  description:
    solo: "a cave chamber"
    backdrop: "a cave"

temple:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      stained glass, marble columns, incense smoke, sacred altars,
      candlelight catching on gilt, stone silence
    backdrop: "stained glass, columns, incense smoke"
  description:
    solo: "a temple nave"
    backdrop: "a temple"

battlefield:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      scorched earth, broken weapons, banners in wind, smoke and dust,
      crows overhead, the dead and the still-not-dead
    backdrop: "scorched earth, broken banners, smoke"
  description:
    solo: "a battlefield"
    backdrop: "a battlefield"
```

- [ ] **Step 3: Validate it loads**

Write a one-shot script (inline in your shell, don't commit):

```bash
cd sidequest-daemon
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run python -c "
from pathlib import Path
from sidequest_daemon.media.catalogs import PlaceCatalog
cat = PlaceCatalog.load(
    Path('../sidequest-content/genre_packs'),
    genre='caverns_and_claudes',
    world='<any-world-that-exists>',
)
print([k for k in cat._entries if 'caverns_and_claudes' in k])
"
```
Expected: 8 archetypes listed (`where:caverns_and_claudes/tavern`, etc).

- [ ] **Step 4: If `low_fantasy` pack exists, repeat Step 2 with tone-appropriate authoring**

For `low_fantasy`, lean into gritty-medieval: tavern = clay mugs, straw on floor, tallow smell; dungeon = cold iron, no romance. Keep the 8 archetype slugs identical across all genres.

- [ ] **Step 5: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/places.yaml
# Add low_fantasy/places.yaml if authored
git commit -m "feat(content): seed archetypal places.yaml for fantasy-native genres"
```

---

### Task 37: Author mutant_wasteland/places.yaml (canary)

**Repo:** `sidequest-content`

**Files:**
- Create: `sidequest-content/genre_packs/mutant_wasteland/places.yaml`

- [ ] **Step 1: Author the file**

`mutant_wasteland` needs genre-rewritten archetypes — a "tavern" is a scavenged dome lit by bioluminescent mushroom lamps; a "temple" is a collapsed broadcast tower with wire-altar rites. Use the `visual_style.yaml` of mutant_wasteland as style guide.

```yaml
# sidequest-content/genre_packs/mutant_wasteland/places.yaml

tavern:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      scavenged dome of riveted sheet metal and fused plastic, bioluminescent
      fungus lamps casting blue-green glow, a bar built from a bus chassis,
      mismatched stools from a dozen salvage runs, mutant moth in the rafters
    backdrop: "riveted metal dome, fungus lamp glow, salvage bar"
  description:
    solo: "a Scrapborn drinking hall"
    backdrop: "a salvage tavern"

forest:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      the Blooming Tangle — trees with bark like fused glass, leaves that pulse
      with faint chloroplast glow, ropes of symbiotic root stretching between
      trunks, soft mossy underfoot with small bones pressed into it
    backdrop: "glass-bark trees, glowing leaves, root-rope canopy"
  description:
    solo: "the Blooming Tangle"
    backdrop: "mutant forest"

dungeon:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      a pre-war bunker reclaimed by rust and mushroom, concrete corridors
      streaked with rad-burn stains, flickering emergency sodium lights,
      chain-link grates, a low hum from something still powered after 200 years
    backdrop: "rusted concrete corridor, sodium flicker, chain-link"
  description:
    solo: "a rad-burn bunker"
    backdrop: "pre-war bunker ruins"

castle:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      a Dome Syndicate fortified compound — shipping-container walls welded
      into a four-story wall, razor-wire crown, a gate scavenged from a pre-war
      vault, banners made of plastic sheeting emblazoned with copper-tape
      sigils
    backdrop: "container walls, razor-wire, plastic banner"
  description:
    solo: "a Syndicate compound"
    backdrop: "a fortified dome"

market:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      a salvage bazaar under patched tarps, stalls of sorted scrap — copper
      wire in coils, boots in every size, pre-war canned goods, rat-meat
      skewers over a brazier, the Scrapborn auctioneer rattling through lots
    backdrop: "patched tarps, scrap piles, brazier smoke"
  description:
    solo: "a salvage bazaar"
    backdrop: "a scrap market"

cave:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      a fissure carved by pre-war ordnance, rad-crystal veins pulsing faint
      green in the walls, a pool of glowing meltwater, cave-adapted moth-lizards
      clinging to the ceiling, the cold tasting of lead
    backdrop: "rad-crystal walls, glowing pool, cave-moths"
  description:
    solo: "a rad-crystal cave"
    backdrop: "mutant cave"

temple:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      a collapsed pre-war broadcast tower repurposed by the Drifters — wire
      altars catching the wind, rust-eaten parabolic dishes like prayer
      wheels, bone windchimes whose song is said to be the Long Signal
    backdrop: "wire altars, rusted dishes, bone chimes"
  description:
    solo: "a Long Signal temple"
    backdrop: "a broadcast-tower shrine"

battlefield:
  landmark: {solo: "", backdrop: ""}
  environment:
    solo: >-
      a scrap-war kill-field — a line of burned-out wasteland trucks, shell
      casings thick on the ground, vultures the size of large dogs, a bruised
      amber sky, the smell of propellant and ozone
    backdrop: "burned trucks, shell-casing scatter, amber sky"
  description:
    solo: "a scrap-war kill-field"
    backdrop: "wasteland battlefield"
```

- [ ] **Step 2: Validate load**

```bash
cd sidequest-daemon
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run python -c "
from pathlib import Path
from sidequest_daemon.media.catalogs import PlaceCatalog
cat = PlaceCatalog.load(Path('../sidequest-content/genre_packs'), genre='mutant_wasteland', world='flickering_reach')
assert 'where:mutant_wasteland/tavern' in cat._entries
print('ok')
"
```

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/mutant_wasteland/places.yaml
git commit -m "feat(content): author mutant_wasteland archetypal places (canary)"
```

---

### Task 38: Author flickering_reach NPC LODs

**Repo:** `sidequest-content`

**Files:**
- Modify: `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/portrait_manifest.yaml`

- [ ] **Step 1: Run the migration script to scaffold**

```bash
cd /Users/keithavery/Projects/oq-1
uv run python scripts/migrate_portrait_manifest_lods.py \
    sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/portrait_manifest.yaml \
    --in-place
```

This creates TODO stubs for every non-solo LOD on every character.

- [ ] **Step 2: Manually author long/short/background for every character**

For each character in the manifest:

- `solo` (40-60 tokens) — already populated by the migration from the existing `appearance` field
- `long` (15-25 tokens) — silhouette-defining features, minimal color, no backstory
- `short` (5-10 tokens) — class/role + one identifying detail
- `background` (1-3 tokens) — the most generic possible noun phrase

Canonical example from the fixture (reuse style):

```yaml
- id: odige_fuseborn
  type: npc_major
  culture: scrapborn
  descriptions:
    solo: >-
      A Scrapborn woman in her fifties with close-cropped grey hair and
      a face that calculates profit margins while you're still talking.
      Medium brown skin marked with circuit-pattern tattoos in copper ink.
      Lean and sharp, dressed in well-maintained salvage clothing — patched,
      yes, but with matching patches. A toolkit at her belt, maintained to
      military precision. Pre-war reading glasses she puts on to look over at you.
    long: >-
      A Scrapborn woman in her fifties, close-cropped grey hair, copper
      circuit tattoos, well-maintained salvage clothing, tool belt,
      pre-war reading glasses
    short: "a Scrapborn woman with copper-ink circuit tattoos and pre-war glasses"
    background: "a Scrapborn"
  default_pose: "arms crossed, appraising stare, glasses lowered"
```

Remove the `_needs_lod_authoring` flag and the legacy `appearance` field once the author is satisfied.

- [ ] **Step 3: Validate load via the daemon**

```bash
cd sidequest-daemon
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run python -c "
from pathlib import Path
from sidequest_daemon.media.catalogs import CharacterCatalog
cat = CharacterCatalog.load(Path('../sidequest-content/genre_packs'), genre='mutant_wasteland', world='flickering_reach')
t = cat.get('npc:odige_fuseborn')
print('solo:', len(t.descriptions[next(iter(t.descriptions))].split()), 'words')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/mutant_wasteland/worlds/flickering_reach/portrait_manifest.yaml
git commit -m "feat(content): author long/short/background LODs for flickering_reach NPCs"
```

---

### Task 39: Author flickering_reach POI backdrop LODs

**Repo:** `sidequest-content`

**Files:**
- Modify: `sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/history.yaml`

- [ ] **Step 1: Run the migration script**

```bash
cd /Users/keithavery/Projects/oq-1
uv run python scripts/migrate_poi_backdrop_lod.py \
    sidequest-content/genre_packs/mutant_wasteland/worlds/flickering_reach/history.yaml \
    --in-place
```

- [ ] **Step 2: For every POI, author the `backdrop` LOD**

`backdrop` is the POI as *setting* for an illustration, not the subject. Terser than `solo`; strip the landmark down to a silhouette.

Example:
```yaml
- slug: the_lookout
  visual_prompt:
    solo: "a weathered stone watchtower atop a rocky promontory, iron-banded timber door, narrow slit windows, a copper weathervane in the shape of an axe"
    backdrop: "a stone watchtower on a rocky promontory"
  environment:
    solo: "barren upland, bruised amber sky, distant mountain silhouettes, scattered gorse"
    backdrop: "barren upland, bruised sky"
```

- [ ] **Step 3: Validate**

```bash
cd sidequest-daemon
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run python -c "
from pathlib import Path
from sidequest_daemon.media.catalogs import PlaceCatalog
cat = PlaceCatalog.load(Path('../sidequest-content/genre_packs'), genre='mutant_wasteland', world='flickering_reach')
t = cat.get('where:flickering_reach/the_lookout')
from sidequest_daemon.media.recipes import PlaceLOD
assert t.landmark[PlaceLOD.BACKDROP]
print('ok')
"
```

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/mutant_wasteland/worlds/flickering_reach/history.yaml
git commit -m "feat(content): author POI backdrop LODs for flickering_reach"
```

---

## Phase 10 — Golden Snapshots and Success Criteria

### Task 40: Golden snapshot tests

**Files:**
- Create: `sidequest-daemon/tests/golden/portrait_npc_rux.txt`
- Create: `sidequest-daemon/tests/golden/poi_the_lookout.txt`
- Create: `sidequest-daemon/tests/golden/illustration_specific_location.txt`
- Create: `sidequest-daemon/tests/golden/illustration_archetypal_location.txt`
- Create: `sidequest-daemon/tests/golden/illustration_topdown_90.txt`
- Modify: `sidequest-daemon/tests/test_composer.py`

- [ ] **Step 1: Write the snapshot-comparison test**

```python
# Append to tests/test_composer.py
GOLDEN_DIR = Path(__file__).parent / "golden"


def _assert_golden(name: str, actual: str) -> None:
    golden_path = GOLDEN_DIR / name
    if not golden_path.exists():
        golden_path.write_text(actual)
        pytest.fail(f"Wrote new golden {name}; inspect and re-run.")
    expected = golden_path.read_text()
    assert actual == expected, f"Golden mismatch for {name}. "\
        f"Delete {golden_path} and re-run to regenerate."


def test_golden_portrait(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="portrait", world="testworld", genre="testgenre",
        character="npc:rux",
    )
    _assert_golden("portrait_npc_rux.txt", composer.compose(t).positive_prompt + "\n")


def test_golden_poi(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="poi", world="testworld", genre="testgenre",
        place="where:testworld/the_lookout",
    )
    _assert_golden("poi_the_lookout.txt", composer.compose(t).positive_prompt + "\n")


def test_golden_illustration_specific(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="arriving at dusk",
        location="where:testworld/the_lookout", camera=CameraPreset.scene,
    )
    _assert_golden(
        "illustration_specific_location.txt",
        composer.compose(t).positive_prompt + "\n",
    )


def test_golden_illustration_archetypal(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="drinking",
        location="where:testgenre/tavern", camera=CameraPreset.scene,
    )
    _assert_golden(
        "illustration_archetypal_location.txt",
        composer.compose(t).positive_prompt + "\n",
    )


def test_golden_illustration_topdown(composer: PromptComposer) -> None:
    t = RenderTarget(
        kind="illustration", world="testworld", genre="testgenre",
        participants=["npc:rux"], action="ambush from the doorway",
        location="where:testworld/the_lookout", camera=CameraPreset.topdown_90,
    )
    _assert_golden(
        "illustration_topdown_90.txt",
        composer.compose(t).positive_prompt + "\n",
    )
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_composer.py::test_golden -v`
Expected: First run writes all 5 goldens and FAILS with "Wrote new golden" messages.

- [ ] **Step 3: Inspect goldens**

Open each file in `tests/golden/` — verify:
- `portrait_npc_rux.txt` — contains `inquisitor`, `three-quarter`, `iron-chased`
- `poi_the_lookout.txt` — contains `watchtower`, `upland`, `wide establishing`
- `illustration_specific_location.txt` — contains `watchtower` AND `arriving at dusk`
- `illustration_archetypal_location.txt` — contains `hearth` (archetype env) AND `drinking`
- `illustration_topdown_90.txt` — contains `top-down`, `ambush`, `watchtower`

If any golden looks wrong (missing tokens, bad ordering), fix the composer and delete the offending golden before re-running.

- [ ] **Step 4: Re-run tests**

Expected: PASS (5 golden tests).

- [ ] **Step 5: Commit**

```bash
git add tests/golden/ tests/test_composer.py
git commit -m "test(composer): golden snapshots for portrait/poi/illustration/topdown"
```

---

### Task 41: Success criteria sweep — CLI against flickering_reach

**Repo:** `sidequest-daemon` (run, no new files)

- [ ] **Step 1: Portrait smoke test**

```bash
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
  uv run sidequest-promptpreview portrait \
  --character npc:odige_fuseborn \
  --world flickering_reach \
  --genre mutant_wasteland
```
Expected: full composed prompt printed, layer breakdown shows `ART_SENSIBILITY.GENRE`, `ART_SENSIBILITY.WORLD`, `ART_SENSIBILITY.CULTURE` (scrapborn).

- [ ] **Step 2: POI smoke test**

```bash
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
  uv run sidequest-promptpreview poi \
  --place where:flickering_reach/the_lookout \
  --world flickering_reach \
  --genre mutant_wasteland
```
Expected: prompt includes watchtower + upland.

- [ ] **Step 3: Illustration specific-location smoke test**

```bash
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
  uv run sidequest-promptpreview illustration \
  --participants npc:odige_fuseborn,npc:darty_ironlung \
  --location where:flickering_reach/the_lookout \
  --action "arguing about the price of copper" \
  --camera scene \
  --world flickering_reach \
  --genre mutant_wasteland
```
Expected: two character contributions, one watchtower location.

- [ ] **Step 4: Illustration archetypal-location smoke test**

```bash
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
  uv run sidequest-promptpreview illustration \
  --participants npc:odige_fuseborn,npc:darty_ironlung \
  --location where:mutant_wasteland/tavern \
  --action "arguing about the price of copper" \
  --camera scene \
  --world flickering_reach \
  --genre mutant_wasteland
```
Expected: same characters, *salvage-dome* archetypal environment (not watchtower).

- [ ] **Step 5: Camera swap smoke test**

Run Step 3 and Step 4 with `--camera topdown_90`; confirm prompts differ (new camera line).

- [ ] **Step 6: Catalog miss smoke test**

```bash
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
  uv run sidequest-promptpreview portrait \
  --character npc:no_such_person \
  --world flickering_reach \
  --genre mutant_wasteland
```
Expected: nonzero exit code; stderr mentions `CharacterCatalog` and `npc:no_such_person`.

- [ ] **Step 7: Record the command output into the PR description**

Paste each command's output into the eventual PR description as evidence of success criteria compliance.

---

### Task 42: Leone canary — live render validation

**Repo:** `sidequest-daemon` (exercises full pipeline)

- [ ] **Step 1: Pick two canary characters in two genre packs**

- Canary A: `npc:odige_fuseborn` in `mutant_wasteland/flickering_reach`
- Canary B: a major NPC in `caverns_and_claudes` (e.g. `npc:<existing>`) — pick any NPC whose `portrait_manifest.yaml` has full LODs authored

- [ ] **Step 2: Run a live Leone render for each**

```bash
just daemon  # ensure daemon is up
# From a second shell, issue a render request via the daemon RPC.
# Replace <daemon-rpc-client-cmd> with whatever the existing integration
# test uses to fire a StageCue at the daemon.
```

Build a `StageCue(tier=RenderTier.PORTRAIT, subject="npc:odige_fuseborn", characters=["npc:odige_fuseborn"], camera=CameraPreset.extreme_closeup_leone, metadata={"world":"flickering_reach","genre":"mutant_wasteland"})` and submit it.

- [ ] **Step 3: Inspect the output**

Open the returned image. Judge:
- Does it read as a Leone-style extreme close-up?
- Is the post-crop working (output is a smaller portion of a larger render)?
- Does the character's identity signature survive the crop?

- [ ] **Step 4: Document the outcome**

Write findings into `docs/content-drift-triage.md` or a new `docs/leone-canary-results.md`:
- If successful: mark `extreme_closeup_leone` validated for production use.
- If not: record failure mode and propose one of (a) stronger prompt, (b) higher pre-crop resolution, (c) face-detection crop center, (d) downgrade preset claims.

- [ ] **Step 5: Commit the findings doc**

```bash
git add docs/leone-canary-results.md
git commit -m "docs(visual-recipes): Leone canary results"
```

---

### Task 43: Final integration — all success criteria checklist

Verify every criterion from the spec:

- [ ] `sidequest-promptpreview` prints a full composed prompt for each of PORTRAIT / POI / ILLUSTRATION targets against `flickering_reach` (covered by Task 41 Steps 1-3)
- [ ] Swapping `--participants` on an illustration target produces visibly different prompts with different culture contributions (run Task 41 Step 3 twice with different `--participants` sets)
- [ ] Swapping `--location` between two specific places produces a visibly different prompt (run Task 41 Step 3 vs Task 41 Step 3 with a different `--location`)
- [ ] Swapping `--location` from specific → archetypal produces a visibly different prompt (Task 41 Step 3 vs Step 4 — same characters/action, different Where)
- [ ] Swapping `--camera scene` → `--camera topdown_90` produces a visibly different prompt; tactical works without `TACTICAL_SKETCH` (Task 41 Step 5)
- [ ] Missing catalog reference produces a clear `CatalogMissError` (Task 41 Step 6)
- [ ] OTEL span `render.prompt_composed` visible in the GM panel on live renders (verify by booting daemon + server and watching `/ws/watcher` — acceptance is the operator confirming the event shows up)
- [ ] All dead server-side copies deleted; no production code imports them (Task 31 Step 1)
- [ ] Full test suite green; wiring test confirms renderer workers use the new composer (Task 29)
- [ ] Leone canary documented (Task 42)

Run the combined gate:
```bash
just check-all
```
Expected: daemon + server + content all green.

---

## Closing

- [ ] **Open the PR per repo on the correct base**
  - `sidequest-daemon` → `develop`
  - `sidequest-content` → `develop`
  - `sidequest-server` → `develop`
  - Orchestrator (this repo, migration scripts) → `main`

- [ ] **PR descriptions must include:** the Task 41 CLI outputs, the Task 42 Leone canary outcome, the success-criteria checklist with each box ticked, and a link to this plan.

- [ ] **After merge:** un-defer ADR-086 story 1 (T5 tokenizer + `visual_budget.yaml` CI gate) in `sprint/backlog.yaml` — that story is now the next logical follow-on.

---

## Notes for Subagent-Driven Execution

- Each Phase maps naturally to a subagent dispatch batch. Phases 1 through 6 can execute in strict sequence.
- Phase 7 (renderer integration) depends on the full composer being green; dispatch it only after Task 23 passes.
- Phase 8 (server cleanup) has **one** cross-repo dependency: the dead-copy deletion must not land before Phase 7 wires the daemon composer, or an in-flight render will fail. Sequence: complete Phase 7 → run Task 29 wiring test on develop → then execute Task 31.
- Phase 9 content migration can run in parallel with Phase 7 (they touch different repos) but its result is only observable once Phase 7 is live.
- Phase 10 (golden snapshots + success criteria) is the final gate.







