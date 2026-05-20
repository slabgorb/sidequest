# Narrator Cache Cost Reduction — Design Spec

**Date:** 2026-05-20
**Author:** Architect (Major Margaret Houlihan)
**Status:** Draft — pending implementation
**Related ADR:** [ADR-101](../../adr/101-anthropic-sdk-as-narrator-backend.md) (amendment, no superseding ADR required)

## Problem

The narrator path is paying for a ~15K token cache write **every turn**. Per the Anthropic console dashboard (May 19 1PM – May 20 4AM, 6h window):

| Bucket | Tokens | Share |
|--------|--------|-------|
| Cache read | 53K | 32% |
| Cache write (5m) | 85K | **51%** |
| Cache write (1h) | 11K | 6% |
| Uncached | 17K | 10% |

Per-request typical narrator turn: `Input: 279 / Cache Read: 10,639 / Cache Write (5m): 15,225 / Cache Write (1h): 0`.

Cost per turn: **~$0.06 per iter × 2 iters ≈ $0.12/turn**, ~85 turns/session ≈ **$10/session**, of which roughly 75% is write cost on a block that should be cached at 1h but isn't.

The fix this spec covers: drive the 5m share of cache writes toward zero by giving the **tools array** an explicit 1h cache marker, and add the instrumentation that proves the fix worked.

## Non-Goals

This spec is **cache hygiene only.** Out of scope (intentionally):

- Drama-based model routing (Haiku for boring turns).
- Promoting ADR-110 (prompt slimming) from deferred.
- Cross-session cache prefix sharing.
- Anthropic Admin API integration / `metadata.user_id` A/B harness — the existing Anthropic console dashboard IS the baseline; the next playtest's dashboard is the comparison.
- Env-var profile switching for runtime rollback. Cache markers are a one-commit revert.

## Investigation Summary

Direct evidence:

- **Account is enrolled in the `extended-cache-ttl-2025-04-11` beta.** Dashboard shows 11K of writes already landing in the 1h bucket, which is impossible without enrollment.
- **The narrator's `system_blocks[0]` IS being cached at 1h correctly.** `cache_read = 10,639` every warm turn matches its size; it never re-writes.
- **A second cache prefix is being created mid-tool-loop and lands in 5m by default.** Evidence: on iter=3 of multi-tool turns, `cache_read` jumps from 10,639 to ~25,591 — that's the 10,639 stable block plus a ~15K prefix that was written during iter=1 or iter=2 of the same turn. The ~15K prefix is consistent in magnitude with the tools array.
- **Tool definitions are ~7,681 tokens** (measured: 30,727 JSON chars across 27 tools, 4 chars/token). Plus messages and assistant tool-use blocks added during tool dispatch, the ~15K figure tracks.
- **The current code does not mark the tools array as cacheable** (`_build_tools_array` returns plain entries without `cache_control`).

Working hypothesis: Anthropic creates an implicit cache prefix covering the tools array (and possibly the assistant tool-use / user tool-result blocks added mid-loop) when prompt caching is active elsewhere in the request. That implicit prefix has no `ttl` override, defaulting to 5m. **The fix is correct under either interpretation:** if the tools array IS the 5m-defaulting prefix, an explicit 1h marker on the last tool entry converts it to 1h. If the 5m writes are coming from some other unmarked region, the explicit tools marker is still correct on its own merits (tools are byte-stable and belong in long-TTL cache), and the new `system_block_sizes_json` telemetry will reveal whatever the actual culprit is so a follow-up PR can address it.

## Architecture

The narrator's cacheable surface becomes a documented **four-region layout**:

| Region | Source | Cache | TTL | Why |
|--------|--------|-------|-----|-----|
| **Tools** | `_build_tools_array` | new | 1h | 27 stable definitions (~7,681 tokens) currently auto-cached at 5m. |
| **Stable** (Primacy + Early) | `system_blocks[0]` | existing | 1h | SOUL, identity, guardrails (~10,639 tokens). |
| **Valley** | `system_blocks[1]` | none | — | Per-turn drift (narrator vocabulary). |
| **Late + Recency** | `system_blocks[2]` | none | — | Per-turn drift (genre transition hints). |

