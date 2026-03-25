---
description: /setup - Interactive Project Setup
---

# /setup - Interactive Project Setup

<command>setup</command>

<purpose>
Launch the interactive project-setup workflow to configure a Pennyfarthing project. This workflow guides you through discovering repos, generating CLAUDE.md, configuring themes, and more.
</purpose>

<usage>
```bash
# Run after pf init
/setup

# Skip certain steps
/setup --skip-theme
/setup --skip-cyclist
```
</usage>

<workflow>
The setup workflow guides you through:

1. **Discovery** - Detect project structure and tech stack
2. **Clone Repos** - Optionally clone subrepos for orchestrator pattern
3. **repos.yaml** - Generate repository configuration
4. **CLAUDE.md** - Create project instruction file
5. **shared-context.md** - Populate with real project info
6. **Task Runner** - Create justfile/Makefile
7. **Theme** - Select persona theme
8. **Theme Packs** - Optionally install additional theme packs
9. **Jira** - Configure Jira project key
10. **Cyclist** - Optionally install visual terminal
11. **Validation** - Run doctor and confirm setup
</workflow>

<when-to-use>
- After running `pf init` for the first time
- When setting up a new orchestrator with subrepos
- When repos.yaml or CLAUDE.md don't exist
- When converting an existing project to use Pennyfarthing
</when-to-use>

<prerequisites>
- Pennyfarthing must be initialized (`pf init`)
- Should be in project root directory
</prerequisites>

<execution>
This skill launches the `project-setup` stepped workflow.

Load the workflow definition:
```bash
cat .pennyfarthing/workflows/project-setup/workflow.yaml
```

Then follow the stepped workflow, starting with:
```bash
cat .pennyfarthing/workflows/project-setup/steps/step-01-discover.md
```
</execution>

<related>
- `/pf-sprint` - Sprint management after setup
- `/theme set` - Change themes after setup
- `/pf-workflow` - View available workflows
- `pf doctor` - Validate installation
</related>
