# Strategic Agent Template

**For:** PM, Architect, Tech-Writer, UX-Designer, DevOps, Orchestrator (support agents)

This template defines the standard structure for strategic agents. These agents support the TDD flow but are not part of the core SM → TEA → Dev → Reviewer cycle.

---

## Section Order

```
1.  # Title
2.  <persona>
3.  <role>
4.  <helpers>
5.  <responsibilities>
6.  <skills>
7.  <constraints>        (optional)
8.  <context>
9.  <on-activation>
10. ## Workflows (markdown sections)
11. <handoffs>
12. <exit>
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
**Primary:** {When this agent is invoked}
**Blessed Path:** {Recommended workflow, e.g., "PM → /pf-architect for design work"}
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
- `/architecture` - Architecture documentation
</skills>

<constraints>
**This agent does NOT:**
- {Constraint 1, e.g., "Write implementation code"}
- {Constraint 2, e.g., "Make unilateral architecture decisions"}
</constraints>

<context>
**See:** `.pennyfarthing/guides/agent-behavior.md` for project info and git strategy.
**Work Directory:** {Where this agent's artifacts live}
</context>

<on-activation>
1. Load sprint context from `sprint/current-sprint.yaml`
2. Check for active work in `.session/*-session.md`
3. {Agent-specific startup steps}
4. Present task menu or offer to continue active work
</on-activation>

## Key Workflows

### {Workflow 1 Name}

**When:** {Trigger condition}
**Output:** {What this workflow produces}

{Workflow steps}

### {Workflow 2 Name}

**When:** {Trigger condition}
**Output:** {What this workflow produces}

{Workflow steps}

<handoffs>
**From:**
- {Agent} → me: {When/why they hand off to me}

**To:**
- me → {Agent}: {When/why I hand off to them}
</handoffs>

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
| `<role>` | When invoked, blessed path | Yes |
| `<helpers>` | What Haiku helpers do | Yes |
| `<responsibilities>` | Duties this agent performs | Yes |
| `<skills>` | /commands this agent uses | Yes |
| `<constraints>` | What this agent does NOT do | Optional |
| `<context>` | Guide files and work directory | Yes |
| `<on-activation>` | Startup checklist | Yes |
| Workflows | Agent-specific procedures | Yes |
| `<handoffs>` | From/to relationships | Yes |
| `<exit>` | How to leave agent mode | Yes |

---

## Differences from Tactical Template

| Aspect | Tactical | Strategic |
|--------|----------|-----------|
| `<reasoning-mode>` | Yes (verbose toggle) | No |
| `<constraints>` | No | Optional |
| Assessment Template | Yes (structured output) | No |
| Handoff section | Auto-invoke logic | From/to relationships |
| Flow position | Part of TDD cycle | Support/enable TDD |

---

## Notes

- **Constraints section** is optional but recommended for agents that should NOT write code (Architect, UX, Tech-Writer)
- **Handoffs** describe relationships, not automatic invocation (unlike tactical agents)
- **Workflows** tend to be domain-specific (design, docs, infra) rather than phase-based
