---
story_id: "4-2"
jira_key: ""
epic: "4"
workflow: "tdd"
---
# Story 4-2: Subject extraction — parse narration for image render subjects, tier classification

## Story Details
- **ID:** 4-2
- **Epic:** 4 — Media Integration
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p0
- **Stack Parent:** none

## Story Description

Parse narration text to extract subjects for image rendering. Classify subjects into tiers for render priority. This enables the image pipeline to know WHAT to render from narrative text.

**Implementation Target:** `sidequest-api` (Rust)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-26T17:05:52Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-26T16:39:45Z | 2026-03-26T16:46:08Z | 6m 23s |
| red | 2026-03-26T16:46:08Z | - | - |

## Context & References

### Related Architecture
- **sidequest-daemon** `scene/` module — Python scene interpreter (existing reference)
- **sidequest-genre** — Genre pack YAML loader (can be used for tier classification rules)
- **sidequest-protocol** — GameMessage types (will need subject extraction payload)

### Epic 4 Context
Epic 4 covers Media Integration:
1. Daemon client integration (4-1, completed)
2. Subject extraction (4-2, this story)
3. Image render queuing (4-3)
4. TTS voice selection (4-4)

### Testing Strategy (TDD)
This is a TDD workflow story. Tests drive the implementation:
1. **Unit tests** for subject extraction logic (regex patterns, rules)
2. **Parser tests** for classification into render tiers
3. **Integration tests** with sidequest-protocol types

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

No upstream findings yet.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Session implementation notes describe a 3-tier system (Tier1/Tier2/Tier3) but story context defines a 4-tier semantic model (Portrait/Scene/Landscape/Abstract). Tests follow story context. Affects `.session/4-2-session.md` (implementation notes should be updated to match). *Found by TEA during test design.*
- **Question** (non-blocking): The Python daemon's `SubjectExtractor` uses LLM (Claude CLI) for extraction, but story context says "heuristics only for now" with LLM explicitly out of scope. The Rust port is a deliberate simplification. No action needed — just documenting the divergence. *Found by TEA during test design.*
- **Improvement** (non-blocking): Dev left `_entity_patterns: Vec<Regex>` and `_scene_keywords` as dead fields on SubjectExtractor — removed during simplify. Also removed unused `regex` crate dependency. Affects `crates/sidequest-game/src/subject.rs` and `Cargo.toml` (already fixed). *Found by TEA during test verification.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

No deviations yet.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec.

### TEA (test design)
- **Tier classification uses 4-tier model (Portrait/Scene/Landscape/Abstract) instead of session's 3-tier (Tier1/Tier2/Tier3)**
  - Spec source: 4-2-session.md, Implementation Notes > Tier Classification System
  - Spec text: "Tier 1 (Critical), Tier 2 (Important), Tier 3 (Optional)"
  - Implementation: Tests use context-story-4-2.md's SubjectTier enum (Portrait, Scene, Landscape, Abstract) which is semantically richer
  - Rationale: Story context (higher authority) defines the 4-tier model; session implementation notes used a simplified placeholder
  - Severity: minor
  - Forward impact: none — Dev follows the test types

## Implementation Notes

### Tier Classification System
Subjects should be classified by render priority:
- **Tier 1 (Critical):** Main character, primary antagonist, location
- **Tier 2 (Important):** Secondary characters, key objects, environment details
- **Tier 3 (Optional):** Minor details, atmospheric elements

### Parser Input/Output
- **Input:** Narration text (string)
- **Output:** `Vec<Subject>` with fields:
  - `name: String`
  - `tier: RenderTier` (enum: Tier1, Tier2, Tier3)
  - `entity_type: EntityType` (Character, Location, Object, etc.)
  - `confidence: f32` (0.0-1.0)

### Integration Points
- Will be called from sidequest-server when narration is received
- Output feeds into image render queue (4-3)
- Genre pack rules may influence tier classification

## TEA Assessment

**Tests Required:** Yes
**Reason:** Core extraction logic with 10 ACs and multiple heuristic paths

**Test Files:**
- `crates/sidequest-game/tests/subject_extraction_story_4_2_tests.rs` — 37 tests covering all ACs
- `crates/sidequest-game/src/subject.rs` — type stubs with `todo!()` implementations

**Tests Written:** 37 tests covering 10 ACs
**Status:** RED (30 failing — ready for Dev)

