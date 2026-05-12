---
id: 99
title: "Coyote Object Salvage Hooks — Two-Phase Auto-Fire for the_salvage"
status: accepted
status_rationale: "Design-phase story 47-8. Extends the auto-fire taxonomy beyond bar-trigger (47-3) and room-entry (47-4) with an object-based trigger. Implementation phase is downstream."
date: 2026-05-12
deciders: ["Keith Avery"]
supersedes: []
superseded-by: null
related: [14, 33, 37, 93]
tags: [genre-mechanics]
implementation-status: deferred
implementation-pointer: null
---

# ADR-099: Coyote Object Salvage Hooks — Two-Phase Auto-Fire for the_salvage

## Status

Accepted (2026-05-12). Implementation deferred to a downstream 47-x story.

## Context

`the_salvage` shipped in story 47-3 with `auto_fire: false` — the narrator decides
when to invoke. In Coyote Star, salvaged alien artifacts ("Coyote Objects") are a
load-bearing texture: the thing you pulled from the wreck has its own opinion
about being pulled. Leaving the firing decision to the narrator means the
confrontation only triggers when the LLM remembers to invoke it. The OTEL panel
already shows the cost of this drift across other systems — Claude is excellent at
"winging it" past mechanical scaffolding.

The auto-fire taxonomy currently has two trigger shapes:

- **Bar-DSL trigger** (47-3) — `auto_fire_trigger: "sanity <= 0.40"`. Evaluated by
  `evaluate_auto_fire_triggers` against character bar values. Used by
  `the_bleeding_through` and `the_quiet_word`.
- **Room-entry trigger** (47-4) — `fire_conditions: {interior_room_present, bond_tier_min,
  cooldown_turns}`. Evaluated by `find_eligible_room_autofire` against player
  room-entry on a specific chassis. Used by `the_tea_brew`.

Neither shape fits salvage. A Coyote Object trigger is keyed on the *object* —
its presence in a room, its movement into an inventory, its identity as a
narrator-tagged alien artifact rather than ordinary loot. Without an
object-based trigger, the_salvage stays narrator-discretionary and Sebastien has
no GM-panel evidence the system is engaged when a derelict hopper drops loot.

The salvage interaction has two distinct mechanical moments:

- **Discovery** — the player becomes aware a Coyote Object is present. The
  artifact is not in their inventory; the room (or its contents) surfaces it. In
  fiction: the panel under the captain's hand starts humming; a gun on the dead
  smuggler's hip has a name etched into the slide.
- **Acquisition** — the player commits an action that takes the object. In
  fiction: hand closes on the gun; data-clip pulled from the alien console.

The two moments carry different consequences. Discovery costs nothing
mechanically but earns a beat of dread / promise (narrative "bait"). Acquisition
is when the artifact's agency engages — the bond ledger begins, OCEAN
disposition surfaces, and `the_salvage` becomes mechanically active.

## Decision

Introduce a third auto-fire shape: the **salvage-hook trigger**, keyed on
object class and lifecycle phase. Both phases share one confrontation
(`the_salvage`); they differ in *when* the firing pipeline evaluates and what
pre-confrontation work runs.

### YAML surface

The existing `the_salvage` definition gains `auto_fire: true` and a new
`salvage_conditions` block alongside `fire_conditions`:

```yaml
- id: the_salvage
  label: "The Salvage"
  plugin_tie_ins: [item_legacy_v1, innate_v1]
  auto_fire: true
  salvage_conditions:
    object_class: coyote_object        # which items qualify
    fire_phase: acquisition             # which lifecycle phase fires the conf
    discovery_emits_beat: true          # discovery emits a narration beat, no confrontation
    cooldown_turns: 0                   # reserved — not evaluated in v1; once-per-object invariant is enforced by resolved_salvage_objects / observed_salvage_objects sets, not this counter
  rounds: 2
  resource_pool: { primary: sanity, secondary: bond }
  outcomes: { ...unchanged... }
```

