# Step 4: Generate CLAUDE.md

<purpose>
Generate the project's CLAUDE.md file - the primary instruction file that Claude Code reads on every session. This file defines project-specific rules, structure, and workflows.
</purpose>

<instructions>
1. Analyze repos.yaml and discovered tech stack
2. Generate CLAUDE.md with project-specific content
3. Include correct commands, structure, and workflows
4. Allow user to review and refine
5. Write to project root
</instructions>

<output>
- CLAUDE.md file created at project root
- Accurate project structure documented
- Correct build/test/lint commands
- Appropriate workflow guidance
- User has approved the content
</output>

## CLAUDE.MD STRUCTURE

```markdown
# CLAUDE.md - {Project Name}

This file provides guidance to Claude Code when working on this project.

## Project Overview

{Brief description of what the project does}

**Type:** {orchestrator|api|ui|cli|library|framework}
**Node:** {version if applicable}
**Type:** {ES module|CommonJS}

## Repository Structure

{if orchestrator}
```
{project_name}/              # Orchestrator
├── .claude/                 # Claude Code configuration
├── .pennyfarthing/          # Pennyfarthing framework
├── sprint/                  # Sprint tracking
├── .session/                # Active work sessions
├── {subrepo1}/              # {description}
└── {subrepo2}/              # {description}
```
{/if}

{if monorepo}
```
{project_name}/
├── packages/
│   ├── {package1}/          # {description}
│   └── {package2}/          # {description}
├── .claude/
└── .pennyfarthing/
```
{/if}

{if single_repo}
```
{project_name}/
├── src/                     # Source code
├── tests/                   # Tests
├── .claude/
└── .pennyfarthing/
```
{/if}

## Build Commands

```bash
{build_command}              # Build the project
{test_command}               # Run tests
{lint_command}               # Run linter
{dev_command}                # Start development
```

## Development Workflow

{if has_sprint}
- `/sm` - Scrum Master (story management)
- `/tea` - Test Engineer/Architect
- `/dev` - Developer
- `/reviewer` - Code Reviewer
{/if}

## Git Workflow

- **Feature branches:** `feat/{story}-{description}`
- **Bug fixes:** `fix/{issue}-{description}`
- **PRs target:** `develop` (or `main` if no develop)

## Testing

```bash
{test_command}                        # Run all tests
{test_command} -- --grep "pattern"    # Run specific tests
```

## Developer Guidance

{if has_pennyfarthing}
### Getting Started

- Run `/pf-help` for context-aware help on any command or agent
- Run `/pf-sprint status` to see current sprint progress
- Run `/pf-sprint work` to pick up your next story

### Daily Workflow

1. `/sm` — Start or resume a story (Scrum Master handles setup)
2. Agent handoffs guide you through the workflow automatically
3. `/reviewer` — Code review when implementation is complete
4. `/sm` — Finish the story (archive, merge, Jira update)

### Key Commands

| Command | Purpose |
|---------|---------|
| `/pf-help` | Context-aware help |
| `/pf-sprint backlog` | See available work |
| `/pf-sprint work STORY` | Start a specific story |
| `/pf-theme show` | See your current persona theme |
| `/pf-workflow` | Check active workflow status |
{/if}

## Important Notes

{Project-specific notes, gotchas, conventions}
```

## GENERATION LOGIC

### 1. Extract from repos.yaml

Read the repos.yaml created in step 2:
- Project name from orchestrator/root repo
- Type from repo classification
- Commands from each repo

### 2. Detect Additional Context

Scan for:
- `tsconfig.json` → TypeScript config details
- `jest.config.*` → Test framework config
- `.eslintrc.*` → Linting config
- `Dockerfile` → Container info
- CI config (`.github/workflows/`, `.gitlab-ci.yml`)

### 3. Include Pennyfarthing Integration

If sprint/ exists:
```markdown
## Sprint Management

- `/pf-sprint status` - View current sprint
- `/pf-sprint backlog` - Available stories
- `/pf-sprint work` - Start a story
```

### 4. Include Developer Guidance

If `.pennyfarthing/` exists (Pennyfarthing is initialized):
```markdown
## Developer Guidance

### Getting Started

- Run `/pf-help` for context-aware help on any command or agent
- Run `/pf-sprint status` to see current sprint progress
- Run `/pf-sprint work` to pick up your next story

### Daily Workflow

1. `/sm` — Start or resume a story (Scrum Master handles setup)
2. Agent handoffs guide you through the workflow automatically
3. `/reviewer` — Code review when implementation is complete
4. `/sm` — Finish the story (archive, merge, Jira update)

### Key Commands

| Command | Purpose |
|---------|---------|
| `/pf-help` | Context-aware help |
| `/pf-sprint backlog` | See available work |
| `/pf-sprint work STORY` | Start a specific story |
| `/pf-theme show` | See your current persona theme |
| `/pf-workflow` | Check active workflow status |
```

### 5. Add Project-Specific Sections

Based on tech stack:

**For TypeScript projects:**
```markdown
## TypeScript

- Use `.js` extensions in imports
- Strict mode enabled
- ES modules (`"type": "module"`)
```

**For React projects:**
```markdown
## React Patterns

- Functional components with hooks
- Component files in `src/components/`
- Tests co-located with components
```

## INTERACTIVE REFINEMENT

```
📄 Generated CLAUDE.md
═══════════════════════

{preview of generated content}

(switch prompt presents options)
```

## SUCCESS CRITERIA

✅ CLAUDE.md accurately describes project
✅ Commands are correct and tested
✅ Structure matches actual project
✅ Workflows appropriate for project type
✅ Developer guidance included (if Pennyfarthing initialized)
✅ User has reviewed and approved

## NEXT STEP

After CLAUDE.md is written, proceed to `step-05-shared-context.md` to populate the shared-context.md file.

<switch tool="AskUserQuestion">
  <case value="accept-and-write-to-claudemd" next="LOOP">
    Accept and write to CLAUDE.md
  </case>
  <case value="edit-a-section" next="LOOP">
    Edit a section
  </case>
  <case value="add-a-new-section" next="LOOP">
    Add a new section
  </case>
  <case value="regenerate-with-different-focus" next="LOOP">
    Regenerate with different focus
  </case>
  <case value="preview-full-content" next="LOOP">
    Preview full content
  </case>
</switch>
