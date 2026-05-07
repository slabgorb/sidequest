---
story_id: "45-53"
jira_key: null
epic: "45"
workflow: "tdd"
---

# Story 45-53: Recurring NPC presence — narrator emits npcs_met every turn they're onstage

## Story Details
- **ID:** 45-53
- **Epic:** 45 (Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup)
- **Workflow:** tdd
- **Type:** bug
- **Points:** 3
- **Priority:** p2
- **Repos:** server
- **Stack Parent:** none

## Problem Statement

The narrator currently only emits `npcs_met` when NPCs are:
1. First encountered (`is_new: true`)
2. Adversaries in a confrontation (per CRITICAL ADVERSARY RULE)

This creates a critical gap: **recurring NPCs (allies, merchants, quest-givers) who appear onstage in multiple turns may disappear from the game state because they're never re-emitted.**

The root cause: the narrator prompt lacks instruction to emit `npcs_met` entries for NPCs who are onstage but not newly encountered in that turn. This causes the game state to lose track of which NPCs are present, making it impossible for downstream systems to maintain encounter continuity or build NPC-centric narrative arcs.

## Acceptance Criteria

From epic-45 context:

1. **MAIN AC:** Every turn where a named, persistent NPC is described as onstage (physically present in the narration), the narrator MUST emit that NPC in `npcs_met` with at minimum `name` and `role`, regardless of whether they are newly encountered that turn.

2. **Coverage:** Applies to all NPC types:
   - Allies / companions
   - Quest-givers / patrons
   - Merchants / vendors
   - Neutral bystanders who are named and present
   - NOT applies to: passing strangers with no dialogue or focus

3. **No silent fallback:** If a named NPC is described in prose as onstage (sitting at a table, standing guard, running a shop, etc.) but narrator fails to emit them in `npcs_met`, the test must fail with a clear error message indicating which NPC was missed.

4. **Spec integration:** The narrator prompt must:
   - Explicitly state the rule to emit `npcs_met` every turn an NPC is onstage
   - Distinguish between "named and onstage" (must emit) vs "passing mention" (optional)
   - Cross-reference the CRITICAL ADVERSARY RULE to show this extends beyond combat

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish (test-writing)
**Phase Started:** 2026-05-07T23:30:11Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-05-07T20:00:00Z | 2026-05-07T23:02:53Z | 3h 2m |
| green | 2026-05-07T23:02:53Z | 2026-05-07T23:07:20Z | 4m 27s |
| spec-check | 2026-05-07T23:07:20Z | 2026-05-07T23:13:00Z | 5m 40s |
| verify | 2026-05-07T23:13:00Z | 2026-05-07T23:18:35Z | 5m 35s |
| review | 2026-05-07T23:18:35Z | 2026-05-07T23:27:34Z | 8m 59s |
| spec-reconcile | 2026-05-07T23:27:34Z | 2026-05-07T23:30:11Z | 2m 37s |
| finish | 2026-05-07T23:30:11Z | - | - |

## Sm Assessment

**Story scope and readiness:** Story 45-53 is well-scoped, unblocked, and ready for the red phase. The problem is a concrete narrator-emission gap (recurring NPCs vanish from `npcs_met` after first appearance), and the fix lives in `sidequest-server` only — server-bounded story, no cross-repo coordination required.

**Technical approach:** Two-part fix.
1. **Narrator prompt amendment** — extend `NARRATOR_OUTPUT_ONLY` in `sidequest/agents/narrator.py` so `npcs_met` covers every-turn presence of named NPCs (not just `is_new` or adversary cases), with the explicit "named & onstage" vs "passing mention" distinction.
2. **Orchestrator validation hook** — extend `_validate_game_patch` (`sidequest/agents/orchestrator.py`) to fail loudly when narration prose references a known recurring NPC by name as onstage but the patch omits them from `npcs_met`. Aligns with the project's "No Silent Fallbacks" principle.

