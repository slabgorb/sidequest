# Gate Recovery: Auto-Trigger Context Creation

When `pf handoff resolve-gate` returns a gate result with failed context checks,
check the workflow YAML for a `recovery:` block on the current phase gate. If
recovery is configured, follow this pipeline:

## Recovery Pipeline

1. **Parse gate result:** After the gate subagent returns GATE_RESULT, check for
   failed checks named `epic-context-validated` or `story-context-validated`.

2. **Check if recoverable:** Only trigger recovery when the check detail indicates
   "missing" or "not found" (exit code 2). Do NOT trigger for validation errors
   (exit code 1) — those require manual fixes.

3. **Cascade order:** Always recover epic context first, then story context.
   Epic context is a prerequisite for story context creation.

4. **For each recoverable check:**
   - Invoke `/pf-context create {type} {id}` (epic or story)
   - Re-run `pf validate context-{type} {id}` to verify

5. **Handle outcomes per check:**
   - **Created + validated:** Continue silently to next check or handoff
   - **Created + invalid:** Report: "Context created but has validation errors.
     Manual fix needed at sprint/context/context-{type}-{id}.md"
   - **Creation failed:** Report: "Context creation failed.
     Run `/pf-context create {type} {id}` manually"

6. **One attempt per level (Rule #6):** Try creation exactly once per context
   type. No retry loops. If creation produces invalid output, stop and report.

7. **After recovery:** If all recoverable checks now pass, re-run the full gate
   to verify. If the gate still fails on non-recoverable checks, report those
   failures normally.

## Example Flow

```
pf handoff resolve-gate 131-2 tdd setup
→ Gate fails: epic-context-validated=fail (missing), story-context-validated=fail (missing)

Recovery:
1. /pf-context create epic 131        → success
2. pf validate context-epic 131   → exit 0 (pass) → continue
3. /pf-context create story 131-2      → success
4. pf validate context-story 131-2 → exit 0 (pass) → continue

Re-run gate → all pass → proceed to handoff
```
