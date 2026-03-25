#!/usr/bin/env python3
"""
Individual Portrait Generator for Pennyfarthing Themes

Generates individual portraits per theme on M3 Max (MPS).
Supports multiple engines: SDXL (Stable Diffusion XL) and Flux.
Reads visual prompts from theme YAML files in three locations:
  - Package:  packages/themes-*/themes/ (output to packages/themes-*/portraits/)
  - Built-in: pennyfarthing-dist/personas/themes/ (output to pennyfarthing-dist/personas/portraits/)
  - Custom:   .claude/pennyfarthing/themes/ (takes precedence, output to built-in portraits dir)

Output: {portraits-dir}/{theme}/{slug}-{OCEAN}.png (512x512px each)

Usage:
    python3 scripts/generate-portraits.py [--dry-run] [--theme THEME] [--engine ENGINE]
    python3 scripts/generate-portraits.py --engine flux --theme gilligans-island --dry-run
    python3 scripts/generate-portraits.py --engine sdxl --role ba --skip-existing

Freeform prompt mode (bypasses theme YAML):
    python3 scripts/generate-portraits.py --prompt "a steampunk bicycle logo" --output logo.png
    python3 scripts/generate-portraits.py --prompt "robot on a penny-farthing" --output bot.png --no-style-suffix
    python3 scripts/generate-portraits.py --prompt "cat riding a bicycle" --output cat.png --style "flat vector logo, minimal, bold colors"
    python3 scripts/generate-portraits.py --prompt "cat riding a bicycle" --output cat.png --engine flux --seed 99
"""

import argparse
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

# Suppress progress bars before importing torch/diffusers
os.environ["TQDM_DISABLE"] = "1"

# Suppress CUDA warnings on MPS (Apple Silicon)
warnings.filterwarnings("ignore", message=".*CUDA is not available.*")

try:
    import yaml
except ImportError:
    print("Missing PyYAML: pip install pyyaml")
    sys.exit(1)

try:
    import torch
    from diffusers import DPMSolverMultistepScheduler, StableDiffusionXLPipeline
    from diffusers.utils import logging as diffusers_logging
    from PIL import Image
    HAS_TORCH = True
    # Suppress diffusers progress bar
    diffusers_logging.disable_progress_bar()
except ImportError as e:
    HAS_TORCH = False
    TORCH_ERROR = str(e)

# Native Flux repo (Black Forest Labs) — loaded lazily when --engine flux is used
HAS_FLUX = False
FLUX_ERROR = ""
FLUX_PROJECT_DIR = Path.home() / "Projects" / "flux"

# CLIP tokenizer for accurate token counting (optional - falls back to word estimate)
try:
    from transformers import CLIPTokenizer
    CLIP_TOKENIZER = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
    HAS_CLIP_TOKENIZER = True
except Exception:
    CLIP_TOKENIZER = None
    HAS_CLIP_TOKENIZER = False


# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()

# Find PROJECT_ROOT by walking up until we find pennyfarthing-dist at the expected level
# Script lives at: {PROJECT_ROOT}/pennyfarthing-dist/scripts/portraits/generate-portraits.py
def _find_project_root() -> Path:
    """Find project root by looking for pennyfarthing-dist or .git marker."""
    current = SCRIPT_DIR
    # Walk up from portraits/ -> scripts/ -> pennyfarthing-dist/ -> PROJECT_ROOT
    for _ in range(5):  # Safety limit
        # Check if this looks like the project root
        if (current / "pennyfarthing-dist" / "personas" / "themes").exists():
            return current
        if (current / ".git").exists() and (current / "pennyfarthing-dist").exists():
            return current
        current = current.parent
    # Fallback: assume old structure (script in {root}/scripts/portraits/)
    return SCRIPT_DIR.parent.parent

