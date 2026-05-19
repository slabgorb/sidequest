---
parent: context-epic-54.md
workflow: tdd
---

# Story 54-6: Runtime resolver tool + `location_promotions` table

## Business Context

The runtime heart of Epic 54. Ships the `resolve_location_entity` agent tool with both modes (`narrator_proactive`, `player_initiated`), the `location_promotions` SQLite table + additive migration, the flavor_only → yes_and promotion handler, the player-initiated mint path, and the tool-registry barrel wiring so the narrator can actually call it.

The two modes encode the Zork-Problem-safe split:
- **`narrator_proactive`** — narrator is the source of the entity name. Manifest miss = contract violation; tool returns `NOT_FOUND` so the narrator's pending mechanical action does not commit. Protects the contract.
- **`player_initiated`** — player is the source. Manifest miss = canonization; mint a new `yes_and_minted` entity in `location_promotions`; player's action proceeds. Honors Yes-And.

A `flavor_only` entity engaged mechanically auto-promotes to `yes_and` (Diamonds-and-Coal). Pure mention is descriptive — no mutation. Authored YAML is **never** mutated; all runtime mutation accumulates in the SQLite table, durable per Keith's no-GC retention policy.

**Audience:** Keith-as-player (the lie-detector substrate that makes the narrator answerable to the manifest); Sebastien (mechanical visibility into when an entity gets canonized or promoted, via the OTEL attributes set here and the dedicated spans 54-8 wraps around them).

**Expected outcome:** The narrator pipeline routes every mechanical-engagement entity claim through `resolve_location_entity`. Promotions persist across reloads. The tool's OTEL attribute surface is the seam 54-8 upgrades to dedicated spans.

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-6-resolver-and-promotions.md` — task-by-task TDD guide. **Read this thoroughly; it contains the load-bearing architectural contract for 54-7 / 54-8 too** (extension seam in `_build_effective_manifest`, `save_id="default"` convention, OTEL attribute names that 54-8 wraps).

**Key files:**
- `sidequest-server/sidequest/game/persistence.py` — `location_promotions` schema added to `SCHEMA_SQL` (additive `CREATE TABLE IF NOT EXISTS`); `LocationPromotionRow` dataclass + `list_location_promotions` / `upsert_location_promotion` methods.
- `sidequest-server/sidequest/game/location_resolver.py` (new) — pure-Python resolver. `_build_effective_manifest`, `_match_label`, `_promote_flavor_to_yes_and`, `_mint_yes_and`, `resolve`. Authored entity list is **never mutated** — promotions layer on top via `model_copy`.
- `sidequest-server/sidequest/protocol/models.py` — `LocationEntityResolution` model.
- `sidequest-server/sidequest/agents/tools/resolve_location_entity.py` (new) — `@tool`-decorated adapter. Sets OTEL attributes on `ctx.otel_span`; the dedicated spans land in 54-8.
- `sidequest-server/sidequest/agents/tools/__init__.py` — barrel import.

**Patterns to follow:**
- WRITE-category tool (the registry's `_write_locks` map handles concurrency automatically).
- `commit_known_fact.py` is the closest existing analog (WRITE, `ctx.store`, OTEL attribute setting).
- Save-id is hardcoded `"default"` in v1 — flagged in code with rationale, not a TODO (multi-save scoping arrives if/when the save-id surface formalizes).
- Label normalization: strip leading article (`the/a/an`), lowercase, trim. Same rule both sides of the match.

**What NOT to touch:**
- Authored YAML (read-only contract).
- The dedicated OTEL spans (`location.entity.resolve` / `.minted` / `.promoted`) — those land in 54-8. This story sets attributes on the existing tool-dispatch span only.
- Encounter overlays (54-7 extends `_build_effective_manifest` to accept them; this story stubs `active_overlays` as empty).

## Scope Boundaries

**In scope:**
- `location_promotions` SQLite table (additive migration).
- Pure-Python resolver in `sidequest/game/location_resolver.py`.
- Agent tool adapter in `sidequest/agents/tools/resolve_location_entity.py` + barrel registration.
- `LocationEntityResolution` model.
- OTEL attribute setting on `ctx.otel_span` (the side-channel that 54-8 keeps).

**Out of scope:**
- Dedicated `location.*` OTEL spans (54-8).
- GM-panel routing (54-8).
- Encounter-overlay merge (54-7 — `active_overlays` is empty here).
- UI surfacing (54-9).
- Cookbook-driven procedural entity emit (55-1).
- Narrator-supplied `promoted_canon` from prose — v1 canon = the label; richer canon capture is a 54-8 enrichment seam.

## AC Context

**AC-1:** `location_promotions` table exists after `SqliteStore.open()` against any save (fresh or pre-54). PRIMARY KEY `(save_id, region_id, entity_id)`. `ON CONFLICT DO UPDATE` shape per spec §4.3.

**AC-2:** `resolve(mode=narrator_proactive)` + manifest miss → `LocationEntityResolution(resolved=False, mode_outcome="no_match")`; no row written.

**AC-3:** `resolve(mode=player_initiated)` + manifest miss → new `yes_and_minted` row written; `LocationEntityResolution(resolved=True, mode_outcome="minted", entity.tier="yes_and", entity.provenance="yes_and_minted")`.

**AC-4:** `resolve` against a `flavor_only` entity with `engagement_kind="mechanical"` → new `yes_and_promoted` row written; resolution carries `mode_outcome="promoted"`, `entity.tier="yes_and"`, `entity.provenance="yes_and_promoted"`.

**AC-5:** `resolve` against a `flavor_only` entity with `engagement_kind="mention"` → no mutation; resolution carries `mode_outcome="matched"`, entity tier unchanged.

**AC-6:** Authored entity list passed to `resolve()` is never mutated (Pydantic round-trip equality check after resolve).

**AC-7:** Label matching is case-insensitive and strips leading article. "The Bar" matches "bar" and "the bar".

**AC-8:** `resolve_location_entity` tool is registered in the agent tool barrel and is callable via the narrator's dispatch path.

**AC-9:** OTEL attributes on `ctx.otel_span`: `location.region_id`, `location.label`, `location.mode`, `location.engagement_kind`, `location.resolved`, `location.mode_outcome`, `location.from_promotion`, plus `location.entity_id` / `location.entity_tier` / `location.binding_kind` when resolved.

**AC-10:** Narrator pipeline cannot mechanically claim an entity without routing through the resolver — the agent tool harness enforces this (no "claim without resolve" code path).
