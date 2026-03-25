# Step 6: Design System Choice

<purpose>Choose appropriate design system approach (custom, established, or themeable) based on project requirements, constraints, and team considerations through collaborative decision-making.</purpose>

<instructions>Present design system options (custom, established, themeable). Analyze project requirements (platform, timeline, team size, brand, technical constraints). Explore specific design system options recommended for the platform. Facilitate decision process through framework questions. Finalize choice with clear rationale. Generate design system content with choice, rationale, implementation approach, and customization strategy sections. Present the switch prompt. Save when user confirms via the switch prompt.</instructions>

<output>Design system choice content appended to specification including rationale and implementation approach, with user confirmation and frontmatter updated.</output>

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input

- 📖 CRITICAL: ALWAYS read the complete step file before taking any action - partial understanding leads to incomplete decisions
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read and understood before proceeding
- ✅ ALWAYS treat this as collaborative discovery between UX facilitator and stakeholder
- 📋 YOU ARE A UX FACILITATOR, not a content generator
- 💬 FOCUS on choosing appropriate design system approach
- 🎯 COLLABORATIVE decision-making, not recommendation-only
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- ⚠️ Present the switch prompt after generating design system decision content
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
- Platform requirements from step 3 inform design system choice
- Inspiration patterns from step 5 guide design system selection
- Focus on choosing foundation for consistent design

## YOUR TASK:

Choose appropriate design system approach based on project requirements and constraints.

## DESIGN SYSTEM CHOICE SEQUENCE:

### 1. Present Design System Options

Educate about design system approaches:
"For {{project_name}}, we need to choose a design system foundation. Think of design systems like LEGO blocks for UI - they provide proven components and patterns, ensuring consistency and speeding development.

**Design System Approaches:**

**1. Custom Design System**

- Complete visual uniqueness
- Full control over every component
- Higher initial investment
- Perfect for established brands with unique needs

**2. Established System (Material Design, Ant Design, etc.)**

- Fast development with proven patterns
- Great defaults and accessibility built-in
- Less visual differentiation
- Ideal for startups or internal tools

**3. Themeable System (MUI, Chakra UI, Tailwind UI)**

- Customizable with strong foundation
- Brand flexibility with proven components
- Moderate learning curve
- Good balance of speed and uniqueness

Which direction feels right for your project?"

### 2. Analyze Project Requirements

Guide decision based on project context:
"**Let's consider your specific needs:**

**Based on our previous conversations:**

- Platform: [platform from step 3]
- Timeline: [inferred from user conversation]
- Team Size: [inferred from user conversation]
- Brand Requirements: [inferred from user conversation]
- Technical Constraints: [inferred from user conversation]

**Decision Factors:**

- Need for speed vs. need for uniqueness
- Brand guidelines or existing visual identity
- Team's design expertise
- Long-term maintenance considerations
- Integration requirements with existing systems"

### 3. Explore Specific Design System Options

Dive deeper into relevant options:
"**Recommended Options Based on Your Needs:**

**For [Your Platform Type]:**

- [Option 1] - [Key benefit] - [Best for scenario]
- [Option 2] - [Key benefit] - [Best for scenario]
- [Option 3] - [Key benefit] - [Best for scenario]

**Considerations:**

- Component library size and quality
- Documentation and community support
- Customization capabilities
- Accessibility compliance
- Performance characteristics
- Learning curve for your team"

### 4. Facilitate Decision Process

Help user make informed choice:
"**Decision Framework:**

1. What's most important: Speed, uniqueness, or balance?
2. How much design expertise does your team have?
3. Are there existing brand guidelines to follow?
4. What's your timeline and budget?
5. Long-term maintenance needs?

Let's evaluate options based on your answers to these questions."

### 5. Finalize Design System Choice

Confirm and document the decision:
"Based on our analysis, I recommend [Design System Choice] for {{project_name}}.

**Rationale:**

- [Reason 1 based on project needs]
- [Reason 2 based on constraints]
- [Reason 3 based on team considerations]

**Next Steps:**

- We'll customize this system to match your brand and needs
- Define component strategy for custom components needed
- Establish design tokens and patterns

Does this design system choice feel right to you?"

### 6. Generate Design System Content

Prepare the content to append to the document:

#### Content Structure:

When saving to document, append these Level 2 and Level 3 sections:

```markdown
## Design System Foundation

### 1.1 Design System Choice

[Design system choice based on conversation]

### Rationale for Selection

[Rationale for design system selection based on conversation]

### Implementation Approach

[Implementation approach based on chosen system]

### Customization Strategy

[Customization strategy based on project needs]
```

### 7. Present Content and Menu

Show the generated design system content and present choices:
"I've documented our design system choice for {{project_name}}. This foundation will ensure consistency and speed up development.

**Here's what I'll add to the document:**

[Show the complete markdown content from step 6]

**What would you like to do?**

### 8. Handle Menu Selection

#### If 'A' (Advanced Elicitation):

- Execute {project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml with the current design system content
- Process the enhanced design system insights that come back
- Ask user: "Accept these improvements to the design system decision? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'P' (Party Mode):

- Execute {project_root}/_bmad/core/workflows/party-mode/workflow.md with the current design system choice
- Process the collaborative design system insights that come back
- Ask user: "Accept these changes to the design system decision? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'C' (Continue):

- Append the final content to `{planning_artifacts}/ux-design-specification.md`
- Update frontmatter: append step to end of stepsCompleted array
- Load `./step-07-defining-experience.md`

## SUCCESS METRICS:

✅ Design system options clearly presented and explained
✅ Decision framework applied to project requirements
✅ Specific design system chosen with clear rationale
✅ Implementation approach planned
✅ Customization strategy defined
✅ switch prompt presented and handled correctly
✅ Content properly appended to document when user confirms via the switch prompt

## FAILURE MODES:

❌ Not explaining design system concepts clearly
❌ Rushing to recommendation without understanding requirements
❌ Not considering technical constraints or team capabilities
❌ Choosing design system without clear rationale
❌ Not planning implementation approach
❌ Not presenting switch prompt after content generation
❌ Appending content without user confirming via the switch prompt

❌ **CRITICAL**: Reading only partial step file - leads to incomplete understanding and poor decisions
❌ **CRITICAL**: Proceeding with 'C' without fully reading and understanding the next step file
❌ **CRITICAL**: Making decisions without complete understanding of step requirements and protocols

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Let's refine our design system decision
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring technical perspectives on design systems
  </case>
  <case value="continue" next="step-07-defining-experience">
    Continue — Save this to the document and move to defining experience
  </case>
</switch>
