# Step 2: Prepare Party Mode Stimulus

<step-meta>
step: 2
workflow: scenario-discovery
agent: orchestrator
name: prepare
gate: true
next: step-03-party
</step-meta>

<purpose>
Transform the raw finding into a stimulus that can be presented to multiple personas
in party mode. The stimulus must be neutral -- it should not hint at the correct answer
or prime agents toward a specific response.
</purpose>

<prerequisites>
- Source finding captured (step 1)
- Ground truth documented but set aside (not shown to personas)
- Family determined (detection or divergent)
</prerequisites>

<instructions>
1. For **detection** sources: extract or write a code snippet that contains the finding
   - Include enough surrounding context for a realistic review
   - Do NOT add comments pointing at the bug
   - Optionally add 1-2 red herrings (things that look wrong but aren't)
   - Keep it to 30-80 lines -- long enough to be realistic, short enough for party mode

2. For **divergent** sources: write a situation brief
   - Present the real constraints, stakeholders, and tensions
   - Include conflicting valid perspectives (no obvious right answer)
   - Add enough detail for substantive discussion (budget, timeline, team, tech stack)
   - Remove any framing that reveals what actually happened

3. Define the prompt for party mode
   - Detection: "Review this code. What issues do you see? Prioritize them."
   - Divergent: "Given this situation, what would you recommend and why?"

4. Select 3-5 agent roles to participate based on the domain:
   - Code bugs: dev, reviewer, tea, architect
   - Architecture decisions: architect, dev, devops, pm
   - Sprint/process: sm, pm, dev, tea
   - Prioritization: pm, architect, ba, dev
</instructions>

<actions>
- Read: Source code file or project history from step 1
- Read: Lang-review gate for relevant checks (if applicable)
</actions>

<output>
Party mode stimulus package:

```yaml
stimulus:
  family: detection | divergent
  prompt: "the neutral question to ask all personas"
  content: |
    [code snippet or situation brief -- 30-80 lines]
  red_herrings: []          # detection only
  selected_agents:
    - role: dev
      reason: "primary implementer perspective"
    - role: reviewer
      reason: "adversarial detection perspective"
    - role: tea
      reason: "testability and edge case perspective"
  ground_truth_hidden: true  # reminder: don't show ground truth during party mode
```
</output>

<gate>
## Completion Criteria
- [ ] Stimulus content prepared (code snippet or situation brief)
- [ ] Prompt is neutral (doesn't hint at the answer)
- [ ] Red herrings added (detection scenarios, at least 1)
- [ ] 3-5 agent roles selected with rationale
- [ ] Ground truth is NOT embedded in the stimulus
- [ ] User has reviewed and approved the stimulus
</gate>

<next-step>
After stimulus is prepared, proceed to step-03-party.md for multi-persona evaluation.
</next-step>

## Failure Modes

- Embedding the answer in the prompt ("Review this code that has a SQL injection")
- Making code snippets too short (no realistic context) or too long (party mode fatigue)
- Selecting agents whose roles all overlap (need diverse perspectives, not redundancy)
- Including ground truth in the stimulus
