---
description: Run a single agent on a scenario with absolute rubric scoring
argument-hint: <theme:agent> --scenario <name> [--as <role>] [--runs N] [--no-judge]
---

# Solo Benchmark

<purpose>
Run a single agent on a scenario. This is the CANONICAL agent execution path.

**Modes:**
- **Full (default):** Agent runs → `/judge` evaluates → `/finalize-run` saves
- **No-judge (`--no-judge`):** Agent runs only, returns raw response (for /duel, /relay)
</purpose>

<architecture>
```
/solo theme:agent --scenario X
    │
    ├──► Execute agent via CLI
    │         └──► Response + tokens
    │
    ├──► /judge --mode solo (if not --no-judge)
    │         └──► Score + verdict
    │
    └──► /finalize-run --type solo
              └──► Validate + save
```
</architecture>

<usage>
```
/solo <contestant> --scenario <name>
/solo <contestant> --scenario <name> --runs 4
/solo <contestant> --scenario <name> --no-judge
/solo <contestant> --as <role> --scenario <name>
```

**Arguments:**
- `contestant` - `theme:agent` format (e.g., `discworld:reviewer`) OR `theme:character` with `--as`
- `--scenario` - Scenario from `scenarios/` directory
- `--as <role>` - Override role (use character's persona for different role's task)
- `--runs N` - Number of runs (default: 1, max: 20)
- `--no-judge` - Skip judging, return raw response

**Cross-Role Testing with `--as`:**

The `--as` flag enables running any persona as any role, useful for research:

```
/solo shakespeare:prospero --as dev --scenario django-10554
```

This uses Prospero's persona traits (wise orchestrator, magic metaphors) but gives him a dev task.
The scenario's role determines what the agent is asked to do; the character determines how they do it.
</usage>

<on-invoke>
The user invoked this command with: $ARGUMENTS

## Step 1: Parse Arguments

Extract:
- `contestant`: `theme:agent` spec (or `theme:character` if using `--as`)
- `scenario_name`: After `--scenario`
- `role_override`: After `--as` (optional - for cross-role testing)
- `runs`: Number (default: 1)
- `no_judge`: Boolean

Validate spec contains `:`, scenario is required, runs is 1-20.

**If `--as` is provided:**
- The second part of the spec is a CHARACTER name, not a role
- `role_override` becomes the effective role for scenario matching
- Character persona is extracted by name lookup across all agents in theme

## Step 2: Load Scenario

```yaml
Glob tool:
  pattern: "scenarios/**/{scenario_name}.yaml"
```

Extract: `prompt`, `scenario_title`, `code_content` (if present)

## Step 3: Load Persona

Read: `pennyfarthing-dist/personas/themes/{theme}.yaml`

**Standard mode (no `--as`):**
- Look up `agents.{agent}` section
- Extract: `character`, `style`, `expertise`, `catchphrases`, `emoji`
- `effective_role` = agent name from spec

**Cross-role mode (with `--as`):**
- The spec contains `theme:character_name` (e.g., `shakespeare:prospero`)
- Search ALL agent sections for one where `character` field matches (case-insensitive, partial match OK)
- Extract persona traits from that agent's config
- `effective_role` = the `--as` value (NOT the role the character normally fills)

```python
# Pseudocode for cross-role lookup
if role_override:
    character_query = spec.split(':')[1].lower()  # e.g., "prospero"
    for agent_name, agent_config in theme['agents'].items():
        char_name = agent_config.get('character', '').lower()
        if character_query in char_name or char_name.startswith(character_query):
            persona = agent_config
            source_role = agent_name  # where character normally lives
            break
    effective_role = role_override  # what we're asking them to do
else:
    agent_name = spec.split(':')[1]  # e.g., "dev"
    persona = theme['agents'][agent_name]
    effective_role = agent_name
    source_role = agent_name
```

This enables running Prospero (normally SM) as a dev, or Gus Fring (normally orchestrator) as a reviewer.

## Step 3b: Build Agent Prompt

Use the Write tool to create the prompt file with this template:

```
You are {character}.

**Style:** {style}
**Expertise:** {expertise}
**Catchphrases:** {catchphrases}

---

## Challenge

{scenario_prompt}

{code_content if present}

---

Respond fully in character. Under 500 words.

**IMPORTANT:** Provide your complete response directly. Do not attempt to use tools, read files, or make function calls.
```

**Cross-role note:** When using `--as`, the scenario prompt comes from the `effective_role` (e.g., dev tasks),
but the character/style/expertise come from the character's original role config. This tests whether
personality traits affect task performance independent of role-specific training.

The final instruction is critical - without it, the model may output tool-call syntax even with `--tools ""`, resulting in incomplete responses.

## Step 4: Execute Agent via CLI

**RECOMMENDED: Use the shell script for reliable execution:**

```bash
./scripts/solo-runner.sh {theme}:{agent} {scenario} {output_dir}
```

