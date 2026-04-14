---
name: 'step-05-design-brief'
description: 'Present design brief for user approval before generating content'

nextStepFile: './step-06-generate.md'
wipFile: '{wip_file}'
---

<purpose>Synthesize research into a concrete design brief. Map historical concepts to game mechanics, lay out faction conflicts, propose cartography, and get user approval before generating files.</purpose>

<instructions>Build design brief from research, present for approval, iterate until user signs off.</instructions>

<output>Approved design brief in WIP. stepsCompleted: [1, 2, 3, 4, 5].</output>

# Step 5: Design Brief

**Progress: Step 5 of 8**

## SEQUENCE

### 1. Build the Brief

From research findings, produce:

a) **World Identity**
   - Name (from cultures.yaml naming patterns — NOT English descriptive)
   - Tagline (one sentence capturing the tone)
   - Axis snapshot (tone slider values from axes.yaml)

b) **Faction Design** (minimum 3, ideally 4-5)
   - Name, description, goal, urgency level
   - Relationships to other factions (hostile/wary/allied/dismissive)
   - Scene injection text
   - **Factions MUST have conflicting goals** — this generates story

c) **Cartography Sketch**
   - Regions with terrain types and descriptions
   - Routes connecting regions (adjacency must be bidirectional)
   - Key landmarks and points of interest

d) **NPC Archetypes** (6-10)
   - Historical role → genre archetype mapping
   - Disposition tendencies, motivations
   - Voice preset suggestions

e) **Trope Beats**
   - Story arcs drawn from historical conflicts
   - Escalation from FRESH through VETERAN maturity
   - Which factions drive which tropes

f) **Aesthetic Direction**
   - Visual style notes (Flux prompt suffix, negative prompt)
   - Music mood mapping
   - Font suggestion if new genre

### 2. Write the brief to a dedicated file

Write the complete brief to `.session/world-builder-wip/design-brief.md`. It lives there because every specialist invoked in step 6 will read it as shared context — passing it inline to five parallel Task calls would balloon token usage. The specialists get the path; they read it themselves.

### 3. Present / iterate (mode-dependent)

**IF `surprise: false` in the WIP frontmatter:**

Show the complete brief to the user. Format as a structured document, not a wall of text.

**HALT and wait for feedback.**

Common adjustments:
- Faction balance (too many allied, not enough conflict)
- Tone drift (too dark, too light for the genre)
- Naming issues (sounds wrong for the culture)
- Scope (too many regions, too few NPCs)

Revise and re-present until user says "go."

**IF `surprise: true`:**

Do not halt. Do not present. The brief is already written to the brief file; step 6 will read it directly. The deterministic safety rails (coherence assertion in step 3, dry-run dir in step 6, fact-diff in step 6, validate + cliche-judge in step 7) are what keeps surprise mode safe — not this gate. Proceed to step 6.

### 4. Update WIP

Append a brief-location pointer to `{wipFile}` (not the full brief — that lives in design-brief.md):

```markdown
## Design Brief

Location: `.session/world-builder-wip/design-brief.md`
Mode: {surprise ? "surprise — auto-generated, not approval-gated" : "manual — Keith-approved"}
Specialists will read this file directly in step 6.
```

Update frontmatter: `stepsCompleted: [1, 2, 3, 4, 5]`
