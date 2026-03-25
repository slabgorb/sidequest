<gate name="context-ok" model="haiku">

<purpose>
Verify that Claude Code context usage is below threshold before allowing
a phase transition. Prevents handoffs when context is too high, which would
result in degraded agent performance in the next phase.
</purpose>

<pass>
Run the context check command and verify usage is acceptable:

1. **Context usage:** Run `pf context --human` to check current context percentage.
   - Extract the usable percent from output
   - Threshold: below 60% usable context

2. **Relay mode:** Check if relay mode is active via `pf context` env var output.
   - If relay mode is on and context is high, TirePump should handle clearing

If context is below threshold, return:

```yaml
GATE_RESULT:
  status: pass
  gate: context-ok
  message: "Context at {N}% — safe to continue"
  checks:
    - name: context-usage
      status: pass
      detail: "{usable_pct}% of available context used ({usable_tokens} tokens)"
```
</pass>

<fail>
If context usage exceeds the threshold:

1. **High context:** Report the current usage level
2. **Recommendation:** Suggest `/clear` before continuing

Return with guidance:

```yaml
GATE_RESULT:
  status: fail
  gate: context-ok
  message: "Context at {N}% — too high for reliable handoff"
  checks:
    - name: context-usage
      status: fail
      detail: "{usable_pct}% of available context used — threshold is 60%"
  recovery:
    - "Run /clear to reset context, then retry the handoff"
    - "If relay mode is on, TirePump will handle this automatically"
```
</fail>

</gate>
