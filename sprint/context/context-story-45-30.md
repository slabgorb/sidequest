---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-30: Render trigger policy contract + OTEL render.trigger reasons

## Business Context

**Playtest 3 evidence (2026-04-19, Felix solo, 71 turns).** The session
produced ~6–8 scrapbook images out of 71 narration turns, and the selection
looked arbitrary — banter turns occasionally rendered, while named-NPC
introductions and resolved encounters did not. Today there is no trigger
*policy*: `_maybe_dispatch_render()` (`session_handler.py:4170`) gates
exclusively on whether the narrator chose to fill in the optional
`visual_scene` block of its game_patch. That decision is opaque, untestable,
and — per the OTEL stream — invisible to the GM panel except as the
downstream "dispatched" or "throttled" event. The image cadence is therefore
governed by Claude's improvisation, not by narrative weight.

This is exactly the failure mode CLAUDE.md flags as "Claude winging it":
the renderer either fires or doesn't, and we cannot tell from telemetry whether
the subsystem is engaged correctly. Sebastien (mechanical-first) needs to see
*why* a render fired or didn't; James (narrative-first, observed
retroactively in the Sunday `caverns_and_claudes` save as Rux) needs the image
cadence to track narrative weight, not banter density. ADR-014 (Diamonds and
Coal) is the design frame: an image is a *diamond* — expensive, scarce, and
should land on real narrative beats, not on coal.

**Load-bearing references:**

- ADR-014 (Diamonds and Coal) — render is the highest-cost diamond; firing
  policy is the rationing lever.
- ADR-031 (Game Watcher) — every subsystem decision emits an OTEL event;
  the trigger predicate is currently silent on its inputs.
- ADR-050 (Image Pacing Throttle) — already gates *frequency*, downstream of
  this story. ADR-050 explicitly notes the BeatFilter is "a separate concern
  from this ADR"; this story formalizes that concern at the server layer.
- ADR-044 (Speculative Prerendering) — orthogonal but related; trigger
  reasons defined here will become the speculation seed when 044 lands.
- CLAUDE.md OTEL Observability Principle — gate-blocking; lie-detector
  requires the trigger reason on every render decision.
- SOUL.md "Cost Scales with Drama" — policy enforces the principle.

The fix is mostly invisible to players in shape (renders still appear when
appropriate) but visible in *cadence* and *coverage*: the right beats now
land, banter no longer steals a render slot, and the GM panel can audit
every decision with `reason=`.

## Technical Guardrails

### Outermost reachable layer (wire-first seam)

The wire-first gate requires the test to drive the actual render-decision
seam, **not** a unit test on a new predicate. Two seams must be hit:

1. **Trigger predicate seam** — `_maybe_dispatch_render()` in
   `sidequest/server/session_handler.py:4170–4290`. The predicate today is the
   single check at line 4192 (`visual is None or not visual.subject.strip()`).
   That branch is the line whose semantics this story replaces: it must be
   driven by an explicit policy classifier, fed by signals already on
   `NarrationTurnResult` (`sidequest/agents/orchestrator.py:240–284`).
2. **UI indicator seam** — the scrapbook render path on the server emits
   `SCRAPBOOK_ENTRY` (`emitters.py:352–478`) and the UI consumes it through
   `ImageBusProvider` (`sidequest-ui/src/providers/ImageBusProvider.tsx`,
   pass-2 metadata-only branch at line 252) → `ScrapbookGallery`
   (`sidequest-ui/src/components/GameBoard/widgets/ScrapbookGallery.tsx:283–297`,
   the existing "no image" placeholder branch). The scrapbook payload
   (`ScrapbookEntryPayload`, `protocol/messages.py:136–147`) needs a single
   discriminator field so the UI placeholder can render *skipped-but-eligible*
   distinctly from *requested-but-failed*.

Boundary tests use the existing scrapbook + render fixtures —
`tests/server/test_render_dispatch.py`,
`tests/server/test_render_dispatch_throttle.py`, and
`tests/server/test_scrapbook_entry_wiring.py` — extended with policy
scenarios. The `_FakeClaudeClient` in `tests/server/conftest.py:195` returns
canned narration so the test controls the `visual_scene` shape and the
beat/NPC/location signals.

### Trigger contract (THE FIX)

Define an explicit enum in
`sidequest/server/render_trigger.py` (new module — single domain home,
imported by `session_handler.py` and by the OTEL telemetry layer):

```python
class RenderTriggerReason(StrEnum):
    BEAT_FIRE          = "beat_fire"        # NarrationTurnResult.beat_selections non-empty
    SCENE_CHANGE       = "scene_change"     # result.location != snapshot.location (pre-apply)
    NPC_INTRO          = "npc_intro"        # any NpcMention.is_new == True
    ENCOUNTER_RESOLVED = "resolved"         # confrontation transitions to resolved
    NONE_POLICY        = "none_policy"      # banter/aside/quiet — eligible signal absent
```

Decision pseudocode (single deterministic function, pure):

