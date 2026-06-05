---
story_id: "73-12"
jira_key: ""
epic: "73"
workflow: "tdd"
---
# Story 73-12: Rewrite stale combat-lifecycle e2e assertions for the dual-dial encounter model

## Story Details
- **ID:** 73-12
- **Jira Key:** (none — Jira not enabled)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T04:23:51Z
**Round-Trip Count:** 2

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T03:08:36Z | 2026-06-05T03:12:26Z | 3m 50s |
| red | 2026-06-05T03:12:26Z | 2026-06-05T03:46:41Z | 34m 15s |
| green | 2026-06-05T03:46:41Z | 2026-06-05T03:49:39Z | 2m 58s |
| review | 2026-06-05T03:49:39Z | 2026-06-05T03:57:05Z | 7m 26s |
| red | 2026-06-05T03:57:05Z | 2026-06-05T04:06:05Z | 9m |
| green | 2026-06-05T04:06:05Z | 2026-06-05T04:07:47Z | 1m 42s |
| review | 2026-06-05T04:07:47Z | 2026-06-05T04:16:57Z | 9m 10s |
| red | 2026-06-05T04:16:57Z | 2026-06-05T04:18:49Z | 1m 52s |
| green | 2026-06-05T04:18:49Z | 2026-06-05T04:20:15Z | 1m 26s |
| review | 2026-06-05T04:20:15Z | 2026-06-05T04:23:51Z | 3m 36s |
| finish | 2026-06-05T04:23:51Z | - | - |

## Sm Assessment

**Story:** Rewrite the two stale e2e assertions in `tests/e2e/test_encounter_wiring_e2e.py` (de-inerted in 73-6) against the dual-dial encounter model.

**Scope is well-bounded and TDD-shaped:**
- `test_combat_walkthrough_initiate_tick_resolve` reads a removed single `metric` field. The model is now `player_metric` / `opponent_metric` with a `_reject_legacy_metric` validator (ADR-024). Rewrite the assertion against the dual-dial fields.
- `test_xp_award_higher_in_combat_than_out` expects in-combat XP delta 25 but observes 10. Verify the *current* XP-award semantics are correct, then re-baseline the assertion to the true delta — don't blindly pin to 10; confirm what the engine should award in-combat vs out and assert that.

**TEA (RED) note:** Both tests already FAIL on stale assertions, so RED is partly pre-existing. The TDD discipline here is: confirm each failure reproduces, then write the *correct* assertions for the dual-dial model so they fail for the right reason (asserting intended behavior), before Dev makes them green. The XP one needs an actual semantic decision — is the in-combat multiplier intended, and what's the right delta? — not just a number swap. Read ADR-024 (dual-track tension / dual-dial) and the StructuredEncounter model.

**Single repo:** sidequest-server only. Branch `feat/73-12-rewrite-combat-lifecycle-e2e-dual-dial` (base develop).

**Sprint hygiene note (out-of-band):** Setup was initially blocked by a sprint-validator failure — story 84-1 carried `depends_on: 76-7`, but 76-7 is complete and archived, which the validator can't see, so it false-flagged the ref and rejected *all* story updates. Removed the satisfied/archived dependency from epic-84.yaml to unblock. Unrelated to 73-12's implementation.

## TEA Assessment

**Tests Required:** Yes (story IS a test rewrite)

**Test File:** `sidequest-server/tests/e2e/test_encounter_wiring_e2e.py`

**What changed:**
- `test_xp_award_higher_in_combat_than_out` — now deterministic and GREEN. Pins the real XP semantics (10 out-of-combat, 25 in-combat). The 73-6 "observed 10" finding was an unstubbed-intent-router flake, not an XP bug (see Delivery Findings).
- `test_combat_walkthrough_initiate_tick_resolve` → renamed `test_combat_walkthrough_router_initiates_dual_dial_encounter` — rebuilt for the post-ADR-113 architecture. Asserts the CREATION half end-to-end through the real handler: router confrontation dispatch → ADR-116 opponent seating → dual-dial `StructuredEncounter` → `CONFRONTATION` frame → `encounter.confrontation_initiated` span. Dual-dial migration guarded (`not hasattr(enc, "metric")`, both `player_metric`/`opponent_metric` present).
- New `deterministic_combat_router` fixture: stubs `IntentRouter.decompose` to emit a deterministic combat dispatch on the opening turn; the REAL pre-narrator pass + dispatch bank + seating run (genuine wiring, network classification pinned). New `_seat_combat_scene` helper: seats the PC at a location with a hostile NPC so ADR-116 can seat the Other.

**Status:** GREEN — both tests pass deterministically (verified 3× consecutively, ~1s, no network). `ruff check` clean. This is a test-maintenance story: production code is already correct (dual-dial + router-driven creation + 25/10 XP all live), so there is **no Dev implementation work** — the deliverable is the corrected, deterministic, meaningful test file.

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| No Source-Text Wiring Tests (CLAUDE.md) | drives real `_execute_narration_turn` → router dispatch → snapshot encounter + OTEL span (no `read_text`) | passing |
| Every Test Suite Needs a Wiring Test | both tests exercise the real handler/router path end-to-end | passing |
| No Silent Fallbacks | dual-dial migration guard (`not hasattr(enc,"metric")`) + asserts a real encounter lands, no quiet no-op | passing |
| Meaningful assertions (TEA self-check) | every assertion checks a concrete value; no `assert True`/`is None`-on-always-None/`let _ =` | passing |
| Determinism (no live Claude) | `decompose` + narrator both stubbed; 3× consecutive green, no ANTHROPIC_API_KEY needed | passing |

