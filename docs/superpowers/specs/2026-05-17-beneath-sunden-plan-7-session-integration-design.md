# Beneath Sünden — Plan 7 Session Integration (Look-Ahead Worker Live Wiring)

> Follow-up to Plan 7 (the async look-ahead materializer). Plan 7 server PR
> `slabgorb/sidequest-server#306` is **merged to `develop`** (merge commit
> `bcabbf6`, 2026-05-17). This spec closes Plan 7's sanctioned honest
> deferral: `register_lookahead_worker` has **zero live-session callers**, so
> in a running game the dungeon does not grow. Companion docs PR
> `slabgorb/sidequest#234` (Plan 7 tracker / spec §10 / Post-Implementation
> Corrections) is still open and is **out of scope here** — recording the
> ADR-106 bottleneck CLOSED is a verified-not-asserted, end-of-implementation
> deliverable coordinated with that tracker, not part of this design.

## 1. Problem & Intent

Plan 7 shipped the full five-stage async materializer, the production
frontier-transition producer seam
(`frontier_hook.notify_region_transition`, called from
`GameSnapshot._apply_world_patch_inner`), and a complete, wiring-tested async
consumer (`sidequest/dungeon/lookahead_worker.py::register_lookahead_worker`).
But nothing in the live WebSocket session lifecycle constructs the session
context and registers the worker. The lie-detector signal is `observers=0`
on live `frontier.region_transition` OTEL spans: the seam fires, no one
listens, the dungeon never grows in a real game.

Two facts make "just register the worker" insufficient:

1. The worker only materializes the *next* expansion when the party
   approaches an **existing** unexpanded frontier edge. Frontier edges exist
   only after expansion 0 (entrance) + expansion 1 are committed. Nothing in
   the live session bootstraps that initial dungeon today (the materializer
   has zero live callers; no save carries dungeon data).
2. The merged materializer's curate stage calls `claude -p` via
   `ClaudeClient.send`. The codebase has migrated LLM calls to the Anthropic
   SDK (`AnthropicSdkClient`, default backend of
   `agents/llm_factory.build_llm_client()`; see
   `docs/superpowers/specs/2026-05-15-anthropic-sdk-migration-design.md`).
   New live consumers must not entrench `claude -p`.

**Intent:** a bounded session-integration story that makes a real
`caverns_and_claudes` / `beneath_sunden` game grow its dungeon — bootstrap
the seed at session-open, register the worker for the session's life,
unregister at teardown, and move the curate call onto the established SDK
one-shot pattern. Success is verified, not asserted: `observers >= 1` on a
live `frontier.region_transition` span and a real region crossing toward an
unexpanded frontier edge materializing the next expansion.

## 2. Decisions (locked during brainstorming)

1. **Scope = wire consumer + bootstrap seed.** This story does both: register
   /unregister the worker AND seed expansion 0 + expansion 1 at session-open
   when a `beneath_sunden` save has no dungeon yet. (Consumer-only would leave
   a fresh game non-growing — ADR-106 reduced, not closed.)
2. **`campaign_seed` = persisted dedicated seed.** Generated once at
   bootstrap (`secrets.randbits(63)`), persisted in the save, read back
   verbatim on every reopen. Frozen with the dungeon; never derived, never
   recomputed (save-is-truth).
3. **Bootstrap timing = synchronous during connect.** The expansion-0/1
   bootstrap is awaited inside the connect handler before the first game
   message. One-time cost on the very first open of a campaign; reopens find
   the persisted dungeon + seed and only register the worker. Chosen for
   correctness (the entrance must be a real graph node before any region
   transition) and zero races.
4. **SDK, not `claude -p`.** The merged materializer curate stage moves onto
   the codebase-idiomatic one-shot SDK call; the worker's `claude_client`
   dep is sourced via `build_llm_client()` (default `AnthropicSdkClient`).
5. **Architecture = a dedicated `session_integration` seam module** (Approach
   A). Two one-line incisions into the hot session subsystem; all complexity
   isolated in one focused, independently-testable module.

## 3. Architecture — the `session_integration` seam

