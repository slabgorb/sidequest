---
name: 'step-04-review'
description: 'Review and finalize the tech-spec'

wipFile: '{implementation_artifacts}/tech-spec-wip.md'
quick_dev_workflow: '{project_root}/.pennyfarthing/workflows/quick-dev/workflow.yaml'
---

<purpose>Present complete spec for user review, iterate on feedback, finalize to ready-for-dev status, and provide clear next-step guidance.</purpose>

<instructions>Present complete spec, handle review feedback, finalize when approved (rename file, update status), present final menu with adversarial review and dev options.</instructions>

<output>Finalized tech-spec at {implementation_artifacts}/tech-spec-{slug}.md with status 'ready-for-dev' and stepsCompleted: [1, 2, 3, 4].</output>

# Step 4: Review & Finalize

**Progress: Step 4 of 4** - Final Step

## RULES:

- MUST NOT skip steps.
- MUST NOT optimize sequence.
- MUST follow exact instructions.

## CONTEXT:

- Requires `{wipFile}` from Step 3.
- MUST present COMPLETE spec content. Iterate until user is satisfied.

## READY FOR DEVELOPMENT STANDARD:

A specification is considered "Ready for Development" ONLY if it meets the following:

- **Actionable**: Every task has a clear file path and specific action.
- **Logical**: Tasks are ordered by dependency (lowest level first).
- **Testable**: All ACs follow Given/When/Then and cover happy path and edge cases.
- **Complete**: All investigation results from Step 2 are inlined; no placeholders or "TBD".
- **Self-Contained**: A fresh agent can implement the feature without reading the workflow history.

## SEQUENCE OF INSTRUCTIONS

### 1. Load and Present Complete Spec

**Read `{wipFile}` completely and extract `slug` from frontmatter for later use.**

**Present to user:**

"Here's your complete tech-spec. Please review:"

[Display the complete spec content - all sections]

"**Quick Summary:**

- {task_count} tasks to implement
- {ac_count} acceptance criteria to verify
- {files_count} files to modify"

**Present review menu:**


**HALT and wait for user selection.**

### 2. Handle Review Feedback

a) **If user requests changes:**

- Make the requested edits to `{wipFile}`
- Re-present the affected sections
- Ask if there are more changes
- Loop until user is satisfied

b) **If the spec does NOT meet the "Ready for Development" standard:**

- Point out the missing/weak sections (e.g., non-actionable tasks, missing ACs).
- Propose specific improvements to reach the standard.
- Make the edits once the user agrees.

c) **If user has questions:**

- Answer questions about the spec
- Clarify any confusing sections
- Make clarifying edits if needed

### 3. Finalize the Spec

**When user confirms the spec is good AND it meets the "Ready for Development" standard:**

a) Update `{wipFile}` frontmatter:

   ```yaml
   ---
   # ... existing values ...
   status: 'ready-for-dev'
   stepsCompleted: [1, 2, 3, 4]
   ---
   ```

b) **Rename WIP file to final filename:**
   - Using the `slug` extracted in Section 1
   - Rename `{wipFile}` → `{implementation_artifacts}/tech-spec-{slug}.md`
   - Store this as `finalFile` for use in menus below

### 4. Present Final Menu

a) **Display completion message and menu:**

```
**Tech-Spec Complete!**

Saved to: {finalFile}

---

**Next Steps:**

[B] Begin Development - start implementing now (not recommended)
[D] Done - exit workflow

---

Once you are fully satisfied with the spec (ideally after **Adversarial Review**),
it is recommended to run implementation in a FRESH CONTEXT for best results.

Copy this prompt to start dev:

quick-dev {finalFile}

This ensures the dev agent has clean context focused solely on implementation.
```

b) **HALT and wait for user selection.**

### 5. Exit Workflow

**When user selects [D]:**

"**All done!** Your tech-spec is ready at:

`{finalFile}`

When you're ready to implement, run:

```
quick-dev {finalFile}
```

Ship it!"

---

## REQUIRED OUTPUTS:

- MUST update status to 'ready-for-dev'.
- MUST rename file to `tech-spec-{slug}.md`.
- MUST provide clear next-step guidance and recommend fresh context for dev.

## VERIFICATION CHECKLIST:

- [ ] Complete spec presented for review.
- [ ] Requested changes implemented.
- [ ] Spec verified against **READY FOR DEVELOPMENT** standard.
- [ ] `stepsCompleted: [1, 2, 3, 4]` set and file renamed.

<switch tool="AskUserQuestion">
  <case value="adversarial-review" next="LOOP">
    Adversarial Review — critique of the spec (recommended)
  </case>
  <case value="begin-development" next="LOOP">
    Begin Development — start implementing now (not recommended)
  </case>
  <case value="done" next="LOOP">
    Done — exit workflow
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode — get expert feedback before dev
  </case>
</switch>
