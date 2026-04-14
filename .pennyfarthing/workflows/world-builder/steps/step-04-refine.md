---
name: 'step-04-refine'
description: 'Second brainstorm — refine research findings into a coherent vision before the design brief'

nextStepFile: './step-05-design-brief.md'
wipFile: '{wip_file}'
---

<purpose>Now that research has surfaced real historical detail, riff again to decide what to keep, what to twist, and what to invent. This is where the world stops being "history with a genre skin" and becomes its own thing.</purpose>

<instructions>Present research findings, then brainstorm with the user on how to adapt, remix, and make the world uniquely SideQuest. Resolve open questions. Lock down the creative direction.</instructions>

<output>Updated WIP with refined creative direction, resolved questions, and clear inputs for the design brief. stepsCompleted: [1, 2, 3, 4].</output>

# Step 4: Refine

**Progress: Step 4 of 8**

## CONTEXT

Research is done. Three contrarian lenses have written their reports and world-builder has assembled a **collision artifact** listing where the lenses contradict each other. Now we decide what this world actually IS — which parts of history we keep faithful, which we twist, and which we throw out entirely.

**The collision is the point.** A contradiction between two lenses is not a bug to resolve — it is creative fuel. When the political lens says "the kingdom fell in 1240" and the spiritual lens says "the temple still receives offerings from that dynasty" — that tension IS the world. The refinement step decides which side of each contradiction to canonize and which to keep unresolved as a mystery the table plays to discover.

## HOW TO REFINE

### 1. Read the collision artifact first

Read `.session/world-builder-wip/collision.md` BEFORE the per-lens reports. The collision is the primary input for refinement; the per-lens reports are reference material for when a contradiction needs to be understood in depth.

Then read the per-lens reports at:
- `.session/world-builder-wip/research-political.md`
- `.session/world-builder-wip/research-material.md`
- `.session/world-builder-wip/research-spiritual.md`

### 2. Present the collision, not the research

Don't dump the full per-lens reports. Present the contradictions and shared anchors as creative prompts:

- "The three lenses agree on {shared anchor}, but political says X and spiritual says Y — which side does the world take, or does it keep the mystery?"
- "The material lens found {specific craft tradition} that nobody else mentioned — is this a faction-level detail or a world-level fact?"
- "All three lenses independently surfaced {named figure} — this is load-bearing, they're a canon anchor, protect them."
- "Political lens flagged a dependency it couldn't resolve ({thing}) — does the spiritual lens' answer work as canon, or do we invent something in that gap?"

### 2. Brainstorm Adaptation

For each key finding, ask:

- **Keep?** Use it fairly straight — it's compelling as-is
- **Twist?** Take the structure but change the context or outcome
- **Invent?** The history suggests a gap — what goes there in our world?
- **Cut?** Interesting but doesn't serve the genre or tone

### 3. Resolve Open Questions

From the riff and research steps, there should be open questions. Work through them:

- Mechanical fit ("does this work with the genre's rules?")
- Tone calibration ("is this too dark / too light?")
- Faction balance ("do we have enough conflict?")
- Naming direction ("do these sound right?")
- Scope ("is this too ambitious for one world?")

### 4. Lock Creative Direction

By the end of this step, these should be decided:

- **World identity** — name, tagline, tone
- **Faction lineup** — who, what they want, why they conflict
- **Geography shape** — what the map feels like
- **Key NPCs** — the 3-5 characters that define the world
- **Trope seeds** — the 2-3 story arcs that will drive play
- **What we're NOT doing** — explicit scope boundaries

## CAPTURE

Update riff notes with refinement decisions:

```markdown
## Refinement Decisions

### Kept from History
- {thing} — {why}

### Twisted
- {historical thing} → {our version} — {why the change}

### Invented
- {new thing} — {what gap it fills}

### Cut
- {thing we dropped} — {why}

### Locked Direction
- World name: {name}
- Tagline: {one line}
- Factions: {list}
- Scope: {what's in, what's out}
```

## EXIT

1. Read back the locked direction
2. Update WIP: append refinement notes, set `stepsCompleted: [1, 2, 3, 4]`

**IF `surprise: false` in the WIP frontmatter:**

Ask: "This is what goes into the design brief. Anything to change?"

**HALT until user confirms.**

**IF `surprise: true`:**

Do not halt. Proceed directly to step 5 design brief. The collision has already been read, the direction is locked by the coordinator's own synthesis of the contradictions. Trust the rails.
