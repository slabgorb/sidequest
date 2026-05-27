# SWN P4 — The Initiative Spine (engine-owned, ceremony-free)

**Date:** 2026-05-27
**Status:** Design (approved for spec review)
**Decision-driver:** Keith Avery
**Parent:** `docs/superpowers/specs/2026-05-26-swn-module-design.md` §6–7 (the turn model)
**Grandparent:** `docs/superpowers/specs/2026-05-26-pluggable-srd-ruleset-modules-design.md`
**Depends on:** P1 seam + `NativeRulesetModule`; P2+P3 resolution surface (PR #468); P6 `space_opera`→SWN binding (server #469 + content #267), all on `develop`
**Consumes (unchanged):** ADR-114 `HpPool`; ADR-036 sealed-letter barrier; ADR-074/075 player-facing dice + 3D overlay; ADR-051 two-tier turn counter; ADR-068 magic-literal discipline; ADR-031/090/103 OTEL polygraph
**Source of truth for constants:** *Stars Without Number: Revised (Free Edition)*, Kevin Crawford / Sine Nomine — local PDF under `~/Documents/DriveThruRPG/Sine Nomine Publishing/`

---

## 1. What this is, and what changed from §6

The module spec's §6 ("blind commitment, initiative-ordered resolution") reads as a
turn-model restructure. It is not, because most of it already shipped:

- **Blind commitment / no mid-round re-plan is already enforced** by the ADR-036
  sealed-letter barrier. Players submit once; nothing resolves until everyone is in;
  narration is withheld until the barrier fires. The §6 headline justification — "makes
  initiative fun by removing reactive re-planning" — is satisfied by code on `develop`.

The only genuine gaps versus §6 are:

1. The **1d8 + DEX initiative roll is never rolled.** `InitiativeEntry` exists in the
   protocol (`protocol/models.py`) but nothing populates it. Today, when the barrier
   fires, one narrator turn receives the combined action and decides resolution *order*
   in prose — so "whose shot lands first" is narrator improv, not a die.
2. There is **no `dead_premise` signal** (handled below — it moves to P5).

So P4 is narrow: **populate and honor a real, engine-owned initiative order.** It is
neither client-rolled nor narrator-whim. The engine rolls server-side with real RNG and
an OTEL span (the polygraph), exactly as the existing `roll_dice` tool already does for
"background rolls that should not interrupt the player with a 3D dice cup." The 3D overlay
(ADR-074/075) stays reserved for the one-player-one-die rolls it is good at — a player's
own attack / skill / damage. An initiative roll is a turn-ordering roll, not a player-skill
roll, so it never touches the cup.

**Design constraint from Keith: "no one really likes rolling for initiative."** The roll is
therefore *ceremony-free* — the engine rolls it **once, silently, at fight start**, persists
it, and reuses it every round. No player prompt, no per-round re-roll.

## 2. Scope

**In scope:** confrontations under `ruleset: swn` (the `hp_depletion` and dial-threshold
confrontations `space_opera` now declares). The initiative *spine*: roll → persist →
broadcast → thread the order into the narrator turn as the authoritative resolution
sequence.

**Out of scope (unchanged behavior):**
- Skill checks and saves (P2/P3 non-beat path) stay point-resolution — no ordering.
- `native` packs get **no** initiative and play identically; the Spec-0 characterization
  tests stay green. No fallback, no dial degradation (`feedback_no_fallbacks_hard`).
- No `enumerate_actions` / `resolve_action`, no commit-model change, no turn-model
  restructure. The seam generalization from §3 of the module spec is **not** pulled in by
  P4 — it is not needed for the initiative spine.

**Explicitly deferred to P5 (decomposition refinement — see §7):** the `dead_premise`
signal and its narrator adjudication.

## 3. The roll — module-owned, rolled once

New **optional** method on `RulesetModule` (`game/ruleset/base.py`):

```python
def roll_initiative(
    self,
    actors: list[EncounterActor],
    core_resolver: Callable[[str], CreatureCore | None],
    rng: random.Random,
) -> list[InitiativeEntry] | None:
    """Resolution order for a confrontation round, or None for no ordering."""
```

- **`NativeRulesetModule`** returns `None` → no ordering; current behavior preserved.
- **`SwnRulesetModule`** rolls **1d8 + DEX-modifier per actor**, sorts descending, returns
  the populated `InitiativeEntry` list. Real RNG (`rng.randint`), no client round-trip.
- The DEX modifier comes through the existing SWN modifier curve already in `SwnConfig`
  (`stat_modifier`), so no new constants leak in as magic literals (ADR-068).

**Where it fires:** `server/dispatch/encounter_lifecycle.instantiate_encounter_from_trigger`,
immediately after actors and `CreatureCore`s are seated (the same seam that already runs
`_seed_combat_hp_depletion_to_npcs`). The engine calls `ruleset.roll_initiative(...)` and
**persists** the result.

**Persistence:** a new field `StructuredEncounter.initiative: list[InitiativeEntry] =
Field(default_factory=list)`. Rolled once at instantiation, reused every round. An empty
list means "this ruleset/encounter has no ordering" (native, or non-confrontation), which
is the truthful state, not a fallback.

### SRD fidelity — what is looked up, not asserted

This design assumes **individual** initiative, rolled **once** and persisted, descending
order. The following are SRD details I will **not** assert from memory; they are looked up
in the PDF at implementation time and pinned into `SwnConfig` (logged honestly per
`feedback_measure_dont_assert`):

- per-round re-roll vs once-per-combat;
- individual vs group(-by-side) initiative;
- the tie-break rule;
- the die and modifier source (`1d8 + DEX` is the working assumption, marked `[SRD]`).

If the PDF contradicts the working assumption, the implementation follows the PDF and the
plan records the correction. The constant block lives in `SwnConfig`, never as literals in
`swn.py`.

## 4. The polygraph

New OTEL span `encounter.initiative_rolled` (in `telemetry/spans.py`, emitted at the
instantiation seam): per-actor d8 face, DEX modifier, total, and the final ordered token
list. This is the lie detector — it proves the d8 was real and the resolution order is
engine-derived, not narrator improv. (CLAUDE.md OTEL Observability Principle; this is a
Keith/dev-panel concern, not a "Sebastien feature" — though the *order itself* surfaces to
players via §5.)

## 5. The table sees it (player-facing)

Populate the **already-existing, always-`None`** `initiative` field on the
confrontation / tactical-grid payload (`protocol/models.py` `TacticalGridPayload`;
threaded through `dispatch/confrontation.build_confrontation_payload`) with the persisted
order. The UI renders a plain initiative list — **no 3D dice overlay**. This is the
SWN-module player-visible-math posture (module spec §9): Sebastien and Jade see the order
as a table fact. ADR-040's no-raw-stats posture is unchanged for `native`/other packs.

## 6. The narrator obeys it

Thread the persisted `initiative` order into the per-round narrator turn input at the
combined-action assembly (`handlers/player_action.dispatch_fired_barrier` →
`_execute_narration_turn`). The narrator receives the authoritative sequence:

> *Resolve the committed actions in this initiative order: `<ordered actor list>`. An
> actor reduced to 0 HP earlier in this order does not act.*

The math (the order) is engine-owned; the narrator only **describes** the round in that
order. The "actor at 0 HP does not act" rule statement keeps the prose correct in the
interim before P5 enforces it mechanically.

## 7. Why `dead_premise` is P5, not P4

§6.4 of the module spec puts `dead_premise` ("a committed action whose target a
higher-initiative ally already dropped") in the turn model. It belongs in **P5**, for a
structural reason:

`dead_premise` can only be *enforced* by an engine that walks the order **actor-by-actor**
and knows, mid-round, that someone just hit 0 HP. That per-actor mechanical walk **is** the
P5 narrator-tool contract — `swn_attack` resolving each slot in turn, the engine checking
HP between slots. P4's flow hands the whole round to a single narrator turn and is **not**
in the per-actor loop, so a `dead_premise` branch built in P4 could never actually fire —
it would be dead code (CLAUDE.md "No Stubbing").

Therefore: **P4 ships the spine** (roll + persist + broadcast + order-into-narrator).
**P5 owns `dead_premise`** — when its tool walk reaches a slot whose actor is down (or whose
target is gone), it emits the `encounter.dead_premise` signal + span and skips the
mechanical resolution; the narrator then describes the fizzle (and, in P5's
`swn_adjudicate_dead_premise`, optionally redirects the swing in fiction). P4's narrator
input states the rule so prose stays correct until then.

## 8. Build surface

| Change | File |
|--------|------|
| `roll_initiative(...) -> list[InitiativeEntry] \| None` (optional, default `None`) | `game/ruleset/base.py` |
| Native impl returns `None` | `game/ruleset/native.py` |
| SWN impl: 1d8 + DEX-mod per actor, sorted, persisted | `game/ruleset/swn.py` |
| `StructuredEncounter.initiative: list[InitiativeEntry]` | `game/encounter.py` |
| Roll + persist at instantiation seam | `server/dispatch/encounter_lifecycle.py` |
| `encounter.initiative_rolled` span | `telemetry/spans.py` |
| Populate payload `initiative` field | `server/dispatch/confrontation.py` |
| Thread order into narrator turn input | `handlers/player_action.py` (`dispatch_fired_barrier`) |

No new wire message type. No UI commit-model change. `InitiativeEntry` already exists.

## 9. Testing

- **Unit:** `swn.roll_initiative` produces one entry per actor, `1d8+DEX` range, descending
  sort, deterministic under a seeded `random.Random`. `native.roll_initiative` returns
  `None`.
- **Persistence:** instantiating an SWN `hp_depletion` confrontation populates
  `StructuredEncounter.initiative`; a `native` encounter leaves it empty.
- **OTEL wiring test (required, per CLAUDE.md):** drive a real `space_opera` confrontation
  instantiation through `instantiate_encounter_from_trigger` and assert the
  `encounter.initiative_rolled` span fired with per-actor rolls — span assertion, not
  source-grep.
- **Narrator-input wiring test:** fire `dispatch_fired_barrier` for an SWN confrontation and
  assert the assembled narrator input carries the ordered actor sequence.
- **Characterization guard:** the Spec-0 `native`-wrap tests stay green (native unchanged).
- No fixtures point at live content beyond the real `space_opera` pack the e2e already
  loads (`feedback_tests_not_point_at_content`).

## 10. Success criteria

- Instantiating a `space_opera` (`ruleset: swn`) confrontation rolls 1d8 + DEX per actor
  **once**, server-side, with no player prompt; the order persists on the encounter and is
  reused each round.
- The GM panel shows an `encounter.initiative_rolled` span with every actor's roll and the
  final order.
- The player UI shows the initiative order as a plain list (no 3D overlay).
- The narrator resolves the round's committed actions in that order.
- `native` packs show no initiative and play byte-for-byte as before.

## 11. Risks

- **SRD detail drift.** The per-round/group/tie-break/die specifics are assumed, not known.
  Mitigated by §3's explicit PDF lookup + `SwnConfig` pinning at implementation time; the
  plan records any correction.
- **Touching the instantiation seam.** `instantiate_encounter_from_trigger` already does
  hp_depletion seeding; adding the initiative roll is additive at the same seam. Mitigated
  by the characterization guard (native unchanged) and the OTEL wiring test.
- **`one mechanism per problem`.** Initiative ordering is SWN-module-owned; native returns
  `None`. There is no second ordering mechanism and no fallback between them.
