---
parent: context-epic-61.md
workflow: tdd
---

# Story 61-20: Reduce per-turn volatile-tail write volume (option b — zone-promote session-static Valley content into the 1h prefix)

## Business Context

This story finishes what **61-19 started**. 61-19 diagnosed the cache-write churn
(of Jade's `perseus_cloud` session 894's $1.567 cost, **73% was cache_write** of a
~9.7k-token volatile tail written to the 1h tier every turn and invalidated after one
read) and applied the **TTL-tier correction**: it stopped writing the volatile tail at
1h. That halved the *price* of the write but did **not** reduce the *volume* — the
~9.7k tail is still written every turn (now at 5m/1.25× instead of 1h/2×). 61-19's
AC1 (<2k/turn), AC2 (≤$0.05/turn), and AC3 (flat at 50 turns) therefore remain open.

61-20 closes them via **option (b)** from the 61-19 deferred decision: amortize the
**session-static** content currently riding the volatile Valley zone — the
`AVAILABLE CULTURES` block, magic `hard_limits`, and the `monster_manual` — up into
the **cached 1h stable prefix**, where it is written once and read every subsequent
turn. What remains in the 5m volatile tail is only the genuinely-per-turn delta
(~1k tokens). That is the move that actually brings per-turn cache_write under 2k,
per-turn cost to ≤$0.05, and holds the flat-cost invariant at 50 turns.

Why it matters to the playgroup: this is the residual blocker on epic 61's
"flat per-turn cost" invariant. Jade and Sebastien run long sessions (the 140-turn
`coyote_star` run is the reference); this fix roughly halves narrator spend again on
top of 61-19 with **zero** change to narration content or player-facing behavior — it
is a cache-zone placement correction, not a prompt-content change.

## Technical Guardrails

**Read `sprint/context/context-story-61-19.md` first — and `sprint/archive/61-19-session.md`.**
61-19's context documents the full cache mechanism (the two-marker interaction, the
prefix-cache TTL semantics, the telemetry surface) in verified file:line detail. This
story builds directly on that fix; do not re-derive it.

### The mechanism this story changes

61-19 left three `CacheableBlock`s in `orchestrator.py` (~3733-3737):
`system_blocks[0]` (stable identity/voice/SOUL/tools) at `cache=True` → 1h, and
Valley + Recency at `cache=False` carrying the per-turn drift. The problem 61-20
fixes: the Valley zone still carries **session-static** content that does not change
turn-to-turn — `AVAILABLE CULTURES`, magic `hard_limits`, `monster_manual` — yet it
is re-serialized into the volatile (5m) tail every turn. ADR-112 (prose-cache
promotion) and 61-10's zone-promotion are the sanctioned mechanism to move those
session-static sections into the **stable, 1h-cached** prefix so they amortize.

### Key files (verified via 61-19 context)

| Path | Role in 61-20 |
|------|---------------|
| `sidequest-server/sidequest/agents/orchestrator.py` `~3733-3737` | `CacheableBlock` system-array construction — where session-static Valley sections get promoted into the stable (cache=True/1h) prefix |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `_build_system_array` (~1014-1026) | Where `cache=True` blocks get their 1h TTL marker — the destination for promoted content |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `_build_messages_payload` (~924-1015) | The user-message marker 61-19 re-tuned — verify the promotion does not re-introduce a 1h write on the tail |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `:320-431` | `narrator.sdk.usage` emit — AC5's stable-prefix-write vs tail-write span axis (may already be landed by 61-19; verify and extend, do not duplicate) |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `:339-342` | **Residual stale comment to fix** (named in the story) — bring it in line with the post-61-19/61-20 marker behavior |
| `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` | Existing cache-TTL/byte-stability gate — sibling test home; new tests co-locate here |

### Constraints / what NOT to break

- **Do not re-zone genuinely-volatile content.** Only **session-static** sections
  (AVAILABLE CULTURES, magic hard_limits, monster_manual) move to the 1h prefix.
  The slimmed snapshot, lore/recency, and per-turn drift STAY in the 5m tail. Moving
  a turn-changing field to 1h would re-create the exact churn 61-19 fought.
- **Do not regress 60-7 or 61-19.** The within-turn tool loop (iter=1 write → iter=2+
  read) must still hit cache. The stable prefix stays 1h; the volatile tail stays 5m
  (or uncached). This story changes *what rides which zone*, not the zones' TTLs.
- **No content change.** Narration text, tool set, and player-facing output are
  byte-identical. This is a cache-zone placement correction. SOUL "No Silent
  Fallbacks": the promotion must be explicit and asserted, not a default flip.
- **session-static must be genuinely static.** If AVAILABLE CULTURES / hard_limits /
  monster_manual can change mid-session (e.g., a new culture enters scope, MM grows),
  promoting them to 1h re-introduces churn. Verify they are session-constant before
  promoting; if any can drift, that section stays in the tail or needs a sub-split.
- **OTEL-observability principle (CLAUDE.md):** the stable-prefix-write vs tail-write
  span (AC5) must be GM-panel-visible and emitted from the production turn path so a
  future re-promotion of a growing field into the tail is catchable.

## Scope Boundaries

**In scope:**
- Promote the session-static Valley sections (AVAILABLE CULTURES block, magic
  `hard_limits`, `monster_manual`) into the cached 1h stable prefix via ADR-112/61-10
  zone-promotion.
