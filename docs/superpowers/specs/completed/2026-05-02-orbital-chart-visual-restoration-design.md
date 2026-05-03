# Orbital Chart Visual Restoration — Design Spec

**Date:** 2026-05-02
**Author:** Adora Belle Dearheart (UX Designer)
**Predecessor work:** `2026-05-01-orbital-map-design.md` (architecture), Track A/B plan (shipped)
**Status:** ready for SM to file as story
**Audience:** Dev (Ponder Stibbons), Architect (Leonard of Quirm) for sign-off on conjunction-search shape

---

## 1. Problem

The Track A/B orbital map shipped a working server-rendered chart (`sidequest-server/sidequest/orbital/render.py` 438 LOC; `sidequest-ui/src/components/OrbitalChart/OrbitalChartView.tsx` 134 LOC) that replaced the deleted client-side `OrreryView.tsx` (817 LOC, PR #180). The new chart is functionally correct but visually and informationally degraded vs. the original. Three regressions, only one of which is acknowledged in code:

| Regression | Acknowledged in code? |
|---|---|
| Eccentric geometry → circular approximation | Yes — explicit deferral comment in `render.py:9-12` ("Plan 2 / Track C") |
| Visual register (HUD palette, per-body glyphs, anomaly markers) | No |
| Time legibility — chart shows position but never shows the clock that's driving it | No |

The third regression is the worst and the one nobody named: **the entire reason rendering moved server-side is that bodies now move with the calendar — and the chart doesn't tell the player what time it is.**

## 2. Goals

In playgroup-rubric order:

1. **Sebastien (mechanics-first):** restore "the math under this is real." Eccentric orbits drawn from `eccentricity` field already in `BodyDef`. Stardate visible. Next conjunction event surfaced with countdown.
2. **James (narrative-first):** per-body identity restored. A gas giant looks different from an asteroid belt looks different from a derelict wreck. Anomalies (Tsveri-blank, Lagrange points) get glyphs, not generic dots.
3. **Alex (slower reader):** drill affordance becomes obvious — hover state, cursor change, tooltip with body name. No more guessing which dots are clickable.
4. **Keith (you):** pan/zoom regression fixed. Labels stay legible at any zoom; click targets stay clickable.

## 3. Decision: chart-as-calendar

Confirmed by Keith 2026-05-02. The chart is the canonical "where are we, when are we" surface. The clock readout and next-conjunction countdown live *on the chart*, not in a separate panel. No second place to look.

## 4. Wireframe — full-system scope

```
┌──────────────────────────────────────────────────────────────────┐
│ ⟦ STARDATE 247.6 · DAY 247 · 14:00 ⟧                  ⟦ RESET ⟧ │  ← HUD top strip (React overlay, ticks live)
│                                                                  │
│                          ✦ COYOTE STAR                           │  ← engraved label (server SVG)
│                                                                  │
│                              ★                                   │  ← star (red disk + corona)
│                          ╱       ╲                               │
│                       ◯           ◯                              │  ← inner planets (eccentric ellipses)
│                                                                  │
│                  ⊛ ←── party                                     │  ← party marker, brass crosshair
│                                                                  │
│                 ◉━━━━━━━━━ band ◉                                │  ← gas giant w/ rings + arc-belt
│                                                                  │
│                            ⬢ Tsveri-blank                        │  ← anomaly glyph
│                                                                  │
│                                                                  │
│ ⟦ NEXT CONJUNCTION ⟧                            ━━━ 1 AU ━━━     │  ← HUD bottom strip
│  Bright Margin ↔ Outer Gate                                      │      (React overlay)
│  T+12d 04h                                                       │
└──────────────────────────────────────────────────────────────────┘
```

Drill-in scope (e.g. centered on Bright Margin) replaces the body cluster with the planet at center + its moons / Lagrange points / orbital habitats around it. HUD strips persist unchanged — the date and next conjunction are global, not scope-dependent.

## 5. Visual tokens

Three sources of truth, in this order: (a) genre theme system (ADR-079), (b) per-world `chart.yaml` overrides if needed, (c) renderer fallback constants below. Coyote Star uses Star Wars HUD register.

### Palette
| Token | Hex | Use |
|---|---|---|
| `chart.bg` | `#000000` | background |
| `chart.brass` | `#f5d020` | orbits, planet glyphs, labels, infrastructure |
| `chart.red` | `#e62a18` | star, hazard-flagged bodies, anomaly outlines, danger HUD |
| `chart.party` | `#ffffff` | party marker only — reserved color |
| `chart.dim` | `#7a6810` | inactive scope hints, dimmed labels |

Existing `BodyDef.label_color` overrides apply per-body. `hazard: true` forces glyph fill to `chart.red` (auto-semantic).

### Typography
| Token | Family | Use |
|---|---|---|
| `chart.font.display` | `Orbitron, monospace` | HUD strips, body labels, scale ruler |
| `chart.font.numeric` | `VT323, monospace` | stardate, countdown, bearing degrees |

Web fonts are loaded by the UI (`@font-face` in `index.css`); renderer just emits `font-family` attributes. **Until web fonts ship**, both fall back to `monospace` — the rest of the restoration still lands.

### Label halos
Single SVG `<filter id="halo">` defined once in defs:
```xml
<filter id="halo" x="-20%" y="-20%" width="140%" height="140%">
  <feMorphology operator="dilate" radius="1.5" in="SourceAlpha" result="thicken"/>
  <feGaussianBlur in="thicken" stdDeviation="1.2" result="halo"/>
  <feFlood flood-color="#000000" flood-opacity="0.85"/>
  <feComposite in2="halo" operator="in" result="haloFilled"/>
  <feMerge><feMergeNode in="haloFilled"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
```
Applied to all body labels and HUD text. Lifts type off colored orbits.

## 6. Per-body glyph spec

The data model already carries six `BodyType` values. The renderer currently only handles three (STAR, COMPANION, ARC_BELT) and falls through to a generic yellow dot for the other three. Below: one glyph per type, plus three new annotation-driven glyphs.

| `BodyType` (existing) | Glyph |
|---|---|
| `STAR` | r=12 disk, fill `chart.red`, plus radial corona via `<radialGradient>` (3 stops, brass→red→transparent). Centered. |
| `COMPANION` | r=6 disk, fill `chart.red`. Same color as primary, smaller. |
| `HABITAT` | r=4 brass square (rotated 45° to read as diamond) with 1px brass stroke. Reads "man-made." |
| `ARC_BELT` | dotted arc spanning `arc_extent_deg` from `epoch_phase_deg`, dot spacing 4px, fill `chart.brass`. **Honors `arc_extent_deg` (currently ignored).** |
| `GATE` | hexagon outline (r=5, stroke `chart.brass`), 1px stroke, no fill. Reads "infrastructure." |
| `WRECK` | jagged 5-point asterisk, stroke `chart.dim`, no fill. Reads "dead, not for you." |

Plus, gas-giant treatment within `HABITAT` or via new annotation kind: bands rendered as 3 horizontal `<line>` elements across the body disk, brass + 60% opacity. Triggered when `BodyDef` carries an explicit `subtype: gas_giant` or by chart.yaml annotation.

| New annotation `kind` | Glyph |
|---|---|
| `anomaly_marker` | hexagon r=8 stroke `chart.red`, fill `chart.bg`, with single-character text label (e.g. "Ψ" for Tsveri-blank) centered. |
| `lagrange_point` | small triangle r=3, stroke `chart.brass`, fill `chart.bg`, label `L1`/`L4`/`L5`. |
| `flight_corridor` | dashed line between two body coordinates, stroke `chart.dim`, dasharray `4,4`. |

**Hazardous override:** any body with `hazard: true` swaps fill to `chart.red`. Single semantic rule, applies regardless of type.

## 7. HUD surfaces

Two thin surfaces that are **React overlays, not server SVG.** Server SVG re-renders only on scope change or significant clock advance; React overlays tick smoothly off `t_hours` from props.

### Top strip
Layout: full-width, height 28px, transparent background, brass border-bottom 1px.
Content (left-aligned):
- `STARDATE {epoch_days + t_days:.1f}` (display font)
- `·` separator
- `DAY {floor(t_days)}`
- `·` separator
- `{HH:MM}` formatted from `t_hours % 24` (numeric font, ticks every minute)

Right-aligned: `RESET` button (existing — keep, but restyle to match HUD: brass outline, transparent fill, brass text).

### Bottom strip
Layout: full-width, height 36px, transparent, brass border-top 1px.
Content (left side):
- Label `NEXT CONJUNCTION` in display font, dim brass
- Below: `{body_a_label} ↔ {body_b_label}` (display font, brass)
- Below: `T+{Nd HHh}` countdown (numeric font, brass; turns `chart.red` when T+ < 24h)

Content (right side): scale ruler — `━━━ 1 AU ━━━` style, length scales with current viewport zoom (1 AU at 100% zoom).

If no conjunctions are configured for a world, the bottom-left content is hidden. Scale ruler always shows.

## 8. Data model changes

### `OrbitsConfig` — new optional field
```python
class ConjunctionPair(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body_a: str
    body_b: str
    label: str | None = None  # display name override; defaults to a's + b's labels

class OrbitsConfig(BaseModel):
    # ... existing ...
    conjunctions: list[ConjunctionPair] = Field(default_factory=list)
```

Validator: `body_a` and `body_b` must be in `bodies`, must share a common ancestor (otherwise conjunction is meaningless), must not be the same body.

### `Annotation` — extend recognized kinds
No schema change. `Annotation.kind` is already free-form `str`. Renderer adds handling for `anomaly_marker`, `lagrange_point`, `flight_corridor` (see §6). Unknown kinds continue to be skipped silently — *no, scratch that.* Per CLAUDE.md "no silent fallbacks": unknown annotation kinds should raise during chart load, not silently disappear at render time.

**Action item for Architect:** decide whether to enum-ify `Annotation.kind` to enforce known values, or add a load-time validator that fails loudly on unknown kinds.

### `BodyDef` — optional subtype
```python
class BodyDef(BaseModel):
    # ... existing ...
    subtype: str | None = None  # e.g. "gas_giant", "rocky", "ice_giant"
```
Free-form string, used by renderer for variant glyph selection. Defaults to None (no variant).

## 9. Server changes

### New module: `sidequest/orbital/position.py`
Port the geometry primitives from the deleted `geometry.ts`:
- `kepler_position(body: BodyDef, t_hours: float) -> tuple[float, float]` — replaces `_body_position_au_polar`. Honors `eccentricity`. Solves Kepler's equation iteratively (Newton's method, 5-iter cap, tolerance 1e-6 rad).
- `ellipse_geometry(body: BodyDef, scale: float) -> EllipseSpec` — returns center offset (focus shifted from hub by `c = a·e`), semi-major px, semi-minor px (`b = a·√(1-e²)`), rotation (currently always 0; reserve for argument-of-periapsis later).
- `moon_kepler_offset(moon: BodyDef, parent_pos: tuple[float, float], t_hours: float) -> tuple[float, float]` — moon position relative to parent, NOT to system center. Used when scope is centered on the parent.
- `lagrange_position(parent_pos, point: Literal["L1","L4","L5"]) -> tuple[float, float]` — geometric placement only (no stability math).

