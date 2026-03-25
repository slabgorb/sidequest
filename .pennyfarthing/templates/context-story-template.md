---
parent: context-epic-{N}.md
workflow: {workflow}
---

# Story {id}: {title}

## Business Context

{Explain WHY this story matters. What business value does it deliver?
Draw from the parent epic context and the story's acceptance criteria.
Include the user problem being solved and expected outcomes.}

## Technical Guardrails

{Constraints and patterns from the parent epic's architecture section.
Include:
- Key files to modify or extend
- Patterns to follow (from epic architecture)
- Dependencies and integration points
- What NOT to touch (scope boundaries from architecture)}

## Scope Boundaries

**In scope:**
- {What this story WILL deliver}

**Out of scope:**
- {What this story will NOT deliver — deferred to other stories}

## AC Context

{Expand terse acceptance criteria into testable detail. For each AC:
- What exactly must be true for this AC to pass?
- What are the edge cases?
- How would a test verify this?}

## Assumptions

{Assumptions the team is making about this story's implementation.
Include:
- Technical assumptions (e.g., "existing API supports X")
- Domain assumptions (e.g., "users always have Y configured")
- Dependency assumptions (e.g., "story Z-N is merged before this starts")

If an assumption proves wrong during implementation, log it as a
Design Deviation and notify SM. Wrong assumptions are the #1 source
of scope creep and rework.}

## Interaction Patterns

{Optional: UI flows, user journeys, state transitions.
Include only if relevant to this story's workflow type.}

## Accessibility Requirements

{Optional: a11y constraints, ARIA roles, keyboard navigation.
Include only for frontend/UI stories.}

## Visual Constraints

{Optional: Design system tokens, layout rules, responsive breakpoints.
Include only for UI stories.}
