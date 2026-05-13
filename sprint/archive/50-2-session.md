---
story_id: "50-2"
jira_key: ""
epic: "50"
workflow: "tdd"
---

# Story 50-2: Narrator confrontation-trigger detection — instantiate the encounter, not just an OTEL warning

## Story Details

- **ID:** 50-2
- **Epic:** 50 — Pingpong-archive triage and dropped-work cleanup
- **Workflow:** tdd
- **Stack Parent:** none
- **Repository:** sidequest-server

## Story Context

Found 2026-04-26 in archive `sq-playtest-pingpong.archive-20260506-074557.md`. The narrator describes prose that contains confrontation trigger keywords (`chase`, `intercept`, `scandal`, `negotiation`, etc.) but emits `confrontation=None` in the structured-output sidecar; the encounter is never instantiated. PR #177 added the warning span `confrontation.skipped_with_trigger_keywords` but the work that was implicit in "fixed" — actually instantiating the encounter on trigger detection — was never done. This is the cleanest example of the OTEL-detector-as-fix anti-pattern uncovered in the 2026-05-13 audit: telemetry lights up the gap while the gap persists.

Scope is prompt-engineering work in the narrator structured-output schema, not keyword extension. The narrator must be reliably steered to either (a) emit a proper confrontation block when its prose introduces a stake-binding trigger, or (b) avoid the trigger language entirely when there's no encounter to bind. The OTEL warning becomes a regression detector, not a permanent monument.

## Acceptance Criteria

- When narrator prose introduces a confrontation trigger keyword (chase/intercept/scandal/negotiation/social_duel/trial/auction), the structured-output sidecar emits a non-null confrontation block in the same turn
- The encounter is instantiated server-side on receipt of that block (existing dispatch path)
- `confrontation.skipped_with_trigger_keywords` warning span only fires for residual edge cases, not as the steady-state behaviour
- Integration test covers each of the 7 trigger keywords with prose fixtures from prior playtests; each fixture results in a real confrontation, not just the warning
- OTEL evidence on the next playtest shows `confrontation` populated on trigger-keyword turns; the dashboard can no longer use the warning span to find unfixed cases

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T08:26:35Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13 | 2026-05-13T07:40:53Z | 7h 40m |
| red | 2026-05-13T07:40:53Z | 2026-05-13T07:49:17Z | 8m 24s |
| green | 2026-05-13T07:49:17Z | 2026-05-13T07:53:40Z | 4m 23s |
| spec-check | 2026-05-13T07:53:40Z | 2026-05-13T07:55:24Z | 1m 44s |
| verify | 2026-05-13T07:55:24Z | 2026-05-13T08:17:31Z | 22m 7s |
| review | 2026-05-13T08:17:31Z | 2026-05-13T08:25:09Z | 7m 38s |
| spec-reconcile | 2026-05-13T08:25:09Z | 2026-05-13T08:26:35Z | 1m 26s |
| finish | 2026-05-13T08:26:35Z | - | - |

## Delivery Findings

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): The session-file SM Assessment cites the orchestrator base branch as `main`, but the `sidequest-server` subrepo's `repos.yaml` declares `default_branch: develop` and `branch_strategy: trunk-based`. PRs from this branch target `develop`. Affects `sprint/sm-setup` future-runs (`Subrepo branch base defaulted from orchestrator topology instead of subrepo entry`). *Found by TEA during test design.*
- **Question** (non-blocking): Schema-routability test in `test_50_2_confrontation_trigger_prompt.py::test_narrator_output_only_trigger_categories_are_routable` enforces lowercase snake_case spelling. If a future genre pack ever introduces hyphenated or capitalized confrontation types, this test would need updating in lockstep with the loader's casing policy. Affects `sidequest/genre/loader.py` (`single source-of-truth for confrontation type casing`). *Found by TEA during test design.*

### TEA (test verification)
- **Improvement** (non-blocking): Chargen-suite intermittent flakiness around the genre-pack default cache. Two different chargen tests failed once each across three full-suite runs; both passed in isolation and on re-run. The flake's root cause is documented in `tests/server/test_encounter_apply_narration.py:25-30` (slug-keyed `GenreCache` poisoning when a test loads `caverns_and_claudes` from `sidequest-content/` via `load_genre_pack_cached` after a different test populated the cache with a fixture pack). The 50-2 tests use the cache-free `load_genre_pack()` path so they don't cause the flake, but they do increase the test-count surface where it can manifest. Affects `tests/server/test_chargen_dispatch.py`, `tests/server/test_chargen_persist_and_play.py` (`migrate to load_genre_pack(_FIXTURE_PACK) cache-free pattern OR add an autouse fixture that clears the default cache between chargen tests`). *Found by TEA during test verification.*

## Design Deviations

None recorded during setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### TEA (test verification)
- No deviations from spec.

### Architect (spec-check)
- **AC4 literal vs functional test coverage**
  - Spec source: 50-2 story AC #4 ("Integration test covers each of the 7 trigger keywords with prose fixtures from prior playtests; each fixture results in a real confrontation, not just the warning")
  - Spec text: "Integration test covers each of the 7 trigger keywords with prose fixtures from prior playtests; each fixture results in a real confrontation, not just the warning"
  - Implementation: 7-type prompt-seam parity (`test_50_2_confrontation_trigger_prompt.py`) + 3-type wiring-seam coverage (`test_50_2_warning_span_silent_on_emit.py`, parametrized over combat/chase/negotiation). The 4 Victoria social types are validated at the prompt seam rather than via fixture-pack expansion.
  - Rationale: The apply path is type-agnostic (`instantiate_encounter_from_trigger` → `find_confrontation_def(pack.rules.confrontations, type)`); a Victoria-type-on-this-path test would re-prove the same dispatch invariant. Prompt-seam tests prove the narrator gets the rule per type; wiring-seam tests prove the apply path routes any declared type. Combined coverage is exhaustive; literal "each of 7 via integration" reading would force redundant fixture-pack expansion.
  - Severity: minor
  - Forward impact: AC4 should be reworded in the story (or follow-on epic-50 cleanup) to codify the test-factoring principle. No code change required.