Snapshot tests pin known orbits (Coyote Star bodies at t=0, t=180d, t=365d).

### New module: `sidequest/orbital/conjunction.py`
- `next_conjunction(orbits, t_hours, search_horizon_days=365) -> ConjunctionEvent | None`
  - For each pair in `orbits.conjunctions`, find the next minimum of angular separation as seen from their common ancestor (usually the star).
  - Algorithm: coarse grid scan (1-day step) to bracket minima, then golden-section refinement to ±0.1 hour.
  - Returns the soonest event across all pairs.
  - Returns `None` if no conjunctions configured or none within horizon.
- `ConjunctionEvent` dataclass: `body_a_id`, `body_b_id`, `label`, `t_hours_event`, `t_hours_until`.

### `render.py` changes
Itemized — keep diffs surgical:

1. Replace `_body_position_au_polar` (lines 72-85) with `position.kepler_position`.
2. In `_render_engraved_layer` (line 233-244): replace the `Circle(r=radius_px)` orbit ring with `Ellipse(center=ellipse_center, rx=semi_major_px, ry=semi_minor_px)` from `position.ellipse_geometry`. Keeps the brass stroke.
3. In `_body_glyph` (lines 302-312): expand the type-switch to cover all six `BodyType` values per §6 spec. Honor `body.subtype` for gas-giant ring overlay.
4. Add `<defs>` with halo filter at top of drawing; apply via `filter="url(#halo)"` to all body label text and any HUD-tier text.
5. In `_render_annotation` (line 324-378): add cases for `anomaly_marker`, `lagrange_point`, `flight_corridor`. Replace the silent `return None` for unknown kinds with an exception (per "no silent fallbacks").
6. Replace generic `"yellow"` strings with palette token lookups. Suggest a small `palette.py` module with the constants from §5.
7. Replace party marker (lines 400-437) with a brass-stroked crosshair (no cursive label — promote `← party` text to brass, halo'd, display font).

### Wire `t_hours` and conjunction event into `ORBITAL_CHART` message
Currently the message ships SVG + `scope_center`. Add:
- `t_hours: float` (so client can drive HUD strip ticks)
- `next_conjunction: { body_a_id, body_b_id, label, t_hours_until } | null`

Backend computes `next_conjunction` on each render. UI uses `t_hours_until` as a starting point and decrements via local `setInterval` between server pushes. When clock advances server-side via beats, server pushes a fresh `ORBITAL_CHART` and the countdown re-syncs.

## 10. UI changes

`OrbitalChartView.tsx` gains two new overlay components and three props:

```typescript
interface OrbitalChartViewProps {
  svg: string;
  scopeCenter: string;
  tHours: number;                    // NEW
  epochDays: number;                 // NEW (for stardate display)
  nextConjunction: ConjunctionEvent | null;  // NEW
  onIntent: (intent: OrbitalIntent) => void;
}
```

Layout: chart container becomes a 3-row CSS grid (`28px 1fr 36px`). Top row: `<HudTopStrip>`. Middle: existing SVG host with pan/zoom. Bottom: `<HudBottomStrip>`.

`<HudTopStrip>`: stateless, derives stardate / day / time from `tHours + epochDays`. No interval needed if precision is `HH:MM` (server pushes ~every beat).

`<HudBottomStrip>`: holds local state for countdown; `setInterval(1000)` decrements `tHoursUntil`; resets to prop value on prop change. Switches color to red when `tHoursUntil < 24`.

### Pan/zoom regression fix
Replace CSS `transform: translate(x,y) scale(s)` on the host div with imperative `setAttribute('transform', ...)` on an inner `<g>` element of the server SVG. Requires the server to wrap its layers in a single `<g id="viewport">` (one-line change in `render_chart`).

This restores: text scales independently of geometry (specify `vector-effect="non-scaling-stroke"` and font-size in viewport-relative units), click targets remain hit-testable at any zoom.

### Drill affordance — hover state
Drillable bodies (data-action="drill_in:*") get:
- `cursor: pointer` (CSS targeting `[data-action^="drill_in"]`)
- on hover: brass outline halo on the cluster glyph (CSS `filter: drop-shadow(0 0 2px #f5d020)`)
- on hover: tooltip via native `<title>` SVG element inside each cluster group, content = body label

No new component needed — pure CSS + one `<title>` per cluster group rendered server-side.

## 11. Acceptance criteria

Player-facing:
1. **Stardate is visible at all times.** Top-left of chart, both system-root and drill-in scopes.
2. **Next conjunction shows when configured.** Bottom-left of chart. Countdown decrements smoothly. Goes red within 24h.
3. **Orbits are eccentric where data says so.** Coyote Star's Bright Margin (eccentricity > 0 in orbits.yaml) renders as an ellipse with focus at the star, not a centered circle.
4. **Distinct glyph per BodyType.** All six existing types render with the §6 glyphs. Gas-giant subtype shows banding.
5. **Hazard bodies are visibly red.** Any body with `hazard: true` adopts `chart.red` fill.
6. **Drillable bodies show pointer cursor + tooltip on hover.**
7. **Pan + zoom keeps text legible.** At 4× zoom, body labels are still readable; at 0.5× zoom, click targets still hit.
8. **Anomaly markers render** for any chart.yaml entry of kind `anomaly_marker`.

Engineering:
9. Snapshot test: Coyote Star at `t_hours=0`, scope=root, no party, no conjunction — pinned.
10. Snapshot test: same world at `t_hours=24*180` (mid-year) — bodies have moved, geometry preserved.
11. Snapshot test: drill-in to Bright Margin shows moons (when authored).
12. `next_conjunction` returns the same event for the same `(orbits, t_hours)` input — deterministic.
13. Unknown annotation `kind` raises at chart-load, not at render. (Per "no silent fallbacks.")
14. OTEL: existing `chart.render` span carries new attributes `t_hours`, `next_conjunction_body_a` / `..._body_b` / `..._t_hours_until`. GM panel can verify the conjunction calc fired and the right pair won.

## 12. Out of scope (defer to follow-up if scope balloons)

- Orbitron + VT323 web font shipping. Acceptance criteria all pass with `monospace` fallback. UX accepts this trade.
- Argument-of-periapsis rotation for ellipses (all currently-known data has aligned orbits).
- Conjunction *prediction* over multiple events ("show me the next 5 conjunctions"). One event is enough for the playgroup.
- Per-body period readout in tooltip (planned future polish).
- Animated body motion (bodies snap to position on each render — no tweening).
- Chart-yaml-driven palette overrides per world. Coyote Star uses the §5 constants; if Aureate Span needs a different register, that's a follow-up.

## 13. Open questions for Architect (Leonard)

1. `Annotation.kind` — enum-ify (breaking schema change for unknown values) or add a load-time validator? Recommend the validator route for forward compat.
2. Conjunction-search horizon — should `search_horizon_days=365` be per-world configurable in `OrbitsConfig`? Coyote Star's longest period is probably < 1 year so 365d is fine, but Aureate Span may have outer bodies with multi-year periods.
3. `position.py` Newton's-method tolerance — 1e-6 rad is overkill for visual rendering but cheap. Keep, or relax to 1e-3?

## 14. Implementation phasing

Single story, three commits in order so each is reviewable:

- **Commit 1: server-side palette + glyph expansion + hazard semantic.** Pure visual restoration, no geometry change. All six BodyTypes render with proper glyphs. Existing snapshot tests update. UI unchanged.
- **Commit 2: eccentric geometry + position.py.** Ellipses replace circles. New snapshot tests for known orbits at multiple times. Wire test: `eccentricity > 0` produces measurably non-circular orbit path.
- **Commit 3: chart-as-calendar — HUD strips + conjunction.py + ORBITAL_CHART message extension.** Top + bottom strips render; countdown ticks; conjunction event computed and surfaced. Wire test: ORBITAL_CHART payload carries `t_hours` and `next_conjunction`; UI overlays render and update.

Each commit ships a working chart. Bisect-friendly.

---

**Estimate:** 5 points (server: ~300 LOC across position.py, conjunction.py, render.py changes, palette.py, models.py extensions; UI: ~150 LOC for two HUD strip components + props plumbing; tests: 8-10 new tests).

**Dependencies:** none. All data already exists in `coyote_star/orbits.yaml` (Bright Margin already has `eccentricity` set per the migration). Conjunction pairs need to be authored — small content addition.
