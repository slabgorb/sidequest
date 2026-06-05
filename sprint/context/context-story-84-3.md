# Story 84-3 Context

## Title
WI-4 Relationship card projector (index-side, summary-tier projection of disposition_log → attitude + key beats)

## Metadata
- **Story ID:** 84-3
- **Type:** story
- **Points:** 3
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** 84 — ADR-118 Amendment — Unified Pertinence Scorer & Tiered Forgetting
- **Stack parents (merged):** 84-1 (pertinence scorer), 84-4 (OTEL decomposition), 84-2 (alias resolution)

## Problem
ADR-118 §A2 widens the index scope to include **`relationship`** as a first-class indexed
type; §A4 specifies the relationship card is **born at SUMMARY tier** — current attitude band +
the two or three *load-bearing* beats — because the `disposition_log` (ADR-136) is a time series
that cannot be embedded whole. Today there is NO relationship card: the universal index holds
only `npc | location | faction`, so the narrator gets no compact, retrievable projection of an
NPC's relationship history (it must read the whole log or nothing). WI-4 adds the index-side
projector.

## Investigation findings (codebase, confirmed this RED phase)

### Decision 1 — `EntityType.RELATIONSHIP`: new enum member + THREE registrations (or the 84-1 scorer fails loud)
- `EntityType` (`entity_card.py:39`) currently has only `NPC | LOCATION | FACTION`. Adding
  `RELATIONSHIP = "relationship"` requires registering it in **three** places or downstream
  fails loud:
  1. **`_ID_NAMESPACE`** (`entity_card.py:55`) — `EntityCard.new` raises `ValueError("unknown
     entity_type … add it to _ID_NAMESPACE")` otherwise. Recommended id namespace: **`rel`**
     (so ids read `rel:borin`, distinct from `npc:borin`).
  2. **`SIGNAL_APPLICABILITY`** (`pertinence.py:80`) — **THE load-bearing one.**
     `pertinence._applicable_signals` (`pertinence.py:147-152`) **`raise ValueError` on any
     EntityType not in the matrix** (No Silent Fallbacks). So adding the enum member WITHOUT a
     `SIGNAL_APPLICABILITY` entry **breaks `score_card` the moment a relationship card is
     scored** in `retrieve_turn_context`. The tests MUST pin this: enum + applicability land
     together, and `score_card` on a relationship card does NOT raise.
     Recommended applicable signals: **`{mention, here, recency}`** (NOT `sim`). §A2: "a
     relationship surfaces because the related NPC is named or present — the NPC's
     floor-presence (or a mention) pulls the relationship card in." It rides the NPC's
     structural signals; topical cosine is the NPC/lore card's job, not the relationship's.
  3. **`retrieve_turn_context._finish` `by_type`** (`retrieval_orchestration.py:228-236`) — the
     dict seeds only NPC/LOCATION/FACTION and surfaces only `retrieved_npcs/locations/factions`.
     A relationship card would land via `setdefault` but never reach a `RetrievedEntities`
     field. WI-4 adds `retrieved_relationships` (mirrors AC-5).

### Decision 2 — Projection is STORED (per-turn sync), not on-demand at retrieval
- Cards enter the index via `entity_sync.sync_for_turn` (`entity_sync.py:185` —
  `for npc in snapshot.npcs: project_npc_card(npc)` → `_apply_typed_card(... "npc_count")`), the
  §D3 dirty-flag reproject sweep. WI-4 projects the relationship card **alongside the NPC card in
  that same loop** (for each `snapshot.npcs` member with disposition history), giving it a new
  typed slice + a `relationship_count` reproject tally. This matches §D3; it is NOT an on-demand
  retrieval-time projection.

