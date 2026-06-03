---
story_id: "78-1"
jira_key: ""
epic: "78"
workflow: "tdd"
---
# Story 78-1: Daemon camera post-processing unwired — apply_post never invoked at render (wire or delete)

## Story Details
- **ID:** 78-1
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Repos:** daemon
**Phase:** finish
**Phase Started:** 2026-06-03T11:30:48Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03T06:51:00Z | 2026-06-03T10:59:04Z | 4h 8m |
| red | 2026-06-03T10:59:04Z | 2026-06-03T11:09:15Z | 10m 11s |
| green | 2026-06-03T11:09:15Z | 2026-06-03T11:17:50Z | 8m 35s |
| spec-check | 2026-06-03T11:17:50Z | 2026-06-03T11:19:14Z | 1m 24s |
| verify | 2026-06-03T11:19:14Z | 2026-06-03T11:25:11Z | 5m 57s |
| review | 2026-06-03T11:25:11Z | 2026-06-03T11:29:38Z | 4m 27s |
| spec-reconcile | 2026-06-03T11:29:38Z | 2026-06-03T11:30:48Z | 1m 10s |
| finish | 2026-06-03T11:30:48Z | - | - |

## Delivery Findings

**Investigation Gate Result (Pre-Red):** Live usage confirmed.

The camera preset `extreme_closeup_leone` in `sidequest-daemon/cameras.yaml` (lines 71-78) sets a `post:` directive with `kind: crop, mode: center, percent: 0.25`. This is a live, intentional camera spec that relies on post-processing. Therefore, the decision is to **WIRE** (not delete) `apply_post` and `required_render_size` into the render path.

Evidence:
- `sidequest-daemon/cameras.yaml:75-78` — extreme_closeup_leone has explicit post directive
- `sidequest_daemon/media/post_processor.py` — apply_post and required_render_size are fully implemented with Pillow
- `tests/test_post_processor.py` — comprehensive unit tests exist (crop, rotate, required_render_size math)
- `sidequest_daemon/media/workers/zimage_mlx_worker.py:render()` — render() currently returns after save (line 517) without invoking post-processing

Wiring required:
1. ZImageMLXWorker.render() must call required_render_size() to compute the generation size based on post directive
2. After image.save() at line 517, apply apply_post() to the generated image
3. Write integration test rendering extreme_closeup_leone camera (or similar) and asserting the crop was applied

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): the compose→params middle link (`composed.post` → `params["post"]`) is not directly behavior-tested — my RED suite brackets it at both ends (composer produces `ComposedPrompt.post`; `render()` consumes `params["post"]`) but the inline copy in `media/daemon.py` `_handle_client` (~line 728-732, alongside the existing `params["positive_prompt"] = composed.positive_prompt` copies) has no behavioral test because it lives in an async socket handler, not an extracted helper. Affects `sidequest_daemon/media/daemon.py` (Dev must add `params["post"] = composed.post.model_dump() if composed.post else None` there; Reviewer should eyeball that one line, or Dev may extract the compose-and-populate block into a testable helper like `build_cue_from_params` was). *Found by TEA during test design.*
- **Question** (non-blocking): `PostDirective.mode` (`center` | `subject_center`) is currently advisory — `apply_post`'s crop path always center-crops and ignores `mode`. `extreme_closeup_leone` sets `mode: center`, so wiring as-is is faithful today. If a future spec sets `subject_center`, that needs a subject bbox the daemon doesn't surface here — out of scope for 78-1, but worth a tracking note. Affects `sidequest_daemon/media/post_processor.py` (`_center_crop`). *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): the daemon tree is not `ruff format`-clean on `develop` (e.g. `recipes.py:160` comment alignment triggers a reformat on lines unrelated to 78-1). I left pre-existing style untouched (only `ruff check`, the gated `daemon-lint`, is enforced and passes) and made only my own added lines format-clean. A separate format-sweep story would clear the backlog. Affects `sidequest_daemon/` (repo-wide ruff format drift). *Found by Dev during implementation.*
- **Resolved (not a finding, noted for Reviewer):** TEA's flagged "untested middle link" (`composed.post` → `params["post"]`) is now wired at `media/daemon.py` in the compose seam (`params["post"] = composed.post.model_dump() if composed.post is not None else None`). It remains covered by bracketing (composer-end + render-end behavioral tests) rather than a direct socket-handler test — Reviewer should eyeball that one line per TEA's note. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): `apply_post`'s `mode: subject_center` is silently treated as `center` (pre-existing `_center_crop` behavior, now reachable in production via 78-1's wiring). No live spec uses it, but per "No Silent Fallbacks" a future story should either implement subject-aware cropping or make `apply_post` raise on an unsupported `mode`. Affects `sidequest_daemon/media/post_processor.py` (`_center_crop` ignores `directive.mode`). *Found by Reviewer during code review.*
- **Question** (non-blocking): a camera spec with a very small crop `percent` (e.g. 0.01) would make `required_render_size` demand a ~100×-per-axis source, a potential GPU-memory blowout — but only via an authored (trusted) `cameras.yaml`, not external input. Worth a sanity ceiling on `required_render_size` if author-tooling ever generates post directives. Affects `sidequest_daemon/media/post_processor.py` (`required_render_size`). *Found by Reviewer during code review.*

