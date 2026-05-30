# Epic 61: Bounded Narrator Prompt — Slim Snapshot + Wire RAG

## Overview

Close the architecture-level invariant that ADRs 048, 098, 109, and 110 each
touched but none owned: **every growing field on `snapshot` must either be
dropped from the prompt, RAG-retrieved on demand, or size-capped before
serialization.** The 2026-05-23 cost-runaway incident burned ~$313 in 48
hours because seven snapshot fields (`room_states`, `journal`, `npcs`,
`known_facts`, `footnotes`, `belief_state`, `location_descriptions`) flow
into the Valley/Recency `system_blocks` unslimmed and uncached, multiplied
by up to 8 tool-loop iterations per turn. Compounded by `LoreStore` being
built (ADR-048) but never wired into production `ToolContext` — `query_lore`
returns `lore_store_wired=False`, so the narrator receives the entire lore
corpus in the prompt every turn instead of retrieving on demand.

**Priority:** P0
**Repo:** server (61-6 in orchestrator)
**Stories:** 6 (17 points) — 61-1 RAG wiring (3), 61-2 snapshot slim (5),
61-3 hard cap canary (2), 61-4 fingerprint alarm (2), 61-5 architecture
gate (3), 61-6 playtest validation (2).

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Memory: runaway-valley-block** (`~/.claude/projects/-Users-slabgorb-Projects-oq-2/memory/project_runaway_valley_block_2026_05_23.md`) | The full diagnosis: file:line evidence, two compounding regressions, fix surface |
| **Memory: anthropic-key-compromise** (`~/.claude/projects/-Users-slabgorb-Projects-oq-2/memory/project_anthropic_key_compromise_2026_05_23.md`) | Incident frame: $20k limit raise + key rotation context; cost arithmetic |
| **60-3 session** (`sprint/archive/60-3-session.md`) | Original tool-loop diagnosis; "Valley acquitted on cache-write churn" framing that punted this gap |
| **ADR-048 Lore RAG Store** (`docs/adr/048-lore-rag-store.md`) | The RAG architecture; 61-1 lands its production wiring ("Phase E") |
| **ADR-098 Stateless Narrator Turns** (`docs/adr/098-stateless-narrator-turns.md`) | §Decision: "Prompt size is bounded by section selection." 61 enforces this at the snapshot layer (currently bounded only at the message layer) |
| **ADR-109 Persistent Location Descriptions + Mechanical Manifest** (`docs/adr/109-persistent-location-descriptions-mechanical-manifest.md`) | Proximate trigger — added `location_descriptions` as a growing snapshot field on 2026-05-19 without updating the DROP list |
| **ADR-110 Game-State Snapshot Slimming** (`docs/adr/110-game-state-snapshot-slimming.md`) | §Decision Phase A+B (shipped) + §Implementation Notes "DROP list is reviewed at every PR that adds a `GameSnapshot` field … schema-validation hook does not enforce this today" — the un-enforced rule that 61-5 finally enforces |
| **Epic 60 context** (`sprint/context/context-epic-60.md`) | The cache-write-churn epic this one completes; "Valley innocent" framing in 60-3 |

## Background

### The incident

2026-05-23 cost audit: $449 MTD against `ANTHROPIC_API_KEY`, ~$313 of that in
the trailing 48 hours, **all claude-sonnet-4-6** (negligible Haiku/Opus).
Anthropic Usage dashboard week May 18-24: **980,465,766 input tokens vs
657,798 output tokens — a 1490:1 input/output ratio.** Recent API logs show
the unique fingerprint: 16 calls in 31 seconds at 02:17 AM EDT, ~60K input
tokens each, **12-19 output tokens each**. A healthy narrator turn is ~12K
input / ~500 output (ratio ~24:1) — so the cost period ran at **60x worse
than baseline**. One Anthropic rate-limit hit was recorded; the account
usage limit had been externally raised to $20,000 (rotated and disabled on
2026-05-23; see `project_anthropic_key_compromise_2026_05_23` memory for
the security frame).

Local cost telemetry — the `narrator.sdk.usage cost_usd=…` log lines —
summed to only ~$9 across the visible two-day log window. The gap (logged
$9 vs billed $313) is logs-truncated-by-repeated-`just up` plus the
heaviest late-session turns dominating the bill at amplitudes the visible
slice did not catch. Driver: the developer iterating on epic 60
cache-rebate work overnight (commits at 02-03 AM EDT on May 23), running
`scenarios/cache_diag_60_3.yaml` against `uvicorn --reload --reload-dir
sidequest` while editing the very narrator files the scenario was
measuring. Every save invalidated the in-process cache; every scenario
re-run paid full input on the growing snapshot × 8 tool-loop iterations.

