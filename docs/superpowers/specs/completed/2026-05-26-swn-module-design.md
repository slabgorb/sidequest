# The SWN Module — Faithful Stars Without Number as a RulesetModule

**Date:** 2026-05-26
**Status:** Design (approved for spec review)
**Author:** Architect (The Man in Black)
**Decision-driver:** Keith Avery
**Parent:** `docs/superpowers/specs/2026-05-26-pluggable-srd-ruleset-modules-design.md` (§8, Spec 1)
**Depends on:** Spec 0 — `docs/superpowers/plans/2026-05-26-ruleset-module-seam-native-wrap.md` (seam + `native`-wrap)
**Consumes:** ADR-114 `HpPool` substrate (live)
**Supersedes (narrowly):** the 05-25 "skip SWN's resolution math" scoping line (`2026-05-25-swn-crunch-ablative-hp-design.md` §"The dividing line"), already flagged for reversal by the parent design
**Source of truth for constants:** *Stars Without Number: Revised (Free Edition)*, Kevin Crawford / Sine Nomine — local PDF under `~/Documents/DriveThruRPG/Sine Nomine Publishing/`

---

## 1. Why this module, and who it is for

The two mechanics-first players — **Sebastien** and **Jade** — carried a 140-turn `coyote_star`
game on narrative alone *while the confrontation engine was broken*, and they specifically miss
the crunch. They asked for **SWN**. Jade is also a content author. The product promise
(`project_customer_is_dm_not_player`) is that a career GM can bring **the system they know cold**
and have it run *faithfully* — a fudged saving throw is spotted in one round.

So this module reproduces SWN's **actual** math, not a SideQuest-flavored approximation. The
05-25 umbrella adopted only SWN's nouns (HP, gear, stims) because there was no pluggable-resolution
seam; the parent design builds that seam, so the half-measure is completed: **SWN resolution is
now in scope, owned by this module.**

### The fidelity bar (inherited, restated)

Faithful math. Real attack rolls vs AC, real 2d6 skill checks, real three-save model, the
author's numbers. Constants are sourced from the SRD PDF and held as **module config**, never
invented and never hardcoded as magic literals (ADR-068 discipline). Where this design references
a number it cannot cite from memory, it marks it `[SRD]` rather than asserting it.

## 2. Scope

**In scope:** the full martial/skill/social SWN turn — character shape (attributes, skills, foci,
classes, saves, AC, HP, XP), faithful resolution (attack / skill check / save / damage), the turn
model (sealed-letter + initiative-ordered resolution), advancement, the per-module narrator tool
contract, player-visible math, and the SWN content schema. First bound to `space_opera`.

**Named follow-on (this epic, not this spec):** **psionics** — SWN disciplines, Effort, and
techniques, and the Psychic class's abilities. The martial/skill/save core does not block on it.
`space_opera` already carries a `magic.yaml`/psychic notion; the follow-on inherits it.

**Out of scope:** B/X, Fate, PbtA, 5e modules (sibling specs); CWN content (reuses this module
later for `neon_dystopia` — only foci/skills/gear content swap); SWN encumbrance
(`encumbrance: none` stands); ship HP (condition-tracks stay — ships are not personal-scale HP);
multiclassing beyond SWN's Adventurer partial-class combos; any change to where the server runs
or deploys.

## 3. Interface reshape — "the module owns the whole turn" (Approach A)

Spec 0 ships a deliberately minimal, native/beat-shaped seam:
`find_confrontation / stat_modifier / compute_dc / apply_beat / resolve_damage`, with
character-shape, advancement, and the narrator contract explicitly deferred "until the SWN plan
needs them." The SWN plan needs them. The seam **generalizes from beats to actions**:

```
class RulesetModule(ABC):
    slug: str

    # Scene framing — UNCHANGED. Confrontation defs stay the scene / Bang catalog.
    def find_confrontation(confrontations, encounter_type) -> ConfrontationDef | None

    # NEW — module owns the turn:
    def enumerate_actions(scene, actor) -> list[ActionOption]
    def resolve_action(action, targets, rng) -> ResolvedAction   # deltas + dice + OTEL
    def initiative(actors) -> list[ActorId]                       # resolution order

    # The deferred surfaces, designed here because SWN is the first to need them:
    def character_shape() -> CharacterShape      # what the slots ARE (§4)
    def advancement() -> AdvancementModel        # §7
    def narrator_surface() -> NarratorContract   # §8
```

