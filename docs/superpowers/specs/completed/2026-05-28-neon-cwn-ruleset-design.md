# Neon Dystopia → Cities Without Number Ruleset

**Date:** 2026-05-28
**Status:** Design — approved, pending spec review
**Author:** GM (with Keith)

## Summary

Bind the `neon_dystopia` genre pack to a faithful **Cities Without Number (CWN)**
ruleset, implemented as a new `cwn` `RulesetModule` that subclasses the existing
`swn` module. CWN is Stars Without Number's cyberpunk cousin — same designer
(Kevin Crawford / Sine Nomine), same core resolution engine — so the bulk of the
work is inheritance plus three cyberpunk-specific engine additions: **System
Strain**, **Trauma/Shock lethality**, and **hacking-as-confrontation**.

This is the cyberpunk parallel to the 2026-05-25 SWN-crunch / ablative-HP
reintroduction — a direct response to Sebastien and Jade, the playgroup's two
mechanics-first players, who want legible crunch in the player-facing surface.

## Motivation

`neon_dystopia` currently runs six bespoke attributes (Body/Reflex/Tech/Net/Cool/
Edge), an ad-hoc 0–100 Humanity tracker, and momentum-dial confrontations for
everything including combat. There is no real lethality, no mechanical cost model
for chrome, and hacking is narrative-only. CWN supplies all three as a coherent,
published ruleset that shares the engine we already shipped for `space_opera`.

## Decisions (locked)

| Fork | Decision |
|---|---|
| Fidelity | New `cwn` module subclassing `swn`; CWN deltas as real engine code (not content-only, not full class/Focus/Edge port). |
| Attributes | New cyberpunk-flavor names, clean 6:1 map to canonical STR/DEX/CON/INT/WIS/CHA. Hacking runs INT+Program. |
| Chrome cost | **System Strain only** (CON-bound). Humanity tracker removed; no separate social/alienation dial. |
| Hacking | Modeled as a confrontation with beats (CWN Verbs → beats, security level → DC). No bespoke cyberspace minigame. |
| Lethality | Trauma/Shock + Mortal Injury **and** the Major Injury d12 table (Sub-decision A: in). |
| Combat shape | Combat moves to HP/AC; the momentum `combat` confrontation is **retired** for neon (Sub-decision B: confirmed). Social/chase stay dial-based. |

No existing saves to preserve — migration churn is not a constraint; optimize for
the best design.

## Scope boundary (SOUL: Crunch in Genre, Flavor in World)

Genre-level change only. `neon_dystopia/rules.yaml` + the new `cwn` engine module
+ supporting pack YAML (inventory, archetypes, tropes, progression). World content
— `franchise_nations` lore, factions, cultures, openings — is **untouched**.

## Architecture

### The `cwn` RulesetModule

New `sidequest-server/sidequest/game/ruleset/cwn.py`, `slug = "cwn"`, registered
in `registry.py` alongside `native` and `swn`. Subclasses `SwnRulesetModule`.

**Inherited unchanged** (the engines are identical):

| Operation | Behavior |
|---|---|
| `stat_modifier` | 3→−2, 4–7→−1, 8–13→0, 14–17→+1, 18→+2 |
| `attack_params` | d20 + attack_bonus + combat_skill + attr mod vs target Armor Class |
| `check_params` | 2d6 + skill + attr mod vs difficulty (6/8/10/12/14) |
| `save_params` | d20 vs `save_base − (level−1) − best-of-attr-pair`. CWN's "16 − level" is arithmetically identical to SWN's existing `15 − (level−1)` (both = 15 at level 1, −1/level). |
| `roll_initiative` | 1d8 + DEX modifier, rolled once, persisted |

**Overridden / added by `cwn`:**

1. **Luck save** — CWN's fourth save category, target `save_base − (level−1)`, no
   attribute modifier. Extend the save category map with `"luck"` (empty attr
   tuple) and special-case the no-attribute path in `save_params`.
2. **`resolve_damage`** — wraps the inherited weapon-damage resolution with the
   Trauma/Shock layer (below).
3. **System Strain** — resource gating hooks (below).

`RulesConfig` gains a `cwn:` config block mirroring the `swn:` shape:
`attribute_map` (required, validated 6:1 — fail loud on a missing canonical
attribute, same as swn), plus `system_strain` config and Trauma defaults.

### Attributes

`ability_score_names` and the `cwn.attribute_map`:

| CWN canonical | Neon flavor | Rationale |
|---|---|---|
| STRENGTH | Brawn | melee, force |
| DEXTERITY | Reflex | speed, initiative, Shoot |
| CONSTITUTION | Body | toughness; **caps System Strain** |
| INTELLIGENCE | Tech | hacking = INT+Program → "Tech" |
| WISDOM | Instinct | street sense, Notice |
| CHARISMA | Cool | presence, Talk/Lead |

The orphaned `Net` and `Edge` attributes retire. Netrunning is no longer an
attribute — it is the Tech (INT) attribute plus the Program skill.

### System Strain (replaces Humanity)

A real resource, CON-bound, not a 0–100 narrative dial:

- **Max = Body (CON) score.** Starts at 0.
- Cyberware install → **permanent** strain (may be fractional; removing cyber
  returns it). Cyber activation / combat pharmaceuticals → **temporary** strain.
- An action that would push strain over max **fails** (can't activate the cyber,
  gain no drug benefit); if forced over by an unavoidable effect → unconscious
  ≥1 hour.
- First aid adds +1 strain per application (caps mid-fight patching).
- **−1 strain per night's rest** (warm, fed, 8 uninterrupted hours).
- The `humanity` resource block and `humanity_tracker` custom rule are **removed**.
  Humanity-referencing tropes are reframed onto strain overload or retired.
