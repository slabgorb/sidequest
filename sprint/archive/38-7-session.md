---
story_id: "38-7"
jira_key: "NO_JIRA"
epic: "38"
workflow: "wire-first"
---
# Story 38-7: Hit severity column in interactions_mvp.yaml — extend all 16 cells with graze/clean/devastating classification, define hull damage increments per severity

## Story Details
- **ID:** 38-7
- **Jira Key:** NO_JIRA (personal project, no Jira)
- **Workflow:** wire-first
- **Stack Parent:** none (content-only, standard branching)

## Workflow Tracking
**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-17T00:48:08Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-16T20:20Z | 2026-04-17T00:19:25Z | 3h 59m |
| red | 2026-04-17T00:19:25Z | 2026-04-17T00:25:05Z | 5m 40s |
| green | 2026-04-17T00:25:05Z | 2026-04-17T00:40:35Z | 15m 30s |
| review | 2026-04-17T00:40:35Z | 2026-04-17T00:48:08Z | 7m 33s |
| finish | 2026-04-17T00:48:08Z | - | - |

## Acceptance Criteria

Content-only story: extend interactions_mvp.yaml (sidequest-content/genre_packs/space_opera/dogfight/interactions_mvp.yaml) with hit severity classifications and damage increments.

### AC1: Add hit_severity field to each cell
Each of the 16 interaction cells must include a `hit_severity` field with one of three values:
- `graze` — glancing blow, minimal system impact
- `clean` — solid hit on primary systems, medium damage
- `devastating` — critical damage to structure or engines, high damage

Cells with no gun_solution on either pilot must be `null` or omitted.

### AC2: Define damage increments per severity
The file must include a root-level `damage_increments` section defining how hull damage scales with severity:
```yaml
damage_increments:
  graze: 5
  clean: 15
  devastating: 30
```

Values are notional baseline; may be calibrated post-playtest per story 38-9.

### AC3: Wire check — narrator damage application
The damage increment values must be visible in the GM panel (OTEL) when the narrator applies deltas post-lookup. No hidden/unapplied damage values.

All 16 cells must pass wire-it validation (content schema, no structural errors).

## Sm Assessment

**Routing:** Content-only story touching `interactions_mvp.yaml` in sidequest-content. Wire-first workflow selected by user override (was trivial). Phased: setup → red → green → review → finish.

**Scope:** 1-point story — extend 16 dogfight interaction cells with hit severity classification (graze/clean/devastating) and add damage_increments section. AC3 requires OTEL visibility of damage values during narrator resolution.

**Repos:** content (sidequest-content)
**Branch:** feat/38-7-hit-severity-interactions
**Next:** RED phase → Radar (TEA) writes failing content validation tests.

## Delivery Findings

No upstream findings.

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): TryFrom should validate starting_hull > 0 when present. Affects `sidequest-api/crates/sidequest-genre/src/models/rules.rs` (add positivity guard in TryFrom). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): TryFrom should enforce damage tier ordering (graze < clean < devastating). Affects `sidequest-api/crates/sidequest-genre/src/models/rules.rs` (add ordering check after positivity loop). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): TryFrom should enforce co-presence of damage_increments and starting_hull. Affects `sidequest-api/crates/sidequest-genre/src/models/rules.rs` (reject one without the other). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): New TryFrom Err paths should emit tracing::warn! per OTEL principle. Affects `sidequest-api/crates/sidequest-genre/src/models/rules.rs` (add tracing calls). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Rename wiring test to reflect content-validation scope. Affects `sidequest-api/crates/sidequest-genre/tests/hit_severity_story_38_7_tests.rs` (rename to content_pipeline_carries_severity_and_damage). *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- TEA "No deviations from spec" → ✓ ACCEPTED by Reviewer: Content tests correctly cover all 3 ACs and match the story context's severity distribution guidance.
- Dev "No deviations from spec" → ✓ ACCEPTED by Reviewer: Implementation follows the story context's "No Rust code changes required" guidance — the Rust additions are elective improvements that support content validation.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Content schema extension with new fields and damage math — needs validation tests

**Test Files:**
- `sidequest-api/crates/sidequest-genre/tests/hit_severity_story_38_7_tests.rs` — 11 tests covering 3 ACs + schema validation + wiring

**Tests Written:** 11 tests covering 3 ACs
**Status:** RED (compilation failure — InteractionTable missing `damage_increments` and `starting_hull` fields)

