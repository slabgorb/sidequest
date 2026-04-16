# Three-Axis Archetype System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the disconnected archetypes.yaml + char_creation.yaml systems with a unified three-axis archetype model (Jungian + RPG Role + NPC Role) using base->genre->world inheritance, funneling into named world archetypes for both PC chargen and NPC generation.

**Architecture:** Three inheritance layers (base -> genre -> world) with genre-level constraints (valid pairings weighted common/uncommon/rare/forbidden) and world-level funnels (many-to-one axis-combination-to-named-archetype mappings). PC chargen and NPC gen share the same pipeline; PCs use Jungian + RPG Role, NPCs add NPC Role. Resolution tiers (spawn/engage/promote) control NPC enrichment depth.

**Tech Stack:** YAML content files (sidequest-content), Rust structs/loader (sidequest-genre), Rust builder FSM (sidequest-game), Rust namegen CLI (sidequest-namegen), Rust dispatch (sidequest-server)

**Spec:** `docs/superpowers/specs/2026-04-16-three-axis-archetype-system-design.md`

---

## Phase 1: Content Schema & Base Layer (YAML)

Create the base-layer YAML definitions and schema files. No Rust changes yet — this phase establishes the content that the loader will consume.

### Task 1: Create base archetype definitions

**Files:**
- Create: `sidequest-content/archetypes_base.yaml`

- [ ] **Step 1: Create base Jungian archetype definitions**

```yaml
# archetypes_base.yaml — genre-agnostic archetype axes
# Resolution chain: base -> genre -> world

jungian:
  - id: caregiver
    drive: "Protects and nurtures others"
    ocean_tendencies:
      openness: [4.0, 6.5]
      conscientiousness: [6.0, 8.5]
      extraversion: [4.5, 7.0]
      agreeableness: [7.0, 9.5]
      neuroticism: [3.0, 6.0]
    stat_affinity: [support, endurance, wisdom]

  - id: ruler
    drive: "Controls and leads through authority"
    ocean_tendencies:
      openness: [3.5, 6.0]
      conscientiousness: [7.0, 9.0]
      extraversion: [6.0, 8.5]
      agreeableness: [2.5, 5.5]
      neuroticism: [2.0, 5.0]
    stat_affinity: [command, presence, intellect]

  - id: artist
    drive: "Creates enduring works and visions"
    ocean_tendencies:
      openness: [8.0, 9.5]
      conscientiousness: [3.0, 6.0]
      extraversion: [3.0, 6.5]
      agreeableness: [4.5, 7.0]
      neuroticism: [5.0, 8.0]
    stat_affinity: [craft, perception, dexterity]

  - id: innocent
    drive: "Seeks safety and does the right thing"
    ocean_tendencies:
      openness: [5.0, 7.5]
      conscientiousness: [5.5, 8.0]
      extraversion: [4.0, 7.0]
      agreeableness: [7.5, 9.5]
      neuroticism: [4.0, 7.0]
    stat_affinity: [faith, endurance, spirit]

  - id: sage
    drive: "Seeks truth and understanding"
    ocean_tendencies:
      openness: [7.0, 9.5]
      conscientiousness: [6.0, 8.0]
      extraversion: [2.0, 5.0]
      agreeableness: [4.0, 7.0]
      neuroticism: [3.0, 6.0]
    stat_affinity: [wisdom, intellect, insight]

  - id: explorer
    drive: "Seeks freedom through discovery"
    ocean_tendencies:
      openness: [8.0, 9.5]
      conscientiousness: [2.5, 5.0]
      extraversion: [5.0, 7.5]
      agreeableness: [4.0, 6.5]
      neuroticism: [2.0, 5.0]
    stat_affinity: [perception, agility, endurance]

  - id: outlaw
    drive: "Breaks rules to overturn what isn't working"
    ocean_tendencies:
      openness: [6.0, 8.5]
      conscientiousness: [2.0, 4.5]
      extraversion: [4.0, 7.0]
      agreeableness: [2.0, 4.5]
      neuroticism: [4.0, 7.0]
    stat_affinity: [cunning, agility, nerve]

  - id: magician
    drive: "Transforms reality through understanding"
    ocean_tendencies:
      openness: [8.5, 9.5]
      conscientiousness: [5.0, 7.5]
      extraversion: [3.0, 6.0]
      agreeableness: [3.5, 6.0]
      neuroticism: [3.0, 6.0]
    stat_affinity: [intellect, wisdom, spirit]

  - id: hero
    drive: "Proves worth through courageous action"
    ocean_tendencies:
      openness: [5.0, 7.0]
      conscientiousness: [6.0, 8.5]
      extraversion: [6.0, 8.5]
      agreeableness: [5.0, 7.5]
      neuroticism: [2.0, 4.5]
    stat_affinity: [strength, endurance, courage]

  - id: lover
    drive: "Pursues connection and intimacy"
    ocean_tendencies:
      openness: [6.0, 8.5]
      conscientiousness: [4.0, 6.5]
      extraversion: [6.0, 8.5]
      agreeableness: [7.0, 9.0]
      neuroticism: [5.0, 8.0]
    stat_affinity: [presence, empathy, perception]

  - id: jester
    drive: "Lives in the moment with joy and mischief"
    ocean_tendencies:
      openness: [7.0, 9.0]
      conscientiousness: [2.0, 4.0]
      extraversion: [7.5, 9.5]
      agreeableness: [5.0, 7.5]
      neuroticism: [2.0, 4.5]
    stat_affinity: [agility, cunning, presence]

  - id: everyman
    drive: "Belongs and connects through common ground"
    ocean_tendencies:
      openness: [4.0, 6.0]
      conscientiousness: [5.0, 7.0]
      extraversion: [5.0, 7.0]
      agreeableness: [6.0, 8.0]
      neuroticism: [4.0, 6.0]
    stat_affinity: [endurance, presence, adaptability]

rpg_roles:
  - id: tank
    combat_function: "Absorbs damage, protects allies"
    stat_affinity: [strength, endurance, constitution]

  - id: dps
    combat_function: "Deals sustained or burst damage"
    stat_affinity: [strength, agility, precision]

  - id: control
    combat_function: "Manipulates battlefield, disables enemies"
    stat_affinity: [intellect, wisdom, cunning]

  - id: healer
    combat_function: "Restores allies, removes conditions"
    stat_affinity: [wisdom, spirit, empathy]

  - id: stealth
    combat_function: "Avoids detection, strikes from surprise"
    stat_affinity: [agility, cunning, perception]

  - id: support
    combat_function: "Buffs allies, debuffs enemies"
    stat_affinity: [presence, intellect, spirit]

  - id: jack_of_all_trades
    combat_function: "Flexible, fills gaps, no specialization"
    stat_affinity: [adaptability, endurance, cunning]

npc_roles:
  - id: mentor
    narrative_function: "Guides protagonist, provides knowledge or training"
  - id: herald
    narrative_function: "Announces change, catalyzes the adventure"
  - id: shadow
    narrative_function: "Embodies what the protagonist fears or rejects"
  - id: threshold
    narrative_function: "Guards a boundary, tests worthiness"
  - id: host
    narrative_function: "Provides shelter, information, or services"
  - id: artisan
    narrative_function: "Creates, repairs, or supplies equipment and goods"
  - id: authority
    narrative_function: "Represents institutional power and social order"
  - id: victim
    narrative_function: "Needs rescue or protection, raises stakes"
  - id: mook
    narrative_function: "Disposable opposition, exists to be overcome"
    skip_enrichment: true
```

- [ ] **Step 2: Validate YAML parses correctly**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/archetypes_base.yaml')); print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add archetypes_base.yaml
git commit -m "content: add base archetype axis definitions (jungian, rpg_role, npc_role)"
```

### Task 2: Create genre-level constraint file for low_fantasy (proof of concept)

**Files:**
- Create: `sidequest-content/genre_packs/low_fantasy/archetype_constraints.yaml`

- [ ] **Step 1: Create constraint definitions**

```yaml
# archetype_constraints.yaml — low_fantasy
# Defines valid Jungian x RPG Role pairings for this genre
# common: chargen default, NPC gen draws most
# uncommon: shown if player explores, NPC diversity
# rare: allowed but unusual, memorable characters
# forbidden: nonsensical for this genre

valid_pairings:
  common:
    - [hero, tank]
    - [hero, dps]
    - [sage, healer]
    - [sage, control]
    - [outlaw, stealth]
    - [outlaw, dps]
    - [caregiver, healer]
    - [caregiver, support]
    - [ruler, tank]
    - [ruler, support]
    - [explorer, stealth]
    - [explorer, jack_of_all_trades]
    - [magician, control]
    - [magician, dps]
    - [everyman, jack_of_all_trades]
    - [everyman, support]

  uncommon:
    - [artist, support]
    - [artist, control]
    - [lover, support]
    - [lover, healer]
    - [jester, stealth]
    - [jester, dps]
    - [innocent, healer]
    - [innocent, support]
    - [hero, jack_of_all_trades]
    - [sage, support]
    - [outlaw, control]

  rare:
    - [jester, tank]
    - [innocent, tank]
    - [lover, dps]
    - [artist, stealth]
    - [everyman, tank]
    - [everyman, dps]

  forbidden:
    - [innocent, stealth]
    - [innocent, dps]
    - [caregiver, stealth]

