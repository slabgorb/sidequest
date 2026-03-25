# Step 11: Complete Setup & Validation

<purpose>
Finalize the project setup, run validation checks, and provide the user with a summary of everything configured. Ensure the project is ready for development.
</purpose>

<instructions>
1. Run pf validate to validate installation
2. Summarize all configurations created
3. Provide quick-start guide
4. Offer next steps and resources
</instructions>

<output>
- All validation checks pass
- Configuration summary presented
- Quick-start guide provided
- User ready to begin development
</output>

## VALIDATION

### Run Doctor

```bash
pf validate
```

Expected output:
```
🔧 Pennyfarthing Health Check
════════════════════════════

✓ .pennyfarthing/ directory exists
✓ Manifest found (v9.1.1)
✓ Symlinks valid
✓ Sprint directory exists
✓ Session directory exists
✓ Git hooks installed
✓ Settings configured

All checks passed!
```

### Manual Validation Checklist

```
📋 Setup Validation
════════════════════

Configuration files:
  {✓|✗} repos.yaml          - Repository configuration
  {✓|✗} CLAUDE.md           - Project instructions
  {✓|✗} shared-context.md   - Agent shared context
  {✓|✗} justfile            - Task runner
  {✓|✗} config.local.yaml - Theme configuration

Directories:
  {✓|✗} .pennyfarthing/     - Framework installation
  {✓|✗} .claude/            - Claude Code config
  {✓|✗} sprint/             - Sprint tracking
  {✓|✗} .session/           - Work sessions

Optional:
  {✓|✗} Frame GUI configured
  {✓|✗} Subrepos cloned
```

## CONFIGURATION SUMMARY

```
📊 Project Setup Summary
═════════════════════════

Project: {project_name}
Type: {orchestrator|monorepo|single}
Theme: {selected_theme}

Repositories Configured:
┌────────────────┬──────────┬────────────────────────┐
│ Name           │ Type     │ Path                   │
├────────────────┼──────────┼────────────────────────┤
│ orchestrator   │ orch     │ .                      │
│ api            │ api      │ {project}-api/         │
│ ui             │ ui       │ {project}-ui/          │
└────────────────┴──────────┴────────────────────────┘

Files Created:
  • repos.yaml           - Repository configuration
  • CLAUDE.md            - Project instructions for Claude
  • shared-context.md    - Shared agent context (updated)
  • justfile             - Task runner with recipes
  • config.local.yaml  - Theme: {theme}

Commands Available:
  just test-all          - Run all tests
  just build-all         - Build all repos
  just dev               - Start development
  just gui               - Launch Frame GUI (if configured)
```

## QUICK-START GUIDE

```
🚀 Quick Start Guide
════════════════════

1. START DEVELOPMENT
   just dev              # Start dev servers
   # OR
   just dev-api          # Start just API
   just dev-ui           # Start just UI

2. RUN TESTS
   just test-all         # Test everything
   just test-api         # Test API only

3. USE PENNYFARTHING AGENTS
   /sm                   # Scrum Master - manage stories
   /sprint status        # View sprint
   /sprint work          # Start a story

4. WORKFLOW
   Story flow: SM → TEA → Dev → Reviewer → SM

5. LAUNCH FRAME GUI (if configured)
   just gui              # Browser UI
   # OR
   pf frame start     # Terminal panels

6. GET HELP
   /help                 # Context-aware help
   pf validate  # Check installation
```

## NEXT STEPS

```
📌 Recommended Next Steps
═════════════════════════

IMMEDIATE:
  □ Take the tour (/guided-tour) to learn the framework
  □ Review CLAUDE.md and customize for your project
  □ Add project-specific notes to shared-context.md
  □ Create your first sprint in sprint/current-sprint.yaml

WHEN READY:
  □ Run /sm to start managing work
  □ Create stories with /sprint story add
  □ Begin TDD workflow with /tea

CUSTOMIZATION:
  □ Add custom skills in .claude/project/skills/
  □ Add custom commands in .claude/project/commands/
  □ Configure agent sidecars in .pennyfarthing/sidecars/

RESOURCES:
  □ Docs: https://github.com/slabgorb/pennyfarthing
  □ Issues: https://github.com/slabgorb/pennyfarthing/issues
  □ Skill help: /help {skill_name}
```

## FINAL MESSAGE

```
✨ Setup Complete!
══════════════════

Your Pennyfarthing project is ready for development.

{if theme_selected}
Your agents now use the '{theme}' theme.
{agent_character} says: "{theme_greeting}"
{/if}

Quick commands:
  /guided-tour     - Take the guided tour
  /sm              - Start managing work
  /sprint status   - View sprint
  /help            - Get help

{if gui_configured}
Launch Frame GUI for the visual experience:
  just gui
{/if}

Happy coding! 🚴
```

## GUIDED TOUR

Now that setup is complete, offer the user a guided tour of the framework.

Use the AskUserQuestion tool as a switch-gate to let the user choose:

<switch>
**Prompt the user with AskUserQuestion:**

"Would you like to take a guided tour of Pennyfarthing? The tour walks through agents, workflows, and key commands."

**Options:**

1. **Yes, start the tour** — Load and begin the `guided-tour` workflow. Run `/guided-tour` to launch it.
2. **Later** — Skip for now. The user can start the tour any time by running `/guided-tour`.
3. **Skip** — Continue without the tour. Setup is complete.

**Behavior per selection:**
- **Yes:** Execute `/guided-tour` to start the guided-tour workflow.
- **Later:** Display: "No problem! Run `/guided-tour` whenever you're ready."
- **Skip:** Proceed directly to WORKFLOW COMPLETE.
</switch>

## WORKFLOW COMPLETE

This workflow is now complete. The user has:

✅ Discovered and configured repositories
✅ Cloned any needed subrepos
✅ Generated repos.yaml
✅ Created CLAUDE.md
✅ Populated shared-context.md
✅ Created justfile with recipes
✅ Selected a persona theme
✅ Optionally installed additional theme packs
✅ Configured Jira project key
✅ Optionally configured Frame GUI
✅ Validated the setup

The project is ready for development with Pennyfarthing.
