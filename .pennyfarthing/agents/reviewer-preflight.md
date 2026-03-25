---
name: reviewer-preflight
description: Gather mechanical data before Reviewer does critical analysis
tools: Bash, Read, Glob, Grep
model: sonnet
---

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `STORY_ID` | Yes | Story identifier, e.g., "31-10" |
| `REPOS` | Yes | Repository name(s) |
| `BRANCH` | Yes | Feature branch name |
| `PR_NUMBER` | No (optional) | Pull request number — skip PR checks if not provided |
</arguments>

<gate>
## Pre-Flight Checklist

Mechanical checks enforced by `gates/reviewer-preflight-check`: tests green (cache-aware), no debug code, error boundaries (UI only).

**Additional data gathering** (this subagent's responsibility):
- [ ] Checkout branch and get diff stats
- [ ] Get PR details via `gh pr view`
</gate>

## 1. Checkout and Diff

```bash
# If REPO is a path, cd to it; otherwise check packages/
cd "${REPO}" 2>/dev/null || cd "packages/${REPO}" && git fetch origin && git checkout {BRANCH} && git diff develop...HEAD --stat
```

## 2. Check Test Cache

```bash
source .pennyfarthing/scripts/test/test-cache.sh
SESSION_FILE=".session/{STORY_ID}-session.md"

if test_cache_valid "$SESSION_FILE"; then
    CACHED_RESULT=$(test_cache_get "$SESSION_FILE" "result")
    echo "Using cached: $CACHED_RESULT"
else
    echo "No cache, running tests"
fi
```

## 3. Run Tests (if no cache)

```yaml
Task tool:
  subagent_type: "general-purpose"
  model: "haiku"
  prompt: |
    You are the testing-runner subagent.

    Read .pennyfarthing/agents/testing-runner.md for your instructions,
    then EXECUTE all steps described there. Do NOT summarize - actually run
    the bash commands and produce the required output format.

    REPOS: {REPOS}
    CONTEXT: PR review pre-flight for Story {STORY_ID}
    RUN_ID: {STORY_ID}-review
```

## 4. Code Smells

Search changed files for:
- `console.log` (not in DEV guard)
- `dangerouslySetInnerHTML`
- `.skip(` test skips
- `TODO` / `FIXME`

## 5. PR Details

```bash
gh pr view {PR_NUMBER} --json title,body,additions,deletions,changedFiles
```

<output>
## Output Format

Return a `PREFLIGHT_RESULT` block:

### Success
```
PREFLIGHT_RESULT:
  status: success
  story_id: {STORY_ID}
  tests:
    overall: {GREEN|YELLOW|RED}
    passed: {N}
    failed: {N}
    skipped: {N}
  code_smells:
    console_log: {N}
    dangerously_set_inner_html: {N}
    test_skips: {N}
    todos: {N}
  diff:
    files: {N}
    additions: {N}
    deletions: {N}
  pr:
    number: {N}
    title: "{title}"
    url: "{url}"
  files_to_review:
    - "{path}"

  next_steps:
    - "Preflight complete. Begin critical analysis of diff."
    - "Focus review on: {files_to_review}"
    - "Code smells found: {total_smells} - investigate before approval."
```

### Blocked
```
PREFLIGHT_RESULT:
  status: blocked
  error: "{description}"
  fix: "{recommended action}"

  next_steps:
    - "Cannot proceed with review. {error}"
    - "Action required: {fix}"
```
</output>
