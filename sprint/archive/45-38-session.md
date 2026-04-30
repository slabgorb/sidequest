---
story_id: "45-38"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 45-38: Z-Image config — add high-fidelity tier (base 1.0) for genre-pack pre-gen

## Story Details
- **ID:** 45-38
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p3
- **Type:** bug
- **Stack Parent:** none

## Story Description

Daemon Z-Image config (sidequest-daemon/sidequest_daemon/media/zimage_config.py) pins Turbo at 8 steps, CFG 0, 768x1024 portrait. Same prompt in Draw Things using base Z-Image 1.0 at 20 steps, CFG 4, 1024x1024 produces visibly more painterly output — McQuarrie/Berkey concept-art adherence crystallizes only at higher step counts on the non-distilled variant. Diagnosed during Coyote Reach picker-portrait authoring; reference image at ~/Desktop/0_painted_sci_fi_concept_art_..._3447260204.png. Two paths: (a) flip globally to base — ~3x wall-clock for all renders; (b) add high-fidelity tier for content pre-gen, keep Turbo for in-session live conjure. (b) preferred — speed matters for live narration, fidelity matters for picker assets.

## Acceptance Criteria
1. New high-fidelity tier wired into mflux config: base Z-Image 1.0, 20 steps, CFG 4, 1024x1024
2. scripts/generate_portrait_images.py and generate_poi_images.py route to the new tier by default for genre-pack pre-gen
3. In-session render path (live narration) continues to use Turbo for latency
4. Regenerated picker_voidborn_medic_m01.png shows visibly more painterly brushwork than current 8-step Turbo version, comparable to Draw Things reference
5. OTEL render.prompt_composed emits model_variant and steps so the GM panel shows which tier ran

## Workflow Tracking
**Workflow:** tdd (phased)
**Phase:** finish
**Phase Started:** 2026-04-30T20:06:49Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-30 | 2026-04-30T19:31:19Z | 19h 31m |
| red | 2026-04-30T19:31:19Z | 2026-04-30T19:40:59Z | 9m 40s |
| green | 2026-04-30T19:40:59Z | 2026-04-30T19:50:48Z | 9m 49s |
| spec-check | 2026-04-30T19:50:48Z | 2026-04-30T19:55:14Z | 4m 26s |
| verify | 2026-04-30T19:55:14Z | 2026-04-30T19:58:46Z | 3m 32s |
| review | 2026-04-30T19:58:46Z | 2026-04-30T20:05:42Z | 6m 56s |
| spec-reconcile | 2026-04-30T20:05:42Z | 2026-04-30T20:06:49Z | 1m 7s |
| finish | 2026-04-30T20:06:49Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Improvement** (non-blocking): Story scope says "single repo (daemon)" but
  AC2 also touches the orchestrator repo (`scripts/generate_portrait_images.py`,
  `scripts/generate_poi_images.py`, `scripts/render_common.py`). Two repos will
  carry commits/PRs for this story (daemon + orchestrator). Affects merge ordering
  — the daemon tier config must land before the script wiring is meaningful, and
  the script tests assert both source-string content (daemon-independent) and
  signature/payload propagation (daemon-independent at the kwarg level). *Found
  by TEA during test design.*

- **Gap** (non-blocking): Pre-existing test failure in
  `tests/test_render_common.py::test_resolve_lora_args_resolved_loras_used_directly`
  — fails with `assert ['/Users/slabgorb/Projects/oq-2/sidequest-content/lora/a.safetensors'] == ['a.safetensors']`.
  Affects `scripts/render_common.py::resolve_lora_args` (resolves relative
  filenames against an absolute LORA_ROOT). Not caused by 45-38; the assertion
  expects raw `file` values but the function now returns absolute paths. Out
  of scope for this story — flagging so Dev doesn't try to fix it on this
  branch. *Found by TEA during test design.*

### Architect (spec-check)

- **Gap** (non-blocking): AC1 is structurally satisfied (config table exists with correct values, request plumbing carries fidelity end-to-end) but functionally partial — `ZImageMLXWorker` still loads turbo at init and does not consume the new tier. Affects `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py`. Recommended path: **file a follow-up story** (e.g. 45-39) for the worker swap rather than reopening this PR. The wiring delivered here is independently useful and the worker swap raises architectural questions (model swap latency vs. dual-load memory vs. daemon-mode separation) that deserve a focused story. Without the follow-up, AC4 cannot be met at verify time. *Found by Architect during spec-check.*

### Dev (implementation)

- **Gap** (non-blocking): Three pre-existing test failures in
  `sidequest-daemon/tests/test_composer.py` predate this branch and stem
  from commit `e3290d4 chore(cameras): blank portrait_3q prompt — fights
  Z-Image natural framing` on `develop`. Tests still assert `"three-quarter"`
  in the camera layer tokens, but `cameras.yaml` now intentionally returns
  empty content for `portrait_3q`. Affects:
  `tests/test_composer.py::test_portrait_camera_uses_recipe_default`,
  `test_compose_portrait_assembles_in_order`,
  `test_golden_portrait` (golden file regen needed).
  None of these touch the prompt_composer changes for 45-38; my Story 45-38
  composer edits only added new payload keys (fidelity, model_variant,
  steps) to render.prompt_composed. Out of scope — file as a follow-up
  cleanup story to update test assertions and regenerate the golden.
  *Found by Dev during GREEN.*

