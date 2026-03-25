# Step 3: Scenario Narrative

<step-meta>
number: 3
name: narrative
gate: true
next: step-04-scoring
</step-meta>

<purpose>
Author the scenario narrative — the rich problem description, context, and constraints that the agent will analyze. This is the core content that differentiates open-ended scenarios from code-based ones.
</purpose>

<prerequisites>
- All metadata populated (step 2)
- Category is open-ended (architecture, pm, sm)
</prerequisites>

<instructions>
1. Author the scenario content based on category type:
   - **Architecture**: technical problem with functional and non-functional requirements
   - **PM**: company context, competing options, stakeholder dynamics
   - **SM**: feature request with team context and breakdown complexity
2. Include a scenario title (short, descriptive)
3. Write the full scenario content as a rich narrative
4. For PM scenarios: add `stakeholder_dynamics` list
5. Ensure sufficient complexity for the chosen difficulty level
6. The narrative should enable divergent but valid approaches — no single "right answer"
</instructions>

<actions>
- Read: `{benchmarks_root}/{scenario_category}/` for existing scenarios as style reference
</actions>

## Category-Specific Narrative Guidance

### Architecture Scenarios

Structure the narrative with:
- **Context** — company/system background
- **Functional Requirements** — what the system must do (bulleted list)
- **Non-Functional Requirements** — performance, scale, reliability targets with specific numbers
- **Constraints** — team size, timeline, existing tech stack
- **Deliverables** — what the architect should produce

Example sections from `arch-001`:
```yaml
scenario:
  title: "Q2 Feature Prioritization"
  content: |
    ## Context
    ...
    ### Functional Requirements
    - Requirement 1 with specifics
    ...
    ### Non-Functional Requirements
    - Handle 10,000 requests per minute
    ...
```

### PM Scenarios

Structure the narrative with:
- **Context** — company situation with real metrics (ARR, churn, runway)
- **The Options** — 3-6 competing features/initiatives with sponsors
- **Stakeholder Dynamics** — relationships, tensions, political dynamics
- **Additional Context** — constraints, deadlines, team morale
- **Deliverables** — assessment, prioritization, communication plan

Include a separate `stakeholder_dynamics` list:
```yaml
stakeholder_dynamics:
  - "Sarah and Diana don't get along"
  - "CEO often overrules the PM"
```

### SM Scenarios

Structure the narrative with:
- **Feature Request** — what needs to be built
- **Team Context** — team size, skills, velocity
- **Complexity Factors** — dependencies, unknowns, technical debt
- **Sprint Constraints** — capacity, deadlines, competing work
- **Deliverables** — breakdown, estimation, sprint plan

## Complexity Calibration

| Difficulty | Narrative Complexity |
|------------|---------------------|
| easy | Clear problem, 2-3 trade-offs, limited stakeholders |
| medium | Multiple concerns, 3-5 trade-offs, some ambiguity |
| hard | Competing constraints, 5+ trade-offs, stakeholder tensions, hidden dynamics |
| extreme | Highly ambiguous, many valid approaches, political complexity, cascading consequences |

<output>
Complete scenario narrative:
- `scenario.title`: short descriptive title
- `scenario.content`: full narrative with context, requirements, and constraints
- For PM: `stakeholder_dynamics` list
- Narrative complexity appropriate for difficulty level
</output>

<gate>
## Completion Criteria
- [ ] Scenario title is concise and descriptive
- [ ] Narrative includes sufficient context for informed analysis
- [ ] Requirements/options are specific enough to evaluate
- [ ] Complexity matches the selected difficulty level
- [ ] No single obviously correct answer — multiple valid approaches possible
- [ ] For PM: stakeholder dynamics included
- [ ] Narrative enables persona differentiation (different personas should legitimately arrive at different conclusions)
</gate>

<next-step>
After narrative is complete, proceed to step-04-scoring.md to define considerations, rubric, and persona mappings.
</next-step>

## Failure Modes

- Narrative too simple for the difficulty level
- Including hints toward a preferred solution
- Not enough context for the agent to do meaningful analysis
- Only one valid approach (doesn't test persona differentiation)
- PM scenario without stakeholder dynamics