# Genre-level fallback names and flavor for each axis value
# Used when no world-level funnel claims a combination
genre_flavor:
  jungian:
    hero:
      speech_pattern: "direct, declarative, sparse"
      equipment_tendency: "well-maintained weapons, practical armor"
      visual_cues: "scarred hands, upright posture, watchful eyes"
    sage:
      speech_pattern: "measured, archaic vocabulary, references to old texts"
      equipment_tendency: "robes, walking staff, herb pouch, journal"
      visual_cues: "weathered hands, ink-stained fingers, squinting eyes"
    outlaw:
      speech_pattern: "clipped, evasive, dark humor"
      equipment_tendency: "concealed blades, dark clothing, lockpicks"
      visual_cues: "hood or scarf, restless gaze, calloused fingers"
    caregiver:
      speech_pattern: "warm, patient, firm when needed"
      equipment_tendency: "healer's kit, sturdy cloak, provisions for others"
      visual_cues: "gentle hands, worry lines, attentive posture"
    ruler:
      speech_pattern: "commanding, formal, economical with words"
      equipment_tendency: "quality weapons, signet ring, heraldic tokens"
      visual_cues: "upright bearing, steady gaze, deliberate movements"
    explorer:
      speech_pattern: "excited about geography, casual, trail-worn idiom"
      equipment_tendency: "rope, maps, climbing gear, worn boots"
      visual_cues: "sun-weathered skin, lean build, distant gaze"
    magician:
      speech_pattern: "precise, layered meanings, uncomfortable with small talk"
      equipment_tendency: "focus object, reagent pouch, annotated grimoire"
      visual_cues: "unusual eye color, faint smell of ozone or herbs"
    artist:
      speech_pattern: "observational, metaphor-heavy, emotionally present"
      equipment_tendency: "tools of craft, sketchbook, instrument"
      visual_cues: "paint under nails, callused fingertips, distracted gaze"
    innocent:
      speech_pattern: "earnest, questions assumed truths, occasionally naive"
      equipment_tendency: "simple weapon, family keepsake, homespun clothes"
      visual_cues: "open face, fidgeting hands, wide eyes"
    lover:
      speech_pattern: "attentive, emotionally fluent, remembers names"
      equipment_tendency: "token from someone, presentable clothes, perfume"
      visual_cues: "expressive face, graceful movement, warm smile"
    jester:
      speech_pattern: "quick wit, deflects with humor, breaks tension"
      equipment_tendency: "motley, hidden blade, props, flask"
      visual_cues: "mischievous eyes, animated gestures, sly grin"
    everyman:
      speech_pattern: "plain, relatable, local dialect"
      equipment_tendency: "practical tools, nothing flashy, worn but functional"
      visual_cues: "unremarkable build, tired eyes, calloused hands"

  rpg_roles:
    tank:
      fallback_name: "Shield-Bearer"
    dps:
      fallback_name: "Blade"
    control:
      fallback_name: "Warder"
    healer:
      fallback_name: "Hedge Healer"
    stealth:
      fallback_name: "Shadow"
    support:
      fallback_name: "Warden"
    jack_of_all_trades:
      fallback_name: "Wanderer"

# NPC roles available in this genre (all enabled for low_fantasy)
npc_roles_available:
  - mentor
  - herald
  - shadow
  - threshold
  - host
  - artisan
  - authority
  - victim
  - mook
```

- [ ] **Step 2: Validate YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/low_fantasy/archetype_constraints.yaml')); print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/low_fantasy/archetype_constraints.yaml
git commit -m "content(low_fantasy): add archetype constraint definitions"
```

### Task 3: Create world-level funnel file for low_fantasy/shattered_reach

**Files:**
- Create: `sidequest-content/genre_packs/low_fantasy/worlds/shattered_reach/archetype_funnels.yaml`

- [ ] **Step 1: Read existing shattered_reach world data for lore context**

Read: `sidequest-content/genre_packs/low_fantasy/worlds/shattered_reach/world.yaml`
Read: `sidequest-content/genre_packs/low_fantasy/worlds/shattered_reach/lore.yaml`
Read: `sidequest-content/genre_packs/low_fantasy/worlds/shattered_reach/cultures.yaml`

Use faction names, cultural details, and locations from these files to inform funnel names and lore.

- [ ] **Step 2: Create funnel definitions**

The funnels below are illustrative — actual names and lore must be derived from the world data read in step 1. Each funnel absorbs multiple axis combinations and carries lore payload.

```yaml
# archetype_funnels.yaml — low_fantasy/shattered_reach
# Many-to-one mappings from [jungian, rpg_role] -> named world archetype
# Resolution: if a combination matches a funnel, use it. Otherwise fall back to genre.

funnels:
  - name: Thornwall Mender
    absorbs:
      - [sage, healer]
      - [caregiver, healer]
      - [caregiver, support]
    faction: Thornwall Convocation
    lore: >-
      Itinerant healers who travel the border villages under the
      Convocation's charter. Recognized by their thornwood staves
      and the green cord at their wrist. They answer to no lord
      but owe a tithe of service to the Convocation each spring.
    cultural_status: respected but watched
    disposition_toward:
      Iron Guard: cautious
      Freeholders: trusted

  - name: Iron Warden
    absorbs:
      - [hero, tank]
      - [ruler, tank]
      - [everyman, tank]
    faction: Iron Guard
    lore: >-
      The standing shield-wall of the Reach. Wardens patrol the
      border marches in paired circuits, sleeping in waystation
      bunks and eating what the villages provide. Most are
      conscripts who stayed; a few are second sons with no
      inheritance.
    cultural_status: feared and necessary
    disposition_toward:
      Thornwall Convocation: wary
      Freeholders: protective

  - name: Ashen Blade
    absorbs:
      - [hero, dps]
      - [outlaw, dps]
      - [lover, dps]
    faction: null
    lore: >-
      Sell-swords and duelists who name themselves after the
      volcanic glass found in the northern crags. No formal
      organization — the name is a reputation, not a guild.
      An Ashen Blade is someone who fights for coin and keeps
      their word about it.
    cultural_status: tolerated
    disposition_toward:
      Iron Guard: professional respect

  - name: Fool's Errand
    absorbs:
      - [jester, stealth]
      - [jester, dps]
      - [outlaw, stealth]
    faction: The Fool's Errand
    lore: >-
      Part spy network, part traveling performers. They carry
      news between villages faster than any official courier
      and know things no entertainer should. Nobody takes them
      seriously, which is exactly how they like it.
    cultural_status: tolerated, secretly feared

  - name: Reach Scholar
    absorbs:
      - [sage, control]
      - [sage, support]
      - [magician, control]
      - [magician, dps]
    faction: null
    lore: >-
      Self-taught or monastery-trained, the scholars of the
      Reach are rare and distrusted. Magic here is a practical
      matter — ward-stones, weather-reading, pest control —
      not the grand sorcery of the old stories. A scholar who
      gets too ambitious tends to disappear.
    cultural_status: useful but suspect

  - name: Hearthkeeper
    absorbs:
      - [caregiver, healer]
      - [everyman, support]
      - [innocent, healer]
      - [innocent, support]
    faction: null
    lore: >-
      The backbone of every village. Hearthkeepers manage
      the communal stores, tend the sick when no Mender is
      near, and settle disputes before they become feuds.
      No title, no pay, no glory — just the knowledge that
      the village stands because someone held it together.
    cultural_status: invisible but essential

  - name: Drifter
    absorbs:
      - [explorer, stealth]
      - [explorer, jack_of_all_trades]
      - [outlaw, control]
      - [everyman, jack_of_all_trades]
    faction: null
    lore: >-
      People who move. Traders, seasonal workers, refugees,
      deserters, people running from something they won't
      name. The Reach has always had drifters — the roads
      were built for them, or by them, depending on who
      you ask.
    cultural_status: watched

  # Additional funnels to cover remaining common/uncommon pairings
  - name: Reeve
    absorbs:
      - [ruler, support]
      - [ruler, tank]
    faction: null
    lore: >-
      Village-appointed administrators who speak for the
      settlement to passing lords, tax collectors, and
      Iron Guard patrols. Part politician, part protector,
      entirely exhausted.
    cultural_status: burdened authority

  - name: Greencloak
    absorbs:
      - [artist, support]
      - [artist, control]
      - [artist, stealth]
    faction: null
    lore: >-
      Wandering craftspeople — woodcarvers, weavers, potters,
      musicians — who wear a green cloak as mark of their
      trade guild. They barter skill for lodging and carry
      the aesthetic memory of the Reach from village to village.
    cultural_status: welcome guests

  - name: Sworn Companion
    absorbs:
      - [lover, support]
      - [lover, healer]
      - [hero, jack_of_all_trades]
    faction: null
    lore: >-
      People who define themselves by who they protect. Not
      a formal order — it's a personal oath, sometimes
      spoken, sometimes not. A Sworn Companion has chosen
      someone to stand beside, and that choice is their
      whole identity.
    cultural_status: admired

# World-specific constraints (narrows genre constraints further)
# Example: this theocratic-leaning world makes outlaw+control very rare
additional_constraints:
  forbidden: []
  # Combinations not listed in any funnel fall back to genre-level names
```

