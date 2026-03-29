---
name: sq-playtest
description: Interactive playtest — launches SideQuest stack in tmux panes, opens Playwright browser, spawns UX Designer for screenshot evaluation, coordinates cross-workspace bug reporting via ping-pong file with OQ-1.
---

# SideQuest Playtest Skill

<run>
You are now the **Playtest SM**. You coordinate an interactive playtest of the SideQuest game engine.

**Architecture:**
- OQ-2 (this workspace): drives the playtest — SM + UX Designer + Playwright browser
- OQ-1 (other workspace): fixes bugs from the shared ping-pong file — SM + Dev + Architect

Read `sq-playtest/pingpong.md` in this skill directory for the full coordination protocol.

---

## Phase 1: Stack Launch

### 1a. Check pane capacity

```bash
pf tmux list
```

If at the 5-pane limit, close idle worker panes first:
```bash
pf tmux close <idle-pane-ref>
```

### 1b. Launch services in tmux panes

Launch all three services. Use absolute paths from the orchestrator root.

```bash
pf tmux run "cd /Users/keithavery/Projects/oq-2/sidequest-api && cargo run 2>&1 | tee /tmp/sq-api.log" --title api-server
pf tmux run "cd /Users/keithavery/Projects/oq-2/sidequest-ui && npm run dev 2>&1 | tee /tmp/sq-ui.log" --title ui-dev
pf tmux run "cd /Users/keithavery/Projects/oq-2/sidequest-daemon && SIDEQUEST_GENRE_PACKS=/Users/keithavery/Projects/oq-2/sidequest-content/genre_packs sidequest-renderer 2>&1 | tee /tmp/sq-daemon.log" --title daemon
```

### 1c. Health check

Poll each pane for startup confirmation. Different timeouts per service:

| Pane | Look for | Timeout |
|------|----------|---------|
| `api-server` | `"listening"` or `"Listening"` or `"ready"` | 120s (compile time) |
| `ui-dev` | `"Local:"` or `"ready in"` (Vite) | 30s |
| `daemon` | `"renderer ready"` or `"running"` | 30s |

For each pane, retry every 3 seconds:
```bash
pf tmux read api-server
```

If a service fails to show its ready string within the timeout, report the error and ask the user whether to continue or abort.

### 1d. Launch Playwright browser

Open a headed browser to the UI:
```
mcp__playwright__browser_navigate(url="http://localhost:5173")
```

Take an initial screenshot to confirm the UI loaded:
```
mcp__playwright__browser_take_screenshot()
```

If the page shows an error (connection refused, blank page), check `pf tmux read ui-dev` for errors.

---

## Phase 2: Agent Setup

### 2a. Create the playtest team

```
TeamCreate:
  team_name: "sq-playtest"
  description: "Interactive playtest — SM drives gameplay, UX Designer evaluates screenshots"
```

### 2b. Spawn UX Designer

Resolve the UX Designer character from the active theme:
```bash
THEME=$(yq '.theme' .pennyfarthing/config.local.yaml 2>/dev/null || echo "firefly")
```

Spawn the UX Designer teammate:
```
Agent:
  subagent_type: "general-purpose"
  model: "sonnet"
  team_name: "sq-playtest"
  name: "ux-observer"
  prompt: |
    You are a UX Designer evaluating a live game UI during an interactive playtest.

    ## Your Workflow

    Wait for the SM to send you screenshots via SendMessage. For each screenshot:

    1. **Read the image** using the Read tool (the SM sends the file path)
    2. **Analyze** what you see. Focus on:
       - Visual bugs — broken layouts, overlapping elements, missing assets
       - Usability — can the player understand what to do next?
       - Accessibility — contrast, font size, color-only indicators
       - Feedback — does the UI confirm actions? Show loading states? Display errors clearly?
       - Game feel — does the UI support immersion or break it?
    3. **Respond** via SendMessage to the SM with categorized findings:
       - `[BUG]` — something is visually broken or non-functional
       - `[BUG-LOW]` — cosmetic issue, not blocking gameplay
       - `[UX]` — usability improvement opportunity
       - `[GAP]` — expected feature or feedback is missing

    Be specific. Reference exact elements ("the HP bar in the top-left", "the submit button
    below the text input"). Include a concrete suggestion, not just the problem.

    If the screenshot looks good, say so briefly and wait for the next one.
```

### 2c. Initialize ping-pong file and screenshots directory

```bash
mkdir -p /Users/keithavery/Projects/sq-playtest-screenshots
```

Create the ping-pong file (or reset it if starting a new session):

