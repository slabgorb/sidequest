# Epic 16: Genre Mechanics Engine — Confrontations & Resource Pools

## Overview

Build two generic subsystems that let genre packs declare mechanical rules the engine
enforces, closing the content-vs-engine gap across all 9 genre packs. Plus a targeted
MusicDirector extension for genre-specific moods.

**Pillar 1: Resource Pools** — Persistent named resources (Luck, Humanity, Heat) with
spend/gain/threshold events that feed into LoreStore as permanent narrator memory.

**Pillar 2: Structured Encounters** — Generalize ChaseState into a YAML-declarable
encounter engine for standoffs, negotiations, gambling, Russian roulette, net combat,
ship combat, and any future structured encounter type.

**Pillar 3: Mood Extension** — String-keyed mood aliases so genre-specific moods
(standoff, saloon, convoy, cyberspace) play the right music instead of falling through.

**ADR:** 033-confrontation-engine-resource-pools.md, 059-monster-manual-server-side-pregen.md

## Current State (as of 2026-04-04)

### What's Done

Stories 16-1 through 16-4 are complete and merged. The playtest branch
(`fix/playtest-tools-and-npc-dedup`) also delivered Monster Manual (ADR-059),
NPC combat integration, and significant combat/NPC fixes that weren't part of the
original epic plan but materially advanced the confrontation infrastructure.

**Combat System** (420 LOC, `combat.rs`) — Fully operational:
- Level-scaled damage with defense mitigation: `defense / (defense + 20)`, min 1 damage
- Status effects: Poison, Stun, Bless, Curse with round-based tick/expire
- Turn order, advance_turn, round tracking, drama_weight for pacing
- Victory conditions: check_victory returns Victory/Defeat/None
- Implements Combatant trait (`name`, `hp`, `max_hp`, `level`, `ac`) — NPCs implement it
- Full OTEL coverage: resolve_attack, damage_log, effects, engage/disengage

**Monster Manual** (442 LOC, `monster_manual.rs`) — ADR-059, fully wired:
- Persistent JSON at `~/.sidequest/manuals/{genre}_{world}.json`
- Pre-generated NPC + encounter pools with lifecycle: Available → Active → Dormant
- Injected into narrator's `<game_state>` section (dispatch lines 385-405)
- Location anchoring, OCEAN summaries, dialogue quirks in formatted output
- Name-based dedup prevents double-registration
- `needs_seeding()` triggers server-side pregen via tool binaries

**NPC Registry** (586 LOC, `npc.rs`) — Dual-model architecture:
- **NpcRegistryEntry** (lightweight, narrator-facing): name, pronouns, role, location,
  last_seen_turn, OCEAN summary, hp/max_hp for combat
- **Npc** (full mechanical): CreatureCore + disposition, identity-locked fields
  (pronouns, appearance, age, build, height, distinguishing_features)
- Identity locking: `merge_patch` checks emptiness before write, logs OTEL on
  attempted overwrites — prevents narrator from changing NPC appearance mid-session
- Disposition → Attitude mapping: Friendly (>10), Neutral (-10..10), Hostile (<-10)
  with OCEAN Agreeableness ±4 bias
- Registration flow: narration extraction → name-length sort (dedup) → namegen CLI
  validation → OCEAN enrichment → identity backfill

**StructuredEncounter** (385 LOC, `encounter.rs`) — Universal model:
- String-keyed `encounter_type` replaces hardcoded combat/chase enums
- EncounterMetric: arbitrary name, current/starting i32, direction (Ascending/
  Descending/Bidirectional), threshold_high/low for resolution
- EncounterPhase: Setup → Opening → Escalation → Climax → Resolution (drama_weight
  per phase for cinematography pacing)
- SecondaryStats: generic `HashMap<String, StatValue>` (supports rig, ship, etc.)
- Constructors: `combat()`, `chase()`, `from_combat_state()`, `from_chase_state()`
- Ready for confrontation beat dispatch (next stories)

**ConfrontationDef YAML Schema** — Parsed by genre loader:
- `confrontation_type`, `label`, `category` (combat/social/pre_combat/movement)
- `metric: MetricDef` — name, direction, starting, threshold_high/low
- `beats: Vec<BeatDef>` — id, label, metric_delta, stat_check, risk, reveals,
  cost, requires, resolution flag, narrator_hint, consequence
- `secondary_stats`, `escalates_to`, `mood` override
- Validated on deserialization (non-empty type, valid category, unique beat IDs)

### What's Not Done

- **Beat dispatch wiring** — narrator action → beat selection → metric delta. The types
  exist but the dispatch pipeline doesn't route actions through confrontation beats yet.
