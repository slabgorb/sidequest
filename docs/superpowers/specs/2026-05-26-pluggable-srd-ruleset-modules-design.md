# Pluggable SRD Ruleset Modules — A Rules VM in the Genre Layer

**Date:** 2026-05-26
**Status:** Design (approved for spec review)
**Author:** Architect (Major Margaret Houlihan)
**Decision-driver:** Keith Avery
**Supersedes (narrowly):** ADR-114 scoping line; re-slots ADR-033
**Blast-radius ADRs:** 003, 004, 007, 014, 021, 033, 074, 075, 095, 114

---

## 1. Why

SideQuest's paying customer is the forever-GM/world-builder (`project_customer_is_dm_not_player`). The
load-bearing pitch is: *"You ran this game for ten years on one side of the screen — get on the
other side, with the people having fun."* That promise only holds if the GM can bring **the
system they already know cold** — D&D B/X, Stars Without Number, Powered by the Apocalypse,
Fate — and have it run *faithfully*. A career GM spots a fudged saving throw in one round.

Today the engine cannot deliver that. The content schema is genuinely flexible — classes,
spells, items, resources, advancement, and even attribute *names* are all pack-authored data.
But three **resolution primitives are welded into engine Python** with no pack lever:

1. The D&D ability-modifier formula `(score − 10) // 2` (`server/dispatch/dice.py`, `game/saves.py`,
   `game/creature_core.py`).
2. A **closed** five-category B/X saving-throw enum (`genre/models/rules.py` `SaveCategory`).
3. d20 + DC resolution with a five-tier outcome ladder, baked through the confrontation engine,
   the opposed-check logic, *and* the 3D dice UI (`protocol/dice.py`, `server/dispatch/dice.py`).

These are not bugs. **They are the B/X ruleset — welded in the wrong place.** They are correct
for `caverns_and_claudes`; they are a straitjacket for every other system. The fix is not to
make the schema "more flexible." It is to **stop the engine from being a ruleset and make it
host rulesets.**

### The fidelity bar (decided)

**Faithful math.** Each genre reproduces its SRD's *actual* resolution — real HP, real saves,
real to-hit, real XP curves, the author's numbers. "Faithful feel" (let SideQuest's own dials
adjudicate underneath foreign flavor) was explicitly rejected: it is the exact friction this
design exists to remove.

## 2. The per-genre SRD map (the product)

Faithful SRDs, one bound per genre pack. This map is the roadmap *and* the proof the seam is
general enough — if one interface cleanly hosts both Fate (no HP, no saves, 4dF) and B/X (HP,
saves, d20), it will host the rest.

| Genre pack         | Ruleset             | Notes                                                     |
|--------------------|---------------------|-----------------------------------------------------------|
| `caverns_and_claudes` | **B/X**          | Real B/X HP restored (§6.2). Play priority.               |
| `space_opera`      | **Stars Without Number** | Builds on ADR-114 HP substrate. Play priority.       |
| `neon_dystopia`    | **Cities Without Number** | Same "Without Number" engine as SWN; cyberware/hacking foci. Reuses the SWN module. |
| `mutant_wasteland` | **Powered by the Apocalypse** | 2d6 + stat moves, harm clocks, no HP/saves.       |
| `pulp_noir`        | **Fate (Accelerated / FAE)** | 4dF + approaches; aspects = tags, stress = edge, fate points = `fate` resource. |
| `heavy_metal`      | **D&D 5e SRD**      | d20 + proficiency, HP, advantage/disadvantage.            |
| `tea_and_murder`   | **mechanics-lite**  | Fate, PbtA, or a bespoke light system — TBD.              |

**Play priority (decided):** **SWN** and **B/X** ship first, because the playgroup is asking for
SWN and is actively trying to play caverns. Fate drops to later precisely *because* it is the
cheapest module and nothing is blocked on it.

