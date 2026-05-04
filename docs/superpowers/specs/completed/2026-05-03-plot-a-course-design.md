# Plot a Course, Kestrel — Design

**Date:** 2026-05-03
**Author:** Architect (Leonard) brainstorm w/ Keith
**Status:** Approved (brainstorm)
**Related plans:** `2026-05-01-orbital-map-design.md` (orbital chart shipped in PR #177)
**Related ADRs:** ADR-001 (Claude CLI subprocess — narrator can't call tools mid-generation), ADR-014 (Diamonds and Coal), ADR-026 (client state mirror), ADR-027 (reactive state messaging), ADR-038 (WebSocket transport), ADR-039 (narrator structured sidecar), ADR-067 (unified narrator), ADR-074 (player-facing dice intent), ADR-090 (OTEL dashboard)
**Mirrors pattern of:** `2026-05-03-internal-ship-map-kestrel-design.md` (server-rendered SVG, REST/WS reactive refetch); `sidequest/orbital/intent.py` (intent → render → response)

## Goal

Let the player ask the narrator to plot a course to a body or quest objective ("Plot a course, Kestrel — Maltese Falcon!") and have the orbital chart show it as a visible curved arc with **time** and **delta-v** cost annotations. The plot is *visual + narrative*; it does not advance the clock, mutate `party_at`, or burn fuel — that's a future "engage" feature.

## Why this and not something else

Per SOUL.md *Crunch in the Genre, Flavor in the World*: navigation is one of the genre's load-bearing scenes (the captain's chair beat). Doing it well requires (a) a visible course on the map, (b) a believable cost so decisions feel weighty, (c) the narrator selecting from a known set rather than inventing destinations.

Per the *Zork Problem*: the player can ask for *any* destination in natural language; the narrator's job is to bind that ask to a real body. Pre-computation puts the narrator in the role of *selector + presenter*, not pathfinder — which is exactly the constraint imposed by ADR-001's one-shot `claude -p` subprocess (no mid-generation tool calls).

Per *Diamonds and Coal*: courses to bodies the player has named or are quest-relevant get prompt real-estate; the rest do not. The map sees the *line*; the narrator sees the *menu*.

## Architecture

```
┌─────────────────────────────────────┐
│ orbits.yaml (existing)              │  bodies = course endpoints
│ scenario_state / world_state        │  quest anchors → body_ids
│ recent_body_mentions (NEW, session) │  ring buffer of named bodies
└─────────────────┬───────────────────┘
                  │ inputs to compute_courses()
                  ▼
┌─────────────────────────────────────┐
│ sidequest/orbital/course.py (NEW)   │
│   compute_courses() — pure          │
│   PlottedCourse model               │
│   validate_course_request()         │
└─────────────────┬───────────────────┘
                  │ <courses> block injected per turn
                  ▼
┌─────────────────────────────────────┐
│ Narrator (claude -p subprocess)     │
│   sidecar: {"intent":"plot_course", │
│             "course_id":"<body>"}   │
└─────────────────┬───────────────────┘
                  │ post-narration apply
                  ▼
┌─────────────────────────────────────┐
│ sidequest/handlers/                 │
│   course_intent.py (NEW)            │
│     validate against compute_courses│
│     accept → state_patch            │
│     reject → next-turn reaction     │
└─────────────────┬───────────────────┘
                  │ STATE_PATCH /plotted_course
                  ▼
┌─────────────────────────────────────┐
│ Snapshot.plotted_course             │
│   PlottedCourse|None (NEW field)    │
└─────────────────┬───────────────────┘
                  │ WS mirror
                  ▼
┌─────────────────────────────────────┐
│ sidequest-ui                        │
│   useOrbitalChart watches           │
│     plotted_course; refetches SVG   │
│   render_chart composes Bezier      │
│     overlay + HUD ETA/Δv chip       │
└─────────────────────────────────────┘
```

## Course = body destination + cost (Q3, Q1, Q2)

A *course* targets a **body** (one of the 25 entries in `coyote_star/orbits.yaml`). Quest objectives reduce to bodies — the prompt entry carries the quest *label* but the geometry resolves to a body endpoint.

```python
class PlottedCourse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to_body_id: str
    label: str | None = None          # narrator-supplied display, e.g. "Maltese Falcon"
    eta_hours: float
    delta_v: float                     # scifi-flavored, see cost model below
    plotted_at_t_hours: float          # for "stale plot" reasoning later
    source: str                        # "in_scope" | "recent_mention" | "quest_objective"


class CourseRow(BaseModel):
    """Computed entry for one body, exposed to narrator + GM panel."""
    model_config = ConfigDict(extra="forbid")
    to_body_id: str
    eta_hours: float
    delta_v: float
    source: str
    label_hint: str | None = None      # quest objective name if source="quest_objective"
```

**Scope decisions:**

- *Plot only, no commit.* Plotting does not advance the clock. A future "engage" intent is filed as out-of-scope below.
- *Bodies + quest goals.* Moving entities (pirate ships, named NPC vessels) are out of scope; the narrator resolves them by saying "last seen at Body X, plotting to Body X."
- *No fuel state.* `delta_v` is a number on the chart, not a deduction from a tracked resource. A future fuel-budget feature can subscribe to the same number.

## Cost model (Q2 — Hohmann-flavored, not Hohmann-accurate)

```python
TRAVEL_HOURS_PER_AU = 80.0       # tuned so Far Landing → Tethys Watch ≈ 12h
DELTA_V_BASE = 1.0               # km/s per AU of chord distance
DELTA_V_INCLINATION_FACTOR = 0.4 # extra Δv for crossing semi-major-axis bands

def compute_eta_and_dv(party_at: BodyDef, dest: BodyDef, orbits: OrbitsConfig) -> tuple[float, float]:
    a1 = party_at.semi_major_au or 0.0
    a2 = dest.semi_major_au or 0.0
    radial_au = abs(a1 - a2)
    angular_au = 0.05 * (chord_angular_distance_deg(party_at, dest, orbits) / 360.0)
    chord_au = radial_au + angular_au
    eta_hours = (chord_au * TRAVEL_HOURS_PER_AU) / orbits.travel.travel_speed_factor
    delta_v = chord_au * DELTA_V_BASE + radial_au * DELTA_V_INCLINATION_FACTOR
    return eta_hours, delta_v
```

Calibration targets (Coyote Star, with `travel_speed_factor: 1.0`):

| Hop | ETA | Δv |
|---|---|---|
| Far Landing → Tethys Watch (moon) | ~12h | ~0.4 |
| Far Landing → Deep Root | ~30h | ~1.0 |
| Far Landing → The Gate | ~90h | ~2.8 |

Tunable via `travel.travel_speed_factor` per genre/world. Per the *Cost Scales with Drama* principle, the numbers should *feel* like decisions ("96 hours" = real fuel-and-supplies thinking; "12 hours" = a quick run). They are not real Hohmann transfer windows; this is sci-fi pace, not orbital realism.

## Selection (Q4 — option C: visible scope + recent-mention + quest objective)

`compute_courses(orbits, scope, party_at, t_hours, scenario_state, recent_body_mentions, quest_anchors)` returns a `dict[body_id, CourseRow]`. A body is included if **any** of:

1. **In current `OrbitalIntent` scope** (`source="in_scope"`). When the player is drilled into Far Landing, only Tethys Watch and the system root are in scope. Mirrors existing scope semantics.
2. **Named in last N turns** (`source="recent_mention"`). The session maintains a `recent_body_mentions: deque[str]` of length 4 (configurable), populated by a one-pass body-name scanner over each turn's narrator output and player input. Cheap; no LLM involvement.
3. **Quest objective** (`source="quest_objective"`). MVP: a `world_state.quest_anchors: list[body_id]` field that the narrator manages via state patch (the existing patch surface). Future: pull from `ScenarioState` once scenario clues carry body anchors.

**Hard cap of 12 entries.** If the union exceeds 12, drop in priority order (`quest_objective` > `recent_mention` > `in_scope`) keeping the highest-priority. Cap is a token-budget guardrail; 12 entries is roughly 250 tokens of `<courses>` block.

**Determinism.** `compute_courses()` is a pure function; same inputs → same output. Sort order: `(source_priority desc, eta_hours asc, body_id asc)`.

## Prompt block

Inserted in the **Recency** zone alongside the dice instruction. Template:

```
<courses>
You can plot a course to any of these. When the player asks to plot a course
("plot a course to X", "Kestrel, lay in a course for X", "take us to X"),
include the matching course_id in your sidecar:
  {"intent":"plot_course","course_id":"<id>"}

If the player asks for a destination not in this list, say so in-fiction
("Kestrel can't lock that, captain — say a body within scanner range or a
known objective"). Do NOT invent course_ids.

- tethys_watch (ETA 12h, Δv 0.4) — orbiting Far Landing
- deep_root (ETA 30h, Δv 1.0) — quest: Hessler's manifest
- the_gate (ETA 90h, Δv 2.8) — recently mentioned
...
</courses>
```

The instruction is unconditional but inert when the courses block is empty (worlds with no orbital tier never reach this code path). The `quest:` / `recently mentioned` / `(no qualifier)` suffixes come from `CourseRow.source` so the narrator has visible context for *why* a course was offered.

## Validation (rejection behavior)

If the narrator emits a `course_id` not in this turn's `compute_courses()` output:

1. The `course_intent` handler rejects via the existing state-patch validator pipeline (no new validation layer).
2. OTEL `course.plot.rejected` span fires with `course_id`, `reason="not_in_scope"|"unknown_body"`, `available_ids=[…]`.
3. The rejection is added to next turn's **reactions** zone:
   ```
   <reactions>
   Your last plot_course request was rejected: course_id 'maltese_falcon'
   is not a known body. Available courses are listed in <courses>.
   </reactions>
   ```
4. The narrator's *prose* is preserved — the player still hears the captain saying "plotting course to the Maltese Falcon" — but the chart does not draw a phantom line. **Failure is silent on the visual layer, loud in OTEL.** This is the lie-detector pattern from CLAUDE.md (prose surface and visual surface in disagreement = catch in the GM panel).

## Persistence (Q5 — option A)

The `plotted_course` field is part of the snapshot and persists:

- **Across turns** until replaced.
- **Across save/load** (it serializes with the snapshot like any other field).
- **Across WebSocket disconnect/reconnect** (the new client mirror picks it up via STATE_PATCH on first sync).

**Cleared by** any of:

- A new `plot_course` intent (replaces the prior plot).
- A new `cancel_course` intent (`{"intent":"cancel_course"}` → state patch sets `plotted_course = None`). Filed as MVP because the narrator needs *some* way to clear a stale plot when the player abandons it; otherwise the line lingers indefinitely.
- Arrival: when `party_at == plotted_course.to_body_id` after any movement event, the snapshot apply pipeline clears it. (Movement is out of scope today, but the clear-on-arrival rule is documented now so the future "engage" feature lands cleanly.)

## Geometry (Q6 — option B: curved Bezier)

Renderer adds a course overlay layer composed onto the existing `render_chart()` SVG (no separate REST endpoint; the chart itself carries the overlay).

- One cubic Bezier from `(party_at, t_hours)` position to `(to_body_id, t_hours)` position.
- Control points offset perpendicular to the chord by `0.3 × chord_length` in the prograde direction.
- Prograde sign: `sign(cross(party_at_velocity_vec, dest_position_vec - party_at_position_vec))`. If both bodies are at the system root with no parent, default to outward (away from `coyote`).
- Stroke style: dashed, engraved register. Color: pale amber (`#d9a766`, recommendation; defer to art-director on final hex).
- Endpoint glyph: small chevron / target reticle at the destination, distinct from the body's existing label.
- HUD chip in `HudBottomStrip`: `COURSE → DEEP ROOT • ETA 38h • Δv 1.1`. Hidden when `plotted_course is None`.

Pure function: `render_course_overlay(svg_root, course, orbits, t_hours) -> None`. No I/O. Snapshot-tested with golden SVG.

## State + protocol

- **Snapshot field** (`sidequest/game/character.py` or wherever the per-session snapshot model lives — Dev finds the canonical spot during execution): `plotted_course: PlottedCourse | None = None`.
- **Sidecar intent shape**: existing dispatch already routes JSON sidecar variants. New variant `{"intent": "plot_course", "course_id": "<id>"}` and `{"intent": "cancel_course"}`.
- **State patch path**: `/plotted_course` (set or null).
- **No new WS message kind**: STATE_PATCH carries everything.
- **UI**: `useOrbitalChart` already refetches on STATE_PATCH; a 3-line addition watches the `plotted_course` field and re-asks for the chart SVG when it changes. The chart endpoint reads `plotted_course` from the bound session and includes the overlay.

## MP authority

**Last-write-wins, no role gate.** Anyone seated can ask the narrator to plot a course; the narrator decides in-fiction whether it's honored ("Sarge, you're not at the helm — Wash, override?"). State patch replaces the prior plot. No conflict-resolution machinery.

If playtest reveals trolling (each player plots a different course every turn), we add a `seated_at_command: player_id` snapshot field gated by the existing Kestrel station-occupancy model. Filed as future-when-needed; not in MVP.

## OTEL spans

Per CLAUDE.md OTEL principle (every backend fix that touches a subsystem MUST add OTEL spans):

| Span | When | Attrs |
|---|---|---|
| `course.compute` | every prompt assembly that includes the `<courses>` block | `course_count`, `in_scope_count`, `recent_count`, `quest_count`, `dropped_by_cap` |
| `course.plot` | state patch accepted | `from_body`, `to_body`, `eta_hours`, `delta_v`, `source`, `player_id` |
| `course.plot.rejected` | state patch rejected | `course_id`, `reason`, `available_ids` |
| `course.cancel` | cancel intent applied | `from_body` (the cleared destination) |
| `course.render_overlay` | chart re-render with course present | `to_body`, `bezier_control_offset_au` |

Spans live in `sidequest/telemetry/spans/course.py` (mirrors orbital's `chart.py` pattern).

## Error handling — fail loud

Per CLAUDE.md *No Silent Fallbacks*:

| Condition | Behavior |
|---|---|
| Narrator emits `course_id` not in current courses | Reject + OTEL + next-turn reaction (see Validation). NEVER silently substitute another body. |
| `compute_courses()` called for a world with no orbital tier | Returns empty dict; the `<courses>` block is omitted from the prompt. The narrator never sees the instruction. |
| `plotted_course.to_body_id` references a body that's been removed from `orbits.yaml` (post-load mutation, save migration) | Render layer drops the overlay, emits `course.render_overlay` span attr `dropped_invalid_target=true`. Snapshot apply pipeline clears the field on next state mutation. Don't display a course to nowhere. |
| Cancel intent for a session with no plotted_course | No-op state patch; OTEL `course.cancel` span attr `was_already_clear=true`. |

## Testing

Per CLAUDE.md *Every Test Suite Needs a Wiring Test*:

| Test file | Purpose |
|---|---|
| `tests/orbital/test_course_compute.py` | Selection logic: in-scope/recent/quest, 12-cap, deterministic order, empty-when-no-orbital-tier |
| `tests/orbital/test_course_cost.py` | ETA + Δv calibration: Far Landing → Tethys Watch ≈ 12h/0.4, Far Landing → The Gate ≈ 90h/2.8 |
| `tests/orbital/test_course_geometry.py` | Bezier control offset, prograde direction, edge cases (same parent, root-to-root) |
| `tests/orbital/test_course_render_overlay.py` | Golden SVG snapshot for Far Landing → Deep Root |
| `tests/handlers/test_course_intent_wired.py` | **Wiring test**: sidecar `plot_course` → state patch → snapshot field; rejection flow; cancel flow |
| `tests/agents/test_narrator_courses_block.py` | **Wiring test**: prompt assembly includes `<courses>` when world has orbital tier; omits it when not |
| `tests/server/test_recent_body_mentions.py` | Ring buffer behavior: append on each turn, length 4, dedupe-not-required |
| UI: `OrbitalChartView` vitest | Refetches on `plotted_course` STATE_PATCH; HUD chip renders ETA/Δv |

## Phasing

| # | Step | Notes |
|---|---|---|
| 1 | `PlottedCourse` model + snapshot field + STATE_PATCH plumbing | server |
| 2 | `compute_courses()` pure function + cost calculation + selection logic | server |
| 3 | `recent_body_mentions` ring buffer in session, populated post-narration | server |
| 4 | `<courses>` prompt block + narrator instruction (Recency zone) | server |
| 5 | Sidecar `plot_course` / `cancel_course` intent handler + validation + OTEL | server |
| 6 | Bezier overlay renderer + HUD chip in chart SVG | server |
| 7 | UI `useOrbitalChart` STATE_PATCH watcher for `plotted_course` | ui |
| 8 | Wiring tests + golden SVG snapshot | server, ui |
| 9 | Boot, smoke, fix one or two things | all |

**Total budget:** ~3 hours of code (≈30 min wall-clock for AI-driven work per memory tuning), plus spec/plan/PR ceremony.

## Graceful cuts (if something breaks)

In priority order, drop from the bottom:

1. **HUD chip** — overlay-only, narrator's prose carries the cost in text.
2. **`cancel_course` intent** — defer to "wait for next plot" or save reload.
3. **Quest-anchor source** — ship with in-scope + recent-mention only. Quest objectives still get named in narrator prose.
4. **OTEL spans** — file as debt, ship without (last resort; violates OTEL principle).

Minimum-viable plot: a curved arc on the chart with body-to-body geometry and a number for ETA. Everything above is amplification.

## Out of scope / Deferred

- **Engage / commit / movement.** Plotting is *visual + narrative* only. A future ADR introduces the "engage" intent, which advances the clock, mutates `party_at`, and burns ∆v from a tracked resource. Today's `delta_v` field exists so that future feature has a number to subtract from.
- **Moving target tracking.** Pirate ships, NPC vessels, and lost freighters do not carry their own orbital state. The narrator resolves them to a body-anchor in prose ("last seen at Tethys Watch") and the player plots to that body.
- **Real Hohmann mechanics.** Transfer windows, eccentricity penalties, `epoch_phase_deg`-aware cost. Filed as future-when-needed if a story actually hangs on missed-window tension.
- **Flight corridors.** `chart.yaml` already supports `flight_corridor` annotations. Snapping courses to named corridors ("the Hyades Approach") is real authoring work and only pays off if the genre starts hanging stories on named lanes. Future ADR.
- **Captain-station gating.** Today, anyone can request a plot. If MP playtest reveals trolling, gate plotting on station occupancy via the Kestrel interior model.
- **Phase-aware curve geometry.** The Bezier offset is direction-aware (prograde) but not phase-magnitude-aware. A polish pass after playtest data tells us whether the visual reads right.
- **Multi-leg courses.** A single plot is one leg, body-to-body. Routing through waypoints (e.g., refuel stop) is future.

## Open choices flagged for spec review

1. **Course color** — recommended pale amber `#d9a766`; defer to art-director on final hex against the engraved register palette.
2. **`recent_body_mentions` ring buffer size** — default 4 turns. Smaller = more responsive to current scene; larger = more forgiving across digressions.
3. **Quest-anchor mechanism** — recommended `world_state.quest_anchors: list[body_id]` in MVP, narrator-managed via state patch. The "scenario-tagged body" version waits for a `ScenarioState` schema extension (separate ADR).
4. **Player UI affordance** — none. Per the Zork Problem, no "plot course" button. Player asks in natural language, narrator handles it. Confirming this is correct (vs. e.g. a chat-command shorthand).

## Acceptance

- A player saying "Kestrel, plot a course to Tethys Watch" causes a curved Bezier arc to appear on the orbital chart from the party's current body to Tethys Watch.
- The chart HUD shows `COURSE → TETHYS WATCH • ETA 12h • Δv 0.4`.
- The narrator's prose mirrors the plot ("Plotting course, captain — twelve hours at burn, Δv four-tenths").
- Asking "plot a course to the Maltese Falcon" (not in the courses block) yields an in-fiction refusal; no phantom line; OTEL `course.plot.rejected` span fires.
- The plot persists across turn boundaries and across save/load.
- A second `plot_course` intent replaces the first; `cancel_course` clears it.
- OTEL `course.compute`, `course.plot`, `course.plot.rejected`, `course.cancel`, `course.render_overlay` spans visible in the GM dashboard.
- No silent fallbacks: bad data fails loudly per the table in *Error handling*.
