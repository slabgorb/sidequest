# Ashes Without Number → Mutant Wasteland: The Fourth Sister Module

**Date:** 2026-06-05
**Status:** Draft (brainstorming) — epic-level design; Plan 1 specified for implementation
**Author:** GM (Game Master), brainstorming session with Keith
**Lineage:** continues `swn` → `wwn` → `cwn` → **`awn`**. This is the next application of the
established pluggable-SRD pattern (ADR-117 / `2026-05-26-pluggable-srd-ruleset-modules-design.md`),
**not** new-from-scratch work. Direct precedents:
- `2026-05-28-neon-cwn-ruleset-design.md` — the CWN module (CWN subclasses SWN; AWN subclasses CWN)
- `2026-06-04-road-warrior-cwn-rig-combat-design.md` — an existing genre pack bound to a sister
  module + its signature genre layer. **AWN follows this spec's shape verbatim.**
- `2026-05-25-swn-crunch-ablative-hp-design.md` — the ablative-HP mandate this realizes for `mutant_wasteland`

**Source of truth (faithful port, do not redesign):**
- *Ashes Without Number: Free Edition* — Kevin Crawford / Sine Nomine, 2025. Local PDF:
  `~/Documents/DriveThruRPG/Sine Nomine Publishing/Ashes Without Number_ Free Edition/AshesWithoutNumber_FreeVersion_071025.pdf`
  (PDF page index = printed page + 4). Key pages cited inline below.

---

## 1. Problem

`mutant_wasteland` runs the **`native` dial engine** (no `ruleset:` line). Its combat is the
"Wasteland Brawl" confrontation — a **momentum-to-7** narrative metric with no lethality
substrate underneath. Damage is prose; there is no HP, no Shock, no Trauma, no death state. This
is precisely the absence the two mechanics-first players — **Sebastien and Jade** — named after
the broken-engine `coyote_star` session: a charmed narrator improvising combat with nothing
mechanical underneath, and no `confrontation.*` spans firing because no confrontation is bound to
a ruleset that emits them.

Meanwhile the engine already contains AWN's entire combat substrate, **fully built as CWN**.
*Ashes Without Number* is the post-apocalyptic sister of *Cities Without Number*: its System
Quick Reference Sheet (printed p.37) confirms AWN combat is CWN's resolution verbatim —

| AWN mechanic (printed pages) | Already in the engine as… |
|---|---|
| d20 + attack bonus + skill + attr-mod vs AC; nat-1 miss, nat-20 hit (p.41) | `SwnRulesetModule.attack_params` |
| 2d6 + skill + attr-mod vs difficulty 6/8/10/12/14 (p.39) | `SwnRulesetModule.check_params` |
| Saves: Physical / Evasion / Mental / **Luck**, d20 ≥ target = 15−(level−1) (p.38) | `CwnRulesetModule.save_params` (Luck included) |
| 1d8 + best Dex group initiative, rolled once (p.41) | `SwnRulesetModule.roll_initiative` |
| **Shock** chip damage on a miss vs low AC; shields negate first (p.41) | `CwnRulesetModule.resolve_shock` |
| **Trauma Die** vs Trauma Target 6 → multiply damage (p.48) | `CwnRulesetModule.resolve_trauma` |
| **System Strain** pool, max = CON, −1/night (p.52) | `CwnRulesetModule.apply_system_strain` |
| **Mortal Injury** (0 HP → die in 6 rounds, stabilize diff 8) + **Major Injury** d12 table (p.52–53) | `CwnRulesetModule.resolve_downed` + `lethality.major_injury_entry` |
| Creature stat-line (HD, AC, Atk `+Nxk`, Save = 15−½HD, Morale) (p.205–206) | existing Without-Number creature schema |

The gap is **binding and wiring** for the combat foundation, then **genre layers** (Mutations,
Radiation, etc.) authored on top — exactly as road_warrior bound CWN and layered rig combat. This
is the "Don't Reinvent — Wire Up What Exists" principle.

## 2. Goal

Make `mutant_wasteland` a faithful AWN pack:

