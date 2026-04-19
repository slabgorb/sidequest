---
story_id: "27-1"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 27-1: Strip TTSWorker and Kokoro from daemon

## Story Details
- **ID:** 27-1
- **Title:** Strip TTSWorker and Kokoro from daemon
- **Points:** 2
- **Priority:** p1
- **Workflow:** trivial
- **Type:** chore
- **Repos:** daemon (sidequest-daemon)
- **Stack Parent:** none

## Context
This is the first story in Epic 27 (MLX Image Renderer migration). As part of the daemon simplification, we're removing TTS (Kokoro/Piper) infrastructure entirely — no user demand for voice synthesis during game sessions. This is pure deletion work with no new code.

**Reference:** sprint/context/context-epic-27.md, ADR-070

## Deletion Scope

### Files to Delete
1. `sidequest_daemon/media/workers/tts_worker.py` — TTSWorker class and implementation
2. `sidequest_daemon/voice/` — Entire directory (17 files):
   - `__init__.py`
   - `kokoro.py` — Kokoro TTS integration
   - `piper.py` — Piper TTS fallback
   - `router.py` — Voice tier routing logic
   - `selector.py` — Voice model selector
   - And 12 additional supporting modules for Kokoro/Piper infrastructure

### Code Changes
1. `sidequest_daemon/media/daemon.py`:
   - Remove TTSWorker import
   - Remove TTS tier routing from WorkerPool (`MUSIC_TIERS`, `TTS_TIERS` → keep only `FLUX_TIERS`, `EMBED_TIERS`)
   - Remove `list_voices()` method from request handler (if present)

2. `pyproject.toml`:
   - Remove `piper-tts>=1.2` dependency

### Verification
After deletion:
- No imports of `tts_worker`, `voice/`, or piper-tts remain in the codebase
- Requests for TTS tiers should raise `ValueError` with "TTS tier no longer supported" message
- daemon.py WorkerPool only routes FLUX_TIERS and EMBED_TIERS

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-07T06:13:41Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-07 | — | — |

## Sm Assessment

**Story 27-1** is a pure deletion task — remove TTSWorker and all Kokoro/Piper voice infrastructure from the daemon. No new code, no new abstractions.

**Scope:** Delete `tts_worker.py`, entire `voice/` directory (17 files), TTS routing from `daemon.py`, `piper-tts` from `pyproject.toml`, and `list_voices` handler.

**Risk:** Low. Pure subtraction with clear boundaries. No cross-repo impact — the Rust API never calls TTS tiers directly.

**Routing:** Trivial workflow → Dev (implement phase). Straightforward deletion with grep verification that no TTS imports remain.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest_daemon/voice/` — Entire directory deleted (17 source files, 2,400+ LOC)
- `sidequest_daemon/media/workers/tts_worker.py` — Deleted (TTSWorker class)
- `sidequest_daemon/media/daemon.py` — Removed TTS tier routing, `list_voices` handler, TTS warmup, `_tts` worker pool fields
- `sidequest_daemon/media/pipeline_factory.py` — Removed voice pipeline (`init_voice`, `register_npcs`, voice imports, `enable_tts` param, `EffectsPresetLibrary`)
- `pyproject.toml` — Removed `piper-tts>=1.2` dependency
- `tests/voice/` — Deleted voice test directory
- `uv.lock` — Updated from dependency removal

**Tests:** 10/10 passing (GREEN)
**Branch:** feat/27-1-strip-tts-kokoro (pushed)

**Handoff:** To review phase (Westley)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 2 stale comments, CLAUDE.md outdated | confirmed 2 (stale docs), dismissed 1 (CLAUDE.md — separate chore) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 0, dismissed 3 (all pre-existing or scoped to 27-2) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 7 | confirmed 0, dismissed 7 (all pre-existing, not introduced by this PR) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 6 | confirmed 2 (stale docstring, stale pyproject description), dismissed 4 (pre-existing) |

**All received:** Yes (4 returned, 5 disabled)
**Total findings:** 2 confirmed (both LOW), 14 dismissed (pre-existing or out-of-scope), 0 deferred

### Subagent Finding Decisions

**Confirmed:**
- [RULE] daemon.py:394 stale docstring lists "tts" as valid warmup — introduced by this PR's incomplete cleanup
- [RULE] pyproject.toml:4 description still says "TTS" — introduced by this PR's incomplete cleanup

**Dismissed (pre-existing, not introduced by this diff):**
- [SILENT] AudioMixer init failure silently swallowed (pipeline_factory.py:72) — pre-existing behavior, not changed by this PR
- [SILENT] ACE-Step warm_up succeeds but render rejects — scoped to story 27-2, intentional
- [SILENT] Dead ACE-Step infrastructure misleading — scoped to story 27-2
- [TYPE] WorkerPool.render() uses bare dict — pre-existing, not changed by this PR
- [TYPE] status() stringly-typed dict — pre-existing
- [TYPE] warmup str|bool union — pre-existing
- [TYPE] RenderTier silent fallback to SCENE_ILLUSTRATION — pre-existing, line untouched
- [TYPE] music_director dead state — pre-existing
- [TYPE] AudioMixer partial-failure fallback — pre-existing
- [TYPE] Missing render exception logging — pre-existing
- [RULE] subject_extractor DEBUG logging — pre-existing, file not in diff
- [RULE] AudioMixer success logged at WARNING — pre-existing
- [RULE] No embed wiring test — pre-existing
- [RULE] No embed OTEL span — pre-existing

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Deletion completeness — grep for `sidequest_daemon\.voice|TTSWorker|kokoro|piper|TTS_TIERS|list_voices|enable_tts|VoicePresetRegistry|VoiceRouter|EffectsPresetLibrary` returns zero hits. All voice imports cleanly severed. Evidence: verified via `rg` across entire daemon codebase.
2. [VERIFIED] No silent fallbacks — unknown tiers hit `ValueError` at daemon.py:124. Per "no silent fallbacks" project rule, this is correct behavior. Evidence: daemon.py:123-124 `else: raise ValueError(...)`.
3. [VERIFIED] AudioQueue constructor — `voice_backend` is optional (defaults to `None` at audio/queue.py:24), so removing the kwarg from pipeline_factory.py:86 is safe. Evidence: `def __init__(self, *, backend: Any, mixer: Any, voice_backend: Any | None = None)`.
4. [VERIFIED] No broken imports at runtime — tests pass (10/10 GREEN), ruff reports no new errors (net -1 from develop baseline). Evidence: preflight subagent test results.
5. [VERIFIED] pyproject.toml dependency removal — `piper-tts>=1.2` correctly removed, uv.lock updated. Evidence: pyproject.toml diff line 15.
6. [LOW] Stale docstring at daemon.py:394 — `warmup can be: False, True/"all", "flux", "tts"` still lists "tts" as valid. Introduced by this PR. [RULE]
7. [LOW] Stale comment at daemon.py:406 — `# Initialize media pipelines (audio + voice) via factory` — voice removed. [DOC]
8. [LOW] pyproject.toml:4 description says "image generation, TTS, and audio playback" — TTS removed. [RULE]