- **Improvement** (non-blocking): The daemon's `ZImageMLXWorker` is a
  per-process singleton (Story 43-5) with class-level `MODEL_VARIANT =
  "z-image-turbo"`. Story 45-38 wires fidelity from script → daemon
  request → composer → OTEL, but the worker still loads a single model
  at startup. This means an HF render request will route through the
  composer (correct OTEL emission, correct steps/CFG passed through) but
  the actual mflux inference still uses the turbo model — so AC4 (visibly
  more painterly output) cannot be met without one of: (a) loading both
  turbo and base models at startup with per-request switching (~2x VRAM),
  (b) lazy-swap with reload latency (~30s+), or (c) daemon-mode at
  startup (`SIDEQUEST_DAEMON_FIDELITY=high_fidelity` env), where the
  daemon process loads one model and rejects requests for the other
  fidelity with a structured error. Affects
  `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py`
  (worker `MODEL_VARIANT` + `TIER_CONFIGS` + `load_model`). Recommended
  follow-up: (c) — minimal architectural disruption, honors CLAUDE.md
  "No Silent Fallbacks." Without this, AC4 verification at the verify
  phase will not produce the expected painterly improvement.
  *Found by Dev during GREEN.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **AC4 omitted from test suite**
  - Spec source: 45-38 ACs in session file, AC-4
  - Spec text: "Regenerated picker_voidborn_medic_m01.png shows visibly more painterly brushwork than current 8-step Turbo version, comparable to Draw Things reference"
  - Implementation: No automated test written for AC4. The acceptance is a visual-quality eyeball comparison against `~/Desktop/0_painted_sci_fi_concept_art_..._3447260204.png`.
  - Rationale: There is no objective unit-testable signal for "more painterly brushwork." A perceptual metric (SSIM, LPIPS) could be added but the threshold is itself subjective and prone to false positives. The proper home for AC4 is a verify-phase manual confirmation by the user.
  - Severity: minor
  - Forward impact: Verify phase (or Reviewer) must regenerate one portrait at high-fidelity and eyeball it against the reference before claiming AC4 met. This is documented in the SM assessment risks already.

- **AC1 width/height locked only on PORTRAIT tier**
  - Spec source: 45-38 AC-1 in session file
  - Spec text: "base Z-Image 1.0, 20 steps, CFG 4, 1024x1024"
  - Implementation: The 1024x1024 dimension is locked on `RenderTier.PORTRAIT` only. Other tiers (LANDSCAPE, SCENE_ILLUSTRATION, CARTOGRAPHY, etc.) get HF entries with locked steps=20 and guidance=4.0 but unspecified width/height.
  - Rationale: The bug was discovered during portrait authoring (Coyote Star picker portraits). AC1 only names the portrait dimension explicitly. Forcing 1024x1024 on landscape would change the aspect ratio (currently 1024x768) and cause unrelated regressions. Steps + guidance are the painterly-output drivers per the AC; resolution is shape-driven.
  - Severity: minor
  - Forward impact: Dev decides per-tier HF dimensions. POI/landscape pre-gen will likely keep 1024x768 (aspect parity with turbo) — that's not a deviation, just a Dev judgment call. If Reviewer disagrees with portrait being the only tier with explicit AC1 dimension, escalate.

- **API shape prescribed (model_variant on ZImageTierConfig + get_zimage_config helper + RenderTarget.fidelity field)**
  - Spec source: epic-45 design themes ("don't reinvent — extend"), AC1+AC3+AC5
  - Spec text: ACs describe behavior, not API shape.
  - Implementation: Tests assume (a) `ZImageTierConfig` gains a required `model_variant: str` field, (b) a parallel `ZIMAGE_HIGH_FIDELITY_TIER_CONFIGS` dict, (c) a `get_zimage_config(tier, fidelity="turbo")` helper, (d) `RenderTarget` gains a `fidelity: str = "turbo"` field, (e) `send_render`/`render_batch` accept `fidelity="turbo"` kwarg.
  - Rationale: Tests need a public surface to call. The shape extends the existing module-level dict pattern in zimage_config.py (consistent with the "don't reinvent" theme). If Dev prefers a different shape (e.g. an `Enum` instead of a string Literal), this is a deviation Dev can log when refactoring tests.
  - Severity: minor
  - Forward impact: Dev may revise the test surface if a different API shape better fits the existing patterns. Tests should still cover AC1/AC3/AC5 behavior at the same granularity.

### Dev (implementation)

- No deviations from spec. Implemented the API shape TEA prescribed: `Literal["turbo", "high_fidelity"]` (not an Enum), parallel HF table (not a unified dict with a fidelity key), `get_zimage_config(tier, fidelity)` helper, `RenderTarget.fidelity` pydantic field, `send_render`/`render_batch` `fidelity` kwarg with default `"turbo"`. The composer's kind→tier mapping (`portrait`→PORTRAIT, `poi`→LANDSCAPE, `illustration`→SCENE_ILLUSTRATION) is a new helper but is internal to the composer and not externally specified by any AC — not a deviation, just a consequence of the composer not previously needing a tier reference.

### Architect (spec-check)