**Passing tests (7):** Type construction, validated constructor, getter API, enum variant, default TierRules

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `subject_tier_variants_are_constructible`, `scene_type_variants_are_constructible` | passing (compile-time check) |
| #5 validated constructors | `render_subject_new_rejects_negative_weight`, `render_subject_new_rejects_weight_above_one`, `render_subject_new_accepts_boundary_weights` | passing |
| #9 public fields | `render_subject_accessed_through_getters` | passing |
| #15 unbounded input | `extract_rejects_oversized_narration`, `extract_rejects_empty_narration`, `extract_accepts_narration_at_max_length` | failing (needs impl) |
| #6 test quality | Self-check: all 37 tests have meaningful assertions, no `let _ =` or `assert!(true)` | pass |

**Rules checked:** 5 of 15 Rust lang-review rules applicable and covered
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev (Loki Silvertongue) for implementation

### Verify Phase

**Phase:** finish
**Status:** GREEN confirmed — 37/37 tests passing

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication found |
| simplify-quality | 3 findings | Dead fields (_entity_patterns, _scene_keywords), unused regex import |
| simplify-efficiency | clean | No over-engineering found |

**Applied:** 4 high-confidence fixes (3 dead code removals + 1 clippy fix)
**Flagged for Review:** 0 medium-confidence findings
**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: applied 4 fixes

**Quality Checks:** 37/37 tests passing, 0 clippy warnings in subject.rs
**Regression Check:** All tests pass after simplify commit
**Handoff:** To Heimdall (Reviewer) for code review

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/subject.rs` — Full extraction pipeline: entity matching, scene classification, weight scoring, tier assignment, prompt composition

**Tests:** 37/37 passing (GREEN)
**Branch:** feat/4-2-subject-extraction (pushed)

**Implementation approach:**
- Entity extraction via `String::contains` matching known NPCs, with `recent_subjects` dedup
- Scene classification priority: `in_combat` flag → dialogue (speech verbs + quotes) → discovery keywords → transition phrases → default exploration
- Weight scoring: word count (length/50 capped 0.3) + action words (0.05 each, capped 0.3) + entity count (0.1 each, capped 0.2) + combat boost (0.15)
- Tier: 2+ entities→Scene, 1→Portrait, 0+landscape cues→Landscape, 0+mood cues→Abstract
- Prompt: entity names + location + narration excerpt

**Handoff:** To next phase (review)

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** 1 (pre-existing, already logged by TEA)

- **4-tier vs 3-tier classification model** (Different behavior — Behavioral, Minor)
  - Spec (session implementation notes): "Tier 1 (Critical), Tier 2 (Important), Tier 3 (Optional)"
  - Code: `SubjectTier::Portrait`, `Scene`, `Landscape`, `Abstract` (4 semantic tiers)
  - Recommendation: **A — Update spec** — Story context (higher authority) defines the 4-tier model. Session implementation notes were a simplified placeholder. The semantic model is richer and matches the Python source's composition intent. TEA logged this correctly during test design.

**AC Coverage:** 10/10 acceptance criteria verified against implementation.
**Dead Code:** `_entity_patterns` and `_scene_keywords` fields are unused stubs (Dev logged this). Not a spec issue — cosmetic, appropriate for future genre-specific patterns (4-3).

**Decision:** Proceed to review

## Delivery Findings

### Dev (implementation)
- **Gap** (non-blocking): `_entity_patterns: Vec<Regex>` and `_scene_keywords: HashMap<SceneType, Vec<String>>` fields on SubjectExtractor are unused — extraction uses inline keyword arrays instead. These could be removed or populated if genre-specific patterns are needed later (story 4-3). Affects `crates/sidequest-game/src/subject.rs` (dead fields). *Found by Dev during implementation.*
- **Improvement** (non-blocking): `SceneType` is used as a `HashMap` key type but doesn't derive `Hash + Eq`, which would be needed if `_scene_keywords` is ever populated. Affects `crates/sidequest-game/src/subject.rs` (add derives if field is used). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): `TierRules.minimum_weight` is `pub f32` with no NaN/range validation. Setting it to `f32::NAN` silently disables the weight threshold (NaN comparisons always false). Affects `crates/sidequest-game/src/subject.rs:124` (add validated constructor or `is_finite()` guard). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `assign_tier()` defaults to `SubjectTier::Landscape` for unclassified content with no documentation that this is a catch-all fallback. Future callers (story 4-3) may not expect landscape images for non-landscape narration. Affects `crates/sidequest-game/src/subject.rs:283` (document the default or add a Generic variant). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `classify_scene` dialogue detection uses `narration.contains('\'')` for quote detection, which matches contractions and fantasy names with apostrophes (e.g., "K'than"). Combined with substring-matching speech verbs (e.g., "essays" matches "says"), this increases false positive rate for Dialogue classification. Affects `crates/sidequest-game/src/subject.rs:214` (consider word-boundary matching). *Found by Reviewer during code review.*

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | tests GREEN (377/377), clippy RED (6 warnings in non-subject files), fmt RED (7 files) | confirmed 1 (clippy/fmt are pre-existing, not story 4-2 scope — non-blocking) |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 2 (oversized input silent None, Landscape default fallback), dismissed 1 (compute_weight→RenderSubject::new None path — defense-in-depth, acceptable) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 3 (NaN in TierRules, TierRules missing PartialEq, SubjectExtractor missing Debug), dismissed 1 (ExtractionContext pub fields — intentional DTO pattern, acceptable) |

**All received:** Yes (3 returned, 6 disabled/skipped)
**Total findings:** 5 confirmed, 2 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] `RenderSubject` fields are private with getters — `subject.rs:51-55` fields are all non-pub, getters at lines 82-104. `narrative_weight` invariant (0.0-1.0) protected by validated constructor at line 69. Complies with private-fields-with-getters rule.

2. [VERIFIED] `#[non_exhaustive]` on both public enums — `SubjectTier` at `subject.rs:18` and `SceneType` at `subject.rs:32`. Tests at lines 573-614 verify compilation with wildcard arms. Complies with non_exhaustive rule.

