---
parent: context-epic-61.md
workflow: tdd
---

# Story 61-19: Stop 1h-cache-writing the per-turn volatile snapshot block — pays 2x write premium without amortizing

## Business Context

Epic 61 closed the **uncached-growth** hole in the narrator prompt (61-2 slimmed
the snapshot; 61-1 wired RAG). It did **not** close the **cache-write churn**
hole — the gap epic 60 explicitly punted ("Valley acquitted on cache-write
churn") and epic 61's flat-cost AC still fails on. Live forensics on Jade's
`perseus_cloud` session (session_id 894, 17 turns, narrator
`claude-sonnet-4-6`) quantify it: of $1.567 total session cost, **cache_write is
$1.144 — 73.0%** — while cache_read (the part that works) is only 15.1%. The
read side is excellent (80.5% hit ratio, 99.99% of input cache-served). The
spend is almost entirely in *writing* a ~9.7k-token volatile block into the
**1h** cache tier (2× base rate) on the first iteration of every turn, then
invalidating it next turn after a single read.

This matters to the playgroup because it is the residual blocker on the
project's "flat per-turn cost" invariant. Jade and Sebastien run long sessions
(the 140-turn `coyote_star` session is reference); at ~$0.085/turn a 140-turn
session costs ~$12 in narrator spend, ~70% of which is recoverable waste. The
fix (~$0.04/turn projected) roughly halves per-turn narrator cost with **zero**
change to narration quality, prompt content, or player-facing behavior — it is
purely a cache-tier placement correction.

## Technical Guardrails

### The mechanism (verified in live code, 2026-05-30)

The volatile tail is written at 1h via an **interaction between two correct-in-
isolation markers**:

1. **`orchestrator.py` ~3733-3737** builds the system array as three
   `CacheableBlock`s:
   ```python
   system_blocks = [CacheableBlock(text=stable_text, cache=True)]      # Primacy+Early
   system_blocks.append(CacheableBlock(text=valley_text, cache=False)) # Valley
   system_blocks.append(CacheableBlock(text=recency_text, cache=False))# Late+Recency
   ```
   Only block 0 (stable identity/voice/SOUL) is `cache=True`. Valley and
   Recency are `cache=False` — they carry the per-turn drift (slimmed snapshot,
   monster_manual, lore/recency).

2. **`anthropic_sdk_client.py:_build_system_array` (~1014)** stamps
   `cache_control={'type':'ephemeral','ttl': self.cache_ttl}` on every block
   whose `.cache` is True — so block 0 → 1h marker. Valley/Recency get **no**
   system-array marker (correct).

3. **`anthropic_sdk_client.py:_build_messages_payload` (~995-1001)** — the
   Story 60-7 fix — stamps the **newest user message's last content block** with
   `cache_control` at `self.cache_ttl` (**1h** by default, from
   `SIDEQUEST_ANTHROPIC_CACHE_TTL`, resolved ~line 177). 60-7 added this to
   override Anthropic's auto-5m default on the iter=1 tail so iter=2 reads at 1h
   instead of paying a 5m→1h displacement.

**The side effect:** Anthropic prefix-caching writes everything between the
previous breakpoint (end of `system_blocks[0]`) and the next marker (the user
message) at the *later* marker's TTL. The user-message 1h marker therefore
extends the **1h write** across `valley_text` + `recency_text` + user message —
the entire ~9.7k volatile tail. Within one turn this is fine (written iter=1,
read iter=2 seconds later). Across turns it is pure waste: the tail changes
every turn, so the 1h (2×) write is invalidated after a single read. A 5m write
(1.25×) — or no write at all — would cover the within-turn tool loop for far
less.

### Telemetry surface (verified)

- `anthropic_sdk_client.py:338-339` reads `cache_read_input_tokens` /
  `cache_creation_input_tokens` from `response.usage`.
- `:346-360` reads the per-TTL split (`cache_creation.ephemeral_5m_input_tokens`
  / `ephemeral_1h_input_tokens`) when the SDK exposes it (anthropic ≥ 0.51).
- `:419-431` publishes the `narrator.sdk.usage` watcher event with
  `cache_write_tokens` (aggregate). The event already carries the **5m/1h TTL
  split** internally but does **not** split by *which block* was written
  (stable-prefix vs volatile-tail). AC5 requires that second axis.
- `:438+` (Story 60-7) already emits a per-iter lie-detector when
  `cache_write_5m > 0 AND cache_write_1h > 0` — a sibling alarm the AC5 span
  should sit beside.

### Key files

| Path | Role in 61-19 |
|------|---------------|
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `_build_messages_payload` (~924-1015) | The user-message `cache_control` marker — primary fix surface for TTL/tier placement |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `_build_system_array` (~1014-1026) | Where `cache=True` blocks get their TTL marker |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `:320-431` | `narrator.sdk.usage` emit — AC5 span extension surface |
| `sidequest-server/sidequest/agents/orchestrator.py` `~3733-3737` | `CacheableBlock` system-array construction (stable vs volatile zoning) |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` `~149-184` | `cache_ttl` resolution from `SIDEQUEST_ANTHROPIC_CACHE_TTL` |
| `sidequest-server/tests/agents/test_cache_ttl_prefix_and_otel.py` | Existing cache-TTL/byte-stability gate — sibling test home; new tests likely co-locate here |
| `sidequest-server/sprint/archive/60-7-session.md` | The marker this story re-tunes; read before touching `_build_messages_payload` |

### Constraints / what NOT to break

- **Do not regress 60-7.** The within-turn tool loop (iter=1 write → iter=2+
  read) MUST still hit cache. The fix changes the *tier* of the volatile write,
  not its *existence*. A 5m write still covers the seconds-long tool loop.
- **Do not re-zone narration content.** This is a cache-tier placement fix, not
  a prompt-content change. `stable_text` / `valley_text` / `recency_text`
  membership stays exactly as ADR-101/112 defines it. SOUL "No Silent
  Fallbacks": any tier change must be explicit and asserted, not a default flip.
- **Stable prefix stays 1h.** `system_blocks[0]` (tools + identity/voice/SOUL)
  amortizes across turns and SHOULD keep the 1h tier — only the volatile tail
  moves.
- **OTEL-observability principle (CLAUDE.md):** the fix MUST add a GM-panel-
  visible span (AC5) splitting cache_write by block, so a future regression is
  catchable — not just a config flip.

### Deferred decision (architect, spec-check)

The story names two fix directions and says "pick per measurement":
- **(a)** Move the volatile block after the last stable breakpoint and send it
  **uncached** (plain input $3/M — cheaper than a 2× write read once).
- **(b) [story-preferred]** Split the breakpoint so only the genuinely-new tail
  (~1k tok) is written each turn while the stable session prefix is written once
  (~25k) and read thereafter. Projects ~$0.04/turn.

A pragmatic third reading of the live code is a **TTL-tier correction**: keep
the user-message marker but stamp it at **5m** for the volatile tail while the
stable prefix keeps 1h. This is the smallest-diff expression of AC4. The choice
among (a)/(b)/TTL-correction is a Dev+Architect call (touches ADR-112 prose-
cache promotion, ADR-110 snapshot slimming, ADR-098/111 bounded prompts) — TEA
tests the *observable outcomes* (ACs), not the chosen mechanism.

## Scope Boundaries

**In scope:**
- Stop writing the per-turn volatile block to the **1h** cache tier (AC1, AC4).
- Bring per-turn cache_write tokens from ~9.7k to <2k at steady state (AC1).
- Bring per-turn cost on Sonnet from ~$0.085 to ≤$0.05 at steady state (AC2).
- Hold epic-61's flat-cost invariant across 50 turns (AC3).
- Add an OTEL span splitting cache_write into stable-prefix-write vs tail-write
  (AC5).
- Confirm the 5m-vs-1h TTL choice for whatever remains cached (AC4).

**Out of scope:**
- Changing *which* content rides Valley/Recency vs the stable prefix (that is
  61-2 / ADR-112 territory).
- Further snapshot slimming (61-2 is done; this is a placement fix on the
  already-slimmed block).
- Changing narration quality, tool set, or player-facing output.
- The RAG wiring (61-1, done).
- A live 50-turn playtest as the *primary* gate — AC3 should be assertable via a
  bounded simulation/telemetry harness, not a 50-turn live session (see AC3
  context below). Live playtest validation, if wanted, is a 61-6-style follow-up.

## AC Context

### AC1 — Per-turn cache_write drops ~9.7k → <2k at steady state
**Pass condition:** Measured via `narrator.sdk.usage cache_write_tokens` on the
**first iter of a turn** (iter=1), after a turn-5 warmup, the cache_write for
the volatile tail is < 2,000 tokens. Today it is ~9,753 (the slimmed snapshot +
monster_manual + lore/recency written at 1h).
**Edge cases to test:**
- iter=1 vs iter=2+ must be distinguished — the second iter already writes only
  ~230 tok (it reuses the just-written cache); the regression lives on iter=1.
- "Steady state / after warmup" — turns 1-4 may legitimately write more as the
  session prefix forms. Assert on a post-warmup turn.
- A 5m write still counts as a *write* in the aggregate; AC1 is about the **1h**
  write volume specifically — pair with AC4's tier assertion so a fix that moves
  9.7k from 1h→5m without reducing it is not falsely credited against AC1 if AC1
  is read as "1h cache_write". Confirm with architect whether AC1 counts
  aggregate writes or 1h-tier writes; the story's "drop from ~9.7k/turn"
  framing reads as **1h-tier** writes.
**Test approach:** Unit-test the payload builder: assemble a representative
system_blocks + user message, invoke the marker logic, and assert the volatile
tail does NOT carry a 1h `cache_control` marker (and carries <2k tokens at 1h).
Integration: a stubbed-SDK turn loop asserting the emitted
`narrator.sdk.usage` 1h write on iter=1 < 2k.

### AC2 — Per-turn cost ~$0.085 → ≤$0.05 at steady state (Sonnet, 17+ turn solo)
**Pass condition:** `session.cost_running_total / turn_count` ≤ $0.05 on a
17+-turn solo Sonnet session at steady state.
**Edge cases:** cost is dominated by cache_write tier — assert the cost delta
traces to the tier change, not to a content reduction (content is unchanged).
Verify `compute_cost_usd` bills 5m at 1.25× and 1h at 2× (the per-TTL split
landed in 60-4) so a tier move is correctly re-priced.
**Test approach:** Drive `compute_cost_usd` with the pre-fix token profile
(9.7k @ 1h) vs post-fix (≤2k @ 1h, remainder @ 5m or uncached) and assert the
per-turn delta clears the ≤$0.05 bar. Avoids needing a live billed session.

### AC3 — Flat-cost invariant holds at 50 turns (within 20% of warmup steady-state)
**Pass condition:** At turn 50, per-turn cost is within 20% of the warmup
steady-state per-turn cost — no linear creep from a re-written growing cache.
**Edge cases:** This is the epic-61 invariant. The risk is that the volatile
tail *still grows* (even at 5m or uncached) — AC3 guards that the **tier fix**
didn't merely move the growth to a cheaper tier while leaving it unbounded.
**Test approach (important — do NOT require a live 50-turn session):** Use a
telemetry/simulation harness: synthesize per-turn token profiles for turns
5→50 with a realistic (already-slimmed, bounded) volatile tail and assert the
per-turn cost series is flat (max within 20% of the turn-5 baseline). Mirror the
60-5 / 24-8 validation-harness pattern but bounded. If a live session is used at
all, it is a follow-up validation chore, not this story's red gate. **Confirm
the harness shape with architect at spec-check.**

### AC4 — No volatile (changes-every-turn) block written to 1h tier; uncached or 5m, justified by a read-count assertion
**Pass condition:** The volatile tail is provably written to either uncached
input or the **5m** tier — never 1h. Justified by a **read-count assertion**:
the block is read ≤1 time before invalidation (so 1h's 2× write premium can
never amortize).
**Edge cases:** This is the load-bearing AC. A config flag alone is
insufficient (per SM watch-item) — the test must assert the actual
`cache_control` marker placement on the assembled payload, not just that an env
var is set. Assert: (1) the user-message / volatile breakpoint TTL is NOT "1h",
(2) the stable prefix breakpoint TTL IS "1h" (unchanged).
**Test approach:** Unit-test `_build_messages_payload` (and the system-array
build) on a representative payload; assert marker TTLs per block. Add a
read-count assertion: across an iter=1→iter=2 loop, the volatile block is
written once and read once, then a new turn re-writes — proving ≤1 read per
write, which is the economic justification for 5m-over-1h.

### AC5 — Per-turn span exposes cache_write split into stable-prefix-write vs tail-write
**Pass condition:** A per-turn OTEL span / watcher event exposes
`cache_write_tokens` decomposed into **stable-prefix-write** vs **tail-write**
so the GM panel can see churn regressions. (This is a *new axis* — distinct
from the existing 5m/1h TTL split already in `narrator.sdk.usage`.)
**Edge cases:** Must fire per turn (not only per iter) so the panel plots churn
over the session. Must distinguish the one-time stable-prefix write (turn 1 /
warmup) from the recurring tail write. Ties the CLAUDE.md OTEL-observability
principle: without this span you cannot tell whether the fix holds or whether a
future ADR re-promotes a growing field into the volatile block.
**Test approach:** Assert the emitted watcher event/span for a turn carries both
fields (`stable_prefix_write_tokens`, `tail_write_tokens` or equivalent) and
that they sum consistently with the SDK-reported `cache_creation_input_tokens`.
Wiring test: assert the span is actually emitted from the production turn path
(not just constructable in isolation) — per CLAUDE.md "Every Test Suite Needs a
Wiring Test".

## Assumptions

- **`compute_cost_usd` already prices 5m at 1.25× and 1h at 2×** (the per-TTL
  split landed in 60-4). The fix re-prices a tier move correctly without cost-
  function changes. *If wrong:* the cost function needs a 5m write rate — log a
  Design Deviation.
- **Anthropic prefix-cache semantics:** content between two `cache_control`
  breakpoints is written at the *later* breakpoint's TTL. This is the basis of
  the diagnosed mechanism. *If wrong* (e.g., each marker is independent), the
  fix surface changes — verify against the live `narrator.sdk.usage 5m=/1h=`
  log lines before implementing.
- **The volatile tail is already bounded** by 61-2's slimming (~9.7k, not
  growing fast). AC3 guards residual growth. *If the tail still grows
  materially,* AC3 fails and the story scope expands — escalate to architect.
- **`SIDEQUEST_ANTHROPIC_CACHE_TTL` default "1h" is correct for the stable
  prefix** and only the volatile tail should diverge to 5m/uncached. *If the
  intended design is per-breakpoint TTL configurability,* that is a larger
  surface — confirm at spec-check.
- **Tests can assert marker placement on the assembled payload without a live
  Anthropic call** (the payload builders are pure functions over
  `system_blocks` + `running_messages`). Verified by reading `_build_*` — they
  return plain dict lists. This is what makes the red phase tractable offline.
