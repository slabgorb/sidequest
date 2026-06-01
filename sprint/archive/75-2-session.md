---
story_id: "75-2"
jira_key: ""
epic: "75"
workflow: "tdd"
---
# Story 75-2: Port budgeted NPC working-set selection (npc_context.rs)

> **Note (2026-06-01):** This session file was reconstructed by Dev after the
> `testing-runner` subagent overwrote it with a results cache. Content restored
> from conversation context; downstream-relevant sections (assessments,
> deviations, ACs, findings) are preserved faithfully.

## Story Details
- **ID:** 75-2
- **Epic:** 75 (RAG Retrieval Layer — Restore Accretion, Budgeted Selection, Universal Retrieval Design)
- **Jira Key:** (none — Jira disabled for this project)
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Base Branch:** develop
- **Branch:** feat/75-2-budgeted-npc-working-set

## Story Context

**Type:** Restoration + Spec Supersession

SUPERSEDES 72-6 (the "cap the pool" framing was wrong — eviction violates
Diamonds-and-Coal / Living World). The Rust prototype bounded NPC prompt cost by
SELECTION, not eviction: `build_npc_registry_context_budgeted`
(github.com/slabgorb/sidequest-api `npc_context.rs:11-86`) gave scene-present
NPCs full profiles, others name+role, and when the player referenced no NPC,
compact names. ADR-118 promotes 75-2's selection to **the deterministic floor**
of the universal-retrieval layer.

**Pre-existing bug:** `session_helpers.py:1179` loaded `snapshot.npc_pool`
VERBATIM into `TurnContext`; `orchestrator.py:2001` registered the full pool +
all stateful NPCs with the narrator — no budgeting. Inflated prompt cost every
turn.

## Acceptance Criteria

1. **Budgeting function implemented:** Turn-context NPC assembly selects a budgeted working-set (scene-present full, others name+role, none-referenced compact) instead of loading `npc_pool` verbatim — port `npc_context.rs:11-86`.
2. **No eviction:** No NPC is ever deleted/evicted; full pool persists in the snapshot. Bounding is by prompt-selection only.
3. **OTEL observability:** OTEL span records how many NPCs were considered vs. selected into the prompt, with tier (full/brief/compact).
4. **Wiring test:** A pool with N NPCs where only k are scene-present (last_seen_turn >= turn - 2) yields a prompt section with k full profiles and the rest abbreviated, via the real turn-build path.

## Workflow Tracking

**Workflow:** tdd (phased) — setup → red → green → review → finish
**Phase:** finish (complete) → handoff to verify/review

| Phase | Owner | Status |
|-------|-------|--------|
| setup | Morpheus (SM) | done |
| red | The Architect (TEA) | done — 12 failing tests |
| green | Agent Smith (Dev) | done — 12 passing, full suite green |

## Sm Assessment

**Story selected (corrected path).** The Operator initially targeted 75-4, but 75-4 `depends_on: 75-2`, which was still `backlog`. 75-2 is the genuine unblocked root of the universal-retrieval chain (75-1 ✅, 75-3 ✅ done; 75-2 → 75-4 → 75-5/6 → 75-7 → 75-8). Built the foundation, not the floor resting on it.

**Nature of work:** RESTORATION port. SUPERSEDES 72-6 (eviction framing rejected as Diamonds-and-Coal / Living World violation). Full roster stays in the snapshot; only the relevant working-set enters the prompt.

**OTEL mandate:** This subsystem decision MUST emit a watcher span (selected-vs-total NPC counts, tier per NPC) so the GM panel can prove the budgeting fired.

**Jira:** Explicitly skipped — integration not configured in this repo.

**Risk flags for TEA:** (1) wire into BOTH consumers (wiring test required); (2) no silent fallback if `last_seen_turn` unset — fail loud or explicit default.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Test File:** `sidequest-server/tests/server/test_npc_working_set_budgeting.py` — 12 failing tests
**Status:** RED confirmed (12 failed, 0 passed; all on missing implementation). No collection errors; fixtures construct real models; `otel_capture` + `_build_turn_context` imports resolve.