The shell script handles all escaping, temp files, and JSON parsing correctly.
Use inline commands only for simple cases or when the script isn't available.

---

**CRITICAL: The `--tools ""` flag is MANDATORY.**

Without `--tools ""`, agents may use tools internally (Read, Write, Bash, etc.), causing:
1. Multi-turn conversations (num_turns > 1)
2. The `.result` field only captures the FINAL message (often just a summary)
3. Full response content is LOST - judges only see truncated output
4. Scores are INVALID because judges evaluate incomplete data

**Evidence:** Miles Vorkosigan benchmark (2026-01-01) scored 76.69 with tools enabled vs Leo McGarry's 91.03 with `--tools ""`. Miles' runs had num_turns: 5-7 and judges only saw summaries, not full story breakdowns.

**CRITICAL: Use PIPE syntax, NOT heredocs.**

**NEVER USE HEREDOCS** - Heredoc syntax (`<<'EOF'`, `<<EOF`, `<<'PROMPT'`, etc.) FAILS in subagents.
The permission system treats heredocs differently and they get auto-denied.

**ALWAYS USE PIPE SYNTAX** - This works in both main sessions and subagents:
- `echo "$PROMPT" | claude -p ...` - WORKS
- `cat file.txt | claude -p ...` - WORKS
- `printf '%s' "$PROMPT" | claude -p ...` - WORKS
- `claude -p ... <<'EOF'` - **FAILS IN SUBAGENTS - DO NOT USE**

**CRITICAL: Use FILE REDIRECTION, NOT variable capture.**

**NEVER CAPTURE OUTPUT IN VARIABLES** - Command substitution with `$(...)` causes zsh parse errors
when the JSON output contains parentheses or special characters:
- `OUTPUT=$(cat file.txt | claude -p ...)` - **FAILS with `parse error near ')'`**

**ALWAYS REDIRECT TO FILES** - This avoids shell parsing issues:
- `cat file.txt | claude -p ... > output.json` - WORKS
- Then read: `jq -r '.result' output.json` - WORKS

```bash
# Step 1: Capture timestamp to file (avoid variable capture issues)
date -u +%Y-%m-%dT%H:%M:%SZ > /tmp/timestamp_$$.txt

# Step 2: Write prompt to file using Write tool (avoids escaping issues)
# Use the Write tool to create: /tmp/prompt_$$.txt

# Step 3: Execute with file redirection (NOT variable capture)
cat /tmp/prompt_$$.txt | claude -p --output-format json --tools "" > /tmp/output_$$.json

# Step 4: Extract results from files
TIMESTAMP=$(cat /tmp/timestamp_$$.txt)
RESPONSE=$(jq -r '.result' /tmp/output_$$.json)
INPUT_TOKENS=$(jq -r '.usage.input_tokens // 0' /tmp/output_$$.json)
OUTPUT_TOKENS=$(jq -r '.usage.output_tokens // 0' /tmp/output_$$.json)

# Step 5: Cleanup
rm -f /tmp/timestamp_$$.txt /tmp/prompt_$$.txt /tmp/output_$$.json
```

**Why file redirection works:** The shell never tries to parse the JSON output.
It goes directly to a file, then jq reads it safely.

## Step 5: Check Mode

**If `--no-judge`:** Return raw response and metadata, STOP.

```markdown
## Solo Agent Response

**Contestant:** {spec} ({character})
**Scenario:** {scenario_name}

---

{response}

---

```json
{
  "spec": "{spec}",
  "character": "{character}",
  "cli_timestamp": "{TIMESTAMP}",
  "response_length": {length},
  "input_tokens": {INPUT_TOKENS},
  "output_tokens": {OUTPUT_TOKENS}
}
```
```

**If full mode:** Continue to Step 6.

## Step 6: Invoke Judge Skill

**Detect SWE-bench scenarios for deterministic evaluation:**

Check if the scenario is from SWE-bench by looking at its path or category:
```python
is_swebench = (
    'swe-bench' in scenario_path.lower() or
    scenario.get('category') == 'swe-bench' or
    scenario.get('source') == 'swe-bench'
)
```

**If SWE-bench scenario:**

Use deterministic Python-based evaluation instead of LLM-as-judge:

```bash
# Save response to temp file for Python judge
echo '{"result": "{RESPONSE}"}' > /tmp/solo_response_$$.json

# Run SWE-bench judge (deterministic scoring against ground truth)
python3 .pennyfarthing/scripts/test/swebench-judge.py {scenario_name} /tmp/solo_response_$$.json
```

The Python script returns:
- `total`: Score out of 100
- `scores`: Breakdown by category (root_cause, fix_quality, completeness, persona)
- `details`: Specific findings and matches

**If standard scenario (non-SWE-bench):**

