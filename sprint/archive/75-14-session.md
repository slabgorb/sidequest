---
story_id: "75-14"
jira_key: ""
epic: "75"
workflow: "trivial"
---

# Story 75-14: Defensive entity_card eviction + entity_card.evicted span for unprojectable cards (ADR-138 D5/D6)

## Story Details

- **ID:** 75-14
- **Title:** Defensive entity_card eviction + entity_card.evicted span for unprojectable cards (ADR-138 D5/D6)
- **Jira Key:** (none)
- **Workflow:** trivial
- **Points:** 1
- **Type:** chore
- **Repos:** sidequest-server
- **Stack Parent:** 75-12 (completed 2026-06-04)

## Context

This story implements ADR-138 D5/D6 — the defensive eviction path for the `is_projectable()` predicate work. The ratification gate (story 75-11) and its wiring into the NPC projection (75-12) are complete.

**ADR-138 Background:**
- NPC pool members have a ratification gate: `observation_pending`. 
- When `True`, a member is a prose-only phantom the narrator invented this turn and hasn't yet re-cited.
- When `False`, the member is real and projectable.
- D1–D4 specify that only ratified members (and promoted NPCs) are eligible for projection into the ADR-118 index and the ADR-135 reference page.
- D5–D6 (this story) add a *defensive eviction* path: if a card somehow exists on a now-unprojectable member (invariant violation), it MUST be evicted and the eviction MUST emit an OTEL span (`entity_card.evicted{reason=unprojectable}`). Per "No Silent Fallbacks," the eviction is never silent.

**Why this story?**
- The main projection paths (75-12 and 75-13) prevent cards from being created on unratified members in the first place.
- A defensive eviction is only needed if a future code path re-marks a member as pending *after* a card was already projected for it.
- The ADR says: "Only if 75-12 surfaces a real path that can strand a card on a now-unprojectable member; otherwise fold the invariant assertion into 75-12 and drop this story."
- 75-12 landed clean with no such path discovered; this is a defensive measure for the "never should happen" case.

## Acceptance Criteria

Per ADR-138 D5/D6:

1. **Defensive eviction path exists:** The entity-sync or entity-card layer checks whether a card's member is still `is_projectable()` before serving it. If not, the card is evicted and never served stale.
2. **OTEL span emitted:** Eviction emits `entity_card.evicted` with `reason=unprojectable` so the GM panel can confirm the defensive gate fired (not a silent drop).
3. **No silent fallbacks:** The eviction is observable and loud, never hidden.
4. **Test coverage:** Unit test verifies the invariant check (member was projectable when card was created, now isn't). Integration test confirms the span fires on eviction.

## Sm Assessment

Story 75-14 is a 1-point trivial chore in `sidequest-server` only. Dependency 75-12 is **done**; this is the defensive D5/D6 tail of ADR-138's `is_projectable()` ratification work. Setup is clean and the story is well-scoped:

- **Single repo, single concern:** Add a defensive eviction check + `entity_card.evicted{reason=unprojectable}` OTEL span. No cross-repo coordination needed.
- **Doctrine fit:** Directly serves "No Silent Fallbacks" (loud eviction) and the OTEL Observability Principle (GM panel must see the gate fire). The ACs already encode both.
- **Scope caution for Dev:** The ADR itself flags that this story may be unnecessary if 75-12 left no path that can strand a card on a now-unprojectable member. 75-12 reportedly landed clean. Dev should first confirm whether such a path can exist; if it genuinely cannot, the right outcome may be an invariant assertion + span on the "should never happen" branch rather than a full eviction subsystem. Do not build defensive machinery for a state the type system already prevents — but DO keep the observable span so the invariant is verifiable.
- **Trivial workflow:** SM → Dev → Reviewer → SM (skips TEA). Dev owns tests per AC #4.

Routing to Dev (Naomi Nagata).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/entity_store.py` — added `discard(card_id) -> bool`, the idempotent eviction sibling of `upsert` (absence is not an error; returns whether a card was removed so the caller only emits the span on a real eviction).
- `sidequest/game/entity_card.py` — added `npc_card_id(name)` (single source of the `npc:<slug>` id convention, shared by the projector and the eviction lookup; blank name raises → nothing to evict) and the `SPAN_ENTITY_CARD_EVICTED` / `ENTITY_CARD_EVICTED_REASON_UNPROJECTABLE` constants.
- `sidequest/game/entity_sync.py` — `EntitySyncResult` gains `evicted` + `evicted_ids`; the pool-member loop, on an unprojectable member, evicts any stranded card it owns (guarding the promoted-`Npc` shadow via `covered_ids`/`covered_origins`).
- `sidequest/server/dispatch/entity_sync.py` — emits one `entity_card.evicted{reason=unprojectable, entity_card.id, turn_number}` span per eviction, adds the `entity_sync.evicted` span attribute, and adds `evicted` to the per-turn watcher payload (ADR-138 §D6 / OTEL lie-detector).

**Tests:** 50/50 passing (GREEN) — 9 new (`tests/game/test_entity_sync_defensive_eviction.py` pure-sweep behavior; `tests/server/dispatch/test_entity_sync_eviction_otel.py` dispatch-tier span + watcher wiring) + 41 pre-existing entity_sync regression tests. Lint clean (ruff), types clean (pyright, 0 errors on changed modules).

**Branch:** `feat/75-14-defensive-entity-eviction` (pushed to origin, base `develop`)

**AC coverage:**
1. Defensive eviction path exists — ✅ `sync_entity_cards` discards a card stranded on a now-unprojectable member.
2. OTEL span emitted — ✅ `entity_card.evicted{reason=unprojectable}` per eviction, asserted via `otel_capture`.
3. No silent fallbacks — ✅ eviction counted + span'd + watcher-surfaced; idempotent `discard` never fabricates a phantom eviction event either.
4. Test coverage — ✅ invariant check (ratified→indexed, re-marked pending→evicted) + span-fires integration test.

**Handoff:** To review (Chrisjen Avasarala).

### Dev Rework (review response) — round 2

Reviewer REJECT findings addressed (commit `b496f82`):
- **[HIGH] accepted & fixed** — `entity_sync.py`: the ratified pool-member branch now does `covered_ids.add(card.id)` after `_apply_typed_card`, mirroring the stateful-Npc loop. The eviction guard now sees ratified pool cards, so a pending slug-twin can never `discard` a live committed card. Verified by the finding's own diagnosis — I confirmed the asymmetry by direct read; the fix is the one-line guard the Reviewer specified.
- **[MEDIUM] accepted & fixed** — `dispatch/entity_sync.py`: the per-eviction `entity_card.evicted` spans now emit *inside* the `accretion.entity_sync` `with` block, so they nest as children of the sweep span (trace link restored).
- **[MEDIUM/LOW] accepted & fixed** — tests: added `test_multiple_stranded_cards_all_evicted` (game) + `test_multiple_evictions_emit_one_span_each` (dispatch) for the n>1 path; added `TestSlugCollisionDoesNotEvictRatifiedSibling` (2 tests — the regression that fails without the HIGH fix, both pool orders); asserted the eviction-span `entity_sync.turn_number` and the sweep span's `entity_sync.evicted` attr; added `len(events) == 1` to the watcher test.
- Two non-blocking Delivery Findings (`world_materialization` casefold dedup; `_slug` Unicode whitespace) left as-is — out of scope for this 1-pt story; the HIGH fix makes the eviction bug unreachable regardless of the upstream dedup.

**Tests:** 56 green (13 eviction + 41 entity_sync regression), ruff + pyright clean. **Branch:** `feat/75-14-defensive-entity-eviction` (pushed, `b496f82`).

**Handoff:** Back to review (Chrisjen Avasarala).

### Dev Rework (review response) — round 3

Reviewer round-2 REJECT findings addressed (commit `39daf49`):
- **[HIGH] accepted & fixed structurally** — the round-1 `covered_ids.add` only closed the *ratified-first* ordering because `covered_ids` fills lazily as the pool loop walks. Reviewer's reproduction (pending-twin-first + pre-seeded store → `evicted=1`) is correct. Fix: **deferred two-phase eviction** (`entity_sync.py`) — the pool loop now collects stranded-card candidates into `eviction_candidates` instead of discarding inline; after the full loop has populated `covered_ids`, a second pass discards only candidates whose id is absent from `covered_ids`. Order-independent by construction — a pending member swept first can no longer delete a live card a ratified slug-twin (or promoted Npc) owns later in the sweep.
- **[MEDIUM] accepted & fixed** — folded the case-sensitive `covered_origins` guard into the slug-normalized `covered_ids`. The stateful-Npc loop now seeds `covered_ids` with `npc_card_id(npc.pool_origin)`, so a pending member matching a *renamed* Npc's origin (`core.name` ≠ `pool_origin`) is guarded case-insensitively. `covered_origins` removed entirely (redundant). Took the Reviewer's "seed `covered_ids`" option.
- **[MEDIUM] accepted & fixed** — replaced the vacuous `test_slug_twin_guard_holds_regardless_of_pool_order` (empty store → `discard` no-op → passed on broken code) with `test_pending_first_does_not_evict_preseeded_ratified_twin` (pre-seeded store + pending-first; fails on round-1 code, passes now) and added `test_pending_member_matching_renamed_npc_origin_not_evicted` for the renamed-origin case.
- **[MEDIUM] accepted & fixed** — tightened the dispatch sweep-span assertion: `len(sweep_spans) == 2`, locate the evicting sweep by its count, assert it carries both `entity_sync.evicted == 1` and `entity_sync.turn_number`.

**Tests:** 74 entity_sync tests green (14 eviction + 60 regression across the `-k entity_sync` filter), ruff + pyright clean (0 errors). **Branch:** `feat/75-14-defensive-entity-eviction` (pushed, `39daf49`).

**Handoff:** Back to review (Chrisjen Avasarala).

## Subagent Results (Round 1 — superseded)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (50/50 green, ruff clean, pyright clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 5 | confirmed 2 (1 HIGH, 1 MEDIUM), deferred 2 (Delivery Findings), confirmed 1 test-gap |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 (both low) | dismissed 2 (1 pre-existing/out-of-scope, 1 verified-correct) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 6 (all coverage gaps; folded into rework + the HIGH-bug test) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings (assessed by Reviewer; types clean per pyright) |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings (assessed by Reviewer; no over-engineering found) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings (rule compliance checked by Reviewer below) |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 3 confirmed blocking-relevant (1 HIGH, 2 MEDIUM), 6 test-coverage gaps confirmed, 4 dismissed/deferred (with rationale)

## Rule Compliance (Round 1 — superseded)

Python lang-review checklist + CLAUDE.md/SOUL.md rules, enumerated against every changed symbol:

- **#1 Silent exception swallowing** — `entity_sync.py:219-224` `except ValueError: continue` on `npc_card_id`. CHECKED: `_slug` raises `ValueError` only on blank name; the catch is narrow and the path is documented + counted under `skipped_unratified`. Compliant (not user-facing silent drop). [SILENT] confirms.
- **#1 / No Silent Fallbacks** — `entity_store.discard` returns `False` on absence rather than raising. CHECKED: documented as idempotent-by-design; caller only counts/spans on `True`. Compliant (contrast with `update_embedding` which raises — asymmetry justified and documented).
- **#3 Type annotations at boundaries** — `discard(self, card_id: str) -> bool`, `npc_card_id(name: str) -> str` both fully annotated. Compliant.
- **#4 Logging** — no new logging in the changed lines; eviction observability is via OTEL span + watcher (correct per OTEL principle). Compliant.
- **#6 Test quality** — no vacuous assertions; assertions check specific ids/counts. Wiring test present (`test_eviction_emits_entity_card_evicted_span` drives real `sync_for_turn`, asserts via OTEL span, not source grep). Compliant with "no source-text wiring tests". Coverage GAPS exist (n>1 path) — see findings.
- **#8 Unsafe deserialization / #11 injection** — none introduced. [SEC] confirms clean.
- **OTEL Observability Principle (CLAUDE.md)** — eviction emits `entity_card.evicted{reason, entity_card.id, turn_number}` + `entity_sync.evicted` attr + watcher field. Subsystem decision IS observable. Compliant in intent; span-parentage defect noted (MEDIUM).
- **Every Test Suite Needs a Wiring Test** — satisfied (dispatch-tier test through production path).

## Reviewer Observations (Round 1 — superseded)

- `[HIGH][EDGE]` Spurious eviction of a ratified pool member's card on intra-sweep slug collision — `sidequest/game/entity_sync.py:247`. `covered_ids` is populated only by the stateful-Npc loop (line 190), never for ratified **pool** members. A ratified member projected at line 247 leaves `covered_ids` empty; a later pending pool member whose name case-folds to the same `npc:<slug>` passes both guards at line 225 and `store.discard`s the live card. Verified by direct read. Reachable: `world_materialization` dedupes pool members by exact string, not casefold, so two slug-colliding entries can coexist. **A defensive-eviction feature that corrupts the index is self-defeating.** Blocks.
- `[MEDIUM][EDGE]` Eviction spans are unparented — `sidequest/server/dispatch/entity_sync.py:242-246`. The `entity_card.evicted` spans are emitted *after* the `accretion.entity_sync` `with` block closes, so they fire as sibling/root spans with no trace link back to the sweep. (`tracer` scope itself is fine — Python `with` doesn't scope; confirmed non-bug.) GM following a non-zero `entity_sync.evicted` can't trace to the per-card spans. Non-blocking alone, but bundle into the rework.
- `[MEDIUM][TEST]` n>1 eviction path entirely unproven — both tiers only ever evict ONE card. The production `for card_id in result.evicted_ids` loop and the `result.evicted == N` tally have no multi-card test; a loop that broke after the first iteration would pass. High-confidence from [TEST], corroborated by [EDGE] Finding 5 (also no slug-collision test).
- `[LOW][TEST]` `entity_sync.evicted` (on the sweep span) and `entity_sync.turn_number` (on the eviction span) are set in production but asserted by no test; the `covered_ids` guard branch (vs `covered_origins`) is untested. Recommend in rework.
- `[VERIFIED]` Stateful-loop-before-pool-loop ordering is sound — `entity_sync.py:178-193` fully completes and populates `covered_ids`/`covered_origins` before the pool loop at 197 begins. No pool ordering races a stateful Npc's coverage. Evidence: edge-hunter confirmed + my read. (This is exactly why the promoted-Npc shadow guard works — but it does NOT protect the ratified-pool-member case, hence the HIGH finding.)
- `[VERIFIED]` `discard` correctness — `entity_store.py:96-101`: deletes by exact key, returns whether removed; per-session store (no cross-session reach). Complies with No-Silent-Fallbacks (loud on real eviction, no fabricated event on absence). Evidence + [SEC] confirms no cross-session bleed.
- `[SEC]` Clean — NPC-name-derived `entity_card.id` in spans is opaque, case-folded, internal-only; no injection/leak/cross-session vector. Pre-existing absence of `max_length` on `NpcPoolMember.name` noted, not introduced here.
- `[DOC]` (disabled) — Reviewer check: new docstrings on `discard`/`npc_card_id`/`EntitySyncResult` are accurate and explain the *why*. No stale comments.
- `[TYPE]` (disabled) — Reviewer check: `evicted: int` / `evicted_ids: list[str]` typed; helpers annotated; pyright 0 errors. No stringly-typed regressions.
- `[SIMPLE]` (disabled) — Reviewer check: no over-engineering; `discard`/`npc_card_id` are minimal and reuse-first (single id-convention source). The eviction is genuinely needed (durable store + mutable flag), confirmed in Dev's deviation note.
- `[RULE]` (disabled) — Reviewer ran the rule enumeration above; one observability-intent compliance with a parentage defect, no hard rule violations.

### Devil's Advocate (Round 1 — superseded)

Argue the code is broken: it *is*, and the break is the feature eating itself. This story exists to defend the retrieval index against stale cards — yet the implementation hands a pending pool member a loaded gun pointed at its own ratified neighbors. The stateful-Npc loop carefully records every card it projects into `covered_ids` precisely so the pool loop won't clobber it; the pool loop then projects ratified members and forgets to do the same bookkeeping. The eviction guard trusts `covered_ids` to mean "a live card legitimately owns this id this sweep" — but for pool-on-pool collisions that set is a lie, empty where it should be full. A confused content author who writes `BORIN` in `world.yaml` while the narrator has already minted `Borin` from dialogue gets two pool entries (world_materialization compares names with `==`, not casefold), and the moment one of them goes pending, the other's card silently vanishes from semantic recall — *and the GM panel cheerfully fires an `entity_card.evicted` span that says everything worked.* That is the worst kind of failure: an observability feature reporting success while corrupting state. A stressed session that re-marks several members pending in one turn exercises the n>1 span loop that no test has ever run; if that loop regresses, every test still passes. What would a malicious narrator do? Emit a name that case-folds onto an existing committed NPC, wait for a ratification flip, and quietly delete a canonical cast member from the index — a *Living World* violation dressed as a defensive gate. The tests look thorough but they only ever stage one eviction with no slug twin, so the whole collision class is invisible. The fix is one line (`covered_ids.add(card.id)` at 247) plus the missing tests — cheap, but mandatory. Until then this defends the index by occasionally shredding it.

## Superseded — Reviewer Verdict (Round 1)

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Spurious eviction of a ratified pool member's card on intra-sweep slug collision (`covered_ids` never updated for ratified pool members) | `sidequest/game/entity_sync.py:247` | Add `covered_ids.add(card.id)` immediately after `_apply_typed_card(...)` in the projectable pool-member branch (mirror the stateful loop at line 190), so the eviction guard at line 225 sees ratified pool cards and never discards a live one. |
| [MEDIUM] | `entity_card.evicted` spans emitted after the `accretion.entity_sync` span closes → unparented, no trace link from the sweep | `sidequest/server/dispatch/entity_sync.py:242-246` | Emit the per-eviction spans *inside* the `with tracer.start_as_current_span("accretion.entity_sync")` block so they nest under the sweep span. |
| [MEDIUM] | n>1 eviction path unproven (single-card only) at both game and dispatch tiers | `tests/game/test_entity_sync_defensive_eviction.py`, `tests/server/dispatch/test_entity_sync_eviction_otel.py` | Add a two-member-pending test: assert `result.evicted == 2` / `set(evicted_ids) == {...}` (game tier) and `len(evict_spans) == 2` (dispatch tier). |
| [LOW] | Slug-collision case + span attributes (`entity_sync.evicted`, eviction-span `turn_number`) + `covered_ids` guard branch untested | test files | Add: ratified `BORIN` + pending `Borin` (no stateful Npc) → assert `evicted == 0` and `npc:borin` retained (this test will FAIL until the HIGH fix lands — use it to prove the fix); assert the two span attributes; add `assert len(events) == 1` in the watcher test. |

**Data flow traced:** narrator/world NPC name → `NpcPoolMember.name` → (member goes unprojectable) → `npc_card_id(member.name)` → `store.discard(stranded_id)` → `result.evicted_ids` → `entity_card.evicted` span + watcher `evicted`. **Unsafe** at the discard step for slug-colliding ratified neighbors (HIGH).

**Handoff:** Back to Dev (Naomi Nagata) for fixes — trivial workflow has no TEA phase; Dev owns both the code fix and the tests.

## Subagent Results (Round 2 — superseded)

Round 2 re-review of Dev's rework (commit `b496f82`). Same five subagents enabled as round 1.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (13/13 eviction tests green serial; ruff clean; pyright 0 errors; wiring verified `websocket_session_handler.py:1394 → sync_for_turn → sync_entity_cards`) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 3 | confirmed 2 (1 HIGH, 1 MEDIUM), confirmed 1 test-gap |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 (1 med, 2 low) | dismissed 3 (pre-existing ADR-006 isolation / by-design idempotency / design-choice telemetry split) |
| 4 | reviewer-test-analyzer | Yes | findings | 2 | confirmed 2 (1 HIGH vacuous-test, 1 MEDIUM sweep-span assertion) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings (assessed by Reviewer; pyright 0 errors) |
| 7 | reviewer-security | Yes | findings | 2 (both low) | confirmed 1 (covered_origins casefold — folds into HIGH root cause), deferred 1 (pre-existing name max_length) |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings (rule compliance checked by Reviewer below) |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 1 HIGH confirmed (blocking, empirically reproduced), 2 MEDIUM confirmed, 3 dismissed (rationale below), 1 deferred (pre-existing)

## Rule Compliance (Round 2 — superseded)

Round-2 enumeration against the round-1 fix delta (`b496f82`):

- **No Silent Fallbacks (CLAUDE.md, load-bearing)** — VIOLATED in spirit by the HIGH. The story's deliverable is an *honest* `entity_card.evicted{reason=unprojectable}` span. The pending-first + pre-seeded-store path fires that span for a card that is NOT actually unprojectable (a ratified slug-twin owns it the same sweep) and is re-indexed immediately. A false eviction signal is the inverse of a silent fallback but the same doctrine breach: the GM-panel lie-detector reports a state transition that did not really happen.
- **OTEL Observability Principle (CLAUDE.md)** — the eviction telemetry is wired (span + attr + watcher), but it can emit a *false positive*. "The GM panel is the lie detector" — here the lie detector lies. AC#2/#3 ("eviction is observable and loud, never hidden" — and, by intent, *true*) are violated for the pending-first ordering.
- **#6 Test quality / no vacuous assertions** — VIOLATED. `test_slug_twin_guard_holds_regardless_of_pool_order` (test_entity_sync_defensive_eviction.py:184) passes on *pre-fix* code (empty store → `discard` no-op) and its own docstring admits it. It claims order-independence it does not prove. Confirmed independently by [TEST] and [EDGE], both high confidence.
- **#3 Type annotations** — `discard(card_id: str) -> bool`, `npc_card_id(name: str) -> str` annotated. Compliant (pyright 0 errors).
- **Every Test Suite Needs a Wiring Test** — satisfied (dispatch-tier test drives `sync_for_turn` through the production module; OTEL-span assertion, not source-grep). Compliant.
- **No Source-Text Wiring Tests** — compliant (span/behavior assertions, no `read_text()` greps).

## Reviewer Observations (Round 2 — superseded)

- `[HIGH][EDGE][TEST]` **Round-1 HIGH only partially fixed — spurious eviction survives in the pending-twin-first ordering.** `sidequest/game/entity_sync.py:225`. The fix added `covered_ids.add(card.id)` at line 255 (ratified pool branch), which closes the *ratified-first* ordering. But `covered_ids` is populated *lazily as the pool loop advances*, so a pending member that appears **before** its ratified slug-twin in `npc_pool` sees an empty `covered_ids` at the eviction guard. If the durable store already holds the card from a prior sweep, `store.discard()` returns `True` → spurious `evicted=1` + false `entity_card.evicted` span + needless re-embed. **Empirically reproduced** (throwaway test, pending-first + pre-seeded store): `evicted=1 ids=['npc:borin'] reprojected=1 card_present=True`. **Reachable in production:** `world_materialization.py:457` matches existing members by exact case-sensitive string (`m.name == name`), so a chapter introducing canonical `"Borin"` while a pending `"borin"` already sits at a lower index *appends* the new ratified member — leaving the pending twin earlier in the list. Next sweep processes it first. Confirmed by [EDGE] (high) + [TEST] (high) + my own reproduction. **Blocks.** Fix: pre-pass to seed `covered_ids` with `npc_card_id(m.name)` for every `is_projectable` pool member before the eviction path, OR two-phase (collect eviction candidates, discard only those not in `covered_ids` after the full pool loop). Order-independence must be structural, not list-order luck.
- `[MEDIUM][TEST]` `test_slug_twin_guard_holds_regardless_of_pool_order` (test_entity_sync_defensive_eviction.py:184) is **vacuous for the ordering it names** — fresh store means `discard` is a no-op, so it passes on pre-fix code. It gives false coverage confidence for exactly the unguarded path. Replace with the pre-seeded variant that asserts `evicted == 0` and `npc:borin in store.cards` (it will fail until the HIGH is fixed — use it as the regression).
- `[MEDIUM][TEST]` Sweep-span assertion in `test_eviction_emits_entity_card_evicted_span` (test_entity_sync_eviction_otel.py:67) uses `any(... evicted == 1)` over both sweeps without pinning `len(sweep_spans) == 2`, and does not assert `entity_sync.turn_number` on the *parent* `accretion.entity_sync` span (only on the child eviction span). Tighten: assert the second sweep span carries both `entity_sync.evicted == 1` and `entity_sync.turn_number`.
- `[MEDIUM][EDGE][SEC]` `covered_origins` guard is case-sensitive (`member.name in covered_origins`, populated verbatim from `npc.pool_origin`) while `covered_ids` is slug-normalized. When a promoted `Npc`'s `core.name` diverges from its `pool_origin` (renamed at promotion), the two guards stop being redundant and a slug-colliding pending member can slip through. Narrower variant of the same root cause. Fold into the HIGH fix: casefold `covered_origins` at the add/compare sites, or seed `covered_ids` with `npc_card_id(npc.pool_origin)` in the stateful loop. Confirmed by [EDGE] (medium) + [SEC] (low).
- `[SILENT]` (dismissed ×3): (1) the broad `except Exception` in `sync_for_turn` (dispatch:204) is the documented ADR-006 graceful-degradation isolation — pre-existing, by design; the `except` payload does not reference `result`, so no NameError. (2) blank-name `except ValueError: continue` (entity_sync:221) is already counted as `skipped_unratified`; a blank-named phantom never had a card — benign. (3) watcher carries aggregate `evicted` not `evicted_ids` — a deliberate OTEL(per-card)/watcher(aggregate) split, consistent with `failed_refs`. None block.
- `[SEC]` Clean on the security axis proper — `EntityStore` is per-session (no cross-session reach in `discard`), card ids in spans are opaque slugs not raw names, no injection. `NpcPoolMember.name` lacks `max_length` (pre-existing, not introduced) — deferred to a Delivery Finding.
- `[VERIFIED]` The span-parentage MEDIUM from round 1 **is fixed** — `dispatch/entity_sync.py:244-248`: per-eviction spans now emit *inside* the `with tracer.start_as_current_span("accretion.entity_sync")` block, so they nest as children. Evidence: line 244 loop sits within the `with` at line 220, before it closes. Complies with the OTEL trace-linkage intent.
- `[VERIFIED]` The n>1 eviction path from round 1 **is now covered** — `test_multiple_stranded_cards_all_evicted` (game:134, asserts `evicted == 2` AND `set(evicted_ids) == {…}`) + `test_multiple_evictions_emit_one_span_each` (dispatch:71, asserts `len(evict_spans) == 2` AND id set). Genuine, non-vacuous. Confirmed by [TEST].
- `[DOC]` (disabled) — Reviewer check: the round-2 docstring at entity_sync.py:248-254 honestly explains *why* the pool loop mirrors the stateful loop. Accurate. (But it overstates completeness — it does not mention the ordering dependency the HIGH exposes.)
- `[TYPE]` (disabled) — Reviewer check: no new stringly-typed regressions; pyright 0 errors.
- `[SIMPLE]` (disabled) — Reviewer check: the one-line `covered_ids.add` is minimal; the correct fix (pre-pass/two-phase) is *not* over-engineering — it is the structural correctness the lazy-population approach lacks.
- `[RULE]` (disabled) — Reviewer ran the enumeration above; the HIGH is a No-Silent-Fallbacks / OTEL-honesty doctrine breach plus a #6 vacuous-test violation.

### Devil's Advocate (Round 2 — superseded)

The round-2 fix is a patch over a patch, and it patched the wrong axis. Naomi correctly mirrored the stateful loop's `covered_ids.add` — but `covered_ids` is built *as the loop walks the pool*, so it only protects collisions where the ratified twin is encountered first. The guard's correctness now depends on `snapshot.npc_pool` happening to list ratified members before their pending case-twins. That is not an invariant — it is list-append order, and `world_materialization.py:457`'s exact-string dedup actively manufactures the opposite ordering: a phantom `"borin"` mentioned in dialogue on turn 2 sits at index 0; a canonical `"Borin"` introduced by a world chapter on turn 5 fails the `==` match and gets appended at index 7; the phantom is now permanently *earlier* in the sweep than the entity it collides with. The moment that phantom is swept while a prior-turn card for the slug exists, the engine fires `entity_card.evicted{reason=unprojectable}` for a card it re-creates microseconds later. A GM staring at the lie-detector sees an invariant violation that never occurred — and this is a story whose *entire reason to exist* is to make eviction honest and observable. The worst part is the test theater: `test_slug_twin_guard_holds_regardless_of_pool_order` is named to claim exactly the coverage that would have caught this, but it quietly uses an empty store so the dangerous `discard` is a no-op, and the docstring *says so out loud*. A reviewer skimming the test names would check the box; the test passes on the broken code. What would a malicious narrator do? Mint a low-case phantom of a known canonical NPC, wait for any ratification churn, and watch the GM panel light up with eviction noise that masks a real eviction in the same turn. What would a confused author do? Write `BORIN` in world.yaml while the narrator already said `Borin` — and get an eviction span every sync thereafter. The card survives, so this is not the index-shredding of round 1 — but for a telemetry feature, a false signal is its own corruption. One structural fix closes it: seed `covered_ids` with every projectable member's slug before any eviction runs, or defer evictions to after the pool loop. Until then the guard works by luck of ordering, and the world materializer is engineered to revoke that luck.

## Superseded — Reviewer Verdict (Round 2)

**Verdict:** REJECTED

The round-1 span-parentage MEDIUM and n>1 test MEDIUM are **fixed and verified**. But the round-1 HIGH is only *partially* closed: the one-line `covered_ids.add` fixes the ratified-first ordering and leaves the pending-twin-first ordering exposed — empirically reproduced, and reachable via `world_materialization`'s exact-string dedup. A defensive-eviction feature whose whole purpose is honest telemetry still emits a false `entity_card.evicted` span.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Spurious eviction survives in the pending-twin-first ordering: `covered_ids` is populated lazily during the pool loop, so a pending member preceding its ratified slug-twin sees an empty set and `discard`s the live prior-sweep card (re-indexed same sweep → false `entity_card.evicted` span + re-embed churn). Empirically reproduced; reachable via `world_materialization.py:457` exact-string dedup. | `sidequest/game/entity_sync.py:207-230` (eviction guard) | Make order-independence structural: **pre-pass** over `snapshot.npc_pool` to seed `covered_ids` with `npc_card_id(m.name)` for every `is_projectable(m)` member (and `covered_origins`/`covered_ids` for stateful Npcs) *before* the eviction branch runs; **or** two-phase — collect candidate `stranded_id`s during the loop and `discard` only those not in `covered_ids` after the full pool loop completes. Do not rely on pool list order. |
| [MEDIUM] | Vacuous regression test: `test_slug_twin_guard_holds_regardless_of_pool_order` passes on pre-fix code (empty store → `discard` no-op); its docstring admits the limitation. Gives false coverage for the unguarded path. | `tests/game/test_entity_sync_defensive_eviction.py:184` | Replace with a **pre-seeded-store** variant: seed via a prior `sync_entity_cards` of ratified `BORIN`, then sync `pool=[pending "Borin", ratified "BORIN"]`; assert `evicted == 0` and `npc:borin in store.cards`. This MUST fail on current code and pass after the HIGH fix — use it as the regression. |
| [MEDIUM] | Sweep-span assertion is loose: `any(... evicted == 1)` over both sweeps without `len(sweep_spans) == 2`; `entity_sync.turn_number` unasserted on the parent `accretion.entity_sync` span. | `tests/server/dispatch/test_entity_sync_eviction_otel.py:67` | Assert `len(sweep_spans) == 2` and that the second (evicting) sweep span carries both `entity_sync.evicted == 1` and `entity_sync.turn_number`. |
| [MEDIUM] | `covered_origins` guard is case-sensitive while `covered_ids` is slug-normalized; when a promoted Npc's `core.name` diverges from `pool_origin`, the guards stop being redundant and a slug-twin can slip the eviction guard. | `sidequest/game/entity_sync.py:192,225` | Casefold `covered_origins` at add + compare, or seed `covered_ids` with `npc_card_id(npc.pool_origin)` in the stateful loop. Folds into the HIGH pre-pass fix. |

**Data flow traced:** dialogue/world NPC name → `NpcPoolMember.name` (case-variant twins coexist via `world_materialization.py:457` exact-string dedup) → pending twin swept before ratified twin → empty `covered_ids` at guard → `store.discard(npc:<slug>)` on a live prior-sweep card → spurious `result.evicted` + false `entity_card.evicted{reason=unprojectable}` span. **Unsafe** at the discard step for the pending-first ordering (HIGH).

**Verified fixed from round 1:** [VERIFIED] span parentage (eviction spans now nest under `accretion.entity_sync`); [VERIFIED] n>1 eviction coverage (game + dispatch, count + id-set asserted).

**Handoff:** Back to Dev (Naomi Nagata) for fixes — trivial workflow has no TEA phase; Dev owns both the structural eviction fix and the pre-seeded regression test (the test that must fail before the fix and pass after).

## Subagent Results

Round 3 re-review of Dev's deferred two-phase eviction fix (commit `39daf49`). Same five subagents enabled.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (14/14 targeted green serial; 73 passed/1 skipped on `-k entity_sync`; ruff clean; pyright 0; wiring verified handler→sync_for_turn→sync_entity_cards) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 5 (all med/low) | confirmed 0 blocking; 1 accepted as non-blocking improvement (dedupe candidates to a set), 4 dismissed/deferred (benign/pre-existing/documented) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 (1 med, 1 low) | dismissed 2 (blank pool_origin suppress benign; no-card eviction is the common benign case) |
| 4 | reviewer-test-analyzer | Yes | findings | 2 | confirmed 2 as non-blocking test-strengthening (renamed-origin test should use mixed-case origin; turn_number assertion should advance the counter) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | N/A — Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — Disabled via settings (pyright 0) |
| 7 | reviewer-security | Yes | findings | 1 (claimed high) | **dismissed** — factually not introduced by this diff + cited "rule" contradicts the OTEL Observability Principle / AC#2 (rationale below) |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | N/A — Disabled via settings (rule compliance checked by Reviewer below) |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 0 blocking; 1 security dismissed (with rationale); ~9 non-blocking MEDIUM/LOW hardening + test-strengthening items captured as Delivery Findings

## Rule Compliance

Round-3 enumeration against the deferred-eviction delta (`39daf49`):

- **No Silent Fallbacks (CLAUDE.md)** — the round-2 false-eviction breach is RESOLVED. The eviction signal is now TRUE: the deferred pass discards a candidate only if no projectable entity owns its id, so `entity_card.evicted` fires only on a genuine stranding. Empirically verified (pending-first + pre-seeded → `evicted=0`; genuine stranding → `evicted=1`). Compliant.
- **OTEL Observability Principle (CLAUDE.md)** — eviction remains observable (span + `entity_sync.evicted` attr + watcher). The `entity_card.id` on the eviction span is the *intended* GM-panel forensic signal — see security dismissal. Compliant.
- **#6 Test quality / no vacuous assertions** — the round-2 vacuous order-test is REPLACED with a genuine pre-seeded pending-first regression that fails on round-1 code (confirmed by [TEST] high-confidence). Two non-blocking strengthening notes remain (origin-casefold isolation, turn_number counter advance) — neither is vacuous-passing-on-broken-code; the code is correct and the feature is regression-guarded. Compliant (with logged polish).
- **#3 Type annotations** — `eviction_candidates: list[str]` annotated; `npc_card_id` typed; pyright 0 errors. Compliant.
- **Every Test Suite Needs a Wiring Test / No Source-Text Wiring Tests** — dispatch-tier test drives `sync_for_turn` through the production seam with OTEL-span assertions, not source-grep. Compliant.

## Reviewer Observations

- `[VERIFIED][EDGE][TEST]` **The round-2 HIGH is fixed structurally.** `entity_sync.py:214-276`. The pool loop now collects stranded ids into `eviction_candidates` and a deferred second pass (line 271) discards only ids absent from a fully-populated `covered_ids`. Order-independent by construction. **Empirically reproduced the fix myself:** pending-first + pre-seeded store → `evicted=0 present=True`; genuine re-mark-pending → `evicted=1 present=False` (no over-correction). [EDGE] confirms all orderings handled; [TEST] confirms the new regression fails on round-1 code.
- `[VERIFIED][SEC]` `covered_origins` removal is sound. The stateful loop seeds `covered_ids` with `npc_card_id(npc.pool_origin)` (slug-normalized), subsuming the old case-sensitive guard. Evidence: `entity_sync.py:203-205`. [SEC] confirms an attacker-controlled `pool_origin` can only ADD to the protection set (prevent eviction), never cause deletion of another entity's card.
- `[SEC]` **Dismissed — `entity_card.id` in the eviction span is not a leak.** `dispatch/entity_sync.py:249`. (1) **Factually not introduced by this diff** — the attribute was added in the original commit `7561688`; the round-3 delta (`39daf49`) touched only `game/entity_sync.py` + two test files (verified via `git show --name-only`), and round-2 [SEC] already cleared it as "opaque slugs… internal-only; no injection/leak/cross-session vector." (2) The cited rule ("name-derived ids must be opaque in spans") was a Reviewer-supplied paraphrase that **contradicts a stated project rule**: the OTEL Observability Principle (CLAUDE.md) — *"The GM panel is the lie detector… you can't tell whether [a subsystem] is engaged"* — and AC#2 — *"entity_card.evicted with reason=unprojectable so the GM panel can confirm the defensive gate fired"*. Confirming *which* card requires the legible id. The span is a GM/dev-only surface behind Cloudflare Zero Trust (playgroup doctrine: OTEL/GM-panel is dev-side, not player-facing); NPC names are fictional game entities, not PII. Hashing the id would defeat the AC. Per the dismissal rule, this is a valid dismissal citing a different rule with quoted text.
- `[MEDIUM][TEST]` (non-blocking) `test_pending_member_matching_renamed_npc_origin_not_evicted` uses an all-lowercase `pool_origin="borin"`, so it guards origin-slug *seeding* (it fails if the seeding line is removed) but doesn't isolate the *casefold* aspect — a raw `f"npc:{pool_origin}"` would also pass. The casefold path is independently covered by the `BORIN`/`Borin` pool-member tests, so this is test-strengthening, not a coverage hole. Recommend mixed-case origin in a follow-up. Captured as a Delivery Finding.
- `[MEDIUM][TEST]` (non-blocking) The sweep-span `turn_number` assertion compares two reads of a counter that never advances (`sync_for_turn` doesn't `record_interaction`), so both sweeps read 1. It catches an absent/zero attribute but can't distinguish the two sweeps. Recommend advancing the counter between sweeps. Captured as a Delivery Finding.
- `[MEDIUM][EDGE]` (non-blocking) `eviction_candidates` is a `list`; correctness on duplicate slugs currently rests on `store.discard` idempotency (true for the in-memory `EntityStore`, and documented at line 270). Deduping to a `set` would make the invariant explicit and store-implementation-independent. Captured as a Delivery Finding.
- `[LOW][EDGE][SILENT]` (non-blocking) Whitespace-only `name`/`pool_origin` are silently skipped via `ValueError` suppression — benign (a whitespace-named member could never have produced a card to guard or evict) but a `logger.warning` would surface the upstream data-integrity artifact. Pre-existing theme (`NpcPoolMember.name` has no blank/length validator). Captured as a Delivery Finding.
- `[DOC]` (disabled) — Reviewer check: the round-3 docstrings/comments accurately explain the deferred-eviction rationale and the order-independence guarantee. No stale comments.
- `[TYPE]` (disabled) — Reviewer check: pyright 0 errors; `eviction_candidates` typed; no stringly-typed regressions.
- `[SIMPLE]` (disabled) — Reviewer check: the two-phase pass is the minimal structural fix; removing `covered_origins` is a net simplification (one guard set, not two). No over-engineering.
- `[RULE]` (disabled) — Reviewer ran the enumeration above; the round-2 doctrine breach is resolved, no new rule violations.

### Devil's Advocate

Try to break the fix. The deferred pass moves the discard out of the pool loop, so the ordering attack that killed round 2 is dead — I reproduced it and got `evicted=0`. So where else could it bleed? **Over-correction:** could the deferral now RETAIN a card that should be evicted? Walk it: a genuinely stranded member (ratified turn N, re-marked pending turn N+1, no slug-twin) — its id is collected as a candidate, nothing else seeds `covered_ids` with that id, so the deferred pass discards it. Verified: `evicted=1`. The guard only retains when a projectable entity *actually* owns the id this sweep — which is exactly correct. **Namespace bleed:** the eviction pass runs before the faction/location loops populate `covered_ids`, so could an npc candidate be wrongly evicted that a later faction would cover? No — `npc:` and `faction:`/`loc:` are disjoint namespaces (`npc_card_id` hard-codes the prefix), so an npc candidate can never match a faction/location id; the ordering is irrelevant. **Failed-projection twin:** a ratified member that throws in `project_npc_card` never seeds `covered_ids`, so a pending slug-twin's card gets evicted — and that is *right*, because a member that can't project has no live card to protect. **Double-count:** two pending members with the same slug both enqueue the id, but `discard` returns True once then False, so `evicted` counts once — correct today, and the only residual risk (a future non-idempotent store) is a documented, non-blocking hardening note. The security agent's "name leak" is the loudest-sounding finding, but it inverts the project's actual doctrine: the GM panel is the lie-detector and AC#2 *requires* the evicted card's identity to be legible to the GM — an opaque hash would blind the exact person the span exists to inform, and the span never reaches a player. What's left is polish: a test that could isolate casefold more sharply, a turn-counter that could advance, a list that could be a set. None of these is a live defect; all are logged for follow-up. The feature now defends the index honestly — and, unlike round 1 and round 2, the eviction telemetry tells the truth. I tried to make it lie and it wouldn't.

## Reviewer Assessment

**Verdict:** APPROVED

The round-2 HIGH (order-dependent spurious eviction) is **fixed structurally** via deferred two-phase eviction, and I **reproduced the fix empirically** (pending-first + pre-seeded store → `evicted=0, card retained`; genuine stranding → `evicted=1, card evicted` — no over-correction). All three round-2 MEDIUMs are resolved: the case-sensitive `covered_origins` guard is folded into the slug-normalized `covered_ids`; the vacuous order-test is replaced with a genuine pre-seeded regression that fails on round-1 code; the sweep-span assertion is tightened to `len == 2` + count-located evicting sweep. Across five subagents and my own reproduction there are **no Critical/High findings**. The one high-sounding [SEC] finding is dismissed with rationale (factually not in this diff; the cited rule contradicts the OTEL Observability Principle and AC#2, which require the legible card id in the GM-only span). Remaining items are MEDIUM/LOW test-strengthening and hardening polish — captured as non-blocking Delivery Findings.

**Dispatch tags:** [EDGE] order-independence + namespace safety verified · [SILENT] suppress paths benign, eviction signal true · [TEST] new pre-seeded regression genuine (round-1 code fails it); two non-blocking strengthening notes · [SEC] dismissed (not introduced + doctrine-contradicting); per-session isolation clean · [DOC]/[TYPE]/[SIMPLE]/[RULE] (disabled) checked by Reviewer — clean.

**Data flow traced:** dialogue/world NPC name → `NpcPoolMember.name` → (member unprojectable) → candidate `npc_card_id(name)` collected → **deferred pass** discards only if absent from fully-populated `covered_ids` → `result.evicted_ids` → `entity_card.evicted` span + watcher. **Safe** — the discard can no longer fire on an id a projectable entity owns, in any pool order.

**Pattern observed:** two-phase collect-then-act eviction (`entity_sync.py:214-276`) — the correct structural answer to an order-dependent guard.
**Error handling:** projector failures counted loud (`failed`/`failed_refs` + log); blank-name paths skip without stranding; `discard` idempotent.
**Handoff:** To SM (Camina Drummer) for finish-story.

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-04T22:48:09Z
**Round-Trip Count:** 2

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-04 | 2026-06-04T20:34:31Z | 20h 34m |
| implement | 2026-06-04T20:34:31Z | 2026-06-04T20:44:14Z | 9m 43s |
| review | 2026-06-04T20:44:14Z | 2026-06-04T22:11:09Z | 1h 26m |
| implement | 2026-06-04T22:11:09Z | 2026-06-04T22:18:40Z | 7m 31s |
| review | 2026-06-04T22:18:40Z | 2026-06-04T22:30:28Z | 11m 48s |
| finish | 2026-06-04T22:30:28Z | - | - |

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings.

### Dev (implementation — round 3)
- **Improvement** (non-blocking): `world_materialization.py:457` matching existing pool members by exact case-sensitive string (`m.name == name`) is the upstream enabler that lets case-variant slug-twins coexist in `npc_pool` (the precondition for the round-2 HIGH). The round-3 deferred-eviction guard makes the eviction *correct* regardless, but casefold-matching there would prevent the dual-entry-for-one-identity in the first place. Affects `sidequest/game/world_materialization.py` (existing-member lookup). *Found by Dev during implementation.* (Re-affirms the Reviewer's round-1 Improvement finding.)

### Reviewer (code review)
- **Improvement** (non-blocking): `world_materialization` dedupes existing pool members by exact-string name comparison (`m.name == name`), not case-folded. Affects `sidequest/game/world_materialization.py` (the existing-member lookup ~line 457 — should casefold-compare to match Epic-72 NPC identity). This is the upstream enabler that lets two slug-colliding pool entries coexist; the 75-14 HIGH fix (`covered_ids.add`) makes the eviction bug unreachable regardless, but the underlying dual-entry-for-one-identity hazard is worth a separate look. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `_slug` (`sidequest/game/entity_card.py:~186`) replaces only ASCII space, leaving internal Unicode whitespace (NBSP, en-space, etc.) verbatim in card ids — a latent id-consistency gap inherited by `npc_card_id`. Pre-existing, not introduced by 75-14; eviction itself is self-consistent. Consider `re.sub(r"\s+", "_", name.strip().casefold())`. *Found by Reviewer during code review.*

### Reviewer (code review — round 2)
- **Gap** (blocking): the round-1 HIGH fix is order-dependent — `covered_ids` is seeded lazily during the pool loop, leaving the pending-twin-first ordering unguarded. Affects `sidequest/game/entity_sync.py` (eviction guard ~lines 207-230 — needs a pre-pass that seeds `covered_ids` for all `is_projectable` members before any `discard`, or a deferred two-phase eviction). *Found by Reviewer during code review.* — **RESOLVED round 3** (deferred two-phase eviction, commit `39daf49`, empirically verified).
- **Improvement** (non-blocking): `NpcPoolMember.name` has no `max_length` (`sidequest/game/npc_pool.py:~44`); this diff is the first to route the name through a per-turn eviction lookup (`npc_card_id(member.name)`), so an unbounded name becomes an unbounded `EntityStore.cards` key + OTEL span attr. Pre-existing, not introduced here. Consider `Field(max_length=256)`. *Found by Reviewer during code review.*

### Reviewer (code review — round 3)
- **Improvement** (non-blocking): the renamed-origin regression test uses an all-lowercase `pool_origin="borin"`, so it guards origin-slug *seeding* but does not isolate the *casefold* behavior (a raw `f"npc:{pool_origin}"` would also pass). Affects `tests/game/test_entity_sync_defensive_eviction.py::test_pending_member_matching_renamed_npc_origin_not_evicted` (use a mixed-case `pool_origin="Borin"` with pending `"borin"` to exercise the casefold). The casefold path is independently covered by the `BORIN`/`Borin` pool-member tests, so this is strengthening, not a hole. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): the dispatch sweep-span `turn_number` assertion compares two reads of a counter that never advances (`sync_for_turn` doesn't `record_interaction`). Affects `tests/server/dispatch/test_entity_sync_eviction_otel.py` (advance the interaction counter between the index and evict sweeps, then assert distinct turn numbers). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `eviction_candidates` is a `list`; correctness on duplicate slugs rests on `store.discard` idempotency. Affects `sidequest/game/entity_sync.py` (dedupe to a `set` to make the invariant explicit and store-implementation-independent). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): whitespace-only `NpcPoolMember.name` / `Npc.pool_origin` are silently skipped via `ValueError` suppression — benign but a data-integrity artifact worth a `logger.warning`. Affects `sidequest/game/entity_sync.py` (and the pre-existing missing blank/length validator on `NpcPoolMember.name`). *Found by Reviewer during code review.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. Implemented ADR-138 §D5 (defensive eviction of a card stranded on a now-unprojectable member) and §D6 (`entity_card.evicted{reason=unprojectable}` span + watcher count) exactly as specified. The SM-flagged "this story may be unnecessary" caution was investigated and dismissed: the eviction path is genuinely reachable (the `EntityStore` is durable, serialized session state while `observation_pending` is mutable — a member ratified-and-indexed on one turn can be re-marked pending on a later turn, stranding its card), so a real eviction subsystem is warranted, not just an invariant assertion.
  - → ✓ ACCEPTED by Reviewer: the no-deviation claim is accurate (the spec was followed) and the eviction-reachability reasoning is correct. **However**, this is not a clean bill of health — a separate HIGH implementation correctness defect was found (the eviction guard omits ratified pool-member cards from `covered_ids`, enabling a spurious eviction on intra-sweep slug collision). That is an implementation bug, not a spec deviation, so it is logged in the Reviewer Assessment severity table rather than here. The "investigated and dismissed" confidence correctly cleared the *reachability* question but did not cover the *guard-completeness* question.

- **Round-3 rework — deferred two-phase eviction + `covered_origins` removal**
  - Spec source: Reviewer round-2 Assessment, HIGH + MEDIUM (covered_origins) fix-required text
  - Spec text: "pre-pass … *or* two-phase — collect candidate `stranded_id`s during the loop and `discard` only those not in `covered_ids` after the full pool loop"; "Casefold `covered_origins` … *or* seed `covered_ids` with `npc_card_id(npc.pool_origin)`"
  - Implementation: chose the two-phase deferred eviction; removed `covered_origins` entirely and seeded its role into the slug-normalized `covered_ids` via `npc_card_id(npc.pool_origin)`
  - Rationale: both options were Reviewer-sanctioned; the two-phase pass keeps a single eviction site and the slug-only guard removes the case-sensitivity bug at its root rather than patching the comparison
  - Severity: minor
  - Forward impact: none — `covered_origins` had no other consumers; the guard's external behavior (don't evict a card a projectable entity owns) is unchanged and now order-independent

### Reviewer (audit)
- No undocumented spec deviations found. The implementation matches ADR-138 §D5/§D6 intent; the defect is a correctness gap within that intent, captured as a REJECT finding.

### Reviewer (audit — round 2)
- No new spec deviations. Dev's round-2 rework is a faithful (but incomplete) attempt at the round-1 fixes — no scope drift. The remaining HIGH is a guard-completeness correctness gap *within* ADR-138 §D5/§D6 intent, captured in the round-2 Reviewer Assessment, not a deviation.

### Reviewer (audit — round 3)
- **Round-3 rework — deferred two-phase eviction + `covered_origins` removal** → ✓ ACCEPTED by Reviewer: both the two-phase approach and the `covered_origins`→`covered_ids` fold were Reviewer-sanctioned options in the round-2 Assessment. The implementation matches the logged rationale, removes the case-sensitivity bug at its root, and the external guard behavior (never evict a card a projectable entity owns) is preserved and now order-independent — empirically verified. No undocumented deviations.