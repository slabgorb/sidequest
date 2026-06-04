# Story Lifecycle

<info>
The `pf sprint story` CLI is the one true path for editing stories. **Never hand-edit sprint YAML** (SM rule) — the CLI keeps ids, dependencies, and the sharded epic layout consistent in a single atomic operation. Most mutating commands accept `--dry-run` to preview without writing.
</info>

## Command Surface

| Command | What it does | Key args / flags |
|---------|--------------|------------------|
| `add EPIC_ID TITLE POINTS` | Add a new story to an epic (or `--initiative` for a standalone). | `--type`, `--priority`, `--workflow`, `--jira`, `--initiative SLUG`, `--repos`, `--depends-on ID`, `--epic ID` (overrides positional), `--dry-run` |
| `update STORY_ID` | Update a story's fields by id. | See [update fields](#update-fields) |
| `move STORY_ID --to-epic EPIC` | Move a story to another epic; renumbers and rewrites dependents. | `--to-epic EPIC` (required), `--dry-run`. See [move](#move). |
| `remove STORY_ID` | Remove a story from the sprint YAML. | `--dry-run` |
| `split STORY_ID -n N` | Split a story into N sub-stories with dependency tracking (points must sum to the original). | `-n / --into N`, `--dry-run` |
| `finish STORY_ID` | Complete a story: archive session, merge PR, transition Jira, update YAML. | `--dry-run` |
| `complete STORY_ID` | Mark a story done and check its plan checkbox (superpowers flow). | `--dry-run` |
| `claim STORY_ID` | Claim or unclaim a story in Jira. | `--claim / --unclaim`, `--dry-run` |
| `show STORY_ID` | Show details for a story. | `--json` |
| `field STORY_ID FIELD_NAME` | Print one field value (e.g. `workflow`, `status`, `points`); `null` if unset. | — |
| `size [POINTS]` | Show story sizing guidelines. | — |
| `template [TYPE]` | Show a story template (`feature`, `bug`, `refactor`, `chore`). | — |

`STORY_ID` accepts either a sprint id (e.g. `156-3`) or a Jira key (e.g. `PROJ-17082`).

## update fields

`pf sprint story update STORY_ID` accepts:

| Flag | Notes |
|------|-------|
| `--status` | `backlog`, `ready`, `in_progress`, `in_review`, `done`, `canceled` (hyphen forms also accepted) |
| `--points INTEGER` | Story points |
| `--priority` | Free text (`p0`–`p3` by convention) |
| `--workflow` | Workflow name (`tdd`, `trivial`, `bdd`, `superpowers`) |
| `--started`, `--completed` | Timestamps |
| `--assigned-to` | Assignee |
| `--description TEXT` | Story description |
| `--review-findings TEXT` | Reviewer findings |
| `--review-verdict` | `approved`, `rejected`, `pending` |
| `--add-ac TEXT` | Append an acceptance criterion (repeatable) |
| `--clear-ac` | Clear all ACs (combine with `--add-ac` to replace) |
| `--jira` | Sync changed fields to Jira after the YAML update |
| `--dry-run` | Preview without writing |

There is **no `--epic` flag on `update`** — changing a story's epic is a `move` (see below), because it has to renumber the story and rewrite dependents.

## move

`pf sprint story move STORY_ID --to-epic EPIC` does three things in one atomic operation:

1. **Renumber** — the story is reassigned to the target epic's next sequential id (e.g. moving `10-1` into epic `20` makes it `20-2` if `20-1` already exists).
2. **Re-parent** — the story is removed from its source (epic shard, `standalone_stories`, or top-level `stories`) and appended to the target epic.
3. **Dependency-rewrite** — every other story whose `depends_on` referenced the moved story's **old** id is rewritten to the **new** id, across all epics, `standalone_stories`, and top-level `stories`. `depends_on` is a single story-id string; matching is whole-value equality, so moving `10-1` never disturbs a dependent on `10-10`.

The whole change is validated before anything is written: if post-move validation fails, nothing is written. `--dry-run` reports the planned move without touching the YAML.

```bash
pf sprint story move 151-3 --to-epic 152
pf sprint story move PROJ-17082 --to-epic 152 --dry-run
```

## CLI-supported vs manual-only

What the CLI handles today, and where the boundaries are:

- **Supported:** add, update (fields above), move (renumber + re-parent + dependency-rewrite), remove, split, finish, complete, claim, show, field.
- **Dependencies:** set on creation with `add --depends-on ID`; `split` wires sub-story dependencies; `move` rewrites references to a moved story. `depends_on` is a single id — there is no multi-dependency model.
- **Not yet CLI-exposed (handle as a deliberate, separate change):**
  - **Re-parenting via `update`** — use `move` instead; `update` has no `--epic`.
  - **Renaming / re-numbering a story in place** — only `move` renumbers, and only as a side effect of changing epics.
  - **Re-pointing a dependency** to a different (unmoved) story — no `update --depends-on`; this is not yet exposed.

When you hit one of these boundaries, prefer the closest supported command over hand-editing the YAML.

## Key Files

| File | Purpose |
|------|---------|
| `pf/sprint/story_add.py` | `add` command + `generate_story_id` |
| `pf/sprint/story_update.py` | `update` command and field handling |
| `pf/sprint/story_move.py` | `move` — renumber, re-parent, `_rewrite_dependencies` |
| `pf/sprint/story_split.py` | `split` with dependency tracking |
| `pf/sprint/story_finish.py` | `finish` — archive, merge, Jira transition |
| `pf/sprint/validator.py` | Sprint document validation (incl. `depends_on`) |
| `pf/sprint/yaml_io.py` | Shard-aware `read_sprint` / `write_sprint` |

<info>
**Related:** `guides/handoff-cli.md` (phase transitions), `guides/gates.md` (quality gates), `schemas/session-schema.md` (session file)
</info>
