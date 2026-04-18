# Layered Content Model — Phase 1: Framework + Archetypes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the four-tier resolver framework (`Global → Genre → World → Culture`) with Provenance tracking and OTEL spans, wired end-to-end through the archetype axis as the reference consumer. Old archetype loader deleted in the same PR so there is never a coexistence window.

**Architecture:** A new generic `Resolver<T>` in `sidequest-genre` walks the four-tier chain producing `Resolved<T>` with full `Provenance`. Per-tier schema types (`GlobalContent`, `GenreContent`, `WorldContent`, `CultureContent`) enforce discipline via the Rust type system and serde's `deny_unknown_fields`. A `Layered` derive macro annotates fields with their merge strategy. Archetype resolution migrates from `archetype_resolve.rs` to the new Resolver; the old function is deleted in the same PR. Provenance rides on `GameMessage` through the wire, and a new GM-panel component renders it.

**Tech Stack:** Rust (`sidequest-api` workspace), `sidequest-telemetry` (existing OTEL), `serde_yaml`, `proc-macro2`/`syn`/`quote` (Layered derive), TypeScript/React (`sidequest-ui`), vitest, `cargo nextest`.

**Spec:** `docs/superpowers/specs/2026-04-17-layered-content-model-design.md`

**Follows (reference model):** `docs/superpowers/specs/2026-04-16-three-axis-archetype-system-design.md` — three-axis archetypes are the existing resolution that migrates onto this framework.

**Phases 2–6 are out of scope for this plan.** Each gets its own plan when Phase 1 lands.

---

## File Structure

### New files (sidequest-api)

- `crates/sidequest-genre/src/resolver/mod.rs` — `Resolver<T>` public API
- `crates/sidequest-genre/src/resolver/resolved.rs` — `Resolved<T>`, `Provenance`, `Tier`, `Span`, `MergeStep`, `ContributionKind`
- `crates/sidequest-genre/src/resolver/merge.rs` — `MergeStrategy` enum and helpers
- `crates/sidequest-genre/src/resolver/load.rs` — per-tier file loading with `deny_unknown_fields`
- `crates/sidequest-genre/src/resolver/otel.rs` — `content.resolve` span emission helpers
- `crates/sidequest-genre/src/schema/mod.rs` — schema module root
- `crates/sidequest-genre/src/schema/global.rs` — `GlobalContent`
- `crates/sidequest-genre/src/schema/genre.rs` — `GenreContent`
- `crates/sidequest-genre/src/schema/world.rs` — `WorldContent`
- `crates/sidequest-genre/src/schema/culture.rs` — `CultureContent`
- `crates/sidequest-genre-layered-derive/Cargo.toml` — new proc-macro crate
- `crates/sidequest-genre-layered-derive/src/lib.rs` — `#[derive(Layered)]` impl
- `crates/sidequest-genre/tests/resolver_unit.rs`
- `crates/sidequest-genre/tests/resolver_integration.rs`
- `crates/sidequest-genre/tests/iron_foundry_regression.rs`
- `crates/sidequest-genre/tests/fixtures/heavy_metal_evropi/...` — fixture tree

### Modified files (sidequest-api)

- `Cargo.toml` (workspace) — add `sidequest-genre-layered-derive`
- `crates/sidequest-genre/Cargo.toml` — deps: `sidequest-genre-layered-derive`, `sidequest-telemetry`
- `crates/sidequest-genre/src/lib.rs` — export `resolver::*`, `schema::*`
- `crates/sidequest-genre/src/archetype_resolve.rs` — **deleted** in Task F4
- `crates/sidequest-protocol/src/lib.rs` — add `Provenance`, extend content-carrying `GameMessage` variants
- `crates/sidequest-game/src/character.rs` — hold `Resolved<ArchetypeResolved>` instead of `ResolvedArchetype`
- `crates/sidequest-server/src/dispatch/archetype.rs` (or wherever `resolve_archetype` is called) — call through `Resolver<ArchetypeResolved>`

### New files (sidequest-ui)

- `src/types/provenance.ts` — `Provenance`, `Tier`, `MergeStep` TS types
- `src/hooks/useProvenance.ts` — subscribe to `content.resolve` OTEL stream or message provenance
- `src/components/GMPanel/ProvenanceInspector.tsx`
- `src/components/GMPanel/ProvenanceInspector.test.tsx`

### Modified files (sidequest-ui)

- `src/components/GMPanel/index.tsx` — mount inspector
- `src/types/messages.ts` (or equivalent) — extend message types with optional `provenance` field

---

## Phase A — Provenance and `Resolved<T>` Types

The provenance types are the spine of the whole framework. Write them first so later tasks can import them.

### Task A1: Define `Tier` and `Span`

**Files:**
- Create: `crates/sidequest-genre/src/resolver/mod.rs`
- Create: `crates/sidequest-genre/src/resolver/resolved.rs`

- [ ] **Step 1: Write failing test for `Tier` serialization**

File: `crates/sidequest-genre/tests/resolver_unit.rs`

```rust
use sidequest_genre::resolver::{Span, Tier};

#[test]
fn tier_serializes_lowercase() {
    assert_eq!(serde_json::to_string(&Tier::Global).unwrap(), "\"global\"");
    assert_eq!(serde_json::to_string(&Tier::Genre).unwrap(), "\"genre\"");
    assert_eq!(serde_json::to_string(&Tier::World).unwrap(), "\"world\"");
    assert_eq!(serde_json::to_string(&Tier::Culture).unwrap(), "\"culture\"");
}

#[test]
fn span_roundtrips() {
    let s = Span { start_line: 12, start_col: 1, end_line: 18, end_col: 0 };
    let json = serde_json::to_string(&s).unwrap();
    let back: Span = serde_json::from_str(&json).unwrap();
    assert_eq!(s, back);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo nextest run -p sidequest-genre --test resolver_unit -- tier_serializes_lowercase span_roundtrips`
Expected: FAIL — module `resolver` does not exist.

- [ ] **Step 3: Write minimal implementation**

File: `crates/sidequest-genre/src/resolver/mod.rs`

```rust
//! Four-tier content resolver: Global -> Genre -> World -> Culture.
//!
//! Every resolution emits an OTEL `content.resolve` span and produces a
//! `Resolved<T>` carrying full provenance.

pub mod resolved;

pub use resolved::{ContributionKind, MergeStep, Provenance, Resolved, Span, Tier};
```

File: `crates/sidequest-genre/src/resolver/resolved.rs`

```rust
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Content-inheritance tier. Always walked in this order: Global, Genre, World, Culture.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Tier {
    Global,
    Genre,
    World,
    Culture,
}

/// Line range in a YAML source file.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Span {
    pub start_line: u32,
    pub start_col: u32,
    pub end_line: u32,
    pub end_col: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContributionKind {
    Initial,
    Replaced,
    Appended,
    Merged,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MergeStep {
    pub tier: Tier,
    pub file: PathBuf,
    pub span: Option<Span>,
    pub contribution: ContributionKind,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Provenance {
    pub source_tier: Tier,
    pub source_file: PathBuf,
    pub source_span: Option<Span>,
    pub merge_trail: Vec<MergeStep>,
}

#[derive(Debug, Clone)]
pub struct Resolved<T> {
    pub value: T,
    pub provenance: Provenance,
}
```

Add `pub mod resolver;` and `pub use resolver::*;` to `crates/sidequest-genre/src/lib.rs`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo nextest run -p sidequest-genre --test resolver_unit`
Expected: PASS — 2 tests green.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/resolver crates/sidequest-genre/src/lib.rs \
        crates/sidequest-genre/tests/resolver_unit.rs
git commit -m "feat(genre): add resolver tier, span, and provenance types"
```

### Task A2: `Provenance` round-trip test

**Files:**
- Modify: `crates/sidequest-genre/tests/resolver_unit.rs`

- [ ] **Step 1: Add failing round-trip test**

Append to `resolver_unit.rs`:

```rust
use sidequest_genre::resolver::{ContributionKind, MergeStep, Provenance};
use std::path::PathBuf;

#[test]
fn provenance_round_trips_through_json() {
    let prov = Provenance {
        source_tier: Tier::World,
        source_file: PathBuf::from("worlds/evropi/archetype_funnels.yaml"),
        source_span: Some(Span { start_line: 12, start_col: 1, end_line: 18, end_col: 0 }),
        merge_trail: vec![
            MergeStep {
                tier: Tier::Genre,
                file: PathBuf::from("heavy_metal/archetype_constraints.yaml"),
                span: Some(Span { start_line: 3, start_col: 1, end_line: 9, end_col: 0 }),
                contribution: ContributionKind::Initial,
            },
            MergeStep {
                tier: Tier::World,
                file: PathBuf::from("worlds/evropi/archetype_funnels.yaml"),
                span: Some(Span { start_line: 12, start_col: 1, end_line: 18, end_col: 0 }),
                contribution: ContributionKind::Replaced,
            },
        ],
    };
    let json = serde_json::to_string(&prov).unwrap();
    let back: Provenance = serde_json::from_str(&json).unwrap();
    assert_eq!(prov, back);
}
```

- [ ] **Step 2: Run test — expect PASS** (no new types needed; just verifying round-trip works).