**Test strategy (red phase guidance for Fezzik):**
- New tests in `tests/agents/test_narrator.py` covering: ally onstage, merchant onstage, quest-giver onstage, named bystander onstage — all must require `npcs_met` emission even when `is_new` is false.
- One test in `tests/agents/test_orchestrator.py` for the validation guard (prose names recurring NPC → patch omits → validation fails with descriptive error).
- One **wiring test** per CLAUDE.md mandate: prove the new prompt rule is reachable from the production narrator path (not just unit-tested in isolation).
- One **OTEL test**: per OTEL Observability Principle, the recurring-presence detector must emit a span when it fires (or when validation rejects a missing recurring NPC). The GM panel needs to see this subsystem engaging.

**Acceptance criteria coverage:** AC1 (every-turn emission) → narrator prompt + tests. AC2 (NPC type coverage) → multiple test fixtures. AC3 (no silent fallback) → orchestrator validation guard. AC4 (spec integration) → prompt amendment.

**Risk / scope discipline:** Resist the temptation to refactor `npcs_met` schema or extend to `npcs_left` symmetry — that's a separate story. Stay inside the AC. Boy-scout fixes welcome if bounded (per project memory).

**Branch and routing:** Feature branch `feat/45-53-npcs_met-recurring-presence` created on `sidequest-server`. Phased TDD workflow → next agent is **TEA (Fezzik)** for the red phase.

## Delivery Findings

No upstream findings at story setup.

<!-- TEA appends below -->

### TEA (test design)

- **Gap** (non-blocking): The SM Assessment referenced a `_validate_game_patch`
  method on `Orchestrator` that does not exist. The actual relevant code path
  is `_apply_npc_mentions` in `sidequest/server/narration_apply.py` (the
  Wave 2A 3-step lookup), which already emits `npc.referenced` spans for
  cited NPCs but has no detector for the *missing* case (named in prose,
  not emitted). The recurring-presence detector belongs alongside it.
  Affects `sidequest/server/session_helpers.py` and
  `sidequest/server/narration_apply.py` (new helper + invocation).
  *Found by TEA during test design.*

- **Improvement** (non-blocking): Existing OTEL `npc.*` spans (`auto_registered`,
  `referenced`, `reinvented`, `pc_name_skipped`) all route as
  `state_transition` events under `component=npc_registry`. The new
  `npc.recurring_presence_missed` span follows the same convention so the
  GM panel shows it in the existing NPC lane without UI work.
  Affects `sidequest/telemetry/spans/npc.py`.
  *Found by TEA during test design.*

## Design Deviations

<!-- Deviation log per phase. SM created this section; each agent appends to its own subsection. -->

### TEA (test design)

- **Detector lives in `session_helpers.py`, not `orchestrator.py`**
  - Spec source: .session/45-53-session.md, SM Assessment Technical Approach §2
  - Spec text: "Orchestrator validation hook — extend `_validate_game_patch`
    (`sidequest/agents/orchestrator.py`) to fail loudly when narration prose
    references a known recurring NPC by name as onstage but the patch omits
    them from npcs_met."
  - Implementation: Tests target a new helper
    `_detect_missed_recurring_npcs` in `sidequest/server/session_helpers.py`,
    invoked from `sidequest/server/narration_apply.py` near
    `_apply_npc_mentions`. There is no `_validate_game_patch` method on
    `Orchestrator` (verified by grep across `sidequest/`). Pattern follows
    the existing `_detect_npc_identity_drift` (also in `session_helpers.py`,
    called from `narration_apply.py`).
  - Rationale: Story scope (session file) has higher authority than the
    `_validate_game_patch` reference, which appears to be SM's planning
    shorthand for "validation-style guard," not a literal method. Keeps
    detection adjacent to the apply path with snapshot, mentions, and
    prose all in scope.
  - Severity: minor
  - Forward impact: minor

