# Orbital Map — Deterministic Travel, Danger Beats, and Drill-In Charts

**Date:** 2026-05-01
**Status:** Design — pre-implementation
**Lead use case:** Coyote Star (hard-SF tier)
**Companion docs:**
- `docs/adr/057-narrator-crunch-separation.md` (LLM narrates, scripts crunch — extended here to orbital state)
- `docs/adr/038-websocket-transport-architecture.md` (intent message protocol patterns)
- `docs/adr/035-unix-socket-ipc-python-sidecar.md` (server-side rendering pattern)
- `sidequest-content/genre_packs/space_opera/worlds/coyote_star/` (lead world; receives the first `orbits.yaml` + `chart.yaml` + `encounters.yaml`)

## Purpose

Stand up a deterministic orbital map system that:

1. **Shows party location** on a chart, as pencil-style annotation on an engraved astronomical document.
2. **Advances orbital state over time** — bodies move along their orbits as the story-time clock advances. The world is alive between sessions.
3. **Plots courses** with relative-difficulty cost, geometric correctness, and per-world travel-realism tier (hard `orbital`, soft `narrative`, in-between `hybrid`).
4. **Generates travel-time pressure as a campaign mechanic** — conjunction windows, hazard sweeps, and danger beats during transit produce Bangs without GM authorship.

The narrator never derives orbital state. All orbital math is pure-function Python on the server, OTEL-traced, golden-vector-tested.

The lead use case is Coyote Star: a binary system (Coyote primary + Red Prospect with its own moon system) with a swarm of named claims, drift hazards, and one absent gate. Other genres opt into `narrative` tier and bypass the math entirely while reusing the chart aesthetic.

## Approach

**Server is authoritative; UI is a thin display layer.**

- All orbital math lives in `sidequest-server` as pure functions over `orbits.yaml`.
- The map SVG is **rendered server-side** as a complete document per request and pushed to UI. UI mounts the SVG, adds pan/zoom (CSS transform, client-only), and routes click intents back to server via WebSocket.
- World content splits cleanly into three files: `orbits.yaml` (mechanics), `chart.yaml` (flavor), `encounters.yaml` (random tables). Plotter reads only `orbits.yaml`. Renderer composes all three. Narrator reads none directly.
- Genre packs supply default travel realism and base factors; worlds override.

**Why this shape:**

- Single source of truth for orbital math (server-side only). No risk of UI and server disagreeing on body positions.
- Clean crunch/flavor separation in content (per SOUL.md "Crunch in the Genre, Flavor in the World"). World authors can add chart annotations without touching mechanics.
- Narrator hallucination on orbital facts is structurally impossible — it never sees the params and only receives structured `COMPUTED_OPTIONS` / `TRAVEL_INTERRUPT` payloads.
- OTEL spans on every computation make Keith's GM panel a working lie detector.

**What's reused vs. new:**

- Reused: WebSocket transport (ADR-038), narrator scene-context-injection pattern (ADR-067), encounter scenario refs (ADR-069), OTEL span infrastructure (`sidequest/telemetry/spans/`).
- New: orbital math module (`sidequest/orbital/`), server-side SVG renderer (`sidequest/orbital/render.py`), three new content file kinds, four new beat-related WebSocket message types.

## Audience anchors

Per CLAUDE.md, weighed against the actual playgroup:

- **Keith** (forever-GM-now-player): the chart must read as a real navigator's document, not a Tailwind-styled UI element. The diegetic engraved aesthetic of the existing Coyote Star map is load-bearing — preserve it. The OTEL surface (`travel.beat.create` with full danger-beat schedule, `orbital.route.compute` with all options + selection) is what makes him trust the system. If he sees the narrator say "11 days" and OTEL says 18, he loses trust. Spans must fire on every computation.
- **Sebastien** (mechanics-first): the conjunction calendar, Hohmann/direct/gravity-assist categorical labels, deterministic danger-beat schedule, and pre-rolled encounter outcomes are *for him*. A "show numbers" toggle exposes deltaV-equivalent + transit days. Off by default; he'll find it.
- **James** (narrative-first): the chart is reference, not interrogation. He sees "Eighteen days later, the burn is over" — the math is invisible. Drill-in to inspect Red Prospect's moon system is a curiosity feature, not a workflow requirement.
- **Alex** (slow typist, narrative-first): smash-cut transit means he isn't asked to do anything during empty travel time. Interrupts are real scenes with real pacing. No fast-input gates anywhere in this slice.
- **Sonia / Antonio / Pedro** (aspirational household): not load-bearing here. Map system serves the playgroup; if it happens to be pretty, fine.

## Locked decisions (this brainstorm)