- **`native` keeps working.** Its `enumerate_actions` yields the beats it always had
  (strike/brace/angle/push); `resolve_action` is the relocated `apply_beat` + `resolve_damage` +
  `compute_dc` (the DC-ladder). The Spec-0 characterization tests still pass — current packs play
  identically. This generalization is additive over the wrap, not a rewrite of it.
- **Confrontation defs remain the scene/Bang catalog** (SOUL: "Confrontation Defs as a Bang
  catalog"). A confrontation still *fires* a scene ("a firefight erupts in the cargo bay"). The
  authored `beats:` array is simply the **`native` module's action menu**; the SWN module **ignores
  authored beats** and derives its own menu from SWN rules + the scene.
- **No fallback.** Exactly one module per session, bound from `ruleset: swn`. An SWN resolution
  never degrades to a dial (`feedback_no_fallbacks_hard`, `feedback_one_mechanism_per_problem`).

**Generality note (deliberate YAGNI):** we build Approach A — concrete `ActionOption` /
`ResolvedAction` shaped for SWN and `native`. We do *not* pre-abstract a fully neutral
`TurnAction` value type now; the B/X and Fate specs will *pull* the interface toward more
generality only when a real second/third consumer proves the shape. (Parent design §3.1.5.)

## 4. SWN character shape

Faithful SWN slots; pack content fills them (the module defines what the slots *are*, ADR-007 —
the `Character` object stays canonical, the module is the lens).

| Slot | SWN shape |
|------|-----------|
| **Attributes** | STR / DEX / CON / INT / WIS / CHA, SWN's tight modifier curve `[SRD]` (narrower than D&D). Generation: array or 3d6-in-order with one score settable to 14 `[SRD]`. |
| **Classes** | Warrior / Expert / Psychic, plus **Adventurer** partial-class combos. Class drives attack-bonus progression, HP-per-level bonus, and the class ability (Warrior reroll/HP, Expert skill reroll, Psychic = follow-on). |
| **Skills** | The SWN skill list (Shoot, Stab, Punch, Fix, Heal, Notice, Talk, Program, Pilot, Sneak, Survive, Know, Lead, …), levels −1…+4 `[SRD]`. |
| **Foci** | SWN foci (Gunslinger, Armsman, Hacker, Die Hard, Alert, …) at levels 1–2, granting skill access + bonuses. |
| **Saves** | Three: **Physical / Evasion / Mental** — replaces the closed B/X 5-category `SaveCategory` enum welded in `genre/models/rules.py`. |
| **Defense** | **AC**, ascending (unarmored base `[SRD]`); from armor + DEX per SWN. |
| **Lethality** | **HP** via `HpPool` (ADR-114), seeded from class HD + CON mod `[SRD]`. |
| **Progression** | XP + level, max level 10 `[SRD]`. |

## 5. SWN resolution (faithful)

- **Attack:** `d20 + attack-bonus + combat-skill + attribute-mod` **vs target AC**; hit → roll the
  weapon's **damage dice** → `HpPool` delta. Damage rolls ride the existing player-facing dice
  protocol (ADR-074) and 3D overlay (ADR-075) — the whole table watches the damage resolve. This
  *is* Sebastien's "show me the math," already built, now fed by SWN.
- **Skill check:** `2d6 + attribute-mod + skill-level` **vs difficulty** (6/8/10/12/14 ladder
  `[SRD]`). Opposed checks = contested 2d6 totals.
- **Save:** `d20` vs the SWN save-target derivation (level + attribute mod `[SRD]`), one of the
  three saves.
- All constants are **module config**, sourced from the PDF by Dev/scenario-designer at
  implementation time, not asserted here and not scattered as literals (ADR-068).

## 6. The turn model — blind commitment, initiative-ordered resolution

This is the load-bearing design and the reason the sealed letter and SWN initiative are *both*
kept. The point of the seal, stated by Keith: it makes initiative **fun** by removing reactive
re-planning — *"I was going to block, then Leonard the Bold killed that one, so I attack instead"*
**cannot happen**, because everyone commits at once.

1. **Sealed-letter barrier preserved (ADR-036).** All players submit their **Main Action**
   simultaneously. No narration until everyone submits. Peer action text is visible during the
   wait (ADR-036 2026-05-03 amendment) — collaboration, not hidden submission. Alex is never
   rushed.
2. **Initiative (1d8 + DEX `[SRD]`) orders *resolution*, not submission.** The d8 still matters
   enormously: it decides whose committed action lands first.
3. **No mid-round adaptation.** You commit blind and live with it. This is the *fun* of the
   seal — commitment under uncertainty, no table-talk re-planning as the round unfolds.
4. **Dead-premise → narrator call.** When a committed action's premise is gone at its initiative
   slot (target already dropped by a higher-initiative ally), the engine emits a **`dead_premise`
   signal** and the **narrator adjudicates: redirect in fiction or let it fizzle, per situation**
   (the swing carries to the nearest threat when plausible; you fired at a corpse and ate the round
   when it isn't). The engine stays deterministic about *math*; the narrator is authoritative about
   *fiction*. **The player never re-chooses.** (See §8 — this is a narrator tool, not an engine
   branch.)

## 7. Action economy → the sealed action menu

SWN's **one Move + one Main Action + any On-Turn actions** per round becomes the action-choice
menu `enumerate_actions` presents — "beat choices informed by SWN." The single sealed **Main
Action** is what is committed blind (Attack / Skill Check / Defend / Use Focus); Move and On-Turn
riders attach to that submission. Defend, like everything else, is declared blind — you brace for
a blow that may not come.

## 8. The narrator tool contract (the hardest surface — in scope)

SideQuest's soul is the natural-language narrator adjudicating anything a player can articulate
(the Zork Problem). If the module owns the turn, the narrator must **speak SWN's terms**, replacing
the beat/`apply_damage` contract for this module. The narrator proposes; the engine adjudicates the
math and emits OTEL; the narrator describes the result.

| Tool | Engine does | OTEL |
|------|-------------|------|
| `swn_attack(attacker, target, weapon)` | d20 vs AC; on hit, damage dice → `HpPool` delta | `state_patch` per HP delta + a resolution span (roll, AC, hit/miss) |
| `swn_skill_check(actor, skill, attribute, difficulty)` | 2d6 + mods vs difficulty | resolution span (roll, target, margin) |
| `swn_save(actor, save, effect)` | d20 vs save target | resolution span |
| `swn_adjudicate_dead_premise(action, gone_target)` | nothing mechanical until the narrator picks a landing; then routes through `swn_attack`/etc. or marks the action spent | span recording redirect-vs-fizzle and why |

**The polygraph requirement (OTEL Observability Principle):** every tool emits a span so the GM
panel can verify SWN actually ran and the narrator isn't improvising mechanical outcomes. A turn
with no SWN resolution span on a mechanical action is a detectable lie.

This is the highest-uncertainty surface (parent §7, §9). It is isolated behind tool-level tests
with OTEL assertions so the rest of the module ships independently.

## 9. Player-visible math (amends ADR-040, module-scoped)

SWN exists to give Sebastien and Jade **legible crunch**. The SWN module therefore **surfaces its
SRD's numbers** in the player-facing UI: AC, attack bonus, skill levels, save targets, HP, XP, and
the damage dice as they roll. This broadens ADR-114's narrow HP-only amendment to ADR-040 into
"**the SWN module shows the numbers its SRD runs on**" — scoped to this module, not made global.
(`native`/Fate packs keep ADR-040's no-raw-stats posture.) This is a *player-UI* consideration —
not a license for SWN numbers on OTEL/GM-panel/dev observability framing.

## 10. Content authoring (Jade's surface)

Re-author `space_opera`'s **mechanics**, keep its **fiction**. Its current six-custom-attribute /
eight-role content is replaced by SWN shape; its lore, world, NPCs, visuals, and audio are
preserved. The genre's fiction survives; its rules become SWN.

New/changed content surfaces (YAML, expressible without engine code — ADR-003/004 additive
`ruleset:` binding, `extra="forbid"` discipline held):
- `rules.yaml`: `ruleset: swn`; SWN attribute names; three saves; AC base; the SWN constant block
  (modifier curve, difficulty ladder, save derivation, attack progression) sourced from the SRD.
- `skills.yaml`, `foci.yaml`: the SWN skill and focus lists.
- classes: HD, attack-bonus progression, class ability, HP-per-level bonus.
- `inventory.yaml`: weapons gain `damage` dice; armor gains AC. (The 05-25 gear/pharmacopeia plan
  `2026-05-25-swn-gear-pharmacopeia.md` feeds this; its damage descriptors now have faithful SWN
  meaning instead of dial-flavor.)

CWN reuse for `neon_dystopia` later swaps only foci/skills/gear content against the same module.

## 11. Sequencing & decomposition

Reuse-first; prove the seam against working code before inventing.

1. **Spec 0 lands first** — the `RulesetModule` seam + `native`-wrap, with characterization tests
   proving current packs are byte-for-byte unchanged. (Already planned.)
2. **Interface generalization (§3)** — beat→action, additive over the wrap; `native` re-expressed
   through `enumerate_actions`/`resolve_action` with the same characterization tests green.
3. **SWN character shape + resolution (§4–5)** — attributes, skills, foci, classes, saves, AC,
   HP binding; attack/skill/save/damage math from SRD config.
4. **SWN turn model (§6–7)** — sealed-letter + initiative-ordered resolution + the dead-premise
   signal + action economy.
5. **Narrator tool contract (§8)** — the four tools + OTEL spans + the dead-premise adjudication.
6. **Content re-authoring (§10)** — `space_opera` mechanics → SWN; gear/pharmacopeia wiring.
7. **Follow-on:** psionics; then CWN content reuse for `neon_dystopia`.

Each numbered block is plan-sized; this spec spawns its own plan(s) via writing-plans.

## 12. Risks

- **Beat→action generalization touches dispatch + the encounter pipeline.** Mitigated by Spec 0's
  `native`-wrap characterization tests landing first; the generalization keeps them green.
- **Narrator contract is highest-uncertainty (§8).** Isolated behind tool-level tests with OTEL
  assertions so the rest of the module ships without it being perfect.
- **"One mechanism per problem" guard.** A second turn model is *not* a violation — exactly one
  module runs per session, no fallback between them. The thing to forbid is any "safety net" that
  runs dial resolution when SWN is uncertain. There is none, by invariant.
- **Inventing SWN constants.** Forbidden. Every `[SRD]` marker is a real lookup in the PDF at
  implementation time, logged honestly, not asserted from memory (`feedback_measure_dont_assert`).
- **Licensing (release gate, not engine).** SWN Revised Free Edition ships under Sine Nomine's free
  SRD terms; a sellable SWN-bound pack needs the correct attribution line. Tracked per-module.

## 13. Success criteria

- A `space_opera` combat round: players submit Main Actions blind behind the sealed barrier; the
  engine resolves them in 1d8+DEX initiative order; an attack rolls d20 vs AC and deals visible
  `HpPool` damage via the 3D dice overlay; a higher-initiative kill triggers a `dead_premise`
  narrator adjudication for a now-targetless committed action.
- A skill check resolves 2d6 + mods vs a difficulty; a save resolves d20 vs its SWN target.
- The GM panel shows a resolution OTEL span for every SWN mechanical action and a `state_patch`
  span for every HP delta — no silent mutation, no narrator improv on mechanics.
- The player UI shows AC, attack bonus, skill levels, save targets, HP, and XP.
- `space_opera` content declares `ruleset: swn` and is authored entirely in YAML, with its prior
  fiction (lore/world/NPCs/visuals/audio) intact.

## 14. ADR disposition

This module is implemented under the **architecture ADR** the parent design produces (the
`RulesetModule` seam ADR). This spec adds no new ADR of its own; it is the first module body that
ADR governs. It carries forward the parent's narrow supersede of ADR-114's scoping line (SWN
resolution in scope) and consumes, unchanged, ADR-114's `HpPool`, ADR-074/075 dice, ADR-036
sealed-letter barrier, and ADR-068 magic-literal discipline.
