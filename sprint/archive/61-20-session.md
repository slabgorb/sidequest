---
story_id: "61-20"
jira_key: ""
epic: "61"
workflow: "tdd"
---
# Story 61-20: Reduce per-turn volatile-tail write volume

## Story Details
- **ID:** 61-20
- **Jira Key:** (none — personal project)
- **Workflow:** tdd
- **Stack Parent:** 61-19 (feat/61-19-stop-volatile-cache-writes)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-30T19:12:12Z
**Repos:** server
**Branch:** feat/61-20-reduce-volatile-tail-write-volume

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30T14:30:00Z | 2026-05-30T18:31:36Z | 4h 1m |
| red | 2026-05-30T18:31:36Z | 2026-05-30T18:41:38Z | 10m 2s |
| green | 2026-05-30T18:41:38Z | 2026-05-30T18:49:52Z | 8m 14s |
| spec-check | 2026-05-30T18:49:52Z | 2026-05-30T18:51:46Z | 1m 54s |
| verify | 2026-05-30T18:51:46Z | 2026-05-30T19:06:54Z | 15m 8s |
| review | 2026-05-30T19:06:54Z | 2026-05-30T19:11:03Z | 4m 9s |
| spec-reconcile | 2026-05-30T19:11:03Z | 2026-05-30T19:12:12Z | 1m 9s |
| finish | 2026-05-30T19:12:12Z | - | - |

## SM Assessment

**Story:** 61-20 — Reduce per-turn volatile-tail write volume (option b: zone-promote
session-static Valley content into the cached 1h prefix). p1, 5pts, `tdd`, server-only.

**Routing decision:** Setup complete → handing off `red` phase to TEA (Radar).

**What the next agent needs to know:**
- This is the **successor to 61-19** (done). 61-19 did the TTL-tier correction (stopped
  writing the volatile tail at 1h → moved it to 5m), which halved the *price* but not
  the *volume*. 61-19's AC1 (<2k/turn), AC2 (≤$0.05/turn), AC3 (flat at 50 turns) remain
  open. **61-20 closes them** via ADR-112/61-10 zone-promotion.
- **The move:** promote three *session-static* sections — `AVAILABLE CULTURES`, magic
  `hard_limits`, `monster_manual` — out of the volatile (5m) Valley tail into the cached
  **1h stable prefix**, so they write once and amortize. Only the ~1k per-turn delta
  stays in the 5m tail.
- **Read `sprint/context/context-story-61-20.md` AND `context-story-61-19.md`** — 61-19's
  context carries the full verified cache mechanism (markers, prefix-cache TTL semantics,
  telemetry surface) in file:line detail. Do not re-derive it.
- **Load-bearing risk for RED to pin:** the promotion is only valid if the three sections
  are *genuinely session-static*. If any can drift mid-session, promoting to 1h
  re-introduces churn. AC3 guards this; tests must assert it.
- **Named deliverables beyond the ACs:** a live-validation probe (confirmation, not the
  red gate) and a stale-comment fix at `anthropic_sdk_client.py:339-342` (do it in-PR).
- The payload builders are pure functions over `system_blocks`+`running_messages` —
  marker-placement assertions are testable offline (no live Anthropic call). RED is tractable.

documented in the 61-19 context this story stacks on; a fresh architect tandem pass would
duplicate it. spec-check (architect) is still in the tdd phase flow for the option-(b)
mechanism confirmation.

**Gate:** sm_setup_exit — session + fields + context (validates) + branch all present.
Jira explicitly skipped (personal project, no Jira).

## TEA Assessment

**Tests Required:** Yes
**Test Files:**
- `sidequest-server/tests/agents/test_61_20_session_static_promotion.py` — new file, 6 tests.

**Tests Written:** 6 tests (2 failing AC drivers + 4 guards) covering AC1/AC3/AC4 + the monster_manual boundary.
**Status:** RED confirmed (testing-runner run `61-20-tea-red`): 2 FAIL (AssertionError), 4 PASS, **0 ERROR**.

| Test | Role | RED status |
|------|------|-----------|
| `test_available_cultures_promoted_to_cached_prefix` | AC1 driver — world_context → system_blocks[0] | **FAIL** (in user msg today) |
| `test_available_cultures_absent_from_volatile_tail` | AC1 displacement guard | PASS |
| `test_magic_hard_limits_promoted_to_cached_prefix` | AC1 driver — static hard_limits → prefix | **FAIL** (absent today) |
| `test_volatile_magic_ledger_stays_out_of_cached_prefix` | AC4 split guard (forces magic_context split) | PASS |
| `test_cached_prefix_byte_stable_across_turns_with_changing_ledger` | AC3/AC4 economic proof (byte-stable prefix vs mutating ledger) | PASS |
| `test_volatile_game_state_not_promoted_to_cached_prefix` | monster_manual boundary guard | PASS |

