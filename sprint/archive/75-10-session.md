---
story_id: "75-10"
jira_key: ""
epic: "75"
workflow: "tdd"
---
# Story 75-10: Wire player-NPC reference signal into the budgeted working-set brief tier (75-2 carryover, ADR-118)

## Story Details
- **ID:** 75-10
- **Epic:** 75 (RAG Retrieval Layer — Restore Accretion, Budgeted Selection, Universal Retrieval Design)
- **Jira Key:** (none — Jira disabled for this project)
- **Workflow:** tdd (phased)
- **Repo:** sidequest-server
- **Base Branch:** develop
- **Branch:** feat/75-10-player-npc-reference-signal-brief-tier
- **Stack Parent:** 75-5 (done)

## Story Context

**Type:** Feature completion / ADR-118 fill wiring

This is a 75-2 carryover story, completing the work deferred by the TEA and Dev assessments in `sprint/archive/75-2-session.md`. Story 75-2 (port budgeted NPC working-set selection) implemented the three-tier NPC roster (full / brief / compact) and is reference-implemented but **unfinished**: `_build_turn_context` passes `player_referenced_npcs=None`, so off-stage NPCs always collapse to COMPACT (name only) in production, never BRIEF (name+role), even when the player just referenced them.

**Problem Statement:**

`build_npc_working_set(snapshot, *, current_turn, player_referenced_npcs=None, recency_window=2)` in `sidequest/agents/npc_context.py` already:
- Implements a three-tier NPC roster (full / brief / compact)
- Is unit-tested for all three tiers
- Is reachable via the API when any caller passes `player_referenced_npcs`

**But in production:**
- `_build_turn_context` (the real per-turn wiring point) passes `player_referenced_npcs=None`
- Referenced off-stage NPCs render COMPACT (name only), never BRIEF (name+role)
- The brief tier is dead code in production

**Goal:**

Supply a real per-turn "did the player reference any NPC" signal at `_build_turn_context` time so referenced off-stage NPCs render BRIEF instead of COMPACT. Story 75-5 (ADR-118 fill orchestration, `retrieve_turn_context`) is now landed — that is the natural wiring point.

## Key Seams and Constraints

Per the 75-2 archive and ADR-118:

1. **Signal source must be player input pre-turn, NOT narrator output post-turn.** Existing `_apply_npc_mentions` (narration_apply.py) reads narrator output post-turn — do NOT reuse it. The reference signal must arrive at `_build_turn_context` time (session_helpers.py / session_handler.py).

2. **ADR-118's `retrieve_turn_context` (75-5) is the fill orchestration.** Check whether the per-turn referenced-entity set can be sourced from there rather than building a new extractor.

3. **Per-entity reference PROMOTION is out of scope.** A referenced off-stage NPC stays BRIEF (not promoted to full). That is ADR-118 fill (75-5). This story is brief-vs-compact only.

4. **Scene-present FULL floor is unchanged (reference-independent).** Referencing or not referencing must never demote a scene-present NPC. Scene-present NPCs (`last_seen_turn >= current_turn - 2`) always render FULL regardless of player reference.

## Acceptance Criteria

1. **Signal integration:** `_build_turn_context` (production turn path) supplies a real `player_referenced_npcs` set derived from player input, replacing the hardcoded `None`.

2. **Brief tier fires in production:** When a player references an off-stage NPC, that NPC renders in the BRIEF tier (name+role), not compact — verified against the real turn-build path, not just a synthetic unit call.

3. **Floor is reference-independent:** The scene-present FULL floor (NPCs with `last_seen_turn >= current_turn - recency_window`) remains unchanged and reference-agnostic — no reference logic affects scene-present NPCs.

4. **OTEL observability:** SPAN_NPC_WORKING_SET emits `references_present=true` and `brief_count>0` on a production-path turn where the player references an off-stage NPC. (Per the OTEL Observability Principle — the GM panel must be able to prove the brief tier fired.)

5. **Wiring test:** At least one integration test driving the real `_build_turn_context` path (not a direct `build_npc_working_set` unit call) proves the signal flows end-to-end.

## Workflow Tracking