### Decision 3 — ADR-136 reuse: REUSE `band_for`, the beat SELECTION is NET-NEW
- `sidequest/game/projection/relationships.py` (ADR-136, the **player-facing** RELATIONSHIPS
  panel) is the SoT for disposition presentation and is ORTHOGONAL to WI-4, BUT it holds
  reusable helpers WI-4 must NOT duplicate:
  - **`band_for(value: int) -> str`** (line 27) — disposition int → 5-level display band
    (Devoted/Warm/Neutral/Cool/Hostile). This is the **attitude band** the §A4 card wants — use
    it (the richer 5-level band, distinct from the 3-level engine `Attitude` enum FRIENDLY/
    NEUTRAL/HOSTILE in `disposition.py:95`). Don't reinvent the band thresholds.
  - **`trend_for(beats)`** (line 40) — optional, if the card carries a trend hint.
  - **NET-NEW (does NOT exist):** the "select 2-3 **load-bearing** beats" summarization.
    `build_relationship_entries` (line 83-86) dumps the **ENTIRE** `disposition_log` into the
    payload (the panel deliberately shows the full log). The SUMMARY-tier *abbreviation*
    (recency + non-zero-delta filter → 2-3 beats) is genuinely new WI-4 work. Do not assume
    ADR-136 has it; it doesn't.

### Source facts (corrections to the setup brief)
- `DispositionBeat` (`disposition.py:79`): fields `turn: int`, `delta: int`, `reason: str`,
  `location: str | None`. `DISPOSITION_LOG_CAP = 10` (`disposition.py:66`).
- The engine `Attitude` enum is **3-level** (FRIENDLY/NEUTRAL/HOSTILE), NOT the 5-level the brief
  listed. For the card's "attitude band" use ADR-136's 5-level `band_for`, OR the 3-level
  `Disposition.attitude()` — Dev's call, but the test pins that SOME attitude band is in content.
- `EntityCard.metadata: dict[str, str]` is live; `project_npc_card` already JSON-encodes sorted
  aliases into `metadata["aliases"]` (84-2) — the relationship card mirrors that.

## Technical Approach
1. **`EntityType.RELATIONSHIP = "relationship"`** + `_ID_NAMESPACE[RELATIONSHIP] = "rel"` +
   `SIGNAL_APPLICABILITY[RELATIONSHIP] = frozenset({mention, here, recency})`.
2. **`project_relationship_card(npc: Npc) -> EntityCard`** (`entity_card.py`, beside the other
   projectors). Stateful `Npc` only (relationships are promoted-NPC-only). Content =
   attitude band (reuse `band_for`) + the 2-3 load-bearing beats' reasons. A net-new pure
   `select_load_bearing_beats(log, *, limit=3) -> list[DispositionBeat]`: most-recent first,
   non-zero-delta only, capped at the limit. Empty/all-zero log → attitude-band-only card (no
   beats), never a blank-content card (EntityCard rejects blank content). Aliases →
   `metadata["aliases"]` (sorted, JSON) like `project_npc_card`. **Deterministic**: same npc
   state → same content (75-6 reproject relies on it).
3. **`RetrievedEntities.retrieved_relationships: list[EntityCard] | None`** + surface it in
   `_finish` `by_type`.
4. **`entity_sync.sync_for_turn`** projects the relationship card alongside the NPC card (new
   `relationship_count` reproject tally + OTEL `card_reproject_count`-style observability).
5. The relationship card SUMMARIZES — it must NOT embed the full log (the cap-10 time series).

## §A2 mechanism decision (TEA + Dev, post-Reviewer-blocker) — FLOOR-COMPANION
**The deliverable is: a present/named NPC's relationship card REACHES THE NARRATOR PROMPT.**
Reviewer (rightly) blocked the first GREEN: the card was indexed but never reached the narrator
on the §A2 named/present path, and `session_helpers` never rendered `retrieved_relationships`.
The first AC-6 test masked this by seeding a cosine match + thin action — the one path that
worked — so it went green while the feature was dead. SM ruling: COMPLETE the wiring (a card no
consumer reads is dead code — "No half-wired features"); do NOT de-scope to an index-only
projector.

