---
story_id: "39-4"
jira_key: ""
epic: "39"
workflow: "wire-first"
---

# Story 39-4: BeatDef.edge_delta + target_edge_delta + beat dispatch wiring

## Story Details

- **ID:** 39-4
- **Jira Key:** (none — personal project)
- **Epic:** 39 — Edge / Composure Combat, Mechanical Advancement, and Push-Currency Rituals
- **Workflow:** wire-first (phased: setup → red → green → review → finish)
- **Points:** 8
- **Stack Parent:** none
- **Repos:** api (sidequest-api)

## Summary

Extend `BeatDef` with `edge_delta`/`target_edge_delta`/`resource_deltas` fields and implement self-debit and target-debit resolution blocks in `handle_applied_side_effects` (parallel to the existing gold_delta pattern at beat.rs:319-337). Auto-resolve combatants when Edge reaches 0 (composure break). Wire OTEL `creature.edge_delta` and `encounter.composure_break` events so the GM panel can trace composure state changes. Stub a hard-coded advancement grant (+2 max edge for Fighters) to serve as the smoke-test gate for the full advancement system being built in 39-5.

## Acceptance Criteria

1. **BeatDef schema extension** — `BeatDef` struct in `sidequest-protocol` or `sidequest-game` has three new fields:
   - `edge_delta: Option<i32>` — damage/healing applied to self
   - `target_edge_delta: Option<i32>` — damage/healing applied to target
   - `resource_deltas: Option<Vec<ResourceDelta>>` — push-currency costs (for 39-6 integration, may be empty for now)
   These are serialized/deserialized correctly in YAML and JSON round-tripping.

2. **Self-debit block in handle_applied_side_effects** — When a beat is applied and `beat.edge_delta.is_some()`, apply it to the acting creature's edge pool exactly like the gold_delta pattern:
   - Read current edge from creature.edge_pool
   - Apply delta (subtract damage, add healing with bounds-checking)
   - Mutate creature.edge_pool.current
   - Emit OTEL `creature.edge_delta` event with: `creature_id`, `delta_value`, `new_current`, `new_state` (e.g., "healthy"/"strained"/"broken")
   - No silent fallbacks: if the creature has no edge pool, fail loudly

3. **Target-debit block in handle_applied_side_effects** — When beat has `target_edge_delta`, apply the same debit logic to the target creature (if a target exists):
   - Apply delta to target.edge_pool.current
   - Emit OTEL `creature.edge_delta` event for target with same attributes
   - Handle no-target case gracefully (log as info-level OTEL event, not error)

4. **Composure break auto-resolution** — When any creature's edge reaches ≤0 after debit:
   - Mark creature as `composure_state: Broken` (or equivalent state enum)
   - Immediately resolve the creature as unable to act (out of combat, or mechanically neutral)
   - Emit OTEL `encounter.composure_break` event with: `creature_id`, `creature_name`, `edge_at_break` (the value that triggered it), `trigger_beat_id`
   - This is a hard stop to combat involvement, visible to the GM panel

5. **OTEL telemetry wiring** — Both `creature.edge_delta` and `encounter.composure_break` are emitted as structured `WatcherEvent`s (using existing `WatcherEventBuilder` pattern) so they appear on the GM panel and are queryable in playtest logs.

6. **Stub advancement grant (smoke test)** — Hard-code a single advancement grant for testing: when any Fighter with name containing "smoke" or matching a test fixture name gains an advancement, add `+2` to their `max_edge`. This is temporary scaffolding to validate the advancement-grant plumbing (CreatureCore mutation, beat dispatch round-trip, OTEL emission) before 39-5 builds the full system.
   - Call site: add this logic at the end of `handle_applied_side_effects` with a loud comment flagging it as temporary test code
   - Verify via OTEL: "advancement.effect_applied" event emitted with `effect_type: "EdgeMaxBonus"`, `magnitude: 2`

7. **Wiring verified end-to-end** — 
   - `BeatDef` fields have non-test consumers in beat dispatch code (grep shows imports in beat.rs, dispatch.rs, or relevant handler)
   - OTEL events are imported from telemetry crate and called in handle_applied_side_effects
   - Advancement grant logic is called during beat application (not deferred to later phase)
   - No stub exports with zero callers

## Key References

- **Story 39-2:** Deleted hp/max_hp from CreatureCore; edge_pool is now the canonical health tracker
- **Story 39-1:** Defined EdgePool type with current/max/recovery_triggers/thresholds
- **Gold delta pattern:** `sidequest-api/crates/sidequest-game/src/beat.rs:319-337` — reference implementation for self/target deltas
- **OTEL pattern:** `sidequest-telemetry/src/watcher.rs` — WatcherEvent emission and span attribute builders
- **ADR-078:** `/Users/keithavery/Projects/oq-1/docs/adr/ADR-078.md` — advancement architecture rationale
- **Content draft:** `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` — smoke test fixture names and advancement values

## Workflow Tracking

**Workflow:** wire-first (phased)
**Phase:** setup
**Phase Started:** 2026-04-19

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-19 | — | — |

## Delivery Findings

No upstream findings.

## Design Deviations

No design deviations at this stage.

---

**Branch:** `feat/39-4-beatdef-edge-delta-dispatch`
**Session Created:** 2026-04-19
**Next Agent:** tea (RED phase)
