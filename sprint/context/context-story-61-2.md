---
parent: context-epic-61.md
workflow: tdd
---

# Story 61-2: Extend snapshot drop-list — per-field decisions for the growing fields

## Business Context

This is the actual root cause of the 2026-05-23 cost-runaway incident
(~$313/48h). `snapshot.model_dump()` at
`session_helpers.py:559` flows into the Valley/Recency `system_blocks`
**uncached** (`cache=False` at `orchestrator.py:3437-3441`), multiplied by
up to 8 tool-loop iterations per turn. ADR-110 Phase B shipped a DROP
list with four fields (`active_tropes`, `axis_values`, `genie_wishes`,
`achievement_tracker`) — **none of those four grow**. The epic-named
seven candidate fields (`room_states`, `journal`, `npcs`, `known_facts`,
`footnotes`, `belief_state`, `location_descriptions`) are where the
session-length cost growth actually lives.

**Red-phase validation discovery (load-bearing):** the seven epic-named
fields do **NOT** all live at the top level of `GameSnapshot`. Three of
them are not snapshot fields at all; two are nested. The decision table
below corrects this against the live code.

## Field Reality Audit — what's actually in `snapshot.model_dump()`

`GameSnapshot.model_fields` enumerates 49 top-level fields. Audit
(`uv run python -c "from sidequest.game.session import GameSnapshot; print(sorted(GameSnapshot.model_fields.keys()))"`):

| Epic-named field | Top-level on `GameSnapshot`? | Reality | Growing? |
|---|---|---|---|
| `room_states` | YES (`session.py:752`) | `dict[room_id, RoomState]` — `RoomState` holds container retrieval state | YES — grows with rooms visited |
| `journal` | **NO** | Not a snapshot field at all. The "journal" UI surface (`JournalRequestHandler`, `handlers/journal_request.py`) is derived from `Character.known_facts` + event log — there is no `snapshot.journal` to drop. | N/A (not in dump) |
| `npcs` | YES (`session.py:600`) | `list[Npc]`. Each `Npc` carries a nested `belief_state` and `last_seen_location` | YES — grows with NPCs encountered/materialized |
| `known_facts` | **NO** — nested on `Character` (`character.py:100`) | `list[KnownFact]` per PC. Lives inside `characters[*].known_facts` in the dump | YES — grows monotonically as PCs learn facts |
| `footnotes` | **NO** | Not a snapshot field. `footnotes` is a per-turn `NarrationResult` field (`orchestrator.py:452`) and journal-feed payload; persisted into the event log, never into `snapshot` | N/A (not in dump) |
| `belief_state` | **NO** — nested on `Npc` (`session.py:175`) | `BeliefState` per Npc. Lives inside `npcs[*].belief_state` in the dump. Also `snapshot.scenario_state.discovered_clues` grows | YES — grows via gossip / clue discovery |
| `location_descriptions` | **NO** | Not a snapshot field. ADR-109 location descriptions ride out-of-band via the `LOCATION_DESCRIPTION` WebSocket message (loaded from `cookbook/assemble.py` at room change). The "growing field" the epic asserts does not exist in `snapshot.model_dump()` | N/A (not in dump) |

**Implication.** This story's actual scope is narrower than the epic
preamble implied: only `room_states`, `npcs`, `known_facts` (nested),
and `belief_state` (nested) are real snapshot bloat sources. The other
three (`journal`, `footnotes`, `location_descriptions`) are red herrings
relative to the snapshot-dump cost surface — they are real growing
subsystems, but they don't ride into `<game_state>` so they cannot be
the source of the Valley/Recency runaway via this path.

This is recorded as a **finding** (not a blocker): the cost-runaway
diagnosis still stands — `room_states` + `npcs[*].belief_state` +
`characters[*].known_facts` alone account for monotonic per-turn
growth, and 8× tool-loop multiplication makes any of them cost-fatal.