- **ResourcePool** — struct designed (in ADR-033) but not implemented
- **Threshold → KnownFact pipeline** — designed but not built
- **UI components** — no EncounterOverlay or ResourceBar yet
- **Genre-specific confrontation types** — only star_chamber has confrontations declared.
  Spaghetti_western, pulp_noir, neon_dystopia, space_opera, road_warrior all need them.
- **Gambling confrontation types** — poker, blackjack, oicho-kabu, Russian roulette

## Background

### The Gap Map (docs/genre-pack-status.md)

Every genre pack defines unique mechanics in rules.yaml. The engine provides generic
subsystems (combat, chase, tropes, factions). Genre-specific rules are LLM-interpreted
only — the narrator reads rules.yaml and applies them narratively. The risk: narrator
drift, forgotten mechanics, contradictory state.

| Genre | Mechanic | Current Enforcement |
|-------|----------|-------------------|
| spaghetti_western | Standoff (pre-combat NERVE ritual) | LLM only |
| spaghetti_western | Luck (spendable resource, 0-6) | LLM only |
| spaghetti_western | Poker / gambling encounters | LLM only |
| neon_dystopia | Humanity Tracker (degrades at 50/25/0) | LLM only |
| pulp_noir | Heat Tracker (0-5, affects factions) | LLM only |
| pulp_noir | Gambling (card games, "Your winnings, monsieur") | LLM only |
| pulp_noir | Contacts system | LLM only |
| space_opera | Ship Block (shields, hull, engines) | LLM only |
| space_opera | Crew Bonds | LLM only |
| road_warrior | Rig HP, Fuel (outside chase context) | Partial — in chase_depth.rs during chases only |
| road_warrior | 10 faction music themes | Tracks exist, no routing logic |
| All genres | 15+ custom moods (standoff, saloon, etc.) | Fall through to nearest of 7 core moods |

### Key Reference Files (Updated)

| File | LOC | Role |
|------|-----|------|
| `sidequest-game/src/combat.rs` | 420 | CombatState — level-scaled damage, status effects, Combatant trait |
| `sidequest-game/src/encounter.rs` | 385 | StructuredEncounter — universal string-keyed encounter model |
| `sidequest-game/src/chase_depth.rs` | 900 | RigStats, beats, terrain, cinematography — chase subsystem |
| `sidequest-game/src/monster_manual.rs` | 442 | MonsterManual — persistent NPC/encounter pre-generation |
| `sidequest-game/src/npc.rs` | 586 | NPC registry, identity locking, OCEAN enrichment |
| `sidequest-game/src/music_director.rs` | 984 | MusicDirector — mood selection, cinematic cues |
| `sidequest-game/src/state.rs` | 1091 | GameSnapshot — gets `resources` field |
| `sidequest-game/src/trope.rs` | 462 | TropeEngine — pattern reference for threshold events |
| `sidequest-game/src/lore.rs` | → `lore/` | LoreStore — receives threshold KnownFacts |
| `sidequest-genre/src/models/rules.rs` | 297 | RulesConfig, ConfrontationDef, BeatDef, MetricDef |
| `sidequest-agents/src/orchestrator.rs` | 992 | Claude CLI orchestration |
| `sidequest-server/src/dispatch/mod.rs` | 2132 | Dispatch pipeline — NPC registry, combat, Monster Manual injection |

## Technical Architecture

### Resource Pool System

**On GameSnapshot:**
```rust
// state.rs
pub resources: HashMap<String, ResourcePool>,
```

**ResourcePool struct:**
```rust
pub struct ResourcePool {
    pub name: String,           // "luck", "humanity", "heat"
    pub label: String,          // "Luck", "Humanity", "Heat"
    pub current: f64,
    pub min: f64,
    pub max: f64,
    pub voluntary: bool,        // player can spend (Luck=true, Humanity=false)
    pub decay_per_turn: f64,    // auto-change per turn (Heat decays at -0.1)
    pub thresholds: Vec<ResourceThreshold>,
    pub fired_thresholds: HashSet<String>,  // idempotent across save/load
}

pub struct ResourceThreshold {
    pub at: f64,
    pub event_id: String,
    pub narrator_hint: String,
    pub direction: ThresholdDirection,  // CrossingDown, CrossingUp, Either
}
```

**Threshold → KnownFact pipeline:**
1. `ResourcePool::apply_delta()` detects threshold crossing
2. Checks `fired_thresholds` set (idempotent)
3. Mints `KnownFact` with category "resource_event", event_id, narrator_hint
4. LoreStore indexes with high relevance score
5. Narrator prompt includes via existing budget-aware selection
6. Fact persists forever — narrator literally cannot forget

