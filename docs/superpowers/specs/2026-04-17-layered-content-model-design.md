# Layered Content Model

Unified four-tier inheritance (`Global → Genre → World → Culture`) applied
uniformly across every content axis, replacing the current ad-hoc resolution
scattered across archetypes, audio, images, tropes, and scenarios.

## Problem

SideQuest's content inheritance is ad-hoc. Genre packs, worlds, and implicit
defaults resolve through undocumented fallthroughs scattered across multiple
loaders. Each content axis has its own resolution logic, its own merge
semantics, and its own opinions about where content lives.

The symptom that forced this spec: chargen in Evropi (a heavy_metal world)
surfaced "Iron Foundry" content that belonged to Long Foundry, the exemplar
world shipped alongside the heavy_metal genre pack. The narration and
mechanical flavor Keith saw as an Evropi player was authored for a completely
different world and leaked across the boundary because nothing enforced one.

Root causes:

1. **Porous authoring boundary.** When a genre is created, its exemplar world
   is authored in the same session. Opinionated world content leaks upward
   into the genre layer, then forward into every subsequent world that
   inherits from that genre.
2. **No provenance.** When resolved content surfaces in-game, nothing records
   which layer it came from. Debugging a flavor bug means grep expeditions
   across many YAML files.
3. **Silent fallthroughs.** If a world does not define something, the resolver
   silently walks the chain with no trace and no way to say "this world
   explicitly does not have that."
4. **Multiple independent resolvers.** Archetypes, audio, images, tropes, and
   scenarios each have their own resolution logic with different merge
   semantics per axis. No unified mental model, no shared diagnostic surface.

## Design Thesis

One layered content model, four fixed tiers, applied uniformly across every
content axis. Every tier has its own schema that structurally forbids content
belonging to other tiers — a genre YAML literally cannot express a named
funnel, because the genre schema has no field to hold one. Every resolved
field carries provenance (source tier, source file, source line range).
Culture is the terminal flavor pass — not cross-cutting, not optional, always
the deepest tier. One resolver. One OTEL span shape. No coexistence with old
loaders: when an axis migrates, its old code path is deleted in the same PR.

## Architecture

### The Resolver

A single generic `Resolver<T>` in `sidequest-genre` walks the chain
`Global → Genre → World → Culture` for every content axis. For each requested
field path (e.g., `archetype.thornwall_mender.lore`, or
`audio.leitmotifs.the_forge`), it produces a `Resolved<T>` carrying both the
final value and its full provenance trail.

```rust
pub struct Resolved<T> {
    pub value: T,
    pub provenance: Provenance,
}

pub struct Provenance {
    pub source_tier: Tier,              // Global | Genre | World | Culture
    pub source_file: PathBuf,           // e.g., worlds/evropi/audio.yaml
    pub source_span: Option<Span>,      // line range in the YAML
    pub merge_trail: Vec<MergeStep>,    // every tier that contributed and how
}

pub enum Tier { Global, Genre, World, Culture }

pub struct MergeStep {
    pub tier: Tier,
    pub file: PathBuf,
    pub span: Option<Span>,
    pub contribution: ContributionKind, // Initial | Replaced | Appended | Merged
}
```

Every resolution emits an OTEL span with `tier`, `field_path`,
`merge_strategy`, and the provenance trail. The GM panel gets a
"where did this content come from?" inspector backed by that stream.

### Per-Tier Schema Split

One schema per tier, enforced by the Rust type system. Each tier's schema is
a distinct struct type; a genre file and a world file cannot share fields
because they cannot share a struct.

- `crates/sidequest-genre/src/schema/global.rs` — `GlobalContent`. Axes,
  primitive SFX, universal negative prompts, base archetype tables. No
  proper nouns, no lore, no cultural specifics.
- `crates/sidequest-genre/src/schema/genre.rs` — `GenreContent`. Constraints,
  patterns, fallback *shapes* (not fallback names with lore), beat
  definitions, LoRA base style, ambient music library. No named instances of
  anything, no funnels, no POIs, no faction names, no leitmotifs tied to a
  specific named thing.
