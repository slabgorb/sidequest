---
name: 'step-04-journeys'
description: 'Map ALL user types that interact with the system with narrative story-based journeys'

# File References
nextStepFile: './step-05-domain.md'
outputFile: '{planning_artifacts}/prd.md'

# Task References
advancedElicitationTask: '{project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{project_root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 4: User Journey Mapping

<purpose>Map all user types that interact with the system with narrative story-based journeys that capture interactions, touchpoints, and emotional states.</purpose>

<instructions>Identify all user personas and archetypes; for each user type, collaboratively craft narrative journey stories; capture decision points, pain points, and desired outcomes; ensure journey completeness from initial interaction through goal completion; save journeys to document.</instructions>

<output>Comprehensive user journey narratives for all identified user types, each with clear story flow, decision points, pain points, and desired outcomes documented in the PRD.</output>

**Progress: Step 4 of 11** - Next: Domain Requirements

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input

- 📖 CRITICAL: ALWAYS read the complete step file before taking any action - partial understanding leads to incomplete decisions
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read and understood before proceeding
- ✅ ALWAYS treat this as collaborative discovery between PM peers
- 📋 YOU ARE A FACILITATOR, not a content generator
- 💬 FOCUS on mapping ALL user types that interact with the system
- 🎯 CRITICAL: No journey = no functional requirements = product doesn't exist
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- ⚠️ Present the switch prompt after generating journey content
- 💾 ONLY save when user confirms via the switch prompt
- 📖 Update output file frontmatter, adding this step name to the end of the list of stepsCompleted
- 🚫 FORBIDDEN to load next step until user confirms via the switch prompt

## CONTEXT BOUNDARIES:

- Current document and frontmatter from previous steps are available
- Success criteria and scope already defined
- Input documents from step-01 are available (product briefs with user personas)
- Every human interaction with the system needs a journey

## YOUR TASK:

Create compelling narrative user journeys that leverage existing personas from product briefs and identify additional user types needed for comprehensive coverage.

## JOURNEY MAPPING SEQUENCE:

### 1. Leverage Existing Users & Identify Additional Types

**Check Input Documents for Existing Personas:**
Analyze product brief, research, and brainstorming documents for user personas already defined.

**If User Personas Exist in Input Documents:**
Guide user to build on existing personas:
- Acknowledge personas found in their product brief
- Extract key persona details and backstories
- Leverage existing insights about their needs
- Prompt to identify additional user types beyond those documented
- Suggest additional user types based on product context (admins, moderators, support, API consumers, internal ops)
- Ask what additional user types should be considered

**If No Personas in Input Documents:**
Start with comprehensive user type discovery:
- Guide exploration of ALL people who interact with the system
- Consider beyond primary users: admins, moderators, support staff, API consumers, internal ops
- Ask what user types should be mapped for this specific product
- Ensure comprehensive coverage of all system interactions

### 2. Create Narrative Story-Based Journeys

For each user type, create compelling narrative journeys that tell their story:

#### Narrative Journey Creation Process:

**If Using Existing Persona from Input Documents:**
Guide narrative journey creation:
- Use persona's existing backstory from brief
- Explore how the product changes their life/situation
- Craft journey narrative: where do we meet them, how does product help them write their next chapter?

**If Creating New Persona:**
Guide persona creation with story framework:
- Name: realistic name and personality
- Situation: What's happening in their life/work that creates need?
- Goal: What do they desperately want to achieve?
- Obstacle: What's standing in their way?
- Solution: How does the product solve their story?

**Story-Based Journey Mapping:**

Guide narrative journey creation using story structure:
- **Opening Scene**: Where/how do we meet them? What's their current pain?
- **Rising Action**: What steps do they take? What do they discover?
- **Climax**: Critical moment where product delivers real value
- **Resolution**: How does their situation improve? What's their new reality?

Encourage narrative format with specific user details, emotional journey, and clear before/after contrast

### 3. Guide Journey Exploration

For each journey, facilitate detailed exploration:
- What happens at each step specifically?
- What could go wrong? What's the recovery path?
- What information do they need to see/hear?
- What's their emotional state at each point?
- Where does this journey succeed or fail?

### 4. Connect Journeys to Requirements

After each journey, explicitly state:
- This journey reveals requirements for specific capability areas
- Help user see how different journeys create different feature sets
- Connect journey needs to concrete capabilities (onboarding, dashboards, notifications, etc.)

### 5. Aim for Comprehensive Coverage

Guide toward complete journey set:

- **Primary user** - happy path (core experience)
- **Primary user** - edge case (different goal, error recovery)
- **Secondary user** (admin, moderator, support, etc.)
- **API consumer** (if applicable)

Ask if additional journeys are needed to cover uncovered user types

### 6. Generate User Journey Content

Prepare the content to append to the document:

#### Content Structure:

When saving to document, append these Level 2 and Level 3 sections:

```markdown
## User Journeys

[All journey narratives based on conversation]

### Journey Requirements Summary

[Summary of capabilities revealed by journeys based on conversation]
```

## SUCCESS METRICS:

✅ Existing personas from product briefs leveraged when available
✅ All user types identified (not just primary users)
✅ Rich narrative storytelling for each persona and journey
✅ Complete story-based journey mapping with emotional arc
✅ Journey requirements clearly connected to capabilities needed
✅ Minimum 3-4 compelling narrative journeys covering different user types
✅ switch prompt presented and handled correctly
✅ Content properly appended to document when user confirms via the switch prompt

## FAILURE MODES:

❌ Ignoring existing personas from product briefs
❌ Only mapping primary user journeys and missing secondary users
❌ Creating generic journeys without rich persona details and narrative
❌ Missing emotional storytelling elements that make journeys compelling
❌ Missing critical decision points and failure scenarios
❌ Not connecting journeys to required capabilities
❌ Not having enough journey diversity (admin, support, API, etc.)
❌ Not presenting switch prompt after content generation
❌ Appending content without user confirming via the switch prompt

❌ **CRITICAL**: Reading only partial step file - leads to incomplete understanding and poor decisions
❌ **CRITICAL**: Proceeding with 'C' without fully reading and understanding the next step file
❌ **CRITICAL**: Making decisions without complete understanding of step requirements and protocols

## JOURNEY TYPES TO ENSURE:

**Minimum Coverage:**

1. **Primary User - Success Path**: Core experience journey
2. **Primary User - Edge Case**: Error recovery, alternative goals
3. **Admin/Operations User**: Management, configuration, monitoring
4. **Support/Troubleshooting**: Help, investigation, issue resolution
5. **API/Integration** (if applicable): Developer/technical user journey

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode
  </case>
  <case value="continue-to-domain-requirements" next="step-05-domain">
    Continue to Domain Requirements (Step 5 of 11)
  </case>
</switch>
