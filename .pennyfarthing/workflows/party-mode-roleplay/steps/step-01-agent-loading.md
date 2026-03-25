# Step 1: Agent Loading and Party Mode Initialization

<step-meta>
number: 1
name: agent-loading
gate: false
next: step-02-discussion
</step-meta>

<purpose>
Load the full Pennyfarthing agent roster with theme personas and initialize party mode with an engaging introduction. This replaces BMAD's CSV manifest loading with PF's agent .md files and theme persona resolution.
</purpose>

<instructions>
1. Read `.pennyfarthing/config.local.yaml` to get the active `theme`
2. Read the theme file from `pennyfarthing-dist/personas/themes/{theme}.yaml` (or `.pennyfarthing/personas/themes/`)
3. Scan `.pennyfarthing/agents/` for all agent `.md` files
4. For each agent, extract their role from the `<role>` tag in their agent file
5. Resolve each agent's persona from the theme file (`agents.{agent-name}` section): character name, style, expertise, emoji
6. Build a complete roster merging agent role data with theme persona data
7. Present an enthusiastic party mode introduction showcasing 3-4 diverse agents
8. Wait for the user to provide an initial topic
</instructions>

<actions>
- Read: `{config_path}` for active theme
- Read: `.pennyfarthing/personas/themes/{theme}.yaml` for persona data
- Read: `{agents_path}/*.md` for agent roles (scan directory, read `<role>` tags)
</actions>

<output>
Present the agent roster and invitation to discuss:

```
PARTY MODE ACTIVATED!

Welcome! All Pennyfarthing agents are here for a group discussion.
I've loaded the full roster with their {theme} personas.

Agents ready to collaborate:

- {emoji} {Character Name} ({Agent Role}): {brief expertise}
- {emoji} {Character Name} ({Agent Role}): {brief expertise}
- {emoji} {Character Name} ({Agent Role}): {brief expertise}
  ... and {N} more agents standing by.

What would you like to discuss with the team?
```
</output>

<switch tool="AskUserQuestion">
  <case value="continue" next="step-02-discussion">
    Continue — User provides a topic and discussion begins
  </case>
</switch>

<next-step>
After user provides a topic, proceed to step-02-discussion.md for multi-round discussion orchestration.
</next-step>

## Agent Roster

Include these primary agents (all found in `.pennyfarthing/agents/`):

| Agent | Role Focus |
|-------|-----------|
| pm | Strategy, prioritization, business value |
| architect | System design, technical possibilities |
| sm | Practical concerns, process, team impact |
| dev | Implementation, code, building |
| tea | Testing, quality, verification |
| ux-designer | User experience, interaction design |
| tech-writer | Documentation, communication |
| devops | Infrastructure, deployment, operations |
| orchestrator | Coordination, the long view |
| reviewer | Code quality, adversarial review |

Only include agents whose `.md` files exist in the agents directory. Skip subagent files (sm-setup, sm-finish, sm-handoff, sm-file-summary, handoff, reviewer-preflight, testing-runner, tandem-backseat).

## Persona Resolution

For each agent, resolve from the theme file:
- `character` — The persona name (e.g., "Amos Burton" in The Expanse theme)
- `style` — Communication style flavor
- `expertise` — Domain framing
- `emoji` — Default emoji identifier

If theme data is unavailable for an agent, fall back to the agent's role description from their `.md` file.

## Failure Modes

- Loading subagent files as primary agents
- Not resolving theme personas (presenting generic names instead of characters)
- Skipping the roster presentation and jumping straight to discussion

## Success Metrics

- All primary agents discovered and loaded
- Theme personas resolved for each agent
- Engaging introduction with character names displayed
- User prompted for an initial discussion topic
