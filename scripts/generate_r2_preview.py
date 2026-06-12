#!/usr/bin/env python3
"""Build a self-contained, auto-refreshing R2 preview gallery for rendered assets.

Unlike ``generate_image_sheets.py`` (which walks LOCAL PNG dirs and so can only
show what's already on THIS box's disk), this tool enumerates every EXPECTED image
asset from the content MANIFESTS — the same authoritative work-list the renderers
walk — and points each tile at its CDN URL. That makes it the right monitor for a
distributed render split across two Macs that both upload to the same R2 bucket:
the local contact sheet can't see the other box's output, but the CDN can.

Each expected asset becomes an ``<img>`` whose ``src`` is its public CDN URL. Tiles
that 404 (not yet uploaded by either box) are styled "pending" rather than hidden —
the whole point is seeing what's still missing. A header counter tracks
"N rendered / M expected" live as images load or error, and the page re-fetches
every img with a fresh cache-bust token every 30s so newly-uploaded renders from
either machine appear without a manual reload (and without losing scroll).

Key derivation is NOT re-invented: the expected R2 key for each asset is exactly the
PNG path the renderer would write (``render_batch`` in render_common), made relative
to the content repo root. We import the manifest collectors (``collect_characters``,
``collect_pois``) and the ``slugify`` helper from the render scripts so the keys we
emit match the renderer's output byte-for-byte.

Usage:
    uv run python scripts/generate_r2_preview.py                       # everything
    uv run python scripts/generate_r2_preview.py --genre heavy_metal
    uv run python scripts/generate_r2_preview.py --kind portraits
    uv run python scripts/generate_r2_preview.py --world evropi --kind poi
    uv run python scripts/generate_r2_preview.py --open                # macOS open

Output defaults to image_sheets/r2_preview.html at the repo root (gitignored).
"""

from __future__ import annotations

import argparse
import html
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from render_common import GENRE_PACKS_DIR, slugify

# Manifest collectors — reused, not re-implemented, so our expected-key list is
# exactly the renderer's work-list.
from generate_portrait_images import collect_characters
from generate_poi_images import collect_pois

_ROOT = Path(__file__).resolve().parent.parent
# content_root is the repo root that R2 keys are relative to: render_common uploads
# each PNG keyed by out_path.relative_to(GENRE_PACKS_DIR.parent). Mirror that exactly.
_CONTENT_ROOT = GENRE_PACKS_DIR.parent
DEFAULT_OUT = _ROOT / "image_sheets"
REFRESH_SECONDS = 30


def _asset_base_url() -> str:
    """Resolve the public CDN base URL — same env override + default as the music tool.

    Fails loud (No-Silent-Fallbacks) if the operator set the override to something
    that can't be a base URL, rather than silently serving broken <img> tags.
    """
    raw = os.environ.get("SIDEQUEST_ASSET_BASE_URL", "https://cdn.slabgorb.com")
    base = raw.rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise SystemExit(
            f"SIDEQUEST_ASSET_BASE_URL must be an http(s) URL, got {raw!r}. "
            "Unset it to use the default https://cdn.slabgorb.com."
        )
    return base


@dataclass(frozen=True)
class Asset:
    genre: str
    world: str
    kind: str  # "portraits" | "poi"
    key: str  # R2 object key, e.g. genre_packs/.../assets/portraits/<slug>.png

    @property
    def filename(self) -> str:
        return self.key.rsplit("/", 1)[-1]


def _portrait_slug(char: dict) -> str:
    """Slug the renderer writes for a portrait entry.

    Mirror render_common.render_batch's out_path slug rule for portraits:
    ``item.get("slug") or (id and slugify(id)) or slugify(name)``. collect_characters
    already sets ``slug = char.get("id") or _slugify_name(name)``, so item["slug"] is
    populated and used directly — same as the live renderer.
    """
    slug = (
        char.get("slug")
        or (char.get("id") and slugify(char["id"]))
        or slugify(char["name"])
    )
    if not slug:
        raise SystemExit(
            f"portrait entry has no derivable slug: {char.get('genre')}/"
            f"{char.get('world')}/{char.get('name')!r}"
        )
    return slug


