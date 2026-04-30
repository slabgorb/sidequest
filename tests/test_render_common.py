"""Tests for scripts.render_common protocol surface.

Task 4.1 covers the send_render signature widening from singleton
(lora_path/lora_scale) to arrays (lora_paths/lora_scales). The old
singleton parameters are removed outright — the daemon is a sidecar
with a small surface; a compat shim would outlast the cutover.

Task 4.3 covers compose_lora_stack — the pure resolver that merges
genre+world LoRA blocks into the effective per-render stack. Lives
in render_common per Architect correction #5 (not a separate module).
"""
from __future__ import annotations

import inspect

import pytest

from pathlib import Path

import yaml

from scripts.render_common import (
    ComposeError,
    compose_lora_stack,
    load_visual_style,
    resolve_lora_args,
    send_render,
)


def test_send_render_accepts_lora_lists() -> None:
    sig = inspect.signature(send_render)
    assert "lora_paths" in sig.parameters
    assert "lora_scales" in sig.parameters


def test_send_render_drops_legacy_singleton_params() -> None:
    """lora_path / lora_scale were removed — clean cutover per ADR-083."""
    sig = inspect.signature(send_render)
    assert "lora_path" not in sig.parameters
    assert "lora_scale" not in sig.parameters


def test_lora_paths_default_is_none() -> None:
    """Absent-LoRA is the common case; default should be optional."""
    sig = inspect.signature(send_render)
    assert sig.parameters["lora_paths"].default is None
    assert sig.parameters["lora_scales"].default is None


# ─── Task 4.3: compose_lora_stack ─────────────────────────────────────


GENRE = {
    "loras": [
        {"name": "sw_landscape", "file": "p1.safetensors", "scale": 0.8,
         "applies_to": ["landscape", "scene"], "trigger": "sw_landscape"},
        {"name": "sw_portrait", "file": "p2.safetensors", "scale": 0.8,
         "applies_to": ["portrait"], "trigger": "sw_portrait"},
    ]
}


def test_no_world_overrides_inherits_genre() -> None:
    """Empty world style → genre LoRAs flow through, filtered by tier."""
    resolved = compose_lora_stack(GENRE, {}, tier="landscape")
    assert [e["name"] for e in resolved] == ["sw_landscape"]


def test_world_exclude_drops_inherited() -> None:
    """world.loras.exclude removes a genre entry by name before tier filter."""
    world = {"loras": {"exclude": ["sw_landscape"]}}
    resolved = compose_lora_stack(GENRE, world, tier="landscape")
    assert resolved == []


def test_world_add_appends_after_genre() -> None:
    """world.loras.add appends new entries; order is genre-first then add-order."""
    world = {
        "loras": {
            "add": [
                {"name": "mccoy_landscape", "file": "p3.safetensors", "scale": 0.85,
                 "applies_to": ["landscape"], "trigger": "mccoy_landscape"}
            ]
        }
    }
    resolved = compose_lora_stack(GENRE, world, tier="landscape")
    assert [e["name"] for e in resolved] == ["sw_landscape", "mccoy_landscape"]


def test_tier_filter_skips_non_matching_applies_to() -> None:
    """An entry with applies_to=[portrait] does not fire on a landscape render."""
    resolved = compose_lora_stack(GENRE, {}, tier="portrait")
    assert [e["name"] for e in resolved] == ["sw_portrait"]


def test_world_add_with_inherited_name_raises() -> None:
    """Reusing a genre name in world.add without exclude is ambiguous → fail loud."""
    world = {
        "loras": {
            "add": [
                {"name": "sw_landscape", "file": "dup.safetensors", "scale": 0.5,
                 "applies_to": ["landscape"]}
            ]
        }
    }
    with pytest.raises(ComposeError, match="duplicate"):
        compose_lora_stack(GENRE, world, tier="landscape")


def test_empty_applies_to_fails_validation() -> None:
    """An entry that fires on no tier is always misconfiguration → fail loud."""
    bad_genre = {
        "loras": [
            {"name": "x", "file": "x.safetensors", "scale": 1.0, "applies_to": []},
        ]
    }
    with pytest.raises(ComposeError, match="applies_to"):
        compose_lora_stack(bad_genre, {}, tier="landscape")


def test_legacy_list_form_world_loras_raises() -> None:
    """A v1-schema world file (list `loras:`) is unsafe to silently inherit."""
    world = {
        "loras": [
            {"name": "x", "file": "x.safetensors", "scale": 1.0,
             "applies_to": ["landscape"]}
        ]
    }
    with pytest.raises(ComposeError, match="legacy list-form"):
        compose_lora_stack(GENRE, world, tier="landscape")