### Why the runaway was structurally possible

Three "we have this covered" claims, each true at the design level, false
at the wiring level:

**1. RAG: built, never wired into production.** `agents/tools/query_lore.py`
lines 96-109 — the production code path explicitly returns empty:

> ```python
> if ctx.lore_store is None:
>     # Phase E wires the LoreStore into ToolContext at the production
>     # call site. Until then, return an empty result with an OTEL marker
>     ...
>     return ToolResult.ok({"fragments": [], "k": args.k, "lore_store_wired": False})
> ```

`SessionHandler.lore_store` exists (`session_handler.py:485`), the tool
exists, the schema describes a working RAG retrieval. The wiring step that
threads `lore_store` from `SessionHandler` through to the per-turn
`ToolContext.lore_store` (`tool_registry.py:99-104`) was never landed.
Result: every piece of world lore that the narrator might need is shoveled
into the prompt up front, every turn, instead of being retrieved on
demand. The RAG mechanism is dark code — it exists, costs nothing, helps
nothing.

**2. Bounded prompts: bounded at the message layer, not the snapshot layer.**
ADR-098 §Decision: *"Prompt size is bounded by section selection, not
tier gating."* The implementation honored this at the message layer —
dropped `claude --resume`, made `running_messages` fresh per turn
(verified: `running_messages` is local to `complete_with_tools` at
`anthropic_sdk_client.py:122`; `messages = [Message(...)]` is rebuilt
each turn at `orchestrator.py:3460`). That part works. But ADR-098's
invariant is honored only if the *sections themselves* are bounded — and
the `<game_state>` section is serialized from `snapshot.model_dump()`,
which grows monotonically across the session. ADR-098 satisfied by the
letter, violated by the spirit. The very growth pattern ADR-098 was
written to kill (Anthropic-side `--resume` history accumulation) was
recreated by the snapshot dump.

**3. Snapshot slimming: Phase A+B shipped — and the growing fields were in
neither.** ADR-110 §Decision adopted **Phase A** (compact JSON encoding)
+ **Phase B** (DROP-list allowlist) and explicitly **deferred Phase C**
(diff-with-anchor) and **Phase D** (hierarchical lazy fetch via
`query_state` tool). Phase B's DROP list landed at `session_helpers.py:64`
as `_PHASE_B_DROP_FIELDS`: `active_tropes`, `axis_values`, `genie_wishes`,
`achievement_tracker`. **None of those four grow.** The seven fields that
do grow (`room_states`, `journal`, `npcs`, `known_facts`, `footnotes`,
`belief_state`, `location_descriptions`) were never enumerated, never
dropped, never RAG-routed. ADR-110 §Implementation Notes anticipated
exactly this regression:

> *"The DROP list is reviewed at every PR that adds a `GameSnapshot` field
> going forward. The schema-validation hook does not enforce this today —
> flagged here as a follow-up consideration, not a blocker."*

Five days later (2026-05-19), ADR-109 added `location_descriptions` as a
persistent growing field. Nobody updated the DROP list. The unenforced
review rule failed silently. 61-5 closes this by making the review
enforceable via test.

### Why epic 60 didn't catch this

Epic 60 was framed as **cache-write churn**: the cached prefix
(`system_blocks[0]`, ~11.7K tokens) was being re-minted at 5m TTL on every
tool-loop continuation, paying ~$0.046/turn × 2 fires/turn = ~$0.089/turn
of waste. The 60-3 diagnostic correctly identified this and called the
Valley block **"innocent"** — meaning innocent of *cache-write churn*.
That was right, inside epic 60's framework. It was wrong globally: an
**uncached** block at 1× input rate, carrying a payload that grows linearly
with session length, multiplied by up to 8 tool-loop iterations per turn,
is a worse cost driver than cache-write churn was. The Valley was
**acquitted on the wrong charge**.