One new module: **`sidequest-server/sidequest/dungeon/session_integration.py`**.
Public surface, exactly two functions:

```python
async def attach_dungeon_to_session(
    *,
    store: SqliteStore,
    snapshot: GameSnapshot,
    genre_pack: Any,
    genre_slug: str,
    world_slug: str,
    world_dir: Path,
) -> LookaheadWorkerHandle | None: ...

async def detach_dungeon_from_session(
    handle: LookaheadWorkerHandle | None,
) -> None: ...
```

- The **genre/world gate lives inside the module**: `attach_…` returns `None`
  (a clean no-op) for anything that is not `caverns_and_claudes` +
  `beneath_sunden`, so the call site is unconditional and free of dungeon
  knowledge.
- `attach_…` internally: gate → `DungeonStore(store.connection())` →
  `ensure_schema()` → resolve deps (§4) → idempotent seed-or-load (§6) →
  `register_lookahead_worker(...)` → return the handle.
- `detach_…` is null-safe: `handle.unregister()` then `await
  handle.drain()`.

This mirrors the existing `frontier_hook` / `telemetry.watcher_hub`
module-registry seam precedent (register at session-open, unregister at
teardown). It is the only new production seam.

## 4. Dependency Resolution

`register_lookahead_worker` requires six deps plus the `lookahead_breadth`
knob. Each dep is sourced honestly at session-open; any unresolved dep raises
loudly with a message naming it (No Silent Fallbacks — never register against
a fake or `None`). `lookahead_breadth` is not a sourced dep — it is left at
its default and not tuned here.

| Dep | Source | Notes |
|---|---|---|
| `persistence: DungeonStore` | `DungeonStore(store.connection())` | **New accessor** `SqliteStore.connection() -> sqlite3.Connection`. Plan 5/7 §7.5 requires game-save + dungeon-save share **one** connection/transaction — never a second WAL connection to the same file. |
| `bundle` | `load_cookbook(world_dir)` | `sidequest/game/cookbook/loader.py`; today test-only, now called at session-open. |
| `palette: ThemePalette` | `load_theme_palette(pack_root)` | `sidequest/dungeon/themes.py`. `pack_root` is the genre-pack directory containing `themes/` (Plan 4 layout `genre_packs/caverns_and_claudes/themes/`), resolved from `world_dir` / `genre_pack` and verified loud (raise if `themes/` absent). |
| `pack_tropes` | resolved from `genre_pack` | Genre + world tropes already at session scope on the loaded `GenrePack`. |
| `claude_client` | `build_llm_client()` | `agents/llm_factory.py`; default backend `anthropic_sdk` → `AnthropicSdkClient` (a `ToolingLlmClient`). Explicitly **not** `ClaudeClient()`/`claude -p`. |
| `campaign_seed: int` | persisted seed (§5) | Read verbatim from the save; never recomputed. |
| `lookahead_breadth` | default `1` | Spec §12 knob default; not tuned here. |

## 5. `campaign_seed` Persistence

A new single-row table in the **same save DB**, owned by `DungeonStore`
alongside the Plan-5 `dungeon_*` tables:

```sql
CREATE TABLE IF NOT EXISTS dungeon_meta (
    id            INTEGER PRIMARY KEY CHECK (id = 1),  -- single-row guard
    campaign_seed INTEGER NOT NULL
);
```

`DungeonStore` gains:

- `get_campaign_seed() -> int | None` — `None` iff the row is absent (fresh
  save).
- `set_campaign_seed(seed: int) -> None` — inserts the single row; raises
  loudly if a row already exists (the seed is write-once; a second write is
  a contract violation, not an upsert).

`ensure_schema()` creates `dungeon_meta` with the other dungeon tables. At
first bootstrap: `seed = secrets.randbits(63)`, `set_campaign_seed(seed)`,
inside the same bootstrap transaction as the seed expansion. Every reopen:
`get_campaign_seed()` returns the frozen value, passed verbatim to the
worker. The seed is never derived from the slug or anything else.

## 6. Idempotent Bootstrap (Seed = Expansion 0)

Inside `attach_dungeon_to_session`, after `ensure_schema()`:

