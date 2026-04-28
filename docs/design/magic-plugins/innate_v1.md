# Plugin: innate_v1

**Status:** Draft, 2026-04-28
**Source:** `innate` (napkin)
**Genres using:** mutant_wasteland (signature), space_opera-Firefly-River, victoria-touched, low_fantasy-bloodline, untrained Force-sensitive register across any space_opera world, the pre-training register of any elemental_harmony bloodline
**Companion docs:** `../magic-taxonomy.md`, `../visible-ledger-and-otel.md`, `../confrontation-advancement.md`, `README.md` (this dir)

## Identity

Innate magic is the source that has nobody on the other end of the line. The character IS the source. There is no patron to negotiate with, no apparatus to channel through, no item to wield, no school to attend. The thing is in you. It fires whether you wanted it to or not.

Three things distinguish this plugin from every other:

1. **There is no account-holder.** Unlike Bargained-For (patron), Divine (deity + apparatus), Item-based (object), or Learned (discipline), Innate has *no external party*. The character cannot petition, negotiate, or appeal — they can only contain or release. Reliability is `wild` by default and `emotion-gated` at higher control tiers.
2. **Severance is impossible.** Where Bargained-For has The Severance and Divine has Renunciation, Innate has no exit door. The character may suppress, may transition to Learned (the wild thing tamed via discipline), may bond into Item-Legacy (the wild thing externalized into a vessel) — but the Innate source itself cannot be returned. You did not borrow it. It is you. *(Cross-plugin transitions out of Innate are how characters change shape — see The Crossing confrontation below.)*
3. **Consent is downstream of stress.** The most distinguishing mechanical claim: under sufficient stress, fear, grief, or condition-trigger, the working fires whether the character wants it to or not. The Innate character is, at the lower control tiers, sometimes a third-person observer of their own power. This is the cliché-judge's load-bearing hook for this plugin — *narration that has the character cleanly choosing every surge violates Innate's nature.*

The plot engine is **identity arcs**: growing into power, surviving the self, the cost-of-being. Witcher-mood at its purest: *you survived this; you're harder now; the body remembers; you trust yourself less.*

## Plugin Definition

