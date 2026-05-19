---
story_id: "52-4"
jira_key: null
epic: "52"
workflow: "tdd"
repos: sidequest-server
---

# Story 52-4: Server emits cavern PNG sidecar from runtime mask via room_file_loader resolve_asset_url

## Story Details
- **ID:** 52-4
- **Title:** Server emits cavern PNG sidecar from runtime mask via room_file_loader resolve_asset_url
- **Jira Key:** None (SideQuest project does not use Jira)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Repos:** sidequest-server (targets `develop`)
- **Stack Parent:** none

## Epic Context
**Epic 52:** Wire Procedural Megadungeon Output to the ADR-096 Cavern Renderer Pipeline

ADR-096's static-authoring approach is subsumed by ADR-106's runtime generator (cellular port already re-homed). Renderer consumer end is built but starved — materializer.py:57 flags the unwired mask gap. Build the seam so procedural regions serialize ADR-096-shaped mask+PNG sidecars the live UI already renders.

## Acceptance Criteria

1. **Mask-to-PNG conversion in room_file_loader:** The room_file_loader.resolve_asset_url() function receives a persisted mask BLOB (from story 52-3) and converts it to a PNG sidecar file in the appropriate asset directory.

2. **PNG sidecar path resolution:** The resolved asset URL correctly points to the PNG file, following the same pattern as ADR-096 static-authored mask+PNG pairs (e.g., `cavern_image_url` matches `cavern_mask_url` layout).

3. **OTEL instrumentation:** All mask-to-PNG conversion operations emit OTEL spans (span name: `dungeon.render.cavern_mask_to_png` or equivalent) so the GM panel can verify the conversion is executing.

4. **No breakage of static path:** Static ADR-096 cavern scenarios continue to resolve asset URLs correctly — mask+PNG pairs authored in genre packs still work.

5. **Integration with existing renderer pipeline:** The PNG sidecar integrates with the existing TacticalGridRenderer (story 52-5 will verify UI end-to-end).

## Technical Context

- **ADR-096:** Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps
- **ADR-106:** Runtime Procedural Jaquaysed Megadungeon — Contiguous Edge-Expansion
- **Story 52-2:** Materializer emits ADR-096 mask + derived block per region
- **Story 52-3:** Persistence: mask-BLOB column + loader (the materializer.py:57 gap)
- **Story 52-5:** UI end-to-end wiring test

The "materializer.py:57 gap" refers to the runtime flow where the materializer generates a mask during procedural generation, persists it (52-3), and then needs to emit a PNG sidecar for the renderer to consume (this story).

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-19T15:21:44Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19 | 2026-05-19T14:25:16Z | 14h 25m |
| red | 2026-05-19T14:25:16Z | 2026-05-19T14:37:21Z | 12m 5s |
| green | 2026-05-19T14:37:21Z | 2026-05-19T14:54:01Z | 16m 40s |
| spec-check | 2026-05-19T14:54:01Z | 2026-05-19T14:57:57Z | 3m 56s |
| verify | 2026-05-19T14:57:57Z | 2026-05-19T15:07:54Z | 9m 57s |
| review | 2026-05-19T15:07:54Z | 2026-05-19T15:19:38Z | 11m 44s |
| spec-reconcile | 2026-05-19T15:19:38Z | 2026-05-19T15:21:44Z | 2m 6s |
| finish | 2026-05-19T15:21:44Z | - | - |

## Sm Assessment

**Routing:** Phased TDD workflow. Setup → red (Hamlet/TEA) → green (Puck/Dev) → spec-check (Oberon/Architect) → verify (TEA) → review (Portia/Reviewer) → spec-reconcile (Architect) → finish (SM).

**Confidence:** High. Deps closed (52-2, 52-3 done 2026-05-19); seam is well-scoped; ACs are explicit; ADR-096 + ADR-106 alignment is documented. No Jira (per project memory).

**For Hamlet (RED):** The story is small (3pt) and concrete — write failing tests against `room_file_loader.resolve_asset_url()` for the runtime mask path. AC3 mandates OTEL instrumentation (`dungeon.render.cavern_mask_to_png` or equivalent) — per the project's OTEL Observability Principle, the failing test for span emission is non-negotiable. AC4 (static-path preservation) is a regression guard — include a test that exercises the static genre-pack mask+PNG resolution and verifies it still works. Verify wiring per project rule: at least one integration test that proves the new code path is reachable from production callers (the materializer pipeline), not just unit-tested in isolation.

**Branch:** `feat/52-4-cavern-png-sidecar-emit` on sidequest-server, tracking `develop`.

## TEA Assessment (red)

**Tests Required:** Yes
**Reason:** TDD workflow, 3pt feature story with explicit ACs. Test bypass not warranted.

**Test Files:**
- `sidequest-server/tests/game/test_room_file_loader_runtime_png.py` — 17 tests across 5 test classes, one per AC plus a wiring test.

