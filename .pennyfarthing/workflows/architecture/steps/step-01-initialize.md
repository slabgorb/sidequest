# Step 1: Initialize Architecture Session

<purpose>
Set up the architecture decision session by gathering inputs, detecting existing workflows, and establishing initial context for collaborative architectural discovery.
</purpose>

<instructions>
Check for existing workflow and either resume from continuation or initialize fresh session. Gather required inputs (PRD, existing documentation, constraints), identify stakeholders, and present collaboration options to proceed.
</instructions>

<output>
Session workspace initialized with frontmatter and either workflow continuation state or fresh initialization summary including discovered inputs, stakeholders, and ready-to-continue status.
</output>

<step-meta>
number: 1
name: initialize
gate: false
</step-meta>

## Mandatory Execution Rules

- READ the complete step file before taking any action
- DETECT existing workflow state before initialization
- NEVER generate content without user input
- ALWAYS treat this as collaborative discovery between architectural peers
- FOCUS on initialization only - don't look ahead to future steps

## Execution Protocols

- Show your analysis before taking any action
- Initialize document and update frontmatter
- Set up frontmatter `stepsCompleted: [1]` before loading next step
- FORBIDDEN to load next step until setup is complete

## Purpose

Set up the architecture decision session by gathering inputs and establishing context.

## Continuation Detection

**First, check for existing workflow:**

1. Look for existing `{output_file}`
2. If exists, read complete file including frontmatter
3. If frontmatter has `stepsCompleted` array → **Load `./step-01b-continue.md`**
4. If not exists → proceed with fresh initialization below

## Instructions

1. **Verify required inputs exist**:
   - Product Requirements Document (PRD) or feature brief
   - Any existing architecture documentation
   - Relevant ADRs from `docs/adr/`

2. **Create session workspace**:
   - Output file: `{output_file}`
   - Working notes in session file

3. **Identify stakeholders and constraints**:
   - Who needs to approve this decision?
   - What are the timeline constraints?
   - Are there budget or resource limitations?

## Actions

- Check: `{output_file}` for existing workflow (continuation detection)
- Read: `{planning_artifacts}/*prd*.md` or `{planning_artifacts}/*brief*.md`
- Read: `docs/adr/*.md` (scan for relevant prior decisions)
- Read: Existing architecture docs if referenced

## Output

Add to session file:

```markdown
## Architecture Session: {project_name}

### Inputs Gathered
- PRD: [path or "not found"]
- Existing ADRs: [list relevant ones]
- Constraints: [timeline, budget, resources]

### Stakeholders
- Decision maker: [name/role]
- Reviewers: [list]
```

## Success Metrics

- Existing workflow detected and handed off to step-01b correctly
- Fresh workflow initialized with proper setup
- Input documents discovered and loaded
- PRD requirement validated and communicated
- User confirmed document setup before proceeding

## Failure Modes

- Proceeding with fresh initialization when existing workflow exists
- Not detecting PRD requirement
- Not confirming inputs with user before proceeding


<switch tool="AskUserQuestion">
  <case value="continue" next="step-02-context">
    Continue — Inputs gathered, proceed to Context Analysis
  </case>
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Use discovery protocols to find additional context
  </case>
  <case value="revise" next="LOOP">
    Revise — Need to locate missing inputs before proceeding
  </case>
</switch>
