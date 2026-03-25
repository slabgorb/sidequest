# Step 2: Common Metadata

<step-meta>
number: 2
name: metadata
gate: true
next: step-03-narrative
</step-meta>

<purpose>
Gather all common metadata fields shared across both code-based and open-ended scenarios.
</purpose>

<prerequisites>
- Category selected (step 1)
- Scenario ID auto-derived
- Mode determined (open-ended)
</prerequisites>

<instructions>
1. Confirm or modify the auto-derived scenario ID (e.g., `arch-002`)
2. Gather the scenario name (human-readable title)
3. Select difficulty level: easy, medium, hard, extreme
4. Write a description explaining what the scenario tests
5. Write a purpose statement explaining what makes this scenario valuable for benchmarking
6. Write instructions that will be given to the agent (the prompt)
7. Confirm the agent assignment (usually auto-determined by category)
8. Optionally add tags for discoverability
9. Derive the filename slug from the name (e.g., "Notification System Architecture" -> `notification-system`)
</instructions>

## Field Reference

| Field | Required | Example | Notes |
|-------|----------|---------|-------|
| `id` | Yes | `arch-002` | Auto-derived, user can override |
| `name` | Yes | `Event Sourcing Migration` | Human-readable title |
| `category` | Yes | `architecture` | From step 1 |
| `difficulty` | Yes | `hard` | easy, medium, hard, extreme |
| `agent` | Yes | `architect` | Usually auto-determined by category |
| `description` | Yes | Multi-line | What the scenario tests and why |
| `purpose` | Yes | Multi-line | Why this scenario is valuable for persona benchmarking |
| `instructions` | Yes | Multi-line | The actual prompt given to the agent |
| `tags` | No | `[architecture, event-sourcing]` | For filtering and search |
| `version` | Auto | `1.0` | Always starts at 1.0 |

## Difficulty Guidelines

| Level | Description |
|-------|-------------|
| `easy` | Clear requirements, limited trade-offs, good for calibration |
| `medium` | Multiple valid approaches, some competing concerns |
| `hard` | Complex trade-offs, stakeholder tensions, requires nuanced analysis |
| `extreme` | Highly ambiguous, many competing constraints, no obviously right answer |

## Open-Ended Instructions Tips

- Frame a realistic business/technical problem
- Include enough context for informed analysis
- Don't hint at preferred solutions
- Specify expected deliverables (sections, depth)
- For PM: include stakeholder dynamics and competing priorities
- For architecture: include both functional and non-functional requirements
- For SM: include feature complexity and team constraints

<output>
All common metadata fields populated:
- id, name, category, difficulty, agent, description, purpose, instructions, tags, version
- Output filename derived: `{scenario_id}-{slug}.yaml`
</output>

<gate>
## Completion Criteria
- [ ] Scenario ID confirmed (valid format: `{prefix}-{NNN}`)
- [ ] Name provided (descriptive, concise)
- [ ] Difficulty selected from valid options
- [ ] Description written (explains what is being tested)
- [ ] Purpose written (explains benchmarking value)
- [ ] Instructions written (clear prompt for the agent)
- [ ] Agent assignment confirmed
- [ ] Output filename derived
</gate>

<next-step>
After all metadata fields are populated, proceed to step-03-narrative.md for scenario narrative authoring.
</next-step>

## Failure Modes

- Skipping the instructions field (most important field for agent evaluation)
- Using a duplicate ID that conflicts with existing scenarios
- Writing instructions that reveal the expected considerations or rubric
- Not including a purpose statement (unique to open-ended scenarios)
