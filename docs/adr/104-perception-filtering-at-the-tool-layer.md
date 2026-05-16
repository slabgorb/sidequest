---
id: 104
title: "Perception Filtering at the Tool Layer"
status: proposed
date: 2026-05-15
deciders: [Keith Avery]
supersedes: [28]
superseded-by: null
related: [28, 36, 101, 102]
depends_on: [101, 102]
tags: [multiplayer, agent-system]
implementation-status: partial
implementation-pointer: 101
load_bearing: false
---

# ADR-104: Perception Filtering at the Tool Layer

## Status

**Proposed.** Promotes to `accepted` on the Phase E merge alongside
ADR-101.

## Context

ADR-028 (Perception Rewriter) envisioned a per-PC LLM rewriting pass
that took an omniscient narration and re-voiced it for each recipient
PC, redacting content their character shouldn't have observed. The
spec's cost math was "N+1 model calls per multiplayer turn" — one
omniscient narration plus N rewrite passes.

**That LLM-based rewriter was never built.** The
`sidequest/agents/perception_rewriter.py` module that exists today is
a *different* thing: a deterministic, post-projection span-strip pass
that runs in the MP fan-out emitter
(`sidequest/server/emitters.py:283`) on top of the visibility
classifier. Its job is **status-effect-based fidelity override**: a
PC who is `blinded` gets `visual_only` spans stripped on top of their
base fidelity, a PC who is `deafened` gets `audio_only` spans
stripped, etc. The module docstring explicitly notes "LLM re-voicing
is deferred to post-MP (G10)."

Phase C of the Anthropic SDK migration (ADR-101) introduced a
different filter — `NarratorPerceptionFilter` at
`sidequest/agents/narrator_perception_filter.py` — that runs on every
**tool result** before it's handed back to the model. This is a
narrator-side filter: it ensures the *narrator* never sees content
the perspective PC shouldn't perceive, so the resulting narration is
perception-correct *at generation time*.

These are two distinct surfaces:

| Filter | Lives | Surface | Driven by |
|---|---|---|---|
| `NarratorPerceptionFilter` (Phase C) | `sidequest/agents/narrator_perception_filter.py` | Tool result returned to the model | `perspective_pc` of the narration call |
| `perception_rewriter.py` (pre-ADR-101, retained) | `sidequest/server/emitters.py` fan-out | WS payload broadcast to each recipient | Recipient's status effects on top of base fidelity |

## Decision

**Narrator-side perception filtering moves to the tool layer.** Per
ADR-101 + ADR-102's tool-use architecture, every read-category tool
result is filtered by `NarratorPerceptionFilter` against the
`perspective_pc` before being returned to the model. The narrator
generates a perception-correct narration directly; no post-narration
rewriter pass is required on the narrator side.

The per-tool filter rule table (from the design spec) is implemented
in `_RULES` at `narrator_perception_filter.py`:

| Tool | Filter |
|---|---|
| `query_npc` | Disposition coarsened to what `perspective_pc` has observed; charm/deception applied |
| `query_known_facts` | Returns only `perspective_pc`'s facts |
| `query_lore` | Filtered to lore PC has access to; classified info hidden |
| `query_scene_state` | Filtered to PC line-of-sight/audibility |
| `lookup_monster` | "Lore-safe" surface default; `include_stat_block=true` perception-gated |
| `query_encounter` | Foe HP coarsened ("unwounded/wounded/bloodied/staggering") |
| `query_magic_state` | PC's own exact; others' visible-effects only |
| `query_gossip` | Filtered to what PC has heard / could overhear |
| `query_scenario_clues` | Filtered to clues this PC has discovered |
| `query_character` | Self exact; party coarsened HP; non-party hidden |

Write-category tools are objective: mutations land regardless of who
observes them; the result_status may include
`observed: false, narration_hint: "..."` to signal the model the
action happened off-camera.

### Coexistence with the MP fan-out filter

`sidequest/agents/perception_rewriter.py` and its call site in
`sidequest/server/emitters.py:283` are **retained**. The fan-out
filter does work the tool-layer filter cannot:

- Tool-layer filtering operates on the *narrator's perspective_pc*.
- Fan-out filtering operates on each *recipient's status effects on
  top of their base fidelity*.

A 4-PC scene where PC-A narrates and broadcasts to PC-B/C/D still
needs B's `blinded` status to strip visual spans from A's narration,
because the *generated* narration is correct for A's perspective —
not for B's combination of (base fidelity from A's narration) +
(B's status effects).

This is what the Phase D plan misread as "delete the rewriter." The
spec's "N+1 → N calls" framing applies only to the LLM-rewriter
mechanism that ADR-028 envisioned and that the codebase never had;
the deterministic span-strip pass has always been part of the MP
fan-out path and is independent of the SDK migration.

## Consequences

### Positive

- Narrator generates perception-correct narration directly — no
  redaction round-trips on the model side.
- Sealed-visibility (PvP, hidden submission) becomes trivial to add:
  route a PC's narration only to that client and don't broadcast. No
  rewriter gymnastics needed.
- The tool-layer filter is a typed, per-tool rule table — easy to
  audit and extend per ADR-102.
- The MP fan-out filter retains its targeted scope: status-effect
  override of fidelity on broadcast. It does one thing well.

### Doctrine preserved

- CLAUDE.md collaborative-visibility doctrine (peer action text
  visible during submit-and-wait per ADR-036's 2026-05-03 amendment)
  is preserved unchanged.
- ADR-028's *intent* (a perception-correct narration per recipient) is
  now delivered by the tool-layer filter for the narrator path; the
  fan-out filter handles cross-PC visibility on broadcast.

### Plan deviation note

The Phase D plan called for outright deletion of
`sidequest/agents/perception_rewriter.py` and its tests. That deletion
was reverted in scope because the module is load-bearing for MP
fan-out. The plan's framing assumed the rewriter was an LLM call (N+1
turn cost); inspection showed it has always been a deterministic
span-strip. See commit `ed6f9ef` (sidequest-server) for the docstring
clarification.

### Negative

- Two filters to keep in sync conceptually: a future change to the
  visibility model needs to thread through both surfaces. The
  responsibility split is documented in both modules' docstrings.

## References

- ADR-101 — Anthropic SDK as Narrator Backend (parent)
- ADR-028 — Perception Rewriter (superseded)
- ADR-036 — Multiplayer Turn Coordination (collaborative-visibility
  doctrine)
- ADR-102 — Tool-Use Protocol for Structured Output (tool-result
  filter substrate)
- Design spec: `docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md` §Perception filtering at the tool layer
