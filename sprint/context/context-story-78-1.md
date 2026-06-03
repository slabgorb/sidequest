---
parent: context-epic-78.md
workflow: tdd
---

# Story 78-1: Daemon camera post-processing unwired — apply_post never invoked at render (wire or delete)

## Business Context

This is a **wire-or-delete decision** on the daemon's camera post-processing
path, surfaced by the 2026-06-02 `sq-wire-it` audit (daemon was at
`origin/develop` during the scan, so the finding is current, not a stale-tree
artifact). It is the **only story in epic 78 that changes real image output** —
78-2 is a dead-export sweep, 78-3 is deferred-feature observability.

Today the pipeline *looks* wired but is silently inert:

- `CameraLoader` loads `cameras.yaml` into `CameraSpec` objects, each of which
  may carry a `post:` directive (`PostDirective` — `crop` or `rotate`).
- `apply_post` and `required_render_size`
  (`sidequest-daemon/sidequest_daemon/media/post_processor.py:12,46`) implement
  that directive correctly and are unit-tested.
- **But `apply_post`/`required_render_size` have no non-test callers.** Only
  `tests/test_post_processor.py` imports them (confirmed by grep).
- The composer (`PromptComposer._resolve_direction_camera`,
  `media/prompt_composer.py:477-491`) resolves the camera preset and reads
  `spec.prompt`, but **never reads `spec.post`**. `ComposedPrompt`
  (`media/recipes.py:174`) has no `post`/`camera` field, so the directive is
  dropped at the composer→worker boundary.
- `ZImageMLXWorker.render` (`media/workers/zimage_mlx_worker.py:400`) generates
  at `tier_cfg.width/height` and `image.save(...)` directly — it never invokes
  `required_render_size` (so it never renders the larger source a crop/rotate
  needs) and never invokes `apply_post` after generate.

Net effect: any camera preset relying on crop/rotate is **silently dropped at
render**. The image still comes back and looks plausible — this is
LLM-compensation in image form, the project's most expensive defect class
("looks-wired"). For the `extreme_closeup_leone` Leone signature shot, the
intended center-crop to a single dominant facial feature simply never happens;
the render is whatever Z-Image produced uncropped.

**Audience tie:** correct camera framing is a narrator/director-quality concern
(Keith) — a signature "extreme closeup" that silently renders as an ordinary
tight portrait is exactly the kind of quiet infidelity the wiring doctrine
exists to catch. There is no player-UI or OTEL-audience angle here beyond
"prove the transform actually fired."

## Technical Guardrails

**FIRST, at story start, re-confirm the decision branch** (develop may have
moved since 2026-06-02). The wire-vs-delete pivot is: *does any in-use
`CameraSpec` set a `post:` directive?* The single live camera spec is shipped in
the daemon, not in content:

```
sidequest-daemon/cameras.yaml          # 17 presets, the ONLY cameras.yaml in the tree
```

There is **no `cameras.yaml` in `sidequest-content`** (confirmed by
`find ... -name cameras.yaml`). The daemon's own file is loaded by
`CameraLoader.from_file(_DAEMON_ROOT / "cameras.yaml")` from the worker
(`zimage_mlx_worker.py:81`), `preview.py:36`, and validated at
`media/daemon.py:1117,1327`. **As of this writing it sets `post:` on at least
one in-use preset** — `extreme_closeup_leone` (`kind: crop, mode: center,
percent: 0.25`). So the expected branch is **WIRE**, not delete. Confirm with:

```
grep -n "post:" sidequest-daemon/cameras.yaml
```

**WIRE branch (expected):**
- Carry the camera `post:` directive through to the worker. The directive is
  resolved in `PromptComposer._resolve_direction_camera` (it already calls
  `self._cameras.get(preset)` and reads `spec.prompt`). The natural seam is to
  surface `spec.post` on `ComposedPrompt` (add a `post: PostDirective | None`
  field) so `compose_prompt_for(cue)` carries it to `render`.
- In `ZImageMLXWorker.render`, before `generate_image`, use
  `required_render_size((tier_cfg.width, tier_cfg.height), directive)` to render
  the **larger source** so the crop/rotate has pixels to consume; after
  generate, apply `apply_post(image, directive)` **before** `image.save(...)`
  and before the R2 upload (the saved/uploaded bytes must be the transformed
  image). Keep `width`/`height` in the returned result dict consistent with the
  *final* post-processed image, not the oversized source.
- ADR-070 names `ZImageMLXWorker.render` the sole runtime image worker — wire
  here, not in a second worker. ADR-127 documents the compose pipeline this
  hooks into; the post directive is a render-time transform, downstream of token
  budgeting, so it does not affect the 512-token eviction ladder.
- **Verify Wiring, Not Just Existence + Every Test Suite Needs a Wiring Test:**
  add an integration test that drives a render of a preset whose spec sets
  `post:` and asserts the transform was actually applied to the output image
  (e.g. output dimensions reflect the crop/rotate, or pixel content differs from
  the un-cropped generate). A unit test of `apply_post` in isolation does **not**
  satisfy this — the test must exercise the `render` path that proves
  `apply_post` is reached in production code.
- The model `generate_image` call is GPU/MLX-bound; the integration test should
  stub/monkeypatch the model to return a known synthetic image so the assertion
  is on the post-transform, not on real inference. The point is to prove the
  call site exists and fires, not to run Z-Image.