```python
def classify_trigger(
    result: NarrationTurnResult,
    snapshot_location_before: str | None,
    encounter_resolved_this_turn: bool,
) -> RenderTriggerReason: ...
```

Priority order is the enum order above; the first match wins. The call
site replaces the `visual is None or not subject.strip()` short-circuit:

- `NONE_POLICY` → no enqueue, OTEL emitted, scrapbook entry still
  persists with `render_status="skipped_policy"`.
- Any other reason → proceed into the existing throttle / daemon-availability
  / queue checks unchanged. The trigger reason is recorded on the dispatched
  `RenderQueuedMessage` and on the scrapbook payload.

**Reuse, don't reinvent.** All four positive signals already land on
`NarrationTurnResult`:
- `beat_selections: list[BeatSelection]` (`orchestrator.py:256`)
- `location: str | None` (line 252) compared to the pre-turn
  `snapshot.location` (read at the seam)
- `npcs_present: list[NpcMention]` with `is_new: bool` (line 185, 257)
- `confrontation: str | None` (line 255) — encounter-resolved is the
  transition observed in `narration_apply.py` already; thread that boolean
  through, don't re-derive.

Do NOT introduce a regex classifier on prose. The daemon already runs
`beat_filter.should_generate()` (`sidequest-daemon/sidequest_daemon/renderer/beat_filter.py`)
as a defense-in-depth keyword pass; the *server* policy is structural and
must read the structured fields the orchestrator already extracted.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md OTEL principle)

