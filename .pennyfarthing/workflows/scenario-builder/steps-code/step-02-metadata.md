# Step 2: Common Metadata

<step-meta>
number: 2
name: metadata
gate: true
next: step-03-code-content
</step-meta>

<purpose>
Gather all common metadata fields shared across both code-based and open-ended scenarios.
</purpose>

<prerequisites>
- Category selected (step 1)
- Scenario ID auto-derived
- Mode determined (code or open-ended)
</prerequisites>

<instructions>
1. Confirm or modify the auto-derived scenario ID (e.g., `cr-003`)
2. Gather the scenario name (human-readable title)
3. Select difficulty level: easy, medium, hard, extreme
4. Write a description explaining what the scenario tests
5. Write instructions that will be given to the agent (the prompt)
6. Confirm the agent assignment (usually auto-determined by category)
7. Optionally add tags for discoverability
8. Derive the filename slug from the name (e.g., "User Service Review" -> `user-service-review`)
</instructions>

## Field Reference

| Field | Required | Example | Notes |
|-------|----------|---------|-------|
| `id` | Yes | `cr-003` | Auto-derived, user can override |
| `name` | Yes | `Auth Module Security Review` | Human-readable title |
| `category` | Yes | `code-review` | From step 1 |
| `difficulty` | Yes | `medium` | easy, medium, hard, extreme |
| `agent` | Yes | `reviewer` | Usually auto-determined by category |
| `description` | Yes | Multi-line | What the scenario tests and why |
| `instructions` | Yes | Multi-line | The actual prompt given to the agent |
| `tags` | No | `[security, go, sql]` | For filtering and search |
| `version` | Auto | `1.0` | Always starts at 1.0 |

## Difficulty Guidelines

| Level | Description |
|-------|-------------|
| `easy` | Obvious issues, straightforward scenario, good for calibration |
| `medium` | Mix of obvious and subtle issues, standard complexity |
| `hard` | Subtle issues, complex interactions, requires deep analysis |
| `extreme` | Expert-level, requires domain expertise, many interconnected issues |

## Instructions Writing Tips

- Write as if briefing the agent on a real task
- Don't hint at specific issues or considerations
- For code scenarios: "Review this code for..." or "Write tests for..."
- For open-ended: frame the problem clearly with all necessary context
- Include what deliverables are expected

<output>
All common metadata fields populated:
- id, name, category, difficulty, agent, description, instructions, tags, version
- Output filename derived: `{scenario_id}-{slug}.yaml`
</output>

<gate>
## Completion Criteria
- [ ] Scenario ID confirmed (valid format: `{prefix}-{NNN}`)
- [ ] Name provided (descriptive, concise)
- [ ] Difficulty selected from valid options
- [ ] Description written (explains what is being tested)
- [ ] Instructions written (clear prompt for the agent)
- [ ] Agent assignment confirmed
- [ ] Output filename derived
</gate>

<next-step>
After all metadata fields are populated, proceed to step-03-code-content.md for code authoring.
</next-step>

## Failure Modes

- Skipping the instructions field (most important field for agent evaluation)
- Using a duplicate ID that conflicts with existing scenarios
- Writing instructions that reveal the answers (known issues or considerations)
