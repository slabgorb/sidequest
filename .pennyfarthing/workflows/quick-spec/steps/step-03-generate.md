---
name: 'step-03-generate'
description: 'Build the implementation plan based on the technical mapping of constraints'

nextStepFile: './step-04-review.md'
wipFile: '{implementation_artifacts}/tech-spec-wip.md'
---

<purpose>Create the implementation sequence that addresses the requirement delta using the captured technical context. Produce actionable, ordered tasks with acceptance criteria.</purpose>

<instructions>Load WIP state, generate implementation tasks ordered by dependency, create Given/When/Then acceptance criteria, fill remaining sections (dependencies, testing, notes), write complete spec, proceed to review.</instructions>

<output>Complete tech-spec with implementation plan, acceptance criteria, and status set to 'review'. stepsCompleted: [1, 2, 3].</output>

# Step 3: Generate Implementation Plan

**Progress: Step 3 of 4** - Next: Review & Finalize

## RULES:

- MUST NOT skip steps.
- MUST NOT optimize sequence.
- MUST follow exact instructions.
- MUST NOT implement anything - just document.

## CONTEXT:

- Requires `{wipFile}` with defined "Overview" and "Context for Development" sections.
- Focus: Create the implementation sequence that addresses the requirement delta using the captured technical context.
- Output: Implementation-ready tasks with specific files and instructions.

## READY FOR DEVELOPMENT STANDARD:

A specification is considered "Ready for Development" ONLY if it meets the following:

- **Actionable**: Every task has a clear file path and specific action.
- **Logical**: Tasks are ordered by dependency (lowest level first).
- **Testable**: All ACs follow Given/When/Then and cover happy path and edge cases.
- **Complete**: All investigation results from Step 2 are inlined; no placeholders or "TBD".
- **Self-Contained**: A fresh agent can implement the feature without reading the workflow history.

## SEQUENCE OF INSTRUCTIONS

### 1. Load Current State

**Read `{wipFile}` completely and extract:**

- All frontmatter values
- Overview section (Problem, Solution, Scope)
- Context for Development section (Patterns, Files, Decisions)

### 2. Generate Implementation Plan

Generate specific implementation tasks:

a) **Task Breakdown**

- Each task should be a discrete, completable unit of work
- Tasks should be ordered logically (dependencies first)
- Include the specific files to modify in each task
- Be explicit about what changes to make

b) **Task Format**

```markdown
- [ ] Task N: Clear action description
  - File: `path/to/file.ext`
  - Action: Specific change to make
  - Notes: Any implementation details
```

### 3. Generate Acceptance Criteria

**Create testable acceptance criteria:**

Each AC should follow Given/When/Then format:

```markdown
- [ ] AC N: Given [precondition], when [action], then [expected result]
```

**Ensure ACs cover:**

- Happy path functionality
- Error handling
- Edge cases (if relevant)
- Integration points (if relevant)

### 4. Complete Additional Context

**Fill in remaining sections:**

a) **Dependencies**

- External libraries or services needed
- Other tasks or features this depends on
- API or data dependencies

b) **Testing Strategy**

- Unit tests needed
- Integration tests needed
- Manual testing steps

c) **Notes**

- High-risk items from pre-mortem analysis
- Known limitations
- Future considerations (out of scope but worth noting)

### 5. Write Complete Spec

a) **Update `{wipFile}` with all generated content:**

- Ensure all template sections are filled in
- No placeholder text remaining
- All frontmatter values current
- Update status to 'review' (NOT 'ready-for-dev' - that happens after user review in Step 4)

b) **Update frontmatter:**

```yaml
---
# ... existing values ...
status: 'review'
stepsCompleted: [1, 2, 3]
---
```

c) **Read fully and follow: `{nextStepFile}` (Step 4)**

## REQUIRED OUTPUTS:

- Tasks MUST be specific, actionable, ordered logically, with files to modify.
- ACs MUST be testable, using Given/When/Then format.
- Status MUST be updated to 'review'.

## VERIFICATION CHECKLIST:

- [ ] `stepsCompleted: [1, 2, 3]` set in frontmatter.
- [ ] Spec meets the **READY FOR DEVELOPMENT** standard.
