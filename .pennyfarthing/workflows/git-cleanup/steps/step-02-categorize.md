# Step 2: Categorize Changes

<purpose>
Group uncommitted changes by initiative type (docs, chore, feat, fix, refactor, test) and organize them into logical groups that can be committed separately, accounting for multi-repo structure where changes may span multiple repositories.
</purpose>

<instructions>
1. Analyze change patterns for each file across all repos to determine initiative type and groupings
2. Use categorization rules (prefix reference) to classify each change
3. Apply grouping heuristics (by story ID, feature, directory, file type)
4. Propose groups in structured format showing which files belong together
5. Present summary with approval gate requiring user decision before execution
6. Allow editing, tracking in Jira, skipping groups, or continuing to execution
</instructions>

<output>
Proposed change groups with:
- Descriptive name for each group
- Type (feat|fix|chore|docs|refactor|test)
- Branch name format
- Commit message format
- Files listed by repo with their status
- Rationale for grouping
- Summary of total groups (quick commits, tracked stories, skipped)
- User choices presented via switch prompt
</output>

## Objective

Organize scattered changes into logical groups that can be committed separately. Each group becomes one branch + commit.

## Multi-Repo Awareness

Changes may span multiple repos. Group by **initiative**, not by repo:

```
Group: "Todos WebSocket feature"
  - pennyfarthing/packages/core/src/main.ts
  - pennyfarthing/packages/core/src/websocket.ts
  - pennyfarthing/packages/core/src/hooks/useTodos.ts
```

All files in a group get committed together in their respective repos.

## Categorization Rules

### Prefix Reference

| Prefix | Type | Branch Pattern | Files Typically |
|--------|------|----------------|-----------------|
| `docs:` | Documentation | `docs/description` | `docs/*.md`, `README.md` |
| `chore:` | Maintenance | `chore/description` | configs, dependencies |
| `chore(sprint):` | Sprint tracking | `chore/sprint-update` | `sprint/*.yaml` |
| `chore(pennyfarthing):` | PF config | `chore/pf-description` | `.claude/**`, `.pennyfarthing/**` |
| `feat:` | New feature | `feat/story-id-desc` | `src/**`, `internal/**` |
| `fix:` | Bug fix | `fix/issue-desc` | various |
| `refactor:` | Code improvement | `refactor/description` | `src/**` |
| `test:` | Test changes | `test/description` | `**/tests/**`, `*.test.*` |

### Grouping Heuristics

1. **By Story ID** - If changes relate to a known story (check session files)
2. **By Feature** - Related functionality across files/repos
3. **By Directory** - Files in same directory often belong together
4. **By File Type** - Docs together, configs together, source together

## Execution

### 2.1 Analyze Change Patterns

For each changed file across all repos, determine:
- Which initiative type it belongs to
- If it relates to an active story
- If it should group with other files
- Which repo it's in

### 2.2 Propose Groupings

Present proposed groups in this format:

```
## Proposed Change Groups

### Group 1: {descriptive_name}
**Type:** {feat|fix|chore|docs|refactor|test}
**Branch:** `{type}/{description}`
**Commit:** `{type}({scope}): {message}`

**Repo: pennyfarthing**
- `packages/core/src/main.ts` (M)
- `packages/core/src/websocket.ts` (M)

**Repo: pennyfarthing-orchestrator**
- `sprint/current-sprint.yaml` (M)

Rationale: {why these files belong together}

---

### Group 2: ...
```

### 2.3 Handle Ambiguous Changes

For files that could belong to multiple groups:
- Present options to user
- Default to the smaller/more focused group
- Allow "skip" to leave uncommitted

## Tracking Decision

For each group, decide tracking level:

| Level | Branch | Jira | PR | Use When |
|-------|--------|------|-----|----------|
| **Quick** | `chore/*` | No | No | Maintenance, configs |
| **Tracked** | `feat/<PROJECT>-*` | Yes | Yes | Features worth tracking |

## Approval Gate

**This step requires user approval before execution.**

Present summary:

```
## Summary

Total groups: {n}
- Quick commits: {count}
- Tracked stories: {count}
- Skipped: {count}

Repos affected: {list}
Files to commit: {count}

Ready to proceed?
```

---

**[E]** Edit groupings (modify a group)
**[T]** Track a group in Jira (promote to standalone story)

<!-- GATE -->

<switch tool="AskUserQuestion">
  <case value="edit-groupings" next="LOOP">
    Edit groupings (modify a group)
  </case>
  <case value="track-a-group-in-jira" next="LOOP">
    Track a group in Jira (promote to standalone story)
  </case>
  <case value="skip-a-group" next="step-03-execute">
    Skip a group (leave those files uncommitted)
  </case>
  <case value="continue-to-execution" next="step-03-execute">
    Continue to execution
  </case>
</switch>