Use LLM-as-judge:
```
/judge --mode solo --data {
  "spec": "{spec}",
  "character": "{character}",
  "challenge": "{prompt}",
  "response": "{RESPONSE}"
}
```

Capture: `score`, `judge_timestamp`, `judge_response`, `judge_tokens`

## Step 7: Invoke Finalize-Run Skill

```
/finalize-run --type solo --data {
  "timestamp": "{ISO8601}",
  "scenario": {"name": "{scenario_name}", "title": "{title}"},
  "agents": [{
    "spec": "{spec}",
    "cli_timestamp": "{TIMESTAMP}",
    "response_text": "{RESPONSE}",
    "input_tokens": {INPUT_TOKENS},
    "output_tokens": {OUTPUT_TOKENS}
  }],
  "judge": {
    "cli_timestamp": "{judge_timestamp}",
    "response_text": "{judge_response}",
    "input_tokens": {judge_input},
    "output_tokens": {judge_output}
  },
  "scores": {"{spec}": {score}},
  "output_path": "internal/results/solo/{timestamp}-{theme}-{agent}.json"
}
```

## Step 8: Display Results

```markdown
## Solo Evaluation

{judge verdict}

---

## Efficiency

| Metric | Value |
|--------|-------|
| Agent Tokens | {agent_total} |
| Judge Tokens | {judge_total} |
| Score | {score}/100 |
| Tokens/Point | {tpp} |

---

✓ Saved to {output_path}
```

## Step 9: Multi-Run Mode (if runs > 1)

1. Create output directory (see Step 10 for path logic)
2. Repeat Steps 4-7 for each run
3. Save each to `runs/run_{i}.json` and `runs/judge_{i}.json`
4. Calculate statistics and save summary.yaml (Step 10)

## Step 10: Save Summary (ALWAYS - even for n=1)

**Output path logic:**

```
if theme == "control":
  base_path = "internal/results/baselines/{scenario}/{effective_role}/"
elif role_override:  # cross-role mode
  # Include character name and effective role for clarity
  base_path = "internal/results/benchmarks/{scenario}/{theme}-{character}-as-{effective_role}/"
else:
  base_path = "internal/results/benchmarks/{scenario}/{theme}-{effective_role}/"
```

**Cross-role example:** `/solo shakespeare:prospero --as dev --scenario django-10554`
→ saves to `internal/results/benchmarks/django-10554/shakespeare-prospero-as-dev/`

**For ALL runs (including n=1):**

1. Create directory structure:
   ```bash
   mkdir -p "{base_path}/runs"
   ```

2. Save run files:
   - `runs/run_{i}.json` - Agent response + tokens
   - `runs/judge_{i}.json` - Judge evaluation

3. Calculate statistics:
   ```python
   scores = [run.score for run in runs]
   mean = sum(scores) / len(scores)
   std_dev = sqrt(sum((s - mean)^2 for s in scores) / len(scores))
   ```

4. **ALWAYS save summary.yaml:**
   ```yaml
   # {theme}:{character} on {scenario} (as {effective_role})
   # Generated: {ISO8601 timestamp}

   agent:
     theme: {theme}
     character: {character_name}
     effective_role: {effective_role}      # role being performed
     source_role: {source_role}            # role where character normally lives
     spec: {theme}:{character}             # original spec
     cross_role: {true if role_override else false}

   scenario:
     name: {scenario_name}
     category: {category}
     difficulty: {difficulty}

   statistics:
     n: {run_count}
     mean: {mean:.2f}
     std_dev: {std_dev:.2f}
     min: {min_score}
     max: {max_score}
     scores: [{score1}, {score2}, ...]

   efficiency:
     avg_input_tokens: {avg_in}
     avg_output_tokens: {avg_out}
     tokens_per_point: {tpp:.2f}

   metadata:
     created_at: {ISO8601 timestamp}
     pennyfarthing_version: {version from package.json}  # REQUIRED
     model: sonnet

   # Include baseline comparison if baseline exists and theme != control
   baseline_comparison:
     control_mean: {baseline_mean}
     control_stddev: {baseline_std}
     delta: {mean - baseline_mean:+.2f}

   runs:
     - run_1.json
     - run_2.json
     # ...
   ```

5. Display:
   ```
   ✓ Saved {n} run(s) to {base_path}
   ✓ Summary: {base_path}/summary.yaml
   ```

</on-invoke>

<reference>
- **Judge Skill:** `.claude/project/skills/judge/SKILL.md`
- **Finalize-Run Skill:** `.claude/project/skills/finalize-run/SKILL.md`
- **Themes:** `pennyfarthing-dist/personas/themes/*.yaml`
- **Scenarios:** `scenarios/**/*.yaml`
- **Baselines:** `internal/results/baselines/{scenario}/{role}/` (control theme)
- **Benchmarks:** `internal/results/benchmarks/{scenario}/{theme}-{role}/` (all other themes)
- **Results README:** `internal/results/README.md`
</reference>
