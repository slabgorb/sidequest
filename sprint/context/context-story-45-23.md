---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-23: world_history arc embedding pipeline writes back to narrative_log/lore

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session — Felix):** session
reached turn 71 with dense story texture; yet `snapshot.narrative_log`
was empty of arc-derived entries (containing only narrator outputs from
recent turns) and `lore_store` had no fragments tagged from arc
content. The arc-embedding pipeline either never ran on the
chapter-promotion path (45-19's recompute), or ran but did not persist
its output back to the snapshot's `narrative_log` and the
`LoreStore.fragments` table. After 71 turns of play, the durable
historical context the narrator could query was the same chargen-time
seed plus per-turn appends — none of the chapter-promotion arc bodies
ever fed retrieval.

This is the canonical Lane B write-back failure in its embedding-pipeline
form: 45-19 wires the arc-tick *trigger* (chapter-promotion across
maturity tiers); 45-23 wires the *write* — chapter content into
`narrative_log` (durable narrative history) and into `LoreStore` (the
RAG-retrievable index). The embedding worker that turns those fragments
into vectors already exists and is wired
(`sidequest/game/lore_embedding.py:embed_pending_fragments`, dispatched
via `_dispatch_embed_worker` at
`sidequest/server/session_handler.py:4569–4609`); what's missing is the
chapter → fragment seeding that puts entries on its `pending_embedding`
queue.

The story description names the divergence as ambiguous: "embedding
pipeline either not running or not writing back." Per Epic 45 design
theme #5 (telemetry-first when the diagnosis is unclear), the right move
is to wire OTEL spans on every step of the pipeline FIRST, capture the
divergence in playtest, THEN fix. The implementation plan is structured
that way: instrument the chapter-promotion → fragment-seed → embed
worker chain so the GM panel can show exactly which step is the gap;
once spans exist, the fix is whichever step shows zero output.

**Audience tie:** James (narrative-first) is the one whose immersion
collapses when the narrator forgets early-session beats — without
arc-fed lore retrieval, turn 71's prose has no access to the texture of
turns 1-30. Sebastien (mechanical-first) needs the OTEL spans to verify
the embedding pipeline is actually moving fragments through to the
RAG-retrievable state; today the path is opaque past the existing
`lore_embedding.worker` span at `lore_embedding.py:141`.

**ADR linkage:**
- **ADR-014 (Diamonds and Coal):** the parsed history chapters
  (`HistoryChapter` at `sidequest/game/history_chapter.py`) carry the
  diamond payload — narrative_log entries, lore strings, world
  context — but the Python port never wired them through to the live
  fragment table.
- **ADR-031 (Game Watcher / OTEL):** every Lane B fix emits a span on
  the write path. This story emits two: one on chapter-promoted
  fragment seeding (the upstream gap, sibling to 45-19's
  `arc_promoted` event) and one on each successful narrative_log
  append driven by arc content.
- **ADR-048 (Lore RAG Store with Cross-Process Embedding):** the
  load-bearing ADR for this story. The lore store + embedding worker
  is already implemented; this story closes the chapter-promotion
  feed-in.
- **ADR-067 (Unified Narrator Agent):** the narrator consumes RAG
  results via `retrieve_lore_context()` at `lore_embedding.py:284`;
  unsealed arc lore is invisible to it because the fragment never
  enters the store.

This is **P2** — important for narrative quality but not blocking. Lane
A correctness sprints first.

## Technical Guardrails

### Outermost reachable layer (wire-first seam)

The wire-first gate requires the test to exercise the actual chapter-
promotion → fragment-seed → embed-worker pipeline, **not** unit tests on
each stage in isolation. Three seams must be hit:

1. **Chapter-promotion → fragment-seed seam** — 45-19 introduces the
   `world_history.arc_promoted` span on tier transitions
   (`world_materialization.py:466` → `materialize_world`). Hook the
   seeding callback at the same site, gated by the SAME predicate
   (chapters newly added by the recompute). The seed call must run
   inside `_execute_narration_turn()` at the post-`record_interaction`
   site (`session_handler.py:3424`) — same site as 45-19 — so the
   handshake is single-threaded with the recompute that authored the
   chapters.
2. **Fragment-seed → narrative_log + LoreStore seam** — the seeded
   fragments must land BOTH in `snapshot.narrative_log` (a
   `list[NarrativeEntry]` at `session.py:354`, persisted via
   `sd.store.append_narrative()` at `session_handler.py:3479`) AND in
   `sd.lore_store` via `LoreStore.add()` (so the embed worker picks
   them up on its `embedding_pending` queue). The two writes are NOT
   redundant: `narrative_log` is the durable in-snapshot history the
   narrator's `state_summary` carries; `lore_store` is the RAG-
   retrievable index queried by `retrieve_lore_context()`.
3. **Seeded fragments → embed worker seam** — `_dispatch_embed_worker`
   at `session_handler.py:4569` already fires every turn after
   narration. Once the chapter-promotion seeds new fragments with
   `embedding_pending=True`, the next dispatch picks them up via
   `lore_store.pending_embedding_ids()` at `session_handler.py:4605`
   and embeds via `embed_pending_fragments()` at
   `lore_embedding.py:105`. NO new dispatch logic is required — verify
   the seam by asserting the worker's pending count picks up the
   seeded entries on the immediate next turn.

Boundary tests must drive all three seams via the WS-driven dispatch
path using `session_handler_factory()` at `tests/server/conftest.py:332`,
`_FakeClaudeClient` at `conftest.py:197`, and a stubbed `DaemonClient`
that returns deterministic embeddings (the
`embed_pending_fragments` worker degrades gracefully when daemon is
unavailable per `lore_embedding.py:151–160` — assert the
`skipped_daemon_unavailable=True` path is NOT what the test is
exercising).

### Seeding helper (THE FIX)

Add a function (recommend
`sidequest/game/lore_seeding.py:seed_lore_from_arc_promotion`) that takes
the newly-promoted chapters (the diff between `chapters_before` and
`chapters_after` from 45-19's recompute) and:

1. For each chapter's `narrative_log` entries (typed
   `ChapterNarrativeEntry` per `history_chapter.py`), append a
   `NarrativeEntry` to `snapshot.narrative_log` and
   `sd.store.append_narrative(entry)` so the entry persists. Entries
   carry `author=entry.speaker`, `content=entry.text`,
   `round=snapshot.turn_manager.round`, `entry_type="arc_promotion"`.
2. For each chapter's `lore` strings (lore_established list per
   `history_chapter.py:HistoryChapter`), mint a `LoreFragment` with
   id `f"lore_arc_{chapter.id}_{lore_index}"`,
   `category=LoreCategory.History`, `source=LoreSource.GameEvent`
   (existing constant at `lore_store.py:57`), and add it via
   `LoreStore.add()`. Duplicate-id collisions raise `DuplicateLoreId`;
   wrap in `_try_add` per the existing pattern at
   `lore_seeding.py:31–37`.
