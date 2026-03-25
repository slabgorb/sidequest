# Handoff CLI — Detailed Usage

## Commands

### `pf handoff resolve-gate`

Resolve the gate for the current workflow phase. Checks assessment and returns gate status.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story identifier (e.g., 105-1) |
| `WORKFLOW` | Yes | Workflow name (e.g., tdd, trivial, patch) |
| `PHASE` | Yes | Current phase name (e.g., green, implement, fix) |
| `--json` | No | Output as JSON |

**JSON output:** `{status, gate_type, gate_file, next_agent, next_phase, assessment_found, error}`

**Status values:** `ready` (gate passed), `blocked` (gate failed), `skip` (no gate), `error`

### `pf handoff complete-phase`

Complete a phase transition with atomic session update. Updates session phase line, timestamps, and history.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `STORY_ID` | Yes | Story identifier (e.g., 105-1) |
| `WORKFLOW` | Yes | Workflow name (e.g., tdd, trivial) |
| `FROM_PHASE` | Yes | Phase being completed (e.g., green) |
| `TO_PHASE` | Yes | Phase being entered (e.g., review) |
| `GATE_TYPE` | Yes | Gate type that was passed (e.g., tests_pass) |

### `pf handoff marker`

Generate an environment-aware AGENT_COMMAND handoff marker block. Detects relay mode and context usage.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `NEXT_AGENT` | No | Agent to hand off to (e.g., dev, tea, reviewer) |
| `--error TEXT` | No | Generate error marker instead of handoff |

### `pf handoff phase-check`

Check if the requested agent owns the current workflow phase.

### `pf handoff status`

Show current handoff/gate state for the active session.

| Arg/Option | Required | Description |
|------------|----------|-------------|
| `--json` | No | Output as JSON |

**JSON output:** `{story_id, phase, workflow, gate_type, next_phase, next_agent, status}`
