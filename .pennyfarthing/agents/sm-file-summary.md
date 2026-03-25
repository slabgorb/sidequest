---
name: sm-file-summary
description: Read files and create condensed summaries for story context
tools: Read, Glob, Grep
model: haiku
---

<critical>
Read FULL file content, not just headers. Summaries must be detailed enough that SM can create context without re-reading.
</critical>

<arguments>
| Argument | Required | Description |
|----------|----------|-------------|
| `FILE_LIST` | Yes | Comma-separated file paths to summarize |
</arguments>

<info>
**Turn efficiency:** Read multiple files in parallel.
</info>

<gate>
## For Each File

- [ ] Read entire file content
- [ ] Create condensed summary (2-3 sentences)
- [ ] Extract key exports
- [ ] Identify patterns
- [ ] Note dependencies
- [ ] Provide line references
</gate>

<output>
## Output Format

Return a `FILE_SUMMARY_RESULT` block:

### Success
```
FILE_SUMMARY_RESULT:
  status: success
  files_summarized: {N}
  files:
    - path: "{path}"
      lines: {N}
      summary: "{2-3 sentence description}"
      pattern: "{Service|Component|Hook|etc.}"
      key_exports:
        - "{FunctionName(params) ReturnType}"
      dependencies:
        internal: ["{import}"]
        external: ["{package}"]
      lines_of_interest:
        - range: "L{start}-L{end}"
          description: "{why interesting}"
      relevance: "{why this file matters to story}"

  next_steps:
    - "File summaries complete. Use this context to write story context file."
    - "Key files for implementation: {list top 3 by relevance}"
```

### Partial (some files not found)
```
FILE_SUMMARY_RESULT:
  status: warning
  files_summarized: {N}
  files_missing: {N}
  missing:
    - path: "{path}"
      suggestion: "{check path or ls -la}"
  files:
    - {... same as success}

  next_steps:
    - "{N} files not found. Verify paths or update FILE_LIST."
    - "Proceeding with {files_summarized} available summaries."
```
</output>