- **Already seeded** — `load_map(entrance_id="entrance")` is non-empty: skip
  bootstrap, `get_campaign_seed()` (must be present — if the map exists but
  the seed row does not, that is a corrupt save → raise loud), register the
  worker. This is every reopen; it is fast.
- **Fresh save** — `load_map` *and* `load_frontier` both empty (loudly
  detected, never assumed — the merged materializer's documented
  precondition): generate + persist `campaign_seed`, construct the entrance
  region + initial `RegionGraph` and the first
  `MaterializationRequest(expansion_id=1, …)`, then `await materialize(...)`
  once. The merged Task-6 commit stage commits the entrance as
  `Expansion(expansion_id=0, new_nodes=[entrance], new_edges=[])` **before**
  the generated expansion 1 — the Seed = Expansion 0 contract is the only
  seed path; the bootstrap does not hand-roll a second one, and relies on
  the pipeline's `rollback()`-on-`PersistError` (caller owns the txn,
  §7.5).

**Executable spec for the entrance / seed graph.** The substantive part of
the bootstrap is the *production analog* of the test seeding helpers in
`sidequest-server/tests/dungeon/test_materializer.py`:
`_seed_graph_themed`, `_commit_palette`, `_materialize_full` (and the
`lookahead_worker` test's `_seed_expansion_one`, which composes them). Those
helpers are the authoritative shape for "seed expansion 1 from nothing." The
implementation plan pins the production entrance/seed-graph construction
against them and against the
`project_beneath_sunden_plan5_seed_expansion0` contract: entrance
`depth_score == 0.0` (frozen root), entrance id `"entrance"`, entrance
belongs to no generated `Expansion.new_nodes`, `rollback()` on
`PersistError`. The entrance is the surface entry to the megadungeon for
world `beneath_sunden`; its theme is drawn from the loaded `ThemePalette`
(shallowest depth band).

Bootstrap runs **synchronously awaited inside the connect handler** before
the first game message is processed.

## 7. SDK Curate Migration (merged-materializer change)

Per Decision 4, the merged `sidequest/dungeon/materializer.py` curate stage
moves off `claude -p` onto the established one-shot SDK pattern (the
orchestrator SDK path is the precedent; no `.send()`-shim exists — call
`complete_with_tools` directly with no tools):

- `_stage_curate`: replace `response = await claude_client.send(prompt)` with

  ```python
  result = await curation_client.complete_with_tools(
      system_blocks=[CacheableBlock(text=_CURATION_SYSTEM, cache=False)],
      messages=[Message(role="user", content=prompt)],
      tools=[],
      tool_dispatch=None,
      model=resolve_model(CallType.SCRATCH),
  )
  curated_text = result.text
  ```

  (`CacheableBlock`, `Message` from `agents/tooling_protocol.py`;
  `resolve_model`, `CallType` from `agents/model_routing.py`.)
- Catch the common base **`LlmClientError`** (covers
  `AnthropicSdkClientError` and `ClaudeClientError`), wrap in the existing
  `CurationError` — the curation-failure-is-LOUD contract and the curate
  OTEL span are preserved exactly.
- `materialize(...)`: drop the `else ClaudeClient()` silent default —
  `claude_client` becomes **required** (the worker always supplies one;
  tests inject a fake). Widen the `ClaudeClient | None` annotations to the
  tooling-client protocol / `Any` consistent with the rest of the migrated
  surface.
- **Necessary test-seam consequence (not scope creep):** the shared Plan-7
  test client fakes (`_reflecting_claude_client`, `_fake_claude_client`,
  `_yielding_concurrency_probe_client` in `tests/dungeon/test_materializer.py`
  / `test_lookahead_worker.py`) are `ClaudeClient.send`-shaped. Once curate
  calls `complete_with_tools`, those fakes must move to an SDK shape (an
  injected fake `AsyncAnthropic` behind `AnthropicSdkClient(sdk=…)`, or a
  `ToolingLlmClient` stub returning a `ToolingResult` whose `.text` is the
  curation verdict). Migrating these shared fakes is part of the §7 change —
  it is the only way §10's "existing materializer/worker tests stay green"
  holds. The reflected-verdict semantics are preserved exactly; only the
  client surface changes.
- **Model tier:** `CallType.SCRATCH` (Haiku) — **decided** (spec read,
  2026-05-17). Curation is structured selection/refinement of monster
  manifests + telegraphs (JSON-shaped, not player-facing prose) and runs
  once ahead of the party — the cheap tier is appropriate.

This is the only change to merged Plan 7 code, and it is the minimal,
codebase-idiomatic diff.

## 8. Session Lifecycle Integration Points

Two one-line incisions; no other production files change beyond the new
module, the two `DungeonStore`/`SqliteStore` accessors, and the §7 curate
edit.

- **Open** — `sidequest/handlers/connect.py`, immediately after
  `_SessionData` is constructed (genre/world/snapshot/store/world_dir all
  resolved): `session._session_data.lookahead_handle = await
  attach_dungeon_to_session(...)`. Add
  `lookahead_handle: LookaheadWorkerHandle | None = None` to `_SessionData`.
- **Teardown** — `sidequest/server/websocket_session_handler.py::cleanup()`,
  immediately after the existing `embed_task` cancellation (the established
  per-session async-resource precedent) and before the `room.save()` /
  `store.save()` step: `await
  detach_dungeon_from_session(self._session_data.lookahead_handle)`.

## 9. Error Handling & the Task-7 Central Constraint

- **Task-7 central constraint preserved untouched.** The sync frontier
  observer must never re-raise into
  `GameSnapshot._apply_world_patch_inner` / `apply_world_patch`; a
  background-prefetch failure must never abort the party's region crossing.
  That guarantee lives entirely inside the already-merged
  `lookahead_worker._observer` (guarded, loud-on-span, no re-raise). This
  story **reuses `register_lookahead_worker` exactly as merged** and adds no
  path that defeats it. Verified by the session-lifecycle wiring test
  asserting a forced background failure does not abort a real region
  crossing.
- **Bootstrap failure at connect (fail loud).** The bootstrap materialize
  pipeline can fail (LLM/persist). Policy: surface the error, do **not**
  register a worker against a half-seeded dungeon, and do **not** silently
  start the session with a broken dungeon. A `beneath_sunden` session whose
  dungeon cannot be seeded is not a playable session — aborting connect with
  a loud error is correct (No Silent Fallbacks). The pipeline's own
  `rollback()`-on-`PersistError` keeps the save clean for a later retry.
- **Dep-resolution misses** raise with a specific message naming the missing
  dep (e.g., absent `themes/` directory, unresolvable `world_dir`).
- **Corrupt-save guard:** map present but `campaign_seed` row absent → raise
  loud (a real corruption, never a silent re-seed that would fork the
  dungeon).
- **Cross-session double-register guard (residual, §14.D).** Each session
  builds a *new* `LookaheadWorkerHandle` → a *new* bound `_observer`;
  `register_lookahead_worker`'s identity-dedup therefore does **not** hold
  across sessions, so two concurrent sessions on one save would
  double-register and double-materialize. The hard constraint forbids
  touching `lookahead_worker.py`/`frontier_hook.py`, so the guard lives in
  the seam this story owns: `session_integration` keeps a process-level
  live registry keyed by **save identity** (save DB path; in-memory stores
  are distinct objects). A second `attach_dungeon_to_session` for an
  already-attached save raises **loud** (concurrent sessions on one save is
  a real contract violation, not a silent upsert — No Silent Fallbacks);
  `detach_dungeon_from_session` clears the key. Sequential reopen (the
  real playgroup pattern — one shared session per save, submit-and-wait)
  is unaffected; the idempotent-reopen contract (§6) is unchanged.

## 10. Testing Strategy

The mandatory session-lifecycle wiring test is the keystone (Every Test
Suite Needs a Wiring Test; the existing worker test proves the *worker*, not
the *session lifecycle*).

- **Session-lifecycle wiring test (new, keystone):** drive the real
  connect → region-crossing → teardown path for a fresh
  `caverns_and_claudes` / `beneath_sunden` save on a real save-DB
  connection, against the **real `GenreLoader().load('caverns_and_claudes')`
  GenrePack** — **no `_attach_pack`-fabricated `.tropes`** (§14.C: that
  fabrication was the No-Stubbing violation that masked the content gap;
  it is deleted from both `test_session_lifecycle_wiring.py` and
  `test_session_integration.py`). The only mock is the SDK curate call
  (the Task-4 injected-client precedent, now an SDK fake). Assert:
  (a) bootstrap commits expansion 0 + expansion 1 (the depth-0 entrance
  theme `drowned_cavern` set-piece `the_siphon` resolves its
  `the_thing_that_followed_you_down` trope against the real pack — the
  exact path that aborted connect before §14.A);
  (b) `frontier_hook.registered_observer_count() >= 1` while the session is
  live;
  (c) a real region crossing toward an unexpanded frontier edge materializes
  the next expansion (`max(expansion_id)` grows);
  (d) the live `frontier.region_transition` span carries **`observers >=
  1`** (the lie-detector signal flips off zero);
  (e) after `cleanup()`, observer count returns to its pre-session baseline
  (no registry leak);
  (f) a second `attach_dungeon_to_session` for the same live save (before
  `detach`) raises loud and does **not** add a second observer
  (§14.D save-keyed dedup); after `detach`, a fresh attach for that save
  succeeds (sequential reopen is unaffected).
- **Idempotency:** second open of the same save does not re-seed and reuses
  the persisted `campaign_seed`.
- **Seed persistence round-trip;** **non-`beneath_sunden` is a clean
  no-op (returns `None`, registers nothing);** **bootstrap failure aborts
  connect loud and registers nothing;** **central-constraint reuse** (forced
  background failure does not abort a real crossing).
- **SDK curate unit test:** `_stage_curate` issues the one-shot
  `complete_with_tools(tools=[])` shape and a failed call (`LlmClientError`)
  becomes `CurationError`.
- Existing `test_lookahead_worker.py` / `test_frontier_hook` / materializer
  tests stay green; full server suite + routing-completeness gate.

## 11. Scope Boundary

**In scope:** the `session_integration` module; the two
`DungeonStore`/`SqliteStore` accessors; `dungeon_meta` seed table; the
synchronous idempotent bootstrap; the §7 curate SDK edit; the two lifecycle
incisions; the test suite above; **plus the §14 DO-NOT-SHIP resolution: the
4-trope content fix in `sidequest-content` (§14.A), the real-pack keystone
rewrite (§14.C), the save-keyed residual guard (§14.D), and — gated on a
verified real-pack growth — the ADR-106 CLOSED recording (§14.E)**.
The ADR-106 closure recording is now part of *this* story's close-out
(Keith's decision 2026-05-17: genuinely close ADR-106 here, verified not
asserted) — it is no longer deferred to a separate deliverable.

**Out of scope:** streaming-narrator SDK migration and any `claude -p` → SDK
work beyond the curate stage; the broader Anthropic SDK migration (its own
spec); the companion docs PR #234 *mechanics* (tracker bookkeeping —
coordinated with, not authored by, this story); **the `beneath_sunden`
`visual_style.yaml` port (§14.B — handled in a separate workstream)** and
adapting any other `caverns_sunden` asset (the rest is sins-comedy-specific
or already authored fresh in `beneath_sunden` — a faithful port would
import the wrong tone); `lookahead_breadth > 1` tuning (default 1); the
Plan-5
mask-persistence gap (inert, tracked in `project_beneath_sunden`); ADR
authoring (this reuses ADR-106 / Plan 7 decisions, adds none).

