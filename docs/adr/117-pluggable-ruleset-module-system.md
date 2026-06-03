---
id: 117
title: "Pluggable Ruleset Module System — Per-Genre Resolution Behind a RulesetModule Seam"
status: accepted
date: 2026-05-28
deciders: ["Keith Avery", "Major Margaret Houlihan (Architect)"]
supersedes: []
superseded-by: null
related: [33, 78, 93, 97, 114]
tags: [game-systems]
implementation-status: live
implementation-pointer: "sidequest-server/sidequest/game/ruleset/registry.py — native, swn, cwn, wwn modules live and pack-bound"
---

# ADR-117: Pluggable Ruleset Module System

> **Documents a system already live in code.** The `RulesetModule` seam, its
> registry, and two modules (`native`, `swn`) shipped during the 2026-05 SWN /
> ablative-HP work (ADR-114) without a governing ADR. This record closes that
> architecture-of-record gap and states what the decision *was*.

## Context

SideQuest's doctrine is **Crunch in the Genre, Flavor in the World** (SOUL.md): a
genre is the rulebook, a world is the campaign setting, and one genre can host
many worlds. Until 2026-05, the engine had exactly one rulebook — the dial-based
Confrontation engine (ADR-033) — applied uniformly to every pack. ADR-033 had
*explicitly rejected* per-genre engine modules ("standoff.rs, humanity.rs…")
on the grounds that a single resource-pool abstraction with genre-supplied data
was sufficient.

Two pressures broke that assumption:

1. **Mechanics-first players (Sebastien, Jade)** wanted real, legible crunch —
   not LLM-interpreted dials. They specifically miss SRD-grade resolution (attack
   rolls, armor class, saves, hit points).
2. **ADR-114 (Ablative HP Substrate)** reintroduced HP as a first-class lethality
   track. HP-based resolution (SWN, B/X, 3.5) cannot be expressed as a thin data
   layer over the dial engine — the *resolution procedure itself* differs (roll
   d20 vs AC and ablate HP, versus advance a dial toward a threshold).

So a genre now needs to choose *which resolution procedure runs*, not merely
supply numbers to one fixed procedure. That is a behavior-selection problem, and
it must honor the project's **No Silent Fallbacks** rule: an unknown or
misconfigured ruleset must fail loudly at pack load, never silently degrade to a
default.

## Decision

**Resolution behavior is pluggable per genre via a `RulesetModule` seam. Each
genre pack binds exactly one module by slug in `rules.yaml` (`ruleset:`). The
binding is resolved through a fail-loud registry. Two modules are implemented:
`native` (the ADR-033 dial/confrontation engine, the default) and `swn` (Stars
Without Number — d20 attack-vs-AC, three-category saves, 2d6 skill checks,
1d8+DEX initiative, ablative HP via ADR-114).**

This is a **scoped reversal of ADR-033's rejection of per-genre engine modules.**
ADR-033 is not superseded — its dial engine survives intact *as the `native`
module*. What changes is that the dial engine is no longer the only resolution
procedure; it is one registered module among a planned several.

### The seam

`sidequest/game/ruleset/`:

- **`base.py`** — `RulesetModule` (ABC). The contract every module implements.
  Abstract: `find_confrontation`, `stat_modifier`, `compute_dc`, `apply_beat`,
  `resolve_damage`. Concrete-with-default (overridable): `attack_params`,
  `ship_attack_params`, `check_params`, `save_params`, `roll_initiative`. Also
  defines `UnknownRulesetError`.
- **`registry.py`** — `_REGISTRY: dict[str, RulesetModule]` of stateless
  singletons; `get_ruleset_module(slug)` resolves or **raises
  `UnknownRulesetError`** (no default, no fallback).
- **`native.py`** — `NativeRulesetModule` (`slug = "native"`). Wraps the ADR-033
  dial engine. The default when a pack omits `ruleset:`.
- **`swn.py`** — `SwnRulesetModule` (`slug = "swn"`). Stars Without Number.
- **`resolution.py`** — shared resolution helpers.

### Binding contract

- `RulesConfig.ruleset: str = "native"` (`genre/models/rules.py`) — the default
  is the current dial engine, so every existing pack keeps its behavior with no
  change.
- The `swn` binding additionally requires a complete `rules.swn.attribute_map`
  (six SWN attributes → flavor stats), validated at load — a missing or partial
  map raises `ValueError` on `RulesConfig`.
- `loader.py` calls `get_ruleset_module(pack.rules.ruleset)` at pack load and
  lets `UnknownRulesetError` propagate — **fail loud at load**, never at turn time.

### Module is per-session, never cross-fallback

A session runs exactly one module for its whole life. Modules are stateless
singletons (safe to share). There is no per-turn module switching and no
"try native, then swn" path.

## Consequences

**Positive**

- Mechanics-first players get genuine SRD crunch where a pack opts in (SWN live
  for `space_opera`); narrative-first packs keep the dial engine untouched.
- New rulesets are additive: register a module, bind it from a pack. No engine
  rewrite, no conditional sprawl in the turn loop.
- Fail-loud binding surfaces misconfiguration at load, honoring No Silent
  Fallbacks.
- HP-based and dial-based resolution coexist cleanly (pairs with ADR-114's
  HP-vs-Edge "different substrates for different engines" intent).

**Negative / cost**

- Two resolution procedures now exist; contributors must know which module a
  pack binds before reasoning about combat.
- The `RulesetModule` contract is broad (10 methods). Adding a third SRD will
  test whether the abstraction generalizes or leaks SWN/native assumptions.
- Per-module narrator surfacing is not uniform yet (see Implementation status).

## Alternatives considered

- **Keep ADR-033's single dial engine + richer genre data (status quo).**
  Rejected: HP resolution is a different *procedure*, not different *data*. Forcing
  it through dials would have been the kind of stringly-typed contortion ADR-033
  was trying to avoid, in reverse.
- **Hard-fork per genre.** Rejected: duplicates the turn loop per pack; violates
  Don't-Reinvent.
- **Runtime auto-detection of ruleset from content shape.** Rejected: implicit and
  fragile; violates No Silent Fallbacks. Explicit `ruleset:` binding wins.

## Implementation status

`implementation-status: partial` — the **seam is live**; the **rollout is partial.**

**Live:**
- `RulesetModule` ABC, registry (fail-loud), `native` + `swn` modules.
- `space_opera` binds `ruleset: swn`; SWN attack-vs-AC + damage + ablative HP +
  `hp_depletion` win condition are live for personal (Firefight) and ship combat
  (e2e green 2026-05-27).

**Deferred / not yet built:**
- SWN `check_params` / `save_params` / `roll_initiative` are implemented in the
  module but **not yet routed from the narrator orchestrator** (skill checks,
  saves, formal initiative do not fire in play yet).
- `space_opera` chargen does not yet author per-class HP tables
  (`base_max_by_class`); characters default to 10 HP until added.
- Non-combat confrontations (negotiation, pursuit, dogfight) still resolve via
  `native` dials even in SWN-bound packs.
- Additional modules (`bx` for `caverns_and_claudes`, plus Fate / PbtA / 5e) are
  designed in the spec but **not implemented**. Per the Edge/HP doctrine
  (ADR-114), the planned Fate module is the intended home for the retired
  Edge/Composure substrate.
