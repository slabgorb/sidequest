---
name: 'step-04-generate-status-file'
description: 'Generate the sprint status YAML file with all epics, stories, and retrospectives'

# Path Definitions
workflow_path: '{project_root}/.pennyfarthing/workflows/sprint-planning'

# File References
thisStepFile: './step-04-generate-status-file.md'
nextStepFile: './step-05-validate-and-report.md'
---

<purpose>
Generate the sprint status YAML file with all epics, stories, and retrospectives. Create or update the status file with complete metadata and development_status structure.
</purpose>

<instructions>
Create or update `{status_file}` with the complete structure:
1. Add metadata comments for documentation: generated date, project name, tracking_system (file-system), and story_location
2. Include comprehensive status definitions comments for Epic, Story, and Retrospective statuses with their transitions
3. Add workflow notes explaining epic transitions, parallel story work, SM story creation patterns, and dev to review workflow
4. CRITICAL: Include metadata fields TWICE - once as comments for documentation, once as YAML key:value fields for parsing
5. Populate development_status section with all items from step 3 in proper epic grouping order
</instructions>

<output>
A complete, well-documented sprint status YAML file at `{status_file}` with all epics, stories, and retrospectives properly structured and ready for validation.
</output>

# Step 4: Generate Sprint Status File

## Goal

Generate the sprint status YAML file with all epics, stories, and retrospectives.

## Actions

Create or update `{status_file}` with the following structure:

## File Structure

```yaml
# generated: {date}
# project: {project_name}
# tracking_system: file-system
# story_location: {story_location}

# STATUS DEFINITIONS:
# ==================
# Epic Status:
#   - backlog: Epic not yet started
#   - in-progress: Epic actively being worked on
#   - done: All stories in epic completed
#
# Epic Status Transitions:
#   - backlog → in-progress: Automatically when first story is created
#   - in-progress → done: Manually when all stories reach 'done' status
#
# Story Status:
#   - backlog: Story only exists in epic file
#   - ready-for-dev: Story file created in stories folder
#   - in-progress: Developer actively working on implementation
#   - review: Ready for code review
#   - done: Story completed
#
# Retrospective Status:
#   - optional: Can be completed but not required
#   - done: Retrospective has been completed
#
# WORKFLOW NOTES:
# ===============
# - Epic transitions to 'in-progress' automatically when first story is created
# - Stories can be worked in parallel if team capacity allows
# - SM typically creates next story after previous one is 'done' to incorporate learnings
# - Dev moves story to 'review', then runs code-review

generated: {date}
project: {project_name}
tracking_system: file-system
story_location: {story_location}

development_status:
  # All epics, stories, and retrospectives in order
```

## Critical Notes

- **CRITICAL**: Metadata appears TWICE - once as comments (#) for documentation, once as YAML key:value fields for parsing
- Ensure all items are ordered: epic, its stories, its retrospective, next epic...
- Write the complete sprint status YAML to `{status_file}`
