---
parent: 106
---

# Story 106-1 Context

## Title
Equip starting armor at chargen and derive AC from the WWN SRD (ramp lever #1) — Leather Armor rolls into inventory with `equipped:false` so every Warrior fights at unarmored AC 10; equip the rolled armor and recompute `armor_class` from the WWN SRD armor entry (weapons already auto-equip; gap is armor-specific), with OTEL proving opponent reprisals roll vs the higher AC

## Metadata
- **Story ID:** 106-1
- **Type:** bug
- **Points:** 3
- **Priority:** p1
- **Workflow:** tdd
- **Repos:** server, content
- **Epic:** 106 — WWN combat hardening for beneath_sunden (fair ramp, ruleset-bleed remediation, narration truth)

## Problem

In the 2026-06-13 single-player combat playtest of `caverns_and_claudes/beneath_sunden`
(WWN ruleset, ADR-117), **every Warrior fought at the unarmored base AC 10** even though
the chargen kit hands each one Leather Armor. The armor sits in inventory `equipped:false`
and contributes nothing. Confirmed systematic across all three develop-era Warriors
(sq-playtest-pingpong 2026-06-13, lines 42–55):

- Zeppo `c33733e9`: `armor_class: 10`, Leather Armor **`equipped: false`**
- Chico `bf7e2e2f`: `armor_class: 10`, Leather Armor **`equipped: false`**
- Gummo `0805bbe7`: `armor_class: 10`, Leather Armor **`equipped: false`**

**Why it's the lethality driver.** Opponent reprisals roll **vs `target_ac: 10`** all
session (OTEL `ENCOUNTER_OPPONENT_ATTACK`) — against an unarmored target. At AC 10 the
dungeon creatures (`d20+2`) hit on **9+ (~65%)**, and this session landed **8 of 8**
reprisals; 1-of-5 Marx-brothers Warriors survived. WWN leather ≈ **AC 13**: the same
creatures would need **12+ (~45%)** — a large survivability swing with zero change to
damage. Operator (Keith) confirmed the diagnosis on 2026-06-13 ("yes likely armor is
ignored as well, good catch"). This is **easy-ramp lever #1** of Epic 106.

**The gap is armor-specific.** Weapons reach the sheet equipped (Iron Mace / Short Sword /
Long Sword all `equipped:true` in the saves), so the symptom is not "nothing equips" — it
is "the kit-roll path that produces armor never flips `equipped`, and nothing recomputes
`armor_class` from it."

### Root cause (code-grounded)

The kit-roll loop that materializes `class_kit` items is the single seam. Every kit slot —
weapon, **armor**, light, consumable, utility — is appended with a hardcoded
`"equipped": False`:

- `sidequest-server/sidequest/game/builder.py:2539-2576` — the `class_kit` /
  `random_table` roll loop. The appended item dict hardcodes **`"equipped": False`** at
  **builder.py:2570**. `warrior_kit.armor` resolves to `leather_armor`
  (sidequest-content `equipment_tables.yaml:56-58`), so Leather Armor lands `equipped:false`.
- By contrast, scene `item_hint` items are appended with **`"equipped": True`**
  (**builder.py:2497**) — this is the asymmetry the pingpong saw: hint-path weapons look
  equipped, kit-path armor does not. (Note: kit-path *weapons* are also `equipped:false` at
  builder.py:2570; the observed equipped weapons came via the `item_hint` path. Either way,
  no step equips kit-rolled **armor**.)

The AC the reprisal rolls against:

- `sidequest-server/sidequest/game/creature_core.py:123` — `armor_class: int = 10`
  (SWN/WWN ascending AC; unarmored = 10; comment already says "Seeded from content armor").
- `sidequest-server/sidequest/server/dispatch/dice.py:1636` —
  `target_ac = int(player_core.armor_class)` feeds the opponent reprisal
  (`resolve_opponent_attack`). **Nothing ever raises `core.armor_class` above the 10
  default for a PC**, because no step reads an equipped armor item and recomputes it.

The catalog already carries the field to derive from — `CatalogItem.armor_class`
(`sidequest-server/sidequest/genre/models/inventory.py:164` — "SWN ascending AC the attack
rolls against, distinct from `mitigation` soak") — and `item_catalog_resolution.py:85-86`
already copies `item.armor_class` onto a gained item dict. **But the
`caverns_and_claudes/inventory.yaml` armor entries declare NO `armor_class` field**
(leather_armor at lines 222-232, chain_shirt, shield_wood, helmet_iron — none have it).
So there is a **two-sided gap**: the engine never equips/derives, and the content has no
SRD value to derive from.

### Why `apply_starting_loadout` is not the fix site

The chargen-confirm wire (`chargen_mixin.py:1239` → `chargen_loadout.apply_starting_loadout`)
handles `starting_equipment[class]` from inventory.yaml — but for `caverns_and_claudes`
that block only lists **Delver** (inventory.yaml:396-407). The WWN Warrior gets its armor
from the **kit-roll** path (`equipment_tables.yaml` `warrior_kit`), not `starting_equipment`.
The fix must cover the kit-roll-produced armor, not just the `starting_equipment` dispatch.

## Technical Approach

Two coordinated changes (server + content), TDD-first.

1. **Content (sidequest-content):** add the WWN-SRD `armor_class` to the
   `caverns_and_claudes/inventory.yaml` armor entries (leather_armor first — the playtest
   subject). **Source the value from the Worlds Without Number SRD armor table, not an
   invented number** (standing ruling 2026-06-13, `.pennyfarthing/sidecars/gm-decisions.md`:
   "WWN-bound mechanical values come from the WWN SRD"; cite which SRD row in the PR). WWN
   leather is AC 13 (per the pingpong's WWN-leather ≈ AC 13). The field name is `armor_class`
   (matches `CatalogItem.armor_class`).

2. **Server (sidequest-server):** introduce a deterministic post-build chargen step that
   (a) **equips** the kit-rolled armor and (b) **recomputes `character.core.armor_class`**
   from the equipped armor's catalog `armor_class`. The natural home is the chargen-confirm
   wire alongside `apply_starting_loadout` (`chargen_mixin.py:1239`), AFTER the loadout/dedup
   pass so the full inventory (kit-roll + starting_equipment) is present. Mirror the existing
   `equip` subsystem's resolve semantics (`agents/subsystems/equip.py`) — flip `equipped`,
   leave `state="Carried"` — but driven by category=`armor` at chargen rather than by a
   player utterance.

   - **No invented AC math.** `armor_class` comes from the equipped armor item's catalog
     `armor_class` field. Unarmored stays 10 (creature_core default). If multiple armor
     pieces are equipped (torso + shield + helm in `warrior_kit.armor`), the design must
     state the WWN-faithful combination rule (WWN uses best-armor AC, not additive — torso
     armor sets AC, a shield grants a flat bonus); resolve from the SRD, not by guessing.
   - **No silent fallback.** If a kit armor item has no `armor_class` in the catalog, fail
     loud (warn/error span) rather than silently leaving AC at 10 — the content gap is the
     other half of this bug and must surface at chargen, not be masked.

3. **OTEL (the gate, per CLAUDE.md OTEL Observability Principle).** Emit a chargen
   armor-derivation span recording: armor item id, its catalog `armor_class`, AC before
   (10) and after, and that `equipped` flipped true. Reuse the established
   inventory/equip span family (`telemetry/spans/inventory.py` —
   `SPAN_EQUIP_RESOLVED` / `equip_resolved_span` at lines 183/219, registered in
   `SPAN_ROUTES`) or add a sibling `chargen.armor_equipped` span in the same module. The
   acceptance gate is then provable end-to-end: fresh Warrior snapshot shows
   `armor_class > 10` with Leather Armor `equipped:true`, AND the opponent reprisal's
   `ENCOUNTER_OPPONENT_ATTACK` span shows `target_ac` = the higher value (dice.py:1636
   reads `core.armor_class`, so this follows automatically once the recompute lands).

## Scope

- **In scope:** equipping the kit-rolled (and starting_equipment) armor at chargen;
  recomputing `core.armor_class` from the equipped armor's SRD `armor_class`; adding the
  WWN-SRD `armor_class` to `caverns_and_claudes/inventory.yaml` armor entries (leather_armor
  mandatory; chain_shirt/shield_wood/helmet_iron if the multi-piece rule needs them); the
  OTEL span proving the derivation + that reprisals roll vs the higher AC; loud-fail on a
  kit armor item missing its catalog `armor_class`.
- **Out of scope:** the unconditional per-beat reprisal model and defensive-beat mitigation
  (106-2); native combat-mechanic gating + XP scale (106-3); consumable/heal-effect wiring
  (106-4); death-state coherence (106-5); narration-truth guardrails (106-6); `mitigation`
  (SWN soak) — distinct from `armor_class` and not this bug; player-facing AC display/UI
  polish; armor for non-WWN packs (this story targets the beneath_sunden / WWN repro;
  note any cross-pack armor-AC gaps as follow-ups, do not expand scope).

## Acceptance Criteria

1. **Armor equips at chargen:** a freshly rolled Warrior in `caverns_and_claudes/beneath_sunden`
   ships with Leather Armor **`equipped: true`** (behavior test on the chargen-confirm path —
   the kit-roll armor is no longer `equipped:false`).
2. **AC derived from the WWN SRD, not invented:** that Warrior's `core.armor_class` equals the
   WWN-SRD leather value (13), sourced from the catalog `armor_class` on the inventory.yaml
   armor entry — **> 10**, never a hardcoded engine constant. (Test asserts the value flows
   from content, e.g. mutate the catalog `armor_class` and the derived AC follows.)
3. **Reprisals roll vs the higher AC:** the opponent reprisal reads the recomputed AC
   (dice.py:1636 `target_ac = int(player_core.armor_class)`); the `ENCOUNTER_OPPONENT_ATTACK`
   span shows `target_ac` = the equipped value (13), not 10.
4. **No silent fallback:** a kit armor item with no catalog `armor_class` fails loud
   (warn/error span) and does NOT silently leave the PC at AC 10.
5. **No regression:** weapons still reach the sheet equipped; unarmored classes / classes
   with no kit armor stay at AC 10; the 45-12 dedup pass and `apply_starting_loadout`
   behavior are unchanged.

---

## Business Context

This is **easy-ramp survivability lever #1** for Epic 106 — the single biggest reason L1
`beneath_sunden` is a meat-grinder (1-of-5 Warriors survived the 2026-06-13 dive, all
fighting at unarmored AC 10 against `d20+2` creatures hitting ~65%). Fixing it swings
opponent hit chance from ~65% to ~45% with zero change to damage, making the dungeon a
**fair, WWN-faithful ramp** instead of a coin-flip slaughter.

Per CLAUDE.md, the primary audience is **Keith's playgroup**, and `beneath_sunden` is the
live WWN meat-grinder they are actually playing. Keith confirmed the bug in person. It
serves the whole table (survivability is universal) and especially the **mechanics-first**
players (Sebastien, Jade) who want mechanical resolution legible — an armor value that
silently does nothing is exactly the "convincing narration with no mechanical backing" the
project exists to eliminate. It also stands for the broader Epic-106 theme that **WWN-bound
values must come from the WWN SRD**, not from native/legacy defaults or invented numbers.

## Technical Guardrails

- **Confirmed seams** (cite file:line in the PR):
  - `sidequest-server/sidequest/game/builder.py:2570` — kit-roll appends armor `equipped:false`
    (the gap); contrast `builder.py:2497` (item_hint path → `equipped:true`).
  - `sidequest-server/sidequest/game/creature_core.py:123` — `armor_class: int = 10` default.
  - `sidequest-server/sidequest/server/dispatch/dice.py:1636` —
    `target_ac = int(player_core.armor_class)` (reprisal reads this; raising AC fixes the symptom).
  - `sidequest-server/sidequest/genre/models/inventory.py:164` — `CatalogItem.armor_class` field
    (already exists; distinct from `mitigation` soak at line 163).
  - `sidequest-server/sidequest/game/item_catalog_resolution.py:85-86` — already copies
    `item.armor_class` onto gained items (reuse this shape).
  - `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py:1239` — chargen-confirm
    wire (call site for `apply_starting_loadout`; equip-armor step belongs here, after it).
  - `sidequest-server/sidequest/agents/subsystems/equip.py` — equip-resolve semantics to mirror
    (flip `equipped`, keep `state="Carried"`).
  - `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml:222-232` — leather_armor
    entry (no `armor_class` today); `equipment_tables.yaml:56-58` — `warrior_kit.armor` → leather_armor.
- **Source AC from the WWN SRD, no invented numbers.** Standing ruling 2026-06-13
  (`.pennyfarthing/sidecars/gm-decisions.md`): WWN-bound mechanical values come from the Worlds
  Without Number SRD. Add `armor_class` to the content armor entries from the SRD armor table
  (leather = 13); cite the SRD row in the content PR.
- **No silent fallback** (CLAUDE.md): a kit armor item missing its catalog `armor_class` must
  fail loud at chargen, not leave AC silently at 10. The recompute reads content, not a
  hardcoded engine constant — derive, don't bake.
- **OTEL is the gate** (CLAUDE.md OTEL Observability Principle): emit a chargen armor-derivation
  span (reuse `telemetry/spans/inventory.py` equip family / add `chargen.armor_equipped`) so the
  GM panel can confirm the derivation fired and reprisals roll vs the higher AC. Prefer OTEL
  span assertions + fixture-driven behavior tests over source-text wiring tests
  (sidequest-server CLAUDE.md "No Source-Text Wiring Tests").
- **Two-PR split** (`server,content`): server code → sidequest-server `develop`; content YAML →
  sidequest-content `develop`. Keep them coordinated (the AC test depends on the content value).

## Scope Boundaries

In scope: equip kit-rolled/starting armor at chargen; recompute `core.armor_class` from the
equipped armor's SRD `armor_class`; add WWN-SRD `armor_class` to `caverns_and_claudes`
inventory armor entries; OTEL proof; loud-fail on missing catalog `armor_class`.

Out of scope: reprisal model & defensive mitigation (106-2); native-mechanic gating + XP
scale (106-3); consumable/heal wiring (106-4); death-state coherence (106-5); narration-truth
(106-6); `mitigation`/SWN soak; AC display UI polish; armor-AC for non-WWN packs (note as
follow-ups, do not expand).

## AC Context

1. Fresh Warrior ships Leather Armor `equipped: true` (behavior test on chargen-confirm).
2. `core.armor_class` = WWN-SRD leather value (13), flowing from content `armor_class`
   (> 10, never a hardcoded constant; mutate-content-and-AC-follows test).
3. `ENCOUNTER_OPPONENT_ATTACK` span shows `target_ac` = the equipped value (13), not 10
   (dice.py:1636 reads `core.armor_class`).
4. Kit armor item with no catalog `armor_class` fails loud (warn/error span); no silent AC 10.
5. No regression: weapons stay equipped; unarmored/no-kit-armor classes stay at AC 10;
   45-12 dedup + `apply_starting_loadout` unchanged.

OTEL proof (the gate): a chargen armor-derivation span records armor item id, catalog
`armor_class`, AC before/after, and `equipped` flip; the opponent-reprisal
`ENCOUNTER_OPPONENT_ATTACK` span shows the higher `target_ac`. Both are GM-panel-visible.

## Dependencies

- **No code dependency on sibling 106 stories** — this is the standalone lever. 106-2 (reprisal
  mitigation) operates on the same reprisal path (dice.py) but on the to-hit/damage side, not AC;
  coordinate to avoid merge churn in `dice.py`.
- **Content ↔ server coupling within this story:** the AC-derivation tests depend on the
  inventory.yaml `armor_class` value — land/coordinate both PRs together.
- **WWN SRD** is the value oracle (`.pennyfarthing/sidecars/gm-decisions.md`, 2026-06-13). If the
  SRD is genuinely silent on a multi-piece (torso + shield + helm) AC combination rule, escalate
  to Keith rather than inventing.
