# Step 6: Retrospective (Optional)

<step-meta>
number: 6
name: retro
gate: false
</step-meta>

<purpose>
Run a retrospective on the work since the last release before cutting the new one. This is optional — skip if you've already done a sprint retro or just want to ship.
</purpose>

<instructions>
1. Offer to run /retro for the release cycle
2. If user accepts, delegate to the retro skill
3. If user skips, continue to commit step
</instructions>

<output>
Retrospective notes (if run), or skip confirmation.
</output>

## Why Retro at Release Time?

A release is a natural checkpoint. Even if sprint retros happen separately, a release retro captures:
- What went well in this release cycle
- What caused friction (like the deploy.sh staging bug)
- Process improvements to carry forward
- Technical debt discovered but not addressed

## Execution

### 6.1 Offer Retrospective

Ask the user: **Want to run a quick retro before releasing?**

If yes, invoke the retro skill:

```
/retro
```

This will run a structured retrospective covering:
- What went well
- What didn't go well
- Action items

The retro output gets saved to `.session/` and can inform the changelog or release notes.

### 6.2 After Retro (or Skip)

Continue to the commit step. Any retro notes are captured separately — they don't block the release.

---


<switch tool="AskUserQuestion">
  <case value="continue-to-commit" next="step-07-commit">
    Continue to commit (skip retro)
  </case>
  <case value="run-retro-first" next="LOOP">
    Run `/retro` first
  </case>
</switch>
