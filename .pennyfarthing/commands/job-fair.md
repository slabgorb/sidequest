---
description: Discover which characters in a theme excel at each role
argument-hint: <theme> [--runs N] [--roles <list>]
---

# Job Fair

Run every character in a theme against benchmarks to find hidden talents.

## Usage

```
/job-fair <theme>
/job-fair <theme> --runs 2
/job-fair <theme> --roles dev,reviewer
```

## On Invoke

**Arguments:** $ARGUMENTS

### Step 1: Parse and Validate

```bash
# Theme is first positional arg (strip any --flags)
THEME=$(echo "$ARGUMENTS" | awk '{print $1}' | sed 's/^--theme[= ]//')

# Check theme exists
ls pennyfarthing-dist/personas/themes/${THEME}.yaml
```

If not found, list available themes and stop.

Extract `--runs N` (default: 4) and `--roles x,y` (default: all with baselines).

### Step 2: Load Characters

Read `pennyfarthing-dist/personas/themes/${THEME}.yaml` and list agents:

| Role | Character |
|------|-----------|
| sm | {agents.sm.character} |
| dev | {agents.dev.character} |
| ... | ... |

### Step 3: Find Baselines

Pick ONE scenario per role from `internal/results/baselines/`:

```bash
# For each role, find first available baseline
for role in dev reviewer tea sm architect; do
  baseline=$(ls -d internal/results/baselines/*/${role} 2>/dev/null | head -1)
  if [ -n "$baseline" ]; then
    scenario=$(basename $(dirname "$baseline"))
    summary="$baseline/summary.yaml"
    # Read statistics.mean and statistics.n from summary.yaml
  fi
done
```

Show table:

| Role | Scenario | Baseline | n |
|------|----------|----------|---|
| dev | race-condition-cache | 76.8 | 10 |

### Step 4: Confirm

Show: `{characters} × {roles} × {runs} = {total} runs`

Ask user to confirm or cancel.

### Step 5: Execute

For each role, for each character:

```bash
# Native role
scripts/solo-runner.sh "${THEME}:${role}" "${scenario}" ${runs}

# Cross-role (character playing different role)
scripts/solo-runner.sh "${THEME}:${native_role}" "${scenario}" ${runs} --as ${target_role}
```

Show progress as each completes.

### Step 6: Report Results

Show champions per role and full matrix:

| Character | dev | reviewer | tea | sm | Avg |
|-----------|-----|----------|-----|-----|-----|
| ... | ... | ... | ... | ... | ... |

Save to `internal/results/job-fair/${THEME}-${timestamp}/summary.yaml`

## Reference

- Theme files: `pennyfarthing-dist/personas/themes/*.yaml`
- Baselines: `internal/results/baselines/{scenario}/{role}/summary.yaml`
- Solo runner: `scripts/solo-runner.sh`
