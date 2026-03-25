# Step 5: Interface Definition

<purpose>
Define APIs, internal contracts, and communication patterns between components. Establish naming conventions, error handling, and versioning strategies that ensure explicit, unambiguous contracts for consistent implementation.
</purpose>

<instructions>
Define external APIs with authentication and request/response formats. Specify internal component communication (synchronous/asynchronous) with exact message formats. Establish naming conventions, error codes, and versioning strategy. Document contract enforcement rules explicit enough for independent implementations.
</instructions>

<output>
Interface Definitions section with External APIs table, Internal Communication protocols, Conventions documented, and Contract Enforcement rules. Update frontmatter stepsCompleted array after user confirms via the switch prompt.
</output>

<step-meta>
number: 5
name: interface-definition
gate: false
</step-meta>

## Mandatory Execution Rules

- READ the complete step file before taking any action
- DEFINE explicit contracts that prevent implementation ambiguity
- ALWAYS treat this as collaborative discovery between architectural peers
- FOCUS on conventions that ensure consistent implementations

## Execution Protocols

- Show your analysis before taking any action
- Present the switch prompt after generating interface definitions
- ONLY save when user confirms via the switch prompt
- Update frontmatter `stepsCompleted: [1, 2, 3, 4, 5]` before loading next step
- FORBIDDEN to load next step until user confirms via the switch prompt

## Purpose

Define the APIs, contracts, and communication patterns between components. Establish conventions that ensure consistent implementation across different agents or developers.

## Instructions

1. **Define External APIs**:
   - What APIs does the system expose?
   - What authentication/authorization is needed?
   - What are the request/response formats?

2. **Define Internal Contracts**:
   - How do components communicate?
   - Synchronous (HTTP, gRPC) or asynchronous (events, queues)?
   - What are the message formats?

3. **Establish Conventions**:
   - Naming conventions
   - Error handling patterns
   - Versioning strategy

4. **Document for Consistency**:
   - Explicit enough that two implementations would be compatible
   - No room for interpretation on critical contracts

## Actions

- Design: API contracts (OpenAPI, protobuf, or pseudocode)
- Document: Event schemas if using async
- Define: Error codes and handling
- Specify: Conventions that must be followed

## Output

Add to session file:

```markdown
## Interface Definitions

### External APIs

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| /api/v1/resource | GET | List resources | Bearer |
| /api/v1/resource | POST | Create resource | Bearer |

### Internal Communication

| From | To | Type | Contract |
|------|----|----- |----------|
| A | B | HTTP | GET /internal/data |
| B | C | Event | DataUpdated { id, payload } |

### Conventions
- **Naming**: [snake_case, camelCase, etc.]
- **Errors**: [HTTP codes, error envelope format]
- **Versioning**: [URL path, header, etc.]

### Contract Enforcement
> Rules that ensure consistent implementation

- [Contract 1]: [Exact specification]
- [Contract 2]: [Exact specification]
```

## Success Metrics

- External APIs clearly documented
- Internal contracts specify exact message formats
- Conventions established for naming, errors, versioning
- Contracts explicit enough for independent implementation
- User confirmed interfaces before proceeding

## Failure Modes

- Ambiguous contract specifications
- Missing error handling definitions
- Inconsistent naming conventions
- Proceeding without user confirmation


<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Use discovery protocols to identify missing contracts or edge cases
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring multiple perspectives to evaluate API design from different consumer viewpoints
  </case>
  <case value="continue" next="step-06-risks">
    Continue — Save the content and proceed to risk assessment
  </case>
  <case value="revise" next="LOOP">
    Revise — Need to reconsider interface design or add missing contracts
  </case>
</switch>
