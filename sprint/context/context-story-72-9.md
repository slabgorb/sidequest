---
parent: context-epic-72.md
workflow: tdd
---

# Story 72-9: Wire OCEAN + belief_state for invented NPCs

> **Epic:** 72 (NPC Identity Hardening) · **Points:** 5 · **Workflow:** tdd · **Repo:** sidequest-server
>
> Read `sprint/context/context-epic-72.md` first — it owns the two-store split-brain
> model (`npc_pool` scaffold vs `npcs` mechanical state), the story→component map, and
> the OTEL span inventory this story extends. This doc is scoped to the OCEAN +
> disposition + scenario-`belief_state` wiring for **narrator-invented** NPCs only.

## Business Context

SideQuest exists so a forever-GM (Keith) can *play* without losing the depth a good
human DM provides. A human DM who invents a stranger at the table gives that stranger a
personality, an attitude toward the party, and — in a mystery — a stake in the plot.
The engine does not. When the narrator names a person who is in neither store, the
invented-mint path (`narration_apply._apply_npc_mentions`, ~line 1292) appends a bare
`NpcPoolMember(drawn_from="narrator_invented")` — name/role/pronouns/appearance and
nothing else. OCEAN, `Disposition`, and `BeliefState` all live on the **mechanical**
`Npc` (`game/session.py:120`), not on the scaffold `NpcPoolMember`, so an invented
person is **identity-thin**: they cannot develop a personality (ADR-042), cannot hold a
stable attitude toward the party (ADR-020), and — critically for the mystery packs Jade
and Sebastien care about — are invisible to the scenario's `belief_state` / `npc_roles`
graph (ADR-053). A suspect the narrator invents mid-investigation can never be *the
guilty one*, never carry a suspicion, never be questioned-as-tracked, because
`bind_scenario` (`server/dispatch/scenario_bind.py`) only seeds beliefs for authored
NPCs already in `snapshot.npcs` at chargen.

This story wires the three identity surfaces onto invented NPCs at the moment they first
become mechanical (`Npc`), so they can subsequently develop (72-1's pipeline reads
`resolution_tier` / disposition / OCEAN) and participate in scenarios. For Sebastien and
Jade this is a **player-facing mechanical-legibility** win — an invented NPC now has a
real disposition number and a real belief bubble the development pipeline and GM panel
can surface — *not* a dev-observability feature. The new OCEAN/belief seed span exists so
**Keith-as-dev** can verify the wiring fired (lie-detector), which is a separate concern
from the player-UI legibility.

## Technical Guardrails

**The seam: invented scaffold → mechanical `Npc`.** OCEAN/disposition/belief_state are
`Npc` fields, absent from `NpcPoolMember`. An invented person becomes an `Npc` only when
it first needs mechanical state, via **`_promote_pool_member_to_npc`**
(`narration_apply.py:916`). That function today builds an `Npc` with **no OCEAN** (`ocean`
defaults `None`), a **default-neutral** `Disposition()` (factory, value 0), and an **empty**
`BeliefState()` — and never touches `snapshot.scenario_state`. This is the primary wiring
target. (Verify whether 72-9 should *also* seed eagerly at mint, or only at promotion —
the epic's data-flow §4 treats promotion as where mechanical state is first attached, so
promotion is the natural single seam. Do not seed OCEAN/belief onto the `NpcPoolMember`
scaffold; it has no fields for them.)

**Reuse the authored-NPC seeding shape — do not reinvent.**
- **Disposition:** `world_materialization` seeds authored NPCs with
  `disposition=int(authored_npc.initial_disposition)` (line ~860); the plain
  authored-chapter path uses `int(npc_data.disposition or 0)` (line ~531). Invented NPCs
  should spawn **neutral** (`Disposition()` value 0 → `Attitude.neutral` per ADR-020's
  `-10..10` band), *not* the `-20` born-hostile creature default in `_npc_from_patch`
  (line ~1533) — that default is 72-5's concern and applies only to MM creatures; the
  invented path must not inherit it. `Disposition` (`game/disposition.py`) coerces a raw
  int via its pydantic schema hook, so `Disposition()` or `disposition=0` both work.
