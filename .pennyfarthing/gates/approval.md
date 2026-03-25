<gate name="approval" model="haiku">

<purpose>
Verify the reviewer has issued an explicit verdict on the code review
AND that all specialist subagents were dispatched, received, assessed,
and their results documented with clear decisions. This gate runs after
the Reviewer agent's review phase to confirm the code has been formally
approved or rejected before proceeding.
</purpose>

<pass>
Check the session file for a Reviewer Assessment section AND a complete Subagent Results table:

1. **Find verdict:** Look for `## Reviewer Assessment` section in the session file.
   - Search for an explicit APPROVED verdict
   - The verdict must be unambiguous — not "looks good" but "APPROVED"

2. **Verify completeness:** The assessment should include:
   - A clear verdict (APPROVED)
   - Summary of what was reviewed

3. **Verify subagent completion** (see nested gate below) — ALL subagents must be received and assessed

4. **Verify subagent dispatch tags** (see nested gate below) — ALL 8 specialist tags present

5. **Verify subagent-before-conclusions gate** — VERIFIEDs must not contradict subagent findings without explicit `Challenged:` notes. See `gates/subagent-before-conclusions.md`.

6. **Verify rule compliance section** (see nested gate below) — `### Rule Compliance` section exists with enumerated rules

7. **Verify VERIFIED rule citations** (see nested gate below) — every VERIFIED includes rule compatibility check

If the review is APPROVED and all subgates pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: approval
  message: "Code review APPROVED by reviewer, all specialist subagents received and assessed"
  checks:
    - name: reviewer-verdict
      status: pass
      detail: "Explicit APPROVED verdict found in Reviewer Assessment"
    - name: subagent-completion
      status: pass
      detail: "All 9 subagents received with decisions documented"
    - name: subagent-dispatch
      status: pass
      detail: "All 8 specialist tags found in assessment"
    - name: rule-compliance
      status: pass
      detail: "Rule Compliance section with enumerated rules and instances"
    - name: verified-rule-citation
      status: pass
      detail: "All VERIFIEDs include rule compatibility checks"
```
</pass>

<fail>
If the review is not approved, diagnose and report:

1. **REJECTED verdict:** The reviewer found issues that need addressing.
   - Extract the specific findings from the Reviewer Assessment
   - List each finding with its severity
   - These must be addressed before the gate can pass

2. **No verdict found:** The reviewer hasn't completed the review yet.
   - The Reviewer Assessment section is missing or incomplete
   - The reviewer needs to complete their review

3. **Incomplete subagent results:** The reviewer did not wait for all subagents.
   - See nested gate failure for details on which subagents are missing
   - The reviewer MUST wait for all subagents — context pressure is not an excuse

4. **Missing subagent tags:** The reviewer skipped specialist subagents.
   - See nested gate failure for details on which tags are missing

5. **Missing decisions:** Subagent findings exist but no confirm/dismiss/defer decision.
   - Every finding from every subagent must have a documented decision
   - "Skipped because context was high" is NOT a valid decision

6. **Missing Rule Compliance section:** The reviewer skipped the rule-by-rule enumeration.
   - See nested gate failure for details

7. **VERIFIEDs lack rule citations:** VERIFIED items don't include rule compatibility checks.
   - See nested gate failure for details

Return with actionable recovery guidance:

```yaml
GATE_RESULT:
  status: fail
  gate: approval
  message: "Gate failed: {reason}"
  checks:
    - name: reviewer-verdict
      status: pass | fail
      detail: "{verdict status}"
    - name: subagent-completion
      status: pass | fail
      detail: "{completion status — which subagents missing}"
    - name: subagent-dispatch
      status: pass | fail
      detail: "{tag coverage status}"
    - name: rule-compliance
      status: pass | fail
      detail: "{rule compliance section status}"
    - name: verified-rule-citation
      status: pass | fail
      detail: "{VERIFIED rule citation status}"
  recovery:
    - "Address reviewer findings: {finding1}, {finding2}"
    - "Complete the Subagent Results table — all 9 rows must show Received: Yes"
    - "Document decisions for all findings — confirmed, dismissed (with rationale), or deferred"
    - "Re-run review with all specialist subagents"
    - "Add ### Rule Compliance section with enumerated rules and per-instance judgments"
    - "Add rule compatibility citation to every VERIFIED"
```
</fail>

<gate name="subagent-completion" model="haiku">

<purpose>
Verify the Reviewer waited for ALL 8 subagents to return before writing the assessment.
The session file must contain a `## Subagent Results` table with all 9 rows filled,
each showing `Received: Yes` (or an explicit error notation), and every finding having
a documented decision. This prevents rushed reviews where the reviewer skips subagent
results due to context pressure or impatience.
</purpose>

<pass>
Search the session file for a `## Subagent Results` section containing:

1. **A table with 9 rows** — one for each specialist subagent
2. **Every row shows `Yes` in the Received column** (or explicit error/timeout notation)
3. **Every row has a Decision** — `confirmed N, dismissed N, deferred N` or `N/A` for clean results
4. **An `All received: Yes` line** after the table