## 12. Decomposition (implementation-plan seed)

Ordered, TDD, subagent-driven with two-stage (spec → code-quality) review
per task, the Plan 7 discipline:

1. `SqliteStore.connection()` accessor + unit test (one connection, §7.5).
2. `DungeonStore` `dungeon_meta` schema + `get/set_campaign_seed`
   (write-once) + round-trip test.
3. Production entrance / seed-graph builder + first
   `MaterializationRequest` (pinned against the test seeding helpers + the
   Seed=Expansion-0 contract) + unit test.
4. `_stage_curate` SDK one-shot migration + `materialize` required-client
   change + curate unit test (`LlmClientError` → `CurationError`).
5. `session_integration.attach_dungeon_to_session` /
   `detach_dungeon_from_session` (gate, dep resolution, idempotent
   seed-or-load, register/return; null-safe detach) + unit tests
   (non-`beneath_sunden` no-op, dep-miss loud, idempotent reopen).
6. Connect-handler open incision + `_SessionData` field + cleanup teardown
   incision.
7. The keystone session-lifecycle wiring test (all of §10 (a)–(e)) +
   central-constraint reuse test + full-suite gate.

## 13. Resolved at Spec Read (2026-05-17)

1. **Curate model tier — DECIDED:** `CallType.SCRATCH` (Haiku). Structured
   curation, runs once ahead of the party; cheap tier is correct. (Not
   `CallType.NARRATION`.)