### Structured Encounter System (Implemented)

**StructuredEncounter** is the universal model. Genre packs declare confrontation
types in `rules.yaml` as `ConfrontationDef`. At runtime, the engine instantiates a
`StructuredEncounter` from the matching `ConfrontationDef`, tracking the metric,
beats, phase, and secondary stats.

**Resolution:** When `metric.current` crosses `threshold_high` or `threshold_low`,
the encounter resolves. Optional `escalates_to` triggers a follow-on (e.g.,
standoff → combat). The 5-phase arc (Setup → Opening → Escalation → Climax →
Resolution) drives drama_weight for cinematography pacing.

**Beat dispatch flow (to be wired):**
1. Player action classified as confrontation beat (by intent router or explicit choice)
2. Beat looked up in active ConfrontationDef
3. Stat check resolved against beat's `stat_check`
4. `metric_delta` applied to encounter metric
5. Optional: `reveals` information surfaced, `risk` consequence triggered
6. Resolution check: metric vs thresholds
7. OTEL span emitted for GM panel visibility

### Gambling Confrontation Types (New)

Gambling encounters use the confrontation engine with social category. The metric
tracks the player's stake/advantage, beats map to game actions, and resolution
conditions capture win/loss/bust.

**Poker** — spaghetti_western, pulp_noir
```yaml
- type: poker
  label: "Poker"
  category: social
  metric:
    name: edge          # psychological advantage, not chip count
    direction: bidirectional
    starting: 0
    threshold_high: 8   # dominating the table → win
    threshold_low: -8   # cleaned out → loss
  beats:
    - id: bet
      label: "Bet"
      metric_delta: 1
      stat_check: NERVE
      risk: "Bad hand — lose 2 edge on fail"
    - id: raise
      label: "Raise"
      metric_delta: 3
      stat_check: CUNNING
      risk: "Overplayed — lose 3 edge if called and weak"
    - id: bluff
      label: "Bluff"
      metric_delta: 2
      stat_check: CUNNING
      risk: "Called bluff — lose 4 edge, table reads you"
      reveals: opponent_tell
    - id: call
      label: "Call"
      metric_delta: 0
      stat_check: PERCEPTION
      reveals: hand_strength
    - id: fold
      label: "Fold"
      metric_delta: -1
      narrator_hint: "Live to play another hand."
    - id: read_table
      label: "Read the Table"
      metric_delta: 0
      stat_check: PERCEPTION
      reveals: opponent_tell
  mood: saloon
```

**Blackjack** — pulp_noir ("Your winnings, monsieur")
```yaml
- type: blackjack
  label: "Blackjack"
  category: social
  metric:
    name: hand_value
    direction: ascending
    starting: 0
    threshold_high: 21    # bust above 21
  beats:
    - id: hit
      label: "Hit"
      metric_delta: 0     # delta determined by draw — narrator resolves
      stat_check: LUCK
      narrator_hint: "Draw a card. Narrator determines value."
    - id: stand
      label: "Stand"
      metric_delta: 0
      resolution: true
      narrator_hint: "Hold. Dealer reveals and draws."
    - id: double_down
      label: "Double Down"
      metric_delta: 0
      stat_check: NERVE
      risk: "One card only — double the stakes"
      narrator_hint: "Double the bet, take exactly one more card."
    - id: count_cards
      label: "Count Cards"
      metric_delta: 0
      stat_check: PERCEPTION
      reveals: deck_state
      risk: "Caught counting — ejected from table"
  mood: saloon
```

**Oicho-Kabu** — Japanese card game, fits neon_dystopia yakuza dens, space_opera cantinas
```yaml
- type: oicho_kabu
  label: "Oicho-Kabu"
  category: social
  metric:
    name: hand_value       # 0-9 scale, closest to 9 wins
    direction: ascending
    starting: 0
    threshold_high: 9
  beats:
    - id: draw
      label: "Draw"
      metric_delta: 0      # narrator resolves card value
      stat_check: LUCK
      narrator_hint: "Draw a card. Hand value is last digit of sum."
    - id: stand
      label: "Stand"
      metric_delta: 0
      resolution: true
    - id: side_bet
      label: "Side Bet"
      metric_delta: 0
      stat_check: CUNNING
      risk: "Side bet lost — additional stakes"
      narrator_hint: "Wager on specific hand combinations (shippin, kuppin, arashi)."
    - id: read_dealer
      label: "Read the Dealer"
      metric_delta: 0
      stat_check: PERCEPTION
      reveals: dealer_tell
  mood: tension
```

