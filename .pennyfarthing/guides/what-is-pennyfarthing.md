# What Is Pennyfarthing?

A Claude Code agent orchestration framework. It coordinates multiple AI agents through BikeLane workflows — structured phase sequences with quality gates and automatic handoffs.

## Three Pillars

| Pillar | What It Does |
|--------|-------------|
| **Development Platform** | 11 agents hand off work through BikeLane workflows. Phased workflows (TDD, BDD, trivial, agent-docs, patch) drive agents through phases automatically. Stepped workflows (architecture, research, PRD) guide users through gated steps. |
| **Personality Research** | 100 themed persona sets (Discworld, Star Trek, Breaking Bad, etc.) studied for how character traits affect agent behavior. OCEAN profiling, TRAIL error taxonomy, benchmarking. |
| **Integration & Tooling** | Visual dashboards (Frame GUI and TUI panels), Jira sync, sprint tracking, codebase health analysis. |

## How BikeLane Workflows Work

A BikeLane workflow defines a sequence of **phases**, each owned by an **agent**, separated by **gates**.

```
Phase 1 → [gate] → Phase 2 → [gate] → Phase 3 → ...
```

Each agent does its job, writes an assessment, passes the gate, and hands off to the next agent. The workflow YAML defines the order — you can create custom workflows or use built-in ones.

**Phased workflows** (agent-driven): SM sets up the story, agents hand off to each other automatically.

| Workflow | Phases | Use For |
|----------|--------|---------|
| `tdd` | SM → TEA → Dev → Reviewer → SM | Features with test-first design |
| `bdd` | SM → UX → TEA → Dev → Reviewer → SM | User-facing features |
| `trivial` | SM → Dev → Reviewer → SM | Quick fixes, 1-2 point chores |
| `agent-docs` | SM → Orchestrator → Tech Writer → SM | Documentation updates |
| `patch` | Dev → Reviewer → SM | Interrupt-driven bug fixes |

**Stepped workflows** (user-guided): BikeLane walks you through gated steps with prompts.

| Workflow | Use For |
|----------|---------|
| `architecture` | System design documents |
| `research` | Technical or domain research |
| `prd` | Product requirements |

## Key Concepts

| Term | What It Is |
|------|-----------|
| **BikeLane** | Workflow engine — the core of Pennyfarthing. Defines phase order, agents, gates, tandem pairings, and team composition. Every structured task runs through a BikeLane. |
| **Frame** | Dashboard panel viewer — browser (GUI) or terminal (TUI), alongside your Claude Code session |
| **Frame** | Local server powering dashboard panels via API |
| **Prime** | Context loader — assembles agent definition, persona, session state, and sidecar memory |
| **TirePump** | Context clearing — resets conversation when approaching limits |
| **Handoff** | Agent transition — assessment → gate check → phase complete → next agent activates |
| **Tandem** | Background observer — a second agent watches and comments as you work |
| **Sidecar** | Persistent learning file — agents record patterns, gotchas, and decisions across stories |
| **Gates** | Quality checks between phases — tests must pass, reviews must approve |

## Entry Points

| Want to... | Command |
|------------|---------|
| Start or resume work | `/pf-work` |
| See sprint backlog | `/pf-sprint backlog` |
| Check installation health | `/pf-health-check` |
| See all commands | `/pf-help` |

## Display Modes

| Mode | How | For |
|------|-----|-----|
| **CLI only** | `claude` | Agents in your terminal, no dashboard |
| **Frame GUI** | `just gui` + `just claude` | Dashboard in browser, Claude in terminal |
| **Frame TUI** | `pf frame start` or `just tui` + `just claude` | Dashboard in terminal alongside Claude |

## What Pennyfarthing Is NOT

- **Not a code generator.** Agents coordinate work; they use Claude Code for the actual coding.
- **Not an IDE replacement.** It wraps Claude Code's CLI with structured workflows. Use your editor as usual.
- **Not mandatory ceremony.** The `trivial` workflow skips TEA entirely for quick fixes. Scale to fit.
- **Not locked to one theme.** Personas are swappable. Run `/pf-theme set shakespeare` and your SM becomes a different character.

## File Layout

| Path | Purpose |
|------|---------|
| `.pennyfarthing/` | Runtime config and symlinks (don't edit directly) |
| `pennyfarthing-dist/agents/` | Agent behavior definitions |
| `pennyfarthing-dist/guides/` | Component documentation (you are here) |
| `pennyfarthing-dist/workflows/` | BikeLane workflow definitions |
| `pennyfarthing-dist/personas/` | Theme and character files |
| `.session/` | Active work sessions |
| `sprint/` | Sprint tracking YAML |
