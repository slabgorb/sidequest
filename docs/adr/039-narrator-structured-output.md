---
id: 39
title: "Narrator Structured Output (JSON Sidecar Block)"
status: superseded
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: 57
related: []
tags: [narrator]
implementation-status: retired
implementation-pointer: null
---

# ADR-039: Narrator Structured Output (JSON Sidecar Block)

> Retrospective — documents a decision already implemented in the codebase.

## Context
The narrator agent (Claude CLI subprocess) was producing prose-only responses. Extracting semantic data — image subjects for generation, NPC names for registration, items acquired, lore established — required either separate LLM calls or fragile regex over free prose. ADR-013 established that lazy JSON extraction was preferable to dedicated extraction calls, but didn't define what to extract or the full protocol shape. As the system matured, the set of data needing structured extraction grew: OCEAN personality events, quest updates, resource deltas, visual scene descriptions. Without a typed protocol, each new field was a new extraction hack.

## Decision
The narrator prompt instructs Claude to append a fenced `\`\`\`json` block after all prose. This block is parsed into a `NarratorStructuredBlock` struct in a single pass. Every field represents a decision to do extraction in-band rather than via a separate call.

Fields in `NarratorStructuredBlock`:
- `footnotes` — sourced references or lore citations
- `items_gained` / `items_lost` — inventory mutations (replaces regex-on-prose item detection)
- `npcs_present` — NPC names appearing in the scene (feeds NPC registry)
- `quest_updates` — progress signals for active quests
- `visual_scene` — image generation subject (eliminates a separate image-subject-extraction LLM call)
- `scene_mood` — emotional register for music/TTS selection
- `personality_events` — typed `PersonalityEvent` values for OCEAN shift proposals (see ADR-042)
- `resource_deltas` — currency, stamina, and other tracked resources
- `lore_established` — facts asserted this scene, written to the lore store

Extraction uses a three-tier fallback strategy (extending ADR-013):
1. Fenced ` ```json ``` ` block (primary)
2. Trailing JSON object identified by known key presence
3. Bare JSON array

The `ActionResult` struct exposes which tier was used as a telemetry field so the GM panel can track LLM formatting compliance over time.

Implemented in: `sidequest-agents/src/orchestrator.rs` — `NarratorStructuredBlock`, `extract_structured_from_response()`

## Alternatives Considered

**Separate extraction LLM calls per field type** — rejected: multiplies latency and token cost. Each call also loses the prose context that makes extraction accurate.

**Regex/heuristic extraction from prose** — rejected: brittle against narrator style variation; proven failure mode before ADR-013.

**Streaming structured output (OpenAI-style)** — rejected: SideQuest uses Claude CLI subprocess (`claude -p`), not the SDK. Streaming structured output isn't available in that execution model.

**Separate structured and prose prompts** — rejected: doubles LLM calls per player action; also loses coherence between what the narrator said and what it extracted.

## Consequences

**Positive:**
- Single LLM call per player action regardless of how many data types need extraction.
- `visual_scene` field eliminates what was previously a second Claude call for image subject generation.
- Typed protocol makes narrator output a first-class contract — fields are versioned with the struct.
- Extraction tier telemetry surfaces LLM formatting compliance without manual inspection.
- OCEAN personality evolution (ADR-042) and NPC registry both depend on this; centralizing extraction keeps those systems coherent.

**Negative:**
- Narrator prompt is longer and more structured than pure prose prompts — slight increase in input tokens.
- Three-tier fallback adds parsing complexity; tier-2 and tier-3 paths need ongoing testing as Claude's formatting behavior evolves.
- If Claude omits the JSON block entirely, all extraction fails silently (mitigated by tier telemetry alerting on tier-3 fallback frequency).
