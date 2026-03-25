---
name: peloton
description: |
  Agent team mode for story workflows. Uses Claude Code native agent teams
  (TeamCreate / SendMessage / TeamDelete) with teammateMode tmux for persistent
  panes per agent role. SM is the team lead, orchestrating Architect, TEA, Dev,
  and Reviewer as teammates.
args: "[start|status|stop]"
---

# /pf-peloton - Agent Team Mode

Run a full agent team through a story workflow using Claude Code's native agent teams.

<run>
pf peloton start
</run>

## Commands

### `/pf-peloton` or `/pf-peloton start`

Initialize peloton team for the current story. Reads the workflow and outputs a TeamCreate prompt for SM.

```bash
pf peloton start [--story-id ID] [--workflow NAME]
```

<args>
| Arg | Required | Description |
|-----|----------|-------------|
| `--story-id` | No | Story ID (default: from session) |
| `--workflow` | No | Workflow name (default: from session) |
</args>

---

### `/pf-peloton status`

Show current peloton team state.

```bash
pf peloton status [--json]
```

---

### `/pf-peloton stop`

Clear peloton state and clean up.

```bash
pf peloton stop
```

## Concept

**Peloton** = the cycling term for the main group riding together. In Pennyfarthing,
SM creates a team of agent teammates — each in a persistent tmux pane — and
orchestrates them through the story workflow.

## Prerequisites

Enable agent teams (one-time):
```json
// .claude/settings.json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "teammateMode": "tmux"
}
```

## Cold Start

```bash
just start          # tmux: Claude Code + TUI + Frame
```
Then in Claude Code, SM picks a story and starts peloton:
```bash
pf agent start "sm"         # SM picks story, creates session
pf peloton start            # SM creates team, spawns agent panes
```

## How It Works

1. `pf peloton start` reads the story's workflow and outputs a `TeamCreate` prompt
2. SM executes `TeamCreate` — teammates spawn in tmux panes (Architect, TEA, Dev, Reviewer)
3. SM dispatches work via `SendMessage` to each teammate in sequence
4. Each teammate loads its agent definition, reads the session file, does its phase work
5. SM reads results, decides next routing — can go back to any teammate
6. When Reviewer approves, SM runs finish flow (PR, merge, archive)
7. `pf peloton stop` + `TeamDelete` to clean up

## Quick Reference

| Command | CLI | Purpose |
|---------|-----|---------|
| `/pf-peloton` | `pf peloton start` | Initialize state, output TeamCreate prompt |
| `/pf-peloton start` | `pf peloton start [--story-id X-Y --workflow tdd]` | Initialize with explicit values |
| `/pf-peloton status` | `pf peloton status [--json]` | Show active team, agents |
| `/pf-peloton stop` | `pf peloton stop` | Clear peloton state file |

## SM Orchestration Flow

SM stays in the MAIN pane and uses `SendMessage` to drive agents:

```
Architect → TEA (RED) → Dev (GREEN) → TEA (verify) → Reviewer
                                                        ↓
                                          Issues? → route back to Dev/TEA/Architect
                                          Clean?  → SM finish flow
```

SM can re-enter any teammate at any time. Teammates are persistent — context preserved.

## State

Peloton state at `.pennyfarthing/peloton-state.json`:

```json
{
  "active": true,
  "story_id": "148-12",
  "workflow": "tdd",
  "team_name": "peloton-148-12",
  "agents": ["architect", "tea", "dev", "reviewer"]
}
```

## Replay Mode (Benchmarking)

For benchmarking the pipeline against known scenarios, use the separate replay harness:

```bash
pf benchmark replay run scenarios/dpgd-116.yaml --theme firefly --n 4
```

See `guides/peloton.md` for the full replay methodology and scoring.

## Related

- `guides/peloton.md` — full guide with cold start walkthrough, replay mode, scoring
- `pf benchmark replay` — benchmark harness
