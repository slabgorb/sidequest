# Step 7: Defining Core Experience

<purpose>Define the core interaction that, if nailed perfectly, makes everything else follow through collaborative exploration of user mental models, success criteria, and interaction mechanics.</purpose>

<instructions>Identify the defining experience (core action users describe to friends). Explore user mental model and current solutions. Define success criteria (when users say it just works). Identify novel vs established patterns. Design experience mechanics (initiation, interaction, feedback, completion). Generate defining experience content with experience description, mental model analysis, success criteria, novel patterns evaluation, and mechanics sections. Present the switch prompt. Save when user confirms via the switch prompt.</instructions>

<output>Defining experience content appended to specification including detailed experience mechanics and success criteria, with user confirmation and frontmatter updated.</output>

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input

- 📖 CRITICAL: ALWAYS read the complete step file before taking any action - partial understanding leads to incomplete decisions
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read and understood before proceeding
- ✅ ALWAYS treat this as collaborative discovery between UX facilitator and stakeholder
- 📋 YOU ARE A UX FACILITATOR, not a content generator
- 💬 FOCUS on defining the core interaction that defines the product
- 🎯 COLLABORATIVE discovery, not assumption-based design
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- ⚠️ Present the switch prompt after generating defining experience content
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
- Core experience from step 3 provides foundation
- Design system choice from step 6 informs implementation
- Focus on the defining interaction that makes the product special

## YOUR TASK:

Define the core interaction that, if nailed, makes everything else follow in the user experience.

## DEFINING EXPERIENCE SEQUENCE:

### 1. Identify the Defining Experience

Focus on the core interaction:
"Every successful product has a defining experience - the core interaction that, if we nail it, everything else follows.

**Think about these famous examples:**

- Tinder: "Swipe to match with people"
- Snapchat: "Share photos that disappear"
- Instagram: "Share perfect moments with filters"
- Spotify: "Discover and play any song instantly"

**For {{project_name}}:**
What's the core action that users will describe to their friends?
What's the interaction that makes users feel successful?
If we get ONE thing perfectly right, what should it be?"

### 2. Explore the User's Mental Model

Understand how users think about the core task:
"**User Mental Model Questions:**

- How do users currently solve this problem?
- What mental model do they bring to this task?
- What's their expectation for how this should work?
- Where are they likely to get confused or frustrated?

**Current Solutions:**

- What do users love/hate about existing approaches?
- What shortcuts or workarounds do they use?
- What makes existing solutions feel magical or terrible?"

### 3. Define Success Criteria for Core Experience

Establish what makes the core interaction successful:
"**Core Experience Success Criteria:**

- What makes users say 'this just works'?
- When do they feel smart or accomplished?
- What feedback tells them they're doing it right?
- How fast should it feel?
- What should happen automatically?

**Success Indicators:**

- [Success indicator 1]
- [Success indicator 2]
- [Success indicator 3]"

### 4. Identify Novel vs. Established Patterns

Determine if we need to innovate or can use proven patterns:
"**Pattern Analysis:**
Looking at your core experience, does this:

- Use established UX patterns that users already understand?
- Require novel interaction design that needs user education?
- Combine familiar patterns in innovative ways?

**If Novel:**

- What makes this different from existing approaches?
- How will we teach users this new pattern?
- What familiar metaphors can we use?

**If Established:**

- Which proven patterns should we adopt?
- How can we innovate within familiar patterns?
- What's our unique twist on established interactions?"

### 5. Define Experience Mechanics

Break down the core interaction into details:
"**Core Experience Mechanics:**
Let's design the step-by-step flow for [defining experience]:

**1. Initiation:**

- How does the user start this action?
- What triggers or invites them to begin?

**2. Interaction:**

- What does the user actually do?
- What controls or inputs do they use?
- How does the system respond?

**3. Feedback:**

- What tells users they're succeeding?
- How do they know when it's working?
- What happens if they make a mistake?

**4. Completion:**

- How do users know they're done?
- What's the successful outcome?
- What's next?"

### 6. Generate Defining Experience Content

Prepare the content to append to the document:

#### Content Structure:

When saving to document, append these Level 2 and Level 3 sections:

```markdown
## 2. Core User Experience

### 2.1 Defining Experience

[Defining experience description based on conversation]

### 2.2 User Mental Model

[User mental model analysis based on conversation]

### 2.3 Success Criteria

[Success criteria for core experience based on conversation]

### 2.4 Novel UX Patterns

[Novel UX patterns analysis based on conversation]

### 2.5 Experience Mechanics

[Detailed mechanics for core experience based on conversation]
```

### 7. Present Content and Menu

Show the generated defining experience content and present choices:
"I've defined the core experience for {{project_name}} - the interaction that will make users love this product.

**Here's what I'll add to the document:**

[Show the complete markdown content from step 6]

**What would you like to do?**

### 8. Handle Menu Selection

#### If 'A' (Advanced Elicitation):

- Execute {project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml with the current defining experience content
- Process the enhanced experience insights that come back
- Ask user: "Accept these improvements to the defining experience? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'P' (Party Mode):

- Execute {project_root}/_bmad/core/workflows/party-mode/workflow.md with the current defining experience
- Process the collaborative experience insights that come back
- Ask user: "Accept these changes to the defining experience? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'C' (Continue):

- Append the final content to `{planning_artifacts}/ux-design-specification.md`
- Update frontmatter: append step to end of stepsCompleted array
- Load `./step-08-visual-foundation.md`

## SUCCESS METRICS:

✅ Defining experience clearly articulated
✅ User mental model thoroughly analyzed
✅ Success criteria established for core interaction
✅ Novel vs. established patterns properly evaluated
✅ Experience mechanics designed in detail
✅ switch prompt presented and handled correctly
✅ Content properly appended to document when user confirms via the switch prompt

## FAILURE MODES:

❌ Not identifying the true core interaction
❌ Missing user's mental model and expectations
❌ Not establishing clear success criteria
❌ Not properly evaluating novel vs. established patterns
❌ Experience mechanics too vague or incomplete
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
    Party Mode — Bring different perspectives on the defining interaction
  </case>
  <case value="continue" next="step-08-visual-foundation">
    Continue — Save this to the document and move to visual foundation
  </case>
</switch>