# ─── Task 4.4: load_visual_style wiring ───────────────────────────────


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))


def test_load_visual_style_without_tier_omits_resolved_loras(tmp_path: Path) -> None:
    """Backward compat: callers that don't pass `tier=` get the old shape."""
    _write_yaml(tmp_path / "visual_style.yaml", {"positive_suffix": "x"})
    style = load_visual_style(tmp_path)
    assert "resolved_loras" not in style


def test_load_visual_style_with_tier_adds_resolved_loras(tmp_path: Path) -> None:
    """Genre-only LoRA flows through to `resolved_loras` for the matching tier."""
    _write_yaml(tmp_path / "visual_style.yaml", {
        "positive_suffix": "x",
        "loras": [
            {"name": "g1", "file": "a.safetensors", "scale": 0.8,
             "applies_to": ["landscape"], "trigger": "g1"},
        ],
    })
    style = load_visual_style(tmp_path, tier="landscape")
    assert [e["name"] for e in style["resolved_loras"]] == ["g1"]


def test_load_visual_style_world_exclude_drops_genre_lora(tmp_path: Path) -> None:
    """End-to-end: genre lists, world excludes, the resolved stack reflects both."""
    _write_yaml(tmp_path / "visual_style.yaml", {
        "loras": [
            {"name": "g1", "file": "a.safetensors", "scale": 0.8,
             "applies_to": ["landscape"]},
        ],
    })
    _write_yaml(tmp_path / "worlds" / "w1" / "visual_style.yaml", {
        "loras": {"exclude": ["g1"]},
    })
    style = load_visual_style(tmp_path, world="w1", tier="landscape")
    assert style["resolved_loras"] == []


def test_load_visual_style_world_loras_key_does_not_clobber_genre_loras(
    tmp_path: Path,
) -> None:
    """The `loras:` key is excluded from the field-by-field overlay.

    A naive `merged.update(world)` would overwrite the genre's list-form
    entries with the world's dict-form `{exclude, add}`, leaving the merged
    dict in a half-broken state. This test pins down that we keep the
    genre list intact as `merged["loras"]` (the resolver still uses the
    raw genre+world dicts internally).
    """
    _write_yaml(tmp_path / "visual_style.yaml", {
        "loras": [
            {"name": "g1", "file": "a.safetensors", "scale": 0.8,
             "applies_to": ["landscape"]},
        ],
    })
    _write_yaml(tmp_path / "worlds" / "w1" / "visual_style.yaml", {
        "loras": {"add": []},
    })
    style = load_visual_style(tmp_path, world="w1", tier="landscape")
    assert style["loras"] == [
        {"name": "g1", "file": "a.safetensors", "scale": 0.8,
         "applies_to": ["landscape"]},
    ]


# ─── Task 4.4 wiring: resolve_lora_args precedence ────────────────────


def test_resolve_lora_args_no_lora_returns_nones() -> None:
    assert resolve_lora_args({}) == (None, None)


def test_resolve_lora_args_legacy_only_promotes_to_arrays() -> None:
    """Pre-migration YAMLs (`lora:` flat key) still flow through."""
    style = {"lora": "/abs/path/style.ckpt", "lora_scale": 0.65}
    paths, scales = resolve_lora_args(style)
    assert paths == ["/abs/path/style.ckpt"]
    assert scales == [0.65]


def test_resolve_lora_args_legacy_default_scale_is_one() -> None:
    """Legacy `lora:` without `lora_scale:` defaults to 1.0."""
    paths, scales = resolve_lora_args({"lora": "/abs/path.ckpt"})
    assert scales == [1.0]


def test_resolve_lora_args_resolved_loras_used_directly() -> None:
    """Migrated YAMLs (`loras:` schema → resolved_loras) bypass legacy path."""
    style = {
        "resolved_loras": [
            {"name": "a", "file": "a.safetensors", "scale": 0.8,
             "applies_to": ["landscape"]},
            {"name": "b", "file": "b.safetensors", "scale": 0.5,
             "applies_to": ["landscape"]},
        ]
    }
    paths, scales = resolve_lora_args(style)
    assert paths == ["a.safetensors", "b.safetensors"]
    assert scales == [0.8, 0.5]


def test_resolve_lora_args_both_schemas_present_raises() -> None:
    """A YAML mid-migration with both keys is ambiguous → fail loud."""
    style = {
        "lora": "/old.ckpt",
        "resolved_loras": [
            {"name": "a", "file": "a.safetensors", "scale": 0.8,
             "applies_to": ["landscape"]},
        ],
    }
    with pytest.raises(ValueError, match="both legacy"):
        resolve_lora_args(style)


