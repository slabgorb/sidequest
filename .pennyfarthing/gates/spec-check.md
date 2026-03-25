<gate name="spec-check" model="haiku">

<purpose>
Verify that the Dev's implementation aligns with the story context and acceptance criteria.
Catches specification drift — where working code diverges from the agreed spec — before
the Reviewer phase.

Checks:
1. All acceptance criteria from the context file are addressed in the Dev Assessment
2. Implementation Complete flag is Yes
3. Design Deviations are properly logged by both TEA and Dev (delegates format validation
   to pf.gates.deviations)

Used by: spec-check phase (after green, before review) in TDD workflow.
</purpose>

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `SESSION_FILE` | Yes | Path to session file |
| `CONTEXT_FILE` | Yes | Path to story context file |
</arguments>

<pass>
Run the Python validation function to check spec alignment:

```bash
python3 -c "
from pf.gates.spec_check import validate_spec_alignment
import json, sys
result = validate_spec_alignment('${SESSION_FILE}', '${CONTEXT_FILE}')
print(json.dumps(result, indent=2))
sys.exit(0 if result['success'] else 1)
"
```

The validator checks:
1. Context file has ## Acceptance Criteria with AC-N items
2. Session file's Dev Assessment has AC Coverage listing that addresses all context ACs
3. Implementation Complete flag is Yes
4. TEA and Dev deviation subsections are present and properly formatted (delegates to pf.gates.deviations)

If all checks pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: spec-check
  message: "Implementation aligns with story context — all ACs addressed, deviations logged"
  checks:
    - name: ac-coverage
      status: pass
      detail: "All {N} ACs addressed in Dev Assessment"
    - name: implementation-complete
      status: pass
      detail: "Implementation marked complete"
    - name: deviations-tea
      status: pass
      detail: "TEA deviations properly logged"
    - name: deviations-dev
      status: pass
      detail: "Dev deviations properly logged"
```
</pass>

<fail>
If validation fails, the result contains specific findings:

**Missing AC coverage:**
```yaml
GATE_RESULT:
  status: fail
  gate: spec-check
  message: "Specification drift detected — missing AC coverage"
  checks:
    - name: ac-coverage
      status: fail
      detail: "Missing AC coverage: AC-2, AC-5"
  recovery:
    - "Add coverage for missing ACs in the Dev Assessment's AC Coverage section"
    - "Each AC from the context file must appear as '- AC-N: description — DONE'"
    - "If an AC was intentionally skipped, log a deviation in ## Design Deviations"
```

**Implementation not complete:**
```yaml
GATE_RESULT:
  status: fail
  gate: spec-check
  message: "Implementation not marked complete"
  checks:
    - name: implementation-complete
      status: fail
      detail: "Implementation Complete flag is 'No'"
  recovery:
    - "Set **Implementation Complete:** Yes in the Dev Assessment when all work is done"
    - "If implementation is genuinely incomplete, return to the green phase"
```

**Deviation format issues:**
```yaml
GATE_RESULT:
  status: fail
  gate: spec-check
  message: "Deviation logging issues detected"
  checks:
    - name: deviations-dev
      status: fail
      detail: "Dev deviations: Missing '### Dev (implementation)' subsection"
  recovery:
    - "Add the missing deviation subsection to ## Design Deviations"
    - "Log each spec deviation using the 6-field format from guides/deviation-format.md"
    - "Or write '- No deviations from spec.' if none"
```
</fail>

</gate>
