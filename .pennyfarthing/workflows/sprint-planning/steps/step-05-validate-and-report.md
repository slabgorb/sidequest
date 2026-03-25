---
name: 'step-05-validate-and-report'
description: 'Validate the generated sprint status file and report results'

# Path Definitions
workflow_path: '{project_root}/.pennyfarthing/workflows/sprint-planning'

# File References
thisStepFile: './step-05-validate-and-report.md'
nextStepFile: null
---

<purpose>
Validate the generated sprint status file and report results. Ensure data integrity and completeness before concluding the sprint planning workflow.
</purpose>

<instructions>
Perform comprehensive validation checks on the generated `{status_file}`:
1. Verify every epic in epic files appears in the status file
2. Verify every story in epic files appears in the status file
3. Verify every epic has a corresponding retrospective entry
4. Verify no items in status file that don't exist in epic files
5. Verify all status values are legal and match state machine definitions
6. Verify file is valid YAML syntax

Calculate and report totals: total epics, total stories, epics in-progress count, and stories done count.

Display completion summary to user with file location, total counts, and next steps for status file usage.
</instructions>

<output>
Validation report confirming all data integrity checks pass, summary statistics showing epic and story counts with status breakdowns, and confirmation message that sprint status has been successfully generated.
</output>

# Step 5: Validate and Report

## Goal

Validate the generated sprint status file and report results.

## Validation Checks

Perform the following validation checks:

- [ ] Every epic in epic files appears in `{status_file}`
- [ ] Every story in epic files appears in `{status_file}`
- [ ] Every epic has a corresponding retrospective entry
- [ ] No items in `{status_file}` that don't exist in epic files
- [ ] All status values are legal (match state machine definitions)
- [ ] File is valid YAML syntax

## Count Totals

Calculate and report:

- Total epics: `{epic_count}`
- Total stories: `{story_count}`
- Epics in-progress: `{in_progress_count}`
- Stories done: `{done_count}`

## Completion Summary

Display to user:

**Sprint Status Generated Successfully**

- **File Location:** `{status_file}`
- **Total Epics:** `{epic_count}`
- **Total Stories:** `{story_count}`
- **Epics In Progress:** `{epics_in_progress_count}`
- **Stories Completed:** `{done_count}`

## Next Steps

1. Review the generated `{status_file}`
2. Use this file to track development progress
3. Agents will update statuses as they work
4. Re-run this workflow to refresh auto-detected statuses