**Binding RED contract for Dev (all NET-NEW):**
1. `sidequest/agents/npc_context.py`: `build_npc_working_set(snapshot, *, current_turn, player_referenced_npcs=None, recency_window=2) -> NpcWorkingSet`; `NpcWorkingSet` frozen dataclass (`full_profiles: list[Npc]`, `brief_entries: list[Npc | NpcPoolMember]`, `compact_names: list[str]`). Tiering: scene-present (`last_seen_turn >= current_turn - recency_window`) → full ALWAYS (floor); off-stage stateful + ALL pool members → brief when referenced, else compact; pool members never full; no eviction.
2. `sidequest/telemetry/spans/npc.py`: `SPAN_NPC_WORKING_SET = "npc.working_set"` + emitter + SpanRoute; attrs `full_count`, `brief_count`, `compact_count`, `total_pool`, `references_present`.
3. `TurnContext.npc_working_set`, populated by `_build_turn_context` (passes `snapshot.turn_manager.interaction`); `register_npc_roster_section` renders from it.

### Rule Coverage

| Rule (python.md) | Test(s) | Status |
|------|---------|--------|
| #6 test-quality | self-check: all 12 assert specific name-sets/counts/attrs | passing (self-check) |
| #1 silent-exceptions / No Silent Fallbacks | `test_never_seen_npc_classified_off_stage_not_scene_present` | RED→GREEN |
| OTEL principle | `test_working_set_span_emits_tier_counts`, `..._reports_compact_mode_when_no_reference` | RED→GREEN |
| Wiring rule | `test_budgeting_wired_into_build_turn_context` (real path + span, no source grep) | RED→GREEN |
| AC-1 recency + boundary | `test_scene_present_npcs_get_full_profiles_when_referenced`, `test_recency_boundary_is_inclusive_at_window_edge` | RED→GREEN |
| AC-2 no eviction | `test_no_eviction_*`, `test_pool_members_*` | RED→GREEN |
| ADR-118 floor (ruling) | `test_floor_holds_scene_present_full_even_with_no_reference`, `test_none_reference_signal_treated_as_no_reference` | RED→GREEN |

**Self-check:** 0 vacuous tests.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 12/12 story tests passing (GREEN); full suite 9415 passed / 361 skipped (3 pre-existing pack-content failures unrelated to this story); lint clean; pyright clean on all changed files (the orchestrator `send_stream` error at :2985 is pre-existing, untouched by this story).
**Branch:** feat/75-2-budgeted-npc-working-set (pushed)

**Files Changed:**
- `sidequest/agents/npc_context.py` (NEW) — `build_npc_working_set` + `NpcWorkingSet`; recency tiering; emits `SPAN_NPC_WORKING_SET`.
- `sidequest/telemetry/spans/npc.py` — `SPAN_NPC_WORKING_SET` constant, `npc_working_set_span` emitter, `SpanRoute` (GM-panel route).
- `sidequest/agents/orchestrator.py` — `TurnContext.npc_working_set` field (TYPE_CHECKING import); call site renders from the working-set when present (legacy npc_pool/npcs path retained for direct callers).
- `sidequest/server/session_helpers.py` — `_build_turn_context` computes + stores the working-set (v1 passes `player_referenced_npcs=None`).
- `sidequest/agents/prompt_framework/core.py` — `register_npc_roster_section` gains additive `working_set` kwarg + `_register_budgeted_npc_roster` tier renderer; `npc_pool`/`npcs` made optional (backward-compatible — all existing roster tests stay green).

**Wiring (no half-wiring):** selection → `TurnContext.npc_working_set` → `register_npc_roster_section` budgeted renderer, reachable from the live turn-build path and proven by OTEL span + the wiring test. The verbatim roster dump is replaced in production.

**Handoff:** To next phase (verify / spec-check / review).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (refactor kept all tests green)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 6 (5 production + the test file)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | 2 high (name-extraction dup; full-NPC rendering dup), 1 medium (header/closing boilerplate) |
| simplify-quality | 2 findings | both low (documented dual-path fallback; tested empty-return) — advisory |
| simplify-efficiency | clean | no findings (hot-path is linear, no over-engineering) |

**Applied:** 1 high-confidence fix — extracted `PromptRegistry._full_npc_line(npc)`, shared by the legacy `register_npc_roster_section` and the budgeted `_register_budgeted_npc_roster` full tier. Removed ~24 lines of verbatim duplication of the full stateful-NPC line; guarantees the ADR-104/105 perception-firewall format stays in sync across both paths. Byte-identical output — the format-sensitive legacy roster attitude tests stay green.

