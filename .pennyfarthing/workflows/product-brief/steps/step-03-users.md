---
name: 'step-03-users'
description: 'Define target users with rich personas and map their key interactions with the product'

# File References
nextStepFile: './step-04-metrics.md'
outputFile: '{planning_artifacts}/product-brief-{{project_name}}-{{date}}.md'

# Task References
advancedElicitationTask: '{project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{project_root}/_bmad/core/workflows/party-mode/workflow.md'
---

<purpose>
Define target users with rich personas and map their key interactions with the product through collaborative user research and journey mapping.
</purpose>

<instructions>
1. Begin user discovery conversation identifying who experiences the problem
2. Develop rich personas for primary user segments
3. Explore secondary user segments and their roles
4. Map user journeys through discovery, onboarding, core usage, and success moments
5. Generate Target Users content with personas and journey maps
6. Present the switch prompt for optional advanced elicitation or party mode
7. Save content to document when user selects C
</instructions>

<output>
- Target Users section with Primary and Secondary user personas
- User Journey section mapping key interaction points
- Rich persona descriptions with motivations and goals
- Document updated at {outputFile} with stepsCompleted: [1, 2, 3]
- User ready to proceed to success metrics definition
</output>

# Step 3: Target Users Discovery

## STEP GOAL:

Define target users with rich personas and map their key interactions with the product through collaborative user research and journey mapping.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

### Role Reinforcement:

- ✅ You are a product-focused Business Analyst facilitator
- ✅ If you already have been given a name, communication_style and persona, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring structured thinking and facilitation skills, while the user brings domain expertise and product vision
- ✅ Maintain collaborative discovery tone throughout

### Step-Specific Rules:

- 🎯 Focus only on defining who this product serves and how they interact with it
- 🚫 FORBIDDEN to create generic user profiles without specific details
- 💬 Approach: Systematic persona development with journey mapping
- 📋 COLLABORATIVE persona development, not assumption-based user creation

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- 💾 Generate user personas and journeys collaboratively with user
- 📖 Update frontmatter `stepsCompleted: [1, 2, 3]` before loading next step
- 🚫 FORBIDDEN to proceed without user confirmation through menu

## CONTEXT BOUNDARIES:

- Available context: Current document and frontmatter from previous steps, product vision and problem already defined
- Focus: Creating vivid, actionable user personas that align with product vision
- Limits: Focus on users who directly experience the problem or benefit from the solution
- Dependencies: Product vision and problem statement from step-02 must be complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Begin User Discovery

**Opening Exploration:**
"Now that we understand what {{project_name}} does, let's define who it's for.

**User Discovery:**

- Who experiences the problem we're solving?
- Are there different types of users with different needs?
- Who gets the most value from this solution?
- Are there primary users and secondary users we should consider?

Let's start by identifying the main user groups."

### 2. Primary User Segment Development

**Persona Development Process:**
For each primary user segment, create rich personas:

**Name & Context:**

- Give them a realistic name and brief backstory
- Define their role, environment, and context
- What motivates them? What are their goals?

**Problem Experience:**

- How do they currently experience the problem?
- What workarounds are they using?
- What are the emotional and practical impacts?

**Success Vision:**

- What would success look like for them?
- What would make them say "this is exactly what I needed"?

**Primary User Questions:**

- "Tell me about a typical person who would use {{project_name}}"
- "What's their day like? Where does our product fit in?"
- "What are they trying to accomplish that's hard right now?"

### 3. Secondary User Segment Exploration

**Secondary User Considerations:**

- "Who else benefits from this solution, even if they're not the primary user?"
- "Are there admin, support, or oversight roles we should consider?"
- "Who influences the decision to adopt or purchase this product?"
- "Are there partner or stakeholder users who matter?"

### 4. User Journey Mapping

**Journey Elements:**
Map key interactions for each user segment:

- **Discovery:** How do they find out about the solution?
- **Onboarding:** What's their first experience like?
- **Core Usage:** How do they use the product day-to-day?
- **Success Moment:** When do they realize the value?
- **Long-term:** How does it become part of their routine?

**Journey Questions:**

- "Walk me through how [Persona Name] would discover and start using {{project_name}}"
- "What's their 'aha!' moment?"
- "How does this product change how they work or live?"

### 5. Generate Target Users Content

**Content to Append:**
Prepare the following structure for document append:

```markdown
## Target Users

### Primary Users

[Primary user segment content based on conversation]

### Secondary Users

[Secondary user segment content based on conversation, or N/A if not discussed]

### User Journey

[User journey content based on conversation, or N/A if not discussed]
```

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [C continue option] is selected and [user personas finalized and saved to document with frontmatter updated], will you then load and read fully `{nextStepFile}` to execute and begin success metrics definition.

---


<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode
  </case>
  <case value="continue" next="step-04-metrics">
    Continue
  </case>
</switch>

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Rich, believable user personas with clear motivations
- Clear distinction between primary and secondary users
- User journeys that show key interaction points and value creation
- User segments that align with product vision and problem statement
- switch prompt presented and handled correctly with proper task execution
- Content properly appended to document when user confirms via the switch prompt
- Frontmatter updated with stepsCompleted: [1, 2, 3]

### ❌ SYSTEM FAILURE:

- Creating generic user profiles without specific details
- Missing key user segments that are important to success
- User journeys that don't show how the product creates value
- Not connecting user needs back to the problem statement
- Not presenting standard switch prompt after content generation
- Appending content without user confirming via the switch prompt
- Not updating frontmatter properly

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
