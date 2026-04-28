# Plugin: obligation_scales_v1

**Status:** Draft, 2026-04-28
**Plugin Type:** **Multi-plugin layer (cross-cutting, horizontal)** — NOT a Source-shaped plugin. Does not implement a napkin Source. Tracks how every working performed by ANY active magic plugin debits five world-shared scales of obligation.
**Genres using:** heavy_metal (signature — and for now, only). The five-scale tracker is heavy_metal's unique cosmological feature; other genres do not host it. Future expansion possible if another genre proves to need cross-cutting obligation propagation.
**Companion docs:** `../magic-taxonomy.md`, `../visible-ledger-and-otel.md`, `../confrontation-advancement.md`, `README.md` (this dir), `bargained_for_v1.md`, `divine_v1.md`, `learned_v1.md`, `innate_v1.md`, `item_legacy_v1.md` (all monitored)

## Identity

The five obligation scales are heavy_metal's load-bearing cosmological claim: **every act of magic propagates obligation at five distinct scopes**, and **the caster does not always know which scopes their working has billed.** The narrator's job is to render this uncertainty as drama; the panel's job is to surface what the dice and the bookkeeping have actually decided.

Three things distinguish this plugin from every Source plugin in the framework:

1. **It has no Source.** This plugin does not deliver magic to characters — the five Source plugins (`bargained_for_v1`, `divine_v1`, `learned_v1`, `innate_v1`, `item_legacy_v1`) do that. This plugin watches the OTEL span those plugins emit and updates five world-shared bars accordingly. It is *infrastructure that runs alongside*, not a shape a character takes.
2. **It has no classes.** A character does not "play" obligation_scales. They play a Warlock or a Cleric or a Witcher (whose magic is hosted by some Source plugin), and obligation_scales tracks their workings' propagation. The five scales are bookkeeping; the character is somewhere else.
3. **Bills can land on populations the character has never met.** The covenant scale fills as the character's bloodline gets billed for what the character has done; the stratigraphic scale fills as ancient pacts wake to the character's working; the communal scale fills as the character's hometown begins paying for the character's choices in distant cities. The character is a node; the scales are the network.

The plot engine is **dramatic uncertainty about consequence-target**: not whether you will pay, but who else will. *You called on the patron in the burned tower. The bill is going somewhere. Six villages south, a child your sister never had has just been marked. You will not learn this for a year. By then, two of those villages will be gone.*

## Plugin Definition

