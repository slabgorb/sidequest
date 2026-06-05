---
story_id: "84-3"
jira_key: ""
epic: "84"
workflow: "tdd"
---
# Story 84-3: WI-4 Relationship card projector (index-side, summary-tier projection of disposition_log → attitude + key beats)

## Story Details
- **ID:** 84-3
- **Jira Key:** (none — no Jira integration for sidequest-server)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Repo:** sidequest-server

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-05T00:00:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-05T00:00:00Z | - | - |

## Technical Approach

### Story Context
WI-4 implements the relationship-card projector — a **summary-tier card** that projects an NPC's `disposition_log` (persisted in `Npc.disposition_log`, ADR-136) into a concise, embeddable entity card for the universal retrieval layer (ADR-118, Amendment §A4). This is the **index-side projection**, distinct from ADR-136's player-facing RELATIONSHIPS surface. The relationship card surfaces in retrieval when:

1. An NPC floor card is retrieved (via 75-2 working set)
2. The NPC's disposition is queried via mention or location
3. Related-entity context is needed by the narrator

### Key Design Constraints (from ADR-118 Amendment §A4)

**Relationship card ≡ summary-tier card:**
- The `disposition_log` is a time series and cannot be embedded whole (too long, too granular)
- The relationship card is **born at SUMMARY tier** (ADR-118 Amendment §A3)
- Carries: current attitude band + the two or three load-bearing beats (filtered by recency)
- The decay machine (tiered projection) and the relationship projector are the **same shape**