## Per-Field Decision Table (validated)

| Field | Snapshot location | Decision | Rationale | Test coverage required |
|---|---|---|---|---|
| `room_states` | top-level | **Project to current-room only** | `_build_turn_context` already reads `current_room_state = snapshot.room_states.get(current_room_id)` at line 627. The narrator only needs the active room's container state; other rooms' container state is dungeon-graph territory (ADR-055), addressable via RAG / dedicated future tool. Drop other room entries from the serialized dump. | populated 5-room fixture → only acting PC's current room id appears under `room_states` in `state_summary` |
| `npcs` | top-level | **Project to in-scene NPCs only** | "In-scene" = `Npc.last_seen_location == party_location` OR `Npc` listed in `encounter.participants`. Other NPCs (cast pool, off-stage) are anti-confabulation anchors but the narrator does NOT need their full nested record every turn — `npc_pool` lists identity, RAG/`query_npc` retrieves details on demand. **Gaslighting-doctrine guard:** `npcs` survives in some form; the dropped entries must be RAG-retrievable | fixture with 5 NPCs (2 in scene, 3 off-stage) → only the 2 appear in the dump's `npcs` list. Off-stage names still appear in `npc_pool` so the narrator can cite them |
| `known_facts` (nested) | `characters[*].known_facts` | **Project to last K=8 entries per PC** | `persistence.py:889` already uses a tail-of-8 pattern for journal renders. Keep symmetric. The narrator needs recency for continuity; older facts ride via RAG. | fixture with 1 PC carrying 25 known_facts → in the dump, that PC's `known_facts` is length 8, ordered tail-most-recent |
| `belief_state` (nested) | `npcs[*].belief_state` | **Drop entirely from `npcs` in dump** | The narrator does not name belief atoms in prose; it gets disposition/personality via dedicated NPC sections. Belief evolution is dispatch-side (gossip propagation, ADR-053), not prompt-side. Future RAG retrieval through `query_npc_belief` if needed | fixture: NPC with populated belief_state → in the dump that NPC entry has no `belief_state` key (or `belief_state == {}`) |
| `scenario_state.discovered_clues` | nested via `scenario_state` | **Cap to K=12 most-recent** | Parallel to `known_facts`; clue graph is RAG-shaped (ADR-053) | fixture: scenario_state with 30 discovered_clues → dump has ≤12 |
| `journal` | not in snapshot | **NO-OP — confirm absence** | Field is not in the snapshot dump; no slim work needed; record as finding | regression assertion: `assert "journal" not in payload` (already true; guard against future regression) |
| `footnotes` | not in snapshot | **NO-OP — confirm absence** | `footnotes` is a NarrationResult per-turn field, not a snapshot field. Guard against future regression where a developer materializes it onto the snapshot | regression assertion: `assert "footnotes" not in payload` |
| `location_descriptions` | not in snapshot | **NO-OP — confirm absence + ADR-109 regression guard** | The proximate-trigger field cited in the epic. ADR-109's storage is out-of-band via `LOCATION_DESCRIPTION`. Adding this field to `GameSnapshot` later WITHOUT extending the drop list is exactly the regression the architecture gate (61-5) blocks | regression assertion: `assert "location_descriptions" not in payload` AND `assert "location_description" not in payload` AND `assert "location_entities" not in payload` |

## Open Questions for Dev

1. **RAG fixture shape for `npcs` projection.** The "in-scene NPCs only" filter
   needs a deterministic `is_in_scene(npc, snapshot, perspective)` helper.
   Two viable signatures:
   - by location: `npc.last_seen_location == snapshot.party_location(perspective=char_name)`
   - by encounter: `encounter is not None and not encounter.resolved and npc.core.name in encounter.participants` (if the encounter model supports it)
   
   Recommend: union of both. Define helper at the seam, not inline.