**What the two failing drivers tell Dev to do:**
1. Promote `world_context` (AVAILABLE CULTURES): re-zone Valley→Early at `orchestrator.py` ~2076 **and** add the section name to `STABLE_SECTION_NAMES` (`prompt_framework/bucket.py`) — the exact Story 57-3 pattern.
2. SPLIT `magic_context`: promote the static header (`hard_limits`/`allowed_sources`/`world_knowledge`) to the cached prefix; keep `active_ledger_for_<actor>` in the Valley tail. The two magic tests together force this — promoting wholesale fails the byte-stability guard.
3. Story-named extras (no test — do them in-PR): the live-validation probe (absolute AC1/AC2 confirmation) and the stale-comment fix at `anthropic_sdk_client.py:339-342`.
4. **DO NOT** try to promote monster_manual — see the blocking Delivery Finding + the boundary guard.

### Rule Coverage (python lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #6 test-quality (meaningful assertions, no vacuous) | all 6 — each asserts a specific marker placement / digest equality; self-checked, none vacuous | enforced |
| No Silent Fallbacks / cache-write economics (CLAUDE.md) | `test_cached_prefix_byte_stable_across_turns_with_changing_ledger` (a 1h write on a mutating prefix is silent waste) | guard |
| No Source-Text Wiring Tests (CLAUDE.md) | all tests drive the real `Orchestrator.run_narration_turn` SDK path and inspect the captured wire payload — zero source greps | compliant |

**Rules checked:** test-quality + the two load-bearing server-CLAUDE.md rules (cache economics, no source-text wiring) are the applicable ones for a cache-zoning change. The injection/deserialization/path/async rules don't apply (no new I/O, parsing, or async surface).
**Self-check:** 0 vacuous assertions.

**Spec note:** AC2/AC3 absolute thresholds + AC5 span are deferred to / covered by existing 61-19 tests + the live probe (see Design Deviations). 61-20's net-new RED surface is the *promotion* (volume reduction) that 61-19 did not do.

**Handoff:** To Dev (Winchester) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 6/6 GREEN on the story file; 48 passed / 0 failed / 13 skipped (genre-gated) across the regression set (61-19 cache-tier, cache_ttl_prefix_and_otel byte-stability/zone, magic context_builder + 47-9 + reliquaries).
**Branch:** `feat/61-20-reduce-volatile-tail-write-volume` (pushed).

**Files Changed (server):**
- `sidequest/agents/prompt_framework/bucket.py` — added `world_context` + `magic_hard_limits` to `STABLE_SECTION_NAMES` (System bucket).
- `sidequest/magic/context_builder.py` — refactored into `_static_lines`/`_volatile_lines`; added public `build_magic_static_block` + `build_magic_volatile_block`; `build_magic_context_block` now composes both, **byte-identical** to its prior output (existing magic tests still pass).
- `sidequest/magic/__init__.py` — export the two new builders.
- `sidequest/agents/orchestrator.py` — `world_context` re-zoned Valley→**Early**; magic registration **split** into `magic_hard_limits` (Early, promoted) + `magic_context` (Valley, volatile ledger tail). `magic_output_rules` unchanged.
- `sidequest/agents/anthropic_sdk_client.py` — fixed the stale pre-61-19 comment (the volatile tail rides 5m via `_VOLATILE_CACHE_TTL`, not 1h).

**How the ACs are met:** a section rides the cached 1h prefix iff (System bucket **AND** Primacy/Early zone) — orchestrator.py:105-117. The two promotions satisfy both conditions; the magic split keeps the live ledger (`active_ledger_for_<actor>` + bar values) in Valley/User → user message (uncached), so the cached prefix stays byte-stable across turns even as magic is cast (proven by `test_cached_prefix_byte_stable_across_turns_with_changing_ledger`).

**Quality:** ruff clean, format clean on all 5 changed files. The one pyright error (`orchestrator.py:2966` `send_stream`) is **pre-existing** — outside my diff (hunks are 2070-2167), in the unrelated streaming path.

