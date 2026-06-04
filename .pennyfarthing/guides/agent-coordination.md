# Pennyfarthing Agent Coordination Architecture

> Architectural reference for how agents coordinate. For runtime behavior protocol, see `agent-behavior.md`.

## Overview

This document describes how Pennyfarthing agents are coordinated. The framework supports both single-repo and multi-repo projects.

**Key Principle:** State detection via session files, phase transitions via `pf handoff` CLI, handoff markers route to the next agent.

## The TDD Flow

SM → TEA → Dev → Reviewer → SM (setup → red → green → review → finish)

**Entry points:** `/pf-sprint work` (smart resume/start) or `/pf-session new` (explicit new story)
**State detection:** Agents read session file on activation — `**Phase:**`, `**Workflow:**`, `**Repos:**`
**Phase transitions:** Agents drive exit directly using `pf handoff` CLI (no handoff subagent)
**Finish:** SM handles when status = `approved`

## Architecture Principles

### 1. Single Source of Truth
- **Agent definitions:** `.pennyfarthing/agents/`
- **Subagent prompts:** `.pennyfarthing/agents/`
- **Scope configuration:** `.pennyfarthing/project/docs/agent-scopes.yaml`
- **Sprint tracking:** `sprint/current-sprint.yaml`
- **Session state:** `.session/{STORY_ID}-session.md`

### 2. Hierarchical Agent Structure
```
Strategic Agents (Full Scope)
├── orchestrator  → Orchestrates everything
├── pm           → Plans across all repos
├── architect    → Designs across all repos
└── devops       → Infrastructure and deployment

Tactical Agents (Story-Scoped) - THE TDD FLOW
├── sm           → Story setup and finish
├── tea          → Write failing tests (RED)
├── dev          → Implement to GREEN, create PR
└── reviewer     → Adversarial code review

Support Agents
├── tech-writer  → Documentation
└── ux-designer  → UI design
```

### 3. Context Loading Strategy
- **Strategic agents** load full project context (both repos)
- **Tactical agents** load only target repo context based on active story
- **Context budget** kept under 500-800 lines per agent
- **Lazy loading** - load docs only when specific task requires them

## Directory Structure

```
/$PROJECT_ROOT/
├── .pennyfarthing/                       # Pennyfarthing coordination directory (symlinks to node_modules)
│   ├── agents/                         # Agent definitions (symlinks to pennyfarthing-dist)
│   │   ├── orchestrator.md             # Master orchestrator
│   │   ├── pm.md                       # Product Manager
│   │   ├── sm.md                       # Scrum Master (+ sm-*.md subagents)
│   │   ├── architect.md                # System Architect
│   │   ├── dev.md                      # Developer
│   │   ├── tea.md                      # Test Engineer
│   │   ├── reviewer.md                 # Code Reviewer (+ reviewer-preflight.md)
│   │   ├── tech-writer.md              # Technical Writer
│   │   ├── ux-designer.md              # UX Designer
│   │   └── devops.md                   # DevOps Engineer
│   │
│   ├── commands/                       # Slash commands (symlinks)
│   ├── guides/                         # Behavior guides (symlinks)
│   ├── skills/                         # Knowledge domain skills (symlinks)
│   ├── scripts/                        # Utility scripts (symlinks)
│   │
│   ├── project/                        # Project-specific overrides
│   │   ├── agents/                     # Agent sidecars (patterns, gotchas, decisions)
│   │   └── commands/                   # Custom project commands
│   │
│   ├── sidecars/                       # Agent learning files (local, writable)
│   ├── config.local.yaml               # Theme, bell_mode, relay_mode, permission_mode
│   └── persona-config.yaml             # Project default theme (shared with team)
│
├── .session/                           # Active work sessions
│   └── {story-id}-session.md           # Session files (one per story)
│
├── sprint/                             # Sprint tracking
│   ├── current-sprint.yaml             # Active sprint and stories
│   ├── context/                        # Epic technical context
│   ├── archive/                        # Completed sprints
│   └── sidecars/                       # Agent learning files
│
└── pennyfarthing-dist/                 # Source of truth (if Pennyfarthing project itself)
    ├── agents/                         # 11 main agents + 6 subagents
    ├── commands/                       # Slash commands
    ├── guides/                         # Behavior guides and patterns
    ├── skills/                         # Knowledge domain skills
    ├── personas/themes/                # Themed personas
    └── scripts/                        # Utility scripts
```

## Agent Types

### Strategic Agents (Full Scope)

**Characteristics:**
- See entire project (both repos)
- Load all context on activation
- Make cross-repo decisions
- Coordinate work across repos

