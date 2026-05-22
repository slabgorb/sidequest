---
parent: context-epic-60.md
workflow: tdd
---

# Story 60-1: Stop cache-writing the volatile game_state snapshot segment — reposition cache_control breakpoint

## Business Context

A 2026-05-21 `tea_and_murder/glenross` playtest showed **~77% of per-narrator-call
cost is cache_write, not work** (~$0.046 of a ~$0.059 call). The narrator places a
`cache_control` breakpoint after the volatile `game_state` snapshot, so a ~12k-token
segment is re-written to the 5-minute cache every turn and never read back (it
mutates each turn → guaranteed cache miss). The stable genre prefix (~11,168 tokens)
caches and reads correctly; only the snapshot breakpoint thrashes. Removing that
wasted write roughly halves per-turn cost. Cost savings scale linearly with playtest
hours, directly serving the playgroup's ability to play longer sessions affordably
(SOUL: *Cost Scales with Drama*).

## Technical Guardrails

- **Breakpoint placement, not size reduction.** This story does NOT slim the
  snapshot (that's ADR-110 / archived 57-5). It moves the volatile `game_state`
  snapshot to sit *after* the last `cache_control` breakpoint so it rides as plain
  input ($3/Mtok) instead of a re-written cache segment ($3.75/Mtok, wasted).
- **Preserve the stable-prefix cache.** The genre/system stable prefix MUST keep
  its breakpoint and continue to produce `cache_read>0` every turn. Do not collapse
  or move that breakpoint.
- **Key files (server):** `sidequest/agents/tooling_protocol.py` and
  `sidequest/agents/anthropic_sdk_client.py` (cache_control assembly + SDK call),
  `sidequest/agents/prompt_framework/bucket.py` (zone bucketing),
  `sidequest/agents/orchestrator.py` (snapshot injection).
- **OTEL is the lie-detector.** `narrator.sdk.usage` already logs `cache_read` /
  `cache_write` / `cost_usd`. Prove the fix with the span delta — no asserting
  savings without the numbers (CLAUDE.md OTEL principle).
- **No silent fallbacks / no stubbing** (CLAUDE.md). If the breakpoint can't be
  cleanly repositioned, fail loud / surface it — don't add a guard that hides it.
- **Tool-loop iterations:** the waste also appears on each tool-use iteration
  (iter=2/3 re-write the growing tail). Verify the fix holds across a multi-iteration
  turn, not just iter=1.

## Scope Boundaries

**In scope:**
- Reposition the `cache_control` breakpoint(s) so the volatile `game_state`
  snapshot is no longer inside a cached/re-written segment.
- A test (and/or playtest hook) capturing `cache_creation_input_tokens` /
  `cache_read_input_tokens` (or the `narrator.sdk.usage` `cache_write`/`cache_read`
  fields) before/after to prove steady-state `cache_write≈0`.
- The mandatory wiring test: prove the repositioned assembly is the one actually
  sent to the SDK on a real turn (not just constructed in isolation).

**Out of scope:**
- Snapshot field pruning / diff-with-anchor (ADR-110, archived 57-5).
- Promoting additional static genre sections into the Stable zone (ADR-112,
  archived 57-3).
- Any model-routing or verbosity change.
- Multiplayer fan-out cost (separate concern).

## AC Context

1. **Volatile snapshot is not cache-written.** On a steady-state turn (turn ≥ 2,
   warm session), `narrator.sdk.usage` shows `cache_write≈0` for the snapshot
   segment — the only cache write per session is the once-per-session stable
   prefix. Before: `cache_write` 12,281–12,456 every call. After: ~0 on
   steady-state turns.
2. **Stable prefix still caches.** `cache_read>0` (≈ the stable prefix, ~11k) is
   still hit on every turn ≥ 2. The fix must not break stable-zone caching.
3. **Holds across the tool loop.** A multi-iteration turn (iter 2/3) does not
   re-introduce a per-iteration snapshot cache write.
4. **Cost drops materially.** Per-call `cost_usd` on steady-state turns falls by
   roughly the wasted-write share (target ~40–50% reduction at the observed
   token sizes).
5. **OTEL evidence captured.** A deterministic test asserts the SDK call's
   `system=`/messages assembly places the snapshot after the last `cache_control`
   marker (proxy evidence acceptable if live cache metadata isn't assertable),
   AND a playtest run shows the `cache_write` delta in the GM panel / Jaeger.
6. **Wiring test present.** At least one test proves the repositioned assembly is
   reachable from the real narrator turn path, not only unit-constructed.
