# Plugin: item_legacy_v1

**Status:** Draft, 2026-04-28
**Source:** `item_based` (napkin)
**Genres using:** spaghetti_western, road_warrior, caverns_and_claudes, heavy_metal, victoria-high-gothic, low_fantasy, pulp_noir
**Companion docs:** `../magic-taxonomy.md`, `../visible-ledger-and-otel.md`, `../confrontation-advancement.md`, `bargained_for_v1.md` (companion plugin), `README.md` (this dir)

## Identity

Item Legacy magic is **the magic that lives in objects with personality**. The named gun, the named vehicle, the cursed letter, the inherited locket, the bargained-blade, the wizard's tower-relic. The items are not props — they are *characters* with OCEAN scores, dispositions, demands, and history.

Three things distinguish this plugin from others:

1. **The carrier is a thing, not a person.** Unlike `bargained_for_v1`'s sentient patron, an item's agency is *bounded* — it has preferences and demands but no broader life. It does not scheme; it *prefers*. The item's "voice" is implicit register, not literal speech (unless the world declares sentient items).
2. **The Bond bar moves both directions.** Unlike Soul/Debt (only rises), Bond is bidirectional. Use the item well (in service of what it wants) and Bond rises. Use it badly (against its nature, casually, dishonorably) and Bond falls. Crossing thresholds emits advancement events.
3. **Items have lifecycles.** They are found, claimed, bonded, used, demanded-of, set down, lost, stolen, destroyed, inherited. Other plugins don't have this carrier-lifecycle dimension. The plugin's confrontations follow this arc: The Finding → The Wielding → The Reckoning → The Renunciation.

## Plugin Definition

