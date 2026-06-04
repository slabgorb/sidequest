---
parent: context-epic-65.md
workflow: tdd
---

# Story 65-15: r2_audit: parse pack audio.yaml in expected_keys() — classical_pd tracks mis-flagged as orphans; real audio 404s go uncaught

## Business Context

Epic 65 replaces git-LFS pointer tracking with a checked-in R2 manifest plus a
YAML-derived gap audit (`scripts/r2_audit.py`) that is the existence oracle for
the dual-clone (OQ-1/OQ-2) asset workflow. The audit's value is that it tells
the operator the truth about which authored assets are missing from R2 and which
R2 objects are orphaned.

This story fixes a defect (Architect audit, 2026-06-03) that makes the audit lie
about audio. `expected_keys()` learns music **only** from
`audio/music/*_input_params.json` (ACE-Step generation params). It never parses a
pack's `audio.yaml`. Consequently every track referenced through `audio.yaml`'s
`path:` field — the entire shared `classical_pd` / `ragtime_pd` library, plus any
pack-local track declared in YAML but generated outside the ACE-Step params flow —
is absent from the expected set and gets mis-reported as an **Orphan** ("in R2, no
YAML"). The same blind spot is symmetric: because YAML-referenced tracks are never
in the expected set, the audit can **never catch a genuine audio 404** (a `path:`
whose R2 object does not exist). Confirmed against `wry_whimsy` and `pulp_noir`
(`classical_pd` + `ragtime_pd`). The audit is the existence oracle; an oracle that
can't see half the audio surface and can't catch a 404 is the bug.

## Technical Guardrails

**File to modify:** `scripts/r2_audit.py` — specifically the music-key derivation
feeding `expected_keys()` (today `_music_keys()` at lines ~141-149, which globs
only `*_input_params.json`).

**The resolution rule is canonical — do NOT invent a new one.** The single source
of truth for turning an `audio.yaml` `path:` into a served location is
`sidequest-server/sidequest/genre/audio_paths.py::resolve_audio_relpath`:

- `path:` starting with `assets/` → **shared** bucket: R2 key is
  `genre_packs/<path>` — i.e. `genre_packs/assets/audio/...` **WITHOUT** the pack
  slug. (PR #338 migrated packs to this shared `assets/` prefix.)
- any other (pack-local) `path:` → R2 key is `genre_packs/<slug>/<path>`.

  Absolute URLs (`http://`, `https://`) and server-absolute (`/...`) paths pass
  through untouched and are **not** R2-managed keys — they must not enter the
  expected set.

**Import-vs-mirror tension (decide and document):** `r2_audit.py` is deliberately
`boto3`- and daemon-import-free, and runs under the **orchestrator root venv**
(`uv run --project .`), not the `sidequest-server` venv — so
`from sidequest.genre.audio_paths import ...` may not be importable here.
`resolve_audio_relpath` also returns a full **URL** (via `resolve_asset_url`),
whereas the audit compares bare **relpath keys**. The established pattern in this
very file is `_slugify_name`, which *mirrors* the daemon's slugify locally with a
comment naming the source of truth. Follow that precedent if a clean import is not
available: encode the one-line `assets/`-prefix rule locally with a comment
pointing at `audio_paths.py::resolve_audio_relpath` as canonical. Do not silently
diverge from the rule. Naive `genre_packs/<pack>/` prefixing of an `assets/` path
is the specific WRONG behavior this story exists to prevent.

**Manifest key form (verified against `sidequest-content/r2_manifest.json`):** keys
are literal relpaths with spaces and parentheses preserved, no URL-encoding —
e.g. `genre_packs/assets/audio/classical_pd/Chopin - Ballade No.1 Op.23.ogg` and
`genre_packs/caverns_and_claudes/audio/music/catacombs.ogg`. The derived expected
key must match this literal form so the diff aligns.

**audio.yaml shape (verified):** music `path:` references live under
`mood_tracks:` as `mood -> list of {path, title, bpm}`. The `sfx_library:` section
is a different shape (mood -> list of bare relpath strings) and is **out of scope**
(see Scope Boundaries). `audio.yaml` is **optional** — a pack without one is not an
error (no silent-fallback applies to malformed data, not to a legitimately absent
optional file).

**No silent fallbacks (CLAUDE.md):** malformed YAML / a malformed track entry must
fail loudly, mirroring how `_poi_keys` raises on a POI with neither slug nor name.

## Scope Boundaries

**In scope:**
- `expected_keys()` parses each pack's `audio.yaml` and adds every `mood_tracks`
  `path:` as an expected R2 key, resolved via the `assets/`-vs-pack-local rule.
- Shared (`assets/`-prefixed) paths resolve WITHOUT the pack slug; pack-local paths
  resolve under `genre_packs/<slug>/`.
- As a consequence: a `classical_pd`/`ragtime_pd` track present in R2 and referenced
  by `audio.yaml` is no longer mis-flagged as an orphan.
- As a consequence: a YAML-referenced track whose resolved key is absent from both
  R2 and disk is now caught as `authored_but_not_rendered` (the 404-catch).
- A pack with no `audio.yaml` continues to work (no crash, no spurious keys).

**Out of scope:**
- `sfx_library:` entries (different shape; deferred — flag as a follow-up if it
  proves to cause its own orphan noise).
- Any boto3 / live-R2 network listing — the audit stays offline against the
  checked-in manifest.
- Changing the `_input_params.json`-derived music keys (keep them; the YAML parse is
  additive — a track may be declared by either source).
- De-duplication concerns beyond what set-union already provides.

## AC Context

**AC1 — `expected_keys()` includes shared (`assets/`-prefixed) audio.yaml paths,
slug-less.** Given a pack `demo` whose `audio.yaml` has a `mood_tracks` entry
`path: assets/audio/classical_pd/Track.ogg`, `expected_keys()` must contain
`genre_packs/assets/audio/classical_pd/Track.ogg` and must **not** contain
`genre_packs/demo/assets/audio/classical_pd/Track.ogg`. Edge: filenames with spaces
and parentheses are preserved verbatim. Test: build a tmp pack with such an
`audio.yaml`, assert membership of the slug-less key and non-membership of the
slug-prefixed key.

**AC2 — `expected_keys()` includes pack-local audio.yaml paths, slug-prefixed.**
Given `path: audio/music/exploration_full.ogg` in pack `demo`'s `audio.yaml`,
`expected_keys()` must contain `genre_packs/demo/audio/music/exploration_full.ogg`.
Test: assert membership.

**AC3 — A shared track in R2 + referenced by audio.yaml is NOT an orphan.** Given the
pack above and a manifest containing `genre_packs/assets/audio/classical_pd/Track.ogg`,
`audit(...).orphans` must not contain that key. This is the headline regression.
Test: assert the key is absent from `orphans`.

**AC4 — A YAML-referenced track absent from R2 and disk IS caught (404-catch).** Given
`audio.yaml` referencing a track whose resolved key is in neither the manifest nor on
disk, `audit(...).authored_but_not_rendered` must contain that resolved key. Test:
assert membership.

**AC5 — A pack without audio.yaml is not an error.** `expected_keys()` over a pack
that has `*_input_params.json` music but no `audio.yaml` still returns the
params-derived keys and does not raise. Test: existing `_build_pack` fixture (no
audio.yaml) continues to pass; add an explicit assertion that no audio.yaml ⇒ no
crash.

**AC6 — Malformed track entry fails loudly (no silent fallback).** A `mood_tracks`
entry that is a mapping but missing `path:` must raise (mirroring `_poi_keys`'s
slug/name guard), not silently skip. Test: `pytest.raises` on such a fixture.

## Assumptions

- `audio.yaml` music `path:` references are confined to `mood_tracks:`; `sfx_library`
  uses a separate bare-string shape and is intentionally out of scope. (Verified
  against wry_whimsy/heavy_metal; if another pack carries `path:` music elsewhere,
  log a deviation.)
- The audit operates on relpath keys (not URLs); deriving the relpath form of
  `resolve_audio_relpath`'s rule is sufficient and correct — confirmed by manifest
  key inspection.
- `resolve_audio_relpath` may not be importable from the orchestrator scripts venv;
  the mirror-with-comment precedent (`_slugify_name`) is an acceptable fallback. If
  the import *does* work cleanly under `uv run --project .`, prefer it.
- The `_input_params.json`-derived keys and the audio.yaml-derived keys can coexist
  (set union); a track present in both sources is harmless.