**Story-named extras:**
- Stale comment at `anthropic_sdk_client.py:339-342` — **fixed**.
- Live-validation probe — **not added as code** (see Design Deviation): the absolute AC1 `<2k`/AC2 `≤$0.05` confirmation rides the existing 61-19 `stable_prefix_write_tokens`/`tail_write_tokens` OTEL span on a live session; recommended as a 61-6-style follow-up chore.
- monster_manual — **deliberately NOT promoted** (TEA's blocking finding; needs architect reconciliation at spec-check).

**Handoff:** To Architect (Major Houlihan) for spec-check — please rule on (1) the monster_manual premise (not promotable in Python) and (2) whether the magic_working instruction/innate-example staying volatile is acceptable or should also be promoted via a guardrail reword.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (premise-level, resolved by spec-update + defer — not a code fix)
**Structural gate:** PASS (`spec_check`) — AC coverage present in Dev Assessment, implementation complete, TEA + Dev deviation subsections well-formed.
**Mismatches Found:** 3 (1 Major, 1 Minor, 1 Trivial) — none require hand-back to Dev.

- **monster_manual named as a promotion target but correctly NOT promoted** (Missing-in-code — Architectural, **Major**)
  - Spec: context-story-61-20.md scope + title list `monster_manual` among the three sections to promote into the cached prefix.
  - Code: only `world_context` and the static magic header are promoted; monster_manual is left volatile.
  - **Ruling: Option A (update spec).** The premise reflects a stale/Rust-era mental model. In the Python impl the Monster Manual is materialized into `snapshot.npcs` (gaslighting doctrine, `monster_manual_inject.py`) and reaches the prompt via the irreducibly-volatile `game_state` section — it is **not** a cacheable section and must not be promoted. The materialization is already **bounded** (`_AVAILABLE_NPC_INJECT_LIMIT=3`, `_OUT_OF_COMBAT_ENCOUNTER_LIMIT=2`) and slimmed by 61-2, so its residual presence in the 5m tail is small and intended. TEA's blocking Delivery Finding is **ratified**; the deviation log (TEA + Dev) is the binding record. AC1's `<2k` rests on the two valid promotions + the bounded snapshot, which is architecturally sound.

- **Absolute AC1 (`<2k`) / AC2 (`≤$0.05`) not verified in code** (Ambiguous-spec — Behavioral, **Minor**)
  - Spec: AC1/AC2 state absolute steady-state thresholds.
  - Code: marker-displacement is asserted (static content leaves the tail / enters the prefix); the absolute counts are not unit-asserted.
  - **Ruling: Option D (defer).** Consistent with 61-19's precedent — absolute, session-level thresholds are only honestly assertable on a live billed run. The implemented promotion is the correct *mechanism*; the existing 61-19 `stable_prefix_write_tokens`/`tail_write_tokens` span is the observability. Confirm via the named live-validation probe (61-6-style follow-up, Dev Delivery Finding). Not a blocker.

- **magic_working instruction prose + innate example left in the volatile tail** (Extra-in-code boundary — Cosmetic, **Trivial**)
  - Spec: promote "magic hard_limits".
  - Code: promoted the world-config head (incl. hard_limits); the ~250-tok static instruction/example stayed volatile.
  - **Ruling: Option C (accept) / D (defer).** The chosen boundary is correct: that prose literally references `active_ledger_for_<actor>` and promoting it would require rewording guardrail text — a content change the story explicitly forbids. The dominant static chunks are promoted. A future micro-optimization (separate static instruction section) is possible but not justified now; logged as Dev's Question finding.

- **Observation (no blocker):** `world_context` byte-stability across turns isn't directly unit-tested (the existing byte-stability gate uses a no-world_context fixture). It is session-static by construction; a future "Yes, And" culture addition mid-session would correctly re-write the prefix once. Acceptable; noted for traceability.

**Decision:** Proceed to review (TEA verify). The implementation is correct, tested (48 passed/0 failed), strictly cost-reducing, and well-scoped (157 lines / 5 files). The only drift is the monster_manual *premise*, resolved by spec-update, not code change.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (with one self-introduced regression found + fixed)

### Simplify Report
**Teammates:** reuse, quality, efficiency (all three, parallel)
**Files Analyzed:** 5 (the changed source files)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | None — the None-guards / `"\n".join` repetition is idiomatic and not extractable; dual registration blocks are intentionally parallel with different zones. |
| simplify-quality | clean | None — naming clear, no dead code (build_magic_context_block intentionally kept for byte-compat), wiring verified via captured payloads. |
| simplify-efficiency | clean | None — the function split is minimal and well-motivated; build_magic_context_block is a deliberate backward-compat shim, not dead code. |

**Overall:** simplify: clean — 0 fixes applied, 0 reverted.

### Regression found & fixed (full-suite gate did its job)
The full-suite run (`61-20-tea-verify`, both env vars set) surfaced a **real regression in a sibling test** that the scoped GREEN run missed: `tests/agents/test_60_6_stable_prefix_live_drift.py` (3 tests) **pinned the pre-61-20 invariant** that `world_context` is a volatile User-bucket field landing in the user message — it deliberately *added* world_context mid-sequence (turn 4) and asserted the prefix digest never drifts. 61-20 promotes world_context into the cached prefix, so the mid-sequence add correctly drifts the digest → the test failed.
**Fix (TEA lane — test contract update for the architect-ratified design):** `world_context` is session-static (set once at connect, constant for the session), so test_60_6 now sets it ONCE on the base context, constant across all 5 turns. The test still proves the genuinely-volatile fields (npc_pool/state_summary/tropes) don't drift the prefix. Committed `36349b59`.
**Re-verified (serial -n0):** test_60_6 **7/7 PASS**, test_61_20 6/6, test_seed_valley_injection 13/13, test_culture_context 9/9, test_notorious_party 12/12. ruff clean on both test files.

### Full-suite baseline reconciliation (pre-existing failures, NOT 61-20)
The full run had 21 failures; after the test_60_6 fix, the remaining 18 are all pre-existing env/infra debt, none attributable to 61-20:
- **6 content/asset** (test_audit_namegen_corpora ×4, pack-validator content/crossref) — sidequest-content asset-tree gaps; server-only change can't affect them.
- **11 "worker crashed"** (test_45_27_trope_tempo_wire, test_chargen_complete_no_hp_leak, test_confrontation_dispatch_wiring) — **proven flaky**: `test_confrontation_dispatch_wiring` PASSES 7/7 when run serially. Root cause is an OTEL `force_flush(200ms)` deadlock (`websocket_session_handler.py:2250`, unreachable localhost:4317) under parallel load — code 61-20 never touches.
- **1 SWN** (test_space_opera_swn_combat_e2e ship hull) — ADR-114 territory, unrelated.

**Quality Checks:** ruff clean (changed files); the one pre-existing `tools/__init__.py:10` I001 and the `orchestrator.py:2966` pyright error are both outside this story's diff.
**Handoff:** To Reviewer (Colonel Potter) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; ruff clean; 45/45 affected tests pass | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — domain assessed by Reviewer |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (also: TEA verify ran all 3 simplify analysts → clean) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — rules assessed by Reviewer (see Rule Compliance) |

**All received:** Yes (preflight returned; the other 8 are disabled via `workflow.reviewer_subagents` and their domains were assessed directly by the Reviewer)
**Total findings:** 0 confirmed blocking, 2 Low (cosmetic), 6 VERIFIED, deviations all stamped ACCEPTED

## Reviewer Assessment

**Verdict:** APPROVED

A small (157 src lines / 5 files), well-scoped cache-zoning change that survived the full pipeline (RED→GREEN→spec-check→verify) with a sibling-test regression already caught and fixed in verify. Eight thematic subagents are disabled via settings; I assessed each domain directly against the diff.

**Data flow traced:** `context.world_context` (set once at `connect.py:820` → `sd.world_context` → `session_helpers.py:1183` → TurnContext) → registered at `orchestrator.py:2080` as section `world_context` zone **Early** + bucket **System** (`STABLE_SECTION_NAMES`) → `compose_split_by_zone` routes it to `stable_text` → `system_blocks[0]` (cache=True, 1h). Safe because world_context is session-static by construction (one source, threaded unchanged; the rare culture-add re-writes the prefix once — architect-accepted).

**Observations (8):**
- `[VERIFIED]` world_context is session-static — `connect.py:820` sets it once on `sd.world_context`; `session_helpers.py:1183` reads it unchanged each turn. Complies with the `STABLE_SECTION_NAMES` byte-identity contract.
- `[VERIFIED]` magic static head is session-static — `_static_lines` reads only `config.{world_slug,allowed_sources,active_plugins,valid_cost_types,hard_limits,world_knowledge}`, all built once in `magic_loader.py:103-132` at session bind, never mutated per-turn. Safe to promote.
- `[VERIFIED][SILENT]` no silent fallback introduced — `build_magic_static_block`/`build_magic_volatile_block` return `""` on `magic_state is None` *explicitly*; the call sites sit inside `if context.magic_state is not None`, so None never reaches them. The `if magic_static:`/`if magic_volatile:` guards skip empty registration but neither is ever empty (static = 6 lines min; volatile always carries the unconditional magic_working instruction). No swallowed error.
- `[VERIFIED][TYPE]` `build_magic_context_block` output is byte-identical post-refactor — `_static_lines(ms) + _volatile_lines(ms,...)` is the exact original append order; `"\n".join` of an identical sequence is identical bytes. Confirmed by `tests/magic/test_context_builder.py` passing unchanged.
- `[VERIFIED][TEST]` the 6 new tests drive the real `Orchestrator.run_narration_turn` SDK path and assert wire-payload `system_blocks` placement / sha256 digest equality — a fixture-driven wiring test per CLAUDE.md "No Source-Text Wiring Tests", not a source grep. Meaningful assertions, no vacuous checks.
- `[VERIFIED][SEC]` no security surface — prompt-text composition only; interpolated content (`magic_static`, `world_context`) is server-built world config, not untrusted user input. No injection/auth/secret exposure.
- `[LOW][DOC]` the volatile block's new wrapper tag `<magic-ledger>` (orchestrator.py:2166) undersells its contents — it also holds the `magic_working` emit instruction, learned-magic, and reliquaries, not just the ledger. Cosmetic: the narrator (an LLM) reads the content regardless of wrapper name, and no parser keys off the tag (verified — only `test_47_9` references "magic-context", and it tests the combined `build_magic_context_block`, not the orchestrator wrapper). Non-blocking.
- `[LOW][TYPE]` API inconsistency — `build_magic_static_block(magic_state)` is positional while its siblings `build_magic_volatile_block`/`build_magic_context_block` are keyword-only (`*,`). The orchestrator calls it by keyword anyway, so harmless; a future tidy could align them. Non-blocking.

### Rule Compliance (python lang-review)

| Rule | Applicable code | Verdict |
|------|-----------------|---------|
| #1 silent exceptions | new builders + orchestrator guards | PASS — no try/except added; None-guards are explicit returns |
| #2 mutable defaults | `build_magic_volatile_block(..., reliquaries=None)` + `build_magic_context_block(..., reliquaries=None)` | PASS — `None` default, not `[]` |
| #3 type annotations at boundaries | all 3 public builders + 2 private helpers | PASS — params + returns annotated (`MagicState \| None` → `str`; `list[str]` helpers) |
| #4 logging | no new error paths | PASS — N/A |
| #6 test quality | 6 new + test_60_6 update | PASS — specific marker/digest assertions; test_60_6 retains teeth |
| #10 import hygiene | `magic/__init__.py` exports, orchestrator lazy import | PASS — explicit imports, `__all__` updated, no star imports |
| #11/#8/#5 input-validation/deserialization/path | — | N/A — no I/O, parsing, or path handling added |

### Devil's Advocate

Suppose this change is broken. The most dangerous failure mode is a *silent cache regression*: if either promoted section is not actually session-static, it gets written into the 1h prefix and invalidated every turn — re-creating the exact 73%-of-cost churn 61-19 fought, but now *harder to detect* because the content moved into the "stable" zone the GM panel trusts. So I attacked staticness hardest. world_context: could a per-turn dispatch mutate it? `culture_context.py` exists to append onto world_context — a "Yes, And" path. If that fires per-turn, the prefix churns. But it appends to `sd.world_context` (session state), a deliberate rare event, and the architect explicitly accepted the one-time re-write; it is not a per-turn recompute. magic static head: could `config.active_plugins` change when a plugin activates mid-session? The only writes are in `magic_loader.py` at bind; runtime plugin *firing* mutates the ledger (volatile, correctly kept in Valley), not `config.active_plugins`. So the static head holds.

Second attack: the byte-stability guard. The verify phase MOVED world_context to a constant in test_60_6 — does that *weaken* the guard so a future dynamic world_context slips through? Partially yes: test_60_6 no longer exercises a changing world_context. But `test_cached_prefix_byte_stable_across_turns_with_changing_ledger` (new, 61-20) does guard the magic half against a mutating ledger, and the displacement tests prove the static content leaves the volatile tail. The residual gap (a future story making world_context per-turn dynamic) is the same latent risk every `STABLE_SECTION_NAMES` member carries; it is a contract, not a code bug here.

Third attack: a confused narrator. The prompt now presents `<magic-context>` (static, in the system prefix) and `<magic-ledger>` (volatile, in the user message) as two separate blocks instead of one. Could the LLM lose the association between a hard_limit and its ledger bar? Both blocks still appear in the same turn's prompt with the same vocabulary; the 57-3 precedent split genre prose identically without narration regression, and the full magic test suite (47-9, reliquaries, context_builder, narrator_pre_prompt) passes. Acceptable.

Conclusion: no break found. The two Low notes are cosmetic.

**Pattern observed:** correct reuse of the ADR-112 / Story 57-3 zone-promotion pattern (zone→Early + name→STABLE_SECTION_NAMES) at `orchestrator.py:2080` + `bucket.py:77-93`.
**Error handling:** explicit None-guards in all three builders; no new failure paths.
**Handoff:** To SM (Hawkeye) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Conflict** (blocking): The story names `monster_manual` as a third zone-promotion target, but it is NOT a promotable prompt section in the Python impl. Per `project_narrator_gaslighting_doctrine.md` and `sidequest/server/dispatch/monster_manual_inject.py`, Manual entries are MATERIALIZED into `snapshot.npcs` as runtime `Npc` records and reach the prompt via the `game_state` (Valley) section — which is irreducibly volatile (NPCs/creatures/HP change every turn). It cannot ride a 1h-cached prefix without breaking correctness. Affects the story premise + `sidequest/agents/orchestrator.py` (game_state registration ~2059, monster_manual path) — **architect must reconcile at spec-check**: the AC1 `<2k` target is reachable from the two valid promotions (cultures + magic hard_limits) plus the already-bounded snapshot (61-2), but NOT by promoting monster_manual. *Found by TEA during test design.*
- **Gap** (non-blocking): `magic_context` is a MIXED section — the static `hard_limits:`/`allowed_sources:`/`world_knowledge:` header is session-static, but `active_ledger_for_<actor>:` (sanity/notice bar values) changes as magic is cast. The fix must SPLIT the section (static header → cached prefix; ledger → Valley tail), not promote it wholesale. Affects `sidequest/agents/orchestrator.py` ~2134 + `sidequest/magic/context_builder.py` (`build_magic_context_block`). Tests `test_magic_hard_limits_promoted_*` + `test_volatile_magic_ledger_stays_out_*` together force the split. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The absolute AC1 (`<2k/turn`) and AC2 (`≤$0.05/turn`) thresholds want a live-session confirmation. The observability already exists — the 61-19 `narrator.sdk.usage` split (`stable_prefix_write_tokens`/`tail_write_tokens`) now shows the shrunken recurring tail on any live run. Recommend a 61-6-style follow-up chore: one 17+-turn `perseus_cloud` (magic) session, read the span, confirm tail <2k + per-turn ≤$0.05. No code change needed. *Found by Dev during implementation.*
- **Question** (non-blocking): The magic_working instruction paragraph + innate_v1 worked-example (static prose, ~250 tok) stayed in the volatile `magic_context` tail rather than being promoted — they reference `active_ledger_for_<actor>` literally and would trip the ledger-out guard / require rewording guardrail prose (a content change the story forbids). If the architect wants that prose promoted too, it needs a separate static instruction section + a reword. Affects `sidequest/magic/context_builder.py` + `sidequest/agents/orchestrator.py`. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): A pre-existing OTEL `force_flush(timeout_millis=200)` deadlock (`sidequest/server/websocket_session_handler.py:2250`) hangs serial (`-n0`) test runs and surfaces as "worker crashed" under xdist when the OTEL collector (`localhost:4317`) is unreachable. Hit by `test_45_27_trope_tempo_wire`, `test_chargen_complete_no_hp_leak`. Not a 61-20 regression (proven: sibling `test_confrontation_dispatch_wiring` passes 7/7 serially). Recommend a follow-up: bound/skip force_flush when no collector is configured. *Found by TEA during test verification.*

