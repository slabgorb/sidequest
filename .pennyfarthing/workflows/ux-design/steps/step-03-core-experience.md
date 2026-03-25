# Step 3: Core Experience Definition

<purpose>Define the core user experience, platform requirements, and what makes interactions effortless through collaborative discovery of the primary user action and critical success moments.</purpose>

<instructions>Identify the ONE core user action. Explore platform requirements (web, mobile, desktop). Identify effortless interactions and critical success moments. Synthesize experience principles. Generate core experience content with defining experience, platform strategy, effortless interactions, critical success moments, and experience principles sections. Present the switch prompt. Save when user selects C.</instructions>

<output>Core user experience content appended to specification including platform strategy and guiding experience principles, with user confirmation and frontmatter updated.</output>

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input

- 📖 CRITICAL: ALWAYS read the complete step file before taking any action - partial understanding leads to incomplete decisions
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read and understood before proceeding
- ✅ ALWAYS treat this as collaborative discovery between UX facilitator and stakeholder
- 📋 YOU ARE A UX FACILITATOR, not a content generator
- 💬 FOCUS on defining the core user experience and platform
- 🎯 COLLABORATIVE discovery, not assumption-based design
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- ⚠️ Present the switch prompt after generating core experience content
- 💾 ONLY save when user confirms via the switch prompt
- 📖 Update output file frontmatter, adding this step to the end of the list of stepsCompleted.
- 🚫 FORBIDDEN to load next step until user confirms via the switch prompt

## PROTOCOL INTEGRATION:

- When 'A' selected: Execute {project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml
- When 'P' selected: Execute {project_root}/_bmad/core/workflows/party-mode/workflow.md
- PROTOCOLS always return to this step's switch prompt
- User accepts/rejects protocol changes before proceeding

## CONTEXT BOUNDARIES:

- Current document and frontmatter from previous steps are available
- Project understanding from step 2 informs this step
- No additional data files needed for this step
- Focus on core experience and platform decisions

## YOUR TASK:

Define the core user experience, platform requirements, and what makes the interaction effortless.

## CORE EXPERIENCE DISCOVERY SEQUENCE:

### 1. Define Core User Action

Start by identifying the most important user interaction:
"Now let's dig into the heart of the user experience for {{project_name}}.

**Core Experience Questions:**

- What's the ONE thing users will do most frequently?
- What user action is absolutely critical to get right?
- What should be completely effortless for users?
- If we nail one interaction, everything else follows - what is it?

Think about the core loop or primary action that defines your product's value."

### 2. Explore Platform Requirements

Determine where and how users will interact:
"Let's define the platform context for {{project_name}}:

**Platform Questions:**

- Web, mobile app, desktop, or multiple platforms?
- Will this be primarily touch-based or mouse/keyboard?
- Any specific platform requirements or constraints?
- Do we need to consider offline functionality?
- Any device-specific capabilities we should leverage?"

### 3. Identify Effortless Interactions

Surface what should feel magical or completely seamless:
"**Effortless Experience Design:**

- What user actions should feel completely natural and require zero thought?
- Where do users currently struggle with similar products?
- What interaction, if made effortless, would create delight?
- What should happen automatically without user intervention?
- Where can we eliminate steps that competitors require?"

### 4. Define Critical Success Moments

Identify the moments that determine success or failure:
"**Critical Success Moments:**

- What's the moment where users realize 'this is better'?
- When does the user feel successful or accomplished?
- What interaction, if failed, would ruin the experience?
- What are the make-or-break user flows?
- Where does first-time user success happen?"

### 5. Synthesize Experience Principles

Extract guiding principles from the conversation:
"Based on our discussion, I'm hearing these core experience principles for {{project_name}}:

**Experience Principles:**

- [Principle 1 based on core action focus]
- [Principle 2 based on effortless interactions]
- [Principle 3 based on platform considerations]
- [Principle 4 based on critical success moments]

These principles will guide all our UX decisions. Do these capture what's most important?"

### 6. Generate Core Experience Content

Prepare the content to append to the document:

#### Content Structure:

When saving to document, append these Level 2 and Level 3 sections:

```markdown
## Core User Experience

### Defining Experience

[Core experience definition based on conversation]

### Platform Strategy

[Platform requirements and decisions based on conversation]

### Effortless Interactions

[Effortless interaction areas identified based on conversation]

### Critical Success Moments

[Critical success moments defined based on conversation]

### Experience Principles

[Guiding principles for UX decisions based on conversation]
```

### 7. Present Content and Menu

Show the generated core experience content and present choices:
"I've defined the core user experience for {{project_name}} based on our conversation. This establishes the foundation for all our UX design decisions.

**Here's what I'll add to the document:**

[Show the complete markdown content from step 6]

**What would you like to do?**

### 8. Handle Menu Selection

#### If 'A' (Advanced Elicitation):

- Execute {project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml with the current core experience content
- Process the enhanced experience insights that come back
- Ask user: "Accept these improvements to the core experience definition? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'P' (Party Mode):

- Execute {project_root}/_bmad/core/workflows/party-mode/workflow.md with the current core experience definition
- Process the collaborative experience improvements that come back
- Ask user: "Accept these changes to the core experience definition? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'C' (Continue):

- Append the final content to `{planning_artifacts}/ux-design-specification.md`
- Update frontmatter: append step to end of stepsCompleted array
- Load `./step-04-emotional-response.md`

## SUCCESS METRICS:

✅ Core user action clearly identified and defined
✅ Platform requirements thoroughly explored
✅ Effortless interaction areas identified
✅ Critical success moments mapped out
✅ Experience principles established as guiding framework
✅ switch prompt presented and handled correctly
✅ Content properly appended to document when user confirms via the switch prompt

## FAILURE MODES:

❌ Missing the core user action that defines the product
❌ Not properly considering platform requirements
❌ Overlooking what should be effortless for users
❌ Not identifying critical make-or-break interactions
❌ Experience principles too generic or not actionable
❌ Not presenting switch prompt after content generation
❌ Appending content without user confirming via the switch prompt

❌ **CRITICAL**: Reading only partial step file - leads to incomplete understanding and poor decisions
❌ **CRITICAL**: Proceeding with 'C' without fully reading and understanding the next step file
❌ **CRITICAL**: Making decisions without complete understanding of step requirements and protocols

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Let's refine the core experience definition
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring different perspectives on the user experience
  </case>
  <case value="continue" next="step-04-emotional-response">
    Continue — Save this to the document and move to emotional response definition
  </case>
</switch>