Write to `/Users/keithavery/Projects/sq-playtest-pingpong.md`:
```markdown
# SideQuest Playtest — {today's date and time}

## Protocol
- **OQ-2** (playtest driver): adds new tasks, verifies fixes, takes screenshots
- **OQ-1** (fix team): picks up tasks, implements fixes, updates status
- Status flow: `open` → `in-progress` → `fixed` → `verified`
- OQ-2 ONLY appends new tasks and updates status to `verified`
- OQ-1 ONLY updates status to `in-progress` or `fixed`
- Neither side deletes entries — status transitions only

## How to Monitor (for OQ-1)
Read this file periodically. When you see new `open` tasks:
1. Update the task status to `in-progress`
2. Fix the issue in the codebase
3. Update the task status to `fixed`
4. If the fix requires a server restart, add a note: `- **Needs restart:** yes`

## Status
Active playtest in progress.

## Tasks (newest first)
```

Tell the user: "Ping-pong file ready at `/Users/keithavery/Projects/sq-playtest-pingpong.md`. Tell OQ-1 to monitor it."

---

## Phase 3: Interactive Playtest Loop

This is the main gameplay loop. Repeat until the user says to stop:

### 3a. Perform a game action

Use Playwright to interact with the game:
```
mcp__playwright__browser_click(...)
mcp__playwright__browser_fill_form(...)
mcp__playwright__browser_navigate(...)
mcp__playwright__browser_press_key(...)
```

Describe what you're doing before each action ("Clicking 'New Game' button").

### 3b. Observe

Take a screenshot and save it:
```
mcp__playwright__browser_take_screenshot()
```

Also save to the shared screenshots directory with a sequential number:
```bash
cp /path/to/screenshot /Users/keithavery/Projects/sq-playtest-screenshots/NNN.png
```

### 3c. Evaluate with UX Designer

Send the screenshot to the UX Designer:
```
SendMessage:
  to: "ux-observer"
  content: "Screenshot {NNN}: {brief description of what just happened}. Image at /Users/keithavery/Projects/sq-playtest-screenshots/NNN.png"
```

Wait for the UX Designer's response.

### 3d. Triage findings

For each finding from the UX Designer (or your own observations):

1. Determine the tag: `[BUG]`, `[BUG-LOW]`, `[UX]`, or `[GAP]`
2. Determine priority: `blocking`, `high`, `medium`, `low`
3. Append to the ping-pong file:

```markdown
### [{TAG}] {title}
- **Priority:** {priority}
- **Found by:** {SM | UX Designer}
- **Repro:** {step-by-step reproduction}
- **Status:** open
- **Screenshot:** /Users/keithavery/Projects/sq-playtest-screenshots/{NNN}.png
- **Notes:** {additional context}
```

For **blocking bugs**, also prepend an attention signal at the top of the Tasks section:
```markdown
> **ATTENTION OQ-1**: Blocking bug added — {brief description}. Please prioritize.
```

### 3e. Monitor ping-pong file (SM owns the sync cycle)

**You are responsible for watching the ping-pong file and driving the fix→verify loop.**

Before each new gameplay action, re-read the ping-pong file:
```bash
cat /Users/keithavery/Projects/sq-playtest-pingpong.md
```

**When you see tasks updated to `fixed`:**

1. Check if the task has `Needs restart: yes`
2. If yes → run the full **Sync & Restart** cycle (see Phase 4)
3. If no → re-test the issue directly via Playwright
4. If verified → update status to `verified` in the ping-pong file
5. If not fixed → add a note explaining what's still broken, set status back to `open`

**When you see tasks still `in-progress`:**
- Note them but don't block — continue playtesting other areas

**When the file hasn't changed:**
- Continue normal gameplay loop

### 3f. Health check (periodic)

Every few actions, check the service panes:
```bash
pf tmux read api-server
pf tmux read ui-dev
pf tmux read daemon
```

If a service has crashed:
1. Check if OQ-1 pushed a fix that requires rebuild
2. If yes → run the Sync & Restart cycle (Phase 4)
3. If no → restart the crashed service and investigate logs

---

## Phase 4: Service Management (SM Owns Git Sync)

**The SM is the single owner of git pull/push for both repos in this workspace.**
OQ-1 pushes fixes to remote. The SM pulls them, rebuilds, restarts, and verifies.

### Sync & Restart Cycle

This is the core flow when OQ-1 has fixed something:

```bash
# 1. Pull latest from all affected repos
cd /Users/keithavery/Projects/oq-2/sidequest-api && git pull origin develop
cd /Users/keithavery/Projects/oq-2/sidequest-ui && git pull origin develop
# (daemon only if OQ-1 touched it)
cd /Users/keithavery/Projects/oq-2/sidequest-daemon && git pull origin develop
```

