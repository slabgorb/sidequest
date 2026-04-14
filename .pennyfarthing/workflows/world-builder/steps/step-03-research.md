---
name: 'step-03-research'
description: 'Three-lens contrarian research — political, material, spiritual — via Task tool fan-out'

nextStepFile: './step-04-refine.md'
wipFile: '{wip_file}'
---

<purpose>Research the real-world source material that will inform the genre pack or world via three parallel contrarian lenses. The collision between the lenses — where they disagree, where each leaves gaps the others fill — is the creative fuel for step 4 refine and step 5 design brief.</purpose>

<instructions>Fan out three parallel research agents via Task tool. Each gets an exclusionary lens instruction. After all three return, run the deterministic coherence assertion. Write the collision artifact. In surprise mode, no approval gate — proceed directly to step 4.</instructions>

<output>Three per-lens research files at `.session/world-builder-wip/research-{lens}.md`, one collision artifact at `.session/world-builder-wip/collision.md`, and a Research section appended to the main WIP. stepsCompleted: [1, 2, 3].</output>

# Step 3: Research (Three-Lens Fan-Out)

**Progress: Step 3 of 8**

## CONTEXT

This is the first step that uses the **Task-tool-fan-out-inside-a-step-file** pattern — the foundation for the whole federation refactor. Get it right here and every later phase (playtest audit, generate, validation) reuses the pattern.

**Why three lenses, not one:** a single monolithic research pass produces *competent* research. Competence is the enemy of surprise. Three contrarian lenses, each with an **exclusionary** instruction (forbidden from certain domains), leave gaps each lens fills for the others. The collision — where two lenses disagree, where one names a thing the others didn't — is where novelty lives.

**Why exclusionary, not thematic:** if you tell three agents "look at this from the political angle / material angle / spiritual angle" without forbidding overlap, all three will converge on the same famous historical artifacts. Exclusion forces each lens to look in its assigned corner of the archive and leaves the rest of the archive for its siblings.

**Cost control:** research costs real tokens. Two lenses use `perplexity_ask` (fast, shallow); one uses `perplexity_research` (slow, deep). Rotate which lens gets the deep dive each run — see `.session/world-builder-wip/last-deep-lens.txt` for the last one used, pick a different one this time.

## SEQUENCE

### 1. Read the seed and mode

Read the WIP file from step 1. Extract:
- `seed` — the creative input from step 2 (paragraph, photograph-with-caption, question, or collision-pair)
- `surprise` — boolean; if true, skip the approval gate in step 5
- `genre` / `world` — target
- `mode` — New Genre, New World, DM Prep, etc.

If the seed is a photograph, the caption is mandatory. Reject naked images and return to step 2 for a caption.

### 2. Determine the deep-lens rotation

```bash
LAST_DEEP=$(cat .session/world-builder-wip/last-deep-lens.txt 2>/dev/null || echo "none")
case "$LAST_DEEP" in
    political) DEEP_LENS=material ;;
    material)  DEEP_LENS=spiritual ;;
    spiritual) DEEP_LENS=political ;;
    *)         DEEP_LENS=political ;;
esac
echo "$DEEP_LENS" > .session/world-builder-wip/last-deep-lens.txt
```

The rotating deep lens gets `perplexity_research`; the other two get `perplexity_ask`.

### 3. Fan out three parallel research agents via Task tool

**CRITICAL:** dispatch all three Task calls in a **single message** — that is what triggers true parallel execution. Sequential Task calls will block on each other.

All three agents use `subagent_type: "general-purpose"`. They are research agents with web/perplexity access, NOT content specialists. Do not fan out to `writer` / `scenario-designer` / etc. at this step — those are authoring specialists, not researchers.

Each agent writes to its own per-lens WIP file: `.session/world-builder-wip/research-{lens}.md`. This avoids interleaved writes into a shared file.

**Political Lens prompt:**

```
You are the POLITICAL LENS research agent for sq-world-builder.

SEED: {seed content, including photograph caption if present}
GENRE: {genre}
WORLD: {world}

Your lens: power, economics, succession, law, class, trade relations, factions, patronage, taxation, diplomacy, dynasty, revolt, reform, corruption.

YOU ARE FORBIDDEN FROM:
- Describing geography, climate, or terrain
- Describing religion, ritual, cosmology, or the uncanny
- Naming gods, spirits, or metaphysical forces
- Food, technology, disease, architecture (unless as a political symbol like "the Versailles palace as a legitimizing monument")

If a political question requires geographic or spiritual context, STATE THE DEPENDENCY EXPLICITLY ("this requires a material-lens check on trade route geography" or "this requires a spiritual-lens check on the temple's religious standing") but do not answer it yourself.

Research deeply. Find specifics. Operate at least one granularity level below the obvious category:
- NOT "medieval tax revolt" — "the 1381 Wat Tyler rising against Richard II's poll tax under John of Gaunt's regency"
- NOT "colonial trade imbalance" — "the 1820s Mexican silver outflow through the Manila Galleon after independence severed the Acapulco route"
- NOT "the nobles vs merchants" — "hereditary jagirdars resisting tax-farming compradores who bought revenue contracts from the Mughal central administration"

Use {perplexity_tool} ({perplexity_research} if this is the rotating deep lens, {perplexity_ask} otherwise).

Write your findings to: .session/world-builder-wip/research-political.md

Structure your report as:
## Political Research Report (Lens: political)

### Power structure
[specific facts]

### Economic base
[specific facts]

### Faction dynamics
[specific facts]

### Named actors
[specific people with dates and roles]

### Dependencies flagged
[places where you needed material or spiritual context — state the dependency, do not answer it]

### Sources
[list every citable reference — URL, book, article, with page numbers where possible]
```