- **OCEAN:** `Npc.ocean` is `dict | None` (`session.py:169`). The typed model is
  `OceanProfile` (`genre/models/ocean.py`) — Big Five, each 0.0–10.0, default 5.0.
  **There is no random-OCEAN generator in the codebase today** (ADR-042's `random/jitter/
  shift` methods were explicitly *not* ported — see the ocean.py docstring). The implementer
  must decide the seed policy and make it explicit: a flat baseline `OceanProfile()`
  (all 5.0) serialized via `.model_dump()`, or a deterministic-jittered profile. Either is
  acceptable for this story **as long as it is a real value, not `None`**, and as long as
  the choice is honest (No Stubbing — don't ship an empty `{}` and call it wired). Flag in
  the test that `ocean is not None` after the invented path runs.
- **belief_state + scenario registration:** mirror `bind_scenario`
  (`scenario_bind.py:45`). When `snapshot.scenario_state is not None`, an invented NPC
  that becomes mechanical must be registered into the scenario graph:
  `scenario_state.npc_roles[npc.core.name]` gets a role (default `"Innocent"` — an
  invented walk-on is not the pre-selected `guilty_npc`), and its `belief_state` is the
  live `BeliefState()` mutation surface (gossip/questioning can later add beliefs via
  `add_belief`). `ScenarioState` is `snapshot.scenario_state: ScenarioState | None`
  (`session.py:741`); `ScenarioState.npc_roles` is `dict[str, str]` keyed by NPC **name**
  (`scenario_state.py:62`). Reuse `record_questioned_npc` / `npc_roles` mutation
  primitives that already exist — do not hand-roll a parallel registry.

**OTEL (required — epic span inventory, 72-9 row).** Add **one new** OCEAN/belief-seed
span fired from the invented-mint→mechanical production path, recording: npc name,
`ocean` seeded (bool/source), disposition value, and `scenario_registered` (bool) +
scenario_id/role when a scenario is active. NPC spans live in
`telemetry/spans/npc.py` (route registry pattern: `SPAN_ROUTES[...] = SpanRoute(...)`);
follow the existing `npc.referenced` / `npc.auto_registered` span-helper shape and register
a `SpanRoute` so the GM panel can extract it. This span is the lie-detector that proves
the wiring fired — per the OTEL Observability Principle, a subsystem that doesn't emit a
span can't be distinguished from Claude improvising identity.

**No Silent Fallbacks.** If the OCEAN model/module needed to mint a profile is genuinely
unavailable, **fail loud** — do not silently leave `ocean=None` and continue as if wired.
(In practice `OceanProfile` is a plain pydantic model that's always importable, so the
realistic "unavailable" case is a scenario-pack/`scenario_state` shape mismatch — surface
it, don't swallow it.)

**Server test rules (CLAUDE.md "No Source-Text Wiring Tests").** Tests must be
**behavioral + OTEL span assertions**, never `read_text()` greps of production source.
Drive the real invented-mint→promotion flow on a synthetic `GameSnapshot` fixture and
assert: (a) the resulting `Npc` carries the seeded fields, and (b) the OCEAN/belief-seed
span fired (the refactor-stable wiring assertion). Include at least one **wiring test**
that the seed is reached from the production invented path (not just unit-tested on a
helper) — per "Every Test Suite Needs a Wiring Test."

## Scope Boundaries

**In scope:**
- Seed OCEAN (`Npc.ocean`), neutral `Disposition`, and `BeliefState` onto a
  narrator-invented NPC at the point it becomes mechanical (`_promote_pool_member_to_npc`,
  `narration_apply.py:916`).
- Register that invented NPC into `snapshot.scenario_state` (npc_roles + live belief_state
  surface) **when a scenario is active**.
- One new OCEAN/belief-seed OTEL span in `telemetry/spans/npc.py` with a `SpanRoute`.

**Out of scope (other stories / do not touch):**
- **Namegen** — routing the invented bare name through ADR-091 culture-bound generation is
  **72-4** (`genre/names/generator.py`). 72-9 wires identity onto whatever name exists; it
  does not generate names.
- **Development pipeline revival** — interest-increment, `resolution_tier` escalation, and
  emergent disposition *drift* are **72-1**. 72-9 only seeds the *initial* values 72-1 then
  develops; do not implement tier escalation or drift here.
- **Born-hostile `-20` fix** for MM creatures — **72-5** (`_npc_from_patch` line ~1533).
- **MM-origin NPCs already carry these fields** (or get them via 72-3/72-5). Do **not**
  double-wire: NPCs materialized via `Session._npc_from_patch` (creature/MM patches) and
  authored NPCs seeded in `world_materialization` already have a disposition and (for
  authored) `ocean`/belief paths. Guard the new seed so it fires only for the
  **`drawn_from="narrator_invented"`** lineage and skips entries that already hold a
  non-default OCEAN/belief. Re-seeding an existing belief_state would clobber learned facts.

## AC Context

No explicit ACs exist in the epic; these are **derived** and are the contract for TDD.
All must be verified by behavioral/span tests (no source-text grep).

**AC-1 — Invented NPC gets an OCEAN profile.** When a narrator-invented NPC
(`drawn_from="narrator_invented"`) becomes mechanical via the production invented path,
the resulting `Npc.ocean` is a real, non-`None` profile (a serialized `OceanProfile`, not
`None` and not an empty `{}`).

**AC-2 — Invented NPC gets a neutral disposition.** The same `Npc` spawns with a
**neutral** `Disposition` (value 0 → `Attitude.neutral` per ADR-020), explicitly *not*
the `-20` born-hostile creature default. (Edge: confirm the MM/creature path is unaffected
— it keeps `-20`.)

**AC-3 — Scenario registration when a scenario is active.** With
`snapshot.scenario_state is not None`, the invented NPC is registered into the scenario:
its name appears in `scenario_state.npc_roles` (default role `"Innocent"`, never the
pre-selected `guilty_npc`) and it carries a live `BeliefState` mutation surface. Mirror
`bind_scenario`'s seeding shape; reuse `npc_roles` / scenario primitives.

**AC-4 — No active scenario → no scenario wiring, OCEAN/disposition still seeded.** When
`snapshot.scenario_state is None`, the NPC still gets OCEAN (AC-1) and disposition (AC-2),
but **no** scenario registration is attempted and nothing fails. (Edge case.)

**AC-5 — Wiring + OTEL span reached from production path.** A behavioral test drives the
real invented-mint→mechanical flow (not a direct helper call) and asserts the new
OCEAN/belief-seed span fired with the expected attributes (npc name, ocean-seeded,
disposition value, scenario_registered bool + scenario_id/role when applicable). This is
the load-bearing wiring assertion required by "Verify Wiring, Not Just Existence."

**Edge cases to cover in tests (not separate ACs):**
- **MM/authored-origin NPC** already has these fields → seed is **skipped** (no
  double-wire, no belief clobber). Assert the existing OCEAN/belief survives.
- **OCEAN model unavailable / scenario shape mismatch** → **fail loud**, do not leave
  `ocean=None` silently (No Silent Fallbacks).

## Assumptions

- **ADR-042 (OCEAN Personality Live Evolution) is marked `drift`** and **ADR-053
  (Scenario System — belief_state/gossip) is marked `partial`** in the ADR index. The
  implementer **must verify these subsystems are actually live before wiring onto them —
  do not assume.** Confirmed during context prep: the **data models** exist and are
  reachable (`OceanProfile` in `genre/models/ocean.py`; `BeliefState`/`add_belief` in
  `game/belief_state.py`; `ScenarioState` in `game/scenario_state.py`, attached as
  `snapshot.scenario_state`; `bind_scenario` in `server/dispatch/scenario_bind.py` is the
  live authored-NPC seeding precedent). The **drift gap** is the *evolution/gossip*
  behavior, not the storage surface — so seeding initial values is wiring onto live
  fields. **Crucially, OCEAN has no random/jitter/shift generator** (the ocean.py docstring
  states those methods were intentionally not ported), so the implementer must choose and
  justify the seed value (flat baseline vs deterministic jitter) rather than calling a
  generator that does not exist.
- The invented lineage is identified by `NpcPoolMember.drawn_from == "narrator_invented"`
  and an `Npc` promoted from it (`pool_origin` set, `ocean` None / disposition still
  default). The seed must key off this lineage, not fire for all `Npc` construction.
- Promotion (`_promote_pool_member_to_npc`, `narration_apply.py:916`) is assumed to be the
  single point where an invented scaffold first gains mechanical state in production; if
  the implementer finds a second invented→`Npc` production path during red-phase
  exploration, both must route through the same seed (one seam, not two).
- Scenario role default for a mid-session walk-on is `"Innocent"` — an invented NPC is
  never the pre-selected `guilty_npc` (that id is chosen at `ScenarioState.from_genre_pack`
  time from `can_be_guilty`). Confirm this matches `scenario_state.py`'s role vocabulary
  (`Guilty` / `Suspect` / `Innocent`).
- Cited line numbers (`narration_apply.py:916/1292`, `session.py:120/741/1501/1533`,
  `world_materialization` ~531/~860, `scenario_state.py:62`) are from the working tree at
  context-prep time and may drift; treat the named functions/fields as authoritative over
  the exact line.
