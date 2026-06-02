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


def parse_shard(spec: str | None) -> tuple[int, int] | None:
    """Parse a ``--shard i/n`` spec into ``(index, total)``; ``None`` when unset.

    Splits a deterministic work-list across N renderers: shard ``i/n`` keeps every
    item whose stable-sorted position is congruent to ``i`` modulo ``n``. Run
    ``--shard 0/2`` on one machine and ``--shard 1/2`` on another for a disjoint,
    complete partition.

    Raises ``SystemExit`` on malformed input — a typo'd shard must fail loud, not
    silently render the whole set on every machine (No Silent Fallbacks).
    """
    if spec is None:
        return None
    try:
        i_str, n_str = spec.split("/", 1)
        index, total = int(i_str), int(n_str)
    except (ValueError, AttributeError):
        raise SystemExit(f"--shard must look like 'i/n' (e.g. 0/2), got {spec!r}")
    if total < 1 or not (0 <= index < total):
        raise SystemExit(
            f"--shard i/n requires 1<=n and 0<=i<n, got {spec!r}",
        )
    return index, total


def apply_shard(items, shard, key):
    """Keep only the items in ``shard`` of a stable-sorted partition of ``items``.

    Sorting by ``key`` before partitioning makes the split identical on every
    machine regardless of filesystem or collection order, so ``0/n`` … ``(n-1)/n``
    are disjoint and together cover the whole list. ``shard=None`` is a pass-through.
    """
    if shard is None:
        return items
    index, total = shard
    ordered = sorted(items, key=key)
    return [item for pos, item in enumerate(ordered) if pos % total == index]


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

    Genre-level provides the base style (positive_suffix,
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
    seed: int,
    steps: int = 15,
    *,
    subject: str = "",
    genre: str = "",
    world: str = "",
    lora_paths: list[str] | None = None,
    lora_scales: list[float] | None = None,
    variant: str = "",
    fidelity: str = "turbo",
) -> dict:
    """Send a render request to the daemon and return the result.

    When subject + genre + world are provided, the daemon routes through
    its catalog-injected PromptComposer (style, camera, cast, and places
    are pulled from the world's visual_style.yaml / characters.yaml /
    places.yaml). Otherwise `positive` is sent as `positive_prompt` — the
    caller pre-composed the full prompt.

    ``fidelity`` selects the Z-Image variant (Story 45-38). ``"turbo"``
    keeps in-session live narration on z-image-turbo / 8 steps;
    ``"high_fidelity"`` routes pre-gen to base z-image / 20 steps / CFG 4.
    """
    reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))

    # No negative_prompt is sent: Z-Image ignores negatives at
    # guidance_scale=0, and for catalog-composed renders the daemon
    # overwrites any config-supplied negative with its own runtime
    # _BASE_NEGATIVES (daemon.py: params["negative_prompt"] =
    # composed.negative_prompt). The zimage worker treats an absent
    # negative_prompt as None. Story 64-11 removed the dead config field.
    params: dict = {
        "tier": tier,
        "seed": seed,
        "fidelity": fidelity,
        # Caller-supplied inference-step override. The worker honors this over
        # the (tier, fidelity) default from get_zimage_config; absent it, the
        # tier default stands. Without this line the `--steps` flag was dead
        # wiring — accepted by the CLI and threaded to send_render, then
        # dropped on the floor here, so the daemon always used the tier default
        # (15→30 produced identical ~125s renders). Validated worker-side.
        "steps": steps,
    }

    if subject and genre and world:
        # Catalog-composed path — daemon pulls style + cast + places from
        # the genre pack via StyleCatalog / CharacterCatalog / PlaceCatalog.
        params["subject"] = subject
        params["genre"] = genre
        params["world"] = world
    else:
        # Direct path — caller pre-composed the prompt.
        params["positive_prompt"] = positive
        params["clip_prompt"] = clip

    if lora_paths:
        # The Z-Image MLX worker rejects lora_paths/lora_scales since the
        # post-MLX renderer dropped LoRA support entirely (see
        # sidequest_daemon/media/workers/zimage_mlx_worker.py: "LoRA support
        # has been removed from the renderer"). visual_style.yaml files
        # still carry `loras:` blocks for documentation / future re-enable;
        # the script must skip them here, not silently pretend they applied.
        if lora_scales is None or len(lora_scales) != len(lora_paths):
            raise ValueError(
                "lora_scales must be provided with the same length as lora_paths"
            )
        log.warning(
            "send_render.lora_skipped count=%d daemon_dropped_support=true tier=%s",
            len(lora_paths),
            tier,
        )
    if variant:
        params["variant"] = variant

    req = {
        "id": f"{tier}-{seed}",
        "method": "render",
        "params": params,
    }

    writer.write((json.dumps(req) + "\n").encode())
    await writer.drain()

    # Daemon emits heartbeat event lines on every connection alongside
    # the response. Skip non-response lines and match by request id.
    response: dict = {}
    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            data = json.loads(line.decode())
        except json.JSONDecodeError:
            continue
        if data.get("id") == req["id"]:
            response = data
            break
    writer.close()
    await writer.wait_closed()

    return response


