---
story_id: "75-12"
jira_key: ""
epic: "75"
workflow: "tdd"
---
# Story 75-12: Wire ratification gate into ADR-118 NPC projection — reuse 49-6 spans, dedup-by-id, floor-includes-pending test (ADR-138 D2/D5/D6)

## Story Details
- **ID:** 75-12
- **Title:** Wire ratification gate into ADR-118 NPC projection — reuse 49-6 spans, dedup-by-id, floor-includes-pending test (ADR-138 D2/D5/D6)
- **Jira Key:** (none—kanban-only project)
- **Workflow:** tdd
- **Stack Parent:** 75-11 (already merged, commit 3eee56d — is_projectable() predicate, ADR-138 D1/D3)
- **Points:** 3
- **Priority:** p2

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-04T19:10:04Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04 | 2026-06-04T18:47:45Z | 18h 47m |
| red | 2026-06-04T18:47:45Z | 2026-06-04T18:58:19Z | 10m 34s |
| green | 2026-06-04T18:58:19Z | 2026-06-04T19:01:51Z | 3m 32s |
| review | 2026-06-04T19:01:51Z | 2026-06-04T19:10:04Z | 8m 13s |
| finish | 2026-06-04T19:10:04Z | - | - |

## Technical Context

### Story Intent
This story implements ADR-138 D2, D5, and D6 by wiring the ratification gate
(`is_projectable()` predicate from 75-11) into the ADR-118 universal-retrieval
NPC projection pipeline. Two concrete changes:

1. **Gate the FILL, not the FLOOR (D2):** the NPC `to_card()` projector in
   `entity_card.py` / `entity_sync.py` must call `is_projectable()` before
   embedding pending members into the index. Unratified members stay out of
   semantic retrieval but remain in the live working-set floor (75-2).

2. **Emit observability spans (D6):** the retrieval seam must emit
   `retrieval.npc_unratified_skipped` count and reuse the existing 49-6
   `npc.ratification.*` spans from the gate-decision layer so the GM panel
   can see which members were withheld and why.

### Load-Bearing Design Facts (from ADR-138)

**The eligibility predicate (75-11, live):**
```python
is_projectable(member: NpcPoolMember) -> bool   # == not member.observation_pending
# Promoted Npc (sidequest.game.session.Npc) is always projectable
```

**The floor/fill boundary (ADR-118 §D4, D2 reconciliation):**
- **FLOOR (75-2, live):** budgeted working-set selection reads live `npc_pool` /
  `Npc` structs for scene-present entities. A freshly-minted, still-pending
  member the player is interacting with **right now** stays in the floor at
  full detail — ratification never drops it from the present scene.
- **FILL (ADR-118 §D3, this story):** the index retrieves semantically-relevant
  members when not scene-present. Unratified members must be withheld here; the
  world has not committed to them yet.

**Why pending members must not be indexed (D1):**
- An auto-minted prose-only phantom (`observation_pending = True`) may be
  purged next turn if the narrator does not re-cite it (49-6 gate).
- If the phantom is indexed now, it becomes semantically retrievable as a
  "recalled" NPC even though the world may reject it.
- The lie-detector (OTEL GM panel) catches this: the narrator re-surfaces a
  phantom the world never committed to, disguised as a canonical cast member.

**Why purge needs no eviction (D5):**
- Because unratified members are never indexed, there is no stale entity_card
  to evict when a phantom is purged.
- Lifecycle: mint (pending, not indexed) → ratify (flip flag, re-embed via
  75-6 reproject hook) → or purge (member removed, no index cleanup).

**Observability requirements (D6):**
- Reuse 49-6 spans: the ratification-gate decisions (`npc.ratification.promote`,
  `npc.ratification.purge`, `npc.ratification.pending`) already emit per-member
  decisions; this story consumes them for visibility.
- Add `retrieval.npc_unratified_skipped` count (extends ADR-118 §D5 OTEL attribute
  set) so the GM panel shows how many members were withheld from the fill per
  retrieval pass.
- No silent drops: every decision (skipped, ratified, projected) is observable.

### Code Sites (Existing, Pre-75-12)

