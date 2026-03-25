---
name: otel
description: Claude Code OTEL telemetry format documentation. Use when working with OTEL span interception, enrichment, or correlation in BikeRack GUI.
allowed_tools: [Read, Glob, Grep, Task]
---

# OTEL Skill - Claude Code Telemetry

<run>Enable OTEL debug logging and inspect telemetry data to understand span structure, attributes, and correlation patterns.</run>

<output>Enriched span data with tool metadata, file information, and correlation IDs for UI visualization and telemetry analysis.</output>

## Purpose

Document the actual OTEL data Claude Code emits. This is ground truth, not speculation.

**WARNING:** Do NOT assume fields exist. Check this document first.

## Quick Start - Enable Debug Logging

```bash
# Option 1: Via environment variable
OTEL_DEBUG=true npm run dev

# Option 2: Runtime toggle (in code or devtools)
import { setOtelDebug } from './otlp-receiver.js';
setOtelDebug(true);
```

Captures go to:
- Console: `[OTEL-CAPTURE]` prefix
- File: `/tmp/otel-capture.jsonl`

View captures:
```bash
cat /tmp/otel-capture.jsonl | jq .
# Or tail live:
tail -f /tmp/otel-capture.jsonl | jq .
```

## Status

**WORKING** - Stories 36-9, 36-10, 36-2, and 36-3 have established working enrichment patterns.

## Known Facts (Verified)

### LogRecord Structure

Claude Code exports OTEL logs (not traces/spans). The logRecord structure:

```typescript
interface LogRecord {
  timeUnixNano: string;       // Nanoseconds since epoch
  observedTimeUnixNano: string;
  body: { stringValue: string };  // Event name (e.g., "claude_code.tool_result")
  attributes: Attribute[];    // Key-value pairs
  droppedAttributesCount: number;
  // NOTE: traceId and spanId are NOT present at logRecord level
}
```

### What We Know Is MISSING

- `traceId` - NOT in logRecord (Story 36-9 confirmed)
- `spanId` - NOT in logRecord (Story 36-9 confirmed)
- `tool_use_id` - NOT in OTEL attributes; use Claude message stream `block.id` instead

### Event Types Observed

| Event Name | Description |
|------------|-------------|
| `claude_code.tool_result` | Tool execution completed |
| `claude_code.user_prompt` | User prompt submitted |
| `claude_code.api_request` | API request made |

### Tool Result Attributes (VERIFIED)

```
tool_name: string           // e.g., "Read", "Edit", "Bash"
tool_parameters: string     // JSON string with tool-specific input
tool_output: string         // Tool output (truncated to ~2000 chars)
duration_ms: string|number  // Execution time in milliseconds
success: string             // "true" or "false" as string
error?: string              // Error message if failed
```

### tool_parameters Format by Tool (VERIFIED)

**Read:**
```json
{ "file_path": "/absolute/path/to/file.ts" }
```

**Edit:**
```json
{
  "file_path": "/absolute/path/to/file.ts",
  "old_string": "text to replace",
  "new_string": "replacement text"
}
```

**Bash:**
```json
{
  "command": "git status",
  "description": "Check git status",
  "timeout": 120000,
  "run_in_background": false
}
```

## Correlation Strategy (WORKING)

Story 36-10 solved the correlation problem:

1. Claude message stream provides `tool_use` with `block.id`, `block.name`, `block.input`
2. Store in pending queue via `storePendingToolInput(toolId, toolName, input)`
3. When OTEL arrives, match via `consumePendingToolInput(toolName, parsedToolParams)`
4. **Key fix:** For Read/Edit, match on `file_path` first for precise correlation
5. Fall back to FIFO by toolName for tools without file_path (e.g., Bash)
6. Use `block.id` (toolId) as synthetic spanId for correlation map

**Why this works:**
- Claude message stream arrives BEFORE OTEL tool_result
- file_path matching handles concurrent Read/Edit operations correctly
- FIFO fallback works for Bash since commands are typically sequential

## Enrichment Pipeline

```
Claude Message Stream           OTEL Logs
       |                             |
  tool_use event               tool_result event
       |                             |
storePendingToolInput()        consumePendingToolInput()
       |                             |
       +-----> Correlation <---------+
                    |
             enrichXxxSpan()
                    |
            ToolEvent with metadata
                    |
              Broadcast to UI
```

### Implemented Enrichments

| Tool | Enrichment Function | Data Added |
|------|---------------------|------------|
| Read | `enrichReadSpan()` | fileSize, lineCount, language, gitStatus |
| Edit | `enrichEditSpan()` | fileSize, language, gitStatus, diff (added/removed) |
| Bash | `enrichBashSpan()` | command (redacted), exitCode, outputSummary, workingDirectory |

### Secret Redaction (Bash)

Commands are redacted before storage:
- `password=xxx` → `password=[REDACTED]`
- `token=xxx` → `token=[REDACTED]`
- AWS credentials → `AWS_SECRET_ACCESS_KEY=[REDACTED]`
- GitHub tokens (ghp_xxx) → `[REDACTED]`
- Long base64 strings (40+ chars) → `[REDACTED]`

## Files to Reference

| File | Purpose |
|------|---------|
| `packages/cyclist/src/otlp-receiver.ts` | OTEL parsing, enrichment integration |
| `packages/cyclist/src/span-correlation.ts` | Pending tool input queue, correlation map |
| `packages/cyclist/src/file-enrichment.ts` | Enrichment functions (Read, Edit, Bash) |
| `packages/cyclist/src/main.ts:820-824` | Message stream tool_use capture |

## API

```typescript
// Enable/disable debug at runtime
import { setOtelDebug, isOtelDebugEnabled } from './otlp-receiver.js';

setOtelDebug(true);   // Start capturing
setOtelDebug(false);  // Stop capturing
isOtelDebugEnabled(); // Check status

// Enrichment functions
import { enrichReadSpan, enrichEditSpan, enrichBashSpan } from './file-enrichment.js';

// Correlation
import { storePendingToolInput, consumePendingToolInput } from './span-correlation.js';
```

## Captured Data Format

Each line in `/tmp/otel-capture.jsonl` contains:

```json
{
  "timestamp": "2026-01-15T08:00:00.000Z",
  "eventName": "claude_code.tool_result",
  "logRecordKeys": ["timeUnixNano", "body", "attributes", ...],
  "traceId": null,
  "spanId": null,
  "attributes": [
    { "key": "tool_name", "value": { "stringValue": "Read" } },
    ...
  ]
}
```

## Related Stories

| Story | Title | Status |
|-------|-------|--------|
| 36-1 | OTEL span interception and correlation | DONE |
| 36-2 | Read/Edit tool enrichment | DONE |
| 36-3 | Bash tool enrichment | DONE |
| 36-4 | Search tool enrichment (Grep/Glob) | Backlog |
| 36-5 | Task/subagent enrichment | Backlog |
| 36-9 | Bug: missing trace/span IDs | DONE |
| 36-10 | Bug: race condition in correlation | DONE |

## Next Steps (Remaining Work)

1. **36-4:** Add Grep/Glob enrichment (pattern, match count, file list)
2. **36-5:** Add Task enrichment (subagent type, prompt summary, turn count)
3. **36-6:** Export enriched spans to UI visualization