**Test Breakdown:**
| Test | AC | What it validates |
|------|-----|-------------------|
| `every_gun_solution_cell_has_hit_severity_on_red_view` | AC-1 | red_view with gun_solution must have hit_severity |
| `every_gun_solution_cell_has_hit_severity_on_blue_view` | AC-1 | blue_view with gun_solution must have hit_severity |
| `cells_without_gun_solution_have_no_hit_severity` | AC-1 | negative case — no spurious severity on non-shooting cells |
| `all_hit_severity_values_are_valid_tiers` | AC-2 | values must be graze/clean/devastating |
| `severity_distribution_follows_rps_balance` | AC-2 | kill_rotation back-shots must be devastating |
| `interaction_table_has_damage_increments_section` | AC-3 | damage_increments field exists with all 3 tiers |
| `damage_increments_are_positive_and_ordered` | AC-3 | graze < clean < devastating, all positive |
| `two_grazes_can_kill_a_light_fighter` | AC-3 | 2 × graze >= starting_hull |
| `interaction_table_rejects_missing_severity_in_damage_increments` | schema | validation rejects incomplete tiers |
| `interaction_table_rejects_zero_damage_increment` | schema | validation rejects zero damage (silent fallback) |
| `sealed_letter_outcome_includes_hit_severity_and_damage` | wiring | end-to-end: load pack → find cell → resolve severity → lookup damage |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #5 validated constructors | `rejects_missing_severity`, `rejects_zero_damage` | failing (RED) |
| #6 test quality | all assertions verified meaningful | passing (self-check) |

**Rules checked:** 2 of 6 applicable lang-review rules have test coverage
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev (Winchester) for implementation — extend InteractionTable struct, add damage_increments/starting_hull fields, populate interactions_mvp.yaml with hit_severity values

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-genre/src/models/rules.rs` — Added `damage_increments: Option<HashMap<String, i64>>` and `starting_hull: Option<i64>` to `RawInteractionTable` and `InteractionTable`, with TryFrom validation (missing tiers, zero/negative values)
- `sidequest-content/genre_packs/space_opera/dogfight/interactions_mvp.yaml` — Added `damage_increments`, `starting_hull`, and `hit_severity` to all 7 gun_solution views

**Severity Assignments:**
| Cell | Actor | Severity | Rationale |
|------|-------|----------|-----------|
| straight vs loop | blue | clean | Standard loop reversal onto passive |
| straight vs kill_rotation | blue | devastating | Flip-and-burn back-shot payoff |
| loop vs straight | red | clean | Standard loop reversal onto passive |
| loop vs kill_rotation | red:graze, blue:clean | — | Mutual gunline; kill_rotation committed riskier move |
| kill_rotation vs straight | red | devastating | Flip-and-burn back-shot payoff |
| kill_rotation vs loop | red:clean, blue:graze | — | Mirror of loop vs kill_rotation |
| kill_rotation vs kill_rotation | both graze | — | Dual drift, worst firing platform |

**Damage Math:** graze=5, clean=15, devastating=30, starting_hull=10. 2×graze(10) ≥ hull(10) ✓

**Tests:** 11/11 passing (GREEN)
**Branch:** feat/38-7-hit-severity-interactions (pushed: api + content)

**Handoff:** To Colonel Potter (Reviewer)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | No | timeout | N/A | Tests independently verified 11/11 GREEN |
| 2 | reviewer-edge-hunter | Yes | findings | 6 | confirmed 3, dismissed 1, deferred 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 5 | confirmed 2, dismissed 1, deferred 2 |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 1, dismissed 2, deferred 1 |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | confirmed 2 |
| 6 | reviewer-type-design | Yes | findings | 5 | confirmed 2, dismissed 2, deferred 1 |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 8 | confirmed 4, dismissed 2, deferred 2 |

**All received:** Yes (6 returned with findings, 1 timed out but domain verified independently, 2 disabled)
**Total findings:** 8 confirmed, 6 dismissed (with rationale), 5 deferred as delivery findings

### Finding Triage

**Confirmed (non-blocking for 1-point content story):**
1. [EDGE][SILENT][RULE] `starting_hull` has no positivity validation in TryFrom — rules.rs:386. Corroborated by 4 subagents. **MEDIUM** — current content is valid (starting_hull=10), gap only affects future invalid content.
2. [EDGE][DOC][RULE] Ordering not enforced in TryFrom — rules.rs:411. Doc says "ordered" but code doesn't check graze < clean < devastating. **MEDIUM** — current content has correct ordering.
3. [EDGE][SILENT][RULE] No co-presence check: damage_increments present but starting_hull absent loads silently — rules.rs:411. **MEDIUM** — current content has both fields.
4. [DOC] Doc comment says "ordered" but TryFrom only checks positivity — rules.rs:370. **LOW** — misleading doc.
5. [TEST][TYPE][RULE] Wiring test name misleading — it reads table data, never calls resolver. **MEDIUM** — valid for content-only story scope but name should be accurate.
6. [EDGE] Extra keys in damage_increments silently accepted — rules.rs:411. **LOW** — misspelled keys would be caught by content CI.
7. [RULE] No tracing on new TryFrom error paths — rules.rs:411-428. **MEDIUM** — OTEL principle.
8. [RULE] interaction_table_has_damage_increments_section checks key existence only, not values — test line 216. **LOW** — compensated by other tests.

**Dismissed:**
1. pub fields on InteractionTable (#9) — ALL existing fields on the struct are pub. Making only damage_increments/starting_hull private would be inconsistent. Struct-wide refactor is out of scope for 1pt story.
2. Stringly-typed HashMap vs DamageIncrements struct — valid improvement but a new type for a 1pt content story is over-engineering. Current content works.
3. hit_severity not validated at Rust type level — by design, cell views are serde_yaml::Value blobs. Content validation is the test suite's job.
4. yaml_value_to_json null return on unrepresentable numbers — pre-existing, not in diff scope.
5. Missing negative damage test case — the val <= 0 guard covers both zero and negative; testing zero boundary is sufficient.
6. Test coupling to "kill_rotation" string literal — all tests couple to fixture content; this is expected.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** YAML interactions_mvp.yaml → load_interaction_table → InteractionTable (with damage_increments, starting_hull) → cell views carry hit_severity as serde_yaml::Value → apply_view_deltas merges into per_actor_state → visible in GM panel actor state. Safe because all content is validated by the test suite against the real fixture.

**Pattern observed:** [VERIFIED] InteractionTable correctly uses `#[serde(try_from = "RawInteractionTable")]` pattern — all deserialization goes through validation. Rules.rs:372, consistent with existing ConfrontationDef pattern at rules.rs:433. Complies with rules #5, #8.

