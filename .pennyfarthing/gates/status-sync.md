<gate name="status-sync" model="haiku">

<purpose>
Verify that YAML sprint status and Jira status are aligned at the expected state
for the current phase transition. Catches drift between local tracking and Jira
before agents proceed with phase work.
</purpose>

<context>
Expected statuses by entering phase:

| Entering Phase | Expected YAML Status | Expected Jira Status |
|---------------|---------------------|---------------------|
| red/implement | in_progress | In Progress |
| green | in_progress | In Progress |
| verify | in_progress | In Progress |
| review | in_review | In Review |
| finish | in_review | In Review |
</context>

<pass>
1. Read the story ID from the session file: `**Story:** {story_id}`
2. Get YAML status:
```bash
pf sprint story field {story_id} status
```
3. Get Jira key from session: `**Jira:** {jira_key}`
4. Get Jira status:
```bash
pf jira view {jira_key} --json
```
Extract the `status` field from the JSON output.

5. Compare both against the expected status for the current phase.

If both YAML and Jira match expected status, return:

```yaml
GATE_RESULT:
  status: pass
  gate: status-sync
  message: "YAML ({yaml_status}) and Jira ({jira_status}) aligned for {phase} phase"
  checks:
    - name: yaml-status
      status: pass
      detail: "YAML status: {yaml_status} (expected: {expected})"
    - name: jira-status
      status: pass
      detail: "Jira status: {jira_status} (expected: {expected})"
```
</pass>

<fail>
If YAML or Jira status does not match expected:

```yaml
GATE_RESULT:
  status: fail
  gate: status-sync
  message: "Status mismatch for {phase} phase"
  checks:
    - name: yaml-status
      status: {pass|fail}
      detail: "YAML status: {yaml_status} (expected: {expected})"
    - name: jira-status
      status: {pass|fail}
      detail: "Jira status: {jira_status} (expected: {expected})"
  recovery:
    - "Fix YAML: pf sprint story update {story_id} --status {expected_yaml}"
    - "Fix Jira: pf jira move {jira_key} \"{expected_jira}\""
    - "Then re-run the gate check"
```
</fail>

</gate>
