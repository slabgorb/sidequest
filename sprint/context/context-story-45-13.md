---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-13: Container/object retrieved-state on room re-entry

## Business Context

**Playtest 3 evidence (2026-04-19, Orin):** Orin knocked the same tin
box off the same wall in round 10 and again in round 16. The narrator
described the same retrieval prose both times and yielded identical
contents (or the model improvised "same" contents — either way the
fiction collapsed). The room's tin box has no per-object retrieved
flag, no lifecycle state, no negative gate when the player re-enters.
Container/object state on re-entry is **implicit** — driven by the
narrator's session memory (ADR-067), which is not authoritative for
mechanical state and explicitly should not be (ADR-014: narrator
narrates, scripts crunch).

This is the **explicit-lifecycle-states-beat-implicit-booleans** lesson
that recurs across Lane B (Epic 45 §3). Sibling stories on the same
theme: 45-14 (`state=Carried` doesn't transition to `Discarded` on
narrator-extracted discard verbs); 45-15 (`Consumed` items not removed
from inventory). 45-13 is the *container* end of that lifecycle —
items have a state, containers have a state, and re-entry is the
read-side gate that keeps the two in sync.

For James (narrative-first), the surface symptom is broken
continuity — he remembers searching the box, the narrator either
contradicts him or pretends nothing happened. For Sebastien
(mechanical-first), this is the GM panel's blind spot — the retrieved
state is in narrator session memory, not in the snapshot, so the
panel can't show "this box has been emptied." For Alex (slower
reader), it's pacing-killing repetition.

ADR-014 (Diamonds and Coal): the tin box's contents are diamond on
first retrieval; the second retrieval is coal pretending to be
diamond. The fix is the explicit `retrieved` state on the container
plus the negative gate at narrator-prompt time.

ADR-085 (port-drift): there is **no Rust precedent** for per-object
retrieved state — the Rust tree never wired this. This is a green
field on the Python tree; do not look for a Rust port to mirror.

## Technical Guardrails

### Outermost reachable seam (wire-first gate)

The wire-first gate has two seams, both must be hit:

1. **Extractor seam — narrator-extracted retrieval action.**
   `sidequest/server/narration_apply.py` already applies
   `result.items_gained` / `result.items_lost` on the rolling
   character (`narration_apply.py:251–319`). The extractor MUST be
   extended (or a sibling extractor added) to detect *which container*
   the items were retrieved from. The narrator's structured output
   already names containers in prose; the orchestrator's
   `NarrationTurnResult` must surface a new `containers_emptied:
   list[ContainerRetrieval]` field (or augment `items_gained` entries
   with `from_container: str | None`). Either shape works; the second
   is less invasive.

2. **Applier seam — room/snapshot state mutation.** A new collection
   on `GameSnapshot` — `retrieved_objects: dict[str, list[str]]`
   keyed by `room_id`, value list of container ids retrieved from in
   that room — OR a new `RoomState` model holding richer per-room
   data. Per Epic 45 theme §1 (explicit lifecycle states), prefer
   the typed model:

   ```python
   class ContainerState(BaseModel):
       container_id: str
       retrieved: bool = False
       retrieved_at_round: int | None = None

   class RoomState(BaseModel):
       room_id: str
       containers: dict[str, ContainerState] = {}
   ```

   On `GameSnapshot`:

   ```python
   room_states: dict[str, RoomState] = Field(default_factory=dict)
   ```

3. **Narrator-prompt gate seam.** When the narrator's turn-context
   builds (`session_helpers.py` per the 45-1 reference), the
   currently-occupied room's `RoomState` is injected into the prompt
   as a "previously retrieved" hint — the narrator is told "the tin
   box has been retrieved from in round 10" so it doesn't re-narrate.
   This is the load-bearing gate; without it, ADR-067's persistent
   narrator session can re-emit the contents on its own.

The wire-first boundary test must drive a turn that retrieves a
container, then a turn that re-enters the room and attempts to
retrieve again, and assert (a) the second turn's narrator prompt
contains the "already retrieved" hint AND (b) the second turn's
extracted `items_gained` is empty (or that the negative gate filters
it). Unit tests on `ContainerState` mutators alone fail the wire bar.

### Content-source for container ids

