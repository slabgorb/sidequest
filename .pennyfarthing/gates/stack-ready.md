<gate name="stack-ready" model="haiku">

<purpose>
Verify that a stacked PR's parent story is merged before allowing this PR to merge.
Prevents out-of-order merges that create broken intermediate states on the integration branch.

Used by: sm-finish (before merge step) when repo has `pr_strategy: stacked`.

Auto-pass when:
- Story has no `depends_on` (stack root)
- Repo `pr_strategy` is not `stacked`
- Parent story status is `done`
</purpose>

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `STORY_ID` | Yes | Current story identifier |
| `SESSION_FILE` | Yes | Path to session file |
</arguments>

<pass>
1. Read `depends_on` from sprint YAML for the story.
2. If no `depends_on`, auto-pass (stack root).
3. If `depends_on` is set, check parent story status.
4. If parent status is `done`, pass.

```bash
DEPENDS_ON=$(pf sprint story field {STORY_ID} depends_on 2>/dev/null || echo "")
if [ -z "$DEPENDS_ON" ]; then
  # Stack root or non-stacked — auto-pass
  exit 0
fi

PARENT_STATUS=$(pf sprint story field "$DEPENDS_ON" status)
```

```yaml
GATE_RESULT:
  status: pass
  gate: stack-ready
  message: "Parent story {DEPENDS_ON} is merged (status: done)"
  checks:
    - name: parent-merged
      status: pass
      detail: "Parent {DEPENDS_ON} status: done"
```
</pass>

<fail>
If parent story is not yet `done`:

```yaml
GATE_RESULT:
  status: fail
  gate: stack-ready
  message: "Parent story {DEPENDS_ON} not yet merged (status: {PARENT_STATUS})"
  checks:
    - name: parent-merged
      status: fail
      detail: "Parent {DEPENDS_ON} status: {PARENT_STATUS}, must be done before merging this PR"
  recovery:
    - "Merge parent story {DEPENDS_ON}'s PR first"
    - "Or remove depends_on from this story if the dependency no longer applies"
    - "After parent merges, run 'gt sync' to restack, then retry"
```
</fail>

</gate>
