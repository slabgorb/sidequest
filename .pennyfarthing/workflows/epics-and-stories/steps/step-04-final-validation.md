---
name: 'step-04-final-validation'
description: 'Validate complete coverage of all requirements and ensure implementation readiness'

# Path Definitions
workflow_path: '{project_root}/.pennyfarthing/workflows/epics-and-stories'

# File References
thisStepFile: './step-04-final-validation.md'
nextStepFile: './step-05-import-to-future.md'
workflowFile: '{workflow_path}/workflow.yaml'
outputFile: '{planning_artifacts}/epics.md'

# Task References (BMAD features - not yet available in Pennyfarthing)
# advancedElicitationTask: '{project_root}/.pennyfarthing/workflows/advanced-elicitation/workflow.yaml'
# partyModeWorkflow: '{project_root}/.pennyfarthing/workflows/party-mode/workflow.yaml'

# Template References
epicsTemplate: './templates/epics-template.md'
---

<purpose>
To validate that all requirements are completely covered by stories, verify story quality and dependencies are correct, ensure the document follows the template structure exactly, and confirm everything is ready for development work.
</purpose>

<instructions>
1. Load the complete epic and story breakdown from the previous step
2. Perform FR coverage validation to ensure every FR is covered by at least one story
3. Validate architecture implementation requirements (starter template, database setup)
4. Validate story quality (completable by single dev agent, clear acceptance criteria, no forward dependencies)
5. Validate epic structure for user value and proper dependencies
6. Perform critical dependency validation (epic independence and within-epic story flow)
7. Update any remaining placeholders and verify formatting
8. Get user confirmation (C) to proceed to import step
</instructions>

<output>
- Verification that every FR has story coverage
- Confirmation of proper architecture requirements implementation
- Validation that stories are appropriately sized and have clear acceptance criteria
- Confirmation of proper story dependencies (only depend on previous stories)
- Final epics.md file with all placeholders replaced and formatting verified
- User confirmation that document is complete and ready for development
</output>

# Step 4: Final Validation

## STEP GOAL:

To validate complete coverage of all requirements and ensure stories are ready for development.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: Process validation sequentially without skipping
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

### Role Reinforcement:

- ✅ You are a product strategist and technical specifications writer
- ✅ If you already have been given communication or persona patterns, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring validation expertise and quality assurance
- ✅ User brings their implementation priorities and final review

### Step-Specific Rules:

- 🎯 Focus ONLY on validating complete requirements coverage
- 🚫 FORBIDDEN to skip any validation checks
- 💬 Validate FR coverage, story completeness, and dependencies
- 🚪 ENSURE all stories are ready for development

## EXECUTION PROTOCOLS:

- 🎯 Validate every requirement has story coverage
- 💾 Check story dependencies and flow
- 📖 Verify architecture compliance
- 🚫 FORBIDDEN to approve incomplete coverage

## CONTEXT BOUNDARIES:

- Available context: Complete epic and story breakdown from previous steps
- Focus: Final validation of requirements coverage and story readiness
- Limits: Validation only, no new content creation
- Dependencies: Completed story generation from Step 3

## VALIDATION PROCESS:

### 1. FR Coverage Validation

Review the complete epic and story breakdown to ensure EVERY FR is covered:

**CRITICAL CHECK:**

- Go through each FR from the Requirements Inventory
- Verify it appears in at least one story
- Check that acceptance criteria fully address the FR
- No FRs should be left uncovered

### 2. Architecture Implementation Validation

**Check for Starter Template Setup:**

- Does Architecture document specify a starter template?
- If YES: Epic 1 Story 1 must be "Set up initial project from starter template"
- This includes cloning, installing dependencies, initial configuration

**Database/Entity Creation Validation:**

- Are database tables/entities created ONLY when needed by stories?
- ❌ WRONG: Epic 1 creates all tables upfront
- ✅ RIGHT: Tables created as part of the first story that needs them
- Each story should create/modify ONLY what it needs

### 3. Story Quality Validation

**Each story must:**

- Be completable by a single dev agent
- Have clear acceptance criteria
- Reference specific FRs it implements
- Include necessary technical details
- **Not have forward dependencies** (can only depend on PREVIOUS stories)
- Be implementable without waiting for future stories

### 4. Epic Structure Validation

**Check that:**

- Epics deliver user value, not technical milestones
- Dependencies flow naturally
- Foundation stories only setup what's needed
- No big upfront technical work

### 5. Dependency Validation (CRITICAL)

**Epic Independence Check:**

- Does each epic deliver COMPLETE functionality for its domain?
- Can Epic 2 function without Epic 3 being implemented?
- Can Epic 3 function standalone using Epic 1 & 2 outputs?
- ❌ WRONG: Epic 2 requires Epic 3 features to work
- ✅ RIGHT: Each epic is independently valuable

**Within-Epic Story Dependency Check:**
For each epic, review stories in order:

- Can Story N.1 be completed without Stories N.2, N.3, etc.?
- Can Story N.2 be completed using only Story N.1 output?
- Can Story N.3 be completed using only Stories N.1 & N.2 outputs?
- ❌ WRONG: "This story depends on a future story"
- ❌ WRONG: Story references features not yet implemented
- ✅ RIGHT: Each story builds only on previous stories

### 6. Complete and Save

If all validations pass:

- Update any remaining placeholders in the document
- Ensure proper formatting
- Save the final epics.md

**All validations complete!** Present the switch prompt to continue.

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN user confirms via the switch prompt and validations are complete, will you then load, read entire file, then execute {nextStepFile} to import epics to future.yaml.
