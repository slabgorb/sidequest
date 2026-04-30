# Three-Axis Archetype System

Unified archetype model for PC chargen and NPC generation, replacing the current
disconnected systems (flat `archetypes.yaml` + bespoke `char_creation.yaml`) with
a composable, inheritable architecture.

## Problem

Two parallel systems describe the same conceptual space:
- `archetypes.yaml` — NPC-only templates (personality, OCEAN, stats, dialogue quirks)
- `char_creation.yaml` — PC-only narrative scenes producing mechanical hints

They share no schema, no vocabulary, no inheritance. Chargen never references
archetypes. NPC gen never uses chargen's vocabulary. Result: duplicated concepts,
no reuse, and Claude defaults to "burly blacksmith / female bartender giving
fetch quests" when generating NPCs on the fly because there's no structured
pipeline feeding it.

## Design

### The Three Axes

Base-level, genre-agnostic structural identifiers. Never shown to players directly.

**Jungian Archetype** — inner drive, personality core:
caregiver, ruler, artist, innocent, sage, explorer, outlaw, magician, hero, lover,
jester, everyman

**RPG Role** — mechanical function:
tank, dps, control, healer, stealth, support, jack-of-all-trades

**NPC Role** — narrative function (NPC gen only, never player-facing):
mentor, herald, shadow, threshold, host, artisan, authority, victim, mook

PCs select Jungian + RPG Role through chargen. NPCs get all three, with NPC Role
assigned first based on what the story needs.

### Inheritance Chain: Base -> Genre -> World

All content definitions follow a three-layer inheritance model. Resolution walks
down the chain; each layer enriches without breaking the upstream shape.

**Base layer (genre-agnostic):**
- Defines the axis values (the lists above)
- Defines universal OCEAN score tendencies per Jungian archetype (sage skews high
  openness/conscientiousness everywhere)
