---
description: Create control baseline for a scenario (shortcut for /benchmark control <agent>)
argument-hint: <agent> [--scenario <name>] [--runs N]
---

# Benchmark Control

<purpose>
Shortcut to run `/benchmark` with the `control` theme. Creates or extends a control baseline for comparing other personas against.

This is equivalent to running:
```
/benchmark control <agent> [--scenario <name>] [--runs N]
```

Default: 10 runs for statistically meaningful baseline data.
</purpose>

<critical-integrity-requirements>
**See `/benchmark` for full integrity requirements.**

Baselines are saved to `internal/results/baselines/{scenario}/{agent}/` with:
- Individual runs in `runs/*.json` with proof-of-work
- Summary statistics in `summary.yaml` (mean, std_dev, CI)
- Timestamp validation (runs must take 30+ seconds each)

Control theme runs must include all proof fields. NO FABRICATION.
</critical-integrity-requirements>

<usage>
```
# Pick scenario interactively
/benchmark-control sm
/benchmark-control reviewer

# Specify scenario directly
/benchmark-control reviewer --scenario order-service
/benchmark-control dev --scenario tdd-shopping-cart --runs 15
```

**Arguments:**
- `agent` - The agent role (e.g., `sm`, `dev`, `reviewer`, `architect`)
- `--scenario` - (Optional) Scenario name. If omitted, shows matching scenarios.
- `--runs N` - Number of runs (default: 10 for baselines, max: 20)
</usage>

<on-invoke>
The user invoked this command with: $ARGUMENTS

**This is a shortcut.** Translate the arguments and invoke `/benchmark`:

1. Prepend `control` as the theme
2. Pass through all other arguments

**Examples:**
- `/benchmark-control sm` → `/benchmark control sm` (runs control:sm)
- `/benchmark-control reviewer --scenario order-service` → `/benchmark control reviewer --scenario order-service` (runs control:reviewer)
- `/benchmark-control dev --runs 15` → `/benchmark control dev --runs 15` (runs control:dev)

**Default runs override:** If `--runs` is not specified, default to 10 (instead of 4) since baselines need more data.

Now execute the equivalent `/benchmark` command with the translated arguments.
</on-invoke>

<reference>
- Main command: `.claude/project/commands/benchmark.md`
- Baselines location: `internal/results/baselines/{scenario}/{role}/`
- Results README: `internal/results/README.md`
</reference>
</output>
