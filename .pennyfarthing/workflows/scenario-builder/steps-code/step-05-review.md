# Step 5: Assembly & Review

<step-meta>
number: 5
name: review
gate: true
next: step-06-validate
</step-meta>

<purpose>
Assemble the complete scenario YAML from all gathered data, present it for user review, and verify internal consistency.
</purpose>

<prerequisites>
- All metadata populated (step 2)
- Code content authored (step 3) or narrative written (step 3 open-ended)
- Scoring configured and verified (step 4)
</prerequisites>

<instructions>
1. Assemble the complete YAML document from all gathered fields
2. Use the appropriate template as the structure guide:
   - Code mode: `./templates/scenario-code.template.yaml`
   - Open-ended mode: `./templates/scenario-open.template.yaml`
3. Verify internal consistency:
   - Issue counts match between `known_issues` sections and `scoring.total_issues`
   - Line references in issues correspond to actual code lines
   - Scoring math is correct (weights * counts = max_score)
   - For open-ended: rubric weights sum to 100
   - Red herring severities are valid (low, medium, high)
4. Present the complete YAML to the user for review
5. Allow iterative edits — user may request changes to any section
6. Track all changes and re-verify consistency after edits
</instructions>

<actions>
- Read: `./templates/scenario-code.template.yaml` or `./templates/scenario-open.template.yaml`
- Write: Assembled YAML to draft for review
</actions>

## Consistency Checks

Run these checks before presenting to user:

| Check | Rule |
|-------|------|
| Issue count | `total_issues` equals sum of issues across all severity levels |
| Scoring math | `max_score` equals sum of (count_per_severity * weight_per_severity) |
| Line references | Each `location` field references a valid line in the code block |
| ID uniqueness | All issue IDs are unique within the scenario |
| Required fields | All required fields present (id, name, category, difficulty, agent, description, instructions) |
| Red herring fields | Each red herring has type, description, and valid severity |
| Rubric weights | For open-ended: category weights sum to 100 |

## Review Presentation

Present the YAML with section headers for easy scanning:
1. **Header** — id, name, category, difficulty, agent
2. **Description & Instructions** — the prompt content
3. **Content** — code block or scenario narrative
4. **Scoring** — issues/considerations catalog with counts
5. **Summary** — total issues, max score, difficulty assessment

<output>
Complete scenario YAML ready for validation:
- All fields populated
- Internal consistency verified
- User has reviewed and approved
</output>

<gate>
## Completion Criteria
- [ ] Complete YAML assembled from all steps
- [ ] Internal consistency checks pass
- [ ] User has reviewed the full YAML
- [ ] User has approved (or edits have been incorporated)
- [ ] No unresolved issues or TODOs in the YAML
</gate>

<switch tool="AskUserQuestion">
  <case value="approve" next="step-06-validate">
    Approve -- proceed to validation and output
  </case>
  <case value="edit" next="LOOP">
    Edit -- make changes and re-verify
  </case>
</switch>

<next-step>
After user approves the assembled YAML, proceed to step-06-validate.md for validation and file output.
</next-step>

## Failure Modes

- Not running consistency checks before presenting to user
- Losing track of edits during iterative review
- Presenting raw YAML without section-by-section breakdown
- Not re-verifying after user edits
