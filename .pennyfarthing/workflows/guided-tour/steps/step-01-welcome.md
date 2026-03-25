# Step 1: Welcome & Getting Started

<step-meta>
step: 1
name: welcome
workflow: guided-tour
agent: orchestrator
gate: true
next: step-02-themes
</step-meta>

<purpose>
Welcome the user to Pennyfarthing and orient them with the getting-started guide and /pf-help command. This step establishes the foundation for the rest of the tour.
</purpose>

<prerequisites>
- Pennyfarthing is installed (`pf` command available)
- Running from a project with `.pennyfarthing/` directory
</prerequisites>

<instructions>
1. Welcome the user to the Pennyfarthing guided tour
2. Explain that this tour covers the five key areas: themes, agents, workflows, sprint management, and configuration
3. Show the user the `/pf-help` command for quick reference at any time
4. Mention the getting-started guide as a companion reference
5. Verify the installation is healthy by running `pf validate`
</instructions>

<actions>
- Run: `pf --version` to confirm installation
- Run: `pf validate` to check project health
- Show: `/pf-help` command for reference
</actions>

<output>
Present a welcome message with tour overview:

```markdown
## Welcome to Pennyfarthing

You're about to explore the key features of the framework:

1. **Themes** — Persona system with character-driven agents
2. **Agents** — Specialized roles (Dev, TEA, Reviewer, etc.)
3. **Workflows** — Phased and stepped development patterns
4. **Sprint** — Story tracking and backlog management
5. **Config** — Hooks, settings, and customization

Use `/pf-help` anytime for quick reference.
```
</output>

<gate>
## Completion Criteria
- [ ] User has seen the tour overview
- [ ] `pf validate` ran successfully (or issues noted)
- [ ] User understands they can use `/pf-help` for reference
</gate>

<deep-dive>
## Deep-Dive: Pennyfarthing Architecture

When the user selects Dig In, explore these topics interactively:

- **Framework structure**: `.pennyfarthing/` directory, `pennyfarthing-dist/`, symlinks
- **Display modes**: TUI (Frame), GUI (Frame GUI), IDE (Frame)
- **Component codenames**: Frame (server), TirePump (context clearing), Frame (panel viewer), BikeLane (workflow engine)
- **Getting-started guide**: Walk through the companion reference document
- **Installation health**: Explain each validator and what it checks

Use AskUserQuestion to let the user pick which sub-topic to explore. Continue the deep-dive loop until the user chooses to move on.
</deep-dive>

<switch tool="AskUserQuestion">
  <case value="continue" next="step-02-themes">
    Continue — Proceed to theme selection
  </case>
  <case value="dig-in" next="LOOP">
    Dig In — Explore Pennyfarthing architecture and components
  </case>
  <case value="try-it" next="LOOP">
    Try It — Run `/pf-help` to see the help system
  </case>
  <case value="skip" next="step-02-themes">
    Skip — Jump ahead to themes
  </case>
</switch>
