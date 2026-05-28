---
name: context-engineering
description: Strategies for managing context windows in long-running agent sessions. Use when approaching context limits, designing subagent prompts, optimizing token usage, or implementing just-in-time context loading.
allowed_tools: [Read, Glob, Grep, Task]
---

# Context Engineering Skill

<run>context-engineering</run>
<output>strategies for managing context windows in long-running agent sessions</output>

**Purpose:** Strategies for managing context windows efficiently in long-running agent sessions.

**Use when:** Working on complex tasks, approaching context limits, designing subagent prompts.

**Source:** [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## Core Principle

> Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome.

Don't pre-load everything. Store lightweight identifiers (paths, URLs, queries) and load just-in-time.

---

## Just-in-Time Context Loading

### The Pattern

```
WRONG: Read all 50 test files upfront to understand patterns
RIGHT: Store test file paths, read specific ones when implementing

WRONG: Load entire codebase structure at session start
RIGHT: Load CLAUDE.md + current task context, explore as needed
```

### Implementation

1. **Store references, not content:**
   ```
   - Test patterns: See .claude/skills/testing/SKILL.md
   - API handlers: internal/handlers/ (or use repos.yaml for multi-repo)
   - UI components: src/components/
   ```

2. **Load on demand:**
   ```
   "I need to implement a handler. Let me read one existing handler first..."
   [reads one file, not all handlers]
   ```

3. **Summarize, don't quote:**
   ```
   GOOD: "The auth middleware checks JWT tokens in the Authorization header"
   BAD: [pastes entire middleware.go into context]
   ```

---

## Context Editing

### Clearing Stale Results

Tool results become stale over time. In long sessions:

1. **Identify stale context:** Results from early in session no longer relevant
2. **Summarize findings:** "Earlier I found X, Y, Z"
3. **Clear mental model:** Focus on current task state

### When to Reset

Consider resetting context when:
- You've been working for 20+ tool calls
- Earlier findings are no longer relevant
- You're going in circles
- The task has shifted significantly

### Reset Pattern

```
"Let me summarize progress:
- Completed: A, B, C
- Current state: D
- Remaining: E, F

Starting fresh from current state..."
```

---

## Subagent Patterns

### The Golden Rule

> Subagents return SUMMARIES, not full context.

### Spawning Subagents

When to spawn:
- Task requires sifting through large amounts of data
- Parallel exploration needed
- Isolated context window beneficial

How to spawn:
```
Task tool:
  subagent_type: "Explore" or "general-purpose"
  model: "haiku"  # For mechanical tasks
  prompt: "Find X, summarize what you find. Don't paste entire files."
```

### Receiving Subagent Results

What you get back:
- Summary of findings
- Key file paths (not file contents)
- Specific answers to questions asked

What you DON'T get:
- Full tool call history
- All files the subagent read
- Raw grep/glob results

---

## Memory Tools

### Cross-Session State

For long-running work, use external files:

1. **Session file:** `.session/{STORY_ID}-session.md`
   - Current story context
   - Progress notes
   - Handoff state

2. **Progress log:** Project-specific tracking
   - What was done
   - What remains
   - Blockers encountered

3. **Sidecar files:** `.pennyfarthing/agents/{agent}-sidecar/`
   - Patterns learned
   - Common fixes
   - Accumulated knowledge

### Writing to Memory

When you learn something reusable:
```
"This pattern worked well. Let me add it to the sidecar..."
[Edit sidecar file with new pattern]
```

When completing work:
```
"Session complete. Updating session file with final state..."
[Update .session/{STORY_ID}-session.md]
```

---

## CLAUDE.md Best Practices

### Keep It Minimal

CLAUDE.md should contain ONLY:
- Project conventions (naming, structure)
- Key commands (test, build, deploy)
- Directory layout
- Architecture notes
- Core app features

### What NOT to Include

- Full API documentation
- Complete code examples
- Every edge case
- Historical decisions

### Reference, Don't Duplicate

```
GOOD:
  "Test patterns: See .claude/skills/testing/SKILL.md"

BAD:
  "Here's how to test:
   [300 lines of testing documentation]"
```

---

## Context Budget

### Typical Limits

| Content Type | Target Lines |
|-------------|--------------|
| Agent file | 200-400 |
| Session file | 50-100 |
| Skill file | 100-200 |
| Repo context | 30-50 |
| **Total per activation** | **500-800** |

### Staying Under Budget

1. **Load incrementally:** Start minimal, add as needed
2. **Summarize findings:** Don't keep raw results
3. **Use subagents:** Offload data-heavy exploration
4. **Reference, don't embed:** Point to files instead of pasting

---

## Signs You're Using Context Poorly

| Symptom | Problem | Solution |
|---------|---------|----------|
| Reading same file multiple times | Not retaining key info | Summarize on first read |
| Pasting entire files in responses | Over-sharing | Quote only relevant sections |
| Long tool result chains | Not filtering | Request focused results |
| Subagent returns everything | Bad prompt | Ask for summary, not raw data |
| "I forgot what we were doing" | Context overflow | Reset with progress summary |

---

## Templates

### Subagent Exploration Prompt

```
Explore the codebase to find [SPECIFIC THING].

Return:
1. File paths where you found it (not file contents)
2. Brief description of what each file does
3. The most relevant 5-10 lines (not entire file)

Do NOT paste entire files or long grep results.
```

### Progress Summary Template

```
## Progress Summary

**Completed:**
- [x] Task A - [brief result]
- [x] Task B - [brief result]

**Current State:**
- Working on: [current task]
- Blockers: [any blockers]

**Remaining:**
- [ ] Task C
- [ ] Task D

**Key Findings:**
- [Important thing 1]
- [Important thing 2]
```

---

## Key Insight

Context is precious. Every token you waste on stale information is a token you can't use for solving the actual problem.

**Ask yourself:**
- Do I need to load this file, or just know it exists?
- Can I summarize this finding instead of quoting it?
- Would a subagent handle this better?
- Is this context still relevant?