PROJECT_ROOT = _find_project_root()
BUILTIN_THEMES_DIR = PROJECT_ROOT / "pennyfarthing-dist" / "personas" / "themes"
CUSTOM_THEMES_DIR = PROJECT_ROOT / ".claude" / "pennyfarthing" / "themes"
BUILTIN_OUTPUT_DIR = PROJECT_ROOT / "pennyfarthing-dist" / "personas" / "portraits"
PACKAGES_DIR = PROJECT_ROOT / "packages"
# Engine configurations
ENGINES = {
    "sdxl": {
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "generation_size": 1024,
        "output_size": 512,
        "num_inference_steps": 30,
        "guidance_scale": 7.5,
        "max_tokens": 77,
        "supports_negative_prompt": True,
    },
    "flux": {
        "model_name": "flux-schnell",
        "generation_size": 1024,
        "output_size": 512,
        "num_inference_steps": 4,
        "guidance_scale": 3.5,
        "max_tokens": 256,
        "supports_negative_prompt": False,
    },
    "flux-dev": {
        "model_name": "flux-dev",
        "generation_size": 1024,
        "output_size": 512,
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "max_tokens": 256,
        "supports_negative_prompt": False,
    },
}

DEFAULT_ENGINE = "sdxl"

# Role order for the 11 agents
ROLES = [
    "orchestrator", "sm", "tea", "dev", "reviewer",
    "architect", "pm", "tech-writer", "ux-designer", "devops", "ba"
]

# Default style suffix (visual description comes first for emphasis)
# Themes can override this by setting 'portrait_style' in their theme metadata
DEFAULT_STYLE_SUFFIX = ", traditional woodcut portrait bust, black and white, bold linework, crosshatching, medieval style"


def to_slug(name: str) -> str:
    """Convert a name to URL-safe slug (lowercase kebab-case)."""
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = re.sub(r'^-|-$', '', slug)
    return slug


def count_clip_tokens(text: str) -> int:
    """Count CLIP tokens in text. Uses actual tokenizer if available, else estimates."""
    if HAS_CLIP_TOKENIZER and CLIP_TOKENIZER:
        tokens = CLIP_TOKENIZER.encode(text)
        return len(tokens)
    else:
        # Fallback: estimate ~1.3 tokens per word (empirical average for CLIP)
        return int(len(text.split()) * 1.3)


def truncate_prompt_to_clip_limit(visual: str, style_suffix: str, max_tokens: int = 77) -> tuple[str, bool]:
    """Truncate prompt to fit within CLIP token limit.

    Strategy: Prioritize the visual description over the style suffix.
    If combined prompt exceeds limit, progressively trim the visual description.

    Returns:
        tuple: (truncated_prompt, was_truncated)
    """
    combined = f"{visual}{style_suffix}"
    token_count = count_clip_tokens(combined)

    if token_count <= max_tokens:
        return combined, False

    # Need to truncate - prioritize visual by trimming words from end
    visual_words = visual.split()
    style_tokens = count_clip_tokens(style_suffix)
    available_for_visual = max_tokens - style_tokens - 2  # Buffer for safety

    # Binary search for optimal truncation point
    while visual_words and count_clip_tokens(" ".join(visual_words)) > available_for_visual:
        visual_words = visual_words[:-1]

    truncated_visual = " ".join(visual_words)
    if truncated_visual and not truncated_visual.endswith((",", ".", ";")):
        truncated_visual = truncated_visual.rstrip(",. ")

    return f"{truncated_visual}{style_suffix}", True


def ocean_suffix(ocean: dict) -> str:
    """Generate OCEAN suffix from scores (e.g., '54432' for O=5,C=4,E=4,A=3,N=2)."""
    return f"{ocean['O']}{ocean['C']}{ocean['E']}{ocean['A']}{ocean['N']}"


def generate_portrait_filename(short_name: str, ocean: dict) -> str:
    """Generate portrait filename from shortName and OCEAN scores.

    Format: {shortName-slug}-{OCEAN}.png (e.g., 'yoda-54242.png')
    """
    slug = to_slug(short_name)
    return f"{slug}-{ocean_suffix(ocean)}.png"


