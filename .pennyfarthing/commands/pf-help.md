---
description: Context-aware help for Pennyfarthing commands, agents, and workflows
---

<purpose>
Get help with Pennyfarthing commands, agents, themes, and workflows.
Provides quick-start guidance for new users and context-aware suggestions based on current work state.
</purpose>

<quick-start>

## New to Pennyfarthing?

Read the **[What Is Pennyfarthing?](../guides/what-is-pennyfarthing.md)** reference card for a 60-second overview.

Start here:

1. **`/pf-work`** - Smart entry point (resumes existing work or starts new)
2. **`/pf-session new`** - Start a fresh work session from backlog
3. **`/pf-health-check`** - Verify your installation is working

### First Time Setup

If Pennyfarthing isn't installed yet:
```bash
pf setup
```

</quick-start>

<workflow>

## TDD Workflow

Pennyfarthing uses Test-Driven Development with four core agents:

```
SM → TEA → Dev → Reviewer → SM (finish)
```

| Phase | Agent | Command | Role |
|-------|-------|---------|------|
| Setup | SM (Scrum Master) | `/sm` | Story selection, context creation |
| RED | TEA (Test Engineer) | `/tea` | Write failing tests |
| GREEN | Dev (Developer) | `/dev` | Implement to pass tests |
| Review | Reviewer | `/reviewer` | Code review, quality enforcement |
| Finish | SM | `/sm` | Merge PR, archive session |

</workflow>

<commands>

## Resource Groups

Commands are organized by resource. Each group is accessible via both slash commands and CLI.

### Sprint — `/pf-sprint` · `pf sprint`

| Command | Description |
|---------|-------------|
| `/pf-sprint` | Show sprint status |
| `/pf-sprint backlog` | Available stories |
| `/pf-sprint work [id\|next]` | Start work on a story |
| `/pf-sprint archive <id>` | Archive completed story |
| `/pf-sprint plan` | Sprint planning session |
| `/pf-sprint sync` | Sync work with sprint |
| `/pf-sprint story [show\|add\|update\|size\|finish]` | Story operations |
| `/pf-sprint epic [show\|add\|promote\|archive]` | Epic operations |

### Git — `/pf-git` · `pf git`

| Command | Description |
|---------|-------------|
| `/pf-git status` | Check all repo status |
| `/pf-git cleanup` | Organize changes into commits/branches |
| `/pf-git branches <id>` | Create feature branches from story |
| `/pf-git release` | Interactive release workflow |

### Session — `/pf-session` · `pf session`

| Command | Description |
|---------|-------------|
| `/pf-session new` | Start next available story |
| `/pf-session continue` | Resume from checkpoint |

### Epic — `/pf-epic` · `pf epic`

| Command | Description |
|---------|-------------|
| `/pf-epic start <id>` | Start epic for development |
| `/pf-epic close <id>` | Close completed epic |

### Jira — `/pf-jira` · `pf jira`

| Command | Description |
|---------|-------------|
| `/pf-jira view <key>` | View issue details |
| `/pf-jira claim <key>` | Claim issue |
| `/pf-jira sync <epic-id>` | Sync YAML to Jira |
| `/pf-jira sync-epic` | Sync epic to Jira |
| `/pf-jira reconcile` | Report mismatches |

### Theme — `/pf-theme` · `pf theme`

| Command | Description |
|---------|-------------|
| `/pf-theme list` | List all themes |
| `/pf-theme show [name]` | Show theme details |
| `/pf-theme set <name>` | Set active theme |
| `/pf-theme create <name>` | Create custom theme |
| `/pf-theme maker` | Interactive theme wizard |

### Workflow — `/pf-workflow` · `pf workflow`

| Command | Description |
|---------|-------------|
| `/pf-workflow` | List available workflows |
| `/pf-workflow show` | Current workflow details |
| `/pf-workflow start <name>` | Start stepped workflow |
| `/pf-workflow resume` | Resume workflow |

## Agents (11)