2. **`known_facts` window size.** K=8 mirrors `persistence.py:889` but the
   journal pipeline (ADR-100) may have its own opinion. Confirm by reading
   `commit_known_fact.py` + `persistence.py:873-890` and pick the value Dev
   agrees feels right; cite both call sites.

3. **`scenario_state.discovered_clues` is a set, not a list.** Ordering is
   not preserved. "Most-recent" requires either a parallel list or a
   discovery-timestamp field. If neither exists, fall back to "any 12" and
   note as a follow-up — but flag it loudly. (Tests for this case will
   verify the size cap only; ordering is best-effort.)

4. **Should the Valley/Recency block at `orchestrator.py:3437-3441` get
   re-zoned post-slim?** If `state_summary` shrinks enough that it becomes
   stable-shaped (low entropy across turns), it could potentially move to a
   cached block. Out of scope here per ADR-110 §Phase B; flagged as
   information for 61-3/61-4/61-5.

5. **`npc_pool` is the gaslighting fallback for dropped NPCs.** Confirm
   that `snapshot.npc_pool` already contains identity entries for every
   `npc` the projection might drop — otherwise the narrator loses the
   ability to even cite the off-stage name and confabulates. If
   `npc_pool` is not exhaustive, the projection cannot land as drawn.

## Technical Guardrails

- **Source ADRs:**
  - `docs/adr/110-game-state-snapshot-slimming.md` — Phase A (compact
    encoding, SHIPPED) + Phase B (DROP list, SHIPPED but incomplete).
    §Implementation Notes: "DROP list is reviewed at every PR that adds
    a `GameSnapshot` field … schema-validation hook does not enforce
    this today" — 61-5 enforces; 61-2 lands the corrected DROP +
    projection.
  - `docs/adr/053-scenario-system.md` — clue graph / belief state
    grow shape. Belief propagation is dispatch-side, not prompt-side.
  - `docs/adr/104-perception-filtering-tool-layer.md` — perception
    filter is wired for tool responses (see
    `narrator_perception_filter.py`), NOT for the snapshot dump. The
    epic's claim that "perception filter already isolates in-scene
    NPCs" is correct at the tool-result layer; this story extends the
    same logical filter to the snapshot dump.
  - `docs/adr/100-journal-pipeline-coherence.md` — journal pipeline.
    Confirms `journal` is event-log derived, not a snapshot field.
  - `docs/adr/109-persistent-location-descriptions-mechanical-manifest.md`
    — `LOCATION_DESCRIPTION` rides out-of-band. Snapshot does not carry it.

- **Edit sites:**
  - `sidequest-server/sidequest/server/session_helpers.py:64` — extend
    `_PHASE_B_DROP_FIELDS` for true top-level drops (none of the
    seven add here; the existing four stay).
  - `sidequest-server/sidequest/server/session_helpers.py:559-571` —
    after `model_dump`, apply the new projections **on the dict
    in-place** (same pattern as the existing `pop("narrative_log")`
    and character-list redaction). This keeps the seam local and
    auditable.
  - Recommend: extract a `_apply_phase_b_projections(payload, snapshot,
    char_name)` helper to keep `_build_turn_context` readable.

