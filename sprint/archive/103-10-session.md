---
story_id: "103-10"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 103-10: End-to-end wiring + regression

## Story Details
- **ID:** 103-10
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Story Summary

**Acceptance Criteria:**
1. Integration test per stock: chargen → narrator opening → confrontation where Saint drawback/stock trait mechanically fires (OTEL-asserted) → save cycle.
2. flickering_reach regression: loads and plays clean, Saint-less, Wild-Mutant-default.
3. cliché-judge audit over shipped content passes.
4. Server loads `seaboard_of_saints` with zero validation errors; every `saints.yaml`/`stocks.yaml` mutation reference resolves against the genre catalog.
5. All 17 regions present in places/cartography.

**Build Plan Reference:** `docs/superpowers/specs/completed/2026-06-10-seaboard-of-saints-build-plan.md` (§4 DoD)

**Critical Dependencies:** All prior stories (103-1 through 103-9). Critical path: 103-1 → 103-2 → 103-8 → 103-10.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-11T15:12:47Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-11T14:41:21+00:00 | 2026-06-11T14:43:23Z | 2m 2s |
| red | 2026-06-11T14:43:23Z | 2026-06-11T15:00:47Z | 17m 24s |
| green | 2026-06-11T15:00:47Z | 2026-06-11T15:08:34Z | 7m 47s |
| review | 2026-06-11T15:08:34Z | 2026-06-11T15:12:47Z | 4m 13s |
| finish | 2026-06-11T15:12:47Z | - | - |

## Sm Assessment

**Story:** 103-10 — the capstone end-to-end wiring + regression story for epic 103 (Seaboard of Saints). 5pts, TDD/phased, repos: server + content.

**Readiness:** Unblocked. The critical path (103-1 → 103-2 → 103-8 → 103-10) is fully merged; all five engine/content prerequisites (Saint layer, stock system, world core, regions, dramatic content) are `done`. The session header lists "103-1 through 103-9" as dependencies, but **103-9 (asset gate) is off the critical path and intentionally in-flight** — Keith confirmed assets are being worked in parallel. 103-10's scope (integration tests, flickering_reach regression, cliché audit, mutation-ID resolution, region presence) requires no rendered portraits/POIs/audio, so the asset gate is not a blocker. **TEA: do not gate RED on 103-9.**

**Routing rationale:** TDD-phased because this is engine-touching integration work (OTEL-asserted confrontation firing, save-cycle, server pack load) — not content-only validation. The content half (flickering_reach regression posture, cliché-judge audit) is verified within the same suite rather than routed to GM, since the AC binds them to mechanical assertions (loads-clean + Wild-only + zero-Saint).

**Watchpoints for RED:**
- AC1 wants OTEL spans (`awn.saint.applied` / `awn.stock.applied`, plus drawback-fires-in-confrontation) asserted — write span-assertion tests, per the project's "GM panel is the lie detector" principle.
- AC4's "every saints.yaml/stocks.yaml mutation reference resolves against the genre catalog" must run against `load_genre_pack`, not just the validator (validator PASS ≠ loader pass — known trap).
- flickering_reach regression must assert *zero* Saint content, not merely "loads."

**Next agent:** TEA (Fezzik) — RED phase.

## TEA Assessment

**Tests Required:** Yes
**Status:** All 13 GREEN on authoring (see "Honesty note" below — this is the correct outcome for a capstone wiring/regression story).

**Test File:**
- `sidequest-server/tests/integration/test_103_10_seaboard_e2e.py` — 13 tests, 5 classes + 1 marquee async test. Drives REAL production seams (`load_genre_pack`, `load_saint_registry`/`load_stock_registry`, `_load_cartography`, `init_mutation_state_for_session`, `_apply_narration_result_to_snapshot`, `PgSaveRepository`). Models on `test_102_7_mutant_wasteland_mutations_live.py` (confrontation cast-spine) + `test_mutation_wiring.py` (PG save/reload).

