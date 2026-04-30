<gate name="sdd-green-exit" model="haiku">

<purpose>
Composite gate for Dev GREEN-phase handoff in the SDD workflow.
Extends dev-exit with a skill-attested check for three superpowers skills.
</purpose>

<ref gate="gates/dev-exit" />

<check name="skill-attested">
Read the session file at `.session/{STORY_ID}-session.md`. Look for a
<skills-invoked> element.

If the <skills-invoked> element is absent from the session file entirely,
treat every required skill as missing and fail — do NOT treat absence of
the element as inability to check.

The GREEN phase of the SDD workflow requires attestation for:
  - test-driven-development
  - verification-before-completion
  - requesting-code-review

For each required skill, find at least one <skill/> element whose
`name` attribute matches AND whose `phase` attribute equals "green".
Attestations recorded for other phases (e.g., the RED phase) do NOT
satisfy this gate — each phase must be attested during that phase.

If any required skill has no matching entry, fail with recovery guidance.
</check>

<pass>
Run all checks from gates/dev-exit first (test-suite, working-tree,
branch-status, no-debug-code), then run the skill-attested check.

If ALL pass:

```yaml
GATE_RESULT:
  status: pass
  gate: sdd-green-exit
  message: "GREEN complete: tests pass, tree clean, all required skills attested"
  checks:
    - name: test-suite
      status: pass
      detail: "{passed}/{total} tests passing"
    - name: working-tree
      status: pass
      detail: "No uncommitted changes"
    - name: branch-status
      status: pass
      detail: "On branch {branch}, HEAD at {short-sha}"
    - name: no-debug-code
      status: pass
      detail: "No debug patterns found"
    - name: skill-attested
      status: pass
      detail: "Attested: test-driven-development, verification-before-completion, requesting-code-review"
```
</pass>

<fail>
If ANY check fails, run all remaining checks (don't short-circuit):

```yaml
GATE_RESULT:
  status: fail
  gate: sdd-green-exit
  message: "GREEN gate failed: {summary of failures}"
  checks:
    - name: test-suite
      status: pass | fail
      detail: "{test results or failure list}"
    - name: working-tree
      status: pass | fail
      detail: "{clean or list of uncommitted files}"
    - name: branch-status
      status: pass | fail
      detail: "{branch match or mismatch details}"
    - name: no-debug-code
      status: pass | fail
      detail: "{clean or list of debug code locations}"
    - name: skill-attested
      status: pass | fail
      detail: "Expected: test-driven-development, verification-before-completion, requesting-code-review. Found: {found}. Missing: {missing}"
  recovery:
    - "Fix failing tests in: {file1}, {file2}"
    - "Commit or stash uncommitted changes"
    - "Remove debug code: {file:line patterns}"
    - "Invoke any missing superpowers skills"
    - "Append attestations to <skills-invoked> in session file:"
    - "  <skill name=\"<name>\" phase=\"green\" at=\"<ISO8601>\"/>"
```
</fail>

</gate>
