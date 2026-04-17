# Narrative Lenses

> A toolkit for generating and judging SideQuest content — worlds, factions, NPCs, mechanisms, lore, and scenes.

## What This Doc Is For

This is a **reference for content authors and evaluators** (human or LLM) working on SideQuest genre packs and worlds. It answers two questions:

1. **Generative:** when writing new content, what questions should I ask to produce something that isn't flat?
2. **Evaluative:** when auditing existing content, what tests should I run to decide whether it's alive or dead?

It is not a style guide. It is not a prose rulebook. It is a set of **interrogation modes** for content, plus one meta-principle that runs underneath all of them.

## The Meta-Principle: Cliche Granularity

Before the lenses, the principle that governs all of them.

**Claude is a cliche engine.** The model averages its training data, and the average is a cliche. Tropes are useful and can't be eliminated. The strategy is not to avoid tropes — it is to pick the right **cliche granularity**.

Every piece of content sits at some granularity, from coarse to fine:

| Granularity | Example | Audience |
|---|---|---|
| Coarse | "Voodoo," "hacker," "ninja," "wizard," "cult" | Everyone recognizes the bucket |
| Medium | "Haitian Vodou," "penetration tester," "Iga-ryu shinobi" | Informed layman recognizes the bucket |
| Fine | "Petro-loa Rada-loa distinction," "runc CVE container escape" | Domain practitioner recognizes the bucket |
| Hyper-fine | "Specific terreiro lineage in 1890s Bahia persecution era" | Only a subdomain specialist recognizes the bucket |

Every audience member has an **expertise granularity** in every domain — the finest resolution at which they can still recognize tropes *as* tropes. Above their resolution, tropes land as cliche and they catch it instantly. Below their resolution, the same tropes land as authenticity.

**The rule: operate at a cliche granularity finer than the audience's expertise granularity.** Drop the granularity until the audience can no longer resolve the tropes.

### The Principle Is Recursive

There is no terminal granularity. Every level has experts sitting at a finer level. "Drop the granularity" is a dial you turn until you're past *this* audience's resolution, not until you're past all possible audiences.

- Layman hits "voodoo" cliche → drop to **Candomblé** → past the layman (a Brazilian scholar still sits below)
- Software generalist hits "hacker" cliche → drop to **container escape via runc CVE + RAG corpus poisoning** → past the generalist (an LLM red-teamer still sits below)

At whatever level you stop, someone still sits below. That's accepted cost. You're not trying to be bulletproof, just past *this* audience.

### Reference Stacking Accelerates the Drop

A single specific reference drops granularity one level. **A stack of two or three specific references triangulates into a niche finer than any component alone.**

- "Container escape" alone → recognizable to a security engineer
- "Container escape + LLM weight poisoning + RAG corpus corruption" → three drops in one move, landing in a niche narrow enough that even someone working on one of the three probably isn't current on how they compose