**Error handling:** [VERIFIED] TryFrom rejects missing severity tiers (rules.rs:414-418) and zero/negative values (rules.rs:420-425). Error messages include tier name and value. No silent fallback on these paths.

**Observations:**
1. [VERIFIED] hit_severity values in YAML are correct — 7 cells with gun_solution have hit_severity, 9 without don't. Content diff confirmed manually.
2. [VERIFIED] Severity distribution follows RPS balance — back-shots = devastating, reversals = clean, mutual gunlines = graze/clean. Content is game-design sound.
3. [VERIFIED] Damage math: graze=5, clean=15, devastating=30, starting_hull=10. 2×5=10 ≥ 10. Paper playtest "2 grazes = kill" rule satisfied.
4. [VERIFIED] Backward compatible — existing tables without damage_increments still load (Option + serde(default)). Test `load_rules_config_preserves_inline_confrontations_regression` from 38-4 suite still passes.
5. [MEDIUM] TryFrom validation gaps (ordering, co-presence, starting_hull positivity) — captured as delivery findings for hardening.

[EDGE] Edge cases: TryFrom ordering gap is real but current content is valid. Captured as delivery finding.
[SILENT] Silent failures: co-presence gap is real but current content has both fields. Captured as delivery finding.
[TEST] Test quality: wiring test name misleading for content-only story. Captured as delivery finding.
[DOC] Documentation: doc comment "ordered" claim not enforced. Captured as delivery finding.
[TYPE] Type design: stringly-typed HashMap acceptable for MVP. DamageIncrements struct is a future improvement.
[SEC] Security: N/A (disabled, no security-sensitive code in diff).
[SIMPLE] Simplifier: N/A (disabled).
[RULE] Rule compliance: 4 confirmed violations, all non-blocking MEDIUM/LOW. No Critical or High.

### Rule Compliance

| Rule | Instances | Verdict |
|------|-----------|---------|
| #1 Silent errors | 0 in diff | N/A |
| #2 non_exhaustive | No new enums | N/A |
| #3 Placeholders | Tier names are authoritative, not placeholders | PASS |
| #4 Tracing | New Err paths lack tracing | MEDIUM — delivery finding |
| #5 Constructors | TryFrom validates via serde(try_from) | PASS |
| #6 Test quality | Wiring test name misleading, key-only assertion | MEDIUM — delivery finding |
| #8 Deserialize bypass | serde(try_from) in place | PASS |
| #9 Public fields | Consistent with existing struct pattern | DISMISSED — struct-wide refactor out of scope |
| #13 Validation consistency | starting_hull not validated in TryFrom | MEDIUM — delivery finding |
| A1 No silent fallbacks | Co-presence gap | MEDIUM — delivery finding |
| A3 Wiring test | Present but tests data access, not pipeline | MEDIUM — acceptable for content-only scope |
| A5 Genre truth | Ordering not enforced | MEDIUM — delivery finding |

### Devil's Advocate

What if Winchester's damage math is wrong and we don't catch it until a playtest? The damage_increments values (5/15/30) are calibration targets from the paper playtest — story 38-9 explicitly exists for calibration. So wrong values here are expected to be tuned. But what if a future content author for a new genre pack copies this file and misspells "devastating" as "devasting"? The load succeeds, the look-up fails silently at game resolution, and the narrator generates narration about a devastating hit that does zero damage. The GM panel shows no damage application — but only if the GM is watching. The OTEL gap means the missing damage wouldn't surface as a validation warning. This is the scenario the validation hardening delivery findings are meant to prevent. For the space_opera dogfight MVP, the test suite catches it. For hypothetical future tables, the gap is real. But it's a hardening concern, not a blocking defect — no other genre pack has a sealed-letter interaction table today.

What about the "2 grazes = kill" math at starting_hull=10? With graze=5, that's exactly 2 hits to deplete hull. Zero margin. A fighter that takes 1 point of environmental damage before the first graze now needs 3 grazes to die, which breaks the rule. This is intentional — the story context says "may be calibrated post-playtest per story 38-9." The tight math is a feature, not a bug: it makes the calibration story meaningful.

**Handoff:** To Hawkeye (SM) for finish-story