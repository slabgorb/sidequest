---
id: 39
title: "Narrator Structured Output (JSON Sidecar Block)"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [13]
tags: [narrator]
implementation-status: live
implementation-pointer: null
---

> **Un-superseded 2026-05-02.** This ADR was previously marked superseded by
> ADR-057 (Narrator Crunch Separation). ADR-057 has since been deprecated —
> its design (narrator calls tools mid-generation) was infeasible under
> ADR-001's `claude -p` transport. The fenced-JSON-sidecar architecture
> described below is what's actually running. Restored to `accepted` /
> `live`. The block has been renamed from generic "JSON sidecar" to
> `game_patch` and the field set has evolved; see
> **§Implementation status (2026-05-02)** for the current contract and
> source-of-truth pointers.

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

## Implementation status (2026-05-02)

The protocol shape this ADR describes is live and load-bearing; the field
set has evolved since the original write-up. Source of truth for the
current narrator contract is the system prompt in
`sidequest-server/sidequest/agents/narrator.py`, not this ADR. Read this
ADR for *why* the design is shaped this way; read `narrator.py` for *which
fields* are current.

**Block rename.** The generic "fenced `json` block" of the original ADR is
now a fenced **`game_patch`** block. See `narrator.py:88`:
> "After your prose, emit a fenced JSON block labeled game_patch …"
The fence label disambiguates the patch block from any incidental JSON
the narrator might cite in prose. The block remains terminal (after all
prose) and exactly one per turn.

**Current field set** (per `narrator.py:90`, valid as of 2026-05-02):
`confrontation, items_gained, items_lost, items_discarded, items_consumed,
location, npcs_met, mood, state_snapshot, beat_selections, visual_scene,
footnotes, gold_change, action_rewrite, status_changes`. Plus
`magic_working` per the magic system at `magic/models.py:73`. The original
field list in §Decision is partial and out of date — defer to the prompt.

**Field renames since the original ADR:**

- `npcs_present` → `npcs_met`
- `scene_mood` → `mood`
- `personality_events` (described in original ADR for ADR-042) — in flux
  per ADR-042's drift status; current narrator does not emit this
  consistently
- `lore_established` → folded into `footnotes` (footnotes carry the
  knowledge journal entries)

**New fields not in the original ADR:**

- `items_discarded` — items dropped/abandoned but recoverable, distinct
  from `items_lost` (gone) and `items_consumed` (used up). Added during
  Playtest 3 to fix the maintenance-kit-after-patch-foam-use bug.
- `items_consumed` — one-shot consumables (Story 45-15).
- `beat_selections` — confrontation beat IDs the narrator chose; consumed
  by `apply_beat()` per ADR-033.
- `gold_change`, `status_changes`, `action_rewrite` — promoted from
  per-field schemas to first-class top-level fields.
- `magic_working` — Coyote Star iter 3 magic system events.

**Python ports of the extraction surface** (extends ADR-013):

- `sidequest-server/sidequest/agents/orchestrator.py:576` —
  `extract_structured_from_response()`, port of the original Rust function
  in `sidequest-agents/src/orchestrator.rs`.
- `sidequest-server/sidequest/agents/orchestrator.py:552` —
  `_strip_json_fence()`, the tier-2 fence-strip helper.
- `sidequest-server/sidequest/agents/__init__.py:46, 75` — public exports.

**Original "Implemented in" line:** the Rust path
`sidequest-agents/src/orchestrator.rs` no longer exists; the implementation
crossed into Python during the 2026-04 port (ADR-082). The Rust source is
preserved at <https://github.com/slabgorb/sidequest-api> for historical
reference.

> The previous `superseded-by: 57` arrow was incorrect. ADR-057 was a
> design that could not ship under ADR-001's `claude -p` transport
> constraint and has been deprecated. The fenced-block architecture this
> ADR describes is the architecture currently running and has been
> continuously since the design landed.