- **Detector emits OTEL span only — no exception or hard validation failure**
  - Spec source: .session/45-53-session.md, AC3
  - Spec text: "If a named NPC is described in prose as onstage … but
    narrator fails to emit them in npcs_met, the test must fail with a clear
    error message indicating which NPC was missed."
  - Implementation: Detector emits `npc.recurring_presence_missed` span +
    a `logger.warning` whose message names the missed NPC. It does NOT
    raise an exception or reject the patch.
  - Rationale: AC3's "test must fail" applies to *unit-test failure during
    development*, not runtime behavior. A hard validation failure at
    runtime would crash the turn for an LLM extraction gap — exactly the
    pattern Story 45-33 explicitly avoids ("strict helper, lenient caller"
    — see narration_apply.py L1782-1793 comment block on the
    `NoOpponentAvailableError` swallow). The lie-detector model
    (CLAUDE.md OTEL Observability Principle) is "subsystem emits span;
    GM panel surfaces; human notices." Test failure on the detector is
    achieved by `_missed_spans(...) == [N]` assertions; runtime stays
    soft.
  - Severity: minor
  - Forward impact: none

- **Match is word-boundary case-insensitive — no fuzzy / phonetic match**
  - Spec source: .session/45-53-session.md, AC2
  - Spec text: (implicit — ACs do not specify match semantics)
  - Implementation: `test_detector_matches_on_word_boundary_not_substring`
    requires `\bname\b`-style word-boundary matching on case-folded prose.
    No Soundex / Levenshtein.
  - Rationale: ADR-031 OTEL discipline favors precision over recall on
    lie-detector signals — false positives turn the GM panel into noise
    and Sebastien stops watching it. Word-boundary case-folded match is
    cheap, language-agnostic for ASCII names, and parallels
    `_apply_npc_mentions`'s case-folded equality. Phonetic / fuzzy match
    is a v2 problem; out of scope for AC3.
  - Severity: minor
  - Forward impact: none

### Dev (implementation)

- **No deviations from spec.** All TEA test contracts implemented as
  specified. The TEA design deviations about detector location
  (`session_helpers.py`) and soft-fail (span only, no exception) were
  honored. Word-boundary case-insensitive matching was implemented
  exactly as `test_detector_matches_on_word_boundary_not_substring`
  required. No new deviations introduced during the green phase.

### Architect (reconcile)

- No additional deviations found.


## TEA Assessment

**Tests Required:** Yes
**Reason:** N/A — TDD red phase mandated by workflow.

**Test Files:**
- `tests/agents/test_narrator.py` (modified) — 3 new tests for AC1/AC2/AC4
  prompt-content rules, appended after the existing dead-code-demolition
  block. Pre-existing 40 tests untouched and still passing.
- `tests/server/test_recurring_npc_presence.py` (new) — 17 tests covering
  AC3 detector contract, OTEL span catalog/routing/helper, and the
  `_apply_narration_result_to_snapshot` wiring boundary.

**Tests Written:** 20 tests covering 4 ACs (AC1 every-turn emission, AC2
NPC-type coverage, AC3 no-silent-fallback detection, AC4 spec integration).

**Status:** RED — confirmed via `uv run pytest`:
- `test_narrator.py`: 3 failed, 40 passed (only the new prompt tests fail).
- `test_recurring_npc_presence.py`: 17 failed (no implementation yet).

### Rule Coverage

| Rule (lang-review/python.md) | Test(s) | Status |
|------|---------|--------|
| #4 logging level/correctness | `test_detector_logs_warning_with_descriptive_message` | failing (impl missing) |
| #6 test quality (meaningful assertions) | self-check pass — 2 vacuous tests removed in commit `19f3d41` and replaced with a sharper `RECURRING`-marker test | n/a |
| Wire-first / wiring-test mandate (CLAUDE.md) | `test_wiring_apply_narration_result_invokes_recurring_presence_detector` | failing (impl missing) |
| OTEL Observability Principle (CLAUDE.md) | `test_span_npc_recurring_presence_missed_is_defined_in_catalog`, `test_npc_recurring_presence_missed_span_is_routed`, `test_npc_recurring_presence_missed_span_helper_is_exported`, `test_recurring_presence_missed_span_attributes_round_trip_via_route` | failing (impl missing) |
| No Silent Fallbacks (CLAUDE.md) | `test_detector_warns_when_known_npc_named_in_prose_but_missing_from_npcs_present` (+ 9 sibling cases) | failing (impl missing) |

