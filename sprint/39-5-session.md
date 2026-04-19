---
story_id: "39-5"
jira_key: "39-5"
epic: "39"
workflow: "wire-first"
---

# Story 39-5: Authored Advancement Effects + resolved_beat_for

## Story Details
- **ID:** 39-5
- **Jira Key:** 39-5
- **Workflow:** wire-first
- **Stack Parent:** 39-4 (BeatDef.edge_delta + target_edge_delta + beat dispatch wiring)

## Workflow Tracking
**Workflow:** wire-first
**Phase:** green
**Phase Started:** 2026-04-19T17:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-19T00:00:00Z | 2026-04-19T16:00:00Z | — |
| red | 2026-04-19T16:00:00Z | 2026-04-19T17:00:00Z | — |
| green | 2026-04-19T17:00:00Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Gap** (non-blocking): AC4 text says "39-4 hard-coded Fighter stub is deleted", but story 39-4 shipped without such a stub — `apply_beat_edge_deltas` reads `beat.edge_delta` directly. The real AC4 work is routing dispatch through `resolved_beat_for` (via the new `apply_beat_edge_deltas_resolved` entry point), not deleting a non-existent stub. Affects `sidequest-api/crates/sidequest-server/src/dispatch/beat.rs` (no stub to delete; wrap existing path via the new resolved entry). *Found by TEA during test design.*
- **Gap** (non-blocking): `RecoveryTrigger` currently lives in `sidequest-game::creature_core` (line 174). AC1 amendment adds `while_strained: bool` to `OnBeatSuccess`, but `AdvancementEffect::EdgeRecovery { trigger: RecoveryTrigger, .. }` in `sidequest-genre` creates a cross-crate cycle (genre would need to depend on game). Dev must either (a) move `RecoveryTrigger` to `sidequest-genre` (cleanest — it's config-shape), or (b) define a parallel `EdgeRecoveryTrigger` in genre. Tests import `sidequest_genre::RecoveryTrigger` under option (a). Affects `sidequest-game/src/creature_core.rs`, `sidequest-genre/src/models/rules.rs`. *Found by TEA during test design.*
- **Gap** (non-blocking): Milestone event bus (ADR-021) is not yet wired — no event type, no dispatch handler. AC5 implementation needs Dev to define a narrow seam. Tests stipulate `sidequest_game::advancement::grant_advancement_tier(&mut Character, tier_id, &tree) -> Result<AdvancementGrantOutcome, AdvancementGrantError>` as that seam; production Milestone handler (whenever it arrives) calls it. Affects `sidequest-game/src/advancement.rs` (new), eventually `sidequest-server/src/dispatch/state_mutations.rs`. *Found by TEA during test design.*
- **Question** (non-blocking): `BeatDef.resource_deltas` is `HashMap<String, f64>` but `AdvancementEffect::BeatDiscount.resource_mod` is `HashMap<String, i32>` per ADR-078 type design. Tests assume the integer `resource_mod` is added to the float delta in the delta's own sign convention (author cost -2.0, mod -1 → resolved -1.0). If Dev picks a different arithmetic (e.g., multiply, saturate at zero, ignore sign-mismatch), update the `resolved_beat_for_beat_discount_resource_mod_reduces_resource_deltas` test accordingly and note the rule in the advancement module doc comment. *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **`apply_beat_edge_deltas_resolved` as a new entry point (additive), not a signature change to `apply_beat_edge_deltas`**
  - Spec source: context-epic-39.md "Engine Wiring" block, "`let resolved = resolved_beat_for(acting_char, beat, &genre.advancement_tree);`"
  - Spec text: Epic implies `handle_applied_side_effects` directly calls `resolved_beat_for`, leaving the existing `apply_beat_edge_deltas` helper to mutate signature.
  - Implementation: Tests introduce a new public entry `apply_beat_edge_deltas_resolved(&mut GameSnapshot, &BeatDef, &str, &AdvancementTree)` alongside the 39-4 `apply_beat_edge_deltas`. The existing 11 tests in `edge_delta_dispatch_wiring_story_39_4_tests.rs` still compile against the old three-arg signature.
  - Rationale: Additive entry keeps 39-4's RED/GREEN intact and avoids a signature-cascade through callers during Dev's GREEN. Dev is free to make `apply_beat_edge_deltas` forward to the resolved entry with an empty `AdvancementTree`, or to delete it outright and migrate the 39-4 tests — test-coupling-to-implementation is not at risk either way.
  - Severity: minor
  - Forward impact: Dev may delete `apply_beat_edge_deltas` and migrate 39-4's tests once 39-5 is green; or keep it as a convenience shim. Either is acceptable.

- **Loader test targets a new `sidequest_genre::load_advancement_tree(&Path)` public function, not the existing `load_genre_pack` loader**
  - Spec source: context-story-39-5.md §Technical Guardrails "Key Files" row: "Load `mechanical_effects` from `progression.yaml` OR standalone `{genre}/advancements.yaml`; fail loudly if both present".
  - Spec text: The spec implies the logic lives inside the existing `load_genre_pack` path.
  - Implementation: Tests call `sidequest_genre::load_advancement_tree(&dir)` as the narrow, testable seam. Dev may still wire this into `load_genre_pack` so `GenrePack` carries the resolved tree — but the test-level surface is the narrow function.
  - Rationale: Constructing a full `GenrePack` from a fixture directory requires ~13 YAML files and is orthogonal to the dual-location-loader behaviour under test. The narrow seam is the minimum production-reachable surface that proves the rule.
  - Severity: minor
  - Forward impact: none — Dev wires `load_advancement_tree` however is most convenient inside `load_genre_pack`.

- **`source_effects: Vec<AdvancementEffect>` (owned) on `ResolvedBeat`, not `Vec<&AdvancementEffect>` as epic context suggests**
  - Spec source: context-epic-39.md §Technical Architecture: "returns a ResolvedBeat with effective edge_delta / target_edge_delta / resource_deltas plus source_effects: Vec<&AdvancementEffect> for telemetry".
  - Spec text: Epic context specifies borrowed references.
  - Implementation: Tests treat `source_effects` as owned `Vec<AdvancementEffect>` via pattern-matching and length checks that work for both owned and borrowed forms; the compile-time wiring test does not pin the exact type.
  - Rationale: Owned effects avoid lifetime parameters on `ResolvedBeat` and keep test construction ergonomic. Dev may choose borrowed with a lifetime, owned, or clone-on-resolve — the behaviour assertions don't care.
  - Severity: minor
  - Forward impact: none — Dev picks whichever form compiles.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (imports resolve to symbols that do not yet exist; cargo check fails to compile the new test files until Dev implements)

**Test Files:**
- `sidequest-api/crates/sidequest-genre/tests/advancement_effects_story_39_5_tests.rs` — 13 tests: enum shape + serde (7), AdvancementTree shape (2), AffinityTier.mechanical_effects (2), live heavy_metal progression.yaml content wiring (1), dual-location loader happy + conflict paths (2)
- `sidequest-api/crates/sidequest-genre/tests/fixtures/standalone_advancements/{progression.yaml,advancements.yaml}` — fixture for standalone-host loader path
- `sidequest-api/crates/sidequest-genre/tests/fixtures/dual_host_conflict/{progression.yaml,advancements.yaml}` — fixture for both-hosts-present fail-loud path
- `sidequest-api/crates/sidequest-server/tests/integration/advancement_resolved_beat_wiring_story_39_5_tests.rs` — 16 tests: `resolved_beat_for` behaviour (7) + dispatch wiring (3) + milestone grant (4) + wiring/source-scan (3)
- `sidequest-api/crates/sidequest-server/tests/integration/main.rs` — new `mod` line adding the 39-5 module to the consolidated test binary

**Tests Written:** 29 tests covering ACs 1, 2, 3, 4, 5, 7
**AC6 (per-genre audit doc artifact):** Not test-targetable — Reviewer must verify the doc lands with a 10-genre table (either as an ADR annex or `docs/` file per story context). Captured in the story context but not in tests.

### Rule Coverage (lang-review/rust.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent error swallowing | `loader_fails_loudly_when_both_hosts_present`, `resolved_beat_for_with_unknown_tier_id_panics_loudly`, `grant_advancement_tier_with_unknown_id_returns_error`, `advancement_tier_id_must_not_be_blank` | failing (red) |
| #2 non-exhaustive on pub enums | `advancement_effect_is_non_exhaustive_for_adr_079_extensions` | failing (red) |
| #4 tracing coverage on state transitions | `grant_advancement_tier_emits_tier_granted_otel_span`, `dispatch_edge_delta_span_carries_advancements_applied_field`, `dispatch_effect_applied_span_emitted_when_resolved_beat_applies_effect` | failing (red) |
| #5 validated constructors at boundaries | `advancement_tier_id_must_not_be_blank` (blank-id rejection in deserialise) | failing (red) |
| #6 test quality | Self-checked — every test has ≥1 assertion with a specific value, no `let _ = result;`, no `assert!(true)`, no vacuous `is_some()` checks | pass (self-check) |
| #8 Deserialize bypassing validated constructors | `advancement_tier_id_must_not_be_blank` covers the deserialize path; Dev should verify their `AdvancementTier::new` (if any) enforces the same blank-id rejection | failing (red) |
| #13 constructor/Deserialize consistency | Implicit via #8 — same rule exercised on same type | failing (red) |

**Rules checked:** 7 of 15 lang-review rules are directly test-exercised. The remaining 8 (#3 placeholders, #7 unsafe casts, #9 public fields, #10 tenant context, #11 workspace deps, #12 dev-deps, #14 fix regressions, #15 unbounded input) do not apply to the shape of this story — it introduces no user-input surfaces, no tenancy, and no multi-tenant state.
**Self-check:** 0 vacuous tests found. The `_ = result;` in `resolved_beat_for_with_unknown_tier_id_panics_loudly` is a `#[should_panic]` test where the assertion is the panic itself — not vacuous.

### RED Verification

Not run inline — cargo-guard hook was timing out on the shared target dir. The RED signal is guaranteed by compile failure: the tests import `AdvancementEffect`, `AdvancementTree`, `LoreRevealScope`, `AdvancementTier`, `AffinityTier.mechanical_effects`, `sidequest_genre::load_advancement_tree`, `sidequest_genre::RecoveryTrigger`, `sidequest_game::advancement::{resolved_beat_for, grant_advancement_tier, ResolvedBeat, AdvancementGrantOutcome, AdvancementGrantError}`, and `sidequest_server::apply_beat_edge_deltas_resolved` — none of which exist in the current tree (verified by Machine Shop explore, item 10: "Do NOT exist yet").

Dev should run `cargo check --tests -p sidequest-genre` and `cargo check --tests -p sidequest-server` at the start of GREEN to see the canonical import-resolution failures, then implement to satisfy them.

**Handoff:** To Naomi Nagata (Dev) for GREEN phase.