Run: `cargo nextest run -p sidequest-genre --test resolver_unit -- provenance_round_trips_through_json`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add crates/sidequest-genre/tests/resolver_unit.rs
git commit -m "test(genre): provenance round-trips through json"
```

---

## Phase B — Per-Tier Schema Types

Four distinct struct types — the discipline spine. Each uses `#[serde(deny_unknown_fields)]` so mis-tiered content fails to load.

### Task B1: `GlobalContent` skeleton

**Files:**
- Create: `crates/sidequest-genre/src/schema/mod.rs`
- Create: `crates/sidequest-genre/src/schema/global.rs`

- [ ] **Step 1: Write failing parsing test**

File: `crates/sidequest-genre/tests/schema_unit.rs`

```rust
use sidequest_genre::schema::global::GlobalContent;

#[test]
fn global_content_parses_minimal() {
    let yaml = r#"
jungian_axis: []
rpg_role_axis: []
npc_role_axis: []
"#;
    let parsed: GlobalContent = serde_yaml::from_str(yaml).unwrap();
    assert!(parsed.jungian_axis.is_empty());
    assert!(parsed.rpg_role_axis.is_empty());
    assert!(parsed.npc_role_axis.is_empty());
}

#[test]
fn global_content_rejects_unknown_field() {
    let yaml = r#"
jungian_axis: []
rpg_role_axis: []
npc_role_axis: []
funnels: []
"#;
    let result: Result<GlobalContent, _> = serde_yaml::from_str(yaml);
    let err = result.unwrap_err().to_string();
    assert!(err.contains("funnels"), "expected error naming 'funnels', got: {err}");
}
```

- [ ] **Step 2: Run — expect fail (no module yet)**

Run: `cargo nextest run -p sidequest-genre --test schema_unit`
Expected: FAIL — unresolved module `schema`.

- [ ] **Step 3: Implement**

File: `crates/sidequest-genre/src/schema/mod.rs`

```rust
//! Per-tier content schemas. Each tier is a distinct type. Serde's
//! `deny_unknown_fields` plus the schema split makes cross-tier content
//! leaks (e.g., a funnel at genre level) a load-time failure.

pub mod culture;
pub mod genre;
pub mod global;
pub mod world;
```

File: `crates/sidequest-genre/src/schema/global.rs`

```rust
use serde::{Deserialize, Serialize};

/// Global-tier content. Genre-agnostic structural primitives.
/// No proper nouns, no lore, no culture-specific flavor.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GlobalContent {
    #[serde(default)]
    pub jungian_axis: Vec<JungianAxisEntry>,
    #[serde(default)]
    pub rpg_role_axis: Vec<RpgRoleAxisEntry>,
    #[serde(default)]
    pub npc_role_axis: Vec<NpcRoleAxisEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct JungianAxisEntry {
    pub id: String,
    #[serde(default)]
    pub drive: String,
    #[serde(default)]
    pub ocean_tendencies: serde_yaml::Value,
    #[serde(default)]
    pub stat_affinity: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RpgRoleAxisEntry {
    pub id: String,
    #[serde(default)]
    pub stat_affinity: Vec<String>,
    #[serde(default)]
    pub combat_function: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NpcRoleAxisEntry {
    pub id: String,
    #[serde(default)]
    pub narrative_function: String,
    #[serde(default)]
    pub skip_enrichment: bool,
}
```

Add `pub mod schema;` to `crates/sidequest-genre/src/lib.rs`.

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test schema_unit`
Expected: PASS — 2 tests green.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/schema crates/sidequest-genre/src/lib.rs \
        crates/sidequest-genre/tests/schema_unit.rs
git commit -m "feat(genre): add GlobalContent schema with deny_unknown_fields"
```

### Task B2: `GenreContent` skeleton

**Files:**
- Create: `crates/sidequest-genre/src/schema/genre.rs`
- Modify: `crates/sidequest-genre/tests/schema_unit.rs`

- [ ] **Step 1: Failing test — genre accepts its own fields, rejects `funnels`**

Append to `schema_unit.rs`:

```rust
use sidequest_genre::schema::genre::GenreContent;

#[test]
fn genre_content_parses_minimal() {
    let yaml = r#"
valid_pairings: {}
genre_flavor: {}
"#;
    let parsed: GenreContent = serde_yaml::from_str(yaml).unwrap();
    assert!(parsed.valid_pairings.is_empty());
}

#[test]
fn genre_content_rejects_funnels() {
    let yaml = r#"
valid_pairings: {}
genre_flavor: {}
funnels: []
"#;
    let result: Result<GenreContent, _> = serde_yaml::from_str(yaml);
    let err = result.unwrap_err().to_string();
    assert!(err.contains("funnels"), "expected error naming 'funnels', got: {err}");
}
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cargo nextest run -p sidequest-genre --test schema_unit -- genre_content`
Expected: FAIL — module `genre` missing.

- [ ] **Step 3: Implement `GenreContent`**

