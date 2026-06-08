# Cloudflare R2 Media Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all curated genre-pack media (~931 MB across 887 LFS files) and all daemon-generated artifacts out of `sidequest-content` and into Cloudflare R2, served via `https://cdn.slabgorb.com`, with a single-seam `resolve_asset_url()` server function and direct R2 writes from the daemon.

**Architecture:** Two top-level R2 prefixes — `genre_packs/` (byte-for-byte mirror, immutable, long Cache-Control) and `artifacts/` (daemon-generated, hash-named, 90-day lifecycle). Server emits URLs through one resolver function that toggles between `cdn.slabgorb.com` (default) and local-serve via `SIDEQUEST_ASSET_BASE_URL`. Daemon uploads directly via S3 keys; OTEL spans cover every PUT and every URL resolve so the GM panel can verify wiring.

**Tech Stack:** Python 3.11+ (server, daemon, scripts), boto3 (S3 client for R2), AWS CLI (one-shot CORS/lifecycle config), pytest, OpenTelemetry, FastAPI/Starlette, React/TypeScript (UI is unchanged — receives URLs, no CDN-awareness).

**Repos involved:**
- `.` (orchestrator) — sync/verify scripts, justfile, .env.example
- `sidequest-server/` — `asset_urls.py`, OTEL span, touch-point refactor
- `sidequest-daemon/` — `r2_writer.py`, image-pipeline integration, OTEL spans
- `sidequest-content/` — LFS strip (destructive, last)

**Spec reference:** `docs/superpowers/specs/2026-05-03-cloudflare-r2-media-migration-design.md`

---

## File Structure

### Created

| File | Repo | Responsibility |
|---|---|---|
| `scripts/r2_sync_packs.py` | orchestrator | Walk `sidequest-content/genre_packs/`, upload media to R2 with correct `Content-Type` and `Cache-Control: immutable`, idempotent via MD5/ETag compare |
| `scripts/r2_verify_packs.py` | orchestrator | HEAD every local LFS-tracked file via `cdn.slabgorb.com`, fail loudly on any non-200 |
| `scripts/tests/test_r2_sync_packs.py` | orchestrator | Unit tests for path filtering and content-type mapping |
| `sidequest-server/sidequest/server/asset_urls.py` | server | Single seam `resolve_asset_url(relative_path)` toggled by `SIDEQUEST_ASSET_BASE_URL` |
| `sidequest-server/tests/server/test_asset_urls.py` | server | Coverage of CDN, local-serve, and edge-case path normalisation |
| `sidequest-server/sidequest/telemetry/spans/asset_url.py` | server | New OTEL span `server.asset_url.resolved` |
| `sidequest-server/tests/telemetry/spans/test_asset_url_span.py` | server | Span emission test |
| `sidequest-daemon/sidequest_daemon/media/r2_writer.py` | daemon | Boto3-backed `upload_artifact(...)`, sha256 keying, fail-loud |
| `sidequest-daemon/tests/media/test_r2_writer.py` | daemon | Mocked-S3 test of upload paths, error propagation |
| `.env.example` | orchestrator | Documented template of all env vars |

### Modified

| File | Repo | Lines | Change |
|---|---|---|---|
| `sidequest-server/sidequest/genre/loader.py` | server | ~800 + audio.yaml emission sites | Wrap audio `path` and theme variation `path` strings via `resolve_asset_url()` at config-load time so the UI receives full URLs |
| `sidequest-server/sidequest/server/views.py` | server | 416 | `portrait_url` set via `resolve_asset_url("artifacts/<world>/<session>/portraits/<hash>.png")` |
| `sidequest-server/sidequest/server/render_mounts.py` | server | URL emission paths | Emit `resolve_asset_url("artifacts/...")` instead of `/renders/...` for new generations; keep `register_root` + `url_for_path` for back-compat reads of pre-migration on-disk artifacts |
| `sidequest-server/sidequest/telemetry/spans/__init__.py` | server | star-import block | Add `from .asset_url import *` |
| `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py` | daemon | 453-457 | After `image.save(...)`, call `r2_writer.upload_artifact(...)` and emit the relative R2 path as `image_url` |
| `sidequest-daemon/sidequest_daemon/media/daemon.py` | daemon | render-completed code path | Pass world/session into worker so the upload path is properly keyed |
| `sidequest-daemon/pyproject.toml` | daemon | dependencies | Add `boto3` |
| `justfile` | orchestrator | server/daemon recipes | Pass through `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_S3_ENDPOINT`, `SIDEQUEST_ASSET_BASE_URL` |
| `sidequest-content/.gitattributes` | content | unchanged | Kept as-is — defensive against future stray binaries |

### Deleted

None. `register_root` / `url_for_path` are kept for reading legacy on-disk artifacts. LFS-tracked files are removed by `git lfs migrate export` (history rewrite, not a normal delete).

---

## Working Conventions

- **TDD:** Write the failing test first, run it to see it fail, implement minimally, run it to see it pass, commit.
- **Commits:** Small. One logical change per commit. Conventional-commit prefixes (`feat:`, `chore:`, `fix:`, `test:`).
- **Branch:** Work on `feat/r2-media-migration` (orchestrator) and matching feature branches in subrepos (`sidequest-server`, `sidequest-daemon`). The `sidequest-content` LFS strip happens on `main` directly because it rewrites history.
- **No silent fallbacks** (CLAUDE.md): every error path raises or emits an OTEL `failure` span. Never mask a missing config with a default.
- **No dependency on a running daemon during unit tests:** all daemon-side tests mock boto3.
- **Multi-repo working directory:** every command shows the explicit `cd` so the engineer doesn't crosswire repos.

---

## Task 1 — Pre-flight Shell Environment

**Files:**
- Modify: `~/.zshrc` (user shell config — not a repo file)

**Why:** The S3 boto3 client needs `R2_S3_ENDPOINT`. The user has the access keys already but the endpoint is not yet exported. Also remove an orphan `R2_ACCESS_KEY` (legacy name, replaced by `R2_ACCESS_KEY_ID`).

- [ ] **Step 1.1: Confirm current env state**

Run:
```bash
echo "endpoint=${R2_S3_ENDPOINT:-UNSET}"
echo "access_id=${R2_ACCESS_KEY_ID:-UNSET}"
echo "secret_set=$([ -n "${R2_SECRET_ACCESS_KEY:-}" ] && echo yes || echo no)"
echo "orphan=${R2_ACCESS_KEY:-UNSET}"
```
Expected: `R2_ACCESS_KEY_ID` set, `R2_SECRET_ACCESS_KEY` set, `R2_S3_ENDPOINT` UNSET, `R2_ACCESS_KEY` may be set (orphan).

- [ ] **Step 1.2: Add `R2_S3_ENDPOINT` and remove the orphan**

Edit `~/.zshrc`. Add:
```bash
export R2_S3_ENDPOINT="https://a55aafa9b0691f828cd6864be28c1674.r2.cloudflarestorage.com"
```
And delete any line that exports `R2_ACCESS_KEY` (no `_ID` suffix).

- [ ] **Step 1.3: Reload and verify**

Run (in a NEW shell, not the current one — `source ~/.zshrc` is acceptable but a new shell is cleaner):
```bash
exec zsh
echo "endpoint=$R2_S3_ENDPOINT"
echo "orphan=${R2_ACCESS_KEY:-UNSET}"
```
Expected: endpoint resolves to the Cloudflare URL; `orphan=UNSET`.

- [ ] **Step 1.4: Probe the bucket end-to-end**

Run:
```bash
aws s3api list-objects-v2 \
  --bucket sidequest \
  --endpoint-url "$R2_S3_ENDPOINT" \
  --max-items 1
```
Expected: returns `{}` or a `Contents` array (bucket exists, creds work). Any 403/InvalidAccessKeyId means stop and recheck creds.

---

## Task 2 — Apply CORS Rule to R2 Bucket

**Files:**
- Create (transient): `/tmp/sidequest-r2-cors-cf.json`

**Why:** The UI's `AudioCache.ts:11` does `fetch(url)` which triggers CORS preflight (unlike `<audio>` / `<img>` elements). Without a CORS rule, audio fetches fail in browser.

> **2026-05-03 note:** The plan originally proposed `aws s3api put-bucket-cors` using the S3 access key, but that key is object-scoped (Object Read & Write only) and gets `AccessDenied` on bucket-level CORS operations. We use the Cloudflare native REST API with the `CLOUDFLARE_API_TOKEN_SIDEQUEST` bearer token instead, which has "R2 buckets read/write" scope. The CF schema differs from the S3 schema (`rules` not `CORSRules`, `allowed.{origins,methods,headers}` substructure, camelCase). The applied schema is shown in Step 2.1.

- [ ] **Step 2.1: Write the CORS config to a temp file**

Create `/tmp/sidequest-r2-cors.json`:
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": [
        "http://localhost:5173",
        "http://localhost:8765",
        "https://slabgorb.com",
        "https://*.slabgorb.com"
      ],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag", "Content-Length"],
      "MaxAgeSeconds": 86400
    }
  ]
}
```

- [ ] **Step 2.2: Apply the CORS rule**

Run:
```bash
aws s3api put-bucket-cors \
  --bucket sidequest \
  --endpoint-url "$R2_S3_ENDPOINT" \
  --cors-configuration file:///tmp/sidequest-r2-cors.json
