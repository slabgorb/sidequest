---
id: 16
title: "Three-Mode Character Creation"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-016: Three-Mode Character Creation

> Ported from sq-2. Language-agnostic game design.

## Decision
Character creation supports three modes, all producing the same `Character` output:

| Mode | Speed | LLM Cost | Description |
|------|-------|----------|-------------|
| **Menu** | ~30s | Zero | List selection from archetypes |
| **Guided** | ~3min | Zero | Scene-based state machine (ADR-015) |
| **Freeform** | ~2min | 1 call | Player writes prose, LLM extracts structure |

### Freeform Parser
Extracts structured character data from prose using Claude CLI. Falls back to keyword heuristics if Claude is unavailable.

### Architecture
All three modes use the same base `CharacterBuilder`. Mode selection happens at the start; the output `Character` struct is identical regardless of path.

## Consequences
- Players choose their preferred creation depth
- Freeform mode degrades gracefully without LLM
- All modes produce identical data for downstream systems
