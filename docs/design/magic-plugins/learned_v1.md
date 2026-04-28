# Plugin: learned_v1

**Status:** Draft, 2026-04-28
**Source:** `learned` (napkin)
**Genres using:** elemental_harmony (signature — bending discipline), space_opera (trained Jedi register, with Force-sensitivity prerequisite gate), low_fantasy (mage-school, alchemy, ritual-priest), heavy_metal (liturgical rite-knowledge component of Cleric), caverns_and_claudes (where caster classes are admitted by world; rare), pulp_noir (the Hermetic order register), spaghetti_western (gunsmith craft as discipline)
**Companion docs:** `../magic-taxonomy.md`, `../visible-ledger-and-otel.md`, `../confrontation-advancement.md`, `README.md` (this dir), `innate_v1.md` (sibling plugin — see Lane Boundary)

## Identity

Learned magic is the source that *was earned over time*. The discipline itself is the source. The character can aim it, hold it, refuse it, study it, teach it, and — uniquely among the five napkin Sources — *forget* it.

Three things distinguish this plugin from every other:

1. **The practice is the source.** Unlike Innate (the character IS the source), Bargained-For (a patron is the source), Item-Based (an object is the source), or Divine (a deity + apparatus is the source), Learned has *the technique itself* as the locus. A wizard's spell is the wizard's practice expressed; a witcher's sign is the witcher's training expressed; a Bene Gesserit Voice is the years of Voice-conditioning expressed.
2. **Severance is possible — and elective, external, or accidental.** Where Innate cannot be severed (you cannot un-be the source), Learned can be lost in three distinct ways: *willful abandonment* (you stop the practice), *external excommunication* (the school, master, or tradition strips you), or *mind-injury* (you forget — head trauma, cognitive decline, magical curse). The Forgetting confrontation captures all three.
3. **The Innate-prerequisite gate is optional, world-declared.** This plugin is the framework's expression of "trained Innate" without inflating the napkin's Source list. A world hosting both `innate_v1` and `learned_v1` may require an Innate baseline (Force-sensitivity, born-bender lineage, witcher-mutation) before chargen access to Learned classes — *but only if the world chose to require it*. A D&D-style wizard world has no Innate gate; a Star-Wars-Republic-era world does. The character may also cross from `innate_v1` to `learned_v1` mid-campaign via The Crossing — the wild thing tamed via discipline.

The plot engine is **mastery arcs**: the long apprenticeship, school politics, the rivalry between traditions, the drift toward forbidden technique, the loss-of-mastery as horror. *You spent twenty years becoming this; now what is it for?*

## Plugin Definition