```yaml
plugin: innate_v1
status: draft
genres_using:
  - mutant_wasteland     # signature — mutations ARE Innate; "Use Mutation"
                         # combat action is the canonical reference invocation
  - space_opera          # Firefly-River world (acquired-via-experimentation flavor),
                         # untrained-Force-sensitive register across any world
  - victoria             # only at gothic ≥ 0.4 (the "touched" register —
                         # mesmerists, hereditary seers)
  - low_fantasy          # bloodline-awakening for noble lines that didn't
                         # know what they were
  - elemental_harmony    # the pre-training register; bloodline children
                         # before formal Discipline (transitions to learned_v1
                         # via The Crossing)

source: innate           # napkin Source — the character IS the source

# ─────────────────────────────────────────────────────────────────────
# FLAVOR — narrative texture, not framework distinction
# Decision 2026-04-28: "Born with it" vs "acquired via event" are the
# same Source. Both fire identically: character is source, no external
# mediator, identity-cost, severance-impossible. The difference is
# where in the life-arc the awakening sits, not what the magic IS.
# ─────────────────────────────────────────────────────────────────────
flavor:
  - id: born_with
    description: |
      Always had it; the Awakening is the moment the character (or
      world) discovers it. Carrie. Buffy. Allomancy noble lines.
      Bloodline benders before training. The young chosen-one before
      they know.
    plot_register: latent → emergence → reckoning
  - id: acquired_via_event
    description: |
      A specific event installed it — radiation, experimentation,
      lightning strike, dying god's last touch, dimensional contact,
      ritual gone wrong. River Tam, mutant_wasteland mutants,
      Spider-Man's bite, Hulk's gamma exposure.
    plot_register: trauma → emergence → reckoning
  - id: inherited
    description: |
      Bloodline-tracked. Grandmother had it; you have it. The
      ancestral Innate, sometimes silent for generations.
    plot_register: heredity → recognition → reckoning
  - id: returned_wrong
    description: |
      Came back from death, the void, or "elsewhere" with something
      that wasn't there before. Witcher-mutation flavor for those who
      DIDN'T choose it; the Pet Sematary register; the dust-of-elsewhere.
    plot_register: loss → return → estrangement → reckoning

# Flavor is narrator-facing register; does NOT branch the schema.
# All four flavors run the same plugin. Difference shows up only in
# narrator_register choices and the Awakening confrontation's framing.

# ─────────────────────────────────────────────────────────────────────
# DELIVERY MECHANISMS — worlds pick which to activate
# Each mechanism unlocks a different plot engine.
# ─────────────────────────────────────────────────────────────────────
delivery_mechanisms:
  - id: native
    description: |
      The primary mechanism for Innate. The trait is in the character.
      The trait IS the character, in some readings — the line between
      "I have an Innate gift" and "I am a different kind of being" is
      one of the central tensions of this plugin's plot register.
    plot_engine: identity arcs, growing-into-power, the cost-of-self
    canonical_examples:
      - "Carrie's telekinesis (born_with flavor)"
      - "River Tam's psychic edge (acquired_via_event flavor)"
      - "An untrained Force-sensitive child (inherited flavor)"
      - "A mutant_wasteland mutation born of the Drift (returned_wrong)"

  - id: condition
    description: |
      The Innate fires only under specific recurring player-state.
      Blood loss, fasted state, hormonal/menstrual cycle, full moon,
      sleep deprivation, near-death threshold, emotional pitch
      (rage, grief, terror, ecstasy). The Innate is always in you,
      but it only opens when the gate is held.
    plot_engine: self-imposed (and externally-imposed) trigger control,
                 ritual-of-self, the danger of need
    canonical_examples:
      - "The Hulk: only under enough rage"
      - "Bloodline benders gated by sea-cycle / lunar-cycle"
      - "Carrie's telekinesis amplified by emotional crescendo"
      - "Mutant_wasteland mutants whose surge requires injury"

  - id: time
    description: |
      Calendar-gated surge windows. Less common than condition but
      distinct: the body knows the season. Lunar, solstice, equinox,
      anniversary of the trauma, eclipse. Combinations with condition
      are common ("only the full moon while bleeding").
    plot_engine: deadlines, cyclical urgency, the long wait
    canonical_examples:
      - "Hereditary seers whose visions only come on the longest night"
      - "Mutant whose surge cycle tracks the Drift's tide"

  - id: place
    description: |
      The Innate amplifies (or only fires) in specific locations.
      The character is the source, but the locus tunes the signal —
      irradiated zones for mutants, blood-soaked battlegrounds for
      psychics, ancestral keep for inherited bloodlines. Distinct
      from `place` in bargained_for_v1 (where the location IS the
      patron) — here the location is a transformer for what's
      already in the character.
    plot_engine: pilgrimage, territorial pull, the place that calls
    canonical_examples:
      - "The Drift in mutant_wasteland: mutations surge near it"
      - "The ancestral hill where the bloodline first emerged"

  - id: cosmic
    description: |
      Ambient-distributed Innate. Everyone has a touch; some have
      more. Allomancy commoners (faint Snapping potential), mid-Chrome
      neon_dystopia Netrunners (everyone's a little wired), low-gothic
      victoria mesmerism background-radiation. The world's baseline
      is non-zero; the player character is a high read on a continuum,
      not a binary haver.
    plot_engine: low friction at delivery (the resource is just there);
                 always combined with condition or native to give the
                 character story-friction
    canonical_examples:
      - "Allomancy commoner Snapping under trauma"
      - "Mid-Chrome ambient netrunner instinct everyone shares"

  - id: discovery
    description: |
      The Awakening as delivery. Distinct usage from item_legacy_v1's
      discovery (find an object) — here, the character discovers
      themselves. The first surge IS the delivery moment. Plot-shape:
      the dawning recognition of what you are. Always combined with
      one of the other mechanisms; discovery is the entry, not the
      sustaining channel.
    plot_engine: emergence, recognition, the irrevocable knowing
    canonical_examples:
      - "Carrie at the prom (born_with + discovery)"
      - "River cracking in the gorram waiting room"
      - "A bender child realizing the fire isn't her brother's"

# Mechanisms NOT supported by this plugin:
# - faction: Innate has no institutional delivery. Institutions arrive
#   only as counters (the Academy that hunts, the Inhibitor faction
#   that suppresses, the Trainer who offers transition into learned_v1).
#   When the narrator describes "the Academy gave River her power," the
#   Academy is the *acquisition event* (acquired_via_event flavor) and
#   then the antagonist counter — they are not a delivery mechanism in
#   the plugin sense. *(Cliché-judge hook: narration that frames a
#   faction as the ongoing delivery channel for an Innate working is
#   plugin-confused; it's leaking into bargained_for_v1 or divine_v1
#   territory and the OTEL panel should YELLOW-flag.)*
# - relational: Innate has no patron. A mentor, a fellow surger, a
#   bonded twin — these are story-shape relationships, not delivery
#   mechanisms. The mentor opens The Crossing into learned_v1; they do
#   not deliver Innate workings. The bond exists at the narrative layer
#   and via `bond` outputs from confrontations, not as a Source channel.

# ─────────────────────────────────────────────────────────────────────
# CLASSES — player-build options that draw from this plugin
# ─────────────────────────────────────────────────────────────────────
classes:
  - id: the_unawakened
    label: "The Unawakened"
    requires: [innate_at_chargen, awakening_pending]
    pact_visibility_to_player: hidden
    typical_mechanisms: [native, discovery]
    control_tier_at_chargen: 0
    narrator_note: |
      The character does not yet know they are the source. Pre-
      emergence. The first session typically contains an Awakening
      confrontation. The world treats them as a normal person until
      they aren't. Highest-impact class shape — the discovery itself
      is plot. Best used in single-character or pre-arranged
      multiplayer setups.

  - id: the_surger
    label: "The Surger"
    requires: [innate_at_chargen]
    pact_visibility_to_player: full
    typical_mechanisms: [native, condition]
    control_tier_at_chargen: 1
    narrator_note: |
      Wild and reflexive. Has had at least one surge; knows what
      they are. Cannot reliably aim it. Lives with the bills the
      body sends after each surge. This is the canonical Innate
      class — Hulk register, early-Carrie, mutant_wasteland default.

  - id: the_touched
    label: "The Touched"
    requires: [innate_at_chargen]
    pact_visibility_to_player: full
    typical_mechanisms: [native, condition, place]
    control_tier_at_chargen: 2
    narrator_note: |
      Quieter Innate. The empath who reads rooms. The mesmerist who
      can hold a gaze. The seer with reliable but oblique visions.
      Costs are subtler than The Surger — vitality drips rather than
      hemorrhages — but identity-drift is faster. The body holds; the
      self frays. Victoria-touched register. Quiet horror.

  - id: the_reckoner
    label: "The Reckoner"
    requires: [innate_at_chargen, prior_major_surge_in_backstory]
    pact_visibility_to_player: full
    typical_mechanisms: [native, condition]
    control_tier_at_chargen: 2
    narrator_note: |
      Has already broken something — a person, a town, a bond — with
      their Innate. Comes to play with stigma already on the body and
      a reputation already in the world. Lives in the long aftermath.
      Best for late-arc one-shots and Witcher-mood campaigns.

  - id: the_carrier
    label: "The Carrier"
    requires: [innate_at_chargen, returned_wrong_or_acquired_flavor]
    pact_visibility_to_player: partial
    typical_mechanisms: [native, condition, place]
    control_tier_at_chargen: 1
    narrator_note: |
      Acquired the Innate via an event the character does not fully
      understand or remember. The radiation, the experiment, the
      crossing-back. They know they have it; they don't know what it
      IS. Discovery is layered — every surge teaches them something
      new about what was installed. River Tam shape, Spider-Man bite
      shape, mutant_wasteland post-Drift-event mutant shape.

# Notable: there is no "the_master" class in innate_v1. Mastered Innate
# is, by definition, learned_v1's territory. The transition is The
# Crossing confrontation — see below. Innate keeps its plot register by
# refusing to let the character get fully comfortable; promotion to
# control_tier 4 forces a Crossing decision.

# ─────────────────────────────────────────────────────────────────────
# COUNTERS — character archetypes that oppose this plugin
# These are NPCs the GM can dispatch as confrontation outputs
# ─────────────────────────────────────────────────────────────────────
counters:
  - id: the_suppressor
    label: "The Suppressor"
    description: |
      Specialist in dampening Innate at the level of physiology,
      apparatus, or environment. Inhibitor collars, suppressant drugs,
      anti-Innate fields, the iron-and-salt room. Engaging a Suppressor
      typically does not kill the character — it strips them. Worse, in
      some registers, than death.
    plot_use: |
      Dispatched as `counter_dispatched` after a high-stigma public
      surge or a pyrrhic_win on The Surge. May be employed by an
      institutional hunter or a private hire.

  - id: the_hunter
    label: "The Hunter"
    description: |
      Institutional anti-Innate agent — Sentinels, the Academy's
      retrieval team, witch-finders, the iron-bracelet sheriff.
      Hunts Innates as threats, criminals, specimens, or property.
      Differs from the Suppressor in that the Hunter brings the
      character somewhere; the Suppressor turns them off in place.
    plot_use: |
      Dispatched when the world's `world_knowledge: classified` or
      `visibility: persecuted` is active. Persistent threat across
      sessions; the Hunter has access to records and can find you
      again.

  - id: the_amplifier
    label: "The Amplifier"
    description: |
      Institutional or individual anti-self counter. The Academy
      that wants to make River into a weapon. The cult that wants
      your bloodline to wake up. The handler who feeds you the
      drug that makes the surge bigger but the bills worse. They
      do not oppose your power — they opposes your *control* of it.
      They want you uncorked.
    plot_use: |
      Most insidious counter. Often arrives disguised as ally. Drives
      pyrrhic_win branches in The Suppression and The Reckoning.

  - id: the_other
    label: "The Other"
    description: |
      Another Innate of the same shape who has gone further than the
      character has. Predecessor, parallel, dark mirror. May be living
      cautionary tale (high stigma, no friends left, the path the
      character is walking). May be active antagonist (chose
      domination; stronger; offers brotherhood).
    plot_use: |
      Most narrative-rich counter — they have their own ledger, their
      own arc, their own bills. Often the central recurring NPC of an
      Innate-anchored campaign.

  - id: the_betrayer
    label: "The Betrayer"
    description: |
      Trusted person — parent, sibling, friend, lover — who turned
      the character in or sold them out, often "for their own good."
      Innate-specific counter shape: the bond was real, the betrayal
      is also real, neither cancels the other. The X-Men "your own
      mother called the Sentinels" pattern.
    plot_use: |
      `enemy_made` with prior `bond` history. Devastating because the
      character cannot frame the relationship simply. Drives some of
      the heaviest identity-shift outputs in the plugin.

  - id: the_trainer
    label: "The Trainer"
    description: |
      Not strictly a counter — a *cross-plugin path-opener*. The
      mentor who can move the character from innate_v1 to learned_v1
      via The Crossing confrontation. Listed among counters because
      from innate_v1's perspective, the Trainer ends the plugin's
      hold on the character: the wild thing becomes a discipline, and
      a different magic system bills the ledger thereafter. The
      character may grieve the loss of the wild self even when the
      transition was wanted.
    plot_use: |
      Drives optional The Crossing confrontation. Output:
      `mechanism_revoked` (innate_v1) + cross-plugin `pact_tier`
      (learned_v1). The Trainer may also be the Amplifier in disguise
      — sorting them is itself a confrontation.

# ─────────────────────────────────────────────────────────────────────
# LEDGER BARS — what this plugin contributes to the visible ledger
# ─────────────────────────────────────────────────────────────────────
ledger_bars:
  - id: strain
    label: "Strain"
    color: bone
    scope: character
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 1.0
    consequence_on_high_cross: |
      The body fails. Collapse, seizure, blackout, hemorrhage —
      narrator chooses the somatic failure mode appropriate to the
      world. Triggers The Reckoning confrontation at session-end OR
      mid-session (GM choice). Narrative protection: the character
      does not die from strain alone, but they spend time off the
      board.
    decay_per_session: 0.20    # the body recovers some; not all
    starts_at_chargen: 0.0

  - id: stigma
    label: "Stigma"
    color: ash
    scope: character
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.6
    threshold_higher: 1.0
    consequence_on_high_cross: |
      Visible alteration. Eyes change color. Nosebleeds become
      structural. The hair greys. A rune surfaces. Mid-tier stigma
      is "passable with effort" — coats, hats, dim rooms, alibis.
    consequence_on_higher_cross: |
      No longer passable. The character cannot hide what they are
      from anyone who looks. Triggers automatic `world_knowledge`
      shift in any classified-Innate world: the specific people who
      see you now know. Multiple `counter_dispatched` outputs likely
      across subsequent sessions. (Decision #3 — no decay; the body
      has changed.)
    decay_per_session: 0.0     # stigma is permanent — the body remembers
    starts_at_chargen: 0.0     # default; some classes (the_reckoner,
                               # the_carrier with returned_wrong flavor)
                               # may chargen at 0.10–0.30

  - id: dissociation
    label: "Dissociation"
    color: glass
    scope: character
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.6
    threshold_higher: 1.0
    consequence_on_high_cross: |
      The character begins narrating in third person about themselves
      occasionally. The *I* and the *thing in me* drift apart. OCEAN
      drift events fire on subsequent surges (each crossing rolls an
      `identity_shift` output, narrator chosen).
    consequence_on_higher_cross: |
      Identity broken. Triggers The Reckoning confrontation
      automatically. The character may emerge as someone else. Cross-
      plugin transition into Learned (via The Crossing) is unlocked
      OR forced as a salvage; staying Innate at this dissociation
      level is a clear-loss waiting to happen.
    decay_per_session: 0.10    # grounding rituals, sleep, friends — modest
    starts_at_chargen: 0.0

  # OPTIONAL world-shared bar (worlds activate if the genre permits)
  - id: signal
    label: "The Signal"
    color: red_iron
    scope: world               # all Innates contribute; hunters track this
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.7
    threshold_higher: 1.0
    consequence_on_high_cross: |
      Hunters arrive in the region. `counter_dispatched: the_hunter`
      becomes likely on next session start.
    consequence_on_higher_cross: |
      Open hunt declared. Multiple Hunter NPCs active. The world's
      `visibility` shifts toward `persecuted` for the duration.
    decay_per_session: 0.05    # background; the world forgets slowly
    starts_at_chargen: world_default
    activation: |
      Active only in worlds where world_knowledge ∈ {classified,
      esoteric, persecuted}. In acknowledged-Innate worlds (Allomancy
      sanctioned-noble, elemental_harmony Disciplines), this bar is
      not instantiated.
    rises_when: |
      Any Innate character in the world performs a high-visibility
      surge (witnesses present, public location, identifiable
      after-effects). Per-character contributions roll up; the bar
      is NOT character-bound but the character is footprint-recorded.
    note: |
      First world-shared bar in this plugin. Pattern parallels
      divine_v1's Hunger (world-shared, slight decay, character
      contributions persist as outputs even when the bar drifts).

# ─────────────────────────────────────────────────────────────────────
# OTEL SPAN SHAPE — what the narrator must emit per working
# ─────────────────────────────────────────────────────────────────────
otel_span:
  span_name: magic.working
  required_attributes:
    - working_id
    - plugin                   # always: innate_v1
    - source                   # always: innate
    - flavor                   # one of: born_with | acquired_via_event |
                               #         inherited | returned_wrong
    - declared_effect
    - domains                  # which Domain(s) — see manifestation
    - modes                    # reflexive | invoked | (rarely) ritual
    - debited_costs            # at minimum strain or dissociation;
                               # often both. NEVER empty.
    - mechanism_engaged        # one of: native | condition | time |
                               #         place | cosmic | discovery
    - mechanism_target         # see visible-ledger-and-otel.md
    - reliability_roll         # wild by default; emotion-gated at
                               # control_tier ≥ 3
    - control_tier_at_event    # 0–4 — the character's discipline level
    - consent_state            # consented | reflexive | resisted |
                               # surged_against_will
    - world_knowledge_at_event
    - visibility_at_event
  optional_attributes:
    - witnesses_present        # who saw — feeds Signal bar and Hunter dispatch
    - confrontation_id
    - confrontation_branch
    - signal_contribution      # how much the working added to The Signal
                               # (only in worlds where Signal is active)
    - amplification_source     # if `place` mechanism active: which locus?
                               # if `cosmic`: ambient strength index
  on_violation: gm_panel_red_flag
  yellow_flag_conditions:
    - "narration implies an Innate-shaped event but no span fires"
    - "consent_state is absent (was the character choosing? did the
       power surge?)"
    - "flavor is unset (which Innate texture is this?)"
    - "control_tier_at_event is unset"
    - "mechanism_engaged set to faction or relational (out of plugin
       lane — see hard_limits)"
  red_flag_conditions:
    - "debited_costs is empty (a free Innate working — never; the body
       always pays)"
    - "consent_state is `consented` while control_tier < 2 (the character
       is not yet practiced enough to reliably consent — narrator may be
       writing past the character's discipline)"
    - "mechanism_engaged set to faction (institutions are counters, not
       channels — leaking into bargained_for_v1 or divine_v1 territory)"
    - "narration depicts a clean choice to NOT surge under high
       condition-trigger pressure at control_tier ≤ 1 (clichéd
       restraint; narrator should be making it cost)"
  deep_red_flag_conditions:
    - "the working violates a hard_limit (severance, transfer, external
       revocation, deity-targeted)"
    - "the narration depicts the character fully aiming and metering an
       Innate working at control_tier 0 (the Awakening hasn't even
       happened yet — narrator is writing Learned in Innate's clothing)"

# Plugin-specific extensions to the universal magic.working span:
# - flavor (the four narrative textures)
# - control_tier_at_event (the discipline axis)
# - consent_state (whether the character chose this firing)
# - signal_contribution (world-bar rollup)
# These attributes are encouraged for ALL workings in this plugin and
# are the load-bearing fields for the cliché-judge's Innate hooks.

# ─────────────────────────────────────────────────────────────────────
# HARD LIMITS specific to innate (above genre baseline)
# ─────────────────────────────────────────────────────────────────────
hard_limits:
  inherits_from_genre: true
  additional_forbidden:
    - id: clean_severance
      description: |
        You cannot stop being the source. There is no Severance
        confrontation in innate_v1 because there is nothing to sever
        — no chain, no contract, no apparatus. Suppression is
        possible (drugs, dampeners, prosthetic restraint); transition
        is possible (The Crossing into learned_v1 or item_legacy_v1);
        forgetting is impossible. Narration that depicts the character
        "losing their power forever" without an acceptable cross-plugin
        transition or sustained Suppression is wrong.
    - id: external_revocation
      description: |
        No external party can revoke an Innate. There is no patron to
        be displeased, no apparatus to be stripped, no item to be
        taken back. A god cannot un-make a mutant. A Guild cannot
        un-make a seer. Suppression apparatus (Inhibitor collars,
        suppressant drugs) holds the source down; it does not remove
        it. Removing the apparatus restores the source.
    - id: transferable
      description: |
        An Innate cannot be gifted, sold, or transferred to another
        character. (Genetic continuation across generations is not
        transfer — it is independent emergence in the next character.
        Two characters of an inherited bloodline each have their own
        Innate; one does not have the other's.) Apparent transfers
        in fiction (the dying-master scene, the touch-of-power) are
        either (a) Awakening of a latent Innate already present, or
        (b) cross-plugin transition into Item-Legacy with the dying
        master's body or marker as the item.
    - id: deity_targeted
      description: |
        An Innate working cannot have a god as target — neither
        damaging, binding, healing, summoning, nor coercing. Gods are
        divine_v1's territory. An Innate may experience visions of a
        god (the Domain is divinatory) but the working is not directed
        at the god as object.
        references_plugin: divine_v1
    - id: patron_invocation
      description: |
        An Innate working cannot name a patron, broker a deal, or
        invoke an external named entity as the source. There is no
        external entity. Narration that says "the spirits granted
        her this" or "the wolf inside answered her call" is leaking
        into bargained_for_v1 or relational-mediated territory and
        plugin-confused.
        references_plugin: bargained_for_v1
    - id: institutional_delivery
      description: |
        Faction is not a delivery mechanism. An institution may have
        triggered the Innate (acquired_via_event flavor — the Academy)
        but the institution does not channel ongoing workings.
        Narration that describes "the Academy supplies her power" as
        a present-tense delivery is wrong; the Academy is a counter.
    - id: control_at_chargen_above_2
      description: |
        Innate characters cannot start at control_tier 3 or 4. Mastered
        Innate IS Learned. A character who would chargen at high
        control should be built as a learned_v1 character with
        Innate-prerequisite-gate, not as innate_v1. This is the
        load-bearing class boundary between the two plugins.
        references_plugin: learned_v1

# ─────────────────────────────────────────────────────────────────────
# NARRATOR REGISTER — prose voice when this plugin fires
# ─────────────────────────────────────────────────────────────────────
narrator_register: |
  The narrator must always render Innate workings as something
  happening *to* the character first and *through* the character
  second. The body is the larder. The self is the witness. The
  world is the consequence.

  Avoid the verbs of mastery. The character does not "cast," "channel,"
  or "direct." At control_tier 0–1, the character "feels it stir,"
  "loses the room," "notices the air go thin." At tier 2, they
  "lean into it," "open the door a finger's width," "hold what they
  can." Even at tier 3, the language stays near the body — they
  "place the surge," "thread it," "let it run a known length."
  Mastery-language belongs to learned_v1. This plugin's voice is
  always partly third-person about the self.

  Costs surface in the somatic before the social. Strain shows as
  the nosebleed, the buckled knee, the tongue tasting copper. Stigma
  shows in the body before anyone else sees it — the iris darkening,
  the hair coming out grey at the next mirror. Dissociation shows in
  the character's own internal narration drifting into observation —
  *she lifts the boy* before *I lift the boy*.

  Consent is downstream of stress. At low control tier, the working
  surges; the character is not asked. The narrator must respect this
  — *do not* render restraint as a costless act of will at tier 0–1.
  The body answers when the trigger is pulled, even when the character
  doesn't want it to. (Rule of Cool exception: a creative refusal
  that costs Vitality is fine — the character holding it down is
  paying the bill, not skipping it.)

  Witnesses are load-bearing. The Signal bar exists because every
  surge that someone sees has consequence beyond the moment. The
  narrator must name witnesses, even briefly — the kid in the doorway,
  the nurse at the end of the hall, the camera in the corner. The
  panel will read those names later when Hunters arrive.

  Awakening narration (first session for an unawakened character) is
  the highest-stakes prose this plugin asks for. Match the flavor:
  born_with → emergence-shock; acquired_via_event → strange-installation;
  inherited → recognition-shock; returned_wrong → estrangement-from-self.
  All four are losses of the prior self; render the loss before the
  power.

# ─────────────────────────────────────────────────────────────────────
# CONFRONTATIONS — see ../confrontation-advancement.md for schema
# ─────────────────────────────────────────────────────────────────────
confrontations:

  # ──────────────────────────────────────────────────────────────
  - id: the_awakening
    label: "The Awakening"
    description: |
      First surge. Once-per-character, unless campaign structure
      explicitly resets (a returned_wrong character may have a
      second Awakening to a NEW Innate they didn't have before
      crossing back). The discovery of self. Sets the character's
      starting baselines on Strain, Stigma, Dissociation; defines
      the Domain(s) the Innate operates in; locks in the flavor.
    when_triggered: |
      The_unawakened class at chargen plays through The Awakening
      in their first session, narratively triggered by stress. May
      also be triggered for any class as a flashback confrontation
      that resolves into chargen baselines (the_reckoner especially
      benefits from this framing).
    resource_pool:
      primary: dissociation     # the self is being rewritten in real time
      secondary: strain         # the body absorbs the first hit
    stakes:
      declared_at_start: false  # the character does not yet know the stakes;
                                # this is the only confrontation in the
                                # plugin where the player learns the rules
                                # by playing
      hidden_dimensions: true
    valid_moves:
      - flinch_into_surge        # the involuntary one — the safest baseline
      - lean_into_surge          # invite it; pyrrhic-win territory
      - try_to_contain_it        # impossible at tier 0; costs heavily
      - witness_only             # narrative-only — observe what's happening
                                 # to oneself; defers the working but
                                 # commits to dissociation
      - cry_for_help             # name another character; their action
                                 # determines the witness layer
    outcomes:
      - branch: clear_win
        description: |
          The surge happened, the world held its shape, and the
          character is recognizably themselves on the other side.
          Best plausible Awakening. Rare and valuable.
        narrative_shape: |
          The fire in the kitchen blew out. The boy stayed alive.
          The character remembers it. They are different now and
          they know it, and they are still themselves.
        mandatory_outputs:
          - type: pact_tier
            delta: +1
            description: "Innate baseline established at tier 1"
          - type: ledger_bar_set
            bar: stigma
            level: 0.10
            description: "Subtle baseline mark; not yet visible to strangers"
          - type: ledger_bar_set
            bar: strain
            level: 0.30
            description: "First-surge body cost"
          - type: secret_known
            description: "The character now knows what they are"
        optional_outputs:
          - type: bond
            description: |
              The witness who held them after the surge. The first
              person who saw them and stayed. This is one of the most
              load-bearing bonds in any campaign.
          - type: identity_shift
            axis: ocean.openness
            delta: +0.05
            description: "The character has learned a new register of self"

      - branch: pyrrhic_win
        description: |
          The surge worked. Something else broke. A person, an
          object, a relationship. The world tilted.
        narrative_shape: |
          The fire in the kitchen blew out — and the wallpaper
          peeled, the windows cracked, a parent staggered back
          changed. The character knows. So does someone else.
        mandatory_outputs:
          - type: pact_tier
            delta: +1
          - type: ledger_bar_set
            bar: stigma
            level: 0.30
            description: "Visible mark; passable but noticeable"
          - type: ledger_bar_set
            bar: strain
            level: 0.60
            description: "Heavy first-surge body cost"
          - type: scar
            severity: defining
            axis: psychic_or_physical
            description: |
              Narrator-chosen permanent mark; the character may not
              fully understand it yet
          - type: bond_broken
            description: |
              Someone present saw what happened and pulled back.
              A parent, a sibling, a friend — the person who used
              to know them no longer does
        optional_outputs:
          - type: counter_dispatched
            target: the_betrayer
            description: |
              The witness who saw is going to call someone — not
              tonight, but soon. The bond was real; the betrayal
              will be too
          - type: ledger_bar_rise
            bar: signal
            delta: 0.20
            description: "(World-shared, if active) The Signal rises"
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.05

      - branch: clear_loss
        description: |
          The surge fired wrong, or fired against the wrong target,
          or fired against the character's own body. The Awakening
          is a wounding. The character emerges Innate but already
          broken in some way they will carry.
        narrative_shape: |
          The fire in the kitchen did not blow out. The boy did not
          live. Or the boy lived and the character did not — they
          went somewhere during the surge and only most of them came
          back.
        mandatory_outputs:
          - type: pact_tier
            delta: +1
          - type: ledger_bar_set
            bar: stigma
            level: 0.40
          - type: ledger_bar_set
            bar: strain
            level: 0.85
            description: "Near-collapse body cost; recovery takes screen time"
          - type: ledger_bar_set
            bar: dissociation
            level: 0.40
            description: "The character did not all return"
          - type: scar
            severity: defining
            axis: psychic
            description: "The Awakening wound — present in every subsequent surge's narration"
          - type: bond_broken
            description: "Whoever the character was trying to protect; whoever they reached for"
        optional_outputs:
          - type: counter_dispatched
            target: the_hunter
            description: "Public collateral; institutional response begins immediately"
          - type: enemy_made
            description: "Someone present blames the character — perhaps correctly"

      - branch: refused
        description: |
          The character did not surge when they should have. They
          held it down at first-emergence, paying full somatic price
          to NOT do the thing the body wanted to do. The Innate is
          still there; the character has spent something to stay
          unawakened-shaped a little longer.
        narrative_shape: |
          The fire in the kitchen burned, and the boy died, and the
          character did not move because they refused to know what
          they were. They will know later. The body remembers what
          it didn't do.
        mandatory_outputs:
          - type: ledger_bar_set
            bar: dissociation
            level: 0.50
            description: |
              Refusing the Awakening costs MORE than allowing it; the
              character has split from themselves to deny it
          - type: ledger_bar_set
            bar: strain
            level: 0.70
          - type: scar
            severity: major
            axis: pride_and_shame
            description: "The thing the character did not do"
        optional_outputs:
          - type: bond_broken
            description: "Whoever the character could have saved"
          - type: identity_shift
            axis: ocean.neuroticism
            delta: +0.10
            description: "Repressed Innate increases internal pressure"

  # ──────────────────────────────────────────────────────────────
  - id: the_surge
    label: "The Surge"
    description: |
      The everyday Innate confrontation. The trigger pulls; the
      working fires. Stakes are how much you spent, what came out,
      and who saw it. The most-frequently-played confrontation in
      this plugin — most Innate sessions contain at least one.
    when_triggered: |
      Stress condition is met (condition mechanism), location is
      reached (place mechanism), time-window opens (time mechanism),
      or the character chooses to lean in (native mechanism — this
      is the closest Innate gets to deliberate invocation, and at
      control_tier 0–1 even "leaning in" is partly involuntary).
    resource_pool:
      primary: strain
      secondary: dissociation
    stakes:
      declared_at_start: false   # the cost level is uncertain even
                                 # to the character; this is core to
                                 # the plugin's plot register
      hidden_dimensions: true    # the surge may produce more (or less)
                                 # than wanted; reliability is wild
    valid_moves:
      - lean_in                  # accept full surge; uncapped output, full bill
      - throttle                 # try to limit; costs control_tier check;
                                 # may produce less effect AND more cost
      - direct                   # try to aim; control_tier check
      - witness_only             # narrate the surge from outside while
                                 # it happens; reduces dissociation cost
                                 # but raises stigma (more obvious working)
      - hold_it_down             # full Suppression attempt within the
                                 # Surge frame; usually escalates into
                                 # The Suppression as a sub-confrontation
    outcomes:
      - branch: clear_win
        description: |
          The surge fired with intent close to the character's; the
          bill matches the working; nobody important saw who matters.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: strain
            delta: 0.15
        optional_outputs:
          - type: affinity_tier
            description: "Tick toward the Innate-Domain affinity advancing"
          - type: bond
            description: "Someone present helped; a bond forms or strengthens"
          - type: ledger_bar_rise
            bar: stigma
            delta: 0.05
            description: "A small visible cost — the after-tremor"

      - branch: pyrrhic_win
        description: |
          The surge fired bigger than wanted, or aimed wrong, or
          left more witnesses than expected. The character got what
          they reached for; the price is heavier than they were
          ready for.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: strain
            delta: 0.30
          - type: ledger_bar_rise
            bar: stigma
            delta: 0.15
          - type: ledger_bar_rise
            bar: dissociation
            delta: 0.10
          - type: scar
            severity: major
            axis: physical_or_psychic
            description: "A visible cost the character did not anticipate"
        optional_outputs:
          - type: ledger_bar_rise
            bar: signal
            delta: 0.20
            description: "(world-shared, if active) The Signal rises"
          - type: counter_dispatched
            target: the_hunter
            description: |
              A high-visibility surge with witnesses; institutional
              response begins, even if not this session
          - type: identity_shift
            axis: ocean.neuroticism
            delta: +0.05
          - type: bond_broken
            description: "A witness pulled back from the character"

      - branch: clear_loss
        description: |
          The surge fired wrong — overshot, undershot, hit the wrong
          target, hit the character's own body, fired into the floor
          when the threat was overhead. Reliability is wild and the
          wild bit you. The body paid; the mission didn't.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: strain
            delta: 0.40
          - type: ledger_bar_rise
            bar: dissociation
            delta: 0.20
          - type: scar
            severity: major
            description: "The wrong-target wound"
          - type: identity_shift
            axis: ocean.openness
            delta: -0.05
            description: "The character trusts themselves less afterward"
        optional_outputs:
          - type: bond_broken
            description: |
              The character hurt someone they didn't mean to; a bond
              cracks
          - type: counter_dispatched
            target: the_amplifier
            description: |
              Someone watching has noticed the character's lack of
              control and is interested for the wrong reason
          - type: mechanism_unlocked
            description: |
              A condition or place mechanism reveals itself in the
              failure — the character notices that the surge fires
              cleaner near water, or while bleeding, or under
              specific emotional pitch. Wild reliability narrows
              slightly into a known gate.

      - branch: refused
        description: |
          The character held the surge down despite the trigger
          firing. They took the Vitality hit themselves rather than
          let the working land. Costly; sometimes correct.
        mandatory_outputs:
          - type: vitality_cost
            description: |
              A direct Vitality hit not tied to a tracked bar —
              the character paid in body to NOT cast. Narrator-
              chosen severity (bruise, broken vessel, lost
              consciousness for an hour, whatever fits)
          - type: ledger_bar_rise
            bar: strain
            delta: 0.25
            description: "Holding it down costs more than letting it out"
          - type: scar
            severity: minor
            axis: pride_or_shame
            description: |
              Some characters wear refusal as pride; some as shame.
              Narrator-chosen, world-flavored
        optional_outputs:
          - type: bond
            description: "A bond with whoever the character protected by NOT casting"
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.05
            description: "The discipline-of-restraint registers — small but real"

  # ──────────────────────────────────────────────────────────────
  - id: the_suppression
    label: "The Suppression"
    description: |
      A sustained refusal across a scene or sequence — not a single
      missed surge, but actively holding the trigger pressure under
      across a stretch of provocation. Common scene shape: the
      character is in interrogation, in a crowded room, in a place
      where Stigma above the Signal threshold would be catastrophic.
      They must not surge. Whether they can is the confrontation.
    when_triggered: |
      Player declares intent to suppress AND a continuous condition
      meets the trigger threshold AND the scene is structured around
      whether the Innate stays contained. Multi-beat. Strain rises
      every beat.
    resource_pool:
      primary: strain
      secondary: dissociation
    stakes:
      declared_at_start: true    # everyone knows the goal is "do not
                                 # surge"; the question is can the
                                 # character pay the bill
      hidden_dimensions: false
    valid_moves:
      - hold                     # bear the strain; passive
      - ground                   # active grounding ritual — costs time, reduces
                                 # dissociation rise, adds to strain
      - displace                 # redirect surge into a smaller, safer
                                 # outlet (a glass of water boils, a
                                 # nearby object cracks); costs stigma
                                 # but releases pressure
      - lean_on_someone          # an ally helps — bond-token
                                 # consumption, narrator-discretionary
      - break                    # let the surge happen; ends the
                                 # Suppression as a clear_loss branch
                                 # automatically
    outcomes:
      - branch: clear_win
        description: |
          The character held it down across the full scene. Nobody
          saw what they are. The body paid; the world remains
          unaware.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: strain
            delta: 0.40
            description: "Sustained suppression is the most expensive Strain event"
          - type: affinity_tier
            description: |
              Tick toward control tier; if the character has
              repeatedly succeeded at Suppression, they are practicing
              a kind of un-discipline that may eventually unlock The
              Crossing
        optional_outputs:
          - type: bond
            description: "Whoever held space for the character through the scene"
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.05

      - branch: pyrrhic_win
        description: |
          The character held it down — but barely, and someone
          noticed enough to be suspicious. The room is held; the
          secret isn't quite.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: strain
            delta: 0.55
          - type: ledger_bar_rise
            bar: dissociation
            delta: 0.15
          - type: secret_known
            description: |
              ONE person in the scene now suspects (target_kind:
              character — narrator names a specific NPC). Not full
              knowledge — informed suspicion
        optional_outputs:
          - type: counter_dispatched
            target: the_hunter
            description: |
              The suspecting NPC is reporting in. Slow-fuse Hunter
              dispatch — manifests next session
          - type: scar
            severity: minor
            axis: physical
            description: "The suppressed surge etched itself in the body"

      - branch: clear_loss
        description: |
          The character could not hold it. The surge broke through
          mid-scene. Stigma in public, Signal contribution, witnesses,
          the works. The Suppression failed and the world saw.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: strain
            delta: 0.35
          - type: ledger_bar_rise
            bar: stigma
            delta: 0.30
          - type: ledger_bar_rise
            bar: dissociation
            delta: 0.20
          - type: ledger_bar_rise
            bar: signal
            delta: 0.40
            description: "(world-shared, if active) Major Signal contribution"
          - type: scar
            severity: major
        optional_outputs:
          - type: counter_dispatched
            target: the_hunter
            description: "Hunters next session, near-certain"
          - type: bond_broken
            description: "Whoever was depending on the character to hold"
          - type: identity_shift
            axis: ocean.openness
            delta: -0.10
            description: "The character knows they failed; they will trust themselves less next time"

      - branch: refused
        description: |
          The character chose to break early — to let the surge
          happen on their own terms before it broke through their
          terms. Less costly than clear_loss; still a loss of the
          original Suppression goal. A controlled fall versus a
          shove.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: strain
            delta: 0.20
            description: "Less than holding to break would have cost"
          - type: ledger_bar_rise
            bar: stigma
            delta: 0.15
          - type: scar
            severity: minor
            axis: pride_or_pragmatism
            description: |
              The character chose. That registers in the body
              differently than collapse
        optional_outputs:
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.03
            description: "The discipline-of-knowing-when-to-fold"
          - type: bond
            description: |
              An ally who appreciates the controlled break may bond
              — relational rather than romantic

  # ──────────────────────────────────────────────────────────────
  - id: the_reckoning
    label: "The Reckoning"
    description: |
      The Innate-equivalent of Bargained-For's The Calling. Not a
      patron arriving to collect — there is no patron. The
      reckoning is the bill paid in social and identity terms for
      what the character has done with their Innate. Two trigger
      paths: (a) Strain or Dissociation hits 1.0 (mechanical
      forced trigger); (b) the world catches up — Hunters arrive,
      the village confronts, a person you hurt comes back, a
      previous Surge's collateral surfaces.
    when_triggered: |
      Strain ≥ 1.0 (immediate — the body has failed and the
      reckoning is the body's bill arriving), OR Dissociation ≥
      1.0 (immediate — the self has fragmented and the reckoning
      is the splitting of what's left), OR narrator-triggered
      when collateral catches up. Cannot be triggered by player
      request — this is a confrontation that arrives, not one
      the player elects.
    resource_pool:
      primary: dissociation
      secondary: strain
    stakes:
      declared_at_start: true    # the cost is named: face the
                                 # consequences or run from them;
                                 # both have outputs
      hidden_dimensions: true    # the depth of cost depends on
                                 # the character's response
    valid_moves:
      - face_it                  # accept the reckoning fully; engage
                                 # with consequences
      - bargain                  # try to renegotiate the social
                                 # debt — note: this is bargaining
                                 # with PEOPLE, not patrons; stays
                                 # in plugin
      - flee                     # try to escape the reckoning; works
                                 # short-term, fails long-term
      - cross                    # invoke The Crossing into another
                                 # plugin as an alternative path —
                                 # available only at certain tiers,
                                 # see The Crossing confrontation
      - break                    # the character refuses ALL paths;
                                 # fragmentation outcome
    outcomes:
      - branch: clear_win
        description: |
          The character faced the reckoning, paid the social and
          identity bill on terms they could live with. Strain and
          Dissociation discharge meaningfully; the world shifts but
          does not break the character.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: strain
            level: 0.6
            description: "Body recovery via accepting the consequences"
          - type: ledger_bar_discharge
            bar: dissociation
            level: 0.5
            description: "Reintegration via accepting what happened"
          - type: pact_tier
            delta: +1
            description: "The Innate has matured through reckoning"
          - type: bond
            description: |
              Whoever stood with the character through the
              reckoning — almost always; this is one of the
              defining bonds in any innate_v1 campaign
        optional_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: +0.10
            description: "The character is more themselves after"
          - type: reputation_tier
            description: "The character's social standing is now legible — feared, respected, pitied; narrator-chosen by world response"
          - type: mechanism_unlocked
            description: "A new condition or place mechanism becomes available — the body has learned"

      - branch: pyrrhic_win
        description: |
          The character faced it and got through; something they
          loved broke in the process. The bill was named in
          someone's life or a piece of self.
        mandatory_outputs:
          - type: ledger_bar_discharge
            bar: strain
            level: 0.4
          - type: ledger_bar_discharge
            bar: dissociation
            level: 0.3
          - type: pact_tier
            delta: +1
          - type: bond_broken
            description: |
              A specific named bond severed by the reckoning's
              cost. Often the bond that defined the character's
              prior arc
          - type: scar
            severity: defining
            axis: psychic_or_social
        optional_outputs:
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.10
            description: "The character is harder afterward"
          - type: counter_dispatched
            target: the_other
            description: "A predecessor Innate has noticed and may seek the character out — for warning or recruitment"

      - branch: clear_loss
        description: |
          The character could not face it. Tried, failed.
          Fragmentation. The body did not recover; the self did
          not reintegrate; the world has not finished with them.
        mandatory_outputs:
          - type: ledger_lock
            bar: strain
            level: 0.9
            description: "Body locked in damaged state until later confrontation resolves it"
          - type: ledger_lock
            bar: dissociation
            level: 0.85
            description: |
              Self locked fragmented. Narration may render the
              character partly third-person until resolved
          - type: scar
            severity: defining
            axis: psychic
          - type: identity_shift
            axis: ocean.neuroticism
            delta: +0.15
            description: "Long-term increase in dysregulation"
        optional_outputs:
          - type: counter_dispatched
            target: the_amplifier
            description: |
              An Amplifier circles — the character is exactly the
              kind of broken Innate they prey on
          - type: enemy_made
            description: |
              Someone the character hurt has decided to dedicate
              themselves to a long answer
          - type: mechanism_revoked
            description: |
              A delivery mechanism — typically place — closes:
              the character cannot return there

      - branch: refused
        description: |
          The character fled. The reckoning is delayed, not
          discharged. They survive the session but the bill has
          rolled forward and accrued interest.
        mandatory_outputs:
          - type: ledger_lock
            bar: dissociation
            level: 0.7
            description: "Refusal locks dissociation; cannot drop below this floor until faced"
          - type: scar
            severity: minor
            axis: shame
            description: "The thing the character ran from"
          - type: ledger_bar_rise
            bar: signal
            delta: 0.30
            description: "(world-shared, if active) the unaddressed reckoning amplifies"
        optional_outputs:
          - type: counter_dispatched
            target: the_betrayer
            description: |
              A previously-loved bond becomes the one who calls
              the Hunters; betrayal because the character left
              them holding the bag
          - type: bond_broken
            description: "Whoever the character abandoned by fleeing"
          - type: mechanism_revoked
            description: "The character cannot return to where they fled from — at least not yet"

  # ──────────────────────────────────────────────────────────────
  - id: the_crossing
    label: "The Crossing"
    description: |
      Cross-plugin transition confrontation. The character chooses
      (or is forced) to move from innate_v1 into another plugin —
      typically learned_v1 (the wild thing tamed via discipline) or
      item_legacy_v1 (the wild thing externalized into a vessel).
      The choice is itself the confrontation; the outcome shapes
      what kind of character emerges on the other side.

      This is innate_v1's analog to bargained_for_v1's The
      Severance — the plugin's exit confrontation. Not severance
      (the source persists; you are still the locus) but
      transformation (the source is now mediated, channeled, or
      disciplined).
    when_triggered: |
      Available at control_tier ≥ 2, OR forced as salvage option
      when Dissociation locks at ≥ 0.85, OR narrator-offered when
      a Trainer-mentor or item-vessel candidate has entered the
      character's life and a moment of decision arrives. May also
      be a chargen-time confrontation for characters whose backstory
      includes a Crossing.
    resource_pool:
      primary: dissociation
      secondary: strain
    stakes:
      declared_at_start: true    # all paths are named: stay innate,
                                 # cross to learned, cross to item
      hidden_dimensions: false   # honest confrontation; no hidden
                                 # cost beyond the ones declared
    valid_moves:
      - cross_to_learned         # accept training; move toward discipline
      - cross_to_item            # bond the wild into a vessel
      - stay_innate              # refuse the crossing — stay wild
      - sabotage_the_path        # damage the option to make it fail
                                 # (the Trainer dies; the item breaks);
                                 # rare and dramatic
    outcomes:
      - branch: clear_win
        description: |
          The character crossed cleanly. The Innate registers as
          severed at the source-channel layer (the wild firing is
          gone); the working continues via the new plugin's
          architecture. Permanent transition.
        narrative_shape: |
          The wild thing has a shape now. The character can name
          it, hold it, choose it. Something is lost — the stranger
          inside is no longer a stranger; the friend is also no
          longer there.
        mandatory_outputs:
          - type: mechanism_revoked
            description: |
              ALL innate_v1 delivery mechanisms close for this
              character. The Innate is no longer the active source.
          - type: pact_tier
            target_plugin: learned_v1     # OR item_legacy_v1, depending
                                          # on which path was crossed
            delta: +2
            description: |
              Cross-plugin advancement: character begins the new
              plugin at tier 2 (the Innate baseline transferred)
          - type: ledger_bar_discharge
            bar: dissociation
            level: 1.0
            description: "Reintegration: the wild self is fully synthesized into the new shape"
          - type: bond
            description: "Whoever guided the crossing — Trainer, item, or community"
        optional_outputs:
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.15
            description: "The character is meaningfully more disciplined afterward"
          - type: scar
            severity: defining
            axis: existential
            description: "The mark of the lost wild self — borne forever"
          - type: reputation_tier
            description: "The character is now legible to society in a new way"

      - branch: pyrrhic_win
        description: |
          The crossing took, but at a cost beyond the character's
          own self. Someone died. A bond shattered. The Trainer
          turned out to be the Amplifier and cannot be undone now
          that the dependency exists.
        mandatory_outputs:
          - type: mechanism_revoked
            description: "innate_v1 mechanisms close"
          - type: pact_tier
            target_plugin: learned_v1     # or item_legacy_v1
            delta: +1
            description: "Cross-plugin advancement, reduced because of the cost"
          - type: bond_broken
            description: "A defining prior bond — sometimes the Trainer themselves"
          - type: scar
            severity: defining
        optional_outputs:
          - type: enemy_made
            target: the_other
            description: |
              A predecessor or parallel Innate sees the crossing
              as betrayal; they remain wild; they may seek the
              character out
          - type: counter_dispatched
            target: the_amplifier
            description: |
              The cost-payer in the Crossing was someone working a
              long con; the character now realizes
          - type: identity_shift
            axis: ocean.openness
            delta: -0.10

      - branch: clear_loss
        description: |
          The crossing failed. The Trainer was wrong, the item
          could not hold it, or the character could not commit.
          The Innate persists, but the character has spent
          something irretrievable trying to leave it.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: dissociation
            delta: 0.35
            description: "Failed crossing fragments the character further"
          - type: ledger_bar_rise
            bar: strain
            delta: 0.30
          - type: scar
            severity: defining
          - type: bond_broken
            description: "Whoever was guiding the crossing"
        optional_outputs:
          - type: mechanism_revoked
            description: "The cross-target plugin is now unavailable to this character — they cannot cross THIS way again"
          - type: enemy_made
            target: the_trainer
            description: |
              The would-be Trainer holds the failure against the
              character; they may become an Amplifier or Hunter
          - type: counter_dispatched
            target: the_other
            description: "A predecessor sees the failed crossing as confirmation"

      - branch: refused
        description: |
          The character chose to stay Innate. Often the right
          call. Always a decision with cost — the path was real
          and they walked away from it, knowing that a cleaner
          register of their power was on offer and refusing it.
        narrative_shape: |
          The character looks at the Trainer, at the vessel, at
          the discipline that would name and hold them — and they
          turn away. They will keep being what they are. The
          stranger inside stays a stranger.
        mandatory_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: +0.05
            description: "Self-knowledge has registered, even without the crossing"
          - type: scar
            severity: minor
            axis: pride_or_grief
            description: |
              The path-not-taken; some characters wear it as
              strength, some as ache
        optional_outputs:
          - type: bond
            description: |
              An unexpected bond forms with another wild Innate
              who saw the refusal and recognized themselves
          - type: bond_broken
            description: "The Trainer who hoped takes the refusal personally; the relationship cracks"
          - type: mechanism_unlocked
            description: |
              The character has chosen wildness; a new condition
              or place mechanism may open in recognition

# ─────────────────────────────────────────────────────────────────────
# REVEAL — confrontation outcome callouts (Decision #2)
# ─────────────────────────────────────────────────────────────────────
reveal:
  mode: explicit
  timing: at_outcome
  format: panel_callout
  suppression: none
  per_branch_iconography:
    clear_win: 🌊      # the surge held its shape
    pyrrhic_win: 🩸    # the body paid in blood (shared with bargained_for)
    clear_loss: ⚡     # the wild lashed
    refused: 🚪       # walked back from the threshold (shared with bargained_for)
  per_confrontation_iconography:
    the_awakening: ✨
    the_surge: 🌊
    the_suppression: 🔒
    the_reckoning: ⚖
    the_crossing: 🌉

# ─────────────────────────────────────────────────────────────────────
# WORLDBUILDING SLOT — what worlds must instantiate
# ─────────────────────────────────────────────────────────────────────
world_layer_required:
  - At least one Innate Domain per active mechanism
    description: |
      A native-mechanism world declares which Domains the local
      Innate runs in (psychic, physical, elemental, divinatory, etc.).
      A condition-mechanism world declares the specific gates
      (blood-loss, full-moon, fasted, hormonal). A place-mechanism
      world names the loci that amplify.
  - Awakening trigger conditions for the_unawakened class
    description: |
      Each world declares what stress condition tends to provoke
      first surges in this world's setting. Carrie's world: peak
      humiliation. River's world: institutional torture-conditioning
      breaking. Mutant_wasteland: proximity to Drift. Worlds without
      this declared cannot host the_unawakened class cleanly.
  - Stigma's somatic vocabulary
    description: |
      How does Stigma express in this world? Glowing eyes, rune-marks,
      hair turning grey, irises changing color, a brand surfacing,
      teeth becoming wrong, a smell only some people can detect.
      Narrator needs the world's specific somatic palette.
  - Signal bar activation decision
    description: |
      Worlds where world_knowledge ∈ {classified, esoteric,
      persecuted} activate the world-shared Signal bar. Worlds where
      Innate is acknowledged or celebrated do NOT activate it
      (there is no hunter-pressure to track).
  - At least one named Hunter, Suppressor, or Amplifier
    description: |
      Worlds with active Signal bar must instantiate at least one
      named institutional or individual counter — the named Academy
      branch, the named witch-finder, the named drug-pusher Amplifier.
      Without a named counter, the Signal bar has no narrative anchor.
  - Cross-plugin paths declared
    description: |
      Worlds may permit or forbid The Crossing. A world that hosts
      learned_v1 alongside innate_v1 (elemental_harmony, space_opera-
      Star-Wars-Republic-era, low_fantasy with active mage-school)
      enables Crossing into Learned. A world that hosts item_legacy_v1
      with vessels suitable for Innate channeling enables Crossing
      into Item. A world with neither closes The Crossing
      confrontation entirely; the character is locked in Innate as
      their permanent shape.
  - Domain palette
    description: |
      Each world declares which Domains its Innate operates in,
      out of the napkin's set: elemental, physical, psychic,
      spatial, temporal, necromantic, illusory, divinatory,
      transmutative, alchemical. mutant_wasteland-default: physical
      + occasional psychic. space_opera-Firefly-River: psychic +
      divinatory. victoria-touched: psychic + divinatory + occasional
      illusory. low_fantasy-bloodline: variable per bloodline.
```

