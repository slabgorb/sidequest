<gate name="deviations-logged" model="haiku">

<purpose>
Verify the agent logged their Design Deviations section in the session file before handoff,
and that every deviation entry conforms to the 6-field format defined in `guides/deviation-format.md`.

TEA must have a `### TEA (test design)` subheading. Dev must have a `### Dev (implementation)` subheading.
Either structured 6-field entries or an explicit "No deviations from spec." is valid — the section
cannot be missing, empty, or contain malformed entries.

Used by: tea-exit (after red phase), dev-exit (after green phase).
</purpose>

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `AGENT` | Yes | `tea`, `dev`, or `architect` — determines which subheading to check |
| `SESSION_FILE` | Yes | Path to session file |
</arguments>

<pass>
Run the Python validation function to check the session file:

```bash
python3 -c "
from pf.gates.deviations import validate_deviations
import json, sys
result = validate_deviations('${SESSION_FILE}', '${AGENT}')
print(json.dumps(result))
sys.exit(0 if result['status'] == 'pass' else 1)
"
```

The validator checks:
1. `## Design Deviations` section exists
2. The agent-specific subsection (`### TEA (test design)`, `### Dev (implementation)`, or `### Architect (reconcile)`) exists
3. The subsection is not empty
4. Each entry has all 6 required fields: Spec source, Spec text, Implementation, Rationale, Severity, Forward impact
5. Severity is `minor` or `major`
6. Forward impact starts with `none`, `minor`, or `breaking`
7. "No deviations from spec." is accepted as a valid entry

If validation passes, return:

```yaml
GATE_RESULT:
  status: pass
  gate: deviations-logged
  message: "Design deviations documented by {AGENT} — {entries_count} entries validated"
  checks:
    - name: deviations-format
      status: pass
      detail: "All entries conform to 6-field format under {HEADING}"
```
</pass>

<fail>
If validation fails, the result contains specific error information:

**Missing section entirely:**
```yaml
GATE_RESULT:
  status: fail
  gate: deviations-logged
  message: "Missing '## Design Deviations' section in session file"
  checks:
    - name: deviations-section
      status: fail
      detail: "Session file has no '## Design Deviations' section"
  recovery:
    - "Add a '## Design Deviations' section to the session file"
    - "Add the agent subsection: '{HEADING}'"
    - "Log each spec deviation using the 6-field format from guides/deviation-format.md"
    - "Or write '- No deviations from spec.' if none"
```

**Missing agent subsection:**
```yaml
GATE_RESULT:
  status: fail
  gate: deviations-logged
  message: "Missing '{HEADING}' subsection in Design Deviations"
  checks:
    - name: deviations-subsection
      status: fail
      detail: "Design Deviations section exists but '{HEADING}' subsection is missing"
  recovery:
    - "Add '{HEADING}' under '## Design Deviations' in the session file"
    - "Log each spec deviation, or write '- No deviations from spec.' if none"
```

**Incomplete entries (field-level recovery):**
```yaml
GATE_RESULT:
  status: fail
  gate: deviations-logged
  message: "Entry '{description}' missing: {field list}"
  checks:
    - name: deviations-format
      status: fail
      detail: "{error_count} entries have missing or invalid fields"
  recovery:
    - "Fix the following entries:"
    - "Entry '{description}' missing: {field list}"
    - "Required fields: Spec source, Spec text, Implementation, Rationale, Severity, Forward impact"
    - "See guides/deviation-format.md for the full format specification"
```
</fail>

</gate>
