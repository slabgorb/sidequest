# Step 5: Populate shared-context.md

<purpose>
Populate the shared-context.md file with accurate project information based on discovery and repos.yaml. This file is loaded by all agents.
</purpose>

<instructions>
1. Read template from .claude/project/docs/shared-context.md
2. Replace placeholder content with discovered information
3. Add repo-specific sections for each repository
4. Include accurate commands and workflows
5. Allow user to review and refine
</instructions>

<output>
- shared-context.md populated with real project data
- Tech stack section accurate
- Repo structure matches repos.yaml
- Commands verified correct
- User has approved content
</output>

## SHARED-CONTEXT STRUCTURE

The shared-context.md has these key sections to populate:

### 1. Project Section

```markdown
## Project

- **Name:** {from repos.yaml or detection}
- **Sprint Status:** `sprint/current-sprint.yaml`
- **Active Work:** `.session/{story-id}-session.md`
- **Agent Framework:** Pennyfarthing (pf CLI)
```

### 2. Tech Stack Table

Generate from repos.yaml:

```markdown
### Tech Stack

| Component | Language | Framework | Notes |
|-----------|----------|-----------|-------|
| API       | TypeScript | Express | REST endpoints |
| UI        | TypeScript | React   | Vite build |
| Shared    | TypeScript | -       | Common types |
```

### 3. Repo Structure

For orchestrator pattern:
```markdown
### Repo Structure

```
{project}/                   # Orchestrator
├── .claude/                 # Claude Code configuration
├── .pennyfarthing/          # Pennyfarthing framework
├── sprint/                  # Sprint tracking
├── .session/                # Active work sessions
├── {project}-api/           # API subrepo (gitignored, clone separately)
│   ├── src/
│   └── tests/
└── {project}-ui/            # UI subrepo (gitignored, clone separately)
    ├── src/
    └── public/
```
```

For monorepo:
```markdown
### Repo Structure

```
{project}/
├── packages/
│   ├── api/                 # Backend service
│   ├── ui/                  # Frontend app
│   └── shared/              # Common code
├── .claude/
└── .pennyfarthing/
```
```

### 4. Git Branch Strategy

```markdown
## Git Branch Strategy

- **All work:** Feature branches
- **Branch from:** `develop` (or `main` if no develop)
- **PRs target:** `develop`
- **Naming:** `feat/{story}-{description}` or `fix/{issue}-{description}`
```

### 5. Testing Commands

Extract from repos.yaml and format:

```markdown
## Testing Commands

{if orchestrator with subrepos}
### API
```bash
cd {project}-api && npm test
```

### UI
```bash
cd {project}-ui && npm test
```
{/if}

{if monorepo}
```bash
# Run all tests
pnpm test

# Run specific package
pnpm test --filter @{project}/api
```
{/if}

{if single repo}
```bash
{test_command}
{test_command} -- --grep "pattern"
```
{/if}
```

### 6. Building

```markdown
## Building

{per-repo build commands from repos.yaml}
```

## POPULATION LOGIC

1. **Read existing file** - preserve any user customizations
2. **Identify placeholder sections** - look for template markers
3. **Replace with real data** - from repos.yaml and discovery
4. **Preserve custom sections** - don't overwrite user additions
5. **Add new sections** - for repos not in template

## INTERACTIVE REFINEMENT

```
📄 Updated shared-context.md
═════════════════════════════

Sections updated:
  ✓ Project name and metadata
  ✓ Tech stack table ({n} components)
  ✓ Repo structure diagram
  ✓ Testing commands
  ✓ Build commands

Preview of changes:
{diff or summary}

(switch prompt presents options)
```

## SUCCESS CRITERIA

✅ All placeholder content replaced
✅ Tech stack matches actual project
✅ Commands are accurate and tested
✅ Repo structure reflects reality
✅ User has reviewed and approved

## NEXT STEP

After shared-context.md is updated, proceed to `step-06-task-runner.md` to create justfile/makefile for orchestrator command proxying.

<switch tool="AskUserQuestion">
  <case value="accept-and-write-changes" next="LOOP">
    Accept and write changes
  </case>
  <case value="edit-a-specific-section" next="LOOP">
    Edit a specific section
  </case>
  <case value="view-full-file" next="LOOP">
    View full file
  </case>
  <case value="show-diff-from-original" next="LOOP">
    Show diff from original
  </case>
</switch>