Today's `RoomDef` (`sidequest/genre/models/world.py:78–92`) has no
`containers` or `objects` field — only `id`, `name`, `room_type`,
`exits`, `description`, `grid`, `tactical_scale`, `legend`. Container
ids are emergent from narration prose. Two options:

1. **Narrator-emitted container ids.** The orchestrator extracts a
   slug from the prose ("the tin box on the wall" →
   `tin_box_on_the_wall` or just `tin_box`). Stable enough for the
   single-room case; collisions across rooms are scoped by
   `room_id` key. **Recommend this** — adding a `containers:
   list[ContainerDef]` field to `RoomDef` is content-pack work that
   doesn't fit a wire-first story's scope, and most worlds in
   `sidequest-content/genre_packs/` would need updating.

2. **Pack-declared container ids.** Add `containers` to `RoomDef`,
   require packs to enumerate them. Higher-trust but
   content-migration-heavy. Defer to a follow-up.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md)

Define in `sidequest/telemetry/spans.py` and register routes. The
existing `SPAN_INVENTORY_NARRATOR_EXTRACTED` at `spans.py:370–371` is
the precedent shape:

| Span | Attributes | Site |
|------|------------|------|
| `container.retrieval_recorded` | `room_id`, `container_id`, `round_number`, `interaction`, `items_gained_count`, `genre`, `world`, `player_name` | `narration_apply.py` after appending the new `RoomState` entry |
| `container.retrieval_blocked` | `room_id`, `container_id`, `prior_retrieved_at_round`, `current_round`, `interaction`, `genre`, `world`, `player_name` | when narrator emits a duplicate retrieval that the negative gate filters |
| `room.state_injected` | `room_id`, `retrieved_container_count`, `interaction` | every narrator-prompt build that injects a `RoomState` |

`room.state_injected` MUST fire on every narrator turn (with
`retrieved_container_count=0` in the no-prior-retrievals case) — same
Sebastien lie-detector argument as elsewhere in this epic. Pair with
`_watcher_publish` per the established Lane B pattern.

### Reuse, don't reinvent

- `narration_apply.py:apply_narration_result()` is the existing
  applier for narrator-extracted state. The new container-retrieval
  applier belongs there as a sibling block to the
  inventory-mutation block at lines 245–319.
- `NarrationTurnResult` (`sidequest/agents/orchestrator.py`) is the
  existing extractor payload. Extend, don't replace.
- `room.snapshot` (`session_room.py`) is the canonical snapshot
  binding — `room_states` lives on the snapshot proper, mutated under
  the room lock through the existing save path.
- `_build_turn_context()` is the documented narrator-prompt seam (per
  the 45-1 reference at `session_helpers.py:143–243`); the
  RoomState injection lands there.
- `discovered_rooms: list[str]` on `GameSnapshot`
  (`session.py:406`) tracks visited rooms — `room_states` is the
  richer sibling. Do not collapse them; they answer different
  questions.
- The 45-14 / 45-15 sibling stories operate on item state
  (Carried/Discarded/Consumed). They share the lifecycle pattern;
  do not invent a separate idiom.

### Test fixtures

- `session_handler_factory()` at
  `sidequest-server/tests/server/conftest.py:332` — for the wire-test.
- `_FakeClaudeClient` at `conftest.py:197` — drive scripted narrator
  outputs that include retrieval prose and attribute container ids.
- The Orin regression fixture: two turns at rounds 10 and 16, same
  room, same container_id, both "retrieve" the tin box.

### Test files (where new tests should land)

- New: `tests/server/test_container_retrieval_state.py` — wire-test
  driving the Orin regression scenario and asserting the negative
  gate fires on the second retrieval.
- New: `tests/server/test_room_state_model.py` — unit tests for
  `RoomState` / `ContainerState` mutators.
- Extend: `tests/server/test_encounter_apply_narration.py` (or
  sibling) — apply-time tests for the new
  `containers_emptied` extraction.

## Scope Boundaries

**In scope:**

- New `ContainerState` and `RoomState` pydantic models on
  `sidequest/game/session.py` (or sibling
  `sidequest/game/room_state.py`).
- New `room_states: dict[str, RoomState]` field on `GameSnapshot`.
- Extend `NarrationTurnResult` with a container-retrieval shape
  (recommend `from_container: str | None` per `items_gained` entry,
  to minimize blast radius).