## Validation Notes

This plugin captures:

- ✅ All 8 napkin Source axes (here: innate)
- ✅ Multiple delivery mechanisms (6 of 8 supported, 2 explicitly excluded with rationale)
- ✅ Class/archetype mapping (5 classes, each with mechanism affinity, control_tier baseline, and pact-visibility level)
- ✅ Counter archetypes (6, including the cross-plugin path-opener Trainer with explicit framing)
- ✅ Visible ledger bars (3 character-bound + 1 optional world-shared, with thresholds and decay rules — Strain decays modestly, Stigma never decays, Dissociation decays only modestly, Signal decays slightly per session)
- ✅ OTEL span shape (required, optional, yellow/red/deep-red flag conditions including plugin-specific extensions: flavor, control_tier_at_event, consent_state, signal_contribution)
- ✅ Hard limits beyond genre baseline (6, several explicitly citing other plugins' lanes)
- ✅ Narrator register (specific to consent-downstream-of-stress, body-larder, witness-third-person)
- ✅ Confrontations (5 confrontation types, each with full 4-branch outcome trees: The Awakening, The Surge, The Suppression, The Reckoning, The Crossing)
- ✅ Mandatory output on every branch (Decision #1)
- ✅ Failure-advances on clear_loss and refused branches (Decision #4)
- ✅ Player-facing reveal (Decision #2 — explicit, at_outcome, panel_callout)
- ✅ No-decay outputs by default (Decision #3); ledger_lock used in The Reckoning's clear_loss/refused
- ✅ Plugin tie-in to confrontations (Decision #5)
- ✅ Cross-plugin advancement output shape (The Crossing → learned_v1 or item_legacy_v1)
- ✅ Bidirectional and cyclical-reset patterns NOT used (this plugin is monotonic-up across all bars; no patron means no Renewal/Cleansing-style cycle — by design)
- ✅ World-shared bar pattern (the optional Signal bar, parallel to divine_v1's Hunger)
- ✅ World-layer instantiation slots specified (Domains, Awakening trigger, Stigma vocabulary, Signal activation, named counters, cross-plugin paths)

## Open Notes for Implementation

1. **`control_tier` as new output type.** The Awakening, The Suppression's clear_win, and The Crossing all gesture toward an axis of "discipline over the wild thing" that is *not* `affinity_tier` (which is keyword-affinity per ADR-021) and *not* `pact_tier` (which is depth-of-source). I've used `affinity_tier` as the proxy ("Tick toward control tier") in confrontation outputs, but a clean implementation would add `control_tier` to the output catalog in `confrontation-advancement.md` with the note that it gates The Crossing's availability and is innate-specific. Architect call.
2. **`vitality_cost` use in The Surge's refused branch.** Already in the catalog. Used here for the "you held it down and your body paid" pattern. Verify no conflict with `ledger_bar_rise` on Strain (these are *both* used in the same branch — `vitality_cost` is the immediate hit, `ledger_bar_rise` is the persistent climb).
3. **Signal bar — first world-shared bar in this plugin.** Pattern parallels divine_v1's Hunger. Confirm the panel UI can render world-shared bars distinct from character-bound bars (different visual register? different panel section?). Buttercup call.
4. **The Crossing's `target_plugin` field.** Used in clear_win mandatory outputs and pyrrhic_win mandatory outputs. The character chooses cross_to_learned vs. cross_to_item via valid_move; the resulting `pact_tier` output's `target_plugin` is determined by which move was taken. This requires the panel to render outputs whose target depends on the move choice, not just on the branch. Implementation note for whoever builds the outcome event emission.
5. **The Awakening as once-per-character.** Mostly. The `returned_wrong` flavor explicitly allows a second Awakening to a different Innate the character did not have before crossing back. No other flavor allows re-Awakening. Worth a unit-test fixture: "a character with the_carrier class and returned_wrong flavor invoking Awakening twice should validate; any other configuration should reject the second."
6. **The_unawakened class is high-touch.** The chargen flow for this class is unusual — the character is built with hidden details (their Innate type and Domain are world-determined, not player-chosen), and the first session's Awakening confrontation reveals the hidden state to the player. This requires session-start narrative scaffolding that other classes don't need. Multiplayer caveat: if multiple players want unawakened characters, their Awakening sequences need scheduling so each gets the spotlight. Default suggestion: at most one the_unawakened character per multiplayer session.
7. **No Renewal/Cleansing confrontation.** Deliberate. This plugin has no analog to divine_v1's Purity reset or bargained_for_v1's discharge-via-Calling. The Reckoning discharges Strain and Dissociation only when faced and survived; Stigma never resets without cross-plugin transition. This is the mechanical expression of "you are the source; the source persists; you cannot un-be." Architects should resist any pressure to add a "spa day for the soul" cleansing-confrontation — it is inconsistent with the plugin's identity.
8. **Genre-pack instantiation** — `mutant_wasteland` is the natural first concrete instantiation. Suggested world-pack: a Drift-adjacent settlement with named Hunter NPC (a wasteland sheriff with iron bracelets), named Amplifier (a Drift-cultist who wants the mutants uncorked), named place-mechanism (the Drift edge itself amplifies surges), Awakening trigger condition (proximity to Drift under stress). Worth ~1 evening of authoring; would validate the full pipeline.

## Plugin Lane Boundary — Innate vs. Learned

This plugin and `learned_v1` share the same Source-region of the napkin (the character is the locus). The boundary is **whether practiced control exists** (per `magic-taxonomy.md`'s Innate-vs-Learned cut). Concretely:

| Aspect | innate_v1 | learned_v1 |
|---|---|---|
| Mode | Reflexive (primary), Invoked (secondary at high control_tier) | Invoked (primary), Ritual (secondary) |
| Reliability | Wild → Emotion-gated at higher tiers | Skill-checked → Deterministic at higher tiers |
| Cost lands on | Body, Identity | Time, Discipline, Components |
| Plot register | Identity arcs, growing-into-power, survival of self | Mastery arcs, school politics, the long apprenticeship |
| Severance | Impossible (only suppression or transition) | Possible (forget the technique, abandon the practice) |
| Chargen control_tier ceiling | 2 (above this is Learned) | (defined by learned_v1) |
| Player consent at low tier | Downstream of stress | Required (you don't accidentally cast Fireball) |

A character moves between plugins via The Crossing — innate_v1 → learned_v1 is the canonical "wild thing tamed" arc, and learned_v1's eventual Innate-prerequisite-gate is the inverse machinery: a discipline that requires the Innate baseline.

## Plugin Lane Boundary — Innate vs. Bargained-For

The most important non-obvious boundary in the framework. Both plugins have a strong "the cost is overwhelming" narrative register, but the structural difference is total:

| Aspect | innate_v1 | bargained_for_v1 |
|---|---|---|
| Locus of source | Internal to character | External patron |
| Account-holder | None | Named entity with agency |
| Severance possibility | Impossible | Possible (catastrophic but real) |
| Consent at firing | Often downstream of stress | Always declared (pact must be invoked) |
| Costs | Body, identity | Soul/Debt, faction obligation |
| Witnesses | Feed the Signal bar (hunters) | Feed the Witness counter (leverage) |
| Hard limit on patron | (no patron) | Cannot kill the patron |

Narration that conflates them — "the wolf inside answered her call," "the spirits granted her surge" — is plugin-confused; the wolf or spirit makes this bargained_for, not innate. *(Cliché-judge hook: any innate_v1 working narration that names an external answering entity is yellow-flag-at-minimum.)*

## Next Concrete Moves (post-this-draft)

- [ ] Architect review the schema; confirm `control_tier` should be added to the output catalog as a first-class type
- [ ] UX (Buttercup) sketch The Surge confrontation panel — the wild reliability dice, the Strain/Stigma/Dissociation rise, the Signal contribution display when active
- [ ] UX (Buttercup) sketch the world-shared Signal bar's panel rendering — distinct from character-bound bars
- [ ] Dev (Inigo) — does the `target_plugin` field's render-time resolution (depends on which valid_move was taken) compile cleanly against the existing confrontation outcome shape?
- [ ] GM — draft `learned_v1` next as the contrasting plugin (mastery, school, deterministic register), completing the napkin Source coverage
- [ ] GM — instantiate mutant_wasteland's Drift-adjacent world layer to validate this plugin against actual play prompts (signature world, signature plugin)
- [ ] Cliché-judge — add the plugin-confusion hooks listed in Plugin Lane Boundary sections above to the magic-narration audit checklist
