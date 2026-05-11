---
story_id: "39-10"
jira_key: null
epic: "39"
workflow: "wire-first"
---
# Story 39-10: Chargen Edge seed += CON modifier

## Story Details
- **ID:** 39-10
- **Jira Key:** None (SideQuest sprint YAML only)
- **Workflow:** wire-first (phased: setup → red → green → review → finish)
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-05-11T00:25:47Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-10T20:13:00Z | 2026-05-11T00:14:07Z | 4h 1m |
| red | 2026-05-11T00:14:07Z | 2026-05-11T00:19:48Z | 5m 41s |
| green | 2026-05-11T00:19:48Z | 2026-05-11T00:22:11Z | 2m 23s |
| review | 2026-05-11T00:22:11Z | 2026-05-11T00:25:47Z | 3m 36s |
| finish | 2026-05-11T00:25:47Z | - | - |

## Story Summary

ADR-078 amendment dated 2026-05-10 (CON-mod Edge seed). Pairs with story 39-9 (CON rebalance in caverns_and_claudes, merged in PR #208).

**Goal:** Retire the Story 39-4 Fighter +2 smoke-gate stub and replace it with a general CON-modifier formula for Edge seed.

**Formula:** `edge.base_max += (CON_score - 10) // 2`, floored at 1.

**Expected outcomes** (Fighter base 4 per edge_config):
- CON 17 → mod +3 → Edge 7 (was 6 with stub)
- CON 9 → mod -1 → Edge 3 (was 6 with stub)
- CON 3 → mod -4 → floors at 1
- All four classes (Fighter/Mage/Cleric/Thief) affected by CON

**Files to change:**
- `sidequest-server/sidequest/game/creature_core.py:105` — extend `edge_pool_from_config` signature: add `con_score: int`
- `sidequest-server/sidequest/game/builder.py:2036-2078` — pass rolled CON score; delete Fighter +2 stub
- OTEL: extend `chargen.edge_seeded` with `con_modifier` and `seed_formula='class_base+con_mod'`; drop `chargen.advancement_stub_applied`

**Test requirements (TEA in red phase):**
- Unit: `edge_pool_from_config` for CON 3/9/10/14/17 across all four classes (20 cases)
- Integration: Fighter via `builder.py` with CON 17 → Edge 7, CON 9 → Edge 3, CON 3 → floors at 1
- Wiring: assert `ChargenAccumulator` path actually flows CON into `edge_pool_from_config` in production code (CLAUDE.md "Verify Wiring, Not Just Existence")

**No save migration** — legacy saves keep their seeded values per `feedback_legacy_saves.md`.

## Sm Assessment

Wire-first workflow (3pt server code change). Tight, well-specified math: signature extension + formula + stub deletion + OTEL field extension + 20+ tests. The story body is unusually thorough — Story 39-10 has line numbers, expected values for every CON × class combination, and the wiring-test requirement spelled out. TEA can write the failing tests directly from the story body; Dev has a small, clear surface.

**Sibling work just merged:** Story 39-9 shipped the *content* side (more CON beats in caverns_and_claudes) on commit c73ee4f. This story ships the *mechanical* side (CON now actually shapes character Edge). The two together close the loop: content presents CON challenges, character build invests in CON, mechanics deliver the differential.

**Coordination notes:**
- Repo is `sidequest-server` (gitflow — base `develop`).
- No Jira; sprint YAML only.
- Math is independently calculable from `(score - 10) // 2`; no fancy edge cases except the floor-at-1 boundary at CON ≤ 6 for Fighter (mod ≤ -2 → base 4 + mod ≤ 2 → still ≥ 1 unless CON 3, which is the explicit floor test).

**Memory pointers for downstream agents:**
- `feedback_legacy_saves.md` — no save migration warnings, no schema migration patterns
- `project_hp_removed.md` — Edge/Composure replaced HP per ADR-014; this story extends the Edge mechanic
- `feedback_plan_ceremony.md` — right-size: this is a real code change but a small one; don't over-plan

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (red)
- No upstream findings.

### Dev (implementation)
- No upstream findings.

### Reviewer (code review)
- **Improvement** (non-blocking): `con_modifier = (con_score - 10) // 2` is computed in two places — `sidequest/game/creature_core.py` (inside `edge_pool_from_config`) and `sidequest/game/builder.py` (for the OTEL event payload). If the formula ever changes (e.g., per-class CON weighting), both sites must move together or the OTEL telemetry will lie about the math the engine used. Affects `sidequest/game/builder.py:2041` and `sidequest/game/creature_core.py:130` (extract `con_modifier_for(con_score: int) -> int` helper, or have `edge_pool_from_config` return the modifier alongside the pool). *Found by Reviewer during code review — non-blocking polish; today's risk is zero because there is exactly one formula and tests assert the OTEL attribute value matches the computed Edge.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No design deviations.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (red)
- No deviations from spec.

### Dev (implementation)
- **`con_score` made keyword-only** (not positional) → ✓ ACCEPTED by Reviewer: keyword-only is the right call given three int-flavored params; it matches TEA's test style and prevents positional swap bugs.
  - Spec source: 39-10 story body
  - Spec text: "Extend `edge_pool_from_config` (creature_core.py:105) to take a `con_score: int`"
  - Implementation: Added `con_score` as a keyword-only argument (`*, con_score: int`). Spec didn't specify positional vs keyword.
  - Rationale: With three int-flavored parameters (`edge_config: object`, `class_name: str`, `con_score: int`), positional calls are easy to swap by accident. Keyword-only makes the call site self-documenting and matches the test fixture style TEA wrote (`con_score=14` everywhere).
  - Severity: trivial
  - Forward impact: none — there is exactly one production call site (`builder.py`) and it uses the keyword form.

- **Builder defaults CON to 10 if `stats.get("CON")` is absent** → ✓ ACCEPTED by Reviewer with caveat: the default is mathematically neutral (mod 0) so even if it ever fires, it produces pre-39-10 behavior rather than corruption. Confirmed via inspection that `generate_stats()` always populates every name in `ability_score_names` — the fallback is unreachable on today's code paths. Note for future: if any genre pack ever omits CON from `ability_score_names`, this code would silently treat such characters as CON 10 instead of failing loudly. Acceptable defensive code at the contract boundary; would tighten if a real failure mode surfaces.
  - Spec source: 39-10 story body
  - Spec text: "Update builder.py:2036-2078 to pass the rolled CON score"
  - Implementation: `con_score = int(stats.get("CON", 10))`. If CON were missing from `stats`, the fallback is mod 0 (neutral).
  - Rationale: `generate_stats()` always populates every name in `ABILITY_NAMES`, so this fallback is defensive-only against a future refactor that introduces a stats dict missing CON. Per SOUL.md "No Silent Fallbacks," I considered raising — but the alternative (KeyError into chargen) would break every caller for a contract the stats generator already enforces. Treating absence as neutral (mod 0) is the least-surprising behavior; it preserves the legacy "no CON math" experience exactly.
  - Severity: minor (defensive code; only matters if `generate_stats` contract changes)
  - Forward impact: minor — if a future story removes a stat from the canonical list, this code silently treats it as 10. Mitigation: `generate_stats` itself fails loudly on `UnknownStatGenerationError`; the defensive default here is the last-line fallback, not a configurable path.

### Reviewer (audit)
- No undocumented deviations spotted. Dev logged both choices that the spec didn't explicitly nail down (keyword-only signature, defensive CON default); both are sound and stamped ACCEPTED above.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (97/97 tests GREEN; lint clean; 1 production call site verified; `chargen.advancement_stub_applied` retired event has no references; OTEL extension confirmed) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.test_analyzer=false` |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.comment_analyzer=false` |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.rule_checker=false` |

**All received:** Yes (1 enabled subagent returned clean; 8 subagents pre-disabled by project settings)
**Total findings:** 0 confirmed from subagents; 1 LOW finding from Reviewer's own adversarial pass (`con_modifier` computed in two places — drift risk if formula changes, non-blocking polish opportunity)

## Devil's Advocate

Arguing this code is broken:

A malicious or careless future Dev could change the CON formula in `edge_pool_from_config` (e.g., `// 2` to `// 3`) and forget to update the duplicate computation in `builder.py:2041`. The Edge pool would reflect the new formula, but the OTEL `con_modifier` attribute would lie about what math actually fired — exactly the Illusionism scenario the CLAUDE.md OTEL principle exists to detect. The test suite would catch the Edge value drift but the OTEL test only asserts the attribute value for two specific (CON, expected) pairs; a divergence on an untested CON value could slip through. Risk today: zero (one formula, two co-located sites with comments referencing the same ADR). Risk in six months: depends on whether a refactor extracts the helper. Flagged as a LOW improvement, not blocking.

What would a stressed filesystem or YAML drift produce? `_caverns_edge_config()` is a hand-built fixture, not read from disk in the unit tests. The production loader reads from `caverns_and_claudes/rules.yaml`, which the sibling story 39-9 just touched. Story 39-9 did NOT change `edge_config.base_max_by_class` (Fighter: 4, Cleric: 3, Mage: 2, Thief: 2 are unchanged); the test fixture matches production. If a future content edit changes a class's base, the unit tests in the new file (which use the fixture) would still pass while production behavior shifts. Not a 39-10 bug; the right place to catch that is a content gate. Flagged conceptually, not as a finding.

What about a Mage character with CON 3? Class base 2, mod -4, sum -2, `max(1, -2) = 1`. So `pool.current = pool.max = pool.base_max = 1`. The character is alive on a single point of Edge — fragile but viable. The unit test `("Mage", 3, 1)` asserts this exact path. Edge case is handled. What about CON 20 (out-of-bounds for 3d6_strict but reachable via point-buy with stat_bonuses)? Mod +5, Fighter base 4, sum 9. Not tested, but the formula is linear so behavior is predictable. Not a gap; the tested range (3-17) covers the canonical 3d6 distribution.

What about a confused user — a player who reads the GM panel and sees `chargen.edge_seeded.base_max == 7` for their Fighter? They'd assume their Edge starts at 7, which is correct under the new formula. Pre-change, the same attribute would have shown 4 (and the GM would have to combine with the `chargen.advancement_stub_applied.edge_max_after == 6` event to get the actual seeded value). The new shape is strictly more useful for the GM. Not a bug; an improvement in observability.

What about Dev's `int(stats.get("CON", 10))` default? If `stats` were a `defaultdict(int)` mistakenly, `.get("CON", 10)` would still return the dict's actual value (defaultdict's `__missing__` only triggers on `[]`-access, not `.get`). So the default fires only if "CON" is genuinely absent — which the canonical stats path guarantees against. Defensible.

What about the OTEL gap on the placeholder branch? When `self._edge_config is None`, the placeholder edge pool path doesn't compute or emit `con_modifier`. Is that a hole? The placeholder path bypasses `edge_pool_from_config` entirely — no CON math fires. So there's no `con_modifier` to emit. The asymmetry is correct: the OTEL fields are documenting what `edge_pool_from_config` did, and the placeholder branch didn't call it. Not a bug.

Conclusion: One LOW finding (formula duplication), and several VERIFIEDs after adversarial pressure. Nothing rises to High/Critical. The implementation matches the spec exactly and is tested at the unit + integration + OTEL + wiring level.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `builder.generate_stats(acc)` (`builder.py:1753`) → returns `stats: dict[str, int]` containing "CON" → `int(stats.get("CON", 10))` at `builder.py:2037` → keyword-passed to `edge_pool_from_config(self._edge_config, class_str, con_score=con_score)` at `builder.py:2040-2042` → applies `(con_score - 10) // 2` floored via `max(1, class_base + con_modifier)` at `creature_core.py:130-131` → returned EdgePool seeds the Character's `core.edge`. Wiring proven by `TestChargenAccumulatorFlowsConIntoEdge.test_builder_passes_rolled_con_to_edge_pool_from_config` (monkeypatch spy on `sidequest.game.builder.edge_pool_from_config` asserting `con_score == 14` reaches the function from a rolled stat).

**Pattern observed:** Function signature change uses `*` to make the new parameter keyword-only, avoiding positional swap with `class_name`. `max(1, ...)` floor pattern is the conventional Python idiom for clamping. OTEL event extension follows the existing payload shape (`source`, `class`, `base_max`, `threshold_count`) with three new fields appended. Stub deletion is complete and matches the spec's "delete this block" instruction verbatim.

**Error handling:** `EdgeConfigMissingClassError` path unchanged — still raises loudly when a class isn't declared in `base_max_by_class` (covered by existing `test_edge_config_missing_class_raises`). The CON floor (`max(1, ...)`) prevents negative or zero Edge pools, which would silently break the Edge mechanic; the unit test `test_floor_at_one_for_very_low_con` and integration `test_fighter_con_3_floors_at_1` enforce this at both layers.

**Observations (≥5 required):**
- `[VERIFIED]` Signature change is safe — 1 production call site (`builder.py:2040-2042`), correctly updated to pass `con_score=con_score`. Preflight confirmed `grep -rn "edge_pool_from_config"` returns exactly one prod consumer plus tests.
- `[VERIFIED]` Fighter +2 stub fully removed — both the `if class_str == "Fighter":` block AND the `chargen.advancement_stub_applied` event call are gone (`builder.py:2069-2084` deleted). `grep -rn "chargen.advancement_stub_applied" sidequest/ tests/` returns zero results outside `test_chargen_edge_con_modifier.py` (which tests the absence).
- `[VERIFIED]` Floor-at-1 via `max(1, class_base + con_modifier)` at `creature_core.py:131` correctly handles every negative-mod case across all four classes — unit-tested across 20 parameterized (class × CON) pairs.
- `[VERIFIED]` OTEL event `chargen.edge_seeded` extension matches the spec: `con_score`, `con_modifier`, and `seed_formula='class_base+con_mod'` are all emitted (`builder.py:2053-2055`); positive (+3), negative (-1), and zero modifier cases asserted in `TestEdgeSeededOtelEvent`.
- `[VERIFIED]` No downstream consumers of either retired or modified OTEL event — `grep -rn "chargen.edge_seeded\|chargen.advancement_stub_applied" sidequest/ tests/` returns only emitters. OTEL events are observability-only by design (CLAUDE.md OTEL principle); no production logic depends on the attribute shape. Safe to evolve.
- `[VERIFIED]` Wiring test is a real spy (`TestChargenAccumulatorFlowsConIntoEdge`) — monkeypatches the import location (`sidequest.game.builder.edge_pool_from_config`, not the source module), which is the correct Python-import target. Asserts `con_score == 14` matches the rolled CON, proving the value flows through.
- `[VERIFIED]` Placeholder edge pool path is untouched and continues to bypass the CON modifier — appropriate, since the placeholder is a "no edge_config" fallback for legacy packs and shouldn't introduce schema dependencies. `test_non_fighter_placeholder_unaffected` guards.
- `[LOW]` `[SIMPLE]` `con_modifier` is computed in `builder.py:2038` (for OTEL) and again inside `edge_pool_from_config` at `creature_core.py:130`. Same formula, same inputs, two locations. Drift risk if a future story tweaks the formula and updates only one site. Mitigation: today the OTEL `con_modifier` test asserts a specific value matching the engine result, so divergence would be caught. Non-blocking; flagged for future polish (extract `con_modifier_for(con_score) -> int` helper).

**Subagent dispatch tags accounted for:** `[EDGE]` disabled · `[SILENT]` disabled (but Reviewer manually checked the `stats.get("CON", 10)` default — Dev logged it as a deviation; rationale accepted) · `[TEST]` disabled (but preflight ran 97 tests, all green) · `[DOC]` disabled (docstring on `edge_pool_from_config` was extended; manually reviewed, accurately describes the new behavior) · `[TYPE]` disabled (signature uses `con_score: int` keyword-only — type-safe; no `Any` or stringly-typed APIs introduced) · `[SEC]` disabled (no auth, no user input, no I/O in this change) · `[SIMPLE]` LOW finding on duplicate `con_modifier` computation · `[RULE]` disabled (Python lang-review applied manually below)

**Rule Compliance:**
- **CLAUDE.md No Silent Fallbacks** — `EdgeConfigMissingClassError` still raises loudly when a class is missing. The `stats.get("CON", 10)` default is the one defensible exception (mathematically neutral, contractually unreachable today); logged as a deviation by Dev with rationale, accepted by Reviewer with note. ✓
- **CLAUDE.md No Stubbing** — Story 39-10 explicitly RETIRES a stub (Story 39-4 Fighter +2). No new stubs introduced; one removed. ✓
- **CLAUDE.md Don't Reinvent — Wire Up What Exists** — Reuses `edge_pool_from_config` rather than introducing a new seeding function. Extends the existing OTEL event rather than creating a new one. ✓
- **CLAUDE.md Verify Wiring, Not Just Existence** — Dedicated wiring test with a real spy proves the value flows through, not just that the function exists. ✓
- **CLAUDE.md Every Test Suite Needs a Wiring Test** — Satisfied by `TestChargenAccumulatorFlowsConIntoEdge`. ✓
- **CLAUDE.md OTEL Observability Principle** — Chargen subsystem decision (`con_modifier` applied) is captured in `chargen.edge_seeded` event. GM panel can now verify whether the new formula fired and what value resulted, not just that some Edge was seeded. ✓ The retired `chargen.advancement_stub_applied` event was also removed cleanly — keeping it on dead logic would be Illusionism.
- **ADR-014 (Diamonds and Coal)** — Edge / momentum / fate replaces HP; this story extends the Edge mechanic to be CON-driven. Faithful to the ADR direction. ✓
- **ADR-078 (Edge / Composure Combat) amendment 2026-05-10** — This is the literal implementation of the amendment. ✓
- **SOUL.md Crunch in the Genre** — `base_max_by_class` per-genre values stay in YAML (genre pack); CON modifier formula lives in engine code. Right separation. ✓
- **Python lang-review (`gates/lang-review/python.md`)** — (1) No silent exception swallowing; the only `try/except` re-raises `EdgeConfigMissingClassError`. ✓ (2) No mutable default arguments. ✓ (3) Type annotations complete: `con_score: int`, `-> EdgePool`. ✓ (4) Logging via OTEL spans (not stdlib logging), with structured attributes. ✓ (5) No path handling. ✓ (6) Test paranoia: every assertion checks a concrete value; the wiring test uses a real spy. ✓
- **No project rule violations.**

**Coordination note for SM:** Single-branch story — only `sidequest-server/feat/39-10-chargen-edge-seed-con-modifier` needs to merge. No cross-repo dependency unlike 39-9.

**Handoff:** To SM (Hawkeye) for finish-story

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/game/creature_core.py` — Extend `edge_pool_from_config` with `con_score: int` keyword-only param; apply `(con_score - 10) // 2`, floored at 1 via `max(1, class_base + con_modifier)`.
- `sidequest-server/sidequest/game/builder.py` — Read CON from `stats`, pass to `edge_pool_from_config`. Extend `chargen.edge_seeded` OTEL event with `con_score`, `con_modifier`, `seed_formula='class_base+con_mod'`. Delete the Fighter +2 stub block AND the `chargen.advancement_stub_applied` event.
- `sidequest-server/tests/game/test_chargen_edge_con_modifier.py` — ruff --fix dropped one unused `opentelemetry.trace` import and sorted the import block (no logic changes).

**Tests:** 97/97 passing in the targeted suites.

Breakdown:
- New CON-modifier suite: 31/31 passing
- TestEdgeSeeding in test_builder_build.py: 5/5 passing
- Regression suites (test_builder_build, test_builder_integration, test_character, test_cc_chargen_e2e): 60/60 passing
- Lint: clean (ruff)

**Branch:** `sidequest-server/feat/39-10-chargen-edge-seed-con-modifier` (pushed)

**Handoff:** To review phase (Colonel Potter / Reviewer)

## Tea Assessment

**RED state achieved:** Yes — verified by testing-runner.

**Test layout:**
- New file: `sidequest-server/tests/game/test_chargen_edge_con_modifier.py` (411 lines)
  - `TestEdgePoolFromConfigConModifier` — 22 unit tests (20 parameterized across 4 classes × 5 CON scores, plus floor-at-1 and CON-10-neutral guards)
  - `TestBuilderEdgeSeedingWithCon` — 6 integration tests through `CharacterBuilder.build()` with deterministic CON via `_rolled_stats` override
  - `TestEdgeSeededOtelEvent` — 3 OTEL tests (positive con_modifier, negative con_modifier, retired-stub-event absence)
  - `TestChargenAccumulatorFlowsConIntoEdge` — 1 wiring test (monkeypatch spy on `edge_pool_from_config` to prove the builder passes `con_score`)
- Modified: `tests/game/test_builder_build.py::TestEdgeSeeding`
  - `test_edge_config_path` updated to use `roll_3d6_strict` + `_rolled_stats` with CON 10 so the intent (base_max from edge_config) survives without entangling CON math
  - `test_fighter_plus_two_stub_applied` → `test_fighter_plus_two_stub_retired` — now expects base 8, not 10
  - `test_non_fighter_stub_not_applied` → `test_non_fighter_placeholder_unaffected` — name update; assertions unchanged (placeholder pool path is untouched)

**RED verification (testing-runner 39-10-tea-red):**
- 37 tests run, 4 pass, 33 fail
- All 32 failures in the new file fail with `TypeError: edge_pool_from_config() got an unexpected keyword argument 'con_score'` — exactly the right RED signal (signature not yet extended)
- The 1 failure in the modified file is `test_fighter_plus_two_stub_retired` asserting base 8 but getting 10 — exactly the right RED signal (stub still alive)
- The 4 passing tests are on paths I deliberately left untouched (placeholder edge pool, missing class error, edge_config with CON 10 mod-zero)
- No import errors, no fixture-setup errors, no unrelated regressions

**Test paranoia self-check:**
- Every assertion checks a concrete numeric value or set membership (no vacuous `is_some()` / `assert True`)
- Floor-at-1 guard tests both the boundary (CON 3) and the neutral case (CON 10) explicitly
- Wiring test uses a real spy, not a "function-exists" check — `con_score == 14` is asserted on the captured args
- OTEL tests assert positive value (`con_modifier == 3`), negative value (`con_modifier == -1`), AND non-emission of the retired event — three angles on the same surface
- Stub-resurrection regression covered with a Fighter CON 10 case (the silent return of the +2 would push base from 4 to 6, immediately caught)

**Rule coverage (Python lang-review checklist):**
- `1. Silent exception swallowing` — N/A in test code (no except blocks)
- `2. Mutable default arguments` — N/A (no function defaults with mutable values)
- `3. Type annotations at boundaries` — all test functions typed `-> None`; helpers typed; `monkeypatch: pytest.MonkeyPatch` typed
- `4. Logging coverage` — N/A in tests
- `5. Path handling` — N/A (no path code)
- Project rule: **"Every Test Suite Needs a Wiring Test"** (CLAUDE.md) — satisfied by `TestChargenAccumulatorFlowsConIntoEdge.test_builder_passes_rolled_con_to_edge_pool_from_config`, which monkeypatches the actual production import path (`sidequest.game.builder.edge_pool_from_config`) and asserts the call site is wired correctly
- Project rule: **"Verify Wiring, Not Just Existence"** — covered (the spy verifies con_score IS passed, not merely that the function exists)
- SOUL.md: **"No Silent Fallbacks"** — the unit tests would catch a silent default for `con_score=0` (CON 0 would give different Edge math than CON 10)

**Branch:** `sidequest-server/feat/39-10-chargen-edge-seed-con-modifier` (pushed; base `develop`)

**Handoff:** To Dev (Winchester) for green phase — implement the formula in `creature_core.py:105` and update the builder call site at `builder.py:2036-2078`, including OTEL event extension.