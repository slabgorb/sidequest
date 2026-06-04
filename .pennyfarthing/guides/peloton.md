# Peloton Guide

Peloton has two modes: **live mode** for real story work and **replay mode** for benchmarking.

## Live Mode

Live mode uses **Claude Code native agent teams** to run a story through the full pipeline. SM is the team lead. Each agent (Architect, TEA, Dev, Reviewer) is a persistent teammate with its own tmux pane. SM orchestrates the flow — dispatching work, reading results, routing back to agents as needed.

### Prerequisites

Enable agent teams (one-time setup):
```json
// .claude/settings.json or .pennyfarthing/config.local.yaml
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "teammateMode": "tmux"
}
```

### Cold Start → Peloton (step by step)

**1. Start the environment** (from a regular terminal):
```bash
just start
```
Launches tmux with Claude Code + TUI + Frame server. You land in the Claude Code pane — this becomes the **MAIN** pane where SM runs.

**2. Activate SM and pick a story:**
```
/pf-sm
```
SM checks the backlog, you pick a story, SM claims it in Jira, creates the session file, and sets up the workflow.

**3. Start peloton:**
```
/pf-peloton
```
SM calls `TeamCreate` to spawn teammates: Architect, TEA, Dev, Reviewer. With `teammateMode: "tmux"`, each teammate automatically gets its own tmux pane. Each teammate is a full, independent Claude Code instance loaded with its agent definition.

```
┌──────────────────────────────────────────────┐
│  MAIN (SM)  │  ARCHITECT  │  TEA             │
│  team lead   │             │                  │
│  orchestrates├─────────────┼──────────────────┤
│              │  DEV        │  REVIEWER        │
│              │             │                  │
└──────────────┴─────────────┴──────────────────┘
  + TUI pane (bottom or side, per layout preference)
```

**4. SM orchestrates the flow:**

SM dispatches work to teammates via `SendMessage` and the shared task list:

1. SM sends task to **Architect** → designs the approach, writes to session file
2. SM reads result, sends task to **TEA** → writes failing tests (RED)
3. SM reads result, sends task to **Dev** → makes tests pass (GREEN)
4. SM reads result, sends task to **TEA** again → verifies tests
5. SM reads result, sends task to **Reviewer** → adversarial code review
6. If Reviewer flags issues → SM routes back to Dev, TEA, or Architect as needed
7. Loop until Reviewer approves

SM decides routing based on each agent's output. The agents gate themselves (each runs its own exit checks), but SM controls sequencing and re-entry. You can also click into any teammate's pane to interact with them directly.

**5. Finish:**
SM runs the finish flow — creates PR, merges, archives session, updates Jira. Calls `TeamDelete` to clean up.

### Key design points

- **Native agent teams:** Uses Claude Code's built-in `TeamCreate` / `SendMessage` / `TeamDelete`. Each teammate is an independent Claude Code instance with its own context window and tmux pane. No custom pane management needed.
- **SM is the team lead:** SM creates the team, dispatches tasks, reads results, decides routing. No linear state machine — SM controls the flow based on agent output.
- **Persistent teammates:** Teammates stay alive for the duration of the story. Context is preserved across re-entries. SM can `SendMessage` to any teammate at any time.
- **Session file is the coordination layer:** All agents read from and write to the same session file. SM doesn't relay content — agents pick it up from the file.
- **Re-entry is natural:** If Reviewer says "tests are wrong," SM sends a message to TEA. TEA is still alive with its full context, picks up from where it left off.
- **Human can interact directly:** Click into any teammate's tmux pane to give additional instructions, ask questions, or redirect their approach.

| Command | Purpose |
|---------|---------|
| `pf peloton start` | SM creates team, spawns teammates, initializes state |
| `pf peloton status` | Show active team, teammates, current task |
| `pf peloton stop` | `TeamDelete`, clean up state |

The `pf peloton` CLI is thin — it sets up the story context and triggers SM to use native team tools. The heavy lifting is Claude Code's agent teams.

