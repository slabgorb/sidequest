---
description: Epic conductor: brainstorm → plan → materialize → execute → review
args: "[start|close] <epic-id>"
---

# /pf-epic — Epic Conductor

Drives an epic end-to-end: **brainstorm → plan → materialize → execute → rollup review**.
The superpowers plan is the source of truth; the epic YAML is a generated ledger.

## Flow

1. **Brainstorm** — invoke `superpowers:brainstorming`. Output: a spec under
   `docs/superpowers/specs/`.
2. **Plan** — invoke `superpowers:writing-plans`. Output: a plan under
   `docs/superpowers/plans/`. Each `### Task N` is one unit of work and becomes one
   PF story. (Story ids do not exist yet — `from-plan` assigns them in the next step.)
3. **Materialize** — ensure the epic exists (`pf epic add <id> "<title>"` if needed),
   then run:
   `pf epic from-plan docs/superpowers/plans/<plan>.md <epic-id>`
   This creates one `workflow: superpowers` story per Task (repos derived from each
   Task's `Files:` block) and appends a closing step to each Task in the plan:
   `- [ ] **Story <id> complete** — run \`pf sprint story complete <id>\``.
   Re-running is safe (idempotent — already-materialized tasks are skipped).
4. **Execute** — invoke `superpowers:subagent-driven-development` (preferred) or
   `superpowers:executing-plans`. The closing step of each Task runs
   `pf sprint story complete <id>`, which flips the story to `done` and checks the
   plan box. Commits may span multiple repos per `repos.yaml`.
5. **Rollup review** — once all stories are `done`, run one review per affected repo
   (the union of every story's `repos:`), each PR'd to that repo's base branch from
   `repos.yaml` (via `/pf-reviewer`). Then `pf epic close <epic-id>`.

## Gates

- **Materialize-before-execute:** do not start execution until `pf epic from-plan` has
  created the stories.
- **Done-before-review:** all epic stories must be `done` before the rollup review.

## Notes

- Per-story TEA→Dev→Reviewer phased ceremony is bypassed for `workflow: superpowers`
  stories; the rollup review is the gate.
- Existing `pf epic` verbs (`start`, `close`, `show`, `add`, `update`, `promote`,
  `archive`, `cancel`, `reindex`) are unchanged; this adds `pf epic from-plan` and a
  conductor flow on top.
- The plan is the source of truth; the epic YAML is generated from it. Edit the plan,
  then re-run `pf epic from-plan` to sync new tasks.

## Related

- `/pf-sprint` — Sprint management
- `/pf-reviewer` — Rollup review per repo
- `superpowers:brainstorming` — Spec generation
- `superpowers:writing-plans` — Plan generation
- `superpowers:subagent-driven-development` — Parallel task execution