2. **Entrance theme — DECIDED:** the entrance uses the shallowest depth-band
   theme from the loaded `ThemePalette` (no new content needed; consistent
   with the depth gradient). The exact construction is pinned in the
   implementation plan against the test seeding helpers + the
   Seed=Expansion-0 contract; no fixed dedicated "entrance" theme is
   introduced.

## 14. Post-Design Correction — DO-NOT-SHIP Resolution (2026-05-17)

> The 7-task branch (`feat/beneath-sunden-plan-7-session-integration`, tip
> `ffff55c6`) is engineering-correct and 6480-suite green, but the final
> adversarial review returned **DO-NOT-SHIP**: a verified, pre-existing
> Plan-4 content gap means a real `beneath_sunden` session aborts at
> connect and the dungeon never grows — **ADR-106 is NOT closed; it was
> relocated.** This section is the authoritative resolution and supersedes
> any earlier clause it contradicts. Keith's chosen path (2026-05-17): *fix
> the content gap + drive the keystone with the real GenrePack* so ADR-106
> is genuinely closed, verified not asserted.

**The verified blocker (traced in code, not asserted).**
`connect.py:~400` constructs `genre_pack = GenreLoader().load(genre_slug)`
(the **genre-level** pack) and passes it straight through as
`pack_tropes`. `setpiece_attach.py:411-413` resolves a set-piece's
`trope_id` against `{t.id: t for t in pack_tropes.tropes}` — i.e. the
genre-level `genre_packs/caverns_and_claudes/tropes.yaml`, which defines
only `{the_keeper_stirs, extraction_panic, hireling_mutiny,
the_deeper_dark}`. World tropes live under `genre_pack.worlds[w].tropes`
(== `[]` for `beneath_sunden`) and are **never passed**; `resolve.py`
emits only world tropes anyway. The 5 Plan-4 genre-level themes reference 4
trope_ids that exist nowhere:

