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
implementation-pointer: "sidequest-server/sidequest/game/ruleset/registry.py — native, swn, cwn, wwn, awn modules live and pack-bound"
---

# ADR-117: Pluggable Ruleset Module System

> **Documents a system already live in code.** The `RulesetModule` seam, its
> registry, and the `native` / `swn` modules shipped during the 2026-05 SWN /
> ablative-HP work (ADR-114) without a governing ADR; the `wwn` and `cwn` modules
> followed. This record closes that architecture-of-record gap and states what
> the decision *was*. Four modules are now live and pack-bound (`native`, `swn`,
> `wwn`, `cwn`).

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
binding is resolved through a fail-loud registry. Four modules are implemented:
`native` (the ADR-033 dial/confrontation engine, the default), `swn` (Stars
Without Number — d20 attack-vs-AC, three-category saves, 2d6 skill checks,
1d8+DEX initiative, ablative HP via ADR-114), and the two SWN-derived
Without-Number modules `wwn` (Worlds Without Number) and `cwn` (Cities Without
Number), each subclassing `swn` and adding its own lethality/subsystem layer.**

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
- **`wwn.py`** — `WwnRulesetModule` (`slug = "wwn"`). Worlds Without Number;
  subclasses `swn` (shared d20/HP core) and adds the WWN lethality layer (Luck
  save, Shock, Trauma, System Strain, Mortal Injury) plus WWN magic (Effort).
- **`cwn.py`** — `CwnRulesetModule` (`slug = "cwn"`). Cities Without Number;
  subclasses `swn` and adds the CWN Luck save and the cyberspace hacking ladder.
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

- Multiple resolution procedures now exist; contributors must know which module a
  pack binds before reasoning about combat.
- The `RulesetModule` contract is broad (10 methods). The `wwn` and `cwn` modules
  exercised the abstraction by subclassing `swn` rather than re-deriving from the
  ABC, confirming the shared Without-Number core generalizes; a non-SWN-derived
  SRD (B/X, Fate) is still the harder test of whether it leaks SWN/native
  assumptions.
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

`implementation-status: live` — the **seam is live** with four pack-bound
modules; some **per-module narrator routing is still partial** (see Deferred).

**Live:**
- `RulesetModule` ABC, registry (fail-loud), four modules: `native`, `swn`,
  `wwn`, `cwn`.
- `space_opera` binds `ruleset: swn`; SWN attack-vs-AC + damage + ablative HP +
  `hp_depletion` win condition are live for personal (Firefight) and ship combat
  (e2e green 2026-05-27).
- `elemental_harmony` binds `ruleset: wwn` and `neon_dystopia` binds
  `ruleset: cwn`; both inherit the SWN attack/damage/HP core and add their own
  lethality/subsystem layers (WWN: Luck/Shock/Trauma/System Strain/Mortal Injury
  + Effort magic; CWN: Luck save + hacking ladder).
- `check_params` / `save_params` / `roll_initiative` are wired through generic
  `ruleset.X(...)` dispatch (not SWN-special-cased): checks/saves via the
  player-initiated `CHECK_THROW` dice protocol (ADR-074; `dispatch/check.py`,
  resolved with no narrator run), initiative via `dispatch/encounter_lifecycle.py`
  (`ruleset.roll_initiative`). Checks are **player-pull** — the narrator does not
  autonomously demand one.

**Deferred / not yet built:**
- The narrator/intent-router does not yet autonomously decide that an action
  *requires* a check and push a roll prompt — checks/saves are player-initiated
  (player-pull) via the dice protocol, not narrator-triggered.
- `space_opera` chargen does not yet author per-class HP tables
  (`base_max_by_class`); characters default to 10 HP until added.
- Non-combat confrontations (negotiation, pursuit, dogfight) still resolve via
  `native` dials even in SWN-bound packs.
- Additional modules (`bx` for `caverns_and_claudes`, plus Fate / PbtA / 5e) are
  designed in the spec but **not implemented**. Per the Edge/HP doctrine
  (ADR-114), the planned Fate module is the intended home for the retired
  Edge/Composure substrate.

## Amendments

### 2026-06-05 — Capability gates, not slug strings (the fifth-module lesson)

The fifth module, `awn` (Ashes Without Number → `mutant_wasteland`;
`AwnRulesetModule(CwnRulesetModule)`, epic 88, design spec
`docs/superpowers/specs/2026-06-05-ashes-without-number-mutant-wasteland-design.md`
§11), exposed a recurring cost in how the engine *outside* the seam keys on
ruleset behavior. Two binding styles coexist:

| Style | Example | Cost per new sister module |
|---|---|---|
| **Capability / type** — `isinstance(cfg, CwnConfig)`, `isinstance(module, CwnRulesetModule)`, method-override probes (e.g. the opponent-reprisal check `type(ruleset).resolve_opponent_attack is not RulesetModule.resolve_opponent_attack`) | `downed_seam.py` cfg gate, `dice.py` reprisal probe | **Zero.** A thin subclass *is* its parent; these sites covered `awn` with no edits. |
| **Slug-string membership** — `rules.ruleset == "cwn"`, `ruleset in ("cwn", "wwn")` | `builder.py` `seed_system_strain`, `downed_seam.py` (second gate), `stabilize_mortal_injury.py`, `adjust_system_strain.py` | **One edit per site per module**, and the failure mode is a *silent no-op* (`"awn" != "cwn"` falls through quietly — a No Silent Fallbacks violation in spirit, since nothing fails loud). |

The `awn` integration (story 88-1) required touching six slug-string sites that
the capability-style sites covered for free; `road_warrior`'s `cwn` binding paid
the same toll earlier.

**Doctrine going forward:** cross-cutting ruleset capability gates SHOULD key on
the **config/module type or a method-override probe**, not on `rules.ruleset`
slug-string membership. Slug strings remain correct for exactly two uses: the
registry lookup itself, and genuinely slug-specific behavior (e.g. the
SWN-only dogfight gate). When a gate means "this family of rulesets supports
System Strain / Mortal Injury / Shock," express it as
`isinstance(cfg, CwnConfig)` (covers all present and future subclasses) or
probe the method override.

**Known debt — RESOLVED (story 88-3, 2026-06-09).** The four slug-string sites
named above were in fact converted to capability gates *inline during 88-1/88-2*,
not deferred: `builder.py` `seed_system_strain` → `isinstance(cfg, CwnConfig)`;
`stabilize_mortal_injury.py` / `adjust_system_strain.py` → `isinstance(module,
CwnRulesetModule)`; `downed_seam.py` → `isinstance(cfg, (CwnConfig, WwnConfig))`.
Each is covered by a green AWN test proving the gate fires for `awn` (a thin
`CwnConfig`/`CwnRulesetModule` subclass): `test_awn_downed_target_gets_mortal_injury`,
`test_awn_returns_pool_maxed_at_con_score`, `test_awn_pack_applies_strain`,
`test_awn_pack_can_stabilize`. Story 88-3 verified this and corrected the lagging
docstring summaries. The only `rules.ruleset == "cwn"` checks that remain are the
genuinely slug-specific hacking-ladder gates (`dice.py`, `confrontation.py`) — kept
by design per the doctrine above. No outstanding consolidation work; the doctrine
stands for sister module #6 and beyond.