- `crates/sidequest-genre/src/schema/world.rs` — `WorldContent`. Named
  funnels, faction rosters, POI registry, leitmotif bindings (this named POI
  gets this motif), additional image prompts, world-specific audio and image
  directories.
- `crates/sidequest-genre/src/schema/culture.rs` — `CultureContent`. Corpus
  binding, speech patterns, visual cues, disposition graph, name-generation
  config, local-language overrides for archetype names, culture-specific
  scenario variants.

All four use `#[serde(deny_unknown_fields)]`. A genre author cannot put
`funnels:` at the genre layer — there is no field to deserialize into, and
serde rejects the load with a loud error naming the offending file and key.

### Merge Semantics

Fields annotate their merge strategy via a `#[derive(Layered)]` macro:

```rust
#[derive(Layered)]
pub struct ArchetypeResolved {
    #[layer(merge = "replace")]        pub name: String,
    #[layer(merge = "deep_merge")]     pub ocean_tendencies: OceanRanges,
    #[layer(merge = "append")]         pub quirks: Vec<Quirk>,
    #[layer(merge = "culture_final")]  pub speech_pattern: Option<String>,
}
```

Merge strategies:

- **`replace`** — deeper tier wins outright. Used for singular values like a
  display name.
- **`append`** — deeper tier's list extends the shallower tier's list. Used
  for audio leitmotifs, quirks, image prompt tokens.
- **`deep_merge`** — struct-walked merge, `replace` at leaves. Used for
  composite structures like OCEAN ranges.
- **`culture_final`** — only the Culture tier may set this field. Genre and
  World cannot. If no culture is assigned, the field resolves to its
  `Option::None` state with provenance tier `Culture` and a "no binding"
  marker.

Each content type ships sensible defaults so authoring rarely touches
annotations. Annotations override the default when a field needs atypical
semantics.

### Where This Code Lives

`sidequest-genre` gets the resolver and the four schema modules.
`sidequest-game` consumes `Resolved<T>` and surfaces `Provenance` on its
state structs. `sidequest-protocol` gains a `Provenance` type alongside
existing content types, and every `GameMessage` variant that carries
resolved content carries provenance with it. The server emits OTEL spans.
The UI's GM panel gets a provenance inspector (new component, small — reads
existing OTEL stream). All existing ad-hoc resolvers in `sidequest-genre`
are deleted when their axis migrates.

After migration, grep for `fn load_archetypes`, `fn load_audio`,
`resolve_genre_or_world_*` returns zero hits. All axes go through
`Resolver::resolve::<T>(path, context)`. One code path, one log shape, one
mental model.

## Per-Axis Schemas

Each axis applies the four-tier chain. A tier is often a no-op for a given
axis — that's fine, the chain is always traversed but empty tiers contribute
nothing. The *shape* of the schema at each tier is what makes the discipline
enforceable.

### Archetypes

| Tier | Holds |
|---|---|
| Global | Jungian axis, rpg_role axis, npc_role axis, OCEAN base tendencies, stat-affinity kinds |
| Genre | Valid pairings (common/uncommon/rare/forbidden), pattern-level speech styles, equipment tendencies, stat-name mapping |
| World | Named funnels, faction bindings, lore prose, cultural status, disposition graph, promotion seeds |
| Culture | Per-culture speech overrides, corpus binding for name generation, visual-cue overrides, local archetype name reskins |

### Audio

| Tier | Holds |
|---|---|
| Global | Universal SFX library (UI clicks, dice, notifications, system sounds) |
| Genre | Music library (all tracks available in this genre), ambient library, scene-to-track selection rules, stingers |
| World | Leitmotifs (named themes), faction music bindings, POI music overrides, world-specific ambient additions |
| Culture | Cultural instrumentation preferences, ceremonial music, a2a-variant leitmotifs per culture |

### Images

| Tier | Holds |
|---|---|
| Global | Universal negative prompt (no watermarks, no extra fingers, no text), render-resolution defaults |
| Genre | LoRA checkpoint path, base style prompt, color palette, composition defaults, `visual_style.yaml` |
| World | Additional prompt tokens, canned POI landscapes, world-level negative additions, map assets |
| Culture | Cultural visual cues (clothing, iconography, architecture), portrait facial/body tendencies |