- Bring per-turn cache_write to **<2k** at steady state (61-19 AC1).
- Bring per-turn cost to **≤$0.05** on Sonnet at steady state (61-19 AC2).
- Hold the flat-cost invariant **at 50 turns** within 20% of warmup (61-19 AC3).
- Add a live-validation probe confirming the steady-state per-turn write/cost.
- Fix the residual stale comment at `anthropic_sdk_client.py:339-342`.
- Ensure the AC5 stable-prefix-write vs tail-write span reflects the new zoning
  (extend the 61-19 span if needed; do not duplicate).

**Out of scope:**
- The TTL-tier correction itself (done in 61-19).
- Further snapshot slimming (61-2, done) — this is a *zone placement* fix on
  already-slimmed content.
- Changing which content is session-static vs volatile beyond the three named
  sections — broader re-zoning is ADR-112 territory, not this story.
- Narration quality, tool set, or player-facing output changes.
- A live 50-turn session as the *primary* AC3 gate — assert via a bounded
  telemetry/simulation harness (mirror the 61-19 approach). A live probe is a
  confirmation, not the red gate.

## AC Context

These ACs are inherited from 61-19 (the story closes 61-19 AC1/AC2/AC3). The YAML
carries no separate AC list; treat the following as the testable surface.

### AC1 — Per-turn cache_write < 2k at steady state
**Pass condition:** Measured via `narrator.sdk.usage cache_write_tokens` on **iter=1**
of a post-warmup turn (after turn ~5), the volatile-tail write is **< 2,000 tokens**.
61-19 left this at ~9.7k (now at 5m tier). After promotion, the tail carries only the
~1k per-turn delta.
**Edge cases:** distinguish iter=1 from iter=2+ (iter=2 already reuses the just-written
cache); assert on a post-warmup turn (turns 1-4 legitimately write more as the 1h
prefix forms — and turn 1 now writes MORE into the prefix because of the promotion,
which is the intended one-time cost). AC1 is about the **recurring tail write**, not
the one-time prefix write.
**Test approach:** Unit-test the system-array + payload builder — assemble a
representative payload, assert the promoted sections carry the 1h `cache_control`
marker (stable prefix) and the volatile tail is <2k. Integration: a stubbed-SDK turn
loop asserting iter=1 tail write < 2k at steady state.

### AC2 — Per-turn cost ≤ $0.05 at steady state (Sonnet, 17+-turn solo)
**Pass condition:** `session.cost_running_total / turn_count` ≤ $0.05 on a 17+-turn
solo Sonnet session at steady state.
**Edge cases:** the cost delta must trace to the **zone move** (one-time 1h prefix
write amortized + tiny recurring 5m tail), not a content reduction (content is
unchanged). Verify `compute_cost_usd` prices the amortized 1h prefix and the 5m tail
correctly (per-TTL pricing landed in 60-4).
**Test approach:** Drive `compute_cost_usd` with the post-promotion token profile
(large one-time 1h prefix written turn 1, ≤1k 5m tail per turn) over 17 turns and
assert the *average* per-turn cost clears ≤$0.05. Avoids a live billed session.

### AC3 — Flat-cost invariant holds at 50 turns (within 20% of warmup steady-state)
**Pass condition:** At turn 50, per-turn cost is within 20% of warmup steady-state —
no linear creep.
**Edge cases:** the risk is that a promoted section is **not actually static** and the
1h prefix grows or re-writes mid-session, or the tail still grows. AC3 guards both.
**Test approach:** Telemetry/simulation harness (mirror 61-19 / 60-5): synthesize
per-turn profiles for turns 5→50 with the promoted-prefix + bounded-tail shape and
assert the per-turn cost series is flat (max within 20% of turn-5 baseline). Do NOT
require a live 50-turn session for the red gate.

### Live-validation probe (story-named deliverable)
A probe (telemetry read or short bounded live run) confirming the steady-state per-turn
write < 2k and cost ≤ $0.05 against the real pack/prompt. Confirmation, not the red gate.

### Stale-comment fix (story-named deliverable)
`anthropic_sdk_client.py:339-342` carries a comment that no longer matches the
post-61-19/61-20 marker behavior. Correct it to describe the actual zoning. Low-risk
but explicitly in scope — do it in this PR (don't leave it for "later").

### AC5 carry-over — stable-prefix-write vs tail-write span stays accurate
61-19 (AC5) added a span splitting cache_write into stable-prefix-write vs tail-write.
After promotion the split shifts (more in the one-time prefix, less in the recurring
tail). Verify the span still decomposes correctly and is emitted from the production
turn path (CLAUDE.md "Every Test Suite Needs a Wiring Test"). Extend, don't duplicate.

## Assumptions

- **61-19 is merged and its TTL-tier correction is live.** This story stacks on it
  (session `Stack Parent: 61-19`). The volatile tail currently writes at 5m, not 1h.
  *If 61-19's fix is not actually in `develop`,* the baseline differs — verify before RED.
- **AVAILABLE CULTURES, magic hard_limits, and monster_manual are session-static.**
  The whole option-(b) economics depend on this. *If any can change mid-session,*
  promoting it to 1h re-introduces churn — log a Design Deviation and keep that section
  in the tail or sub-split it. Verify against live snapshot construction before promoting.
- **ADR-112 / 61-10 zone-promotion is the sanctioned mechanism** for moving
  session-static prose into the stable 1h prefix. *If 61-10 is not landed or the
  promotion seam differs,* confirm the actual seam with architect at spec-check.
- **`compute_cost_usd` prices the amortized 1h prefix + 5m tail correctly** (per-TTL
  split landed in 60-4). *If wrong,* the cost function needs adjustment — log a deviation.
- **The payload builders are pure functions** over `system_blocks` + `running_messages`
  (verified in 61-19), so marker-placement assertions are testable offline without a
  live Anthropic call. This is what makes the RED phase tractable.
