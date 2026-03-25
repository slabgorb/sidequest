# Handoff CLI

<info>
Python CLI for managing workflow phase transitions. Agents use `pf handoff` to resolve gates, complete phase transitions, and generate handoff markers during their exit protocol.
</info>

## Commands

### resolve-gate

Check whether the current phase has a gate and resolve it.

```bash
pf handoff resolve-gate STORY_ID WORKFLOW PHASE
```

**Arguments:**
- `STORY_ID` — Story identifier (e.g., `105-1`)
- `WORKFLOW` — Workflow name (e.g., `tdd`, `trivial`, `patch`)
- `PHASE` — Current phase name (e.g., `green`, `implement`, `fix`)

**Output:** YAML `RESOLVE_RESULT` block:

```yaml
RESOLVE_RESULT:
  status: ready
  gate_type: sm_setup_exit
  gate_file: gates/sm-setup-exit
  next_agent: dev
  next_phase: implement
  assessment_found: true
  error: null
```

| Status | Meaning | Exit code |
|--------|---------|-----------|
| `ready` | Gate exists, subagent should evaluate it | 0 |
| `skip` | No gate for this phase (or manual gate), proceed directly | 0 |
| `error` | Workflow/phase not found or misconfigured | 0 |
| `blocked` | Phase cannot transition | 1 |

The `next:` directive in workflow YAML supports non-linear phase routing. When a phase declares `next: <phase-name>`, resolve-gate follows it instead of advancing sequentially.

### complete-phase

Atomically update the session file to record a phase transition.

```bash
pf handoff complete-phase STORY_ID WORKFLOW FROM_PHASE TO_PHASE GATE_TYPE
```

**Arguments:**
- `STORY_ID` — Story identifier
- `WORKFLOW` — Workflow name
- `FROM_PHASE` — Phase being completed (e.g., `green`)
- `TO_PHASE` — Phase being entered (e.g., `review`)
- `GATE_TYPE` — Gate that was passed (e.g., `tests_pass`, `sm_setup_exit`, `skip`, `none`)

**Output:** YAML `COMPLETE_RESULT` block:

```yaml
COMPLETE_RESULT:
  status: success
  session_file: .session/105-1-session.md
  error: null
```

Updates the session file: `**Phase:**` line, timestamps, and phase history table.

**Requires assessment:** The agent must write a `## {Agent} Assessment` section to the session file before calling complete-phase. Missing assessments cause an error.

### marker

Generate an environment-aware handoff marker block.

```bash
pf handoff marker NEXT_AGENT
pf handoff marker --error "Tests failing"
```

**Arguments:**
- `NEXT_AGENT` — Agent to hand off to (e.g., `dev`, `tea`, `reviewer`)

**Options:**
- `--error MSG` — Generate an error marker instead of a handoff

The marker generator checks relay mode and context usage to produce the appropriate output:

- **Relay ON:** `AGENT_COMMAND` block with `relay: true` and an `invoke` field (e.g., `/pf-dev`). The agent uses the Skill tool to invoke the next agent automatically.
- **Relay OFF:** `AGENT_COMMAND` block with `relay: false` and a `fallback` message for the user to invoke manually.

**Output example (relay on):**

```yaml
---
AGENT_COMMAND:
  relay: true
  invoke: "/pf-dev"
  fallback: "Run `/pf-dev` to continue"
  context_percent: 6
---
```

### phase-check

Check if a given agent owns the current workflow phase. Used during agent activation to detect misrouted handoffs.

```bash
pf handoff phase-check AGENT
```

**Arguments:**
- `AGENT` — Agent to check (e.g., `dev`, `tea`, `reviewer`, `sm`)

**Output:** YAML `PHASE_CHECK` block:

```yaml
PHASE_CHECK:
  action: start        # "start" (proceed) or "redirect" (wrong agent)
  agent: dev           # Agent that should run
  story_id: "105-1"   # Current story (null if no session)
  phase: green         # Current phase (null if no session)
  phase_owner: dev     # Agent that owns the phase
  message: "Agent dev owns phase 'green' — proceeding"
```

When `action: redirect`, the command also emits a handoff marker for the correct agent.

### status

Show current handoff and gate state for the active session.

```bash
pf handoff status
pf handoff status --json
```

**Options:**
- `--json` — Output as JSON

**Output (text):**

```
Story: 105-1
Phase: green
Workflow: tdd
Gate: tests_pass
Next: review (reviewer)
```

**Output (JSON):**

```json
{
  "story_id": "105-1",
  "phase": "green",
  "workflow": "tdd",
  "gate_type": "tests_pass",
  "next_phase": "review",
  "next_agent": "reviewer",
  "status": "active"
}
```

Returns `"status": "no_session"` with all other fields null when no session is active.

## Agent Exit Protocol

The handoff CLI is used in sequence during agent exit:

```
1. Write assessment to session file
2. pf handoff resolve-gate {story-id} {workflow} {phase}
   ├── blocked → report error, STOP
   ├── error → report error, STOP
   ├── skip → jump to step 4
   └── ready → spawn gate subagent → GATE_RESULT
       ├── fail → fix issues, retry (max 3)
       │          If gate has recovery: config, auto-create missing context
       └── pass → check gate_extensions (step 2b)
2b. If RESOLVE_RESULT.gate_extensions is present:
    For each extension gate ref:
      parse_gate_file() → spawn subagent → extract_gate_result()
      ├── fail → stop chain, merge_gate_results(), report combined failure
      └── pass → merge_gate_results(), continue to next extension
    All extensions pass → continue with combined result
3. pf handoff complete-phase {story-id} {workflow} {from} {to} {gate-type}
4. pf handoff marker {next-agent}
   ├── relay: true → invoke the `invoke` skill via Skill tool (next agent starts)
   └── relay: false → output fallback text → EXIT
```

See `guides/gates.md` for gate file format and evaluation details.

## Gate Recovery

When a gate check fails because required context is missing (not invalid), the recovery module can auto-trigger context creation. Recovery config is defined in the workflow YAML as a `recovery:` block on the gate definition.

Recovery only triggers for "not found" failures — validation errors require manual fixes. See `pf/handoff/gate_recovery.py` for the implementation.

## Key Files

| File | Purpose |
|------|---------|
| `pf/handoff/cli.py` | Click command definitions |
| `pf/handoff/resolve_gate.py` | Gate resolution logic |
| `pf/handoff/complete_phase.py` | Session file atomic updates |
| `pf/handoff/marker.py` | Environment-aware marker generation |
| `pf/handoff/phase_check.py` | Agent phase ownership check |
| `pf/handoff/gate_runner.py` | Gate subagent spawner |
| `pf/handoff/gate_file.py` | Gate file discovery |
| `pf/handoff/gate_recovery.py` | Auto-recovery for missing context |

<info>
**Related:** `guides/gates.md` (gate system), `agents/agent-behavior.md` (exit protocol), `guides/relay-mode.md` (relay configuration)
</info>
