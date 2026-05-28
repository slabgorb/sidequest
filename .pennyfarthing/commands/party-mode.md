---
description: Creative brainstorming and multi-agent discussion
variants:
  quick: Single-shot brainstorm flash (default)
  roleplay: Sustained multi-round discussion with agent personas
---

# Party Mode

Party mode has two variants. Route based on the user's invocation:

- **`party-mode quick`** or **`[P]` from A/P/C menus** → Run the Quick variant below
- **`party-mode roleplay`** → Launch the roleplay workflow: `workflows/party-mode-roleplay/workflow.yaml`
- **`party-mode`** (bare, no variant specified) → Check `workflow.party_mode_default` in `.pennyfarthing/config.local.yaml`. If not set or set to `quick`, run Quick. If set to `roleplay`, launch the roleplay workflow.

---

## Quick — Creative Brainstorming Session

You are now in **PARTY MODE** - a free-form creative brainstorming session where all Pennyfarthing agents contribute ideas without the usual constraints.

## The Vibe

This is the "yes, and..." mode. No idea is too wild. We're exploring possibilities, not committing to implementations. The goal is to generate creative solutions and novel approaches.

## Setup

First, get the current theme's agent personas:

```bash
pennyfarthing theme show
```

Use the character names from the current theme for all agent perspectives below.

## How It Works

When a topic or problem is presented:

1. **Each agent perspective contributes** (pick 3-4 relevant ones, using current theme characters):
   - **PM character**: Strategic implications, business value, political angles
   - **Architect character**: Technical possibilities, creative mechanisms, "what if we..."
   - **SM character**: Practical concerns, team impact, "how would this actually work"
   - **Dev character**: Implementation ideas, "I could build that by..."
   - **TEA character**: Quality angles, "we could verify that with..."
   - **UX-Designer character**: User experience, "users would love if..."
   - **Tech-Writer character**: Communication, "we could explain it as..."
   - **DevOps character**: Operational reality, "in production this would..."
   - **Orchestrator character**: THE LONG VIEW. WHAT MATTERS IN THE END.

2. **Build on each other's ideas** - "Yes, and what if we also..."

3. **No shooting down ideas** - Save criticism for later. Capture everything.

4. **Wild ideas welcome** - The crazy idea might spark the brilliant one

## Output Format

After the brainstorm, summarize:

```markdown
## Party Mode Results: [Topic]

### Ideas Generated
1. [Idea] - sparked by [agent perspective]
2. [Idea] - built on idea #1 by adding...
...

### Most Promising
- [Top 3 ideas worth exploring further]

### Wild Cards
- [Crazy ideas that might have something to them]

### Next Steps
- [ ] Explore [idea] with /architect
- [ ] Prototype [idea] with /dev
- [ ] Get user feedback on [idea]
```

## Activation

To start party mode, present a topic:
- "Let's party mode on: how to improve the dashboard"
- "Party mode: what if we had real-time collaboration?"
- "Creative session: solving the notification spam problem"

---

**THE PARTY HAS STARTED. WHAT SHALL WE BRAINSTORM?**