### Tropes

| Tier | Holds |
|---|---|
| Global | Abstract trope *roles* (the mentor leaves, the rival returns, the price is paid) |
| Genre | Trope rule definitions, mechanical weight, progression curves, trigger patterns, basic abilities per trope |
| World | Named trope instances bound to specific NPCs/factions/POIs, hand-authored trope beats |
| Culture | Cultural expressions of tropes — how this culture performs "the price is paid," cultural disposition modifiers |

### Scenarios

| Tier | Holds |
|---|---|
| Global | Scenario primitive types (combat, chase, duel, trial, poker, dogfight), universal beat grammar |
| Genre | Which scenarios are available in this genre, combat roles, beat vocabulary, hit/damage tables, progression increments |
| World | Named encounters bound to POIs, hand-authored scenario beats for story-critical moments |
| Culture | Cultural scenario variants — a duel in Thornwall is pistols-at-dawn, in Highmark is ritual flyting, in the Fool's Guild is bare-knuckle boxing |

### Cross-Axis Invariants

- Global never holds proper nouns.
- Genre never holds named instances of anything.
- World never holds culture-specific flavor (that belongs at Culture).
- Culture never holds structural rules (those are Genre or Global).
- When a tier has nothing to contribute for a given axis, it is absent from
  the filesystem, not a silent empty string.

## Culture as a First-Class Entity

### Directory Shape

Cultures live as subdirectories of their world. One culture = one directory:

```
genre_packs/heavy_metal/worlds/evropi/
  cultures/
    thornwall/
      culture.yaml             # identity, represents, corpus binding
      speech.yaml              # speech-pattern overrides per archetype
      visual.yaml              # clothing, iconography, architectural cues
      disposition.yaml         # stance toward other cultures
      archetype_reskins.yaml   # local names for funneled archetypes
      audio/                   # ceremonial music, culture-specific leitmotif variants
    highmark/
      culture.yaml
      ...
    fools_guild/
      culture.yaml
      ...
```

No flat `cultures.yaml` list at world root. The Culture tier has its own
discrete files under its own directory — the filesystem itself encodes tier
membership.

### `culture.yaml` Contents

```yaml
id: thornwall
display_name: Thornwall
represents: faction          # Race | Faction | Class | Composite
corpus_binding:
  primary: corpus/old_germanic
  secondary: corpus/mercian_latin
default_disposition_lean: cautious
```

Separate files (`speech.yaml`, `visual.yaml`, `disposition.yaml`,
`archetype_reskins.yaml`) keep each concern in its own small file —
consistent with the schema-is-the-discipline principle.

### No Cross-World Sharing (v1)

Two worlds that both want "Elves" duplicate the culture directory. Cultures
are world-sovereign: Elves in Iron Marches and Elves in Shattered Reach are
different Elves that happen to share a linguistic label. The shared name is
a coincidence, not a shared entity.

Rationale: a cross-world library would re-introduce the exact "named content
at genre" loophole the schema split exists to close. If duplication becomes
a real burden later, a shared-catalog mechanism with explicit `imports:` can
be added as a follow-on spec.

### One Primary Culture per Character

A PC or NPC has exactly one culture assignment. Resolution is deterministic
— no stacking, no "which disposition wins when I'm half-Thornwall
half-Highmark." Secondary affiliations (faction memberships, adopted
loyalties) attach to the character as relationships, not as additional
culture layers in the resolver.

### Chargen Integration

Culture becomes a chargen step, typically after Jungian + RPG Role are
chosen but before backstory. The player picks from the world's declared
cultures (enumerated by scanning `worlds/<world>/cultures/*/`). The
axes-plus-culture resolution produces the final named archetype with
culture-local reskinning. The narrator sees the reskinned name; the
mechanical axes remain stable underneath.

Example: `[sage, healer]` in Thornwall surfaces as "Thornwall Mender;" the
same axes in Highmark surface as "Forge-Mother."

### NPC Generation

POIs in `cartography.yaml` declare `primary_culture:` and optional
`secondary_cultures:` with weights. NPC spawns at that POI roll culture
from that weighted distribution. Cross-culture NPCs (a Highmark merchant
visiting a Thornwall village) are modeled explicitly in world lore, not as
emergent resolver output.

