# Magic Plugins

**Status:** Active spec directory, opened 2026-04-27.
**Parent docs:** `../magic-taxonomy.md`, `../visible-ledger-and-otel.md`

## What is a Magic Plugin?

A magic plugin is **one parallel magic system** within a genre. Multiple plugins coexist in a single genre — heavy_metal can run a Bargained-For plugin alongside a Divine plugin alongside a Learned-Ritual plugin. Each plugin defines its own:

- **Source** (which napkin Source it implements)
- **Delivery mechanisms** (one or more of: faction, place, time, condition, native, discovery, relational, cosmic — each with its own plot engine)
- **Class/archetype mapping** (which player builds use this plugin)
- **Counter archetypes** (which NPCs oppose this plugin)
- **Ledger bars** (what costs appear on the visible ledger)
- **OTEL span shape** (what the narrator must emit when invoking this magic)
- **Hard limits** (specialized fences beyond the genre baseline)

**Faction is one delivery mechanism among several, not THE delivery mechanism.** A plugin's resource can reach the player through institutions, places, calendar events, player-state conditions, native traits, found objects, personal bonds, or ambient world-truth. Each unlocks a different story shape.

## Why Plugins, Not Inheritance?

Genres aren't single magic systems — they're *collections* of magic systems. A D&D-style heavy_metal world has Cleric (Divine plugin) + Wizard (Learned-Ritual plugin) + Sorcerer (Innate plugin) + Warlock (Bargained-For plugin) all running simultaneously, and *each magic system bills differently*. Inheritance forces one shape; plugins let parallel shapes coexist.

The same architecture covers non-magic pipelines: spaghetti_western's gunsmith faction supplies trick rounds via the same plugin shape. **Every "where does the player get this from?" question routes through some delivery mechanism — faction is one option among several.** Magic systems and material economies share the same architecture.

## Plugin Spec Template

Every plugin lives as a single markdown file: `<plugin_id>_v<n>.md`.

```yaml
plugin: <plugin_id>_v1
status: draft | committed | superseded
genres_using: [heavy_metal, victoria, ...]

source: <one of the napkin Source values>

# One or more — worlds pick which to activate.
# Each mechanism brings its own plot engine.
delivery_mechanisms:
  - id: faction              # institution as broker/distributor
    archetype: <generic faction type>
    description: <what this faction does>
    npc_roles: [list]
    plot_engine: politics, NPC dispatch, betrayal arcs
  - id: place                # location-bound resource
    description: <where in the world>
    plot_engine: pilgrimage, territorial control
  - id: time                 # calendar/season/event-gated
    description: <when it's available>
    plot_engine: deadlines, cyclical urgency
  - id: condition            # player-state-gated (penance, fast, blood-debt)
    description: <what condition must be met>
    plot_engine: self-imposed transformation, ritual purity
  - id: native               # born with it
    description: <which trait>
    plot_engine: identity arcs, growing into power
  - id: discovery            # find it in the world
    description: <typical find-context>
    plot_engine: treasure-hunt, dungeon-crawl
  - id: relational           # personal bond with non-faction entity
    description: <bond shape>
    plot_engine: patron-protégé arcs, bonds-and-betrayals
  - id: cosmic               # ambient world-truth
    description: <which axis>
    plot_engine: low-friction; usually combined with another mechanism

classes:
  - id: <class_id>
    label: <display>
    requires: <pact / training / inheritance / etc.>

counters:
  - id: <counter_id>
    label: <display>
    description: <what this counter does>

ledger_bars:
  - id: <bar_id>
    label: <display>
    scope: character | world | faction | location | item | bond_pair
    range: [<min>, <max>]              # [-1.0, 1.0] for bidirectional, [0.0, 1.0] for monotonic
    direction: monotonic_up | monotonic_down | bidirectional
    threshold_high: <fill triggering high-side consequence>     # required if monotonic_up or bidirectional
    threshold_higher: <deeper threshold>                        # optional second tier
    threshold_low: <fill triggering low-side consequence>       # required if monotonic_down or bidirectional
    threshold_lower: <deeper threshold>                         # optional second tier
    consequence_on_high_cross: <description>
    consequence_on_low_cross: <description>                     # only for bidirectional/monotonic_down
    decay_per_session: <0.0 if never decays — but see Decision #3 clarification below>
    starts_at_chargen: <0.0–1.0 default starting value>
    cyclical_reset:                         # OPTIONAL — only for bars that
                                            # restore on event triggers
      trigger: <event name>                 # e.g. ritual_cycle, dawn, season
      reset_to: <0.0–1.0 reset level>

otel_span:
  span_name: magic.working
  required_attributes: [list]               # universal + plugin-required
  optional_attributes: [list]               # plugin-defined extensions allowed
  yellow_flag_conditions: [list]
  red_flag_conditions: [list]
  deep_red_flag_conditions: [list]
  on_violation: gm_panel_red_flag

# Plugins MAY extend the OTEL span with plugin-specific attributes
# (e.g. item_legacy_v1 adds item_id, alignment_with_item_nature;
#  bargained_for_v1 adds patron_id). The base span name is universal;
#  attributes beyond the universal set live in the plugin's optional_attributes.

hard_limits:
  inherits_from_genre: true
  additional_forbidden: [list]

narrator_register: |
  <prose register the narrator must use when this plugin fires>

# The confrontation types this plugin participates in.
# See ../confrontation-advancement.md for the schema.
# Each confrontation declares its own moves, stakes, branches, and outputs
# — and outputs are how characters advance when this plugin's magic is in play.
confrontations:
  - id: <confrontation_id>           # e.g. the_bargain
    label: <display>
    resource_pool: { primary: <bar>, secondary: <bar> }
    stakes: { declared_at_start: true|false }
    outcomes:
      - branch: clear_win
        mandatory_outputs: [...]      # at least one (Decision #1)
        optional_outputs: [...]
      - branch: pyrrhic_win
        mandatory_outputs: [...]
        optional_outputs: [...]
      - branch: clear_loss            # failure advances (Decision #4)
        mandatory_outputs: [...]      # different output menu, but real growth
        optional_outputs: [...]
      - branch: refused               # walking away advances too
        mandatory_outputs: [...]
        optional_outputs: [...]
    reveal:
      mode: explicit                  # always explicit (Decision #2)
      timing: at_outcome
      format: panel_callout
```

