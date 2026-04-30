<gate name="sdd-red-exit" model="haiku">

<purpose>
Composite gate for TEA RED-phase handoff in the SDD workflow.
Extends tests-fail with a skill-attested check for the
test-driven-development skill.
</purpose>

<ref gate="gates/tests-fail" />

<check name="skill-attested">
Read the session file at `.session/{STORY_ID}-session.md`. Look for a
<skills-invoked> element.

If the <skills-invoked> element is absent from the session file entirely,
treat every required skill as missing and fail — do NOT treat absence of
the element as inability to check.

The RED phase of the SDD workflow requires attestation for:
  - test-driven-development

For each required skill, find at least one <skill/> element whose
`name` attribute matches AND whose `phase` attribute equals "red".
Attestations recorded for other phases do NOT satisfy this gate.

If any required skill has no matching entry, fail with recovery guidance.
</check>

<pass>
Run all checks from gates/tests-fail first (ac-coverage, tests-red),
then run the skill-attested check.

If ALL pass:

```yaml
GATE_RESULT:
  status: pass
  gate: sdd-red-exit
  message: "RED complete: {N} failing tests, TDD skill attested"
  checks:
    - name: ac-coverage
      status: pass
      detail: "All ACs have test coverage"
    - name: tests-red
      status: pass
      detail: "{N} tests failing as expected"
    - name: skill-attested
      status: pass
      detail: "Attested: test-driven-development"
```
</pass>

<fail>
If ANY check fails, run all remaining checks (don't short-circuit) and return:

```yaml
GATE_RESULT:
  status: fail
  gate: sdd-red-exit
  message: "RED gate failed: {summary of failures}"
  checks:
    - name: ac-coverage
      status: pass | fail
      detail: "{coverage summary or list of uncovered ACs}"
    - name: tests-red
      status: pass | fail
      detail: "{test state or list of tests that shouldn't be passing yet}"
    - name: skill-attested
      status: pass | fail
      detail: "Expected: test-driven-development. Found: {found}. Missing: {missing}"
  recovery:
    - "Add tests for any uncovered ACs"
    - "Verify all new tests are failing (RED) — implementation should not yet exist"
    - "Invoke superpowers:test-driven-development skill if not yet done"
    - "Append attestation to <skills-invoked> in session file:"
    - "  <skill name=\"test-driven-development\" phase=\"red\" at=\"<ISO8601>\"/>"
```
</fail>

</gate>