### Data Flow Traced
Render request → `_handle_client` → tier routing at `pool.render()` → FLUX_TIERS check → FluxWorker. TTS tier requests now correctly hit `ValueError("Unknown tier: 'tts'")` → GENERATION_FAILED error response to client. No silent degradation.

### Wiring Check
No new wiring needed — this is pure deletion. Verified no callers of `init_voice()` or `register_npcs()` remain (grep returns zero hits).

### Error Handling
Unknown tier → ValueError → GENERATION_FAILED error response. Correct.

### Security Analysis
No new attack surface. Pure deletion reduces surface area. No new input paths.

### Rule Compliance
- **No silent fallbacks:** Compliant. Unknown tiers raise ValueError.
- **No stubbing:** Compliant. No placeholders left behind.
- **Verify wiring:** Compliant. No dangling imports.
- **OTEL:** N/A for deletion story — no new subsystem decisions to instrument.

### Devil's Advocate

What if a user has a running SideQuest session and the daemon restarts with this new code? Any in-flight TTS requests from the Rust API's `sidequest-daemon-client` crate would get `UNKNOWN_METHOD` for `list_voices` and `GENERATION_FAILED` for `tts` tier renders. The Rust side still has `TtsParams`, `TtsResult`, `synthesize()`, `list_voices()`, and `tts_stream.rs` — a full TTS client pointing at dead endpoints. During a playtest, this would manifest as silent failures in the API logs (the daemon returns errors, but does the Rust client handle them gracefully or panic?).

However: TTS was already effectively dead — "no user demand for voice synthesis during play" per ADR-070. The Rust TTS client code is dead code that was never called in production paths. The daemon's `list_voices` and TTS tier routing were vestigial. This PR makes the daemon honest about what it actually does.

The stale docstring and pyproject description are cosmetic but they're "lies in documentation" — exactly the kind of thing that wastes debugging time when someone reads the docs and expects TTS to work. These are LOW severity and don't block the PR, but they should be fixed before merge.

