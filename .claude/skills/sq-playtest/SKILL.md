---
name: sq-playtest
description: Interactive playtest — full-stack (UI + Playwright + UX Designer) or headless (API-only + Python driver). Coordinates cross-workspace bug reporting via ping-pong file with OQ-1.
---

# SideQuest Playtest Skill

<run>
You are now the **Playtest SM**. You coordinate an interactive playtest of the SideQuest game engine.

**Two modes:**

- **Full-stack** (default): UI + daemon + Playwright browser + UX Designer for visual testing
- **Headless** (`/sq-playtest headless`): API-only + Python driver for game loop, narration, and backend testing

If the user said "headless" (or "headless playtest", "API playtest", "no UI"), skip to **Headless Mode** below.
Otherwise, proceed with the full-stack flow.

**Architecture (full-stack):**

- this workspace: drives the playtest — SM + UX Designer + Playwright browser
- other workspace: fixes bugs from the shared ping-pong file — SM + Dev + Architect

Read `sq-playtest/pingpong.md` in this skill directory for the full coordination protocol.

---

## Phase 1: Stack Launch (Full-Stack)

Poll for services- if services are not up, ask the user to start them.

Launch Playwright browser

Open a headed browser to the UI:

```
mcp__playwright__browser_navigate(url="http://localhost:5173")
```

Take an initial screenshot to confirm the UI loaded. **Always pass `filename` with an absolute path to the shared screenshots dir — never let Playwright drop into cwd:**

```
mcp__playwright__browser_take_screenshot(filename="/Users/keithavery/Projects/sq-playtest-screenshots/000-initial-load.png")
```

If the page shows an error (connection refused, blank page), check `pf tmux read ui-dev` for errors.

---

## Phase 2: Setup


### Initialize ping-pong file 

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


### 3b. Check logs (in /tmp)

### 3c. Open the otel dashboard and check it

### 3d. Triage findings

For each finding:

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


## Multiplayer Mode

When the user requests multiplayer testing, use separate Playwright browser contexts
to simulate multiple players connecting to the same game session.

### Setup

Create multiple contexts (each gets independent cookies/session state):

```js
// Playwright MCP supports multiple tabs — open a second tab for Player 2
mcp__playwright__browser_navigate((url = "http://localhost:5173")); // Tab 1 = Player 1
// Use browser_tabs to manage multiple tabs
```


### Hosts File

Hosts file entries allow for protection of state
player1.local
player2.local
player3.local
player4.local


</run>

<output>
Interactive playtest session:

- Headed Playwright browser for gameplay interaction
- Multiplayer mode with dual Playwright tabs for concurrent player testing

- Cross-workspace bug coordination via ping-pong file at ../Projects/sq-playtest-pingpong.md
- Service restart and log reading capability
  </output>