**Russian Roulette** — ultimate tension confrontation, any genre with desperation
```yaml
- type: russian_roulette
  label: "Russian Roulette"
  category: social
  metric:
    name: rounds_survived
    direction: ascending
    starting: 0
    threshold_high: 6     # survived full cylinder → win
  beats:
    - id: spin
      label: "Spin the Cylinder"
      metric_delta: 0
      narrator_hint: "Reset the odds. The cylinder spins."
    - id: pull_trigger
      label: "Pull the Trigger"
      metric_delta: 1
      stat_check: NERVE
      risk: "Chamber fires — immediate loss"
      narrator_hint: "1-in-6 chance decreasing each round. Narrator resolves."
    - id: pass_gun
      label: "Pass the Gun"
      metric_delta: 0
      narrator_hint: "Opponent's turn. Watch their hands shake."
    - id: bluff_pull
      label: "Bluff Pull"
      metric_delta: 0
      stat_check: CUNNING
      risk: "Opponent calls the bluff — must actually pull"
      narrator_hint: "Fake the pull. Rattle their nerve."
    - id: taunt
      label: "Taunt"
      metric_delta: 0
      stat_check: CUNNING
      reveals: opponent_nerve
      narrator_hint: "Psychological warfare between clicks."
  escalates_to: null
  mood: tension
```

**Poison Chalice / Battle of Wits** — any genre with intrigue, deception, or court politics
```yaml
- type: poison_chalice
  label: "Battle of Wits"
  category: social
  metric:
    name: deduction
    direction: ascending
    starting: 0
    threshold_high: 8     # certain which cup → must choose
  beats:
    - id: interrogate_logic
      label: "Interrogate Their Logic"
      metric_delta: 2
      stat_check: PERCEPTION
      reveals: poisoner_tell
      narrator_hint: "Probe their reasoning. Where did they look when they poured?"
    - id: monologue
      label: "Expound on Poison Lore"
      metric_delta: 1
      stat_check: CUNNING
      narrator_hint: "Display knowledge. Watch their reaction to each detail."
    - id: switch_cups
      label: "Switch the Cups"
      metric_delta: 0
      stat_check: CUNNING
      risk: "Caught switching — opponent knows your cup is poisoned"
      narrator_hint: "Misdirection. But did they see?"
    - id: stall
      label: "Stall for Time"
      metric_delta: 1
      stat_check: NERVE
      narrator_hint: "Delay. Study. Wait for a tell."
    - id: drink
      label: "Drink"
      metric_delta: 0
      resolution: true
      stat_check: NERVE
      narrator_hint: "Choose a cup and drink. The truth reveals itself."
    - id: accuse
      label: "Accuse"
      metric_delta: 0
      resolution: true
      stat_check: PERCEPTION
      narrator_hint: "Declare which cup is poisoned. Force their hand."
  mood: tension
```

### Mood Extension (MusicDirector)

**YAML addition to audio.yaml:**
```yaml
mood_aliases:
  standoff: tension
  saloon: calm
  riding: exploration
  convoy: exploration
  betrayal: tension
  cyberspace: mystery
  club: exploration
  corporate: calm
  teahouse: calm
  spirit: mystery
  ceremony: calm
  void: sorrow
  gambling: tension
  tribunal: tension
```

**Resolution chain in MusicDirector:**
1. If active StructuredEncounter has `mood_override` → use that
2. Classify mood from narration keywords (existing, already string-keyed)
3. Look up classified mood in `mood_tracks` HashMap
4. If not found → follow `mood_aliases` chain
5. If still not found → fall back to "exploration" (safe default)

### UI Components

**GenericResourceBar:**
- Props: `name`, `value`, `max`, `color`, `thresholds`, `genreTheme`
- Renders in character sheet footer
- Threshold crossings trigger pulse animation + toast
- Audio sting via existing AudioCue on threshold

**EncounterOverlay:**
- Replaces/wraps existing CombatOverlay for non-combat encounters
- Shows: metric bar, available beats as action buttons, actor portraits
- Active StructuredEncounter's `encounter_type` determines visual treatment
- Standoff: letterbox framing, extreme close-up portraits
- Gambling: card table layout, chip/stake display, opponent tells
- Russian roulette: extreme tension UI — cylinder visualization, heartbeat audio
- Falls back to generic metric + beats for undefined types

### WebSocket Protocol

**New message types:**
```rust
// Resource state update (server → client)
ResourceUpdate {
    resources: HashMap<String, ResourceState>,
}

// Resource threshold event (server → client)
ResourceThresholdEvent {
    resource: String,
    event_id: String,
    narrator_hint: String,
}

// Encounter state update (server → client, replaces CHASE_UPDATE)
EncounterUpdate {
    encounter_type: String,
    metric: EncounterMetricState,
    beat: u32,
    phase: String,
    secondary_stats: Option<HashMap<String, f64>>,
    available_beats: Vec<BeatOption>,
}
```

