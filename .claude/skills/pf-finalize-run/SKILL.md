---
name: finalize-run
description: Validate and save benchmark run results. Use when completing a benchmark run, validating results before storage, or ensuring all runs pass through the single guardrail exit point.
---

# Finalize Run Skill

<run>Validates and saves benchmark run results</run>
<output>JSON with validation success status and saved file path</output>

All runs MUST pass through this skill before saving. This is the guardrail.

## Invocation

```
/finalize-run --type <type> --data <json>
```

**Types:**
- `solo` - Single agent evaluation
- `duel` - Two-agent comparison
- `relay` - Team relay competition

## Validation Rules

### Agent Validation

For EACH agent in the run:

| Field | Rule | Action on Fail |
|-------|------|----------------|
| `cli_timestamp` | Valid ISO8601 | REJECT |
| `response_text` | ≥ 200 characters | REJECT |
| `input_tokens` | > 0 | REJECT |
| `output_tokens` | > 0 | REJECT |

### Judge Validation

| Field | Rule | Action on Fail |
|-------|------|----------------|
| `cli_timestamp` | Valid ISO8601 | REJECT |
| `response_text` | Contains "WEIGHTED_TOTAL" or "RATING:" | REJECT |
| `response_text` | ≥ 100 characters | REJECT |

### Score Validation

| Field | Rule | Action on Fail |
|-------|------|----------------|
| `total` | Number 1-100 | REJECT |
| Extracted from judge | Matches claimed score | REJECT |

### Timestamp Sanity

```
elapsed = last_timestamp - first_timestamp
minimum = 30 × number_of_agents

if elapsed < minimum:
  WARN: "Timestamps suspiciously close"
```

## On Invoke

### Step 1: Parse Input

Extract:
- `type`: solo, duel, or relay
- `data`: JSON with run data

**Required data structure:**

```json
{
  "type": "solo|duel|relay",
  "timestamp": "ISO8601",
  "scenario": {"name": "...", "title": "..."},
  "agents": [
    {
      "spec": "theme:agent",
      "cli_timestamp": "ISO8601",
      "response_text": "full response",
      "input_tokens": 1234,
      "output_tokens": 5678
    }
  ],
  "judge": {
    "cli_timestamp": "ISO8601",
    "response_text": "full verdict",
    "input_tokens": 2345,
    "output_tokens": 890
  },
  "scores": {"spec": score},
  "output_path": "results/..."
}
```

### Step 2: Validate Agents

For each agent:

```bash
# Check timestamp format
if ! [[ "$cli_timestamp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T ]]; then
  REJECT "Invalid timestamp: $cli_timestamp"
fi

# Check response length
response_len=${#response_text}
if [[ $response_len -lt 200 ]]; then
  REJECT "Response too short: $response_len chars (min 200)"
fi

# Check tokens
if [[ $input_tokens -le 0 ]] || [[ $output_tokens -le 0 ]]; then
  REJECT "Invalid tokens: in=$input_tokens out=$output_tokens"
fi
```

### Step 3: Validate Judge

```bash
# Check for score marker
if ! echo "$judge_response" | grep -qE "WEIGHTED_TOTAL|RATING:"; then
  REJECT "Judge response missing score marker"
fi

# Check response length
if [[ ${#judge_response} -lt 100 ]]; then
  REJECT "Judge response too short"
fi

# Check tokens
if [[ $judge_input_tokens -le 0 ]] || [[ $judge_output_tokens -le 0 ]]; then
  REJECT "Invalid judge tokens"
fi
```

### Step 4: Validate Scores

```bash
# Extract score from judge
extracted=$(echo "$judge_response" | grep -oE "WEIGHTED_TOTAL[^0-9]*([0-9]+)" | grep -oE "[0-9]+" | tail -1)

# Verify against claimed score
if [[ "$extracted" != "$claimed_score" ]]; then
  REJECT "Score mismatch: claimed=$claimed_score extracted=$extracted"
fi

# Check range
if [[ $extracted -lt 1 ]] || [[ $extracted -gt 100 ]]; then
  REJECT "Score out of range: $extracted"
fi
```

### Step 5: Timestamp Sanity Check

```bash
# Calculate elapsed time
first_ts=$(date -d "$first_agent_timestamp" +%s)
last_ts=$(date -d "$judge_timestamp" +%s)
elapsed=$((last_ts - first_ts))

# Check minimum expected time
num_agents=${#agents[@]}
minimum=$((30 * num_agents))

if [[ $elapsed -lt $minimum ]]; then
  WARN "Elapsed time ${elapsed}s < expected ${minimum}s"
fi
```

### Step 6: Display Validation Report

```markdown
### Finalize Run Validation

**Type:** {type}
**Scenario:** {scenario.name}

#### Agent Validation
| Agent | Timestamp | Response | Tokens | Status |
|-------|-----------|----------|--------|--------|
| {spec} | {ts} | {len} chars | in={in} out={out} | ✓ |

#### Judge Validation
| Field | Value | Status |
|-------|-------|--------|
| Timestamp | {ts} | ✓ |
| Response | {len} chars | ✓ |
| Score | {score}/100 | ✓ |

#### Timestamp Sanity
- Elapsed: {elapsed}s
- Expected: ≥{minimum}s
- Status: ✓ PASS

---
**VALIDATION: PASSED**
```

### Step 7: Save Results

If ALL validations pass:

```bash
# Ensure directory exists
mkdir -p "$(dirname "$output_path")"

# Write result
echo "$result_json" > "$output_path"
```

Display:
```
✓ Saved to {output_path}
```

### Step 8: Return Success

```json
{
  "success": true,
  "path": "{output_path}",
  "validation": {
    "agents_validated": {count},
    "judge_validated": true,
    "scores_verified": true,
    "timestamp_sane": true
  }
}
```

## On Validation Failure

```markdown
### ❌ VALIDATION FAILED

**Failed Check:** {which validation}
**Reason:** {specific reason}
**Value:** {what was provided}

**This run will NOT be saved.**

To fix:
- {remediation steps}
```

Return:
```json
{
  "success": false,
  "error": "{reason}",
  "failed_check": "{which}"
}
```

## The Golden Rule

**Real data or no data.**

Never estimate. Never fabricate. If validation fails, the run did not happen.
