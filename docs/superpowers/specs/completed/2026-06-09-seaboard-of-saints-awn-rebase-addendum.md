# Seaboard of Saints → AWN Rebase Addendum

**Date:** 2026-06-09
**Author:** GM (Game Master)
**Status:** reconciliation note — does not modify the source spec
**Rebases:** `2026-05-14-mutant-wasteland-seaboard-of-saints-design.md` (the "Seaboard spec")
**Onto:** `completed/2026-06-05-ashes-without-number-mutant-wasteland-design.md` (the "AWN spec"), decisions D1–D6 locked with Keith 2026-06-05

---

## Governing doctrine (Keith, 2026-06-09)

> **AWN wins always.**

Wherever the Seaboard spec and AWN conflict on mechanics, AWN is authoritative — no case-by-case
adjudication. The Seaboard spec is now a **world + content layer**; it contributes flavor, geography,
cosmology, factions, and Saint *content*, and contributes **zero** mechanics that diverge from AWN.
Where AWN is silent (genuinely net-new, e.g. non-human PC stocks), Seaboard content is **additive**
and must be built from AWN primitives (MP, System Strain, ablative HP, the standard six, the four
saves) — it may extend AWN, never contradict it.

This resolves every conflict in the ledger below in AWN's favor by default, including the items
previously left open.

---

## Why this exists

The Seaboard spec (2026-05-14) was written when `mutant_wasteland` ran the **`native` dial engine**.
It therefore proposed its *own* genre-level mechanics — a 7-step chargen overhaul, a homebrew
Saint-Bundle mutation system, a Qud-derived defects-for-power economy, and an Edge-costed resource
loop.

Three weeks later (2026-06-05) Keith locked the **AWN** direction: `mutant_wasteland` is bound to a
faithful **Ashes Without Number** ruleset module (`awn`, subclass of `cwn`), with ablative HP /
Shock / Trauma / four-saves combat and a **bespoke `MutationPlugin`** carrying AWN's native MP
economy. AWN's decisions D4 and D5 **supersede the Seaboard spec's mechanical layer.**

**Net effect: Seaboard is no longer a genre-mechanics overhaul. It is a world + Saint-content layer
riding AWN's crunch.** The original spec stays valid for *world flavor, geography, factions, register,
and the Saint cosmology*. This addendum tells the eventual plan-author which mechanical sections to
drop and how to re-express the rest on top of AWN.

This note does not delete or rewrite anything in the Seaboard spec. Read the spec for the world;
read this for the mechanics rebase.

---

## The Gamma World question, settled

The Seaboard spec borrowed Gamma World at two altitudes. They land differently on AWN:

