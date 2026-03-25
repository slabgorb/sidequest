# ADR-002: SOUL Principles

> Ported from sq-2. Language-agnostic — game design philosophy.

## Status
Accepted

## Context
SOUL.md is a human-readable design document that also serves as machine-parsed prompt content. It defines the seven principles that govern all agent behavior.

## Decision
SOUL.md is parsed at startup, cached, and injected into every agent's system prompt using dual-zone placement (EARLY for context-setting, LATE for verification).

### The Seven Principles

| Principle | Enforcement |
|-----------|-------------|
| **Agency** | Player choices must matter; never control the player character |
| **Living World** | NPCs act on their own goals; world continues when player isn't looking |
| **Genre Truth** | Genre pack rules override defaults; tone must be consistent |
| **Tabletop First** | Mechanics serve narrative, not the other way around |
| **Cost Scales with Drama** | Effort (tokens, compute, detail) proportional to narrative weight |
| **Diamonds and Coal** | Important things get detail; mundane things stay minimal |
| **The Test** | "Would this be a good moment at a tabletop?" |

### Injection Pattern
1. Parse bold-header principles from SOUL.md into `SoulPrinciple` structs
2. Cache via `once_cell::sync::Lazy` (parsed once at startup)
3. Inject into EARLY zone of every prompt (context-setting)
4. Append `<before-you-respond>` block in LATE zone (verification checklist)

## Consequences
- Every agent prompt includes ~200 tokens of principle content
- Dual-zone ensures principles are seen at both high-attention positions
- SOUL.md is the single source of truth for game philosophy