**Insight — one engine, three packs.** The "Without Number" family (Sine Nomine) is one core
engine in three skins: Stars (sci-fi), Worlds (fantasy), Cities (cyberpunk). One SWN
`RulesetModule` powers `space_opera`, `neon_dystopia`, and any future fantasy WWN pack — the
genre layer swaps only the foci / skill / gear content.

## 3. The architecture: `RulesetModule`

A `RulesetModule` is the unit a genre pack binds. The engine stops *being* a ruleset and starts
*hosting* them. A pack declares its binding in `rules.yaml`:

```yaml
ruleset: swn        # one of a registered set: native | swn | bx | fate_fae | pbta | dnd5e_srd
```

### 3.1 What a module owns (the interface contract)

A module is the authority for the **entire turn**, top to bottom:

1. **Character shape** — the *kind* of mechanical character (attributes / skills / FAE approaches /
   SWN foci). Pack content fills the slots; the module defines what the slots *are*.
2. **Resolution** — the dice and the check procedure. SWN: d20+skill+attr vs AC, plus 2d6+attr+skill
   skill checks. FAE: 4dF+approach vs difficulty. PbtA: 2d6+stat move. B/X: d20 to-hit and d20
   saves vs target.
3. **Outcome model** — the ladder. SWN hit/miss; Fate fail/tie/succeed/succeed-with-style;
   PbtA miss / 7–9 / 10+.
4. **Lethality / resource substrate** — HP-family (`HpPool`, from ADR-114) for SWN/B/X/5e;
   stress + consequences for Fate; harm clocks for PbtA.
5. **Turn orchestration** — initiative, action economy, and *what an action/beat/move is*. **This is
   the deep, new part: the module owns the whole turn, not just the dice.**
6. **Saves / defenses** — SWN's three (Physical/Mental/Evasion), B/X's five, Fate's defend action,
   PbtA's none.
7. **Advancement** — XP+level, milestones, playbook advances, refresh/aspects — per the SRD.
8. **Narrator resolution surface** — how the narrator proposes and adjudicates an action *in this
   module's terms* (per-module narrator tool contract — see §7).

### 3.2 What the engine keeps providing (shared, reused — not reinvented)

Modules **compose** these primitives; they do not duplicate them:

- The dice-lib (already built to support arbitrary dice — 4dF, 2d6, d20, pools).
- `HpPool` and `ResourcePool` (ADR-114, ADR-033 Pillar 2).
- Tags / aspects (the `target_tag` machinery — Fate aspects, PbtA tags, B/X conditions).
- `lethality_policy.yaml` + the `LethalityArbiter` (genre-authored 0-substrate outcomes).
- The `state_patch` OTEL span and the GM-panel polygraph.
- Persistence, sessions, perception filtering, the narrator backend.

### 3.3 Hard invariants (project rules, applied)

- **Exactly one module active per session.** Bound at pack load from `ruleset:`.
- **No cross-module fallback.** Per the hard ban (`feedback_no_fallbacks_hard`,
  `feedback_one_mechanism_per_problem`): an unknown or missing `ruleset:` **fails loud at pack
  load** (ERROR span, surfaced) — it never silently degrades to a default ruleset. There is no
  "if SWN resolution fails, fall back to the dials." One module, end to end.
- **`extra="forbid"` discipline holds.** New schema fields land with paired model changes in the
  same wave (`project_genre_models_extra_forbid`).
- **OTEL on every mechanical decision.** Each module emits spans for its resolution and substrate
  mutations; the GM panel must be able to audit which module ran and what it decided
  (OTEL Observability Principle).

## 4. ADR dispositions (the blast radius)

### 4.1 ADR-114 (Ablative HP Substrate) — survives, narrowly superseded

ADR-114's concrete machinery is **kept and promoted to a shared substrate**:

- `HpPool` (current/max/base_max) on `CreatureCore`, CON-mod seeding from `rules.yaml`.
- The tagged damage channel on beats (`strike` rolls weapon dice, `brace` mitigates).
- `CatalogItem.damage` / `CatalogItem.mitigation`.
- The `lethality_policy.yaml` 0-HP verdict path.
- The mandatory `state_patch` span on every HP delta.

These become **the HP-family substrate** that the SWN, B/X, and 5e modules consume.

**Reversed (and only this):** ADR-114 §"What we take from SWN, and what we don't" reads *"Steal
the nouns and the flavor. Leave SWN's resolution math … Skip SWN's d20-to-hit-vs-AC, 2d6
roll-under skill checks, the saving-throw table."* That scoping line is **superseded** for the
SWN module: SWN resolution is now **in scope**, owned by the SWN module. ADR-114 borrowed one
noun (HP) because there was no pluggable-resolution seam to do more; this design builds that seam,
so the half-measure is completed rather than abandoned. The new architecture ADR will carry a
narrow `supersedes`-style note against ADR-114's scoping section, the same surgical way ADR-114
handled ADR-078.

### 4.2 ADR-033 (Confrontation Engine / dials) — re-slotted, not deleted

This is the largest conceptual change and it is explicit:

The momentum / leverage / engagement-range **dials stop being a universal layer** imposed on every
genre. They become **the turn model of the SideQuest-native / Fate-family module** (`native`,
later `fate_fae`). They keep running, unchanged, for the packs that bind them (pulp_noir,
tea_and_murder). They are simply **no longer imposed** on SWN or B/X, which own their own turns.

ADR-114's "two-layer thesis" (dials on top, HP underneath) was *almost* this idea — it just kept
the dials universal. Here the two layers collapse into "the module owns the whole turn," and the
dial model is *one module's* turn, not everyone's.

### 4.3 Touch-only

- **ADR-003 / 004** (genre pack architecture, lazy binding): `ruleset:` is a new bound field; the
  loader resolves it to a registered module at load. Additive.
- **ADR-007** (Unified Character Model): the `Character` object stays the canonical struct; modules
  interpret its `stats` / `abilities` per their character shape. The shared object survives;
  modules are the lens.
- **ADR-040** (No Raw Stats): unchanged — ADR-114's narrow HP-visibility amendment carries forward;
  each module decides what numbers it surfaces per its SRD.
- **ADR-074 / 075** (dice protocol + 3D overlay): the dice-lib is the shared resolution renderer;
  modules request rolls through it (4dF, 2d6, d20, pools).

## 5. Sequencing — prove the seam against working code first

Reuse-first: the cleanest proof that "module owns the whole turn" works is to wrap **what already
works** before inventing anything.

1. **Define the seam.** `RulesetModule` interface + registry + `ruleset:` binding + dispatch.
   No behavior change yet — the dispatch path learns to route through a module.