**Rules checked:** 5 of 5 applicable. **Self-check:** 0 vacuous tests (diagnostics removed before commit).

**Handoff:** To Dev — no production work expected (test-only rewrite, already green). Dev confirms GREEN / nothing to implement, then Reviewer.

### TEA Rework (round 2 — addressing Reviewer REJECT)

All three blocking findings + the recommendations fixed (test-only; still no production change):

1. **[TEST/SILENT] vacuous `assert not hasattr(enc, "metric")`** → replaced with a real `with pytest.raises(ValidationError): StructuredEncounter(encounter_type="combat", metric={...})` that actively drives the `_reject_legacy_metric` rejection path. Imports `ValidationError` + `StructuredEncounter`.
2. **[TEST] missing creation-turn XP assertion** → added `assert mid - after_out == 25` after the encounter-opening turn, pinning the in-combat-on-creation claim. XP now read by acting-character name (`_pc_xp()`), not `characters[0]`.
3. **[EDGE] wrong `_fake_decompose` liveness comment** → comment corrected (production sets `resolved=True`, never clears to None) and guard hardened: `has_live_encounter = bool(enc_summary) and not enc_summary.get("resolved", False)`.

Recommendations also done: `_seat_combat_scene` derives the PC name from `characters[0].core.name` (no hard-coded "Rux"); new `tests/e2e/conftest.py` adds an autouse `_stub_intent_router_factory` guard (mirrors `tests/server/conftest.py`) so future e2e tests can't spawn a real Claude client; module docstring softened to call the full router→beat→resolution *handler* path a tracked gap (not "covered").

**Verification:** `test_encounter_wiring_e2e.py` 2/2 GREEN, 3× consecutive, `-n0`, no network; `ruff check` clean. The new autouse conftest is a verbatim copy of the CI-passing server-conftest pattern; verified it does not break collection or the two target tests. (The other `tests/e2e/` WebSocket tests hang on live infra — Postgres/real server — in this headless env regardless of the conftest; pre-existing, confirmed by reproducing the hang with the conftest moved aside.)

**Handoff:** To Dev (GREEN confirm — no production work), then Reviewer.

### TEA Rework (round 3 — addressing Reviewer round-2 REJECT)

Single blocking finding fixed: the `pytest.raises(ValidationError)` guard now carries `match=r"legacy 'metric' field"`, pinning `_reject_legacy_metric`'s own message. Without it the block passed on the unrelated missing-required-dial / `extra="forbid"` ValidationError the same constructor raises, so it couldn't detect a deleted validator. Reviewer's analysis confirmed and applied verbatim. The round-2 LOW/MEDIUM edge nits (hardcoded `player_id`, substring `attack` match, `isinstance` guard, autouse-stub-not-AsyncMock) were explicitly marked non-blocking/optional by the Reviewer and consistent with the canonical server-conftest pattern — left as-is. Verified: 2/2 GREEN, 3× consecutive, `-n0`; ruff clean. **Handoff:** To Dev (GREEN confirm), then Reviewer.

## Dev Assessment

**Implementation Complete:** Yes (no production code required — test-only story)

**Files Changed:**
- `sidequest-server/tests/e2e/test_encounter_wiring_e2e.py` — TEA's rewrite (committed in RED). No further edits by Dev.

**Production changes:** None. The dual-dial model, router-driven encounter creation, and 25/10 XP semantics the tests assert are already live in production. The minimal change to make the tests pass is no change — verified, not assumed.

**Tests:** 2/2 passing (GREEN), verified via testing-runner (`uv run pytest tests/e2e/test_encounter_wiring_e2e.py -n0`, 0.82s). Serial `-n0` per the project's xdist OTEL-deadlock note.

**Self-review:**
- Wired: both tests drive the real `_execute_narration_turn` → router dispatch → snapshot encounter + OTEL span path (no source-text assertions). ✓
- Project patterns: fixture/seating helpers mirror `test_encounter_actors_all_combatants.py` and `test_61_18`. ✓
- ACs met: the two stale tests are rewritten against the dual-dial + router model; XP semantics pinned. Scope reduction (beat→resolution) logged as a deviation with engine-level coverage cited. ✓
- Working tree clean; branch `feat/73-12-rewrite-combat-lifecycle-e2e-dual-dial` pushed.

**Handoff:** To Reviewer (Chrisjen Avasarala). Note for review: this is a test-maintenance rewrite that surfaced a far larger scope than the story title (4 changed contracts post-ADR-113) — the key judgment call is the deliberate scope reduction of the walkthrough test to its creation half (deviation logged, engine-level coverage intact).

### Dev Rework (round 2)

