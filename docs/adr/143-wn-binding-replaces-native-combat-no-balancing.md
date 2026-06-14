---
id: 143
title: "A Without-Number Binding Replaces the Native Combat Engine — We Bind the Ruleset to Stop Balancing, Not to Balance Against It"
status: accepted
date: 2026-06-14
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [33, 114, 116, 117, 123, 139, 142]
tags: [game-systems]
implementation-status: partial
implementation-pointer: "sidequest-server/sidequest/server/dispatch/wn_round.py — sealed initiative-round engine; live for WWN hp_depletion combat, residual native-beat reuse + content beat_selection scaffolding to be removed"
---

# ADR-143: A Without-Number Binding Replaces the Native Combat Engine — We Bind the Ruleset to Stop Balancing, Not to Balance Against It

> **This ADR exists because we keep undoing it.** Three separate times the project
> has tried to make the native dial/beat engine "work with" a Worlds Without Number
> binding by tuning, converting, or gating native mechanics underneath WWN math. Each
> attempt re-introduces the native scaffolding it was supposed to remove, and the next
> contributor — reading a design doc that still says "keep `beat_selection`" — rebuilds
> the hybrid. This record makes the decision **load-bearing and durable** so it stops
> reverting. Operator directive, verbatim intent (Keith, 2026-06-14, emphatic):
> *"We have tried in the past to make native work with WWN. This is a DEAD END. We are
> going to use the Without Number engine so we don't have to balance. Trying to balance
> native tricks against the other stuff is the thing we failed at, because the scope was
> too much. Get this clear in ALL documentation — we keep undoing it."*

## Context

SideQuest's doctrine is **Crunch in the Genre, Flavor in the World** (SOUL.md), and
ADR-117 made resolution behavior pluggable per genre behind the `RulesetModule` seam.
A genre binds exactly one module by slug in `rules.yaml` (`ruleset:`). The Without
Number family — `swn`, `wwn`, `cwn`, `awn` — shares a single extracted core,
`WithoutNumberRulesetModule` (ADR-142, `without_number.py`), supplying SRD-grade
resolution: `d20 + hit vs AC`, weapon dice, three-category saves, Shock, morale,
Luck/Trauma/System-Strain/Mortal-Injury lethality, and Effort magic.

**The single most important fact about a Without Number binding is the reason we chose
it: WN ships published, already-balanced math. We bind WN so that we never have to
balance combat ourselves.** That is the entire value proposition. The moment we layer
the native engine underneath a WN binding and start tuning the seam between them, we
have thrown that value away and signed up for exactly the open-ended balancing problem
the binding was meant to eliminate.

The native engine (ADR-033, the `native` module) resolves combat as a sequence of
**beats** — `strike` / `brace` / `push` / `angle` `BeatKind`s in `beat_kinds.py` — each
advancing a **dial** (`player_metric` / `opponent_metric`) toward a threshold, granting
**fleeting tags** ("Opening", "Counter Stance") via `edge_config`, and triggering a
**per-beat auto-reprisal**. This is a fine engine for narrative-first packs. It is **not**
WN, and it cannot be made into WN by adjusting its numbers.

### The history this ADR closes

Every prior attempt tried to *keep* the native combat scaffolding and reconcile it with
WN:

- The **2026-06-12 `beneath_sunden` WWN port design** specified `resolution_mode:
  beat_selection`, `win_condition: hp_depletion`, copying the `heavy_metal` "Blade-work"
  beat shape — i.e. keep the native beats, run WWN resolution under them. (That doc is
  corrected by this ADR; see Alternatives.)
- The **"Option A full-defend" balance path (#839)** and the per-finding patches that
  followed — **#192** (defensive-reprisal *mitigation magnitude*), **#442** (converting
  the native "Counter Stance" edge/tag for WWN), and assorted **Brace tuning** — were all
  attempts to *balance a native mechanic so it behaves acceptably under WWN.*