**Workflow:** tdd (phased) — setup → red → green → spec-check → verify → review → spec-reconcile → finish
**Phase:** finish (in progress)
**Phase Started:** 2026-06-03T22:06:19Z (NOW)

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-03 | 2026-06-03T21:36:30Z | 21h 36m |
| red | 2026-06-03T21:36:30Z | 2026-06-03T21:48:48Z | 12m 18s |
| green | 2026-06-03T21:48:48Z | 2026-06-03T21:55:54Z | 7m 6s |
| spec-check | 2026-06-03T21:55:54Z | 2026-06-03T21:57:36Z | 1m 42s |
| verify | 2026-06-03T21:57:36Z | 2026-06-03T22:00:26Z | 2m 50s |
| review | 2026-06-03T22:00:26Z | 2026-06-03T22:05:25Z | 4m 59s |
| spec-reconcile | 2026-06-03T22:05:25Z | 2026-06-03T22:06:19Z | 54s |
| finish | 2026-06-03T22:06:19Z | - | - |

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Improvement** (non-blocking): The working set is built TWICE per production turn — once in `retrieve_turn_context` (`retrieval_orchestration.py:180`) for budget accounting + fill dedup, and again in `_build_turn_context` (`session_helpers.py:1241`) for the prompt-bound `npc_working_set`, both with `player_referenced_npcs=None`. Affects `sidequest/server/session_helpers.py` (consume `entity_retrieval.floor` when present, so the set is built once with the signal). *Found by TEA during test design.*
- **Question** (non-blocking): Pool-member references — a player can name an `NpcPoolMember` (identity-only, no recency), and they belong to the off-stage tier. The derivation must match against `snapshot.npc_pool` names too, not only `snapshot.npcs`. Pinned by `test_referenced_pool_member_carried_brief`. Affects the new derivation helper (roster source = `npcs` ∪ `npc_pool`). *Found by TEA during test design.*
- **Gap** (non-blocking): 75-2's wiring test (`test_npc_working_set_budgeting.py::test_budgeting_wired_into_build_turn_context`) deliberately asserts ONLY the floor and documents the brief-vs-compact signal as "the still-open question." 75-10 closes it; Dev must keep that test green (the `entity_retrieval is None` recompute path it exercises is unchanged). *Found by TEA during test design.*

### Dev (implementation)

