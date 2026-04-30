---
story_id: "45-37"
epic: "45"
jira_key: null
workflow: "tdd"
---
# Story 45-37: Image pipeline silent-fallback teardown — kill SF1-SF7 + render.completed lie detector

## Story Details
- **ID:** 45-37
- **Epic:** 45 — Playtest 3 Closeout
- **Jira Key:** (none assigned)
- **Workflow:** tdd
- **Type:** bug
- **Priority:** p1
- **Points:** 8
- **Repos:** server, daemon, orchestrator
- **Branches:**
  - `feat/45-37-image-pipeline-silent-fallback-teardown` (sidequest-server)
  - `feat/45-37-image-pipeline-silent-fallback-teardown` (sidequest-daemon)
  - `feat/45-37-image-pipeline-silent-fallback-teardown` (oq-1 orchestrator)
- **Stack Parent:** none (standard multi-repo PR)

## Description

Image pipeline has seven silent fallbacks layered such that when the visual_style.yaml decomposition (sidequest-content PR #149) broke the topmost gate, every gameplay scene_illustration silently bypassed the composer. Z-Image now receives raw narration prose with zero style — symptom: photoreal CG with prose-bleed text on shipboard scenes, Coyote Star world.

Per CLAUDE.md No-Silent-Fallbacks rule, every fallback below must be DELETED, not hardened. Lie detector (world_style_applied) was emitted inside the skipped composer, so it never fires. The lie detector got bypassed by the lie.

Three-repo coordinated change:
- **Server:** participant injection
- **Daemon:** delete SF1-SF6 + relocated render.completed lie detector
- **Orchestrator scripts:** delete SF7

## Acceptance Criteria

### AC1: SERVER — Add participant injection for scene_illustration
- **File:** `sidequest-server/sidequest/server/websocket_session_handler.py` ~L2497
- [ ] For tier=='scene_illustration', set `params['participants']=[f'pc:{slug}']` and `params['pc_descriptor']=descriptor` (mirroring the existing portrait branch)
- [ ] Wiring test asserts dispatch includes both fields

### AC2: DAEMON SF1 — Replace silent gate with error on missing fields
- **File:** `daemon.py:454`
- [ ] Remove silent gate `if subject and world and genre and not positive_prompt:`
- [ ] When any required field is missing, raise `RenderConfigError('missing field: <name>')`
- [ ] Emit OTEL span `compose.gate_short_circuit` on error
- [ ] No fall-through

### AC3: DAEMON SF2 — Delete broad except in try_compose_prompt_for
- **File:** `zimage_mlx_worker.py:169-191`
- [ ] Delete broad `except Exception` handler
- [ ] `ValidationError` and `CatalogMissError` surface as `RenderConfigError`
- [ ] Function either returns `ComposedPrompt` or raises

### AC4: DAEMON SF3 — Delete no-style-injection fallback branch
- **File:** `zimage_mlx_worker.py:419-441` (`_compose_prompt` fallback branch)
- [ ] DELETE the no-style-injection fallback
- [ ] If worker is reached without `params['positive_prompt']`, raise `RenderConfigError('compose pipeline failed to produce a prompt')`
- [ ] No styleless render path exists

### AC5: DAEMON SF4/SF5/SF6 — Raise StyleMissError on absent key or empty suffix
- **File:** `catalogs.py:267-322` (get_world / get_genre / _load_world / _load_genre)
- [ ] Raise `StyleMissError` on absent key OR empty positive_suffix
- [ ] Emit OTEL signal per failure: `style_catalog.miss` with attributes `kind=world|genre genre=X world=Y reason=missing|empty`
- [ ] Worlds without visual_style.yaml or with empty positive_suffix become unrenderable — confirmed contract

### AC6: ORCHESTRATOR SF7 — Delete script-local pre-composed fallback
- **File:** `scripts/render_common.py:422`
- [ ] Delete script-local pre-composed fallback
- [ ] `catalog_compose=True` is required; `catalog_ref` empty is a hard error, not a fall-through

### AC7: RELOCATED LIE DETECTOR — render.completed observability
- [ ] Emit OTEL span `render.completed` at the worker level after prompt is finalized — outside the composer that may not run
- [ ] Attributes: `{ genre, world, world_style_applied, genre_style_applied }`
- [ ] `world_style_applied=True` iff the world's positive_suffix substring appears in the final prompt going to Z-Image
- [ ] Daemon logs ensure this span fires on every image generation attempt

### AC8: DAEMON TESTS — Compose and dispatch error paths
- [ ] `test_composer.py`: `test_compose_raises_on_unknown_world_style` (world missing from catalog)
- [ ] `test_composer.py`: `test_compose_raises_on_empty_world_positive_suffix` (world present but empty positive_suffix)
- [ ] `test_daemon.py` or dispatch: `test_render_fails_loudly_on_missing_world` (missing world schema)
- [ ] `test_daemon.py` or dispatch: `test_render_fails_loudly_on_validation_error` (Z-Image contract violation)

### AC9: SERVER TESTS — Wiring test for participant injection
- [ ] Wiring test that scene_illustration dispatch includes `participants` and `pc_descriptor`
- [ ] Test verifies both fields are present in the RenderRequest message

### AC10: ORCHESTRATOR TESTS — Smoke test for script error path
- [ ] `scripts/render_common.py` smoke test that `render_batch()` raises when `catalog_ref` is empty and `catalog_compose=True`

### AC11: VERIFICATION — Coyote Star POI render
- [ ] Coyote Star POI render shows McQuarrie/Berkey/Leone painterly styling end-to-end (no prose-bleed CG)
- [ ] Production daemon log `/tmp/sidequest-daemon.log` shows zero `compose.skipped` warnings

### AC12: PRECONDITION — sidequest-content sync
- [ ] Manual verification: sidequest-content PR #152 release-sync includes the per-world visual_style.yaml decomposition
- [ ] Verify before merging the daemon teardown PR — otherwise prod content lacks the per-world files and every render breaks

### AC13: FUTURE — Scene-illustration cutscene decision
- [ ] OPEN-DECISION DEFERRED — scene_illustration with no on-screen player character (cutscene of villain alone, place-of-action)
- [ ] Current ship: `participants=[pc:slug]` always
- [ ] Follow-up filed only if/when a cutscene case surfaces

## Story Context

### Domain: Image Render Pipeline
The image render pipeline (daemon) composes styled prompts for Z-Image based on world/genre visual_style.yaml configs. Seven layers of silent fallbacks meant that when visual_style.yaml decomposition broke the topmost gate, every render silently downgraded to raw narration prose without style application.

### Root Cause
1. **SF1 (daemon.py):** Gate checks for field presence but doesn't error on miss; falls through to next layer
2. **SF2 (zimage_mlx_worker):** Broad `except Exception` catches validation errors and returns empty prompt
3. **SF3 (zimage_mlx_worker):** Fallback branch renders without style injection when composer is skipped
4. **SF4/SF5/SF6 (catalogs.py):** Missing world/genre style configs silently return empty or default values instead of failing
5. **SF7 (orchestrator scripts):** Script-local fallback provides pre-composed prompt when catalog lookup fails
6. **Missing lie detector:** `world_style_applied` OTEL signal was emitted inside the composer (which got skipped), so it never fired. The lie detector was inside the broken path.

**Symptom observed:** Coyote Star POI renders show photoreal CG with raw prose-bleed text (no styling). Same narration text appears verbatim in image, indicating style composition was completely bypassed.

### Integration Points
- **Content:** visual_style.yaml per-world configs (sidequest-content PR #152) must be present before daemon changes land
- **Server:** scene_illustration dispatch must inject participants and descriptor (mirroring portrait branch)
- **Daemon:** every fallback must be deleted; missing fields = hard error with OTEL signal
- **GM Panel:** OTEL render.completed span reports whether style was actually applied (lie detector)

### Testing Approach for TEA
The RED tests must exercise:
1. Error paths when required fields are missing (SF1 gate)
2. Missing world/genre style configs (SF4/SF5/SF6)
3. Validation errors from Z-Image (SF2)
4. Server dispatch includes participant injection (AC1)
5. Orchestrator script fails on empty catalog_ref (AC10)
6. Lie detector fires with correct style_applied attributes (AC7)

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-04-29T20:51:42Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-29T20:49:59Z | 2026-04-29T20:51:42Z | 1m 43s |
| red | 2026-04-29T20:51:42Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each entry: one list item. Use "No upstream findings" if none.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Sm Assessment

**Setup Complete:** Yes
**Story:** 45-37 — Image pipeline silent-fallback teardown — kill SF1-SF7 + render.completed lie detector
**Workflow:** tdd (phased)
**Repos:** server, daemon, orchestrator
**Branches:** `feat/45-37-image-pipeline-silent-fallback-teardown` created in all three repos
**Jira:** None — sprint-YAML-only tracking per user instruction
**ACs:** 14 acceptance criteria captured covering server participant injection, six daemon delete points (SF1–SF6), orchestrator scripts SF7, relocated render.completed lie detector OTEL, four test surfaces, end-to-end visual verification, PR #152 precondition, and one deferred decision (cutscene case).

**Design Decisions Confirmed (with user):**
1. `scene_illustration` always sets `participants=[pc:<slug>]` — cutscene case deferred to follow-up if it surfaces.
2. Worlds without `visual_style.yaml` or with empty `positive_suffix` become unrenderable. Hard contract: every world ships visual_style or it can't render.
3. `sidequest-content` PR #152 precondition tracked as manual verification, not a depends_on gate — verify before daemon teardown PR (45-38 work) merges.

**Spec Source:** Full Inigo handoff transcript with file paths and line numbers preserved in conversation context above; story description and ACs derived from it.

**Handoff:** To Fezzik (TEA) for RED phase — write failing tests covering all 14 ACs across the four test surfaces (daemon test_composer.py, daemon test_daemon.py / dispatch, server scene_illustration wiring, orchestrator scripts/render_common smoke).