**Mechanism (no change to the frozen 84-1 fill scorer):** a present/named NPC's `rel:<slug>`
card rides the **FLOOR** — it surfaces in `retrieved_relationships` BECAUSE the NPC is
scene-present or player-referenced (the §A2 "surfaces because the related NPC is named or
present"), not via cosine. `retrieve_turn_context` collects the rel cards for the floor's NPCs
(present-scene + `player_referenced_npcs`) from the store and emits them in
`retrieved_relationships` on every turn — INCLUDING the drama-gate-skip turn where the cosine
fill is empty. Then `session_helpers._build_turn_context` renders them into a
`retrieved_entity_relationships` `TurnContext` field and `Orchestrator.build_narrator_prompt`
registers a `retrieved_relationships` Valley section — exactly the seam the NPC/location/faction
fills already use (`session_helpers.py:1154-1166`, `orchestrator.py:2168-2182`). This is
strictly additive to the floor + render plumbing; the 84-1 `score_card`/`select_within_budget`
fill loop is untouched.

## Scope
- **In scope:** `EntityType.RELATIONSHIP` + its 3 registrations; `project_relationship_card` +
  `select_load_bearing_beats`; the SUMMARY-tier content; deterministic projection + alias
  metadata; the entity_sync projection hook + its OTEL observability; **the §A2 floor-companion
  surfacing (present/named NPC → rel card in `retrieved_relationships`, including the
  embed-skip turn); the session_helpers + orchestrator RENDER so the card reaches the narrator
  prompt** (the load-bearing deliverable).
- **Out of scope:** the ADR-136 player-facing panel (orthogonal — do not touch
  `projection/relationships.py` beyond *importing* `band_for`); tiered demotion/rehydration
  (WI-3/84-6 — the card is born SUMMARY and stays SUMMARY here, no demote logic); faction/
  location relationship cards (NPC-relationships only); any scorer/weight change (84-1 frozen —
  WI-4 only adds the type + its applicability row).

## Acceptance Criteria

> Each AC has failing test coverage written in the RED phase (see Test Coverage).

- **AC-1 — `project_relationship_card` summary-tier content.** Projecting an `Npc` with a
  populated `disposition_log` yields an `EntityCard` whose content carries the **attitude band**
  and **2-3 load-bearing beat reasons** — and does NOT contain the full log (a >3-beat log
  surfaces at most 3 beats). *Tests:* `test_card_content_has_attitude_band`,
  `test_card_content_has_load_bearing_beats`, `test_card_never_embeds_full_log`.

- **AC-2 — Load-bearing beat selection (recency + non-zero delta).** `select_load_bearing_beats`
  returns the most-recent non-zero-delta beats, capped at the limit; zero-delta beats are
  excluded; an empty or all-zero log returns `[]`. *Tests:*
  `test_select_beats_drops_zero_delta`, `test_select_beats_most_recent_first`,
  `test_select_beats_caps_at_limit`, `test_select_beats_empty_log_returns_empty`.

- **AC-3 — Attitude-only fallback (empty/all-zero log).** An `Npc` with an empty (or all-zero)
  `disposition_log` projects a valid card carrying ONLY the attitude band (no beats) — never a
  blank-content card (No Silent Fallbacks: EntityCard rejects blank content, so the fallback
  must still produce non-blank content). *Tests:* `test_empty_log_projects_attitude_only_card`,
  `test_empty_log_card_content_not_blank`.

- **AC-4 — `EntityType.RELATIONSHIP` registered everywhere, NO fail-loud regression.**
  `RELATIONSHIP` is in `EntityType`, `_ID_NAMESPACE` (id `rel:<slug>`), AND `SIGNAL_APPLICABILITY`
  — and `pertinence.score_card` on a relationship card does NOT raise `ValueError` (the 84-1
  fail-loud guard is satisfied). *Tests:* `test_relationship_entity_type_registered`,
  `test_relationship_in_id_namespace`, `test_relationship_in_signal_applicability`,
  `test_score_card_on_relationship_does_not_fail_loud`.

- **AC-5 — Deterministic projection.** The same `Npc` state projects to byte-identical card
  content + metadata every time (75-6 dirty-flag reproject relies on it); beat ordering and
  alias serialization are stable. *Tests:* `test_projection_is_deterministic`,
  `test_aliases_sorted_in_metadata`.

- **AC-6 — §A2 floor-companion: a present/named NPC's relationship card surfaces in
  retrieval — INCLUDING the embed-skip turn.** `retrieve_turn_context` returns the rel card in
  `retrieved_relationships` BECAUSE the NPC is scene-present or `player_referenced`, NOT via
  cosine. The load-bearing case: a NAMED + present action ("I attack Borin") triggers the 84-1
  drama-gate skip (`embed_skipped=True`) and the cosine fill is empty — yet the rel card MUST
  still surface (it rides the floor; a zero-vector rel card that can never win cosine still
  surfaces). An NPC who is neither present nor named does NOT pull its rel card → `None`
  (zero-byte-leak). *Tests:*
  `test_named_present_npc_surfaces_relationship_card_on_gate_skip`,
  `test_present_npc_relationship_card_does_not_need_cosine`,
  `test_absent_npc_relationship_card_not_surfaced`,
  `test_retrieved_relationships_field_exists`.

- **AC-7 — RENDER: the relationship card reaches the narrator prompt (the real deliverable).**
  `session_helpers._build_turn_context` renders a populated `retrieved_relationships` into a
  `retrieved_entity_relationships` `TurnContext` field, and `Orchestrator.build_narrator_prompt`
  registers it as a `retrieved_relationships` Valley section carrying the summary — mirroring
  the NPC/location/faction fills. No card → no section (zero-byte-leak). *Tests:*
  `test_build_turn_context_renders_relationship_section`,
  `test_relationship_section_reaches_narrator_prompt`,
  `test_no_relationship_registers_no_section`.

- **AC-8 — OTEL: projection/reproject is observable.** When the entity-sync sweep projects a
  relationship card it is counted (`relationship_count` reproject tally) on the
  `accretion.entity_sync` span + watcher event, so the GM panel verifies the card is
  engine-projected. *Tests:* `test_sync_counts_relationship_reprojects`,
  `test_relationship_card_indexed_by_live_sync_for_turn` (the live `sync_for_turn` INDEXING
  proof — scope-honest: it proves storage + counting, NOT retrieval-to-narrator, which AC-6/AC-7
  cover).

- **AC-9 — Quality gate.** All ACs have failing coverage before GREEN; tree clean; correct
  branch (`feat/84-3-relationship-card-projector`); `just server-check` green; no fail-loud
  regression in the 84-1 scorer (and the fill loop untouched — floor-companion + render only);
  the projection emits OTEL. **No dead wiring: every layer added has a non-test consumer
  (index → retrieve → render → narrator prompt).**

## Test Coverage (RED — failing tests in place)
- `sidequest-server/tests/game/test_relationship_card_projector.py` — `project_relationship_card`
  + `select_load_bearing_beats` (AC-1, AC-2, AC-3, AC-5). Synthetic `Npc` + `disposition_log`.
- `sidequest-server/tests/game/test_relationship_entity_type.py` — `EntityType.RELATIONSHIP` 3
  registrations + the 84-1 fail-loud guard (AC-4). Run `-n0` if any scorer span.
- `sidequest-server/tests/game/test_relationship_retrieval.py` — **§A2 floor-companion**: a
  named/present NPC's rel card surfaces in `retrieved_relationships` on the embed-skip turn (no
  cosine), absent NPC → None (AC-6). Run `-n0` (retrieval span).
