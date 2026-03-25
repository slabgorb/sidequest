---
name: 'step-06-resolve-findings'
description: 'Handle review findings interactively, apply fixes, update tech-spec with final status'

workflow_path: '{project_root}/_bmad/bmm/workflows/bmad-quick-flow/quick-dev'
thisStepFile: './step-06-resolve-findings.md'
---

<purpose>
Present the user with three options for handling adversarial review findings: walk through each finding individually for discussion and decision, automatically fix items classified as "real", or skip all findings and proceed. Apply chosen approach, update tech-spec with final status, and provide completion summary.
</purpose>

<instructions>
1. Present three resolution options to user: [1] Walk-through, [2] Auto-fix, [3] Skip
2. Execute chosen option:
   - Walk-through: For each finding, present context, ask fix/skip/discuss, apply fixes as requested
   - Auto-fix: Filter to "real" findings, apply all fixes, report results
   - Skip: Acknowledge findings were reviewed, note user chose to proceed without fixes
3. If Mode A (tech-spec): Load tech-spec file, update status to "Completed", add review notes section with findings summary, save
4. Present completion output explaining what was implemented at appropriate detail level
5. Inform user the workflow is complete and ready to commit
</instructions>

<output>
- Findings status (all addressed, auto-fixed with count, or skipped)
- List of applied fixes (if applicable)
- Tech-spec updated with completion status and review notes (Mode A only)
- Final completion summary with what was implemented, files modified, tests status, findings summary
- Clear next steps for user (commit changes, run more tests, or start new session)
</output>

# Step 6: Resolve Findings

**Goal:** Handle adversarial review findings interactively, apply fixes, finalize tech-spec.

---

## AVAILABLE STATE

From previous steps:

- `{baseline_commit}` - Git HEAD at workflow start
- `{execution_mode}` - "tech-spec" or "direct"
- `{tech_spec_path}` - Tech-spec file (if Mode A)
- Findings table from step-05

---

## RESOLUTION OPTIONS

Present choice to user:

```
How would you like to handle these findings?

**[1] Walk through** - Discuss each finding individually
**[2] Auto-fix** - Automatically fix issues classified as "real"
**[3] Skip** - Acknowledge and proceed to commit
```

---

## OPTION 1: WALK THROUGH

For each finding in order:

1. Present the finding with context
2. Ask: **fix now / skip / discuss**
3. If fix: Apply the fix immediately
4. If skip: Note as acknowledged, continue
5. If discuss: Provide more context, re-ask
6. Move to next finding

After all findings processed, summarize what was fixed/skipped.

---

## OPTION 2: AUTO-FIX

1. Filter findings to only those classified as "real"
2. Apply fixes for each real finding
3. Report what was fixed:

```
**Auto-fix Applied:**
- F1: {description of fix}
- F3: {description of fix}
...

Skipped (noise/uncertain): F2, F4
```

---

## OPTION 3: SKIP

1. Acknowledge all findings were reviewed
2. Note that user chose to proceed without fixes
3. Continue to completion

---

## UPDATE TECH-SPEC (Mode A only)

If `{execution_mode}` is "tech-spec":

1. Load `{tech_spec_path}`
2. Update status to "Completed"
3. Add review notes:
   ```
   ## Review Notes
   - Adversarial review completed
   - Findings: {count} total, {fixed} fixed, {skipped} skipped
   - Resolution approach: {walk-through/auto-fix/skip}
   ```
4. Save changes

---

## COMPLETION OUTPUT

```
**Review complete. Ready to commit.**

**Implementation Summary:**
- {what was implemented}
- Files modified: {count}
- Tests: {status}
- Review findings: {X} addressed, {Y} skipped

{Explain what was implemented based on user_skill_level}
```

---

## WORKFLOW COMPLETE

This is the final step. The Quick Dev workflow is now complete.

User can:

- Commit changes
- Run additional tests
- Start new Quick Dev session

---

## SUCCESS METRICS

- User presented with resolution options
- Chosen approach executed correctly
- Fixes applied cleanly (if applicable)
- Tech-spec updated with final status (Mode A)
- Completion summary provided
- User understands what was implemented

## FAILURE MODES

- Not presenting resolution options
- Auto-fixing "noise" or "uncertain" findings
- Not updating tech-spec after resolution (Mode A)
- No completion summary
- Leaving user unclear on next steps
