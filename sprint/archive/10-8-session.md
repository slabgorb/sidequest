---
story_id: "10-8"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 10-8: Backfill OCEAN profiles on existing NPC archetypes across genre packs

## Story Details
- **ID:** 10-8
- **Title:** Backfill OCEAN profiles on existing NPC archetypes across genre packs
- **Points:** 3
- **Jira Key:** N/A (personal project)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-03-28T19:40:02Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-28 | 2026-03-28T19:21:20Z | 19h 21m |
| implement | 2026-03-28T19:21:20Z | 2026-03-28T19:33:55Z | 12m 35s |
| review | 2026-03-28T19:33:55Z | 2026-03-28T19:40:02Z | 6m 7s |
| finish | 2026-03-28T19:40:02Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): `NpcArchetype` in `sidequest-genre/src/models.rs:580` lacks `#[serde(deny_unknown_fields)]`. A YAML typo like `extroversion` instead of `extraversion` would silently default to 5.0 rather than failing. The genre crate CLAUDE.md states `deny_unknown_fields` is used on key types. Affects `sidequest-api/crates/sidequest-genre/src/models.rs` (add attribute to NpcArchetype and/or OceanProfile). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No undocumented deviations found. Dev's "no deviations" is accurate — the implementation follows the established mutant_wasteland pattern exactly.

## Sm Assessment

**Story:** 10-8 — Backfill OCEAN profiles on existing NPC archetypes
**Workflow:** trivial (setup → implement → review → finish)
**Scope:** Add OCEAN personality profiles to all NPC archetype YAML files across genre packs that don't already have them. Epic 10 established the OCEAN model; this is the backfill pass.
**Repos:** orc-quest (genre_packs YAML only)
**Risk:** Low — data-only changes, no code. Just YAML edits.
**Routing:** dev for implement phase

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `genre_packs/mutant_wasteland/archetypes.yaml` — added 3 missing OCEAN profiles (Ruin Diver, Village Elder, Beastkin Scout)
- `genre_packs/low_fantasy/archetypes.yaml` — added 6 OCEAN profiles
- `genre_packs/elemental_harmony/archetypes.yaml` — added 6 OCEAN profiles
- `genre_packs/road_warrior/archetypes.yaml` — added 8 OCEAN profiles
- `genre_packs/neon_dystopia/archetypes.yaml` — added 8 OCEAN profiles
- `genre_packs/space_opera/archetypes.yaml` — added 8 OCEAN profiles
- `genre_packs/pulp_noir/archetypes.yaml` — added 9 OCEAN profiles
- `genre_packs/elemental_harmony/worlds/burning_peace/archetypes.yaml` — added 12 OCEAN profiles
- `genre_packs/neon_dystopia/worlds/franchise_nations/archetypes.yaml` — added 8 OCEAN profiles
- `genre_packs/pulp_noir/worlds/annees_folles/archetypes.yaml` — added 8 OCEAN profiles
- `genre_packs/road_warrior/worlds/the_circuit/archetypes.yaml` — added 12 OCEAN profiles

**Coverage:** 91/91 archetypes now have OCEAN profiles (was 3/91)
**Tests:** N/A — data-only changes, no code tests
**Branch:** feat/10-8-backfill-ocean-profiles (pushed to sidequest-content)

**Handoff:** To review phase

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | N/A | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | N/A | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | N/A | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 1 | confirmed 0, dismissed 0, deferred 1 |
| 7 | reviewer-security | N/A | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | N/A | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | none | N/A |