def parse_theme_file(theme_path: Path) -> dict:
    """Parse theme YAML file to extract visual prompts for each agent."""
    with open(theme_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    theme_metadata = data.get("theme", {})
    result = {
        "theme": theme_path.stem,
        "source": theme_metadata.get("source", ""),
        "portrait_prefix": theme_metadata.get("portrait_prefix", None),
        "portrait_style": theme_metadata.get("portrait_style", None),
        "negative_prompt": theme_metadata.get("negative_prompt", None),
        "characters": {}
    }

    agents = data.get("agents", {})
    for role, agent_data in agents.items():
        if isinstance(agent_data, dict) and "visual" in agent_data:
            # Get shortName, fallback to first word of character name
            character = agent_data.get("character", role)
            short_name = agent_data.get("shortName", character.split()[0])
            ocean = agent_data.get("ocean", {})

            # Generate filename if OCEAN scores are available
            if ocean and all(k in ocean for k in ['O', 'C', 'E', 'A', 'N']):
                filename = generate_portrait_filename(short_name, ocean)
            else:
                # Fallback to role-based name if no OCEAN scores
                filename = f"{role}.png"

            result["characters"][role] = {
                "name": character,
                "shortName": short_name,
                "visual": agent_data["visual"],
                "ocean": ocean,
                "filename": filename
            }

    return result


def build_portrait_prompt(visual: str, style_suffix: str = None, prefix: str = None, max_tokens: int = 77) -> tuple[str, bool, int]:
    """Build a prompt for portrait generation with token limit enforcement.

    Args:
        visual: The character's visual description from theme YAML
        style_suffix: Optional theme-specific style suffix. Falls back to DEFAULT_STYLE_SUFFIX.
        prefix: Optional theme-specific prefix prepended before the visual description.
        max_tokens: Token limit for the engine (77 for SDXL/CLIP, 256 for Flux/T5).

    Returns:
        tuple: (prompt, was_truncated, token_count)
    """
    suffix = style_suffix if style_suffix is not None else DEFAULT_STYLE_SUFFIX
    prefixed_visual = f"{prefix} {visual}" if prefix else visual
    prompt, was_truncated = truncate_prompt_to_clip_limit(prefixed_visual, suffix, max_tokens=max_tokens)
    token_count = count_clip_tokens(prompt)
    return prompt, was_truncated, token_count


def _load_flux_modules():
    """Lazy-load the native Flux repo and return its modules."""
    global HAS_FLUX, FLUX_ERROR

    if not FLUX_PROJECT_DIR.exists():
        FLUX_ERROR = f"Flux project not found at {FLUX_PROJECT_DIR}"
        return None

    # Add flux src to path so we can import it
    flux_src = str(FLUX_PROJECT_DIR / "src")
    if flux_src not in sys.path:
        sys.path.insert(0, flux_src)

    try:
        from flux.sampling import denoise, get_noise, get_schedule, prepare, unpack
        from flux.util import configs, load_ae, load_clip, load_flow_model, load_t5
        HAS_FLUX = True
        return {
            "denoise": denoise,
            "get_noise": get_noise,
            "get_schedule": get_schedule,
            "prepare": prepare,
            "unpack": unpack,
            "configs": configs,
            "load_ae": load_ae,
            "load_clip": load_clip,
            "load_flow_model": load_flow_model,
            "load_t5": load_t5,
        }
    except ImportError as e:
        FLUX_ERROR = str(e)
        return None


def load_pipeline(engine_name: str):
    """Load the image generation pipeline for the specified engine.

    Returns a dict with engine-specific components.
    For SDXL: {"pipe": StableDiffusionXLPipeline}
    For Flux: {"model", "ae", "t5", "clip", "flux_modules", "device"}
    """
    engine = ENGINES[engine_name]

    if engine_name in ("flux", "flux-dev"):
        model_name = engine["model_name"]
        print(f"\nLoading Flux ({model_name}) on MPS...")
        print("  (First run downloads the model)")

        flux = _load_flux_modules()
        if flux is None:
            print(f"Error loading Flux: {FLUX_ERROR}")
            print(f"Expected Flux repo at: {FLUX_PROJECT_DIR}")
            print("Install: git clone https://github.com/black-forest-labs/flux ~/Projects/flux")
            sys.exit(1)

        device = torch.device("mps")
        t5 = flux["load_t5"](device, max_length=256)
        clip = flux["load_clip"](device)
        model = flux["load_flow_model"](model_name, device=device)
        ae = flux["load_ae"](model_name, device=device)

        print("Flux models loaded.\n")
        return {
            "model": model, "ae": ae, "t5": t5, "clip": clip,
            "flux_modules": flux, "device": device,
        }
    else:
        model_id = engine["model_id"]
        print("\nLoading SDXL model on MPS...")
        print(f"  Model: {model_id}")
        print("  (First run downloads ~6.5GB model)")

        pipe = StableDiffusionXLPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            use_safetensors=True,
        )
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe = pipe.to("mps")
        pipe.enable_attention_slicing()

        print("Model loaded.\n")
        return {"pipe": pipe}


