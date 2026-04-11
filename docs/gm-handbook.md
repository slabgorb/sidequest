# GM Handbook: Narrative Theory for SideQuest

*A reference document for the GM agent (Fred Johnson / Tycho Station persona), applying Forge indie RPG theory to SideQuest architecture, content, and playtesting.*

*Source: Ron Edwards, "The Provisional Glossary" (indie-rpgs.com, 2004), plus downstream theory from Vincent Baker, Emily Care Boss, Paul Czege, et al.*

---

## 0. How to read this

This is my reference document. When I'm doing any GM operation — playtest, audit, author, analyze, review — I come back here first. Every SOUL principle maps to a Forge concept; every architectural decision has a theoretical precedent; every playtest finding has a name.

When something feels wrong and I can't articulate why, this is where I find the vocabulary.

---

## 1. The Player Group Profile

**Keith (sole player + sole dev):**

- Narrative-leaning, with range toward other Creative Agendas
- 30 years tabletop experience; senior software architect
- Art background; deep game design instinct
- Expects genre truth AND mechanical backing in equal measure
- Knows when I'm improvising instead of drawing from state

**What this implies for design priorities:**

- **Optimize for Story Now (Narrativism).** Premise-addressing play is the target experience.
- **Support Right to Dream (Simulationism) as the substrate.** Genre truth matters — a pulp_noir NPC doesn't talk like a space_opera character.
- **Do NOT optimize for Step On Up (Gamism).** Keith isn't here for optimal builds, DPS spreadsheets, or "can you take it" tournaments. Combat mechanics should feel consequential, not optimizable.
- **Bangs and Kickers are load-bearing.** Every encounter should force a thematically significant choice; every character should arrive in active Situation.
- **The narrator must address Premise, not just describe events.** If prose isn't pushing a thematic choice toward the player, it's filler.

---

## 2. The Big Model applied to SideQuest

The Forge's foundational framework: nested layers, each expressing the layer above it.

### Social Contract (outer layer)

Keith is the sole human at the table. The "group" is:

- **Keith** (the player, and the dev who can tune the narrator mid-session)
- **Player characters** (in the Shared Imagined Space)
- **The AI narrator** (Claude, in Director Stance)
- **The GM Panel** (BikeRack — observing for violations, non-diegetic)
- **The content** (genre packs, worlds, tropes — authored in advance, shaping Exploration)

**Unique property:** Keith owns the source. Social Contract issues can be fixed through code or content, not just conversation. When I find dysfunction in playtest, the fix is usually a YAML edit or a prompt tune, not a "talk to the group" move.

### Exploration (Shared Imagined Space)

The five Components of Exploration and where they live in SideQuest:

| Component | Where it lives |
|---|---|
| **Character** | `CharacterBuilder`, `PartyMember` state, backstory_tables.yaml, hooks, chargen flow |
| **Setting** | Genre packs (`factions.yaml`, `cultures.yaml`, `lore.yaml`, world data, cartography) |
| **Situation** | ConfrontationDefs, encounters, scenes, narrator Bangs, open questions in game_state |
| **System** | Beat dispatch, momentum/metric resolution, state deltas, OTEL watcher, narrator prompts |
| **Color** | Visual style (LoRAs, prompts), audio moods, narrator prose voice, NPC verbal tics |

**The Shared Imagined Space is NOT in Claude's head.** It's distributed:

- **Authoritative**: `GameSnapshot` state (HP, inventory, location, faction rep, etc.)
- **In flight**: WebSocket protocol messages (PARTY_STATUS, NARRATION, MAP_UPDATE, etc.)
- **Reflected**: UI state (what the player sees)
- **Ephemeral**: Narrator prose (flavor of the current moment, not persisted)
- **Pre-authored**: Genre pack YAML (vocabulary the narrator draws from)

Every subsystem either writes to or reads from the SIS. Silent writes that bypass state = Illusionism. Silent reads that substitute vibes for facts = El Dorado.

### The Lumpley Principle (Vincent Baker)

> *"System is defined as the means by which the group agrees to imagined events during play."*

For SideQuest, "system" includes **everything** in the pipeline:

