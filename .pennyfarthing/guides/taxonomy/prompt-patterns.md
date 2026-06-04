# Prompt Patterns Guide

This document describes the prompt engineering patterns used in Pennyfarthing, based on [Anthropic's official documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview).

---

## Why XML Tags?

From [Anthropic's documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags):

> When your prompts involve multiple components like context, instructions, and examples, XML tags can be a game-changer. They help Claude parse your prompts more accurately, leading to higher-quality outputs.

**Benefits:**
- **Clarity:** Clearly separate different parts of your prompt
- **Accuracy:** Reduce errors caused by Claude misinterpreting parts of your prompt
- **Flexibility:** Easily find, add, remove, or modify parts without rewriting everything
- **Parseability:** Makes it easier to extract specific parts of Claude's response

**Key insight from Anthropic:**
> There are no canonical "best" XML tags that Claude has been trained with in particular, although we recommend that your tag names make sense with the information they surround.

---

## Anthropic's Best Practices

### 1. Be Consistent

Use the same tag names throughout your prompts, and refer to those tag names when talking about the content:

```
Using the contract in <contract> tags, analyze the liability clauses.
```

### 2. Nest Tags for Hierarchy

```xml
<outer>
  <inner>
    Content here
  </inner>
</outer>
```

### 3. Combine with Other Techniques

Combine XML tags with:
- **Multishot prompting:** `<examples>`
- **Chain of thought:** `<thinking>`, `<answer>`
- **Role prompting:** System message for role, XML for structure

---

## Pennyfarthing Tag Conventions

### Agent Lifecycle Tags

| Tag | Purpose | When Applied |
|-----|---------|--------------|
| `<agent-activation>` | Step-by-step activation sequence | On agent start |
| `<agent-exit>` | Cleanup steps when leaving | On "exit" or switch |
| `<persona-loading>` | Instructions for loading character | Before activation |

### Guidance Tags

| Tag | Purpose | Used By |
|-----|---------|---------|
| `<blessed-path-guidance>` | Explains the primary workflow | Tactical agents |
| `<support-agent-guidance>` | Clarifies this is a support agent | PM, Architect, etc. |

### Attribute Patterns

Use attributes to signal importance or provide metadata:

```xml
<agent-activation CRITICAL="TRUE">
  These steps MUST be followed exactly.
</agent-activation>

<persona-loading agent="dev">
  Load the dev agent's persona.
</persona-loading>
```

---

## Tag Reference

### `<agent-activation CRITICAL="TRUE">`

The core activation sequence for every agent. The `CRITICAL="TRUE"` attribute signals this must be followed exactly.

**Structure:**
```xml
<agent-activation CRITICAL="TRUE">
1. LOAD shared behavior from .pennyfarthing/guides/agent-behavior.md
2. LOAD the FULL agent file from .pennyfarthing/agents/{agent}.md
3. READ its entire contents
4. LOAD SIDECAR MEMORY:
   ```bash
   SIDECAR="$CLAUDE_PROJECT_DIR/.pennyfarthing/sidecars"
   [ -d "$SIDECAR" ] && cat "$SIDECAR"/{agent}-*.md 2>/dev/null | head -150
   ```
5. Execute ALL activation steps exactly as written
6. Apply the loaded persona throughout the session
7. Stay in character until exit
</agent-activation>
```

### `<agent-exit>`

Cleanup steps when the agent exits or switches.

**Structure:**
```xml
<agent-exit>
When the user says "exit", "switch agent", or ends the session:
1. CAPTURE LEARNINGS: Ask yourself - any patterns, gotchas, or decisions to save?
   If yes, append to `.pennyfarthing/sidecars/{agent}-{patterns|gotchas|decisions}.md`
2. Run: [session stop command]
3. Confirm session closed.
</agent-exit>
```

### `<persona-loading agent="X">`

Instructions for loading the agent's character from the theme system.

**Structure:**
```xml
<persona-loading agent="dev">
Load this agent's persona before activation:
1. Read `.pennyfarthing/config.local.yaml`
2. Get `theme` value (default: "discworld")
3. Read `.pennyfarthing/personas/themes/{theme}.yaml`
4. Extract `agents.{agent}` section (character, style, helper, etc.)
5. Apply `attributes` from config (verbosity, formality, humor, emoji_use)
</persona-loading>
```

### `<blessed-path-guidance>`

Explains the primary "happy path" workflow for tactical agents.

**Purpose:** Guides users to use `/pf-session new` rather than invoking agents directly.

**Structure:**
```xml
<blessed-path-guidance>
## The Blessed Path

**For story-based development work:**

| Command | When to Use |
|---------|-------------|
| `/pf-session new` | Start a NEW story from the backlog |

**The TDD Flow:** `/pf-session new` -> SM -> TEA -> Dev -> Reviewer -> SM (finish)

**Other commands exist** but are not part of the main dev loop.
</blessed-path-guidance>
```

### `<support-agent-guidance>`

Clarifies that an agent is outside the core TDD loop.

**Structure:**
```xml
<support-agent-guidance>
## About This Agent

This agent supports the development process but is **not part of the core TDD loop**.

**The Core TDD Loop:** `/pf-session new` -> SM -> TEA -> Dev -> Reviewer -> SM

**When to use {Agent}:**
- {Use case 1}
- {Use case 2}

**To start story-based development work,** use `/pf-session new` instead.
</support-agent-guidance>
```

---

## Role Prompting

From [Anthropic's documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/system-prompts):

> When using Claude, you can dramatically improve its performance by using the `system` parameter to give it a role. This technique, known as role prompting, is the most powerful way to use system prompts with Claude.

**Benefits:**
- **Enhanced accuracy:** In complex scenarios, role prompting significantly boosts performance
- **Tailored tone:** Adjusts Claude's communication style
- **Improved focus:** Keeps Claude within task-specific requirements

### Pennyfarthing's Approach

We use the **persona system** for role prompting:

1. **Theme files** define characters (e.g., Discworld theme)
2. **Persona-loading** instructions tell Claude to adopt the character
3. **Agent files** provide the role's expertise and workflows

This separates:
- **Who you are** (persona) from
- **What you do** (agent instructions) from
- **How you do it** (shared behavior)

---

## Common Patterns

### Conditional Behavior Blocks

Use tags to define behavior for specific situations:

```xml
<when-tests-fail>
If tests are failing:
1. Read the error output
2. Identify the root cause
3. Fix the issue
4. Re-run tests
</when-tests-fail>
```

### Instruction Blocks

Use tags to group related instructions:

```xml
<instructions>
1. First, do X
2. Then, do Y
3. Finally, do Z
</instructions>
```

### Context Blocks

Use tags to separate context from instructions:

```xml
<context>
This project uses Go for the backend and React for the frontend.
The API follows REST conventions.
</context>

<task>
Implement a new endpoint for user authentication.
</task>
```

### Example Blocks

Use tags to provide examples:

```xml
<example>
Input: "hello world"
Output: "HELLO WORLD"
</example>
```

---

## Chain of Thought

For complex reasoning, use thinking tags:

```xml
<thinking>
Let me work through this step by step...
1. First, I need to understand the problem
2. Then, identify possible solutions
3. Finally, choose the best approach
</thinking>

<answer>
The best solution is X because...
</answer>
```

Pennyfarthing uses this in the **Reasoning Mode** (verbose mode) for tactical agents.

---

## Anti-Patterns

### Don't: Use Tags for Everything

Tags are for **structure**, not emphasis. Use markdown for emphasis:

```markdown
**IMPORTANT:** This is critical.  <!-- Good -->
```

```xml
<important>This is critical.</important>  <!-- Overkill -->
```

### Don't: Invent Unparseable Tags

If you need to extract content programmatically, use consistent, simple tags:

```xml
<output>Result here</output>  <!-- Easy to parse -->
```

```xml
<the-final-output-of-the-analysis>Result</the-final-output-of-the-analysis>  <!-- Hard to parse -->
```

### Don't: Mix Instruction Styles

Be consistent. Don't mix XML tags with other delimiters:

```xml
<!-- Good: Consistent -->
<instructions>Do X</instructions>
<context>Background info</context>

<!-- Bad: Mixed styles -->
<instructions>Do X</instructions>
---CONTEXT---
Background info
```

---

## Further Reading

- [Anthropic: Use XML tags](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags)
- [Anthropic: Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
- [Anthropic: System prompts and roles](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/system-prompts)
- [GitHub: Anthropic prompt engineering tutorial](https://github.com/anthropics/prompt-eng-interactive-tutorial)
- [Google Sheets: Interactive prompting tutorial](https://docs.google.com/spreadsheets/d/19jzLgRruG9kjUQNKtCg1ZjdD6l6weA6qRXG5zLIAhC8)