Could the deletion of `EffectsPresetLibrary` break audio? No — it was only used for `creature_voice_presets` loading, which fed into the TTS pipeline. The `AudioQueue` still works without `voice_backend` (it's optional). The audio mixer, backend, and queue are intact.

Could the deletion of `voice/` break genre pack loading? No — `GenrePack` may have `voice_presets` and `required_voice_models` fields in its schema, but those are data model fields in `genre/models.py` (not deleted). They'll just be unused data. Removing them would be a schema change, out of scope.

No critical or high issues found. The 3 LOW findings are stale documentation artifacts. **APPROVED.**

[EDGE] No findings — disabled via settings
[SILENT] 3 findings — all dismissed as pre-existing or scoped to 27-2
[TEST] No findings — disabled via settings
[DOC] Stale comment at daemon.py:406 confirmed LOW
[TYPE] 7 findings — all dismissed as pre-existing
[SEC] No findings — disabled via settings
[SIMPLE] No findings — disabled via settings
[RULE] 2 confirmed LOW (stale docstring daemon.py:394, stale pyproject.toml:4 description)

**Handoff:** To SM (Vizzini) for finish-story

## Delivery Findings

No upstream findings at setup phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): `EffectsPresetLibrary` from `voice.presets` was also used in `pipeline_factory.py` for creature voice effect presets. Removed along with voice infrastructure. If creature voice effects are needed in future (unlikely without TTS), they'd need reimplementation. Affects `sidequest_daemon/media/pipeline_factory.py` (creature_voice_presets loading removed). *Found by Dev during implementation.*
- No other upstream findings.

### Reviewer (code review)
- **Gap** (non-blocking): Rust `sidequest-daemon-client` crate still exports `TtsParams`, `TtsResult`, `synthesize()`, `list_voices()`, and `tts_stream.rs` — all pointing at dead daemon endpoints. Affects `sidequest-api/crates/sidequest-daemon-client/` (dead TTS client code to remove). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): daemon.py:394 docstring still lists "tts" as valid warmup target. Affects `sidequest_daemon/media/daemon.py` (update docstring). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): pyproject.toml:4 description still says "image generation, TTS, and audio playback". Affects `pyproject.toml` (update description). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): sidequest-daemon CLAUDE.md still describes TTS (Kokoro) in Architecture and "Why Python" sections. Affects `sidequest-daemon/CLAUDE.md` (update to reflect TTS removal). *Found by Reviewer during code review.*

## Impact Summary

**Upstream Effects:** 5 findings (1 Gap, 0 Conflict, 0 Question, 4 Improvement)
**Blocking:** None

- **Improvement:** `EffectsPresetLibrary` from `voice.presets` was also used in `pipeline_factory.py` for creature voice effect presets. Removed along with voice infrastructure. If creature voice effects are needed in future (unlikely without TTS), they'd need reimplementation. Affects `sidequest_daemon/media/pipeline_factory.py`.
- **Gap:** Rust `sidequest-daemon-client` crate still exports `TtsParams`, `TtsResult`, `synthesize()`, `list_voices()`, and `tts_stream.rs` — all pointing at dead daemon endpoints. Affects `sidequest-api/crates/sidequest-daemon-client/`.
- **Improvement:** daemon.py:394 docstring still lists "tts" as valid warmup target. Affects `sidequest_daemon/media/daemon.py`.
- **Improvement:** pyproject.toml:4 description still says "image generation, TTS, and audio playback". Affects `pyproject.toml`.
- **Improvement:** sidequest-daemon CLAUDE.md still describes TTS (Kokoro) in Architecture and "Why Python" sections. Affects `sidequest-daemon/CLAUDE.md`.

### Downstream Effects

Cross-module impact: 5 findings across 4 modules

- **`sidequest_daemon/media`** — 2 findings
- **`.`** — 1 finding
- **`sidequest-api/crates`** — 1 finding
- **`sidequest-daemon`** — 1 finding

### Deviation Justifications

1 deviation

- **Removed EffectsPresetLibrary and creature_voice_presets loading from pipeline_factory**
  - Rationale: These are voice infrastructure — `EffectsPresetLibrary` lives in `voice/presets.py` (deleted), `VoicePresetRegistry` in `voice/registry.py` (deleted), `VoiceRouter` in `voice/router.py` (deleted). Removing them is necessary to avoid broken imports
  - Severity: minor
  - Forward impact: none — creature voice effects were only used by TTS pipeline which is being removed

## Design Deviations

No design deviations at setup phase.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Removed EffectsPresetLibrary and creature_voice_presets loading from pipeline_factory**
  - Spec source: 27-1-session.md, Deletion Scope
  - Spec text: Session listed `voice/` directory, `tts_worker.py`, TTS routing, `piper-tts`, and `list_voices` as deletion scope
  - Implementation: Also removed `EffectsPresetLibrary` import/usage and `creature_voice_presets` loading from `pipeline_factory.py`, plus `voice_adapter` parameter and `voice_backend` passthrough to AudioQueue
  - Rationale: These are voice infrastructure — `EffectsPresetLibrary` lives in `voice/presets.py` (deleted), `VoicePresetRegistry` in `voice/registry.py` (deleted), `VoiceRouter` in `voice/router.py` (deleted). Removing them is necessary to avoid broken imports
  - Severity: minor
  - Forward impact: none — creature voice effects were only used by TTS pipeline which is being removed

### Reviewer (audit)
- **Removed EffectsPresetLibrary and creature_voice_presets** → ✓ ACCEPTED by Reviewer: Necessary to avoid broken imports since the source modules were deleted. creature_voice_presets were exclusively TTS pipeline consumers.