GREEN re-confirmed after TEA addressed all three Reviewer REJECT findings + recommendations (see TEA Rework note above). No production code changed — still a test-only story. Verified via testing-runner: 2/2 GREEN (`-n0`, 0.80s, no network). Working tree clean; two rework commits (`251b35f`, `4b99fbd`) pushed to `origin/feat/73-12-rewrite-combat-lifecycle-e2e-dual-dial`. New `tests/e2e/conftest.py` autouse guard confirmed not to break the two target tests or collection. **Handoff:** To Reviewer for re-review.

### Dev Rework (round 3)

GREEN re-confirmed after TEA added `match=r"legacy 'metric' field"` to the `pytest.raises` block (round-2 Reviewer finding). No production change. 2/2 GREEN (`-n0`, 0.79s, no network); tree clean; commit `7495f9a` pushed. **Handoff:** To Reviewer for re-review (only the one-line `match=` differs from the previously-reviewed round-2 state).

## Subagent Results (Round 1 — superseded)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A (GREEN 2/2, ruff clean, 0 smells) |
| 2 | reviewer-edge-hunter | Yes | findings | 1 high, 2 med, 2 low | confirmed 1, deferred 4 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 high, 2 med, 1 low | confirmed 1, dismissed 1, deferred 2 |
| 4 | reviewer-test-analyzer | Yes | findings | 2 high, 2 med, 1 low | confirmed 2, deferred 3 |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 1 med | confirmed 1 (non-blocking) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 3 confirmed blocking-as-rework, 3 confirmed non-blocking, 1 dismissed, several deferred (low-value future-coupling nits)

## Rule Compliance

Applicable rules for a test-only Python diff (from CLAUDE.md / SOUL.md / server CLAUDE.md):

- **"Every test must assert something meaningful"** — enumerated every assertion in both tests:
  - `test_combat_walkthrough_router_initiates_dual_dial_encounter`: `enc is not None`, `encounter_type == "combat"`, `not resolved`, `sides` has player+opponent, `player_metric.current == 0`, `opponent_metric.current == 0`, thresholds `> 0`, `len(conf) == 1`, payload active + dual-dial currents, `confrontation_initiated` span — all meaningful EXCEPT `assert not hasattr(enc, "metric")` → **VIOLATION** (vacuous: a Pydantic model with no declared `metric` field can never have the attribute; the comment claims it proves `_reject_legacy_metric` rejection, which it does not). Confirmed by [SILENT] + [TEST].
  - `test_xp_award_higher_in_combat_than_out`: `after_out - before == 10`, `after_combat - mid == 25` — meaningful. **GAP**: the creation turn's XP (`mid - after_out`) is read but never asserted, though the comment claims that turn is in-combat (25). Confirmed by [TEST].
- **"No Source-Text Wiring Tests"** — COMPLIANT. Both tests assert via OTEL spans (`encounter.confrontation_initiated`) and fixture-driven behavior (real `_execute_narration_turn` → router dispatch → snapshot encounter). No `read_text()`/source-grep. ✓
- **"Every Test Suite Needs a Wiring Test"** — COMPLIANT. Both drive the real handler/router path end-to-end. ✓
- **"Tests MUST NOT spawn a real Claude client"** — COMPLIANT for the two tests in the diff (both declare `deterministic_combat_router`, which patches `build_intent_router_for_session`; orchestrator is `MagicMock`). [SEC] notes a defense-in-depth gap: no `tests/e2e/conftest.py` autouse guard for FUTURE tests — recommended, non-blocking.
- **"No Silent Fallbacks"** — COMPLIANT. `_fake_decompose` falls back to an explicit `_empty_package()` (intentional no-encounter state), not a hidden alternative. ✓

## Devil's Advocate

Argue this change is broken. The headline risk: the test *looks* thorough but quietly under-pins the very behaviors it advertises. The walkthrough test's docstring promises "creation half end-to-end," and it largely delivers — but `assert not hasattr(enc, "metric")` is decorative. A reader sees a dual-dial-migration guard; the runtime sees a tautology that holds for any Pydantic model lacking the field. If someone deleted `_reject_legacy_metric` tomorrow, this assertion stays green — the comment lies about what protects the invariant. That's worse than no assertion: it manufactures false confidence in a test-quality story.

The XP test is the sharper miss. Its own comment asserts a non-trivial ordering claim — that `award_turn_xp` sees `in_combat=True` *on the turn the encounter is created*, because the router opens it pre-narrator. That is exactly the kind of off-by-one the 73-6 flake was made of (`in_combat_now` evaluated relative to encounter commit timing). Yet `mid` is captured and never compared to `after_out`. A regression that made the creation turn award 10 (encounter committed after the XP check) sails through green. The test pins the *second* combat turn and leaves the interesting one — the boundary turn — unguarded.

A confused future author is the third victim. `_fake_decompose`'s comment states resolved encounters are "cleared from the snapshot by the lifecycle"; [EDGE] verified production does no such thing (it flips `resolved=True` on the live object). The stub works today only because `"Again!"` lacks the substring `"attack"` — not because of the liveness guard the comment credits. Copy this fixture into a test with a resolved-then-attack turn and it silently refuses to re-open the encounter, surfacing as a baffling `enc is None` three asserts later. And `tests/e2e/` has no autouse Claude-client guard, so an unguarded future test spends real API credits if `ANTHROPIC_API_KEY` is set. None of these break the two tests as written — but in a story whose deliverable IS meaningful assertions, shipping a vacuous one + an unasserted documented claim + a factually wrong comment is the failure mode the review exists to catch.