1. **Three travel-realism tiers** as a per-world dial with genre default: `narrative` (narrator hand-waves all transits), `hybrid` (engine computes, narrator presents soft), `orbital` (full deterministic mechanics, hard numbers available). Coyote Star = `orbital`. Most other genres = `narrative`.
2. **Crunch wall:** narrator never receives `orbits.yaml`. Receives only structured `COMPUTED_OPTIONS` and `TRAVEL_INTERRUPT` payloads. Cannot derive math, cannot estimate, cannot reroll.
3. **Standard Day = 24h.** No mechanical local-cycle handling. Narrator may flavor-mention divergent local rotations; clock uses Standard.
4. **Internal time unit: hours.** All beats carry `duration_hours`. Display layer formats to scale-appropriate units (min / h / d / w / mo).
5. **Four beat kinds:** `encounter` (1h default, narrator can override), `rest` (8h fixed), `travel` (computed by `route_options()`), `downtime` (player-declared). Clock advances only via beats. Every beat emits an OTEL span.
6. **Travel uses simplified Hohmann-shape math.** Engine returns categorical options (Hohmann window / direct burn / gravity assist), each with `transit_hours`, relative-difficulty score, and `available_now` boolean. Per-world `travel_speed_factor` tunes absolute scale for narrative pacing. **Not real Kepler at solar mass.**
7. **Travel beats smash-cut by default.** Interrupted only at danger beats that resolve to non-`nothing`. Multi-day transits produce a paragraph of arrival prose unless the engine has a real interrupt to surface.
8. **Danger beat formula:** `danger_beats = ceil(duration_hours × world.danger_density) + sum(hazard_arc_intersections)`. Defaults for Coyote Star: `danger_density: 0.012`, `hazard_arc_density: 0.10`. World-builder tunes.
9. **Danger beats are pre-rolled at travel-beat creation.** Seeded RNG. Full schedule emitted in `travel.beat.create` OTEL span. Deterministic and replayable.
10. **Scheduled events take danger-beat slot priority.** Conjunction events, hazard arc transits, gate-window events from `orbits.yaml` slot in first; remaining slots roll on world encounter tables. Predictable cosmic events override random ones.
11. **Roll is the roll.** No player abilities modify danger-beat rolls in v1. `Lucky` / `Slip the Eye` / similar abilities deferred to a future slice that will modify rolls *deterministically* and via OTEL-traced effects only.
12. **Map SVG rendered server-side, one document per request.** UI mounts SVG, adds pan/zoom client-side, routes click intents (`data-body-id`, `data-action`) back via WebSocket. UI does no math.
13. **Drill-in is a server-rendered scope swap.** A body is drillable iff some other body has it as `parent`. Renderer derives this at load time. Cross-scope route plotting terminates at chart edge with directional caps.
14. **Three content files per world.** `orbits.yaml` (mechanics, plotter input), `chart.yaml` (flavor, renderer-only), `encounters.yaml` (random tables, danger beat resolution). All three live in the world directory under `sidequest-content/`.
15. **Player marker is annotation, not engraving.** Drawn as pencil/ink overlay at current body or along trajectory; never replaces engraved chart elements. Co-located NPCs of consequence (e.g., Bad Girl when traveling with party) get a smaller adjacent mark.
16. **Time-advance animation deferred.** Steady-state map is static. Bodies move between snapshots, not within a frame loop. A "TIME ADVANCED" sweep transition is purely cosmetic and ships later if at all.

---

## 1. Architecture

Four layers, each with a single responsibility:

| Layer | Lives in | Owns |
|---|---|---|
| **Mechanics engine** | `sidequest-server` (`sidequest/orbital/`) | Authoritative clock; pure-function `position()`, `route_options()`, `conjunction_events()`; danger beat scheduler; encounter rolls; OTEL spans on every call. |
| **Renderer** | `sidequest-server` (`sidequest/orbital/render.py`) | Composes SVG document per request: engraved chart + flavor overlay + party marker + plot overlay. Reads `orbits.yaml` and `chart.yaml`. Emits one SVG per (world, scope, t, plot_state). |
| **Display + interaction** | `sidequest-ui` (existing Map tab + thin SVG host component) | Mounts received SVG; pan/zoom via CSS transform; reads `data-body-id` / `data-action` on click; sends intent messages back. **No math, no body position computation.** |
| **World content** | `sidequest-content` (per-world directory) | `orbits.yaml`, `chart.yaml`, `encounters.yaml`. Genre packs supply defaults; worlds override per-field. |

**The crunch wall:** the narrator receives only structured payloads from the mechanics engine — `COMPUTED_OPTIONS`, `TRAVEL_INTERRUPT`, `CLOCK_ADVANCE`. The narrator never reads `orbits.yaml` or `encounters.yaml`. The narrator cannot derive a body position, estimate a transit time, decide whether a window is open, or skip/reroll a danger beat outcome. This is enforced by what's injected into its scene context — the narrator simply has no orbital data to hallucinate from.

