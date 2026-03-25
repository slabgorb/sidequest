---
description: Load essential project context at agent activation
---

<purpose>
Quickly load essential context files to reduce agent cold-start overhead.
Automatically invoked on agent activation via `pf agent start`.
</purpose>

<when-to-use>
- Automatically on agent activation (`/sm`, `/tea`, `/dev`, `/reviewer`)
- Manually to refresh context mid-session
- To verify what context is available
</when-to-use>

<execution>

## Running /prime

Use the `pf` CLI:

```bash
# Load all essential context (default)
pf agent start "sm"

# Minimal mode - fastest startup
pf agent start "sm" --minimal

# Full mode - include domain docs
pf agent start "sm" --full

# Skip persona loading
pf agent start "sm" --no-persona

# JSON output (for Cyclist integration)
pf agent start "sm" --json
```

## Options

| Option | Description |
|--------|-------------|
| `--minimal` | Load only CLAUDE.md files (fastest startup) |
| `--full` | Include domain docs from .claude/project/ |
| `--quiet` | Suppress section headers (for automated use) |
| `--agent <name>` | Load agent's sidecar patterns (learned project-specific patterns) |

## What Gets Loaded

Context is loaded in priority order:

### Default Mode
| Priority | Content | Source |
|----------|---------|--------|
| 1 | Project instructions | `CLAUDE.md` |
| 2 | User instructions | `~/.claude/CLAUDE.md` (if exists) |
| 3 | Sprint summary | `sprint/current-sprint.yaml` (key fields only) |
| 4 | Active session | `.session/*-session.md` (first 50 lines) |
| 5 | Agent sidecar | `.pennyfarthing/sidecars/{agent}/*.md` (if `--agent` provided) |
| 6 | Shared context | `.pennyfarthing/guides/agent-behavior.md` (project info - all agents) |
| 7 | Shared behavior | `.pennyfarthing/guides/agent-behavior.md` (protocols - all agents) |
| 8 | Tactical guide | `.pennyfarthing/guides/agent-behavior.md` (for sm, tea, dev, reviewer only) |

### Minimal Mode (`--minimal`)
Only loads CLAUDE.md files (priority 1-2).

### Full Mode (`--full`)
Adds domain documentation from `.claude/project/CLAUDE-*.md` files.

### Agent Sidecar (`--agent <name>`)
When agent name is provided, loads the agent's project-specific patterns from their sidecar directory. This gives agents their learned patterns immediately on activation.

### Agent Behavior Guide (automatic for all agents)
All agents receive the shared context guide which includes project info, directory structure, git strategy, sprint system overview, and build commands.

### Shared Behavior (automatic for all agents)
All agents receive the shared behavior guide which includes confidence protocols, sidecar memory system documentation, reasoning modes, and exit protocols.

### Tactical Guide (automatic for tactical agents)
For tactical agents (sm, tea, dev, reviewer), additionally loads the tactical behavior guide which includes critical patterns for Bash tool usage, session file handling, and handoff protocols.

</execution>

<output-format>

```
# CLAUDE.md
[Project instructions content...]

# ~/.claude/CLAUDE.md (if exists)
[User instructions content...]

---
# Sprint Context
Sprint 7: Benchmark framework expansion, monorepo consolidation, rich agent telemetry
Progress: 62/106 points

---
# Active Session
[First 50 lines of session file...]
```

With `--quiet`, section headers are suppressed.

</output-format>

<integration>

## Python CLI Integration

The `/prime` command is automatically invoked when agents activate:

1. User invokes `/sm`, `/tea`, `/dev`, or `/reviewer`
2. `pf agent start <name>` runs
3. Context is loaded: workflow state, agent definition, persona, behavior guide, sprint context, session, sidecars
4. Agent starts with full context AND their learned patterns loaded

This reduces the "cold start" problem where agents must discover context through multiple file reads.

## Manual Refresh

If context becomes stale mid-session, run `/prime` manually:

```bash
/prime        # Refresh standard context
/prime --full # Include domain docs
```

</integration>

<reference>
- **CLI:** `pf agent start <name>` or `python3 -m pf.cli agent start <name>`
- **Loads:** Workflow state, agent definition, persona, behavior guide, sprint context, session, sidecars
- **Sidecar location:** `.pennyfarthing/sidecars/{agent}/*.md`
- **Behavior guide:** `.pennyfarthing/guides/agent-behavior.md` (all agents)
</reference>