**Material Lens prompt:**

```
You are the MATERIAL LENS research agent for sq-world-builder.

SEED: {seed content, including photograph caption if present}
GENRE: {genre}
WORLD: {world}

Your lens: climate, terrain, food, technology, trade routes, disease, architecture, material culture, clothing, tools, craft traditions, transport, labor, resource geography.

YOU ARE FORBIDDEN FROM:
- Describing power structures, governance, factions, or law
- Describing religion, ritual, cosmology, or the uncanny
- Evaluating political motivations or spiritual meaning

If a material question requires political or spiritual context, STATE THE DEPENDENCY EXPLICITLY but do not answer it yourself.

Operate at one granularity level below the obvious category:
- NOT "medieval agriculture" — "the 11th-century Champagne two-field rotation with marl-and-ash fertilization on chalk soils"
- NOT "tropical climate" — "the 1876 El Niño drought in the Deccan plateau, specifically the Madras Presidency's millet crop failure"
- NOT "timber-frame architecture" — "the Fachwerkhaus joinery traditions of 17th-century Hessen with specific emphasis on pegged tenon joints"

Use {perplexity_tool}.

Write to: .session/world-builder-wip/research-material.md

Structure:
## Material Research Report (Lens: material)

### Climate and terrain
[specific facts]

### Food systems
[specific facts]

### Technology and craft
[specific facts]

### Trade routes and goods
[specific facts]

### Architecture and built environment
[specific facts]

### Dependencies flagged
[places where you needed political or spiritual context]

### Sources
[citations with specificity]
```

**Spiritual Lens prompt:**

```
You are the SPIRITUAL LENS research agent for sq-world-builder.

SEED: {seed content, including photograph caption if present}
GENRE: {genre}
WORLD: {world}

Your lens: cosmology, ritual, death practices, art, fear, the dead, the uncanny, pilgrimage, mysticism, heresy, prophecy, oracle, sacrifice, memory, the sacred.

YOU ARE FORBIDDEN FROM:
- Describing economics, trade, or taxation
- Describing geography, climate, or terrain (unless as sacred landscape — and then only the sacred meaning, not the material)
- Discussing political power except insofar as it touches divine legitimacy

If a spiritual question requires material or political context, STATE THE DEPENDENCY EXPLICITLY but do not answer it yourself.

Operate at one granularity level below the obvious category:
- NOT "ancestor worship" — "the Candomblé Ketu Xangô initiation rites in the Ilê Axé Opô Afonjá terreiro, Salvador da Bahia, with specific reference to the obi kola-nut divination"
- NOT "medieval heresy" — "the 1209 Albigensian Crusade against the Cathar perfecti in Languedoc, specifically the Béziers massacre under Arnaud Amalric"
- NOT "death rituals" — "the Tana Toraja tomate funerary ceremony in Sulawesi, with specific reference to the ma'nene body-cleaning rite"

Use {perplexity_tool}.

Write to: .session/world-builder-wip/research-spiritual.md

Structure:
## Spiritual Research Report (Lens: spiritual)

### Cosmology
[specific facts]

### Ritual practices
[specific facts]

### Death and the dead
[specific facts]

### Art, fear, the uncanny
[specific facts]

### Named figures and traditions
[specific named mystics, heretics, saints, oracles with dates]

### Dependencies flagged
[places where you needed political or material context]

### Sources
[citations with specificity]
```

### 4. Wait for all three to complete

All three Task calls return results. Read each per-lens file before proceeding. If any file is missing or empty, retry that specific lens with a reminder that the file must be written.

### 5. Run the coherence assertion (DETERMINISTIC, NOT HUMAN)

This is the surprise-mode safety rail. It catches "plausible but incoherent" research that would otherwise silently produce garbage worlds.

**Rule:** the three reports must share at least **3 named anchors** — specific proper nouns (places, periods, figures, events, cultures) that appear in at least two of the three reports. Shared anchors mean the lenses are looking at the same world from different angles. Zero or one shared anchor means they diverged and are researching three different things.

