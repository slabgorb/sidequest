---
id: 95
title: "Class Mechanical Surface — One Signature Ability Per Non-Magical Class"
status: accepted
date: 2026-05-10
deciders: ["Keith Avery", "The Man in Black (Architect)"]
supersedes: []
superseded-by: null
related: [14, 21, 86]
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-095: Class Mechanical Surface — One Signature Ability Per Non-Magical Class

## Status

Accepted.

## Context

Two of the four primary-audience players (Keith — 40-year B/X veteran;
Sebastien — mechanics-first) read the character sheet before the prose. A
freshly-created Lv 1 Cleric and Lv 1 Thief in `caverns_and_claudes`
displayed `"No abilities."` on the Abilities tab — honest data, honest
rendering, but to a B/X reader it parses as a load failure or a missing
class definition.

ADR-021 established Affinities (`progression.yaml`) as the growth lane —
class-agnostic, earned through play. The data shape of `classes.yaml`
implied that classes themselves are a flavor lane (kit, stat prime,
encounter beats, magic plugin) with no mechanical signature of their own.

## Decision

**Classes are a mechanical lane, not flavor-only.** Every class either
has a magic plugin filling its signature mechanical slot, or carries one
Class-source `AbilityDefinition` that does. Affinities remain the
*growth* lane on top — the class signature is the *starting* mechanical
lane. Both ship and coexist; neither replaces the other.

For `caverns_and_claudes`:

- Cleric → **Turn Undead** (Class-source signature ability)
- Fighter → **Taunt** (Class-source signature ability + new beat ID with
  taunt-aware targeting bias and per-encounter damage redirect)
- Thief → **Backstab** (Class-source signature ability)
- Mage → no Class signature; magic plugin fills the slot

The Abilities tab renders four sections gated on per-source presence:
Class signature, Class moves (chip row from `encounter_beat_choices`),
From inventory (Item-source — hooked but empty), Earned (Play-source).
Empty sections suppress their headers. The string `"No abilities."` does
not appear in rendered output.

The taunt mechanic is wired into the real combat path:

- `_opposite_side_first_actor` in `apply_beat` consults `enc.taunt` and
  routes single-target enemy hits onto the taunter when the taunter is
  among the opposite-side live actors.
- The spread-mode branch reroutes one ally hit per round to the taunter
  via `TauntState.try_consume_redirect()`.
- `taunt_tick.py` runs `end_of_round_decay()` on the WebSocket session
  handler's round-advance hook (`record_interaction()`), emitting an
  `encounter.taunt.expired` OTEL span when the taunter clears.

## Scope

`caverns_and_claudes` only. Other 10 genre packs adopt the data shape
lazily as they surface for playtest.

## Consequences

### Positive

- Sebastien sees a mechanical signature on every L1 sheet — the design
  intent is now visible without prose mediation.
- Keith's B/X expectations are met: Cleric has Turn Undead, Thief has
  Backstab, both rendered with mechanical detail.
- Fighter's Taunt is mechanically real, not just a sheet line — the
  redirect actually fires in combat, observable via the GM panel's
  State Transitions tab (`taunt_redirected` flag on edge_debit events).
- The "no abilities" empty state dies. Empty Item-source and Earned
  sections gracefully suppress their headers.
- The four-source layout (Race / Class / Item / Play) is now load-bearing
  at the UI level, not just the data level.

### Negative

- Per-genre adoption is now a real cost — each genre pack that wants to
  show class signatures must author them in `abilities:` blocks.
- A class with both `magic_config` and `abilities:` populates both. By
  design, but a future genre author could create unexpected combinations.
- `AbilityDefinition` and `AbilitySource` were relocated from
  `sidequest.game` into `sidequest.protocol.models` to break a circular
  import. The dependency direction `game → protocol` (via re-export) is
  architecturally unusual; a follow-up ADR may extract these into a
  shared `_types` module.

### Neutral

- ADR-021 is amended, not superseded. Affinities continue exactly as
  designed. The class signature is *additive*.

## Alternatives Considered

Three options were brainstormed (per design spec
`docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md` §10):

1. **Minimum visibility fix.** Change the empty-state string; surface
   Turn Undead via the existing `magic_config.turn_undead: true` flag.
   Rejected — papers over the structural issue.
2. **Promote class beats to abilities.** Treat `encounter_beat_choices`
   (filtered) as Class-source abilities directly. Rejected — collapses
   two abstractions that should remain separate (the cards-vs-chips
   visual distinction is load-bearing).
3. **Restore B/X canonical class data.** Add Thief percentage skills,
   Turn Undead matrix, etc. Deferred — likely the right move for a future
   "canonical sheets" pass, but blocks this story on too much content.

The chosen design — one signature `AbilityDefinition` per non-magical
class plus the chip row — captures most of the mechanical-signal value
at a fraction of Option 3's content lift.

## References

- Design spec: `docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-10-class-mechanical-surface.md`
- ADR-014 (Diamonds and Coal) — detail signals importance
- ADR-021 (Progression System) — Affinity lane (amended by this ADR)
- CLAUDE.md "Who This Is For" — Sebastien / Keith audience rubric
