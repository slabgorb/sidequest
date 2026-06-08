# Persistent Location Descriptions with Mechanical Manifest — Design

**Date:** 2026-05-19
**Author:** Oberon (Architect agent) with Keith
**Status:** Design approved; pending implementation plan
**Audience:** Future-Keith, future-agents implementing Epics 54 + 55

---

## 1. Problem

SideQuest's narrator (Anthropic SDK per ADR-101) can write convincing prose with zero mechanical backing. A player who engages with a described detail — "I tug the rusted chain hanging from the ceiling" — discovers an empty trapdoor: there is no chain object, no affordance, just improv. Sometimes the improv is charming; often it collapses (overbaited hook, broken trust).

The play table asked for **persistent room/area descriptions, mechanically backed**. Anything the description names must either:

- be a real game-state thing with affordances, OR
- be trivial enough that "yes-and" promotion handles engagement without breaking trust.

This is the SOUL.md "Diamonds and Coal" + "Yes, And" + OTEL-Observability principles applied to flavor text. It also lives under the Zork-Problem doctrine — the manifest is a **producer-side contract** (what the narrator and authors may claim), never a **consumer-side gate** (the closed verb set of "things players may touch"). The player can always introduce new entities the description didn't mention; the system says yes.

A new UI tab "Location" surfaces the description so players can read it on demand.

## 2. Scope

### In scope

- Server-side typed manifest of named entities per location, with three tiers (`real_object`, `yes_and`, `flavor_only`).
- Two production paths:
  - **POI worlds** — hand-authored manifest in `cartography.yaml regions[*].entities[]`.
  - **Procedural worlds** (`beneath_sunden`) — deterministically composed by the existing cookbook pattern (`game/cookbook/assemble.py` + `LookDef.dressing` + `SpecialRoom.telegraph`) at dungeon materialize time.
- A `pf validate locations` validator enforcing well-formedness, binding resolution, and prose-manifest coherence at author/CI time.
- Runtime resolver tool `resolve_location_entity` with **two modes**: `narrator_proactive` (closed contract; manifest miss = no-commit) and `player_initiated` (open canon; manifest miss = mint new `yes_and` entity).
- `location_promotions` SQLite table for runtime mutation (flavor_only → yes_and promotion, plus player-initiated mint). Authored YAML never mutates.
- Encounter-bound action overrides — entity_delta + prose_suffix layered at read time, base never destructive.
- OTEL spans for resolver activity, mint events, promotion events, overlay activate/deactivate.
- New UI `LocationPanel.tsx` tab — prose-only render (base + active overlay suffixes).

### Out of scope (v1)

- Player-facing entity chips / clickable manifest in the Location tab. **Reinforced exclusion** — surfacing the manifest as a UI verb set is itself a Zork violation. Manifest stays server-side contract data.
- Multi-language prose.
- Audio cues bound to entities.
- Image generation bound to entities (POI/room image regeneration on overlay).
- Cross-region entities (entities referenced from multiple regions). NPCs go via the NPC subsystem.
- Per-PC perception filtering on the manifest (ADR-104 / ADR-105). Deferred; all entities universally visible in v1.

## 3. Architecture Overview

```
POI worlds (hand-authored)              Procedural worlds (beneath_sunden)
─────────────────────────────           ─────────────────────────────────
cartography.yaml regions[*]             cookbook/looks.yaml + special_rooms.yaml
  .description (already exists)           .dressing[] + .register + .telegraph
  .entities[] (NEW typed manifest)      ↓
       ↓                                game/cookbook/assemble.py (extended)
       ↓                                  compose_room_prose(seed, room_id) →
       ↓                                  (prose, entities[]) deterministic
       ↓                                ↓
       ↓                                rooms/<room_id>.yaml  (persisted at materialize)
       ↓                                  .description  (composed prose)
       ↓                                  .entities[]   (typed manifest)
       └─────────────────┬──────────────┘
                         ↓
                 Server consumption:
                   room_file_loader (settlements/caverns)
                   genre pack loader (cartography regions)
                         ↓
                Runtime: tools/resolve_location_entity(label, region_id, mode)
                   mode=narrator_proactive → manifest-miss = {resolved:false}, OTEL lie-detector
                   mode=player_initiated   → manifest-miss = mint yes_and entity, OTEL positive
                   → flavor_only entities auto-promote to yes_and on engagement
                         ↓
                Client: WebSocket LOCATION_DESCRIPTION + LOCATION_OVERLAY_CHANGED
                         ↓
                UI: LocationPanel.tsx (new tab, mirrors JournalView pattern)
                         ↓
                Action overrides (encounter-bound):
                   encounter.location_overlay = { entity_delta, prose_suffix }
                   merged at read time, never mutates base
```