Define in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES` entries:

| Span | Attributes | Site |
|------|------------|------|
| `render.trigger` | `reason` (one of `beat_fire`/`scene_change`/`npc_intro`/`resolved`/`none_policy`), `turn_number`, `player_id`, `had_visual_scene` (bool — did the narrator emit a `visual_scene` block at all?), `subject_present` (bool) | every call to `_maybe_dispatch_render()`, BEFORE the throttle/daemon-availability checks. Fires once per turn, including on `none_policy`. |
| `render.policy_skip` | `reason="none_policy"`, `turn_number`, `eligible_signals_seen` (list — empty in the negative case), `narrator_emitted_subject` (bool — distinguishes "narrator didn't even try" from "narrator tried but no policy match") | only on the `NONE_POLICY` branch; convenience filter for the GM panel. |

`render.trigger` MUST fire on every turn that reaches `_maybe_dispatch_render()`,
not only on the dispatch path. A skipped turn is exactly the case the GM panel
needs to surface — silence is the bug. The existing `render` watcher events
(`field=render`, `op=throttle_decision`/`dispatched`/`failed`) remain unchanged
and downstream of this span.

### UI indicator (skipped-but-eligible vs requested-but-failed)

Add a `render_status` discriminator to `ScrapbookEntryPayload`
(`protocol/messages.py:136`). Three values:

- `"rendered"` — image landed; `image_url` populated as today.
- `"skipped_policy"` — server's trigger policy returned `none_policy`. UI
  renders the existing "no image" placeholder
  (`ScrapbookGallery.tsx:283–297`) with a muted *eligible-but-skipped* badge
  (e.g., a single dot glyph, no spinner — per the existing "no silent
  fallbacks" UI rule already documented at `ScrapbookGallery.tsx:284–290`).
- `"failed"` — render was eligible and dispatched but the daemon path failed
  (covers existing `daemon_unavailable`, `daemon_error`, `exception`
  branches at `session_handler.py:4665–4715`). UI renders a distinct
  failure glyph.

The discriminator is set on the scrapbook payload at emit time
(`emitters.py:440`). The eligibility decision (skipped vs failed) is the
trigger classifier's output; the failure path updates the previously-emitted
row through the existing IMAGE-arrival merge in
`ImageBusProvider.tsx:177–283`. No protocol-level retroactive update is
required — `failed` is set on initial emit when the dispatch attempt has
already failed pre-turn-end (e.g., daemon unavailable at gate); async failures
flow through the existing `render.failed` watcher event and do NOT need to
mutate the scrapbook row for this story (out of scope).

### Optional: session-level density target

The story description marks density-target enforcement as optional. Defer
unless the trigger contract lands cheaply; if implemented, it MUST be a
*soft* multiplier on `NONE_POLICY` (allow a banter turn to render if
`renders_per_turn < target`) and emit `render.trigger` with
`reason=density_floor` as a sixth enum value. Do not gate this story on it.

### Reuse, don't reinvent

- `NarrationTurnResult` already carries every signal needed; do not add new
  fields — read structured outputs the orchestrator extracts.
- `_maybe_dispatch_render()` is the single decision site; do not split it
  across dispatch handlers.
- `ScrapbookEntryPayload` already has `scene_type` — the new
  `render_status` field is a sibling discriminator, not a replacement.
- `_watcher_publish` is already imported in `session_handler.py`; emit the
  new span through the same channel as the existing render watcher events.
- The throttle (`image_pacing.py`) is downstream and unchanged — this
  story decides *whether* to consult the throttle, not *how*.

### Test files (where new tests should land)

- New: `tests/server/test_render_trigger_policy.py` — unit tests on
  `classify_trigger()` covering each enum reason, including the priority
  order (e.g., a turn with both a beat fire and an NPC intro reports
  `BEAT_FIRE`).
- Extend: `tests/server/test_render_dispatch.py` — wire-first boundary
  test that drives `_maybe_dispatch_render()` end-to-end with a canned
  `NarrationTurnResult` per reason and asserts both the dispatch decision
  and the OTEL `render.trigger` span.
- Extend: `tests/server/test_scrapbook_entry_wiring.py` — assert the new
  `render_status` discriminator lands on the scrapbook payload for each
  reason.
- New: `sidequest-ui/src/components/GameBoard/widgets/__tests__/ScrapbookGallery.render_status.test.tsx`
  — assert the skipped-but-eligible glyph and the failed glyph render
  distinctly, and neither resembles the "no scene yet" empty state.

## Scope Boundaries

**In scope:**

- `RenderTriggerReason` enum + `classify_trigger()` pure function.
- Replace the visual-scene short-circuit at `session_handler.py:4192` with
  the policy call.
- New OTEL spans `render.trigger` and `render.policy_skip`, registered in
  `SPAN_ROUTES`.
- `render_status` field on `ScrapbookEntryPayload` (`rendered` /
  `skipped_policy` / `failed`).
- UI indicators in `ScrapbookGallery` for skipped-but-eligible and
  requested-but-failed, distinct from the empty/`no image` placeholder.
- Wire-first boundary test reproducing the Felix scenario: a turn sequence
  with one of each trigger reason fires the expected OTEL span and the
  expected dispatch outcome.

**Out of scope:**

- Daemon-side compute changes (this story is server-side decision policy
  only). The daemon's `beat_filter` (`sidequest-daemon/.../beat_filter.py`)
  is unchanged — it remains as defense-in-depth.
- Image quality, post-processing, or recipe selection.
- Heartbeat, queue depth, and graceful-degradation work — those belong to
  story 45-31 and share zero code with this story.
- Density target with backpressure-aware enforcement — explicit deferral
  unless cheap. If implemented, it MUST land behind a feature flag.
- Retroactive scrapbook-row updates from async render failures (today's
  fire-and-forget pattern survives intact for this story).
- Throttle behavior — ADR-050 stays exactly as it is; trigger policy runs
  *before* the throttle.

## AC Context

1. **Each trigger reason fires the dispatch on a positive scenario.**
   - Test (boundary): drive `_maybe_dispatch_render()` four times with
     canned `NarrationTurnResult` carrying respectively (a) a non-empty
     `beat_selections`, (b) a `location` change vs. the pre-turn snapshot,
     (c) an `NpcMention(is_new=True)`, (d) an encounter-resolved boolean.
     Each MUST proceed past the policy gate; each MUST emit
     `render.trigger` with the matching `reason` attribute.
   - Distinguish the priority order: a turn carrying multiple signals
     reports the highest-priority enum value (`BEAT_FIRE` wins over
     `NPC_INTRO`).

2. **Banter turn produces no enqueue and emits `none_policy`.**
   - Negative test: drive a turn with no beat selection, no location change,
     no `is_new` NPC, no encounter resolution — even if the narrator
     emitted a `visual_scene` block. Assert: no daemon dispatch is invoked,
     `render.trigger` fires once with `reason="none_policy"`, and
     `render.policy_skip` fires with `narrator_emitted_subject` reflecting
     reality.

3. **OTEL span `render.trigger` is registered and reaches the GM panel.**
   - Test: confirm `SPAN_ROUTES["render.trigger"]` exists with
     `event_type="render.trigger"`, `component="render"`. Drive a turn and
     assert the watcher publishes the event with the expected attributes
     (`reason`, `turn_number`, `player_id`, `had_visual_scene`,
     `subject_present`).

4. **Scrapbook row carries the `render_status` discriminator.**
   - Test (extending `test_scrapbook_entry_wiring.py`): for each of the
     five reasons, the persisted + emitted `ScrapbookEntryPayload` carries
     `render_status` matching the policy outcome (`rendered` for a
     positive reason that survives downstream gates;
     `skipped_policy` for `none_policy`; `failed` when the daemon
     gate refuses synchronously).

5. **UI distinguishes skipped-but-eligible from requested-but-failed.**
   - Component test: render `ScrapbookGallery` with three entries — one
     `rendered`, one `skipped_policy`, one `failed`. Assert each renders a
     distinct DOM element / `data-testid`, none uses the empty-state
     glyph, and the visual difference is non-cosmetic (an a11y label
     reads the state aloud).

6. **Wire-first round trip from playtest reproduction.**
   - Boundary test: replay a synthetic 8-turn Felix-shaped sequence (one
     beat fire, one scene change, one NPC intro, one resolved encounter,
     four banter turns). Assert four dispatches and four `none_policy`
     spans; assert the GM panel watcher stream reflects all eight
     decisions in order.
