# Road Warrior → Cities Without Number: Two-Tier Rig Combat

**Date:** 2026-06-04
**Status:** Draft (brainstorming) — epic-level design; Plan 1 specified for implementation
**Author:** GM (Game Master)
**Sources of truth (faithful port, do not redesign):**
- Stars Without Number: Revised (Free Edition) — *Space Combat*, pp. 114–119
- Cities Without Number SRD 1.0 — *Vehicle Combat* §2.4.8, *Chases and Pursuit* §2.6.0–2.6.2
- Worlds Without Number SRD 1.0 — reference only (shared WN chassis)

---

## 1. Problem

`road_warrior` runs the **`native` dial engine** (no `ruleset:` line). Its entire rig
identity — Rig Composure, the two-pool damage model, the chase system, crash events — is
**prose content with no mechanical backing**. The `rules.yaml` spec literally points at "a
backlog story for RigComposurePool wiring." The result is exactly the failure mode the
GM panel exists to catch: a charmed-prose narrator improvising vehicular combat with
nothing underneath. There are no `confrontation.*` / `rig_pool.*` spans firing in real
play because no confrontation is bound to a ruleset that uses them.

Meanwhile the engine already contains most of the substrate, dormant:
- `RigComposurePool` (`sidequest/game/rig_composure_pool.py`) — a vessel-attached ablative
  pool, character+chassis bound, with `rig_pool.delta` / `rig_pool.zero_crossing` spans.
- `rig_crash.py`, `vessel_tags.py`, `telemetry/spans/rig.py`, `chargen_loadout.py` wiring.
- The `cwn` ruleset module (`CwnRulesetModule(SwnRulesetModule)`) — personal combat:
  `hp_depletion`, Shock/Trauma/Mortal/Major Injury, hacking.
- SWN `ship_attack_params` (to-hit math for crewed vessels) reachable via the subclass.

The gap is **binding and wiring**, plus one genuinely net-new primitive (a crew-seat
vessel for the War Rig). This is the "Don't Reinvent — Wire Up What Exists" principle.

## 2. Goal

Bind `road_warrior` to the `cwn` ruleset and give rig combat real mechanical backing, in
two tiers the playgroup explicitly chose:
- **Solo rig (default)** — each PC drives their own rig; rig = personal vessel with its own
  AC/Armor/Hull (Composure). CWN Vehicle Combat is the native substrate.
- **War Rig (special)** — the party shares one crewed vessel; each PC mans a station with a
  concurrent verb; one shared Hull. SWN Space Combat is the substrate. This is the literal
  realization of the SOUL **Guitar Solo / wider-action** principle.

Driver-on-foot combat becomes standard CWN personal combat (ablative HP).

## 3. Decisions (locked with Keith, 2026-06-04)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Both tiers** — solo rig default, War Rig special | Playgroup is multiplayer; War Rig = Guitar-Solo ideal; solo reuses the existing single-char pool |
| D2 | **Driver = full ablative HP**, Driver Edge (ADR-078) removed | SWN-crunch / ablative-HP reintroduction mandate; one combat model engine-wide; space_opera/neon_dystopia precedent |
| D3 | **Adopt the standard CWN six** (STR/DEX/CON/INT/WIS/CHA) on the sheet; drop the flavor names (Grip/Iron/Nerve/Scrap/Road Sense/Swagger) | Zero attribute-map risk; "a port is a port." Consequence: remap every flavor-name reference in content (see §6.3) |
| D4 | **Faithful SRD port**, not a redesign | Keith handed over the three SRDs; mechanics are lifted verbatim and scaled, not reinvented |

## 4. Source mechanics (extracted, so the implementer need not re-read the PDFs)

### 4.1 CWN Vehicle Combat (§2.4.8) — the solo-rig substrate
- Each vehicle is **its own side** for initiative; all passengers act on its turn.
- Driver spends a **Main Action each round maintaining control**; if they can't and nobody
  grabs the wheel → **Luck save or crash** (success = safe halt).
- **Vehicle AC**: applies to melee & ranged attacks against it. Stationary = **−4**; moving
  = **+ driver's Drive skill** to AC. Vehicles may have an **Armor** rating subtracted from
  all damage.
- Each mounted weapon needs a **gunner** spending a Main Action; firing personal weapons out
  the window while moving = **−4**.
- **Vehicle destruction** (§2.4.8.1): 0 HP or crash → destroyed; occupants take damage as if
  hit by whatever killed the vehicle, **Luck save for half**.
- **Vehicle crashes** (§2.4.8.2): at combat speed → each passenger rolls **Physical save AND
  Luck save**. Both pass = unscathed; fail one = half max HP damage (may be Mortal); fail
  both = Mortally Wounded + Major Injury if survived.
- **Traumatic Hits** (§2.4.8.3): each vehicle type has a **Trauma Target ≥ 6**.
- **Ramming** (§2.4.8.4): opposed **Dex/Drive vs Dex/Drive** (or Dex/Exert for a person).
  Win → target takes the **vehicle's max HP** in damage, **Trauma 1d12/×3**; ramming vehicle
  **also takes damage** as if rammed back. Human-sized ram only in confined areas; target
  gets an Evasion save.