def _poi_slug(poi: dict) -> str:
    """Slug the renderer writes for a POI entry (render_batch rule)."""
    slug = poi.get("slug") or (poi.get("id") and slugify(poi["id"])) or slugify(poi["name"])
    if not slug:
        raise SystemExit(
            f"POI entry has no derivable slug: {poi.get('genre')}/"
            f"{poi.get('world')}/{poi.get('name')!r}"
        )
    return slug


def _world_asset_key(genre: str, world: str, kind: str, slug: str) -> str:
    """Build the R2 key the renderer writes for a world-scoped portrait/POI.

    render_batch writes world-scoped flavor to
    GENRE_PACKS_DIR/<genre>/worlds/<world>/assets/<kind>/<slug>.png and uploads it
    keyed by its path relative to content_root — reproduce that exact key.
    """
    if not world or world == "default":
        # Portraits/POIs are world-scoped in render_batch; a "default" world has no
        # canonical world-scoped key. Skip loudly upstream rather than guess one.
        raise SystemExit(
            f"{kind} entry for {genre}/{slug} has world={world!r}; world-scoped "
            "assets require a real world. This entry would have no canonical R2 key."
        )
    out_path = (
        GENRE_PACKS_DIR / genre / "worlds" / world / "assets" / kind / f"{slug}.png"
    )
    return out_path.relative_to(_CONTENT_ROOT).as_posix()


def collect_assets() -> tuple[list[Asset], dict[str, int]]:
    """Enumerate every expected portrait + POI asset from the manifests.

    Returns the asset list plus a per-kind count for the summary line. Reads only
    manifests (never walks local PNG dirs), so it shows what SHOULD exist regardless
    of which box rendered it.
    """
    assets: list[Asset] = []
    per_kind: dict[str, int] = {"portraits": 0, "poi": 0}

    for genre_dir in sorted(p for p in GENRE_PACKS_DIR.iterdir() if p.is_dir()):
        genre = genre_dir.name

        for char in collect_characters(genre_dir):
            world = char["world"]
            if not world or world == "default":
                # Portraits live under worlds/<world>/assets/portraits/; a default-world
                # entry has no world-scoped key. Skip it (don't fabricate a path).
                continue
            slug = _portrait_slug(char)
            key = _world_asset_key(genre, world, "portraits", slug)
            assets.append(Asset(genre, world, "portraits", key))
            per_kind["portraits"] += 1

        for poi in collect_pois(genre_dir):
            world = poi["world"]
            if not world or world == "default":
                continue
            slug = _poi_slug(poi)
            key = _world_asset_key(genre, world, "poi", slug)
            assets.append(Asset(genre, world, "poi", key))
            per_kind["poi"] += 1

    return assets, per_kind


# ── HTML emission ─────────────────────────────────────────────────────────────