### Reviewer (code review)
- **Improvement** (non-blocking): the test_60_6 fix made `world_context` constant, so no test now guards against a *future* change making world_context per-turn dynamic (which would silently churn the promoted prefix). Same latent risk every `STABLE_SECTION_NAMES` member carries. If a later story adds a per-turn world_context mutation, add a byte-stability test with a *changing* world_context. Affects `tests/agents/test_60_6_stable_prefix_live_drift.py`. *Found by Reviewer during code review.*
- No blocking findings during code review.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **monster_manual promotion not tested as a promotion (tested as a boundary guard instead)**
  - Spec source: context-story-61-20.md, Scope/AC1 + story title ("zone-promotion of ... monster_manual")
  - Spec text: "promote the session-static Valley sections (AVAILABLE CULTURES block, magic hard_limits, monster_manual) into the cached 1h stable prefix"
  - Implementation: No promotion test for monster_manual. Instead `test_volatile_game_state_not_promoted_to_cached_prefix` pins that the monster_manual-bearing `game_state` section stays OUT of the cached prefix.
  - Rationale: monster_manual is not a cacheable prompt section in Python — it is materialized into volatile `snapshot.npcs`/`game_state` (see blocking Delivery Finding). A promotion test would assert a behavior that is incorrect to implement.
  - Severity: major
  - Forward impact: architect must reconcile the story premise at spec-check; AC1 `<2k` rests on the two valid promotions + 61-2's bounded snapshot, not on monster_manual.
