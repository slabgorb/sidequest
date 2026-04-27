---
story_id: "43-2"
jira_key: null
epic: "43"
workflow: "trivial"
---
# Story 43-2: Remove LoRA wiring from PromptComposer clip-prompt fork and daemon Flux1 model construction — Z-Image text-prompt path only

## Story Details
- **ID:** 43-2
- **Jira Key:** None (sprint-only tracking)
- **Workflow:** trivial
- **Epic:** 43 — Dead Code Cleanup
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-27T16:49:32Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T12:40:00Z | 2026-04-27T16:41:29Z | 4h 1m |
| implement | 2026-04-27T16:41:29Z | 2026-04-27T16:45:03Z | 3m 34s |
| review | 2026-04-27T16:45:03Z | 2026-04-27T16:49:32Z | 4m 29s |
| finish | 2026-04-27T16:49:32Z | - | - |

## Scope
Strip LoRA wiring from two locations:

1. **PromptComposer clip-prompt fork** (sidequest-server)
   - Remove `lora_path` and `lora_scale` parameter handling
   - Delete the `lora_trigger` vs `positive_suffix` fork (single composition flow only)
   - Keep Z-Image text-prompt path as the only composition path

2. **Daemon Flux1 model construction** (sidequest-daemon)
   - Remove LoRA-related logic from model initialization
   - Verify Flux1 loads without LoRA parameters

**Context:** ADRs 032/083/084 superseded by ADR-070 (Z-Image Turbo) on 2026-04-24. Story 43-1 (VisualStyle schema removal) merged 2026-04-27.

**Wiring Test:** Render succeeds on a genre with no LoRA fields present.

## Sm Assessment

Trivial workflow. Companion to 43-1 (merged). Scope is bounded grep+delete in two repos: PromptComposer clip-prompt fork in server, Flux1 LoRA wiring in daemon. ADR-070 already deprecated the Flux1 LoRA pipeline; the daemon's `zimage_mlx_worker.py:309–313` already explicitly rejects LoRA render params. Risk is low — the dead code is confirmed dead (Story 43-1 wiring test verified server side). Hand to Dev for implement.

## Dev Assessment

**Phase:** finish
**Status:** Complete — 2 commits, all tests pass.

**Implementation:**
- `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py`: dropped the LoRA-rejection block (lines 306–314 of pre-image, 9 lines). Story 43-1's wiring test confirms no server caller sends `lora_paths` / `lora_scales`, so the defensive guard was dead.
- `sidequest-daemon/tests/test_zimage_mlx_worker.py`: deleted `test_render_rejects_lora_params` (the test exercising the removed block).
- **Boy-scout**: `sidequest-server/sidequest/genre/models/pack.py:91–100` — scrubbed the stale `lora_triggers` mention from `PortraitManifestEntry` docstring (TEA flagged as a follow-up during 43-1).

**Scope clarifications:**
- **PromptComposer side (server)**: No code changes needed. `grep -rn "lora" sidequest/agents/prompt_framework/` returns zero matches. The "clip-prompt fork" the story description names doesn't exist in current code; either it never existed in the Python port or it was removed earlier. Story 43-1's wiring test (`test_no_lora_attribute_access_in_production_code`) already pins this.
- **Daemon Flux1 model construction**: Doesn't exist. The daemon uses Z-Image (mflux ZImage) per ADR-070; the only "Flux" references in the daemon are string identifiers for backend dispatch (`"flux"` warmup target) and historical comments. No actual Flux1 model construction code remains.
- **`mlx_lm.lora` import in `training/trainer.py:41`**: Out of scope. That's LM (Qwen) fine-tuning per ADR-073 Phase 3, not Flux image LoRA. Different pipeline entirely.

**Test verification:**
- `uv run pytest tests/test_zimage_mlx_worker.py -v` → 9 passed (down from 10 — the rejection test is gone; happy-path render test confirms wiring).
- `uv run pytest` (full daemon suite) → 224 passed, 2 deprecation warnings.
- `uv run pytest tests/genre/test_models/` (server, after pack.py docstring change) → 154 passed.

**Wiring proof:** `test_render_returns_expected_result_shape` (unchanged) sends `{tier, positive_prompt, negative_prompt, seed}` and asserts a real PIL image + correct dimensions returned. That's the "render succeeds on a genre with no lora fields present" wiring test the story specifies.

**Branches:**
- `sidequest-daemon`: `feat/43-2-remove-lora-wiring-promptcomposer-flux1` (1 commit, +0/−26 lines).
- `sidequest-server`: `feat/43-2-remove-lora-wiring-promptcomposer-flux1` (1 commit, +5/−5 lines docstring).

**Handoff:** To Reviewer.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 1 pre-existing test failure (unchanged from develop) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | clean | 0 | N/A |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (1 medium, 1 high-confidence) | confirmed 1 (fixed), dismissed 1 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 (high-confidence: bare-dict type, vacuous test, silent-fallback docstring) | confirmed 1 (fixed), deferred 2 (pre-existing) |