**AC → test mapping (build plan §4 DoD):**
| AC | Coverage | Status |
|----|----------|--------|
| AC1 — chargen per stock, OTEL-asserted | `TestPerStockChargenOtel` (saint_marked / harbor_seal animal / sleeper / wild) | GREEN |
| AC1 — confrontation drawback fires + save cycle | `test_saint_marked_drawback_lives_through_confrontation_and_save` (marquee) | GREEN |
| AC2 — flickering_reach Saint-less regression | `TestFlickeringReachRegression` | GREEN |
| AC3 — cliché audit | **NOT a pytest** — agent-judgment task, content-lane action (see Delivery Findings) | OPEN |
| AC4 — content resolves against catalog | `TestSeaboardContentResolvesAgainstCatalog` (+ loud-fail guard) | GREEN |
| AC5 — all 17 regions present | `TestSeaboardCartography` (asserts `>= 17`; content has 18) | GREEN |

**Honesty note (why RED is GREEN):** the epic's engine (103-1/103-2) and content (103-4..103-8) all landed and merged before this capstone. The e2e/regression tests therefore PASS on authoring — they *prove and guard* the wiring rather than drive new production code. This is a legitimate capstone outcome ("Every Test Suite Needs a Wiring Test"), not a vacuous pass: every test exercises a real production path and would fail loudly on a broken seam (e.g., the loud-fail guard `test_unresolvable_mutation_reference_fails_loud` proves the validator has teeth; the marquee asserts spans fire + state survives PG). There is no production code for Dev to write for GREEN.

### Rule Coverage
N/A — 103-10 adds no production types/constructors/handlers (integration/regression proof over already-shipped code). The lang-review checklist targets production-code design; no new production surface exists in this story. See Design Deviations.

**Self-check:** 0 vacuous tests. Every test has a meaningful assertion on a value or span; `test_draft_world_is_skipped_by_pack_load` asserts current production behavior (guards the explanation the rest of the file depends on) and is not vacuous.

**Handoff:** To Dev (Inigo) for GREEN. GREEN is **confirmatory** (re-run the file + full suite) PLUS two real content-lane actions that the tests cannot encode:
1. **AC3 cliché audit** — run the `cliche-judge` subagent over `worlds/seaboard_of_saints/*` (spec §11 bans) and record the result. **Required before close.**
2. **AC5 region reconciliation** — content ships 18 regions vs spec/DoD's 17; confirm intentional or correct the count (GM lane).
Optional follow-up: the draft-world validation gap (Delivery Findings) — a CI guard so seaboard content is validated in production before the asset gate lifts draft.

## Dev Assessment

**Implementation Complete:** Yes (GREEN confirmed + AC3 resolved)

**Files Changed:**
- `sidequest-server/tests/integration/test_103_10_seaboard_e2e.py` — the capstone e2e/regression test suite (committed during RED; the deliverable).
- `sidequest-content/.../seaboard_of_saints/bestiary.yaml` — 1-word fix: Handcar Wrecker `role:` "raider" → "looter" (resolves the one objective §11 ban-word the cliché audit found).

**No production server code changed** — the epic's engine + content shipped in 103-1..103-8, so GREEN was confirmatory, not constructive.

**Tests:** 13/13 GREEN in `test_103_10_seaboard_e2e.py` (with `SIDEQUEST_TEST_DATABASE_URL` set so the marquee PG test runs, not skips). Regression: full `tests/integration/` + `tests/mutation/` = 498 passed, 0 failed, 18 skipped (baseline) — no new failures.

**AC status:** AC1 ✓ (per-stock chargen OTEL + marquee confrontation/save), AC2 ✓ (flickering_reach regression), **AC3 ✓ (cliché audit PASS, 0 blockers)**, AC4 ✓ (content resolves against catalog), AC5 ✓ (≥17 regions + graph integrity; 17-vs-18 reconciliation flagged to GM).

**Branches (pushed):**
- `sidequest-server`: `feat/103-10-103-10-seaboard-e2e-wiring-regression`
- `sidequest-content`: `feat/103-10-103-10-seaboard-e2e-wiring-regression`