```
Expected: empty success output (no JSON returned on `put`).

- [ ] **Step 2.3: Verify the CORS rule was applied**

Run:
```bash
aws s3api get-bucket-cors --bucket sidequest --endpoint-url "$R2_S3_ENDPOINT"
```
Expected: JSON matching what was sent, with `AllowedOrigins`, `AllowedMethods: ["GET", "HEAD"]`, etc.

- [ ] **Step 2.4: Clean up temp file**

Run: `rm /tmp/sidequest-r2-cors.json`

---

## Task 3 — DROPPED (no lifecycle rule)

**Status:** DROPPED 2026-05-03 by Keith. The original spec proposed a 90-day
expiry on `artifacts/`; that was rejected because SideQuest is built for
years-long campaigns and save files reference artifact URLs. A timed reaper
silently breaks portraits in season-old saves. See spec §5 "R2 lifecycle
rule" for the rationale and the cost-trivial nature of unbounded retention.

**No work to do.** Nothing applied to the bucket. Skip to Task 4.

If unbounded retention ever becomes expensive enough to matter (it does not
at current scale), the right design is a save-aware sweep — list active
save files, find unreferenced artifacts, delete only those — not a blunt
date-based rule. File that as a separate story when warranted.

---

## Task 4 — Phase A: Sync Script (`r2_sync_packs.py`)

**Files:**
- Create: `scripts/r2_sync_packs.py`
- Create: `scripts/tests/test_r2_sync_packs.py`

**Why:** Phase A copies all curated media into R2 without touching production. Idempotent: re-running skips files whose MD5 matches the remote ETag.

- [ ] **Step 4.1: Write the failing test for path filtering**

Create `scripts/tests/test_r2_sync_packs.py`:
```python
"""Tests for r2_sync_packs path filtering and content-type mapping."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.r2_sync_packs import (
    LFS_EXTENSIONS,
    content_type_for,
    iter_media_files,
)


def test_lfs_extensions_match_gitattributes() -> None:
    expected = {".ogg", ".png", ".wav", ".mp3", ".jpg", ".jpeg", ".webp", ".flac"}
    assert LFS_EXTENSIONS == expected


def test_content_type_for_known_extensions() -> None:
    assert content_type_for(Path("a.ogg")) == "audio/ogg"
    assert content_type_for(Path("a.png")) == "image/png"
    assert content_type_for(Path("a.jpg")) == "image/jpeg"
    assert content_type_for(Path("a.jpeg")) == "image/jpeg"
    assert content_type_for(Path("a.webp")) == "image/webp"
    assert content_type_for(Path("a.mp3")) == "audio/mpeg"
    assert content_type_for(Path("a.wav")) == "audio/wav"
    assert content_type_for(Path("a.flac")) == "audio/flac"


def test_content_type_for_unknown_extension_raises() -> None:
    with pytest.raises(ValueError, match="unsupported extension"):
        content_type_for(Path("a.txt"))


def test_iter_media_files_skips_yaml_and_text(tmp_path: Path) -> None:
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "track.ogg").write_bytes(b"x")
    (tmp_path / "config.yaml").write_text("ok")
    (tmp_path / "README.md").write_text("ok")
    found = sorted(p.name for p in iter_media_files(tmp_path))
    assert found == ["track.ogg"]


def test_iter_media_files_recurses(tmp_path: Path) -> None:
    deep = tmp_path / "worlds" / "dungeon" / "audio" / "music"
    deep.mkdir(parents=True)
    (deep / "combat.ogg").write_bytes(b"x")
    (tmp_path / "portraits" / "hero.png").parent.mkdir(parents=True)
    (tmp_path / "portraits" / "hero.png").write_bytes(b"y")
    found = sorted(p.relative_to(tmp_path).as_posix() for p in iter_media_files(tmp_path))
    assert found == [
        "portraits/hero.png",
        "worlds/dungeon/audio/music/combat.ogg",
    ]
```

- [ ] **Step 4.2: Run the failing test**

Run: `cd /Users/slabgorb/Projects/oq-1 && uv run --with pytest --with boto3 pytest scripts/tests/test_r2_sync_packs.py -v`
Expected: ImportError (module doesn't exist yet) — that's the RED.

- [ ] **Step 4.3: Implement the sync script**

Create `scripts/r2_sync_packs.py`:
```python
"""Phase A — sync sidequest-content/genre_packs/ into R2.

Walks the local content tree, uploads every LFS-tracked binary to R2 under
the same relative path, and is idempotent across re-runs (compares local MD5
to remote ETag and skips matches).

Per CLAUDE.md no-silent-fallbacks rule: any HTTP error aborts the run.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

LFS_EXTENSIONS: frozenset[str] = frozenset(
    {".ogg", ".png", ".wav", ".mp3", ".jpg", ".jpeg", ".webp", ".flac"}
)