## Story Dependency Graph

```
16-1 (prompt injection) ─── ✅ DONE
16-2 (StructuredEncounter) ─ ✅ DONE
16-3 (Confrontation YAML) ── ✅ DONE
16-4 (migrate combat) ────── ✅ DONE
16-14 (mood aliases) ─────── standalone quick win

16-5 (migrate chase) ──────→ 16-6 (standoff)
                             16-7 (social: gambling, interrogation)
                             16-8 (genre-specific: net combat, ship combat, roulette)

16-10 (ResourcePool) ──────→ 16-11 (threshold→KnownFact) ──→ 16-12 (wire genres)
         │
         └────────────────→ 16-13 (UI ResourceBar)

16-9 (UI EncounterOverlay) ─ after 16-5/6/7 so there are types to display

16-16 (content audit) ────── after all other stories
```

## Acceptance Criteria Summary

| Story | Key ACs |
|-------|---------|
| 16-1 | ✅ Resource state appears in narrator prompt context. |
| 16-2 | ✅ StructuredEncounter struct compiles. All existing chase tests pass. |
| 16-3 | ✅ Genre loader parses `confrontations` from rules.yaml. Schema validation on load. |
| 16-4 | ✅ CombatState migrated. `from_combat_state()` constructor works. |
| 16-5 | ChaseState expressed as StructuredEncounter. All chase_depth tests pass. |
| 16-6 | Standoff playable: beats resolve, tension builds, escalates to combat. |
| 16-7 | Poker, blackjack, oicho-kabu, interrogation encounter types declared and functional. Beat dispatch wired. |
| 16-8 | Net combat, ship combat, Russian roulette, auction declared in respective genre packs. |
| 16-9 | EncounterOverlay renders any encounter type. Gambling gets card table treatment. |
| 16-10 | ResourcePool loads from YAML, tracks state, validates patches, persists. |
| 16-11 | Threshold crossing mints KnownFact. Fact appears in narrator prompt. Idempotent. |
| 16-12 | Luck, Humanity, Heat functional as ResourcePool instances. |
| 16-13 | ResourceBar renders in character sheet. Threshold animation works. |
| 16-14 | Custom moods resolve via alias chain. Genre-specific tracks play. |
| 16-15 | Faction themes trigger by location/NPC context. Road warrior 10 factions tested. |
| 16-16 | All 9 genre packs updated. genre-pack-status.md reflects new completeness. |

## Confrontation Type Catalog

Types planned across all genre packs. Category in parentheses.

| Type | Genres | Category | Metric | Key Mechanic |
|------|--------|----------|--------|-------------|
| **standoff** | spaghetti_western | pre_combat | tension (asc) | NERVE duel, escalates to combat |
| **poker** | spaghetti_western, pulp_noir | social | edge (bidir) | Bluff/read/raise, psychological |
| **blackjack** | pulp_noir | social | hand_value (asc) | Hit/stand/count, bust at 21 |
| **oicho_kabu** | neon_dystopia, space_opera | social | hand_value (asc) | Japanese card game, yakuza dens |
| **russian_roulette** | any (desperation) | social | rounds_survived (asc) | Ultimate tension, 1-in-6 |
| **poison_chalice** | any (intrigue) | social | deduction (asc) | Battle of wits, iocane powder |
| **negotiation** | all | social | leverage (bidir) | Persuade/threaten/concede |
| **interrogation** | pulp_noir, star_chamber | social | cooperation (asc) | Good cop/bad cop |
| **inquisition** | star_chamber | social | conviction (bidir) | Testimony/cross-examine |
| **net_combat** | neon_dystopia | combat | firewall (desc) | ICE/programs/trace |
| **ship_combat** | space_opera | combat | hull (desc) | Shields/weapons/maneuver |
| **auction** | pulp_noir, victoria | social | bid (asc) | Outbid/bluff/sabotage |
| **chase** | all | movement | separation (asc) | Existing system, migrated |

## Planning Documents

| Document | Path |
|----------|------|
| ADR-033 | docs/adr/033-confrontation-engine-resource-pools.md |
| ADR-059 | docs/adr/059-monster-manual-server-side-pregen.md |
| Gap Analysis | docs/genre-pack-status.md |
| Chase ADR | docs/adr/017-chase-types.md |
| Patch ADR | docs/adr/011-structured-patches.md |
| Epic YAML | sprint/epic-16.yaml |