## Sm Assessment

**Setup complete — handing to TEA (red).** Story 78-1 is a 2pt TDD wiring-debt
story in `sidequest-daemon` only (branch `feat/78-1-wire-or-delete-daemon-apply-post`
off `develop`).

**Investigation gate (wire-vs-delete) is resolved → WIRE.** A live, in-use camera
preset — `extreme_closeup_leone` in `sidequest-daemon/cameras.yaml` — sets a
`post:` directive (`kind: crop, mode: center, percent: 0.25`). Deleting the post
path would silently discard a real directive, so the decision is to connect
`required_render_size` + `apply_post` into `ZImageMLXWorker.render` and prove it
with an integration test. The full composer→worker boundary trace and both
decision branches are documented in `sprint/context/context-story-78-1.md`.

**Red-phase ask (Igor):** write a failing integration test that drives the render
path for a spec carrying a `post:` directive and asserts the transform actually
applied (output reflects the center crop) — NOT a unit test of `apply_post` in
isolation, which already exists. Stub the MLX model to return a known synthetic
image so the assertion is on the post-transform, not real inference. This is the
wiring test the doctrine requires ("Verify Wiring, Not Just Existence").

**Scope guardrails:** daemon-only; do not bleed into 78-2 (dead-export sweep) or
78-3 (heartbeat/GPU observability). Do not delete the post surface — WIRE branch
is final.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Wiring story — must prove `apply_post`/`required_render_size` are reached from production `render()`, not merely that they work in isolation (the existing `test_post_processor.py` already covers isolation).

**Test Files:**
- `sidequest-daemon/tests/test_camera_post_wiring.py` — new RED suite (6 tests), distinct from the isolated-unit `test_post_processor.py`.

**Tests Written:** 6 tests covering AC2 (the WIRE branch; AC1 resolved at setup, AC3/delete branch closed).
**Status:** RED — 5 failing, 1 no-op guard passing. Verified via testing-runner (`78-1-tea-red`): `5 failed, 1 passed`.

**Pinned contract (what GREEN must satisfy):**
1. `ComposedPrompt` gains `post: PostDirective | None`, populated by `compose()` from the resolved camera spec's `.post` (the `_resolve_direction_camera` seam reads `spec.prompt` today; it must also surface `spec.post`).
2. `media/daemon.py` compose seam copies `composed.post` → `params["post"]` (see Delivery Finding — the one untested middle link).
3. `ZImageMLXWorker.render` reads `params["post"]` (JSON dict form: `{kind,mode,percent,degrees}` or absent/None), validates it via `PostDirective`, calls `required_render_size((tier_w,tier_h), directive)` to size generation, and `apply_post(image, directive)` **before** `image.save()` (line 517) and the R2 upload. Note: the result-dict `width`/`height` already equal the final (post-cropped) target size, so they need no change for a crop.

