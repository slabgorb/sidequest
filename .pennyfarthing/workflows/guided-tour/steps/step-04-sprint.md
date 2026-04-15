# Step 04: Sprint Management

<purpose>
Learn how Pennyfarthing organizes work using sprints, epics, and stories. Then practice the full sprint lifecycle hands-on by creating, claiming, completing, and cleaning up a practice story.
</purpose>

<instructions>
1. Explain the sprint/epic/story hierarchy
2. Demonstrate read-only sprint commands
3. Run the hands-on practice exercise
4. Clean up practice artifacts
5. Offer deep-dive into advanced sprint topics
</instructions>

<output>
- Developer understands sprint/epic/story hierarchy
- Developer has practiced the full sprint lifecycle (create, claim, complete, cleanup)
- Practice artifacts are fully cleaned up
- Developer knows key sprint commands
</output>

<gate>
## Completion Criteria
- [ ] User has seen the sprint status
- [ ] User understands the epic/story hierarchy
- [ ] User knows how to start work with `/pf-sprint work`
- [ ] User understands the YAML shard structure
</gate>

## SPRINT CONCEPTS

Pennyfarthing uses a three-level hierarchy to organize work:

```
Sprint (time-boxed period)
  └── Epic (feature group, tracked in Jira)
        └── Story (unit of work, 1-5 points)
```

**Sprints** are two-week periods. Each sprint has a `current-sprint.yaml` index file that references one or more **epic shards** — separate YAML files per epic.

**Epics** group related stories. Each epic gets its own shard file (`sprint/epic-{jira-key}.yaml`) so multiple agents can work on different epics without merge conflicts.

**Stories** are the atomic unit of work. Each story has:
- An ID (e.g., `132-15`)
- A Jira key (e.g., `<PROJECT-KEY>`)
- Points (1-5, measuring complexity)
- A workflow (tdd, trivial, etc.)
- A status (backlog → in_progress → in_review → done)

### Jira Integration

Pennyfarthing syncs stories bidirectionally with Jira. When you claim a story locally, it updates Jira. When Jira status changes, `pf jira bidirectional` syncs back. This keeps both systems in sync without manual effort.

## SPRINT COMMANDS

Let's see your current sprint:

```bash
pf sprint status
```

This shows all stories grouped by status. Now check the backlog:

```bash
pf sprint backlog
```

This shows available stories grouped by epic. You can also look at individual stories:

```bash
pf sprint story show <story-id>
```

## HANDS-ON PRACTICE

Now let's practice the full sprint lifecycle. You'll create a practice story, claim it, make a change, and complete it — experiencing the real workflow.

### Phase 1: Setup (automated)

The tour creates a temporary practice epic and story for you to work with:

```bash
# The tour runs this automatically:
# 1. Copies practice epic template to sprint/epic-tour-practice.yaml
# 2. Registers it in the sprint index
```

Let's verify the practice story appeared:

```bash
pf sprint status
pf sprint backlog
```

You should see a "Guided Tour Practice Epic" with one story: "Practice: Add a comment to a file."

### Phase 2: Claim the Story

Now claim the practice story — just like you would with a real story:

```bash
pf sprint work tour-practice-1
```

This transitions the story from `backlog` to `in_progress` and creates a session file at `.session/tour-practice-1-session.md`. The session file tracks the story's context, acceptance criteria, and agent assessments.

### Phase 3: Do the Work

For this practice, make a trivial edit — add a comment to any file in your project:

```
// Tour practice edit — you can remove this
```

In a real story, you'd:
1. Write failing tests (TEA agent, RED phase)
2. Implement the feature (Dev agent, GREEN phase)
3. Get a code review (Reviewer agent)
4. Create a PR and merge

For practice, we'll skip the full TDD workflow.

### Phase 4: Complete the Story

Now finish the practice story:

```bash
pf sprint story finish tour-practice-1
```

This transitions the story through `in_review` → `done`, archives the session file, and cleans up. Let's verify:

```bash
pf sprint status
```

The practice story should now show as done.

### Phase 5: Cleanup

We'll clean up all practice artifacts now so they don't pollute your sprint data:

1. Remove the practice epic shard (`sprint/epic-tour-practice.yaml`)
2. Remove any session artifacts (`.session/tour-practice-1-session.md`)
3. Remove any archive artifacts (`sprint/archive/tour-practice-1-session.md`)
4. Revert the practice file edit via `git checkout` on that file

```bash
# The tour handles cleanup automatically
```

Let's verify everything is clean:

```bash
pf sprint status
```

The practice epic and story should be gone.

<deep-dive>
## Deep-Dive: Sprint System Internals

When the user selects Dig In, explore these topics interactively:

### YAML Shard Structure
Sprint tracking uses a sharded YAML architecture:
- **`current-sprint.yaml`** is the index file containing sprint metadata and epic references (as string keys like `<PROJECT-KEY>`)
- **`epic-<PROJECT-KEY>.yaml`** shard files contain the actual story details for each epic
- The `load_sprint()` loader merges shards into a unified data structure
- `write_sprint()` handles writing back to the correct shard files

### Epic Lifecycle
- Epics are created via `pf sprint epic add` or imported from BMAD via `pf sprint epic import`
- Each epic gets its own shard file: `sprint/epic-{jira-key}.yaml`
- Stories within epics track points, priority, status, workflow, and acceptance criteria
- Completed epics can be archived via `pf sprint epic archive`

### Story Lifecycle
Full lifecycle: backlog → in_progress → done → archived
- **backlog**: Story exists in YAML, not yet claimed
- **in_progress**: Claimed via `/pf-sprint work`, Jira moved to In Progress
- **done**: All phases complete, PR merged, Jira moved to Done
- **archived**: Session file moved to `sprint/archive/`, YAML updated

### Archive Process
When a story finishes (`pf sprint story finish`):
1. Session file archived to `sprint/archive/{jira-key}-session.md`
2. PR auto-merged (if open)
3. Jira status moved to Done
4. Sprint YAML updated with completion date
5. Feature branch cleaned up

### Jira Sync and Reconciliation
- `pf jira create story EPIC_KEY STORY_ID` — Create Jira issue from YAML
- `pf jira sync EPIC_ID` — Push YAML changes to Jira
- `pf jira bidirectional` — Two-way sync (Jira wins by default)
- `pf jira reconcile` — Audit report of mismatches between YAML and Jira
- Sprint association via `pf jira sprint add`

Use AskUserQuestion to let the user pick which sub-topic to explore. Continue the deep-dive loop until the user chooses to move on.
</deep-dive>

<switch tool="AskUserQuestion">
  <case value="continue" next="step-05-config">
    Continue — Proceed to hooks and configuration
  </case>
  <case value="dig-in" next="LOOP">
    Dig In — Explore YAML shards, epic lifecycle, archive, and Jira sync
  </case>
  <case value="try-it" next="LOOP">
    Try It — Run `pf sprint status` or `pf sprint backlog`
  </case>
  <case value="skip" next="step-05-config">
    Skip — Move to configuration
  </case>
</switch>
