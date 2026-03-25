---
name: ux-tandem
description: Live UX review tandem — spawn a UX designer to watch a tmux pane and suggest improvements in real time
---

# UX Tandem Skill

<run>
Spawn a UX designer teammate that watches a tmux pane and provides real-time usability feedback via Agent Teams.

This is NOT the standard tandem-backseat protocol (observation files + PostToolUse injection). This uses native Agent Teams with `SendMessage` for real-time two-way collaboration, and `tmux capture-pane` for visual observation.

## Step 1: Identify the Target Pane

Find the tmux pane to observe:

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_title} #{pane_current_command} [#{pane_width}x#{pane_height}]'
```

Pick the pane running the target UI (e.g., a TUI, dev server output, or running application). Note the pane address in `{session}:{window}.{pane}` format.

If the user specified a pane, use that. If not, choose the pane that most likely contains the UI under review.

## Step 2: Resolve Persona

Read the active theme to get the UX designer character:

```bash
THEME=$(yq '.theme' .pennyfarthing/config.local.yaml 2>/dev/null || echo "discworld")
```

Then read the theme file to find the UX designer character name.

## Step 3: Create the Team

```
TeamCreate:
  team_name: "ux-tandem"
  description: "Live UX review — observer watches tmux pane and suggests improvements"
```

## Step 4: Create Tasks

Create two tasks:

1. **"Observe tmux pane and provide UX feedback"** — assigned to the UX observer
2. **"Implement UX suggestions from observer"** — assigned to self (the lead)

## Step 5: Spawn the UX Observer

Use the Task tool to spawn the observer teammate:

```
Task:
  subagent_type: "general-purpose"
  model: "sonnet"
  team_name: "ux-tandem"
  name: "ux-observer"
  prompt: |
    You are a UX designer reviewing a live terminal UI. Your role is to watch a tmux pane
    and send usability suggestions to the lead agent.

    CHARACTER: {resolved character name from theme}
    TARGET_PANE: {session}:{window}.{pane}

    ## Your Workflow

    **Loop** (repeat until told to stop):

    1. **Capture** the current pane state:
       ```bash
       tmux capture-pane -t '{TARGET_PANE}' -p
       ```

    2. **Analyze** what you see. Focus on:
       - Layout and visual hierarchy — is the information easy to scan?
       - Alignment and spacing — are elements consistently aligned?
       - Color usage and contrast — is text readable? Are colors meaningful?
       - Information density — too cluttered or too sparse?
       - Labels and terminology — clear and consistent?
       - Navigation cues — can the user tell where they are and what they can do?
       - Error states — are errors visible and actionable?
       - Empty states — what shows when there's no data?

    3. **Send suggestions** via SendMessage to the lead:
       - One suggestion per message
       - Be specific: reference exact text, positions, or elements you see
       - Categorize as [LAYOUT], [COLOR], [COPY], [INTERACTION], or [ACCESSIBILITY]
       - Include a concrete fix, not just the problem
       - Priority: focus on high-impact issues first

    4. **Wait** for the lead to confirm implementation or ask questions, then re-capture
       to verify the change and continue.

    ## Communication Protocol

    - Use `SendMessage` with `type: "message"` to send suggestions
    - Keep messages concise — one issue per message
    - If you see no issues, say so and wait before re-capturing
    - If the lead sends you a message, respond via SendMessage
    - When told to wrap up, acknowledge and stop

    ## Example Message

    ```
    [LAYOUT] The status indicators in the top-right are misaligned — "Sprint: 4"
    sits 2 chars higher than "Stories: 12/15". Suggestion: pad the Sprint label
    with a leading space or align both to the same row baseline.
    ```

    Stay in character as {CHARACTER}. Begin by capturing the pane and sending
    your first observation.
```

## Step 6: Implement Suggestions

As the lead agent, receive suggestions via automatic message delivery.
For each suggestion:

1. Read the suggestion
2. Decide whether to implement (confirm to the observer via `SendMessage`)
3. Make the code change
4. Let the observer re-capture and verify

## Step 7: Teardown

When the review session is complete:

1. Send a shutdown request to the observer:
   ```
   SendMessage:
     type: "shutdown_request"
     recipient: "ux-observer"
     content: "UX review complete, shutting down"
   ```

2. After the observer confirms, delete the team:
   ```
   TeamDelete
   ```
</run>

<output>
Real-time UX feedback loop between the lead agent and a UX observer teammate. The observer captures the target tmux pane, analyzes it for usability issues, and sends categorized suggestions ([LAYOUT], [COLOR], [COPY], [INTERACTION], [ACCESSIBILITY]) via SendMessage. The lead confirms, implements, and the observer re-captures to verify. Continues until the lead triggers teardown.
</output>

## When to Use

- Reviewing a TUI for usability issues while actively developing it
- Getting real-time UX feedback on a running application in another tmux pane
- Polishing visual output (tables, panels, status bars, progress indicators)
- Pre-release UI review of terminal tools

## When NOT to Use

- **Code-only review** — use the standard tandem-backseat protocol or `/pf-code-review`
- **Non-visual targets** — if there's no UI to look at, this skill adds nothing
- **No tmux** — requires tmux for pane capture; won't work in plain terminal sessions

## Customizing the Observer Role

The observer doesn't have to be a UX designer. Swap the role and analysis criteria:

| Observer Role | Focus Areas |
|---------------|-------------|
| **UX Designer** (default) | Layout, color, copy, interaction, accessibility |
| **Architect** | Component structure, separation of concerns, data flow visible in UI |
| **TEA** | Error states, edge cases, missing validation feedback |
| **PM** | Feature completeness, user story coverage, workflow gaps |

To use a different observer, modify the spawn prompt's analysis criteria and character resolution to match the desired role.

## Customizing the Observation Target

The `tmux capture-pane` command can be replaced with other observation methods:

| Target | Capture Method |
|--------|---------------|
| **tmux pane** (default) | `tmux capture-pane -t '{pane}' -p` |
| **Browser** | Screenshot via Playwright MCP / `browser_take_screenshot` |
| **Log file** | `tail -n 50 /path/to/logfile` |
| **API response** | `curl -s http://localhost:3000/api/status` |

## Differences from Tandem-Backseat

| Aspect | Tandem-Backseat | UX Tandem (this skill) |
|--------|----------------|----------------------|
| Communication | One-way (observation file + hook injection) | Two-way (`SendMessage`) |
| Infrastructure | PostToolUse hook, observation files | Agent Teams (`TeamCreate`/`SendMessage`) |
| Model | Haiku (background) | Sonnet (teammate) |
| Observation | git diff, file reads | `tmux capture-pane` (visual) |
| Lifecycle | Background task, auto-injected | Interactive team, manual confirm/reject |
| Use case | Code-level observation during workflow | Visual/UX review of running UI |
