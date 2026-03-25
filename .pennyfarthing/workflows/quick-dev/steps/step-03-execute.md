---
name: 'step-03-execute'
description: 'Execute implementation - iterate through tasks, write code, run tests'

workflow_path: '{project_root}/_bmad/bmm/workflows/bmad-quick-flow/quick-dev'
thisStepFile: './step-03-execute.md'
nextStepFile: './step-04-self-check.md'
---

<purpose>
Execute all planned tasks in sequence without pausing for approval between tasks. Write code following identified patterns, run tests to verify functionality, and only halt for blocking issues that require user guidance.
</purpose>

<instructions>
1. For each task in the plan (from tech-spec or mental plan):
   - Load relevant source files to understand context
   - Implement changes following existing code patterns
   - Write or update tests to verify the specific acceptance criteria for this task
   - Mark task complete and move to the next task immediately
2. Handle errors pragmatically: retry, look for patterns, test incrementally
3. Only halt and request guidance if facing a blocking issue (3+ failures, ambiguous decision)
4. Track all completed work for the next step (self-check)
5. Once all tasks are complete (or blocked), proceed to step-04-self-check.md
</instructions>

<output>
- Implemented code changes for all tasks
- Tests written and passing for new/modified functionality
- All existing tests still passing
- List of completed tasks checked off
- Any blocking issues documented with clear explanation
- Ready to transition to self-check phase
</output>

# Step 3: Execute Implementation

**Goal:** Implement all tasks, write tests, follow patterns, handle errors.

**Critical:** Continue through ALL tasks without stopping for milestones.

---

## AVAILABLE STATE

From previous steps:

- `{baseline_commit}` - Git HEAD at workflow start
- `{execution_mode}` - "tech-spec" or "direct"
- `{tech_spec_path}` - Tech-spec file (if Mode A)
- `{project_context}` - Project patterns (if exists)

From context:

- Mode A: Tasks and AC extracted from tech-spec
- Mode B: Tasks and AC from step-02 mental plan

---

## EXECUTION LOOP

For each task:

### 1. Load Context

- Read files relevant to this task
- Review patterns from project-context or observed code
- Understand dependencies

### 2. Implement

- Write code following existing patterns
- Handle errors appropriately
- Follow conventions observed in codebase
- Add appropriate comments where non-obvious

### 3. Test

- Write tests if appropriate for the change
- Run existing tests to catch regressions
- Verify the specific AC for this task

### 4. Mark Complete

- Check off task: `- [x] Task N`
- Continue to next task immediately

---

## HALT CONDITIONS

**HALT and request guidance if:**

- 3 consecutive failures on same task
- Tests fail and fix is not obvious
- Blocking dependency discovered
- Ambiguity that requires user decision

**Do NOT halt for:**

- Minor issues that can be noted and continued
- Warnings that don't block functionality
- Style preferences (follow existing patterns)

---

## CONTINUOUS EXECUTION

**Critical:** Do not stop between tasks for approval.

- Execute all tasks in sequence
- Only halt for blocking issues
- Tests failing = fix before continuing
- Track all completed work for self-check

---

## NEXT STEP

When ALL tasks are complete (or halted on blocker), load `step-04-self-check.md`.

---

## SUCCESS METRICS

- All tasks attempted
- Code follows existing patterns
- Error handling appropriate
- Tests written where appropriate
- Tests passing
- No unnecessary halts

## FAILURE MODES

- Stopping for approval between tasks
- Ignoring existing patterns
- Not running tests after changes
- Giving up after first failure
- Not following project-context rules (if exists)
