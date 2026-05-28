---
name: agentic-patterns
description: Core reasoning patterns for building effective LLM agents. Use when designing agent behavior, debugging agent failures, improving agent reliability, or understanding ReAct/Plan-and-Execute patterns.
allowed_tools: [Read, Glob, Grep, Task]
---

# Agentic Patterns Skill

<run>When designing agent behavior, debugging agent failures, improving agent reliability.</run>

<output>Core reasoning patterns for building effective LLM agents. Includes ReAct, Plan-and-Execute, Self-Reflection, confidence calibration, error recovery, multi-agent coordination, and context management strategies.</output>

**Purpose:** Core reasoning patterns for building effective LLM agents.

**Use when:** Designing agent behavior, debugging agent failures, improving agent reliability.

---

## Core Reasoning Patterns

### 1. ReAct (Reasoning and Acting)

The foundational agentic loop. Combines chain-of-thought with tool use.

```
THOUGHT: What am I trying to accomplish? What do I know?
ACTION: Execute tool/command based on reasoning
OBSERVATION: What was the result? Did it match expectations?
THOUGHT: Based on observation, what next?
... repeat until goal achieved
```

**Why it works:** Grounds LLM outputs in real observations. Reduces hallucinations.

**When to use:** Most tasks. This is the default pattern.

**Example:**
```
THOUGHT: I need to find where authentication is handled
ACTION: grep -r "authenticate" --include="*.go"
OBSERVATION: Found 3 files: auth.go, middleware.go, handlers.go
THOUGHT: middleware.go likely has the auth middleware, let me read it
```

### 2. Plan-and-Execute

Decompose complex goals into sub-tasks before acting.

```
1. PLAN: Break goal into discrete steps
2. EXECUTE: Work through each step
3. VERIFY: Check each step succeeded before moving on
4. ADJUST: Replan if something fails
```

**Why it works:** Prevents getting lost in complex tasks. Makes progress visible.

**When to use:** Multi-step tasks, unfamiliar codebases, architectural changes.

**Example:**
```
PLAN for "Add user authentication":
1. Check existing auth patterns in codebase
2. Design auth middleware
3. Implement token validation
4. Add protected routes
5. Write tests
6. Update documentation

Now executing step 1...
```

### 3. Self-Reflection

Evaluate own outputs before presenting them.

```
1. GENERATE: Produce initial output
2. CRITIQUE: What could be wrong? What did I assume?
3. REFINE: Improve based on critique
4. PRESENT: Only after reflection
```

**Why it works:** Catches errors before they propagate. Improves quality.

**When to use:** Code generation, architectural decisions, any output that matters.

**Example:**
```
GENERATED: Function to validate email
CRITIQUE: Did I handle edge cases? Empty string? Unicode?
REFINE: Add null check, use proper regex, handle IDN domains
PRESENT: Here's the validated function...
```

---

## Confidence and Uncertainty

### Confidence Levels

| Level | Indicators | Action |
|-------|-----------|--------|
| HIGH (proceed) | Matches known patterns, clear requirements, similar past success | Act autonomously |
| MEDIUM (verify) | Some unknowns, first time for this pattern, could break things | Ask before risky actions |
| LOW (ask) | Architectural change, security-sensitive, deleting files | Always ask user |

### Expressing Uncertainty

When uncertain, SAY SO:

```
GOOD: "I'm not sure if this is the right approach. Here's my reasoning..."
GOOD: "I found two possible solutions. Let me explain the tradeoffs..."
BAD: [silently picks one approach without mentioning alternatives]
BAD: [confidently states something without verifying]
```

### Confidence Calibration

Before acting, ask yourself:
1. Have I seen this pattern before? (in skills, sidecars, or this session)
2. What could go wrong?
3. Is this reversible?
4. Would a senior engineer want to review this?

---

## Error Recovery

### The Retry Pattern

```
1. ATTEMPT: Try the action
2. OBSERVE: Did it succeed?
3. DIAGNOSE: If failed, why?
4. ADJUST: Modify approach based on diagnosis
5. RETRY: Max 2 retries with different approaches
6. ESCALATE: If still failing, ask user
```

### Graceful Degradation

When stuck:
1. **Never silently fail.** Always report what happened.
2. **Provide context.** What were you trying to do? What went wrong?
3. **Suggest alternatives.** "I couldn't do X, but I could try Y instead..."
4. **Ask for help.** "I'm blocked on Z. Can you help?"

### Common Failure Modes

| Failure | Recovery |
|---------|----------|
| Tool returned error | Read error message, adjust inputs, retry |
| Unexpected output | Verify assumptions, try different approach |
| Stuck in loop | Stop, reflect, try fundamentally different approach |
| Context exhaustion | Summarize progress, ask user for direction |

---

## Multi-Agent Coordination

### Handoff Patterns

When handing off to another agent:

1. **Write before you speak.** Update session file BEFORE saying "ready for X"
2. **Summarize, don't dump.** Pass key findings, not full context
3. **State expectations.** What should the next agent do?
4. **Verify handoff.** Confirm the update was written

### State Synchronization

**Session file is source of truth.** Always:
- Read session file on activation
- Write your assessment before handoff
- Verify what you wrote is actually in the file

### Conflict Resolution

If agents disagree (e.g., Reviewer rejects Dev's code):
1. Reviewer documents specific issues
2. Dev addresses each issue
3. Reviewer re-reviews
4. Repeat until resolved or escalate to user

---

## Context Management

### Just-in-Time Loading

**Don't:** Load all potentially relevant files upfront
**Do:** Store paths/identifiers, load only when needed

```
WRONG: Read all 50 test files to understand testing patterns
RIGHT: Read testing skill, then load specific test when implementing
```

### Context Efficiency

- Keep tool results focused (don't read entire files if you need one function)
- Summarize findings rather than quoting everything
- Reference file:line instead of copying code

### When Context Gets Full

1. Summarize progress so far
2. Identify what's still needed
3. Ask user if you should continue with fresh context
4. Or hand off to subagent with focused task

---

## Reasoning Mode (Toggleable)

**Default:** Quiet mode - follow patterns internally, show only key decisions

**Verbose mode:** User says "verbose mode" to enable explicit reasoning

When verbose, show:
```
THOUGHT: [articulate intent]
ACTION: [describe tool/command]
OBSERVATION: [verify result]
REFLECT: [adjust if needed]
```

When quiet, only show:
- Key decisions
- Results
- Questions/blockers

---

## Key Sources

- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic: Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [LangChain: ReAct Pattern](https://blog.langchain.com/react-agent/)
- [LangChain: Reflection Agents](https://blog.langchain.com/reflection-agents/)

---

**Remember:** The goal is not to follow patterns rigidly, but to THINK before acting, VERIFY results, and ASK when uncertain.