- **AC1 partially met — worker does not consume the new tier**
  - Spec source: 45-38 AC-1 in session file
  - Spec text: "New high-fidelity tier wired into mflux config: base Z-Image 1.0, 20 steps, CFG 4, 1024x1024"
  - Implementation: The tier is defined in `ZIMAGE_HIGH_FIDELITY_TIER_CONFIGS` with the correct values, and the request payload carries `fidelity` end-to-end (script → wire → daemon → composer → OTEL). However, `ZImageMLXWorker.MODEL_VARIANT` is still class-level `"z-image-turbo"` and `TIER_CONFIGS` still hardcodes 8-step turbo values. The actual mflux model loaded at worker init does not vary with `params["fidelity"]`. So an HF render request travels through the system, the OTEL span correctly reports `model_variant="z-image"` and `steps=20`, but the inference step uses the loaded turbo model with the original turbo parameters.
  - Rationale: The phrase "wired into mflux config" admits two readings — (a) the data table that drives mflux exists with these values, (b) mflux at render time uses these values. Reading (a) is met; reading (b) is not. Dev's delivery finding flags this honestly and proposes daemon-mode separation (env var `SIDEQUEST_DAEMON_FIDELITY`) as the cleanest follow-up.
  - Severity: major (blocks AC4 — without this, regenerated portraits will be visually identical to the current Turbo output)
  - Forward impact: AC4 cannot be verified at the verify or review phase as currently implemented. The user must decide one of: (1) accept the wiring layer as the deliverable for 45-38 and split out a follow-up story for the worker swap (file as 45-39 or similar), (2) re-loop Dev to add the worker swap now (option (c) from Dev finding — env-var-driven daemon mode, ~30 LOC, fits within the 3-pt envelope at the cost of a second daemon-restart cycle for testing). Architect recommends (1): the wiring is independently useful, the worker swap has architectural questions (model swap latency vs. dual load vs. process separation) that benefit from a focused story.

### TEA (test verification)

- No deviations from spec during verify phase. The simplify pass produced no actionable findings within 45-38's scope; no fixes were applied; no quality-pass exceptions were granted. Pre-existing failures (test_composer.py portrait_3q, test_resolve_lora_args_resolved_loras_used_directly) and pre-existing lint issues (scene_interpreter.py, test_embed_endpoint_story_37_5.py) remain as documented in earlier delivery findings — not introduced by this story.

### Architect (reconcile)

This is the consolidated deviation manifest for Story 45-38 — the audit artifact summarizing what landed vs. what the spec asked for.

**Verification of existing entries:**

- TEA's AC4 omission: confirmed accurate. AC4 is a visual-quality eyeball test against `~/Desktop/0_painted_sci_fi_concept_art_..._3447260204.png`. No automated test is feasible. Properly deferred to verify-phase manual confirmation.
- TEA's AC1 width/height locked only on PORTRAIT: confirmed accurate. `ZIMAGE_HIGH_FIDELITY_TIER_CONFIGS[RenderTier.PORTRAIT]` is 1024x1024 (square — the AC1 specified dimension). Other tiers use their existing turbo aspect ratios (LANDSCAPE 1024x768, etc.). Steps + guidance lock to 20 + 4.0 across every tier.
- TEA's API-shape prescription: confirmed accurate. Dev followed the prescribed shape (Literal not Enum, parallel HF table, `get_zimage_config(tier, fidelity)` helper, `RenderTarget.fidelity` pydantic field, `send_render`/`render_batch` `fidelity` kwarg).
- Dev's "no deviations": confirmed — implementation matched the prescribed shape with no scope changes.
- Architect's (spec-check) AC1 partial finding: confirmed and elevated to the central reconcile concern below.
- TEA's verify-phase "no deviations": confirmed.

**No additional deviations found** beyond those already logged. The reconcile audit reduces to a single load-bearing concern, captured below.

**Central reconcile concern — the wiring/inference split:**

- **Spec source:** 45-38 ACs 1 and 4 (session file, lines 23, 26)
- **Spec text (AC-1):** "New high-fidelity tier wired into mflux config: base Z-Image 1.0, 20 steps, CFG 4, 1024x1024"
- **Spec text (AC-4):** "Regenerated picker_voidborn_medic_m01.png shows visibly more painterly brushwork than current 8-step Turbo version, comparable to Draw Things reference"
- **Implementation:** The configuration table exists with the correct values and the request payload carries `fidelity` end-to-end (script → JSON-RPC params → `StageCue.metadata` → `RenderTarget.fidelity` → composer span). The composer's `render.prompt_composed` OTEL span correctly reports `model_variant="z-image"` and `steps=20` when `fidelity="high_fidelity"` is requested. **However**, `ZImageMLXWorker` still hardcodes `MODEL_VARIANT = "z-image-turbo"` and a turbo-only `TIER_CONFIGS` dict. The actual mflux inference uses the loaded turbo model regardless of request fidelity. So an HF render request travels through the system, the OTEL span reports HF values, but the rendered pixels come from turbo.
- **Rationale:** The phrase "wired into mflux config" admits two readings — (a) the data table that drives mflux exists with these values, (b) mflux at render time uses these values. Reading (a) is met; reading (b) is not. Reading (b) is what AC4 requires. Splitting the worker swap into a follow-up keeps the wiring layer's commit history clean and lets the architectural choice (daemon-mode env var vs dual-load vs lazy-swap) be made deliberately rather than improvised in this PR. The Reviewer endorsed this split.
- **Severity:** major (blocks AC4)
- **Forward impact:** AC4 verification is deferred to a follow-up story (suggested **45-39: ZImageMLXWorker daemon-mode env var for high-fidelity tier**). Without that follow-up landing, regenerating any picker portrait at `fidelity="high_fidelity"` produces a visually identical Turbo image. The OTEL span will report what was *requested*, not what was *rendered* — composer-vs-worker span divergence is the diagnostic signal. Recommended approach for the follow-up: option (c) from Dev's findings — `SIDEQUEST_DAEMON_FIDELITY` env var read at worker init, daemon process loads one model and rejects requests for the other fidelity with a structured error (no silent fallbacks, per CLAUDE.md). Estimated scope: ~30 LOC + tests, fits a 2-pt story.