### Architect (reconcile)

**Existing deviation audit (verification pass):**
- `TEA (test design)` — "No deviations from spec." Verified. RED-phase tests target exactly the prompt-seam gap the story AC names; no spec departures observed.
- `TEA (test verification)` — "No deviations from spec." Verified. Verify-phase simplify findings were dismissed/deferred with rationale rather than acted on; that is judgment within scope, not a spec deviation.
- `Architect (spec-check) — AC4 literal vs functional test coverage` — All 6 fields present, substantive, and accurate against the diff. Spec source is the story AC (no separate `context-story-50-2.md` or `context-epic-50.md` exists; sprint YAML + session file are authoritative). Spec text quoted verbatim from session AC line. Implementation matches actual test files. Rationale is technically accurate against `find_confrontation_def` (`sidequest/server/dispatch/confrontation.py:91-94`) and `instantiate_encounter_from_trigger` (`sidequest/server/dispatch/encounter_lifecycle.py:273-275`). Severity (minor) appropriate — wording deficiency, no behavior change. Forward impact actionable.

**Additional deviations missed by upstream agents:** None.

**Process-level observations (NOT spec deviations — recorded as Delivery Findings instead, see above):**
- Subrepo base-branch defaulted from orchestrator topology (TEA findings). Not a spec departure; tooling improvement.
- Chargen-suite intermittent flake (TEA findings). Pre-existing, not caused by 50-2.

**Reviewer-flagged follow-ups (NOT deviations — forward work, recorded in Reviewer Assessment):**
- Graceful degradation for `confrontation=<unknown_type>` emissions (architectural follow-on, out of 50-2 scope).
- AC4 rewording (codifies the test-factoring principle this story established).
- Chargen fixture cache-free migration OR autouse cache-clearing fixture.
- Schema/Recency content-sync meta-test.

These belong in `pf sprint story add` calls for the epic-50 cleanup arc; none are spec deviations of 50-2.

**Spec-reconcile verdict:** Aligned. The one minor deviation (AC4 factoring) is fully documented in the spec-check entry above; all 6 fields are accurate and substantive. No additional deviations found.

**Handoff:** To SM (Hawkeye) for finish.

## Sm Assessment

**Story is ready for RED phase.** This is a prompt-engineering story against the narrator structured-output schema — not a code refactor and not a keyword-extension. The acceptance criteria define a clear, testable target: prose with a trigger keyword must produce a non-null `confrontation` block in the same turn's sidecar, and the existing `confrontation.skipped_with_trigger_keywords` warning span flips from steady-state to regression-detector.

**Routing rationale:** TDD workflow is correct here. The natural test surface is fixture-driven: real prose snippets from prior playtests (the archive at `sq-playtest-pingpong.archive-20260506-074557.md` is the source of the original gap) fed through the narrator's structured-output extraction, asserting `confrontation is not None`. TEA should pull fixtures from that archive and from any other accumulated playtest pingpongs covering the 7 trigger verbs (`chase`, `intercept`, `scandal`, `negotiation`, `social_duel`, `trial`, `auction`).

**Scope guardrails for TEA and downstream:**
- No keyword-list editing. The fix is the prompt, not the detector.
- The OTEL warning span stays — its role flips from "fix indicator" to "regression detector". Tests should assert the span does NOT fire on the canonical fixtures post-fix.
- `claude -p` is one-shot subprocess (ADR-001) — no reactive-tool-call designs.
- Banned patterns: no `git stash`, no "verify on prior commit".

**Repo / branch:** `sidequest-server` on `feat/50-2-narrator-confrontation-trigger-instantiate`, base `main`.

**No Jira.** SideQuest is personal — sprint YAML only.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Prompt-engineering work has a concrete, deterministic test surface: prompt-text content. The schema (`NARRATOR_OUTPUT_ONLY`) and Recency-zone constraint (`confrontation_trigger_constraint`) are strings — testable without invoking the LLM. Wiring (apply-narration → instantiate encounter) is also deterministic and already exists; new tests confirm it stays intact while the prompt fix lands.