This is an **ADR-101 amendment**, recorded inline in that ADR's history section. No new ADR required. Regions 3 and 4 stay uncached — that's the deliberate ADR-101 Phase D Task 6 design (zone-aligned cache blocks) and isn't being changed.

## Components

### 1. `AnthropicSdkClient._build_tools_array` (`sidequest-server/sidequest/agents/anthropic_sdk_client.py`)

Add `cache_control: {"type": "ephemeral", "ttl": self.cache_ttl}` to the last entry of the returned list.

- TTL inherits `self.cache_ttl` (the same env-configured value the system marker uses) — no parallel config.
- If `tools` is empty (only in test fixtures), skip the marker. Best-effort opt-in, no exception.

### 2. `AnthropicSdkClient.complete_with_tools` usage extraction

After reading the existing `cache_creation_input_tokens` aggregate, read the per-TTL breakdown:

```python
cache_creation = getattr(usage, "cache_creation", None)
cache_write_5m = int(getattr(cache_creation, "ephemeral_5m_input_tokens", 0)) if cache_creation else 0
cache_write_1h = int(getattr(cache_creation, "ephemeral_1h_input_tokens", 0)) if cache_creation else 0
```

These flow into new optional fields on `ToolingResult`:
- `cached_input_write_5m_tokens: int = 0`
- `cached_input_write_1h_tokens: int = 0`

Per-iter log line gains `5m=N 1h=N` columns alongside the existing `cache_write=N`.

### 3. Orchestrator span attribution (`sidequest-server/sidequest/agents/orchestrator.py`)

In the narration turn span attribute block, alongside the existing `narration.turn.cache_write_tokens`, add:

- `narration.turn.cache_write_5m_tokens`
- `narration.turn.cache_write_1h_tokens`
- `narration.turn.system_block_sizes_json` — small JSON `{"stable": N, "valley": N, "recency": N, "tools": N}` carrying the per-block size at compose time (token estimate via `len(text) // 4`, matching the project's existing approximation convention)

The GM panel reads `narration.turn.*` via the existing OTEL pipeline (ADR-103). New attributes appear automatically; no panel code change required for this spec.

### Touched Files

| File | Change |
|------|--------|
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` | ~15 lines added |
| `sidequest-server/sidequest/agents/tooling_protocol.py` | 2 new optional fields on `ToolingResult` |
| `sidequest-server/sidequest/agents/orchestrator.py` | ~5 lines in span-attribution block |
| `sidequest-server/tests/agents/test_anthropic_sdk_client.py` | New test cases |
| `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` | New assertions on the existing wiring test |
| `docs/adr/101-anthropic-sdk-as-narrator-backend.md` | Inline amendment documenting the four-region layout |

## Data Flow

Per-turn happy path:

```
Orchestrator.build_narrator_prompt
  composes 3 system blocks + tools registry
        |
        v
AnthropicSdkClient.complete_with_tools(system_blocks, messages, tools)
  _build_system_array:  system_blocks[0] gets cache_control(ttl=1h)   [existing]
  _build_tools_array:   tools[-1]        gets cache_control(ttl=1h)   [new]
  extra_headers:        anthropic-beta: extended-cache-ttl-2025-04-11 [existing]
        |
        v
sdk.messages.create(...) returns response.usage with:
   cache_read_input_tokens
   cache_creation_input_tokens         (aggregate)
   cache_creation.ephemeral_5m_input_tokens   [new read]
   cache_creation.ephemeral_1h_input_tokens   [new read]
        |
        v
Per-iter log:        narrator.sdk.usage ... 5m=N 1h=N
ToolingResult:       cached_input_write_5m_tokens, cached_input_write_1h_tokens
        |
        v
Orchestrator span attribution:
   narration.turn.cache_write_tokens        (aggregate, existing)
   narration.turn.cache_write_5m_tokens     [new]
   narration.turn.cache_write_1h_tokens     [new]
   narration.turn.system_block_sizes_json   [new]
```

## Success Criteria

Observable predictions, verified by the Anthropic console dashboard during the next playtest:

1. `cache_write_1h` >> `cache_write_5m` on every turn (today's ratio is inverted: 85K:11K over 6h).
2. `cache_read` rises from ~10,639 to ~18,000+ on warm turns (stable block + tools).
3. `cache_write_1h` on warm turns approaches zero (both regions established earlier in the session).
4. Cold start: one turn pays a ~18K 1h write; every warm turn pays ~0 in writes.

If all four hold, the fix worked. If they don't, `narration.turn.system_block_sizes_json` reveals which region is drifting.

## Error Handling

| Failure | Behavior | Rationale |
|---------|----------|-----------|
| SDK version returns no `cache_creation` breakdown object | `5m=0 1h=0` in logs, aggregate still correct | Older SDKs (<0.51) don't expose the breakdown; fail-quiet-but-visible, not silent fallback. We're on 0.102.0 which does expose it. |
| `tools == []` (test fixtures only) | Skip the marker, no exception | Marker is best-effort opt-in. Production has 27 tools registered at startup. |
| Beta header rejected by API | Request fails, error surfaces | Unchanged from current behavior. No silent fallback to 5m. |
| `system_blocks == []` | Existing code raises; unchanged | Narrator path never sends empty system; an empty list is a real bug worth surfacing. |

**Explicitly NOT done:**

- No retry-with-5m on cache-related errors. If 1h ever stops working, we want to see it, not paper over it.
- No production-code assertion that the cache hit. Dashboard and OTEL panel are the lie detector.

## Testing

Four new unit tests, all in `sidequest-server/tests/agents/`:

1. **`test_anthropic_sdk_client.py` — last tool gets cache_control marker.** Stub SDK records the request payload. With three tools, assert `tools[-1]` has `cache_control == {"type": "ephemeral", "ttl": "1h"}` and `tools[0..-2]` do not. With `SIDEQUEST_ANTHROPIC_CACHE_TTL=5m`, assert the marker carries `ttl: "5m"` (verifies TTL inheritance — no parallel config).
2. **`test_anthropic_sdk_client.py` — empty tools array skips marker without raising.** `tools=[]` produces a request with `tools: []`, no exception.
3. **`test_anthropic_sdk_client.py` — 5m/1h breakdown plumbed into `ToolingResult`.** Stub SDK usage with breakdown fields populated; assert they flow through. Sibling test with no `cache_creation` attribute asserts both fields default to 0 without raising.
4. **`test_cache_ttl_prefix_and_otel.py` (extend existing) — orchestrator emits new span attributes.** Existing test already protects byte-stability of `system_blocks[0]`. Add: assert the narration turn span carries `narration.turn.cache_write_5m_tokens`, `narration.turn.cache_write_1h_tokens`, and `narration.turn.system_block_sizes_json` with the expected key set.

**Deliberately NOT tested:**

- That the Anthropic API actually honors the 1h marker. External dependency. Dashboard verifies.
- Narration quality before/after. Out of cache-hygiene scope.
- Cache hit rate improvement. Dashboard verifies.

The extended `test_cache_ttl_prefix_and_otel.py` serves as the wiring test per CLAUDE.md — proving the orchestrator's narration turn calls `complete_with_tools` with the right shape AND that the new span attributes land at the OTEL surface.

## Rollback

Revert the commit. Cache markers are a one-line change in `_build_tools_array`; behavior returns to pre-fix immediately.

## Open Questions

None at spec time. If the `system_block_sizes_json` diagnostic surfaces drift in the supposedly-stable Primacy+Early zone (e.g. a timestamp leaking in), that becomes a **separate follow-up PR** with its own spec — not folded into this one.
