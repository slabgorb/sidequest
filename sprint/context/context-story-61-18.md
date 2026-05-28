---
parent: context-epic-61.md
workflow: tdd
---

# Story 61-18: Audit CONFRONTATION_TRIGGER_CONSTRAINT dead-prose on the SDK narrator path

## Business Context

`CONFRONTATION_TRIGGER_CONSTRAINT` is the prompt guardrail that steers the narrator to
emit a `confrontation` in its `game_patch` whenever its prose describes a stake-binding
engagement (a weapon drawn, an auctioneer calling the lot, a writ served). It exists
because of a real, recurring failure mode (Pingpong 2026-05-03: narrator wrote a
textbook chase-firing beat but the patch carried `confrontation=None`) — the exact
"convincing narration with zero mechanical backing" that the OTEL lie-detector
principle and ADR-014 (Diamonds and Coal) are meant to prevent.

The concern: on the **default production backend** (Anthropic SDK, ADR-101), this
guardrail may be **dead prose** — registered nowhere, reaching the model never. The
four Recency-zone guardrails are gated behind `_maybe_register_legacy_guardrail`, which
only registers them on the legacy `claude -p` / Ollama backends. Its docstring claims
ADR-111 migrated the SDK-path guardrails to "the `tools=` array's `description` field
or the slimmed-sidecar Primacy/Stable cached prose" — **but ADR-111 is deferred**
(see the CLAUDE.md ADR index and `docs/adr/DRIFT.md`). If the migration never landed,
the SDK narrator runs with no confrontation-trigger steering at all, silently
reopening the 2026-05-03 bug class on every live session.

This is an **audit-first** story: establish ground truth on the SDK path, then either
migrate the prose to a live injection point or confirm a different subsystem now owns
confrontation triggering.

## Technical Guardrails

**Key files:**

| Path | Role |
|------|------|
| `sidequest-server/sidequest/agents/narrator_guardrails.py:55` | `CONFRONTATION_TRIGGER_CONSTRAINT` prose definition |
| `sidequest-server/sidequest/agents/narrator_guardrails.py:187` | `ALL_GUARDRAILS` tuple — the four guardrails iterated by skip-span attrs |
| `sidequest-server/sidequest/agents/orchestrator.py:1555-1583` | `_maybe_register_legacy_guardrail` — gates registration on `not isinstance(self._client, ToolingLlmClient)` (legacy only) |
| `sidequest-server/sidequest/agents/orchestrator.py:2378-2382` | The call site that would register `CONFRONTATION_TRIGGER_CONSTRAINT` (legacy path only) |
| `sidequest-server/sidequest/agents/dispatch_engagement_watcher.py` | Post-narration lie-detector — `dispatch_engagement.{subsystem}.mismatch` spans (the existing backstop) |
| `sidequest-server/sidequest/agents/intent_router.py` | IntentRouter (ADR-113) — candidate owner of confrontation triggering pre-narrator |
| `sidequest-server/sidequest/agents/subsystems/` | `run_dispatch_bank` confrontation dispatch handler |

**Verified gate behavior:** `_maybe_register_legacy_guardrail` registers a
Recency-zone `Guardrail` PromptSection **only** when `not isinstance(self._client,
ToolingLlmClient)`. The SDK client is a `ToolingLlmClient`, so on the production path
the guardrail is *not* registered into the prompt. The docstring asserts a migration
target; ADR-111 (the migration's authority) is **deferred**, so that assertion is
unverified and likely false.

**Patterns / constraints:**

- **No silent fallbacks (CLAUDE.md):** if confrontation triggering is genuinely
  unowned on the SDK path, that is a loud finding — do not paper over it.
- **OTEL is the lie-detector:** the deliverable must leave a span that proves whichever
  path owns confrontation triggering is actually engaging. Source-grep wiring tests are
  forbidden (CLAUDE.md "No Source-Text Wiring Tests") — use the
  `dispatch_engagement_watcher` mismatch span or a fixture-driven behavior test that
  fires a real turn and asserts the emitted `confrontation`.
- This guardrail is a **co-design with the validator** (`confrontation_intent_validator`
  emits `confrontation.intent_mismatch`). Audit whether that validator still fires on
  the SDK path too — the prose steers, the validator catches; losing the prose shifts
  all weight onto the catch.

## Scope Boundaries

**In scope:**
- Determine empirically whether `CONFRONTATION_TRIGGER_CONSTRAINT` (or equivalent
  steering) reaches the model on the SDK path: trace tool descriptions, cached/Stable
  prose sections, and IntentRouter dispatch.
- Resolve to exactly one of:
  - **(a) Migrate** the prose to a live SDK-path injection point (tool `description`
    or cached Primacy/Stable prose) per ADR-111's intent, and add an OTEL/behavior
    test proving it reaches the narrator; **or**
  - **(b) Confirm** the IntentRouter (ADR-113) + dispatch bank now owns confrontation
    triggering on the SDK path, document that the prose guardrail is intentionally
    legacy-only, and add a test pinning the SDK-path owner.
- Update the `_maybe_register_legacy_guardrail` docstring to match reality (it
  currently cites a migration that may not exist).

**Out of scope:**
- Reviving the legacy `claude -p` / Ollama backends (they are opt-in non-default).
- Re-implementing the confrontation engine itself (ADR-033 / `ruleset/native.py`).
- The other three guardrails (`npc_intro_visual`, `npc_extraction`, `location_patch`) —
  same dead-prose risk applies, but this story scopes to confrontation only. Note any
  finding about the others as a follow-up.
- Un-deferring ADR-111 wholesale — this story lands the confrontation slice and records
  whether the broader ADR-111 migration is still warranted.

## AC Context

**AC-1 — Ground truth established.** Drive a turn through the live SDK path whose prose
describes a stake-binding engagement (e.g. a `space_opera` ship_combat trigger) and
capture whether the narrator receives any confrontation-trigger steering. Evidence is
the actual assembled prompt / tool array, not inference. Record the finding.

**AC-2 — Owner resolved with a test.** Whichever of (a)/(b) is chosen, a test fires a
real turn through the SDK path on a trigger-bearing action and asserts the
`confrontation` is emitted (or the owning subsystem's OTEL span fires). The test must
fail if confrontation triggering regresses to dead-prose. No source-text grep
assertions.

**AC-3 — Docstring/ADR reconciled.** `_maybe_register_legacy_guardrail`'s docstring
states the true SDK-path behavior. If ADR-111 stays deferred, note that the
confrontation slice was resolved independently and update `docs/adr/DRIFT.md` /
ADR-111 accordingly.

**Edge case:** the IntentRouter spine is "structurally live but operationally under
validation" (per the server CLAUDE.md) — every dispatch in the package fires with no
confidence gating. If (b), confirm the confrontation dispatch *actually* engages on a
real trigger, not just that the handler is registered.

## Assumptions

- ADR-111 is deferred and its migration likely did **not** land — the docstring is
  aspirational. Verify before trusting either the docstring or the "Intent Router owns
  it" hypothesis.
- The `confrontation_intent_validator` (`confrontation.intent_mismatch` span) still
  runs on the SDK path and provides a post-hoc catch even if the steering prose is
  absent — confirm; if it too is dead, the gap is worse than prose-only.
- This audit may surface that all four Recency guardrails are SDK-path dead prose. If
  so, file the broader cleanup as a follow-up rather than expanding this story's scope.
