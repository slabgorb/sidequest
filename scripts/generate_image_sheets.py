#!/usr/bin/env python3
"""Generate labeled contact sheets for quick visual review of pack/world assets.

Discovers every image group in the content tree and renders one grid sheet per
group. A "group" is any directory of PNGs at either:

    genre_packs/<pack>/images/<kind>/                     (pack-level, e.g. portraits)
    genre_packs/<pack>/worlds/<world>/assets/<kind>/      (world-level, e.g. poi)

Each thumbnail is captioned with its filename so you can map a face/landscape
back to its manifest entry at a glance.

Usage:
    python3 scripts/generate_image_sheets.py                      # all groups
    python3 scripts/generate_image_sheets.py --genre pulp_noir
    python3 scripts/generate_image_sheets.py --kind portraits
    python3 scripts/generate_image_sheets.py --world coyote_star --kind poi
    python3 scripts/generate_image_sheets.py --open               # macOS: open sheets when done

Output defaults to image_sheets/ at the repo root (gitignored). Run from the
daemon venv so PIL is available:
    cd sidequest-daemon && uv run python ../scripts/generate_image_sheets.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from render_common import GENRE_PACKS_DIR

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = _ROOT / "image_sheets"

# Candidate fonts, tried in order; falls back to PIL's bundled default.
_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
)


@dataclass(frozen=True)
class Group:
    pack: str
    world: str | None  # None for pack-level groups
    kind: str
    directory: Path

    @property
    def label(self) -> str:
        scope = f"{self.pack}" if self.world is None else f"{self.pack} / {self.world}"
        return f"{scope}  ·  {self.kind}"

    @property
    def out_stem(self) -> str:
        scope = self.pack if self.world is None else f"{self.pack}__{self.world}"
        return f"{scope}__{self.kind}"


def discover_groups(packs_dir: Path) -> list[Group]:
    """Find every directory of PNGs under images/<kind> or worlds/*/assets/<kind>."""
    groups: list[Group] = []
    for pack_dir in sorted(p for p in packs_dir.iterdir() if p.is_dir()):
        pack = pack_dir.name

        # Pack-level: images/<kind>/
        images_dir = pack_dir / "images"
        if images_dir.is_dir():
            for kind_dir in sorted(d for d in images_dir.iterdir() if d.is_dir()):
                if _has_png(kind_dir):
                    groups.append(Group(pack, None, kind_dir.name, kind_dir))

        # World-level: worlds/<world>/assets/<kind>/
        worlds_dir = pack_dir / "worlds"
        if worlds_dir.is_dir():
            for world_dir in sorted(d for d in worlds_dir.iterdir() if d.is_dir()):
                assets_dir = world_dir / "assets"
                if not assets_dir.is_dir():
                    continue
                for kind_dir in sorted(d for d in assets_dir.iterdir() if d.is_dir()):
                    if _has_png(kind_dir):
                        groups.append(Group(pack, world_dir.name, kind_dir.name, kind_dir))
    return groups


def _has_png(directory: Path) -> bool:
    return any(directory.glob("*.png"))


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10
    except TypeError:
        return ImageFont.load_default()


def _fit_caption(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """Truncate text with an ellipsis so it fits within max_width pixels."""
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "…"
    while text and draw.textlength(text + ellipsis, font=font) > max_width:
        text = text[:-1]
    return text + ellipsis


def build_sheet(group: Group, *, thumb: int, cols: int, bg: str) -> Image.Image:
    paths = sorted(group.directory.glob("*.png"))
    bg_rgb = ImageColor.getrgb(bg)
    # Light backgrounds get dark text and vice versa.
    fg = (30, 30, 30) if sum(bg_rgb) > 384 else (235, 235, 235)
    muted = (120, 120, 120) if sum(bg_rgb) > 384 else (160, 160, 160)

    cols = max(1, min(cols, len(paths)))
    rows = -(-len(paths) // cols)  # ceil

    pad = 12
    caption_h = 22
    cell_w = thumb + pad
    cell_h = thumb + caption_h + pad
    title_h = 56

    sheet_w = cols * cell_w + pad
    sheet_h = title_h + rows * cell_h + pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), bg_rgb)
    draw = ImageDraw.Draw(sheet)

    title_font = _load_font(26)
    cap_font = _load_font(14)

    draw.text((pad, pad), group.label, fill=fg, font=title_font)
    draw.text(
        (pad, pad + 32),
        f"{len(paths)} image{'s' if len(paths) != 1 else ''}  ·  {group.directory}",
        fill=muted,
        font=cap_font,
    )

    for idx, path in enumerate(paths):
        col, row = idx % cols, idx // cols
        x0 = pad + col * cell_w
        y0 = title_h + row * cell_h

        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((thumb, thumb), Image.LANCZOS)
        except Exception as exc:  # noqa: BLE001 - a bad file shouldn't kill the sheet
            draw.rectangle([x0, y0, x0 + thumb, y0 + thumb], outline=(200, 60, 60), width=2)
            draw.text((x0 + 4, y0 + 4), f"ERR\n{exc}", fill=(200, 60, 60), font=cap_font)
            continue

        # Center the thumbnail in its square slot.
        off_x = x0 + (thumb - im.width) // 2
        off_y = y0 + (thumb - im.height) // 2
        sheet.paste(im, (off_x, off_y))

        caption = _fit_caption(draw, path.stem, cap_font, thumb)
        cap_w = draw.textlength(caption, font=cap_font)
        draw.text(
            (x0 + (thumb - cap_w) / 2, y0 + thumb + 4),
            caption,
            fill=fg,
            font=cap_font,
        )

    return sheet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--genre", help="Only this pack (directory name under genre_packs/).")
    parser.add_argument("--world", help="Only this world (directory name under worlds/).")
    parser.add_argument("--kind", help="Only this asset kind (portraits, poi, creatures, …).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Output dir (default: {DEFAULT_OUT}).")
    parser.add_argument("--thumb", type=int, default=256, help="Thumbnail box size in px (default: 256).")
    parser.add_argument("--cols", type=int, default=5, help="Max columns (default: 5).")
    parser.add_argument("--bg", default="#1b1b1b", help="Background color (default: #1b1b1b).")
    parser.add_argument("--open", action="store_true", help="Open sheets with the OS viewer when done (macOS).")
    args = parser.parse_args()

    groups = discover_groups(GENRE_PACKS_DIR)
    if args.genre:
        groups = [g for g in groups if g.pack == args.genre]
    if args.world:
        groups = [g for g in groups if g.world == args.world]
    if args.kind:
        groups = [g for g in groups if g.kind == args.kind]

    if not groups:
        print("No matching image groups found.", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for group in groups:
        sheet = build_sheet(group, thumb=args.thumb, cols=args.cols, bg=args.bg)
        out_path = args.out / f"{group.out_stem}.png"
        sheet.save(out_path)
        print(f"[OK] {group.label}  ->  {out_path}")
        written.append(out_path)

    print(f"\nWrote {len(written)} sheet(s) to {args.out}")
    if args.open and sys.platform == "darwin" and written:
        subprocess.run(["open", *map(str, written)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
