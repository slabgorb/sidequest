"""Automated still-grabber for LoRA training datasets.

Downloads a video and extracts visually meaningful stills, filtering out
black screens, fades, wipes, duplicates, and blurry frames.

Usage:
    python3 scripts/grab_stills.py URL -o output_dir/
    python3 scripts/grab_stills.py URL -o output_dir/ --interval 2
    python3 scripts/grab_stills.py URL -o output_dir/ --max-stills 200
    python3 scripts/grab_stills.py URL -o output_dir/ --min-resolution 720

Requires: yt-dlp, ffmpeg, Pillow, numpy
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

log = logging.getLogger(__name__)

# --- Quality filters ---

# Frames with mean pixel value below this are "black" (0-255 scale)
BLACK_THRESHOLD = 15

# Frames with mean pixel value above this are "white" (blown out)
WHITE_THRESHOLD = 245

# Frames with std dev below this are "flat" (solid color, fade, wipe)
FLAT_THRESHOLD = 20

# Laplacian variance below this = blurry
BLUR_THRESHOLD = 50

# Perceptual hash: frames within this hamming distance are duplicates
DUPE_HASH_THRESHOLD = 8


def download_video(url: str, output_dir: Path) -> Path:
    """Download video with yt-dlp, return path to file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title)s.%(ext)s")

    log.info("Downloading: %s", url)
    result = subprocess.run(
        [
            "yt-dlp",
            "--no-playlist",
            "-f", "bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/best[height>=720]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            url,
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")

    # Find the downloaded file
    mp4_files = sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4_files:
        # Check for other video formats
        video_files = sorted(
            (p for p in output_dir.iterdir() if p.suffix in {".mp4", ".mkv", ".webm"}),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not video_files:
            raise RuntimeError(f"No video file found in {output_dir}")
        return video_files[0]

    log.info("Downloaded: %s", mp4_files[0].name)
    return mp4_files[0]


def extract_frames(video_path: Path, output_dir: Path, interval: float = 1.0) -> list[Path]:
    """Extract frames from video at given interval using ffmpeg."""
    frames_dir = output_dir / "raw_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    log.info("Extracting frames every %.1fs...", interval)
    result = subprocess.run(
        [
            "ffmpeg", "-i", str(video_path),
            "-vf", f"fps=1/{interval}",
            "-q:v", "2",  # High JPEG quality
            str(frames_dir / "frame_%06d.jpg"),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    log.info("Extracted %d raw frames", len(frames))
    return frames


def is_black(img_array: np.ndarray) -> bool:
    """Check if frame is mostly black."""
    return img_array.mean() < BLACK_THRESHOLD


def is_white(img_array: np.ndarray) -> bool:
    """Check if frame is mostly white/blown out."""
    return img_array.mean() > WHITE_THRESHOLD


def is_flat(img_array: np.ndarray) -> bool:
    """Check if frame is flat (solid color, fade, wipe, title card)."""
    return img_array.std() < FLAT_THRESHOLD


def is_blurry(img: Image.Image) -> bool:
    """Check if frame is blurry using Laplacian variance."""
    gray = img.convert("L")
    laplacian = gray.filter(ImageFilter.Kernel(
        size=(3, 3),
        kernel=[-1, -1, -1, -1, 8, -1, -1, -1, -1],
        scale=1,
        offset=128,
    ))
    variance = np.array(laplacian).var()
    return variance < BLUR_THRESHOLD


def perceptual_hash(img: Image.Image, hash_size: int = 16) -> int:
    """Compute a perceptual hash (average hash) for deduplication."""
    resized = img.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(resized)
    mean = pixels.mean()
    bits = (pixels > mean).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming_distance(h1: int, h2: int) -> int:
    """Count differing bits between two hashes."""
    return bin(h1 ^ h2).count("1")


def filter_frames(
    frames: list[Path],
    min_resolution: int = 720,
) -> list[Path]:
    """Filter frames for quality, removing bad captures."""
    kept = []
    seen_hashes: list[int] = []

    stats = {"black": 0, "white": 0, "flat": 0, "blurry": 0, "dupe": 0, "small": 0, "kept": 0}

    for frame_path in frames:
        img = Image.open(frame_path)

        # Resolution check
        if min(img.size) < min_resolution:
            stats["small"] += 1
            continue

        img_array = np.array(img)

        if is_black(img_array):
            stats["black"] += 1
            continue

        if is_white(img_array):
            stats["white"] += 1
            continue

        if is_flat(img_array):
            stats["flat"] += 1
            continue

        if is_blurry(img):
            stats["blurry"] += 1
            continue

        # Deduplication via perceptual hash
        ph = perceptual_hash(img)
        is_dupe = False
        for existing_hash in seen_hashes:
            if hamming_distance(ph, existing_hash) < DUPE_HASH_THRESHOLD:
                is_dupe = True
                break

        if is_dupe:
            stats["dupe"] += 1
            continue

        seen_hashes.append(ph)
        kept.append(frame_path)
        stats["kept"] += 1

    log.info(
        "Filter results: %d kept, %d black, %d white, %d flat, %d blurry, %d dupe, %d small (of %d total)",
        stats["kept"], stats["black"], stats["white"], stats["flat"],
        stats["blurry"], stats["dupe"], stats["small"], len(frames),
    )
    return kept


def main():
    parser = argparse.ArgumentParser(description="Grab stills from video for LoRA training")
    parser.add_argument("url", help="Video URL (YouTube, Vimeo, etc.)")
    parser.add_argument("-o", "--output", required=True, help="Output directory for stills")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Seconds between frame captures (default: 1.0)")
    parser.add_argument("--max-stills", type=int, default=500,
                        help="Maximum number of stills to keep (default: 500)")
    parser.add_argument("--min-resolution", type=int, default=720,
                        help="Minimum frame dimension in pixels (default: 720)")
    parser.add_argument("--keep-video", action="store_true",
                        help="Keep downloaded video file")
    parser.add_argument("--keep-raw", action="store_true",
                        help="Keep raw unfiltered frames")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="sq-stills-") as tmpdir:
        tmp = Path(tmpdir)

        # Step 1: Download
        start = time.monotonic()
        video_path = download_video(args.url, tmp)
        log.info("Download took %.1fs", time.monotonic() - start)

        # Step 2: Extract frames
        extract_start = time.monotonic()
        raw_frames = extract_frames(video_path, tmp, interval=args.interval)
        log.info("Extraction took %.1fs", time.monotonic() - extract_start)

        if not raw_frames:
            log.error("No frames extracted!")
            sys.exit(1)

        # Step 3: Filter
        filter_start = time.monotonic()
        good_frames = filter_frames(raw_frames, min_resolution=args.min_resolution)
        log.info("Filtering took %.1fs", time.monotonic() - filter_start)

        # Step 4: Limit and copy to output
        if len(good_frames) > args.max_stills:
            # Evenly sample from the filtered set
            step = len(good_frames) / args.max_stills
            indices = [int(i * step) for i in range(args.max_stills)]
            good_frames = [good_frames[i] for i in indices]
            log.info("Sampled down to %d stills", len(good_frames))

        stills_dir = output_dir / "stills"
        stills_dir.mkdir(parents=True, exist_ok=True)

        for i, frame_path in enumerate(good_frames):
            dest = stills_dir / f"still_{i:04d}.jpg"
            shutil.copy2(frame_path, dest)

        # Keep video if requested
        if args.keep_video:
            shutil.copy2(video_path, output_dir / video_path.name)

        # Keep raw frames if requested
        if args.keep_raw:
            raw_dest = output_dir / "raw_frames"
            raw_dest.mkdir(exist_ok=True)
            for f in raw_frames:
                shutil.copy2(f, raw_dest / f.name)

    total_time = time.monotonic() - start
    print(f"\nStill grab complete:")
    print(f"  Source: {args.url}")
    print(f"  Stills: {len(good_frames)} (in {stills_dir})")
    print(f"  Total time: {total_time:.1f}s")


if __name__ == "__main__":
    main()