**Test → behavior map:**
| Test | Proves | Today |
|------|--------|-------|
| `test_render_generates_at_required_source_size_for_crop` | `required_render_size` wired (generate at 4096² for 1024² target ÷0.25) | FAIL (gen 1024²) |
| `test_render_crops_generated_image_after_generate` | `apply_post` reached (saved = 25% of generated) | FAIL (saved = generated) |
| `test_render_rejects_invalid_post_directive_loudly` | boundary validation, No Silent Fallback | FAIL (no raise) |
| `test_compose_carries_camera_post_directive` | `ComposedPrompt.post` populated from spec | FAIL (AttributeError) |
| `test_compose_no_post_when_camera_has_no_directive` | carry is opt-in, not fabricated | FAIL (AttributeError) |
| `test_render_without_post_directive_renders_unchanged` | no-op edge guard | PASS |

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|---------------------------|---------|--------|
| #1 Silent exception swallowing / No Silent Fallback | `test_render_rejects_invalid_post_directive_loudly` | failing |
| #11 Input validation at boundaries (params["post"] is socket input) | `test_render_rejects_invalid_post_directive_loudly` | failing |
| #6 Test quality (meaningful assertions, no vacuous checks) | self-check — all 6 tests assert concrete sizes/values, none use `assert True`/bare truthy | pass (self-audit) |