### Culture's Role in Resolution

Culture is the terminal flavor pass. It never overrides mechanical
structure — OCEAN tendencies stay from Global, stat affinities stay from
Genre, funnel structure stays from World. It overrides *presentation* —
names, speech patterns, visual cues, ceremonial details, scenario variants.

Structurally: the `#[layer(merge = "culture_final")]` annotation marks a
field that only Culture can set. If no culture is assigned, the field
resolves to its `None` state with provenance tier `Culture` and a
"no binding" marker — not a silent genre fallthrough.

## Migration Sequencing

Every migration PR both adds the new path and deletes the old. No
framework-exists-but-nobody-uses-it state, ever. That shapes the phase
ordering:

### Phase 1 — Framework + Archetypes (one PR, indivisible)

The resolver, per-tier schema types, `Resolved<T>`, `Provenance`, OTEL
spans, and the `Layered` derive macro ship together with the archetype
migration. Archetypes go first because the three-axis system (merged in
`c9c8cac`) is structurally closest to the target model — smallest jump,
cleanest framework validation.

On merge: archetypes resolve through the new path; `fn load_archetypes`
and its ad-hoc fallthrough logic are deleted; OTEL provenance is visible
in the GM panel for every resolved archetype. Grep for the old loader
returns zero hits.

### Phase 2 — Tropes + Culture (one PR)

Tropes is the axis most entangled with Culture, so Culture becomes real
here. The PR:

- Introduces the `CultureContent` schema and the
  `worlds/<world>/cultures/<culture>/` directory contract.
- Migrates every existing world to author its cultures as directories
  (Evropi, Long Foundry, Iron Marches, Shattered Reach, The Circuit,
  etc.). This is mechanical — existing `cultures.yaml` rows become
  culture directories with their contents split across the new schema
  files.
- Migrates the trope loader to the new resolver. Culture-tier trope
  expressions (how this culture performs "the price is paid") become
  authorable.
- Deletes the old trope loader and both the genre-level and flat
  world-level `cultures.yaml` files.

Biggest PR after Phase 1 because it touches every world's content, but
the ceiling is content migration mechanics, not framework risk.

### Phase 3 — Audio

Adds `worlds/<world>/audio/` directories where missing. Migrates the
audio resolver. Leitmotifs become named, world-level entities with
declared bindings to POIs/factions/characters. Culture-level
instrumentation variants land (optional — a culture can declare a
ceremonial-music set, or leave the tier empty). Deletes the old audio
loader. Music library at genre stays genre; leitmotifs move to world.

### Phase 4 — Images

Adds `worlds/<world>/images/` (additional prompts, canned POI
landscapes, world-level negative additions). Adds culture-level
`visual.yaml` (clothing, iconography). Migrates the image-prompt
composition path. Deletes the old prompt composer. LoRA base stays at
genre.

### Phase 5 — Scenarios

Scenarios have the least genre-pack footprint (most scenario logic
lives in API crates). Migration surface is smaller: combat roles, beat
definitions, hit tables move through the resolver; world-level scenario
bindings (named encounters, story-critical beats) get their schema.
Culture-level scenario variants land (duel-as-pistols vs duel-as-flyting).
Deletes the old scenario loader.

### Phase 6 — Sweep & Close

Spec-close gate. Hard checks before merge:

- Grep for the old loader function names — must return zero.
- Grep for flat `cultures.yaml` anywhere in the tree — must return zero.
- Every content axis resolves through `Resolver<T>`.
- Every axis emits OTEL provenance.
- Every resolved field in the GM panel shows tier + file + line.
- Spec's Delivery Findings section closed, no deferred wiring.

### Invariants

Two invariants are non-negotiable across phases:

1. **No phase ships framework without a consumer.** Phase 1 is
   framework+archetypes indivisibly. No phase adds infrastructure without
   wiring it to real content.
2. **No phase ships a new axis without deleting the old loader.** If the
   PR contains `fn new_loader(...)` it also contains the deletion of
   `fn old_loader(...)`.

