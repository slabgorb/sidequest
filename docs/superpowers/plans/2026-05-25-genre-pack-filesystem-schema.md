# Genre Pack Filesystem Schema — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize genre pack file structure with a machine-readable schema, declared extensions in pack.yaml/world.yaml, consolidated asset directories, and a validate command that checks presence, schema, and cross-references without booting the game server.

**Architecture:** A `pack_schema.yaml` file at the content root declares required files, required directories, and named extensions for both genre and world levels. `pack.yaml` and `world.yaml` gain `extensions:` lists. The existing loader adds schema awareness (skip draft worlds, validate extensions). A new `pack` subcommand in the validate CLI checks all gates. Content migration (asset dirs, corpus, audio flattening, cultures→directories) is done in dedicated tasks.

**Tech Stack:** Python (Pydantic v2, Click CLI), YAML, shell scripts for content migration

**Spec:** `docs/superpowers/specs/2026-05-25-genre-pack-filesystem-schema-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `sidequest-content/pack_schema.yaml` | Canonical schema definition |
| Modify | `sidequest-content/genre_packs/*/pack.yaml` | Add `extensions:` key to all 10 packs |
| Modify | `sidequest-content/genre_packs/*/worlds/*/world.yaml` | Add `extensions:` key to all worlds |
| Create | `sidequest-server/sidequest/cli/validate/pack.py` | Pack structure validator |
| Modify | `sidequest-server/sidequest/cli/validate/__main__.py:29-31` | Register `pack` subcommand |
| Modify | `sidequest-server/sidequest/genre/models/world.py:271-286` | Add `draft` field to WorldConfig |
| Modify | `sidequest-server/sidequest/genre/loader.py:712-716` | Skip draft worlds |
| Modify | `sidequest-server/sidequest/genre/models/pack.py:77-93` | Add `extensions` field to PackMeta |
| Create | `sidequest-server/tests/cli/validate/test_pack_validator.py` | Tests for pack validator |
| Create | `sidequest-server/tests/genre/test_draft_world_skip.py` | Test draft world loader gating |
| Modify | `sidequest-content/genre_packs/*/` | Asset dir consolidation (images/ → assets/images/) |
| Modify | `sidequest-content/genre_packs/*/worlds/*/` | cultures.yaml → cultures/, legends.yaml → legends/ |
| Modify | `sidequest-content/genre_packs/*/audio/music/` | Flatten set-N/ subdirs |
| Delete | `sidequest-content/genre_packs/*/corpus/` | Merge into centralized sidequest-content/corpus/ |
| Modify | `justfile` | Add content-validate and content-validate-all recipes |

---

### Task 1: Create pack_schema.yaml

**Files:**
- Create: `sidequest-content/pack_schema.yaml`

- [ ] **Step 1: Write the schema file**

```yaml
schema_version: "1.0"

genre_pack:
  required_files:
    - pack.yaml
    - theme.yaml
    - archetypes.yaml
    - tropes.yaml
    - lore.yaml
    - visual_style.yaml
    - audio.yaml
    - rules.yaml
    - cultures.yaml
    - char_creation.yaml
    - inventory.yaml
    - lethality_policy.yaml
    - power_tiers.yaml
    - progression.yaml
    - prompts.yaml
    - axes.yaml
    - visibility_baseline.yaml
    - client_theme.css

  required_dirs:
    - audio/music
    - assets/fonts
    - assets/images/portraits
    - assets/images/poi
    - worlds

  extensions:
    magic:
      files: [magic.yaml]
    classes:
      files: [classes.yaml]
    spellbook:
      files: [spellbook.yaml]
      dirs: [spells]
    openings:
      files: [openings.yaml]
    projection:
      files: [projection.yaml]
    beat_vocabulary:
      files: [beat_vocabulary.yaml]
    archetype_constraints:
      files: [archetype_constraints.yaml]
    achievements:
      files: [achievements.yaml]
    powers:
      files: [powers.yaml]
    chassis_classes:
      files: [chassis_classes.yaml]
    calendar:
      files: [calendar.yaml]
    weather:
      files: [weather.yaml]
    history:
      files: [history.yaml]
    dogfight:
      dirs: [dogfight]
    pacing:
      files: [pacing.yaml]
    seed_tropes:
      files: [seed_tropes.yaml]
    equipment_tables:
      files: [equipment_tables.yaml]
    backstory_tables:
      files: [backstory_tables.yaml]

world:
  required_files:
    - world.yaml
    - cartography.yaml
    - history.yaml
    - lore.yaml
    - openings.yaml
    - portrait_manifest.yaml
    - tropes.yaml
    - visual_style.yaml
    - archetypes.yaml

  required_dirs:
    - cultures
    - legends
    - assets/images/portraits
    - assets/images/poi

  extensions:
    archetype_funnels:
      files: [archetype_funnels.yaml]
    npcs:
      files: [npcs.yaml]
    creatures:
      files: [creatures.yaml]
    magic:
      files: [magic.yaml]
    confrontations:
      files: [confrontations.yaml]
    encounter_tables:
      files: [encounter_tables.yaml]
    calendar:
      files: [calendar.yaml]
    demographics:
      files: [demographics.yaml]
    rooms:
      dirs: [rooms]
    cookbook:
      dirs: [cookbook]
    world_register:
      files: [world_register.yaml]
    faction_agendas:
      files: [faction_agendas.yaml]
    orbits:
      files: [orbits.yaml]
    rigs:
      files: [rigs.yaml]
    inventions:
      files: [inventions.yaml]
    items:
      files: [items.yaml]
```

- [ ] **Step 2: Commit**

```bash
cd sidequest-content
git checkout -b feat/pack-schema
git add pack_schema.yaml
git commit -m "feat: add pack_schema.yaml — canonical genre pack structure definition"
```

---

### Task 2: Add extensions field to PackMeta model

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/pack.py:77-93`
- Test: `sidequest-server/tests/genre/test_pack_meta_extensions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/genre/test_pack_meta_extensions.py
"""Verify PackMeta accepts and stores an extensions list."""

from sidequest.genre.models.pack import PackMeta


def test_pack_meta_accepts_extensions_list():
    meta = PackMeta(
        name="Test Pack",
        version="1.0.0",
        description="A test genre pack",
        min_sidequest_version="0.1.0",
        extensions=["magic", "classes"],
    )
    assert meta.extensions == ["magic", "classes"]


def test_pack_meta_extensions_defaults_empty():
    meta = PackMeta(
        name="Test Pack",
        version="1.0.0",
        description="A test genre pack",
        min_sidequest_version="0.1.0",
    )
    assert meta.extensions == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_meta_extensions.py -v`
