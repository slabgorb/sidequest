# Tactical Agent Template

**For:** SM, TEA, Dev, Reviewer (TDD flow agents)

This template defines the standard structure for tactical agents. All tactical agents should follow this section order for consistency and easy comparison.

---

## Section Order

```
1.  # Title
2.  <persona>
3.  <role>
4.  <helpers>
5.  <responsibilities>
6.  <skills>
7.  <context>
8.  <reasoning-mode>
9.  <on-activation>
10. ## Workflows (markdown sections)
11. ## Assessment Template
12. ## Handoff
13. <exit>
```

---

## Template

```markdown
# {NAME} Agent - {Role Title}

<persona>
Auto-loaded by `pf agent start` from theme config. See output above.

**Fallback if not loaded:** {Brief personality description}
</persona>

<role>
**Primary:** {When this agent is invoked, e.g., "via /pf-tea for TDD test writing"}
**Position:** {Where in TDD flow, e.g., "SM → **TEA** → Dev → Reviewer"}
</role>

<helpers>
From theme config. Model: haiku. Tasks: {What helpers do for this agent}

**Skills I Use:**
- `/skill-name` - {description}
</helpers>

<responsibilities>
- {Duty 1 - what this agent is responsible for}
- {Duty 2}
- {Duty 3}
</responsibilities>

<skills>
**Skills I Use:**
- `/pf-sprint` - Sprint status and backlog
- `/pf-testing` - Test execution patterns
</skills>

<context>
**See:** `.pennyfarthing/guides/agent-behavior.md` for shared tactical agent behavior, project info, and git strategy.
</context>

<reasoning-mode>
**Default:** Quiet mode - follow ReAct pattern internally, show only key decisions

**Toggle:** User says "verbose mode" to see explicit reasoning

When verbose, show thought process:
```
THOUGHT: {what I'm considering}
ACTION: {what I'm doing}
OBSERVATION: {what I found}
REFLECT: {what this means}
```

**{Agent}-Specific Reasoning:**
- {When doing X: reason about Y}
- {When doing Z: think through W}

**REMINDER:** Delegate test runs to testing-runner subagent.
</reasoning-mode>

<on-activation>
1. Workflow state is provided in prime activation output (`# Workflow State` section)
2. Read session file if active work exists
3. Verify actual state matches session file
4. Check if handed off to me (Phase field)
5. If handed off: offer to start immediately
6. If not: show task menu
</on-activation>

## Primary Workflow: {Workflow Name}

{Agent-specific workflow description}

### Step 1: {Step Name}
{Description}

### Step 2: {Step Name}
{Description}

## {Agent} Assessment Template

```markdown
## {Agent} Assessment

**{Key field 1}:** {value}
**{Key field 2}:** {value}

**Handoff:** To {next agent} for {next task}
```

## Handoff (Context-Aware Auto-Invoke)

After completing work:

1. Write assessment to session file
2. Spawn handoff helper (`.pennyfarthing/agents/{agent}-handoff.md`)
3. Check context: `pf context`
4. If `HANDOFF_MODE=auto`: Use Skill tool to invoke next agent
5. If `HANDOFF_MODE=ask`: Tell user to start fresh session

<exit>
To exit: "Exit {Agent}" or "Switch to [other agent]"

Follow exit protocol from `agent-behavior.md` (resolve-gate → complete-phase → marker). EXIT.
</exit>
```

---

## Section Descriptions

| Section | Purpose | Required |
|---------|---------|----------|
| `<persona>` | Character/personality from theme | Yes |
| `<role>` | When invoked, position in flow | Yes |
| `<helpers>` | What Haiku helpers do | Yes |
| `<responsibilities>` | Duties this agent performs | Yes |
| `<skills>` | /commands this agent uses | Yes |
| `<context>` | Guide files to reference | Yes |
| `<reasoning-mode>` | Verbose/quiet toggle | Yes |
| `<on-activation>` | Startup checklist | Yes |
| Workflows | Agent-specific procedures | Yes |
| Assessment | Output format template | Yes |
| Handoff | Auto-invoke instructions | Yes |
| `<exit>` | How to leave agent mode | Yes |

---

## Notes

- **Preserve existing workflow content** when aligning to this template
- **Section order matters** for consistency across agents
- **XML tags** are used for structured sections that benefit from clear boundaries
- **Markdown headers** are used for longer narrative sections (workflows)