```yaml
plugin: obligation_scales_v1
status: draft
plugin_type: cross_cutting_multi_plugin   # NOT source_shaped
genres_using:
  - heavy_metal           # signature — the only genre hosting this
                          # cosmology at present

# This plugin has NO `source:` field. It does not implement a napkin
# Source. It is infrastructure that runs alongside the five Source
# plugins active in heavy_metal worlds.

# This plugin has NO `delivery_mechanisms:` field. It does not deliver
# magic. Its scope is bookkeeping.

# This plugin has NO `classes:` field. Characters take classes from
# the Source plugins (Warlock from bargained_for_v1, Cleric from
# divine_v1, etc.); obligation_scales tracks their workings.

# ─────────────────────────────────────────────────────────────────────
# MONITORED PLUGINS — which active magic plugins this tracker watches
# ─────────────────────────────────────────────────────────────────────
# The plugin requires OTEL span events from each of these. Without
# the source plugin's span, the scales cannot be updated — there is
# nothing to track. A heavy_metal world that activates this plugin
# MUST also activate at least one of the monitored plugins.
monitored_plugins:
  - id: bargained_for_v1
    primary_scales: [individual, communal, covenant]
    description: |
      Bargained-For workings primarily debit the individual scale
      (the pact-bearer's own bill) and frequently the communal
      scale (the patron's territory, the witnessing faction).
      Pacts inherited via bloodline (Crossroads-Walker class with
      inherited variant) also debit covenant.

  - id: divine_v1
    primary_scales: [divine, communal, covenant]
    description: |
      Divine workings always debit the divine scale (the worshipped
      god's hunger). Workings performed via apparatus (faction
      mechanism) also debit communal (the church's standing-with-the-
      god ripples through the local clergy and laity). Workings
      performed by inherited divine roles (saint-line, hierophantic
      lineage) also debit covenant.

  - id: learned_v1
    primary_scales: [communal, individual]
    description: |
      Learned workings always debit communal at minimum — knowledge
      is shared debt; the school's lineage carries the weight. The
      character's individual scale also rises (their personal
      practice's bill). Learned workings rarely debit covenant or
      divine unless the tradition itself is faith-bound (heavy_metal
      Cleric's liturgical Learned component).

  - id: innate_v1
    primary_scales: [covenant, individual]
    description: |
      Heavy_metal Innate is debt-assumed-without-consent: covenant-
      peoples (born_with) carry biology-as-contract; stratigraphic-
      touched (acquired_via_event) carry exposure-as-contract.
      Both primarily debit covenant scale. The character's
      individual scale rises as well. *(Note: heavy_metal-specific
      reading of innate_v1 — most other genres' innate workings
      do NOT debit covenant; that's heavy_metal's unique inflection.)*

  - id: item_legacy_v1
    primary_scales: [individual, stratigraphic]
    description: |
      Item-Legacy workings debit individual (the wielder's bond
      ledger). Items predating the current civilization
      (stratigraphic artifacts — relics from the un-closed pacts
      of older epochs) ALSO debit stratigraphic scale. Most modern
      items do not; ancient items always do.

# Worlds activate this plugin alongside any combination of the five
# monitored plugins. Activation is in the world's magic.yaml; the
# plugin instantiates its five bars and registers as the OTEL span
# consumer for magic.working events emitted by monitored plugins.

# ─────────────────────────────────────────────────────────────────────
# THE FIVE SCALES — ledger bars
# ─────────────────────────────────────────────────────────────────────
# Each scale is a world-shared bar (parallel to divine_v1's Hunger
# and innate_v1's Signal patterns). Bars rise based on workings
# debited by monitored plugins; thresholds trigger confrontations
# at the appropriate scope.
ledger_bars:

  - id: individual_scale
    label: "Individual Pact"
    color: ember
    scope: character           # one bar per pact-bearing character
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 1.0
    consequence_on_high_cross: |
      The individual bill comes due. The character's own account-
      holder (patron, deity, inherited contract) collects.
      Triggers the relevant Source plugin's collection-confrontation:
      bargained_for_v1's The Calling, divine_v1's The Audit,
      innate_v1's The Reckoning at the individual register, etc.
      This bar's threshold-crossing is NOT itself a confrontation
      — it is a delegated trigger to the appropriate Source plugin.
    decay_per_session: 0.0     # Decision #3 — character's own ledger
                               # does not decay (parallel to bargained_for_v1's
                               # soul_debt rule)
    starts_at_chargen: 0.05    # mirrors bargained_for_v1.soul_debt — the
                               # chargen pact itself costs a sliver
    note: |
      Mechanical note: this bar may already be tracked by an
      individual Source plugin under a different name (bargained_for_v1
      tracks soul_debt; divine_v1 tracks individual standing). When
      multiple Source plugins are active for one character, the
      `individual_scale` bar serves as the UNION view — the
      character's total individual obligation across all active
      Sources. Implementation note: the panel may render either the
      union or the per-Source breakdown; default render is the union
      with per-Source drill-down on click.

  - id: communal_scale
    label: "Communal Debt"
    color: bone
    scope: location_or_faction  # one bar per witnessing community
                                # (a village, a guild quarter, a religious
                                # parish, etc.)
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.6
    threshold_higher: 1.0
    consequence_on_high_cross: |
      Mid-tier communal pressure. The community begins to feel the
      weight — small bad-luck events, harvest failures, weddings
      that don't bear children, water wells running murky. The
      effects are diffuse and easily attributed to mundane causes.
      Locals don't yet know they're paying for someone's working.
    consequence_on_higher_cross: |
      The community formally pays. Triggers The Account Comes Due
      confrontation at communal scope. The narrator chooses the
      tangible consequence: a structure collapses, a child is born
      cursed, a faction-leader dies, the harvest fails completely,
      the wedding-day ends in violence. The community now knows
      something is wrong with the place.
    decay_per_session: 0.03    # very slow — communities forget over
                               # generations, not sessions
    starts_at_chargen: 0.0     # the chargen character's home community
                               # does not begin in debt unless backstory
                               # specifies; world may set per-location
                               # baselines
    instantiation: |
      One bar per named community in the world. Workings performed
      WITHIN a community (witnesses present, location is the
      community's territory) debit that community's bar. Workings
      performed OUTSIDE a community but TARGETING the community
      (a curse cast at a distant village) ALSO debit that community's
      bar — the bill follows the target, not the casting location.
      *(Cliché-judge hook: a working with no clear communal
      witnesses or target should NOT debit any communal bar. If
      the narrator is debiting communal scale on a working with no
      community involvement, flag YELLOW.)*

  - id: covenant_scale
    label: "Covenant Mark"
    color: blood_iron
    scope: bloodline           # one bar per covenant-people / bloodline
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.5
    threshold_higher: 1.0
    consequence_on_high_cross: |
      The bloodline's covenant deepens. New family members born
      into the lineage manifest stronger marks; existing
      family members' marks ache. The covenant-people's biological
      contract is now visibly more active — their identifying
      mutations grow more pronounced, their inherited prophecies
      come more often, their generational obligations land
      heavier. Affects ALL members of the bloodline, not just the
      acting character.
    consequence_on_higher_cross: |
      The covenant-people pay. Triggers The Account Comes Due at
      covenant scope. Multiple bloodline-members may be killed,
      transformed, claimed, or revealed-as-marked simultaneously
      across the world. The covenant's identifying feature
      (the mark, the trait, the curse) becomes catastrophic — what
      was ache becomes incapacity, what was prophecy becomes
      possession. *Generations after the working may continue to
      pay for the threshold-crossing.*
    decay_per_session: 0.005   # nearly never — covenants forget across
                               # millennia, not generations
    starts_at_chargen: 0.10    # covenant-people characters chargen with
                               # a baseline; the bloodline carries
                               # accumulated debt from prior generations
    instantiation: |
      One bar per named covenant-people or bloodline in the world.
      A character is associated with at most a small number of
      bloodlines (genetic and adopted-in). Workings performed by a
      covenant-people character debit their bloodline's scale by
      default. Inherited Bargained-For pacts (Crossroads-Walker
      class, grandmother's-fae register) ALSO debit the bloodline.
      Divine workings performed by inherited divine roles
      (saint-line) debit the saint-line's bloodline.
      *(Cliché-judge hook: a working performed by a non-covenant
      character should NOT debit covenant scale unless explicit
      bloodline backstory ties them in. Flag YELLOW if narrator
      debits covenant for an unmarked character.)*

  - id: divine_scale
    label: "Divine Hunger"
    color: gold_dim
    scope: deity               # one bar per worshipped god in the world
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.7
    threshold_higher: 1.0
    consequence_on_high_cross: |
      The god is hungrier. divine_v1's Hunger bar (if active for
      this god — the two bars overlap conceptually) is in fact the
      same bar viewed through divine_v1's lens; obligation_scales_v1
      treats it as one of its five and the bar is shared
      bidirectionally between the plugins. When the bar crosses high
      threshold from EITHER plugin's contributions, the consequence
      fires and both plugins' panels update. The clergy demand more
      offerings. The god's saints suffer specific torments. The
      hierophantic apparatus tightens.
    consequence_on_higher_cross: |
      The god feeds directly. Triggers The Account Comes Due at
      divine scope; in heavy_metal worlds this typically chains into
      divine_v1's The Calling for any character with a divine
      relationship to that god. Mass-effect events possible
      (plagues attributed to the god, miracles that demand
      payment-in-blood, the apparatus formally declares a Holy
      Crisis).
    decay_per_session: 0.02    # gods are patient but not infinite;
                               # background hunger drift
    starts_at_chargen: world_default
    shared_with_plugin: divine_v1.hunger
    note: |
      First case in the framework of a SHARED bar across plugins.
      The mechanical implementation is a single bar with two named
      views; updates from EITHER plugin propagate to the OTHER. The
      panel may render under either name; default rendering depends
      on which plugin's confrontation is currently most-relevant
      (divine_v1 default in religious contexts; obligation_scales_v1
      default in cross-plugin observability views).

  - id: stratigraphic_scale
    label: "Stratigraphic Pressure"
    color: stone_red
    scope: world               # one bar per world (NOT per region —
                               # the bedrock is contiguous)
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.5
    threshold_higher: 0.85
    threshold_apocalyptic: 1.0
    consequence_on_high_cross: |
      The bedrock answers. Stratigraphic resonance phenomena begin:
      ancient ruins emit faint sound at certain hours; pre-civilization
      sites become subtly haunted; characters with stratigraphic-
      touched innate_v1 backgrounds experience surge-amplification
      near such sites. The un-closed pacts of older epochs are
      stirring.
    consequence_on_higher_cross: |
      Triggers The Stratigraphic Resonance confrontation at world
      scope. Affects all characters in the world simultaneously.
      Pre-civilization entities partially manifest; ancient ruins
      become actively hostile or actively recruiting; geological
      features become unstable; characters near affected sites
      experience layered-time phenomena (hearing voices from
      civilizations dead for ages).
    consequence_on_apocalyptic_cross: |
      Triggers The Cascade — full re-emergence of stratigraphic
      forces. Campaign-defining event. The civilization the players
      are part of begins competing with previously-extinct
      civilizations for the world. May be the explicit endgame of
      a heavy_metal campaign. Almost always pyrrhic at best.
    decay_per_session: 0.001   # functionally never — bedrock is
                               # bedrock; obligation here is measured
                               # in centuries
    starts_at_chargen: world_default
    instantiation: |
      One bar per world. Worlds set their own starting baseline —
      The Long Reckoning's bedrock, after twelve centuries of
      stratigraphic accumulation, may chargen the bar at 0.30+.
      Newly-settled worlds (post-cataclysm settlements where the
      players are themselves the civilization) start much lower.
      *(Cliché-judge hook: a working that does not engage with
      ancient artifacts, ancient sites, or stratigraphic-touched
      lineage should NOT debit stratigraphic scale. Flag YELLOW
      if narrator routinely debits stratigraphic without a
      stratigraphic-shaped reason; flag DEEP RED if the bar is
      ever raised by 0.10+ in a single working without explicit
      stratigraphic engagement.)*

# ─────────────────────────────────────────────────────────────────────
# OTEL SPAN INTEGRATION — how this plugin consumes events from others
# ─────────────────────────────────────────────────────────────────────
# This plugin does NOT emit its own magic.working spans. It REQUIRES
# every monitored plugin's magic.working span to include the
# debited_scales attribute. Without that attribute, this plugin has
# nothing to track and the world cannot host this plugin alongside
# the source plugin in question.
otel_span_consumption:
  consumed_span: magic.working          # emitted by Source plugins
  required_attribute_extension: debited_scales
  shape: |
    debited_scales: [
      {scale: <one of: individual|communal|covenant|divine|stratigraphic>,
       delta: <float, typically 0.01–0.30>,
       target: <bar's scope-instance ID — village name, deity name,
                bloodline ID, character ID, or "world" for stratigraphic>,
       attribution_state: <named|partial|hidden>}
    ]
  attribution_states:
    - id: named
      description: |
        The character (and the player, via the panel) sees exactly
        which scale and target was debited. Default for low-stakes
        canonical workings.
    - id: partial
      description: |
        The character sees which scale, but not which specific target
        instance. The panel shows "communal_scale debited 0.10
        (community: ?)". Used when the working's reach is uncertain
        even mechanically. Common register in heavy_metal — most of
        the genre's drama lives here.
    - id: hidden
      description: |
        The character does not see the debit. The panel shows the
        debit on the GM-facing OTEL feed but suppresses it in the
        player-facing panel until consequence fires. Used for the
        deepest registers — stratigraphic debits often hidden;
        long-arc covenant accumulation often hidden until threshold
        approach.
        Resurfaces when consequence triggers.

  fallback_behavior_on_missing_attribute: |
    If a magic.working span fires without `debited_scales`, this
    plugin emits a YELLOW flag on the GM panel ("scale attribution
    missing") and applies a CONSERVATIVE default: 0.05 to the
    individual scale only, marked attribution_state=partial. This
    fallback is a last-ditch graceful degradation — every monitored
    Source plugin SHOULD populate debited_scales explicitly. The
    fallback exists so a span without scale-attribution does not
    crash the bookkeeping, NOT as a sustainable practice.

# ─────────────────────────────────────────────────────────────────────
# CONFRONTATIONS — see ../confrontation-advancement.md for schema
# ─────────────────────────────────────────────────────────────────────
# This plugin contributes confrontations triggered by scale
# threshold-crossings. Most threshold-crossings DELEGATE to the
# appropriate Source plugin's existing confrontation (individual_scale
# crossing → bargained_for_v1's The Calling or divine_v1's The Audit
# or innate_v1's The Reckoning). The confrontations defined HERE are
# the ones with no clean Source-plugin home — the genuinely cross-
# scale events.
confrontations:

  # ──────────────────────────────────────────────────────────────
  - id: the_account_comes_due
    label: "The Account Comes Due"
    description: |
      A communal_scale, covenant_scale, or divine_scale crossing
      threshold_higher (1.0). The bill at that scope is now
      payable. Distinct from individual scope (which delegates to
      the relevant Source plugin's collection confrontation) and
      from stratigraphic scope (which has its own confrontation
      below). This confrontation handles the *community / bloodline /
      god* paying for the workings done in their name.
    when_triggered: |
      communal_scale, covenant_scale, OR divine_scale crosses 1.0.
      Multiple simultaneous crossings may chain confrontations.
      The character may be present (acting in the affected
      community, witnessed by the covenant-people, in the god's
      apparatus) or absent (the bill comes due in their hometown
      while they are far away — the character learns, often by
      letter, weeks later).
    resource_pool:
      primary: <crossing_scale>           # the specific scale that crossed
      secondary: bond                     # the character's bond(s) to
                                          # affected community / bloodline / god
    stakes:
      declared_at_start: true             # the panel makes the scale
                                          # crossing visible
      hidden_dimensions: true             # WHO specifically pays may
                                          # be partially-hidden if the
                                          # scale's accumulated debits
                                          # were largely partial/hidden
                                          # attribution
    valid_moves:
      - witness                           # be present; accept the consequence
      - intervene                         # try to redirect or absorb; high cost
      - flee                              # leave the affected scope before
                                          # consequence lands; works short-term,
                                          # accumulates debt elsewhere
      - confess                           # reveal to the affected community /
                                          # covenant / clergy that you caused this;
                                          # changes the relational dynamics
      - sacrifice_self                    # offer your own ledger to absorb
                                          # the scale-crossing; may discharge
                                          # the scale at catastrophic personal cost
      - bargain_with_responsible_party    # negotiate with the patron / god /
                                          # covenant-elder for partial discharge;
                                          # cross-plugin (re-engages the relevant
                                          # Source plugin's negotiation register)
    outcomes:
      - branch: clear_win
        description: |
          The character handled the arriving consequence well. The
          community / covenant / god is satisfied; the scale
          discharges; the character gains standing through the
          difficult moment.
        narrative_shape: |
          The character was present, took responsibility, accepted
          the cost, paid in something specific and visible. The
          village mourns but holds. The bloodline grieves but
          continues. The god is fed and stands down.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: <crossing_scale>
            level: 0.5
            description: "The arrived consequence is paid; scale falls meaningfully"
          - type: bond
            target_kind: <community|bloodline|patron|deity>
            description: |
              Whichever entity was affected: the character now has a
              concrete bond to it. The community knows them by name;
              the bloodline acknowledges them; the god has noted them
        optional_outputs:
          - type: pact_tier
            target_plugin: <relevant Source plugin>
            delta: +1
            description: "Standing with the responsible party deepens"
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.05
            description: "The character is more accountable afterward"
          - type: reputation_tier
            description: "The character is now legible to the affected scope"

      - branch: pyrrhic_win
        description: |
          The character handled it AND someone else paid most of the
          price — a defining bond was severed because they took the
          weight; a community member died protecting the character
          from the consequence; the god's hunger fell partly upon a
          named NPC who had helped the character previously.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: <crossing_scale>
            level: 0.4
          - type: bond_broken
            description: "A non-character entity paid the price; the bond severs"
          - type: scar
            severity: defining
            axis: psychic_or_social
        optional_outputs:
          - type: counter_dispatched
            target: <Source plugin's relevant counter>
            description: |
              A witness or affected party becomes an active opposing
              force in subsequent sessions
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.05

      - branch: clear_loss
        description: |
          The character was unable to handle the arriving consequence.
          The community / bloodline / god takes catastrophic
          damage; the scale does not discharge cleanly; subsequent
          workings will land on a still-paying scope.
        mandatory_outputs:
          - type: ledger_lock
            bar: <crossing_scale>
            level: 0.85
            description: |
              The scale is locked high — the consequence is ongoing,
              not paid. Future workings to the same scope amplify;
              the affected community / bloodline / god is no longer
              in equilibrium
          - type: bond_broken
            description: "Catastrophic loss in the affected scope — multiple bonds may sever"
          - type: scar
            severity: defining
            axis: existential
          - type: enemy_made
            description: |
              The affected scope produces an antagonist — a survivor
              of the affected village who now hunts the character;
              a covenant-elder who declares the character outcast;
              a hierophant who calls heresy
        optional_outputs:
          - type: counter_dispatched
            target: stratigraphic_resonance
            description: |
              An unhealed scale crossing can stir the stratigraphic
              scale — the un-closed pacts of older epochs notice
              the un-paid bill and stir
          - type: mechanism_revoked
            description: |
              The character may lose access to the mechanism that
              caused the working — a faction casts them out, a
              place becomes hostile

      - branch: refused
        description: |
          The character refused to engage with the arriving
          consequence. Walked away. The scale remains crossed; the
          consequence still lands, but on people the character has
          chosen not to know about.
        mandatory_outputs:
          - type: ledger_lock
            bar: <crossing_scale>
            level: 0.7
            description: "Scale remains high; consequence fires offstage"
          - type: scar
            severity: major
            axis: shame_or_principle
          - type: bond_broken
            description: "The character abandoned someone who needed them"
        optional_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: -0.10
            description: "The character closes against future obligation"
          - type: counter_dispatched
            description: "An NPC who survived the abandoned scope hunts the character"

  # ──────────────────────────────────────────────────────────────
  - id: the_stratigraphic_resonance
    label: "The Stratigraphic Resonance"
    description: |
      The stratigraphic_scale crosses threshold_higher (0.85) but
      not yet apocalyptic. The bedrock is awake; ancient
      civilizations are partially manifesting; pre-current-epoch
      entities have agency in the world. World-scope confrontation
      that affects all characters simultaneously. May span multiple
      sessions; the resonance does not resolve in one scene.
    when_triggered: |
      stratigraphic_scale crosses 0.85. Once triggered, the
      confrontation remains active across sessions until resolved.
      Subsequent workings during active resonance debit at 1.5×
      multipliers across all five scales (the bedrock's instability
      amplifies everything).
    resource_pool:
      primary: stratigraphic_scale
      secondary: world_state
    stakes:
      declared_at_start: true
      hidden_dimensions: true       # which specific stratigraphic
                                    # entity is manifesting may be
                                    # hidden — multiple are possible
    valid_moves:
      - investigate                 # learn what is manifesting
      - appease                     # offer to the awakening force on
                                    # something like its own terms
      - close_the_pact              # complete the un-closed pact of the
                                    # affected ancient civilization;
                                    # discharges stratigraphic scale at
                                    # extreme cost
      - reinforce_the_seal          # strengthen barriers; temporary
                                    # fix that buys time but does not
                                    # discharge
      - flee_the_affected_region    # withdraw from the resonance zone;
                                    # other characters may suffer
      - serve_the_awakening         # actively help the stratigraphic
                                    # entity; betrayal of current
                                    # civilization
    outcomes:
      - branch: clear_win
        description: |
          The character successfully closed an un-closed pact OR
          appeased the resonance OR sealed the breach. The
          stratigraphic scale discharges substantially. The
          civilization holds. Most-celebrated heavy_metal
          confrontation outcome — the character has saved
          everyone they have ever met from a force they did not
          know existed.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: stratigraphic_scale
            level: 0.40
            description: "Bedrock subsides; resonance ends"
          - type: pact_tier
            delta: +2
            description: "Massive standing-with-the-current-civilization gain"
          - type: bond
            target_kind: world
            description: "The character has a bond with the world itself now — the world remembers them"
          - type: secret_known
            description: "The character knows the name and shape of the closed pact"
        optional_outputs:
          - type: scar
            severity: defining
            axis: existential
            description: "What the character saw cannot be unseen"
          - type: reputation_tier
            description: |
              The character is now legendary in the affected region —
              the stranger who closed the breach
          - type: mechanism_unlocked
            description: |
              Stratigraphic-touched innate_v1 character may unlock
              a Crossing into a stratigraphic-tradition learned
              variant — esoteric, world-specific

      - branch: pyrrhic_win
        description: |
          The resonance was contained — at the cost of something
          irreplaceable. A community is consumed. A bloodline
          ends. A god dies feeding the seal. The character closed
          the pact AND the price was a defining piece of the
          world.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: stratigraphic_scale
            level: 0.30
          - type: world_state
            description: |
              A defining feature of the world is permanently changed
              — a city falls, a god dies, a region becomes
              uninhabitable, a covenant-people is wiped out
          - type: scar
            severity: defining
          - type: bond_broken
            description: "Whatever or whoever paid the price"
        optional_outputs:
          - type: counter_dispatched
            target: stratigraphic_remnant
            description: |
              Some part of the awakening did not seal cleanly;
              a remnant remains active in the world, manageable
              but persistent
          - type: identity_shift
            axis: ocean.openness
            delta: -0.15

      - branch: clear_loss
        description: |
          The resonance was not contained. The stratigraphic scale
          escalates toward apocalyptic. The Cascade confrontation
          is now imminent. The character has failed and the world
          is failing.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: stratigraphic_scale
            delta: 0.10
            description: "Scale rises further, approaching apocalyptic threshold"
          - type: world_state
            description: |
              The affected region is now permanently changed —
              ancient terrain features re-emerge, ancient
              boundaries collapse, ancient roads reappear
          - type: scar
            severity: defining
            axis: existential
        optional_outputs:
          - type: counter_dispatched
            target: cascade_imminent
            description: "The Cascade confrontation is now scheduled"
          - type: enemy_made
            description: |
              An ancient entity has noticed the character; not
              hostile in the modern sense, but interested

      - branch: refused
        description: |
          The character fled the affected region and let the
          resonance proceed. Survival; abandonment. The
          stratigraphic scale remains dangerously high; the
          character is not present for resolution. Other NPCs
          (or PCs) may handle it; or it may proceed to The
          Cascade. The character pays in self-knowledge, not
          in ledger.
        mandatory_outputs:
          - type: scar
            severity: defining
            axis: shame
            description: "The thing the character ran from"
          - type: ledger_lock
            bar: stratigraphic_scale
            level: 0.80
            description: |
              Scale locks at high — the resonance proceeds at
              reduced rate (the world has SOMETHING holding it),
              but does not discharge
        optional_outputs:
          - type: bond_broken
            description: "Whoever the character abandoned in the affected region"
          - type: identity_shift
            axis: ocean.openness
            delta: -0.20
          - type: mechanism_revoked
            description: |
              The character may be unable to return to the
              affected region without triggering hostile
              recognition

  # ──────────────────────────────────────────────────────────────
  - id: the_cascade
    label: "The Cascade"
    description: |
      Three or more scales cross threshold_higher within a short
      period (defined by world; default: same session) AND/OR
      stratigraphic_scale crosses threshold_apocalyptic (1.0). The
      world is paying simultaneously across multiple registers; the
      bookkeeping has reached crisis. Campaign-defining event.
      Almost always pyrrhic at best. May be the explicit endgame
      of a heavy_metal campaign.
    when_triggered: |
      EITHER:
        (a) Three or more of {communal, covenant, divine,
        stratigraphic} cross 1.0 within one session, OR
        (b) stratigraphic_scale crosses 1.0 (apocalyptic threshold).
      Once triggered, The Cascade supersedes other active
      confrontations — they delegate to it. Discharge of any single
      scale during The Cascade is harder (the cascade-state
      multiplies costs).
    resource_pool:
      primary: stratigraphic_scale
      secondary: world_state
      tertiary: bond                # the character's network of
                                    # supportive relationships across
                                    # all affected scopes
    stakes:
      declared_at_start: true
      hidden_dimensions: true       # the cascade has interlocking
                                    # mechanisms; closing one scale
                                    # may release another
    valid_moves:
      - sacrifice_a_scope           # offer one community/bloodline/god
                                    # to save the others
      - close_the_oldest_pact       # attempt to address the
                                    # stratigraphic source first
      - feed_the_loudest_god        # whichever divine_scale is highest
      - rally_the_living_civilization  # multi-character; requires bonds
                                       # across multiple affected scopes
      - serve_the_awakening         # cross over; help the stratigraphic
                                    # forces; betrayal-of-civilization;
                                    # may be the only survivable path
                                    # at apocalyptic threshold
      - flee_to_an_unaffected_world # narrative escape; may not be
                                    # available in all worlds
    outcomes:
      - branch: clear_win
        description: |
          The character (or party) closed the cascade. Multiple
          scales discharge; the world holds. The character is
          changed permanently. This branch is rare and earned.
        narrative_shape: |
          What was crossed has been re-closed. The bedrock
          subsides. The gods return to their feeding-cycles.
          The covenants stabilize. The communities mourn but
          rebuild. The character stands in a different world
          than the one they entered — shape preserved, color
          changed.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: stratigraphic_scale
            level: 0.5
          - type: ledger_bar_discharge
            bar: <each crossed scale>
            level: 0.4
          - type: pact_tier
            delta: +3
            description: "Legendary standing — among the rarest outputs in the framework"
          - type: bond
            target_kind: world
            description: "The world itself has bonded with the character"
          - type: scar
            severity: defining
            axis: existential
            description: "The character will carry the cascade for life"
          - type: identity_shift
            axis: ocean.openness
            delta: +0.20
            description: "The character is now profoundly more open"
        optional_outputs:
          - type: reputation_tier
            description: "Legendary; the character's name will be remembered for centuries"
          - type: secret_known
            description: |
              The character now knows the metaphysics of the world
              at a depth no other character may share

      - branch: pyrrhic_win
        description: |
          The cascade was closed at the cost of one defining scope.
          A bloodline ended forever. A god died. A great
          civilization-region went dark. The character lived; the
          world is meaningfully diminished.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: stratigraphic_scale
            level: 0.4
          - type: world_state
            description: "A scope is permanently lost — bloodline extinct, god dead, region uninhabitable"
          - type: scar
            severity: defining
            axis: existential
          - type: bond_broken
            description: "The lost scope's bonds with the character — or the character's central bond with another character who paid the price"
        optional_outputs:
          - type: counter_dispatched
            target: stratigraphic_remnant_persistent
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.20

      - branch: clear_loss
        description: |
          The cascade was not closed. The civilization the players
          are part of falls. Cross-civilization replacement:
          stratigraphic forces fully manifest; the current epoch
          ends. The character may survive personally but the world
          they knew is gone. This is a campaign-ending outcome
          in most heavy_metal worlds.
        narrative_shape: |
          The character watches the bedrock take shape it has not
          held in ten thousand years. Civilizations are not saved.
          The character is alive in something different now. What
          comes next is the players' problem — but it is no longer
          THIS campaign's problem.
        mandatory_outputs:
          - type: world_state
            description: "Civilization-level transition; current epoch ends"
          - type: ledger_lock
            bar: stratigraphic_scale
            level: 1.0
            description: "Scale locked at apocalyptic; new epoch begins"
          - type: scar
            severity: defining
            axis: existential
          - type: bond_broken
            description: "The character's network of relationships is largely shattered"
        optional_outputs:
          - type: identity_shift
            description: "Multiple OCEAN axes shift; the character is profoundly remade"
          - type: mechanism_unlocked
            description: |
              The new epoch has its own delivery mechanisms; the
              character may emerge as a founding figure of what
              comes next

      - branch: refused
        description: |
          The character refused engagement. Either fled to an
          unaffected world (if available — rare) or simply did
          not act. The cascade proceeded without the character's
          participation; its outcome is offstage from the
          character's perspective.
        narrative_shape: |
          The character saved themselves and left the world to its
          accounting. Possibly the most morally complex outcome
          in the framework. Whether it was wisdom or cowardice
          depends on the world and the world's narrator.
        mandatory_outputs:
          - type: world_state
            description: |
              Outcome is determined by world's NPC mechanics; the
              character does not influence; possibly clear_win,
              possibly clear_loss outcomes happen offstage
          - type: scar
            severity: defining
            axis: shame_or_relief
            description: |
              Narrator-chosen by world-tone; some characters wear
              this as wisdom, some as the wound that defines them
          - type: bond_broken
            description: "The bonds the character abandoned"
        optional_outputs:
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.30
            description: |
              Profound closure against future obligation — the
              character may not be able to engage at this scope
              again
          - type: mechanism_revoked
            description: |
              All scopes within the affected world close to the
              character; the character must operate elsewhere

# ─────────────────────────────────────────────────────────────────────
# REVEAL — confrontation outcome callouts (Decision #2)
# ─────────────────────────────────────────────────────────────────────
reveal:
  mode: explicit
  timing: at_outcome
  format: panel_callout
  suppression: none
  per_branch_iconography:
    clear_win: ⚖
    pyrrhic_win: 🩸
    clear_loss: ⛓
    refused: 🚪
  per_confrontation_iconography:
    the_account_comes_due: 📜
    the_stratigraphic_resonance: 🪨
    the_cascade: 🌋

  # Special panel render for partial/hidden attribution
  attribution_disclosure_at_outcome: |
    When a confrontation resolves, all hidden-attribution debits
    that contributed to the crossing scale are fully disclosed.
    The panel renders the previously-hidden contributions in a
    "the bill, finally itemized" footer. This is a key dramatic
    beat: the character has been paying without knowing the
    addresses; at outcome, the addresses are revealed.

# ─────────────────────────────────────────────────────────────────────
# HARD LIMITS specific to obligation_scales
# ─────────────────────────────────────────────────────────────────────
hard_limits:
  inherits_from_genre: true
  additional_forbidden:
    - id: scale_dischargable_without_confrontation
      description: |
        A scale at threshold_high or threshold_higher cannot
        discharge except through a confrontation outcome. There is
        no "downtime" or "session-end" discharge for crossed scales.
        The bill comes due with witnesses and stakes, not in summary
        narrative. Narration that dribbles a covenant_scale down
        from 1.0 to 0.4 between sessions without an explicit
        Account Comes Due confrontation is wrong.
    - id: cross_world_scale_propagation
      description: |
        Stratigraphic scale is per-world. A character's workings in
        World A do NOT debit World B's stratigraphic scale, even if
        the character is the same. The bedrock is not portable.
        (Other scales follow the character — covenant follows the
        bloodline; individual follows the character; communal
        follows the affected community per scope rules.) Stratigraphic
        is the exception.
    - id: pre_chargen_debt_assignment
      description: |
        Worlds may set chargen baselines for scales (long-historied
        worlds chargen with high stratigraphic baseline; covenant-
        people characters chargen with elevated covenant). Worlds
        may NOT chargen a character with their personal individual
        scale already crossed; the character's first session must
        include the working that crosses, OR the character was not
        a magic-user before chargen.
    - id: scale_dishonesty
      description: |
        A debited_scales attribute on a magic.working span MUST be
        accurate. The narrator may use partial or hidden
        attribution_state to dramatize uncertainty, but the
        underlying debit MUST be calculated against the actual
        working's reach. Decorative scale-debiting (for atmosphere
        only, with no real bookkeeping update) is a deep_red OTEL
        violation.

# ─────────────────────────────────────────────────────────────────────
# NARRATOR REGISTER — prose voice for the cross-scale uncertainty
# ─────────────────────────────────────────────────────────────────────
narrator_register: |
  This plugin's narrator register is *uncertainty about the address*.
  Every working's effect lands clearly in the moment; the bill's
  destination may not. Render this as a felt thing — not as
  exposition. The pact-bearer feels the working land but does not
  know who is paying. The narrator surfaces this with vocabulary of
  *direction*: "the bill is sent — somewhere," "something distant
  has been charged," "a community the caster has never visited
  records the working in a book they will not read."

  Use the five scales as TAG SET rather than as exposition. Do not
  narrate "your working has debited the covenant scale by 0.10."
  Narrate the felt register: "the mark on your forearm aches; the
  marks on your cousins ache too, three towns away." The panel
  shows the math; the prose shows the meaning.

  When attribution_state is partial or hidden, use indirect
  vocabulary. The character "feels the working land but cannot
  trace its tail." The narrator may add specificity later, when
  the bill is itemized at outcome — "you remember the Reverend's
  daughter who was kind to you in the village by the standing
  stone. She was the address. She is gone now." Disclosure-at-
  outcome is one of the genre's load-bearing dramatic beats.

  Stratigraphic-scale debits are the deepest register. Render with
  vocabulary of geology, sleep, and slow waking. "The bedrock
  remembers something." "Something far below has noticed." "An
  un-closed contract has just felt itself referenced." Use sparingly;
  the stratigraphic register loses force if every working invokes
  it.

  Communal-scale debits are the most-played register. Render with
  vocabulary of distance, community, witnessing. "The town will
  pay for this in some way you may not see for a season." "The
  guild's books are heavier tonight." "Somewhere in the parish, a
  child is born marked." The communal scale is where most of the
  genre's mid-arc drama lives.

  Covenant-scale debits are the most personal-while-not-yours
  register. Render with vocabulary of family, lineage, biology
  beyond consent. "Your mother feels the mark deepen." "Your
  cousin's child will be born with the trait full-strength." The
  covenant scale is where the genre's hereditary register lives.

  Divine-scale debits are the loudest in narrative volume but
  least surprising. Render with vocabulary of feeding, hunger,
  apparatus. "The god's tongue moves; the clergy will be
  hungrier this week." Use specific named gods always; never
  generic "a god" register.

  The Cascade narration, if it happens, is a tonal shift. The
  prose may slow, expand, become incantatory. The world is
  visibly paying across multiple ledgers; the narration should
  feel like a worldscape view rather than a character-scope
  view.

# ─────────────────────────────────────────────────────────────────────
# WORLDBUILDING SLOT — what worlds must instantiate
# ─────────────────────────────────────────────────────────────────────
world_layer_required:
  - At least one named instantiation per active scale
    description: |
      A world hosting this plugin MUST instantiate:
        - communal_scale: at least one named community (village,
          guild quarter, parish)
        - covenant_scale: at least one named covenant-people /
          bloodline (the genre's "covenant-peoples" cosmological
          register made specific)
        - divine_scale: at least one named god (with named clergy
          and feeding apparatus — overlaps with divine_v1 instantiation)
        - stratigraphic_scale: at least one named ancient
          civilization or pre-current-epoch entity whose un-closed
          pacts contribute to the bar
      Worlds may have many instantiations per scale. Few is acceptable
      for early worlds; depth comes with maturity.

  - Stratigraphic baseline declaration
    description: |
      Each world declares the chargen-time stratigraphic_scale
      baseline. The Long Reckoning, after twelve centuries of
      accumulated obligation, may chargen at 0.30 or 0.40. A
      newly-settled world (post-cataclysm settlements) may
      chargen near zero.

  - Cascade availability
    description: |
      Worlds declare whether The Cascade confrontation is reachable
      in this campaign. Some worlds explicitly position The Cascade
      as endgame; others declare it unreachable (because the
      stratigraphic_scale's apocalyptic threshold has been narratively
      protected from crossing in this campaign). The
      `cascade_availability: campaign_endgame` configuration is the
      most common heavy_metal setup.

  - Per-scale decay overrides
    description: |
      Worlds may override the default decay rates for their specific
      cosmological tone. A world with very-active gods may set
      divine_scale decay HIGHER (gods feed continuously) to model
      the apparatus working as designed. A world recovering from
      a recent civilization-fall may set stratigraphic decay LOWER
      than the framework default (the bedrock is not yet
      stabilized).

  - Per-scale chargen baseline overrides
    description: |
      Beyond the framework defaults, worlds may set per-instance
      baselines — particular communities chargen with high
      communal_scale because of recent magical events; particular
      bloodlines chargen with high covenant_scale because of
      historical obligation; particular gods chargen with high
      divine_scale because of recent crises in their apparatus.

  - Confrontation-resolution NPCs
    description: |
      The Account Comes Due confrontation requires named NPCs at
      the affected scope to dispatch. A world hosting this plugin
      should have:
        - per affected community: a community-elder / mayor / parish-priest
          who is the face of the consequence
        - per affected bloodline: a covenant-elder who carries the
          mark most visibly
        - per affected god: a hierophant / bishop / saint who
          interfaces with the apparatus
        - per stratigraphic site: a guardian / hermit / haunting
          who answers when the scale is queried
      These NPCs exist whether or not the character ever meets them;
      they are the world's bookkeepers.
```