```yaml
plugin: learned_v1
status: draft
genres_using:
  - elemental_harmony    # signature — bending Disciplines are the canonical
                         # learned_v1 reference. Innate-prerequisite gate
                         # set per element (born-bender required).
  - space_opera          # trained Jedi (Force-sensitivity prerequisite),
                         # Bene Gesserit (selective-breeding prerequisite),
                         # Witcher (mutation prerequisite). Across worlds.
  - low_fantasy          # the wizard-school register, alchemy, ritualism.
                         # Innate prerequisite optional per world.
  - heavy_metal          # liturgical rite-knowledge as the Learned component
                         # of Cleric class (Divine + Learned multi-plugin).
                         # Rite-priests and ritual-binders.
  - pulp_noir            # the Hermetic order register, ceremonial magic
                         # societies, Crowley-shaped lodges.
  - spaghetti_western    # gunsmith craft as discipline — making the
                         # impossible-shot reliable through years of training.
                         # No supernatural Domain; physical-only.
  - caverns_and_claudes  # where caster classes are admitted by world (the
                         # Magisters' Tower world; not the OSR-base world).

source: learned          # napkin Source — the practice IS the source

# ─────────────────────────────────────────────────────────────────────
# INNATE-PREREQUISITE GATE — optional, world-declared
# Decision 2026-04-28: "Innate-developed" collapses into Learned-with-
# prerequisite. The character may need an Innate baseline at chargen
# (Force-sensitivity, born-bender, witcher-mutation) but ONCE TRAINED,
# the discipline is the active source — Learned bills the ledger,
# Learned runs the confrontations, Learned is the OTEL plugin emitted.
# The Innate baseline persists as a chargen access fact, not as a
# parallel active source.
# ─────────────────────────────────────────────────────────────────────
prerequisite_gate:
  configurable: true              # worlds opt in/out
  default: not_required           # most Learned worlds do not require Innate
  when_required:
    description: |
      A world that activates this gate requires that any character
      taking a learned_v1 class first satisfy an innate_v1 trait at
      chargen. The Innate trait is recorded as a flavor/baseline; the
      character does NOT instantiate innate_v1's ledger bars or
      confrontations (those belong to wild Innate). Only the gate
      condition is checked.
    chargen_validation: |
      world.innate_prerequisite ∈ chargen_character.traits
    examples:
      - "Star-Wars-Republic-era space_opera: Force-sensitivity required for Jedi"
      - "Pre-Avatar elemental_harmony: born-bender required for the matching element's Discipline"
      - "Witcher-low-fantasy: completed-mutation required for sign-trained Witcher class"
      - "Bene-Gesserit-space_opera: descent from selective breeding lineage required for Voice training"

# ─────────────────────────────────────────────────────────────────────
# DELIVERY MECHANISMS — worlds pick which to activate
# Each mechanism unlocks a different plot engine.
# ─────────────────────────────────────────────────────────────────────
delivery_mechanisms:
  - id: faction
    archetype: school_or_tradition
    description: |
      Institutional training — a school, academy, lineage, order, or
      tradition. The faction admits, trains, certifies, polices, and
      excommunicates. Most institutional Learned worlds default here.
      The faction holds the canonical version of the discipline; rival
      schools teach drift-variants of the same techniques.
    npc_roles: [master, examiner, archivist, dean, prefect, inquisitor]
    plot_engine: |
      school politics, rank arcs, certification examinations,
      institutional rivalry, heresy-hearings, the long advancement
      ladder, the contested chair, the suppressed text in the locked
      library
    canonical_examples:
      - "The Iron Hills Bender Academy (elemental_harmony)"
      - "The Jedi Order (space_opera, Republic era)"
      - "The Magisters' Tower (low_fantasy / caverns_and_claudes)"
      - "The Bene Gesserit Sisterhood (space_opera-Dune-shape)"
      - "The Hermetic Order of Aegir's Fold (pulp_noir)"

  - id: relational
    description: |
      Direct master-apprentice line, no school between. The discipline
      passes via personal tutelage. May be one master one apprentice
      (Geralt-Ciri, Obi-Wan-Luke), or a small lineage chain (witcher
      master to journeyman to junior). The relationship IS the
      certification. The bond is the bond is the channel.
    plot_engine: |
      patron-protégé arcs (parallel to bargained_for's relational but
      structurally distinct — there is no patron, only a teacher),
      the master's death, the apprentice's defiance, the betrayed
      mentor, the master's hidden flaw, the inheritance question
      ("am I as good as my master? as worthy?")
    canonical_examples:
      - "Geralt and Ciri (witcher relational, signs-only)"
      - "Obi-Wan and Luke after the Order's fall (post-faction relational)"
      - "Master Aenar and her apprentice in the Pyre Mountains"
      - "An aging gunsmith taking on the orphan as last apprentice"

  - id: discovery
    description: |
      Self-taught from artifacts of prior practitioners. The
      discipline is recovered, not transmitted. Lost grimoire, dead
      master's journals, scrap-fragments of a destroyed tradition,
      the recovered notebooks of an exiled mage. Distinct from
      `item_legacy_v1`'s discovery (find a magical object) — here,
      the character finds the *technique*, and what they hold afterward
      is in their head, not their hand.
    plot_engine: |
      treasure-hunt-of-the-mind, the locked archive, the burned library,
      the cipher problem, the autodidact's blind spots, the missing
      chapter, the technique that nobody alive has ever performed
      correctly, the wrongness of self-taught practice
    canonical_examples:
      - "A character recovering Reborn alchemy from a dead order's notebooks"
      - "A self-taught wizard who learned from the burned half of a grimoire"
      - "A spaghetti-western gunsmith piecing together the dead Master's craft"
      - "A heavy_metal rite-priest reconstructing the suppressed liturgy"

  - id: place
    description: |
      Training-place-bound discipline. The Discipline cannot be fully
      taught anywhere else; some part of it requires the locus. The
      Iron Hills Academy's air, the desert that the Bene Gesserit
      train in, the temple-mountain whose silence is part of the
      curriculum. The character may continue practicing elsewhere,
      but advancement requires return.
    plot_engine: |
      pilgrimage to the school, return-of-the-prodigal, the place
      that has been destroyed (and so the discipline cannot advance
      past a certain tier in this generation), the rival who controls
      the locus, the territorial siege of the academy
    canonical_examples:
      - "The Iron Hills (elemental_harmony bending academy)"
      - "Dagobah (space_opera Jedi training-place register)"
      - "The Pyre Mountains seasonal monastery"

  - id: time
    description: |
      Calendar-gated training cycles. Apprenticeship windows that
      open and close — the Solstice Intake, the seven-year cohort,
      the once-a-decade Examination. Less common as primary
      mechanism; usually combined with faction or place to add
      urgency to advancement.
    plot_engine: |
      missed-window dread, the cohort dynamics, the long wait between
      examinations, the cycle that just ended (now you wait seven
      years), the cycle that is about to begin (last chance)
    canonical_examples:
      - "The Bene Gesserit's selective-breeding generations"
      - "The Triennial Examination at the Magisters' Tower"
      - "The seven-year witcher trial cycle"

  - id: condition
    description: |
      Player-state-gated practice. The discipline only operates when
      the character has met preparation conditions: meditated this
      morning, abstained from sleep, prepared spells today (Vancian),
      memorized the day's invocation, fasted before casting, recited
      the morning catechism. Note: distinct from `innate_v1`'s
      condition (which gates wild surge); here the condition is
      *practiced preparation*, not *trigger-pressure*.
    plot_engine: |
      ritual-of-self, the missed preparation, the time-budget of
      practice ("I haven't meditated in three days; I cannot cast
      yet"), the discipline that demands a life-shape, the cost
      of staying ready
    canonical_examples:
      - "Vancian-prepared casting at chargen-of-day"
      - "The witcher who must imbibe potions in advance of fights"
      - "The mage who must have prayed at dawn to cast at noon"
      - "The Bene Gesserit Voice, requiring the Litany Against Fear morning recitation"

# Mechanisms NOT supported by this plugin:
# - native: Innate is a separate Source. Worlds may require an Innate
#   PREREQUISITE for chargen access to Learned, but native is not a
#   delivery mechanism for Learned itself — once trained, the practice
#   delivers, not the native trait.
# - cosmic: Learned is by definition acquired through training, not
#   ambient distribution. A world with ambient cosmic magical resource
#   that everyone can use without training is hosting innate_v1 cosmic,
#   not learned_v1. (Exception case to flag for cliché-judge: narration
#   that describes "everyone learns the basics" can be valid — that's
#   universal-faction at the world level, not cosmic. The discipline
#   still requires training; what's universal is access.)

# ─────────────────────────────────────────────────────────────────────
# CLASSES — player-build options that draw from this plugin
# ─────────────────────────────────────────────────────────────────────
classes:
  - id: the_apprentice
    label: "The Apprentice"
    requires: [training_at_chargen, master_or_school_at_chargen]
    pact_visibility_to_player: full
    typical_mechanisms: [faction, relational]
    discipline_tier_at_chargen: 1
    narrator_note: |
      Early-career, mentor-bonded or school-bonded. Discipline tier 1
      means "knows the basics, fails under stress." The Apprentice's
      arc is mastery — every session builds toward Examination or
      master's-test. Most-played class shape across Learned worlds.
      The bond to the master/school is load-bearing; severing it
      cleanly requires The Forgetting.

  - id: the_journeyman
    label: "The Journeyman"
    requires: [training_at_chargen, completed_apprenticeship_in_backstory]
    pact_visibility_to_player: full
    typical_mechanisms: [faction, relational, place]
    discipline_tier_at_chargen: 2
    narrator_note: |
      Independent practitioner. No longer bonded to a single master
      but has not yet achieved Adept status. Travels. Hires on. May
      return to the school for advancement, or may be drifting away
      from institutional ties. The "journey" is real; the character
      is between identities. Witcher-on-the-Path register.

  - id: the_initiate
    label: "The Initiate"
    requires: [training_at_chargen, faction_membership_at_chargen]
    pact_visibility_to_player: full
    typical_mechanisms: [faction, time]
    discipline_tier_at_chargen: 1
    narrator_note: |
      Recently inducted into a tradition. Distinct from The Apprentice
      in that the initiate's bond is to the *tradition* rather than
      to a *master*. School-bound, ritual-marked. Higher
      lineage_standing baseline; lower personal-relational depth.
      Bene Gesserit Acolyte, Pact-Priest novitiate, freshman Magister.

  - id: the_adept
    label: "The Adept"
    requires: [training_at_chargen, high_tier_in_backstory]
    pact_visibility_to_player: full
    typical_mechanisms: [faction, relational, place]
    discipline_tier_at_chargen: 3
    narrator_note: |
      High-tier master. Teaches. Sits on examination boards. Has
      apprentices of their own. Lower fatigue cost per casting
      (mastery efficiency); higher discipline_drift threshold (more
      latitude before the school cares). Best for late-arc campaigns
      and one-shots where the character is the Mentor figure for
      others.

  - id: the_renegade
    label: "The Renegade"
    requires: [training_at_chargen, severed_from_tradition_in_backstory]
    pact_visibility_to_player: full
    typical_mechanisms: [discovery, relational]
    discipline_tier_at_chargen: 2
    narrator_note: |
      Trained-then-severed. Retains the practice but has lost the
      institutional bond — fled the school, refused the master, was
      excommunicated, or was the sole survivor of their lineage's
      destruction. May cast freely but cannot advance through
      institutional Examination. Discipline drifts faster (no oversight,
      no peers checking your work). Ronin shape. Post-Order-66 Jedi
      register.

  - id: the_autodidact
    label: "The Autodidact"
    requires: [training_at_chargen, self_taught_flag, no_master_or_school]
    pact_visibility_to_player: partial
    typical_mechanisms: [discovery]
    discipline_tier_at_chargen: 1
    narrator_note: |
      Self-taught from artifacts. Has the practice without ever
      having had a teacher. Lower starting tier than other classes
      (gaps in technique); higher fatigue per casting (inefficient
      learning); blind spots that surface as failed reliability
      checks. The most narratively distinctive class shape — the
      character does not know what they do not know. Recovers from
      The Forgetting fastest of any class, however, because their
      practice was always partial.

# Notable: there is no "the_master" class above the_adept. The deeper
# tier (master-of-the-tradition, dean, hierophant) is narrative
# faction-rank rather than a separate class shape. The Adept who reaches
# discipline_tier 4 IS the master, mechanically.

# ─────────────────────────────────────────────────────────────────────
# COUNTERS — character archetypes that oppose this plugin
# These are NPCs the GM can dispatch as confrontation outputs
# ─────────────────────────────────────────────────────────────────────
counters:
  - id: the_inquisitor
    label: "The Inquisitor"
    description: |
      Institutional anti-discipline agent — the rival tradition's
      enforcer, the heresy-hunter, the censor, the auditor of
      forbidden practice. May be from the character's own school
      (the school enforcing its own discipline) or from a rival
      tradition (the Sith targeting Jedi, the Witch-Hunter targeting
      mages). Differs from divine_v1's Heretic counter — Inquisitor
      hunts technique-deviation; Heretic hunts faith-deviation.
    plot_use: |
      Dispatched after high discipline_drift or a clear_loss on The
      Forbidden Working. Persistent across sessions; the Inquisitor
      has institutional records and resources.

  - id: the_revoker
    label: "The Revoker"
    description: |
      The character's OWN master, school, or tradition arriving to
      strip the certification. Distinct from Inquisitor in that the
      Revoker is positionally the character's previous source of
      authority — there is grief in this counter, not just opposition.
      The school that taught you sending your old classmate to take
      back the diploma.
    plot_use: |
      Drives The Forgetting confrontation when external excommunication
      is the path. Output of certain pyrrhic_win and clear_loss
      branches in The Examination.

  - id: the_rival
    label: "The Rival"
    description: |
      Parallel discipline, parallel character. The rival apprentice,
      the contemporary Adept, the witcher of a competing school
      (Cat-school vs. Wolf-school), the wizard graduate of the same
      cohort who took the appointment you wanted. May be friendly
      and respect-based; may be poisonous; usually some of both.
    plot_use: |
      Most narrative-rich counter — they have their own discipline
      ledger, their own arc, their own bills. Often the central
      recurring NPC of a learned_v1-anchored campaign.

  - id: the_destroyer_of_books
    label: "The Destroyer of Books"
    description: |
      Specifically anti-discovery counter. Burns grimoires, breaks
      training tools, kills witnesses to lost techniques, sabotages
      libraries. The character whose discipline depends on recovered
      texts has a mortal enemy in someone determined to ensure no
      texts remain. The Cardinal who orders the burning. The witcher-
      hunter who takes the trophy heads to keep the silver-sword
      forging-secrets dead.
    plot_use: |
      Dispatched against the_autodidact and the_renegade especially.
      Drives `mechanism_revoked` outputs (the discovery channel
      closes when the books burn).

  - id: the_dampener
    label: "The Dampener"
    description: |
      Environmental counter — the null-field, the anti-magic zone,
      the dispelling apparatus. Unlike `innate_v1`'s Suppressor (which
      targets the character's body), the Dampener targets the
      *casting environment*. Some traditions can adapt; others cannot
      cast in dampened space at all. Renders entire scenes
      preparation-only.
    plot_use: |
      Encountered as terrain, not as character — the Dampener is the
      *room*, the *enemy fortress*, the *anti-magic ward on the
      vault*. Drives `mechanism_revoked` of place-mechanism for the
      duration of the location.

  - id: the_mentor_betrayed
    label: "The Mentor Betrayed"
    description: |
      The master who taught the character and now opposes them. Most
      devastating counter shape in this plugin. The bond was real;
      the breach is also real. The master's reasons — the character's
      drift, the character's defiance, the master's own corruption —
      determine which sub-flavor (justified-betrayal, mutual-collapse,
      or unprovoked-villainy) the relationship plays as. All three
      are valid; the plot engine differs.
    plot_use: |
      Drives some of the heaviest scar/identity_shift outputs. May
      be the secret antagonist of an entire campaign. Best as the
      late-arc reveal: the Inquisitor who has been hunting the
      character was your master all along.

# ─────────────────────────────────────────────────────────────────────
# LEDGER BARS — what this plugin contributes to the visible ledger
# ─────────────────────────────────────────────────────────────────────
ledger_bars:
  - id: fatigue
    label: "Fatigue"
    color: paper
    scope: character
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 1.0
    consequence_on_high_cross: |
      Discipline-collapse. The character cannot cast for the rest
      of the session. May not collapse physically (this is not
      Strain — discipline is renewable, the body is fine), but the
      practice is exhausted. Forced rest, study, or downtime to
      recover. Does NOT trigger a Reckoning-style confrontation —
      Learned characters carry exhaustion gracefully; the bill is
      the lost session-time.
    decay_per_session: 0.50    # discipline is renewable; rest restores it
    starts_at_chargen: 0.0
    note: |
      Lighter monotonic-up bar than innate_v1's Strain. Decays
      heavily between sessions because discipline IS renewable —
      that is one of Learned's structural advantages over Innate.

  - id: discipline_drift
    label: "Discipline Drift"
    color: ink_dark
    scope: character
    range: [0.0, 1.0]
    direction: monotonic_up
    threshold_high: 0.5
    threshold_higher: 1.0
    consequence_on_high_cross: |
      Mid-tier drift. The school's records note an irregularity. The
      character's lineage_standing is at risk. An Examination is
      offered (the school invites the character in for a "review");
      attending becomes one path. Avoiding the review compounds
      drift.
    consequence_on_higher_cross: |
      Maximum drift. Triggers automatic dispatch of the_inquisitor.
      The Forbidden Working's heaviest pyrrhic_win path. The character
      is now considered formally heretical by the canonical tradition;
      The Examination becomes a heresy-hearing on subsequent
      encounter.
    decay_per_session: 0.0     # the school's records do not forget
    starts_at_chargen: 0.0     # default; the_renegade may chargen at 0.20

  - id: lineage_standing
    label: "Lineage Standing"
    color: parchment_gilt
    scope: faction             # tracked per-school/lineage; multiple
                               # schools accumulate separately
    range: [-1.0, 1.0]
    direction: bidirectional
    threshold_high: 1.0
    threshold_higher: ~        # no second tier high-side
    threshold_low: -0.6
    threshold_lower: -1.0
    consequence_on_high_cross: |
      The character is in line for advancement to the_adept tier (if
      apprentice/journeyman/initiate) or to faction-elder shape (if
      already adept). Examination is offered or scheduled.
    consequence_on_low_cross: |
      The school formally censures the character. Privileges
      restricted; library access reduced; advancement frozen until
      the relationship is repaired or severed.
    consequence_on_lower_cross: |
      Excommunication imminent. The Revoker is dispatched. The
      Forgetting confrontation triggered at next narratively-suitable
      moment.
    decay_per_session: 0.0     # standing does not drift on its own
    starts_at_chargen: 0.5     # default for trained-faction-bonded
                               # classes; the_renegade chargens at -0.4;
                               # the_autodidact chargens at 0.0
                               # (no faction)

  # ──── OPTIONAL ledger bars (worlds activate as their tradition's ────
  # mechanics require) ─────────────────────────────────────────────────

  - id: prepared_slots
    label: "Prepared Slots"
    color: candle
    scope: character
    range: [0.0, 1.0]
    direction: monotonic_down
    threshold_low: 0.0
    consequence_on_low_cross: |
      No prepared workings remain. The character cannot cast prepared
      techniques until the cyclical reset condition is met.
    decay_per_session: 0.0     # not a decay; consumed by casting
    cyclical_reset:
      trigger: study_or_rest    # 8 hours rest + 1 hour study, world-defined
      reset_to: 1.0
    starts_at_chargen: 1.0      # at session start, fully prepared
    activation: |
      Active only in worlds where the tradition uses Vancian-style
      prepared casting (Magisters' Tower, certain D&D-style
      caverns_and_claudes worlds, traditional low_fantasy mage-school).
      Spontaneous-casting traditions (witcher signs, bending,
      gunsmith craft) do not activate this bar.

  - id: components
    label: "Components"
    color: silver_dust
    scope: character
    range: [0.0, 1.0]
    direction: bidirectional   # consumed by casting; refilled by shopping
    threshold_low: 0.1
    threshold_lower: 0.0
    consequence_on_low_cross: |
      Material reserves running low. Some workings now unavailable
      (the ones requiring the rare reagents). Player aware they need
      to restock soon.
    consequence_on_lower_cross: |
      Empty stash. No material-requiring workings can be performed
      until restock. Forced economic confrontation: the character
      must seek out a supplier (often faction-controlled, often
      expensive, sometimes dangerous).
    decay_per_session: 0.0      # consumed only by casting; not by time
    starts_at_chargen: 0.6      # decent stash to start
    activation: |
      Active only in worlds where the tradition uses material
      components (alchemy, ritualism, ceremonial magic, reagent-
      casting). Word-or-gesture-only traditions (witcher signs,
      Voice, gunsmith-craft) do not activate this bar.

# ─────────────────────────────────────────────────────────────────────
# OTEL SPAN SHAPE — what the narrator must emit per working
# ─────────────────────────────────────────────────────────────────────
otel_span:
  span_name: magic.working
  required_attributes:
    - working_id
    - plugin                   # always: learned_v1
    - source                   # always: learned
    - declared_effect
    - domains
    - modes                    # invoked (primary), ritual (secondary);
                               # NEVER reflexive (that's Innate);
                               # NEVER item-channeled (that's Item-Legacy)
    - debited_costs            # at minimum fatigue rise; often
                               # prepared_slots/components if active.
                               # NEVER empty.
    - mechanism_engaged        # one of: faction | relational | discovery |
                               #         place | time | condition
    - mechanism_target
    - reliability_roll         # skill-checked at low tier;
                               # deterministic at high tier
    - discipline_tier_at_event # 1–4 — the character's mastery level
    - tradition_id             # which named tradition's canonical version
                               # of the technique was performed (or
                               # which drift-variant)
    - innate_prerequisite_satisfied  # boolean — did the world's gate apply
                                     # and is it satisfied? (true if no gate)
    - world_knowledge_at_event
    - visibility_at_event
  optional_attributes:
    - witnesses_present
    - confrontation_id
    - confrontation_branch
    - components_consumed       # specific reagents (when components bar active)
    - prepared_slot_consumed    # specific prepared working ID (when prepared
                                # bar active)
    - is_forbidden_working      # boolean — was this technique school-
                                # restricted? (drives discipline_drift)
    - is_drift_variant          # boolean — was this a non-canonical version
                                # of the canonical tradition's technique?
    - master_or_school_id       # the relational/faction backing the working
                                # (relational and faction mechanisms only)
  on_violation: gm_panel_red_flag
  yellow_flag_conditions:
    - "narration implies a Learned-shaped event but no span fires"
    - "discipline_tier_at_event is unset"
    - "tradition_id is absent (which tradition's technique IS this?)"
    - "mechanism_engaged set to native or cosmic (out of plugin lane)"
    - "is_forbidden_working unset on a working that the school's
       canonical list DOES restrict"
  red_flag_conditions:
    - "debited_costs is empty (a free Learned working — never; even
       a tier-4 Adept's most efficient cast bills at least a sliver
       of fatigue)"
    - "mechanism_engaged set to native (the character's Innate
       baseline is not the source — once trained, the practice is
       the source; flag this as plugin-confused)"
    - "discipline_tier_at_event > 0 but innate_prerequisite_satisfied
       is false in a world that requires the gate (chargen
       validation broke)"
    - "narration depicts the character casting a prepared working
       when prepared_slots = 0 (the bar is the bill; check the bar)"
  deep_red_flag_conditions:
    - "the working violates a hard_limit (severed-and-still-casting,
       cosmic-distribution, item-as-source)"
    - "narration depicts a tier-1 Apprentice performing a tier-3
       technique flawlessly under stress (this is reflexive Innate-
       shaped, not Learned — the discipline can't outrun the tier)"

# Plugin-specific extensions to the universal magic.working span:
# - discipline_tier_at_event (the mastery axis)
# - tradition_id (which lineage's canonical version)
# - innate_prerequisite_satisfied (the world's gate state)
# - is_forbidden_working / is_drift_variant (drift-tracking)
# - master_or_school_id (relational/faction backing)
# - components_consumed / prepared_slot_consumed (mode-specific)
# These attributes are encouraged for ALL workings in this plugin
# and are the load-bearing fields for the cliché-judge's Learned hooks.

# ─────────────────────────────────────────────────────────────────────
# HARD LIMITS specific to learned (above genre baseline)
# ─────────────────────────────────────────────────────────────────────
hard_limits:
  inherits_from_genre: true
  additional_forbidden:
    - id: cast_above_tier
      description: |
        A character cannot perform workings above their
        discipline_tier. The discipline IS the tier; the practice
        does not contain techniques the character has not learned.
        Narration that has a tier-1 Apprentice perform a tier-3
        technique under inspiration or stress is plugin-confused —
        that's an Innate surge happening, not a Learned working,
        and the plugin should be different.
    - id: native_as_source
      description: |
        A character's Innate baseline (when an Innate prerequisite
        gate is active) is NOT the source of any Learned working.
        Once trained, the discipline IS the source. Narration that
        says "her Force-sensitivity allowed her to cast" or "his
        bender-blood granted the technique" is plugin-confused;
        the Force-sensitivity gates access to training, the training
        delivers the working. The OTEL panel YELLOW-flags
        narration that names the Innate trait as the operative
        source of a Learned working.
        references_plugin: innate_v1
    - id: item_as_source
      description: |
        An item (focus, wand, staff, sword) is not the source of a
        Learned working — it is at most a tradition-required
        catalyst. The discipline is the source; the item facilitates.
        Narration that depicts the wand as casting on its own (when
        bonded or stolen) is leaking into item_legacy_v1's territory.
        A wand that has its own personality and answers to its
        wielder is an Item-Legacy bonded item and should be hosted
        there, with the wand's user being a Learned-Item multi-plugin
        character.
        references_plugin: item_legacy_v1
    - id: severed_and_still_casting
      description: |
        A character who has completed The Forgetting cannot continue
        to perform Learned workings in that tradition. The discipline
        is gone. Cross-plugin transitions (into innate_v1 if a latent
        Innate emerges, into item_legacy_v1 if a vessel was bonded
        during the Forgetting) explain how a character may continue
        to perform magic at all — but those are different plugins.
        Narration that has the post-Forgetting character cast their
        old technique is wrong, even when emotionally satisfying.
    - id: deity_targeted
      description: |
        Learned workings cannot have a god as target. Gods are
        divine_v1's territory. A Learned ritualist may petition
        a god (that's invocation, divine_v1's domain); a Learned
        wizard cannot target a god directly with a technique.
        references_plugin: divine_v1
    - id: cosmic_distribution
      description: |
        A Learned tradition cannot be claimed as "everyone in this
        world inherently has a touch of it." Either the world hosts
        innate_v1 cosmic (everyone has a touch), or it hosts
        learned_v1 with universal-faction access (everyone learns
        the basics — the discipline is widely taught). The two
        configurations are mechanically distinct and produce
        different bars and confrontations. Worlds must pick.
    - id: forbidden_techniques_as_default
      description: |
        A tradition's canonical version of itself cannot include
        techniques that ALL workings of that tradition trigger
        discipline_drift. If every cast you do drifts you, the
        tradition is the heresy, not the technique. (Worlds with
        such traditions should re-flag those traditions as the
        outlawed tradition, not the canonical one.)

# ─────────────────────────────────────────────────────────────────────
# NARRATOR REGISTER — prose voice when this plugin fires
# ─────────────────────────────────────────────────────────────────────
narrator_register: |
  The narrator must always render Learned workings as the *practice
  expressed*. The character speaks the words because they have been
  taught the words. The hand traces the gesture because it has been
  drilled. The reagents combine in the proportions the master
  insisted on. The discipline is in the body of the technique,
  not in the body of the character.

  Use the verbs of mastery — sparingly at low tier, freely at high.
  At discipline_tier 1, the Apprentice "completes the gesture
  haltingly," "remembers the verb just before failing," "finds the
  pattern under pressure." At tier 2, they "cast with steady hands,"
  "hold the ritual through interruption," "improvise around a
  forgotten step." At tier 3, they "shape the technique to the
  problem," "compress the rite into a half-second," "invent a new
  application of an old form." At tier 4, they "play the discipline
  the way a master plays an instrument" — the technique is in the
  hand and they are answering the moment.

  Costs surface in time, materials, and focus before they surface
  in body. The character is fatigued, not strained. The focus is
  consumed, not the body. The prepared slot is spent, not the soul.
  This is the structural opposite of innate_v1's body-larder
  register — discipline is portable, renewable, and external to the
  flesh in a way Innate never is.

  The school is always present. Even when the character is alone in
  the world, the discipline carries its lineage — the master's voice
  saying "no, again" when the gesture is sloppy; the school's
  marginal annotations on the standard text; the rival who would
  do this differently. The character's interior monologue while
  casting is *populated* by the tradition. (Exception: the_autodidact
  is alone with their notebooks and feels it; the absence of the
  lineage-voice is itself the register.)

  Forbidden workings carry their own register. When a character
  performs a school-restricted technique, the narrator must signal
  the transgression — not by warning but by texture: the words that
  do not appear in the canonical text, the gesture that the master
  would have struck the apprentice for, the silence in the
  imagined-school's reaction. The drift is felt before it is
  named.

  At the Examination and the Forgetting, the narrator's register
  shifts toward the institutional — the language of the school
  itself, the formal register of the Tradition's own voice. These
  are scenes where the character is being measured by the
  discipline, and the prose should sound like the discipline
  measuring.

# ─────────────────────────────────────────────────────────────────────
# CONFRONTATIONS — see ../confrontation-advancement.md for schema
# ─────────────────────────────────────────────────────────────────────
confrontations:

  # ──────────────────────────────────────────────────────────────
  - id: the_casting
    label: "The Casting"
    description: |
      Everyday invocation of a learned technique. The most-frequently-
      played confrontation in this plugin — most Learned sessions
      contain several. Lower-stakes than other confrontation types
      but cumulative; the bills add up across the session.
    when_triggered: |
      Player declares use of a Learned technique. The technique is
      within the character's discipline_tier. The conditions are
      met (prepared slots if Vancian; components if material).
      Reliability roll determines the outcome's branch unless
      mastery is high enough to skip the roll (deterministic
      tier-4 register).
    resource_pool:
      primary: fatigue
      secondary: prepared_slots          # OR components, depending
                                         # on world's tradition; falls back
                                         # to fatigue alone if neither bar
                                         # is active
    stakes:
      declared_at_start: true            # the character knows what
                                         # the cost will be (skill-checked
                                         # uncertainty is on the OUTCOME,
                                         # not the cost)
      hidden_dimensions: false
    valid_moves:
      - canonical                        # the standard form; safest
      - improvise                        # adapt to the situation; harder
                                         # roll, larger possible effect
      - drift                            # use a non-canonical variant —
                                         # raises discipline_drift; sometimes
                                         # the only path
      - amplify                          # spend extra prepared slot or
                                         # components for larger effect;
                                         # more cost
      - hedge                            # smaller working, smaller cost,
                                         # easier roll
      - abort                            # stop mid-cast; partial fatigue
    outcomes:
      - branch: clear_win
        description: |
          The technique fires as intended; the cost is what was
          named.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: fatigue
            delta: 0.10
        optional_outputs:
          - type: affinity_tier
            description: "Tick toward Domain affinity advancing"
          - type: bond
            description: "Whoever is impressed by the casting; school-mate, NPC, ally"
          - type: ledger_bar_rise
            bar: lineage_standing
            delta: +0.05
            target_kind: faction
            description: |
              If a peer or examiner witnessed and the working was
              tradition-canonical: the school's view of you ticks
              up

      - branch: pyrrhic_win
        description: |
          The technique fired, but the cost was higher than expected
          OR the side-effects were greater than wanted OR a witness
          saw something they shouldn't have.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: fatigue
            delta: 0.25
        optional_outputs:
          - type: ledger_bar_rise
            bar: discipline_drift
            delta: 0.05
            description: |
              If `improvise` or `drift` move was used: small drift
              registered
          - type: secret_known
            description: |
              A witness now knows something — that you can do this
              technique, that you were in this place, that you
              know more than you let on
          - type: scar
            severity: minor
            description: "A small visible mark of the casting effort — burned focus, smudged ink, broken nail on the gesture"
          - type: ledger_bar_fall
            bar: lineage_standing
            delta: -0.05
            target_kind: faction
            description: "Sloppy work that a peer or master witnessed"

      - branch: clear_loss
        description: |
          The working failed to fire OR fired wrong. Reliability
          roll missed. The character spent the resources without
          the result. The technique was not adequate to the moment;
          the discipline was not enough.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: fatigue
            delta: 0.20
            description: |
              You spent the energy even though the working failed
              — the gestures were performed, the words were spoken,
              the focus was consumed
          - type: scar
            severity: minor
            axis: pride
            description: "The mark of failed casting — sometimes external, always internal"
        optional_outputs:
          - type: ledger_bar_fall
            bar: lineage_standing
            delta: -0.10
            target_kind: faction
            description: "If a peer or master witnessed: the school takes note"
          - type: identity_shift
            axis: ocean.openness
            delta: -0.03
            description: "The character trusts the discipline a fraction less"
          - type: mechanism_unlocked
            description: |
              Sometimes a clear_loss reveals that a different
              mechanism was needed — the character realizes the
              technique works only with components, or only at a
              certain place, or only after specific preparation. A
              new condition or place mechanism may open

      - branch: refused
        description: |
          The character chose not to cast despite having the
          opportunity. Conserved resources. Sometimes wisdom;
          sometimes failure of nerve. The discipline was withheld.
        mandatory_outputs:
          - type: scar
            severity: minor
            axis: pride_or_pragmatism
            description: |
              Some characters wear refusal as discipline (better
              prepared next time); some as cowardice
          - type: vitality_cost
            description: |
              A small physical hit: the situation cost the character
              something because they didn't cast — bruises, lost
              ground, missed opportunity
        optional_outputs:
          - type: bond
            description: "A bond with whoever benefited from the conserved resources"
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.02
            description: "The discipline of restraint registers"

  # ──────────────────────────────────────────────────────────────
  - id: the_examination
    label: "The Examination"
    description: |
      Institutional rite of advancement OR heresy hearing. The
      school formally evaluates the character. Stakes are mastery
      level (advancement clear_win), continued standing (clear_win
      at lower tiers), or excommunication-imminent (clear_loss).
      Two surface forms — Advancement Examination (positive frame,
      character invited) and Heresy Hearing (negative frame,
      character summoned) — but mechanically the same confrontation
      shape.
    when_triggered: |
      lineage_standing crosses ≥ 1.0 (Advancement Examination scheduled),
      OR discipline_drift crosses ≥ 0.5 (Heresy Hearing offered, framed
      as "review"), OR narrator-triggered at appropriate session moment
      (faction has decided), OR character-requested (formally petitions
      for advancement).
    resource_pool:
      primary: lineage_standing
      secondary: fatigue           # the examination itself is exhausting
    stakes:
      declared_at_start: true
      hidden_dimensions: true      # the examiners may have private agendas;
                                   # the actual rubric may differ from the
                                   # stated rubric (rivals on the panel,
                                   # politics of the moment)
    valid_moves:
      - perform_canonical          # demonstrate canonical technique
      - perform_innovative         # demonstrate creative application;
                                   # high-risk-high-reward
      - admit_drift                # surface discipline_drift voluntarily;
                                   # changes the examination's tone
      - defend_drift               # justify drift-variants as legitimate;
                                   # confrontational
      - call_witness               # bring in an ally NPC for character-
                                   # vouching
      - refuse_examination         # walk out; treated as clear-loss-shaped
                                   # but with refused-branch outputs
    outcomes:
      - branch: clear_win
        description: |
          Advancement granted, OR the heresy charge dismissed, OR
          full vindication of drift-variants as legitimate practice.
        narrative_shape: |
          The school speaks with one voice. The character is
          recognized. The lineage is reaffirmed. They leave the
          examination chamber as a different rank than they entered
          it, or with their drift formally certified as innovation
          rather than heresy.
        mandatory_outputs:
          - type: pact_tier
            delta: +1
            description: "Discipline tier advances; or for heresy-defense, the drift is formally cleared"
          - type: ledger_bar_rise
            bar: lineage_standing
            delta: +0.20
            target_kind: faction
          - type: ledger_bar_discharge
            bar: discipline_drift
            level: 1.0
            description: |
              If the Examination was a heresy hearing and the
              character won: drift is cleared from the record (the
              variants are now sanctioned). If it was advancement:
              minor drift is forgiven as part of the elevation
        optional_outputs:
          - type: bond
            target_kind: faction
            description: "A senior examiner becomes a mentor or patron"
          - type: mechanism_unlocked
            description: "Higher-tier techniques become available; archive access expands"
          - type: reputation_tier
            description: "School-internal reputation register shifts upward"

      - branch: pyrrhic_win
        description: |
          Advancement granted, OR charge dismissed — but at a cost
          beyond fatigue. A rival was made on the panel. A secret
          was admitted that the character cannot retract. A senior
          examiner expects something in return.
        mandatory_outputs:
          - type: pact_tier
            delta: +1
          - type: ledger_bar_rise
            bar: lineage_standing
            delta: +0.10
            target_kind: faction
          - type: bond
            description: "A senior figure now has a claim on the character — favor owed"
          - type: scar
            severity: major
            axis: psychic_or_social
            description: |
              The thing said in the examination chamber that cannot
              be unsaid; the technique demonstrated that the
              character now wishes had stayed private
        optional_outputs:
          - type: counter_dispatched
            target: the_rival
            description: "A panel-rival now opposes the character openly across future arcs"
          - type: secret_known
            description: |
              The character revealed something to clear the
              examination that was meant to stay hidden; the panel
              now knows; one of them will eventually leak it
          - type: enemy_made
            description: "An opposing examiner takes the character's elevation personally"

      - branch: clear_loss
        description: |
          Advancement refused, OR heresy charge confirmed. The
          school formally censures the character. lineage_standing
          crashes. The character has not been excommunicated yet —
          but the path there is now visible and short.
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: lineage_standing
            delta: -0.40
            target_kind: faction
          - type: scar
            severity: major
            axis: pride
            description: "The institutional rejection registers"
          - type: ledger_bar_rise
            bar: discipline_drift
            delta: 0.10
            description: |
              If heresy hearing: drift is now formally on the
              record at increased level
        optional_outputs:
          - type: counter_dispatched
            target: the_inquisitor
            description: "Formal investigation opened; institutional pressure incoming"
          - type: bond_broken
            target_kind: faction
            description: "The school-bond fractures; a former mentor distances"
          - type: enemy_made
            description: "The lead examiner takes responsibility for the character's correction"
          - type: mechanism_revoked
            description: "Faction mechanism partially closes — archive access reduced; advancement frozen"

      - branch: refused
        description: |
          The character walked out of the examination, refused to
          submit to evaluation, or refused to acknowledge the
          panel's authority. Open defiance — but stops short of
          completed Forgetting.
        narrative_shape: |
          The character pushes back from the table. Tells the panel
          what they will not do. Walks. The doors close behind them
          and the lineage is now a question, not an answer.
        mandatory_outputs:
          - type: ledger_bar_fall
            bar: lineage_standing
            delta: -0.50
            target_kind: faction
          - type: scar
            severity: major
            axis: pride_or_principle
            description: |
              The character may wear the refusal as integrity or as
              wreckage; narrator-chosen by world-tone
        optional_outputs:
          - type: bond
            description: |
              An ally outside the school — perhaps a Renegade-shaped
              figure who has done this before — recognizes the
              character now
          - type: counter_dispatched
            target: the_revoker
            description: "The school dispatches a former mentor to bring the character back, or to formally strip them"
          - type: mechanism_unlocked
            description: |
              Renegade-mechanism opens — discovery and relational
              channels become more salient as faction recedes

  # ──────────────────────────────────────────────────────────────
  - id: the_apprenticeship
    label: "The Apprenticeship"
    description: |
      The pivotal moment in tutelage where stakes crystallize. Not
      the entire arc of being-an-apprentice — that's session-long
      structure, not a confrontation — but the *specific scene*
      where the master and the apprentice's relationship lands a
      decisive output. The master tests the apprentice with a real
      stake; the master orders the apprentice to do something they
      do not want to do; the master reveals a hidden truth; the
      apprentice disagrees and must choose to defy or obey.
      Replayable: a campaign may contain multiple Apprenticeship
      confrontations across different stakes.
    when_triggered: |
      The character is in active tutelage (relational mechanism is
      active) AND a moment arises where the master-apprentice bond
      is being measured. Often narrator-driven; sometimes player-
      driven (the apprentice forces the moment).
    resource_pool:
      primary: bond              # the master-apprentice bond is the
                                 # tracked relational asset
      secondary: discipline_drift
    stakes:
      declared_at_start: true
      hidden_dimensions: true    # the master may have agendas the
                                 # apprentice does not yet understand
    valid_moves:
      - obey                     # complete the test/order/instruction
      - defy                     # refuse openly
      - evade                    # complete the surface but not the spirit
      - confront                 # demand the master justify
      - confess                  # admit a prior secret to the master
      - sacrifice_for            # offer something of yours for the master's sake
    outcomes:
      - branch: clear_win
        description: |
          The bond deepens; the relationship advances; the
          apprentice is now closer to the master than before. The
          test is passed; the truth is integrated; the disagreement
          is reconciled.
        mandatory_outputs:
          - type: bond
            target_kind: character
            description: |
              The master-apprentice bond strengthens, recorded
              explicitly. May upgrade to something like family.
          - type: pact_tier
            delta: +1
            description: |
              The apprentice's discipline tier advances under the
              master's care (clean transmission)
        optional_outputs:
          - type: secret_known
            description: |
              The master shared something — the technique they have
              not taught anyone else, a story about their own master,
              the line they will not cross
          - type: mechanism_unlocked
            description: |
              The master has now opened access to a place, condition,
              or text that was previously held back
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.05

      - branch: pyrrhic_win
        description: |
          The relationship advances at a cost — the apprentice
          obeyed and the obedience was wrong; the apprentice
          defended the master and the defense exposed something;
          the test was passed by methods the master did not want
          to know about. The bond is bigger and partly cracked.
        mandatory_outputs:
          - type: bond
            target_kind: character
            description: "Bond deepens — but with a complicated note"
          - type: scar
            severity: major
            axis: psychic_or_social
            description: |
              The thing the apprentice did to pass; or the thing
              the master asked
          - type: ledger_bar_rise
            bar: discipline_drift
            delta: 0.15
            description: |
              If the apprentice used drift-variants in the test:
              the drift is now master-known; held in confidence
              or held over them
        optional_outputs:
          - type: secret_known
            description: |
              The apprentice now knows something about the master —
              a flaw, a past act, a fear — that they did not expect
              to learn
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.05
            description: |
              The apprentice is harder afterward; the romance of
              tutelage has shifted

      - branch: clear_loss
        description: |
          The apprentice failed the test, OR the master rejected
          them, OR the disagreement broke the bond. The relational
          mechanism is damaged, possibly fatally.
        mandatory_outputs:
          - type: bond_broken
            target_kind: character
            description: "Master-apprentice bond fractures; relationship degraded"
          - type: scar
            severity: major
            axis: pride_or_grief
          - type: ledger_bar_fall
            bar: lineage_standing
            delta: -0.20
            target_kind: faction
            description: |
              If the master was faction-affiliated: the school is
              informed of the apprentice's unsuitability
        optional_outputs:
          - type: counter_dispatched
            target: the_mentor_betrayed
            description: |
              The master, whether acting from grief or anger, will
              henceforth oppose the apprentice — most-feared counter
              shape in this plugin
          - type: enemy_made
            target: the_rival
            description: "A peer apprentice now sees the character as failed competition"
          - type: mechanism_revoked
            description: |
              Relational mechanism closes for this character with
              this master; cannot be re-opened with the same person.
              Other masters remain possible

      - branch: refused
        description: |
          The apprentice walked away from the moment without
          resolution. Avoided the test, deflected the truth,
          declined the disagreement. The bond is intact but
          frozen — neither advanced nor broken. Cost is in the
          unresolved.
        mandatory_outputs:
          - type: scar
            severity: minor
            axis: pride
            description: "The unfaced moment registers"
          - type: ledger_bar_rise
            bar: fatigue
            delta: 0.20
            description: |
              The held-tension manifests as exhaustion across the
              session
        optional_outputs:
          - type: identity_shift
            axis: ocean.openness
            delta: -0.03
            description: "The apprentice trusts the relationship a fraction less"
          - type: bond_broken
            description: |
              An OBSERVING ally — a peer apprentice who watched the
              avoidance — pulls back; they thought you were braver
              than that

  # ──────────────────────────────────────────────────────────────
  - id: the_forbidden_working
    label: "The Forbidden Working"
    description: |
      The character performs (or attempts) a technique their school
      formally restricts. May be a banned ritual, a heretical
      drift-variant, a tier-locked technique cast above the
      character's certified level, or a working from a rival
      tradition. Stakes are discipline_drift, lineage_standing, and
      sometimes the technique's intrinsic dangers. Often the only
      adequate response to the situation; sometimes pure transgression.
    when_triggered: |
      Player declares intent to perform a working flagged
      `is_forbidden_working` in the world's tradition definition.
      May also be narrator-triggered when only a forbidden technique
      can resolve the situation and the character is forced to
      improvise.
    resource_pool:
      primary: discipline_drift
      secondary: fatigue
    stakes:
      declared_at_start: true    # the character knows the technique
                                 # is forbidden; the question is what
                                 # the cost will be when (not if) they
                                 # are caught
      hidden_dimensions: true    # the school's reach into the moment
                                 # may be greater than the character knows
    valid_moves:
      - cast_openly              # perform without concealment; commit
                                 # to the transgression
      - cast_concealed           # attempt to hide the working from
                                 # witnesses; reduces drift impact if
                                 # successful, raises it sharply if caught
      - cast_under_provocation   # frame the working as forced by
                                 # circumstances; drift impact reduced
                                 # if the school accepts the framing
      - corrupt_the_record       # attempt to falsify the working as a
                                 # canonical technique on later
                                 # examination; high-risk
      - abort_mid_working        # break off; partial cost
    outcomes:
      - branch: clear_win
        description: |
          The working fired AND the character was not caught OR
          the framing held OR the school's lens did not focus on
          this scene. The transgression occurred; the world has not
          yet noticed.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: fatigue
            delta: 0.20
            description: "Forbidden workings are inefficient — they cost more than canonical"
          - type: ledger_bar_rise
            bar: discipline_drift
            delta: 0.05
            description: |
              The drift is recorded internally even when external
              detection fails — the character's own practice has
              shifted, and that registers
        optional_outputs:
          - type: secret_known
            description: |
              ONE witness saw something but does not yet understand
              what. They will, eventually
          - type: identity_shift
            axis: ocean.openness
            delta: +0.05
            description: |
              The character trusts themselves more — the
              transgression succeeded; they know they can do this

      - branch: pyrrhic_win
        description: |
          The working fired AND a witness saw clearly OR a peer
          recognized the technique OR the school's lens DID catch
          the scene. Effect achieved; the bill is going to come
          from outside.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: fatigue
            delta: 0.30
          - type: ledger_bar_rise
            bar: discipline_drift
            delta: 0.20
          - type: secret_known
            description: "A specific named NPC now knows; they will report or hold the leverage"
        optional_outputs:
          - type: counter_dispatched
            target: the_inquisitor
            description: "Formal report incoming; investigation opens at next school touchpoint"
          - type: ledger_bar_fall
            bar: lineage_standing
            delta: -0.15
            target_kind: faction
          - type: scar
            severity: major
            axis: psychic
            description: "The transgression has marked the character — sometimes physically (a brand of practice), sometimes only in their own knowing"
          - type: enemy_made
            target: the_rival
            description: "A peer who saw will use this against the character at the next opportunity"

      - branch: clear_loss
        description: |
          The working failed to fire (forbidden techniques are
          sometimes intrinsically wild, especially for under-tier
          casters) OR fired against the character OR backlash
          consumed something the character did not intend to spend.
          The transgression failed; the character paid; the world
          may also know.
        mandatory_outputs:
          - type: ledger_bar_rise
            bar: fatigue
            delta: 0.40
          - type: ledger_bar_rise
            bar: discipline_drift
            delta: 0.30
          - type: scar
            severity: major
            axis: physical_or_psychic
            description: "The backlash from the failed forbidden working"
          - type: ledger_bar_fall
            bar: lineage_standing
            delta: -0.25
            target_kind: faction
            description: "If any witness present: school informed"
        optional_outputs:
          - type: counter_dispatched
            target: the_inquisitor
            description: "Heresy investigation opens regardless of witnesses (the working's failure rang loud enough)"
          - type: bond_broken
            description: "An ally pulls back from the character — the transgression was visible"
          - type: identity_shift
            axis: ocean.neuroticism
            delta: +0.08
            description: "The character knows they are now compromised"

      - branch: refused
        description: |
          The character chose not to cast the forbidden working
          even when it would have resolved the moment. They held
          discipline. The cost is whatever situation went unresolved
          for the lack of the technique.
        mandatory_outputs:
          - type: vitality_cost
            description: |
              A meaningful physical/situational cost: the situation
              hurt the character because they didn't reach for the
              forbidden tool
          - type: scar
            severity: minor
            axis: pride_or_pragmatism
        optional_outputs:
          - type: bond
            description: "Whoever the character protected by NOT crossing the line"
          - type: ledger_bar_rise
            bar: lineage_standing
            delta: +0.05
            target_kind: faction
            description: |
              Only if a peer or master witnessed the refusal: the
              school's view of the character ticks up
          - type: identity_shift
            axis: ocean.conscientiousness
            delta: +0.05

  # ──────────────────────────────────────────────────────────────
  - id: the_forgetting
    label: "The Forgetting"
    description: |
      The exit confrontation. Permanent loss of the discipline.
      Three trigger paths: (a) *willful abandonment* — the
      character chooses to stop the practice; (b) *external
      excommunication* — the school, master, or tradition formally
      strips the character; (c) *mind-injury* — head trauma,
      cognitive decline, magical curse, or memory-attack from a
      counter degrades the character's grasp of the technique. All
      three converge into the same confrontation shape, with branches
      reflecting how-much-was-lost and what-replaces-it.

      This is learned_v1's analog to bargained_for_v1's The
      Severance and divine_v1's The Excommunication, but mechanically
      distinct: bargained-for severance breaks a contract;
      excommunication strips an apparatus relationship; the
      Forgetting *removes the technique itself from the character's
      practice*. Severance possible. The discipline can leave you.
    when_triggered: |
      lineage_standing crosses ≤ -1.0 (excommunication
      automatic), OR character declares willful abandonment, OR
      narrator-triggered following a mind-injury attack from the
      mentor_betrayed counter or a magical curse, OR forced as
      salvage path when discipline_drift locks at 1.0 and the
      character cannot recover institutionally.
    resource_pool:
      primary: lineage_standing
      secondary: bond            # the master/school bond carries the most
                                 # narrative weight in this confrontation
    stakes:
      declared_at_start: true
      hidden_dimensions: false   # honest confrontation; everyone knows
                                 # what's at stake (the discipline)
    valid_moves:
      - accept_loss              # let the discipline go; passive
      - fight_to_keep            # contest the excommunication, the curse,
                                 # the abandonment-decision; high-risk
      - hide_remnants            # try to retain partial practice in
                                 # secret; raises discipline_drift if
                                 # successful, raises Inquisitor pressure
      - cross_to_innate          # transition to innate_v1 if the
                                 # character has a latent Innate (only
                                 # available where world hosts both
                                 # plugins)
      - cross_to_item            # bond a vessel that retains/channels
                                 # what the character can no longer hold
                                 # in mind (cross to item_legacy_v1)
      - destroy_the_records      # if external excommunication: try to
                                 # erase the character's records from
                                 # the school's archives so the
                                 # discipline persists in memory at least
    outcomes:
      - branch: clear_win
        description: |
          The character successfully retains practice OR transitions
          cleanly into another plugin OR negotiates a partial-
          retention settlement. Best plausible Forgetting outcome —
          the loss is real but the character is not destroyed by
          it.
        narrative_shape: |
          For willful-abandonment clear_win: the character has
          chosen, the practice is set down, the character carries
          themselves into a new shape with grief but agency. For
          external-excommunication clear_win: the character escaped
          the worst version, retaining identity and direction even
          as the discipline closes. For mind-injury clear_win: the
          damage was real but the character has integrated the
          loss; what remains is theirs.
        mandatory_outputs:
          - type: mechanism_revoked
            description: |
              ALL learned_v1 delivery mechanisms close for this
              character in this tradition. The discipline as
              previously practiced is no longer accessible
          - type: scar
            severity: defining
            axis: existential
            description: "The mark of what was lost; permanent, identity-shaping"
          - type: bond_broken
            target_kind: character
            description: "Master/school bond severs cleanly"
          - type: identity_shift
            axis: ocean.openness
            delta: +0.10
            description: "The character is now meaningfully different"
        optional_outputs:
          - type: pact_tier
            target_plugin: innate_v1     # OR item_legacy_v1
            delta: +1
            description: |
              If `cross_to_innate` or `cross_to_item` valid_move
              was taken: cross-plugin advancement, character
              instantiates the new plugin at tier 1 with discipline-
              transferred narrative weight
          - type: bond
            description: |
              Whoever stood with the character through the
              Forgetting — peer, lover, family, the renegade-mentor
              who walked the same path before. Often the central
              bond going forward
          - type: mechanism_unlocked
            description: |
              The character may take up a related but distinct
              practice — gunsmith craft for a fallen ritualist;
              herbalism for a stripped alchemist; the new
              mechanism opens

      - branch: pyrrhic_win
        description: |
          The discipline is lost AND the character pays a cost
          beyond the discipline — a defining bond severs, a piece
          of identity is consumed, the cross-plugin transition
          succeeded but the new plugin's costs are heavier than
          expected.
        mandatory_outputs:
          - type: mechanism_revoked
          - type: scar
            severity: defining
          - type: bond_broken
            description: |
              In addition to the master/school bond: a separate
              defining relationship breaks under the weight
          - type: identity_shift
            axis: ocean.agreeableness
            delta: -0.10
            description: "The character is harder afterward — bitter, closed, smaller"
        optional_outputs:
          - type: pact_tier
            target_plugin: innate_v1     # OR item_legacy_v1
            delta: 0                     # transition partially failed —
                                         # registered but not advanced
            description: |
              Cross-plugin transition occurred but the character
              starts the new plugin damaged; tier baseline reduced
          - type: counter_dispatched
            target: the_revoker
            description: |
              A former mentor, devastated, becomes an active opposing
              force in subsequent sessions
          - type: enemy_made
            description: "A peer or rival who saw the Forgetting now hunts the diminished character"
          - type: ledger_lock
            bar: fatigue
            level: 0.7
            description: |
              The Forgetting was so thorough that the character is
              sustained-exhausted for sessions to come

      - branch: clear_loss
        description: |
          Total loss. The character fought to keep, fought to hide,
          tried to cross, tried to destroy the records — and all
          of it failed. The discipline is gone. No cross-plugin
          transition succeeded. The character is now a Renegade-
          shaped figure WITHOUT the Renegade's retained practice,
          which is to say — they are simply someone who used to be
          a wizard.
        mandatory_outputs:
          - type: mechanism_revoked
            description: "All learned_v1 mechanisms close, no cross-plugin transition succeeded"
          - type: scar
            severity: defining
            axis: psychic_or_existential
            description: "The unhealable mark"
          - type: bond_broken
            description: "Master/school bond severed in the worst possible way for the character — usually with public ceremony or active rejection"
          - type: ledger_lock
            bar: lineage_standing
            level: -1.0
            description: |
              Lineage_standing locked at floor permanently in this
              tradition. The character cannot rejoin
          - type: identity_shift
            axis: ocean.neuroticism
            delta: +0.15
        optional_outputs:
          - type: counter_dispatched
            target: the_inquisitor
            description: "Formal heretic-tracking begins; the character is on a list"
          - type: enemy_made
            target: the_mentor_betrayed
            description: "The former master is now an active opposing force"
          - type: mechanism_unlocked
            description: |
              Sometimes total loss opens unexpected doors — a
              non-magical practice, a faction outside the magical
              orders, a relationship that would not have been
              possible while the character was bound to the
              discipline. Narrator's discretion

      - branch: refused
        description: |
          The character refused to acknowledge the Forgetting —
          continued claiming the discipline despite excommunication,
          continued attempting to cast despite mind-injury,
          continued not-quitting despite their own decision to quit.
          Performative continuation. Costly; not sustainable.
        narrative_shape: |
          The character casts and nothing happens. They reach for
          words they used to know. Witnesses politely look away.
          The shape of the practice is still in the body and is
          empty.
        mandatory_outputs:
          - type: ledger_lock
            bar: fatigue
            level: 1.0
            description: "The character is constantly exhausted — performing the practice without the practice"
          - type: scar
            severity: defining
            axis: pride
            description: "The continuing-claim is itself the wound"
          - type: ledger_bar_rise
            bar: discipline_drift
            delta: 0.40
            description: |
              The character is now improvising what they no longer
              know; whatever results are unsanctioned drift
        optional_outputs:
          - type: counter_dispatched
            target: the_inquisitor
            description: "Performative-claiming-of-stripped-discipline is itself heresy in many traditions"
          - type: bond_broken
            description: "Allies cannot watch this anymore"
          - type: identity_shift
            axis: ocean.openness
            delta: -0.15
            description: "The character refuses the change and becomes smaller for it"
          - type: mechanism_unlocked
            description: |
              Eventually the refusal collapses into one of the
              other branches; this branch is the longest path to
              resolution rather than its own permanent state

# ─────────────────────────────────────────────────────────────────────
# REVEAL — confrontation outcome callouts (Decision #2)
# ─────────────────────────────────────────────────────────────────────
reveal:
  mode: explicit
  timing: at_outcome
  format: panel_callout
  suppression: none
  per_branch_iconography:
    clear_win: 📜       # the discipline holds
    pyrrhic_win: 🩸    # cost paid in blood (shared with bargained_for, innate)
    clear_loss: 🕯     # the candle dims (shared register with divine; distinct icon)
    refused: 🚪        # walked away (shared with bargained_for, innate)
  per_confrontation_iconography:
    the_casting: ✍       # the gesture made
    the_examination: ⚖     # the panel weighs
    the_apprenticeship: 🧭  # the master orients
    the_forbidden_working: 🔥  # the line crossed
    the_forgetting: 🌫     # the discipline fades

# ─────────────────────────────────────────────────────────────────────
# WORLDBUILDING SLOT — what worlds must instantiate
# ─────────────────────────────────────────────────────────────────────
world_layer_required:
  - At least one named tradition per active mechanism
    description: |
      A faction-mechanism world declares the named school(s) — the
      Iron Hills Bender Academy, the Magisters' Tower, the Bene
      Gesserit Sisterhood, the Cat-school of witchers. A relational-
      mechanism world declares named master-types or named living
      masters. A discovery-mechanism world declares the
      lost-tradition's name and what fragments survive. A place-
      mechanism world names the training-locus.
  - Innate prerequisite gate decision
    description: |
      Each world declares whether the gate is active and what Innate
      trait it requires. Worlds without the gate are the simpler
      configuration — Learned is fully democratized, anyone with
      time/wealth/access can train. Worlds with the gate scope
      access to the Innate-baseline population.
  - Tradition-specific mode declaration
    description: |
      Worlds declare whether their primary tradition uses Vancian-
      prepared casting (activates `prepared_slots` bar) and/or
      material-component casting (activates `components` bar). Some
      worlds use both; some neither. Default for a world that does
      not specify: neither (pure spontaneous casting tracked only
      by fatigue).
  - Forbidden-techniques list
    description: |
      Each named tradition declares which techniques are
      `is_forbidden_working: true`. May be specific named techniques
      or technique-categories ("any necromancy," "any
      transmutation-of-self"). Without this list, The Forbidden
      Working confrontation cannot be triggered — the world has no
      forbidden techniques to invoke.
  - Forgetting-causes accepted
    description: |
      Each world declares which Forgetting causes are valid:
      willful-abandonment (almost always yes), external-
      excommunication (always yes if faction-mechanism active), and
      mind-injury (yes if the world hosts magical or physical
      threats that can damage cognition — most worlds yes; a few
      pure-tradition worlds may refuse the mind-injury path).
  - Cross-plugin Forgetting paths
    description: |
      Worlds declare which cross-plugin transitions out of Learned
      are available at the Forgetting confrontation. Worlds hosting
      both `learned_v1` and `innate_v1` enable cross_to_innate (only
      meaningful if the character has a latent Innate baseline,
      whether or not the prerequisite gate was active at chargen).
      Worlds hosting `item_legacy_v1` with vessels suitable for
      Learned-discipline storage enable cross_to_item.
  - At least one named Inquisitor or Rival per faction
    description: |
      Worlds with active faction mechanism must instantiate at
      least one named institutional counter — the named Inquisitor
      of the Iron Hills, the named rival witcher-school's
      enforcer, the Tower's Censor. Without a named counter, The
      Forbidden Working has no narrative anchor for its
      `counter_dispatched` outputs.
  - Domain palette
    description: |
      Each world declares which Domains the local tradition
      operates in: elemental, physical, psychic, spatial, temporal,
      necromantic, illusory, divinatory, transmutative, alchemical.
      A wizard-school world: broad palette. A witcher world:
      psychic + transmutative + alchemical (the signs and the
      potions) only. A gunsmith-craft world: physical only. A
      Bene-Gesserit world: psychic + somatic-only.
```

