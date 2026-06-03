---
story_id: "72-11"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 72-11: Pregen MAX_CULTURES=4 cap silently drops world cultures from the seeded NPC roster — scale to the world's culture count (coyote_star: voidborn excluded; surfaced by 71-31)

## Story Details
- **ID:** 72-11
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Acceptance Criteria

1. **SCALE (all cultures seeded):** seed_manual for a world declaring N cultures seeds NPCs from ALL N cultures (N * NPCS_PER_CULTURE NPCs), not capped at 4. Verified with a >=5-culture world (coyote_star -> 5 cultures incl voidborn -> 15 NPCs), asserting an NPC with culture=voidborn was added. The [:MAX_CULTURES] slice is gone.

2. **NO SILENT DROP (fail-loud) + dead-code removal:** the MAX_CULTURES=4 constant (pregen.py:48) and its slice (pregen.py:225) are removed; effective_cultures(world) is honored in full. The fix does NOT bump the cap to 5 and does NOT introduce random sub-sampling. If any future guardrail ever drops a culture it MUST be observable (WARNING log + span flag), never a silent slice (CLAUDE.md No Silent Fallbacks).

3. **OTEL CONTRACT (lie-detector, the load-bearing AC):** the pregen.seed_manual span exposes BOTH effective_culture_count (pre-seed, the world truth) AND the seeded culture count; for coyote_star both = 5 with cultures_source=world. Asserted by driving the REAL seed_manual and reading the emitted span attributes (OTEL span assertion) — NOT by grepping source (CLAUDE.md No Source-Text Wiring Tests).

4. **BEHAVIORAL WIRING TEST (extends tests/server/dispatch/test_pregen.py):** a >=5-culture fixture/world drives the real seed_manual and asserts BOTH (a) a culture=voidborn NPC was added to the manual AND (b) the pregen.seed_manual span fired with effective_culture_count == seeded_count == 5. This closes the regression hole that let the bug ship (no current test exercises >=5 cultures).

5. **NO REGRESSION:** existing pregen tests stay green — 2-culture seed (6 NPCs), no-culture fallback (DEFAULT_NPC_FALLBACK_COUNT=9), pack-load-failure fallback, dedup-keeps-unique-names, and the caverns_and_claudes e2e. Server suite green; ruff + pyright clean.

## Story Context

**Type:** refactor  
**Points:** 3  
**Priority:** p3  
**Repos:** sidequest-server  
**Affected Modules:** sidequest/server/dispatch/pregen.py, telemetry/spans/pregen.py, tests/server/dispatch/test_pregen.py

**Problem Summary:**  
pregen.seed_manual() silently drops world cultures beyond the first 4 due to a hardcoded [:MAX_CULTURES] slice (pregen.py:225). This is a Rust-port artifact with no design rationale. For coyote_star (5-culture world), the voidborn culture never seeds NPCs because it sorts last alphabetically. The OTEL span compounds the lie by reporting the post-cap count (4) as fact.

**Design Direction (Architect, 2026-06-02):**
- DELETE the [:MAX_CULTURES] slice and MAX_CULTURES=4 constant
- Honor all effective_cultures() results in full
- Add effective_culture_count + seeded_culture_count to pregen.seed_manual span
- Ensure voidborn and all configured cultures seed appropriately
- No random sampling, no bumping the cap — world author's culture list is the bound

**SEAM:**
- sidequest/server/dispatch/pregen.py (remove slice + constant, update NPC generation loop)
- telemetry/spans/pregen.py (add span attributes)
- tests/server/dispatch/test_pregen.py (add >=5-culture regression test + span assertions)

## Sm Assessment

**Setup complete — routing to TEA (red phase).**