## Active Specs

| Plugin | Status | Source | Genres |
|---|---|---|---|
| `bargained_for_v1` | ✅ drafted 2026-04-28 | bargained_for | heavy_metal, victoria-high-gothic, low_fantasy-with-pacts |
| `item_legacy_v1` | ✅ drafted 2026-04-28 | item_based | spaghetti_western, road_warrior, c&c, heavy_metal, victoria, low_fantasy, pulp_noir |
| `divine_v1` | ✅ drafted 2026-04-28 | divine | heavy_metal, victoria-Catholic, low_fantasy, elemental_harmony, space_opera-religious |
| `innate_v1` | ✅ drafted 2026-04-28 | innate | mutant_wasteland (signature), space_opera-Firefly-River, victoria-touched, low_fantasy-bloodline, untrained Force/bender register |
| `learned_v1` | ✅ drafted 2026-04-28 | learned | elemental_harmony (signature — bending discipline), space_opera-Jedi-trained, low_fantasy-wizards, witcher-signs, Bene Gesserit, heavy_metal-rite-priest, pulp_noir-Hermetic, spaghetti_western-gunsmith |
| `obligation_scales_v1` | ✅ drafted 2026-04-28 | (multi-plugin layer — cross-cutting tracker, no Source) | heavy_metal signature — tracks the five obligation scales (individual, communal, covenant, divine, stratigraphic) across all monitored Source plugins |

**Framework plugin coverage is mechanically complete.** All five napkin Sources are covered by Source-shaped plugins, and the heavy_metal-specific multi-plugin tracker is drafted. Remaining work is concrete world-layer instantiations and architect/dev/UX review passes.

### Folded plugins (no longer separate specs)

- `mccoy_v1` — folded into `item_legacy_v1` as a delivery mechanism *(2026-04-28)*. Building an item is acquisition; what's built is an item with personality. Smith / Tinkerer classes in item_legacy_v1 are McCoy-using.
- `mutation_v1` — folded into `innate_v1` as the acquired-via-event flavor *(2026-04-28)*. Mutations are Innate with an event-acquisition narrative texture, not a separate Source.
- `innate_developed_v1` — folded into `learned_v1` as Learned-with-prerequisite-gate *(2026-04-28)*. Trained Force-sensitives, trained benders, trained Witcher-mutated — all Learned with an Innate prerequisite. Untrained register lives in `innate_v1`.

## Plugin Lane Respect

Plugins explicitly delineate their territory. When a plugin's `hard_limits` cite another plugin's domain (e.g. divine_v1 forbids deity-targeted bargaining because that's bargained_for_v1's territory), the citation is meaningful — it prevents content drift where a narrator improvises a "this divine working is actually a bargain" workaround. Plugins are encouraged to write hard_limits like:

```yaml
hard_limits:
  additional_forbidden:
    - id: deity_targeted_bargaining
      description: |
        You don't negotiate with gods. Bargaining-with-a-god is the
        bargained_for_v1 plugin's territory. Doing it inside divine_v1
        is heresy.
      references_plugin: bargained_for_v1
```

This pattern keeps plugins concrete in their lane and lets the cliché-judge / OTEL panel detect lane-crossings.

## Plugin vs. Genre vs. World — Layer Boundaries

| Lives at... | Defines... | Example |
|---|---|---|
| Plugin spec (this dir) | The magic-system shape itself | "How does Bargained-For magic work in any world?" |
| Genre `magic.yaml` | Which plugins this genre permits + universal narrator register | "Heavy_metal allows bargained, divine, learned-ritual; never alchemy" |
| World `magic.yaml` | Named factions instantiating each plugin + world's intensity dial | "The Long Reckoning's Bargainers Guild is the Eastern Chapter; gravity is 0.85" |

**Plugins NEVER live at the world layer.** Worlds inherit; they don't define new magic systems.

## Authoring Discipline

- One file per plugin, one plugin per file
- Plugin IDs are versioned: `bargained_for_v1`, then `_v2` for breaking changes
- Plugin specs are **content** (this is the GM's lane). Implementation lives in code; this dir is the source of truth for *what should exist*.
- Each plugin's `ledger_bars` and `otel_span` must be concrete enough that the visible-ledger UI and the OTEL watcher can be built against them
