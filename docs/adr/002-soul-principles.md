---
id: 2
title: "SOUL Principles"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [82]
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-002: SOUL Principles

## Implementation status (2026-05-02)

**SOUL.md is the canonical source of truth for game philosophy. Read it, not this ADR, for the actual principles.** This ADR exists only to record the decision *that SOUL.md is parsed and injected into agent prompts* — the principle text itself lives in `SOUL.md` at the repo root and is the single source of truth.

Live wiring (Python, post-ADR-082 port):
- **Parser:** `sidequest-server/sidequest/agents/prompt_framework/soul.py` — `parse_soul_md`, `SoulData`, `SoulPrinciple` (Pydantic models, frozen).
- **Injection site:** `sidequest-server/sidequest/agents/orchestrator.py` loads `SOUL.md` via `parse_soul_md` and injects principles into agent prompts under the `soul_principles` reference label.
- **Single-zone EARLY injection.** `SoulData.as_prompt_text()` returns one set of `<important>` blocks for the EARLY zone. The original 2026-03-25 design called for a dual-zone EARLY+LATE pattern with a `<before-you-respond>` verification block; that LATE-zone block was never implemented (in either the Rust or Python tree). The narrator's Primacy guardrails serve much of the verification role.
- **Narrator exclusion (story 23-10):** `_NARRATOR_COVERED_PRINCIPLES = frozenset(["Agency", "Genre Truth"])` — these two principles are excluded from the narrator's SOUL injection because the narrator's Primacy guardrails already cover them, preventing double-injection.

Drift watch — if any of the following happens, this ADR is wrong:
- `parse_soul_md` is removed or `SOUL.md` stops being loaded at startup.
- An Anthropic SDK call bypasses the prompt_framework injection path.

The original 2026-03-25 decision is preserved below for historical context. The principle-count and per-principle gloss tables that were here have been removed in favor of pointing at `SOUL.md`, which is the canonical source.

## Context
SOUL.md is a human-readable design document that also serves as machine-parsed prompt content. It defines the principles that govern all agent behavior.

## Decision
SOUL.md is parsed at startup, cached, and injected into every agent's system prompt. The principle text itself is not duplicated in any ADR — `SOUL.md` is the single source of truth.

> **Historical context (port era).** The 2026-03-25 form of this decision specified dual-zone placement (EARLY for context-setting, LATE for verification via a `<before-you-respond>` checklist) and a Rust caching detail (`once_cell::sync::Lazy`). The dual-zone block was never built; the current Python implementation uses single-zone EARLY injection only. See the Implementation status section above.

## Consequences
- Every agent prompt includes a SOUL.md principle block in the EARLY zone.
- SOUL.md is the single source of truth for game philosophy — no ADR, prompt, or agent should re-state the principles in prose.
- Drift between SOUL.md and agent behavior is auditable through the prompt log: the principles are in the prompt verbatim.
