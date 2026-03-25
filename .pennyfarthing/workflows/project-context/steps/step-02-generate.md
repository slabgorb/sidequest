# Step 2: Context Rules Generation

<purpose>
Collaboratively generate specific, critical rules that AI agents must follow when implementing code in this project, organized by technology stack, language, framework, testing, code quality, workflow, and anti-patterns.
</purpose>

<instructions>
1. Document exact technology stack and versions from discovery
2. Generate language-specific rules for unobvious patterns
3. Generate framework-specific rules for project conventions
4. Generate testing rules for consistency
5. Generate code quality and style rules
6. Generate development workflow rules
7. Identify critical don't-miss rules and anti-patterns
8. Present the switch prompt after each category for user validation
9. Append validated rules to project context file
10. Update frontmatter with completed sections
</instructions>

<output>
- Technology stack and versions documented
- Language-specific rules for each category
- Framework-specific rules for project patterns
- Testing rules for consistency
- Code quality and style rules
- Development workflow rules
- Critical anti-pattern rules documented
- switch prompt selections processed
- Rules appended to project context file
- Frontmatter updated with sections_completed
- Ready to proceed to step-03
</output>

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input
- ✅ ALWAYS treat this as collaborative discovery between technical peers
- 📋 YOU ARE A FACILITATOR, not a content generator
- 💬 FOCUS on unobvious rules that AI agents need to be reminded of
- 🎯 KEEP CONTENT LEAN - optimize for LLM context efficiency
- ⚠️ ABSOLUTELY NO TIME ESTIMATES - AI development speed has fundamentally changed
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- 📝 Focus on specific, actionable rules rather than general advice
- ⚠️ Present the switch prompt after each major rule category
- 💾 ONLY save when user confirms via the switch prompt
- 📖 Update frontmatter with completed sections
- 🚫 FORBIDDEN to load next step until all sections are complete

## PROTOCOL INTEGRATION:

- When 'A' selected: Execute {project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml
- When 'P' selected: Execute {project_root}/_bmad/core/workflows/party-mode
- PROTOCOLS always return to display this step's switch prompt after the A or P have completed
- User accepts/rejects protocol changes before proceeding

## CONTEXT BOUNDARIES:

- Discovery results from step-1 are available
- Technology stack and existing patterns are identified
- Focus on rules that prevent implementation mistakes
- Prioritize unobvious details that AI agents might miss

## YOUR TASK:

Collaboratively generate specific, critical rules that AI agents must follow when implementing code in this project.

## CONTEXT GENERATION SEQUENCE:

### 1. Technology Stack & Versions

Document the exact technology stack from discovery:

**Core Technologies:**
Based on user skill level, present findings:

**Expert Mode:**
"Technology stack from your architecture and package files:
{{exact_technologies_with_versions}}

Any critical version constraints I should document for agents?"

**Intermediate Mode:**
"I found your technology stack:

**Core Technologies:**
{{main_technologies_with_versions}}

**Key Dependencies:**
{{important_dependencies_with_versions}}

Are there any version constraints or compatibility notes agents should know about?"

**Beginner Mode:**
"Here are the technologies you're using:

**Main Technologies:**
{{friendly_description_of_tech_stack}}

**Important Notes:**
{{key_things_agents_need_to_know_about_versions}}

Should I document any special version rules or compatibility requirements?"

### 2. Language-Specific Rules

Focus on unobvious language patterns agents might miss:

**TypeScript/JavaScript Rules:**
"Based on your codebase, I notice some specific patterns:

**Configuration Requirements:**
{{typescript_config_rules}}

**Import/Export Patterns:**
{{import_export_conventions}}

**Error Handling Patterns:**
{{error_handling_requirements}}

Are these patterns correct? Any other language-specific rules agents should follow?"

**Python/Ruby/Other Language Rules:**
Adapt to the actual language in use with similar focused questions.

### 3. Framework-Specific Rules

Document framework-specific patterns:

**React Rules (if applicable):**
"For React development, I see these patterns:

**Hooks Usage:**
{{hooks_usage_patterns}}

**Component Structure:**
{{component_organization_rules}}

**State Management:**
{{state_management_patterns}}

**Performance Rules:**
{{performance_optimization_requirements}}

Should I add any other React-specific rules?"

**Other Framework Rules:**
Adapt for Vue, Angular, Next.js, Express, etc.

### 4. Testing Rules

Focus on testing patterns that ensure consistency:

**Test Structure Rules:**
"Your testing setup shows these patterns:

**Test Organization:**
{{test_file_organization}}

**Mock Usage:**
{{mock_patterns_and_conventions}}

**Test Coverage Requirements:**
{{coverage_expectations}}

**Integration vs Unit Test Rules:**
{{test_boundary_patterns}}

Are there testing rules agents should always follow?"

### 5. Code Quality & Style Rules

Document critical style and quality rules:

**Linting/Formatting:**
"Your code style configuration requires:

**ESLint/Prettier Rules:**
{{specific_linting_rules}}

**Code Organization:**
{{file_and_folder_structure_rules}}

**Naming Conventions:**
{{naming_patterns_agents_must_follow}}

**Documentation Requirements:**
{{comment_and_documentation_patterns}}

Any additional code quality rules?"

### 6. Development Workflow Rules

Document workflow patterns that affect implementation:

**Git/Repository Rules:**
"Your project uses these patterns:

**Branch Naming:**
{{branch_naming_conventions}}

**Commit Message Format:**
{{commit_message_patterns}}

**PR Requirements:**
{{pull_request_checklist}}

**Deployment Patterns:**
{{deployment_considerations}}

Should I document any other workflow rules?"

### 7. Critical Don't-Miss Rules

Identify rules that prevent common mistakes:

**Anti-Patterns to Avoid:**
"Based on your codebase, here are critical things agents must NOT do:

{{critical_anti_patterns_with_examples}}

**Edge Cases:**
{{specific_edge_cases_agents_should_handle}}

**Security Rules:**
{{security_considerations_agents_must_follow}}

**Performance Gotchas:**
{{performance_patterns_to_avoid}}

Are there other 'gotchas' agents should know about?"

### 8. Generate Context Content

For each category, prepare lean content for the project context file:

#### Content Structure:

```markdown
## Technology Stack & Versions

{{concise_technology_list_with_exact_versions}}

## Critical Implementation Rules

### Language-Specific Rules

{{bullet_points_of_critical_language_rules}}

### Framework-Specific Rules

{{bullet_points_of_framework_patterns}}

### Testing Rules

{{bullet_points_of_testing_requirements}}

### Code Quality & Style Rules

{{bullet_points_of_style_and_quality_rules}}

### Development Workflow Rules

{{bullet_points_of_workflow_patterns}}

### Critical Don't-Miss Rules

{{bullet_points_of_anti_patterns_and_edge_cases}}
```

### 9. Present Content and Menu

After each category, show the generated rules and present choices:

"I've drafted the {{category_name}} rules for your project context.

**Here's what I'll add:**

[Show the complete markdown content for this category]

**What would you like to do?**

### 10. Handle Menu Selection

#### If 'A' (Advanced Elicitation):

- Execute advanced-elicitation.xml with current category rules
- Process enhanced rules that come back
- Ask user: "Accept these enhanced rules for {{category}}? (y/n)"
- If yes: Update content, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'P' (Party Mode):

- Execute party-mode workflow with category rules context
- Process collaborative insights on implementation patterns
- Ask user: "Accept these changes to {{category}} rules? (y/n)"
- If yes: Update content, then return to switch prompt
- If no: Keep original content, then return to switch prompt

#### If 'C' (Continue):

- Save the current category content to project context file
- Update frontmatter: `sections_completed: [...]`
- Proceed to next category or step-03 if complete

## APPEND TO PROJECT CONTEXT:

When user confirms via the switch prompt for a category, append the content directly to `{output_folder}/project-context.md` using the structure from step 8.

## SUCCESS METRICS:

✅ All critical technology versions accurately documented
✅ Language-specific rules cover unobvious patterns
✅ Framework rules capture project-specific conventions
✅ Testing rules ensure consistent test quality
✅ Code quality rules maintain project standards
✅ Workflow rules prevent implementation conflicts
✅ Content is lean and optimized for LLM context
✅ switch prompt presented and handled correctly for each category

## FAILURE MODES:

❌ Including obvious rules that agents already know
❌ Making content too verbose for LLM context efficiency
❌ Missing critical anti-patterns or edge cases
❌ Not getting user validation for each rule category
❌ Not documenting exact versions and configurations
❌ Not presenting switch prompt after content generation

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation — Explore nuanced rules for this category
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — Review from different implementation perspectives
  </case>
  <case value="continue" next="step-03-complete">
    Continue — Save these rules and move to next category
  </case>
</switch>