- [ ] **Step 3: Validate YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('sidequest-content/genre_packs/low_fantasy/worlds/shattered_reach/archetype_funnels.yaml')); print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/low_fantasy/worlds/shattered_reach/archetype_funnels.yaml
git commit -m "content(low_fantasy/shattered_reach): add archetype funnel definitions"
```

---

## Phase 2: Rust Genre Loader — New Structs & Inheritance Resolution

Update `sidequest-genre` to parse the new YAML schema and resolve the inheritance chain.

### Task 4: Add base archetype structs to sidequest-genre

**Files:**
- Create: `sidequest-api/crates/sidequest-genre/src/models/archetype_axes.rs`
- Modify: `sidequest-api/crates/sidequest-genre/src/models/mod.rs` (add module)

- [ ] **Step 1: Write failing test — base archetype deserialization**

Create test file: `sidequest-api/crates/sidequest-genre/tests/archetype_axes_test.rs`

```rust
use sidequest_genre::models::archetype_axes::*;

#[test]
fn test_deserialize_jungian_archetype() {
    let yaml = r#"
        id: sage
        drive: "Seeks truth and understanding"
        ocean_tendencies:
          openness: [7.0, 9.5]
          conscientiousness: [6.0, 8.0]
          extraversion: [2.0, 5.0]
          agreeableness: [4.0, 7.0]
          neuroticism: [3.0, 6.0]
        stat_affinity: [wisdom, intellect, insight]
    "#;
    let archetype: JungianArchetype = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(archetype.id, "sage");
    assert_eq!(archetype.stat_affinity.len(), 3);
    assert!((archetype.ocean_tendencies.openness[0] - 7.0).abs() < f64::EPSILON);
}

#[test]
fn test_deserialize_rpg_role() {
    let yaml = r#"
        id: healer
        combat_function: "Restores allies, removes conditions"
        stat_affinity: [wisdom, spirit, empathy]
    "#;
    let role: RpgRole = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(role.id, "healer");
    assert_eq!(role.combat_function, "Restores allies, removes conditions");
}

#[test]
fn test_deserialize_npc_role() {
    let yaml = r#"
        id: mook
        narrative_function: "Disposable opposition, exists to be overcome"
        skip_enrichment: true
    "#;
    let role: NpcRole = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(role.id, "mook");
    assert!(role.skip_enrichment);
}

#[test]
fn test_deserialize_npc_role_default_skip() {
    let yaml = r#"
        id: mentor
        narrative_function: "Guides protagonist"
    "#;
    let role: NpcRole = serde_yaml::from_str(yaml).unwrap();
    assert!(!role.skip_enrichment);
}