1. **Foundation (Plan 1):** bind it to a thin **`awn`** ruleset module so personal combat resolves
   with real ablative HP, Shock, Trauma, Mortal/Major Injury, and the four saves — the crunch
   Sebastien and Jade asked for, visible on the sheet and in the dice overlay.
2. **Genre identity (Plans 2+):** layer AWN's post-apoc subsystems — **Mutations** (the marquee),
   Radiation, Disease, Stress/Addiction, the survival hexcrawl, Creatures of the Wastes, and
   Enclaves — each as its own spec → plan → PR, foundation-first.

## 3. Decisions (locked with Keith, 2026-06-05)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Full faithful port** of AWN, decomposed into sub-projects | Keith chose the complete port over a thin slice; each subsystem is its own spec/plan/PR cycle |
| D2 | **Foundation-first** build order | Plan 1 (ruleset binding) de-risks and unblocks every genre layer; mutant_wasteland is playable on `awn` ASAP, then identity layers in |
| D3 | **Thin `awn` module** — `AwnRulesetModule(CwnRulesetModule)`, slug `"awn"` | AWN combat == CWN; the subclass inherits everything and exists for the honest slug (a mutant game is not "Cities Without Number") and a home for any future AWN-only ruleset hook. Mild, deliberate break from road_warrior's reuse-`cwn` precedent |
| D4 | **Adopt the standard six** (STR/DEX/CON/INT/WIS/CHA); drop the flavor names Brawn/Reflexes/Toughness/Wits/Instinct/Presence | AWN natively uses the standard six; zero attribute-map risk; "a port is a port." Narrator may still *call* DEX "reflexes" in prose. Consequence: sweep every content file (see §6.3). Follows road_warrior D3 |
| D5 | **Mutations = bespoke `MutationPlugin`**, not the MagicPlugin/ADR-126 seam | AWN's MP economy + System-Strain-coupled powers + random tables don't fit the spell abstraction cleanly; a dedicated subsystem is the honest fit. (Plan 2 reconciles with the pack's existing `magic.yaml` framing — see §5.2 / §7) |
| D6 | **Faithful SRD port**, not a redesign | Mechanics are lifted from the AWN Free Edition and scaled, not reinvented |

## 4. Source mechanics — combat foundation (extracted so the implementer need not re-read the PDF)

AWN personal combat is CWN. Plan 1 carries **no new combat math** — it binds the existing CWN
resolution. The numbers the `awn` config must carry (all already CWN defaults):

- **`unarmored_ac` = 10**, **`save_base` = 15** (target = 15 − (level−1)); difficulty ladder
  6/8/10/12/14 (p.37–39).
- **Trauma:** `default_trauma_target` = 6, `mortal_injury_rounds` = 6, `major_injury_save` =
  `"physical"` (p.48, p.52). Per-weapon Trauma Die/Rating and Shock live on weapon content
  (`DamageSpec`), authored in Plan that fattens `inventory.yaml`.
- **System Strain:** `max_source` = `CONSTITUTION`, `rest_recovery_per_night` = 1,
  `first_aid_cost` = 1 (p.52). AWN's strain *sources* differ from CWN (mutations / stims /
  radiation / privation rather than cyberware) but the **pool mechanic is identical** — those
  sources are added by later genre-layer plans, not Plan 1.
- **No hacking.** AWN has the `Program` skill but no cyberspace net-run ladder. `AwnConfig`
  leaves `hacking = None` (CwnConfig default); mutant_wasteland never opens a `net_run`, so
  the inherited `resolve_hacking` is dormant, never called. Not a reason to diverge the module.

## 5. Source mechanics — the genre layers (shape only; each gets its own spec when reached)

Extracted shapes so the epic decomposition is grounded. **No sister-system analog** flagged
where the engine has nothing to lean on.

### 5.1 Mutations (marquee — Plan 2) — *net-new, no analog*
- **MP economy** (p.16): Mutant Edge +2 MP, Mutation Acceleration +2, each negative mutation
  +2 (max 3), concealable Stigma −1; spend: random positive −1, pick-any −3, two-same-category −3.