- OTEL: `cwn.system_strain.delta` emitted on every change (source, amount,
  new total, max).

### Combat lethality — Trauma & Shock

Neon combat moves from the momentum dial to **HP + Armor Class** on the ablative
`HpPool` (`CreatureCore`, ADR-114 Part 1 — the path `space_opera` already uses):

- Hit → weapon damage die + relevant attr mod, reduced first by armor **Damage
  Soak** (depletes over the fight, refreshes after combat).
- **Trauma:** on a hit with a lethally-intended attack, roll the weapon's Trauma
  Die vs the victim's Trauma Target (6 for an unarmored human). On a Traumatic
  Hit, multiply total damage by the weapon's Trauma Rating (e.g. shotgun ×3).
- **Shock:** a melee weapon with `Shock X/AC` chips X damage on a *miss* against
  a target whose Melee AC ≤ the weapon's Shock rating.
- 0 HP from lethal damage → **Mortal Injury**: dies at end of the 6th round
  unless stabilized (Dex/Heal or Int/Heal check, difficulty 8 + rounds elapsed).
  Recovers at 1 HP + **Frail**.
- 0 HP in a scene where a Traumatic Hit landed → **Major Injury** risk: Physical
  save; on failure roll 1d12 on the Major Injury table (instant death, internal
  damage, brain damage, lost eye/limb, etc.).
- Weapon damage die / Trauma Die / Trauma Target / Trauma Rating / Shock and
  armor AC / Damage Soak are **content** in `inventory.yaml`.
- OTEL: `cwn.trauma.roll` (die, target, rating, traumatic?), `cwn.shock.applied`,
  `cwn.major_injury.roll`. HP deltas continue via the existing `state_patch_hp`.

### Hacking — a CWN-flavored confrontation

Hacking is a confrontation with beats, not a new engine and not a bespoke
minigame (a dogfight-style cyberspace mechanic à la ADR-077 is possible later but
is not needed for fidelity).

- A `net_run` confrontation type. **DC = CWN security level** (private home 7 →
  corp/government black site 12), with situational modifiers (+1 alerted, etc.).
- Beats map to CWN cyberspace **Verbs/actions**, resolved on **Tech (INT) +
  Program**:
  - *Jack In* (entry)
  - *Run Program* (strike — Verb+Subject effect vs security DC)
  - *Spoof / Unlock Barrier* (brace/angle — reduce alert or open a path)
  - *Move Nodes* (push toward the objective)
  - *Jack Out* (push — exit, lose un-extracted data)
- Opponent metric = network **alert / Demon trace**; the CWN "Alert the Network
  ×2" rule is the opponent's win condition. Player metric = objective progress
  (data extracted / device controlled).
- The player never solves a technical puzzle — they state intent, the
  confrontation + narrator resolve. Preserves the Zork-problem advantage and the
  "character is the expert" SOUL note.
- OTEL: `cwn.hacking.security_check` (verb, security level, modifiers, result).

## Content edits (pack YAML)

- **`rules.yaml`** — new `ability_score_names`; `ruleset: cwn` + `cwn:` block
  (`attribute_map`, save config, `system_strain` config, Trauma defaults); remove
  the `humanity` resource; rewire every confrontation beat's `stat_check` to the
  new attribute names; add `attack_bonus` / `combat_skill` to strike beats
  (space_opera precedent); rebuild the net_run confrontation per above; retire the
  momentum `combat` confrontation.
- **`inventory.yaml`** — weapons gain damage die + Trauma Die/Target/Rating +
  Shock; armor gains AC + Damage Soak.
- **`archetypes.yaml` / classes** — neon roles (Solo, Netrunner, Fixer, …) stay
  as flavor; each gets an attack-bonus-by-level chassis and granted combat /
  Program skills so the attack path and hacking have inputs.
- **`tropes.yaml`, `progression.yaml`, `power_tiers.yaml`** — align to CWN skill
  levels and System Strain; drop Humanity hooks.

## Out of scope (YAGNI)

- Full CWN **class / Focus / Edge / Contact** catalogs (faithful module was
  chosen, not a full port).
- Cyberdeck **CPU / Memory / Access** program economy as live engine — deck
  loadout stays narrative/inventory. Possible follow-up.
- Bespoke cyberspace **dogfight minigame** — confrontations suffice.

## Testing & wiring

- `registry` test: `get_ruleset_module("cwn")` resolves to `CwnRulesetModule`;
  unknown slug still fails loud.
- Unit tests: Luck save target math; Trauma Die multiplication; Shock-on-miss
  threshold; System Strain gating (activation refused at max, −1/rest, first-aid
  cost); Major Injury save + table roll.
- **Wiring test** (behavior/OTEL, never source-grep): load the `neon_dystopia`
  pack and assert the bound module is `CwnRulesetModule`, then drive a strike
  beat and assert `cwn.trauma.roll` fires — proves the pack→module binding and
  the damage override are reachable from a production code path.
- OTEL span assertions for `cwn.system_strain.delta`, `cwn.trauma.roll`,
  `cwn.hacking.security_check`.
- A confrontation-drive test for `net_run` end-to-end.

## References

- `docs/superpowers/specs/2026-05-26-swn-module-design.md` — the SWN module this
  subclasses.
- `docs/superpowers/specs/2026-05-26-pluggable-srd-ruleset-modules-design.md` —
  the `RulesetModule` seam (ADR-117).
- `docs/superpowers/specs/2026-05-25-swn-crunch-ablative-hp-design.md` — ablative
  HP substrate (ADR-114) this combat path reuses.
- ADRs: 033 (confrontation engine), 114 (ablative HP), 117 (pluggable rulesets).
- Source: Cities Without Number SRD v1.0, Kevin Crawford (CC0).
