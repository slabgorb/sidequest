<gate name="merge-ready" model="haiku">

<purpose>
Block new work if non-draft pull requests are open for stories not in review.
Open non-draft PRs for stories with in_review status are expected and allowed.
Draft PRs are always allowed — they represent in-progress work not yet ready for review.
</purpose>

<pass>
Run:
```bash
gh pr list --state open --search "draft:false" --json number,title,url,headRefName
```

For each non-draft PR, extract the story ID from the branch name:
- Pattern: `feat/{story-id}-*` or `feature/{story-id}-*`
- Example: `feat/141-3-add-status-sync` → story ID `141-3`

For each matched story ID, check status:
```bash
pf sprint story field {story_id} status
```

If ALL of these are true, return pass:
- No non-draft open PRs exist, OR
- Every non-draft PR matches a story with `in_review` status

```yaml
GATE_RESULT:
  status: pass
  gate: merge-ready
  message: "No blocking PRs. Clear to start new work."
  checks:
    - name: no-blocking-prs
      status: pass
      detail: "All open PRs are for stories in review (or no PRs open)"
```
</pass>

<fail>
If any non-draft PR has no matching story or the story is not `in_review`:

```yaml
GATE_RESULT:
  status: fail
  gate: merge-ready
  message: "Blocked: {N} PR(s) not in review state"
  checks:
    - name: no-blocking-prs
      status: fail
      detail: "Blocking PRs: {list of PR numbers, titles, and story statuses}"
  recovery:
    - "Merge or close blocking PRs before starting new work"
    - "Use /reviewer to complete pending reviews"
    - "Convert to draft if work is not ready: gh pr ready --undo {number}"
    - "If story should be in review: pf sprint story update {story_id} --status in_review"
```
</fail>

</gate>