Expected: FAIL — `PackMeta` has `extra="forbid"` and rejects `extensions` field.

- [ ] **Step 3: Add extensions field to PackMeta**

In `sidequest-server/sidequest/genre/models/pack.py`, add to the `PackMeta` class (after line 93):

```python
    extensions: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_meta_extensions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git checkout -b feat/pack-schema
git add sidequest/genre/models/pack.py tests/genre/test_pack_meta_extensions.py
git commit -m "feat: add extensions field to PackMeta model"
```

---

### Task 3: Add draft field to WorldConfig and skip in loader

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/world.py:271-286`
- Modify: `sidequest-server/sidequest/genre/loader.py:712-716`
- Test: `sidequest-server/tests/genre/test_draft_world_skip.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/genre/test_draft_world_skip.py
"""Verify that worlds with draft: true in world.yaml are skipped by the loader."""

import textwrap
from pathlib import Path

import yaml

from sidequest.genre.models.world import WorldConfig


def test_world_config_accepts_draft_field():
    config = WorldConfig(
        name="Draft World",
        description="A work in progress",
        draft=True,
    )
    assert config.draft is True


def test_world_config_draft_defaults_false():
    config = WorldConfig(
        name="Live World",
        description="A real world",
    )
    assert config.draft is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_draft_world_skip.py -v`
Expected: FAIL on `test_world_config_draft_defaults_false` — `WorldConfig` has `extra="allow"` so `draft=True` will pass through as an extra field, but `config.draft` on the default test will raise `AttributeError` since there's no explicit field.

- [ ] **Step 3: Add draft field to WorldConfig**

In `sidequest-server/sidequest/genre/models/world.py`, add to `WorldConfig` class (after line 286):

```python
    draft: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_draft_world_skip.py -v`
Expected: PASS

- [ ] **Step 5: Add extensions field to WorldConfig**

In `sidequest-server/sidequest/genre/models/world.py`, add to `WorldConfig` class (after the draft field):

```python
    extensions: list[str] = Field(default_factory=list)
```

- [ ] **Step 6: Add draft-skip logic to the loader**

In `sidequest-server/sidequest/genre/loader.py`, modify the `_load_subdirectories` call for worlds (around line 1102). The cleanest approach: add early-return logic in `_load_single_world` right after loading `config`:

```python
# In _load_single_world, after line 735 (config = _load_yaml(...)):
    if config.draft:
        return None
```

Then update the `_load_subdirectories` caller to filter `None` results. Find `_load_subdirectories` (around line 330) and modify it to skip `None` returns:

```python
# In _load_subdirectories, change the dict comprehension to filter None:
    return {
        name: result
        for name, result in (
            (subdir.name, loader(subdir)) for subdir in subdirs
        )
        if result is not None
    }
```

Also update `_load_single_world` return type annotation from `-> World` to `-> World | None`.

- [ ] **Step 7: Add loader integration test**

Append to `tests/genre/test_draft_world_skip.py`:

```python
def test_load_single_world_returns_none_for_draft(tmp_path: Path):
    """A draft world returns None from the loader instead of a World."""
    world_dir = tmp_path / "worlds" / "draft_test"
    world_dir.mkdir(parents=True)

    # Minimal world.yaml with draft: true
    (world_dir / "world.yaml").write_text(
        yaml.dump({"name": "Draft", "description": "WIP", "slug": "draft_test", "draft": True})
    )

    from sidequest.genre.loader import _load_single_world

    result = _load_single_world(world_dir, genre_tropes=[], genre_root=tmp_path)
    assert result is None
```

- [ ] **Step 8: Run all tests to verify**

Run: `cd sidequest-server && uv run pytest tests/genre/test_draft_world_skip.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 9: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/world.py sidequest/genre/loader.py tests/genre/test_draft_world_skip.py
git commit -m "feat: add draft field to WorldConfig, skip draft worlds in loader"
```

---

### Task 4: Build the pack structure validator

This is the largest task — the new `pack` subcommand for the validate CLI. It reads `pack_schema.yaml` and checks presence, extensions, and orphans.

**Files:**
- Create: `sidequest-server/sidequest/cli/validate/pack.py`
- Modify: `sidequest-server/sidequest/cli/validate/__main__.py`
- Create: `sidequest-server/tests/cli/validate/test_pack_validator.py`

- [ ] **Step 1: Write the failing test for schema loading**

```python
# tests/cli/validate/test_pack_validator.py
"""Tests for the pack structure validator."""

import textwrap
from pathlib import Path

import yaml
import pytest


def _write_yaml(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False))