_PAGE_CSS = """
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #141414; color: #e8e8e8;
         font: 14px/1.4 -apple-system, system-ui, Helvetica, Arial, sans-serif; }
  header { position: sticky; top: 0; z-index: 10; padding: 14px 20px;
           background: #1d1d1d; border-bottom: 1px solid #333;
           display: flex; align-items: baseline; gap: 18px; flex-wrap: wrap; }
  header h1 { font-size: 18px; margin: 0; }
  .counter { font-variant-numeric: tabular-nums; font-size: 15px; }
  .counter b { color: #7fd17f; }
  .counter .pending { color: #d1a86a; }
  .meta { color: #888; font-size: 12px; }
  h2.genre { margin: 28px 20px 6px; font-size: 20px; color: #fafafa;
             border-bottom: 2px solid #3a3a3a; padding-bottom: 4px; }
  h3.world { margin: 16px 20px 4px; font-size: 16px; color: #cfcfcf; }
  h4.kind { margin: 10px 20px 8px; font-size: 13px; text-transform: uppercase;
            letter-spacing: 0.08em; color: #9a9a9a; }
  .grid { display: grid; gap: 12px; padding: 0 20px 8px;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
  figure { margin: 0; background: #1d1d1d; border: 1px solid #2c2c2c;
           border-radius: 6px; padding: 6px; text-align: center; }
  figure img { width: 100%; aspect-ratio: 1 / 1; object-fit: cover;
               border-radius: 4px; background: #262626; display: block; }
  figcaption { margin-top: 5px; font-size: 11px; color: #bdbdbd;
               word-break: break-all; }
  figure.pending { border-style: dashed; border-color: #5a4a2a; opacity: 0.55; }
  figure.pending img { visibility: hidden; }
  figure.pending::before { content: "pending"; display: block; position: relative;
                           top: 50%; transform: translateY(-50%); margin-top: -50%;
                           height: 0; color: #d1a86a; font-size: 12px;
                           text-transform: uppercase; letter-spacing: 0.1em;
                           pointer-events: none; }
  figure:not(.pending) img { cursor: zoom-in; }
  /* Lightbox overlay — hidden until JS adds .open */
  #lightbox { position: fixed; inset: 0; z-index: 100; display: none;
              align-items: center; justify-content: center;
              background: rgba(0, 0, 0, 0.86); }
  #lightbox.open { display: flex; }
  #lightbox .lb-stage { display: flex; flex-direction: column; align-items: center;
                        max-width: 92vw; max-height: 92vh; }
  #lightbox img { max-width: 92vw; max-height: 82vh; object-fit: contain;
                  border-radius: 4px; background: #262626; box-shadow: 0 8px 40px rgba(0,0,0,0.6); }
  #lightbox .lb-caption { margin-top: 10px; text-align: center; max-width: 92vw; }
  #lightbox .lb-name { font-size: 14px; color: #f0f0f0; word-break: break-all; }
  #lightbox .lb-group { font-size: 12px; color: #9a9a9a; margin-top: 2px; }
  #lightbox .lb-btn { position: fixed; top: 50%; transform: translateY(-50%);
                      background: rgba(40,40,40,0.85); color: #eee; border: 1px solid #555;
                      font-size: 28px; line-height: 1; width: 52px; height: 64px;
                      border-radius: 6px; cursor: pointer; user-select: none; }
  #lightbox .lb-btn:hover { background: rgba(70,70,70,0.95); }
  #lightbox .lb-btn[disabled] { opacity: 0.3; cursor: default; }
  #lightbox #lb-prev { left: 16px; }
  #lightbox #lb-next { right: 16px; }
  #lightbox #lb-close { position: fixed; top: 14px; right: 18px; width: 44px; height: 44px;
                        font-size: 30px; border-radius: 6px; }
"""