---

## Replay Mode (Benchmarking)

## What is a Peloton Test?

A peloton test is a **repeatable benchmark scenario** that measures how well a team of AI agents performs on real-world code review tasks. The name follows Pennyfarthing's bicycle metaphor — a peloton is the main group in a cycling race, where riders work together as a unit.

Each peloton test:

1. **Starts from a real PR** that was reviewed by a human
2. **Uses the reviewer's actual findings** as ground truth — these are things the AI pipeline missed
3. **Replays the full TDD pipeline** (TEA → Dev → Reviewer) against the same code
4. **Scores the result** by comparing what the pipeline caught vs. what the human found

The key insight: **we are not making up test cases.** Every finding in a peloton scenario is something a real reviewer flagged on a real pull request that our pipeline approved and shipped. The question is: can we do better?

## How Peloton Tests Are Created

### The Discovery Cycle

Peloton scenarios emerge naturally from the development process:

```
Developer writes code with AI pipeline (TEA → Dev → Reviewer)
    → Pipeline approves the PR
    → External reviewer reviews the PR
    → Reviewer finds issues the pipeline missed
    → Those findings become the ground truth for a new peloton scenario
```

### What Makes a Good Ground Truth Finding

Not every comment from a reviewer becomes a ground truth finding. We include:

- **Critical issues** — security vulnerabilities, data loss, silent failures
- **Important issues** — pattern violations, test quality gaps, missing validation

We exclude:

- **Suggestions** — style preferences, nice-to-haves
- **Tech debt** — future improvements, refactoring ideas

Each finding is tagged with:

| Field | Purpose |
|-------|---------|
| `id` | Short identifier (C1, I1, I2...) |
| `severity` | critical or important |
| `weight` | Score points (higher = more impactful) |
| `category` | security, testing, build, etc. |
| `phase_ideal` | Which pipeline phase *should* have caught this |
| `files` | Where in the code the issue lives |
| `description` | What the issue is and why it matters |

### Available Scenarios

| Scenario | Story | Findings | Weight | Source |
|----------|-------|----------|--------|--------|
| **DPGD-116** | 6.1 CLI Framework | 7 (1C + 6I) | 37 | External first-pass review |
| **DPGD-117** | 8.1 REST API Foundation | 10 (0C + 8I + 2 regression) | 52 | External first-pass + re-review |

## Running Peloton Tests

### Prerequisites

- `pf` CLI installed globally (`uv tool install -e pennyfarthing/`)
- Access to the target repo (the code under test)
- Run from a **regular terminal** — not from inside Claude Code (nested `claude -p` is blocked)
- A Claude Max Pro account (benchmark runs are expensive — ~$2-5 per pipeline run)

### Basic Usage

```bash
# Run one pipeline with the control theme (no persona)
pf benchmark replay run scenarios/dpgd-116.yaml --model sonnet --n 1

# Run with a persona theme
pf benchmark replay run scenarios/dpgd-116.yaml --theme firefly --model sonnet --n 4

# Skip scoring (just run the pipeline, judge later)
pf benchmark replay run scenarios/dpgd-116.yaml --theme discworld --n 4 --skip-score

# Keep the git worktree for manual inspection
pf benchmark replay run scenarios/dpgd-116.yaml --n 1 --keep-worktree
```

### Multi-Judge Scoring

A single LLM judge is noisy. We run 3 judges per run and take a majority vote:

```bash
# Add judge passes to reach 3 judges per run
pf benchmark replay judge scenarios/dpgd-116.yaml --target-judges 3

# Only judge one theme
pf benchmark replay judge scenarios/dpgd-116.yaml --theme firefly --target-judges 3
```

This produces per-run files:
- `score.yaml` — initial judge
- `judge_1.yaml`, `judge_2.yaml` — additional passes
- `majority_vote.yaml` — consensus (2-of-3 or better)

### Comparing Themes

```bash
pf benchmark replay compare scenarios/dpgd-116.yaml
```

