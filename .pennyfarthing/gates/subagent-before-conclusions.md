<gate name="subagent-before-conclusions" model="haiku">

<purpose>
Prevent any agent from writing conclusions, assessments, or VERIFIED claims
before all spawned subagents have returned results. This gate enforces
SOUL.md #11 (Automatic Beats Instructional) — agents were instructed to
wait for subagents but fabricated answers instead. Now it's enforced.

This gate applies to ANY agent that uses subagents, not just the Reviewer.
</purpose>

<pass>
Check the session file for these conditions:

1. **Subagent Results table exists** with a `## Subagent Results` heading
2. **All rows show `Received: Yes`** (or explicit error/timeout, or `Skipped` for subagents disabled via `workflow.reviewer_subagents` settings)
3. **`All received: Yes` line present** after the table
4. **No VERIFIED contradicts a subagent finding:** For each `[VERIFIED]` in
   the assessment, check whether any subagent flagged the same file or area.
   If a subagent reported a finding about file X and the assessment marks
   the same area as VERIFIED, that VERIFIED must include a `Challenged:` note
   explaining why the subagent finding was dismissed.

If all conditions met:

```yaml
GATE_RESULT:
  status: pass
  gate: subagent-before-conclusions
  message: "All subagents returned before conclusions were written. No unsupported VERIFIEDs."
```
</pass>

<fail>
1. **No Subagent Results table:** Agent wrote conclusions without documenting
   subagent results at all.

2. **Incomplete table:** Some subagents missing from the table — agent
   started writing conclusions before all results were back.

3. **Contradicted VERIFIED:** Agent marked something as VERIFIED but a
   subagent flagged the same area. The VERIFIED lacks a `Challenged:` note
   explaining the disagreement.

```yaml
GATE_RESULT:
  status: fail
  gate: subagent-before-conclusions
  message: "{specific failure reason}"
  recovery:
    - "Do not write your assessment until ALL subagent results are documented"
    - "Every VERIFIED that conflicts with a subagent finding must include a Challenged: note"
    - "If you cannot explain why the subagent is wrong with specific file:line evidence, downgrade the VERIFIED to a finding"
```
</fail>

</gate>