3. Optionally, for each chapter's notes / world-lore prose, mint a
   single coalesced fragment (id `f"lore_arc_{chapter.id}_summary"`)
   so the embed budget is not exhausted by a flood of small
   fragments. Recommend a simple length budget (~512 chars per
   fragment) — `LoreFragment` content has a `min_length=1` constraint
   (`lore_store.py:77`) and the existing `DEFAULT_FRAGMENT_PREVIEW_CHARS
   = 240` (`lore_embedding.py:54`) gives a sane upper bound for
   per-fragment retrieval previews.

The function returns a structured result so the OTEL span carries
counts (entries appended, fragments minted, fragments skipped as
duplicates, content bytes seeded).

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md OTEL principle)

Telemetry-first per Epic 45 theme #5: instrument every step before the
fix lands so the divergence is observable in playtest.

Define in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES`:

| Span | Attributes | Site |
|------|------------|------|
| `world_history.arc_embedding_seed` | `chapter_id`, `narrative_entries_appended`, `lore_fragments_minted`, `lore_fragments_skipped_duplicate`, `content_bytes_seeded`, `interaction` | every chapter newly promoted by the 45-19 recompute (one span per chapter, fires even when seeded counts are zero so the GM panel sees the path engaged on every promotion) |
| `world_history.narrative_log_writeback` | `chapter_id`, `entries_count`, `interaction`, `entry_type=arc_promotion` | each `narrative_log.append` driven by arc content; pairs with the existing per-turn `sd.store.append_narrative` site |
| `world_history.lore_writeback` | `chapter_id`, `fragment_id`, `category`, `content_bytes`, `pending_embedding=True` | each `LoreStore.add` driven by arc content; the `pending_embedding=True` attribute confirms the entry is on the worker queue and the next `lore_embedding.worker` span at `lore_embedding.py:141` will pick it up |

The `arc_embedding_seed` span MUST fire on every chapter promotion,
including no-op promotions (chapter has empty narrative_log + empty
lore — possible for sparse genre packs). The bug Felix saw was the
silent absence of the path; if the span only emits on writes, the panel
cannot tell whether a promotion occurred without content vs. the path
never engaging. The `narrative_log_writeback` and `lore_writeback`
spans are per-write — they pair with the existing
`SPAN_LORE_ESTABLISHED` (`spans.py:419`) and `SPAN_QUEST_UPDATE`
(`spans.py:312`) registrations as siblings.

**Negative-path span — failure case:**
when 45-19's recompute does not promote any chapters this tick (the
common case past Veteran tier), the `arc_embedding_seed` span MUST NOT
fire. Negative test asserts the absence — this is the seam between 45-19
(emits `arc_tick` always, `arc_promoted` on transition) and 45-23
(emits `arc_embedding_seed` only when promotion happens). Crossing this
boundary would produce noise spans the GM panel can't interpret.

### Reuse, don't reinvent

- `LoreStore.add()` at `sidequest/game/lore_store.py` is the canonical
  fragment-add path; it sets `embedding_pending=True` and the existing
  `_dispatch_embed_worker` at `session_handler.py:4569` will pick the
  fragment up.
- `seed_lore_from_char_creation` at `sidequest/game/lore_seeding.py:102`
  is the existing seed pattern; the new
  `seed_lore_from_arc_promotion` mirrors it (same `_try_add` wrapper,
  same idempotent duplicate-skip semantics).
- `NarrativeEntry` at `sidequest/game/session.py` and the existing
  `world_materialization._apply_chapter` block at
  `world_materialization.py:263–274` already convert
  `ChapterNarrativeEntry` to `NarrativeEntry`. The new code re-uses
  that conversion (factor it out if it's the second copy site).
- `sd.store.append_narrative(entry)` at `session_handler.py:3479` is
  the existing per-turn persistence call; arc-driven appends use the
  same path.
- `LoreSource.GameEvent` at `sidequest/game/lore_store.py:57` is the
  existing source tag for runtime-minted (not chargen-seeded)
  fragments. The arc seeds use it.
- `embed_pending_fragments` at `lore_embedding.py:105` and
  `_dispatch_embed_worker` at `session_handler.py:4569` are unchanged —
  they pick up new pending fragments naturally on the next turn.
- 45-19's `arc_promoted` span attributes include `chapters_added: list[str]`
  — the seeding helper consumes that list directly.

### Test files (where new tests should land)

- New: `tests/game/test_lore_seeding_arc_promotion.py` — unit tests for
  the seeding helper (chapter with narrative_log entries → those land
  in `snapshot.narrative_log`; chapter with lore strings → those land
  in `LoreStore` with `embedding_pending=True`; idempotent duplicate
  skip).
- Extend: `tests/server/test_narration_turn_dispatch.py` (or the closest
  `_execute_narration_turn` integration test) — wire-first boundary
  test driving a session past a maturity tier boundary (e.g. turn 6
  Fresh→Early), asserting:
  - The new `arc_embedding_seed` span fires on the promotion turn.
  - `snapshot.narrative_log` gains entries with `entry_type=
    "arc_promotion"`.
  - `lore_store` gains fragments with `pending_embedding=True`.
  - The next turn's `_dispatch_embed_worker` picks them up
    (`lore.pending_count` attribute on the `lore_embedding.worker`
    span includes the seeded entries).
- New: `tests/server/test_arc_embedding_negative_path.py` — assert that
  on a turn where 45-19's recompute does NOT promote (turn 100,
  Veteran-stable), the `arc_embedding_seed` span does NOT fire and
  no new fragments enter `lore_store`.
- Extend: `tests/telemetry/test_spans.py` — assert
  `SPAN_WORLD_HISTORY_ARC_EMBEDDING_SEED`,
  `SPAN_WORLD_HISTORY_NARRATIVE_LOG_WRITEBACK`,
  `SPAN_WORLD_HISTORY_LORE_WRITEBACK` are registered with correct
  `SpanRoute` entries.

## Scope Boundaries

**In scope:**

- New `seed_lore_from_arc_promotion(snapshot, store, lore_store,
  chapters_added)` helper in `sidequest/game/lore_seeding.py`,
  returning a structured result for OTEL emission.
- Wire the helper into `_execute_narration_turn()` at the same
  post-`record_interaction` site as 45-19's recompute
  (`session_handler.py:3424`), gated on
  `arc_promoted` (chapter list non-empty).
- Three new OTEL spans (`arc_embedding_seed`,
  `narrative_log_writeback`, `lore_writeback`) with `SPAN_ROUTES`
  registrations.
- Wire-first boundary test reproducing Felix's evropi scenario: drive
  through a maturity tier boundary, assert the chapter content lands
  in BOTH `narrative_log` AND `lore_store`, and the embed worker
  picks the new fragments up on the immediate next turn.
- Negative-path test: no promotion → no seed span fires.

**Out of scope:**

- **45-19 (arc tick / recompute).** 45-19 is the upstream that emits
  `arc_promoted` events with `chapters_added`. 45-23 is the consumer.
  The two stories are siblings — 45-19 must land first or in parallel,
  but NEITHER may reach into the other's emit/consume sites.
  - 45-19 owns: cadence predicate, recompute call, `arc_tick` span,
    `arc_promoted` span. Does NOT touch `narrative_log` or `lore_store`.
  - 45-23 owns: seeding helper, `arc_embedding_seed` span,
    `narrative_log_writeback` span, `lore_writeback` span. Does NOT
    touch the recompute predicate or the `arc_tick` cadence.
- **The embed worker itself.** `embed_pending_fragments` at
  `lore_embedding.py:105` and the daemon-side embedding RPC are
  unchanged; this story only seeds fragments onto its pending queue.
  If the worker is silently broken (daemon unavailable, dim mismatch),
  that is a pre-existing bug visible via the existing
  `lore_embedding.worker` span — not this story's problem.
- **Daemon contract changes.** No changes to the
  `sidequest_daemon.media.embed` RPC, MAX_EMBED_BYTES, or vector
  dimensions.
- **Narrator prompt template changes.** The narrator already consumes
  `narrative_log` (via `state_summary`) and lore via
  `retrieve_lore_context` (Valley zone, see
  `agents/orchestrator.py:1219`). No prompt scaffolding edits.
- **Chargen-time chapter seeding.** `seed_lore_from_char_creation` at
  `lore_seeding.py:102` and the existing
  `world_materialization._apply_chapter` paths
  (`world_materialization.py:263–274`) already populate the
  chargen-time fresh chapter's narrative entries into
  `snapshot.narrative_log`. The new helper is for *runtime*
  promotions only — explicitly disjoint from the chargen path.
- **45-20 (trope resolution → quest_log).** Distinct write-back path:
  45-20 writes to `quest_log` and `active_stakes`, NOT to
  `narrative_log` or `lore_store`. The two stories' write surfaces
  are non-overlapping.

## AC Context

The story description carries the contract; we expand it into testable ACs:

1. **Arc generation triggers writeback to `narrative_log`.**
   - Test: drive a session across a maturity tier boundary (e.g. turn
     6, Fresh → Early). Assert `snapshot.narrative_log` gains entries
     sourced from the newly-promoted Early chapter, with
     `entry_type="arc_promotion"` and `round` matching the
     promotion turn.
   - Wire-first: the assertion is on the JSON the next narrator
     receives in `state_summary`, not the raw snapshot — confirms the
     post-mutation timing seam.

2. **Arc generation triggers writeback to `lore_store`.**
   - Test: same fixture as AC #1. Assert `lore_store` gains
     `LoreFragment`s with id prefix `lore_arc_<chapter_id>_*`,
     `category=LoreCategory.History`, `source=LoreSource.GameEvent`,
     and `embedding_pending=True`.
   - Test: on the immediate next turn, the `_dispatch_embed_worker`
     fires; the `lore_embedding.worker` span's `lore.pending_count`
     attribute includes the newly-seeded entries; if the stubbed
     daemon returns embeddings, `lore.embedded` matches the seeded
     count.

3. **OTEL `world_history.arc_embedding_seed` span fires per
   promoted chapter with seeded counts.**
   - Test: trigger a promotion of two chapters (e.g. a session that
     skips through Fresh → Mid in one recompute by virtue of high
     beats_fired). Assert the span fires twice — once per chapter —
     with `narrative_entries_appended`, `lore_fragments_minted`,
     `lore_fragments_skipped_duplicate`, `content_bytes_seeded` set.
   - Verify `SPAN_ROUTES` registers the watcher mapping so events
     reach the GM panel.

4. **Negative — no writeback fires when no chapters are promoted.**
   - Test: drive a turn at Veteran-stable (turn 100, no tier change).
     Assert `world_history.arc_tick` fires (45-19's emission) but
     `world_history.arc_embedding_seed`,
     `world_history.narrative_log_writeback`, and
     `world_history.lore_writeback` do NOT fire. No new entries enter
     `narrative_log` or `lore_store` from this turn's recompute.
   - Confirms the seam between 45-19 (always-tick) and 45-23
     (promotion-only). The bug Felix saw was a silent no-op on the
     45-23 side; the negative test ensures the new path is also a
     true no-op when no chapters promote, not a noisy zero-fragment
     emit.

5. **Negative — arc seeding does not duplicate chargen-time chapter
   content.**
   - Regression test: chargen materialized the `Fresh` chapter at
     `session_handler.py:2647–2693`, which already wrote that
     chapter's narrative_log entries into `snapshot.narrative_log`
     via `world_materialization._apply_chapter`. A subsequent
     recompute that re-touches the `Fresh` chapter (e.g. due to
     idempotent re-tick) MUST NOT re-seed those entries.
   - Implementation note: the seeding helper consumes ONLY
     `chapters_added` (the diff from 45-19's recompute), not the
     full applicable list. The diff is empty for an idempotent
     re-tick; the helper short-circuits.

6. **Save/reload durability for `narrative_log` arc entries.**
   - Test: drive promotion; persist via `sd.store.save(snapshot)` and
     `sd.store.append_narrative(...)`; reload via the persistence
     path; assert the arc-promotion entries are still present on the
     reloaded snapshot's `narrative_log`. The `lore_store` durability
     is governed by the existing LoreStore persistence (separate
     concern handled by ADR-048).