def generate_portrait(pipeline_components: dict, prompt: str, engine_name: str, seed: int = 42) -> "Image.Image":
    """Generate a single portrait using the specified engine."""
    engine = ENGINES[engine_name]
    gen_size = engine["generation_size"]
    out_size = engine["output_size"]

    if engine_name in ("flux", "flux-dev"):
        from einops import rearrange

        flux = pipeline_components["flux_modules"]
        model = pipeline_components["model"]
        ae = pipeline_components["ae"]
        t5 = pipeline_components["t5"]
        clip = pipeline_components["clip"]
        device = pipeline_components["device"]

        # Flux native sampling pipeline
        x = flux["get_noise"](
            1, gen_size, gen_size,
            device=device, dtype=torch.bfloat16, seed=seed,
        )
        inp = flux["prepare"](t5, clip, x, prompt=prompt)
        # flux-dev uses shift=True, schnell uses shift=False
        use_shift = engine_name == "flux-dev"
        timesteps = flux["get_schedule"](
            engine["num_inference_steps"], inp["img"].shape[1], shift=use_shift,
        )

        with torch.no_grad():
            x = flux["denoise"](model, **inp, timesteps=timesteps, guidance=engine["guidance_scale"])

        x = flux["unpack"](x.float(), gen_size, gen_size)
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
            x = ae.decode(x)

        # Convert tensor to PIL
        x = x.clamp(-1, 1)
        x = rearrange(x[0], "c h w -> h w c")
        image = Image.fromarray((127.5 * (x + 1.0)).cpu().byte().numpy())
    else:
        # SDXL via diffusers
        pipe = pipeline_components["pipe"]
        generator = torch.Generator().manual_seed(seed)

        kwargs = {
            "prompt": prompt,
            "width": gen_size,
            "height": gen_size,
            "num_inference_steps": engine["num_inference_steps"],
            "guidance_scale": engine["guidance_scale"],
            "generator": generator,
        }
        if engine["supports_negative_prompt"]:
            kwargs["negative_prompt"] = pipeline_components.get("negative_prompt",
                "photorealistic, 3d render, glossy, blurry, deformed")

        with torch.no_grad():
            result = pipe(**kwargs)

        image = result.images[0]

    return image.resize((out_size, out_size), Image.Resampling.LANCZOS)


