# Step 7: Decision Documentation

<purpose>
Consolidate all architecture decisions from previous steps into a formal Architecture Decision Record (ADR) or specification. Validate completeness and finalize the decision document for stakeholder review.
</purpose>

<instructions>
Validate all previous step outputs are complete before proceeding. Choose appropriate document type (ADR/Architecture Spec/Design Doc). Compile comprehensive decision record including context, drivers, options, outcome, components, interfaces, risks, and consistency rules. Write to appropriate location with proper linking.
</instructions>

<output>
Finalized architecture decision document (ADR or spec format) stored in docs/adr/ or appropriate location, with complete sections from all previous steps, validation confirmation, and completion summary. Update frontmatter stepsCompleted array with all steps completed.
</output>

<step-meta>
number: 7
name: documentation
gate: false
</step-meta>

## Mandatory Execution Rules

- READ the complete step file before taking any action
- COMPILE all outputs from previous steps into cohesive document
- VALIDATE completeness before finalizing
- ALWAYS treat this as collaborative completion between architectural peers

## Execution Protocols

- Show your analysis before taking any action
- Validate all sections are complete before generating document
- Present completion summary and options
- Update frontmatter `stepsCompleted: [1, 2, 3, 4, 5, 6, 7]`
- NO MORE STEPS - this is the final step

## Purpose

Consolidate the architecture decision into a formal document (ADR or architecture spec). Validate completeness before finalizing.

## Pre-Documentation Validation

Before compiling the document, verify:

- [ ] Context analysis is complete (Step 2)
- [ ] Patterns selected with rationale (Step 3)
- [ ] Components defined with boundaries (Step 4)
- [ ] Interfaces specified with contracts (Step 5)
- [ ] Risks assessed with mitigations (Step 6)

If any section is incomplete, report to user before proceeding.

## Instructions

1. **Compile Decision Record**:
   Gather outputs from all previous steps into a cohesive document:
   - Context and problem statement
   - Decision drivers (constraints, concerns)
   - Considered options
   - Decision outcome
   - Consequences

2. **Choose Document Type**:
   - **ADR**: For significant, reversible decisions
   - **Architecture Spec**: For system-wide design
   - **Design Doc**: For feature-level architecture

3. **Finalize and Store**:
   - Write to appropriate location
   - Link from session/story
   - Update architecture index if exists

## Actions

- Validate: All previous step outputs are complete
- Write: Architecture document using template
- Store: In `docs/adr/` or `docs/architecture/`
- Update: Any architecture index or registry

## Output

Create `{output_file}` using the template, containing:

```markdown
# ADR-NNNN: [Decision Title]

**Status:** Proposed | Accepted | Deprecated | Superseded
**Date:** {date}
**Author:** {agent} ({persona})

## Context

[Summary from Step 2 - Context Analysis]

## Decision Drivers

[Key concerns from Step 2]

## Considered Options

[Patterns from Step 3 with trade-offs]

## Decision Outcome

[Selected pattern(s) and rationale]

### Component Structure

[From Step 4]

### Interfaces

[From Step 5]

## Consequences

### Positive
- [Benefits]

### Negative
- [Trade-offs accepted]

### Risks and Mitigations
[From Step 6]

## Implementation Consistency Rules

[Rules that ensure AI agents implement consistently]

## Related Decisions

- [Links to related ADRs]
```

## Completion Menu

After generating document, present completion options:

- **[V] Validate** - Run comprehensive validation checks on the complete architecture
- **[E] Edit** - Make revisions to specific sections

## Validation Checks

When user selects [V]:
1. Verify all PRD requirements have corresponding architecture decisions
2. Check component boundaries align with domain concepts
3. Validate interfaces are complete and consistent
4. Confirm risks have appropriate mitigations
5. Report validation results with any gaps

## Completion

The architecture workflow is complete. The decision document is ready for review.

**Next steps:**
1. Review document with stakeholders
2. Update status to "Accepted" after approval
3. Begin implementation planning

## Success Metrics

- All previous step outputs compiled into document
- Validation checks passed
- Document written to appropriate location
- User confirmed completion


<switch tool="AskUserQuestion">
  <case value="validate" next="LOOP">
    Validate — Run comprehensive validation checks on the complete architecture
  </case>
  <case value="edit" next="LOOP">
    Edit — Make revisions to specific sections
  </case>
  <case value="complete" next="CONTINUE">
    Complete — Finalize document and end workflow
  </case>
  <case value="restart-section" next="LOOP">
    Restart Section — Go back to a specific step
  </case>
</switch>

## Failure Modes

- Missing sections from previous steps
- Incomplete validation
- Not confirming completion with user
