---
name: 'step-07-project-type'
description: 'Conduct project-type specific discovery using CSV-driven guidance'

# File References
nextStepFile: './step-08-scoping.md'
outputFile: '{planning_artifacts}/prd.md'

# Data Files
projectTypesCSV: '../data/project-types.csv'

# Task References
advancedElicitationTask: '{project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{project_root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 7: Project-Type Deep Dive

<purpose>Conduct project-type specific discovery using CSV-driven guidance to explore key considerations unique to the product type.</purpose>

<instructions>Load project-type guidance from CSV file matching the detected project type; use guidance framework to conduct type-specific discovery dialogue; explore type-specific features, architecture patterns, and considerations; document project-type insights.</instructions>

<output>Project-type specific discovery documentation capturing type-specific features, architectural considerations, and key discovery insights for the product type.</output>

**Progress: Step 7 of 11** - Next: Scoping

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input

- 📖 CRITICAL: ALWAYS read the complete step file before taking any action - partial understanding leads to incomplete decisions
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read and understood before proceeding
- ✅ ALWAYS treat this as collaborative discovery between PM peers
- 📋 YOU ARE A FACILITATOR, not a content generator
- 💬 FOCUS on project-type specific requirements and technical considerations
- 🎯 DATA-DRIVEN: Use CSV configuration to guide discovery
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- ⚠️ Present the switch prompt after generating project-type content
- 💾 ONLY save when user confirms via the switch prompt
- 📖 Update output file frontmatter, adding this step name to the end of the list of stepsCompleted
- 🚫 FORBIDDEN to load next step until user confirms via the switch prompt

## CONTEXT BOUNDARIES:

- Current document and frontmatter from previous steps are available
- Project type from step-02 is available for configuration loading
- Project-type CSV data will be loaded in this step
- Focus on technical and functional requirements specific to this project type

## YOUR TASK:

Conduct project-type specific discovery using CSV-driven guidance to define technical requirements.

## PROJECT-TYPE DISCOVERY SEQUENCE:

### 1. Load Project-Type Configuration Data

**Attempt subprocess data lookup:**

"Your task: Lookup data in {projectTypesCSV}

**Search criteria:**
- Find row where project_type matches {{projectTypeFromStep02}}

**Return format:**
Return ONLY the matching row as a YAML-formatted object with these fields:
project_type, key_questions, required_sections, skip_sections, innovation_signals

**Do NOT return the entire CSV - only the matching row.**"

**Graceful degradation (if Task tool unavailable):**
- Load the CSV file directly
- Find the matching row manually
- Extract required fields:
  - `key_questions` (semicolon-separated list of discovery questions)
  - `required_sections` (semicolon-separated list of sections to document)
  - `skip_sections` (semicolon-separated list of sections to skip)
  - `innovation_signals` (already explored in step-6)

### 2. Conduct Guided Discovery Using Key Questions

Parse `key_questions` from CSV and explore each:

#### Question-Based Discovery:

For each question in `key_questions` from CSV:

- Ask the user naturally in conversational style
- Listen for their response and ask clarifying follow-ups
- Connect answers to product value proposition

**Example Flow:**
If key_questions = "Endpoints needed?;Authentication method?;Data formats?;Rate limits?;Versioning?;SDK needed?"

Ask naturally:

- "What are the main endpoints your API needs to expose?"
- "How will you handle authentication and authorization?"
- "What data formats will you support for requests and responses?"

### 3. Document Project-Type Specific Requirements

Based on user answers to key_questions, synthesize comprehensive requirements:

#### Requirement Categories:

Cover the areas indicated by `required_sections` from CSV:

- Synthesize what was discovered for each required section
- Document specific requirements, constraints, and decisions
- Connect to product differentiator when relevant

#### Skip Irrelevant Sections:

Skip areas indicated by `skip_sections` from CSV to avoid wasting time on irrelevant aspects.

### 4. Generate Dynamic Content Sections

Parse `required_sections` list from the matched CSV row. For each section name, generate corresponding content:

#### Common CSV Section Mappings:

- "endpoint_specs" or "endpoint_specification" → API endpoints documentation
- "auth_model" or "authentication_model" → Authentication approach
- "platform_reqs" or "platform_requirements" → Platform support needs
- "device_permissions" or "device_features" → Device capabilities
- "tenant_model" → Multi-tenancy approach
- "rbac_matrix" or "permission_matrix" → Permission structure

#### Template Variable Strategy:

- For sections matching common template variables: generate specific content
- For sections without template matches: include in main project_type_requirements
- Hybrid approach balances template structure with CSV-driven flexibility

### 5. Generate Project-Type Content

Prepare the content to append to the document:

#### Content Structure:

When saving to document, append these Level 2 and Level 3 sections:

```markdown
## [Project Type] Specific Requirements

### Project-Type Overview

[Project type summary based on conversation]

### Technical Architecture Considerations

[Technical architecture requirements based on conversation]

[Dynamic sections based on CSV and conversation]

### Implementation Considerations

[Implementation specific requirements based on conversation]
```

## SUCCESS METRICS:

✅ Project-type configuration loaded and used effectively
✅ All key questions from CSV explored with user input
✅ Required sections generated per CSV configuration
✅ Skip sections properly avoided to save time
✅ Technical requirements connected to product value
✅ switch prompt presented and handled correctly
✅ Content properly appended to document when user confirms via the switch prompt

## FAILURE MODES:

❌ Not loading or using project-type CSV configuration
❌ Missing key questions from CSV in discovery process
❌ Not generating required sections per CSV configuration
❌ Documenting sections that should be skipped per CSV
❌ Creating generic content without project-type specificity
❌ Not presenting switch prompt after content generation
❌ Appending content without user confirming via the switch prompt

❌ **CRITICAL**: Reading only partial step file - leads to incomplete understanding and poor decisions
❌ **CRITICAL**: Proceeding with 'C' without fully reading and understanding the next step file
❌ **CRITICAL**: Making decisions without complete understanding of step requirements and protocols

## PROJECT-TYPE EXAMPLES:

**For api_backend:**

- Focus on endpoints, authentication, data schemas, rate limiting
- Skip visual design and user journey sections
- Generate API specification documentation

**For mobile_app:**

- Focus on platform requirements, device permissions, offline mode
- Skip API endpoint documentation unless needed
- Generate mobile-specific technical requirements

**For saas_b2b:**

- Focus on multi-tenancy, permissions, integrations
- Skip mobile-first considerations unless relevant
- Generate enterprise-specific requirements

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode
  </case>
  <case value="continue-to-scoping" next="step-08-scoping">
    Continue to Scoping (Step 8 of 11)
  </case>
</switch>