Flexible: the order of phases 3 / 4 / 5 can shuffle if playtest surfaces
a higher-priority axis. Phase 1 must be first. Phase 2 must be second
(Culture is needed before audio/images/scenarios can use culture-level
overrides). Phase 6 must be last.

## OTEL Observability and Provenance

Every resolution emits one span. If you cannot see a resolution in the
OTEL stream, it did not happen through the framework — that is a wiring
bug.

### Span Shape

Name: `content.resolve`. Emitted once per call to
`Resolver::resolve::<T>(field_path, context)`.

Required attributes:

```
content.axis                 = "archetype" | "audio" | "image" | "trope" | "scenario"
content.field_path           = "archetype.thornwall_mender.lore"
content.genre                = "heavy_metal"
content.world                = "evropi"
content.culture              = "thornwall"   (absent if no culture binding)
content.source_tier          = "Global" | "Genre" | "World" | "Culture"
content.source_file          = "worlds/evropi/cultures/thornwall/archetype_reskins.yaml"
content.source_span          = "12:1-18:0"   (line range)
content.merge_strategy       = "replace" | "append" | "deep_merge" | "culture_final"
content.merge_trail          = JSON array of contributing tiers
content.elapsed_us           = integer
```

`content.merge_trail` entries are `{tier, file, span, contribution}`. The
final value is reconstructible from the trail alone.

### When Spans Emit

Every resolve call, always, no sampling. Resolutions are cheap. If span
volume becomes a real problem post-rewrite, the span can move behind a
`SIDEQUEST_DEBUG_PROVENANCE` flag — but default-on through the entire
migration sprint.

### Error Paths

If resolution fails (missing required field, schema mismatch, culture not
found), the span carries `content.resolve.error = "<reason>"` and
`content.resolve.fallback = "<what we returned instead>"` — with the hard
rule that fallbacks are *declared, not silent*. A missing field with no
declared fallback is a loud failure, not `Default::default()`.

### GM Panel Provenance Inspector

A new panel tab or sidebar drawer. The inspector is always available;
no spoiler-hiding gymnastics. If Keith looks at the inspector (or at
source YAML directly) and spoils himself, that is his choice. The tool
is a debugger, not a dramaturge.

For any content currently on screen — a character's archetype name, a
leitmotif playing, an image rendered, a trope that just fired — the
inspector shows:

- Field path being resolved
- Final value
- Source tier (color-coded badge: Global / Genre / World / Culture)
- Source file with line range
- Full merge trail as a collapsible list

Data source: the OTEL stream the GM panel already consumes. New component
subscribes to `content.resolve` spans, indexes the most recent by
`content.field_path`, renders on demand.

### End-to-End Traceability

Four-step chain, all four must hold for every rendered piece of content:

1. **UI shows it** (character panel, narration, audio, image).
2. **Protocol carries provenance** — the relevant `GameMessage` or state
   snapshot includes the `Provenance` struct alongside the value. No bare
   strings traveling without source attribution.
3. **Span emitted** at resolve time in Rust, with full attributes.
4. **Source YAML file + line is reachable** — the span's source_file +
   source_span point to real bytes on disk, not a computed-at-runtime
   synthetic.

### What This Prevents

The Iron Foundry bug has a specific diagnostic signature under this
contract: chargen in Evropi surfaces "Iron Foundry," the player opens the
provenance inspector, and immediately sees
`source_tier: Genre, source_file: heavy_metal/char_creation.yaml,
source_span: 142-156` — the exact lines where exemplar-world content
leaked into the genre layer. Diagnosis takes seconds instead of a grep
expedition. After the schema split ships the file-load itself fails loudly
— but provenance is what makes any *future* leak diagnosable at a glance.

## Authoring Review Model

The four-tier schema split has a direct consequence for how new content
gets reviewed before shipping to playtest. The review boundary runs
along the same line as the schema boundary:

- **Global + Genre (mechanical content) — reviewed before merge.**
  Rules, tables, axes, constraints, beat grammar, valid pairings, damage
  increments, progression curves, combat roles. Keith reviews these.
  Mechanical surprises in playtest break the game; they are bugs, not
  features.