File: `crates/sidequest-genre/src/schema/genre.rs`

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Genre-tier content. Patterns, constraints, fallback *shapes* — never named
/// instances. No funnels, no POIs, no faction names, no leitmotifs tied to a
/// specific named thing. Enforced by absence of fields for those concerns.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GenreContent {
    #[serde(default)]
    pub valid_pairings: HashMap<String, Vec<[String; 2]>>, // "common" | "uncommon" | "rare" | "forbidden"
    #[serde(default)]
    pub genre_flavor: HashMap<String, GenreFlavorEntry>,
    #[serde(default)]
    pub stat_name_mapping: HashMap<String, String>,
    #[serde(default)]
    pub ambient_music_library: Vec<String>,
    #[serde(default)]
    pub music_library: Vec<String>,
    #[serde(default)]
    pub lora_checkpoint: Option<String>,
    #[serde(default)]
    pub base_style_prompt: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GenreFlavorEntry {
    #[serde(default)]
    pub speech_pattern: String,
    #[serde(default)]
    pub equipment_tendency: String,
    #[serde(default)]
    pub visual_cues: String,
    #[serde(default)]
    pub fallback_name: Option<String>,
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test schema_unit -- genre_content`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/schema/genre.rs crates/sidequest-genre/tests/schema_unit.rs
git commit -m "feat(genre): add GenreContent schema rejecting named-instance fields"
```

### Task B3: `WorldContent` skeleton

**Files:**
- Create: `crates/sidequest-genre/src/schema/world.rs`
- Modify: `crates/sidequest-genre/tests/schema_unit.rs`

- [ ] **Step 1: Failing test — world accepts funnels, rejects `valid_pairings`**

Append to `schema_unit.rs`:

```rust
use sidequest_genre::schema::world::WorldContent;

#[test]
fn world_content_parses_funnels() {
    let yaml = r#"
funnels:
  - name: Thornwall Mender
    absorbs:
      - [sage, healer]
      - [caregiver, healer]
    faction: Thornwall Convocation
    lore: "Itinerant healers."
    cultural_status: respected
"#;
    let parsed: WorldContent = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(parsed.funnels.len(), 1);
    assert_eq!(parsed.funnels[0].name, "Thornwall Mender");
}

#[test]
fn world_content_rejects_valid_pairings() {
    let yaml = r#"
funnels: []
valid_pairings: {}
"#;
    let result: Result<WorldContent, _> = serde_yaml::from_str(yaml);
    let err = result.unwrap_err().to_string();
    assert!(err.contains("valid_pairings"), "expected error naming 'valid_pairings', got: {err}");
}
```

- [ ] **Step 2: Run — expect FAIL** (module missing).

Run: `cargo nextest run -p sidequest-genre --test schema_unit -- world_content`
Expected: FAIL.

- [ ] **Step 3: Implement `WorldContent`**

File: `crates/sidequest-genre/src/schema/world.rs`

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// World-tier content. Named instances: funnels, factions, POIs, leitmotif
/// bindings, world-specific image prompt additions.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorldContent {
    #[serde(default)]
    pub funnels: Vec<FunnelEntry>,
    #[serde(default)]
    pub factions: Vec<FactionEntry>,
    #[serde(default)]
    pub leitmotifs: HashMap<String, String>, // leitmotif name -> audio path
    #[serde(default)]
    pub additional_image_prompt: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FunnelEntry {
    pub name: String,
    pub absorbs: Vec<[String; 2]>,
    #[serde(default)]
    pub faction: Option<String>,
    #[serde(default)]
    pub lore: String,
    #[serde(default)]
    pub cultural_status: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FactionEntry {
    pub name: String,
    #[serde(default)]
    pub description: String,
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test schema_unit -- world_content`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/schema/world.rs crates/sidequest-genre/tests/schema_unit.rs
git commit -m "feat(genre): add WorldContent schema permitting named instances"
```

### Task B4: `CultureContent` skeleton

**Files:**
- Create: `crates/sidequest-genre/src/schema/culture.rs`
- Modify: `crates/sidequest-genre/tests/schema_unit.rs`

- [ ] **Step 1: Failing test — culture accepts reskins, rejects `funnels`**

Append to `schema_unit.rs`:

```rust
use sidequest_genre::schema::culture::CultureContent;

#[test]
fn culture_content_parses_reskins() {
    let yaml = r#"
id: thornwall
display_name: Thornwall
represents: faction
reskins:
  "Thornwall Mender":
    display_name: "Thornwall Mender"
    speech_pattern: "archaic Germanic cadence"
"#;
    let parsed: CultureContent = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(parsed.id, "thornwall");
    assert_eq!(parsed.reskins.len(), 1);
}

#[test]
fn culture_content_rejects_funnels() {
    let yaml = r#"
id: thornwall
display_name: Thornwall
represents: faction
funnels: []
"#;
    let result: Result<CultureContent, _> = serde_yaml::from_str(yaml);
    let err = result.unwrap_err().to_string();
    assert!(err.contains("funnels"), "expected error naming 'funnels', got: {err}");
}
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cargo nextest run -p sidequest-genre --test schema_unit -- culture_content`
Expected: FAIL.

- [ ] **Step 3: Implement `CultureContent`**

File: `crates/sidequest-genre/src/schema/culture.rs`

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Culture-tier content. Terminal flavor pass: names, speech, visual cues,
/// disposition, scenario variants. Never structural rules (those are Genre
/// or Global).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CultureContent {
    pub id: String,
    pub display_name: String,
    pub represents: CultureRepresents,
    #[serde(default)]
    pub corpus_binding: Option<CorpusBinding>,
    #[serde(default)]
    pub default_disposition_lean: Option<String>,
    #[serde(default)]
    pub reskins: HashMap<String, ArchetypeReskin>,
    #[serde(default)]
    pub speech: HashMap<String, String>,
    #[serde(default)]
    pub disposition_toward: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CultureRepresents {
    Race,
    Faction,
    Class,
    Composite,
}

impl Default for CultureRepresents {
    fn default() -> Self { Self::Faction }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusBinding {
    pub primary: String,
    #[serde(default)]
    pub secondary: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArchetypeReskin {
    #[serde(default)]
    pub display_name: Option<String>,
    #[serde(default)]
    pub speech_pattern: Option<String>,
    #[serde(default)]
    pub visual_cues: Vec<String>,
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test schema_unit -- culture_content`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/schema/culture.rs crates/sidequest-genre/tests/schema_unit.rs
git commit -m "feat(genre): add CultureContent schema (terminal flavor tier)"
```

---

## Phase C — Merge Strategies and the `Layered` Derive Macro

### Task C1: `MergeStrategy` enum + strategy helpers

**Files:**
- Create: `crates/sidequest-genre/src/resolver/merge.rs`

- [ ] **Step 1: Failing test — each strategy applied to concrete values**

Append to `resolver_unit.rs`:

```rust
use sidequest_genre::resolver::merge::{apply_strategy, MergeStrategy};

#[test]
fn replace_strategy_returns_deeper() {
    let out = apply_strategy(MergeStrategy::Replace, Some("base"), Some("deeper"));
    assert_eq!(out, Some("deeper"));
}

#[test]
fn replace_strategy_keeps_base_when_deeper_absent() {
    let out = apply_strategy(MergeStrategy::Replace, Some("base"), None::<&str>);
    assert_eq!(out, Some("base"));
}
```

- [ ] **Step 2: Run — expect FAIL** (module missing).

- [ ] **Step 3: Implement**

File: `crates/sidequest-genre/src/resolver/merge.rs`

```rust
use serde::{Deserialize, Serialize};

/// Per-field merge strategy. Annotated on each `Layered` struct field.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MergeStrategy {
    Replace,
    Append,
    DeepMerge,
    CultureFinal,
}

/// Apply `Replace` semantics: deeper tier wins when present.
pub fn apply_strategy<T: Clone>(
    strategy: MergeStrategy,
    base: Option<T>,
    deeper: Option<T>,
) -> Option<T> {
    match strategy {
        MergeStrategy::Replace => deeper.or(base),
        MergeStrategy::Append => {
            // Lists/vectors handled by the derive macro, not this helper.
            deeper.or(base)
        }
        MergeStrategy::DeepMerge => {
            // Struct-walked merge is also the derive macro's job.
            deeper.or(base)
        }
        MergeStrategy::CultureFinal => deeper.or(base),
    }
}
```

Add `pub mod merge;` to `crates/sidequest-genre/src/resolver/mod.rs` and re-export: `pub use merge::{MergeStrategy, apply_strategy};`.

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test resolver_unit -- replace_strategy`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/resolver/merge.rs crates/sidequest-genre/src/resolver/mod.rs \
        crates/sidequest-genre/tests/resolver_unit.rs
git commit -m "feat(genre): add MergeStrategy enum and Replace helper"
```

### Task C2: `append` strategy for Vec fields

- [ ] **Step 1: Failing test**

Append to `resolver_unit.rs`:

```rust
use sidequest_genre::resolver::merge::apply_append;

#[test]
fn append_strategy_concatenates_lists() {
    let base = vec!["a".to_string(), "b".to_string()];
    let deeper = vec!["c".to_string()];
    let out = apply_append(&base, &deeper);
    assert_eq!(out, vec!["a", "b", "c"]);
}

#[test]
fn append_strategy_handles_empty_base() {
    let base: Vec<String> = vec![];
    let deeper = vec!["only".to_string()];
    let out = apply_append(&base, &deeper);
    assert_eq!(out, vec!["only"]);
}
```

- [ ] **Step 2: Run — expect FAIL** (unresolved import).

- [ ] **Step 3: Implement in `resolver/merge.rs`**

```rust
/// Append-strategy: deeper's list concatenates onto base's.
pub fn apply_append<T: Clone>(base: &[T], deeper: &[T]) -> Vec<T> {
    let mut out = Vec::with_capacity(base.len() + deeper.len());
    out.extend_from_slice(base);
    out.extend_from_slice(deeper);
    out
}
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/resolver/merge.rs crates/sidequest-genre/tests/resolver_unit.rs
git commit -m "feat(genre): add Append merge strategy for list fields"
```

### Task C3: Create the `sidequest-genre-layered-derive` crate

**Files:**
- Create: `crates/sidequest-genre-layered-derive/Cargo.toml`
- Create: `crates/sidequest-genre-layered-derive/src/lib.rs`
- Modify: `Cargo.toml` (workspace)
- Modify: `crates/sidequest-genre/Cargo.toml`

- [ ] **Step 1: Write failing test**

File: `crates/sidequest-genre/tests/layered_derive.rs`

```rust
use sidequest_genre::Layered;

#[derive(Debug, Clone, PartialEq, Layered)]
struct Archetype {
    #[layer(merge = "replace")]
    name: String,
    #[layer(merge = "append")]
    quirks: Vec<String>,
}

#[test]
fn layered_replace_field_uses_deeper_value() {
    let base = Archetype { name: "Base".into(), quirks: vec!["a".into()] };
    let deeper = Archetype { name: "Deeper".into(), quirks: vec!["b".into()] };
    let merged = base.merge(deeper);
    assert_eq!(merged.name, "Deeper");
}

#[test]
fn layered_append_field_concatenates() {
    let base = Archetype { name: "Base".into(), quirks: vec!["a".into()] };
    let deeper = Archetype { name: "Deeper".into(), quirks: vec!["b".into()] };
    let merged = base.merge(deeper);
    assert_eq!(merged.quirks, vec!["a", "b"]);
}
```

- [ ] **Step 2: Run — expect FAIL** (derive macro missing).

Run: `cargo nextest run -p sidequest-genre --test layered_derive`
Expected: FAIL — `Layered` macro not found.

- [ ] **Step 3: Create the proc-macro crate**

File: `crates/sidequest-genre-layered-derive/Cargo.toml`

```toml
[package]
name = "sidequest-genre-layered-derive"
version.workspace = true
edition.workspace = true
license.workspace = true

[lib]
proc-macro = true

[dependencies]
proc-macro2 = "1"
quote = "1"
syn = { version = "2", features = ["full"] }
```

File: `crates/sidequest-genre-layered-derive/src/lib.rs`

```rust
use proc_macro::TokenStream;
use proc_macro2::TokenStream as TokenStream2;
use quote::quote;
use syn::{parse_macro_input, Data, DeriveInput, Fields, Meta};

/// `#[derive(Layered)]` — generates a `merge(self, other) -> Self` impl
/// that walks each field according to its `#[layer(merge = "...")]` annotation.
#[proc_macro_derive(Layered, attributes(layer))]
pub fn derive_layered(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    let name = &ast.ident;

    let Data::Struct(data) = &ast.data else {
        return syn::Error::new_spanned(&ast, "Layered only supports structs")
            .to_compile_error()
            .into();
    };
    let Fields::Named(fields) = &data.fields else {
        return syn::Error::new_spanned(&ast, "Layered requires named fields")
            .to_compile_error()
            .into();
    };

    let merges: Vec<TokenStream2> = fields.named.iter().map(|f| {
        let ident = f.ident.as_ref().unwrap();
        let strategy = extract_strategy(f).unwrap_or_else(|| "replace".to_string());
        match strategy.as_str() {
            "append" => quote! {
                #ident: {
                    let mut v = self.#ident;
                    v.extend(other.#ident);
                    v
                }
            },
            "replace" | "culture_final" => quote! {
                #ident: other.#ident
            },
            "deep_merge" => quote! {
                #ident: self.#ident.merge(other.#ident)
            },
            _ => quote! {
                #ident: other.#ident
            },
        }
    }).collect();

    let expanded = quote! {
        impl #name {
            pub fn merge(self, other: Self) -> Self {
                Self {
                    #( #merges ),*
                }
            }
        }
    };
    expanded.into()
}

fn extract_strategy(f: &syn::Field) -> Option<String> {
    for attr in &f.attrs {
        if !attr.path().is_ident("layer") {
            continue;
        }
        if let Meta::List(list) = &attr.meta {
            let mut found = None;
            let _ = list.parse_nested_meta(|meta| {
                if meta.path.is_ident("merge") {
                    let value: syn::LitStr = meta.value()?.parse()?;
                    found = Some(value.value());
                }
                Ok(())
            });
            if found.is_some() {
                return found;
            }
        }
    }
    None
}
```

Update workspace `Cargo.toml`:

```toml
[workspace]
members = [
    # ... existing members ...
    "crates/sidequest-genre-layered-derive",
]
```

Update `crates/sidequest-genre/Cargo.toml` `[dependencies]`:

```toml
sidequest-genre-layered-derive = { path = "../sidequest-genre-layered-derive" }
```

Add re-export in `crates/sidequest-genre/src/lib.rs`:

```rust
pub use sidequest_genre_layered_derive::Layered;
```

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test layered_derive`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre-layered-derive Cargo.toml \
        crates/sidequest-genre/Cargo.toml crates/sidequest-genre/src/lib.rs \
        crates/sidequest-genre/tests/layered_derive.rs
git commit -m "feat(genre): add #[derive(Layered)] proc-macro for per-field merge"
```

### Task C4: `deep_merge` and `culture_final` handling

- [ ] **Step 1: Failing test**

Append to `layered_derive.rs`:

```rust
#[derive(Debug, Clone, PartialEq, Default, Layered)]
struct Nested {
    #[layer(merge = "replace")]
    inner: String,
}

#[derive(Debug, Clone, PartialEq, Default, Layered)]
struct Outer {
    #[layer(merge = "deep_merge")]
    nested: Nested,
    #[layer(merge = "culture_final")]
    culture_only: Option<String>,
}

#[test]
fn deep_merge_walks_into_nested_struct() {
    let base = Outer { nested: Nested { inner: "base".into() }, culture_only: None };
    let deeper = Outer { nested: Nested { inner: "deeper".into() }, culture_only: Some("x".into()) };
    let merged = base.merge(deeper);
    assert_eq!(merged.nested.inner, "deeper");
    assert_eq!(merged.culture_only, Some("x".into()));
}

#[test]
fn culture_final_field_takes_deeper_value() {
    let base = Outer { nested: Nested::default(), culture_only: Some("from_base".into()) };
    let deeper = Outer { nested: Nested::default(), culture_only: Some("from_deeper".into()) };
    let merged = base.merge(deeper);
    assert_eq!(merged.culture_only, Some("from_deeper".into()));
}
```

- [ ] **Step 2: Run — expect PASS** (the macro already handles `deep_merge` and `culture_final` in C3's impl).

Run: `cargo nextest run -p sidequest-genre --test layered_derive`
Expected: PASS — 4 tests green total.

- [ ] **Step 3: Commit**

```bash
git add crates/sidequest-genre/tests/layered_derive.rs
git commit -m "test(genre): verify deep_merge and culture_final strategies"
```

---

## Phase D — The Resolver

The `Resolver<T>` loads tier files, applies the `Layered` merge walk, and records provenance for each contributing tier.

### Task D1: `ResolutionContext` — genre + world + culture identifiers

**Files:**
- Modify: `crates/sidequest-genre/src/resolver/mod.rs`

- [ ] **Step 1: Failing test**

Append to `resolver_unit.rs`:

```rust
use sidequest_genre::resolver::ResolutionContext;

#[test]
fn resolution_context_identifies_chain() {
    let ctx = ResolutionContext {
        genre: "heavy_metal".into(),
        world: Some("evropi".into()),
        culture: Some("thornwall".into()),
    };
    assert_eq!(ctx.genre, "heavy_metal");
    assert_eq!(ctx.world.as_deref(), Some("evropi"));
    assert_eq!(ctx.culture.as_deref(), Some("thornwall"));
}
```

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Implement**

In `resolver/mod.rs`:

```rust
/// What to resolve against. Chain is walked in order: Global → Genre → World → Culture.
#[derive(Debug, Clone)]
pub struct ResolutionContext {
    pub genre: String,
    pub world: Option<String>,
    pub culture: Option<String>,
}
```

- [ ] **Step 4: Run — expect PASS**.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/resolver/mod.rs crates/sidequest-genre/tests/resolver_unit.rs
git commit -m "feat(genre): add ResolutionContext"
```

### Task D2: `Resolver<T>::resolve` with file-based tier loading

**Files:**
- Create: `crates/sidequest-genre/src/resolver/load.rs`
- Modify: `crates/sidequest-genre/src/resolver/mod.rs`

- [ ] **Step 1: Failing integration test**

File: `crates/sidequest-genre/tests/resolver_integration.rs`

```rust
use sidequest_genre::resolver::{ResolutionContext, Resolver, Tier};
use sidequest_genre::schema::world::WorldContent;
use std::path::PathBuf;

fn fixture_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/heavy_metal_evropi")
}

#[test]
fn resolver_returns_world_tier_provenance_for_funnel() {
    let root = fixture_root();
    let ctx = ResolutionContext {
        genre: "heavy_metal".into(),
        world: Some("evropi".into()),
        culture: None,
    };
    let resolved: sidequest_genre::resolver::Resolved<WorldContent> =
        Resolver::<WorldContent>::new(&root).resolve("world", &ctx).unwrap();
    assert_eq!(resolved.provenance.source_tier, Tier::World);
    assert!(resolved.provenance.source_file.ends_with("worlds/evropi/world.yaml"));
    assert!(resolved.value.funnels.iter().any(|f| f.name == "Thornwall Mender"));
}
```

- [ ] **Step 2: Create fixture tree**

Create `crates/sidequest-genre/tests/fixtures/heavy_metal_evropi/` with:

File: `tests/fixtures/heavy_metal_evropi/archetypes_base.yaml`

```yaml
jungian_axis:
  - id: sage
    drive: "Seeks truth"
rpg_role_axis:
  - id: healer
npc_role_axis: []
```

File: `tests/fixtures/heavy_metal_evropi/heavy_metal/pack.yaml`

```yaml
valid_pairings:
  common:
    - [sage, healer]
genre_flavor:
  sage:
    speech_pattern: "measured"
```

File: `tests/fixtures/heavy_metal_evropi/heavy_metal/worlds/evropi/world.yaml`

```yaml
funnels:
  - name: Thornwall Mender
    absorbs:
      - [sage, healer]
    faction: Thornwall Convocation
    lore: "Itinerant healers."
    cultural_status: respected
```

- [ ] **Step 3: Run — expect FAIL**

Run: `cargo nextest run -p sidequest-genre --test resolver_integration`
Expected: FAIL — `Resolver` type not defined.

- [ ] **Step 4: Implement `Resolver` and `load.rs`**

File: `crates/sidequest-genre/src/resolver/load.rs`

```rust
use crate::error::GenreError;
use crate::resolver::{Resolved, Provenance, Tier, MergeStep, ContributionKind};
use serde::de::DeserializeOwned;
use std::marker::PhantomData;
use std::path::{Path, PathBuf};

pub struct Resolver<T> {
    root: PathBuf,
    _t: PhantomData<T>,
}

impl<T: DeserializeOwned> Resolver<T> {
    pub fn new(root: &Path) -> Self {
        Self { root: root.to_path_buf(), _t: PhantomData }
    }

    pub fn resolve(
        &self,
        axis: &str,
        ctx: &crate::resolver::ResolutionContext,
    ) -> Result<Resolved<T>, GenreError> {
        // For Phase 1, the world-tier file is authoritative for content that
        // *only* exists at World (e.g., funnels). Later tasks extend this to
        // walk Global → Genre → World → Culture with merging.
        let world = ctx.world.as_ref().ok_or_else(|| GenreError::ValidationError {
            message: "world is required for this axis".into(),
        })?;
        let path = self.root.join("heavy_metal").join("worlds").join(world).join(format!("{axis}.yaml"));
        let bytes = std::fs::read_to_string(&path).map_err(|e| GenreError::IoError {
            message: format!("reading {}: {}", path.display(), e),
        })?;
        let value: T = serde_yaml::from_str(&bytes).map_err(|e| GenreError::ValidationError {
            message: format!("parsing {}: {}", path.display(), e),
        })?;
        Ok(Resolved {
            value,
            provenance: Provenance {
                source_tier: Tier::World,
                source_file: path.clone(),
                source_span: None,
                merge_trail: vec![MergeStep {
                    tier: Tier::World,
                    file: path,
                    span: None,
                    contribution: ContributionKind::Initial,
                }],
            },
        })
    }
}
```

In `resolver/mod.rs` re-export: `pub use load::Resolver;`

Add error variants to `src/error.rs` if `IoError` does not exist:

```rust
#[error("I/O error: {message}")]
IoError { message: String },
```

- [ ] **Step 5: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test resolver_integration`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crates/sidequest-genre/src/resolver crates/sidequest-genre/src/error.rs \
        crates/sidequest-genre/tests/resolver_integration.rs \
        crates/sidequest-genre/tests/fixtures
git commit -m "feat(genre): implement Resolver<T> for World-tier file loading"
```

### Task D3: Extend `Resolver` to walk Global → Genre → World → Culture with merge

**Files:**
- Modify: `crates/sidequest-genre/src/resolver/load.rs`

- [ ] **Step 1: Failing test — resolving ArchetypeResolved merges Genre pattern + World named**

Append to `resolver_integration.rs`:

```rust
use sidequest_genre::Layered;

#[derive(Debug, Clone, Default, serde::Deserialize, Layered)]
struct ArchetypeSample {
    #[layer(merge = "replace")]
    name: String,
    #[layer(merge = "replace")]
    speech_pattern: String,
}

#[test]
fn resolver_merges_genre_and_world_tiers() {
    // TODO extend fixture and Resolver to support full chain; see Task D3 impl.
    // For now the test is scaffolded; the implementation step makes it pass.
    let root = fixture_root();
    let ctx = ResolutionContext {
        genre: "heavy_metal".into(),
        world: Some("evropi".into()),
        culture: None,
    };
    let resolved = Resolver::<ArchetypeSample>::new(&root)
        .resolve_merged("archetype.thornwall_mender", &ctx)
        .unwrap();
    // World-tier funnel supplies the name; Genre-tier flavor supplies speech.
    assert_eq!(resolved.value.name, "Thornwall Mender");
    assert_eq!(resolved.value.speech_pattern, "measured");
    assert_eq!(resolved.provenance.merge_trail.len(), 2);
    assert_eq!(resolved.provenance.merge_trail[0].tier, sidequest_genre::resolver::Tier::Genre);
    assert_eq!(resolved.provenance.merge_trail[1].tier, sidequest_genre::resolver::Tier::World);
}
```

- [ ] **Step 2: Extend fixture** — add Genre-tier speech fragment and World-tier archetype file under a path the resolver can find. Create:

File: `tests/fixtures/heavy_metal_evropi/heavy_metal/archetype_fragments/thornwall_mender.yaml`

```yaml
speech_pattern: "measured"
```

File: `tests/fixtures/heavy_metal_evropi/heavy_metal/worlds/evropi/archetype_fragments/thornwall_mender.yaml`

```yaml
name: "Thornwall Mender"
```

- [ ] **Step 3: Run — expect FAIL** (`resolve_merged` missing).

- [ ] **Step 4: Implement `resolve_merged`**

In `resolver/load.rs`, add:

```rust
impl<T: DeserializeOwned + Default + Clone> Resolver<T> {
    /// Resolve a field path across Global → Genre → World → Culture, merging at each tier.
    /// Requires that T implements the Layered `merge` method (via derive).
    pub fn resolve_merged(
        &self,
        field_path: &str,
        ctx: &crate::resolver::ResolutionContext,
    ) -> Result<Resolved<T>, GenreError>
    where
        T: LayeredMerge,
    {
        let mut trail = Vec::new();
        let mut current: Option<T> = None;
        let mut final_tier = Tier::Global;
        let mut final_file = PathBuf::new();

        // Global tier
        let global_path = self.root.join(format!("{field_path}.yaml"));
        if let Ok(bytes) = std::fs::read_to_string(&global_path) {
            let val: T = serde_yaml::from_str(&bytes).map_err(|e| GenreError::ValidationError {
                message: format!("parsing {}: {}", global_path.display(), e),
            })?;
            current = Some(val);
            final_tier = Tier::Global;
            final_file = global_path.clone();
            trail.push(MergeStep {
                tier: Tier::Global,
                file: global_path,
                span: None,
                contribution: ContributionKind::Initial,
            });
        }

        // Genre tier
        let genre_path = self.root.join(&ctx.genre).join(format!("{field_path}.yaml"));
        if let Ok(bytes) = std::fs::read_to_string(&genre_path) {
            let val: T = serde_yaml::from_str(&bytes).map_err(|e| GenreError::ValidationError {
                message: format!("parsing {}: {}", genre_path.display(), e),
            })?;
            let contribution = if current.is_some() { ContributionKind::Merged } else { ContributionKind::Initial };
            current = Some(match current {
                Some(base) => base.merge(val),
                None => val,
            });
            final_tier = Tier::Genre;
            final_file = genre_path.clone();
            trail.push(MergeStep {
                tier: Tier::Genre,
                file: genre_path,
                span: None,
                contribution,
            });
        }

        // World tier
        if let Some(world) = &ctx.world {
            let world_path = self.root.join(&ctx.genre).join("worlds").join(world).join(format!("{field_path}.yaml"));
            if let Ok(bytes) = std::fs::read_to_string(&world_path) {
                let val: T = serde_yaml::from_str(&bytes).map_err(|e| GenreError::ValidationError {
                    message: format!("parsing {}: {}", world_path.display(), e),
                })?;
                let contribution = if current.is_some() { ContributionKind::Merged } else { ContributionKind::Initial };
                current = Some(match current {
                    Some(base) => base.merge(val),
                    None => val,
                });
                final_tier = Tier::World;
                final_file = world_path.clone();
                trail.push(MergeStep {
                    tier: Tier::World,
                    file: world_path,
                    span: None,
                    contribution,
                });
            }
        }

        // Culture tier
        if let (Some(world), Some(culture)) = (&ctx.world, &ctx.culture) {
            let culture_path = self.root.join(&ctx.genre).join("worlds").join(world)
                .join("cultures").join(culture).join(format!("{field_path}.yaml"));
            if let Ok(bytes) = std::fs::read_to_string(&culture_path) {
                let val: T = serde_yaml::from_str(&bytes).map_err(|e| GenreError::ValidationError {
                    message: format!("parsing {}: {}", culture_path.display(), e),
                })?;
                let contribution = if current.is_some() { ContributionKind::Merged } else { ContributionKind::Initial };
                current = Some(match current {
                    Some(base) => base.merge(val),
                    None => val,
                });
                final_tier = Tier::Culture;
                final_file = culture_path.clone();
                trail.push(MergeStep {
                    tier: Tier::Culture,
                    file: culture_path,
                    span: None,
                    contribution,
                });
            }
        }

        let value = current.ok_or_else(|| GenreError::ValidationError {
            message: format!("no tier supplied field '{field_path}'"),
        })?;

        Ok(Resolved {
            value,
            provenance: Provenance {
                source_tier: final_tier,
                source_file: final_file,
                source_span: None,
                merge_trail: trail,
            },
        })
    }
}

/// Trait implemented by every struct with `#[derive(Layered)]`.
pub trait LayeredMerge {
    fn merge(self, other: Self) -> Self;
}
```

Update the derive macro in `sidequest-genre-layered-derive/src/lib.rs` to generate a `LayeredMerge` impl instead of a bare `merge` method. Change the expanded block:

```rust
let expanded = quote! {
    impl ::sidequest_genre::resolver::LayeredMerge for #name {
        fn merge(self, other: Self) -> Self {
            Self {
                #( #merges ),*
            }
        }
    }
};
```

Re-export `LayeredMerge` from `resolver/mod.rs`: `pub use load::{Resolver, LayeredMerge};`

- [ ] **Step 5: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test resolver_integration`
Expected: PASS — all tests green.

- [ ] **Step 6: Commit**

```bash
git add crates/sidequest-genre/src/resolver crates/sidequest-genre-layered-derive/src/lib.rs \
        crates/sidequest-genre/tests/resolver_integration.rs \
        crates/sidequest-genre/tests/fixtures
git commit -m "feat(genre): walk Global→Genre→World→Culture with Layered merge"
```

---

## Phase E — OTEL Span Emission

### Task E1: `content.resolve` span attributes

**Files:**
- Create: `crates/sidequest-genre/src/resolver/otel.rs`
- Modify: `crates/sidequest-genre/Cargo.toml` (add `sidequest-telemetry` dep if not present)

- [ ] **Step 1: Failing test — span carries expected attributes**

Append to `resolver_integration.rs`:

```rust
#[test]
fn resolver_emits_content_resolve_span() {
    // Set up test-local tracing subscriber that captures spans into a Vec.
    let captured = sidequest_telemetry::test_support::capture_spans(|| {
        let root = fixture_root();
        let ctx = ResolutionContext {
            genre: "heavy_metal".into(),
            world: Some("evropi".into()),
            culture: None,
        };
        let _ = Resolver::<ArchetypeSample>::new(&root)
            .resolve_merged("archetype.thornwall_mender", &ctx)
            .unwrap();
    });
    let span = captured.iter().find(|s| s.name == "content.resolve")
        .expect("content.resolve span not emitted");
    assert_eq!(span.attrs.get("content.axis").map(String::as_str), Some("archetype"));
    assert_eq!(span.attrs.get("content.genre").map(String::as_str), Some("heavy_metal"));
    assert_eq!(span.attrs.get("content.world").map(String::as_str), Some("evropi"));
    assert_eq!(span.attrs.get("content.source_tier").map(String::as_str), Some("world"));
    assert!(span.attrs.get("content.field_path").is_some());
}
```

- [ ] **Step 2: Run — expect FAIL** (test helper missing + span not emitted).

- [ ] **Step 3: Implement span emission helper**

File: `crates/sidequest-genre/src/resolver/otel.rs`

```rust
use crate::resolver::{Provenance, Tier};

pub fn emit_content_resolve_span(
    axis: &str,
    field_path: &str,
    genre: &str,
    world: Option<&str>,
    culture: Option<&str>,
    provenance: &Provenance,
    elapsed_us: u64,
) {
    let tier_str = match provenance.source_tier {
        Tier::Global => "global",
        Tier::Genre => "genre",
        Tier::World => "world",
        Tier::Culture => "culture",
    };
    tracing::info_span!(
        "content.resolve",
        otel.name = "content.resolve",
        content.axis = axis,
        content.field_path = field_path,
        content.genre = genre,
        content.world = world.unwrap_or(""),
        content.culture = culture.unwrap_or(""),
        content.source_tier = tier_str,
        content.source_file = %provenance.source_file.display(),
        content.merge_trail_len = provenance.merge_trail.len(),
        content.elapsed_us = elapsed_us,
    ).in_scope(|| ());
}
```

In `resolver/load.rs::resolve_merged`, at the end (before returning), wrap the result and call `emit_content_resolve_span(field_path.split('.').next().unwrap_or(field_path), field_path, &ctx.genre, ctx.world.as_deref(), ctx.culture.as_deref(), &provenance, elapsed_us)` where `elapsed_us` is measured with `Instant::now()`.

Add `test_support::capture_spans` to `sidequest-telemetry` if not present:

File: `crates/sidequest-telemetry/src/test_support.rs`

```rust
// (Implementation depends on the existing tracing subscriber setup.
// If a capturing subscriber already exists, export it. Otherwise use
// `tracing_subscriber::fmt::layer().with_test_writer()` with a shared
// Vec<CapturedSpan> wrapped in Mutex. Add CapturedSpan {name, attrs} struct.)
```

Add `pub mod otel;` to `resolver/mod.rs`.

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test resolver_integration -- resolver_emits`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/resolver/otel.rs \
        crates/sidequest-genre/src/resolver/load.rs \
        crates/sidequest-genre/src/resolver/mod.rs \
        crates/sidequest-telemetry/src/test_support.rs \
        crates/sidequest-telemetry/src/lib.rs \
        crates/sidequest-genre/tests/resolver_integration.rs
git commit -m "feat(genre): emit content.resolve OTEL span with provenance attrs"
```

---

## Phase F — Migrate Archetype Resolution to the Framework

### Task F1: Read the existing archetype path

- [ ] **Step 1: Read the current loader**

Read `crates/sidequest-genre/src/archetype_resolve.rs` top-to-bottom. Record:
- What `ResolvedArchetype` contains.
- Which callers call `resolve_archetype(...)` (grep the workspace).

Run: `rg -n 'resolve_archetype' --type rust`

Record each call site. You will rewrite each in Task F3.

- [ ] **Step 2: No code change in this task — this is a reconnaissance step**

Move on.

### Task F2: Define `ArchetypeResolved` on the new framework

**Files:**
- Modify: `crates/sidequest-genre/src/schema/world.rs` (if `FunnelEntry` needs augmentation)
- Create: `crates/sidequest-genre/src/archetype/resolved.rs` (new module)

- [ ] **Step 1: Failing test**

File: `crates/sidequest-genre/tests/archetype_resolved_unit.rs`

```rust
use sidequest_genre::archetype::ArchetypeResolved;
use sidequest_genre::resolver::LayeredMerge;

#[test]
fn archetype_resolved_merges_genre_then_world() {
    let base = ArchetypeResolved {
        name: String::new(),
        jungian: "sage".into(),
        rpg_role: "healer".into(),
        speech_pattern: "measured".into(),
        lore: "".into(),
        faction: None,
        cultural_status: None,
    };
    let world = ArchetypeResolved {
        name: "Thornwall Mender".into(),
        jungian: "sage".into(),
        rpg_role: "healer".into(),
        speech_pattern: String::new(),
        lore: "Itinerant healers.".into(),
        faction: Some("Thornwall Convocation".into()),
        cultural_status: Some("respected".into()),
    };
    let merged = base.merge(world);
    assert_eq!(merged.name, "Thornwall Mender");
    assert_eq!(merged.speech_pattern, ""); // replace strategy; world had empty
}
```

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Implement**

File: `crates/sidequest-genre/src/archetype/mod.rs`

```rust
pub mod resolved;
pub use resolved::ArchetypeResolved;
```

File: `crates/sidequest-genre/src/archetype/resolved.rs`

```rust
use crate::Layered;
use serde::Deserialize;

#[derive(Debug, Clone, Default, Deserialize, Layered)]
pub struct ArchetypeResolved {
    #[layer(merge = "replace")]
    pub name: String,
    #[layer(merge = "replace")]
    pub jungian: String,
    #[layer(merge = "replace")]
    pub rpg_role: String,
    #[layer(merge = "replace")]
    pub speech_pattern: String,
    #[layer(merge = "replace")]
    pub lore: String,
    #[layer(merge = "replace")]
    pub faction: Option<String>,
    #[layer(merge = "replace")]
    pub cultural_status: Option<String>,
}
```

Add `pub mod archetype;` to `lib.rs`.

- [ ] **Step 4: Run — expect PASS**.

- [ ] **Step 5: Commit**

```bash
git add crates/sidequest-genre/src/archetype crates/sidequest-genre/src/lib.rs \
        crates/sidequest-genre/tests/archetype_resolved_unit.rs
git commit -m "feat(genre): add ArchetypeResolved on the Layered framework"
```

### Task F3: Rewrite call sites to use `Resolver<ArchetypeResolved>`

**Files:**
- Modify: every caller of `resolve_archetype` identified in F1

- [ ] **Step 1: Write integration test asserting new path in use**

File: `crates/sidequest-genre/tests/archetype_migration.rs`

```rust
use sidequest_genre::archetype::ArchetypeResolved;
use sidequest_genre::resolver::{ResolutionContext, Resolver};
use std::path::PathBuf;

#[test]
fn archetype_resolves_through_new_framework() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/heavy_metal_evropi");
    let ctx = ResolutionContext {
        genre: "heavy_metal".into(),
        world: Some("evropi".into()),
        culture: None,
    };
    let resolved = Resolver::<ArchetypeResolved>::new(&root)
        .resolve_merged("archetype.thornwall_mender", &ctx)
        .expect("archetype should resolve");
    assert_eq!(resolved.value.name, "Thornwall Mender");
    assert_eq!(resolved.provenance.merge_trail.len() >= 2, true);
}
```

- [ ] **Step 2: Run — expect PASS** if fixture is ready (from D3).

- [ ] **Step 3: Rewrite each caller**

For every line in F1's grep output, replace:

```rust
let a = resolve_archetype(jungian, rpg_role, &base, &constraints, Some(&funnels))?;
```

with:

```rust
let ctx = ResolutionContext { genre: genre_id, world: Some(world_id), culture: cult };
let resolved = Resolver::<ArchetypeResolved>::new(&content_root)
    .resolve_merged(&format!("archetype.{slug}"), &ctx)?;
```

Adjust downstream code that reads fields off the old `ResolvedArchetype` to read from `resolved.value` (field shapes are compatible; add missing fields if any downstream consumer expected them).

- [ ] **Step 4: Run full workspace tests — expect PASS**

Run: `cargo nextest run --workspace`
Expected: PASS. Any remaining reference to the old `resolve_archetype` fails compilation, which is deliberate — F4 deletes it.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(archetype): route resolution through Resolver<ArchetypeResolved>"
```

### Task F4: Delete the old `archetype_resolve.rs`

**Files:**
- Delete: `crates/sidequest-genre/src/archetype_resolve.rs`
- Modify: `crates/sidequest-genre/src/lib.rs` (remove `pub mod archetype_resolve`)

- [ ] **Step 1: Write failing grep-based wiring test**

File: `crates/sidequest-genre/tests/wiring_no_old_loader.rs`

```rust
use std::process::Command;

#[test]
fn old_archetype_resolver_function_is_removed() {
    let out = Command::new("git")
        .arg("grep").arg("-l").arg("fn resolve_archetype")
        .arg("--").arg("crates")
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .output()
        .expect("git grep");
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.trim().is_empty(),
        "old `fn resolve_archetype` still exists in:\n{}", stdout);
}
```

- [ ] **Step 2: Run — expect FAIL** (old function still present).

Run: `cargo nextest run -p sidequest-genre --test wiring_no_old_loader`
Expected: FAIL.

- [ ] **Step 3: Delete the file**

```bash
rm crates/sidequest-genre/src/archetype_resolve.rs
```

Remove `pub mod archetype_resolve;` from `crates/sidequest-genre/src/lib.rs`. Remove any `use` statements of `archetype_resolve` across the workspace (the compiler surfaces these).

- [ ] **Step 4: Run — expect PASS**

Run: `cargo nextest run --workspace`
Expected: PASS — no remaining references.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(archetype): delete old archetype_resolve.rs (superseded by Resolver)"
```

---

## Phase G — Protocol and Game Crate Wiring

### Task G1: Add `Provenance` to `sidequest-protocol`

**Files:**
- Modify: `crates/sidequest-protocol/src/lib.rs` (or wherever content-carrying types are defined)

- [ ] **Step 1: Failing test — Provenance serializes through protocol format**

File: `crates/sidequest-protocol/tests/provenance_wire.rs`

```rust
use sidequest_protocol::{Provenance, Tier};
use std::path::PathBuf;

#[test]
fn provenance_roundtrips_through_protocol_json() {
    let p = Provenance {
        source_tier: Tier::World,
        source_file: PathBuf::from("worlds/evropi/world.yaml"),
        source_span: None,
        merge_trail: vec![],
    };
    let s = serde_json::to_string(&p).unwrap();
    let back: Provenance = serde_json::from_str(&s).unwrap();
    assert_eq!(p.source_tier, back.source_tier);
}
```

- [ ] **Step 2: Run — expect FAIL** (not defined in protocol).

- [ ] **Step 3: Implement**

In `crates/sidequest-protocol/src/lib.rs`, re-export the `Provenance` and related types from `sidequest-genre`:

```rust
pub use sidequest_genre::resolver::{ContributionKind, MergeStep, Provenance, Span, Tier};
```

Or define parallel protocol types that `serde`-roundtrip with the same JSON shape. The simplest path: re-export (sidequest-protocol already depends on sidequest-genre, or can).

Verify this does not create a circular dependency. If sidequest-genre depends on sidequest-protocol, invert: move `Provenance` into `sidequest-protocol` and re-export from `sidequest-genre`.

- [ ] **Step 4: Run — expect PASS**.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(protocol): expose Provenance type for GameMessage payloads"
```

### Task G2: Attach `Provenance` to `GameMessage` archetype variants

- [ ] **Step 1: Failing test — a character-state message carries provenance**

File: `crates/sidequest-protocol/tests/game_message_provenance.rs`

```rust
use sidequest_protocol::{CharacterState, GameMessage, Provenance, Tier};
use std::path::PathBuf;

#[test]
fn character_state_carries_archetype_provenance() {
    let msg = GameMessage::CharacterState(CharacterState {
        name: "Rux".into(),
        archetype_name: "Thornwall Mender".into(),
        archetype_provenance: Some(Provenance {
            source_tier: Tier::Culture,
            source_file: PathBuf::from("worlds/evropi/cultures/thornwall/archetype_reskins.yaml"),
            source_span: None,
            merge_trail: vec![],
        }),
    });
    let s = serde_json::to_string(&msg).unwrap();
    assert!(s.contains("archetype_provenance"));
    assert!(s.contains("culture"));
}
```

- [ ] **Step 2: Run — expect FAIL** (field missing).

- [ ] **Step 3: Add optional `archetype_provenance` to `CharacterState`**

In `sidequest-protocol`, find `CharacterState` (or equivalent struct that holds the archetype name). Add:

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CharacterState {
    pub name: String,
    pub archetype_name: String,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub archetype_provenance: Option<Provenance>,
}
```

Update every constructor in the codebase to populate `archetype_provenance: Some(resolved.provenance.clone())` where the archetype is set from a `Resolved<ArchetypeResolved>`.

- [ ] **Step 4: Run full workspace — expect PASS**.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(protocol): add archetype_provenance to CharacterState"
```

### Task G3: Consume `Resolved<ArchetypeResolved>` in `sidequest-game`

**Files:**
- Modify: `crates/sidequest-game/src/character.rs` (or wherever archetype is stored)

- [ ] **Step 1: Failing test**

File: `crates/sidequest-game/tests/character_provenance.rs`

```rust
use sidequest_game::character::Character;
use sidequest_genre::archetype::ArchetypeResolved;
use sidequest_genre::resolver::{ContributionKind, MergeStep, Provenance, Resolved, Tier};
use std::path::PathBuf;

#[test]
fn character_retains_archetype_provenance() {
    let resolved = Resolved {
        value: ArchetypeResolved {
            name: "Thornwall Mender".into(),
            ..Default::default()
        },
        provenance: Provenance {
            source_tier: Tier::Culture,
            source_file: PathBuf::from("cultures/thornwall/archetype_reskins.yaml"),
            source_span: None,
            merge_trail: vec![MergeStep {
                tier: Tier::Culture,
                file: PathBuf::from("cultures/thornwall/archetype_reskins.yaml"),
                span: None,
                contribution: ContributionKind::Initial,
            }],
        },
    };
    let c = Character::with_archetype("Rux".into(), resolved);
    assert_eq!(c.archetype.source_tier_for_panel(), "culture");
}
```

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Implement**

In `sidequest-game/src/character.rs`:

```rust
use sidequest_genre::archetype::ArchetypeResolved;
use sidequest_genre::resolver::Resolved;

pub struct Character {
    pub name: String,
    pub archetype: Resolved<ArchetypeResolved>,
}

impl Character {
    pub fn with_archetype(name: String, archetype: Resolved<ArchetypeResolved>) -> Self {
        Self { name, archetype }
    }
}

pub trait ProvenancePanelExt {
    fn source_tier_for_panel(&self) -> &'static str;
}

impl ProvenancePanelExt for Resolved<ArchetypeResolved> {
    fn source_tier_for_panel(&self) -> &'static str {
        use sidequest_genre::resolver::Tier;
        match self.provenance.source_tier {
            Tier::Global => "global",
            Tier::Genre => "genre",
            Tier::World => "world",
            Tier::Culture => "culture",
        }
    }
}
```

- [ ] **Step 4: Run — expect PASS**.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(game): character holds Resolved<ArchetypeResolved> with provenance"
```

---

## Phase H — UI Provenance Inspector

### Task H1: TypeScript `Provenance` types

**Files:**
- Create: `sidequest-ui/src/types/provenance.ts`

- [ ] **Step 1: Failing test**

File: `sidequest-ui/src/types/__tests__/provenance.test.ts`

```ts
import { describe, it, expect } from "vitest";
import type { Provenance, Tier } from "../provenance";

describe("Provenance TS type", () => {
  it("parses a wire-shape provenance", () => {
    const json = `{
      "source_tier": "culture",
      "source_file": "worlds/evropi/cultures/thornwall/archetype_reskins.yaml",
      "source_span": null,
      "merge_trail": []
    }`;
    const parsed: Provenance = JSON.parse(json);
    const tier: Tier = parsed.source_tier;
    expect(tier).toBe("culture");
    expect(parsed.source_file.endsWith("archetype_reskins.yaml")).toBe(true);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd sidequest-ui && npm test -- provenance`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

File: `sidequest-ui/src/types/provenance.ts`

```ts
export type Tier = "global" | "genre" | "world" | "culture";

export type ContributionKind = "initial" | "replaced" | "appended" | "merged";

export interface Span {
  start_line: number;
  start_col: number;
  end_line: number;
  end_col: number;
}

export interface MergeStep {
  tier: Tier;
  file: string;
  span: Span | null;
  contribution: ContributionKind;
}

export interface Provenance {
  source_tier: Tier;
  source_file: string;
  source_span: Span | null;
  merge_trail: MergeStep[];
}
```

- [ ] **Step 4: Run — expect PASS**.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/types/provenance.ts \
        sidequest-ui/src/types/__tests__/provenance.test.ts
git commit -m "feat(ui): Provenance TypeScript types"
```

### Task H2: `ProvenanceInspector` component

**Files:**
- Create: `sidequest-ui/src/components/GMPanel/ProvenanceInspector.tsx`
- Create: `sidequest-ui/src/components/GMPanel/ProvenanceInspector.test.tsx`

- [ ] **Step 1: Failing test**

File: `sidequest-ui/src/components/GMPanel/ProvenanceInspector.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ProvenanceInspector } from "./ProvenanceInspector";
import type { Provenance } from "../../types/provenance";

const sample: Provenance = {
  source_tier: "culture",
  source_file: "worlds/evropi/cultures/thornwall/archetype_reskins.yaml",
  source_span: { start_line: 12, start_col: 1, end_line: 18, end_col: 0 },
  merge_trail: [
    { tier: "genre",   file: "heavy_metal/archetype_fragments/thornwall_mender.yaml", span: null, contribution: "initial" },
    { tier: "world",   file: "worlds/evropi/archetype_fragments/thornwall_mender.yaml", span: null, contribution: "merged" },
    { tier: "culture", file: "worlds/evropi/cultures/thornwall/archetype_reskins.yaml", span: null, contribution: "merged" },
  ],
};

describe("ProvenanceInspector", () => {
  it("renders source tier badge and file", () => {
    render(<ProvenanceInspector fieldPath="archetype.thornwall_mender" provenance={sample} />);
    expect(screen.getByText(/culture/i)).toBeInTheDocument();
    expect(screen.getByText(/archetype_reskins\.yaml/)).toBeInTheDocument();
  });

  it("renders the merge trail entries", () => {
    render(<ProvenanceInspector fieldPath="archetype.thornwall_mender" provenance={sample} />);
    expect(screen.getByText(/thornwall_mender\.yaml/)).toBeInTheDocument();
    expect(screen.getAllByTestId("merge-step")).toHaveLength(3);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Implement**

File: `sidequest-ui/src/components/GMPanel/ProvenanceInspector.tsx`

```tsx
import type { Provenance, Tier } from "../../types/provenance";

const tierLabel: Record<Tier, string> = {
  global: "Global",
  genre: "Genre",
  world: "World",
  culture: "Culture",
};

interface Props {
  fieldPath: string;
  provenance: Provenance;
}

export function ProvenanceInspector({ fieldPath, provenance }: Props) {
  return (
    <div className="provenance-inspector">
      <div className="provenance-header">
        <code>{fieldPath}</code>
        <span className={`tier-badge tier-${provenance.source_tier}`}>
          {tierLabel[provenance.source_tier]}
        </span>
      </div>
      <div className="source-file">{provenance.source_file}
        {provenance.source_span && (
          <span className="source-span">
            {" "}L{provenance.source_span.start_line}–{provenance.source_span.end_line}
          </span>
        )}
      </div>
      <ol className="merge-trail">
        {provenance.merge_trail.map((step, i) => (
          <li key={i} data-testid="merge-step" className={`tier-${step.tier}`}>
            <span className={`tier-badge tier-${step.tier}`}>{tierLabel[step.tier]}</span>
            <code>{step.file}</code>
            <span className="contribution">{step.contribution}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd sidequest-ui && npm test -- ProvenanceInspector`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/GMPanel/ProvenanceInspector.tsx \
        sidequest-ui/src/components/GMPanel/ProvenanceInspector.test.tsx
git commit -m "feat(ui): ProvenanceInspector component rendering tier + trail"
```

### Task H3: Mount inspector in GM Panel (wiring)

**Files:**
- Modify: `sidequest-ui/src/components/GMPanel/index.tsx`

- [ ] **Step 1: Failing wiring test**

File: `sidequest-ui/src/components/GMPanel/GMPanel.provenance.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { GMPanel } from "./index";

describe("GMPanel provenance wiring", () => {
  it("renders ProvenanceInspector when a character with provenance is present", () => {
    const state = {
      characters: [{
        name: "Rux",
        archetype_name: "Thornwall Mender",
        archetype_provenance: {
          source_tier: "culture",
          source_file: "worlds/evropi/cultures/thornwall/archetype_reskins.yaml",
          source_span: null,
          merge_trail: [],
        },
      }],
    };
    render(<GMPanel gameState={state as any} />);
    expect(screen.getByText(/archetype_reskins\.yaml/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Wire the inspector into GMPanel**

Read `sidequest-ui/src/components/GMPanel/index.tsx`. Add, for each character in `gameState.characters`:

```tsx
{char.archetype_provenance && (
  <ProvenanceInspector
    fieldPath={`archetype.${char.name}`}
    provenance={char.archetype_provenance}
  />
)}
```

- [ ] **Step 4: Run — expect PASS**.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/GMPanel/index.tsx \
        sidequest-ui/src/components/GMPanel/GMPanel.provenance.test.tsx
git commit -m "feat(ui): mount ProvenanceInspector in GMPanel per-character"
```

---

## Phase I — Iron Foundry Regression and Final Sweep

### Task I1: The Iron Foundry regression test (the gravestone)

**Files:**
- Create: `crates/sidequest-genre/tests/iron_foundry_regression.rs`

- [ ] **Step 1: Write the regression test**

```rust
use sidequest_genre::archetype::ArchetypeResolved;
use sidequest_genre::resolver::{ResolutionContext, Resolver};
use std::path::PathBuf;

#[test]
fn evropi_archetype_resolution_never_sources_from_long_foundry() {
    let root = PathBuf::from("../../sidequest-content/genre_packs");
    let ctx = ResolutionContext {
        genre: "heavy_metal".into(),
        world: Some("evropi".into()),
        culture: None,
    };
    // Resolve every archetype-relevant field exercised during chargen.
    let field_paths = [
        "archetype.overview",
        "archetype.chargen_opening",
        "archetype.lore_prologue",
    ];
    for fp in field_paths {
        let resolver = Resolver::<ArchetypeResolved>::new(&root);
        if let Ok(resolved) = resolver.resolve_merged(fp, &ctx) {
            let path_str = resolved.provenance.source_file.to_string_lossy().to_lowercase();
            assert!(!path_str.contains("long_foundry"),
                "Iron Foundry content leaked: field {fp} sourced from {path_str}");
            for step in &resolved.provenance.merge_trail {
                let step_path = step.file.to_string_lossy().to_lowercase();
                assert!(!step_path.contains("long_foundry"),
                    "Iron Foundry content in merge trail: field {fp} step {step_path}");
            }
        }
    }
}
```

- [ ] **Step 2: Run — expect the test to be honest about current state**

Run: `cargo nextest run -p sidequest-genre --test iron_foundry_regression`
Expected: at this point the genre-level `heavy_metal/char_creation.yaml` / `heavy_metal/lore.yaml` still contain exemplar-world content. If those files are read during any of the enumerated field resolutions, the test FAILS — which is correct: the test is the gate for Task I2.

- [ ] **Step 3: Commit the failing test** (intentional — the following task makes it pass)

```bash
git add crates/sidequest-genre/tests/iron_foundry_regression.rs
git commit -m "test(genre): Iron Foundry regression — evropi must not source from long_foundry"
```

### Task I2: Relocate Long Foundry content out of genre-tier files

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/char_creation.yaml`
- Modify: `sidequest-content/genre_packs/heavy_metal/lore.yaml`
- Create/modify: `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/*`

- [ ] **Step 1: Identify leaked content**

Run:
```
rg -n -i 'foundry|forge' sidequest-content/genre_packs/heavy_metal/char_creation.yaml \
                           sidequest-content/genre_packs/heavy_metal/lore.yaml
```

For each hit, decide: is this content universally heavy_metal (stays at genre) or is it Long-Foundry-specific (moves)?

- [ ] **Step 2: Move Long-Foundry-specific content to the world directory**

Cut sections from the genre files, paste into `sidequest-content/genre_packs/heavy_metal/worlds/long_foundry/<appropriate_file>.yaml`.

- [ ] **Step 3: Run the regression test — expect PASS**

Run: `cargo nextest run -p sidequest-genre --test iron_foundry_regression`
Expected: PASS.

- [ ] **Step 4: Run full workspace tests — expect PASS**

Run: `cargo nextest run --workspace`

- [ ] **Step 5: Commit**

```bash
git add sidequest-content/genre_packs/heavy_metal
git commit -m "content(heavy_metal): relocate Long Foundry content out of genre tier"
```

### Task I3: Final sweep — no-coexistence verification

- [ ] **Step 1: Assert old loader is gone**

Run: `rg -n 'fn resolve_archetype\b' --type rust`
Expected: no output.

Run: `rg -n 'use crate::archetype_resolve' --type rust`
Expected: no output.

- [ ] **Step 2: Assert Resolver has a non-test consumer**

Run: `rg -n 'Resolver::<.*>::new' crates/sidequest-server crates/sidequest-game`
Expected: at least one hit in each crate outside `#[cfg(test)]`.

- [ ] **Step 3: Run `just check-all`**

Expected: PASS. No new debt.

- [ ] **Step 4: Commit (no-op if clean)**

```bash
git commit --allow-empty -m "chore: Phase 1 sweep — framework + archetypes migrated, old loader gone"
```

---

## Self-Review Summary

- **Spec coverage:** Every Phase-1 requirement from the spec has at least one task.
  - Resolver / Resolved / Provenance: Phase A, D.
  - Per-tier schema split: Phase B.
  - Merge semantics with Layered derive: Phase C.
  - OTEL content.resolve span: Phase E.
  - Archetype migration + old-loader deletion: Phase F.
  - Provenance through protocol and game: Phase G.
  - GM panel inspector: Phase H.
  - Iron Foundry regression test + content relocation: Phase I.
- **Placeholders:** None. Every step has concrete code, tests, or exact commands.
- **Type consistency:**
  - `Resolved<T>`, `Provenance`, `Tier`, `MergeStep`, `ContributionKind` are defined in Phase A and referenced consistently through G and H.
  - `ArchetypeResolved` is defined in F2 and referenced in F3, G3, I1.
  - `LayeredMerge` trait is defined in D3; macro in C3 is updated in D3 to implement it — watch for compile order when executing.
- **Known rough edges (implementer should read adjacent code):**
  - Task F1 is explicitly a reconnaissance task; F3 depends on its findings.
  - Task E1 references `sidequest_telemetry::test_support::capture_spans`; if that helper doesn't exist in the current telemetry crate, adding it is in scope for this task (it's a one-file helper).
  - Task G1 flags a potential circular-dependency between sidequest-protocol and sidequest-genre; the implementer picks the non-circular direction when they see the current `Cargo.toml` graph.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-layered-content-phase-1-framework-and-archetypes.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Matches the no-coexistence discipline because each subagent runs in a fresh context and commits per task.
2. **Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints for review.

Which approach?