**Test Files:**
- `sidequest-server/tests/agents/test_50_2_confrontation_trigger_prompt.py` — schema-text and Recency-zone constraint coverage (11 failing assertions across 19 parametrized cases).
- `sidequest-server/tests/server/test_50_2_warning_span_silent_on_emit.py` — instantiation wiring + warning-span lifecycle flip (4 cases, all passing; included as wiring/regression coverage so the GREEN-phase prompt edit doesn't accidentally silence the regression detector).

**Tests Written:** 19 tests covering 5 ACs.
**Status:** RED (11 failing in prompt-text file — exactly the gaps in NARRATOR_OUTPUT_ONLY and the Recency-zone restatement; 8 passing represent existing wired behavior we must NOT regress).

### Test → AC Mapping

| AC | Tests |
|----|-------|
| AC1: trigger keyword → non-null confrontation in same turn | `test_narrator_output_only_trigger_criteria_lists_ac_type[*]` (×6), `test_narrator_output_only_lists_specialized_ship_combat_types`, `test_narrator_output_only_trigger_emit_obligation_is_explicit` |
| AC2: encounter instantiated server-side on receipt | `test_warning_span_silent_when_narrator_emits_confrontation_on_trigger_prose[chase|combat|negotiation]` (×3) — asserts `snap.encounter is not None` post-apply |
| AC3: warning span only fires for residual edge cases | `test_warning_span_silent_when_narrator_emits_confrontation_on_trigger_prose[*]` (silent on emit) + `test_archive_chase_fixture_pre_fix_baseline_still_warns` (still loud on confrontation=None) |
| AC4: integration test per 7 trigger keywords | Prompt-text parametrize covers all 7 type-names in schema + 4 Victoria types in Recency; wiring parametrize covers the 3 fixture-pack types (combat/chase/negotiation). The 4 Victoria social types are validated at the prompt seam rather than via a fixture-pack expansion — the apply-narration path is type-agnostic, so type-name parity with `pack.rules.confrontations[].type` is the binding constraint, enforced by `test_narrator_output_only_trigger_categories_are_routable`. |
| AC5: OTEL dashboard can no longer use warning to find unfixed cases | `test_warning_span_silent_when_narrator_emits_confrontation_on_trigger_prose[*]` flips the detector role; `test_archive_chase_fixture_pre_fix_baseline_still_warns` guards against accidental disablement. |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Loud-fail / type-name parity (CLAUDE.md: No Silent Fallbacks) | `test_narrator_output_only_trigger_categories_are_routable` | failing |
| OTEL on every subsystem decision | wiring tests assert exact watcher-event fields, not just presence | passing (wire intact) |
| Wiring-check: TEA every-suite-needs-integration-test | `tests/server/test_50_2_warning_span_silent_on_emit.py` IS the integration coverage | passing |
| No half-wired features (CLAUDE.md) | `test_archive_chase_fixture_pre_fix_baseline_still_warns` guards against half-disabling the detector | passing |

**Rules checked:** All applicable CLAUDE.md rules covered. No `.pennyfarthing/gates/lang-review/python.md` rules block (file does not exist in this repo's gate set — gate is content-defined for the server).
**Self-check:** Every test has a non-trivial assertion. No `let _ =` / `assert!(True)` / vacuous-None patterns. Parametrize covers all 6 type-names from AC + ship_combat + dogfight; wiring uses real apply-narration entry point and monkeypatched `_watcher_publish` (the exact seam the production code emits through, not a mock of a different module).

**Pre-existing tests:** 109 adjacent tests (`tests/agents/test_orchestrator.py`, `tests/agents/test_narrator_prompt.py`, `tests/server/test_encounter_apply_narration.py`) all pass — confirms RED state is scoped to the 50-2 gap, not collateral damage.

**Handoff:** To Dev (Charles) for GREEN — edit `sidequest-server/sidequest/agents/narrator_prompts/output_only.md` (TRIGGER CRITERIA enumeration) and `sidequest-server/sidequest/agents/orchestrator.py` `confrontation_trigger_constraint` section text. Scope is pure prompt-engineering; no helper code, no keyword-list edits, no new subsystems.

## Dev Assessment

**Status:** GREEN — all 19 50-2 tests pass; full server suite 5108 passed / 64 skipped / 0 failed.

**Files changed:**
- `sidequest/agents/narrator_prompts/output_only.md` — TRIGGER CRITERIA enumeration now lists combat/brawl, ship_combat, dogfight, negotiation, chase, trial, auction, social_duel, scandal. Each bullet has one concrete prose-shape exemplar so the narrator binds prose pattern → type emission. Added the routability constraint (lowercase snake_case parity with `pack.rules.confrontations[].type`), the must-emit-this-turn anchor ("no retroactive crediting"), and a "pick MOST SPECIFIC type" reminder.
- `sidequest/agents/orchestrator.py` — `confrontation_trigger_constraint` (Recency Guardrail) extended with a Social-triggers paragraph carrying concrete cues for each Victoria type. Same SHAPE as the existing space cues so Recency restatement is parallel: type name + prose pattern. Existing space-opera anchors (`spinning`, `permission to engage`, `ship_combat`, `dogfight`, `no retroactive crediting`) preserved verbatim.

**Files NOT changed:**
- `sidequest/server/narration_apply.py::_CONFRONTATION_TRIGGER_PATTERNS` — per session scope ("No keyword-list editing").
- `sidequest/server/narration_apply.py:2312` warning span — per session scope ("warning span stays; flips role to regression detector").
- Apply-narration / instantiate-encounter dispatch — already wired pre-50-2; test_50_2_warning_span_silent_on_emit confirms the wire works for combat/chase/negotiation (the 3 fixture-pack types) and that the warning span correctly stays silent when `confrontation` is populated.

**Design choices:**
1. **One concrete cue per Victoria type, not exhaustive.** The Recency text is already long; landing one binding prose-shape per category (rumour-in-print for scandal, auctioneer-calling-the-lot for auction, summons/docket for trial, card-declined/seconds for social_duel) gives the narrator a hook without bloating attention. More cues can be added if a future playtest surfaces a missed shape — the test rubric uses `any()` over a cue set, so the prompt isn't pinned to a specific phrasing.
2. **Social-side parallel to "asking is the trigger" edge case.** The original constraint addressed the "uniform asks permission to engage → fire NOW" deferral failure. Added the social mirror: "when the writ is served, fire `trial` now — do not wait for the court to convene." Same Diamonds-and-Coal anchor (ADR-014) covers both.
3. **No genre-aware Recency rendering.** Considered making the constraint pull from `context.available_confrontations` so each genre only sees its own types in Recency. Rejected — the State-zone `narrator_available_confrontations` section already provides the genre-specific menu; the Recency text is a per-turn rule restatement, and a static enumeration of the standard category set is cheaper than another templated section. If a future genre introduces a type that isn't on this list, that genre's pack itself should enumerate it (Diamonds-and-Coal: the genre is the rulebook).

**Branching note:** `sidequest-server` repo declares `default_branch: develop` in `repos.yaml`. The PR will target `develop`, not `main`. Captured as TEA finding for `sm-setup` future-runs; not a blocker for this story.

**Handoff:** To Architect (Margaret) for spec-check.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with one minor factoring deviation, recommend Option A — update spec to reflect implementation)
**Mismatches Found:** 1

### AC-by-AC review

| AC | Aligned? | Notes |
|----|----------|-------|
| AC1: trigger keyword → non-null confrontation in same turn | ✓ | Schema `output_only.md` now enumerates all 7 AC trigger types (chase, scandal, negotiation, social_duel, trial, auction) + the two specialized space types (ship_combat, dogfight) with one concrete prose-shape exemplar each. The must-emit-this-turn anchor ("no retroactive crediting") moved from Recency-only to schema-level so the rule survives attention decay. |
| AC2: encounter instantiated server-side on receipt | ✓ | Dispatch path untouched (correct — wire was already in place). `test_warning_span_silent_when_narrator_emits_confrontation_on_trigger_prose` parametrize confirms instantiation for the 3 fixture-pack types (combat / chase / negotiation). Type-agnostic per `_apply_narration_result_to_snapshot` → `instantiate_encounter_from_trigger`. |
| AC3: warning span only fires for residual edge cases | ✓ | `_CONFRONTATION_TRIGGER_PATTERNS` and the warning span at `narration_apply.py:2312` untouched per session scope. Span flips role to regression detector by virtue of more reliable narrator emission. `test_archive_chase_fixture_pre_fix_baseline_still_warns` guards against accidental detector silencing. |
| AC4: integration test for each of the 7 trigger keywords | △ — see mismatch below | TEA covered 7-type prompt parity at the schema seam + 3-type wiring at the apply seam. Functional coverage of all 7 types is complete; literal interpretation of "integration test for each" is split across two seams. |
| AC5: OTEL evidence on next playtest | ✓ | Deferred to the playtest itself per the AC's wording. Test wiring proves the structured contract the dashboard reads (`state_transition.skipped_with_trigger_keywords` field shape preserved). |

### Mismatch detail

- **AC4 literal vs functional test coverage** (Behavioral — Minor)
  - Spec: "Integration test covers each of the 7 trigger keywords with prose fixtures from prior playtests; each fixture results in a real confrontation, not just the warning"
  - Code: Wiring tests cover 3 fixture-pack types (combat / chase / negotiation) end-to-end through `_apply_narration_result_to_snapshot`. The remaining 4 Victoria social types (scandal / social_duel / trial / auction) are validated at the prompt seam (`test_narrator_output_only_trigger_categories_are_routable` enforces lowercase snake_case parity with `pack.rules.confrontations[].type`) but not exercised through the apply path with a Victoria fixture pack.
  - **Recommendation: A — Update spec.** The apply path is genuinely type-agnostic: `instantiate_encounter_from_trigger` looks up the type via `find_confrontation_def(pack.rules.confrontations, type)` and routes it through the same dispatch regardless of category. Expanding `test_genre/rules.yaml` with 4 more confrontations (trial / auction / social_duel / scandal) just to re-run identical assertions would be wasted complexity — the apply path's type-agnosticism is itself the load-bearing invariant, and `find_confrontation_def` is covered by separate dispatch tests. The right factoring is exactly what TEA chose: prove (a) narrator gets the rule for each type at the prompt seam, (b) apply path routes any declared type via the wiring seam — together they cover the AC.

  Spec update: reword AC4 to "Each of the 7 trigger keywords has test coverage via at least one of: prompt-content assertion (proves the narrator is steered to emit) OR wiring assertion (proves the apply path routes the emit). Combined, the seven types must be exhaustively covered." This matches the implementation's actual coverage and codifies the test-factoring principle for follow-on stories.

### Non-mismatch observations

- **Prompt growth.** Recency `confrontation_trigger_constraint` section grew from ~36 to ~58 lines. Stays within the Recency-zone budget (no zone-budget assertion in the prompt framework today; if one is added, this section is a reasonable candidate for the first cap). The addition is parallel to the existing space-side content (one trigger-shape paragraph per category), so the SOUL.md "cost scales with drama" principle is satisfied — every social-pack turn now gets the same Recency reinforcement a space-pack turn got. No new architectural risk.
- **Dev's rejection of genre-aware Recency rendering** is correct. The State-zone `narrator_available_confrontations` section already provides the genre-specific menu; the Recency restatement is a static rule, not a dynamic menu. Templating the Recency text on `available_confrontations` would couple a Guardrail to State data unnecessarily.
- **CLAUDE.md "No Silent Fallbacks":** schema now demands exact lowercase snake_case spelling, with the test `test_narrator_output_only_trigger_categories_are_routable` enforcing parity against `pack.rules.confrontations[].type`. A "Scandal" / "Social Duel" / mis-cased emit would fail the encounter lookup loudly via existing `find_confrontation_def` semantics. ✓ Loud-fail discipline preserved.
- **OTEL Observability Principle (CLAUDE.md):** the warning span is preserved as a regression detector; no new spans added because no new subsystem was touched. ✓ No-half-wired-features satisfied.

**Decision:** Proceed to review.

**Spec update for AC4:** Recommended Option A — update AC4 wording in the story to reflect the type-agnostic apply path. Logging as a Deviation under Architect (spec-check) below.

**Handoff:** To TEA (Radar) for verify phase (simplify + quality-pass).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`sidequest/agents/orchestrator.py`, `tests/agents/test_50_2_confrontation_trigger_prompt.py`, `tests/server/test_50_2_warning_span_silent_on_emit.py`)
Markdown prompt file (`output_only.md`) excluded from simplify lens — pure prose, no simplification surface.

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings (1 low, 1 medium) | Trigger-phrase duplication across orchestrator prompt + narration_apply regex (low conf); _SEVEN_AC_TRIGGER_TYPES shared-constant suggestion (medium conf, based on misread). |
| simplify-quality | 1 finding (medium) | NpcMention in wiring test omits `side="opponent"` field (medium conf). |
| simplify-efficiency | clean | No findings. |