## Reviewer Assessment (Round 1 — REJECTED, superseded)

**Verdict:** REJECTED

This is a test-only diff (`tests/e2e/test_encounter_wiring_e2e.py`, +215/-87, no production change). Preflight is clean (GREEN 2/2, ruff clean, 0 smells) and the rewrite's architecture is correct — the router-driven creation model, ADR-116 seating fixture, dual-dial assertions, and the determinism fix are all sound work, and the diagnosis behind it (the 73-6 XP flake = unstubbed router) is excellent. I am rejecting only because the story's deliverable *is* meaningful test assertions, two subagents independently flagged a vacuous assertion that matches a stated project rule (which I may not dismiss), and the most interesting behavioral claim in the XP test is documented but never asserted. All three required fixes are small.

**Data flow traced:** player action `"I attack!"` → stubbed `decompose` emits a `confrontation/combat` `SubsystemDispatch` (conf 0.95) → real `execute_intent_router_pre_narrator_pass` → real `run_dispatch_bank` → `run_confrontation_dispatch` → ADR-116 location-roster seating (PC Rux + hostile NPC from `_seat_combat_scene`) → `StructuredEncounter` on the snapshot → `ConfrontationMessage` + `encounter.confrontation_initiated` span. Genuine end-to-end wiring; the only stubbed link is the LLM classification. Verified sound.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM] [TEST][SILENT] | `assert not hasattr(enc, "metric")` is vacuous — a Pydantic model with no declared `metric` field can never expose the attribute, so it can't fail; the comment falsely claims it proves `_reject_legacy_metric` rejection. Matches the "every test must assert something meaningful" project rule (two subagents, high confidence — cannot be dismissed). | `test_encounter_wiring_e2e.py` ~line 299 | Remove the line (the following `player_metric`/`opponent_metric` positive assertions already carry the dual-dial coverage), OR replace it with a real guard: `with pytest.raises(ValidationError): StructuredEncounter(..., metric={...})`. Fix or drop the misleading comment. |
| [MEDIUM] [TEST] | XP test never asserts the **creation-turn** award. `mid` is read after the `"I attack."` turn but never compared to `after_out`, even though the comment claims that turn is in-combat (25). The exact off-by-one the 73-6 flake was made of (encounter-commit vs `in_combat_now` timing) would pass green. | `test_encounter_wiring_e2e.py` ~line 332 | Add `assert mid - after_out == 25` (creation turn is in-combat) so the documented claim is pinned. |
| [MEDIUM] [EDGE] | `_fake_decompose` liveness comment is factually wrong — production does NOT clear `snapshot.encounter` to None on resolution (it sets `resolved=True` on the live object). The stub works today only because `"Again!"` lacks the `"attack"` substring, not because of the liveness guard the comment credits. Latent trap for any future resolved-then-attack turn. | `test_encounter_wiring_e2e.py` ~line 117-124 | Correct the comment, and harden the check: `has_live_encounter = bool(state_summary.get("encounter") and not state_summary["encounter"].get("resolved", False))`. |