**Agents:**
- **Orchestrator:** Orchestrates all agents and workflows
- **PM:** Plans sprints, prioritizes epics, manages backlog
- **SM:** Creates stories, adds technical context, validates readiness
- **Architect:** Makes design decisions, defines patterns, ensures consistency

**Context Loading:**
```yaml
On Activation:
  1. sprint/current-sprint.yaml     # Full sprint status
  2. API/.claude/context.md         # API context
  3. UI/.claude/context.md          # UI context
  4. API/docs/epics.md              # Epic definitions (PM only)
  5. .session/{STORY_ID}-session.md # Active work
```

### Tactical Agents (Story-Scoped)

**Characteristics:**
- Focus on specific repo(s)
- Load context based on active story
- Implement/test/document specific features
- Narrow, deep expertise

**Agents:**
- **Dev:** Implements features in target repo
- **TEA:** Tests features in target repo
- **Tech Writer:** Documents features in target repo
- **UX Designer:** Designs UI interfaces (UI only)

**Context Loading:**
```yaml
On Activation:
  1. sprint/current-sprint.yaml     # Current sprint (story section)
  2. .session/{STORY_ID}-session.md # Active story
  3. Determine target repo from story "Repos:" field
  4. Load target repo context:
     - If API:  API/.claude/context.md
     - If UI:   UI/.claude/context.md
     - If Both: Load both contexts
```

## Context Files

### Base Directory Context

#### `sprint/current-sprint.yaml`
**Purpose:** Unified sprint tracking for all stories
**Size:** ~100-200 lines
**Loaded By:** All agents
**Content:**
- Sprint goals
- All stories (API, UI, Both)
- Story status (backlog, in-progress, review, done)
- Story metadata (repos, priority, points, files)

#### `.session/{STORY_ID}-session.md`
**Purpose:** Current work session context
**Size:** ~50-100 lines
**Loaded By:** All agents
**Content:**
- Active story ID
- Target repo(s)
- Story context
- Progress notes
- Done checklist

### Repository Context

#### `API/.claude/context.md`
**Purpose:** API-specific patterns and structure
**Size:** ~30-50 lines
**Loaded By:** Strategic agents + Dev/TEA when working on API

#### `UI/.claude/context.md`
**Purpose:** UI-specific patterns and structure
**Size:** ~30-50 lines
**Loaded By:** Strategic agents + Dev/TEA/UX when working on UI

## Agent Activation Protocol

### Step 1: Load Agent Definition
```
Read: .pennyfarthing/agents/[agent].md
Identify: Strategic or Tactical agent type
```

### Step 2: Load Base Context
```
Load files from agent-scopes.yaml:
  - Sprint status
  - Active work (if exists)
  - Repo contexts (based on agent type)
```

### Step 3: Determine Scope (Tactical Agents Only)
```
Read: .session/{STORY_ID}-session.md
Extract: "Repos:" field (API|UI|Both)
Load: Appropriate repo context
```

### Step 4: Present Ready State
```
Display: Agent persona and menu
Show: Loaded context summary
Ready: For user input
```

## Agent Handoffs (TDD Flow)

Phase transitions are driven by the active agent using `pf handoff` commands directly — no dedicated handoff subagent. Each agent runs the exit protocol when their phase is complete.

### The Flow

```
SM → TEA → Dev → Reviewer → SM
```

### Exit Protocol (All Tactical Agents)

```
1. Write assessment to session file
2. pf handoff resolve-gate {story-id} {workflow} {phase}
   ├── blocked → report error, STOP
   ├── skip    → jump to step 4
   └── ready   → spawn gate subagent → GATE_RESULT
       ├── fail → fix issues, retry (max 3)
       └── pass → continue
3. pf handoff complete-phase {story-id} {workflow} {from} {to} {gate-type}
4. pf handoff marker {next-agent} → emit marker → EXIT
```

See `handoff-cli.md` for full command reference and `gates.md` for gate file format.

### SM → TEA (Story Setup)
**Trigger:** User selects story to start
**Action:** SM runs `sm-setup` subagent (MODE=setup) to claim Jira, write session file, create branches
**Exit:** SM runs exit protocol → `pf handoff marker tea`

### TEA → Dev (Tests Written)
**Trigger:** TEA completes failing tests (RED phase)
**Exit:** TEA runs exit protocol → `pf handoff complete-phase {id} {workflow} red green tests_fail` → `pf handoff marker dev`

### Dev → Reviewer (Implementation Complete)
**Trigger:** Dev creates PR with passing tests (GREEN phase)
**Exit:** Dev runs exit protocol → `pf handoff complete-phase {id} {workflow} green review tests_pass` → `pf handoff marker reviewer`

