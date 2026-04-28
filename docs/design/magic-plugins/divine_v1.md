# Plugin: divine_v1

**Status:** Draft, 2026-04-28
**Source:** `divine` (napkin)
**Genres using:** heavy_metal, victoria-Catholic, low_fantasy, elemental_harmony, space_opera-religious-orders
**Companion docs:** `../magic-taxonomy.md`, `../visible-ledger-and-otel.md`, `../confrontation-advancement.md`, `bargained_for_v1.md`, `item_legacy_v1.md`

## Identity

Divine magic is **participation in a feeding economy**. Gods are real, specific, and hungry. Churches that work are feeding operations. Magic flows from worship — not from negotiation, not from possession, not from mutation, but from the believer's *participation in the apparatus that feeds the god in exchange for the god's grant*.

Three things distinguish this plugin from `bargained_for_v1` (the other sentient-patron plugin):

1. **The apparatus mediates.** In Bargained-For, the patron answers you directly. In Divine, the *bureaucracy* mediates between you and the god. Most workings flow through the apparatus' procedural texture — the rite, the tithe, the doctrine. Direct divine contact (The Calling) is rarer and weightier than Bargained-For's equivalent.
2. **Cost-shape is procedural, not personal.** Worship costs purity (ritual preparation), time (the rite, the festival, the prayer cycle), components (the offering, the tithe, the sacrifice), and *standing* (your position in the apparatus). Soul/Debt is light here — you don't bargain your soul; you offer your devotion. The god takes what is offered, not what is owed.
3. **Severance is institutional.** Excommunication, not Severance. You are cast out of a *community*, not freed from a *contract*. The apparatus persists; you are simply no longer part of it. The god remains hungry; you are simply no longer feeding it.

This plugin is heavy_metal's **divine** obligation scale — the third of five obligation-scales in that genre's cosmology. The plugin's `god_id` and `apparatus_id` integrate with heavy_metal's `obligation_scales_v1` plugin (TODO).

## Plugin Definition

