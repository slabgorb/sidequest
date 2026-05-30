---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-32: World-level scenario discovery + world-aware binding

## Business Context

ADR-053 (Scenario System — clue graph, belief state, gossip propagation) is the
mechanical spine that makes a mystery **solvable by the engine** rather than
improvised by the narrator. Story 71-19 authored Glenross's first scenario, "The
Man Off the Morning Train," and placed it at the **pack** level
(`genre_packs/tea_and_murder/scenarios/the_morning_train/`) because that was the
only level the loader understood. That was an explicit, Operator-approved
compromise: ship a playable scenario today, then file this follow-up to teach the
engine world-level scenarios and make binding world-aware.

The compromise is now a latent **No Silent Fallbacks** violation waiting to fire.
`tea_and_murder` will host more than one world (`glenross` ships today;
`blackthorn_moor` is in draft). The current binder picks `next(iter(pack.scenarios))`
— the first scenario in the *whole pack* — regardless of which world the player
chose. The moment a second world or a second scenario exists, a Glenross player
could silently get Blackthorn Moor's mystery, or vice versa, with no error. This
story closes that gap so each world binds **only its own** scenario, and an
absence of scenario is an explicit authored choice, not an accident.

This directly serves the project's load-bearing requirement that worlds are
**content, not code**: Jade (and any future author) must be able to drop a
scenario under `worlds/<world>/scenarios/` and have it bind for that world alone,
without touching the engine. It also serves the mechanics-first players
(Sebastien, Jade) for whom a *working* clue/belief engine — verifiable in the GM
panel via OTEL — is the difference between a real mystery and narration that only
sounds like one.

## Technical Guardrails

**Repos:** `sidequest-server` (loader + binder + World model) and
`sidequest-content` (relocate the scenario files). Server is gitflow off
`develop`; content is gitflow off `develop`. Branch
`feat/71-32-world-scenario-discovery` already exists in both.

**Key files (verified against source — line numbers approximate, confirm before editing):**

| File | What's there now | What changes |
|------|------------------|--------------|
| `sidequest-server/sidequest/genre/models/pack.py:119` (`class World`) | World model has **no** `scenarios` field | Add `scenarios: dict[str, ScenarioPack] = Field(default_factory=dict)` |
| `sidequest-server/sidequest/genre/loader.py:~1273` (`_load_subdirectories(path, "scenarios", _load_single_scenario)`) | Scenarios auto-discovered **only at pack root** | Also discover per-world scenarios from `worlds/<world>/scenarios/` and attach to the `World` model |
| `sidequest-server/sidequest/server/dispatch/scenario_bind.py:45` (`def bind_scenario`) | Signature **already** has `world_slug: str` (kw-only, required) at line 50, but the body **ignores it** — reads `pack.scenarios` (line 67) and binds `next(iter(pack.scenarios.items()))` (line 72) | Body must look up `pack.worlds[world_slug].scenarios` and bind only that world's scenario; emit an OTEL span recording the decision |
| `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py:871` and `:1055` | The **two** (only) callers of `bind_scenario` | Likely **no change** — `world_slug` is a required kw-only arg, so both call sites already pass it. Verify, don't assume. |
| `sidequest-content/genre_packs/tea_and_murder/scenarios/the_morning_train/` | Scenario files at pack root | `git mv` to `worlds/glenross/scenarios/the_morning_train/` (preserve all 5 files: scenario.yaml, clue_graph.yaml, npcs.yaml, assignment_matrix.yaml, atmosphere_matrix.yaml) |

**Architecture decision — fallback strategy (RECORDED): Option A, explicit absence, no silent fallback.**
When a world declares no scenarios, `world.scenarios == {}` and `bind_scenario`
returns `None` for that world. The binder does **not** fall back to pack-level
scenarios for a world that has none. This is mandated by the **No Silent
Fallbacks** principle (CLAUDE.md, server CLAUDE.md): a world with no mystery is a
valid authored state, and silently inheriting the pack's first scenario is
exactly the cross-world bleed this story exists to kill. Pack-level discovery
**stays** as an independent, documented path for packs that legitimately use it
(see Scope Boundaries) — keeping it is not a fallback; binding a world to it would be.

**OTEL is mandatory (CLAUDE.md OTEL Observability Principle).** `bind_scenario`
touches a subsystem, so the bind decision MUST emit a watcher span recording at
minimum: `world_slug`, `genre_slug`, the bound `scenario_id` (or `None`), and a
`bound` boolean. The GM panel is the lie detector — without the span we cannot
prove the right world's scenario bound versus the narrator improvising a mystery.

**Test-strategy constraint (server CLAUDE.md "No Source-Text Wiring Tests").**
Do **not** assert by grepping production source (no `read_text()` + regex on
`loader.py`/`scenario_bind.py`). Wiring must be proven by **behavior**: either
(1) OTEL span assertions — drive a bind, assert the span fired with the right
attributes — or (2) fixture-driven behavior tests — synthetic multi-world genre
pack + snapshot, call the real `bind_scenario`, assert `snapshot.scenario_state`
and returned `(scenario_id, pack)`. Reflection-based field checks
(`World` now has a `scenarios` field) are the allowed tripwire exception.

## Scope Boundaries

**In scope:**
- Add `scenarios: dict[str, ScenarioPack]` to the `World` model (`pack.py`).
- Teach the loader to discover `worlds/<world>/scenarios/` and attach to each World.
- Make `bind_scenario` world-aware: bind from `pack.worlds[world_slug].scenarios`,
  return `None` when that world has none (Option A — no pack-level fallback for a
  scenario-less world).
- Emit an OTEL span for the bind decision (world, genre, scenario_id, bound).
- Relocate `the_morning_train` from `tea_and_murder/scenarios/` to
  `tea_and_murder/worlds/glenross/scenarios/` in `sidequest-content`.