3. [VERIFIED] `RenderSubject::new()` validated constructor correctly rejects NaN — `subject.rs:69` uses `!(0.0..=1.0).contains(&narrative_weight)`. `RangeInclusive::contains` on NaN returns false, negation triggers the guard. Verified via Rust execution. Complies with validated constructor rule.

4. [VERIFIED] No `unwrap()` in production code — all 7 functions in `subject.rs` checked, zero unwrap/expect calls. Test file uses `.unwrap()` extensively (expected). Complies with no-unwrap rule.

5. [VERIFIED] Input boundary validation — `subject.rs:169` rejects empty, whitespace-only, and oversized (>10,000 bytes) narration. `MAX_NARRATION_LENGTH` documented with CWE-674 reference at line 11. Test coverage at lines 703-749. Complies with input validation rule.

6. [MEDIUM] [RULE] `TierRules.minimum_weight` NaN vulnerability — `subject.rs:124` `pub minimum_weight: f32` with no validation. NaN disables the weight threshold silently. Confirmed by both my own Rust execution and rule-checker subagent. Not blocking: TierRules is internal API, not user-facing input; the only constructor path is `TierRules::default()` (hardcoded 0.2) or explicit caller construction. Log as delivery finding for 4-3.

7. [MEDIUM] [SILENT] `assign_tier()` defaults to `Landscape` for unclassified content — `subject.rs:283`. Render queue will request landscape images for non-spatial narration. Heuristic acceptable for initial implementation; document the fallback behavior.

8. [LOW] [RULE] `TierRules` missing `PartialEq` derive — `subject.rs:121`. Plain data struct with one f32 field should derive PartialEq for test ergonomics.

9. [LOW] `SubjectExtractor` missing `Debug` derive — `subject.rs:139`. Contains only `TierRules` which is Debug. Should derive Debug for diagnostics.

10. [VERIFIED] Weight computation is clamped — `subject.rs:253` uses `.clamp(0.0, 1.0)`. All component scores have explicit `.min()` caps (0.3, 0.3, 0.2). No arithmetic overflow or NaN possible from the inputs (integer casts and constants).

### Rule Compliance

| Rule | Instances | Compliant | Violations |
|------|-----------|-----------|------------|
| #[non_exhaustive] on public enums | 2 (SubjectTier, SceneType) | 2 | 0 |
| Validated constructors | 3 (RenderSubject::new, SubjectExtractor::new, with_tier_rules) | 2 | 1 (with_tier_rules accepts NaN TierRules — medium) |
| Private fields with getters | 3 (RenderSubject, ExtractionContext, TierRules) | 1 | 2 (ExtractionContext pub is intentional DTO — dismissed; TierRules pub minimum_weight — medium) |
| No unwrap in prod code | 7 functions | 7 | 0 |
| f32 NaN handling | 4 sites | 3 | 1 (TierRules.minimum_weight — medium) |
| Input validation | 3 boundaries | 3 | 0 |
| No panic paths | 5 functions | 5 | 0 |
| Derive traits | 5 types | 3 | 2 (TierRules missing PartialEq — low; SubjectExtractor missing Debug — low) |

### Data Flow Traced

`narration: &str` → `extract()` length/empty check → entity filtering (known_npcs ∩ narration text, minus recent_subjects) → `classify_scene()` keyword heuristics → `compute_weight()` scoring → threshold check → `assign_tier()` entity count rules → `compose_prompt()` string assembly → `RenderSubject::new()` validated construction → `Option<RenderSubject>` to caller.

