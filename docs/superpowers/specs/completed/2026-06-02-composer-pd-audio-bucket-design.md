# Composer ↔ audio.yaml — Shared PD Music Bucket

**Status:** Design approved (Operator, 2026-06-02). Pending implementation plan.
**Author:** Architect (Neo)
**Repos touched:** `sidequest-content`, `sidequest-server`, orchestrator (`scripts/`). `sidequest-composer` is **unchanged** (reuse, not extension).
**Related:** ADR-095 (Daemon Music Tier / R2 audio), ADR-131 (R2 artifact layout), ADR-120/121 (genre↔world flavor boundary, layered resolution), Story 65-1 (`r2_manifest.json`).

---

## 1. Motivation

Worlds declare public-domain music tracks in `audio.yaml` as a **deferred-asset class** — the manifest is the spec, the OGG is "sourced later from the shared classical_pd library" (`wry_whimsy/audio.yaml` header). Today that library does not exist: **50 distinct `classical_pd/*.ogg` tracks are referenced across `wry_whimsy` + `tea_and_murder`, and zero are rendered** (the dir holds only a `LICENSE.md`).

`sidequest-composer` is the renderer that closes this gap: it turns public-domain notation (MusicXML/MIDI from IMSLP/Mutopia) into tagged, rights-free OGG **by construction** — no recording licenses. This spec wires the composer's output into the SideQuest content pipeline so a world's `audio.yaml` can be *delivered* as real audio on R2.

## 2. Core Insight

`audio.yaml` is **demand**. A catalog is **supply**. The composer is the renderer. The integration is a *join*, not new audio infrastructure:

```
world audio.yaml (demand: which classical_pd tracks)
        +
shared catalog.yaml (supply: source_url + composer/work per track)
        ↓  reconciler builds a composer Manifest of the gap
composer render → tagged OGG → shared bucket → existing R2 sync → r2_manifest.json
        ↓
delivered manifest/report (rendered · uploaded · skipped · unresolved)
```

Two facts make this clean:
- **R2 mirrors content paths 1:1** — an entry's `r2_manifest.json` `key` *is* its content-relative path *is* its R2 object key. Render to the right relative path and the R2 layout follows for free.
- **Runtime audio resolution does not read `r2_manifest.json`** — `resolve_asset_url()` prepends `cdn.slabgorb.com/`; the 404 is the lie detector. The manifest is the R2 *inventory* (reference pages, `r2_audit`), not a runtime lookup. So "add to manifest" = let the **existing** `r2_sync_packs.sync()` → `r2_manifest.py` pipeline record the uploads. We do not hand-roll an uploader or a manifest writer.

## 3. Altitude (locked decisions)

- **Bucket o' music, mirroring bucket o' fonts.** A single shared bucket at the `genre_packs/assets/` level (sibling to every pack), holding one copy of each PD piece, referenced by all packs. Mirrors `genre_packs/assets/fonts/*.woff2`. **Not** duplicated per-pack.
- **Storage tier = R2.** OGGs are MB-scale and already gitignored (`genre_packs/**/audio/**/*.ogg`). The *organization* mirrors fonts (shared, deduplicated); the *tier* is R2, like all music (ADR-095). Only the catalog (text) is git-tracked.
- **Composer stays pure.** It learns nothing about SideQuest's schema, R2, or boto3. "Notation in, audio out." All SideQuest-specific translation lives on the SideQuest side. (Composer scope discipline; Architect reuse-first.)
- **Shared-asset path spelling = `assets/` prefix convention** (Operator choice). An `audio.yaml` `MoodTrack.path` whose first segment is `assets/` resolves to `genre_packs/assets/…` (no pack slug); anything else stays pack-relative. Backward-compatible.

## 4. Components

### 4.1 Shared music bucket (content)
```
genre_packs/assets/audio/classical_pd/
├── catalog.yaml                              # tracked — the supply spec
├── Satie - Gymnopedie No.1.ogg               # R2-only (gitignored)
├── Chopin - Nocturne Op.9 No.2 in E-flat major.ogg
└── … (one per PD piece, shared by all packs)
```
- R2 key for each OGG = `genre_packs/assets/audio/classical_pd/<file>.ogg`.
- Path chosen so the **existing** `genre_packs/**/audio/**/*.ogg` gitignore covers it.

