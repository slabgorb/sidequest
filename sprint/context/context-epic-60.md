# Epic 60: Narrator Token & Cost Budget — Cache-Write Efficiency

## Overview

Continuation of archived epic 57 (Narrator Prompt Token Reduction). A live
`tea_and_murder/glenross` playtest on 2026-05-21 surfaced that the dominant
component of per-narrator-call cost is **cache_write, not actual work**: a
~12k-token cache breakpoint is re-written to the 5-minute prompt cache on every
turn (and every tool-loop iteration) for the volatile `game_state` snapshot,
which mutates each turn and is therefore never read back. This epic eliminates
that wasted cache-write premium so cost tracks narrative weight (SOUL: *Cost
Scales with Drama*) instead of bleeding on cache churn.

**Priority:** P2
**Repo:** server
**Stories:** 1 (3 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-110 Game-State Snapshot Slimming** (`docs/adr/110-game-state-snapshot-slimming.md`) | Snapshot size reduction — complementary lever (reduces *what* is written) |
| **ADR-112 Genre Prose Cache Promotion** (`docs/adr/112-genre-prose-stable-cache-promotion.md`) | Stable-zone `cache_control` placement; mutability rubric (always-fire+static promotes, conditional/volatile defers) |
| **ADR-101 Anthropic SDK as Narrator Backend** (`docs/adr/101-*.md`) | Phase D stable-zone caching; `system=` array assembly with `cache_control` |
| **ADR-098 Stateless Narrator Turns** (`docs/adr/098-*.md`) | Bounded per-turn prompts — the volatile snapshot is the per-turn payload |
| **Archived epic 57** (`sprint/archive/epic-57.yaml`) | Parent effort; 57-3 (cache promotion) and 57-5 (snapshot slimming) overlap but target size, not breakpoint placement |

## Background

Epic 57 ("Narrator Prompt Token Reduction") was archived `done` on 2026-05-20,
but its cost-reduction stories 57-3 (promote static genre prose into the Stable
cached zone, ADR-112) and 57-5 (game_state snapshot slimming, ADR-110) remained
unfinished. The 2026-05-21 playtest gave concrete numbers that re-open the cost
question from a different angle.

**Observed signature (7 calls, single clean stack):**
- Total ~$0.41; **~$0.059 per call**, of which **~$0.046 is cache-write premium**.
- `cache_read` stays flat at the stable genre prefix (~11,168 tokens) — that
  segment caches correctly and is read on every call.
- `cache_write` churns **12,281–12,456 tokens on every call**, all to the 5-minute
  TTL, all attributable to a *second* breakpoint covering the volatile snapshot.
- Because the snapshot differs next turn, that write is never read back: you pay
  the 1.25× cache-write premium ($3.75/Mtok on Sonnet) for a guaranteed miss.

This is distinct from 57-3/57-5. Those reduce the *size* of cached/written
content. This epic is about **breakpoint placement**: a `cache_control` marker
should only sit on content that will be *read* again within the TTL. Putting one
after the mutating snapshot converts cheap plain input ($3/Mtok) into a more
expensive wasted write ($3.75/Mtok) with zero downstream benefit. Cost savings
scale linearly with playtest hours, so the lever grows as the group plays more.

## Technical Architecture

The narrator prompt is assembled into an Anthropic SDK `system=` block array
where selected segments carry `cache_control: {type: ephemeral}` markers. Each
marker defines a cache breakpoint; the API caches the prefix up to that point.

**Key files (server):**

| File | Role |
|------|------|
| `sidequest/agents/anthropic_sdk_client.py` | SDK call site; emits `narrator.sdk.usage` (input/output/cache_read/cache_write/cost) — the OTEL lie-detector for this work |
| `sidequest/agents/tooling_protocol.py` | Tool-use protocol; builds system blocks + `cache_control` placement |
| `sidequest/agents/prompt_framework/bucket.py` | Section bucketing (Stable / Valley / Recency zones) that decides which segments are cacheable |
| `sidequest/agents/orchestrator.py` | Per-turn prompt construction; injects the volatile `game_state` snapshot |

**Target behaviour:** the stable genre/system prefix keeps its breakpoint
(written once per session, read every turn). The volatile `game_state` snapshot
moves *after* the last cache breakpoint so it rides as plain input — no per-turn
write. Steady-state `cache_write` should drop toward ~0 (only the once-per-session
stable write remains), while `cache_read` continues to hit the stable prefix.

**Verification (OTEL, per CLAUDE.md OTEL principle):** `narrator.sdk.usage` already
logs `cache_read` / `cache_write` per call. Success is measurable directly: after
the fix, steady-state turns show `cache_write≈0` and `cache_read>0`, and per-call
cost drops materially. The GM panel / Jaeger stream is the lie-detector — no
"winging it" claim of savings without the span delta.

## Cross-Epic Dependencies

**Depends on:**
- None hard. ADR-101 Phase D stable-zone caching is live; the `cache_control`
  plumbing it provides is what this epic re-targets.

**Depended on by:**
- None. Pure cost optimization — no downstream story consumes its output.

**Related (not blocking):**
- Archived epic 57, stories 57-3 (ADR-112 cache promotion) and 57-5 (ADR-110
  snapshot slimming) — complementary size-reduction levers. If those resume,
  coordinate breakpoint placement so the two efforts don't re-introduce a
  volatile-segment write.