**How to run it:**

```bash
# Extract proper nouns from each report (multi-word capitalized phrases, years, known place markers)
POL=$(grep -oE '(\b[A-Z][a-z]+(\s+[A-Z][a-z]+)+\b|\b1[0-9]{3}\b|\b2[0-9]{3}\b)' .session/world-builder-wip/research-political.md | sort -u)
MAT=$(grep -oE '(\b[A-Z][a-z]+(\s+[A-Z][a-z]+)+\b|\b1[0-9]{3}\b|\b2[0-9]{3}\b)' .session/world-builder-wip/research-material.md | sort -u)
SPI=$(grep -oE '(\b[A-Z][a-z]+(\s+[A-Z][a-z]+)+\b|\b1[0-9]{3}\b|\b2[0-9]{3}\b)' .session/world-builder-wip/research-spiritual.md | sort -u)

# Shared between any two
SHARED_PM=$(comm -12 <(echo "$POL") <(echo "$MAT"))
SHARED_PS=$(comm -12 <(echo "$POL") <(echo "$SPI"))
SHARED_MS=$(comm -12 <(echo "$MAT") <(echo "$SPI"))

ALL_SHARED=$(printf '%s\n%s\n%s\n' "$SHARED_PM" "$SHARED_PS" "$SHARED_MS" | sort -u | grep -v '^$')
COUNT=$(echo "$ALL_SHARED" | wc -l)

if [ "$COUNT" -lt 3 ]; then
    echo "COHERENCE FAILURE: only $COUNT shared anchors across the three lenses."
    echo "Shared anchors: $ALL_SHARED"
    # Pick the strongest anchor — the one that appears in the political report
    ANCHOR=$(echo "$POL" | head -3)
    echo "Re-running research with realignment hint: $ANCHOR"
    # Loop back to step 3 sequence item 3 with the anchor in each prompt
fi
```

If the assertion fails, re-run all three lenses with the seed augmented by an explicit realignment instruction: `"You diverged from the other lenses. Realign on {anchor}. The other lenses are looking at {anchor} — you must research within that frame."`

**Retry budget:** two realignment retries. After two failed coherence assertions, HALT and escalate to Keith: "Research diverged twice. Seed may be underspecified or contradictory. Please refine the seed or select a different one."

### 6. Write the collision artifact

After coherence passes, extract the **contradictions** between the three reports. A contradiction is the feature — it is the creative friction step 4 refine will consume.

Write `.session/world-builder-wip/collision.md` with:

```markdown
# Research Collision — {seed summary}

## Shared anchors
[list of named entities that appear in 2+ reports]

## Contradictions

### {contradiction title}
- **Political says:** {the political lens' version}
- **Material says:** {the material lens' version, if applicable}
- **Spiritual says:** {the spiritual lens' version, if applicable}
- **Tension:** {one sentence on what the disagreement IS — why they see it differently}

[repeat for every contradiction]

## Dependencies unresolved
[list of the "I need X-lens context" flags that were never answered because the other lens didn't cover that territory]

## Strongest threads (for step 4 refine)
[3-5 sentences on the most promising angles the collision suggests]
```

### 7. Append a summary to the main WIP

Append to `{wipFile}`:

```markdown
## Research Findings (Three-Lens Fan-Out)

Deep lens this run: {DEEP_LENS}
Per-lens files:
- `.session/world-builder-wip/research-political.md`
- `.session/world-builder-wip/research-material.md`
- `.session/world-builder-wip/research-spiritual.md`

Collision artifact: `.session/world-builder-wip/collision.md`

### Top shared anchors
{list}

### Top contradictions
{list}

### Deep lens findings summary
{2-3 paragraph synthesis of the rotating-deep lens' most specific findings}
```

Update frontmatter: `stepsCompleted: [1, 2, 3]`

### 8. Approval gate (manual mode only)

**IF `surprise: false` in the WIP frontmatter:**

Present the research summary and collision artifact to Keith. Ask:
- Does the collision point at something worth pursuing?
- Any of the contradictions feel wrong, or are they all productive?
- Ready to proceed to step 4 refine?

**HALT and wait for confirmation.**

**IF `surprise: true`:**

Do not halt. Proceed directly to step 4 refine. The coherence assertion (section 5) has already run and passed — that is the surprise-mode safety rail. No further human gate.

---

## What this step does NOT do

- Does not write any content YAML (genre_packs, worlds). Only WIP and per-lens research files.
- Does not invoke the content specialists (writer, scenario-designer, etc.). Those are step 6.
- Does not invoke cliche-judge. Research is pre-content; cliche-judge runs on generated content in step 7.
- Does not resolve contradictions. Contradictions are creative fuel for step 4, not bugs to fix here.
