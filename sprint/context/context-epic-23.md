# Epic 23: Narrator Prompt Architecture — Template, RAG, Universal Cartography

## Overview

Rework the narrator system prompt from a hardcoded monolith into a structured template
with attention-zone-aware sections, bash tool wrappers, and graph-based lore retrieval.

**Specification:** `docs/prompt-reworked.md` defines the canonical narrator contract.
**RAG strategy:** `docs/narrator-prompt-rag-strategy.md` (stories 23-2, 23-4).
**Room graph:** `docs/universal-room-graph-cartography.md` (story 23-3).

## Current State (post 23-1)

Story 23-1 restructured the narrator's own sections from a monolithic `NARRATOR_SYSTEM_PROMPT`
constant into 7 discrete sections registered via `NarratorAgent::build_context()`:

| Section | Zone | Category | Source |
|---------|------|----------|--------|
| narrator_identity | Primacy | Identity | narrator.rs |
| narrator_constraints | Primacy | Guardrail | narrator.rs |
| narrator_agency | Primacy | Guardrail | narrator.rs |
| narrator_consequences | Primacy | Guardrail | narrator.rs |
| narrator_output_only | Primacy | Guardrail | narrator.rs |
| narrator_output_style | Early | Format | narrator.rs |
| narrator_referral_rule | Early | Guardrail | narrator.rs |

The **orchestrator** (`orchestrator.rs:build_narrator_prompt()`) still adds its own sections
on top: SOUL principles, trope beats, script tools, game state, merchant context, active tropes,
SFX library, verbosity/vocabulary, and player action. These orchestrator-level sections are the
target of stories 23-6 through 23-11.

## Key Files

| File | Role |
|------|------|
| `crates/sidequest-agents/src/agents/narrator.rs` | Narrator's 7 structured sections |
| `crates/sidequest-agents/src/orchestrator.rs` | Prompt assembly pipeline (L254-L555) |
| `crates/sidequest-agents/src/prompt_framework/types.rs` | AttentionZone, SectionCategory, PromptSection |
| `crates/sidequest-agents/src/context_builder.rs` | ContextBuilder — zone-ordered composition |
| `crates/sidequest-server/src/dispatch/prompt.rs` | state_summary assembly from game state |
| `SOUL.md` | Principle definitions with per-agent filtering |
| `docs/prompt-reworked.md` | Target template specification |

## Tools

`scripts/preview-prompt.py` — Python mirror of the prompt composition pipeline for rapid
iteration. Shows all sections ordered by zone with token estimates. Use `--raw` for
Claude's-eye view. This is the shaping tool; OTEL prompt inspector is the tuning tool.

## Architectural Decisions

- **No template engine** (23-1): Handlebars syntax in `prompt-reworked.md` is design notation.
  PromptSection + ContextBuilder IS the template engine. `format!()` strings, not crate deps.
- **SOUL is orchestrator's responsibility**: Narrator's `build_context()` never injects
  SectionCategory::Soul. The orchestrator filters SOUL.md per agent name and injects in Early zone.
- **Token budget awareness**: ~1,934 tokens structural overhead before game state. SOUL principles
  alone are ~635 tokens. Stories 23-10 and 23-11 address budget optimization.

## SOUL Overlap Map

| SOUL Principle | agents tag | Narrator guardrail equivalent | Overlap? |
|---|---|---|---|
| Agency | all | narrator_agency (Primacy) | Yes — narrator version adds multiplayer rules |
| Living World | all | (none) | No overlap |
| Genre Truth | all | narrator_consequences (Primacy) | Yes — narrator version is operationally specific |
| Diamonds and Coal | narrator,ensemble | (none) | No overlap |
| Yes, And | all | (none) | No overlap |
| Cut the Dull Bits | narrator,ensemble,dialectician | (none) | No overlap |
| Rule of Cool | all | (none) | No overlap |
| The Test | all | (none) | No overlap |

Story 23-10 resolves the Agency and Genre Truth overlaps.

## Story Dependency Graph

```
23-1 (done) ← foundation for all others
  ├── 23-6 (tool wrappers) — independent
  ├── 23-9 (env vars) — pairs naturally with 23-6
  ├── 23-10 (SOUL dedup) — independent
  ├── 23-11 (tool simplification) — pairs naturally with 23-6
  ├── 23-7 (tone axes) — needs genre pack model changes
  ├── 23-8 (state split) — needs server dispatch/prompt.rs changes
  ├── 23-5 (dynamic tone axes) — depends on 23-7
  ├── 23-2 (lore summaries) — independent, content repo
  ├── 23-3 (room graph cartography) — independent, content + api
  └── 23-4 (LoreFilter) — depends on 23-2, 23-3
```

## Planning Documents

| Document | Path |
|----------|------|
| Prompt template spec | `docs/prompt-reworked.md` |
| RAG strategy | `docs/narrator-prompt-rag-strategy.md` |
| Room graph cartography | `docs/universal-room-graph-cartography.md` |
| ADR-009 (attention zones) | `docs/adr/009-attention-aware-prompt-zones.md` |
| Preview tool | `scripts/preview-prompt.py` |
