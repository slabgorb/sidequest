# Brownfield & Code Analysis Tools

<info>
CLI tools for analyzing existing codebases. Identify change hotspots, complexity bottlenecks, dead code, stale dependencies, and code markers (TODO/FIXME). Each tool produces table, JSON, or CSV output and has a corresponding Frame API route for panel integration.
</info>

## Overview

All tools are available under `pf debug` and share a consistent interface: `--format` (table/json/csv), `--output` (file), `--top` (result count), `--exclude` (patterns), and `--repo` (target).

## Tools

### Hotspots

Find files that change most frequently — high churn often correlates with bugs and complexity.

```bash
# Full analysis (files + directories)
pf debug hotspots analyze

# File-level only
pf debug hotspots files

# Directory-level only
pf debug hotspots dirs

# Options
pf debug hotspots analyze --days 90 --top 20 --repo pennyfarthing
pf debug hotspots analyze --format json --output hotspots.json
pf debug hotspots analyze --exclude "*.test.ts" --branch main
pf debug hotspots analyze --skip-type orchestrator
```

### Complexity

Measure code complexity metrics across files.

```bash
pf debug complexity analyze
pf debug complexity analyze --path ./packages/core/src
pf debug complexity analyze --top 30 --format csv
```

### Dead Code

Find unused code: stale files with no recent commits, and unused TypeScript exports.

```bash
# Files with no recent commits (default: 180 days)
pf debug deadcode stale
pf debug deadcode stale --days 90 --repo pennyfarthing

# Unused TypeScript exports (via ts-prune)
pf debug deadcode exports
pf debug deadcode exports --repo pennyfarthing --format json
```

### Code Markers

Detect TODO, FIXME, HACK, and XXX comments with git blame data.

```bash
# Full analysis with blame data
pf debug codemarkers analyze

# Only stale markers (older than threshold)
pf debug codemarkers stale --days 90

# Summary counts by type
pf debug codemarkers summary

# Deprecated symbol detection
pf debug codemarkers deprecations
```

### Dependencies

Analyze dependency staleness and security advisories.

```bash
pf debug dependencies analyze
pf debug dependencies analyze --path ./pennyfarthing --format json
```

### Health Score

Composite health score across all dimensions (hotspots, complexity, dead code, dependencies, markers).

```bash
pf debug healthscore analyze
pf debug healthscore analyze --no-cache   # Bypass cache
pf debug healthscore analyze --format json --output health.json
```

## Common Options

| Option | Description | Default |
|--------|-------------|---------|
| `--repo NAME` | Analyze a single named repo from `repos.yaml` | All repos |
| `--path DIR` | Analyze a standalone directory | Current directory |
| `--format FMT` | Output format: `table`, `json`, `csv` | `table` |
| `--output FILE` | Write output to file | stdout |
| `--top N` | Number of top results | 20 |
| `--exclude PAT` | Exclude patterns (repeatable) | — |
| `--days N` | Time window for analysis | Varies by tool |

## Frame API Routes

Each tool has a corresponding HTTP API in Frame for panel integration:

| Route | Tool |
|-------|------|
| `/api/hotspots` | Hotspot analysis |
| `/api/complexity` | Complexity metrics |
| `/api/dead-code` | Dead code detection |
| `/api/dependencies` | Dependency health |
| `/api/code-markers` | Code marker scan |
| `/api/health-score` | Composite health score |

These power the **HotspotsPanel** in Frame.

## Key Files

| Directory | Purpose |
|-----------|---------|
| `pf/hotspots/` | Hotspot analysis (analyze, formatters, models) |
| `pf/complexity/` | Complexity analysis |
| `pf/deadcode/` | Dead code detection |
| `pf/dependencies/` | Dependency analysis |
| `pf/codemarkers/` | Code marker detection |
| `pf/healthscore/` | Composite health score |
| `pf/brownfield/` | Brownfield codebase discovery |
| `packages/core/src/server/api/` | Frame API routes |