```bash
# 2. Restart the affected service(s)
pf tmux close api-server
pf tmux run "cd /Users/keithavery/Projects/oq-2/sidequest-api && cargo run 2>&1 | tee /tmp/sq-api.log" --title api-server
```

Same pattern for `ui-dev` and `daemon` if their repos were updated.

```bash
# 3. Wait for health check (api may need to recompile)
pf tmux read api-server   # retry until "listening" appears
```

```bash
# 4. Refresh the browser
```
```
mcp__playwright__browser_navigate(url="http://localhost:5173")
```

```bash
# 5. Re-test the fixed issue and update ping-pong file
```

**When to trigger this cycle:**
- You see `fixed` + `Needs restart: yes` in the ping-pong file
- A service pane shows a crash and you suspect OQ-1 pushed breaking changes
- The user tells you OQ-1 has pushed a fix
- You notice the browser showing stale behavior after OQ-1 reports `fixed`

### Restart a single service (no git pull)

For crashes or hangs that don't involve code changes:

```bash
pf tmux close api-server
pf tmux run "cd /Users/keithavery/Projects/oq-2/sidequest-api && cargo run 2>&1 | tee /tmp/sq-api.log" --title api-server
```

### Read logs

```bash
pf tmux read <title>       # Current visible content in the pane
cat /tmp/sq-api.log         # Full log history (api)
cat /tmp/sq-ui.log          # Full log history (ui)
cat /tmp/sq-daemon.log      # Full log history (daemon)
```

### Push findings for OQ-1

If you discover something in the logs that OQ-1 needs to know (stack traces, error messages), copy the relevant log snippet into the ping-pong file task entry under `Notes:`.

---

## Phase 5: Teardown

When the user says the playtest is done:

### 5a. Shut down UX Designer
```
SendMessage:
  to: "ux-observer"
  type: "shutdown_request"
  content: "Playtest complete, shutting down"
```

Wait for acknowledgment, then:
```
TeamDelete:
  team_name: "sq-playtest"
```

### 5b. Close service panes
```bash
pf tmux close api-server
pf tmux close ui-dev
pf tmux close daemon
```

### 5c. Close browser
```
mcp__playwright__browser_close()
```

### 5d. Archive ping-pong file
```bash
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
mkdir -p /Users/keithavery/Projects/sq-playtest-archive
cp /Users/keithavery/Projects/sq-playtest-pingpong.md /Users/keithavery/Projects/sq-playtest-archive/$TIMESTAMP.md
```

### 5e. Summary

Read the ping-pong file and print a summary:
- Total findings by category (`[BUG]`, `[BUG-LOW]`, `[UX]`, `[GAP]`)
- Findings by status (open, in-progress, fixed, verified)
- Blocking bugs still open (if any)

---

## Multiplayer Mode

When the user requests multiplayer testing, use separate Playwright browser contexts
to simulate multiple players connecting to the same game session.

### Setup

Create two browser contexts (each gets independent cookies/session state):

```js
// Playwright MCP supports multiple tabs — open a second tab for Player 2
mcp__playwright__browser_navigate(url="http://localhost:5173")  // Tab 1 = Player 1
// Use browser_tabs to manage multiple tabs
```

### Player management

- **Player 1:** Primary tab — controlled by SM as usual
- **Player 2:** Second tab — SM alternates between tabs to drive both players
- Use `mcp__playwright__browser_tabs` to list and switch between tabs
- Each player gets a unique name (e.g., "Kael" and "Mira")
- Both players should select the same genre/world to join the same session

### Multiplayer verification checklist

Test these scenarios:
1. **Both players connect** — party pane shows both names
2. **Player 1 acts** — Player 2 sees the narration update
3. **Player 2 acts** — Player 1 sees the narration update
4. **Disconnect/reconnect** — one player refreshes, verify they rejoin the session
5. **Concurrent actions** — both players submit actions close together, verify no crash

### Screenshots

Take screenshots from both tabs for each significant moment. Use naming convention:
- `NNN-p1.png` — Player 1's view
- `NNN-p2.png` — Player 2's view

Compare both views to verify state synchronization.

</run>

<output>
Interactive playtest session with:
- 3 SideQuest services in tmux panes (api-server, ui-dev, daemon)
- Headed Playwright browser for gameplay interaction
- UX Designer teammate evaluating screenshots
- Cross-workspace bug coordination via ping-pong file at /Users/keithavery/Projects/sq-playtest-pingpong.md
- Service restart and log reading capability
- Multiplayer mode with dual Playwright tabs for concurrent player testing
</output>