**Flagged for Review (not applied):**
- *(reuse, high)* Reuse `_name_of` from `npc_context.py` in the core.py brief loop. **Deliberately not applied:** importing it inverts the dependency (prompt_framework → agents.npc_context at runtime) and would consolidate only ~1 line that also carries inline pronouns/role extraction; the cross-module coupling isn't worth the marginal dedup. The inline `core.name if core else str(entry.name)` is correct and stable.
- *(reuse, medium)* Extract the section header + closing instruction into module constants. Marginal payoff; left for a future broader roster cleanup.
- *(quality, low ×2)* Dual-path branch fallback and the empty-tiers early-return are both already documented and tested — advisory only, no change.

**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Regression check:** ran directly via pytest (NOT testing-runner — that subagent overwrote the session file earlier in green; running directly protects it). Results: story tests 12/12 green; `tests/agents/` + roster server tests = 1669 passed; lint clean; pyright clean on the changed file. Pushed as `06c4db2`.

**Handoff:** To Reviewer (The Merovingian) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None requiring a code fix (2 documented defers)

Reviewed the full production diff (npc_context.py, orchestrator.py, core.py, session_helpers.py, telemetry/spans/npc.py) against all four ACs:

- **AC-1 (budgeting function):** `build_npc_working_set` ports `npc_context.rs:11-86` faithfully — scene-present full / off-stage brief / none-referenced compact. The verbatim roster dump into the *narrator prompt* is replaced (orchestrator:2006 renders from the working-set). The full `npc_pool`/`npcs` remain on `TurnContext` for other consumers — correct per the no-eviction doctrine.
- **AC-2 (no eviction):** working-set holds references to existing snapshot objects; snapshot is not mutated; off-stage entities are still named (compact). Aligned.
- **AC-3 (OTEL):** `SPAN_NPC_WORKING_SET` emits full/brief/compact/total + references_present, with a `SpanRoute` for the GM panel. Aligned.
- **AC-4 (wiring):** budgeted selection reachable from the live `_build_turn_context` path and consumed by the roster renderer; proven by span + wiring test (no source-text grep). Aligned.

**Deferred (resolution belongs to 75-5 per the ADR-118 waterfall — Option D):**
- **`player_referenced_npcs` signal (Behavioral, Minor):** v1 passes `None`, so off-stage NPCs always render compact in production; the brief tier is implemented, tested, and reachable but not yet triggered. Already logged as a Dev deviation. The reference/relevance signal is ADR-118 *fill* (75-5). The load-bearing floor (scene-present full) is reference-independent and fully live — accept.
- **Floor "current-location" dimension (Architectural, Minor):** ADR-118 D4 describes the floor as "last_seen ≤ N turns, current location's NPCs/POI." The implementation floors by **recency only** — faithful to the session scope and the Rust origin (`npc_context.rs` used `last_seen_turn`), and location-based flooring requires the location indexing that is genuinely 75-4/75-5 work. Not a 75-2 defect; flagged for the 75-5 retrieval orchestration. Pool members (no recency field) correctly default to off-stage; truly scene-present NPCs exist as stateful `Npc` records with `last_seen_turn`.

**Decision:** Proceed to review (verify phase). No hand-back to Dev.

## Delivery Findings

### TEA (test design)
- **Question** (non-blocking): The `player_referenced_npcs` signal source is undefined. Existing `_apply_npc_mentions` (narration_apply.py) reads NARRATOR output *post-turn*, not player input *pre-turn*. The brief-vs-compact toggle needs a per-turn signal at `_build_turn_context` time. Affects `sidequest/server/session_handler.py`. Not blocking — the scene-present floor is reference-independent. *Found by TEA during test design.*
- **Improvement** (non-blocking): A referenced *off-stage* NPC stays brief (not promoted to full); per-entity reference promotion is ADR-118 *fill* (75-5), not the 75-2 floor. Affects `75-5` scope. *Found by TEA during test design.*

