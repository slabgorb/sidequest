---
parent: context-epic-24.md
workflow: tdd
---

# Story 24-10: Wire world-grounding YAML loaders + ToolContext fields at session bootstrap

## Business Context

Epic 24 shipped seven stories (24-1 through 24-7, plus 24-9) that together
produce a typed, procedural world-grounding pipeline: schemas, authored YAML
for tea_and_murder/glenross and spaghetti_western, a Python weather
generator, a narrator-callable grounding tool, and three OTEL spans for the
GM dashboard's lie-detector view. Every one of those stories is GREEN, code
reviewed, and merged.

**None of them are wired into production.**

A `/sq-wire-it` audit on 2026-05-21 (immediately after 24-7 finish) found
that:

* `WeatherGenerator` is instantiated nowhere outside the
  `sidequest.cli.weathergen` CLI. The session handler never loads
  `weather.yaml`, never constructs a generator, never produces a
  `WeatherState`.
* No production code path reads `demographics.yaml` or `calendar.yaml`
  from `sidequest-content/genre_packs/<pack>/`. No loaders exist for
  either file.
* The three `ToolContext` fields added by 24-6 —
  `weather_state`, `world_demographics`, `world_calendar` — are defined
  on the dataclass (`sidequest/agents/tool_registry.py:140-142`), read
  by the `get_world_grounding` tool handler
  (`sidequest/agents/tools/get_world_grounding.py:99-147`), and **never
  written anywhere in production**. The only `ToolContext(...)`
  constructor call on the production path is at
  `sidequest/agents/orchestrator.py:3259`; it omits all three fields,
  which default to `None` every turn.

The downstream effect is exactly the **Pattern 1 (Component-First TDD)**
and **Pattern 5 (LLM Compensation)** failures the sq-wire-it skill exists
to catch. Each component is individually green. The integration seam was
no one's story. If 24-8 (playtest validation) ran today:

1. Narrator calls `get_world_grounding` → tool returns `{weather: null,
   demographics: null, calendar: null}`.
2. The existing dispatch-span attrs `tool.grounding.<section>_present`
   correctly report `False` for all three sections — they truthfully say
   "session has no data wired."
3. The two new 24-7 spans (`world_grounding.weather_used` and
   `world_grounding.demographics_injected`) **do not fire**. Their gates
   require `ctx.<field> is not None`.
4. The narrator improvises weather and demographics from nothing. To a
   reader of the prose the system looks like it works. The GM dashboard
   would correctly show empty world-grounding columns, but only a
   Sebastien-class player who watches the dashboard would notice.

**This story closes the gap.** It is the bootstrap-loader + per-turn
plumbing that makes Epic 24's existing implementations reachable from a
real game turn. After this lands, 24-8 (playtest validation) has signal
to grade against.

## Technical Guardrails

**Spec authority hierarchy:** the file-placement decisions from 24-1's
context are load-bearing for this story. Specifically:

| File | Level | Pack location |
|------|-------|---------------|
| `weather.yaml` | pack | `sidequest-content/genre_packs/<pack>/weather.yaml` |
| `demographics.yaml` | world | `sidequest-content/genre_packs/<pack>/worlds/<world>/demographics.yaml` |
| `calendar.yaml` | world | `sidequest-content/genre_packs/<pack>/worlds/<world>/calendar.yaml` |

Loader code MUST honour the pack-vs-world split. Loading `demographics.yaml`
from the pack root is wrong even if a pack author misfiles the file there
— fail loud (per CLAUDE.md "no silent fallbacks") rather than silently
falling back to a different path.

**No silent fallbacks (verbatim from CLAUDE.md):** when a pack declares
weather/demographics/calendar but the file is missing, the loader MUST
raise a typed exception at session bootstrap. Packs that have never
authored these files (e.g. the `heavy_metal` stub, `low_fantasy`
workshopping) MUST continue to work — `ctx.weather_state /
world_demographics / world_calendar` simply stay `None`, the existing
24-6 `tool.grounding.<section>_present=False` attrs surface, and the
narrator-side tool call returns `null` for the absent section without
crashing the turn.

**Discovery rule:** "this pack declares weather grounding" must come
from the actual presence of `weather.yaml` in the pack directory,
not from a flag in `pack.yaml`. Authoring a `weather.yaml` IS the
declaration — symmetric with how `cultures.yaml` is discovered.

**Per-session generator lifecycle:** a single `WeatherGenerator` instance
per session, constructed at bootstrap from the pack-level `weather.yaml`,
held on the session handler / `TurnContext` analog. Per-turn weather
sampling (the `generate(zone, season, seed)` call that fires the
`world_grounding.weather_proposed` span) is a separate decision —
**this story does NOT scope a "regen weather every turn" policy**. For
the playtest, calling `generate()` once at session bootstrap with a
deterministic seed and stamping the resulting `WeatherState` onto every
turn's `ToolContext` is sufficient. If 24-8 surfaces a need for
per-scene or per-day re-roll, that's a follow-up story.

**Zone/season selection:** the seed-pick is genre-pack-level for now.
Hardcode the playtest's choice — `tea_and_murder` opens in autumn at
`glen_floor` — somewhere visible (a pack/world config, NOT inline in the
loader). The longer arc (calendar-driven seasonal advancement, region
selection from the location graph) is not in scope here.

**ToolContext extension seam:** the existing `orchestrator.py:3259`
constructor call already passes `lore_store` and `monster_manual` as
Phase E wiring. This story adds three more kwargs in the same pattern.
The carrier is whatever per-turn context object `orchestrator.py:405`
defines — extend it the same way 24-6's amendment extended `ToolContext`
itself.