**Handoff:** To Reviewer (Westley). Note for review: run server tests with `SIDEQUEST_TEST_DATABASE_URL` exported or the marquee proof skips; the 17-vs-18 region count and the 3 deferred cliché-polish items are GM-lane non-blocking follow-ups (logged in Delivery Findings).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `seaboard_of_saints` is `draft: true`, and `load_genre_pack` silently skips draft worlds (`loader._load_single_world` returns None on `config.draft`) — so the production pack-load path validates NONE of the world's saints.yaml / stocks.yaml / cartography while it stays draft. The only guard today is the new `test_103_10_seaboard_e2e.py` (which drives the loaders directly). Affects `sidequest/genre/loader.py` + the world's content — when 103-9 lifts `draft: true`, add an assertion that `seaboard_of_saints in pack.worlds` and that the full world load is error-free; consider a CI guard that validates draft-world content so a broken ref isn't masked until the asset gate. *Found by TEA during test design.*
- **Question** (non-blocking): content ships **18** regions in `cartography.yaml`; world design spec §3 (and the DoD §4) say **"17 regions."** The new region test asserts the DoD floor (`>= 17`), but the 17-vs-18 mismatch should be reconciled — is the 18th region (the roster: adirondacks, baltimore, boston_common, cape_ann, catskills, dc, down_east, hudson_valley, merrimack_mills, outer_boroughs, philadelphia, pioneer_valley, plymouth_stone, providence, salem_country, sunken_bight, whalecoast, white_mountains) intentional, or should spec/DoD be corrected to 18? Affects `genre_packs/mutant_wasteland/worlds/seaboard_of_saints/cartography.yaml` (GM lane). *Found by TEA during test design.*
- **Gap** (blocking for DoD completeness): AC3 — the `cliche-judge` audit over the shipped Seaboard content (spec §11 bans) — is an agent-judgment task with no server-side pytest harness, so it is NOT encoded in the test file. It must be run as a content-lane action during GREEN/review (the `cliche-judge` subagent over `worlds/seaboard_of_saints/*`), and the result recorded, before the story closes. Affects `genre_packs/mutant_wasteland/worlds/seaboard_of_saints/` (content). *Found by TEA during test design.*
- **Improvement** (non-blocking): the epic's wiring was already complete (103-1/103-2 engine + 103-4/103-8 content all merged), so the new e2e/regression tests PASS on authoring — they prove and guard the wiring rather than drive new code. There is no production code for Dev to write for GREEN; GREEN is confirmatory (re-run the suite) plus the AC3 cliché pass and the AC5 region reconciliation above. *Found by TEA during test design.*

### Dev (implementation)
- **AC3 RESOLVED** (non-blocking): ran the `cliche-judge` subagent over `worlds/seaboard_of_saints/*` (saints, stocks, cartography, lore, history, tropes, archetypes, bestiary, items, inventory, openings, cultures). **Verdict: PASS — zero blocking clichés.** The world systematically operates below a 40-year veteran's granularity threshold (real Acushnet/Father Mapple, Putnam-Porter spectral-evidence feud, real Penobscot/Wampanoag uplift lexemes). AC3 is satisfied. *Found by Dev during implementation.*
- **Improvement** (non-blocking, GM lane): cliché audit flagged 1 objective fix (done) + 3 low polish items deferred to the writer/GM (inventing flavor names is out of the engine lane): (a) **DONE** — `bestiary.yaml` Handcar Wrecker `role:` used the §11-banned word "raider"; fixed to "looter". (b) the four Ancient artifact NAMES in `items.yaml` ("Growth Wand", "Ancient Screen", "Screaming Purifier", "Mystery Compass") still sit at the generic Gamma-World loot register though their lore was de-genericized — the one spot the generic floor reaches the player; rename to the Seaboard antiquarian register (keep stable ids). (c) `band_stand_brass_bot` is named slightly differently in `bestiary.yaml` vs `stocks.yaml` and leans on the generic "-bot" suffix; anchor to a specific resort house-band. (d) "The Vault" (`bestiary.yaml` vault_factor) reads as coinage unless a one-line lore nod confirms it's the real 1950s-70s Boston-finance "Vault" deep-cut. Affects `genre_packs/mutant_wasteland/worlds/seaboard_of_saints/{items,bestiary,stocks}.yaml`. *Found by Dev during implementation.*
- **Note** (non-blocking): the marquee PG test (`test_saint_marked_drawback_lives_through_confrontation_and_save`) uses the standard `migrated_db` fixture, which SKIPS with a clear reason when `SIDEQUEST_TEST_DATABASE_URL` is unset (same gate as `test_mutation_wiring`). It PASSES when that env var is exported (verified). Reviewer/CI must run with `SIDEQUEST_TEST_DATABASE_URL` set or the capstone proof silently skips. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **One representative per stock branch-class instead of all 23 stocks**
  - Spec source: build plan §4 DoD / story title — "integration test per stock"
  - Spec text: "integration test per stock: chargen → ... → save cycle"
  - Implementation: parametrized coverage across the branch-classes (Saint-Marked, Animal=harbor_seal, Sleeper, Wild) rather than all 23 roster entries; Plant/Synthetic share Animal's generic engine (build plan D-B), so the animal case proves the shared path.
  - Rationale: P2-4 discipline — assert WIRING (the generic stock-application path fires per branch-class), not content breadth (23 near-identical entries). The full roster's id resolution is covered by `test_stocks_registry_loads_and_every_id_resolves`.
  - Severity: minor
  - Forward impact: if a future stock adds a net-new engine path (not the generic apply), it needs its own integration case.
