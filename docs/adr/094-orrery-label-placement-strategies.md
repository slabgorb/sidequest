---
id: 94
title: "Orrery Label Placement — Three-Strategy Taxonomy"
status: accepted
date: 2026-05-04
deciders: ["Keith Avery", "The Man in Black (Architect)"]
supersedes: []
superseded-by: null
related: [86, 88, 90]
tags: [frontend-protocol, observability]
implementation-status: deferred
implementation-pointer: null
---

# ADR-094: Orrery Label Placement — Three-Strategy Taxonomy

## Context

The orrery v2 visual restoration (story 45-43, merged 2026-05-04) ports the
engraved-brass orbital chart back to Python. It retained two label-placement
strategies from the Rust prototype:

1. **Curved (textPath)** — `engraved_label` annotations with `curve_along`
   point at an orbit ring or a body's moon ring; the label wraps along the
   resolved SVG path via `<textPath>`.
2. **Radial-out** — every body with a `label:` field renders a label at
   `body_radial + glyph_radius + LABEL_RADIAL_PADDING_PX`, anchored on the
   bearing from chart center to body. Peer collisions within
   `MIN_ANGULAR_SEPARATION_DEG` (25°) trigger radial tier-bumping
   (`render._assign_collision_tiers`, capped at `LABEL_TIER_MAX = 3`).

A live render of the campaign world (`coyote_star`, the active playgroup
campaign) at the system-scale shown in screenshots from 2026-05-04 surfaced
three structural failures of this two-strategy design. They are not
configuration bugs — they are the fully-instantiated cost of the design.

### Failure 1 — radial-out fails when angular separation is just above
the tier threshold but label width exceeds available arc

`coyote_star` has three bodies clustered around 1.00 AU at bearings 45°, 75°,
105° (`far_landing`, `deep_root_world`, `gravel_orchard`). Adjacent pairs
are 30° apart — *just* above the 25° tier-bump threshold — so all three
bodies stay at tier 0. At ~1 AU rendered radius the available arc-length
between adjacent labels is shorter than the label-width of "GRAVEL
ORCHARD" / "DEEP ROOT" / "FAR LANDING". Result: three haloed labels
overlap, their stroke-halos paint over each other, and the inner system
becomes unreadable. The 25° threshold is angular-only; it has no concept
of "would these labels actually fit at this radius."

### Failure 2 — curved (textPath) fails when path circumference is shorter
than text length