- Defines universal stat affinities per RPG role (healer always leans toward the
  genre's equivalent of wisdom/support stats)
- No names, no flavor, no lore. Pure structure.

**Genre layer:**
- Defines valid pairings — which Jungian x RPG combinations exist in this genre,
  weighted as common/uncommon/rare/forbidden
- Adds genre flavor: speech patterns, equipment tendencies, visual style cues
- Provides genre-level fallback names for combinations no world claims (a
  neon_dystopia healer is a "Street Doc" unless the world overrides)
- Defines NPC Role availability (spaghetti_western might not use "host,"
  road_warrior might merge "artisan" into something else)

**World layer:**
- Defines funnels — many-to-one mappings from axis combinations to named world
  archetypes ("Hierarch," "Fool's Guild initiate," "Thornwall Mender")
- Adds lore: faction membership, cultural expectations, local reputation,
  relationship seeds
- Can further constrain what the genre allows (a theocracy world removes "outlaw"
  or funnels it into "heretic")
- Provides the names that chargen and the narrator actually use

Resolution order: world -> genre -> base. If the world defines a funnel for this
combination, use it. If not, fall back to genre name. If genre doesn't name it
either, it's not a valid combination.

### Constraint and Funnel System

**Constraints (genre level):**

Valid Jungian x RPG pairings classified as:
- `common` — chargen presents these by default, NPC gen draws from them most
- `uncommon` — show up if player explores or for NPC pool diversity
- `rare` — allowed but unusual, produces memorable weird combos
- `forbidden` — genuinely nonsensical for the genre

Chargen freeform input can still land on uncommon/rare — the system resolves it,
never refuses.

**Funnels (world level):**

Many-to-one mappings from axis combinations to named world archetypes:
- `{jester + stealth}`, `{jester + dps}` -> "Fool's Guild"
- `{healer + ruler}`, `{caregiver + healer}` -> "Hierarch"

A world typically defines 15-20 funneled archetypes that absorb all valid
combinations. Combinations not explicitly funneled fall back to genre-level names.
Funnels carry lore payload: faction membership, cultural status, default
disposition toward other funneled archetypes.

Authoring a new world = define your funnels, write the lore for each. Axes and
genre constraints are inherited.

### PC Chargen Pipeline

Chargen keeps its narrative scene structure. What changes is the mechanical layer.

1. Narrative scenes present genre/world-flavored choices (same feel as today)
2. Each choice maps to axis values behind the curtain
3. By end of scene flow, axes resolve through the world's funnel to a **named
   archetype** ("Thornwall Mender," "Datashade")
4. Named archetype is presented to the player with world-lore description
5. Backstory generation in three modes:
   - **Manual** — player writes their own, system validates fit and offers lore
     hooks to weave in
   - **Guided** — system proposes backstory elements, player picks and edits
   - **Auto** — system generates full backstory from archetype + world state

`char_creation.yaml` files get refactored: narrative scenes stay, `mechanical_effects`
replaced with axis mappings. `allows_freeform: true` stays — Zork Problem means
the player can always say something unexpected, and the system resolves to the
nearest valid combination.

### NPC Generation Pipeline

Two paths, same pipeline, different timing.

**Pre-gen (world-build time):**
1. Read POI roster for each location
2. Assign NPC Role first (what does this location need?)
3. Assign Jungian + RPG Role from valid pairings, weighted for diversity
4. Run through genre -> world enrichment, funnel produces named archetype
5. Generate OCEAN scores from Jungian base tendencies + genre variance
6. Generate backstory with faction linkages, relationship seeds
7. Queue portrait generation
8. Inject into game state as world facts

**On-the-fly (narrator needs someone or player creates demand):**
Same pipeline steps 1-6, minus portrait queue. Injected into game state
immediately so they persist. Triggered when the narrator needs an NPC or when the
player asserts one into existence ("I just got mugged" — Yes, And).

**Resolution tiers (Diamonds and Coal):**
- **Spawn** — axes assigned, name, one quirk ("nervous laugh," "missing fingers").
  Coal. No trope connections, no plot hooks. A quirk is a quirk, not a mystery.
- **Engage** — player interacts beyond initial moment. Backstory fills in from
  world layer, faction links resolve, personality deepens. Baited hook.
- **Promote** — player keeps engaging. Full backstory, portrait queued,
  relationship web connected to PCs and factions. Diamond.

**Promotion heuristic:** Three non-transactional interactions. Buying a sword
doesn't count. Asking the merchant about the scar on their face does. The
narrator tracks interactions *as a person* vs interactions *as a service
interface*. Transactional exchanges (buy, sell, ask for directions) don't
advance the counter. Personal engagement (ask about their past, notice
something about them, return to continue a conversation) does.

The system never overbaits at spawn. Promotion is triggered by player interest,
not by the generator deciding every NPC is secretly important.

**Mooks** are a special case — NPC Role "mook" skips enrichment entirely. Name,
basic description, combat stats. May be treated as monsters rather than NPCs
if that simplifies the system.

### Integration Points

**Trope Engine:**
- Tropes reference archetypes by name (unchanged). Names now come from funnels.
- Trope escalations requesting "a mentor" can query by NPC Role axis. System
  finds or generates one from the pool.

**Narrator / Game State:**
- Pre-gen NPCs injected as world facts (existing Monster Manual pattern).
  Narrator picks from pool, doesn't invent.
- On-the-fly NPCs go through same pipeline, injected immediately.
- Narrator sees named archetype and lore payload, never raw axes.

**OTEL Observability:**
- NPC generation emits spans: axes selected, funnel resolved, resolution tier
- Promotion events tracked — coal-to-diamond logged so GM panel can verify
  narrator isn't secretly promoting everyone
- Missing generation spans = narrator improvising NPCs. Red flag.

**Existing Content Migration:**
- Current `archetypes.yaml` decomposed: each existing archetype maps to axis
  values and becomes a funnel entry at genre or world level
- Current `char_creation.yaml` refactored: narrative scenes stay,
  `mechanical_effects` replaced with axis mappings
- OCEAN scores on existing archetypes become Jungian base tendencies

**Portrait / Image System:**
- Pre-gen and promoted NPCs queue portrait generation
- Visual style draws from named archetype's genre/world layer
- Monster manual entries get archetype-level portraits shared across instances

## Future Extensions (Not In Scope)

- Leitmotifs / theme music per archetype funnel
- Visual signature system per archetype
- Archetype-driven dialogue style injection
- Cross-world archetype comparison tooling

## YAML Schema (Illustrative)

### Base layer: `archetypes_base.yaml`
```yaml
jungian:
  - id: sage
    ocean_tendencies:
      openness: [7.0, 9.5]
      conscientiousness: [6.0, 8.0]
      extraversion: [2.0, 5.0]
      agreeableness: [4.0, 7.0]
      neuroticism: [3.0, 6.0]
    stat_affinity: [wisdom, intellect, insight]  # genre resolves to local stat names

rpg_roles:
  - id: healer
    stat_affinity: [wisdom, support]
    combat_function: restoration

npc_roles:
  - id: mentor
    narrative_function: guides protagonist, provides knowledge or training
  - id: mook
    narrative_function: disposable opposition
    skip_enrichment: true
```

### Genre layer: `low_fantasy/archetype_constraints.yaml`
```yaml
valid_pairings:
  common:
    - [hero, tank]
    - [sage, healer]
    - [outlaw, stealth]
    - [caregiver, support]
  uncommon:
    - [jester, dps]
    - [explorer, control]
    - [ruler, support]
  rare:
    - [innocent, stealth]
    - [jester, tank]
  forbidden:
    - [innocent, dps]

genre_flavor:
  sage:
    speech_pattern: "measured, archaic vocabulary, references to old texts"
    equipment_tendency: "robes, walking staff, herb pouch"
    visual_cues: "weathered hands, ink-stained fingers"
  healer:
    fallback_name: "Hedge Healer"
```

### World layer: `low_fantasy/worlds/iron_marches/archetype_funnels.yaml`
```yaml
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
      and the green cord at their wrist.
    cultural_status: respected but watched
    disposition_toward:
      Iron Guard: cautious
      Freeholders: trusted

  - name: Fool's Guild
    absorbs:
      - [jester, stealth]
      - [jester, dps]
      - [outlaw, stealth]
    faction: The Fool's Guild
    lore: >-
      Part spy network, part traveling performers. Nobody takes
      them seriously, which is exactly how they like it.
    cultural_status: tolerated, secretly feared
```
