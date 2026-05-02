---
id: 13
title: "Lazy JSON Extraction"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [39]
tags: [agent-system]
implementation-status: live
implementation-pointer: null
---

> **Un-superseded 2026-05-02.** This ADR was previously marked superseded by
> ADR-057 (Narrator Crunch Separation). ADR-057 has since been deprecated —
> its design was infeasible under ADR-001 (`claude -p` cannot call tools
> mid-generation). The three-tier extraction strategy described below is
> the architecture currently running in Python. Restored to `accepted` /
> `live`. See **§Implementation status (2026-05-02)** for the Python ports.

# ADR-013: Lazy JSON Extraction

> Ported from sq-2. Original adaptation: Rust `serde_json` with regex fallback.
> Current adaptation: Python equivalents in `sidequest-server`.

## Context
Claude's output format varies despite explicit JSON instructions. ~10% of responses wrap JSON in markdown fences, add preamble text, or use other formatting.

## Decision
Three-tier extraction fallback that never panics:

1. **Direct parse:** `serde_json::from_str(raw)`
2. **Fence strip:** Extract from `` ```json ... ``` `` block, then parse
3. **Regex extract:** Find first `{ ... }` block via regex, then parse

```rust
pub fn extract_json<T: DeserializeOwned>(raw: &str) -> Option<T> {
    // Tier 1: direct parse
    if let Ok(v) = serde_json::from_str(raw) {
        return Some(v);
    }

    // Tier 2: markdown fence
    if let Some(fenced) = extract_fenced_json(raw) {
        if let Ok(v) = serde_json::from_str(&fenced) {
            return Some(v);
        }
    }

    // Tier 3: regex first { } block
    if let Some(block) = extract_first_json_block(raw) {
        if let Ok(v) = serde_json::from_str(&block) {
            return Some(v);
        }
    }

    None
}
```

## Consequences
- Robust against Claude's formatting variability
- Never raises exceptions — returns `None` on total failure
- Should be a shared utility, not duplicated per agent

## Implementation status (2026-05-02)

Three-tier extraction is live in Python under `sidequest-server`. The Rust
code sample above is preserved as the original design illustration; the
current implementation is below.

- **Tier 2 fence strip** — `_strip_json_fence()` at
  `sidequest-server/sidequest/agents/orchestrator.py:552`. Comment notes it
  is "Port of `strip_json_fence()` in `orchestrator.rs`". Discards
  post-patch content with a logged warning (no silent fallback).
- **Tier 1 + 2 + 3 combined entry point** —
  `extract_structured_from_response()` at
  `sidequest-server/sidequest/agents/orchestrator.py:576`. Public API
  re-exported from `sidequest/agents/__init__.py:46, 75`.
- **LocalDM-side equivalent** — `_extract_json_object()` at
  `sidequest-server/sidequest/agents/local_dm.py:229` handles the same
  fence-strip pattern for Haiku responses (the LocalDM preprocessor is
  dormant per the 2026-04-28 spec but the helper remains).

Returns the `None`-on-total-failure semantics this ADR specified. The
"never panics" property carries through to Python as "never raises" —
malformed JSON returns `None`/empty dict and the caller decides what to do.

> The previous `superseded-by: 57` arrow was incorrect. ADR-057 was a
> design that could not ship under ADR-001's transport constraint and has
> been deprecated. The three-tier extraction this ADR describes is what
> the system has used continuously since 2026-03-25.
