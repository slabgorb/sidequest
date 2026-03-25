# ADR-013: Lazy JSON Extraction

> Ported from sq-2. Rust adaptation: `serde_json` with regex fallback.

## Status
Accepted

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