**Audit summary for the boss:**

- Wiring landed honestly: every layer between the script and the OTEL emission threads `fidelity` correctly, validated at the pydantic boundary, no silent fallbacks. 22 new tests, all passing.
- AC4 is a paper victory until 45-39 lands: rendered output won't show the painterly difference until the worker swap.
- Filed-or-merged decision belongs to the user. Recommended: file 45-39, merge this PR, schedule 45-39 next.

## Sm Assessment

**Story scope:** Add a `high_fidelity` tier to Z-Image config (base 1.0, 20 steps, CFG 4, 1024x1024) alongside the existing Turbo tier. Wire pre-gen scripts to the new tier; keep Turbo for in-session live narration. Surface model_variant + steps on the OTEL render.prompt_composed span.

**Surface area:** Single repo (daemon). Touch points: `sidequest-daemon/sidequest_daemon/media/zimage_config.py`, `scripts/generate_portrait_images.py`, `scripts/generate_poi_images.py`, and the OTEL emission site for `render.prompt_composed`. Minor — well within tdd scope.

**TDD shape:** TEA writes failing tests for AC1 (config tier exists with correct values), AC2 (pre-gen scripts default to high-fidelity), AC3 (in-session path stays Turbo), AC5 (OTEL span carries model_variant + steps). AC4 is a visual-quality acceptance — verifiable only by regen + eyeball; not a unit test. Flag for verify phase as a manual step.

**Risks / sharp edges:**
- AC4 is subjective. The verify step needs the user (Keith) to compare regenerated `picker_voidborn_medic_m01.png` against the Draw Things reference. Don't claim AC4 met without a human eye.
- Branch already exists from a prior partial setup (commit b927514). Confirm working tree is clean before TEA writes tests.
- Don't reinvent: there's an existing tier mechanism in zimage_config.py — extend it, don't replace.

**Workflow:** tdd phased. Next: TEA writes failing tests (RED).

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Status:** RED (22 new failing tests, ready for Dev)

**Test Files:**
- `sidequest-daemon/tests/test_zimage_high_fidelity_tier.py` — new file, 15 tests
  covering AC1 (config values), AC3 (turbo unchanged), AC5 (OTEL span)
- `tests/test_render_common.py` (orchestrator) — 7 new tests covering AC2 (script
  wiring) plus an end-to-end fidelity-propagation wiring test

**Tests Written:** 22 tests covering 4 ACs (AC1, AC2, AC3, AC5). AC4 is visual-eyeball, not unit-testable — flagged as a verify-phase manual step.

### Rule Coverage (.pennyfarthing/gates/lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 Silent exception swallowing | `test_get_zimage_config_unknown_fidelity_raises`, `test_render_target_rejects_unknown_fidelity` (no silent fallbacks — both must raise) | failing (RED) |
| #2 Mutable default arguments | N/A — no new function defs in test code expose mutables | n/a |
| #3 Type annotation gaps at boundaries | Tests exercise the public surface via signature inspection (`test_send_render_accepts_fidelity_kwarg`, `test_render_batch_accepts_fidelity_kwarg`) | failing (RED) |
| #4 Logging coverage | N/A — config + composer paths, no new logging surface | n/a |
| #5 Path handling | N/A — no new path manipulation | n/a |
| #6 Test quality | Self-checked — every test has specific value assertions, no `assert True`, no `assert result`-only checks, no skipped tests, no parametrize duplicates | passing (this audit) |
| #7 Resource leaks | N/A — wiring test uses fake reader/writer; no real socket | n/a |
| #8 Unsafe deserialization | N/A — JSON-RPC payload uses `json.loads` only on the test-fake response, not user input | n/a |
| #9 Async/await pitfalls | Wiring test uses `asyncio.run` correctly with `monkeypatch` of `open_unix_connection`; fake writer's `drain()`/`wait_closed()` are awaitable | passing (this audit) |
| #10 Import hygiene | All imports explicit, no `*`; module-level imports of new symbols are inside test bodies so import errors don't cascade-fail unrelated tests | passing (this audit) |
| #11 Input validation at boundaries | `test_render_target_rejects_unknown_fidelity` enforces RenderTarget rejects bogus fidelity at construction (pydantic boundary) | failing (RED) |