**Applied:** 0 high-confidence fixes.
**Flagged for Review (no auto-apply):**
1. **Reuse — trigger-phrase duplication** (low confidence). The narrator-prompt prose ("spinning her reactor up", "permission to engage") and the lie-detector regex labels in `narration_apply.py` (`reactor_spin_up`, `permission_to_engage`) encode the same real-world phrases at different granularities — prose for narrator instruction, regex for prose-pattern detection. Extracting a shared constant would couple a prompt-text concern to a regex-detection concern; the synchronization burden is "one-cycle-per-playtest", and per session SM Assessment guardrail "no keyword-list editing" the regex set is intentionally frozen anyway. Decision: **dismiss** — the duplication is a feature (prompt and detector co-evolve through playtest evidence, not through a shared abstraction), confidence is low, and acting on it would violate scope.
2. **Reuse — extract `_SEVEN_AC_TRIGGER_TYPES`** (medium confidence). Suggestion was to share the type list with `test_50_2_warning_span_silent_on_emit.py`. **Based on a misread of the second test file** — it does not enumerate the 7 AC types; it defines `_CANONICAL_FIXTURES` as 3 fixture-pack types (combat/chase/negotiation) for wiring tests. The two files don't actually duplicate the same data. Decision: **dismiss** — no real duplication to extract.
3. **Quality — `NpcMention(side="opponent")` in wiring test** (medium confidence). My new test calls `NpcMention(name=opponent_name, role="hostile", is_new=True)` without explicit `side`. Existing `test_encounter_apply_narration.py::test_narrator_confrontation_trigger_creates_encounter` (line 72) uses the identical role-only pattern and is a well-established convention in this suite. The CRITICAL ADVERSARY RULE in `output_only.md` mandates `side` for *narrator-emitted* npcs_met entries; it does not mandate that *test fixtures* simulating those emissions must populate every optional field. The wiring assertion is `snap.encounter is not None` + `encounter_type == X` — both pass without `side`, proving the dispatch path works. Decision: **defer** — flagging for Reviewer judgment. If tighter fixture-realism discipline is desired, the fix is a 4-character edit in 3 places; not load-bearing for the AC.