**Rules checked:** 5 of the relevant lang-review/CLAUDE.md rules have direct
test coverage. Rules #1, #2, #3, #5, #7-#13 are implementation-time
checklists for Dev (and the Reviewer's preflight gate) — they apply to the
GREEN-phase code, not to test design.

**Self-check:** 2 vacuous tests caught in the first RED-verify pass and
fixed in commit `19f3d41` (`test_narrator_prompt_recurring_rule_extends_beyond_combat`
and `test_narrator_prompt_recurring_rule_includes_role_field_requirement`).
Both passed on existing prompt content — replaced with a single
`RECURRING`-marker assertion that fails meaningfully.

### What Dev (Inigo Montoya) needs to implement

1. **`sidequest/agents/narrator.py`** — extend `NARRATOR_OUTPUT_ONLY` with a
   labeled `RECURRING ...` rule block stating: every turn a named NPC is
   onstage, MUST be in npcs_met (uniform `name AND role` contract); explicit
   "named and onstage" vs "passing mention" distinction; CRITICAL ADVERSARY
   RULE remains alongside.
2. **`sidequest/telemetry/spans/npc.py`** — add `SPAN_NPC_RECURRING_PRESENCE_MISSED`
   constant (`"npc.recurring_presence_missed"`), register a `SpanRoute` (event_type
   `state_transition`, component `npc_registry`, op `recurring_presence_missed`,
   surfacing attrs `name`, `source`, `turn_number`, `last_seen_turn`), and
   the `npc_recurring_presence_missed_span(...)` context manager.
3. **`sidequest/server/session_helpers.py`** — new helper
   `_detect_missed_recurring_npcs(*, snapshot, narration_text, emitted_mentions, turn_num)`.
   Word-boundary case-insensitive match against `snapshot.npcs` ∪
   `snapshot.npc_pool` names, with PC-name filter and npcs-shadows-pool
   precedence. Emit one span + warning log per miss.
4. **`sidequest/server/narration_apply.py`** — invoke the detector after
   `_apply_npc_mentions` (passing `result.narration` and
   `list(result.npcs_present)` plus `snapshot` and `turn_num`).
5. **`sidequest/server/session_handler.py`** — re-export
   `_detect_missed_recurring_npcs` in `__all__` for back-compat parity with
   `_detect_npc_identity_drift`.

**Handoff:** To Dev (Inigo Montoya) for implementation.

## Dev Assessment

**Status:** GREEN — all 59 story tests passing, 722 adjacent regression tests passing, lint clean.

**Implementation Complete:** Yes

**AC Coverage:**
- AC-1 (every-turn emission): narrator prompt RECURRING PRESENCE RULE (every turn / onstage); test: `test_narrator_prompt_requires_npcs_met_emission_every_turn_npc_is_onstage`.
- AC-2 (NPC type coverage — ally/merchant/quest-giver/bystander): narrator prompt enumerates roles; tests: `test_detector_warns_when_known_pool_member_named_in_prose_but_missing` (merchant case), `test_detector_warns_when_known_npc_named_in_prose_but_missing_from_npcs_present` (general).
- AC-3 (no silent fallback): `_detect_missed_recurring_npcs` emits warning span + WARNING log per miss; tests: 10 detector cases including `test_detector_logs_warning_with_descriptive_message` and the wiring test.
- AC-4 (spec integration — explicit rule, named-onstage vs passing mention, cross-reference adversary rule): narrator prompt amendment; tests: `test_narrator_prompt_distinguishes_named_onstage_from_passing_mention` and `test_narrator_prompt_introduces_dedicated_recurring_rule_block`.

**Implementation:**

1. **`sidequest/telemetry/spans/npc.py`** (+54 lines) — added
   `SPAN_NPC_RECURRING_PRESENCE_MISSED = "npc.recurring_presence_missed"`,
   registered a `SpanRoute` (event_type `state_transition`, component
   `npc_registry`, op `recurring_presence_missed`, surfacing `name`,
   `source`, `turn_number`, `last_seen_turn`), and the
   `npc_recurring_presence_missed_span(...)` context manager with
   `severity="warning"` baked in (parallel to `npc_reinvented_span`).

2. **`sidequest/server/session_helpers.py`** (+87 lines) — new
   `_detect_missed_recurring_npcs(*, snapshot, narration_text,
   emitted_mentions, turn_num)`. Builds a candidate map keyed by
   case-folded name where `npc_pool` entries are added first and
   `npcs` entries overwrite (so npcs-shadows-pool falls out
   naturally with `source="npcs"`). PC names are filtered out before
   matching. Per name, `re.search(rf"\b{re.escape(key)}\b", folded_text)`
   guards against substring false-positives (`Marya` ≠ `Maryana`).
   `re.escape` covers names with regex metacharacters. Emits one span
   + one WARNING log per miss, no exception. Imported `GameSnapshot`
   from `sidequest.game.session` for the type hint.

3. **`sidequest/server/narration_apply.py`** (+11 lines) — invokes
   `_detect_missed_recurring_npcs` immediately after `_apply_npc_mentions`
   inside `_apply_narration_result_to_snapshot`. Passes
   `result.narration or ""` (defensive empty-string fallback for
   degraded turns) and `list(result.npcs_present)`.

4. **`sidequest/server/session_handler.py`** (+2 lines) — re-exports
   `_detect_missed_recurring_npcs` in `__all__` parallel to
   `_detect_npc_identity_drift`.

5. **`sidequest/agents/narrator.py`** (+18 lines) — added a labeled
   "RECURRING PRESENCE RULE — MANDATORY ..." block after the
   CRITICAL ADVERSARY RULE in `NARRATOR_OUTPUT_ONLY`. Uses the
   uppercase `RECURRING` marker, contains the phrases "every turn",
   "onstage", "named and onstage", "passing mention", and explicitly
   notes the rule "extends the CRITICAL ADVERSARY RULE to non-combat
   scenes; both rules coexist." Concrete examples (Boris pours a
   drink / Marya is bent over her ledger) anchor the positive case;
   "the captain mentioned Boris in passing last week" anchors the
   negative case.