The forest stays one forest. No new top-level entity competing with `regions[]` or with `rooms/<id>.yaml`. Cookbook pattern is the procedural seam (per `assemble_region` / `RegionContentManifest`); cartography is the POI seam. Both produce shapes the same loader path can consume.

## 4. Data Model

### 4.1 Manifest types

```python
# sidequest/protocol/models.py (or sidequest/genre/models/location.py — implementer's call)

class LocationEntity(BaseModel):
    model_config = {"extra": "forbid"}

    id: str                              # stable; world-unique within a region/room
    label: str                            # what the prose calls it ("the bar")
    tier: Literal["real_object", "yes_and", "flavor_only"]
    binding: LocationEntityBinding | None = None  # only when tier == real_object (initially)
    affordances: list[str] = Field(default_factory=list)  # v1: free-form interaction hints
    provenance: Literal[
        "authored",          # came from cartography.yaml or hand-authored room YAML
        "cookbook",          # composed by cookbook assembler at materialize time
        "yes_and_promoted",  # was authored flavor_only, runtime-promoted on engagement
        "yes_and_minted",    # minted on player input that named a non-manifest entity
    ] = "authored"
    promoted_at_turn: int | None = None
    promoted_canon: str | None = None    # what the player canonized on engagement


class LocationEntityBinding(BaseModel):
    model_config = {"extra": "forbid"}
    kind: Literal["location_feature", "npc", "item", "clue", "scenario_clue"]
    ref: str                              # id resolvable in the target subsystem


class EncounterLocationOverlay(BaseModel):
    """Per-encounter contribution merged at read time."""
    model_config = {"extra": "forbid"}
    bound_room_id: str
    entity_delta: list[LocationEntity] = Field(default_factory=list)
    prose_suffix: str = ""
```

### 4.2 Where it lives

| World class | File | Field |
|---|---|---|
| POI | `<world>/cartography.yaml` | `regions[*].entities[]` (replaces the untyped `landmarks[]` string array) |
| Procedural settlement | `<world>/rooms/<id>.yaml` | top-level `entities[]` alongside the existing `description` |
| Procedural cavern | `<world>/rooms/<id>.yaml` | top-level `description` + `entities[]` (both composed by cookbook assembler) |

### 4.3 Save persistence

Two persistence channels. **Authored YAML is never mutated by the server.**

