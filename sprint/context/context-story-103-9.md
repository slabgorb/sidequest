---
parent: context-epic-103.md
workflow: tdd
---

# Story 103-9: Asset gate (art/music lane) — visual style, portraits, POIs, audio

## Business Context

The Seaboard stays `draft: true` until its asset gate is MET — the same gate every live world cleared (franchise_nations, annees_folles, evropi, long_foundry, aureate_span). This story produces the world's visual language (a literary-gonzo Northeast palette distinct from flickering_reach's), the Saint-icon and faction-NPC portraits, POI landscapes for all 17 regions, and the audio plan. It's what turns the world from text into the multi-sensory table experience ("Tabletop First, Then Better").

## Technical Guardrails

- **`visual_style.yaml`:** style/medium lives ONLY in the positive_suffix (Keith, emphatic — style in solos/appearances fights the suffix and flattens renders). Define the world's palette: granite-and-fog Down East, drowned-neon Sunken Bight, Borscht Belt pastel — one coherent suffix, regional variation through subject content.
- **`portrait_manifest.yaml`:** Saint icons (from 103-4's iconography fields) + faction leadership NPCs (103-7). Art-director lane conventions; no facial-scar defaults; diacritic-safe naming (the three-divergent-slug-rules trap — keep names ASCII-safe or verify slug keying).
- **POI landscapes:** all 17 regions per `/sq-poi` pipeline + ADR-086 composition taxonomy; landmark selection from 103-6's cartography.
- **Audio:** `audio.yaml` per ADR-095/ACE-Step conventions (music-director lane); shared-PD music via the `assets/audio/` prefix where classical PD fits (per the established shared-bucket pattern — never per-pack copies); region/scene cue mapping.
- **Render ops:** verify the running daemon reads THIS clone's `SIDEQUEST_GENRE_PACKS` before rendering (the oq-1-vs-oq-4 CatalogMiss trap); render/publish scripts run under the orchestrator root venv (`uv run --project .` for boto3/R2).
- **Gate definition:** portraits + POI landscapes rendered and published to R2, audio.yaml resolving — the same MET bar as the pack README's other worlds. Only then flip `draft: false` (a one-line world.yaml change, done here).

## Scope Boundaries

**In scope:**
- visual_style.yaml, portrait_manifest.yaml, Saint-icon + faction-NPC portrait prompts and renders, 17-region POI landscapes, audio.yaml + music params, R2 publication, draft-flag flip on gate MET

**Out of scope:**
- New daemon/engine capabilities; LoRA training; per-Saint hagiography illustrations (Phase 3); UI theming beyond what visual_style.yaml drives (ADR-079 consumes it)

## AC Context

1. **visual_style.yaml** loads; suffix carries all style/medium language; sample renders show coherent world identity distinct from flickering_reach.
2. **Portraits:** every portrait_manifest entry rendered + published to R2 with correctly-keyed slugs (verify against a live bucket scan, not r2_audit's unreliable audio classification — that caveat is audio-specific but the verify-against-bucket habit generalizes).
3. **POIs:** each of the 17 regions has at least its keynote landmark rendered (Giglio-on-the-Water, the Tip-Top House, the drowned torch, Brown's Hotel, etc.) and published.
4. **Audio:** audio.yaml paths resolve (shared `assets/` prefix entries verified against the live bucket); region/scene cues mapped.
5. **Gate MET → draft lifted:** world appears in selection only after all of the above; pack README world-status table updated.

## Assumptions

- 103-6 (landmarks) + 103-7 (faction NPCs) merged; 103-4 iconography available for Saint icons.
- Z-Image daemon capacity and R2 access as per current ops; art-director/music-director agent lanes execute the authoring, this story tracks the gate.
- 17-region POI coverage at one keynote landmark each is the MET bar for v1 (more landmarks can accrete post-launch).