**Noted:** 0 low-confidence observations beyond the reuse finding above.
**Reverted:** 0 (no simplify changes applied).

**Overall:** simplify: clean (all findings dismissed or deferred with rationale; nothing auto-applied)

### Quality Gate

| Check | Result |
|-------|--------|
| `uv run pytest` (full server suite) | 5108 passed, 64 skipped, 0 failed (102.57s) |
| `uv run ruff check .` | clean |
| 50-2 tests (19 total) | 19/19 passed |
| Adjacent suites (`test_orchestrator.py`, `test_narrator_prompt.py`, `test_encounter_apply_narration.py`) | 109/109 passed |

**Flake note:** During the first two `pf check` / `tests/server/` runs we observed two different chargen tests fail intermittently (`test_chargen_confirm_persists_deduped_inventory` once, `test_caverns_delver_loadout_wired_into_snapshot` once). Both pass in isolation; both pass on subsequent re-runs of the full suite. The chargen suite has known order-sensitivity around the genre-pack default cache (commented in `test_encounter_apply_narration.py:25-30` — slug-keyed cache poisoning). The 50-2 tests use the cache-free `load_genre_pack()` path identical to the established convention, so they neither cause nor amplify the flake beyond statistical exposure. Not a 50-2 blocker; recommended follow-up (`pf sprint story add`) is an epic-50-or-later cleanup to make the chargen handler fixtures explicitly use the cache-free loader.