- **POI:** authored manifest lives in YAML (read-only at runtime). Per-game promotions and mints accumulate in a `location_promotions` SQLite table keyed by `(save_id, region_id, entity_id)`. Read-time merge layers promotions on top of authored.
- **Procedural:** generated manifest is written to `rooms/<id>.yaml` at materialize time (consistent with ADR-106's materializer-emits-region pattern). yes_and promotions and player mints accumulate in the same `location_promotions` table. The materialized YAML is never rewritten by runtime engagement.

```sql
CREATE TABLE location_promotions (
    save_id TEXT NOT NULL,
    region_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    provenance TEXT NOT NULL,      -- 'yes_and_promoted' | 'yes_and_minted'
    label TEXT NOT NULL,           -- needed for minted entities (no authored row)
    promoted_at_turn INTEGER NOT NULL,
    promoted_canon TEXT NOT NULL,
    new_tier TEXT NOT NULL DEFAULT 'yes_and',
    new_binding_kind TEXT,
    new_binding_ref TEXT,
    PRIMARY KEY (save_id, region_id, entity_id)
);
```

Promotions are **durable** per the durable-retention principle. No GC. Storage cost is trivial; broken canon in old saves is not.

### 4.4 Action overrides

Encounters can contribute an overlay to the room they're bound to (`encounter.bound_room_id`). The overlay carries an `entity_delta` (added entities visible only while encounter active) and a `prose_suffix` (text appended below the base description). Base description and base manifest **never mutate** from overlays. Two encounters layered on the same room produce concatenated deltas and concatenated suffixes in encounter-arrival order (deterministic).

## 5. Runtime Contract

### 5.1 Validator (`pf validate locations`)

A new validator alongside the existing `pf validate {adr, agent, sprint, context, ...}` family. Three checks per genre pack, per world:

| Check | Behavior | Failure |
|---|---|---|
| **Manifest well-formedness** | Every `entities[*]` row parses as `LocationEntity`. No duplicate `id` within a region/room. No `binding` when `tier != real_object`. No empty `label`. | hard error |
| **Binding resolution** | For each entity with `binding.kind in {npc, item, clue, scenario_clue}`, the `ref` resolves in the target subsystem (`npcs.yaml`, item corpus, scenario clue graph, etc.). `location_feature` is free-form (no cross-file lookup, but `id` unique within region). | hard error |
| **Prose-manifest coherence** | Loader scans `description` prose for proper-noun-shaped tokens and definite-article phrases ("the X"). Each candidate must resolve to either (a) an entity in `entities[]` whose `label` matches, (b) an NPC name from `npcs.yaml` for the world, or (c) a per-pack `generic_allowlist[]` entry (the day, the weather, the village, …). Unresolved tokens emit warnings with line refs. | warning (non-blocking) |

Hard-error checks gate CI. Warning check is observable but never blocking. **The server's loader does not re-validate at runtime** — it trusts content that passed the validator.

Procedural-side: the validator runs against generated `<world>/rooms/<id>.yaml` as a post-hoc check after materialization, not a precondition. Cookbook fragments are validated up-front (every dressing line parseable, every `LookDef` has a `register`, etc.).

### 5.2 Loader wiring

| Loader | Change |
|---|---|
| `genre/loader.py` (cartography parser) | Parse `regions[*].entities[]` into `list[LocationEntity]` on the existing region model. |
| `room_file_loader.py` | After existing settlement/cavern parsing, parse top-level `entities[]` and surface on `TacticalGridPayload` (new field `entities: list[LocationEntity]`) and on settlement payloads. |
| `cookbook/assemble.py` | Extend `RegionContentManifest` with `room_descriptions: list[GeneratedRoomDescription]`. New function `compose_room_prose(rng, look_def, special_rooms, room_id)` → `(prose: str, entities: list[LocationEntity])`. Dressing lines selected for the room become `flavor_only` entities; `SpecialRoom.telegraph` references become `real_object` entities with `binding.kind = location_feature` and affordances seeded from `SpecialRoom.mechanic`. Deterministic seeded RNG `(campaign_seed, expansion_id, room_id)` — same seed → same prose, same manifest. |
| `dungeon/materializer.py` | After Epic 52's mask emit, call `compose_room_prose()` for each materialized room and persist into `<world>/rooms/<id>.yaml` alongside the mask. **Single materializer rewrite** — Approach C's stitch story. |

### 5.3 Resolver tool — `resolve_location_entity`

A new agent tool (`sidequest/agents/tools/resolve_location_entity.py`). Signature:

```python
def resolve_location_entity(
    label: str,
    region_id: str,
    mode: Literal["narrator_proactive", "player_initiated"],
    *,
    engagement_kind: Literal["mention", "mechanical"] = "mention",
) -> LocationEntityResolution:
    # 1. Build the effective manifest: authored + active overlays + promotion rows.
    # 2. Match `label` against entity.label (case-insensitive, definite-article stripped).
    # 3. Branch on mode:
    #    - narrator_proactive + miss → {resolved: false}. OTEL lie-detector span.
    #    - player_initiated + miss   → mint new yes_and entity, write to promotions table,
    #                                  fire location.entity.minted span, return resolved.
    # 4. If resolved entity is flavor_only and engagement_kind == "mechanical",
    #    fire flavor_only → yes_and promotion path, fire location.entity.promoted span,
    #    return resolved with new tier.
```

**The narrator is not required to call this tool for every prose mention.** Pure narration (descriptive text without mechanical commitment) does not require resolver calls. The tool is called when the narrator is about to mechanically engage an entity (emit damage, move it, claim its content) or when the player's input has been parsed to mention an entity. The OTEL `resolve` span is the lie detector that catches the narrator-proactive case where prose claims something the manifest can't back.

The two modes encode the Zork-Problem-safe split:

- **`narrator_proactive`**: the narrator is the source of the entity name. Manifest miss = contract violation. The narrator's pending mechanical action does NOT commit. (Protects the contract.)
- **`player_initiated`**: the player is the source. Manifest miss = canonization. A new `yes_and` entity is minted with `provenance="yes_and_minted"`. (Honors Yes-And and the Zork doctrine.)

### 5.4 Tier mutation paths

Two write paths into `location_promotions`, both producing `yes_and`-tier entities:

| Path | Trigger | Provenance |
|---|---|---|
| flavor_only → yes_and promotion | Authored `flavor_only` entity engaged mechanically | `yes_and_promoted` |
| Player-initiated mint | Player input names an entity not in the manifest | `yes_and_minted` |

In both cases, OTEL fires (`location.entity.promoted` for the first, `location.entity.minted` for the second), the row is durable, subsequent reads of the manifest see the new entity at `yes_and` tier with the player's canon attached.

### 5.5 Action-override merge (read-time)

```python
def get_location_manifest(region_id: str) -> list[LocationEntity]:
    return (
        authored_entities(region_id)
        + concat(o.entity_delta for o in active_overlays(region_id))  # encounter arrival order
        + promotion_layer(save_id, region_id)                          # merged by entity_id
    )

def get_location_prose(region_id: str) -> str:
    base = authored_description(region_id)
    suffixes = [o.prose_suffix for o in active_overlays(region_id) if o.prose_suffix]
    return base if not suffixes else base + "\n\n" + "\n\n".join(suffixes)
```

Encounter activate/deactivate emits `LOCATION_OVERLAY_CHANGED` WebSocket events so the UI re-renders without polling. Watcher events `location.overlay.activate` / `location.overlay.deactivate` fire alongside.

### 5.6 OTEL spans

| Span | Trigger | Key attributes |
|---|---|---|
| `location.entity.resolve` | Every resolver call | `region_id`, `label`, `mode`, `engagement_kind`, `resolved`, `tier`, `binding.kind`, `from_overlay`, `from_promotion` |
| `location.entity.minted` | Player-initiated mint of new entity | `region_id`, `entity_id` (newly assigned), `label`, `canon`, `turn` |
| `location.entity.promoted` | flavor_only → yes_and promotion of authored entity | `region_id`, `entity_id`, `from_tier`, `to_tier`, `canon`, `turn` |
| `location.overlay.activate` / `deactivate` | Encounter overlay state change | `region_id`, `encounter_id`, `delta_count`, `suffix_chars` |

GM panel surfaces:

- `location.entity.resolve { mode=narrator_proactive, resolved=false }` → **yellow warning** ("narrator referenced an unmanaged entity"). This is the lie detector.
- `location.entity.resolve { mode=player_initiated, resolved=false }` → **blue positive** ("player canonized an entity") — paired with `location.entity.minted`.
- `location.entity.promoted` → blue positive ("player engaged with described detail").
- Overlay events → muted info, useful for debugging encounter scoping.

### 5.7 Failure modes

| Scenario | Behavior |
|---|---|
| Validator hard-error in CI | Block release. Author fixes binding ref or removes prose mention. |
| Validator warning at runtime | Watcher event fires; play continues; GM panel surfaces drift count per session. |
| Resolver called `narrator_proactive` + manifest miss | Returns `{resolved: false}`. Span fires `resolved=false`. Narrator's mechanical action returns `not_found` and the turn unwinds without committing the mechanical effect. **No silent fallback.** |
| Resolver called `player_initiated` + manifest miss | Mints a new entity. Span fires `entity.minted`. The narrator's response is grounded against the new entity. The player's action proceeds. |
| Promotion / mint write to `location_promotions` fails (DB lock, IO error) | Hard error. The turn aborts before narrator response is broadcast. We do NOT broadcast a canonized-but-unpersisted entity — players would see a real interaction whose mechanical effect doesn't survive reload. |
| Encounter deactivates mid-merge | Reads use a snapshot — activation/deactivation acquires the same write lock as the resolver. Standard sequential-per-session pattern (existing Registry `_write_locks` map). |
| Cookbook assembler emits an entity whose binding ref doesn't resolve | Validator catches at post-materialize check; if missed at runtime, resolver returns `{resolved: false}` (narrator_proactive) and GM panel surfaces the warning. |

## 6. UI — `LocationPanel.tsx`

### 6.1 Component shape

A new component peer to `JournalView.tsx` / `KnowledgeJournal.tsx` / `InventoryPanel.tsx`. Reuses the existing provider stack and `useStateMirror` (ADR-026) consumption. No new context provider.

| Element | Treatment |
|---|---|
| **Tab nav placement** | UX-designer decision at implementation. Recommend "between Map and Journal" — geographically adjacent to Map, narratively adjacent to Journal. Tab visible only when `state.currentLocation` is non-null (graceful absence on legacy saves with no manifest yet). |
| **Header** | Region/room display name + secondary-weight terrain badge (`building`, `cavern`, `settlement`). |
| **Base prose block** | The `description` field, rendered as paragraphs. Existing typography tokens (per ADR-079 genre theme system). |
| **Overlay prose block** | Encounter `prose_suffix(es)` below the base with subtle separator. Visually distinct from base ("right now" vs "always true"). |
| **Entity manifest UI** | **NOT rendered in v1.** Surfacing the manifest as clickable verbs is a Zork violation. Manifest is server-side contract data only. |
| **Overlay indicator** | Small "Overlay active" pip when one or more encounter overlays merged. Tooltip names contributing encounters. |
| **Empty / loading** | Standard skeleton-loader; never a placeholder string. Graceful absence per `sidequest-ui/CLAUDE.md`. |

### 6.2 WebSocket plumbing

| Message | Direction | Trigger | Payload |
|---|---|---|---|
| `LOCATION_DESCRIPTION` | server → client | `current_room` change, session resume | `{region_id, prose, terrain, overlays: []}` (snapshot) |
| `LOCATION_OVERLAY_CHANGED` | server → client | Encounter activate/deactivate touching a `bound_room_id` | `{region_id, overlays: [{encounter_id, prose_suffix, entity_delta_count}]}` (delta) |

Both payloads typed in `sidequest-ui/src/types/payloads.ts` as additions. State mirror exposes `state.currentLocation: LocationDescription | null`.

### 6.3 Failure modes

| Scenario | Behavior |
|---|---|
| Server emits `LOCATION_DESCRIPTION` for a region the client has never seen | UI accepts and renders. Server is authoritative. |
| Server emits `LOCATION_OVERLAY_CHANGED` before baseline | UI buffers the delta until baseline arrives, then merges. Standard `useStateMirror` pattern. |
| Overlay's `prose_suffix` is empty but `entity_delta` is non-empty | UI shows the "Overlay active" pip but no extra prose. Manifest changes are server-only in v1, so this manifests purely as a pip + tooltip. |
| Save has promotion rows but authored manifest was edited offline | Server merges what it can; entity_id collisions resolve as "promotion wins" (durable-retention). |

## 7. Rollout — Approach C (Sibling Epics + Late-Merging Stitch)

### 7.1 Epic 52 — unchanged

`Wire Procedural Megadungeon Output to the ADR-096 Cavern Renderer Pipeline`. Existing scope. 5 stories. **Ships without absorbing description work.** This is the deliberate Approach-C tradeoff — Epic 52's visible-megadungeon payoff ships cleanly.

### 7.2 Epic 54 — new

`Persistent Location Descriptions (Mechanical Manifest)`. POI-side and infrastructure. Ships fully without touching `dungeon/materializer.py`.

| ID | Title | Pts | Repo | Workflow |
|---|---|-----|------|----------|
| 54-1 | ADR: Persistent Location Descriptions + Mechanical Manifest (doctrine, manifest type spec, validator surface, OTEL contract, two-mode resolver) | 1 | orchestrator | trivial |
| 54-2 | Server schema: `LocationEntity` + `LocationEntityBinding` types; extend cartography region schema and `<world>/rooms/<id>.yaml` schema; loader wiring through `TacticalGridPayload` and region payload; **new `LOCATION_DESCRIPTION` WebSocket message + server-side emit on `current_room` change and session resume** | 4 | server | tdd |
| 54-3 | New `pf validate locations` validator — well-formedness + binding resolution (hard) + prose-manifest coherence (warning); CI integration; per-pack/per-world reporting | 3 | orchestrator + server | tdd |
| 54-4 | Content backfill: `tea_and_murder/glenross` — convert 12 region `landmarks[]` to typed `entities[]`, add bindings to existing NPCs/clues, validator-clean | 2 | content | trivial |
| 54-5 | Content backfill: `caverns_and_claudes/beneath_sunden` settlement rooms — add `entities[]` to existing descriptions, validator-clean | 2 | content | trivial |
| 54-6 | Runtime: `resolve_location_entity` tool with both modes (`narrator_proactive` + `player_initiated`); `location_promotions` SQLite table + migration; flavor_only→yes_and promotion handler; player-initiated mint path; tool dispatch wiring | 3 | server | tdd |
| 54-7 | Action overlays: `EncounterLocationOverlay` model + read-time merge in `get_location_manifest` / `get_location_prose` + WebSocket `LOCATION_OVERLAY_CHANGED` emit on encounter activate/deactivate | 3 | server | tdd |
| 54-8 | OTEL: `location.entity.resolve` (both modes) + `location.entity.minted` + `location.entity.promoted` + `location.overlay.{activate,deactivate}` spans; GM-panel surfacing distinguishing narrator-lie vs player-canon | 2 | server + ui | tdd |
| 54-9 | UI: `LocationPanel.tsx` + tab registration + state-mirror integration + WebSocket payload types; base prose + overlay suffixes; "Overlay active" pip; mirrors `JournalView` pattern | 3 | ui | tdd |

Estimate total: ~22 pts (kanban — complexity signal, not capacity).

### 7.3 Epic 55 — stitch

`Procedural Cavern Description+Manifest Emit at Materialize Time`. Depends on both Epic 52 and Epic 54.

| ID | Title | Pts | Repo | Depends on | Workflow |
|---|---|-----|------|------------|----------|
| 55-1 | Cookbook extension: `compose_room_prose(rng, look_def, special_rooms, room_id)` → `(prose, entities[])`; `RegionContentManifest` gains `room_descriptions[]`; deterministic seeded from `(campaign_seed, expansion_id, room_id)`. Materializer calls it after Epic 52's mask emit and persists into `<world>/rooms/<id>.yaml`. Validator post-check on emitted rooms. | 5 | server | 52-2, 52-3, **54-2, 54-3** | tdd |

**Single materializer rewrite, scheduled after both upstream chains settle.** No double-pass on `dungeon/materializer.py`.

### 7.4 Suggested rollout order

```
Epic 52  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓     (parallel)
Epic 54  54-1 → 54-2 ─┬─ 54-3 ─┬─ 54-4 ─┬── 54-6 ──┬──┻─→ 55-1
                       │         │       │
                       │         │       └─ 54-5 ──┤
                       │         │                  │
                       │         └─ 54-7 ──────────┤
                       │                            │
                       └─ 54-9 (waits on 54-2)─────┤
                                                    │
                            54-8 (waits on 54-7)───┘
```

54-1 first (doctrine ADR). 54-2 unblocks the entire chain. 54-3 (validator) gates content backfills but parallelizable with runtime work. 54-4 and 54-5 are author-time, pickable in any order once 54-3 lands. 54-9 (UI) blocks only on schema (54-2). 54-8 (OTEL) waits on overlays (54-7) for full attribute coverage. 55-1 fires last, after both upstreams.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Prose-manifest coherence validator's proper-noun scan produces too many false positives (e.g. "Tuesday", "Highland") | Per-pack `generic_allowlist[]` in pack config; warn only when un-allowlisted *and* un-resolved. |
| Cookbook assembler's deterministic prose feels too repetitive across rooms with the same look | Cookbook dressing pool size matters. Author 8-12 dressing lines per look minimum; assembler samples 2-3 per room with `(seed, room_id)`-derived ordering. |
| `location_promotions` table grows without bound across long campaigns | Promotions are durable per Keith's durable-retention principle — do not GC. Storage cost trivial; broken canon in old saves is not. |
| Encounter overlay accidentally references a base-manifest entity id that doesn't exist | Validator's binding-resolution check extends to overlay `entity_delta[]` at encounter-bind time; runtime resolver returns `{resolved: false}` in narrator_proactive mode otherwise. |
| Narrator improvises a new entity not in the manifest in proactive mode | `location.entity.resolve { mode=narrator_proactive, resolved=false }` span fires; GM panel surfaces drift; over multiple sessions the warning count drives prose-revision work. Not a hard fail by design — soft handling so the table doesn't see an error mid-scene. |
| Player input parsing fails to detect a noun phrase that should trigger player_initiated mode | The narrator's pipeline determines mode based on input parsing. If a player names an entity that the narrator doesn't notice and the narrator then mechanically claims it without a resolver call, the contract is silently violated. **Mitigation**: every narrator-side mechanical claim against an entity (move, damage, take, etc.) must route through the resolver — there is no "claim without resolve" code path. Implementer enforces this in the agent tool harness. |

## 9. Open Questions (deferred)

1. **Player-canonization grammar.** When narrator promotes/mints, what exactly is `promoted_canon`? Free-form text capture from narrator response, or structured player-claim? Suggest free-form text v1 (matches KnownFacts pattern); structured later if drift observed.
2. **Per-PC perception filtering** of the manifest (ADR-104 / ADR-105). Some entities should be invisible to some PCs (charmed character doesn't see the hidden door). v1 assumes all entities universally visible to all seated players. Add a `visibility` field with per-PC perception in a follow-up.
3. **Voice/aside hooks.** Once entities are mechanically grounded, certain entities could carry a "voice line" attribute (e.g. examining the bell triggers a one-line aside). Not v1.
4. **Player-canonized entity edit/retract.** v1 promotions are append-only. If a player canonizes "the bookcase is full of cookbooks" and a later turn establishes "the bookcase was always empty," there is no edit mechanism. Acceptable v1; revisit if observed in playtest.

## 10. Reuse Summary

| Existing infrastructure | How it's extended |
|---|---|
| `cartography.yaml regions[*]` schema | Replace untyped `landmarks[]` with typed `entities[]`. |
| `cookbook/{looks,special_rooms}.yaml` | Source of dressing/telegraph fragments — no schema change. |
| `cookbook/assemble.py` | Add `compose_room_prose()` function; `RegionContentManifest` gains `room_descriptions[]`. |
| `<world>/rooms/<id>.yaml` (per ADR-096) | Add top-level `entities[]` alongside existing `description`. |
| `room_file_loader.py` | Read `entities[]`, surface through `TacticalGridPayload`. |
| `pf validate` family | New validator: `pf validate locations`. |
| ADR-100 KnownFacts | Untouched — KnownFacts may bind by `entity.id` but lifecycles are independent (KnownFacts is per-PC evidential; manifest is per-region structural). |
| ADR-026 client state mirror | New `state.currentLocation` slice; same provider pattern. |
| Existing UI panels (`JournalView`, `KnowledgeJournal`, `InventoryPanel`) | Pattern for `LocationPanel`. |
| Existing OTEL span infrastructure (`telemetry/spans/`) | New `telemetry/spans/location.py` module. |
| GM panel | Surfaces new spans with the same lie-detector / positive-event color discipline. |

**No new top-level entity, no new context provider, no new state slice paradigm.** The design extends what's there.

---

## Doctrine quotes (load-bearing)

- **Zork Problem** (CLAUDE.md): "never let the interface imply a closed set of options when the set is open." → Manifest is **producer-side** contract, never **consumer-side** gate. Two-mode resolver enforces this split.
- **Yes, And** (SOUL.md): "When a player introduces something into the world — a location, an object, a backstory detail — say yes." → `player_initiated` mode mints `yes_and_minted` entities on the fly.
- **Diamonds and Coal** (SOUL.md): "Match narrative detail to narrative weight. Coal can become a diamond when the players choose to polish it." → flavor_only → yes_and promotion path is the canonization mechanism.
- **OTEL Observability Principle** (CLAUDE.md): "Every backend fix that touches a subsystem MUST add OTEL watcher events." → location resolver, mints, promotions, overlays are all observable; GM panel distinguishes narrator-lie from player-canon.
- **Durable Retention** (project memory): "Never reap save-referenced artifacts on a timer." → `location_promotions` table has no GC.
- **No Silent Fallbacks** (CLAUDE.md): narrator_proactive manifest miss does NOT silently improvise — the turn unwinds.
