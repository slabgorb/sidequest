# Team Mode — Phase-Scoped Native Teams

Team mode enables parallel agent collaboration within a single workflow phase using Claude Code's native Agent Teams. The phase agent is always the **team lead**; spawned agents are **teammates**. Teams are created at phase start and destroyed before handoff.

**Prerequisites:**
- Workflow phase has a `team:` block in its YAML definition
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env var is set
- Interactive session (not `-p` mode)
- Feature detection passes (`pf detect teams` or equivalent)

**If prerequisites are not met:** Fall back to solo execution (optionally with tandem consultation). No error — team mode is always optional.

## Detection

On activation, check the workflow YAML for a `team:` block on your phase:

```yaml
phases:
  - name: green
    agent: dev
    team:
      teammates:
        - agent: architect
          task: "Review implementation approach and patterns"
        - agent: tea
          task: "Verify tests stay green, flag regressions"
```

If `team:` is present and prerequisites are met, you are the **team lead** for this phase.

## Team Lead Responsibilities

**On phase entry:**

1. **Create the team:**
   ```
   TeamCreate("phase-{PHASE}-{STORY_ID}")
   ```

2. **Spawn teammates** per workflow YAML config. Each teammate gets a spawn prompt:
   ```
   Task(team_name="phase-{PHASE}-{STORY_ID}", name="{agent}",
        prompt="Run `pf agent start {agent}`. Story: {STORY_ID}.
                {task assignment from YAML}")
   ```
   Teammates auto-load CLAUDE.md, MCP servers, and skills from the working directory. Spawn prompts only need the activation command and task assignment — keep under 500 tokens.

3. **Coordinate via SendMessage.** Use `SendMessage` for all intra-phase communication with teammates:
   - Assign work: `SendMessage(to="{teammate}", message="Implement the adapter pattern for...")`
   - Check status: `SendMessage(to="{teammate}", message="Status on your review?")`
   - Broadcast: `SendMessage(message="Shifting approach — using strategy pattern instead")`

4. **Do your own work.** You are still the primary implementer. Teammates assist — they don't replace you.

**Before exit protocol:**

5. **Shut down all teammates.** This is mandatory before starting the normal exit protocol:
   ```
   SendMessage(to="{teammate}", message="Phase complete. Shut down.")
   ```
   Wait for teammates to go idle, then:
   ```
   TeamDelete("phase-{PHASE}-{STORY_ID}")
   ```

6. **Proceed with normal exit protocol** (assessment → resolve-gate → complete-phase → marker).

## Teammate Responsibilities

When spawned as a teammate (you receive a task via spawn prompt, not a phase handoff):

1. **Recognize you are a teammate, not the lead.** You do not own the phase. You do not run the exit protocol. You do not emit handoff markers.

2. **Activate normally** via `pf agent start {agent}`. Read the session file for story context.

3. **Communicate via SendMessage.** All collaboration with the lead and other teammates uses `SendMessage`:
   - Report findings: `SendMessage(to="lead", message="Found coupling issue in...")`
   - Ask questions: `SendMessage(to="lead", message="Should I use the existing adapter?")`
   - Share status: `SendMessage(to="lead", message="Review complete. 2 issues found.")`

4. **Go idle when your task is done.** Once your assigned task is complete, send a final status message and wait. Do not start new work unprompted.

5. **Respond to shutdown requests.** When the lead sends a shutdown message, wrap up immediately. Save any observations to the session file or sidecar, then stop.

## Communication Channels

| Channel | Scope | Used For |
|---------|-------|----------|
| `SendMessage` | Intra-phase (within team) | Lead ↔ teammate collaboration, status updates, task assignment |
| Handoff markers | Inter-phase (between phases) | Handoff from one phase agent to the next — **unchanged** |
| Session file | Cross-phase persistence | Story state, assessments, ACs — written by lead only in team mode |
| Sidecar files | Agent learning | Teammates may write to their own sidecar with file locking |

<critical>
**Never use SendMessage for inter-phase handoff.** Markers and `pf handoff` are the only way to transition between phases. SendMessage is for real-time collaboration within a phase.

**Never use markers for intra-phase communication.** Markers are routing signals for Frame GUI and the handoff system. They have no meaning inside a team.
</critical>