- **Stigma** (p.17): cosmetic; d6 body-part × d6 nature × d12 flavor tables.
- **Negative mutations** (p.18): d100 table (~40 entries), rolled before positives, attr penalties
  floor at −2.
- **Positive mutations** (p.20–25): 6 categories × 10 = 60 powers (Structure / Sense / Hybrid /
  Cognition / Pseudo-Psychic / Exotic). Each bespoke: System-Strain costs, per-scene/per-day
  limits, save-vs effects; several are combat powers (Crushing Jaws / Savage Claws / Venom Glands
  use Punch + Shock + Trauma → already-built combat hooks).
- **State:** MP pool, stigma, negative/positive lists, per-mutation usage counters; powers modify
  AC / Move / attr-mods / Trauma Target / HP-on-revive.
- **Reconcile** with the pack's existing `magic.yaml` ("mutations ARE this pack's magic system",
  the "Use Mutation" beat) — see §7.

### 5.2 Radiation (Plan 3) — *net-new, no analog*
- Periodic **Physical save** at an interval set by intensity (p.55); success = 1d4 Strain, failure =
  lose 1d6 CON (+ excess Strain). CON < 3 → die in 3d12 h. Optional Rad-Mutation: nat-20 → random
  positive, nat-1 → random negative (links to Plan 2).

### 5.3 Disease (Plan 3) — *expanded, semi-net-new*
- Exposure check → d10 Disease Types (Mild 1-6 / Severe 7-9 / Lethal 10); Physical save to resist,
  2d6-day recovery save steps severity down (p.54). Medic adds Heal to saves; antibiotics grant
  rerolls.

### 5.4 Stress → Breakdown → Hardening/Scars, + Addiction (Plan 4) — *net-new, no analog*
- Stress pool vs Wisdom; over Wis → Mental save (escalating −2/−4/−6) or **Breakdown**; opt to
  **Harden** → Stress 0 + permanent **Psychic Scar** (p.56). **Addiction** strictly *requires*
  Stress (p.58) — Stress ships first. Genre-gated (After-the-Fall / Deadlands flavor) → lower
  priority for a mutant-wasteland-first build.

### 5.5 Survival hexcrawl (Plan 5) — *WWN-adjacent, expanded*
- Tracking (Wis/Survive vs trail-age difficulty), 5km-hex overland travel + encounter checks,
  foraging (Wis/Survive → 1d6 + skill units), hunger/thirst/supplies + privation Strain (p.59–63).

### 5.6 Creatures of the Wastes (Plan 6) — *content + thin code*
- AWN bestiary as Monster Manual content (ADR-059), injected into `<game_state>`. **Nemesis traits**
  (The Invincible / The Killer / The Messiah, p.228) as a thin override layer over normal death.

### 5.7 Enclaves & Settlements (Plan 7) — *standalone faction sim*
- Power 1-5 → Action Die; Cohesion; Features/Problems/Trouble; monthly enclave turn; 80-tag
  content table (p.104–135). Verify against existing faction/disposition systems before building.

## 6. Plan 1 — `awn` module + binding + ablative-HP personal combat (implementable)

**Repos:** `sidequest-server` (module + config + calibration) and `sidequest-content`
(mutant_wasteland YAML).
**Pattern precedent:** road_warrior→CWN (`2026-06-04`, §6) and neon_dystopia→CWN. Apply the same
Without-Number wiring checklist; most CWN seams already exist (neon_dystopia, road_warrior) —
**verify, don't rebuild.**

### 6.1 Engine — `sidequest-server`
- **New module** `sidequest/game/ruleset/awn.py`: `class AwnRulesetModule(CwnRulesetModule): slug = "awn"`.
  No method overrides in Plan 1 (combat == CWN). Docstring states the inheritance and why the
  subclass exists (honest slug + future-hook home).
- **Register** in `sidequest/game/ruleset/registry.py`: import + `AwnRulesetModule.slug: AwnRulesetModule()`.
- **Config model** in `sidequest/genre/models/rules.py`: `class AwnConfig(CwnConfig)` (inherits
  `system_strain` + `trauma` + `attribute_map`; `hacking` stays `None`). Add `awn: AwnConfig | None = None`
  to `RulesConfig`, plus a `_validate_awn` model_validator mirroring `_validate_cwn` (require a
  complete six-key `attribute_map` when `ruleset == "awn"`; fail loud, no silent default).