### Dev (implementation)
- **Question** (non-blocking): Resolved the above TEA finding for v1 by passing `player_referenced_npcs=None` from `_build_turn_context` — in production, off-stage NPCs currently render compact (name only), never brief. The brief tier is reachable via the API (any caller passing references) and tested, but no production caller supplies the signal yet. The natural wiring point is ADR-118's fill orchestration (75-5). Affects `sidequest/server/session_helpers.py` / `75-5`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (blocking): The never-seen invariant breaks at session start. `build_npc_working_set` classifies scene-present as `last_seen_turn >= current_turn - recency_window`; `interaction` starts at 1, so the threshold is ≤ 0 for turns 1–2, and every NPC with the default `last_seen_turn=0` (never cited) is misclassified scene-present and injected at full detail. Affects `sidequest/agents/npc_context.py:82,90` (guard `last_seen_turn == 0` as never-seen, e.g. `npc.last_seen_turn > 0 and npc.last_seen_turn >= threshold`) and `tests/server/test_npc_working_set_budgeting.py` (add `current_turn=1`/`=2` cases). *Found by Reviewer during code review.*
- **Gap** (non-blocking): Test coverage gap — the never-seen invariant test only exercised `current_turn=10`, masking the early-turn boundary. The fix's new cases close it. Affects `tests/server/test_npc_working_set_budgeting.py`. *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- **No-reference case keeps the scene-present floor full (overrides session test-plan)**
  - Spec source: `.session/75-2-session.md`, Test Plan → unit test 2 (`test_npc_working_set_compact_only_when_no_references`)
  - Spec text: "Call `build_npc_working_set(snapshot, current_turn=10, player_referenced_npcs=set())` — Assert: 0 full profiles, 0 brief entries, 5 compact names"
  - Implementation: Tests encode the ADR-118 D4 floor — scene-present NPCs remain FULL even when no NPC was referenced; only off-stage entities collapse to compact (`test_floor_holds_scene_present_full_even_with_no_reference`).
  - Rationale: Operator ruling 2026-05-31; ADR-118 D4 defines 75-2 as the deterministic floor ("scene-present entities ALWAYS included, full detail"); SOUL Living World / Guitar Solo.
  - Severity: major
  - Forward impact: 75-5's floor+fill consumes this floor directly; resolved at the foundation now.
- **Single typed `TurnContext.npc_working_set` field instead of three parallel lists**
  - Spec source: `.session/75-2-session.md`, Technical Approach → Step 4
  - Spec text: "Extend `TurnContext` with new fields: `npc_pool_budgeted` ...; `npc_pool_brief` ...; `npc_compact_names` ..."
  - Implementation: One cohesive typed field `TurnContext.npc_working_set: NpcWorkingSet | None`.
  - Rationale: type-design — one typed value cannot desync the way three parallel lists can.
  - Severity: minor
  - Forward impact: none — `register_npc_roster_section` reads `context.npc_working_set`.
- **`build_npc_working_set` returns model objects, not projected dicts**
  - Spec source: `.session/75-2-session.md`, Technical Approach → Step 2
  - Spec text: 'Returns: {"full_profiles": [{"name": "...", ...}], "brief_entries": [...], "compact_names": [...]}'
  - Implementation: `NpcWorkingSet.full_profiles`/`brief_entries` hold existing `Npc`/`NpcPoolMember` objects; only `compact_names` are strings.
  - Rationale: reuse — the renderer already renders from `Npc`/`NpcPoolMember`; avoids dict re-projection drift and stringly-typed dicts.
  - Severity: minor
  - Forward impact: none.

### Dev (implementation)
- **`player_referenced_npcs` signal deferred to 75-5 (v1 passes None)**
  - Spec source: context-story-75-2.md, Technical Guardrails + TEA Question finding
  - Spec text: "the brief-vs-compact toggle needs a per-turn 'did the player reference any NPC' signal at `_build_turn_context` time"
  - Implementation: `_build_turn_context` passes `player_referenced_npcs=None`; off-stage NPCs render compact. The scene-present floor (the load-bearing behavior) is reference-independent and fully live.
  - Rationale: TEA explicitly sanctioned "pass None for v1 and log it"; a real reference/relevance signal is ADR-118 *fill* (75-5) territory. Avoids a speculative name-scanner with false-positive risk.
  - Severity: minor
  - Forward impact: 75-5 wires the real signal; until then off-stage NPCs are named (compact) but not role-tagged (brief). No eviction; floor intact.