```yaml
plugin: item_legacy_v1
status: draft
genres_using:
  - spaghetti_western      # named guns, cursed bullets — signature
  - road_warrior           # named vehicles — signature
  - caverns_and_claudes    # cursed/relic items — signature
  - heavy_metal            # bargained-blades, stratigraphic artifacts
  - victoria               # cursed letters, locked-room keys, portraits
  - low_fantasy            # relics, surviving wizard's-tower items
  - pulp_noir              # artifacts, dead-language texts

source: item_based         # napkin Source

# ─────────────────────────────────────────────────────────────────────
# DELIVERY MECHANISMS — how the item reaches the wielder
# Once acquired, the item itself is the channel; mechanism describes
# the FINDING, not the using.
# ─────────────────────────────────────────────────────────────────────
delivery_mechanisms:
  - id: discovery
    description: |
      You find the item. The dungeon, the dead man's hand, the
      attic trunk, the abandoned vehicle in the wasteland. Most
      common acquisition path; central to dungeon-crawl genres.
    plot_engine: treasure-hunt, exploration-tension, "I have to find the X"
    canonical_examples:
      - "Stormbringer in the burial mound (Elric)"
      - "The Lassiter on the dead courier (Firefly)"
      - "A cursed scroll in the goblin warrens (caverns_and_claudes)"

  - id: relational
    description: |
      Someone gives it to you. Dying mentor, inheriting heir, gift,
      bequest, forced custody. The item arrives WITH a relationship
      attached — the giver's history is now part of the carrying.
    plot_engine: patron-protégé, inheritance arcs, debts-via-gift
    canonical_examples:
      - "The grandmother's locket, opened on her death"
      - "The dying mentor's gun pressed into your hand"
      - "The captain bequeathing his ship before the final raid"

  - id: faction
    description: |
      Institutional supply. The Smith's Guild, the Cartel, the Cult
      of the Sword that forges named blades, the corporation that
      issues prototype rifles to favored agents. The item is a
      faction-asset, lent or sold or earned-through-rank.
    plot_engine: politics, faction-rank arcs, allegiance-as-condition
    canonical_examples:
      - "The Templar Order issues a blessed blade to its knights"
      - "The Cartel's named cars given to top earners"
      - "The Crown's regalia — only worn by the chosen heir"

  - id: condition
    description: |
      The item only accepts wielders who meet a state-condition.
      Slay the dragon. Survive the trial. Have shed your own blood
      within the hour. Be of pure blood. Be of corrupted blood.
      The condition is the gate; meet it and the item answers.
    plot_engine: trial-arcs, ritual-purity, self-imposed transformation
    canonical_examples:
      - "The sword-in-the-stone (only the rightful king)"
      - "The relic that wakes only for one of the Founder's bloodline"
      - "The blood-brand that bonds only to those who have killed kin"

  - id: place
    description: |
      The item is locus-bound — it does not function (or does not
      leave) outside a specific location. Take the relic from the
      altar and it becomes inert. Drive the named car off the named
      road and it loses its weight.
    plot_engine: pilgrimage, geographic-tension, "I must bring X to Y"
    canonical_examples:
      - "The altar-bound chalice that bleeds only on the altar"
      - "The named blade that hums only in the ruins where it was forged"
      - "The cursed letter that opens only in the locked-room manor"

  - id: mccoy
    description: |
      You build it. The character creates the named item themselves —
      forging, machining, programming, jury-rigging, sculpting,
      writing, brewing, installing. Building is acquisition; what's
      built is an item with personality, history, and bond. The
      maker's hand is part of the item's history forever — items
      built by their wielder start with higher base bond but also
      higher implicit demand (the item knows whose hand made it).
    plot_engine: craft arcs, the workshop sequence, "I need to find
                 the part," the long build, the mistake-in-the-making
    canonical_examples:
      - "Doc Brown builds the flux capacitor (Back to the Future)"
      - "Tony Stark in the cave (Iron Man — first armor)"
      - "Q's gadget for this mission (Bond)"
      - "MacGyver improvising in the moment"
      - "The gunsmith's trick rounds (spaghetti_western)"
      - "The ripperdoc's chrome installation (neon_dystopia)"
      - "The wrencher's salvage rebuild (road_warrior)"
      - "The wizard's tower-relic, forged once (heavy_metal Smith)"
    flavors:
      - id: smith
        description: |
          Rare, slow, expensive. Produces legendary items. The
          legendary blade forged once. The relic that takes a
          decade. Often faction-mediated (a Smith works for a
          Cult, a Guild, a Crown).
      - id: tinkerer
        description: |
          Frequent, fast, cheap. Produces functional items used
          quickly. The gunsmith's trick rounds, MacGyver's
          improvising, the ripperdoc installing yesterday's chrome.
          The made item still has personality but typically
          short-lived (consumed, broken, replaced).

# Mechanisms NOT supported:
# - native: items are by definition external (you can't be born wielding one;
#   even inheritance is acquisition, not native)
# - time: rare enough to fold into condition (e.g. "wakes only at the eclipse"
#   is a time-condition compound; defer to condition mechanism with
#   time-axis tag if needed)
# - cosmic: items are specific, not ambient

# ─────────────────────────────────────────────────────────────────────
# CLASSES — player-build options that draw from this plugin
# ─────────────────────────────────────────────────────────────────────
classes:
  - id: wielder
    label: Wielder
    requires: []                 # no chargen item required; can acquire in play
    typical_mechanisms: [discovery, relational]
    narrator_note: |
      The general carry-a-named-thing archetype. Spaghetti western
      gunslingers, low_fantasy relic-bearers, caverns_and_claudes
      delvers who've found something they can name. Default class
      for most genres permitting this plugin.

  - id: bonded
    label: Bonded
    requires: [item_at_chargen, bond_bar >= 0.5]
    typical_mechanisms: [relational, condition]
    pact_visibility_to_player: full
    narrator_note: |
      The Elric archetype — character is *defined* by their item.
      Cannot put it down without the Renunciation confrontation.
      The item shows up in the character's identity, not just
      their inventory. High mechanical power; high narrative cost.

  - id: inheritor
    label: Inheritor
    requires: [item_at_chargen, item_acquisition: relational]
    typical_mechanisms: [relational, condition]
    narrator_note: |
      Received the item via lineage, gift, or bequest. The giver's
      history travels with the item. Often used in victoria
      (the family locket, the inherited library) and low_fantasy
      (the heirloom blade, the family's long-kept relic).

  - id: salvager
    label: Salvager / Hunter
    requires: []
    typical_mechanisms: [discovery, faction]
    narrator_note: |
      Seeks named items actively. The treasure-hunter archetype.
      Often allied with a Smith or Maker who can identify and
      restore. Common in road_warrior (wasteland scavengers) and
      caverns_and_claudes (the dungeoneer who dreams of the
      Sealed Chamber).

  - id: smith
    label: Smith / Maker
    requires: [smith_at_chargen]
    typical_mechanisms: [mccoy, faction, condition]
    narrator_note: |
      Creates legendary named items via the mccoy mechanism's
      smith-flavor. Rare, slow, expensive — one major work per
      campaign arc, with the making itself as a confrontation
      sequence. Often faction-mediated (a Smith works for a
      Cult, a Guild, a Crown). The wizard's tower-relic, the
      bargained-blade forged once, the named car built lovingly
      over years.

  - id: tinkerer
    label: Tinkerer / Gunsmith / Ripperdoc
    requires: [craft_at_chargen]
    typical_mechanisms: [mccoy, faction]
    narrator_note: |
      Creates functional items via the mccoy mechanism's
      tinkerer-flavor. Fast, frequent, less legendary but more
      useful in play. The gunsmith making trick rounds, MacGyver
      improvising in the moment, the ripperdoc installing
      yesterday's chrome. Items are typically short-lived
      (consumed, broken, replaced) but each still has personality
      and bond while in play.

# ─────────────────────────────────────────────────────────────────────
# COUNTERS — character archetypes that oppose this plugin
# ─────────────────────────────────────────────────────────────────────
counters:
  - id: rival_wielder
    label: The Other Wielder
    description: |
      Someone with their own named item whose item's nature
      conflicts with yours. The fastest gun. The other vehicle.
      The opposing relic. Often the most narrative-rich counter —
      both characters have full ledgers and arcs.
    plot_use: |
      `enemy_made` output. Often the campaign-arc antagonist.
      The two items contest at climactic confrontations.

  - id: thief
    label: The Thief
    description: |
      Wants to take the item. Operates by stealth, deception, or
      betrayal. Rarely a direct combatant; usually a recurring
      irritant who escalates over sessions.
    plot_use: |
      `counter_dispatched` after high-Notoriety workings. Drives
      The Wielding-and-discover-it's-gone subplot.

  - id: smith_who_made_it
    label: The Maker
    description: |
      Knows the item intimately — its weaknesses, its true name,
      its breaking-point. May want it back, may want it destroyed,
      may want to see who finally outwields it.
    plot_use: |
      `counter_dispatched` for high-tier items. Sometimes ally
      (advises on care), sometimes antagonist (the relic was not
      meant for you).

  - id: former_owner
    label: The Former Owner
    description: |
      Previous wielder of the item — alive (the dispossessed
      heir, the grieving widow) or dead (the ghost, the
      ancestral memory). Wants the item back, by force or by
      shame.
    plot_use: |
      Usually `enemy_made` if alive; `bond_broken` or
      `secret_known` events if dead-but-haunting.

  - id: banehand
    label: The Banehand
    description: |
      Anti-item specialist. The iron-charm-maker, the dispeller,
      the breaker-of-named-things. Expensive to hire and rare —
      knows how to unmake what makers made.
    plot_use: |
      `counter_dispatched` against high-tier items. The Banehand
      is to Item Legacy what the Severer is to Bargained-For.

# ─────────────────────────────────────────────────────────────────────
# LEDGER BARS — what this plugin contributes to the visible ledger
# ─────────────────────────────────────────────────────────────────────
ledger_bars:
  - id: bond
    label: "Bond"
    color: bronze
    scope: item                  # tracked per item
    range: [-1.0, 1.0]           # BIDIRECTIONAL — different from Soul/Debt
    threshold_high: 0.5
    threshold_higher: 0.8
    threshold_low: 0.0
    threshold_lower: -0.3
    consequence_on_high_cross: |
      `item_bond` output emitted: the item begins to recognize
      the wielder. New abilities surface. Narrator describes the
      item's small responses (settling in the holster, starting
      on the first crank).
    consequence_on_higher_cross: |
      `pact_tier` output emitted on the item itself: the item is
      DEEPLY bonded — it answers thoughts, fires when expected,
      may even resist being lost.
    consequence_on_low_cross: |
      Item enters strained state. Reliability drops. Narrator
      describes resistance — the gun's draw is heavier, the car
      coughs at ignition, the letter is harder to read.
    consequence_on_lower_cross: |
      `item_unbond` output emitted: the item REFUSES. Will not
      fire. Will not start. Will not open. The wielder must
      Reckon, Renounce, or attempt re-bonding through the
      Wielding confrontation.
    decay_per_session: 0.0       # Decision #3 — bond is sticky between sessions
    starts_at_chargen: 0.3       # if item is acquired at chargen, default friendly

  - id: notoriety
    label: "Notoriety"
    color: copper
    scope: world                 # the WORLD knows you have the item
    range: [0.0, 1.0]            # monotonic — only rises
    threshold: 0.3
    threshold_higher: 0.7
    consequence_on_threshold_cross: |
      `reputation_tier` output emitted: the wielder is now known
      as the carrier. NPCs reference. Counter NPCs (Thief,
      Banehand, Rival Wielder) become eligible for dispatch.
    consequence_on_higher_cross: |
      The wielder is legendary. NPCs from across the campaign
      world are aware. Faction interest shifts. The item becomes
      a marker of identity that cannot be removed by simply
      hiding the item.
    decay_per_session: 0.0       # Decision #3 — fame doesn't fade between sessions
    starts_at_chargen: 0.0       # nobody knows yet

# ─────────────────────────────────────────────────────────────────────
# OTEL SPAN SHAPE
# ─────────────────────────────────────────────────────────────────────
otel_span:
  span_name: magic.working
  required_attributes:
    - working_id
    - plugin                     # always: item_legacy_v1
    - source                     # always: item_based
    - declared_effect
    - domains
    - modes                      # typically: item_channeled
    - debited_costs              # at minimum: { bond: <delta> } — can be ±
    - mechanism_engaged          # only on acquisition workings; null on use
    - item_id                    # ALWAYS — the named item being engaged
    - item_subtype               # weapon | scroll | relic | vessel | vehicle | ...
    - item_disposition_at_event
    - reliability_roll
    - world_knowledge_at_event
    - visibility_at_event
  optional_attributes:
    - witnesses_present          # feeds Notoriety rise + counter dispatch eligibility
    - confrontation_id
    - confrontation_branch
    - alignment_with_item_nature # boolean — was this use IN LINE with what
                                 # the item wants? Drives bond direction.
  on_violation: gm_panel_red_flag
  yellow_flag_conditions:
    - "narration claims an item-magic effect but no span fires"
    - "item_id absent (narrator hasn't named which item)"
    - "alignment_with_item_nature is absent (narrator hasn't decided if
       this use was in service of or against the item's nature)"
  red_flag_conditions:
    - "debited_costs has no `bond` field (item magic always touches bond)"
    - "item_id references an item not in the world's instantiated set"
    - "mechanism_engaged set on a non-acquisition working"
  deep_red_flag_conditions:
    - "the item is used in a way explicitly forbidden by its nature
       (a sword named for revenge used to forgive — the item's preferences
       are hard limits)"
    - "the working violates a hard_limit (item as resurrection, etc.)"

# ─────────────────────────────────────────────────────────────────────
# HARD LIMITS specific to item_legacy
# ─────────────────────────────────────────────────────────────────────
hard_limits:
  inherits_from_genre: true
  additional_forbidden:
    - id: item_as_resurrection
      description: |
        Items are not bargaining chips for the dead. The genre-level
        resurrection forbidden is amplified for this plugin
        specifically — items can extend lifespan, prevent dying,
        even bring back the freshly-fallen-but-not-yet-cold (genre
        permitting), but cannot return the dead.
    - id: against_the_item_nature
      description: |
        An item's preferences are HARD limits. A sword named for
        revenge cannot be used to forgive. A vehicle named for the
        run cannot be parked. The cursed letter named for ruin
        cannot be used to reconcile. Attempting violates the item
        and forces immediate `item_unbond` regardless of bond level.
    - id: perfect_replication
      description: |
        Each named item is singular. Cannot be perfectly replicated,
        forged, or mass-produced. A copy that LOOKS identical does
        not have the personality, the bond, or the history. World
        may permit "the lost twin of the named blade" as a
        narrative beat but the items are distinct entities.
    - id: forced_wield_below_threshold
      description: |
        An unbonded item (bond < threshold_lower) cannot be forced
        to fire. Pleading, drawing, threatening, declaring — all
        fail. The wielder must Reckon or re-bond first.

# ─────────────────────────────────────────────────────────────────────
# NARRATOR REGISTER — prose voice when this plugin fires
# ─────────────────────────────────────────────────────────────────────
narrator_register: |
  The item is a character. Describe its mood, its weight, its
  preferences, its history. When it is used well, narrate its
  satisfaction — the gun settles in the hand, the engine catches on
  the first crank, the letter unfolds smoothly. When used badly,
  narrate its resistance — the draw is heavy, the engine coughs,
  the parchment fights the seal.

  Items have voices, but the voice is implicit register, not
  literal speech. Stormbringer does not say "I am thirsty"; it
  pulls toward bared throats. The Pursuit Special does not say
  "drive me harder"; the engine purrs at high speed and rattles
  at low. Sentient items (worlds may declare some) speak only
  when the world's tuple permits.

  Each named item has OCEAN scores and a personality the narrator
  must hold consistently across all uses. The named gun that is
  high-conscientiousness, low-agreeableness fires precisely but
  with disdain — the narrator stays in that register for every
  encounter with the gun across sessions. The vehicle that is
  high-extraversion, low-neuroticism is exuberant and steady;
  describe its character in each engagement.

  Use of the item against its nature is felt as transgression.
  When a wielder forces an item to act against what it is, the
  narrator surfaces the item's protest — physical, social, or
  narrative — as warning. The hard_limit on against_the_item_nature
  fires after warning is ignored.

  Notoriety is felt as the world recognizing. NPCs who reference
  the item by name signal that Notoriety has crossed threshold.
  The narrator names the item before the wielder when introducing
  them at high Notoriety: "the Lassiter and its bearer entered
  the saloon" rather than "Mal walked in carrying the Lassiter."

# ─────────────────────────────────────────────────────────────────────
# ITEM SHAPE — what each named item carries
# Worlds instantiate this shape per named item.
# ─────────────────────────────────────────────────────────────────────
item_npc_shape:
  required:
    - id                         # canonical identifier
    - name                       # display name (e.g. "The Lassiter")
    - subtype                    # weapon | scroll | relic | vessel | vehicle |
                                 # tome | letter | jewelry | tool | structure
    - ocean
    - disposition_default
    - nature                     # the item's central preference / drive
                                 # (e.g. "thirsts for kin-blood",
                                 #  "wants to be driven hard",
                                 #  "wants to be read aloud")
    - history                    # short prose — where it came from
  optional:
    - sentience                  # implicit | explicit (world declares)
    - bonded_to                  # set in play
    - demands                    # list — what triggers The Reckoning
    - prohibitions               # list — uses that immediately drop bond
    - resonances                 # list — uses that immediately raise bond
    - hidden_history             # known only at higher bond tiers

  example_instantiation: |
    items:
      - id: stormbringer
        name: "Stormbringer"
        subtype: weapon
        ocean: { o: 0.7, c: 0.4, e: 0.85, a: 0.05, n: 0.7 }
        disposition_default: -10
        nature: "thirsts for blood, especially of kin"
        history: |
          Forged in the elder days; one of two sibling blades.
          Has fed and consumed every wielder it has known.
        demands:
          - "must drink within three days of last drinking"
          - "the wielder must offer a piece of self every hundred kills"
        prohibitions:
          - "cannot be sheathed mid-combat without a feeding"
          - "cannot be wielded against its sister-blade"
        resonances:
          - "wielded against the strong is satisfying"
          - "drinking blood of the kingdom's lineage deepens bond"
        sentience: implicit       # has personality, doesn't speak

# ─────────────────────────────────────────────────────────────────────
# CONFRONTATIONS
# ─────────────────────────────────────────────────────────────────────
confrontations:

  # ──────────────────────────────────────────────────────────────
  - id: the_finding
    label: "The Finding"
    description: |
      Acquiring a named item — discovery, gift, faction-grant,
      condition-met, or place-claim. Stakes: do you walk away
      with it, and on what terms?
    when_triggered: |
      Player declares intent to claim a known item, OR narrator
      surfaces a discovery moment (the dead man's hand, the dust-
      covered crate, the dying mentor's gift).
    resource_pool:
      primary: bond              # the starting bond level is what's negotiated
      secondary: vitality        # cost of the finding itself (the trial, the journey)
    stakes:
      declared_at_start: true    # the item's nature is at least partially known
      hidden_dimensions: true    # the full history may remain hidden
    valid_moves:
      - claim_directly
      - negotiate_terms          # if relational mechanism
      - meet_the_condition       # if condition mechanism
      - take_by_force            # always available, raises bond risk
      - swear_to_the_item        # ceremonial; raises starting bond
      - walk_away
    outcomes:
      - branch: clear_win
        description: "You found it cleanly; it accepted you."
        narrative_shape: |
          The item is yours, the bond starts positive, and the
          history flows in the moment of acquisition — a memory,
          a name, a feeling of who held it before.
        mandatory_outputs:
          - type: item_bond
            description: "New bond established with named item"
          - type: ledger_bar_set
            bar: bond
            level: 0.3
        optional_outputs:
          - type: ally_named
            description: "Whoever helped you find it becomes an ally"
          - type: secret_known
            description: "The item's history reveals one piece"

      - branch: pyrrhic_win
        description: "You found it but at cost beyond what you knew."
        mandatory_outputs:
          - type: item_bond
            description: "New bond, but starting suspicious"
          - type: ledger_bar_set
            bar: bond
            level: 0.0
          - type: scar
            severity: major
            description: "The finding marked you — physical or psychic"
        optional_outputs:
          - type: counter_dispatched
            target: banehand
            description: "An anti-item agent noticed the surge"
          - type: bond_broken
            description: "Someone you cared about died or turned in the finding"

      - branch: clear_loss
        description: "You didn't find it, OR found it and it rejected you."
        mandatory_outputs:
          - type: scar
            severity: psychic
            description: "The shame of being refused, or the loss of the search"
          - type: bond_broken
            description: "Whoever helped you is now estranged"
        optional_outputs:
          - type: enemy_made
            target: rival_wielder
            description: "Someone else found it first"
          - type: mechanism_revoked
            description: "This delivery path is closed to you"

      - branch: refused
        description: "You walked away from a known item."
        mandatory_outputs:
          - type: scar
            severity: minor
            axis: pride
            description: "A felt mark of choice — virtue or doubt"
        optional_outputs:
          - type: bond
            description: "A bond with whoever supported your walking away"

  # ──────────────────────────────────────────────────────────────
  - id: the_wielding
    label: "The Wielding"
    description: |
      Using the item in a confrontation. Bond rises if the use
      aligned with the item's nature; falls if the use was against
      it, casual, or dishonorable. Notoriety always rises with use.
    when_triggered: |
      Player declares use of a named item during any confrontation
      (combat, chase, séance, etc.). The Wielding piggybacks on
      the host confrontation but emits its own outcome span.
    resource_pool:
      primary: bond
      secondary: notoriety
    stakes:
      declared_at_start: false   # bond direction depends on use-alignment
      hidden_dimensions: true    # the item may surprise you
    valid_moves:
      - use_in_alignment         # use the item in service of its nature
      - use_for_purpose          # use the item for the wielder's purpose
                                 # (alignment unclear; depends on item)
      - use_carelessly           # casual use; bond falls
      - hold_back                # do not draw / do not start
      - wield_for_show           # display without firing; minor notoriety
    outcomes:
      - branch: clear_win
        description: "You used the item well; it answered. Bond rises."
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: bond
            delta: 0.10
          - type: ledger_bar_rise
            bar: notoriety
            delta: 0.05
        optional_outputs:
          - type: affinity_tier
            description: "Tick toward affinity tier-up if applicable"
          - type: scar
            severity: minor
            description: "A small visible mark of the wielding — pact-stigma equivalent"

      - branch: pyrrhic_win
        description: "You got the result but paid in bond."
        narrative_shape: |
          The wielder forced the item into a use it didn't share.
          The desired effect happened, but the item is now wary,
          slower to answer, suspicious of the next call.
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: bond
            delta: -0.15
          - type: ledger_bar_rise
            bar: notoriety
            delta: 0.10
        optional_outputs:
          - type: scar
            severity: major
            description: "The item visibly resisted; people saw"
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.05
            description: "You used it for a purpose it didn't share"

      - branch: clear_loss
        description: "The item refused to fire, OR fired wrong."
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: bond
            delta: -0.20
          - type: reputation_tier
            description: "People saw you fumble; your reputation shifts"
        optional_outputs:
          - type: counter_dispatched
            target: thief
            description: "Someone realized you can't fully control it"
          - type: bond_broken
            description: "Allies who depended on the item are now distant"

      - branch: refused
        description: "You held the item but didn't use it."
        narrative_shape: |
          Restraint. The wielder had the option to draw, drive,
          read aloud, invoke — and chose not to. The item, if it
          has any patience, respects this.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: bond
            delta: 0.05
            description: "The item respects restraint (slight)"
          - type: vitality_cost
            delta: 0.15
            description: "The situation cost you because you didn't draw"
        optional_outputs:
          - type: bond
            description: "A bond with whoever you protected by holding back"

  # ──────────────────────────────────────────────────────────────
  - id: the_reckoning
    label: "The Reckoning"
    description: |
      The item demands. Stormbringer wants blood. The cursed letter
      wants to be read aloud. The Pursuit Special wants the run.
      The wielder must answer — feed it, deny it, or negotiate. This
      is the item-equivalent of bargained_for_v1's The Calling.
    when_triggered: |
      Bond bar at threshold_high or higher AND a triggering condition
      from the item's `demands` is met (e.g. three days since
      Stormbringer drank), OR narrator-triggered at pivotal moments
      (the item has waited long enough).
    resource_pool:
      primary: bond
      secondary: identity
    stakes:
      declared_at_start: true    # the item's demand is named
      hidden_dimensions: true    # the deeper cost may not be visible
    valid_moves:
      - feed_the_item
      - feed_in_alignment        # find a target the item also wants
      - negotiate_terms          # offer a substitute
      - delay                    # buy time at higher cost
      - refuse                   # open break with the item
    outcomes:
      - branch: clear_win
        description: "You fed it what it wanted, on terms you can live with."
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: bond
            delta: 0.30
          - type: pact_tier
            target_kind: item
            delta: +1
            description: "Item bond deepens to a new tier — new abilities surface"
        optional_outputs:
          - type: mechanism_unlocked
            description: "Deeper item history revealed; new abilities"
          - type: secret_known
            description: "The item shares part of its hidden history"

      - branch: pyrrhic_win
        description: "You fed it, but paid more than expected."
        mandatory_outputs:
          - type: bond_broken
            description: "A non-item NPC bond is severed (they paid the price)"
          - type: scar
            severity: defining
            description: "The wielder is visibly changed"
          - type: ledger_bar_rise
            bar: bond
            delta: 0.15
        optional_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: -0.10
          - type: counter_dispatched
            target: rival_wielder
            description: "Someone has seen you cross a line"

      - branch: clear_loss
        description: "You couldn't feed it, OR refused to deliver mid-attempt."
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: bond
            delta: -0.50
            description: "Bond collapses"
          - type: scar
            severity: defining
        optional_outputs:
          - type: item_unbond
            description: |
              If bond falls below threshold_lower, the item rejects
              the wielder for the remainder of the session
          - type: counter_dispatched
            target: thief
            description: "The item's vulnerability is now known"

      - branch: refused
        description: "You said no openly to the item."
        narrative_shape: |
          The most dramatic branch. The wielder has chosen not to
          feed the demand. The item registers the refusal and the
          wielding-relationship enters crisis.
        mandatory_outputs:
          - type: item_unbond
            description: "The item rejects the wielder; will not fire next time"
          - type: scar
            severity: major
            axis: reputation
            description: "The wielder is now the one who refused the named item"
        optional_outputs:
          - type: bond
            description: "A bond with whoever stood with you when you refused"
          - type: counter_dispatched
            target: rival_wielder
            description: |
              Word travels; another wielder may try to claim the
              item by force, knowing the bond is broken

  # ──────────────────────────────────────────────────────────────
  - id: the_renunciation
    label: "The Renunciation"
    description: |
      Setting the item down forever. Different from The Severance
      in bargained_for_v1 — items can be set down (the contract is
      with you, not with both parties). But setting down a deeply
      bonded item is its own crisis. Stormbringer cannot be put
      down; that's the genre's central tragedy. Other items can.
    when_triggered: |
      Player declares intent to set the item down permanently.
      May be initiated proactively (after The Reckoning's `refused`
      branch) or in response to narrative pressure.
    resource_pool:
      primary: bond
      secondary: identity
    stakes:
      declared_at_start: true
      hidden_dimensions: false   # everyone knows what's at stake
    valid_moves:
      - set_down_in_a_named_place      # ceremonial; bond bar handles cleanly
      - destroy_the_item                # extreme; usually triggers Banehand
      - pass_it_to_another              # transfer to a new wielder
      - hide_it_from_self               # fail-safe — locked cabinet, buried
      - leave_it_where_it_lies          # casual; lowest ceremony
    outcomes:
      - branch: clear_win
        description: "You set it down; both parties accept the parting."
        mandatory_outputs:
          - type: item_unbond
            description: "Bond is severed cleanly"
          - type: reputation_tier
            description: "You became the one who put it down"
        optional_outputs:
          - type: bond
            description: "A bond with whoever supported your choice"
          - type: pact_tier
            target_plugin: another_plugin
            description: |
              A new path opens — a McCoy invention, an Innate
              awakening, a Bargained-For pact. Item-power lost;
              other path gained.

      - branch: pyrrhic_win
        description: "You set it down but it cost you."
        mandatory_outputs:
          - type: item_unbond
          - type: scar
            severity: defining
          - type: bond_broken
            description: "Someone who depended on the item's power is now without it"
        optional_outputs:
          - type: counter_dispatched
            target: rival_wielder
            description: "Someone who wanted the item to stay in your hands"
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.05
            description: "The renunciation made you steadier"

      - branch: clear_loss
        description: "You tried to set it down and couldn't / it wouldn't let you."
        narrative_shape: |
          The bonded item refuses to be released. Stormbringer-shape:
          the wielder cannot escape the carrying. The attempt at
          renunciation deepens the bond involuntarily.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: bond
            delta: 0.30
            description: "Bond deepens involuntarily"
          - type: scar
            severity: defining
        optional_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: -0.15
            description: "The wielder is being consumed by the carrying"

      - branch: refused
        description: "You backed out of the renunciation at the last moment."
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: bond
            delta: -0.10
            description: "The item knows you tried"
          - type: scar
            severity: minor
            axis: pride
        optional_outputs:
          - type: pact_tier
            target_kind: item
            delta: +1
            description: |
              Forced — the item now demands more, having seen the
              wielder's weakness

# ─────────────────────────────────────────────────────────────────────
# REVEAL — confrontation outcome callouts (Decision #2)
# ─────────────────────────────────────────────────────────────────────
reveal:
  mode: explicit
  timing: at_outcome
  format: panel_callout
  suppression: none
  per_branch_iconography:
    clear_win: 🌟
    pyrrhic_win: ⚖
    clear_loss: 💔
    refused: 🔒

# ─────────────────────────────────────────────────────────────────────
# WORLDBUILDING SLOT — what worlds must instantiate
# ─────────────────────────────────────────────────────────────────────
world_layer_required:
  - At least one named item per active mechanism
    description: |
      A discovery-mechanism world declares the named items
      findable in the world (the Lassiter on the dead courier;
      Stormbringer in the burial mound). A relational-mechanism
      world declares the giving relationships and the inherited
      items. A faction-mechanism world declares which factions
      issue or hold named items.
  - Each item's full NPC shape (see item_npc_shape above)
    description: |
      Worlds cannot use this plugin with un-personalitied items.
      Each named item must have OCEAN, disposition, nature,
      history at minimum.
  - Item subtypes the world admits
    description: |
      Some worlds admit only weapons (spaghetti_western), some
      vessels (road_warrior), some letters/tomes (victoria,
      pulp_noir). The world declares which subtypes are
      narratively coherent.
  - Sentience policy
    description: |
      Worlds declare whether implicit-only or explicit-allowed.
      Most worlds default to implicit; a few (high-magic
      heavy_metal, weird-pulp) admit literal-speaking items.
```