- Tests: world-level load, world-aware bind selection, multi-world isolation
  (binding glenross binds the train scenario; binding a scenario-less world binds
  nothing), OTEL-span assertion, and a `World.scenarios` field tripwire.

**Out of scope:**
- Migrating `pulp_noir` scenarios (`midnight_express`, `the_warehouse`) to
  world-level. They stay pack-level; pack-level discovery is preserved for them.
  Whether pulp_noir eventually goes world-level is a **future story**, not this one.
- Authoring any new scenario content (no new clue graphs / beliefs). This is a
  structural move + engine change only — `the_morning_train`'s content is unchanged.
- Authoring a `blackthorn_moor` scenario. The multi-world isolation test may use a
  synthetic/fixture second world; it does not require real blackthorn_moor content.
- Any change to `ScenarioState` / `BeliefState` runtime mechanics, clue-graph
  traversal, or gossip propagation — those are downstream of binding and untouched.
- Router/dispatch classification of investigation actions (`scenario_clue`) — the
  71-19 work confirmed that path is healthy; it is not re-litigated here.

## AC Context

**AC1 — World-level scenario loading.** After loading a pack, each `World` in
`pack.worlds` exposes a `scenarios: dict[str, ScenarioPack]`. For a pack whose
`worlds/glenross/scenarios/the_morning_train/` exists,
`pack.worlds["glenross"].scenarios["the_morning_train"]` is a populated
`ScenarioPack`. *Test:* build a fixture pack (or load tea_and_murder post-relocation)
and assert the world carries its scenario. *Edge:* a world with **no** scenarios dir
→ `world.scenarios == {}` (not missing-attr, not `None`).

**AC2 — World-aware binding selects the right world's scenario.** `bind_scenario(pack,
snapshot, genre_slug=..., world_slug="glenross", rng=...)` mutates `snapshot.scenario_state`
from the **glenross** scenario and returns `("the_morning_train", <pack>)`. *Test
(fixture-driven behavior):* construct a pack with two worlds, each carrying a
*distinct* scenario; bind world A; assert the bound `scenario_id` is A's and **not**
B's. This is the core regression guard against cross-world bleed — it must fail
against today's `next(iter(pack.scenarios))` body. *Edge:* the current code reads
`pack.scenarios`, so a fixture where `pack.scenarios` differs from
`pack.worlds[w].scenarios` cleanly distinguishes old vs new behavior.

**AC3 — Explicit absence, no silent fallback (Option A).** `bind_scenario(...,
world_slug="<scenario-less world>")` returns `None` and leaves
`snapshot.scenario_state` unset, **even when `pack.scenarios` (pack-level) is
non-empty**. *Test:* fixture pack with a pack-level scenario present but the target
world declaring none → bind returns `None`, scenario_state is `None`. This is the
assertion that proves we did NOT silently inherit the pack scenario. *Edge:* unknown
`world_slug` (not in `pack.worlds`) → also `None`, no `KeyError`.

**AC4 — OTEL span on the bind decision.** Driving a bind emits one watcher span
carrying `world_slug`, `genre_slug`, `scenario_id` (or `None`), and `bound: bool`.
*Test:* use the project's span-capture fixture (same pattern as existing watcher
tests), drive a successful bind and a `None` bind, assert a span fired in **both**
cases with correct attributes (bound=true with id; bound=false with id=None). Per
OTEL doctrine the absence-bind must emit too — "no scenario for this world" is a
real subsystem decision, not silence.

**AC5 — File relocation preserves content.** Post-`git mv`,
`genre_packs/tea_and_murder/worlds/glenross/scenarios/the_morning_train/` contains
all 5 files and `genre_packs/tea_and_murder/scenarios/the_morning_train/` no longer
exists. *Test/check:* loader loads tea_and_murder without error and
`pack.worlds["glenross"].scenarios["the_morning_train"]` is populated; the old
pack-level path yields nothing for tea_and_murder. (Content-repo move + server-side
load assertion together prove the relocation is wired, not just moved.)

**AC6 — No backward-incompatibility break for pulp_noir.** Loading `pulp_noir`
still surfaces its pack-level scenarios (`midnight_express`, `the_warehouse`) via
the preserved pack-level discovery path. *Test:* load pulp_noir, assert its
pack-level scenarios still load. This guards the "keep pack-level for packs that
use it" decision against an over-eager removal of pack-level discovery.

## Assumptions

- **`world_slug` already reaches the binder.** Because `bind_scenario`'s `world_slug`
  is a required keyword-only parameter (no default), both call sites in
  `chargen_mixin.py` must already pass it; today the function simply discards it.
  *If wrong* (e.g., a caller passes a placeholder/empty slug), that's a Design
  Deviation — log it and the call sites enter scope.
- **`_load_single_scenario` and `ScenarioPack` are reusable as-is** for world-level
  discovery — the per-world loader can call the same subdirectory helper the
  pack-level path uses, just rooted at the world directory. No change to scenario
  parsing is expected.
- **A fixture/synthetic second world is acceptable** for the multi-world isolation
  test (AC2/AC3); we do not need real `blackthorn_moor` scenario content to prove
  the binder selects per-world.
- **The relocation is content-safe.** `the_morning_train`'s YAML has no internal
  path references that break when the directory moves; only its location in the
  tree changes. *If wrong*, fix the references as part of the move and log it.
- **Span-capture test infrastructure exists** (watcher/OTEL test fixtures are used
  elsewhere in the suite per ADR-031/-090/-103). RED tests for AC4 lean on it
  rather than introducing new harness.

If any assumption proves wrong during implementation, log it as a Design Deviation
and notify SM before proceeding — wrong assumptions are the #1 source of scope creep.