### Reviewer (audit)
- **TEA: No-reference case keeps the scene-present floor full** → ✓ ACCEPTED by Reviewer: matches the Operator ruling + ADR-118 D4; the floor is the correct load-bearing behavior.
- **TEA: Single typed `TurnContext.npc_working_set` field** → ✓ ACCEPTED by Reviewer: type-design sound; one cohesive value beats three desyncable lists.
- **TEA: `build_npc_working_set` returns model objects, not dicts** → ✓ ACCEPTED by Reviewer: reuse-correct; renderer consumes `Npc`/`NpcPoolMember` directly, no projection drift.
- **Dev: `player_referenced_npcs` signal deferred to 75-5 (v1 passes None)** → ✓ ACCEPTED by Reviewer: TEA-sanctioned, ADR-118 waterfall-correct, floor is reference-independent. Not the cause of the rejection finding below.
- **UNDOCUMENTED (Reviewer):** The never-seen → off-stage invariant (asserted by `test_never_seen_npc_classified_off_stage_not_scene_present` and SM risk-flag #2) is violated for `current_turn ≤ 2` because the recency threshold goes ≤ 0 and `last_seen_turn=0` is the unset sentinel. Spec/intent said unset → off-stage; code does scene-present (full) at session start. Not logged by TEA/Dev. Severity: **High** (blocking) — see Reviewer Assessment.

### Architect (reconcile)

**Existing-entry verification:** The four logged deviations (TEA ×3, Dev ×1) each carry all 6 fields with accurate spec sources, quoted spec text, and forward-impact. No corrections needed. The Reviewer's UNDOCUMENTED early-turn finding was a *defect*, not a standing deviation — it is now resolved in code (`npc_context.py:90` sentinel guard) and pinned by three regression tests; it does not survive as a deviation.

**AC deferral check:** No ACs were DEFERRED or DESCOPED — all four (budgeting function, no-eviction, OTEL, wiring) are DONE and verified. The only deferral is a sub-behavior (brief-vs-compact reference signal), already captured as the Dev deviation above. No-op.

**Missed deviation added:**

- **Floor selection is recency-only; ADR-118 D4's location dimension is deferred**
  - Spec source: `docs/adr/118-universal-retrieval-layer.md`, decision D4
  - Spec text: "FLOOR = 75-2 working-set selection (scene-present entities: last_seen ≤ N turns, current location's NPCs/POI) → ALWAYS included, full detail, counted against the budget FIRST."
  - Implementation: `build_npc_working_set` floors by recency only (`last_seen_turn > 0 and last_seen_turn >= current_turn - recency_window`). The "current location's NPCs/POI" half of the floor is not implemented; an NPC physically at the current location but last seen > N turns ago is classified off-stage.
  - Rationale: Faithful to the higher-authority story scope and the Rust origin (`npc_context.rs:11-86` floored by `last_seen_turn` alone), per the spec-authority hierarchy (story scope > ADR). The location dimension requires the location/POI indexing that is ADR-118's *fill* work; adding it here would pull 75-5 scope into the floor story. In practice an NPC actively in a scene is cited and thus recency-stamped, so the recency floor covers the common case.
  - Severity: minor
  - Forward impact: **75-5** (`retrieve_turn_context` floor+fill) should complete the floor's location dimension when location/POI cards are indexed — flagged there so the ADR-118 floor contract is fully honored. No impact on 75-4 (EntityCard/projectors), which does not depend on the location-floor.

## Test Results (GREEN — Dev)

- **Story tests** `test_npc_working_set_budgeting.py`: **12 passed**.
- **Regression guard** (roster renderer / spans): **73 passed** across test_npc_roster_attitude, test_turn_context_sdk_wiring, test_orchestrator_split_allowlist, test_party_peer_identity, test_npc_identity_drift.
- **Full suite:** 9415 passed, 361 skipped (3 pre-existing pack-content failures unrelated to this story). No import cycles.
- **Lint/format:** clean. **pyright (changed files):** clean.
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (26 tests green, ruff clean, pyright pre-existing only) | N/A — confirmed baseline; flagged getattr duck-typing + early-turn threshold for scrutiny |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 (early-turn never-seen full-detail injection) | confirmed 1 (escalated to High) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 enabled returned, 7 disabled via settings)
**Total findings:** 1 confirmed (High), 1 derived test-coverage gap (Medium), 1 style note (Low); 0 dismissed

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [SEC] | Never-seen invariant breaks at session start: `interaction` starts at 1, so for turns 1–2 the recency threshold (`current_turn - 2`) is ≤ 0 and every NPC with the default `last_seen_turn=0` satisfies `last_seen_turn >= threshold` → misclassified scene-present and injected at FULL detail. Defeats the story's cost-bounding at session start, breaks the asserted never-seen→off-stage invariant, and silently treats the unset sentinel as recently-seen (No Silent Fallbacks — CRITICAL rule; SM risk-flag #2). | `sidequest/agents/npc_context.py:82,90` | Treat `last_seen_turn == 0` as never-seen regardless of threshold — e.g. `npc.last_seen_turn > 0 and npc.last_seen_turn >= threshold` (or `>= max(1, threshold)`). |
| [MEDIUM] [TEST] | Coverage gap: `test_never_seen_npc_classified_off_stage_not_scene_present` only ran at `current_turn=10`, missing the early-turn boundary where the bug lives. | `tests/server/test_npc_working_set_budgeting.py` | Add `current_turn=1` and `current_turn=2` cases asserting `last_seen_turn=0` NPCs land off-stage (compact). |
| [LOW] | Brief-tier name/role extraction duck-types the `Npc | NpcPoolMember` union via `getattr(..., None)` while `npc_context._name_of` uses `isinstance`; getattr could mask a future field rename (silent None). Non-blocking; note for consistency. | `sidequest/agents/prompt_framework/core.py` (`_register_budgeted_npc_roster` brief loop) | Optional: reuse isinstance-based extraction or accept as-is. |

