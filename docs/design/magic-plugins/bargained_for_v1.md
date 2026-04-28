# Plugin: bargained_for_v1

**Status:** Draft, 2026-04-28
**Source:** `bargained_for` (napkin)
**Genres using:** heavy_metal, victoria-high-gothic, low_fantasy-with-pacts
**Companion docs:** `../magic-taxonomy.md`, `../visible-ledger-and-otel.md`, `../confrontation-advancement.md`, `README.md` (this dir)

## Identity

Bargained-For magic is Faustian. The resource is granted by an external, sentient, self-interested account-holder in exchange for *something the character has, will have, or will become*. The grant is never free, the bill always comes due, and the patron is more powerful than the bargainer in at least one important way.

Three things distinguish this plugin from others:

1. **The patron has agency.** Unlike Innate (which is internal), Item-based (which is inert), or Learned (which is technique), Bargained-For magic answers to *someone who can refuse, modify, or revoke*. Reliability is `negotiated`.
2. **Every working bills a ledger that rises across sessions.** Soul/Debt does not decay (Decision #3). The character carries every pact-use forever.
3. **The pact itself is a contract with terms.** Both parties are bound. The character cannot unilaterally void the pact; severance is its own confrontation, with catastrophic stakes.

## Plugin Definition

```yaml
plugin: bargained_for_v1
status: draft
genres_using:
  - heavy_metal           # signature plugin; default for any caster build
  - victoria              # only at gothic ≥ 0.6 (high gothic worlds)
  - low_fantasy           # for the standing-stones / nameless-spirits register

source: bargained_for     # napkin Source

# ─────────────────────────────────────────────────────────────────────
# DELIVERY MECHANISMS — worlds pick which to activate
# Each mechanism unlocks a different plot engine.
# ─────────────────────────────────────────────────────────────────────
delivery_mechanisms:
  - id: faction
    archetype: pact_guild
    description: |
      An institutional pact-broker that witnesses, enforces, and collects.
      The Guild has chapters, hierarchies, internal politics, and rivalries
      with other plugin-hosting institutions (the Divine apparatus, etc.).
    npc_roles: [broker, witness, collector, severer, inner_circle]
    plot_engine: politics, NPC dispatch, faction-rank arcs, betrayal
    canonical_examples:
      - "The Bargainers Guild (heavy_metal — The Long Reckoning)"
      - "The Lodge of the Six (low_fantasy — eldritch standing-stones cartel)"

  - id: place
    description: |
      The pact is locus-bound. The crossroads at midnight, the cracked
      altar, the burned tree, the haunted millpond. To bargain you must
      go *there*. Going there twice has compounding cost; the place
      remembers.
    plot_engine: pilgrimage, territorial control, geography-as-character
    canonical_examples:
      - "The crossroads at midnight (folk Faustian)"
      - "The Old Altar in the burned wood (heavy_metal frontier)"
      - "The cliff above the locked house (victoria gothic)"

  - id: relational
    description: |
      Direct personal pact with a non-faction entity — fae, ancestral
      ghost, bound spirit, forest god, named demon, the thing in the
      lake. There is no Guild between you. The relationship is the
      contract. Severing means betraying someone, not resigning.
    plot_engine: patron-protégé arcs, bonds-and-betrayals, the friendship-cost
    canonical_examples:
      - "A character's compact with the spirit of a place"
      - "An inherited fae bond from a grandmother"
      - "The unnamed thing in the manor's east wing (victoria)"

  - id: condition
    description: |
      The pact only opens (or only fires) under specific player-state.
      You must have buried someone you loved. You must have fasted forty
      days. You must have shed your own blood within the hour. The
      condition is the cost paid in advance for access.
    plot_engine: penance arcs, self-imposed transformation, ritual purity
    canonical_examples:
      - "The grief-pact: only available after a confirmed loss"
      - "The blood-pact: only fires within an hour of self-wounding"

  - id: time
    description: |
      The pact is calendar-gated. Once-a-century alignment, full moon,
      eclipse, jubilee year. Less common; usually combined with another
      mechanism (place + time = "the crossroads at the equinox").
    plot_engine: deadlines, cyclical urgency, missed-window dread
    canonical_examples:
      - "The dark of the moon, never any other night"
      - "The jubilee year — every fiftieth year the books are settled"

# Mechanisms NOT supported by this plugin:
# - native: Bargained-For is by definition external; native is its opposite
# - discovery: too passive — discovering a pact is a relational/place hook,
#   not a delivery mechanism
# - cosmic: too ambient; Bargained-For requires specific contractual moment

# ─────────────────────────────────────────────────────────────────────
# CLASSES — player-build options that draw from this plugin
# ─────────────────────────────────────────────────────────────────────
classes:
  - id: warlock
    label: Warlock
    requires: [pact_at_chargen]
    pact_visibility_to_player: partial
    typical_mechanisms: [faction, relational]
    narrator_note: |
      Knows what they bargained for; doesn't fully know what they
      bargained with. The patron's name is partially hidden until
      higher tiers.

  - id: pact_priest
    label: Pact-Priest
    requires: [pact_at_chargen, faction_membership]
    pact_visibility_to_player: full
    typical_mechanisms: [faction]
    narrator_note: |
      Institutional. The Guild is their employer. Knows the contract,
      the chain of command, the going rates. Moral weight differs from
      Warlock — Pact-Priests are professionals.

  - id: soul_trader
    label: Soul-Trader
    requires: [pact_at_chargen]
    pact_visibility_to_player: full
    typical_mechanisms: [faction, relational]
    narrator_note: |
      Brokers pacts FOR OTHER CHARACTERS. The Soul-Trader's own pact
      is the *license to broker*. They take a commission. NPCs come
      to them. They are loathed and useful.

  - id: crossroads_walker
    label: Crossroads-Walker
    requires: [pact_at_chargen]
    pact_visibility_to_player: minimal
    typical_mechanisms: [place, relational, condition]
    narrator_note: |
      The lone bargainer. No Guild, no formal contract — just a deal
      made in a desperate moment that the world has now decided to
      honor. Rural, frontier, rogue. The most narrative variant.

# ─────────────────────────────────────────────────────────────────────
# COUNTERS — character archetypes that oppose this plugin
# These are NPCs the GM can dispatch as confrontation outputs
# ─────────────────────────────────────────────────────────────────────
counters:
  - id: severer
    label: The Severer
    description: |
      Specialist in cutting obligation chains. Knows the metaphysics
      of pact-binding intimately. Will die for a fee or a cause.
      Engaging a Severer is fatal to caster if successful — the chain
      is cut by tearing the soul-anchor out.
    plot_use: |
      Dispatched against caster as `counter_dispatched` output.
      Also serves as ally on a Severance confrontation when the
      character wants OUT of their own pact.

  - id: account_holder_revoker
    label: The Patron Themselves
    description: |
      The patron arrives in person to revoke, modify, or collect. This
      is The Calling confrontation made physical. Always more powerful
      than the bargainer in at least one important way.
    plot_use: |
      Drives The Calling confrontation. Output of certain pyrrhic_win
      and clear_loss branches.

  - id: inquisitor
    label: The Inquisitor
    description: |
      Institutional anti-pact agent — church, secular authority, rival
      Guild. Hunts pact-bearers as heretics, criminals, or competitors.
    plot_use: |
      Dispatched as `counter_dispatched` when the world's
      `visibility: persecuted` setting is active.

  - id: rival_pact_bearer
    label: The Rival
    description: |
      Another character with their own pact whose patron's interests
      conflict with yours. Often a former friend or sibling-in-pact.
    plot_use: |
      `enemy_made` output. The most narrative-rich counter — they
      have their own ledger, their own arc.

  - id: witness
    label: The Witness
    description: |
      Someone who was present when the pact was made and now holds
      leverage. Not a magical opponent — a human one with a secret.
    plot_use: |
      `secret_known` against the character; can become `enemy_made`
      via blackmail-shaped confrontation.

# ─────────────────────────────────────────────────────────────────────
# LEDGER BARS — what this plugin contributes to the visible ledger
# ─────────────────────────────────────────────────────────────────────
ledger_bars:
  - id: soul_debt
    label: "Soul / Debt"
    color: ember
    scope: character           # character-bound; you carry your own bill
    threshold: 1.0
    consequence_on_fill: |
      The patron arrives to collect. Triggers The Calling confrontation
      automatically at session start of the next session, OR mid-session
      at narratively appropriate moment (GM choice).
    decay_per_session: 0.0     # Decision #3 — does not decay
    starts_at_chargen: 0.05    # the chargen pact itself costs a sliver

  - id: obligation
    label: "Obligation"
    color: iron
    scope: faction             # tracked per-faction (Bargainers Guild
                               # standing accumulates separately from
                               # the Lodge of the Six standing)
    threshold: 1.0
    consequence_on_fill: |
      The faction calls in their full claim. The character is the
      resource of the faction for the duration of one major arc.
      Refusing triggers `mechanism_revoked` permanently.
    decay_per_session: 0.0
    starts_at_chargen: 0.0     # only accrues from faction-mediated workings

# ─────────────────────────────────────────────────────────────────────
# OTEL SPAN SHAPE — what the narrator must emit per working
# ─────────────────────────────────────────────────────────────────────
otel_span:
  span_name: magic.working
  required_attributes:
    - working_id
    - plugin                   # always: bargained_for_v1
    - source                   # always: bargained_for
    - declared_effect
    - domains
    - modes
    - debited_costs            # at minimum: { soul_debt: <delta> }
    - mechanism_engaged        # one of: faction|place|relational|condition|time
    - mechanism_target         # typed payload — see visible-ledger-and-otel.md
    - patron_id                # which named patron answered
    - reliability_roll         # negotiated by default
    - world_knowledge_at_event
    - visibility_at_event
  optional_attributes:
    - witnesses_present        # who saw the working — feeds Witness counter
    - confrontation_id         # if invoked during a confrontation
    - confrontation_branch     # if confrontation has resolved
  on_violation: gm_panel_red_flag
  yellow_flag_conditions:
    - "narration implies bargain-magic but no span fires"
    - "patron_id is absent (narrator hasn't named who answered)"
    - "mechanism_engaged is absent or set to a non-permitted value"
  red_flag_conditions:
    - "debited_costs is empty (a free Bargained-For working — never)"
    - "mechanism_engaged set to native, discovery, or cosmic"
    - "patron_id references a patron not declared in the world tuple"
  deep_red_flag_conditions:
    - "the working violates a hard_limit (resurrection, transferable pact, etc.)"

# ─────────────────────────────────────────────────────────────────────
# HARD LIMITS specific to bargained_for (above genre baseline)
# ─────────────────────────────────────────────────────────────────────
hard_limits:
  inherits_from_genre: true
  additional_forbidden:
    - id: kill_the_patron
      description: |
        No bargain that targets the patron's existence. The patron is
        more powerful than the bargainer in at least one important way;
        the contract cannot include the patron's death as deliverable.
    - id: retroactive_pact
      description: |
        No bargaining for what already happened. Pacts bind future
        reality, not past. ("Make my dead wife alive" is forbidden;
        "ensure my next child lives" is allowed.)
    - id: transferable_without_consent
      description: |
        A pact cannot be transferred to another character without the
        patron's explicit ratification. Inherited pacts (the
        Crossroads-Walker's grandmother) are valid only if the patron
        chose to maintain the line.
    - id: bargained_for_resurrection
      description: |
        The genre-level resurrection forbidden is amplified for this
        plugin specifically. Bargained-For resurrection is the most
        deeply-feared variant; if a world entertains resurrection at
        all, it CANNOT be via this plugin. Use Divine or Innate paths.

# ─────────────────────────────────────────────────────────────────────
# NARRATOR REGISTER — prose voice when this plugin fires
# ─────────────────────────────────────────────────────────────────────
narrator_register: |
  Every working is witnessed. The narrator must convey the patron's
  attention — even when the patron does not appear, their judgment
  hangs over the working like a pressure. Costs surface in the same
  beat as effects: the patron grants, but the bill is named alongside.

  The patron has personality. Bargained-For magic is never neutral
  delivery — the patron is amused, displeased, hungry, magnanimous,
  bored, jealous. The narrator gives the patron a register and holds
  it consistently across workings.

  Pact-language is precise. "The patron grants" — not "your magic
  succeeds." "The bill rises" — not "you spend mana." "The chain
  tightens" — not "you've leveled up." Pacts are felt as social
  contracts gone metaphysical.

  At higher Soul/Debt fills, the narrator surfaces the patron's voice
  more directly. Whispers. A felt hand on the shoulder. The patron's
  name half-spoken in the character's own thoughts. The bill arriving
  is never a surprise; the player has been hearing it coming.

# ─────────────────────────────────────────────────────────────────────
# CONFRONTATIONS — see ../confrontation-advancement.md for schema
# ─────────────────────────────────────────────────────────────────────
confrontations:

  # ──────────────────────────────────────────────────────────────
  - id: the_bargain
    label: "The Bargain"
    description: |
      Making a new pact, or extending an existing one. The character
      proposes terms or accepts terms; the patron answers. Stakes are
      what is gained vs. what is owed.
    when_triggered: |
      Player declares intent to bargain (chargen, in-play moment of
      desperation, faction-mediated transaction). Cannot be triggered
      retroactively to explain a power.
    resource_pool:
      primary: obligation     # the faction-or-patron claim being negotiated
      secondary: vitality     # how much of yourself you're willing to commit
    stakes:
      declared_at_start: true
      hidden_dimensions: false  # The Bargain is the ONE confrontation where
                                # all terms are surfaced; no hidden cost
    valid_moves:
      - declare_terms
      - push_for_more
      - accept_lesser
      - swear_blood            # commit body — escalates stakes
      - invoke_witness         # bring in a NPC witness for leverage
      - walk_away
    outcomes:
      - branch: clear_win
        description: "You got what you wanted; the bill is fair."
        narrative_shape: |
          The patron grants on the terms named. Both parties signed.
          The character leaves the bargain heavier but not broken.
        mandatory_outputs:
          - type: pact_tier
            delta: +1
          - type: faction_standing
            delta: +1
            target_kind: faction       # if mechanism_engaged == faction
          - type: bond
            target_kind: patron
            description: "Pact-bond established with named patron"
        optional_outputs:
          - type: item_bond
            description: "A pact-token (ring, scar, mark) bonds to character"
          - type: ally_named
            description: "Another pact-bearer becomes an ally via shared standing"

      - branch: pyrrhic_win
        description: "You got it, but the bill is heavier than you understood."
        narrative_shape: |
          The patron grants — but the terms accepted included something
          the character will only realize the cost of later. A
          favored-NPC's life. A piece of identity. A future the character
          will not have.
        mandatory_outputs:
          - type: pact_tier
            delta: +1
          - type: scar
            severity: major
            axis: psychic
            description: "A felt mark; the character knows something is gone"
          - type: ledger_lock
            bar: obligation
            level: 0.7
            description: "An obligation bar locks high; cannot be discharged this session"
        optional_outputs:
          - type: counter_dispatched
            target: severer
            description: "A Severer noticed the working and is now interested"
          - type: bond_broken
            description: "Someone in your life was the price; the bond is gone"

      - branch: clear_loss
        description: |
          The pact didn't take, OR the patron asked too much and you
          couldn't deliver, OR the terms were rejected.
        narrative_shape: |
          The patron does not grant. The character is exposed — they
          tried to bargain and were refused. Whatever they came to
          buy, they leave without. Their reputation is altered.
        mandatory_outputs:
          - type: scar
            severity: major
            axis: psychic
            description: "The shame of the refused bargain"
          - type: faction_standing
            delta: -1
            target_kind: faction
          - type: bond_broken
            target_kind: patron
            description: "The patron will remember the failed approach"
        optional_outputs:
          - type: enemy_made
            target: the_patron_themselves
            description: "If the character pushed too hard, the patron is now an active antagonist"
          - type: mechanism_revoked
            description: "This delivery mechanism (faction or place or...) is closed to the character"

      - branch: refused
        description: "You walked away. The Guild remembers."
        narrative_shape: |
          The character stepped to the threshold and stepped back.
          Sometimes virtue, sometimes failure of nerve, sometimes
          the right call. The character is intact but altered by
          the encounter.
        mandatory_outputs:
          - type: faction_standing
            delta: -1
            target_kind: faction
          - type: scar
            severity: minor
            axis: pride
            description: "A felt mark of doubt or pride, depending on framing"
        optional_outputs:
          - type: bond
            description: "A bond with whoever pulled the character back from the brink"

  # ──────────────────────────────────────────────────────────────
  - id: the_working
    label: "The Working"
    description: |
      Invoking the pact's granted power for a specific use. Lower
      stakes than The Bargain (no new contract is being formed) but
      cumulative — every working bills the ledger and the bill never
      decays.
    when_triggered: |
      Player declares use of bargain-derived power. Or the character
      is in a confrontation where the only resolution-path uses pact
      power.
    resource_pool:
      primary: soul_debt
      secondary: vitality
    stakes:
      declared_at_start: false  # the cost is announced at outcome,
                                # but the cost level is uncertain at start
      hidden_dimensions: true   # the patron may bill more than expected
    valid_moves:
      - invoke_routine          # small, known cost
      - invoke_full             # big, larger cost
      - hedge                   # ask for less, accept lower effect
      - amplify_via_ritual      # spend time + components for cost reduction
      - stop_mid_working        # abort; partial cost
    outcomes:
      - branch: clear_win
        description: "The working fires; the bill is what you expected."
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: soul_debt
            delta: 0.15
        optional_outputs:
          - type: affinity_tier
            description: "Tick toward affinity tier-up if applicable"
          - type: bond
            target_kind: patron
            description: "Pact-bond deepens (within character)"
          - type: scar
            severity: minor
            description: "A small visible mark of the working — pact-stigma"

      - branch: pyrrhic_win
        description: "The working fires, but the patron billed more than you bargained for."
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: soul_debt
            delta: 0.30          # higher than expected
          - type: scar
            severity: major
            description: "A visible cost the character didn't anticipate"
        optional_outputs:
          - type: counter_dispatched
            target: severer
          - type: ledger_lock
            bar: soul_debt
            level: 0.85
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.05

      - branch: clear_loss
        description: |
          The working fails to fire OR fires wrong. The patron did not
          grant. Maybe they're displeased; maybe they're occupied;
          maybe the character has lost standing without knowing it.
        mandatory_outputs:
          - type: scar
            severity: psychic
            description: "The character reached and the patron didn't answer"
          - type: bond_broken
            target_kind: patron
            description: "Trust in the pact is eroded"
        optional_outputs:
          - type: faction_standing
            delta: -1
            target_kind: faction
          - type: mechanism_unlocked
            description: |
              Sometimes failure reveals an alternative path — the
              character tried the pact, it didn't fire, and they
              improvised an alternative. A new delivery mechanism
              opens (a place, a relational entity) as the working
              gets re-routed.

      - branch: refused
        description: "You held back; you didn't invoke even when desperate."
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: vitality
            delta: 0.15
            description: "The situation cost you physically because you didn't reach"
          - type: reputation_tier
            description: "People noticed you didn't use your power"
        optional_outputs:
          - type: bond
            description: "A bond with whoever you protected by NOT casting"

  # ──────────────────────────────────────────────────────────────
  - id: the_calling
    label: "The Calling"
    description: |
      The patron summons the character to deliver on the bargain. The
      character is no longer the customer — they are the resource
      being collected. Stakes are very high. This is when bills
      genuinely come due. Triggered narratively or by Soul/Debt
      reaching threshold.
    when_triggered: |
      Soul/Debt bar at 1.0 (automatic), OR narrator-triggered at
      pivotal moments (the patron has decided to act on the contract),
      OR character-triggered (the character requests an audience to
      renegotiate).
    resource_pool:
      primary: soul_debt
      secondary: identity        # tracked as OCEAN drift potential
    stakes:
      declared_at_start: true    # the patron names what they want
      hidden_dimensions: true    # the patron may name more than they reveal
    valid_moves:
      - accept_terms
      - counter_propose
      - delay                    # buy time at higher cost
      - sacrifice_other          # offer someone else as the deliverable
      - refuse                   # open break with the patron
    outcomes:
      - branch: clear_win
        description: "You delivered what was asked, on terms you can live with."
        mandatory_outputs:
          - type: pact_tier
            delta: +1
            description: "The character is now in deeper standing — trusted"
          - type: bond
            target_kind: patron
            description: "Pact-bond deepens significantly"
          - type: ledger_bar_discharge
            bar: soul_debt
            level: 0.4            # the bill is paid down meaningfully
        optional_outputs:
          - type: mechanism_unlocked
            description: "Earned access to deeper bargains (Inner Sanctum)"
          - type: faction_standing
            delta: +2
            target_kind: faction

      - branch: pyrrhic_win
        description: "You delivered, but the cost was someone you loved or a defining piece of yourself."
        mandatory_outputs:
          - type: bond_broken
            description: "A non-patron NPC bond is severed (they paid the price)"
          - type: scar
            severity: defining
            description: "A mark visible to everyone who knows the character"
          - type: pact_tier
            delta: +1
        optional_outputs:
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.10
            description: "The character is becoming someone harder"
          - type: counter_dispatched
            target: rival_pact_bearer
            description: "Someone has seen the character cross a line"

      - branch: clear_loss
        description: |
          You couldn't deliver, or you tried and failed. The patron's
          claim is unsatisfied. The character has not refused (open
          break) but they have failed to perform. The patron extracts
          consequence.
        mandatory_outputs:
          - type: ledger_lock
            bar: soul_debt
            level: 1.0
            description: "Maxed out — the patron has the character on a leash"
          - type: mechanism_revoked
            description: "Whichever mechanism brought the character to the Calling is now closed"
          - type: scar
            severity: defining
        optional_outputs:
          - type: counter_dispatched
            target: severer
            description: "A Severer is now hunting the character"
          - type: enemy_made
            target: the_patron_themselves

      - branch: refused
        description: "You said no, openly, to the patron. An open break."
        narrative_shape: |
          This is the most dramatic branch. The character has chosen
          freedom over power. The patron's enforcers come immediately;
          the character may not survive the session.
        mandatory_outputs:
          - type: mechanism_revoked
            description: "Permanently closed for this character — the pact is broken"
          - type: counter_dispatched
            target: account_holder_revoker
            description: "The patron themselves arrives, OR sends their highest-rank enforcer"
          - type: reputation_tier
            description: |
              The character is now legendary or hunted, depending on
              context — the one who said no to that patron
        optional_outputs:
          - type: bond
            description: "A bond with anyone who stood with the character at the moment of refusal"

  # ──────────────────────────────────────────────────────────────
  - id: the_severance
    label: "The Severance"
    description: |
      Attempting to break the pact entirely. Catastrophic stakes.
      Often involves a Severer NPC — as ally (helping the character
      cut) or as enemy (the patron's own Severer-equivalent).
    when_triggered: |
      Character declares intent to break the pact. Often follows
      a clear_loss in The Calling. May be initiated proactively
      with a Severer's aid.
    resource_pool:
      primary: vitality
      secondary: identity
    stakes:
      declared_at_start: true
      hidden_dimensions: false   # everyone knows what's at stake
    valid_moves:
      - cut_with_severer         # ally-Severer helps; tactical
      - confront_patron_directly # face-to-face renunciation
      - exploit_loophole         # legal-shaped break via contract terms
      - flee                     # not severance — abandonment
    outcomes:
      - branch: clear_win
        description: "You broke the pact and survived."
        narrative_shape: |
          The character is free — but the chain ripped out a piece
          of them. They are smaller, harder, and finally their own.
          Power lost; agency regained.
        mandatory_outputs:
          - type: mechanism_revoked
            description: "This pact-mechanism is gone. Power lost."
          - type: scar
            severity: defining
            description: "Multiple scars — the chain ripped"
          - type: bond_broken
            target_kind: patron
            description: "Decisively"
          - type: ledger_bar_discharge
            bar: soul_debt
            level: 1.0
            description: "Bar zeroed — the bill is null because the contract is null"
        optional_outputs:
          - type: pact_tier
            target_plugin: another_plugin
            description: "A new path opens — an Innate awakening, an Item adoption, a Divine calling"
          - type: bond
            target_kind: severer
            description: "The Severer who helped is now a permanent ally"

      - branch: pyrrhic_win
        description: "You broke it, but at terrible cost beyond your own."
        mandatory_outputs:
          - type: mechanism_revoked
          - type: scar
            severity: defining
          - type: bond_broken
            description: "The patron AND someone else who paid the price"
        optional_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: -0.15
            description: "The character is permanently more closed"
          - type: enemy_made
            target: severer
            description: "The Severer who helped now wants the price they were promised"
          - type: counter_dispatched
            target: account_holder_revoker
            description: "The patron's revenge in motion"

      - branch: clear_loss
        description: |
          You failed to break it, AND tried. The patron knows now.
          The pact is reinforced involuntarily.
        mandatory_outputs:
          - type: pact_tier
            delta: +2            # forced deeper
            description: "You are now more bound, not less"
          - type: scar
            severity: defining
          - type: faction_standing
            delta: -3
            description: "Collapsed to lowest possible standing"
        optional_outputs:
          - type: counter_dispatched
            target: severer
            description: "The patron has dispatched a Severer of their own"
          - type: ledger_lock
            bar: soul_debt
            level: 1.0

      - branch: refused
        description: "You backed out of the Severance attempt at the last moment."
        mandatory_outputs:
          - type: scar
            severity: minor
            axis: pride
            description: "The shame of attempted-and-aborted severance"
          - type: bond_broken
            description: "Whoever was helping the character sever now distrusts them"
        optional_outputs:
          - type: pact_tier
            delta: +1
            description: "The patron sees the weakness; the chain tightens slightly"

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

# ─────────────────────────────────────────────────────────────────────
# WORLDBUILDING SLOT — what worlds must instantiate
# ─────────────────────────────────────────────────────────────────────
world_layer_required:
  - At least one named patron per active mechanism
    description: |
      A faction-mechanism world declares the Bargainers Guild's
      named chapter. A relational-mechanism world declares the
      named entity (the thing in the lake, the grandmother's fae,
      etc.). A place-mechanism world names the location.
  - Soul/Debt starting offset
    description: |
      Some worlds (heavy_metal "stratigraphic" register) start the
      Soul/Debt bar at 0.10 even at chargen — the world's accumulated
      pact-history weighs on every new bargainer. Default 0.05.
  - Patron register
    description: |
      Each named patron has a personality register the narrator must
      hold consistently across all workings — amused, displeased,
      hungry, magnanimous, jealous. World declares.
```

## Validation Notes

This plugin captures:

- ✅ All 8 napkin Source axes (here: bargained_for)
- ✅ Multiple delivery mechanisms (5 of 8 supported, 3 explicitly excluded with rationale)
- ✅ Class/archetype mapping (4 classes, each with mechanism affinity and pact-visibility level)
- ✅ Counter archetypes (5, each with description and plot-use)
- ✅ Visible ledger bars (2, both with no-decay rule and threshold consequences)
- ✅ OTEL span shape (required, optional, yellow/red/deep-red flag conditions)
- ✅ Hard limits beyond genre baseline (4, with rationale each)
- ✅ Narrator register (specific to bargain-language)
- ✅ Confrontations (4 confrontation types, each with full 4-branch outcome trees)
- ✅ Mandatory output on every branch (Decision #1)
- ✅ Failure-advances on clear_loss and refused branches (Decision #4)
- ✅ Player-facing reveal (Decision #2 — explicit, at_outcome, panel_callout)
- ✅ No-decay outputs (Decision #3 — only ledger_lock has session-bound resolution)
- ✅ Plugin tie-in to confrontations (Decision #5)
- ✅ World-layer instantiation slots specified

## Open Notes for Implementation

1. **`ledger_bar_discharge`** is a new output type used in The Calling's clear_win and The Severance's clear_win branches. Add it to the output catalog in `confrontation-advancement.md` if not already implied by the schema.
2. **`pact_tier` capping behavior** — when at genre-cap, overflow converts to `mechanism_unlocked`. This needs uniform handling across plugins.
3. **`mechanism_unlocked` on clear_loss of The Working** is a deliberately surprising branch — the *failure* opens a workaround. This is the model for "failure advances" giving a *different* output, not just a worse output. Worth highlighting in `confrontation-advancement.md`.
4. **Multi-patron characters.** Can a Soul-Trader broker for multiple patrons simultaneously? Probably yes; tracked as separate `obligation` bars per patron. Schema supports this (scope: faction).
5. **Genre-pack instantiation** — heavy_metal will need its `worlds/the_long_reckoning/magic.yaml` to instantiate this plugin's faction (Bargainers Guild Eastern Chapter), at least one named patron, and the world's Soul/Debt starting offset.

## Next Concrete Moves (post-this-draft)

- [ ] Architect review the schema; flag anything that won't load cleanly into a code-side plugin registry
- [ ] UX (Buttercup) sketch The Bargain confrontation panel — moves, stakes display, outcome callout for each branch
- [ ] Dev (Inigo) — does the OTEL span shape compile cleanly against existing telemetry infrastructure?
- [ ] GM — draft `divine_v1` next as the contrasting plugin (institutional/feeding-economy register), then `item_legacy_v1` as the items-as-NPCs plugin
- [ ] Worldbuild The Long Reckoning's faction & patron instantiation as the first concrete world example
