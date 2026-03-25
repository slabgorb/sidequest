<gate name="spec-drift-precheck" model="haiku">

<purpose>
Detect specification drift at review phase entry — mismatches between what was specified
(story context + acceptance criteria) and what was actually implemented (session file).
Produces a drift report the Reviewer uses as a first-pass checklist before substantive review.

Checks:
1. All acceptance criteria from context are addressed in Dev Assessment
2. Design Deviations section exists with Dev subsection and proper 6-field format
3. No scope creep — files changed are traceable to acceptance criteria
4. Major/breaking deviations are flagged for reviewer attention
5. Implementation Complete flag is Yes
</purpose>

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `SESSION_FILE` | Yes | Path to session file |
| `CONTEXT_FILE` | Yes | Path to story context file |
</arguments>

<pass>
Run the Python validation function:

```bash
python3 -c "
from pf.gates.spec_drift_precheck import run_spec_drift_precheck
import json, sys
result = run_spec_drift_precheck('${SESSION_FILE}', '${CONTEXT_FILE}')
print(json.dumps(result, indent=2))
sys.exit(0 if result['success'] else 1)
"
```

If all checks pass:

```yaml
GATE_RESULT:
  status: pass
  gate: spec-drift-precheck
  message: "No specification drift detected — implementation aligns with story context"
  drift_score: 0
  findings: []
```
</pass>

<fail>
If drift is detected:

```yaml
GATE_RESULT:
  status: fail
  gate: spec-drift-precheck
  message: "Specification drift detected — N findings require reviewer attention"
  drift_score: {score}
  findings:
    - category: missing-ac
      severity: high
      detail: "AC-2 not addressed in Dev Assessment"
    - category: major-deviation
      severity: high
      detail: "Major deviation requires reviewer attention: Changed data model"
  recovery:
    - "Address all acceptance criteria in Dev Assessment AC Coverage section"
    - "Log deviations using 6-field format in ## Design Deviations"
    - "Remove or justify files not traceable to acceptance criteria"
    - "Set Implementation Complete to Yes when all work is done"
```
</fail>

</gate>
