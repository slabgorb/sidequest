# Step 2: Context Analysis

<purpose>
Analyze project context and requirements to identify technical constraints, current system landscape, and key architectural concerns that will drive pattern selection and design decisions.
</purpose>

<instructions>
Extract technical constraints from PRD (performance, security, integration requirements). Map existing systems and patterns. Identify scalability, reliability, maintainability, and cost concerns. Generate analysis and Present the switch prompt.
</instructions>

<output>
Architecture Context section in session file with Technical Constraints, Current Landscape overview, and Key Concerns documented. Update frontmatter stepsCompleted array after user confirms via the switch prompt.
</output>

<step-meta>
number: 2
name: context-analysis
gate: true
</step-meta>

## Mandatory Execution Rules

- READ the complete step file before taking any action
- ANALYZE loaded documents, don't assume or generate requirements
- ALWAYS treat this as collaborative discovery between architectural peers
- FOCUS on understanding project scope and requirements for architecture

## Execution Protocols

- Show your analysis before taking any action
- Present the switch prompt after generating context analysis
- ONLY save when user confirms via the switch prompt
- Update frontmatter `stepsCompleted: [1, 2]` before loading next step
- FORBIDDEN to load next step until user confirms via the switch prompt

## Purpose

Analyze the project context and identify architectural concerns that will shape the decision.

## Instructions

1. **Extract Technical Constraints** from the PRD:
   - Performance requirements (latency, throughput, scale)
   - Security and compliance requirements
   - Integration requirements with existing systems
   - Technology mandates or restrictions

2. **Map the Current Landscape**:
   - What systems already exist?
   - What are the integration points?
   - What patterns are already in use?

3. **Identify Key Concerns**:
   - Scalability needs
   - Reliability requirements
   - Maintainability considerations
   - Cost constraints

## Actions

- Read: `{planning_artifacts}/*prd*.md`
- Read: `**/project-context.md` (if exists)
- Grep: Search codebase for existing patterns

## Output

Add to session file:

```markdown
## Architecture Context

### Technical Constraints
- Performance: [requirements from PRD]
- Security: [requirements]
- Integration: [required touchpoints]

### Current Landscape
- Existing systems: [list]
- Patterns in use: [list]
- Tech stack: [languages, frameworks]

### Key Concerns
1. [Concern]: [Why it matters]
2. [Concern]: [Why it matters]
```

<!-- GATE -->

## Success Metrics

- Technical constraints extracted from PRD
- Current landscape mapped accurately
- Key concerns identified with rationale
- User confirmed context before proceeding


<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Use discovery protocols to develop deeper insights about project context and architectural implications
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring multiple perspectives to analyze project requirements from different architectural angles
  </case>
  <case value="continue" next="step-03-patterns">
    Continue — Save the content to the document and proceed to pattern selection
  </case>
  <case value="revise" next="LOOP">
    Revise — Need to gather more information or clarify constraints
  </case>
</switch>

## Failure Modes

- Generating requirements not found in documents
- Proceeding without user confirmation
- Missing critical constraints from PRD