| Agent | Command | Role |
|-------|---------|------|
| SM | `/sm` | Scrum Master — Story coordination, sprint management |
| TEA | `/tea` | Test Engineer — Test strategy, TDD design |
| Dev | `/dev` | Developer — Implementation, feature shipping |
| Reviewer | `/reviewer` | Code Reviewer — Quality enforcement |
| Architect | `/architect` | System Architect — Technical design |
| PM | `/pm` | Product Manager — Strategic planning |
| DevOps | `/devops` | DevOps — Infrastructure and deployment |
| Tech-Writer | `/tech-writer` | Technical Writer — Documentation |
| UX-Designer | `/ux-designer` | UX Designer — User experience |
| Orchestrator | `/orchestrator` | Orchestrator — Multi-agent coordination |
| BA | `/ba` | Business Analyst — Requirements discovery |

## Utilities

| Command | Description |
|---------|-------------|
| `/pf-work` | Smart entry point — resume or start new |
| `/pf-check` | Run quality gates before handoff |
| `/pf-prime` | Load project context at agent activation |
| `/pf-health-check` | Check installation health |
| `/pf-setup` | First-time project setup |
| `/pf-chore` | Quick commit for small changes |
| `/pf-patch` | Bug fix during active story work |
| `/pf-standalone` | Wrap changes into standalone story |
| `/pf-ci run` | Detect and run CI locally |
| `/pf-docs update` | Update domain documentation |

## Benchmarking

| Command | Description |
|---------|-------------|
| `/pf-benchmark` | Compare performance against baseline |
| `/pf-benchmark-control` | Create control baseline |
| `/pf-job-fair` | Discover best characters per role |
| `/pf-solo` | Single agent rubric scoring |

## Creative

| Command | Description |
|---------|-------------|
| `/pf-party-mode` | Creative brainstorming with all agents |
| `/pf-brainstorming` | Structured problem-solving session |
| `/pf-retro` | Sprint retrospective |

</commands>

<themes>

## Themes

Pennyfarthing agents adopt personas from themed character sets. There are **102 themes** available.

### Popular Themes

| Theme | Description |
|-------|-------------|
| `rome` | Characters from HBO's Rome series |
| `star-trek-tos` | Original Star Trek series characters |
| `star-trek-tng` | Star Trek: The Next Generation characters |
| `discworld` | Terry Pratchett's Discworld characters |
| `shakespeare` | Shakespearean characters |
| `jane-austen` | Jane Austen novel characters |
| `breaking-bad` | Breaking Bad characters |
| `battlestar-galactica` | Battlestar Galactica characters |

Run `/pf-theme list` to see all 102 available themes.

</themes>

<context-aware>

## Context-Aware Help

Based on your current state, here's what you might need:

### No Active Session
- Use `/pf-work` or `/pf-session new` to begin
- Check `/pf-health-check` if first time

### In Dev Phase
- Run `/pf-check` before handoff
- Then `/reviewer` for code review

### In Review Phase
- Reviewer will approve or reject
- Then `/sm` to finish the story

### Between Stories
- `/pf-work` to pick up next story
- `/pf-sprint plan` for planning session

</context-aware>

<reference>

## CLI Help

For detailed help on any command group:
```bash
pf help           # Overview of all groups
pf help sprint    # Sprint commands
pf help git       # Git commands
pf help session   # Session commands
pf help epic      # Epic commands
```

## Documentation

- **Project Setup:** `CLAUDE.md`
- **Sprint Status:** `sprint/current-sprint.yaml`
- **Active Session:** `.session/*-session.md`
- **Agent Definitions:** `pennyfarthing-dist/agents/*.md`
- **Command Definitions:** `pennyfarthing-dist/commands/*.md`
- **Command Registry:** `pennyfarthing-dist/command-registry.yaml`
- **Theme Files:** `pennyfarthing-dist/personas/themes/*.yaml`
- **Guides:** `.pennyfarthing/guides/*.md`

</reference>