| trope_id | theme (set-piece) | set-piece params |
|---|---|---|
| `the_thing_that_followed_you_down` | `drowned_cavern` (`the_siphon`) | `{from_region: surface}` |
| `the_keeper_notices_the_disturbance` | `bone_crypt` (`the_false_floor`) | `{patience: low}` |
| `priest_demands_a_sacrifice` | `sunless_temple` (`the_altar_that_waits`) | `{countdown_expansions: 2}` |
| `the_resource_clock_you_can_see` | `labyrinth_trap` (`the_only_path`) | `{resource: light}` |

`drowned_cavern` is the depth-0 **entrance** theme (`DepthBand min 0.0`),
hit *first* by the bootstrap → `attach_set_piece` PASS-1 raises
`ValueError: trope_id 'the_thing_that_followed_you_down' not found in pack`
→ connect aborts. The 7 tasks' tests pass only because
`test_session_integration.py`/`test_session_lifecycle_wiring.py` inject
`_attach_pack(*fabricated ids)` — a No-Stubbing violation masking the gap
(false green). `winding_catacomb` / `sunless_temple` `quest_components`
(`find_the_unlit_way_out`, `deny_or_feed_the_altar`) need **nothing** —
re-verified: `setpiece_attach.py` (Decisions B/C, L488-489, L584) has no
quest registry; quest_id is thread-provenance only.