## Validation Notes

### What this plugin tests against the framework

- ✅ All schema slots populated (8 of 8)
- ✅ Multiple delivery mechanisms (5 of 8 supported, 3 explicitly excluded)
- ✅ Class/archetype mapping (5 classes — more than bargained_for_v1's 4, validates that plugin spec scales)
- ✅ Counter archetypes (5)
- ✅ **Bidirectional ledger bar (Bond)** — first plugin to use this pattern; validates that the schema supports both monotonic (Soul/Debt, Notoriety) and bidirectional (Bond) bars
- ✅ OTEL span shape with item-specific attributes (item_id, item_subtype, alignment_with_item_nature)
- ✅ Hard limits beyond genre baseline (4)
- ✅ Narrator register specifying the item-as-character voice and the implicit-vs-explicit sentience distinction
- ✅ **Item NPC shape** — formalizes "items as NPCs with OCEAN" decision into queryable schema
- ✅ Confrontations (4 confrontation types, each with full 4-branch outcome trees)
- ✅ Mandatory output on every branch (Decision #1)
- ✅ Failure-advances on clear_loss and refused branches (Decision #4)
- ✅ Player-facing reveal (Decision #2)
- ✅ No-decay (Decision #3)
- ✅ Plugin tie-in to confrontations (Decision #5)

### Patterns this surfaces for the framework

1. **Bidirectional ledger bars are a real pattern.** Bond moves both directions. The Notoriety bar is monotonic (only rises). Plugins should explicitly declare bar `range:` and `direction:` characteristics. The framework should formally support both monotonic and bidirectional bars.

2. **`ledger_bar_set` as an output type** — distinct from `ledger_bar_rise` and `ledger_bar_fall`. Used in The Finding's outcomes to *initialize* the bond bar at a specific level. Different from a delta. Add to the output catalog.

3. **`ledger_bar_fall` as an output type** — already implied but should be made explicit. Item Legacy is the first plugin where falls are common, not exceptional.

4. **`vitality_cost` as a non-bar output type** — used in The Wielding's `refused` branch (the situation hurt because you didn't draw). This is a one-time cost that's not the same as a ledger bar rising. Add to catalog.

5. **`alignment_with_item_nature` is a plugin-specific OTEL attribute** that doesn't fit the universal schema. The OTEL span schema needs to support plugin-extended attributes — already implied but worth formalizing.

6. **The `target_kind: item` extension on `pact_tier`** — pact_tier originally implied character-bound. Items can also have tiers (a deeply-bonded item gains abilities). Schema should support `target_kind: item | character | faction | bond_pair`.

7. **Cross-plugin output (`pact_tier` with `target_plugin: another_plugin`)** — used in The Renunciation's clear_win, where setting down an item opens a new path in a *different* plugin. The framework needs to support cross-plugin advancement events. Add to catalog.

8. **Items as carriers for cross-genre passport** *(party-mode wild-card #12)* — this plugin's item_npc_shape is exactly what would travel between genres. A named item from spaghetti_western (the Lassiter) carried into space_opera retains its OCEAN, disposition, and history. The plugin makes this technically possible; the question is whether to enable it.

## Notable distinctness from bargained_for_v1

| Dimension | bargained_for_v1 | item_legacy_v1 |
|---|---|---|
| **Carrier** | Sentient patron with full agency | Bounded item with personality |
| **Cost direction** | Soul/Debt monotonic up | Bond bidirectional |
| **Severance** | Catastrophic — pact binds both parties | Renunciation — usually possible cleanly |
| **Acquisition** | Negotiation with patron | Discovery / inheritance / faction-grant |
| **Counters** | Severer (cuts chains) | Banehand (unmakes objects) |
| **Hard-limit signature** | No bargaining for what already happened | No use against the item's nature |
| **Plot arc** | Pact → Working → Calling → Severance | Finding → Wielding → Reckoning → Renunciation |

**Both plugins fit the same framework**, but they feel completely different in play. Validates that the plugin model captures genuine distinction without forcing them into one shape.

## Next Concrete Moves

- [ ] Architect: review the bidirectional ledger pattern, the output catalog additions (`ledger_bar_set`, `ledger_bar_fall`, `vitality_cost`, cross-plugin `target_plugin`), and the `target_kind: item` extension to `pact_tier`. These are framework-touching changes that should be ratified before more plugins draft.
- [ ] UX (Buttercup): named-item display — does the panel show the item's OCEAN? Its current bond bar? Its disposition toward the wielder? Sketch.
- [ ] GM: instantiate The Lassiter in a Firefly-world `magic.yaml` as the first concrete worked example of a `world_layer_required` instantiation.
- [ ] GM: draft `divine_v1` as the third plugin — the institutional feeding-economy register, contrasts with both bargained_for and item_legacy.
- [ ] Open question: should the cross-genre item passport (party-mode wild-card #12) be a real feature? Item Legacy makes it technically possible. Worth a design conversation.