- **Marquee test grants a catalog Strain-costed positive for the use-fire rather than relying on the Saint's bundle being usable**
  - Spec source: build plan §4 DoD — "confrontation where the Saint drawback/stock trait mechanically fires (OTEL-asserted)"
  - Spec text: "Saint drawback/stock trait mechanically fires"
  - Implementation: AWN negatives are passive penalties (no usage/strain — `use_ops` refuses non-positives), so the drawback "fires" by being OTEL-recorded at chargen + carried in `negative_ids` + surfaced in `build_mutation_static_block`; the *bundle* (the usable half) fires `use_mutation` in combat, and the test grants a known Strain-costed catalog positive to the Saint-Marked PC to drive that path deterministically.
  - Rationale: a robust assertion that does not depend on whether a specific Saint's bundle happens to contain a usable mark (content can change); proves a Saint-Marked PC participates in the live mutation-use path.
  - Severity: minor
  - Forward impact: none — if a "usable negative" mechanic is ever added, the drawback-fire assertion can tighten to use it.
- **No lang-review rule-enforcement tests written**
  - Spec source: TEA agent definition — Phase B (rule-enforcement tests per `.pennyfarthing/gates/lang-review/python.md`)
  - Spec text: "For each applicable rule in the lang-review checklist, write at least one test that would catch a violation."
  - Implementation: none — 103-10 adds no production types/constructors/handlers; it is an integration/regression proof over already-shipped code (the engine + content landed in 103-1..103-8).
  - Rationale: the lang-review rules target production-code design (validated constructors, non_exhaustive enums, tenant context, etc.); there is no new production surface in this story for them to apply to.
  - Severity: minor
  - Forward impact: if Dev writes production code in GREEN (e.g., a draft-world validation guard per the Delivery Findings), the applicable rules must get coverage then.

### Dev (implementation)
- No deviations from spec. No production code was required — the epic's engine (103-1/103-2) and content (103-4..103-8) shipped already, so GREEN was confirmatory. The single content edit (the `raider` ban-word) is an audit-driven correction, not a spec deviation; the subjective cliché-polish items are deferred to the GM lane (writer judgment on flavor names) as non-blocking findings below.

### Reviewer (review)
- No spec deviations introduced. The Reviewer applied one **pure-formatting** fixup (committed `28dd4861`): `ruff format` collapsed a two-line assert message that now fits the line limit onto one line — zero semantic change, verified via `--diff` before applying and all 13 tests re-run green after. Consistent with the project's "approve-with-note on pure reflows" guidance, actioned rather than deferred so the branch merges formatted.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (format) | confirmed 1, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings (domain assessed by Reviewer — see Rule Compliance + Observations) |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings (no production types in diff) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings (no auth/input surface in diff) |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings (rules enumerated by Reviewer below) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents`)
**Total findings:** 1 confirmed (format — RESOLVED by Reviewer), 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict: APPROVE**

The diff is a 534-line server integration-test file + a 1-word content YAML fix. With 8 of 9 subagents disabled via settings, I assessed the relevant domains (test quality, silent-failure, simplicity, rules) myself against the diff.

