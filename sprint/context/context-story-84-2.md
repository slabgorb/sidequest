# Story 84-2 Context

## Title
WI-5 Alias resolution + accretion-fed aliases — mention resolves through epithets, promoted entities accrete via 75-1 path

## Metadata
- **Story ID:** 84-2
- **Type:** story
- **Points:** 3
- **Priority:** p2
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** 84 — ADR-118 Amendment — Unified Pertinence Scorer & Tiered Forgetting
- **Stack parent:** 84-1 (unified pertinence scorer, merged); sibling 84-4 (OTEL decomposition, merged)

## Problem
84-1's `mention` signal — the DOMINANT term in the unified pertinence score — is **name-match
only**. `retrieval_orchestration.py:300-303` carries the explicit WI-5 TODO:
`mention = 1.0 if player_referenced_npcs else 0.0`, where `player_referenced_npcs` comes from
the word-bounded `player_referenced_npcs_from_action` (matches the canonical NAME only). So
"the old man" / "the Baron" / "the seat of the fire king" (ADR-048's own example) never raise
`mention`, and the dominant signal silently degrades to the keyword/cosine tail for every
off-name reference — exactly the failure ADR-118 §A4 names ("Without this, the dominant signal
degrades to keyword matching").

ADR-118 §A4 requires two things: (1) `mention` resolves through each entity's **aliases/
epithets**, not raw player tokens; (2) world-authored entities carry aliases, and **promoted/
yes-and entities accrete epithets** via the 75-1 accretion path so matching "gets smarter the
longer the campaign runs, with no new pipeline."

## Investigation findings (codebase, confirmed this RED phase)

### Alias storage: a Pydantic field on `Npc`, NO Alembic migration
- `Npc` (`sidequest/game/session.py:126`) is a Pydantic `BaseModel` with `model_config =
  {"extra": "forbid"}` and **no `aliases` field today**. It already holds `list[str]` fields via
  `Field(default_factory=list)` (`distinguishing_features`, `abilities`).
- **Persistence is JSON, not columnar.** `GameSnapshot` (which contains `npcs: list[Npc]`) is
  saved as one JSON blob — `snapshot.model_dump_json()` → `game_state.snapshot_json`
  (`sidequest/game/pg/snapshot.py:83-92`) — and loaded via `GameSnapshot.model_validate(...)`.
  Only two Alembic migrations exist (`0001_initial_unified_schema`, `0002_asset_ledger`); NPCs
  are NOT stored in dedicated columns.
- **DECISION: add `aliases: list[str] = Field(default_factory=list)` to `Npc`. NO migration.**
  Rationale: the field rides the existing JSON blob; `default_factory=list` means pre-84-2 saves
  (no `aliases` key) load with an empty list (Pydantic supplies the default; the loader runs
  `migrate_legacy_snapshot` with `extra: ignore` tolerance). Adding a Postgres column would be
  pure over-engineering — there is no column to add to. (`NpcPoolMember` carries identity-only
  scaffolding; aliases live on the promoted stateful `Npc` per the session brief.)

### Promotion handler (the accretion hook)
- `_promote_pool_member_to_npc(member)` — `sidequest/server/narration_apply.py:1075` — builds the
  stateful `Npc` from a pool member (the invented→canonical factory).
- Call site ~`narration_apply.py:1240-1269`: matches the actor name in `snapshot.npc_pool`,
  promotes, `snapshot.npcs.append(promoted)`, and fires a `state_transition` /
  `op="promoted_from_pool"` watcher event. **This is where alias accretion hooks in** — on
  promotion, extract epithets from the turn's narration and append to `promoted.aliases`,
  emitting a 75-1-shaped accretion span/event.
- The 75-1 pattern to mirror: `sidequest/game/lore_accretion.py:70 accrete_facts_to_lore`
  (idempotent mint → dedup → result struct → OTEL) + `server/dispatch/lore_accretion.py:33
  accrete_for_turn` (the per-turn wrapper that emits the watcher event).

### Mention seam + dispatch path
- `retrieval_orchestration.py:300-303` builds `turn_signals.mention` (name-match only).
- The dispatch (`server/dispatch/universal_retrieval.py:70`) computes `player_referenced_npcs`
  via `player_referenced_npcs_from_action(snapshot, action)` (`agents/npc_context.py:62`) —
  word-bounded, case-insensitive, NAME only.
- `project_npc_card` (`entity_card.py:211`) projects content (name/role/pronouns/attitude);
  `EntityCard.new` accepts `metadata=` (the live 75-4 dict). Aliases → `metadata["aliases"]`.

## Technical Approach
1. **`Npc.aliases: list[str] = Field(default_factory=list)`** (session.py). No migration.
2. **Alias-aware mention resolver** (new pure helper, e.g. `sidequest/game/alias_resolution.py`
   `resolve_mention(action_text, *, names, aliases_by_name) -> set[str]` or a strength scorer):
   word-bounded match of the action against each entity's NAME ∪ ALIASES. Returns the matched
   entity identities (and/or a 0..1 strength). Multi-word epithets ("the old man", "the seat of
   the fire king") match as phrases, not just single tokens. Reuses the `\b`-bounded discipline
   of `player_referenced_npcs_from_action` so "Art" still isn't matched inside "start".
3. **Wire the resolver** into the mention computation. The cleanest seam: extend
   `player_referenced_npcs_from_action` (or add a sibling) to also match aliases — it already
   iterates `snapshot.npcs` (which will carry `.aliases`) and `snapshot.npc_pool`, and its
   result already flows to `retrieval_orchestration.py` mention. An alias hit must raise `mention`
   exactly as a name hit does.
4. **Card projection carries aliases** — `project_npc_card` populates `metadata["aliases"]` from
   the stateful `Npc.aliases` (deterministic: same aliases → same metadata, for 75-6 reproject).
5. **Accretion hook on promotion** — at `_promote_pool_member_to_npc` / the promotion call site,
   extract epithets from the turn's narration and append to `promoted.aliases` (idempotent: no
   duplicate aliases; case-folded dedup). Emit a 75-1-shaped OTEL/watcher event
   (`entity.alias_accreted` or a `state_transition` op) so the GM panel sees the accretion.
6. **Persistence** rides the JSON blob automatically; the test pins round-trip.

## Scope
- **In scope:** `Npc.aliases` field; the alias-aware mention resolver + its wiring into the
  mention signal; `project_npc_card` alias metadata; the accretion-on-promotion hook + its OTEL
  event; the persistence round-trip.
- **Out of scope:** world-authored aliases in YAML (the §A4 "world-authored entities carry
  aliases in YAML" leg — a genre-pack/content change; WI-5 reads `Npc.aliases` whatever its
  source, but adding the YAML authoring surface is a separate content story); faction/location
  alias accretion (NPC-first per the playgroup value cut — factions/locations can follow); the
  relationship-card projector (WI-4/84-3); tiered forgetting (WI-3/84-6); any scorer/weight
  change (84-1 is frozen — WI-5 only feeds a stronger `mention` *value* in).
- **No migration.** Aliases live in the existing snapshot JSON blob.

## Acceptance Criteria

> Each AC has failing test coverage written in the RED phase (see Test Coverage).

- **AC-1 — `mention` resolves through an alias/epithet (the headline).** An NPC with alias
  "old man" is referenced by a player action "I greet the old man" → the resolver returns that
  NPC and the `mention` signal for its card is RAISED (≥ the strong threshold), exactly as a
  canonical-name reference would. A name reference still works (no regression). A non-matching
  action ("I look at the wall") raises `mention` for nobody. *Tests:*
  `test_alias_reference_resolves_to_npc`, `test_canonical_name_still_resolves`,
  `test_unrelated_action_matches_nobody`, `test_multiword_epithet_matches_as_phrase`,
  `test_word_boundary_respected_for_aliases` (alias "art" not matched inside "start").

- **AC-2 — `Npc.aliases` field exists and projects into the card.** `Npc` carries
  `aliases: list[str]` (default empty); `project_npc_card` includes those aliases in
  `EntityCard.metadata["aliases"]` deterministically (same aliases → same metadata). *Tests:*
  `test_npc_has_aliases_field_defaulting_empty`,
  `test_project_npc_card_carries_aliases_in_metadata`,
  `test_projection_is_deterministic_for_same_aliases`.

- **AC-3 — Accretion: a promoted NPC accrues epithets into its aliases.** When a pool member is
  promoted to a stateful `Npc` and the turn's narration carries an epithet for it, that epithet
  is appended to `promoted.aliases` via the 75-1-shaped path. Accretion is idempotent
  (case-folded dedup — the same epithet on a later turn does not duplicate) and never appends a
  blank. *Tests:* `test_promotion_accretes_epithet_into_aliases`,
  `test_accretion_is_idempotent_no_duplicate_aliases`, `test_accretion_skips_blank_epithet`.

- **AC-4 — Persistence: aliases survive save/load with NO migration.** An `Npc` with accreted
  aliases round-trips through `model_dump_json()` → `model_validate()` (the snapshot blob path)
  with aliases intact; a legacy snapshot dict WITHOUT an `aliases` key loads to an empty-list
  default (No Silent Fallbacks — old saves don't crash, they default honestly). *Tests:*
  `test_aliases_survive_snapshot_json_roundtrip`,
  `test_legacy_snapshot_without_aliases_defaults_empty`.

- **AC-5 — OTEL: alias accretion is observable (GM-panel lie-detector).** The accretion path
  emits a span/watcher event (e.g. `entity.alias_accreted` or a `state_transition` carrying the
  npc name + the accreted alias) so the GM panel can verify aliases are engine-written, not
  narrator-improvised. The event fires on a real accretion and does NOT fire when nothing
  accreted. *Tests:* `test_alias_accretion_emits_otel_event`,
  `test_no_accretion_event_when_nothing_accreted`.

- **AC-6 — Drama-gate interaction: an alias-matched card still surfaces when the embed is
  skipped.** When the player references an NPC by ALIAS and the drama-gate (84-1
  `structured_signals_sufficient`) skips the cosine embed on the strength of the alias-raised
  `mention`, the alias-referenced NPC must still reach the prompt (it rides the floor / is not
  budgeted out). The alias must NOT silently require an embed to surface. *Tests:*
  `test_alias_match_skips_embed_and_npc_still_surfaces`.

- **AC-7 — WIRING.** Alias-resolved mention reaches the LIVE retrieval/handler path: driving a
  real player action that references a seeded-alias NPC through `_retrieve_entities_for_turn`
  (or `retrieve_for_turn`) classifies that NPC as referenced and the alias-raised mention is
  observable on the live path (the floor renders the referenced NPC / the `retrieval.universal`
  span reflects the resolution). Behavior + span only — no source grep. *Test:*
  `test_live_turn_resolves_alias_to_referenced_npc`.

- **AC-8 — Quality gate.** All ACs have failing coverage before GREEN; tree clean; correct
  branch (`feat/84-2-alias-resolution`); `just server-check` green; no Alembic migration added
  (the field rides the JSON blob); the alias accretion emits OTEL (CLAUDE.md OTEL principle).

## Test Coverage (RED — failing tests in place)
- `sidequest-server/tests/game/test_alias_resolution.py` — pure resolver (AC-1, AC-5 partial):
  alias→NPC, name still resolves, no-match, multi-word epithet, word-boundary, accretion
  idempotency/blank-skip (pure). Synthetic fixtures.
- `sidequest-server/tests/game/test_npc_aliases_field.py` — `Npc.aliases` field + projection +
  persistence (AC-2, AC-4): field default, `project_npc_card` metadata, determinism, JSON
  round-trip, legacy-default.
- `sidequest-server/tests/server/test_alias_accretion.py` — promotion accretion + OTEL (AC-3,
  AC-5): promotion accretes epithet, idempotent, blank-skip, emits event, no-event-when-empty.
  Run span-count assertions `-n0`.
- `sidequest-server/tests/game/test_alias_mention_retrieval.py` — drama-gate interaction +
  WIRING (AC-6, AC-7): alias match skips embed yet NPC surfaces (orchestration), and the live
  delegate resolves an alias to the referenced NPC. Run `-n0`.

## Notes for Dev
- **No Alembic migration.** Add `aliases: list[str] = Field(default_factory=list)` to `Npc`; it
  rides `snapshot_json`. Do NOT write a `CREATE TABLE`/`ALTER` — there is no column. (If you
  reach for `alembic revision`, stop — investigation confirmed JSON-blob storage.)
- **Reuse, don't reinvent the matcher.** `player_referenced_npcs_from_action`
  (`agents/npc_context.py:62`) is the word-bounded name matcher that already feeds mention;
  extend it (or add an alias-aware sibling) rather than a parallel tokenizer. Keep the `\b`
  discipline so "art" isn't matched inside "start".
- **Accretion hook:** `narration_apply.py` `_promote_pool_member_to_npc` (factory) + the
  promotion call site (~1246-1269, where the `promoted_from_pool` watcher event already fires).
  Mirror `lore_accretion.accrete_facts_to_lore`'s idempotent shape; emit the OTEL event there.
- **Mention seam:** `retrieval_orchestration.py:300-303`. An alias hit must raise `mention`
  identically to a name hit so the drama-gate and ranking treat it the same (AC-6).
- **Card metadata:** `project_npc_card` → `EntityCard.new(..., metadata={"aliases": ...})`.
  Deterministic for 75-6 reproject (sort the alias list before serialization).

---
_Acceptance criteria authored by TEA (Amos Burton) in the RED phase from ADR-118 §A4 + the 84-2
session brief + live codebase investigation (alias storage = JSON blob, no migration; promotion
hook at narration_apply.py:1075/1246). Supersedes the generated placeholder._