The 2026-06-13/14 `beneath_sunden` playtests showed the bleed directly: a successful
defensive action granted a native **"Counter Stance"** tag the narrator rendered to the
player; **Brace** was offered as a combat action though it is not a WWN action; the
per-beat auto-reprisal fired as native confrontation behavior, not WN initiative. Each is
the native scaffolding surfacing through a WN binding. None is fixable by tuning, because
the scaffolding should not be present at all.

## Decision

**Under a Without Number binding, combat is resolved by the Without Number
initiative-round engine (`wn_round.py`). The native ADR-033 beat/dial engine — the
`strike`/`brace`/`push`/`angle` beat kinds, the `edge_config` fleeting-tag system
("Opening"/"Counter Stance"), the inert dial metrics, and the per-beat auto-reprisal — is
NOT used and is NOT balanced under a WN binding. It is removed from the WN combat path.**

**We do not balance WN combat. Binding the ruleset *is* the balance decision.** WN's
published math is the authority (per the standing WWN-SRD ruling, gm-decisions.md
2026-06-13). Any task framed as "tune / convert / gate / mitigate the native beat" under a
WN world is **out of bounds** — the correct action is to remove the native mechanic from
the WN path, not to make it behave.

### What a WN combat turn is

Each side acts on its **own initiative**. A player's combat action is a **WN action**
(attack, full defense, move, item-use, cast) resolved by **WN math** — attack `d20 + hit
vs AC`, weapon damage dice, Shock, morale, WN saves, WN lethality (Trauma / System Strain
/ Mortal Injury), WN/expedition XP. It is **not** a native `BeatKind` carrying dial deltas
and fleeting-tag grants. The opponent acts at **its own initiative slot** inside the
round walk — there is no per-beat auto-reprisal rider.

### The seam (where the cut goes)

The WN sealed initiative-round engine **already exists and already runs WWN combat**
(story 102-4, `wn_round.py`). When a pack binds a WN module, the encounter is
`hp_depletion`, and initiative is persisted, 100% of combat resolves through
`run_wn_round()`; the legacy immediate per-beat reprisal path is already starved. **This
is a cleanup of residual native reuse, not a new engine build.** Three residual bleeds
remain to be removed:

1. **`run_wn_round()` reuses native `apply_beat()`** (`beat_kinds.py`) to resolve the
   player's committed action — which still grants native fleeting tags ("Opening",
   "Counter Stance"), advances inert dials, and speaks in `BeatKind` terms. Under a WN
   binding, the player's action MUST resolve as a WN action with no native fleeting-tag /
   dial-delta / composure rider firing.
2. **Content combat defs are still authored as `resolution_mode: beat_selection`** with
   native beat lists, `edge_config`, and combat `momentum`/`morale` dial blocks. WN
   combat defs MUST stop authoring native combat scaffolding; the WN action set and WN
   lethality replace it.
3. **The "Counter Stance"/edge grant and the Brace action** are presented to WN players.
   Both are native; neither exists under WN and both MUST be absent from the WN action
   surface.

### Scope

