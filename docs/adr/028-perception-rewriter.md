---
id: 28
title: "Perception Rewriter"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [multiplayer]
implementation-status: live
implementation-pointer: null
---

# ADR-028: Perception Rewriter

> Ported from sq-2. Language-agnostic multiplayer mechanic.

## Context
In multiplayer, different players should perceive the same event differently based on their character's status effects (charmed, blinded, deafened, etc.).

## Decision
The server maintains a canonical narration and rewrites it per-player based on active status effects.

### Rewrite Rules
| Effect | Rewrite |
|--------|---------|
| Charmed | Enemies described as allies; danger downplayed |
| Blinded | Visual details removed; sounds and smells emphasized |
| Deafened | Dialogue removed; visual descriptions enhanced |
| Frightened | Threats exaggerated; escape routes highlighted |
| Invisible | Other characters described from observer perspective |

### Parallel Execution
Multiple rewrites run concurrently via `tokio::join!` — total latency is the slowest single rewrite, not accumulated.

### SOUL Alignment
This is "asymmetric message passing that exceeds what a tabletop GM could manage" — exactly what the digital medium should provide.

## Consequences
- Each player gets a unique, status-appropriate version of events
- One LLM call per player per effect (parallelized)
- Canonical narration is always preserved for logs