**Alias/epithet awareness:**
- The relationship card carries an alias set in metadata (like `project_npc_card` already does) so mention-matching works through epithets
- Aliases are sourced from `Npc.aliases` (accretion-fed via story 84-2's WI-5 path)

### File Pointers & Implementation Seams

**Disposition-log source:**
- File: `/Users/slabgorb/Projects/oq-3/sidequest-server/sidequest/game/session.py` (lines ~200-254)
- Model: `Npc.disposition_log: list[DispositionBeat]` (ring buffer, capped at `DISPOSITION_LOG_CAP`)
- Beat schema: `DispositionBeat(turn, delta, reason, location)` — persisted by `record_disposition_beat(...)` at engine mutation points

**Attitude derivation:**
- File: `/Users/slabgorb/Projects/oq-3/sidequest-server/sidequest/game/disposition.py`
- Method: `Disposition.attitude()` → `Attitude` enum (HOSTILE / COOL / NEUTRAL / WARM / DEVOTED) — live on the engine, already in use by `project_npc_card`
- NPC disposition lives on `Npc.disposition` (wrapper on an `int` in range −100..+100)

**Entity-card projector seam:**
- File: `/Users/slabgorb/Projects/oq-3/sidequest-server/sidequest/game/entity_card.py` (lines ~182–316)
- Existing projectors: `project_npc_card()` (lines ~212–258), `project_faction_card()` (lines ~261–274), `project_location_card()` (lines ~277–315)
- **New: `project_relationship_card(npc: Npc) -> EntityCard`** — the WI-4 story work
  - Accepts only a stateful `Npc` (not `NpcPoolMember` — relationships are only for promoted NPCs)
  - Extracts `npc.disposition_log` and filters to load-bearing beats (most recent 2–3 with non-zero impact)
  - Projects: `"{NPC name} — disposition: {attitude} — key beats: {beat1 reason}, {beat2 reason}, ..."`
  - Stores aliases in metadata (JSON-encoded, sorted) like `project_npc_card` does, so mention resolution works
  - Entity type: `EntityType.RELATIONSHIP` (requires adding to the type enum; ADR-118 Amendment §A2 recognizes relationships as an index-side type)

**Retrieval wiring:**
- File: `/Users/slabgorb/Projects/oq-3/sidequest-server/sidequest/game/retrieval_orchestration.py`
- Struct: `RetrievedEntities` (lines ~82–119) will gain an optional `retrieved_relationships: list[EntityCard] | None` field
- Function: `retrieve_turn_context(...)` (lines ~182+) orchestrates floor + fill; fills will include relationship cards when NPCs are indexed
- Entry point: Called from `sidequest/agents/intent_router.py` / narrator pipeline

**Index storage:**
- File: `/Users/slabgorb/Projects/oq-3/sidequest-server/sidequest/game/entity_store.py`
- Model: `EntityStore` holds typed `EntityCard`s indexed by entity type; relationship cards become a new typed slice
- Cards are projected on NPC mutation (dirty-flag → reproject path, per ADR-118 §D3)

**ADR-136 relationship surface (player-facing, separate from WI-4):**
- File: `/Users/slabgorb/Projects/oq-3/docs/superpowers/plans/2026-06-01-npc-relationship-panel.md`
- Implementation: Server-side `RelationshipProjectionStage` + client `RELATIONSHIPS` message (live, per ADR-136 implementation-pointer)
- Distinct from WI-4: ADR-136 is the **player-facing projection** (attitude band + beat-log as UI); WI-4 is the **index-side retrieval projection** (summary-tier embeddable card for the narrator's turn context)

### Testing Strategy (TDD workflow)

1. **Unit tests** — `test_project_relationship_card()`
   - Project an `Npc` with a populated `disposition_log` → assert the card content contains the attitude band and key beats
   - Assert aliases are serialized into metadata
   - Assert blank disposition_log → minimal card (current attitude only, no beats)
   - Assert beat filtering: only load-bearing beats (non-zero delta, within recency window) are included

2. **Integration tests** — `test_relationship_card_in_retrieval()`
   - Fixture: genre snapshot + an `Npc` with populated `disposition_log` and aliases
   - Call `retrieve_turn_context(...)` with a query mentioning the NPC
   - Assert the relationship card appears in the result (in `retrieved_relationships`)
   - Assert the card's content is serialized into the prompt and reaches the narrator

3. **Wiring test** — `test_relationship_card_entity_type_registered()`
   - Assert `EntityType.RELATIONSHIP` is registered in `_ID_NAMESPACE`
   - Assert `project_relationship_card` is called from the entity-sync dispatch (ADR-138) when an NPC's disposition changes
   - OTEL assertion: verify `card_reproject_count` span is emitted when a relationship card is dirtied

### Open Questions / Risk Flags

- **Recency window for beat filtering:** The spec says "two or three load-bearing beats" — should this be a tunable constant or driven by a token budget for the card content?
- **Attitude-only fallback:** If `disposition_log` is empty (legacy save or fresh NPC), should the card fall back to the current attitude alone, or fail loud?
- **Card-id convention:** Should relationship cards use `"relationship:{npc_name}"` or `"npc:{npc_name}:relationship"` to avoid colliding with NPC cards? (Recommend `"rel:{npc_name}"` per the id-namespace pattern.)

## TEA Assessment

**Tests Required:** Yes
**Reason:** New index-side card type that touches the 84-1 fail-loud scorer + the per-turn sync sweep — every AC needs failing coverage, and the fail-loud chain is a real regression hazard.

**EntityType / SIGNAL_APPLICABILITY decision (investigated):** `RELATIONSHIP` is a NEW `EntityType` member that MUST be registered in THREE places together or downstream fails loud:
1. `EntityType` enum (`entity_card.py:39`) + `_ID_NAMESPACE` (`:55`, namespace `"rel"` → `rel:<slug>`) — else `EntityCard.new` raises `ValueError`.
2. **`SIGNAL_APPLICABILITY` (`pertinence.py:80`) — THE load-bearing one.** `pertinence._applicable_signals` (`:147-152`) **`raise ValueError` on any EntityType not in the matrix**. Adding the enum WITHOUT the applicability row breaks `score_card` the moment a relationship card is scored in `retrieve_turn_context`. Recommended applicable signals: **`{mention, here, recency}`** (NOT `sim`) — §A2: a relationship surfaces because the related NPC is named/present; it rides the NPC's structural signals, topical cosine is the NPC card's job. AC-4 pins enum + applicability land together with no fail-loud regression.
3. `retrieve_turn_context._finish` `by_type` (`retrieval_orchestration.py:228`) — add `retrieved_relationships` (AC-6).

**Projection/index approach (investigated): STORED, not on-demand.** Cards enter the index via `entity_sync.sync_entity_cards` / dispatch `sync_for_turn` (the §D3 per-turn dirty-flag sweep, `entity_sync.py:185` NPC loop), NOT projected on-demand at retrieval. WI-4 projects the `rel:<slug>` card alongside the `npc:<slug>` card in that loop, with a `relationship_count` reproject tally + the existing `card_reproject_count` OTEL span. AC-7/AC-8 pin this.

**ADR-136 reuse (investigated — the load-bearing answer): REUSE `band_for`, the beat SELECTION is NET-NEW.** `sidequest/game/projection/relationships.py` (the player-facing panel, orthogonal) holds `band_for(value) -> str` (`:27`, disposition int → 5-level band Devoted/Warm/Neutral/Cool/Hostile) and `trend_for(beats)` (`:40`) — REUSE `band_for` for the card's attitude band, don't reinvent the thresholds. BUT `build_relationship_entries` (`:83-86`) dumps the **ENTIRE** `disposition_log` into the payload — there is **NO existing 2-3-beat load-bearing selection**. The SUMMARY-tier abbreviation (`select_load_bearing_beats`) is genuinely NET-NEW WI-4 work. Do not touch the ADR-136 panel beyond importing `band_for`.

**Source corrections to the setup brief:** the engine `Attitude` enum is **3-level** (FRIENDLY/NEUTRAL/HOSTILE, `disposition.py:95`), NOT the 5-level the brief listed. `DISPOSITION_LOG_CAP = 10`. For the card's "attitude band", reuse ADR-136's 5-level `band_for` (richer) — the test pins that SOME attitude band is in content, leaving the band-vocabulary choice to Dev.

**Test Files:**
- `sidequest-server/tests/game/test_relationship_card_projector.py` — `project_relationship_card` + `select_load_bearing_beats` (AC-1/2/3/5). 14 tests.
- `sidequest-server/tests/game/test_relationship_entity_type.py` — 3-registration + 84-1 fail-loud guard (AC-4). 6 tests.
- `sidequest-server/tests/game/test_relationship_retrieval.py` — `retrieved_relationships` field + surfaces-in-retrieval (AC-6). 3 tests (`-n0`).
- `sidequest-server/tests/server/test_relationship_card_sync_wiring.py` — entity-sync projection + count + live dispatch wiring (AC-7/8). 3 tests (`-n0`).

**Tests Written:** 26 covering AC-1…AC-8 (AC-9 = GREEN-gate quality check).
**Status:** RED — 25 failing, 1 passing.
- 14 `ImportError` (`project_relationship_card`/`select_load_bearing_beats` absent), 8 `AttributeError` (`EntityType.RELATIONSHIP`/`EntitySyncResult.relationship_count` absent), 3 `AssertionError` (registration/field-presence: `RELATIONSHIP` not in enum, `retrieved_relationships` not on RetrievedEntities, `relationship_count` not on EntitySyncResult). All clean feature-absence — no typos/fixture bugs.
- The 1 passing test (`test_unregistered_type_still_fails_loud`) is an intentional "guard the guard" regression lock on the No-Silent-Fallbacks mechanism — it must pass before AND after, proving Dev didn't neuter the fail-loud when adding RELATIONSHIP.

**Wiring path:** dispatch `entity_sync.sync_for_turn` → `sync_entity_cards` (projects `rel:<slug>` alongside `npc:<slug>`, counts it) → `retrieve_turn_context` surfaces it in `retrieved_relationships`. The wiring test drives the real `sync_for_turn` and asserts the `rel:borin` card lands in the live `entity_store` + the watcher event carries `relationship_count`.

**Run command (OTEL-sensitive — serial):**
`uv run pytest -n0 tests/game/test_relationship_card_projector.py tests/game/test_relationship_entity_type.py tests/game/test_relationship_retrieval.py tests/server/test_relationship_card_sync_wiring.py`

**Handoff:** To Dev (Naomi) for implementation (GREEN).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/entity_card.py` — `EntityType.RELATIONSHIP` + `_ID_NAMESPACE["rel"]` (regs 1 of the 3-reg chain); NEW `select_load_bearing_beats` + `project_relationship_card` (SUMMARY tier, `band_for` reuse, sorted-alias metadata, `rel:<slug>` id); added `retrieval.relationship_count` to `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` (keeps 84-4's bidirectional contract honest).
- `sidequest/game/pertinence.py` — `SIGNAL_APPLICABILITY[RELATIONSHIP] = {mention, here, recency}` (reg 2; NOT sim — §A2).
- `sidequest/game/retrieval_orchestration.py` — `retrieved_relationships` field on `RetrievedEntities`; `_finish` by_type bucket + `retrieval.relationship_count` span attr (reg 3).
- `sidequest/game/entity_sync.py` — `relationship_count` on `EntitySyncResult`; `_has_relationship_to_project` gate; project `rel:<slug>` in the NPC loop.
- `sidequest/server/dispatch/entity_sync.py` — `relationship_count` on the sweep span (`entity_sync.relationship_count`) + the published watcher event.
- `tests/game/test_entity_sync_stateful_npcs.py` — updated 2 pre-existing reproject-count assertions for the added relationship card (see Design Deviations).

**3-registration landing:** all three landed together (enum+namespace, SIGNAL_APPLICABILITY, retrieval by_type) so the live 84-1 scorer never sees a half-registered type. `test_score_card_on_relationship_does_not_fail_loud` (canary) and `test_unregistered_type_still_fails_loud` (No-Silent-Fallbacks guard) both green.

**Projection gate:** project `rel:<slug>` ONLY when the NPC has disposition history OR a non-neutral band (`_has_relationship_to_project`). Neutral + history-less NPC = coal, skipped (Diamonds and Coal). Observable via `relationship_count` (span + watcher), not silent. The AC-3 attitude-only fallback (non-neutral NPC, no beats → band-only card) is a separate axis and stays green.

**OTEL:** `retrieval.relationship_count` (span `retrieval.universal` + declared in the contract set); `entity_sync.relationship_count` (span `accretion.entity_sync` + the `entity_sync` watcher event field). GM-panel observable.

**Tests:** 26/26 new green (14 projector + 6 registration + 3 retrieval + 3 sync/wiring; the 1 intentional fail-loud guard stays green). Regression: retrieval+pertinence+84-4 span+entity_card 76, entity_sync+dispatch+store 308 — all passed. `ruff check` clean on all changed files.
**Branch:** feat/84-3-relationship-card-projector (committed; not pushed — SM finishes).

**Handoff:** To review (Chrisjen Avasarala).

### Reviewer-blocker fix (round 2) — §A2 floor-companion + render wiring

Reviewer REJECTED (valid Blocker, accepted): the rel card was projected/stored/scored but never reached the narrator — it surfaced only on the cosine path (which a named/present turn skips) and `session_helpers` never rendered `retrieved_relationships` into the prompt (dead wiring). Completed the wiring (not de-scoped — no other WI consumes `retrieved_relationships`). **4 connections:**
1. `sidequest/game/retrieval_orchestration.py:~216` — §A2 FLOOR-COMPANION: after the floor is built, collect each present-scene (`floor.full_profiles`) AND named (`player_referenced_npcs`) NPC's `rel:<slug>` card from the store into `floor_relationship_cards`; `_finish` merges them into the relationship bucket (deduped vs the fill) on EVERY return path including the `embed_skipped` early-return. NEW `relationship_card_id` helper in `entity_card.py` for the slug convention. **Frozen 84-1 `score_card`/`select_within_budget`/fill loop UNTOUCHED** — floor plumbing only.
2. `sidequest/server/session_helpers.py:~1151,1173` — render `retrieved_relationships` via `render_entity_section` into the new `retrieved_entity_relationships` field (mirrors npc/location/faction).
3. `sidequest/agents/orchestrator.py:~807` — `TurnContext.retrieved_entity_relationships: str | None = None`; plumbed at `session_helpers.py:~1282`.
4. `sidequest/agents/orchestrator.py:~2176` — registered `("retrieved_relationships", context.retrieved_entity_relationships)` in the Valley injection loop.

**Surfaced-set observability:** the `retrieval.relationship_count` span attr (already on `retrieval.universal`) now counts the SURFACED set (`len(rel_cards)` = fill + floor companions), not just the synced set.

**Tests:** 4 RED → green (2 §A2 named/present retrieval + 2 render-wiring... 3 render incl. the no-section zero-byte-leak); 23 correct held → full 84-3 set 30/30. Regression: orchestrator+session_helpers+turn_context+retrieval e2e 76, retrieval+frozen-scorer+84-4-span+entity 81, dispatch+entity_sync+store 298 — all passed. `ruff` clean; `pyright` clean on changed code (the one `orchestrator.py:3053 send_stream` error is PRE-EXISTING at HEAD, shifted +7 by this diff, not introduced here). Frozen 84-1 scorer + 84-4 contract untouched and green.

**Handoff:** To review (Chrisjen Avasarala) — re-review.

## Delivery Findings

No upstream findings.

### TEA (test design)
- **Gap** (blocking-if-missed): Adding `EntityType.RELATIONSHIP` to the enum ALONE breaks `pertinence.score_card` (`pertinence.py:147` raises on undeclared types) AND `EntityCard.new` (`_ID_NAMESPACE`). All THREE registrations must land together. AC-4 pins it; `test_score_card_on_relationship_does_not_fail_loud` is the canary.
- **Improvement** (non-blocking): REUSE `band_for` from `projection/relationships.py:27` for the attitude band — do NOT reinvent the 5-level thresholds, and do NOT touch the ADR-136 panel otherwise. The 2-3-beat `select_load_bearing_beats` is net-new (ADR-136 dumps the full log).
- **Improvement** (non-blocking): Projection is STORED via the per-turn `sync_entity_cards` sweep (`entity_sync.py:185`), not on-demand. Project the `rel:` card in the NPC loop with its own `relationship_count` tally so the GM panel doesn't under-report the relationship index.
- **Question** (non-blocking): Should a relationship card project for EVERY stateful NPC, or only those with non-empty disposition history / `last_seen_turn > 0` (the ADR-136 seen-gate)? The tests project for any NPC with a log and fall back to attitude-only on empty; Dev may want a seen-gate to avoid indexing relationship cards for never-met NPCs (mirrors `build_relationship_entries`). Flagged for Dev's judgment — not pinned by a test.

### Dev (implementation)
- **Improvement** (non-blocking): I gated projection on history-OR-non-neutral-band rather than the ADR-136 `last_seen_turn > 0` seen-gate. A non-neutral standing is itself "something to say" even if `last_seen_turn` is unset (e.g. a world-authored hostile faction-NPC). If a future story wants strict seen-gate parity with the player-facing `build_relationship_entries` panel, the gate is a single function (`_has_relationship_to_project`) — add `and npc.last_seen_turn > 0` there. Affects `sidequest/game/entity_sync.py`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `project_relationship_card` content order is `name — band — beat1 — beat2 — beat3`. The band uses the 5-level `band_for` ("Devoted"/"Warm"/"Neutral"/"Cool"/"Hostile"), distinct from the engine 3-level `Attitude` on the NPC card. The two cards (`npc:` and `rel:`) thus carry different band vocabularies for the same NPC by design (identity vs. standing) — a reviewer/UI consumer should not expect them to match. Affects `sidequest/game/entity_card.py`. *Found by Dev during implementation.*
- No blocking upstream findings.

## Design Deviations

None yet.

### TEA (test design)
- No deviations *in the first RED pass*. ACs derived from ADR-118 §A2/§A3/§A4 + live investigation (3-registration fail-loud chain, stored projection, `band_for` reuse).
- **AC CONTRACT CORRECTION (post-Reviewer-blocker, 2nd RED pass):** The first AC-6 + its test (`test_relationship_card_surfaces_in_retrieval`) were written to the IMPLEMENTATION's happy path — a seeded cosine embedding + a thin action — which MASKED the dead §A2 named/present path and the missing render seam, so the suite went green while the feature never reached the narrator (Reviewer's valid Blocker). **My fault: the test was written to what passes, not to §A2 intent.** Corrected this RED pass:
  - **AC-6 rewritten** to the §A2 FLOOR-COMPANION contract: a present/named NPC's rel card surfaces in `retrieved_relationships` BECAUSE the NPC is present/referenced (not via cosine), including the `embed_skipped=True` drama-gate-skip turn. The masked cosine-seed test was REPLACED with `test_named_present_npc_surfaces_relationship_card_on_gate_skip` (zero-vector rel card that can never win cosine, named+present action → rel card must still surface). Currently returns None → honest RED.
  - **AC-7 ADDED** (the render seam — the dead wiring the first GREEN shipped): new file `tests/server/test_relationship_card_render_wiring.py` drives `_build_turn_context` → `retrieved_entity_relationships` → `build_narrator_prompt` Valley section. No consumer today → RED.
  - **AC-8 test renamed** `test_relationship_card_live_retrieval_wiring` → `test_relationship_card_indexed_by_live_sync_for_turn` (it overclaimed; it proves INDEXING via `sync_for_turn`, not retrieval-to-narrator). Reviewer flagged the overclaim.
  - The original session/AC text OVERCLAIMED "complete wiring" with no deviation logged — fixed. The corrected contract states the real deliverable: rel card reaches the narrator for a present/named NPC (index → retrieve → render, no dead layers).
  - The correct pre-existing tests (projector, 3-registration, gate, summary-tier, sync indexing) stay GREEN — they were never the gap.
  - Severity: blocker (the masked test let dead code ship). Forward impact: Dev wires the floor-companion surfacing in `retrieve_turn_context` + the render in `session_helpers`/`orchestrator` (the frozen 84-1 fill loop is NOT touched).

### Dev (implementation)
- **Updated two pre-existing `test_entity_sync_stateful_npcs.py` reproject-count assertions for the added relationship card**
  - Spec source: context-story-84-3.md, AC-7 / story scope ("project the rel:<slug> card alongside npc:<slug> in the per-turn sync sweep")
  - Spec text: "project a `rel:<slug>` card for a stateful NPC with disposition history… alongside the `npc:<slug>` card"
  - Implementation: `sync_entity_cards` now projects a relationship card in the NPC loop (gated on history/non-neutral band). Two pre-WI-4 tests asserted `result.reprojected == 1` for an NPC whose band is non-neutral (disposition=50) — that NPC now ALSO yields a `rel:` card, so `reprojected == 2`. `test_promoted_npc_dedups_against_its_pool_origin` → assert `npc_count == 1` (the real dedup invariant it was proxying), `relationship_count == 1`, `reprojected == 2`. `test_stateful_band_change_reprojects_through_sync` → `reprojected == 2` (band crossing re-arms BOTH the npc card AND the rel card; the direct `embedding_pending is True` assertion on the npc card is unchanged).
  - Rationale: WI-4 deliberately adds a second card type to the sweep; these tests counted only the NPC card. Their original intent (dedup, band-change re-arm) is preserved — only the reproject totals were updated to include the new, correct relationship projection.
  - Severity: minor
  - Forward impact: none — the relationship-card projection is the AC-7 deliverable; these tests now reflect the post-WI-4 sweep shape.
- **Projection gate decision (TEA-deferred open question, SM steer):** project `rel:<slug>` ONLY when the NPC has disposition history (non-empty `disposition_log`) OR a non-neutral 5-level band — a neutral, history-less NPC is coal (Diamonds and Coal), so we don't flood the index with empty neutral relationship cards. The gate is explicit (`_has_relationship_to_project`) and observable: `relationship_count` (span `entity_sync.relationship_count` + watcher event field) advances only for gated, content-bearing cards. The empty-LOG attitude-only fallback (AC-3) is a different axis — a card IS projected for a non-neutral NPC with no beats (band-only content), tested green; the gate only suppresses the neutral+empty flood case.

## Reviewer Assessment — SUPERSEDED (84-3, commit 32773b0, REJECTED — blocker since closed by c7ef649)

> NOTE: This REJECTED assessment is SUPERSEDED by the re-review addendum below
> (commit c7ef649). Heading renamed so the approval-gate tag scan matches the
> final APPROVED section uniquely. The Blocker it raised was valid and is now
> confirmed closed — see "## Reviewer Assessment (84-3, commit c7ef649)".

**Reviewer:** Chrisjen Avasarala (adversarial review, Lap 4)
**Verdict (superseded):** REJECTED — one Blocker. The projector itself is correct and well-built, but the
RETRIEVAL→PROMPT pipeline the story headlines (§A2: a relationship card surfaces because its NPC is
named/present) is HALF-WIRED, and the AC-6 test masks the gap by exercising only the one path that
works. This trips the server's "No half-wired features — connect the full pipeline or don't start" rule.

**Scope reviewed:** full diff `develop...feat/84-3-relationship-card-projector` (746 +/3 -): EntityType.
RELATIONSHIP + 3 registrations, `project_relationship_card` + `select_load_bearing_beats`, the entity_sync
hook, `retrieved_relationships` field, OTEL, 4 new test files + 2 modified. Verified vs ADR-118 §A2/§A4 +
context ACs.

**Verification run (-n0 serial):**
- 84-3 suites + 2 modified: **36 passed**. Regression (84-1/84-2/84-4 scorer/orchestration/span/entity_card
  /dispatch): **87 passed**. `ruff check`: clean. Tree clean; subrepo HEAD 32773b0.

**Adversarial checks (8 observations):**
1. **Fail-loud 3-registration chain — ATOMIC, exhaustiveness mostly clean.** EntityType.RELATIONSHIP +
   `_ID_NAMESPACE["rel"]` + `SIGNAL_APPLICABILITY[RELATIONSHIP]` all land in this one commit — no
   half-registered window. Grepped EVERY EntityType use site: `entity_store` filters parametric (safe),
   `by_type.setdefault` generic + explicitly seeded (safe), `pertinence._applicable_signals` now declared
   (safe), no match/case exhaustiveness anywhere. `score_card` on a rel card does not raise (tested).
   **BUT see #2 — the consumers (`session_helpers` renderer, `universal_retrieval` watcher) DON'T handle
   the new typed bucket.**
2. **BLOCKER — the relationship card never reaches the narrator on the §A2 path (half-wired).** Two
   compounding gaps, both proven empirically:
   (a) **Never surfaces on named/present.** Rel cards are declared `{mention, here, recency}` — NO sim
   (§A2: "surfaces because the NPC is named/present, not topical cosine"). But the retrieval fill is
   populated ONLY by `entity_store.query_by_similarity` (cosine), and the fill loop hardcodes
   mention/here/recency=0 for every fill card — so a rel card can ONLY enter via the sim channel it is
   declared NOT to use, and scores 0 when it does. On the named/present turn (drama-gate skip) the fill is
   EMPTY, so the rel card never surfaces. I drove it: `"I attack Borin"` + present+referenced Borin +
   indexed `rel:borin` → `embed_skipped=True`, `retrieved_relationships=None`. The card surfaces ONLY on a
   THIN cosine action — the exact opposite of §A2.
   (b) **Even when surfaced, nothing consumes it.** `session_helpers.py` has ZERO references to
   `retrieved_relationships` — a surfaced rel card is never rendered into the narrator prompt; the
   `universal_retrieval` watcher never counts it. So the card the whole story exists to deliver never
   reaches the narrator on any turn.
   The AC-6 test (`test_relationship_card_surfaces_in_retrieval`) hides (a) by seeding the rel embedding to
   match the query vector and using a thin action — the one path that surfaces it. The AC-8 "live retrieval
   wiring" test only drives `sync_for_turn` (indexing), NOT `retrieve_turn_context` to a prompt — the name
   overclaims. The session (lines 30, 138) presents the wiring as complete; there is NO Design Deviation
   acknowledging the named/present path returns None. *Location: `retrieval_orchestration.py:300-355` (fill
   loop scores only sim; no per-card mention/here/recency), `pertinence.py:88` (RELATIONSHIP sim-less),
   `session_helpers.py:1155-1165` (no rel render), `tests/game/test_relationship_retrieval.py:86`
   (cosine-only test).*
3. **Beat selection — CORRECT.** `select_load_bearing_beats` = `reversed([b for b in log if b.delta!=0])
   [:limit]` — recency-first deterministic, non-zero-delta filter, cap-3 (no off-by-one, exclusive slice),
   empty/all-zero → [] (no crash). Source log is cap-10 (session.py:253 ring trim); even a >10 corrupt
   loaded log yields ≤3 beats — no content blow-up. Determinism holds (no set iteration).
4. **Band-vocab coexistence — SAFE.** npc card uses 3-level `Attitude` (FRIENDLY/NEUTRAL/HOSTILE); rel card
   uses 5-level `band_for` (Devoted/Warm/Neutral/Cool/Hostile). Different card types (`npc:`/`rel:`),
   isolated to their own content strings; grep confirms nothing downstream cross-compares or assumes they
   match. (Nit: `_has_relationship_to_project` compares `band_for(...) != "Neutral"` against a magic string
   literal — brittle if the band label ever changes.)
5. **2 modified tests — STRENGTHENED, not weakened (confirmed via git diff).** `test_entity_sync_stateful_
   npcs.py`: `reprojected == 1` → `== 2` (now also reprojecting `rel:borin`) and ADDED
   `relationship_count == 1`, while PRESERVING the guarded invariants (`npc_count == 1` dedup;
   `embedding_pending is True`). Comments explain why. Legit.
6. **Projection gate — CORRECT but see caveat.** `_has_relationship_to_project` = history OR non-neutral
   band — a sound "something to say" test (Diamonds and Coal); neutral+empty NPCs skipped (no flood). Gate
   is observable via `relationship_count` (not a silent skip). `band_for(int(npc.disposition))` is an O(1)
   threshold compare — cheap per-NPC in the sync sweep. AC-3 attitude-only fallback never blank (band always
   present). No dead code in the projector. (The gate is fine; the problem is downstream of it — #2.)
7. **Scorer + 84-4 OTEL intact — VERIFIED.** `pertinence.py` = 7 +/0 - (matrix row only, no logic touched).
   `retrieval.relationship_count` is BOTH declared (entity_card.py) AND emitted (retrieval_orchestration.py)
   — 84-4's bidirectional contract holds. `entity_sync.relationship_count` on span + watcher event.
8. **Determinism / No Silent Fallbacks (projector) — VERIFIED.** Sorted-alias JSON metadata, fixed beat
   order, `tier="summary"` always present. The projector half is clean.

**Findings:**

| Severity | Finding | Location |
|----------|---------|----------|
| **BLOCKER** | The relationship card never reaches the narrator on the §A2 named/present path (drama-gate empties the fill; rel cards are sim-less yet the fill is cosine-only) AND is never rendered by `session_helpers` even when surfaced. The AC-6 test masks this by testing only the thin-cosine path; the session claims complete wiring with no deviation note. Half-wired feature. **Fix options:** (a) compute per-card mention/here/recency in the fill so a present/named NPC pulls its `rel:` card (the 84-1-noted per-card-signal seam) AND render `retrieved_relationships` in `session_helpers`; OR (b) honestly de-scope retrieval-surfacing to a follow-on, land only the projector+index side, and rewrite AC-6 + the session claims to say "field + index only; retrieval surfacing deferred." Either is fine — but the current state ships a card that never reaches the narrator while claiming it does. | `retrieval_orchestration.py:300-355`, `pertinence.py:88`, `session_helpers.py:1155-1165`, `tests/game/test_relationship_retrieval.py:86` |
| Should-fix | AC-8 test `test_relationship_card_live_retrieval_wiring` is named "live retrieval" but only drives `sync_for_turn` (indexing) — it never calls `retrieve_turn_context` to prove the card surfaces in a prompt. Either add a real retrieval→prompt assertion (which today would fail on the §A2 path, exposing the Blocker) or rename to "live SYNC wiring." | `tests/server/test_relationship_card_sync_wiring.py:106` |
| Nit | `_has_relationship_to_project` compares `band_for(...) != "Neutral"` against a hardcoded string. If the 5-level band label changes, the gate silently mis-classifies. Consider a `band_for` companion constant or a numeric threshold. | `entity_sync.py` (`_has_relationship_to_project`) |

**Deviation audit:**
- TEA + Dev logged "No deviations." The 2 modified tests are properly logged + strengthened. **BUT** the
  named/present-surfacing gap is an UNDOCUMENTED deviation from §A2 / AC-6 — it should have been flagged as
  a Design Deviation (the implementation surfaces rel cards by cosine, not by the §A2 structural signals).
  Logging it under `### Reviewer (audit)`.

**Handoff:** Back to Dev. The projector, beat selection, gate, registrations, and OTEL are all correct and
mergeable — the rejection is solely the half-wired retrieval→narrator pipeline (#2). Quickest honest path
is option (b): de-scope retrieval surfacing to a stacked follow-on (it needs the per-card structured-signal
fill change that 84-1 explicitly deferred and that this story's own scope marks "out of scope: scorer
change" — the story is internally contradictory on this point), land the index-side projector now, and make
AC-6 + the session say what actually ships. If (a) is chosen, it's a larger change touching the frozen 84-1
fill loop + the renderer.

### Reviewer (audit)
- **UNDOCUMENTED deviation (blocking):** the relationship card surfaces in retrieval ONLY via the cosine
  fill on a thin action — NOT via the §A2 structural signals (mention/here) on a named/present turn, where
  the drama-gate empties the fill and `retrieved_relationships` returns None. It is also never rendered into
  the narrator prompt by `session_helpers`. The §A2 design and AC-6 both assert named/present surfacing;
  neither holds. Should have been logged as a Design Deviation. *Found by Reviewer during code review.*

## Reviewer Assessment (84-3, commit c7ef649)

**Reviewer:** Chrisjen Avasarala (re-review of the REJECT — Lap 4, blocker-fix)
**Verdict:** APPROVED — merge-ready. The Blocker is CLOSED. I found the pipeline dead; I have now
proven it alive end-to-end, at the actual narrator prompt, on the exact §A2 path I rejected — without
any frozen-scorer change. SM's "complete the wiring (not de-scope to dead code)" steer was honored.

**Fix mechanism reviewed (commit c7ef649 on top of projector core 32773b0):** FLOOR-COMPANION — a
present/named NPC's `rel:<slug>` card rides the floor (collected once at retrieval_orchestration.py ~:216,
merged in `_finish` ~:265 deduped by id), surfacing on EVERY return path including the `embed_skipped`
early-return. Render plumbed `session_helpers` → `TurnContext.retrieved_entity_relationships` → orchestrator
Valley injection loop. New `relationship_card_id()` single-source helper. `score_card`/`select_within_budget`
/fill loop NOT touched.

**Empirical re-verification (I drove the code, not just read it):**
1. **The EXACT dead path is ALIVE.** `"I attack Borin"`, Borin present + referenced, rel card with a
   **ZERO/cosine-losing vector** `[0,0,0]` → `embed_skipped=True`, `retrieved_relationships=['rel:borin']`.
   My original repro returned `None` here; it now surfaces via the FLOOR, provably not cosine (zero vector
   can't win similarity). **Alive.**
2. **Reaches the actual NARRATOR PROMPT.** Traced `_build_turn_context` (renders via `render_entity_section`
   → tagged `<retrieved_relationships>- Borin — Warm — saved the party from the ogre</retrieved_relationships>`
   block) → `TurnContext.retrieved_entity_relationships` → orchestrator Valley loop `register_section(...
   AttentionZone.Valley, SectionCategory.State)` — the IDENTICAL mechanism as the proven npc/location/faction
   siblings → `registry.compose(agent_name)` (orchestrator.py:2801) builds the LLM-visible prompt string. The
   render-wiring test asserts the section registers exactly once with the summary text in content. It does NOT
   stop at a struct field one layer up — I checked the consumer at every seam.
3. **Dedup CONFIRMED.** Rel card arriving via BOTH floor-companion AND cosine fill → appears exactly once
   (`['rel:borin']`). The `_finish` merge dedups by id (`fill_rel_cards + [floor not in _rel_ids]`).
4. **ALL return paths populate it.** Drove each: `success`/embed_skipped → `['rel:borin']`; daemon-down
   (`query_failed`) → `['rel:borin']`; blank-query (`query_failed`) → `['rel:borin']`. No path drops it —
   the companion is collected BEFORE the early returns and merged in `_finish` (which runs on every path).
5. **Frozen scorer + 84-4 intact.** `pertinence.py` untouched by the fix (empty numstat); `score_card`/
   `select_within_budget` have zero logic deltas across the whole branch vs develop. `retrieval.relationship_
   count` is BOTH declared in `UNIVERSAL_RETRIEVAL_SPAN_ATTRS` AND emitted (line 290) — 84-4's bidirectional
   contract holds. The count is `len(rel_cards)` = the merged SURFACED set (fill+floor, deduped) — honest
   "surfaced," not "synced."
6. **No new exhaustiveness break.** The Valley injection loop is data-driven (a tuple of (name, body) pairs)
   — no section-name allowlist/switch that would reject `retrieved_relationships`; grep found none.
   `render_entity_section` is generic. The `contextlib.suppress(ValueError)` around the companion lookup
   correctly tolerates a blank-name `_slug` raise without dropping the rest.
7. **Tests strengthened, not weakened.** The masked AC-6 (`test_relationship_card_surfaces_in_retrieval`,
   thin-action npcs=[] — the path that hid the gap) was REPLACED by `test_named_present_npc_surfaces_
   relationship_card_on_gate_skip` (zero vector, present+referenced, asserts `embed_skipped is True` AND the
   card surfaces via floor) — the exact contract I demanded, written RED-first by TEA. The new
   `test_relationship_card_render_wiring.py` (3 tests) pins the prompt-injection seam. Full 84-3 set + render
   wiring **40 passed**; regression (84-1/84-2/84-4 scorer/orchestration/span/contract/dispatch) **87 passed**;
   `ruff check` clean. The 23 correct tests stay green — none weakened to accommodate the rewire.

**Findings:** none blocking. The two non-blocking items from my original REJECT remain advisory:
- **Should-fix (carried, downgraded to Nit):** the AC-8 sync-wiring test name still says "live retrieval"
  though it drives only `sync_for_turn` — but the NEW `test_relationship_card_render_wiring.py` now provides
  the genuine retrieval→prompt coverage, so the misnomer is cosmetic. `test_relationship_card_sync_wiring.py:106`.
- **Nit (carried):** `_has_relationship_to_project` compares `band_for(...) != "Neutral"` against a magic
  string literal. `entity_sync.py`.

**Deviation audit (re-review):** the §A2 surfacing deviation I logged under `### Reviewer (audit)` is now
RESOLVED by c7ef649 — the floor-companion mechanism makes the implementation match §A2 ("surfaces because
the NPC is named/present"). The fix is honestly documented in the session (the "4 connections" note) and the
masked test was replaced with a true contract.

**Handoff:** To SM for finish-story. Blocker closed, end-to-end aliveness proven at the prompt. Merge-ready.