**Recommended (non-blocking — fix opportunistically while reworking):**
- [SEC] Add `tests/e2e/conftest.py` with an autouse fixture that stubs `build_intent_router_for_session` (mirror `tests/server/conftest.py`'s `_stub_intent_router_factory`), so future e2e tests can't spawn a real Claude client. Current two tests comply; this is defense-in-depth.
- [EDGE][TEST] Derive the PC name from `sd.snapshot.characters[0].core.name` instead of hard-coding `"Rux"` in `_seat_combat_scene`; pin the XP assertion to the acting character by name rather than `characters[0]`.
- [TEST] Soften the docstring's "covered deterministically at the engine level" to acknowledge the full handler-path resolution gap TEA already filed.

**Dispatch tag coverage:** [EDGE] confirmed (liveness comment + fragilities) · [SILENT] confirmed (vacuous hasattr) · [TEST] confirmed (vacuous assertion + missing XP creation-turn assertion) · [SEC] confirmed non-blocking (missing e2e conftest guard) · [DOC] N/A (comment_analyzer disabled — I covered comment accuracy directly: the two misleading comments are in the table) · [TYPE] N/A (type_design disabled — no type changes in a test-only diff) · [SIMPLE] N/A (simplifier disabled — no over-engineering observed; the fixture mirrors existing patterns) · [RULE] N/A (rule_checker disabled — I performed the rule enumeration directly in the Rule Compliance section; the meaningful-assertions violation is the result).

**Dismissed:** [SILENT] production finding — `apply_resource_patches` bare-except + missing OTEL span at `websocket_session_handler.py:1297`. Dismissed from THIS story's blocking set: it is pre-existing production code NOT in the diff (`git diff develop...HEAD` is the test file only). Recorded as a non-blocking Delivery Finding for a future story.

**Handoff:** Back to TEA (Amos Burton) for the three rework items — these are test-design changes (green→red rework).

## Subagent Results (Round 2 — superseded)

(Round 2 re-review of the rework diff — `tests/e2e/test_encounter_wiring_e2e.py` +344/-92 and new `tests/e2e/conftest.py`.)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A (GREEN 2/2, ruff clean, 0 smells, hermetic) |
| 2 | reviewer-edge-hunter | Yes | findings | 1 med, 3 low | deferred 4 (future-coupling nits) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 high, 1 low | confirmed 1 (blocking), deferred 1 |
| 4 | reviewer-test-analyzer | Yes | findings | 1 high, 1 med | dismissed 1 (false positive, with evidence), deferred 1; confirmed all 3 round-1 fixes |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A (round-1 guard gap resolved by new conftest; fixture ordering verified) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 1 confirmed blocking (the `match=` gap), 1 dismissed (false positive, evidence below), 4 deferred non-blocking nits. All three round-1 REJECT findings verified FIXED.

### Round-1 fix verification

- **Vacuous `hasattr`** → replaced with `pytest.raises(ValidationError)` driving `_reject_legacy_metric`. Structurally correct (but see blocking finding below — needs `match=`). [TEST][SILENT]
- **Missing creation-turn XP assertion** → `assert mid - after_out == 25` present; XP read by acting-character name via `_pc_xp()`. FIXED. [TEST]
- **Wrong liveness comment** → comment corrected + guard hardened (`not enc_summary.get("resolved", False)`). FIXED. [EDGE]
- **Missing e2e Claude-client guard** → `tests/e2e/conftest.py` autouse `_stub_intent_router_factory` added; security confirms compliance + correct fixture ordering. FIXED. [SEC]

### Dismissed (false positive)

- [TEST] "XP test dead third-call assertion — 2-element `side_effect` exhausted on the `Again!` turn → `StopIteration` → final assert unreachable." **DISMISSED with evidence:** the `"I walk."` turn consumes the SEPARATE first mock (`AsyncMock(return_value=...)`); the 2-element `side_effect` mock is installed afterward and consumed by exactly two calls (`"I attack."`, `"Again!"`). Preflight + a direct run both show the test PASSES (`1 passed`) — an exhausted `side_effect` would raise `StopIteration` and ERROR, not pass. The analyzer miscounted by attributing `"I walk."` to the `side_effect` list. Verified empirically.

## Rule Compliance (Round 2)

- **"Every test must assert something meaningful"** — round-1 vacuous `hasattr` is gone. The replacement `pytest.raises(ValidationError)` is **still partially vacuous** (VIOLATION, blocking — see assessment): it lacks a `match=`, and the constructor omits the required `player_metric`/`opponent_metric`, so a deleted `_reject_legacy_metric` would still raise `ValidationError` (missing fields) and the block would pass. Empirically verified: `StructuredEncounter(encounter_type="combat")` raises `ValidationError` on missing dials. The XP assertions and dual-dial assertions are meaningful. ✓ except the one block.
- **"Tests MUST NOT spawn a real Claude client"** — COMPLIANT, now structurally (autouse conftest) + per-test. ✓
- **"No Source-Text Wiring Tests"** — COMPLIANT (OTEL span + behavior assertions). ✓
- **"No Silent Fallbacks"** — COMPLIANT. ✓

## Devil's Advocate (Round 2)

The rework is genuinely good — three findings fixed, a structural Claude-client guard added, security clean. But the fix to the headline round-1 finding reintroduced the same flaw one layer down. `with pytest.raises(ValidationError): StructuredEncounter(encounter_type="combat", metric={...})` *looks* like it proves the legacy-field validator fires — but the constructor is missing both required dials, so Pydantic raises `ValidationError` for missing fields irrespective of `_reject_legacy_metric`. Delete the validator and the test stays green. It is the round-1 vacuity wearing a `pytest.raises` costume: it asserts "constructing this raises," not "the legacy field is rejected." In a story whose entire deliverable is meaningful assertions, that is precisely the regression the review must not wave through — and waving it through after rejecting the identical class in round 1 would be incoherent. The remedy is one token: `match=r"legacy 'metric' field"`. Everything else (edge-hunter's substring/`player_id`/`isinstance` nits) is future-coupling that no current test reaches; the autouse-stub-not-AsyncMock observation is deliberately consistent with the canonical `tests/server/conftest.py` and inspects nothing today. None of those block. The `match=` does.

## Reviewer Assessment (Round 2 — REJECTED, superseded)

**Verdict:** REJECTED

The rework correctly closed all three round-1 findings and added the recommended Claude-client guard — strong, responsive work. I am rejecting on a single new, high-confidence, empirically-verified issue: the replacement for the round-1 vacuous assertion is itself partially vacuous, and it matches the meaningful-assertions project rule (which I may not dismiss). One-line fix.

**Data flow traced:** unchanged from round 1 and still sound — player action → stubbed `decompose` (combat dispatch) → real pass/bank/ADR-116 seating → dual-dial encounter → CONFRONTATION frame → OTEL span. New autouse conftest guard verified to not leak into the combat tests (monkeypatch LIFO; `deterministic_combat_router` applied after the autouse default wins).

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM] [SILENT] | `with pytest.raises(ValidationError): StructuredEncounter(encounter_type="combat", metric={...})` is partially vacuous — the constructor omits the required `player_metric`/`opponent_metric`, so it raises `ValidationError` (missing fields) even if `_reject_legacy_metric` is deleted; the block can't distinguish "validator fires" from "missing fields." Verified: `StructuredEncounter(encounter_type="combat")` raises ValidationError. Matches the meaningful-assertions rule (same class as the round-1 reject). | `test_encounter_wiring_e2e.py` (the `pytest.raises` block, ~line 267) | Add `match=r"legacy 'metric' field"` (the validator's message) so the block pins the legacy-rejection path specifically: `with pytest.raises(ValidationError, match=r"legacy 'metric' field"):`. |

