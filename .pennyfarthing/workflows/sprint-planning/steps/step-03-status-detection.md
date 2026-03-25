---
name: 'step-03-status-detection'
description: 'Apply intelligent status detection based on file existence and existing status'

# Path Definitions
workflow_path: '{project_root}/.pennyfarthing/workflows/sprint-planning'

# File References
thisStepFile: './step-03-status-detection.md'
nextStepFile: './step-04-generate-status-file.md'
---

<purpose>
Apply intelligent status detection based on file existence and existing status. Automatically upgrade story statuses based on physical story files and preserve advanced statuses from existing status files.
</purpose>

<instructions>
For each story from step 2, apply the following detection logic:
1. Check if story file exists at `{story_location}/{story-key}.md` (e.g., `stories/1-1-user-authentication.md`)
2. If story file exists, upgrade status to at least `ready-for-dev`
3. Apply preservation rule: If existing `{status_file}` exists with more advanced status, preserve it (never downgrade status)
4. Use the status flow references provided: Epic flows from backlog → in-progress → done, Stories flow from backlog → ready-for-dev → in-progress → review → done, Retrospectives toggle between optional ↔ done
</instructions>

<output>
Sprint status structure with all statuses intelligently detected and set based on file existence and existing status file values, ready for YAML generation.
</output>

# Step 3: Apply Intelligent Status Detection

## Goal

Apply intelligent status detection based on file existence and existing status.

## Actions

For each story, detect current status by checking files:

### Story File Detection

- Check: `{story_location}/{story-key}.md` (e.g., `stories/1-1-user-authentication.md`)
- If exists → upgrade status to at least `ready-for-dev`

### Preservation Rule

- If existing `{status_file}` exists and has more advanced status, preserve it
- Never downgrade status (e.g., don't change `done` to `ready-for-dev`)

## Status Flow Reference

### Epic Status

```
backlog → in-progress → done
```

- **backlog**: Epic not yet started
- **in-progress**: Epic actively being worked on (stories being created/implemented)
- **done**: All stories in epic completed

### Story Status

```
backlog → ready-for-dev → in-progress → review → done
```

- **backlog**: Story only exists in epic file
- **ready-for-dev**: Story file created (e.g., `stories/1-3-plant-naming.md`)
- **in-progress**: Developer actively working
- **review**: Ready for code review
- **done**: Completed

### Retrospective Status

```
optional ↔ done
```

- **optional**: Ready to be conducted but not required
- **done**: Finished
