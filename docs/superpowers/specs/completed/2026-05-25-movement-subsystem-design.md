# Movement Subsystem — Technical Design Spec

**Date:** 2026-05-25 (rev. 2026-05-26 — per-PC split-party model, Keith overturned the single-token premise)
**Status:** Approved for TDD (Keith locked option (a); MP model = per-PC, no party token)
**Author:** Architect
**Relevant ADRs:** ADR-113 (Intent Router engagement spine), ADR-106 (runtime procedural Jaquaysed megadungeon / materializer), ADR-055 (room-graph / region navigation), ADR-036 (multiplayer sealed-round turn coordination), ADR-037 (shared-world / per-player state split), ADR-104 / ADR-105 (perception filtering — narration-asymmetry follow-up), ADR-011 (WorldStatePatch apply)

> **Revision note (2026-05-26):** Keith overturned the original §Q5 "single party token / deepest-intent-wins reconciliation." **Movement is PER-PC — the party can genuinely split.** If Rux says "deeper" and Slabgorb says "leave!", Rux ends up in region A and Slabgorb in region B *simultaneously*. Each PC's intent resolves and moves THAT PC only — no winner, no loser, no contested directive. The dungeon grows wherever ANY PC is (multiple concurrent frontiers). `map_emitted` and OTEL go per-PC. Asymmetric *narration* (addressing each split sub-group as its own scene) is **out of scope for this build** — deferred to ADR-104/105 perception filtering or an explicit follow-up. This build is the engine-truth mechanical core: per-PC positions advance correctly, per-region materialize fires, per-PC map/OTEL.

---

## Problem

In `caverns_and_claudes/beneath_sunden`, player descent/movement advances **NARRATION ONLY**. The region-graph stays pinned at the surface spawn `ropefoot` with `discovered=0/6`; `dungeon.materialize` / region-commit / edge-expansion **never fire**. The ADR-106 materializer and ADR-055 region-graph are inert at runtime.

**Confirmed root cause:** the only runtime writer of `snapshot.current_region` is the narrator's `apply_world_patch` tool (`sidequest/agents/tools/apply_world_patch.py`), flowing through `GameSnapshot._apply_world_patch_inner` (`sidequest/game/session.py` L1100-1123). It does not fire on descent. There is **no `movement` subsystem**. Movement is therefore pure prose Illusionism with zero graph backing — precisely the failure OTEL exists to catch.

The producer seam is already live: `notify_region_transition` (`sidequest/dungeon/frontier_hook.py` L109-156) dedup-appends into `discovered_regions`, notifies registered observers, and emits `frontier.region_transition`. The lookahead worker (`sidequest/dungeon/lookahead_worker.py`) registers an observer at session init that enqueues `materialize()`. **The producer fires only when `current_region` actually changes — and nothing changes it on descent.** We are wiring the missing *engine-truth writer*, not building new graph machinery.

---

## Decision

