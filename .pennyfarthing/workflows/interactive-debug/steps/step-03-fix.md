# Step 3: Fix Issues

<step-meta>
number: 3
name: fix
gate: false
</step-meta>

<purpose>
Work through identified issues one by one, making fixes and verifying them in the browser.
</purpose>

<instructions>
1. FIX one issue at a time
2. For each issue: Analyze (reproduce, locate source, understand why)
3. Consult UX Designer perspective on visual/UX fixes
4. Implement focused code changes
5. VERIFY each fix in browser with Playwright MCP
6. Take before/after screenshots
7. Confirm with user that fix is correct
8. TRACK all changes for final commit
9. Repeat until all issues are fixed and verified
</instructions>

<output>
Provide for each fix:
- Issue description
- Before screenshot
- After screenshot
- Files changed with descriptions
- Confirmation from user
- Running list of all changes made
- Final summary of all fixes ready for commit
</output>

## Purpose

Work through identified issues one by one, making fixes and verifying them in the browser.

## Mandatory Execution Rules

- FIX one issue at a time
- VERIFY each fix in the browser before moving on
- TRACK all changes made for the final commit
- CONSULT UX Designer perspective on visual fixes

## Issue Triage

Present the issues found:

```
## Issues to Fix

| # | Issue | Severity | Type |
|---|-------|----------|------|
| 1 | [description] | High/Med/Low | Visual/Interaction/UX |
| 2 | [description] | High/Med/Low | Visual/Interaction/UX |
...

Which issue should we tackle first?
```

## Fix Loop

For each issue:

### 1. Analyze

- **Reproduce** - Use Playwright to show the bug
- **Locate** - Find the source file(s) responsible
- **Understand** - Why is this happening?

### 2. Consult UX Designer

For visual/UX issues, apply UX Designer thinking:

- Is this a one-off fix or a pattern problem?
- Does the fix align with design system?
- Are there accessibility implications?
- Will this fix break other states (hover, focus, mobile)?

### 3. Implement Fix

- Make the code change
- Keep changes minimal and focused

### 4. Verify

- Use Playwright to navigate back to the affected area
- Take a screenshot showing the fix
- Confirm with user:

```
## Fixed: [Issue Description]

**Before:** [screenshot or description]
**After:** [screenshot]
**Files Changed:** [list]

Does this look right?
- **[Y] Yes** - Mark fixed, next issue
- **[N] No** - Needs adjustment
```

### 5. Track

Maintain a running list:

```
## Changes Made

- [ ] `src/components/Panel.css` - Fixed overflow on main panel
- [ ] `src/components/Button.tsx` - Added missing click handler
...
```

<switch tool="AskUserQuestion">
  <case value="yes" next="LOOP">
    Yes — Mark fixed, next issue
  </case>
  <case value="no" next="LOOP">
    No — Needs adjustment
  </case>
  <case value="revert" next="LOOP">
    Revert — Undo this change
  </case>
  <case value="add-issue" next="LOOP">
    Add issue — Found another issue while fixing
  </case>
  <case value="verify-all" next="LOOP">
    Verify all — Re-check all fixes together
  </case>
  <case value="commit" next="step-04-commit">
    Commit — All issues fixed, ready to commit
  </case>
</switch>

## Next Step

When all issues are fixed and verified, proceed to commit.