**Ratification gate (75-11, merged):**
- `sidequest/game/npc_pool.py:NpcPoolMember.observation_pending`
- `sidequest/game/npc_pool.py:is_projectable(member: NpcPoolMember) -> bool`
- Test coverage: `tests/game/test_npc_pool_is_projectable.py`

**NPC to_card() projection (ADR-118, 75-4+, live):**
- `sidequest/game/entity_card.py:Npc.to_card()` — converts a live Npc to a
  retrievable EntityCard for the index.
- `sidequest/game/entity_sync.py` — manages the index, card re-projection,
  dirtying.

**Retrieval seam (ADR-118, 75-5+, live):**
- `sidequest/game/retrieval/retrieve_turn_context()` — floor+fill orchestration.
- Calls `npc_context()` for floor selection (75-2, budgeted working-set).
- Calls `entity_sync.retrieve_cards()` for fill retrieval.

**Watcher/OTEL (ADR-031, ADR-118, live):**
- `sidequest/telemetry/watcher.py:WatcherHub` — OTEL span dispatcher.
- `sidequest/game/npc_pool.py` and `sidequest/game/entity_sync.py` emit
  ratification and retrieval spans.

### This Story's Changes

**Must deliver (RED phase):**
1. Edit `to_card()` / NPC-card projector to gate on `is_projectable()` so
   pending members are not embedded.
2. Add `retrieval.npc_unratified_skipped` span attribute so the retrieval seam
   records how many members were skipped.
3. Unit test: `test_npc_to_card_pending_not_projected` — assert that
   `observation_pending = True` member does not produce a card.
4. OTEL/integration test: `test_retrieval_floor_includes_pending_scene_present` —
   verify that even though a pending member is not indexed, if it is scene-present
   (e.g., the player is talking to it), it still appears in the floor via 75-2
   working-set selection. This proves the floor/fill boundary is respected.

**Reuse:**
- 49-6 spans (`npc.ratification.promote`, `npc.ratification.purge`,
  `npc.ratification.pending`) are already emitted by the gate; this story just
  needs visibility that they fired. No change to the gate itself.

**Out of scope:**
- ADR-135 reference page wiring (75-13).
- Defensive entity_card eviction for invariant violation (75-14, optional).
- Re-embedding on ratification (75-6, already live).

### Dedup-by-id Note (Story Title)
The title mentions "dedup-by-id"; this refers to the entity_sync deduplication
logic that prevents duplicate cards in the index. The 75-11 gate ensures pending
members are never created as cards in the first place — no cleanup needed, just
a skip at projection time.

## Sm Assessment

**Routing decision:** Story 75-12 selected by Bossmang after 75-14 (originally
requested) was found dependency-blocked — 75-14 `depends_on` 75-12, which was
still in backlog. 75-12 is the correct next move: higher priority (p2 vs p3),
and it unblocks the whole D5/D6 chain.

