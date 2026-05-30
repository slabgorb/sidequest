---
parent: context-epic-72.md
workflow: tdd
---

# Story 72-6: Cap npc_pool growth + prune stale scaffolds

Epic 72 (NPC Identity Hardening) · 3 pts · type: bug · workflow: tdd · repo: sidequest-server

## Business Context

`snapshot.npc_pool` (`list[NpcPoolMember]`, `sidequest/game/npc_pool.py`) is the world's
identity-scaffold store: name / role / pronouns / appearance hooks the narrator cites so a
"bartender at the Black Hart" can be re-named consistently turns later. It is **append-only and
unbounded**. Mint sites add members but nothing ever caps the list:

- `narration_apply._apply_npc_mentions` → `snapshot.npc_pool.append(new_member)`
  (`sidequest/server/narration_apply.py:1293,1301`) — novel-name branch.
- `session_helpers._auto_mint_prose_only_npcs` → `snapshot.npc_pool.append(NpcPoolMember(...,
  observation_pending=True))` (`sidequest/server/session_helpers.py:1799-1805`) — prose-only
  role/honorific mentions.
- `world_materialization.py:457` — world-authored seeding.

Two failure modes accumulate over a long session (the trigger was perseus_cloud session 894,
2026-05-29, a 140+-turn-class game):

1. **Unbounded growth.** Every glimpsed-but-unengaged face the narrator names pins a permanent
   pool entry. Over a long session the pool bloats the snapshot, every per-turn name-match scan,
   and the prompt's NPC roster — pure overhead for people the table will never interact with.
2. **Stale `observation_pending` scaffolds.** The ratification gate
   (`_apply_npc_observation_gate`, `session_helpers.py:1912`) is *supposed* to clear pending
   members the next turn — promote (re-cited) or purge (dropped). But a member only gets purged
   if the gate runs against that member on a turn where it's evaluated; entries the narrator
   drops *and* never re-mentions, or that the gate skips, persist as phantom pending scaffolds
   that were glimpsed but never engaged.

