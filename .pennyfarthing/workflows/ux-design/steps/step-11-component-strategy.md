# Step 11: Component Strategy

<purpose>Define component library strategy and design custom components not covered by the chosen design system through collaborative analysis of component needs and implementation planning.</purpose>

<instructions>Analyze design system coverage (available vs needed). Design each custom component with purpose, content, actions, states, variants, and accessibility. Document component specifications. Define overall component strategy (foundation components, custom components, implementation approach). Plan implementation roadmap (phase 1 core, phase 2 supporting, phase 3 enhancement). Generate component strategy content with design system analysis, custom component specifications, implementation strategy, and roadmap sections. Present the switch prompt. Save when user confirms via the switch prompt.</instructions>

<output>Component strategy content appended to specification including custom component specifications with accessibility considerations, implementation roadmap prioritized by criticality, with user confirmation and frontmatter updated.</output>

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input

- 📖 CRITICAL: ALWAYS read the complete step file before taking any action - partial understanding leads to incomplete decisions
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read and understood before proceeding
- ✅ ALWAYS treat this as collaborative discovery between UX facilitator and stakeholder
- 📋 YOU ARE A UX FACILITATOR, not a content generator
- 💬 FOCUS on defining component library strategy and custom components
- 🎯 COLLABORATIVE component planning, not assumption-based design
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- ⚠️ Present the switch prompt after generating component strategy content
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
- Design system choice from step 6 determines available components
- User journeys from step 10 identify component needs
- Focus on defining custom components and implementation strategy

## YOUR TASK:

Define component library strategy and design custom components not covered by the design system.

## COMPONENT STRATEGY SEQUENCE:

### 1. Analyze Design System Coverage

Review what components are available vs. needed:
"Based on our chosen design system [design system from step 6], let's identify what components are already available and what we need to create custom.

**Available from Design System:**
[List of components available in chosen design system]

**Components Needed for {{project_name}}:**
Looking at our user journeys and design direction, we need:

- [Component need 1 from journey analysis]
- [Component need 2 from design requirements]
- [Component need 3 from core experience]

**Gap Analysis:**

- [Gap 1 - needed but not available]
- [Gap 2 - needed but not available]"

### 2. Design Custom Components

For each custom component needed, design thoroughly:

**For each custom component:**
"**[Component Name] Design:**

**Purpose:** What does this component do for users?
**Content:** What information or data does it display?
**Actions:** What can users do with this component?
**States:** What different states does it have? (default, hover, active, disabled, error, etc.)
**Variants:** Are there different sizes or styles needed?
**Accessibility:** What ARIA labels and keyboard support needed?

Let's walk through each custom component systematically."

### 3. Document Component Specifications

Create detailed specifications for each component:

**Component Specification Template:**

```markdown
### [Component Name]

**Purpose:** [Clear purpose statement]
**Usage:** [When and how to use]
**Anatomy:** [Visual breakdown of parts]
**States:** [All possible states with descriptions]
**Variants:** [Different sizes/styles if applicable]
**Accessibility:** [ARIA labels, keyboard navigation]
**Content Guidelines:** [What content works best]
**Interaction Behavior:** [How users interact]
```

### 4. Define Component Strategy

Establish overall component library approach:
"**Component Strategy:**

**Foundation Components:** (from design system)

- [Foundation component 1]
- [Foundation component 2]

**Custom Components:** (designed in this step)

- [Custom component 1 with rationale]
- [Custom component 2 with rationale]

**Implementation Approach:**

- Build custom components using design system tokens
- Ensure consistency with established patterns
- Follow accessibility best practices
- Create reusable patterns for common use cases"

### 5. Plan Implementation Roadmap

Define how and when to build components:
"**Implementation Roadmap:**

**Phase 1 - Core Components:**

- [Component 1] - needed for [critical flow]
- [Component 2] - needed for [critical flow]

**Phase 2 - Supporting Components:**

- [Component 3] - enhances [user experience]
- [Component 4] - supports [design pattern]

**Phase 3 - Enhancement Components:**

- [Component 5] - optimizes [user journey]
- [Component 6] - adds [special feature]

This roadmap helps prioritize development based on user journey criticality."

### 6. Generate Component Strategy Content

Prepare the content to append to the document:

#### Content Structure:

When saving to document, append these Level 2 and Level 3 sections:

```markdown
## Component Strategy

### Design System Components

[Analysis of available design system components based on conversation]

### Custom Components

[Custom component specifications based on conversation]

### Component Implementation Strategy

[Component implementation strategy based on conversation]

### Implementation Roadmap

[Implementation roadmap based on conversation]
```

### 7. Present Content and Menu

Show the generated component strategy content and present choices:
"I've defined the component strategy for {{project_name}}. This balances using proven design system components with custom components for your unique needs.

**Here's what I'll add to the document:**

[Show the complete markdown content from step 6]

**What would you like to do?**

### 8. Handle Menu Selection

#### If 'A' (Advanced Elicitation):

- Execute {project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml with the current component strategy content
- Process the enhanced component insights that come back
- Ask user: "Accept these improvements to the component strategy? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'P' (Party Mode):

- Execute {project_root}/_bmad/core/workflows/party-mode/workflow.md with the current component strategy
- Process the collaborative component insights that come back
- Ask user: "Accept these changes to the component strategy? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'C' (Continue):

- Append the final content to `{planning_artifacts}/ux-design-specification.md`
- Update frontmatter: append step to end of stepsCompleted array
- Load `./step-12-ux-patterns.md`

## SUCCESS METRICS:

✅ Design system coverage properly analyzed
✅ All custom components thoroughly specified
✅ Component strategy clearly defined
✅ Implementation roadmap prioritized by user need
✅ Accessibility considered for all components
✅ switch prompt presented and handled correctly
✅ Content properly appended to document when user confirms via the switch prompt

## FAILURE MODES:

❌ Not analyzing design system coverage properly
❌ Custom components not thoroughly specified
❌ Missing accessibility considerations
❌ Component strategy not aligned with user journeys
❌ Implementation roadmap not prioritized effectively
❌ Not presenting switch prompt after content generation
❌ Appending content without user confirming via the switch prompt

❌ **CRITICAL**: Reading only partial step file - leads to incomplete understanding and poor decisions
❌ **CRITICAL**: Proceeding with 'C' without fully reading and understanding the next step file
❌ **CRITICAL**: Making decisions without complete understanding of step requirements and protocols

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Let's refine our component strategy
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring technical perspectives on component design
  </case>
  <case value="continue" next="step-12-ux-patterns">
    Continue — Save this to the document and move to UX patterns
  </case>
</switch>
