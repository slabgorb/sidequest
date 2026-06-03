---
parent: context-epic-78.md
workflow: trivial
---

# Story 78-2: Daemon dead-export sweep — NullRenderer/Renderer ABC, dead genre/models.py stubs, half-extracted dispatch_request image branch

## Business Context

This is pure debt reduction from the 2026-06-02 `sq-wire-it` audit, which scanned
the daemon (then at `origin/develop`) for code with no production consumer. Dead
exports are the project's most expensive defect class: they let a subsystem
*look* wired while it is inert, and they ambush future callers who assume an
export is reachable. The daemon's render/socket surface is also the seam most
prone to "looks-wired" traps because images and music share one JSON-RPC dispatch.

Three findings in this story are pure dead code (or a dead trap), no behavior to
preserve, no ADR lineage to honor (unlike 78-3). Removing them shrinks the daemon
to an honest surface and directly applies four CLAUDE.md doctrines: **No Stubbing**
(don't keep skeleton/placeholder modules), **Delete dead code in the same PR**,
**Verify Wiring, Not Just Existence** (confirm zero consumers, don't assume), and
**No Silent Fallbacks** (the `dispatch_request` trap must fail loud or not exist —
not silently no-op).

This serves Keith (the dev): a smaller daemon is easier to reason about and audit,
and removing the `NotImplementedError` trap means a future wire-up of image-tier
dispatch starts from a clean seam rather than a half-extracted one. No player-facing
behavior changes. Nothing blocks on this story.

## Technical Guardrails

All work is in the daemon subrepo: `/Users/slabgorb/Projects/oq-2/sidequest-daemon`
(currently on `develop`). **Default action is delete.** Re-confirm zero consumers
with a fresh grep *immediately before* each removal — develop may have moved since
this doc was written.

**(1) NullRenderer + Renderer ABC — DELETE both, as a coupled pair.**
- `sidequest_daemon/renderer/null.py` — `NullRenderer`. Verified zero references
  except its own class definition. No factory, no daemon path, no test.
- `sidequest_daemon/renderer/base.py` — `Renderer` ABC. Its *only* code importer
  is `null.py` (`from sidequest_daemon.renderer.base import Renderer`). The single
  other hit (`scene_interpreter.py:4`) is a docstring word ("the Renderer can
  consume"), not an import. They are a closed dead pair — once `null.py` goes, the
  ABC has no importer at all. Delete `null.py` and `base.py` together. Do **not**
  delete `renderer/models.py` (`RenderResult`, `RenderTier`, `StageCue`) or
  `renderer/beat_filter.py` — those are live and imported across the daemon.

**(2) genre/models.py dead stubs — DELETE the 8, but mind the GenrePack coupling.**
- The 8 stubs (`VisualStyle`, `AudioConfig`, `MixerSettings`, `AIGenerationConfig`,
  `ThemeFamily`, `MoodTrack`, `Variation`, `PackMeta`) have **zero external
  references** — confirmed by per-symbol grep across the whole daemon. The file's
  module docstring claims they're "used by prompt_composer.py / interpreter.py /
  library_backend.py / mixer.py" — **that docstring is stale**: `prompt_composer.py`
  exists but imports nothing from `genre.models`, and `interpreter.py` /
  `library_backend.py` / `mixer.py` do not exist in the daemon. The daemon reads
  visual/audio config from `StyleCatalog`/YAML directly (`media/catalogs.py`), not
  these models.
- **GOTCHA — `GenrePack` composes all 8 stubs as field-type defaults.** `GenrePack`
  is retained (per AC, it is TYPE_CHECKING-referenced) but its body wires the stubs:
  `meta: PackMeta = PackMeta(...)`, `audio: AudioConfig = AudioConfig()`,
  `visual_style: VisualStyle = VisualStyle()`; and `AudioConfig` in turn references
  `MoodTrack`, `MixerSettings`, `AIGenerationConfig`, `ThemeFamily`, which references
  `Variation`. So the 8 are not free-floating orphans — they are the **transitive
  composition closure of the retained `GenrePack`**. A naive "delete the 8 classes"
  will break `GenrePack`'s class definition at import time (NameError on the field
  annotations/defaults). See AC Context for the two valid resolutions; the
  implementer must pick one and make `python -c "from sidequest_daemon.genre.models
  import GenrePack"` succeed.
- `GenrePack` itself is referenced **only** under `TYPE_CHECKING` (scene_interpreter.py
  lines 18–19, 331) and never instantiated at runtime; `SceneInterpreter.__init__`
  stores `genre_pack` to `self._genre_pack` and nothing reads it back, and no caller
  passes a `GenrePack`. Do **not** delete `GenrePack` in this story — the AC scopes
  it as retained. (A `genre_pack`-param cleanup is out of scope here.)

**(3) dispatch_request image-tier branch — REMOVE THE TRAP.**
- `media/daemon.py` ~line 246: inside `dispatch_request`, `if tier in IMAGE_TIERS:
  raise NotImplementedError(...)`. This is the half-extracted branch (the music
  tier is fully wired through this same function).
- Verified the trap is **unreachable in production today**: the only prod call site
  (`_handle_client`, ~line 513–520) gates `dispatch_request` behind `params.get("tier")
  in MUSIC_TIERS`; image tiers are dispatched inline later in `_handle_client`
  (~line 630+). So it can only ambush a *future* caller who routes an image tier here.
- Two acceptable resolutions (epic guardrail): **(a)** finish the image-tier
  extraction so `dispatch_request` actually handles image tiers end-to-end and the
  inline `_handle_client` path delegates to it — only if that's genuinely small and
  testable; or **(b)** collapse the trap: remove the `if tier in IMAGE_TIERS: raise
  NotImplementedError` block (and the matching docstring sentences about Task 12 /
  the between-session-music plan) so the function cleanly handles music and falls
  through to the existing `raise ValueError(f"Unknown tier: {tier!r}")` for anything
  else. **Default to (b)** for a 3-point trivial story — finishing the extraction is
  a larger wiring effort and is not required. Do **not** leave the `NotImplementedError`
  in place. Keep the final `ValueError` (No Silent Fallbacks).
- Existing test `tests/test_music_dispatch.py` asserts only the music path and the
  `method != "render"` / unknown-tier `ValueError` paths — it does **not** assert the
  image-branch `NotImplementedError`, so removing that branch will not break it.

**Gate after all removals (both must be green):**
- `just daemon-test` and `just daemon-lint` (ruff). No dangling imports, no
  unreferenced names, no leftover docstring references to deleted symbols.

## Scope Boundaries

**In scope:**
- Delete `renderer/null.py` (`NullRenderer`) and `renderer/base.py` (`Renderer` ABC)
  as a coupled pair (confirm zero importers first).
- Delete the 8 dead `genre/models.py` stubs (`VisualStyle`, `AudioConfig`,
  `MixerSettings`, `AIGenerationConfig`, `ThemeFamily`, `MoodTrack`, `Variation`,
  `PackMeta`), resolving the `GenrePack` composition coupling so `GenrePack` still
  imports.
- Resolve the `dispatch_request` image-tier `NotImplementedError` trap
  (`media/daemon.py:~246`) — default: remove the branch + its stale docstring lines.
- Remove any now-stale docstring/comment text that references the deleted symbols.
- `daemon-test` + `daemon-lint` green; no dangling imports.

**Out of scope:**
- 78-1: camera post-processing (`apply_post` / `required_render_size` / `CameraSpec.post`
  wire-or-delete at the render seam).
- 78-3: deferred-feature observability — `start_periodic_heartbeat` (ADR-131
  liveness) and `detect_gpu`/`GpuInfo` (ADR-046) finish-or-cut.
- Retaining vs. removing `GenrePack` as a type (keep it; it is TYPE_CHECKING-referenced).
- Any cleanup of the unused `genre_pack` constructor param in `SceneInterpreter`
  (it stores to `self._genre_pack` with no reader) — not part of this sweep.
- Live render-path behavior, music pipeline behavior, or any player-facing change.

## AC Context

1. **"NullRenderer + Renderer ABC removed (confirmed zero importers first)."**
   Re-run the grep (`grep -rn "NullRenderer" ... ` and `from sidequest_daemon.renderer.base
   import Renderer`) to confirm `null.py` is the sole importer of the ABC and nothing
   imports `NullRenderer`. Delete `renderer/null.py` and `renderer/base.py`. Verify:
   neither symbol appears anywhere post-delete (including tests); the docstring word
   in `scene_interpreter.py` is fine to leave (it's prose, not an import). Keep
   `renderer/models.py` and `renderer/beat_filter.py`.

2. **"Confirmed-dead genre/models.py stubs removed; GenrePack retained if still
   TYPE_CHECKING-referenced."** Confirm the 8 stubs have zero external references
   (per-symbol grep). Remove them while keeping `GenrePack` importable — because
   `GenrePack` composes the stubs as field types/defaults, the implementer must
   either (a) inline those defaults into `GenrePack` (e.g. drop the structured
   sub-models and rely on `model_config = ConfigDict(extra="allow")` with plain/dict
   fields, since `GenrePack` is never instantiated at runtime anyway), or (b) keep
   the minimal subset that `GenrePack`'s definition actually needs and remove only
   the truly-leaf-dead ones. Verify: `python -c "from sidequest_daemon.genre.models
   import GenrePack"` succeeds; the 8 named stubs no longer resolve; the stale module
   docstring claiming "used by prompt_composer.py / interpreter.py / ..." is removed
   or corrected.

3. **"dispatch_request image-tier NotImplementedError trap resolved (extraction
   finished OR branch removed)."** Default action: remove the `if tier in IMAGE_TIERS:
   raise NotImplementedError(...)` block and the docstring sentences referencing the
   Task 12 / between-session-music plan. The function should still route `music` and
   raise the existing `ValueError` for unknown tiers. Verify: no `NotImplementedError`
   remains in `dispatch_request`; `IMAGE_TIERS` is still used by `_handle_client`
   (don't delete the constant — it gates the inline image path); the music dispatch
   test still passes.

4. **"daemon-test + daemon-lint green after removals; no dangling imports."**
   Run `just daemon-test` and `just daemon-lint` from the orchestrator root after all
   three removals. Both green. No leftover imports of deleted names, no ruff
   unused-import/undefined-name errors, no stale references in comments/docstrings.

## Assumptions

- The implementer re-greps to confirm zero-consumer status at story start (develop
  may have advanced). The findings recorded here were measured against daemon
  `develop` at `8d8d6c0` on 2026-06-02 and matched the epic's audit.
- `GenrePack` stays (TYPE_CHECKING-only reference is sufficient to retain it per AC).
  If the implementer discovers `GenrePack` is *also* provably dead and wants to remove
  it too, that is a scope change to raise — this story scopes it as retained.
- For AC3, "default to remove the branch" is the recommended path for a trivial
  3-point story; finishing the full image-tier extraction is acceptable only if it
  stays small and is covered by a wiring test, but is not required.
