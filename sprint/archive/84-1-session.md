---
story_id: "84-1"
jira_key: ""
epic: "84"
workflow: "tdd"
---
# Story 84-1: WI-1 Unified pertinence scorer + present-scene invariant + drama-gated embed (supersedes ADR-118 §D4)

## Story Details
- **ID:** 84-1
- **Jira Key:** (none — Jira disabled)
- **Workflow:** tdd
- **Epic:** 84 — ADR-118 Amendment — Unified Pertinence Scorer & Tiered Forgetting
- **Points:** 5
- **Repos:** sidequest-server
- **Stack Parent:** none
- **Branch:** feat/84-1-unified-pertinence-scorer

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-06-05T06:17:59Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T06:17:59Z | - | - |

## Story Summary

**WI-1** implements the unified pertinence scorer from the ADR-118 amendment (§A1), superseding the original ADR-118 §D4 floor/fill split. This is the foundation story for Epic 84 — all other WI-stories (WI-2 through WI-6) depend on it.

### Key Requirements

1. **Unified pertinence score** (A1): Replace the binary floor + similarity fill with one weighted score:
   ```
   score(card) = w_mention·mention(card, action, aliases)
               + w_location·here(card, snapshot)
               + w_recency·decay(card.last_seen, now)
               + w_sim·cosine(embed(action), card)
   ```
   Rank all candidates by score; select cards until the per-turn token budget is exhausted.

2. **Present-scene hard invariant** (A1): A card for an entity the player is physically engaging this turn cannot be budgeted out — full stop. This is a *hard constraint* on top of the ranking, not an emergent property of weights.

3. **Drama-gated embedding** (A1 — SOUL *Cost Scales with Drama*): The `w_sim·cosine` term is expensive (requires daemon embed). Compute it **only when structured signals come back thin** — i.e., when the action named nothing and the party is nowhere specific. "I attack Borin" resolves on mention + location; the embed is **skipped**.

4. **Per-type signal applicability** (A1): Each entity type declares *which* of the four signals apply to it. The *weight* of each signal it uses is a single global tuning vector — one knob, no nonsense terms.

5. **Supersedes ADR-118 §D4**: The live §D4 mechanism (floor/fill split in `retrieve_turn_context`) is replaced. The core layer (D1–D3, D5) remains live and unchanged until this lands.

### Acceptance Criteria

- [ ] Define a `PertinenceScore` data structure capturing the four signals (mention, here, recency, sim) and the combined score
- [ ] Implement the weighted-sum formula with configurable global weights
- [ ] Implement signal applicability matrix per entity type (e.g., `here` applies to NPCs, not lore)
- [ ] Implement the hard invariant for present-scene entities — budget cannot exclude them
- [ ] Implement drama-gating: skip embedding when `mention + here` scores are sufficient (logic to be specified in TDD red phase)
- [ ] Update `retrieve_turn_context` orchestration to use the new scorer instead of the §D4 floor/fill split
- [ ] All acceptance criteria have failing test coverage before GREEN phase
- [ ] Tree clean, no debug code, correct branch at GREEN gate
- [ ] OTEL integration test passes (story 84-4 ships alongside to verify the rewrite)

### Technical Notes

- **Replaces:** `sidequest-server/sidequest/game/retrieval_orchestration.py` `retrieve_turn_context` orchestration and the floor/fill split logic
- **Touches:** `sidequest-server/sidequest/game/entity_card.py` (card projectors), `dispatch/universal_retrieval.py` (retrieval handler)
- **Related:** ADR-118 amendment (§A1–A5), ADR-048 (Lore RAG — reuses embedding worker), ADR-031 (OTEL observability)
- **Sequencing:** This is WI-1, the foundation story. Stories 84-2 through 84-4 stack on top; 84-5 through 84-6 are deferred (p3).
- **Blocker cleared:** Epic 76 (entity index population) is confirmed merged — 76-6 + 76-7 landed, so the index is ready for retrieval on day one.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Net-new scorer + behavioral rewrite of a live retrieval path — every AC needs failing coverage.

**Test Files:**
- `sidequest-server/tests/game/test_pertinence_scorer.py` — pure scorer unit/contract spec (weights ordering, weighted sum, per-type applicability matrix, present-scene flag + `select_within_budget` invariant, drama-gate predicate, `embed_used`/`sim=None` semantics). 14 tests.
- `sidequest-server/tests/game/test_unified_retrieval_supersedes_d4.py` — orchestration-level supersession of §D4 (drama-gate skips/runs the daemon embed end-to-end, per-card `card_scores` exposed, `RetrievedEntities` back-compat, present-scene invariant under a 1-token budget). 5 tests.
- `sidequest-server/tests/game/test_pertinence_wiring.py` — production WIRING via real `WebSocketSessionHandler` turn: `retrieval.universal` span fires + named-action embed is skipped on the live path + `retrieval.embed_skipped=True` span attribute. 1 test.