Prints a detection heatmap showing which findings each theme catches and by which phase.

### OTEL Telemetry

If Frame (Frame server) is running, benchmark runs auto-detect it and send OTEL traces for tool-use timing analysis:

```bash
# Explicit endpoint
pf benchmark replay run scenarios/dpgd-116.yaml --otel-endpoint http://localhost:3456

# Auto-detect from running Frame (reads .frame-port)
pf benchmark replay run scenarios/dpgd-116.yaml
# Output: [OTEL] Auto-detected Frame at http://localhost:3456
```

## How a Run Works

Each `pf benchmark replay run` does the following:

```
1. Load scenario YAML (findings, commit, phase prompts)
2. Create a git worktree at the scenario's base commit
3. For each phase (TEA → Dev → Reviewer):
   a. Run `pf agent start <role>` to get the production-faithful prompt
   b. Write CLAUDE.md into the worktree (agent def + epic + story context)
   c. Run `claude -p "<task prompt>" --output-format json` in the worktree
   d. Capture output, tokens, model, cost, session_id
4. Score with LLM judge against ground truth findings
5. Save results: per-phase output, pipeline.yaml, score.yaml
6. Clean up worktree
```

The prompt each agent receives is the **same prompt it would get in production** — extracted from `pf agent start` with workflow/sprint noise stripped. The only variable between runs is the persona theme.

## Results So Far

### DPGD-116: 33 themes, 152 pipeline runs

The DPGD-116 scenario has been run with 33 different persona themes (plus a control baseline) at N=4 each, with 3-judge majority voting.

**Control baseline (N=11):** 49.5% mean detection rate (bimodal — some runs get 67.6%, others 40.5%).

**Finding detection patterns:**

| Finding | What It Is | Detection Rate | Caught By |
|---------|-----------|----------------|-----------|
| C1 | Silent error swallowing (config) | ~30% | Varies |
| I1 | CWE-209 error exposure | ~80% | TEA (writes security tests) |
| I2 | CWE-113 header injection | ~85% | TEA (writes injection tests) |
| I3 | Workspace dep violations | ~10% | Rarely caught |
| I4 | Secret left on disk | ~70% | TEA or Reviewer |
| I5 | Vacuously true test | ~15% | Rarely caught |
| I6 | Zero-assertion test | ~15% | Rarely caught |

Key observations:

- **Security issues (I1, I2, I4) are well-caught** — the pipeline is good at CWE-class vulnerabilities
- **Build/pattern issues (I3) are nearly invisible** — agents don't check Cargo.toml workspace rules
- **Test quality issues (I5, I6) are hard** — the pipeline writes its own tests and rarely questions them
- **C1 is the diagnostic finding** — catching it requires understanding error-handling philosophy, not just pattern matching

### What We've Learned

1. **Persona themes don't dramatically change detection rates** — most themes score within ±10% of control. The pipeline's ceiling is set by the agent definitions and prompts, not the character voice.

2. **Detection profiles differ by persona** — while total scores are similar, different themes catch different subsets of findings. Firefly catches CORS issues more often; Discworld catches type-safety issues more often.

3. **The TEA phase is the most impactful** — findings caught by TEA (via tests that would fail) are caught reliably. Findings that depend on the Reviewer flagging them are caught less consistently.

4. **Some findings are structurally invisible** — I3 (workspace deps) requires checking build configuration against project conventions, which no phase is specifically prompted to do. I5/I6 (vacuous tests) require the pipeline to critique its own test output.

5. **Multi-judge voting stabilizes scores** — single-judge runs are noisy (±15pp). Three judges with majority vote reduces variance significantly.

## Creating a New Peloton Scenario

### Step 1: Identify a Reviewed PR

Find a PR where:
- The internal pipeline (TEA → Dev → Reviewer) ran and **approved** the code
- An external reviewer subsequently found real issues
- The findings are documented with enough detail to judge against

### Step 2: Write the Scenario YAML