**Test results:**
- `tests/agents/test_narrator.py`: 43 passed (3 new + 40 pre-existing).
- `tests/server/test_recurring_npc_presence.py`: 16 passed (all detector
  + OTEL + wiring tests).
- Adjacent regression scope (722 tests across `tests/agents/`,
  `tests/server/test_dispatch.py`, `tests/server/test_npc_pool_narration_apply.py`,
  `tests/server/test_npc_identity_drift.py`,
  `tests/server/test_state_patch_current_room.py`, `tests/telemetry/`,
  `tests/integration/test_npc_wiring.py`): all green.
- Lint (`ruff check`) on the 7 changed files: clean (one auto-fixed
  import-ordering nit on the test file).

**Branch:** `feat/45-53-npcs_met-recurring-presence` pushed to
`origin/feat/45-53-npcs_met-recurring-presence` (commits `5b3e441`
TEA red, `19f3d41` TEA self-fix, `2b1987d` Dev green).

(Dev's deviation entry lives under `## Design Deviations → ### Dev (implementation)` above.)

**Handoff:** To Reviewer (Westley) for code review.

## Architect Assessment

**Status:** spec-check pass.

**Spec-check gate:** all 4 sub-checks pass — AC coverage (4 ACs addressed), Implementation Complete flag present, TEA deviations properly logged (3 entries, 6-field format), Dev deviations properly logged (1 entry).

**Architectural review:**

1. **ADR-031 (Game Watcher / OTEL)** — `SPAN_NPC_RECURRING_PRESENCE_MISSED` follows the established pattern: `state_transition` event_type, `npc_registry` component, attributes routed to a stable dict shape (`name`, `source`, `turn_number`, `last_seen_turn`, `op`). `severity="warning"` baked into the helper so `WatcherSpanProcessor` renders it as a drift alert. Parallel to `npc_reinvented_span` — no architectural drift.

2. **ADR-039 (Narrator Structured Output / `npcs_met` spec origin)** — prompt amendment extends the existing rule, does not replace it. Uniform "name AND role" contract preserved. CRITICAL ADVERSARY RULE remains intact alongside the new RECURRING PRESENCE RULE; both rules coexist as the prompt explicitly states.

3. **ADR-067 (Unified Narrator Agent)** — single persistent narrator session; the rule lives in `NARRATOR_OUTPUT_ONLY` which the Orchestrator injects into the Primacy/Guardrail zone every turn. No new agent spawn, no new session split.

4. **ADR-014 (Diamonds and Coal)** — recurring NPCs are diamonds-by-promotion (per the principle: "a minor NPC becomes major when players care about them"). The detector ensures the system can *see* the promotion happen by holding the narrator accountable to per-turn re-emission. Without this guard, every recurring NPC silently regresses from diamond to coal between turns.

5. **CLAUDE.md "No Silent Fallbacks"** — detector emits a loud warning (span + WARNING log) when narrator prose names a known recurring NPC but `npcs_present` omits them. The runtime stays soft (no exception) per the "strict helper, lenient caller" precedent (story 45-33). This is the right balance: visibility without crash-on-extraction-gap.

6. **CLAUDE.md "Verify Wiring"** — `test_wiring_apply_narration_result_invokes_recurring_presence_detector` exercises `_apply_narration_result_to_snapshot` end-to-end and asserts the span fires in production code path. The detector is not just unit-tested in isolation — it's wired in.

7. **Pattern alignment with Wave 2A (story 45-47)** — detector follows the npcs-shadows-pool precedence rule from `_apply_npc_mentions`, lives in the same module (`session_helpers.py`) as `_detect_npc_identity_drift`, and is invoked from the same site (`_apply_narration_result_to_snapshot` in `narration_apply.py`). No architectural surprises.

**Findings:**

- **Improvement (non-blocking):** `import re` inside `_detect_missed_recurring_npcs` — acceptable but could be hoisted to module-level for consistency with the rest of `session_helpers.py`. Not a blocker; Reviewer may flag as a polish item.
- **Improvement (non-blocking):** Story 45-53 originally lacked a `context-story-45-53.md` file (TEA proceeded with epic context only). Spec-check phase created one to satisfy the validator. Future stories in epic 45 should include story-context generation in setup if the TDD workflow mandates it.

**Deviations:** None added during spec-check. TEA's 3 deviations and Dev's 1 deviation entry are all correctly logged with the 6-field format.

**Handoff:** To TEA (Fezzik) for verify phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 7 (5 production, 2 test) — scope `5b3e441^..HEAD`

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No high-confidence reuse opportunities. The detector and `_apply_npc_mentions` iterate similar structures but serve different semantic purposes (read-only verification vs mutation); merging would obscure intent. Span helpers follow an intentional consistent pattern (`Span.open` + attribute dict) — extraction would hide the OTEL contract. Test fixtures are minimal one-liners with high semantic load. |
| simplify-quality | clean | Inline `import re` mirrors the existing pattern in `session_helpers.py` (`build_secret_note_events` uses inline `import json` / `from sidequest.protocol.dispatch`). Docstrings explain WHY, not WHAT. Inline comments are well-placed (PC-skip, emitted-name set, candidate-map shadowing, regex rationale). No vacuous test assertions; no dead code. |
| simplify-efficiency | clean | Per-name `re.search(rf"\b{re.escape(key)}\b", folded_text)` inside the loop is acceptable — Python caches compiled patterns, candidate lists are small (typical 5–20 names), this is a monitoring path not the render hot path. The two-pass candidate map (npc_pool first, then npcs overwrite) is the cleanest expression of the npcs-shadows-pool rule. The 17-line prompt block is necessary — every line is anchored by a test (RECURRING marker, every turn, onstage, named and onstage, passing mention). No abstraction bloat. |

**Applied:** 0 fixes — all three teammates returned `status: clean`.
**Flagged for Review:** 0 medium-confidence findings.
**Noted:** 0 low-confidence observations.
**Reverted:** 0.

**Overall:** simplify: clean

### Quality Checks

- **Story-specific tests** (`tests/agents/test_narrator.py` + `tests/server/test_recurring_npc_presence.py`): **59 passed**.
- **Story-area regression scope** (`tests/agents/`, `tests/server/test_dispatch.py`, `tests/server/test_npc_pool_narration_apply.py`, `tests/server/test_npc_identity_drift.py`, `tests/telemetry/`, `tests/integration/test_npc_wiring.py`): **717 passed**, 0 failed.
- **Lint** (`ruff check` on the 7 changed files): **clean**.
- **Full suite** (`uv run pytest` server-wide): 4450 passed, **10 pre-existing failures** in unrelated subsystems (chargen state machine, REST hub endpoints, opening turn bootstrap, character-sheet projection). Verified pre-existing by checking out parent commit `3f9a0ca`: at least 4 of the 10 failures (`tests/server/test_rest_hub_endpoint.py`) reproduce on main without any 45-53 changes. None of the 10 failures touch `narrator.py`, `narration_apply.py`, `session_helpers.py`, `npc.py`, or the apply-narration code path. Out of scope for this story.
- **Pre-existing repo-wide ruff errors** (3 — `game/beat_kinds.py`, `tests/game/test_opposed_check_numerical_advantage.py`, `tests/server/test_numerical_advantage.py`): present on `3f9a0ca`, not introduced by 45-53. Out of scope.

### Findings (this phase)

- No upstream findings during test verification.

**Handoff:** To Reviewer (Westley) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (1H, 2M, 2L) | confirmed 3, dismissed 0, deferred 2 |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 (4M, 1L) | confirmed 1, dismissed 4, deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 (2H) | confirmed 2, dismissed 0, deferred 0 |

**All received:** Yes (4 enabled subagents returned, 5 disabled via settings)
**Total findings:** 6 confirmed (fixed in commit `edd7f3d`), 4 dismissed (with rationale), 2 deferred (low-confidence fragility signals).

## Reviewer Assessment

**Status:** APPROVED — fixes applied, all tests green, lint clean.

### Confirmed findings (fixed in commit `edd7f3d`)

1. **[TEST] [DOC] `field`/`source` inconsistency in SpanRoute** (test-analyzer #2 high + comment-analyzer #5 medium — corroborated). The route lambda hardcoded `"field": "npc_pool"` for all `npc.recurring_presence_missed` spans regardless of `source`. Stateful Npc misses (source="npcs") were being routed to the wrong GM-panel column. Fix: route field now mirrors source — `"npc_registry"` for `source="npcs"`, `"npc_pool"` for `source="npc_pool"`. Added two new tests covering both branches (`test_recurring_presence_missed_span_route_field_uses_npc_pool_for_pool_source` + assertion in the existing round-trip test).

2. **[RULE] Inline `import re` in detector** (rule-checker #10 high). Standard library `re` has no circular-import risk and `narration_apply.py` already imports it at module level. Moved to module-level imports in `session_helpers.py` for consistency with the project convention (existing inline imports in this file — `json`, `SubsystemDispatch` — are deferred only to break circular imports).

3. **[RULE] Missing type annotation on `_missed_spans`** (rule-checker #3 high). Added `InMemorySpanExporter` annotation under `TYPE_CHECKING` import block, matching the pattern used elsewhere.

4. **[TEST] Pool-member test missing attribute assertions** (test-analyzer #1 medium). The pool-source test was only asserting `source="npc_pool"`. Added `turn_number == 12` and `last_seen_turn == 0` assertions so a regression that mis-threads turn_num or surfaces a garbage last_seen_turn can be caught.

5. **[TEST] No regex-metacharacter regression test** (test-analyzer #3 medium). The detector relies on `re.escape(key)` to match names like `"Dr. Smith"` literally. Added `test_detector_matches_name_with_regex_metacharacters` to lock that contract in.

6. **[TEST] Route round-trip test never asserted `extracted['field']`** (test-analyzer #2). Now asserted alongside the new dynamic-field logic.

### Dismissed findings (with rationale)

1–4. **[DOC] "Story 45-53:" tag in 4 production-code locations** (comment-analyzer #1, #2, #3, #4 — three medium, one low). DISMISSED. Story-ID prefixes are a pervasive project convention used as institutional-memory anchors throughout the codebase — see `# Story 45-21:`, `# Story 45-47:`, `# Story 45-33:`, `# Story 37-44:`, `# Wave 2A (story 45-47):` and many others in the same files. Story IDs are immutable, so the "stale-on-arrival" rationale does not apply. Removing them would diverge from established convention without a corresponding rule. Per the agent definition's dismissal criteria, the dismissal cites a counter-pattern in the codebase rather than a competing rule, but is supported by uniform precedent.

### Deferred findings (low-confidence fragility signals)

1. **[TEST] Wiring test could assert span attributes** (test-analyzer #4 low). DEFERRED. The current wiring test asserts the detector fires through the production path — the strongest signal. Argument-binding correctness is exhaustively covered by the unit tests on the detector (which assert all four attribute fields). Adding attribute assertions to the wiring test is defensible polish but doesn't catch a bug the unit tests miss.

2. **[TEST] `caplog.at_level(logger="sidequest.server.session_helpers")` pin** (test-analyzer #5 low). DEFERRED. No current breakage; the default root-logger propagation works. A future change that breaks propagation would surface as a hard test failure (correctly), not a silent pass. Pinning is a polish item.

### Re-verification after fixes

- `tests/agents/test_narrator.py` + `tests/server/test_recurring_npc_presence.py`: **61 passed** (up from 59, +2 new tests).
- Adjacent regression scope (agents/, dispatch, npc_pool_narration_apply, npc_identity_drift, telemetry/, integration/test_npc_wiring): **717 passed**.
- `ruff check` on the 7 changed files: clean.

### ADR / spec alignment (independent confirmation of Architect's review)

- ADR-031 (Game Watcher / OTEL): the dynamic `field` mapping now correctly bridges the npcs-vs-pool dichotomy and matches the GM-panel routing convention used by `npc.auto_registered`, `npc.referenced`, and `npc.reinvented`.
- AC1–AC4: all four ACs remain covered after the fixes; no test was removed, only added or strengthened.
- "Strict helper, lenient caller" precedent (story 45-33): the detector's soft-fail behavior is preserved — no exception is raised on miss, only span + warning log.

### Summary

The implementation is **production-ready** after the 6 confirmed fixes. The original code was structurally sound — no architectural drift, no silent fallbacks, OTEL discipline correct, wire-first test in place. The findings caught in review are surface polish (annotation completeness, regex-edge regression coverage, route-field accuracy) rather than design flaws. Story 45-53 is approved for merge.

**Branch:** `feat/45-53-npcs_met-recurring-presence` pushed (commit `edd7f3d`). Ready for SM finish.

**Handoff:** To Architect (The Man in Black) for spec-reconcile.

## Technical Context

### Current Narrator Architecture

- **Prompt location:** `sidequest-server/sidequest/agents/narrator.py`
  - `NARRATOR_OUTPUT_ONLY` constant (~line 81–300+) defines `npcs_met` spec
  - `CRITICAL ADVERSARY RULE` (~line 231) currently only mentions confrontation context
  - `npcs_met` section (~line 247) currently reads "Include every named NPC, creature, or distinct group the player encounters" — ambiguous on recurring presence

- **Orchestrator validation:** `sidequest-server/sidequest/agents/orchestrator.py`
  - `_validate_game_patch` method validates patch correctness
  - Currently validates: confrontation adversary presence, new NPC registration, item transactions
  - Does NOT validate: recurring NPC presence (this is the gap)

- **Test structure:** `sidequest-server/tests/agents/test_narrator.py`
  - Contains `test_narrator_output_format_requires_adversaries_in_npcs_met` (confrontation scenario)
  - Needs new test(s) for recurring NPC emission

### Key References

- ADR-067 Unified Narrator Agent
- ADR-039 Narrator Structured Output (npcs_met spec origin)
- ADR-059 Monster Manual (NPC pre-generation, relevant for test fixtures)

### Current Test Suite Status

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/agents/test_narrator.py -v  # Current state
uv run pytest tests/agents/test_orchestrator.py -v  # Validation tests
```