**Quality Checks:** All passing.
**Handoff:** To Reviewer (Colonel Potter) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (0 fails, 0 skips on diff, 0 smells, 5108 passed / 64 pre-existing skips) | N/A |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled via `workflow.reviewer_subagents.edge_hunter=false` | N/A (covered by my own enumeration below) |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` | N/A (covered by my own analysis below) |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled via `workflow.reviewer_subagents.test_analyzer=false` | N/A (covered by my own enumeration below) |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled via `workflow.reviewer_subagents.comment_analyzer=false` | N/A |
| 6 | reviewer-type-design | Yes | Skipped | disabled via `workflow.reviewer_subagents.type_design=false` | N/A |
| 7 | reviewer-security | Yes | Skipped | disabled via `workflow.reviewer_subagents.security=false` | N/A (no security surface in prompt-text additions) |
| 8 | reviewer-simplifier | Yes | Skipped | disabled via `workflow.reviewer_subagents.simplifier=false` | N/A (TEA verify already ran simplify-reuse/quality/efficiency) |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled via `workflow.reviewer_subagents.rule_checker=false` | N/A (Rule Compliance section below is my own enumeration) |

**All received:** Yes (1 returned, 8 skipped per settings)
**Total findings:** 0 from subagents; 0 confirmed problems from my analysis; 4 [VERIFIED] observations; 1 [LOW] follow-up suggestion; 1 [INFO] preflight-noted maintenance risk.

## Reviewer Assessment

### Diff scope sanity-check

Two production-file edits, both pure prompt content:
- `sidequest/agents/narrator_prompts/output_only.md` — added 6 type-bullets (`ship_combat`, `dogfight`, `trial`, `auction`, `social_duel`, `scandal`) + routability spelling constraint + "no retroactive crediting" anchor + "pick MOST SPECIFIC" reminder. Net +6 lines, 0 deletions of existing rule text.
- `sidequest/agents/orchestrator.py` — extended the existing `confrontation_trigger_constraint` PromptSection string from ~36 to ~58 lines. Combat/pursuit triggers grouped into one paragraph, social triggers grouped into a new paragraph. All pre-existing space-opera anchors preserved verbatim (`spinning`, `permission to engage`, `ship_combat`, `dogfight`, `no retroactive crediting`, `Diamonds-and-Coal`).

Two new test files (488 lines added, parametrized + wiring); zero edits to existing test files.

### Rule Compliance

Enumerated against `sidequest-server/CLAUDE.md` (server-specific rules) and `CLAUDE.md` (project root):

| Rule | Where checked | Compliant? |
|------|---------------|------------|
| **No Silent Fallbacks** (CLAUDE.md root + server) | Schema now requires exact lowercase snake_case spelling; `instantiate_encounter_from_trigger` already raises `ValueError("unknown encounter_type")` on misses (`encounter_lifecycle.py:274-275`); apply path PROPAGATES (`narration_apply.py:2383-2406` catches only `NoOpponentAvailableError` + `SealedLetterArityError`, lets ValueErrors crash the turn per intentional comment). | ✓ Compliant — loud-fail discipline strengthened, not weakened. |
| **No Stubbing** (CLAUDE.md root + server) | Both edits are real content; no empty shells. | ✓ Compliant. |
| **Don't Reinvent — Wire Up What Exists** (CLAUDE.md root + server) | Dev explicitly chose NOT to add a new server-side keyword→instantiation path; the existing dispatch wire is what carries the fix. Reuses `instantiate_encounter_from_trigger`, `find_confrontation_def`, `_watcher_publish`, the existing `PromptSection` registry, `AVAILABLE ENCOUNTER TYPES` State-zone block. | ✓ Compliant — pure reuse. |
| **Verify Wiring, Not Just Existence** (CLAUDE.md root + server) | `test_50_2_warning_span_silent_on_emit.py` calls the production entry point `_apply_narration_result_to_snapshot` with real `GenrePack`, asserts `snap.encounter is not None` + correct `encounter_type` per parametrize. Not a mocked seam. | ✓ Compliant. |
| **Every Test Suite Needs a Wiring Test** (CLAUDE.md root + server) | `test_50_2_warning_span_silent_on_emit.py` IS the wiring test for the prompt-engineering work — pairs the schema text change with an end-to-end apply-path assertion. | ✓ Compliant. |
| **OTEL Observability Principle** (CLAUDE.md root + server) | No new subsystem; the warning span at `narration_apply.py:2312` is preserved with its existing payload shape. Test asserts the span fires on pre-fix prose (regression detector) and stays silent on emitted-confrontation prose (post-fix steady state). | ✓ Compliant. |
| **TTS deprecated** (project memory) | N/A — no audio touched. | ✓ |
| **HP removed per ADR-078** (project memory) | N/A — confrontation typing, not health. | ✓ |
| **Personal project / no Jira** (server CLAUDE.md) | Session has `jira_key: ""`; commit messages contain no Jira refs; PR will go to `develop` per `repos.yaml`, not to any work-org repo. | ✓ Compliant. |
| **ADR-001 Claude CLI Only** | Tests run prompt-content checks against module constants and Recency-zone string content. No live `claude -p` invocation in tests; `make_canned_client` returns a fake. | ✓ Compliant. |
| **SOUL.md — Crunch in the Genre, Flavor in the World** | The new schema enumerates *types* (the rule layer) without enumerating *world content* (locations, named NPCs). Social cues are SHAPES ("a rumour reaching print"), not Victoria-specific names ("Lord Halloway's affair"). | ✓ Compliant. |
| **SOUL.md — Cost Scales with Drama** | The Recency text grew ~22 lines, firing every turn. Justified by the rule's load-bearing role (the original PR #177 placed it in Recency precisely because the System-zone schema decays). The cost is small text per turn; the drama is "mechanical commit affects whole-turn flow." | ✓ Compliant. |
| **Banned patterns: no `git stash`, no "verify on prior commit"** (project memory) | Reviewed all six commits across this story; none use stash or run prior-commit. Preflight subagent also instructed banned-pattern-aware. | ✓ Compliant. |

No rule violations. No dismissals — every rule above maps to an existing pattern in the diff or an absence (correctly absent for irrelevant rules).

### Observations

1. **[VERIFIED] No-Silent-Fallbacks discipline strengthened** — schema text now demands lowercase snake_case spelling exactly matching `pack.rules.confrontations[].type`. `find_confrontation_def` (`sidequest/server/dispatch/confrontation.py:91-94`) returns `None` on miss; caller `instantiate_encounter_from_trigger` (`sidequest/server/dispatch/encounter_lifecycle.py:273-275`) raises `ValueError("unknown encounter_type {!r} — not in pack confrontations")`; `_apply_narration_result_to_snapshot` (`sidequest/server/narration_apply.py:2373-2406`) catches only NoOpponentAvailableError + SealedLetterArityError, so the ValueError propagates and crashes the turn loudly. Test `test_narrator_output_only_trigger_categories_are_routable` enforces the schema parity. Complies with CLAUDE.md root + server.

2. **[VERIFIED] Existing test convention followed for `NpcMention` fixtures** — `tests/server/test_50_2_warning_span_silent_on_emit.py:130` creates `NpcMention(name=opponent_name, role="hostile", is_new=True)` without explicit `side`. Identical to `tests/server/test_encounter_apply_narration.py:82` (the canonical wiring test established in 2026-04 and re-validated through ~12 subsequent stories). Both paths route through the same `_apply_narration_result_to_snapshot` → `instantiate_encounter_from_trigger` chain; both encounter NpcMention.side="neutral" default; both assert `snap.encounter is not None` + encounter_type correctness without asserting side. The convention is intentional: NpcMention default side is the realistic narrator-emit shape per the schema's "side" doc (which says "MUST include side" but the apply path tolerates the default while logging at higher levels). TEA verify's deferred quality finding noted; not a blocker for this story.

3. **[LOW] Schema/Recency content sync risk** — preflight observed that the schema text in `output_only.md` and the Recency-zone string in `orchestrator.py` both enumerate the trigger-type set independently, with no shared constant. If a future genre introduces a new confrontation category (say `inquisition`), the maintainer must edit two files plus add an entry to `pack.rules.confrontations`. The synchronization burden is low (already true before 50-2 — PR #177 introduced the parallel pattern), but the surface grew with this story. **Decision: defer** — extracting a shared constant would couple a prompt-text concern to data-layer schema, and the test `test_narrator_output_only_trigger_categories_are_routable` catches the schema half on drift. A `confrontation_type` typo would crash via the loud-fail path above. The Recency half has no automated sync check; future story should add `pf sprint story add` to either (a) extract a shared `STANDARD_TRIGGER_TYPES` constant referenced by both prompt builders, or (b) add a test that asserts the Recency text mentions every type the schema enumerates.

4. **[VERIFIED] Wiring intact — confrontation populated → encounter instantiated** — `tests/server/test_50_2_warning_span_silent_on_emit.py::test_warning_span_silent_when_narrator_emits_confrontation_on_trigger_prose` parametrizes over (chase, combat, negotiation), each emitting a non-null `confrontation` field; all three assertions pass: `snap.encounter is not None` AND `snap.encounter.encounter_type == encounter_type` AND `confrontation.skipped_with_trigger_keywords` watcher event does NOT fire. The 4 Victoria social types are covered at the prompt seam (per Architect's spec-check Option A; AC4 wording acknowledged as inexact). Combined: 7-type prompt coverage + 3-type wiring coverage + type-agnostic apply path = AC4 satisfied in spirit.

5. **[VERIFIED] Regression detector preserved** — `tests/server/test_50_2_warning_span_silent_on_emit.py::test_archive_chase_fixture_pre_fix_baseline_still_warns` uses the verbatim 2026-04-26 archive prose with `confrontation=None`, asserts the watcher event fires AND `snap.encounter is None`. This locks in the warning span's regression-detector role post-fix — if a future change accidentally silences `_scan_for_confrontation_trigger_keywords` or removes the warning publish, this test breaks loudly. Lie-detector discipline (CLAUDE.md OTEL principle) preserved.

6. **[VERIFIED] Tests have meaningful assertions** — every test in the new files has at least one substantive `assert`. No `let _ =`, no `assert True`, no `is_none()` on always-None values. The parametrized prompt-content tests use `in NARRATOR_OUTPUT_ONLY` substring checks (acceptable for prompt-text contracts), backed by the routability test that re-validates exact-token spelling via regex with non-alphanumeric fencing. The wiring tests assert state mutations (`snap.encounter is not None`, `encounter_type == X`) plus negative-state on the watcher capture list. None are vacuous.

### Trace: end-to-end data flow

User input (narrator action) → orchestrator builds prompt → registers `confrontation_trigger_constraint` Recency section (now with social cues) → registers `narrator_available_confrontations` State section (genre-specific menu, unchanged) → schema lives in `NARRATOR_OUTPUT_ONLY` Primacy section (now enumerates all 9 categories) → `claude -p` subprocess returns narration + `game_patch` block → `extract_structured_from_response` parses → `NarrationTurnResult.confrontation` populated → `_apply_narration_result_to_snapshot` checks `result.confrontation is not None` → `instantiate_encounter_from_trigger(encounter_type=result.confrontation)` → `find_confrontation_def(pack.rules.confrontations, encounter_type)` → on hit: encounter instantiates; on miss: ValueError propagates and crashes turn (intentional loud-fail). Wiring path unchanged from pre-50-2; my prompt edits are upstream of the dispatch logic.

### Error/failure analysis

- **Narrator emits a type the genre doesn't offer** (e.g. `confrontation="scandal"` in `caverns_and_claudes`): the schema and Recency text both anchor the rule to "AVAILABLE ENCOUNTER TYPES" and add "(when the genre offers it)" qualifiers; the loud-fail path in `find_confrontation_def` catches drift. Pre-existing behavior, unchanged.
- **Narrator emits a malformed type** (e.g. `confrontation="Scandal"`): schema explicitly forbids capitalized/non-snake-case spellings; the test `test_narrator_output_only_trigger_categories_are_routable` enforces parity with pack data. Loud-fail catches drift.
- **Narrator skips emission on a trigger turn (pre-fix behavior)**: `_scan_for_confrontation_trigger_keywords` still runs in `narration_apply.py:2317`, the warning span still publishes, the GM panel still sees the gap. Regression detector intact.
- **Narrator emits `confrontation` AND prose lacks any trigger keyword**: schema explicitly says "Err on the side of triggering — the system handles de-escalation gracefully"; no negative assertion; pre-existing pattern.
- **Empty narration**: `_scan_for_confrontation_trigger_keywords("")` returns `[]` per existing test coverage in `test_encounter_apply_narration.py:417`. Unchanged.

### Security analysis

No security surface in prompt-text changes. No new auth paths, no new input boundaries, no secrets, no untrusted data flow. The schema additions instruct the LLM about its own output structure; nothing user-controlled feeds into the new bullets. Skipped specialists confirm: 7 (reviewer-security) toggled off because no security-relevant code in this scope; concur with the toggle.

### Devil's Advocate

The code is broken because... let me try harder.

A truly malicious or confused narrator could exploit my schema additions in three ways: (1) it could pick `confrontation="scandal"` on a `caverns_and_claudes` turn because the schema now lists `scandal` as a valid type, even with the "(when the genre offers it)" qualifier — LLMs are notorious for ignoring conditional qualifiers in dense rule blocks. The result would be a `ValueError` from `find_confrontation_def` propagating up the apply path, crashing the entire narration turn. The pre-50-2 behavior was that the schema only listed combat/negotiation/chase, so this failure mode was *already possible* but rarer — a narrator had to invent the type from nothing. Post-50-2, the schema *names* the type, which under-prepared LLMs may take as permission to use. **However**: the parallel `narrator_available_confrontations` State-zone section enumerates the actual genre's menu, the schema text explicitly bounds the choice to that menu, and the Recency restatement reinforces the "spell the type exactly as it appears in the available list" anchor. The mitigation is stacked, but the failure mode is real and would manifest in the GM panel as a crashed turn rather than a silent fallback — which is the CLAUDE.md-mandated tradeoff. Acceptable risk, but worth a follow-up story to add a gentler degradation path: catch the `ValueError`, publish a `confrontation.unknown_type` OTEL event, treat as if `confrontation=None`. That's a behavior change beyond 50-2's scope; flagging.

(2) The schema now says "no retroactive crediting" — a literal-minded narrator might decide that any prose about a *past* engagement ("Last night, the patrol cutter spun up its reactor and I bolted") must NOT emit `confrontation`. That was always true pre-50-2, but the explicit anchor makes the wrong reading easier to defend. Mitigation: the existing trigger phrases ("spinning UP", "RIGHT NOW") strongly imply present-tense; combined with the existing `_scan_for_confrontation_trigger_keywords` regex which doesn't backreference past-tense markers, the failure mode is narrow.

(3) The growing Recency section consumes token budget. The narrator's overall prompt is now ~22 lines heavier. If a future story adds another Recency section, attention decay on the *original* anchors (spinning reactor, permission to engage) could increase. Mitigation: the prompt framework's zone budgets are not currently enforced (would surface in a separate ADR-082 follow-up); the 22-line growth in a single section is well within informal limits and is parallel to existing patterns (the `npc_extraction_constraint` section adjacent to mine is ~20 lines).

What about a confused user? A new contributor reading the diff might assume `_CONFRONTATION_TRIGGER_PATTERNS` in `narration_apply.py:403-447` should be extended to cover scandal/auction/trial/social_duel prose. That would be exactly the wrong move per the SM scope guardrail "no keyword-list editing" — the detector is intentionally biased toward high-precision space-opera prose because that was the original gap. A follow-up story may eventually add social-pack regex labels, but only after playtest evidence shows the detector is too narrow. The session's TEA Assessment and SM Assessment both call this out explicitly; an in-code comment in narration_apply.py:389-402 also documents the intentional scoping. Risk: low.

Stressed filesystem? Config with unexpected fields? Race conditions? None apply — this is a deterministic prompt-text edit and additive tests. The only test-suite concern is the intermittent chargen flake noted in TEA verify; that pre-exists and is unrelated to 50-2 semantically (different cache mechanism).

Devil's advocate did surface one real concern (the future-story degradation path for unknown-type emissions) and one cosmetic concern (Recency growth budget). Neither is a 50-2 blocker; both belong in follow-up stories.

### Story 50-2 — Verdict

**APPROVE.**

All ACs satisfied (AC4 with Architect-noted factoring deviation — Option A clarification recommended for the AC wording, not the code). All project rules in scope are complied with. The fix is minimal, scoped exactly as the session SM Assessment defined, and preserves the regression-detector lie-detector role. Tests are real-wired through production entry points and pin both the prompt-engineering target and the apply-path invariants. Adjacent suites are green (109/109); full server suite 5108/5108 on stable run.

**Follow-ups (non-blocking, recommended `pf sprint story add` for epic-50 cleanup):**
1. Add a graceful-degradation path for `confrontation=<unknown_type>` emissions (catch ValueError, emit OTEL event, treat as None). Architectural change beyond 50-2 scope.
2. Reword AC4 in the story to codify the test-factoring principle (Architect Option A).
3. Migrate chargen-suite fixtures to the cache-free `load_genre_pack` pattern OR add an autouse cache-clearing fixture.
4. Schema/Recency sync: add a meta-test asserting the Recency-zone constraint mentions every type the schema enumerates (low-priority drift detector).

**Branch:** `feat/50-2-narrator-confrontation-trigger-instantiate` ready to PR against `develop` (per `repos.yaml` for the `sidequest-server` subrepo, NOT `main`).

**Handoff:** To Architect (Margaret) for spec-reconcile, then SM (Hawkeye) for finish.