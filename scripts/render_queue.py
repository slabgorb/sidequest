#!/usr/bin/env python3
"""Sequential asset pipeline runner for SideQuest worlds: render then publish.

The media daemon renders one image at a time, so there's no benefit to firing
batches in parallel — it just makes two client scripts fight over the socket.
This runner executes a list of jobs strictly in sequence and stops on the first
failure. Two job kinds:

  render  — invokes scripts/generate_{portrait,poi}_images.py under the
            sidequest-server project, SIDEQUEST_GENRE_PACKS -> local content.
  sync    — builds an explicit UPLOAD PAYLOAD (the rendered PNGs for a world),
            prints it for audit, then publishes it to R2 via
            scripts/r2_sync_packs.py under the orchestrator-root project
            (boto3 lives there, NOT in sidequest-server).

IMPORTANT — branches: renders read the *current git working tree*. If a job's
prompts live on an unmerged branch (e.g. five_points), check that branch out in
sidequest-content BEFORE this runner reaches the job. Never switch branches
while a render is mid-flight.

Usage:
    uv run --project sidequest-server python scripts/render_queue.py
    uv run --project sidequest-server python scripts/render_queue.py --steps 20
    # ad-hoc jobs (kind:genre:world), kind in {portraits,pois,sync}:
    uv run --project sidequest-server python scripts/render_queue.py \
        pois:space_opera:aureate_span sync:space_opera:aureate_span
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO / "sidequest-content"
CONTENT = CONTENT_ROOT / "genre_packs"

RENDER_SCRIPT = {
    "portraits": "generate_portrait_images.py",
    "pois": "generate_poi_images.py",
}
KINDS = set(RENDER_SCRIPT) | {"sync"}

# Default queue. Each entry: (kind, genre, world). Edit, or pass jobs on the CLI.
# Entries needing an unmerged branch note the branch to check out first.
JOBS: list[tuple[str, str, str]] = [
    ("pois", "space_opera", "aureate_span"),
    ("sync", "space_opera", "aureate_span"),
    # ("portraits", "spaghetti_western", "five_points"),  # branch: feat/five-points-poi-visual-language
    # ("pois", "spaghetti_western", "five_points"),        # branch: feat/five-points-poi-visual-language
    # ("sync", "spaghetti_western", "five_points"),         # branch: feat/five-points-poi-visual-language
]


def parse_jobs(raw: list[str]) -> list[tuple[str, str, str]]:
    jobs = []
    for spec in raw:
        parts = spec.split(":")
        if len(parts) != 3 or parts[0] not in KINDS:
            sys.exit(f"bad job spec {spec!r}; expected kind:genre:world, kind in {sorted(KINDS)}")
        jobs.append((parts[0], parts[1], parts[2]))
    return jobs


def upload_payload(genre: str, world: str) -> list[Path]:
    """The explicit set of local rendered assets to publish for a world.

    Everything under <genre>/worlds/<world>/assets/**.png — portraits + POIs.
    """
    assets = CONTENT / genre / "worlds" / world / "assets"
    return sorted(p for p in assets.rglob("*.png") if p.is_file())


def run_render(kind: str, genre: str, world: str, steps: int, force: bool) -> int:
    script = REPO / "scripts" / RENDER_SCRIPT[kind]
    cmd = [
        "uv", "run", "--project", "sidequest-server", "python", str(script),
        "--genre", genre, "--world", world, "--steps", str(steps),
    ]
    if force:
        cmd.append("--force")
    env = {**os.environ, "SIDEQUEST_GENRE_PACKS": str(CONTENT)}
    banner(f"render {kind} :: {genre}/{world} :: steps={steps} force={force}")
    return timed(lambda: subprocess.run(cmd, cwd=REPO, env=env).returncode, f"render {kind} {genre}/{world}")


def run_sync(genre: str, world: str) -> int:
    payload = upload_payload(genre, world)
    banner(f"sync (UPLOAD PAYLOAD) :: {genre}/{world}")
    if not payload:
        print(f"[render-queue] payload empty — no PNGs under {genre}/worlds/{world}/assets; nothing to upload.", flush=True)
        return 0
    total = 0
    print(f"[render-queue] upload payload — {len(payload)} file(s) -> R2 (cdn.slabgorb.com):", flush=True)
    for p in payload:
        size = p.stat().st_size
        total += size
        print(f"    + {p.relative_to(CONTENT_ROOT)}  ({size / 1024:.0f} KiB)", flush=True)
    print(f"[render-queue] payload total: {total / 1024 / 1024:.1f} MiB", flush=True)

    script = REPO / "scripts" / "r2_sync_packs.py"
    cmd = [
        "uv", "run", "--project", str(REPO), "python", str(script),
        "--content-root", str(CONTENT_ROOT),
        "--files", *[str(p) for p in payload],
    ]
    return timed(lambda: subprocess.run(cmd, cwd=REPO, env={**os.environ}).returncode, f"sync {genre}/{world}")


def banner(msg: str) -> None:
    print(f"\n{'=' * 72}\n[render-queue] {msg}\n{'=' * 72}", flush=True)


def timed(fn, label: str) -> int:
    start = time.monotonic()
    rc = fn()
    mins = (time.monotonic() - start) / 60
    print(f"[render-queue] {label} -> exit {rc} in {mins:.1f} min", flush=True)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="Run SideQuest render + R2-sync jobs in sequence.")
    ap.add_argument("jobs", nargs="*", help="kind:genre:world specs; overrides the built-in JOBS list")
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--no-force", action="store_true", help="skip --force (don't re-render existing)")
    args = ap.parse_args()

    jobs = parse_jobs(args.jobs) if args.jobs else JOBS
    if not jobs:
        sys.exit("no jobs (JOBS list empty and none on CLI)")
    if not CONTENT.exists():
        sys.exit(f"content tree not found at {CONTENT} — run from the orchestrator checkout")

    print(f"[render-queue] {len(jobs)} job(s), steps={args.steps}, force={not args.no_force}", flush=True)
    results = []
    for kind, genre, world in jobs:
        if kind == "sync":
            rc = run_sync(genre, world)
        else:
            rc = run_render(kind, genre, world, args.steps, not args.no_force)
        results.append(((kind, genre, world), rc))
        if rc != 0:
            print(f"\n[render-queue] STOP — {kind} {genre}/{world} failed (exit {rc}); halting queue.", flush=True)
            break

    print("\n[render-queue] SUMMARY", flush=True)
    for (kind, genre, world), rc in results:
        print(f"  {'OK  ' if rc == 0 else 'FAIL'}  {kind:9} {genre}/{world}  (exit {rc})", flush=True)
    return 0 if results and all(rc == 0 for _, rc in results) else 1


if __name__ == "__main__":
    sys.exit(main())
