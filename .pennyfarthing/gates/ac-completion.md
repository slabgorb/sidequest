<gate name="ac-completion" model="haiku">

<purpose>
Verify that every acceptance criterion in the story context document is accounted for
in the session file. Each AC must have a status of DONE, DEFERRED (with operator approval),
or DESCOPED (with operator approval). Unstatused ACs block handoff.

This gate is composable — it accepts CONTEXT_FILE and SESSION_FILE as arguments and
makes no assumptions about which workflow phase triggered it or which agent is active.

Used by: dev-exit (after green phase), or any phase that requires AC accountability.
</purpose>

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `CONTEXT_FILE` | Yes | Path to the story context document containing `## AC Context` |
| `SESSION_FILE` | Yes | Path to the session file containing AC status markers |
</arguments>

<pass>
Run the Python validation function to check AC completion:

```bash
python3 -c "
from pf.gates.ac_completion import validate_ac_completion
import json, sys
result = validate_ac_completion('${CONTEXT_FILE}', '${SESSION_FILE}')
print(json.dumps(result))
sys.exit(0 if result['status'] == 'pass' else 1)
"
```

The validator checks:
1. Story context document exists and has `## AC Context` section
2. Each AC in the context has a status entry in the session file
3. Status is one of: DONE, DEFERRED, DESCOPED
4. DEFERRED and DESCOPED entries prompt the operator for approval (default: reject)
5. All ACs are accounted for in a full accountability table

If validation passes, return:

```yaml
GATE_RESULT:
  status: pass
  gate: ac-completion
  message: "All {ac_count} acceptance criteria accounted for"
  checks:
    - name: ac-completion
      status: pass
      detail: "Full accountability table logged — {done_count} DONE, {deferred_count} approved deferrals"
```
</pass>

<fail>
If validation fails, diagnose the specific failure:

**Context document not found:**
```yaml
GATE_RESULT:
  status: fail
  gate: ac-completion
  message: "Story context document not found at {path}"
  checks:
    - name: context-file
      status: fail
      detail: "ac-completion gate requires a context document"
  recovery:
    - "Ensure story context document exists at the expected path"
    - "Context documents are created during SM setup phase"
```

**No AC Context section:**
```yaml
GATE_RESULT:
  status: fail
  gate: ac-completion
  message: "No AC Context section found in story context"
  checks:
    - name: ac-section
      status: fail
      detail: "Cannot determine AC list without ## AC Context section"
  recovery:
    - "Add a '## AC Context' section to the story context document"
    - "Each AC should be a ### heading: '### AC-N: Title'"
```

**Unstatused AC:**
```yaml
GATE_RESULT:
  status: fail
  gate: ac-completion
  message: "{AC-N} has no status. Mark as DONE, DEFERRED, or DESCOPED."
  checks:
    - name: ac-status
      status: fail
      detail: "{AC-N} not found in session file AC Status section"
  recovery:
    - "Add '- {AC-N}: DONE' to ## AC Status in the session file"
    - "Or '- {AC-N}: DEFERRED {justification}' if deferring"
    - "Or '- {AC-N}: DESCOPED {justification}' if descoping"
```

**Operator-rejected deferral:**
```yaml
GATE_RESULT:
  status: fail
  gate: ac-completion
  message: "{AC-N} deferral rejected by operator. Implement {AC-N} or provide stronger justification."
  checks:
    - name: ac-approval
      status: fail
      detail: "Operator rejected {STATUS} for {AC-N}"
  recovery:
    - "Implement {AC-N} to satisfy the acceptance criterion"
    - "Or update the justification and re-trigger the gate"
```
</fail>

</gate>
