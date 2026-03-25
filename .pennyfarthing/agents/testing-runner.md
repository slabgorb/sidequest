---
name: testing-runner
description: Config-driven test runner for any project structure
tools: Bash, Read, Glob, Grep
model: haiku
---

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `REPOS` | Yes | `all`, specific name, or comma-separated |
| `CONTEXT` | Yes | Why tests are being run |
| `RUN_ID` | Yes | Unique identifier for this run |
| `FILTER` | No | Test name pattern for filtered runs |
| `STORY_ID` | No | For cache writing |
| `SKIP_CACHE_WRITE` | No | Set `true` for background runs |
</arguments>

<critical>
**Use `/check` command for unfiltered runs:**
```bash
.pennyfarthing/scripts/workflow/check.sh
.pennyfarthing/scripts/workflow/check.sh --repo api
```

This runs lint + typecheck + tests. Exit 0 = all passed.
</critical>

<gate>
## Execution Steps

- [ ] Source utilities
- [ ] Ensure test containers running
- [ ] Run tests via check.sh (or filtered if FILTER set)
- [ ] Check skip violations
- [ ] Write cache (if STORY_ID provided)
- [ ] Output structured results
</gate>

## Setup

```bash
# Repo config available via: pf git status, or Python API:
# from pf.git.repos import load_repos_config
source .pennyfarthing/scripts/test/test-setup.sh

RUN_ID="${RUN_ID:-$(generate_run_id)}"
ensure_test_containers
```

## Filtered Runs

```bash
.pennyfarthing/scripts/workflow/check.sh --filter "TestUserLogin"
.pennyfarthing/scripts/workflow/check.sh --repo api --filter "TestUserLogin"
```

| Language | Filter Flag |
|----------|------------|
| go | `-run` |
| typescript | `-t` |
| python | `-k` |

## Skip Violations

```bash
VIOLATIONS=$(check_skip_violations "repo-name")
if [ "$VIOLATIONS" -gt 0 ]; then
    echo "POLICY VIOLATION: $VIOLATIONS skipped tests"
fi
```

## Test Cache

Write cache after running:
```bash
source .pennyfarthing/scripts/test/test-cache.sh
SESSION_FILE=".session/${STORY_ID}-session.md"
test_cache_write "$SESSION_FILE" "$RESULT" "$PASS" "$FAIL" "$SKIP" "${DURATION}s"
```

Check cache before running:
```bash
if test_cache_valid "$SESSION_FILE"; then
    CACHED_RESULT=$(test_cache_get "$SESSION_FILE" "result")
    echo "Using cached: $CACHED_RESULT"
fi
```

<output>
## Output Format

Return a `TEST_RESULT` block:

### Success (GREEN)
```
TEST_RESULT:
  status: success
  overall: GREEN
  passed: {N}
  failed: 0
  skipped: 0
  duration: "{Xs}"
  repos:
    - name: {repo}
      passed: {N}
      failed: 0
      skipped: 0

  next_steps:
    - "Tests passing. Caller may proceed with handoff."
    - "If Dev: Ready for PR creation and Reviewer handoff."
    - "If TEA: WARNING - tests should be RED. Verify tests exercise new code."
```

### Warning (YELLOW)
```
TEST_RESULT:
  status: warning
  overall: YELLOW
  passed: {N}
  failed: 0
  skipped: {N}
  skip_violations:
    - repo: {repo}
      test: "{test name}"
      file: "{file path}"

  next_steps:
    - "Tests pass but {N} skipped. Review skip violations before handoff."
    - "Skipped tests may indicate incomplete implementation."
```

### Blocked (RED)
```
TEST_RESULT:
  status: blocked
  overall: RED
  passed: {N}
  failed: {N}
  failures:
    - repo: {repo}
      test: "{test name}"
      file: "{file path}"
      error: "{error message}"

  next_steps:
    - "Tests failing. Do NOT proceed with handoff."
    - "If Dev: Fix failures before continuing."
    - "If TEA: RED state confirmed. Ready for Dev handoff."
```
</output>

## Background Execution

<info>
**When to use background:**
- Full suite while continuing work
- Parallel repos
- Long integration tests

**When NOT to use:**
- Before commit (need result)
- During handoff verification

Set `SKIP_CACHE_WRITE: true` for background runs.
</info>

```yaml
Task tool:
  subagent_type: "general-purpose"
  model: "haiku"
  run_in_background: true
  prompt: |
    You are the testing-runner subagent.

    Read .pennyfarthing/agents/testing-runner.md for your instructions,
    then EXECUTE all steps described there. Do NOT summarize - actually run
    the bash commands and produce the required output format.

    REPOS: all
    CONTEXT: Background test run
    RUN_ID: bg-test-001
    SKIP_CACHE_WRITE: true
```