**Dependency gate — verified clear:**
- 75-12 `depends_on` 75-11 (`is_projectable()` predicate, ADR-138 D1/D3).
- 75-11 is MERGED (orchestrator commit 3eee56d, sidequest-server PR #654).
- The predicate this story wires into the projection pipeline is live on develop.
  No blocked seam — TEA can write red tests against `is_projectable()` today.

**Scope discipline (1 story, 3 pts, tdd):** D2 (gate the FILL, not the FLOOR),
D5 (no eviction needed — pending members never indexed), D6 (reuse 49-6 spans +
add `retrieval.npc_unratified_skipped`). Explicitly OUT: 75-13 (ADR-135 ref page),
75-14 (defensive eviction), 75-6 (re-embed on ratify, already live).

**OTEL doctrine respected:** the story carries a mandatory observability
deliverable (`retrieval.npc_unratified_skipped`) — this is a Keith/dev GM-panel
lie-detector concern, correctly framed as backend telemetry, not a player-facing
surface.

**Branch:** `feat/75-12-wire-ratification-npc-projection` in sidequest-server,
targets develop per dual-clone protocol (orchestrator → main, subrepos → develop).

**Jira:** skipped explicitly — integration not configured (kanban-only project).
No silent skip; verified `pf jira` refuses cleanly.

**Handoff → TEA (red phase).** Crew aligned, objective clear.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 3-pt behavioral story wiring a gate into a live projection pipeline —
pure-function + dispatch-wiring + a load-bearing floor/fill invariant. Not a chore.

**Test Files:**
- `tests/game/test_entity_sync_ratification_gate.py` — game-tier, pure
  `sync_entity_cards` gate behavior (10 tests).
- `tests/server/dispatch/test_entity_sync_ratification_otel.py` — dispatch-tier
  D6 observability + the §D2 floor/fill wiring invariant (3 tests).

**Tests Written:** 13 tests covering 6 TEA-defined ACs (the sprint YAML carried no
ACs — defined during RED from the session Technical Context + ADR-138 §D2/§D5/§D6).

**ACs defined (RED):**
- **AC1 (§D2 — gate the FILL):** a pending (`observation_pending=True`) pool member
  produces NO card in `EntityStore`; not reprojected, not counted as `npc_count`.
- **AC2 (§D6 — counted, not silent):** the skip increments a new
  `EntitySyncResult.skipped_unratified`, NOT `failed` (a phantom is not an error).
- **AC3 (§D1 — ratified unaffected):** a ratified member (the default) and a
  stateful `Npc` still project normally; never counted as skipped. Regression guard.
- **AC4 (§D1 — Npc always projectable):** a stateful `Npc` is never gated even
  with no `pool_origin` (`is_projectable(Npc) → True`).
- **AC5 (§D6 — GM-panel observability):** `sync_for_turn` surfaces
  `skipped_unratified` on the `entity_sync` `state_transition` watcher payload —
  the lie-detector sees what was withheld vs indexed.
- **AC6 (§D2 invariant — gate the FILL, not the FLOOR):** the same scene-present
  pending member is WITHHELD from `EntityStore` yet STILL present in
  `build_npc_working_set` (the floor). End-to-end wiring proof on one snapshot.

**Status:** RED (12 failing, 1 intentional regression-guard pass).

### Rule Coverage

| Rule (lang-review / project) | Test(s) | Status |
|------|---------|--------|
| No Silent Fallbacks (skip is counted, not swallowed) | `test_pending_member_is_counted_skipped_not_failed`, `test_blank_named_pending_member_is_skipped_before_projection` | failing |
| OTEL Observability (every subsystem decision emits a span/event) | `test_sync_for_turn_reports_skipped_unratified_to_watcher` | failing |
| Wiring test (component reachable from production path) | `test_sync_for_turn_does_not_index_pending_member`, `test_pending_member_withheld_from_index_but_present_in_floor` | failing |
| No Source-Text Wiring Tests (behavior/OTEL, not grep) | all — watcher-payload + store-state assertions, no `read_text()` | n/a |

**Rules checked:** No-Silent-Fallbacks, OTEL Observability, Wiring-Test-per-suite,
No-Source-Text-Wiring — all covered by behavior/observability assertions.
**Self-check:** 0 vacuous tests — every test asserts on store contents, a result
counter, or a watcher-payload key. RED verified by `testing-runner` (run
`75-12-tea-red`): all failures are clean `AttributeError`
(`EntitySyncResult.skipped_unratified` missing) or `AssertionError` (pending member
present in index) / `KeyError` (watcher payload key missing) — no collection,
import, or fixture errors.

**Implementation contract for Dev (Naomi):**
1. `sidequest/game/entity_sync.py` — add `skipped_unratified: int = 0` to
   `EntitySyncResult`; in the pool-member loop of `sync_entity_cards`, gate on
   `is_projectable(member)` (import from `sidequest.game.npc_pool`). A withheld
   pending member increments `skipped_unratified` and is NOT projected, NOT
   counted `failed`. Gate BEFORE `project_npc_card` (a blank-named phantom must
   skip, not fail — see AC and the blank-name test). Stateful `npcs` loop is
   untouched (Npc always projectable).
2. `sidequest/server/dispatch/entity_sync.py` — add `skipped_unratified` to the
   `entity_sync` watcher payload AND set `entity_sync.npc_unratified_skipped` on
   the `accretion.entity_sync` span (OTEL Observability Principle).
3. Do NOT touch the floor (`build_npc_working_set`) — AC6 proves it must keep
   showing pending scene-present members.

**Handoff:** To Dev (Naomi Nagata) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/entity_sync.py` — added `skipped_unratified: int = 0` to
  `EntitySyncResult` (+ docstring); in `sync_entity_cards`, gate each pool member
  on `is_projectable(member)` BEFORE projection — a withheld phantom increments
  `skipped_unratified` and is skipped (not projected, not `failed`). Imported
  `is_projectable` from `sidequest.game.npc_pool`. Stateful `npcs` loop untouched.
- `sidequest/server/dispatch/entity_sync.py` — set
  `entity_sync.npc_unratified_skipped` on the `accretion.entity_sync` span and
  added `skipped_unratified` to the `entity_sync` watcher payload (D6).

**Implementation notes (followed TEA's contract exactly):**
- Gate is placed BEFORE `project_npc_card`, so a blank-named pending phantom is a
  skip, not a `failed` — `is_projectable` never even calls the projector for an
  unratified member (§D5: never indexed → no eviction; §D6: counted, not silent).
- The `outcome` property was left unchanged: an all-pending roster yields
  `reprojected==0` → `outcome="skipped"`, which is honest ("nothing reached the
  index") and no test constrained it otherwise. Minimal change.
- The floor (`build_npc_working_set`) was NOT touched — AC6 confirms the gate is
  on the FILL only; the scene-present member still rides the working set.

**Tests:** 41/41 passing (GREEN) — 11 new story tests + 30 regression tests across
`test_entity_sync.py`, `test_entity_sync_stateful_npcs.py`, and
`test_entity_sync_dispatch.py`. Verified by `testing-runner` (run `75-12-dev-green`).
Lint + format clean (`ruff check` / `ruff format`).

**Branch:** `feat/75-12-wire-ratification-npc-projection` (pushed).

**Handoff:** To verify phase (TEA — Amos Burton).

## Delivery Findings

<!-- Append-only. Each agent appends under its own subheading; never edit another agent's entries. -->

### Dev (implementation)

- No upstream findings during implementation. TEA's implementation contract was
  precise and complete; the gate landed exactly as specified with no surprises in
  the shared sync path (all 30 regression tests stayed green).

### TEA (test design)

- **Improvement** (non-blocking): the 75-7 GM-panel dashboard consumer should read
  the skip count as `entity_sync.npc_unratified_skipped` (span) / `skipped_unratified`
  (watcher field), NOT a `retrieval.*` attribute. The session's "retrieval seam"
  framing was imprecise — the gate fires at sync time and the count lives on the
  entity_sync surface. Affects the future 75-7 dashboard wiring (no file change now).
  *Found by TEA during test design.*
- **Gap** (non-blocking): session code-site reference
  `sidequest/game/retrieval/retrieve_turn_context()` is a phantom path — the real
  module is `sidequest/game/retrieval_orchestration.py`. Corrected in the tests;
  flagged so Dev does not chase it. Affects nothing in production.
  *Found by TEA during test design.*

### Reviewer (code review)

- **Improvement** (non-blocking): the OTEL span attribute
  `entity_sync.npc_unratified_skipped` is set but not directly asserted by any test —
  only the parallel watcher-payload field `skipped_unratified` is. This matches the
  ENTIRE entity_sync subsystem's convention (no sibling test asserts span attributes;
  all use `_watcher_publish` capture), so it is consistent, not a 75-12 defect. A
  future hardening story could add span-attribute assertions across the subsystem.
  Affects `tests/server/dispatch/` (subsystem-wide, optional). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the `EntitySyncResult.outcome` property returns
  `"skipped"` for BOTH a quiet all-unchanged turn and an all-pending-gated turn
  (`reprojected==0`). The disambiguating data IS published (`skipped_unratified` on
  the watcher payload + span), so the GM panel can already tell them apart — but a
  future story could add an explicit `"unratified"` outcome branch for clarity.
  Pre-existing property semantics; not introduced here. Affects
  `sidequest/game/entity_sync.py:66` (`outcome`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the pre-existing dedup-drop
  (`if card.id in covered_ids or member.name in covered_origins: continue`,
  `entity_sync.py:165`) discards a ratified member with NO counter increment —
  the only untallied exit in the pool loop. Verified present on `develop`; NOT
  introduced by 75-12. A future story could add a `dedup_skipped` tally to complete
  the §D6 observability contract for this loop. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): a blank-named PENDING member is now skipped before
  projection with no `logger` line (a ratified blank member still fails loud at the
  projector). The skip is counted on OTEL, so it is not fully silent, and the design
  is correct (a phantom's name validity is irrelevant until ratification). A
  `logger.debug` for blank-named pending skips would aid diagnosing a misbehaving
  upstream extractor. Affects `sidequest/game/entity_sync.py:148`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): both new test files' module docstrings still say
  "INTENTIONALLY RED until 75-12 lands" — accurate as historical TDD context but now
  stale (tests are green). A one-line touch-up would avoid confusing a future reader.
  Affects `tests/game/test_entity_sync_ratification_gate.py` and
  `tests/server/dispatch/test_entity_sync_ratification_otel.py`. *Found by Reviewer during code review.*

## Design Deviations

### Dev (implementation)

- No deviations from spec. Implemented exactly to TEA's contract: gate on
  `is_projectable` before projection, new `skipped_unratified` counter, span
  attribute `entity_sync.npc_unratified_skipped` + watcher field, floor untouched.
  TEA already logged the span-naming reconciliation (`retrieval.*` →
  `entity_sync.*`) as a test-design deviation; this implementation adopts it
  rather than introducing a new one.

### TEA (test design)

- **OTEL skip-count lives on the entity_sync span, not a "retrieval seam" span**
  - Spec source: .session/75-12-session.md → Technical Context, "Observability spans (D6)" and "This Story's Changes" #2
  - Spec text: "Add `retrieval.npc_unratified_skipped` span attribute so the retrieval seam records how many members were skipped."
  - Implementation: tests pin the skip count on the **entity-sync** path instead —
    `EntitySyncResult.skipped_unratified` (game tier) and the `entity_sync`
    `state_transition` watcher payload field `skipped_unratified` (dispatch tier,
    `sidequest/server/dispatch/entity_sync.py`). Dev should additionally set a
    matching span attribute (`entity_sync.npc_unratified_skipped`) on the existing
    `accretion.entity_sync` span to honor the OTEL Observability Principle.
  - Rationale: the gate fires at sync time. Per §D5, pending members are **never
    inserted into `EntityStore`**, so by the time `retrieve_turn_context`
    (`retrieval_orchestration.py`) runs, the withheld members are simply absent —
    the retrieval seam has nothing to count and no plumbing to know what was
    skipped. The only place the skip is observable is the sync gate. The session's
    "retrieval seam" framing is imprecise about where the gate physically lives;
    the count is attached where the decision is actually made. Suffix
    `npc_unratified_skipped` is preserved; the namespace is corrected from
    `retrieval.` to `entity_sync.` to match the existing `entity_sync.*` span
    attribute family.
  - Severity: minor
  - Forward impact: 75-7 GM-panel dashboard consumer should read
    `entity_sync.npc_unratified_skipped` (or the watcher `skipped_unratified`
    field), not a `retrieval.*` attribute. Noted as a Delivery Finding.

- **Session code-site path `sidequest/game/retrieval/retrieve_turn_context()` is wrong**
  - Spec source: .session/75-12-session.md → "Retrieval seam (ADR-118, 75-5+, live)"
  - Spec text: "`sidequest/game/retrieval/retrieve_turn_context()` — floor+fill orchestration."
  - Implementation: the real module is `sidequest/game/retrieval_orchestration.py`
    (no `retrieval/` package exists). Tests and the floor-invariant assertion use
    the correct path (`build_npc_working_set` from `sidequest/agents/npc_context.py`).
  - Rationale: verified on disk during test design (the `retrieval/` directory does
    not exist). Recording so Dev does not chase a phantom path.
  - Severity: minor
  - Forward impact: none — corrected in the tests.

- **Dedup-composition test passes during RED (intentional regression guard)**
  - Spec source: story title — "dedup-by-id"
  - Spec text: "...dedup-by-id, floor-includes-pending test..."
  - Implementation: `test_pending_member_shadowed_by_promoted_npc_yields_one_card`
    asserts the existing stateful-wins dedup still yields exactly one card. It
    passes today because the stateful Npc already shadows the pool member by id —
    it is a guard that the gate must not BREAK dedup, not a feature-driving RED
    test. It deliberately does not constrain whether the shadowed pending member
    is attributed to the dedup path or the gate (both withhold it; both defensible).
  - Rationale: the story title calls out dedup-by-id; this pins it without
    over-specifying the gate/dedup ordering, which is Dev's call.
  - Severity: minor
  - Forward impact: none.

### Reviewer (audit)

- **TEA: OTEL skip-count on the entity_sync span, not a "retrieval seam" span** →
  ✓ ACCEPTED by Reviewer: architecturally correct and verified. The gate fires in
  `sync_entity_cards`; per §D5 pending members never enter `EntityStore`, so the
  retrieval seam (`retrieval_orchestration.py`) physically cannot count them. The
  count belongs on the `entity_sync` surface. The `entity_sync.npc_unratified_skipped`
  span attribute + `skipped_unratified` watcher field are both wired and the
  watcher field is tested. security subagent confirms it carries only an integer
  (no PII/leak).
- **TEA: session code-site path `sidequest/game/retrieval/...` is wrong** →
  ✓ ACCEPTED by Reviewer: verified on disk — no `retrieval/` package exists; the
  module is `retrieval_orchestration.py`. The tests use the correct path.
- **TEA: dedup-composition test passes during RED (intentional regression guard)** →
  ✓ ACCEPTED by Reviewer: confirmed the test is a legitimate dedup-composition
  guard, not a vacuous test. The ratification gate has strong INDEPENDENT coverage
  from the non-colliding pending-member tests (`test_pending_pool_member_produces_no_card`,
  `test_mixed_roster_projects_ratified_and_skips_pending`, etc.), so the gate is
  not solely reliant on this overlap test. The test-analyzer's note that this test
  alone can't distinguish gate-from-dedup is true but moot given the independent
  coverage. Captured as a non-blocking clarity improvement (see Delivery Findings).
- **Dev: No deviations from spec** → ✓ ACCEPTED by Reviewer: the implementation
  matches TEA's contract exactly (gate before projection, new counter, span attr +
  watcher field, floor untouched). Verified line-by-line against the diff.

#### Undocumented deviations found by Reviewer
- None. Every behavioral change in the diff is covered by a logged TEA/Dev entry
  or is a pre-existing mechanism (see the dedup-drop / `outcome`-conflation
  observations in the Reviewer Assessment — both verified present on `develop`,
  not introduced by this story).

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A — 41/41 green, lint clean, 0 smells |
| 2 | reviewer-edge-hunter | Yes | findings | 2 | confirmed 0 blocking, deferred 2 (both pre-existing, non-blocking) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 0 blocking, deferred 2 (1 pre-existing dedup-drop, 1 minor blank-name log) |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 0 blocking, deferred 5 (test-tightening nits; gate independently covered) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings (stale-docstring nit caught by preflight + Reviewer instead) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (Reviewer checked types directly — see Rule Compliance) |
| 7 | reviewer-security | Yes | clean | 0 | N/A — net-positive on ADR-047 surface, integer-only telemetry |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (diff is minimal: +1 import, +1 field, +3-line gate, +2 emits) |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (Reviewer ran the python lang-review checklist manually — see Rule Compliance) |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 0 confirmed blocking, 0 dismissed, 9 deferred (all non-blocking; captured as Delivery Findings for follow-up)

## Reviewer Assessment

**Verdict:** APPROVED

A small, surgical, well-tested change that does exactly what ADR-138 §D2/§D5/§D6
asks: it gates unratified ("observation_pending") NPC pool members out of the
ADR-118 semantic retrieval index (the FILL) while leaving the scene-present working
set (the FLOOR) untouched, and surfaces the withholding count on the GM-panel
lie-detector. 41/41 tests green, lint clean, security net-positive. No Critical or
High findings. Every specialist finding is either pre-existing (verified on
`develop`), a test-tightening nicety, or based on a false premise — none block.

### Data flow traced
A player-influenced auto-minted phantom (`NpcPoolMember`, `drawn_from=
"dialogue_extraction"`, `observation_pending=True`) → `sync_entity_cards`
(`entity_sync.py:138`) → `is_projectable(member)` returns `False`
(`npc_pool.py:108`) → `result.skipped_unratified += 1; continue`
(`entity_sync.py:148-150`) → member is NEVER projected into `EntityStore`, so it
cannot resurface via semantic recall in a future narrator prompt before the world
ratifies it. The count flows → `sync_for_turn` → span attribute
`entity_sync.npc_unratified_skipped` (`dispatch/entity_sync.py:78`) + watcher field
`skipped_unratified` (`:90`) → GM panel. SAFE: the security subagent confirms the
telemetry carries only an integer (no NPC name/content), and the withholding
NARROWS the ADR-047 prompt-injection surface (the highest-risk player-influenced
text is the one now withheld from recall).

### Observations (5+ required)
- `[VERIFIED]` Gate placement is correct — gate runs BEFORE `project_npc_card`
  (`entity_sync.py:148`), so a pending phantom is skipped, not projected, not
  `failed`. Evidence: `entity_sync.py:148-150` precedes the `try/project` at `:152`.
  Complies with §D5 (never indexed → no eviction) and the No-Silent-Fallbacks rule
  (the skip is counted on OTEL, not swallowed).
- `[VERIFIED]` Stateful `Npc` is never gated — `is_projectable` is called only in
  the pool-member loop; the `snapshot.npcs` loop (`:115-130`) is untouched, and
  `is_projectable` returns `True` for any non-`NpcPoolMember` (`npc_pool.py:109`).
  AC4 holds.
- `[VERIFIED]` No circular import — `from sidequest.game.npc_pool import
  is_projectable` (`:29`); `npc_pool` is a lower-level module importing `Npc` only
  under `TYPE_CHECKING`. Lint clean + 41 tests import successfully prove no cycle.
- `[VERIFIED]` Loud-failure path preserved for RATIFIED members — a blank-named
  member with the default `observation_pending=False` still reaches the projector
  and fails loud (`failed`/`failed_refs`/`logger.warning`); proven by the still-green
  regression test `test_unprojectable_entity_fails_loud_no_stub_card`.
- `[EDGE]` `[MEDIUM→non-blocking]` The `outcome` property conflates a quiet
  all-unchanged turn with an all-pending-gated turn (both → `"skipped"`). Verified
  PRE-EXISTING on `develop` (`git show develop:...entity_sync.py` — identical
  property). Disambiguating data (`skipped_unratified`) IS published. Deferred as a
  non-blocking Delivery Finding.
- `[SILENT]` `[non-blocking]` The dedup-drop (`:165`) discards a ratified member
  with no counter. Verified PRE-EXISTING on `develop` (line 149 there). Out of scope
  for this story; deferred as a Delivery Finding.
- `[SILENT]` `[LOW]` A blank-named PENDING member loses the per-member
  `logger.warning` (it is now counted on OTEL instead). Design-correct (name validity
  is irrelevant pre-ratification); deferred as an optional `logger.debug` follow-up.
- `[TEST]` `[non-blocking]` Span attribute `entity_sync.npc_unratified_skipped` is
  not directly asserted — only the watcher field is. Verified this matches the
  ENTIRE entity_sync subsystem convention (no sibling test asserts span attributes).
  The test-analyzer's "look at sibling span assertions" suggestion rests on a false
  premise. The gate itself is independently well-covered. Deferred.
- `[TEST]` `[non-blocking]` `test_pending_member_shadowed_by_promoted_npc_yields_one_card`
  passes with or without the gate (dedup covers the collision). True, but the gate is
  independently proven by 4+ non-colliding pending-member tests. A clarity rename is
  deferred as a Delivery Finding.
- `[DOC]` `[LOW]` Both test docstrings still say "INTENTIONALLY RED until 75-12
  lands" (now green). Deferred as a cosmetic touch-up.
- `[TYPE]` (subagent disabled) Reviewer check: the one new field
  `skipped_unratified: int = 0` is annotated; the new import is a function, not a
  type; no stringly-typed API, no new enum, no constructor. No type-design concern.
- `[SEC]` Clean — confirmed by the security subagent: no injection vector, no
  PII/secret in telemetry, net-positive on the ADR-047 surface, no tenant/isolation
  concern (single-session in-memory `EntityStore`).
- `[SIMPLE]` (subagent disabled) Reviewer check: the change is already minimal
  (+1 import, +1 dataclass field, a 3-line guard, +2 telemetry emits). Nothing to
  simplify; no dead code, no over-engineering.
- `[RULE]` (subagent disabled) Reviewer ran the python lang-review checklist
  manually — see Rule Compliance below. No violations.

### Rule Compliance (python lang-review checklist — manual, rule_checker disabled)
- **#1 Silent exception swallowing:** PASS. No new `except`. The existing
  `except (ValueError, ValidationError)` (specific, logged) is unchanged. The new
  skip path is a counted `continue`, not an exception swallow.
- **#2 Mutable default arguments:** PASS. No new function signatures; the new field
  is `int = 0`.
- **#3 Type annotation gaps:** PASS. `skipped_unratified: int = 0` annotated;
  `is_projectable` already annotated. No `Any`, no `# type: ignore`.
- **#4 Logging coverage/correctness:** PASS (with the LOW non-blocking note that a
  blank-named pending member no longer logs — counted on OTEL instead).