2. **Wrap the current dial pipeline as the `native` module.** Zero behavior change.
   Characterization-tested so **every existing pack plays identically.** This validates the
   interface against live, working code before any new system exists. (This is the same
   discipline as extracting legacy code behind an interface: relocate, don't redesign.)
3. **SWN module** (play priority #1). First genuinely-different turn model: d20+skill vs AC,
   2d6 skill checks, three saves, foci, real HP. Builds directly on the ADR-114 HP substrate,
   which is already `space_opera`-first and half-built (`2026-05-25-swn-hp-substrate.md`).
4. **B/X module** (play priority #2; caverns). Real B/X HP restored (§6.2), B/X saves and to-hit
   relocated out of the engine welds into the module.
5. **Later sub-specs:** `fate_fae` (FAE — approaches map onto the six-slot frame), `pbta`
   (moves + harm clocks), `dnd5e_srd`, and CWN-as-SWN-reuse for `neon_dystopia`.

Steps 1–2 are the foundational architecture work and de-risk everything after: if the `native`
wrap can't reproduce current play, the interface is wrong and we learn it cheaply.

## 6. Two notes the modules inherit

### 6.1 The welds are the B/X module's raw material

The three welded primitives (§1) are not deleted in step 1 — they are **relocated** into the
`bx` module in step 4. Until then they live (working) inside the `native`/`bx` path. This is
extraction, not rewrite.

### 6.2 caverns gets real B/X HP (decided)

caverns currently runs ADR-014/ADR-078-era abstract combat (momentum/edge) with B/X *saves and
classes* — a hybrid. When it binds the `bx` module it gets **real B/X hit points**, using the
same `HpPool` substrate as SWN. Per ADR-114, caverns content **already carries B/X HP** that the
materializer currently translates *away*; restoring it is largely the "stop discarding what we
already author" deletion ADR-114 described for the sünden backport — not new construction.

## 7. The hardest integration surface: the narrator

SideQuest's soul is the natural-language narrator adjudicating anything a player can articulate
(the Zork Problem, SOUL.md). Today the narrator resolves via the confrontation/beat tool contract
plus the `apply_damage` tool. If each module owns the turn, **the narrator must speak each
module's resolution** — propose an SWN skill check in SWN terms, a PbtA move in move terms, a
Fate create-advantage in aspect terms.

This is a **per-module narrator tool contract**, and it is the deepest piece of integration. It is
**out of scope for the architecture ADR** and gets its own design section inside the **SWN
sub-spec** (the first module to need it). The architecture ADR only commits to: the module
interface *includes* a narrator-resolution surface (§3.1.8); it does not yet design SWN's.

## 8. Decomposition (this is an epic)

This design is too large for one implementation plan. It decomposes into:

- **Spec 0 — Architecture ADR (this design → ADR).** The `RulesetModule` seam, the interface
  contract, the ADR-114/033 dispositions, the registry + `ruleset:` binding + dispatch, the
  `native`-wrap proof. Implementation = steps 1–2.
- **Spec 1 — SWN module.** Resolution, saves, foci, advancement, HP substrate binding, and the
  per-module narrator tool contract. (Play priority #1.)
- **Spec 2 — B/X module.** Weld relocation, real B/X HP for caverns, B/X saves/to-hit, advancement.
  (Play priority #2.)
- **Later specs — `fate_fae`, `pbta`, `dnd5e_srd`, CWN-reuse for `neon_dystopia`.**

Each module spec gets its own spec → plan → implementation cycle.

## 9. Risks

- **Turn-orchestration refactor is the deep cut.** Dispatch handlers and the encounter pipeline
  assume the dial model today. The `native`-wrap (step 2) is the explicit de-risking move:
  validate the seam against working code, with a characterization test that current packs are
  byte-for-byte unchanged in behavior, before adding SWN.
- **Narrator per-module contract (§7)** is the highest-uncertainty surface; isolating it in the
  SWN sub-spec keeps the architecture ADR shippable.
- **"One mechanism per problem" must be guarded.** N turn models is *not* a violation — exactly
  one module runs per session, dispatched by `ruleset:`, with no fallback between them. The
  violation to watch for is any "safety net" that runs a second module's resolution when the
  first is uncertain. There is none, by invariant (§3.3).
- **Licensing (product concern).** Each SRD has its own terms — Fate (CC-BY, Evil Hat), the
  "Without Number" line (free SRDs, Sine Nomine), D&D 5e SRD (CC-BY 4.0 / OGL). Shipping a
  bound ruleset as a sellable genre pack requires the correct attribution line per module. Track
  per-module; not an engine concern, but a release gate.

## 10. Out of scope

- Designing any individual module's full resolution (SWN's skill-check math, Fate's aspect
  economy) — those are the per-module sub-specs.
- The narrator's per-module tool contract design (SWN sub-spec).
- Multiclassing, prestige, and other advanced character-progression shapes (per-module, later).
- Any change to where the server runs or how it is deployed (`feedback_tech_not_equal_deployment`).
