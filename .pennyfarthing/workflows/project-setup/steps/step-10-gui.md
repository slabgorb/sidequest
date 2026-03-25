# Step 10: BikeRack GUI (Optional)

<purpose>
Optionally configure the BikeRack GUI, the graphical panel viewer for Claude Code. BikeRack renders sprint tracking, workflow visualization, and enhanced tool display panels in a browser window alongside your terminal.
</purpose>

<instructions>
1. Explain what BikeRack GUI provides
2. Show the three display modes (TUI, GUI, IDE)
3. Offer to configure GUI mode
4. Verify the setup works
</instructions>

<output>
- User informed about BikeRack GUI features
- GUI configured if user requested
- User knows the three display modes
</output>

## WHAT IS BIKERACK GUI?

```
BikeRack GUI - Panel Viewer for Claude Code
═════════════════════════════════════════════

BikeRack renders framework panels in three display modes:

┌─────────────────────────────────────────────────────────────────────┐
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│  │ Sprint Panel │ │ Workflow     │ │ Changed      │                │
│  │              │ │ Panel        │ │ Files        │                │
│  │ • Status     │ │              │ │              │                │
│  │ • Stories    │ │ • Phase      │ │ • Diffs      │                │
│  │ • Progress   │ │ • Handoffs   │ │ • Staging    │                │
│  └──────────────┘ └──────────────┘ └──────────────┘                │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                     Message Panel                              │ │
│  │                                                                │ │
│  │  Claude: I'll help you implement that feature...               │ │
│  │                                                                │ │
│  │  [Tool Call] Reading src/components/App.tsx                    │ │
│  │  [Tool Call] Writing src/components/Feature.tsx                │ │
│  │                                                                │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

Display Modes:
  • TUI  — `pf bikerack start` — terminal panels alongside Claude Code CLI
  • GUI  — `just gui` — full browser UI with dockview panel layout
  • IDE  — VS Code / Cursor sidebar panels via WheelHub API

Panels:
  • Sprint panel - Live sprint status and story tracking
  • Workflow panel - BikeLane phase visualization
  • Changed files panel - Git diff integration
  • Themed personas - Character portraits and styles
  • Tool visualization - Enhanced tool call display
  • Quick actions - One-click workflow commands
```

## DISPLAY MODE SELECTION

```
BikeRack Display Modes
═══════════════════════

How would you like to view BikeRack panels?

[1] TUI mode (recommended for terminal users)
    pf bikerack start
    Panels render in tmux panes alongside Claude Code

[2] GUI mode (full browser experience)
    just gui
    Full dockview layout in a browser window

[3] IDE mode (VS Code / Cursor)
    Sidebar panels via WheelHub API
    Requires WheelHub server running

[4] Skip - I'll use terminal only
    BikeRack is optional, CLI works fine without it
```

## VERIFICATION

After configuration:

```bash
# Check WheelHub server (reads port from .bikerack-port, default 2898)
pf bikerack status

# TUI mode test
pf bikerack start --dry-run

# GUI mode test
just gui --help 2>/dev/null || echo "Add 'gui' recipe to justfile"
```

## JUSTFILE INTEGRATION

If justfile was created in step 6, offer to add GUI recipe:

```
Add GUI recipe to justfile?

[Y] Yes, add recipe:
    gui:
        pf bikerack start

[N] No, I'll launch it manually
```

## BIKERACK FEATURES DEEP DIVE

If user selects "Learn more":

```
BikeRack Panel Features
════════════════════════

PANELS (draggable, resizable):
┌────────────────┬─────────────────────────────────────────────┐
│ Panel          │ Features                                    │
├────────────────┼─────────────────────────────────────────────┤
│ Message        │ Conversation display, streaming, markdown   │
│ Sprint         │ Current sprint, stories, progress bars      │
│ Workflow       │ BikeLane phases, handoff detection          │
│ Changed Files  │ Git status, staged/unstaged, diffs          │
│ Acceptance     │ Story AC checkboxes                         │
│ Todos          │ Task list tracking                          │
│ Background     │ Background task monitoring                  │
│ Debug          │ OTEL spans, performance data                │
│ Git            │ Branch info, commit history                 │
│ Settings       │ Theme, fonts, colors                        │
└────────────────┴─────────────────────────────────────────────┘

TOOL VISUALIZATION:
  • Collapsible tool calls with intent summaries
  • Stacked consecutive tool calls
  • Color-coded by tool type
  • Execution time display

PERSONA INTEGRATION:
  • Character portraits for each agent
  • Theme-specific colors and styles
  • Agent popup with role info

QUICK ACTIONS:
  • One-click workflow commands
  • Handoff buttons
```

## SUCCESS CRITERIA

- User informed about BikeRack display modes
- Preferred display mode configured (if requested)
- Justfile updated (if applicable)
- User knows how to launch panels

## NEXT STEP

After BikeRack GUI setup, proceed to `step-11-complete.md` to finalize project setup and run validation.

<switch tool="AskUserQuestion">
  <case value="try-tui" next="LOOP">
    Try TUI mode
  </case>
  <case value="try-gui" next="LOOP">
    Try GUI mode
  </case>
  <case value="skip" next="step-11-complete">
    Skip BikeRack for now
  </case>
</switch>
</output>