60-4's description doubled down: *"Do NOT re-zone the state sections —
they are User-bucket/uncached; re-zoning is a no-op for cost."* Re-zoning
is indeed a no-op for cost. **Slimming-and-RAG-routing** is the actual
fix, and it sits outside epic 60's scope. Epic 60 closed the cache-write
gap (60-4 landed 2026-05-23 at 03:41 EDT, ~$0.08/turn saved). Epic 61
closes the orthogonal growth gap (estimated $300+/2 days saved in the
incident's amplitude regime).

### What the cost actually was

At ~60K input tokens × up to 8 tool-loop iterations × N turns, where the
snapshot grows by O(N) over the session: late-session turns dominated the
bill. The 1490:1 input/output ratio is the unique fingerprint of "model
receives massive prompt, has nothing new to say" — exactly what happens
when the same growing payload is fed through the tool-loop 8 times for a
single player action, with the model producing short tool-stub responses
at each iteration. The May 22 and May 23 spikes are precisely this
pattern: long debugging sessions where each `cache_diag_60_3.yaml` run
hammered the loop while the snapshot accumulated session state.

### Adjacent regressions (out of scope, tracked)

Sidequest-server-agent investigation also surfaced a stable-block cache
TTL mismatch — `SIDEQUEST_ANTHROPIC_CACHE_TTL` defaults to "1h" at
`anthropic_sdk_client.py:80-90`, but the system-path `cache_control`
marker writes 5m (server log evidence: `5m=11520..12224, 1h=0` on every
iter=1). 60-4 fixed the 1h TTL for tool_result continuation but did not
extend it to the system-path block 0 marker. This is a smaller cost
driver and lives more naturally as a 60-followup story than as part of
61's scope.

## Technical Architecture

The fix is **structural, not pointwise**. Four layers, in dependency order:

### Layer 1 — RAG production wiring (61-1)

Land ADR-048's missing "Phase E". Code surfaces already in place:

- `sidequest/game/lore_store.py` — `LoreStore` class (the RAG store)
- `sidequest/server/session_handler.py:485` — `lore_store: LoreStore = field(default_factory=LoreStore)`
- `sidequest/agents/tool_registry.py:99-104` — `lore_store: LoreStore | None = None` on `ToolContext`
- `sidequest/agents/tools/query_lore.py` — the `@tool` definition

What's missing: at the per-turn `ToolContext` construction site (in
`orchestrator.py` or wherever the context is built for the SDK call),
thread `session_handler.lore_store` into `ToolContext.lore_store`. Once
wired, `query_lore.py:96-109`'s early-return-empty branch no longer
fires and the tool returns real top-k retrieval.

This story unblocks Layer 2's per-field decisions: fields routed to RAG
(rather than dropped or projected) require RAG to actually work.

### Layer 2 — Snapshot slim (61-2)

`session_helpers.py:64` defines `_PHASE_B_DROP_FIELDS`. Extend it.

**Correction 2026-05-23 (post-61-2 red-phase):** the seven fields the
epic preamble named are not all snapshot fields. Validation against
`GameSnapshot.model_fields` showed **four ride the snapshot and got
projected; three are decoys that ride other channels and got regression
guards instead.** Total surface = 4 real growers + 1 bonus catch
(`scenario_state.discovered_clues`).

**Four real growers — projected in `_apply_phase_c_projections`:**

| Field | Where it lives | Decision | Code anchor |
|---|---|---|---|
| `room_states` | top-level on `GameSnapshot` | Keep acting PC's `current_room_id` only; empty dict when absent (structural anchor) | `session_helpers.py:_apply_phase_c_projections` |
| `npcs` | top-level on `GameSnapshot` | In-scene only (`last_seen_location == current_room_id` OR encounter actor); off-stage retain identity in `npc_pool` | `session_helpers.py:_npc_in_scene` + `_apply_phase_c_projections` |
| `known_facts` | nested on `Character` (under `characters[*]`) | Tail-K=8 per PC (mirrors `persistence.py:889`) | `session_helpers.py:_apply_phase_c_projections` |
| `belief_state` | nested on `Npc` (under `npcs[*]`) | Stripped from surviving in-scene entries (dispatch-side state, ADR-053; not prompt-side) | `session_helpers.py:_apply_phase_c_projections` |

**Bonus catch (also nested) — projected in `_apply_phase_c_projections`:**

| Field | Where it lives | Decision |
|---|---|---|
| `discovered_clues` | nested on `scenario_state` | Size cap at 12, sorted by clue id (source is `set[str]`) |

**Three decoys — NOT snapshot fields; regression guards only:**

