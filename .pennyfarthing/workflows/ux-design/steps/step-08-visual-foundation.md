# Step 8: Visual Foundation

<purpose>Establish visual design foundation including color themes, typography systems, and spacing/layout foundations through collaborative exploration of brand guidelines and design principles.</purpose>

<instructions>Assess brand guidelines. If no brand exists, generate color theme options and HTML visualizer. Define typography system (tone, readability, hierarchy). Establish spacing and layout foundation (density, grid system). Create visual foundation strategy with color system, typography, spacing, and accessibility sections. Generate visual foundation content. Present the switch prompt. Save when user confirms via the switch prompt.</instructions>

<output>Visual design foundation content appended to specification including color system, typography system, spacing/layout foundation, and accessibility considerations, with user confirmation and frontmatter updated.</output>

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input

- 📖 CRITICAL: ALWAYS read the complete step file before taking any action - partial understanding leads to incomplete decisions
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read and understood before proceeding
- ✅ ALWAYS treat this as collaborative discovery between UX facilitator and stakeholder
- 📋 YOU ARE A UX FACILITATOR, not a content generator
- 💬 FOCUS on establishing visual design foundation (colors, typography, spacing)
- 🎯 COLLABORATIVE discovery, not assumption-based design
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- ⚠️ Present the switch prompt after generating visual foundation content
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
- Design system choice from step 6 provides component foundation
- Emotional response goals from step 4 inform visual decisions
- Focus on colors, typography, spacing, and layout foundation

## YOUR TASK:

Establish the visual design foundation including color themes, typography, and spacing systems.

## VISUAL FOUNDATION SEQUENCE:

### 1. Brand Guidelines Assessment

Check for existing brand requirements:
"Do you have existing brand guidelines or a specific color palette I should follow? (y/n)

If yes, I'll extract and document your brand colors and create semantic color mappings.
If no, I'll generate theme options based on your project's personality and emotional goals from our earlier discussion."

### 2. Generate Color Theme Options (If no brand guidelines)

Create visual exploration opportunities:
"If no existing brand guidelines, I'll create a color theme visualizer to help you explore options.

🎨 I can generate comprehensive HTML color theme visualizers with multiple theme options, complete UI examples, and the ability to see how colors work in real interface contexts.

This will help you make an informed decision about the visual direction for {{project_name}}."

### 3. Define Typography System

Establish the typographic foundation:
"**Typography Questions:**

- What should the overall tone feel like? (Professional, friendly, modern, classic?)
- How much text content will users read? (Headings only? Long-form content?)
- Any accessibility requirements for font sizes or contrast?
- Any brand fonts we must use?

**Typography Strategy:**

- Choose primary and secondary typefaces
- Establish type scale (h1, h2, h3, body, etc.)
- Define line heights and spacing relationships
- Consider readability and accessibility"

### 4. Establish Spacing and Layout Foundation

Define the structural foundation:
"**Spacing and Layout Foundation:**

- How should the overall layout feel? (Dense and efficient? Airy and spacious?)
- What spacing unit should we use? (4px, 8px, 12px base?)
- How much white space should be between elements?
- Should we use a grid system? If so, what column structure?

**Layout Principles:**

- [Layout principle 1 based on product type]
- [Layout principle 2 based on user needs]
- [Layout principle 3 based on platform requirements]"

### 5. Create Visual Foundation Strategy

Synthesize all visual decisions:
"**Visual Foundation Strategy:**

**Color System:**

- [Color strategy based on brand guidelines or generated themes]
- Semantic color mapping (primary, secondary, success, warning, error, etc.)
- Accessibility compliance (contrast ratios)

**Typography System:**

- [Typography strategy based on content needs and tone]
- Type scale and hierarchy
- Font pairing rationale

**Spacing & Layout:**

- [Spacing strategy based on content density and platform]
- Grid system approach
- Component spacing relationships

This foundation will ensure consistency across all our design decisions."

### 6. Generate Visual Foundation Content

Prepare the content to append to the document:

#### Content Structure:

When saving to document, append these Level 2 and Level 3 sections:

```markdown
## Visual Design Foundation

### Color System

[Color system strategy based on conversation]

### Typography System

[Typography system strategy based on conversation]

### Spacing & Layout Foundation

[Spacing and layout foundation based on conversation]

### Accessibility Considerations

[Accessibility considerations based on conversation]
```

### 7. Present Content and Menu

Show the generated visual foundation content and present choices:
"I've established the visual design foundation for {{project_name}}. This provides the building blocks for consistent, beautiful design.

**Here's what I'll add to the document:**

[Show the complete markdown content from step 6]

**What would you like to do?**

### 8. Handle Menu Selection

#### If 'A' (Advanced Elicitation):

- Execute {project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml with the current visual foundation content
- Process the enhanced visual insights that come back
- Ask user: "Accept these improvements to the visual foundation? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'P' (Party Mode):

- Execute {project_root}/_bmad/core/workflows/party-mode/workflow.md with the current visual foundation
- Process the collaborative visual insights that come back
- Ask user: "Accept these changes to the visual foundation? (y/n)"
- If yes: Update content with improvements, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'C' (Continue):

- Append the final content to `{planning_artifacts}/ux-design-specification.md`
- Update frontmatter: append step to end of stepsCompleted array
- Load `./step-09-design-directions.md`

## SUCCESS METRICS:

✅ Brand guidelines assessed and incorporated if available
✅ Color system established with accessibility consideration
✅ Typography system defined with appropriate hierarchy
✅ Spacing and layout foundation created
✅ Visual foundation strategy documented
✅ switch prompt presented and handled correctly
✅ Content properly appended to document when user confirms via the switch prompt

## FAILURE MODES:

❌ Not checking for existing brand guidelines first
❌ Color palette not aligned with emotional goals
❌ Typography not suitable for content type or readability needs
❌ Spacing system not appropriate for content density
❌ Missing accessibility considerations
❌ Not presenting switch prompt after content generation
❌ Appending content without user confirming via the switch prompt

❌ **CRITICAL**: Reading only partial step file - leads to incomplete understanding and poor decisions
❌ **CRITICAL**: Proceeding with 'C' without fully reading and understanding the next step file
❌ **CRITICAL**: Making decisions without complete understanding of step requirements and protocols

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Let's refine our visual foundation
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Bring design perspectives on visual choices
  </case>
  <case value="continue" next="step-09-design-directions">
    Continue — Save this to the document and move to design directions
  </case>
</switch>
