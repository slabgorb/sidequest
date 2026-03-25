# Step 2: Explore UI

<step-meta>
number: 2
name: explore
gate: false
</step-meta>

<purpose>
Systematically explore the UI to understand current state and identify areas of concern.
</purpose>

<instructions>
1. USE Playwright MCP for all browser interactions
2. Take initial screenshot of landing page
3. Identify main navigation routes and sections
4. Note any immediate issues (broken layouts, console errors, visual glitches)
5. Ask user which area to focus on
6. For each area: navigate, screenshot, interact, observe issues
7. Document all findings with screenshots
8. Present issues found and get user guidance on what to fix
</instructions>

<output>
Report findings:
- Current State: [screenshots showing landing page and main sections]
- Main Sections: [list navigation items found]
- Initial Observations: [notable findings]
- Issues Found: [list with descriptions and severity]
- Ready for user to select area or decide on fixes
</output>

## Purpose

Systematically explore the UI to understand current state and identify areas of concern.

## Mandatory Execution Rules

- USE Playwright MCP for all browser interactions
- TAKE screenshots at each major view
- DOCUMENT what you observe
- ASK user where to focus

## Initial Exploration

1. **Screenshot the landing page** - What do we see first?
2. **Identify navigation** - What are the main routes/sections?
3. **Note any immediate issues** - Broken layouts, console errors, visual glitches

**Present findings:**

```
## Current State

**Landing Page:** [screenshot]
**Main Sections:** [list navigation items found]
**Initial Observations:**
- [anything notable - good or bad]
```

## User-Guided Focus

Ask the user:

> What area would you like to focus on?
>
> I can see these sections: [list main navigation/features]
>
> Or describe what you'd like me to look at.

## Exploration Loop

For each area the user wants to explore:

1. **Navigate** - Use Playwright to go there
2. **Screenshot** - Capture the current state
3. **Interact** - Click buttons, fill forms, test interactions
4. **Observe** - Note any issues:
   - Visual bugs (misalignment, overflow, wrong colors)
   - Interaction bugs (buttons don't work, forms fail)
   - Console errors (check browser console if possible)
   - UX issues (confusing flow, missing feedback)

**Report findings as you go:**

```
## Exploring: [Section Name]

**Screenshot:** [image]
**Interactions Tested:** [what I clicked/typed]
**Issues Found:**
- [ ] Issue 1: [description]
- [ ] Issue 2: [description]

**No Issues:** [if clean]
```

<switch tool="AskUserQuestion">
  <case value="explore-more" next="LOOP">
    Explore more — Look at another section
  </case>
  <case value="investigate-issue" next="LOOP">
    Investigate issue — Dig deeper into a specific problem
  </case>
  <case value="fix-issues" next="LOOP">
    Fix issues — Ready to start fixing what we found
  </case>
  <case value="done" next="LOOP">
    Done — No issues found, exit workflow
  </case>
</switch>

## Next Step

When user is ready to fix issues, proceed to the fix phase.