- **AC1 numeric `<2k/turn` asserted via marker-displacement, not a raw token count**
  - Spec source: context-story-61-20.md, AC1
  - Spec text: "per-turn cache_write < 2,000 tokens at steady state"
  - Implementation: Tests assert the static markers (AVAILABLE CULTURES header, hard_limits header) LEAVE the volatile tail and ENTER the cached prefix (`test_available_cultures_*`, `test_magic_hard_limits_*`). The absolute `<2k` token count is not asserted in a unit test.
  - Rationale: the residual tail size depends on the (non-promotable, live) snapshot; a raw count is brittle and not honestly assertable against a fake. Mirrors 61-19's deferral of AC2/AC3 absolute thresholds to a live "61-6-style" probe. The story's live-validation probe is the absolute gate.
  - Severity: minor
  - Forward impact: the live-validation-probe deliverable (named in the story) is the absolute AC1/AC2 confirmation.
- **AC5 (stable-prefix/tail write split span) not re-tested — covered by 61-19**
  - Spec source: context-story-61-20.md, AC5 carry-over
  - Spec text: "verify the split still decomposes correctly and is emitted from the production turn path"
  - Implementation: No new AC5 test. `tests/agents/test_61_19_volatile_block_cache_tier.py` already asserts the per-turn `stable_prefix_write_tokens`/`tail_write_tokens` split + wiring + cadence; the span keys off the 1h/5m TTL tiers, which the promotion preserves (promoted content rides the 1h prefix, recurring tail stays 5m).
  - Rationale: avoid duplicating live coverage (Don't Reinvent). If Dev's split changes the span's tier mapping, 61-19's tests will catch it.
  - Severity: minor
  - Forward impact: if the implementation alters the span's field/tier contract, add a 61-20 span test; otherwise 61-19's coverage holds.

### Dev (implementation)
- **Live-validation probe not implemented as code**
  - Spec source: context-story-61-20.md, "Live-validation probe (story-named deliverable)"
  - Spec text: "a probe (telemetry read or short bounded live run) confirming the steady-state per-turn write < 2k and cost ≤ $0.05"
  - Implementation: No probe script written. The confirmation rides the EXISTING 61-19 `narrator.sdk.usage` split span (`stable_prefix_write_tokens`/`tail_write_tokens`), which an operator reads on any live session.
  - Rationale: a live billed Anthropic session is not a unit-testable artifact, and writing throwaway probe code violates "No Stubbing". 61-19 set the precedent of deferring absolute thresholds to a 61-6-style follow-up. Logged as a non-blocking Delivery Finding.
  - Severity: minor
  - Forward impact: AC1/AC2 absolute confirmation is a follow-up live chore, not part of this PR.
- **magic_working instruction + innate example left in the volatile tail (not promoted)**
  - Spec source: context-story-61-20.md, Scope ("magic hard_limits")
  - Spec text: "promote ... magic hard_limits ... into the cached 1h stable prefix"
  - Implementation: Promoted only the world-config head through `world_knowledge` (incl. `hard_limits`) into `magic_hard_limits`. The magic_working instruction paragraph + innate_v1 worked-example (static, ~250 tok) stayed in volatile `magic_context`.
  - Rationale: that prose contains the literal `active_ledger_for_<actor>` reference and is coupled to the per-actor ledger; promoting it would trip the ledger-out guard and require rewording guardrail prose (a content change the story forbids). The story names "hard_limits" specifically — the world-config head is the clean, test-satisfying boundary.
  - Severity: minor
  - Forward impact: a small static residual remains in the 5m tail; if the architect wants it promoted, it needs a separate instruction section + reword (logged as a Dev Question finding).

### TEA (test verification)
- **Updated test_60_6 to reflect the promoted world_context invariant**
  - Spec source: 61-20 design (architect-ratified spec-check) + context-story-61-20.md AC1
  - Spec text: "promote ... AVAILABLE CULTURES ... into the cached 1h stable prefix"
  - Implementation: `tests/agents/test_60_6_stable_prefix_live_drift.py` previously listed `world_context` among volatile User-bucket fields and added it mid-sequence (turn 4), asserting zero prefix drift. Changed it to set `world_context` ONCE on the base context (constant across all 5 turns), matching its real session-static lifecycle.
  - Rationale: 61-20 intentionally promotes world_context into the cached prefix; the old test encoded the pre-61-20 invariant and broke. The test's core intent (genuinely-volatile fields don't drift the prefix) is preserved for npc_pool/state_summary/tropes. This is a sibling-test contract update, not a weakening — the byte-stability assertion still holds and still has teeth.
  - Severity: minor
  - Forward impact: none — test_60_6 now passes 7/7 and continues to guard prefix byte-stability under the new zoning.