| Field | Actual home | Why it's not on snapshot |
|---|---|---|
| `journal` | derived from `Character.known_facts` + event log via `JournalRequestHandler` (ADR-100) | Event-log-shaped, not snapshot-shaped |
| `footnotes` | per-turn `NarrationResult.footnotes` (`orchestrator.py:452`) | Per-turn artifact, never persisted to snapshot |
| `location_descriptions` | out-of-band via `LOCATION_DESCRIPTION` WebSocket messages, loaded from `cookbook/assemble.py` at room change (ADR-109) | Not in `<game_state>` — rides a separate prompt section / network message |

The cost-runaway diagnosis stands on the four real bloat sources. The
3-decoy correction means the original "seven fields growing into the
Valley" framing was overstated — but the Valley *was* growing on the
four (room_states with N rooms visited, npcs with N NPCs accumulated,
known_facts with N facts per PC, belief_state with O(NPC × clue)
cardinality), which is enough to fully account for the $313/48h
amplitude regime at session lengths reached on 2026-05-22-23. Regression
guards for the three decoys (the "anchor / regression guards" tests in
`test_61_2_snapshot_seven_field_projection.py`) will fail fast if a
future ADR-109-shaped change materializes any of them onto
`GameSnapshot` without an explicit projection decision.

The narrator-load-bearing audit method is in ADR-110 §Phase B:

1. Static survey — grep narrator prompt assembly for snapshot field references.
2. Recency-zone overlap check — any field already re-rendered by a dedicated prompt section is dropped (footnotes is the textbook case).
3. Deferred-subsystem trim — fields with no live consumer are dropped.

Per ADR-110: "No silent fallbacks — if a future field's narrator-relevance
is unknown, it stays in by default; the DROP list is the conscious
removal, not the omission." 61-2 makes the seven decisions consciously.

### Layer 3 — Defense in depth (61-3, 61-4, 61-5)

**61-3 — Hard-cap the oversized canary.** Today
(`orchestrator.py:2967-2997`):

```python
def _maybe_emit_oversized_canary(self, system_prompt, user_message, registry, agent_name):
    """Soft canary for unbounded growth regressions (ADR-098 §Bound canary)."""
    total = len(system_prompt) + len(user_message)
    if total <= SOFT_PROMPT_BUDGET_BYTES:
        return
    ...
    logger.warning("narrator.prompt_oversized total_bytes=%d budget=%d ...")
    _pub("prompt_oversized", {...})
```

Soft → hard. When total bytes exceed `SOFT_PROMPT_BUDGET_BYTES`,
either (a) refuse the call and return a degraded result with a loud
operator-facing emit, or (b) aggressively truncate the Valley payload to
fit (drop oldest entries first within bounded fields). Emit must be
*loud* on the GM panel — not a buried `logger.warning` that scrolled past
unread during overnight debugging.

**61-4 — Fingerprint alarm.** Add a runtime check at
`agents/anthropic_sdk_client.py` (the SDK call entry, where
`narrator.sdk.usage` already logs cost). Fire alarm when:

- `input_tokens > N × rolling_baseline` (e.g., N=2), **AND**
- `output_tokens < M` (e.g., M=50)

— the 60K-in/12-out signature the incident exhibited. Single-call
alarm; doesn't need to wait for daily aggregates. Emit to the GM panel
loud. This is the lie detector for "model is being hammered with no
new info to respond to" — a class of bug the existing observability
missed.

**61-5 — Architecture gate (test enforcement).** Add a test in
`sidequest-server/tests/server/` that:

1. Enumerates the top-level fields of `GameSnapshot` (via `pydantic`
   `model_fields` reflection — the "tripwire" pattern already established
   at `tests/dungeon/test_setpiece_attach_wiring.py`).
2. Asserts every field is either in `_PHASE_B_DROP_FIELDS`, marked
   bounded-by-construction in a sibling registry, or has an explicit
   per-field projection decision recorded.
3. Fails when a new field lands without one of those.

This is the test that, had it existed before 2026-05-19, would have
blocked ADR-109's `location_descriptions` from landing without an explicit
slim decision. Makes ADR-110 §Implementation Notes' un-enforced review
rule enforceable.

### Layer 4 — Verification (61-6)

Mirrors 60-5 / 24-8 playtest-validation pattern. Drive a **50-turn solo
session of `tea_and_murder/glenross`** through the live SDK path on a
fresh `develop` post-61-2 merge. Acceptance:

