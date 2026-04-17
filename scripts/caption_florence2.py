"""Standalone Florence-2 captioning — runs in ai-toolkit's venv.

Uses transformers 4.57.3 (ai-toolkit pinned) where Florence-2 remote code
is compatible. Writes .txt caption files alongside each image.

Usage (run with ai-toolkit's Python):
    /path/to/ai-toolkit/.venv/bin/python scripts/caption_florence2.py /path/to/images/
    /path/to/ai-toolkit/.venv/bin/python scripts/caption_florence2.py /path/to/images/ --trigger ukiyoe_style
    /path/to/ai-toolkit/.venv/bin/python scripts/caption_florence2.py /path/to/images/ --metadata /path/to/metadata/
    /path/to/ai-toolkit/.venv/bin/python scripts/caption_florence2.py /path/to/images/ --overwrite

Why standalone? Florence-2's remote model code is incompatible with transformers 5.x
(the daemon's version). Until Microsoft publishes a native-compatible Florence-2,
captioning runs in ai-toolkit's venv which pins transformers 4.57.3.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

log = logging.getLogger(__name__)

MODEL_ID = "multimodalart/Florence-2-large-no-flash-attn"

CAPTION_MODES = {
    "detailed": "<DETAILED_CAPTION>",
    "tags": "<MORE_DETAILED_CAPTION>",
    "brief": "<CAPTION>",
}

MODE_MAX_TOKENS = {
    "detailed": 1024,
    "tags": 1024,
    "brief": 256,
}


def load_model(device: str = "mps"):
    """Load Florence-2 model and processor."""
    dtype = torch.float16 if device == "mps" else torch.float32
    log.info("Loading Florence-2 on %s...", device)
    start = time.monotonic()

    # NOTE: Florence-2's remote model code needs _supports_sdpa = False on
    # PreTrainedModel subclasses for transformers >= 4.50. The cached model
    # file at ~/.cache/huggingface/hub/models--multimodalart--Florence-2-large-
    # no-flash-attn/.../modeling_florence2.py must be patched once. If loading
    # fails with '_supports_sdpa' error, add `_supports_sdpa = False` to both
    # Florence2LanguagePreTrainedModel and Florence2PreTrainedModel classes.
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=dtype, trust_remote_code=True,
    ).to(device)

    processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)

    elapsed = time.monotonic() - start
    log.info("Florence-2 loaded (%.1fs)", elapsed)
    return model, processor, dtype


def caption_image(
    model, processor, image_path: Path, mode: str, trigger_word: str,
    device: str, dtype,
) -> str:
    """Generate a caption for a single image."""
    image = Image.open(image_path).convert("RGB")
    task_prompt = CAPTION_MODES[mode]
    max_tokens = MODE_MAX_TOKENS[mode]

    inputs = processor(
        text=task_prompt, images=image, return_tensors="pt",
    ).to(device, dtype)

    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=max_tokens,
        num_beams=3,
    )

    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(
        generated_text, task=task_prompt, image_size=(image.width, image.height),
    )

    caption = parsed[task_prompt]
    caption = caption.replace("The image shows ", "")

    if trigger_word:
        caption = f"{caption} {trigger_word}"

    return caption


def enrich_with_metadata(image_dir: Path, metadata_dir: Path) -> int:
    """Merge structured metadata into captions."""
    enriched = 0
    for txt_path in sorted(image_dir.glob("*.txt")):
        meta_path = metadata_dir / f"{txt_path.stem}.json"
        if not meta_path.exists():
            continue

        caption = txt_path.read_text().strip()
        meta = json.loads(meta_path.read_text())

        parts = []
        if meta.get("artists"):
            parts.append(f"by {meta['artists'][0]}")
        if meta.get("dated"):
            parts.append(meta["dated"])
        if meta.get("title"):
            parts.append(f'"{meta["title"]}"')

        if parts:
            prefix = ", ".join(parts)
            txt_path.write_text(f"{prefix}. {caption}")
            enriched += 1

    return enriched


def main():
    parser = argparse.ArgumentParser(description="Caption images with Florence-2")
    parser.add_argument("directory", help="Directory of images to caption")
    parser.add_argument("--mode", default="detailed", choices=["detailed", "tags", "brief"])
    parser.add_argument("--trigger", help="Trigger word to append")
    parser.add_argument("--metadata", help="JSON metadata dir for enrichment")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing captions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    image_dir = Path(args.directory).resolve()
    if not image_dir.is_dir():
        log.error("Not a directory: %s", image_dir)
        sys.exit(1)

    image_files = sorted(
        p for p in image_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    log.info("Found %d images in %s", len(image_files), image_dir)

    existing = sum(1 for p in image_files if p.with_suffix(".txt").exists())
    to_caption = len(image_files) if args.overwrite else len(image_files) - existing

    if args.dry_run:
        print(f"\nDry run:")
        print(f"  Images: {len(image_files)}")
        print(f"  Already captioned: {existing}")
        print(f"  Would caption: {to_caption}")
        print(f"  Mode: {args.mode}")
        print(f"  Trigger: {args.trigger or '(none)'}")
        return

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model, processor, dtype = load_model(device)

    completed = 0
    skipped = 0
    failed = 0
    start_time = time.monotonic()

    for i, img_path in enumerate(image_files, 1):
        txt_path = img_path.with_suffix(".txt")

        if txt_path.exists() and not args.overwrite:
            skipped += 1
            continue

        try:
            img_start = time.monotonic()
            caption = caption_image(
                model, processor, img_path, args.mode,
                args.trigger or "", device, dtype,
            )
            txt_path.write_text(caption)
            elapsed = time.monotonic() - img_start
            completed += 1
            log.info("[%d/%d] %s (%.1fs)", i, len(image_files), img_path.name, elapsed)
        except Exception as e:
            failed += 1
            log.error("[%d/%d] %s FAILED: %s", i, len(image_files), img_path.name, e)

    total_time = time.monotonic() - start_time

    print(f"\nCaptioning complete:")
    print(f"  Completed: {completed}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Elapsed: {total_time:.1f}s")
    if completed > 0:
        print(f"  Avg: {total_time / completed:.1f}s per image")

    if args.metadata:
        metadata_dir = Path(args.metadata).resolve()
        if metadata_dir.is_dir():
            enriched = enrich_with_metadata(image_dir, metadata_dir)
            print(f"  Enriched {enriched} captions with metadata")
        else:
            log.error("Metadata dir not found: %s", metadata_dir)


if __name__ == "__main__":
    main()
