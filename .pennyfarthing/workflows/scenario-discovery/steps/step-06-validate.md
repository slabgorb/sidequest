# Step 6: Validate and Baseline

<step-meta>
step: 6
workflow: scenario-discovery
agent: orchestrator
name: validate
gate: true
next: step-07-verify-persona
</step-meta>

<purpose>
Validate the scenario against schema, optionally run a control baseline to calibrate
difficulty, and verify the scenario produces meaningful score discrimination.
</purpose>

<prerequisites>
- Scenario YAML written to benchmarks directory (step 5)
- All required fields populated
</prerequisites>

<instructions>
1. **Schema validation**
   Run the scenario validator against the new file:
   ```bash
   pf validate scenario {scenario_file}
   ```
   Fix any validation errors before proceeding.

2. **Smoke test with /solo**
   Run a single agent on the scenario to verify it works end-to-end:
   ```
   /solo {agent_target} --scenario {id}
   ```
   Check that:
   - The agent receives the stimulus correctly
   - The judge can score the response
   - The score falls within a reasonable range (not 0 or 100)

3. **Optional: Create control baseline**
   If the scenario is ready for calibration:
   ```
   /benchmark-control {agent_target} --scenario {id} --runs 10
   ```
   This creates `internal/results/baselines/{id}/{agent}/summary.yaml` with:
   - Mean score
   - Standard deviation
   - 95% confidence interval
   - Sample size

4. **Calibrate difficulty** (if baseline was run)
   Compare baseline statistics against the difficulty tiers:
   - easy: mean >= 80, stddev < 8
   - medium: mean 65-79, stddev < 12
   - hard: mean 50-64 OR stddev >= 12
   - extreme: mean < 50

   If declared difficulty doesn't match empirical difficulty, update the scenario.

5. **Check for ceiling/floor effects**
   - If mean > 95: scenario is too easy, needs harder elements
   - If mean < 20: scenario may be broken or too ambiguous
   - If stddev < 3: scenario doesn't discriminate between agents (all score similarly)
   - If stddev > 30: stimulus may be ambiguous (bimodal distribution)
</instructions>

<actions>
- Run: `pf validate scenario {scenario_file}` (schema check)
- Run: `/solo` for smoke test
- Run: `/benchmark-control` for baseline (optional)
</actions>

<output>
Validation results:
- Schema: pass/fail with error details
- Smoke test: score and judge feedback
- Baseline (if run): mean, stddev, CI, n
- Difficulty calibration: declared vs empirical
</output>

<gate>
## Completion Criteria
- [ ] Schema validation passes
- [ ] Smoke test produces a reasonable score (not 0 or 100)
- [ ] Judge can score the response without errors
- [ ] No ceiling or floor effects detected
- [ ] Difficulty label matches empirical data (or baseline deferred)
</gate>

<next-step>
After validation, proceed to step-07-verify-persona.md for persona persistence verification.
</next-step>

## Failure Modes

- Skipping schema validation (broken scenarios pollute the corpus)
- Not running a smoke test (scenario may not work end-to-end)
- Ignoring ceiling effects (easy scenarios don't discriminate)
- Forcing difficulty to match declared rather than updating the label