- **World + Culture (flavor content) — ships unreviewed.** Faction
  names, archetype reskins, leitmotif prose, trope flavor, POI details,
  cultural speech patterns, disposition graphs. Keith discovers these
  in playtest as a player. Agent-authored flavor does not get
  per-faction review.

This keeps playtest meaningful as a first encounter with world flavor
while still gating the mechanical layer. The tier schema is the
mechanism: if a field is annotated `#[layer(merge = "culture_final")]`
or lives in a `WorldContent` or `CultureContent` struct, it's flavor
and it ships without per-item review. If it lives in `GlobalContent` or
`GenreContent`, it's mechanical and Keith sees it before merge.

### Verification Strategy

**Long Foundry is the spoilable test-bed world.** Keith authored it
alongside heavy_metal, so it is already spoiled for him — the canonical
world for verifying the resolver mechanic end-to-end. Integration tests
and playtest correctness checks run against Long Foundry. Evropi and
other worlds stay unspoiled and serve as fresh surprise-surfaces for
flavor verification. The Iron Foundry regression test specifically uses
Evropi because Evropi is supposed to have no Long Foundry content in
its resolution trail.

## Testing Strategy

### Layer 1 — Unit Tests

Location: `crates/sidequest-genre/src/` with `#[cfg(test)]` modules.
Runner: `cargo nextest run -p sidequest-genre`.

- Schema parsing per tier. Known-good fixture deserializes; out-of-tier
  content (e.g., a genre fixture with a `funnels:` key) fails to load with
  a loud error.
- Merge strategies. One test per strategy (`replace`, `append`,
  `deep_merge`, `culture_final`), asserting both final value and merge
  trail length.
- Derive macro. Compile-fail tests (trybuild or equivalent) for invalid
  `#[layer(...)]` annotations.

### Layer 2 — Integration Tests

Location: `crates/sidequest-genre/tests/`.

- Full-chain resolution. Load Evropi under heavy_metal with the Thornwall
  culture, resolve `archetype.thornwall_mender.display_name`, assert
  value and provenance. Cover a resolution from each tier.
- Cross-axis parity. Same test fixture exercised against archetypes /
  audio / images / tropes / scenarios — confirms the resolver shape is
  uniform.
- **Iron Foundry regression test.** Load `heavy_metal/evropi`, resolve
  every field exercised by chargen, assert no field's `source_file`
  contains `long_foundry`. This test is the bug's permanent gravestone.

### Layer 3 — Wiring Tests (mandatory per CLAUDE.md)

- Non-test consumer check. Grep-based assertion that the new resolver has
  a production consumer in `sidequest-server` or `sidequest-game`.
  Equivalent for the old loader: after its axis migrates, a grep asserts
  the old function name is not present anywhere in the tree.
- Protocol-to-UI provenance. Integration test running the server
  end-to-end for a synthetic chargen session, intercepting the
  `GameMessage` carrying the resolved archetype, asserting `Provenance`
  is populated.
- GM panel consumption. UI test feeding a mock `content.resolve` span
  into the provenance inspector, asserting the expected badge, file path,
  and merge trail render.

### Layer 4 — Content Validation

Runs in `just api-check` and as a pre-commit hook.

- Pack linter. For each genre pack under `sidequest-content/`, walk the
  filesystem and try to load every file into its expected tier schema.
  Any file that fails the tier's schema is a structural error.
- Cultures-as-directories check. Asserts no flat `cultures.yaml` exists
  anywhere. Asserts every existing world has at least one
  `cultures/<name>/` directory during the spec window.

### Layer 5 — Schema Round-Trip

Serialize-deserialize round-trip per tier schema. Catches asymmetric
serde config before it causes a content-loading mystery.

### What Runs Where

- `just api-test` (local, required green before handoff): Layers 1, 2, 3.
  Local checks are the gate — CI is not blocking on OQ-2.
- `just check-all`: above plus Layer 4 content linter plus the UI
  provenance test. Full pre-merge gate.
- Pre-commit hook: Layer 4 content linter only. Cheap, catches
  misplacements the moment an author saves a YAML.

### What Is Not Tested Automatically