**Required subagents (9):**
- `reviewer-preflight`
- `reviewer-edge-hunter`
- `reviewer-silent-failure-hunter`
- `reviewer-test-analyzer`
- `reviewer-comment-analyzer`
- `reviewer-type-design`
- `reviewer-security`
- `reviewer-simplifier`
- `reviewer-rule-checker`

If all 8 are received and decisions are documented, return:

```yaml
GATE_RESULT:
  status: pass
  gate: subagent-completion
  message: "All 9 subagents received and assessed with documented decisions"
  checks:
    - name: all-received
      status: pass
      detail: "9/9 subagents returned results"
    - name: all-decided
      status: pass
      detail: "Every finding has a confirm/dismiss/defer decision"
```
</pass>

<fail>
If the Subagent Results table is missing, incomplete, or has gaps:

1. **No table:** The reviewer skipped the completion gate entirely
2. **Missing rows:** Some subagents were not waited for
3. **Missing decisions:** Findings exist but lack confirm/dismiss/defer

```yaml
GATE_RESULT:
  status: fail
  gate: subagent-completion
  message: "Subagent results incomplete: {specific problem}"
  checks:
    - name: all-received
      status: fail
      detail: "{N}/8 subagents received. Missing: {list}"
    - name: all-decided
      status: fail
      detail: "Findings without decisions: {count}"
  recovery:
    - "Wait for all subagents to return — do not proceed until complete"
    - "Fill in every row of the Subagent Results table"
    - "Document a decision for every finding: confirmed, dismissed (with rationale), or deferred"
    - "Context pressure is not a reason to skip — the system handles context management"
```
</fail>

</gate>

<gate name="subagent-dispatch" model="haiku">

<purpose>
Verify the Reviewer ran all 8 specialist subagents during the review.
The Reviewer Assessment must contain tagged findings or explicit dismissals
from each specialist category. This prevents rubber-stamp reviews that skip
the parallel analysis pipeline.
</purpose>

<pass>
Search the Reviewer Assessment section in the session file for these 8 tags.
Each tag must appear at least once — either as a confirmed finding or an
explicit dismissal (e.g., "[SEC] No security concerns" counts).

**Required tags:**
- `[EDGE]` — edge-hunter (boundary conditions)
- `[SILENT]` — silent-failure-hunter (swallowed errors)
- `[TEST]` — test-analyzer (test quality)
- `[DOC]` — comment-analyzer (documentation)
- `[TYPE]` — type-design (type invariants)
- `[SEC]` — security (vulnerabilities)
- `[SIMPLE]` — simplifier (unnecessary complexity)
- `[RULE]` — rule-checker (project rule violations)

If all 8 tags are present, return:

```yaml
GATE_RESULT:
  status: pass
  gate: subagent-dispatch
  message: "All 8 specialist subagent categories represented in assessment"
  checks:
    - name: tag-coverage
      status: pass
      detail: "Found: [EDGE], [SILENT], [TEST], [DOC], [TYPE], [SEC], [SIMPLE], [RULE]"
```
</pass>

<fail>
If any tags are missing, the reviewer skipped specialist subagents.
List which tags are present and which are missing.

```yaml
GATE_RESULT:
  status: fail
  gate: subagent-dispatch
  message: "Missing specialist subagent tags: {missing_list}"
  checks:
    - name: tag-coverage
      status: fail
      detail: "Found: {present_list}. Missing: {missing_list}"
  recovery:
    - "Re-run the review phase with all 8 subagents spawned in parallel"
    - "Each specialist must be represented in the assessment with its tag"
    - "Tags: [EDGE], [SILENT], [TEST], [DOC], [TYPE], [SEC], [SIMPLE]"
```
</fail>

</gate>

<gate name="rule-compliance" model="haiku">