- No upstream findings during implementation. (TEA's two findings resolved: the double-computation is removed — `_build_turn_context` now consumes `entity_retrieval.floor`; pool-member references are matched — roster source is `npcs ∪ npc_pool`; the 75-2 floor-only wiring test stays green via the unchanged `entity_retrieval is None` recompute path.)

### TEA (verify)

- **Improvement** (non-blocking): The word-boundary regex idiom `re.search(rf"\b{re.escape(name)}\b", ...)` now lives in two places — `agents/npc_context.py::player_referenced_npcs_from_action` (case-insensitive, NPC/pool) and `server/visibility_classifier.py:80::_find_pc_in_text` (case-sensitive, PC). A future shared `_matches_word_boundary(name, text, *, case_sensitive)` util could consolidate the idiom IF a third caller appears; not worth the cross-module dependency inversion today. Affects nothing (advisory). *Found by TEA during test verification.*

### Reviewer (code review)

- **Improvement** (non-blocking): Multi-word NPC names separated by multiple spaces/newlines in player action text won't match (`re.escape` escapes the internal space to a literal single space, not `\s+`). Fails safe (off-stage stays compact). Affects `sidequest/agents/npc_context.py` (`player_referenced_npcs_from_action` — could normalize whitespace or use `\s+` between tokens IF it ever bites). Not worth doing now. *Found by Reviewer during code review.*

## Design Deviations

No design deviations at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Signal derived at the retrieval delegate; `_build_turn_context` consumes `entity_retrieval.floor`**
  - Spec source: context-story-75-10.md, AC-1 ("`_build_turn_context` … supplies a real `player_referenced_npcs` set derived from player input, replacing the hardcoded `None`")
  - Spec text: AC-1 literally locates the supply at `_build_turn_context`.
  - Implementation: Tests pin the derivation in the production retrieval delegate (`handler._retrieve_entities_for_turn` → `retrieve_for_turn` → `retrieve_turn_context`, which ALREADY takes `action_text` and a `player_referenced_npcs` param), with `RetrievedEntities.floor` carrying the tiered set; `_build_turn_context` consumes `entity_retrieval.floor` for `npc_working_set` rather than gaining a new `action` param and recomputing. The `entity_retrieval is None` legacy path keeps its reference-free recompute (75-2 floor-only wiring test stays green).
  - Rationale: the action text already lives at the retrieval delegate; deriving there reuses an existing param (Don't Reinvent) and removes the wasteful double-computation of the working set (today it is built once in `retrieve_turn_context` and again at `session_helpers.py:1241`). AC-1's intent — "the production turn path supplies a real set, not `None`" — is satisfied; only the exact module is pinned.
  - Severity: minor
  - Forward impact: Dev should implement consume-floor + upstream derivation, NOT a new `action_text` param on `_build_turn_context`. If Dev prefers the param approach, the AC2/AC3 tests (which call `_build_turn_context(sd, entity_retrieval=result)` without an action) must still observe the brief tier — i.e. the floor must already carry it.

- **Matching semantics pinned: case-insensitive + word-bounded**
  - Spec source: context-story-75-10.md, AC-1/AC-2 (signal "derived from player input"); strategy unspecified.
  - Spec text: the ACs do not prescribe how the action text maps to NPC names.
  - Implementation: `test_reference_match_is_case_insensitive` requires a lower-cased mention to match; `test_reference_does_not_false_match_name_inside_unrelated_word` requires "Art" NOT to match inside "start" (word boundary).
  - Rationale: case-sensitivity would make the feature near-useless in natural play; substring matching would inflate the brief tier the floor exists to bound (budget integrity, ADR-118). A `\b`-bounded case-folded match satisfies both.
  - Severity: minor
  - Forward impact: Dev must use word-boundary (regex `\b` / tokenization), not a naive `name.lower() in action.lower()`. Possessives ("Joran's") still match under `\bJoran\b` and remain in scope as a match.

### Dev (implementation)

- Implemented exactly to TEA's two pinned contracts (derivation locus = retrieval delegate; matching = case-folded + `\b` word-bounded). No deviations from spec.
- **Note on the brief-tier toggle being turn-level, not per-entity.** `build_npc_working_set` reads only `bool(player_referenced_npcs)` — so ANY referenced roster NPC flips the WHOLE off-stage tier to brief (the faithful 75-2/Rust design, Operator-ruled 2026-05-31). The derivation helper returns the matched-name set, but its contents beyond emptiness don't change tiering. This is the existing 75-2 contract, not a 75-10 deviation; per-entity promotion remains out of scope.

### Reviewer (audit)

- **TEA: Signal derived at the retrieval delegate; `_build_turn_context` consumes `entity_retrieval.floor`** → ✓ ACCEPTED by Reviewer: the better design. Reuses `retrieve_turn_context`'s existing `action_text`+`player_referenced_npcs` params (Don't Reinvent), removes a per-turn double-computation, and meets AC1's intent ("production path supplies a real set, not `None`"). Architect concurred (spec-check, Option A). The `entity_retrieval is None` recompute is correctly preserved for the dice-replay/error/fixture callers (`session_helpers.py:1257-1262`).
- **TEA: Matching semantics pinned: case-insensitive + word-bounded** → ✓ ACCEPTED by Reviewer: case-folding is required for natural play; `\b` word-bounding protects the budget the floor exists to maintain (prevents "Art" ⊂ "start" false-positives). `re.escape` correctly neutralizes regex metacharacters in names. Verified at `npc_context.py:85`.
- **Dev: Note on turn-level (not per-entity) toggle** → ✓ ACCEPTED by Reviewer: accurate characterization of the existing 75-2 `bool(player_referenced_npcs)` contract; per-entity promotion is correctly out of scope.
- **No undocumented deviations found.** The code matches the logged contracts exactly.

### Architect (reconcile)

**Existing-entry verification (all entries accurate — no corrections needed):**
- **TEA #1 (derivation locus / consume-floor)** — all 6 fields present. Spec source `context-story-75-10.md` exists (`sprint/context/`); AC-1 quote is accurate. Implementation description matches the code: derivation in `universal_retrieval.retrieve_for_turn` (`:69`), consume-floor in `session_helpers._build_turn_context` (`:1255-1262`). Forward impact accurate — Dev implemented consume-floor, not a new `_build_turn_context` param. Reviewer stamped ACCEPTED. ✓
- **TEA #2 (matching semantics: case-insensitive + word-bounded)** — all 6 fields present; accurate. The ACs indeed leave matching strategy unspecified; the code implements `\b`-bounded `re.IGNORECASE` over `re.escape(name)` (`npc_context.py:85`). Forward impact accurate. Reviewer stamped ACCEPTED. ✓
- **Dev (turn-level toggle note)** — accurate: `build_npc_working_set` reads only `bool(player_referenced_npcs)`; per-entity promotion correctly out of scope per story constraint #3. ✓

**Missed deviations:** No additional deviations found. The implementation is faithful to story scope (no per-entity promotion; floor reference-independent; signal from player input pre-turn). The only spec-vs-code nuance — AC-1 literally naming `_build_turn_context` as the supply site while the code derives upstream and consumes `entity_retrieval.floor` — is already captured by TEA #1 and Option-A resolved in spec-check.

**AC deferral check:** No ACs were DEFERRED or DESCOPED — all 5 (signal integration, brief-fires-in-prod, floor-independence, OTEL, wiring test) are DONE and verified GREEN. No-op.

## Sm Assessment

**Setup complete — routing to TEA (Igor) for RED phase.**

2pt **75-2 carryover** (ADR-118). Technical approach is fully pre-documented in
`sprint/archive/75-2-session.md` (Dev deviation + two TEA findings), so I created
context solo — no architect tandem; right-sized ceremony for a well-spec'd
wiring story.

**Gates:** dependency 75-5 (done) is the ADR-118 fill orchestration
`retrieve_turn_context` and the natural signal source. Merge gate clear (only
open PR #615 is a draft). Jira disabled for this project (explicitly skipped).

**The work in one line:** `build_npc_working_set`'s brief tier is implemented,
tested, and reachable but never fires in prod because `_build_turn_context`
passes `player_referenced_npcs=None`. Wire a real player-input-derived reference
signal at that seam so referenced off-stage NPCs render brief (name+role), not
compact (name only).

**TEA watch-points for RED:**
- AC5 is load-bearing — drive the **real** `_build_turn_context` production path,
  not a synthetic `build_npc_working_set` unit call. The bug is the prod caller;
  a unit test alone won't catch a regression.
- AC4 OTEL — assert `SPAN_NPC_WORKING_SET` emits `references_present=true` and
  `brief_count>0` on that prod-path turn (today both false/zero in prod).
- AC3 floor — pin that scene-present NPCs stay full regardless of reference.
- Signal source — confirm whether 75-5's `retrieve_turn_context` already surfaces
  a usable player-reference set before building any new extractor (context
  Assumptions: wrong assumption here = Design Deviation back to SM).
- Out of scope: per-entity reference *promotion* (off-stage → full).

Context: `sprint/context/context-story-75-10.md` (validated).

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** Net-new signal wiring through a production path — needs behavioral + OTEL coverage.

**Test Files:**
- `tests/server/test_75_10_player_npc_reference_signal.py` — 8 tests; all drive the LIVE production delegate `handler._retrieve_entities_for_turn(sd, action)` (autouse daemon-down guard computes the floor offline) and assert on observed behaviour: `RetrievedEntities.floor`, `TurnContext.npc_working_set`, and the `npc.working_set` OTEL span. No source-text grepping (server CLAUDE.md "No Source-Text Wiring Tests").

**Tests Written:** 8 tests covering 5 ACs (RED: 6 fail on clean assertions, GREEN: 2 regression guards pass).

| Test | AC | RED status |
|------|-----|-----------|
| `test_referenced_offstage_npc_carried_brief_in_retrieval_floor` | AC1/AC5 | FAILING |
| `test_referenced_pool_member_carried_brief` | AC1 (pool source) | FAILING |
| `test_referenced_offstage_npc_renders_brief_in_turn_context` | AC2 | FAILING |
| `test_scene_present_floor_holds_when_offstage_npc_referenced` | AC3 | FAILING |
| `test_working_set_span_records_reference_on_production_path` | AC4 (OTEL) | FAILING |
| `test_reference_match_is_case_insensitive` | AC1 (matching) | FAILING |
| `test_unreferenced_offstage_npc_stays_compact` | negative guard | passing (green-on-develop) |
| `test_reference_does_not_false_match_name_inside_unrelated_word` | budget guard | passing (green-on-develop) |

**Status:** RED confirmed (`75-10-tea-red` via testing-runner) — 6 FAILED / 2 PASSED, no import/collection/fixture errors. Matches the intended split.

### Rule Coverage

| Rule (lang-review python.md) | Test(s) / handling | Status |
|------|---------|--------|
| #6 Test quality (no vacuous asserts) | All 8 — specific-value asserts (set equality, membership, span-attr value+bool), no `assert True`/truthy-only/skips | self-checked clean |
| #9 Async/await | All 8 `async def` await the real delegate; `asyncio_mode=auto` | clean |
| Project: No Source-Text Wiring Tests | All assertions behavioral (delegate return + span); zero `read_text()`/source-grep | enforced |
| Project: Every Suite Needs a Wiring Test | Tests 1–8 all enter via `handler._retrieve_entities_for_turn` (the live prod seam) | enforced |
| Project: OTEL Observability | AC4 test asserts `npc.working_set` span `references_present=True` + `brief_count>0` | enforced |

**Rules checked:** test-design-applicable rules (#6, #9) + the 3 load-bearing project rules have coverage.
**Self-check:** 0 vacuous tests found.

**Implementation guidance for Dev (Ponder):**
- Derive `player_referenced_npcs` from `action`/`action_text` where it already lives — `retrieve_for_turn` (`universal_retrieval.py:59`) currently calls `retrieve_turn_context(..., current_turn=...)` with no signal; add the derivation and pass it through. Roster source = `snapshot.npcs` ∪ `snapshot.npc_pool` names. Matching = case-folded, word-bounded (`\b`).
- Make `_build_turn_context` consume `entity_retrieval.floor` for `npc_working_set` when `entity_retrieval is not None` (removes the `session_helpers.py:1241` double-compute with `None`); keep the reference-free recompute only for the `entity_retrieval is None` legacy/fixture path so `test_npc_working_set_budgeting.py` stays green.
- Out of scope (do NOT implement): per-entity reference *promotion* (referenced off-stage → full).
- See `### TEA (test design)` deviations for the two pinned contracts (derivation locus; matching semantics).

**Handoff:** To Dev (Ponder Stibbons) for GREEN.

---
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/agents/npc_context.py` — new `player_referenced_npcs_from_action(snapshot, action_text)` helper (case-folded, `\b` word-bounded match over `snapshot.npcs ∪ snapshot.npc_pool`); `import re` added. Pure function next to `build_npc_working_set` it feeds.
- `sidequest/server/dispatch/universal_retrieval.py` — `retrieve_for_turn` now derives the signal from the player action and passes `player_referenced_npcs=` into `retrieve_turn_context`, so `RetrievedEntities.floor` carries the brief tier in production.
- `sidequest/server/session_helpers.py` — `_build_turn_context` consumes `entity_retrieval.floor` for `npc_working_set` when `entity_retrieval is not None`; the reference-free recompute survives only for the `entity_retrieval is None` legacy/fixture path (dice-replay/error turns, unit tests). Removes the per-turn double-computation TEA flagged.
- `tests/server/test_75_10_player_npc_reference_signal.py` — whitespace-only `ruff format` reflow (TEA's RED file; no logic change).

**Approach:** Implemented exactly to TEA's two pinned contracts. The action text already lived at the retrieval delegate (`retrieve_turn_context` already accepted `action_text` + a `player_referenced_npcs` param), so the wiring is one derivation call + one consume-floor swap — no new params on `_build_turn_context`, no new extractor (Don't Reinvent). The two real player-action paths (`player_action.py:498` main turn, `websocket_session_handler.py:2584` opening) both pass `entity_retrieval`, so the brief tier reaches the prompt on every player turn; dice-replay/error turns keep the reference-free recompute (no fresh player reference to honor there).

**Tests:** 8/8 story tests GREEN (`75-10-dev-green`). Full server unit suite GREEN — **8,869 passed / 0 failed / 1,422 skipped** (`75-10-dev-green-fullsuite`), no bystander regression from the hot-path edit. Neighbor suites (75-2 budgeting, 75-5 orchestration, 75-7/75-8 universal retrieval) all green. `ruff check` + `ruff format --check` clean on all changed files.

**OTEL:** No new span needed — `SPAN_NPC_WORKING_SET` ("npc.working_set") already carries `references_present` / `brief_count`; the fix makes them fire truthfully in production (`references_present=True` / `brief_count>0` when a player names an off-stage NPC). Verified by `test_working_set_span_records_reference_on_production_path`.

**Branch:** feat/75-10-player-npc-reference-signal-brief-tier (pushed)

**Handoff:** To verify (Igor) — simplify + quality-pass.

---
## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 1 (documented, Option-A resolved — not drift requiring a Dev hand-back)

- **AC1 derivation locus — signal derived at the retrieval delegate, not literally inside `_build_turn_context`** (Ambiguous spec — Architectural, Minor)
  - Spec: AC1 says "`_build_turn_context` (production turn path) supplies a real `player_referenced_npcs` set … replacing the hardcoded `None`."
  - Code: the set is derived in `retrieve_for_turn` via `player_referenced_npcs_from_action(snapshot, action)` and threaded into `retrieve_turn_context` → `build_npc_working_set`; `_build_turn_context` consumes `entity_retrieval.floor`. The hardcoded `None` survives only on the `entity_retrieval is None` legacy/fixture path.
  - Recommendation: **A — Update spec.** The implementation reveals the better approach: the action text already lives at the retrieval delegate, so deriving there reuses an existing param and removes a per-turn double-computation of the working set. AC1's intent — "the production turn path supplies a real set, not `None`" — is fully met. Already recorded as the `### TEA (test design)` deviation; no further action.

**Substantive AC checks (code read against spec):**
- AC2 — brief tier reaches `TurnContext.npc_working_set` via `entity_retrieval.floor` on both real player-action paths (`player_action.py:498`, `websocket_session_handler.py:2584`, both pass `entity_retrieval`). Aligned.
- AC3 — `build_npc_working_set` floor logic is byte-unchanged; the floor stays reference-independent. The consumed `entity_retrieval.floor` is built with the same `snapshot` + `current_turn=interaction` + default window `_build_turn_context` would have used, so the only delta is the signal. Aligned.
- AC4 — `SPAN_NPC_WORKING_SET` now fires `references_present=True`/`brief_count>0` truthfully in prod (existing span, no schema change). Aligned.
- AC5 — all 8 tests enter via the live `handler._retrieve_entities_for_turn` delegate. Aligned.

**Architectural notes (no action):**
- Reuse-first: zero new infrastructure; one pure helper + an existing param. The double-computation removal is a real improvement, not scope creep.
- `re.escape` + `\b` correctly guards regex metacharacters and substring false-matches; per-call regex compile is O(roster) and negligible at the bounded roster sizes ADR-118 exists to maintain. Trivial — not worth pre-compiling.

**Decision:** Proceed to review (verify phase next — Igor's simplify + quality-pass).

---
## TEA Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (3 production + the story test file)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | LOW-confidence: word-boundary regex idiom `\b{re.escape(name)}\b` also at `visibility_classifier.py:80` (`_find_pc_in_text`) — could share a `_matches_word_boundary` helper |
| simplify-quality | clean | none |
| simplify-efficiency | clean | none |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 1 low-confidence observation (below)
**Reverted:** 0

**Low-confidence observation (NOT applied — judgment call):** The reuse teammate itself rated this low confidence. The two sites differ in a load-bearing way: `visibility_classifier._find_pc_in_text` is **case-sensitive**, runs **post-narration** over **PC** names; `player_referenced_npcs_from_action` is **case-insensitive**, runs **pre-narration** over **NPC + pool** names. Extracting a shared helper would invert a cross-module dependency (`server.visibility_classifier` ↔ `agents.npc_context`) to consolidate a single-line regex idiom that carries *different* semantics — consolidation that obscures intent more than it clarifies. This is the same call 75-2's review made when it declined the symmetric `_name_of` cross-module dedup (session `### Reviewer (audit)`, 2026-06-01). Left as-is.

**Quality Checks:** All passing — `ruff check` + `ruff format --check` clean on all 4 changed files (Dev-verified); full server unit suite GREEN (8,869 passed / 0 failed) at green-phase; no code changed in verify, so the tree is unchanged from the pushed GREEN commit.

### Delivery Findings Capture

(see `### TEA (verify)` under Delivery Findings)

**Handoff:** To Reviewer (Granny Weatherwax) for code review.

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (8/8 tests green, ruff clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [EDGE]) |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [SILENT]) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [TEST]) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [DOC]) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [TYPE]) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [SEC]) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [SIMPLE]) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings — reviewer-assessed (see [RULE]) |