```yaml
plugin: divine_v1
status: draft
genres_using:
  - heavy_metal              # signature — one of three magic systems
  - victoria                 # only at gothic ≥ 0.4 — Catholic-coded register
  - low_fantasy              # multiple competing churches (Pale Fire, Drowned Mother)
  - elemental_harmony        # spirit-medium has divine-shaped contact
  - space_opera              # Dune Bene Gesserit, Star Wars Jedi-as-religious-order

source: divine               # napkin Source

# ─────────────────────────────────────────────────────────────────────
# DELIVERY MECHANISMS
# ─────────────────────────────────────────────────────────────────────
delivery_mechanisms:
  - id: faction
    archetype: religious_apparatus
    description: |
      The Church, the Order, the Cult, the Diocese, the Temple
      Hierarchy. The institutional feeding bureaucracy. This is the
      strongest signature mechanism for divine_v1 — most divine
      magic flows through institutional rite.
    npc_roles: [priest, hierophant, deacon, lay_worker, inquisitor, apostate]
    plot_engine: institutional politics, rank arcs, doctrinal schism
    canonical_examples:
      - "The Church of the Pale Fire (low_fantasy)"
      - "The Catholic apparatus (victoria, Brontë register)"
      - "The Bene Gesserit (Dune-world space_opera)"
      - "The Eastern Diocese of the Hungering Lord (heavy_metal)"

  - id: place
    description: |
      The holy site, the consecrated altar, the sacred grove, the
      shrine, the ruined cathedral. Divine magic flows from or only
      at the site. The site is the god's mouth.
    plot_engine: pilgrimage, geographic-tension, contested-holy-ground
    canonical_examples:
      - "The Drowned Mother's altar at the cliff (low_fantasy)"
      - "The unmarked grove where the local god feeds (heavy_metal)"
      - "The cathedral whose nave still works (victoria)"

  - id: condition
    description: |
      Ritual purity, fasting, prayer, confession, penance, abstention.
      The god responds when the worshipper has prepared. The
      condition is the cost paid in advance for access.
    plot_engine: ascetic transformation, ritual-purity arcs
    canonical_examples:
      - "Forty days of fasting before the rite"
      - "Confession before communion"
      - "The blood-fast (no flesh) before the war-rite"

  - id: time
    description: |
      Liturgical calendar — festival, feast day, holy hour, ember
      week, the night the god walks. The cycle is the channel; miss
      the window, the god is asleep.
    plot_engine: deadlines, cyclical urgency, missed-window dread
    canonical_examples:
      - "Compline only, never any other office"
      - "The Festival of the Bones — once a year"
      - "Easter Vigil — the god wakes at midnight"

  - id: relational
    description: |
      Direct line to a saint, named demigod, ancestor, intercessor.
      The character has a personal advocate within the divine
      apparatus — uncommon, often itself a Calling-shaped event.
      The relationship is with the saint/intercessor, not the god.
    plot_engine: patron-protégé, hagiography-as-history
    canonical_examples:
      - "I pray to my dead grandmother who became a local saint"
      - "St. Eulalia answers when others do not"

  - id: native
    description: |
      Born marked by a god — the chosen apostle, the divine bloodline,
      the marked-at-birth heir. Rare. Usually carries a chosen_one
      narrative tag. The character did not choose; the god did.
    plot_engine: identity arcs, growing-into-the-mark
    canonical_examples:
      - "Born with the stigmata visible from infancy"
      - "Heir of a Vessel-line, marked at birth"

# Mechanisms NOT supported:
# - discovery: divine magic isn't found in objects — that's item_legacy
#   with religious-coded artifacts (the saint's reliquary is an item_legacy
#   instance); divine_v1 itself doesn't deliver via found objects
# - cosmic: too ambient — divine_v1 requires specific god, specific
#   apparatus or specific contact; the cosmic-ambient register is
#   served by other framing (genre-default morality cosmology, not
#   plugin)

# ─────────────────────────────────────────────────────────────────────
# CLASSES — player-build options that draw from this plugin
# ─────────────────────────────────────────────────────────────────────
classes:
  - id: priest
    label: Priest / Cleric
    requires: [apparatus_membership, doctrinal_training]
    typical_mechanisms: [faction, condition, time]
    pact_visibility_to_player: full      # priests know the doctrine
    narrator_note: |
      Trained in the Apparatus. Knows the rites, the calendar, the
      hierarchy. Performs formal worship. The default class for
      this plugin in most genres.

  - id: devotee
    label: Devotee / Lay-Worshipper
    requires: [apparatus_membership]
    typical_mechanisms: [faction, place, time]
    pact_visibility_to_player: partial   # knows their own observance, not doctrine
    narrator_note: |
      Participates in feeding without official rank. Lay-cleric
      register. Less mechanical power than Priest but lower
      institutional debt — the apparatus expects less but grants
      less.

  - id: saint
    label: Saint / Vessel
    requires: [chosen_by_god]            # narrative-only at chargen; arrives via The Calling in play
    typical_mechanisms: [relational, native]
    pact_visibility_to_player: minimal   # the Saint does not know what is asked of them
    chosen_one_tag: true                 # may carry the chosen_one narrative tag
    narrator_note: |
      Has direct contact with the god, often without choice. Rare;
      usually arrives mid-campaign via a Calling. The Saint's
      relationship is with the GOD, not the apparatus — and the
      apparatus is often jealous, suspicious, or hostile.

  - id: hierophant
    label: Hierophant
    requires: [apparatus_membership, rank: high, doctrinal_training: advanced]
    typical_mechanisms: [faction]
    pact_visibility_to_player: full
    narrator_note: |
      High-rank religious official. Knows the bureaucratic
      hierarchy intimately. Makes doctrine; not just follows it.
      Moral weight is heavy — the hierophant decides what others
      may worship.

  - id: wandering_prophet
    label: Wandering Prophet
    requires: [direct_divine_contact_claim]
    typical_mechanisms: [relational, native, place]
    pact_visibility_to_player: full
    narrator_note: |
      Outside the Apparatus. Claims direct divine contact. Often
      heretical from the apparatus' point of view — and may BE
      heretical, or may be a true Saint outside official channels.
      Always controversial.

# ─────────────────────────────────────────────────────────────────────
# COUNTERS
# ─────────────────────────────────────────────────────────────────────
counters:
  - id: heretic
    label: The Heretic
    description: |
      Doctrinally opposed practitioner — may serve a different god,
      a different sect of the same god, or no god at all. Ideologically
      committed; not just an enemy of convenience.
    plot_use: |
      `enemy_made` output, often campaign-arc antagonist. The
      heretic has their own divine_v1 instantiation (or another
      plugin). Two divine_v1 characters of opposed doctrines is
      rich content.

  - id: rival_inquisitor
    label: The Rival Inquisitor
    description: |
      Institutional anti-heresy agent of an OPPOSING church. (An
      inquisitor of YOUR church is your ally.) Hunts your apparatus'
      practitioners as heretics. May be a Priest of equal rank but
      opposite faith.
    plot_use: |
      `counter_dispatched` after high-Standing or high-Notoriety
      workings. Drives cross-apparatus politics.

  - id: apostate
    label: The Apostate
    description: |
      Former priest who walked away. Knows the apparatus, knows
      its rites, knows where it is weakest. May want it destroyed,
      reformed, or simply forgotten. The most dangerous counter
      because they have insider knowledge.
    plot_use: |
      `enemy_made` if hostile; `ally_named` if returning to the
      fold; `secret_known` carrier in either case. Drives the
      "what if we lose someone in the church" arc.

  - id: eater_of_gods
    label: The Eater of Gods
    description: |
      Esoteric counter. Specialist who can starve a god by
      interrupting its feeding economy — assassinating priests,
      defiling altars, breaking liturgical cycles. Rare, expensive,
      almost mythical. The Banehand of divine_v1.
    plot_use: |
      `counter_dispatched` against high-tier characters or against
      a hunger-maximum god. The Eater is often a singular legendary
      figure rather than a class of NPC.

  - id: rival_faith
    label: The Rival Faith
    description: |
      Another god's apparatus competing for the same souls and
      feeding territory. Not a single NPC but a faction-as-counter.
      Drives the "two churches in one town" arc.
    plot_use: |
      `faction_standing` decreases against this faction track in
      proportion to your own apparatus' Standing rises. Zero-sum
      in shared geography.

# ─────────────────────────────────────────────────────────────────────
# LEDGER BARS
# ─────────────────────────────────────────────────────────────────────
ledger_bars:
  - id: standing
    label: "Standing"
    color: gold
    scope: faction               # tracked per apparatus (multi-apparatus
                                 # characters carry separate Standing bars)
    range: [-1.0, 1.0]
    direction: bidirectional
    threshold_high: 0.5
    threshold_higher: 0.85
    threshold_low: 0.0
    threshold_lower: -0.4
    consequence_on_high_cross: |
      Player promoted in the apparatus. New rite-access. New
      mechanism_unlocked output eligible. Apparatus NPCs treat
      the character as trusted.
    consequence_on_higher_cross: |
      Hierophant tier — the character may make doctrine, not just
      follow it. Becomes apparatus-political-actor.
    consequence_on_low_cross: |
      Apparatus enters distrust state. Audits trigger more
      readily. Mechanism_revoked output eligible on next failed
      rite.
    consequence_on_lower_cross: |
      Excommunication automatic at next session-start, OR when
      next surface-conflict-with-apparatus occurs.
    decay_per_session: 0.0       # Decision #3
    starts_at_chargen: 0.3       # default loyal-novice Standing

  - id: hunger
    label: "Hunger"
    color: ash
    scope: world                 # SHARED across all worshippers of the god
                                 # this is the god's hunger, not yours
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold: 0.5
    threshold_higher: 0.85
    consequence_on_threshold_cross: |
      The god is dissatisfied. Workings become less reliable.
      Reliability shifts from `negotiated` to `wild`. Apparatus
      may impose extra fasts and rites world-wide.
    consequence_on_higher_cross: |
      The god is starving. Catastrophic. The hunger SEEKS — wild
      manifestations, possessions, miracle/atrocity flips.
      Inquisitors of YOUR OWN apparatus may begin hunting their
      own faithful for failures.
    decay_per_session: -0.1      # Hunger DOES fall over time as
                                 # other worshippers feed in the
                                 # background — this is the rare
                                 # exception to no-decay because
                                 # the bar is world-shared
    starts_at_chargen: 0.0       # depends on world's prior history

  - id: purity
    label: "Purity"
    color: white
    scope: character
    range: [0.0, 1.0]
    direction: bidirectional
    threshold_high: 0.5
    threshold_low: 0.0
    consequence_on_high_cross: |
      Character is in a state of grace. Rites perform at higher
      reliability. The Calling is more likely to choose this
      character.
    consequence_on_low_cross: |
      Character is unclean. Rites fail or pollute. Character must
      perform purification (ritual cycle) to recover.
    decay_per_session: -0.2      # Purity DOES decay between sessions —
                                 # this is the per-character analog of
                                 # Hunger; ritual cycles maintain it
    cyclical_reset:
      trigger: ritual_cycle      # full restoration on completion of cycle
      reset_to: 1.0
    starts_at_chargen: 0.5       # default mid-purity

# ─────────────────────────────────────────────────────────────────────
# OTEL SPAN SHAPE
# ─────────────────────────────────────────────────────────────────────
otel_span:
  span_name: magic.working
  required_attributes:
    - working_id
    - plugin                     # always: divine_v1
    - source                     # always: divine
    - declared_effect
    - domains
    - modes                      # typically: invoked | ritual
    - debited_costs              # typically: { standing, purity, components, time }
    - mechanism_engaged
    - mechanism_target
    - god_id                     # which named deity
    - apparatus_id               # which apparatus mediated (null if direct)
    - doctrinal_alignment        # in_doctrine | borderline | heretical
    - rite_id                    # which specific rite was performed
    - reliability_roll
    - world_knowledge_at_event
    - visibility_at_event
  optional_attributes:
    - witnesses_present
    - confrontation_id
    - confrontation_branch
    - hunger_impact              # delta on the world Hunger bar
  on_violation: gm_panel_red_flag
  yellow_flag_conditions:
    - "narration implies divine effect but no span fires"
    - "god_id absent (narrator hasn't named which deity)"
    - "doctrinal_alignment absent (narrator hasn't decided in/out of doctrine)"
    - "rite_id absent (the working has no procedural identity)"
  red_flag_conditions:
    - "debited_costs has no `standing`, `purity`, or `components` field"
    - "god_id references a god not in the world's pantheon"
    - "apparatus_id references an apparatus that doesn't serve god_id"
    - "doctrinal_alignment is heretical AND no Heretic counter dispatched"
  deep_red_flag_conditions:
    - "the working violates a hard_limit (multi-god simultaneous, etc.)"
    - "the working invokes a god whose Hunger is at maximum and unfed"

# ─────────────────────────────────────────────────────────────────────
# HARD LIMITS
# ─────────────────────────────────────────────────────────────────────
hard_limits:
  inherits_from_genre: true
  additional_forbidden:
    - id: multi_god_simultaneous
      description: |
        A single working cannot invoke multiple competing gods. Gods
        hate each other. A character may serve multiple gods over
        time but cannot blend their working. Gods of distinct
        domains in the SAME pantheon may sometimes co-work (Mars
        and Venus both bless certain unions); cross-pantheon never.
    - id: deity_targeted_bargaining
      description: |
        You don't negotiate with gods. You offer; they take or refuse.
        Bargaining-with-a-god is the bargained_for_v1 plugin's
        territory. Doing it inside divine_v1 is heresy and
        immediately drops Standing AND Purity AND raises Hunger.
    - id: working_without_doctrine
      description: |
        A divine working must be rooted in the god's nature. Praying
        to the war-god for healing without a heretical bend is
        forbidden. The narrator must be able to name the doctrinal
        path connecting the working to the god's domain. Improvised
        "the god granted me healing because I'm pious" is yellow-flag
        at minimum.
    - id: divine_resurrection_default
      description: |
        Divine resurrection inherits genre's resurrection rule. Most
        worlds: forbidden. Heavy_metal-permitting worlds: allowed
        but at heaviest cost — multiple Standing, Purity, components,
        AND a Calling event triggered. Victoria: forbidden absolutely.
    - id: invoking_starving_god
      description: |
        A god whose Hunger is at maximum cannot be invoked. The god
        has gone elsewhere or gone wrong. Invoking such a god summons
        the wrong-thing — possession, miracle/atrocity-flip, or
        nothing at all. Workings against this limit are deep-red
        flagged.

# ─────────────────────────────────────────────────────────────────────
# NARRATOR REGISTER
# ─────────────────────────────────────────────────────────────────────
narrator_register: |
  The god is real but rarely present. The apparatus is the
  interface. Most workings flow through doctrine — the priest does
  not say "give me healing"; they perform the rite that channels
  the god's healing-aspect. The procedure is the prayer; the
  prayer is the procedure.

  Costs are felt as participation in a larger flow, not personal
  exchange. The cleric doesn't pay; they offer, and the offering
  joins all other offerings. The cost is real but distributed —
  the bill belongs to the apparatus and the worshipper together.

  The bureaucracy has texture. Every working has procedural weight:
  the words, the gestures, the components, the timing, the
  hierarchy informed. The narrator surfaces this texture even in
  brief workings — "she made the sign before speaking" rather than
  "she cast healing."

  Failure of doctrine is heretical; failure of feeding is starvation.
  The narrator distinguishes these. Heresy attracts inquisition
  (counter_dispatched: rival_inquisitor) — a social and procedural
  threat. Starvation attracts something worse — the god itself
  going wrong, manifestations of hunger, the apparatus' inquisitors
  hunting their own to feed the god what was missed.

  Each named god has a register the narrator must hold consistently:
  the hungry god is greedy in every working; the merciful god is
  costly even in mercy; the silent god grants only when not asked.
  The world declares each god's register at instantiation; the
  narrator never deviates.

  At higher Standing, the apparatus' procedural texture loosens —
  the priest may improvise within doctrine, the hierophant may
  bend doctrine to the god's underlying nature. At lower Standing,
  every working is scrutinized; the narrator surfaces the
  apparatus' suspicion as palpable atmosphere.

  At higher Hunger, the world feels wrong. The god is reaching
  past the apparatus. Manifestations leak; signs and portents
  intensify; common workings have uncommon side-effects. The
  narrator surfaces this WITHOUT explaining — players should feel
  the world's wrongness through detail (a candle burns blue, a
  sermon is too long, the silence after the rite stretches).

# ─────────────────────────────────────────────────────────────────────
# CONFRONTATIONS
# ─────────────────────────────────────────────────────────────────────
confrontations:

  # ──────────────────────────────────────────────────────────────
  - id: the_rite
    label: "The Rite"
    description: |
      Performing a divine working. The bureaucratic procedure
      matters — the words, the gestures, the components, the
      timing. Different from bargained_for's The Working in that
      doctrinal compliance is itself a stake.
    when_triggered: |
      Player declares a divine working. Or a confrontation in
      another plugin escalates such that only divine intervention
      can resolve it (and the character has standing to invoke).
    resource_pool:
      primary: standing
      secondary: purity
    stakes:
      declared_at_start: true    # the rite's purpose is named
      hidden_dimensions: false   # divine workings are procedural and overt
    valid_moves:
      - perform_in_doctrine
      - perform_with_corner_cut    # faster but lower compliance
      - amplify_with_extra_offering
      - hold_back_components
      - improvise_within_doctrine  # only at high Standing
      - decline                    # do not perform even when needed
    outcomes:
      - branch: clear_win
        description: "Rite performed correctly; god grants."
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: standing
            delta: 0.05
          - type: ledger_bar_discharge
            bar: purity
            delta: 0.30
            description: "Purity used in the rite — must be replenished"
          - type: affinity_tier
            description: "Tick toward affinity tier-up"
        optional_outputs:
          - type: bond
            target_kind: god
            description: "Pact-bond with the god strengthens slightly"
          - type: secret_known
            description: "Doctrinal insight or revelation"

      - branch: pyrrhic_win
        description: |
          It worked, but you cut a corner. The apparatus may
          notice. The god noticed.
        mandatory_outputs:
          - type: ledger_bar_set
            bar: standing
            delta: 0.0
            description: "Standing did not rise — the rite was unworthy"
          - type: ledger_bar_rise
            bar: hunger
            delta: 0.20
            description: "The god is unsatisfied; world Hunger rises"
          - type: scar
            severity: psychic
            description: "The character knows what they cut"
        optional_outputs:
          - type: counter_dispatched
            target: rival_inquisitor
            description: "An inquisitor (of an opposing church) noticed"
          - type: bond_broken
            target_kind: character
            description: "Another priest who saw the corner-cut now distrusts"

      - branch: clear_loss
        description: |
          The rite failed — god didn't grant, OR you fumbled the
          procedure entirely.
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: standing
            delta: -0.10
          - type: ledger_bar_fall
            bar: purity
            delta: -0.50
            description: "Failed rite pollutes"
          - type: scar
            severity: faith
            description: "Visible doubt; the character's belief shaken"
        optional_outputs:
          - type: faction_standing
            delta: -1
            target_kind: faction
          - type: mechanism_revoked
            description: "This specific rite is closed for one session"

      - branch: refused
        description: "You held back — didn't perform the rite when called."
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: standing
            delta: -0.10
          - type: vitality_cost
            delta: 0.20
            description: "The situation cost without the rite's protection"
          - type: reputation_tier
            description: "People noticed you didn't perform when you should have"
        optional_outputs:
          - type: bond
            description: "A bond with whoever you protected by not invoking"

  # ──────────────────────────────────────────────────────────────
  - id: the_audit
    label: "The Audit"
    description: |
      The apparatus reviews your standing. You answer for tithes,
      observance, doctrine, conduct. May be routine (annual
      visitation) or emergency (an inquisitor has heard rumors).
    when_triggered: |
      Standing fluctuation + apparatus narrative pressure — typically
      after high-Notoriety workings, after pyrrhic_win on The Rite,
      or after a session of skipped rites.
    resource_pool:
      primary: standing
      secondary: purity
    stakes:
      declared_at_start: true
      hidden_dimensions: true    # what the auditors actually know
                                 # may be more or less than they say
    valid_moves:
      - answer_truthfully
      - answer_with_partial_truth
      - mount_doctrinal_defense      # invoke high-rank ally or doctrine
      - confess_and_seek_penance
      - lie                          # only available at lower-Standing strats
      - walk_out
    outcomes:
      - branch: clear_win
        description: "Apparatus is satisfied; you're in good standing."
        mandatory_outputs:
          - type: faction_standing
            delta: +2
            target_kind: faction
          - type: mechanism_unlocked
            description: "Deeper rite-access; new doctrine made available"
        optional_outputs:
          - type: pact_tier
            target_kind: faction
            description: "Rank advancement in the apparatus"
          - type: ally_named
            description: "A higher cleric vouches for you publicly"

      - branch: pyrrhic_win
        description: "You survived the audit but lied to do so."
        mandatory_outputs:
          - type: faction_standing
            delta: +1
            target_kind: faction
          - type: scar
            severity: moral
            description: "The lie sits on the character's conscience"
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: -0.05
        optional_outputs:
          - type: counter_dispatched
            target: apostate
            description: "Someone who knew the truth is now a threat"
          - type: enemy_made
            description: "A specific witness who knows you lied"

      - branch: clear_loss
        description: "Apparatus is dissatisfied; you're disciplined."
        mandatory_outputs:
          - type: faction_standing
            delta: -2
            target_kind: faction
          - type: mechanism_revoked
            description: "Rite-access tightened; specific rites closed"
          - type: scar
            severity: institutional
            description: "An entry on your record"
        optional_outputs:
          - type: counter_dispatched
            target: rival_inquisitor
            description: |
              Your own apparatus is now watching you (the
              inquisitor of YOUR church becomes an
              uncomfortable presence)

      - branch: refused
        description: "You walked out of the audit."
        narrative_shape: |
          Open break with the apparatus' procedural authority. The
          character has not yet been excommunicated but has
          chosen confrontation over compliance.
        mandatory_outputs:
          - type: faction_standing
            delta: -3
            target_kind: faction
            description: "Standing collapses to lowest"
          - type: mechanism_revoked
            description: "The apparatus closes ranks; access withdrawn"
          - type: reputation_tier
            description: "You became the one who walked out"
        optional_outputs:
          - type: bond
            description: "A bond with whoever supported your walking out"

  # ──────────────────────────────────────────────────────────────
  - id: the_calling
    label: "The Calling"
    description: |
      The god itself calls — bypassing the apparatus. Rarer than
      bargained_for_v1's Calling because the apparatus is meant
      to mediate; a direct Calling means the god has chosen this
      character specifically. Often makes the character a Saint
      or a Vessel; often makes the apparatus jealous.
    when_triggered: |
      Narrator-driven — the god has decided. Triggers: Standing
      higher_threshold reached AND Purity high; OR Hunger maximum
      and the god needs a deed done; OR character's biography
      makes them a destined Vessel.
    resource_pool:
      primary: purity
      secondary: identity
    stakes:
      declared_at_start: true    # the god names the deed
      hidden_dimensions: true    # the deeper cost beyond the deed itself
    valid_moves:
      - accept
      - counter_propose            # ask the god for modified terms (rare)
      - delay                      # buy time at higher cost
      - flee                       # the character runs from the calling
      - refuse                     # explicit no to the god
    outcomes:
      - branch: clear_win
        description: "You delivered for the god directly."
        mandatory_outputs:
          - type: pact_tier
            target_kind: god
            delta: +2
            description: "Direct bond with the god deepens substantially"
          - type: ledger_bar_set
            bar: purity
            level: 1.0
            description: "The god restores purity completely"
          - type: bond
            target_kind: god
            description: "The character is now seen by the god"
        optional_outputs:
          - type: mechanism_unlocked
            description: "Saint/Vessel class becomes available"
          - type: faction_standing
            delta: -1
            target_kind: faction
            description: "Apparatus is JEALOUS — you skipped the hierarchy"

      - branch: pyrrhic_win
        description: "You delivered, but at cost beyond yourself."
        mandatory_outputs:
          - type: pact_tier
            target_kind: god
            delta: +1
          - type: bond_broken
            description: "A non-god NPC bond is severed (they paid the price)"
          - type: scar
            severity: defining
        optional_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: -0.10
          - type: counter_dispatched
            target: rival_inquisitor
            description: "The apparatus is now actively suspicious of your direct contact"

      - branch: clear_loss
        description: "You couldn't deliver / failed the god's deed."
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: hunger
            delta: 0.50
            description: "The god is angry; the world will pay"
          - type: scar
            severity: defining
          - type: mechanism_revoked
            description: "The god has moved on; this path is closed"
        optional_outputs:
          - type: counter_dispatched
            target: rival_inquisitor
            description: "The apparatus dispatches a Vessel-replacement against you"
          - type: enemy_made
            target_kind: god
            description: "The god itself, briefly — a divine grudge"

      - branch: refused
        description: "You said no to the god."
        narrative_shape: |
          The most dramatic branch. The character has chosen
          mortal freedom over divine purpose. The god's wrath is
          immediate.
        mandatory_outputs:
          - type: mechanism_revoked
            description: "Closed forever for this character with this god"
          - type: counter_dispatched
            target: rival_inquisitor
            description: "Immediate divine wrath via the apparatus' enforcers"
          - type: reputation_tier
            description: "You became the one who refused the god"
        optional_outputs:
          - type: pact_tier
            target_plugin: another_plugin
            description: |
              Refusing the god opens a different path — Bargained-for
              with another patron, Item Legacy with a relic that
              prefers free wielders, Innate awakening into something
              the god could not own

  # ──────────────────────────────────────────────────────────────
  - id: the_excommunication
    label: "The Excommunication"
    description: |
      Formal severance from the apparatus. Different from
      bargained_for_v1's Severance — the god isn't being broken
      from; the character is being expelled from a community.
      May be initiated by the apparatus (formal action) or by the
      character (open break). The god remains; the character is
      simply no longer part of the feeding.
    when_triggered: |
      Standing falls below threshold_lower (automatic), OR after
      a clear_loss in The Audit, OR character-initiated as
      proactive break.
    resource_pool:
      primary: standing
      secondary: identity
    stakes:
      declared_at_start: true
      hidden_dimensions: false   # excommunication is procedural, no hidden terms
    valid_moves:
      - accept_the_judgment
      - mount_appeal               # call on hierophant ally if any
      - confess_and_seek_reduction # accept lesser penalty
      - declare_open_break         # voluntarily walk out
      - flee                       # refuse to attend the proceeding
    outcomes:
      - branch: clear_win
        description: |
          You walked out cleanly; the apparatus accepts the parting.
          Rare — clean excommunication is a graceful resolution.
        mandatory_outputs:
          - type: mechanism_revoked
            description: "This apparatus closed forever"
          - type: reputation_tier
            description: "Former clergy of [the apparatus]"
          - type: ledger_bar_set
            bar: standing
            level: 0.0
            description: "Standing zeroed, not collapsed"
        optional_outputs:
          - type: bond
            description: "A bond with whoever stood with you"
          - type: pact_tier
            target_plugin: another_plugin
            description: "A new path opens — another god, another plugin"

      - branch: pyrrhic_win
        description: |
          You walked out, but the apparatus extracted a piece of you.
        mandatory_outputs:
          - type: mechanism_revoked
          - type: scar
            severity: defining
          - type: bond_broken
            description: "Former allies in the apparatus are now distant"
        optional_outputs:
          - type: counter_dispatched
            target: rival_inquisitor
            description: |
              An inquisitor of your former church now hunts you
              (your former apparatus' inquisitor, NOT a rival church)

      - branch: clear_loss
        description: |
          You tried to negotiate the excommunication and failed.
          The apparatus extracts maximum penalty.
        mandatory_outputs:
          - type: faction_standing
            delta: -3
            target_kind: faction
            description: "Standing collapses to lowest possible"
          - type: mechanism_revoked
          - type: scar
            severity: defining
        optional_outputs:
          - type: counter_dispatched
            target: rival_inquisitor
          - type: ledger_lock
            bar: standing
            level: -1.0

      - branch: refused
        description: |
          You backed out of the excommunication at the last
          moment. Returned to the fold. The apparatus knows you
          tried to leave.
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: standing
            delta: -0.10
            description: "You're tainted by the attempt"
          - type: ledger_bar_set
            bar: purity
            level: 0.0
            description: "Must start over with full purification cycle"
        optional_outputs:
          - type: pact_tier
            target_kind: faction
            delta: +1
            description: |
              Forced — extra penance now required to recover
              standing; the apparatus has imposed greater obligations

# ─────────────────────────────────────────────────────────────────────
# REVEAL
# ─────────────────────────────────────────────────────────────────────
reveal:
  mode: explicit
  timing: at_outcome
  format: panel_callout
  suppression: none
  per_branch_iconography:
    clear_win: ✝
    pyrrhic_win: 🕯
    clear_loss: ✝̸
    refused: 🚪

# ─────────────────────────────────────────────────────────────────────
# WORLDBUILDING SLOT
# ─────────────────────────────────────────────────────────────────────
world_layer_required:
  - At least one named god + apparatus per active mechanism
    description: |
      Faction-mechanism world declares the apparatus (the Pale
      Fire Cult, the Eastern Diocese of the Hungering Lord) AND
      the god it serves. A god may be served by multiple
      apparatuses (sects); apparatuses must serve at least one
      god.
  - Each god's register
    description: |
      A short narrator-facing prose block describing the god's
      personality, domain, doctrinal core, and what its hunger
      tastes like. Hungry god is greedy; merciful god is costly
      in mercy; silent god grants only when not asked. Held
      consistently across all workings.
  - Pantheon structure (if multi-god)
    description: |
      Worlds with multiple gods declare relationships — allied
      pantheons (Mars and Venus may co-bless), rival pantheons
      (Hungering Lord and Pale Fire compete for souls), distinct
      pantheons (cannot be invoked together).
  - Liturgical calendar (if time mechanism active)
    description: |
      Festivals, feast days, holy hours. Worlds with active time
      mechanism must declare the cycle — when the gods sleep,
      wake, walk, hunger, are fed.
  - Hunger starting offset
    description: |
      Heavy_metal worlds with stratigraphic register may start a
      god's Hunger at 0.20 — accumulated unfulfilled debts from
      older civilizations. Default 0.0.
```