<purpose>
Verify the Reviewer performed exhaustive rule-by-rule checking against the project's
rules files (CLAUDE.md, SOUL.md, .claude/rules/*.md). The assessment must contain a
`### Rule Compliance` section that enumerates specific rules and checks EVERY applicable
instance in the code — not just one exemplar per rule.

This prevents the "thematic scanning" failure where the reviewer catches one PluginId pub
field violation but misses the identical pattern on PluginManifest and RawEvent.
</purpose>

<pass>
Search the session file (in or near the Reviewer Assessment) for a `### Rule Compliance` section containing:

1. **Section exists** — `### Rule Compliance` heading is present
2. **Rules are enumerated** — at least 3 specific rules are listed by name or description
   (e.g., "private fields with getters", "#[non_exhaustive] on enums that will grow",
   "validated constructors return Result")
3. **Instances are checked per rule** — each rule lists the specific types/functions/enums
   it was checked against, not just "all checked" or "compliant"
4. **Judgments are explicit** — each instance is marked compliant or violation

Example of a PASSING section:
```
### Rule Compliance
**Rule: #[non_exhaustive] on enums that will grow**
- PluginKind (identity.rs:68) — VIOLATION: missing
- PluginHealth (health.rs:7) — VIOLATION: missing
- PluginError (error.rs:12) — compliant

**Rule: private fields with getters on security-critical types**
- RawEvent.tenant_id (lib.rs:24) — VIOLATION: pub field
- PluginManifest.permissions (manifest.rs:15) — VIOLATION: pub field
- PluginId.namespace (identity.rs:16) — VIOLATION: pub field
```

Example of a FAILING section:
```
### Rule Compliance
All project rules checked. Code is compliant.
```
(No specific rules listed, no instances enumerated — this is a rubber stamp)

If the section exists with enumerated rules and instances:

```yaml
GATE_RESULT:
  status: pass
  gate: rule-compliance
  message: "Rule Compliance section contains enumerated rules with per-instance judgments"
  checks:
    - name: section-exists
      status: pass
      detail: "### Rule Compliance heading found"
    - name: rules-enumerated
      status: pass
      detail: "{N} specific rules listed"
    - name: instances-checked
      status: pass
      detail: "Per-instance judgments found for each rule"
```
</pass>

<fail>
If the Rule Compliance section is missing, generic, or lacks per-instance checking:

1. **No section:** The reviewer skipped rule-by-rule enumeration entirely
2. **Generic compliance claim:** Section exists but just says "all rules checked" without
   listing specific rules or instances
3. **Missing instances:** Rules listed but not checked against specific types/functions

```yaml
GATE_RESULT:
  status: fail
  gate: rule-compliance
  message: "Rule Compliance section missing or insufficient: {specific problem}"
  checks:
    - name: section-exists
      status: pass | fail
      detail: "{whether ### Rule Compliance heading found}"
    - name: rules-enumerated
      status: pass | fail
      detail: "{whether specific rules are listed by name}"
    - name: instances-checked
      status: pass | fail
      detail: "{whether per-instance judgments exist}"
  recovery:
    - "Add a ### Rule Compliance section to the assessment"
    - "Read the project's rules files: CLAUDE.md, SOUL.md, .claude/rules/*.md"
    - "For EACH applicable rule, list EVERY type/struct/enum/function it governs in the diff"
    - "Mark each instance as compliant or violation — do not summarize"
    - "One exemplar per rule is not enough — check ALL instances"
```
</fail>

</gate>

<gate name="verified-rule-citation" model="haiku">

<purpose>
Verify that every [VERIFIED] item in the Reviewer Assessment includes a rule
compatibility check — not just line-level evidence that the feature exists.

This prevents the failure where the reviewer writes "[VERIFIED] RawEvent carries
TenantId — ingestion/src/lib.rs:24" (proving the field exists) without checking
whether the field being pub violates the private-fields-with-getters rule.
Existence is not compliance.
</purpose>

<pass>
Search the Reviewer Assessment for all `[VERIFIED]` items. For each one, check:

1. **Line evidence present** — cites specific file:line
2. **Rule check present** — mentions which project rule(s) were checked, or explicitly
   states no applicable rules. Look for patterns like:
   - "Complies with {rule name}"
   - "Checked against {rule} — compliant"
   - "No applicable project rules for this item"
   - A reference to a rule by name or description

A VERIFIED that only proves existence without rule checking is INSUFFICIENT:
- BAD: `[VERIFIED] RawEvent carries TenantId — ingestion/src/lib.rs:24 has pub tenant_id: TenantId`
- GOOD: `[VERIFIED] RawEvent.tenant_id is private with getter — ingestion/src/lib.rs:24 field is pub(crate), getter at line 30. Complies with private-fields-with-getters rule.`

If ALL VERIFIEDs include rule citations:

```yaml
GATE_RESULT:
  status: pass
  gate: verified-rule-citation
  message: "All VERIFIED items include rule compatibility checks"
  checks:
    - name: verified-format
      status: pass
      detail: "{N} VERIFIEDs found, all include rule citations"
```
</pass>

<fail>
If any VERIFIED lacks a rule compatibility check:

```yaml
GATE_RESULT:
  status: fail
  gate: verified-rule-citation
  message: "VERIFIED items missing rule compatibility checks"
  checks:
    - name: verified-format
      status: fail
      detail: "{N} VERIFIEDs found, {M} lack rule citations: {list of deficient VERIFIEDs}"
  recovery:
    - "Every VERIFIED must include which project rules were checked"
    - "Proving a feature EXISTS is not the same as proving it COMPLIES with project rules"
    - "For each VERIFIED, ask: does ANY rule in CLAUDE.md, SOUL.md, or .claude/rules/ apply to this code?"
    - "If a rule applies, cite it and confirm compliance. If no rules apply, state that explicitly."
    - "Example: [VERIFIED] ... Complies with {rule name}. Or: No applicable project rules."
```
</fail>

</gate>

</gate>
