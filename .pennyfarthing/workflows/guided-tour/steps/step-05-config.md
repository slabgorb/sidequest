# Step 5: Hooks & Configuration

<step-meta>
step: 5
name: config
workflow: guided-tour
agent: orchestrator
gate: true
next: complete
</step-meta>

<purpose>
Explore Pennyfarthing's hook system and configuration options. Hooks intercept Claude Code events (session start, tool use, stop) to add framework behavior. Configuration lives in `.pennyfarthing/config.local.yaml`.
</purpose>

<prerequisites>
- Step 4 (Sprint) completed
- `.pennyfarthing/config.local.yaml` exists
</prerequisites>

<instructions>
1. Explain the hook system: hooks intercept Claude Code lifecycle events
2. List the key hooks with detailed explanations
3. Show the config file structure and key settings
4. Explain workflow settings: permission_mode, relay_mode, bell_mode
5. Show how to view current settings
6. Summarize the tour and suggest next steps
</instructions>

<actions>
- Read: `.pennyfarthing/config.local.yaml` to show current settings
- Show: hook list and what each one does
- Show: configuration examples
</actions>

<output>
Present hooks and config overview:

```markdown
## Hooks & Configuration

**Hooks** intercept Claude Code events to add framework behavior:

| Hook | Event | Purpose |
|------|-------|---------|
| session-start | SessionStart | Setup, welcome banner, Frame connection |
| bell-mode | PostToolUse | Message queue injection and tandem observations |
| pre-edit-check | PreToolUse | Block edits to protected files (.pennyfarthing/, node_modules/) |
| reflector-check | Stop | Enforce UI markers on every agent turn |
| context-warning | PreToolUse | Warn when context usage exceeds threshold |
| schema-validation | PreToolUse:Write | Validate session/skill/step file schemas |
| sprint-yaml | PostToolUse | Validate sprint YAML after modifications |

**Configuration** in `.pennyfarthing/config.local.yaml`:
```yaml
theme: discworld
workflow:
  permission_mode: accept   # plan, manual, accept
  relay_mode: true           # auto-handoff between agents
  bell_mode: true            # message queue injection
  statusbar: true            # status line display
```

### Permission Modes

| Mode | Behavior |
|------|----------|
| `plan` | Agent must present plan for approval before making changes |
| `manual` | Each tool call requires user approval |
| `accept` | Auto-accept all tool calls (fastest, least oversight) |

### Relay Mode
When `relay_mode: true`, agents automatically hand off to the next agent in the workflow without requiring the user to manually invoke `/pf-{agent}`. The handoff marker triggers an inline activation of the next agent.

### Bell Mode
When `bell_mode: true`, the PostToolUse hook checks a message queue and injects messages into the conversation. This powers tandem observations (background agent insights) and inter-agent notifications.

## Tour Complete!

You've explored Pennyfarthing's five key areas. Next steps:
- Run `/pf-sprint work` to pick up a story
- Run `/pf-help` for command reference anytime
- Check the getting-started guide for deeper documentation
```
</output>

<gate>
## Completion Criteria
- [ ] User has seen the hook system overview
- [ ] User understands the config file structure
- [ ] User understands permission_mode, relay_mode, and bell_mode
- [ ] User knows where to go next (sprint work, help, guides)
</gate>

<deep-dive>
## Deep-Dive: Hooks & Configuration Internals

When the user selects Dig In, explore these topics interactively:

### Session-Start Hook
The session-start hook fires on every new Claude Code session:
- Loads checkpoint from previous session for continuity
- Starts Frame server (if Frame is active)
- Displays welcome banner with project name and theme
- Sets up the status line display

### Pre-Edit-Check Hook
Guards protected paths defined in `repos.yaml`:
- Blocks edits to `.pennyfarthing/` symlinked directories
- Blocks edits to `node_modules/` and build output (`dist/`)
- Reports the correct source path to edit instead

### Bell Mode Details
The bell-mode PostToolUse hook:
- Reads from `.pennyfarthing/bell-queue/` message files
- Injects messages as `[Bell] source: message` into conversation
- Powers tandem observations: `[Tandem] Character: insight`
- Messages are consumed (deleted) after injection

### Permission Mode Deep-Dive
- **plan**: Best for learning — agent explains what it will do before doing it
- **manual**: Good balance — you approve each significant action
- **accept**: Production speed — agent works autonomously with full tool access

### Relay Mode Details
When relay_mode is enabled:
- Handoff markers trigger `pf agent start {next} --tier handoff --quiet`
- The next agent activates inline without user intervention
- Context percentage determines if inline handoff or TirePump (context clear) is needed
- At >80% context, user is prompted to `/clear` before continuing

### Other Configuration
- `theme`: Active persona theme (e.g., discworld, star-trek-tng)
- `statusbar`: Enable/disable the Claude Code status line
- `layout`: Frame panel arrangement
- `display`: Color presets and font settings

Use AskUserQuestion to let the user pick which sub-topic to explore. Continue the deep-dive loop until the user chooses to move on.
</deep-dive>

<switch tool="AskUserQuestion">
  <case value="continue" next="complete">
    Continue — Complete the tour
  </case>
  <case value="dig-in" next="LOOP">
    Dig In — Explore hooks, permission modes, and relay mode in detail
  </case>
  <case value="try-it" next="LOOP">
    Try It — View your config file
  </case>
  <case value="skip" next="complete">
    Skip — Finish the tour
  </case>
</switch>