**Tests Written:** 20 tests covering AC-1…AC-6 (AC-7 is the GREEN-gate quality check).
**Status:** RED — 19 failing, 1 intentionally green.
- 15 `ModuleNotFoundError` (`sidequest.game.pertinence` absent), 2 `AttributeError` (`RetrievedEntities.embed_skipped` absent), 1 orchestration `AttributeError` chained off the missing module, 1 wiring `AssertionError` (named action embedded anyway — drama-gate absent on live path; the `retrieval.universal` span DID fire, proving the path is reached).
- The 1 green test (`test_result_still_exposes_consumer_fields`) is a deliberate **regression guard** on the public `RetrievedEntities` shape: it must pass against both the old §D4 code and the new scorer so Dev cannot break the renderer/watcher consumers during the rewrite.

**Production call path the wiring test pins (where the scorer plugs in):**
`websocket_session_handler.py:3170 _retrieve_entities_for_turn` → `server/dispatch/universal_retrieval.py:60 retrieve_for_turn` → `game/retrieval_orchestration.py:159 retrieve_turn_context`.

**Run command (OTEL-sensitive — serial):**
`uv run pytest -n0 tests/game/test_pertinence_scorer.py tests/game/test_unified_retrieval_supersedes_d4.py tests/game/test_pertinence_wiring.py`

