---
story_id: "13-12"
jira_key: "none"
epic: "13"
workflow: "tdd"
---

# Story 13-12: Initiative stat mapping — genre pack schema + caverns authoring

## Story Details

- **ID:** 13-12
- **Jira Key:** none (personal project)
- **Epic:** 13 — Sealed Letter Turn System
- **Workflow:** tdd (phased: setup → red → green → spec-check → verify → review → spec-reconcile → finish)
- **Points:** 3
- **Priority:** p0
- **Repos:** sidequest-api, sidequest-content
- **Branch:** feat/13-12-initiative-stat-mapping
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-10T11:07:28Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-10T14:30:00Z | 2026-04-10T11:02:27Z | -12453s |
| red | 2026-04-10T11:02:27Z | - | - |

## Delivery Findings

### TEA (test design)

- **Conflict** (blocking): Story 13-12 is already complete on develop in both repos. Affects `sprint/epic-13.yaml` (story status must be reconciled from `backlog` to done/complete) and `.session/13-12-session.md` (session should be archived, not worked). *Found by TEA during test design.*

  **Evidence (four proofs):**
  1. `cargo test --test initiative_rules_story_13_12_tests` — **11 passed, 0 failed**. The tests are GREEN on a fresh feature branch cut from develop.
  2. `InitiativeRule` struct exists at `crates/sidequest-genre/src/models/rules.rs:16` and the `initiative_rules: HashMap<String, InitiativeRule>` field is at line 443.
  3. `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml:58` contains the `initiative_rules:` block.
  4. [slabgorb/sidequest-api#377](https://github.com/slabgorb/sidequest-api/pull/377) "feat(13-12): initiative stat mapping schema + validation" was **MERGED to develop at 2026-04-09T18:30:34Z** (yesterday).
  5. Both feature branches (`feat/13-12-initiative-stat-mapping` in sidequest-api and sidequest-content) have **zero commits ahead of develop** — `git diff develop --stat` is empty in both.

  **Root cause:** OQ-1 and OQ-2 are two machines doing parallel sprint work. Story 13-12 was implemented and merged on OQ-1 (or an earlier session) yesterday, but the sprint YAML on this machine/branch was never updated. This is the same failure mode that produced the 27-9 zombie branches earlier today — stale sprint metadata diverged from actual git state.

- **Improvement** (non-blocking): The test file at `crates/sidequest-genre/tests/initiative_rules_story_13_12_tests.rs:16` has an `unused import: std::collections::HashMap` warning that `cargo test` surfaces. Commit `2581c29 refactor: remove unused import from 13-12 tests` appears to have addressed unused imports but this one survived — either a sibling import was removed and `HashMap` was missed, or the commit hasn't yet reached develop. Candidate for a cleanup chore. Affects `sidequest-api/crates/sidequest-genre/tests/initiative_rules_story_13_12_tests.rs` (remove the stray import). *Found by TEA during test design.*

## Design Deviations

### TEA (test design)
- No deviations from spec. No test design occurred because the story's implementation already exists on develop and the test suite was already written, merged, and is GREEN.

## Story Goal

Add initiative stat mapping to the genre pack schema. Initiative rules map encounter types (combat, chase, social, exploration) to primary ability scores. This enables the sealed-letter turn system (Epic 13) to order actions based on character stats. The schema lives in `rules.yaml` under `initiative_rules`, with a companion struct `InitiativeRule` in the Rust codebase.

## Acceptance Criteria

### AC-1: InitiativeRule struct defined
- Type name: `InitiativeRule`
- Fields: `primary_stat` (String) and `description` (String)
- Both fields required (no Option)
- Must be deserializable from YAML via serde

### AC-2: RulesConfig has initiative_rules field
- New field: `initiative_rules: HashMap<String, InitiativeRule>`
- Defaults to empty HashMap when absent from YAML
- Keyed by encounter type identifier (e.g., "combat", "social", "chase", "exploration")

### AC-3: Caverns_and_claudes authored
- caverns_and_claudes/rules.yaml contains `initiative_rules` block
- Defines 4 encounter types: combat, chase, social, exploration
- Each maps to valid ability score from ability_score_names (STR/DEX/CON/INT/WIS/CHA)
- Example mapping:
  - combat → DEX (reflexes/speed)
  - chase → DEX (agility)
  - social → CHA (personality)
  - exploration → WIS (awareness)

### AC-4: Validation enforced
- InitiativeRule stat names must exist in genre's ability_score_names
- Validation runs during GenreLoader initialization
- Invalid rules fail loudly (no silent fallback)

### AC-5: Loader wiring verified
- GenreLoader reads initiative_rules from rules.yaml
- Full roundtrip test: genre pack → RulesConfig → InitiativeRule
- Wiring test loads real caverns_and_claudes pack and validates

## Implementation Context

### Current State

**Test Suite Location:**
- `/sidequest-api/crates/sidequest-genre/tests/initiative_rules_story_13_12_tests.rs` (written, currently RED)
- 11 test cases covering all acceptance criteria
- Tests fail because InitiativeRule type doesn't exist yet

**What's Needed:**

1. **sidequest-genre crate:**
   - Add `InitiativeRule` struct to models.rs (or separate file if needed)
   - Add `initiative_rules: HashMap<String, InitiativeRule>` to RulesConfig struct
   - Ensure serde attributes handle defaults and deny_unknown_fields

2. **sidequest-content/caverns_and_claudes:**
   - Add `initiative_rules` section to rules.yaml
   - Define 4 encounter types with valid stats and descriptions

3. **Validation:**
   - Extend RulesConfig::validate() to check initiative rule stats against ability_score_names
   - Fail at load time if invalid

### Key References

- Test file: `/sidequest-api/crates/sidequest-genre/tests/initiative_rules_story_13_12_tests.rs`
- RulesConfig location: `sidequest-api/crates/sidequest-genre/src/models.rs`
- Genre loader: `sidequest-api/crates/sidequest-genre/src/loader.rs`
- Caverns rules: `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`

### Test Strategy (RED phase)

The test suite is already written. RED phase simply runs tests to confirm they fail with "InitiativeRule not found":

```bash
cd /Users/keithavery/Projects/oq-2/sidequest-api
cargo test --test initiative_rules_story_13_12_tests 2>&1
```

Expected failures:
1. `error[E0433]: cannot find type 'InitiativeRule' in this scope`
2. `error[E0425]: cannot find value 'InitiativeRule' in this scope`

### GREEN Phase Checklist

1. Define InitiativeRule struct in models.rs
   - pub struct InitiativeRule with #[derive(Debug, Serialize, Deserialize)]
   - pub primary_stat: String
   - pub description: String
   - No Option types (fields are required)

2. Add initiative_rules to RulesConfig
   - pub initiative_rules: HashMap<String, InitiativeRule>
   - #[serde(default)] to allow omission in YAML

3. Export from module lib.rs
   - pub use types::InitiativeRule

4. Extend validation in RulesConfig
   - validate_initiative_rules() method
   - Check each rule's primary_stat is in ability_score_names
   - Called during load (not optional)

5. Author caverns_and_claudes/rules.yaml
   - Add initiative_rules block after ability_score_names
   - 4 entries: combat, chase, social, exploration
   - Test will verify via loader integration test

6. Run tests to confirm GREEN
   ```bash
   cargo test --test initiative_rules_story_13_12_tests --lib
   ```

### Wiring Verification

This is an add-only feature (no breaking changes):
- InitiativeRule is new type (no migrations)
- initiative_rules defaults to empty HashMap (backward compat)
- Validation is additive (no existing code breaks)
- No changes to dispatch, state, or protocol

Protocol impact: None (initiative rules are genre metadata, not game state).
Server wiring: None (not used in this story — future story 13-13 wires it to turn ordering).

### Risks / Questions

- **Q:** Should we validate during GenreLoader.load_genre_pack() or later?
  **A:** During load — fail early, no silent fallbacks per CLAUDE.md.

- **Q:** What if a genre has no initiative_rules? Is that OK?
  **A:** Yes. Defaults to empty HashMap. Not required until a story uses it.

- **Q:** Is "primary_stat" the right field name, or should it be "ability_score"?
  **A:** Use "primary_stat" per test YAML (already written, matches convention).

## Files to Create/Modify

### sidequest-api

- `crates/sidequest-genre/src/models.rs` — Add InitiativeRule struct
- `crates/sidequest-genre/src/lib.rs` — Export InitiativeRule
- `crates/sidequest-genre/src/validate.rs` — Add validation logic
- Tests already exist at `crates/sidequest-genre/tests/initiative_rules_story_13_12_tests.rs`

### sidequest-content

- `genre_packs/caverns_and_claudes/rules.yaml` — Add initiative_rules block

## Exit Criteria (For TEA/Dev)

- All 11 tests in initiative_rules_story_13_12_tests.rs pass
- `cargo test --lib` passes with no warnings
- `cargo clippy` passes
- caverns_and_claudes loads successfully with new rules
- Validation test confirms invalid stats fail loudly

## Sm Assessment

**Scope fit:** Clean 3-pt add-only feature. Two repos, one new struct, one YAML addition, one validation hook. No protocol changes, no migrations, no wiring into server dispatch. This is as isolated as TDD work gets — the blast radius is the genre crate plus one pack's `rules.yaml`.

**Setup verification:**
- Session file created with full ACs, implementation notes, and file list.
- Feature branch `feat/13-12-initiative-stat-mapping` created in both `sidequest-api` and `sidequest-content` off `develop`.
- Sprint YAML (`epic-13.yaml`) updated with assignee and branch tracking.
- No blocking open PRs anywhere (merge gate verified clean before setup).

**Flag for TEA:** The RED test suite is reportedly already on disk at `sidequest-api/crates/sidequest-genre/tests/initiative_rules_story_13_12_tests.rs` (11 cases). This is unusual for a story coming off the backlog — for a brand-new TDD story, RED is normally TEA's first action. Three possibilities, in order of likelihood:
1. Tests were pre-written in an earlier scouting / planning session and left behind unpushed → verify they're on `develop` not `main`, and that they match the ACs in this session file.
2. Tests were written on `main` by a parallel session → branch should have picked them up through `develop`.
3. A stale leftover from an abandoned attempt → delete and rewrite if they don't align with the ACs.

TEA should run `cargo test --test initiative_rules_story_13_12_tests` on the new branch to verify they're genuinely RED with the expected compile errors (`cannot find type InitiativeRule`), and cross-check the test ACs against the session file ACs. If they diverge, trust the session file and rewrite; the ACs are the contract.

**Wiring scope for this story:** Intentionally narrow. This story defines the schema and authors one genre. Consumption (turn ordering in sealed-letter) is story 13-13. Per CLAUDE.md "every test suite needs a wiring test" — the loader roundtrip (AC-5) is the wiring test; it proves the struct is reachable from `GenreLoader::load_genre_pack()` in production code path, not just in isolation.

**Routing:** Phased TDD workflow, next agent is TEA (Mr. Praline) for RED phase verification. No design deviations, no blockers.

---

## TEA Assessment

**Tests Required:** No — **phase is moot**
**Reason:** Story 13-12 is already complete on develop. The implementation, the test suite, and the caverns_and_claudes authoring were all shipped yesterday via PR slabgorb/sidequest-api#377 (merged 2026-04-09T18:30:34Z). Both feature branches created by SM setup have zero commits ahead of develop — they are pure zombies. There is no RED phase to execute because the test suite is already GREEN (11/11 passing) on the branch as-inherited-from-develop.

**Test Files:** Pre-existing (not written by this TEA session)
- `sidequest-api/crates/sidequest-genre/tests/initiative_rules_story_13_12_tests.rs` — 11 test cases, GREEN, already on develop

**Tests Written:** 0 new tests
**Status:** Cannot establish RED — test suite is already passing against an already-implemented feature

### Rule Coverage

Rule coverage analysis was not performed because no new tests were written. The pre-existing suite covers the ACs from the story context reasonably well:

| AC | Pre-existing test | Status |
|----|------|--------|
| AC-1: InitiativeRule struct defined | `initiative_rule_deserializes_from_yaml`, `initiative_rule_requires_primary_stat`, `initiative_rule_requires_description` | passing |
| AC-2: RulesConfig has initiative_rules field | `rules_config_parses_initiative_rules`, `rules_config_initiative_rules_empty_when_absent` | passing |
| AC-3: Caverns_and_claudes authored | `caverns_initiative_rules_has_required_encounter_types`, `loader_reads_initiative_rules_from_caverns` | passing |
| AC-4: Validation enforced | `validation_rejects_invalid_initiative_stat` | passing (note: test only asserts the rule parsed with the invalid stat; does not assert loud validation failure — this is a mild coverage gap but not a blocker since the story is already shipped) |
| AC-5: Loader wiring verified | `loader_reads_initiative_rules_from_caverns` | passing |

**Self-check:** One minor observation in `validation_rejects_invalid_initiative_stat` — the test parses a rule with an invalid stat (`REFLEXES` not in `ability_score_names`) and asserts the parse succeeded, but it does NOT assert that `GenrePack` validation rejects the pack at load time. The test comment acknowledges this ("For now, verify the rules parsed — the validation test below uses the real loader") but the "test below" (`loader_reads_initiative_rules_from_caverns`) tests the GREEN path against caverns, not a negative-validation path against an invalid genre. So strictly speaking AC-4 (validation fails loudly) is not directly exercised by a failing-pack test. **This is a coverage gap worth noting for a future cleanup story** but is not blocking — the story is already merged.

**Handoff:** **Back to SM (The Announcer)** — not Dev. There is no implementation work to do. SM needs to reconcile sprint state:

### Recommended SM Actions

1. **Reconcile sprint YAML:** Move story 13-12 from `backlog` → `done` (or whatever the terminal state is called) in `sprint/epic-13.yaml`. Record `merged_at: 2026-04-09T18:30:34Z` and `pr: slabgorb/sidequest-api#377`.
2. **Archive session:** Move `.session/13-12-session.md` to `sprint/archive/` as part of `pf sprint story finish 13-12`.
3. **Delete zombie feature branches:**
   - `git -C sidequest-api branch -d feat/13-12-initiative-stat-mapping` (will succeed with `-d` since zero diff from develop)
   - `git -C sidequest-content branch -d feat/13-12-initiative-stat-mapping` (same)
4. **Optional — diagnostic action:** Consider adding a pre-setup check to sm-setup that runs `git log --oneline develop -- <story-related-paths>` to detect stories whose implementation already landed. This would have caught both 27-9 and 13-12 before branches were created. (Follow-up story candidate — not in scope here.)
5. **Optional — cleanup follow-up:** File a chore to remove the `use std::collections::HashMap;` unused-import warning in `initiative_rules_story_13_12_tests.rs:16`. Trivial, but it's a clippy/cargo warning on develop right now.

### Phase Transition

I am NOT running the standard `red → green` phase transition because:
- No tests were written (phase work is vacuous)
- The gate likely fails since there's no test commit to validate
- Routing to Dev would be wrong — there's no implementation work to do

Instead, I am emitting a handoff marker directly back to **SM** so the Announcer can run the reconciliation flow. SM should treat this as a "finish" case (story is merged) rather than a "continue" case.