async def check_daemon() -> bool:
    """Check if the daemon is running.

    The daemon emits heartbeat event lines before/alongside the response.
    Skip lines without `id == "healthcheck"` and look for our reply.
    """
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
        req = {"id": "healthcheck", "method": "ping"}
        writer.write((json.dumps(req) + "\n").encode())
        await writer.drain()
        for _ in range(20):
            line = await asyncio.wait_for(reader.readline(), timeout=2.0)
            if not line:
                break
            try:
                data = json.loads(line.decode())
            except json.JSONDecodeError:
                continue
            if data.get("id") == "healthcheck":
                writer.close()
                await writer.wait_closed()
                return data.get("result", {}).get("status") == "ok"
        writer.close()
        await writer.wait_closed()
        return False
    except Exception:
        return False


def existing_r2_keys(prefix: str = "genre_packs/", bucket: str = "sidequest") -> set[str]:
    """Return the set of live R2 object keys under ``prefix`` (one paginated LIST).

    Generated PNGs are gitignored, so a local-disk-only existence check
    regenerates assets already on R2 on any clone that didn't render them
    locally. Listing the bucket lets the batch loop skip what's already
    uploaded. Reuses the boto3 client from r2_sync_packs — no second client.

    Fails loud: a missing R2_S3_ENDPOINT/creds (KeyError) or a ClientError
    propagates rather than silently returning an empty set, which would make
    the caller regenerate every asset (No-Silent-Fallbacks).

    The boto3 client config mirrors r2_sync_packs._build_client, but is inlined
    rather than imported: the generators run as ``python3 scripts/x.py`` (this
    module is imported top-level), whereas r2_sync_packs imports
    ``scripts.r2_manifest`` and only resolves under the repo-root package
    regime — importing it here would break the generators at runtime.
    """
    import os

    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_S3_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    keys: set[str] = set()
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.add(obj["Key"])
    return keys


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
    catalog_compose: bool = False,
    fidelity: str = "turbo",
) -> None:
    """Generic batch render loop for any image type.

    Args:
        items: List of dicts, each with 'genre', 'world', 'name', '_visual_style'.
        compose_fn: Function(item, visual_style) -> (positive, clip, seed).
        tier: Renderer tier ('portrait', 'landscape', etc.).
        image_subdir: Subdirectory under assets/ ('portraits', 'poi', etc.).
            When ``image_subdir`` is ``"poi"`` or ``"portraits"``, output is
            auto-bridged to the world-scoped path
            ``<genre>/worlds/<world>/assets/<subdir>/<slug>.png``. POIs match
            the server's cover_poi resolver
            (sidequest-server/sidequest/server/rest.py:215-218); portraits
            (Story 65-6) match emitters._resolve_npc_portrait_url, which
            attaches the portrait to a scrapbook NPC ref when the invoked NPC
            is in the world's portrait_manifest. All other subdirs route to the
            genre-flat ``<genre>/images/<subdir>/<slug>.png`` (e.g. creatures).
            For POI and portrait items, raises ValueError if world is empty or
            "default": the world-scoped resolver cannot reach genre-level
            entries, so a silent fallback would orphan the file
            (No-Silent-Fallbacks).
        genre_filter: Only process items from this genre.
        dry_run: Preview prompts without rendering.
        steps: Inference steps.
        force: Regenerate even if image exists.
        output_dir: Override output directory (escape hatch for ad-hoc dumps;
            bypasses the world-scoped POI routing).
        catalog_compose: When True and an item has a `catalog_ref` (e.g.
            `where:<world>/<slug>` for POIs, `npc:<slug>` for portraits),
            route through the daemon's PromptComposer so all style layers
            (genre + world + casting + culture + camera) apply. Items
            without `catalog_ref` fall back to the legacy local-composition
            path so worlds with no catalog-ready content still render.
    """
    import time

    if not items:
        log.error("No items found!")
        return

    log.info("Found %d items across %d genre packs",
             len(items), len(set(it["genre"] for it in items)))

    content_root = GENRE_PACKS_DIR.parent
    remote_keys: set[str] = set()
    if not force and not dry_run:
        remote_keys = existing_r2_keys()
        log.info("R2 has %d objects under genre_packs/ — will skip those already uploaded",
                 len(remote_keys))

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
        positive, clip, seed = compose_fn(item, visual_style)

        suffix = visual_style.get("positive_suffix", "")
        full_positive = f"{positive}, {suffix}" if suffix else positive

        if output_dir:
            out_dir = output_dir / item["genre"]
        elif image_subdir in ("poi", "portraits"):
            # Both POIs (ADR-086) and NPC portraits (Story 65-6) are
            # world-scoped FLAVOR: they live under
            # worlds/<world>/assets/<subdir>/ so the server's world-scoped
            # resolvers reach them (cover_poi for POIs;
            # emitters._resolve_npc_portrait_url for portraits). A
            # genre-level entry would be orphaned — the resolver only walks
            # worlds/<world>/assets/. Fail loudly (No-Silent-Fallbacks).
            world = item.get("world", "")
            if not world or world == "default":
                kind = "POI" if image_subdir == "poi" else "portrait"
                src = (
                    "worlds/<world>/history.yaml"
                    if image_subdir == "poi"
                    else "worlds/<world>/portrait_manifest.yaml"
                )
                raise ValueError(
                    f"render_batch: {kind} items must carry a real world (got "
                    f"world={world!r}) — the server's world-scoped resolver only "
                    f"reaches files under worlds/<world>/assets/{image_subdir}/, "
                    f"so a genre-level entry would be orphaned. Move the entry "
                    f"under {src}. Offending item: "
                    f"{item.get('genre')}/{item.get('name')}."
                )
            out_dir = (
                GENRE_PACKS_DIR
                / item["genre"]
                / "worlds"
                / world
                / "assets"
                / image_subdir
            )
        else:
            out_dir = GENRE_PACKS_DIR / item["genre"] / "images" / image_subdir

        slug = item.get("slug") or (item.get("id") and slugify(item["id"])) or slugify(item["name"])
        out_path = out_dir / f"{slug}.png"

        # Skip if already generated locally OR already on R2 (unless --force).
        # R2 key is the LOGICAL path relative to content_root (genre_packs/...),
        # matching r2_sync_packs' 1:1 upload convention. Do NOT resolve() — a
        # symlinked assets/poi would otherwise resolve to a different key than
        # what was uploaded. output_dir dumps live outside content_root, so they
        # have no R2 key and fall back to the disk-only check.
        on_r2 = False
        if remote_keys:
            try:
                r2_key = out_path.relative_to(content_root).as_posix()
            except ValueError:
                r2_key = None
            on_r2 = r2_key is not None and r2_key in remote_keys

        if (out_path.exists() or on_r2) and not force and not dry_run:
            where = "local" if out_path.exists() else "R2"
            log.info("[%d/%d] SKIP %s/%s (already exists: %s)",
                     i, total, item["genre"], item["name"], where)
            success += 1
            continue

        # catalog_compose validation runs AFTER the skip gate: an item already
        # on R2 (or local) is skipped without needing a catalog_ref — only items
        # we actually render must satisfy the catalog contract.
        if catalog_compose:
            catalog_subject = item.get("catalog_ref", "")
            if not catalog_subject:
                raise ValueError(
                    f"render_batch: catalog_compose=True requires non-empty "
                    f"catalog_ref on every item; got empty for "
                    f"{item.get('genre')}/{item.get('world')}/{item.get('name')}"
                )
            use_catalog = True
        else:
            use_catalog = False
            catalog_subject = ""

        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)

        label = item.get("role", item.get("chapter_label", ""))
        log.info("[%d/%d] %s / %s / %s%s", i, total, item["genre"], item["world"], item["name"],
                 f" ({label})" if label else "")

        if dry_run:
            print(f"\n{'='*80}")
            print(f"Genre: {item['genre']}  World: {item['world']}")
            print(f"Name: {item['name']}")
            print(f"Seed: {seed}")
            if use_catalog:
                print("\nMode: catalog-composed (daemon applies GENRE + WORLD + CASTING + LOCATION + camera)")
                print(f"Catalog ref: {catalog_subject}")
            else:
                print("\nMode: local pre-composed prompt (legacy fallback)")
                print(f"\nSubject ({estimate_tokens(positive)} tokens):")
                print(f"  {positive}")
                print("\nStyle suffix:")
                print(f"  {suffix or '(none)'}")
                print(f"\nFull positive prompt sent to daemon ({estimate_tokens(full_positive)} tokens):")
                print(f"  {full_positive}")
                print("\nCLIP prompt:")
                print(f"  {clip}")
            print(f"\nOutput: {out_path}")
            continue

        try:
            lora_paths, lora_scales = resolve_lora_args(visual_style)
            if use_catalog:
                result = await send_render(
                    tier, "", "", seed, steps,
                    subject=catalog_subject,
                    genre=item["genre"],
                    world=item["world"],
                    lora_paths=lora_paths,
                    lora_scales=lora_scales,
                    variant=visual_style.get("preferred_model", ""),
                    fidelity=fidelity,
                )
            else:
                result = await send_render(
                    tier, full_positive, clip, seed, steps,
                    lora_paths=lora_paths,
                    lora_scales=lora_scales,
                    variant=visual_style.get("preferred_model", ""),
                    fidelity=fidelity,
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
