---
description: Compare an agent's performance against a stored baseline
argument-hint: <theme> <agent> [--as <role>] [--scenario <name>] [--runs N]
---

# Benchmark

<purpose>
Compare a persona agent's performance against the established control baseline. Runs the agent on the scenario and calculates statistical measures including effect size (Cohen's d) and significance.

Default: 4 runs for comparison (balance between reliability and runtime). Runs execute in parallel for faster results.

**Simplified Usage:** Just specify theme and agent role - you'll be presented with matching scenarios to choose from.
</purpose>

<critical-integrity-requirements>
## DO NOT FABRICATE COMPARISON DATA

Comparisons are only meaningful if BOTH the baseline AND the contestant runs are real.

**Before comparing:**
1. Validate baseline has proof-of-work (check runs have `proof.*` fields)
2. Actually run `/solo` for the contestant with real Task tool calls
3. Validate contestant runs have proof-of-work before calculating statistics

**Baseline Validation:**
Before using a baseline, spot-check at least one run file:
- Read a run from `internal/results/baselines/{scenario}/{agent}/runs/*.json`
- Verify it has `proof.agent_task_id`, `proof.agent_response_text`, `proof.judge_task_id`
- Verify `proof.agent_response_text` is at least 200 characters
- Verify `token_usage.input_tokens` > 0

**If baseline validation fails:**
```markdown
Error: Baseline for '{scenario}' appears to be fabricated (missing proof-of-work).
Run `/benchmark-control --scenario {scenario}` to create a real baseline.
```

**Contestant runs MUST include proof-of-work.** See `/solo` for requirements.
</critical-integrity-requirements>

<usage>
```
# Simple: Pick scenario interactively
/benchmark the-expanse sm
/benchmark discworld reviewer

# Direct: Specify scenario explicitly
/benchmark discworld reviewer --scenario order-service
/benchmark ted-lasso dev --scenario tdd-shopping-cart --runs 8

# Cross-role: Run any character as any role
/benchmark shakespeare prospero --as dev --scenario django-10554
/benchmark discworld granny --as dev --scenario tdd-shopping-cart
```

**Arguments:**
- `theme` - The persona theme (e.g., `discworld`, `the-expanse`, `ted-lasso`)
- `agent` - The agent role OR character name (if using `--as`)
- `--as <role>` - (Optional) Override role for cross-role testing. Makes `agent` a character name lookup.
- `--scenario` - (Optional) Scenario name. If omitted, shows matching scenarios to choose from.
- `--runs N` - Number of evaluation runs (default: 4, max: 20)

**Cross-Role Testing:**
The `--as` flag enables running any character as any role:
```
/benchmark shakespeare prospero --as dev --scenario django-10554
```
This uses Prospero's persona traits (wise orchestrator) but gives him a dev task.
The scenario's role determines what the agent is asked to do; the character determines HOW they do it.

**Examples:**
```
# Let me pick from SM scenarios
/benchmark the-expanse sm

# Let me pick from code review scenarios
/benchmark discworld reviewer

# Run specific scenario directly
/benchmark princess-bride reviewer --scenario order-service --runs 8

# Cross-role: Prospero (SM) doing dev work
/benchmark shakespeare prospero --as dev --scenario tdd-shopping-cart --runs 4
```
</usage>

<on-invoke>
The user invoked this command with: $ARGUMENTS

## Step 1: Parse Arguments

Parse the arguments to extract:
- `theme`: First positional argument (e.g., `discworld`, `the-expanse`)
- `agent_or_character`: Second positional argument (role name OR character name if `--as` is used)
- `role_override`: Value after `--as` (OPTIONAL - enables cross-role mode)
- `scenario_name`: Value after `--scenario` (OPTIONAL)
- `runs`: Value after `--runs` (default: 4, max: 20)

**Cross-Role Mode:**
If `--as <role>` is provided:
- `agent_or_character` is treated as a CHARACTER NAME (case-insensitive search)
- `role_override` becomes the `effective_role` for scenario matching
- Results save to `internal/results/benchmarks/{scenario}/{theme}-{character}-as-{role}/`

**Legacy format support:** If first argument contains `:`, split it (e.g., `discworld:reviewer` → theme=discworld, agent_or_character=reviewer)

