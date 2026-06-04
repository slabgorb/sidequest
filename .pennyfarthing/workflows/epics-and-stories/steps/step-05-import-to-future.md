---
name: 'step-05-import-to-future'
description: 'Create initiative file and import validated epics into sprint/future.yaml backlog'

# Path Definitions
workflow_path: '{project_root}/.pennyfarthing/workflows/epics-and-stories'

# File References
thisStepFile: './step-05-import-to-future.md'
workflowFile: '{workflow_path}/workflow.yaml'
outputFile: '{planning_artifacts}/epics.md'
futureYaml: '{project_root}/sprint/future.yaml'
---

<purpose>
To import the validated and complete epics and stories from the epics.md document into the sprint/future.yaml backlog system, making them available for sprint planning and story promotion. This is the final step that makes the epics accessible through the sprint management system.
</purpose>

<instructions>
1. Determine the initiative name from the epics document (prompt user if not obvious)
2. Read current future.yaml to find the next epic number (highest epic-N + 1)
3. Read the validated epics.md output and construct the YAML structure
4. Display a preview to the user showing epic numbers, initiative structure, and story IDs
5. Get user confirmation that the preview looks correct
6. If confirmed, append the new initiative and epics to future.yaml using yq
7. Verify the import by checking that epic appears in future.yaml with correct numbering
8. Display completion message with epic number, initiative name, and story count
</instructions>

<output>
- Initiative file created at sprint/initiative-{name}.yaml with epic metadata
- Initiative name added to sprint/future.yaml
- Epic assigned with correct sequential number (epic-N)
- All stories with proper IDs (epic-N-story-M format)
- Dry-run preview showing exactly what will be imported
- Verification that both initiative file and future.yaml entry exist
- Completion message with next steps for sprint planning
</output>

# Step 5: Import to Future Backlog

## STEP GOAL:

To import the validated epics and stories into `sprint/future.yaml` so they appear in the backlog and can be promoted to sprints.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER skip this step - epics must be in future.yaml to be scheduled
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, confirming import with user
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style

### Step-Specific Rules:

- 🎯 Focus ONLY on importing to future.yaml
- 💬 Ask user for initiative name if not obvious from document
- 🚫 FORBIDDEN to modify the validated epics document
- ✅ Show dry-run output before applying

## IMPORT PROCESS:

### 1. Determine Initiative Name

Look at the epics document title and ask user:

> "What should this initiative be called in future.yaml?"
>
> Suggested: `{extracted_title}`

Wait for user confirmation or alternative name.

### 2. Determine Next Epic Number

Read `sprint/future.yaml` and find the highest `epic-N` ID currently in use:

```bash
yq '.future.initiatives[].epics[].id' sprint/future.yaml | grep -oE 'epic-[0-9]+' | sed 's/epic-//' | sort -n | tail -1
```

The next epic gets `epic-{N+1}`. Stories use `{N+1}-{story_number}` format.

### 3. Construct and Preview

Read the validated epics.md output file. For each epic, construct the YAML structure:

```yaml
- id: epic-{N}
  title: "Epic: {epic_title}"
  points: {total_points}
  priority: {priority}
  repos: {repo}
  stories:
    - id: "{N}-1"
      title: "{story_title}"
      points: {points}
      type: {type}
      status: backlog
      workflow: {workflow}
      priority: {priority}
      repos: {repo}
```

Display the full preview to the user showing:
- Next epic number that will be assigned
- Initiative structure
- All stories with IDs

### 4. Confirm and Apply

Ask user: "Does this look correct? [Y] Yes, import to future.yaml / [N] No, make changes"

**If Y:**

**Step A — Create the initiative file** (`sprint/initiative-{initiative_name}.yaml`).
This file is required by the sprint system to hold epic metadata. Use the following structure:

```yaml
name: "{Initiative Display Name}"
description: |
  {Brief description extracted from the epics document}
status: backlog
blocked_by:
total_points: {sum of all story points}
epics:
  - epic-{N}
```

If the initiative produces multiple epics, list all of them in the `epics` array.

**Step B — Append initiative name to `sprint/future.yaml`.**
Add `{initiative_name}` to the `future.initiatives` list using yq or direct YAML editing.

**If N:**
Ask what changes are needed and help user adjust before re-applying.

### 5. Verify Import

After successful import, verify **both** files:

```bash
# Verify initiative file exists and has correct structure
cat sprint/initiative-{initiative_name}.yaml

# Verify initiative is listed in future.yaml
grep "{initiative_name}" sprint/future.yaml
```

Confirm:
- Initiative file exists at `sprint/initiative-{initiative_name}.yaml`
- Initiative file contains epic IDs and metadata
- Initiative name appears in future.yaml
- Epic numbers are correct
- Stories have proper IDs

### 6. Complete Workflow

Display completion message:

```
## Workflow Complete!

**Epic imported:** epic-{N}
**Initiative:** {initiative_name}
**Stories:** {count} stories ready for sprint planning
**Files created/updated:**
- sprint/initiative-{initiative_name}.yaml (NEW)
- sprint/future.yaml (UPDATED)

Next steps:
- Use `/pf-sprint` to view the backlog
- Use `pf sprint epic promote` to move to a sprint when ready
```

## SUCCESS CRITERIA:

- ✅ Initiative file created at `sprint/initiative-{initiative_name}.yaml`
- ✅ Initiative appears in future.yaml
- ✅ Epic has correct sequential number
- ✅ All stories have proper IDs (epic-story format)
- ✅ User confirms import is correct

## FAILURE MODES:

- ❌ future.yaml not found - ensure sprint/ directory exists
- ❌ Initiative file not created - sprint commands won't find epic data
- ❌ Duplicate epic number - check existing IDs before assigning
- ❌ yq not installed - required for YAML manipulation (`brew install yq`)

**Master Rule:** The workflow is not complete until both the initiative file exists AND the initiative is listed in future.yaml.