- **Anti-confabulation anchors (gaslighting doctrine) — MUST survive:**
  - `characters` (top-level, with redaction by notorious-party gate
    only) — already tested at `test_57_5_snapshot_slimming.py::test_anchor_preserved_characters_with_content`
  - `npcs` — must remain present, but with in-scene projection
    applied. **A test must assert `npcs` is still a list and contains
    the in-scene names** (don't strip to empty).
  - `quest_log`, `character_locations`, `current_region` — already tested.
  - `npc_pool` — the identity-only roster of off-stage NPCs. The
    projection drops bodies from `npcs` but the narrator must still be
    able to cite the names; `npc_pool` is the seam.

- **No silent fallbacks:** If a projection removes an entry that a
  consumer reads downstream, the consumer must read from a real seam
  (RAG, dedicated section, projection) — not silently fall back to
  empty defaults.

- **No source-text wiring tests** (per `sidequest-server/CLAUDE.md`).
  Tests drive the production code path (`_build_turn_context`) and
  assert on the resulting `state_summary` payload, not on grep of
  `session_helpers.py`.

## AC Context

| AC | Detail |
|----|--------|
| AC1 — `room_states` projection | Snapshot fixture with N≥5 rooms in `room_states` → only the acting PC's `current_room` id is present in `state_summary["room_states"]`. Other room ids are gone. |
| AC2 — `npcs` in-scene projection | Snapshot fixture with 5 NPCs (2 in-scene by `last_seen_location`, 3 off-stage) → `state_summary["npcs"]` contains exactly the 2 in-scene NPCs. Off-stage names appear in `npc_pool` (anchor) and NOT in `state_summary["npcs"]`. |
| AC3 — `npcs` belief_state drop | For each entry in `state_summary["npcs"]`, the `belief_state` key is absent (or `{}`). |
| AC4 — `known_facts` tail-K | Snapshot fixture with 1 PC carrying 25 `known_facts` → in `state_summary["characters"][0]["known_facts"]` the length is ≤ 8 and the entries are the last 8 (by insertion order). |
| AC5 — `scenario_state.discovered_clues` cap | Snapshot fixture with `scenario_state.discovered_clues` of 30 → dump has ≤ 12. |
| AC6 — regression guards (`journal`, `footnotes`, `location_descriptions`) | Dump does not contain any of these top-level keys. Test names the field explicitly so a future regression is caught at the field name. |
| AC7 — wiring | Driving `_build_turn_context` (the production seam) produces the projection — not a unit-only test on a private helper. |
| AC8 — gaslighting anchors preserved | `characters`, `quest_log`, `current_region`, `npc_pool`, `character_locations` survive all projections. |
| AC9 — OTEL span carries projection counts | The `prompt.game_state.bytes` span (already fires per 57-5) gains attributes recording how many entries were projected away: `npcs_dropped`, `room_states_dropped`, `known_facts_truncated_total`, `clues_truncated`. **Sebastien's lie-detector requirement** — the GM panel must see WHAT got dropped, not just total bytes. |
| AC10 — byte reduction holds | On a populated late-session fixture (5 rooms, 10 NPCs, 25 facts each on 4 PCs, 30 clues), the dump is at least 35% smaller than the post-Phase-B baseline (i.e., the extra projections beyond Phase B contribute ≥35% on top of Phase B's existing ≥50%). |

## Assumptions

- `Npc.last_seen_location` is a reliable signal of in-scene-ness. (It
  is populated per `Npc` docstring `last_seen_location` field comment
  at `session.py:152`; defaults to `None` for un-touched NPCs.)
- `snapshot.party_location(perspective=name)` is the canonical "where
  is this PC" accessor post-Wave 2B.
- `npc_pool` already contains identity entries for all materialized
  NPCs — confirmed at `tests/server/test_57_5_snapshot_slimming.py`
  pattern where the fixture seeds both `npcs` and (implicit
  pool-seeded by `world_materialization`).

## Out of Scope

- The RAG retrieval implementations themselves (those are 61-1 territory
  — landed at commit 06ad79c, 2026-05-21). This story relies on
  RAG being live so dropped entries are retrievable, but does NOT
  modify `query_lore` / `query_npc` / `query_known_facts`.
- The hard cap (61-3), fingerprint alarm (61-4), and architecture-gate
  test (61-5). Those are separate stories in the epic.
- Re-zoning the Valley block to cached — explicitly punted in ADR-110.
- `journal`, `footnotes`, `location_descriptions` retrieval — these
  are not snapshot fields, so they're inherently out of snapshot-slim
  scope. Their existing pipelines (ADR-100 journal, ADR-109 location)
  remain as-is.