- **#6 Test quality:** PASS. No vacuous assertions; assertions check store contents,
  exact counters, and watcher-payload keys. The one always-green test is a documented
  composition guard (deferred clarity note), not a vacuous test.
- **#10 Import hygiene:** PASS. Explicit single import, no star import, no cycle.
- **#11 Input validation at boundaries:** PASS — security subagent confirms.
- **Project rule — No Silent Fallbacks:** PASS. The skip is counted and emitted.
- **Project rule — OTEL Observability:** PASS. The subsystem decision emits both a
  span attribute and a watcher event.
- **Project rule — No half-wired features:** PASS. Gate → result field → dispatch
  span + watcher → end-to-end, proven by the dispatch wiring tests.
- Checks #5/#7/#8/#9/#12 — not applicable (no path handling, resources, deserialization,
  async, or dependency changes in the diff).

### Devil's Advocate
Let me try to break this. *Could a real, world-committed NPC get silently
dropped from recall?* Only if `is_projectable` returned `False` for a ratified
member — but it returns `not observation_pending`, and ratified means
`observation_pending is False`, so a ratified member always passes. A promoted
`Npc` returns `True` unconditionally. So no canonical NPC is ever gated. *Could a
malicious player force a phantom into permanent recall?* No — the gate withholds
exactly the player-influenced auto-minted phantoms from the index until the world
ratifies them; the security subagent calls this a net reduction of the injection
surface. *Could the count lie?* The counter increments on the only skip path and is
published verbatim; the watcher-field test pins it. The span attribute is untested
but reads the same integer in the same code block — a divergence is implausible.
*Could gating-before-dedup corrupt counts?* A pending member colliding with a
promoted twin increments `skipped_unratified` even though dedup would also have
caught it — but `npc_count` stays honest (1 card), no counter is double-incremented,
and the test deliberately leaves attribution unconstrained. Benign. *Could an
all-pending roster mislead the GM?* `outcome` says `"skipped"`, same as a quiet
turn — but `skipped_unratified > 0` distinguishes them on the same payload. *Stale
filesystem / huge input / config surprise?* The change touches an in-memory loop
over a list; no I/O, no config, no external input. *The worst real-world outcome*
I can construct is a future dashboard author reading `outcome="skipped"` without
also reading `skipped_unratified` and momentarily mis-reading an all-gated turn as
a no-op — a UI-consumer nuance, already disambiguable, captured as a non-blocking
finding. Nothing here rises to a blocking defect.

**Handoff:** To SM (Camina Drummer) for finish-story.