### Reviewer → SM (Approved)
**Trigger:** Reviewer approves PR
**Exit:** Reviewer runs exit protocol → `pf handoff complete-phase {id} {workflow} review finish approved` → `pf handoff marker sm`

### Reviewer → Dev (Rejected)
**Trigger:** Reviewer finds issues requiring changes
**Exit:** Reviewer runs exit protocol → routes back to implement phase → `pf handoff marker dev`

### SM → Done (Finish)
**Trigger:** Status = `approved`
**Action:** SM runs `sm-finish` subagent (PHASE=execute) — archives session, creates summary, updates sprint YAML, syncs Jira

### Wrong Phase Detection

On activation, any agent can verify they own the current phase:

```bash
pf handoff phase-check {your_agent_name}
```

If result has `action: "redirect"`, the agent emits a marker to the correct phase owner and exits without doing any work.

## Complete Subagent Inventory

Subagents are lightweight Haiku-based agents for mechanical tasks. Invoked via `Task tool`.

| Subagent File | Purpose | Model |
|--------------|---------|-------|
| `sm-setup.md` | Research backlog (MODE=research) or setup story (MODE=setup) | haiku |
| `sm-finish.md` | Preflight checks (PHASE=preflight) or execute finish (PHASE=execute) | haiku |
| `sm-file-summary.md` | Summarize file changes for commits | haiku |
| `reviewer-preflight.md` | Pre-flight checks before review | haiku |
| `testing-runner.md` | Run tests and report results | haiku |
| `tandem-backseat.md` | Background observer for tandem mode | haiku |

## Support Agent Handoffs

### Any → Architect
**Trigger:** Need design decisions or architectural guidance
**Context:** Technical problem or design question
**Action:** Architect provides design and implementation guidance

### Any → Tech Writer
**Trigger:** Feature needs documentation
**Context:** Implemented feature
**Action:** Tech Writer creates documentation

### Any → UX Designer
**Trigger:** Feature needs UI design
**Context:** User story and requirements
**Action:** UX Designer creates UI design and specs

## Context Budget Management

### Target Budgets
- **Agent file:** 200-400 lines
- **Sprint status:** 100-200 lines (full) or 50 lines (story section)
- **Repo contexts:** 30-50 lines each
- **Active work:** 50-100 lines
- **Total per agent:** 500-800 lines

### Strategic Agent Budget
```
PM Agent Example:
  - pm.md:                    200 lines
  - current-sprint.yaml:      150 lines
  - API/context:               30 lines
  - UI/context:                30 lines
  - epics.md (summary):       100 lines
  - active work:               50 lines
  Total:                      560 lines ✓
```

### Tactical Agent Budget
```
Dev Agent Example (API story):
  - dev.md:                   300 lines
  - current-sprint (story):    50 lines
  - API/context:               30 lines
  - active work:               50 lines
  Total:                      430 lines ✓
```

## Benefits

### Single Source of Truth
- All agents defined in one place
- No duplicate or conflicting agent files
- Easy to update and maintain

### Coordinated Planning
- Strategic agents see full project scope
- Unified sprint tracking
- Clear cross-repo dependencies

### Focused Implementation
- Tactical agents load only what they need
- Reduced context overhead
- Faster agent activation

### Clear Hierarchy
- Strategic agents coordinate
- Tactical agents execute
- Clean handoffs between agents

## Architecture History

### Previous Architecture (Pre-December 2025)
- Separate commands: `/pf-session new`, `/pickup-work`, `/handoff-work`, `/finish-work`
- Manual handoff documentation
- No subagent extraction

### Intermediate Architecture (January 2026)
- Smart entry point: `/pf-work` (resumes or starts new)
- State detection via session file in `.session/`
- Handoffs via dedicated Haiku subagents (`handoff.md`, `sm-handoff.md`)
- 100 themed personas for agent personality

### Current Architecture
- Entry: `/pf-sprint work` or `/pf-session new`
- Session file drives state: `**Phase:**`, `**Workflow:**`, `**Repos:**`
- Agents drive their own exit via `pf handoff` CLI — no handoff subagent
- Exit sequence: write assessment → `resolve-gate` → `complete-phase` → `marker` → EXIT
- Wrong-phase detection via `pf handoff phase-check`
- 6 active subagents for mechanical tasks (sm-setup, sm-finish, sm-file-summary, reviewer-preflight, testing-runner, tandem-backseat)

## Research Tools

Agents have access to two external research tools via MCP for combating training data staleness. Use them to verify library APIs, check for breaking changes, and ground decisions in current documentation.

### Context7 (Library Documentation)

Context7 provides versioned, semantically-searched documentation for public libraries. Two tools:

1. **`resolve-library-id`** — Maps a package name to a Context7 library ID. Always call this first.
2. **`query-docs`** — Retrieves current documentation and code examples for a resolved library ID.

**Two-step lookup pattern:** Always `resolve-library-id` first, then `query-docs`. Never call `query-docs` without a valid library ID.

**Three-call limit:** Do not call Context7 tools more than 3 times per question. Resolve once, query up to twice.

**Internal tool carve-out:** Context7 indexes external/public libraries only. Internal tools (`pf` CLI, `@pennyfarthing/*` packages, project-specific code) are NOT in Context7. Use training data, skill docs, and guides for internal APIs.

**Graceful degradation:** If Context7 is unavailable or `resolve-library-id` returns no matches, proceed with training data knowledge. Note "Context7 unavailable — using training data" in your work. Do NOT block, retry in a loop, or ask the user to fix MCP configuration.

### Perplexity (Web Research)

Perplexity provides real-time web intelligence for broader knowledge needs. Four tools with different speed/depth tradeoffs:

| Tool | Speed | Best For |
|------|-------|----------|
| `perplexity_search` | Fast | URLs, changelogs, release notes |
| `perplexity_ask` | Fast | Quick factual Q&A (default choice) |
| `perplexity_reason` | Medium | Trade-off analysis, logical problems |
| `perplexity_research` | Slow (2-4 min) | Deep multi-source investigation (Architect only) |

**Speed-tier routing:** Default to `perplexity_ask` — it's fast and handles most questions. Escalate only when needed:
1. `perplexity_ask` — First choice for any factual question ("does X support Y?", "what changed in v3?")
2. `perplexity_search` — When you need specific URLs, changelogs, or release notes
3. `perplexity_reason` — When you need step-by-step analysis or trade-off comparison
4. `perplexity_research` — Deep multi-source investigation. **Architect only.** Takes 2-4 minutes. Never use for quick lookups.

**Scope restriction:** Queries must relate to the active story or task. No open-ended browsing or curiosity-driven research.

**Graceful degradation:** If Perplexity is unavailable or returns errors, proceed with training data knowledge and note "Perplexity unavailable — proceeding with training data" in your assessment. Do NOT block, retry in a loop, or ask the user to fix MCP configuration.

### Routing: Which Tool for Which Need?

| Information Need | First Try | Escalate To | Never Use |
|-----------------|-----------|-------------|-----------|
| Current API signature for known library | Context7 `query-docs` | Perplexity `perplexity_ask` | `perplexity_research` |
| "Does library X support feature Y?" | Context7 `query-docs` | Perplexity `perplexity_ask` | — |
| Best practice for general pattern | Perplexity `perplexity_ask` | `perplexity_reason` | Context7 (not library-specific) |
| Comparing two technologies | Perplexity `perplexity_reason` | `perplexity_research` (Architect only) | Context7 (single-library tool) |
| Finding a library for a task | Perplexity `perplexity_search` | `perplexity_ask` | Context7 (need name first) |
| Known vulnerabilities / CVEs | Perplexity `perplexity_ask` | `perplexity_search` | Context7 (not security-focused) |
| Error diagnosis (unfamiliar error) | Perplexity `perplexity_ask` | Context7 if library-specific | `perplexity_research` |
| Internal tool documentation (`pf` CLI) | Training data / skill docs | — | Context7 or Perplexity (not indexed) |

### Shared Principles

- **Citation discipline:** Decisions informed by research get a citation in session file or commit message.
- **Scoped queries:** Queries must relate to the active story/task. No open-ended browsing.
- **Trust but verify:** Research output informs decisions but is never ground truth. Always run the code.
- **Graceful degradation:** If either tool is unavailable, proceed with training data and note the gap.
- **Subagent exclusion:** Subagents (haiku model) should NOT use Context7 or Perplexity. MCP round-trips on mechanical tasks are waste. Only strategic agents (Opus) use research tools.

## Commands Reference

```bash
# Entry points
/pf-sprint work     # Smart entry - resume or start new
/pf-session new     # Explicitly start new story

# TDD Flow agents
/pf-sm              # Scrum Master (setup + finish)
/pf-tea             # Test Engineer (RED phase)
/pf-dev             # Developer (GREEN phase)
/pf-reviewer        # Code Reviewer

# Support agents
/pf-architect       # Architecture design
/pf-tech-writer     # Documentation
/pf-ux-designer     # UI/UX design
/pf-devops          # Infrastructure

# Utility
/pf-check           # Run quality gates before handoff
/pf-chore           # Quick commit for small changes
/pf-git             # Git operations
```

---

**State detection. pf handoff CLI. Themed personas.**
