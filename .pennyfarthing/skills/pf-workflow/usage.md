# Workflow CLI — Detailed Usage

## Commands

### `pf.sh workflow check`

Check current workflow state.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `--json` | No | Output as JSON |

### `pf.sh workflow complete-step`

Complete the current step of a stepped workflow.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | No | Workflow name (auto-detects from session if omitted) |
| `--step` | No | Complete a specific step number instead of current step |

### `pf.sh workflow fix-phase`

Repair session phase tracking when handoffs didn't update properly.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story ID (e.g., 56-1 or <PROJECT-KEY>) |
| `TARGET_PHASE` | Yes | Target phase to set (e.g., review, approved, finish) |
| `--dry-run` | No | Preview without making changes |

### `pf.sh workflow handoff`

Emit an environment-aware handoff marker.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NEXT_AGENT` | Yes | The agent to hand off to (tea, dev, reviewer, etc.) |

### `pf.sh workflow list`

List all available workflows.

### `pf.sh workflow phase-check`

Check which agent owns a workflow phase.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `WORKFLOW_NAME` | Yes | The workflow type (tdd, trivial, etc.) |
| `PHASE` | Yes | The phase to check (red, implement, review, etc.) |

### `pf.sh workflow phases`

Show workflow phases with status annotation.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | No | Story ID to look up session phase (optional) |
| `--json` | No | Output as JSON |

### `pf.sh workflow resume`

Resume a stepped workflow from the current step.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | No | Workflow name (auto-detects from active session if omitted) |

### `pf.sh workflow show`

Show workflow details including phase flow, triggers, and gates.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | No | Workflow name (defaults to current session's workflow or tdd) |

### `pf.sh workflow start`

Start a stepped workflow from step 1.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | Yes | Workflow name (e.g., architecture, release) |
| `-m, --mode` | No | Mode: create, validate, or edit |

### `pf.sh workflow status`

Show current stepped workflow progress.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NAME` | No | Workflow name (auto-detects from active session if omitted) |

### `pf.sh workflow type`

Get workflow type (phased, stepped, or procedural).

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `WORKFLOW_NAME` | Yes | Workflow name (e.g., tdd, architecture) |