Build **option (a): a mechanical Movement subsystem** (Keith's locked decision, 2026-05-25 — do not relitigate).

> IntentRouter classifies movement → a new `run_movement_dispatch` traverses the **real** frontier-graph adjacencies to pick the next region → advances `current_region` → emits an OTEL span → triggers `notify_region_transition` → frontier observers → lookahead_worker `materialize()`. Deterministic, engine-truth, lie-detector-visible.

**Explicitly rejected:** the narrator-driven approach (prompting the narrator to call `apply_world_patch` on descent). It is fragile Illusionism — the LLM both decides movement happened *and* reports it, with no mechanical arbiter. **Do not add it back, not even as a "safety net."** (One-mechanism rule; `feedback_one_mechanism_per_problem`, `feedback_no_fallbacks_hard`.)

This subsystem is the **single** movement-resolution mechanism. The narrator's `apply_world_patch(current_region=...)` escape hatch remains for non-movement region writes (e.g. monster-manual injection, scripted teleports) but is **never** the answer to "a PC walked deeper."

---

## Design

### Q0 (NEW). Per-PC region data model — the hard premise change

**Finding (grounded in source, not hand-waved):**

- `GameSnapshot.current_region: str` (`session.py` L632) is a **single party-level field**. `notify_region_transition` (`frontier_hook.py` L109-156), the lookahead observer, the materializer, and `_maybe_emit_dungeon_map` (`websocket_session_handler.py` L1257-1310) **all key off this one value**. This is exactly what breaks under a split party.
- `discovered_regions: list[str]` (`session.py` L633) is likewise party-level (one fog-of-war set for the whole table).
- **Per-PC infra already exists and is load-bearing:** `GameSnapshot.character_locations: dict[str, str]` (`session.py` L761, Wave 2B / story 45-48) is the per-PC *scene/location string* source of truth. `party_location(perspective=name)` (L915-987) already returns the single-PC value and already handles split: with no perspective it returns the consensus string, or `None` + a `party_location_query` span with `party_split=True` when seated PCs disagree. `player_seats: dict[str, str]` (L804) enumerates the seated PCs (the ADR-037 seat map). `WorldStatePatch.location` (L366) is a *party-frame* intent ("everyone is now here") and fans out to every seated PC's `character_locations` (L1083-1089).
- **The gap:** `character_locations` carries the *narrative scene string*, not the *graph region id*. The frontier/materializer keys off `current_region` (the graph node), which has **no per-PC analogue**. So today the engine literally cannot represent "Rux in region A, Slabgorb in region B."

**Decision — add a per-PC region map mirroring the existing `character_locations` pattern:**

```python
# GameSnapshot, new field (sits beside character_locations at L761)
pc_regions: dict[str, str] = Field(default_factory=dict)   # player_name -> region_id
```

Justification: this is the *exact* shape (`dict[player_name, str]`) and ADR-037 per-player-state spirit the codebase already uses for `character_locations`. We do NOT invent a new `PerPlayerState` container (no infra for it exists; `character_locations` IS the precedent) and we do NOT overload `character_locations` (it holds a free-text scene string, not a graph node id — conflating them would corrupt the narrator-scene path). `player_seats` enumerates whose `pc_regions` entries are authoritative.

**Fate of `current_region` — retired as the per-PC truth, retained as a derived consensus/spawn anchor (NOT silently ambiguous):**

- `current_region` is **no longer written by movement.** It stops being "where the party is."
- It is **retained** as the **seed/spawn anchor** (the entrance the dungeon bootstraps at — `region_init` turn-1 still sets it) and as a **derived consensus accessor**, mirroring `party_location()`'s three-mode contract. Add `region_for(perspective=name)`:
  - `perspective` supplied → `pc_regions.get(name)` (fail-loud if the seated PC has no entry — a binding bug, never a quiet `current_region` fallback).
  - `perspective` omitted, all seated PCs agree → that consensus region id.
  - `perspective` omitted, seated PCs disagree → `None` (callers render "(party split)"), emitting the same `party_location_query`-style span with `party_split=True`. **No silent fallback to the stale singular `current_region`.**
- **Migration (save-compat):** on load, if `pc_regions` is empty but `current_region` is set (every pre-this-story save), seed `pc_regions[name] = current_region` for each seated PC (the `_migrate_s3_party_location` precedent at `session.py` L582, which promoted legacy `location` into `character_locations`). New field is `Field(default_factory=dict)` so old saves deserialize cleanly under `extra: ignore`.

Everything downstream that read `snapshot.current_region` for "where is this PC" must move to `region_for(perspective=pc)` / `pc_regions[pc]` — enumerated in §Q2, §Q-map, and the TDD plan.

---

### 0. Subsystem registration & contract

Register `movement` in `_register_defaults()` (`sidequest/agents/subsystems/__init__.py` L134-153), following the existing unregister-then-register idempotent pattern:

```python
from sidequest.agents.subsystems.movement import run_movement_dispatch
...
("movement", run_movement_dispatch),
```

Handler signature (keyword-only, signature-filtered by `_filter_context_for_callable`, L57-88):

```python
async def run_movement_dispatch(
    dispatch: SubsystemDispatch,
    *,
    snapshot: GameSnapshot,
    player_name: str,            # THIS PC — the dispatch runs per-submission, so we know whose move this is
    dungeon_store: "DungeonStore | None" = None,
    palette: "ThemePalette | None" = None,
) -> SubsystemOutput: ...
```

Per the bank contract (`SubsystemOutput`, L91-108) the handler **must not re-raise** for recoverable failures — it returns `directives=[]` + `data["error"]=<code>` and the bank records an error span (`run_dispatch_bank`, L184-281). It DOES raise only for genuine programmer bugs (caught & span-recorded by the bank regardless).

**Context threading (new wiring).** The dispatch bank context is built at `sidequest/server/intent_router_pass.py` L158-167. Today it passes `snapshot/pack/player_name/npcs_present/additional_player_names`. The movement handler needs the live region graph, which lives on `SessionData.dungeon_store` (a `DungeonStore`, wired by the Beneath Sünden path — `websocket_session_handler.py` L641) and the genre `ThemePalette`. Add `dungeon_store` and `palette` to the context dict built in `intent_router_pass.py`. Because the bank filters context by signature (L57-88), the six existing subsystems that don't declare these kwargs are unaffected. The handler that needs them declares them; everyone else ignores them. **Do not** rely on the redundant double-dispatch at `orchestrator.py:2539` ({npc_pool}-only context) — it will not carry `dungeon_store` and must not (see §2).

---

### Q1. Router params contract (coarse intent, never a guessed region_id)

The router/narrator does **not** know graph topology and MUST NOT emit a region_id. Add a new `movement` subsystem key to the IntentRouter `_SYSTEM_PROMPT` (`sidequest/agents/intent_router.py` L102-142), in the "Available subsystem keys and their required params" block:

```
- movement: the party physically relocates between dungeon regions
  (descend, ascend, go through an exit, retreat). params={
    "direction": "<one of: deeper | back | toward_exit>",
    "exit_descriptor": "<optional free-text label of the exit the
                        player named, e.g. 'the iron stair', 'the
                        crack in the east wall'>"
  }.
  Emit movement ONLY for genuine region relocation, not look-around /
  search / examine. NEVER emit a region id — you do not know the graph.
  Describe WHICH exit by exit_descriptor only; the engine resolves it.
```

`params` shape (the typed input the handler reads):

| field | type | meaning |
|---|---|---|
| `direction` | enum `deeper` \| `back` \| `toward_exit` | coarse vector |
| `exit_descriptor` | `str` (optional) | the player's own words for the exit, if any |

**Deterministic resolution algorithm** inside `run_movement_dispatch`:

1. Load the live graph: `graph = dungeon_store.load_map(entrance_id=_ENTRANCE_ID)` (same call the worker uses, `lookahead_worker.py` L345). If `dungeon_store is None` → this world has no procedural dungeon; return `data["error"]="no_dungeon_store"` (recoverable — movement is then a non-mechanical world; see §4 note). Fail loud via span, do not invent a region.
2. Resolve **THIS PC's** current region: `from_region = snapshot.region_for(perspective=player_name)` (per-PC, §Q0 — NOT the singular `current_region`). If the seated PC has no `pc_regions` entry → fail loud (binding bug; never default to `current_region`). Project it: `proj = project_region(graph, from_region, palette)` (`region_projection.py` L111-174). `proj.exits` is the **deterministically sorted** (visible-before-hidden, then by `to_region_id`, L162) list of `RegionExit(to_region_id, kind, hidden, shortcut)`. This is the candidate set — **only real adjacencies, never invented**.
3. **Filter `hidden` exits out** of the candidate set unless `snapshot.discovered_routes` already records that edge as found (hidden exits are not yet known to the party; offering one is Illusionism in reverse). Secret edges (`kind="secret"`) are always `hidden=True` by construction.
4. Resolve the coarse intent against the filtered candidates:
   - **`exit_descriptor` present** → token-overlap match against each candidate's surface form. The surface form for matching is the destination region's `node.theme` display + region id tokens + `kind` keyword (e.g. `stairs`→{"stair","stairs","up","down","descend"}, `shaft`/`chute`→{"shaft","chute","drop","down"}, `corridor`→{"corridor","hall","passage","tunnel"}, `secret`→never auto-matched). Score = count of shared lowercased alpha tokens. Pick the single highest score.
   - **`direction="deeper"`** (no/failed descriptor match) → among candidates, prefer edges whose target `node.depth_score` is **strictly greater** than the current node's `depth_score`; among those, the **maximum** depth delta. `kind` tie-break order: `shaft` > `chute` > `stairs` > `corridor` > `secret`.
   - **`direction="back"`** → prefer the edge to a region already in `snapshot.discovered_regions` with the **smallest** `depth_score` (toward the surface). Tie-break: the region most-recently-prior in `discovered_regions` order (the way they came).
   - **`direction="toward_exit"`** → BFS toward `graph.entrance_id` using `RegionGraph.bfs_dist` (model.py L125+); step to the neighbor on the shortest path. Tie-break by `to_region_id` ascending.
5. **Tie-breaks at every level are total and deterministic** (final fallback: ascending `to_region_id`). A career GM must never see the dungeon "shift."
6. **Zero candidates after filtering, OR an `exit_descriptor` whose top-2 token scores are tied (genuine ambiguity)** → FAIL LOUD (§4). Do not pick one silently.

The resolved value is a **specific, real adjacent `region_id`** present in `graph.neighbors(from_region)` (this PC's region). Assert this before advancing (a resolution that escapes the neighbor set is a programmer bug → raise).

---

### Q2. Where a PC's region is advanced — ONE mechanism, per-PC

**Decision: option (b), per-PC — emit a `WorldStatePatch` carrying a per-PC region delta and apply it through the existing `snapshot.apply_world_patch(...)` path, which fires `notify_region_transition` for THAT pc.** The handler does **NOT** mutate `pc_regions` directly and does **NOT** call `notify_region_transition` itself. One applier, one transition, per PC.

**New patch field.** `WorldStatePatch` (`session.py` L357-382, `extra: forbid`) gets a per-PC region delta beside the existing party-frame fields. Because `run_movement_dispatch` runs per-submission and knows `player_name`, it writes exactly one PC:

```python
# WorldStatePatch, new field
pc_region: dict[str, str] | None = None   # {player_name: region_id} — per-PC region move
```

(A `dict` rather than a scalar so a single patch shape can also express batch seeds at migration/init; movement always writes a one-entry dict for its own `player_name`.)

**`_apply_world_patch_inner` change — move the existing transition logic from the singular `current_region` block (L1100-1123) onto the per-PC field.** The current block keys off `patch.current_region` vs `_prev = self.current_region`. The new block iterates `patch.pc_region` entries:

```python
if patch.pc_region is not None:
    for pc_name, to_region in patch.pc_region.items():
        prev = self.pc_regions.get(pc_name)
        self.pc_regions[pc_name] = to_region
        if to_region and to_region != prev:
            from sidequest.dungeon.frontier_hook import notify_region_transition
            notify_region_transition(
                self, pc_name=pc_name, from_region=prev or None, to_region=to_region,
            )
```

The legacy `patch.current_region` block is **retained only for the seed/spawn-anchor + scripted-teleport path** (it now writes `self.current_region` AND, for back-compat, fans the anchor into `pc_regions` for any seated PC lacking an entry — the §Q0 migration shape). Movement never sets `patch.current_region`; it sets `patch.pc_region`. One mechanism per concern: per-PC moves go through `pc_region`, the world-anchor goes through `current_region`.

**`notify_region_transition` new signature (frontier_hook.py L109-156).** It currently takes `(snapshot, *, from_region, to_region)` and is party-level. Make it carry **which PC moved**, and scope the dedup + observer to that PC:

```python
def notify_region_transition(snapshot, *, pc_name: str, from_region: str | None, to_region: str) -> None: ...
```

- **Promote-to-active** now dedup-appends `to_region` into `snapshot.discovered_regions` (still the shared fog-of-war set — a region ANY PC has entered is "discovered" for the whole table's map; that is correct and matches the existing dungeon-map fog model) **and** is the recorded landing for `pc_name`.
- **Frontier-approach dispatch** notifies observers with `pc_name=pc_name` so the lookahead worker materializes the frontier **around `to_region`** (this PC's new region) — see §Q3. The worker's observer signature gains `pc_name` (it already receives `snapshot, from_region, to_region` via kwargs; add `pc_name`).
- The `frontier.region_transition` span gains a `pc_name` attribute.

**Exact call site inside `run_movement_dispatch`:**

```python
from sidequest.game.session import WorldStatePatch
snapshot.apply_world_patch(WorldStatePatch(pc_region={player_name: resolved_region_id}))
```

In-place mutation of the canonical snapshot (the bank convention — confrontation mutates in-place), visible to the rest of the turn and persisted.

**Fires exactly once PER PC — proof of the hazards:**
- **No-op guard:** the per-PC block fires the transition only when `to_region != prev` for that `pc_name`. A PC who "moves" to their own region (never — §1 fails loud first) is a no-op.
- **One applier:** the move goes *through* the single patch path; no parallel in-place write competes. One write → one transition → one materialize, scoped to `pc_name`.
- **Two PCs in one round → two patches → two transitions → two materializes,** each scoped to its own `pc_name`. This is the desired split-party behavior, not a hazard (see §"Per-PC movement & split party").
- **Double-dispatch hazard (path 2):** the redundant `orchestrator.py:2539` invocation runs with `{npc_pool}`-only context — missing `dungeon_store`/`palette`/`player_name`, so `run_movement_dispatch` hits the `no_dungeon_store` branch and applies **no patch**. It cannot re-fire any transition. Path 1 (`intent_router_pass.py` L158, real per-submission context) is authoritative. **Per Keith: leave path 2 as the harmless no-op** — consolidation is a separate ADR-105/113 story, not this build.

---

### Q3. Unmaterialized-frontier ordering — move-then-materialize

When THIS PC's resolved target is a frontier edge whose region is **not yet materialized**:

**Ordering: SYNC-MATERIALIZE THEN MOVE** (Keith locked, resolves former O1 — KEEP this branch, do NOT make it a `raise`). The resolved target MUST already be a real graph node before the PC moves into it. Two cases:

- **Target is an existing node** (already in `graph.nodes`, including look-ahead-materialized neighbors): apply the patch immediately. `notify_region_transition(pc_name=...)` → observer → worker enqueues a *next-ring* `materialize()` for the frontier around this PC's new region (move-then-materialize for the ring beyond). The PC lands in a real, graph-backed region this turn; next turn's per-PC `dungeon.map_emitted` reflects it.
- **Target is a frontier edge with no committed node yet** (the candidate came from `proj.exits` but `graph.nodes` lacks the destination): the handler MUST NOT move the PC into an uncommitted region (that would land them in a phantom — `project_region` raises on a non-node region, §1 fail-loud). Instead: **synchronously materialize the single needed edge first, then move.** Reuse the worker's own path — call the worker handle's materialize entry for the specific edge (`sd.lookahead_handle`), await it, confirm the node now exists in a fresh `load_map`, then apply the per-PC patch. If the synchronous materialize fails → FAIL LOUD (§4), do not move.

> **This branch is load-bearing under split-party (Keith's rationale):** with PCs in multiple regions, each occupied region is its own live frontier and they **compete for the single lookahead worker**. The worker falling behind is therefore *more* likely than in the single-token model — so the sync-materialize path is real, exercised code, NOT dead-code-to-raise-on. Breadth-≥1 is best-effort under contention, never a hard guarantee.

This guarantees the **post-move invariant**: every PC's `pc_regions[pc]` is always a real node, so `project_region(graph, region_for(perspective=pc), ...)` succeeds next turn and that PC's `dungeon.map_emitted` is graph-true.

---

### Q4. No-edge / ambiguous intent — FAIL LOUD, no fallback

When resolution finds **no real adjacency** for the coarse intent, or the `exit_descriptor` is **genuinely ambiguous** (top-2 token scores tied):

- Emit an **ERROR-level** OTEL span `movement.unresolved` (see OTEL contract) with `reason ∈ {no_candidate_edges, ambiguous_descriptor, no_dungeon_store}`, the `intent` params, and the candidate exit ids.
- Return `SubsystemOutput(directives=[NarratorDirective(...)], data={"error": reason})`. The directive instructs the narrator to **surface the failure honestly** to THIS PC — e.g. `must_narrate`: "Rux finds no such way from here; the exits are X, Y, Z." This is the loud, player-visible surface: the PC is told the truth (there is no such exit) rather than being silently teleported or silently kept in place with invented prose.
- **This PC does NOT move** — their `pc_regions[pc]` is unchanged because no patch is applied. No `frontier.region_transition` fires for them (correct: they didn't move). **Other PCs who sealed valid moves this round still move** — one PC's no-edge failure never blocks another PC. The player can re-declare next round.
- **NO silent fallback:** we never invent a region, never "default to staying put" *without the ERROR span + narrator surface*, never pick an arbitrary exit to keep things flowing. Staying put is only acceptable *because it is loudly signaled*. (`feedback_no_fallbacks_hard`: silent = worst; fail loud = ERROR span + surfaced + recoverable retry.)

The `no_dungeon_store` case is a config/world mismatch (movement classified in a non-procedural world). It is ERROR-spanned and surfaced the same way; it is recoverable (next turn the player tries non-movement).

---

### Q5. Per-PC movement & split party — NO party token, NO reconciliation

**Keith's locked decision (overturns the original single-token premise):** *"everyone takes care of themselves. If Rux says deeper and Slabgorb says leave!, they split up."* There is **NO single party token, NO winner/loser, NO contested directive, NO reconciliation.** Each PC's movement intent resolves independently and moves **THAT PC only.** Rux ends in region A and Slabgorb in region B **simultaneously.** This aligns with ADR-037 (shared-world / per-player state split).

Per ADR-036 sealed rounds: all seated PCs act every round; there is no single "acting player" (`feedback_sealed_rounds_no_acting_player`). Each seated PC's movement dispatch arrives on the live path **per-submission**, so `run_movement_dispatch` runs once per PC with that PC's `player_name`.

**Mechanics (entirely from the per-PC primitives above — there is nothing to "reconcile"):**

1. Each movement dispatch resolves against **that PC's own** `from_region = region_for(perspective=player_name)` (§Q1 step 2) — independently, no shared decision.
2. Each resolved move emits its own `WorldStatePatch(pc_region={player_name: target})` through the single apply path (§Q2).
3. That patch fires `notify_region_transition(pc_name=player_name, ...)` **exactly once for that PC** → the observer materializes the frontier **around that PC's new region** (§Q3).
4. **Two PCs sealing different intents in one round produce two independent patches → two transitions → two materializes → two distinct `pc_regions` entries.** The party is genuinely split: `pc_regions == {"Rux": "<deeper>", "Slabgorb": "<back>"}`. `region_for()` with no perspective now returns `None` (`party_split`), and per-PC `dungeon.map_emitted` shows each client its own PC's region (§Q-map).
5. **The dungeon grows wherever ANY PC is** — multiple concurrent frontiers, one per occupied region. No intent is dropped; no intent overrides another.

**No reconciliation, no freeze, no surfaced "loser":** the old §Q5 `contested` / `losing_intents` / deepest-wins machinery is **deleted**. There are no losers because there is no single token to contend for.

**Out of scope — asymmetric narration (deferred, per Keith).** The narrator addressing each split sub-group as its own scene (Rux gets a deeper-dark scene, Slabgorb gets a retreat scene) is **NOT in this build.** This build is the engine-truth mechanical core: per-PC positions advance correctly, per-region materialize fires, per-PC map/OTEL. The narrator in this build still produces one narration stream over the now-split positions. **Follow-up:** asymmetric per-sub-group narration is deferred to **ADR-104 / ADR-105 perception filtering** (the tool-layer + broadcast-firewall path that already scopes what each client sees) **or an explicit follow-up story.** Flag this as the known seam, not a silent gap.

---

### Q-map. Per-PC `dungeon.map_emitted`

Today `_maybe_emit_dungeon_map` (`websocket_session_handler.py` L1200-1310) reads the singular `snapshot.current_region` (L1257) and sets `is_current_room=(rid == current_region)` (L1284) and `DungeonMapPayload(current_location=current_region, region=current_region, ...)` (L1288-1292). It already runs **per-connection** and already stamps `player_id=getattr(sd, "player_id", "")` (L1293) — so the emit site is structurally per-PC; it just keys off the wrong (party-level) region.

**Change:** the emit reads **this connection's PC region**. The handler knows the connection's PC (the seat bound to `sd.player_id`); resolve `pc_region = snapshot.region_for(perspective=<this connection's pc>)`:

- `current_region` local var (L1257) → `pc_region` for the emitting connection.
- `is_current_room` (L1284) → `(rid == pc_region)` — each client's "you are here" is *their own* PC's region.
- `DungeonMapPayload.current_location` / `.region` (L1289-1290) → `pc_region`.
- `discovered` (L1258-1262) stays the **shared** fog-of-war set (`discovered_regions`) — the table's collective map; only the YOU-ARE-HERE marker is per-PC. (A region any PC entered is on everyone's map; that matches the existing fog model and avoids hiding the dungeon from a PC whose ally scouted ahead.)

Result: in a split party, Rux's client shows YOU-ARE-HERE on region A and Slabgorb's on region B, over the same discovered-region map. The `dungeon.map_emitted` span gains a `pc_name` + `pc_region` attribute so the GM panel sees each client's per-PC frame. If the emitting connection has no seated PC / no `pc_regions` entry → emit `dungeon.map_skipped` with `reason="no_pc_region"` (loud, never a silent fall-through to the stale singular `current_region`).

---

## OTEL Contract

The GM panel is the lie detector. Movement MUST be provably engaged vs. improvised.

All movement spans are **per-PC** — every span carries `pc_name` so the GM panel can see each PC's move independently (split-party legibility).

**Span 1 — `movement.resolved`** (INFO; the happy path, one per PC who moved):
| attribute | value |
|---|---|
| `pc_name` | the PC who moved (the dispatch's `player_name`) |
| `from_region` | this PC's pre-move region (`region_for(perspective=pc)`) |
| `to_region` | resolved adjacent region id |
| `intent.direction` | `deeper` \| `back` \| `toward_exit` |
| `intent.exit_descriptor` | raw descriptor or `""` |
| `resolved_via` | `descriptor_match` \| `depth_delta` \| `bfs_to_exit` |
| `candidate_exits` | list of candidate `to_region_id` |
| `edge_kind` | `corridor` \| `stairs` \| `shaft` \| `chute` \| `secret` |
| `target_pre_materialized` | bool (was the node already committed) |
| `materialize_triggered` | bool (did this move enqueue look-ahead around `to_region`) |
| `party_split_after` | bool (do seated PCs now disagree on region, i.e. `region_for()` is `None`) |

(No `contested` / `intent_count` / `losing_intents` — there is no reconciliation. Each PC's move is its own span.)

**Span 2 — `movement.unresolved`** (ERROR; fail-loud, §4, one per failing PC):
| attribute | value |
|---|---|
| `pc_name` | the PC whose move failed |
| `reason` | `no_candidate_edges` \| `ambiguous_descriptor` \| `no_dungeon_store` |
| `from_region` | this PC's region |
| `intent.direction`, `intent.exit_descriptor` | the failed intent |
| `available_exits` | candidate ids offered to the narrator surface |

**Reused downstream spans (must continue to fire on this path, now `pc_name`-stamped):** `frontier.region_transition` (`frontier_hook.py` L138 — gains `pc_name`) and the worker's `dungeon.materialize` (`lookahead_worker.py` L347). Two PCs moving = two `frontier.region_transition` + two `dungeon.materialize`, each tagged with its `pc_name`. The new span lives in `sidequest/telemetry/spans/` alongside `dungeon_materialize.py` — propose `sidequest/telemetry/spans/movement.py` exporting `movement_resolved_span(...)` and `movement_unresolved_span(...)`, matching the `frontier_region_transition_span` context-manager shape.

---

## MP Semantics (summary)

- **NO party token.** Movement is per-PC; the party can genuinely split (ADR-037).
- Each seated PC's movement intent resolves **independently** against that PC's own region and moves **only that PC** — no winner, no loser, no reconciliation, no contested directive.
- Two PCs sealing different intents in one round → **two independent patches, two `frontier.region_transition`, two `dungeon.materialize`, two distinct `pc_regions` entries.** The dungeon grows wherever ANY PC is.
- Each client's `dungeon.map_emitted` shows **its own PC's** YOU-ARE-HERE over the shared discovered-region fog map.
- All movement OTEL spans carry `pc_name`.
- **Asymmetric narration is out of scope** — deferred to ADR-104/105 perception filtering or an explicit follow-up.

---

## Failure Modes (fail-loud, no fallback)

| condition | behavior |
|---|---|
| No real adjacency for this PC's intent | ERROR span `movement.unresolved(no_candidate_edges)` (with `pc_name`), narrator surfaces "no such way" to THAT PC, this PC does not move, no patch; other PCs still move |
| Ambiguous `exit_descriptor` | ERROR span `movement.unresolved(ambiguous_descriptor)`, narrator surfaces the choices to that PC, no patch |
| `dungeon_store` absent (non-procedural world) | ERROR span `movement.unresolved(no_dungeon_store)`, surfaced, no patch |
| Seated PC has no `pc_regions` entry | fail loud (binding/migration bug) — never silently default to the singular `current_region` |
| Resolution escapes `neighbors(from_region)` set | programmer bug → `raise` (bank records error span); never move into a phantom |
| Target uncommitted + synchronous materialize fails | FAIL LOUD, do not move that PC (Q3) |
| Resolved == this PC's current region | no-op guard in `_apply_world_patch_inner` per-PC block; should be unreachable (§1 step 6 fails first) |
| Emitting connection has no PC region (map) | `dungeon.map_skipped(no_pc_region)`, never a silent fall-through to stale `current_region` |

No `try/except` swallow. No silent stay-put. No invented region. No silent fallback to the singular `current_region`. No parallel narrator path. One PC's failure never blocks another PC's move.

---

## TDD Test Plan (enumerate only — Dev writes these)

**Resolution (unit, fixture graph — no live pack, per `feedback_no_content_coupled_tests`):**
1. `direction="deeper"` picks the strictly-greater-`depth_score` neighbor; correct `kind` tie-break (`shaft` > `chute` > `stairs` > `corridor`).
2. `direction="back"` picks the smallest-`depth_score` discovered neighbor; "way they came" tie-break.
3. `direction="toward_exit"` steps along `bfs_dist` shortest path to `entrance_id`.
4. `exit_descriptor` token-overlap selects the named exit; highest-score wins.
5. Hidden/secret exits excluded from candidates unless in `discovered_routes`.
6. Resolution result is always in `graph.neighbors(from_region)` where `from_region = region_for(perspective=pc)`.

**Per-PC data model & migration (Q0):**
7a. `pc_regions` is the per-PC truth: a move writes only the moving PC's entry; other PCs' entries untouched.
7b. `region_for(perspective=pc)` returns that PC's region; consensus when all seated PCs agree; `None` (party_split) when they disagree — never falls back to stale `current_region`.
7c. Migration: load a pre-this-story save (empty `pc_regions`, set `current_region`) → seeds `pc_regions[name]=current_region` for each seated PC; new save round-trips `pc_regions`.

**Fail-loud:**
8. No candidate edges → `data["error"]=="no_candidate_edges"`, ERROR span `movement.unresolved` (with `pc_name`), **no patch applied** (assert this PC's `pc_regions[pc]` unchanged), directive surfaces exits.
9. Ambiguous descriptor (tied top-2) → `ambiguous_descriptor`, no patch.
10. `dungeon_store is None` → `no_dungeon_store`, no patch.
11. Seated PC missing a `pc_regions` entry → fail loud, never defaults to `current_region`.
12. Resolution escaping `neighbors(from_region)` set → raises (bank catches & spans).

**Transition-fires-once PER PC (behavior, not source grep — per "No Source-Text Wiring Tests"):**
13. One PC's successful move applies exactly ONE `WorldStatePatch(pc_region=...)`; assert `frontier.region_transition` span fired **exactly once** with that `pc_name` and `to_region` appended once to shared `discovered_regions` (no dup).
14. Path-2 ({npc_pool}-only context) invocation applies NO patch and fires NO transition (double-dispatch no-op guard — Keith: leave path 2 in place).

**Materialize ordering (Q3):**
15. Move into an already-committed neighbor → patch applied, observer enqueues next-ring materialize around `to_region` (`materialize_triggered=True`).
16. Move toward an uncommitted edge → synchronous materialize runs first, node exists in fresh `load_map`, THEN patch applied; post-move this PC's region is a real node (`project_region` succeeds). (KEEP this path — Keith resolved former O1: sync-materialize-then-move, not a raise.)

**Per-PC split party (Q5 — REPLACES the old reconciliation tests):**
17. Two PCs seal different intents (`deeper` + `back`) in one round → they end in **different** regions: `pc_regions[A] != pc_regions[B]`, both real graph nodes. Assert **two** `frontier.region_transition` spans (distinct `pc_name`) and **two** `dungeon.materialize` (one per occupied region).
18. After the split, `region_for()` (no perspective) returns `None` / `party_split`; `region_for(perspective=A)` and `(perspective=B)` return their respective regions.
19. One PC's no-edge failure (`movement.unresolved`) does NOT block the other PC's valid move in the same round (independence).
20. Per-PC `dungeon.map_emitted`: PC A's connection emits `is_current_room`/`current_location` for region A; PC B's for region B; both over the same shared `discovered` set. Span carries `pc_name`+`pc_region`.

**Wiring (mandatory — "Every Test Suite Needs a Wiring Test"):**
21. `get_registered()` includes `"movement"` → `run_movement_dispatch` (registry enumeration, refactor-stable).
22. IntentRouter `_SYSTEM_PROMPT` exercised via a behavior test: a movement action through the real router (mocked Haiku returning a `movement` dispatch) → bank invokes `run_movement_dispatch` → that PC's region advances. (Drive the flow + assert span, NOT a source grep.)
23. `intent_router_pass` context now threads `dungeon_store` + `palette` (+ existing `player_name`): fixture session with a `dungeon_store` → movement dispatch resolves through the real graph and moves the dispatching PC (proves the new context wiring reaches the handler).
24. **Reflection tripwire** (allowed exception, per CLAUDE.md): `WorldStatePatch` has a `pc_region` field and `GameSnapshot` has a `pc_regions` field (`model_fields` interrogation) — guards the migration/data-model wiring.

---

## Resolved (was Open) — locked by Keith 2026-05-26

- **O1 — sync-materialize ordering. RESOLVED: KEEP the synchronous materialize-then-move branch** (Q3). Not dead code: under split-party, multiple occupied frontiers compete for the one worker, so the worker falling behind is *more* likely. Do NOT make it a `raise`.
- **O2 — MP reconciliation. RESOLVED/DROPPED: there is no reconciliation.** Movement is per-PC; the party splits. Old deepest-wins/contested model deleted (§Q5).
- **O3 — descriptor synonyms. RESOLVED: hardcode the kind→synonym table in the engine for v1.** Follow-up (noted below) to expose exit-vocabulary in content YAML for Jade.
- **O4 — double-dispatch path 2. RESOLVED: leave it as the harmless no-op.** Consolidation is a separate ADR-105/113 story; do not touch path 2 in this build.

## Follow-ups (explicit, not silent gaps)

- **Asymmetric per-sub-group narration** — narrator addressing each split sub-group as its own scene. Deferred to ADR-104/105 perception filtering or an explicit follow-up story. This build is engine-truth only; the narrator still emits one stream over split positions.
- **Content-authored exit vocabulary** — move the hardcoded kind→synonym table into genre/world YAML so Jade can author dungeon-specific exit words (the §Q1 O3 resolution's v2).
- **Path-2 dispatch consolidation** — retire the redundant `orchestrator.py:2539` invocation under a separate ADR-105/113 story.

## New Open Questions (surfaced by the per-PC model)

- **OP1 — connection→PC binding for the map emit.** §Q-map needs "this connection's PC" to pick the per-PC region. Is `sd.player_id` → seat → PC name reliably resolvable at the `_maybe_emit_dungeon_map` call site for every connected client (including spectators / the GM-panel connection)? If a connection has no seated PC, the spec emits `dungeon.map_skipped(no_pc_region)` — is that the right behavior for a spectator, or should a spectator see the consensus/whole-party view instead?
- **OP2 — does a split party need a per-PC `discovered_regions`?** This build keeps `discovered_regions` shared (a region any PC entered is on everyone's map). If you ever want true per-PC fog (Slabgorb shouldn't see the map of where Rux scouted alone), that is a second per-PC field (`pc_discovered: dict[str, list[str]]`) and a follow-up — out of scope now, but flag if the table-feel wants it.
- **OP3 — rejoin/merge semantics.** When split PCs later move back into the *same* region, `region_for()` returns to consensus automatically (no special handling). Confirm that's the desired "party reunites" behavior and that nothing downstream depends on a distinct merge event.