### Observations (8)

- [HIGH][SEC] Early-turn never-seen full-detail injection — `npc_context.py:82,90` (the blocking finding above; confirmed by reviewer-security + my own turn-counter trace: `interaction` default=1, monotonic, never 0, so `last_seen_turn=0` is an unambiguous never-seen sentinel that the ≤0 threshold mishandles at turns 1–2).
- [VERIFIED] Perception firewall (ADR-104/105) intact — `_full_npc_line` emits `npc.disposition.attitude().value` (the coarsened band StrEnum), never the raw `disposition.value` integer. Evidence: `core.py:568`. Brief tier emits no disposition at all. reviewer-security confirmed 0 violations on this rule.
- [VERIFIED] No eviction (AC-2) — `build_npc_working_set` holds references to existing snapshot objects; snapshot not mutated; `full ∪ brief ∪ compact` covers the whole roster. Evidence: `npc_context.py:88-103`; tested by `test_no_eviction_every_npc_appears_and_snapshot_unchanged`.
- [VERIFIED] OTEL observability (AC-3) — `SPAN_NPC_WORKING_SET` fires every call with `full_count`/`brief_count`/`compact_count`/`total_pool`/`references_present`; `SpanRoute` registered for the GM panel; span carries integer counts + bool only (no names/PII). Evidence: `telemetry/spans/npc.py`; reviewer-security confirmed no leakage.
- [VERIFIED] Wiring (AC-4) reachable from the live path — `_build_turn_context` populates `TurnContext.npc_working_set`; orchestrator call site renders from it; proven by `test_budgeting_wired_into_build_turn_context` (behavior + span, no source-text grep — compliant with "No Source-Text Wiring Tests").
- [VERIFIED] Backward compatibility — `register_npc_roster_section` keeps `npc_pool`/`npcs` optional; the 14 legacy attitude tests stay green; `_full_npc_line` extraction is byte-identical.
- [MEDIUM][TEST] Coverage gap at early turns (above).
- [LOW] getattr duck-typing in the brief tier (above).

### Rule Compliance