**Recommended (non-blocking — optional, fix opportunistically):**
- [EDGE] `_combat_package` hardcodes `player_id="player-1"`; aligns with the factory default and `_normalize_per_player_ids` rewrites it anyway, but pass `sd.player_id` if you want to decouple. (medium-confidence future-coupling)
- [EDGE] `_fake_decompose`: `"attack" in action.lower()` substring would false-fire on `"counterattack"` on an opening turn; word-boundary match avoids it. No current test reaches this. (low)
- [EDGE] add `state_summary: dict` annotation / isinstance guard in `_fake_decompose`. (low)
- [TEST][EDGE] autouse stub uses a plain `async def` rather than `AsyncMock` — intentionally consistent with `tests/server/conftest.py`; only matters if a future test wants `.call_count`. (low — no change recommended; keep parity with the canonical pattern)

**Dispatch tag coverage:** [SILENT] confirmed blocking (`match=` gap) · [TEST] round-1 fixes verified + 1 false-positive dismissed with evidence · [EDGE] 4 low/med future-coupling nits deferred · [SEC] clean (guard gap resolved) · [DOC] N/A (disabled — comment accuracy checked directly; the corrected liveness comment is sound) · [TYPE] N/A (disabled — no type changes) · [SIMPLE] N/A (disabled — no over-engineering; conftest mirrors canonical pattern) · [RULE] N/A (disabled — rule enumeration performed directly in Rule Compliance above; the meaningful-assertions violation is the result).

**Handoff:** Back to TEA (Amos Burton) for the one-line `match=` fix (green→red rework).

## Subagent Results

