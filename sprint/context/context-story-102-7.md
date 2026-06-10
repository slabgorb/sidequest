---
parent: context-epic-102.md
workflow: tdd
---

# Story 102-7: AWN module live wiring for mutant_wasteland

## Business Context

Make the fourth sister real at the table. AWN Plan 1 already landed the foundation — `AwnRulesetModule` exists (subclassing `CwnRulesetModule` with zero overrides, an honest `awn` slug) and `genre_packs/mutant_wasteland/rules.yaml:14` binds `ruleset: awn` — but the AWN spec's §6.5 mandate ("OTEL / wiring test — the GM panel is the lie detector") has not been discharged with **live** proof. mutant_wasteland is a shipped, selectable pack; a player can start a fight there today and nobody has verified the AWN lethality stack actually fires through live dispatch the way WWN's does in heavy_metal. This story is Verify Wiring, Not Just Existence, applied to a whole module: prove AWN combat + lethality live, and close whatever gaps the proof finds.

## Technical Guardrails

- **Read the architect addendum first:** AWN spec §11 (binding styles — the load-bearing finding, §11.1; the partitioned change-list, §11.2; calibration trap, §6.4/§11.4). The two binding styles finding determines where any missing wiring lives.
- **Inheritance is the design:** AWN inherits CWN resolution verbatim in Plan 1. Expect ZERO new resolution code — the deliverables are proof artifacts (fixtures, span assertions, a live playtest slug) plus fixes for anything the proof exposes. If a fix requires AWN-specific overrides, that contradicts Plan 1's "no overrides" and needs an Architect flag before coding.
- **Mirror the WWN proof shape:** 90-7's `combat_wwn_emberfront` deterministic fixture and the heavy_metal live-proof pattern are the templates — build `combat_awn_*` equivalents for mutant_wasteland. Reuse the scene-harness (ADR-092) fixture machinery.
- **This story inherits the epic's seam fixes:** 102-1's PC-death downed seam covers AWN automatically via `isinstance(module, CwnRulesetModule)` capability binding — the AWN fixtures should assert `awn.mortal_injury`/`awn.shock` (honest slug!) on both drop directions, sequenced after 102-1 merges.
- **Calibration trap (§6.4/§11.4):** the documented remap consequence means pre-existing mutant_wasteland calibration numbers may *look* like a regression after AWN binding — do NOT "fix" them back; the spec documents the expected shift.
- **Content lane:** any `rules.yaml` additions follow ADR-140 (genre owns mechanics config) and validate via the pack validator; content invariants (e.g., "mutant_wasteland binds awn") belong in the validator, not pytest (project memory).
- **Span slug assertions everywhere:** the whole point of the subclass is the honest slug — every assertion checks `awn.`, and at least one test asserts spans are NOT labeled `cwn.` for an AWN-bound encounter.

## Scope Boundaries

**In scope:**
- Deterministic AWN combat fixture(s) for mutant_wasteland (strike path, reprisal/PC-death path, killing blow) with span assertions
- A live free-play playtest proving AWN combat + lethality on the GM panel (slug recorded, mirroring `2026-06-10-long_foundry`)
- Fixes for any wiring gaps the proof exposes (within the inherits-CWN envelope)
- Any missing mutant_wasteland `rules.yaml` mechanics config the proof requires + validator coverage

**Out of scope:**
- AWN Plans 2–7 (mutations, radiation, disease, stress, hexcrawl, creatures, enclaves) — each gets its own spec when reached
- AWN-specific resolution overrides (Plan 1 = zero overrides by design)
- The shared-seam work itself (102-1..3 land independently; this story consumes them)

## AC Context

1. **Strike-path lethality live:** PC drops an opponent in a mutant_wasteland encounter → `awn.shock`/`awn.mortal_injury` (per CWN-inherited rules) through live dispatch. Fixture + span assertions.
2. **PC-death lethality live (post-102-1):** opponent reprisal drops the PC → AWN downed seam fires with `awn.` slug. Fixture asserts both directions.
3. **Honest slug:** all module spans in AWN encounters carry `awn`, none carry `cwn` (negative assertion); save files / GM panel show `awn`.
4. **Live proof:** a recorded free-play playtest (sq-playtest, headless acceptable) shows AWN combat engaging on the GM panel — the §6.5 mandate discharged, slug noted in the session record.
5. **Calibration documented:** if difficulty numbers shifted per §6.4, the session/PR notes say so explicitly, citing the spec — no silent renumbering, no false-regression "fix."
6. **Wiring test:** integration test reaches AWN resolution from WebSocket-level dispatch in a mutant_wasteland-configured session.

## Assumptions

- 102-1 merges before this story's PC-death assertions (sequencing dependency — the strike-path half is independent and can start first).
- mutant_wasteland's pack content (archetypes, encounters) is complete enough to drive a combat playtest without content authoring beyond `rules.yaml` mechanics config.
- The scene-harness dev endpoint (ADR-092, *partial*) supports mutant_wasteland fixtures as it did heavy_metal's; if not, extending it is in-scope.
