# Magic System Design: The Orthodoxy (Contrast Reference)

--

## 0. The first decision: hard or soft?

Before anything else, pick a paradigm. The source article treats "functional
magic system" as a synonym for "hard magic system." It is not. There are two
paradigms in modern fantasy, and they produce fundamentally different genres.

| | **Hard magic** | **Soft magic** |
|---|---|---|
| **Rules** | Known to reader/player | Unknown or partial |
| **Can resolve conflict?** | Yes (Sanderson's First Law) | No — magic is the problem or the atmosphere, not the solution |
| **Resource economy** | Usually tallied (mana, slots, metals) | Scene-shaped — cost lands as story beat, not number |
| **Tone** | Systemic, engineerable, "magic as physics" | Numinous, atmospheric, "magic as weather or rumor" |
| **Exemplars** | Sanderson (*Mistborn*), Paolini (*Eragon*), Butcher (*Dresden Files*), *Magic: the Gathering* | Tolkien, Le Guin (mostly), Wolfe, Tim Powers, Howard, Crowley, Peake, Vance |

**A genre pack must declare its paradigm.** Write it into `pack.yaml` as a
`magic_paradigm` field with value `hard`, `soft`, or `hybrid`, and answer every
question below in a way consistent with that choice.

**If you pick soft, you are committing to:**
- No mana pool, no spell slots, no crafting tree
- The narrator withholds rules from the player on purpose
- Magic is rare and lands like a thunderclap when it happens
- Characters cannot reliably use magic as a tool — it happens *to* them, or
  *through* an object that has its own agenda

**If you pick hard, you are committing to:**
- A published-to-the-player rule system
- A resource economy (which must be designed to avoid the errand-game trap)
- Magic as a reliable problem-solving tool with reader-legible limits
- A higher authoring burden — every rule must be Reasonable and Respected
  across every scene

---

## 1. Where does the magic come from?

Pick one or more. In hard paradigms, this defines the system. In soft paradigms,
the answer is often *intentionally unanswered in-fiction* — the author knows,
the characters don't.

| Source | Description | Fits well with |
|---|---|---|
| **Divinity** | Granted by gods who may refuse | Active pantheons, priest-focused settings |
| **Life force** | Draws on living energy (own or others') | Blood-price settings, horror-adjacent |
| **Ambient field** | Everywhere, mages tap it ("the Force") | Wuxia, Jedi-style, elemental harmony |
| **Parallel realm** | From elsewhere, mage is a conduit | Summoner/pact settings |
| **Relic / artifact** | Carried objects with their own agenda | **Canonical soft-magic answer** (Wolfe's Claw, the One Ring) |
| **Mixed** | Any combination | Most real settings |

**Soft-magic note:** in soft paradigms the protagonist usually doesn't *own* the
source — they carry it, are haunted by it, or were present when it happened.

---

## 2. Who can touch the magic?

| Archetype | Description | Frequency |
|---|---|---|
| **The Chosen** | Elite few per generation | Tiny — single digits |
| **Supernatural beings** | Non-human entities only | Rare, usually NPCs |
| **A subspecies** | Distinct hereditary group | Small but meaningful (wizard clans, elves) |
| **Spontaneous** | Random emergence | <0.1% typical |
| **Learned** | Years of study, often with a cost | Gated by access, not blood |
| **Nonhumans only** | Species-locked | Setting-dependent |
| **Everyone** | Universal access | All characters mages |

**Soft-magic note:** the answer is often "whoever the world picked, and nobody
knows why." Access is a burden or a chance, not a skill ceiling.

---

## 3. How is magic performed?

| Method | Description |
|---|---|
| **Will** | Pure focus, no external trappings |
| **Gesture** | Specific movements |
| **Word / spell** | Spoken formulae |
| **Sign** | Drawn or inscribed symbols |
| **Object** | Wands, crystals, relics |
| **Circle** | Inscribed geometric figures |
| **Ritual** | Extended ceremonial sequences |

**Soft-magic note:** in soft paradigms, this question often has the answer
*"the protagonist doesn't perform magic at all — magic happens to them, or
through an object that chooses its own moments."* That is a valid answer and
should be stated plainly in the pack.

---

## 4. What can't the magic do?

**The two Rs:** limits must be **Reasonable** (grounded in the nature of the
system, not arbitrary) and **Respected** (enforced on every character
including gods, without Deus ex Machina exceptions).

Common limit categories:

- **Body / soul cost** — magic tires, damages, or ages the user
- **Finite supply** — only so much available globally or locally
- **Complexity cost** — bigger effects require exponentially more
- **Exotic components** — rare materials required (⚠ *errand trap*, see §6)
- **Sensory range** — can only affect what the mage can perceive
- **Spatial range** — limited by distance
- **External veto** — a higher power blocks overreach
- **No creation from nothing** — only manipulation of existing things
- **Magic blocks magic** — one mage's influence blocks another's
- **Knowledge gaps** — not all combinations are known
- **Regional lockout** — only works in certain places
- **Counters exist** — every effect has a defense

**Soft-magic note:** the strongest limit in a soft paradigm is **opacity
itself.** Nobody knows how far the magic goes, so nobody pushes past the edge
of what they've personally seen. The limit is *epistemic*. Fear of the unknown
is the containment field, and it does not require mechanical enforcement.

---

## 5. Pitfalls (from the article, relevant in both paradigms)

- **Take rules to their logical conclusion.** Water mage = blood mage (70%
  water). Air mage = weather mage. If healing works by touch, so does harming.
- **Line-of-sight ambiguity.** Does a mirror count? A telescope? A camera feed?
  A dream? Decide before playtest, not during.
- **No new powers as the plot demands.** If the protagonist gains an ability
  at the climax, that ability must be seeded earlier.
- **Respect physical law where possible.** Fire needs fuel. Disappearing mass
  should imply implosion. Invisibility that covers clothes should cover the
  coins in the pocket.
- **Know your domain.** Fire and electricity are *processes*, not substances.
  Ice and water are the same thing at different temperatures.
- **Don't change established rules mid-story.** Rules, once stated, are canon.
- **Don't over-limit.** Magic exists to produce wonder. Strip too many powers
  out and you've written it out of relevance.

---

## 6. The SideQuest-specific trap: resource economies and the errand loop

This is the single most important section for SideQuest genre pack authors.

The TVTropes article treats "exotic components" and "finite supply" as normal,
healthy limiters. In a tabletop book, they are. **In a narrative-driven CRPG,
they are the single biggest failure mode.** A resource economy, once added,
inevitably creates scenes in which the player is gathering components to make
things to make other things, and every one of those scenes is a pure time-tax
on the player with no decisions, reveals, or stakes attached to it.

This is the Skyrim-smithing-tree failure. It is forbidden in SideQuest. See
the **Law 8: Scarcity creates decisions, not errands** principle in the
development notes.

The discipline: **costs must be scene-shaped, never tallied.**

- ❌ "You need three iron, two leather, one cloth to forge this sword."
- ✅ "You have one swing of your blade left before it breaks. Do you take it?"
- ❌ "Track arrow count. Gather feathers to fletch more."
- ✅ "You have your last arrow. The deer is forty paces out. Decide."
- ❌ "Mana regenerates at 1/turn. Spell cost: 30 mana."
- ✅ "The working took something from you that won't come back this season.
     You're walking slower now."

Hard-magic genre packs must design their resource economy against this
constraint. Soft-magic genre packs sidestep it by construction — if there is
no system, there is nothing to tally.

---

## 7. Authoring checklist

Before shipping a genre pack that includes magic, fill in:

- [ ] **Paradigm:** hard / soft / hybrid
- [ ] **Source of magic:** [one or more from §1]
- [ ] **Who has access:** [one or more from §2]
- [ ] **How performed:** [one or more from §3, or "not performed — happens to
      characters" for soft]
- [ ] **Limits:** at least three from §4
- [ ] **Narrative stance:** public (everyone knows, society organizes around
      it) / hidden (most people disbelieve, only the few know)
- [ ] **Cost shape:** tallied (hard, requires §6 review) / scene-shaped (soft
      or narrative-hard)
- [ ] **The errand test:** for every mechanical cost, confirm it cannot be
      satisfied by repetitive low-stakes gathering. If it can, redesign.
- [ ] **Rules stated once, respected always:** no Deus ex Machina exceptions,
      including for gods and antagonists.

---

## 8. The Greats

### Sanderson's *Mistborn* (hard)
The canonical hard-magic exemplar. Sixteen metals, each with exactly one power,
physics-respecting, fully published to the reader. The magic is solvable,
combinable, and conflicts can be resolved through clever application of the
rules.

### Sanderson's Three Laws

1. **An author's ability to solve conflict with magic is directly proportional
   to how well the reader understands said magic.** (Soft magic cannot resolve
   conflicts because the reader doesn't know the rules — which is *fine*, it
   just means conflicts must resolve by other means.)
2. **Limitations > powers.** What the magic *can't* do is more interesting
   than what it can.
3. **Expand before you add.** Deepen an existing system before introducing a
   new one.

### *Magic: the Gathering* color pie
Not a mechanic — a **typology of philosophical stances toward power**. Five
colors, each with a strength taken to its flaw:

- **White** — order, collective good, peace → can become utopia-justifies-the-means
- **Blue** — knowledge, control, perfectionism → paralysis by analysis
- **Black** — self, ambition, pragmatism → isolation, nihilism-adjacent
- **Red** — passion, freedom, impulse → burnout, short-sightedness
- **Green** — growth, nature, tradition → stagnation, Luddism

Each color has two allies (adjacent on the pentagon) and two enemies (across).
The typology is **portable to any paradigm** — it's about how characters relate
to power, not how the power works mechanically.

### The soft-magic canon (the article's omission)

The article pretends only hard magic is "functional." This is wrong. The
soft-magic canon produced most of the books that made people love fantasy:

- **Tolkien** — Gandalf is useful, the Rings have real power, but there is no
  rulebook for any of it and there cannot be.
- **Gene Wolfe** — *Book of the New Sun*, *Soldier of the Mist* / *Arete* /
  *Sidon*. The Claw of the Conciliator heals sometimes, and nobody knows why.
  Latro can see gods at the edge of torchlight and forgets them by morning.
- **Ursula K. Le Guin** — *Earthsea* has rules (true names), but the rules
  themselves are numinous and the magic is fundamentally about restraint.
- **Tim Powers** — *Declare*, *The Anubis Gates*, *On Stranger Tides*. Magic
  operates in the gaps of known history. The real historical record is almost
  the whole story; the supernatural fits into its seams.
- **Robert E. Howard** — magic is the *other*. Conan encounters it, usually
  regrets it, and survives by being faster than whatever summoned it.
- **John Crowley** — *Little, Big*. Faerie hides in plain sight and only some
  people can see it.
- **Mervyn Peake** — *Gormenghast*. Atmosphere as magic. The castle itself is
  the supernatural element.
- **Jack Vance** — *Dying Earth*. Magic is memorized and forgotten like
  language fragments from a dead age. Inspired D&D Vancian casting, ironically
  one of the more hard-magic descendants.

---

## 9. How to use this contrast reference

This document exists so that you can **recognize the orthodoxy when you meet
it**, not so that you can follow it. When you read fantasy-writing advice
elsewhere in the hobby, most of it will assume the hard-magic frame described
above. This guide is the map of that territory, written so you know where the
assumptions live and can push back on them when they try to creep into
SideQuest content.

**When you see a reviewer or reference suggesting:**

- "You need to define how the magic works so the reader understands it" —
  that is Sanderson's First Law. It is correct for hard magic and *wrong* for
  soft magic. In soft magic the reader's partial ignorance is the *point*.
- "Every spell should have a mana cost" — that is the resource-economy
  assumption. In SideQuest, this is a Law 8 violation. Redirect.
- "What's the cost for casting this?" — valid question. Answer it in
  scene-shape, not in numerical tally. (§6)
- "Define the limits of the system" — valid in both paradigms, but in soft
  magic the limit is *opacity* and *rarity*, not a rule list. (§4)
- "Why can the protagonist do X now when they couldn't at the start?" — this
  is a hard-magic consistency concern. In soft magic, magic is not a skill
  the protagonist levels up — so this question doesn't apply the same way.

**SideQuest's actual magic design approach** is documented separately (and,
at time of writing, is still being written as part of the Blood and Brawn
rewrite). When the SideQuest soft-magic guide exists, it will live alongside
this one and this file will link to it here.

---

*Source: summarized from TVTropes, "So You Want To Write a Functional Magic
System." This is a contrast document; SideQuest does not follow this
orthodoxy. SideQuest-specific additions (§0 hard/soft distinction, §6 errand
trap, §8 soft canon) exist to position the orthodoxy against the paradigm
SideQuest actually inhabits.*