```yaml
id: dpgd-XXX
title: "Story N.N: Feature Name"
story_id: "N-N"
jira: DPGD-XXX

repo:
  path: my-project                  # Repo containing the code
  base_commit: abc123def456         # Commit BEFORE the pipeline ran
  branch: feature/story-N.N-name   # Branch the PR was on

## Context — Sprint (has epic+story docs from pennyfarthing orchestrator)
context:
  epic: sprint/context/context-epic-N.md
  story: sprint/context/context-story-N-N.md
  session_archive: sprint/archive/DPGD-XXX-session.md  # optional

## Context — Repo (pre-framework PRs, external repos without sprint docs)
# context:
#   claude_md: CLAUDE.md            # Relative to repo root (resolved via roots.repo)
# roots:
#   repo: ../../../../../poller-orc/poller-cobra  # Relative to scenario file

phases: [tea, dev, reviewer]

ground_truth:
  total_weight: 37  # Sum of all finding weights
  round_1:
    findings:
      - id: C1
        title: "Short description of the critical finding"
        severity: critical
        weight: 8
        category: security
        phase_ideal: dev
        files: [crates/foo/src/bar.rs]
        description: >
          Detailed description of the issue, why it matters,
          and what the fix should look like.
      - id: I1
        title: "..."
        # ... more findings

phase_prompts:
  tea: |
    You are the TEA for Story N.N: Feature Name.
    Your task is the RED phase of TDD...
  dev: |
    You are the Dev for Story N.N: Feature Name.
    Your task is the GREEN phase...
  reviewer: |
    You are the Reviewer for Story N.N: Feature Name.
    Your task is the REVIEW phase...
```

### Step 3: Validate

```bash
# Dry run — one pipeline execution, skip scoring
pf benchmark replay run scenarios/dpgd-XXX.yaml --n 1 --skip-score --keep-worktree

# Check the worktree to see what the pipeline produced
ls /tmp/pf-replay/dpgd-XXX-control-run-1/
```

### Step 4: Run at Scale

```bash
# Control baseline (N=4 minimum, N=10 for statistical power)
pf benchmark replay run scenarios/dpgd-XXX.yaml --n 4

# Themed runs
pf benchmark replay run scenarios/dpgd-XXX.yaml --theme firefly --n 4
pf benchmark replay run scenarios/dpgd-XXX.yaml --theme discworld --n 4

# Multi-judge all runs
pf benchmark replay judge scenarios/dpgd-XXX.yaml --target-judges 3

# Compare
pf benchmark replay compare scenarios/dpgd-XXX.yaml
```

## Glossary

| Term | Definition |
|------|------------|
| **Peloton test** | Repeatable benchmark scenario for a full agent team, sourced from real external review findings. |
| **Pipeline replay** | The harness (`pf benchmark replay`) that executes peloton tests. |
| **Ground truth** | The set of findings from external review that the pipeline should have caught. |
| **External review** | Human code review that produces structured, severity-rated PR findings. |
| **Majority vote** | Consensus scoring from 3+ independent LLM judge passes (reduces noise). |
| **Control** | Baseline theme with no persona (OCEAN 3/3/3/3/3) — the "what would a vanilla agent do?" comparison point. |
| **Phase ideal** | Which pipeline phase (TEA, Dev, or Reviewer) should have caught a given finding. |
| **JobFair** | Single-agent benchmarking — tests one role in isolation. Peloton tests the whole team. |

## File Locations

| What | Where |
|------|-------|
| Harness code | `pennyfarthing-dist/src/pf/benchmark/pipeline_replay.py` |
| CLI commands | `pennyfarthing-dist/src/pf/benchmark/cli.py` |
| Scenario YAMLs | `orc-ax/benchmarks/scenarios/` (or project-local) |
| Results | `internal/results/pipeline-replay/<scenario-id>/<theme>/run-N/` |
| Dashboard | `internal/results/benchmark-dashboard.html` |
| This guide | `pennyfarthing-dist/guides/peloton.md` |