**Who this serves.** This is a Keith/dev-side hardening bug, not a player-facing feature. The
payoff is downstream: a bounded, prune-clean pool keeps the NPC roster the narrator and
`run_npc_agency` (`agents/subsystems/npc_agency.py`) read from honest, and the eviction/prune
OTEL spans let the GM panel (Keith's lie-detector) confirm the cap fired rather than the engine
silently bloating. This sits squarely under "No Silent Fallbacks": NPC-identity drops must be
audited, never silent — exactly the doctrine `npc_observation_gate_purged_span` already encodes.

**Diamonds-and-Coal constraint (ADR-014).** Eviction must never drop a "diamond." A pool member
backing a promoted/stateful `Npc` (the `Npc.pool_origin = member.name` back-pointer,
`session.py:151`), or one the development pipeline has escalated past `"spawn"`
(`Npc.resolution_tier`, `session.py:177`; `non_transactional_interactions`, `:178`), is an NPC
the table has shown genuine interest in. Evicting it would erase identity the playgroup earned.
Cap pressure must fall on *coal* — unreferenced, never-promoted scaffolds — only.

## Technical Guardrails

- **No new module.** Add cap + prune in `sidequest/game/npc_pool.py` (or a thin pure helper
  beside it) and call it from the existing mint/gate seams. Do not reinvent a registry.
- **Mirror the existing cap precedent.** `_DISCOVERED_CLUES_CAP = 12` in
  `session_helpers.py:232` with truncation at `:395-397` is the in-repo pattern for a bounded
  snapshot collection. Follow its shape: a module-level constant cap + a deterministic
  truncation pass + a count surfaced for telemetry. Make the cap a named constant (configurable
  by editing the constant — no env plumbing required unless the epic asks).
- **Eviction ordering = last-seen / LRU.** `NpcPoolMember` has **no timestamp field today**
  (`name`, `role`, `pronouns`, `appearance`, `archetype_id`, `drawn_from`,
  `observation_pending`). To order by recency you must either (a) add a `last_seen_turn`-style
  int to `NpcPoolMember` stamped at mint and on each re-mention in `_apply_npc_mentions`, or
  (b) derive recency from a parallel structure. Option (a) mirrors `Npc.last_seen_turn`
  (`session.py:160`) and is the straightforward choice — note `model_config = {"extra":
  "forbid"}`, so the field must be declared, with a default that keeps legacy snapshots loadable.
  Whichever you pick, **lower last-seen evicts first**; ties break deterministically (e.g. by
  insertion order / name) so tests are stable.
- **Stale-pending prune needs an age measure.** A member is "stale observation_pending" when it
  has been pending for more than a threshold number of turns without promotion. Since pending
  members are normally resolved next turn by the gate, measuring "past a threshold" requires the
  same per-member turn stamp as above (minted-turn or last-seen-turn). Prune runs as part of /
  adjacent to the gate pass so it shares the gate's turn number.
- **Diamond guard is mandatory.** Before evicting/pruning a member, exclude any member whose
  `name` (case-folded) appears as a `pool_origin` on a live `Npc` in `snapshot.npcs`, or whose
  backing `Npc` has `resolution_tier != "spawn"` / `non_transactional_interactions > 0`. The
  name join is case-folded — every other store-join in this code is (`_apply_npc_mentions`,
  `run_npc_agency`). World-authored members (`drawn_from="world_authored"`) should likewise be
  treated as protected, not transient coal.
- **OTEL is required (every leg).** Per epic spec and the server OTEL principle, add two spans in
  `sidequest/telemetry/spans/npc.py`: an **LRU-eviction** span and a **stale-pending-prune**
  span. Set `severity="warning"` on drops, mirroring `npc_observation_gate_purged_span`
  (`telemetry/spans/npc.py:478`) — that function is the canonical shape to copy (keyword-only
  args, `Span.open`, `_tracer` override hook, `**attrs`). Emit the evicted/pruned name + role +
  turn + the reason (cap-pressure vs stale-age) + survivor/evicted counts.
- **Server test rule — behavioral/span assertions only.** Per `sidequest-server/CLAUDE.md`
  "No Source-Text Wiring Tests": do **not** grep production source as a wiring check. Drive the
  cap/prune through a real snapshot fixture and assert on (1) resulting pool membership and
  (2) the emitted OTEL spans. The wiring test for this story is "build a snapshot whose pool
  exceeds the cap, run the mint/gate path, assert the eviction span fired and the diamond
  survived" — span-driven, refactor-stable.

## Scope Boundaries

**In scope:**
- A configurable cap on `snapshot.npc_pool` length with deterministic last-seen/LRU eviction.
- A stale-`observation_pending` prune (pending beyond a turn-count threshold, never promoted).
- The per-member recency/age field on `NpcPoolMember` that both of the above require.
- Diamond guard (never evict promoted/`pool_origin`-backed/tier-escalated/world-authored).
- Two OTEL spans (eviction, prune) in `telemetry/spans/npc.py`, wired into the mint/gate seams.

**Out of scope:**
- Promotion logic, `resolution_tier` escalation, `non_transactional_interactions` increment,
  disposition drift — that is the **development pipeline (72-1)**. 72-6 only *reads* these
  fields to identify diamonds; it does not write or escalate them.
- Disposition preservation / load-time `npcs ↔ npc_pool` reconcile — **72-2**.
- Authoritative identity-drift overwrite of pronoun/role on re-mention — **72-7**. 72-6 may add
  a recency stamp at the re-mention site but must not change drift/overwrite semantics.
- Stamping `last_seen_*` on structured encounter presence — **72-8**. (If 72-6 adds a pool
  recency field, it stamps it at prose-mention/mint; encounter-presence stamping is 72-8's leg.)
- MM `manual_origin` provenance (**72-3**), namegen routing (**72-4**), born-hostile default
  (**72-5**), OCEAN/belief seeding (**72-9**), gate-ordering assert (**72-10**).

## AC Context

Derived ACs (no explicit ACs existed on the story). Each is behaviorally testable against a
snapshot fixture + OTEL span capture.

1. **Pool growth is bounded by a configurable cap.** After mint paths run on a snapshot whose
   `npc_pool` would exceed the cap, `len(snapshot.npc_pool) <= CAP`. The cap is a named
   module-level constant (mirroring `_DISCOVERED_CLUES_CAP`).
   - *Edge — pool exactly at cap:* a pool at exactly `CAP` with no new mint triggers **no**
     eviction (boundary is inclusive; only growth *past* cap evicts).

2. **Eviction is last-seen / LRU ordered.** When the cap forces a drop, the member with the
   oldest last-seen/minted turn is evicted first; more-recently-seen members survive.
   - *Edge — tie in last_seen:* two members with identical last-seen turn break ties
     deterministically (documented order — e.g. insertion order or case-folded name), so the
     test asserts a single stable outcome rather than a nondeterministic one.

3. **Stale `observation_pending` scaffolds are pruned.** A member that has been
   `observation_pending=True` for more than the stale-age threshold without being promoted is
   removed from the pool, independent of cap pressure.
   - *Edge — re-engaged pending member:* an `observation_pending` member the player/narrator
     re-cites this turn is promoted by the gate (flag cleared, recency stamp refreshed) and is
     **not** pruned — re-engagement resets its age, so it survives.

4. **Promoted / important NPCs are NEVER evicted (Diamonds-and-Coal).** A pool member that backs
   a live `Npc` (`Npc.pool_origin == member.name`, case-folded), or whose `Npc` has
   `resolution_tier != "spawn"` or `non_transactional_interactions > 0`, or that is
   `drawn_from="world_authored"`, survives both the cap eviction and the stale prune even when
   it is the oldest / most-stale candidate. Cap pressure spills onto the next-oldest *coal*
   instead. If every member is a diamond, nothing is evicted (the pool may legitimately exceed
   the soft cap rather than drop a diamond).

5. **Every eviction and prune emits an OTEL span.** A cap eviction emits the eviction span and a
   stale prune emits the prune span, each at `severity="warning"` with the dropped member's
   name + role + turn + reason + counts — so the GM panel can confirm the cap/prune engaged and
   audit every NPC-identity drop. (This is also the wiring test: assert the span fired from the
   real seam, not from a unit-only call.)

## Assumptions

- **`NpcPoolMember` gains a per-member turn field.** Both LRU eviction and stale-age prune need
  a recency/age measure the type does not currently carry. Adding e.g. `last_seen_turn: int`
  (defaulted, declared so `extra="forbid"` accepts it) stamped at mint and on re-mention is
  assumed in-scope as the minimal enabler. If the implementer derives recency another way, ACs
  2 and 3 still hold; the field is the recommended path because it mirrors `Npc.last_seen_turn`.
- **Cap and stale-threshold are named constants**, configurable by editing the constant (the
  `_DISCOVERED_CLUES_CAP` precedent). No env-var plumbing is assumed unless the epic adds it.
  Sensible starting values are a design choice for the implementer; tests should parameterize on
  the constant, not a hard-coded literal.
- **Diamond detection reads `snapshot.npcs`.** The guard requires the cap/prune pass to see both
  stores (pool + `npcs`) so it can join on `pool_origin`/tier. The pass runs where both are
  available (the mint/gate seams in `narration_apply` / `session_helpers` already hold the full
  snapshot).
- **Prune shares the gate's turn number.** Stale-age is measured against the current turn, which
  the gate pass (`_apply_npc_observation_gate`) already receives — the prune runs in/adjacent to
  that pass.
- **No save migration burden.** Per the project's standing "no saves to migrate" stance, a new
  defaulted field on `NpcPoolMember` is sufficient for legacy snapshots; no Alembic/data
  migration is expected for this story.