def main():
    parser = argparse.ArgumentParser(description="Generate individual portraits from theme YAML files")
    parser.add_argument("--dry-run", action="store_true", help="List without generating")
    parser.add_argument("--theme", type=str, help="Generate only this theme")
    parser.add_argument("--role", type=str, help="Generate only this role (with --theme)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--skip-existing", action="store_true", help="Skip existing files")
    parser.add_argument("--output-dir", type=str, help="Output to different directory (default: pennyfarthing-dist/personas/portraits)")
    parser.add_argument("--engine", type=str, choices=list(ENGINES.keys()), default=DEFAULT_ENGINE,
                        help=f"Image generation engine (default: {DEFAULT_ENGINE})")
    parser.add_argument("--prompt", type=str, help="Generate a single image from an arbitrary text prompt (bypasses theme YAML)")
    parser.add_argument("--output", type=str, help="Output file path (required with --prompt)")
    parser.add_argument("--no-style-suffix", action="store_true", help="Skip appending the default style suffix (use with --prompt)")
    parser.add_argument("--style", type=str, help="Custom style suffix to append to --prompt (overrides default woodcut style)")
    args = parser.parse_args()

    # Freeform prompt mode — bypass theme loading entirely
    if args.prompt:
        if not args.output:
            print("Error: --output is required when using --prompt")
            sys.exit(1)

        engine_name = args.engine
        engine = ENGINES[engine_name]

        if args.no_style_suffix:
            style_suffix = ""
        elif args.style:
            style_suffix = f", {args.style}"
        else:
            style_suffix = DEFAULT_STYLE_SUFFIX

        prompt, was_truncated, token_count = build_portrait_prompt(
            args.prompt, style_suffix, max_tokens=engine["max_tokens"]
        )

        print(f"Engine: {engine_name.upper()}")
        print(f"Prompt ({token_count} tokens): {prompt}")
        if was_truncated:
            print(f"  WARNING: Truncated to {engine['max_tokens']} token limit")

        if args.dry_run:
            print("Dry run — no image generated.")
            return

        if not HAS_TORCH:
            print(f"Missing required package: {TORCH_ERROR}")
            print("\nInstall: pip install diffusers transformers accelerate torch pillow")
            sys.exit(1)

        pipeline_components = load_pipeline(engine_name)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Generating: {out_path}...")
        image = generate_portrait(pipeline_components, prompt, engine_name, seed=args.seed)
        image.save(out_path, "PNG")
        print(f"Done: {out_path}")
        return

    engine_name = args.engine
    engine = ENGINES[engine_name]

    # Determine output directory override
    output_override = Path(args.output_dir) if args.output_dir else None

    # Find theme files from package, built-in, and custom directories
    # Each entry tracks its own output directory
    # Priority: custom > built-in > package (later entries override earlier)
    theme_map: dict[str, dict] = {}

    # 1. Package themes (packages/themes-*/themes/ -> packages/themes-*/portraits/)
    pkg_sources = []
    if PACKAGES_DIR.exists():
        for pkg_dir in sorted(PACKAGES_DIR.glob("themes-*")):
            themes_dir = pkg_dir / "themes"
            portraits_dir = pkg_dir / "portraits"
            if themes_dir.exists():
                pkg_sources.append(themes_dir)
                for tf in themes_dir.glob("*.yaml"):
                    theme_map[tf.stem] = {"path": tf, "output_dir": portraits_dir}

    # 2. Built-in themes (override packages if same name)
    if BUILTIN_THEMES_DIR.exists():
        for tf in BUILTIN_THEMES_DIR.glob("*.yaml"):
            theme_map[tf.stem] = {"path": tf, "output_dir": BUILTIN_OUTPUT_DIR}

    # 3. Custom themes (override everything)
    if CUSTOM_THEMES_DIR.exists():
        for tf in CUSTOM_THEMES_DIR.glob("*.yaml"):
            theme_map[tf.stem] = {"path": tf, "output_dir": BUILTIN_OUTPUT_DIR}

    theme_entries = sorted(theme_map.values(), key=lambda e: e["path"].stem)

    if args.theme:
        if args.theme in theme_map:
            theme_entries = [theme_map[args.theme]]
        else:
            print(f"Theme '{args.theme}' not found")
            print(f"  Searched: {BUILTIN_THEMES_DIR}")
            for src in pkg_sources:
                print(f"  Searched: {src}")
            print(f"  Searched: {CUSTOM_THEMES_DIR}")
            sys.exit(1)

    print("Theme sources:")
    print(f"  Built-in: {BUILTIN_THEMES_DIR}")
    for src in pkg_sources:
        print(f"  Package:  {src}")
    print(f"  Custom:   {CUSTOM_THEMES_DIR}")
    print(f"Found {len(theme_entries)} themes")
    engine_label = engine.get("model_id", engine.get("model_name", engine_name))
    print(f"Engine: {engine_name.upper()} ({engine_label})")

    if args.dry_run:
        print(f"\nToken limit: {engine['max_tokens']} tokens ({engine_name.upper()})")
        print(f"Tokenizer: {'CLIP (accurate)' if HAS_CLIP_TOKENIZER else 'word estimate (fallback)'}")
        roles_to_show = [args.role] if args.role else ROLES
        print(f"\nDry run - portraits to generate (roles: {', '.join(roles_to_show)}):")
        truncation_warnings = []
        for entry in theme_entries:
            tf = entry["path"]
            output_base = output_override or entry["output_dir"]
            parsed = parse_theme_file(tf)
            theme_dir = output_base / parsed["theme"]
            char_count = len(parsed["characters"])
            style_desc = parsed["portrait_style"][:60] + "..." if parsed["portrait_style"] and len(parsed["portrait_style"]) > 60 else parsed["portrait_style"]
            style_display = style_desc if style_desc else "(default woodcut)"
            print(f"\n  {parsed['theme']}/ ({char_count} characters with visual)")
            print(f"    Style: {style_display}")
            print(f"    Output: {output_base}")
            for role in roles_to_show:
                if role in parsed["characters"]:
                    char = parsed["characters"][role]
                    out_path = theme_dir / char["filename"]
                    status = "EXISTS" if out_path.exists() else "PENDING"

                    # Check token count and truncation
                    prompt, was_truncated, token_count = build_portrait_prompt(
                        char["visual"], parsed["portrait_style"], prefix=parsed["portrait_prefix"], max_tokens=engine["max_tokens"]
                    )
                    token_status = f"{token_count}tok"
                    if was_truncated:
                        token_status = f"⚠️ {token_count}tok TRUNCATED"
                        truncation_warnings.append((parsed["theme"], role, char["filename"]))

                    visual_preview = char["visual"][:40] + "..." if len(char["visual"]) > 40 else char["visual"]
                    print(f"    [{status}] {char['filename']} ({token_status}): {visual_preview}")
                else:
                    print(f"    [SKIP] {role}: no visual field")

        if truncation_warnings:
            print(f"\n{'='*60}")
            print(f"⚠️  WARNING: {len(truncation_warnings)} prompts will be truncated!")
            print(f"    Token limit is {engine['max_tokens']} ({engine_name.upper()}). Consider shortening:")
            for theme, role, filename in truncation_warnings[:10]:
                print(f"    - {theme}/{filename} ({role})")
            if len(truncation_warnings) > 10:
                print(f"    ... and {len(truncation_warnings) - 10} more")
        return

    # Check for torch
    if not HAS_TORCH:
        print(f"Missing required package: {TORCH_ERROR}")
        print("\nInstall: pip install diffusers transformers accelerate torch pillow")
        sys.exit(1)

    # Load model
    pipeline_components = load_pipeline(engine_name)

    # Track results
    successful = 0
    failed = []
    truncated = []
    start_time = datetime.now()

    total_themes = len(theme_entries)
    for theme_idx, entry in enumerate(theme_entries, 1):
        tf = entry["path"]
        output_base = output_override or entry["output_dir"]
        parsed = parse_theme_file(tf)
        theme = parsed["theme"]
        theme_dir = output_base / theme
        theme_dir.mkdir(parents=True, exist_ok=True)

        # Inject theme-specific negative prompt into pipeline components
        if parsed["negative_prompt"]:
            pipeline_components["negative_prompt"] = parsed["negative_prompt"]
        elif "negative_prompt" in pipeline_components:
            del pipeline_components["negative_prompt"]

        roles_to_gen = [args.role] if args.role else ROLES
        print(f"\n[{theme_idx}/{total_themes}] Theme: {theme}")

        for role in roles_to_gen:
            if role not in parsed["characters"]:
                continue

            char = parsed["characters"][role]
            out_path = theme_dir / char["filename"]
            if args.skip_existing and out_path.exists():
                print(f"  SKIP (exists): {char['filename']}")
                continue

            prompt, was_truncated, token_count = build_portrait_prompt(
                char["visual"], parsed["portrait_style"], prefix=parsed["portrait_prefix"], max_tokens=engine["max_tokens"]
            )

            if was_truncated:
                truncated.append((theme, char["filename"], token_count))
                print(f"  WARNING: Truncated {char['filename']} to {token_count} tokens")

            print(f"  Generating: {char['filename']} ({char['name']})...")
            print(f"    Prompt: {prompt}")
            try:
                # Vary seed per character for diversity (base_seed + role_index)
                role_seed = args.seed + ROLES.index(role)
                image = generate_portrait(pipeline_components, prompt, engine_name, seed=role_seed)
                image.save(out_path, "PNG")
                successful += 1
                print(f"  DONE: {char['filename']}")
            except Exception as e:
                failed.append((theme, char["filename"], str(e)))
                print(f"  FAILED: {char['filename']}: {e}")

    # Summary
    elapsed = datetime.now() - start_time
    print(f"\n{'='*50}")
    print(f"Complete: {successful} portraits in {elapsed}")
    if truncated:
        print(f"Truncated: {len(truncated)} prompts exceeded {engine['max_tokens']} token limit ({engine_name.upper()})")
    if failed:
        print(f"Failed: {len(failed)}")
        for t, r, e in failed:
            print(f"  - {t}/{r}: {e}")


if __name__ == "__main__":
    main()