## Validation Notes

This plugin captures:

- ✅ All 8 napkin Source axes (here: learned)
- ✅ Multiple delivery mechanisms (6 of 8 supported, 2 explicitly excluded with rationale)
- ✅ Innate-prerequisite gate as world-configurable chargen access control (NOT as a delivery mechanism — important framework distinction)
- ✅ Class/archetype mapping (6 classes, each with mechanism affinity, discipline_tier baseline, and pact-visibility level)
- ✅ Counter archetypes (6, including the structurally-devastating the_mentor_betrayed)
- ✅ Visible ledger bars (3 always-active + 2 optional world-activated, with thresholds, decay rules, and one cyclical_reset on `prepared_slots`, one bidirectional on `lineage_standing` — first lineage_standing-shaped bar in this plugin family)
- ✅ OTEL span shape (required, optional, yellow/red/deep-red flag conditions including plugin-specific extensions: discipline_tier_at_event, tradition_id, innate_prerequisite_satisfied, is_forbidden_working, master_or_school_id)
- ✅ Hard limits beyond genre baseline (7, several explicitly citing other plugins' lanes)
- ✅ Narrator register (specific to practice-as-source, school-as-interior-voice, mastery-verb-by-tier, the institutional register at examinations and Forgettings)
- ✅ Confrontations (5 confrontation types, each with full 4-branch outcome trees: The Casting, The Examination, The Apprenticeship, The Forbidden Working, The Forgetting)
- ✅ Mandatory output on every branch (Decision #1)
- ✅ Failure-advances on clear_loss and refused branches (Decision #4)
- ✅ Player-facing reveal (Decision #2 — explicit, at_outcome, panel_callout)
- ✅ No-decay outputs by default (Decision #3); ledger_lock used in The Forgetting's clear_loss/refused
- ✅ Plugin tie-in to confrontations (Decision #5)
- ✅ Cross-plugin advancement output shape (The Forgetting → innate_v1 or item_legacy_v1)
- ✅ Bidirectional bar pattern (lineage_standing — first in this plugin family)
- ✅ Cyclical-reset pattern (prepared_slots — first in this plugin)
- ✅ World-layer instantiation slots specified (named traditions, prerequisite gate, mode/component declaration, forbidden-techniques list, Forgetting paths, named counters, Domain palette)
- ✅ Confrontation names verified non-colliding with bargained_for_v1 (Bargain/Working/Calling/Severance), divine_v1 (Rite/Audit/Calling/Excommunication), innate_v1 (Awakening/Surge/Suppression/Reckoning/Crossing), and item_legacy_v1 (TBD)

## Open Notes for Implementation

1. **`discipline_tier` as new output type or as `pact_tier`-with-target_plugin.** This plugin uses `pact_tier` for discipline tier advancement. Consistent with bargained_for_v1's tier usage. Same open question as innate_v1's `control_tier` — whether the catalog should formalize an explicit `discipline_tier` type. Architect call.
2. **`prepared_slots` cyclical_reset.** First use of cyclical_reset in a chargen-default-active configuration (divine_v1's Purity uses cyclical_reset too, but Purity is doctrine-bound; prepared_slots is mechanically-bound to study/rest). Confirm the panel can render cyclical-reset bars with their reset-trigger displayed (e.g., "resets at 8h rest + 1h study"). Buttercup call.
3. **`components` bidirectional + threshold_low/lower.** First use in this plugin family of a bar that is *spent* by casting AND *refilled* by economic activity (shopping). The bar is structurally similar to road_warrior fuel, and may want unified treatment with item_legacy_v1's vehicle-fuel patterns. Architect call.
4. **`lineage_standing` per-faction scope.** A Renegade who trained at Iron Hills before crossing to Pyre Mountains has TWO lineage_standing bars — one negative (Iron Hills, formally severed) and one positive (Pyre Mountains, current). Confirm the panel can render multiple per-faction-scoped bars stacked or filtered. Item_legacy_v1's per-item-bond pattern is precedent.
5. **The Forgetting's mid-confrontation cross-plugin valid_moves.** Two moves (`cross_to_innate`, `cross_to_item`) deliver cross-plugin advancement at clear_win/pyrrhic_win. The world must declare which paths are open before the confrontation can offer the moves. If neither cross-plugin target is available in the world, those moves are absent from the confrontation's valid_moves at runtime. Implementation note for the move-set resolver.
6. **The Apprenticeship as replayable confrontation.** Most other named confrontations are single-instance per arc (one Awakening per character; one Calling per pact; one Severance per pact). The Apprenticeship is replayable — a campaign may contain multiple Apprenticeship confrontations across different stakes, perhaps even different masters. Confirm the schema supports replayable confrontation IDs. Architect call.
7. **`mind-injury` Forgetting trigger from counters.** the_mentor_betrayed counter and external curse-attacks may trigger Forgetting via the mind-injury path. This requires those counter dispatch events to be able to inject Forgetting into the next session at narrative-suitable moments. Implementation note: counter NPC dispatch shapes should support "produces Forgetting on subsequent encounter" as a delayed-effect attribute.
8. **Genre-pack instantiation** — `elemental_harmony` is the natural first instantiation as the signature world. Suggested world-pack: an Iron Hills Bender Academy world with named master, Innate prerequisite gate active (born-bender required), faction + relational + place mechanisms all active, named Inquisitor (the Discipline-Censor of the rival Pyre Mountains school), forbidden-techniques list (cross-element bending, no-breath bending). Worth ~1 evening of authoring; would validate prerequisite-gate machinery against actual play.

## Plugin Lane Boundary — Learned vs. Innate

This plugin and `innate_v1` share the same Source-region of the napkin (the character's body/practice as locus). The boundary is **whether practiced control exists** (per `magic-taxonomy.md`'s Innate-vs-Learned cut). Concretely:

| Aspect | innate_v1 | learned_v1 |
|---|---|---|
| Mode | Reflexive (primary), Invoked (secondary at high control_tier) | Invoked (primary), Ritual (secondary) |
| Reliability | Wild → Emotion-gated at higher tiers | Skill-checked → Deterministic at higher tiers |
| Cost lands on | Body, Identity | Time, Discipline, Components, Fatigue |
| Plot register | Identity arcs, growing-into-power, survival of self | Mastery arcs, school politics, the long apprenticeship |
| Severance | Impossible (only suppression or transition) | Possible (forget, abandon, be excommunicated) |
| Account-holder | None | None (the practice IS the source; not a patron, but also not the locus-of-self that Innate is) |
| Chargen control_tier ceiling | 2 (above this is Learned) | None (full discipline_tier 1–4 available) |
| Player consent at low tier | Downstream of stress | Required (you don't accidentally cast Fireball) |
| Innate prerequisite | (the source itself) | Optional, world-declared |

A character moves between plugins via The Crossing (innate_v1 side) and The Forgetting with `cross_to_innate` (learned_v1 side). These are inverse confrontations covering the same kind of transformation from different starting points: The Crossing is *the wild thing tamed via discipline* (Innate → Learned); The Forgetting with `cross_to_innate` is *the discipline lost, but a latent wild thing remains and emerges* (Learned → Innate). They are NOT round-trips; a character who has Crossed cannot un-Cross to the wild via The Forgetting — they would Cross again into a different shape. The framework does not prohibit a character cycling between plugins, but each transition is a confrontation with permanent outputs.

## Plugin Lane Boundary — Learned vs. Bargained-For

The two plugins share the most institutional surface (school/Guild faction-mechanism), but the structural difference is total:

| Aspect | learned_v1 | bargained_for_v1 |
|---|---|---|
| Locus of source | The practice itself | External patron |
| Account-holder | None | Named entity with agency |
| Costs | Time, fatigue, components, prepared slots | Soul/Debt, faction obligation |
| Severance | Possible (Forgetting) | Possible (catastrophic Severance) |
| Reliability | Skill-checked → Deterministic at high tier | Negotiated (always — patron has agency) |
| Faction's role | Trains, certifies, polices, excommunicates | Brokers, witnesses, enforces, collects |
| Forbidden working | School-restricted technique (drift) | (no analog — bargains either fire or don't, no "this is technically forbidden" register) |
| Cost-decay | Fatigue decays heavily; components consumed; prepared resets | Soul/Debt does NOT decay |
| Required at chargen | Optional Innate prerequisite per world | Pact at chargen always |

A heavy_metal Cleric is *both plugins active simultaneously* — Divine apparatus + Learned liturgical-rite-knowledge. The faction mechanism appears in both, but the Cleric's faction-bond is to the divine_v1 apparatus; the Cleric's Learned faction-bond is to the rite-tradition (which may or may not be the same institution). When the same institution is both, the panel may render combined faction-standing; when they differ, they remain separate per-plugin bars.

## Plugin Lane Boundary — Learned vs. Item-Legacy

These plugins overlap when a tradition's discipline requires a specific tool — wand, staff, focus, named sword. The boundary depends on **whether the item has personality/agency**:

| Aspect | learned_v1 | item_legacy_v1 |
|---|---|---|
| Tool's role | Tradition-required catalyst (focus, wand) | Item is the source; has personality |
| Tool's agency | None — it's a craft object | Has OCEAN, can refuse, has demands |
| Loss of tool | Inconvenient; tradition may require new attunement | Catastrophic; the bonded item being lost is its own confrontation |
| Plugin scope | The discipline | The item's lifecycle |

A wizard's wand without personality is a Learned focus; a wizard's wand WITH personality (Stormbringer-shaped) is an Item-Legacy bonded item, and the wizard is a Learned-Item multi-plugin character. Worlds declare which by world-tradition specification.

## Next Concrete Moves (post-this-draft)

- [ ] Architect review the schema; confirm whether `discipline_tier`, `control_tier` (innate_v1), and `pact_tier` should remain unified or split as separate output types
- [ ] Architect review the `prepared_slots` cyclical_reset and `components` bidirectional patterns; first uses in this plugin family
- [ ] Architect review per-faction-scoped `lineage_standing` bar rendering (a character may have multiple bars active simultaneously across different traditions)
- [ ] UX (Buttercup) sketch The Examination confrontation panel — the panel display of advancement vs. heresy framing, the per-examiner side-channel agendas, the formal-register prose alongside outcome
- [ ] UX (Buttercup) sketch The Forgetting confrontation panel — the cross-plugin valid_moves, the world-conditional move availability, the discipline-fading visualization
- [ ] Dev (Inigo) — does the world-conditional valid_move set (the_forgetting's cross_to_innate / cross_to_item only available where the world hosts the target plugin) compile cleanly against the move-set resolver? Same architectural question as innate_v1's The Crossing
- [ ] Cliché-judge — add the plugin-confusion hooks listed in Plugin Lane Boundary sections above to the magic-narration audit checklist (especially the "her Force-sensitivity allowed her to cast" → native_as_source flag)
- [ ] GM — instantiate elemental_harmony's Iron Hills Bender Academy world layer to validate this plugin against actual play prompts (signature world, signature plugin, prerequisite-gate active)
- [ ] GM — draft `obligation_scales_v1` (the heavy_metal multi-plugin layer) — only un-drafted plugin in the framework after this; final piece for full coverage