_PAGE_JS = """
  const REFRESH_MS = %(refresh_ms)d;
  let rendered = 0, errored = 0;
  const expected = document.querySelectorAll('img[data-key]').length;

  function paint() {
    document.getElementById('rendered').textContent = rendered;
    document.getElementById('pending').textContent = expected - rendered;
    document.getElementById('expected').textContent = expected;
  }

  // First-resolution accounting: count each img once on its first load/error so a
  // 30s re-fetch of an already-good tile doesn't double-count.
  function onLoad(img) {
    img.closest('figure').classList.remove('pending');
    if (!img.dataset.seen) { img.dataset.seen = '1'; rendered++; paint(); }
    else if (img.dataset.state === 'pending') {
      img.dataset.state = 'ok'; rendered++; errored--; paint();  // appeared since last cycle
    }
  }
  function onError(img) {
    img.closest('figure').classList.add('pending');
    if (!img.dataset.seen) { img.dataset.seen = '1'; img.dataset.state = 'pending'; errored++; }
    else if (img.dataset.state === 'ok') {
      img.dataset.state = 'pending'; rendered--; errored++; paint();  // disappeared (rare)
    }
  }

  // Re-fetch every img with a new cache-bust token so freshly-uploaded renders from
  // EITHER box appear. No full-page reload — scroll position is preserved.
  function refresh() {
    const cb = Date.now();
    document.querySelectorAll('img[data-key]').forEach(img => {
      img.src = img.dataset.key + '?cb=' + cb;
    });
  }

  paint();
  setInterval(refresh, REFRESH_MS);

  // ── Lightbox ────────────────────────────────────────────────────────────────
  // Navigation list is recomputed live each step from the DOM (rendered tiles only,
  // in document order). Nothing here caches img elements across the 30s refresh, and
  // clicks are delegated from a stable parent, so re-fetching srcs never orphans it.
  const lb = document.getElementById('lightbox');
  const lbImg = document.getElementById('lb-img');
  const lbName = document.getElementById('lb-name');
  const lbGroup = document.getElementById('lb-group');
  const lbPrev = document.getElementById('lb-prev');
  const lbNext = document.getElementById('lb-next');
  let lbKey = null;  // data-key of the currently shown image (identity survives refresh)

  // Rendered tiles in document order: a figure is rendered iff it lacks .pending.
  function renderedImgs() {
    return Array.from(document.querySelectorAll('figure:not(.pending) > img[data-key]'));
  }
  function indexOfKey(imgs, key) {
    return imgs.findIndex(im => im.dataset.key === key);
  }

  function showAt(imgs, idx) {
    if (idx < 0 || idx >= imgs.length) return;
    const img = imgs[idx];
    lbKey = img.dataset.key;
    lbImg.src = img.currentSrc || img.src;  // reuse the already-cache-busted, loaded src
    lbImg.alt = img.alt;
    lbName.textContent = img.alt;
    lbGroup.textContent = img.dataset.group || '';
    lbPrev.disabled = idx <= 0;            // clamp at the ends
    lbNext.disabled = idx >= imgs.length - 1;
  }

  function openLightbox(img) {
    const imgs = renderedImgs();
    const idx = indexOfKey(imgs, img.dataset.key);
    if (idx < 0) return;  // not a rendered tile (e.g. became pending) — nothing to show
    showAt(imgs, idx);
    lb.classList.add('open');
  }
  function closeLightbox() { lb.classList.remove('open'); lbKey = null; }
  function step(delta) {
    if (lbKey === null) return;
    const imgs = renderedImgs();
    let idx = indexOfKey(imgs, lbKey);
    if (idx < 0) idx = 0;  // current tile dropped out (rare); land on the first
    showAt(imgs, idx + delta);
  }

  // Delegate tile clicks from document — only RENDERED images open the lightbox.
  document.addEventListener('click', (e) => {
    const img = e.target.closest('figure:not(.pending) > img[data-key]');
    if (img) { openLightbox(img); }
  });
  // Backdrop click closes; clicks on the image/controls do not bubble to a close.
  lb.addEventListener('click', (e) => { if (e.target === lb) closeLightbox(); });
  document.getElementById('lb-close').addEventListener('click', closeLightbox);
  lbPrev.addEventListener('click', () => step(-1));
  lbNext.addEventListener('click', () => step(1));

  document.addEventListener('keydown', (e) => {
    if (!lb.classList.contains('open')) return;
    if (e.key === 'Escape') { closeLightbox(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
  });
"""


def _img_tag(asset: Asset, base: str, cache_bust: str) -> str:
    url = f"{base}/{asset.key}"
    safe_url = html.escape(url, quote=True)
    safe_name = html.escape(asset.filename)
    safe_group = html.escape(f"{asset.genre} / {asset.world} / {asset.kind}", quote=True)
    return (
        '<figure>'
        f'<img loading="lazy" data-key="{safe_url}" data-group="{safe_group}" '
        f'src="{safe_url}?cb={cache_bust}" '
        'onload="onLoad(this)" onerror="onError(this)" '
        f'alt="{safe_name}">'
        f'<figcaption>{safe_name}</figcaption>'
        '</figure>'
    )