**Validation:**
- Theme must be a valid theme name
- If `--as` is provided: validate `role_override` is one of: `sm`, `dev`, `reviewer`, `architect`, `tea`, `pm`
- If `--as` is NOT provided: validate `agent_or_character` is one of: `sm`, `dev`, `reviewer`, `architect`, `tea`, `pm`
- `--runs` must be a positive integer between 1 and 20

**Determine effective_role:**
```python
if role_override:
    effective_role = role_override  # e.g., "dev"
    cross_role = True
else:
    effective_role = agent_or_character  # e.g., "dev"
    cross_role = False
```

## Step 2: Scenario Discovery (if --scenario not provided)

If `scenario_name` is NOT provided, discover matching scenarios.

**Use `effective_role` (not `agent_or_character`) for scenario discovery.**
Cross-role mode: Prospero --as dev should see dev scenarios, not SM scenarios.

**Role-to-Category Mapping:**
| effective_role | Scenario Categories |
|----------------|---------------------|
| sm | `sm` |
| dev | `dev` (includes debug scenarios) |
| reviewer | `code-review` |
| architect | `architecture` |
| tea | `tea` |

**Time Estimates by Difficulty (parallel execution):**
| Difficulty | Est. Time (4 runs) | Note |
|------------|-------------------|------|
| easy | ~1 min | Runs execute in parallel |
| medium | ~2 min | Runs execute in parallel |
| hard | ~4 min | Runs execute in parallel |
| extreme | ~8 min | Runs execute in parallel |

**Discover scenarios:**
```bash
# Use Bash to list matching scenarios
ls scenarios/{category}/*.yaml | xargs -I {} yq -r '"{}|\(.name)|\(.difficulty)|\(.title)|\(.description)"' {}
```

**Present choices (Reflector-aware):**

First output marker: `<!-- CYCLIST:CHOICES:scenario -->`

Then use AskUserQuestion:
```yaml
AskUserQuestion:
  questions:
    - question: "Which scenario do you want to benchmark {theme}:{agent_type} on?"
      header: "Scenario"
      multiSelect: false
      options:
        - label: "{name} ({difficulty})"
          description: "{title} - ~{time_estimate}"
        # ... up to 4 options
```

If more than 4 scenarios exist, show the first 4 by difficulty (hardest first) and let user type "Other" for full list.

**After user selects:** Set `scenario_name` to the selected scenario's name and continue.

## Step 3: Control Theme Handling