**All received:** Yes (preflight returned clean; specialists 2-9 disabled via `workflow.reviewer_subagents` — their domains assessed by the Reviewer directly, the change being a 3-edit surgical diff)
**Total findings:** 0 confirmed blocking, 2 LOW (non-blocking), 7 VERIFIED-good

### Rule Compliance (Python lang-review checklist — exhaustive over the diff)

The diff adds ONE public function (`player_referenced_npcs_from_action`), one import + one kwarg pass-through (`universal_retrieval.py`), and one conditional expression (`session_helpers.py`). Enumerated against every applicable rule:

| Rule | Instances in diff | Verdict |
|------|-------------------|---------|
| #1 silent exception swallowing | no `try/except` added anywhere | compliant |
| #2 mutable default arguments | `player_referenced_npcs_from_action(snapshot, action_text)` — no defaults | compliant |
| #3 type annotations at boundaries | new public fn fully annotated `(GameSnapshot, str) -> set[str]` | compliant |
| #4 logging coverage/correctness | pure fn, no error path needing a log; no new log calls | N/A |
| #6 test quality | story tests behavioral, specific-value asserts (verified RED + verify) | compliant |
| #9 async pitfalls | helper is sync (pure CPU regex over short player text) called inside async `retrieve_for_turn` — non-blocking, no I/O, no `asyncio.to_thread` needed | compliant |
| #10 import hygiene | new `from sidequest.agents.npc_context import …` in `universal_retrieval.py` — NOT a new cycle (`retrieval_orchestration.py:37` already imports the same module); full suite 8,869 green confirms no ImportError | compliant |
| #11 input validation at boundaries | `action_text` guarded for empty/whitespace (`npc_context.py:78-79`); player text is the regex *haystack*, never the *pattern* — no injection | compliant |
| Rules #5 (paths), #7 (resource leaks), #8 (deserialization), #12 (deps) | no matching constructs in diff | N/A |

