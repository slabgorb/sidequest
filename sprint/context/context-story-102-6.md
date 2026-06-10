---
parent: context-epic-102.md
workflow: tdd
---

# Story 102-6: Psionics — SWN/WWN psychic disciplines + Effort economy + System Strain

## Business Context

Retires deferred phase P7. Psionics is signature SWN content — space_opera without psychics is missing the genre's marquee crunch — and the Effort economy (commit/reclaim against a small pool, with System Strain as the overcommit cost) is the resource game the mechanics-first players want legible. WWN shares the discipline/Effort shape for its own traditions. 90-7 already landed WWN *effort hydration* (`wwn.magic_hydrated`), so the substrate exists; this story makes disciplines *playable in live dispatch* with the full span set (`{ruleset}.effort.commit/reclaim`, `system_strain.delta`).

## Technical Guardrails

- **Spec authority:** SWN module design §6 follow-on / P7 sequencing; the Effort/Strain rules are Sine-Nomine-faithful (the fidelity bar, §1). Where SWN and WWN differ in discipline shape, the module seam differentiates — shared core in the family base, per-module catalogs.
- **Crunch in the Genre, Flavor in the World (ADR-140):** discipline *catalogs* are content (`sidequest-content` genre rules), mechanics are engine. Jade must be able to author a homebrew discipline in YAML without touching Python — this is the load-bearing authoring requirement. Validator coverage for the catalog schema is part of the content surface (project memory: content invariants go in the pack VALIDATOR, never unit tests).
- **Reuse the cast spine and hydration:** psionic activation should flow through the same dispatch entry points 102-2/102-3 wire (beat path + intent-router path), with Effort instead of slot/cast accounting where the rules differ. Don't build a parallel "psionics dispatch."
- **Effort lifecycle is stateful:** committed Effort reclaims on scene/day boundaries per the rules — wire reclaim into the existing scene/time advance surfaces (ADR-130 story-time clock is the precedent for beat-driven time effects). Resume-safety: Effort state persists in the save.
- **Span set is named in the story:** `{ruleset}.effort.commit`, `{ruleset}.effort.reclaim`, `system_strain.delta` — plus discipline-activation spans consistent with `wwn.spell.cast`'s shape.
- **System Strain is shared substrate:** CWN/AWN lethality already uses System Strain — make sure psionic Strain and lethality Strain hit the SAME counter (one ledger per character, no forked strain fields).
- Player-visible math: Effort pool, committed/free, and Strain must be legible in player-facing surfaces (party panel / character sheet projection), per the Sebastien/Jade design rubric.

## Scope Boundaries

**In scope:**
- Engine: discipline activation, Effort commit/reclaim lifecycle, System Strain integration, behind the module seam for SWN + WWN
- Content: discipline catalogs for space_opera (SWN) and the WWN-bound packs that want them (heavy_metal at minimum), with validator schema
- Dispatch wiring on both entry paths; OTEL span set; fixtures + wiring test
- Player-facing Effort/Strain projection

**Out of scope:**
- CWN/AWN-specific psionics (CWN has none canonically; AWN mutations are AWN Plan 2, NOT this story — the AWN spec keeps mutations separate)
- The narrator tool contract verbs for psionics beyond what 102-5's contract already shapes (if 102-5 lands first, add the psionic tools here per its pattern)
- Torch/foci/high-tech psitech items (content backlog, not engine)

## AC Context

1. **Discipline activation live:** a PC with a discipline activates it in live dispatch (beat or free-text path) → discipline span + `{ruleset}.effort.commit` with pool deltas; narration reflects the mechanical outcome.
   - Edge: zero free Effort → activation refused or Strain-bought per the rules — loudly, never silent success.
2. **Reclaim lifecycle:** Effort committed "scene" reclaims on scene end; "day" on day advance — `{ruleset}.effort.reclaim` spans fire from the time-advance surfaces. Test: fixture advancing the clock, asserting pool restoration + spans.
3. **Strain ledger unity:** psionic Strain and lethality Strain accumulate on one counter; `system_strain.delta` carries source attribution. Test: mixed-source fixture.
4. **Authoring surface:** a new discipline added purely in pack YAML validates and is activatable with zero engine edits (test: synthetic fixture discipline in a test pack — code-shaped test; real catalog completeness is validator territory).
5. **Persistence:** save/load round-trips Effort commitments and Strain (resume-safe).
6. **Wiring:** integration test from player input through dispatch to spans.

## Assumptions

- 90-7's hydration covers the discipline/Effort data shape or extends naturally to it (verify `wwn.magic_hydrated`'s payload first).
- Scene/day boundaries are detectable from existing clock/scene surfaces (ADR-130 + scene machinery) without new narrator obligations.
- server+content only (per story header); any player-facing projection lands via existing reactive state surfaces without new UI components — if a character-sheet UI change becomes necessary, flag scope to SM (story says server,content).