### 4.2 CWN Vehicle Chases (§2.6.2) — the chase substrate
- Fleeing driver rolls **Drive (usually +Dex)** = the **pace**. Passengers may hinder
  pursuit (skill checks, +1 each up to +3).
- Each pursuing vehicle rolls **Dex/Drive** vs the pace, modified by situation:
  - can't directly see the pursued −2 · pursuer flying / pursued not +3 · pursued flying /
    pursuer not −3 · spotter relaying target +1 · local-terrain knowledge −2..+2 ·
    half-hearted pursuit −1 · enraged/vengeful +1.
- Beat the pace → catch up (→ vehicle combat). Tie/under → fall behind / escape.

### 4.3 SWN Space Combat (pp. 114–119) — the War Rig substrate
- **Initiative**: each vessel rolls **1d8 + pilot Int/Dex mod**; PCs win ties; not rerolled.
- **Departments** (→ rig stations): **bridge** (pilot: escape/pursue/evasive),
  **gunnery** (fire weapons / target systems), **engineering** (damage control / boost
  engines / emergency repairs), **comms** (ECM / sensor ghost / crash systems), **captain**
  (support dept / into the fire / keep it together).
- **Command Points (CP)**: vessel starts each turn at 0. Generated by **Do Your Duty**
  (+1), **Above and Beyond** (+skill+1, exclusive), captain **Support Department** (−2 cost
  to one dept action). Spent on actions. Unspent CP lost at round end. **NPC ships** get a
  flat CP pool by crew quality (fighters/civilian 4, military/pirate 5, elite 6–7).
- **Single-seat fighter** = lone crew holds all five departments: takes **one** department's
  action that round; the other four auto-**Do Your Duty** → **4 CP**. *This is the solo rig
  expressed in the same system.*
- **Attacks**: gunner rolls **BAB + better(Int,Dex) + Shoot** (Pilot replaces Shoot on a
  fighter-class hull) vs target **AC**. Hit → damage − Armor (AP negates). **Target Systems**:
  −4 to hit, half damage, disables a system on any leak-through.
- **Hull → 0**: fighter-class instantly destroyed; larger hulls mortally damaged (explode
  2d6 min unless Int/Fix DC 10 → burnt-out hulk).
- **Crises** (accept instead of a hit; one voluntary/round): d10 table — Armor Loss,
  Cargo Loss, Crew Lost, Engine Lock, Fuel Bleed, Haywire Systems, Hull Breach, System
  Damage, Target Decalibration, VIP Imperiled; **continuing** vs **acute**. **Deal With a
  Crisis** general action = relevant skill vs DC 10±2.

### 4.4 The mapping

| SWN/CWN source | Road Warrior |
|---|---|
| Vehicle / fighter hull HP | **Rig Composure** (existing `RigComposurePool`) |
| Vehicle AC (+Drive moving, −4 stationary) | Rig AC |
| Bridge / pilot | **Driver** (Wheelman) — the chase |
| Gunnery | **Gunner** — mounted weapons (mount_slots) |
| Engineering (damage control / boost) | **Wrench** (Grease Monkey) — repair Composure, +Speed |
| Comms (ECM / sensor ghost) | **Spotter / Nav** — road sense, jamming |
| Captain (support / into the fire) | **Road Boss** — Command Points |
| Command Points | rig crew-coordination resource (name TBD: "Calls"/"Hollers") |
| Crisis table | **rig crises** (existing `rig_damage_tiers` / `rig_crash`) |
| Single-seat fighter | **solo rig** |
| Crash damage to occupants / Mortal | driver ablative HP + Trauma/Major Injury (CWN) |

## 5. Epic decomposition (each is its own spec → plan → PR cycle)

This is a multi-plan epic. Plans are ordered by dependency; **Plan 1 is specified in §6**,
the rest are scoped here and get their own specs when reached.

- **Plan 1 — CWN binding + driver combat** *(this spec, §6)*. `ruleset: cwn`; standard six;
  Driver Edge → ablative HP; Shock/Trauma/Mortal/Major-Injury reachable; classes→CWN
  class+foci; **calibration-test migration**. The de-risking foundation; follows the
  documented Without-Number wiring checklist.
- **Plan 2 — Solo rig two-pool vehicle combat.** Wire `RigComposurePool`/`rig_crash` into a
  real confrontation: vehicle AC (+Drive moving), Armor, ramming (opposed Dex/Drive), crash
  damage to occupants. **Net-new two-pool resolution** (hull→0 = crash → dismounted → driver
  HP) — a new `WinCondition` variant or a beat-application branch. OTEL: `rig_pool.*` spans
  already exist; assert they fire.
- **Plan 3 — Vehicle chase confrontation.** CWN pace/pursuit (§4.2) as the chase encounter
  type; road_warrior's Opening/Pursuit/Escalation/Crisis/Resolution beats map onto it; closes
  into Plan 2 combat when vehicles converge.