### Devil's Advocate

Let me argue this code is broken. **First, the consume-floor swap.** `_build_turn_context` now trusts `entity_retrieval.floor` instead of recomputing. What if that floor was built against a *different* snapshot or turn number than `_build_turn_context` sees? Then the roster the narrator gets would be stale. I traced it: `retrieve_for_turn` builds the floor with `current_turn=sd.snapshot.turn_manager.interaction` over `sd.snapshot`, and the production callers (`player_action.py:498`, `websocket_session_handler.py:2584`) call `_retrieve_entities_for_turn(sd, action)` then `_build_turn_context(sd, …)` back-to-back with no interaction increment and the *same* `sd.snapshot` object — so the floor is identical to what the recompute would have produced, save the signal. The 8,869-test suite (including the e2e capstone that drives both functions) is green. Not broken.

**Second, the matcher.** A malicious or confused player. Could player text inject a regex bomb? No — player text is the *haystack* passed to `re.search(pattern, action_text)`; the *pattern* is `\b{re.escape(name)}\b`, built from roster names with metacharacters escaped. No ReDoS surface (anchors + literal, no quantifiers/alternation). Could a name with weird characters break `re.escape`? `re.escape` accepts any str and never raises. Could a never-ending action_text hang the search? It's a linear scan per name; player actions are short, rosters bounded by ADR-118's premise. **Third, false matches that inflate the budget.** "I start the forge" must not flip the off-stage tier via NPC "Art" — `\b` blocks the substring; tested and green. The inverse over-correction: NPC "Arthur" vs action "art" — `\bArt\b` won't match inside "Arthur" either; correct. **Fourth, a real gap I'll concede:** a *multi-word* name ("Captain Carrot") whose tokens are separated by **multiple** spaces or a newline in the player text won't match — `re.escape` turns the internal space into a literal single space, not `\s+`. A player typing "Captain  Carrot" (double space) gets no brief promotion. This is LOW: rare in natural typing, fails *safe* (off-stage stays compact — the floor and existing behavior are untouched), and is trivially fixable later if it ever bites. It does not break any AC or test. **Fifth, the empty-name guard:** an NPC with a blank name is skipped (`if not name: continue`) — without it, `\b\b` would match everywhere and flip the tier spuriously. Good defensive code. Nothing here rises to blocking.