**If theme is `control`:** This is a baseline creation run.
- Default `runs` to 10 (instead of 4) for statistical reliability
- Results save to `internal/results/baselines/{scenario}/{agent}/` instead of comparison
- Skip baseline validation (we're creating the baseline)
- After running, calculate and save baseline statistics
- Display baseline summary and exit

**If theme is NOT `control`:** Continue to Step 4 for comparison workflow.

## Step 4: Load and Validate Baseline

**Baseline is based on `effective_role`, not the character's native role.**
Cross-role tests compare against the effective role's baseline (e.g., prospero --as dev compares against control:dev).

Check if baseline exists:

```yaml
Read tool:
  file_path: "internal/results/baselines/{scenario_name}/{effective_role}/summary.yaml"
```

**If baseline does not exist:**
```markdown
Error: No baseline found for scenario '{scenario_name}' with agent type '{agent_type}'.

To create a baseline, run:
/benchmark control {agent_type} --scenario {scenario_name}

Or use the shortcut:
/benchmark-control {agent_type} --scenario {scenario_name}
```

**If baseline exists, VALIDATE IT:**

1. Get list of run files:
   ```yaml
   Glob tool:
     pattern: "internal/results/baselines/{scenario_name}/{agent_type}/runs/*.json"
   ```

2. Read at least one run file and validate proof-of-work:
   ```yaml
   Read tool:
     file_path: "{first run file}"
   ```

3. **Check for proof-of-work fields:**
   - Has `proof.agent_task_id`?
   - Has `proof.agent_response_text` with length >= 200?
   - Has `proof.judge_task_id`?
   - Has `proof.judge_response_text`?
   - Has `token_usage.input_tokens` > 0?
   - Has `token_usage.output_tokens` > 0?

4. **If validation fails:**
   ```markdown
   Error: Baseline for '{scenario_name}' is INVALID - missing proof-of-work.

   The baseline data appears to be fabricated (no agent/judge response text,
   no task IDs, or no token counts).

   Delete the invalid baseline and create a real one:
   rm -rf internal/results/baselines/{scenario_name}/{agent_type}
   /benchmark-control --scenario {scenario_name}
   ```

**If baseline is valid:**
- Extract `sample_size`, `statistics.total.mean`, `statistics.total.std_dev`
- Display baseline info with validation confirmation

**Sample size warning:**
If baseline sample size < 5:
```markdown
**Warning:** Baseline sample size ({n}) is less than 5. Results may not be statistically reliable.
Consider running `/benchmark-control --scenario {scenario_name} --runs 10` to add more data.
```

## Step 5: Run Contestant Evaluation (Parallel)

For efficiency, spawn multiple runs in parallel using Task agents.

**Batch Strategy:**
- If runs ≤ 4: Spawn all in parallel (single message with N Task agents)
- If runs > 4: Spawn in batches of 4 to avoid overwhelming the system

**Build the /solo command:**
```python
if cross_role:
    # Cross-role: agent_or_character is a character name
    solo_cmd = f"/solo {theme}:{agent_or_character} --as {effective_role} --scenario {scenario_name}"
else:
    # Standard: agent_or_character is the role name
    solo_cmd = f"/solo {theme}:{agent_or_character} --scenario {scenario_name}"
```

**For each run, spawn a Task agent:**
```
Task (run 1 of N):
  subagent_type: general-purpose
  prompt: |
    Run {solo_cmd}
    This is run 1 of N for baseline/benchmark.
    Return the full result JSON including score and token_usage.
```

**Example commands:**
- Standard: `/solo discworld:dev --scenario tdd-shopping-cart`
- Cross-role: `/solo shakespeare:prospero --as dev --scenario tdd-shopping-cart`

**Spawn all batch tasks in a SINGLE message for parallel execution.**

Wait for all tasks to complete. Collect results:
- Per-run scores (total, plus dimension breakdown if available)
- Per-run token usage (input_tokens, output_tokens)
- Per-run timestamps
- Cross-role metadata (source_role, effective_role, cross_role flag)

**If a run fails:** Note the failure, continue with successful runs. Warn if < 3 successful runs.

## Step 6: Calculate Comparison Statistics

**Contestant Statistics:**
- `contestant_mean`: Average total score
- `contestant_std_dev`: Standard deviation
- `contestant_n`: Number of runs

**Baseline Statistics (from summary.yaml):**
- `baseline_mean`: statistics.total.mean
- `baseline_std_dev`: statistics.total.std_dev
- `baseline_n`: sample_size

**Mean Difference:**
```
difference = contestant_mean - baseline_mean
```

**Cohen's d Effect Size:**
```
pooled_std_dev = sqrt((contestant_std_dev² + baseline_std_dev²) / 2)
cohens_d = difference / pooled_std_dev
```

**Effect Size Interpretation:**
| Cohen's d | Interpretation |
|-----------|----------------|
| < 0.2 | Negligible |
| 0.2 - 0.5 | Small |
| 0.5 - 0.8 | Medium |
| > 0.8 | Large |

**95% Confidence Interval for Difference:**
```
se_diff = sqrt(contestant_std_dev²/contestant_n + baseline_std_dev²/baseline_n)
ci_lower = difference - 1.96 × se_diff
ci_upper = difference + 1.96 × se_diff
```

**Statistical Significance:**
If CI does not include 0, the difference is statistically significant at p < 0.05.

## Step 7: Display Comparison Results

```markdown
---

## Baseline Comparison

**Contestant:** {theme}:{agent_type} ({character_name})
**Scenario:** {scenario_name}
**Baseline:** control:{agent_type} (n={baseline_n})

### Performance vs Baseline

| Metric | Contestant | Baseline | Difference | Effect Size |
|--------|------------|----------|------------|-------------|
| Total Score | {c_mean} ± {c_std} | {b_mean} ± {b_std} | {diff:+.1f} | **{cohens_d:.1f}σ** ({interpretation}) |
| Detection | {c_det} | {b_det} | {diff:+.1f} | {effect} |
| Depth | {c_dep} | {b_dep} | {diff:+.1f} | {effect} |
| Quality | {c_qual} | {b_qual} | {diff:+.1f} | {effect} |
| Persona | {c_per} | {b_per} | {diff:+.1f} | {effect} |

### Efficiency

| Metric | Contestant | Baseline |
|--------|------------|----------|
| Tokens/Point | {c_tokens_per_point} | {b_tokens_per_point} |
| Efficiency | {efficiency_pct}% of baseline | 100% |

### Statistical Significance

- **Effect Size (Cohen's d):** {cohens_d:.2f} ({interpretation})
- **95% CI for difference:** [{ci_lower:+.1f}, {ci_upper:+.1f}]
- **Significant:** {Yes/No} (p < 0.05)

### Verdict

{verdict based on effect size and significance}

---
```

**Verdict Logic:**
- If not significant: "No statistically significant difference from baseline."
- If significant and positive large effect: "Contestant **significantly outperforms** baseline with large effect size."
- If significant and positive medium effect: "Contestant **outperforms** baseline with medium effect size."
- If significant and positive small effect: "Contestant **slightly outperforms** baseline."
- If significant and negative: "Contestant **underperforms** baseline."

## Step 8: Save Results (ALWAYS)

**Output path logic:**
```python
if theme == "control":
    base_path = f"internal/results/baselines/{scenario_name}/{effective_role}/"
elif cross_role:
    # Cross-role: include character slug for clarity
    character_slug = slugify(character_name)  # e.g., "prospero", "granny-weatherwax"
    base_path = f"internal/results/benchmarks/{scenario_name}/{theme}-{character_slug}-as-{effective_role}/"
else:
    base_path = f"internal/results/benchmarks/{scenario_name}/{theme}-{effective_role}/"
```

**Cross-role examples:**
- `/benchmark shakespeare prospero --as dev` → `internal/results/benchmarks/{scenario}/shakespeare-prospero-as-dev/`
- `/benchmark discworld granny --as dev` → `internal/results/benchmarks/{scenario}/discworld-granny-weatherwax-as-dev/`

**Save structure:**
```
{base_path}/
├── runs/
│   ├── run_1.json
│   ├── judge_1.json
│   └── ...
└── summary.yaml
```

**summary.yaml format:** See `/solo` command Step 10. For cross-role runs, include:
```yaml
agent:
  theme: {theme}
  character: {character_name}
  source_role: {source_role}      # where character normally lives (e.g., sm)
  effective_role: {effective_role}  # what they're doing (e.g., dev)
  cross_role: true
```

**REQUIRED: Capture Pennyfarthing version in metadata:**
```bash
# Get version from package.json
version=$(node -p "require('./package.json').version")
```

Include in summary.yaml:
```yaml
metadata:
  created_at: "{ISO timestamp}"
  pennyfarthing_version: "{version}"  # REQUIRED for baseline staleness detection
  model: sonnet
```

**ALWAYS save summary.yaml, even for n=1.** This ensures consistent data structure for analysis.

Display:
```
✓ Saved {n} run(s) to {base_path}
✓ Summary: {base_path}/summary.yaml
```
</on-invoke>

<error-handling>
**Baseline not found:**
```markdown
Error: No baseline found for scenario '{scenario_name}' with agent type '{agent_type}'.

To create a baseline, run:
/benchmark-control --scenario {scenario_name}
```

**Invalid contestant spec:**
```markdown
Error: Invalid contestant format. Expected 'theme:agent', got '{value}'.

Examples:
- discworld:reviewer
- princess-bride:dev
- control:sm
```

**Missing --scenario:**
```markdown
Error: --scenario is required.

Usage: /benchmark <theme:agent> --scenario <name> [--runs N]
```

**Invalid runs value:**
```markdown
Error: --runs must be between 1 and 20. Got: {value}
```
</error-handling>

<reference>
- Solo Command: `.claude/project/commands/solo.md`
- Establish Baseline: `.claude/project/commands/benchmark-control.md`
- Effect Size: Cohen's d standard interpretation (0.2 small, 0.5 medium, 0.8 large)
- Baselines: `internal/results/baselines/{scenario}/{role}/` (control theme)
- Benchmarks: `internal/results/benchmarks/{scenario}/{theme}-{role}/` (all other themes)
- Results README: `internal/results/README.md`
</reference>
</output>