## Validation Notes

This plugin captures:

- ✅ All five napkin obligation scales as world-shared ledger bars (parallel to divine_v1's Hunger and innate_v1's Signal patterns)
- ✅ Cross-cutting plugin type explicitly declared (NOT source_shaped); no Source, no classes, no delivery mechanisms — these omissions are by design and explained
- ✅ Monitored plugins enumerated with primary scales each typically debits — five Source plugins all integrated
- ✅ OTEL span CONSUMPTION shape (not emission) — first plugin to consume rather than emit; required attribute extension on monitored plugins' magic.working spans is fully specified
- ✅ Three attribution states (named / partial / hidden) covering the dramatic-uncertainty mechanic
- ✅ Fallback behavior on missing attribute (graceful degradation with YELLOW flag)
- ✅ Three confrontations with full 4-branch outcome trees (The Account Comes Due, The Stratigraphic Resonance, The Cascade)
- ✅ Mandatory output on every branch (Decision #1)
- ✅ Failure-advances on clear_loss and refused branches (Decision #4)
- ✅ Player-facing reveal (Decision #2 — explicit, at_outcome, panel_callout, with attribution_disclosure_at_outcome as a special render)
- ✅ Decay rates per scale calibrated to scale's narrative time-horizon (individual: never, communal: very slow, covenant: nearly never, divine: slow, stratigraphic: functionally never)
- ✅ Hard limits specific to the cross-cutting nature (no off-screen discharge; no cross-world stratigraphic propagation; no pre-chargen individual debt; no decorative debiting)
- ✅ Narrator register tailored to address-uncertainty as the load-bearing dramatic mechanic
- ✅ World-layer instantiation slots specified (named instances per scale, baselines, cascade availability, decay overrides, confrontation-resolution NPCs)
- ✅ Shared bar pattern with divine_v1 explicitly declared — divine_scale here IS divine_v1's Hunger viewed through this plugin's lens; bidirectional shared updates

## Plugin Lane Boundary — How obligation_scales relates to Source plugins

Unlike Plugin Lane Boundary sections in Source-shaped plugins (which delineate which Source's territory is which), this plugin's lane boundary is *vertical*: it operates ABOVE the Source plugins and AGAINST none of them. The boundaries that matter:

| Concern | Source plugin handles | obligation_scales_v1 handles |
|---|---|---|
| Whether the character can perform a working | YES | NO — defers entirely |
| What the working DOES (the effect) | YES | NO |
| Individual character costs (the personal bill) | YES (via plugin-specific bars) | Tracked via individual_scale as union view, but NOT the source of truth — Source plugins own the per-character bill |
| Community / bloodline / god / world consequences | NO | YES — exclusive territory |
| Cross-scope cascading (one scale's crossing affecting another) | NO | YES — exclusive territory |
| The dramatic uncertainty about WHERE the bill goes | NO | YES — exclusive territory |
| The metaphysical claim that workings PROPAGATE at five scopes | NO | YES — the cosmological feature this plugin exists to enforce |

This plugin is **not in competition** with the Source plugins. It depends on them. It cannot be activated in a world that has zero Source plugins active (there would be nothing to track). Its role is to make the heavy_metal cosmology mechanically real — the genre asserts that obligation propagates at five scales and the framework now enforces this.

## Open Notes for Implementation

1. **Shared-bar implementation pattern.** divine_scale here IS divine_v1's Hunger bar, viewed through this plugin's lens. First explicit case in the framework of two plugins owning views of the same underlying ledger entry. Implementation needs to ensure updates from EITHER plugin propagate to the OTHER without double-counting and without race conditions. Architect call.

2. **OTEL span consumption (not emission) is structurally new.** This is the first plugin in the framework that reads other plugins' spans rather than emitting its own. The monitored plugins' span attribute extension (`debited_scales`) needs to be a hard requirement at server startup — heavy_metal worlds cannot run with monitored Source plugins that don't populate this attribute. Validation should fire at world-load, not at first-working-cast.

3. **Per-scope-instance ledger bars at world-load time.** A world with 12 named communities + 3 bloodlines + 2 gods + 1 ancient civilization instantiates 18 communal/covenant/divine/stratigraphic bars (plus N individual_scale bars for active characters). This is more bars than any other plugin requests; the panel architecture needs to handle filtering and rolling-up at scale. Buttercup call.

4. **Attribution state in the panel.** Three render modes for debits (named, partial, hidden) need three visual treatments. Hidden-attribution-disclosed-at-outcome is a load-bearing dramatic beat that requires special panel render. Buttercup call.

5. **Confrontation chaining at threshold crossings.** When individual_scale crosses 1.0, this plugin DELEGATES to the relevant Source plugin's collection confrontation (bargained_for_v1's The Calling, divine_v1's The Audit, etc.) rather than firing its own confrontation. This delegation pattern is new — confirm the confrontation orchestrator can route based on the crossing's source-plugin context.

6. **The Cascade as session-spanning state.** Most confrontations resolve within a session. The Stratigraphic Resonance can span multiple sessions; The Cascade is campaign-defining and may span the full remainder of the campaign. The state machine for these multi-session confrontations needs explicit modeling — they are not single confrontations but ongoing world-states with periodic resolution-attempt confrontations within them. Architect call.

7. **No multi-genre obligation propagation.** Confirmed: stratigraphic scale is per-world. A character who travels worlds (rare in heavy_metal but possible) does not carry stratigraphic obligation across; they DO carry individual and covenant. World-load logic needs to handle inbound character bookkeeping correctly when the character has crossed worlds.

8. **No cross-genre instantiation.** This plugin is heavy_metal-only at present. Other genres' magic.yaml files MUST NOT activate this plugin; the framework's plugin loader should reject the activation. Open question (deferred): if another genre proves to need cross-cutting propagation (e.g., if elemental_harmony develops a five-element-balance tracker shaped similarly), would that be a SECOND multi-plugin layer plugin, or a multi-instance generalization of this one? Defer until concretely needed.

9. **Genre-pack instantiation** — the natural first concrete instantiation is `heavy_metal/worlds/the_long_reckoning/magic.yaml`. The Long Reckoning has the deepest cosmological depth in the lore (twelve centuries of accumulated obligation; the Hungering Lord and the Bargainers Guild; the un-closed pacts of older epochs). Authoring effort: meaningful — needs to enumerate at least one community per scale, several bloodlines, named gods, and the stratigraphic civilizations. Estimated 800–1200 lines (similar to flickering_reach).

## Next Concrete Moves (post-this-draft)

- [ ] Architect review the shared-bar pattern with divine_v1 — first such case; needs implementation strategy
- [ ] Architect review the OTEL span CONSUMPTION pattern — first plugin to do this; consider whether the framework needs a generic "plugin observer" pattern or whether this is bespoke
- [ ] Architect review the multi-session confrontation pattern (The Stratigraphic Resonance, The Cascade) — confirm state-machine support
- [ ] Architect review the delegation pattern for individual_scale crossings — confirms the confrontation orchestrator can route to monitored plugins
- [ ] UX (Buttercup) sketch the cross-cutting panel — multiple bars per scale (per-community, per-bloodline, etc.), attribution-state rendering, the disclosure-at-outcome footer
- [ ] UX (Buttercup) sketch The Cascade panel — campaign-defining, multi-scale visualization
- [ ] GM — instantiate The Long Reckoning's `magic.yaml` to validate this plugin against actual play prompts (signature world, signature multi-plugin layer)
- [ ] Cliché-judge — add the four hooks listed in ledger_bars (decorative scale-debiting, communal-without-witnesses, covenant-without-bloodline, stratigraphic-without-engagement) to the magic-narration audit checklist
- [ ] Plugin authoring — confirm all five Source plugins' magic.working span specs include `debited_scales` as an optional_attribute extension when the active genre is heavy_metal. The shape may need backporting into bargained_for_v1.md, divine_v1.md, learned_v1.md, innate_v1.md, item_legacy_v1.md as a "heavy_metal-extension" note in their OTEL sections. *(Defer until heavy_metal world-layer instantiation forces it.)*

## Framework Note: Plugin Coverage Now Complete

With this draft, all six entries in `magic-plugins/README.md`'s active specs table are drafted:

| Plugin | Source | Status |
|---|---|---|
| `bargained_for_v1` | bargained_for | ✅ |
| `item_legacy_v1` | item_based | ✅ |
| `divine_v1` | divine | ✅ |
| `innate_v1` | innate | ✅ |
| `learned_v1` | learned | ✅ |
| `obligation_scales_v1` | (multi-plugin layer) | ✅ NEW |

The framework's plugin coverage is mechanically complete at the design layer. Remaining work is concrete world-layer instantiations (one done — flickering_reach; one suggested next — the_long_reckoning) and architect/dev/UX review passes against the implementation pipeline.
