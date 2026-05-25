# Epic 60: Narrator Token & Cost Budget — Cache-Write Efficiency

## Overview

Continuation of archived epic 57 (Narrator Prompt Token Reduction). A 2026-05-21
`tea_and_murder/glenross` playtest surfaced ~$0.046/call of wasted `cache_write`.
The original framing blamed the `game_state` snapshot; reading the code (and the
OTEL Prompt zone-breakdown at T5 on 2026-05-22) **disproved that** and pinned the
real cause. This epic builds the observability to *see* the cost, confirms the
root cause with those eyes, then fixes it — in that order (you cannot reposition
what you cannot see drift).

**Priority:** P2
**Repo:** server (60-2 also touches ui)
**Stories:** 3 active (60-2, 60-3, 60-4), split from the original 60-1 (status: split)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-101 Anthropic SDK Narrator Backend** (`docs/adr/101-*.md`) | Phase D three-zone cacheable layout; `system_blocks[0]` cache marker; four-region cache amendment |
| **ADR-112 Genre Prose Cache Promotion** (`docs/adr/112-*.md`) | Mutability rubric: always-fire+static promotes to Stable; **conditional/volatile must NOT** ride the cached zone (combat/chase) |
| **ADR-110 Snapshot Slimming** (`docs/adr/110-*.md`) | Snapshot size — *complementary, not this epic* |
| **ADR-090 / ADR-103 OTEL** | Watcher events + GM panel; `prompt_assembled` event powering the Prompt tab |
| **Archived epic 57** (`sprint/archive/epic-57.yaml`) | 57-3 promoted static prose to Early; that re-zoning is adjacent to the bug |

## Background

> **⚠️ ROOT CAUSE CORRECTED BY STORY 60-3 (2026-05-22).** The hypothesis below
> ("three mis-zoned `state` sections churn cached block 0") was **disproved** by
> measurement. Keep this section for history, but the **authoritative** root
> cause and fix are in *Corrected root cause (60-3)* immediately after it, and in
> `sprint/archive/60-3-session.md` → "Dev Diagnosis (60-3 — FINAL)".

### The ORIGINAL hypothesis (disproved — kept for history)

The narrator prompt is assembled into Anthropic `system` blocks. Per ADR-101
Phase D (`orchestrator.py:3199-3222`):

- **`system_blocks[0]` = Primacy + Early zones, `cache=True`** — one `cache_control`
  marker at its end. ~11.7k tokens.
- `system_blocks[1]` = Valley, `cache=False`. Contains `game_state` (703 tok) and
  `world_context` — **uncached, innocent.**
- `system_blocks[2]` = Late + Recency, `cache=False`.
- tools array — byte-stable ~11k, separately cache-marked → healthy `cache_read`.

The original hypothesis: the 2026-05-22 OTEL zone-breakdown showed three
`state`-category sections (`narrator_available_confrontations`,
`trope_beat_directives`, `npc_roster`) in the **Early** zone, and assumed their
per-turn changes invalidated cached block 0 every turn.

### Corrected root cause (60-3, MEASURED — authoritative)

The three suspected sections are **User-bucket** (not in `STABLE_SECTION_NAMES`),
so `compose_split_by_zone` routes them into the **uncached** user message — they
never touch `system_blocks[0]`. The cached prefix (block 0 + tools) is **byte-stable**
across turns (digest constant; `mis_zoned` was a bucket-blind false positive).

The real cause: the narrator runs a **tool-use loop**. The first call of a turn
caches the prefix at **1h** correctly, but every **continuation call** (iter 2+,
carrying `tool_use`/`tool_result`) **re-mints the whole ~11.7k prefix at the default
5m TTL** — because the growing tool-use conversation carries no `cache_control`
breakpoint. At submit-and-wait cadence the 5m copy expires between turns, so the
prefix is re-paid every turn. The snapshot was never the cost, and neither was
zoning.