**DELETE branch (only if grep shows NO live spec sets `post:`):**
- Remove `apply_post` and `required_render_size`
  (`media/post_processor.py`), the `CameraSpec.post` field and `PostDirective`
  model (`media/camera_specs.py`), and any `post:` parsing — all **in one PR**
  (Delete Dead Code in the Same PR). Remove `tests/test_post_processor.py` since
  it points at deleted code.
- `daemon-test` + `daemon-lint` must stay green; no dangling import or reference
  to the removed names anywhere.

**Doctrine constraints (both branches):**
- No Silent Fallbacks: if a `post:` directive has an unknown `kind`, `apply_post`
  already raises — preserve that loud failure, don't swallow it at the new call
  site.
- No Stubbing: do not add a `post` field to `ComposedPrompt` "for later" unless
  it is read in `render` this PR.

## Scope Boundaries

**In scope:**
- The wire-or-delete of camera post-processing **only**: `apply_post`,
  `required_render_size`, `CameraSpec.post`/`PostDirective`, and the
  composer→worker carry of the directive into `ZImageMLXWorker.render`.
- If wiring: an integration test that proves the transform is applied on the
  render path.
- If deleting: removal of all four surfaces (functions, field, model, parsing)
  plus the now-orphaned unit test, in one PR.

**Out of scope:**
- 78-2 dead-export sweep (`NullRenderer`, `Renderer` ABC, `genre/models.py`
  stubs, the `dispatch_request` image-tier `NotImplementedError` trap).
- 78-3 deferred-feature observability (`start_periodic_heartbeat` liveness,
  `detect_gpu`/`GpuInfo` GPU span).
- Editing `cameras.yaml` *content* (adding/removing presets or directives) —
  this story wires the mechanism, it does not author new camera presets.
- Any server-side or UI change. This is a daemon-only story.
- R2 upload mechanics beyond ensuring the post-processed (not pre-crop) bytes
  are what gets saved/uploaded.

## AC Context

The three acceptance criteria map to the decision-then-execute shape:

1. **"Determined whether any in-use CameraSpec sets a post directive (evidence:
   grep of content camera specs)."** The implementer must run the grep at story
   start and record the result as the branch selector. Note the AC says
   "content camera specs," but the only `cameras.yaml` lives in the **daemon**
   (`sidequest-daemon/cameras.yaml`) — there is no content-tree cameras.yaml.
   Grep the daemon file. As of 2026-06-02 it sets `post:` on
   `extreme_closeup_leone`, so the expected answer is **YES → wire**. The
   evidence (the grep output) should be captured in the PR/commit so the chosen
   branch is auditable.

2. **"If wired: ZImageMLXWorker.render calls required_render_size + apply_post;
   an integration test renders a spec with post and asserts the transform
   applied."** Both calls must land in the real `render` path — `required_render_size`
   *before* generate (to size the source) and `apply_post` *after* generate
   (before save/upload). The integration test must drive the render entry point
   (not call `apply_post` directly) and assert the output reflects the
   transform. This is the wiring test the doctrine requires; an isolated
   `apply_post` unit test does not satisfy this AC.

3. **"If deleted: apply_post, required_render_size, CameraSpec.post field, and
   CameraLoader post-parsing all removed in one PR; no dangling references."**
   Only taken if AC1 finds no live `post:`. All four surfaces gone in a single
   PR, the orphaned `test_post_processor.py` removed, and `daemon-test` +
   `daemon-lint` green with zero dangling references.

**AC ambiguity to flag:** AC1 says "grep of **content** camera specs," but
camera specs live in the daemon, not content (`find` returns only
`sidequest-daemon/cameras.yaml`). The implementer should grep the daemon file
and note the AC's "content" wording as imprecise — the substantive question
("does any in-use spec set `post:`?") is unchanged. ACs 2 and 3 are mutually
exclusive branches gated by AC1; the story is "done" when the AC1-selected
branch is complete, not both.

## Assumptions

- **The decision branch is WIRE.** `sidequest-daemon/cameras.yaml` ships
  `extreme_closeup_leone` with `post: {kind: crop, mode: center, percent: 0.25}`,
  and `extreme_closeup_leone` is a real, selectable preset (a Leone signature
  shot), so a live `CameraSpec` does set `post:`. The implementer must
  re-confirm this with the grep at story start — if develop has since removed
  that preset's `post:` (or the preset itself), the branch flips to DELETE.
- The `mode: center` / `mode: subject_center` field on `PostDirective` is
  currently advisory: `apply_post`'s crop path always center-crops and ignores
  `mode`. Wiring `apply_post` as-is preserves today's behavior (center crop);
  implementing `subject_center` is **not** part of this story (would need a
  subject bounding box the daemon doesn't surface here). If the `extreme_closeup_leone`
  spec relies on `subject_center` semantics, treat that as a separate concern and
  do not silently approximate it — wire the existing center-crop behavior and
  note the gap.
- Rendering the oversized source via `required_render_size` is acceptable cost
  for the affected presets (a 0.25 crop quadruples linear dimensions). If that
  blows a GPU/MLX size budget, that is a real constraint to surface loudly, not
  a reason to skip `required_render_size` and crop a too-small image.
- `width`/`height` in the worker's returned result dict should describe the
  **final post-processed** image; downstream consumers (server/UI) treat those
  as the artifact's true dimensions.
