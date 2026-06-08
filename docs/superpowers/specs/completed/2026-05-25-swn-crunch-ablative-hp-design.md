# SWN Crunch + Ablative HP — Umbrella Design

**Date:** 2026-05-25
**Author:** GM (brainstorming session with Keith)
**Status:** Design approved; decomposes into per-lane implementation plans
**Supersedes/amends:** ADR-078 (supersede), ADR-040 (amend), ADR-033 (re-slot), ADR-014 (touch)

---

## Origin

Direct playgroup request. The two mechanics-first players — **Sebastien** and **Jade** (new
member: a forever-GM-who-wants-to-play, and a content author in her own right) — ran the
5-hour, 140+ turn `coyote_star` session *while the confrontation engine was broken*. They
loved the narrative, NPCs, and relationship continuity, but felt the absence of mechanical
crunch. They are specifically asking for SWN-style mechanics.

Keith authorized reintroducing **ablative HP** ("open up ablation as a mechanic again — hp,
etc — we keep fighting uphill battles") and explicitly accepted that **this supersedes ADRs**:
"I want to please them, and it isn't like I want to die on the hill."

Source material: *Stars Without Number: Revised (Free Edition)*, Kevin Crawford / Sine Nomine.
Local PDF under `~/Documents/DriveThruRPG/Sine Nomine Publishing/`.

## Core thesis

Give SideQuest its mechanical crunch back **without** sacrificing the narrative layer that
carried the broken-engine game. **Two layers, not two rivals:**

- The **dial / confrontation engine** (ADR-033) stays as the *narrative pacing layer* —
  the strike/brace/angle/push beats that Alex and James engage with. It answers *how the
  fiction moves this round.*
- **Ablative HP** returns as the *lethality substrate underneath* it. It answers *how close
  to dead you are.* Concrete, visible, and legible to Sebastien and Jade.

The broken-engine session is the proof: with the dials not firing, there was *neither* layer.
Restoring HP gives a floor of mechanical truth even when only the narrative is running.

## The dividing line (what we take from SWN, what we don't)

> **Steal the nouns and the flavor. Leave SWN's resolution math.**

- **Adopt:** the ablative HP/wound lethality model; the gear/armor/stim catalogs and their
  flavor; the Tech-Level (TL0–6) + maltech/pretech/postech worldbuilding spine; the hull
  taxonomy + fittings as ship *capabilities*.
- **Skip:** SWN's d20-to-hit vs Armor Class, 2d6 roll-under skill checks, saving-throw
  table, and Readied/Stowed Strength-based encumbrance. SideQuest keeps its own resolution
  (dials + the existing player-facing dice system) — HP is the piece being adopted, not the
  whole SWN combat procedure.

---

## Part 1 — The engine reversal (Architect + Dev, behind a new ADR)

This is **not** GM content lane. GM produces this spec; implementation hands off to Architect
(ADR + seam design) and Dev (engine).

### 1.1 HP as first-class state
- HP / `max_hp` return as first-class runtime state on character and creature entities.
- **De-risk fact:** the content YAML *already carries* B/X-style HP. Per ADR-078 the
  materializer *translates it away* at the `world_materialization._apply_npc()` seam. The
  reversal is largely **stop discarding what we already author** — not a rebuild.
- HP supersedes **Edge's damage-track role**. EdgePool (ADR-078) was the HP surrogate; HP
  reclaims that job.

### 1.2 Additive under the dials
- The confrontation engine keeps its beats and metric dials (momentum / leverage /
  engagement_range). Underneath, beats gain an **HP-damage channel**:
  - `strike` beats deal HP damage.
  - `brace` beats mitigate incoming HP damage.
  - `angle` / `push` keep their dial semantics; HP effects optional per beat.
- At 0 HP → mortally wounded / unconscious / dead, governed by the genre's
  `lethality_policy.yaml` (space_opera: moderate; Sünden: harsher).

### 1.3 Player-visible math
- HP is **shown** on the character sheet — this **amends ADR-040** (no-raw-stats) for the
  lethality number specifically. The narrative character sheet bends here, deliberately.
- Damage rolls ride the **existing player-facing dice system (ADR-074 protocol, ADR-075 3D
  overlay).** Weapon damage dice become 3D dice the whole table watches resolve. This *is*
  Sebastien's "show me the math" — already built, just needs HP to feed.
- **OTEL:** HP mutations emit the existing `state_patch` span. The GM-panel lie-detector
  requirement is satisfied by the span we already have; verify it fires on every HP delta.

### 1.4 Ships are unchanged
- Ships keep narrative **condition-tracks** (shields/hull/engines/weapons degrading). That
  model is *already* ablative — multi-track HP with narrative labels — and preserves the
  "losing your ship is a death in the family" design. HP reintroduction stays **personal-scale.**

### 1.5 ADR housekeeping
- New ADR **supersedes ADR-078** (symmetric: 078's `superseded_by` points back, new ADR's
  `supersedes` lists only 078). Per schema rules, 078 → `implementation-status: retired`.
- New ADR **amends ADR-040** (HP visible) and **re-slots ADR-033** (dials sit on top of HP,
  not instead of it). Note the ADR-014 touch (diamonds/coal currency interaction).

### 1.6 Open decision handed to Architect
- **Fate of Edge's non-damage roles.** ADR-078 also defined push-currency rituals and
  mechanical advancement on Edge/Composure. With HP reclaiming the damage track, Edge's
  remaining roles must either be **retired** or **repurposed** (e.g. folded into the
  progression system / kept as a pure push-currency). This is an engine-design call the
  superseding ADR must resolve — flagged, not decided here.

---

## Part 2 — The content (GM lane — three parallel passes on `space_opera`)

### Lane A — Gear & Pharmacopeia (`inventory.yaml`)
- Current catalog is thin (one sidearm, one rifle, one knife…). Fatten it with an
  SWN-derived weapon/armor/gear spread, translating item + lore + relative power.
- With HP restored, weapons gain a **`damage` descriptor.** Proposal: **SWN-native dice**
  (1d6 … 2d12) so the values are concrete, Sebastien-legible, and drive the dice overlay.
  (Exact damage-schema — dice vs. flat — is a mechanical-design detail for
  scenario-designer/Architect; GM authors the catalog and its relative power ordering.)
- **Pharmacopeia:** add the SWN stim line as `category: consumable` items with
  `narrative_weight`, `lore`, and an `effect` / `narrator_hint`:
  - HP-relevant now: **Lift** (heals), **Lazarus patch** (stabilize at 0), **Bezoar** (cure).
  - Scene-hooks: **Squeal** (truth serum → interrogation), **Hush** (compliance →
    control/kidnapping), **Reverie** (cold-calm killer), **Psych** / **Tsunami** (combat
    rage drugs with a backlash cost).
- Pure content; zero engine risk; improves every `space_opera` playtest immediately. Wires
  to HP once Part 1 lands.

### Lane B — Tech-Level worldbuilding spine
- Introduce **TL0–6** + **maltech / pretech / postech** as a **per-world property** that
  gates which gear/ships exist on a world.
- Seed the **three Maltech prohibitions** (no tools to enslave humankind, no unbraked AI, no
  planet-killers) as scenario/trope hooks.
- Author-facing surface → directly serves Jade-as-content-author. Touches the world schema
  (small Dev assist to add the world-tier field + loader support).

### Lane C — Chassis roster expansion (`chassis_classes.yaml`)
- Author the **5 deferred chassis classes** — `prospector_skiff`, `hegemonic_patrol_cruiser`,
  `fighter`, `station_hull`, `courier_skiff` — using SWN's hull taxonomy (Strike Fighter,
  Patrol Boat, Station, Shuttle, Corvette, Free Merchant) as **role/silhouette** source.