The annotation `curve_along: body:broken_drift` resolves to broken_drift's
own minor-axis ring (the conceptual moon-band ring around it, used for
labelling the body itself rather than its orbit). At system scale that
ring's circumference is shorter than "broken drift" text-width × 1×; the
textPath wraps past its own start, letters mirror, and the label renders
upside-down or backwards (`Brokendrig` → `pirdnekorB`). The renderer has
flip-detection comments at `render.py:467` ("so textPath letters stay
upright in the player's reading direction") but no path-shorter-than-text
guard.

### Failure 3 — radial-out is structurally unable to serve
companion-children habitats

`red_prospect` is a `companion`-type body (binary companion star) at 5.24
AU with **six named, narratively-important habitats** parented to it
(`turning_hub`, `whitedrift`, `ember_moon`, `the_horn`, `dead_lash`,
`vael_thain`). Their semi-major axes are 0.0071–0.0271 AU. At a chart
that's 10 AU outermost, those distances are sub-pixel — the render path
collapses them into the unlabeled `_render_moon_band` ring. The
playgroup loses the ability to navigate to "Vael Thain" or "Ember
Moon" because they cannot identify which dot is which. Radial-out
labels can't help: the radial floor is the body's render position,
which is essentially zero.

This is not a fixable case for either existing strategy — it is the
absence of a strategy.

### Audience and lie-detector implications

CLAUDE.md identifies the GM panel as the lie detector and Sebastien
(mechanics-first player) as its load-bearing audience. The orrery is a
navigation surface; if the chart renders but the names of destinations are
unreachable, the narrator's "you set course for Vael Thain" claim has no
in-chart corroboration. The visual layer must answer "where is X" without
requiring zoom, scope-shift, or reading the YAML — at the same scale the
narrator is acting on. This ADR resolves that with explicit per-body
strategy attribution emitted as OTEL spans, so the GM panel can show the
strategy distribution per render.

## Decision

The orrery renderer adopts a **three-strategy taxonomy** for body labels,
with explicit selection rules and OTEL attribution. The third strategy —
**leader-line callouts** — is added; the existing two are retained.

### The three strategies

| Strategy | Anchor | Label position | When |
|---|---|---|---|
| `textpath` | the body glyph itself | curved along an explicit `curve_along` SVG path | annotation opts in via `kind: engraved_label` + `curve_along: …` AND path circumference ≥ text-width × 1.2 |
| `radial` | the body glyph itself | along the bearing-from-center ray, offset by `body_radial + glyph_radius + padding + tier·offset` | body has a `label:` field AND the resolved label fits the available arc length AND parent.type ≠ companion |
| `callout` | a small **anchor mark** at the body position | a **label block** placed in a margin gutter zone, joined by an orthogonal **leader line** | fallback when 1 and 2 don't apply, OR forced when parent.type == companion (first-class-destination rule) |

The taxonomy is orthogonal to the existing **register** axis (`engraved`
/ `chalk` / `prose` per ADR-026's port-era predecessor and `models.py:44`).
A label uses one *strategy* and one *register*; the register supplies font
/ color / weight / opacity, the strategy supplies geometry.

### Selection rule

Per body, in this order — first match wins:

1. **Forced callout** — if `body.parent.type == "companion"`, strategy =
   `callout`. (No exceptions. The first-class-destination rule is what
   makes the chart navigable for habitat groups.)
2. **textpath** — if `body` is the target of an `engraved_label`
   annotation with `curve_along` AND that annotation's resolved path
   circumference ≥ text-width × 1.2, strategy = `textpath`.
3. **radial** — if the body's label, when placed at
   `body_radial + glyph_radius + padding + tier·offset`, fits within the
   available arc length to its angular neighbors AND its tier ≤
   `LABEL_TIER_MAX`, strategy = `radial`.
4. **callout** — fallback. Strategy = `callout`.

Available-arc-length check (rule 3): `arc_at(r) = 2π·r · (Δθ_to_neighbor /
360°)` where `Δθ_to_neighbor` is the angular distance to the nearest
peer's label edge (not center). The label's pixel-width in its register
font is compared to `arc_at(r)`. If multiple peers share an angular band,
the smallest applicable arc wins.

### Anchor-glyph reuse — no new shapes

The callout's anchor mark at the body position is the **body-type glyph
already in the palette**, drawn at standard size. No new shapes:

- `star` / `companion` — the existing red core disk (`STAR_RETICLE_CORE_R`)
- `habitat` — the existing yellow diamond
- `gate` — the existing hexagon
- `wreck` — the existing dashed ring stub
- `arc_belt` — N/A (belts use textpath or radial; never callout)

The callout's distinguishing element is the **leader line + label block**,
not a new anchor shape. This is a hard constraint: introducing new anchor
shapes would fragment the visual vocabulary the playgroup has already
learned from existing v2 renders.

### Leader-line geometry

- **Routing:** orthogonal (right-angle bend), at most one bend per leader.
  Origin: anchor center. Terminus: label-block edge nearest the bend.
- **Style:** 1px stroke, color = body's `label_register` palette color
  (`engraved` → `BRASS`, `chalk` → `PARTY` (white), `prose` → `DIM` (italic-yellow)).
- **Terminator:** small filled square (3×3px) at the label-block end, in
  the same color as the leader line. The eye locks onto where the line
  "lands."
- **Avoidance:** leader lines may not cross each other within a single
  group (the six Red Prospect habitats are *one* group, fanned in
  bearing-order so lines don't cross). Cross-group crossings are tolerated
  but logged as an OTEL warning (see Observability section).

### Label-block content rule — title only, optional one-tag-line

A callout's label block contains:
- **Title** (line 1): the body's `label:` value, in its register font/weight.
- **Tag line** (line 2, OPTIONAL): a single short tag — typically `type`
  + a single quantitative attribute (e.g., `"habitat · 1.68M km"` for
  vael_thain, or `"gate · jumpline"` for grand_gate). Maximum 24 characters.

No paragraphs. No descriptions. The orrery is a navigation chart, not a
lore wiki. Bodies whose role needs more than one tag line indicate
content-side over-loading; address upstream, not in the chart.

### Gutter zone layout

A new render zone — the **legend gutter** — is reserved outside the
chart-circle bounding box but inside the SVG viewBox. The chart already
reserves margin for stardate header (top-left), reset button (top-right),
conjunction indicator (bottom-left), scale ruler (bottom-center), and
the AU scale (bottom-right). The legend gutter occupies the right and
left vertical strips between the chart circle and the SVG edges.

**Stacking rule for sibling groups.** When 3+ bodies share a parent and
all use callout strategy (the Red Prospect habitats are the canonical
case), the callouts are grouped into a single bordered block titled
`"<PARENT LABEL> SYSTEM"`. Six leader lines fan from anchors on the
parent's moon-band ring into the grouped block. Within the block,
children are listed in **`semi_major_au` ascending order** (innermost
first), each line as `<LABEL> · <distance>`.

**Inset fallback.** If neither gutter strip has the vertical real estate
for the required callouts, the renderer places the label block **inside**
the chart bounding box at an empty interior region, with a longer leader
line. This case emits an OTEL warning span; persistent inset placement
indicates chart density requires either a larger viewBox or fewer
labeled bodies.

### Annotation kind addition

A new annotation kind `callout_label` is added to chart.yaml schema for
explicit per-body callout opt-in (in addition to the rule-driven
fallback). Mirrors the `engraved_label` shape:

```yaml
- kind: callout_label
  text: "VAEL THAIN"
  body_ref: vael_thain
  tag: "habitat · 1.68M km"   # optional second line
```

Use cases: forcing a callout where radial would technically fit but the
chart designer wants emphasis (e.g., a campaign-pivotal location); or
overriding the auto-rule for a specific body.

## Observability — the lie-detector wiring

Per CLAUDE.md OTEL Observability Principle, every label-strategy
decision emits a span. Sebastien's GM panel becomes able to answer
"why is the chart this way."

### Per-body span: `chart.label_strategy`

Emitted once per labeled body, per render.

| Attribute | Type | Meaning |
|---|---|---|
| `body_id` | string | The body's slug. |
| `parent_id` | string \| null | Parent body slug, or null for root. |
| `parent_type` | string \| null | Parent's type (drives forced-callout rule). |
| `strategy_chosen` | enum: `textpath` \| `radial` \| `callout` | The selected strategy. |
| `selection_reason` | enum: `forced_companion` \| `textpath_fits` \| `radial_fits` \| `fallback_arc_too_short` \| `fallback_tier_capped` \| `fallback_textpath_too_short` \| `explicit_callout_label` | Why this strategy won. |
| `tier` | int (0..LABEL_TIER_MAX, only for `radial`) | The peer-collision tier. |
| `arc_available_px` | float (only for `radial` evaluations) | Arc-length to nearest neighbor. |
| `text_width_px` | float | Estimated label width in selected register font. |
| `path_circumference_px` | float (only for `textpath` evaluations) | Resolved curve_along path length. |

### Render-summary span: `chart.label_distribution`

Emitted once per chart render. Aggregates strategy attribution.

| Attribute | Type | Meaning |
|---|---|---|
| `bodies_total` | int | Bodies considered for labeling. |
| `bodies_textpath` | int | Strategy distribution. |
| `bodies_radial` | int | |
| `bodies_callout` | int | |
| `bodies_unlabeled` | int | Bodies with no `label:` field, intentionally anonymous (e.g., moon-band moons that aren't promoted). |
| `gutter_inset_fallbacks` | int | Times the gutter was full and inset placement was used. |
| `cross_group_crossings` | int | Leader lines that crossed across groups (warning indicator). |

### What the GM panel reads

A campaign world rendering with `bodies_callout / bodies_total` near zero
and `gutter_inset_fallbacks: 0` is healthy. A world with high
`gutter_inset_fallbacks` is content-side over-dense and wants a chart
redesign. A world with `bodies_unlabeled / bodies_total` high and
narratively-important destinations among them is the failure mode that
motivated this ADR — exactly the Red Prospect habitats case.

## Consequences

### Positive

- The orrery becomes navigable for companion-children habitats — the
  primary failure that motivated this ADR is structurally resolved.
- The 1-AU trojan cluster collision is resolved by fall-through to
  callouts when arc-length-fit fails.
- The `body:broken_drift` textPath flip is resolved by the
  path-circumference guard (rule 2's `× 1.2` factor).
- The renderer's strategy decisions become observable per body. Sebastien
  sees exactly which placement won and why. CLAUDE.md's lie-detector
  principle is now satisfied for chart rendering.
- Star Wars HUD palette alignment (commit 8895b56, the orrery v2 visual
  restoration) is preserved — callouts are HUD-pattern by design.

### Negative

- The strategy-selection logic is more code than the current two-strategy
  default. Estimated +250 lines of renderer code, +2 OTEL span types, +1
  annotation kind in the chart schema.
- Gutter zone reservation steals SVG real estate. Charts where the body
  count exceeds gutter capacity (rare; coyote_star is near the upper
  bound) will land in inset fallback with longer leader lines.
- A content world's "good" rendering now depends on the renderer
  predicting `text_width_px` from a font-metric estimate rather than the
  browser's actual measurement. Render-time vs display-time divergence is
  possible. Mitigation: the `× 1.2` safety factor on textpath fit, the
  same factor (or larger) on arc-length fit, and CI snapshot tests for
  representative campaign worlds.

### Neutral

- The annotation YAML schema gains one new kind (`callout_label`) but
  existing chart.yaml files do not require migration; auto-rule covers
  the cases that motivated this ADR.

## Alternatives Considered

### A. Replace radial-out with callouts wholesale

Single-strategy design. Rejected: outer-ring bodies (NEW CLAIM,
GRAND GATE, COMPACT ANCHORAGE, THE COUNTER) render perfectly with the
current radial-out logic. Replacing them with margin-callouts adds
visual noise without solving any failure. The failures are localized
to clustered, sub-AU, and companion-children regions; the strategy
should be likewise localized.

### B. Increase the radial canvas (zoom-in default)

Render the chart at 5 AU outermost instead of 10 AU, dropping last_drift
off-frame. Rejected: last_drift is the campaign's known boundary marker
(the "you have arrived at the edge" landmark in coyote_star lore). Cutting
it to make labels fit fixes the symptom by deleting the patient.

### C. Extend tier-bumping to also bump tangentially

Have tier-collisions push labels both radially AND tangentially. Rejected:
this *is* tangential displacement at the level of fan-spread, but it
keeps labels chained to bearing rays. The Red Prospect case (six children
within 0.027 AU of a 5.24 AU companion) doesn't yield to angular
displacement — there is no angular space at that radius. Tangential
bumping is a band-aid for the trojan-cluster case (failure 1) but does
not address failure 3 at all.

### D. Solve content-side only — split the chart

Rather than render six habitats around red_prospect, force scope-zoom to
Red Prospect to see its system. Rejected: forcing a zoom-shift to
identify a body breaks the navigation flow ("course-plot to Vael Thain"
becomes "first scope to Red Prospect, then identify, then go back").
The system-scope chart is the master navigation surface; it must be
self-sufficient for naming destinations the narrator may reference.

### E. Add a two-line legend in a fixed corner

Static legend listing all bodies, like a real cartographic key.
Rejected: visual reference shown ("HUD callouts" pattern, image
2026-05-04) is the established cinematic vocabulary the chart already
uses. A static legend separates name from position; callouts integrate
them. Also: a static legend doesn't give per-body strategy attribution
to the GM panel, which is the ADR's secondary goal.

### F. Defer to next playtest

Document the failures, ship as-is, fix when the playgroup hits the wall.
Rejected: the playgroup *did* hit the wall — the screenshot review on
2026-05-04 was the wall. Deferring further means narration that
references unidentifiable bodies, exactly the Sebastien lie-detector
failure mode this ADR is shaped to prevent.

## Implementation Pointer

This ADR ships ahead of implementation. The implementation lands as a
multi-story epic-45 follow-up, planned during the brainstorming phase
that precedes the implementation plan:

- **Story X — Renderer: callout strategy + selection rules** (server,
  ~5pts). Adds strategy enum, selection function, gutter-zone layout,
  leader-line geometry, OTEL spans `chart.label_strategy` /
  `chart.label_distribution`, and the `callout_label` annotation kind.
  Forced-callout for companion-children. Snapshot regression test
  against `coyote_star` at the failure-case scale.
- **Story Y — Content: label fields on companion habitats** (content,
  ~1pt, depends on Story X for the label rendering to engage). Adds
  `label:` to the six red_prospect habitats and the moons of
  far_landing / deep_root_world. Pure YAML.

Until those stories land, this ADR is `implementation-status: deferred`.
When Story X merges, the frontmatter flips to `live` and the
`implementation-pointer` is set to the merge commit / ADR-90 OTEL span
constant.

## References

- Live failure render: 2026-05-04 user screenshot of `coyote_star`
  system-scope, captured during ad-hoc design review.
- Story 45-43 (orrery v2 visual restoration, OQ-2 contributor, merged
  2026-05-04 to sidequest-server/develop, commit `7fa72e4` on
  orchestrator).
- Star Wars HUD palette alignment: sidequest-server commit 8895b56
  ("feat(orbital): align course overlay with Star Wars HUD palette").
- ADR-086 (Image-Composition Taxonomy) — taxonomy-of-strategies pattern
  precedent.
- ADR-088 (ADR Frontmatter Schema) — frontmatter conventions used here.
- ADR-090 (OTEL Dashboard Restoration) — span destination.
- CLAUDE.md "GM panel is the lie detector" — observability requirement.
- CLAUDE.md audience profile, Sebastien (mechanics-first, mechanical
  visibility is a feature) — drives OTEL attribution requirements.
- Existing renderer source: `sidequest-server/sidequest/orbital/render.py`
  (lines 840–927 for current label de-collision; lines 1053–1078 for
  moon-band rendering — the carve-out point for forced-callout).
- Existing chart annotations: `sidequest-server/sidequest/orbital/models.py:44`
  (Register Literal); models.py:187 (annotation kind dispatch).
- Campaign world: `sidequest-content/genre_packs/space_opera/worlds/coyote_star/orbits.yaml`
  (the failure-case fixture).
