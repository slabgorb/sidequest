---
name: 'step-02-build-sprint-status'
description: 'Build sprint status structure from parsed epic and story data'

# Path Definitions
workflow_path: '{project_root}/.pennyfarthing/workflows/sprint-planning'

# File References
thisStepFile: './step-02-build-sprint-status.md'
nextStepFile: './step-03-status-detection.md'
---

<purpose>
Build sprint status structure from parsed epic and story data. Create the foundational structure that tracks all epics, stories, and retrospectives with their default statuses.
</purpose>

<instructions>
For each epic found from step 1, create entries in this exact order:
1. Epic entry with key `epic-{num}` and default status `backlog`
2. Story entries with key `{epic}-{story}-{title}` and default status `backlog`
3. Retrospective entry with key `epic-{num}-retrospective` and default status `optional`

Ensure all items are properly grouped by epic: Epic N entry, all stories for Epic N, retrospective for Epic N, Epic N+1 entry, etc. Follow the example structure provided in the Goal section.
</instructions>

<output>
A structured development_status YAML structure organized by epic, with all stories and retrospectives properly grouped, ready for status detection in the next step.
</output>

# Step 2: Build Sprint Status Structure

## Goal

Build sprint status structure from parsed epic and story data.

## Actions

For each epic found, create entries in this order:

1. **Epic entry** - Key: `epic-{num}`, Default status: `backlog`
2. **Story entries** - Key: `{epic}-{story}-{title}`, Default status: `backlog`
3. **Retrospective entry** - Key: `epic-{num}-retrospective`, Default status: `optional`

## Example Structure

```yaml
development_status:
  epic-1: backlog
  1-1-user-authentication: backlog
  1-2-account-management: backlog
  epic-1-retrospective: optional
```

## Ordering

Ensure items are grouped by epic:
- Epic N entry
- All stories for Epic N
- Retrospective for Epic N
- Epic N+1 entry
- etc.