- Apply path in `narration_apply.py` writes the
  `RoomState.containers[container_id].retrieved = True` plus
  `retrieved_at_round = snapshot.turn_manager.round`.
- Narrator-prompt gate in the turn-context builder (sibling to the
  45-1 wire) injects a "previously retrieved" hint when the current
  room has any retrieved containers.
- New OTEL spans `container.retrieval_recorded`,
  `container.retrieval_blocked`, `room.state_injected`, registered in
  `SPAN_ROUTES`.
- Wire-first boundary test driving the Orin regression (two-turn
  retrieval, second turn must be blocked / emit blocked-span).

**Out of scope:**

- Adding `containers` to `RoomDef` (`world.py:78`) or migrating
  every pack's rooms.yaml. Container ids stay narrator-emergent for
  this story; pack-declaration is a follow-up.
- Item state lifecycle (Carried/Discarded/Consumed). Sibling
  stories 45-14 / 45-15 cover that. Do not reinvent a parallel
  enum here for items — only the *container* gets a state. Items
  belong to inventory and have their own enum.
- Multi-player visibility filtering on retrieved containers. ADR-028
  perception rewriter applies; if a peer hasn't been to the room,
  they don't see the retrieved hint. That filtering is layered on
  top per the existing perception pattern; do not reinvent here.
- Trap / lock state on containers. This story is *retrieved-state*
  only.
- Room re-entry resetting of stochastic descriptors (e.g., the
  ambient description varying across visits). Out of scope.
- UI surfacing of "you've already searched here" on the player side.
  Server-side gate is enough to prevent narrator double-emission;
  player-facing UI cue is a separate UX story.
- Save migration. Old saves without `room_states` deserialize with
  the field empty (default `{}`); this is forward-compatible.

## AC Context

1. **First retrieval of a container in a room records state and emits
   `container.retrieval_recorded`.**
   - Wire-test: drive a narration turn whose orchestrator output
     includes `items_gained=[{"name": "tin box contents", "from_container": "tin_box"}]`.
     Assert
     `snapshot.room_states[current_room_id].containers["tin_box"].retrieved == True`,
     `retrieved_at_round` reflects the turn's round, span fires once
     with the correct attributes.

2. **Second retrieval of the same container in the same room is
   blocked; `container.retrieval_blocked` fires.**
   - Wire-test (the Orin regression): drive turn 10 (first
     retrieval, AC #1 passes). Drive turn 16 — same room, same
     container_id. The narrator-prompt for turn 16 MUST contain the
     "previously retrieved at round 10" hint
     (`room.state_injected` span fires with
     `retrieved_container_count >= 1`). If the narrator nonetheless
     emits a retrieval, the apply-time gate filters it: items are
     NOT appended to inventory; `container.retrieval_blocked` fires
     with `prior_retrieved_at_round=10`, `current_round=16`.
   - This is the negative-to-positive transformation: the bug
     evidence (Orin's identical contents at rounds 10 and 16)
     becomes the failing test.

3. **Negative gate is room-scoped, not global.**
   - Test: container `tin_box` in room A is retrieved; an unrelated
     container also called `tin_box` in room B has no state. First
     retrieval in room B succeeds normally.

4. **`room.state_injected` fires on every narrator turn.**
   - Test: 3 narrator turns — first turn (no retrievals yet, span
     fires with `retrieved_container_count=0`); second turn (one
     retrieval recorded, span fires with `retrieved_container_count=1`
     for that room); third turn (different room, span fires with
     `retrieved_container_count=0` for the new room).
   - Sebastien's lie-detector requires the no-op-firing case.

5. **Round-trip persistence — `room_states` survives save → load.**
   - Test: drive a retrieval, save the snapshot, reload via
     `SqliteStore.load()`, assert
     `snapshot.room_states[room_id].containers[container_id].retrieved
     == True`. Forward-compat: load a snapshot serialized without
     `room_states` (older save) → field defaults to `{}` cleanly.

6. **Apply-time gate is the load-bearing block (not just the
   prompt-time hint).**
   - Test: bypass the prompt hint (force the narrator to emit a
     retrieval anyway, e.g., by stubbing the orchestrator). Assert
     the apply-time gate still filters the items_gained for the
     already-retrieved container, items are NOT appended,
     `container.retrieval_blocked` fires. The prompt hint reduces
     the rate of leak; the apply-time gate prevents the leak.
