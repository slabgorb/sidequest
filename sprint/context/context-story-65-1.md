---
parent: context-epic-65.md
workflow: tdd
---

# Story 65-1: R2 asset manifest — checked-in tracking + YAML-derived gap audit

## Business Context

OQ-1 and OQ-2 render different asset classes and cannot see each other's R2
uploads — PNGs are gitignored, and `git pull local` only syncs YAML. This
story delivers the committed record (`r2_manifest.json`) and the intent-vs-
reality audit (`r2_audit.py`) so either clone can answer "what's already in R2?"
and "what's authored but not yet rendered/uploaded?" without re-rendering or
silently orphaning assets. This directly serves the dual-repo content workflow
Keith runs across two clones.

## Technical Guardrails

**Code placement (deviation from original story prose — see Design
Deviations):** All *code* lands in the orchestrator's `scripts/` tree alongside
`r2_sync_packs.py` / `r2_verify_packs.py`; tests in `scripts/tests/`. The
`r2_manifest.json` *data artifact* is committed under `sidequest-content/` so
`git pull local` syncs it between clones. Rationale: the entire R2 tooling
family + its pytest harness already live in the orchestrator; `sidequest-content`
has no Python test harness at all, and `r2_audit.py` must reuse
`iter_media_files` / generator path logic that lives in `scripts/`.

**Key derivation MUST reuse generator logic — do not hardcode the path strings
from the original story prose, which are wrong.** Authoritative conventions
(R2 key == local rel path, per `r2_sync_packs.sync()`):
- POI: `genre_packs/<genre>/worlds/<world>/assets/poi/<slug>.png`
  (slug from `history.yaml` `chapters.*.points_of_interest.*.slug`;
  `render_batch(image_subdir="poi")`).
- Portrait: `genre_packs/<genre>/images/portraits/<slug>.png` — **genre-flat**,
  not world-scoped (slug from `portrait_manifest.yaml` `characters.*.id` or
  `_slugify_name(name)`; `render_batch(image_subdir="portraits")`).
- Music: `genre_packs/<genre>/audio/music/<track>.ogg`
  (track = `*_input_params.json` filename prefix).

**Key files:**
- Extend `scripts/r2_sync_packs.py` — `sync()` currently returns only counts;
  it must also collect per-file records and write the manifest.
- New `scripts/r2_manifest.py` — boto3-free: `build_manifest_entry`,
  `write_manifest` (atomic, sorted), `load_manifest`.
- New `scripts/r2_audit.py` — pyyaml-only: `expected_keys`, `audit`,
  `format_report`, `main` (CLI, exit code).

**Constraints:**
- No silent fallbacks (CLAUDE.md): a missing/malformed YAML or manifest must
  fail loudly, not skip.
- Atomic write: temp file + `os.replace()` — never a partial manifest.
- Manifest core logic stays boto3-free so it tests without AWS deps; `boto3`
  must be added to orchestrator dev deps to exercise the `sync()` integration.

## Scope Boundaries

**In scope:**
- Part A: `r2_manifest.json` writer — one entry per R2 key
  (`{key, md5, size_bytes, uploaded_at, source}`), pretty-printed, key-sorted,
  atomic, idempotent; written by `sync()`.
- Part B: `r2_audit.py` — walk YAML, build expected-key set via generator
  logic, diff against manifest, report three categories
  (authored-but-not-rendered, rendered-but-not-uploaded, orphans), exit
  non-zero on any gap.

**Out of scope:**
- Part C: `r2_pull.py` (hydrate local files from manifest) — nice-to-have,
  defer if RED/GREEN run long; does not block the story.
- Runtime per-session asset tracking — that's story 65-2.
- Actual R2 network round-trips in tests — mock/avoid; test logic and contract.

## AC Context

**AC1 — manifest written atomically after sync.**
- `build_manifest_entry(path, content_root)` returns
  `{key, md5, size_bytes, uploaded_at, source}` where `key == rel.as_posix()`
  (matches `sync()`'s key), `md5` matches `_md5_of`, `source == "r2_sync_packs"`.
- `write_manifest(entries, path)` emits pretty JSON (2-space indent), entries
  **sorted by key** (stable diffs), via temp-file + `os.replace` (no partial
  file on interrupt).
- Idempotent: writing the same entries twice (any input order) yields byte-
  identical output. Round-trip `load_manifest` returns the same keys.
- Edge: empty entry list → valid empty manifest (`[]` or `{}`), not a crash.

**AC2 — audit walks YAML and reports gaps with correct keys.**
- `expected_keys(content_root)` builds the POI/portrait/music keys using the
  **correct** conventions above. A test with a synthetic fixture pack asserts a
  POI key is `.../worlds/<world>/assets/poi/<slug>.png` (and **not**
  `images/pois/...`) — this catches a naive impl that follows the wrong prose.
- `audit(content_root, manifest)` categorizes: authored-but-not-rendered
  (in expected, absent from manifest), orphans (in manifest, absent from
  expected), rendered-but-not-uploaded (local file present, absent from
  manifest).
- `main()` exit code: `0` when all three categories empty, `1` when any gap.
- Malformed YAML (e.g. `points_of_interest` entry missing `slug`) fails loudly.

**AC3 — report is human-readable and accurate.**
- `format_report(result)` includes pack/world context, per-entry asset type
  (portrait/POI/music), and a summary line with counts
  (expected, uploaded, gaps). No false positives: every reported gap is real.

**AC4 — integration / wiring.**
- `sync()` (dry-run path) produces a manifest with one entry per candidate file
  — the wiring test proving Part A is reachable from the uploader, not just a
  standalone helper.
- `r2_audit.py` is invokable as a CLI (`main()` exists, returns the exit code).

## Assumptions

- `boto3` will be added to the orchestrator dev dependencies (it is required to
  import `r2_sync_packs` at all; its absence currently breaks even the existing
  r2 test). If this proves contentious, the `sync()` integration test is the
  only test that needs it — all other logic is boto3-free.
- R2 keys mirror local relative paths 1:1 (true today in `sync()`); if that
  ever changes, the audit's key derivation must change with it.
- Music tracks map 1:1 from `*_input_params.json` to `<track>.ogg`; packs
  without an `audio/music/` dir contribute zero music keys (not an error).
