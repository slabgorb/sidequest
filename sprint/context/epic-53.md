# Epic 53: Road Warrior — Rig two-pool wiring + content alignment

## Overview
Content-side rig overhaul landed in sidequest-content (rules.yaml edge_config, inventory.yaml vessel templates, classes.yaml signatures, npcs.yaml). Backend wiring needed: RigComposurePool extension to EdgePool model, materializer hooks for vessel item → rig pool, crash-event handler at Composure→0, OTEL spans per ADR-031. Also includes the slugify precedence fix in scripts/render_common.py.

## Affected Subsystems
- **EdgePool framework** — RigComposurePool extends vessel-attached mechanics (ADR-014, ADR-078)
- **Materializer** — Bind vessel items to character rig pools
- **Event handler** — Crash events fire at Composure→0
- **OTEL observability** — Track rig pool deltas and crash events per ADR-031
- **UI surfaces** — Show RigComposure + Edge + injury tags on CharacterSheet
- **Scripts** — slugify precedence (item.slug over slugify(name))

## Story Dependencies
1. **53-1** RigComposurePool: extend Edge framework for vessel-attached pools (foundation)
2. **53-2** Materializer: instantiate rig vessel item → bind RigComposurePool to character
3. **53-3** Crash event handler: Composure→0 fires injury tag + Edge hit + dismount
4. **53-4** OTEL spans: rig_pool delta + rig_crash_event per ADR-031
5. **53-5** UI: surface RigComposure + Edge + injury tags on CharacterSheet
6. **53-6** scripts/render_common.slugify prefers item.slug over slugify(name)

## References
- **ADR-014** Diamonds and Coal (Edge/Composure framework)
- **ADR-078** Edge / Composure Combat (vessel pools extension)
- **ADR-031** Game Watcher — Semantic Telemetry for AI Agent Observability
- Content pack: sidequest-content/genre_packs/{world}/rules.yaml, inventory.yaml, classes.yaml, npcs.yaml

## Implementation Notes
- RigComposurePool is modeled on EdgePool but bound to a vessel/rig item
- Composure→0 is a trigger event (not auto-resolved damage pool like injury)
- OTEL spans must emit on pool creation, delta, and zero-crossing
