# Step 4: Component Design

<purpose>
Define major system components, their responsibilities, boundaries, and dependencies based on selected patterns. Establish implementation consistency rules that prevent AI agents from making conflicting architectural choices.
</purpose>

<instructions>
Identify primary components from selected patterns with clear responsibilities and data ownership. Define component boundaries and communication protocols. Map component dependencies. Document explicit consistency rules for AI implementation to ensure compatible implementations across different agents.
</instructions>

<output>
Component Design section with ASCII/Mermaid component diagram, Component Responsibilities table, Boundary Decisions, and Implementation Consistency Rules. Update frontmatter stepsCompleted array after user confirms via the switch prompt.
</output>

<step-meta>
number: 4
name: component-design
gate: true
</step-meta>

## Mandatory Execution Rules

- READ the complete step file before taking any action
- FOCUS on components that prevent AI agent implementation conflicts
- EMPHASIZE what agents could decide DIFFERENTLY if not specified
- ALWAYS treat this as collaborative discovery between architectural peers

## Execution Protocols

- Show your analysis before taking any action
- Present the switch prompt after generating component design
- ONLY save when user confirms via the switch prompt
- Update frontmatter `stepsCompleted: [1, 2, 3, 4]` before loading next step
- FORBIDDEN to load next step until user confirms via the switch prompt

## Purpose

Define the major components of the system and their responsibilities based on the selected patterns. Focus on clarity that prevents implementation ambiguity.

## Instructions

1. **Identify Components**:
   Based on the selected pattern(s), define the major building blocks:
   - What are the primary components/services?
   - What is each component responsible for?
   - What data does each component own?

2. **Define Boundaries**:
   - Where are the component boundaries?
   - What crosses each boundary?
   - How do components communicate?

3. **Map Dependencies**:
   - Which components depend on others?
   - Are there circular dependencies to avoid?
   - What is the deployment topology?

4. **Specify for Agent Consistency** (BMAD pattern):
   - What decisions must be consistent across implementations?
   - Where could two different AI agents make conflicting choices?
   - Document explicit rules to prevent divergence

## Actions

- Design: Component diagram (can be ASCII or Mermaid)
- Document: Component responsibilities
- Validate: Boundaries align with domain concepts
- Specify: Consistency rules for AI implementation

## Output

Add to session file:

```markdown
## Component Design

### Component Diagram

\`\`\`
┌─────────────┐     ┌─────────────┐
│ Component A │────▶│ Component B │
└─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ Component C │     │ Component D │
└─────────────┘     └─────────────┘
\`\`\`

### Component Responsibilities

| Component | Responsibility | Data Owned | Dependencies |
|-----------|---------------|------------|--------------|
| [A] | [what it does] | [data] | [deps] |
| [B] | [what it does] | [data] | [deps] |

### Boundary Decisions
- [Boundary 1]: [What crosses, protocol]
- [Boundary 2]: [What crosses, protocol]

### Implementation Consistency Rules
> These rules prevent AI agents from making conflicting implementation choices

- [Rule 1]: [Why this must be consistent]
- [Rule 2]: [Why this must be consistent]
```

<!-- GATE -->

## Success Metrics

- Components clearly defined with single responsibilities
- Boundaries align with domain concepts
- Dependencies mapped without cycles
- Implementation consistency rules documented
- User confirmed design before proceeding


<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Use discovery protocols to explore alternative component structures or hidden dependencies
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring multiple perspectives to evaluate component boundaries from different angles
  </case>
  <case value="continue" next="step-05-interfaces">
    Continue — Save the content and proceed to interface definition
  </case>
  <case value="revise" next="LOOP">
    Revise — Need to reconsider component structure or boundaries
  </case>
</switch>

## Failure Modes

- Ambiguous component responsibilities
- Unclear boundary decisions
- Missing consistency rules for AI implementation
- Proceeding without user confirmation