- `sidequest-server/tests/server/test_relationship_card_render_wiring.py` — **the render seam**:
  `_build_turn_context` → `retrieved_entity_relationships` → `build_narrator_prompt` Valley
  section (AC-7). The card reaches the narrator prompt. Run `-n0`.
- `sidequest-server/tests/server/test_relationship_card_sync_wiring.py` — entity-sync projection
  + OTEL + live INDEXING via `sync_for_turn` (AC-8 — scope-honest, indexing only). Run `-n0`.

## Notes for Dev
- **The fail-loud is the trap.** Adding `EntityType.RELATIONSHIP` to the enum alone breaks
  `pertinence.score_card` (`pertinence.py:147` raises on undeclared types) AND `EntityCard.new`
  (`_ID_NAMESPACE` KeyError→ValueError). Land all THREE registrations together. AC-4 pins it.
- **REUSE `band_for`** from `projection/relationships.py:27` for the attitude band — don't
  reinvent the 5-level thresholds. But the **2-3-beat selection is net-new** — ADR-136 dumps the
  full log; the SUMMARY-tier abbreviation is yours to write (a pure
  `select_load_bearing_beats`). Don't touch the ADR-136 panel code beyond importing `band_for`.
- **Projection is STORED** via `entity_sync.sync_for_turn` (`entity_sync.py:185` NPC loop), not
  on-demand. Project the relationship card in that loop with its own reproject tally.