- **Story:** 72-11 (epic 72, NPC Identity Hardening). 3pts, p3, tdd, single repo `sidequest-server`. No Jira (personal project).
- **Branch:** `feat/72-11-pregen-scale-cultures`, cut clean from a freshly-synced `develop` (server gitflow base).
- **Spec provenance:** the 5 ACs + design direction were authored by the Architect (White Queen) directly against the real seam (`pregen.py:48,225`; span at `pregen.py:317-330`). Decision-complete: no ADR, no content change (coyote_star already declares voidborn). TEA writes failing tests first against these ACs.
- **Merge gate:** clear. The only blocker was orphan PR #588 (`feat/nl-equip-intent`, NL equip intent) — squash-merged to `develop` at operator instruction (unreviewed, no CI; bundled `test_equip_dispatch.py` is the safety net). No open PRs remain in any repo.
- **Load-bearing AC:** #3 (OTEL contract) — the span must expose `effective_culture_count` vs seeded count so this silent-drop class is never invisible again. Asserted via real span emission, not source grep (CLAUDE.md No Source-Text Wiring Tests).
- **Watch-out for TEA:** do NOT let a fix that merely bumps the cap to 5 pass — AC1+AC4 must exercise a ≥5-culture world and assert a `culture=voidborn` NPC seeds. The regression hole (no test exercises ≥5 cultures) is what let this ship.

## Workflow Tracking
**Workflow:** tdd  
**Phase:** finish  
**Phase Started:** 2026-06-03T02:25:28Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-02T00:00:00Z | 2026-06-03T01:38:00Z | 25h 38m |
| red | 2026-06-03T01:38:00Z | 2026-06-03T01:52:08Z | 14m 8s |
| green | 2026-06-03T01:52:08Z | 2026-06-03T01:56:07Z | 3m 59s |
| spec-check | 2026-06-03T01:56:07Z | 2026-06-03T01:57:56Z | 1m 49s |
| verify | 2026-06-03T01:57:56Z | 2026-06-03T02:04:34Z | 6m 38s |
| review | 2026-06-03T02:04:34Z | 2026-06-03T02:13:40Z | 9m 6s |
| green | 2026-06-03T02:13:40Z | 2026-06-03T02:16:15Z | 2m 35s |
| spec-check | 2026-06-03T02:16:15Z | 2026-06-03T02:17:05Z | 50s |
| verify | 2026-06-03T02:17:05Z | 2026-06-03T02:18:25Z | 1m 20s |
| review | 2026-06-03T02:18:25Z | 2026-06-03T02:24:04Z | 5m 39s |
| spec-reconcile | 2026-06-03T02:24:04Z | 2026-06-03T02:25:28Z | 1m 24s |
| finish | 2026-06-03T02:25:28Z | - | - |

## Delivery Findings