Syncretism (see lens #3) is the cultural version of this technique: name real traditions and mark the seams where they collide. Same operation, different domain.

### The Failure Mode

Coarse granularity in a domain the audience has high expertise in. Every failure we care about is some version of this:
- Generic "cyberpunk hacker scene" in front of a software engineer
- Generic "voodoo curse" in front of a Brazilian
- Generic "medieval tavern" in front of a tabletop veteran

Coarse granularity is the universal failure mode. Dropping granularity through specificity and stacking is the universal fix.

### The Canonical Reference Pair: Mr. Robot vs Swordfish

The cleanest possible demonstration of the granularity principle in a single domain (hacking/software), at opposite ends of the dial:

- **Swordfish (coarse):** "I need root access" while a 3D wireframe file system rotates and the protagonist types with a gun to his head. The movie isn't trying to pass a software engineer's sniff test; it assumes no engineer is in the audience. Response from an actual practitioner: *"that's not fucking right."* Response from the rest of the theater: *"it's a movie, sit down."*
- **Mr. Robot (fine):** Kali Linux actually on screen. Real rubber ducky USB drops. Raspberry Pi planted in a climate-control system. Actual social-engineering pretexting scripts. The showrunners had security consultants on staff; r/netsec decoded each episode's exploit the next morning. The specificity *is* the aesthetic.

The load-bearing insight: **fine granularity did not cost Mr. Robot mass-market appeal.** The show was a hit. The specificity didn't wall off the non-technical audience — it *impressed* them by passing the sniff test of the technical audience they could see tweeting about it. Granularity compounds: insiders validate, outsiders trust the validation.

**This is the target for any SideQuest content touching a domain Keith has expertise in.** Not "accessible." Not "accurate." Accurate enough that an expert would tweet about the specific detail, so the non-expert audience feels the weight of that validation without needing to understand it. That's `neon_dystopia` netruns, `elemental_harmony` martial arts, `low_fantasy` medieval mechanisms, `space_opera` ship systems, and everything else in the high-expertise domains.

## The Five Lenses

Each lens is an **interrogation mode** — a question you ask content to see if it's alive. Content should pass the lens it's written in, and hopefully hold up if probed from an adjacent lens too.

### 1. Mechanism

**The question:** How does this actually work, all the way down?

**Generative prompt:** Pick any detail and walk the causal chain three levels deep. What feeds this? What does it feed? What happens if it breaks? If you can't answer, the detail is decoration.

**Evaluative test:** Can a player probe a detail and get a coherent answer three levels down? If the narrator has to wing it past the second "why," the content fails.

**Failure mode:** Decorative worldbuilding. Things that look cool but collapse under inspection. The classic example: a medieval city economy that never explains where the food comes from.

**Examples at fine granularity:**
- A water clock in a `low_fantasy` monastery, described with specific flow rates, reservoir volume, and the escapement mechanism (inspired by Su Song's 11th-century Chinese water clock, not generic "medieval clock")
- A starship FTL drive in `space_opera` that specifies the energy cost, the failure mode (not "explosion" but "phase-lock collapse causing time dilation in the drive chamber"), and the maintenance schedule
- A neon_dystopia data heist that specifies the actual attack vector: compromised build pipeline, not "I hack the mainframe"

### 2. Metaphor

**The question:** What social, political, or psychological condition is this the physical form of?

**Generative prompt:** Pick a condition (alienation, class struggle, grief, addiction, nostalgia, surveillance) and ask what it would look like if it were built. What architecture, what ritual, what economy would physicalize it?

**Evaluative test:** Does the setting *argue* something, or is it just dressed up? Content written through this lens should feel like it's pointing at a condition in the reader's world, not just decorating a fantasy one.

**Failure mode:** Theme park. Everything is vivid and nothing means anything. The setting has no target outside itself.

**Examples at fine granularity:**
- The two cities in Miéville's *The City & The City* as a physicalization of consensual unseeing — a Balkan-Cold-War-phenomenology stack
- A `neon_dystopia` arcology where the floor you live on is tattooed on your skin at birth — caste mobility made literally surgical
- A `road_warrior` convoy whose rank structure mirrors an oil company org chart, with "vice presidents" commanding gun crews

### 3. Syncretism

**The question:** What specific, real traditions have fused here, and where are the seams still visible?

**Generative prompt:** Name two or three real-world traditions (religious, technical, cultural, mechanical) that would plausibly collide in this place under specific historical pressure. The content is the collision product. Mark the seams where the old joints are still visible.

**Evaluative test:** Can the author name the component traditions and point at the seams? Content that can't name its seams is pretending to be pure — and nothing real is ever pure. Every real tradition is already a syncretic stack of prior traditions.

**Failure mode:** Generic fusion. "A mix of eastern and western traditions" is a shrug, not syncretism. Syncretism is *specific*: "Shingon esotericism fused with Shugendō mountain practice and a surviving Bon divination lineage, where the mountain kami is addressed as both a bodhisattva and a pre-Buddhist ancestor in alternating verses of the same ritual chant."

**Why this lens is also cross-cutting:** syncretism applies to every other lens too. Mechanism content is syncretic (all real technology is a collision of prior technologies). Metaphor content is syncretic (Miéville is fusing Cold War Berlin with ethnic cleansing with phenomenology). System content is syncretic (Sanderson's Mistborn is medieval alchemy + periodic table + martial arts weight classes). Myth content is almost definitionally syncretic (every origin story is a palimpsest). **Whatever lens you're writing in, name the components and mark the seams.**

**Examples at fine granularity:**
- A `pulp_noir` Harlem spiritualist church: Moorish Science Temple theology + Haitian Vodou drumming + mail-order Rosicrucian correspondence degrees. *Seam:* the pastor preaches Noble Drew Ali's Moorish doctrine on Sunday and consults the loa on Tuesday, insisting they are the same practice.
- A `low_fantasy` monastic order: Cistercian agricultural discipline + smuggled Bogomil dualist theology + Kabbalah fragments from expelled Iberian Jews. *Seam:* they grow wheat by day (Cistercian) but the bread is consecrated with a dualist liturgy calling the material world Satanael's forgery.
- A `space_opera` generation-ship order: Ismaili hidden-imam theology + Russian cosmism (Fedorov's resurrection-through-physics) + Jesuit intellectual discipline. *Seam:* they believe the hidden imam will return when the ship arrives, and that arrival will physically resurrect the ancestors stored in cryo.

### 4. System

**The question:** What are the rules, the costs, and the exploits?

**Generative prompt:** Define the mechanism as a rulebook. What does it cost? What's the exchange rate? What clever move breaks it, and does the world acknowledge the exploit as valid?

**Evaluative test:** Can a clever player break the world in a way the world *acknowledges*? A system that can't be exploited by a clever player is a set of props, not a system.

**Failure mode:** Magic-as-vibes. Powers that do whatever the plot needs, with no costs the player can reason about. "She wields the ancient power" is not a system; it's stage dressing.

**Examples at fine granularity:**
- `elemental_harmony` martial arts that specify the exact qi cost per technique, the recovery time, and the specific exploit a clever player can run (channel qi through a weapon to bypass the recovery window, at the cost of corroding the weapon)
- `neon_dystopia` cyberware with specified heat dissipation limits — use it too fast and you cook, use it too slow and you lose the edge
- A `mutant_wasteland` mutation system where every gift has a cost the player must pay in front of the group (literalizing guilt)

### 5. Myth

**The question:** What story does this culture tell about itself, and how is it wrong?

**Generative prompt:** Write the culture's official origin story. Then write what actually happened. The gap between them is the content. NPCs either repeat the official story (believers), hint at the gap (doubters), or know the truth (dangerous).

**Evaluative test:** Do NPCs *contradict* the world's official history? A culture whose members all tell the same story is a history textbook, not a culture. Real cultures have believers and skeptics and heretics.

**Failure mode:** Exposition-dump history. The world has a deep timeline that no character ever disputes. Everyone agrees on what happened 1000 years ago. That's not a world, it's a wiki.

**Examples at fine granularity:**
- A `low_fantasy` kingdom whose founding myth is "the Holy King slew the Worm." The truth: the Worm was a Bogomil heretic preacher whose followers were massacred, and the "holy sword" in the cathedral is the executioner's axe. Three NPCs know this and one is writing a forbidden history.
- A `space_opera` colony whose official record says the first generation arrived as willing settlers. The truth: they were penal labor, and the current prosperity is built on a slave economy the grandchildren have rewritten into heroism.
- A `mutant_wasteland` tribe whose elders describe the Before as a golden age of plenty. The truth (buried in an accessible archive): the Before was the decade of collapse, and the "golden age" memories are inherited propaganda from the last functional government.

## Per-Genre Lens Assignments (Tentative)

Each genre pack should declare which lens dominates, which is secondary, and which cross-cutting principle applies (Syncretism always does, but emphasis varies).

| Genre | Dominant | Secondary | Notes |
|---|---|---|---|
| `pulp_noir` | Metaphor (the city as moral condition) | Syncretism (1930s esoterica) | The city is the argument; the cults are the texture |
| `low_fantasy` | Mechanism (how does medieval life actually work) | Myth (unreliable cultural memory) | Grit comes from mechanism; depth comes from myth |
| `neon_dystopia` | Metaphor (late capitalism physicalized) | System (cyberware rules, costs, exploits) | Miéville + Sanderson |
| `mutant_wasteland` | Myth (post-apocalyptic cultures lie about the Before) | Syncretism (post-collapse religious fusion) | The lies and the fusion are the same operation |
| `road_warrior` | Mechanism (vehicles are load-bearing) | Myth (the Before is a lie) | Cars have to work; cultures lie about why |
| `elemental_harmony` | System (martial arts as rulebook) | Syncretism (Shugendō + Shingon + Bon) | The techniques are systematic; the lineages are syncretic |
| `space_opera` | Mechanism (ships and systems must work) | Myth (colonies lie about their founding) | Stephenson + Le Guin |

These assignments are **starting points** — not locked in. Pressure-test them against actual playtest and audit results. A genre that feels flat is probably misassigned or operating at too coarse a granularity.

## How to Apply

### When Authoring Content

1. **Declare the lens.** Which lens is this content written through? Which is secondary? Write it in the YAML or the commit message.
2. **Declare the granularity.** Is this pitched at medium, fine, or hyper-fine? For any content in Keith's high-expertise domains, default to fine or finer.
3. **Name the stack.** If the content is syncretic (and it should almost always be, even implicitly), name the component traditions and mark the seams.
4. **Write it.** Then re-read it through a different lens. If it collapses when probed from an adjacent angle, it's flat. If it holds up from two, it's alive. Three means diamond — reserve for content that actually matters.

### When Auditing Content

For any piece of content under audit, ask:

1. **Which lens does this claim to use?** If unclear, the content probably has no lens — which is itself the finding.
2. **Does it pass that lens's evaluative test?** Concrete failures, not vibes.
3. **At what cliche granularity is it pitched?** If coarse in a high-expertise domain, flag it.
4. **Can you probe it from an adjacent lens?** If it collapses, it's decoration.
5. **Are the syncretic seams named?** If the content gestures at fusion without specifying the components, it's a shrug.

### When Assembling Narrator Prompts

Inject the lens, the granularity, and the reference stack into the narrator's context. Not adjective clouds — *named particulars*.

- Bad: "A mysterious scholar, brilliant and obsessive."
- Good: "Alaric Venn, scholar of the forbidden geometries. Evocative of: John Dee (angelic Enochian scrying), Isaac Newton (the alchemical/apocalyptic Newton, not the physicist), Moriarty (Victorian criminal intelligence). Seam: he insists the math and the angels are the same project. Lens: Syncretism + Mechanism."

The narrator LLM will produce dramatically better output from the second prompt because the granularity is pinned and the seams are explicit.

## The One Rule That Matters

If you remember nothing else from this doc: **generic is the failure mode at every level.** Every lens, every genre, every piece of content fails the same way — by operating at a cliche granularity coarser than the audience's resolution. The fix is always the same: drop the granularity, stack the references, name the seams.

Diamonds and coal. Most content is coal; the granularity dial is how you make the diamonds where they matter.