Items in inventory YAML (or runtime-tagged via narrator output) carry the
`coyote_object: true` flag plus an optional `salvage_phase_default` (defaults to
`acquisition`). The flag is set at item definition time for known artifacts
(named guns from `item_legacy_v1.yaml`) and may be set by narrator output when a
generic salvage item turns out to be alien-resonant.

A new `SalvageConditions` Pydantic model in `magic/confrontations.py` mirrors
`FireConditions` (extra=forbid, required fields validated at load). One model,
optional on the definition; absence preserves the existing
narrator-discretionary path.

### Hook sites

Two evaluators are added, each emitting one OTEL span:

1. **Discovery hook** — `evaluate_salvage_discovery(*, confrontations, actor_id,
   visible_object_ids, observed_salvage_objects) -> list[SalvageDiscovery]`.
   (Where `visible_object_ids` is the set of item IDs currently surfaced for the
   actor in the room — items physically present plus items the actor's
   perception-filter exposes per ADR-028. `observed_salvage_objects` is the
   actor's per-player MagicState set as defined in §Consequences.)
   Called from the room-entry / room-snapshot pipeline (same site as
   `find_eligible_room_autofire`). Returns the set of new Coyote Objects this
   actor has not yet observed in this room context. For each new observation,
   the pipeline emits a narration beat (a baited hook, ADR-014 SOUL) and
   records the object_id in the actor's `observed_salvage_objects` set on the
   per-player state slice (ADR-037 per-player scope). No confrontation fires.

2. **Acquisition hook** — `evaluate_salvage_acquisition(*, confrontations,
   actor_id, acquired_object_id, object_tags) -> ConfrontationDefinition |
   None`. Called from `narration_apply` after the inventory mutation pipeline
   (`items_gained processing in narration_apply.py`) materializes a new item into an actor's
   inventory. When the acquired item carries `coyote_object: true` and the
   actor has not yet resolved `the_salvage` against this object_id, dispatch
   the confrontation through the existing `dispatch/confrontation.py` flow.

Discovery is intentionally light: it emits a *promise*, not a confrontation.
This preserves the Diamonds and Coal rhythm — discovery is the bait, acquisition
is the bite. The narrator is free to leave the bait in the water if the player
doesn't reach for it (ADR-014 "untaken bait" doctrine).

### Pool binding and outcomes

Pool binding stays as defined: `primary: sanity, secondary: bond`. Mandatory
outputs per branch were already authored in 47-3 (`item_acquired`,
`item_history_increment`, `sanity_decrement`, `status_add_scratch`,
`status_add_wound`, `item_acquired_with_low_bond`, `sanity_increment`). No
output catalog changes.

`item_acquired` is the canonical advancement output for acquisition. When the
confrontation outcome is `clear_win` or `pyrrhic_win` and the item is not yet
in the actor's inventory (i.e. the acquisition fired pre-inventory-application),
the output materializes the item. When the firing site is post-inventory (as
specified above), `item_acquired` is idempotent — confirms the item is bound
to the actor and records `acquisition_resolved: true` on the item's
per-character state slice.

### OTEL spans

Two new spans register with `SPAN_ROUTES` under `event_type=state_transition,
component=magic`:

- **`magic.salvage_discovery`** — emitted on every discovery-hook evaluation
  for the actor (including evaluations where the hook skips). The
  triggered/skip semantics live on the span attributes, not on whether the
  span is emitted, so the GM panel can distinguish "evaluator ran and
  correctly skipped" from "evaluator never ran." Attributes: `actor_id`,
  `object_id`, `object_class`, `room_local_id`, `triggered: bool`,
  `skip_reason: "already_observed" | "wrong_class" | null`,
  `narration_beat_id: str` (the `LoreFragment.id` of the LoreFragment minted
  for the beat — null when `triggered: false`).

- **`magic.salvage_acquisition`** — emitted on every inventory-mutation event
  where the evaluator runs. The evaluator is called for every acquired item
  carrying `coyote_object: true`; mundane items short-circuit before the
  evaluator (no span). Within the evaluator the span emits with attributes:
  `actor_id`, `object_id`, `confrontation_id`, `fired: bool`,
  `skip_reason: "already_resolved" | "wrong_phase" | null`, plus the standard
  confrontation context (`pool_primary`, `pool_secondary`, `rounds`) when
  `fired: true`. (Items that reach acquisition without the `coyote_object`
  flag set is a *loader bug* — the load-time validator should have rejected
  the item definition or the runtime tagger should have set the flag before
  the inventory mutation — and therefore is not a runtime skip_reason. See
  Implementation Notes.)

Together these spans make Sebastien's GM panel a true lie detector for
salvage: if a Coyote Object appears in the inventory and no
`magic.salvage_acquisition` span fired, the system is broken or the narrator
forged the inventory mutation outside the pipeline.

### Multi-player projection (ADR-037)

Salvage is *per-actor*, not shared-world. ADR-037's split:

- **Discovery** — per-player. Each player sees the bait only when *they* enter
  the room with sufficient context. Observed-objects-by-actor is a per-player
  state slice. A second player entering the same room later gets their own
  discovery beat (different bait register if their character's lineage /
  classifications differ — out of scope for this ADR, deferred to the
  Perception Rewriter ADR-028 surface).

- **Acquisition** — per-actor. Only the player whose action acquired the item
  drives the confrontation. Other players are *aware* the actor is engaging
  with the artifact (the narration is shared), but the confrontation's
  resource pool deltas land on the acquirer's ledger only.

The item itself, once acquired, is single-owner per genre rules. World-shared
ledgers (`hegemony_heat`) may be incremented by salvage outcomes via the
existing `mandatory_outputs` flow — that propagation is unchanged from 47-3.

### Cooldown and arc semantics

`cooldown_turns: 0` is the default and the recommended setting for v1. Each
Coyote Object resolves `the_salvage` *once* per actor per object_id — tracked
in the per-player `resolved_salvage_objects` set. Repeat firings against the
same object_id never occur. The `cooldown_turns` field is reserved for future
worlds where a long-running artifact might re-resolve under different
circumstances (Heavy Metal pact items, for example); v1 leaves it unused.

`once_per_arc: false` for the_salvage. Multiple Coyote Objects can resolve
within the same arc; the per-object_id tracking handles the "no double-fire"
invariant.

## Consequences

- **New shape, small footprint.** `SalvageConditions` is ~30 LOC; two
  evaluators ~80 LOC combined; two SPAN_ROUTES entries; one per-player state
  slice (`observed_salvage_objects: set[str]`, `resolved_salvage_objects:
  set[str]`). The discovery/acquisition pipeline taps existing hook sites
  (room-entry observer, `items_gained processing in narration_apply.py`) — no new dispatch flow.

- **`auto_fire: true` is no longer one-or-the-other.** The_salvage will have
  `auto_fire: true` AND no `auto_fire_trigger`. The auto-fire selection
  becomes: (a) bar-DSL trigger if `auto_fire_trigger` is set; (b)
  room-entry trigger if `fire_conditions` is set; (c) salvage trigger if
  `salvage_conditions` is set. A confrontation with `auto_fire: true` MUST set
  exactly one of these three condition blocks; validator enforces.

- **Item-tag schema extension.** Item YAML gains `coyote_object: bool` and
  `salvage_phase_default: Literal["discovery", "acquisition"]`. Loader-side
  validation; missing flag defaults to `false` (not a Coyote Object).

- **OTEL coverage.** `magic.salvage_discovery` and `magic.salvage_acquisition`
  spans give Sebastien's GM panel two new event types. The "Claude wrote
  evocative salvage prose but no span fired" failure mode becomes
  diagnosable rather than invisible.

- **Narrator prompt context.** The narrator's pre-prompt magic context block
  (per 47-3) gains a `coyote_objects_in_room` list when relevant — the
  narrator knows which artifacts in the current scene carry agency and can
  shape prose accordingly. No new prompt section; this rides the existing
  `magic_context` block.

- **Saves.** Per-player state slices (`observed_salvage_objects`,
  `resolved_salvage_objects`) persist with the existing per-player
  `MagicState`. Legacy saves init these as empty sets — first room-entry after
  a load re-emits discovery beats for any in-room Coyote Objects, which is
  the desired behavior (the player needs to remember the bait existed).

- **Item Legacy plugin integration.** Item Legacy items already exist in the
  schema (47-3). The Coyote Object flag is additive — most Item Legacy items
  are Coyote Objects in Coyote Star, but the flag is the authoritative gate
  (some named McCoy items might be flagged off if they're meant to skip the
  confrontation; future-world authoring affordance).

## Alternatives Considered

### A1: Single-phase trigger on acquisition only

Rejected. Removes discovery beats; loses the bait/bite rhythm; Coyote Objects
become invisible until taken. Discovery is cheap (one OTEL span, one narration
beat, one set membership check) and load-bearing for Sebastien's "I want to
see the artifact coming" pacing.

### A2: Two separate confrontations (`the_discovery`, `the_acquisition`)

Rejected. Splits one mechanical moment into two confrontation overlays in the
UI. The salvage interaction is *one* dramatic event; the discovery is its
opening beat, not its own confrontation. Authoring overhead (two YAML
definitions, doubled output catalog) costs more than `salvage_conditions`
costs.

### A3: Extend `FireConditions` with object_class / fire_phase

Rejected. `FireConditions` is room+bond+cooldown — a coherent shape for
room-entry chassis-bonded auto-fire. Object-class triggers are a different
domain (item identity, not room presence). Overloading `FireConditions` would
muddle the model. Two narrow models read cleaner than one mega-model.

### A4: Narrator emits an explicit `salvage_working` block, server fires conf

Rejected. Trusts the narrator to remember. The whole point of auto-fire is to
remove the narrator-discretionary failure mode. Sebastien's lie detector
shouldn't depend on the lie-detected system to self-report.

## Implementation Notes (for the downstream story)

- New model: `SalvageConditions` in `sidequest-server/sidequest/magic/confrontations.py`.
- New evaluators: `evaluate_salvage_discovery`, `evaluate_salvage_acquisition`
  alongside `evaluate_auto_fire_triggers` and `find_eligible_room_autofire`.
- Per-player state slice extensions: `observed_salvage_objects`,
  `resolved_salvage_objects` on the `MagicState` per-player slice.
- SPAN_ROUTES: `magic.salvage_discovery`, `magic.salvage_acquisition` under
  `event_type=state_transition, component=magic`.
- Item schema extension: `coyote_object: bool`, `salvage_phase_default` in the
  item loader.
- Validator rule: `auto_fire: true` requires exactly one of
  `auto_fire_trigger | fire_conditions | salvage_conditions`. Failure raises
  `ConfrontationLoaderError` (no silent fallback).
- Scenario seed: `scenarios/coyote_salvage_smoke.yaml` (authored under this
  story — see References).
- Wiring tests: at least one integration test confirms the
  `items_gained processing in narration_apply.py` → `evaluate_salvage_acquisition` →
  `dispatch_confrontation` chain runs end-to-end against a Coyote Star
  fixture.

## References

- ADR-014 — Diamonds and Coal (bait / bite doctrine)
- ADR-033 — Confrontation Engine (the dispatch flow this rides on)
- ADR-037 — Shared-World / Per-Player State Split (multi-player projection)
- ADR-058 — Claude Subprocess OTEL Passthrough (span emission machinery)
- ADR-090 — OTEL Dashboard Restoration (where the new spans surface)
- ADR-093 — Confrontation Difficulty Calibration (pool sizing context)
- Story 47-3 (shipped) — five named confrontations including `the_salvage`
- Story 47-4 (shipped) — `the_tea_brew` room-entry auto-fire + `FireConditions`
- Magic implementation design — `docs/superpowers/specs/2026-04-28-magic-system-coyote-reach-implementation-design.md`
- Coyote Star confrontations YAML — `sidequest-content/genre_packs/space_opera/worlds/coyote_star/confrontations.yaml`
- Scenario seed — `scenarios/coyote_salvage_smoke.yaml`