#[test]
fn test_deserialize_base_archetypes_file() {
    let yaml = r#"
        jungian:
          - id: sage
            drive: "Seeks truth"
            ocean_tendencies:
              openness: [7.0, 9.5]
              conscientiousness: [6.0, 8.0]
              extraversion: [2.0, 5.0]
              agreeableness: [4.0, 7.0]
              neuroticism: [3.0, 6.0]
            stat_affinity: [wisdom]
        rpg_roles:
          - id: healer
            combat_function: "Restores allies"
            stat_affinity: [wisdom]
        npc_roles:
          - id: mentor
            narrative_function: "Guides protagonist"
    "#;
    let base: BaseArchetypes = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(base.jungian.len(), 1);
    assert_eq!(base.rpg_roles.len(), 1);
    assert_eq!(base.npc_roles.len(), 1);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-api && cargo test --test archetype_axes_test 2>&1 | head -20`

Expected: Compilation error — module `archetype_axes` does not exist.

- [ ] **Step 3: Implement the structs**

Create `sidequest-api/crates/sidequest-genre/src/models/archetype_axes.rs`:

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// OCEAN score ranges — [min, max] for each Big Five dimension.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct OceanTendencies {
    pub openness: [f64; 2],
    pub conscientiousness: [f64; 2],
    pub extraversion: [f64; 2],
    pub agreeableness: [f64; 2],
    pub neuroticism: [f64; 2],
}

/// Base Jungian archetype — personality core, genre-agnostic.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct JungianArchetype {
    pub id: String,
    pub drive: String,
    pub ocean_tendencies: OceanTendencies,
    pub stat_affinity: Vec<String>,
}

/// Base RPG role — mechanical combat function, genre-agnostic.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RpgRole {
    pub id: String,
    pub combat_function: String,
    pub stat_affinity: Vec<String>,
}

/// NPC narrative role — assigned by the system, never player-facing.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct NpcRole {
    pub id: String,
    pub narrative_function: String,
    #[serde(default)]
    pub skip_enrichment: bool,
}

/// Top-level container for the base archetype definitions file.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct BaseArchetypes {
    pub jungian: Vec<JungianArchetype>,
    pub rpg_roles: Vec<RpgRole>,
    pub npc_roles: Vec<NpcRole>,
}
```

Add to `sidequest-api/crates/sidequest-genre/src/models/mod.rs`:

```rust
pub mod archetype_axes;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-api && cargo test --test archetype_axes_test`

Expected: All 5 tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-genre/src/models/archetype_axes.rs
git add crates/sidequest-genre/src/models/mod.rs
git add crates/sidequest-genre/tests/archetype_axes_test.rs
git commit -m "feat(genre): add base archetype axis structs (jungian, rpg_role, npc_role)"
```

### Task 5: Add genre-level constraint structs

**Files:**
- Create: `sidequest-api/crates/sidequest-genre/src/models/archetype_constraints.rs`
- Modify: `sidequest-api/crates/sidequest-genre/src/models/mod.rs`

- [ ] **Step 1: Write failing test — constraint deserialization**

Add to test file `sidequest-api/crates/sidequest-genre/tests/archetype_axes_test.rs`:

```rust
use sidequest_genre::models::archetype_constraints::*;

#[test]
fn test_deserialize_constraints() {
    let yaml = r#"
        valid_pairings:
          common:
            - [hero, tank]
            - [sage, healer]
          uncommon:
            - [jester, stealth]
          rare:
            - [innocent, tank]
          forbidden:
            - [innocent, stealth]
        genre_flavor:
          jungian:
            hero:
              speech_pattern: "direct"
              equipment_tendency: "weapons"
              visual_cues: "scarred hands"
          rpg_roles:
            tank:
              fallback_name: "Shield-Bearer"
        npc_roles_available:
          - mentor
          - mook
    "#;
    let constraints: ArchetypeConstraints = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(constraints.valid_pairings.common.len(), 2);
    assert_eq!(constraints.valid_pairings.forbidden.len(), 1);
    assert_eq!(
        constraints.genre_flavor.rpg_roles["tank"].fallback_name,
        "Shield-Bearer"
    );
}

#[test]
fn test_pairing_weight_lookup() {
    let yaml = r#"
        valid_pairings:
          common:
            - [hero, tank]
          uncommon:
            - [jester, stealth]
          rare:
            - [innocent, tank]
          forbidden:
            - [innocent, stealth]
        genre_flavor:
          jungian: {}
          rpg_roles: {}
        npc_roles_available: []
    "#;
    let constraints: ArchetypeConstraints = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(
        constraints.pairing_weight("hero", "tank"),
        Some(PairingWeight::Common)
    );
    assert_eq!(
        constraints.pairing_weight("jester", "stealth"),
        Some(PairingWeight::Uncommon)
    );
    assert_eq!(
        constraints.pairing_weight("innocent", "stealth"),
        Some(PairingWeight::Forbidden)
    );
    assert_eq!(
        constraints.pairing_weight("hero", "healer"),
        None  // Not defined
    );
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-api && cargo test --test archetype_axes_test 2>&1 | head -20`

Expected: Compilation error.

- [ ] **Step 3: Implement constraint structs**

Create `sidequest-api/crates/sidequest-genre/src/models/archetype_constraints.rs`:

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Weight classification for a Jungian x RPG Role pairing.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PairingWeight {
    Common,
    Uncommon,
    Rare,
    Forbidden,
}

/// Valid pairings grouped by weight. Each entry is [jungian_id, rpg_role_id].
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ValidPairings {
    #[serde(default)]
    pub common: Vec<[String; 2]>,
    #[serde(default)]
    pub uncommon: Vec<[String; 2]>,
    #[serde(default)]
    pub rare: Vec<[String; 2]>,
    #[serde(default)]
    pub forbidden: Vec<[String; 2]>,
}

/// Genre-specific flavor for a Jungian archetype.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct JungianFlavor {
    #[serde(default)]
    pub speech_pattern: String,
    #[serde(default)]
    pub equipment_tendency: String,
    #[serde(default)]
    pub visual_cues: String,
}

/// Genre-specific flavor for an RPG role.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct RpgRoleFlavor {
    pub fallback_name: String,
}

/// Genre-level flavor collections.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct GenreFlavor {
    #[serde(default)]
    pub jungian: HashMap<String, JungianFlavor>,
    #[serde(default)]
    pub rpg_roles: HashMap<String, RpgRoleFlavor>,
}

/// Genre-level archetype constraints — valid pairings and flavor.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ArchetypeConstraints {
    pub valid_pairings: ValidPairings,
    pub genre_flavor: GenreFlavor,
    #[serde(default)]
    pub npc_roles_available: Vec<String>,
}

impl ArchetypeConstraints {
    /// Look up the weight of a [jungian, rpg_role] pairing.
    /// Returns None if the pairing is not listed in any weight category.
    pub fn pairing_weight(&self, jungian: &str, rpg_role: &str) -> Option<PairingWeight> {
        let matches = |pair: &[String; 2]| pair[0] == jungian && pair[1] == rpg_role;

        if self.valid_pairings.common.iter().any(matches) {
            Some(PairingWeight::Common)
        } else if self.valid_pairings.uncommon.iter().any(matches) {
            Some(PairingWeight::Uncommon)
        } else if self.valid_pairings.rare.iter().any(matches) {
            Some(PairingWeight::Rare)
        } else if self.valid_pairings.forbidden.iter().any(matches) {
            Some(PairingWeight::Forbidden)
        } else {
            None
        }
    }

    /// Get the fallback name for an RPG role in this genre.
    pub fn fallback_name(&self, rpg_role: &str) -> Option<&str> {
        self.genre_flavor
            .rpg_roles
            .get(rpg_role)
            .map(|f| f.fallback_name.as_str())
    }
}
```

Add to `sidequest-api/crates/sidequest-genre/src/models/mod.rs`:

```rust
pub mod archetype_constraints;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-api && cargo test --test archetype_axes_test`

Expected: All tests pass (previous + 2 new).

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-genre/src/models/archetype_constraints.rs
git add crates/sidequest-genre/src/models/mod.rs
git add crates/sidequest-genre/tests/archetype_axes_test.rs
git commit -m "feat(genre): add archetype constraint structs with pairing weight lookup"
```

### Task 6: Add world-level funnel structs

**Files:**
- Create: `sidequest-api/crates/sidequest-genre/src/models/archetype_funnels.rs`
- Modify: `sidequest-api/crates/sidequest-genre/src/models/mod.rs`

- [ ] **Step 1: Write failing test — funnel deserialization and resolution**

Add to test file `sidequest-api/crates/sidequest-genre/tests/archetype_axes_test.rs`:

```rust
use sidequest_genre::models::archetype_funnels::*;

#[test]
fn test_deserialize_funnel() {
    let yaml = r#"
        funnels:
          - name: Thornwall Mender
            absorbs:
              - [sage, healer]
              - [caregiver, healer]
            faction: Thornwall Convocation
            lore: "Itinerant healers"
            cultural_status: respected but watched
            disposition_toward:
              Iron Guard: cautious
          - name: Iron Warden
            absorbs:
              - [hero, tank]
            faction: Iron Guard
            lore: "Standing shield-wall"
            cultural_status: feared
        additional_constraints:
          forbidden: []
    "#;
    let funnels: ArchetypeFunnels = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(funnels.funnels.len(), 2);
    assert_eq!(funnels.funnels[0].absorbs.len(), 2);
    assert_eq!(
        funnels.funnels[0].disposition_toward.get("Iron Guard").unwrap(),
        "cautious"
    );
}

#[test]
fn test_funnel_resolution() {
    let yaml = r#"
        funnels:
          - name: Thornwall Mender
            absorbs:
              - [sage, healer]
              - [caregiver, healer]
            faction: Thornwall Convocation
            lore: "Itinerant healers"
            cultural_status: respected
          - name: Iron Warden
            absorbs:
              - [hero, tank]
            faction: Iron Guard
            lore: "Shield-wall"
            cultural_status: feared
        additional_constraints:
          forbidden: []
    "#;
    let funnels: ArchetypeFunnels = serde_yaml::from_str(yaml).unwrap();

    let result = funnels.resolve("sage", "healer");
    assert!(result.is_some());
    let funnel = result.unwrap();
    assert_eq!(funnel.name, "Thornwall Mender");

    let result = funnels.resolve("hero", "tank");
    assert!(result.is_some());
    assert_eq!(result.unwrap().name, "Iron Warden");

    // Unmatched combination returns None (falls back to genre)
    let result = funnels.resolve("jester", "dps");
    assert!(result.is_none());
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-api && cargo test --test archetype_axes_test 2>&1 | head -20`

Expected: Compilation error.

- [ ] **Step 3: Implement funnel structs**

Create `sidequest-api/crates/sidequest-genre/src/models/archetype_funnels.rs`:

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A single funnel entry — maps multiple axis combinations to one named archetype.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Funnel {
    pub name: String,
    pub absorbs: Vec<[String; 2]>,
    #[serde(default)]
    pub faction: Option<String>,
    pub lore: String,
    #[serde(default)]
    pub cultural_status: Option<String>,
    #[serde(default)]
    pub disposition_toward: HashMap<String, String>,
}

/// World-level additional constraints.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct WorldConstraints {
    #[serde(default)]
    pub forbidden: Vec<[String; 2]>,
}

/// World-level archetype funnels — resolves axis pairs to named archetypes.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ArchetypeFunnels {
    pub funnels: Vec<Funnel>,
    #[serde(default)]
    pub additional_constraints: WorldConstraints,
}

impl ArchetypeFunnels {
    /// Resolve a [jungian, rpg_role] pair to a funnel entry.
    /// Returns None if no funnel claims this combination.
    pub fn resolve(&self, jungian: &str, rpg_role: &str) -> Option<&Funnel> {
        self.funnels.iter().find(|f| {
            f.absorbs
                .iter()
                .any(|pair| pair[0] == jungian && pair[1] == rpg_role)
        })
    }

    /// Check if a pairing is forbidden at the world level.
    pub fn is_forbidden(&self, jungian: &str, rpg_role: &str) -> bool {
        self.additional_constraints
            .forbidden
            .iter()
            .any(|pair| pair[0] == jungian && pair[1] == rpg_role)
    }
}
```

Add to `sidequest-api/crates/sidequest-genre/src/models/mod.rs`:

```rust
pub mod archetype_funnels;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-api && cargo test --test archetype_axes_test`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-genre/src/models/archetype_funnels.rs
git add crates/sidequest-genre/src/models/mod.rs
git add crates/sidequest-genre/tests/archetype_axes_test.rs
git commit -m "feat(genre): add archetype funnel structs with resolution lookup"
```

### Task 7: Add archetype resolution engine

**Files:**
- Create: `sidequest-api/crates/sidequest-genre/src/archetype_resolve.rs`
- Modify: `sidequest-api/crates/sidequest-genre/src/lib.rs`

- [ ] **Step 1: Write failing test — full resolution chain**

Create test file `sidequest-api/crates/sidequest-genre/tests/archetype_resolve_test.rs`:

```rust
use sidequest_genre::archetype_resolve::*;
use sidequest_genre::models::archetype_axes::*;
use sidequest_genre::models::archetype_constraints::*;
use sidequest_genre::models::archetype_funnels::*;

fn test_base() -> BaseArchetypes {
    serde_yaml::from_str(r#"
        jungian:
          - id: sage
            drive: "Seeks truth"
            ocean_tendencies:
              openness: [7.0, 9.5]
              conscientiousness: [6.0, 8.0]
              extraversion: [2.0, 5.0]
              agreeableness: [4.0, 7.0]
              neuroticism: [3.0, 6.0]
            stat_affinity: [wisdom, intellect]
          - id: hero
            drive: "Proves worth"
            ocean_tendencies:
              openness: [5.0, 7.0]
              conscientiousness: [6.0, 8.5]
              extraversion: [6.0, 8.5]
              agreeableness: [5.0, 7.5]
              neuroticism: [2.0, 4.5]
            stat_affinity: [strength, endurance]
        rpg_roles:
          - id: healer
            combat_function: "Restores allies"
            stat_affinity: [wisdom]
          - id: tank
            combat_function: "Absorbs damage"
            stat_affinity: [strength]
        npc_roles:
          - id: mentor
            narrative_function: "Guides protagonist"
    "#).unwrap()
}

fn test_constraints() -> ArchetypeConstraints {
    serde_yaml::from_str(r#"
        valid_pairings:
          common:
            - [sage, healer]
            - [hero, tank]
          uncommon: []
          rare: []
          forbidden: []
        genre_flavor:
          jungian: {}
          rpg_roles:
            healer:
              fallback_name: "Hedge Healer"
            tank:
              fallback_name: "Shield-Bearer"
        npc_roles_available: [mentor]
    "#).unwrap()
}

fn test_funnels() -> ArchetypeFunnels {
    serde_yaml::from_str(r#"
        funnels:
          - name: Thornwall Mender
            absorbs:
              - [sage, healer]
            faction: Thornwall Convocation
            lore: "Itinerant healers"
            cultural_status: respected
        additional_constraints:
          forbidden: []
    "#).unwrap()
}

#[test]
fn test_resolve_with_world_funnel() {
    let base = test_base();
    let constraints = test_constraints();
    let funnels = Some(test_funnels());

    let result = resolve_archetype("sage", "healer", &base, &constraints, funnels.as_ref());
    assert!(result.is_ok());
    let resolved = result.unwrap();
    assert_eq!(resolved.name, "Thornwall Mender");
    assert_eq!(resolved.faction.as_deref(), Some("Thornwall Convocation"));
    assert!(resolved.lore.contains("Itinerant"));
}

#[test]
fn test_resolve_falls_back_to_genre() {
    let base = test_base();
    let constraints = test_constraints();

    // No funnels — should fall back to genre fallback_name
    let result = resolve_archetype("hero", "tank", &base, &constraints, None);
    assert!(result.is_ok());
    let resolved = result.unwrap();
    assert_eq!(resolved.name, "Shield-Bearer");
    assert!(resolved.faction.is_none());
}

#[test]
fn test_resolve_forbidden_pairing() {
    let base = test_base();
    let constraints: ArchetypeConstraints = serde_yaml::from_str(r#"
        valid_pairings:
          common: []
          uncommon: []
          rare: []
          forbidden:
            - [sage, tank]
        genre_flavor:
          jungian: {}
          rpg_roles: {}
        npc_roles_available: []
    "#).unwrap();

    let result = resolve_archetype("sage", "tank", &base, &constraints, None);
    assert!(result.is_err());
}

#[test]
fn test_resolve_unknown_axis_value() {
    let base = test_base();
    let constraints = test_constraints();

    let result = resolve_archetype("nonexistent", "healer", &base, &constraints, None);
    assert!(result.is_err());
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-api && cargo test --test archetype_resolve_test 2>&1 | head -20`

Expected: Compilation error.

- [ ] **Step 3: Implement the resolution engine**

Create `sidequest-api/crates/sidequest-genre/src/archetype_resolve.rs`:

```rust
use crate::error::GenreError;
use crate::models::archetype_axes::BaseArchetypes;
use crate::models::archetype_constraints::{ArchetypeConstraints, PairingWeight};
use crate::models::archetype_funnels::ArchetypeFunnels;

/// The resolved output of the archetype pipeline.
#[derive(Debug, Clone)]
pub struct ResolvedArchetype {
    /// The display name (from funnel, genre fallback, or axis IDs).
    pub name: String,
    /// Jungian axis value.
    pub jungian: String,
    /// RPG role axis value.
    pub rpg_role: String,
    /// NPC role axis value (None for PCs).
    pub npc_role: Option<String>,
    /// Faction from funnel, if any.
    pub faction: Option<String>,
    /// Lore description from funnel or genre flavor.
    pub lore: String,
    /// Cultural status from funnel.
    pub cultural_status: Option<String>,
    /// Pairing weight classification.
    pub weight: PairingWeight,
    /// Source of the name resolution.
    pub resolution_source: ResolutionSource,
}

/// Where the resolved name came from.
#[derive(Debug, Clone, PartialEq)]
pub enum ResolutionSource {
    /// Name came from a world-level funnel.
    WorldFunnel,
    /// Name came from genre-level fallback.
    GenreFallback,
}

/// Resolve a [jungian, rpg_role] pair through the full inheritance chain.
///
/// Resolution order:
/// 1. Check base layer — both axis values must exist
/// 2. Check constraints — pairing must not be forbidden
/// 3. Check world funnels — if a funnel claims it, use that name
/// 4. Fall back to genre fallback name
pub fn resolve_archetype(
    jungian: &str,
    rpg_role: &str,
    base: &BaseArchetypes,
    constraints: &ArchetypeConstraints,
    funnels: Option<&ArchetypeFunnels>,
) -> Result<ResolvedArchetype, GenreError> {
    // Step 1: Validate axis values exist in base
    if !base.jungian.iter().any(|j| j.id == jungian) {
        return Err(GenreError::Validation(format!(
            "Unknown Jungian archetype: '{jungian}'"
        )));
    }
    if !base.rpg_roles.iter().any(|r| r.id == rpg_role) {
        return Err(GenreError::Validation(format!(
            "Unknown RPG role: '{rpg_role}'"
        )));
    }

    // Step 2: Check constraints
    let weight = constraints
        .pairing_weight(jungian, rpg_role)
        .unwrap_or(PairingWeight::Uncommon); // Unlisted = uncommon by default

    if weight == PairingWeight::Forbidden {
        return Err(GenreError::Validation(format!(
            "Forbidden pairing: [{jungian}, {rpg_role}]"
        )));
    }

    // Step 2b: Check world-level forbidden
    if let Some(funnels) = funnels {
        if funnels.is_forbidden(jungian, rpg_role) {
            return Err(GenreError::Validation(format!(
                "World-forbidden pairing: [{jungian}, {rpg_role}]"
            )));
        }
    }

    // Step 3: Try world funnel
    if let Some(funnels) = funnels {
        if let Some(funnel) = funnels.resolve(jungian, rpg_role) {
            return Ok(ResolvedArchetype {
                name: funnel.name.clone(),
                jungian: jungian.to_string(),
                rpg_role: rpg_role.to_string(),
                npc_role: None,
                faction: funnel.faction.clone(),
                lore: funnel.lore.clone(),
                cultural_status: funnel.cultural_status.clone(),
                weight,
                resolution_source: ResolutionSource::WorldFunnel,
            });
        }
    }

    // Step 4: Genre fallback
    let fallback_name = constraints
        .fallback_name(rpg_role)
        .unwrap_or(rpg_role)
        .to_string();

    Ok(ResolvedArchetype {
        name: fallback_name,
        jungian: jungian.to_string(),
        rpg_role: rpg_role.to_string(),
        npc_role: None,
        faction: None,
        lore: String::new(),
        cultural_status: None,
        weight,
        resolution_source: ResolutionSource::GenreFallback,
    })
}
```

Add to `sidequest-api/crates/sidequest-genre/src/lib.rs`:

```rust
pub mod archetype_resolve;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-api && cargo test --test archetype_resolve_test`

Expected: All 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-genre/src/archetype_resolve.rs
git add crates/sidequest-genre/src/lib.rs
git add crates/sidequest-genre/tests/archetype_resolve_test.rs
git commit -m "feat(genre): add archetype resolution engine (base->genre->world chain)"
```

### Task 8: Wire base archetype and constraint/funnel loading into genre loader

**Files:**
- Modify: `sidequest-api/crates/sidequest-genre/src/loader.rs`
- Modify: `sidequest-api/crates/sidequest-genre/src/models/pack.rs`

- [ ] **Step 1: Write failing test — GenrePack includes new fields**

Add to `sidequest-api/crates/sidequest-genre/tests/archetype_resolve_test.rs`:

```rust
#[test]
fn test_genre_pack_has_new_archetype_fields() {
    use sidequest_genre::models::pack::GenrePack;
    use sidequest_genre::models::archetype_axes::BaseArchetypes;
    use sidequest_genre::models::archetype_constraints::ArchetypeConstraints;
    // If this compiles, the fields exist.
    fn _assert_fields(pack: &GenrePack) -> (&Option<BaseArchetypes>, &Option<ArchetypeConstraints>) {
        (&pack.base_archetypes, &pack.archetype_constraints)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-api && cargo test --test archetype_resolve_test 2>&1 | head -20`

Expected: Compilation error — fields do not exist.

- [ ] **Step 3: Add fields to GenrePack and World, update loader**

In `sidequest-api/crates/sidequest-genre/src/models/pack.rs`, add to `GenrePack`:

```rust
pub base_archetypes: Option<BaseArchetypes>,
pub archetype_constraints: Option<ArchetypeConstraints>,
```

Add to `World`:

```rust
pub archetype_funnels: Option<ArchetypeFunnels>,
```

Add imports at top of `pack.rs`:

```rust
use super::archetype_axes::BaseArchetypes;
use super::archetype_constraints::ArchetypeConstraints;
use super::archetype_funnels::ArchetypeFunnels;
```

In `sidequest-api/crates/sidequest-genre/src/loader.rs`:

The `GenreLoader` has `search_paths` — the base `archetypes_base.yaml` lives at the
content root (parent of genre pack dirs). In `load_genre_pack()`, attempt to load it
from the parent directory of the genre pack path:

```rust
// Load base archetypes from content root (parent of genre pack dir)
let base_archetypes: Option<BaseArchetypes> = path
    .parent()
    .and_then(|parent| parent.parent()) // genre_packs/ -> content root
    .map(|root| load_yaml_optional(&root.join("archetypes_base.yaml")))
    .transpose()?
    .flatten();
```

Load genre-level constraints:

```rust
let archetype_constraints: Option<ArchetypeConstraints> =
    load_yaml_optional(&path.join("archetype_constraints.yaml"))?;
```

Include both in GenrePack construction:

```rust
base_archetypes,
archetype_constraints,
```

In `load_single_world()`, add:

```rust
let archetype_funnels: Option<ArchetypeFunnels> =
    load_yaml_optional(&world_path.join("archetype_funnels.yaml"))?;
```

And include in World construction:

```rust
archetype_funnels,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-api && cargo test --test archetype_resolve_test`

Expected: All tests pass.

- [ ] **Step 5: Run full genre crate tests to verify nothing broke**

Run: `cd sidequest-api && cargo test -p sidequest-genre`

Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
cd sidequest-api
git add crates/sidequest-genre/src/loader.rs
git add crates/sidequest-genre/src/models/pack.rs
git add crates/sidequest-genre/tests/archetype_resolve_test.rs
git commit -m "feat(genre): wire archetype constraints and funnels into genre loader"
```

### Task 9: Integration test — load real genre pack with new files

**Files:**
- Create: `sidequest-api/crates/sidequest-genre/tests/archetype_integration_test.rs`

- [ ] **Step 1: Write integration test that loads low_fantasy with constraints**

```rust
use sidequest_genre::loader::load_genre_pack;
use std::path::Path;

#[test]
fn test_load_low_fantasy_with_constraints() {
    let content_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .join("sidequest-content/genre_packs/low_fantasy");

    // Skip if content repo not available
    if !content_path.exists() {
        eprintln!("Skipping: sidequest-content not found at {:?}", content_path);
        return;
    }

    let pack = load_genre_pack(&content_path).expect("Failed to load low_fantasy");

    // Verify constraints loaded
    assert!(
        pack.archetype_constraints.is_some(),
        "archetype_constraints.yaml should be loaded"
    );

    let constraints = pack.archetype_constraints.as_ref().unwrap();
    assert!(
        !constraints.valid_pairings.common.is_empty(),
        "Should have common pairings"
    );

    // Verify funnels loaded for shattered_reach
    if let Some(world) = pack.worlds.get("shattered_reach") {
        assert!(
            world.archetype_funnels.is_some(),
            "shattered_reach should have archetype_funnels.yaml"
        );
        let funnels = world.archetype_funnels.as_ref().unwrap();
        assert!(
            !funnels.funnels.is_empty(),
            "Should have at least one funnel"
        );

        // Verify resolution works end-to-end
        let mender = funnels.resolve("sage", "healer");
        assert!(mender.is_some(), "sage+healer should resolve to a funnel");
        assert_eq!(mender.unwrap().name, "Thornwall Mender");
    }
}
```

- [ ] **Step 2: Run integration test**

Run: `cd sidequest-api && cargo test --test archetype_integration_test`

Expected: PASS (assuming content repo is available with Task 2 and Task 3 committed).

- [ ] **Step 3: Commit**

```bash
cd sidequest-api
git add crates/sidequest-genre/tests/archetype_integration_test.rs
git commit -m "test(genre): add integration test for archetype constraint/funnel loading"
```

---

## Phase 3: Chargen Refactor

Update `MechanicalEffects` and the `CharacterBuilder` FSM to produce axis values that resolve through the archetype pipeline.

### Task 10: Add axis fields to MechanicalEffects

**Files:**
- Modify: `sidequest-api/crates/sidequest-genre/src/models/character.rs`

- [ ] **Step 1: Write failing test — axis fields on MechanicalEffects**

Add to `sidequest-api/crates/sidequest-genre/tests/archetype_axes_test.rs`:

```rust
use sidequest_genre::models::character::MechanicalEffects;

#[test]
fn test_mechanical_effects_has_axis_fields() {
    let yaml = r#"
        jungian_hint: sage
        rpg_role_hint: healer
    "#;
    let effects: MechanicalEffects = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(effects.jungian_hint.as_deref(), Some("sage"));
    assert_eq!(effects.rpg_role_hint.as_deref(), Some("healer"));
}

#[test]
fn test_mechanical_effects_backward_compatible() {
    let yaml = r#"
        class_hint: Cleric
        race_hint: Human
        background: Farmer
    "#;
    let effects: MechanicalEffects = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(effects.class_hint.as_deref(), Some("Cleric"));
    assert!(effects.jungian_hint.is_none());
    assert!(effects.rpg_role_hint.is_none());
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-api && cargo test --test archetype_axes_test test_mechanical_effects 2>&1 | head -20`

Expected: Compilation error — field `jungian_hint` does not exist.

- [ ] **Step 3: Add axis fields to MechanicalEffects**

In `sidequest-api/crates/sidequest-genre/src/models/character.rs`, add to `MechanicalEffects`:

```rust
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub jungian_hint: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rpg_role_hint: Option<String>,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-api && cargo test --test archetype_axes_test test_mechanical_effects`

Expected: Both tests pass.

- [ ] **Step 5: Run full test suite to verify backward compatibility**

Run: `cd sidequest-api && cargo test -p sidequest-genre`

Expected: All tests pass — existing char_creation.yaml files still load because the new fields are optional.

- [ ] **Step 6: Commit**

```bash
cd sidequest-api
git add crates/sidequest-genre/src/models/character.rs
git add crates/sidequest-genre/tests/archetype_axes_test.rs
git commit -m "feat(genre): add jungian_hint and rpg_role_hint to MechanicalEffects"
```

### Task 11: Add axis accumulation to CharacterBuilder

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/builder.rs`

- [ ] **Step 1: Write failing test — AccumulatedChoices includes axis values**

Add to `sidequest-api/crates/sidequest-game/tests/builder_test.rs` (or create if needed):

```rust
use sidequest_game::builder::AccumulatedChoices;

#[test]
fn test_accumulated_choices_has_axis_fields() {
    let acc = AccumulatedChoices::default();
    assert!(acc.jungian_hint.is_none());
    assert!(acc.rpg_role_hint.is_none());
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-api && cargo test -p sidequest-game test_accumulated_choices_has_axis 2>&1 | head -20`

Expected: Compilation error — field does not exist.

- [ ] **Step 3: Add axis fields to AccumulatedChoices and accumulation logic**

In `sidequest-api/crates/sidequest-game/src/builder.rs`:

Add to `AccumulatedChoices` struct (around line 123-159):

```rust
    pub jungian_hint: Option<String>,
    pub rpg_role_hint: Option<String>,
```

In the `accumulated()` method (around line 572-656), add accumulation logic alongside existing hint accumulation:

```rust
    if let Some(ref jungian) = effects.jungian_hint {
        acc.jungian_hint = Some(jungian.clone());
    }
    if let Some(ref rpg_role) = effects.rpg_role_hint {
        acc.rpg_role_hint = Some(rpg_role.clone());
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-api && cargo test -p sidequest-game`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-game/src/builder.rs
git commit -m "feat(game): accumulate jungian_hint and rpg_role_hint in CharacterBuilder"
```

### Task 12: Resolve archetype in builder.build()

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/builder.rs`
- Modify: `sidequest-api/crates/sidequest-game/src/character.rs`

- [ ] **Step 1: Write failing test — Character has resolved_archetype field**

```rust
use sidequest_game::character::Character;

#[test]
fn test_character_has_resolved_archetype() {
    // Just checking the field exists on the struct
    fn _assert_field(c: &Character) -> &Option<String> {
        &c.resolved_archetype
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Expected: Compilation error.

- [ ] **Step 3: Add resolved_archetype to Character**

In `sidequest-api/crates/sidequest-game/src/character.rs`, add:

```rust
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resolved_archetype: Option<String>,
```

In `builder.rs` `build()` method (around line 1185-1217), after constructing the Character, set:

```rust
    resolved_archetype: acc.jungian_hint.as_ref().and_then(|j| {
        acc.rpg_role_hint.as_ref().map(|r| format!("{j}/{r}"))
    }),
```

This stores the raw axis values for now. Full resolution (through constraints + funnels) requires the genre pack to be available at build time, which will be wired in the dispatch layer (Task 13).

- [ ] **Step 4: Run tests**

Run: `cd sidequest-api && cargo test -p sidequest-game`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-game/src/character.rs
git add crates/sidequest-game/src/builder.rs
git commit -m "feat(game): add resolved_archetype to Character, set from axis hints in builder"
```

### Task 13: Wire full archetype resolution into chargen dispatch

**Files:**
- Modify: `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs`

- [ ] **Step 1: Write failing test — chargen dispatch resolves archetype**

This test verifies that the confirmation phase in `dispatch_character_creation()` calls `resolve_archetype()` when axis hints are present and stores the resolved name on the Character.

```rust
// In the dispatch test module or a new test file
#[test]
fn test_chargen_resolves_archetype_when_axis_hints_present() {
    // Build a DispatchContext with a genre pack that has constraints + funnels
    // Submit chargen scenes that produce jungian_hint + rpg_role_hint
    // Verify the resulting Character has resolved_archetype set to the funnel name
    // (Exact setup depends on test infrastructure — may need mock context)
}
```

Note: This test requires the dispatch test harness. The implementer should follow existing test patterns in the connect.rs test module.

- [ ] **Step 2: Implement resolution in confirmation phase**

In `dispatch_character_creation()` confirmation phase (around line 1404), after `builder.build(char_name)`:

```rust
    // Resolve archetype through the pipeline if axis hints are present
    if let (Some(ref jungian), Some(ref rpg_role)) = (
        character.resolved_archetype_jungian(),
        character.resolved_archetype_rpg_role(),
    ) {
        if let Some(ref constraints) = ctx.genre_pack.archetype_constraints {
            let world_funnels = ctx.world().and_then(|w| w.archetype_funnels.as_ref());
            match resolve_archetype(jungian, rpg_role, &base_archetypes, constraints, world_funnels) {
                Ok(resolved) => {
                    character.resolved_archetype = Some(resolved.name.clone());
                    // OTEL: log resolution
                    WatcherEventBuilder::new("archetype", WatcherEventType::StateTransition)
                        .field("event", "archetype.resolved")
                        .field("jungian", jungian)
                        .field("rpg_role", rpg_role)
                        .field("resolved_name", &resolved.name)
                        .field("source", format!("{:?}", resolved.resolution_source))
                        .field("faction", resolved.faction.as_deref().unwrap_or("none"))
                        .send();
                }
                Err(e) => {
                    tracing::warn!("Archetype resolution failed: {e}");
                }
            }
        }
    }
```

- [ ] **Step 3: Run full test suite**

Run: `cd sidequest-api && cargo test -p sidequest-server`

Expected: All tests pass. Existing chargen without axis hints is unaffected (resolution is skipped when hints are None).

- [ ] **Step 4: Commit**

```bash
cd sidequest-api
git add crates/sidequest-server/src/dispatch/connect.rs
git commit -m "feat(server): wire archetype resolution into chargen confirmation with OTEL"
```

---

## Phase 4: NPC Generation Pipeline

Update namegen and the Monster Manual to use the three-axis system.

### Task 14: Add axis fields to namegen NpcBlock output

**Files:**
- Modify: `sidequest-api/crates/sidequest-namegen/src/main.rs`

- [ ] **Step 1: Add jungian_id, rpg_role_id, npc_role_id to NpcBlock**

In the `NpcBlock` struct (around line 58-77), add:

```rust
    pub jungian_id: String,
    pub rpg_role_id: String,
    pub npc_role_id: Option<String>,
    pub resolved_archetype: String,
    pub resolution_source: String,  // "world_funnel" or "genre_fallback"
```

- [ ] **Step 2: Update generation flow to accept axis inputs**

Add CLI args:

```rust
    #[arg(long)]
    jungian: Option<String>,

    #[arg(long)]
    rpg_role: Option<String>,

    #[arg(long)]
    npc_role: Option<String>,
```

Update the generation flow (around lines 156-282):

1. If `--jungian` and `--rpg-role` are provided, use them directly
2. If not, select randomly from valid pairings (weighted by common > uncommon > rare)
3. If `--npc-role` is provided, use it; otherwise assign based on context
4. Resolve through constraints + funnels to get the named archetype
5. Use the resolved name as the `archetype` field (replacing the old archetype selection)

- [ ] **Step 3: Update OCEAN jitter to use Jungian base tendencies**

Replace the current archetype-based OCEAN lookup with:

```rust
    // Look up Jungian base tendencies from archetypes_base.yaml
    let jungian_def = base_archetypes.jungian.iter()
        .find(|j| j.id == jungian_id)
        .expect("Jungian archetype validated earlier");

    let ocean = OceanValues {
        openness: jitter_range(jungian_def.ocean_tendencies.openness, &mut rng),
        conscientiousness: jitter_range(jungian_def.ocean_tendencies.conscientiousness, &mut rng),
        extraversion: jitter_range(jungian_def.ocean_tendencies.extraversion, &mut rng),
        agreeableness: jitter_range(jungian_def.ocean_tendencies.agreeableness, &mut rng),
        neuroticism: jitter_range(jungian_def.ocean_tendencies.neuroticism, &mut rng),
    };
```

Where `jitter_range` picks a random value in the [min, max] range with some noise.

- [ ] **Step 4: Update history template to use funnel lore**

When the resolved archetype has lore (from a world funnel), incorporate it into the generated history instead of using the generic template.

- [ ] **Step 5: Test namegen with new flags**

Run: `cd sidequest-api && cargo run -p sidequest-namegen -- --genre low_fantasy --jungian sage --rpg-role healer --genre-packs-path ../sidequest-content/genre_packs`

Expected: Output includes `"jungian_id": "sage"`, `"rpg_role_id": "healer"`, `"resolved_archetype": "Thornwall Mender"` (if shattered_reach world is targeted).

- [ ] **Step 6: Test backward compatibility — namegen without new flags**

Run: `cd sidequest-api && cargo run -p sidequest-namegen -- --genre low_fantasy --genre-packs-path ../sidequest-content/genre_packs`

Expected: Random axis selection, output includes all new fields with randomly selected values.

- [ ] **Step 7: Commit**

```bash
cd sidequest-api
git add crates/sidequest-namegen/src/main.rs
git commit -m "feat(namegen): add three-axis selection with funnel resolution"
```

### Task 15: Add resolution tier tracking to NPC registry

**Files:**
- Modify: `sidequest-api/crates/sidequest-game/src/npc.rs`
- Modify: `sidequest-api/crates/sidequest-server/src/dispatch/npc_registry.rs`

- [ ] **Step 1: Add resolution tier enum and interaction counter to Npc**

In `sidequest-api/crates/sidequest-game/src/npc.rs`, add:

```rust
/// NPC enrichment tier — controls how much detail the system invests.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum ResolutionTier {
    /// Axes assigned, name, one quirk. No trope connections.
    #[default]
    Spawn,
    /// Player engaged beyond transactional. Backstory fills in.
    Engage,
    /// Player keeps engaging. Full backstory, portrait queued, relationship web.
    Promote,
}

// Add to Npc struct:
    #[serde(default)]
    pub resolution_tier: ResolutionTier,
    #[serde(default)]
    pub non_transactional_interactions: u32,
    #[serde(default)]
    pub jungian_id: Option<String>,
    #[serde(default)]
    pub rpg_role_id: Option<String>,
    #[serde(default)]
    pub npc_role_id: Option<String>,
    #[serde(default)]
    pub resolved_archetype: Option<String>,
```

- [ ] **Step 2: Add promotion logic to NPC registry**

In `sidequest-api/crates/sidequest-server/src/dispatch/npc_registry.rs`, add a function:

```rust
/// Evaluate whether an NPC should be promoted based on non-transactional interactions.
/// Three non-transactional interactions triggers promotion.
pub fn evaluate_promotion(npc: &mut Npc) -> Option<ResolutionTier> {
    let previous = npc.resolution_tier;
    let new_tier = match npc.non_transactional_interactions {
        0 => ResolutionTier::Spawn,
        1..=2 => ResolutionTier::Engage,
        _ => ResolutionTier::Promote,
    };

    if new_tier != previous {
        npc.resolution_tier = new_tier;
        Some(new_tier)
    } else {
        None
    }
}
```

- [ ] **Step 3: Add OTEL span for promotion events**

```rust
    if let Some(new_tier) = evaluate_promotion(npc) {
        WatcherEventBuilder::new("npc_promotion", WatcherEventType::StateTransition)
            .field("event", "npc.promoted")
            .field("npc_name", &npc.core.name)
            .field("from_tier", format!("{:?}", previous))
            .field("to_tier", format!("{:?}", new_tier))
            .field("non_transactional_interactions", npc.non_transactional_interactions)
            .field("turn", ctx.turn_manager.interaction())
            .send();
    }
```

- [ ] **Step 4: Run tests**

Run: `cd sidequest-api && cargo test -p sidequest-game && cargo test -p sidequest-server`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-game/src/npc.rs
git add crates/sidequest-server/src/dispatch/npc_registry.rs
git commit -m "feat(npc): add resolution tiers with promotion tracking and OTEL"
```

### Task 16: Update Monster Manual pre-gen to use axes

**Files:**
- Modify: `sidequest-api/crates/sidequest-server/src/dispatch/pregen.rs`

- [ ] **Step 1: Update seeding to pass axis values to namegen**

In `pregen.rs` (around lines 78-162), update the namegen invocation to include axis selection:

```rust
    // For each culture, generate NPCs with diverse axis combinations
    let pairings = select_diverse_pairings(&constraints, count_per_culture, &mut rng);

    for (jungian, rpg_role, npc_role) in pairings {
        let mut cmd = Command::new(namegen_path);
        cmd.arg("--genre").arg(&genre_slug)
            .arg("--culture").arg(&culture.id)
            .arg("--jungian").arg(&jungian)
            .arg("--rpg-role").arg(&rpg_role)
            .arg("--npc-role").arg(&npc_role)
            .arg("--genre-packs-path").arg(&genre_packs_path);
        // ... execute and collect result
    }
```

- [ ] **Step 2: Implement diverse pairing selection**

```rust
/// Select diverse [jungian, rpg_role, npc_role] combinations for pre-gen pool.
/// Weighted toward common pairings but includes uncommon/rare for diversity.
fn select_diverse_pairings(
    constraints: &ArchetypeConstraints,
    count: usize,
    rng: &mut impl Rng,
) -> Vec<(String, String, String)> {
    let mut pool = Vec::new();

    // 60% common, 30% uncommon, 10% rare
    let common_count = (count as f64 * 0.6).ceil() as usize;
    let uncommon_count = (count as f64 * 0.3).ceil() as usize;
    let rare_count = count.saturating_sub(common_count + uncommon_count);

    // Sample from each weight category
    pool.extend(sample_pairings(&constraints.valid_pairings.common, common_count, rng));
    pool.extend(sample_pairings(&constraints.valid_pairings.uncommon, uncommon_count, rng));
    pool.extend(sample_pairings(&constraints.valid_pairings.rare, rare_count, rng));

    // Assign NPC roles — distribute across available roles
    let npc_roles = &constraints.npc_roles_available;
    pool.into_iter()
        .enumerate()
        .map(|(i, (j, r))| {
            let role = &npc_roles[i % npc_roles.len()];
            (j, r, role.clone())
        })
        .collect()
}
```

- [ ] **Step 3: Run tests**

Run: `cd sidequest-api && cargo test -p sidequest-server`

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd sidequest-api
git add crates/sidequest-server/src/dispatch/pregen.rs
git commit -m "feat(pregen): use three-axis diverse pairing selection for Monster Manual seeding"
```

---

## Phase 5: Content Migration

Migrate remaining genre packs to the new system. Each genre needs an `archetype_constraints.yaml` and each world needs an `archetype_funnels.yaml`.

### Task 17: Create archetype_constraints.yaml for remaining genres

**Files:**
- Create: `sidequest-content/genre_packs/{genre}/archetype_constraints.yaml` for each of:
  - neon_dystopia
  - space_opera
  - road_warrior
  - pulp_noir
  - spaghetti_western
  - elemental_harmony
  - mutant_wasteland

- [ ] **Step 1: For each genre, read existing archetypes.yaml to understand current archetypes**

Read the existing archetypes for each genre to inform which Jungian x RPG Role pairings are valid. Map existing named archetypes to their axis values.

- [ ] **Step 2: Create constraint files with genre-appropriate pairings and flavor**

Each genre has different valid combinations. Examples:

- `neon_dystopia`: `innocent` is rare (this world eats innocence). `outlaw` is common.
- `spaghetti_western`: `healer` role barely exists. `dps` and `stealth` dominate.
- `road_warrior`: `artisan` NPC role is critical (mechanics, modders). `innocent` is forbidden.
- `space_opera`: Most combinations are valid — broad genre.

Write each constraint file following the schema from Task 2, with genre-appropriate fallback names.

- [ ] **Step 3: Validate all YAML files**

Run: `for f in sidequest-content/genre_packs/*/archetype_constraints.yaml; do python3 -c "import yaml; yaml.safe_load(open('$f')); print(f'OK: $f')"; done`

Expected: All files parse successfully.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/*/archetype_constraints.yaml
git commit -m "content: add archetype constraints for all genre packs"
```

### Task 18: Create archetype_funnels.yaml for active worlds

**Files:**
- Create funnel files for each active world across all genre packs

- [ ] **Step 1: Identify active worlds**

```bash
ls -d sidequest-content/genre_packs/*/worlds/*/
```

- [ ] **Step 2: For each world, read world.yaml, lore.yaml, cultures.yaml, factions.yaml**

Use the world's existing lore to inform funnel names, faction assignments, and cultural status.

- [ ] **Step 3: Create funnel files**

Each world defines 10-20 funnels that absorb the valid pairings from the genre constraints. Funnel names should be world-specific and lore-grounded — not generic.

- [ ] **Step 4: Validate all YAML files**

Run: `find sidequest-content -name archetype_funnels.yaml -exec python3 -c "import yaml; yaml.safe_load(open('{}')); print('OK: {}')" \;`

Expected: All files parse successfully.

- [ ] **Step 5: Commit**

```bash
cd sidequest-content
git add genre_packs/*/worlds/*/archetype_funnels.yaml
git commit -m "content: add archetype funnels for all active worlds"
```

### Task 19: Refactor char_creation.yaml files to use axis mappings

**Files:**
- Modify: `sidequest-content/genre_packs/*/char_creation.yaml`

- [ ] **Step 1: For each genre, map existing choices to axis values**

Example for low_fantasy crucible scene:

Before:
```yaml
    - label: The Blade
      mechanical_effects:
        class_hint: Fighter
        personality_trait: Disciplined
```

After:
```yaml
    - label: The Blade
      mechanical_effects:
        class_hint: Fighter
        personality_trait: Disciplined
        jungian_hint: hero
        rpg_role_hint: dps
```

The existing fields stay for backward compatibility. The new axis hints are added alongside them. Over time, the old fields can be deprecated as the resolution pipeline takes over.

- [ ] **Step 2: Update all genre pack char_creation.yaml files**

Add `jungian_hint` and `rpg_role_hint` to every choice in every chargen scene that produces mechanical effects. Some scenes (pronouns, name) don't need axis hints.

Mapping guide:
- "The Blade" / "I Handle It" / fighter-like → `hero` or `outlaw` + `dps` or `tank`
- "The Wild" / ranger-like → `explorer` + `stealth` or `jack_of_all_trades`
- "The Shadow" / rogue-like → `outlaw` + `stealth`
- "The Vigil" / cleric-like → `sage` or `caregiver` + `healer`
- "I Jack In" / netrunner → `magician` + `control`
- "I Know A Guy" / fixer → `ruler` or `everyman` + `support`
- etc.

- [ ] **Step 3: Validate all modified files**

Run: `for f in sidequest-content/genre_packs/*/char_creation.yaml; do python3 -c "import yaml; yaml.safe_load(open('$f')); print(f'OK: $f')"; done`

Expected: All files parse.

- [ ] **Step 4: Run Rust genre loader to verify backward compatibility**

Run: `cd sidequest-api && cargo test -p sidequest-genre`

Expected: All tests pass — new optional fields don't break existing deserialization.

- [ ] **Step 5: Commit**

```bash
cd sidequest-content
git add genre_packs/*/char_creation.yaml
git commit -m "content: add axis hints to chargen choices across all genre packs"
```

---

## Phase 6: OTEL Dashboard Integration

Ensure the GM panel can see archetype resolution, NPC generation axes, and promotion events.

### Task 20: Add archetype-specific OTEL spans

**Files:**
- Modify: `sidequest-api/crates/sidequest-server/src/dispatch/npc_registry.rs`
- Modify: `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs`

- [ ] **Step 1: Add archetype axis values to NPC registration span**

In `npc_registry.rs`, update the `npc.registration` span (around line 46-55):

```rust
let span = tracing::info_span!(
    "npc.registration",
    npc_name = %npc.name,
    npc_role = %npc.role,
    jungian_id = tracing::field::Empty,
    rpg_role_id = tracing::field::Empty,
    npc_role_id = tracing::field::Empty,
    resolved_archetype = tracing::field::Empty,
    resolution_tier = tracing::field::Empty,
    ocean_summary = tracing::field::Empty,
    archetype_source = tracing::field::Empty,
    namegen_validated = tracing::field::Empty,
    genre = %ctx.genre_slug,
);
```

Record the new fields when available from the namegen output.

- [ ] **Step 2: Add archetype resolution OTEL event to chargen**

Already added in Task 13. Verify it's present and includes all axis values plus resolution source.

- [ ] **Step 3: Add promotion OTEL event**

Already added in Task 15. Verify it fires correctly when `non_transactional_interactions` crosses thresholds.

- [ ] **Step 4: Run full test suite**

Run: `cd sidequest-api && cargo test`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-api
git add crates/sidequest-server/src/dispatch/npc_registry.rs
git add crates/sidequest-server/src/dispatch/connect.rs
git commit -m "feat(otel): add archetype axis and resolution tier spans to NPC and chargen"
```

### Task 21: End-to-end verification

- [ ] **Step 1: Build everything**

Run: `cd sidequest-api && cargo build`

Expected: Clean build, no warnings.

- [ ] **Step 2: Run full test suite**

Run: `cd sidequest-api && cargo test`

Expected: All tests pass.

- [ ] **Step 3: Run namegen with axis flags**

Run: `cd sidequest-api && cargo run -p sidequest-namegen -- --genre low_fantasy --jungian sage --rpg-role healer --genre-packs-path ../sidequest-content/genre_packs 2>/dev/null | python3 -m json.tool`

Expected: JSON output with `jungian_id`, `rpg_role_id`, `resolved_archetype` fields populated.

- [ ] **Step 4: Run namegen without axis flags (random selection)**

Run: `cd sidequest-api && cargo run -p sidequest-namegen -- --genre neon_dystopia --genre-packs-path ../sidequest-content/genre_packs 2>/dev/null | python3 -m json.tool`

Expected: Random axis selection from valid pairings, all new fields present.

- [ ] **Step 5: Verify genre packs load with new files**

Run: `cd sidequest-api && cargo test --test archetype_integration_test`

Expected: Integration test passes — constraints and funnels loaded, resolution works.

- [ ] **Step 6: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final cleanup for three-axis archetype system"
```
