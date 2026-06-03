---
parent: context-epic-82.md
workflow: tdd
---

# Story 82-4: Make the four-tier Resolver the production resolution path or narrow ADR-121

## Business Context

ADR-121 describes a four-tier content resolution walk (Global → Genre → World → Culture) with
per-field merge strategies and provenance, exposed via `Resolver[T].resolve_merged`. The class
exists and its supporting types are live and on the wire — but `resolve_merged` is never
called: production archetype resolution uses a simpler two-tier shim (world funnel → genre
fallback). So the ADR claims a four-tier reality the code doesn't run. This matters for
homebrew authoring (ADR-121 is the contract authors rely on for how their world/culture
overrides merge): if the real path is two-tier, authors' culture-level overrides may not
resolve as documented. This story forces the question — wire the full path, or make the ADR
tell the truth — and removes the dead-code ambiguity either way.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 anchors may drift):**
- `genre/resolver.py` (~:200-390 — `Resolver[T]` + `resolve_merged`; ~:89-128 `LayeredMerge`; ~:23-57 `MergeStrategy`).
- `genre/archetype/shim.py` (~:64-158 — the live two-tier `resolve_archetype` path).
- `server/websocket_handlers/chargen_mixin.py` (~:391 — the production caller) → `game/archetype_apply.py` (~:16-23).
- `protocol/provenance.py` (~:53-76 — `Provenance`/`MergeStep`); `protocol/models.py` (~:194 — `archetype_provenance` on the wire).

**Patterns to follow:**
- If wiring the Resolver: it must emit OTEL describing the merge steps/provenance (the ADR's
  provenance promise becomes observable — dev/GM can see which tier won each field).
- Fail-loud on a resolution that can't complete; don't silently fall back to a partial merge.

**What NOT to touch:**
- `LayeredMerge` / `MergeStrategy` / `Provenance` types — they are live and correct.
- The wire format for `archetype_provenance` (already shipped).

## Scope Boundaries

**In scope:**
- A recorded decision (with code evidence) — adopt the four-tier Resolver as the production
  path, or narrow ADR-121 to the two-tier shim.
- Executing the chosen path: either route production resolution through `resolve_merged`
  (+ OTEL), or rewrite ADR-121 + remove/mark `resolve_merged` so no unmarked dead code remains.
- A wiring test for the chosen mechanism.

**Out of scope:**
- Redesigning the merge-strategy taxonomy or provenance schema.
- Broadening resolution to entity types beyond what the shim handles today (unless the decision
  explicitly requires it).

## AC Context

1. **Decision recorded.** The story logs which path was chosen and why, citing the code reality
   (two-tier shim vs four-tier Resolver) — this is the first deliverable, made before code.
2. **If wired:** production archetype resolution calls `Resolver.resolve_merged`; the
   Global→Genre→World→Culture merge + provenance actually runs; OTEL emits the merge
   steps/provenance. Test asserts a culture-tier override resolves per the documented strategy.
3. **If narrowed:** ADR-121 is rewritten so the two-tier shim is described as the production
   reality, and `resolve_merged` is removed or explicitly marked non-production (no unmarked
   dead code). Frontmatter/indexes updated accordingly.
4. **Wiring test.** The production resolution path exercises the chosen mechanism end-to-end;
   if the four-tier path is chosen, the test fails on current `develop`. Full `just server-test`
   green.

## Assumptions

- The two-tier shim's current behavior is acceptable for the cases it handles today; the
  decision turns on whether culture-tier (and global-tier) overrides are actually needed by
  live/forthcoming content (e.g. Jade's `perseus_cloud` work).
- Provenance is already plumbed to the client, so wiring the Resolver mainly changes the
  producer, not the wire contract.
- This story does not depend on 82-2/82-3; it can run independently.
