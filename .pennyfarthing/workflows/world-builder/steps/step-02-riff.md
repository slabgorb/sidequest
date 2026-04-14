---
name: 'step-02-riff'
description: 'Creative riffing session — explore the concept space before committing to research'

nextStepFile: './step-03-research.md'
wipFile: '{wip_file}'
---

<purpose>Open-ended creative exploration of the world concept. Riff on ideas, explore what-ifs, find the angle that makes this world sing before locking into structured research.</purpose>

<instructions>Free-form brainstorm with the user. No structure yet — just vibes, references, and "what if" exploration. Capture the best ideas for research direction.</instructions>

<output>Updated WIP with concept direction, key inspirations, and research questions. stepsCompleted: [1, 2].</output>

# Step 2: Riff

**Progress: Step 2 of 8**

## CONTEXT

This is where the seed enters the system. In **manual mode**, this is a creative riff session — free-form brainstorm, the user leads, world-builder reflects ideas back sharpened. In **surprise mode**, this step accepts one of four structured seed formats and does NOT riff — it captures the seed, validates it, and hands off to the three-lens research fan-out in step 3.

Check the `surprise` field in the WIP frontmatter (set in step 1). Route accordingly.

---

## SURPRISE MODE — Structured seed intake

If `surprise: true`, this step does NOT riff. It accepts a seed in one of four formats and validates it. The seed is the only creative input; everything downstream is automatic until the final PR review (or a fact-conflict escalation in step 6).

### Four seed formats

#### 1. Paragraph seed
Free-form text, the current default. One paragraph of creative direction. Example:

> "A low-tech colony on a tidally-locked world where the terminator ring is the only habitable zone. Three generations in. The original colonists are dying off; their grandchildren have never seen a spaceship. Mesoamerican-style sky mythology adapted to a world where the sky never moves."

Accept as-is. No validation beyond "not empty." Write to WIP as `seed_type: paragraph`, `seed_content: <the text>`.

#### 2. Photograph seed
Image file path + **REQUIRED one-line caption**. The caption provides identification; the photograph provides texture.

**NAKED IMAGES ARE REJECTED.** Vision models will confidently miscaption a specific 1890s Parsi wedding as "a traditional South Asian ceremony" — exactly the generic category-level cliche Keith is trying to escape. The caption anchors the specificity. Example:

- Path: `seeds/photographs/1887-mysore-guards.jpg`
- Caption: "Guards at the Mysore palace, 1887, during the succession dispute. Note the uniform — post-British-treaty but pre-reform."

If the invocation lacks a caption, HALT and ask: "Photograph seeds require a one-line caption naming the period, place, and what to notice. Please provide."

Once the caption is provided:
1. Use the Read tool's vision capability to read the image
2. Write to WIP as `seed_type: photograph`, `seed_path: <path>`, `seed_caption: <caption>`, `seed_vision_notes: <what the model saw in the image, grounded by the caption>`

The vision notes are reference material — step 3's research lenses will read both the caption and the vision notes.

#### 3. Question seed
A single interrogative sentence the downstream pipeline is **forbidden from resolving**. Every generated file must deepen the question, not answer it. Example:

> "What if the gods were right but the prophets were wrong?"

Validate: is it an interrogative? Does it end in `?`? Is it a single sentence? If yes, accept. If no, ask for a reformulation.

Write to WIP as `seed_type: question`, `seed_content: <the question>`, plus a special flag `generate_must_deepen_not_resolve: true` that step 6's specialist prompts read — every content file must be structured so that the question is still load-bearing at the end, not resolved.

#### 4. Collision-pair seed
A row from the living catalog at `/Users/keithavery/Projects/oq-1/seeds/untried-pairs.yaml`. The catalog holds unused syncretic pairs Keith has collected. Two domains that have never been synthesized. Example:

> pair: "Byzantine tax law + deep-sea anglerfish biology"
> consumed: null

**Selection:**
- Keith can pick a row by name
- Keith can say "roll d20" — world-builder picks a pseudorandom row using `python3 -c 'import random; ...'`
- Keith can say "surprise me" — world-builder picks the row that's most different from Keith's most recent world (heuristic: fewest shared keywords with the prior three worlds in sprint archive)

Once selected:
1. Read the row
2. Write to WIP as `seed_type: collision_pair`, `seed_content: <the pair>`, `seed_source: untried-pairs.yaml row {N}`
3. Update the catalog: set `consumed: {date}` on the selected row with a brief note on which world it's fueling
4. Commit the catalog update as a separate commit in the seeds path (NOT mixed with content commits)

### Surprise mode exit

After the seed is captured:
1. Summarize the seed in one sentence
2. Update WIP: append seed capture, set `stepsCompleted: [1, 2]`
3. Do NOT halt. Proceed directly to step 3 research fan-out.

---

## MANUAL MODE — Creative riff

If `surprise: false`, run the creative riff below.

## HOW TO RIFF

**Follow the user's energy.** They may want to:
- Free-associate genre mashups ("what if Victorian England but the fae courts are real")
- Explore tone ("darker than low_fantasy, but not grimdark — more morally gray")
- Riff on faction dynamics ("three families who all think they're the rightful rulers")
- Reference media ("Peaky Blinders meets Dishonored")
- Sketch geography ("archipelago, trade routes between islands, one island nobody returns from")
- Play with naming ("I want it to sound Polynesian but filtered through the genre")

**Your job:**
- Reflect ideas back sharpened ("so the tension is colonial power vs indigenous knowledge")
- Suggest connections ("that maps nicely to the faction agenda system — three factions with incompatible claims")
- Flag mechanical opportunities ("that island could be a VETERAN-unlock region")
- Name-drop historical parallels ("that's basically the Hanseatic League dynamic")
- Push back when something doesn't fit the genre's rules ("road_warrior doesn't have magic — would this be a trope instead?")

**Do NOT:**
- Shut down ideas prematurely
- Force structure too early
- Write YAML files
- Start formal research yet

## CAPTURE

As the riff develops, track the emerging direction in notes:

```markdown
## Riff Notes

### Core Concept
{the one-sentence pitch that's emerging}

### Key Inspirations
- {media reference} — {what we're taking from it}
- {historical period} — {what we're taking from it}

### Tone
{how this world feels}

### Open Questions for Research
- {thing we need to look up}
- {historical detail we're unsure about}
- {mechanical question about genre fit}

### Ideas to Explore
- {promising tangent that needs more thought}
```

## EXIT

When the user feels the concept is solid enough to research:

1. Summarize the direction in 3-4 sentences
2. List the research questions that emerged
3. Update WIP: append riff notes, set `stepsCompleted: [1, 2]`
4. **Ask:** "Ready to dig into the research, or still riffing?"

**HALT until user confirms.**