**Handoff:** To Dev for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/pertinence.py` (NEW) — pure §A1 scorer: `PertinenceWeights` + `DEFAULT_PERTINENCE_WEIGHTS` (mention=1.0 ≫ location=0.4 > recency=0.2 > 0, and mention > location+recency+sim=0.9), `PertinenceSignals`, `PertinenceScore`, `SIGNAL_APPLICABILITY` (NPC/LOCATION carry `here`; FACTION does not), `SIGNAL_{MENTION,HERE,RECENCY,SIM}`, `structured_signals_sufficient` (drama-gate predicate), `score_card` (weighted sum over applicable signals; `sim=None` → `embed_used=False`, 0 sim contribution), `select_within_budget` (present-scene admitted first + unconditionally, rest by descending score within budget).
- `sidequest/game/retrieval_orchestration.py` — rewrote `retrieve_turn_context` to supersede §D4 floor/fill: builds a turn-level structured signal (mention ← `player_referenced_npcs`, here ← present floor), drama-gates `client.embed(action)` behind `structured_signals_sufficient`, scores the cosine fill with `score_card` + `select_within_budget`. Extended frozen `RetrievedEntities` with `embed_skipped: bool` + `card_scores: list[PertinenceScore]` (defaulted for legacy constructors, always populated by `_finish`). Preserved the `_OUTCOME_QUERY_FAILED` daemon-down/blank-query branch as the thin-action fallback (a real daemon failure does NOT set `embed_skipped`).
- `tests/game/test_pertinence_scorer.py`, `test_unified_retrieval_supersedes_d4.py`, `test_pertinence_wiring.py` (NEW, TEA-authored) — import-ordering/unused-import auto-fixed for lint.
- `tests/game/test_retrieval_orchestration.py` — updated 3 §D4-premised tests to the §A1 thin-action contract (see Design Deviations).

**OTEL:** `retrieval.embed_skipped` (bool) added to the existing `retrieval.universal` span in `_finish` — fires every turn, asserted by the wiring test. Full per-card decomposition is 84-4's job.

**Tests:** 20/20 target green (14 scorer + 5 orchestration + 1 wiring). Regression sweep: full `tests/game/` 2521 passed / 15 skipped; `tests/server/dispatch/` 249 passed; turn-context consumer tests 23 passed. `ruff check .` clean.
**Branch:** feat/84-1-unified-pertinence-scorer (committed; not pushed — SM handles finish)

**Handoff:** To review (Chrisjen Avasarala).

## Delivery Findings

### TEA (test design)
- **Question** (non-blocking): The mention signal currently has only the word-bounded `player_referenced_npcs_from_action` (`sidequest/agents/npc_context.py`) as a source — alias/epithet resolution is WI-5 (84-2). WI-1 should compute mention behind a seam WI-5 can extend, but until 84-2 lands the dominant signal degrades to keyword match for non-NPC types. Acceptable for WI-1; flagged so Dev keeps the seam clean. Affects `sidequest/game/retrieval_orchestration.py` (mention computation).
- **Gap** (non-blocking): The live `retrieve_turn_context` ALWAYS embeds (`game/retrieval_orchestration.py:248`). The drama-gate must move the `client.embed(action)` call behind `structured_signals_sufficient`. The current `_OUTCOME_QUERY_FAILED` blank-query/daemon-down branch (lines 239-254) must be preserved for the THIN-action fallback path — don't let the gate swallow a genuine daemon failure into a false "skipped". Affects `sidequest/game/retrieval_orchestration.py`.
- **Improvement** (non-blocking): The MP arrival-grounding narration triggers its OWN retrieval turn that DOES embed (observed in the wiring test: the daemon was called for both the grounding turn and "I attack Borin"). The drama-gate is per-retrieval-turn, so that's correct — but Dev should confirm the grounding-turn retrieval isn't accidentally exempted from the gate. The wiring test targets the "Borin" turn specifically (`calls_for("Borin")`) to avoid coupling to the grounding turn. Affects the `_retrieve_entities_for_turn` call frequency.

### Dev (implementation)
- **Improvement** (non-blocking): The drama-gate currently computes ONE turn-level structured-signal vector (mention from `player_referenced_npcs`, here from the present floor) rather than per-candidate-card structured signals. This is sufficient for WI-1's contract (named/present → skip embed; thin → embed) and keeps the fill cards scored purely on cosine `sim`. When WI-5 (84-2) adds aliases and WI-4 (84-3) adds relationship cards, mention/here/recency should be computed *per fill card* so a named off-floor entity can also win the fill without an embed. Affects `sidequest/game/retrieval_orchestration.py` (the `turn_signals` block + the per-card `PertinenceSignals` construction in the fill loop).
- **Question** (non-blocking): On the drama-gate-skip path the fill is intentionally empty (the present scene rides the floor, no cosine pass). If a future story wants a named/present turn to ALSO surface topically-related non-present cards, the gate would need a "skip embed but still rank cached embeddings" mode. Out of scope for WI-1; flagged so WI-3 (tiered projection) knows the current skip is total. Affects `retrieve_turn_context` drama-gate branch.
- No blocking upstream findings.

## Design Deviations

### Dev (implementation)
- **Updated three superseded §D4 tests in `test_retrieval_orchestration.py` to the §A1 thin-action contract**
  - Spec source: context-story-84-1.md, AC-5 / story title ("supersedes ADR-118 §D4")
  - Spec text: "Rewrite `retrieve_turn_context` to use the unified scorer instead of the floor/fill split" / "§A1 only changes how a projected card is *scored and selected*"
  - Implementation: `test_floor_and_fill_both_present_under_budget`, `test_floor_token_cost_counted_before_fill`, and `test_floor_npc_is_deduped_from_fill` each named a scene-present NPC (`player_referenced_npcs={"Borin"}`), which under §A1 fires the drama-gate and SKIPS the cosine fill — so the fill those tests asserted no longer runs. Their *mechanisms* (floor+fill coexist, floor-token budget accounting, floor-vs-fill dedup) are still valid on the THIN-action path, so I changed each to a thin action (dropped the `player_referenced_npcs` reference; Borin stays scene-present for the floor) so the cosine fill still runs and the original assertion intent is preserved under the §A1 regime.
  - Rationale: The story explicitly supersedes §D4; these were §D4-premised tests TEA's RED handoff did not list among the back-compat guards. Leaving them asserting the old always-embed coexistence would contradict the §A1 drama-gate the new suite pins. Minimal change: only the action/reference inputs, not the assertions.
  - Severity: minor
  - Forward impact: none — the new `test_unified_retrieval_supersedes_d4.py` suite is the authoritative §A1 coverage; these three retain their §D4 mechanism checks on the path where they still apply.

## Reviewer Assessment (84-1, commit 0a03312)

**Reviewer:** Chrisjen Avasarala (adversarial review)
**Verdict:** APPROVED — merge-ready. No Blocker or High findings.

**Scope reviewed:** full diff `develop...feat/84-1-unified-pertinence-scorer` (1202 +/11 -):
new `game/pertinence.py`, rewritten `retrieve_turn_context`, 3 new test files,
3 retargeted §D4 tests. Verified against ADR-118 Amendment §A1 + context ACs.

**Verification run (OTEL-sensitive, -n0 serial):**
- 84-1 suites + retargeted §D4: **39 passed**.
- Downstream consumers (universal_retrieval dispatch + e2e, 75-10 signal, entity_sync): **43 passed**.
- entity_card + scorer + orchestration regression: **65 passed**.
- `ruff check .` clean; `ruff format --check` clean. Tree clean, branch + HEAD correct.

**Adversarial checks (8 observations):**
1. **Scorer math vs §A1 — VERIFIED.** `DEFAULT_PERTINENCE_WEIGHTS` (1.0/0.4/0.2/0.3) satisfies
   both `mention>location>recency>0` AND `mention(1.0) > location+recency+sim(0.9)` — mention
   dominant, not merely first. `here→w_location` mapping is correct. Test-pinned.
2. **Present-scene HARD invariant — VERIFIED, two layers.** On the live path the present scene
   rides the `floor` (`build_npc_working_set`), which is computed independently of `budget_tokens`
   and never truncated (`remaining` may go negative; floor survives). Confirmed by
   `test_present_npc_never_dropped_under_tight_budget` (budget=1, Borin survives). `select_within_budget`'s
   own present-scene exemption is unit-tested but UNREACHED on the live path (fill cards are always
   `present_scene=False`) — forward machinery for WI-2/WI-4, documented, not a stub. No code path
   can evict a present entity.
3. **No Silent Fallbacks (drama-gate vs daemon failure) — code CORRECT, test gap.** `embed_skipped`
   is flipped True only at the gate's early-return; the `DaemonUnavailable/Request/ValueError`
   branch returns `_OUTCOME_QUERY_FAILED` with `embed_skipped` still False. A real daemon failure
   CANNOT masquerade as a drama-gate skip. **However** the existing daemon-failure test
   (`test_daemon_embed_exception_is_caught_not_propagated`, test_retrieval_orchestration.py:692) asserts
   `outcome=="query_failed"` but does NOT assert `embed_skipped is False`. See Should-fix #1.
4. **Retargeted §D4 tests — VERIFIED not weakened.** Git diff confirms the 3 tests changed ONLY by
   dropping `player_referenced_npcs={"Borin"}` (which would fire the gate and skip the fill those
   tests assert) and adding explanatory comments. **Assertions byte-for-byte unchanged.** Legitimate
   §A1 retarget, not a force-green.
5. **OTEL discipline — VERIFIED.** `retrieval.embed_skipped` set in `_finish` → fires on every return
   path (gate-skip / query_failed / no_candidates / success). Wiring test asserts the live span carries
   `embed_skipped=True`. The GM panel can observe the drama-gate decision every turn.
6. **Frozen-dataclass extension — VERIFIED back-compat.** `RetrievedEntities` gains `embed_skipped: bool`
   + `card_scores: list[PertinenceScore]`, both defaulted (legacy/fixture-safe) and ALWAYS populated by
   `_finish` on the live path. No consumer (`session_helpers`, `universal_retrieval`) reads the new fields
   yet; all existing fields preserved. 43 consumer tests green.
7. **Type design / fail-loud — VERIFIED.** `_applicable_signals` raises `ValueError` on an undeclared
   `EntityType` (No Silent Fallbacks); all 3 live enum members are declared; the "every type declared"
   test iterates the live enum, so a future 4th type fails loud at test- and run-time. StrEnum keys, no
   stringly-typed leakage.
8. **Recency signal — UNDER-IMPLEMENTED (see Should-fix #2).** `score_card` supports recency (unit-tested),
   but the orchestration hardcodes `recency=0.0` in BOTH the turn-signal and every fill card. `EntityCard`
   has no `last_seen_turn`, so live wiring is non-trivial. The inline comment "mention/here/recency are
   the floor's job" overstates: recency contributes 0 to `card_scores`. Consistent with the ACs as written
   (no AC requires live recency), but the §A1 formula advertises a term that is currently dead.

**Findings (none blocking):**

| Severity | Finding | Location |
|----------|---------|----------|
| Should-fix | Daemon-failure path has no test pinning `embed_skipped is False` — the load-bearing No-Silent-Fallbacks invariant (a real embed failure must not look like a drama-gate skip). Code is correct; add one assertion to the existing failure test to lock it. | `tests/game/test_retrieval_orchestration.py:719` (add `assert result.embed_skipped is False`) |
| Should-fix | Recency hardcoded to 0.0 in orchestration — the §A1 `w_recency·decay` term is dead on the live path; comment at line 341 implies it is computed. Either wire `last_seen_turn`→recency or downgrade the comment to an explicit "deferred to a follow-on" note so the silent zero is honest. | `retrieval_orchestration.py:284,341,351` |
| Nit | Turn-level binary `mention` (1.0 if ANY roster NPC named) lets a NAMED-but-off-scene NPC + any present NPC fire the gate and skip the fill, so the off-scene NPC is reachable only via the floor's brief tier, not semantic fill — a behavioral narrowing vs §D4 always-embed. Explicitly sequenced to WI-5 (per-card mention) by Dev note + §A4; flagged for traceability, not for this story. | `retrieval_orchestration.py:282-287` |

**Deviation audit:**
- Dev's "retargeted 3 §D4 tests" deviation — **ACCEPTED.** Independently verified assertions unchanged;
  the input-only change is the minimal correct §A1 adaptation. Rationale and forward-impact sound.

**Handoff:** To SM for finish-story. Both Should-fix items are non-blocking test/comment hygiene on
correct code; recommend folding the `embed_skipped is False` assertion into this story before merge if
cheap, otherwise tracking as a 84-x follow-up (it is a one-line lock on the project's headline principle).