**Rules checked:** 6 of 13 applicable Python rules have test coverage (the others don't apply — config + signature + composer surface, no I/O, no logging, no async pitfalls beyond the one wiring test).

**Self-check (Phase C):** No vacuous assertions. No `assert True`, no truthy-only checks, no `let _ =` equivalents (Python: nothing assigned-and-discarded). The broadest assertion is `pytest.raises(Exception)` on `test_render_target_rejects_unknown_fidelity` — broad because the field type (Literal vs Enum vs validated str) is left to Dev; Dev should narrow to `pydantic.ValidationError` or equivalent during GREEN if appropriate.

**Wiring test:** `test_send_render_fidelity_propagates_to_request_payload` exercises the seam from the kwarg through to the JSON-RPC params dict the daemon receives. Without this test, `send_render` could accept `fidelity` and drop it before serialization — passing tests, broken production. Per CLAUDE.md "Every Test Suite Needs a Wiring Test."

**Branch state:**
- Orchestrator: `feat/45-38-zimage-high-fidelity-tier` (commit 8939cd9 — orchestrator test edits)
- Daemon: `feat/45-38-zimage-high-fidelity-tier` (commit 4ea8c26 — new daemon test file)

**Pre-existing failure (not my code):** `tests/test_render_common.py::test_resolve_lora_args_resolved_loras_used_directly` was already failing on develop. Flagged in Delivery Findings as out-of-scope.

**Handoff:** To Dev (Ponder Stibbons) for GREEN phase implementation in `sidequest-daemon/sidequest_daemon/media/zimage_config.py`, `recipes.py` (RenderTarget.fidelity), `prompt_composer.py` (OTEL span attrs), and `scripts/render_common.py` + `scripts/generate_*.py`.
## Dev Assessment

**Phase:** finish
**Status:** GREEN (all 22 Story 45-38 tests pass)

### Implementation Summary

| File | Change |
|------|--------|
| `sidequest-daemon/sidequest_daemon/media/zimage_config.py` | Added `ZIMAGE_BASE_MODEL_VARIANT="z-image"`, `model_variant` field on `ZImageTierConfig`, parallel `ZIMAGE_HIGH_FIDELITY_TIER_CONFIGS` table, `Fidelity` Literal alias, and `get_zimage_config(tier, fidelity)` lookup helper. Existing `ZIMAGE_TIER_CONFIGS` constructor calls updated to include `model_variant=ZIMAGE_MODEL_VARIANT`. |
| `sidequest-daemon/sidequest_daemon/media/recipes.py` | `RenderTarget` gains `fidelity: Literal["turbo", "high_fidelity"] = "turbo"`. Pydantic enforces validation — bogus values raise `ValidationError` at construction (no silent fallbacks). |
| `sidequest-daemon/sidequest_daemon/media/prompt_composer.py` | `render.prompt_composed` OTEL span now carries `fidelity`, `model_variant`, and `steps`. Added `_KIND_TO_TIER` map (portrait→PORTRAIT, poi→LANDSCAPE, illustration→SCENE_ILLUSTRATION) so the composer can look up the Z-Image config from the kind it already has. |
| `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py` | `build_cue_from_params` now reads `params["fidelity"]` (default `"turbo"`) and stashes it in `StageCue.metadata`; `build_render_target` pulls it back out and pins it on every `RenderTarget` shape (portrait, poi, illustration). |
| `scripts/render_common.py` | `send_render` and `render_batch` accept `fidelity` kwarg (default `"turbo"`); `send_render` writes `params["fidelity"]` into the JSON-RPC payload. |
| `scripts/generate_portrait_images.py` | `render_batch` call sets `fidelity="high_fidelity"` for picker portrait pre-gen. |
| `scripts/generate_poi_images.py` | Same — POI landscape pre-gen routes to high-fidelity. |

### Design Decisions

**Fidelity is a Literal alias, not an Enum.** Serializes naturally over JSON-RPC; pydantic validation rejects bogus values without a separate decode step.

**`ZImageTierConfig` gained a required `model_variant` field.** Single-source-of-truth for the model alias keeps OTEL emission honest — span attributes come from the same dict the worker would consult, so a future drift between the two is visible.

**Composer reports requested fidelity, not effective fidelity.** The composer fires its span before any model is loaded, so it reports what the caller asked for. The worker emits its own `model.variant` span at load time. A divergence between composer and worker spans is itself diagnostic.

**Worker model swap intentionally out of scope.** See delivery findings — getting AC4 (visibly more painterly output) requires either dual-model load, lazy reload, or daemon-mode separation. None fits in a 3-pt story without scope creep.

### Test Results

| Test File | Tests | Pass | Fail |
|-----------|-------|------|------|
| `sidequest-daemon/tests/test_zimage_high_fidelity_tier.py` | 15 | 15 | 0 |
| `tests/test_render_common.py` (new tests for 45-38) | 7 | 7 | 0 |
| `sidequest-daemon/tests/test_zimage_config.py` (existing — regression check) | 7 | 7 | 0 |
| `sidequest-daemon/tests/test_composer.py` | 255 | 252 | 3 |
| `sidequest-daemon/tests/*` (other) | ~270 | ~270 | 0 |

All 22 new Story 45-38 tests pass. The 3 `test_composer.py` failures predate this branch — see Dev delivery findings (cameras.yaml `portrait_3q` was intentionally blanked in commit `e3290d4`, but the assertions checking for `"three-quarter"` were not updated and the golden file was not regenerated). Pre-existing `test_resolve_lora_args_resolved_loras_used_directly` also continues to fail — flagged by TEA, still out of scope.

### Branch State

- Daemon: `feat/45-38-zimage-high-fidelity-tier` — commits `4ea8c26` (TEA tests), `d531874` (Dev impl)
- Orchestrator: `feat/45-38-zimage-high-fidelity-tier` — commits `8939cd9` (TEA tests), `5c41c80` (Dev impl)

### Handoff

To TEA (Igor) for verify phase: simplify pass + final quality-pass gate. AC4 (visual eyeball comparison) is a verify-time manual step against the Draw Things reference — note that without the worker model-swap follow-up, AC4 will not produce the expected painterly difference; the OTEL span will report the requested HF values but the actual mflux inference will still use turbo. Reviewer/user should be aware before claiming AC4 met.

**Implementation Complete:** Yes

**AC Coverage:**

- AC-1: high-fidelity tier wired into mflux config (base Z-Image 1.0, 20 steps, CFG 4, 1024x1024 portrait) — DONE for the config table; `ZIMAGE_HIGH_FIDELITY_TIER_CONFIGS` defines exactly these values for `RenderTier.PORTRAIT`. Worker consumption of this table is a separate concern — see Architect deviation.
- AC-2: pre-gen scripts (`generate_portrait_images.py`, `generate_poi_images.py`) route to the high-fidelity tier by default — DONE. Both call `render_batch(..., fidelity="high_fidelity")`.
- AC-3: in-session render path stays Turbo for latency — DONE. The `fidelity` kwarg defaults to `"turbo"` on `send_render` and `render_batch`; in-session callers omit it and keep existing behavior.
- AC-4: regenerated picker_voidborn_medic_m01.png shows visibly more painterly brushwork — DEFERRED to verify-phase manual confirmation, AND blocked by the worker model-swap follow-up flagged by Dev. Without the worker change, regenerated images will be visually identical to current Turbo output even though the OTEL span reports HF values. See Architect deviation.
- AC-5: render.prompt_composed OTEL span emits `model_variant` and `steps` — DONE. The composer span now carries `fidelity`, `model_variant`, and `steps`, sourced from `get_zimage_config(tier, fidelity)`.
## Architect Assessment

**Phase:** finish
**Status:** PASS_WITH_FOLLOWUP

### Spec Alignment

| AC | Status | Notes |
|----|--------|-------|
| AC-1 | partial | Config defined and routed end-to-end; worker doesn't consume it yet |
| AC-2 | done | Both pre-gen scripts pass `fidelity="high_fidelity"` |
| AC-3 | done | Default fidelity `"turbo"` preserved on every public surface |
| AC-4 | deferred | Visual eyeball — blocked by AC-1's worker gap |
| AC-5 | done | OTEL `render.prompt_composed` carries `fidelity`, `model_variant`, `steps` |

### Architectural Review

**The wiring is sound.** Fidelity flows through the request payload (`params["fidelity"]`), into `StageCue.metadata`, onto `RenderTarget.fidelity`, through `get_zimage_config(tier, fidelity)` lookup, and out the OTEL span. The composer reports requested fidelity; the worker's existing `model.variant` span reports actual loaded variant — the divergence between the two is itself diagnostic, which is the correct lie-detector posture per CLAUDE.md.

**The composer's kind→tier mapping is internal and acceptable.** A `RenderTarget` carries `kind` (portrait/poi/illustration), not `RenderTier`. The composer maps `portrait→PORTRAIT`, `poi→LANDSCAPE`, `illustration→SCENE_ILLUSTRATION` for the Z-Image config lookup. The mapping is lossy on width/height (PORTRAIT vs PORTRAIT_SQUARE, LANDSCAPE vs CARTOGRAPHY), but the lossy axes are the worker's concern; the composer's only need from `get_zimage_config` is `model_variant` and `steps`, both of which are constant within a fidelity tier. No design problem.

**The Literal-not-Enum choice is correct.** Pydantic validates the field at construction without a separate decode step, and JSON-RPC carries the string value over the wire trivially. An Enum would have required an extra encode step on the script side.

**The major gap is the worker.** `ZImageMLXWorker` is a per-process singleton (Story 43-5) with class-level `MODEL_VARIANT = "z-image-turbo"` and a hardcoded `TIER_CONFIGS` dict. Without changing this, the actual mflux inference step uses the turbo model regardless of request fidelity. The current implementation OTEL-honestly reports what was requested (not what was used), but the user-visible output (AC4) won't show the painterly difference.

**Recommendation:** Close 45-38 with the wiring layer delivered. File a follow-up story (suggest 45-39) for the worker swap. The follow-up story should make a deliberate choice between three architectures:

1. **Daemon-mode separation** (env var `SIDEQUEST_DAEMON_FIDELITY`): one model per daemon process, requests with mismatched fidelity rejected with structured error. Cheapest and most CLAUDE.md-aligned (no silent fallbacks). Ops impact: pre-gen runs require restarting the daemon in HF mode.
2. **Dual-model load**: load both turbo and base at init, pick at render time. ~2x VRAM. Simplest from caller's POV.
3. **Lazy reload**: load whichever model is requested next, evicting the other. Latency hit on every fidelity flip (~30s+). Bad for mixed workloads.

Architect prefers (1). It's smallest, makes the failure mode loud, and matches the existing daemon's process-isolation philosophy (per ADR-035).

### Implementation Quality

- No silent fallbacks: `get_zimage_config` raises on unknown fidelity; `RenderTarget.fidelity` pydantic-validates.
- No stubs: every code path has a non-test consumer.
- Test wiring: TEA's `test_send_render_fidelity_propagates_to_request_payload` exercises the actual JSON-RPC seam with a fake unix-socket reader/writer — exactly the integration test CLAUDE.md mandates.
- OTEL: span attributes added per CLAUDE.md "every fix that touches a subsystem MUST add OTEL".

### Handoff

To TEA (Igor) for verify phase. The simplify pass and quality-pass gate proceed normally. Reviewer must read this assessment before claiming AC4 met. User decides whether to file the worker-swap follow-up before merging this PR or alongside it.
## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7 (4 daemon, 3 orchestrator)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | Both pre-existing/intentional: token-estimation duplication between daemon and scripts (predates 45-38), worker subprocess TIER_CONFIGS duplication (subprocess can't import — documented intentional coupling) |
| simplify-quality | 8 findings | All either pre-existing or false positive: dead-code claim on `_compose_prompt` is wrong (called at line 347; tests at test_zimage_mlx_worker.py:122); type-annotation gaps and import-order issues are pre-existing; lora-scales logging gap was untouched by 45-38 |
| simplify-efficiency | clean | 0 findings |

**Applied:** 0 high-confidence fixes (all high-confidence findings are out of scope for 45-38)
**Flagged for Review:** 0 (all medium-confidence findings predate this branch)
**Noted:** 2 (token-estimation duplication and subprocess tier-config sync — both pre-existing)
**Reverted:** 0

**Overall:** simplify: clean (no changes applied)

**Rationale for not auto-applying:** Per the verify-workflow protocol, only findings *introduced by this story's diff* are in scope. The simplify-quality report was generous in flagging adjacent pre-existing issues (which is correct paranoia for a quality scan), but acting on them would mix unrelated changes into 45-38's PR. The one finding that touches a 45-38-edited file (`_compose_prompt` dead-code claim in `zimage_mlx_worker.py`) is a false positive — `render()` calls `_compose_prompt` at line 347, and a test exercises it directly.

### Quality Checks

- Daemon pytest: 255 pass, 3 pre-existing failures (test_composer.py — cameras.yaml `portrait_3q` blank in commit e3290d4)
- Orchestrator pytest: 26 pass, 1 pre-existing failure (test_resolve_lora_args_resolved_loras_used_directly)
- Daemon ruff: 4 pre-existing issues in unrelated files (scene_interpreter.py E402, test_embed_endpoint_story_37_5.py F401×2) — none in 45-38 changed files

All pre-existing failures and lint issues are documented in delivery findings (TEA-red, Dev-green) as out-of-scope.

### Verify-Phase Notes for AC4

AC4 (visibly more painterly portrait regen) cannot be checked at this verify phase — the worker model swap is a follow-up per the architect's spec-check assessment. If the user/reviewer wants to manually attempt AC4 verification:

1. Restart the daemon
2. Run `python3 scripts/generate_portrait_images.py --genre coyote_star --force` (or equivalent for the target genre)
3. Compare the regenerated `picker_voidborn_medic_m01.png` against `~/Desktop/0_painted_sci_fi_concept_art_..._3447260204.png`
4. **Expected outcome:** The regenerated image will look visually identical to the previous Turbo output, because the worker still loads `z-image-turbo` regardless of `params["fidelity"]`. The OTEL `render.prompt_composed` span will correctly report `model_variant="z-image"` and `steps=20` (the requested values), but the actual mflux inference uses the loaded turbo model. This is the gap the architect flagged — the wiring is in place but the worker doesn't honor it yet.

### Handoff

To Reviewer (Granny Weatherwax) for code review. Reviewer must read the architect assessment before claiming AC4 met — the worker-swap follow-up is a known gap.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (282 pass, 4 pre-existing fails not in 45-38 surface) | confirmed: tests green, lint clean on changed files |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received: Yes** (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` settings)

## Reviewer Assessment

**Phase:** finish
**Status:** APPROVE_WITH_FOLLOWUP
**Decision:** Merge after the user files the worker-swap follow-up story. The wiring layer is honest and useful; the follow-up is the predicate for AC4 verification.

### Direct Diff Audit (Granny's own read)

I read the diff myself — 584 lines daemon, 218 lines orchestrator. Findings:

#### Confirmed: Architecture gap (architect already flagged)

The worker-side gap noted by Architect and Dev is correct: `ZImageMLXWorker.MODEL_VARIANT` and `TIER_CONFIGS` are still hardcoded to turbo. A request with `fidelity="high_fidelity"` flows correctly through `params → StageCue.metadata → RenderTarget.fidelity → composer span` and the OTEL faithfully reports `model_variant="z-image"` and `steps=20` — but the actual mflux inference uses the loaded turbo model. **AC4 (visibly more painterly portraits) cannot be met with this PR alone.** Architect's recommendation (file 45-39 for daemon-mode env-var separation) is correct: it's the smallest change that doesn't smuggle architecture into a 3-pt story.

I challenged this finding by checking the daemon's exception path — pydantic's `ValidationError` does inherit from `ValueError` in both v1 and v2, so `_handle_client`'s `except ValueError` would catch a bogus fidelity value and emit a structured `COMPOSE_FAILED` error. No silent fallback. The boundary is loud.

I also challenged the kind→tier mapping completeness: `RenderTarget.kind` is `Literal["portrait", "poi", "illustration"]` and `_KIND_TO_TIER` covers all three — exhaustive at the type level. If a new kind is added, the Literal change forces a co-edit in prompt_composer.py via the `dict[str, RenderTier]` annotation.

#### Confirmed: Minor DRY (low, non-blocking)

`zimage_config.py` defines `Fidelity = Literal["turbo", "high_fidelity"]` and `recipes.py` re-spells `Literal["turbo", "high_fidelity"]` inline on `RenderTarget.fidelity`. Importing the `Fidelity` alias from `zimage_config` would centralize the canonical list. **Don't block on this** — they're in the same package and any drift is a 1-line fix, but a future story that adds a third fidelity value would have to update two places. Worth a follow-up cleanup or reviewer-cleanup pass.

#### Confirmed: Test exception breadth (low, non-blocking)

- `test_get_zimage_config_unknown_fidelity_raises` uses `pytest.raises((ValueError, KeyError))` — implementation only raises `ValueError`. Catching KeyError is permissive cover for a different implementation; either tighten to `ValueError` only or remove the comment. Non-blocking — passes on the actual error type.
- `test_render_target_rejects_unknown_fidelity` uses `pytest.raises(Exception)` — broad. The actual error is `pydantic.ValidationError` (subclass of `ValueError`). Tightening to `ValidationError` would catch a future regression where pydantic stops validating. Non-blocking.

#### Challenged: Pre-existing failures

- `test_composer.py` 3 failures from `cameras.yaml portrait_3q` blank (commit `e3290d4`, predates branch) — verified by Dev's git log inspection. Not 45-38 territory; do not block.
- `test_resolve_lora_args_resolved_loras_used_directly` — TEA flagged at red phase; verified pre-existing. Do not block.
- Ruff lint findings in `scene_interpreter.py` and `test_embed_endpoint_story_37_5.py` — not in 45-38 changed files. Do not block.

### Spec Coverage

| AC | Status | Reviewer note |
|----|--------|---------------|
| AC-1 | partial | Tier defined with locked values; worker doesn't consume yet (architect-flagged) |
| AC-2 | done | Both pre-gen scripts pass `fidelity="high_fidelity"`; src grep confirms |
| AC-3 | done | All public surfaces default to `"turbo"`; in-session callers unaffected |
| AC-4 | deferred | Visual eyeball — blocked by AC-1 worker gap (follow-up required) |
| AC-5 | done | OTEL `render.prompt_composed` carries `fidelity`, `model_variant`, `steps`; verified by direct diff read at `prompt_composer.py:184-194` |

### Rule Compliance (Python lang-review checklist)

| # | Rule | Status |
|---|------|--------|
| 1 | Silent exception swallowing | PASS — `get_zimage_config` raises loudly on unknown fidelity; pydantic validates RenderTarget.fidelity at construction |
| 2 | Mutable default arguments | PASS — no new function defs introduce mutables |
| 3 | Type annotations at boundaries | PASS — `get_zimage_config` and `send_render`/`render_batch` fully annotated; `Fidelity` Literal alias exists |
| 4 | Logging coverage | N/A — no new logging surface introduced |
| 5 | Path handling | N/A — no new path manipulation |
| 6 | Test quality | PASS — every new test has specific value assertions; no `assert True`, no truthy-only checks |
| 7 | Resource leaks | PASS — wiring test uses fake reader/writer with proper close() |
| 8 | Unsafe deserialization | N/A — JSON-RPC payloads use `json.loads` only on test-fake response |
| 9 | Async/await pitfalls | PASS — wiring test uses `asyncio.run` correctly |
| 10 | Import hygiene | PASS — explicit imports throughout |
| 11 | Input validation at boundaries | PASS — pydantic enforces `Literal["turbo", "high_fidelity"]` on RenderTarget; daemon's `_handle_client` catches ValidationError as ValueError |
| 12 | Dependency hygiene | N/A — no new deps |
| 13 | Fix-introduced regressions | PASS — no findings to mitigate |

### Decision

**APPROVE** with the explicit precondition that the user files the worker-swap follow-up (suggest **45-39: ZImageMLXWorker daemon-mode env var for high-fidelity tier**) before or alongside merging. AC4 is currently a paper victory — the wiring is real but the inference still uses turbo. Granny doesn't approve paper victories. File the follow-up, then merge.

If the user wants AC4 actually verified in this PR, re-loop Dev to add the env-var-driven worker mode (~30 LOC per Dev's option (c)). That is a defensible scope expansion within the 3-pt envelope. Either path is acceptable; the dishonest path is shipping AC4 as "done".

### Handoff

To SM (Captain Carrot) for the spec-reconcile phase. SM should confirm with the user which path was taken (follow-up filed vs. PR expanded). If follow-up: open the PRs, wait for merge. If expansion: re-loop to Dev for the worker-mode env var.