### 4.2 `catalog.yaml` (content — tracked text, composer-native)
It **is** a composer `Manifest`. Each entry keyed by the exact filename `audio.yaml` expects, carrying the `source_url`/`composer`/`work` that `MoodTrack` (`extra:"forbid"`, fields `path/title/bpm/energy`) cannot hold:

```yaml
# genre_packs/assets/audio/classical_pd/catalog.yaml
loudness: -16                 # composer manifest-level default
entries:
  - out_name: "Satie - Gymnopedie No.1.ogg"   # == the audio.yaml filename
    title: Gymnopédie No. 1
    composer: Erik Satie
    work: Trois Gymnopedies
    movement: No. 1
    source_url: https://www.mutopiaproject.org/ftp/SatieE/gymnopedie_1/gymnopedie_1.mid
```

This is the provenance artifact (Approach C — "guess the URL from the title" — was rejected for exactly this reason). One catalog, shared.

### 4.3 Reconciler (orchestrator `scripts/render_pd_audio.py`)
Cross-repo media script, sibling to `generate_music.py`. Pure-Python orchestration; does **not** import composer internals — it invokes the `composer` CLI as a subprocess (the daemon/server boundary pattern).

Algorithm:
1. **Collect demand.** Read every pack/world `audio.yaml` (or a `--pack`-scoped subset). Gather the distinct set of `MoodTrack.path` values whose first segment is `assets/` and which point at `classical_pd/` → the demand set.
2. **Join to supply.** For each demanded filename, look up the matching `catalog.yaml` entry. **Fail loud** if a demanded track has no catalog entry (No Silent Fallbacks — this is the "I referenced a track I never catalogued" lie detector). Emit the missing list and exit non-zero.
3. **Skip rendered.** Drop entries already present in `r2_manifest.json` (idempotent re-runs). `--force` overrides.
4. **Render the gap.** Write a temp composer manifest of the remaining entries (with `out_dir` = the shared bucket) and run `composer render <manifest> --out-dir genre_packs/assets/audio/classical_pd`. OGGs land locally (gitignored).
5. **Upload + record.** Invoke the existing `r2_sync_packs.sync()` → uploads the new OGGs to R2 and `r2_manifest.py` writes their manifest entries.
6. **Deliver the manifest/report.** Print and write a run report: `rendered`, `uploaded`, `skipped (already in R2)`, `unresolved (no catalog entry)`, `failed (render error)`. This report is the "audio manifest" deliverable.

### 4.4 Server: shared-asset audio path convention
The single behavioral change in `sidequest-server`. `MoodTrack` schema is **unchanged** (still a plain `path` string). Only *resolution* changes, centralized so it is defined once:

- **Rule:** an audio `MoodTrack.path` whose first path segment is `assets/` resolves to `genre_packs/{path}` (i.e. `genre_packs/assets/…`, no slug). Any other path resolves pack-relative to `genre_packs/{slug}/{path}` as today. Absolute URLs / server-absolute paths pass through untouched (existing behavior).
- **`assets/` is reserved** in the audio-path namespace for the shared bucket. Pack-relative audio uses `audio/…`; there is no collision.
- **Single seam.** Today `audio_cue.py::_maybe_prefix` hand-rolls `genre_packs/{slug}/{path}`. A prior playtest (2026-05-10) showed audio was the one media path bypassing the `asset_urls` seam and silently 404ing. This convention is implemented **once** in the asset-resolution seam and consumed by every audio path site (`audio_cue.py` runtime, `cli/validate/audio.py` existence check, `audio/library_backend.py` base-path join) — not re-derived per call site.

### 4.5 Composer
Unchanged. Already renders a `Manifest` → tagged OGG with provenance, backend-agnostic (MuseScore 4 / FluidSynth), ffmpeg-normalized. The reconciler is its only new caller.