- **Determinism is load-bearing** (75-6 reproject): sort aliases, fix beat order (most-recent
  first), no `set` iteration in content. AC-5 pins it.
- **Never embed the full log** — the card SUMMARIZES (cap-10 time series → 2-3 beats). AC-1 pins
  the abbreviation; the embedding vector must key on the summary, not the granular log.
- **§A2 FLOOR-COMPANION (the Reviewer-blocker fix — the load-bearing work):** the rel card must
  reach `retrieved_relationships` because its NPC is present/named, NOT via cosine. In
  `retrieve_turn_context`, after the floor is built, collect the `rel:<slug>` card from the store
  for each floor NPC (the `floor.full_profiles` present-scene set + the `player_referenced_npcs`
  named set) and put them in `retrieved_relationships` — on EVERY turn, including the
  `embed_skipped=True` drama-gate-skip path (where the cosine fill is empty and returns early).
  This is the path AC-6 pins; a zero-vector rel card (never wins cosine) must still surface. Do
  NOT touch the 84-1 `score_card`/`select_within_budget` fill loop — this is floor plumbing.
- **RENDER the card or it's dead code (the other half of the blocker):**
  `session_helpers._build_turn_context` (`session_helpers.py:1151-1166`) renders
  `retrieved_npcs/locations/factions` into `retrieved_entity_*` strings — add a
  `retrieved_entity_relationships` rendered via `render_entity_section("retrieved_relationships",
  ...)`. Add the `retrieved_entity_relationships: str | None` field to `TurnContext`
  (`orchestrator.py:804-806`) and the `("retrieved_relationships", context.retrieved_entity_relationships)`
  entry to the section-registration loop (`orchestrator.py:2168-2171`). AC-7 pins the full chain
  to the assembled prompt.
- The retrieval consumer (`session_helpers` render + `universal_retrieval` watcher) reads the
  existing `retrieved_*` fields — add `retrieved_relationships` without breaking them.

---
_Acceptance criteria authored by TEA (Amos Burton) in the RED phase from ADR-118 §A2/§A3/§A4 +
live codebase investigation (3-registration fail-loud chain; stored-not-on-demand projection;
ADR-136 `band_for` reuse, beat-selection net-new). **Revised post-Reviewer-blocker: AC-6 corrected
from the cosine-masked happy path to the §A2 floor-companion intent; AC-7 added for the
render-to-narrator seam (the dead wiring the first GREEN shipped). The deliverable is the rel card
reaching the narrator for a present/named NPC — index → retrieve → render, no dead layers.**_