_CONTENT_TYPES: dict[str, str] = {
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

CACHE_CONTROL_IMMUTABLE = "public, max-age=31536000, immutable"

logger = logging.getLogger("r2_sync_packs")


def content_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in _CONTENT_TYPES:
        raise ValueError(f"unsupported extension: {ext}")
    return _CONTENT_TYPES[ext]


def iter_media_files(root: Path) -> Iterator[Path]:
    """Yield all LFS-tracked media files under root, recursively."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in LFS_EXTENSIONS:
            continue
        yield path


def _md5_of(path: Path) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _remote_etag(client: BaseClient, bucket: str, key: str) -> str | None:
    try:
        resp = client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    etag = resp.get("ETag", "").strip('"')
    return etag or None


def _build_client() -> BaseClient:
    endpoint = os.environ["R2_S3_ENDPOINT"]
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def sync(content_root: Path, bucket: str = "sidequest", dry_run: bool = False) -> dict[str, int]:
    """Walk content_root and upload every LFS-tracked file. Returns counts."""
    if not (content_root / "genre_packs").is_dir():
        raise FileNotFoundError(f"genre_packs/ not found under {content_root}")

    client = None if dry_run else _build_client()
    skipped = 0
    uploaded = 0
    bytes_uploaded = 0

    for path in iter_media_files(content_root / "genre_packs"):
        rel = path.relative_to(content_root).as_posix()
        key = rel  # 1:1 mirror, e.g. genre_packs/<genre>/audio/<f>.ogg
        size = path.stat().st_size
        local_md5 = _md5_of(path)

        if dry_run:
            logger.info("DRY would upload key=%s size=%d md5=%s", key, size, local_md5)
            uploaded += 1
            bytes_uploaded += size
            continue

        assert client is not None
        remote = _remote_etag(client, bucket, key)
        if remote == local_md5:
            logger.info("SKIP key=%s (matches remote)", key)
            skipped += 1
            continue

        ctype = content_type_for(path)
        with path.open("rb") as f:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=f,
                ContentType=ctype,
                CacheControl=CACHE_CONTROL_IMMUTABLE,
            )
        logger.info(
            "PUT key=%s size=%d ctype=%s md5=%s", key, size, ctype, local_md5
        )
        uploaded += 1
        bytes_uploaded += size

    return {"uploaded": uploaded, "skipped": skipped, "bytes_uploaded": bytes_uploaded}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--content-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sidequest-content",
        help="Path to sidequest-content checkout",
    )
    parser.add_argument("--bucket", default="sidequest")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-file", type=Path, default=Path("/tmp/r2-sync.log"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(args.log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    counts = sync(args.content_root, bucket=args.bucket, dry_run=args.dry_run)
    logger.info(
        "DONE uploaded=%d skipped=%d bytes=%d",
        counts["uploaded"], counts["skipped"], counts["bytes_uploaded"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Also create `scripts/tests/__init__.py` if it does not exist:
```python
```

- [ ] **Step 4.4: Run the test to confirm it passes**

Run: `cd /Users/slabgorb/Projects/oq-1 && uv run --with pytest --with boto3 pytest scripts/tests/test_r2_sync_packs.py -v`
Expected: 5 passed.

- [ ] **Step 4.5: Dry-run end-to-end against the real content tree**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
uv run --with boto3 python -m scripts.r2_sync_packs --dry-run
```
Expected: log shows `DRY would upload …` for every LFS-tracked file under `sidequest-content/genre_packs/`. Final line: `DONE uploaded=N skipped=0 bytes=B` with N matching `git -C sidequest-content lfs ls-files | wc -l` give-or-take untracked extras.

- [ ] **Step 4.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git checkout -b feat/r2-media-migration
git add scripts/r2_sync_packs.py scripts/tests/__init__.py scripts/tests/test_r2_sync_packs.py
git commit -m "feat(r2): add Phase A sync script for genre_packs media"
```

---

## Task 5 — Phase A: Verify Script (`r2_verify_packs.py`)

**Files:**
- Create: `scripts/r2_verify_packs.py`

**Why:** Confirms every local LFS-tracked file is reachable through `cdn.slabgorb.com` with HTTP 200. Must be 100% green before Phase B.

- [ ] **Step 5.1: Implement the verify script**

Create `scripts/r2_verify_packs.py`:
```python
"""Phase A verification — HEAD every local media file via cdn.slabgorb.com.

Aborts on any non-200; per CLAUDE.md a missing object is loud, not silent.
"""
from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import urllib3

from scripts.r2_sync_packs import iter_media_files

logger = logging.getLogger("r2_verify_packs")
DEFAULT_BASE = "https://cdn.slabgorb.com"


def head_one(http: urllib3.PoolManager, base: str, key: str) -> tuple[str, int]:
    url = f"{base.rstrip('/')}/{key.lstrip('/')}"
    resp = http.request("HEAD", url, retries=False, timeout=10.0)
    return key, resp.status


def verify(content_root: Path, base: str = DEFAULT_BASE, workers: int = 16) -> int:
    """Returns the count of failed checks. 0 means perfect."""
    http = urllib3.PoolManager(num_pools=4, maxsize=workers)
    keys = [
        p.relative_to(content_root).as_posix()
        for p in iter_media_files(content_root / "genre_packs")
    ]
    failures = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(head_one, http, base, k): k for k in keys}
        for fut in as_completed(futs):
            key, status = fut.result()
            if status == 200:
                logger.info("OK %s", key)
            else:
                logger.error("FAIL status=%d %s", status, key)
                failures += 1
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--content-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "sidequest-content",
    )
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--log-file", type=Path, default=Path("/tmp/r2-verify.log"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(args.log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    failures = verify(args.content_root, base=args.base, workers=args.workers)
    if failures:
        logger.error("VERIFY FAILED count=%d", failures)
        return 1
    logger.info("VERIFY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5.2: Spot-check by running it (expected to mostly fail until Task 6 sync runs)**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
uv run --with urllib3 --with boto3 python -m scripts.r2_verify_packs --workers 4 2>&1 | head -20
```
Expected: lots of `FAIL status=404` lines. That's correct — bucket is empty until Task 6.

- [ ] **Step 5.3: Commit**

```bash
git add scripts/r2_verify_packs.py
git commit -m "feat(r2): add Phase A verify script (HEAD probe via cdn.slabgorb.com)"
```

---

## Task 6 — Run Phase A: Real Sync + Verify

**Files:**
- None (operational task).

**Why:** Bucket population. After this step, R2 has a complete mirror of curated media but production still serves locally.

- [ ] **Step 6.1: Run the sync (real)**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
uv run --with boto3 python -m scripts.r2_sync_packs 2>&1 | tail -3
```
Expected runtime: 10-30 minutes for 931 MB. Final line: `DONE uploaded=~887 skipped=0 bytes=~931000000`.

- [ ] **Step 6.2: Re-run sync to confirm idempotency**

Run the same command again. Expected: `DONE uploaded=0 skipped=~887 bytes=0` (every file's MD5 matches its remote ETag).

- [ ] **Step 6.3: Run the verify and require 0 failures**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
uv run --with urllib3 --with boto3 python -m scripts.r2_verify_packs
echo "exit=$?"
```
Expected: log ends with `VERIFY OK`, exit code 0. **Do not proceed past this task if any failures.**

- [ ] **Step 6.4: Spot-check a few URLs in a browser**

Open `https://cdn.slabgorb.com/genre_packs/caverns_and_claudes/audio/music/` style URLs (any one with audio in the manifest). Confirm browser plays the audio file.

---

## Task 7 — Server: `asset_urls.py` Module

**Files:**
- Create: `sidequest-server/sidequest/server/asset_urls.py`
- Create: `sidequest-server/tests/server/test_asset_urls.py`

**Why:** Single seam for URL emission. Toggling `SIDEQUEST_ASSET_BASE_URL` between `https://cdn.slabgorb.com`, `local`, and `""` is the entire cutover/rollback mechanism.

- [ ] **Step 7.1: Write the failing test**

Create `sidequest-server/tests/server/test_asset_urls.py`:
```python
"""Coverage for the resolve_asset_url single-seam URL builder."""
from __future__ import annotations

import pytest

from sidequest.server import asset_urls


def test_default_emits_cdn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    url = asset_urls.resolve_asset_url(
        "genre_packs/caverns_and_claudes/audio/music/combat.ogg"
    )
    assert url == (
        "https://cdn.slabgorb.com/genre_packs/caverns_and_claudes/audio/music/combat.ogg"
    )


def test_explicit_cdn_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "https://staging.example/")
    url = asset_urls.resolve_asset_url("artifacts/world/sess/portraits/x.png")
    assert url == "https://staging.example/artifacts/world/sess/portraits/x.png"


@pytest.mark.parametrize("value", ["", "local"])
def test_local_serve_mode(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", value)
    url = asset_urls.resolve_asset_url(
        "genre_packs/caverns_and_claudes/audio/music/combat.ogg"
    )
    # Local-serve mirrors the existing /genre/<rest> static mount.
    assert url == "/genre/caverns_and_claudes/audio/music/combat.ogg"


def test_local_serve_for_artifacts_uses_renders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "local")
    url = asset_urls.resolve_asset_url("artifacts/w/s/portraits/abc.png")
    # Local-serve fallback for daemon artifacts goes via /renders/.
    assert url == "/renders/artifacts/w/s/portraits/abc.png"


def test_leading_slash_is_normalised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    url = asset_urls.resolve_asset_url("/genre_packs/foo.ogg")
    assert url == "https://cdn.slabgorb.com/genre_packs/foo.ogg"


def test_unknown_top_level_in_local_mode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "local")
    with pytest.raises(ValueError, match="unknown asset prefix"):
        asset_urls.resolve_asset_url("randomthing/foo.ogg")
```

Make sure `sidequest-server/tests/server/__init__.py` exists (it does in this repo — confirm with `ls`).

- [ ] **Step 7.2: Run test to verify it fails**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_asset_urls.py -v
```
Expected: ImportError on `from sidequest.server import asset_urls`.

- [ ] **Step 7.3: Implement `asset_urls.py`**

Create `sidequest-server/sidequest/server/asset_urls.py`:
```python
"""Single-seam URL builder for player-facing media assets.

Toggled by the SIDEQUEST_ASSET_BASE_URL env var:

* unset / not present  -> https://cdn.slabgorb.com (production default)
* "" or "local"        -> local-serve fallback (/genre/* and /renders/*)
* any other URL        -> use that URL as the prefix

The local-serve fallback exists for offline dev and rollback. It maps the
two top-level R2 prefixes back onto the existing static mounts:

* genre_packs/<rest>  -> /genre/<rest>  (mounted by app.py against
  $SIDEQUEST_GENRE_PACKS)
* artifacts/<rest>    -> /renders/<rest>  (legacy back-compat for
  pre-migration artifacts written under ~/.sidequest/)

Per CLAUDE.md no-silent-fallbacks rule: a relative_path with an unknown
top-level prefix raises in local mode. CDN mode tolerates anything (the
404 is the lie detector).
"""
from __future__ import annotations

import os
from typing import Final

from sidequest.telemetry.spans.asset_url import asset_url_resolved_span

_DEFAULT_BASE: Final[str] = "https://cdn.slabgorb.com"

_LOCAL_PREFIX_MAP: Final[dict[str, str]] = {
    "genre_packs/": "/genre/",
    "artifacts/": "/renders/artifacts/",
}


def _local_path_for(relative: str) -> str:
    for prefix, replacement in _LOCAL_PREFIX_MAP.items():
        if relative.startswith(prefix):
            return replacement + relative[len(prefix):]
    raise ValueError(
        f"unknown asset prefix in local mode: {relative!r} "
        f"(expected one of {sorted(_LOCAL_PREFIX_MAP)})"
    )


def resolve_asset_url(relative_path: str) -> str:
    """Convert a content-relative path to the URL the UI should fetch.

    Examples (default config):
      "genre_packs/cav/audio/music/combat.ogg"
        -> "https://cdn.slabgorb.com/genre_packs/cav/audio/music/combat.ogg"
      "artifacts/dungeon/0d8e/portraits/abc.png"
        -> "https://cdn.slabgorb.com/artifacts/dungeon/0d8e/portraits/abc.png"
    """
    rel = relative_path.lstrip("/")
    base = os.environ.get("SIDEQUEST_ASSET_BASE_URL", _DEFAULT_BASE)
    if base in ("", "local"):
        url = _local_path_for(rel)
        mode = "local"
    else:
        url = f"{base.rstrip('/')}/{rel}"
        mode = "cdn"

    with asset_url_resolved_span(relative_path=rel, base_url=base, mode=mode):
        pass
    return url
```

> **Note:** This module imports the OTEL helper from Task 9 — write that span module *before* running the tests for this module, OR temporarily stub the import. The order in this plan keeps the test green by deferring `_emit_resolved_span` integration to Task 9. To keep Task 7 self-contained, replace the `with asset_url_resolved_span(...)` call with `pass` here, and re-add the call in Task 9 once the span exists.

- [ ] **Step 7.4: Replace span call with `pass` for now**

Edit `sidequest-server/sidequest/server/asset_urls.py`. Replace lines 47-49:
```python
    with asset_url_resolved_span(relative_path=rel, base_url=base, mode=mode):
        pass
    return url
```
with:
```python
    # OTEL span emission added in Task 9.
    _ = mode  # keep variable used; deleted with Task 9 wiring
    return url
```
And remove the import at the top:
```python
from sidequest.telemetry.spans.asset_url import asset_url_resolved_span
```

- [ ] **Step 7.5: Run the tests, expect green**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_asset_urls.py -v
```
Expected: 6 passed.

- [ ] **Step 7.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git checkout -b feat/r2-asset-urls
git add sidequest/server/asset_urls.py tests/server/test_asset_urls.py
git commit -m "feat(server): add resolve_asset_url single-seam URL builder"
```

---

## Task 8 — Server: Wire `resolve_asset_url` into Audio Loader

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py` (around line 800, the `audio = _load_yaml(...)` call)
- Create: `sidequest-server/tests/genre/test_audio_url_resolution.py`

**Why:** The audio config emits bare relative paths (e.g. `"audio/music/combat.ogg"` inside `MoodTrack.path` and `AudioVariation.path`). The UI passes these straight to `fetch()`, so the server must convert them to full URLs before serialising the GenrePack.

- [ ] **Step 8.1: Inspect the current emission**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -n "MoodTrack\|AudioVariation\|MusicTheme\|AudioTheme\|audio = " sidequest/genre/loader.py | head -20
grep -n "music\|theme\|track" sidequest/genre/models/audio.py | head -40
```
This is for the engineer's situational awareness — note which fields hold relative paths.

- [ ] **Step 8.2: Write the failing integration test**

Create `sidequest-server/tests/genre/test_audio_url_resolution.py`:
```python
"""Verify that audio paths are URL-resolved at GenrePack load time."""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.genre.loader import load_genre_pack


@pytest.fixture
def caverns_pack(monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    packs_root = (
        Path(__file__).resolve().parents[2].parent
        / "sidequest-content"
        / "genre_packs"
    )
    return load_genre_pack(packs_root / "caverns_and_claudes")


def test_mood_track_paths_are_full_urls(caverns_pack: object) -> None:
    moods = caverns_pack.audio.moods  # type: ignore[attr-defined]
    assert moods, "expected at least one mood track in caverns_and_claudes"
    for mood_name, tracks in moods.items():
        for track in tracks:
            assert track.path.startswith("https://cdn.slabgorb.com/"), (
                f"mood {mood_name!r} track has non-CDN path: {track.path!r}"
            )
            assert "genre_packs/caverns_and_claudes/" in track.path


def test_local_mode_emits_genre_static_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "local")
    packs_root = (
        Path(__file__).resolve().parents[2].parent
        / "sidequest-content"
        / "genre_packs"
    )
    pack = load_genre_pack(packs_root / "caverns_and_claudes")
    moods = pack.audio.moods
    assert moods
    for tracks in moods.values():
        for track in tracks:
            assert track.path.startswith("/genre/caverns_and_claudes/")
```

- [ ] **Step 8.3: Run test to confirm it fails**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/genre/test_audio_url_resolution.py -v
```
Expected: FAIL — paths still bare relative (e.g. `audio/music/combat.ogg`).

- [ ] **Step 8.4: Implement the resolver pass**

Edit `sidequest-server/sidequest/genre/loader.py`. Locate the line near 800:
```python
    audio = _load_yaml(path / "audio.yaml", AudioConfig)
```
Add immediately after:
```python
    _resolve_audio_urls(audio, genre_slug=path.name)
```
Then add this helper function near the bottom of `loader.py` (above `load_genre_pack`):
```python
def _resolve_audio_urls(audio: AudioConfig, *, genre_slug: str) -> None:
    """In-place: rewrite every relative path in audio config to an absolute URL.

    Audio YAML stores paths relative to the genre-pack root, e.g.
    ``audio/music/combat.ogg``. The UI fetches these directly, so the server
    publishes them as full URLs at load time. Goes through resolve_asset_url
    so the cutover is one env var.
    """
    from sidequest.server.asset_urls import resolve_asset_url

    def _fix(rel: str) -> str:
        if not rel:
            return rel
        if rel.startswith(("http://", "https://", "/")):
            return rel  # already resolved (e.g. test fixtures)
        return resolve_asset_url(f"genre_packs/{genre_slug}/{rel}")

    for tracks in audio.moods.values():
        for track in tracks:
            track.path = _fix(track.path)
    for theme in audio.themes:
        for variation in theme.variations:
            variation.path = _fix(variation.path)
    # Cover any other path-bearing structures that exist on AudioConfig.
    # If new fields are added later (e.g. ambience banks), audit-extend here.
```

> **Engineer note:** `AudioConfig` may have additional path-bearing fields not present in the snippet above (e.g. `ambience`, `sfx_pool`). Run:
> ```bash
> grep -n "path: str" sidequest/genre/models/audio.py
> ```
> and extend `_resolve_audio_urls` to cover every such field before moving on. Each extension needs a parallel test in `test_audio_url_resolution.py`.

- [ ] **Step 8.5: Run test to confirm it passes**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/genre/test_audio_url_resolution.py -v
```
Expected: 2 passed.

- [ ] **Step 8.6: Run the broader genre test suite to catch regressions**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/genre -v
```
Expected: all green. If a fixture-based test relied on bare paths, fix the fixture or assertion to accept resolved URLs.

- [ ] **Step 8.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/genre/loader.py tests/genre/test_audio_url_resolution.py
git commit -m "feat(server): resolve audio paths through asset_urls at load time"
```

---

## Task 9 — Server: `server.asset_url.resolved` OTEL Span

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/asset_url.py`
- Create: `sidequest-server/tests/telemetry/spans/test_asset_url_span.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py`
- Modify: `sidequest-server/sidequest/server/asset_urls.py` (re-add the span emission deferred in Task 7)

**Why:** GM-panel lie detector. Without a span on every URL resolve, the panel cannot tell whether a path was rewritten to CDN, local-serve, or skipped entirely.

- [ ] **Step 9.1: Write the span helper test**

Create `sidequest-server/tests/telemetry/spans/test_asset_url_span.py`:
```python
"""Verify the asset_url span emits with expected attributes."""
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from sidequest.telemetry.spans.asset_url import (
    SPAN_ASSET_URL_RESOLVED,
    asset_url_resolved_span,
)


def test_span_records_attrs() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(__name__)

    with asset_url_resolved_span(
        relative_path="genre_packs/cav/audio/x.ogg",
        base_url="https://cdn.slabgorb.com",
        mode="cdn",
        _tracer=tracer,
    ):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == SPAN_ASSET_URL_RESOLVED
    assert span.attributes is not None
    assert span.attributes["asset.relative_path"] == "genre_packs/cav/audio/x.ogg"
    assert span.attributes["asset.base_url"] == "https://cdn.slabgorb.com"
    assert span.attributes["asset.mode"] == "cdn"
```

- [ ] **Step 9.2: Run test to confirm it fails**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/spans/test_asset_url_span.py -v
```
Expected: ImportError.

- [ ] **Step 9.3: Implement the span helper**

Create `sidequest-server/sidequest/telemetry/spans/asset_url.py`:
```python
"""Asset-URL resolution span — fires every time the server emits a media URL."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from ._core import FLAT_ONLY_SPANS
from .span import Span

SPAN_ASSET_URL_RESOLVED = "server.asset_url.resolved"

# Flat-only: the GM panel reads it via the agent_span_close fan-out; no
# typed event extractor needed yet (forensics-only span).
FLAT_ONLY_SPANS.add(SPAN_ASSET_URL_RESOLVED)


@contextmanager
def asset_url_resolved_span(
    *,
    relative_path: str,
    base_url: str,
    mode: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_ASSET_URL_RESOLVED,
        {
            "asset.relative_path": relative_path,
            "asset.base_url": base_url,
            "asset.mode": mode,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span
```

- [ ] **Step 9.4: Register the new module in the spans package**

Edit `sidequest-server/sidequest/telemetry/spans/__init__.py`. Add a star-import line in alphabetical position among the other domain imports (after `from .agent import *`):
```python
from .asset_url import *  # noqa: F401, F403
```

- [ ] **Step 9.5: Run the span test to confirm it passes**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/spans/test_asset_url_span.py -v
```
Expected: 1 passed.

- [ ] **Step 9.6: Run the routing-completeness lint**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/telemetry/test_routing_completeness.py -v
```
Expected: green. (If it complains about the new constant, audit the test — `FLAT_ONLY_SPANS.add` should satisfy it.)

- [ ] **Step 9.7: Re-wire the span into `asset_urls.py`**

Edit `sidequest-server/sidequest/server/asset_urls.py`. Restore the import at the top:
```python
from sidequest.telemetry.spans.asset_url import asset_url_resolved_span
```
Replace the placeholder block:
```python
    # OTEL span emission added in Task 9.
    _ = mode  # keep variable used; deleted with Task 9 wiring
    return url
```
with:
```python
    with asset_url_resolved_span(
        relative_path=rel, base_url=base or "", mode=mode
    ):
        pass
    return url
```

- [ ] **Step 9.8: Re-run the asset_urls tests**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_asset_urls.py -v
```
Expected: 6 passed (still green — span is fire-and-forget).

- [ ] **Step 9.9: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add sidequest/telemetry/spans/asset_url.py sidequest/telemetry/spans/__init__.py tests/telemetry/spans/test_asset_url_span.py sidequest/server/asset_urls.py
git commit -m "feat(server): emit server.asset_url.resolved OTEL span"
```

---

## Task 10 — Server: Route `portrait_url` Through Resolver

**Files:**
- Modify: `sidequest-server/sidequest/server/views.py:416`

**Why:** The character payload's `portrait_url` is currently set to `None` at this site, but elsewhere in the codebase it can be set to a local path. After migration, it must always come from `resolve_asset_url("artifacts/<world>/<session>/portraits/<hash>.png")`.

- [ ] **Step 10.1: Inspect the current sites**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -rn "portrait_url" sidequest/ --include="*.py"
```
Expected: shows views.py:416 plus any other site (e.g. `protocol/models.py` definition, scrapbook, character builder). The plan covers `views.py` directly; if the engineer finds other emission sites that set `portrait_url` to a non-URL string, treat them as additional touch points and add a wrap-test in the next sub-step.

- [ ] **Step 10.2: Write a regression test for the `views.py` site**

Add to `sidequest-server/tests/server/test_views.py` (or create that file if it doesn't exist) a test that verifies any non-None `portrait_url` value from views is either an absolute URL or starts with `/`:

```python
"""Verify portrait_url emission from views.py uses resolve_asset_url."""
from __future__ import annotations

import pytest

from sidequest.server.asset_urls import resolve_asset_url


def test_portrait_url_via_resolver_default_is_cdn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    rel = "artifacts/dungeon_survivor/abc123/portraits/deadbeef.png"
    assert resolve_asset_url(rel) == f"https://cdn.slabgorb.com/{rel}"


def test_portrait_url_via_resolver_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "local")
    rel = "artifacts/dungeon_survivor/abc123/portraits/deadbeef.png"
    assert resolve_asset_url(rel) == f"/renders/{rel}"
```

- [ ] **Step 10.3: Run the test, expect green (it's calling the resolver, not views)**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/server/test_views.py -v
```
Expected: 2 passed.

- [ ] **Step 10.4: Refactor views.py:416 — confirm the site is None today and locate any sibling site that hands a real path**

The line at 416 is `portrait_url=None,` per the earlier grep. Search for the *other* place in the server where `portrait_url` is computed (likely in a character pre-gen path, scrapbook, or daemon-callback handler):

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -rn "portrait_url\s*=\s*[^N]" sidequest/ --include="*.py" | grep -v ": str | None = None"
```
For each non-None assignment found, replace the literal-path expression with `resolve_asset_url(rel)` where `rel` is the artifacts-prefixed relative path (`f"artifacts/{world}/{session}/portraits/{sha}.png"`).

For sites that today do `portrait_url=str(some_local_path)`, the rewrite is:
```python
portrait_url = resolve_asset_url(
    f"artifacts/{world_slug}/{session_id}/portraits/{sha256}.png"
)
```

- [ ] **Step 10.5: Run the full server test suite**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v -x
```
Expected: green. If a test asserted on the literal local-path form, update its assertion to match the resolved URL form (preserving its monkeypatch on `SIDEQUEST_ASSET_BASE_URL` to keep determinism).

- [ ] **Step 10.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add -p   # review every chunk
git commit -m "feat(server): route portrait_url emission through resolve_asset_url"
```

---

## Task 11 — Server: Route Render Mounts URLs Through Resolver

**Files:**
- Modify: `sidequest-server/sidequest/server/render_mounts.py` — `url_for_path` / `ensure_render_mount` callers

**Why:** Existing render-completed handlers turn an absolute filesystem path into a `/renders/...` URL. Post-migration, daemon-generated artifacts are uploaded directly to R2 by the daemon (Task 12-13) and the *daemon* returns a relative R2 path. The server then runs that path through `resolve_asset_url`. This task addresses callers that today consume the daemon's local-path-to-/renders/-URL pipeline.

- [ ] **Step 11.1: Find every caller of `url_for_path` and `ensure_render_mount`**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
grep -rn "url_for_path\|ensure_render_mount" sidequest/ --include="*.py"
```
Note each caller. Expected sites: `session_handler.py`, `narration_apply.py`, possibly `dispatch/`.

- [ ] **Step 11.2: Add a wrapper `resolve_artifact_url`**

Edit `sidequest-server/sidequest/server/render_mounts.py`. Add at the bottom:
```python
def resolve_artifact_url(relative_artifact_path: str | None) -> str | None:
    """New code path: daemon returns an R2-relative path
    (``artifacts/<world>/<session>/...``), server hands UI an absolute URL
    via the asset_urls seam.

    Returns None for a None/empty input — callers must surface that as an
    image_unavailable event (no silent fallback).
    """
    if not relative_artifact_path:
        return None
    from sidequest.server.asset_urls import resolve_asset_url

    return resolve_asset_url(relative_artifact_path)
```

- [ ] **Step 11.3: Update each caller**

For each caller identified in Step 11.1: when the caller is in the *new* code path (daemon already uploaded to R2, returned a relative artifact path), call `resolve_artifact_url(relative)` instead of `ensure_render_mount(app, absolute_disk_path)`. When the caller is in a *legacy* read path (looking at a pre-migration on-disk artifact), keep `ensure_render_mount`.

The decision rule:
- If the daemon message includes an `r2_key` field (introduced in Task 13) → new path → `resolve_artifact_url(message.r2_key)`.
- Otherwise → legacy on-disk path → `ensure_render_mount(app, message.image_path)`.

Edit each caller to branch on the presence of `r2_key`.

> **Engineer note:** Resist the temptation to delete `register_root` / `ensure_render_mount` — pre-migration on-disk artifacts under `~/.sidequest/renders` still need them. Per the spec "Out of Scope," we do not backfill those. They live until users delete them.

- [ ] **Step 11.4: Add a unit test for the wrapper**

Append to `sidequest-server/tests/server/test_views.py` (or wherever render-mount tests live):
```python
def test_resolve_artifact_url_none_passthrough() -> None:
    from sidequest.server.render_mounts import resolve_artifact_url

    assert resolve_artifact_url(None) is None
    assert resolve_artifact_url("") is None


def test_resolve_artifact_url_routes_through_asset_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIDEQUEST_ASSET_BASE_URL", raising=False)
    from sidequest.server.render_mounts import resolve_artifact_url

    url = resolve_artifact_url("artifacts/w/s/portraits/abc.png")
    assert url == "https://cdn.slabgorb.com/artifacts/w/s/portraits/abc.png"
```

- [ ] **Step 11.5: Run the full server test suite**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest -v -x
```
Expected: green.

- [ ] **Step 11.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add -p
git commit -m "feat(server): branch render-mount callers on r2_key vs legacy disk path"
```

---

## Task 12 — Daemon: `r2_writer.py` Module

**Files:**
- Create: `sidequest-daemon/sidequest_daemon/media/r2_writer.py`
- Create: `sidequest-daemon/tests/media/test_r2_writer.py`
- Modify: `sidequest-daemon/pyproject.toml` (add `boto3` dependency)

**Why:** Direct daemon → R2 upload. Failures must propagate, not be masked by a fake URL.

- [ ] **Step 12.1: Add boto3 dependency**

Edit `sidequest-daemon/pyproject.toml`. Find the `dependencies = [` block (or `[project.dependencies]`/`[tool.poetry.dependencies]`, depending on layout) and add `"boto3>=1.34"` (or current pinned major).

Run to verify it installs cleanly:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv sync
```
Expected: `boto3` shows up in the lock file. No errors.

- [ ] **Step 12.2: Write the failing tests**

Create `sidequest-daemon/tests/media/test_r2_writer.py`:
```python
"""Unit tests for r2_writer.upload_artifact (mocked S3)."""
from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from sidequest_daemon.media import r2_writer


def _bytes(payload: bytes = b"x") -> bytes:
    return payload * 32


def _expected_key(world: str, session: str, kind: str, content: bytes, ext: str) -> str:
    sha = hashlib.sha256(content).hexdigest()
    return f"artifacts/{world}/{session}/{kind}/{sha}.{ext}"


@pytest.fixture
def fake_client() -> MagicMock:
    return MagicMock()


def test_upload_artifact_returns_relative_path(fake_client: MagicMock) -> None:
    content = _bytes(b"abc")
    expected = _expected_key("w1", "s1", "portraits", content, "png")
    with patch.object(r2_writer, "_client", lambda: fake_client):
        rel = r2_writer.upload_artifact(
            world_slug="w1",
            session_id="s1",
            kind="portraits",
            content_bytes=content,
            content_type="image/png",
        )
    assert rel == expected
    fake_client.put_object.assert_called_once()
    kwargs = fake_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "sidequest"
    assert kwargs["Key"] == expected
    assert kwargs["ContentType"] == "image/png"
    assert kwargs["CacheControl"] == "public, max-age=86400"
    assert kwargs["Body"] == content


def test_upload_artifact_invalid_kind_raises() -> None:
    with pytest.raises(ValueError, match="kind"):
        r2_writer.upload_artifact(
            world_slug="w",
            session_id="s",
            kind="bogus",  # type: ignore[arg-type]
            content_bytes=b"x",
            content_type="image/png",
        )


def test_upload_artifact_unknown_content_type_raises() -> None:
    with pytest.raises(ValueError, match="content_type"):
        r2_writer.upload_artifact(
            world_slug="w",
            session_id="s",
            kind="portraits",
            content_bytes=b"x",
            content_type="application/x-bogus",
        )


def test_upload_artifact_propagates_client_errors(fake_client: MagicMock) -> None:
    fake_client.put_object.side_effect = RuntimeError("boom")
    with patch.object(r2_writer, "_client", lambda: fake_client):
        with pytest.raises(RuntimeError, match="boom"):
            r2_writer.upload_artifact(
                world_slug="w",
                session_id="s",
                kind="portraits",
                content_bytes=b"x",
                content_type="image/png",
            )


@pytest.mark.parametrize(
    "kind,ctype,ext",
    [
        ("portraits", "image/png", "png"),
        ("poi", "image/png", "png"),
        ("scenes", "image/jpeg", "jpg"),
        ("music", "audio/ogg", "ogg"),
        ("sfx", "audio/ogg", "ogg"),
    ],
)
def test_upload_artifact_extension_for_content_type(
    fake_client: MagicMock, kind: str, ctype: str, ext: str
) -> None:
    content = b"data" * 16
    expected = _expected_key("w", "s", kind, content, ext)
    with patch.object(r2_writer, "_client", lambda: fake_client):
        rel = r2_writer.upload_artifact(
            world_slug="w",
            session_id="s",
            kind=kind,  # type: ignore[arg-type]
            content_bytes=content,
            content_type=ctype,
        )
    assert rel == expected
```

Make sure `sidequest-daemon/tests/media/__init__.py` exists.

- [ ] **Step 12.3: Run the failing tests**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest tests/media/test_r2_writer.py -v
```
Expected: ImportError.

- [ ] **Step 12.4: Implement `r2_writer.py`**

Create `sidequest-daemon/sidequest_daemon/media/r2_writer.py`:
```python
"""Direct daemon → R2 artifact uploader.

Per CLAUDE.md no-silent-fallback: any boto error propagates. The daemon's
caller is responsible for surfacing the failure to the server, which emits
an image_unavailable event. We never hand back a fake URL.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Final, Literal

import boto3
from botocore.client import BaseClient

ArtifactKind = Literal["portraits", "poi", "scenes", "music", "sfx"]
_VALID_KINDS: Final[frozenset[str]] = frozenset(
    {"portraits", "poi", "scenes", "music", "sfx"}
)

_EXT_FOR_CONTENT_TYPE: Final[dict[str, str]] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/flac": "flac",
}

CACHE_CONTROL_ARTIFACTS: Final[str] = "public, max-age=86400"
BUCKET: Final[str] = "sidequest"


@lru_cache(maxsize=1)
def _client() -> BaseClient:
    """Lazy boto3 client singleton; respects env mutation across tests
    via the patch.object(r2_writer, "_client", ...) idiom."""
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_S3_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def upload_artifact(
    *,
    world_slug: str,
    session_id: str,
    kind: ArtifactKind,
    content_bytes: bytes,
    content_type: str,
) -> str:
    """Upload `content_bytes` to R2 under
    ``artifacts/<world>/<session>/<kind>/<sha256>.<ext>``.

    Returns the relative key. Raises ValueError on invalid kind/content_type.
    Raises any boto3/HTTP error verbatim — caller must propagate, not swallow.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"kind must be one of {sorted(_VALID_KINDS)}, got {kind!r}"
        )
    if content_type not in _EXT_FOR_CONTENT_TYPE:
        raise ValueError(
            f"content_type must be one of {sorted(_EXT_FOR_CONTENT_TYPE)}, "
            f"got {content_type!r}"
        )

    ext = _EXT_FOR_CONTENT_TYPE[content_type]
    sha = hashlib.sha256(content_bytes).hexdigest()
    key = f"artifacts/{world_slug}/{session_id}/{kind}/{sha}.{ext}"

    _client().put_object(
        Bucket=BUCKET,
        Key=key,
        Body=content_bytes,
        ContentType=content_type,
        CacheControl=CACHE_CONTROL_ARTIFACTS,
    )
    return key
```

- [ ] **Step 12.5: Run the tests, expect green**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest tests/media/test_r2_writer.py -v
```
Expected: 8 passed (4 named + 5 parametrised, with one overlap; concretely the file collects to ~9 cases).

- [ ] **Step 12.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
git checkout -b feat/r2-writer
git add sidequest_daemon/media/r2_writer.py tests/media/test_r2_writer.py tests/media/__init__.py pyproject.toml uv.lock
git commit -m "feat(daemon): add r2_writer.upload_artifact (sha256-keyed, fail-loud)"
```

---

## Task 13 — Daemon: Wire R2 Writer Into Image Pipeline

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py:453-457`
- Modify: `sidequest-daemon/sidequest_daemon/media/daemon.py` — render-completed message construction

**Why:** Today the worker saves to disk and emits the disk path as `image_url`. Post-migration, the worker (or its caller) calls `upload_artifact` and emits the relative R2 key, leaving the disk write as a transient cache (cleared at daemon teardown).

- [ ] **Step 13.1: Inspect the current worker emission**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
sed -n '440,470p' sidequest_daemon/media/workers/zimage_mlx_worker.py
```
Note the dict shape returned to the daemon main loop. The fields likely include `image_url`, `image_path`, and metadata. The plan adds an `r2_key` field alongside (not replacing) `image_url` so the legacy path keeps working during cutover.

- [ ] **Step 13.2: Write the integration test (mocked R2)**

Create `sidequest-daemon/tests/media/test_zimage_worker_r2.py`:
```python
"""Verify the zimage worker calls r2_writer.upload_artifact and emits r2_key."""
from __future__ import annotations

from unittest.mock import patch

import pytest

# The worker has heavy ML deps; we test the R2 wiring in isolation by
# extracting the key-construction logic into a helper. If that's not yet
# feasible, this test is marked xfail until the worker is refactored to
# accept an injected uploader.


@pytest.fixture(autouse=True)
def _r2_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("R2_S3_ENDPOINT", "https://endpoint.example")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "y")


def test_worker_emits_r2_key_after_save() -> None:
    from sidequest_daemon.media import r2_writer
    from sidequest_daemon.media.workers import zimage_mlx_worker

    fake_bytes = b"\x89PNG\r\n\x1a\n" + b"x" * 64
    captured: dict[str, object] = {}

    def fake_upload(*, world_slug, session_id, kind, content_bytes, content_type):
        captured.update(
            world_slug=world_slug,
            session_id=session_id,
            kind=kind,
            content_type=content_type,
        )
        return f"artifacts/{world_slug}/{session_id}/{kind}/abcd.png"

    with patch.object(r2_writer, "upload_artifact", side_effect=fake_upload):
        result = zimage_mlx_worker.upload_render_to_r2(
            content_bytes=fake_bytes,
            world_slug="dungeon",
            session_id="0d8e",
            kind="portraits",
            content_type="image/png",
        )

    assert result == "artifacts/dungeon/0d8e/portraits/abcd.png"
    assert captured["world_slug"] == "dungeon"
    assert captured["session_id"] == "0d8e"
    assert captured["kind"] == "portraits"
    assert captured["content_type"] == "image/png"
```

- [ ] **Step 13.3: Run the test to verify it fails**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest tests/media/test_zimage_worker_r2.py -v
```
Expected: AttributeError (no `upload_render_to_r2`).

- [ ] **Step 13.4: Add the helper to the worker**

Edit `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py`. Add at module level (above the worker class):
```python
from sidequest_daemon.media import r2_writer


def upload_render_to_r2(
    *,
    content_bytes: bytes,
    world_slug: str,
    session_id: str,
    kind: r2_writer.ArtifactKind,
    content_type: str,
) -> str:
    """Thin wrapper: upload a freshly-generated render to R2, return the
    relative key. Surfaces upload errors to the caller (no swallowing)."""
    return r2_writer.upload_artifact(
        world_slug=world_slug,
        session_id=session_id,
        kind=kind,
        content_bytes=content_bytes,
        content_type=content_type,
    )
```

- [ ] **Step 13.5: Hook the worker save site to call the helper**

Edit `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py` near line 453-457. Today's snippet:
```python
image_path = self.output_dir / filename
image.save(str(image_path))
return {
    ...
    "image_url": str(image_path),
}
```
Becomes:
```python
image_path = self.output_dir / filename
image.save(str(image_path))

r2_key: str | None = None
try:
    with open(image_path, "rb") as fh:
        content = fh.read()
    r2_key = upload_render_to_r2(
        content_bytes=content,
        world_slug=request.world_slug,
        session_id=request.session_id,
        kind="portraits" if request.kind == "portrait" else request.kind,
        content_type="image/png",
    )
except Exception:
    # Per CLAUDE.md: surface, don't swallow. The daemon main loop is
    # responsible for emitting the failure span and propagating an
    # image_unavailable event back to the server.
    raise

return {
    ...
    "image_url": str(image_path),  # legacy local path — still emitted for
                                   # in-flight back-compat
    "r2_key": r2_key,
}
```

> **Engineer note:** Replace `request.world_slug`, `request.session_id`, and `request.kind` with the actual field names of the worker's request payload. If the worker doesn't currently receive world/session, propagate them from `daemon.py` first (Step 13.7).

- [ ] **Step 13.6: Run the worker R2 test, expect green**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest tests/media/test_zimage_worker_r2.py -v
```
Expected: 1 passed.

- [ ] **Step 13.7: Propagate world_slug + session_id to the worker request**

Edit `sidequest-daemon/sidequest_daemon/media/daemon.py` — at the dispatch site that creates the worker request, add `world_slug` and `session_id` fields drawn from the inbound message. If the inbound protocol doesn't yet carry these, add them: this is a sidequest-server → sidequest-daemon protocol change. (If the change is non-trivial, file as a follow-up subtask and stub `world_slug="unknown"` / `session_id="unknown"` for the moment with a TODO referencing this plan and a tracker entry; the playtest verification of Task 16 catches the wiring.)

- [ ] **Step 13.8: Run the daemon test suite**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest -v -x
```
Expected: green. Fix any test that asserted on the previous worker payload shape (must add an `r2_key` slot).

- [ ] **Step 13.9: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
git add -p
git commit -m "feat(daemon): upload renders to R2 and emit r2_key alongside legacy image_url"
```

---

## Task 14 — Daemon: OTEL Spans for R2 Upload

**Files:**
- Modify: `sidequest-daemon/sidequest_daemon/media/r2_writer.py` (emit start/success/failure spans)
- Create: `sidequest-daemon/tests/media/test_r2_writer_otel.py`

**Why:** Without OTEL, the GM panel can't tell whether the daemon actually uploaded. Per CLAUDE.md observability principle, every subsystem decision emits.

> The daemon's OTEL plumbing follows whatever pattern is already established in `sidequest-daemon/`. Audit before writing — emit_event, otel module, `start_as_current_span`, etc. The plan below uses a plain `tracer.start_as_current_span`; replace with the daemon's house pattern if different.

- [ ] **Step 14.1: Inspect daemon OTEL conventions**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
grep -rn "trace.get_tracer\|start_as_current_span\|otel\|opentelemetry" sidequest_daemon/ --include="*.py" | head -20
```
Note the established pattern — a tracer factory, a span decorator, etc.

- [ ] **Step 14.2: Write the failing OTEL test**

Create `sidequest-daemon/tests/media/test_r2_writer_otel.py`:
```python
"""Verify r2_writer emits start/success/failure spans."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from sidequest_daemon.media import r2_writer


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    with patch.object(r2_writer, "_tracer_provider_for_tests", provider):
        yield exp


def test_success_emits_start_and_success(exporter: InMemorySpanExporter) -> None:
    fake = MagicMock()
    with patch.object(r2_writer, "_client", lambda: fake):
        r2_writer.upload_artifact(
            world_slug="w",
            session_id="s",
            kind="portraits",
            content_bytes=b"x" * 16,
            content_type="image/png",
        )
    names = [s.name for s in exporter.get_finished_spans()]
    assert "daemon.r2.upload.start" in names
    assert "daemon.r2.upload.success" in names
    assert "daemon.r2.upload.failure" not in names


def test_failure_emits_start_and_failure(exporter: InMemorySpanExporter) -> None:
    fake = MagicMock()
    fake.put_object.side_effect = RuntimeError("simulated outage")
    with patch.object(r2_writer, "_client", lambda: fake):
        with pytest.raises(RuntimeError):
            r2_writer.upload_artifact(
                world_slug="w",
                session_id="s",
                kind="portraits",
                content_bytes=b"x" * 16,
                content_type="image/png",
            )
    names = [s.name for s in exporter.get_finished_spans()]
    assert "daemon.r2.upload.start" in names
    assert "daemon.r2.upload.failure" in names
    failure = [s for s in exporter.get_finished_spans() if s.name == "daemon.r2.upload.failure"][0]
    assert failure.attributes is not None
    assert failure.attributes["upload.error_class"] == "RuntimeError"
```

- [ ] **Step 14.3: Run the test, confirm failure**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest tests/media/test_r2_writer_otel.py -v
```
Expected: AssertionError — span names not present.

- [ ] **Step 14.4: Wire OTEL into r2_writer**

Edit `sidequest-daemon/sidequest_daemon/media/r2_writer.py`. Add at the top:
```python
import time
from typing import cast

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# Test seam — overridden via patch.object in unit tests to inject an
# in-memory exporter. Production: read the global tracer provider.
_tracer_provider_for_tests: TracerProvider | None = None


def _get_tracer() -> trace.Tracer:
    if _tracer_provider_for_tests is not None:
        return _tracer_provider_for_tests.get_tracer("sidequest_daemon.media.r2_writer")
    return trace.get_tracer("sidequest_daemon.media.r2_writer")
```

And rewrite `upload_artifact` to wrap the put_object call:
```python
def upload_artifact(
    *,
    world_slug: str,
    session_id: str,
    kind: ArtifactKind,
    content_bytes: bytes,
    content_type: str,
) -> str:
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"kind must be one of {sorted(_VALID_KINDS)}, got {kind!r}"
        )
    if content_type not in _EXT_FOR_CONTENT_TYPE:
        raise ValueError(
            f"content_type must be one of {sorted(_EXT_FOR_CONTENT_TYPE)}, "
            f"got {content_type!r}"
        )

    ext = _EXT_FOR_CONTENT_TYPE[content_type]
    sha = hashlib.sha256(content_bytes).hexdigest()
    key = f"artifacts/{world_slug}/{session_id}/{kind}/{sha}.{ext}"
    size = len(content_bytes)
    tracer = _get_tracer()

    with tracer.start_as_current_span("daemon.r2.upload.start") as start_span:
        start_span.set_attribute("upload.kind", kind)
        start_span.set_attribute("upload.world", world_slug)
        start_span.set_attribute("upload.session", session_id)
        start_span.set_attribute("upload.bytes", size)

    t0 = time.perf_counter()
    try:
        _client().put_object(
            Bucket=BUCKET,
            Key=key,
            Body=content_bytes,
            ContentType=content_type,
            CacheControl=CACHE_CONTROL_ARTIFACTS,
        )
    except Exception as exc:
        with tracer.start_as_current_span("daemon.r2.upload.failure") as fail_span:
            fail_span.set_attribute("upload.kind", kind)
            fail_span.set_attribute("upload.error_class", exc.__class__.__name__)
            fail_span.set_attribute("upload.error_message", str(exc))
            fail_span.set_attribute("upload.retry_attempt", 0)
        raise

    dt_ms = int((time.perf_counter() - t0) * 1000)
    with tracer.start_as_current_span("daemon.r2.upload.success") as ok_span:
        ok_span.set_attribute("upload.kind", kind)
        ok_span.set_attribute("upload.key", key)
        ok_span.set_attribute("upload.ms", dt_ms)
        ok_span.set_attribute("upload.bytes", size)
    return key
```

- [ ] **Step 14.5: Run the OTEL test, expect green**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest tests/media/test_r2_writer_otel.py -v
```
Expected: 2 passed.

- [ ] **Step 14.6: Re-run the original r2_writer tests to confirm no regression**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
uv run pytest tests/media/test_r2_writer.py -v
```
Expected: still all passing.

- [ ] **Step 14.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
git add sidequest_daemon/media/r2_writer.py tests/media/test_r2_writer_otel.py
git commit -m "feat(daemon): emit start/success/failure spans on R2 upload"
```

---

## Task 15 — Justfile + .env.example: Wire Env Vars Through Recipes

**Files:**
- Modify: `justfile` (orchestrator)
- Create: `.env.example` (orchestrator)

**Why:** Daemon needs `R2_*` exports to upload; server reads `SIDEQUEST_ASSET_BASE_URL` to toggle the seam; both should be documented for new clones.

- [ ] **Step 15.1: Confirm current recipe contents**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
sed -n '1,60p' justfile
```
Note where `server`, `client`, `daemon` recipes export env vars.

- [ ] **Step 15.2: Update each recipe**

Edit `justfile`. In the `server`, `daemon`, and `up` recipes, prepend the new exports inline before the launch command. For the `server` recipe:
```bash
SIDEQUEST_GENRE_PACKS={{content}} \
SIDEQUEST_RENDER_ENABLED=1 \
SIDEQUEST_ASSET_BASE_URL="${SIDEQUEST_ASSET_BASE_URL:-https://cdn.slabgorb.com}" \
    uv run uvicorn sidequest.server.app:create_app \
        --factory --reload --host 127.0.0.1 --port 8765 {{flags}} 2>&1 \
    | tee "$log"
```
For the `daemon` recipe, ensure `R2_S3_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` are passed through (they should flow from the user's shell env automatically; add explicit `: "${R2_S3_ENDPOINT:?must be set in shell}"` style guards):
```bash
: "${R2_S3_ENDPOINT:?R2_S3_ENDPOINT must be set in shell}"
: "${R2_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID must be set in shell}"
: "${R2_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY must be set in shell}"
```
This is no-silent-fallback: a missing env aborts daemon start with a clear message instead of producing fake URLs at runtime.

- [ ] **Step 15.3: Create `.env.example`**

Create `/Users/slabgorb/Projects/oq-1/.env.example`:
```bash
# SideQuest environment template.
# Copy to .env (NOT committed) or export from your shell rc.

# --- R2 / Cloudflare media storage ---------------------------------------
# Required for daemon uploads. Get from CF dashboard or 1Password.
R2_S3_ENDPOINT="https://a55aafa9b0691f828cd6864be28c1674.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID="<paste S3 access key id here>"
R2_SECRET_ACCESS_KEY="<paste S3 secret access key here>"

# --- Server URL emission -------------------------------------------------
# Default: production CDN. Set to "local" for offline dev (serves from
# SIDEQUEST_GENRE_PACKS via the /genre/* mount).
SIDEQUEST_ASSET_BASE_URL="https://cdn.slabgorb.com"

# --- Genre / content paths -----------------------------------------------
# Path to sidequest-content checkout (typically "$REPO/sidequest-content").
SIDEQUEST_GENRE_PACKS="$REPO/sidequest-content/genre_packs"

# --- Renders -------------------------------------------------------------
# 0 = disable on-disk render mounts (post-migration default once R2 is GA)
# 1 = legacy on-disk renders still served via /renders/*
SIDEQUEST_RENDER_ENABLED=1
```

- [ ] **Step 15.4: Verify the recipes load**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
just --list 2>&1 | head -10
```
Expected: just lists recipes without parse error. Then quick-launch the server in a side terminal (`just server`) and confirm it starts cleanly with the new env block.

- [ ] **Step 15.5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add justfile .env.example
git commit -m "feat(orchestrator): document and wire R2 env vars in justfile + .env.example"
```

---

## Task 16 — End-to-End Verification in Dev

**Files:**
- None (operational task).

**Why:** The migration is byte-for-byte at the URL layer; the only way to catch surviving local-path emissions is to play through a session and watch the network panel.

- [ ] **Step 16.1: Boot all services**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
just up 2>&1 | tee /tmp/r2-cutover-boot.log
```
Wait for all three to come up. Expected: server logs `Application startup complete`, daemon logs ML model loaded, UI is reachable on `:5173`.

- [ ] **Step 16.2: Open the UI and DevTools Network panel filtered to `cdn.slabgorb.com`**

Open `http://localhost:5173`. In DevTools → Network, set the filter to `cdn.slabgorb.com`. Start a new session — pick a genre pack with curated audio (e.g. caverns_and_claudes) and a world.

- [ ] **Step 16.3: Walk a full session**

Play ~5-10 turns covering:
- Title screen audio (curated music)
- Combat encounter (curated combat track + SFX)
- Portrait generation (daemon → R2 round-trip)
- POI / scene image generation
- A second-act music swap

- [ ] **Step 16.4: Audit the network panel**

Confirm:
- Every audio fetch lands on `cdn.slabgorb.com/genre_packs/...` with HTTP 200.
- Every newly-generated image lands on `cdn.slabgorb.com/artifacts/<world>/<session>/...` with HTTP 200.
- No requests to `/genre/*` or `/renders/*` for migrated assets.
- No CORS errors in the Console panel (the AudioCache fetch is the trigger).

- [ ] **Step 16.5: Audit the GM panel for OTEL coverage**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1
just otel 2>&1 &
```
Open the GM dashboard. Confirm presence of:
- `daemon.r2.upload.start` events during portrait/POI generation
- `daemon.r2.upload.success` events with `upload.bytes` > 0 and `upload.ms` > 0
- `server.asset_url.resolved` events with `asset.mode == "cdn"`

If any are missing, do not proceed — go back and find the unwired call site.

- [ ] **Step 16.6: Test the rollback path**

Stop services. Run:
```bash
SIDEQUEST_ASSET_BASE_URL="local" just up
```
Open the UI. Confirm audio plays via `/genre/*` (the local-serve fallback). This proves the rollback toggle works.

Stop services again, restart with default (CDN).

- [ ] **Step 16.7: Tear down on completion**

Run: `just down`.

- [ ] **Step 16.8: Commit (no code changes — operational note in the PR body is enough; if a tweak surfaces, commit that here)**

If the verification surfaced bugs and you fixed them inline, commit the fixes now with a message like `fix(server): handle <case> exposed by E2E`. Otherwise this task has no commit.

---

## Task 17 — LFS Strip on `sidequest-content`

**Files:**
- Operational on `sidequest-content` repo (history rewrite).
- `sidequest-content/.gitattributes` retained (defensive — catches future stray binaries).

**Why:** Reclaim ~931 MB. Only safe after Task 16 is fully green and confirmed by Keith.

> **DESTRUCTIVE OPERATION.** Requires explicit user confirmation. Do not run autonomously even in auto mode. Stop and ask.

- [ ] **Step 17.1: Pre-flight check**

Confirm with user (Keith) that:
- Task 16 verification was 100% green.
- The oq-2 dual checkout is on a clean state (no uncommitted work) — the engineer should run `cd /Users/slabgorb/Projects/oq-2/sidequest-content && git status` and confirm clean.
- A snapshot of `sidequest-content` exists (e.g. zip on external storage, GitHub backup) so the LFS objects can be re-pushed if R2 vanishes.

**Block here until Keith says go.**

- [ ] **Step 17.2: Branch the strip**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git checkout main
git pull
git checkout -b chore/lfs-strip-r2-cutover
```

- [ ] **Step 17.3: Run the LFS export**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git lfs migrate export \
  --include="*.ogg,*.png,*.wav,*.mp3,*.jpg,*.jpeg,*.webp,*.flac" \
  --everything
```
Expected: rewrites every commit on every branch, producing a smaller `.git`. Output should mention `... rewriting commits` and finish without error.

- [ ] **Step 17.4: Verify locally**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git lfs ls-files | wc -l
du -sh .git
```
Expected: `git lfs ls-files` returns 0; `.git` is dramatically smaller.

- [ ] **Step 17.5: Push the rewrite**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
git push --force-with-lease origin chore/lfs-strip-r2-cutover:main
```
**Note:** force-pushing to `main`. This is the explicit destructive action — only do it after Keith has acknowledged.

- [ ] **Step 17.6: Coordinate the oq-2 reset**

Run (from a terminal with cwd in `oq-2`):
```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git fetch
git reset --hard origin/main
```
Expected: oq-2 now matches the rewritten history. `git lfs ls-files` returns 0 there too.

- [ ] **Step 17.7: Confirm `.gitattributes` is intact**

Run:
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content
cat .gitattributes
```
Expected: still lists the LFS extensions (defensive — they catch a stray future binary commit even though no LFS-tracked files exist now).

---

## Task 18 — Cleanup: Revoke Admin-Scope Cloudflare Tokens

**Files:**
- None (operational task).

**Why:** Least-privilege hygiene. Now that the migration has proven out, any admin-scope CF tokens used during setup should be rotated to the read-only / scoped tokens that remain.

- [ ] **Step 18.1: List active CF API tokens**

In the Cloudflare dashboard → My Profile → API Tokens, list all active tokens for the `slabgorb` account.

- [ ] **Step 18.2: Identify which tokens to revoke**

Keep:
- `CLOUDFLARE_API_TOKEN_SIDEQUEST` (R2 buckets read/write, R2 custom domains read/write, zone read on `slabgorb.com`)
- The S3 keys (`R2_ACCESS_KEY_ID/SECRET`) — these are R2-bucket-scoped already.

Revoke:
- Any token broader than that (account-wide admin, all-zones-edit, etc.) used during setup.

- [ ] **Step 18.3: Revoke**

For each token to revoke: dashboard → ⋯ → Delete. Confirm the deletion.

- [ ] **Step 18.4: Verify the kept token still works**

Run:
```bash
curl -sH "Authorization: Bearer $CLOUDFLARE_API_TOKEN_SIDEQUEST" \
  https://api.cloudflare.com/client/v4/accounts/a55aafa9b0691f828cd6864be28c1674/r2/buckets \
  | head -20
```
Expected: JSON listing the `sidequest` bucket. Anything else means stop and recheck which token got revoked.

---

## Task 19 — Open the Pull Requests

**Files:**
- None (operational task — opens PRs in three repos).

- [ ] **Step 19.1: Push and PR each repo**

Run (one command per repo, sequential):

Orchestrator:
```bash
cd /Users/slabgorb/Projects/oq-1
git push -u origin feat/r2-media-migration
gh pr create --base main --title "feat(r2): media migration to Cloudflare R2 (scripts, justfile, env)" \
  --body "$(cat <<'EOF'
## Summary
- Adds `scripts/r2_sync_packs.py` and `scripts/r2_verify_packs.py` for Phase A LFS→R2 mirror.
- Wires `R2_*` and `SIDEQUEST_ASSET_BASE_URL` into `justfile` and adds `.env.example`.
- See spec: `docs/superpowers/specs/2026-05-03-cloudflare-r2-media-migration-design.md`.
- See plan: `docs/superpowers/plans/2026-05-03-cloudflare-r2-media-migration.md`.

## Test plan
- [ ] `uv run pytest scripts/tests -v` green
- [ ] Real sync ran in dev (931 MB) and second-run reports 0 uploads, 0 bytes (idempotency)
- [ ] `r2_verify_packs.py` reports VERIFY OK
EOF
)"
```

Server (working in `sidequest-server`, branch `feat/r2-asset-urls`):
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git push -u origin feat/r2-asset-urls
gh pr create --base develop --title "feat(server): single-seam asset URL resolver + OTEL span" \
  --body "$(cat <<'EOF'
## Summary
- Adds `resolve_asset_url()` and routes audio loader, portrait_url, render-mount callers through it.
- Adds `server.asset_url.resolved` OTEL span (flat-only).
- Local-serve fallback preserved for offline dev (`SIDEQUEST_ASSET_BASE_URL=local`).

## Test plan
- [ ] `uv run pytest tests/server/test_asset_urls.py -v`
- [ ] `uv run pytest tests/genre/test_audio_url_resolution.py -v`
- [ ] `uv run pytest tests/telemetry/spans/test_asset_url_span.py -v`
- [ ] Full server suite green
EOF
)"
```

Daemon (working in `sidequest-daemon`, branch `feat/r2-writer`):
```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-daemon
git push -u origin feat/r2-writer
gh pr create --base develop --title "feat(daemon): direct R2 uploads for generated artifacts + OTEL" \
  --body "$(cat <<'EOF'
## Summary
- Adds `r2_writer.upload_artifact` (sha256-keyed, fail-loud, no silent fallback).
- Wires the zimage worker to upload renders and emit `r2_key` alongside legacy `image_url`.
- Emits `daemon.r2.upload.{start,success,failure}` spans for every PUT.

## Test plan
- [ ] `uv run pytest tests/media/test_r2_writer.py -v`
- [ ] `uv run pytest tests/media/test_r2_writer_otel.py -v`
- [ ] `uv run pytest tests/media/test_zimage_worker_r2.py -v`
- [ ] E2E: Task 16 of the migration plan verified `daemon.r2.upload.success` fires during dev session
EOF
)"
```

---

## Self-Review

**Spec coverage (against `docs/superpowers/specs/2026-05-03-cloudflare-r2-media-migration-design.md`):**

| Spec Section | Plan Coverage |
|---|---|
| §1 Custom Domain & Bucket Access — public read | Already operational, confirmed by spec. No task needed. |
| §1 CORS rule | Task 2 |
| §1 Cache-Control immutable for `genre_packs/` | Task 4 (sets it on every PUT) |
| §1 Cache-Control 24h for `artifacts/` | Task 12 (`CACHE_CONTROL_ARTIFACTS`) |
| §2 Bucket layout (genre_packs/, artifacts/, probes/) | Tasks 4 (writes genre_packs/), 12 (writes artifacts/), `probes/` is operational (not exercised by code) |
| §3 Phase A sync | Tasks 4-6 |
| §3 Phase B cutover steps | Tasks 7-15 (server + daemon + justfile), 16 (verification), 17 (LFS strip) |
| §3 Rollback (unset SIDEQUEST_ASSET_BASE_URL) | Tasks 7 (resolver supports it), 16.6 (verified) |
| §3 Coordination scope (oq-2 reset) | Task 17.6 |
| §4 `resolve_asset_url` single seam | Task 7 |
| §4 Touch points (loader.py audio, views.py portrait_url, render_mounts) | Tasks 8, 10, 11 |
| §4 UI consumption unchanged | Implicit — UI already URL-agnostic; verification in Task 16 |
| §4 Daemon write side | Tasks 12-14 |
| §5 Daemon r2_writer module | Task 12 |
| §5 OTEL spans (4 spans) | Tasks 9 (server.asset_url.resolved), 14 (daemon.r2.upload.{start,success,failure}) |
| §5 Lifecycle rule | Task 3 |
| §5 Cost ceiling check | Verified at design time; no task needed (re-audited if the cost dashboard surprises) |
| §5 Verification plan | Task 16 |
| §5 Risk register | Tasks 12 (no silent fallback for upload), 16 (CORS), 17 (LFS strip with --force-with-lease + Keith confirmation) |
| Implementation order (1-10) | Mapped to Tasks 1-18 with 1:1+ correspondence |
| Acceptance criteria (1-10) | All ten criteria are verifiable through Tasks 6, 9, 14, 16, 17 |
| Out-of-scope items (world-first restructure, offline cache) | Filed as task #7, #8 in the spec. Not implemented here. |
| Follow-ups (token revocation) | Task 18 |

**Placeholder scan:** No `TBD`, no `implement later`, no `add appropriate error handling`. Each step contains the actual code or command. The deliberate "engineer note" callouts (Steps 8.4, 11.3, 13.7) flag judgement calls the engineer must make, but always with a concrete fallback pattern and an audit query.

**Type consistency:**
- `resolve_asset_url(relative_path: str) -> str` consistent across Tasks 7, 8, 9, 10, 11.
- `upload_artifact(*, world_slug, session_id, kind, content_bytes, content_type) -> str` consistent across Tasks 12, 13, 14.
- `ArtifactKind = Literal["portraits", "poi", "scenes", "music", "sfx"]` consistent.
- Span constants spelled `daemon.r2.upload.{start,success,failure}` and `server.asset_url.resolved` consistently.
- `SIDEQUEST_ASSET_BASE_URL` env var name consistent.
- `r2_key` field on worker payload consistent across Tasks 11 (server reads it), 13 (worker emits it).

**Risks the plan does not directly mitigate:**
- A subtle UI assumption that audio paths start with `/genre/` (it doesn't — UI is already URL-agnostic per the spec table, but not unit-tested). Task 16 catches this.
- The daemon's request payload may not yet carry world/session — Task 13.7 papers over this with a stub if needed and files a follow-up. The plan accepts this small bit of risk in favour of forward progress; the playtest in Task 16 will surface it as a `unknown/unknown/...` R2 prefix in the dashboard.

Plan is complete.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-03-cloudflare-r2-media-migration.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
