# Context: Epic 113 — Fate Core Narrator / Intent-Router Integration (ADR-144 F2)

## Summary

Wire the Fate engine (F1, merged) into the live narrator + intent-router spine. F1 built the Fate ruleset module, payloads, the `dispatch_fate_action` engine entry, and 12 live Fate spans behind the explicit `FATE_ACTION` message channel. F2 makes Fate reachable from natural language and renders it back to players, across four slices:

- **F2a** — Fate action classifier: freeform action → Intent Router → `fate_action` subsystem → `dispatch_fate_action` (**this epic's only story so far, 113-1**).
- **F2b** — aspects-as-prompt + invoke surfacing + compel proposal.
- **F2c** — create-advantage rendering + the Fate honesty lie-detector.
- **F2d** — deterministic proactive opponent AI.

F2a settles the shared contracts (the `fate_action` subsystem, the `dispatch.params` shape, the `_build_fate_summary` projection, the `fate.action.classified` span) that F2b/F2c/F2d build on.

## Repos
server (sidequest-server) only — no ui/content/daemon.

## Doctrine & Constraints

- **ADR-144 / SOUL "Bind the Ruleset, Don't Balance It":** Fate Core (CC-BY SRD) is bound for the detective/social genres; the native ruleset is being removed, not balanced against. No native beat/dial mechanic is recreated, converted, or gated on the Fate path.
- **No `full_defense` creep:** Fate's actions are overcome / create_advantage / attack / concede (+ reactive Defend). A "full/total defense +2 stance" is a d20-ism not in the Fate SRD — keep it out (caught smuggled into F1c).
- **Two channels, one engine:** the explicit `FATE_ACTION` message (F1d) and the freeform classifier (F2a) both terminate in `dispatch_fate_action`. No duplicate classifier, no duplicate engine entry (CLAUDE.md "Don't Reinvent").
- **Pre-narrator engagement + OTEL lie-detector:** mechanical engagement runs on the canonical snapshot before the narrator, and every decision emits a span (the GM panel is the lie-detector). Wiring is proven via spans + runtime `get_registered()` + real-bank drives, never source greps.

## Dependencies
F1a–F1d merged to server `develop` (`FateRulesetModule`, `FateActionPayload`, `dispatch_fate_action`, the 12 live Fate spans).

## Refs
- Decision of record: ADR-144 — Fate Core binding replaces the native ruleset
- Design: `docs/superpowers/specs/2026-06-14-fate-core-binding-replaces-native-design.md`
- Epic decomposition (F2a–F2d slice map, shared contracts, OTEL inventory, open §7 decisions): `docs/superpowers/plans/2026-06-14-f2-narrator-intent-router-integration.md`