## Reviewer Assessment

**Verdict:** APPROVED

**Observations (9 — no rubber-stamp):**
1. **[VERIFIED]** Data flow traced end-to-end: player `action` → `retrieve_for_turn` → `player_referenced_npcs_from_action(sd.snapshot, action)` → `retrieve_turn_context(player_referenced_npcs=…)` → `build_npc_working_set` brief tier → `RetrievedEntities.floor` → `_build_turn_context` `npc_working_set` → narrator prompt + `npc.working_set` span. Evidence: `universal_retrieval.py:69`, `session_helpers.py:1255-1262`.
2. **[VERIFIED]** Consume-floor is desync-safe — `entity_retrieval.floor` is built with the same `sd.snapshot` + `current_turn` + default window `_build_turn_context` uses, and `RetrievedEntities.floor` is always a non-None `NpcWorkingSet` (built before the daemon call, `retrieve_turn_context` never raises). Evidence: `retrieval_orchestration.py:180`, `session_helpers.py:1255`.
3. **[EDGE]** (specialist disabled; reviewer-assessed) Boundary guards present: empty/whitespace action → `set()` (`npc_context.py:78-79`); empty NPC name → skipped (`:84`); substring false-match blocked by `\b` (tested `test_reference_does_not_false_match_name_inside_unrelated_word`). Unicode names match (`\w`/IGNORECASE are Unicode-aware in py3) — important for conlang NPCs.
4. **[SILENT]** (disabled; reviewer-assessed) No swallowed errors / silent fallbacks. The helper is pure and total; the consume-floor branch is explicit (`if entity_retrieval is not None`), and the `None` path is documented, not a silent default. No `except: pass`.
5. **[SEC]** (disabled; reviewer-assessed) No injection / ReDoS — player text is the search *subject*, names are the *pattern* via `re.escape` (`npc_context.py:85`), anchors-only, no quantifiers. Perception firewall intact: derivation returns only roster names; brief-tier rendering (firewall-checked in 75-2) is unchanged — no disposition/secret leak.
6. **[TYPE]** (disabled; reviewer-assessed) Fully-typed `(GameSnapshot, str) -> set[str]`, matching `build_npc_working_set`'s `set[str] | None` param. Real model types throughout; `_name_of` reused for the `Npc | NpcPoolMember` union.
7. **[TEST]** (disabled; reviewer-assessed) 8 behavioral tests drive the live `handler._retrieve_entities_for_turn` delegate (no source-grep wiring); RED→GREEN confirmed; OTEL span assertion proves the GM-panel signal. Meaningful asserts, no vacuity.
8. **[SIMPLE]** (disabled; reviewer-assessed) Minimal — one pure helper, one kwarg, one ternary that *removes* a double-computation. No over-engineering. **[LOW]** word-boundary idiom now duplicated with `visibility_classifier.py:80` (different case-sensitivity/source/phase) — correctly declined for dedup in verify; not worth a cross-module dependency inversion.
9. **[DOC]** (disabled; reviewer-assessed) Docstrings accurate and load-bearing; the `session_helpers.py` comment correctly explains the consume-floor rationale and the surviving `None` legacy path. No stale comments. **[RULE]** (disabled; reviewer-assessed) Full Python lang-review enumeration above — all applicable rules compliant.

**[LOW] (non-blocking, noted not fixed):** multi-word NPC names separated by multiple spaces/newlines in player text won't match (`re.escape` → literal single space, not `\s+`). Fails safe (off-stage stays compact); rare in natural typing; no AC/test affected.

**Data flow traced:** player action → derivation → floor → TurnContext.npc_working_set → narrator prompt (safe — see obs. 1-2).
**Pattern observed:** "derive the signal where the input already lives, consume it downstream" — clean, removes duplication, follows the existing `retrieve_turn_context` seam. `universal_retrieval.py:69`.
**Error handling:** total pure function + explicit conditional; no failure path to mishandle. `npc_context.py:78-87`.

No Critical/High/Medium findings. Two LOW observations, both non-blocking. The work is correctly wired across both real player-turn paths, OTEL-truthful, fully tested, and faithful to the logged contracts.

**Handoff:** To SM for finish-story.