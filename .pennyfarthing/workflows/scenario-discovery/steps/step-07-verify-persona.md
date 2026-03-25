# Step 7: Verify Persona Persistence

<step-meta>
step: 7
workflow: scenario-discovery
agent: orchestrator
name: verify-persona
gate: true
next: none
</step-meta>

<purpose>
Verify that the scenario actually produces measurable persona differentiation -- different
personalities should approach it differently, not just communicate differently.

Scientific basis: MBTI-in-Thoughts (arxiv 2509.04343) verifies personality persistence
by running personality assessments AFTER task completion. PersonaGym measures whether
persona traits influence Expected Action, not just Linguistic Habits.
</purpose>

<prerequisites>
- Scenario validated and smoke-tested (step 6)
- Expected tendencies documented (step 5)
</prerequisites>

<instructions>
1. **Run the scenario with 2-3 contrasting personas** using `/solo`:
   - Pick personas with opposing traits (e.g., high-C vs low-C, high-O vs low-O)
   - Use `--as {theme}:{role}` to test specific theme personas
   ```
   /solo {theme_a}:{role} --scenario {id}
   /solo {theme_b}:{role} --scenario {id}
   ```

2. **Compare responses against expected tendencies**
   - Did the cautious persona respond cautiously?
   - Did the creative persona propose novel approaches?
   - Are the differences in WHAT they found/recommended, not just HOW they said it?

3. **Null hypothesis test**
   The null hypothesis is: "Personas only affect communication style, not substance."
   - If responses are substantively identical with different phrasing -> scenario FAILS
   - If responses differ in findings, priorities, or recommendations -> scenario PASSES

4. **Score discrimination check**
   Compare scores across the 2-3 runs:
   - If scores differ by >= 0.5 stddev -> good discrimination
   - If scores are within 0.2 stddev -> poor discrimination, scenario may need rework

5. **Document the verdict**
   ```yaml
   persona_verification:
     runs:
       - theme: {theme_a}
         role: {role}
         weighted_total: {score}
         substantive_differences: [list of how this persona's response differed]
       - theme: {theme_b}
         role: {role}
         weighted_total: {score}
         substantive_differences: [list]
     null_hypothesis_rejected: true | false
     discrimination: good | adequate | poor
     notes: "summary of what differentiated the responses"
   ```

6. **If scenario fails persona verification:**
   - Add more ambiguity or tension points that personality traits would resolve differently
   - Revisit persona_influence dimensions -- are they targeting the right traits?
   - Consider whether the scenario is too constrained (one obvious right answer)
</instructions>

<output>
Persona verification report with:
- 2-3 contrasting persona runs with scores
- Null hypothesis verdict (rejected = good)
- Discrimination assessment
- Final scenario status: ready | needs-rework
</output>

<gate>
## Completion Criteria
- [ ] At least 2 contrasting persona runs completed
- [ ] Responses compared for substantive (not just stylistic) differences
- [ ] Null hypothesis assessed
- [ ] Score discrimination measured
- [ ] Scenario marked as ready or flagged for rework
</gate>

## Success

When this step passes, the scenario is ready for:
- `/benchmark-control` to create a formal baseline (10 runs)
- `/benchmark {theme}:{role}` to compare personas with Cohen's d effect size
- Addition to the JobFair corpus for ongoing persona evaluation

## Failure Modes

- Comparing only communication style, not substance
- Using personas that are too similar (need opposing traits)
- Accepting poor discrimination without reworking the scenario
- Declaring success with only 1 persona run (need contrast)