### Rule Compliance (CLAUDE.md / SOUL.md — server)
- **"No Source-Text Wiring Tests"** (CLAUDE.md) — COMPLIANT. The tests assert behavior via OTEL spans (`awn.saint.applied`/`awn.stock.applied`/`awn.mutation.used`) and fixture-driven state, and load real content via `load_*_registry`/`_load_cartography`. No `read_text()` source-grep anywhere. Exemplary use of the sanctioned patterns (OTEL span assertions + fixture-driven behavior).
- **"Every Test Suite Needs a Wiring Test"** — COMPLIANT. This file IS the epic's wiring test; the marquee drives the real `_apply_narration_result_to_snapshot` apply path + PG round-trip.
- **"No Silent Fallbacks"** — COMPLIANT and *enforced* by `test_unresolvable_mutation_reference_fails_loud`, which proves the loader raises (not silently drops) on an unresolvable granted id.
- **OTEL Observability Principle** — COMPLIANT. Every chargen/confrontation assertion is a span assertion, the project's prescribed lie-detector.
- **Content "No Silent Fallbacks" / §11 cliché bans** — the 1-word bestiary fix removes a self-contradiction (a role string used the world's own banned word "raider"); preflight confirmed no banned word remains in any name/role field (remaining hits are comment text).

### Observations (≥5)
1. **[TEST] Assertions are meaningful, none vacuous** — every test asserts on a concrete value or a named span + its attributes (saint_id, drawback, granted_count, strain delta, persisted ids). No `assert True`, no `let _ =`-equivalent, no `is_none()` on always-None. VERIFIED good.
2. **[TEST] `otel_capture` is function-scoped** — so the *negative* assertions in `test_flickering_reach_wild_mutant_chargen_seeds_clean` ("no saint/stock span fired") are valid and not polluted by sibling tests. VERIFIED good.
3. **[TEST] The draft-skip test is an intentional tripwire, not a bug-lock** — `test_draft_world_is_skipped_by_pack_load` asserts current behavior and its message instructs the future dev to flip it when 103-9 lifts `draft:true`. Acceptable; it guards the rationale the rest of the file depends on.
4. **[TEST] Marquee PG test skips without `SIDEQUEST_TEST_DATABASE_URL`** — LOW. This is the established `migrated_db` contract (identical to `test_mutation_wiring.py`), so it's consistent with the codebase, not a new flaw. Risk: in a runner that doesn't export the TEST url the capstone proof silently skips. Mitigation already documented in Dev findings; non-blocking. Confirmed it PASSES with the var set (preflight ran it green, not skipped).
5. **[SIMPLE] 534 lines / 13 tests is long but justified** — integration tests need full pack-load + character + confrontation + PG scaffolding; helpers (`_load_pack`, `_seaboard_pc`, `_pg_store_with`) are factored, not duplicated. No dead code. VERIFIED good.
6. **[DOC] Docstrings are accurate and load-bearing** — they record the draft trap, the passive-negative drawback mechanism, and the 17-vs-18 discrepancy honestly. No stale/misleading comments.
7. **[SEC] No security surface** — test code + content flavor YAML; no auth, input parsing, or tenant boundary touched. N/A.

### Resolved during review
- **[PREFLIGHT] ruff format divergence** — CONFIRMED then RESOLVED by Reviewer (pure reflow, committed `28dd4861`, tests re-verified green).

### Non-blocking follow-ups (already logged, correctly routed to GM lane)
- 17-vs-18 region reconciliation (test asserts the DoD floor `>=17`; correctness is a GM content decision).
- 3 cliché-polish items (artifact names, brass-bot naming, "The Vault" sourcing) — writer judgment, outside the engine lane.
- Draft-world CI validation gap — a sound future hardening, not in this story's scope.

**Quality gate:** lint clean, format clean (post-fixup), 13/13 tests green, full integration+mutation suite 498 passed / 0 failed / 18 baseline-skipped, content YAML parses. AC1/AC2/AC3/AC4/AC5 all satisfied.

**Handoff:** To SM (Vizzini) for finish — create + merge the server and content PRs to develop.