## Validation Notes

### What this plugin tests against the framework

- ✅ All schema slots populated
- ✅ Six delivery mechanisms supported (the most of any plugin so far) — faction, place, condition, time, relational, native
- ✅ Five classes including a chosen-one-tag-bearing class (Saint/Vessel)
- ✅ Five counter archetypes
- ✅ **Three ledger bars with three different patterns**: bidirectional with thresholds (Standing); world-shared monotonic-up with rare decay (Hunger); bidirectional with cyclical reset (Purity)
- ✅ Plugin-extended OTEL attributes (god_id, apparatus_id, doctrinal_alignment, rite_id)
- ✅ Hard limits (5) including the **multi-plugin interaction limit** (deity_targeted_bargaining is forbidden because that's bargained_for_v1's territory — plugins respect each other's lanes)
- ✅ Narrator register specifying the procedural-bureaucratic voice and the difference between heresy-failure and starvation-failure
- ✅ Confrontations (4) with full 4-branch trees, including The Calling for direct god-contact and The Excommunication for institutional severance
- ✅ All five framework decisions held

### Patterns this surfaces

1. **World-shared ledger bars.** Hunger is shared across all worshippers of a god — different from per-character (Soul/Debt) and per-faction (Standing) and per-item (Bond). Schema needs `scope: world` formally supported. Already added to plugin template.
2. **Rare decay on a world-shared bar.** Hunger decays slightly because *other worshippers feed in the background*. This is the genuine exception to Decision #3's "no decay" rule, and it's contextual: the bar belongs to the world, not the character. Decision #3 applies to *character advancement*; world-state bars are different. Worth clarifying in the framework.
3. **Cyclical reset.** Purity restores at ritual cycle. This is a third bar pattern — bidirectional with periodic reset events. Schema needs `cyclical_reset:` block. Added to plugin template informally.
4. **Multi-plugin lane respect.** Divine forbids deity-targeted bargaining because that's bargained_for_v1's territory. Plugins explicitly cite each other's hard limits — worth formalizing as a pattern: plugins can declare "this kind of working belongs to plugin X."
5. **Chosen-one tag carrier class.** The Saint/Vessel class formally carries `chosen_one_tag: true`. This is the first concrete example of the chosen-one decision (narrative role, not Source) instantiating in a plugin. Pattern works.
6. **Heavy_metal cosmology integration.** Heavy_metal's cosmology mentioned five obligation scales: individual, communal, covenant, divine, stratigraphic. Divine_v1's apparatus_id is the *divine* obligation scale's tracking shape. When `obligation_scales_v1` plugin is drafted, divine_v1 will integrate cleanly via this field.

### Notable distinctness from prior plugins

| Dimension | bargained_for_v1 | item_legacy_v1 | divine_v1 |
|---|---|---|---|
| **Carrier** | Sentient patron | Bounded item | God + apparatus |
| **Mediation** | Direct | Item is itself the channel | Apparatus mediates |
| **Cost shape** | Soul/Debt monotonic | Bond bidirectional | Standing bidirectional + world Hunger |
| **Severance** | Catastrophic | Usually clean | Institutional excommunication |
| **Counter signature** | Severer (cuts chains) | Banehand (unmakes objects) | Eater of Gods (starves the source) |
| **Plot arc** | Pact → Working → Calling → Severance | Finding → Wielding → Reckoning → Renunciation | Rite → Audit → Calling → Excommunication |
| **Failure signature** | Patron displeasure | Item refusal | Heresy + Starvation (two distinct fail modes) |

**All three plugins fit the same framework**, but every dimension feels different. The model holds across three very distinct shapes.

## Open Questions Surfaced

1. **Hunger as world-state.** The bar is shared across worshippers. Multiplayer implications: a divine character's working raises Hunger for ALL other worshippers of that god in the same world. The OTEL panel should show this as a world-level event. Worth checking with Architect.
2. **Decision #3 and world-state bars.** Worth clarifying: outputs to characters are sticky (no decay), but world-state bars representing collective conditions can drift. Add to `confrontation-advancement.md`.
3. **Cyclical reset as a bar pattern.** Should be formalized in the schema as `cyclical_reset:` block. Update plugin template.
4. **Plugin-citing-plugin hard limits.** "deity_targeted_bargaining is forbidden because bargained_for_v1's territory" is a useful pattern. Plugins explicitly delineating their lanes prevents content drift. Pattern worth naming and documenting.
5. **Saint/Vessel chargen path.** The class requires `chosen_by_god` — narrative-only at chargen. Worlds need to clarify whether players can SEEK to be Saint (rare) or only have it bestowed. Defer to world-layer decisions.

## Three-plugin coverage check

With bargained_for + item_legacy + divine, plugin coverage spans:
- ✅ Sentient-patron magic with personal contract (bargained_for)
- ✅ Object-bound magic with NPC personalities (item_legacy)
- ✅ Institutional worship-economy magic (divine)
- ⏳ Native/innate magic (innate_developed_v1) — TODO
- ⏳ Inventor/craft magic (mccoy_v1) — TODO
- ⏳ Acquired/mutation magic (mutation_v1) — TODO
- ⏳ Learned ritual magic (learned_ritual_v1) — TODO

**Three more plugins would saturate the napkin's eight Sources.** The framework has held across the three drafted; high confidence the remaining four will fit.

## Next Concrete Moves

- [ ] **Architect**: review world-shared ledger bars, cyclical reset, plugin-citing-plugin patterns. Three framework refinements ready to fold in.
- [ ] **GM**: draft `obligation_scales_v1` plugin (heavy_metal's signature) — integrates with divine_v1's apparatus_id. Validates plugin-on-plugin integration.
- [ ] **GM**: draft `innate_developed_v1` next — covers Force/bending/witcher-mutations/Avatar bending. Major coverage gap.
- [ ] **GM**: instantiate concrete world example. The Hungering Lord's Eastern Diocese (heavy_metal's The Long Reckoning), or the Pale Fire Cult (low_fantasy), or the Catholic apparatus at high gothic (victoria).
- [ ] **UX (Buttercup)**: panel mock for the three-bar divine display (Standing, Hunger, Purity) — significantly different visual texture than bargained_for's two-bar or item_legacy's two-bar.