## 2. Content schema

### 2.1 `orbits.yaml` — pure mechanics

Plotter's only input. Renderer also reads it for body positions. Narrator never sees it.

```yaml
# sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml
version: "0.1.0"
clock:
  epoch_days: 0          # t=0 reference

travel:
  realism: orbital        # narrative | hybrid | orbital
  travel_speed_factor: 1.0   # tunes absolute transit times (per world)
  danger_density: 0.012      # baseline danger beats per hour
  hazard_arc_density: 0.10   # additional density inside hazard arcs

bodies:
  coyote:
    type: star
    label: "COYOTE"
    label_color: red

  red_prospect:
    parent: coyote
    type: companion          # sub-stellar / red dwarf
    semi_major_au: 1.2
    period_days: 380
    epoch_phase_deg: 270
    eccentricity: 0          # default 0; only specify when non-circular
    label: "RED PROSPECT"
    label_color: red

  turning_hub:
    parent: red_prospect      # moon of Red Prospect — drill-in scope
    type: habitat
    semi_major_au: 0.04
    period_days: 6
    epoch_phase_deg: 0

  ember:
    parent: red_prospect
    type: habitat
    semi_major_au: 0.08
    period_days: 18
    epoch_phase_deg: 90

  far_landing:
    parent: coyote
    type: habitat
    semi_major_au: 2.4
    period_days: 980
    epoch_phase_deg: 45

  broken_drift:
    parent: coyote
    type: arc_belt           # not a point — sweeps an arc
    semi_major_au: 1.5
    period_days: 600
    epoch_phase_deg: 30
    arc_extent_deg: 90       # belt covers 90° of orbit
    hazard: true
    hazard_table: hazard_broken_drift   # encounter table override when in arc

  # ... other named bodies: deep_root_world, gravel_orchard,
  #     dead_mans_drift, new_claim, compact_anchorage, the_counter
```

**Fields:**

- `parent` — body this orbits. Determines drill-in hierarchy. Top-level bodies parent to the system primary (Coyote).
- `semi_major_au` — orbital radius (AU). Required if `parent` exists.
- `period_days` — orbital period. Required if `parent` exists.
- `epoch_phase_deg` — angular position at `clock.epoch_days = 0`. Required if `parent` exists.
- `eccentricity` — defaults to 0 (circular). v1 supports circular only; eccentric bodies render correctly in v1 but `position()` uses circular approximation. True Kepler solver is a future slice if any body needs it.
- `type` — `star`, `companion`, `habitat`, `arc_belt`, `gate`, `wreck`, etc. Drives renderer glyph choice; some types (e.g., `arc_belt`) get hazard-arc treatment.
- `arc_extent_deg` — required for `arc_belt`. Belt covers this many degrees centered on `epoch_phase_deg + 360 * t / period`.
- `hazard: true` — flag the body for hazard-arc intersection logic.
- `hazard_table` — name of an encounter table in `encounters.yaml` to use when route is inside this body's hazard window.

**Ranges and defaults at engine layer:**

- `travel_speed_factor` is dimensionless; default 1.0. Higher = faster transits. World-tuned; genre default supplied.
- `danger_density` is danger beats per hour; floor at 0, no ceiling enforced (sanity-checked at load).
- Period values are in *days*, not seconds; engine converts internally.

### 2.2 `chart.yaml` — pure flavor

Renderer reads. Plotter ignores. Narrator never sees.

```yaml
# sidequest-content/genre_packs/space_opera/worlds/coyote_star/chart.yaml
version: "0.1.0"
annotations:
  - kind: engraved_label
    text: "the Last Drift"
    curve_along: orbit_outermost      # render along outer orbit arc
    style: engraved_curved

  - kind: engraved_label
    text: "broken drift"
    curve_along: body:broken_drift
    style: engraved_curved

  - kind: glyph
    at: { ra_deg: 135, au: 5.0 }       # absolute polar coordinates
    text: "?"
    caption: "absent gate"
    style: question_mark

  - kind: scale_ruler
    at: { ra_deg: 350, au: 4.5 }
    label: "scale (engraved) — 0 1 2 3 4 5 AU"

  - kind: bearing_marks
    body_ref: coyote
    bearings: [0, 90, 180, 270]        # cardinal bearings around primary
```

**Annotation kinds:**

- `engraved_label` — text rendered along an orbital curve or in straight-line; engraved typography.
- `glyph` — single character or short string at a specified location.
- `scale_ruler` — dimensional reference at a fixed location.
- `bearing_marks` — cardinal/ordinal angular markers around a body.

