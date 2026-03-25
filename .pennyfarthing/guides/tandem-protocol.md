# Tandem Protocol Guide

Tandem mode pairs a background observer ("backseat") with the primary agent during a workflow phase. The backseat watches the primary agent's work and writes observations to a shared file. The PostToolUse hook automatically injects those observations into the primary agent's context.

## Architecture

```
Primary Agent                 Backseat Agent (Haiku, background)
     │                              │
     ├── works on story             ├── watches via git diff / file reads
     │                              │
     │                              ├── writes observation to
     │                              │   .session/{story}-tandem-{partner}.md
     │                              │
     ├── PostToolUse hook fires ────┤
     │   pf hooks bell-mode detects │
     │   new observation, injects   │
     │   "[Tandem] Character: ..."  │
     │                              │
     ├── surfaces in own voice      │
     │   "The Caterpillar notes..." │
     │                              │
     └── terminates backseat ───────┘
         before handoff
```

## Prerequisites

- Workflow must have `tandem:` block on the phase (e.g., in team workflow YAMLs)
- Session file must contain `**Tandem:** {partner} ({scope})` line (written by handoff subagent)

No configuration required. Tandem injection is always active in the PostToolUse hook — the presence of observation files in `.session/` is the only signal needed. Works in both CLI and Frame GUI.

## How It Works

### 1. Detection

On activation, agents check the session file for a `**Tandem:**` line:

```
**Tandem:** architect (file-watch)
```

If present, the agent spawns a backseat observer. If absent, tandem is a complete no-op.

### 2. Persona Resolution

The backseat agent plays its character from the active theme:

```bash
THEME=$(yq '.theme' .pennyfarthing/config.local.yaml)
CHARACTER=$(yq ".agents.{PARTNER}.character" .pennyfarthing/personas/themes/${THEME}.yaml)
```

### 3. Observation File Initialization

The primary agent creates the observation file before spawning the backseat:

```markdown
# Tandem Observations: {STORY_ID}
**Observer:** {PARTNER} ({CHARACTER})
**Phase:** {PHASE}
**Started:** {ISO_TIMESTAMP}

---
```

File path: `.session/{STORY_ID}-tandem-{PARTNER}.md`

### 4. Backseat Spawn

Via the Task tool:

```yaml
subagent_type: "general-purpose"
model: "haiku"
run_in_background: true
prompt: |
  Read .pennyfarthing/agents/tandem-backseat.md for your instructions.

  PARTNER: "{PARTNER}"
  CHARACTER: "{CHARACTER}"
  STORY_ID: "{STORY_ID}"
  SCOPE: "{SCOPE}"
  OBSERVATION_FILE: ".session/{STORY_ID}-tandem-{PARTNER}.md"
  SESSION_FILE: ".session/{STORY_ID}-session.md"
```

### 5. Observation Injection

The PostToolUse hook (tandem injection runs unconditionally, no config required):
1. Checks `.session/*-tandem-*.md` files for mtime changes
2. Parses the latest `## [HH:MM] Observation` block
3. Extracts the persona from the `**Observer:**` header
4. Injects as: `[Tandem] {Character}: {observation text}`

### 6. Surfacing Observations

When the primary agent receives a tandem injection, it surfaces the observation in its own voice using the backseat's character name:

> "The Caterpillar notes that `UserService.ts:42` returns null instead of the result object AC-3 requires."

### 7. Cleanup

Before handoff, the primary agent terminates the backseat background task. This must happen before starting the exit protocol.

## Observation Scopes

| Scope | What the backseat monitors |
|-------|---------------------------|
| `file-watch` | `git diff --stat`, changed file inspection, pattern drift |
| `tool-watch` | Tool call log (`.session/{story}-tool-log.md`), test failures, edit patterns |
| `context-watch` | Session file progress, AC coverage, scope drift |

## Observation File Format

Each entry follows this format (matches `observation-writer.ts`):

```markdown
## [HH:MM] Observation
**Trigger:** {scope}: {detail}
{observation text}

---
```

## Tandem Workflow Pairings

Tandem pairings are defined in the `tandem:` block of each workflow phase YAML. Check the active workflow YAML (e.g., `tdd-team.yaml`, `bdd-team.yaml`) for current pairings.

## Tandem Consultation Protocol

For active, synchronous agent-to-agent questions (as opposed to passive observation), see `protocols/tandem-consultation.md`. Key differences:

| Aspect | Backseat (this guide) | Consultation |
|--------|----------------------|--------------|
| Mode | Passive observer | Active request/response |
| Trigger | Phase start (automatic) | Leader-initiated (on demand) |
| Model | Haiku | Sonnet |
| Output | Observation file | Structured recommendation |
| Lifecycle | Background process | Synchronous spawn |

## Related Infrastructure

| Component | Purpose |
|-----------|---------|
| `tandem-lifecycle.ts` | Library module for future Frame integration |
| `observation-writer.ts` | TypeScript API for observation file I/O |
| `file-watch.ts` | File system change detection |
| `tool-watch.ts` | Tool call log monitoring |
| `pf hooks bell-mode` | PostToolUse hook with tandem injection |
| `bellmode_hook.py` | Python implementation of bell mode hook |
| `pf hooks statusline` | CLI statusline with tandem indicator |
| `tandem-backseat.md` | Backseat agent prompt template |
| `agent-behavior.md` | Shared agent behavior with tandem protocol |