### 14.A — Author the 4 tropes (genre-level, `sidequest-content`)

Home **decided by code-tracing, not guessed:** the 4 tropes go in
genre-level **`genre_packs/caverns_and_claudes/tropes.yaml`** — the only
file the materializer resolves against (chain above). A
`worlds/beneath_sunden/tropes.yaml` would never be consulted by the
materializer *and* `resolve.py` would drop the 4 genre tropes from the
world view — architecturally wrong for this path. The Plan-4 themes are
themselves genre-level, so their tropes belong genre-level (consistent;
they are generic megadungeon set-piece tropes — the genre *is* the
megadungeon now).

Author all 4 **faithfully** to the real `TropeDefinition` schema
(`id`, `name`, `description`, `category`, `triggers`, `narrative_hints`,
`tension_level`, `resolution_hints`/`resolution_patterns`, `tags`,
`escalation[at/event/npcs_involved/stakes]`, `passive_progression`) — real
game tropes, **not stubs**. Match (a) the existing genre trope voice
(`the_keeper_stirs` family — Keeper/extraction/depth, grave, lethal),
(b) `beneath_sunden`'s tone ("Grave, lethal, Moria-as-tragedy. No
winking."), (c) each set-piece's mechanical intent + params (e.g.
`priest_demands_a_sacrifice` escalation is a ~2-expansion countdown ending
in sacrifice-or-consequence; `the_resource_clock_you_can_see` escalates a
visible light/resource drain). Authored by the **writer** +
**scenario-designer** agents, two-stage reviewed. **Subrepo-branch
discipline:** a `sidequest-content` `feat/*` branch created **before**
dispatching any content implementer; this content must merge first/with
the server branch (the server keystone reads the sibling content
checkout).

### 14.B — `visual_style.yaml` port — OUT OF SCOPE (handled elsewhere)

**Removed from this story (Keith, 2026-05-17): the `beneath_sunden`
`visual_style.yaml` port is being handled in a separate workstream.** It is
loaded via the existing optional path and requires no server change, so it
is fully decoupled from this story's ADR-106 closure. Not in this spec's
plan, tests, or close-out gate. (The original analysis — that the port
reduces to `visual_style.yaml` because the rest of `caverns_sunden` is
sins-comedy-specific — is retained in §11 for the record.)

### 14.C — Real-pack keystone rewrite (`sidequest-server` branch)

Rewrite `tests/dungeon/test_session_lifecycle_wiring.py` **and**
`tests/dungeon/test_session_integration.py` to drive the real
`GenreLoader().load('caverns_and_claudes')` GenrePack and **delete every
`_attach_pack` fabrication**. They must pass *for real* once 14.A merges —
genuinely proving a real session grows the dungeon (§10 (a)–(f)).

### 14.D — Save-keyed residual guard (`session_integration`, the seam we own)

Per §9's new cross-session bullet. The hard constraint forbids touching
`lookahead_worker.py`/`frontier_hook.py`; the save-identity dedup lives in
`session_integration.py` (process-level live registry keyed by save DB
path). Second concurrent attach for an already-attached save raises loud;
detach clears the key. Covered by §10 (f).

### 14.E — Close-out (gated, verified-not-asserted)

Only **after** 14.A, 14.C, and 14.D land (14.B is out of scope — handled
elsewhere) and the real-pack keystone genuinely passes
(observers ≥ 1 on a real `frontier.region_transition` span + a real
crossing materializes the next expansion): re-run the final adversarial
whole-impl review against the real pack; then — and only then — record
**ADR-106 CLOSED** in the parent megadungeon spec
(`docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md`)
§10 decomposition item 7 (Plan 7) + that spec's Post-Implementation
Corrections appendix (coordinated with companion docs PR #234), and finish
the branch via `superpowers:finishing-a-development-branch`.
Until that verification passes, ADR-106 is **not** claimed closed
anywhere. No push/merge until the real-pack keystone is genuinely green
and the final review clears.