(Round 3 re-review. The only delta since round 2 is the one-line `match=r"legacy 'metric' field"` added to the `pytest.raises(ValidationError)` block — the exact fix the round-2 REJECT prescribed.)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A (GREEN 2/2, ruff clean, 1-line diff) |
| 2 | reviewer-edge-hunter | Yes | clean | none | N/A (`match=` regex correct; apostrophe not a metachar; Pydantic v2 preserves the message) |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A (round-2 finding FULLY RESOLVED — competing error paths don't match the pattern; `mode="before"` ordering confirmed) |
| 4 | reviewer-test-analyzer | Yes | clean | none | N/A (assertion now meaningful; XP "dead assertion" false-positive re-confirmed) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none | N/A (test-only string literal; no secret/real-client path; conftest guard unchanged) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (5 enabled returned, 4 disabled pre-filled)
**Total findings:** 0 — all five enabled specialists clean. The round-2 blocking finding is resolved; all round-1 findings remain fixed.

## Rule Compliance (Round 3)

- **"Every test must assert something meaningful"** — NOW FULLY COMPLIANT. The `pytest.raises(ValidationError, match=r"legacy 'metric' field")` pins `_reject_legacy_metric`'s own message; verified the competing `extra="forbid"`/missing-field `ValidationError`s carry different text, so the block fails if the validator is deleted. The round-1 vacuous `hasattr` and the round-2 match-less partial-vacuity are both closed. All other assertions (dual-dial values, XP 10/25 incl. creation-turn, ConfrontationMessage payload, OTEL span) are concrete and meaningful.
- **"Tests MUST NOT spawn a real Claude client"** — COMPLIANT (autouse conftest guard + per-test stub; security clean). ✓
- **"No Source-Text Wiring Tests"** — COMPLIANT (OTEL span + behavior). ✓
- **"No Silent Fallbacks"** — COMPLIANT. ✓

## Devil's Advocate (Round 3)

The hardest remaining attack on this test is "the `match=` could still pass for the wrong reason" — and three independent specialists chased exactly that and came back empty. The validator is a `mode="before"` model_validator, so when `metric=` is supplied it fires before field-presence and `extra="forbid"` checks; its message (`"...legacy 'metric' field is rejected..."`) is what lands in the `ValidationError`, and `re.search(r"legacy 'metric' field", ...)` finds it. Delete the validator and the *only* remaining raises are `"Extra inputs are not permitted"` and `"Field required"` — neither matches the pattern, so the block fails loudly. That is a genuine validator-presence guard now, not a costume. The other angles are exhausted: the determinism (both LLM seams stubbed), the Claude-client guard (autouse conftest, security-clean), the XP boundary turn (creation-turn award pinned), and the false-positive "dead assertion" (the test passes; `"I walk."` uses a separate mock). The remaining edge-hunter nits (hardcoded `player_id`, substring `attack`, missing `isinstance`) are future-coupling on code paths no current test reaches, and the autouse-stub-not-`AsyncMock` is deliberately faithful to the canonical server conftest. Nothing here blocks; the only honest verdict is APPROVE.

## Reviewer Assessment

**Verdict:** APPROVED

The single round-2 blocking finding (partially-vacuous `pytest.raises`) is resolved by the prescribed one-line `match=`, and all five enabled specialists return clean on the round-3 diff. All three round-1 findings were verified fixed in round 2, the recommended Claude-client guard was added, and across the three rounds the test file became materially stronger: a real validator-presence guard, a pinned creation-turn XP award, a hardened liveness check, character-name-pinned XP reads, and a structural e2e Claude-client guard.

**Data flow traced:** player action `"I attack!"` → stubbed `decompose` (deterministic combat dispatch) → real `execute_intent_router_pre_narrator_pass` → real `run_dispatch_bank` → `run_confrontation_dispatch` → ADR-116 location-roster opponent seating → dual-dial `StructuredEncounter` on the snapshot → `ConfrontationMessage` (active, dual-dial payload) → `encounter.confrontation_initiated` OTEL span. Genuine end-to-end handler wiring with only the LLM classification pinned. Safe.

**Pattern observed:** the rework consistently mirrors established patterns — `_seat_combat_scene` ← `tests/server/test_encounter_actors_all_combatants.py`; deterministic `DispatchPackage` ← `tests/agents/test_61_18_confrontation_trigger_sdk_path.py`; `tests/e2e/conftest.py` ← `tests/server/conftest.py`'s `_stub_intent_router_factory`.

**Error handling:** the `pytest.raises(ValidationError, match=...)` exercises the real `_reject_legacy_metric` rejection path (`sidequest/game/encounter.py:233`) and now fails if that validator is removed.

**Dispatch tag coverage:** [SILENT] clean (round-2 finding resolved) · [TEST] clean (meaningful assertion; false-positive re-confirmed) · [EDGE] clean (`match=` regex verified) · [SEC] clean (no new concern; guard intact) · [DOC] N/A (disabled — comment accuracy checked directly; the round-3 comment correctly explains the `match=` rationale) · [TYPE] N/A (disabled — no type changes) · [SIMPLE] N/A (disabled — one-line addition, no complexity) · [RULE] N/A (disabled — rule enumeration done directly in Rule Compliance; meaningful-assertions rule now satisfied).

**Scope note (accepted, not a blocker):** this is a test-only story; production code was already correct (dual-dial + router-driven creation + 25/10 XP). The walkthrough's beat-tick→resolution-through-the-handler coverage was deliberately scoped out (deviation ACCEPTED round 1; tracked as a delivery-finding Gap with engine-level coverage intact).

**Handoff:** To SM (Camina Drummer) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The 73-6 "in-combat XP observed 10" finding is a symptom of an unstubbed intent-router pass, not an XP bug. The XP semantics are correct (`award_turn_xp`: 25 in-combat / 10 otherwise). The flaky "10" happened when the real (network) `IntentRouter.decompose` failed to classify the turn as combat, so no encounter was created → `in_combat_now` False → 10. Fixed by stubbing `decompose` deterministically. Affects `tests/e2e/test_encounter_wiring_e2e.py` (now green/deterministic) — no production change needed.
- **Gap** (non-blocking): No e2e/handler-level test drives the full combat beat-tick → threshold/HP-depletion → resolution lifecycle through `DICE_THROW`. The 73-12 rewrite covers creation through the handler and the lifecycle at the engine level only. Affects a future story: add a combat-capable session fixture (PC + opponent with wired combatant `CreatureCore`/stats so the dice-path `edge_resolver` resolves the opponent) and drive `handle_message(DICE_THROW)` to resolution. *Found by TEA during test design.*
- **Question** (non-blocking): Worth confirming the dual-dial momentum semantics for caverns_and_claudes combat are intended — a plain "attack" (kind=strike) debits opponent edge/HP and does NOT advance the momentum `player_metric`. If `dial_threshold` combat is meant to resolve via momentum, which beats advance the player dial? (Surfaced while rebuilding the walkthrough; not blocking 73-12.) Affects `sidequest/game/beat_kinds.py` / caverns combat beat defs. *Found by TEA during test design.*
- **Note** (non-blocking): `pf sprint story update` required hand-editing `sprint/epic-84.yaml` to drop a `depends_on: 76-7` that points at an archived story (SM already handled; recorded here for traceability — the validator can't see archived stories).

### Dev (implementation)
- No upstream findings during implementation. TEA's RED-phase findings already capture the substantive scope discoveries (XP root cause, missing beat→resolution handler coverage, the strike-vs-momentum question). Verified GREEN (2/2, `-n0`) against unchanged production code; nothing further surfaced.

### Reviewer (code review)
- **Improvement** (non-blocking): `apply_resource_patches` is wrapped in a bare `except Exception` that logs a warning and silently sets `crossed_thresholds = []`, with no OTEL span on the failure path. Affects `sidequest/server/websocket_session_handler.py:~1297` (add a `resource.patch_exception` span so the GM-panel lie-detector can see silently-dropped patch failures — per the OTEL Observability Principle). Pre-existing production code, NOT in this diff — for a future story. *Found by Reviewer during code review.*
- **Gap** (non-blocking): `tests/e2e/` has no `conftest.py` autouse guard against spawning a real Claude client (the `tests/server/` autouse stubs don't apply to the sibling dir). Affects `sidequest-server/tests/e2e/` (add a conftest mirroring `tests/server/conftest.py`'s `_stub_intent_router_factory`). The two tests in this diff comply individually; this protects future e2e tests. *Found by Reviewer during code review.* → **RESOLVED in round-2 rework** (new `tests/e2e/conftest.py` added).
- No new upstream findings during round-2 code review. The single blocking item (partially-vacuous `pytest.raises` lacking `match=`) is recorded in the round-2 Reviewer Assessment severity table; all other round-2 subagent findings are deferred non-blocking future-coupling nits. *Found by Reviewer during code review (round 2).*
- No new upstream findings during round-3 code review. The `match=` fix resolved the sole round-2 blocker; all five enabled specialists clean. APPROVED. *Found by Reviewer during code review (round 3).*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Dropped the beat-tick → threshold → resolution half of the combat walkthrough**
  - Spec source: story title 73-12 ("Rewrite stale combat-lifecycle e2e assertions … rewrite against StructuredEncounter dual-dial model"); SM Assessment ("write the correct assertions for the dual-dial model").
  - Spec text: the original `test_combat_walkthrough_initiate_tick_resolve` asserted the full lifecycle — attack/shield_bash beats advance the momentum dial to threshold_high=10 → resolution.
  - Implementation: the rewritten `test_combat_walkthrough_router_initiates_dual_dial_encounter` asserts only the CREATION half (router dispatch → ADR-116 seating → dual-dial encounter → CONFRONTATION frame → `encounter.confrontation_initiated` span). The XP test still pins in-combat XP semantics.
  - Rationale: the story scoped this as an assertion rewrite, but post-ADR-113 the test's whole driving model is dead across FOUR contracts — (1) creation is router-driven not `result.confrontation` (Story 59-4), (2) PC beats arrive via DICE_THROW not narrator `beat_selections` (SOUL "The Test" gate rejects inferred PC beats), (3) dual-dial `player_metric`/`opponent_metric` (ADR-024), (4) a caverns "attack" (strike) debits opponent edge/HP, not the momentum dial — so the original "dial crosses threshold via attack beats" scenario is not reproducible as written. Driving beats→resolution through the handler additionally needs fully-wired opponent combatant cores in the synthetic session (the dice-path edge_resolver). The beat→resolution lifecycle is already covered deterministically at the engine level (`tests/integration/test_combat_otel_wiring.py` constructs the encounter + cores and calls `apply_beat`; `tests/server/test_confrontation_dispatch_wiring.py` drives resolution). Re-creating it through the handler is a fixture lift beyond a stale-assertion rewrite.
  - Severity: minor
  - Forward impact: handler-level e2e coverage of beat-tick→resolution is a documented follow-up (see Delivery Findings). Engine-level coverage is intact, so no net coverage loss for the mechanics themselves.

### Dev (implementation)
- No deviations from spec. This is a test-only story; production code already implements the dual-dial + router-driven creation + 25/10 XP semantics the tests assert. No implementation changes were made — TEA's rewrite is GREEN against current production code, so the minimal change that makes the tests pass is no change.

### Reviewer (audit)
- **TEA: "Dropped the beat-tick → threshold → resolution half of the combat walkthrough"** → ✓ ACCEPTED by Reviewer: the scope reduction itself is sound — the four changed contracts and the DICE_THROW/combatant-core fixture lift are real, and re-architecting full handler-path resolution is genuinely out of scope for a stale-assertion rewrite. One caveat (does NOT reverse the acceptance): the rationale's "covered deterministically at the engine level" slightly overstates it — `test_combat_otel_wiring.py` calls `apply_beat` directly and `test_confrontation_dispatch_wiring.py` pre-seats the encounter, so the *full router→beat→resolution handler path* remains uncovered. TEA already filed that as a Gap delivery finding, so the hole is tracked. The docstring should soften "covered at the engine level" to "the beat/resolution *mechanics* are covered at the engine level; full handler-path resolution is a tracked gap" (folded into the rework list as a minor item).
- **Dev: "No deviations from spec"** → ✓ ACCEPTED by Reviewer: confirmed — no production code changed; `git diff develop...HEAD` is the single test file only.
- **Round 2:** No new deviations logged by TEA/Dev in the rework. The diff is still test-only (`tests/e2e/test_encounter_wiring_e2e.py` + new `tests/e2e/conftest.py`); the scope-reduction deviation stands as ACCEPTED above. The docstring coverage claim was softened in rework (the round-1 caveat), which I accept as fully addressing my audit note.
- **Round 3:** No new deviations. The only change is the one-line `match=` addition. All logged deviations remain ACCEPTED. ✓ Audit complete.