**Safe because:** No external I/O, no allocations beyond String clones of known entities, no panic paths, weight clamped to [0.0, 1.0], input bounded at 10KB.

### Wiring

Types re-exported from `lib.rs:44-47`. Not yet consumed by `sidequest-server` — integration is story 4-3 (render queue). No broken wiring.

### Error Handling

All failure paths return `None`: empty input, oversized input, below-weight narration, NaN weight (via RenderSubject::new). No panics. Appropriate for a "maybe render" API where None means "skip this narration."

### Security Analysis

No auth/tenant concerns — this is a pure text-processing function with no I/O, no network, no file access. Input bounded by MAX_NARRATION_LENGTH (CWE-674). No injection surface — output is consumed internally by the render queue, not echoed to users.

### Devil's Advocate

What if this code is broken? Let me attack it.

**Attack 1: Substring matching for speech verbs.** `lower.contains("says")` will match "essays" (e-s-s-a-y-s contains s-a-y-s at positions 2-5). Combined with an apostrophe in a fantasy name like "K'than", the narration "K'than essays a response" would classify as Dialogue. This is a real false positive, but the blast radius is limited — a wrong scene_type means a slightly different image composition, not a crash or data loss. The heuristic approach is documented as intentionally simple (TEA delivery finding notes the Python version uses LLM, this is a deliberate simplification). Severity: low in practice.

**Attack 2: Case-sensitive entity matching.** `narration.contains(npc.as_str())` is case-sensitive. If the LLM narrator writes "GRAK THE DESTROYER" in all caps for dramatic effect, the entity won't be matched. This means a combat scene with the main antagonist could produce an entity-less Landscape render instead of a Portrait. The test suite doesn't cover this case. However, since the LLM narrator is prompted with exact names, case mismatch is unlikely in practice.

**Attack 3: The NaN attack on TierRules.** Already confirmed. If code in story 4-3 constructs `TierRules { minimum_weight: some_config_f32 }` and the config value is NaN (e.g., from a failed parse), every narration produces a render subject, flooding the image queue. This is the most plausible real-world failure. But the fix is straightforward (validate in constructor) and can be done in 4-3 when TierRules becomes configurable.

**Attack 4: Memory exhaustion via entities.** If `known_npcs` has thousands of entries and narration mentions many of them, the entity Vec grows proportionally. But known_npcs is bounded by the game state (typically <50 NPCs), and the narration is bounded at 10KB, so this is not a realistic attack.

**Attack 5: Prompt fragment length.** `compose_prompt` caps the narration excerpt at 120 chars but doesn't cap entity names or location. A location like "The Ancient City of Zul'kharaxathremnopolis..." could produce an oversized prompt. The daemon consuming this would need its own length check. Low severity — internal API.

**Conclusion:** The devil's advocate uncovered no new critical or high issues. The NaN concern (already confirmed medium) is the most actionable. The heuristic weaknesses are acceptable for a v1 implementation that will be refined as the pipeline matures.

### Design Deviation Audit

### Reviewer (audit)
- **Tier classification uses 4-tier model (Portrait/Scene/Landscape/Abstract) instead of session's 3-tier (Tier1/Tier2/Tier3)** → ✓ ACCEPTED by Reviewer: agrees with TEA and Architect reasoning — story context (higher authority) defines 4-tier model, session notes were a placeholder. Implementation is semantically richer and matches Python source intent.
- **Dev (implementation): No deviations** → ✓ ACCEPTED by Reviewer: confirmed, no undocumented deviations found in code review.

### Architect (reconcile)
- **`assign_tier()` uses Landscape as catch-all default for unclassified narration**
  - Spec source: sprint/context/context-story-4-2.md, Technical Approach > Subject Tier Classification
  - Spec text: "Landscape, // Environment focus (entering new area, descriptive passage)"
  - Implementation: `assign_tier()` at `subject.rs:283` returns `SubjectTier::Landscape` when no entities found AND no landscape/abstract keyword cues match. This means non-spatial, non-mood narration (e.g., "The merchant counts his coins") also routes to Landscape.
  - Rationale: Acceptable v1 heuristic — Landscape is the safest visual default (wide shot) for ambiguous narration. The `#[non_exhaustive]` attribute on SubjectTier allows adding a Generic/Fallback variant in a future story without breaking callers.
  - Severity: minor
  - Forward impact: Story 4-3 (render queue) should be aware that Landscape tier includes catch-all narration, not only spatial descriptions. May want to add a Generic variant or tighten keyword matching when render queue applies per-tier budgets.
- No additional deviations found beyond the above.

**Handoff:** To SM for finish-story