**Architectural touchpoints to read first:**

* `sidequest/agents/tool_registry.py:84-142` — the `ToolContext`
  dataclass and the Phase E lore_store/monster_manual amendment that
  this story mirrors.
* `sidequest/agents/orchestrator.py:405` (TurnContext) and `:3259`
  (the ToolContext construction site).
* `sidequest/game/weather.py:207-305` — the existing
  `WeatherGenerator` and `WeatherState` types. NO changes here.
* `sidequest/agents/tools/get_world_grounding.py` — the consumer.
  NO changes here — the gate is "this tool returns non-null when wired."
* `sidequest/handlers/` and `sidequest/server/` — find the session
  bootstrap path. (Likely in `connect.py` or a `session_handler.py`.)

## Acceptance Criteria

1. **YAML loaders.** A loader module (e.g. `sidequest/game/world_grounding_loader.py`)
   exposes three functions: `load_pack_weather(pack_dir) -> ClimateRulesFile | None`,
   `load_world_demographics(world_dir) -> dict | None`,
   `load_world_calendar(world_dir) -> dict | None`. Each returns `None`
   when the file is absent (legitimate — pack/world chose not to author
   that surface). Each raises a typed exception when the file is present
   but malformed (no silent skipping). The weather loader returns the
   already-validated `ClimateRulesFile` from `sidequest/game/weather.py`,
   not raw dict.

2. **Session bootstrap calls the loaders.** When a session connects to a
   `tea_and_murder/glenross` world, the bootstrap path invokes all three
   loaders against the pack/world directories and stores results on the
   session handler's per-turn context. Verified end-to-end (loader is
   called from non-test production code reachable from the WebSocket
   connect handler).

3. **`WeatherGenerator` instantiated at bootstrap.** If
   `load_pack_weather()` returns non-None, the session constructs a
   `WeatherGenerator` instance (one per session, not per turn). The
   generator's `generate()` is called once at bootstrap for the playtest's
   chosen (zone, season, seed) to produce a `WeatherState`. This call
   fires the `world_grounding.weather_proposed` span via the 24-7 hook
   already in `WeatherGenerator.generate()`.

4. **`TurnContext` (or equivalent) gains three fields.** The per-turn
   context object at `orchestrator.py:405` is extended with
   `weather_state: WeatherState | None`, `world_demographics: dict | None`,
   `world_calendar: dict | None`. Populated at session bootstrap from
   the loader output, propagated unchanged through every turn.

5. **`ToolContext` constructor passes all three through.** The single
   construction site at `orchestrator.py:3259` adds three kwargs —
   `weather_state=context.weather_state`,
   `world_demographics=context.world_demographics`,
   `world_calendar=context.world_calendar` — in the same pattern as the
   existing `lore_store` / `monster_manual` lines.

6. **Wiring test (mandatory per CLAUDE.md).** An integration test in
   `tests/server/` or `tests/integration/` constructs a real session for
   `tea_and_murder/glenross`, calls the `get_world_grounding` tool through
   the production dispatch path (NOT a unit-mocked context), and asserts:
   * payload `weather` is a dict with the expected `WeatherState` fields
   * payload `demographics` is a non-None dict with `parish`/`recurring_cast`
   * payload `calendar` is a non-None dict (if 24-4 calendar landed —
     verify the file exists before writing this assertion)
   * the dispatch span carries `tool.grounding.weather_present=True`,
     `demographics_present=True`, and `calendar_present=True`
   * the `world_grounding.weather_used` and
     `world_grounding.demographics_injected` spans both fire

7. **Pack-without-grounding doesn't crash.** A second integration test
   uses a pack that does NOT author weather/demographics/calendar (use
   `caverns_and_claudes` or any pack that has no `weather.yaml`).
   Session connects cleanly, the tool returns three `null` sections, the
   dispatch span shows `*_present=False`, and the 24-7 spans do not fire.
   No exception, no error.

8. **Pack-with-malformed-yaml fails loud.** A test fixture with a
   syntactically invalid `weather.yaml` causes the loader to raise at
   session bootstrap — surfaced as a typed error in the connect handler,
   not a silent `None` and a downstream "weather grounding mysteriously
   absent" symptom. No silent fallback.

## Out of Scope

* **Per-turn re-roll policy.** Bootstrap-time single sample is fine for
  24-8. Calendar-driven advancement is a future story.
* **Region selection from the location graph.** Hardcode the seed pick;
  the room-graph integration is a future story.
* **Demographics or calendar generators.** Both are authored YAML loaded
  verbatim — no procedural generation in this story.
* **UI surface.** The narrator's prose will reflect grounding when it
  calls the tool; no client-side changes are required.
* **Adding `weather.yaml` / `demographics.yaml` to packs that don't have
  them.** Authoring is the content team's job per epic 24's existing
  story split. This story only wires the already-authored files.

## Risk

**Low-medium.** All the moving parts already exist and are tested in
isolation. The risk is in finding the right session-bootstrap seam without
disturbing the lore_store / monster_manual / Phase E precedents. Mirror
those lines, don't invent a new pattern.

The most common failure mode for this kind of story is shipping #1–#5 and
skipping #6/#7/#8 — the very same Pattern 1 failure that produced this
story. The integration test in #6 is the single most load-bearing AC; if
it doesn't exist or it mocks the dispatch path, the story has not
delivered.

## Forward Impact

After this story lands, 24-8 (playtest validation) becomes meaningful —
the playtest can grade narrator behavior against actual grounded state.
Without this story, 24-8 grades the narrator against `null`, which means
the playtest can't tell the lie detector from the implementation.