**Tests Written:** 17 tests covering 5 ACs
**Status:** RED — 13 failing, 4 passing.
- 13 failing tests are genuine missing-feature signals:
  * 11× `ImportError: cannot import name 'emit_runtime_cavern_png'` (AC1 unit + AC3 OTEL behavior)
  * 1× `AssertionError: no SPAN_* constant equals 'dungeon.render.cavern_mask_to_png'` (AC3 catalog)
  * 1× `AssertionError: span … is neither routed nor flat-only` (AC3 routing completeness)
  * 1× `AssertionError: no non-test production module … mentions 'emit_runtime_cavern_png'` (AC5 wiring)
- 4 passing tests exercise existing-and-unchanged code paths:
  * 2× AC2 URL round-trip (CDN + local mode) — `resolve_asset_url` already does the right thing
  * 2× AC4 static-path regression — `load_room_payload` static branch is the canary

### Notable test-design decisions

1. **Function name locked to `emit_runtime_cavern_png` in `sidequest.game.room_file_loader`** — honors AC1's "in room_file_loader" wording. Strong contract on the symbol name and module path; soft contract on internal layout.
2. **Span name locked to `dungeon.render.cavern_mask_to_png`** — taken from AC3 (spec text fixes the canonical name). Three tests enforce: name constant exists, routing decision made, attributes emitted on call.
3. **AC5 wiring test is intentionally soft on call-site** — asserts only that *some* non-test module under `sidequest/` mentions the symbol.
4. **No end-to-end integration test in 52-4** — that's 52-5's concern.
5. **AC4 fixture re-pointed to `genre_workshopping/caverns_sunden/`** — the canonical `genre_packs/...caverns_sunden/` was relocated (sidequest-content PR #228); workshopping copy still has static fixtures.

**Branch:** `feat/52-4-cavern-png-sidecar-emit` on sidequest-server
**RED commit:** `74ce3a1`
**Handoff (red→green):** To Puck (Dev) for implementation.

## Dev Assessment (green)

**Phase:** finish
**Status:** GREEN — 17/17 story tests pass, full suite 6676 passed / 0 failed / 396 skipped, ruff clean.

### What I built

| Surface | Location | Role |
|---|---|---|
| `emit_runtime_cavern_png` (public) | `sidequest/game/room_file_loader.py` | Decodes persisted mask BLOB → writes ADR-096 `.cavern.png` sidecar; emits `dungeon.render.cavern_mask_to_png` OTEL span. |
| `_decode_runtime_mask_grid` (private) | same file | Decodes base64+ASCII mask into a 2D wall/floor grid; raises loudly on missing keys, bad base64, illegal bytes, empty/ragged grids. |
| `_render_runtime_grid_to_png` (private) | same file | Minimal Pillow grid-to-PNG: solid wall background + solid floor cells. Dimensions byte-pinned to `grid × cell_width`. |
| `SPAN_DUNGEON_RENDER_CAVERN_MASK_TO_PNG` + `cavern_mask_to_png_span` | `sidequest/telemetry/spans/dungeon_render.py` (NEW) | Span constant + context manager + `SPAN_ROUTES` entry (state_transition, component=dungeon). |
| Span module registration | `sidequest/telemetry/spans/__init__.py` | `from .dungeon_render import *` |
| `_maybe_build_runtime_cavern_payload` | `sidequest/server/websocket_session_handler.py` | Production caller — when `_maybe_emit_tactical_grid` hits `RoomNotFoundError`, reads `sd.dungeon_store.load_masks()`, emits the PNG, synthesises a `TacticalGridPayload`, falls through to the normal TACTICAL_GRID emit. |
| Pillow dependency | `pyproject.toml` | `pillow>=10.0` added to runtime deps. |

### Key decisions

1. **Public emitter API `emit_runtime_cavern_png(*, mask_dict, output_path, region_id) -> None`** — kwargs-only, no return value (caller owns URL construction via `resolve_asset_url`).
2. **`region_id` is the only attribution input** — caller owns path composition.
3. **Minimal inline renderer, not a port of `cavern_renderer`** — visual parity not load-bearing; adding a sidequest-content dep would be a worse trade.
4. **`cellular=None` for runtime rooms** — generation params live in `GenerationReport`, not in the mask BLOB; ADR-006 graceful absence applies.
5. **`exits={}`, `pois=[]` for runtime rooms** — procedural exits are region-graph-level; POIs would require porting `cavern_renderer.derive.find_pois`.
6. **Wiring is real, not a stub** — PNG written to `<SIDEQUEST_OUTPUT_DIR>/artifacts/dungeon/<save_id>/regions/<region>.cavern.png`, URL resolved, full TacticalGridPayload emitted via the same `emit_fn` the static path uses.
7. **Decision-N grep gate preserved** — `_maybe_build_runtime_cavern_payload` uses `<var> = getattr(sd, "dungeon_store", None) / if <var> is not None:` shape; `tests/dungeon/test_setpiece_attach_wiring.py` continues to pass.

**Branch:** `feat/52-4-cavern-png-sidecar-emit`
**RED commit:** `74ce3a1`
**GREEN commit:** `34ca3cd`
**Handoff (green→spec-check):** To Oberon (Architect).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 3 minor (none blocking)

### Spec sources consulted

- **Story scope** (session ACs 1–5) — highest authority. No `context-story-52-4.md` exists on develop (TEA noted at setup; story-context-validated gate passed via directory-level validator).
- **Epic context** (`context-epic-52.md`) — defines 5-layer pipeline: 52-4 is layer 4 (server sidecar). Honored.
- **ADR-096** — "the mask is the truth" + cell-stepped math + `#/./newline` alphabet. Honored byte-for-byte.
- **ADR-106** — materializer is upstream; 52-4 is a pure downstream consumer of the persisted form.
- **ADR-090 / OTEL Observability Principle** — new span routed (state_transition, component=dungeon), six ground-truth attributes (region_id, mask_sha256, grid_width, grid_height, cell_width, output_path).

### Mismatches

**M1 — AC1 wording ambiguity (Ambiguous spec, Cosmetic, Trivial)**
Spec conflates "renderer" and "URL builder"; Dev correctly split them (`emit_runtime_cavern_png` in room_file_loader for the renderer; existing `resolve_asset_url` in `server/asset_urls.py` for the URL). **Recommendation: A (update spec)** — document on archive.

**M2 — Procedural `cellular` and `derived` data shape (Extra in code, Behavioral, Minor)**
Dev ships `cellular=None`, `derived=DerivedRoomData(floor_count=N, exits={}, pois=[])`. AC5 didn't specify. **Recommendation: D (defer)** to 52-5 / future.

**M3 — `room_name = room_id` for procedural rooms (Extra in code, Cosmetic, Trivial)**
No spec; Dev chose region_id-as-name. **Recommendation: D (defer)** — procedural naming is ADR-106 / future-story scope.

All 7 of Dev's flagged decisions confirmed architecturally sound. OTEL routing follows the exact established dungeon-domain pattern.

### Decision

**Proceed to verify.** Implementation is spec-aligned; no hand-back to Dev. Three minor mismatches are documentation/wording or deliberate scope deferrals.

**Handoff (spec-check→verify):** To Hamlet (TEA).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — 6676 passed / 0 failed / 396 skipped post-simplify; ruff check + format clean.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (`room_file_loader.py`, `websocket_session_handler.py`, `telemetry/spans/dungeon_render.py`, `telemetry/spans/__init__.py`, `tests/game/test_room_file_loader_runtime_png.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | (1) Wiring-helper decodes mask twice via inline `b64decode` (med); (2) Mask alphabet constants in two forms across `room_file_loader.py` (`ord()` ints) and `materializer.py` (byte literals) (low); (3) Missing `decode_mask_text_from_dict` abstraction (med). |
| simplify-quality | 1 finding | `import base64 as _base64` was mid-function (line 553) instead of grouped with other function-scoped imports at lines 500-504 (med). |
| simplify-efficiency | 1 finding | `_block = mask_dict["block"]; del _block` assign-and-delete pattern for early-KeyError raise is more verbose than bare access (med). |

**Applied:** 1 fix (commit `1844876`)
- Quality finding: moved `import base64 as _base64` from line 553 into the function-local imports block. Pure motion; no behavior change. Ruff + suite still green.

**Flagged for Reviewer (medium-confidence, not auto-applied):**
- **Reuse #1 / #3 (mask decode duplication / missing helper)** — `_maybe_build_runtime_cavern_payload` does its own `b64decode(...).decode("ascii")` rather than reusing decoded output from `emit_runtime_cavern_png`. **Architect already acknowledged this in spec-check** (Improvement, non-blocking — Dev's `-> None` emitter API is intentionally a side-effecting renderer; promoting decode to a public helper is a future-story concern). Reviewer can confirm or defer; not load-bearing.
- **Efficiency #1 (assign-and-delete pattern at room_file_loader.py:260-261)** — `_block = mask_dict["block"]; del _block` for early-KeyError. The simpler bare `mask_dict["block"]` would trip ruff `B018` "useless expression". An alternative `if "block" not in mask_dict: raise KeyError(...)` would be ruff-safe and clearer. Dev's comment explains intent; the pattern is functionally correct and lint-safe. Reviewer judgment call; minor stylistic.

**Noted (low-confidence):**
- **Reuse #2 (mask alphabet constants in two forms)** — `room_file_loader.py:37-39` defines `_MASK_WALL = ord("#")` etc. (ints, for byte-by-byte decode comparisons); `dungeon/materializer.py:318-320` defines `_MASK_WALL = b"#"` etc. (byte literals, for `bytearray.extend()`). Semantically equivalent but used in different operations. Consolidating would create a 3-constant module that one site has to convert away from — net cost > benefit at current scale. Note for future refactor if more mask consumers land.

**Reverted:** 0
**Overall:** simplify: applied 1 fix; 3 medium-confidence findings flagged; 1 low-confidence note.

### Quality Checks

**Pre-handoff suite (post-simplify):**
- Tests: 6676 passed, 0 failed, 396 skipped (108.22s)
- `tests/game/test_room_file_loader_runtime_png.py`: 17/17 pass
- `tests/dungeon/test_setpiece_attach_wiring.py::test_mandatory_wiring_decision_n_handler_site_present_and_seam_declared`: pass (Decision-N grep gate preserved)
- `tests/telemetry/test_routing_completeness.py`: pass (new `dungeon.render.cavern_mask_to_png` is routed)

**Lint:**
- `uv run ruff check sidequest/ tests/`: clean
- `uv run ruff format --check sidequest/ tests/`: clean for 52-4 files. (Format debt of ~73 pre-existing files remains from the 52-3 telemetry-substrate work — out of scope per [project_telemetry_substrate_phase1] memory.)

### Session-file note for posterity

The testing-runner subagent overwrote this session file at ~14:59 UTC (truncating it to a 14-line snippet titled "52-4 TEA Verify — Import Motion Refactor"). Reconstructed from conversation history. This is the same hazard captured in memory [feedback_testing_runner_overwrites_session] from story 49-2. The session-file content above is faithful to the actual workflow; verification commits `1844876` and prior are in git.

**Branch:** `feat/52-4-cavern-png-sidecar-emit` on sidequest-server
**Verify commit:** `1844876` — `refactor: simplify code per verify review`
**Handoff (verify→review):** To Portia (Reviewer) for code review.

## Delivery Findings

<!-- Append-only. Each agent writes under its own subheading. -->

### TEA (test design)

- **Gap** (non-blocking): Pillow / PIL was not a `sidequest-server` dependency at RED-write time. Dev added it for the GREEN renderer step. Affects `sidequest-server/pyproject.toml` (now resolved by GREEN commit `34ca3cd`). *Found by TEA during test design.*

- **Improvement** (non-blocking): The static-path canary at `genre_workshopping/caverns_sunden/` is the only remaining static-ADR-096 fixture in the tree (`caverns_and_claudes/worlds/caverns_sunden/` was relocated by sidequest-content PR #228). Once that workshopping world is fully retired, AC4 regression coverage disappears. A dedicated minimal in-repo test fixture would be more durable. Out of scope for 52-4; flag for future cleanup. *Found by TEA during test design.*

- **Question** (non-blocking): AC1 wording conflates `room_file_loader.resolve_asset_url()` — `resolve_asset_url` lives in `sidequest.server.asset_urls`, not `room_file_loader`. Interpreted charitably: emitter goes in room_file_loader; resolve_asset_url is invoked at URL-construction time. Architect confirmed in spec-check. *Found by TEA during test design.*

- **Conflict** (non-blocking): `tests/conftest.py` line 68 names `game/test_room_file_loader.py` in `_CAVERNS_SUNDEN_DEPRECATED_TESTS`. My new file is `game/test_room_file_loader_runtime_png.py` — distinct, not in skip-set, and bound to the relocated `genre_workshopping/caverns_sunden/` fixture. The pre-existing `test_room_file_loader.py` will keep skipping until re-pointed to `beneath_sunden`. Separate story; not 52-4. *Found by TEA during test design.*

### Dev (green implementation)

- **Improvement** (non-blocking): Pillow is now a `sidequest-server` runtime dep. The static `cavern_renderer` authoring tool still has its own isolated `pyproject.toml` with its own Pillow pin. Room exists to share rendering code if visual parity becomes load-bearing — future-DRY consideration. *Found by Dev during green implementation.*

- **Gap** (non-blocking): `_maybe_build_runtime_cavern_payload` reads `getattr(sd.store, "_path", None)` to derive `save_id`. `_path` is a private attribute on `SqliteStore`; existing callers also use this pattern (persistence.py:419, 441, 451). Following existing convention rather than adding a public property (out of scope for 3pt). A `SqliteStore.save_id` property would be a cleaner long-term seam. *Found by Dev during green implementation.*

- **Improvement** (non-blocking): Runtime path produces `TacticalGridPayload` with `cellular=None`, `exits={}`, `pois=[]`. Surfacing procedural cellular params would require persistence schema change (52-3) or `GenerationReport` re-derivation. Surfacing exits would require reconciling mask edges with region-graph edges. Both reasonable for 52-5 or future story. *Found by Dev during green implementation.*

- **Question** (non-blocking): Runtime PNG output path uses `<SIDEQUEST_OUTPUT_DIR>/artifacts/dungeon/<save_id>/regions/<region_id>.cavern.png`. When `SIDEQUEST_OUTPUT_DIR` is unset, the helper logs at DEBUG and returns None (no PNG, UI gracefully has no Map tab per ADR-006). Architect-confirmed: `app.py` already logs LOUD at server start when output dir is unresolved; per-turn duplicate would be ignorable noise. *Found by Dev during green implementation; resolved by Architect at spec-check.*

### Architect (spec-check)

- **Improvement** (non-blocking): AC1 wording-split between renderer and URL builder — Dev's split is the right design; AC1 should be reworded on archive. *Found by Architect during spec-check.*

- **Improvement** (non-blocking): `_maybe_build_runtime_cavern_payload` calls `dungeon_store.load_masks()` per room-not-found event — a full BLOB scan. For long Beneath Sünden sessions this is O(regions × room-enters). Not a problem at current scale; a `DungeonStore.load_mask(region_id)` single-row lookup is the natural optimisation. Out of scope for 52-4. *Found by Architect during spec-check.*

- **Improvement** (non-blocking): `_maybe_build_runtime_cavern_payload` decodes the mask twice (once in `emit_runtime_cavern_png`, once for `TacticalGridPayload.mask`). Cheap; keeps emitter API clean. If a future story needs to chain more derivations off the decoded mask, promote a public `decode_runtime_mask_text(mask_dict) -> str` helper. *Found by Architect during spec-check.*

### TEA (test verification)

- **Improvement** (non-blocking, flagged for Reviewer judgment): Three medium-confidence simplify findings flagged but NOT auto-applied — see Simplify Report above. Summary: (a) mask-decode duplication between wiring helper and emitter is architect-acknowledged trade-off; (b) `_block = ...; del _block` early-KeyError pattern at `room_file_loader.py:260-261` is functionally correct but stylistically verbose (bare `mask_dict["block"]` trips ruff B018; `if "block" not in mask_dict: raise KeyError(...)` would be ruff-safe and clearer). Reviewer can confirm or defer. *Found by TEA during test verification.*

- **Question** (non-blocking): The testing-runner subagent overwrote this session file mid-verify with a 14-line summary. Reconstructed from conversation. This is a recurring hazard (also observed on 49-2; in memory as [feedback_testing_runner_overwrites_session]). Worth a future story to harden the testing-runner subagent against session-file writes. Affects `.pennyfarthing/agents/testing-runner.md` (subagent definition). *Found by TEA during test verification.*

## Design Deviations

### TEA (test design)

- No deviations from spec.

### Dev (green implementation)

- No deviations from spec. Decisions on `cellular=None` / `exits={}` / `pois=[]` for procedural rooms were scope cuts the architect confirmed in spec-check as deliberate deferrals, not deviations.

### Architect (spec-check)

- **AC1 wording split between renderer and URL builder**
  - Spec source: session 52-4 / AC1
  - Spec text: "The `room_file_loader.resolve_asset_url()` function receives a persisted mask BLOB ... and converts it to a PNG sidecar file in the appropriate asset directory."
  - Implementation: Two distinct functions — `emit_runtime_cavern_png` (renderer) + existing `resolve_asset_url` (URL builder). Composed by the wiring helper.
  - Rationale: Splitting honors single-responsibility. Coupling them would force the renderer to take `relative_path` purely for URL purposes.
  - Severity: trivial
  - Forward impact: AC1 rewording recommended on archive; does not block 52-4.

- **`cellular` is `None` for runtime cavern payloads**
  - Spec source: session 52-4 / AC5 + epic context layer 4
  - Spec text: AC5 unspecified for `cellular`.
  - Implementation: `TacticalGridPayload.cellular = None` for procedural rooms.
  - Rationale: ADR-106 generation params live in `GenerationReport`, not the mask BLOB. Surfacing requires 52-3 schema change or save-side re-derivation — both out of scope. ADR-006 graceful absence applies; UI treats `cellular` as informational metadata.
  - Severity: minor
  - Forward impact: 52-5 or future story may surface generation params; path open via persisted-with-mask or re-derive-from-GenerationReport.

- **`derived.exits = {}` and `derived.pois = []` for runtime cavern payloads**
  - Spec source: session 52-4 / AC5
  - Spec text: AC5 unspecified for procedural `derived` content.
  - Implementation: `DerivedRoomData(floor_count=mask.count("."), exits={}, pois=[])`.
  - Rationale: Procedural exits live at the region-graph level (`RegionGraph.edges` is the navigability source of truth). POI derivation would require porting `cavern_renderer.derive.find_pois`. Both out of scope for 3pt. `floor_count` is a one-liner.
  - Severity: minor
  - Forward impact: future POI/exit work can port `cavern_renderer.derive` or join mask exits with region-graph edges at payload-build time.

### TEA (test verification)

- No deviations from spec at verify. One simplify fix applied (commit `1844876`); three medium-confidence findings flagged for Reviewer judgment, not auto-applied per workflow.

### Reviewer (code review)

- No deviations from spec at review. Five high-confidence findings addressed in-place (commit `4474d9d`): output_path assertion gap, CDN URL test tightening, lying docstring (daemon handshake file), bare `dict` type annotation, missing-output-dir DEBUG → WARNING + watcher event. Four findings dismissed with rationale (see Reviewer Assessment). Two deferred to follow-up (defensive test hardening, not spec-required).

### Architect (reconcile)

**Audit of existing deviation entries** — all three Architect (spec-check) entries verified accurate post-Reviewer fixes:

| Entry | Spec source verified | Spec text accurate | Implementation matches shipped code | Forward impact | All 6 fields |
|---|---|---|---|---|---|
| AC1 wording split | session 52-4 / AC1 ✓ | quoted accurately ✓ | `emit_runtime_cavern_png` in `room_file_loader.py`; `resolve_asset_url` in `server/asset_urls.py` — still split ✓ | AC1 rewording on archive — still applicable ✓ | yes |
| `cellular=None` for runtime | session 52-4 / AC5 + epic context layer 4 ✓ | "AC5 unspecified for cellular" — checked AC5 text again, confirmed ✓ | `_maybe_build_runtime_cavern_payload` line 581 ships `cellular=None` — unchanged by review fixes ✓ | 52-5 or future story may surface generation params ✓ | yes |
| `derived.exits={}` / `pois=[]` | session 52-4 / AC5 ✓ | "AC5 unspecified" — confirmed ✓ | line 586-590 ships `DerivedRoomData(floor_count=mask.count("."), exits={}, pois=[])` ✓ | future POI/exit work can port `cavern_renderer.derive` ✓ | yes |

TEA (test design) and Dev (green implementation) "No deviations" subsections also verified — accurate; neither phase introduced spec deviations that would have required a 6-field entry. The cellular/exits/pois scope cuts Dev flagged were correctly converted to formal Architect-logged deviations at spec-check rather than left as informal flags.

**AC deferral cross-check:** All 5 ACs are DONE. None deferred or descoped. No reconciliation needed against an AC accountability table.

**Additional deviations missed by prior phases:** None.

**Architect-reconcile reflection (not a spec deviation, recorded for audit traceability):** My spec-check (this story) accepted the `DEBUG`-severity log on missing `SIDEQUEST_OUTPUT_DIR` as "non-noise per-turn", citing the loud server-startup warning at `app.py`. Reviewer (Portia) correctly escalated this to `logger.warning(...)` + a `tactical_grid.runtime_render_skipped` watcher event per CLAUDE.md No-Silent-Fallbacks (commit `4474d9d`). This is the rule's intended behavior — startup-time logging is not a substitute for per-turn observability when the same condition manifests at a different layer. Calibration note for future spec-checks: "logged elsewhere" is not a valid defense against No-Silent-Fallbacks at the layer where the silent return-None actually occurs. The Reviewer's correction is the canonical state.

- No additional deviations found.

---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A (suite 6676/0; lint clean) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 2 (T1, T3 applied), dismissed 2 (T4, T6), deferred 2 (T2, T5) |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 | confirmed 1 (C1 applied) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 2 (R3, R4 applied), dismissed 2 (R1, R2) |

**All received:** Yes (4 enabled subagents returned, 5 disabled via `workflow.reviewer_subagents` settings)
**Total findings:** 5 confirmed-and-applied, 4 dismissed (with rationale), 2 deferred (follow-up scope)

## Reviewer Assessment

**Verdict:** Approve to merge.
**Review commits:** `4474d9d` (5 fixes applied this phase).
**Suite (post-review-fixes):** 6676 passed / 0 failed / 396 skipped. Ruff check + format clean for all 52-4 files.

### Findings — Confirmed and Applied (5)

**[TEST] T1 — `output_path` span assertion gap (HIGH)**
- `tests/game/test_room_file_loader_runtime_png.py:423` — `test_span_is_emitted_with_lie_detector_attributes` did not assert `attrs.get("output_path")`. AC3 explicitly names `output_path` as a lie-detector attribute; the span passes it; the test silently dropped it from the rubric. A refactor removing the attribute would pass undetected.
- **Applied** (commit `4474d9d`): added `assert attrs.get("output_path") == str(out)` and corrected the docstring to list output_path.

**[TEST] T3 — CDN URL test asserts prefix/suffix instead of full value (HIGH)**
- `tests/game/test_room_file_loader_runtime_png.py:367` — `test_runtime_cavern_png_relative_path_resolves_to_url` checked only `url.endswith(".cavern.png")` + `url.startswith("https://cdn.example/")`. A broken `resolve_asset_url` that returned `"https://cdn.example/.cavern.png"` (dropped path segment) would have passed both. AC2 contract is a *URL round-trip*.
- **Applied** (commit `4474d9d`): replaced both partial checks with `assert url == "https://cdn.example/artifacts/dungeon/save01/regions/exp001r0.cavern.png"` — symmetric with the local-mode test that already asserts the exact value.

**[DOC] C1 — Lying docstring re: "daemon handshake file" (HIGH)**
- `sidequest/server/websocket_session_handler.py:491` — the third return-None bullet in `_maybe_build_runtime_cavern_payload`'s docstring said: "`SIDEQUEST_OUTPUT_DIR` unset and the daemon handshake file absent — the server.app startup logs this as a loud warning already". The function ONLY checks the env var; the handshake file logic lives in `server.app`'s startup path, not here. The compound `and` condition was fabricated.
- **Applied** (commit `4474d9d`): reworded the bullet to describe only the per-turn env-var check + cross-reference (not implementation conflation) to `server.app`'s startup logging.

**[RULE] R3 — Bare `dict` type annotation on public boundary (HIGH — lang-review #3)**
- `sidequest/game/room_file_loader.py:155` — `emit_runtime_cavern_png(*, mask_dict: dict, ...)` uses bare `dict`, which is equivalent to `dict[Any, Any]`. Lang-review rule #3 says "Any is acceptable only with a comment explaining why". The docstring documents the dict shape extensively, but the annotation itself was unspecific.
- **Applied** (commit `4474d9d`): changed `mask_dict: dict` to `mask_dict: dict[str, Any]` (matching `DungeonStore.load_masks() -> dict[str, dict]` upstream shape; the inner dict values are mixed-type per `RegionMask.to_dict()`); added `Any` import. Also tightened `_decode_runtime_mask_grid` signature for consistency.

**[RULE] R4 — Missing-output-dir log at DEBUG (HIGH — CLAUDE.md No Silent Fallbacks)**
- `sidequest/server/websocket_session_handler.py:529` — when `SIDEQUEST_OUTPUT_DIR` was unset, the helper logged at DEBUG and returned None. CLAUDE.md No-Silent-Fallbacks rule: "If something isn't where it should be, fail loudly." The architect's spec-check noted that `server.app` already logs loudly at startup; but at runtime, a per-turn-skip with debug visibility is exactly the rule's failure mode (operator-broken config silently produces no UI map).
- **Applied** (commit `4474d9d`): upgraded `logger.debug(...)` → `logger.warning(...)` AND added a `_watcher_publish("tactical_grid.runtime_render_skipped", {...}, component="cavern_renderer", severity="warning")` event so the GM panel sees the per-turn skip. Frequency: ≤ once per procedural-room enter, not flood-scale. Matches the established `tactical_grid.*` watcher event family already emitted by `_maybe_emit_tactical_grid`'s sibling branches.

### Findings — Dismissed with Rationale (4)

**[TEST] T4 — Wiring test does soft string-grep (MEDIUM, dismissed)**
- The wiring test `test_emitter_has_non_test_production_consumer` walks `sidequest/` and asserts any module text contains `emit_runtime_cavern_png`. A comment-only reference would pass.
- **Dismissal rationale:** intentional design per TEA red-phase Notable Decision #3 ("AC5 wiring test is intentionally soft on call-site so the dev has freedom to wire it in a cleaner location if one exists") AND architect-confirmed in spec-check ("All 7 of Dev's flagged decisions are architecturally sound"). The Decision-N grep gate at `tests/dungeon/test_setpiece_attach_wiring.py` is the structural-grep canary; tightening 52-4's wiring test further would couple it to a specific line in `websocket_session_handler.py` and create maintenance churn whenever the wiring is moved.

**[TEST] T6 — Static cavern test asserts only `"#" in mask` (LOW, dismissed)**
- `test_static_cavern_load_still_returns_image_url_and_mask` asserts `"#" in payload.mask`. A degenerate single-`#` mask would pass.
- **Dismissal rationale:** the test's load-bearing purpose is the regression guard "static path doesn't break". Existing assertions already cover `mask is not None`, `payload.room_type == "cavern"`, `payload.cavern_image_url.endswith("/mouth.cavern.png")`. Adding `"." in mask` would couple the test to fixture content that may drift across `genre_workshopping/caverns_sunden/` evolutions. Low priority; the existing assertion catches the regression case.

**[RULE] R1 — Broad `except Exception` in `_maybe_build_runtime_cavern_payload` (HIGH, dismissed)**
- Rule-checker flagged the `except Exception as exc: # noqa: BLE001` around `dungeon_store.load_masks()` (line 514-524) as a Rule #1 violation.
- **Dismissal rationale:** the catch pattern matches NONE of Rule #1's enumerated patterns. The rule specifically flags: (a) bare `except:`, (b) `except Exception: pass`, (c) `except Exception:` with only `logger.debug()`, (d) try/except around a single line where the type is known, (e) `suppress()` without comment. My code is `except Exception as exc: logger.warning(...with exception details...); return None` — names the exception, logs at WARNING (correct severity per Rule #4 for a server-side resource failure), preserves the rationale in the docstring's "must-not-crash-a-turn" + immediately-following Architect spec-check confirmation. The `# noqa: BLE001` is the explicit acknowledgment pattern the linter contemplates for an intentional broad catch. The pattern is also the established convention throughout `websocket_session_handler.py` (see the world-dir lookup at line 622, the load_room_payload outer catch at line 686, etc.).

**[RULE] R2 — Function-scoped stdlib imports (HIGH, dismissed)**
- Rule-checker flagged `import base64 as _base64`, `import os as _os` inside `_maybe_build_runtime_cavern_payload` as Rule #10 (import hygiene) violations.
- **Dismissal rationale:** function-scoped imports are the *established* `websocket_session_handler.py` convention. See `_maybe_emit_tactical_grid` at line 605 (`from sidequest.game.room_file_loader import RoomNotFoundError, load_room_payload`), the existing pattern is uniform across the file. Moving the new imports to module-top would create a stylistic inconsistency *within this file*. The TEA-verify simplify-quality pass already moved `import base64` from mid-function to function-top (commit `1844876`) — that was within the function-scoped convention, not a move to module-top. The stdlib imports are lightweight enough that the lazy-load pattern has no cost; the project convention wins. (If we wanted to break the convention, that's a separate refactor story across the whole file, not a 52-4 concern.)

### Findings — Deferred to Follow-up (2)

**[TEST] T2 — No test asserts span absence on render-failure (MEDIUM, deferred)**
- The OTEL span fires AFTER `_render_runtime_grid_to_png` completes (room_file_loader.py:230-238 — `with cavern_mask_to_png_span(...): pass`). If PIL `img.save()` raises `OSError`, the span never fires. There's no test pinning that behavior.
- **Deferral rationale:** the current placement is defensible (no-span = no-PNG-produced = GM panel truth) but unverified. A negative-path test would harden the contract but represents scope expansion. Worth a 1-pt hardening story in a future sprint, alongside T5.

**[TEST] T5 — No test pins block-vs-decoded-grid mismatch behavior (MEDIUM, deferred)**
- Production code uses `len(grid)`, `len(grid[0])` (decoded grid dimensions), not `block.grid_width` / `block.grid_height` (mask-metadata dimensions). A test where these disagree would prove the decoder output drives the render. Currently the structural property is only documented.
- **Deferral rationale:** a real defect would mismatch the persisted SHA at the span layer (since the SHA is computed over the raw bytes regardless of block claims) — the GM panel would catch divergence. Adding a defensive test is a hardening win, not load-bearing for 52-4 correctness. Pair with T2 in a follow-up.

### Rule Compliance — Exhaustive

Cross-referenced reviewer-rule-checker's 18-rule, 97-instance enumeration. Confirmed:

| Rule | Coverage | Violations | Status |
|------|----------|------------|--------|
| #1 Silent exception swallowing | 4 instances | 0 (R1 dismissed — not a rule-pattern match) | Pass |
| #2 Mutable default arguments | 6 instances | 0 | Pass |
| #3 Type annotation gaps at boundaries | 4 instances | 1 (R3 applied) | Pass after fix |
| #4 Logging: coverage AND correctness | 8 instances | 0 (R4-WARNING upgrade reinforces) | Pass |
| #5 Path handling | 6 instances | 0 (pathlib throughout) | Pass |
| #6 Test quality | 18 instances | 0 (no vacuous; T1+T3 tightening reinforces) | Pass |
| #7 Resource leaks | 5 instances | 0 (PIL `with Image.open` used in tests) | Pass |
| #8 Unsafe deserialization | 3 instances | 0 (base64 with `validate=True`; no pickle/yaml/eval) | Pass |
| #9 Async/await pitfalls | 4 instances | 0 (sync `_maybe_emit_tactical_grid` chain, no async leak — verified call chain is sync from `narration.location_change` and `chargen.room_graph_init` callsites) | Pass |
| #10 Import hygiene | 6 instances | 0 (R2 dismissed — established convention; no star imports at top level; star-imports in `telemetry/spans/__init__.py` are the existing domain-submodule pattern) | Pass |
| #11 Input validation at boundaries | 3 instances | 0 (mask_dict comes from DungeonStore — server-controlled, not HTTP input; validation enforced via `_decode_runtime_mask_grid`) | Pass |
| #12 Dependency hygiene | 1 instance | 0 (pillow lower-bound-only pin matches existing project convention — fastapi, pydantic, etc. all follow same pattern) | Pass |
| #13 Fix-introduced regressions | 3 instances | 0 (verified post-R3/R4 fixes; no new class introduced) | Pass |
| #14 State cleanup ordering | 2 instances | 0 (no fallible-side-effect queue pattern present) | N/A |
| **CLAUDE.md No Silent Fallbacks** | 5 instances | 0 (R4 applied → WARNING + watcher; emit_runtime_cavern_png raises loudly on every gap) | Pass after fix |
| **CLAUDE.md No Stubbing** | 4 instances | 0 (all functions fully implemented; no placeholders) | Pass |
| **CLAUDE.md Don't Reinvent** | 2 instances | 0 (uses existing `resolve_asset_url`; OTEL routing follows existing `dungeon_*` spans pattern) | Pass |
| **CLAUDE.md Verify Wiring** | 2 instances | 0 (emit_runtime_cavern_png called from `_maybe_build_runtime_cavern_payload`, in turn called from `_maybe_emit_tactical_grid`'s RoomNotFoundError branch) | Pass |
| **CLAUDE.md Every Test Suite Needs a Wiring Test** | 1 instance | 0 (`test_emitter_has_non_test_production_consumer`) | Pass |
| **CLAUDE.md OTEL Observability Principle** | 3 instances | 0 (`dungeon.render.cavern_mask_to_png` routed + 6 ground-truth attrs) | Pass |

### Path-traversal note (independent finding, not blocking)

Independent of subagent reports, I verified that `output_root / relative` would NOT contain a path-traversal risk in production: `room_id` is server-state from `snapshot.character_locations` or `RegionNode.id` (materialiser-generated `expNNN.rN` format), never user input. I probed the edge case (`room_id = "../../../etc/passwd"`) and confirmed Path resolution can escape `output_root` if the input is adversarial — but the threat surface is null today. Documenting here as a "future security hardening" pointer: if `room_id` ever becomes user-influenced (e.g. via a future API), `output_path.resolve()` should be validated against `output_root.resolve()` before write. Not in 52-4 scope.

### Decision

**Approve. Story 52-4 is ready for merge.**

- All 5 ACs covered by tests, all tightened where reviewer findings exposed gaps.
- Suite GREEN: 6676 / 0 / 396.
- Ruff clean.
- Spec-aligned per architect spec-check (Aligned, 3 minor mismatches all logged + accepted).
- Project rules: all 14 lang-review checks + 6 CLAUDE.md principles pass.
- Two deferrals (T2, T5) are hardening tests, not spec-required.

**Branch:** `feat/52-4-cavern-png-sidecar-emit` on sidequest-server
**Review commit:** `4474d9d` — `review(52-4): address reviewer findings`
**Commit chain:** `74ce3a1` (RED) → `34ca3cd` (GREEN) → `1844876` (verify simplify) → `4474d9d` (review fixes)
**Handoff (review→spec-reconcile):** To Oberon (Architect) for final spec reconciliation, then to SM for finish.