**Rules checked:** 3 of 13 lang-review rules are applicable to this change (the rest — async, deserialization, resource leaks, deps, path handling — are not triggered; the suite uses `with Image.open(...)` context managers per #7).
**Self-check:** 0 vacuous tests found. Every test asserts a concrete dimension/value with an explanatory message; the size-faithful stub model is what makes wired/unwired distinguishable (a naive fixed-size stub would let the crop assertions pass vacuously).

**Handoff:** To Dev (Ponder Stibbons) for GREEN implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Branch:** `feat/78-1-wire-or-delete-daemon-apply-post` (daemon, pushed — commit `be82cc9`)

**Files Changed:**
- `sidequest_daemon/media/recipes.py` — moved `PostDirective` here (cycle-break) + added `ComposedPrompt.post: PostDirective | None`.
- `sidequest_daemon/media/camera_specs.py` — re-export `PostDirective` from `recipes` (backward-compat) + `__all__`.
- `sidequest_daemon/media/prompt_composer.py` — `compose()` sets `post=self._resolve_post_directive(target)`; new `_resolve_post_directive` mirrors `_resolve_direction_camera`'s preset resolution and returns the spec's `.post`.
- `sidequest_daemon/media/daemon.py` — compose seam forwards `composed.post` → `params["post"]` (JSON dict / None).
- `sidequest_daemon/media/workers/zimage_mlx_worker.py` — `render()` validates `params["post"]` (loud on malformed), generates at `required_render_size`, applies `apply_post` before save/upload; OTEL `render.post_applied` / `post_kind` / `source_width` / `source_height`.

**Tests:** 6/6 new wiring tests GREEN; full daemon suite **371 passed, 0 failed** (`78-1-dev-green-2`). The one regression an interim change caused (`test_render_returns_expected_result_shape`) was caught and fixed by reverting result dims to `tier_cfg` — NOT shipped.

**Wiring proof (end-to-end, all in-daemon):** composer resolves `spec.post` → `ComposedPrompt.post` → daemon copies to `params["post"]` → `render()` validates, sizes generation up, and `apply_post` crops before save. The live `extreme_closeup_leone` (crop/center/0.25) now renders cropped instead of silently dropped. `ruff check` (gated `daemon-lint`) passes; my added lines are `ruff format`-clean (repo-wide format drift left untouched — see Delivery Finding).

**Handoff:** To next phase (spec-check / Architect — Leonard of Quirm).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

**AC-by-AC verification (against the committed diff `develop...HEAD`):**
- **AC1** (determine if any in-use CameraSpec sets `post:`) — satisfied pre-red: `extreme_closeup_leone` (crop/center/0.25) is live in `cameras.yaml`; WIRE branch correctly chosen. Evidence captured in Delivery Findings.
- **AC2** (wired: `render` calls `required_render_size` + `apply_post`; integration test asserts the transform) — **fully met.** `render()` computes `gen_width, gen_height = required_render_size((tier_cfg.width, tier_cfg.height), post_directive)`, passes those to `generate_image`, and calls `apply_post(image, post_directive)` before `image.save()` / R2 upload. Two integration tests drive the real `render()` path and assert (a) generation at the oversized source size and (b) the saved image is the cropped result — they cannot pass without both functions reached. Verified GREEN (6/6; full suite 371 passed).
- **AC3** (delete branch) — correctly N/A; the post surface is preserved.

**Architectural notes (no drift, recorded for traceability):**
- The implementation honors reuse-first: it wires the pre-existing, unit-tested `apply_post`/`required_render_size` rather than reimplementing them, and `_resolve_post_directive` mirrors the existing `_resolve_direction_camera` preset-resolution pattern. No new component introduced.
- `PostDirective` relocation (camera_specs → recipes, with re-export) is the minimal, sound way to let `ComposedPrompt` carry the type without a circular import; the public import path is preserved. Logged as a minor deviation by Dev — concur, no forward impact.
- `mode: subject_center` remains advisory (center-crop only) per TEA's Question finding — this is a deferred capability, not drift from 78-1's spec (which only requires the crop wiring; `extreme_closeup_leone` uses `mode: center`). No new deviation; appropriate for a future story if a `subject_center` spec ever ships.
- The daemon compose-seam middle link (`params["post"] = composed.post.model_dump() if … else None`) is present and covered transitively by the bracketing tests; Reviewer eyeball recommended per the existing finding.

**Decision:** Proceed to review (via TEA verify). No hand-back to Dev required.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (full daemon suite 371 passed, 0 failed after simplify)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (the changed `.py` files, diff `develop...HEAD`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 high + 1 medium | High: `_resolve_direction_camera` & `_resolve_post_directive` duplicated the camera-preset resolution chain. Medium: optional-model validation helper — self-dismissed ("only used once, keep local"). |
| simplify-quality | clean | No naming/dead-code/architecture issues; confirmed cycle-break + wiring + OTEL + error handling all sound. |
| simplify-efficiency | clean | No over-engineering; implementation follows established patterns. |

**Applied:** 1 high-confidence fix — extracted `_resolve_camera_preset(target) -> CameraPreset | None` as the single source of truth for preset resolution; both callers delegate to it, each keeping its divergent null handling (`_resolve_direction_camera` asserts a preset; `_resolve_post_directive` tolerates `None`). Committed `cecf272`.
**Flagged for Review:** 0 medium-confidence findings (the one medium was self-dismissed as premature — only one consumer today).
**Noted:** the reuse agent's second "finding" was a restatement of the first (same duplication, viewed from the post side) — addressed by the same extraction.
**Reverted:** 0.

**Overall:** simplify: applied 1 fix

**Regression detection:** full daemon suite re-run after the refactor → 371 passed, 0 failed (`78-1-tea-verify`). `ruff check` clean; refactored lines `ruff format`-clean (pre-existing repo-wide format drift left untouched per the Dev finding). The post-refactor signature collapse was whitespace-only.

**Quality Checks:** All passing.
**Handoff:** To Reviewer (Granny Weatherwax) for code review.

### TEA (test verification)
- No additional upstream findings during test verification. (The simplify duplication was self-introduced and resolved in-phase; the daemon-seam middle-link and ruff-format-drift findings from earlier phases stand.)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; 371 passed/0 failed; lint clean; tree clean; branch pushed | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled returned, 8 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 confirmed blocking, 0 dismissed, 3 LOW noted (all pre-existing/documented). Disabled subagents → I performed their domains (edge, silent-failure, test-quality, type, rule) manually below.

## Reviewer Assessment

**Verdict:** APPROVED

8 of 9 specialists are disabled via settings, so I carried edge/silent-failure/test/type/rule analysis myself against the diff and the python lang-review checklist.

**Observations (≥5):**
- `[VERIFIED]` **Boundary validation is loud** — `zimage_mlx_worker.py:439-444`: `PostDirective.model_validate(params["post"])` validates external socket input; pydantic `ValidationError` (a `ValueError` subclass) propagates through render's `try/except` (records span error + re-raises). Malformed `kind`, empty `{}` (missing required `kind`), and non-dict all fail loud. Complies with lang-review #1 (no silent swallow) and #11 (input validation at boundaries). Covered by `test_render_rejects_invalid_post_directive_loudly`.
- `[VERIFIED]` **End-to-end wiring, no half-wire** — composer `_resolve_post_directive` (prompt_composer.py:501-511) → `ComposedPrompt.post` (recipes.py:199) → daemon seam `params["post"] = composed.post.model_dump() if … else None` (daemon.py:737-741) → `render()` consumes/validates/applies (worker.py:439-444, 536-537, 547). Both ends behaviorally tested; the middle link is present and reviewed. Complies with daemon CLAUDE.md "Verify Wiring, Not Just Existence".
- `[VERIFIED]` **No circular import** — `PostDirective` defined in `recipes.py:174`, re-exported from `camera_specs.py:9` (which already imported `CameraPreset` from recipes); no reverse edge added. `__all__` set on camera_specs (lang-review #10 hygiene). Full suite imports clean (371 passed) — empirical proof, not just inspection.
- `[VERIFIED]` **OTEL observability for the wired subsystem** — worker.py:480-489 emits `render.post_applied`, `render.post_kind`, `render.source_width/height`. Satisfies the project OTEL principle (a real subsystem decision — did post fire? — is now visible to the GM panel). render.width/height correctly remain the final target dims.
- `[VERIFIED]` **`params["post"]` has exactly one production writer** — grep confirms no other code path sets it; sole source is the daemon compose block. Consistent with siblings (`positive_prompt`/`clip_prompt`/`seed` are also set only there). Since the composer is daemon-only, a caller that bypasses compose (sends a raw `positive_prompt`) also resolves no camera, so there is no post to drop — verified consistent, not a wiring gap.
- `[VERIFIED]` **Test suite proves wiring, not just isolation** — the size-faithful stub model makes "generated at the oversized source" and "saved == 25% of generated" independently falsifiable; these cannot pass on the unwired code (confirmed RED→GREEN). The no-op guard (`test_render_without_post_directive_renders_unchanged`) protects ordinary renders. No vacuous assertions (lang-review #6).
- `[LOW]` **`assert preset is not None` stripped under `python -O`** — `prompt_composer.py:489`. **Pre-existing** (develop:482 had `assert target.camera is not None`); the refactor relocated it unchanged. Only reachable if a `{camera}` recipe gets a target with `camera=None`, which composer callers prevent. Not introduced by 78-1; out of scope to harden here.
- `[LOW]` **`mode: subject_center` silently center-crops** — `apply_post` ignores `mode` (pre-existing). No live spec uses `subject_center` (`extreme_closeup_leone` uses `center`). Documented by TEA. Deferred to a future story if a `subject_center` spec ever ships.
- `[LOW]` **Result dims = `tier_cfg`, approximate for a future `rotate`** — for a rotate directive the inscribed output may differ from `tier_cfg` by a pixel or two; exact for crop (the only live case). Documented Dev deviation; no live rotate spec.

**### Rule Compliance** (python lang-review checklist, applied to every changed symbol):
- #1 Silent exceptions — PASS: no bare/swallowing except added; the new boundary raises loudly.
- #2 Mutable defaults — PASS: `post: PostDirective | None = None` (immutable default); no list/dict defaults added.
- #3 Type annotations at boundaries — PASS: `_resolve_camera_preset`, `_resolve_post_directive` fully annotated; `ComposedPrompt.post` typed; `post_directive: PostDirective | None` annotated.
- #6 Test quality — PASS: 6 tests, concrete assertions with messages, no vacuous checks, no unexplained skips.
- #7 Resource leaks — PASS: tests use `with Image.open(...)`; production `open(image_path, "rb")` path is pre-existing and uses `with`.
- #10 Import hygiene — PASS: explicit imports, no star imports, `__all__` added, no new circular edge.
- #11 Input validation — PASS: socket `params["post"]` validated via pydantic at the render boundary.
- #4/#5/#8/#9/#12 — N/A (no new logging-error paths, no path handling, no deserialization of untrusted bytes beyond pydantic, no async changes, no dependency changes).

**Data flow traced:** external `params["post"]` (JSON dict) → `PostDirective.model_validate` (validated, loud on bad input) → `required_render_size((tier_w,tier_h), directive)` → `generate_image(width=gen_w, …)` → `apply_post(image, directive)` → `image.save` → R2 upload. Safe: validated at entry, no unchecked path.

### Devil's Advocate

Suppose this code is broken. Where would it bite? First, the `-O` stripping of `assert preset is not None`: under `python -O`, a `{camera}` recipe with a `None` target camera would sail past the assert into `self._cameras.get(None)` — a dict miss. But this predates 78-1 and the composer's callers (illustration always supplies a camera; portrait/poi use fixed presets) never pass `None`; the refactor preserved exact behavior, so 78-1 introduces no new exposure. Second, a malicious/confused caller could send `params["post"] = {"kind":"crop","percent":-1}`: `required_render_size` raises `ValueError("crop percent must be > 0")` — loud, caught, surfaced as a render error. Good. What about `{"kind":"crop"}` with no percent? `percent or 1.0` → 1.0 → no upsize, `apply_post` crops at 100% → identity. Harmless no-op, not a crash. What about a *huge* crop inverse — `percent: 0.01` would demand a 100×-per-axis source (e.g. 102400²), blowing GPU memory? That's a real DoS-via-config vector, but it requires authoring a malicious camera spec in `cameras.yaml` (a trusted, in-repo file the daemon owns) — not external player input. The live spec is 0.25 (4× linear), well within budget. A confused author could foot-gun, but that's a content-authoring concern, not a runtime injection. Third, the stressed-filesystem angle: `apply_post` returns a new `Image`; `image.save` already handled disk errors pre-78-1 and still does. Fourth, does the post survive the token-eviction ladder? No — `post` is resolved from the camera spec independently of the layer budget (`_resolve_post_directive` doesn't touch `layers`), so even if the DIRECTION_CAMERA *prompt* layer is evicted, the post directive still rides on `ComposedPrompt.post`. Verified clean. Nothing here rises above LOW.

**Pattern observed:** reuse-first wiring — `_resolve_post_directive` mirrors and now shares `_resolve_camera_preset` with `_resolve_direction_camera`; `apply_post`/`required_render_size` reused as-is (prompt_composer.py:481-511, worker.py:439-547).
**Error handling:** loud validation + propagation at worker.py:439-444; no silent fallback.
**Handoff:** To SM for finish-story.

## Design Deviations

### TEA (test design)
- **Carry form pinned to a JSON dict, not the PostDirective object**
  - Spec source: context-story-78-1.md, "Technical Guardrails / WIRE branch"
  - Spec text: "surface `spec.post` on `ComposedPrompt` (add a `post: PostDirective | None` field) so `compose_prompt_for(cue)` carries it to `render`"
  - Implementation: the render-end test passes `params["post"]` as a JSON-style dict (`{"kind","mode","percent"}`), not a `PostDirective` instance, and expects `render()` to validate it.
  - Rationale: `params` is fundamentally the JSON socket surface — the other composed fields the daemon copies into params (`positive_prompt:str`, `seed:int`) are JSON scalars. Keeping `post` a dict there is consistent and forces boundary validation (No Silent Fallbacks). Dev may pass the object internally so long as `render()` validates external dict input; the invalid-directive test pins the validation.
  - Severity: minor
  - Forward impact: Dev must `PostDirective.model_validate(params["post"])` in `render()` rather than assume a live object; the daemon seam should `model_dump()` when copying.
- **Middle link (daemon.py compose→params copy) covered by bracketing, not a direct test**
  - Spec source: SideQuest CLAUDE.md, "Every Test Suite Needs a Wiring Test" / "Verify Wiring, Not Just Existence"
  - Spec text: "at least one integration test that verifies the component is wired ... reachable from production code paths"
  - Implementation: the composer end and render end each have behavioral tests; the one-line inline copy in the async `_handle_client` handler is asserted only transitively (both ends green ⇒ the copy is the remaining link).
  - Rationale: the copy lives in an async socket handler with no extracted seam; a socket-harness test is disproportionate for a 2pt story. Logged as a non-blocking Delivery Finding recommending extraction so a future test can cover it directly.
  - Severity: minor
  - Forward impact: Reviewer must eyeball the `params["post"] = composed.post...` line in `media/daemon.py`; if absent, the feature is half-wired despite both ends being green.

### Dev (implementation)
- **PostDirective relocated from camera_specs.py to recipes.py (with re-export)**
  - Spec source: context-story-78-1.md, "Technical Guardrails / WIRE branch"
  - Spec text: "surface `spec.post` on `ComposedPrompt` (add a `post: PostDirective | None` field)"
  - Implementation: To add `ComposedPrompt.post` (in recipes.py) without a circular import (camera_specs.py imports CameraPreset from recipes.py), I moved the `PostDirective` class definition into recipes.py and re-exported it from camera_specs.py (`from ...recipes import PostDirective`, plus `__all__`). All three existing importers (`post_processor.py`, both test files) keep their `from ...camera_specs import PostDirective` unchanged.
  - Rationale: recipes.py has zero dependencies on camera_specs.py (one-directional), and PostDirective is a standalone pydantic model with no camera_specs deps — so moving it is the minimal change that dissolves the cycle. The alternative (forward-ref + model_rebuild) is more complex for no benefit.
  - Severity: minor
  - Forward impact: none — the public import path (`camera_specs.PostDirective`) is preserved via re-export; `recipes.PostDirective` is now also valid.
- **Result-dict width/height kept as tier_cfg, not the post-cropped image size**
  - Spec source: TEA Assessment, "Pinned contract" item 3 ("the result-dict width/height already equal the final target size, so they need no change")
  - Spec text: "result-dict `width`/`height` already equal the final (post-cropped) target size"
  - Implementation: I briefly changed the result dims to `image.width/height` (truthful to the saved artifact) but reverted to `tier_cfg.width/height` after it regressed `test_render_returns_expected_result_shape` (whose fake model returns a fixed 64×64 image ignoring the requested size). In production the real model returns the requested size, so `image.size == tier_cfg` for crop and no-post cases — the two are equivalent.
  - Rationale: minimalism — no 78-1 test requires `image.size`; reverting passes all tests (mine + the existing one) and is production-equivalent. Churning the existing test for a production-equivalent niceties is unjustified scope.
  - Severity: minor
  - Forward impact: a future `rotate` directive's inscribed output may differ from `tier_cfg` by a pixel or two; no live rotate spec exists today. If exact post-rotate dims ever matter, report `image.size` and update the fixed-size fake in `test_render_returns_expected_result_shape` to be size-faithful.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Reviewer (audit)
- **TEA — carry form pinned to a JSON dict** → ✓ ACCEPTED by Reviewer: JSON-dict carry is consistent with the sibling composed fields and forces boundary validation; `render()` validates via `PostDirective.model_validate`, and the daemon seam serializes with `model_dump()`. Sound.
- **TEA — middle link covered by bracketing, not a direct test** → ✓ ACCEPTED by Reviewer: the one-line daemon seam (`params["post"] = composed.post.model_dump() if … else None`, daemon.py:737-741) is present and correct; I eyeballed it per the note. A socket-handler test is disproportionate for a 2pt story; bracketing + eyeball is adequate.
- **Dev — PostDirective relocated to recipes.py with re-export** → ✓ ACCEPTED by Reviewer: minimal, correct cycle-break; `recipes` has no reverse dependency on `camera_specs`, the public import path is preserved, and the full suite imports clean (371 passed). No forward impact.
- **Dev — result dims kept as tier_cfg, not image.size** → ✓ ACCEPTED by Reviewer: production-equivalent for crop and no-post (the only live cases); reverting avoided churning an existing fixed-fake test. The rotate-approximation caveat is documented and has no live consumer.
- No undocumented deviations found — the diff matches the logged deviations and the spec.

### Architect (reconcile)
- **Verify-phase extraction of `_resolve_camera_preset` (abstraction not in the original spec)**
  - Spec source: context-story-78-1.md, "Technical Guardrails / WIRE branch"
  - Spec text: "The directive is resolved in `PromptComposer._resolve_direction_camera` (it already calls `self._cameras.get(preset)` and reads `spec.prompt`). The natural seam is to surface `spec.post` on `ComposedPrompt`."
  - Implementation: the spec implied adding `_resolve_post_directive` alongside the existing `_resolve_direction_camera`; during the verify phase a `simplify-reuse` finding (high confidence) prompted extracting the shared preset-resolution chain into a new third method, `_resolve_camera_preset(target) -> CameraPreset | None`, which both callers now delegate to (`prompt_composer.py:481-511`).
  - Rationale: removes the duplicated recipe-lookup / `{camera}`-conditional / `CameraPreset` construction that `_resolve_post_directive` would otherwise copy from `_resolve_direction_camera`; each caller retains its divergent null handling (direction asserts a preset, post tolerates `None`). Behavior-preserving; full daemon suite green (371) after the extraction.
  - Severity: trivial
  - Forward impact: none — internal refactor of `PromptComposer`; no public API or contract change.
- **AC3 (delete branch) correctly DESCOPED, not deferred** — AC2 ("if wired") and AC3 ("if deleted") are mutually exclusive conditionals gated by AC1's investigation. AC1 found a live `post:` spec (`extreme_closeup_leone`), selecting WIRE, so AC3 is moot by design — not an open deferral. No AC accountability gap.
- No further missed deviations. The four prior entries (TEA ×2, Dev ×2) are accurate, each cites a real spec source with quoted text, and the implementation descriptions match the committed diff (`develop...HEAD`).