- **Loader cfg selection:** wherever the loader maps `ruleset` slug → the `cfg` passed to module
  methods (currently picks `rules.cwn` for `"cwn"`), add the `"awn" → rules.awn` branch. Because
  `AwnConfig` *is a* `CwnConfig`, every inherited `isinstance(cfg, CwnConfig)` assert in `cwn.py`
  passes unchanged.
- **OTEL:** combat reuses the existing `cwn.*` spans (`cwn.shock.applied`, `cwn.trauma.roll`,
  `cwn.mortal_injury.declared`, `cwn.major_injury.roll`, `cwn.system_strain.delta`) + `state_patch_hp`.
  No new spans in Plan 1. (AWN-specific spans — `awn.mutation.*`, `awn.radiation.*` — arrive with
  their genre-layer plans.)
- Apply the **Without-Number module wiring checklist** (PR #520 lessons): spans `__init__`
  re-export, `dice.py` downed-seam guard + `_physical_save_target_for` isinstance handling, OTEL
  span-assertion tests. Verify each is already satisfied by the CWN path; add only what's missing.

### 6.2 Content — `genre_packs/mutant_wasteland/rules.yaml`
- Add `ruleset: awn`.
- Replace `ability_score_names` (Brawn/Reflexes/Toughness/Wits/Instinct/Presence) with the standard
  six. Add an `awn:` config block with the (now identity) `attribute_map` and AWN's trauma /
  system_strain numbers from §4.
- Replace the momentum **"Wasteland Brawl"** combat confrontation with an `hp_depletion` combat
  confrontation carrying `opponent_default_stats` for **all six** ability scores + `hp` +
  `armor_class` (the documented "needs ALL SIX for saves" gotcha). Keep the strike/brace/angle/push
  beat texture; HP now flows underneath.
- **Keep** the social "Wasteland Parley" (negotiation) and "Wasteland Pursuit" (chase)
  confrontations as dial confrontations — they are not combat and don't need `hp_depletion`.
- Retire the `magic_level` flag per its own DRAFT note; the Mutation system framing moves to Plan 2.
- Honor `lethality_policy.yaml` (pack is `lethality: moderate`) for the 0-HP outcome.

### 6.3 Content remap consequence of D4 (standard six)
Every flavor-name reference must move to the standard six. Sweep at minimum:
`archetypes.yaml`, `char_creation.yaml`, `progression.yaml`, `power_tiers.yaml`, `axes.yaml`,
`inventory.yaml`, `prompts.yaml`, and every `stat_check:` in `rules.yaml` confrontations
(`Brawn`→STR, `Reflexes`→DEX, `Toughness`→CON, `Wits`→INT, `Instinct`→WIS, `Presence`→CHA).
The sweep must be exhaustive or the narrator will reference dead stat names. Classes/Stocks
(Scavenger/Mutant/Pureblood/Wirewalker/Beastkin/Tinker; Mutant Human / Pure Strain Human / etc.)
keep their flavor names; only the six attributes change label.

### 6.4 Calibration migration (documented trap — do NOT misread as regression)
Binding to `hp_depletion` regresses the pack-load / dial-schema and `COMBAT_PACKS` calibration
tests by design (road_warrior §6.2/§8 hit this exactly). Fix per precedent: filter
`dial_threshold`, drop mutant_wasteland from the dial-`COMBAT_PACKS` set. Record the baseline
failure list first; gate on the FULL suite with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS`
set.

### 6.5 OTEL / wiring test (mandatory — the GM panel is the lie detector)
- Seed a mutant_wasteland combat encounter; run a turn through the production narrator-context /
  dispatch path; assert the `cwn.*` personal-combat spans fire (attack resolution, Shock/Trauma)
  and HP depletes on the ablative pool — not improvised prose.
- At least one integration test proving the bound `awn` ruleset is reachable from a production
  turn path (loads via `get_ruleset_module("awn")`, fail-loud on unknown), not just unit-tested.

## 7. Open items handed forward (not decided in Plan 1)
- **Mutations ↔ `magic.yaml` reconciliation (Plan 2).** The pack already models mutations as its
  "magic system" (`magic.yaml`, the "Use Mutation" beat, `docs/design/magic-taxonomy.md`). Plan 2
  must decide whether the bespoke `MutationPlugin` *replaces* that framing or the magic.yaml becomes
  a thin descriptor pointing at the plugin. Architect call in the Plan 2 spec.
- **AWN-specific OTEL spans** (`awn.mutation.*`, `awn.radiation.*`, `awn.stress.*`) — defined with
  their owning genre-layer plans, following the `cwn.py`/`wwn.py` span-file pattern.
- **`flickering_reach` (the spoilable world)** combat content recalibration to ablative HP — a
  world-layer pass after Plan 1 proves the substrate.

## 8. Epic decomposition (each its own spec → plan → PR; foundation-first)

| # | Plan | Lane | Owner | Depends on |
|---|------|------|-------|------------|
| 1 | `awn` module + binding + ablative-HP personal combat | engine + content | Architect → Dev + GM | — (foundation) |
| 2 | **Mutations** (bespoke `MutationPlugin` + tables) | engine + content | Architect + GM | 1 |
| 3 | Radiation + Disease (+ Poisons) status tracks | engine + content | Dev + GM | 1 |
| 4 | Stress → Breakdown → Hardening/Scars + Addiction | engine + content | Dev + GM | 1 (Stress before Addiction) |
| 5 | Survival hexcrawl (travel/track/forage/hunger) | engine + content | Dev + GM | 1 |
| 6 | Creatures of the Wastes + nemesis traits | content + thin code | GM + Dev | 1 |
| 7 | Enclaves & Settlements faction sim | engine + content | Architect + GM | — (parallel; verify vs existing faction sys) |

Plan 1 gates the mechanical meaning of everything below it. GM owns the content lanes (mutation
tables, equipment catalog, bestiary, enclave content) and design/genre-truth coherence; the engine
lanes (module, config, status-track subsystems, MutationPlugin) route to **Architect/Dev** through
the sprint system.

## 9. Non-goals (Plan 1)
- No Mutations, Radiation, Disease, Stress, survival, creatures, or enclaves wiring — those are
  Plans 2–7. Plan 1 stops at: mutant_wasteland is a working `awn` pack with ablative-HP personal
  combat and a clean foundation.
- No AWN encumbrance (the pack's `encumbrance: none` philosophy stands until the equipment plan).
- No new combat UI; HP rides the existing ablative-HP sheet display + the ADR-074/075 dice overlay.
- No redesign of AWN's resolution math — faithful port (D6).

## 10. Risks
- **Calibration-test false alarms** — the `hp_depletion` migration regresses dial/COMBAT_PACKS
  tests by design (§6.4); documented but easy to misread as a real regression. Baseline first.
- **Content remap breadth (D4)** — standard-six touches more files than a pure `ruleset:` flip; the
  sweep (§6.3) must be exhaustive or the narrator references dead stat names.
- **`magic.yaml` double-truth** — until Plan 2 reconciles, the pack carries both the old
  "mutation = magic" framing and the new awn binding; flag clearly so no prompt implies mechanical
  backing that isn't live yet.
- **Spoiler discipline** — `flickering_reach` is the only spoilable world; recalibration of its
  combat content (§7) must not leak its lore into specs/reviews of the foundation.

---

## 11. Architect Addendum (2026-06-05) — Plan 1 seam analysis & Dev guidance

**Author:** Architect (White Queen). **Verdict:** the design is sound and reuse-correct; the
subclass choices (D3 `AwnRulesetModule(CwnRulesetModule)`, implied `AwnConfig(CwnConfig)`) are the
right ones. **But Plan 1 §6.1's "no method overrides, almost pure wiring" undercounts the scope:**
the engine keys ruleset behavior two different ways, and a thin `awn` subclass is treated
differently by each.

### 11.1 The two binding styles (the load-bearing finding)

| Binding style | Sites | Does a thin `awn` subclass work? |
|---|---|---|
| **Capability / isinstance** — `isinstance(cfg, CwnConfig)`, `isinstance(module, CwnRulesetModule)`, method-override probes (`type(ruleset).resolve_opponent_attack is not RulesetModule.resolve_opponent_attack`, `dice.py:773`) | `cwn.py:100/153/237`, `downed_seam.py:71`, `dice.py:341`, `encounter_lifecycle.py:1324`, `dice.py:776` opponent-reprisal | **Yes — free.** `AwnConfig`/`AwnRulesetModule` *are* their parents; isinstance and override-probes pass unchanged. This is why D3 is correct. |
| **Slug-string membership** — `rules.ruleset == "cwn"`, `ruleset in ("cwn","wwn")`, `ruleset != "cwn"` | `rules.py:ruleset_config()`, `builder.py:90`, `downed_seam.py:128`, `stabilize_mortal_injury.py:101`, `adjust_system_strain.py:89` | **No — silent fall-through.** `"awn" != "cwn"`. Each must be taught `awn`, or the behavior silently no-ops. |

The capability style is the better pattern and already proves itself: the server-driven opponent
reprisal (`dice.py:776`) keys on the *override*, so `awn` inherits the enemy turn with zero new
code — a faithful AWN firefight where the player can actually lose. The slug-string style is the
fragile one, and it's now being re-touched by a **fourth** module.

### 11.2 Plan 1 engine change-list — partitioned (this supersedes §6.1's list)

**MUST change (awn falls through the slug-string sites):**

1. **`sidequest/game/ruleset/awn.py`** *(new)* — `class AwnRulesetModule(CwnRulesetModule): slug = "awn"`, no overrides. Docstring: inherits CWN combat verbatim; exists for honest slug + future-hook home.
2. **`sidequest/game/ruleset/registry.py`** — import + `AwnRulesetModule.slug: AwnRulesetModule()`.
3. **`sidequest/genre/models/rules.py`** — `class AwnConfig(CwnConfig)` (empty body; inherits `system_strain`/`trauma`/`attribute_map`, `hacking` stays `None`); add `awn: AwnConfig | None = None`; add `_validate_awn` mirroring `_validate_cwn` (complete six-key attribute_map, strain `max_source` in map, valid `major_injury_save`); add the `awn → self.awn` branch to **`ruleset_config()`** (`rules.py:1206`).
4. **`sidequest/game/builder.py:82` `seed_system_strain`** — currently `if rules.ruleset != "cwn" or rules.cwn is None: return None`. **This is the chargen strain-pool gap** — without it, awn characters have no `system_strain` pool and `apply_system_strain`/first-aid/stabilize raise at runtime. **Recommended fix (capability form, not a third slug):** key on the config type —
   ```python
   cfg = rules.ruleset_config()
   if not isinstance(cfg, CwnConfig):   # CwnConfig ∪ subclasses (awn, and any future)
       return None
   con_flavor = cfg.attribute_map["CONSTITUTION"]
   ```
   This auto-covers awn *and* immunizes the site against the next sister module.
5. **`sidequest/server/dispatch/downed_seam.py:128`** — `ruleset in ("cwn","wwn")` gates Mortal/Major Injury, which AWN combat needs. Line 71 in the same file already uses `isinstance(cfg, (CwnConfig, WwnConfig))`; **align line 128 to that isinstance form** so awn rides for free and the file stops carrying two divergent gates.
6. **`sidequest/agents/tools/stabilize_mortal_injury.py:101`** — `ruleset != "cwn"` blocks awn; the `isinstance(module, CwnRulesetModule)` assert at :99 already passes for awn. AWN has the stabilize-at-0 rule (p.52). Loosen the string guard (accept `awn`, or test `isinstance(module, CwnRulesetModule)`).
7. **`sidequest/agents/tools/adjust_system_strain.py:89`** — same shape; AWN uses System Strain (stims/mutations/first-aid). Loosen the guard. *(Strictly exercised by Plan 2/3, but generalize the guard now to avoid a half-wired pack.)*

**FREE (no change — isinstance/override already covers awn):** `cwn.py` inherited-method cfg asserts; `downed_seam.py:71`; `dice.py:341`; `dice.py:776` opponent reprisal. Verify with tests; do not edit.

**DO NOT touch (awn correctly does not want these):**
- Hacking — `dice.py:328` (`== "cwn" and category=="hacking"`), `encounter_lifecycle.py:1324` (`cfg.hacking is None`). AWN has no net-run; the fall-through is correct. `AwnConfig.hacking` stays `None`.
- WWN-only — `commit_effort`/`long_rest`/`veterans_luck`, `session.py:95`, `narration_apply.py:4423`, `dice.py:515/596/675`, `loader.py:688/1474`, `builder.py:125`.
- Dogfight — `dogfight_shot.py:324` (`!= "swn"`); AWN ships/vehicles are a later plan, not Plan 1.

### 11.3 ADR decision

**No new ADR.** Adding `awn` is an *instance* of **ADR-117** (Pluggable Ruleset Module System) and
inherits **ADR-114** (Ablative HP); the `native → awn` pack switch for mutant_wasteland mirrors the
road_warrior precedent and changes no global decision. The sister-module specs were design docs, not
per-module ADRs — this doc continues that.

**Recommended: append one amendment note to ADR-117** capturing the debt this fourth module exposes:
> *Cross-cutting ruleset capability gates should key on the module/config type or a method-override
> probe (see `dice.py` opponent-reprisal), not on `rules.ruleset` slug-string membership. Slug
> branches (`seed_system_strain`, `downed_seam`, the CWN-only tools) now require editing on every
> new sister module; prefer `isinstance(cfg, CwnConfig)` / capability predicates.*

I am **not** recommending a full consolidation refactor in Plan 1 (pragmatic restraint — out of
scope, higher risk). The targeted capability-form fixes in items 4–5 leave the touched sites cleaner
without a sweep; the note records the rest as known debt for whoever adds module #5.

### 11.4 Calibration & test guidance (confirms §6.4/§6.5)
- The `hp_depletion` migration regresses the dial-schema / `COMBAT_PACKS` calibration tests **by
  design** (road_warrior PR precedent). Record the baseline failure list *before* the change; gate on
  the FULL suite with `SIDEQUEST_DATABASE_URL` + `SIDEQUEST_GENRE_PACKS` set.
- Mandatory wiring test (the GM-panel lie-detector): drive a mutant_wasteland combat turn through the
  production dispatch path and assert (a) `get_ruleset_module("awn")` resolves (fail-loud on unknown),
  (b) the inherited `cwn.*` spans fire (`cwn.shock.applied` / `cwn.trauma.roll` / `cwn.mortal_injury.declared`),
  (c) HP depletes on the ablative pool, and (d) the opponent reprisal fires (player can lose). Assert
  spans, not source text (per server CLAUDE.md "No Source-Text Wiring Tests").
- **Chargen smoke:** create a mutant_wasteland character and assert a non-None `system_strain` pool
  with `max == CONSTITUTION-flavor score` — this is the regression guard for the item-4 gap.

### 11.5 Note for the GM content lane (not Plan-1 engine)
AWN's native chargen is 3d6-in-order or the standard array (14/12/11/10/9/7), not point-buy; the pack
currently declares `stat_generation: point_buy, point_buy_budget: 27`. Point-buy stays mechanically
valid (the builder seeds strain from final scores regardless), so it's **not** a Plan-1 blocker — but
flag it as a faithfulness/calibration choice for the GM during the standard-six content sweep (§6.3).

### 11.6 Suggested story split for Plan 1
- **Story A (engine, Dev):** items 1–7 above + `_validate_awn` + the wiring/chargen tests. Owner: Dev.
- **Story B (content, GM):** `rules.yaml` `ruleset: awn` + `awn:` config block + standard-six
  `ability_score_names` + the `hp_depletion` combat confrontation + the §6.3 content sweep + retire
  `magic_level`. Owner: GM. Depends on Story A's `_validate_awn` (so the pack loads).

Story A is the foundation; Story B can author against it as it lands. Both are needed before
mutant_wasteland is a working `awn` pack.