- **No Silent Fallbacks (CLAUDE.md, CRITICAL):** VIOLATED at `npc_context.py:90` — the unset `last_seen_turn=0` is silently treated as scene-present at turns 1–2 instead of failing/landing off-stage. This is the blocking finding. (Cannot be dismissed — matches a stated project rule and SM risk-flag #2.)
- **ADR-104/105 perception firewall:** COMPLIANT (band, not raw value — `core.py:568`).
- **OTEL principle (every subsystem decision emits a span):** COMPLIANT (`SPAN_NPC_WORKING_SET`).
- **Every test suite needs a wiring test / No Source-Text Wiring Tests:** COMPLIANT (`test_budgeting_wired_into_build_turn_context`).
- **No Stubbing:** COMPLIANT (no stubs/placeholders).
- **python.md #1 silent exceptions / #2 mutable defaults / #3 type annotations:** COMPLIANT (no bare excepts; `player_referenced_npcs=None` default; full annotations).
- **python.md #6 test quality:** PARTIAL — assertions are non-vacuous, but the never-seen test had a boundary-coverage gap (Medium finding).

### Devil's Advocate

Assume this code is broken. The most damaging case is the one that fires on turn 1 of *every* session: a world that pre-materializes its opening cast into `snapshot.npcs` (bartender, quest-giver, guards) leaves each with `last_seen_turn=0` until the narrator first cites them. On turns 1 and 2 the threshold is `-1` then `0`, so all of them clear `last_seen_turn >= threshold` and render at full detail — the exact verbatim-dump-at-full-detail the story exists to eliminate, now reintroduced precisely at the highest-cast moment. A confused author would see the budgeting "working" at turn 10 in tests and never suspect session start. A cost-conscious operator would see prompt bytes spike on turn 1 and conclude the feature does nothing. Worse, the narrator is primed with the full cast — including NPCs the party hasn't met — inviting it to reference characters before they're introduced (a Diamonds-and-Coal inversion: coal rendered as diamonds). What about `interaction=0`? The default is 1 and it only increments, but any code path that constructs a turn context against a freshly-built snapshot before the first `record_interaction()` would hit `threshold=-2` — same failure class, wider. What if `last_seen_turn` were ever negative (corruption)? It would still be `< threshold` for turns ≥3, harmlessly off-stage — so the danger is strictly the unset-sentinel-meets-low-threshold collision. The fix is one conjunct (`last_seen_turn > 0`), but without it the story ships a benefit it does not deliver for the first two turns and violates its own asserted invariant. That is blocking.

**Data flow traced:** player action → `_build_turn_context(sd)` → `build_npc_working_set(snapshot, current_turn=interaction, player_referenced_npcs=None)` → `NpcWorkingSet` on `TurnContext` → `Orchestrator` roster call site → `register_npc_roster_section(working_set=...)` → `_register_budgeted_npc_roster` → narrator prompt section. The defect is at the classification step (`npc_context.py:90`) for `current_turn ≤ 2`.

**Handoff:** Back to TEA (red/rework) — add failing early-turn cases, then Dev applies the one-conjunct guard.
## TEA Assessment (rework RED — 2026-06-01)

**Trigger:** Reviewer HIGH finding — never-seen invariant breaks at session start.
**Tests added:** 3 to `tests/server/test_npc_working_set_budgeting.py`:
- `test_never_seen_npc_off_stage_at_session_start` (current_turn=1, threshold=-1)
- `test_never_seen_npc_off_stage_at_turn_two` (current_turn=2, threshold=0)
- `test_genuinely_recent_npc_still_full_at_early_turn` (guards against over-correction — NPCs seen at turns 1/2 must stay full; only the never-seen sentinel drops off-stage)

**RED confirmed:** 3 new tests fail against the current impl; 12 existing tests still pass (`3 failed, 12 passed`). Failures are the early-turn boundary, exactly the reviewer's finding.

**Fix contract for Dev:** the scene-present condition must treat `last_seen_turn == 0` (unset/never-seen) as off-stage regardless of threshold — e.g. `npc.last_seen_turn > 0 and npc.last_seen_turn >= threshold`. The new over-correction guard test ensures the fix doesn't drop legitimately-recent early-turn NPCs.

**Deviations:** No new deviations — this rework aligns the implementation to the asserted invariant (see `### TEA (test design)`).

**Handoff:** To Dev (Agent Smith) for GREEN (apply the guard).
## Dev Assessment (rework GREEN — 2026-06-01)

**Fix applied:** `sidequest/agents/npc_context.py:90` — scene-present condition is now `npc.last_seen_turn > 0 and npc.last_seen_turn >= threshold`. The unset sentinel (`last_seen_turn == 0`, never cited) is off-stage regardless of the threshold, closing the early-turn (turns 1-2) floor leak the Reviewer flagged. One-conjunct change; no other files touched.

**Tests:** 15/15 story tests green (12 original + 3 rework early-turn cases); roster regression 23/23; `tests/agents/` + party/identity = 1669 passed; ruff clean; pyright clean on the changed file.

**Verifies the Reviewer HIGH finding closed** and the No Silent Fallbacks rule satisfied (unset last_seen_turn no longer silently floored). The over-correction guard test confirms genuinely-recent early-turn NPCs still render full.

**Branch:** feat/75-2-budgeted-npc-working-set (pushed, `ba7ff59`).
**Handoff:** Back through spec-check / verify / review.
## Architect Assessment (spec-check — rework 2026-06-01)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Reviewed the rework diff (`06c4db2..HEAD`, one conjunct in `npc_context.py:90`). The guard `npc.last_seen_turn > 0 and npc.last_seen_turn >= threshold` correctly resolves the Reviewer HIGH finding: `last_seen_turn == 0` is the unset sentinel (interaction starts at 1, monotonic), so a never-seen NPC is now off-stage at all turns including session start. No new drift — the change aligns the implementation to the already-asserted never-seen→off-stage invariant.

**Correctness note:** the `> 0` guard never wrongly excludes a legitimately scene-present NPC — a cited NPC is always stamped `last_seen_turn >= 1`, so present NPCs are unaffected; the over-correction guard test (`test_genuinely_recent_npc_still_full_at_early_turn`) confirms turn-1/turn-2 recent NPCs stay full.

**Decision:** Proceed to verify. No hand-back.
## TEA Assessment (verify — rework 2026-06-01)

**Phase:** finish (rework cycle)
**Status:** GREEN confirmed

**Simplify:** Assessed the rework delta directly (1 file, +7/-1 — a single boolean guard `last_seen_turn > 0` plus an explanatory comment). No reuse, quality, or efficiency surface: no new abstraction, no duplication, no hot-path cost. The full simplify panel (reuse/quality/efficiency) already ran on the complete implementation in the first verify cycle and its results stand (1 fix applied: `_full_npc_line` extraction). Spawning the panel for a one-conjunct guard would be disproportionate.

**Quality checks:** story+roster tests 29/29 green; ruff clean; format clean; pyright clean on the changed file.

**Overall:** simplify: clean (delta); prior verify applied 1 fix.
**Handoff:** To Reviewer (The Merovingian) for re-review of the rework.
## Subagent Results (rework re-review — 2026-06-01)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (15/15 green incl. 3 early-turn tests; ruff+pyright clean) | N/A — confirms HIGH finding CLOSED |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A — confirms guard tightens firewall, no new leak, prior finding closed |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (2 enabled returned, 7 disabled via settings)
**Total findings:** 0 new; prior HIGH finding verified CLOSED

## Reviewer Assessment (rework re-review)

**Verdict:** APPROVED

**Prior HIGH finding — CLOSED.** The guard `npc.last_seen_turn > 0 and npc.last_seen_turn >= threshold` (`npc_context.py:90`) routes the never-seen sentinel (`last_seen_turn=0`) off-stage at all turns including session start (turn 1: `0 > 0` is False → off-stage; turn 2: same). Verified independently by me, reviewer-preflight (3 pinning tests now pass), and reviewer-security (firewall strictly tighter, no new leak).

**No regression / no over-correction:** a cited NPC is always stamped `last_seen_turn >= 1` (interaction starts at 1, monotonic), so the `> 0` guard never wrongly excludes a legitimately-present NPC. `test_genuinely_recent_npc_still_full_at_early_turn` confirms turn-1/turn-2 recent NPCs stay full while only the sentinel drops off-stage.

**Data flow re-traced:** player action → `_build_turn_context` → `build_npc_working_set(current_turn=interaction)` → classification (now sentinel-guarded) → `TurnContext.npc_working_set` → roster renderer → prompt. The defect point (`npc_context.py:90`) is fixed; everything downstream verified clean in the prior review (perception firewall, no-eviction, OTEL span, wiring) and is untouched by this delta.

**Deviation audit:** No new deviations introduced by the rework; the prior `### Reviewer (audit)` stamps stand (all 4 TEA/Dev deviations ACCEPTED). The previously-UNDOCUMENTED early-turn invariant violation is now resolved in code + tests.

**Verified good (≥5):**
- [VERIFIED] never-seen sentinel off-stage at session start — `npc_context.py:90`; tests at current_turn=1 and =2 pass.
- [VERIFIED] present NPCs unaffected — cited NPCs stamped `>=1`; over-correction guard test green.
- [VERIFIED] No Silent Fallbacks satisfied — unset sentinel explicitly guarded, documented in the comment.
- [VERIFIED] perception firewall intact — delta does not touch the renderer; `disposition.attitude().value` band only (prior review).
- [VERIFIED] OTEL span fires unconditionally with per-tier counts — GM-panel lie detector intact.
- [VERIFIED] full suite/regression — 15/15 story, 1669 agents/roster (Dev green run), lint+types clean.

**Handoff:** To SM (Morpheus) for finish-story.

### Reviewer (code review — rework re-review)
- **Resolved:** The prior blocking Gap (never-seen invariant at session start) is CLOSED by the `last_seen_turn > 0` guard; verified by preflight (3 pinning tests green) + security (firewall strictly tighter). No new findings during re-review. *Found/closed by Reviewer during code review.*