**Cost (measured, Sonnet 4.6):** current **~$0.116/turn**, of which **~$0.089 (76%)
is wasted `cache_write`** — and it fires **twice per turn** (iter 1 + iter 2 both
write), so the epic's original "~$0.046/call" under-counted by ~2×. Post-fix
estimate **~$0.035/turn** (continuations read the 1h prefix) → **~70% / ~$0.08/turn
saved**; an ~85-turn session drops **~$9.88 → ~$3.01**. (Secondary: `anthropic_cost.py`
prices 1h writes at the 5m rate, so the GM-panel cost_usd understates real 1h
billing — track in 60-4.) See the 60-3 session for the full evidence chain and
ruled-out alternatives.

### Why observability came first

Today's Prompt-tab display is built from a **separate** per-zone, char/4
*estimate* path (`orchestrator.py:2228` `prompt_assembled`), decoupled from the
real `system_blocks` and from the real API `cache_read/cache_write`
(`narrator.sdk.usage`). It can show "looks fine" while the cached prefix churns.
The bug hid for exactly this reason. So: build the eyes (60-2), confirm with them
(60-3), then fix (60-4).

## Technical Architecture

**Three-story arc:**

- **60-2 (OTEL eyes — START HERE).** Extend the existing Prompt-tab Zone Breakdown
  so it makes caching legible: mark the cache boundary (which sections ride cached
  block 0 vs uncached blocks vs tools), join the **real** API `cache_read/cache_write`
  (not estimates), emit a per-block content **digest** and show drift vs the prior
  turn, and flag `state`-category sections that landed in a cached zone. The display
  must be sourced from the **actual assembled blocks** sent to Anthropic — no
  divergent recomputation. Repos: **server + ui**.
- **60-3 (Diagnose/confirm — spike). ✅ DONE.** Using 60-2's eyes + isolated SDK
  replays, **disproved** the mis-zoned-sections hypothesis and found the real cause:
  the tool-use loop continuation re-mints the byte-stable prefix at 5m (no cache
  breakpoint on the growing conversation). Full evidence + the fix in
  `sprint/archive/60-3-session.md`. Repos: server.
- **60-4 (Fix) — RE-SCOPED by 60-3.** Do **not** re-zone state sections (they're
  User-bucket / already uncached — a no-op for cost). Instead, in
  `agents/anthropic_sdk_client.py::complete_with_tools`, add a moving
  `cache_control={"ttl":"1h"}` breakpoint on the **last continuation message**
  (the freshly-appended `tool_result`) and clear stale message-level markers so
  total breakpoints stay ≤ 4. Also fix the bucket-blind `mis_zoned` flag
  (`orchestrator.py` `_compute_zones_payload`) to AND with bucket. Success:
  continuation `cache_creation` lands in `ephemeral_1h_input_tokens` (not 5m),
  steady-state `cache_write≈0` after warmup, `cache_read>0`, per-turn cost down
  from ~$0.116 to ≤~$0.04 (~70%, measured), verified in the 60-2 display + a
  regression test. Repos: server.

**Key files:** `agents/orchestrator.py` (zone registration 1320-1460; `system_blocks`
assembly 3199-3222; `prompt_assembled` emission 2228-2306), `agents/anthropic_sdk_client.py`
(`narrator.sdk.usage`, real cache usage), `agents/prompt_framework/bucket.py`
(`STABLE_SECTION_NAMES`, zone→bucket), `sidequest-ui/src/components/Dashboard/tabs/PromptTab.tsx`.

## Cross-Epic Dependencies

**Depends on:** None hard. ADR-101 Phase D caching is live.

**Depended on by:** None.

**Related (not blocking):** Archived epic 57 (57-3 promoted prose into Early — the
adjacent re-zoning; 57-5 snapshot slimming — orthogonal size lever). 60-4 should
coordinate so re-zoning state OUT of Early doesn't fight 57-3's promotion of static
prose INTO Early — they are compatible (static stays, volatile leaves).
