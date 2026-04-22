"""Shared utilities for image generation scripts.

Common code for portrait and POI batch renderers: daemon communication,
visual style loading, token estimation, slugification, and YAML helpers.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
from pathlib import Path

SOCKET_PATH = Path("/tmp/sidequest-renderer.sock")
_root = Path(__file__).resolve().parent.parent
GENRE_PACKS_DIR = _root / "sidequest-content" / "genre_packs"
LORA_DIR = _root / "sidequest-content" / "lora"

# T5-XXL token limit
TOKEN_LIMIT = 512
TOKENS_PER_WORD = 1.3

log = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text.split()) * TOKENS_PER_WORD))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    words = text.split()
    max_words = int(max_tokens / TOKENS_PER_WORD)
    return " ".join(words[:max_words]) if max_words > 0 else ""


def load_yaml(path: Path) -> dict:
    import yaml
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_visual_style(
    genre_dir: Path,
    world: str = "",
    *,
    tier: str | None = None,
) -> dict:
    """Load visual_style.yaml — genre-level base, world-level overrides on top.

    Genre-level provides the base style (positive_suffix, negative_prompt,
    preferred_model, LoRA config). World-level can override or extend with
    world-specific fields (style_prompt, color_palette, etc.). The merge
    ensures world overrides don't lose genre-level rendering fields.

    When `tier` is provided (Task 4.4 wiring), also resolves the LoRA stack
    via compose_lora_stack and exposes it as `merged["resolved_loras"]`.
    The `loras:` key is intentionally skipped during the field-by-field
    world overlay because the world form is a dict `{exclude, add}` not a
    list — a naive overlay would silently clobber inherited genre entries.
    Callers who pass `tier=...` should read `resolved_loras`; callers that
    don't are still on the legacy `lora:` / `lora_scale:` flat path until
    Task 4.6 migrates the YAML files.
    """
    genre_vs_path = genre_dir / "visual_style.yaml"
    genre_style = load_yaml(genre_vs_path) if genre_vs_path.exists() else {}

    world_style: dict = {}
    if world:
        world_vs = genre_dir / "worlds" / world / "visual_style.yaml"
        if world_vs.exists():
            log.debug("Merging world visual_style: %s", world_vs)
            world_style = load_yaml(world_vs)

    merged = dict(genre_style)
    for key, value in world_style.items():
        if key == "loras":
            continue
        merged[key] = value

    if tier is not None:
        merged["resolved_loras"] = compose_lora_stack(
            genre_style, world_style, tier=tier
        )

    return merged


# ── Multi-LoRA stack composition (Phase 4 Task 4.3) ───────────────────
#
# Per ADR-083 Decision 4 + Architect correction #5: lives in render_common
# rather than a dedicated scripts/lora/compose.py module. Pure function;
# no I/O beyond the YAML-parsed dicts the caller hands in.


class ComposeError(RuntimeError):
    """Raised when genre+world LoRA composition violates schema rules."""


_LORA_REQUIRED_FIELDS = ("name", "file", "scale", "applies_to")


def _validate_lora_entry(entry: dict, source: str) -> None:
    """Validate a single LoRA entry against the visual_style.yaml schema.

    `source` is "genre" or "world" — surfaces the right context in errors so
    the user knows which file to fix when validation trips.
    """
    for field in _LORA_REQUIRED_FIELDS:
        if field not in entry:
            raise ComposeError(
                f"{source}: LoRA entry missing required field {field!r} "
                f"(name={entry.get('name', '?')!r})"
            )
    applies_to = entry["applies_to"]
    if not isinstance(applies_to, list) or not applies_to:
        raise ComposeError(
            f"{source}: LoRA {entry.get('name', '?')!r} has empty applies_to — "
            f"misconfiguration (an entry that applies to no tier never fires)."
        )


def compose_lora_stack(
    genre_style: dict,
    world_style: dict,
    tier: str,
) -> list[dict]:
    """Resolve the effective LoRA stack for a single render at the given tier.

    Inputs are the YAML-parsed `visual_style.yaml` dicts for genre and
    (optionally) world. Returns a flat list of LoRA entries that pass the
    `applies_to` tier filter, in order: genre entries first, then any
    world `add:` entries appended.

    World schema (the new form, post-Task 4.6):
        loras:
          exclude: [name, ...]   # genre entries to drop before adding
          add:                   # extra entries unique to this world
            - name: ...
              file: ...
              ...

    Hard fails on:
      - missing required fields on any entry
      - empty `applies_to` (never-fires entry is always misconfiguration)
      - world.loras given as a list (legacy v1 schema — must be migrated
        to the dict form before composition will accept it)
      - world.add reusing a name still inherited from genre (use exclude
        first to drop it, so the operator's intent is explicit)
    """
    base: list[dict] = list(genre_style.get("loras") or [])
    for entry in base:
        _validate_lora_entry(entry, source="genre")

    world_loras = world_style.get("loras") or {}
    if isinstance(world_loras, list):
        raise ComposeError(
            "world visual_style.yaml has legacy list-form `loras:`; "
            "expected `{exclude: [...], add: [...]}` schema. Migrate the "
            "world file or move its entries up to the genre level."
        )

    excluded = set(world_loras.get("exclude") or [])
    base = [e for e in base if e["name"] not in excluded]

    added: list[dict] = list(world_loras.get("add") or [])
    for entry in added:
        _validate_lora_entry(entry, source="world")

    existing_names = {e["name"] for e in base}
    for add_entry in added:
        if add_entry["name"] in existing_names:
            raise ComposeError(
                f"world.loras.add declares duplicate name {add_entry['name']!r}; "
                f"use world.loras.exclude first to drop the inherited entry."
            )

    composed = base + added
    return [e for e in composed if tier in e["applies_to"]]


def _resolve_lora_file(file: str) -> str:
    """Resolve a YAML `file:` entry to an absolute path the daemon can open.

    Relative entries resolve against sidequest-content/lora/ — the single
    canonical LoRA root — so YAML stays machine-portable across clones.
    Absolute paths are passed through untouched.
    """
    p = Path(file)
    if p.is_absolute():
        return str(p)
    return str((LORA_DIR / p).resolve())


def resolve_lora_args(visual_style: dict) -> tuple[list[str] | None, list[float] | None]:
    """Pick lora_paths/lora_scales for send_render based on schema state.

    Three valid input shapes:
      1. `resolved_loras` present (set by load_visual_style when tier= was
         passed) — preferred path; ship those entries' file+scale.
      2. Legacy flat `lora:` + optional `lora_scale:` — promoted to a
         single-entry array. Transitional; comes off when all
         visual_style.yaml files migrate to the loras: schema.
      3. Neither — return (None, None) for an un-LoRA'd render.

    `file:` entries may be relative (preferred — resolved against
    sidequest-content/lora/) or absolute. Either way, absolute paths are
    what reach the daemon; no cwd-dependent behavior at render time.

    Hard-fails on the cross-schema case (`lora:` AND non-empty
    `resolved_loras` both present): no silent precedence rule should
    paper over a misconfigured YAML mid-migration.
    """
    has_legacy = bool(visual_style.get("lora"))
    resolved = visual_style.get("resolved_loras") or []

    if has_legacy and resolved:
        raise ValueError(
            "visual_style has both legacy `lora:` and resolved `loras:` — "
            "pick one schema; the merged dict cannot represent both."
        )

    if resolved:
        return (
            [_resolve_lora_file(entry["file"]) for entry in resolved],
            [float(entry["scale"]) for entry in resolved],
        )

    if has_legacy:
        return (
            [_resolve_lora_file(visual_style["lora"])],
            [float(visual_style.get("lora_scale", 1.0))],
        )

    return (None, None)


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    return (
        text.lower()
        .replace("'", "")
        .replace("\u2019", "")
        .replace('"', "")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .replace(".", "")
        .replace(":", "")
        .replace("/", "-")
        .replace(" ", "_")
        .strip("_-")
    )


def deterministic_seed(key: str, base_seed: int) -> int:
    """Generate a deterministic seed from a string key and base seed."""
    digest = hashlib.sha256(key.encode()).hexdigest()
    return (int(digest[:8], 16) + base_seed) % (2**32)


async def send_render(
    tier: str,
    positive: str,
    clip: str,
    negative: str,
    seed: int,
    steps: int = 15,
    *,
    art_style: str = "",
    visual_tag_overrides: dict | None = None,
    lora_paths: list[str] | None = None,
    lora_scales: list[float] | None = None,
    variant: str = "",
) -> dict:
    """Send a render request to the daemon and return the result.

    When art_style is provided, `positive` is treated as `subject` and the
    daemon's PromptComposer handles style injection, tag overrides, and LoRA.
    Without art_style, `positive` is sent as `positive_prompt` (direct path).
    """
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    params: dict = {
        "tier": tier,
        "negative_prompt": negative,
        "seed": seed,
    }

    if art_style:
        # Route through daemon's PromptComposer for proper style injection
        params["subject"] = positive
        params["art_style"] = art_style
        if visual_tag_overrides:
            params["visual_tag_overrides"] = visual_tag_overrides
    else:
        # Direct path — caller pre-composed the prompt
        params["positive_prompt"] = positive
        params["clip_prompt"] = clip

    if lora_paths:
        if lora_scales is None or len(lora_scales) != len(lora_paths):
            raise ValueError(
                "lora_scales must be provided with the same length as lora_paths"
            )
        params["lora_paths"] = list(lora_paths)
        params["lora_scales"] = list(lora_scales)
    if variant:
        params["variant"] = variant

    req = {
        "id": f"{tier}-{seed}",
        "method": "render",
        "params": params,
    }

    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()

    response_line = await reader.readline()
    writer.close()
    await writer.wait_closed()

    return json.loads(response_line.decode())


async def check_daemon() -> bool:
    """Check if the daemon is running."""
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
        req = {"id": "healthcheck", "method": "ping"}
        writer.write((json.dumps(req) + "\n").encode())
        await writer.drain()
        resp = await reader.readline()
        writer.close()
        await writer.wait_closed()
        data = json.loads(resp.decode())
        return data.get("result", {}).get("status") == "ok"
    except Exception:
        return False


async def render_batch(
    items: list[dict],
    compose_fn,
    tier: str,
    image_subdir: str,
    *,
    genre_filter: str | None = None,
    dry_run: bool = False,
    steps: int = 15,
    force: bool = False,
    output_dir: Path | None = None,
) -> None:
    """Generic batch render loop for any image type.

    Args:
        items: List of dicts, each with 'genre', 'world', 'name', '_visual_style'.
        compose_fn: Function(item, visual_style) -> (positive, clip, negative, seed).
        tier: Renderer tier ('portrait', 'landscape', etc.).
        image_subdir: Subdirectory under images/ ('portraits', 'poi', etc.).
        genre_filter: Only process items from this genre.
        dry_run: Preview prompts without rendering.
        steps: Inference steps.
        force: Regenerate even if image exists.
        output_dir: Override output directory.
    """
    import time

    if not items:
        log.error("No items found!")
        return

    log.info("Found %d items across %d genre packs",
             len(items), len(set(it["genre"] for it in items)))

    if not dry_run:
        if not await check_daemon():
            log.error("Daemon not running at %s — start with: sidequest-renderer", SOCKET_PATH)
            return
        log.info("Daemon is alive at %s", SOCKET_PATH)

    total = len(items)
    success = 0
    failed = 0
    start_time = time.monotonic()

    for i, item in enumerate(items, 1):
        visual_style = item.pop("_visual_style")
        positive, clip, negative, seed = compose_fn(item, visual_style)

        if output_dir:
            out_dir = output_dir / item["genre"]
        else:
            out_dir = GENRE_PACKS_DIR / item["genre"] / "images" / image_subdir
        out_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(item["name"])
        out_path = out_dir / f"{slug}.png"

        # Skip if already generated (unless --force)
        if out_path.exists() and not force and not dry_run:
            log.info("[%d/%d] SKIP %s/%s (already exists)", i, total, item["genre"], item["name"])
            success += 1
            continue

        label = item.get("role", item.get("chapter_label", ""))
        log.info("[%d/%d] %s / %s / %s%s", i, total, item["genre"], item["world"], item["name"],
                 f" ({label})" if label else "")

        if dry_run:
            print(f"\n{'='*80}")
            print(f"Genre: {item['genre']}  World: {item['world']}")
            print(f"Name: {item['name']}")
            print(f"Seed: {seed}")
            print(f"\nPositive prompt ({estimate_tokens(positive)} tokens):")
            print(f"  {positive}")
            print(f"\nCLIP prompt:")
            print(f"  {clip}")
            print(f"\nNegative prompt:")
            print(f"  {negative}")
            print(f"\nOutput: {out_path}")
            continue

        try:
            lora_paths, lora_scales = resolve_lora_args(visual_style)
            result = await send_render(
                tier, positive, clip, negative, seed, steps,
                art_style=visual_style.get("positive_suffix", ""),
                visual_tag_overrides=visual_style.get("visual_tag_overrides"),
                lora_paths=lora_paths,
                lora_scales=lora_scales,
                variant=visual_style.get("preferred_model", ""),
            )
            if "error" in result:
                log.error("  FAILED: %s", result["error"])
                failed += 1
                continue

            render_result = result["result"]
            rendered_path = Path(render_result.get("image_path") or render_result["image_url"])
            shutil.copy2(rendered_path, out_path)
            elapsed = result["result"].get("elapsed_ms", 0)
            log.info("  OK (%.1fs) → %s", elapsed / 1000, out_path)
            success += 1

        except Exception as e:
            log.error("  FAILED: %s", e)
            failed += 1

    total_time = time.monotonic() - start_time

    print(f"\n{'='*80}")
    print(f"Done! {success}/{total} generated, {failed} failed")
    print(f"Total time: {total_time/60:.1f} minutes")
    if success > 0 and total_time > 0:
        print(f"Average: {total_time/success:.1f}s per image")