- SWN **fittings** (smuggler's hold, drop pod, mobile factory, sensor mask, drill-course
  regulator, fuel scoops, exodus bay, psionic anchorpoint…) become **condition-track
  capabilities / quirks**, never HP/mass/power budgets.
- Independent of Part 1 (ships = condition tracks).

---

## Part 3 — Sünden backport

HP is an **engine-level** change, not a `space_opera`-only feature. Once the substrate lands
and is proven in `space_opera`, **backport HP to `beneath_sunden`** — replicating the pattern
with Sünden's own (harsher) `lethality_policy.yaml`. Sünden content already carries B/X HP, so
this is the same "stop discarding" move applied to a second pack.

---

## Decomposition into implementation plans

This umbrella spawns separate plans, sequenced by dependency:

| # | Plan | Lane | Owner | Depends on |
|---|------|------|-------|------------|
| 1 | ADR (supersede 078) + HP substrate restoration | engine | Architect → Dev | — (foundational) |
| 2 | Gear & Pharmacopeia catalog | content (A) | GM | #1 for damage wiring (authoring can start now) |
| 3 | Tech-Level spine | content + schema (B) | GM + Dev | — (parallel) |
| 4 | Chassis roster expansion | content (C) | GM | — (independent) |
| 5 | Sünden HP backport | engine + content | Dev + GM | #1 proven in space_opera |

**Foundational:** #1 gates the *mechanical meaning* of #2's damage values. Content authoring
for #2/#3/#4 can proceed in parallel against the HP field as it lands. #4 is fully independent.

## Success criteria

- A `space_opera` combat turn deals **visible HP damage** via a player-facing dice roll,
  while the dial/confrontation beats still drive the narration. Both layers legible in one turn.
- The GM panel shows a `state_patch` OTEL span for every HP change (no silent HP mutation).
- `inventory.yaml` offers a genre-true weapon/armor spread + the stim pharmacopeia, each item
  carrying lore and a concrete mechanical handle.
- A world can declare a Tech Level that gates gear/ship availability.
- The 5 deferred chassis classes exist as authored content.
- `beneath_sunden` characters take and track HP under its own lethality policy.

## Non-goals

- Adopting SWN's d20/2d6/saving-throw resolution procedure.
- SWN encumbrance (`encumbrance: none` philosophy stands).
- HP on ships (condition-tracks stay).
- Exposing non-lethality raw stats in the UI (ADR-040 stands except for the HP number).