### Reviewer (audit)
- **TEA: monster_manual not tested as a promotion** → ✓ ACCEPTED by Reviewer: correct — monster_manual is materialized into volatile `snapshot.npcs`, not a cacheable section; architect ratified at spec-check. Not promotable.
- **TEA: AC1 numeric `<2k` via marker-displacement** → ✓ ACCEPTED by Reviewer: honest given the live snapshot dependency; mirrors 61-19's deferral. Live probe is the absolute gate.
- **TEA: AC5 split span not re-tested (covered by 61-19)** → ✓ ACCEPTED by Reviewer: the promotion preserves the 1h-prefix/5m-tail TTL mapping the existing span keys off; no duplication warranted.
- **Dev: live-validation probe not implemented as code** → ✓ ACCEPTED by Reviewer: a live billed run isn't a unit artifact; the 61-19 OTEL split span provides the observability. Follow-up chore, correctly logged.
- **Dev: magic_working instruction + innate example left volatile** → ✓ ACCEPTED by Reviewer: promoting that prose would require rewording guardrail text (forbidden) and trips the ledger-out guard; the world-config head is the correct promotion boundary.
- **TEA(verify): test_60_6 updated for promoted world_context** → ✓ ACCEPTED by Reviewer: a legitimate sibling-test contract update for the architect-ratified design, not a weakening — byte-identity still asserted with teeth (mutating npc_pool/state_summary/tropes).
- **Undocumented (Reviewer-spotted): volatile magic block re-wrapped `<magic-context>` → `<magic-ledger>`** (`orchestrator.py:2166`): the split renamed the volatile block's wrapper tag. Spec implied the magic block stays `<magic-context>`; code now emits two blocks (`<magic-context>` static + `<magic-ledger>` volatile). Severity: **Low** — cosmetic, no parser/test consumer (verified), narration unaffected. → ✓ ACCEPTED by Reviewer as an inherent, sensible consequence of the split. (Also raised as a Low observation in the assessment.)

