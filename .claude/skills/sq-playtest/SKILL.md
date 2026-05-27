---
name: sq-playtest
description: Interactive playtest — full-stack (UI + Playwright + UX Designer) or headless (API-only + Python driver). Coordinates cross-workspace bug reporting via ping-pong file with FIXER.
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

- this workspace [DRIVER]: drives the playtest — SM + UX Designer + Playwright browser
- other workspace [FIXER]: fixes bugs from the shared ping-pong file — SM + Dev + Architect

Read `sq-playtest/pingpong.md` in this skill directory for the full coordination protocol.

---

## Phase 1: Stack Launch (Full-Stack)

Poll for services- if services are not up, ask the user to start them. Start the save forensics service.

Launch Playwright browser

We have a set of host aliases to avoid cross-session contamination.
  127.0.0.1     player1.local
  127.0.0.1     player2.local
  127.0.0.1     player3.local
  127.0.0.1     player4.local

Open a headed browser to the UI:
```
mcp__playwright__browser_navigate(url="player1.local:5173")
```

Take an initial screenshot to confirm the UI loaded. **Always pass `filename` with an absolute path to the shared screenshots dir — never let Playwright drop into cwd:**

Open a tab to the OTEL dashboard: http://localhost:8765/dashboard
Open a tab to the save forensics: http://localhost:8799/forensics

```
mcp__playwright__browser_take_screenshot(filename="~Projects/sq-playtest-screenshots/000-initial-load.png")
```
---

## Phase 2: Setup

### Initialize ping-pong file 

```bash
mkdir .sq-playtest-screenshots
```

Create the ping-pong file (or reset it if starting a new session):

Write to `~/Projects/sq-playtest-pingpong.md`:

```markdown
# SideQuest Playtest — {today's date and time}

## Protocol

- **DRIVER** (playtest driver): adds new tasks, verifies fixes, takes screenshots
- **FIXER** (fix team): picks up tasks, implements fixes, updates status
- Status flow: `open` → `in-progress` → `fixed` → `verified`
- DRIVER ONLY appends new tasks and updates status to `verified`
- FIXER ONLY updates status to `in-progress` or `fixed`
- Neither side deletes entries — status transitions only

## How to Monitor (for FIXER)

Read this file periodically. When you see new `open` tasks:

1. Update the task status to `in-progress`
2. Fix the issue in the codebase
3. Update the task status to `fixed`
4. If the fix requires a server restart, add a note: `- **Needs restart:** yes`

## Status

Active playtest in progress.

## Tasks (newest first)
```

Tell the user: "Ping-pong file ready at `~/Projects/sq-playtest-pingpong.md`. Tell FIXER to monitor it."

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

### 3c. Check OTEL and save forensics

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
- **Screenshot:** ~Projects/sq-playtest-screenshots/{NNN}.png
- **Notes:** {additional context}
```

For **blocking bugs**, also prepend an attention signal at the top of the Tasks section:

```markdown
> **ATTENTION FIXER**: Blocking bug added — {brief description}. Please prioritize.
```

### 3e. Monitor ping-pong file (SM owns the sync cycle)

**You are responsible for watching the ping-pong file and driving the fix→verify loop.**

Before each new gameplay action, re-read the ping-pong file:

```bash
cat ~Projects/sq-playtest-pingpong.md
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


---


</run>

<output>
Interactive playtest session:

- Headed Playwright browser for gameplay interaction
- Multiplayer mode with dual Playwright tabs for concurrent player testing

- Cross-workspace bug coordination via ping-pong file at ../Projects/sq-playtest-pingpong.md
- Service restart and log reading capability
  </output>