def build_html(assets: list[Asset], base: str) -> tuple[str, int]:
    """Render the full self-contained page. Returns (html, group_count)."""
    cache_bust = str(int(time.time()))

    # genre -> world -> kind -> [assets]
    tree: dict[str, dict[str, dict[str, list[Asset]]]] = {}
    for a in assets:
        tree.setdefault(a.genre, {}).setdefault(a.world, {}).setdefault(a.kind, []).append(a)

    body: list[str] = []
    group_count = 0
    for genre in sorted(tree):
        body.append(f'<h2 class="genre">{html.escape(genre)}</h2>')
        for world in sorted(tree[genre]):
            body.append(f'<h3 class="world">{html.escape(world)}</h3>')
            for kind in sorted(tree[genre][world]):
                group_count += 1
                kind_assets = sorted(tree[genre][world][kind], key=lambda a: a.filename)
                body.append(f'<h4 class="kind">{html.escape(kind)} ({len(kind_assets)})</h4>')
                body.append('<div class="grid">')
                body.extend(_img_tag(a, base, cache_bust) for a in kind_assets)
                body.append('</div>')

    generated = time.strftime("%Y-%m-%d %H:%M:%S")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SideQuest R2 Preview</title>
<style>{_PAGE_CSS}</style>
</head>
<body>
<header>
  <h1>SideQuest R2 Preview</h1>
  <span class="counter">
    <b id="rendered">0</b> rendered /
    <span class="pending" id="pending">0</span> pending /
    <span id="expected">0</span> expected
  </span>
  <span class="meta">base: {html.escape(base)} &middot; generated {generated} &middot;
    auto-refresh {REFRESH_SECONDS}s</span>
</header>
{chr(10).join(body)}
<div id="lightbox" role="dialog" aria-modal="true" aria-label="Image preview">
  <button id="lb-close" class="lb-btn" title="Close (Esc)" aria-label="Close">&times;</button>
  <button id="lb-prev" class="lb-btn" title="Previous (&larr;)" aria-label="Previous">&lsaquo;</button>
  <button id="lb-next" class="lb-btn" title="Next (&rarr;)" aria-label="Next">&rsaquo;</button>
  <div class="lb-stage">
    <img id="lb-img" alt="">
    <div class="lb-caption">
      <div class="lb-name" id="lb-name"></div>
      <div class="lb-group" id="lb-group"></div>
    </div>
  </div>
</div>
<script>{_PAGE_JS % {"refresh_ms": REFRESH_SECONDS * 1000}}</script>
</body>
</html>
"""
    return page, group_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--genre", help="Only this pack (directory name under genre_packs/).")
    parser.add_argument("--world", help="Only this world (directory name under worlds/).")
    parser.add_argument("--kind", choices=["portraits", "poi"], help="Only this asset kind.")
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help=f"Output dir (default: {DEFAULT_OUT})."
    )
    parser.add_argument(
        "--open", action="store_true", help="Open the page in the OS viewer when done (macOS)."
    )
    args = parser.parse_args()

    base = _asset_base_url()

    assets, per_kind = collect_assets()
    if args.genre:
        assets = [a for a in assets if a.genre == args.genre]
    if args.world:
        assets = [a for a in assets if a.world == args.world]
    if args.kind:
        assets = [a for a in assets if a.kind == args.kind]

    if not assets:
        print("No expected assets matched the given filters.", file=sys.stderr)
        return 1

    page, group_count = build_html(assets, base)

    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / "r2_preview.html"
    out_path.write_text(page, encoding="utf-8")

    # Per-kind breakdown for the assets that survived filtering.
    kinds_written: dict[str, int] = {}
    for a in assets:
        kinds_written[a.kind] = kinds_written.get(a.kind, 0) + 1
    breakdown = ", ".join(f"{k}={v}" for k, v in sorted(kinds_written.items()))

    print(f"[OK] {out_path}")
    print(
        f"Wrote {len(assets)} expected asset(s) across {group_count} group(s) "
        f"({breakdown}). CDN base: {base}"
    )

    if args.open and sys.platform == "darwin":
        subprocess.run(["open", str(out_path)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
