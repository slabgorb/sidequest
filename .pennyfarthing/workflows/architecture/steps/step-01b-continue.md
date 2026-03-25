# Step 1b: Workflow Continuation Handler

<purpose>
Detect existing architecture workflow state from session file and provide user with options to continue, restart, or review previous progress before proceeding.
</purpose>

<instructions>
Read the existing output file and parse frontmatter to identify completed steps and current progress. Analyze the document state, summarize decisions made so far, and present continuation options with data loss prevention (archiving).
</instructions>

<output>
Workflow continuation information displayed with summary of completed steps, current document state, and user-selectable options (Continue/Restart/View) with archive confirmation if restarting.
</output>

<step-meta>
number: 1b
name: continue
gate: false
</step-meta>

## Mandatory Execution Rules

- DETECT existing workflow state from output document frontmatter
- READ complete document to understand current progress
- PRESENT continuation options to user before proceeding
- NEVER proceed without user confirmation

## Purpose

Handle workflow resumption when an existing architecture document is detected. This step is invoked automatically when step 1 finds an existing document with `stepsCompleted` in frontmatter.

## Detection Trigger

Step 1 redirects here when:
1. Output file `{output_file}` already exists
2. Document has frontmatter with `stepsCompleted` array
3. Workflow was previously started but not completed

## Instructions

1. **Read Existing State**:
   - Parse frontmatter for `stepsCompleted` array
   - Identify last completed step
   - Load document content to understand current progress

2. **Analyze Progress**:
   - Which steps are complete?
   - What decisions have been made?
   - Are there any inconsistencies?

3. **Present Continuation Options**:
   Based on current state, offer user choices:

## Actions

- Read: `{output_file}` completely (including frontmatter)
- Parse: `stepsCompleted` from frontmatter
- Analyze: Current document state

## Output

Present to user:

```markdown
## Workflow Continuation

**Document found:** {output_file}
**Steps completed:** {stepsCompleted}
**Last step:** {last_step_name}

### Current Document State
{summary of what's been decided so far}

### Continuation Options

- **[V] View** - Show complete document before deciding
```

## Continuation Flow

After user confirms via the switch prompt:
1. Load the next incomplete step file
2. Resume workflow from that point
3. Continue normal step progression

After user selects Revise:
1. Archive existing document to `{output_file}.backup-{timestamp}`
2. Return to step 1 for fresh initialization
3. Proceed with new workflow

## Success Metrics

- Existing workflow detected and state loaded correctly
- User informed of current progress
- Continuation or restart handled smoothly
- No data loss (archive before restart)


<switch tool="AskUserQuestion">
  <case value="continue" next="step-02-context">
    Continue — Resume from step {next_step}
  </case>
  <case value="restart" next="LOOP">
    Restart — Start fresh (will archive existing document)
  </case>
  <case value="view" next="LOOP">
    View — Show complete document before deciding
  </case>
</switch>

## Failure Modes

- Proceeding without user confirmation
- Not loading complete existing document
- Losing work by overwriting without archive
- Misreading stepsCompleted array
