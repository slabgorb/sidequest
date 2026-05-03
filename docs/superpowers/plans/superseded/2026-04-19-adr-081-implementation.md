# ADR-081 Implementation — Expanded Story 39-5

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship seven `AdvancementEffect` variants (ADR-078's five + ADR-081's two), `ConditionExpr` grammar, `starting_kit` and `inherits:` hydration, character-scoped `ResourcePool` hydration (Th`rook's reniksnad), scene-end decay + threshold watchers, and the reaction hook in beat dispatch — all landing in one expanded Epic 39 story 5.

**Architecture:** Two distinct resolution paths. `resolved_beat_for` (enum-local substitution) handles six variants including `ConditionalEffectGating`. A new reaction hook inside `handle_applied_side_effects` handles `AllyEdgeIntercept` by redirecting target Edge deltas before the ally is debited. All chargen-time validation fails loud. All advancement decisions emit OTEL spans.

**Tech Stack:** Rust (sidequest-game, sidequest-api, sidequest-telemetry), serde YAML, existing `ResourcePool` struct, existing OTEL span machinery.

**Spec:** `docs/superpowers/specs/2026-04-19-adr-081-implementation-design.md`

---

## Prerequisites (critical — read before starting)

This plan assumes Epic 39 stories 39-1 through 39-4 have shipped. Those stories build the foundation this plan extends:

- **39-1** — `EdgePool` struct; shared `thresholds.rs` helper.
- **39-2** — HP fields removed from `CreatureCore`; `Combatant` trait gains `edge/max_edge/is_broken`.
- **39-3** — `RulesConfig.edge_config`; heavy_metal `rules.yaml` purged of HP, gains edge config.
- **39-4** — `BeatDef.edge_delta`, `BeatDef.target_edge_delta`, `BeatDef.resource_deltas`; `handle_applied_side_effects` has self-debit and target-debit blocks; placeholder hard-coded advancement (Fighter +2 edge_max) for smoke gate.

**If any prereq is missing, stop and address that first.** This plan cannot land otherwise — the reaction hook attaches to 39-4's target-debit block, and the enum extends 39-5's not-yet-landed enum skeleton.

**Verification at start:**

```bash
# From repo root
grep -n "pub struct EdgePool" sidequest-api/crates/sidequest-game/src/thresholds.rs   # 39-1
grep -n "target_edge_delta" sidequest-api/crates/sidequest-game/src/beat.rs            # 39-4
grep -n "edge_config" sidequest-api/crates/sidequest-game/src/rules.rs                  # 39-3
```

All three must return matches. If any miss, stop.

---

## File Structure

**New files:**
- `sidequest-api/crates/sidequest-game/src/advancement.rs` — `AdvancementEffect`, `ConditionExpr`, `resolved_beat_for`, error types
- `sidequest-api/crates/sidequest-game/src/advancement_hydration.rs` — `starting_kit` loader, `inherits:` resolution, cycle detection
- `sidequest-api/crates/sidequest-game/src/character_resources.rs` — character-scoped `ResourcePool` hydration, scene-end decay hook
- `sidequest-api/crates/sidequest-game/tests/advancement_tests.rs` — unit tests for the enum resolution
- `sidequest-api/crates/sidequest-game/tests/hydration_tests.rs` — unit tests for loader + inherits
- `sidequest-api/crates/sidequest-game/tests/character_resources_tests.rs` — decay + threshold tests
- `sidequest-api/tests/adr_081_integration_tests.rs` — integration + real wiring tests
- `sidequest-api/tests/fixtures/adr_081/` — YAML fixtures for integration tests
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/playtest_fixtures/prot_thokk_intercept.md` — 39-8 playtest scene
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/playtest_fixtures/th_rook_dose_flip.md` — 39-8 playtest scene

**Modified files:**
- `sidequest-api/crates/sidequest-game/src/creature_core.rs` — add `acquired_advancements`, `acquired_grants`, `character_resources` fields
- `sidequest-api/crates/sidequest-game/src/beat.rs` — reaction hook in target-debit block of `handle_applied_side_effects`
- `sidequest-api/crates/sidequest-game/src/lib.rs` — register new modules
- `sidequest-api/crates/sidequest-telemetry/src/spans.rs` — add six new span kinds
- `sidequest-api/crates/sidequest-genre/src/loader.rs` — call into advancement_hydration + character_resources loaders at chargen

---

## Task 1: `AdvancementEffect` + `ConditionExpr` enums with serde round-trip

**Files:**
- Create: `sidequest-api/crates/sidequest-game/src/advancement.rs`
- Create: `sidequest-api/crates/sidequest-game/tests/advancement_tests.rs`
- Modify: `sidequest-api/crates/sidequest-game/src/lib.rs` (register module)

- [ ] **Step 1: Write the failing test**

Create `sidequest-api/crates/sidequest-game/tests/advancement_tests.rs`:

```rust
use sidequest_game::advancement::{AdvancementEffect, ConditionExpr, RecoveryTrigger, ResourceDelta};

#[test]
fn edge_max_bonus_round_trips() {
    let yaml = "type: edge_max_bonus\namount: 1";
    let parsed: AdvancementEffect = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(parsed, AdvancementEffect::EdgeMaxBonus { amount: 1 });
    let re_emitted = serde_yaml::to_string(&parsed).unwrap();
    let re_parsed: AdvancementEffect = serde_yaml::from_str(&re_emitted).unwrap();
    assert_eq!(parsed, re_parsed);
}

#[test]
fn ally_edge_intercept_round_trips() {
    let yaml = "type: ally_edge_intercept\nally_whitelist:\n  - Cheeney\n  - \"Lil'Sebastian\"\nmax_redirect: 3";
    let parsed: AdvancementEffect = serde_yaml::from_str(yaml).unwrap();
    match &parsed {
        AdvancementEffect::AllyEdgeIntercept { ally_whitelist, max_redirect } => {
            assert_eq!(ally_whitelist, &vec!["Cheeney".to_string(), "Lil'Sebastian".to_string()]);
            assert_eq!(*max_redirect, 3);
        }
        other => panic!("expected AllyEdgeIntercept, got {:?}", other),
    }
}

#[test]
fn conditional_effect_gating_recursive_round_trip() {
    let yaml = r#"
type: conditional_effect_gating
condition:
  type: resource_above
  resource: reniksnad
  threshold: 5
when_true:
  type: beat_discount
  beat_id: commit_cost
  resource_mod: { flesh: 1 }
when_false:
  type: beat_discount
  beat_id: commit_cost
  resource_mod: { flesh: -1 }
"#;
    let parsed: AdvancementEffect = serde_yaml::from_str(yaml).unwrap();
    match &parsed {
        AdvancementEffect::ConditionalEffectGating { condition, when_true, when_false } => {
            assert!(matches!(condition, ConditionExpr::ResourceAbove { resource, threshold }
                if resource == "reniksnad" && *threshold == 5));
            assert!(matches!(when_true.as_ref(), AdvancementEffect::BeatDiscount { .. }));
            assert!(when_false.is_some());
        }
        other => panic!("expected ConditionalEffectGating, got {:?}", other),
    }
}

#[test]
fn conditional_effect_gating_when_false_defaults_to_none() {
    let yaml = r#"
type: conditional_effect_gating
condition:
  type: resource_at_or_below
  resource: reniksnad
  threshold: 3
when_true:
  type: leverage_bonus
  beat_id: commit_cost
  target_edge_delta_mod: -1
"#;
    let parsed: AdvancementEffect = serde_yaml::from_str(yaml).unwrap();
    match &parsed {
        AdvancementEffect::ConditionalEffectGating { when_false, .. } => {
            assert!(when_false.is_none());
        }
        _ => panic!("expected ConditionalEffectGating"),
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test advancement_tests`
Expected: FAIL — `advancement` module not found.

- [ ] **Step 3: Implement the enum**

Create `sidequest-api/crates/sidequest-game/src/advancement.rs`:

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub type ResourceDelta = HashMap<String, i32>;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum RecoveryTrigger {
    OnBeatSuccess {
        #[serde(default)]
        while_strained: bool,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ConditionExpr {
    ResourceAbove { resource: String, threshold: i32 },
    ResourceAtOrBelow { resource: String, threshold: i32 },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum AdvancementEffect {
    EdgeMaxBonus {
        amount: i32,
    },
    BeatDiscount {
        beat_id: String,
        #[serde(default)]
        edge_delta_mod: Option<i32>,
        #[serde(default)]
        resource_mod: Option<ResourceDelta>,
    },
    LeverageBonus {
        beat_id: String,
        target_edge_delta_mod: i32,
    },
    EdgeRecovery {
        trigger: RecoveryTrigger,
        amount: u32,
    },
    LoreRevealBonus {
        scope: String,
    },
    // ADR-081
    AllyEdgeIntercept {
        ally_whitelist: Vec<String>,
        max_redirect: u32,
    },
    ConditionalEffectGating {
        condition: ConditionExpr,
        when_true: Box<AdvancementEffect>,
        #[serde(default)]
        when_false: Option<Box<AdvancementEffect>>,
    },
}
```

Register in `sidequest-api/crates/sidequest-game/src/lib.rs` — add:

```rust
pub mod advancement;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test advancement_tests`
Expected: PASS (all 4 tests green).

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/advancement.rs \
        sidequest-api/crates/sidequest-game/tests/advancement_tests.rs \
        sidequest-api/crates/sidequest-game/src/lib.rs
git commit -m "$(cat <<'EOF'
feat(advancement): AdvancementEffect + ConditionExpr enums (7 variants)

Five ADR-078 day-1 variants (EdgeMaxBonus, BeatDiscount, LeverageBonus,
EdgeRecovery, LoreRevealBonus) plus two ADR-081 variants
(AllyEdgeIntercept, ConditionalEffectGating). ConditionExpr grammar
ships with ResourceAbove and ResourceAtOrBelow comparators only;
boolean composition out of scope per ADR-081.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `CreatureCore` schema extensions

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/creature_core.rs`
- Modify: `sidequest-api/crates/sidequest-game/tests/creature_core_tests.rs` (add test)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-api/crates/sidequest-game/tests/creature_core_tests.rs`:

```rust
use sidequest_game::advancement::AdvancementEffect;
use sidequest_game::creature_core::{CreatureCore, GrantRef};
use sidequest_game::thresholds::ResourcePool;

#[test]
fn creature_core_carries_advancement_state_fields() {
    let mut cc = CreatureCore::default_for_tests();
    cc.acquired_advancements.push(AdvancementEffect::EdgeMaxBonus { amount: 1 });
    cc.acquired_grants.push(GrantRef {
        id: "stand_in_front_kit".into(),
        label: "Stand in Front".into(),
        narration_hint: "While Prot'Thokk is at full Edge...".into(),
    });
    cc.character_resources.insert(
        "reniksnad".into(),
        ResourcePool::new(0, 10, 7),
    );

    assert_eq!(cc.acquired_advancements.len(), 1);
    assert_eq!(cc.acquired_grants.len(), 1);
    assert!(cc.character_resources.contains_key("reniksnad"));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test creature_core_tests creature_core_carries_advancement_state_fields`
Expected: FAIL — missing fields / missing `GrantRef`.

- [ ] **Step 3: Add fields to CreatureCore and define GrantRef**

In `sidequest-api/crates/sidequest-game/src/creature_core.rs`, add the fields inside the `CreatureCore` struct (keep existing fields untouched):

```rust
use crate::advancement::AdvancementEffect;
use crate::thresholds::ResourcePool;
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GrantRef {
    pub id: String,
    pub label: String,
    pub narration_hint: String,
}

// Inside CreatureCore (add these fields with Default derived):
pub struct CreatureCore {
    // ... existing fields
    #[serde(default)]
    pub acquired_advancements: Vec<AdvancementEffect>,
    #[serde(default)]
    pub acquired_grants: Vec<GrantRef>,
    #[serde(default)]
    pub character_resources: HashMap<String, ResourcePool>,
}
```

Ensure `CreatureCore::default_for_tests()` (or whatever the existing test helper is) initializes the three new fields as empty. If `ResourcePool::new(min, max, starting)` doesn't already exist, add it as a thin constructor in `thresholds.rs`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test creature_core_tests`
Expected: PASS. Also verify nothing else in the workspace broke — `cargo build --workspace`.

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/creature_core.rs \
        sidequest-api/crates/sidequest-game/src/thresholds.rs \
        sidequest-api/crates/sidequest-game/tests/creature_core_tests.rs
git commit -m "feat(creature_core): acquired_advancements, acquired_grants, character_resources

Effects are stored flat (Vec<AdvancementEffect>); grant-level identity
(id/label/narration_hint) stored separately in acquired_grants for
GM-panel display and KnownFact injection. Resolution logic reads only
the flat effect list — decoupling from authoring shape. character_resources
reuses existing ResourcePool struct — no new pool type.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Starting-kit loader + `inherits:` resolution

**Files:**
- Create: `sidequest-api/crates/sidequest-game/src/advancement_hydration.rs`
- Create: `sidequest-api/crates/sidequest-game/tests/hydration_tests.rs`
- Modify: `sidequest-api/crates/sidequest-game/src/lib.rs`

- [ ] **Step 1: Write the failing tests**

Create `sidequest-api/crates/sidequest-game/tests/hydration_tests.rs`:

```rust
use sidequest_game::advancement::AdvancementEffect;
use sidequest_game::advancement_hydration::{
    hydrate_starting_kit, StartingKitHydrationError, ProgressionFiles,
};

fn rux_yaml() -> &'static str {
    r#"
character:
  save_id: rux
  name: Rux
starting_kit:
  label: Servant of the Old Line
  grants:
    - id: strike_from_the_low_line_kit
      label: Strike from the Low Line
      narration_hint: Tismenni precision
      effects:
        - { type: leverage_bonus, beat_id: strike, target_edge_delta_mod: -1 }
    - id: stand_in_front_kit
      label: Stand in Front
      narration_hint: Posture, not shield
      effects:
        - { type: edge_max_bonus, amount: 1 }
        - { type: beat_discount, beat_id: brace, edge_delta_mod: -1 }
"#
}

fn ludzo_inherits_rux() -> &'static str {
    r#"
character: { save_id: ludzo, name: Ludzo }
starting_kit:
  inherits: rux
  note: test sandbox
"#
}

#[test]
fn hydrate_flattens_grants_into_effects_and_records_grant_refs() {
    let files = ProgressionFiles::from_inline(vec![("rux", rux_yaml())]);
    let (effects, grants) = hydrate_starting_kit("rux", &files).unwrap();

    // Three effects total (compound grant contributes two).
    assert_eq!(effects.len(), 3);
    // Two grants recorded for display.
    assert_eq!(grants.len(), 2);
    assert_eq!(grants[0].id, "strike_from_the_low_line_kit");
    assert_eq!(grants[1].id, "stand_in_front_kit");

    assert!(matches!(&effects[0], AdvancementEffect::LeverageBonus { beat_id, .. } if beat_id == "strike"));
    assert!(matches!(&effects[1], AdvancementEffect::EdgeMaxBonus { amount: 1 }));
    assert!(matches!(&effects[2], AdvancementEffect::BeatDiscount { beat_id, .. } if beat_id == "brace"));
}

#[test]
fn inherits_resolves_to_source_character_kit() {
    let files = ProgressionFiles::from_inline(vec![
        ("rux", rux_yaml()),
        ("ludzo", ludzo_inherits_rux()),
    ]);
    let (ludzo_effects, ludzo_grants) = hydrate_starting_kit("ludzo", &files).unwrap();
    let (rux_effects, rux_grants) = hydrate_starting_kit("rux", &files).unwrap();
    assert_eq!(ludzo_effects, rux_effects);
    assert_eq!(ludzo_grants, rux_grants);
}

#[test]
fn inherits_cycle_is_hard_failure() {
    let a = "character: { save_id: a, name: A }\nstarting_kit: { inherits: b }";
    let b = "character: { save_id: b, name: B }\nstarting_kit: { inherits: a }";
    let files = ProgressionFiles::from_inline(vec![("a", a), ("b", b)]);
    let err = hydrate_starting_kit("a", &files).unwrap_err();
    assert!(matches!(err, StartingKitHydrationError::InheritCycle { .. }));
}

#[test]
fn inherits_missing_is_hard_failure() {
    let a = "character: { save_id: a, name: A }\nstarting_kit: { inherits: ghost }";
    let files = ProgressionFiles::from_inline(vec![("a", a)]);
    let err = hydrate_starting_kit("a", &files).unwrap_err();
    assert!(matches!(err, StartingKitHydrationError::InheritMissing { .. }));
}

#[test]
fn unknown_effect_type_is_hard_failure() {
    let bad = r#"
character: { save_id: bad, name: Bad }
starting_kit:
  grants:
    - id: oops
      label: Oops
      narration_hint: x
      effects:
        - { type: teleport_across_dimensions, amount: 1 }
"#;
    let files = ProgressionFiles::from_inline(vec![("bad", bad)]);
    let err = hydrate_starting_kit("bad", &files).unwrap_err();
    assert!(matches!(err, StartingKitHydrationError::UnknownEffectType { .. }));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test hydration_tests`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the loader**

Create `sidequest-api/crates/sidequest-game/src/advancement_hydration.rs`:

```rust
use crate::advancement::AdvancementEffect;
use crate::creature_core::GrantRef;
use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StartingKitHydrationError {
    #[error("character `{source_id}` inherits from `{target}` which was not found")]
    InheritMissing { source_id: String, target: String },
    #[error("inherit cycle detected starting at `{start}` (chain: {chain:?})")]
    InheritCycle { start: String, chain: Vec<String> },
    #[error("unknown effect type in `{character_id}` grant `{grant_id}`: {detail}")]
    UnknownEffectType { character_id: String, grant_id: String, detail: String },
    #[error("YAML parse failure for character `{character_id}`: {detail}")]
    YamlParse { character_id: String, detail: String },
}

#[derive(Debug, Deserialize)]
struct ProgressionFile {
    #[serde(default)]
    starting_kit: Option<StartingKitYaml>,
}

#[derive(Debug, Deserialize)]
struct StartingKitYaml {
    #[serde(default)]
    label: Option<String>,
    #[serde(default)]
    inherits: Option<String>,
    #[serde(default)]
    grants: Vec<GrantYaml>,
}

#[derive(Debug, Deserialize)]
struct GrantYaml {
    id: String,
    label: String,
    narration_hint: String,
    #[serde(default)]
    effects: Vec<AdvancementEffect>,
}

/// Owns a map from character id to raw YAML. The real loader reads files from disk;
/// tests use `from_inline`.
pub struct ProgressionFiles {
    map: HashMap<String, String>,
}

impl ProgressionFiles {
    pub fn from_inline(entries: Vec<(&str, &str)>) -> Self {
        Self {
            map: entries.into_iter().map(|(k, v)| (k.to_string(), v.to_string())).collect(),
        }
    }

    pub fn from_dir(dir: &std::path::Path) -> std::io::Result<Self> {
        let mut map = HashMap::new();
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("yaml") {
                continue;
            }
            let id = path.file_stem().and_then(|s| s.to_str()).unwrap_or("").to_string();
            let content = std::fs::read_to_string(&path)?;
            map.insert(id, content);
        }
        Ok(Self { map })
    }

    fn get(&self, id: &str) -> Option<&str> {
        self.map.get(id).map(|s| s.as_str())
    }
}

pub fn hydrate_starting_kit(
    character_id: &str,
    files: &ProgressionFiles,
) -> Result<(Vec<AdvancementEffect>, Vec<GrantRef>), StartingKitHydrationError> {
    let mut visited: HashSet<String> = HashSet::new();
    let mut chain: Vec<String> = Vec::new();
    resolve(character_id, files, &mut visited, &mut chain)
}

fn resolve(
    id: &str,
    files: &ProgressionFiles,
    visited: &mut HashSet<String>,
    chain: &mut Vec<String>,
) -> Result<(Vec<AdvancementEffect>, Vec<GrantRef>), StartingKitHydrationError> {
    if !visited.insert(id.to_string()) {
        chain.push(id.to_string());
        return Err(StartingKitHydrationError::InheritCycle {
            start: chain.first().cloned().unwrap_or_else(|| id.to_string()),
            chain: chain.clone(),
        });
    }
    chain.push(id.to_string());

    let raw = files.get(id).ok_or_else(|| StartingKitHydrationError::InheritMissing {
        source_id: chain.get(chain.len().saturating_sub(2)).cloned().unwrap_or_default(),
        target: id.to_string(),
    })?;

    let file: ProgressionFile = serde_yaml::from_str(raw).map_err(|e| {
        // Try to detect "unknown variant" to translate to UnknownEffectType with context.
        let msg = e.to_string();
        if msg.contains("unknown variant") {
            StartingKitHydrationError::UnknownEffectType {
                character_id: id.to_string(),
                grant_id: String::new(),
                detail: msg,
            }
        } else {
            StartingKitHydrationError::YamlParse {
                character_id: id.to_string(),
                detail: msg,
            }
        }
    })?;

    let kit = match file.starting_kit {
        Some(k) => k,
        None => return Ok((vec![], vec![])),
    };

    if let Some(parent) = kit.inherits.as_deref() {
        return resolve(parent, files, visited, chain);
    }

    let mut effects = Vec::new();
    let mut grants = Vec::new();
    for grant in kit.grants {
        grants.push(GrantRef {
            id: grant.id,
            label: grant.label,
            narration_hint: grant.narration_hint,
        });
        for eff in grant.effects {
            effects.push(eff);
        }
    }
    Ok((effects, grants))
}
```

Register in `sidequest-api/crates/sidequest-game/src/lib.rs`:

```rust
pub mod advancement_hydration;
```

Add `thiserror = "1"` to `sidequest-game/Cargo.toml` `[dependencies]` if not already present.

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test hydration_tests`
Expected: PASS (all 5 tests green).

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/advancement_hydration.rs \
        sidequest-api/crates/sidequest-game/tests/hydration_tests.rs \
        sidequest-api/crates/sidequest-game/src/lib.rs \
        sidequest-api/crates/sidequest-game/Cargo.toml
git commit -m "feat(hydration): starting_kit loader with inherits + cycle detection

Flattens grants into a Vec<AdvancementEffect> and a separate
Vec<GrantRef> for GM-panel display. inherits: resolves across files
with cycle and missing-target hard failures. Unknown effect types
surface at hydration time, never at dispatch.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `character_resources:` loader + hydration

**Files:**
- Create: `sidequest-api/crates/sidequest-game/src/character_resources.rs`
- Create: `sidequest-api/crates/sidequest-game/tests/character_resources_tests.rs`
- Modify: `sidequest-api/crates/sidequest-game/src/lib.rs`

- [ ] **Step 1: Write the failing test**

```rust
// tests/character_resources_tests.rs
use sidequest_game::character_resources::{hydrate_character_resources, CharacterResourcesError};

fn th_rook_yaml() -> &'static str {
    r#"
character: { save_id: th_rook, name: "Th`rook" }
character_resources:
  - name: reniksnad
    label: Reniksnad
    min: 0
    max: 10
    starting: 7
    voluntary: false
    decay_per_scene: 1
    refill_trigger: narrator-authored dose event
    thresholds:
      - at: 5
        event_id: reniksnad_first_tremor
        narrator_hint: tremor
        direction: crossing_down
      - at: 3
        event_id: reniksnad_withdrawal
        narrator_hint: withdrawal
        direction: crossing_down
      - at: 0
        event_id: reniksnad_death_clock
        narrator_hint: death clock
        direction: crossing_down
"#
}

#[test]
fn hydrate_reniksnad_creates_pool_with_thresholds_and_starting_value() {
    let pools = hydrate_character_resources(th_rook_yaml()).unwrap();
    let reniksnad = pools.get("reniksnad").expect("reniksnad pool");
    assert_eq!(reniksnad.min(), 0);
    assert_eq!(reniksnad.max(), 10);
    assert_eq!(reniksnad.current(), 7);
    assert_eq!(reniksnad.thresholds().len(), 3);
}

#[test]
fn no_character_resources_block_is_fine() {
    let yaml = "character: { save_id: x, name: X }";
    let pools = hydrate_character_resources(yaml).unwrap();
    assert!(pools.is_empty());
}

#[test]
fn malformed_threshold_is_hard_error() {
    let yaml = r#"
character: { save_id: x, name: X }
character_resources:
  - name: oops
    min: 0
    max: 10
    starting: 5
    thresholds:
      - { at: "not-a-number", event_id: x, narrator_hint: x, direction: crossing_down }
"#;
    let err = hydrate_character_resources(yaml).unwrap_err();
    assert!(matches!(err, CharacterResourcesError::YamlParse { .. }));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test character_resources_tests`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the loader**

Create `sidequest-api/crates/sidequest-game/src/character_resources.rs`:

```rust
use crate::thresholds::{ResourcePool, Threshold, ThresholdDirection};
use serde::Deserialize;
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum CharacterResourcesError {
    #[error("YAML parse failure: {detail}")]
    YamlParse { detail: String },
}

#[derive(Debug, Deserialize)]
struct FileShape {
    #[serde(default)]
    character_resources: Vec<PoolYaml>,
}

#[derive(Debug, Deserialize)]
struct PoolYaml {
    name: String,
    #[serde(default)]
    label: Option<String>,
    min: i32,
    max: i32,
    starting: i32,
    #[serde(default)]
    voluntary: bool,
    #[serde(default)]
    decay_per_scene: Option<i32>,
    #[serde(default)]
    decay_per_turn: Option<i32>,
    #[serde(default)]
    refill_trigger: Option<String>,
    #[serde(default)]
    thresholds: Vec<ThresholdYaml>,
}

#[derive(Debug, Deserialize)]
struct ThresholdYaml {
    at: i32,
    event_id: String,
    narrator_hint: String,
    direction: ThresholdDirection,
}

pub fn hydrate_character_resources(
    yaml: &str,
) -> Result<HashMap<String, ResourcePool>, CharacterResourcesError> {
    let file: FileShape = serde_yaml::from_str(yaml).map_err(|e| {
        CharacterResourcesError::YamlParse { detail: e.to_string() }
    })?;

    let mut pools = HashMap::new();
    for p in file.character_resources {
        let mut pool = ResourcePool::new(p.min, p.max, p.starting);
        pool.set_label(p.label.unwrap_or_else(|| p.name.clone()));
        pool.set_voluntary(p.voluntary);
        if let Some(d) = p.decay_per_scene {
            pool.set_decay_per_scene(d);
        }
        if let Some(d) = p.decay_per_turn {
            pool.set_decay_per_turn(d);
        }
        if let Some(r) = p.refill_trigger {
            pool.set_refill_trigger(r);
        }
        for t in p.thresholds {
            pool.add_threshold(Threshold {
                at: t.at,
                event_id: t.event_id,
                narrator_hint: t.narrator_hint,
                direction: t.direction,
            });
        }
        pools.insert(p.name, pool);
    }
    Ok(pools)
}
```

If `ResourcePool` doesn't yet have the setters / `Threshold` shape referenced above, add minimal versions to `thresholds.rs`. Use `#[derive(Deserialize)]` on `ThresholdDirection` and derive or impl `Default` as needed.

Register module: add `pub mod character_resources;` to `lib.rs`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test character_resources_tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/character_resources.rs \
        sidequest-api/crates/sidequest-game/src/thresholds.rs \
        sidequest-api/crates/sidequest-game/tests/character_resources_tests.rs \
        sidequest-api/crates/sidequest-game/src/lib.rs
git commit -m "feat(character_resources): hydrate character-scoped ResourcePools

Reuses the existing ResourcePool struct; no new pool type. Reads the
character_resources: block from progression YAML, constructs one pool
per entry with thresholds wired. Malformed YAML fails loud.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Scene-end decay hook + threshold crossing events for character-scoped pools

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/character_resources.rs` (add `apply_scene_end_decay`)
- Modify: `sidequest-api/crates/sidequest-game/tests/character_resources_tests.rs` (add tests)
- Modify: `sidequest-api/crates/sidequest-game/src/scene.rs` (call decay hook on scene end)

- [ ] **Step 1: Write the failing test**

Append to `tests/character_resources_tests.rs`:

```rust
use sidequest_game::character_resources::apply_scene_end_decay;
use sidequest_game::creature_core::CreatureCore;

#[test]
fn scene_end_decay_decrements_pool_and_fires_threshold_event() {
    let mut cc = CreatureCore::default_for_tests();
    let pools = hydrate_character_resources(th_rook_yaml()).unwrap();
    cc.character_resources = pools;

    // Starts at 7, decays by 1/scene. After 2 scenes -> 5, crossing the 5-threshold.
    let events_scene_1 = apply_scene_end_decay(&mut cc);
    assert_eq!(cc.character_resources["reniksnad"].current(), 6);
    assert!(events_scene_1.is_empty(), "no threshold crossed yet");

    let events_scene_2 = apply_scene_end_decay(&mut cc);
    assert_eq!(cc.character_resources["reniksnad"].current(), 5);
    assert_eq!(events_scene_2.len(), 1);
    assert_eq!(events_scene_2[0].event_id, "reniksnad_first_tremor");
}

#[test]
fn decay_does_not_go_below_min() {
    let mut cc = CreatureCore::default_for_tests();
    let mut pools = hydrate_character_resources(th_rook_yaml()).unwrap();
    pools.get_mut("reniksnad").unwrap().set_current(0);
    cc.character_resources = pools;

    apply_scene_end_decay(&mut cc);
    assert_eq!(cc.character_resources["reniksnad"].current(), 0);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test character_resources_tests`
Expected: FAIL — `apply_scene_end_decay` missing.

- [ ] **Step 3: Implement `apply_scene_end_decay`**

Add to `character_resources.rs`:

```rust
use crate::creature_core::CreatureCore;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ThresholdCrossingEvent {
    pub creature_id: String,
    pub resource: String,
    pub from: i32,
    pub to: i32,
    pub event_id: String,
    pub direction: ThresholdDirection,
}

pub fn apply_scene_end_decay(cc: &mut CreatureCore) -> Vec<ThresholdCrossingEvent> {
    let mut events = Vec::new();
    let creature_id = cc.id().to_string();
    for (name, pool) in cc.character_resources.iter_mut() {
        if let Some(decay) = pool.decay_per_scene() {
            let from = pool.current();
            pool.decrement(decay);
            let to = pool.current();
            for t in pool.thresholds() {
                if crossed(from, to, t.at, t.direction) {
                    events.push(ThresholdCrossingEvent {
                        creature_id: creature_id.clone(),
                        resource: name.clone(),
                        from,
                        to,
                        event_id: t.event_id.clone(),
                        direction: t.direction,
                    });
                }
            }
        }
    }
    events
}

fn crossed(from: i32, to: i32, at: i32, direction: ThresholdDirection) -> bool {
    match direction {
        ThresholdDirection::CrossingDown => from > at && to <= at,
        ThresholdDirection::CrossingUp => from < at && to >= at,
    }
}
```

Expose on `ResourcePool` whatever setters / accessors the above uses (`current()`, `decrement(amount)`, `decay_per_scene()`, `thresholds()`). Add `CreatureCore::id()` if missing (returns `&str`).

In `scene.rs`, call `apply_scene_end_decay` on every active creature at scene boundary and forward events to the OTEL layer (Task 8 will add the spans).

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test character_resources_tests`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/character_resources.rs \
        sidequest-api/crates/sidequest-game/src/thresholds.rs \
        sidequest-api/crates/sidequest-game/src/creature_core.rs \
        sidequest-api/crates/sidequest-game/src/scene.rs \
        sidequest-api/crates/sidequest-game/tests/character_resources_tests.rs
git commit -m "feat(character_resources): scene-end decay + threshold crossing events

apply_scene_end_decay decrements each pool by decay_per_scene and
returns ThresholdCrossingEvents. Clamped at min. Scene boundary hook
invokes this on every active creature.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `resolved_beat_for` — day-1 five variants

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/advancement.rs` (add `resolved_beat_for`)
- Modify: `sidequest-api/crates/sidequest-game/tests/advancement_tests.rs` (add tests)

- [ ] **Step 1: Write the failing test**

Append to `advancement_tests.rs`:

```rust
use sidequest_game::advancement::resolved_beat_for;
use sidequest_game::beat::BeatDef;
use sidequest_game::creature_core::CreatureCore;

fn actor_with(effects: Vec<AdvancementEffect>) -> CreatureCore {
    let mut cc = CreatureCore::default_for_tests();
    cc.acquired_advancements = effects;
    cc
}

fn base_strike() -> BeatDef {
    BeatDef {
        id: "strike".into(),
        edge_delta: Some(-1),
        target_edge_delta: Some(-2),
        resource_deltas: Default::default(),
        ..BeatDef::default_for_tests()
    }
}

#[test]
fn beat_discount_reduces_edge_cost() {
    let cc = actor_with(vec![AdvancementEffect::BeatDiscount {
        beat_id: "strike".into(),
        edge_delta_mod: Some(1),  // +1 to edge_delta means less loss
        resource_mod: None,
    }]);
    let resolved = resolved_beat_for(&cc, &base_strike());
    assert_eq!(resolved.edge_delta, Some(0));  // -1 + 1 = 0
}

#[test]
fn leverage_bonus_increases_target_damage() {
    let cc = actor_with(vec![AdvancementEffect::LeverageBonus {
        beat_id: "strike".into(),
        target_edge_delta_mod: -1,  // -1 more damage
    }]);
    let resolved = resolved_beat_for(&cc, &base_strike());
    assert_eq!(resolved.target_edge_delta, Some(-3));
}

#[test]
fn non_matching_beat_id_is_unchanged() {
    let cc = actor_with(vec![AdvancementEffect::LeverageBonus {
        beat_id: "brace".into(),
        target_edge_delta_mod: -1,
    }]);
    let resolved = resolved_beat_for(&cc, &base_strike());
    assert_eq!(resolved.target_edge_delta, Some(-2));
}

#[test]
fn multiple_effects_stack_in_order() {
    let cc = actor_with(vec![
        AdvancementEffect::LeverageBonus { beat_id: "strike".into(), target_edge_delta_mod: -1 },
        AdvancementEffect::LeverageBonus { beat_id: "strike".into(), target_edge_delta_mod: -1 },
    ]);
    let resolved = resolved_beat_for(&cc, &base_strike());
    assert_eq!(resolved.target_edge_delta, Some(-4));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test advancement_tests`
Expected: FAIL — `resolved_beat_for` missing.

- [ ] **Step 3: Implement `resolved_beat_for` for the five day-1 variants**

Add to `advancement.rs`:

```rust
use crate::beat::BeatDef;
use crate::creature_core::CreatureCore;

pub fn resolved_beat_for(actor: &CreatureCore, beat: &BeatDef) -> BeatDef {
    let mut out = beat.clone();
    for eff in &actor.acquired_advancements {
        apply_effect(&mut out, eff);
    }
    out
}

fn apply_effect(beat: &mut BeatDef, eff: &AdvancementEffect) {
    match eff {
        AdvancementEffect::BeatDiscount { beat_id, edge_delta_mod, resource_mod } => {
            if beat.id != *beat_id { return; }
            if let (Some(cur), Some(m)) = (beat.edge_delta, *edge_delta_mod) {
                beat.edge_delta = Some(cur + m);
            }
            if let Some(rm) = resource_mod {
                for (k, v) in rm {
                    *beat.resource_deltas.entry(k.clone()).or_insert(0) += v;
                }
            }
        }
        AdvancementEffect::LeverageBonus { beat_id, target_edge_delta_mod } => {
            if beat.id != *beat_id { return; }
            if let Some(cur) = beat.target_edge_delta {
                beat.target_edge_delta = Some(cur + target_edge_delta_mod);
            }
        }
        AdvancementEffect::EdgeMaxBonus { .. }
        | AdvancementEffect::EdgeRecovery { .. }
        | AdvancementEffect::LoreRevealBonus { .. } => {
            // Passive — not applied at beat resolution.
        }
        AdvancementEffect::AllyEdgeIntercept { .. } => {
            // Reaction-dispatch variant. Handled in handle_applied_side_effects — not here.
        }
        AdvancementEffect::ConditionalEffectGating { .. } => {
            // Covered in Task 7.
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test advancement_tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/advancement.rs \
        sidequest-api/crates/sidequest-game/tests/advancement_tests.rs
git commit -m "feat(advancement): resolved_beat_for handles day-1 five variants

BeatDiscount and LeverageBonus modify the resolved BeatDef. EdgeMaxBonus,
EdgeRecovery, LoreRevealBonus are passive and skip resolution. AllyEdgeIntercept
is deferred to the reaction hook; ConditionalEffectGating to Task 7.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `resolved_beat_for` — `ConditionalEffectGating` with recursive resolution

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/advancement.rs`
- Modify: `sidequest-api/crates/sidequest-game/tests/advancement_tests.rs`

- [ ] **Step 1: Write the failing test**

```rust
// Append to advancement_tests.rs
use sidequest_game::advancement::{ConditionExpr, resolved_beat_for};
use sidequest_game::thresholds::ResourcePool;

fn th_rook_with_dose_helps(reniksnad_current: i32) -> CreatureCore {
    let mut cc = CreatureCore::default_for_tests();
    let mut pool = ResourcePool::new(0, 10, reniksnad_current);
    cc.character_resources.insert("reniksnad".into(), pool);
    cc.acquired_advancements = vec![AdvancementEffect::ConditionalEffectGating {
        condition: ConditionExpr::ResourceAbove {
            resource: "reniksnad".into(),
            threshold: 5,
        },
        when_true: Box::new(AdvancementEffect::BeatDiscount {
            beat_id: "commit_cost".into(),
            edge_delta_mod: None,
            resource_mod: Some([("flesh".into(), 1)].into_iter().collect()),
        }),
        when_false: Some(Box::new(AdvancementEffect::BeatDiscount {
            beat_id: "commit_cost".into(),
            edge_delta_mod: None,
            resource_mod: Some([("flesh".into(), -1)].into_iter().collect()),
        })),
    }];
    cc
}

fn base_commit_cost() -> BeatDef {
    BeatDef {
        id: "commit_cost".into(),
        edge_delta: Some(-1),
        target_edge_delta: None,
        resource_deltas: [("flesh".into(), -2)].into_iter().collect(),
        ..BeatDef::default_for_tests()
    }
}

#[test]
fn dose_helps_above_threshold_reduces_flesh_cost() {
    let cc = th_rook_with_dose_helps(7); // above 5
    let resolved = resolved_beat_for(&cc, &base_commit_cost());
    // Base -2 + when_true +1 = -1
    assert_eq!(resolved.resource_deltas.get("flesh"), Some(&-1));
}

#[test]
fn dose_helps_at_or_below_threshold_increases_flesh_cost() {
    let cc = th_rook_with_dose_helps(5); // not above
    let resolved = resolved_beat_for(&cc, &base_commit_cost());
    // Base -2 + when_false -1 = -3
    assert_eq!(resolved.resource_deltas.get("flesh"), Some(&-3));
}

#[test]
fn gating_with_when_false_none_is_noop_when_false() {
    let mut cc = th_rook_with_dose_helps(3);
    if let AdvancementEffect::ConditionalEffectGating { when_false, .. } =
        &mut cc.acquired_advancements[0]
    {
        *when_false = None;
    }
    let resolved = resolved_beat_for(&cc, &base_commit_cost());
    // Unchanged from base.
    assert_eq!(resolved.resource_deltas.get("flesh"), Some(&-2));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test advancement_tests`
Expected: FAIL — gating returns no-op.

- [ ] **Step 3: Extend `apply_effect` for the gating case**

In `advancement.rs`, replace the stub in `apply_effect`:

```rust
AdvancementEffect::ConditionalEffectGating { condition, when_true, when_false } => {
    if evaluate(condition, actor_context(beat)) { /* TODO: need creature state */ }
}
```

The cleanest shape is to thread the actor's `&CreatureCore` through `apply_effect`. Change signature:

```rust
fn apply_effect(beat: &mut BeatDef, eff: &AdvancementEffect, actor: &CreatureCore) {
    match eff {
        // ... existing arms unchanged apart from passing `actor` where needed
        AdvancementEffect::ConditionalEffectGating { condition, when_true, when_false } => {
            let active: Option<&AdvancementEffect> = if evaluate(condition, actor) {
                Some(when_true.as_ref())
            } else {
                when_false.as_deref()
            };
            if let Some(inner) = active {
                apply_effect(beat, inner, actor);
            }
        }
        _ => { /* other arms */ }
    }
}

fn evaluate(expr: &ConditionExpr, actor: &CreatureCore) -> bool {
    match expr {
        ConditionExpr::ResourceAbove { resource, threshold } => {
            actor.character_resources.get(resource).map(|p| p.current() > *threshold).unwrap_or(false)
        }
        ConditionExpr::ResourceAtOrBelow { resource, threshold } => {
            actor.character_resources.get(resource).map(|p| p.current() <= *threshold).unwrap_or(false)
        }
    }
}
```

Update `resolved_beat_for` call site to pass `actor` into `apply_effect`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test advancement_tests`
Expected: PASS (all 7+ tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/advancement.rs \
        sidequest-api/crates/sidequest-game/tests/advancement_tests.rs
git commit -m "feat(advancement): ConditionalEffectGating in resolved_beat_for

Evaluates ConditionExpr against actor's character_resources and recursively
applies either when_true or when_false. when_false: None is a no-op when the
condition is false. Missing resource defaults to false (never panics).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Reaction hook — `AllyEdgeIntercept` in `handle_applied_side_effects`

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/beat.rs`
- Create: `sidequest-api/crates/sidequest-game/tests/intercept_tests.rs`

- [ ] **Step 1: Write the failing test**

Create `tests/intercept_tests.rs`:

```rust
use sidequest_game::advancement::AdvancementEffect;
use sidequest_game::beat::{handle_applied_side_effects, TargetDebit};
use sidequest_game::creature_core::CreatureCore;

fn prot_thokk(edge: i32) -> CreatureCore {
    let mut cc = CreatureCore::default_for_tests_with_name("Prot'Thokk");
    cc.set_edge(edge);
    cc.set_max_edge(5);
    cc.acquired_advancements.push(AdvancementEffect::AllyEdgeIntercept {
        ally_whitelist: vec!["Cheeney".into(), "Lil'Sebastian".into()],
        max_redirect: 3,
    });
    cc
}

fn cheeney(edge: i32) -> CreatureCore {
    let mut cc = CreatureCore::default_for_tests_with_name("Cheeney");
    cc.set_edge(edge);
    cc.set_max_edge(3);
    cc
}

#[test]
fn intercept_redirects_ally_damage_to_actor() {
    let mut pt = prot_thokk(5);
    let mut ch = cheeney(3);
    let debit = TargetDebit { target: "Cheeney".into(), delta: -4 };

    let result = handle_applied_side_effects(&debit, &mut ch, &mut [&mut pt]);

    // Prot'Thokk absorbs 3, clamped edge down by 3: 5 -> 2
    assert_eq!(pt.edge(), 2);
    // Cheeney takes the remaining 1: 3 -> 2
    assert_eq!(ch.edge(), 2);
    assert_eq!(result.absorbed_delta, -3);
    assert_eq!(result.remainder, -1);
}

#[test]
fn intercept_clamps_actor_edge_to_one_minimum() {
    let mut pt = prot_thokk(2);  // only 2 Edge
    let mut ch = cheeney(3);
    let debit = TargetDebit { target: "Cheeney".into(), delta: -3 };

    let result = handle_applied_side_effects(&debit, &mut ch, &mut [&mut pt]);

    // Prot'Thokk clamped at 1. Edge change = 1 (2 -> 1), not 3.
    assert_eq!(pt.edge(), 1);
    // Cheeney takes the rest: 3 - 2 = 1
    assert_eq!(ch.edge(), 1);
    assert_eq!(result.absorbed_delta, -1);
    assert_eq!(result.remainder, -2);
}

#[test]
fn intercept_does_not_fire_when_ally_not_whitelisted() {
    let mut pt = prot_thokk(5);
    let mut hant = CreatureCore::default_for_tests_with_name("Hant");
    hant.set_edge(3);
    hant.set_max_edge(3);
    let debit = TargetDebit { target: "Hant".into(), delta: -2 };

    let result = handle_applied_side_effects(&debit, &mut hant, &mut [&mut pt]);

    assert_eq!(pt.edge(), 5);         // untouched
    assert_eq!(hant.edge(), 1);       // took full hit
    assert_eq!(result.absorbed_delta, 0);
    assert_eq!(result.remainder, -2);
}

#[test]
fn first_matching_interceptor_wins() {
    let mut pt_a = prot_thokk(5);
    let mut pt_b = prot_thokk(5);
    let mut ch = cheeney(3);
    let debit = TargetDebit { target: "Cheeney".into(), delta: -4 };

    let result = handle_applied_side_effects(&debit, &mut ch, &mut [&mut pt_a, &mut pt_b]);

    // First interceptor absorbs; second is untouched.
    assert_eq!(pt_a.edge(), 2);
    assert_eq!(pt_b.edge(), 5);
    assert_eq!(result.absorbed_delta, -3);
    assert_eq!(result.remainder, -1);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-game --test intercept_tests`
Expected: FAIL — `handle_applied_side_effects` does not yet take an interceptor list, or `TargetDebit` return type differs.

- [ ] **Step 3: Extend `handle_applied_side_effects`**

In `beat.rs`, extend (or wrap) the existing target-debit block. Shape the public signature:

```rust
pub struct TargetDebit {
    pub target: String,
    pub delta: i32,
}

pub struct InterceptOutcome {
    pub absorbed_delta: i32,
    pub remainder: i32,
    pub interceptor: Option<String>,
}

pub fn handle_applied_side_effects(
    debit: &TargetDebit,
    target: &mut CreatureCore,
    potential_interceptors: &mut [&mut CreatureCore],
) -> InterceptOutcome {
    for interceptor in potential_interceptors.iter_mut() {
        if let Some((absorbed, remainder)) = try_intercept(debit, interceptor) {
            apply_edge_delta(target, remainder);
            return InterceptOutcome {
                absorbed_delta: absorbed,
                remainder,
                interceptor: Some(interceptor.name().to_string()),
            };
        }
    }
    apply_edge_delta(target, debit.delta);
    InterceptOutcome { absorbed_delta: 0, remainder: debit.delta, interceptor: None }
}

fn try_intercept(debit: &TargetDebit, interceptor: &mut CreatureCore) -> Option<(i32, i32)> {
    for eff in &interceptor.acquired_advancements {
        if let AdvancementEffect::AllyEdgeIntercept { ally_whitelist, max_redirect } = eff {
            let matches = ally_whitelist.is_empty() || ally_whitelist.iter().any(|a| a == &debit.target);
            if !matches { continue; }
            let want = debit.delta.abs().min(*max_redirect as i32);
            let actor_edge = interceptor.edge();
            let can_take = (actor_edge - 1).max(0); // clamp-to-1 minimum
            let absorbed_abs = want.min(can_take);
            interceptor.set_edge(actor_edge - absorbed_abs);
            let absorbed = -absorbed_abs;
            let remainder = debit.delta - absorbed;
            return Some((absorbed, remainder));
        }
    }
    None
}

fn apply_edge_delta(creature: &mut CreatureCore, delta: i32) {
    creature.set_edge((creature.edge() + delta).max(0));
}
```

Callers that currently invoke the target-debit block must pass a `potential_interceptors` slice. Typical call site: `Vec<&mut CreatureCore>` built from the actor's party minus the target.

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-game --test intercept_tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-game/src/beat.rs \
        sidequest-api/crates/sidequest-game/tests/intercept_tests.rs
git commit -m "feat(beat): reaction hook for AllyEdgeIntercept in target-debit

Scans potential_interceptors before applying target_edge_delta to the
original target; first matching interceptor absorbs up to max_redirect
with actor Edge clamped to 1 minimum. Remainder flows through to the
target as normal. No action or initiative cost.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: OTEL spans for advancement + character_resources

**Files:**
- Modify: `sidequest-api/crates/sidequest-telemetry/src/spans.rs`
- Modify: `sidequest-api/crates/sidequest-game/src/advancement.rs` (emit from resolution)
- Modify: `sidequest-api/crates/sidequest-game/src/character_resources.rs` (emit from decay)
- Modify: `sidequest-api/crates/sidequest-game/src/beat.rs` (emit from intercept)
- Create: `sidequest-api/tests/otel_span_tests.rs`

- [ ] **Step 1: Write the failing test**

Create `sidequest-api/tests/otel_span_tests.rs`:

```rust
use sidequest_telemetry::spans::{test_span_recorder, SpanKind};

#[test]
fn intercept_emits_ally_edge_intercept_span() {
    let recorder = test_span_recorder();
    // (reuse the Prot'Thokk / Cheeney setup from intercept_tests via a shared helper)
    run_prot_thokk_intercept_scenario();
    let spans = recorder.spans();
    assert!(spans.iter().any(|s| s.kind == SpanKind::AdvancementAllyEdgeIntercept));
    let span = spans.iter().find(|s| s.kind == SpanKind::AdvancementAllyEdgeIntercept).unwrap();
    assert_eq!(span.field_str("actor"), Some("Prot'Thokk"));
    assert_eq!(span.field_str("ally"), Some("Cheeney"));
    assert_eq!(span.field_i32("absorbed_delta"), Some(-3));
}

#[test]
fn conditional_gating_emits_span_with_evaluated_and_applied_variant() {
    let recorder = test_span_recorder();
    run_th_rook_dose_helps_above_threshold();
    let span = recorder.spans().into_iter()
        .find(|s| s.kind == SpanKind::AdvancementConditionalEffectGating)
        .expect("gating span");
    assert_eq!(span.field_bool("evaluated"), Some(true));
    assert_eq!(span.field_str("applied_variant"), Some("when_true"));
}

#[test]
fn scene_end_decay_emits_one_span_per_creature_per_pool() {
    let recorder = test_span_recorder();
    run_th_rook_one_scene_decay();
    let spans = recorder.spans();
    assert_eq!(spans.iter().filter(|s| s.kind == SpanKind::CharacterResourceDecayed).count(), 1);
}

#[test]
fn threshold_crossing_emits_dedicated_span() {
    let recorder = test_span_recorder();
    run_th_rook_decay_to_five();
    assert!(recorder.spans().iter().any(|s| s.kind == SpanKind::CharacterResourceThresholdCrossed));
}
```

The helper `run_*_scenario()` functions set up the same state the earlier unit tests did but run through the real pipeline. Extract shared fixture builders into `tests/common/mod.rs` to avoid duplication.

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-api --test otel_span_tests`
Expected: FAIL — span kinds missing and/or never emitted.

- [ ] **Step 3: Add span kinds + emission**

In `sidequest-api/crates/sidequest-telemetry/src/spans.rs`, extend `SpanKind`:

```rust
pub enum SpanKind {
    // ... existing
    AdvancementEffectResolved,
    AdvancementAllyEdgeIntercept,
    AdvancementAllyEdgeInterceptSkipped,
    AdvancementConditionalEffectGating,
    CharacterResourceThresholdCrossed,
    CharacterResourceDecayed,
}
```

Emit from each site:
- In `resolved_beat_for`'s `apply_effect`: emit `AdvancementEffectResolved` for BeatDiscount and LeverageBonus arms (the passive arms do not emit).
- In `apply_effect` ConditionalEffectGating arm: emit `AdvancementConditionalEffectGating` with fields `{ actor, condition, evaluated, applied_variant }`.
- In `try_intercept` hit path: emit `AdvancementAllyEdgeIntercept` with `{ actor, ally, original_delta, absorbed_delta, remainder, actor_edge_after }`.
- When an interceptor is present but no match fires: emit `AdvancementAllyEdgeInterceptSkipped` with `{ actor, reason }` at TRACE level.
- In `apply_scene_end_decay`: emit `CharacterResourceDecayed` per pool with `{ creature, resource, from, to, decay_per_scene }`, then `CharacterResourceThresholdCrossed` per crossing with `{ creature, resource, from, to, event_id, direction }`.

Use the existing `tracing::span!` / telemetry macros (whatever pattern `sidequest-telemetry` already uses for other spans — follow the existing convention).

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-api --test otel_span_tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-telemetry/src/spans.rs \
        sidequest-api/crates/sidequest-game/src/advancement.rs \
        sidequest-api/crates/sidequest-game/src/character_resources.rs \
        sidequest-api/crates/sidequest-game/src/beat.rs \
        sidequest-api/tests/otel_span_tests.rs \
        sidequest-api/tests/common/mod.rs
git commit -m "feat(telemetry): six new OTEL spans for advancement + character_resources

AdvancementEffectResolved, AllyEdgeIntercept (+Skipped),
ConditionalEffectGating, CharacterResourceDecayed,
CharacterResourceThresholdCrossed. Every advancement decision and
pool mutation emits a span — no silent behavior per CLAUDE.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Wire hydration into chargen

**Files:**
- Modify: `sidequest-api/crates/sidequest-genre/src/loader.rs` (or wherever chargen composes a `CreatureCore`)
- Modify: whatever test covers chargen composition

- [ ] **Step 1: Write the failing test**

Add to the existing chargen test module (find via `grep -rn "fn.*chargen" sidequest-api/crates/`):

```rust
#[test]
fn chargen_hydrates_starting_kit_and_character_resources_for_th_rook() {
    let genre_pack_path = std::path::Path::new("../../sidequest-content/genre_packs/heavy_metal");
    let world = "evropi";
    let cc = chargen_compose(genre_pack_path, world, "th_rook").unwrap();

    assert_eq!(cc.acquired_grants.len(), 3);
    assert!(cc.acquired_grants.iter().any(|g| g.id == "knotsung_name"));
    assert!(cc.acquired_grants.iter().any(|g| g.id == "the_dose_helps"));
    assert_eq!(cc.acquired_advancements.len(), 3);

    let reniksnad = cc.character_resources.get("reniksnad").unwrap();
    assert_eq!(reniksnad.current(), 7);
    assert_eq!(reniksnad.thresholds().len(), 3);
}

#[test]
fn chargen_inherits_rux_kit_for_ludzo() {
    let genre_pack_path = std::path::Path::new("../../sidequest-content/genre_packs/heavy_metal");
    let rux = chargen_compose(genre_pack_path, "evropi", "rux").unwrap();
    let ludzo = chargen_compose(genre_pack_path, "evropi", "ludzo").unwrap();
    assert_eq!(rux.acquired_advancements, ludzo.acquired_advancements);
    assert_eq!(rux.acquired_grants, ludzo.acquired_grants);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-genre chargen_hydrates_starting_kit`
Expected: FAIL — chargen doesn't populate the new fields.

- [ ] **Step 3: Wire the two hydration calls**

In the chargen composer (existing function that builds a `CreatureCore` from genre pack + world + save_id), add after the existing CreatureCore construction:

```rust
use sidequest_game::advancement_hydration::{hydrate_starting_kit, ProgressionFiles};
use sidequest_game::character_resources::hydrate_character_resources;

let progression_dir = genre_pack_path
    .join("worlds").join(world)
    .join("_drafts").join("character-progression");
let files = ProgressionFiles::from_dir(&progression_dir)?;

let (effects, grants) = hydrate_starting_kit(save_id, &files)?;
cc.acquired_advancements = effects;
cc.acquired_grants = grants;

let raw = std::fs::read_to_string(progression_dir.join(format!("{save_id}.yaml")))?;
cc.character_resources = hydrate_character_resources(&raw)?;
```

Error propagation: hydration errors should bubble up as chargen errors with context (use `anyhow` or the chargen error enum already in use). No silent fallback — per CLAUDE.md "no silent fallbacks".

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-genre chargen_hydrates_starting_kit`
Run: `cargo test -p sidequest-genre chargen_inherits_rux_kit_for_ludzo`
Expected: PASS both.

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/crates/sidequest-genre/src/loader.rs \
        sidequest-api/crates/sidequest-genre/tests/chargen_tests.rs
git commit -m "feat(chargen): hydrate starting_kit + character_resources from progression YAML

Chargen reads genre_packs/.../worlds/<world>/_drafts/character-progression/<id>.yaml,
hydrates acquired_advancements + acquired_grants + character_resources on the
CreatureCore. Hydration errors fail chargen loud — no silent fallbacks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Integration test — Prot'Thokk intercept + Th`rook dose flip (real wiring)

**Files:**
- Create: `sidequest-api/tests/adr_081_integration_tests.rs`
- Create: `sidequest-api/tests/fixtures/adr_081/scenario_prot_thokk_defends.md` (human-readable, for reference)

- [ ] **Step 1: Write the failing integration test**

```rust
// adr_081_integration_tests.rs
use sidequest_api::dispatch::{DispatchContext, apply_beat_dispatch};
use sidequest_game::chargen::chargen_compose;
use std::path::Path;

const GENRE_PACK: &str = "../sidequest-content/genre_packs/heavy_metal";

#[test]
fn prot_thokk_intercepts_hit_on_cheeney_via_live_dispatch() {
    let genre_pack = Path::new(GENRE_PACK);
    let mut pt = chargen_compose(genre_pack, "evropi", "prot_thokk").unwrap();
    let mut cheeney = fixture_cheeney();
    let mut enemy = fixture_orc_raider();

    let mut ctx = DispatchContext::new()
        .with_active(vec![pt.clone(), cheeney.clone(), enemy.clone()]);

    // Enemy beat targeting Cheeney with -4 target_edge_delta
    let result = apply_beat_dispatch(
        &mut ctx,
        &enemy,
        "strike",
        Some("Cheeney"),
    ).unwrap();

    assert!(result.intercepts.iter().any(|i| i.interceptor.as_deref() == Some("Prot'Thokk")));
    let pt_after = ctx.creature("Prot'Thokk").unwrap();
    let ch_after = ctx.creature("Cheeney").unwrap();
    assert!(pt_after.edge() < pt.edge()); // absorbed
    assert!(ch_after.edge() > cheeney.edge() - 4); // took less than the full hit
}

#[test]
fn th_rook_dose_helps_flips_sign_across_reniksnad_threshold_via_dispatch() {
    let genre_pack = Path::new(GENRE_PACK);
    let mut th_rook = chargen_compose(genre_pack, "evropi", "th_rook").unwrap();
    // Starts at 7 (above 5) — when_true branch active.
    let mut ctx = DispatchContext::new().with_active(vec![th_rook.clone()]);

    let result_before = apply_beat_dispatch(&mut ctx, &th_rook, "commit_cost", None).unwrap();
    let flesh_before = ctx.creature("Th`rook").unwrap().resource_total("flesh");

    // Drop reniksnad to 5 via two scene-ends (decay 1/scene).
    ctx.end_scene();
    ctx.end_scene();
    assert_eq!(ctx.creature("Th`rook").unwrap().character_resources["reniksnad"].current(), 5);

    let result_after = apply_beat_dispatch(&mut ctx, &th_rook, "commit_cost", None).unwrap();
    let flesh_after = ctx.creature("Th`rook").unwrap().resource_total("flesh");

    // The same beat resolves to a worse flesh cost post-threshold.
    assert!(flesh_after < flesh_before, "flesh_before={flesh_before} flesh_after={flesh_after}");
}
```

The scenarios rely on real `DispatchContext + apply_beat_dispatch`, per story 39-7's "real wiring test" pattern. If those fixture/helper functions don't yet exist in the chosen shape, create thin stubs alongside this test — the goal is to exercise the actual dispatch path, not a regex source match.

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p sidequest-api --test adr_081_integration_tests`
Expected: FAIL — scenarios not yet green through real dispatch.

- [ ] **Step 3: Wire up any missing glue to make the tests green**

Likely needs: a chargen helper re-export at `sidequest_game::chargen`; `DispatchContext::with_active` / `::end_scene` / `::creature` accessors; `CreatureCore::resource_total` summing genre + character pools. Add the minimum glue required for these tests to exercise the real pipeline.

No new subsystems. If something seems to require a new subsystem, stop — it's out of scope.

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p sidequest-api --test adr_081_integration_tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-api/tests/adr_081_integration_tests.rs \
        sidequest-api/tests/fixtures/adr_081/
git commit -m "test(adr_081): real-wiring integration — intercept + conditional flip

Exercises the full DispatchContext + apply_beat_dispatch path for
Prot'Thokk intercepting a hit on Cheeney and Th'rook's The Dose Helps
flipping flesh cost as reniksnad decays across the 5-threshold. Per
story 39-7's real-wiring-test mandate (no regex source matching).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Playtest fixtures for story 39-8 acceptance gate

**Files:**
- Create: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/playtest_fixtures/prot_thokk_intercept.md`
- Create: `sidequest-content/genre_packs/heavy_metal/worlds/evropi/playtest_fixtures/th_rook_dose_flip.md`

- [ ] **Step 1: Write Prot'Thokk intercept scenario fixture**

Create `sidequest-content/genre_packs/heavy_metal/worlds/evropi/playtest_fixtures/prot_thokk_intercept.md`:

```markdown
# Playtest Fixture — Prot'Thokk Defends Cheeney

**Acceptance criterion:** Sebastien-facing GM panel shows a `advancement.ally_edge_intercept` span with correct arithmetic during live play.

## Setup

- Party: Prot'Thokk (heavy_metal fighter, Edge 5 / 5), Cheeney (NPC ally, Edge 3 / 3).
- Encounter: 1 Orc Raider (basic heavy_metal enemy).

## Scripted beat

1. Orc Raider's turn. Raider selects `strike` with `target_edge_delta: -4`, targeting Cheeney.
2. Dispatch fires the AllyEdgeIntercept reaction on Prot'Thokk.
3. Expected state after:
   - Prot'Thokk Edge: 5 → 2
   - Cheeney Edge: 3 → 2
   - GM panel shows `advancement.ally_edge_intercept` with `{actor: Prot'Thokk, ally: Cheeney, original_delta: -4, absorbed_delta: -3, remainder: -1, actor_edge_after: 2}`.

## Narrator SOUL §12 check

Narrator prose must describe Prot'Thokk *interposing* — not Cheeney being hit in full. The mechanical truth is that Prot'Thokk took most of it; the narration must reflect that.

## Failure modes

- Narrator describes Cheeney taking the full hit → wiring broken or narrator is improvising (run narrator-wiring check).
- No OTEL span → reaction hook not firing in dispatch path.
- Prot'Thokk Edge = 0 or negative → clamp-to-1 broken.
```

- [ ] **Step 2: Write Th`rook dose-flip scenario fixture**

Create `sidequest-content/genre_packs/heavy_metal/worlds/evropi/playtest_fixtures/th_rook_dose_flip.md`:

```markdown
# Playtest Fixture — Th`rook Reniksnad Threshold Flip

**Acceptance criterion:** Sebastien-facing GM panel shows the reniksnad threshold crossing and the conditional-gating flip on the next commit_cost beat.

## Setup

- Party: Th`rook (Pakook`rook Warlock, reniksnad starting 7).
- Encounter: ritual-type, not combat. Any `pact_working` ConfrontationDef works.

## Scripted sequence

1. Scene 1: Th`rook uses `commit_cost` beat with base flesh cost -2.
   - `ConditionalEffectGating` condition `resource_above reniksnad 5` is true.
   - when_true branch active: `beat_discount commit_cost flesh: 1`.
   - Resolved flesh delta: -1 (base -2 + mod +1).
   - GM panel shows `advancement.conditional_effect_gating { evaluated: true, applied_variant: when_true }`.
2. Scene ends. reniksnad decays 7 → 6. No threshold crossed; `character_resource.decayed` span only.
3. Scene 2 ends. reniksnad decays 6 → 5. Crosses at=5 threshold.
   - GM panel shows `character_resource.threshold_crossed { from: 6, to: 5, event_id: reniksnad_first_tremor, direction: crossing_down }`.
   - Narrator receives `reniksnad_first_tremor` KnownFact.
4. Scene 3: Th`rook uses `commit_cost` again.
   - Condition now false (reniksnad = 5, not > 5).
   - when_false branch: `beat_discount commit_cost flesh: -1`.
   - Resolved flesh delta: -3 (base -2 + mod -1).
   - GM panel shows gating span with `evaluated: false, applied_variant: when_false`.

## Narrator SOUL §12 check

At the threshold crossing, narrator prose describes the tremor — not the party noticing automatically. Scene-2 narration can cue informers (Wazdia) seeing it; scene-3 withdrawal narration can describe Th`rook pushing through it, not choosing to.

## Failure modes

- No flip at reniksnad = 5 → gating not evaluating or resource lookup broken.
- Narrator adds or omits flavor from KnownFact → narrator KnownFact injection broken (pre-existing ADR-078 concern, not ADR-081 scope).
- No decay on scene end → scene-end hook not wired.
```

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/heavy_metal/worlds/evropi/playtest_fixtures/
git commit -m "content(evropi): playtest fixtures for ADR-081 acceptance gate

Two scripted scenarios for story 39-8's acceptance playtest — Prot'Thokk
intercepting a hit on Cheeney, and Th'rook's The Dose Helps flipping sign
across the reniksnad=5 threshold. Each fixture lists expected state, GM
panel spans, and SOUL §12 narration failure modes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
cd ..
```

---

## Final verification

- [ ] **Step 1: Full workspace test**

Run: `cargo test --workspace`
Expected: All green.

- [ ] **Step 2: Lint gate**

Run: `cargo fmt --check && cargo clippy --workspace -- -D warnings`
Expected: Clean.

- [ ] **Step 3: YAML parse audit (all evropi characters)**

Run:
```bash
cd sidequest-content
for f in genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/*.yaml; do
    python3 -c "import yaml; yaml.safe_load(open('$f'))" && echo "  OK: $(basename $f)"
done
```
Expected: All six print `OK`.

- [ ] **Step 4: Chargen smoke — all six characters hydrate cleanly**

Run: `cargo test -p sidequest-genre chargen_hydrates_all_evropi_characters -- --nocapture` (add this test if missing — iterate over the six save_ids and assert `chargen_compose` returns `Ok`).

- [ ] **Step 5: Summary commit (optional)**

If any incidental fixes were made during verification, commit them with a tight message. Otherwise skip.

---

## Summary

12 task commits + final verification. Delivers:

- Seven `AdvancementEffect` variants and `ConditionExpr` grammar
- `CreatureCore` extended with `acquired_advancements`, `acquired_grants`, `character_resources`
- `starting_kit` hydration with `inherits:` resolution and cycle detection
- `character_resources` hydration with scene-end decay and threshold crossing events
- `resolved_beat_for` covering six variants (five day-1 + `ConditionalEffectGating`)
- Reaction hook in `handle_applied_side_effects` for `AllyEdgeIntercept`
- Six OTEL span kinds, emitted on every decision path
- Chargen wiring for all six Evropi characters (including Ludzo inheritance)
- Real-wiring integration tests for both ADR-081 variants
- Two playtest fixtures for story 39-8's acceptance gate

On completion, Prot'Thokk and Th`rook are mechanically distinct at turn one in live dispatch, with full GM-panel visibility. ADR-081 variants are exercised end-to-end. Story 39-5 ships with expanded scope (~16-18 pts).
