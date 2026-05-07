---
parent: sprint/epic-45.yaml
story: 45-53
---

# Story 45-53: Recurring NPC presence — narrator emits npcs_met every turn they're onstage

## Overview

Lane B / Bookkeeping bug. The narrator's `npcs_met` emission only fires
reliably for newly encountered NPCs (`is_new: true`) and adversaries on
confrontation turns (the CRITICAL ADVERSARY RULE in `NARRATOR_OUTPUT_ONLY`).
Recurring NPCs — allies, merchants, quest-givers, named bystanders — drop
out of `npcs_met` after their first appearance, so downstream subsystems
(`_apply_npc_mentions`, NPC pool, party state) lose track of who is
currently onstage. Playtest 3 (2026-04-19) and follow-up sessions surfaced
the pattern: an NPC introduced in turn N "vanishes" by turn N+3 even when
narration prose clearly places them in the scene.

## Background

The npcs_met spec lives in `sidequest/agents/narrator.py:NARRATOR_OUTPUT_ONLY`
(currently ambiguous on recurring presence: "Include every named NPC … the
player encounters" — encounters once or every turn?). The Wave 2A NPC pool
(`sidequest/server/narration_apply.py:_apply_npc_mentions`, story 45-47)
already updates `last_seen_*` on stateful Npcs and additively upserts pool
members on every cite — but the prompt-level emission gap means
`_apply_npc_mentions` is never invoked for the missed NPC, so the GM panel
sees nothing.

This story closes the loop on two surfaces simultaneously:

1. **Prompt amendment** — make the every-turn emission rule explicit so
   the narrator stops collapsing recurring presence into a one-shot
   introduction list.
2. **Server-side detector** — when narration prose names a known recurring
   NPC by name as onstage but `npcs_present` omits them, emit a warning
   span (`npc.recurring_presence_missed`) so Sebastien's GM-panel
   lie-detector (CLAUDE.md OTEL Observability Principle) sees the gap
   even when the narrator drifts.

## Acceptance Criteria

- AC-1 (every-turn emission rule): `NARRATOR_OUTPUT_ONLY` MUST include
  an explicit rule that every turn a named, persistent NPC is described
  as onstage (physically present in the narration), the narrator MUST
  emit that NPC in `npcs_met` with at minimum `name` and `role`,
  regardless of whether they are newly encountered that turn.

- AC-2 (NPC type coverage): The rule MUST apply to all recurring NPC
  roles — allies / companions, quest-givers / patrons, merchants /
  vendors, neutral bystanders who are named and present. Passing
  strangers with no dialogue or focus are out of scope (optional).

- AC-3 (no silent fallback): If a named NPC is described in prose as
  onstage but the narrator fails to emit them in `npcs_met`, the
  subsystem MUST surface the gap loudly. A test must fail (during
  development) with a clear error message indicating which NPC was
  missed; at runtime the gap MUST emit a warning OTEL span and a
  WARNING-level log naming the missed NPC. The runtime path is
  observation-only (no exception) per the "strict helper, lenient
  caller" precedent in story 45-33.

- AC-4 (spec integration): The narrator prompt amendment MUST
  explicitly state the every-turn rule, distinguish "named and onstage"
  (must emit) from "passing mention" (optional), and cross-reference
  the existing CRITICAL ADVERSARY RULE so the recurring rule is
  understood to extend it (not replace it) into non-combat scenes. The
  uniform `name AND role` contract applies.

## Technical Context

- **Prompt location:** `sidequest/agents/narrator.py` —
  `NARRATOR_OUTPUT_ONLY` constant, `npcs_met` section. The new rule
  block sits adjacent to the CRITICAL ADVERSARY RULE.
- **Detector location:** `sidequest/server/session_helpers.py` —
  parallel to `_detect_npc_identity_drift`. Invoked from
  `sidequest/server/narration_apply.py:_apply_narration_result_to_snapshot`
  immediately after `_apply_npc_mentions`.
- **OTEL span:** `sidequest/telemetry/spans/npc.py` — new
  `SPAN_NPC_RECURRING_PRESENCE_MISSED = "npc.recurring_presence_missed"`,
  routed as `state_transition` under `component=npc_registry` (parallel
  to `npc.referenced`, `npc.auto_registered`, `npc.reinvented`).
- **Match semantics:** word-boundary case-insensitive on the NPC name
  against `snapshot.npcs ∪ snapshot.npc_pool`, with PC-name filter and
  npcs-shadows-pool precedence.

## References

- ADR-031 — Game Watcher / OTEL (lie-detector signal pattern).
- ADR-039 — Narrator Structured Output / `npcs_met` spec origin.
- ADR-067 — Unified Narrator Agent (single persistent session).
- Story 45-47 — Wave 2A NPC pool / state split (the apply path the
  detector hooks into).
- Story 45-33 — "strict helper, lenient caller" precedent (no exception
  on LLM extraction gaps).
- CLAUDE.md — OTEL Observability Principle, No Silent Fallbacks,
  Verify Wiring Not Just Existence.
