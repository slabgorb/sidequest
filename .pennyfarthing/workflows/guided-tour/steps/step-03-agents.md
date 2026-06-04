# Step 3: Agent Activation & Workflow Basics

<step-meta>
step: 3
name: agents
workflow: guided-tour
agent: orchestrator
gate: true
next: step-04-sprint
</step-meta>

<purpose>
Introduce the agent system and workflow patterns. Agents are specialized roles (Dev, TEA, Reviewer, SM, Architect, etc.) that collaborate through phased workflows. Each agent activates with its persona and toolset.
</purpose>

<prerequisites>
- Step 2 (Themes) completed
- A theme is set (agents use theme characters)
</prerequisites>

<instructions>
1. Explain the agent model: each agent has a specific role and expertise
2. Show the available agents and their slash commands (all use /pf- prefix)
3. Explain the workflow concept: agents hand off to each other in sequence
4. Show workflow types: phased (TDD, trivial) vs stepped (architecture, this tour)
5. Demonstrate a workflow listing with `pf workflow list`
</instructions>

<actions>
- Run: `pf workflow list` to show all available workflows
- Run: `pf workflow show tdd` to display the TDD workflow phases
- Show: full agent commands table with /pf- prefix
</actions>

<output>
Present the agent and workflow overview:

```markdown
## Agents & Workflows

**Agents** are specialized roles activated via slash commands:

| Command | Agent | Role |
|---------|-------|------|
| `/pf-sm` | Scrum Master | Story setup, sprint coordination, story completion |
| `/pf-tea` | Test Engineer | Test design, TDD RED phase, acceptance criteria analysis |
| `/pf-dev` | Developer | Feature implementation, making tests GREEN |
| `/pf-reviewer` | Code Reviewer | Adversarial review, quality enforcement |
| `/pf-architect` | System Architect | Technical design, architecture decisions |
| `/pf-pm` | Product Manager | Strategic planning, prioritization |
| `/pf-tech-writer` | Technical Writer | Documentation creation and maintenance |
| `/pf-ux-designer` | UX Designer | User experience design and UI patterns |
| `/pf-devops` | DevOps Engineer | Infrastructure, deployment, CI/CD |
| `/pf-ba` | Business Analyst | Requirements discovery, stakeholder analysis |
| `/pf-orchestrator` | Orchestrator | Meta-operations, agent coordination |

**Workflows** define how agents collaborate:
- **TDD** (phased): `/pf-sm` → `/pf-tea` → `/pf-dev` → `/pf-reviewer` → `/pf-sm`
- **Trivial** (phased): `/pf-sm` → `/pf-dev` → `/pf-reviewer` → `/pf-sm`
- **Stepped** workflows guide you through interactive steps (like this tour)
```
</output>

<gate>
## Completion Criteria
- [ ] User understands the agent role model
- [ ] User has seen the full 11-agent roster with /pf- commands
- [ ] User has seen the workflow list
- [ ] User understands phased vs stepped workflow types
</gate>

<deep-dive>
## Deep-Dive: Agents & Workflows

When the user selects Dig In, explore these topics interactively:

- **Agent activation**: How `/pf-{agent}` loads persona, session, and tools via `pf agent start`
- **Phased workflows**: TDD, BDD, trivial — phase order, gates between phases, handoff protocol
- **Stepped workflows**: BikeLane engine, step files, collaboration menus, verification gates
- **Tandem mode**: Background observer pairing (e.g., Architect watching Dev)
- **Team mode**: Native Claude Code agent teams for parallel collaboration within a phase
- **Subagents**: Haiku-powered helpers (testing-runner, sm-setup, reviewer-preflight)
- **Handoff protocol**: resolve-gate → complete-phase → marker → next agent activates

Use AskUserQuestion to let the user pick which sub-topic to explore. Continue the deep-dive loop until the user chooses to move on.
</deep-dive>

<switch tool="AskUserQuestion">
  <case value="continue" next="step-04-sprint">
    Continue — Proceed to sprint commands
  </case>
  <case value="dig-in" next="LOOP">
    Dig In — Explore agent activation, handoff protocol, and team mode
  </case>
  <case value="try-it" next="LOOP">
    Try It — Run `pf workflow list` or `pf workflow show tdd`
  </case>
  <case value="skip" next="step-04-sprint">
    Skip — Move to sprint management
  </case>
</switch>