- `input_tokens` at turn 50 ≤ 1.2× `input_tokens` at turn 5 (bounded growth)
- Per-turn cost stays flat across turns 5-50 (no monotonic increase)
- A deliberate runaway attempt (revert 61-2 locally) trips the 61-4
  fingerprint alarm within 3 turns
- The 61-3 hard cap engages on a constructed oversized-Valley case and
  the GM-panel surfaces the loud emit

Runs in `orchestrator` repo (per 60-5 / 24-8 precedent for cross-cutting
validation chores).

### Key files

| Path | Role in 61 |
|------|-----------|
| `sidequest-server/sidequest/server/session_helpers.py:64` | `_PHASE_B_DROP_FIELDS` — extend in 61-2 |
| `sidequest-server/sidequest/server/session_helpers.py:559` | `snapshot.model_dump()` call site — projection happens here |
| `sidequest-server/sidequest/agents/orchestrator.py:3437-3441` | Valley/Recency `cache=False` registration — may need re-zoning of slimmed remnants |
| `sidequest-server/sidequest/agents/orchestrator.py:2967-2997` | Soft canary — hard-cap in 61-3 |
| `sidequest-server/sidequest/agents/anthropic_sdk_client.py` | SDK call entry — fingerprint alarm in 61-4 |
| `sidequest-server/sidequest/agents/tools/query_lore.py:96-109` | RAG-not-wired early-return — eliminated by 61-1 |
| `sidequest-server/sidequest/agents/tool_registry.py:99-104` | `ToolContext.lore_store` — populated in 61-1 |
| `sidequest-server/sidequest/server/session_handler.py:485` | `LoreStore` owner — threaded through in 61-1 |
| `sidequest-server/sidequest/game/lore_store.py` | The RAG store implementation |
| `sidequest-server/sidequest/game/session.py` (or wherever `GameSnapshot` is defined) | Source of the field enumeration that 61-5's gate test reflects over |

## Cross-Epic Dependencies

**Depends on:**

- **Epic 60 (Narrator Token & Cost Budget — Cache-Write Efficiency)** —
  60-4 (1h cache breakpoint on tool-loop continuation) landed 2026-05-23.
  60-2 (per-block cache attribution OTEL eyes) and 60-3 (diagnose spike)
  done. 61 builds on the observability 60-2 added (per-block digest, drift
  detection, real `cache_read`/`cache_write` join) and the SDK call
  surface 60-4 stabilized. 61-4's fingerprint alarm is a sibling of
  60-2's per-block cost telemetry.

**Depended on by:**

- **Future scenario / journal / lore retrieval work** — once `LoreStore`
  is wired (61-1), it becomes the production seam for ADR-100 journal
  retrieval, ADR-053 scenario clue retrieval, and any future "narrator
  queries world state" mechanic. 61-1 unblocks all of these.

**Related (not blocking):**

- **ADR-098 Stateless Narrator Turns** — 61 closes the snapshot-side
  hole that left ADR-098's "Prompt size is bounded by section selection"
  aspirational. Post-61, "bounded per-turn prompts" is enforced at both
  the message layer (already done) AND the snapshot layer (61-2 + 61-5).
- **ADR-110 Game-State Snapshot Slimming** — 61-2 effectively completes
  ADR-110's Phase B by carrying out the per-field audit the original
  story (57-5) stopped short of. 61-5 enforces the §Implementation Notes
  "DROP list reviewed at every PR" rule via test. Optional follow-up
  beyond 61: revisit Phase C (diff-with-anchor) if 61-2's drop/project
  decisions still leave the Valley too large at session length 100+.
- **ADR-048 Lore RAG Store** — 61-1 lands ADR-048's missing production
  wiring step. The store, the tool, and the context field exist; only
  the per-turn population is missing.
- **ADR-109 Persistent Location Descriptions** — the proximate trigger.
  61-2 must include `location_descriptions` in its per-field projection.
  The field is load-bearing for the narrator (POI prose), so the
  decision is "project to active POI only", not "drop entirely".
- **Adjacent regression (stable-block 5m vs 1h TTL on system path)** —
  surfaced during the 61 investigation. Not in scope here; tracked as a
  potential 60-followup. Small absolute cost (~$0.02/turn) vs 61's
  growth-bound cost (unbounded), so deferring is safe.
