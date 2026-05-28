---
name: persona-benchmark
description: Run benchmarks to compare persona effectiveness across themes. Use when testing which personas perform best on code review, test writing, or architecture tasks, or when running comparative analysis across themes.
---

# Persona Benchmark Skill

Run benchmarks to compare persona effectiveness.

<run>
/persona-benchmark <test-case-id> <persona>
/persona-benchmark <test-case-id> <persona> [--analyze] [--suite]
</run>

<output>
Benchmark results saved to `.claude/benchmarks/results/{timestamp}-{persona}-{test-case-id}.yaml` with quantitative and qualitative metrics, or analysis summary when using `--analyze`.
</output>

## Usage

```
/persona-benchmark <test-case-id> <persona>
/persona-benchmark cr-001 discworld
/persona-benchmark tw-001 literary-classics
/persona-benchmark --suite              # Run all tests, all personas
/persona-benchmark --analyze            # Analyze collected results
```

## Benchmark Execution Protocol

### Step 1: Load Test Case

Read the test case from `.claude/benchmarks/test-cases/{category}/{id}.yaml`

Extract:
- `instructions` - What to give the agent
- `code` - The code/problem to analyze
- `known_issues` or `known_edge_cases` or `known_considerations` - DO NOT reveal to agent

### Step 2: Configure Persona

Temporarily set persona in `.claude/persona-config.yaml`:
```yaml
theme: {persona}
```

### Step 3: Execute Task

Invoke the appropriate agent:
- `code-review` → `/reviewer`
- `test-writing` → `/tea`
- `architecture` → `/architect`

Provide ONLY:
- The instructions
- The code/problem

Do NOT reveal known issues list.

### Step 4: Collect Results

After agent completes, score the output:

**Quantitative Scoring:**
```yaml
# For code review:
issues_found: [list of issues detected]
issues_matched: [map to known_issues ids]
detection_rate: issues_matched / total_known_issues
false_positives: issues not in known list

# For test writing:
edge_cases_found: [list of edge cases covered]
edge_cases_matched: [map to known_edge_cases ids]
coverage_rate: edge_cases_matched / total_known_edge_cases

# For architecture:
considerations_found: [list of considerations mentioned]
considerations_matched: [map to known_considerations ids]
completeness_rate: considerations_matched / total_known_considerations
```

**Qualitative Scoring (1-5):**
- `persona_consistency`: Did the agent stay in character?
- `explanation_quality`: How well did it explain its findings?
- `actionability`: How usable is the output?
- `engagement`: How enjoyable was the interaction?

### Step 5: Save Results

Write to `.claude/benchmarks/results/{timestamp}-{persona}-{test-case-id}.yaml`:

```yaml
benchmark:
  test_case: cr-001
  persona: discworld
  agent: reviewer
  character: Granny Weatherwax
  timestamp: 2024-01-15T10:30:00Z

quantitative:
  items_found: 8
  items_expected: 14
  items_matched:
    - SQL_INJECTION_1
    - SQL_INJECTION_2
    - PLAINTEXT_PASSWORD
    - PASSWORD_EXPOSURE_1
    - PASSWORD_EXPOSURE_2
    - NO_AUTH_CHECK
    - ASYNC_DELETE_NO_TX
    - ROWS_NOT_CLOSED
  detection_rate: 0.57
  false_positives: 1
  weighted_score: 15.5
  max_weighted_score: 22.5
  weighted_rate: 0.69

qualitative:
  persona_consistency: 5
  explanation_quality: 4
  actionability: 4
  engagement: 5

notes: |
  Found both SQL injections immediately with strong language.
  Missed the error handling issues.
  Very much in character - "I aten't reviewing code that's already dead."

raw_output: |
  [Full agent output preserved here]
```

## Analysis Mode

When run with `--analyze`:

1. Load all results from `.claude/benchmarks/results/`

2. Aggregate by persona:
```
| Persona          | Detection Rate | False Pos | Persona Score | Engagement |
|------------------|----------------|-----------|---------------|------------|
| discworld        | 0.71           | 1.2       | 4.8           | 4.9        |
| star-trek        | 0.68           | 0.8       | 4.5           | 4.2        |
| literary-classics| 0.73           | 1.5       | 4.2           | 4.0        |
| minimalist       | 0.65           | 0.5       | N/A           | 3.2        |
```

3. Aggregate by test category:
```
| Category     | Best Persona      | Avg Detection |
|--------------|-------------------|---------------|
| code-review  | literary-classics | 0.71          |
| test-writing | discworld         | 0.68          |
| architecture | star-trek         | 0.75          |
```

4. Statistical significance:
- Calculate standard deviation
- Note if differences are significant

5. Qualitative patterns:
- Which personas stay in character best?
- Which provide most actionable output?
- User enjoyment patterns

## Running a Full Suite

```bash
# This will take a while - runs each test case with each persona
/persona-benchmark --suite
```

Executes:
- All test cases in `test-cases/`
- With each persona: discworld, star-trek, literary-classics, minimalist
- Saves individual results
- Produces summary comparison

## Tips for Valid Benchmarks

1. **Same evaluator**: Same person should score qualitative metrics
2. **Blind evaluation**: Score output before checking which persona
3. **Multiple runs**: Run each test 3+ times for reliability
4. **Fresh context**: Start new session for each benchmark run
5. **Control variables**: Same time of day, same evaluator state
