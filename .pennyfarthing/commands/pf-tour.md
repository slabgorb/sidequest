---
description: /guided-tour - Interactive Guided Tour
---

# /guided-tour - Interactive Guided Tour

<command>guided-tour</command>

<purpose>
Launch the guided-tour workflow to walk through Pennyfarthing's agents, workflows, and key commands. Can be run at any time after setup is complete.
</purpose>

<usage>
```bash
# Start the guided tour
/guided-tour
```
</usage>

<workflow>
The guided-tour workflow walks you through:

1. **Welcome** - Overview of what Pennyfarthing provides
2. **Agents** - Meet the agent roster and their roles
3. **Workflows** - Understand TDD, setup, and custom workflows
4. **Sprint** - Learn sprint management and story tracking
5. **Commands** - Key commands and skills for daily use
6. **Next Steps** - Suggested first actions for your project
</workflow>

<when-to-use>
- After running `/setup` for the first time
- When onboarding new team members
- When you want a refresher on available features
- Any time — the tour is always available
</when-to-use>

<prerequisites>
- Pennyfarthing must be initialized (`pf setup` or `/setup` completed)
</prerequisites>

<execution>
This skill launches the `guided-tour` stepped workflow.

Load the workflow definition:
```bash
cat .pennyfarthing/workflows/guided-tour/workflow.yaml
```

Then follow the stepped workflow, starting with the first step as defined in the workflow YAML.
</execution>

<related>
- `/pf-setup` - Initial project setup
- `/pf-sprint` - Sprint management
- `/pf-workflow` - View available workflows
- `/pf-help` - Context-aware help
</related>