- **In scope: WN combat** — `hp_depletion` confrontations under a WN binding. **Active
  rollout target: the WWN packs in play** (`caverns_and_claudes/beneath_sunden`,
  `heavy_metal`, `elemental_harmony`, `heavy_metal/barsoom`). The doctrine is
  family-wide; `swn` / `cwn` / `awn` combat follows the **same** rule and is staged behind
  the WWN cutover (mirroring ADR-116's staged guard rollout) — they are not a separate
  decision and never revert to native-hybrid.
- **Out of scope, unchanged: dial chase / negotiation confrontations.** A WN pack keeps
  the native dial engine for non-combat pacing scenes (chase, negotiation) — those are
  genre-neutral pacing devices, not WN-SRD combat, and WN does not (yet) supply their
  resolution. This is the only place the native engine legitimately runs inside a WN pack.
- **Out of scope, forbidden: balancing.** No rebalancing of WN numbers, no tuning of a
  native mechanic to "fit" WN. The whole point is to stop.
- The `native` module stays in the registry and is unchanged for native-bound packs.

### Invariants preserved

This ADR changes *which engine resolves WN combat*; it does not relax the confrontation
invariants. All continue to hold under the WN round:

- **ADR-116** — a confrontation requires an Other; one room-sourced opponent-seater.
  *(This subsumes the 107-2 "MM seater ignores the bound roster" finding: under WN the
  round MUST seat its opponent from the bound room roster, not improvise one.)*
- **ADR-139** — win-condition liveness (`hp_depletion` resolves on state), seated-actor
  HP durability, the mechanically-capable Other (content authors `opponent_damage`;
  seeded mooks have empty inventories), and the dispatch applicability gate.
- **ADR-114** — ablative HP is the WN lethality substrate.

### OTEL (the lie detector must prove native is OFF)

The round engine already emits `{slug}.round.committed` / `.initiative` / `.resolved`,
`{slug}.dead_premise`, `encounter.beat_applied{source="wn_round"}`, and
`encounter.opponent_attack_resolved`. Per the OTEL Observability Principle, the cleanup
MUST also make the **absence of native scaffolding observable** — enrich the WN beat
resolution span (or add a dedicated `wn.native_scaffolding_suppressed` span) to assert
that under a WN binding no fleeting-tag grant, dial-metric advance, or per-beat reprisal
fired. *An invariant you cannot observe is an invariant you cannot trust* (ADR-139): the
GM panel must be able to confirm the native engine did **not** run.

## Consequences

**Positive**

- We stop chasing balance. WN packs get SRD-true combat with zero per-feature tuning.
- WN combat content authoring collapses: no beat lists, no `edge_config`, no dial
  `momentum`/`morale` blocks to balance — the WN action set + WN lethality is the surface.
- The bleed Keith observed in play (Counter Stance, Brace, auto-reprisal) is removed at
  the source rather than papered over.

**Negative / cost**

- `beat_kinds.apply_beat()` currently serves two masters (native packs, and — vestigially
  — the WN round walk). The cleanup removes the WN reuse; care is needed not to regress
  native packs that legitimately depend on it.
- Contributors must internalize the doctrine: under a WN binding there is **no native beat
  to fix**. The reflex to "balance the mechanic" is the regression this ADR exists to stop.

## Alternatives considered

- **Keep `beat_selection` and layer WWN resolution on top (the 2026-06-12 `beneath_sunden`
  design; the `heavy_metal`/`elemental_harmony` shape).** **Rejected, emphatically (Keith,
  2026-06-14).** This is the native/WN hybrid. It re-introduces the native scaffolding and
  requires balancing the seam between two engines forever — the dead end we keep failing
  at, with scope that is too large. The 2026-06-12 design doc is corrected by this ADR; WN
  combat is **not** `beat_selection`.
- **Tune / convert / gate native beats per finding** (Option A full-defend #839; #192
  mitigation magnitude; #442 Counter-Stance conversion; Brace tuning). **Rejected**, same
  reason: each is a balancing patch on a scaffold that should not exist under WN. These
  findings are resolved by *removal*, not adjustment.
- **A bespoke per-WN-pack combat fork.** Rejected: duplicates the round loop per pack and
  violates Don't-Reinvent; `wn_round.py` already generalizes across the WN family.

## Amendments

### 2026-06-14 — Standing ruling logged

The Operator directive driving this ADR is recorded in
`.pennyfarthing/sidecars/gm-decisions.md` (2026-06-14) and as the 🛑 standing-ruling
banner atop the active playtest ping-pong. Both point here as the architecture-of-record.

### Note — ADR-142 doc gap

ADR-142 ("Without Number core extraction — honest `WithoutNumberRulesetModule` +
lethality/attribute groundwork") shipped in `sidequest-server` (#841,
`tests/game/ruleset/test_142_wn_core_extraction.py`,
`test_102_4_wn_turn_model_family.py`) but its ADR document was never landed in
`docs/adr/` (the orchestrator ADR set jumps 141 → 143). This ADR depends on ADR-142's WN
core; the missing ADR-142 record is tracked as housekeeping (subrepo-code-without-
orchestrator-ADR drift) and does not block this decision.
