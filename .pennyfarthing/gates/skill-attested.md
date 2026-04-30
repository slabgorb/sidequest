<gate name="skill-attested" model="haiku">

<purpose>
Reference template for verifying that required superpowers skills have been
invoked and attested in the session file.

This file is NOT referenced directly by workflow YAML. Composite gates that
need skill attestation (e.g., gates/sdd-red-exit, gates/sdd-green-exit)
include their own `<check name="skill-attested">` block with phase-specific
required skills listed inline.
</purpose>

<check name="skill-attested">
Read the session file at `.session/{STORY_ID}-session.md`.

Look for a <skills-invoked> element containing one <skill/> per invocation:

    <skills-invoked>
      <skill name="test-driven-development" phase="red" at="2026-04-19T14:22:03Z"/>
      <skill name="verification-before-completion" phase="green" at="2026-04-19T15:01:47Z"/>
    </skills-invoked>

For each skill name in the composite gate's required list:
- Find at least one <skill/> element whose `name` attribute matches AND
  whose `phase` attribute equals the current phase.
- If missing, fail with recovery guidance to invoke the skill and attest.
</check>

<pass>
All required skills have attestation entries for the current phase.

```yaml
GATE_RESULT:
  status: pass
  gate: skill-attested
  message: "All required skills attested for phase {phase}"
  checks:
    - name: skill-attested
      status: pass
      detail: "Attested: {comma-separated skill names}"
```
</pass>

<fail>
One or more required skills has no attestation entry for the current phase.

```yaml
GATE_RESULT:
  status: fail
  gate: skill-attested
  message: "Missing skill attestations: {missing list}"
  checks:
    - name: skill-attested
      status: fail
      detail: "Expected: {required}. Found: {found}. Missing: {missing}"
  recovery:
    - "Invoke each missing skill via the Skill tool"
    - "After invocation, append an entry to <skills-invoked> in the session file:"
    - "  <skill name=\"<name>\" phase=\"<current-phase>\" at=\"<ISO8601 timestamp>\"/>"
    - "Re-run the exit protocol"
```
</fail>

</gate>
