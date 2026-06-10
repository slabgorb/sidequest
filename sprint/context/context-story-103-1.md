---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-1: Saint layer — saints.yaml schema + SaintRegistry + Saint-Marked chargen preset

## Business Context

The Saint layer is the epic's keystone: it implements the world's central conceit (iconographic mutation — drink a Saint's spring, receive that Saint's marks and drawback) as a **curation preset over the live AWN MP economy**, per the 2026-06-09 rebase addendum. Until this lands, no Saint content can be authored (103-4 is blocked on this schema freeze) and the Seaboard's signature chargen path doesn't exist. For the mechanics-first players (Sebastien, Jade), the Saint bundle must be *real crunch* — actual AWN mutations with actual MP math — not narrator flavor; the OTEL span is how the dev (Keith) proves it.

## Technical Guardrails

- **Extend `sidequest-server/sidequest/mutation/`** — the `SaintRegistry` loader joins the existing models/catalog modules there. Do NOT create a new top-level subsystem and do NOT route through the MagicPlugin/ADR-126 seam (AWN decision D5: mutations are a bespoke subsystem).
- **Reuse `MpEconomy`** (`sidequest/mutation/models.py`) — Saint-Marked application = the same MP pricing as Wild Mutant, with picks pre-bound by the bundle. Two presets, one engine. If you find yourself writing a second pricing path, stop.
- **Schema (build plan §D-A):** Saint = `{id, name, tradition: literary|catholic_immigrant|folk_place|wilderness_sleeper, patron_regions: [], bundle: [positive mutation IDs], drawback: exactly one negative ID, affinity: [] optional, iconography, veneration}`. IDs use the genre catalog namespace `category/snake_case`.
- **Loud validation (No Silent Fallbacks):** at world load, every `bundle`/`drawback`/`affinity` ID must resolve against `genre_packs/mutant_wasteland/mutations.yaml`. A miss is a load **error**, not a warning, not a skip.
- **World-tier only (ADR-140):** `saints.yaml` lives at `worlds/seaboard_of_saints/saints.yaml`. No genre-tier saints file. flickering_reach must load with zero Saint content and zero new requirements.
- **OTEL (D-D):** emit `awn.saint.applied` with saint id, bundle IDs, drawback ID, and the MP arithmetic. Follow the span conventions in `sidequest/telemetry/`.
- **Wiring test mandatory** (CLAUDE.md): at least one integration test proving the registry is loaded via the production world-load path and the chargen preset is reachable — not just unit tests on the loader.
- **Do not touch:** `ruleset/awn.py` combat math, the Wild-Mutant freeform path's behavior, flickering_reach content.

## Scope Boundaries

**In scope:**
- `saints.yaml` schema definition + `SaintRegistry` loader + load-time ID validation
- Saint-Marked chargen preset application through MpEconomy
- `awn.saint.applied` OTEL span
- **3 proof Saints** in a minimal `worlds/seaboard_of_saints/saints.yaml` (world dir may be created skeletal here): one bundle-only, one bundle+affinity, one whose drawback demonstrably fires in a confrontation
- Wiring + integration tests; flickering_reach load regression check

**Out of scope:**
- The full ~25-Saint canon (103-4)
- The stock chargen step / stocks.yaml (103-2) — this story's preset can ride the existing `mutation` chargen step
- Any world flavor content beyond the skeletal world.yaml needed to load (103-5)
- UI work beyond what the existing chargen flow already renders

## AC Context

1. **Schema + loader:** `SaintRegistry` parses `saints.yaml`; a malformed Saint (missing drawback, >1 drawback, unknown tradition) is a validation error with a precise message. Test: fixture YAMLs for each malformation.
2. **Loud ID validation:** a Saint referencing `structure/does_not_exist` fails world load with the offending saint id + mutation id in the error. Test: load attempt with bad fixture asserts the error surface, not a silent skip.
3. **Preset application:** creating a Saint-Marked character yields exactly the bundle's positives + the drawback negative on the sheet, with MP accounting consistent with MpEconomy (drawback counts as the negative that funds the bundle per AWN pricing). Test: chargen integration test asserting character state.
4. **Drawback is mechanically live:** in a confrontation, the proof Saint's drawback fires through the existing mutation-use machinery and is observable. Test: OTEL-asserted confrontation fixture (the lie-detector pattern from 102's AC5b work).
5. **Span:** `awn.saint.applied` emitted on application with saint id, bundle, drawback, MP math. Test: span capture assertion.
6. **Regression:** flickering_reach loads clean with no saints.yaml present — absence of the file is valid (a world without Saints), but a *present-and-broken* file is loud.

## Assumptions

- AWN Plan 2's mutation catalog and MpEconomy are stable surfaces (verified live 2026-06-10; 102-7 merged).
- The 3 proof Saints can be drawn from the world spec §6 roster (e.g. Saint Herman, Saint Edgar) with bundle IDs hand-mapped to existing catalog entries; if no clean analog exists for a proof Saint, pick a different proof Saint rather than adding genre mutations in this story (gap-filling is 103-4's job).
- The existing chargen `mutation` step has a seam to offer preset-vs-freeform; if it requires a new step instead, log a deviation and keep the step additive.