## 5. Data Flow (end to end)

```
catalog.yaml ─┐
              ├─ reconciler: demand ∩ supply ∖ already-in-R2 ─► temp composer Manifest
audio.yaml ───┘                                                        │
                                                                       ▼
                                       composer render --out-dir .../assets/audio/classical_pd
                                                                       │ (local OGG, gitignored)
                                                                       ▼
                                              r2_sync_packs.sync()  ─►  R2 + r2_manifest.json
                                                                       │
                                                                       ▼
                                                    run report  ("the audio manifest")

# runtime, unchanged except the assets/ rule:
audio.yaml path "assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg"
   → resolve_asset_url("genre_packs/assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg")
   → https://cdn.slabgorb.com/genre_packs/assets/audio/classical_pd/Satie - Gymnopedie No.1.ogg
```

## 6. Failure & Idempotency (No Silent Fallbacks)

- **Demand without supply** → hard error, names the uncatalogued tracks, non-zero exit. Never silently skip.
- **Render failure** (bad source URL, MuseScore missing) → reported per-track in the run report; the run continues for other tracks but exits non-zero if any failed. No partial-success masquerading as success.
- **Re-run** with everything already in R2 → no-op render, report shows all `skipped`. Safe to run on every content change.
- **`assets/` path with no matching R2 object** → runtime 404 (the existing lie detector); not masked.

## 7. Observability (OTEL)

Per the project's OTEL principle (every subsystem decision emits a span so the GM panel can tell engagement from improvisation):
- Reconciler emits a structured run summary (counts by outcome) — this is a dev/operator artifact, not a player surface.
- **Server side:** add a span on the shared-asset resolution branch — `asset_url_resolved` already spans `mode` (cdn/local); extend it (or add a sibling) to record `scope = shared | pack` so a playtest can confirm a track actually resolved to the shared bucket and didn't silently fall back to a pack-relative 404. This is the runtime lie detector for the `assets/` convention.

## 8. Scope & Phasing

- **Phase 1 — Catalog + convention (unblocks everything).** Author `catalog.yaml` for the 50 demanded tracks; implement the server `assets/` resolution convention + span; update `wry_whimsy` + `tea_and_murder` `audio.yaml` paths to `assets/audio/classical_pd/…`. Wiring test: a pack with a shared-bucket track resolves to a `genre_packs/assets/…` URL.
- **Phase 2 — Reconciler.** `scripts/render_pd_audio.py` (demand∩supply∖R2 → composer → sync → report) + `just render-pd-audio [pack]`. Integration test on the Satie smoke track (composer already has the gated Gymnopédie test).
- **Phase 3 — Backfill.** Run the reconciler to render + upload all 50; verify via `r2_audit`.

## 9. Testing

- **Server:** unit — `assets/`-prefixed path resolves to `genre_packs/assets/…` (no slug); pack-relative path unchanged; absolute URL passes through. Wiring — a real pack `audio.yaml` shared-bucket track resolves end-to-end through the live seam (not the hand-rolled prefix).
- **Reconciler:** demand∩supply set math; **fail-loud on uncatalogued demand**; idempotent skip when in `r2_manifest.json`; report shape. Mock the `composer` subprocess + `r2_sync` for unit; one gated end-to-end on the Satie track.
- **Composer:** none new — reused as-is (its gated Gymnopédie integration test already proves the renderer).

## 10. Non-Goals (YAGNI)

- No composer changes; no SideQuest-aware composer mode; no composer-side R2/boto3.
- No per-pack catalogs (the bucket is shared — one catalog).
- No new manifest format/writer — reuse `r2_manifest.py` via `r2_sync_packs`.
- No runtime manifest lookup for audio (resolution stays string-prefix; 404 is the detector).
- No `MoodTrack` schema change — the `assets/` convention is pure resolution.
- No mood/curation automation — which track sits in which mood stays authored in `audio.yaml`.
- No AI generation — the composer is deterministic synthesis by charter.
```