def test_resolve_lora_args_empty_resolved_falls_through_to_legacy() -> None:
    """Empty resolved_loras (tier had no matching entries) is not a conflict."""
    style = {"lora": "/old.ckpt", "lora_scale": 0.7, "resolved_loras": []}
    paths, scales = resolve_lora_args(style)
    assert paths == ["/old.ckpt"]
    assert scales == [0.7]


# ─── Story 45-38: high-fidelity tier wiring (AC2) ─────────────────────


def test_send_render_accepts_fidelity_kwarg() -> None:
    """Story 45-38 AC2: send_render exposes a `fidelity` kwarg so callers
    can request the base-1.0 / 20-step / CFG 4 path for pre-gen, while
    in-session callers omit it and stay on Turbo (AC3)."""
    sig = inspect.signature(send_render)
    assert "fidelity" in sig.parameters


def test_send_render_default_fidelity_is_turbo() -> None:
    """AC3: callers that don't pass `fidelity` get Turbo — preserves the
    in-session live-narration latency budget without behavioral change."""
    sig = inspect.signature(send_render)
    assert sig.parameters["fidelity"].default == "turbo"


def test_render_batch_accepts_fidelity_kwarg() -> None:
    """The batch loop must thread fidelity through to each send_render call."""
    from scripts.render_common import render_batch

    sig = inspect.signature(render_batch)
    assert "fidelity" in sig.parameters


def test_render_batch_default_fidelity_is_turbo() -> None:
    """Default behavior unchanged — pre-gen scripts must opt into HF explicitly."""
    from scripts.render_common import render_batch

    sig = inspect.signature(render_batch)
    assert sig.parameters["fidelity"].default == "turbo"


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def test_generate_portrait_script_routes_to_high_fidelity_by_default() -> None:
    """AC2: generate_portrait_images.py defaults to the high-fidelity tier
    for genre-pack pre-gen.

    This is a source-level wiring assertion — the script's render_batch call
    must specify ``fidelity="high_fidelity"``. The test deliberately accepts
    either quoting style so Dev's formatter choice doesn't break the check.
    """
    src = (SCRIPTS_DIR / "generate_portrait_images.py").read_text()
    assert (
        'fidelity="high_fidelity"' in src
        or "fidelity='high_fidelity'" in src
    ), (
        "generate_portrait_images.py must call render_batch with "
        "fidelity='high_fidelity' to default pre-gen to base Z-Image 1.0"
    )


def test_generate_poi_script_routes_to_high_fidelity_by_default() -> None:
    """AC2: generate_poi_images.py defaults to the high-fidelity tier."""
    src = (SCRIPTS_DIR / "generate_poi_images.py").read_text()
    assert (
        'fidelity="high_fidelity"' in src
        or "fidelity='high_fidelity'" in src
    ), (
        "generate_poi_images.py must call render_batch with "
        "fidelity='high_fidelity' to default pre-gen to base Z-Image 1.0"
    )


def test_send_render_fidelity_propagates_to_request_payload(monkeypatch) -> None:
    """Wiring test (CLAUDE.md mandate): the fidelity kwarg must reach the
    JSON-RPC params dict the daemon receives — not just sit in the function
    signature dead.

    Without this, send_render could accept the kwarg, satisfy the signature
    test, and still drop it before serialization — passing tests, broken
    production. The mock captures the line written to the unix socket and
    asserts ``fidelity`` survives the trip.
    """
    import asyncio
    import json
    from scripts import render_common

    captured: dict = {}

    class _FakeWriter:
        def __init__(self) -> None:
            self.buffer = bytearray()

        def write(self, data: bytes) -> None:
            self.buffer.extend(data)

        async def drain(self) -> None:
            return None

        def close(self) -> None:
            return None

        async def wait_closed(self) -> None:
            return None

    class _FakeReader:
        async def readline(self) -> bytes:
            return (json.dumps({"id": "x", "result": {"image_path": "/tmp/x"}}) + "\n").encode()

    async def fake_open_unix_connection(path):
        writer = _FakeWriter()
        captured["writer"] = writer
        return _FakeReader(), writer

    monkeypatch.setattr(
        "scripts.render_common.asyncio.open_unix_connection",
        fake_open_unix_connection,
    )

    asyncio.run(
        render_common.send_render(
            tier="portrait",
            positive="x", clip="y", negative="z", seed=42, steps=20,
            fidelity="high_fidelity",
        )
    )

    line = bytes(captured["writer"].buffer).decode().strip()
    assert line, "send_render must write a request line to the socket"
    payload = json.loads(line)
    assert payload["params"].get("fidelity") == "high_fidelity", (
        "send_render must propagate fidelity to the JSON-RPC params dict; "
        "otherwise the daemon never sees it. Got params="
        f"{payload['params']!r}"
    )