### Architect (reconcile)

**Manifest verification:** All six in-flight deviation entries (TEA ×3, Dev ×2, TEA-verify ×1) carry the full 6-field format with accurate spec sources (`context-story-61-20.md` exists; `61-19` precedent cited correctly) and accurate code citations (verified `orchestrator.py:2166` = the `<magic-ledger>` wrapper; the staticness claims hold per `connect.py:820` + `magic_loader.py:103-132`). The Reviewer audit stamped every entry ACCEPTED and surfaced one additional Low deviation (the `<magic-context>`→`<magic-ledger>` tag rename), also accepted. No entry is inaccurate or incomplete.

**AC deferral check:** No-op — the story inherited 61-19's ACs with no structured YAML AC list, so the ac-completion gate wrote no AC accountability table. The deferrals (AC1 `<2k` / AC2 `≤$0.05` absolute thresholds → live probe; AC5 span → existing 61-19 coverage) are documented in the TEA/Dev deviations and ratified at spec-check. Nothing slipped through.

**Headline deviation (for the audit reader):** The story named **three** promotion targets (AVAILABLE CULTURES, magic hard_limits, monster_manual); **two** were promoted. `monster_manual` was correctly NOT promoted — in the Python impl it is materialized into the volatile `snapshot.npcs`/`game_state` (gaslighting doctrine), not a cacheable prompt section, so it is not promotable without breaking correctness. This is a **spec-update (Option A)**, ratified at spec-check: AC1's `<2k` target rests on the two valid promotions + 61-2's already-bounded snapshot, which is architecturally sound. The premise correction is fully traced: TEA blocking finding → TEA major deviation → Architect spec-check ruling → Reviewer ACCEPTED.

- No additional deviations found beyond those already logged and stamped.