**All received:** Yes (4 active subagents, 5 skipped per settings)
**Total findings:** 1 confirmed and fixed, 1 dismissed, 3 deferred (pre-existing or out-of-scope)

### Confirmed and fixed during review
- `[DOC] [RULE]` `pack.py` docstring formerly read "Story 43-4 will scrub the legacy `lora_triggers` blocks; until then they also drop in here as opaque extras" — both rule-checker §13 and comment-analyzer §1 flagged this as documenting/normalizing a silent-ignore pattern with a deferred-cleanup note. **Fixed in amended commit:** removed the `lora_triggers` mention entirely from the docstring; restored the original "The Rust loader drops them silently; we match that rather than failing the whole pack load" wording. The example list now contains only legitimate flavor fields (dress_1878, register, flux_prompt, negative_additions, references).

### Dismissed (with rationale)
- `[DOC]` Worker module docstring "No LoRA support" should explicitly say "silently ignored" (comment-analyzer §2) — DISMISSED. The docstring is *still accurate*: no LoRA weights are loaded, no LoRA logic executes. The behavioral contract change (loud reject → no-op on unused dict keys) doesn't make the docstring lie. Adding "silently ignored" verbiage would invent a policy where there is none — the worker simply doesn't process LoRA params, period. The diff is honest deletion-only.

### Deferred (pre-existing, out of scope)
- `[TYPE]` `render(params: dict) -> dict` bare unparameterized dict (rule-checker §3) — pre-existing on develop, not in 43-2's diff hunk. Worth a hygiene story; not introduced by this work.
- `[TEST]` `test_tier_configs_match_render_tier_enum` contains `assert 'tactical_sketch' not in worker.TIER_CONFIGS` vacuous negative assertion (rule-checker §6) — pre-existing test, not in 43-2's diff. Worth fixing in a future hygiene pass.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** any caller → `worker.render({tier, positive_prompt, negative_prompt, seed, ...})` → `_compose_prompt(params)` reads only `positive_prompt | prompt | subject | mood | location | tags`. No LoRA keys are read anywhere in the worker. Story 43-1's wiring test (`test_no_lora_attribute_access_in_production_code`) verified server has no `.lora*` access; the daemon's only LoRA reference (the rejection block) is removed by this diff. Net: no LoRA code path remains in the image pipeline.

**Pattern observed:** Surgical deletion (10 lines from worker, 16 lines from test). The deleted defensive guard was paired 1:1 with its test; both go together. The boy-scouted server docstring (now amended) cleanly removes a stale field name without normalizing dead-YAML acceptance.

**Error handling:** N/A — pure deletion. The remaining `tier_name not in TIER_CONFIGS` check still fails loudly on bad input. The tests verify happy path + unknown-tier rejection.

### Findings table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| `[LOW] [TYPE] [RULE]` | `render(params: dict) -> dict` bare unparameterized dict — pre-existing, not introduced by 43-2. | `sidequest_daemon/media/workers/zimage_mlx_worker.py:297` | Out of scope; future hygiene story. |
| `[LOW] [TEST] [RULE]` | `assert 'tactical_sketch' not in worker.TIER_CONFIGS` vacuous negative — pre-existing, not in diff. | `tests/test_zimage_mlx_worker.py:32` | Out of scope; future hygiene story. |
| `[NOTE] [DOC]` | Worker module docstring "No LoRA support" considered for "silently ignored" expansion — dismissed (see "Dismissed" rationale above). | `sidequest_daemon/media/workers/zimage_mlx_worker.py:1–6` | None — docstring is accurate as-is. |

No Critical or High severity findings. Both LOW items are pre-existing, not introduced by 43-2's deletion.

### Rule Compliance

Rule-checker checked 18 rules across 47 instances. 1 violation introduced by this diff (the docstring) — fixed in-flight. 2 violations pre-existing on develop (bare dict type, vacuous test) — out of scope. All 5 CLAUDE.md additional rules pass (the LoRA guard removal is justified by 43-1's wiring proof; `test_render_returns_expected_result_shape` is the wiring test for the happy path).

### Devil's Advocate

The biggest argument against this diff is the silent-fallback concern: removing the runtime guard means a future caller who passes `lora_paths=[...]` will get a successful render with their LoRA silently ignored, possibly believing it was applied. Counter: (1) Story 43-1's wiring test pins server-side cleanliness — no caller exists to silently mislead; (2) the worker's `_compose_prompt` doesn't read any LoRA keys, so the "silent ignore" is really "unused dict key" rather than "silent fallback to default behavior"; (3) the daemon's renderer interface is internal to the SideQuest stack, not a public API where surprise compatibility matters; (4) restoring the guard would re-introduce dead defensive code that this entire epic is designed to remove. The honest deletion is correct. Second argument: the test surface lost a negative test, leaving only happy-path coverage. Counter: there's nothing left to test — the rejected behavior no longer exists. The remaining test surface (8 tests) covers the happy path, unknown tier rejection, prompt fallback paths, and turbo-preset lockdown. Coverage of the still-existent behavior is unchanged. The diff does what its name says; nothing more, nothing less.

**Handoff:** To Vizzini (SM) for finish.

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

None yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->