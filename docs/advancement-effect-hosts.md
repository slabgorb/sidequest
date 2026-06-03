# Advancement Effect Hosts — Per-Genre Audit (Story 39-5 / AC6)

**Status:** Decision artifact for ADR-078 / ADR-081
**Last updated:** 2026-04-19

## Decision

Each genre authors its [`AdvancementTree`](../sidequest-api/crates/sidequest-genre/src/models/advancement.rs)
in one of two mutually-exclusive locations:

- **Progression host** — `mechanical_effects:` blocks on affinity tiers in
  `progression.yaml`. Harvested by
  [`load_advancement_tree`](../sidequest-api/crates/sidequest-genre/src/loader.rs)
  into a tree where each tier id is auto-derived from the affinity + tier slot
  (e.g. `iron_tier_1`).
- **Sidecar host** — a standalone `advancements.yaml` file at the genre root,
  deserialised directly as an `AdvancementTree`.

A genre may use **exactly one** of the two hosts. Carrying both files is a
validation error — the loader fails loudly with
`GenreError::ValidationError` naming both paths. See
[`load_advancement_tree`](../sidequest-api/crates/sidequest-genre/src/loader.rs)
for the enforced rule. No silent fallback.

A genre with neither host is valid (empty `AdvancementTree::default()`) and
indicates that the pack has not yet been wired for mechanical advancement —
these genres still author narrative abilities on affinity tiers, but those
abilities do not feed the Edge / Composure mechanical path until a tier carries
a `mechanical_effects:` block or the genre ships an `advancements.yaml`.

## Per-Genre Decisions

Heavy_metal is the lead implementation for 39-5; the remaining genres declare
their host decision here and land their mechanical content in follow-up
stories.

| Genre                 | Host                | Status (as of 39-5) | Rationale |
|-----------------------|---------------------|---------------------|-----------|
| heavy_metal           | progression.yaml    | **populated**       | Six-affinity structure (Iron/Pact/Craft/Lore/Court/Ruin) maps cleanly to `AffinityTier.mechanical_effects`. This story lifts ADR-081 draft §2 into live YAML; see `sidequest-content/genre_packs/heavy_metal/progression.yaml`. |
| caverns_and_claudes   | progression.yaml    | empty (declared)    | Delver / Plunderer / Slayer / Spellweaver / Steel affinities already carry rich `unlocks` → `mechanical_effects` lands on the same tiers when content arrives. Meta-humor genre, so mechanical depth is low priority. |
| elemental_harmony     | progression.yaml    | empty (declared)    | Element affinities already host tiered abilities; `mechanical_effects` lives there rather than in a parallel file. Future story will wire element-specific BeatDiscount / LeverageBonus. |
| mutant_wasteland      | advancements.yaml   | empty (declared)    | Radiation mutations and scavenger perks do not map cleanly to the six-affinity structure used by other packs — a sidecar keeps the mutation catalogue independent from the core progression tree. |
| neon_dystopia         | advancements.yaml   | empty (declared)    | Cybernetic augments are modular and cross-cutting (a neural jack is not a tier on a single affinity). Sidecar allows augment grants to reference multiple triggers and class gates without forcing them into a progression slot. |
| pulp_noir             | progression.yaml    | empty (declared)    | Hunch / Heat / Leverage / Grit affinities carry mechanical effects on their tiers — same pattern as heavy_metal. |
| road_warrior          | advancements.yaml   | empty (declared)    | Vehicle modifications are first-class content — a sidecar lets mod-grant tiers reference `vehicle_class` gates and beat ids from the dogfight subsystem (ADR-077) without cluttering driver progression. |
| space_opera           | progression.yaml    | empty (declared)    | Ship officer archetypes use affinity tiers (Command / Science / Operations / Security) — mechanical effects host there. |
| spaghetti_western     | progression.yaml    | empty (declared)    | Draw / Grit / Survival / Reputation affinities host mechanical effects on tiers, matching heavy_metal / pulp_noir. |
| tea_and_murder              | progression.yaml    | empty (declared)    | Propriety / Reason / Sentiment / Constitution affinities — same host pattern as pulp_noir. |

**Summary:** 7 progression-hosted, 3 sidecar-hosted. The sidecar choice is
reserved for genres where the mechanical content is either modular
(cybernetics, vehicle mods) or categorically outside the affinity model
(mutations). The default is the progression host — it keeps the mechanical
hook adjacent to the authored ability narrative.

## Wiring Path

For the progression-hosted genres, `load_advancement_tree` harvests tiers by
walking `progression.yaml → affinities[].unlocks.{tier_0..tier_3}.mechanical_effects`
and yielding an `AdvancementTier` per populated host. Tier ids are synthesised
as `{affinity_lowercase}_tier_{n}`; authors do not write ids by hand in this
path.

For sidecar-hosted genres, authors write the full `AdvancementTree` YAML
directly, including explicit tier ids. The sidecar schema matches the
`AdvancementTree` type exactly.

Both paths terminate in the same runtime type — `AdvancementTree` — consumed
identically by [`resolved_beat_for`](../sidequest-api/crates/sidequest-game/src/advancement.rs)
and [`grant_advancement_tier`](../sidequest-api/crates/sidequest-game/src/advancement.rs).

## Non-Goals (Story 39-5)

- **Landing content for the other nine genres.** Each genre's mechanical
  content is its own story. This audit captures the *decision*, not the YAML.
- **Migrating from one host to the other.** A genre that declares
  progression and later decides it needs the sidecar (or vice versa) does so
  in a follow-up story that moves the content and lands the dual-host
  validation test.