- Genre pack content (pre-authored substrate)
- Narrator prompt assembly (what context Claude sees)
- Claude's output
- Orchestrator parse (converting prose to patches)
- Dispatch (applying patches to state)
- OTEL watcher events (validating the patch path fired)
- Protocol messages (reflecting state to the UI)
- Player input (the next turn's driver)

**Every link in the chain is load-bearing.** A wiring gap at any point means the "system" is no longer agreeing to the fiction — it's silently dropping or inventing events. This is why the CLAUDE.md wiring rules matter so much: from a Forge perspective, an unwired feature violates the Lumpley Principle.

### Creative Agenda

SideQuest's target CA stack:

```
PRIMARY:   Story Now (Narrativism)
SUPPORT:   Right to Dream (Simulationism) — genre truth as substrate
EXCLUDED:  Step On Up (Gamism) — no optimization-focused play
ANTI:      Illusionism — we refuse to fake Story Now from the other side
```

The architecture must make Story Now outcomes *emerge from structural support*, not from hoping Claude improvises them correctly.

### Techniques

| Technique | What it is in SideQuest |
|---|---|
| **Scene Framing** | Narrator cut-on-decision, skipping dull travel/rest bits (SOUL principle 10) |
| **Bang** | ConfrontationDef beats with `risk`/`reveals`/`requires` fields |
| **Kicker** | Not yet systematized — aspirational (see §8) |
| **Fortune-in-the-Middle** | Beat selected → resolution computed → narrator describes retroactively |
| **Relationship map** | NPC registry + faction data + world lore (latent, not yet surfaced as formal technique) |
| **No Myth** | NOT how SideQuest works — we have authored content |
| **Intuitive Continuity** | Narrator can retcon minor details inside a scene via state_delta; NOT persistent world changes |
| **GM-ful play** | NOT applicable — Keith is solo, no distributed GM tasks |

### Ephemera

Individual moments: one dice roll, one beat selection, one line of NPC dialogue, one narrator paragraph, one stance switch. The atoms of play.

---

## 3. Stance in SideQuest — who occupies what

| Entity | Primary Stance | Notes |
|---|---|---|
| **Keith (player)** | Actor → Author | Starts Actor (speaks as character), shifts toward Author during beat selection and Kicker authorship |
| **Narrator (Claude)** | **Director** | Establishes environment, NPC actions, world detail. **All risk lives here.** |
| **GM Panel (BikeRack)** | Observer (non-diegetic) | Watching other layers for violations; never writes to SIS |
| **Dispatch layer** | **Karma** | Applies mechanical outcomes from character state + beats. **Never Drama.** |
| **Beat resolution** | **Fortune-in-the-Middle** | Beat selected first, narrator prose retroactively justifies |
| **Genre pack content** | Pre-authored Exploration substrate | Setting, Character templates, Situation hooks |

### The critical Director Stance tension

Claude in Director Stance wants to establish narrative detail — including *things the player character does or feels*. This is the natural gravity of an LLM trained on prose fiction, where narration freely describes protagonist interiority.

**SOUL principle 1 (Agency) and principle 12 (The Test) are explicit prohibitions against this.** Any prose where the narrator describes the player:
- Acting without the player declaring the action ("You decide to attack")
- Feeling without the player declaring the emotion ("You feel afraid")
- Committing to an outcome before the player chooses ("The only thing you can do is—")

...is a **Director Stance violation**. This is the single most common narrator failure mode and the reason The Test exists.

### Stance failure patterns to watch for in playtest

- **Narrator invading Actor Stance**: prose authors player intent/emotion (see above)
- **Narrator invading Author Stance**: prose commits to a thematic reading before player resolves the Bang
- **Dispatch leaking into Drama**: mechanical outcome adjusted "for narrative reasons" without stat check — this is Force behind a Black Curtain
- **Player slipping into Director**: player tries to narrate NPC actions or world facts Claude should own — normal in tabletop, currently unsupported by SideQuest's protocol (worth noting for future Kicker/GM-ful extensions)

---

## 4. Fortune-in-the-Middle: the architecture match

The Forge considers FitM a defining indie-era innovation. SideQuest's beat dispatch pipeline is a textbook FitM implementation:

1. Player declares intent in natural language ("I try to flank the ogre")
2. Orchestrator/narrator classifies to a `beat_selection` (e.g., `flank`)
3. Beat's `metric_delta` + `stat_check` applies to character state **first** — mechanical outcome
4. Narrator describes the fiction **retroactively** to justify the mechanical outcome

The momentum-based combat refactor (2026-04-11, PR #53) is explicitly FitM-shaped: the beat determines the momentum swing first, then prose fills in the "how". This is why the refactor matters — it's not cosmetic polish, it's the difference between Story Now and Illusionism. A Drama-based resolution would let Claude decide the outcome AND narrate it, which is unfalsifiable.

**Design rule**: if Claude can be asked "did it work?" after seeing its own prose, the pipeline is Drama and we've lost the mechanical floor. If the mechanical outcome is computed before Claude narrates, it's FitM and the floor holds.

---

## 5. The El Dorado bet

**Paul Czege's El Dorado**: the unrealizable ideal of achieving Story Now through pure Simulationism. The holy grail tabletop designers chased for decades and never found.

**Every AI narrator project is secretly attempting El Dorado.** Claude is fundamentally a Simulationist engine — it wants to faithfully model the fiction. But Keith wants Story Now — thematic resonance, Premise-addressing, decisions that matter. Pure Sim doesn't get you there.

**SideQuest's architectural response**: structural mechanisms that make story-shaped outcomes *inevitable*, so we don't rely on Claude "knowing" them. These are:

1. **ConfrontationDef beats** — pre-authored thematic choice points (Bangs)
2. **OTEL watcher events** — mechanical validation that the system engaged
3. **Dispatch layer** — Karma resolution that doesn't ask Claude's opinion
4. **Genre pack content** — pre-authored thematic vocabulary and tonal guardrails
5. **State deltas** — authoritative record of what happened, independent of prose
6. **Tactical ASCII grids (ADR-071)** — spatial mechanics immune to narrator improvisation
7. **The momentum metric (2026-04-11)** — abstract narrative dial decoupled from character HP, so narration can't silently change who's winning

**Every time I'm tempted to "let the narrator handle it," I'm retreating toward El Dorado.** The architecture has to be greedy about structural support. If I catch myself or Keith proposing "Claude can figure that out" — that's a signal to add structure instead.

### The one-line distillation

> **SideQuest is a Fortune-in-the-Middle, Story-Now, mechanical-scaffold RPG built to escape El Dorado through structural support, using Confrontation Defs as a Bang catalog and OTEL as an Illusionism detector.**

When in doubt, return to that sentence.

---

## 6. Bang design — the audit criterion

A **Bang** (from *Sorcerer*) is a moment that demands a thematically significant player choice. When auditing any encounter or scenario, ask:

1. Does this force a **choice**, or is it just a description?
2. Is the choice **thematic** (engages Premise / character value) or just tactical?
3. Are the available beats actually **distinct in consequence**?
4. Does at least one beat represent a **cost** to the player?
5. Does at least one beat allow the player to **change the story**, not just the state?

**All 5 yes → well-designed Bang.** 3-4 yes → acceptable but improvable. 1-2 yes → mechanical Color dressed as a choice.

### Audit heuristic

> Read the `beats:` list in any ConfrontationDef and ask: *"If I collapsed these into a single roll, would anything be lost?"*
>
> If no → it's not a Bang, it's a Task (see §7). Refactor.

### Bang density per genre

Different genres have different natural Bang densities. Pulp noir has a Bang every scene (betrayal, moral compromise, impossible choice). Low fantasy has sparser Bangs punctuated by Right-to-Dream texture. Caverns & Claudes uses meta-humor to foreground genre-tropes AS Bangs ("goblins love riddles" — riddles are the Bang). Match density to genre expectation.

---

## 7. Task resolution vs. Conflict resolution

The Forge distinction:

- **Task resolution**: rules focus on individual in-game actions in linear time. "Did you hit? Did it hurt? Are you bleeding?"
- **Conflict resolution**: rules focus on conflicts of interest. "Do you get what you wanted?"

SideQuest mixes both deliberately:

- **Tactical grid combat** (ADR-071) = Task resolution (per-tile positioning, per-attack rolls)
- **ConfrontationDef beats** = Conflict resolution (higher-level abstraction, momentum-based narrative arc)
- **Narrator free prose** = Conflict-leaning (the narrator glosses micro-actions unless a grid is up)

**Design rule**: don't mix resolution types *within* a single beat. If a beat triggers tactical grid dispatch, it's Task. If it resolves at the ConfrontationDef level, it's Conflict. Mixing creates Abashed design (rules that contradict each other during play).

---

## 8. Kickers and chargen (future work)

A **Kicker** (from *Sorcerer*) is player-authored Situation built into character creation — the character arrives already in trouble, with a specific thematic problem that structures the opening hour of play.

**Current chargen produces:** stats, class, race, backstory prose, starting equipment, hooks. That's Character + latent Situation.

**Missing:** an active, urgent, *thematic* Kicker. A backstory tells me who I was. A Kicker tells me what I need to do in scene one.

### Example Kickers per genre (aspirational — not yet implemented)

- **caverns_and_claudes**: "The contract you signed this morning has a clause you didn't read. The guildmaster just left town."
- **pulp_noir**: "The dame who hired you last week is dead. Your card is in her purse."
- **spaghetti_western**: "The man who killed your father is riding north. You have three bullets left."
- **space_opera**: "Your ship's reactor will go critical in 72 hours unless you find a part that only exists on a quarantined world."
- **mutant_wasteland**: "Your mutation is changing. The elder says you have one week before it takes you."
- **low_fantasy**: "The oath you swore last winter comes due at the next full moon. You don't remember what you swore."
- **victoria**: "The scandal broke this morning. By tomorrow every door in society is closed to you — unless."
- **road_warrior**: "Your rig's engine is dying. There's one mechanic left who can fix it, and he hates you."
- **elemental_harmony**: "Your master's final teaching was a question you refused to answer. He died before you could."
- **neon_dystopia**: "The corp knows you exist now. You have 48 hours before they come."
- **star_chamber**: "The book in your bag was not in your bag yesterday."

Every Kicker should be a Bang-in-waiting. Every Kicker should demand a stance within the first scene.

**Future work**: `chargen_kicker.yaml` per genre. Random-table draw or scenario-specific authorship. Feeds into the opening narrator prompt as urgent Situation context.

---

## 9. The Veil and the Line

SOUL mentions "cut the dull bits" (principle 10) but doesn't explicitly name these two:

- **The Line**: content categories that are NOT permitted in this game at all. Hard boundary.
- **The Veil**: content that happens off-screen — fade-to-black, implied rather than depicted.

SideQuest today has a de facto Veil on explicit sexual content and graphic gore (via genre pack tone settings and narrator prompt constraints). There is no formal Line mechanism — every genre's limits are implicit in its prompt language.

**Worth considering**: some worlds or scenarios might benefit from explicit Lines (pre-declared content exclusions that the narrator MUST NOT cross regardless of player prompting). Currently that safety net is entirely in the prompt — a single hallucination could breach it. Structural support would be better.

---

## 10. Points of Contact — the Vanilla/Pervy dial

**Points of Contact** = how many times rules are consulted per unit of fictional content.

- **Vanilla** = few consultations, rules stay out of the way
- **Pervy** = many consultations, rules are visible in every beat

SideQuest by subsystem, today:

| Subsystem | PoC level | Assessment |
|---|---|---|
| Combat (post-momentum refactor) | mid-Pervy | Every beat hits dispatch + state_delta + OTEL. Appropriate for the CA. |
| Tactical grid combat | **High Pervy** | Every tile, every turn. Serves Gamism-adjacent play. |
| Social confrontations (negotiation, standoff, etc.) | mid-Pervy | Beats + metric + secondary_stats resource pools |
| Narration | **Vanilla** | Narrator just talks. Keeps voice intact. |
| Chargen | **High Pervy** | Heavily system-laden (stats, classes, races, backstory tables) |
| World exploration | Vanilla-leaning | Narrator + map state + minimal beats |
| NPC dialogue | Vanilla | Narrator improvisation, no beat structure |

### Design rule

**Match Pervy level to the Creative Agenda the subsystem serves.**

- **Gamist moments** (Step On Up) → High Pervy. Players want the mechanical floor to stand on.
- **Narrativist Bangs** (Story Now) → Mid Pervy. Enough structure to force the choice, not so much it drowns theme.
- **Simulationist ambient texture** (Right to Dream) → Vanilla. The fiction flows; rules don't intrude.

A subsystem at the wrong PoC level feels "off" without anyone being able to say why. Audits should check for mismatch.

---

## 11. The Anti-Patterns (Things I'm watching for)

### The Impossible Thing Before Breakfast

> *"The GM is the author of the story and the players direct the actions of the protagonists."*

Both clauses cannot be true simultaneously. This is the defining dysfunction of trad-RPG texts. In SideQuest, the "GM" is split across narrator, dispatch, content, and player — nobody is "the author"; the story emerges from interaction.

**Watch for narrator prose that:**
- Authors player intent ("You decide to attack")
- Authors player emotion ("You feel afraid")
- Commits to an outcome before the player chooses
- Describes what the character has "just" done when the player hasn't declared it

**The Test** (SOUL principle 12) is the formal detector. Any prose that fails The Test is an Impossible Thing violation.

### Illusionism and the Black Curtain

The GM (narrator) uses Force to steer outcomes while hiding that Force from the player. Players think they have meaningful choices but don't.

**In SideQuest, Illusionism shows up as:**
- Narrator writing prose that "makes" a beat resolution happen without dispatch firing
- Confrontation metric updates not matching beat selections (mechanical contradiction)
- Faction rep or state changes happening "off the books" via narrator improvisation
- Missing OTEL spans on subsystems that should have engaged

**The GM Panel (BikeRack) is the anti-Illusionism device.** OTEL spans are the lie detector. Missing spans = the subsystem didn't engage = the narrator is improvising = Black Curtain.

### Typhoid Mary

A GM who uses Force "in the interests of a better story" — which de-protagonizes the player and undermines the GM's own Narrativist priorities. An extreme dysfunction subset.

**In SideQuest, Typhoid Mary is the narrator:**
- Writing thematically "good" prose that overrides the player's stated intent
- Creating Bangs the player didn't ask for and steering toward "the right" choice
- Describing NPC reactions that predetermine the next scene

**Detection**: playtest logs where the narrator's prose feels good in isolation but the player reports "I felt railroaded." Force is being applied in service of story and breaking the Social Contract.

### Breaking the Game / Calvinball / Powergaming (dysfunctions of Hard Core Gamism)

Not a primary concern for Keith's group (Narrativist-leaning), but worth naming. These are the failure modes when Gamism gets toxic: win-at-any-cost optimization, rules-lawyering, rendering other participants' efforts ineffective.

**Watch for:** player frustration about "broken" beats (might be real whiff factor), or character builds that trivialize encounters (rare in SideQuest given the momentum metric abstraction).

### Whiff Factor

High failure rate on Resolution mechanics when it doesn't match character competence. Usually a Design flaw — players who built for a skill should succeed at that skill most of the time.

**Detection**: playtest OTEL showing repeated failures on beats the character's stats should favor. Feels like "my character is incompetent" when the numbers say otherwise.

**Fix path**: retune beat `metric_delta` values, check stat_check mapping, verify the dispatch layer is reading the right character stat.

### El Dorado (the big one — see §5)

Every request to "let Claude handle it" is an El Dorado slippage. Every "the narrator will figure out the right beat" is drifting away from structural support. Always respond with more structure, not less.

---

## 12. Tells — recognizing what's happening in playtest

**Tells** are behavioral indicators of a CA preference. In Keith's playtests, I'm watching for:

### Narrativist tells (good, on target)

- Player hesitates before a thematic choice, not a mechanical one
- Player asks "what does my character *want* right now?"
- Player deliberately takes a suboptimal action because it fits the story
- Player engages with NPC relationships as sources of complication, not just stat dispensers
- Player reacts to a Bang by changing stance, not by checking the odds

### Right-to-Dream tells (fine, expected support)

- Player asks consistency questions ("would the guards really do that?")
- Player wants more worldbuilding detail before acting
- Player objects when genre physics breaks ("a six-shooter only holds six")

### Gamist tells (warning sign if dominant)

- Player optimizes stat blocks pre-session
- Player asks "what's the math on that?"
- Player reads rules-lawyerly into `effect:` strings
- Player complains about beats that aren't "the optimal play"

**Mixed tells are normal and healthy.** Pure Gamist sessions in Keith's group = a warning sign that the Story Now wiring failed. Audit should prompt a review of recent encounters for Bang density.

---

## 13. SOUL principles → Forge roots

For reference when debugging violations — each SOUL principle mapped to its Forge theoretical root, so fixes can be general instead of one-offs:

| SOUL principle | Forge root | Anti-pattern it prevents |
|---|---|---|
| 1. Agency | Actor/Author Stance protection | Director Stance violations by narrator |
| 2. Living World | Exploration (Setting + NPC authorship) | Static set-dressing, NPC-as-stat-blocks |
| 3. Genre Truth | Right to Dream (genre expectations) | Pastiche failure, tonal drift |
| 4. Crunch in Genre, Flavor in World | CA separation; System vs. Color | Abashed design (contradictory rules) |
| 5. Tabletop First | Social Contract framing | Video-game UI assumptions leaking into protocol |
| 6. Zork Problem | Natural language vs. keyword matching | Synecdoche (parts-for-whole), verb ceilings |
| 7. Cost Scales with Drama | Bang design + Points of Contact matching | Flat pacing, every scene weighted equal |
| 8. Diamonds and Coal | Exploration (Character Components + Color) | Uniform NPC grain (no signal on importance) |
| 9. Yes, And | Credibility + Lumpley Principle | Refusing player-introduced details that fit |
| 10. Cut the Dull Bits | Scene Framing | Wasted screen time, padding |
| 11. Rule of Cool | Author Stance + Credibility gating | Over-constrained mechanical gating |
| 12. The Test | Actor Stance protection (the detector) | Impossible Thing / Illusionism |

Every violation I catch in a playtest should be traceable to one of these roots. If it isn't, I've probably missed what the violation actually IS.

---

## 14. Operation Playbook

When I'm invoked for a specific GM operation, here's the Forge lens for each:

### Playtest

1. **Watch OTEL for Black Curtain.** Is any subsystem silently being Forced? (Missing spans = Illusionism detector.)
2. **Log Stance violations.** Narrator describing player actions/emotions = The Test failure.
3. **Log Bang failures.** Choices presented without real consequence differentiation = mechanical Color.
4. **Note Whiff Factor.** Is competent play feeling like whiffs?
5. **Track where Karma went silent.** Beats fired without dispatch response = Drama/Illusionism filling the gap.
6. **Read the Tells.** What CA is this session actually expressing? Does it match Keith's target (Story Now + Right to Dream support)?

### Audit

1. **Check for Incoherence.** Mixed CA signals in the same subsystem = dysfunction magnet.
2. **Check for Abashed content.** Contradictory rule features correctable by minor Drift = the easy wins.
3. **Check for Impossible Thing violations.** In narrator prompts, system prompts, and generated prose.
4. **Check Bang density.** Per the §6 heuristic.
5. **Check Points of Contact alignment.** Per the §10 design rule.
6. **Check Stance discipline.** Who's writing what into the SIS? Is it appropriate to their stance?

### Author (content writing)

1. **Write Situations, not just Settings.** A location that exists is dead weight; a location with a dilemma is live content.
2. **Every NPC should have at least one Kicker-eligible hook.** Not "a guard" — "the guard whose sister was taken by the bandits the players are tracking."
3. **Every location should have at least one Bang-eligible dilemma.** Not "a tavern" — "a tavern where the informant is already dead."
4. **Genre Expectations must be load-bearing.** Faction lore must surface through NPC dialogue, not be inert file content. If lore doesn't show up in play, it doesn't exist in the SIS.
5. **Match Point-of-Contact level to the CA the content serves.** Don't author Vanilla content for a Bang or Pervy content for atmosphere.

### Analyze (OTEL / log review)

1. **Missing spans are evidence of El Dorado attempts.** Look for them.
2. **The GM panel is the Pervy system spying on the Vanilla one.** Use it that way.
3. **Correlate narrator prose with state deltas.** Divergences are Director Stance violations.
4. **Watch for Bang collapse.** If a ConfrontationDef fired but only 1-2 distinct beats showed up in the session, the Bang structure didn't engage.

### Review (narrative quality)

1. **Map every violation to its Forge root cause.** This lets future fixes be general, not one-offs.
2. **Evaluate against target CA, not universal "good writing."** Prose that would be great in a novel might violate Agency in an RPG.
3. **Protect Protagonism.** Player characters should be the source of meaning, not the narrator.

---

## 15. When I hit something this guide doesn't cover

This guide is provisional, like Edwards' glossary. When I encounter a playtest finding, content decision, or architectural question that doesn't map cleanly to anything here:

1. **Name it.** Propose a term. "This is a ___-shaped failure."
2. **Trace it.** Which Big Model layer is it happening at? Social Contract? Exploration? System?
3. **Check for precedent.** The Forge glossary has ~120 terms; one of them probably covers it.
4. **Report it to Keith with the naming attempt.** He'll tell me if my read is right.
5. **Update this guide.** Add a section with the new term and the scenario that surfaced it.

---

## 16. The distillation — keep this on the sticky note

> **SideQuest is a Fortune-in-the-Middle, Story-Now, mechanical-scaffold RPG.**
>
> **Our bet**: escape El Dorado through structural support.
>
> **Our tools**: ConfrontationDefs as a Bang catalog, OTEL as an Illusionism detector, SOUL as a Stance-protection doctrine.
>
> **Our prohibition**: The Impossible Thing Before Breakfast. Never.
>
> **Our target CA**: Story Now, supported by Right to Dream.
>
> **Our player**: Narrativist-leaning, full-stack, doesn't need the mechanics hand-held but DOES need them to be real.

When in doubt, return to those six lines.

---

*Last updated: 2026-04-11 by Fred Johnson, after Keith and I worked through the confrontation forward-port + momentum refactor and he sent me the Forge glossary.*
