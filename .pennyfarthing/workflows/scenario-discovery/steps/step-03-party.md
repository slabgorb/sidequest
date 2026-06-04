# Step 3: Party Mode Discovery

<step-meta>
step: 3
workflow: scenario-discovery
agent: orchestrator
name: party
gate: true
next: step-04-observe
</step-meta>

<purpose>
Run the prepared stimulus through party mode with the selected personas. This is the
core discovery step -- observe how different personas respond to the same stimulus,
what they catch, what they miss, and how their personality influences their approach.

Scientific basis: PersonaGym's Expected Action task -- "given this scenario, what does
the persona do?" We're running it live with our themed characters.
</purpose>

<prerequisites>
- Stimulus package prepared (step 2)
- Agent roles selected
- Ground truth set aside (not revealed)
</prerequisites>

<instructions>
1. Enter party mode with the selected agents using the prepared stimulus

2. Use the Skill tool to invoke `/pf-party-mode` with:
   - The stimulus prompt as the initial topic
   - The code snippet or situation brief as context

3. During the discussion, observe WITHOUT correcting:
   - Which persona identifies the key finding first?
   - Which persona frames it as highest priority?
   - Which persona misses it entirely?
   - Do any personas catch things NOT in your ground truth (novel findings)?
   - How does each persona's communication style affect their analysis?
   - Do personas disagree? On what? Why?

4. Run 2-3 rounds of discussion:
   - Round 1: Initial reactions to the stimulus
   - Round 2: "What else are you concerned about?" (probes for depth)
   - Round 3: "Prioritize your top 3 findings." (forces ranking)

5. If using detection stimulus, optionally probe the red herrings:
   - "What about [red herring area]? Any concerns there?"
   - Track which personas take the bait vs which see through it

6. Exit party mode and capture the full discussion
</instructions>

<actions>
- Run: `/pf-party-mode` with stimulus content
</actions>

## Recording Template

During the party mode session, take notes using this template:

```markdown
## Party Mode Observations

### Round 1: Initial Reactions
| Persona | Key Finding Found? | Priority Given | Notable Framing |
|---------|-------------------|----------------|-----------------|
| {name}  | yes/no/partial    | high/med/low   | how they framed it |

### Round 2: Depth Probe
| Persona | Additional Findings | Missed Items | Novel Discoveries |
|---------|--------------------:|-------------:|------------------:|
| {name}  | what else they found | what they missed | things not in ground truth |

### Round 3: Prioritization
| Persona | Top 3 Priorities | Reasoning Style |
|---------|------------------|-----------------|
| {name}  | 1. 2. 3.         | risk-averse / pragmatic / creative / systematic |

### Red Herring Responses (detection only)
| Persona | Took Bait? | Explanation |
|---------|------------|-------------|
| {name}  | yes/no     | how they responded |

### Cross-Talk Patterns
- Who agreed with whom?
- What disagreements emerged?
- Did any persona change position based on another's argument?

### Persona Influence Observations
- Which personality traits visibly affected analysis?
  (e.g., cautious characters flagged more risks, creative characters proposed alternatives)
- Did persona affect WHAT was found, or only HOW it was communicated?
```

<output>
Completed party mode session with:
- Full discussion transcript
- Observation notes per the recording template
- Initial assessment of which personas excelled and which struggled
</output>

<gate>
## Completion Criteria
- [ ] Party mode session completed with all selected agents
- [ ] At least 2 discussion rounds conducted
- [ ] Observations recorded per template
- [ ] Ground truth was NOT revealed during the session
- [ ] Novel findings (if any) documented
</gate>

<next-step>
After party mode session, proceed to step-04-observe.md to analyze observations and
extract behavioral anchors.
</next-step>

## Failure Modes

- Correcting personas during the session (biases the observation)
- Running only 1 round (insufficient depth for behavioral anchors)
- Not recording observations (memory fades, need structured notes)
- Revealing ground truth mid-session