| GW/Qud borrowing | Altitude | Lands on AWN as |
|---|---|---|
| **Wahoo register** (GW4 mood ceiling + *A.I.*/*Sleeper* comic dystopia) | world flavor | **Keep verbatim.** Register is a world choice; it sits fine on AWN's grimmer default. |
| **Defects-for-power** (Qud) | mechanics | **Already native to AWN** — §5.1 MP economy: each negative mutation +2 MP (max 3), negatives rolled before positives, Stigma tables. Your instinct *is* AWN; stop hand-rolling it. |
| **"Roll the Bones"** 3d6-in-order alt chargen | mechanics | **Keep, rephrased to the standard six.** Small flag in chargen. |
| **Cryptic-alliance structure** | mechanics/content | **= AWN Enclaves** (AWN spec §5.7 / Plan 7). Build as that, not bespoke. |
| **Six "stocks"** (Saint-Marked / Wild Mutant / Sleeper / Animal / Plant / Synthetic) | mechanics | **Becomes a content/curation layer**, not a parallel chargen engine — see mapping below. |

**Verdict: the Gamma World *feel* is fully compatible with AWN. The Gamma World/Qud *mechanics* the
Seaboard spec hand-built are not — because AWN already ships a faithful-SRD version of the same
asymmetry.**

---

## Conflict ledger — what AWN overrides

| # | Seaboard spec says | AWN decision | Resolution |
|---|---|---|---|
| C1 | Retain the flavor-six (Brawn / Reflexes / Toughness / Wits / Instinct / Presence); add no new attributes (spec §9 step 4, "What chargen does NOT do") | **D4** — drop the flavor names, adopt the standard six STR/DEX/CON/INT/WIS/CHA; narrator may still *say* "reflexes" in prose | **AWN wins.** Every Seaboard chargen/content reference to the flavor-six is renamed in the AWN content sweep (AWN spec §6.3). "Roll the Bones" places into the standard six. |
| C2 | Homebrew Saint-Bundle mutation system + custom defects-for-power, in new `mutations.yaml` / `saints.yaml` | **D5** — bespoke `MutationPlugin` carrying AWN's MP economy (MP pool, System-Strain coupling, d100 negative table, 6 categories × 10 positives) | **AWN wins on the engine.** Saints are re-expressed as curated bundles *over* AWN mutations (see below). `saints.yaml` survives as **content**; a parallel `mutations.yaml` does **not** — AWN's mutation catalog is the source. |
| C3 | "Drain costs **Edge** per mutation use"; Edge as the resource economy | AWN runs on **System Strain + ablative HP**; Edge is being removed | **Edge references are dead.** Mutation costs are System Strain per AWN §5.1. |
| C4 | 27-point-buy default + flavor-six | AWN attributes + standard six (D4) | Point-buy is fine; just over the standard six. |
| C5 | Callings restricted by stock; new **Penitent** calling added at genre level (spec §9 step 3) | AWN inherits CWN/SWN class structure | **AWN wins (resolved 2026-06-09).** Adopt AWN's class structure as the spine. The native calling names (Scavenger/Mutant/Pureblood/Wirewalker/Beastkin/Tinker) survive **only as flavor labels / foci over AWN classes**, never as a parallel class system. **Penitent** survives **only** as an additive flavor-focus that does not contradict AWN class mechanics — its "miracle-narration social beats" must resolve through existing AWN/confrontation primitives, and its vow-drawback through System Strain or an existing penalty hook, not a bespoke economy. |

---

## The re-expression — Saints as a curation layer over AWN mutations

The Seaboard spec's central conceit (**iconographic mutation**: drink a Saint's spring, receive that
Saint's marks + drawback) **survives completely**. Only its implementation changes:

- **A Saint = a curated bundle of AWN positive mutations + one AWN negative mutation as the canonical
  "drawback," priced in AWN MP.** Not a new mutation table — a hand-picked subset of AWN's 6×10
  positives, with a designated AWN negative standing in for "the Saint's drawback."
- **`worlds/seaboard_of_saints/saints.yaml`** holds the canon: each Saint → its bundle of AWN
  mutation IDs + its drawback mutation ID + flavor. This is exactly the world-opts-into-a-subset
  shape the Seaboard spec already wanted (spec §"files", `worlds/<world>/saints.yaml`), just pointing
  at AWN mutation IDs instead of homebrew ones.
- **Saint-Marked chargen** = "take this Saint's pre-bundled MP package" (a guided, legible path).
  **Wild Mutant** = "spend MP freely against AWN's tables" (the open path). The Saint-Marked /
  Wild-Mutant split the spec wanted is just **two presets over the same AWN MP economy** —
  curated-vs-freeform — not two engines.
- **flickering_reach stays Saint-less** (Seaboard spec open-question #2, recommendation accepted):
  no New Catholicism reached it; its mutants are all Wild Mutants — i.e., raw AWN MP spend, no
  curation layer. flickering_reach inherits AWN cleanly with zero Saint content.

### Stock → AWN mapping

| Seaboard stock | AWN expression |
|---|---|
| **Saint-Marked** | curated MP preset (a `saints.yaml` bundle) — *most common* |
| **Wild Mutant** | freeform AWN MP spend against the d100/positive tables |
| **Sleeper** | pre-war human; **no mutations**, MP spent on pre-war implants instead (reconcile with AWN System-Strain item sources when the implant content is authored) |
| **Animal-Stock / Plant-Stock / Synthetic** | base creature/chassis trait set + (optionally) one Saint affinity bundle; **needs its own content spec** — AWN has no native non-human PC stock, so this is genuinely net-new content layered over AWN, flag at plan time |

---

## Build-order placement

Seaboard does **not** get its own foundation work — AWN Plan 1 (the `awn` module + binding + ablative
HP) is the foundation, already specified. Seaboard slots in **after AWN Plan 2 (Mutations)** lands,
because the Saint curation layer points at AWN mutation IDs that don't exist until Plan 2 ships.

Dependency chain:
```
AWN Plan 1 (awn module + binding)            ── foundation, specified
        ↓
AWN Plan 2 (MutationPlugin + AWN mutations)  ── Saints depend on these IDs
        ↓
Seaboard world plan                          ── world content + saints.yaml curation + chargen presets
```

The Seaboard chargen texture (stocks-as-presets, Roll-the-Bones, Penitent) folds into **AWN's**
chargen, not `native`'s. There is no separate "genre-level chargen overhaul" project anymore — that
scope was absorbed by AWN.

---

## What the Seaboard plan-author keeps from the original spec, unchanged

Everything that isn't in the conflict ledger:

- The whole **world**: the Corridor, all regions (Down East, Whalecoast, Cape Ann, Merrimack Mills,
  Providence, Hudson Valley, Philadelphia, …), their registers and statuses.
- The **Saint cosmology** and **New Catholicism / Magisterium** framework (governance, Plenary-Council
  form, the canon of Saints and their flavor).
- **Factions** (Saturday Club, Patroon Houses, Sisters of the Whitman Circle, Atwells Avenue Society, …).
- **Economy/currency** flavor (Mint-struck coins, Lighthouse Letters, Mass Pike Tokens).
- **Tone targets**, sensory/vocabulary guidance, the "not a survival game / not tacky-gonzo" guardrails.

These are world-tier flavor and are orthogonal to the ruleset — they ride any combat substrate.

---

## Remaining content questions (not mechanics conflicts — "AWN wins always" already settled those)

These are **scope/fidelity** questions, not adjudications. AWN is silent here (genuinely net-new),
so the answers are additive content built from AWN primitives — none of them can contradict AWN.

1. **Non-human stocks** (Animal / Plant / Synthetic): AWN has no native PC-stock system, so these are
   net-new content **extending** AWN (trait sets + one Saint affinity, expressed via existing
   attribute-mods / Move / AC / Trauma-Target hooks). Open question is only **whether they're wanted
   for v1 and at what fidelity** — not how they fight AWN (they don't get to).
2. **Sleeper implants** are authored as **AWN System-Strain item sources** (the same pool slot AWN
   uses for cyberware/stims/mutations), not a parallel implant economy.
3. **Animal/Plant trait fidelity:** how granular the natural-ability sets get is a content-budget
   call; mechanically they resolve through AWN's existing modifiers.
