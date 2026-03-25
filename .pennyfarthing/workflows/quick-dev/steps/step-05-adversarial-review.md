---
name: 'step-05-adversarial-review'
description: 'Construct diff and invoke adversarial review task'

workflow_path: '{project_root}/_bmad/bmm/workflows/bmad-quick-flow/quick-dev'
thisStepFile: './step-05-adversarial-review.md'
nextStepFile: './step-06-resolve-findings.md'
---

<purpose>
Construct a complete diff of all changes made during the workflow and invoke an adversarial review to identify potential issues. The review should be skeptical and comprehensive, not confirmatory. Process findings into a structured list for the user to address.
</purpose>

<instructions>
1. Construct diff from baseline_commit: if Git repo, use `git diff {baseline_commit}`; if no Git, list all modified files with their current state
2. Include all untracked files created during this workflow (step 2-4 only)
3. Invoke the adversarial review task with the complete diff as input
4. Receive findings from the review task
5. If zero findings found, halt and request guidance (this is suspicious)
6. For each finding, evaluate severity (Critical/High/Medium/Low) and validity (real/noise/undecided)
7. Order findings by severity, number them (F1, F2, etc.)
8. Present findings as structured list (table or TODO format) to the user
9. Load step-06-resolve-findings.md to let user choose resolution approach
</instructions>

<output>
- Complete diff of all changes since baseline_commit
- Adversarial review findings list with ID, severity, validity, and description
- Ordered by severity (Critical → Low)
- Ready for user to choose resolution approach (walk-through/auto-fix/skip)
</output>

# Step 5: Adversarial Code Review

**Goal:** Construct diff of all changes, invoke adversarial review task, present findings.

---

## AVAILABLE STATE

From previous steps:

- `{baseline_commit}` - Git HEAD at workflow start (CRITICAL for diff)
- `{execution_mode}` - "tech-spec" or "direct"
- `{tech_spec_path}` - Tech-spec file (if Mode A)

---

### 1. Construct Diff

Build complete diff of all changes since workflow started.

### If `{baseline_commit}` is a Git commit hash:

**Tracked File Changes:**

```bash
git diff {baseline_commit}
```

**New Untracked Files:**
Only include untracked files that YOU created during this workflow (steps 2-4).
Do not include pre-existing untracked files.
For each new file created, include its full content as a "new file" addition.

### If `{baseline_commit}` is "NO_GIT":

Use best-effort diff construction:

- List all files you modified during steps 2-4
- For each file, show the changes you made (before/after if you recall, or just current state)
- Include any new files you created with their full content
- Note: This is less precise than Git diff but still enables meaningful review

### Capture as {diff_output}

Merge all changes into `{diff_output}`.

**Note:** Do NOT `git add` anything - this is read-only inspection.

---

### 2. Invoke Adversarial Review

With `{diff_output}` constructed, invoke the review task. If possible, use information asymmetry: run this step, and only it, in a separate subagent or process with read access to the project, but no context except the `{diff_output}`.

```xml
<invoke-task>Review {diff_output} using {project_root}/_bmad/core/tasks/review-adversarial-general.xml</invoke-task>
```

**Platform fallback:** If task invocation not available, load the task file and execute its instructions inline, passing `{diff_output}` as the content.

The task should: review `{diff_output}` and return a list of findings.

---

### 3. Process Findings

Capture the findings from the task output.
**If zero findings:** HALT - this is suspicious. Re-analyze or request user guidance.
Evaluate severity (Critical, High, Medium, Low) and validity (real, noise, undecided).
DO NOT exclude findings based on severity or validity unless explicitly asked to do so.
Order findings by severity.
Number the ordered findings (F1, F2, F3, etc.).
If TodoWrite or similar tool is available, turn each finding into a TODO, include ID, severity, validity, and description in the TODO; otherwise present findings as a table with columns: ID, Severity, Validity, Description

---

## NEXT STEP

With findings in hand, load `step-06-resolve-findings.md` for user to choose resolution approach.

---

## SUCCESS METRICS

- Diff constructed from baseline_commit
- New files included in diff
- Task invoked with diff as input
- Findings received
- Findings processed into TODOs or table and presented to user

## FAILURE MODES

- Missing baseline_commit (can't construct accurate diff)
- Not including new untracked files in diff
- Invoking task without providing diff input
- Accepting zero findings without questioning
- Presenting fewer findings than the review task returned without explicit instruction to do so
