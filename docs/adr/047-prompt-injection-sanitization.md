---
id: 47
title: "Prompt Injection Sanitization Layer"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [transport-infrastructure]
implementation-status: live
implementation-pointer: null
---

# ADR-047: Prompt Injection Sanitization Layer

> Retrospective — documents a decision already implemented in the codebase.

## Context
Players submit free-form text (dialogue, actions, item names) that flows directly into Claude's context window via agent prompts. Without sanitization, a player can trivially inject structural instructions — wrapping input in `<system>` tags, prefixing with "ignore all previous instructions", or using unicode confusables to bypass naive filters. The attack surface is at the seam between player input and prompt construction.

The question was where to place the defense: at each agent call site, or at the protocol boundary before any routing occurs.

## Decision
All player-authored text passes through `sanitize_player_text()` in `sidequest-protocol` before it can reach any agent. The sanitizer runs at the protocol deserialization layer, so no consumer — narrator, creature_smith, ensemble — can receive unsanitized player text by mistake.

The sanitizer strips:
- XML-like structural tags: `<system>`, `<context>`, `<prompt>`, `<instruction>`, etc.
- Bracket-notation override markers: `[SYSTEM]`, `[INST]`, `[CONTEXT]`
- Override preambles: "ignore all previous instructions", "disregard your system prompt", and variants
- Fullwidth unicode confusables: `＜＞` normalized to `<>` before tag stripping
- Zero-width characters used for tag bypass: U+200B, U+200C, U+200D, U+FEFF

Regex patterns are compiled once at startup via `LazyLock` and reused across all calls — no per-call compilation overhead.

```rust
// sidequest-protocol/src/sanitize.rs
static XML_TAG_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)<\s*/?\s*(system|context|prompt|instruction|human|assistant)\s*[^>]*>").unwrap()
});
```

The function is `pub` within the protocol crate and called during `PlayerAction` deserialization, ensuring the boundary is enforced structurally rather than by convention.

## Alternatives Considered

**Agent-level sanitization** — each agent sanitizes its own inputs. Rejected: requires every current and future agent author to remember to call sanitize. One missed call opens the hole.

**Allowlist-only characters** — strip anything outside `[a-zA-Z0-9 .,!?'-]`. Rejected: too restrictive for natural language. Breaks non-English text, proper nouns, and legitimate punctuation.

**LLM-based detection** — route suspicious input through a guard model. Rejected: circular dependency (the guard is also a Claude call), adds latency on every player action, and creates a second attack surface.

## Consequences

**Positive:**
- Security boundary is enforced at the protocol layer — no agent can receive unsanitized player text by construction.
- `LazyLock` compilation keeps hot-path cost negligible (pattern compiled once).
- Adding new attack patterns requires changes in one place only.

**Negative:**
- Sanitization happens before logging — raw player input is not preserved anywhere in the pipeline if needed for forensics.
- Overly aggressive pattern matching could strip legitimate player text that happens to contain bracket notation (e.g., stage directions like `[draws sword]`). Tuning the patterns is an ongoing concern.