**All received:** Yes (4 returned, 5 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 1 deferred

**Type-design finding (deferred):** `NpcArchetype` lacks `#[serde(deny_unknown_fields)]` — a YAML field typo in ocean dimensions would silently default to 5.0. Pre-existing issue not introduced by this diff; deferred as a non-blocking improvement for a future story.

### Rule Compliance

No code-level project rules apply to this YAML data change. Checked:
- Epic 10 spec: 5 f64 dimensions, 0.0–10.0 range — **COMPLIANT** (all 455 values in 1.0–9.5)
- Existing pattern (mutant_wasteland baseline): ocean block after disposition_default, O→C→E→A→N order, float with 1 decimal — **COMPLIANT** across all 91 archetypes
- Rust struct field names match YAML keys — **COMPLIANT** (verified at sidequest-genre/src/models.rs:71-87)

### Devil's Advocate

What if this data is subtly wrong in ways that won't show up until gameplay? Here's what could go wrong:

**Personality-description misalignment.** The biggest risk isn't structural — it's semantic. Each OCEAN profile was generated by an LLM reading archetype descriptions and mapping them to five floats. An LLM could systematically misinterpret a trait: for example, confusing "stoic" (which in Big Five terms means low Neuroticism + low Extraversion) with "emotionless" (which might get wrongly mapped to low Agreeableness). I spot-checked 5 archetypes and they were psychologically sound, but I didn't check all 91. A systematic bias — like consistently underscoring Openness on scholarly archetypes, or consistently overscoring Extraversion on leaders — would only surface during extended playtesting when NPCs "feel" wrong.

**The ±1.5 variance problem.** The spec says random NPC generation applies ±1.5 variance from the archetype baseline. If a baseline is set at 1.0 (e.g., Camelot du Roi's Openness and Agreeableness), the variance could push it to -0.5 — but the Rust code clamps to 0.0. This means archetypes with extreme low scores (near 0-1.5) will have compressed variance on the low end. This is by design (clamping is in the spec), but it means that very extreme archetypes have less personality variation in their generated NPCs. Not a bug, but a design consequence worth knowing.

**Silent deserialization defaults.** If someone later edits an ocean block and accidentally misspells a field (e.g., "openess"), the `#[serde(default)]` will silently fill in 5.0 (neutral). The archetype would load without error but with a wrong personality. This is the same issue flagged by the type-design subagent. The current data is correct, but the system lacks a safety net for future edits.

**Cross-genre consistency.** I verified that the duplicate "Data Broker" in neon_dystopia has appropriately differentiated profiles. But I didn't exhaustively check whether similar archetypes across genres (e.g., "Traveling Merchant" in low_fantasy vs "Wasteland Trader" in mutant_wasteland vs "River Trader" in elemental_harmony) have profiles that diverge enough to feel distinct during gameplay. They may all cluster around "high E, moderate O, moderate C" because traders share a behavioral archetype. This would make trader NPCs feel samey across genres — but arguably that's realistic.

None of these rise to blocking severity. The data is structurally perfect, the profiles are psychologically defensible on the samples I checked, and the only latent risk is the deserialization safety net (deferred improvement, not this story's scope).

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** YAML `ocean:` block → serde_yaml deserializer → `OceanProfile` struct (models.rs:71) via `deserialize_clamped` → `NpcArchetype.ocean: Option<OceanProfile>` (models.rs:605) → narrator behavioral_summary(). Safe because: field names match exactly, values are in range, clamping handles edge cases.

**Pattern observed:** [VERIFIED] Consistent O→C→E→A→N field ordering across all 91 blocks, matching the Rust struct field declaration order. Block placement after `disposition_default` matches the 3 existing mutant_wasteland exemplars.

**Error handling:** [TYPE] The Rust deserializer has `deserialize_clamped` on each field and `#[serde(default = "neutral")]` — missing or out-of-range values are handled gracefully. However, `NpcArchetype` lacks `deny_unknown_fields` so misspelled YAML keys would silently default rather than fail. Deferred as improvement.

**Coverage:** [RULE] 91/91 archetypes across 11 files. 455 dimension values all in range 1.0–9.5. [SILENT] No structural inconsistencies — field count, ordering, indentation, float formatting all uniform.

**Observations:**
1. [VERIFIED] All 91 archetypes have complete ocean blocks — programmatic validation via Python yaml parser
2. [VERIFIED] YAML field names match Rust OceanProfile struct exactly — sidequest-genre/src/models.rs:71-87
3. [VERIFIED] Value range 1.0–9.5 within 0.0–10.0 spec — statistical check: O mean=5.00, C mean=6.22, E mean=4.96, A mean=4.58, N mean=3.99
4. [VERIFIED] Personality-profile consistency on 5 spot-checked archetypes (Nervous Fence, AI Fragment, War Boy, The Don, Burned Operative) — all psychologically coherent with traits and descriptions
5. [VERIFIED] 3 existing mutant_wasteland profiles unchanged — diff shows additions only at Ruin Diver, Village Elder, Beastkin Scout
6. [LOW] Pre-existing duplicate "The Data Broker" in neon_dystopia genre+world — correctly differentiated profiles (genre: N=7.5 paranoid, world: N=4.0 amoral). Not introduced by this PR.
7. [TYPE] (deferred) NpcArchetype missing `deny_unknown_fields` — latent typo risk on future YAML edits

[EDGE] N/A — disabled via settings
[SILENT] Clean — no silent failures found
[TEST] N/A — disabled via settings
[DOC] N/A — disabled via settings
[TYPE] 1 deferred finding (pre-existing, not this diff)
[SEC] N/A — disabled via settings
[SIMPLE] N/A — disabled via settings
[RULE] Clean — all rules checked, 0 violations

**Handoff:** To Hawkeye Pierce (SM) for finish-story