### TEA (test design)
- **Gap** (non-blocking): `tests/server/dispatch/test_pregen.py` is entirely skip-listed in `tests/conftest.py` (`_CAVERNS_SUNDEN_DEPRECATED_TESTS`, line 217) because of ONE deprecated `caverns_sunden` e2e — sweeping in ~16 world-agnostic `seed_manual` unit tests (the same over-broad file-level skip the conftest's own NOTE rescued `test_pov_swap` from). Worse, those unit tests' `_stub_pack` is stale: it exposes `.cultures` but `seed_manual` now calls `pack.effective_cultures(world)`, so they would ERROR if un-skipped. Net: AC5's "existing pregen tests stay green" is unverifiable as literally written — they are skipped-and-stale, not green. Affects `tests/conftest.py` (remove `test_pregen.py` from the skip set) + `tests/server/dispatch/test_pregen.py` (re-point the `caverns_sunden` e2e to a live world; update `_stub_pack` to implement `effective_cultures`). Recommend as Dev green-phase cleanup or a fast follow-up. *Found by TEA during test design.*

### Dev (implementation)
- No new upstream findings during implementation. The fix stayed within the seam the Architect identified (`pregen.py`); no adjacent gaps surfaced. The `test_pregen.py` skip-list + stale-stub debt (TEA's Gap above) is acknowledged and deliberately deferred — see the Dev deviation below. *Found by Dev during implementation.*

### TEA (test verification)
- **Gap** (non-blocking, NOT a 72-11 regression): the full server suite has one pre-existing failure — `tests/handlers/test_aside_channel_wiring.py::test_aside_is_out_of_band_in_mp` — `AttributeError: '_StubSession' object has no attribute '_retrieve_entities_for_turn'`. The test's `_StubSession` is stale vs the universal-retrieval entity path (epic 75/76); production `_build_turn_context`/session handling now calls `_retrieve_entities_for_turn` which the stub never gained. Fails in isolation (not flaky), not in this branch's diff, and PR #588's commit message already flagged it as a known "unrelated failure." Affects `tests/handlers/test_aside_channel_wiring.py` (add `_retrieve_entities_for_turn` to `_StubSession`). Recommend a 75/76 follow-up — out of scope for the pregen cap fix. *Found by TEA during test verification.*

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Tests added to `test_pregen_seed_world_cultures.py`, not `test_pregen.py`**
  - Spec source: context-story-72-11.md, AC-4 ("extends tests/server/dispatch/test_pregen.py")
  - Spec text: "a >=5-culture fixture/world drives the real seed_manual ... extends tests/server/dispatch/test_pregen.py"
  - Implementation: the 5 new tests live in `tests/server/dispatch/test_pregen_seed_world_cultures.py` instead
  - Rationale: `test_pregen.py` is blanket-skipped by `tests/conftest.py` (caverns_sunden deprecation), so any test added there is silently SKIPPED — a vacuous, false-confidence test. The sibling file is the live, non-skipped home for the *same* subsystem (world-culture seeding), already carrying the correct `GenrePack.model_construct`/`effective_cultures` stub and the OTEL `InMemorySpanExporter` span harness. Extending it fulfils AC4's intent (drive the real `seed_manual`, assert the span) while the tests actually run.
  - Severity: minor
  - Forward impact: none — same subsystem, same seam; AC4's behavioral coverage is delivered and executes.
- **AC1 verified with a coyote_star-SHAPED stub, not the real coyote_star pack**
  - Spec source: context-story-72-11.md, AC-1
  - Spec text: "Verified with a >=5-culture world (coyote_star -> 5 cultures incl voidborn -> 15 NPCs)"
  - Implementation: a `GenrePack.model_construct` stub declaring 5 world cultures (`broken_drift, free_miners, hegemonic, tsveri, voidborn`, voidborn last so the `[:4]` cap drops it); `_generate_npc` spied for hermeticity
  - Rationale: per Story 71-31, coyote_star's LIVE culture resolution is mid-migration — its `cultures/` files are visual-only and `effective_cultures(coyote_star)` currently falls back to the GENRE set (source=GENRE). Coupling a cap unit-test to that shifting content would let it pass/fail for reasons unrelated to the cap. The stub pins the cap mechanism deterministically; the real coyote_star culture inventory is governed by `tests/genre/test_71_31_space_opera_culture_doctrine.py`.
  - Severity: minor
  - Forward impact: once 71-31 finalises coyote_star's world-tier namegen cultures, a real-content coyote_star e2e could be added as belt-and-suspenders (non-blocking).

### Dev (implementation)
- **AC5's literal "existing pregen tests stay green" scoped to the new running coverage; `test_pregen.py` rescue deferred**
  - Spec source: context-story-72-11.md, AC-5
  - Spec text: "existing pregen tests stay green — 2-culture seed (6 NPCs), no-culture fallback (DEFAULT_NPC_FALLBACK_COUNT=9), pack-load-failure fallback, dedup-keeps-unique-names, and the caverns_and_claudes e2e"
  - Implementation: the cap fix touches only `pregen.py`; no-regression is verified by the 164 passing neighbouring tests + the new `test_seed_manual_two_cultures_under_cap_unaffected` guard. The named `test_pregen.py` tests AC5 references remain blanket-skipped (and their `_stub_pack` is stale vs `effective_cultures`) — I did NOT un-skip/rescue them this story.
  - Rationale: per minimalist discipline, no failing test demanded the rescue, and it is a *separate* debt (the caverns_sunden→genre_workshopping deprecation, sidequest-content PR #228), not the cap defect. Un-skipping would require re-pointing a deprecated-world e2e and fixing a stale stub — real scope and real regression risk unrelated to MAX_CULTURES. TEA's Delivery Finding already files it as the recommended follow-up.
  - Severity: minor
  - Forward impact: AC5's intent (no regression from the cap fix) is met; the literal "those four named tests are green" awaits the follow-up rescue. Non-blocking.

### Architect (reconcile)

**Existing deviations reviewed:** the two TEA (test design) entries — test file location vs AC4's literal `test_pregen.py` (justified: that file is blanket-skipped), and the coyote_star-shaped stub vs live pack (justified: 71-31 content migration) — and the one Dev (implementation) entry (AC5 literal rescue deferred) are all accurate, fully-fielded, and stand. No corrections needed.

**Missed deviation added:**

- **Span seeded-count kept as `culture_count`, not renamed `seeded_culture_count`**
  - Spec source: context-story-72-11.md, Design Direction (Architect)
  - Spec text: "Add effective_culture_count + seeded_culture_count to pregen.seed_manual span"
  - Implementation: the fix added the new `effective_culture_count` attribute and left the pre-existing `culture_count` (= `len(cultures)`) as the seeded count; no attribute literally named `seeded_culture_count` was introduced.
  - Rationale: `culture_count` was *already* the seeded-count attribute on the `pregen.seed_manual` span — asserted by the pre-existing `test_seed_manual_emits_otel_with_world_culture_source` (`culture_count == 1`) and read by GM-panel consumers. Renaming it would break the existing span contract for zero benefit. AC3's binding text ("exposes BOTH effective_culture_count AND the seeded culture count") is fully satisfied by `{effective_culture_count, culture_count}`; only my informal Design-Direction note used the `seeded_culture_count` name. The implementation's choice is superior — the design note is superseded (resolution A, decided at spec-check).
  - Severity: trivial
  - Forward impact: none — the live OTEL contract is `{effective_culture_count, culture_count}`; any consumer keys on those attribute names.

**AC deferral verification:** AC5 is the only partially-deferred AC (DONE in intent / DEFERRED in literal, per the Dev AC-accountability table). The deferral is justified and unchanged by review — the named `test_pregen.py` regression tests are pre-existing skip-listed-and-stale debt (caverns_sunden→genre_workshopping deprecation, content PR #228), tracked by TEA's Delivery Finding for a dedicated follow-up. No AC was inadvertently addressed or invalidated during review. The reviewer-accepted "RED today" test-docstring phrasing is cosmetic (not a spec deviation) — an optional Dev tidy, not gating.

**Manifest complete.** Implementation matches the design and all five ACs (AC5 in intent; literal `test_pregen.py` rescue deferred with a filed follow-up). Proceed to SM finish.

## TEA Assessment

**Tests Required:** Yes
**Reason:** behavioral bug fix with a load-bearing OTEL contract — AC-driven failing tests required.

**Test File:** `sidequest-server/tests/server/dispatch/test_pregen_seed_world_cultures.py` (extended — live, non-skipped home; see deviation re: AC4's literal `test_pregen.py`)

**Tests Written:** 5 new (4 RED + 1 green regression guard) covering all 5 ACs.

| Test | AC | RED reason (verified) |
|------|----|------------------------|
| `test_seed_manual_seeds_all_five_world_cultures_uncapped` | AC1/AC4 | `assert 12 == 5*3` — `[:4]` drops voidborn |
| `test_seed_manual_does_not_cap_at_five_either` | AC2 (anti-cheat) | `assert 12 == 6*3` — kills "bump MAX_CULTURES to 5" non-fix |
| `test_seed_manual_span_reports_effective_and_seeded_culture_counts` | AC3 | `assert None == 5` — span has no `effective_culture_count` |
| `test_max_cultures_constant_is_removed` | AC2 (dead-code) | constant still defined (reflection tripwire, not source grep) |
| `test_seed_manual_two_cultures_under_cap_unaffected` | AC5 | green (regression guard, stays green) |

**Status:** RED — 4 failing for the cap/span/constant, 3 passing (2 pre-existing world-culture tests + the AC5 guard). Verified via direct `pytest` run (`--tb=line`): failures are `12==15`, `12==18`, `None==5`, and the constant tripwire — all correct-reason.

### Rule Coverage

| Rule (python lang-review) | Test(s) | Status |
|---------------------------|---------|--------|
| #6 Test quality (no vacuous asserts) | self-check: all 5 assert concrete values (counts, set membership, span attrs); no `assert True`/`let _ =` | pass |
| No Silent Fallbacks (SOUL/CLAUDE.md) | AC1 all-seed + AC3 span-truth tests enforce loud, complete behavior over the silent `[:4]` drop | failing (RED) |
| No Source-Text Wiring Tests (CLAUDE.md) | AC2 dead-code test uses `not hasattr(pregen, "MAX_CULTURES")` (runtime reflection), AC3 uses real span emission via InMemorySpanExporter — no `read_text()`/regex | pass |

**Rules checked:** 3 of 3 applicable (most lang-review rules target Dev's green-phase source, not tests).
**Self-check:** 0 vacuous tests found.

**Handoff:** To Dev (White Rabbit) for GREEN — remove the `[:MAX_CULTURES]` slice + the constant, seed all `effective_cultures`, and add `effective_culture_count` (pre-seed) to the `pregen.seed_manual` span alongside the seeded `culture_count`. Watch the AC2 anti-cheat test: a fix that bumps the cap to 5 will still fail the 6-culture test.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/server/dispatch/pregen.py` — (1) deleted the `MAX_CULTURES = 4` constant + docstring; (2) replaced `cultures = [c.name for c in effective[:MAX_CULTURES]]` with `cultures = [c.name for c in effective]` (seed ALL world cultures); (3) added `effective_culture_count` (= `len(effective)`, pre-seed world truth) to the `pregen.seed_manual` span alongside the seeded `culture_count`.

**Approach:** minimal — exactly the Architect's seam, nothing more. The world author's declared culture list is now the bound; no cap, no sampling, no bump-to-5. The span now carries both the world's true count and the seeded count, so a future divergence is visible on the GM panel instead of silent.

**Tests:** 7/7 passing in the target file (5 new + 2 pre-existing). Neighbouring suites: **164 passed, 17 skipped** (the 17 are the pre-existing `test_pregen.py` blanket-skip). `ruff` clean, `pyright` 0 errors. No other `MAX_CULTURES` consumers exist.

### AC Accountability

| AC | Status | Evidence |
|----|--------|----------|
| AC1 — scale to all cultures | DONE | `test_seed_manual_seeds_all_five_world_cultures_uncapped` green (15 NPCs, voidborn present) |
| AC2 — no silent drop + dead-code removal | DONE | constant deleted (`test_max_cultures_constant_is_removed` green); `does_not_cap_at_five_either` green (6 cultures) |
| AC3 — OTEL span exposes effective + seeded | DONE | `test_seed_manual_span_reports_effective_and_seeded_culture_counts` green (both = 5) |
| AC4 — behavioral wiring test (real seed_manual + span) | DONE | covered by AC1/AC3 tests driving real `seed_manual`; see TEA deviation re: file location |
| AC5 — no regression | DONE (intent) / DEFERRED (literal) | 164 neighbours green + under-cap guard green; the four named `test_pregen.py` tests remain blanket-skipped — rescue deferred (see Dev deviation + TEA finding) |

**Branch:** `feat/72-11-pregen-scale-cultures` (commits `b9d4d283` tests, `bb53afb5` fix — not pushed; PR is SM's finish-phase job)

**Handoff:** To next phase (verify / spec-check / review).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (2 minor/trivial deviations, both pre-logged, both sound)
**Mismatches Found:** 2

I authored this seam, so the check is exacting. The diff is *exactly* the design: `MAX_CULTURES` constant deleted, the `effective[:MAX_CULTURES]` slice replaced with `effective` (seed all), and `effective_culture_count` added to the `pregen.seed_manual` span. AC1/AC2/AC4 are aligned with no mismatch; AC3 and AC5 carry the two deviations below.

- **Span seeded-count attribute kept as `culture_count`, not renamed `seeded_culture_count`** (Different naming — cosmetic, trivial)
  - Spec: my design-direction note (context-story-72-11.md) said "Add effective_culture_count + seeded_culture_count to the span."
  - Code: added `effective_culture_count` and left the **existing** `culture_count` (= `len(cultures)`) as the seeded count.
  - Recommendation: **A — Update spec.** The code is *better*: `culture_count` was already the seeded-count attribute and is read by an existing assertion (`test_seed_manual_emits_otel_with_world_culture_source` → `culture_count==1`) and by GM-panel consumers. Renaming it would break the existing span contract for zero benefit. AC3's literal text ("exposes BOTH effective_culture_count AND the seeded culture count") is fully satisfied by `{effective_culture_count, culture_count}`. My design note's `seeded_culture_count` name is superseded. Trivial — noted in passing, no code change.

- **AC5's literal "existing pregen tests stay green" deferred (the named tests live in the blanket-skipped, stale `test_pregen.py`)** (Ambiguous spec — minor)
  - Spec: AC5 names four `test_pregen.py` tests + the caverns_and_claudes e2e that should "stay green."
  - Code/tests: no-regression is verified by 164 passing neighbours + the new under-cap guard; the named `test_pregen.py` tests remain blanket-skipped and their `_stub_pack` is stale (pre-existing, unrelated debt).
  - Recommendation: **A + D — Update spec & defer the work.** AC5 was written by me uninformed that `test_pregen.py` was already skipped-and-stale (the caverns_sunden→genre_workshopping deprecation, sidequest-content PR #228) — those tests were never green to begin with, so the cap fix cannot have regressed them. AC5's *intent* (no regression from this change) is met. The rescue (un-skip + re-point the deprecated e2e + fix the stale stub) is a distinct concern correctly deferred per TEA's Delivery Finding; it should be filed as a follow-up. Non-blocking. **A follow-up story is recommended** (un-skip `test_pregen.py`, fix `_stub_pack` to use `effective_cultures`, re-point the caverns_sunden e2e) — honors "No skipping tests for live subsystems" without bloating this 3-pt fix.

**Decision:** Proceed to verify. No hand-back to Dev — implementation matches design and AC intent; both deviations are cosmetic/spec-correcting, not behavioral defects.

### Spec-Check Cycle 1 (post-rework)

Re-checked after the reviewer-driven rework (commit `4f683156`). The only *source* change is the `seed_manual` docstring (the lying "up to 4 cultures, max 12 NPCs" → accurate no-cap text) — **zero logic drift**; the cap-removal + span attribute from cycle 0 are byte-identical. The other three changes are test-only (AC3 under-cap assertion, unused-param removal, span cross-check) and tighten coverage without altering the contract. The two cycle-0 deviations (span `culture_count` naming kept; AC5 literal `test_pregen.py` rescue deferred) are unchanged and still sound. **Spec Alignment: Aligned.** Proceed to verify.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (72-11 changes); 1 pre-existing unrelated suite failure documented below.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`pregen.py`, `test_pregen_seed_world_cultures.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | exporter-setup dup (high), spy-helper overlap (medium), `_culture` cross-file dup (high) |
| simplify-quality | clean | — |
| simplify-efficiency | clean | (1 low note: 2-line helper overlap — not a defect) |

**Applied:** 1 high-confidence fix — extracted `_local_span_exporter(monkeypatch)` to dedup the InMemorySpanExporter setup shared by the two span tests (commit `9bb…`; a *local* helper, not the suggested cross-test-file import, which would couple test modules). 7/7 still green, ruff clean.
**Flagged for Review:** 1 medium — `_install_spies`/`_install_capture` consolidation (kept separate: distinct narratives — original-bug vs the fix).
**Noted (not applied):** 1 high-but-out-of-scope — `_culture()` is duplicated across 3 test files; the fix is a new shared `tests/_helpers` module + 3-file edit, a pre-existing systemic concern beyond this 3-pt story.
**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Regression gate (full server suite):** **9739 passed, 361 skipped, 1 failed**. The single failure — `tests/handlers/test_aside_channel_wiring.py::test_aside_is_out_of_band_in_mp` — is **pre-existing and unrelated** to 72-11: not in this branch's diff, fails in isolation (not flaky/ordering), and its cause is a stale `_StubSession` missing `_retrieve_entities_for_turn` (from the entity-retrieval epic, 75/76). PR #588's own commit message already flags it as a known "unrelated failure." Per the verify-workflow no revert was warranted (the simplify change is unrelated). The 72-11 blast radius (dispatch + telemetry + genre culture suites) is fully green.

**Quality Checks:** 72-11 changes green; ruff + pyright clean on changed files.
**Handoff:** To Reviewer (Queen of Hearts) for code review.

## Reviewer Assessment

**Verdict:** APPROVED (review cycle 1, post-rework)
**Review verdict:** approved
**Cycle:** 1

Cycle 0 was REJECTED for a lying `seed_manual` docstring (it claimed "up to 4 cultures, max 12 NPCs" *after* the cap was removed) plus AC3 coverage gaps. The rework (commit `4f683156`) addressed all four required changes, and the re-convened four-reviewer panel confirms **every cycle-0 finding is resolved with zero new violations**: rule-checker 16 rules / 51 instances / **0 violations**; test-analyzer clean; preflight GREEN (149 passed, 0 failed); comment-analyzer confirms the docstring is now accurate. The fix's substance was sound throughout (No-Silent-Fallbacks, OTEL wiring, reflection tripwire all compliant). **APPROVED.**

### Findings by Specialist (cycle 1)

- **[DOC]** (comment-analyzer) — docstring fix **CONFIRMED accurate** ("all of the world's declared cultures (no cap)", matches the code). One **non-blocking** nit: four *test* docstrings carry "RED today:" phrasing that reads stale post-fix (the tests are GREEN now). Accepted, not blocking — it documents the failing state each test was authored to catch (TDD intent archaeology), is not a behavioral-contract lie, and rule-checker found zero comment violations. Optional trivial tidy for the Dev; not worth a second rework cycle. (Span-comment framing dismissed again — it accurately states the detection contract.)
- **[RULE]** (rule-checker) — **CLEAN**, 16 rules / 51 instances / **0 violations**. Both cycle-0 violations resolved: rule-13 (docstring now accurate) and rule-6 (`_local_span_exporter` return now bound + asserted at both call sites). A1 No-Silent-Fallbacks / A2 No-Source-Text-Wiring / A3 OTEL-Observability re-confirmed compliant.
- **[TEST]** (test-analyzer) — **CLEAN.** All three cycle-0 items fixed: `effective_culture_count==1` asserted in the 1-culture test; unused `monkeypatch` removed; AC3 span test binds `captured` and cross-checks `len==15`. No new test-quality issues; all five AC tests carry substantive assertions.
- **[EDGE]**, **[SILENT]**, **[TYPE]**, **[SEC]**, **[SIMPLE]** — disabled via `workflow.reviewer_subagents`; no findings (dismissed by configuration). [SIMPLE] coverage was exercised by the TEA verify simplify fan-out.

## Subagent Results

**Cycle: 1** (re-review after rework commit `4f683156`)

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | pass | 0 | confirm — 149 passed/17 skipped/0 failed in blast radius; all 7 story tests green; aside failure pre-existing + unchanged |
| 2 | reviewer-test-analyzer | Yes | clean | 0 | confirm all 3 cycle-0 test findings fixed; no new issues |
| 3 | reviewer-comment-analyzer | Yes | findings | 1 | confirm docstring fix accurate; "RED today" test-docstring phrasing accepted non-blocking; span-comment dismissed |
| 4 | reviewer-rule-checker | Yes | clean | 0 | confirm both cycle-0 violations resolved (rule-13, rule-6); 16 rules / 51 instances / 0 violations; A1/A2/A3 compliant |
| 5 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings (TEA verify already ran the simplify fan-out) |

**All received: Yes** — all 4 enabled subagents returned; 5 subagents disabled via `workflow.reviewer_subagents` settings.

**Total findings:** 0 confirmed-blocking, 1 accepted non-blocking ("RED today" test-docstring tidy), 2 dismissed (span-comment framing; reflection-redundancy). All cycle-0 findings resolved.

### Required Changes (Dev)

1. **[BLOCKING] [DOC] [RULE] Fix the `seed_manual` docstring (`pregen.py:193-194`).** It still reads *"generates 3 NPCs per culture (up to 4 cultures, max 12 NPCs)"* — a direct lie after the cap removal (5 cultures → 15 NPCs). Replace the parenthetical with no-cap language, e.g. "generates 3 NPCs per culture for **all** of the world's declared cultures (no cap — story 72-11)". Flagged by **[DOC]** comment-analyzer AND **[RULE]** rule-checker rule-13 (independent corroboration).
2. **[REQUIRED] [TEST] Assert the new span attribute in the existing 1-culture test.** `test_seed_manual_emits_otel_with_world_culture_source` (test file ~line 100) emits `effective_culture_count=1` but never asserts it. Add `assert attrs.get("effective_culture_count") == 1`. Closes a gap on the load-bearing AC3 (OTEL) contract in the under-cap case. (**[TEST]** test-analyzer, high.)
3. **[REQUIRED, trivial] [TEST] Remove the unused `monkeypatch` param** from `test_max_cultures_constant_is_removed` — the test only calls `hasattr(pregen, "MAX_CULTURES")`. (Keep the test itself — it correctly enforces AC2's "constant deleted"; **[RULE]** rule-checker A2 blessed it as the reflection tripwire pattern.) (**[TEST]** test-analyzer, high.)
4. **[MINOR] [TEST] [RULE] AC3 span test cross-check.** In `test_seed_manual_span_reports_effective_and_seeded_culture_counts`, assign `_install_capture(...)`'s return and add `assert len(captured) == 5 * pregen.NPCS_PER_CULTURE` so the span's `culture_count=5` is tied to 15 actual seed attempts (defends the "counted but not seeded" path). (**[TEST]** test-analyzer + **[RULE]** rule-checker rule-6 discarded-return smell.)

### Optional (Dev discretion / follow-up)
5. A span-asserting variant on the pack-load-failure / empty-effective path (`effective_culture_count == 0`) — confirms the new field initializes to 0 on the fallback branch. Non-blocking.

### Rule Compliance
Per `gates/lang-review/python.md` (rule-checker, exhaustive): rules 1 (silent except), 2 (mutable defaults), 4 (logging), 5 (paths), 7 (resource leaks), 8 (deserialization), 10 (imports), 11 (input validation) — all **compliant**. Rule 3 (type annotations) compliant on the public boundary (the docstring issue is rule-13, not 3). Rule 6 (test quality) — one minor discarded-return smell (F4). Rule 13 (fix-introduced regression) — **the lying docstring** (F1). Project rules: No Silent Fallbacks ✅, No Source-Text Wiring Tests ✅, OTEL Observability ✅.

**Decision:** Return to Dev (White Rabbit) for items 1-4. Re-review on return — expect a fast turnaround; the substance is correct, this is documentation accuracy + AC3 coverage tightening.

## Dev Rework — Review Cycle 1

All four required changes addressed (commit `4f683156`):

1. **[BLOCKING][DOC][RULE] Docstring fixed** — `seed_manual` no longer claims "(up to 4 cultures, max 12 NPCs)"; now reads "generates 3 NPCs per culture for **all** of the world's declared cultures (no cap — story 72-11; a world declaring N cultures seeds N × 3 NPCs)". The lie is gone.
2. **[REQUIRED][TEST] AC3 under-cap coverage** — `test_seed_manual_emits_otel_with_world_culture_source` now asserts `effective_culture_count == 1`, so the new span attribute is pinned in the 1-culture case, not only the ≥5-culture test.
3. **[REQUIRED][TEST] Unused param removed** — `test_max_cultures_constant_is_removed()` no longer takes `monkeypatch`. The reflection tripwire itself is retained (enforces AC2's constant-deleted).
4. **[MINOR][TEST][RULE] AC3 cross-check** — the span test now binds `_install_capture`'s return and asserts `len(captured) == 5 * pregen.NPCS_PER_CULTURE`, tying the span's `culture_count=5` to 15 real seed attempts (closes the "counted but not seeded" path).

**Verification:** 7/7 target tests green (incl. the two new assertions); ruff + pyright clean on both changed files. No source behavior change beyond the docstring — the cap-removal fix from cycle 0 is unchanged.

**Handoff:** Back through the cycle (spec-check → verify → review) for re-review.

## TEA Verify — Cycle 1 (post-rework)

**Status:** GREEN confirmed.

### Simplify Report

**Teammates:** reuse, quality, efficiency — **not re-run this cycle (no new surface).**
**Files Analyzed:** 0 new (same 2 files; the cycle-0 fan-out already analyzed `pregen.py` + `test_pregen_seed_world_cultures.py` and applied the `_local_span_exporter` dedup).

The rework delta (commit `4f683156`) is a docstring rewrite + three test-assertion additions (AC3 `effective_culture_count==1`, unused-param removal, `len(captured)==15` cross-check). None introduce duplication, dead code, or complexity — the reviewer's findings *were* the cleanup, and the cross-check strengthens an existing test. Re-fanning three simplify subagents over a docstring + assertion change would be theater. Self-checked the delta: no vacuous assertions, no extractable duplication, no over-engineering.

**Overall:** simplify: clean (no new findings; cycle-0 fixes stand)

**Regression gate:** target suite 7/7 green; ruff + pyright clean on both changed files (0 errors). The pre-existing unrelated `test_aside_channel_wiring` failure (epic 75/76, documented above) is unchanged and still out of scope.

**Handoff:** To Reviewer (Queen of Hearts) for re-review.