`chart.yaml` adds zero mechanical effect. Removing the `?` glyph at the absent-gate location does not change plotter behavior. The plotter wouldn't route there *anyway* because no body in `orbits.yaml` exists at that location. The `?` is purely a player-facing hint.

### 2.3 `encounters.yaml` — random tables

Read only by the danger-beat scheduler. Narrator receives `scenario_ref` resolved to a payload; never reads the table directly.

```yaml
# sidequest-content/genre_packs/space_opera/worlds/coyote_star/encounters.yaml
version: "0.1.0"
tables:
  transit:                                # default in-system transit
    - { weight: 60, result: nothing }
    - { weight: 15, kind: navigational, scenario_ref: ore_haulers_passing }
    - { weight: 10, kind: hazard,       scenario_ref: micrometeor_swarm }
    - { weight: 10, kind: contact,      scenario_ref: distress_call }
    - { weight: 5,  kind: combat,       scenario_ref: corsair_intercept }

  hazard_broken_drift:                    # used when in broken-drift hazard window
    - { weight: 30, result: nothing }
    - { weight: 50, kind: hazard,       scenario_ref: drift_debris_strike }
    - { weight: 20, kind: navigational, scenario_ref: drift_anomaly }
```

**Resolution:**

1. Scheduler picks a danger-beat slot.
2. If a scheduled event (conjunction / hazard transit / gate window from `orbits.yaml`) sits in this slot, it takes priority — slot resolves to the scheduled event payload.
3. Otherwise, scheduler determines which table applies (default `transit` or hazard-table override from intersected hazard bodies) and rolls weighted-random.
4. `result: nothing` resolves to no interrupt; transit continues.
5. Anything else resolves to a `TRAVEL_INTERRUPT` payload with `kind`, `scenario_ref`, and route context. Sent to narrator via scene context injection (ADR-067 pattern).

**Scenario refs** point at scenario fixtures (ADR-069 territory). v1 may stub scenarios as plain narrator-prompt scaffolds; full scenario integration is concurrent with ADR-069 maturity, not gated on it.

## 3. Time and beat taxonomy

### 3.1 Clock unit

- **Internal:** hours, stored as integer or float on server.
- **Reference:** `clock.epoch_days = 0` from `orbits.yaml`. All position math is `position(body, t_hours - epoch_hours)`.
- **Display:** scale-appropriate, formatted by UI display utility. Engine never returns formatted strings.

| Duration range | Unit |
|---|---|
| < 60 min | minutes |
| 1h – 24h | hours |
| 1d – 14d | days |
| 14d – 90d | weeks |
| 90d+ | months / years |