def _write_text(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _minimal_pack(pack_dir: Path, extensions: list[str] | None = None) -> None:
    """Write the minimum required files for a valid genre pack."""
    required_files_yaml = [
        "pack.yaml", "theme.yaml", "archetypes.yaml", "tropes.yaml",
        "lore.yaml", "visual_style.yaml", "audio.yaml", "rules.yaml",
        "cultures.yaml", "char_creation.yaml", "inventory.yaml",
        "lethality_policy.yaml", "power_tiers.yaml", "progression.yaml",
        "prompts.yaml", "axes.yaml", "visibility_baseline.yaml",
    ]
    pack_data = {
        "name": "Test Pack", "version": "1.0.0",
        "description": "Test", "min_sidequest_version": "0.1.0",
    }
    if extensions:
        pack_data["extensions"] = extensions
    _write_yaml(pack_dir / "pack.yaml", pack_data)
    for f in required_files_yaml:
        if f != "pack.yaml":
            _write_yaml(pack_dir / f, {})
    _write_text(pack_dir / "client_theme.css", ":root {}")

    # Required dirs
    (pack_dir / "audio" / "music").mkdir(parents=True, exist_ok=True)
    (pack_dir / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    (pack_dir / "assets" / "images" / "portraits").mkdir(parents=True, exist_ok=True)
    (pack_dir / "assets" / "images" / "poi").mkdir(parents=True, exist_ok=True)
    (pack_dir / "worlds").mkdir(parents=True, exist_ok=True)


def _minimal_world(world_dir: Path, extensions: list[str] | None = None) -> None:
    """Write the minimum required files for a valid world."""
    world_data = {
        "name": "Test World", "description": "Test", "slug": world_dir.name,
    }
    if extensions:
        world_data["extensions"] = extensions
    _write_yaml(world_dir / "world.yaml", world_data)
    for f in ["cartography.yaml", "history.yaml", "lore.yaml",
              "openings.yaml", "portrait_manifest.yaml", "tropes.yaml",
              "visual_style.yaml", "archetypes.yaml"]:
        _write_yaml(world_dir / f, {})
    (world_dir / "cultures").mkdir(exist_ok=True)
    (world_dir / "legends").mkdir(exist_ok=True)
    (world_dir / "assets" / "images" / "portraits").mkdir(parents=True, exist_ok=True)
    (world_dir / "assets" / "images" / "poi").mkdir(parents=True, exist_ok=True)


class TestPackSchemaLoading:
    def test_load_schema(self, tmp_path: Path):
        from sidequest.cli.validate.pack import load_pack_schema

        schema_path = tmp_path / "pack_schema.yaml"
        _write_yaml(schema_path, {
            "schema_version": "1.0",
            "genre_pack": {
                "required_files": ["pack.yaml"],
                "required_dirs": ["worlds"],
                "extensions": {},
            },
            "world": {
                "required_files": ["world.yaml"],
                "required_dirs": ["cultures"],
                "extensions": {},
            },
        })
        schema = load_pack_schema(schema_path)
        assert schema["genre_pack"]["required_files"] == ["pack.yaml"]


class TestPresenceGate:
    def test_valid_pack_passes(self, tmp_path: Path):
        from sidequest.cli.validate.pack import validate_pack_structure

        schema_path = tmp_path / "pack_schema.yaml"
        # Copy the real schema
        _write_yaml(schema_path, yaml.safe_load(
            (Path(__file__).resolve().parents[4] / "sidequest-content" / "pack_schema.yaml")
            .read_text()
        ))

        pack_dir = tmp_path / "test_pack"
        _minimal_pack(pack_dir)
        world_dir = pack_dir / "worlds" / "test_world"
        _minimal_world(world_dir)

        errors, warnings = validate_pack_structure(pack_dir, schema_path)
        assert len(errors) == 0

    def test_missing_required_file_is_error(self, tmp_path: Path):
        from sidequest.cli.validate.pack import validate_pack_structure

        schema_path = tmp_path / "pack_schema.yaml"
        _write_yaml(schema_path, yaml.safe_load(
            (Path(__file__).resolve().parents[4] / "sidequest-content" / "pack_schema.yaml")
            .read_text()
        ))

        pack_dir = tmp_path / "test_pack"
        _minimal_pack(pack_dir)
        (pack_dir / "theme.yaml").unlink()  # Remove a required file
        world_dir = pack_dir / "worlds" / "test_world"
        _minimal_world(world_dir)

        errors, warnings = validate_pack_structure(pack_dir, schema_path)
        assert any("theme.yaml" in e for e in errors)

    def test_declared_extension_missing_is_error(self, tmp_path: Path):
        from sidequest.cli.validate.pack import validate_pack_structure

        schema_path = tmp_path / "pack_schema.yaml"
        _write_yaml(schema_path, yaml.safe_load(
            (Path(__file__).resolve().parents[4] / "sidequest-content" / "pack_schema.yaml")
            .read_text()
        ))

        pack_dir = tmp_path / "test_pack"
        _minimal_pack(pack_dir, extensions=["magic"])
        # Don't create magic.yaml — declared but missing
        world_dir = pack_dir / "worlds" / "test_world"
        _minimal_world(world_dir)

        errors, warnings = validate_pack_structure(pack_dir, schema_path)
        assert any("magic.yaml" in e for e in errors)

    def test_orphan_file_is_warning(self, tmp_path: Path):
        from sidequest.cli.validate.pack import validate_pack_structure

        schema_path = tmp_path / "pack_schema.yaml"
        _write_yaml(schema_path, yaml.safe_load(
            (Path(__file__).resolve().parents[4] / "sidequest-content" / "pack_schema.yaml")
            .read_text()
        ))

        pack_dir = tmp_path / "test_pack"
        _minimal_pack(pack_dir)
        _write_yaml(pack_dir / "mystery_file.yaml", {"surprise": True})
        world_dir = pack_dir / "worlds" / "test_world"
        _minimal_world(world_dir)

        errors, warnings = validate_pack_structure(pack_dir, schema_path)
        assert any("mystery_file.yaml" in w for w in warnings)

    def test_draft_world_warnings_not_errors(self, tmp_path: Path):
        from sidequest.cli.validate.pack import validate_pack_structure

        schema_path = tmp_path / "pack_schema.yaml"
        _write_yaml(schema_path, yaml.safe_load(
            (Path(__file__).resolve().parents[4] / "sidequest-content" / "pack_schema.yaml")
            .read_text()
        ))

        pack_dir = tmp_path / "test_pack"
        _minimal_pack(pack_dir)
        # Create a draft world with missing files
        draft_dir = pack_dir / "worlds" / "draft_world"
        draft_dir.mkdir(parents=True)
        _write_yaml(draft_dir / "world.yaml", {
            "name": "Draft", "description": "WIP", "slug": "draft_world", "draft": True,
        })

        errors, warnings = validate_pack_structure(pack_dir, schema_path)
        # Draft world missing files → warnings, not errors
        assert len(errors) == 0
        assert any("draft_world" in w for w in warnings)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/cli/validate/test_pack_validator.py -v`
Expected: FAIL — `sidequest.cli.validate.pack` does not exist.

- [ ] **Step 3: Implement pack.py validator**

Create `sidequest-server/sidequest/cli/validate/pack.py`:

```python
"""Pack structure validator — checks file presence, extensions, and orphans.

Reads pack_schema.yaml and validates a genre pack directory against it.
Does not boot the game server or run Pydantic model validation (that's
the schema gate — a separate concern layered on top of this).
"""

from __future__ import annotations

from pathlib import Path

import click
import yaml


def load_pack_schema(schema_path: Path) -> dict:
    with schema_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _check_required_files(
    directory: Path,
    required: list[str],
    label: str,
) -> list[str]:
    errors = []
    for fname in required:
        if not (directory / fname).exists():
            errors.append(f"{label}: missing required file: {fname}")
    return errors


def _check_required_dirs(
    directory: Path,
    required: list[str],
    label: str,
) -> list[str]:
    errors = []
    for dname in required:
        target = directory / dname
        if not target.exists() or not target.is_dir():
            errors.append(f"{label}: missing required directory: {dname}")
    return errors


def _resolve_extension_paths(
    extensions_declared: list[str],
    extensions_schema: dict,
) -> tuple[set[str], set[str]]:
    expected_files: set[str] = set()
    expected_dirs: set[str] = set()
    for ext_name in extensions_declared:
        ext_def = extensions_schema.get(ext_name, {})
        for f in ext_def.get("files", []):
            expected_files.add(f)
        for d in ext_def.get("dirs", []):
            expected_dirs.add(d)
    return expected_files, expected_dirs


def _check_extensions(
    directory: Path,
    extensions_declared: list[str],
    extensions_schema: dict,
    label: str,
) -> list[str]:
    errors = []
    for ext_name in extensions_declared:
        if ext_name not in extensions_schema:
            errors.append(f"{label}: unknown extension declared: {ext_name}")
            continue
        ext_def = extensions_schema[ext_name]
        for f in ext_def.get("files", []):
            if not (directory / f).exists():
                errors.append(
                    f"{label}: extension '{ext_name}' declared but missing: {f}"
                )
        for d in ext_def.get("dirs", []):
            target = directory / d
            if not target.exists() or not target.is_dir():
                errors.append(
                    f"{label}: extension '{ext_name}' declared but missing directory: {d}"
                )
    return errors


def _check_orphans(
    directory: Path,
    required_files: list[str],
    required_dirs: list[str],
    extension_files: set[str],
    extension_dirs: set[str],
    genre_required_files: list[str] | None,
    genre_extension_files: set[str] | None,
    label: str,
) -> list[str]:
    warnings = []
    known_files = set(required_files) | extension_files
    known_dirs = {d.split("/")[0] for d in required_dirs} | extension_dirs

    # For world-level orphan detection, genre-level files are valid overrides
    if genre_required_files is not None:
        known_files |= set(genre_required_files)
    if genre_extension_files is not None:
        known_files |= genre_extension_files

    for item in sorted(directory.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_file() and item.name not in known_files:
            warnings.append(f"{label}: orphan file: {item.name}")
        elif item.is_dir() and item.name not in known_dirs:
            warnings.append(f"{label}: orphan directory: {item.name}")
    return warnings


def _validate_world(
    world_dir: Path,
    world_schema: dict,
    genre_schema: dict,
    genre_ext_files: set[str],
    genre_ext_dirs: set[str],
    genre_extensions_declared: list[str],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    label = f"world {world_dir.name}"

    world_yaml_path = world_dir / "world.yaml"
    if not world_yaml_path.exists():
        errors.append(f"{label}: missing world.yaml")
        return errors, warnings

    with world_yaml_path.open("r", encoding="utf-8") as f:
        world_data = yaml.safe_load(f) or {}

    is_draft = world_data.get("draft", False)
    extensions_declared = world_data.get("extensions", [])

    ext_files, ext_dirs = _resolve_extension_paths(
        extensions_declared, world_schema.get("extensions", {})
    )

    # Genre-level known files for override detection
    genre_known_files = genre_schema.get("required_files", [])
    genre_all_ext_files = set()
    for ext_name in genre_extensions_declared:
        ext_def = genre_schema.get("extensions", {}).get(ext_name, {})
        for f in ext_def.get("files", []):
            genre_all_ext_files.add(f)

    file_errors = _check_required_files(
        world_dir, world_schema["required_files"], label
    )
    dir_errors = _check_required_dirs(
        world_dir, world_schema["required_dirs"], label
    )
    ext_errors = _check_extensions(
        world_dir, extensions_declared,
        world_schema.get("extensions", {}), label,
    )
    orphan_warnings = _check_orphans(
        world_dir,
        world_schema["required_files"],
        world_schema["required_dirs"],
        ext_files, ext_dirs,
        genre_known_files, genre_all_ext_files,
        label,
    )

    if is_draft:
        # Draft worlds: file/dir/ext problems are warnings, not errors
        warnings.extend(file_errors)
        warnings.extend(dir_errors)
        warnings.extend(ext_errors)
        warnings.extend(f"(draft) {w}" for w in orphan_warnings)
    else:
        errors.extend(file_errors)
        errors.extend(dir_errors)
        errors.extend(ext_errors)
        warnings.extend(orphan_warnings)

    return errors, warnings


def validate_pack_structure(
    pack_dir: Path,
    schema_path: Path,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    label = pack_dir.name

    schema = load_pack_schema(schema_path)
    genre_schema = schema["genre_pack"]
    world_schema = schema["world"]

    # Read pack.yaml for extensions
    pack_yaml_path = pack_dir / "pack.yaml"
    if not pack_yaml_path.exists():
        errors.append(f"{label}: missing pack.yaml — not a valid genre pack")
        return errors, warnings

    with pack_yaml_path.open("r", encoding="utf-8") as f:
        pack_data = yaml.safe_load(f) or {}

    extensions_declared = pack_data.get("extensions", [])
    ext_files, ext_dirs = _resolve_extension_paths(
        extensions_declared, genre_schema.get("extensions", {})
    )

    # Genre-level checks
    errors.extend(_check_required_files(pack_dir, genre_schema["required_files"], label))
    errors.extend(_check_required_dirs(pack_dir, genre_schema["required_dirs"], label))
    errors.extend(_check_extensions(
        pack_dir, extensions_declared,
        genre_schema.get("extensions", {}), label,
    ))
    warnings.extend(_check_orphans(
        pack_dir,
        genre_schema["required_files"],
        genre_schema["required_dirs"],
        ext_files, ext_dirs,
        None, None,
        label,
    ))

    # World-level checks
    worlds_dir = pack_dir / "worlds"
    if worlds_dir.is_dir():
        for world_dir in sorted(worlds_dir.iterdir()):
            if not world_dir.is_dir() or world_dir.name.startswith("."):
                continue
            w_errors, w_warnings = _validate_world(
                world_dir, world_schema, genre_schema,
                ext_files, ext_dirs, extensions_declared,
            )
            errors.extend(w_errors)
            warnings.extend(w_warnings)

    return errors, warnings


def _format_report(
    pack_name: str,
    errors: list[str],
    warnings: list[str],
) -> str:
    status = "FAIL" if errors else "PASS"
    counts = []
    if errors:
        counts.append(f"{len(errors)} error{'s' if len(errors) != 1 else ''}")
    if warnings:
        counts.append(f"{len(warnings)} warning{'s' if len(warnings) != 1 else ''}")
    count_str = f" ({', '.join(counts)})" if counts else ""

    dots = "." * max(1, 50 - len(pack_name))
    lines = [f"{pack_name} {dots} {status}{count_str}"]
    for e in errors:
        lines.append(f"  ✗ {e}")
    for w in warnings:
        lines.append(f"  ⚠ {w}")
    return "\n".join(lines)


@click.command(name="pack")
@click.argument("pack_dir")
@click.option(
    "--schema",
    "schema_path",
    default=None,
    help="Path to pack_schema.yaml (defaults to content root)",
)
@click.option("--verbose", is_flag=True, help="Show warnings even on pass")
def main(pack_dir: str, schema_path: str | None, verbose: bool) -> None:
    """Validate genre pack file structure against pack_schema.yaml."""
    pack_path = Path(pack_dir).resolve()

    if schema_path is None:
        # Walk up to find pack_schema.yaml at content root
        candidate = pack_path.parent.parent / "pack_schema.yaml"
        if not candidate.exists():
            candidate = pack_path.parent / "pack_schema.yaml"
        if not candidate.exists():
            click.echo("ERROR: Cannot find pack_schema.yaml. Use --schema to specify.", err=True)
            raise SystemExit(1)
        resolved_schema = candidate
    else:
        resolved_schema = Path(schema_path).resolve()

    from sidequest.cli.validate.common import packs_in

    packs = packs_in(pack_path)
    if not packs:
        click.echo(f"No genre packs found in {pack_path}", err=True)
        raise SystemExit(1)

    exit_code = 0
    for pack in packs:
        errors, warnings = validate_pack_structure(pack, resolved_schema)
        if errors:
            exit_code = 1
        if errors or warnings or verbose:
            click.echo(_format_report(pack.name, errors, warnings))

    raise SystemExit(exit_code)
```

- [ ] **Step 4: Register in __main__.py**

In `sidequest-server/sidequest/cli/validate/__main__.py`, add the import and registration:

After line 21, add:
```python
from sidequest.cli.validate.pack import main as pack_main
```

After line 31, add:
```python
cli.add_command(pack_main, name="pack")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/cli/validate/test_pack_validator.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 6: Run full test suite to check for regressions**

Run: `cd sidequest-server && uv run pytest -v`
Expected: No new failures

- [ ] **Step 7: Commit**

```bash
cd sidequest-server
git add sidequest/cli/validate/pack.py sidequest/cli/validate/__main__.py tests/cli/validate/test_pack_validator.py
git commit -m "feat: add pack structure validator (presence gate + extension checking)"
```

---

### Task 5: Add extensions to all pack.yaml files

**Files:**
- Modify: `sidequest-content/genre_packs/*/pack.yaml` (10 files)

Based on the audit, each pack declares the extensions it actually uses. These are determined by which optional files currently exist in each pack.

- [ ] **Step 1: Add extensions to caverns_and_claudes/pack.yaml**

Append to the end of the file:
```yaml
extensions:
  - magic
  - classes
  - spellbook
  - projection
  - beat_vocabulary
  - archetype_constraints
  - backstory_tables
  - equipment_tables
```

- [ ] **Step 2: Add extensions to elemental_harmony/pack.yaml**

```yaml
extensions:
  - projection
  - archetype_constraints
  - achievements
```

- [ ] **Step 3: Add extensions to heavy_metal/pack.yaml**

```yaml
extensions:
  - beat_vocabulary
  - archetype_constraints
  - openings
  - achievements
```

- [ ] **Step 4: Add extensions to mutant_wasteland/pack.yaml**

```yaml
extensions:
  - magic
  - pacing
  - achievements
```

- [ ] **Step 5: Add extensions to neon_dystopia/pack.yaml**

```yaml
extensions:
  - archetype_constraints
  - openings
  - achievements
```

- [ ] **Step 6: Add extensions to pulp_noir/pack.yaml**

```yaml
extensions:
  - archetype_constraints
  - openings
  - achievements
```

- [ ] **Step 7: Add extensions to road_warrior/pack.yaml**

```yaml
extensions:
  - magic
  - classes
  - projection
  - beat_vocabulary
  - powers
  - achievements
```

- [ ] **Step 8: Add extensions to space_opera/pack.yaml**

```yaml
extensions:
  - magic
  - projection
  - archetype_constraints
  - chassis_classes
  - achievements
```

- [ ] **Step 9: Add extensions to spaghetti_western/pack.yaml**

```yaml
extensions:
  - magic
  - projection
  - calendar
  - history
  - openings
  - achievements
```

- [ ] **Step 10: Add extensions to tea_and_murder/pack.yaml**

```yaml
extensions:
  - magic
  - classes
  - beat_vocabulary
  - calendar
  - weather
  - history
  - seed_tropes
  - equipment_tables
  - achievements
```

- [ ] **Step 11: Commit**

```bash
cd sidequest-content
git add genre_packs/*/pack.yaml
git commit -m "feat: declare extensions in all pack.yaml files"
```

---

### Task 6: Add extensions to all world.yaml files

**Files:**
- Modify: `sidequest-content/genre_packs/*/worlds/*/world.yaml` (14 files)

Based on the audit of which optional files exist per world.

- [ ] **Step 1: Add extensions to beneath_sunden/world.yaml**

```yaml
extensions:
  - creatures
  - rooms
  - cookbook
  - world_register
```

- [ ] **Step 2: Add extensions to coyote_star/world.yaml**

```yaml
extensions:
  - archetype_funnels
  - npcs
  - magic
  - confrontations
  - orbits
  - rigs
```

- [ ] **Step 3: Add extensions to glenross/world.yaml**

```yaml
extensions:
  - npcs
  - calendar
  - demographics
```

- [ ] **Step 4: Add extensions to long_foundry/world.yaml**

```yaml
extensions:
  - archetype_funnels
  - magic
```

- [ ] **Step 5: Add extensions to evropi/world.yaml (heavy_metal)**

Check what's actually in this world dir and add matching extensions. If it only has the required files, add empty extensions: `extensions: []`

- [ ] **Step 6: Add extensions to flickering_reach/world.yaml**

```yaml
extensions:
  - creatures
  - encounter_tables
```

Note: `magic.yaml.draft` is not a valid extension file — ignore it (it's a draft artifact).

- [ ] **Step 7: Add extensions to burning_peace/world.yaml**

```yaml
extensions:
  - archetype_funnels
```

- [ ] **Step 8: Add extensions to shattered_accord/world.yaml**

```yaml
extensions:
  - archetype_funnels
  - faction_agendas
```

- [ ] **Step 9: Add extensions to the_circuit/world.yaml**

```yaml
extensions:
  - npcs
```

- [ ] **Step 10: Add extensions to the_real_mccoy/world.yaml**

```yaml
extensions:
  - inventions
```

Note: `audio.yaml` and `char_creation.yaml` at world level are overrides, not extensions.

- [ ] **Step 11: Add empty extensions to remaining worlds**

For `dust_and_lead`, `franchise_nations`, `annees_folles`: these have only required files. Add `extensions: []` to each world.yaml.

- [ ] **Step 12: Commit**

```bash
cd sidequest-content
git add genre_packs/*/worlds/*/world.yaml
git commit -m "feat: declare extensions in all world.yaml files"
```

---

### Task 7: Add missing client_theme.css to heavy_metal

**Files:**
- Create: `sidequest-content/genre_packs/heavy_metal/client_theme.css`

- [ ] **Step 1: Create a minimal client_theme.css**

Check what other packs' CSS looks like for structure:
```bash
head -20 sidequest-content/genre_packs/caverns_and_claudes/client_theme.css
```

Create `heavy_metal/client_theme.css` following the same pattern with appropriate heavy metal theme values (dark, aggressive, metallic).

- [ ] **Step 2: Commit**

```bash
cd sidequest-content
git add genre_packs/heavy_metal/client_theme.css
git commit -m "feat: add client_theme.css to heavy_metal (schema-required)"
```

---

### Task 8: Consolidate asset directories

Move `images/` contents into `assets/images/` at genre level. Create missing `assets/` subdirs.

**Files:**
- Modify: `sidequest-content/genre_packs/{caverns_and_claudes,elemental_harmony,road_warrior,spaghetti_western}/`

- [ ] **Step 1: Move caverns_and_claudes images**

```bash
cd sidequest-content
mkdir -p genre_packs/caverns_and_claudes/assets/images
# creatures/ is a special case — check if it belongs under images or elsewhere
mv genre_packs/caverns_and_claudes/images/poi genre_packs/caverns_and_claudes/assets/images/poi
mv genre_packs/caverns_and_claudes/images/creatures genre_packs/caverns_and_claudes/assets/images/creatures
rmdir genre_packs/caverns_and_claudes/images 2>/dev/null || true
```

- [ ] **Step 2: Move road_warrior images**

```bash
mkdir -p genre_packs/road_warrior/assets/images
mv genre_packs/road_warrior/images/poi genre_packs/road_warrior/assets/images/poi
mv genre_packs/road_warrior/images/portraits genre_packs/road_warrior/assets/images/portraits
rmdir genre_packs/road_warrior/images 2>/dev/null || true
```

- [ ] **Step 3: Move spaghetti_western images**

```bash
mkdir -p genre_packs/spaghetti_western/assets/images
mv genre_packs/spaghetti_western/images/encounters genre_packs/spaghetti_western/assets/images/encounters
rmdir genre_packs/spaghetti_western/images 2>/dev/null || true
```

- [ ] **Step 4: Clean up empty images dirs**

```bash
# elemental_harmony/images and heavy_metal/images and space_opera/images are empty (just .DS_Store)
rm -rf genre_packs/elemental_harmony/images
rm -rf genre_packs/heavy_metal/images
rm -rf genre_packs/space_opera/images
```

- [ ] **Step 5: Create missing assets subdirs for all packs**

```bash
for pack in genre_packs/*/; do
    mkdir -p "$pack/assets/fonts"
    mkdir -p "$pack/assets/images/portraits"
    mkdir -p "$pack/assets/images/poi"
done
```

- [ ] **Step 6: Create missing world-level assets subdirs**

```bash
for world in genre_packs/*/worlds/*/; do
    mkdir -p "$world/assets/images/portraits"
    mkdir -p "$world/assets/images/poi"
done
```

Note: Git doesn't track empty directories. Add `.gitkeep` files to empty required dirs:
```bash
for dir in genre_packs/*/assets/fonts genre_packs/*/assets/images/portraits genre_packs/*/assets/images/poi; do
    if [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        touch "$dir/.gitkeep"
    fi
done
for dir in genre_packs/*/worlds/*/assets/images/portraits genre_packs/*/worlds/*/assets/images/poi; do
    if [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        touch "$dir/.gitkeep"
    fi
done
```

- [ ] **Step 7: Commit**

```bash
cd sidequest-content
git add -A genre_packs/*/assets genre_packs/*/worlds/*/assets
git add -A genre_packs/*/images  # captures deletions
git commit -m "feat: consolidate images/ into assets/images/ across all packs"
```

---

### Task 9: Migrate corpus to centralized location

**Files:**
- Modify: `sidequest-content/corpus/`
- Delete: `sidequest-content/genre_packs/*/corpus/`

- [ ] **Step 1: Audit what's already in sidequest-content/corpus/**

```bash
ls sidequest-content/corpus/
```

- [ ] **Step 2: Merge per-pack corpus files**

```bash
cd sidequest-content
# Heavy metal has 13 files — the most populated
cp -n genre_packs/heavy_metal/corpus/*.txt corpus/ 2>/dev/null || true
cp -n genre_packs/spaghetti_western/corpus/*.txt corpus/ 2>/dev/null || true
cp -n genre_packs/tea_and_murder/corpus/*.txt corpus/ 2>/dev/null || true
cp -n genre_packs/caverns_and_claudes/corpus/*.txt corpus/ 2>/dev/null || true
cp -n genre_packs/road_warrior/corpus/*.txt corpus/ 2>/dev/null || true
# pulp_noir names/ also migrates
cp -n genre_packs/pulp_noir/names/*.txt corpus/ 2>/dev/null || true
```

Use `cp -n` (no clobber) to avoid overwriting existing centralized files. After copy, diff any files that existed in both locations to verify they're identical or decide which to keep.

- [ ] **Step 3: Remove per-pack corpus and names directories**

```bash
cd sidequest-content
rm -rf genre_packs/*/corpus
rm -rf genre_packs/pulp_noir/names
```

- [ ] **Step 4: Verify the server corpus loader still finds files**

The corpus loader in `sidequest-server/sidequest/corpus/` should already look at `sidequest-content/corpus/`. Verify:
```bash
grep -r "corpus" sidequest-server/sidequest/corpus/ | head -20
```

- [ ] **Step 5: Commit**

```bash
cd sidequest-content
git add corpus/ genre_packs/*/corpus genre_packs/pulp_noir/names
git commit -m "feat: centralize all corpus files into sidequest-content/corpus/"
```

---

### Task 10: Flatten audio set subdirectories

**Files:**
- Modify: `sidequest-content/genre_packs/{road_warrior,elemental_harmony,space_opera,mutant_wasteland}/audio/music/`

- [ ] **Step 1: Flatten road_warrior audio sets**

```bash
cd sidequest-content/genre_packs/road_warrior/audio/music

# set-1 files: rename to include _set1 suffix before _input_params
for f in set-1/*_input_params.json; do
    base=$(basename "$f" _input_params.json)
    mv "$f" "${base}_alt1_input_params.json"
done

# set-2 files: rename to include _alt2 suffix
for f in set-2/*_input_params.json; do
    base=$(basename "$f" _input_params.json)
    mv "$f" "${base}_alt2_input_params.json"
done

# themed/ files: already have distinct names, move up
mv themed/*_input_params.json .

rmdir set-1 set-2 themed 2>/dev/null || true
```

- [ ] **Step 2: Repeat for elemental_harmony, space_opera, mutant_wasteland**

Same pattern for each pack's set subdirectories. Adjust the alt numbering per set.

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add -A genre_packs/*/audio/music/
git commit -m "feat: flatten audio set-N/ subdirs into music/ with alt suffixes"
```

---

### Task 11: Convert cultures.yaml and legends.yaml to directories

**Files:**
- Modify: All world directories that have single-file cultures.yaml or legends.yaml

- [ ] **Step 1: Convert cultures.yaml to cultures/ for each world**

For each world that has `cultures.yaml` as a single file (most worlds):

```bash
cd sidequest-content
for world in genre_packs/*/worlds/*/; do
    if [ -f "${world}cultures.yaml" ] && [ ! -d "${world}cultures" ]; then
        mkdir -p "${world}cultures"
        # Split the YAML list into per-culture files
        # This requires a script — use Python to read the list and write individual files
    fi
done
```

Write a helper script `tools/split_cultures.py`:
```python
"""Split cultures.yaml (YAML list) into cultures/{culture_name}.yaml files."""
import sys
from pathlib import Path
import yaml

world_dir = Path(sys.argv[1])
src = world_dir / "cultures.yaml"
dst = world_dir / "cultures"

with src.open() as f:
    data = yaml.safe_load(f)

if not isinstance(data, list):
    print(f"SKIP {src}: not a list")
    sys.exit(0)

dst.mkdir(exist_ok=True)
for culture in data:
    name = culture.get("name", culture.get("id", "unknown"))
    slug = name.lower().replace(" ", "_").replace("-", "_")
    out = dst / f"{slug}.yaml"
    with out.open("w") as f:
        yaml.dump(culture, f, default_flow_style=False, allow_unicode=True)
    print(f"  wrote {out}")

src.unlink()
print(f"  removed {src}")
```

Run for each world:
```bash
for world in genre_packs/*/worlds/*/; do
    if [ -f "${world}cultures.yaml" ] && [ ! -d "${world}cultures" ]; then
        python tools/split_cultures.py "$world"
    fi
done
```

- [ ] **Step 2: Convert legends.yaml to legends/ for each world**

Same approach — write `tools/split_legends.py` with similar logic (handling both list and map-with-key shapes per `_load_legends_flexible` in the loader).

Run for each world:
```bash
for world in genre_packs/*/worlds/*/; do
    if [ -f "${world}legends.yaml" ] && [ ! -d "${world}legends" ]; then
        python tools/split_legends.py "$world"
    fi
done
```

- [ ] **Step 3: Handle worlds that already have cultures/ directory**

`coyote_star` and `glenross` already have `cultures/` directories. They may also have a `cultures.yaml` at the same level. If so, verify the directory contents are canonical and remove the single file.

- [ ] **Step 4: Update the server world loader to read from directories**

In `sidequest-server/sidequest/genre/loader.py`, modify `_load_single_world` (around lines 740-743) to load cultures from a directory:

```python
    # Load cultures — directory (per-file) or single file (legacy)
    cultures_dir = world_path / "cultures"
    cultures: list[Culture] = []
    if cultures_dir.is_dir():
        for culture_file in sorted(cultures_dir.glob("*.yaml")):
            raw = _load_yaml_raw(culture_file)
            if isinstance(raw, dict):
                cultures.append(Culture.model_validate(raw))
    else:
        cultures_raw = _load_yaml_raw_optional(world_path / "cultures.yaml")
        cultures = (
            [Culture.model_validate(c) for c in cultures_raw]
            if isinstance(cultures_raw, list) else []
        )
```

Same pattern for legends (around line 746).

- [ ] **Step 5: Add test for directory-based culture loading**

```python
# tests/genre/test_world_cultures_dir.py
"""Verify the world loader reads cultures from a directory of per-culture files."""

from pathlib import Path

import yaml

from sidequest.genre.models.culture import Culture


def _write_yaml(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))


def test_load_cultures_from_directory(tmp_path: Path):
    """When cultures/ is a directory, loader reads each .yaml file as a Culture."""
    world_dir = tmp_path / "worlds" / "test_world"
    cultures_dir = world_dir / "cultures"
    cultures_dir.mkdir(parents=True)

    _write_yaml(cultures_dir / "highland_scots.yaml", {
        "name": "Highland Scots",
        "description": "Hardy folk of the northern hills",
    })
    _write_yaml(cultures_dir / "english_gentry.yaml", {
        "name": "English Gentry",
        "description": "The landed class",
    })

    # Simulate what the loader does
    cultures: list[Culture] = []
    for culture_file in sorted(cultures_dir.glob("*.yaml")):
        with culture_file.open() as f:
            raw = yaml.safe_load(f)
        if isinstance(raw, dict):
            cultures.append(Culture.model_validate(raw))

    assert len(cultures) == 2
    assert cultures[0].name == "English Gentry"
    assert cultures[1].name == "Highland Scots"
```

- [ ] **Step 6: Commit**

```bash
cd sidequest-content
git add -A genre_packs/*/worlds/*/cultures genre_packs/*/worlds/*/legends
git add tools/split_cultures.py tools/split_legends.py
git commit -m "feat: convert cultures.yaml and legends.yaml to per-entry directories"
```

```bash
cd sidequest-server
git add sidequest/genre/loader.py tests/genre/
git commit -m "feat: support cultures/ and legends/ directories in world loader"
```

---

### Task 12: Clean up workshopping directory

**Files:**
- Delete: `sidequest-content/genre_workshopping/caverns_sunden/`
- Move: workshopping alternate-worlds into parent packs as draft worlds

- [ ] **Step 1: Delete deprecated caverns_sunden**

```bash
cd sidequest-content
rm -rf genre_workshopping/caverns_sunden
```

- [ ] **Step 2: Move alternate worlds into parent packs as draft worlds**

```bash
# elemental_harmony workshopping world → draft world in live pack
mv genre_workshopping/elemental_harmony/worlds/burning_peace genre_packs/elemental_harmony/worlds/burning_peace_draft
# Add draft: true to its world.yaml

# space_opera workshopping world
mv genre_workshopping/space_opera/worlds/aureate_span genre_packs/space_opera/worlds/aureate_span
# Add draft: true to its world.yaml

# tea_and_murder workshopping world
mv genre_workshopping/tea_and_murder/worlds/blackthorn_moor genre_packs/tea_and_murder/worlds/blackthorn_moor
# Add draft: true to its world.yaml
```

Wait — `burning_peace` already exists as a live world in elemental_harmony. The workshopping version may be an earlier draft. Check before moving:
```bash
diff -rq genre_workshopping/elemental_harmony/worlds/burning_peace genre_packs/elemental_harmony/worlds/burning_peace
```

If they're different, the workshopping version is stale — delete it rather than creating a naming conflict. If the workshopping one is newer, it should have replaced the live one already.

For `aureate_span` and `blackthorn_moor`, these don't exist in the live packs, so the move is safe. Add `draft: true` to each world.yaml after moving.

- [ ] **Step 3: Clean up empty workshopping pack shells**

After moving worlds out, remove the empty workshopping pack directories (those that only held alternate worlds, not full packs):
```bash
rm -rf genre_workshopping/elemental_harmony
rm -rf genre_workshopping/space_opera
rm -rf genre_workshopping/tea_and_murder
```

`low_fantasy` stays — it's a real in-progress pack.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add -A genre_workshopping/ genre_packs/*/worlds/
git commit -m "feat: migrate workshopping alternate-worlds as draft worlds, delete deprecated caverns_sunden"
```

---

### Task 13: Add justfile recipes

**Files:**
- Modify: `justfile`

- [ ] **Step 1: Add content-validate and content-validate-all recipes**

Add to the orchestrator `justfile`:

```just
# Content validation
content-validate genre:
    cd sidequest-server && uv run python -m sidequest.cli.validate pack {{root}}/sidequest-content/genre_packs/{{genre}}

content-validate-all:
    cd sidequest-server && uv run python -m sidequest.cli.validate pack {{root}}/sidequest-content/genre_packs
```

- [ ] **Step 2: Test the recipe**

```bash
just content-validate caverns_and_claudes
just content-validate-all
```

- [ ] **Step 3: Commit**

```bash
git add justfile
git commit -m "feat: add content-validate and content-validate-all justfile recipes"
```

---

### Task 14: Clean up dead artifacts

**Files:**
- Delete: `sidequest-content/genre_packs/heavy_metal/_drafts/`
- Delete: `sidequest-content/genre_packs/caverns_and_claudes/themes/`
- Delete: `sidequest-content/genre_packs/spaghetti_western/draw_things_preset.json`

- [ ] **Step 1: Audit each artifact**

```bash
# Check if themes/ is referenced anywhere in the codebase
grep -r "themes/" sidequest-server/ sidequest-content/genre_packs/caverns_and_claudes/ --include="*.py" --include="*.yaml"

# Check if _drafts/ contents have been promoted
diff sidequest-content/genre_packs/heavy_metal/_drafts/magic.yaml sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/magic.yaml 2>/dev/null

# Check if draw_things_preset.json is loaded anywhere
grep -r "draw_things_preset" sidequest-server/ sidequest-daemon/
```

- [ ] **Step 2: Remove confirmed dead artifacts**

Only delete what the audit confirms is unused. For each:
```bash
cd sidequest-content
rm -rf genre_packs/heavy_metal/_drafts
rm -rf genre_packs/caverns_and_claudes/themes  # if unused
rm genre_packs/spaghetti_western/draw_things_preset.json  # if unused
```

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add -A
git commit -m "chore: remove dead content artifacts (drafts, unused themes, stale presets)"
```

---

### Task 15: End-to-end validation run

- [ ] **Step 1: Run validate-all and fix remaining issues**

```bash
just content-validate-all
```

Review the output. Any errors indicate migration gaps (missed extensions, missing required dirs after consolidation, orphan files that need extension declarations). Fix each one.

- [ ] **Step 2: Run the game server to verify packs still load**

```bash
just server
# In another terminal:
curl http://localhost:8765/genres
```

Verify all 10 packs load successfully. Check logs for `GenreLoadError`.

- [ ] **Step 3: Run server tests**

```bash
just server-test
```

No new failures.

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve remaining validation gaps from filesystem migration"
```