- Flavor quality. Whether a resolved archetype name feels right is Keith's
  call at the GM panel, not a unit test's. Surface telemetry for human
  judgment; don't use AI to judge AI.
- Cross-playtest behavioral drift. Integration tests lock the shape of
  resolutions, not their content. Author-driven content changes are
  content PRs, not test failures.

## Out of Scope / Future

- Cross-world cultures library. Deferred unless duplication becomes a
  real authoring burden. Any v2 proposal must preserve the "genre holds
  no named content" discipline via explicit `imports:`.
- Culture-as-mixin mechanic (stacking multiple cultures per character).
  Would require rethinking resolution determinism.
- Additional archetype axes beyond Jungian / RPG Role / NPC Role.
- Cross-genre content reuse (a trope that applies to multiple genres).
  Current scope is single-genre resolution only.

## Appendix A — Illustrative YAML

### Global tier: `sidequest-content/archetypes_base.yaml`

```yaml
jungian:
  - id: sage
    ocean_tendencies:
      openness: [7.0, 9.5]
      conscientiousness: [6.0, 8.0]
      extraversion: [2.0, 5.0]
      agreeableness: [4.0, 7.0]
      neuroticism: [3.0, 6.0]
    stat_affinity: [wisdom, intellect, insight]

rpg_roles:
  - id: healer
    stat_affinity: [wisdom, support]
    combat_function: restoration

npc_roles:
  - id: mentor
    narrative_function: guides protagonist, provides knowledge
```

### Genre tier: `heavy_metal/archetype_constraints.yaml`

```yaml
valid_pairings:
  common:
    - [hero, tank]
    - [sage, healer]
    - [outlaw, stealth]
  rare:
    - [innocent, stealth]
  forbidden:
    - [innocent, dps]

genre_flavor:
  sage:
    speech_pattern: "measured, references to old engineering manuals"
    equipment_tendency: "scarred tools, leather apron, soot-stained hands"
```

### World tier: `heavy_metal/worlds/evropi/archetype_funnels.yaml`

```yaml
funnels:
  - name: Thornwall Mender
    absorbs:
      - [sage, healer]
      - [caregiver, healer]
      - [caregiver, support]
    faction: Thornwall Convocation
    lore: >-
      Itinerant healers traveling the border villages under the
      Convocation's charter.
    cultural_status: respected but watched
```

### Culture tier: `heavy_metal/worlds/evropi/cultures/thornwall/archetype_reskins.yaml`

```yaml
reskins:
  Thornwall Mender:
    display_name: Thornwall Mender
    speech_pattern: "archaic Germanic cadence, rarely uses contractions"
    visual_cues:
      - "thornwood staff with green wrist cord"
      - "herb satchel"
```

## Appendix B — Current Evropi vs Target

The current Evropi setup has three structural violations against the target
design. All three resolve in Phase 2 (Tropes + Culture) migration.

1. **Lore at genre level.** `heavy_metal/lore.yaml` holds prose that
   belongs at the world tier. Target: this content moves to
   `worlds/<world>/lore.yaml` where it already partially exists, and the
   genre-level file is deleted.
2. **Chargen flavor at genre level.** `heavy_metal/char_creation.yaml`
   contains the Iron Foundry content that leaked into Evropi. Under the
   new schema, the file can hold chargen scene *shape* (beats, axis
   mappings) but not named instances or specific flavor prose. Named
   content moves to per-world chargen files.
3. **Cultures at genre level.** `heavy_metal/cultures.yaml` and
   `worlds/evropi/cultures.yaml` both exist. Target: both are deleted;
   each culture becomes a subdirectory under
   `worlds/<world>/cultures/<culture>/` with its contents split across
   the Culture-tier schema files.

Additionally:

- Evropi has no `worlds/evropi/audio/` or `worlds/evropi/images/`
  directories. Phase 3 and Phase 4 add these directories, empty at first,
  then populate them with Evropi-specific leitmotifs, POI landscapes, and
  visual notes.
- `heavy_metal/corpus/` is currently loaded by genre-level code. Under
  the new design, corpora are referenced by `corpus_binding:` from
  Culture `culture.yaml` files, and the corpus directory stays shared
  under the genre pack as a neutral library (data, not named content).