Standard Day = 24h. Per-habitat rotation periods (Mendes' Post 26h shifts, etc.) are narrator flavor only — never affect clock or beat duration.

### 3.2 Beat kinds

Every clock advance is a beat. No silent advances.

| Beat | Default duration | Source of duration |
|---|---|---|
| `encounter` | 1h | Narrator can override per-scene ("the negotiation runs six hours"); OTEL span records final duration |
| `rest` | 8h | Fixed |
| `travel` | computed | `route_options()` returns `transit_hours`; not narrator-overridable |
| `downtime` | player-declared | Player input parsed into hours; capped at world-defined max if any |

### 3.3 Beat OTEL spans

Each beat emits a `clock.advance` span:

```
clock.advance
  beat_kind: travel | encounter | rest | downtime
  duration_hours: float
  t_before_h: float
  t_after_h: float
  trigger: <scene_id | player_action_id | route_id>
```

Plus subsystem-specific spans (see §7.3).

## 4. Travel mechanics

### 4.1 Position function

Pure, deterministic, server-side.

```python
def position(body_id: str, t_hours: float) -> tuple[float, float]:
    """Return (au_from_parent, theta_deg) at story-time t.
    Recurses up parent chain so moons return position relative to system primary
    when caller requests system-scope coordinates.
    Circular orbit: theta = epoch_phase_deg + 360 * t_days / period_days.
    """
```

- Inputs: `body_id`, `t_hours`.
- Output: polar coordinates `(au, theta_deg)` either body-local (under parent) or global (under system primary), per caller.
- Pure function; no side effects beyond OTEL emission.
- Circular-orbit math; eccentricity > 0 falls back to circular in v1 with a `WARN` log.

### 4.2 Route options

Returns 1–4 categorical options for getting from body A to body B at time t:

```python
@dataclass
class RouteOption:
    kind: Literal["hohmann", "direct", "gravity_assist", "gate"]
    transit_hours: float
    difficulty: Literal["easy", "moderate", "hard", "brutal"]
    available_now: bool
    window_in_days: float | None        # None if available_now
    fuel_cost_relative: float           # 0.0 - 1.0, world-tuned
    constraints: list[str]              # human-readable, narrator-consumable
    delta_v_proxy: float                # exposed only when "show numbers" on
```

Options always considered:

- **Hohmann transfer** — cheap fuel, slow, requires alignment window. `available_now` only at conjunction; otherwise `window_in_days` to next conjunction.
- **Direct burn** — always `available_now`; flat multiplier of Hohmann time, higher fuel.
- **Gravity assist** — situational; geometry check (current angular separation in viable Oberth window with a third body). When available, fastest + cheapest; otherwise `available_now: false` with `constraints: ["red_prospect on wrong side"]`.
- **Gate transit** — only if a reachable gate exists in `orbits.yaml` and destination is gate-served. Provisional in v1; gate-route fleshing-out is a sub-slice (see §9.3).

### 4.3 Simplified transit-time formula

Not real Kepler. Tuned for narrative pacing.

```
hohmann_dimensionless(a1, a2) = ((a1 + a2) / 2) ** 1.5

transit_hours_hohmann(from, to, t)
  = base_hohmann_factor × hohmann_dimensionless(from.semi_major, to.semi_major)
  × alignment_penalty(angular_separation(from, to, t))
  / world.travel_speed_factor
```

- `world.travel_speed_factor` *divides* into transit time so higher values produce faster transits, consistent with its name. Default 1.0; operatic worlds raise it; sleepy hard-SF worlds lower it.
- `base_hohmann_factor` is a server-side constant, calibrated so default `travel_speed_factor: 1.0` produces narratively-appropriate transit times for a Coyote-Star-scale system (days–weeks, not years).
- `alignment_penalty` is 1.0 at conjunction, climbs to a cap at opposition. Penalty curves chosen so off-window Hohmanns are *unavailable* (return `available_now: false`) rather than punitively expensive — Hohmann is *the* alignment mode, not the always-mode.
- Direct burn: `transit_hours_direct = transit_hours_hohmann × DIRECT_SPEED_RATIO`, with `DIRECT_SPEED_RATIO ∈ (0, 1)` (faster than Hohmann), and `fuel_cost_relative` correspondingly higher.
- Gravity assist: requires a third-body geometric check; when available, `transit_hours_assist < transit_hours_hohmann` and `fuel_cost_relative` is lowest of the three.

Golden vectors pin all three for representative Coyote Star geometries. Drift in any value is a test failure.

### 4.4 Conjunction event detection

```python
def conjunction_events(t_range: tuple[float, float]) -> list[ConjunctionEvent]:
    """Find moments in [t_start, t_end] where named body pairs hit minimum
    angular separation. Returns events with t_h, body_a, body_b, separation_deg.
    """
```

Used by:

- Plotter — report next Hohmann window for a route.
- Danger beat scheduler — emit scheduled events when a conjunction lands inside a transit window.
- World author — pre-script Bangs against predictable astronomy.

## 5. Danger beat system

### 5.1 Schedule construction

When the player commits a route (`commit_route` intent), the engine creates a travel beat and pre-rolls its full danger-beat schedule:

```python
def create_travel_beat(
    from_body: str, to_body: str, route_kind: str, t_now: float
) -> TravelBeat:
    duration_h = route_options(...)[route_kind].transit_hours

    base_count = ceil(duration_h * world.danger_density)
    hazard_intersections = trajectory_hazard_windows(from_body, to_body, route_kind, t_now)
    extra_count = sum(
        ceil(window.duration_h * world.hazard_arc_density)
        for window in hazard_intersections
    )

    total = base_count + extra_count
    slot_offsets = distribute_slots(total, duration_h, hazard_intersections)
    schedule = []
    for offset_h in slot_offsets:
        scheduled = scheduled_event_at(t_now + offset_h, trajectory)
        if scheduled:
            schedule.append(DangerBeat(t_offset_h=offset_h, kind="scheduled", payload=scheduled))
        else:
            table = encounter_table_for(offset_h, hazard_intersections)
            roll = seeded_roll(travel_beat_id, offset_h, table)
            schedule.append(DangerBeat(t_offset_h=offset_h, kind="rolled", payload=roll))
    return TravelBeat(..., danger_beats=schedule)
```

- Seeded RNG: seed derived from `(travel_beat_id, offset_h)` so a given beat is replay-stable. Travel beats created from a session save reproduce identical schedules on reload.
- `distribute_slots` weights extra slots inside hazard windows so the visible hazard arc matches encounter density.

### 5.2 Schedule playback

When the travel beat plays out (server advances clock through it):

1. Smash-cut to next non-`nothing` danger beat. Emit `clock.advance` for the elapsed gap.
2. At the danger beat, emit `travel.beat.interrupt` with full payload. Inject `TRAVEL_INTERRUPT` into narrator scene context.
3. Narrator runs the interrupt as a scene. Scene resolves with player action / outcome.
4. Resume: smash-cut to next non-`nothing` beat or to arrival.
5. On arrival, emit `clock.advance` for final gap and a `travel.beat.complete` span.

### 5.3 Pre-rolled `nothing` slots are still emitted

Every danger beat — including those that resolved to `nothing` — appears in the `travel.beat.create` schedule span. Keith and Sebastien see the full prediction at burn-commit time; they can verify the engine produced the schedule the narrator's interrupts will follow.

### 5.4 Player agency in v1

The roll is the roll. Player abilities cannot modify danger-beat outcomes in v1. `Lucky` / `Slip the Eye` / similar abilities are explicitly deferred (§9.2).

In-scene player choices during an interrupt (fight / flee / talk / hide) determine *outcomes within the scene*, not whether the scene happened. This is consistent with Story-Now design: preparation gates outcomes, not occurrence.

## 6. Map rendering and UI contract

### 6.1 Server SVG composition

Renderer assembles a single SVG document per `(world_id, scope, t_hours, plot_state)`:

```
<svg>
  <g id="layer-engraved">      <!-- orbits, named bodies, scale ruler, bearings -->
  <g id="layer-flavor">         <!-- chart.yaml annotations -->
  <g id="layer-party">          <!-- party marker (pencil annotation) -->
  <g id="layer-plot" optional>  <!-- plot overlay when plotting active -->
</svg>
```

- Output is deterministic given inputs. Snapshot tests pin canonical outputs.
- Click-target elements carry `data-body-id="<id>"` and/or `data-action="<kind>:<arg>"` attributes.
- Viewport defaults to scope-appropriate framing; UI may CSS-transform-pan/zoom freely without touching the SVG.

### 6.2 Scopes

A *scope* is the rendering view: which body is centered and what subset of bodies is rendered.

- **System scope** — primary at center; all bodies whose root ancestor is the primary; sub-systems (bodies with their own children) render as a *cluster glyph* with a "+N" affordance.
- **Body scope** — a body with children at center; that body and its direct children rendered at proper local scale; parent system shown as a directional indicator at chart edge ("← COYOTE SYSTEM, 1.2 AU").

A body is drillable iff some other body has it as `parent`. Renderer derives the drillable-set at world load.

### 6.3 Intent message protocol

UI sends intent messages over WebSocket; server returns updated SVG (or scene update for `commit_route`).

**Intent kinds (v1):**

```ts
type Intent =
  | { kind: "view_map"; scope: ScopeId }
  | { kind: "drill_in"; body_id: string }
  | { kind: "drill_out" }
  | { kind: "plot_route"; to: string }       // from = current party body
  | { kind: "commit_route"; route_kind: "hohmann" | "direct" | "gravity_assist" | "gate" }
  | { kind: "cancel_plot" };
```

UI never parses geometry. Each `data-action` attribute on a clickable SVG element maps directly to one intent.

### 6.4 Pan / zoom / reset

- Pan + zoom are CSS transforms on the SVG container. Client-only. 60fps. Server uninvolved.
- `RESET` button restores the server-provided default viewport for the active scope.
- Zoom level does not drive scope changes; drill-in is explicit (double-click on drillable body or via UI affordance).

### 6.5 Party marker

- Rendered into `layer-party` server-side.
- At a body: small reticle echo of the primary's target, miniature, off-axis (drawn-on, not engraved). Label: "← party: ZJ" or similar, in handwritten/notation style.
- In transit: rendered along trajectory arc at `t_now / transit_hours` fraction. Trail behind shows last-seen body fading out.
- In drilled-in scope where party is at a body in a different scope: rendered as off-chart edge indicator with directional cap and label ("← party at Coyote system").
- In drilled-in scope where party is at a body collapsed into the parent body's cluster glyph: marker rides the cluster glyph with a micro-label ("(at Turning Hub)").

### 6.6 Plot overlay

When `plot_route` intent fires, server returns SVG with `layer-plot` populated:

- One pencil-style dotted arc per available `RouteOption` (up to 3–4).
- Each arc terminates at destination body with a small annotation card: `route_kind`, difficulty (dots or word), `transit_hours` formatted to scale, `available_now` or `window_in_days`.
- Cancel intent removes the overlay; commit intent removes the overlay and starts the travel beat.

Cross-scope plotted routes terminate at the chart edge with a directional cap and an annotation showing destination + AU; full geometry visible only when drilled out to system scope.

## 7. Narrator contract and OTEL

### 7.1 What the narrator receives

Server-side scene context injection (ADR-067 pattern) supplies:

- **`COMPUTED_OPTIONS`** — when player input is parsed as a travel intent. Structure per §4.2 plus a context summary the narrator can quote ("Bad Girl's read on the lanes").
- **`TRAVEL_INTERRUPT`** — when a danger beat resolves to a non-`nothing` event. Includes `t_in_transit_h`, `t_remaining_h`, `kind`, `scenario_ref`, and trajectory context (route_kind, hazard_proximity, party state).
- **`CLOCK_ADVANCE`** notifications for narration framing ("eighteen days later…").

### 7.2 What the narrator must never do

- Derive a body position from orbital params.
- Estimate a transit time when the world is `realism: orbital` (estimating in `narrative` worlds is fine — there's no engine-supplied truth to contradict).
- Decide whether a window is open / closed.
- Improvise an interrupt that the engine didn't surface, or skip an interrupt the engine did surface.
- Soften an interrupt's `kind` (a `combat` interrupt cannot become a "tense conversation" — it can be played out tensely, but combat happens).
- Quietly advance the clock outside a beat.

These constraints are enforced structurally: the narrator has no orbital data to hallucinate from, and no mechanism to advance the clock without emitting a beat span.

### 7.3 OTEL spans

All emitted from server-side mechanics engine. Visible on Keith's GM dashboard.

| Span | When | Payload |
|---|---|---|
| `orbital.position.compute` | `position()` called | `body_id`, `t_h`, result `(au, theta_deg)` |
| `orbital.route.compute` | `route_options()` called | inputs, all options returned, option selected (when committed) |
| `orbital.conjunction.detect` | `conjunction_events()` called | `t_range`, events found |
| `travel.beat.create` | Travel beat constructed | `from`, `to`, `route_kind`, `transit_hours`, **full danger-beat schedule** |
| `travel.beat.interrupt` | Interrupt fires mid-transit | `t_in_transit_h`, `kind`, `scenario_ref` |
| `travel.beat.complete` | Travel beat resolves | `arrived_at`, `total_clock_advance_h`, interrupts_fired_count |
| `clock.advance` | Any beat advances the clock | `beat_kind`, `duration_h`, `t_before/after`, `trigger` |
| `chart.render` | Server emits SVG | `world_id`, `scope`, `t_h`, `plot_state`, output_size_bytes |

Lie-detector pattern: any factual claim the narrator makes about orbital state ("the window opens in 11 days") can be cross-checked against the corresponding span. Drift is a regression.

## 8. Test gate (non-negotiable for v1)

### 8.1 Unit tests

- `position(body_id, t)` — golden vectors for ~20 representative `(body_id, t_hours)` pairs across Coyote Star geometry. Pinned values; drift = test failure.
- `route_options(from, to, t)` — golden vectors for representative geometries (conjunction, opposition, gravity-assist-eligible, gravity-assist-ineligible). Pinned `transit_hours`, `available_now`, `window_in_days`.
- `conjunction_events(t_range)` — golden event lists for ~5 representative ranges.
- `danger_beat_schedule` — given seeded RNG, pinned full schedule for a representative travel beat. Encoder uses fixed RNG seed in tests; production uses `(travel_beat_id, offset_h)` seed.

### 8.2 Renderer snapshot tests

- For ~5 canonical `(world, scope, t, plot_state)` tuples, pin the SVG output. Format-stable; whitespace-normalized.
- Drift = test failure (which usually means renderer output changed; intentional changes update snapshot).

### 8.3 Wiring tests (per CLAUDE.md "Every Test Suite Needs a Wiring Test")

- End-to-end: WebSocket `view_map` intent → server renders SVG → UI receives → click `drill_in` intent → server renders new SVG. Test verifies the chain runs and produces deterministic output for a fixed clock.
- End-to-end: `commit_route` intent → travel beat creation → first `clock.advance` → first `travel.beat.interrupt` → narrator scene context contains `TRAVEL_INTERRUPT` payload.

## 9. Deferred / future slices (explicit)

These are deliberately out of v1 to keep the slice tractable. Each is named so a reader knows it was considered, not forgotten.

### 9.1 Time-advance "sweep" animation

Visual sugar. Steady-state map is static; bodies jump to new positions on snapshot updates. A 1-second SVG transition sweeping bodies forward through orbital arcs on clock advance is purely cosmetic and can ship later if it earns its keep.

### 9.2 Player abilities that modify danger-beat rolls

`Lucky`, `Slip the Eye`, sensor-stealth gear, etc. v2 surface: ability declares a deterministic effect on a specific roll class (re-roll one beat, shift table weights, suppress one beat). All effects OTEL-traced. Same crunch-wall rules apply.

### 9.3 Gate transit fleshing-out

v1 supports a `gate` route kind provisionally — flat-time transit if both endpoints are gate-served and a reachable gate exists. v2 introduces gate-specific danger tables (gate weirdness, transit anomalies), gate state (open/closed/contested), and gate-specific scheduled events.

### 9.4 Ship-time downtime sub-beats

"I spend the burn studying Bad Girl's manifest" / training / research / relationship-building during smash-cut transit. Sub-beat kind that consumes `n` hours of the smash-cut window for declared-purpose effect. Add when a player asks for it.

### 9.5 Eccentric orbits with true Kepler solver

v1 uses circular approximation regardless of declared eccentricity. Cometary orbits, smuggler-hideout long-period bodies, etc. need a real solver. Add when a body is authored that needs it.

### 9.6 Local rotation periods as mechanics

Per-body rotation periods (Mendes' Post 26h shifts) are flavor only in v1. If a future scenario needs day-night-cycle mechanics on a specific body, add per-body rotation as a separate clock, not as a override of Standard Day.

### 9.7 Sensor / fog-of-war on chart

v1 chart shows all bodies in `orbits.yaml` to the player. A fog-of-war layer (party knows about a body iff visited or briefed) is a v2 feature; affects renderer (filter `layer-engraved` and `layer-flavor` by player knowledge state) without touching mechanics.

### 9.8 Narrative tier full-bypass UI

For worlds with `realism: narrative`, the chart still renders (engraved aesthetic is genre-agnostic) but the plotter returns one option ("travel to X — narrator-determined") and the narrator hand-waves duration. v1 ships engine support; UI affordances for narrative-tier plotting may be minimal.

### 9.9 Multi-leg route plotting

v1 supports point-to-point. "I want to go to Far Landing via Compact Anchorage to refuel" is multi-leg and requires sequential beat-creation logic. Add when first asked.

## 10. Slicing recommendation

Three implementation tracks, sliceable largely independently:

| Track | Description | Depends on |
|---|---|---|
| **A. Clock + beat taxonomy + OTEL** | `clock.advance` span, four beat kinds, internal time storage in hours, scale-appropriate display utility. | Nothing. Foundational. |
| **B. Server SVG renderer + intent protocol + drill-in** | `chart.render`, intent message types, `view_map` / `drill_in` / `drill_out` cycle, party-marker rendering. Returns engraved chart at static `t`. | Track A (clock value to render at). Body params from `orbits.yaml` but no plotter math yet. |
| **C. Orbital math + plot options + danger beats** | `position()`, `route_options()`, `conjunction_events()`, danger-beat scheduler, encounter table resolution, `commit_route` intent, narrator context injection for `COMPUTED_OPTIONS` and `TRAVEL_INTERRUPT`. | Tracks A + B. |

Suggested ordering for plan generation:

1. Track A (clock, beats, OTEL) — small, foundational, unblocks playtest of beat-driven time advance independent of map.
2. Track B (renderer, intent protocol, drill-in) — ships the engraved chart with party marker. Independently playtestable.
3. Track C (orbital math, plotter, danger beats) — the meat. Depends on both prior tracks.

Within Track C, sub-slices by independence:

- C1: `position()` + `conjunction_events()` + golden vectors.
- C2: `route_options()` + plot overlay rendering (Track B extension).
- C3: Danger beat scheduler + encounter table loading + `travel.beat.create` span.
- C4: Travel beat playback + `TRAVEL_INTERRUPT` injection + narrator scene context wiring.

Coyote Star content (`orbits.yaml`, `chart.yaml`, `encounters.yaml`) is authored in parallel with Track C, gated only on schema lock from §2.

## 11. Open questions for the implementation plan

These are decisions the implementation plan should make explicit; not blockers for the spec:

- **Where exactly does scene-context injection sit** in the dispatch pipeline (per ADR-067)? `COMPUTED_OPTIONS` likely injects at travel-intent parse time; `TRAVEL_INTERRUPT` at danger-beat fire time. Plan should name the dispatch hooks.
- **What's the WebSocket message shape** for SVG delivery — inline string, base64, or out-of-band fetch? Inline string is simplest for v1; revisit if payloads exceed ~100KB.
- **How does UI debounce pan/zoom** to avoid hammering the server with unnecessary `view_map` intents during normal panning? Pan/zoom is client-only per §6.4 — only scope changes round-trip — so this should be a non-issue, but plan should confirm.
- **`base_hohmann_factor` calibration value.** Plan should pick a starting value and test against Coyote Star content to verify "days–weeks, not years" target. World-builder will iterate.
- **Failure mode when world has `realism: orbital` but missing required fields** in `orbits.yaml`. Per CLAUDE.md "No Silent Fallbacks": fail loudly at world load with a clear error naming the missing field and body.
