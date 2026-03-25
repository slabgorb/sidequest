---
name: 'step-04-self-check'
description: 'Self-audit implementation against tasks, tests, AC, and patterns'

workflow_path: '{project_root}/_bmad/bmm/workflows/bmad-quick-flow/quick-dev'
thisStepFile: './step-04-self-check.md'
nextStepFile: './step-05-adversarial-review.md'
---

<purpose>
Perform a comprehensive self-audit of the implementation before external review. Verify that all tasks are complete, tests pass, acceptance criteria are satisfied, and code follows project patterns. Update tech-spec status if in Mode A. Provide a clear summary for the adversarial review phase.
</purpose>

<instructions>
1. Verify all tasks marked complete with no skipped work
2. Run full test suite and confirm all tests passing
3. For each acceptance criterion, verify it is demonstrably satisfied
4. Review all modified code to ensure it follows existing patterns and project-context rules
5. If Mode A (tech-spec): load tech-spec file, mark all tasks as [x], update status to "Implementation Complete", save
6. Present implementation summary to transition to review phase
7. Load step-05-adversarial-review.md to proceed
</instructions>

<output>
- Verification checklist: Tasks ✓, Tests ✓, AC ✓, Patterns ✓
- Test suite run results (all passing)
- Tech-spec updated with completion status (Mode A only)
- Implementation summary showing what was built, files modified, and test status
- Transition message to adversarial review phase
</output>

# Step 4: Self-Check

**Goal:** Audit completed work against tasks, tests, AC, and patterns before external review.

---

## AVAILABLE STATE

From previous steps:

- `{baseline_commit}` - Git HEAD at workflow start
- `{execution_mode}` - "tech-spec" or "direct"
- `{tech_spec_path}` - Tech-spec file (if Mode A)
- `{project_context}` - Project patterns (if exists)

---

## SELF-CHECK AUDIT

### 1. Tasks Complete

Verify all tasks are marked complete:

- [ ] All tasks from tech-spec or mental plan marked `[x]`
- [ ] No tasks skipped without documented reason
- [ ] Any blocked tasks have clear explanation

### 2. Tests Passing

Verify test status:

- [ ] All existing tests still pass
- [ ] New tests written for new functionality
- [ ] No test warnings or skipped tests without reason

### 3. Acceptance Criteria Satisfied

For each AC:

- [ ] AC is demonstrably met
- [ ] Can explain how implementation satisfies AC
- [ ] Edge cases considered

### 4. Patterns Followed

Verify code quality:

- [ ] Follows existing code patterns in codebase
- [ ] Follows project-context rules (if exists)
- [ ] Error handling consistent with codebase
- [ ] No obvious code smells introduced

---

## UPDATE TECH-SPEC (Mode A only)

If `{execution_mode}` is "tech-spec":

1. Load `{tech_spec_path}`
2. Mark all tasks as `[x]` complete
3. Update status to "Implementation Complete"
4. Save changes

---

## IMPLEMENTATION SUMMARY

Present summary to transition to review:

```
**Implementation Complete!**

**Summary:** {what was implemented}
**Files Modified:** {list of files}
**Tests:** {test summary - passed/added/etc}
**AC Status:** {all satisfied / issues noted}

Proceeding to adversarial code review...
```

---

## NEXT STEP

Proceed immediately to `step-05-adversarial-review.md`.

---

## SUCCESS METRICS

- All tasks verified complete
- All tests passing
- All AC satisfied
- Patterns followed
- Tech-spec updated (if Mode A)
- Summary presented

## FAILURE MODES

- Claiming tasks complete when they're not
- Not running tests before proceeding
- Missing AC verification
- Ignoring pattern violations
- Not updating tech-spec status (Mode A)
