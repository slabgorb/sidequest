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
- Scenario narrative authored (step 3)
- Considerations, rubric, and persona mappings defined (step 4)
</prerequisites>

<instructions>
1. Assemble the complete YAML document from all gathered fields
2. Use `./templates/scenario-open.template.yaml` as the structure guide
3. Verify internal consistency:
   - Rubric category weights sum to exactly 100
   - Each rubric category has criteria with point values
   - Persona influence areas have complete spectrums
   - Expected tendencies reference valid personas
   - All required fields present
4. Present the complete YAML to the user for review
5. Allow iterative edits — user may request changes to any section
6. Track all changes and re-verify consistency after edits
</instructions>

<actions>
- Read: `./templates/scenario-open.template.yaml`
- Write: Assembled YAML to draft for review
</actions>

## Consistency Checks

Run these checks before presenting to user:

| Check | Rule |
|-------|------|
| Required fields | id, name, category, difficulty, agent, description, purpose, instructions present |
| Rubric weights | Category weights sum to exactly 100 |
| Criteria points | Each rubric category has at least 2 criteria with points |
| Influence areas | At least 2 areas with complete spectrums (3 points each) |
| Expected tendencies | At least 3 personas mapped with traits and likely outcomes |
| Consideration IDs | All IDs are unique SCREAMING_SNAKE_CASE |
| Narrative completeness | Scenario content has sufficient depth for difficulty level |

## Review Presentation

Present the YAML with section headers for easy scanning:
1. **Header** — id, name, category, difficulty, agent
2. **Description, Purpose & Instructions** — the prompt content
3. **Scenario Narrative** — the full problem description
4. **Known Considerations** — organized by domain with counts
5. **Scoring Rubric** — categories, weights, and criteria
6. **Persona Influence Areas** — spectrums for differentiation
7. **Expected Tendencies** — persona predictions
8. **Summary** — total considerations, weight verification, persona count

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
- [ ] Rubric weights verified (sum to 100)
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
- Not re-verifying rubric weights after user edits