- **Plan 4 — War Rig (crewed vessel).** SWN departments + Command Points + Crisis table; the
  **net-new crew-seat primitive** (`EncounterActor` has no seat field today): multi-PC, one
  shared Hull, concurrent verbs per round. The Guitar-Solo wider-action. Depends on 1–2.
  *Open architectural fork for that spec:* reuse the ADR-077 dogfight sealed-letter infra,
  the `beat_selection` confrontation path, or a new crew-seat confrontation type.
- **Plan 5 — Content remap + calibration + playtest.** Vessel stat blocks in `inventory.yaml`,
  mount_slots → CWN vehicle weapons, archetype/lethality calibration, OTEL playtest pass.

## 6. Plan 1 — CWN binding + driver combat (implementable)

**Repo:** `sidequest-server` (engine/calibration) + `sidequest-content` (road_warrior YAML).
**Pattern precedent:** space_opera→SWN (#468/#469, #267) and neon_dystopia→CWN bindings.

### 6.1 Content changes — `genre_packs/road_warrior/rules.yaml`
- Add `ruleset: cwn`.
- Replace `ability_score_names` (Grip/Iron/Nerve/Scrap/Road Sense/Swagger) with the standard
  six: STR, DEX, CON, INT, WIS, CHA.
- **Remove** the `edge_config` block and Driver Edge framing; the driver is now an ablative-HP
  CWN character. Keep `stat_display_fields` for fuel/injuries/dismounted (character-side
  trackers survive).
- Add a `combat` confrontation with `win_condition: hp_depletion` and
  `opponent_default_stats` carrying **all six** ability scores + `hp` + `armor_class`
  (per the documented "needs ALL SIX ability scores for saves" gotcha).
- Leave the rig/composure/chase prose **in place but inert** for Plan 1 — Plans 2–4 wire it.
  Flag clearly that it is not yet mechanically live (no silent implication of backing).

### 6.2 Engine changes — `sidequest-server`
- Confirm `road_warrior` loads through `get_ruleset_module("cwn")` (fail-loud at load).
- Apply the **Without-Number module wiring checklist** (PR #520 lessons): spans `__init__`
  re-export, `dice.py` downed-seam guard + `_physical_save_target_for` isinstance handling,
  OTEL span-assertion tests. Most cwn seams already exist (neon_dystopia); verify, don't
  rebuild.
- **Calibration migration** (documented trap): binding to `hp_depletion` regresses
  `test_road_warrior_pack_loads_with_dual_dial_schema` and the `COMBAT_PACKS` calibration
  set. Fix per the space_opera precedent — filter `dial_threshold`, drop road_warrior from
  `COMBAT_PACKS`. **Do not** treat these as pre-existing failures.

### 6.3 Content remap consequence of D3 (standard six)
Every flavor-name reference must move to the standard six. Known sites to sweep:
- `injury_system` stat penalties ("Grip −1", "Road Sense −1", "Iron −1", "Scrap −1") → DEX/WIS/STR/INT etc.
- `archetypes.yaml`, `classes.yaml`, `char_creation.yaml`, `power_tiers.yaml` — any stat
  references.
- Proposed flavor→stat intent (narrator can still *call* DEX "grip" in prose; the sheet uses
  the standard label): Grip→DEX, Iron→STR, Nerve→WIS, Scrap→INT, Road Sense→CON?, Swagger→CHA.
  The Nerve/Road-Sense vs WIS/CON assignment is a calibration detail to settle during remap.
- Classes (Wheelman/Wrecker/Grease Monkey/War Rider/Chrome Saint/Road Preacher) → CWN
  class chassis (Warrior/Expert/Adventurer + Edge) + Foci. Mechanical mapping is Keith's
  crunch call; flavor names stay.

### 6.4 OTEL / wiring test (mandatory — the GM panel is the lie detector)
- Seed a road_warrior combat encounter; run a turn through narrator context build; assert the
  `cwn` personal-combat spans fire (attack resolution, Shock/Trauma) and HP depletes on the
  ablative pool — not improvised prose.
- At least one integration test proving the bound ruleset is reachable from a production turn
  path, not just unit-tested in isolation.

## 7. Non-goals (Plan 1)
- No rig/vehicle confrontation wiring (Plan 2), no chase confrontation (Plan 3), no crew-seat
  War Rig (Plan 4). Plan 1 stops at: the pack is a working CWN pack with ablative-HP driver
  combat and a clean foundation for the rig layers.
- No new vessel UI. No magic changes (`magic_level: none` stays; the rig-as-item-magic prose
  is untouched flavor).

## 8. Risks
- **Calibration-test false alarms** — the hp_depletion migration regresses two tests by
  design; the fix is documented but easy to misread as a regression. Gate on the FULL suite
  with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set; record the baseline failure
  list first.
- **Content remap breadth** (D3) — adopting the standard six touches more content files than a
  pure `ruleset:` flip; an attribute_map would have been narrower. Accepted for zero mapping
  risk. Sweep must be exhaustive or the narrator will reference dead stat names.
- **Dormant-prose honesty** — the rig/chase prose stays in `rules.yaml` for Plans 2–4 but is
  not yet live; it must be flagged so nobody (or no narrator prompt) implies mechanical
  backing that isn't there.
