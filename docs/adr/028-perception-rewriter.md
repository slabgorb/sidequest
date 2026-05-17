---
id: 28
title: "Perception Rewriter"
status: superseded
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: 104
related: [36, 101, 104]
tags: [multiplayer]
implementation-status: retired
implementation-pointer: "Original post-narration N+1 rewriter retired — replaced by ADR-104 tool-layer filtering (sidequest-server/sidequest/agents/narrator_perception_filter.py) on the default anthropic_sdk path. The perception_rewriter.py module survives only as the non-LLM ADR-105 broadcast-layer status-effect prose filter (rewrite_for_recipient, server/emitters.py:17,334,370)."
---

# ADR-028: Perception Rewriter

> **SUPERSEDED AND RETIRED (correction 2026-05-17).** The mechanism described
> below — a *post-narration N+1 LLM rewrite*, one extra Claude call per
> recipient — is **retired**. On the default `anthropic_sdk` backend
> (ADR-101), per-recipient perception is enforced at the **tool layer**
> ([ADR-104](104-perception-filtering-at-the-tool-layer.md)) via
> `sidequest-server/sidequest/agents/narrator_perception_filter.py` — no
> extra LLM call. A descendant module, `agents/perception_rewriter.py`
> (`rewrite_for_recipient`), survives **only** as the non-LLM
> broadcast-layer status-effect prose filter
> ([ADR-105](105-broadcast-layer-perception-firewall.md)),
> called from `sidequest-server/sidequest/server/emitters.py:17,334,370`.
> The N+1-call design below is preserved as a historical record only.

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
